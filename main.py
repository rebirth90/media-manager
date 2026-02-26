import os
import re
import sys
import threading
import time
from typing import Any, Dict, List, Optional

import paramiko
import qbittorrentapi
import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from PyQt6.QtCore import Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QProgressBar, QPushButton,
    QRadioButton, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout,
    QWidget, QHeaderView
)

# Strictly load environment variables at the top level
load_dotenv()

# Instantiate the FastAPI backend
app = FastAPI(
    title="Secure PyQt6 + FastAPI Service",
    description="A cleanly architected Python micro-desktop application.",
    version="1.0.0"
)


@app.get("/", response_model=Dict[str, str])
async def root_status() -> Dict[str, str]:
    """Status endpoint validating the REST server is operational."""
    return {"status": "success", "message": "Secure Local Server is Running."}


def run_server(host: str, port: int) -> None:
    """Runs the Uvicorn server explicitly bound to a background thread block."""
    try:
        config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        print(f"Error starting Uvicorn background server: {e}", file=sys.stderr)


class SSHTelemetryClient(QThread):
    """Encapsulated background QThread to execute paramiko commands asynchronously."""
    telemetry_data = pyqtSignal(str, str, str, int)
    error = pyqtSignal(str)

    def run(self) -> None:
        host = os.getenv("SSH_HOST", "127.0.0.1")
        user = os.getenv("SSH_USER", "root")
        password = os.getenv("SSH_PASS", "toor")
        remote_app_dir = os.getenv("REMOTE_APP_DIR", "/opt/movie-conversion")

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # Hard timeout imposed to prevent GUI locking in network edge cases
            client.connect(hostname=host, username=user, password=password, timeout=10.0)

            db_out = self._exec_cmd(client, f'sqlite3 {remote_app_dir}/conversion_data.db -header -column "SELECT id, status, path FROM jobs;"')
            gen_out = self._exec_cmd(client, 'tail -n 15 /var/log/conversion/app.log')
            ff_out = self._exec_cmd(client, 'LATEST_LOG=$(ls -t /var/log/conversion/ffmpeg/*.log 2>/dev/null | head -n 1); if [ -n "$LATEST_LOG" ]; then tail -n 15 "$LATEST_LOG"; else echo "No active logs found."; fi')

            client.close()
            prog = self._calculate_conversion_progress(ff_out)
            self.telemetry_data.emit(db_out, gen_out, ff_out, prog)
        except Exception as e:
            self.error.emit(f"SSH Telemetry Failed: {str(e)}")

    def _exec_cmd(self, client: paramiko.SSHClient, command: str) -> str:
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode('utf-8').strip()
        if not output:
             return "No data found."
        return output

    def _calculate_conversion_progress(self, ff_log: str) -> int:
        matches = re.findall(r"time=(\d{2}):(\d{2}):(\d{2})", ff_log)
        if not matches:
            return 0
        h, m, s = matches[-1]
        total_seconds = int(h) * 3600 + int(m) * 60 + int(s)
        # Mock total duration to 2 hours (7200 seconds)
        percentage = int((total_seconds / 7200) * 100)
        return min(percentage, 100)


