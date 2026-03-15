import os
import re
import json
import paramiko
import time
import base64
import shlex
from PyQt6.QtCore import QThread

from src.domain.repositories import IMediaRepository
from src.application.use_cases.sync_use_cases import SyncConversionStateUseCase

class SSHTelemetryClient(QThread):
    """
    Background infrastructure task that polls SSH Conversion Telemetry for a specific media item.
    Updates the repository and triggers UseCase signals over the EventBus.
    """
    def __init__(self, repo: IMediaRepository, sync_use_case: SyncConversionStateUseCase, item_id: int, target_title: str, parent=None) -> None:
        super().__init__(parent)
        self.repo = repo
        self.sync_use_case = sync_use_case
        self.item_id = item_id
        self.target_title = target_title
        self.safe_title = re.sub(r'[\\/*?:"<>| \']', "_", self.target_title)
        self._is_running = True

    def stop(self):
        self._is_running = False
        self.wait()

    def _get_remote_script_b64(self) -> str:
        """Reads the companion telemetry script from disk and base64 encodes it."""
        script_path = os.path.join(os.path.dirname(__file__), 'remote_telemetry.py')
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        return base64.b64encode(script_content.encode('utf-8')).decode('utf-8')

    def run(self) -> None:
        host = os.getenv("SSH_HOST")
        user = os.getenv("SSH_USER")
        password = os.getenv("SSH_PASS")
        remote_app_dir = os.getenv("REMOTE_APP_DIR")

        if not all([host, user, password, remote_app_dir]):
            return

        search_target = self.target_title
        explicit_season = ""
        
        try:
            item = self.repo.get_item(self.item_id)
            if item:
                search_target = item.relative_path if getattr(item, 'relative_path', None) else self.target_title
                explicit_season = str(getattr(item, 'season', ''))
        except Exception:
            pass

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=host, username=user, password=password, timeout=5.0)

            # 1. Get the base64 encoded payload of our cleanly separated file
            b64_script = self._get_remote_script_b64()

            # 2. Use shlex.quote to prevent command injection via file names or titles
            safe_target = shlex.quote(search_target)
            safe_season = shlex.quote(explicit_season)
            safe_dir = shlex.quote(remote_app_dir)

            # 3. Construct the execution command. 
            # `python3 -` tells Python to execute the script from standard input while still accepting CLI args.
            db_cmd = (
                f"echo {b64_script} | base64 -d | "
                f"python3 - --target {safe_target} --season {safe_season} --dir {safe_dir}"
            )

            while self._is_running:
                stdin, stdout, stderr = client.exec_command(db_cmd)
                raw_output = stdout.read().decode('utf-8').strip()
                
                stdin.close()
                stdout.close()
                stderr.close()
                
                try:
                    match = re.search(r'\[.*\]', raw_output, re.DOTALL)
                    if match:
                        json_str = match.group()
                        
                        try:
                            results = json.loads(json_str)
                            # Stop fetching if everything is completed
                            if results and isinstance(results, list) and all(r.get("db_status", "").upper() == "COMPLETED" for r in results):
                                self.sync_use_case.execute(self.item_id, json_str)
                                self._is_running = False 
                                break
                        except json.JSONDecodeError:
                            pass
                            
                        self.sync_use_case.execute(self.item_id, json_str)
                    elif raw_output:
                        self.sync_use_case.execute(self.item_id, raw_output)
                except json.JSONDecodeError:
                    pass
                    
                for _ in range(30):
                    if not self._is_running:
                        break
                    time.sleep(0.1)

        except Exception:
            pass
        finally:
            # Ensure the connection actually closes if the thread is stopped or fails
            try:
                client.close()
            except:
                pass