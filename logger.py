import os
import json
import uuid
from datetime import datetime, timezone
from config import LOG_DIR, LOG_FILE
from threat_classifier import classify, SEVERITY
import db

os.makedirs(LOG_DIR, exist_ok=True)
db.init_db()
SESSION_ID = uuid.uuid4().hex[:8]


def log_event(cwd, cmd, response, source, session_id=None):
    category = classify(cmd)
    entry = {
        "session_id": session_id or SESSION_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cwd": cwd,
        "command": cmd,
        "response": response,
        "source": source,
        "category": category,
        "severity": SEVERITY[category],
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    db.insert_event(entry)
    return entry