class QBittorrentClient(QThread):
    """Encapsulated background QThread to push torrent bytes and path safely."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    added = pyqtSignal()

    def __init__(self, torrent_bytes: bytes, save_path: str, parent=None) -> None:
        super().__init__(parent)
        self.torrent_bytes = torrent_bytes
        self.save_path = save_path

    def run(self) -> None:
        host = os.getenv("QBIT_HOST", "127.0.0.1")
        port = os.getenv("QBIT_PORT", "8080")
        user = os.getenv("QBIT_USER", "admin")
        password = os.getenv("QBIT_PASS", "adminadmin")

        try:
            client = qbittorrentapi.Client(host=f"http://{host}:{port}", username=user, password=password)
            client.auth_log_in()
            res = client.torrents_add(
                torrent_files={'downloaded.torrent': self.torrent_bytes},
                save_path=self.save_path
            )
            self.finished.emit(f"QBittorrent Push Success! Server Response: {res}")
            self.added.emit()
        except Exception as e:
            self.error.emit(f"QBittorrent Upload Failed: {str(e)}")


class TorrentPollingThread(QThread):
    """Secure polling daemon executing strictly on a synchronized QThread."""
    data_updated = pyqtSignal(list)
    torrent_completed = pyqtSignal()
    target_progress = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active = True
        self.target_hash: Optional[str] = None
        self.is_waiting_for_new_target: bool = False
        self.hashes_before_add: List[str] = []
        self.host = os.getenv("QBIT_HOST", "127.0.0.1")
        self.port = os.getenv("QBIT_PORT", "8080")
        self.user = os.getenv("QBIT_USER", "admin")
        self.password = os.getenv("QBIT_PASS", "adminadmin")

    def set_pre_add_state(self, hashes: List[str]) -> None:
        """Takes a volatile snapshot of active torrents to detect the push target."""
        self.hashes_before_add = hashes
        self.target_hash = None
        self.is_waiting_for_new_target = True

    def run(self) -> None:
        client = qbittorrentapi.Client(host=f"{self.host}:{self.port}", username=self.user, password=self.password)
        try:
            client.auth_log_in()
        except Exception as e:
            self.error.emit(f"Polling Auth Failed: {str(e)}")
            return

        while self.active:
            try:
                torrents = client.torrents_info()
                current_hashes = [t.get('hash') for t in torrents]

                # Detection logic for dynamically tracking the pushed torrent
                if self.is_waiting_for_new_target and current_hashes:
                    for h in current_hashes:
                        if h not in self.hashes_before_add:
                            self.target_hash = h
                            self.is_waiting_for_new_target = False
                            break

                # Filter datablock for UI representation
                target_torrent_data = []

                # Continuous state monitoring
                if self.target_hash:
                    for t in torrents:
                        if t.get('hash') == self.target_hash:
                            target_torrent_data.append(t)
                            prog = t.get('progress', 0.0)
                            self.target_progress.emit(int(prog * 100))
                            state = t.get('state', '')
                            if prog == 1.0 or state in ['uploading', 'stalledUP', 'pausedUP', 'completed']:
                                self.torrent_completed.emit()
                                self.target_hash = None  # Block cascade loops
                            break
                            
                # Push only the targeted payload (or empty list if none) and all background hashes
                self.data_updated.emit([target_torrent_data, current_hashes])

            except Exception as e:
                self.error.emit(f"Polling Error: {str(e)}")

            # Controlled polling cadence (no lockups on the event stream)
            QThread.sleep(2)

    def stop(self) -> None:
        """Signal teardown to prevent trailing QTimer anomalies."""
        self.active = False
        self.wait()


class MediaCategoryDialog(QDialog):
    """Dynamic dialog strictly architected for modular media routing."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Categorize Intersected Media")
        self.setFixedSize(400, 200)

        self.layout = QVBoxLayout(self)

        # Radio Toggles
        self.radio_group = QGroupBox("Media Type")
        self.radio_layout = QHBoxLayout()
        self.btn_movie = QRadioButton("Movies")
        self.btn_tv = QRadioButton("TV-Series")
        self.btn_movie.setChecked(True)
        self.radio_layout.addWidget(self.btn_movie)
        self.radio_layout.addWidget(self.btn_tv)
        self.radio_group.setLayout(self.radio_layout)
        self.layout.addWidget(self.radio_group)

        # Dynamic Forms Block
        self.form_layout = QFormLayout()

        # Movie Dropdown (Strict definitions)
        self.genre_dropdown = QComboBox()
        self.genre_dropdown.addItems([
            "action", "adventure", "anime", "bollywood", "cartoons", "comedy",
            "crime", "detective", "drama", "family", "fantasy", "horror",
            "romance", "sf", "thriller", "zombie"
        ])

        # TV LineEdit Input
        self.series_input = QLineEdit()
        self.series_input.setPlaceholderText("e.g. breaking bad")
        
        # State logic binding (Movies selected by default)
        self.series_input.hide()
        
        self.form_label_genre = QLabel("Genre:")
        self.form_label_series = QLabel("Series Name:")
        self.form_label_series.hide()

        self.form_layout.addRow(self.form_label_genre, self.genre_dropdown)
        self.form_layout.addRow(self.form_label_series, self.series_input)
        self.layout.addLayout(self.form_layout)

        # Standard dialog execution mapping
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        # Signal bounds
        self.btn_movie.toggled.connect(self._toggle_inputs)
        self.btn_tv.toggled.connect(self._toggle_inputs)

    def _toggle_inputs(self) -> None:
        """Dynamically hides/shows strictly irrelevant inputs based on selected category."""
        if self.btn_movie.isChecked():
            self.series_input.hide()
            self.form_label_series.hide()
            self.genre_dropdown.show()
            self.form_label_genre.show()
        else:
            self.genre_dropdown.hide()
            self.form_label_genre.hide()
            self.series_input.show()
            self.form_label_series.show()

    def get_relative_path(self) -> str:
        """Computes the final relative path string per absolute organizational boundaries."""
        if self.btn_movie.isChecked():
            genre = self.genre_dropdown.currentText()
            return f"movies/{genre}"
        else:
            name = self.series_input.text().strip().lower().replace(" ", "_")
            if not name:
                name = "unknown_series"
            return f"tv-series/{name}"


