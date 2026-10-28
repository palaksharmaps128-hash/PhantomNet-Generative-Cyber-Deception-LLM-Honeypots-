import os
import json
import uuid
from datetime import datetime, timezone
from config import LOG_DIR, LOG_FILE

os.makedirs(LOG_DIR, exist_ok=True)
SESSION_ID = uuid.uuid4().hex[:8]


def log_event(cwd, cmd, response, source):
    entry = {
        "session_id": SESSION_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cwd": cwd,
        "command": cmd,
        "response": response,
        "source": source,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")