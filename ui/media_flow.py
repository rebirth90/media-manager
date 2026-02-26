import os
from typing import List, Any
import qbittorrentapi
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from workers.image_downloader import ImageDownloaderThread
from workers.torrent_poller import TorrentPollingThread
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

        # Enhanced card styling matching mockup - cleaner, more professional
        self.setStyleSheet("""
            QFrame { 
                background-color: #ffffff; 
                border: 1.5px solid #dce9f2;
                border-radius: 14px;
                padding: 14px;
                margin: 5px 0;
            }
            QFrame:hover {
                background-color: #f8fcff;
                border-color: #b8d8e8;
                box-shadow: 0 4px 12px rgba(40, 100, 140, 0.1);
            }
            QLabel { 
                color: #1e293b; 
                font-size: 11pt; 
                font-family: 'Segoe UI', 'San Francisco', 'Helvetica Neue', Arial; 
            }
            QPushButton { 
                background-color: #f4f8fc; 
                color: #475569; 
                border: 1.8px solid #c8d8e8; 
                border-radius: 16px; 
                padding: 10px 20px; 
                font-weight: 600; 
                font-size: 9.5pt;
                min-width: 130px;
            }
            QPushButton:hover { 
                background-color: #e0ecf5; 
                border-color: #98b8d0;
            }
        """)
        self.setFixedHeight(82)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(18, 10, 18, 10)
        self.main_layout.setSpacing(14)

        # Title with index - refined typography
        self.title_lbl = QLabel(f"{self.flow_index}. {self.title}")
        self.title_lbl.setStyleSheet("""
            font-size: 12.5pt; 
            font-weight: 600;
            color: #0d1e30;
            letter-spacing: -0.4px;
        """)
        self.main_layout.addWidget(self.title_lbl, stretch=2)

        # Status buttons with mockup-inspired design
        self.btn_download = QPushButton("▶ Start Project")
        self.btn_convert = QPushButton("✎ Edit Content")
        self.btn_finish = QPushButton("✔ Approve & Share")
        
        # Add cursor pointer for better UX
        self.btn_download.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_convert.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_finish.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.btn_download.clicked.connect(self._open_details_modal)
        self.btn_convert.clicked.connect(self._open_details_modal)
        self.btn_finish.clicked.connect(self._open_details_modal)

        self.main_layout.addWidget(self.btn_download)
        self.main_layout.addSpacing(10)
        
        # Enhanced arrow with better visual weight
        arrow1 = QLabel("→")
        arrow1.setStyleSheet("color: #b0c5d5; font-size: 15pt; font-weight: 600;")
        self.main_layout.addWidget(arrow1)
        self.main_layout.addSpacing(10)
        
        self.main_layout.addWidget(self.btn_convert)
        self.main_layout.addSpacing(10)
        
        arrow2 = QLabel("→")
        arrow2.setStyleSheet("color: #b0c5d5; font-size: 15pt; font-weight: 600;")
        self.main_layout.addWidget(arrow2)
        self.main_layout.addSpacing(10)
        
        self.main_layout.addWidget(self.btn_finish)

        self._start_flow()

    def _open_details_modal(self) -> None:
        modal = FlowDetailsModal(
            title=self.title,
            qbit_state=self._active_qbit_state,
            ffmpeg_log=self._active_ffmpeg_log,
            illustration_path=self._illustration_path,
            parent=self.window()
        )
        modal.exec()

    def _start_flow(self) -> None:
        # Initialize with "Start Project" state - refined blue accent
        self.btn_download.setStyleSheet("""
            QPushButton { 
                border: 2.8px solid #5ba3d0; 
                background-color: #e8f4fc; 
                color: #0d4068;
                font-weight: 600;
                box-shadow: 0 0 0 3px rgba(91, 163, 208, 0.15);
            }
            QPushButton:hover {
                background-color: #d0e8f8;
                border-color: #3b8bc0;
                box-shadow: 0 0 0 4px rgba(91, 163, 208, 0.2);
            }
        """)
        self.btn_download.setText("▶ Initializing DB")

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

    def _update_torrent_ui(self, data_payload: List[Any]) -> None:
        target_torrents, _ = data_payload
        if target_torrents:
            t = target_torrents[0]
            prog_val = t.get('progress', 0)
            state = t.get('state', 'Unknown')
            dlspeed = t.get('dlspeed', 0) / (1024**2)
            
            self._active_qbit_state = f"State: {state} | Progress: {int(prog_val * 100)}% | Speed: {dlspeed:.1f} MB/s"

            # Downloading state - refined amber/yellow scheme
            if prog_val < 1.0 and state not in ['error', 'missingFiles']:
                self.btn_download.setText(f"⏳ Downloading {int(prog_val * 100)}%")
                self.btn_download.setStyleSheet("""
                    QPushButton { 
                        border: 2.8px solid #e8a838; 
                        background-color: #fef8e8; 
                        color: #a86810;
                        font-weight: 600;
                        box-shadow: 0 0 0 3px rgba(232, 168, 56, 0.15);
                    }
                    QPushButton:hover {
                        background-color: #fef0d0;
                        border-color: #d89820;
                        box-shadow: 0 0 0 4px rgba(232, 168, 56, 0.2);
                    }
                """)
            
            # Error state - refined red scheme
            elif state in ['error', 'missingFiles']:
                self.btn_download.setText("⚠ Torrent Error")
                self.btn_download.setStyleSheet("""
                    QPushButton { 
                        border: 2.8px solid #e85858; 
                        background-color: #fee8e8; 
                        color: #a81818;
                        font-weight: 600;
                        box-shadow: 0 0 0 3px rgba(232, 88, 88, 0.15);
                    }
                    QPushButton:hover {
                        background-color: #fed0d0;
                        border-color: #d83838;
                        box-shadow: 0 0 0 4px rgba(232, 88, 88, 0.2);
                    }
                """)

            # Completed state - transition to encoding
            if prog_val == 1.0 or state in ['uploading', 'stalledUP', 'pausedUP', 'completed']:
                if not hasattr(self, 'ssh_timer'):
                    # Download complete - refined neutral state
                    self.btn_download.setText("✓ Verified")
                    self.btn_download.setStyleSheet("""
                        QPushButton { 
                            background-color: #f4f8fc; 
                            color: #5a7088; 
                            border: 1.8px solid #c0d0e0;
                            font-weight: 600;
                        }
                    """)
                    
                    # Activate encoding button - refined amber/processing state
                    self.btn_convert.setText("✎ Encoding 0%")
                    self.btn_convert.setStyleSheet("""
                        QPushButton { 
                            border: 2.8px solid #e8a838; 
                            background-color: #fef8e8; 
                            color: #a86810;
                            font-weight: 600;
                            box-shadow: 0 0 0 3px rgba(232, 168, 56, 0.15);
                        }
                        QPushButton:hover {
                            background-color: #fef0d0;
                            border-color: #d89820;
                            box-shadow: 0 0 0 4px rgba(232, 168, 56, 0.2);
                        }
                    """)
                    self._active_qbit_state = "Completed Verification."
                    
                    # Start SSH telemetry polling
                    self.ssh_timer = QTimer(self)
                    self.ssh_timer.timeout.connect(self._pull_ssh)
                    self.ssh_timer.setInterval(3000)
                    self.ssh_timer.start()

    def _pull_ssh(self) -> None:
        if hasattr(self, 'ssh_worker') and self.ssh_worker.isRunning(): 
            return
        self.ssh_worker = SSHTelemetryClient(self)
        self.ssh_worker.telemetry_data.connect(self._update_telemetry_ui)
        self.ssh_worker.start()

    def _update_telemetry_ui(self, db_out: str, gen_out: str, ff_out: str, prog: int) -> None:
        self._active_ffmpeg_log = ff_out
        self.btn_convert.setText(f"✎ Encoding {prog}%")
        
        # Encoding complete - refined success state
        if prog >= 100:
            self.btn_convert.setText("✓ Encoded")
            self.btn_convert.setStyleSheet("""
                QPushButton { 
                    background-color: #f4f8fc; 
                    color: #5a7088; 
                    border: 1.8px solid #c0d0e0;
                    font-weight: 600;
                }
            """)
            
            # Activate final approval button - refined green success
            self.btn_finish.setText("✔ Approve & Share")
            self.btn_finish.setStyleSheet("""
                QPushButton { 
                    border: 2.8px solid #28a868; 
                    background-color: #e8faf0; 
                    color: #106840;
                    font-weight: 600;
                    box-shadow: 0 0 0 3px rgba(40, 168, 104, 0.15);
                }
                QPushButton:hover {
                    background-color: #d0f5e0;
                    border-color: #189850;
                    box-shadow: 0 0 0 4px rgba(40, 168, 104, 0.2);
                }
            """)
            
            if hasattr(self, 'ssh_timer'): 
                self.ssh_timer.stop()

    def close_flow(self) -> None:
        if hasattr(self, 'poll_worker'): 
            self.poll_worker.stop()
        if hasattr(self, 'ssh_timer'): 
            self.ssh_timer.stop()
        if hasattr(self, 'ssh_worker') and self.ssh_worker.isRunning(): 
            self.ssh_worker.wait()
