import os
import time
from typing import List, Optional

import qbittorrentapi
from PyQt6.QtCore import QThread, pyqtSignal

class TorrentPollingThread(QThread):
    data_updated = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active = True
        self.host = os.getenv("QBIT_HOST", "127.0.0.1")
        self.port = os.getenv("QBIT_PORT", "8080")

    def run(self) -> None:
        try:
            # FIX: Added http:// to the host string
            client = qbittorrentapi.Client(host=f"http://{self.host}:{self.port}", username=os.getenv("QBIT_USER", "admin"), password=os.getenv("QBIT_PASS", "adminadmin"))
            client.auth_log_in()
        except Exception as e:
            self.error.emit(f"Polling Auth Failed: {str(e)}")
            return

        while self.active:
            try:
                torrents = client.torrents_info()
                self.data_updated.emit(torrents)
            except Exception as e:
                self.error.emit(f"Polling Error: {str(e)}")
            QThread.sleep(2)

    def stop(self) -> None:
        self.active = False
        self.wait()