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
        
        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet("border-radius: 12px;")
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
            request.stateChanged.connect(
                lambda state: self._on_download_state_changed(state, request, img_url, title)
            )
            
        self.web_view.page().runJavaScript(js_code, js_callback)

    def _on_page_loaded(self, ok: bool) -> None:
        if not ok: 
            return
            
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
                    if(u && p && c) {{ 
                        u.value="{user}"; 
                        p.value="{password}"; 
                        c.checked=true; 
                        s ? s.click() : document.forms[0].submit(); 
                    }}
                }})();
            '''
            self.web_view.page().runJavaScript(js_code)
            
        elif current_url in ["https://filelist.io/", "https://filelist.io/index.php"]:
            self.web_view.setUrl(QUrl("https://filelist.io/browse.php"))

    def _on_download_state_changed(
        self, 
        state: QWebEngineDownloadRequest.DownloadState, 
        request: QWebEngineDownloadRequest, 
        img_url: str, 
        title: str
    ) -> None:
        if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            file_path = request.downloadDirectory() + os.sep + request.downloadFileName()
            self.torrent_downloaded.emit(file_path, img_url, title)
            self.accept()


class MediaCategoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Categorize Media")
        self.setFixedSize(450, 250)
        
        # Modern styling for category dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border-radius: 16px;
            }
            QGroupBox {
                font-weight: 600;
                font-size: 11pt;
                color: #1e293b;
                border: 2px solid #e0e8f0;
                border-radius: 12px;
                padding: 15px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                background-color: #ffffff;
            }
            QRadioButton {
                font-size: 10pt;
                color: #334155;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
            QRadioButton::indicator:checked {
                background-color: #60a5fa;
                border: 2px solid #2563eb;
                border-radius: 9px;
            }
            QRadioButton::indicator:unchecked {
                background-color: #ffffff;
                border: 2px solid #cbd5e1;
                border-radius: 9px;
            }
            QLabel {
                font-size: 10pt;
                color: #475569;
                font-weight: 600;
            }
            QComboBox, QLineEdit {
                padding: 8px 12px;
                border: 2px solid #e0e8f0;
                border-radius: 10px;
                background-color: #f8fafc;
                font-size: 10pt;
                color: #334155;
            }
            QComboBox:focus, QLineEdit:focus {
                border-color: #60a5fa;
                background-color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #64748b;
                margin-right: 8px;
            }
            QPushButton {
                padding: 10px 20px;
                border-radius: 10px;
                font-weight: 600;
                font-size: 10pt;
            }
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(20, 20, 20, 20)

        # Radio button group for media type
        self.radio_group = QGroupBox("Media Type")
        self.radio_layout = QHBoxLayout()
        self.radio_layout.setSpacing(20)
        
        self.btn_movie = QRadioButton("Movies")
        self.btn_tv = QRadioButton("TV-Series")
        self.btn_movie.setChecked(True)
        
        self.radio_layout.addWidget(self.btn_movie)
        self.radio_layout.addWidget(self.btn_tv)
        self.radio_layout.addStretch()
        self.radio_group.setLayout(self.radio_layout)
        self.layout.addWidget(self.radio_group)

        # Form for genre/series selection
        self.form_layout = QFormLayout()
        self.form_layout.setSpacing(12)
        self.form_layout.setContentsMargins(10, 5, 10, 5)
        
        self.genre_dropdown = QComboBox()
        self.genre_dropdown.addItems([
            "action", "adventure", "anime", "comedy", 
            "crime", "drama", "horror", "sf", "thriller"
        ])
        
        self.series_input = QLineEdit()
        self.series_input.setPlaceholderText("e.g. breaking bad")
        self.series_input.hide()
        
        self.form_label_genre = QLabel("Genre:")
        self.form_label_series = QLabel("Series Name:")
        self.form_label_series.hide()

        self.form_layout.addRow(self.form_label_genre, self.genre_dropdown)
        self.form_layout.addRow(self.form_label_series, self.series_input)
        self.layout.addLayout(self.form_layout)

        # Dialog buttons with modern styling
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        
        # Style OK button
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #60a5fa;
                color: #ffffff;
                border: none;
            }
            QPushButton:hover {
                background-color: #3b82f6;
            }
            QPushButton:pressed {
                background-color: #2563eb;
            }
        """)
        
        # Style Cancel button
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #475569;
                border: 2px solid #e0e8f0;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
                border-color: #cbd5e1;
            }
        """)
        
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
    def __init__(
        self, 
        title: str, 
        qbit_state: str, 
        ffmpeg_log: str, 
        illustration_path: str, 
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle(f"Pipeline Details: {title}")
        
        # Modern card-based styling matching mockup
        self.setStyleSheet("""
            QDialog { 
                background-color: #f8fafc; 
                border-radius: 16px;
            }
            QLabel { 
                color: #1e293b; 
                font-family: 'Segoe UI', Arial; 
            }
            QTextEdit { 
                background-color: #ffffff; 
                color: #334155; 
                border: 2px solid #e0e8f0; 
                border-radius: 10px; 
                font-family: 'Consolas', 'Courier New', monospace; 
                font-size: 9pt;
                padding: 10px;
            }
        """)
        self.setFixedSize(650, 420)

        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(25, 25, 25, 25)

        # Left side: Workflow status with illustration
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        left_layout.setSpacing(15)
        
        title_lbl = QLabel("Workflow Status")
        title_lbl.setStyleSheet("""
            font-size: 14pt; 
            font-weight: bold; 
            color: #0f172a;
        """)
        
        # Illustration image
        img_lbl = QLabel()
        if os.path.exists(illustration_path):
            pixmap = QPixmap(illustration_path)
            scaled_pixmap = pixmap.scaled(
                220, 220, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            img_lbl.setPixmap(scaled_pixmap)
        else:
            img_lbl.setText("📊\nWorkflow\nVisualization")
            img_lbl.setStyleSheet("""
                color: #94a3b8;
                font-size: 10pt;
                background-color: #f1f5f9;
                border: 2px dashed #cbd5e1;
                border-radius: 12px;
                padding: 40px;
            """)
            img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Modify button with modern styling
        btn_modify = QPushButton("✎ Modify (Complete)")
        btn_modify.setFixedHeight(40)
        btn_modify.setStyleSheet("""
            QPushButton {
                background-color: #60a5fa;
                color: #ffffff;
                border: none;
                border-radius: 12px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #3b82f6;
            }
            QPushButton:pressed {
                background-color: #2563eb;
            }
        """)
        
        # Add link button
        btn_link = QPushButton("🔗 VIEW & SHARE LINK")
        btn_link.setFixedHeight(40)
        btn_link.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #475569;
                border: 2px solid #cbd5e1;
                border-radius: 12px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
                border-color: #94a3b8;
            }
        """)
        
        left_layout.addWidget(title_lbl)
        left_layout.addWidget(img_lbl)
        left_layout.addStretch()
        left_layout.addWidget(btn_modify)
        left_layout.addWidget(btn_link)

        # Right side: Content details
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_layout.setSpacing(12)
        
        # Header
        det_lbl = QLabel("CONTENT DETAILS")
        det_lbl.setStyleSheet("""
            font-size: 9pt; 
            font-weight: bold; 
            color: #64748b;
            letter-spacing: 1px;
        """)
        
        # Project info card
        project_card = QWidget()
        project_card.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e0e8f0;
                padding: 12px;
            }
        """)
        project_layout = QVBoxLayout(project_card)
        project_layout.setSpacing(8)
        
        # Title
        lbl_title_header = QLabel("Active Target:")
        lbl_title_header.setStyleSheet("font-size: 9pt; color: #64748b; font-weight: 600;")
        lbl_title_val = QLabel(f"[{title}]")
        lbl_title_val.setStyleSheet("""
            background-color: #eff6ff; 
            color: #1e40af;
            border-radius: 6px; 
            padding: 6px 10px;
            font-weight: 600;
        """)
        lbl_title_val.setWordWrap(True)
        
        # Downloader status
        lbl_qbit_header = QLabel("Downloader Tracker:")
        lbl_qbit_header.setStyleSheet("font-size: 9pt; color: #64748b; font-weight: 600;")
        lbl_qbit_val = QLabel(f"[{qbit_state}]")
        lbl_qbit_val.setStyleSheet("""
            background-color: #f0fdf4; 
            color: #166534;
            border-radius: 6px; 
            padding: 6px 10px;
            font-weight: 600;
        """)
        lbl_qbit_val.setWordWrap(True)
        
        project_layout.addWidget(lbl_title_header)
        project_layout.addWidget(lbl_title_val)
        project_layout.addWidget(lbl_qbit_header)
        project_layout.addWidget(lbl_qbit_val)
        
        # FFmpeg log section
        lbl_log_header = QLabel("Recent Telemetry (FFmpeg):")
        lbl_log_header.setStyleSheet("""
            font-size: 9pt; 
            color: #64748b; 
            font-weight: 600;
            margin-top: 8px;
        """)
        
        txt_log = QTextEdit(ffmpeg_log)
        txt_log.setReadOnly(True)
        txt_log.setMinimumHeight(120)

        right_layout.addWidget(det_lbl)
        right_layout.addWidget(project_card)
        right_layout.addWidget(lbl_log_header)
        right_layout.addWidget(txt_log, stretch=1)

        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addLayout(right_layout, stretch=2)
