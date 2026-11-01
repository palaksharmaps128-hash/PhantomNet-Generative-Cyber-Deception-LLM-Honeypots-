# Comparison

flash-lite: `evaluation/results_gemini-3.1-flash-lite_final.csv`
flash: `evaluation/results_gemini-3.5-flash_final.csv`

| Metric | flash-lite | flash |
|---|---|---|
| Commands | 40 | 40 |
| Answered by Python (no LLM) | 50.0% | 50.0% |
| Latency mean, all commands | 2.69 s | 3.32 s |
| Latency p95, all commands | 10.86 s | 13.25 s |
| Latency mean, LLM commands | 5.34 s | 6.61 s |
| Realism checks passed | 100.0% | 100.0% |
| Classifier accuracy | 100.0% | 100.0% |
