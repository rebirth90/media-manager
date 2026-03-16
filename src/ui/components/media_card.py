import os
import re
import qbittorrentapi
from datetime import datetime
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QEvent, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QDesktopServices
from PyQt6.QtCore import QRectF, QSize
from PyQt6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QDialog,
    QScrollArea
)

from src.ui.dialogs.delete_torrent import DeleteTorrentDialog
from src.ui.conversion_flowchart import ConversionFlowViewer
from src.infrastructure.services.image_downloader import ImageDownloaderThread
from src.presentation.utils.ui_helpers import apply_blur_effect, remove_blur_effect


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


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _format_size_bytes(num_bytes: int) -> str:
    size = float(max(0, _safe_int(num_bytes)))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        # Match qBittorrent display units (SI/base-10).
        if size < 1000.0 or unit == "TB":
            return f"{size:.2f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1000.0
    return "0 B"


def _format_size_text_two_decimals(size_text: str) -> str:
    text = str(size_text or "").strip()
    if not text:
        return "0 B"
    match = re.match(r'^\s*([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z/]+)\s*$', text)
    if not match:
        return text
    value = _safe_float(match.group(1), 0.0)
    unit = match.group(2)
    if unit.upper() == "B":
        return f"{int(value)} B"
    return f"{value:.2f} {unit}"


def _minutes_from_general_log(log_path: str) -> float:
    if not log_path or not os.path.exists(log_path):
        return 0.0
    start_ts = None
    end_ts = None
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                ts_match = re.match(r'^(\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2})\s+-', line)
                if not ts_match:
                    continue
                if "PIPELINE STARTED" in line and start_ts is None:
                    start_ts = datetime.strptime(ts_match.group(1), "%Y-%m-%d_%H:%M:%S")
                if "PIPELINE SUCCESS" in line:
                    end_ts = datetime.strptime(ts_match.group(1), "%Y-%m-%d_%H:%M:%S")
        if start_ts and end_ts and end_ts >= start_ts:
            return round((end_ts - start_ts).total_seconds() / 60.0, 2)
    except Exception:
        return 0.0
    return 0.0


