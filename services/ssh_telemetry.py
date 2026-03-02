import os
import re
import paramiko
from PyQt6.QtCore import QThread, pyqtSignal

class SSHTelemetryClient(QThread):
    telemetry_data = pyqtSignal(str, str, int, str, str)
    error = pyqtSignal(str)

    def __init__(self, target_title: str, parent=None) -> None:
        super().__init__(parent)
        self.target_title = target_title
        self.safe_title = re.sub(r'[\\/*?:"<>| \']', "_", self.target_title)

    def run(self) -> None:
        host = os.getenv("CONVERSION_SSH_HOST", "192.168.10.109")
        user = os.getenv("CONVERSION_SSH_USER", "root")
        password = os.getenv("CONVERSION_SSH_PASS", "toor")
        remote_app_dir = os.getenv("REMOTE_APP_DIR", "/opt/movie-conversion")
        
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=host, username=user, password=password, timeout=5.0)

            sql_title = self.safe_title.replace("'", "''")
            db_cmd = f'sqlite3 {remote_app_dir}/conversion_data.db -column "SELECT status FROM jobs WHERE path LIKE \'%{sql_title}%\' ORDER BY id DESC LIMIT 1;"'
            db_status = self._exec_cmd(client, db_cmd) or "NOT STARTED"

            gen_cmd = f'LOG=$(ls -t /var/log/conversion/general/*{self.safe_title}*.log 2>/dev/null | head -n 1); if [ -n "$LOG" ]; then cat "$LOG"; else echo "Pending..."; fi'
            full_gen_log = self._exec_cmd(client, gen_cmd)

            ff_cmd = f'LOG=$(ls -t /var/log/conversion/ffmpeg/*{self.safe_title}*.log 2>/dev/null | head -n 1); if [ -n "$LOG" ]; then tail -n 50 "$LOG"; else echo "Pending..."; fi'
            ff_tail = self._exec_cmd(client, ff_cmd)
            
            ff_full_cmd = f'LOG=$(ls -t /var/log/conversion/ffmpeg/*{self.safe_title}*.log 2>/dev/null | head -n 1); if [ -n "$LOG" ]; then cat "$LOG"; fi'
            ff_full_log = self._exec_cmd(client, ff_full_cmd)
            prog = self._calculate_conversion_progress(ff_full_log)
            
            sub_status = "Pending"
            if "Extracting subtitles" in full_gen_log:
                sub_status = "In Progress"
            if "Extracted" in full_gen_log or "Converted" in full_gen_log:
                sub_status = "Completed"
            if "No subtitles found" in full_gen_log:
                sub_status = "None"

            client.close()
            self.telemetry_data.emit(db_status, sub_status, prog, full_gen_log, ff_tail)
        except Exception as e:
            self.error.emit(f"SSH Telemetry Failed: {str(e)}")

    def _exec_cmd(self, client: paramiko.SSHClient, command: str) -> str:
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode('utf-8').strip()
        return output if output else "No data found."

    def _calculate_conversion_progress(self, ff_log: str) -> int:
        if not ff_log or ff_log == "No data found.": 
            return 0
            
        duration_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})", ff_log)
        if not duration_match: 
            return 0
            
        dh, dm, ds = duration_match.groups()
        total_seconds = int(dh) * 3600 + int(dm) * 60 + int(ds)
        if total_seconds == 0: 
            return 0

        time_matches = re.findall(r"time=(\d{2}):(\d{2}):(\d{2})", ff_log)
        if not time_matches: 
            return 0
            
        ch, cm, cs = time_matches[-1]
        current_seconds = int(ch) * 3600 + int(cm) * 60 + int(cs)
        
        return min(int((current_seconds / total_seconds) * 100), 100)
