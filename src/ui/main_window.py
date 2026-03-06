import os
from typing import List
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QScrollArea, QLabel, QLineEdit, QGraphicsBlurEffect, QDialog, QApplication, QFrame,
    QButtonGroup
)

from src.ui.dialogs.browser_modal import BrowserModalDialog
from src.ui.dialogs.media_category import MediaCategoryDialog
from src.ui.components.media_card import MediaCardWidget
from src.ui.components.search_bar import SearchBarWidget
from src.utils.formatting import format_size, format_speed
from PyQt6.QtWebEngineCore import QWebEngineProfile


class SecureServerWindow(QMainWindow):
    def __init__(self, shared_profile, media_controller) -> None:
        super().__init__()
        
        self.shared_profile = shared_profile
        self.media_controller = media_controller
        
        # Wire global controller signals back to UI
        self.media_controller.torrents_updated.connect(self._update_qbit_ui_globally)
        self.media_controller.title_resolved.connect(self._on_title_resolved)
        self.media_controller.details_resolved.connect(self._on_details_resolved)
        self.media_controller.image_downloaded.connect(self._on_image_downloaded)
        self.media_controller.ssh_telemetry_updated.connect(self._on_ssh_telemetry_updated)
        
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
        
        # Movies / TV Series Toggle
        from src.ui.components.animated_toggle import AnimatedToggle
        self.animated_toggle = AnimatedToggle("Movies", "TV Series")
        self.animated_toggle.setFixedHeight(48)
        self.animated_toggle.setMinimumWidth(216)
        
        self.current_media_filter = "Movies"
        self.animated_toggle.toggled.connect(self._on_media_toggle_changed)
        
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
        nav_layout.addWidget(self.animated_toggle)
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
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollArea > QWidget { background: transparent; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        self.scroll_content.setStyleSheet("QWidget#ScrollContent { background-color: #0A0B0E; }")
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
                season_val = row.get("season", "")
                
                from src.ui.components.media_card import MediaCardWidget, SeriesCardWidget
                
                if season_val:
                    flow = SeriesCardWidget(
                        index=index,
                        relative_path=row["relative_path"],
                        title=row["title"],
                        season=season_val,
                        db_id=row["id"],
                        parent=self.scroll_content
                    )
                else:
                    flow = MediaCardWidget(
                        index=index,
                        relative_path=row["relative_path"],
                        title=row["title"],
                        season="",
                        db_id=row["id"],
                        parent=self.scroll_content
                    )
                
                # Wire signals
                flow.delete_confirmed.connect(self._on_flow_delete)
                
                self.all_flows.append(flow)
                self.flows_layout.addWidget(flow)
                
                # Inject cached data if available
                import json
                
                # Start SSH telemetry — defer if title is still a raw TMDB ID
                raw_title = row["title"]
                if raw_title.startswith("tmdb:"):
                    # Re-use the TMDB fetcher to get the resolved title, then start telemetry
                    try:
                        _, media_type, tmdb_id = raw_title.split(":", 2)
                        from src.core.tmdb_fetcher import TMDBFetcherThread
                        restore_fetcher = TMDBFetcherThread(tmdb_id, media_type, self)
                        restore_fetcher.title_resolved.connect(
                            lambda resolved, idx=index: self.media_controller.start_ssh_telemetry(idx, resolved)
                        )
                        restore_fetcher.start()
                    except Exception:
                        pass  # Skip telemetry for malformed tmdb: titles
                else:
                    self.media_controller.start_ssh_telemetry(index, raw_title)
                        
                # Check torrent cache
                tor_cache = self.db_manager.get_torrent_cache_by_path(row["relative_path"].replace("\\", "/"))
                if tor_cache:
                    try:
                        matched_t = json.loads(tor_cache)
                        flow._current_hash = matched_t.get('hash', '')
                        flow._current_torrent_name = matched_t.get('name', '')
                        size = matched_t.get('size', 0)
                        active_state_str = f"State: Completed | Progress: 100% | Size: {format_size(size)}"
                        flow.update_torrent_ui(
                            human_state="Completed",
                            pill_class="PillSuccess",
                            pb_style="PbSuccess",
                            prog_val=1.0,
                            size_str=format_size(size),
                            speed_str="-",
                            active_state_str=active_state_str
                        )
                    except json.JSONDecodeError:
                        pass
                
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
            self._update_maximize_icon()

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
                
                from src.ui.components.media_card import MediaCardWidget, SeriesCardWidget
                if season:
                    flow = SeriesCardWidget(
                        index=index,
                        relative_path=relative_path,
                        title=title,
                        season=season,
                        db_id=db_id,
                        parent=self.scroll_content
                    )
                else:
                    flow = MediaCardWidget(
                        index=index,
                        relative_path=relative_path,
                        title=title,
                        season="",
                        db_id=db_id,
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
            self._update_maximize_icon()
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass

    def _on_flow_delete(self, hashes: List[str], delete_files: bool, flow_widget: object) -> None:
        self.media_controller.request_deletion(hashes, delete_files)
        
        # Remove item logically from SQLite
        if getattr(flow_widget, 'db_id', None) is not None:
            self.db_manager.delete_item(flow_widget.db_id)
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
                flow._current_torrent_name = matched_t.get('name', '')
                prog_val = matched_t.get('progress', 0.0)
                state = matched_t.get('state', 'Unknown')
                dlspeed = matched_t.get('dlspeed', 0)
                size = matched_t.get('size', 0)
                
                QBIT_STATE_MAP = {
                    # ── Downloading group (Blue) ──────────────────────────────────
                    "downloading":          ("Downloading",   "PillDownloading", "PbActive"),
                    "stalledDL":            ("Stalled",       "PillDownloading", "PbActive"),
                    "forcedDL":             ("Forced DL",     "PillDownloading", "PbActive"),
                    "metaDL":               ("Fetching Meta", "PillDownloading", "PbActive"),
                    "moving":               ("Moving",        "PillDownloading", "PbActive"),
                    # ── Seeding / Completed group (Green) ────────────────────
                    "uploading":            ("Seeding",       "PillSuccess",     "PbSuccess"),
                    "stalledUP":            ("Stalled",       "PillSuccess",     "PbSuccess"),
                    "forcedUP":             ("Forced UP",     "PillSuccess",     "PbSuccess"),
                    # ── Completed ───────────────────────────────────────────
                    "completed":            ("Completed",     "PillSuccess",     "PbSuccess"),
                    # ── Paused group (Amber) ─────────────────────────────────
                    "pausedDL":             ("Paused",        "PillPaused",      "PbUnknown"),
                    "pausedUP":             ("Paused",        "PillPaused",      "PbUnknown"),
                    # ── Checking / Processing group (Teal) ───────────────────
                    "checkingDL":           ("Checking",      "PillChecking",    "PbUnknown"),
                    "checkingUP":           ("Checking",      "PillChecking",    "PbUnknown"),
                    "checkingResumeData":   ("Checking",      "PillChecking",    "PbUnknown"),
                    "allocating":           ("Allocating",    "PillChecking",    "PbUnknown"),
                    # ── Queued / Stopped group (Grey) ────────────────────────
                    "queuedDL":             ("Queued",        "PillQueued",      "PbUnknown"),
                    "queuedUP":             ("Queued",        "PillQueued",      "PbUnknown"),
                    "stopped":              ("Stopped",       "PillQueued",      "PbUnknown"),
                    "stoppedDL":            ("Stopped",       "PillQueued",      "PbUnknown"),
                    "unknown":              ("Unknown",       "PillUnknown",     "PbUnknown"),
                    # ── Error group (Red) ─────────────────────────────────────
                    "missingFiles":         ("Missing Files", "PillDanger",      "PbUnknown"),
                    "error":                ("Error",         "PillDanger",      "PbUnknown"),
                }

                if prog_val == 1.0:
                    human_state, pill_class, pb_style = "Completed", "PillSuccess", "PbSuccess"
                    import json
                    
                    target_path = flow.relative_path.replace("\\", "/")
                    if not self.db_manager.get_torrent_cache_by_path(target_path):
                        self.db_manager.set_torrent_cache(matched_t.get("hash", ""), target_path, json.dumps(matched_t))
                        self.media_controller.request_conversion(flow.relative_path)
                else:
                    fallback = (state.replace("DL","").replace("UP","").strip().capitalize(), "PillWarning", "PbWarning")
                    human_state, pill_class, pb_style = QBIT_STATE_MAP.get(state, fallback)

                active_state_str = f"State: {human_state} | Progress: {int(prog_val * 100)}% | Size: {format_size(size)}"
                flow.update_torrent_ui(
                    human_state=human_state,
                    pill_class=pill_class,
                    pb_style=pb_style,
                    prog_val=prog_val,
                    size_str=format_size(size),
                    speed_str=format_speed(dlspeed),
                    active_state_str=active_state_str
                )

    def _on_title_resolved(self, flow_index: int, title: str) -> None:
        for flow in self.all_flows:
            if flow.flow_index == flow_index:
                flow.title_lbl.setText(title)
                # Persist the human-readable title back to DB so future restores work correctly
                if hasattr(flow, 'db_id') and flow.db_id and str(flow.title_lbl.text()).startswith("tmdb:"):
                    self.db_manager.update_item_title(flow.db_id, title)
                elif hasattr(flow, 'db_id') and flow.db_id:
                    # Check if the stored DB title is still a tmdb: string
                    all_items = self.db_manager.get_all_items()
                    for item in all_items:
                        if item['id'] == flow.db_id and item['title'].startswith('tmdb:'):
                            self.db_manager.update_item_title(flow.db_id, title)
                            break
                break

    def _on_details_resolved(self, flow_index: int, details: dict) -> None:
        for flow in self.all_flows:
            if flow.flow_index == flow_index:
                desc = details.get("description", "No description available.")
                genre = details.get("genre", "Unknown")
                rating = details.get("rating", "-")
                
                # Keep current title, just update metadata fields
                current_title = flow.title_lbl.text()
                flow.update_metadata(current_title, desc, genre, rating)
                break

    def _on_image_downloaded(self, flow_index: int, image_bytes: bytes) -> None:
        for flow in self.all_flows:
            if flow.flow_index == flow_index:
                from PyQt6.QtGui import QPixmap
                pixmap = QPixmap()
                if pixmap.loadFromData(image_bytes):
                    flow.set_poster_pixmap(pixmap)
                break

    def _on_ssh_telemetry_updated(self, flow_index: int, json_payload: str) -> None:
        import json
        try:
            episodes_data = json.loads(json_payload)
        except Exception as e:
            print(f"Failed to parse telemetry JSON: {e}")
            episodes_data = []

        for flow in self.all_flows:
            if flow.flow_index == flow_index:
                # Pass the raw array down to the card to handle
                flow.update_telemetry_ui(episodes_data)
                
                # Check for completion to cache payload
                all_finished = True
                for ep in episodes_data:
                    state = ep.get("db_status", "NOT STARTED").upper()
                    if state not in ["COMPLETED", "FAILED", "REJECTED"]:
                        all_finished = False
                        break
                        
                if all_finished and episodes_data:
                    self.db_manager.set_conversion_cache(flow.relative_path.replace("\\", "/"), json.dumps(episodes_data))
                    
                break

    def _on_media_toggle_changed(self, index: int) -> None:
        self.current_media_filter = "Movies" if index == 0 else "TV Series"
        self._filter_media_list(self.search_bar.get_query())

    def _filter_media_list(self, query: str) -> None:
        """Filter the displayed list of media cards based on search and toggle category."""
        query = query.lower().strip()
        for flow in self.all_flows:
            title = flow.title_lbl.text().lower()
            matches_search = not query or query in title
            
            is_tv = bool(hasattr(flow, 'season') and getattr(flow, 'season'))
            matches_category = (self.current_media_filter == "TV Series" and is_tv) or \
                               (self.current_media_filter == "Movies" and not is_tv)
            
            if matches_search and matches_category:
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
        else:
            self.showMaximized()
        self._update_maximize_icon()

    def _update_maximize_icon(self) -> None:
        self.btn_maximize.setText("")
        if self.isMaximized():
            self.btn_maximize.setIcon(self.icon_restore)
        else:
            self.btn_maximize.setIcon(self.icon_max)

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
                self.btn_maximize.setText("")
                self.btn_maximize.setIcon(self.icon_max)
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._is_dragging = False
        super().mouseReleaseEvent(event)
