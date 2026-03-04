import os
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QColor, QPen
from PyQt6.QtCore import QRectF, QSize
from PyQt6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QSizePolicy, QDialog
)

from src.ui.dialogs.flow_details import FlowDetailsModal
from src.ui.dialogs.delete_torrent import DeleteTorrentDialog
from src.ui.conversion_flowchart import ConversionFlowViewer


class MediaCardWidget(QFrame):
    # Signals emitted to the external Logic Controller
    delete_confirmed = pyqtSignal(list, bool, object)  # [hash], delete_files, flow_reference
    send_to_conversion_requested = pyqtSignal(str, object)

    def __init__(self, index: int, relative_path: str, title: str, season: str = "", hash_val: str = "", parent=None):
        super().__init__(parent)
        self.flow_index = index
        self.relative_path = relative_path
        self._current_hash = hash_val
        self.db_id = None
        
        base_title = title if title else "Unknown Media"
        if season:
            self.title = f"{base_title} - {season}"
        else:
            self.title = base_title

        self._active_qbit_state = "Initializing..."
        self._active_ffmpeg_log = "Awaiting conversion pipeline..."
        self._illustration_path = r"C:\Users\Codrut\.gemini\antigravity\brain\8785b3f2-114a-4ae3-86c6-da36af48ada5\isometric_drafting_illustration_1772118592306.png"

        self.setObjectName("MediaCardWrapper")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._setup_top_row()
        self._setup_foldout()

    def _setup_top_row(self):
        self.top_row_container = QWidget()
        self.top_row_container.setObjectName("TopRow")
        self.top_row_container.setStyleSheet("background-color: transparent;")
        self.top_row_container.setAutoFillBackground(False)
        self.top_row_container.setFixedHeight(120)
        self.top_row_container.installEventFilter(self)
        self.top_row_container.setCursor(Qt.CursorShape.PointingHandCursor)

        self.top_row_layout = QHBoxLayout(self.top_row_container)
        self.top_row_layout.setContentsMargins(16, 16, 16, 16)
        self.top_row_layout.setSpacing(20)

        # 1. Poster
        self.lbl_poster = QLabel()
        self.lbl_poster.setFixedSize(60, 85)
        self.lbl_poster.setObjectName("PosterImage")
        self.lbl_poster.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.top_row_layout.addWidget(self.lbl_poster)

        # 2. Metadata (Flex)
        info_container = QWidget()
        info_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        info_container.setAutoFillBackground(False)
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.title_lbl = QLabel(self.title)
        self.title_lbl.setObjectName("TitleText")
        self.title_lbl.setWordWrap(False)
        
        self.lbl_foldout_genre_rating = QLabel("Genre: N/A | Rating: N/A")
        self.lbl_foldout_genre_rating.setObjectName("SubText")
        
        self.lbl_foldout_desc = QLabel("No description available.")
        self.lbl_foldout_desc.setObjectName("DescText")
        self.lbl_foldout_desc.setWordWrap(True)
        self.lbl_foldout_desc.setMaximumHeight(35)
        
        info_layout.addWidget(self.title_lbl)
        info_layout.addWidget(self.lbl_foldout_genre_rating)
        info_layout.addWidget(self.lbl_foldout_desc)
        self.top_row_layout.addWidget(info_container)

        # 3. Status Pills
        status_layout = QHBoxLayout()
        status_layout.setSpacing(24)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        
        def create_col(title_str, min_width):
            container = QWidget()
            container.setFixedWidth(min_width)
            container.setAutoFillBackground(False)
            v = QVBoxLayout(container)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(8)
            v.setAlignment(Qt.AlignmentFlag.AlignCenter) 
            cap = QLabel(title_str)
            cap.setObjectName("PillHeader")
            cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.addWidget(cap)
            return container, v
            
        ts_container, ts_v = create_col("Torrent Status", 110)
        self.lbl_state_val = QLabel("Initializing")
        self.lbl_state_val.setFixedHeight(24)
        self.lbl_state_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_state_val.setProperty("class", "PillUnknown")
        ts_v.addWidget(self.lbl_state_val)
        status_layout.addWidget(ts_container)

        sz_container, sz_v = create_col("Torrent Size", 80)
        self.lbl_size_val = QLabel("0 B")
        self.lbl_size_val.setFixedHeight(24)
        self.lbl_size_val.setObjectName("SizeText")
        self.lbl_size_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sz_v.addWidget(self.lbl_size_val)
        status_layout.addWidget(sz_container)

        pr_container, pr_v = create_col("Torrent Progress", 90)
        self.prog_bar_dl = QProgressBar()
        self.prog_bar_dl.setRange(0, 100)
        self.prog_bar_dl.setValue(0)
        self.prog_bar_dl.setFormat("%p%")
        self.prog_bar_dl.setFixedSize(80, 24)
        self.prog_bar_dl.setProperty("class", "PbUnknown")
        pr_v.addWidget(self.prog_bar_dl)
        status_layout.addWidget(pr_container)

        sp_container, sp_v = create_col("DL Speed", 80)
        self.lbl_speed_display = QLabel("0 kB/s")
        self.lbl_speed_display.setFixedHeight(24)
        self.lbl_speed_display.setObjectName("SizeText")
        self.lbl_speed_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sp_v.addWidget(self.lbl_speed_display)
        status_layout.addWidget(sp_container)
        
        cs_container, cs_v = create_col("Conversion Status", 130)
        self.lbl_conv_state_val = QLabel("NOT STARTED")
        self.lbl_conv_state_val.setFixedHeight(24)
        self.lbl_conv_state_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_conv_state_val.setProperty("class", "PillUnknown")
        self.prog_bar_conv = QProgressBar()
        self.prog_bar_conv.setRange(0, 100)
        self.prog_bar_conv.setFixedSize(80, 24)
        self.prog_bar_conv.hide()
        cs_v.addWidget(self.lbl_conv_state_val)
        cs_v.addWidget(self.prog_bar_conv)
        status_layout.addWidget(cs_container)

        self.top_row_layout.addLayout(status_layout)
        
        # 4. Actions
        self.action_buttons_container = QWidget()
        self.action_buttons_container.setFixedWidth(100)
        self.action_buttons_container.setAutoFillBackground(False)
        
        actions_layout = QHBoxLayout(self.action_buttons_container)
        actions_layout.setSpacing(12)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        trash_icon_path = os.path.join(base_dir, "assets", "trash_icon.svg")
        chev_down_path = os.path.join(base_dir, "assets", "chevron_down.svg")
        
        self.btn_trash_row = QPushButton()
        self.btn_trash_row.setIcon(QIcon(trash_icon_path))
        self.btn_trash_row.setIconSize(QSize(20, 20))
        self.btn_trash_row.setFixedSize(40, 40)
        self.btn_trash_row.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_trash_row.setObjectName("DangerIconButton")
        self.btn_trash_row.clicked.connect(self._prompt_delete)
        
        self.btn_expand = QPushButton()
        self.btn_expand.setIcon(QIcon(chev_down_path))
        self.btn_expand.setIconSize(QSize(22, 22))
        self.btn_expand.setFixedSize(40, 40)
        self.btn_expand.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_expand.setObjectName("ActionIconButton")
        self.btn_expand.clicked.connect(self._toggle_foldout)

        actions_layout.addWidget(self.btn_trash_row)
        actions_layout.addWidget(self.btn_expand)
        self.top_row_layout.addWidget(self.action_buttons_container)

        self.main_layout.addWidget(self.top_row_container)

    def _setup_foldout(self):
        self.foldout_container = QWidget()
        self.foldout_container.setObjectName("FoldoutCard")
        self.foldout_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.foldout_container.setVisible(False)
        # style assigned via QSS objectName
        self.foldout_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.foldout_container.setMinimumHeight(350) 
        self.foldout_layout = QVBoxLayout(self.foldout_container)
        self.foldout_layout.setContentsMargins(10, 0, 10, 10)
        self.foldout_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.flowchart_view = ConversionFlowViewer()
        self.flowchart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.foldout_layout.addWidget(self.flowchart_view)

        # Legacy variables
        self.lbl_speed_val = QLabel("0 kB/s")
        self.lbl_foldout_db_status = QLabel("")
        self.lbl_foldout_sub_status = QLabel("")
        self.btn_send_conv = QPushButton()

        self.main_layout.addWidget(self.foldout_container)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj == self.top_row_container and event.type() == QEvent.Type.MouseButtonRelease:
            self._toggle_foldout()
            return True
        return super().eventFilter(obj, event)

    def _toggle_foldout(self) -> None:
        is_visible = self.foldout_container.isVisible()
        self.foldout_container.setVisible(not is_visible)
        
        # Trigger explicit resize / update cycle on HTML logic if expanded
        if not is_visible and hasattr(self, 'flowchart_view'):
            if hasattr(self.flowchart_view, '_view'):
                self.flowchart_view._view.resizeEvent(None)  # or simple trigger
            self.flowchart_view.updateGeometry()
            self.foldout_container.adjustSize()
    def _prompt_delete(self) -> None:
        # We handle dialog inside UI, but logic deletion is emitted to controller
        if not self._current_hash:
            return
            
        dialog = DeleteTorrentDialog(self.title, self.window())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            delete_files = dialog.should_delete_files()
            self.delete_confirmed.emit([self._current_hash], delete_files, self)

    def set_poster_pixmap(self, raw_pixmap: QPixmap) -> None:
        scaled = raw_pixmap.scaled(self.lbl_poster.width(), self.lbl_poster.height(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        rounded_pixmap = QPixmap(scaled.size())
        rounded_pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(rounded_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, scaled.width(), scaled.height()), 8, 8)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled)
        pen = QPen(QColor(255, 255, 255, 13)) 
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawPath(path)
        painter.end()
        
        self.lbl_poster.setPixmap(rounded_pixmap)
        self.lbl_poster.setText("")
        self.lbl_poster.setStyleSheet("background-color: transparent;")
        self.lbl_poster.show()

    def update_metadata(self, title: str, desc: str, genre: str, rating: str):
        self.title = title
        self.title_lbl.setText(title)
        self.lbl_foldout_desc.setText(desc)
        self.lbl_foldout_genre_rating.setText(f"Genre: {genre} | Rating: ★ {rating}")

    def update_torrent_ui(self, human_state: str, pill_class: str, pb_style: str, prog_val: float, size_str: str, speed_str: str, active_state_str: str):
        self._active_qbit_state = active_state_str
        self.lbl_state_val.setText(human_state)
        self.lbl_state_val.setProperty("class", pill_class)
        self.lbl_state_val.style().unpolish(self.lbl_state_val)
        self.lbl_state_val.style().polish(self.lbl_state_val)
        self.prog_bar_dl.setProperty("class", pb_style)
        self.prog_bar_dl.style().unpolish(self.prog_bar_dl)
        self.prog_bar_dl.style().polish(self.prog_bar_dl)
        self.lbl_size_val.setText(size_str)
        self.prog_bar_dl.setValue(int(prog_val * 100))
        self.lbl_speed_val.setText(speed_str)
        self.lbl_speed_display.setText(speed_str)

    def update_telemetry_ui(self, episodes_data: list):
        if not episodes_data:
            return
            
        # For now, just grab the first episode (movie behavior)
        # We will refactor this to distribute to EpisodeRowWidgets for TV shows
        first_ep = episodes_data[0]
        db_status = first_ep.get("db_status", "NOT STARTED")
        sub_status = first_ep.get("sub_status", "Pending")
        ff_out = first_ep.get("ff_tail", "")
        stage_flags_json = first_ep.get("stage_results", "{}")
        
        pill_css = "PillUnknown"
        if db_status == "COMPLETED": pill_css = "PillSuccess"
        elif db_status == "FAILED": pill_css = "PillDanger"
        elif db_status not in ["NOT STARTED", "INITIALIZING"]: pill_css = "PillActive"

        self._active_qbit_state = f"DB Status: {db_status}"
        self._active_ffmpeg_log = ff_out
        
        self.lbl_conv_state_val.setText(db_status)
        self.lbl_conv_state_val.setProperty("class", pill_css)
        self.lbl_conv_state_val.style().unpolish(self.lbl_conv_state_val)
        self.lbl_conv_state_val.style().polish(self.lbl_conv_state_val)
        self.lbl_foldout_db_status.setText(f"Conversion Status: {db_status}")
        self.lbl_foldout_sub_status.setText(f"Subtitles: {sub_status}")
        
        if hasattr(self, 'flowchart_view') and stage_flags_json:
            self.flowchart_view.update_pipeline_state(stage_flags_json)

