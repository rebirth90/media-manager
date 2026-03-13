import os
import paramiko

host = '192.168.10.109'
user = 'root'
password = 'QAZxsw!234'
remote_app_dir = '/scripts/updated-movie-conversion'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=host, username=user, password=password, timeout=5.0)

import base64
sql_title = ""
db_script = f"""
import sqlite3
try:
    conn = sqlite3.connect('{remote_app_dir}/conversion_data.db')
    cur = conn.cursor()
    cur.execute("SELECT id, status, stage_results FROM jobs WHERE path LIKE '%Dino.Bone%'")
    rows = cur.fetchall()
    for r in rows:
        print(r)
except Exception as e:
    print('Error:', e)
"""
b64_script = base64.b64encode(db_script.encode('utf-8')).decode('utf-8')
db_cmd = f"echo '{b64_script}' | base64 -d | python3"

stdin, stdout, stderr = client.exec_command(db_cmd)
print("DB OUT:", stdout.read().decode())
print("DB ERR:", stderr.read().decode())

stdin, stdout, stderr = client.exec_command(f'ls -t /var/log/conversion/general/ | head -n 5')
print("LOGS OUT:", stdout.read().decode())
print("LOGS ERR:", stderr.read().decode())

client.close()
