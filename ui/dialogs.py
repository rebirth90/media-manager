import os
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QComboBox, QRadioButton, QVBoxLayout,
    QPushButton, QTextEdit, QWidget
)

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
        
        state_dict = {"img_url": None, "title": None, "season": None, "completed": False}
        
        def try_finish():
            if state_dict["completed"] and state_dict["title"] is not None:
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

    def closeEvent(self, event) -> None:
        self.profile.downloadRequested.disconnect(self._on_download_requested)
        if self.web_view.page():
            self.web_view.page().deleteLater()
        self.web_view.setPage(None)
        self.web_view.deleteLater()
        super().closeEvent(event)


class MediaCategoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Construct path")
        self.setFixedSize(500, 310)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._is_movie = True

        root = QWidget(self)
        root.setGeometry(0, 0, 500, 310)
        root.setObjectName("card")
        root.setStyleSheet("""
            QWidget#card {
                background-color: #ffffff;
                border-radius: 22px;
                border: 1px solid #dde6ee;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(root)

        layout = QVBoxLayout(root)
        layout.setSpacing(20)
        layout.setContentsMargins(32, 28, 32, 28)

        lbl_title = QLabel("Construct path")
        lbl_title.setStyleSheet(
            "font-size: 16pt; font-weight: 800; color: #0d1f35; letter-spacing: -0.5px;"
        )
        layout.addWidget(lbl_title)

        # Segmented pill control (grey track with blue fill for active)
        seg_track = QWidget()
        seg_track.setFixedHeight(52)
        seg_track.setStyleSheet("QWidget { background-color: #ebebed; border-radius: 26px; }")
        seg_layout = QHBoxLayout(seg_track)
        seg_layout.setContentsMargins(5, 5, 5, 5)
        seg_layout.setSpacing(4)

        self._ss_active = (
            "QPushButton { background-color: #2878e8; color: #ffffff; border: none;"
            " border-radius: 21px; font-weight: 700; font-size: 11pt; padding: 0 10px; }"
        )
        self._ss_inactive = (
            "QPushButton { background-color: transparent; color: #8a9aaa; border: none;"
            " border-radius: 21px; font-weight: 600; font-size: 11pt; padding: 0 10px; }"
        )

        self.btn_movie = QPushButton("🎬  Movie")
        self.btn_tv    = QPushButton("📺  TV-Series")
        for _b in (self.btn_movie, self.btn_tv):
            _b.setCursor(Qt.CursorShape.PointingHandCursor)
            _b.setFixedHeight(42)

        self.btn_movie.setStyleSheet(self._ss_active)
        self.btn_tv.setStyleSheet(self._ss_inactive)
        self.btn_movie.clicked.connect(lambda: self._select_type(True))
        self.btn_tv.clicked.connect(lambda: self._select_type(False))

        seg_layout.addWidget(self.btn_movie, 1)
        seg_layout.addWidget(self.btn_tv, 1)
        layout.addWidget(seg_track)

        _div = QWidget()
        _div.setFixedHeight(1)
        _div.setStyleSheet("background-color: #eaeff4;")
        layout.addWidget(_div)

        # ── Genre dropdown (movie mode) ────────────────────────────
        self.genre_container = QWidget()
        genre_row = QHBoxLayout(self.genre_container)
        genre_row.setContentsMargins(0, 0, 0, 0)
        genre_row.setSpacing(14)

        lbl_genre = QLabel("Genre")
        lbl_genre.setStyleSheet("""
            font-size: 10pt; font-weight: 600; color: #4a6070;
        """)
        lbl_genre.setFixedWidth(72)

        self.genre_dropdown = QComboBox()
        self.genre_dropdown.addItems([
            "action", "adventure", "anime", "comedy",
            "crime", "drama", "horror", "sf", "thriller"
        ])
        self.genre_dropdown.setFixedHeight(42)
        self.genre_dropdown.setStyleSheet("""
            QComboBox {
                background-color: #f4f8fb;
                border: 1.5px solid #c8d8e8;
                border-radius: 12px;
                padding-left: 14px;
                padding-right: 36px;
                font-size: 10pt;
                color: #1e293b;
            }
            QComboBox:focus {
                border-color: #7db8d5;
                background-color: #ffffff;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                width: 32px;
                border-left: 1px solid #dde8f0;
                border-top-right-radius: 12px;
                border-bottom-right-radius: 12px;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #5a7a8a;
                margin-top: 2px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1.5px solid #c8d8e8;
                border-radius: 10px;
                selection-background-color: #e8f4fb;
                selection-color: #0f2847;
                padding: 4px;
                outline: 0;
            }
        """)

        genre_row.addWidget(lbl_genre)
        genre_row.addWidget(self.genre_dropdown, 1)
        layout.addWidget(self.genre_container)

        # ── Series name input (TV mode, hidden by default) ─────────
        self.series_container = QWidget()
        series_row = QHBoxLayout(self.series_container)
        series_row.setContentsMargins(0, 0, 0, 0)
        series_row.setSpacing(14)

        lbl_series = QLabel("Series")
        lbl_series.setStyleSheet("""
            font-size: 10pt; font-weight: 600; color: #4a6070;
        """)
        lbl_series.setFixedWidth(72)

        self.series_input = QLineEdit()
        self.series_input.setPlaceholderText("e.g. breaking bad")
        self.series_input.setFixedHeight(42)
        self.series_input.setStyleSheet("""
            QLineEdit {
                background-color: #f4f8fb;
                border: 1.5px solid #c8d8e8;
                border-radius: 12px;
                padding-left: 14px;
                font-size: 10pt;
                color: #1e293b;
            }
            QLineEdit:focus {
                border-color: #7db8d5;
                background-color: #ffffff;
            }
        """)

        series_row.addWidget(lbl_series)
        series_row.addWidget(self.series_input, 1)
        self.series_container.hide()
        layout.addWidget(self.series_container)

        layout.addStretch()

        # ── Action buttons ─────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(40)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f0f6fa;
                color: #5a7a8a;
                border: 1.5px solid #c8d8e8;
                border-radius: 12px;
                padding: 0 22px;
                font-weight: 600;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #e0edf5;
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("Confirm")
        btn_ok.setFixedHeight(40)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #9dc9e0;
                color: #0f2847;
                border: none;
                border-radius: 12px;
                padding: 0 26px;
                font-weight: 700;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #7db8d5;
            }
            QPushButton:pressed {
                background-color: #6ba8c8;
            }
        """)
        btn_ok.clicked.connect(self.accept)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _select_type(self, is_movie: bool) -> None:
        self._is_movie = is_movie
        self.btn_movie.setStyleSheet(self._ss_active   if is_movie else self._ss_inactive)
        self.btn_tv.setStyleSheet(   self._ss_inactive if is_movie else self._ss_active)
        self.genre_container.setVisible(is_movie)
        self.series_container.setVisible(not is_movie)

    def get_relative_path(self) -> str:
        if self._is_movie:
            return f"movies/{self.genre_dropdown.currentText()}"
        else:
            name = self.series_input.text().strip().replace(" ", ".")
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

