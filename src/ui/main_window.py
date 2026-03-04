import os
from typing import List
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QScrollArea, QLabel, QLineEdit, QGraphicsBlurEffect, QDialog, QApplication, QFrame
)

from src.ui.dialogs.browser_modal import BrowserModalDialog
from src.ui.dialogs.media_category import MediaCategoryDialog
from src.ui.components.media_card import MediaCardWidget
from src.utils.formatting import format_size, format_speed
from PyQt6.QtWebEngineCore import QWebEngineProfile


class SecureServerWindow(QMainWindow):
    def __init__(self, shared_profile, media_controller) -> None:
        super().__init__()
        
        self.shared_profile = shared_profile
        self.media_controller = media_controller
        
        # Wire global controller signals back to UI
        self.media_controller.torrents_updated.connect(self._update_qbit_ui_globally)
        
        self.setWindowTitle("Media Manager - Enterprise Dashboard")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.showMaximized()
        self._is_dragging = False
        self._drag_pos = None
        self._modal_open = False   # Guard: prevent multiple simultaneous Add Item modals
        
        # Refined gradient background inspired by mockup - softer, more professional
        pass

        self.central_w = QWidget()
        self.main_layout = QVBoxLayout(self.central_w)
        self.main_layout.setContentsMargins(0, 0, 0, 25) # Top margin 0 for flush header
        self.main_layout.setSpacing(0)

        # White Header Container
        self.header_container = QWidget()
        self.header_container.setObjectName("HeaderContainer")
        self.header_container.setFixedHeight(72)
        
        # Navigation inside the header
        nav_layout = QHBoxLayout(self.header_container)
        nav_layout.setContentsMargins(30, 0, 30, 0)
        nav_layout.setSpacing(18)
        
        # Add button with refined styling matching mockup
        self.btn_add_torrent = QPushButton("Add item")

        self.btn_add_torrent.setFixedHeight(48)
        self.btn_add_torrent.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_torrent.setObjectName("PrimaryButton")
        self.btn_add_torrent.clicked.connect(self._spawn_browser_modal_with_blur)
        
        # Refined functional search bar matching mockup design
        self.search_bar = SearchBarWidget(self)
        self.search_bar.search_query_changed.connect(self._filter_media_list)

        # Window control buttons
        window_controls = QHBoxLayout()
        window_controls.setSpacing(8)

        self.btn_minimize = QPushButton()
        self.btn_maximize = QPushButton() # Initially maximized state implies restoring next, but we start max
        self.btn_close = QPushButton()

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.icon_min = QIcon(os.path.join(base_dir, "assets", "win_min.svg"))
        self.icon_max = QIcon(os.path.join(base_dir, "assets", "win_max.svg"))
        self.icon_restore = QIcon(os.path.join(base_dir, "assets", "win_restore.svg"))
        self.icon_close = QIcon(os.path.join(base_dir, "assets", "win_close.svg"))

        self.btn_minimize.setIcon(self.icon_min)
        # Assuming the window starts maximized (as it does in main.py, showMaximized)
        self.btn_maximize.setIcon(self.icon_restore) 
        self.btn_close.setIcon(self.icon_close)

        for btn in [self.btn_minimize, self.btn_maximize, self.btn_close]:
            btn.setIconSize(QSize(20, 20))
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setObjectName("WindowControlButton")

        self.btn_close.setObjectName("WindowCloseButton")

        self.btn_minimize.clicked.connect(self.showMinimized)
        self.btn_maximize.clicked.connect(self._toggle_maximize)
        self.btn_close.clicked.connect(self.close)

        window_controls.addWidget(self.btn_minimize)
        window_controls.addWidget(self.btn_maximize)
        window_controls.addWidget(self.btn_close)

        nav_layout.addWidget(self.btn_add_torrent)
        nav_layout.addStretch(1)
        nav_layout.addWidget(self.search_bar)
        nav_layout.addStretch(1)           # Equal stretch after search → centers the bar

        nav_layout.addLayout(window_controls)

        self.main_layout.addWidget(self.header_container)

        # Main content container with enhanced card styling
        self.canvas_container = QWidget()
        self.canvas_container.setObjectName("CanvasContainer")
        canvas_layout = QVBoxLayout(self.canvas_container)
        canvas_layout.setContentsMargins(50, 35, 50, 28)
        canvas_layout.setSpacing(18)

        # Scrollable content area with custom scrollbar
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        pass
        
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
        
        self.all_flows: List[MediaCardWidget] = []
        
        from src.models.local_db import LocalDBManager
        self.db_manager = LocalDBManager()
        self._restore_saved_flows()

    def _restore_saved_flows(self) -> None:
        try:
            items = self.db_manager.get_all_items()
            for row in items:
                index = len(self.all_flows) + 1
                flow = MediaCardWidget(
                    index=index,
                    relative_path=row["relative_path"],
                    title=row["title"],
                    season=row.get("season", ""),
                    parent=self.scroll_content
                )
                
                # Wire signals
                flow.delete_confirmed.connect(self._on_flow_delete)
                
                self.all_flows.append(flow)
                self.flows_layout.addWidget(flow)
                
                self.media_controller.add_media_flow(
                    flow_index=index,
                    title=row["title"],
                    relative_path=row["relative_path"],
                    torrent_bytes=b"",
                    image_url=row.get("image_url", ""),
                    is_restored=True
                )
        except Exception as e:
            print(f"Failed to restore media flows: {e}")

    def _spawn_browser_modal_with_blur(self) -> None:
        # Guard: only one browser modal at a time
        if self._modal_open:
            return
        self._modal_open = True
        try:
            blur_effect = QGraphicsBlurEffect()
            blur_effect.setBlurRadius(25)
            self.canvas_container.setGraphicsEffect(blur_effect)

            dialog = BrowserModalDialog(self.shared_profile, self)
            dialog.torrent_downloaded.connect(self._process_downloaded_torrent)
            dialog.exec()
        finally:
            self.canvas_container.setGraphicsEffect(None)
            self._modal_open = False

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

                # Add to local db
                db_id = self.db_manager.add_item(
                    relative_path=relative_path,
                    image_url=img_url,
                    title=title,
                    season=season
                )

                index = len(self.all_flows) + 1
                flow = MediaCardWidget(
                    index=index,
                    relative_path=relative_path,
                    title=title,
                    season=season,
                    parent=self.scroll_content
                )
                
                # Wire signals
                flow.delete_confirmed.connect(self._on_flow_delete)

                self.all_flows.append(flow)
                self.flows_layout.addWidget(flow)
                
                self.media_controller.add_media_flow(
                    flow_index=index,
                    title=title,
                    relative_path=relative_path,
                    torrent_bytes=torrent_bytes,
                    image_url=img_url,
                    is_restored=False
                )
            # Cancelled: no error, nothing to do
        except Exception as e:
            print(f"Error instantiating pipeline: {e}")
        finally:
            self.canvas_container.setGraphicsEffect(None)
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass

    def _on_flow_delete(self, hashes: List[str], delete_files: bool, flow_widget: object) -> None:
        self.media_controller.request_deletion(hashes, delete_files)
        # remove flow from ui
        if hasattr(flow_widget, 'close_flow'):
            flow_widget.close_flow()
        flow_widget.close()
        if flow_widget in self.all_flows:
            self.all_flows.remove(flow_widget)
        self.flows_layout.removeWidget(flow_widget)

    def _update_qbit_ui_globally(self, torrents_list: list) -> None:
        for flow in self.all_flows:
            matched_t = None
            target_suffix = flow.relative_path.replace("\\", "/")
            
            for t in torrents_list:
                sp = t.get('save_path', '').replace("\\", "/")
                # Ensure the folder structure matches our target
                if sp.endswith(target_suffix) or target_suffix in sp:
                    matched_t = t
                    break
                    
            if matched_t:
                flow._current_hash = matched_t.get('hash', '')
                prog_val = matched_t.get('progress', 0.0)
                state = matched_t.get('state', 'Unknown')
                dlspeed = matched_t.get('dlspeed', 0)
                size = matched_t.get('size', 0)
                
                is_done = state in ['uploading', 'stalledUP', 'pausedUP', 'completed', 'stalledDL'] and prog_val == 1.0
                human_state = "Unknown"
                
                if is_done or prog_val == 1.0:
                    human_state = "Completed"
                    state_css = "PillSuccess"
                    pb_style = "PbSuccess"
                elif state in ['downloading', 'stalledDL'] and prog_val < 1.0:
                    human_state = "Downloading"
                    state_css = "PillActive"
                    pb_style = "PbActive"
                elif state in ['pausedDL', 'stopped', 'stoppedDL', 'checkingDL', 'checkingUP']:
                    human_state = "Stopped"
                    state_css = "PillUnknown"
                    pb_style = "PbUnknown"
                else:
                    human_state = state.capitalize()
                    state_css = "PillWarning"
                    pb_style = "PbWarning"

                active_state_str = f"State: {human_state} | Progress: {int(prog_val * 100)}% | Size: {format_size(size)}"
                
                flow.update_torrent_ui(
                    human_state=human_state,
                    state_css=state_css,
                    pb_style=pb_style,
                    prog_val=prog_val,
                    size_str=format_size(size),
                    speed_str=format_speed(dlspeed),
                    active_state_str=active_state_str
                )

    def _filter_media_list(self, query: str) -> None:
        """Filter the displayed list of media cards based on the search query."""
        query = query.lower().strip()
        for flow in self.all_flows:
            title = flow.title_lbl.text().lower()
            if not query or query in title:
                flow.setVisible(True)
            else:
                flow.setVisible(False)

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
