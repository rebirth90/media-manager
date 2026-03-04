import os
from PyQt6.QtCore import QObject
from PyQt6.QtWebEngineCore import QWebEngineProfile
from src.services.filelist_auth import FilelistAuthenticator
from src.ui.main_window import SecureServerWindow
from src.core.media_controller import MediaController


class AppController(QObject):
    """
    Main Application Controller.
    Manages the lifecycle of the application, authenticates global services,
    and orchestrates communication between the UI and MediaController.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Setup Global WebEngine Auth Profile
        cache_dir = os.path.join(os.getcwd(), ".qt_cache")
        os.makedirs(cache_dir, exist_ok=True)
        
        self.shared_profile = QWebEngineProfile("filelist_auth", self)
        self.shared_profile.setPersistentStoragePath(cache_dir)
        self.shared_profile.setCachePath(cache_dir)
        
        self.auth_manager = FilelistAuthenticator(self.shared_profile, self)
        self.auth_manager.login()

        # 2. Initialize Controllers
        self.media_controller = MediaController(self)
        
        # 3. Create and configure Main Window
        self.main_window = SecureServerWindow(self.shared_profile, self.media_controller)

    def run(self):
        """Displays the main window to start the user interaction loop."""
        self.main_window.showMaximized()
