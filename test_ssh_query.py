import sqlite3, json, os, glob, re, base64, paramiko

target_title = 'Dear Basketball (2017)'
host = '192.168.10.109'
user = 'root'
password = 'QAZxsw!234'
remote_app_dir = '/scripts/updated-movie-conversion'

remote_script = f'''
import sqlite3, json, os, glob, re

target_title = """{target_title}"""
remote_app_dir = """{remote_app_dir}"""

results = []
try:
    conn = sqlite3.connect(f"{{remote_app_dir}}/conversion_data.db")
    cur = conn.cursor()
    cur.execute("SELECT status, COALESCE(stage_results, '{{}}'), path FROM jobs WHERE path LIKE ? ORDER BY path ASC", ('%' + target_title + '%',))
    rows = cur.fetchall()
    
    if not rows:
        words = [w for w in re.split(r"\\W+", target_title) if len(w) > 2]
        if words:
            query = "SELECT status, COALESCE(stage_results, '{{}}'), path FROM jobs WHERE " + " AND ".join(["path LIKE ?"] * len(words)) + " ORDER BY path ASC"
            cur.execute(query, ['%' + w + '%' for w in words])
            rows = cur.fetchall()
            
    print(json.dumps(rows))
except Exception as e:
    print(str(e))
'''
try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=user, password=password, timeout=5.0)

    b64_script = base64.b64encode(remote_script.encode('utf-8')).decode('utf-8')
    db_cmd = f"echo '{b64_script}' | base64 -d | python3"
    
    stdin, stdout, stderr = client.exec_command(db_cmd)
    print("OUTPUT:", stdout.read().decode('utf-8').strip())
    print("ERR:", stderr.read().decode('utf-8').strip())
except Exception as e:
    print(e)
