import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from PyQt6.QtCore import Qt

from src.application.events import event_bus
from src.domain.repositories import IMediaRepository
from src.ui.components.media_card import MediaCardWidget, SeriesCardWidget

class MediaGridWidget(QWidget):
    """
    Manages the scroll area containing Media flows.
    Listens to EventBus signals to repaint specific cards.
    """
    def __init__(self, repo: IMediaRepository, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.all_flows = []
        
        self.setObjectName("CanvasContainer")
        canvas_layout = QVBoxLayout(self)
        canvas_layout.setContentsMargins(50, 35, 50, 28)
        canvas_layout.setSpacing(18)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollArea > QWidget { background: transparent; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        self.scroll_content.setStyleSheet("QWidget#ScrollContent { background-color: #0A0B0E; }")
        self.flows_layout = QVBoxLayout(self.scroll_content)
        self.flows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.flows_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.scroll_content)
        canvas_layout.addWidget(self.scroll_area)

        # Connect EventBus Signals (DDD Reactive State)
        event_bus.media_added_signal.connect(self._on_media_added)
        event_bus.media_deleted_signal.connect(self._on_media_deleted)
        event_bus.torrent_updated_signal.connect(self._on_torrent_updated)
        event_bus.conversion_updated_signal.connect(self._on_conversion_updated)
        event_bus.metadata_updated_signal.connect(self._on_metadata_updated)

    def load_initial_data(self):
        items = self.repo.get_all_items()
        for item in items:
            self._render_item(item)

    def _render_item(self, item):
        index = len(self.all_flows) + 1
        is_tv = item.media_type == 'tv-series'
        
        hash_val = ""
        cached_files = []
        if item.torrent_data:
            try:
                t_info = json.loads(item.torrent_data)
                hash_val = t_info.get("hash", "")
                cached_files = t_info.get("files", [])
            except: pass
            
        if is_tv:
            flow = SeriesCardWidget(index=index, relative_path=item.relative_path, title=item.title, season=item.season, is_season=bool(item.is_season), hash_val=hash_val, db_id=item.id, parent=self.scroll_content)
            if cached_files:
                flow._cached_files = cached_files
                flow.populate_episodes_from_files(cached_files)
        else:
            flow = MediaCardWidget(index=index, relative_path=item.relative_path, title=item.title, season=item.season, hash_val=hash_val, db_id=item.id, parent=self.scroll_content)
            
        # Hydrate description visually
        desc = item.description or "No description available."
        genre = item.genre or "Unknown"
        rating = item.rating or "-"
        flow.update_metadata(item.title, desc, genre, rating)
        
        # Determine conversion state visually
        conversion_completed = False
        c_data_str = item.conversion_data or self.repo.get_conversion_cache(item.relative_path.replace("\\", "/"))
        if c_data_str:
            try:
                c_info = json.loads(c_data_str)
                if isinstance(c_info, dict): c_info = [c_info]
                flow.update_telemetry_ui(c_info)
                if c_info and all(ep.get("db_status", "NOT STARTED").upper() in ["COMPLETED", "FAILED", "REJECTED"] for ep in c_info):
                    conversion_completed = True
            except: pass
            
        flow.conversion_completed = conversion_completed
            
        # Determine torrent state visually
        torrent_completed = False
        if item.torrent_data:
            try:
                t_info = json.loads(item.torrent_data)
                flow.update_torrent_ui(
                    human_state=t_info.get("human_state", "Unknown"),
                    pill_class=t_info.get("pill_class", "PillUnknown"),
                    pb_style=t_info.get("pb_style", "PbUnknown"),
                    prog_val=t_info.get("prog_val", 0.0),
                    size_str=t_info.get("size_str", "0 B"),
                    speed_str=t_info.get("speed_str", "0.0 MB/s"),
                    active_state_str=t_info.get("active_state_str", "")
                )
                if t_info.get("prog_val", 0.0) >= 1.0:
                    torrent_completed = True
            except: pass
            
        flow.torrent_completed = torrent_completed
        
        self.all_flows.append(flow)
        self.flows_layout.addWidget(flow)

    def _get_flow_by_id(self, item_id: int):
        for f in self.all_flows:
            if getattr(f, 'db_id', None) == item_id:
                return f
        return None

    def _on_media_added(self, item_id: int):
        item = self.repo.get_item(item_id)
        if item:
            self._render_item(item)

    def _on_media_deleted(self, item_id: int):
        flow = self._get_flow_by_id(item_id)
        if flow:
            if hasattr(flow, 'close_flow'):
                flow.close_flow()
            flow.close()
            self.all_flows.remove(flow)
            self.flows_layout.removeWidget(flow)

    def _on_torrent_updated(self, item_id: int):
        flow = self._get_flow_by_id(item_id)
        if not flow: return
        item = self.repo.get_item(item_id)
        if not item or not item.torrent_data: return
        
        try:
            t_info = json.loads(item.torrent_data)
            flow.update_torrent_ui(
                human_state=t_info.get("human_state", "Unknown"),
                pill_class=t_info.get("pill_class", "PillUnknown"),
                pb_style=t_info.get("pb_style", "PbUnknown"),
                prog_val=t_info.get("prog_val", 0.0),
                size_str=t_info.get("size_str", "0 B"),
                speed_str=t_info.get("speed_str", "0.0 MB/s"),
                active_state_str=t_info.get("active_state_str", "")
            )
            if t_info.get("prog_val", 0.0) >= 1.0:
                flow.torrent_completed = True
        except: pass

    def _on_conversion_updated(self, item_id: int):
        flow = self._get_flow_by_id(item_id)
        if not flow: return
        item = self.repo.get_item(item_id)
        if not item or not item.conversion_data: return
        
        try:
            c_info = json.loads(item.conversion_data)
            if isinstance(c_info, dict): c_info = [c_info]
            flow.update_telemetry_ui(c_info)
            if c_info and all(ep.get("db_status", "NOT STARTED").upper() in ["COMPLETED", "FAILED", "REJECTED"] for ep in c_info):
                flow.conversion_completed = True
        except: pass

    def _on_metadata_updated(self, item_id: int):
        flow = self._get_flow_by_id(item_id)
        if not flow: return
        item = self.repo.get_item(item_id)
        if not item: return
        
        desc = item.description or "No description available."
        genre = item.genre or "Unknown"
        rating = item.rating or "-"
        flow.update_metadata(item.title, desc, genre, rating)

    def filter_items(self, query: str, category: str):
        query = query.lower().strip()
        for flow in self.all_flows:
            title = flow.title_lbl.text().lower()
            matches_search = not query or query in title
            matches_category = (category == "TV Series" and getattr(flow, 'media_type', 'movie') == 'tv-series') or \
                               (category == "Movies" and getattr(flow, 'media_type', 'movie') == 'movie')
            flow.setVisible(matches_search and matches_category)
