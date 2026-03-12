import os
from PyQt6.QtCore import QObject
from PyQt6.QtWebEngineCore import QWebEngineProfile
from src.infrastructure.services.filelist_auth import FilelistAuthenticator
from src.presentation.windows.main_dashboard import MainDashboard
from src.infrastructure.repositories.sqlite_media_repository import SQLiteMediaRepository
from src.application.media_controller import MediaController


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

        # 2. Initialize Infrastructure & Controllers
        self.repo = SQLiteMediaRepository()
        
        # MediaController will eventually be broken into UseCases in the Application Layer,
        # but for now we inject the repo indirectly or simply retain its capabilities.
        self.media_controller = MediaController(self)
        
        # 3. Create and configure Main Dashboard
        self.main_window = MainDashboard(self.shared_profile, self.media_controller, self.repo)

    def run(self):
        """Displays the main window to start the user interaction loop."""
        self.main_window.showMaximized()
