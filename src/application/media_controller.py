import os
import logging
from typing import List, Any
import qbittorrentapi
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from src.infrastructure.services.image_downloader import ImageDownloaderThread
from src.infrastructure.services.torrent_poller import TorrentPollingThread
from src.infrastructure.services.tmdb_fetcher import TMDBFetcherThread, TMDBEpisodeFetcherThread
from src.infrastructure.services.qbittorrent import QBittorrentClient, QBittorrentFilesWorker
from src.infrastructure.services.ssh_client import SSHTelemetryClient

import re

# Configure Logging for conversion tracking
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MediaController")

def parse_tv_title(raw_name: str):
    """Parses a torrent name into (Show Name, Season Number, Is Season Pack)."""
    # 1. Check for episode pattern first: S01E05, 1x05
    ep_match = re.search(r'(.*?)[. ]s(\d{1,2})e(\d{1,2})', raw_name, re.IGNORECASE)
    if not ep_match:
        ep_match = re.search(r'(.*?)[. ](\d{1,2})x(\d{1,2})', raw_name, re.IGNORECASE)
        
    if ep_match:
        show_name = ep_match.group(1).replace(".", " ").strip()
        season_num = int(ep_match.group(2))
        return show_name, season_num, False # It's a single episode, no accordion
        
    # 2. Check for season pattern: S03, S3, Season 3
    s_match = re.search(r'(.*?)[. ]s(\d{1,2})(?:[e. ]|$)', raw_name, re.IGNORECASE)
    if not s_match:
        s_match = re.search(r'(.*?)[. ]season[. ]?(\d{1,2})', raw_name, re.IGNORECASE)
        
    if s_match:
        show_name = s_match.group(1).replace(".", " ").strip()
        season_num = int(s_match.group(2))
        return show_name, season_num, True # It is a full season pack, force accordion
        
    return raw_name, None, False


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
    torrent_files_resolved = pyqtSignal(int, list) # flow_index, files_list
    season_episodes_resolved = pyqtSignal(int, dict) # flow_index, episodes_dict
    
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
            try:
                parts = title.split(":")
                media_type = parts[1]
                tmdb_id = parts[2]
                
                # If it's TV, we might have a season number to override
                season_num = None
                if media_type == "tv" and len(parts) > 3:
                    try: season_num = int(parts[3])
                    except: pass
                
                # If we don't have a season num but it's a TV series, try parsing relative_path
                if media_type == "tv" and not season_num:
                    _, parsed_s, _ = parse_tv_title(os.path.basename(relative_path))
                    if parsed_s: season_num = parsed_s

                # Boot up the episodes fetch immediately
                if media_type == "tv" and season_num:
                    self.request_season_episodes(flow_index, tmdb_id, season_num)

                fetcher = TMDBFetcherThread(tmdb_id, media_type, self)
                
                def on_title_resolved(resolved_title, idx=flow_index, s_num=season_num):
                    final_title = resolved_title
                    if s_num and f"Season {s_num}" not in resolved_title:
                        final_title = f"{resolved_title} - Season {s_num}"
                    self.title_resolved.emit(idx, final_title)
                
                fetcher.title_resolved.connect(on_title_resolved)
                
                def handle_details(details, idx=flow_index):
                    self.details_resolved.emit(idx, details)
                    img = details.get("image_url") or image_url
                    if img:
                        self.fetch_image(idx, img)
                
                fetcher.details_resolved.connect(handle_details)
                
                if not is_restored:
                    fetcher.title_resolved.connect(
                        lambda resolved_title, idx=flow_index: self.start_ssh_telemetry(idx, resolved_title)
                    )
                
                self._threads.append(fetcher)
                fetcher.start()
            except Exception as e:
                logger.error(f"Error starting TMDB resolution for {title}: {e}")
                self.title_resolved.emit(flow_index, title)
        else:
            if image_url:
                self.fetch_image(flow_index, image_url)
            # For plain-string titles, start SSH telemetry immediately
            if not is_restored:
                self.start_ssh_telemetry(flow_index, title)
            
        # 2. Add to qBittorrent if it's new
        if not is_restored and torrent_bytes:
            base_path = os.getenv("BASE_SCRATCH_PATH")
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
        target_path = relative_path.replace("\\", "/") 
        logger.info(f"[Read-Only Mode] Torrent completed for: {target_path}. Deferring trigger to native qBittorrent script.")

    def request_deletion(self, hashes: List[str], delete_files: bool):
        try:
            logger.info(f"Requesting deletion of torrents: {hashes}")
            h = os.getenv("QBIT_HOST")
            p = os.getenv("QBIT_PORT")
            c = qbittorrentapi.Client(
                host=f"http://{h}:{p}", 
                username=os.getenv("QBIT_USER"), 
                password=os.getenv("QBIT_PASS")
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

    def request_torrent_files(self, flow_index: int, torrent_hash: str):
        worker = QBittorrentFilesWorker(torrent_hash, self)
        worker.finished.connect(lambda files: self.torrent_files_resolved.emit(flow_index, files))
        worker.error.connect(lambda err: logger.error(f"[Files Fetch Error - {flow_index}]: {err}"))
        self._threads.append(worker)
        worker.start()

    def request_season_episodes(self, flow_index: int, tmdb_id: str, season_num: int):
        worker = TMDBEpisodeFetcherThread(tmdb_id, season_num, self)
        worker.episodes_resolved.connect(lambda eps: self.season_episodes_resolved.emit(flow_index, eps))
        worker.error.connect(lambda err: logger.error(f"[TMDB Episodes Error - {flow_index}]: {err}"))
        self._threads.append(worker)
        worker.start()