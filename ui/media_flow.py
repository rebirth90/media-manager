import os
from typing import List, Any
import qbittorrentapi
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QGridLayout, QVBoxLayout, QProgressBar, QSizePolicy, QWidget

from workers.image_downloader import ImageDownloaderThread
from workers.torrent_poller import TorrentPollingThread
from workers.tmdb_fetcher import TMDBFetcherThread
from services.qbittorrent import QBittorrentClient
from services.ssh_telemetry import SSHTelemetryClient
from ui.dialogs import FlowDetailsModal
from PyQt6.QtCore import pyqtSignal, QThread

class QueueAppenderThread(QThread):
    finished_appending = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, target_path: str, parent=None):
        super().__init__(parent)
        self.target_path = target_path

    def run(self):
        try:
            with open(r"\\192.168.20.102\Media\conversion.txt", "a", encoding="utf-8") as f:
                f.write(self.target_path + "\n")
            self.finished_appending.emit()
        except Exception as e:
            self.error.emit(str(e))

class MediaFlowWidget(QFrame):
    def __init__(self, index: int, relative_path: str, torrent_bytes: bytes, image_url: str, title: str, season: str = "", parent=None, db_id: int = None, is_restored: bool = False):
        super().__init__(parent)
        self.flow_index = index
        self.relative_path = relative_path
        self.torrent_bytes = torrent_bytes
        self.image_url = image_url
        self.db_id = db_id
        self.is_restored = is_restored
        base_title = title if title else "Unknown Media"
        if season:
            self.title = f"{base_title} - {season}"
        else:
            self.title = base_title
        self._current_hash = ""

        self._active_qbit_state = "Initializing..."
        self._active_ffmpeg_log = "Awaiting conversion pipeline..."
        self._illustration_path = r"C:\Users\Codrut\.gemini\antigravity\brain\8785b3f2-114a-4ae3-86c6-da36af48ada5\isometric_drafting_illustration_1772118592306.png"

        self.setObjectName("MediaCardWrapper")
        self.setStyleSheet("""
            #MediaCardWrapper { 
                background-color: #1A1D24; 
                border: 1px solid rgba(255, 255, 255, 0.05); 
                border-radius: 12px;
            } 
            QLabel { font-family: 'Segoe UI', 'San Francisco', 'Helvetica Neue', Arial, sans-serif; }
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- The top_row_container (Always structured exactly like Figma) ---
        self.top_row_container = QWidget()
        self.top_row_container.setObjectName("TopRow")
        self.top_row_container.setStyleSheet("#TopRow { background: transparent; border: none; }")
        
        self.top_row_container.setFixedHeight(120)
        self.top_row_container.installEventFilter(self)
        self.top_row_container.setCursor(Qt.CursorShape.PointingHandCursor)

        self.top_row_layout = QHBoxLayout(self.top_row_container)
        self.top_row_layout.setContentsMargins(16, 16, 16, 16)
        self.top_row_layout.setSpacing(20)

        # 1. Left: Poster
        self.lbl_poster = QLabel()
        self.lbl_poster.setFixedSize(60, 85)
        self.lbl_poster.setStyleSheet("background-color: #0A0B0E; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.05);")
        self.lbl_poster.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.top_row_layout.addWidget(self.lbl_poster)

        # 2. Middle: Metadata (Flex space)
        info_container = QWidget()
        info_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.title_lbl = QLabel(self.title)
        self.title_lbl.setStyleSheet("font-size: 13pt; font-weight: bold; color: #F8FAFC;")
        self.title_lbl.setWordWrap(False)
        
        self.lbl_foldout_genre_rating = QLabel("Genre: N/A | Rating: N/A")
        self.lbl_foldout_genre_rating.setStyleSheet("font-size: 9pt; color: #9ca3af;")
        
        self.lbl_foldout_desc = QLabel("No description available.")
        self.lbl_foldout_desc.setStyleSheet("font-size: 9pt; color: #94A3B8;")
        self.lbl_foldout_desc.setWordWrap(True)
        # Prevent desc stretching the height
        self.lbl_foldout_desc.setMaximumHeight(35)
        
        info_layout.addWidget(self.title_lbl)
        info_layout.addWidget(self.lbl_foldout_genre_rating)
        info_layout.addWidget(self.lbl_foldout_desc)
        
        self.top_row_layout.addWidget(info_container)

        # 3. Right: Status Columns (Pills)
        status_layout = QHBoxLayout()
        status_layout.setSpacing(24)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        
        def create_col(title_str, w, min_width):
            container = QWidget()
            container.setFixedWidth(min_width)
            v = QVBoxLayout(container)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(8)
            v.setAlignment(Qt.AlignmentFlag.AlignCenter) # Center everything inside column
            
            cap = QLabel(title_str)
            cap.setStyleSheet("color: #6b7280; font-size: 8pt; font-weight: 500;")
            cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.addWidget(cap)
            return container, v
            
        ts_container, ts_v = create_col("Torrent Status", self, 110)
        self.lbl_state_val = QLabel("Initializing")
        self.lbl_state_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_state_val.setStyleSheet("background-color: rgba(107,114,128,0.1); color: #9ca3af; border: 1px solid rgba(107,114,128,0.3); border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;")
        ts_v.addWidget(self.lbl_state_val)
        status_layout.addWidget(ts_container)

        sz_container, sz_v = create_col("Size", self, 80)
        self.lbl_size_val = QLabel("0 B")
        self.lbl_size_val.setStyleSheet("color: #ffffff; font-weight: 500; font-size: 10pt;")
        self.lbl_size_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sz_v.addWidget(self.lbl_size_val)
        status_layout.addWidget(sz_container)

        pr_container, pr_v = create_col("Progress", self, 80)
        self.prog_bar_dl = QProgressBar()
        self.prog_bar_dl.setRange(0, 100)
        self.prog_bar_dl.setValue(0)
        self.prog_bar_dl.setFormat("%p%")
        self.prog_bar_dl.setFixedSize(70, 24)
        self.prog_bar_dl.setStyleSheet("QProgressBar { background-color: rgba(34,197,94,0.1); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); border-radius: 6px; text-align: center; font-weight: 600; font-size: 11px; } QProgressBar::chunk { background-color: transparent; }")
        pr_v.addWidget(self.prog_bar_dl)
        status_layout.addWidget(pr_container)
        
        cs_container, cs_v = create_col("Conversion", self, 110)
        self.lbl_conv_state_val = QLabel("NOT STARTED")
        self.lbl_conv_state_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_conv_state_val.setStyleSheet("background-color: rgba(107,114,128,0.1); color: #9ca3af; border: 1px solid rgba(107,114,128,0.3); border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;")
        self.prog_bar_conv = QProgressBar()
        self.prog_bar_conv.setRange(0, 100)
        self.prog_bar_conv.setFixedSize(80, 15)
        self.prog_bar_conv.hide()
        cs_v.addWidget(self.lbl_conv_state_val)
        cs_v.addWidget(self.prog_bar_conv)
        status_layout.addWidget(cs_container)

        self.top_row_layout.addLayout(status_layout)
        
        # 4. Far Right: Actions
        self.action_buttons_container = QWidget()
        self.action_buttons_container.setFixedWidth(100)
        
        actions_layout = QHBoxLayout(self.action_buttons_container)
        actions_layout.setSpacing(12)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        import os
        from PyQt6.QtGui import QIcon, QPixmap
        from PyQt6.QtCore import QSize
        
        self.btn_trash_row = QPushButton()
        trash_icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "trash_icon.svg")
        self.btn_trash_row.setIcon(QIcon(trash_icon_path))
        self.btn_trash_row.setIconSize(QSize(18, 18))
        self.btn_trash_row.setFixedSize(36, 36)
        self.btn_trash_row.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_trash_row.setStyleSheet("QPushButton { background-color: transparent; border: none; border-radius: 8px; } QPushButton:hover { background-color: rgba(239, 68, 68, 0.1); }")
        self.btn_trash_row.clicked.connect(self._prompt_delete)
        
        self.btn_expand = QPushButton()
        chev_down_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "chevron_down.svg")
        self.btn_expand.setIcon(QIcon(chev_down_path))
        self.btn_expand.setIconSize(QSize(22, 22))
        self.btn_expand.setFixedSize(36, 36)
        self.btn_expand.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_expand.setStyleSheet("QPushButton { background-color: transparent; border: none; border-radius: 8px; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.05); }")
        self.btn_expand.clicked.connect(self._toggle_foldout)

        actions_layout.addWidget(self.btn_trash_row)
        actions_layout.addWidget(self.btn_expand)
        self.top_row_layout.addWidget(self.action_buttons_container)

        self.main_layout.addWidget(self.top_row_container)

        # --- The foldout_container (For HTML ONLY) ---
        self.foldout_container = QWidget()
        self.foldout_container.setObjectName("FoldoutCard")
        # * Set this container to setVisible(False) by default.
        self.foldout_container.setVisible(False)
        self.foldout_container.setStyleSheet("#FoldoutCard { background: transparent; border: none; }")
        self.foldout_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.foldout_layout = QVBoxLayout(self.foldout_container)
        self.foldout_layout.setContentsMargins(16, 0, 16, 16)
        self.foldout_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        from ui.conversion_flowchart import ConversionFlowViewer
        self.flowchart_view = ConversionFlowViewer()
        self.foldout_layout.addWidget(self.flowchart_view)

        # Legacy variables initialized for compatibility with telemetry/polling slots
        self.lbl_speed_val = QLabel("0 kB/s")
        self.lbl_foldout_db_status = QLabel("")
        self.lbl_foldout_sub_status = QLabel("")
        self.btn_send_conv = QPushButton()

        self.main_layout.addWidget(self.foldout_container)
        
        self._start_flow()

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj == self.top_row_container and event.type() == QEvent.Type.MouseButtonRelease:
            # Capture click exactly like the expand chevron
            self._toggle_foldout()
            return True
        return super().eventFilter(obj, event)

    def _toggle_foldout(self, index=0) -> None:
        if self.foldout_container.isVisible():
            self.foldout_container.setVisible(False)
        else:
            self.foldout_container.setVisible(True)

    def _open_details_modal(self) -> None:
        modal = FlowDetailsModal(
            title=self.title_lbl.text(),
            qbit_state=self._active_qbit_state,
            ffmpeg_log=self._active_ffmpeg_log,
            illustration_path=self._illustration_path,
            parent=self.window()
        )
        modal.exec()

    def _start_flow(self) -> None:
        if self.title.startswith("tmdb:"):
            _, media_type, tmdb_id = self.title.split(":", 2)
            self.title_lbl.setText(tmdb_id)
            self.tmdb_fetcher = TMDBFetcherThread(tmdb_id, media_type, self)
            self.tmdb_fetcher.title_resolved.connect(self._on_title_resolved)
            self.tmdb_fetcher.details_resolved.connect(self._on_details_resolved)
            self.tmdb_fetcher.start()
        elif self.image_url:
            self.img_thread = ImageDownloaderThread(self.image_url, self)
            self.img_thread.finished.connect(self._on_image_downloaded)
            self.img_thread.start()

        self.poll_worker = TorrentPollingThread(self)
        self.poll_worker.data_updated.connect(self._update_torrent_ui)
        
        try:
            h = os.getenv("QBIT_HOST", "127.0.0.1")
            p = os.getenv("QBIT_PORT", "8080")
            c = qbittorrentapi.Client(
                host=f"{h}:{p}", 
                username=os.getenv("QBIT_USER", "admin"), 
                password=os.getenv("QBIT_PASS", "adminadmin")
            )
            c.auth_log_in()
            current_hashes = [t.get('hash') for t in c.torrents_info()]
        except Exception:
            current_hashes = []
            
        self.poll_worker.set_pre_add_state(current_hashes)
        self.poll_worker.start()
        
        if not self.is_restored and self.torrent_bytes:
            base_path = os.getenv("BASE_SCRATCH_PATH", "/data/scratch")
            final_save_path = f"{base_path}/{self.relative_path}".replace("\\", "/")
            
            self.qbit_worker = QBittorrentClient(self.torrent_bytes, final_save_path, self)
            self.qbit_worker.start()

    def _on_title_resolved(self, resolved_title: str) -> None:
        self.title_lbl.setText(resolved_title)
        pass
        self.title = resolved_title

    def _on_details_resolved(self, details: dict) -> None:
        desc = details.get("description", "No description available.")
        genre = details.get("genre", "Unknown")
        rating = details.get("rating", "-")
        
        self.lbl_foldout_desc.setText(desc)
        self.lbl_foldout_genre_rating.setText(f"Genre: {genre} | Rating: ★ {rating}")
        
        img_url = details.get("image_url")
        if img_url:
            self.img_thread = ImageDownloaderThread(img_url, self)
            self.img_thread.finished.connect(self._on_image_downloaded)
            self.img_thread.start()
        elif self.image_url:
            self.img_thread = ImageDownloaderThread(self.image_url, self)
            self.img_thread.finished.connect(self._on_image_downloaded)
            self.img_thread.start()

    def _on_image_downloaded(self, data: bytes) -> None:
        if data:
            from PyQt6.QtGui import QPixmap
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                pixmap = pixmap.scaled(self.lbl_poster.width(), self.lbl_poster.height(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                self.lbl_poster.setPixmap(pixmap)
                self.lbl_poster.setText("")
                self.lbl_poster.setStyleSheet("background-color: transparent; border-radius: 8px; border: 1px solid #e2e8f0;")
                self.lbl_poster.show()

    def _update_torrent_ui(self, data_payload: List[Any]) -> None:
        target_torrents, _ = data_payload
        if target_torrents:
            t = target_torrents[0]
            self._current_hash = t.get('hash', "")
            self._torrent_name = t.get('name', 'Unknown')
            prog_val = t.get('progress', 0.0)
            state = t.get('state', 'Unknown')
            dlspeed = t.get('dlspeed', 0)
            size = t.get('size', 0)
            
            is_done = state in ['uploading', 'stalledUP', 'pausedUP', 'completed', 'stalledDL'] and prog_val == 1.0
            
            human_state = "Unknown"
            if is_done or prog_val == 1.0:
                human_state = "Completed"
                state_css = "background-color: rgba(34,197,94,0.1); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;"
                pb_style = "QProgressBar { background-color: rgba(34,197,94,0.1); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); border-radius: 6px; text-align: center; font-weight: 600; font-size: 11px; } QProgressBar::chunk { background-color: transparent; }"
            elif state in ['downloading', 'stalledDL'] and prog_val < 1.0:
                human_state = "Downloading"
                state_css = "background-color: rgba(59,130,246,0.1); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;"
                pb_style = "QProgressBar { background-color: rgba(59,130,246,0.1); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); border-radius: 6px; text-align: center; font-weight: 600; font-size: 11px; } QProgressBar::chunk { background-color: transparent; }"
            elif state in ['pausedDL', 'stopped', 'stoppedDL', 'checkingDL', 'checkingUP']:
                human_state = "Stopped"
                state_css = "background-color: rgba(107,114,128,0.1); color: #9ca3af; border: 1px solid rgba(107,114,128,0.3); border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;"
                pb_style = "QProgressBar { background-color: rgba(107,114,128,0.1); color: #4ade80; border: 1px solid rgba(107,114,128,0.3); border-radius: 6px; text-align: center; font-weight: 600; font-size: 11px; } QProgressBar::chunk { background-color: transparent; }"
            else:
                human_state = state.capitalize()
                state_css = "background-color: rgba(168,85,247,0.1); color: #c084fc; border: 1px solid rgba(168,85,247,0.3); border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;"
                pb_style = "QProgressBar { background-color: rgba(168,85,247,0.1); color: #c084fc; border: 1px solid rgba(168,85,247,0.3); border-radius: 6px; text-align: center; font-weight: 600; font-size: 11px; } QProgressBar::chunk { background-color: transparent; }"

            self._active_qbit_state = f"State: {human_state} | Progress: {int(prog_val * 100)}% | Size: {self._format_size(size)}"

            self.lbl_state_val.setText(human_state)
            self.lbl_state_val.setStyleSheet(state_css)
            self.prog_bar_dl.setStyleSheet(pb_style)
            
            self.lbl_size_val.setText(self._format_size(size))
            self.prog_bar_dl.setValue(int(prog_val * 100))
            self.lbl_speed_val.setText(self._format_speed(dlspeed))

            if prog_val == 1.0 or state in ['uploading', 'stalledUP', 'pausedUP', 'completed']:
                 if not hasattr(self, 'ssh_timer'):
                     self.lbl_state_val.setText("Completed")
                     self.lbl_state_val.setStyleSheet("background-color: rgba(34,197,94,0.1); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;")
                     
                     self.ssh_timer = QTimer(self)
                     self.ssh_timer.timeout.connect(self._pull_ssh)
                     self.ssh_timer.setInterval(3000)
                     self.ssh_timer.start()

    def _pull_ssh(self) -> None:
        if hasattr(self, 'ssh_worker') and self.ssh_worker.isRunning(): 
             return
             
        # Use the raw torrent name (e.g. 'The.Cruel.Sea.1953') for accurate DB/log matching
        # Fallback to title_lbl if the torrent data hasn't populated yet
        title_for_ssh = getattr(self, '_torrent_name', self.title_lbl.text())
        if title_for_ssh.isdigit(): 
             return  # Still waiting for TMDB fetch
        
        self.ssh_worker = SSHTelemetryClient(target_title=title_for_ssh, parent=self)
        self.ssh_worker.telemetry_data.connect(self._update_telemetry_ui)
        self.ssh_worker.start()

    def _send_to_conversion(self):
        target_path = self.relative_path.replace("\\", "/") # Linux consistent path
        self.queue_thread = QueueAppenderThread(target_path, self)
        self.queue_thread.finished_appending.connect(lambda: self.btn_send_conv.setText("Sent ✓"))
        self.queue_thread.finished_appending.connect(lambda: self.btn_send_conv.setEnabled(False))
        self.queue_thread.error.connect(lambda err: self.btn_send_conv.setText("Error!"))
        self.queue_thread.start()
        self.btn_send_conv.setEnabled(False)
        self.btn_send_conv.setText("Sending...")

    def _update_telemetry_ui(self, db_status: str, sub_status: str, prog: int, gen_out: str, ff_out: str, stage_flags_json: str) -> None:
        self._active_qbit_state = f"DB Status: {db_status}"
        self._active_ffmpeg_log = ff_out
        
        if db_status.upper() == "COMPLETED":
            pill_css = "background-color: rgba(34,197,94,0.1); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;"
        elif db_status.upper() == "FAILED":
            pill_css = "background-color: rgba(239, 68, 68, 0.1); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;"
        elif db_status.upper() != "NOT STARTED":
            pill_css = "background-color: rgba(59,130,246,0.1); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;"
        else:
            pill_css = "background-color: rgba(107,114,128,0.1); color: #9ca3af; border: 1px solid rgba(107,114,128,0.3); border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;"

        self.lbl_conv_state_val.setText(db_status)
        self.lbl_conv_state_val.setStyleSheet(pill_css)
        self.lbl_foldout_db_status.setText(f"Conversion Status: {db_status}")
        self.lbl_foldout_sub_status.setText(f"Subtitles: {sub_status}")
        
        if hasattr(self, 'flowchart_view') and stage_flags_json:
            self.flowchart_view.update_pipeline_state(stage_flags_json)

        if prog >= 100 or db_status.upper() == "COMPLETED":
            if hasattr(self, 'ssh_timer'): 
                self.ssh_timer.stop()

    def _format_size(self, bytes_size: int) -> str:
        if bytes_size == 0: return "0 B"
        elif bytes_size < 1024**2: return f"{bytes_size / 1024:.2f} KB"
        elif bytes_size < 1024**3: return f"{bytes_size / (1024**2):.2f} MB"
        else: return f"{bytes_size / (1024**3):.2f} GB"

    def _format_speed(self, bytes_per_sec: int) -> str:
        if bytes_per_sec == 0: return "0 kB/s"
        elif bytes_per_sec < 1024**2: return f"{bytes_per_sec / 1024:.0f} kB/s"
        else: return f"{bytes_per_sec / (1024**2):.1f} MB/s"

    def _format_time(self, seconds: int) -> str:
        if seconds >= 8640000: return "∞" # 100 days representation by qbittorrent
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0: return f"{h}h {m}m"
        elif m > 0: return f"{m}m {s}s"
        else: return f"{s}s"

    def _format_timestamp(self, unix_ts: int) -> str:
        if unix_ts <= 0: return "-"
        from datetime import datetime
        return datetime.fromtimestamp(unix_ts).strftime('%Y-%m-%d %H:%M:%S')

    def close_flow(self) -> None:
        if hasattr(self, 'poll_worker'): self.poll_worker.stop()
        if hasattr(self, 'ssh_timer'): self.ssh_timer.stop()
        if hasattr(self, 'ssh_worker') and self.ssh_worker.isRunning(): self.ssh_worker.wait()
        if hasattr(self, 'del_worker') and self.del_worker.isRunning(): self.del_worker.wait()

    def _prompt_delete(self) -> None:
        from ui.dialogs import DeleteTorrentDialog
        if not self._current_hash:
            return
            
        from PyQt6.QtWidgets import QDialog
        dialog = DeleteTorrentDialog(self.title, self.window())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            delete_files = dialog.should_delete_files()
            from services.qbittorrent import QBittorrentDeleteWorker
            self.del_worker = QBittorrentDeleteWorker([self._current_hash], delete_files, self)
            self.del_worker.finished.connect(self._on_deleted)
            self.del_worker.start()

    def _on_deleted(self, success: bool) -> None:
        if success:
            if hasattr(self, 'db_id') and self.db_id is not None:
                try:
                    from services.local_db import LocalDBManager
                    db = LocalDBManager()
                    db.delete_item(self.db_id)
                except Exception as e:
                    print(f"Failed to delete DB entry: {e}")
                    
            if hasattr(self.window(), 'all_flows'):
                if self in self.window().all_flows:
                    self.window().all_flows.remove(self)
                    
            self.close_flow()
            self.setParent(None)
