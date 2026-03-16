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
    def __init__(self, repo: IMediaRepository, sync_use_case: SyncConversionStateUseCase, item_id: int, target_title: str, run_once: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.repo = repo
        self.sync_use_case = sync_use_case
        self.item_id = item_id
        self.target_title = target_title
        self.safe_title = re.sub(r'[\\/*?:"<>| \']', "_", self.target_title)
        self._is_running = True
        self._run_once = run_once

    def stop(self):
        self._is_running = False
        self.wait()

    def _get_remote_script_b64(self) -> str:
        """Reads the companion telemetry script from disk and base64 encodes it."""
        script_path = os.path.join(os.path.dirname(__file__), 'remote_telemetry.py')
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        return base64.b64encode(script_content.encode('utf-8')).decode('utf-8')

    def _download_logs_for_completed_jobs(self, client: paramiko.SSHClient, results: list) -> None:
        """Fetches remote logs only after conversion completion and stores local file paths in payload."""
        try:
            sftp = client.open_sftp()
        except Exception:
            sftp = None

        app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        logs_root = os.path.join(app_root, "temp_torrents", "conversion_logs", f"item_{self.item_id}")
        os.makedirs(logs_root, exist_ok=True)

        try:
            for idx, row in enumerate(results):
                status = str(row.get("db_status", "")).upper()
                if status != "COMPLETED":
                    continue

                for remote_key, local_key, prefix in (
                    ("gen_log_remote_path", "gen_log_local_path", "general"),
                    ("ff_log_remote_path", "ff_log_local_path", "ffmpeg"),
                ):
                    remote_path = str(row.get(remote_key, "") or "").strip()
                    if not remote_path:
                        continue

                    base_name = os.path.basename(remote_path) or f"{prefix}_{idx + 1}.log"
                    safe_name = re.sub(r'[^A-Za-z0-9._-]+', '_', base_name)
                    local_name = f"{idx + 1:02d}_{prefix}_{safe_name}"
                    local_path = os.path.join(logs_root, local_name)

                    try:
                        if sftp and not os.path.exists(local_path):
                            sftp.get(remote_path, local_path)
                        row[local_key] = local_path
                    except Exception:
                        row[local_key] = ""

                # Fallback persistence: if remote-path download failed, store available payload logs locally.
                fallback_gen_path = str(row.get("gen_log_local_path", "") or "")
                if not fallback_gen_path:
                    gen_content = str(row.get("gen_log", "") or "").strip()
                    if gen_content:
                        fallback_gen_path = os.path.join(logs_root, f"{idx + 1:02d}_general_payload.log")
                        try:
                            with open(fallback_gen_path, 'w', encoding='utf-8', errors='ignore') as f:
                                f.write(gen_content)
                            row["gen_log_local_path"] = fallback_gen_path
                        except Exception:
                            row["gen_log_local_path"] = ""

                fallback_ff_path = str(row.get("ff_log_local_path", "") or "")
                if not fallback_ff_path:
                    ff_content = str(row.get("ff_tail", "") or "").strip()
                    if ff_content:
                        fallback_ff_path = os.path.join(logs_root, f"{idx + 1:02d}_ffmpeg_payload.log")
                        try:
                            with open(fallback_ff_path, 'w', encoding='utf-8', errors='ignore') as f:
                                f.write(ff_content)
                            row["ff_log_local_path"] = fallback_ff_path
                        except Exception:
                            row["ff_log_local_path"] = ""
        finally:
            try:
                if sftp:
                    sftp.close()
            except Exception:
                pass

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
                            if results and isinstance(results, list):
                                # Persist logs to disk for rows already completed.
                                if any(str(r.get("db_status", "")).upper() == "COMPLETED" for r in results):
                                    self._download_logs_for_completed_jobs(client, results)

                                self.sync_use_case.execute(self.item_id, json.dumps(results))

                                # Stop polling once every row is completed.
                                if all(str(r.get("db_status", "")).upper() == "COMPLETED" for r in results):
                                    self._is_running = False
                                    break
                            else:
                                self.sync_use_case.execute(self.item_id, json_str)
                        except json.JSONDecodeError:
                            self.sync_use_case.execute(self.item_id, json_str)
                    elif raw_output:
                        self.sync_use_case.execute(self.item_id, raw_output)
                except json.JSONDecodeError:
                    pass

                if self._run_once:
                    self._is_running = False
                    break
                    
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