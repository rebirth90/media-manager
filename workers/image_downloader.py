import requests
from PyQt6.QtCore import QThread, pyqtSignal

class ImageDownloaderThread(QThread):
    finished = pyqtSignal(bytes)

    def __init__(self, url: str, parent=None) -> None:
        super().__init__(parent)
        self.url = url

    def run(self) -> None:
        try:
            if not self.url or not self.url.startswith("http"):
                self.finished.emit(b"")
                return
            resp = requests.get(self.url, timeout=10)
            if resp.status_code == 200:
                self.finished.emit(resp.content)
            else:
                self.finished.emit(b"")
        except Exception as e:
            print(f"Image fetch error: {e}")
            self.finished.emit(b"")
