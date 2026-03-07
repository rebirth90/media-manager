import os
import logging
from typing import List, Any
import qbittorrentapi
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from src.core.image_downloader import ImageDownloaderThread
from src.core.torrent_poller import TorrentPollingThread
from src.core.tmdb_fetcher import TMDBFetcherThread
from src.services.qbittorrent import QBittorrentClient
from src.services.ssh_telemetry import SSHTelemetryClient

# Configure Logging for conversion tracking
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MediaController")


class MediaController(QObject):
    """
    Central Controller for handling Media Business Logic.
    Decoupled from UI components. Operates in read-only telemetry mode for conversions.
    """
    # Signals to update the UI
    torrents_updated = pyqtSignal(list)
    title_resolved = pyqtSignal(int, str) # flow_index, title
    details_resolved = pyqtSignal(int, dict) # flow_index, details_dict
    image_downloaded = pyqtSignal(int, bytes) # flow_index, image_bytes
    ssh_telemetry_updated = pyqtSignal(int, str) # flow_index, json_payload
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._threads = []
        self._qbit_client = None
        self._poll_worker = None
        self.start_global_polling()

    def start_global_polling(self):
        """Initializes the single qBittorrent poller."""
        if self._poll_worker:
            return

        self._poll_worker = TorrentPollingThread(self)
        self._poll_worker.data_updated.connect(self.torrents_updated.emit)
        self._poll_worker.start()

    def add_media_flow(self, flow_index: int, title: str, relative_path: str, torrent_bytes: bytes, image_url: str, is_restored: bool = False):
        """Bootstraps the background tasks for a newly added media flow."""
        logger.info(f"Adding media flow [{flow_index}]: {title}")
        
        # 1. Start TMDB resolution
        if title.startswith("tmdb:"):
            _, media_type, tmdb_id = title.split(":", 2)
            self.title_resolved.emit(flow_index, tmdb_id)
            fetcher = TMDBFetcherThread(tmdb_id, media_type, self)
            fetcher.title_resolved.connect(lambda t: self.title_resolved.emit(flow_index, t))
            
            def handle_details(details, idx=flow_index):
                self.details_resolved.emit(idx, details)
                img = details.get("image_url") or image_url
                if img:
                    self.fetch_image(idx, img)
            
            fetcher.details_resolved.connect(handle_details)
            
            # Delay SSH telemetry until the human title is available
            if not is_restored:
                fetcher.title_resolved.connect(
                    lambda resolved_title, idx=flow_index: self.start_ssh_telemetry(idx, resolved_title)
                )
            
            self._threads.append(fetcher)
            fetcher.start()
        else:
            if image_url:
                self.fetch_image(flow_index, image_url)
            # For plain-string titles, start SSH telemetry immediately
            if not is_restored:
                self.start_ssh_telemetry(flow_index, title)
            
        # 2. Add to qBittorrent if it's new
        if not is_restored and torrent_bytes:
            base_path = os.getenv("BASE_SCRATCH_PATH", "/data/scratch")
            final_save_path = f"{base_path}/{relative_path}".replace("\\", "/")
            logger.info(f"Queueing torrent download to: {final_save_path}")
            
            qbit_worker = QBittorrentClient(torrent_bytes, final_save_path, self)
            self._threads.append(qbit_worker)
            qbit_worker.start()

    def fetch_image(self, flow_index: int, url: str):
        thread = ImageDownloaderThread(url, self)
        thread.finished.connect(lambda data: self.image_downloaded.emit(flow_index, data))
        self._threads.append(thread)
        thread.start()

    def request_conversion(self, relative_path: str):
        """
        Called when a torrent completes.
        App is now in strictly read-only telemetry mode. Bypassing conversion.txt append.
        qBittorrent handles the script triggering natively.
        """
        target_path = relative_path.replace("\\", "/") 
        logger.info(f"[Read-Only Mode] Torrent completed for: {target_path}. Deferring trigger to native qBittorrent script.")

    def request_deletion(self, hashes: List[str], delete_files: bool):
        try:
            logger.info(f"Requesting deletion of torrents: {hashes}")
            h = os.getenv("QBIT_HOST", "127.0.0.1")
            p = os.getenv("QBIT_PORT", "8080")
            c = qbittorrentapi.Client(
                host=f"{h}:{p}", 
                username=os.getenv("QBIT_USER", "admin"), 
                password=os.getenv("QBIT_PASS", "adminadmin")
            )
            c.auth_log_in()
            c.torrents_delete(delete_files=delete_files, torrent_hashes=hashes)
        except Exception as e:
            logger.error(f"Failed to delete torrents {hashes}: {e}")

    def start_ssh_telemetry(self, flow_index: int, target_title: str):
        logger.info(f"Initializing SSH telemetry for: {target_title}")
        ssh_worker = SSHTelemetryClient(target_title=target_title, parent=self)
        ssh_worker.telemetry_data.connect(lambda json_payload: 
            self.ssh_telemetry_updated.emit(flow_index, json_payload)
        )
        ssh_worker.error.connect(lambda err: logger.error(f"[Telemetry Error - {target_title}]: {err}"))
        self._threads.append(ssh_worker)
        ssh_worker.start()