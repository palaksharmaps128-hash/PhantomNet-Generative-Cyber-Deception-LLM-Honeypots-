# PhantomNet evaluation: gemini-3.1-flash-lite (final)

Total commands: 40  (LLM: 20, Python: 20)

| Metric | Result |
|---|---|
| Realism checks passed | 100.0% |
| LLM error rate | 0.0% |
| Lure accuracy (exact content) | 100.0% |
| Consistency (cd / pwd / ls) | 100.0% |
| Safety (no AI leak) | 100.0% |
| Threat classifier accuracy | 100.0% |
| Backup model used | 0 time(s) |
| Answered by Python (no LLM) | 50.0% |
| Latency mean, all commands | 2.69 s |
| LLM latency mean | 5.34 s |
| LLM latency median | 4.67 s |
| LLM latency p95 | 11.61 s |
| Python-handled latency mean | 36 ms |

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
