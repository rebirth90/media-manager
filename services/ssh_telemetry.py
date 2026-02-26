import os
import re
import paramiko
from PyQt6.QtCore import QThread, pyqtSignal

class SSHTelemetryClient(QThread):
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
            client.connect(hostname=host, username=user, password=password, timeout=5.0)
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
        return output if output else "No data found."

    def _calculate_conversion_progress(self, ff_log: str) -> int:
        matches = re.findall(r"time=(\d{2}):(\d{2}):(\d{2})", ff_log)
        if not matches:
            return 0
        h, m, s = matches[-1]
        total_seconds = int(h) * 3600 + int(m) * 60 + int(s)
        percentage = int((total_seconds / 7200) * 100)
        return min(percentage, 100)
