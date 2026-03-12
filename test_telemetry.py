
import os
import paramiko
import json
import base64
from dotenv import load_dotenv

def test_telemetry():
    load_dotenv()
    host = os.getenv("SSH_HOST")
    user = os.getenv("SSH_USER")
    password = os.getenv("SSH_PASS")
    target_title = "The Gruffalo (2009)"
    remote_app_dir = os.getenv("REMOTE_APP_DIR")

    print(f"Connecting to {host}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=user, password=password, timeout=5.0)

    remote_script = f"""
import sqlite3, json, os, glob, re

target_title = '''{target_title}'''
remote_app_dir = '''{remote_app_dir}'''

results = []
try:
    conn = sqlite3.connect(f'{{remote_app_dir}}/conversion_data.db')
    cur = conn.cursor()
    cur.execute("SELECT status, COALESCE(stage_results, '{{}}'), path FROM jobs WHERE path LIKE ? ORDER BY path ASC", ('%' + target_title + '%',))
    rows = cur.fetchall()
    
    unique_jobs = {{}}
    for db_status, stage_flags, db_path in rows:
        unique_jobs[db_path] = (db_status, stage_flags)
        
    for db_path, (db_status, stage_flags) in unique_jobs.items():
        results.append({{
            "path": db_path,
            "db_status": db_status,
            "stage_results": stage_flags
        }})
except Exception as e:
    print(f"Error: {{e}}")

if not results:
    results.append({{
        "path": target_title,
        "db_status": "NOT STARTED",
        "stage_results": "{{}}"
    }})

print(json.dumps(results))
"""
    b64_script = base64.b64encode(remote_script.encode('utf-8')).decode('utf-8')
    db_cmd = f"echo '{b64_script}' | base64 -d | python3"

    print("Executing command...")
    stdin, stdout, stderr = client.exec_command(db_cmd)
    raw_output = stdout.read().decode('utf-8').strip()
    err_output = stderr.read().decode('utf-8').strip()

    print(f"STDOUT: {raw_output}")
    print(f"STDERR: {err_output}")
    
    try:
        data = json.loads(raw_output)
        print(f"PARSED DATA: {json.dumps(data, indent=2)}")
    except:
        print("FAILED TO PARSE JSON")

    client.close()

if __name__ == "__main__":
    test_telemetry()
