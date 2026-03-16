import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup

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
        self._state_cache = {}
        
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

        self._filter_anim = None
        self._last_filter_key = None

        # Connect EventBus Signals (DDD Reactive State)
        event_bus.media_added_signal.connect(self._on_media_added)
        event_bus.media_deleted_signal.connect(self._on_media_deleted)
        event_bus.torrent_updated_signal.connect(self._on_torrent_updated)
        event_bus.conversion_updated_signal.connect(self._on_conversion_updated)
        event_bus.metadata_updated_signal.connect(self._on_metadata_updated)

    def load_initial_data(self):
        items = self.repo.get_all_items()
        for item in items:
            self._state_cache[item.id] = {
                "title": item.title,
                "description": item.description,
                "genre": item.genre,
                "rating": item.rating,
                "image_url": item.image_url,
                "torrent_data": item.torrent_data,
                "conversion_data": item.conversion_data,
            }
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
        state = self._state_cache.get(item.id, {})
        desc = state.get("description") or item.description or "No description available."
        genre = state.get("genre") or item.genre or "Unknown"
        rating = state.get("rating") or item.rating or "-"
        flow.update_metadata(item.title, desc, genre, rating)
        
        # Determine conversion state visually
        conversion_completed = False
        c_data_str = state.get("conversion_data") or item.conversion_data or self.repo.get_conversion_cache(item.relative_path.replace("\\", "/"))
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
        t_data_str = state.get("torrent_data") or item.torrent_data
        if t_data_str:
            try:
                t_info = json.loads(t_data_str)
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

    def collapse_all_foldouts(self) -> None:
        seen_episode_rows = set()
        for flow in self.all_flows:
            if hasattr(flow, 'collapse_foldout'):
                flow.collapse_foldout()
            if hasattr(flow, 'collapse_episodes'):
                flow.collapse_episodes()

            episodes_map = getattr(flow, 'episodes_map', {}) or {}
            for row in episodes_map.values():
                row_id = id(row)
                if row_id in seen_episode_rows:
                    continue
                seen_episode_rows.add(row_id)
                if hasattr(row, 'collapse_foldout'):
                    row.collapse_foldout()

    def _on_media_added(self, item_id: int):
        item = self.repo.get_item(item_id)
        if item:
            self._render_item(item)
            # Fade-in animation for the new card
            flow = self.all_flows[-1] if self.all_flows else None
            if flow:
                effect = QGraphicsOpacityEffect(flow)
                effect.setOpacity(0.0)
                flow.setGraphicsEffect(effect)
                anim = QPropertyAnimation(effect, b"opacity", flow)
                anim.setDuration(300)
                anim.setStartValue(0.0)
                anim.setEndValue(1.0)
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                anim.finished.connect(lambda: flow.setGraphicsEffect(None))
                anim.start()

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

            cached = self._state_cache.setdefault(item_id, {})
            cached["torrent_data"] = item.torrent_data
            
            # Populate episode rows when file list first arrives for TV series
            cached_files = t_info.get("files", [])
            if cached_files and hasattr(flow, 'populate_episodes_from_files'):
                if not getattr(flow, '_cached_files', None):
                    flow._cached_files = cached_files
                    tmdb_eps = getattr(flow, '_cached_tmdb_eps', None)
                    flow.populate_episodes_from_files(cached_files, tmdb_eps)
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
            cached = self._state_cache.setdefault(item_id, {})
            cached["conversion_data"] = item.conversion_data
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
        cached = self._state_cache.setdefault(item_id, {})
        cached["title"] = item.title
        cached["description"] = item.description
        cached["genre"] = item.genre
        cached["rating"] = item.rating

    def filter_items(self, query: str, category: str):
        filter_key = f"{query.lower().strip()}|{category}"
        if filter_key == self._last_filter_key:
            return
        self._last_filter_key = filter_key

        q = query.lower().strip()

        for flow in self.all_flows:
            title = flow.title_lbl.text().lower()
            matches_search = not q or q in title
            
            # 1. Foolproof verification: check the literal Widget Class type
            is_tv = isinstance(flow, SeriesCardWidget)
            
            matches_category = (category == "TV Series" and is_tv) or \
                               (category == "Movies" and not is_tv)
            
            should_be_visible = matches_search and matches_category
            
            # 2. Force the visibility state strictly (No IF checks, no layout pausing)
            flow.setVisible(should_be_visible)
