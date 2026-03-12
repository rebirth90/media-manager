import os
from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout

class BrowserModalDialog(QDialog):
    torrent_downloaded = pyqtSignal(str, str, str, str)

    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.setWindowTitle("Filelist Torrents Browser")
        
        # Modern dark theme for browser modal
        self.setStyleSheet("""
            QDialog {
                background-color: #1e293b;
                border-radius: 12px;
            }
        """)
        
        screen = QApplication.primaryScreen().geometry()
        self.resize(int(screen.width() * 0.75), int(screen.height() * 0.75))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        from PyQt6.QtWebEngineCore import QWebEnginePage
        self.web_view = QWebEngineView(self)
        new_page = QWebEnginePage(self.profile, self.web_view)
        self.web_view.setPage(new_page)

        self.web_view.setStyleSheet("border-radius: 12px;")
        layout.addWidget(self.web_view)

        # Connection that caused signal duplication on multiple opens
        self.profile.downloadRequested.connect(self._on_download_requested)
        self.web_view.page().loadFinished.connect(self._on_page_loaded)

        self.web_view.setUrl(QUrl("https://filelist.io/browse.php"))
        self._current_request = None

    def _on_download_requested(self, request: QWebEngineDownloadRequest) -> None:
        self._current_request = request
        
        temp_dir = os.path.join(os.getcwd(), "temp_torrents")
        os.makedirs(temp_dir, exist_ok=True)
        request.setDownloadDirectory(temp_dir)
        request.accept()
        
        # Added tracking to prevent multiple signals from firing simultaneously
        state_dict = {"img_url": None, "title": None, "season": None, "completed": False, "emitted": False}
        
        def try_finish():
            if state_dict["completed"] and state_dict["title"] is not None:
                if state_dict["emitted"]: return
                state_dict["emitted"] = True
                
                file_path = request.downloadDirectory() + os.sep + request.downloadFileName()
                print(f"DEBUG: Download completed successfully! File: {file_path}")
                self.torrent_downloaded.emit(file_path, state_dict["img_url"], state_dict["title"], state_dict.get("season") or "")
                self.accept()
                
        def on_state_changed(state):
            print(f"DEBUG: State changed to {state}")
            if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                state_dict["completed"] = True
                try_finish()
            elif state == QWebEngineDownloadRequest.DownloadState.DownloadCancelled:
                print("DEBUG: Download cancelled")
            elif state == QWebEngineDownloadRequest.DownloadState.DownloadInterrupted:
                print(f"DEBUG: Download interrupted. Reason: {request.interruptReasonString()}")
                
        request.stateChanged.connect(on_state_changed)
        
        js_code = """
            (function() {
                var img = document.querySelector("img[src*='tmdb.org']") || document.querySelector("img[src*='imdb.com']");
                var cleanTitle = "";
                var tmdbId = "";
                var tmdbType = "";
                
                var tmdbLink = document.querySelector("a[href*='themoviedb.org/movie/'], a[href*='themoviedb.org/tv/']");
                if (tmdbLink) {
                    if (tmdbLink.href.includes('/movie/')) tmdbType = "movie";
                    else if (tmdbLink.href.includes('/tv/')) tmdbType = "tv";
                    
                    var urlParts = tmdbLink.href.split('?')[0].split('/');
                    var lastPart = urlParts[urlParts.length - 1] || urlParts[urlParts.length - 2];
                    if (lastPart) {
                        var match = lastPart.match(/^(\\d+)/);
                        if (match) tmdbId = match[1];
                    }
                }
                
                if (!tmdbId) {
                    var imdbLink = document.querySelector("a[href*='imdb.com/title/']");
                    if (imdbLink) {
                        var match = imdbLink.href.match(/tt\\d+/);
                        if (match) {
                            tmdbId = match[0];
                            tmdbType = "imdb";
                        }
                    }
                }
                
                if (tmdbId && tmdbType) {
                    cleanTitle = "tmdb:" + tmdbType + ":" + tmdbId;
                } else {
                    var rawTitle = "";
                    var h1 = document.querySelector(".page-header, h1");
                    if (h1) rawTitle = h1.textContent.trim();
                    else rawTitle = document.title || "Unknown Media";
                    
                    var tmpTitle = rawTitle.split('.').join(' ');
                    var match = tmpTitle.match(/^(.*?)(?:\\s+(?:1080p|720p|2160p|4k|web-dl|bluray|hdtv|x264|h264|hevc))/i);
                    if (match) cleanTitle = match[1].trim();
                    else cleanTitle = tmpTitle;
                }
                
                var seasonStr = "";
                var titleToRegex = window.document.title;
                var h1Element = document.querySelector(".page-header, h1");
                if (h1Element) titleToRegex = h1Element.textContent;
                
                var sMatch = titleToRegex.match(/[Ss](\\d{1,2})|Season\\s*(\\d{1,2})/i);
                if (sMatch) {
                    var sNum = parseInt(sMatch[1] || sMatch[2], 10);
                    if (!isNaN(sNum)) {
                        seasonStr = "Season " + sNum;
                    }
                }
                
                return { imageUrl: img ? img.src : "", title: cleanTitle, season: seasonStr };
            })();
        """
        
        def js_callback(result):
            state_dict["img_url"] = result.get('imageUrl', '') if isinstance(result, dict) else ''
            state_dict["title"] = result.get('title', 'Unknown Media') if isinstance(result, dict) else 'Unknown Media'
            state_dict["season"] = result.get('season', '') if isinstance(result, dict) else ''
            try_finish()
            
        self.web_view.page().runJavaScript(js_code, js_callback)

    def _on_page_loaded(self, ok: bool) -> None:
        if not ok: 
            return
            
        current_url = self.web_view.url().toString()
        
        if "login.php" in current_url:
            print("DEBUG: Cookie expired or missing. Delegating to background auth manager...")
            parent_win = self.parent()
            if hasattr(parent_win, 'auth_manager'):
                self.web_view.setDisabled(True)
                parent_win.auth_manager.authenticated.connect(self._on_reauth_success)
                parent_win.auth_manager.login()
            else:
                print("ERROR: Background auth manager not found!")
                
    def _on_reauth_success(self):
        print("DEBUG: Background re-auth successful. Reloading browse page in modal...")
        parent_win = self.parent()
        if hasattr(parent_win, 'auth_manager'):
            try:
                parent_win.auth_manager.authenticated.disconnect(self._on_reauth_success)
            except TypeError:
                pass
        self.web_view.setDisabled(False)
        self.web_view.setUrl(QUrl("https://filelist.io/browse.php"))

    # FIX ISSUE 3: Safely decouple signals universally to avoid firing twice
    def _cleanup_connections(self):
        try:
            self.profile.downloadRequested.disconnect(self._on_download_requested)
        except Exception:
            pass

    def accept(self):
        self._cleanup_connections()
        super().accept()

    def reject(self):
        self._cleanup_connections()
        super().reject()

    def closeEvent(self, event) -> None:
        self._cleanup_connections()
        if self.web_view.page():
            self.web_view.page().deleteLater()
        self.web_view.setPage(None)
        self.web_view.deleteLater()
        super().closeEvent(event)