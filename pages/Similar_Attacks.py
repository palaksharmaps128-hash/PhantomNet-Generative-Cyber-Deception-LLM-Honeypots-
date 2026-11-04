import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

import db  # noqa: E402
import vector_store as vs  # noqa: E402

st.title("Similar attacks (vector search)")
st.caption(
    "Every logged command is turned into an embedding and stored in a vector "
    "database. Pick or type a command to find earlier commands that look like it."
)

try:
    info = vs.status()
except Exception as exc:
    st.error(f"The vector database could not start: {exc}")
    st.stop()

st.write(
    f"Vector store: **{info['backend']}**. "
    f"Indexed commands: Gemini embeddings = {info['gemini']}, offline embeddings = {info['local']}."
)

if st.button("Index latest logs", key="index_btn"):
    with st.spinner("Creating embeddings and saving them..."):
        try:
            result = vs.index_events()
            st.success(
                f"Indexed {result['new']} new command(s) with {result['mode']} embeddings. "
                f"Total in store: {result['total']}."
            )
        except Exception as exc:
            st.error(f"Indexing failed: {exc}")

events = db.fetch_logs(limit=1000)
commands = list(dict.fromkeys(e["command"] for e in events if e["command"].strip()))
if not commands:
    st.info("No logs yet. Send some commands in the dashboard terminal first.")
    st.stop()

chosen = st.selectbox("Pick a logged command", commands, key="pick_cmd")
typed = st.text_input("Or type any command", key="typed_cmd")
query = typed.strip() or chosen
hide_exact = st.checkbox("Hide the same command", value=True, key="hide_exact")
top_k = st.slider("How many results", 1, 10, 5, key="top_k")

if st.button("Find similar attacks", key="find_btn"):
    with st.spinner("Searching..."):
        found = vs.search_similar(query, k=top_k, hide_exact=hide_exact)
    if not found["results"]:
        st.warning("Nothing to show. Click 'Index latest logs' first, then search again.")
    else:
        st.write(f"Commands similar to `{query}` (embeddings: {found['mode']}):")
        table = pd.DataFrame(found["results"])
        table = table[["command", "similarity", "category", "severity", "session_id", "timestamp"]]
        st.dataframe(table, hide_index=True)