import os
import re
import time
import posixpath
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-3.1-flash-lite"

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

chat = client.chats.create(
    model=MODEL,
    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
)

VALID_DIRS = {
    "/", "/root", "/home", "/etc", "/var", "/var/lib", "/var/log", "/var/tmp",
    "/var/lib/postgresql", "/var/lib/postgresql/14", "/var/lib/postgresql/14/main",
    "/var/log/postgresql", "/etc/postgresql", "/etc/postgresql/14",
    "/etc/postgresql/14/main", "/tmp", "/usr", "/usr/bin", "/usr/local",
    "/usr/share", "/opt", "/bin", "/sbin", "/boot", "/dev", "/proc", "/sys",
    "/run", "/srv", "/mnt", "/media", "/lib",
}

PROMPT_RE = re.compile(r"^\s*\w+@[\w-]+:.*[#$]\s*$")


def clean(text):
    lines = []
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("```"):
            continue
        if PROMPT_RE.match(line):
            continue
        if s.startswith("$ "):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def ask(cwd, cmd):
    msg = f"[current directory: {cwd}]\n$ {cmd}"
    for attempt in range(6):
        try:
            return chat.send_message(msg).text or ""
        except Exception:
            print(f"[server busy, retry {attempt + 1}/6]")
            time.sleep(4)
    return "bash: fork: retry: Resource temporarily unavailable"


def do_cd(cmd, cwd):
    parts = cmd.split(maxsplit=1)
    raw = parts[1].strip() if len(parts) > 1 else "~"
    target = raw
    if target == "-":
        return cwd, ""
    if target == "~" or target.startswith("~/"):
        target = "/root" + target[1:]
    if not target.startswith("/"):
        target = posixpath.join(cwd, target)
    target = posixpath.normpath(target)
    if target in VALID_DIRS:
        return target, ""
    return cwd, f"bash: cd: {raw}: No such file or directory"


cwd = "/root"
print("Ubuntu 22.04.3 LTS prod-db-01 tty1\n")
while True:
    try:
        shown = "~" if cwd == "/root" else cwd
        cmd = input(f"root@prod-db-01:{shown}# ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        break
    if cmd in ("exit", "logout"):
        break
    if not cmd:
        continue
    if cmd.split()[0] == "cd":
        cwd, err = do_cd(cmd, cwd)
        if err:
            print(err)
        continue
    if cmd == "pwd":
        print(cwd)
        continue
    out = clean(ask(cwd, cmd))
    if out:
        print(out)