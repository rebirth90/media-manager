import os
from typing import List, Any
import qbittorrentapi
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from src.core.image_downloader import ImageDownloaderThread
from src.core.torrent_poller import TorrentPollingThread
from src.core.tmdb_fetcher import TMDBFetcherThread
from src.services.qbittorrent import QBittorrentClient
from src.services.ssh_telemetry import SSHTelemetryClient


class QueueAppenderThread(QThread):
    finished_appending = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, target_path: str, parent=None):
        super().__init__(parent)
        self.target_path = target_path

    def run(self):
        try:
            with open(r"\\192.168.20.102\Media\conversion.txt", "a", encoding="utf-8") as f:
                f.write(self.target_path + "\n")
            self.finished_appending.emit()
        except Exception as e:
            self.error.emit(str(e))


class MediaController(QObject):
    """
    Central Controller for handling Media Business Logic.
    Decoupled from UI components.
    """
    # Signals to update the UI
    torrents_updated = pyqtSignal(list)
    title_resolved = pyqtSignal(int, str) # flow_index, title
    details_resolved = pyqtSignal(int, dict) # flow_index, details_dict
    image_downloaded = pyqtSignal(int, bytes) # flow_index, image_bytes
    ssh_telemetry_updated = pyqtSignal(int, str, str, int, str, str, str) # db_status, sub_status, prog, gen_out, ff_out, flags
    
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
            self._threads.append(fetcher)
            fetcher.start()
        elif image_url:
            self.fetch_image(flow_index, image_url)
            
        # 2. Add to qBittorrent if it's new
        if not is_restored and torrent_bytes:
            base_path = os.getenv("BASE_SCRATCH_PATH", "/data/scratch")
            final_save_path = f"{base_path}/{relative_path}".replace("\\", "/")
            
            qbit_worker = QBittorrentClient(torrent_bytes, final_save_path, self)
            self._threads.append(qbit_worker)
            qbit_worker.start()

    def fetch_image(self, flow_index: int, url: str):
        thread = ImageDownloaderThread(url, self)
        thread.finished.connect(lambda data: self.image_downloaded.emit(flow_index, data))
        self._threads.append(thread)
        thread.start()

    def request_conversion(self, relative_path: str):
        target_path = relative_path.replace("\\", "/") 
        queue_thread = QueueAppenderThread(target_path, self)
        self._threads.append(queue_thread)
        queue_thread.start()

    def request_deletion(self, hashes: List[str], delete_files: bool):
        try:
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
            print(f"Failed to delete torrents {hashes}: {e}")

    def start_ssh_telemetry(self, flow_index: int, target_title: str):
        ssh_worker = SSHTelemetryClient(target_title=target_title, parent=self)
        ssh_worker.telemetry_data.connect(lambda db, sub, prog, gen, ff, flags: 
            self.ssh_telemetry_updated.emit(flow_index, db, sub, prog, gen, ff, flags)
        )
        self._threads.append(ssh_worker)
        ssh_worker.start()
