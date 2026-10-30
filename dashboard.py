import time
import requests
import pandas as pd
import streamlit as st

API_URL = "http://127.0.0.1:5000"
HOSTNAME = "prod-db-01"

st.set_page_config(page_title="PhantomNet Dashboard", layout="wide")
st.title("PhantomNet: Attacker Activity Dashboard")


def api_get(path, params=None):
    r = requests.get(f"{API_URL}{path}", params=params, timeout=5)
    r.raise_for_status()
    return r.json()


col_a, col_b = st.columns([1, 5])
col_a.button("Refresh")
auto = col_b.checkbox("Auto-refresh (5 sec)")

try:
    stats = api_get("/api/stats")
    logs = api_get("/api/logs", {"limit": 1000})
except requests.RequestException:
    st.error(
        "Could not connect to the API. Start it in a new terminal with "
        "`python api.py`, then click Refresh."
    )
    st.stop()

if not logs:
    st.info("No logs yet. Send some commands to the honeypot.")
    st.stop()

df = pd.DataFrame(logs)
df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
try:
    df["time"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
except Exception:
    df["time"] = df["timestamp"]

sessions = ["All"] + sorted(df["session_id"].unique().tolist())
choice = st.sidebar.selectbox("Session", sessions)
if choice != "All":
    df = df[df["session_id"] == choice]

alerts = df[df["severity"].isin(["high", "critical"])]

if choice == "All":
    total, n_sessions, n_alerts = (
        stats["total_commands"],
        stats["sessions"],
        stats["high_critical_alerts"],
    )
else:
    total, n_sessions, n_alerts = len(df), 1, len(alerts)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total commands", total)
c2.metric("Sessions", n_sessions)
c3.metric("High/Critical alerts", n_alerts)
c4.metric("LLM responses", int((df["source"] == "llm").sum()))
c5.metric("LLM errors", int((df["source"] == "llm-error").sum()))

left, right = st.columns(2)
with left:
    st.subheader("Attack categories")
    st.bar_chart(df["category"].value_counts())
with right:
    st.subheader("Severity")
    st.bar_chart(df["severity"].value_counts())

st.subheader("Attack timeline (commands per minute)")
tl = df.copy()
tl["minute"] = tl["time"].dt.floor("min").dt.tz_localize(None)
timeline = tl.groupby(["minute", "category"]).size().unstack(fill_value=0)
timeline.index = timeline.index.strftime("%H:%M")
st.bar_chart(timeline)

st.subheader("Alerts (high / critical)")
if alerts.empty:
    st.success("No high/critical alerts yet.")
else:
    st.dataframe(
        alerts.sort_values("id", ascending=False)[
            ["time", "session_id", "command", "category", "severity"]
        ],
    )

st.subheader("Live terminal view")
view = df.sort_values("id")
if choice == "All":
    view = view.tail(20)
lines = []
for _, row in view.iterrows():
    shown = "~" if row["cwd"] == "/root" else row["cwd"]
    lines.append(f"root@{HOSTNAME}:{shown}# {row['command']}")
    if row["response"]:
        lines.append(row["response"])
st.code("\n".join(lines), language="bash")

st.subheader("Command history")
st.dataframe(
    df.sort_values("id", ascending=False)[
        ["time", "session_id", "cwd", "command", "category", "severity", "response", "source"]
    ],
)

if auto:
    time.sleep(5)
    st.rerun()