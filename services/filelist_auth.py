import os
from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage

class FilelistAuthenticator(QObject):
    authenticated = pyqtSignal()
    
    def __init__(self, profile: QWebEngineProfile, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.page = QWebEnginePage(self.profile, self)
        self.page.loadFinished.connect(self._on_load_finished)
        
    def login(self):
        self.page.setUrl(QUrl("https://filelist.io/login.php"))
        
    def _on_load_finished(self, ok: bool):
        if not ok: return
        url = self.page.url().toString()
        if "login.php" in url:
            user = os.getenv("FILELIST_USER", "")
            password = os.getenv("FILELIST_PASS", "")
            js = f'''
                (function() {{
                    var u = document.querySelector('input[name="username"]');
                    var p = document.querySelector('input[name="password"]');
                    var c = document.querySelector('input[name="unlock"]');
                    var s = document.querySelector('input[type="submit"]');
                    if(u && p && c) {{ 
                        u.value="{user}"; 
                        p.value="{password}"; 
                        c.checked=true; 
                        s ? s.click() : document.forms[0].submit(); 
                    }}
                }})();
            '''
            self.page.runJavaScript(js)
        elif "index.php" in url or "browse.php" in url or url == "https://filelist.io/":
            self.authenticated.emit()
