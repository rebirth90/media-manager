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

class MediaFlowWidget(QFrame):
    def __init__(self, index: int, relative_path: str, torrent_bytes: bytes, image_url: str, title: str, season: str = "", parent=None):
        super().__init__(parent)
        self.flow_index = index
        self.relative_path = relative_path
        self.torrent_bytes = torrent_bytes
        self.image_url = image_url
        base_title = title if title else "Unknown Media"
        if season:
            self.title = f"{base_title} - {season}"
        else:
            self.title = base_title
        self._current_hash = ""

        self._active_qbit_state = "Initializing..."
        self._active_ffmpeg_log = "Awaiting conversion pipeline..."
        self._illustration_path = r"C:\Users\Codrut\.gemini\antigravity\brain\8785b3f2-114a-4ae3-86c6-da36af48ada5\isometric_drafting_illustration_1772118592306.png"

        self.setStyleSheet("""
            MediaFlowWidget { background-color: transparent; border: none; }
            QLabel { 
                color: #1e293b; 
                font-family: 'Segoe UI', 'San Francisco', 'Helvetica Neue', Arial; 
                border: none;
                background-color: transparent;
            }
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 10) # 10px bottom margin between flows
        self.main_layout.setSpacing(0)

        # Main Card Container
        self.main_card_container = QWidget()
        self.main_card_container.setObjectName("MainCard")
        self.main_card_container.setStyleSheet("""
            #MainCard {
                background-color: #eaf2f8; 
                border: 1.5px solid #dce9f2;
                border-radius: 12px;
            }
        """)
        self.main_card_container.setFixedHeight(64)
        self.main_card_container.setCursor(Qt.CursorShape.PointingHandCursor)
        self.main_card_container.mousePressEvent = self._toggle_foldout

        self.card_layout = QHBoxLayout(self.main_card_container)
        self.card_layout.setContentsMargins(10, 6, 10, 6)
        self.card_layout.setSpacing(12)

        # Left Section
        self.title_lbl = QLabel(self.title)
        self.title_lbl.setStyleSheet("""
            font-size: 12pt; 
            font-weight: 800;
            color: #0f172a;
            letter-spacing: -0.2px;
        """)
        self.title_lbl.setWordWrap(False)
        self.card_layout.addWidget(self.title_lbl, stretch=6)

        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.VLine)
        div1.setStyleSheet("border: 1px solid #cbd5e1; background-color: #cbd5e1;")
        div1.setFixedWidth(2)
        self.card_layout.addWidget(div1)

        # Middle Section
        self.mid_layout = QHBoxLayout()
        self.mid_layout.setContentsMargins(4, 0, 4, 0)
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
        self.mid_layout.addWidget(self.lbl_speed_val)
        self.mid_layout.addStretch()

        self.card_layout.addLayout(self.mid_layout, stretch=3)

        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.VLine)
        div2.setStyleSheet("border: 1px solid #cbd5e1; background-color: #cbd5e1;")
        div2.setFixedWidth(2)
        self.card_layout.addWidget(div2)

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
        self.btn_trash_row = QPushButton("🗑 Delete")
        self.btn_trash_row.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_trash_row.setStyleSheet("""
            QPushButton { background-color: transparent; border: none; color: #ef4444; font-weight: bold;}
            QPushButton:hover { background-color: #fee2e2; border-radius: 4px; }
        """)
        self.btn_trash_row.clicked.connect(self._prompt_delete)
        self.conv_layout.addWidget(self.btn_trash_row)
        self.conv_layout.addStretch()
        
        self.card_layout.addLayout(self.conv_layout, stretch=2)
        self.main_layout.addWidget(self.main_card_container)

        # Foldout Container (Initially hidden)
        self.details_foldout_container = QWidget()
        self.details_foldout_container.setObjectName("FoldoutCard")
        self.details_foldout_container.setVisible(False)
        self.details_foldout_container.setStyleSheet("""
            #FoldoutCard {
                background-color: #ffffff;
                border-left: 1.5px solid #dce9f2;
                border-right: 1.5px solid #dce9f2;
                border-bottom: 1.5px solid #dce9f2;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
                margin-top: -2px;
            }
        """)
        self.details_foldout_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        foldout_v = QVBoxLayout(self.details_foldout_container)
        foldout_v.setContentsMargins(16, 12, 16, 12)
        
        self.foldout_layout = QHBoxLayout()
        self.foldout_layout.setSpacing(15)
        
        self.foldout_labels = {}
        fields = [
            "Size", "Progress", "DL Speed", "UL Speed", "Down (global)", 
            "Up (global)", "ETA", "Peers", "Seeds", "State", 
            "Ratio", "Category", "Tags", "Added On", "Avail"
        ]
        
        for field in fields:
            v_box = QVBoxLayout()
            v_box.setSpacing(2)
            lbl_cap = QLabel(field)
            lbl_cap.setStyleSheet("font-size: 7.5pt; color: #94a3b8; font-weight: 500;")
            lbl_val = QLabel("-")
            lbl_val.setStyleSheet("font-size: 8.5pt; color: #334155; font-weight: bold;")
            
            if field == "Progress" or field == "State":
                lbl_val.setStyleSheet("""
                    font-size: 8pt; color: white; font-weight: bold;
                    background-color: #16a34a; border-radius: 3px; padding: 2px 6px;
                """)
            elif field in ["Category", "Tags"]:
                lbl_val.setStyleSheet("""
                    font-size: 8pt; color: white; font-weight: bold;
                    background-color: #0284c7; border-radius: 3px; padding: 2px 6px;
                """)
                
            self.foldout_labels[field] = lbl_val
            v_box.addWidget(lbl_cap)
            v_box.addWidget(lbl_val)
            self.foldout_layout.addLayout(v_box)
            
        self.foldout_layout.addStretch()
        foldout_v.addLayout(self.foldout_layout)
        self.main_layout.addWidget(self.details_foldout_container)

        self._start_flow()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Handle resize logic if necessary, no overlay_btn here

    def _toggle_foldout(self, event) -> None:
        if self.details_foldout_container.isVisible():
            self.details_foldout_container.setVisible(False)
            self.main_card_container.setStyleSheet("""
                #MainCard {
                    background-color: #eaf2f8; 
                    border: 1.5px solid #dce9f2;
                    border-radius: 12px;
                }
            """)
        else:
            self.details_foldout_container.setVisible(True)
            self.main_card_container.setStyleSheet("""
                #MainCard {
                    background-color: #eaf2f8; 
                    border: 1.5px solid #dce9f2;
                    border-top-left-radius: 12px;
                    border-top-right-radius: 12px;
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 0px;
                    border-bottom: none;
                }
            """)

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

    def _on_details_resolved(self, details: dict) -> None:
        img_url = details.get("image_url")
        if img_url:
            self.img_thread = ImageDownloaderThread(img_url, self)
            self.img_thread.start()

    def _update_torrent_ui(self, data_payload: List[Any]) -> None:
        target_torrents, _ = data_payload
        if target_torrents:
            t = target_torrents[0]
            self._current_hash = t.get('hash', "")
            prog_val = t.get('progress', 0.0)
            state = t.get('state', 'Unknown')
            dlspeed = t.get('dlspeed', 0)
            size = t.get('size', 0)
            
            # Extended stats for foldout
            ulspeed = t.get('upspeed', 0)
            dl_global = t.get('downloaded', 0)
            ul_global = t.get('uploaded', 0)
            eta = t.get('eta', 8640000)
            peers = t.get('num_incomplete', 0)
            seeds = t.get('num_complete', 0)
            ratio = t.get('ratio', 0.0)
            category = t.get('category', '')
            tags = t.get('tags', '')
            added_on = t.get('added_on', 0)
            availability = t.get('availability', -1.0)
            
            self._active_qbit_state = f"State: {state} | Progress: {int(prog_val * 100)}% | Size: {self._format_size(size)}"

            self.lbl_state_val.setText(state.capitalize())
            self.lbl_size_val.setText(self._format_size(size))
            self.prog_bar_dl.setValue(int(prog_val * 100))
            self.lbl_speed_val.setText(self._format_speed(dlspeed))

            # Update Foldout Dashboard
            if hasattr(self, 'foldout_labels'):
                self.foldout_labels["Size"].setText(self._format_size(size))
                self.foldout_labels["Progress"].setText(f"{int(prog_val * 100)} %")
                self.foldout_labels["DL Speed"].setText(self._format_speed(dlspeed))
                self.foldout_labels["UL Speed"].setText(self._format_speed(ulspeed))
                self.foldout_labels["Down (global)"].setText(self._format_size(dl_global))
                self.foldout_labels["Up (global)"].setText(self._format_size(ul_global))
                self.foldout_labels["ETA"].setText(self._format_time(eta))
                self.foldout_labels["Peers"].setText(str(peers))
                self.foldout_labels["Seeds"].setText(str(seeds))
                
                formatted_state = "Done" if state in ['uploading', 'stalledUP', 'pausedUP', 'completed'] or prog_val == 1.0 else state.capitalize()
                self.foldout_labels["State"].setText(f" {formatted_state} ")
                
                self.foldout_labels["Ratio"].setText(f"{ratio:.2f}")
                self.foldout_labels["Category"].setText(category if category else "(no category)")
                self.foldout_labels["Tags"].setText(tags if tags else "(no tags)")
                self.foldout_labels["Added On"].setText(self._format_timestamp(added_on))
                self.foldout_labels["Avail"].setText(f"{availability:.1f}" if availability >= 0 else "-1")

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
            self.close_flow()
            self.setParent(None)
