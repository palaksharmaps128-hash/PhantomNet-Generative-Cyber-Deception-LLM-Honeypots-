import os
import sqlite3
from contextlib import closing
from config import LOG_DIR

os.makedirs(LOG_DIR, exist_ok=True)
DB_FILE = os.path.join(LOG_DIR, "phantomnet.db")


def _conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(_conn()) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TEXT,
                cwd TEXT,
                command TEXT,
                response TEXT,
                source TEXT,
                category TEXT,
                severity TEXT
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON events(session_id)")
        conn.commit()


def insert_event(entry):
    with closing(_conn()) as conn:
        conn.execute(
            """INSERT INTO events
               (session_id, timestamp, cwd, command, response, source, category, severity)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry["session_id"],
                entry["timestamp"],
                entry["cwd"],
                entry["command"],
                entry["response"],
                entry["source"],
                entry["category"],
                entry["severity"],
            ),
        )
        conn.commit()


def fetch_logs(session_id=None, limit=100):
    limit = max(1, min(int(limit), 1000))
    query = "SELECT * FROM events"
    params = []
    if session_id:
        query += " WHERE session_id = ?"
        params.append(session_id)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with closing(_conn()) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def fetch_stats():
    with closing(_conn()) as conn:
        total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        sessions = conn.execute(
            "SELECT COUNT(DISTINCT session_id) FROM events"
        ).fetchone()[0]
        by_category = {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT category, COUNT(*) FROM events GROUP BY category"
            )
        }
        by_severity = {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT severity, COUNT(*) FROM events GROUP BY severity"
            )
        }
        by_source = {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT source, COUNT(*) FROM events GROUP BY source"
            )
        }
    alerts = by_severity.get("high", 0) + by_severity.get("critical", 0)
    return {
        "total_commands": total,
        "sessions": sessions,
        "high_critical_alerts": alerts,
        "by_category": by_category,
        "by_severity": by_severity,
        "by_source": by_source,
    }