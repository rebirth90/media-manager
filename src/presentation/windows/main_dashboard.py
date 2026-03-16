import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QDialog, QApplication, QLabel, QGraphicsOpacityEffect
)

from src.presentation.widgets.header_navigation import HeaderNavigationWidget
from src.presentation.widgets.media_grid import MediaGridWidget
from src.presentation.utils.ui_helpers import apply_blur_effect, remove_blur_effect

from src.ui.dialogs.browser_modal import BrowserModalDialog
from src.ui.dialogs.media_category import MediaCategoryDialog
from src.application.media_controller import parse_tv_title
from src.application.use_cases.media_use_cases import AddMediaUseCase
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QTimer

MODAL_BLUR_RADIUS = 90

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LoadingOverlay")
        self.setStyleSheet("background-color: #0A0B0E;")
        layout = QVBoxLayout(self)
        self.label = QLabel("Initializing Media Ecosystem...")
        self.label.setStyleSheet("color: #60A5FA; font-size: 18px; font-weight: bold;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

class MainDashboard(QMainWindow):
    """
    The main presentation layer dashboard.
    Assembles the HeaderNavigationWidget and MediaGridWidget.
    Triggers Application Use Cases upon user interaction.
    """
    def __init__(self, shared_profile, media_controller, repo) -> None:
        super().__init__()
        
        self.shared_profile = shared_profile
        self.media_controller = media_controller
        self.repo = repo
        
        # Use Cases
        self.add_media_use_case = AddMediaUseCase(self.repo)

        self.setWindowTitle("Media Manager - Enterprise Dashboard")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.showMaximized()
        self._is_dragging = False
        self._drag_pos = None
        self._modal_open = False
        self._modal_blur_locks = 0
        
        self.central_w = QWidget()
        self.main_layout = QVBoxLayout(self.central_w)
        self.main_layout.setContentsMargins(0, 0, 0, 25)
        self.main_layout.setSpacing(0)
        
        # Initialize Sub-components
        self.header_nav = HeaderNavigationWidget(self)
        self.media_grid = MediaGridWidget(self.repo, self)
        
        # Connect Header Signals
        self.header_nav.add_clicked.connect(self._spawn_browser_modal)
        self.header_nav.toggle_changed.connect(self._on_media_toggle_changed)
        self.header_nav.search_changed.connect(self._on_search_changed)
        self.header_nav.minimize_clicked.connect(self.showMinimized)
        self.header_nav.maximize_clicked.connect(self._toggle_maximize)
        self.header_nav.close_clicked.connect(self.close)

        self.main_layout.addWidget(self.header_nav)
        self.main_layout.addWidget(self.media_grid)
        
        # Requirement 3: Startup Overlay
        self.loading_overlay = LoadingOverlay(self.central_w)
        self.loading_overlay.setGeometry(self.rect())
        self.loading_overlay.raise_()
        
        self.setCentralWidget(self.central_w)
        
        # Wire up TMDB resolution signals
        self.media_controller.title_resolved.connect(self._on_title_resolved)
        self.media_controller.details_resolved.connect(self._on_details_resolved)
        self.media_controller.image_downloaded.connect(self._on_image_downloaded)
        self.media_controller.season_episodes_resolved.connect(self._on_episodes_resolved)

        # Initial Boot
        self._restore_saved_flows()

    def _is_tv_selected_safe(self) -> bool:
        try:
            method = getattr(self.header_nav, "is_tv_series_selected", None)
            if callable(method):
                return bool(method())
            toggle = getattr(self.header_nav, "animated_toggle", None)
            if toggle and hasattr(toggle, "index"):
                return int(toggle.index()) == 1
        except Exception:
            pass
        return False

    def _current_category_safe(self) -> str:
        return "TV Series" if self._is_tv_selected_safe() else "Movies"

    def _on_search_changed(self, query: str) -> None:
        try:
            self.media_grid.filter_items(query, self._current_category_safe())
        except Exception:
            # Search input should never crash the UI loop.
            pass

    def _restore_saved_flows(self):
        """Loads items from the DB to populate the grid visually on start."""
        items = self.repo.get_all_items()
        self.media_grid.load_initial_data()
        
        # Note: the media_controller in the original architecture was responsible for booting
        # up background tasks for all loaded flows.
        for item in items:
            self.media_controller.add_media_flow(
                flow_index=item.id,
                title=item.title,
                relative_path=item.relative_path,
                torrent_bytes=b"",
                image_url=item.image_url or "",
                is_restored=True,
                tmdb_id=item.tmdb_id,
                media_type=item.media_type,
                season=item.season
            )
            
        # Non-blocking filter to prevent initial hang
        QTimer.singleShot(0, lambda: self.media_grid.filter_items("", "Movies"))

        # Keep startup overlay until initial row hydration is complete.
        self._wait_for_initial_grid_ready(items)

    def _wait_for_initial_grid_ready(self, items):
        expected_ids = {item.id for item in items}
        if not expected_ids:
            self._fade_out_overlay()
            return

        waited_ms = 0
        max_wait_ms = 20000

        def poll_ready():
            nonlocal waited_ms
            waited_ms += 150

            rendered_ids = {getattr(f, 'db_id', None) for f in self.media_grid.all_flows}
            if not expected_ids.issubset(rendered_ids):
                if waited_ms >= max_wait_ms:
                    self._fade_out_overlay()
                    return
                QTimer.singleShot(150, poll_ready)
                return

            if all(self._is_flow_render_ready(item_id) for item_id in expected_ids):
                self._fade_out_overlay()
                return

            if waited_ms >= max_wait_ms:
                self._fade_out_overlay()
                return

            QTimer.singleShot(150, poll_ready)

        QTimer.singleShot(150, poll_ready)

    def _apply_modal_blur(self):
        self._modal_blur_locks += 1
        if self._modal_blur_locks == 1:
            apply_blur_effect(self.central_w, radius=MODAL_BLUR_RADIUS)

    def _release_modal_blur(self):
        if self._modal_blur_locks > 0:
            self._modal_blur_locks -= 1
        if self._modal_blur_locks == 0:
            remove_blur_effect(self.central_w)

    def _is_flow_render_ready(self, item_id: int) -> bool:
        flow = self.media_grid._get_flow_by_id(item_id)
        item = self.repo.get_item(item_id)
        if not flow or not item:
            return False

        if not getattr(flow, 'title_lbl', None) or not flow.title_lbl.text().strip():
            return False

        if getattr(item, 'image_url', None):
            pix = getattr(getattr(flow, 'lbl_poster', None), 'pixmap', lambda: None)()
            if not pix or pix.isNull():
                return False

        if item.torrent_data:
            state_val = getattr(getattr(flow, 'lbl_state_val', None), 'text', lambda: "")().strip().lower()
            if state_val in ("", "initializing"):
                return False

        if item.conversion_data:
            flowchart = getattr(flow, 'flowchart_view', None)
            # Only gate startup on the card-level chart. Episode-level charts initialize lazily.
            if flowchart and not getattr(flowchart, '_page_loaded', False):
                return False

        return True

    def _hold_blur_until_flow_ready(self, item_id: int):
        waited_ms = 0

        def poll_ready():
            nonlocal waited_ms
            waited_ms += 250
            if self._is_flow_render_ready(item_id) or waited_ms >= 30000:
                self._release_modal_blur()
                return
            QTimer.singleShot(250, poll_ready)

        QTimer.singleShot(250, poll_ready)

    def _exec_modal(self, dialog: QDialog, *, release_blur: bool = True, apply_blur: bool = True) -> int:
        self.media_grid.collapse_all_foldouts()
        if apply_blur:
            self._apply_modal_blur()
        try:
            return dialog.exec()
        finally:
            if release_blur:
                self._release_modal_blur()
            self.header_nav.update_maximize_icon(self.isMaximized())

    def _fade_out_overlay(self):
        self.effect = QGraphicsOpacityEffect(self.loading_overlay)
        self.loading_overlay.setGraphicsEffect(self.effect)
        
        self.anim = QPropertyAnimation(self.effect, b"opacity")
        self.anim.setDuration(800)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(self.loading_overlay.deleteLater)
        self.anim.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'loading_overlay') and self.loading_overlay:
            self.loading_overlay.setGeometry(self.central_w.rect())

    def _spawn_browser_modal(self) -> None:
        if self._modal_open: return
        self._modal_open = True
        try:
            dialog = BrowserModalDialog(self.shared_profile, self)
            dialog.torrent_downloaded.connect(self._process_downloaded_torrent)
            result = self._exec_modal(dialog, release_blur=False)
            if result != QDialog.DialogCode.Accepted:
                self._release_modal_blur()
        finally:
            self._modal_open = False

    def _process_downloaded_torrent(self, file_path: str, img_url: str, title: str, season: str = "") -> None:
        hold_blur_for_row = False
        try:
            torrent_name = os.path.splitext(os.path.basename(file_path))[0]
            dialog = MediaCategoryDialog(self)
            if self._exec_modal(dialog, release_blur=False, apply_blur=False) == QDialog.DialogCode.Accepted:
                relative_path = dialog.get_relative_path()
                with open(file_path, "rb") as f:
                    torrent_bytes = f.read()

                is_season_flag = dialog.get_is_season()
                
                _, p_season, p_is_season = parse_tv_title(torrent_name)
                if not season and p_season: season = str(p_season)
                if p_is_season: is_season_flag = True
                
                is_tv_bool = bool(is_season_flag or season)
                media_type = 'tv-series' if is_tv_bool else 'movie'
                
                # DDD Note: Call the application use case instead of the repository directly 
                item_id = self.add_media_use_case.execute(
                    relative_path=relative_path, 
                    image_url=img_url, 
                    title=title, 
                    season=season, 
                    is_season=int(is_season_flag), 
                    media_type=media_type
                )
                
                # Hand over to MediaController to start downloading & resolving metadata
                self.media_controller.add_media_flow(
                    flow_index=item_id, 
                    title=title, 
                    relative_path=relative_path,
                    torrent_bytes=torrent_bytes, 
                    image_url=img_url, 
                    is_restored=False,
                    media_type=media_type,
                    season=season
                )

                hold_blur_for_row = True
                self._hold_blur_until_flow_ready(item_id)
                
                self.media_grid.filter_items(self.header_nav.get_search_query(), self._current_category_safe())
        except Exception: pass
        finally:
            if not hold_blur_for_row:
                self._release_modal_blur()
            self.header_nav.update_maximize_icon(self.isMaximized())
            try:
                if file_path and os.path.exists(file_path): os.remove(file_path)
            except Exception: pass

    def _on_title_resolved(self, flow_index: int, title: str):
        from src.application.events import event_bus
        self.repo.update_item_title(flow_index, title)
        event_bus.metadata_updated_signal.emit(flow_index)

    def _on_details_resolved(self, flow_index: int, details: dict):
        from src.application.events import event_bus
        desc = details.get("description", "")
        genre = details.get("genre", "")
        rating = details.get("rating", "")
        self.repo.update_metadata(flow_index, desc, genre, rating)
        
        img = details.get("image_url")
        if img and hasattr(self.repo, 'update_item_image_url'):
            self.repo.update_item_image_url(flow_index, img)
            
        event_bus.metadata_updated_signal.emit(flow_index)

    def _on_image_downloaded(self, flow_index: int, image_bytes: bytes):
        flow = self.media_grid._get_flow_by_id(flow_index)
        if flow and hasattr(flow, 'set_poster_pixmap'):
            from PyQt6.QtGui import QPixmap
            pm = QPixmap()
            pm.loadFromData(image_bytes)
            flow.set_poster_pixmap(pm)
            
    def _on_episodes_resolved(self, flow_index: int, episodes: dict):
        flow = self.media_grid._get_flow_by_id(flow_index)
        if flow and hasattr(flow, '_ensure_episode_row'):
            from PyQt6.QtCore import QTimer
            flow._cached_tmdb_eps = episodes
            # If files arrived first, populate now. Otherwise media_grid will do it when they arrive.
            if getattr(flow, '_cached_files', None):
                QTimer.singleShot(0, lambda: flow.populate_episodes_from_files(flow._cached_files, episodes))

    def _on_media_toggle_changed(self, index: int) -> None:
        category = "TV Series" if index == 1 else "Movies"
        self.media_grid.filter_items(self.header_nav.get_search_query(), category)

    def closeEvent(self, event) -> None:
        if hasattr(self, 'shared_profile'): self.shared_profile.deleteLater()
        super().closeEvent(event)
        QApplication.quit()
        os._exit(0)

    def _toggle_maximize(self) -> None:
        if self.isMaximized(): 
            self.showNormal()
        else: 
            self.showMaximized()
        self.header_nav.update_maximize_icon(self.isMaximized())

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and event.pos().y() < 72:
            self._is_dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            if self.isMaximized():
                self.showNormal()
                self.header_nav.update_maximize_icon(False)
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._is_dragging = False
        super().mouseReleaseEvent(event)
