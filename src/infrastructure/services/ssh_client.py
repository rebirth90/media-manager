import os
import re
import json
import paramiko
import time
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

    def run(self) -> None:
        host = os.getenv("SSH_HOST")
        user = os.getenv("SSH_USER")
        password = os.getenv("SSH_PASS")
        remote_app_dir = os.getenv("REMOTE_APP_DIR")

        # FIX: Fetch the actual torrent path and explicit season from the DB locally
        search_target = self.target_title
        explicit_season = ""
        try:
            item = self.repo.get_item(self.item_id)
            if item:
                # relative_path holds the raw torrent name (e.g., Reacher.S02) rather than just "Reacher"
                search_target = item.relative_path if getattr(item, 'relative_path', None) else self.target_title
                explicit_season = str(getattr(item, 'season', ''))
        except Exception:
            pass

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if not host or not user or not password:
                return
                
            client.connect(hostname=host, username=user, password=password, timeout=5.0)

            # Reusing the original SQLite remote query script with strict Python filtering
            remote_script = f"""
import sqlite3, json, os, glob, re, sys

target_title = {repr(search_target)}
explicit_season = {repr(explicit_season)}
remote_app_dir = {repr(remote_app_dir)}

results = []
try:
    db_path = f'{{remote_app_dir}}/conversion_data.db'
    conn = sqlite3.connect(f'file:{{db_path}}?mode=ro', uri=True, timeout=10.0)
    cur = conn.cursor()
    
    # 1. Base words from the torrent name (ignoring tiny words, season/episode tags)
    clean_target = target_title.replace('_', ' ').replace('.', ' ')
    words = [w for w in re.split(r'\\W+', clean_target) if len(w) > 2]
    words = [w for w in words if w.lower() not in ('season', 'episode')]
    words = [w for w in words if not (w.isdigit() and len(w) == 4)]
    
    if not words:
        words = [clean_target]
        
    # Fetch broadly first
    query = "SELECT status, COALESCE(stage_results, '{{}}'), path FROM jobs WHERE " + " AND ".join(["path LIKE ?"] * len(words)) + " ORDER BY id DESC"
    cur.execute(query, ['%' + w + '%' for w in words])
    rows = cur.fetchall()
    
    # 2. Extract expected Season and Episode
    s_num = None
    e_num = None
    
    # Prioritize the explicitly chosen season from the UI Dropdown
    if explicit_season:
        ex_s_match = re.search(r'\d+', str(explicit_season))
        if ex_s_match:
            s_num = int(ex_s_match.group())
        
    se_match = re.search(r'(?i)(?:season\\s*0*(\\d+)|s0*(\\d+))(?:.*?(?:episode\\s*0*(\\d+)|e0*(\\d+)))?', clean_target)
    if se_match:
        if s_num is None:
            s_num = int(se_match.group(1) or se_match.group(2))
        if se_match.group(3) or se_match.group(4):
            e_num = int(se_match.group(3) or se_match.group(4))
            
    filtered_rows = []
    
    # 3. Apply strict Python Filtering to lock it to the right season
    if s_num is not None:
        for r in rows:
            path_str = r[2].lower()
            path_se = re.search(r'(?i)(?:season\\s*0*(\\d+)|s0*(\\d+))(?:.*?(?:episode\\s*0*(\\d+)|e0*(\\d+)))?', path_str)
            
            if path_se:
                p_s = int(path_se.group(1) or path_se.group(2))
                p_e = None
                if path_se.group(3) or path_se.group(4):
                    p_e = int(path_se.group(3) or path_se.group(4))
                    
                # The file MUST belong to the requested season to pass
                if p_s == s_num:
                    if e_num is not None:
                        if p_e == e_num:
                            filtered_rows.append(r)
                    else:
                        filtered_rows.append(r)
    else:
        # Non-TV filtering for movie sequels
        digits = [w for w in re.split(r'\\W+', clean_target) if w.isdigit() and len(w) <= 2]
        if digits:
            for r in rows:
                path_nums = [n for n in re.split(r'\\W+', r[2]) if n.isdigit()]
                if all((d in path_nums or f"{{int(d):02d}}" in path_nums) for d in digits):
                    filtered_rows.append(r)
        else:
            filtered_rows = rows
            
    rows = filtered_rows
    
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
                    flags[linear_path[i]] = 'pass'

        if db_status.upper() == "COMPLETED":
            for c in linear_path:
                if c not in flags:
                    flags[c] = 'pass'
            
            if not any(k in flags for k in ["p3-movie", "p3-tv"]):
                if "tv" in db_path.lower() or "season" in db_path.lower() or re.search(r's\\d{{2}}e\\d{{2}}', db_path.lower()):
                    flags["p3-tv"] = 'pass'; flags["p4-tv"] = 'pass'; flags["p8-tv"] = 'pass'
                else:
                    flags["p3-movie"] = 'pass'; flags["p4-movie"] = 'pass'; flags["p8-movie"] = 'pass'
                    
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
                        
                        flags["p7-heuristics"] = 'pass'
                        flags["p7-audio"] = 'pass'
                        flags["p7-t2"] = 'pass' 
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
            db_cmd = f"echo {b64_script} | base64 -d | python3"

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
                        self.sync_use_case.execute(self.item_id, json_str)
                    elif raw_output:
                        self.sync_use_case.execute(self.item_id, raw_output)
                except json.JSONDecodeError:
                    pass
                    
                for _ in range(30):
                    if not self._is_running:
                        break
                    time.sleep(0.1)

            client.close()
        except:
            pass
