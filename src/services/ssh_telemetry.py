import os
import re
import json
import paramiko
import time
from PyQt6.QtCore import QThread, pyqtSignal


class SSHTelemetryClient(QThread):
    telemetry_data = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, target_title: str, parent=None) -> None:
        super().__init__(parent)
        self.target_title = target_title
        self.safe_title = re.sub(r'[\\/*?:"<>| \']', "_", self.target_title)
        self._is_running = True

    def stop(self):
        """Allows the application to gracefully kill the thread."""
        self._is_running = False
        self.wait()

    def run(self) -> None:
        host = os.getenv("SSH_HOST", "192.168.10.109")
        user = os.getenv("SSH_USER", "root")
        password = os.getenv("SSH_PASS", "QAZxsw!234")
        remote_app_dir = os.getenv("REMOTE_APP_DIR", "/opt/movie-conversion")

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=host, username=user, password=password, timeout=5.0)

            remote_script = f"""
import sqlite3, json, os, glob, re, sys

target_title = {repr(self.target_title)}
remote_app_dir = {repr(remote_app_dir)}

results = []
try:
    db_path = f'{{remote_app_dir}}/conversion_data.db'
    conn = sqlite3.connect(f'file:{{db_path}}?mode=ro', uri=True, timeout=10.0)
    cur = conn.cursor()
    
    cur.execute("SELECT status, COALESCE(stage_results, '{{}}'), path FROM jobs WHERE path LIKE ? ORDER BY id DESC", ('%' + target_title + '%',))
    rows = cur.fetchall()
    
    if not rows:
        words = [w for w in re.split(r'\\W+', target_title) if len(w) > 2]
        if words:
            query = "SELECT status, COALESCE(stage_results, '{{}}'), path FROM jobs WHERE " + " AND ".join(["path LIKE ?"] * len(words)) + " ORDER BY id DESC"
            cur.execute(query, ['%' + w + '%' for w in words])
            rows = cur.fetchall()
            
    unique_jobs = {{}}
    for db_status, stage_flags, db_path in rows:
        if db_path not in unique_jobs:
            unique_jobs[db_path] = (db_status, stage_flags)
        
    for db_path, (db_status, stage_flags) in unique_jobs.items():
        try:
            flags = json.loads(stage_flags)
        except:
            flags = {{}}

        linear_path = [
            "p1-input", "p1-queue", "p2-dequeue", "p2-pass", "p3-router",
            "p5-check", "p5-pass", "p6-discovery", "p7-heuristics",
            "p7-audio", "p7-tiers", "p7-outcome", "p8-relocate",
            "p8-cleanup", "p8-complete"
        ]
        
        max_idx = -1
        for i, node in enumerate(linear_path):
            if node in flags: max_idx = i
            
        if max_idx >= 0:
            for i in range(max_idx):
                if linear_path[i] not in flags:
                    flags[linear_path[i]] = True

        if db_status.upper() == "COMPLETED":
            for c in linear_path:
                if c not in flags:
                    flags[c] = True
            
            if not any(k in flags for k in ["p3-movie", "p3-tv"]):
                if "tv" in db_path.lower() or "season" in db_path.lower() or re.search(r's\\d{{2}}e\\d{{2}}', db_path.lower()):
                    flags["p3-tv"] = True; flags["p4-tv"] = True; flags["p8-tv"] = True
                else:
                    flags["p3-movie"] = True; flags["p4-movie"] = True; flags["p8-movie"] = True
                    
        words = [w.lower() for w in re.split(r'\\W+', db_path) if len(w) > 3 and not w.isdigit()]
        ignore = ['action', 'comedy', 'movies', 'scratch', 'data', 'dvdrip', 'xvid', 'x264', '1080p', '720p', 'web', 'dl', 'aac2', 'h264', 'mkv', 'avi', 'mp4']
        keywords = [w for w in words if w not in ignore]
        
        gen_log_content = "Pending..."
        sub_status = "Pending"
        ff_tail = "Pending..."
        ff_prog = 0
        
        logs = sorted(glob.glob("/var/log/conversion/general/*.log"), key=os.path.getmtime, reverse=True)
        matched_gen = None
        if keywords:
            for log in logs:
                if any(k in os.path.basename(log).lower() for k in keywords):
                    matched_gen = log
                    break
        if not matched_gen and logs:
            matched_gen = logs[0]
            
        if matched_gen:
            try:
                with open(matched_gen, 'r', encoding='utf-8', errors='ignore') as f:
                    gen_log_content = f.read().strip()
                if "Extracting subtitle" in gen_log_content: sub_status = "In Progress"
                if "Extracted" in gen_log_content or "Converted" in gen_log_content: sub_status = "Completed"
                if "No subtitle" in gen_log_content or "Continuing with video only" in gen_log_content: sub_status = "None"
            except: pass
            
        ff_logs = sorted(glob.glob("/var/log/conversion/ffmpeg/*.log"), key=os.path.getmtime, reverse=True)
        matched_ff = None
        if keywords:
            for log in ff_logs:
                if any(k in os.path.basename(log).lower() for k in keywords):
                    matched_ff = log
                    break
        if not matched_ff and ff_logs:
            matched_ff = ff_logs[0]

        if matched_ff:
            try:
                with open(matched_ff, 'r', encoding='utf-8', errors='ignore') as f:
                    ff_lines = f.readlines()
                    ff_tail = "".join(ff_lines[-50:]).strip()
                    ff_full = "".join(ff_lines)
                duration_match = re.search(r"Duration: (\\d{{2}}):(\\d{{2}}):(\\d{{2}})", ff_full)
                if duration_match:
                    dh, dm, ds = duration_match.groups()
                    total_s = int(dh)*3600 + int(dm)*60 + int(ds)
                    time_matches = re.findall(r"time=(\\d{{2}}):(\\d{{2}}):(\\d{{2}})", ff_full)
                    if time_matches and total_s > 0:
                        ch, cm, cs = time_matches[-1]
                        curr_s = int(ch)*3600 + int(cm)*60 + int(cs)
                        ff_prog = min(int((curr_s / total_s) * 100), 100)
                        
                        flags["p7-heuristics"] = True
                        flags["p7-audio"] = True
                        flags["p7-t2"] = True 
            except: pass
            
        results.append({{
            "path": db_path,
            "db_status": db_status,
            "stage_results": json.dumps(flags),
            "sub_status": sub_status,
            "gen_log": gen_log_content,
            "ff_tail": ff_tail,
            "prog": ff_prog
        }})

except Exception as e:
    pass

print(json.dumps(results))
"""
            import base64
            b64_script = base64.b64encode(remote_script.encode('utf-8')).decode('utf-8')
            
            # Robust, distro-independent execution bypassing echo/pipe complexities
            db_cmd = f"python3 -c \"import base64; exec(base64.b64decode('{b64_script}').decode('utf-8'))\""

            while self._is_running:
                stdin, stdout, stderr = client.exec_command(db_cmd)
                raw_output = stdout.read().decode('utf-8').strip()
                
                # CRITICAL: Close streams explicitly to prevent SSH Channel leaks (MaxSessions exhaustion)
                stdin.close()
                stdout.close()
                stderr.close()
                
                try:
                    match = re.search(r'\[.*\]', raw_output, re.DOTALL)
                    if match:
                        json_str = match.group()
                        self.telemetry_data.emit(json_str)
                    elif raw_output:
                        self.telemetry_data.emit(raw_output)
                except json.JSONDecodeError:
                    pass
                    
                # Iterative sleep ensures instantaneous shutdown when self._is_running flips
                for _ in range(30):
                    if not self._is_running:
                        break
                    time.sleep(0.1)

            client.close()
        except Exception as e:
            self.error.emit(f"SSH Telemetry Failed: {str(e)}")