class EpisodeRowWidget(QWidget):
    def __init__(self, ep_name: str, parent=None):
        super().__init__(parent)
        self.ep_name = ep_name
        self.setObjectName("EpisodeRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # --- Top Bar ---
        self.top_bar = QWidget()
        self.top_bar.setObjectName("EpisodeTopBar") 
        self.top_bar.setFixedHeight(64)
        self.top_bar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.top_bar.installEventFilter(self)
        
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(16, 0, 16, 0)
        top_layout.setSpacing(16)
        
        # Badge
        self.badge = QLabel("EP")
        self.badge.setFixedSize(40, 40)
        self.badge.setObjectName("EpisodeBadge")
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(self.badge)
        
        # Title
        self.title_lbl = QLabel(ep_name)
        self.title_lbl.setObjectName("TitleText")
        top_layout.addWidget(self.title_lbl, 1)
        
        # Conv Status
        status_v = QVBoxLayout()
        status_v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_v.setSpacing(4)
        status_header = QLabel("Conversion Status")
        status_header.setObjectName("PillHeader")
        status_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status = QLabel("NOT STARTED")
        self.lbl_status.setFixedHeight(24)
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setProperty("class", "PillUnknown")
        status_v.addWidget(status_header)
        status_v.addWidget(self.lbl_status)
        
        top_layout.addLayout(status_v)
        
        # Chevron
        self.btn_expand = QPushButton()
        chev_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "assets", "chevron_down.svg")
        self.btn_expand.setIcon(QIcon(chev_path))
        self.btn_expand.setIconSize(QSize(22, 22))
        self.btn_expand.setFixedSize(40, 40)
        self.btn_expand.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_expand.setObjectName("ActionIconButton")
        self.btn_expand.clicked.connect(self._toggle_foldout)
        top_layout.addWidget(self.btn_expand)
        
        self.main_layout.addWidget(self.top_bar)
        
        # --- Flowchart Foldout ---
        self.foldout = QWidget()
        self.foldout.setVisible(False)
        self.foldout.setMinimumHeight(300)
        foldout_layout = QVBoxLayout(self.foldout)
        self.flowchart = ConversionFlowViewer()
        foldout_layout.addWidget(self.flowchart)
        self.main_layout.addWidget(self.foldout)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj == self.top_bar and event.type() == QEvent.Type.MouseButtonRelease:
            self._toggle_foldout()
            return True
        return super().eventFilter(obj, event)

    def _toggle_foldout(self):
        is_vis = self.foldout.isVisible()
        self.foldout.setVisible(not is_vis)
        if not is_vis:
            if hasattr(self.flowchart, '_view'):
                self.flowchart._view.resizeEvent(None)
            self.flowchart.updateGeometry()

    def update_status(self, db_status, stage_flags_json):
        self.lbl_status.setText(db_status)
        pill_css = "PillUnknown"
        if db_status == "COMPLETED": pill_css = "PillSuccess"
        elif db_status == "FAILED": pill_css = "PillDanger"
        elif db_status not in ["NOT STARTED", "INITIALIZING"]: pill_css = "PillActive"
        
        self.lbl_status.setProperty("class", pill_css)
        self.lbl_status.style().unpolish(self.lbl_status)
        self.lbl_status.style().polish(self.lbl_status)
        
        if stage_flags_json:
            self.flowchart.update_pipeline_state(stage_flags_json)

