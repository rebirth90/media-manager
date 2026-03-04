import os
import qbittorrentapi
from PyQt6.QtCore import QThread, pyqtSignal

class QBittorrentClient(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    added = pyqtSignal()

    def __init__(self, torrent_bytes: bytes, save_path: str, parent=None) -> None:
        super().__init__(parent)
        self.torrent_bytes = torrent_bytes
        self.save_path = save_path

    def run(self) -> None:
        host = os.getenv("QBIT_HOST", "127.0.0.1")
        port = os.getenv("QBIT_PORT", "8080")
        try:
            client = qbittorrentapi.Client(host=f"http://{host}:{port}", username=os.getenv("QBIT_USER", "admin"), password=os.getenv("QBIT_PASS", "adminadmin"))
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
        host = os.getenv("QBIT_HOST", "127.0.0.1")
        port = os.getenv("QBIT_PORT", "8080")
        try:
            client = qbittorrentapi.Client(host=f"http://{host}:{port}", username=os.getenv("QBIT_USER", "admin"), password=os.getenv("QBIT_PASS", "adminadmin"))
            client.auth_log_in()
            client.torrents_delete(delete_files=self.delete_files, torrent_hashes=self.torrent_hashes)
            self.finished.emit(True)
        except Exception as e:
            self.error.emit(f"Delete Failed: {str(e)}")
