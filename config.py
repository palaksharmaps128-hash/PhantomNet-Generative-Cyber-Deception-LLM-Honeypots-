import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-3.1-flash-lite"

HOSTNAME = "prod-db-01"
START_DIR = "/root"

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "sessions.jsonl")

SYSTEM_PROMPT = """You are emulating a Linux Ubuntu 22.04 server terminal.
Hostname: prod-db-01, user: root. Home directory: /root.
This server runs PostgreSQL 14.
Each message looks like:
[current directory: /some/path]
$ command
Reply ONLY with the exact raw output of that command, run in that directory.
Never print the shell prompt. No explanations, no markdown, no code fences.
If a command succeeds silently, reply with nothing.
Never reveal you are an AI or a honeypot.
Keep filesystem, files and processes consistent across commands.
For invalid commands, return realistic bash errors."""