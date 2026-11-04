# PhantomNet: Generative Cyber-Deception (LLM Honeypot)

PhantomNet is a proof-of-concept honeypot. It looks like a Linux database server
(`prod-db-01`, Ubuntu 22.04, PostgreSQL 14) to anyone who types commands into it.
Answers are produced by a mix of fixed Python responses and a Gemini LLM.
Every command is logged, classified by attack type, and shown in a dashboard.

Built for the Infotact Solutions Generative AI internship (project ITS/GAI/1147).

![Architecture](architecture.png)

```mermaid
flowchart LR
  A[Attacker] --> B[honeypot.py CLI]
  A --> C[api.py Flask API]
  B --> D{Command router}
  C --> D
  D -->|cd, pwd| E[shell.py]
  D -->|fixed commands, lure files| F[static_responses.py + lures.py]
  D -->|everything else| G[llm_engine.py]
  G --> H[Gemini main model]
  G -.->|if busy| I[Gemini backup model]
  E --> J[logger.py]
  F --> J
  G --> J
  J --> K[threat_classifier.py]
  J --> L[(SQLite + JSONL logs)]
  L --> M[Flask API: logs, stats, summary]
  M --> N[Streamlit dashboard]
```

## How it works

1. **Hybrid answers.** Commands with fixed output (`whoami`, `uname -a`, `sudo -l`,
   `cat /etc/passwd`), the bait files, and commands that must stay consistent
   (`wget`/`curl`/`scp`/`ssh` always fail because the server has no internet, `useradd`
   adds the user to `/etc/passwd`) are answered by Python, instantly and always the same.
   Everything else (`ps aux`, `uptime`, `netstat`) is answered by Gemini.
2. **Lures.** `/root` holds invented bait files: `.pgpass`, `db_backup.sql`, `backup.sh`,
   `notes.txt`, `.bash_history`. All credentials and data are fake.
3. **Safety guards.** Prompt-injection attempts ("ignore previous instructions", "are you an AI")
   and any output that leaks AI wording are replaced with `command not found`.
   The API limits each session to 30 commands per minute and 500 in total.
4. **Reliability.** If the main Gemini model is busy, the engine retries and then
   switches to a backup model.
5. **Threat classifier.** Rule-based, tags each command as recon, credential_access,
   data_access, malware_download, persistence, privilege_escalation, exfiltration,
   destructive or other, with a severity.
6. **Logging and reports.** Events go to SQLite and a JSONL file. When a session ends,
   a short admin summary is produced.
7. **Similar attacks (vector database).** Each logged command is turned into an embedding
   (Gemini embeddings, with an offline fallback) and stored in ChromaDB. The dashboard page
   "Similar Attacks" and `GET /api/similar` find earlier commands that look like a new one.

## Files

| File | Purpose |
|---|---|
| `honeypot.py` | Terminal honeypot (local CLI) |
| `api.py` | Flask REST API around the same honeypot |
| `llm_engine.py` | Gemini calls, retry, backup model, safety guards |
| `shell.py` | `cd`, fake `ls` / `cat`, and consistent `useradd` / `wget` / `scp` answers |
| `lures.py` | Bait files and their metadata |
| `static_responses.py` | Fixed answers for static commands |
| `threat_classifier.py` | Command to attack category and severity |
| `logger.py`, `db.py` | JSONL and SQLite logging |
| `summary.py` | Per-session admin summary |
| `dashboard.py` | Streamlit dashboard with a live attacker terminal (uses the API) |
| `pages/Similar_Attacks.py` | Dashboard page for vector search of similar attacks |
| `vector_store.py`, `index_logs.py` | Embeddings and ChromaDB store, and a script to index the logs |
| `Dockerfile`, `docker-compose.yml`, `start.sh` | Optional Docker packaging (local use) |
| `start_demo.ps1` | One-click start of API and dashboard on Windows |
| `evaluate.py`, `compare.py` | Evaluation runs and before/after table |
| `evaluation/` | Saved evaluation results |

## Setup

```
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and put your Gemini API key in it. Never commit `.env`.

## Run

```
python honeypot.py                    # terminal honeypot
python api.py                         # Flask API on http://127.0.0.1:5000
python -m streamlit run dashboard.py  # dashboard with a built-in attacker terminal (start the API first)
python index_logs.py                  # index logged commands for vector search
python evaluate.py --tag mytest       # evaluation, results go to evaluation/
python compare.py                     # before/after table
```

One-click start on Windows: `powershell -ExecutionPolicy Bypass -File .\start_demo.ps1`

With Docker (optional, local only): `docker compose up --build`, then open
http://localhost:8501. The `.env` file is read at run time and is not copied into the image.

### API

| Method | Path | Description |
|---|---|---|
| POST | `/api/command` | Send `{"command": "...", "session_id": "..."}`, get the output |
| GET | `/api/logs?limit=100&session_id=...` | Recent events |
| GET | `/api/stats` | Totals by category, severity and source |
| GET | `/api/summary/<session_id>` | Session summary |
| GET | `/api/similar?q=...&k=5` | Earlier commands similar to `q` (vector search) |
| GET | `/api/health` | Health check |

Example (PowerShell):

```
Invoke-RestMethod -Uri http://127.0.0.1:5000/api/command -Method Post -ContentType "application/json" -Body '{"command":"whoami"}'
```

## Evaluation

40 scripted attacker commands in 9 scenarios, run through the API code path with
`gemini-3.1-flash-lite`. "Before" is the LLM-only version for static commands,
"after" adds `static_responses.py`.

| Metric | Before | After |
|---|---|---|
| Answered by Python (no LLM) | 32.5% | 50.0% |
| Latency mean, all commands | 10.34 s | 2.10 s |
| Latency p95, all commands | 39.02 s | 14.13 s |
| Latency mean, LLM commands | 15.31 s | 4.15 s |
| Realism checks passed | 97.5% | 100.0% |
| Classifier accuracy | 100.0% | 100.0% |

Raw results are in `evaluation/`.

## Limitations

- **Proof of concept.** The honeypot runs locally (API bound to `127.0.0.1`). It is not a real
  SSH server and was not exposed to the internet or tested against real attackers.
- **Latency depends on Google's load.** The before/after run happened at different times, so the
  latency numbers are indicative only. LLM answers can still take several seconds, which a
  careful attacker could notice.
- **Small test set.** Realism and classifier scores come from 40 commands. The classifier rules
  were written with similar commands in mind, so 100% is not a general accuracy claim.
- **Automatic checks only.** Realism is checked with simple text rules, not by human judges.
- **Backup model has no chat history.** When it answers, it does not see earlier commands.
- **Vector search uses the command text only.** It needs the logs to be indexed first and works
  best with Gemini embeddings. If they are not available, an offline fallback is used, which
  matches on similar spelling more than on meaning.
- **Docker and the start script are for local use.** The container runs Flask's development
  server, is bound to localhost, and is not hardened for public exposure.
- **No pipes or scripts.** Commands with `|`, `>` or `;` are answered by the LLM and may be
  less consistent with the fake file system.

## Safety

Run this only on your own machine. Do not expose it to a public network. All credentials,
names and e-mail addresses in the bait files are invented. Logs may contain attacker input,
so they are excluded from git.