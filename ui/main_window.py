import os
from typing import List
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QScrollArea, QLabel, QLineEdit, QGraphicsBlurEffect, QDialog, QApplication
)

from ui.dialogs import BrowserModalDialog, MediaCategoryDialog
from ui.media_flow import MediaFlowWidget
from services.filelist_auth import FilelistAuthenticator
from PyQt6.QtWebEngineCore import QWebEngineProfile

class SecureServerWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        
        cache_dir = os.path.join(os.getcwd(), ".qt_cache")
        os.makedirs(cache_dir, exist_ok=True)
        
        self.shared_profile = QWebEngineProfile("filelist_auth", self)
        self.shared_profile.setPersistentStoragePath(cache_dir)
        self.shared_profile.setCachePath(cache_dir)
        self.auth_manager = FilelistAuthenticator(self.shared_profile, self)
        self.auth_manager.login()
        
        self.setWindowTitle("Media Manager - Enterprise Dashboard")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.showMaximized()
        self._is_dragging = False
        self._drag_pos = None
        
        # Refined gradient background inspired by mockup - softer, more professional
        self.setStyleSheet("""
            QMainWindow { 
                background-color: #ffffff;
                font-family: 'Segoe UI', 'San Francisco', 'Helvetica Neue', Arial, sans-serif; 
            }
        """)

        self.central_w = QWidget()
        self.main_layout = QVBoxLayout(self.central_w)
        self.main_layout.setContentsMargins(0, 0, 0, 25) # Top margin 0 for flush header
        self.main_layout.setSpacing(0)

        # White Header Container
        self.header_container = QWidget()
        self.header_container.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-bottom: 1px solid #e1e4e8;
            }
        """)
        self.header_container.setFixedHeight(72)
        
        # Navigation inside the header
        nav_layout = QHBoxLayout(self.header_container)
        nav_layout.setContentsMargins(30, 0, 30, 0)
        nav_layout.setSpacing(18)
        
        # Add button with refined styling matching mockup
        self.btn_add_torrent = QPushButton("+ Movie / TV-Series")
        self.btn_add_torrent.setFixedHeight(48)
        self.btn_add_torrent.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_torrent.setStyleSheet("""
            QPushButton { 
                background-color: #9dc9e0; 
                color: #0f2847; 
                border: none; 
                border-radius: 24px; 
                padding: 0 28px; 
                font-weight: 600; 
                font-size: 11.5pt;
            }
            QPushButton:hover { 
                background-color: #7db8d5; 
                color: #081a2e; 
            }
            QPushButton:pressed {
                background-color: #6ba8c8;
            }
        """)
        self.btn_add_torrent.clicked.connect(self._spawn_browser_modal_with_blur)
        
        # Refined search bar matching mockup design
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search")
        self.search_bar.setFixedHeight(48)
        self.search_bar.setMaximumWidth(480)
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                border: 2px solid #c8d8e8;
                border-radius: 24px;
                padding-left: 24px;
                padding-right: 24px;
                font-size: 10.5pt;
                color: #3d4f60;
            }
            QLineEdit:focus {
                border: 2px solid #7db8d5;
                background-color: #fcfdff;
            }
            QLineEdit::placeholder {
                color: #a0b0c0;
            }
        """)

        # Window control buttons
        window_controls = QHBoxLayout()
        window_controls.setSpacing(8)

        self.btn_minimize = QPushButton()
        self.btn_maximize = QPushButton() # Initially maximized state implies restoring next, but we start max
        self.btn_close = QPushButton()

        import os
        from PyQt6.QtGui import QIcon
        from PyQt6.QtCore import QSize
        
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.icon_min = QIcon(os.path.join(base_dir, "assets", "win_min.svg"))
        self.icon_max = QIcon(os.path.join(base_dir, "assets", "win_max.svg"))
        self.icon_restore = QIcon(os.path.join(base_dir, "assets", "win_restore.svg"))
        self.icon_close = QIcon(os.path.join(base_dir, "assets", "win_close.svg"))

        self.btn_minimize.setIcon(self.icon_min)
        # Assuming the window starts maximized (as it does in main.py, showMaximized)
        self.btn_maximize.setIcon(self.icon_restore) 
        self.btn_close.setIcon(self.icon_close)

        for btn in [self.btn_minimize, self.btn_maximize, self.btn_close]:
            btn.setIconSize(QSize(18, 18))
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 18px;
                }
                QPushButton:hover {
                    background-color: #f0f6fa;
                }
            """)

        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 18px;
            }
            QPushButton:hover {
                background-color: #ffe6e6;
            }
        """)

        self.btn_minimize.clicked.connect(self.showMinimized)
        self.btn_maximize.clicked.connect(self._toggle_maximize)
        self.btn_close.clicked.connect(self.close)

        window_controls.addWidget(self.btn_minimize)
        window_controls.addWidget(self.btn_maximize)
        window_controls.addWidget(self.btn_close)

        nav_layout.addWidget(self.btn_add_torrent)
        nav_layout.addStretch()
        nav_layout.addWidget(self.search_bar)
        nav_layout.addStretch()
        nav_layout.addLayout(window_controls)

        self.main_layout.addWidget(self.header_container)

        # Main content container with enhanced card styling
        self.canvas_container = QWidget()
        self.canvas_container.setStyleSheet("""
            QWidget {
                background-color: #f8fbfe;
                border-radius: 12px;
            }
        """)
        canvas_layout = QVBoxLayout(self.canvas_container)
        canvas_layout.setContentsMargins(50, 35, 50, 28)
        canvas_layout.setSpacing(18)

        # Scrollable content area with custom scrollbar
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background-color: transparent; 
            }
            QScrollBar:vertical {
                background: #f0f6fa;
                width: 14px;
                border-radius: 7px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #b0c8d8;
                border-radius: 7px;
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover {
                background: #90b0c8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")
        self.flows_layout = QVBoxLayout(self.scroll_content)
        self.flows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.flows_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.scroll_content)
        canvas_layout.addWidget(self.scroll_area)
        self.main_layout.addWidget(self.canvas_container)
        
        # Removed exit fullscreen button
        
        self.setCentralWidget(self.central_w)
        
        self.all_flows: List[MediaFlowWidget] = []

    def _spawn_browser_modal_with_blur(self) -> None:
        # Enhanced blur effect
        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(25)
        self.canvas_container.setGraphicsEffect(blur_effect)

        dialog = BrowserModalDialog(self.shared_profile, self)
        dialog.torrent_downloaded.connect(self._process_downloaded_torrent)
        dialog.exec()
        
        # Remove blur
        self.canvas_container.setGraphicsEffect(None)

    def _process_downloaded_torrent(self, file_path: str, img_url: str, title: str, season: str = "") -> None:
        try:
            blur_effect = QGraphicsBlurEffect()
            blur_effect.setBlurRadius(25)
            self.canvas_container.setGraphicsEffect(blur_effect)

            dialog = MediaCategoryDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                relative_path = dialog.get_relative_path()
                with open(file_path, "rb") as f:
                    torrent_bytes = f.read()

                index = len(self.all_flows) + 1
                flow = MediaFlowWidget(index, relative_path, torrent_bytes, img_url, title, season, self.scroll_content)
                self.all_flows.append(flow)
                self.flows_layout.addWidget(flow)
                
        except Exception as e:
            print(f"Error instantiating pipeline: {e}")
        finally:
            self.canvas_container.setGraphicsEffect(None)
            if os.path.exists(file_path):
                os.remove(file_path)

    def closeEvent(self, event) -> None:
        for flow in self.all_flows:
            flow.close_flow()
            
        if hasattr(self, 'shared_profile'):
            self.shared_profile.deleteLater()
            
        super().closeEvent(event)
        
        # Hard exit to completely kill Uvicorn background threads and drop Chromium locks
        QApplication.quit()
        os._exit(0)

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
            self.btn_maximize.setIcon(self.icon_max)
        else:
            self.showMaximized()
            self.btn_maximize.setIcon(self.icon_restore)

    def mousePressEvent(self, event) -> None:
        from PyQt6.QtCore import Qt
        if event.button() == Qt.MouseButton.LeftButton and event.pos().y() < 72:
            self._is_dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        from PyQt6.QtCore import Qt
        if self._is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            if self.isMaximized():
                self.showNormal()
                self.btn_maximize.setText("🗖")
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._is_dragging = False
        super().mouseReleaseEvent(event)
