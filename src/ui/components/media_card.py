import os
import re
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QEvent, QSequentialAnimationGroup, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QColor, QPen
from PyQt6.QtCore import QRectF, QSize
from PyQt6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QSizePolicy, QDialog,
    QGraphicsOpacityEffect
)

from src.ui.dialogs.flow_details import FlowDetailsModal
from src.ui.dialogs.delete_torrent import DeleteTorrentDialog
from src.ui.conversion_flowchart import ConversionFlowViewer
from src.infrastructure.services.image_downloader import ImageDownloaderThread


# -------------------------------------------------------------
# Base Helper for Pill Columns
# -------------------------------------------------------------
def create_status_column(title_str, min_width):
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


# -------------------------------------------------------------
# Standard Movie Card 
# -------------------------------------------------------------
class MediaCardWidget(QFrame):
    delete_confirmed = pyqtSignal(list, bool, object)  

    def __init__(self, index: int, relative_path: str, title: str, season: str = "", hash_val: str = "", db_id: int = -1, parent=None):
        super().__init__(parent)
        self.flow_index = index
        self.relative_path = relative_path
        self._current_hash = hash_val
        self.db_id = db_id
        self.media_type = "movie"
        
        self.title = title if title else "Unknown Media"
        
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
        self.top_row_container.setMinimumHeight(160)
        self.top_row_container.installEventFilter(self)
        self.top_row_container.setCursor(Qt.CursorShape.PointingHandCursor)

        self.top_row_layout = QHBoxLayout(self.top_row_container)
        self.top_row_layout.setContentsMargins(16, 16, 16, 16)
        self.top_row_layout.setSpacing(20)

        self.lbl_poster = QLabel()
        self.lbl_poster.setFixedSize(85, 128)
        self.lbl_poster.setObjectName("PosterImage")
        self.top_row_layout.addWidget(self.lbl_poster, alignment=Qt.AlignmentFlag.AlignTop)

        info_container = QWidget()
        info_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        
        self.title_lbl = QLabel(self.title)
        self.title_lbl.setObjectName("TitleText")
        
        self.lbl_foldout_genre_rating = QLabel("Genre: N/A | Rating: N/A")
        self.lbl_foldout_genre_rating.setObjectName("SubText")
        
        self.lbl_foldout_desc = QLabel("No description available.")
        self.lbl_foldout_desc.setObjectName("DescText")
        self.lbl_foldout_desc.setWordWrap(True)
        self.lbl_foldout_desc.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.lbl_foldout_desc.setMinimumHeight(70)
        
        info_layout.addWidget(self.title_lbl)
        info_layout.addWidget(self.lbl_foldout_genre_rating)
        info_layout.addWidget(self.lbl_foldout_desc)
        self.top_row_layout.addWidget(info_container)

        status_layout = QHBoxLayout()
        status_layout.setSpacing(24)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        
        ts_container, ts_v = create_status_column("Torrent Status", 110)
        self.lbl_state_val = QLabel("Initializing")
        self.lbl_state_val.setFixedHeight(24)
        self.lbl_state_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_state_val.setProperty("class", "PillUnknown")
        ts_v.addWidget(self.lbl_state_val)
        status_layout.addWidget(ts_container)

        sz_container, sz_v = create_status_column("Torrent Size", 80)
        self.lbl_size_val = QLabel("0 B")
        self.lbl_size_val.setFixedHeight(24)
        self.lbl_size_val.setObjectName("SizeText")
        self.lbl_size_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sz_v.addWidget(self.lbl_size_val)
        status_layout.addWidget(sz_container)

        pr_container, pr_v = create_status_column("Torrent Progress", 90)
        self.prog_bar_dl = QProgressBar()
        self.prog_bar_dl.setRange(0, 100)
        self.prog_bar_dl.setValue(0)
        self.prog_bar_dl.setFormat("%p%")
        self.prog_bar_dl.setFixedSize(80, 24)
        self.prog_bar_dl.setProperty("class", "PbUnknown")
        pr_v.addWidget(self.prog_bar_dl)
        status_layout.addWidget(pr_container)

        sp_container, sp_v = create_status_column("Torrent DL speed", 110)
        self.lbl_speed_display = QLabel("-")
        self.lbl_speed_display.setFixedHeight(24)
        self.lbl_speed_display.setObjectName("SizeText")
        self.lbl_speed_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sp_v.addWidget(self.lbl_speed_display)
        status_layout.addWidget(sp_container)
        
        cs_container, cs_v = create_status_column("Conversion Status", 130)
        self.lbl_conv_status = QLabel("Not Started")
        self.lbl_conv_status.setFixedHeight(24)
        self.lbl_conv_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_conv_status.setProperty("class", "PillUnknown")
        cs_v.addWidget(self.lbl_conv_status)
        status_layout.addWidget(cs_container)

        cp_container, cp_v = create_status_column("Conversion Progress", 130)
        from src.ui.components.progress_pill import ProgressPillWidget
        self.prog_pill_conv = ProgressPillWidget()
        cp_v.addWidget(self.prog_pill_conv)
        status_layout.addWidget(cp_container)

        self.top_row_layout.addLayout(status_layout)
        
        self.action_buttons_container = QWidget()
        self.action_buttons_container.setFixedWidth(100)
        actions_layout = QHBoxLayout(self.action_buttons_container)
        actions_layout.setSpacing(12)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        self.btn_trash_row = QPushButton()
        self.btn_trash_row.setIcon(QIcon(os.path.join(base_dir, "assets", "trash_icon.svg")))
        self.btn_trash_row.setFixedSize(40, 40)
        self.btn_trash_row.setObjectName("DangerIconButton")
        self.btn_trash_row.clicked.connect(self._prompt_delete)
        
        self.btn_expand = QPushButton()
        self.btn_expand.setIcon(QIcon(os.path.join(base_dir, "assets", "chevron_down.svg")))
        self.btn_expand.setFixedSize(40, 40)
        self.btn_expand.setObjectName("ActionIconButton")
        self.btn_expand.clicked.connect(self._toggle_foldout)

        actions_layout.addWidget(self.btn_trash_row)
        actions_layout.addWidget(self.btn_expand)
        self.top_row_layout.addWidget(self.action_buttons_container)

        self.main_layout.addWidget(self.top_row_container)

    def _setup_foldout(self):
        self.foldout_container = QWidget()
        self.foldout_container.setObjectName("FoldoutCard")
        self.foldout_container.setVisible(False)
        self.foldout_container.setMaximumHeight(0) 
        self.foldout_layout = QVBoxLayout(self.foldout_container)
        self.foldout_layout.setContentsMargins(10, 0, 10, 0)
        
        self.flowchart_view = ConversionFlowViewer()
        self.foldout_layout.addWidget(self.flowchart_view)
        self.main_layout.addWidget(self.foldout_container)

    def eventFilter(self, obj, event):
        if obj == self.top_row_container and event.type() == QEvent.Type.MouseButtonRelease:
            if not self.btn_trash_row.underMouse() and not self.btn_expand.underMouse():
                self._toggle_foldout()
                return True
        return super().eventFilter(obj, event)

    def _toggle_foldout(self) -> None:
        is_opening = self.foldout_container.maximumHeight() == 0
        if not hasattr(self, '_foldout_anim'):
            self._foldout_anim = QPropertyAnimation(self.foldout_container, b"maximumHeight", self)
            self._foldout_anim.setDuration(280)
            self._foldout_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._foldout_anim.stop()
        try: self._foldout_anim.finished.disconnect()
        except TypeError: pass

        if is_opening:
            self.foldout_container.setVisible(True)
            target_h = self.foldout_container.sizeHint().height() or 550
            self._foldout_anim.setStartValue(0)
            self._foldout_anim.setEndValue(target_h)
            def on_open_finished(): self.foldout_container.setMaximumHeight(16777215)
            self._foldout_anim.finished.connect(on_open_finished)
            self._foldout_anim.start()
        else:
            def on_close_finished(): self.foldout_container.setVisible(False)
            self._foldout_anim.finished.connect(on_close_finished)
            self._foldout_anim.setStartValue(self.foldout_container.height())
            self._foldout_anim.setEndValue(0)
            self._foldout_anim.start()

    def _prompt_delete(self) -> None:
        dialog = DeleteTorrentDialog(self.title, self.window())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.delete_confirmed.emit([self._current_hash] if self._current_hash else [], dialog.should_delete_files(), self)

    def set_poster_pixmap(self, raw_pixmap: QPixmap) -> None:
        scaled = raw_pixmap.scaled(self.lbl_poster.width(), self.lbl_poster.height(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        rounded = QPixmap(scaled.size())
        rounded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, scaled.width(), scaled.height()), 8, 8)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled)
        painter.end()
        self.lbl_poster.setPixmap(rounded)
        self.lbl_poster.setText("")

    def update_metadata(self, title: str, desc: str, genre: str, rating: str):
        self.title = title
        self.title_lbl.setText(title)
        self.lbl_foldout_desc.setText(desc)
        self.lbl_foldout_genre_rating.setText(f"Genre: {genre} | Rating: ★ {rating}")

    def update_torrent_ui(self, human_state, pill_class, pb_style, prog_val, size_str, speed_str, active_state_str):
        self.lbl_state_val.setText(human_state)
        self.lbl_state_val.setProperty("class", pill_class)
        self.lbl_state_val.style().unpolish(self.lbl_state_val)
        self.lbl_state_val.style().polish(self.lbl_state_val)
            
        self.prog_bar_dl.setProperty("class", pb_style)
        self.prog_bar_dl.style().unpolish(self.prog_bar_dl)
        self.prog_bar_dl.style().polish(self.prog_bar_dl)
            
        self.lbl_size_val.setText(size_str)
        self.prog_bar_dl.setValue(int(prog_val * 100))
        self.lbl_speed_display.setText("-" if prog_val >= 1.0 or "0.0 MB" in speed_str else speed_str)

    def update_telemetry_ui(self, episodes_data: list):
        if not episodes_data: return
        first_ep = episodes_data[0]
        db_status = first_ep.get("db_status", first_ep.get("status", "NOT STARTED")).upper()
        from src.ui.components.progress_pill import calculate_conversion_progress
        state_text, percentage = calculate_conversion_progress(first_ep)
        
        if db_status == "COMPLETED":
            percentage = 100
            state_text = "Completed"

        pill_css = "PillUnknown"
        if state_text == "Completed": pill_css = "PillSuccess"
        elif "Failed" in state_text: pill_css = "PillDanger"
        elif percentage > 0: pill_css = "PillActive"

        self.lbl_conv_status.setText(state_text)
        self.lbl_conv_status.setProperty("class", pill_css)
        self.lbl_conv_status.style().unpolish(self.lbl_conv_status)
        self.lbl_conv_status.style().polish(self.lbl_conv_status)
        self.prog_pill_conv.set_data(state_text, percentage)
        
        stage_flags_raw = first_ep.get("stage_results", {})
        if isinstance(stage_flags_raw, str):
            try:
                import json
                stage_flags = json.loads(stage_flags_raw) if stage_flags_raw else {}
            except Exception:
                stage_flags = {}
        else:
            stage_flags = stage_flags_raw.copy() if stage_flags_raw else {}
            
        if db_status == "COMPLETED":
            stage_flags["p8-complete"] = True
            if not any(k.startswith("p3-") for k in stage_flags):
                stage_flags["p1-input"] = True; stage_flags["p1-queue"] = True
                stage_flags["p2-dequeue"] = True; stage_flags["p2-pass"] = True
                stage_flags["p3-router"] = True
                stage_flags["p3-movie"] = True
                stage_flags["p4-movie"] = True
                stage_flags["p5-check"] = True; stage_flags["p5-pass"] = True
                stage_flags["p8-relocate"] = True
                stage_flags["p8-movie"] = True
                stage_flags["p8-cleanup"] = True

        self.flowchart_view.update_pipeline_state(stage_flags)


