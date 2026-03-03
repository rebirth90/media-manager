import os
import re
import json
import paramiko
from PyQt6.QtCore import QThread, pyqtSignal


class SSHTelemetryClient(QThread):
    # 6th arg: stage_results JSON string e.g. '{"p1-input":"pass","p6-vobsub":"fail",...}'
    telemetry_data = pyqtSignal(str, str, int, str, str, str)
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

db_status = "NOT STARTED"
stage_flags = "{{}}"
db_path = target_title

try:
    conn = sqlite3.connect(f'{{remote_app_dir}}/conversion_data.db')
    cur = conn.cursor()
    cur.execute("SELECT status, COALESCE(stage_results, '{{}}'), path FROM jobs WHERE path LIKE ? ORDER BY id DESC LIMIT 1", ('%' + target_title + '%',))
    row = cur.fetchone()
    if not row:
        words = [w for w in re.split(r'\\W+', target_title) if len(w) > 2]
        if words:
            query = "SELECT status, COALESCE(stage_results, '{{}}'), path FROM jobs WHERE " + " AND ".join(["path LIKE ?"] * len(words)) + " ORDER BY id DESC LIMIT 1"
            cur.execute(query, ['%' + w + '%' for w in words])
            row = cur.fetchone()
            
    if row:
        db_status, stage_flags, db_path = row
except Exception:
    pass

try:
    flags = json.loads(stage_flags)
except:
    flags = {{}}

# All distinct ordered milestones
linear_path = [
    "p1-input", "p1-queue", "p2-dequeue", "p2-pass", "p3-router",
    "p5-check", "p5-pass", "p6-discovery", "p7-heuristics",
    "p7-audio", "p7-tiers", "p7-outcome", "p8-relocate",
    "p8-cleanup", "p8-complete"
]

# If we have reached a node, all previous linear nodes must be treated as passed/skipped
max_idx = -1
for i, node in enumerate(linear_path):
    if node in flags:
        max_idx = i

if max_idx >= 0:
    for i in range(max_idx):
        if linear_path[i] not in flags:
            flags[linear_path[i]] = "skip"

if db_status.upper() == "COMPLETED":
    all_cards = [
        "p1-input", "p1-queue", "p2-dequeue", "p2-pass", "p3-router",
        "p5-check", "p5-pass", "p6-discovery", "p7-heuristics", 
        "p7-audio", "p7-tiers", "p7-outcome", "p8-relocate", 
        "p8-cleanup", "p8-complete", "p3-movie", "p4-movie", "p8-movie"
    ]
    for c in all_cards:
        if c not in flags:
            flags[c] = "pass"

stage_flags = json.dumps(flags)

words = [w.lower() for w in re.split(r'\\W+', db_path or target_title) if len(w) > 3 and not w.isdigit()]
ignore = ['action', 'comedy', 'movies', 'scratch', 'data', 'dvdrip', 'xvid', 'x264', '1080p', '720p', 'web', 'dl', 'aac2', 'h264', 'mkv', 'avi', 'mp4']
keywords = [w for w in words if w not in ignore]

gen_log_content = "Pending..."
sub_status = "Pending"
ff_tail = "Pending..."
ff_prog = 0

try:
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
        with open(matched_gen, 'r', encoding='utf-8', errors='ignore') as f:
            gen_log_content = f.read().strip()
            
        if "Extracting subtitle" in gen_log_content:
            sub_status = "In Progress"
        if "Extracted" in gen_log_content or "Converted" in gen_log_content:
            sub_status = "Completed"
        if "No subtitle" in gen_log_content or "Continuing with video only" in gen_log_content:
            sub_status = "None"
            
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
        with open(matched_ff, 'r', encoding='utf-8', errors='ignore') as f:
            ff_lines = f.readlines()
            ff_tail = "".join(ff_lines[-50:]).strip()
            ff_full = "".join(ff_lines)
            
        duration_match = re.search(r"Duration: (\d{{2}}):(\d{{2}}):(\d{{2}})", ff_full)
        if duration_match:
            dh, dm, ds = duration_match.groups()
            total_s = int(dh)*3600 + int(dm)*60 + int(ds)
            
            time_matches = re.findall(r"time=(\d{{2}}):(\d{{2}}):(\d{{2}})", ff_full)
            if time_matches and total_s > 0:
                ch, cm, cs = time_matches[-1]
                curr_s = int(ch)*3600 + int(cm)*60 + int(cs)
                ff_prog = min(int((curr_s / total_s) * 100), 100)
except Exception:
    pass

print(json.dumps({{
    "db_status": db_status,
    "stage_results": stage_flags,
    "sub_status": sub_status,
    "gen_log": gen_log_content,
    "ff_tail": ff_tail,
    "prog": ff_prog
}}))
"""
            import base64
            b64_script = base64.b64encode(remote_script.encode('utf-8')).decode('utf-8')
            db_cmd = f"echo '{b64_script}' | base64 -d | python3"

            stdin, stdout, stderr = client.exec_command(db_cmd)
            raw_output = stdout.read().decode('utf-8').strip()
            
            try:
                data = json.loads(raw_output)
                self.telemetry_data.emit(
                    data.get("db_status", "NOT STARTED"),
                    data.get("sub_status", "Pending"),
                    data.get("prog", 0),
                    data.get("gen_log", ""),
                    data.get("ff_tail", ""),
                    data.get("stage_results", "{}")
                )
            except json.JSONDecodeError:
                self.error.emit(f"JSON Parse Error. Raw: {raw_output}")

            client.close()
        except Exception as e:
            self.error.emit(f"SSH Telemetry Failed: {str(e)}")
