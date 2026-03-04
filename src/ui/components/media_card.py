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
        self.setObjectName("MediaCardWrapper")
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
        self.top_row_container.setObjectName("TopRow")
        
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
        self.lbl_state_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_state_val.setProperty("class", "PillUnknown")
        ts_v.addWidget(self.lbl_state_val)
        status_layout.addWidget(ts_container)

        sz_container, sz_v = create_col("Size", 80)
        self.lbl_size_val = QLabel("0 B")
        self.lbl_size_val.setObjectName("SizeText")
        self.lbl_size_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sz_v.addWidget(self.lbl_size_val)
        status_layout.addWidget(sz_container)

        pr_container, pr_v = create_col("Progress", 80)
        self.prog_bar_dl = QProgressBar()
        self.prog_bar_dl.setRange(0, 100)
        self.prog_bar_dl.setValue(0)
        self.prog_bar_dl.setFormat("%p%")
        self.prog_bar_dl.setFixedSize(70, 24)
        self.prog_bar_dl.setProperty("class", "PbUnknown")
        pr_v.addWidget(self.prog_bar_dl)
        status_layout.addWidget(pr_container)
        
        cs_container, cs_v = create_col("Conversion", 110)
        self.lbl_conv_state_val = QLabel("NOT STARTED")
        self.lbl_conv_state_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_conv_state_val.setProperty("class", "PillUnknown")
        self.prog_bar_conv = QProgressBar()
        self.prog_bar_conv.setRange(0, 100)
        self.prog_bar_conv.setFixedSize(80, 15)
        self.prog_bar_conv.hide()
        cs_v.addWidget(self.lbl_conv_state_val)
        cs_v.addWidget(self.prog_bar_conv)
        status_layout.addWidget(cs_container)

        self.top_row_layout.addLayout(status_layout)
        
        # 4. Actions
        self.action_buttons_container = QWidget()
        self.action_buttons_container.setFixedWidth(100)
        
        actions_layout = QHBoxLayout(self.action_buttons_container)
        actions_layout.setSpacing(12)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        trash_icon_path = os.path.join(base_dir, "assets", "trash_icon.svg")
        chev_down_path = os.path.join(base_dir, "assets", "chevron_down.svg")
        
        self.btn_trash_row = QPushButton()
        self.btn_trash_row.setIcon(QIcon(trash_icon_path))
        self.btn_trash_row.setIconSize(QSize(18, 18))
        self.btn_trash_row.setFixedSize(36, 36)
        self.btn_trash_row.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_trash_row.setObjectName("DangerIconButton")
        self.btn_trash_row.clicked.connect(self._prompt_delete)
        
        self.btn_expand = QPushButton()
        self.btn_expand.setIcon(QIcon(chev_down_path))
        self.btn_expand.setIconSize(QSize(22, 22))
        self.btn_expand.setFixedSize(36, 36)
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
        self.title_lbl.setText(title)
        self.lbl_foldout_desc.setText(desc)
        self.lbl_foldout_genre_rating.setText(f"Genre: {genre} | Rating: ★ {rating}")

    def update_torrent_ui(self, human_state: str, state_css: str, pb_style: str, prog_val: float, size_str: str, speed_str: str, active_state_str: str):
        self._active_qbit_state = active_state_str
        self.lbl_state_val.setText(human_state)
        self.lbl_state_val.setStyleSheet(state_css)
        self.prog_bar_dl.setStyleSheet(pb_style)
        self.lbl_size_val.setText(size_str)
        self.prog_bar_dl.setValue(int(prog_val * 100))
        self.lbl_speed_val.setText(speed_str)

    def update_telemetry_ui(self, db_status: str, sub_status: str, prog: int, pill_css: str, ff_out: str, stage_flags_json: str):
        self._active_qbit_state = f"DB Status: {db_status}"
        self._active_ffmpeg_log = ff_out
        
        self.lbl_conv_state_val.setText(db_status)
        self.lbl_conv_state_val.setStyleSheet(pill_css)
        self.lbl_foldout_db_status.setText(f"Conversion Status: {db_status}")
        self.lbl_foldout_sub_status.setText(f"Subtitles: {sub_status}")
        
        if hasattr(self, 'flowchart_view') and stage_flags_json:
            self.flowchart_view.update_pipeline_state(stage_flags_json)
