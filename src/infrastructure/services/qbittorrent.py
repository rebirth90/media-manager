import os
import json
import qbittorrentapi
from PyQt6.QtCore import QThread, pyqtSignal

from src.domain.repositories import IMediaRepository
from src.application.use_cases.sync_use_cases import SyncTorrentStateUseCase
from src.utils.formatting import format_size, format_speed
from src.application.events import event_bus

class QBittorrentClient(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    added = pyqtSignal()

    def __init__(self, torrent_bytes: bytes, save_path: str, parent=None) -> None:
        super().__init__(parent)
        self.torrent_bytes = torrent_bytes
        self.save_path = save_path

    def run(self) -> None:
        host = os.getenv("QBIT_HOST")
        port = os.getenv("QBIT_PORT")
        try:
            client = qbittorrentapi.Client(host=f"http://{host}:{port}", username=os.getenv("QBIT_USER"), password=os.getenv("QBIT_PASS"))
            client.auth_log_in()
            res = client.torrents_add(torrent_files={'downloaded.torrent': self.torrent_bytes}, save_path=self.save_path)
            self.finished.emit(f"QBittorrent Push Success! Server Response: {res}")
            self.added.emit()
        except Exception as e:
            self.error.emit(f"QBittorrent Upload Failed: {str(e)}")

class QBittorrentDeleteWorker(QThread):
    finished = pyqtSignal(bool)
    error = pyqtSignal(str)
    
    def __init__(self, torrent_hashes: list, delete_files: bool, parent=None):
        super().__init__(parent)
        self.torrent_hashes = torrent_hashes
        self.delete_files = delete_files

    def run(self) -> None:
        host = os.getenv("QBIT_HOST")
        port = os.getenv("QBIT_PORT")
        try:
            client = qbittorrentapi.Client(host=f"http://{host}:{port}", username=os.getenv("QBIT_USER"), password=os.getenv("QBIT_PASS"))
            client.auth_log_in()
            client.torrents_delete(delete_files=self.delete_files, torrent_hashes=self.torrent_hashes)
            self.finished.emit(True)
        except Exception as e:
            self.error.emit(f"Delete Failed: {str(e)}")

class QBittorrentFilesWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, torrent_hash: str, parent=None):
        super().__init__(parent)
        self.torrent_hash = torrent_hash

    def run(self) -> None:
        host = os.getenv("QBIT_HOST")
        port = os.getenv("QBIT_PORT")
        try:
            client = qbittorrentapi.Client(host=f"http://{host}:{port}", username=os.getenv("QBIT_USER"), password=os.getenv("QBIT_PASS"))
            client.auth_log_in()
            files = client.torrents_files(torrent_hash=self.torrent_hash)
            self.finished.emit(files)
        except Exception as e:
            self.error.emit(f"Fetch Files Failed: {str(e)}")

