# PhantomNet evaluation: gemini-3.1-flash-lite (static)

Total commands: 40  (LLM: 20, Python: 20)

| Metric | Result |
|---|---|
| Realism checks passed | 100.0% |
| LLM error rate | 0.0% |
| Lure accuracy (exact content) | 100.0% |
| Consistency (cd / pwd / ls) | 100.0% |
| Safety (no AI leak) | 100.0% |
| Threat classifier accuracy | 100.0% |
| Backup model used | 1 time(s) |
| Answered by Python (no LLM) | 50.0% |
| Latency mean, all commands | 2.10 s |
| LLM latency mean | 4.15 s |
| LLM latency median | 2.03 s |
| LLM latency p95 | 15.84 s |
| Python-handled latency mean | 56 ms |

## Realism by scenario

| Scenario | Passed |
|---|---|
| recon | 10/10 |
| credential_hunt | 2/2 |
| lures | 7/7 |
| consistency | 6/6 |
| malware | 4/4 |
| persistence | 3/3 |
| privilege_escalation | 3/3 |
| destructive_exfil | 2/2 |
| safety | 3/3 |

## Realism failures

None

## Classifier mismatches

None
