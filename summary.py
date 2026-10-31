import posixpath
from collections import Counter
from datetime import datetime
import db
from lures import FAKE_FILES

SEV_ORDER = ["info", "low", "medium", "high", "critical"]
LURE_NAMES = sorted({posixpath.basename(p) for p in FAKE_FILES})


def build_summary(session_id):
    db.init_db()
    rows = db.fetch_logs(session_id=session_id, limit=1000)
    if not rows:
        return None
    rows.sort(key=lambda r: r["id"])
    start = datetime.fromisoformat(rows[0]["timestamp"])
    end = datetime.fromisoformat(rows[-1]["timestamp"])
    categories = Counter(r["category"] for r in rows)
    top = max(rows, key=lambda r: SEV_ORDER.index(r["severity"]))["severity"]
    lures = sorted(
        {name for r in rows for name in LURE_NAMES if name in r["command"]}
    )
    alerts = [r["command"] for r in rows if r["severity"] in ("high", "critical")]
    return {
        "session_id": session_id,
        "commands": len(rows),
        "duration_seconds": int((end - start).total_seconds()),
        "highest_severity": top,
        "categories": dict(categories),
        "lure_files_touched": lures,
        "high_critical_commands": alerts,
    }


def format_summary(s):
    cats = ", ".join(f"{k}={v}" for k, v in sorted(s["categories"].items()))
    lines = [
        "=== PhantomNet session summary (admin only) ===",
        f"Session          : {s['session_id']}",
        f"Commands         : {s['commands']} in {s['duration_seconds']} sec",
        f"Highest severity : {s['highest_severity']}",
        f"Categories       : {cats}",
        f"Lure files read  : {', '.join(s['lure_files_touched']) or 'none'}",
    ]
    if s["high_critical_commands"]:
        lines.append("High/critical commands:")
        lines += [f"  - {c}" for c in s["high_critical_commands"]]
    return "\n".join(lines)