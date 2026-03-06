import os
import re
import json
import paramiko
from PyQt6.QtCore import QThread, pyqtSignal


class SSHTelemetryClient(QThread):
    # Emits a JSON encoded list of dictionaries containing episode conversion statuses
    telemetry_data = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, target_title: str, parent=None) -> None:
        super().__init__(parent)
        self.target_title = target_title
        self.safe_title = re.sub(r'[\\/*?:"<>| \']', "_", self.target_title)

    def run(self) -> None:
        host = os.getenv("SSH_HOST", "192.168.10.109")
        user = os.getenv("SSH_USER", "root")
        password = os.getenv("SSH_PASS", "QAZxsw!234")
        remote_app_dir = os.getenv("REMOTE_APP_DIR", "/opt/movie-conversion")

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=host, username=user, password=password, timeout=5.0)

            # Python script to run remotely via base64 encoded payload
            remote_script = f"""
import sqlite3, json, os, glob, re

target_title = '''{self.target_title}'''
remote_app_dir = '''{remote_app_dir}'''

results = []
try:
    conn = sqlite3.connect(f'{{remote_app_dir}}/conversion_data.db')
    cur = conn.cursor()
    cur.execute("SELECT status, COALESCE(stage_results, '{{}}'), path FROM jobs WHERE path LIKE ? ORDER BY path ASC", ('%' + target_title + '%',))
    rows = cur.fetchall()
    
    if not rows:
        words = [w for w in re.split(r'\\W+', target_title) if len(w) > 2]
        if words:
            query = "SELECT status, COALESCE(stage_results, '{{}}'), path FROM jobs WHERE " + " AND ".join(["path LIKE ?"] * len(words)) + " ORDER BY path ASC"
            cur.execute(query, ['%' + w + '%' for w in words])
            rows = cur.fetchall()
            
    unique_jobs = {{}}
    for db_status, stage_flags, db_path in rows:
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
                    flags[linear_path[i]] = "skip"

        if db_status.upper() == "COMPLETED":
            all_cards = linear_path + ["p3-movie", "p4-movie", "p8-movie", "p3-tv", "p4-tv"]
            for c in all_cards:
                if c not in flags:
                    flags[c] = "pass"
                    
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

if not results:
    results.append({{
        "path": target_title,
        "db_status": "NOT STARTED",
        "stage_results": "{{}}",
        "sub_status": "Pending",
        "gen_log": "",
        "ff_tail": "",
        "prog": 0
    }})

print(json.dumps(results))
"""
            import base64
            import time
            b64_script = base64.b64encode(remote_script.encode('utf-8')).decode('utf-8')
            db_cmd = f"echo '{b64_script}' | base64 -d | python3"

            while True:
                stdin, stdout, stderr = client.exec_command(db_cmd)
                raw_output = stdout.read().decode('utf-8').strip()
                err_output = stderr.read().decode('utf-8').strip()
                
                if err_output:
                    print(f"[{self.target_title} Telemetry STDERR]: {err_output}")
                
                try:
                    # Find the JSON array in the output (in case of server banners/warnings)
                    match = re.search(r'\[.*\]', raw_output, re.DOTALL)
                    if match:
                        json_str = match.group()
                        data = json.loads(json_str)
                        self.telemetry_data.emit(json_str)
                    else:
                        # Fallback for empty/malformed
                        data = json.loads(raw_output)
                        self.telemetry_data.emit(raw_output)
                    
                    if isinstance(data, list):
                        
                        # Stop polling if all episodes are settled
                        all_finished = True
                        for ep in data:
                            state = ep.get("db_status", "NOT STARTED").upper()
                            if state not in ["COMPLETED", "FAILED", "REJECTED"]:
                                all_finished = False
                                break
                                
                        if all_finished and data:
                            break
                    else:
                        self.error.emit(f"Expected JSON array. Got: {raw_output}")
                        break
                except json.JSONDecodeError:
                    print(f"[SSH Telemetry - {self.target_title}] JSON Parse Error. Raw: {raw_output}")
                    self.error.emit(f"JSON Parse Error for {self.target_title}")
                    # Continue instead of break to allow temporary server hiccups
                    time.sleep(5)
                    continue
                    
                time.sleep(3)

            client.close()
        except Exception as e:
            self.error.emit(f"SSH Telemetry Failed: {str(e)}")
