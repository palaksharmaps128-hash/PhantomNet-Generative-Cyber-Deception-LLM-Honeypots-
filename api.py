import re
import uuid
import threading
from flask import Flask, request, jsonify
from config import START_DIR, HOSTNAME
from llm_engine import ask, clean, new_chat
from shell import do_cd
from logger import log_event
from threat_classifier import classify, SEVERITY
import db

app = Flask(__name__)

SESSIONS = {}
SESSIONS_LOCK = threading.Lock()
SID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
MAX_CMD_LEN = 500


def get_session(sid):
    with SESSIONS_LOCK:
        if not sid:
            sid = uuid.uuid4().hex[:8]
        if sid not in SESSIONS:
            SESSIONS[sid] = {
                "cwd": START_DIR,
                "chat": new_chat(),
                "lock": threading.Lock(),
            }
        return sid, SESSIONS[sid]


def prompt_for(cwd):
    shown = "~" if cwd == START_DIR else cwd
    return f"root@{HOSTNAME}:{shown}# "


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "PhantomNet"})


@app.post("/api/command")
def command():
    data = request.get_json(silent=True) or {}
    cmd = str(data.get("command", "")).strip()
    sid = data.get("session_id")

    if not cmd:
        return jsonify({"error": "command is required"}), 400
    if len(cmd) > MAX_CMD_LEN:
        return jsonify({"error": f"command too long (max {MAX_CMD_LEN})"}), 400
    if sid is not None and not SID_RE.match(str(sid)):
        return jsonify({"error": "invalid session_id"}), 400

    sid, session = get_session(sid)
    with session["lock"]:
        cwd = session["cwd"]
        first = cmd.split()[0]

        if first in ("exit", "logout"):
            log_event(cwd, cmd, "", "python", session_id=sid)
            with SESSIONS_LOCK:
                SESSIONS.pop(sid, None)
            output, source = "logout", "python"
        elif first == "cd":
            new_cwd, err = do_cd(cmd, cwd)
            session["cwd"] = new_cwd
            log_event(cwd, cmd, err, "python", session_id=sid)
            output, source = err, "python"
        elif cmd == "pwd":
            log_event(cwd, cmd, cwd, "python", session_id=sid)
            output, source = cwd, "python"
        else:
            raw, ok = ask(cwd, cmd, chat_obj=session["chat"])
            output = clean(raw)
            source = "llm" if ok else "llm-error"
            log_event(cwd, cmd, output, source, session_id=sid)

    category = classify(cmd)
    return jsonify(
        {
            "session_id": sid,
            "command": cmd,
            "output": output,
            "cwd": session["cwd"],
            "prompt": prompt_for(session["cwd"]),
            "source": source,
            "category": category,
            "severity": SEVERITY[category],
        }
    )


@app.get("/api/logs")
def logs():
    sid = request.args.get("session_id")
    limit = request.args.get("limit", 100)
    try:
        limit = int(limit)
    except ValueError:
        return jsonify({"error": "limit must be a number"}), 400
    return jsonify(db.fetch_logs(session_id=sid, limit=limit))


@app.get("/api/stats")
def stats():
    return jsonify(db.fetch_stats())


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)