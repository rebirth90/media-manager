import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QDialog, QApplication

from src.presentation.widgets.header_navigation import HeaderNavigationWidget
from src.presentation.widgets.media_grid import MediaGridWidget
from src.presentation.utils.ui_helpers import apply_blur_effect, remove_blur_effect

from src.ui.dialogs.browser_modal import BrowserModalDialog
from src.ui.dialogs.media_category import MediaCategoryDialog
from src.core.media_controller import parse_tv_title
from src.application.use_cases.media_use_cases import AddMediaUseCase

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
        self.header_nav.search_changed.connect(
            lambda query: self.media_grid.filter_items(query, "TV Series" if self.header_nav.is_tv_series_selected() else "Movies")
        )
        self.header_nav.minimize_clicked.connect(self.showMinimized)
        self.header_nav.maximize_clicked.connect(self._toggle_maximize)
        self.header_nav.close_clicked.connect(self.close)

        self.main_layout.addWidget(self.header_nav)
        self.main_layout.addWidget(self.media_grid)
        
        self.setCentralWidget(self.central_w)
        
        # Wire up TMDB resolution signals
        self.media_controller.title_resolved.connect(self._on_title_resolved)
        self.media_controller.details_resolved.connect(self._on_details_resolved)
        self.media_controller.image_downloaded.connect(self._on_image_downloaded)
        self.media_controller.season_episodes_resolved.connect(self._on_episodes_resolved)

        # Initial Boot
        self._restore_saved_flows()

    def _restore_saved_flows(self):
        """Loads items from the DB to populate the grid visually on start."""
        self.media_grid.load_initial_data()
        
        # Note: the media_controller in the original architecture was responsible for booting
        # up background tasks for all loaded flows.
        for item in self.repo.get_all_items():
            self.media_controller.add_media_flow(
                flow_index=item.id,
                title=item.title,
                relative_path=item.relative_path,
                torrent_bytes=b"",
                image_url=item.image_url or "",
                is_restored=True
            )
            
        self.media_grid.filter_items("", "Movies")

    def _spawn_browser_modal(self) -> None:
        if self._modal_open: return
        self._modal_open = True
        try:
            apply_blur_effect(self.media_grid, radius=25)
            dialog = BrowserModalDialog(self.shared_profile, self)
            dialog.torrent_downloaded.connect(self._process_downloaded_torrent)
            dialog.exec()
        finally:
            remove_blur_effect(self.media_grid)
            self._modal_open = False
            self.header_nav.update_maximize_icon(self.isMaximized())

    def _process_downloaded_torrent(self, file_path: str, img_url: str, title: str, season: str = "") -> None:
        try:
            torrent_name = os.path.splitext(os.path.basename(file_path))[0]
            apply_blur_effect(self.media_grid, radius=25)

            dialog = MediaCategoryDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
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
                    is_restored=False
                )
                
                self.media_grid.filter_items(self.header_nav.get_search_query(), "TV Series" if self.header_nav.is_tv_series_selected() else "Movies")
        except Exception: pass
        finally:
            remove_blur_effect(self.media_grid)
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
            flow._tmdb_episodes = episodes
            if getattr(flow, '_cached_files', None):
                QTimer.singleShot(0, lambda: flow.populate_episodes_from_files(flow._cached_files))

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