class SecureServerWindow(QMainWindow):
    """
    Main application window strictly encapsulating GUI layout logic in OOP fashion.
    Forces True Fullscreen architecture and houses the asynchronous services.
    """
    def __init__(self, host: str, port: int) -> None:
        super().__init__()
        self.setWindowTitle("Secure Enterprise Local Server")
        self.showFullScreen()

        # In-memory torrent state allocations
        self.torrent_bytes: Optional[bytes] = None
        self.download_url: str = ""
        self.relative_path: str = ""

        # Tracking active pipeline strings
        self.current_qbit_hashes: List[str] = []

        central_widget = QWidget()
        self.main_layout = QVBoxLayout(central_widget)

        # Status Label Implementation
        env_mode = os.getenv("APP_ENV", "development")
        self.status_label = QLabel(
            f"Mode: {env_mode.upper()}\n"
            f"Backend Status: Running\n"
            f"Location: {host}:{port}\n"
            f"Active Torrent Target: None"
        )
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #f39c12;")
        self.main_layout.addWidget(self.status_label)

        # Progress Bars Layer
        progress_layout = QHBoxLayout()
        self.qbit_progress = QProgressBar()
        self.qbit_progress.setRange(0, 100)
        self.qbit_progress.setFormat("Download: %p%")
        progress_layout.addWidget(self.qbit_progress)

        self.conv_progress = QProgressBar()
        self.conv_progress.setRange(0, 100)
        self.conv_progress.setFormat("Conversion: %p%")
        progress_layout.addWidget(self.conv_progress)

        self.main_layout.addLayout(progress_layout)

        # Actions Panel Implementation
        action_layout = QHBoxLayout()

        self.btn_web = QPushButton("1. Open Filelist Browser")
        self.btn_qbit = QPushButton("2. Push to qBittorrent Engine")
        self.btn_ssh = QPushButton("3. SSH Telemetry Pull")
        self.btn_ssh.setCheckable(True)
        self.btn_exit = QPushButton("Exit Fullscreen")

        # Layout integration
        action_layout.addWidget(self.btn_web)
        action_layout.addWidget(self.btn_qbit)
        action_layout.addWidget(self.btn_ssh)
        action_layout.addWidget(self.btn_exit)
        self.main_layout.addLayout(action_layout)

        # Explicit Event Hook Mappings
        self.btn_web.clicked.connect(self._toggle_browser)
        self.btn_qbit.clicked.connect(self._push_to_qbit)
        self.btn_ssh.clicked.connect(self._toggle_ssh_telemetry)
        self.btn_exit.clicked.connect(self.close)

        # Live Tail Polling Hook
        self.ssh_timer = QTimer(self)
        self.ssh_timer.timeout.connect(self._pull_ssh)
        self.ssh_timer.setInterval(3000)

        # Structural Split
        split_layout = QVBoxLayout()

        # Telemetry Panels Layer
        telemetry_layout = QHBoxLayout()

        # Database Queue
        self.db_table = QTableWidget(0, 3)
        self.db_table.setHorizontalHeaderLabels(["ID", "Status", "Path"])
        self.db_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.db_table.setStyleSheet("background-color: #2b2b2b; color: #ffffff;")
        db_group = QGroupBox("Live Database Queue")
        db_layout = QVBoxLayout()
        db_layout.addWidget(self.db_table)
        db_group.setLayout(db_layout)
        telemetry_layout.addWidget(db_group, stretch=1)

        # General App Log
        self.gen_log = QTextEdit()
        self.gen_log.setReadOnly(True)
        self.gen_log.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: monospace; font-size: 9pt;")
        gen_group = QGroupBox("General App Log")
        gen_layout = QVBoxLayout()
        gen_layout.addWidget(self.gen_log)
        gen_group.setLayout(gen_layout)
        telemetry_layout.addWidget(gen_group, stretch=1)

        # FFmpeg Encode Log
        self.ffmpeg_log = QTextEdit()
        self.ffmpeg_log.setReadOnly(True)
        self.ffmpeg_log.setStyleSheet("background-color: #1e1e1e; color: #f39c12; font-family: monospace; font-size: 9pt;")
        ffmpeg_group = QGroupBox("FFmpeg Encode Log")
        ffmpeg_layout = QVBoxLayout()
        ffmpeg_layout.addWidget(self.ffmpeg_log)
        ffmpeg_group.setLayout(ffmpeg_layout)
        telemetry_layout.addWidget(ffmpeg_group, stretch=1)

        split_layout.addLayout(telemetry_layout, stretch=2)

        # Torrent Data Dashboard UI (polling sink)
        self.torrent_table = QTableWidget(0, 4)
        self.torrent_table.setHorizontalHeaderLabels(["Name", "Size", "Progress", "State"])
        self.torrent_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.torrent_table.setStyleSheet("background-color: #2b2b2b; color: #ffffff;")
        split_layout.addWidget(self.torrent_table, stretch=1)

        self.main_layout.addLayout(split_layout)

        # Central Viewport Element
        self.web_view = QWebEngineView()
        self.web_view.hide()
        self.main_layout.addWidget(self.web_view, stretch=1)

        # Chromium Pipeline Interception Slot
        profile = self.web_view.page().profile()
        profile.downloadRequested.connect(self._on_download_requested)
        self.web_view.page().loadFinished.connect(self._on_page_loaded)

        self.setCentralWidget(central_widget)

        # Instantiating Live Polling on secondary CPU block
        self._start_torrent_polling()

    def _start_torrent_polling(self) -> None:
        """Isolated binding for QThread QTimer logic."""
        self.poll_worker = TorrentPollingThread()
        self.poll_worker.data_updated.connect(self._update_torrent_table)
        self.poll_worker.torrent_completed.connect(self._on_torrent_target_complete)
        self.poll_worker.target_progress.connect(self.qbit_progress.setValue)
        self.poll_worker.error.connect(self.log_console)
        self.poll_worker.start()

    def _update_torrent_table(self, data_payload: List[Any]) -> None:
        """Securely executes back on Qt MainThread strictly processing UI layout mutations."""
        target_torrents, all_hashes_in_background = data_payload
        
        # Maintain background hash state for `set_pre_add_state` tracking
        self.current_qbit_hashes = all_hashes_in_background
        
        self.torrent_table.setRowCount(len(target_torrents))
        for row, t in enumerate(target_torrents):
            name = t.get('name', 'Unknown')
            size = f"{t.get('size', 0) / (1024**2):.2f} MB"
            prog = f"{t.get('progress', 0) * 100:.1f}%"
            state = t.get('state', 'Unknown')

            self.torrent_table.setItem(row, 0, QTableWidgetItem(name))
            self.torrent_table.setItem(row, 1, QTableWidgetItem(size))
            self.torrent_table.setItem(row, 2, QTableWidgetItem(prog))
            self.torrent_table.setItem(row, 3, QTableWidgetItem(state))

    def _on_torrent_target_complete(self) -> None:
        """Fires safely in MainThread when daemon target states completion logic bounds are hit."""
        self.log_console("Target Tracking Alert: Upload/Download pipeline marked COMPLETED.")
        self.btn_qbit.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_qbit.setText("2. ✔ Push Complete")

    def log_console(self, text: str) -> None:
        """Appends output securely to the read-only dashboard console."""
        if hasattr(self, 'gen_log'):
            self.gen_log.append(f"> {text}")

    def _toggle_browser(self) -> None:
        if self.web_view.isHidden():
            self.web_view.show()
            self.web_view.setUrl(QUrl("https://filelist.io/login.php"))
            self.log_console("Engine instantiated for Automated Login Sequence.")
        else:
            self.web_view.hide()

    def _on_download_requested(self, request: QWebEngineDownloadRequest) -> None:
        """Intercepts Qt's file-based download pipeline to natively push to disk."""
        self.download_url = request.url().toString()
        temp_dir = os.path.join(os.getcwd(), "temp_torrents")
        os.makedirs(temp_dir, exist_ok=True)
        
        request.setDownloadDirectory(temp_dir)
        request.accept()
        request.stateChanged.connect(lambda state: self._on_download_state_changed(state, request))
        
        self.log_console(f"Intercepting download stream natively to disk: {temp_dir}")

    def _on_page_loaded(self, ok: bool) -> None:
        """Automates Filelist authentication loop strictly post-DOM load."""
        if not ok:
            return

        current_url = self.web_view.url().toString()
        if "login.php" in current_url:
            self.log_console("Automating Filelist Security Challenge...")

            user = os.getenv("FILELIST_USER", "")
            password = os.getenv("FILELIST_PASS", "")

            # Javascript DOM injection payload addressing input elements securely
            js_code = f"""
                (function() {{
                    var userField = document.querySelector('input[name="username"]');
                    var passField = document.querySelector('input[name="password"]');
                    var unlockBox = document.querySelector('input[name="unlock"]');
                    var submitBtn = document.querySelector('input[type="submit"]');

                    if(userField && passField && unlockBox) {{
                        userField.value = "{user}";
                        passField.value = "{password}";
                        unlockBox.checked = true;
                        if(submitBtn) {{
                            submitBtn.click();
                        }} else {{
                            document.forms[0].submit();
                        }}
                    }}
                }})();
            """
            self.web_view.page().runJavaScript(js_code)

    def _on_download_state_changed(self, state: QWebEngineDownloadRequest.DownloadState, request: QWebEngineDownloadRequest) -> None:
        """Tracks the lifecycle of the torrent file arriving on disk."""
        if state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            file_path = request.downloadDirectory() + os.sep + request.downloadFileName()
            self.web_view.hide()
            self.log_console(f"Stream acquired natively to disk: {file_path}. Spawning Dialog...")
            self._process_downloaded_torrent(file_path)

    def _process_downloaded_torrent(self, file_path: str) -> None:
        """Completes the disk bridge, spawns synchronous Categorization UX mapping, and cleans up."""
        try:
            # Modal Event Loop Hijack
            dialog = MediaCategoryDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.relative_path = dialog.get_relative_path()
                self.log_console(f"Categorization String Defined -> {self.relative_path}")
                
                with open(file_path, "rb") as f:
                    self.torrent_bytes = f.read()

                # Success Mutation
                self.btn_web.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
                self.btn_web.setText("1. ✔ Torrent Assigned")

                # State Overlay Shift
                env_mode = os.getenv("APP_ENV", "development")
                self.status_label.setText(
                    f"Mode: {env_mode.upper()}\n"
                    f"Backend Status: Running\n"
                    f"Location: {os.getenv('SERVER_HOST')}:{os.getenv('LOCAL_PORT')}\n"
                    f"Active Torrent Target: {self.relative_path}"
                )
                self._push_to_qbit()
            else:
                self.log_console("User aborted categorization flow. Torrent cache in volatile state voided.")
                self.torrent_bytes = None

        except Exception as e:
            self.log_console(f"CRITICAL ERROR: Native file acquisition collapsed: {str(e)}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.log_console("Volatile file state purged from local IO.")

    def _push_to_qbit(self) -> None:
        """Dispatches fully constructed state packet into off-the-books network loop."""
        if not self.torrent_bytes or not self.relative_path:
            self.log_console("FATAL: Torrent stream unassigned or categorization absent. Obtain via GUI Engine block.")
            return

        base_path = os.getenv("BASE_SCRATCH_PATH", "/data/scratch")
        
        # OS-agnostic native path binding formatting
        final_save_path = f"{base_path}/{self.relative_path}".replace("\\", "/")

        self.log_console(f"Pushing dynamically categorized data structures to -> {final_save_path}")

        # Mark heuristic map point for TorPolling tracking
        self.poll_worker.set_pre_add_state(self.current_qbit_hashes)

        # Isolate pushing to decoupled class routine
        self.qbit_worker = QBittorrentClient(self.torrent_bytes, final_save_path)
        self.qbit_worker.finished.connect(self.log_console)
        self.qbit_worker.error.connect(self.log_console)
        self.qbit_worker.start()

    def _toggle_ssh_telemetry(self) -> None:
        if self.btn_ssh.isChecked():
            self.btn_ssh.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")
            self.btn_ssh.setText("3. Stop Telemetry")
            self._pull_ssh()
            self.ssh_timer.start()
        else:
            self.btn_ssh.setStyleSheet("")
            self.btn_ssh.setText("3. SSH Telemetry Pull")
            self.ssh_timer.stop()

    def _pull_ssh(self) -> None:
        """Routes SSH stream request to decoupled QThread block."""
        if hasattr(self, 'ssh_worker') and self.ssh_worker.isRunning():
            return

        self.ssh_worker = SSHTelemetryClient()
        self.ssh_worker.telemetry_data.connect(self._update_telemetry_ui)
        self.ssh_worker.error.connect(self.log_console)
        self.ssh_worker.start()

    def _update_telemetry_ui(self, db_out: str, gen_out: str, ff_out: str, prog: int) -> None:
        """Updates GUI from thread-safe signals."""
        self.conv_progress.setValue(prog)
        if hasattr(self, 'gen_log'):
            self.gen_log.setText(gen_out)
            self.ffmpeg_log.setText(ff_out)
        
        # Parse DB output
        lines = db_out.split('\n')
        # We skip the first 2 lines (header and dashes)
        if len(lines) > 2:
            data_lines = lines[2:]
            self.db_table.setRowCount(len(data_lines))
            for row, line in enumerate(data_lines):
                parts = re.split(r'\s{2,}', line.strip())
                if len(parts) < 3:
                     parts = line.split(maxsplit=2)
                for col, part in enumerate(parts[:3]):
                    if part:
                        self.db_table.setItem(row, col, QTableWidgetItem(part))
        else:
            self.db_table.setRowCount(0)

    def closeEvent(self, event) -> None:
        """Overrides generic exit to dismantle active background pooling loops correctly."""
        self.poll_worker.stop()
        super().closeEvent(event)


def main() -> None:
    # 1. Configuration & Secrets extraction
    server_host: str = os.getenv("SERVER_HOST", "127.0.0.1")
    port_str: str = os.getenv("LOCAL_PORT", "9000")

    try:
        server_port: int = int(port_str)
    except ValueError:
        server_port = 9000

    # 2. Asynchronous API loop isolated outside Qt domain
    server_thread = threading.Thread(
        target=run_server,
        args=(server_host, server_port),
        daemon=True
    )
    server_thread.start()

    # 3. Synchronous QT Object Root
    qt_app = QApplication(sys.argv)
    main_window = SecureServerWindow(host=server_host, port=server_port)
    main_window.showFullScreen()

    # 4. Process execution block override
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
