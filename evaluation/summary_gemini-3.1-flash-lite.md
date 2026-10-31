# PhantomNet evaluation: gemini-3.1-flash-lite

Total commands: 40  (LLM: 27, Python: 13)

| Metric | Result |
|---|---|
| Realism checks passed | 97.5% |
| LLM error rate | 0.0% |
| Lure accuracy (exact content) | 100.0% |
| Consistency (cd / pwd / ls) | 100.0% |
| Safety (no AI leak) | 100.0% |
| Threat classifier accuracy | 100.0% |
| Backup model used | 2 time(s) |
| LLM latency mean | 15.31 s |
| LLM latency median | 9.12 s |
| LLM latency p95 | 43.17 s |
| Python-handled latency mean | 25 ms |

## Realism by scenario

| Scenario | Passed |
|---|---|
| recon | 10/10 |
| credential_hunt | 1/2 |
| lures | 7/7 |
| consistency | 6/6 |
| malware | 4/4 |
| persistence | 3/3 |
| privilege_escalation | 3/3 |
| destructive_exfil | 2/2 |
| safety | 3/3 |

## Realism failures

- `cat /etc/shadow`: missing 'root:'

## Classifier mismatches

None
