import os
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QComboBox, QRadioButton, QVBoxLayout,
    QPushButton, QTextEdit
)

class BrowserModalDialog(QDialog):
    torrent_downloaded = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filelist Torrents Modal Browser")
        self.setStyleSheet("background-color: #1a1c23;")
        
        screen = QApplication.primaryScreen().geometry()
        self.resize(int(screen.width() * 0.75), int(screen.height() * 0.75))

        layout = QVBoxLayout(self)
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

        profile = self.web_view.page().profile()
        profile.downloadRequested.connect(self._on_download_requested)
        self.web_view.page().loadFinished.connect(self._on_page_loaded)

        self.web_view.setUrl(QUrl("https://filelist.io/login.php"))
        self._current_request = None

    def _on_download_requested(self, request: QWebEngineDownloadRequest) -> None:
        self._current_request = request
        
        js_code = """
            (function() {
                var img = document.querySelector("img[src*='tmdb.org']") || document.querySelector("img[src*='imdb.com']");
                var title = document.title || "";
                return { imageUrl: img ? img.src : "", title: title };
            })();
        """
        
        def js_callback(result):
            img_url = result.get('imageUrl', '') if isinstance(result, dict) else ''
            title = result.get('title', 'Unknown Media') if isinstance(result, dict) else 'Unknown Media'
            
            temp_dir = os.path.join(os.getcwd(), "temp_torrents")
            os.makedirs(temp_dir, exist_ok=True)
            request.setDownloadDirectory(temp_dir)
            
            request.accept()
            request.stateChanged.connect(lambda state: self._on_download_state_changed(state, request, img_url, title))
            
        self.web_view.page().runJavaScript(js_code, js_callback)

    def _on_page_loaded(self, ok: bool) -> None:
        if not ok: return
        current_url = self.web_view.url().toString()
        if "login.php" in current_url:
            user = os.getenv("FILELIST_USER", "")
            password = os.getenv("FILELIST_PASS", "")
            js_code = f'''
                (function() {{
                    var u = document.querySelector('input[name="username"]');
                    var p = document.querySelector('input[name="password"]');
                    var c = document.querySelector('input[name="unlock"]');
                    var s = document.querySelector('input[type="submit"]');
                    if(u && p && c) {{ u.value="{user}"; p.value="{password}"; c.checked=true; s ? s.click() : document.forms[0].submit(); }}
                }})();
            '''
            self.web_view.page().runJavaScript(js_code)
        elif current_url in ["https://filelist.io/", "https://filelist.io/index.php"]:
            self.web_view.setUrl(QUrl("https://filelist.io/browse.php"))

    def _on_download_state_changed(self, state: QWebEngineDownloadRequest.DownloadState, request: QWebEngineDownloadRequest, img_url: str, title: str) -> None:
        if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            file_path = request.downloadDirectory() + os.sep + request.downloadFileName()
            self.torrent_downloaded.emit(file_path, img_url, title)
            self.accept()


class MediaCategoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Categorize Intersected Media")
        self.setFixedSize(400, 200)
        self.layout = QVBoxLayout(self)

        self.radio_group = QGroupBox("Media Type")
        self.radio_layout = QHBoxLayout()
        self.btn_movie = QRadioButton("Movies")
        self.btn_tv = QRadioButton("TV-Series")
        self.btn_movie.setChecked(True)
        self.radio_layout.addWidget(self.btn_movie)
        self.radio_layout.addWidget(self.btn_tv)
        self.radio_group.setLayout(self.radio_layout)
        self.layout.addWidget(self.radio_group)

        self.form_layout = QFormLayout()
        self.genre_dropdown = QComboBox()
        self.genre_dropdown.addItems(["action", "adventure", "anime", "comedy", "crime", "drama", "horror", "sf", "thriller"])
        self.series_input = QLineEdit()
        self.series_input.setPlaceholderText("e.g. breaking bad")
        self.series_input.hide()
        
        self.form_label_genre = QLabel("Genre:")
        self.form_label_series = QLabel("Series Name:")
        self.form_label_series.hide()

        self.form_layout.addRow(self.form_label_genre, self.genre_dropdown)
        self.form_layout.addRow(self.form_label_series, self.series_input)
        self.layout.addLayout(self.form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.btn_movie.toggled.connect(self._toggle_inputs)

    def _toggle_inputs(self) -> None:
        if self.btn_movie.isChecked():
            self.series_input.hide()
            self.form_label_series.hide()
            self.genre_dropdown.show()
            self.form_label_genre.show()
        else:
            self.genre_dropdown.hide()
            self.form_label_genre.hide()
            self.series_input.show()
            self.form_label_series.show()

    def get_relative_path(self) -> str:
        if self.btn_movie.isChecked():
            return f"movies/{self.genre_dropdown.currentText()}"
        else:
            name = self.series_input.text().strip().lower().replace(" ", "_")
            return f"tv-series/{name if name else 'unknown_series'}"


class FlowDetailsModal(QDialog):
    def __init__(self, title: str, qbit_state: str, ffmpeg_log: str, illustration_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"PIPELINE DETAILS: {title}")
        self.setStyleSheet("""
            QDialog { background-color: #f8fafc; border-radius: 12px; }
            QLabel { color: #1e293b; font-family: 'Segoe UI', Arial; }
            QTextEdit { background-color: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; font-family: monospace; font-size: 9pt; }
        """)
        self.setFixedSize(550, 350)

        main_layout = QHBoxLayout(self)

        # Left: Isometric Illustration Area
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        title_lbl = QLabel("Workflow Status")
        title_lbl.setStyleSheet("font-size: 14pt; font-weight: bold; color: #0f172a;")
        
        img_lbl = QLabel()
        if os.path.exists(illustration_path):
            pixmap = QPixmap(illustration_path)
            scaled_pixmap = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            img_lbl.setPixmap(scaled_pixmap)
        
        btn_modify = QPushButton("Modify Settings")
        btn_modify.setStyleSheet("background-color: #60a5fa; color: white; border-radius: 8px; padding: 8px; font-weight: bold;")
        
        left_layout.addWidget(title_lbl)
        left_layout.addWidget(img_lbl)
        left_layout.addStretch()
        left_layout.addWidget(btn_modify)

        # Right: Content Details Area
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        det_lbl = QLabel("CONTENT DETAILS")
        det_lbl.setStyleSheet("font-size: 10pt; font-weight: bold; color: #475569;")
        
        lbl_title_header = QLabel("Active Target:")
        lbl_title_val = QLabel(f"[{title}]")
        lbl_title_val.setStyleSheet("background-color: #e2e8f0; border-radius: 4px; padding: 4px;")
        
        lbl_qbit_header = QLabel("Downloader Tracker:")
        lbl_qbit_val = QLabel(f"[{qbit_state}]")
        lbl_qbit_val.setStyleSheet("background-color: #e2e8f0; border-radius: 4px; padding: 4px;")
        
        lbl_log_header = QLabel("Recent Telemetry (FFmpeg):")
        txt_log = QTextEdit(ffmpeg_log)
        txt_log.setReadOnly(True)

        right_layout.addWidget(det_lbl)
        right_layout.addSpacing(10)
        right_layout.addWidget(lbl_title_header)
        right_layout.addWidget(lbl_title_val)
        right_layout.addSpacing(5)
        right_layout.addWidget(lbl_qbit_header)
        right_layout.addWidget(lbl_qbit_val)
        right_layout.addSpacing(5)
        right_layout.addWidget(lbl_log_header)
        right_layout.addWidget(txt_log, stretch=1)

        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addSpacing(20)
        main_layout.addLayout(right_layout, stretch=2)
