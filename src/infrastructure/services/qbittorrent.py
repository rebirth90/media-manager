import os
import json
import qbittorrentapi
from PyQt6.QtCore import QThread, pyqtSignal

from src.domain.repositories import IMediaRepository
from src.application.use_cases.sync_use_cases import SyncTorrentStateUseCase
from src.utils.formatting import format_size, format_speed

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
            raw_files = client.torrents_files(torrent_hash=self.torrent_hash)
            normalized_files = []
            for f in raw_files:
                try:
                    size_val = f.get("size", 0)
                except Exception:
                    size_val = 0
                normalized_files.append({
                    "name": f.get("name", ""),
                    "size": int(size_val or 0),
                })
            self.finished.emit(normalized_files)
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

        client = None

        while self.active:
            try:
                # 1. Self-healing connection. Re-authenticate if client is None
                if not client:
                    client = qbittorrentapi.Client(
                        host=f"http://{self.host}:{self.port}", 
                        username=os.getenv("QBIT_USER"), 
                        password=os.getenv("QBIT_PASS")
                    )
                    client.auth_log_in()

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
                        if not item.is_season:
                            # Fully cached movie. Emit DB state directly and skip API evaluation.
                            self.sync_use_case.execute(item.id, t_data)
                            continue
                        # TV series: also freeze if conversion is fully done.
                        # After conversion completes, torrent files are removed and qBittorrent
                        # reports MissingFiles. Freezing here keeps the UI at "Completed".
                        if item.is_season and item.conversion_data:
                            try:
                                c_info = json.loads(item.conversion_data)
                                if isinstance(c_info, dict): c_info = [c_info]
                                if c_info and all(
                                    str(r.get("db_status", "")).upper() == "COMPLETED"
                                    for r in c_info
                                ):
                                    self.sync_use_case.execute(item.id, t_data)
                                    continue
                            except Exception:
                                pass
                    
                    current_hash = t_info.get("hash", "")
                    expected_name = t_info.get("name", "")

                    expected_season = None
                    if item.is_season:
                        try:
                            season_raw = str(getattr(item, 'season', '') or '')
                            season_digits = ''.join(ch for ch in season_raw if ch.isdigit())
                            if season_digits:
                                expected_season = int(season_digits)
                        except Exception:
                            expected_season = None

                    def _season_matches(torrent_obj) -> bool:
                        if expected_season is None:
                            return True
                        t_name = str(torrent_obj.get('name', '')).lower()
                        tokens = (
                            f"s{expected_season:02d}",
                            f"season {expected_season}",
                            f"season{expected_season}",
                        )
                        return any(tok in t_name for tok in tokens)
                    
                    matched_t = None
                    if current_hash:
                        matched_t = next((t for t in torrents if t.get('hash') == current_hash), None)
                        if matched_t and not _season_matches(matched_t):
                            matched_t = None
                    if not matched_t and expected_name:
                        matched_t = next((t for t in torrents if t.get('name') == expected_name), None)
                        if matched_t and not _season_matches(matched_t):
                            matched_t = None
                    if not matched_t:
                        target_suffix = item.relative_path.replace("\\", "/")
                        candidates = []
                        for t in torrents:
                            sp = t.get('save_path', '').replace("\\", "/")
                            # Do not block by known_hashes here: stale DB mappings can otherwise never self-heal.
                            if (sp.endswith(target_suffix) or target_suffix in sp) and _season_matches(t):
                                candidates.append(t)

                        # If no season-aware candidate is found, fallback to path-only candidates.
                        if not candidates:
                            for t in torrents:
                                sp = t.get('save_path', '').replace("\\", "/")
                                if sp.endswith(target_suffix) or target_suffix in sp:
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
                            "raw_size_bytes": int(raw_size or 0),
                            "size_str": format_size(raw_size),
                            "speed_str": format_speed(dlspeed),
                            "active_state_str": active_state_str
                        })
                        
                        # Fetch file list (with sizes) for TV series to enable accurate episode rows
                        cached_files = t_info.get("files", [])
                        files_need_refresh = (
                            not isinstance(cached_files, list)
                            or not cached_files
                            or any(not isinstance(f, dict) or "size" not in f for f in cached_files)
                        )
                        if item.is_season and files_need_refresh and new_hash:
                            try:
                                raw_files = client.torrents_files(torrent_hash=new_hash)
                                t_info["files"] = [
                                    {
                                        "name": f.get("name", ""),
                                        "size": int(f.get("size", 0) or 0),
                                    }
                                    for f in raw_files
                                ]
                            except:
                                pass
                        
                        # Use Domain Case to update DB and emit via EventBus
                        self.sync_use_case.execute(item.id, json.dumps(t_info))
                        
            except Exception as e:
                # If connection fails, set client to None so it tries to log in again next loop
                client = None
                print(f"[QBitTracker] Polling cycle failed, will retry: {str(e)}")
                
            # 2. Responsive sleeping: Sleep in 100ms chunks to allow instant thread termination
            for _ in range(20):
                if not self.active:
                    break
                self.msleep(100)

    def stop(self):
        self.active = False
        self.wait()