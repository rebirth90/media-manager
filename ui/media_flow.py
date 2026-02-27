import os
from typing import List, Any
import qbittorrentapi
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QGridLayout, QVBoxLayout, QProgressBar, QSizePolicy

from workers.image_downloader import ImageDownloaderThread
from workers.torrent_poller import TorrentPollingThread
from workers.tmdb_fetcher import TMDBFetcherThread
from services.qbittorrent import QBittorrentClient
from services.ssh_telemetry import SSHTelemetryClient
from ui.dialogs import FlowDetailsModal

class MediaFlowWidget(QFrame):
    def __init__(self, index: int, relative_path: str, torrent_bytes: bytes, image_url: str, title: str, parent=None):
        super().__init__(parent)
        self.flow_index = index
        self.relative_path = relative_path
        self.torrent_bytes = torrent_bytes
        self.image_url = image_url
        self.title = title if title else "Unknown Media"

        self._active_qbit_state = "Initializing..."
        self._active_ffmpeg_log = "Awaiting conversion pipeline..."
        self._illustration_path = r"C:\Users\Codrut\.gemini\antigravity\brain\8785b3f2-114a-4ae3-86c6-da36af48ada5\isometric_drafting_illustration_1772118592306.png"

        self.setStyleSheet("""
            QFrame { 
                background-color: #eaf2f8; 
                border: 1.5px solid #dce9f2;
                border-radius: 8px;
            }
            QLabel { 
                color: #1e293b; 
                font-family: 'Segoe UI', 'San Francisco', 'Helvetica Neue', Arial; 
                border: none;
                background-color: transparent;
            }
        """)
        self.setFixedHeight(64)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 6, 10, 6)
        self.main_layout.setSpacing(12)

        # Left Section
        self.title_lbl = QLabel(self.title)
        self.title_lbl.setStyleSheet("""
            font-size: 12pt; 
            font-weight: 800;
            color: #0f172a;
            letter-spacing: -0.2px;
        """)
        self.title_lbl.setWordWrap(False)
        self.main_layout.addWidget(self.title_lbl, stretch=6)

        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.VLine)
        div1.setStyleSheet("border: 1px solid #cbd5e1; background-color: #cbd5e1;")
        div1.setFixedWidth(2)
        self.main_layout.addWidget(div1)

        # Middle Section (Flattened)
        self.mid_layout = QHBoxLayout()
        self.mid_layout.setSpacing(8)

        lbl_style_cap = "font-size: 8pt; color: #64748b; font-weight: normal;"
        lbl_style_val = "font-size: 9pt; font-weight: bold; color: #0f172a;"

        self.lbl_state_cap = QLabel("State:")
        self.lbl_state_cap.setStyleSheet(lbl_style_cap)
        self.lbl_state_val = QLabel("Initializing")
        self.lbl_state_val.setStyleSheet(lbl_style_val)
        
        self.lbl_size_cap = QLabel("Size:")
        self.lbl_size_cap.setStyleSheet(lbl_style_cap)
        self.lbl_size_val = QLabel("0 B")
        self.lbl_size_val.setStyleSheet(lbl_style_val)

        self.lbl_prog_cap = QLabel("Progress:")
        self.lbl_prog_cap.setStyleSheet(lbl_style_cap)
        
        self.prog_bar_dl = QProgressBar()
        self.prog_bar_dl.setRange(0, 100)
        self.prog_bar_dl.setValue(0)
        self.prog_bar_dl.setTextVisible(True)
        self.prog_bar_dl.setFormat("%p %")
        self.prog_bar_dl.setFixedWidth(70)
        self.prog_bar_dl.setStyleSheet("""
            QProgressBar {
                background-color: #1e293b;
                border: 1px solid #0f172a;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                font-weight: bold;
                font-size: 7pt;
            }
            QProgressBar::chunk {
                background-color: #4ade80;
                border-radius: 3px;
            }
        """)
        self.prog_bar_dl.setFixedHeight(15)

        self.lbl_speed_cap = QLabel("Speed:")
        self.lbl_speed_cap.setStyleSheet(lbl_style_cap)
        self.lbl_speed_val = QLabel("0 kB/s")
        self.lbl_speed_val.setStyleSheet(lbl_style_val)

        def _add_mid_div():
            d = QFrame()
            d.setFrameShape(QFrame.Shape.VLine)
            d.setStyleSheet("border: 1px dashed #cbd5e1; margin: 0 4px;")
            self.mid_layout.addWidget(d)

        self.mid_layout.addWidget(self.lbl_state_cap)
        self.mid_layout.addWidget(self.lbl_state_val)
        _add_mid_div()
        self.mid_layout.addWidget(self.lbl_size_cap)
        self.mid_layout.addWidget(self.lbl_size_val)
        _add_mid_div()
        self.mid_layout.addWidget(self.lbl_prog_cap)
        self.mid_layout.addWidget(self.prog_bar_dl)
        _add_mid_div()
        self.mid_layout.addWidget(self.lbl_speed_cap)
        self.mid_layout.addWidget(self.lbl_speed_val)
        self.mid_layout.addStretch()

        self.main_layout.addLayout(self.mid_layout, stretch=3)

        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.VLine)
        div2.setStyleSheet("border: 1px solid #cbd5e1; background-color: #cbd5e1;")
        div2.setFixedWidth(2)
        self.main_layout.addWidget(div2)

        # Right Section (Flattened)
        self.conv_layout = QHBoxLayout()
        self.conv_layout.setSpacing(12)
        
        self.lbl_conv_state_val = QLabel("Not Started")
        self.lbl_conv_state_val.setStyleSheet(lbl_style_val)
        
        self.prog_bar_conv = QProgressBar()
        self.prog_bar_conv.setRange(0, 100)
        self.prog_bar_conv.setValue(0)
        self.prog_bar_conv.setTextVisible(True)
        self.prog_bar_conv.setFormat("%p %")
        self.prog_bar_conv.setMaximumWidth(120)
        self.prog_bar_conv.setStyleSheet("""
            QProgressBar {
                background-color: #f1f5f9;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                text-align: center;
                color: #0f172a;
                font-weight: bold;
                font-size: 7pt;
            }
            QProgressBar::chunk {
                background-color: #4ade80;
                border-radius: 3px;
            }
        """)
        self.prog_bar_conv.setFixedHeight(15)
        
        self.conv_layout.addWidget(self.lbl_conv_state_val)
        self.conv_layout.addWidget(self.prog_bar_conv)
        self.conv_layout.addStretch()
        
        self.main_layout.addLayout(self.conv_layout, stretch=2)

        # Overlay click button
        self.overlay_btn = QPushButton(self)
        self.overlay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.overlay_btn.setStyleSheet("background-color: transparent; border: none;")
        self.overlay_btn.clicked.connect(self._open_details_modal)

        self._start_flow()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay_btn.resize(self.size())

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
            self.tmdb_fetcher.start()
            
        if self.image_url:
            self.img_thread = ImageDownloaderThread(self.image_url, self)
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
        
        base_path = os.getenv("BASE_SCRATCH_PATH", "/data/scratch")
        final_save_path = f"{base_path}/{self.relative_path}".replace("\\", "/")
        
        self.qbit_worker = QBittorrentClient(self.torrent_bytes, final_save_path, self)
        self.qbit_worker.start()

    def _on_title_resolved(self, resolved_title: str) -> None:
        self.title_lbl.setText(resolved_title)
        self.title = resolved_title

    def _update_torrent_ui(self, data_payload: List[Any]) -> None:
        target_torrents, _ = data_payload
        if target_torrents:
            t = target_torrents[0]
            prog_val = t.get('progress', 0.0)
            state = t.get('state', 'Unknown')
            dlspeed = t.get('dlspeed', 0)
            size = t.get('size', 0)
            
            self._active_qbit_state = f"State: {state} | Progress: {int(prog_val * 100)}% | Size: {self._format_size(size)}"

            self.lbl_state_val.setText(state.capitalize())
            self.lbl_size_val.setText(self._format_size(size))
            self.prog_bar_dl.setValue(int(prog_val * 100))
            self.lbl_speed_val.setText(self._format_speed(dlspeed))

            if prog_val == 1.0 or state in ['uploading', 'stalledUP', 'pausedUP', 'completed']:
                 if not hasattr(self, 'ssh_timer'):
                     self.lbl_state_val.setText("Completed")
                     self.lbl_speed_val.setText("0 kB/s")
                     
                     self.ssh_timer = QTimer(self)
                     self.ssh_timer.timeout.connect(self._pull_ssh)
                     self.ssh_timer.setInterval(3000)
                     self.ssh_timer.start()

    def _pull_ssh(self) -> None:
        if hasattr(self, 'ssh_worker') and self.ssh_worker.isRunning(): 
             return
             
        title_for_ssh = self.title_lbl.text()
        if title_for_ssh.isdigit(): 
             return  # Still waiting for TMDB fetch
        
        self.ssh_worker = SSHTelemetryClient(target_title=title_for_ssh, parent=self)
        self.ssh_worker.telemetry_data.connect(self._update_telemetry_ui)
        self.ssh_worker.start()

    def _update_telemetry_ui(self, db_status: str, gen_out: str, ff_out: str, prog: int) -> None:
        self._active_qbit_state = f"DB Status: {db_status}"
        self._active_ffmpeg_log = ff_out
        
        self.lbl_conv_state_val.setText(db_status)
        self.prog_bar_conv.setValue(prog)
        
        if prog >= 100 or db_status.upper() == "COMPLETED":
            self.prog_bar_conv.setValue(100)
            self.prog_bar_conv.setStyleSheet("""
                QProgressBar {
                    background-color: #f1f5f9;
                    border: 1px solid #cbd5e1;
                    border-radius: 4px;
                    text-align: center;
                    color: white;
                    font-weight: bold;
                    font-size: 8pt;
                }
                QProgressBar::chunk {
                    background-color: #10b981;
                    border-radius: 3px;
                }
            """)
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

    def close_flow(self) -> None:
        if hasattr(self, 'poll_worker'): self.poll_worker.stop()
        if hasattr(self, 'ssh_timer'): self.ssh_timer.stop()
        if hasattr(self, 'ssh_worker') and self.ssh_worker.isRunning(): self.ssh_worker.wait()
