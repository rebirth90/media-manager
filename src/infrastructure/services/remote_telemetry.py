# remote_telemetry.py
import sqlite3
import json
import os
import glob
import re
import argparse

def main():
    parser = argparse.ArgumentParser(description="Fetch telemetry data from SQLite and logs.")
    parser.add_argument('--target', required=True, help="Target title")
    parser.add_argument('--season', default="", help="Explicit season")
    parser.add_argument('--dir', required=True, help="Remote app directory")
    args = parser.parse_args()

    results = []
    try:
        db_path = f"{args.dir}/conversion_data.db"
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10.0)
        cur = conn.cursor()
        
        # 1. Base words from the torrent name
        clean_target = args.target.replace('_', ' ').replace('.', ' ')
        words = [w for w in re.split(r'\W+', clean_target) if len(w) > 2]
        words = [w for w in words if w.lower() not in ('season', 'episode')]
        words = [w for w in words if not (w.isdigit() and len(w) == 4)]
        
        if not words:
            words = [clean_target]
            
        # Fetch broadly first
        query = "SELECT status, COALESCE(stage_results, '{}'), path FROM jobs WHERE " + " AND ".join(["path LIKE ?"] * len(words)) + " ORDER BY id DESC"
        cur.execute(query, ['%' + w + '%' for w in words])
        rows = cur.fetchall()
        
        # 2. Extract expected Season and Episode
        s_num = None
        e_num = None
        
        if args.season:
            ex_s_match = re.search(r'\d+', str(args.season))
            if ex_s_match:
                s_num = int(ex_s_match.group())
            
        se_match = re.search(r'(?i)(?:season\s*0*(\d+)|s0*(\d+))(?:.*?(?:episode\s*0*(\d+)|e0*(\d+)))?', clean_target)
        if se_match:
            if s_num is None:
                s_num = int(se_match.group(1) or se_match.group(2))
            if se_match.group(3) or se_match.group(4):
                e_num = int(se_match.group(3) or se_match.group(4))
                
        filtered_rows = []
        
        # 3. Apply strict Python Filtering
        if s_num is not None:
            for r in rows:
                path_str = r[2].lower()
                path_se = re.search(r'(?i)(?:season\s*0*(\d+)|s0*(\d+))(?:.*?(?:episode\s*0*(\d+)|e0*(\d+)))?', path_str)
                
                if path_se:
                    p_s = int(path_se.group(1) or path_se.group(2))
                    p_e = None
                    if path_se.group(3) or path_se.group(4):
                        p_e = int(path_se.group(3) or path_se.group(4))
                        
                    if p_s == s_num:
                        if e_num is not None:
                            if p_e == e_num:
                                filtered_rows.append(r)
                        else:
                            filtered_rows.append(r)
        else:
            digits = [w for w in re.split(r'\W+', clean_target) if w.isdigit() and len(w) <= 2]
            if digits:
                for r in rows:
                    path_nums = [n for n in re.split(r'\W+', r[2]) if n.isdigit()]
                    if all((d in path_nums or f"{int(d):02d}" in path_nums) for d in digits):
                        filtered_rows.append(r)
            else:
                filtered_rows = rows
                
        rows = filtered_rows
        
        unique_jobs = {}
        for db_status, stage_flags, db_path in rows:
            if db_path not in unique_jobs:
                unique_jobs[db_path] = (db_status, stage_flags)
            
        for db_path, (db_status, stage_flags) in unique_jobs.items():
            try:
                flags = json.loads(stage_flags)
            except:
                flags = {}

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

            # Always infer movie vs tv if we have passed the router
            if max_idx >= linear_path.index("p3-router"):
                if not any(k in flags for k in ["p3-movie", "p3-tv"]):
                    if "tv" in db_path.lower() or "season" in db_path.lower() or re.search(r's\d{2}e\d{2}', db_path.lower()):
                        flags["p3-tv"] = 'pass'; flags["p4-tv"] = 'pass'
                        if db_status.upper() == "COMPLETED": flags["p8-tv"] = 'pass'
                    else:
                        flags["p3-movie"] = 'pass'; flags["p4-movie"] = 'pass'
                        if db_status.upper() == "COMPLETED": flags["p8-movie"] = 'pass'

            if db_status.upper() == "COMPLETED":
                for c in linear_path:
                    if c not in flags:
                        flags[c] = 'pass'

            # Build stable keyword list for log matching.
            words = [w.lower() for w in re.split(r'\W+', db_path) if len(w) > 3 and not w.isdigit()]
            ignore = [
                'action', 'comedy', 'movies', 'scratch', 'data', 'dvdrip',
                'xvid', 'x264', '1080p', '720p', 'web', 'dl', 'aac2', 'h264',
                'mkv', 'avi', 'mp4', 'bluray', 'brrip', 'webrip', 'x265',
                'hevc', 'hdr', 'proper', 'repack'
            ]
            keywords = [w for w in words if w not in ignore]

            # Fallback to meaningful target words if path is too generic.
            if not keywords:
                target_words = [w.lower() for w in re.split(r'\W+', clean_target) if len(w) > 2 and not w.isdigit()]
                keywords = [w for w in target_words if w not in ignore]

            gen_log_content = "Pending..."
            sub_status = "Pending"
            ff_tail = "Pending..."
            ff_prog = 0
            
            logs = sorted(glob.glob("/var/log/conversion/general/*.log"), key=os.path.getmtime, reverse=True)
            matched_gen = next((log for log in logs if any(k in os.path.basename(log).lower() for k in keywords)), None)
            
            if matched_gen:
                try:
                    with open(matched_gen, 'r', encoding='utf-8', errors='ignore') as f:
                        gen_log_content = f.read().strip()
                    if "Extracting subtitle" in gen_log_content: sub_status = "In Progress"
                    if "Extracted" in gen_log_content or "Converted" in gen_log_content: sub_status = "Completed"
                    if "No subtitle" in gen_log_content or "Continuing with video only" in gen_log_content: sub_status = "None"
                except: pass
                
            ff_logs = sorted(glob.glob("/var/log/conversion/ffmpeg/*.log"), key=os.path.getmtime, reverse=True)
            matched_ff = next((log for log in ff_logs if any(k in os.path.basename(log).lower() for k in keywords)), None)

            if matched_ff:
                try:
                    with open(matched_ff, 'r', encoding='utf-8', errors='ignore') as f:
                        ff_lines = f.readlines()
                        ff_tail = "".join(ff_lines[-50:]).strip()
                        ff_full = "".join(ff_lines)
                    duration_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})", ff_full)
                    if duration_match:
                        dh, dm, ds = duration_match.groups()
                        total_s = int(dh)*3600 + int(dm)*60 + int(ds)
                        time_matches = re.findall(r"time=(\d{2}):(\d{2}):(\d{2})", ff_full)
                        if time_matches and total_s > 0:
                            ch, cm, cs = time_matches[-1]
                            curr_s = int(ch)*3600 + int(cm)*60 + int(cs)
                            ff_prog = min(int((curr_s / total_s) * 100), 100)
                            
                            flags["p7-heuristics"] = 'pass'
                            flags["p7-audio"] = 'pass'
                            flags["p7-t2"] = 'pass' 
                except: pass
                
            results.append({
                "path": db_path,
                "db_status": db_status,
                "stage_results": json.dumps(flags),
                "sub_status": sub_status,
                "gen_log": gen_log_content,
                "ff_tail": ff_tail,
                "prog": ff_prog
            })

    except Exception:
        pass

    print(json.dumps(results))

if __name__ == "__main__":
    main()