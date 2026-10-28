import json
import os
import pandas as pd
import streamlit as st
from config import LOG_FILE

st.set_page_config(page_title="PhantomNet Dashboard", layout="wide")
st.title("PhantomNet: Attacker Activity Dashboard")
st.button("Refresh")


def load_logs():
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame()
    rows = []
    with open(LOG_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return pd.DataFrame(rows)


df = load_logs()
if df.empty:
    st.info("Abhi koi log nahi hai. Pehle honeypot.py chalao aur kuch commands likho.")
    st.stop()

df["timestamp"] = pd.to_datetime(df["timestamp"])

sessions = ["All"] + sorted(df["session_id"].unique().tolist())
choice = st.sidebar.selectbox("Session", sessions)
if choice != "All":
    df = df[df["session_id"] == choice]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total commands", len(df))
c2.metric("Sessions", df["session_id"].nunique())
c3.metric("LLM responses", int((df["source"] == "llm").sum()))
c4.metric("LLM errors", int((df["source"] == "llm-error").sum()))

left, right = st.columns(2)
with left:
    st.subheader("Top commands")
    top = df["command"].str.split().str[0].value_counts()
    st.bar_chart(top)
with right:
    st.subheader("Response source")
    st.bar_chart(df["source"].value_counts())

st.subheader("Command history")
cols = ["timestamp", "session_id", "cwd", "command", "response", "source"]
st.dataframe(df.sort_values("timestamp", ascending=False)[cols])