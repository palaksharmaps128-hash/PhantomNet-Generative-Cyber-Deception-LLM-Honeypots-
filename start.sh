#!/bin/bash
# Runs the API and the dashboard in one container.
python -m flask --app api run --host 0.0.0.0 --port 5000 &
exec python -m streamlit run dashboard.py --server.address 0.0.0.0 --server.port 8501 --server.headless true