# -------------------------------------------------------------
# TV Series Episode Child Row (No Torrent Details, Expandable)
# -------------------------------------------------------------
class EpisodeRowWidget(QFrame):
    """Episode row designed to perfectly mimic the standard movie row, strictly indented beneath the season parent."""
    delete_episode = pyqtSignal(str) 

    def __init__(self, ep_name: str, ep_desc: str = "No description available.", path: str = "", ep_num: int = None, rating: str = "-", parent=None):
        super().__init__(parent)
        self.ep_name = ep_name
        self.ep_num = ep_num
        self.ep_path = path
        self.ep_rating = rating
        self._image_thread = None
        
        self.setObjectName("MediaCardWrapper")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0) 
        self.main_layout.setSpacing(0)
        
        self.top_row_container = QWidget()
        self.top_row_container.setObjectName("TopRow") 
        self.top_row_container.setMinimumHeight(140) 
        self.top_row_container.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(self.top_row_container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)
        
        self.badge = QLabel("EP")
        self.badge.setFixedSize(60, 85)
        self.badge.setObjectName("EpisodeBadge")
        self.badge.setStyleSheet("background-color: #3B82F6; border-radius: 8px; font-size: 16px; font-weight: bold; color: white;")
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.badge, alignment=Qt.AlignmentFlag.AlignTop)
        
        info_container = QWidget()
        info_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        
        ep_display = f"Episode {ep_num} - {ep_name}" if ep_num else ep_name
        self.title_lbl = QLabel(ep_display)
        self.title_lbl.setObjectName("TitleText")
        
        rating_str = f"Rating: ★ {rating}" if rating and rating != "-" else "Rating: N/A"
        self.sub_lbl = QLabel(rating_str)
        self.sub_lbl.setObjectName("SubText")
        
        self.lbl_desc = QLabel(ep_desc)
        self.lbl_desc.setObjectName("DescText")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        info_layout.addWidget(self.title_lbl)
        info_layout.addWidget(self.sub_lbl)
        info_layout.addWidget(self.lbl_desc)
        layout.addWidget(info_container)
        
        status_layout = QHBoxLayout()
        status_layout.setSpacing(24)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)

        cs_container, cs_v = create_status_column("Conversion Status", 130)
        self.lbl_conv_status = QLabel("Not Started")
        self.lbl_conv_status.setFixedHeight(24)
        self.lbl_conv_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_conv_status.setProperty("class", "PillUnknown")
        cs_v.addWidget(self.lbl_conv_status)
        status_layout.addWidget(cs_container)

        cp_container, cp_v = create_status_column("Conversion Progress", 130)
        from src.ui.components.progress_pill import ProgressPillWidget
        self.prog_pill_conv = ProgressPillWidget()
        cp_v.addWidget(self.prog_pill_conv)
        status_layout.addWidget(cp_container)

        layout.addLayout(status_layout)

        # Exact matched buttons wrapper container
        self.action_buttons_container = QWidget()
        self.action_buttons_container.setFixedWidth(100)
        actions_layout = QHBoxLayout(self.action_buttons_container)
        actions_layout.setSpacing(12)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        self.btn_trash_row = QPushButton()
        self.btn_trash_row.setIcon(QIcon(os.path.join(base_dir, "assets", "trash_icon.svg")))
        self.btn_trash_row.setFixedSize(40, 40)
        self.btn_trash_row.setObjectName("DangerIconButton")
        self.btn_trash_row.clicked.connect(self._prompt_delete)
        
        self.btn_expand = QPushButton()
        self.btn_expand.setIcon(QIcon(os.path.join(base_dir, "assets", "chevron_down.svg")))
        self.btn_expand.setFixedSize(40, 40)
        self.btn_expand.setObjectName("ActionIconButton")
        self.btn_expand.clicked.connect(self._toggle_foldout)

        actions_layout.addWidget(self.btn_trash_row)
        actions_layout.addWidget(self.btn_expand)
        layout.addWidget(self.action_buttons_container)

        self.main_layout.addWidget(self.top_row_container)

        self.foldout_container = QWidget()
        self.foldout_container.setObjectName("FoldoutCard")
        self.foldout_container.setVisible(False)
        self.foldout_container.setMaximumHeight(0) 
        self.foldout_layout = QVBoxLayout(self.foldout_container)
        self.foldout_layout.setContentsMargins(10, 0, 10, 0)
        
        self.flowchart_view = ConversionFlowViewer()
        self.foldout_layout.addWidget(self.flowchart_view)
        self.main_layout.addWidget(self.foldout_container)

        self.top_row_container.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.top_row_container and event.type() == QEvent.Type.MouseButtonRelease:
            if not self.btn_trash_row.underMouse() and not self.btn_expand.underMouse():
                self._toggle_foldout()
                return True
        return super().eventFilter(obj, event)

    def _toggle_foldout(self) -> None:
        is_opening = self.foldout_container.maximumHeight() == 0
        if not hasattr(self, '_foldout_anim'):
            self._foldout_anim = QPropertyAnimation(self.foldout_container, b"maximumHeight", self)
            self._foldout_anim.setDuration(280)
            self._foldout_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._foldout_anim.stop()
        try: self._foldout_anim.finished.disconnect()
        except TypeError: pass

        if is_opening:
            self.foldout_container.setVisible(True)
            target_h = self.foldout_container.sizeHint().height() or 550
            self._foldout_anim.setStartValue(0)
            self._foldout_anim.setEndValue(target_h)
            def on_open_finished(): self.foldout_container.setMaximumHeight(16777215)
            self._foldout_anim.finished.connect(on_open_finished)
            self._foldout_anim.start()
        else:
            def on_close_finished(): self.foldout_container.setVisible(False)
            self._foldout_anim.finished.connect(on_close_finished)
            self._foldout_anim.setStartValue(self.foldout_container.height())
            self._foldout_anim.setEndValue(0)
            self._foldout_anim.start()

    def _prompt_delete(self) -> None:
        dialog = DeleteTorrentDialog(self.ep_name, self.window())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.delete_episode.emit(self.ep_path)

    def update_tmdb_data(self, title: str, overview: str, still_url: str = "", rating: str = None):
        if title:
            self.ep_name = title
            ep_display = f"Episode {self.ep_num} - {title}" if self.ep_num else title
            self.title_lbl.setText(ep_display)
        if overview:
            self.lbl_desc.setText(overview)
        if rating is not None:
            self.ep_rating = rating
            rating_str = f"Rating: ★ {rating}" if rating and rating != "-" else "Rating: N/A"
            self.sub_lbl.setText(rating_str)
        if still_url:
            self._fetch_episode_image(still_url)

    def _fetch_episode_image(self, url: str):
        self._image_thread = ImageDownloaderThread(url, self)
        self._image_thread.finished.connect(self._on_image_downloaded)
        self._image_thread.start()

    def _on_image_downloaded(self, image_bytes: bytes) -> None:
        if image_bytes:
            pixmap = QPixmap()
            if pixmap.loadFromData(image_bytes):
                # Scale the horizontal still into a center-cropped vertical thumbnail slice
                scaled = pixmap.scaled(self.badge.width(), self.badge.height(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                rounded = QPixmap(scaled.size())
                rounded.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                
                path = QPainterPath()
                path.addRoundedRect(QRectF(0, 0, scaled.width(), scaled.height()), 8, 8)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, scaled)
                painter.end()
                
                self.badge.setPixmap(rounded)
                self.badge.setText("")
                self.badge.setStyleSheet("background-color: transparent;")

    def update_status(self, ep_data: dict):
        from src.ui.components.progress_pill import calculate_conversion_progress
        state_text, percentage = calculate_conversion_progress(ep_data)
        
        pill_css = "PillUnknown"
        if state_text == "Completed": pill_css = "PillSuccess"
        elif "Failed" in state_text: pill_css = "PillDanger"
        elif percentage > 0: pill_css = "PillActive"

        self.lbl_conv_status.setText(state_text)
        self.lbl_conv_status.setProperty("class", pill_css)
        self.lbl_conv_status.style().unpolish(self.lbl_conv_status)
        self.lbl_conv_status.style().polish(self.lbl_conv_status)
        self.prog_pill_conv.set_data(state_text, percentage)

        stage_flags_raw = ep_data.get("stage_results", {})
        if isinstance(stage_flags_raw, str):
            try:
                import json
                stage_flags = json.loads(stage_flags_raw) if stage_flags_raw else {}
            except Exception:
                stage_flags = {}
        else:
            stage_flags = stage_flags_raw.copy() if stage_flags_raw else {}
            
        db_status = (ep_data.get("db_status") or ep_data.get("status") or "").upper()
        if db_status == "COMPLETED":
            stage_flags["p8-complete"] = True
            if not any(k.startswith("p3-") for k in stage_flags):
                stage_flags["p1-input"] = True; stage_flags["p1-queue"] = True
                stage_flags["p2-dequeue"] = True; stage_flags["p2-pass"] = True
                stage_flags["p3-router"] = True
                stage_flags["p3-tv"] = True
                stage_flags["p4-tv"] = True
                stage_flags["p5-check"] = True; stage_flags["p5-pass"] = True
                stage_flags["p8-relocate"] = True
                stage_flags["p8-tv"] = True
                stage_flags["p8-cleanup"] = True

        self.flowchart_view.update_pipeline_state(stage_flags)


# -------------------------------------------------------------
# TV Series Parent Card (With full Torrent Details + Aggregate logic)
# -------------------------------------------------------------
class SeriesCardWidget(QWidget): 
    """Parent Row for a Season. Cleanly isolates standard row styling preventing foldout leakage."""
    delete_confirmed = pyqtSignal(list, bool, object)

    def __init__(self, index: int, relative_path: str, title: str, season: str, is_season: bool = False, hash_val: str = "", db_id: int = -1, parent=None):
        super().__init__(parent)
        self.flow_index = index
        self.db_id = db_id
        self.media_type = "tv-series"
        self.relative_path = relative_path
        self._current_hash = hash_val
        self.season = season
        self.is_season = is_season
        self.episodes_map = {} 
        self._expanded = False
        
        base_title = title if title else "Unknown Media"
        if season and "Season" not in base_title:
            s_num = re.sub(r'\D', '', str(season))
            if s_num:
                self.title = f"{base_title} - Season {s_num}"
            else:
                self.title = base_title
        else:
            self.title = base_title
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(8) 

        # Using a structural replica of the standard MediaCard to guarantee identical CSS mappings
        self.top_row_wrapper = QFrame() 
        self.top_row_wrapper.setObjectName("MediaCardWrapper") 
        self.top_row_wrapper.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        wrapper_layout = QVBoxLayout(self.top_row_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)
        
        self.top_row_container = QWidget()
        self.top_row_container.setObjectName("TopRow")
        self.top_row_container.setMinimumHeight(160)
        self.top_row_container.setCursor(Qt.CursorShape.PointingHandCursor)
        self.top_row_container.installEventFilter(self)
        
        top_layout = QHBoxLayout(self.top_row_container)
        top_layout.setContentsMargins(16, 16, 16, 16)
        top_layout.setSpacing(20)

        self.lbl_poster = QLabel()
        self.lbl_poster.setFixedSize(85, 128)
        self.lbl_poster.setObjectName("PosterImage")
        top_layout.addWidget(self.lbl_poster, alignment=Qt.AlignmentFlag.AlignTop)

        info_v = QVBoxLayout()
        info_v.setContentsMargins(0, 0, 0, 0)
        info_v.setSpacing(4)
        
        self.title_lbl = QLabel(self.title)
        self.title_lbl.setObjectName("TitleText")
        self.lbl_genre = QLabel("Genre: N/A | Rating: N/A")
        self.lbl_genre.setObjectName("SubText")
        self.lbl_desc = QLabel("No description available.")
        self.lbl_desc.setObjectName("DescText")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.lbl_desc.setMinimumHeight(70)
        
        info_v.addWidget(self.title_lbl)
        info_v.addWidget(self.lbl_genre)
        info_v.addWidget(self.lbl_desc)
        top_layout.addLayout(info_v, 1)

        status_layout = QHBoxLayout()
        status_layout.setSpacing(24)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        
        ts_container, ts_v = create_status_column("Torrent Status", 110)
        self.lbl_state_val = QLabel("Initializing")
        self.lbl_state_val.setFixedHeight(24)
        self.lbl_state_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_state_val.setProperty("class", "PillUnknown")
        ts_v.addWidget(self.lbl_state_val)
        status_layout.addWidget(ts_container)

        sz_container, sz_v = create_status_column("Torrent Size", 80)
        self.lbl_size_val = QLabel("0 B")
        self.lbl_size_val.setFixedHeight(24)
        self.lbl_size_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sz_v.addWidget(self.lbl_size_val)
        status_layout.addWidget(sz_container)

        pr_container, pr_v = create_status_column("Torrent Progress", 90)
        self.prog_bar_dl = QProgressBar()
        self.prog_bar_dl.setRange(0, 100)
        self.prog_bar_dl.setValue(0)
        self.prog_bar_dl.setFormat("%p%")
        self.prog_bar_dl.setFixedSize(80, 24)
        self.prog_bar_dl.setProperty("class", "PbUnknown")
        pr_v.addWidget(self.prog_bar_dl)
        status_layout.addWidget(pr_container)

        sp_container, sp_v = create_status_column("Torrent DL speed", 110)
        self.lbl_speed_display = QLabel("-")
        self.lbl_speed_display.setFixedHeight(24)
        self.lbl_speed_display.setObjectName("SizeText")
        self.lbl_speed_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sp_v.addWidget(self.lbl_speed_display)
        status_layout.addWidget(sp_container)

        cs_container, cs_v = create_status_column("Season Status", 150)
        self.lbl_conv_status = QLabel("Not Started")
        self.lbl_conv_status.setFixedHeight(24)
        self.lbl_conv_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_conv_status.setProperty("class", "PillUnknown")
        cs_v.addWidget(self.lbl_conv_status)
        status_layout.addWidget(cs_container)

        cp_container, cp_v = create_status_column("Season Progress", 130)
        from src.ui.components.progress_pill import ProgressPillWidget
        self.prog_pill_conv = ProgressPillWidget()
        cp_v.addWidget(self.prog_pill_conv)
        status_layout.addWidget(cp_container)
        
        top_layout.addLayout(status_layout)

        # Exact matched buttons wrapper container
        self.action_buttons_container = QWidget()
        self.action_buttons_container.setFixedWidth(100)
        actions_layout = QHBoxLayout(self.action_buttons_container)
        actions_layout.setSpacing(12)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        self.btn_trash_row = QPushButton()
        self.btn_trash_row.setIcon(QIcon(os.path.join(base_dir, "assets", "trash_icon.svg")))
        self.btn_trash_row.setFixedSize(40, 40)
        self.btn_trash_row.setObjectName("DangerIconButton")
        self.btn_trash_row.clicked.connect(self._prompt_delete)
        
        self.btn_expand = QPushButton()
        self.btn_expand.setFixedSize(40, 40)
        self.btn_expand.setObjectName("ActionIconButton")
        self.btn_expand.setIcon(QIcon(os.path.join(base_dir, "assets", "chevron_down.svg")))
        self.btn_expand.clicked.connect(self._toggle_episodes)
        
        actions_layout.addWidget(self.btn_trash_row)
        actions_layout.addWidget(self.btn_expand)
        top_layout.addWidget(self.action_buttons_container)

        wrapper_layout.addWidget(self.top_row_container)
        self.main_layout.addWidget(self.top_row_wrapper)

        self.episodes_container = QWidget()
        self.episodes_container.setObjectName("EpisodesContainer")
        self.episodes_container.setStyleSheet("background: transparent;")
        
        self.episodes_layout = QVBoxLayout(self.episodes_container)
        self.episodes_layout.setContentsMargins(40, 0, 0, 0)
        self.episodes_layout.setSpacing(6)
        
        self.episodes_container.setVisible(False)
        self.episodes_container.setMaximumHeight(0)
        self.main_layout.addWidget(self.episodes_container)

    def eventFilter(self, obj, event):
        if obj == self.top_row_container and event.type() == QEvent.Type.MouseButtonRelease:
            if not self.btn_trash_row.underMouse() and not self.btn_expand.underMouse():
                self._toggle_episodes()
                return True
        return super().eventFilter(obj, event)

    def close_flow(self):
        self.deleteLater()

    def _toggle_episodes(self):
        self._expanded = not self._expanded
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        if not hasattr(self, '_ep_anim'):
            self._ep_anim = QPropertyAnimation(self.episodes_container, b"maximumHeight", self)
            self._ep_anim.setDuration(280)
            self._ep_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._ep_anim.stop()
        try: self._ep_anim.finished.disconnect()
        except TypeError: pass
        
        if self._expanded:
            self.episodes_container.setVisible(True)
            self.btn_expand.setIcon(QIcon(os.path.join(base_dir, "assets", "chevron_up.svg")))
            target_h = self.episodes_container.sizeHint().height() or 400
            self._ep_anim.setStartValue(0)
            self._ep_anim.setEndValue(target_h)
            def on_ep_open(): self.episodes_container.setMaximumHeight(16777215)
            self._ep_anim.finished.connect(on_ep_open)
            self._ep_anim.start()
        else:
            self.btn_expand.setIcon(QIcon(os.path.join(base_dir, "assets", "chevron_down.svg")))
            def on_ep_close(): self.episodes_container.setVisible(False)
            self._ep_anim.finished.connect(on_ep_close)
            self._ep_anim.setStartValue(self.episodes_container.height())
            self._ep_anim.setEndValue(0)
            self._ep_anim.start()

    def update_metadata(self, title, desc, genre, rating):
        display_title = title
        if self.season and "Season" not in title:
            s_num = re.sub(r'\D', '', str(self.season))
            if s_num:
                display_title = f"{title} - Season {s_num}"
                
        self.title = display_title
        self.title_lbl.setText(display_title)
        self.lbl_desc.setText(desc)
        self.lbl_genre.setText(f"Genre: {genre} | Rating: ★ {rating}")

    def set_poster_pixmap(self, raw_pixmap):
        scaled = raw_pixmap.scaled(self.lbl_poster.width(), self.lbl_poster.height(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        rounded = QPixmap(scaled.size())
        rounded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, scaled.width(), scaled.height()), 8, 8)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled)
        painter.end()
        self.lbl_poster.setPixmap(rounded)
        self.lbl_poster.setText("")

    def update_torrent_ui(self, human_state, pill_class, pb_style, prog_val, size_str, speed_str, active_state_str):
        self.lbl_state_val.setText(human_state)
        self.lbl_state_val.setProperty("class", pill_class)
        self.lbl_state_val.style().unpolish(self.lbl_state_val)
        self.lbl_state_val.style().polish(self.lbl_state_val)
            
        self.prog_bar_dl.setProperty("class", pb_style)
        self.prog_bar_dl.style().unpolish(self.prog_bar_dl)
        self.prog_bar_dl.style().polish(self.prog_bar_dl)
            
        self.lbl_size_val.setText(size_str)
        self.lbl_speed_display.setText(speed_str)
        self.prog_bar_dl.setValue(int(prog_val * 100))

    def _ensure_episode_row(self, rel_path: str, tmdb_episodes: dict = None):
        if rel_path in self.episodes_map:
            row = self.episodes_map[rel_path]
            match = re.search(r'[sS]?(\d{1,2})[xXeE](\d{1,2})', rel_path)
            if not match: match = re.search(r'[eE](\d{1,2})', rel_path)
            ep_num = int(match.group(2)) if match and len(match.groups()) > 1 else (int(match.group(1)) if match else None)
            
            if ep_num and tmdb_episodes:
                ep_data = tmdb_episodes.get(ep_num) or tmdb_episodes.get(str(ep_num))
                if ep_data:
                    ep_vote = ep_data.get('vote_average', '-')
                    ep_rating_str = str(round(float(ep_vote), 1)) if ep_vote and ep_vote != '-' else '-'
                    row.update_tmdb_data(
                        ep_data.get('name'), 
                        ep_data.get('overview'),
                        ep_data.get('still_url', ''),
                        rating=ep_rating_str
                    )
            return row
            
        match = re.search(r'[sS]?(\d{1,2})[xXeE](\d{1,2})', rel_path)
        if not match: match = re.search(r'[eE](\d{1,2})', rel_path)
        ep_num = int(match.group(2)) if match and len(match.groups()) > 1 else (int(match.group(1)) if match else None)
        
        display_title = os.path.basename(rel_path)
        desc = "No description available."
        still_url = ""
        
        ep_rating = "-"
        if tmdb_episodes and ep_num:
            ep_data = tmdb_episodes.get(ep_num) or tmdb_episodes.get(str(ep_num))
            if ep_data:
                display_title = ep_data.get('name', display_title)
                desc = ep_data.get('overview', desc)
                still_url = ep_data.get('still_url', "")
                ep_rating = ep_data.get('vote_average', '-')
                if ep_rating and ep_rating != '-':
                    ep_rating = str(round(float(ep_rating), 1))
        
        row = EpisodeRowWidget(display_title, desc, path=rel_path, ep_num=ep_num, rating=ep_rating)
        if ep_num:
            row.badge.setText(f"EP {ep_num}")
            
        if still_url:
            row.update_tmdb_data(display_title, desc, still_url)
            
        self.episodes_map[rel_path] = row
        self.episodes_layout.addWidget(row)
        return row

    def populate_episodes_from_files(self, files: list, tmdb_episodes: dict = None):
        video_extensions = ('.mp4', '.mkv', '.avi', '.m4v')
        video_files = [f for f in files if f.get('name', '').lower().endswith(video_extensions)]
        
        for f_info in sorted(video_files, key=lambda x: x.get('name', '')):
            rel_path = f_info.get('name', '')
            if not rel_path: continue
            self._ensure_episode_row(rel_path, tmdb_episodes)

    def update_telemetry_ui(self, episodes_data: list):
        if not episodes_data: return
        
        total_completed = 0
        active_status_text = "Not Started"
        
        for ep_data in episodes_data:
            path = ep_data.get("path", "")
            if not path: continue
            
            row = self.episodes_map.get(path)
            if not row:
                fname = os.path.basename(path)
                for qbit_path, widget in self.episodes_map.items():
                    if os.path.basename(qbit_path) == fname:
                        row = widget
                        break
                        
            if not row:
                row = self._ensure_episode_row(path, getattr(self, '_cached_tmdb_eps', None))
            
            from src.ui.components.progress_pill import calculate_conversion_progress
            state_text, ep_prog = calculate_conversion_progress(ep_data)
            
            if row:
                row.update_status(ep_data)

            if ep_prog == 100 or state_text == "Completed":
                total_completed += 1
            elif ep_prog > 0 and active_status_text == "Not Started":
                ep_badge = row.badge.text() if row else "EP?"
                active_status_text = f"{ep_badge} - {state_text}"

        total_eps = len(self.episodes_map) if self.episodes_map else len(episodes_data)
        if total_eps == 0: total_eps = 1

        aggregate_progress = int((total_completed / total_eps) * 100)
        
        if total_completed == total_eps: final_status = "Completed"
        elif aggregate_progress > 0 or active_status_text != "Not Started": final_status = active_status_text
        else: final_status = "Not Started"
            
        pill_css = "PillUnknown"
        if final_status == "Completed": pill_css = "PillSuccess"
        elif "Failed" in final_status: pill_css = "PillDanger"
        elif aggregate_progress > 0 or final_status != "Not Started": pill_css = "PillActive"

        self.lbl_conv_status.setText(final_status)
        self.lbl_conv_status.setProperty("class", pill_css)
        self.lbl_conv_status.style().unpolish(self.lbl_conv_status)
        self.lbl_conv_status.style().polish(self.lbl_conv_status)
        self.prog_pill_conv.set_data(final_status, aggregate_progress)

    def _prompt_delete(self) -> None:
        dialog = DeleteTorrentDialog(self.title, self.window())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.delete_confirmed.emit([self._current_hash] if self._current_hash else [], dialog.should_delete_files(), self)