class SeriesCardWidget(QFrame):
    delete_confirmed = pyqtSignal(list, bool, object)

    def __init__(self, index: int, relative_path: str, title: str, season: str, hash_val: str = "", parent=None):
        super().__init__(parent)
        self.flow_index = index
        self.relative_path = relative_path
        self._current_hash = hash_val
        self.season = season
        self.title = title
        self.episodes_map = {} # path -> EpisodeRowWidget
        
        self.setObjectName("MediaCardWrapper")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 16)
        self.main_layout.setSpacing(0)

        # Top Row
        self.top_row = QWidget()
        self.top_row.setFixedHeight(120)
        top_layout = QHBoxLayout(self.top_row)
        top_layout.setContentsMargins(16, 16, 16, 16)
        top_layout.setSpacing(20)

        self.lbl_poster = QLabel()
        self.lbl_poster.setFixedSize(60, 85)
        self.lbl_poster.setObjectName("PosterImage")
        top_layout.addWidget(self.lbl_poster)

        info_v = QVBoxLayout()
        self.title_lbl = QLabel(f"{title} — {season}" if season else title)
        self.title_lbl.setObjectName("TitleText")
        self.lbl_genre = QLabel("Genre: N/A | Rating: N/A")
        self.lbl_genre.setObjectName("SubText")
        self.lbl_desc = QLabel("No description available.")
        self.lbl_desc.setObjectName("DescText")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setMaximumHeight(35)
        
        info_v.addWidget(self.title_lbl)
        info_v.addWidget(self.lbl_genre)
        info_v.addWidget(self.lbl_desc)
        top_layout.addLayout(info_v, 1)

        # Collapse Button
        self.btn_collapse = QPushButton("Collapse episodes")
        self.btn_collapse.setObjectName("CollapseButton")
        self.btn_collapse.setFixedSize(130, 24)
        self.btn_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapse.clicked.connect(self._toggle_episodes)
        
        collapse_v = QVBoxLayout()
        collapse_v.addWidget(self.btn_collapse, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        collapse_v.addStretch(1)
        top_layout.addLayout(collapse_v)

        self.main_layout.addWidget(self.top_row)

        # Episodes Container
        self.episodes_container = QWidget()
        self.episodes_layout = QVBoxLayout(self.episodes_container)
        self.episodes_layout.setContentsMargins(16, 0, 16, 0)
        self.episodes_layout.setSpacing(8)
        self.main_layout.addWidget(self.episodes_container)

    def close_flow(self):
        # Allow main window to clean up
        self.deleteLater()

    def _toggle_episodes(self):
        is_vis = self.episodes_container.isVisible()
        self.episodes_container.setVisible(not is_vis)
        self.btn_collapse.setText("Expand episodes" if is_vis else "Collapse episodes")

    def update_metadata(self, title, desc, genre, rating):
        self.title = title
        self.title_lbl.setText(f"{title} — {self.season}" if self.season else title)
        self.lbl_desc.setText(desc)
        self.lbl_genre.setText(f"Genre: {genre} | Rating: ★ {rating}")

    def set_poster_pixmap(self, raw_pixmap: QPixmap) -> None:
        scaled = raw_pixmap.scaled(self.lbl_poster.width(), self.lbl_poster.height(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        rounded_pixmap = QPixmap(scaled.size())
        rounded_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, scaled.width(), scaled.height()), 8, 8)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled)
        pen = QPen(QColor(255, 255, 255, 13)) 
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawPath(path)
        painter.end()
        self.lbl_poster.setPixmap(rounded_pixmap)
        self.lbl_poster.setText("")
        self.lbl_poster.setStyleSheet("background-color: transparent;")

    def update_torrent_ui(self, human_state: str, pill_class: str, pb_style: str, prog_val: float, size_str: str, speed_str: str, active_state_str: str):
        pass # Series level torrent tracking can be implemented later.

    def update_telemetry_ui(self, episodes_data: list):
        if not episodes_data: return
        import os, re
        
        # Sort by episode path to ensure E1 is before E2
        for ep_data in sorted(episodes_data, key=lambda x: x.get("path", "")):
            path = ep_data.get("path", "")
            if not path: continue
            
            if path not in self.episodes_map:
                ep_name = os.path.basename(path)
                row = EpisodeRowWidget(ep_name)
                match = re.search(r'[eE](\d{1,2})', ep_name)
                badge_text = f"E{match.group(1).lstrip('0')}" if match else "EP"
                row.badge.setText(badge_text)
                
                self.episodes_map[path] = row
                self.episodes_layout.addWidget(row)
                
            row = self.episodes_map[path]
            row.update_status(ep_data.get("db_status", "NOT STARTED"), ep_data.get("stage_results", "{}"))
