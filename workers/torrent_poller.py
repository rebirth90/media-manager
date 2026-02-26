import os
import time
from typing import List, Optional

import qbittorrentapi
from PyQt6.QtCore import QThread, pyqtSignal

class TorrentPollingThread(QThread):
    data_updated = pyqtSignal(list)
    torrent_completed = pyqtSignal()
    target_progress = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active = True
        self.target_hash: Optional[str] = None
        self.is_waiting_for_new_target: bool = False
        self.hashes_before_add: List[str] = []
        self.host = os.getenv("QBIT_HOST", "127.0.0.1")
        self.port = os.getenv("QBIT_PORT", "8080")

    def set_pre_add_state(self, hashes: List[str]) -> None:
        self.hashes_before_add = hashes
        self.target_hash = None
        self.is_waiting_for_new_target = True

    def run(self) -> None:
        try:
            client = qbittorrentapi.Client(host=f"{self.host}:{self.port}", username=os.getenv("QBIT_USER", "admin"), password=os.getenv("QBIT_PASS", "adminadmin"))
            client.auth_log_in()
        except Exception as e:
            self.error.emit(f"Polling Auth Failed: {str(e)}")
            return

        while self.active:
            try:
                torrents = client.torrents_info()
                current_hashes = [t.get('hash') for t in torrents]
                if self.is_waiting_for_new_target and current_hashes:
                    for h in current_hashes:
                        if h not in self.hashes_before_add:
                            self.target_hash = h
                            self.is_waiting_for_new_target = False
                            break

                target_torrent_data = []
                if self.target_hash:
                    for t in torrents:
                        if t.get('hash') == self.target_hash:
                            target_torrent_data.append(t)
                            prog = t.get('progress', 0.0)
                            self.target_progress.emit(int(prog * 100))
                            state = t.get('state', '')
                            if prog == 1.0 or state in ['uploading', 'stalledUP', 'pausedUP', 'completed']:
                                self.torrent_completed.emit()
                                self.target_hash = None
                            break
                            
                self.data_updated.emit([target_torrent_data, current_hashes])
            except Exception as e:
                self.error.emit(f"Polling Error: {str(e)}")
            QThread.sleep(2)

    def stop(self) -> None:
        self.active = False
        self.wait()