from PyQt6.QtWidgets import QCheckBox

class DeleteTorrentDialog(QDialog):
    def __init__(self, torrent_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Delete 1 torrent")
        self.setFixedSize(450, 210)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border-radius: 12px;
            }
            QLabel {
                font-family: 'Segoe UI', Arial;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Name label acting like a readonly input
        self.lbl_name = QLabel(torrent_name)
        self.lbl_name.setStyleSheet("""
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 8px 12px;
            color: #334155;
            font-size: 10pt;
        """)
        self.lbl_name.setWordWrap(True)
        layout.addWidget(self.lbl_name)

        # Hard drive checkbox logic
        chk_layout = QHBoxLayout()
        chk_layout.setSpacing(10)
        
        lbl_disk = QLabel("💾")
        lbl_disk.setStyleSheet("font-size: 14pt; color: #10b981;")
        
        self.chk_delete_files = QCheckBox("Delete files with torrent")
        self.chk_delete_files.setStyleSheet("""
            QCheckBox {
                font-size: 10pt;
                color: #1e293b;
                font-weight: 600;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #cbd5e1;
                background: #ffffff;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #3b82f6;
                background: #60a5fa;
                border-radius: 4px;
            }
        """)
        chk_layout.addWidget(lbl_disk)
        chk_layout.addWidget(self.chk_delete_files)
        chk_layout.addStretch()
        layout.addLayout(chk_layout)

        # Warning
        lbl_warn = QLabel("⚠️ Ticking this checkbox will delete everything contained in those torrents")
        lbl_warn.setStyleSheet("color: #ef4444; font-size: 9pt;")
        lbl_warn.setWordWrap(True)
        layout.addWidget(lbl_warn)

        layout.addStretch()

        # Buttons
        self.button_box = QDialogButtonBox()
        btn_cancel = self.button_box.addButton("CANCEL", QDialogButtonBox.ButtonRole.RejectRole)
        btn_delete = self.button_box.addButton("DELETE", QDialogButtonBox.ButtonRole.AcceptRole)

        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748b;
                border: none;
                font-weight: bold;
                font-size: 10pt;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #f1f5f9; }
        """)
        
        btn_delete.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ef4444;
                border: none;
                font-weight: bold;
                font-size: 10pt;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #fee2e2; }
        """)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.button_box)
        layout.addLayout(btn_layout)

    def should_delete_files(self) -> bool:
        return self.chk_delete_files.isChecked()
