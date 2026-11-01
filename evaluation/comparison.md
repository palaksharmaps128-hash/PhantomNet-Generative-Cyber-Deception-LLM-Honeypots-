# Before / after comparison

Before: `evaluation/results_gemini-3.1-flash-lite.csv`
After: `evaluation/results_gemini-3.1-flash-lite_static.csv`

| Metric | Before | After |
|---|---|---|
| Commands | 40 | 40 |
| Answered by Python (no LLM) | 32.5% | 50.0% |
| Latency mean, all commands | 10.34 s | 2.10 s |
| Latency p95, all commands | 39.02 s | 14.13 s |
| Latency mean, LLM commands | 15.31 s | 4.15 s |
| Realism checks passed | 97.5% | 100.0% |
| Classifier accuracy | 100.0% | 100.0% |
