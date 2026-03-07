import os
import json
from typing import List
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
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
        
        self.media_controller.torrents_updated.connect(self._update_qbit_db_globally)
        self.media_controller.title_resolved.connect(self._on_title_resolved)
        self.media_controller.details_resolved.connect(self._on_details_resolved)
        self.media_controller.image_downloaded.connect(self._on_image_downloaded)
        self.media_controller.ssh_telemetry_updated.connect(self._on_ssh_telemetry_updated)
        
        self.setWindowTitle("Media Manager - Enterprise Dashboard")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.showMaximized()
        self._is_dragging = False
        self._drag_pos = None
        self._modal_open = False
        
        self.central_w = QWidget()
        self.main_layout = QVBoxLayout(self.central_w)
        self.main_layout.setContentsMargins(0, 0, 0, 25)
        self.main_layout.setSpacing(0)

        self.header_container = QWidget()
        self.header_container.setObjectName("HeaderContainer")
        self.header_container.setFixedHeight(72)
        
        nav_layout = QHBoxLayout(self.header_container)
        nav_layout.setContentsMargins(30, 0, 30, 0)
        nav_layout.setSpacing(18)
        
        self.btn_add_torrent = QPushButton("Add item")
        self.btn_add_torrent.setFixedHeight(48)
        self.btn_add_torrent.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_torrent.setObjectName("PrimaryButton")
        self.btn_add_torrent.clicked.connect(self._spawn_browser_modal_with_blur)
        
        from src.ui.components.animated_toggle import AnimatedToggle
        self.animated_toggle = AnimatedToggle("Movies", "TV Series")
        self.animated_toggle.setFixedHeight(48)
        self.animated_toggle.setMinimumWidth(216)
        
        self.current_media_filter = "Movies"
        self.animated_toggle.toggled.connect(self._on_media_toggle_changed)
        
        self.search_bar = SearchBarWidget(self)
        self.search_bar.search_query_changed.connect(self._filter_media_list)

        window_controls = QHBoxLayout()
        window_controls.setSpacing(8)

        self.btn_minimize = QPushButton()
        self.btn_maximize = QPushButton()
        self.btn_close = QPushButton()

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.icon_min = QIcon(os.path.join(base_dir, "assets", "win_min.svg"))
        self.icon_max = QIcon(os.path.join(base_dir, "assets", "win_max.svg"))
        self.icon_restore = QIcon(os.path.join(base_dir, "assets", "win_restore.svg"))
        self.icon_close = QIcon(os.path.join(base_dir, "assets", "win_close.svg"))

        self.btn_minimize.setIcon(self.icon_min)
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
        nav_layout.addStretch(1)
        nav_layout.addLayout(window_controls)
        self.main_layout.addWidget(self.header_container)

        self.canvas_container = QWidget()
        self.canvas_container.setObjectName("CanvasContainer")
        canvas_layout = QVBoxLayout(self.canvas_container)
        canvas_layout.setContentsMargins(50, 35, 50, 28)
        canvas_layout.setSpacing(18)

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
        
        self.setCentralWidget(self.central_w)
        
        self.all_flows: List[MediaCardWidget] = []
        
        from src.models.local_db import LocalDBManager
        self.db_manager = LocalDBManager()
        self._restore_saved_flows()

        self.db_sync_timer = QTimer(self)
        self.db_sync_timer.timeout.connect(self._sync_ui_from_db)
        self.db_sync_timer.start(1500)

    def _sync_ui_from_db(self):
        try:
            items = self.db_manager.get_all_items()
            item_dict = {row["id"]: row for row in items}
            
            for flow in self.all_flows:
                if not getattr(flow, 'db_id', None): continue
                db_row = item_dict.get(flow.db_id)
                if not db_row: continue
                
                # 1. Sync Metadata safely avoiding tmdb prefixes
                desc = db_row.get("description")
                title = db_row.get("title", flow.title)
                
                if title.startswith("tmdb:"):
                    title = flow.title
                    
                if desc:
                    flow.update_metadata(title, desc, db_row.get("genre", "Unknown"), db_row.get("rating", "-"))
                elif title != flow.title:
                    flow.update_metadata(title, "No description available.", "Unknown", "-")
                    
                # 2. Sync Torrent Data
                t_data = db_row.get("torrent_data")
                if t_data:
                    import json
                    try:
                        t_info = json.loads(t_data)
                        
                        # Restore unique identifiers for exact matching
                        if "hash" in t_info:
                            flow._current_hash = t_info["hash"]
                        if "name" in t_info:
                            flow._expected_torrent_name = t_info["name"]
                            
                        flow.update_torrent_ui(
                            human_state=t_info.get("human_state", "Unknown"),
                            pill_class=t_info.get("pill_class", "PillUnknown"),
                            pb_style=t_info.get("pb_style", "PbUnknown"),
                            prog_val=t_info.get("prog_val", 0.0),
                            size_str=t_info.get("size_str", "0 B"),
                            speed_str=t_info.get("speed_str", "0.0 MB/s"),
                            active_state_str=t_info.get("active_state_str", "")
                        )
                    except Exception: pass
                    
                # 3. Sync Conversion Data
                c_data = db_row.get("conversion_data")
                if c_data:
                    import json
                    try:
                        c_info = json.loads(c_data)
                        if isinstance(c_info, dict): c_info = [c_info]
                        flow.update_telemetry_ui(c_info)
                    except Exception: pass
        except Exception as e:
            pass

    def _restore_saved_flows(self) -> None:
        try:
            items = self.db_manager.get_all_items()
            for row in items:
                index = len(self.all_flows) + 1
                season_val = row.get("season", "")
                
                from src.ui.components.media_card import MediaCardWidget, SeriesCardWidget
                if season_val:
                    flow = SeriesCardWidget(index=index, relative_path=row["relative_path"], title=row["title"], season=season_val, db_id=row["id"], parent=self.scroll_content)
                else:
                    flow = MediaCardWidget(index=index, relative_path=row["relative_path"], title=row["title"], season="", db_id=row["id"], parent=self.scroll_content)
                
                flow.delete_confirmed.connect(self._on_flow_delete)
                self.all_flows.append(flow)
                self.flows_layout.addWidget(flow)
                
                conversion_completed = False
                c_data = row.get("conversion_data") or self.db_manager.get_conversion_cache(row["relative_path"].replace("\\", "/"))
                if c_data:
                    try:
                        import json
                        c_info = json.loads(c_data)
                        if isinstance(c_info, dict): c_info = [c_info]
                        if c_info and all(ep.get("db_status", "NOT STARTED").upper() in ["COMPLETED", "FAILED", "REJECTED"] for ep in c_info):
                            conversion_completed = True
                    except Exception: pass

                torrent_completed = False
                t_data = row.get("torrent_data") or self.db_manager.get_torrent_cache_by_path(row["relative_path"].replace("\\", "/"))
                if t_data:
                    try:
                        import json
                        t_info = json.loads(t_data)
                        if t_info.get("prog_val", 0.0) >= 1.0 or t_info.get("progress", 0.0) >= 1.0:
                            torrent_completed = True
                    except Exception: pass

                flow.conversion_completed = conversion_completed
                flow.torrent_completed = torrent_completed
                
                if not conversion_completed:
                    raw_title = row["title"]
                    if raw_title.startswith("tmdb:"):
                        try:
                            _, media_type, tmdb_id = raw_title.split(":", 2)
                            from src.core.tmdb_fetcher import TMDBFetcherThread
                            restore_fetcher = TMDBFetcherThread(tmdb_id, media_type, self)
                            restore_fetcher.title_resolved.connect(lambda resolved, idx=index: self.media_controller.start_ssh_telemetry(idx, resolved))
                            restore_fetcher.start()
                        except Exception: pass
                    else:
                        self.media_controller.start_ssh_telemetry(index, raw_title)
                
                self.media_controller.add_media_flow(
                    flow_index=index,
                    title=row["title"],
                    relative_path=row["relative_path"],
                    torrent_bytes=b"",
                    image_url=row.get("image_url", ""),
                    is_restored=True
                )
            self._sync_ui_from_db()
        except Exception as e:
            pass

    def _spawn_browser_modal_with_blur(self) -> None:
        if self._modal_open: return
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
            # Extract the exact scene name from the .torrent file to use for flawless matching
            torrent_name = os.path.splitext(os.path.basename(file_path))[0]
            
            blur_effect = QGraphicsBlurEffect()
            blur_effect.setBlurRadius(25)
            self.canvas_container.setGraphicsEffect(blur_effect)

            dialog = MediaCategoryDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                relative_path = dialog.get_relative_path()
                with open(file_path, "rb") as f:
                    torrent_bytes = f.read()

                db_id = self.db_manager.add_item(relative_path=relative_path, image_url=img_url, title=title, season=season)
                index = len(self.all_flows) + 1
                
                from src.ui.components.media_card import MediaCardWidget, SeriesCardWidget
                if season:
                    flow = SeriesCardWidget(index=index, relative_path=relative_path, title=title, season=season, db_id=db_id, parent=self.scroll_content)
                else:
                    flow = MediaCardWidget(index=index, relative_path=relative_path, title=title, season="", db_id=db_id, parent=self.scroll_content)
                
                flow.delete_confirmed.connect(self._on_flow_delete)
                flow.conversion_completed = False
                flow.torrent_completed = False
                
                # Bind the expected name so _update_qbit_db_globally can hunt it down precisely
                flow._expected_torrent_name = torrent_name 
                
                self.all_flows.append(flow)
                self.flows_layout.addWidget(flow)
                
                self.media_controller.add_media_flow(
                    flow_index=index, title=title, relative_path=relative_path,
                    torrent_bytes=torrent_bytes, image_url=img_url, is_restored=False
                )
        except Exception as e:
            pass
        finally:
            self.canvas_container.setGraphicsEffect(None)
            self._update_maximize_icon()
            try:
                if file_path and os.path.exists(file_path): os.remove(file_path)
            except Exception: pass

    def _on_flow_delete(self, hashes: List[str], delete_files: bool, flow_widget: object) -> None:
        self.media_controller.request_deletion(hashes, delete_files)
        if getattr(flow_widget, 'db_id', None) is not None:
            self.db_manager.delete_item(flow_widget.db_id)
        if hasattr(flow_widget, 'close_flow'):
            flow_widget.close_flow()
        flow_widget.close()
        if flow_widget in self.all_flows:
            self.all_flows.remove(flow_widget)
        self.flows_layout.removeWidget(flow_widget)

    def _update_qbit_db_globally(self, torrents_list: list) -> None:
        # Collect all hashes currently claimed by rows to avoid duplicate assignment
        known_hashes = {f._current_hash for f in self.all_flows if getattr(f, '_current_hash', None)}

        for flow in self.all_flows:
            if getattr(flow, 'torrent_completed', False):
                continue
                
            matched_t = None
            
            # Match Strategy 1: Exact Hash (For restored sessions and persistent tracking)
            if getattr(flow, '_current_hash', None):
                for t in torrents_list:
                    if t.get('hash') == flow._current_hash:
                        matched_t = t
                        break
            
            # Match Strategy 2: Exact Scene Name (Matches newly added downloads from modal)
            if not matched_t and getattr(flow, '_expected_torrent_name', None):
                for t in torrents_list:
                    if t.get('name') == flow._expected_torrent_name:
                        matched_t = t
                        break
                        
            # Match Strategy 3: Fallback by Save Path (Safeguarded against taking other flows' torrents)
            if not matched_t:
                target_suffix = flow.relative_path.replace("\\", "/")
                candidates = []
                for t in torrents_list:
                    sp = t.get('save_path', '').replace("\\", "/")
                    if (sp.endswith(target_suffix) or target_suffix in sp) and t.get('hash') not in known_hashes:
                        candidates.append(t)
                
                if candidates:
                    candidates.sort(key=lambda x: x.get('added_on', 0), reverse=True)
                    matched_t = candidates[0]
                    
            if matched_t and getattr(flow, 'db_id', None):
                # Lock in the identifiers
                flow._current_hash = matched_t.get('hash', '')
                flow._current_torrent_name = matched_t.get('name', '')
                known_hashes.add(flow._current_hash)
                
                prog_val = matched_t.get('progress', 0.0)
                state = matched_t.get('state', 'Unknown')
                dlspeed = matched_t.get('dlspeed', 0)
                size = matched_t.get('total_size', matched_t.get('size', 0)) # Ensure raw bytes are grabbed
                
                QBIT_STATE_MAP = {
                    "downloading":          ("Downloading",   "PillDownloading", "PbActive"),
                    "stalledDL":            ("Stalled",       "PillDownloading", "PbActive"),
                    "forcedDL":             ("Forced DL",     "PillDownloading", "PbActive"),
                    "metaDL":               ("Fetching Meta", "PillDownloading", "PbActive"),
                    "moving":               ("Moving",        "PillDownloading", "PbActive"),
                    "uploading":            ("Seeding",       "PillSuccess",     "PbSuccess"),
                    "stalledUP":            ("Stalled",       "PillSuccess",     "PbSuccess"),
                    "forcedUP":             ("Forced UP",     "PillSuccess",     "PbSuccess"),
                    "completed":            ("Completed",     "PillSuccess",     "PbSuccess"),
                    "pausedDL":             ("Paused",        "PillPaused",      "PbUnknown"),
                    "pausedUP":             ("Paused",        "PillPaused",      "PbUnknown"),
                    "checkingDL":           ("Checking",      "PillChecking",    "PbUnknown"),
                    "checkingUP":           ("Checking",      "PillChecking",    "PbUnknown"),
                    "checkingResumeData":   ("Checking",      "PillChecking",    "PbUnknown"),
                    "allocating":           ("Allocating",    "PillChecking",    "PbUnknown"),
                    "queuedDL":             ("Queued",        "PillQueued",      "PbUnknown"),
                    "queuedUP":             ("Queued",        "PillQueued",      "PbUnknown"),
                    "stopped":              ("Stopped",       "PillQueued",      "PbUnknown"),
                    "stoppedDL":            ("Stopped",       "PillQueued",      "PbUnknown"),
                    "unknown":              ("Unknown",       "PillUnknown",     "PbUnknown"),
                    "missingFiles":         ("Missing Files", "PillDanger",      "PbUnknown"),
                    "error":                ("Error",         "PillDanger",      "PbUnknown"),
                }

                if prog_val == 1.0:
                    human_state, pill_class, pb_style = "Completed", "PillSuccess", "PbSuccess"
                    flow.torrent_completed = True
                    
                    target_path = flow.relative_path.replace("\\", "/")
                    if not self.db_manager.get_torrent_cache_by_path(target_path):
                        import json
                        self.db_manager.set_torrent_cache(matched_t.get("hash", ""), target_path, json.dumps(matched_t))
                        self.media_controller.request_conversion(flow.relative_path)
                else:
                    fallback = (state.replace("DL","").replace("UP","").strip().capitalize(), "PillWarning", "PbWarning")
                    human_state, pill_class, pb_style = QBIT_STATE_MAP.get(state, fallback)

                active_state_str = f"State: {human_state} | Progress: {int(prog_val * 100)}% | Size: {format_size(size)}"
                
                import json
                t_info = {
                    "hash": flow._current_hash,
                    "name": flow._current_torrent_name,
                    "human_state": human_state,
                    "pill_class": pill_class,
                    "pb_style": pb_style,
                    "prog_val": prog_val,
                    "size_str": format_size(size),
                    "speed_str": format_speed(dlspeed),
                    "active_state_str": active_state_str
                }
                self.db_manager.update_torrent_data(flow.db_id, json.dumps(t_info))

    def _on_title_resolved(self, flow_index: int, title: str) -> None:
        for flow in self.all_flows:
            if flow.flow_index == flow_index:
                if getattr(flow, 'db_id', None):
                    self.db_manager.update_item_title(flow.db_id, title)
                flow.title = title
                season = getattr(flow, 'season', "")
                flow.title_lbl.setText(f"{title} — {season}" if season else title)
                break

    def _on_details_resolved(self, flow_index: int, details: dict) -> None:
        for flow in self.all_flows:
            if flow.flow_index == flow_index and getattr(flow, 'db_id', None):
                desc = details.get("description", "No description available.")
                genre = details.get("genre", "Unknown")
                rating = details.get("rating", "-")
                self.db_manager.update_metadata(flow.db_id, desc, genre, rating)
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
        for flow in self.all_flows:
            if flow.flow_index == flow_index and getattr(flow, 'db_id', None):
                self.db_manager.update_conversion_data(flow.db_id, json_payload)
                
                try:
                    import json
                    episodes_data = json.loads(json_payload)
                    if isinstance(episodes_data, dict): episodes_data = [episodes_data]
                    
                    all_finished = True
                    for ep in episodes_data:
                        state = ep.get("db_status", "NOT STARTED").upper()
                        if state not in ["COMPLETED", "FAILED", "REJECTED"]:
                            all_finished = False
                            break
                            
                    if all_finished and episodes_data:
                        flow.conversion_completed = True 
                        self.db_manager.set_conversion_cache(flow.relative_path.replace("\\", "/"), json.dumps(episodes_data))
                except Exception:
                    pass
                break

    def _on_media_toggle_changed(self, index: int) -> None:
        self.current_media_filter = "Movies" if index == 0 else "TV Series"
        self._filter_media_list(self.search_bar.get_query())

    def _filter_media_list(self, query: str) -> None:
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