def _minutes_from_general_log_text(log_text: str) -> float:
    if not log_text:
        return 0.0
    start_ts = None
    end_ts = None
    try:
        for line in str(log_text).splitlines():
            ts_match = re.match(r'^(\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2})\s+-', line)
            if not ts_match:
                continue
            if "PIPELINE STARTED" in line and start_ts is None:
                start_ts = datetime.strptime(ts_match.group(1), "%Y-%m-%d_%H:%M:%S")
            if "PIPELINE SUCCESS" in line:
                end_ts = datetime.strptime(ts_match.group(1), "%Y-%m-%d_%H:%M:%S")
        if start_ts and end_ts and end_ts >= start_ts:
            return round((end_ts - start_ts).total_seconds() / 60.0, 2)
    except Exception:
        return 0.0
    return 0.0


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
        self._qbit_initial_size_bytes = 0
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
        from src.ui.components.progress_pill import ProgressPillWidget
        self.prog_bar_dl = ProgressPillWidget()
        self.prog_bar_dl.set_data("Not Started", 0)
        self.prog_bar_dl.setFixedSize(90, 24)
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

        cp_container, cp_v = create_status_column("Conversion Progress", 90)
        from src.ui.components.progress_pill import ProgressPillWidget
        self.prog_pill_conv = ProgressPillWidget()
        self.prog_pill_conv.setFixedSize(90, 24)
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

        self._gen_log_local_path = ""
        self._ff_log_local_path = ""
        self._build_foldout_summary_panel()
        
        self.flowchart_view = ConversionFlowViewer()
        self.flowchart_view.height_calculated.connect(self._sync_foldout_height)
        self.foldout_layout.addWidget(self.flowchart_view)
        self.main_layout.addWidget(self.foldout_container)

    def _build_foldout_summary_panel(self) -> None:
        panel = QWidget()
        panel.setObjectName("FoldoutStatsPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 10, 8, 8)
        panel_layout.setSpacing(4)

        row_metrics = QHBoxLayout()
        row_metrics.setSpacing(18)

        self.lbl_initial_size = QLabel("Initial size: -")
        self.lbl_final_size = QLabel("Final size: -")
        self.lbl_total_minutes = QLabel("Total conversion time: -")
        for lbl in (self.lbl_initial_size, self.lbl_final_size, self.lbl_total_minutes):
            lbl.setObjectName("SubText")
            row_metrics.addWidget(lbl)

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        log_icon_path = os.path.join(base_dir, "assets", "icons8-log.svg")
        self.btn_general_log = QPushButton("General log")
        self.btn_ffmpeg_log = QPushButton("FFmpeg log")
        for btn in (self.btn_general_log, self.btn_ffmpeg_log):
            btn.setObjectName("ActionIconButton")
            btn.setMinimumHeight(36)
            btn.setMinimumWidth(112)
            btn.setIcon(QIcon(log_icon_path))
            btn.setIconSize(QSize(18, 18))
            btn.setEnabled(False)
        self.btn_general_log.clicked.connect(lambda: self._open_log_file(self._gen_log_local_path))
        self.btn_ffmpeg_log.clicked.connect(lambda: self._open_log_file(self._ff_log_local_path))

        row_metrics.addStretch(1)
        row_metrics.addWidget(self.btn_general_log)
        row_metrics.addWidget(self.btn_ffmpeg_log)
        panel_layout.addLayout(row_metrics)

        self.foldout_layout.addWidget(panel)

    def _open_log_file(self, file_path: str) -> None:
        if not file_path or not os.path.exists(file_path):
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

    def _resolve_movie_qbit_initial_size(self) -> int:
        current_hash = str(getattr(self, '_current_hash', '') or '')
        if not current_hash:
            return 0
        try:
            host = os.getenv("QBIT_HOST")
            port = os.getenv("QBIT_PORT")
            user = os.getenv("QBIT_USER")
            pwd = os.getenv("QBIT_PASS")
            if not all([host, port, user, pwd]):
                return 0

            client = qbittorrentapi.Client(
                host=f"http://{host}:{port}",
                username=user,
                password=pwd,
            )
            client.auth_log_in()
            torrents = client.torrents_info()
            matched = next((t for t in torrents if str(t.get("hash", "")) == current_hash), None)
            if not matched:
                return 0
            raw_size = matched.get("total_size")
            if raw_size is None:
                raw_size = matched.get("size", 0)
            return _safe_int(raw_size, 0)
        except Exception:
            return 0

    def _update_foldout_summary(self, telemetry: dict, db_status: str) -> None:
        # Source of truth: qBittorrent torrent size for movies.
        initial_size = _safe_int(self._qbit_initial_size_bytes)
        if initial_size <= 0:
            initial_size = self._resolve_movie_qbit_initial_size()
            if initial_size > 0:
                self._qbit_initial_size_bytes = initial_size
        final_size = _safe_int(telemetry.get("final_size_bytes", 0))
        diff_pct = _safe_float(telemetry.get("size_diff_pct", 0.0))
        total_minutes = _safe_float(telemetry.get("conversion_total_minutes", 0.0))

        if diff_pct == 0.0 and initial_size > 0 and final_size > 0:
            diff_pct = round(((initial_size - final_size) / float(initial_size)) * 100.0, 2)

        self.lbl_initial_size.setText(f"Initial size: {_format_size_bytes(initial_size) if initial_size > 0 else '-'}")
        if initial_size > 0 and final_size > 0:
            self.lbl_final_size.setText(f"Final size: {_format_size_bytes(final_size)} (-{abs(diff_pct):.2f}%)")
        else:
            self.lbl_final_size.setText(f"Final size: {_format_size_bytes(final_size) if final_size > 0 else '-'}")

        self.lbl_total_minutes.setText(f"Total conversion time: {total_minutes:.2f} min" if total_minutes > 0 else "Total conversion time: -")

        self._gen_log_local_path = str(telemetry.get("gen_log_local_path", "") or "")
        self._ff_log_local_path = str(telemetry.get("ff_log_local_path", "") or "")

        if total_minutes <= 0.0:
            total_minutes = _minutes_from_general_log_text(str(telemetry.get("gen_log", "") or ""))
        if total_minutes <= 0.0 and self._gen_log_local_path:
            total_minutes = _minutes_from_general_log(self._gen_log_local_path)

        is_completed = str(db_status).upper() == "COMPLETED"
        self.btn_general_log.setEnabled(is_completed and bool(self._gen_log_local_path) and os.path.exists(self._gen_log_local_path))
        self.btn_ffmpeg_log.setEnabled(is_completed and bool(self._ff_log_local_path) and os.path.exists(self._ff_log_local_path))
        self.lbl_total_minutes.setText(f"Total conversion time: {total_minutes:.2f} min" if total_minutes > 0 else "Total conversion time: -")

    def _summary_height(self) -> int:
        summary_item = self.foldout_layout.itemAt(0)
        if not summary_item:
            return 90
        summary_widget = summary_item.widget()
        if not summary_widget:
            return 90
        return max(90, summary_widget.sizeHint().height())

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
            self._foldout_anim.setDuration(420)
            self._foldout_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self._foldout_anim.stop()
        try: self._foldout_anim.finished.disconnect()
        except TypeError: pass

        scroll_area = self.window().findChild(QScrollArea)
        if scroll_area: scroll_area.setUpdatesEnabled(False)
        
        def restore_updates():
            if scroll_area: scroll_area.setUpdatesEnabled(True)

        if is_opening:
            self.foldout_container.setVisible(True)
            self.flowchart_view.show_foldout_loading()
            summary_h = self._summary_height()
            if getattr(self.flowchart_view, '_is_revealed', False):
                target_h = int(getattr(self.flowchart_view, '_forced_h', 500)) + summary_h + 20
            else:
                target_h = summary_h + 190
            self._foldout_anim.setStartValue(0)
            self._foldout_anim.setEndValue(target_h)
            def on_open_finished(): 
                self.foldout_container.setMaximumHeight(16777215)
                self.flowchart_view.reveal_after_foldout_expand()
                restore_updates()
            self._foldout_anim.finished.connect(on_open_finished)
            self._foldout_anim.start()
        else:
            def on_close_finished(): 
                self.foldout_container.setVisible(False)
                restore_updates()
            self._foldout_anim.finished.connect(on_close_finished)
            self._foldout_anim.setStartValue(self.foldout_container.height())
            self._foldout_anim.setEndValue(0)
            self._foldout_anim.start()

    def _sync_foldout_height(self, chart_height: int):
        if self.foldout_container.maximumHeight() == 0:
            return
        summary_h = self._summary_height()
        target_h = max(summary_h + 190, int(chart_height) + summary_h + 20)
        anim = QPropertyAnimation(self.foldout_container, b"maximumHeight", self)
        anim.setDuration(280)
        anim.setStartValue(self.foldout_container.height())
        anim.setEndValue(target_h)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._foldout_resize_anim = anim
        anim.start()

    def collapse_foldout(self) -> None:
        if hasattr(self, '_foldout_anim'):
            self._foldout_anim.stop()
        self.foldout_container.setMaximumHeight(0)
        self.foldout_container.setVisible(False)

    def _prompt_delete(self) -> None:
        host = self.window()
        media_grid = getattr(host, 'media_grid', None)
        if media_grid and hasattr(media_grid, 'collapse_all_foldouts'):
            media_grid.collapse_all_foldouts()
        blur_target = getattr(host, 'central_w', host)
        apply_blur_effect(blur_target, radius=90)
        try:
            dialog = DeleteTorrentDialog(self.title, host)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.delete_confirmed.emit([self._current_hash] if self._current_hash else [], dialog.should_delete_files(), self)
        finally:
            remove_blur_effect(blur_target)

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

    def update_torrent_ui(self, human_state, pill_class, pb_style, prog_val, size_str, speed_str, active_state_str, hash_val: str = "", raw_size_bytes: int = 0):
        if hash_val:
            self._current_hash = hash_val
        if _safe_int(raw_size_bytes) > 0:
            self._qbit_initial_size_bytes = _safe_int(raw_size_bytes)

        self.lbl_state_val.setText(human_state)
        self.lbl_state_val.setProperty("class", pill_class)
        self.lbl_state_val.style().unpolish(self.lbl_state_val)
        self.lbl_state_val.style().polish(self.lbl_state_val)
            
        if self._qbit_initial_size_bytes > 0:
            self.lbl_size_val.setText(_format_size_bytes(self._qbit_initial_size_bytes))
        else:
            self.lbl_size_val.setText(_format_size_text_two_decimals(size_str))
        self.prog_bar_dl.set_data(human_state, int(prog_val * 100))
        self.lbl_speed_display.setText("-" if prog_val >= 1.0 or "0.0 MB" in speed_str else speed_str)

    def update_telemetry_ui(self, episodes_data: list):
        if not episodes_data: return
        # Telemetry may include multiple jobs; choose the best path match for this card.
        rel_norm = (self.relative_path or "").replace('\\', '/').lower()
        rel_leaf = os.path.basename(rel_norm)
        title_tokens = [w for w in re.split(r'\W+', (self.title or '').lower()) if len(w) > 2]

        def _score(entry: dict) -> int:
            path = (entry.get("path", "") or "").replace('\\', '/').lower()
            score = 0
            if rel_norm and rel_norm in path:
                score += 100
            if rel_leaf and rel_leaf in path:
                score += 60
            score += sum(3 for t in title_tokens if t in path)
            if entry.get("db_status", "").upper() == "COMPLETED":
                score -= 2
            return score

        first_ep = max(episodes_data, key=_score)
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
        self.prog_pill_conv.update()
        self.prog_pill_conv.repaint()
        self._update_foldout_summary(first_ep, db_status)
        
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

        if not stage_flags and db_status in ["NOT STARTED", "PENDING", "QUEUED", "WAITING"]:
            stage_flags = {"p1-input": True, "p1-queue": True}

        self.flowchart_view.update_pipeline_state(stage_flags)


# -------------------------------------------------------------
# TV Series Episode Child Row (No Torrent Details, Expandable)
# -------------------------------------------------------------
class EpisodeRowWidget(QFrame):
    delete_episode = pyqtSignal(str) 

    def __init__(self, ep_name: str, ep_desc: str = "No description available.", path: str = "", ep_num: int = None, rating: str = "-", parent=None):
        super().__init__(parent)
        self.ep_name = ep_name
        self.ep_num = ep_num
        self.ep_path = path
        self.ep_rating = rating
        self._image_thread = None
        self._qbit_initial_size_bytes = 0
        self._last_summary_telemetry = {}
        self._last_summary_db_status = "NOT STARTED"
        
        # State tracking for mathematically accurate parent aggregation
        self.current_progress = 0
        self.current_state_text = "Not Started"
        
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

        cp_container, cp_v = create_status_column("Conversion Progress", 90)
        from src.ui.components.progress_pill import ProgressPillWidget
        self.prog_pill_conv = ProgressPillWidget()
        self.prog_pill_conv.setFixedSize(90, 24)
        cp_v.addWidget(self.prog_pill_conv)
        status_layout.addWidget(cp_container)

        layout.addLayout(status_layout)

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

        self._gen_log_local_path = ""
        self._ff_log_local_path = ""
        self._build_foldout_summary_panel()
        
        self.flowchart_view = ConversionFlowViewer()
        self.flowchart_view.height_calculated.connect(self._sync_foldout_height)
        self.foldout_layout.addWidget(self.flowchart_view)
        self.main_layout.addWidget(self.foldout_container)

        self.top_row_container.installEventFilter(self)

    def _build_foldout_summary_panel(self) -> None:
        panel = QWidget()
        panel.setObjectName("FoldoutStatsPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 10, 8, 8)
        panel_layout.setSpacing(4)

        row_metrics = QHBoxLayout()
        row_metrics.setSpacing(18)

        self.lbl_initial_size = QLabel("Initial size: -")
        self.lbl_final_size = QLabel("Final size: -")
        self.lbl_total_minutes = QLabel("Total conversion time: -")
        for lbl in (self.lbl_initial_size, self.lbl_final_size, self.lbl_total_minutes):
            lbl.setObjectName("SubText")
            row_metrics.addWidget(lbl)

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        log_icon_path = os.path.join(base_dir, "assets", "icons8-log.svg")
        self.btn_general_log = QPushButton("General log")
        self.btn_ffmpeg_log = QPushButton("FFmpeg log")
        for btn in (self.btn_general_log, self.btn_ffmpeg_log):
            btn.setObjectName("ActionIconButton")
            btn.setMinimumHeight(36)
            btn.setMinimumWidth(112)
            btn.setIcon(QIcon(log_icon_path))
            btn.setIconSize(QSize(18, 18))
            btn.setEnabled(False)
        self.btn_general_log.clicked.connect(lambda: self._open_log_file(self._gen_log_local_path))
        self.btn_ffmpeg_log.clicked.connect(lambda: self._open_log_file(self._ff_log_local_path))

        row_metrics.addStretch(1)
        row_metrics.addWidget(self.btn_general_log)
        row_metrics.addWidget(self.btn_ffmpeg_log)
        panel_layout.addLayout(row_metrics)

        self.foldout_layout.addWidget(panel)

    def _open_log_file(self, file_path: str) -> None:
        if not file_path or not os.path.exists(file_path):
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

    def _update_foldout_summary(self, telemetry: dict, db_status: str) -> None:
        self._last_summary_telemetry = telemetry or {}
        self._last_summary_db_status = str(db_status or "NOT STARTED")
        qbit_initial_size = _safe_int(self._qbit_initial_size_bytes)
        # Source of truth: qBittorrent file size for episodes.
        initial_size = qbit_initial_size
        final_size = _safe_int(telemetry.get("final_size_bytes", 0))
        diff_pct = _safe_float(telemetry.get("size_diff_pct", 0.0))
        total_minutes = _safe_float(telemetry.get("conversion_total_minutes", 0.0))

        if diff_pct == 0.0 and initial_size > 0 and final_size > 0:
            diff_pct = round(((initial_size - final_size) / float(initial_size)) * 100.0, 2)

        self.lbl_initial_size.setText(f"Initial size: {_format_size_bytes(initial_size) if initial_size > 0 else '-'}")
        if initial_size > 0 and final_size > 0:
            self.lbl_final_size.setText(f"Final size: {_format_size_bytes(final_size)} (-{abs(diff_pct):.2f}%)")
        else:
            self.lbl_final_size.setText(f"Final size: {_format_size_bytes(final_size) if final_size > 0 else '-'}")

        self.lbl_total_minutes.setText(f"Total conversion time: {total_minutes:.2f} min" if total_minutes > 0 else "Total conversion time: -")

        self._gen_log_local_path = str(telemetry.get("gen_log_local_path", "") or "")
        self._ff_log_local_path = str(telemetry.get("ff_log_local_path", "") or "")

        if total_minutes <= 0.0:
            total_minutes = _minutes_from_general_log_text(str(telemetry.get("gen_log", "") or ""))
        if total_minutes <= 0.0 and self._gen_log_local_path:
            total_minutes = _minutes_from_general_log(self._gen_log_local_path)

        is_completed = str(db_status).upper() == "COMPLETED"
        self.btn_general_log.setEnabled(is_completed and bool(self._gen_log_local_path) and os.path.exists(self._gen_log_local_path))
        self.btn_ffmpeg_log.setEnabled(is_completed and bool(self._ff_log_local_path) and os.path.exists(self._ff_log_local_path))
        self.lbl_total_minutes.setText(f"Total conversion time: {total_minutes:.2f} min" if total_minutes > 0 else "Total conversion time: -")

    def _summary_height(self) -> int:
        summary_item = self.foldout_layout.itemAt(0)
        if not summary_item:
            return 90
        summary_widget = summary_item.widget()
        if not summary_widget:
            return 90
        return max(90, summary_widget.sizeHint().height())

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
            self._foldout_anim.setDuration(420)
            self._foldout_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self._foldout_anim.stop()
        try: self._foldout_anim.finished.disconnect()
        except TypeError: pass

        scroll_area = self.window().findChild(QScrollArea)
        if scroll_area: scroll_area.setUpdatesEnabled(False)
        
        def restore_updates():
            if scroll_area: scroll_area.setUpdatesEnabled(True)

        if is_opening:
            self.foldout_container.setVisible(True)
            self.flowchart_view.show_foldout_loading()
            summary_h = self._summary_height()
            if getattr(self.flowchart_view, '_is_revealed', False):
                target_h = int(getattr(self.flowchart_view, '_forced_h', 500)) + summary_h + 20
            else:
                target_h = summary_h + 190
            self._foldout_anim.setStartValue(0)
            self._foldout_anim.setEndValue(target_h)
            def on_open_finished(): 
                self.foldout_container.setMaximumHeight(16777215)
                self.flowchart_view.reveal_after_foldout_expand()
                restore_updates()
            self._foldout_anim.finished.connect(on_open_finished)
            self._foldout_anim.start()
        else:
            def on_close_finished(): 
                self.foldout_container.setVisible(False)
                restore_updates()
            self._foldout_anim.finished.connect(on_close_finished)
            self._foldout_anim.setStartValue(self.foldout_container.height())
            self._foldout_anim.setEndValue(0)
            self._foldout_anim.start()

    def _sync_foldout_height(self, chart_height: int):
        if self.foldout_container.maximumHeight() == 0:
            return
        summary_h = self._summary_height()
        target_h = max(summary_h + 190, int(chart_height) + summary_h + 20)
        anim = QPropertyAnimation(self.foldout_container, b"maximumHeight", self)
        anim.setDuration(280)
        anim.setStartValue(self.foldout_container.height())
        anim.setEndValue(target_h)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._foldout_resize_anim = anim
        anim.start()

    def collapse_foldout(self) -> None:
        if hasattr(self, '_foldout_anim'):
            self._foldout_anim.stop()
        self.foldout_container.setMaximumHeight(0)
        self.foldout_container.setVisible(False)

    def _prompt_delete(self) -> None:
        host = self.window()
        media_grid = getattr(host, 'media_grid', None)
        if media_grid and hasattr(media_grid, 'collapse_all_foldouts'):
            media_grid.collapse_all_foldouts()
        blur_target = getattr(host, 'central_w', host)
        apply_blur_effect(blur_target, radius=90)
        try:
            dialog = DeleteTorrentDialog(self.ep_name, host)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.delete_episode.emit(self.ep_path)
        finally:
            remove_blur_effect(blur_target)

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

    def set_qbit_initial_size_hint(self, size_bytes: int) -> None:
        new_size = max(0, _safe_int(size_bytes))
        if new_size <= 0:
            return
        if new_size == self._qbit_initial_size_bytes:
            return

        self._qbit_initial_size_bytes = new_size

        # Recompute summary immediately so UI reflects refreshed qB size data.
        self._update_foldout_summary(self._last_summary_telemetry, self._last_summary_db_status)

    def _fetch_episode_image(self, url: str):
        self._image_thread = ImageDownloaderThread(url, self)
        self._image_thread.finished.connect(self._on_image_downloaded)
        self._image_thread.start()

    def _on_image_downloaded(self, image_bytes: bytes) -> None:
        if image_bytes:
            pixmap = QPixmap()
            if pixmap.loadFromData(image_bytes):
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

    def update_status(self, ep_data: dict = None):
        from src.ui.components.progress_pill import calculate_conversion_progress
        
        if not ep_data:
            self.current_progress = 0
            self.current_state_text = "Not Started"
            self.lbl_conv_status.setText("Not Started")
            self.lbl_conv_status.setProperty("class", "PillUnknown")
            self.lbl_conv_status.style().unpolish(self.lbl_conv_status)
            self.lbl_conv_status.style().polish(self.lbl_conv_status)
            self.prog_pill_conv.set_data("Not Started", 0)
            self._update_foldout_summary({}, "NOT STARTED")
            self.flowchart_view.update_pipeline_state({"p1-input": True, "p1-queue": True})
            return

        state_text, percentage = calculate_conversion_progress(ep_data)
        db_status = (ep_data.get("db_status") or ep_data.get("status") or "NOT STARTED").upper()
        
        # STRICT OVERRIDE: Eliminate backend hallucination for queued items
        if db_status == "COMPLETED":
            percentage = 100
            state_text = "Completed"
        elif db_status in ["NOT STARTED", "PENDING", "QUEUED", "WAITING"]:
            percentage = 0
            state_text = db_status.capitalize() if db_status != "NOT STARTED" else "Not Started"
            
        self.current_progress = percentage
        self.current_state_text = state_text
            
        pill_css = "PillUnknown"
        if state_text == "Completed": pill_css = "PillSuccess"
        elif "Failed" in state_text: pill_css = "PillDanger"
        elif percentage > 0 or db_status not in ["COMPLETED", "NOT STARTED", "FAILED", "REJECTED", "PENDING", "QUEUED", "WAITING"]: 
            pill_css = "PillActive"

        self.lbl_conv_status.setText(state_text)
        self.lbl_conv_status.setProperty("class", pill_css)
        self.lbl_conv_status.style().unpolish(self.lbl_conv_status)
        self.lbl_conv_status.style().polish(self.lbl_conv_status)
        self.lbl_conv_status.update()
        
        self.prog_pill_conv.set_data(state_text, percentage)
        self.prog_pill_conv.update()
        self.prog_pill_conv.repaint()
        self._update_foldout_summary(ep_data, db_status)

        stage_flags_raw = ep_data.get("stage_results", {})
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
                stage_flags["p3-tv"] = True
                stage_flags["p4-tv"] = True
                stage_flags["p5-check"] = True; stage_flags["p5-pass"] = True
                stage_flags["p8-relocate"] = True
                stage_flags["p8-tv"] = True
                stage_flags["p8-cleanup"] = True

        # STRICT ISOLATION: Wipe visual pipeline for pending episodes
        if not stage_flags and db_status in ["NOT STARTED", "PENDING", "QUEUED", "WAITING"]:
            stage_flags = {"p1-input": True, "p1-queue": True}

        self.flowchart_view.update_pipeline_state(stage_flags)


# -------------------------------------------------------------
# TV Series Parent Card (With full Torrent Details + Aggregate logic)
# -------------------------------------------------------------
class SeriesCardWidget(QWidget): 
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
        self._cached_files = []
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
        from src.ui.components.progress_pill import ProgressPillWidget
        self.prog_bar_dl = ProgressPillWidget()
        self.prog_bar_dl.set_data("Not Started", 0)
        self.prog_bar_dl.setFixedSize(90, 24)
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

        cp_container, cp_v = create_status_column("Season Progress", 90)
        from src.ui.components.progress_pill import ProgressPillWidget
        self.prog_pill_conv = ProgressPillWidget()
        self.prog_pill_conv.setFixedSize(90, 24)
        cp_v.addWidget(self.prog_pill_conv)
        status_layout.addWidget(cp_container)
        
        top_layout.addLayout(status_layout)

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
            self._ep_anim.setDuration(460)
            self._ep_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        self._ep_anim.stop()
        try: self._ep_anim.finished.disconnect()
        except TypeError: pass
        
        scroll_area = self.window().findChild(QScrollArea)
        if scroll_area: scroll_area.setUpdatesEnabled(False)
        
        def restore_updates():
            if scroll_area: scroll_area.setUpdatesEnabled(True)
        
        if self._expanded:
            self.episodes_container.setVisible(True)
            self.btn_expand.setIcon(QIcon(os.path.join(base_dir, "assets", "chevron_up.svg")))
            target_h = self.episodes_layout.sizeHint().height() + 20
            self._ep_anim.setStartValue(0)
            self._ep_anim.setEndValue(target_h)
            def on_ep_open(): 
                self.episodes_container.setMaximumHeight(16777215)
                restore_updates()
            self._ep_anim.finished.connect(on_ep_open)
            self._ep_anim.start()
        else:
            self.btn_expand.setIcon(QIcon(os.path.join(base_dir, "assets", "chevron_down.svg")))
            def on_ep_close(): 
                self.episodes_container.setVisible(False)
                restore_updates()
            self._ep_anim.finished.connect(on_ep_close)
            self._ep_anim.setStartValue(self.episodes_container.height())
            self._ep_anim.setEndValue(0)
            self._ep_anim.start()

    def collapse_episodes(self) -> None:
        self._expanded = False
        if hasattr(self, '_ep_anim'):
            self._ep_anim.stop()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        self.btn_expand.setIcon(QIcon(os.path.join(base_dir, "assets", "chevron_down.svg")))
        self.episodes_container.setMaximumHeight(0)
        self.episodes_container.setVisible(False)

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

    def update_torrent_ui(self, human_state, pill_class, pb_style, prog_val, size_str, speed_str, active_state_str, hash_val: str = "", raw_size_bytes: int = 0):
        if hash_val:
            self._current_hash = hash_val
        self.lbl_state_val.setText(human_state)
        self.lbl_state_val.setProperty("class", pill_class)
        self.lbl_state_val.style().unpolish(self.lbl_state_val)
        self.lbl_state_val.style().polish(self.lbl_state_val)
            
        self.lbl_size_val.setText(size_str)
        self.lbl_speed_display.setText(speed_str)
        self.prog_bar_dl.set_data(human_state, int(prog_val * 100))

    def _ensure_episode_row(self, rel_path: str, tmdb_episodes: dict = None, qbit_size_bytes: int = 0):
        # 1. Extract ep_num immediately
        match = re.search(r'[sS]?(\d{1,2})[xXeE](\d{1,2})', rel_path)
        if not match: match = re.search(r'[eE](\d{1,2})', rel_path)
        ep_num = int(match.group(2)) if match and len(match.groups()) > 1 else (int(match.group(1)) if match else None)
        
        if ep_num is None:
            return None

        # 2. Prevent Duplicates: Check if we already have this episode row
        row = self.episodes_map.get(rel_path)
        if not row:
            for existing_path, widget in self.episodes_map.items():
                if getattr(widget, 'ep_num', None) == ep_num:
                    row = widget
                    self.episodes_map[rel_path] = row # Map the new path (telemetry) to the existing widget
                    break
                    
        if row:
            if qbit_size_bytes > 0 and hasattr(row, "set_qbit_initial_size_hint"):
                row.set_qbit_initial_size_hint(qbit_size_bytes)
            # We found an existing row, just update its TMDB data if available
            if tmdb_episodes:
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
            
        # 3. If no row exists at all, create a brand new one
        display_title = os.path.basename(rel_path)
        desc = "No description available."
        still_url = ""
        
        ep_rating = "-"
        if tmdb_episodes:
            ep_data = tmdb_episodes.get(ep_num) or tmdb_episodes.get(str(ep_num))
            if ep_data:
                display_title = ep_data.get('name', display_title)
                desc = ep_data.get('overview', desc)
                still_url = ep_data.get('still_url', "")
                ep_rating = ep_data.get('vote_average', '-')
                if ep_rating and ep_rating != '-':
                    ep_rating = str(round(float(ep_rating), 1))
        
        row = EpisodeRowWidget(display_title, desc, path=rel_path, ep_num=ep_num, rating=ep_rating)
        row.badge.setText(f"EP {ep_num}")
        if qbit_size_bytes > 0:
            row.set_qbit_initial_size_hint(qbit_size_bytes)
            
        if still_url:
            row.update_tmdb_data(display_title, desc, still_url)
            
        self.episodes_map[rel_path] = row
        
        # 4. Insert in sorted order
        insert_idx = self.episodes_layout.count()
        for i in range(self.episodes_layout.count()):
            existing_widget = self.episodes_layout.itemAt(i).widget()
            if isinstance(existing_widget, EpisodeRowWidget):
                existing_ep_num = getattr(existing_widget, 'ep_num', 999) or 999
                if ep_num < existing_ep_num:
                    insert_idx = i
                    break
                    
        self.episodes_layout.insertWidget(insert_idx, row)
        return row

    def populate_episodes_from_files(self, files: list, tmdb_episodes: dict = None):
        self._cached_files = files or []
        video_extensions = ('.mp4', '.mkv', '.avi', '.m4v')
        video_files = [f for f in files if f.get('name', '').lower().endswith(video_extensions)]
        
        for f_info in sorted(video_files, key=lambda x: x.get('name', '')):
            rel_path = f_info.get('name', '')
            if not rel_path: continue
            qbit_size = _safe_int(f_info.get('size', 0))
            self._ensure_episode_row(rel_path, tmdb_episodes, qbit_size_bytes=qbit_size)

    def _extract_episode_number(self, value: str):
        if not value:
            return None
        match = re.search(r'[sS]?(\d{1,2})[xXeE](\d{1,2})', value)
        if not match:
            match = re.search(r'[eE](\d{1,2})', value)
        if not match:
            return None
        return int(match.group(2)) if len(match.groups()) > 1 else int(match.group(1))

    def _resolve_qbit_initial_size(self, telemetry_path: str, row=None) -> int:
        cached_files = getattr(self, '_cached_files', None) or []
        normalized_telemetry_path = str(telemetry_path or '').replace('\\', '/').lower()
        telemetry_basename = os.path.basename(normalized_telemetry_path)

        # Use strict filename/suffix matching to avoid cross-season E07 collisions.
        for f_info in cached_files:
            file_path = str(f_info.get('name', '')).replace('\\', '/').lower()
            if not file_path:
                continue
            if file_path.endswith(normalized_telemetry_path) or os.path.basename(file_path) == telemetry_basename:
                return _safe_int(f_info.get('size', 0))

        # Live qB fallback: derive the file size directly from current torrent hash + basename.
        # This mirrors the verified EP7 source used in manual tracing (2931171105 bytes => 2.93 GB).
        current_hash = str(getattr(self, '_current_hash', '') or '')
        if not current_hash:
            return 0
        try:
            host = os.getenv("QBIT_HOST")
            port = os.getenv("QBIT_PORT")
            user = os.getenv("QBIT_USER")
            pwd = os.getenv("QBIT_PASS")
            if not all([host, port, user, pwd]):
                return 0

            client = qbittorrentapi.Client(
                host=f"http://{host}:{port}",
                username=user,
                password=pwd,
            )
            client.auth_log_in()
            raw_files = client.torrents_files(torrent_hash=current_hash)

            # Refresh local cached files with live data when available.
            refreshed = []
            for f in raw_files:
                refreshed.append({
                    "name": f.get("name", ""),
                    "size": _safe_int(f.get("size", 0), 0),
                })
            if refreshed:
                self._cached_files = refreshed

            for f_info in refreshed:
                file_path = str(f_info.get('name', '')).replace('\\', '/').lower()
                if not file_path:
                    continue
                if file_path.endswith(normalized_telemetry_path) or os.path.basename(file_path) == telemetry_basename:
                    return _safe_int(f_info.get('size', 0))
        except Exception:
            return 0

        return 0

    def update_telemetry_ui(self, episodes_data: list):
        if not episodes_data: return
        
        # 1. Update matching rows with explicit telemetry
        for ep_data in episodes_data:
            path = ep_data.get("path", "")
            if not path: continue
            
            row = self.episodes_map.get(path)
            
            # Strict fallback match using EP Number
            if not row:
                fname = os.path.basename(path)
                match = re.search(r'[sS]?(\d{1,2})[xXeE](\d{1,2})', fname)
                if not match: match = re.search(r'[eE](\d{1,2})', fname)
                ep_num = int(match.group(2)) if match and len(match.groups()) > 1 else (int(match.group(1)) if match else None)
                
                for qbit_path, widget in self.episodes_map.items():
                    # FIX: Prioritize episode number matching over filename matching
                    if ep_num is not None and getattr(widget, 'ep_num', None) == ep_num:
                        row = widget
                        break
                    elif os.path.basename(qbit_path) == fname:
                        row = widget
                        break
                            
            if not row:
                qbit_size = self._resolve_qbit_initial_size(path)
                row = self._ensure_episode_row(path, getattr(self, '_cached_tmdb_eps', None), qbit_size_bytes=qbit_size)
                
            if row:
                qbit_size = self._resolve_qbit_initial_size(path, row=row)
                if qbit_size > 0 and hasattr(row, 'set_qbit_initial_size_hint'):
                    row.set_qbit_initial_size_hint(qbit_size)

                # Keep episode metadata hydrated regardless of event order.
                tmdb_eps = getattr(self, '_cached_tmdb_eps', None)
                if tmdb_eps and hasattr(row, 'ep_num'):
                    ep_meta = tmdb_eps.get(row.ep_num) or tmdb_eps.get(str(row.ep_num))
                    if ep_meta:
                        ep_vote = ep_meta.get('vote_average', '-')
                        ep_rating_str = str(round(float(ep_vote), 1)) if ep_vote and ep_vote != '-' else '-'
                        row.update_tmdb_data(
                            ep_meta.get('name', row.ep_name),
                            ep_meta.get('overview', row.lbl_desc.text()),
                            ep_meta.get('still_url', ''),
                            rating=ep_rating_str
                        )
                row.update_status(ep_data)

        # 2. Derive true season average from the physically stored states of ALL rows
        total_percentage_sum = 0.0
        active_eps = []
        
        for path, row in self.episodes_map.items():
            ep_prog = getattr(row, 'current_progress', 0)
            state_text = getattr(row, 'current_state_text', "Not Started")
            
            total_percentage_sum += ep_prog

            # Active Episode Logic
            is_active = False
            if 0 < ep_prog < 100:
                is_active = True
            elif state_text.upper() not in ["NOT STARTED", "COMPLETED", "FAILED", "REJECTED", "PENDING", "QUEUED", "WAITING"]:
                is_active = True
                
            if is_active:
                ep_num_val = getattr(row, 'ep_num', None)
                ep_badge = f"EP{ep_num_val}" if ep_num_val else "EP?"
                active_eps.append((ep_num_val or 999, state_text, ep_badge))

        # 3. Denominator must be total TMDB episodes, not just currently downloaded files
        tmdb_eps = getattr(self, '_cached_tmdb_eps', None)
        if tmdb_eps and isinstance(tmdb_eps, dict) and len(tmdb_eps) > 0:
            total_eps_count = len(tmdb_eps)
        else:
            total_eps_count = len(self.episodes_map)
            
        total_eps_count = max(1, total_eps_count)
        aggregate_progress = int(total_percentage_sum / total_eps_count)
        
        if aggregate_progress == 100: 
            final_status = "Completed"
        elif active_eps:
            active_eps.sort(key=lambda x: x[0])
            final_status = f"{active_eps[0][2]} - {active_eps[0][1]}"
        elif aggregate_progress > 0: 
            final_status = "Converting..."
        else: 
            final_status = "Not Started"
            
        pill_css = "PillUnknown"
        if final_status == "Completed": pill_css = "PillSuccess"
        elif "Failed" in final_status: pill_css = "PillDanger"
        elif aggregate_progress > 0 or final_status != "Not Started": pill_css = "PillActive"

        self.lbl_conv_status.setText(final_status)
        self.lbl_conv_status.setProperty("class", pill_css)
        self.lbl_conv_status.style().unpolish(self.lbl_conv_status)
        self.lbl_conv_status.style().polish(self.lbl_conv_status)
        self.lbl_conv_status.update()
        
        self.prog_pill_conv.set_data(final_status, aggregate_progress)
        self.prog_pill_conv.update()
        self.prog_pill_conv.repaint()

    def _prompt_delete(self) -> None:
        host = self.window()
        media_grid = getattr(host, 'media_grid', None)
        if media_grid and hasattr(media_grid, 'collapse_all_foldouts'):
            media_grid.collapse_all_foldouts()
        blur_target = getattr(host, 'central_w', host)
        apply_blur_effect(blur_target, radius=90)
        try:
            dialog = DeleteTorrentDialog(self.title, host)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.delete_confirmed.emit([self._current_hash] if self._current_hash else [], dialog.should_delete_files(), self)
        finally:
            remove_blur_effect(blur_target)