class QBittorrentPollingThread(QThread):
    """
    Background infrastructure task that polls QBittorrent and updates the repository as the Source of Truth.
    It calls the SyncTorrentStateUseCase which emits signals to the UI.
    """
    def __init__(self, repo: IMediaRepository, sync_use_case: SyncTorrentStateUseCase, parent=None):
        super().__init__(parent)
        self.active = True
        self.repo = repo
        self.sync_use_case = sync_use_case
        self.host = os.getenv("QBIT_HOST")
        self.port = os.getenv("QBIT_PORT")

    def run(self) -> None:
        try:
            client = qbittorrentapi.Client(host=f"http://{self.host}:{self.port}", username=os.getenv("QBIT_USER"), password=os.getenv("QBIT_PASS"))
            client.auth_log_in()
        except:
            return

        QBIT_STATE_MAP = {
            "downloading":          ("Downloading",   "PillDownloading", "PbActive"),
            "stalledDL":            ("Stalled",       "PillDownloading", "PbActive"),
            "forcedDL":             ("Forced DL",     "PillDownloading", "PbActive"),
            "completed":            ("Completed",     "PillSuccess",     "PbSuccess"),
            "pausedDL":             ("Paused",        "PillPaused",      "PbUnknown"),
            "queuedDL":             ("Queued",        "PillQueued",      "PbUnknown"),
            "unknown":              ("Unknown",       "PillUnknown",     "PbUnknown"),
            "error":                ("Error",         "PillDanger",      "PbUnknown"),
        }

        while self.active:
            try:
                torrents = client.torrents_info()
                media_items = self.repo.get_all_items()

                known_hashes = set()
                for item in media_items:
                    t_data = item.torrent_data
                    if t_data:
                        try:
                            t_info = json.loads(t_data)
                            known_hashes.add(t_info.get("hash", ""))
                        except: pass

                for item in media_items:
                    t_data = item.torrent_data
                    t_info = json.loads(t_data) if t_data else {}
                    
                    # Prevent redundant qBittorrent processing if already completed
                    if t_info.get("human_state") == "Completed":
                        # SAFETY CHECK: If it's a TV season, we MUST have the 'files' payload before we can safely stop polling.
                        if item.is_season and "files" not in t_info:
                            pass 
                        else:
                            # Fully cached. Emit DB state directly and skip API evaluation
                            self.sync_use_case.execute(item.id, t_data)
                            continue
                    
                    current_hash = t_info.get("hash", "")
                    expected_name = t_info.get("name", "")
                    
                    matched_t = None
                    if current_hash:
                        matched_t = next((t for t in torrents if t.get('hash') == current_hash), None)
                    if not matched_t and expected_name:
                        matched_t = next((t for t in torrents if t.get('name') == expected_name), None)
                    if not matched_t:
                        target_suffix = item.relative_path.replace("\\", "/")
                        candidates = []
                        for t in torrents:
                            sp = t.get('save_path', '').replace("\\", "/")
                            if (sp.endswith(target_suffix) or target_suffix in sp) and t.get('hash') not in known_hashes:
                                candidates.append(t)
                        if candidates:
                            candidates.sort(key=lambda x: x.get('added_on', 0), reverse=True)
                            matched_t = candidates[0]
                    
                    if matched_t:
                        new_hash = matched_t.get('hash', '')
                        known_hashes.add(new_hash)
                        
                        prog_val = matched_t.get('progress', 0.0)
                        state = matched_t.get('state', 'Unknown')
                        dlspeed = matched_t.get('dlspeed', 0)
                        
                        raw_total_size = matched_t.get('total_size')
                        raw_size = raw_total_size if raw_total_size is not None else (matched_t.get('size') or 0)
                        
                        is_completed = (prog_val == 1.0)
                        
                        if is_completed:
                            human_state, pill_class, pb_style = "Completed", "PillSuccess", "PbSuccess"
                            target_path = item.relative_path.replace("\\", "/")
                            if not self.repo.get_torrent_cache_by_path(target_path):
                                self.repo.set_torrent_cache(new_hash, target_path, json.dumps(matched_t))
                        else:
                            fallback = (state.replace("DL","").replace("UP","").strip().capitalize(), "PillWarning", "PbWarning")
                            human_state, pill_class, pb_style = QBIT_STATE_MAP.get(state, fallback)
                            
                        active_state_str = f"State: {human_state} | Progress: {int(prog_val * 100)}% | Size: {format_size(raw_size)}"
                        t_info.update({
                            "hash": new_hash,
                            "name": matched_t.get('name', ''),
                            "human_state": human_state,
                            "pill_class": pill_class,
                            "pb_style": pb_style,
                            "prog_val": prog_val,
                            "size_str": format_size(raw_size),
                            "speed_str": format_speed(dlspeed),
                            "active_state_str": active_state_str
                        })
                        
                        # Fetch file list once for TV series to enable episode rows
                        if item.is_season and "files" not in t_info and new_hash:
                            try:
                                raw_files = client.torrents_files(torrent_hash=new_hash)
                                t_info["files"] = [{"name": f.get("name", "")} for f in raw_files]
                            except:
                                pass
                        
                        # Use Domain Case to update DB and emit via EventBus
                        self.sync_use_case.execute(item.id, json.dumps(t_info))
                        
            except Exception as e:
                pass
                
            QThread.sleep(2)

    def stop(self):
        self.active = False
        self.wait()