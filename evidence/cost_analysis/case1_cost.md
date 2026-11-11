# Case 1 Cost Estimate

All numbers below are derived from stated, reproducible assumptions — measured
on the assessment machine (Python 3.10.8, Windows 11) with the default dataset
(200 customers / 10,000 transactions). They are estimates for the prototype's
scale, not production quotes. Copy also at `evidence/cost_analysis/case1_cost.md`.

## Measured compute (this machine)

| Stage | Command | Observed wall time | Notes |
| --- | --- | --- | --- |
| Data generation | `python -m fraud.data.generate` | ~1 s | 10k transactions, 4 tables |
| Quality report | `python -m fraud.data.quality` | < 1 s | pure-python joins |
| Training (LR) | `python -m fraud.model.train` | ~2 s | 7,000 train rows, 12 features |
| Training (HGB, optional) | `python -m fraud.model.train --model hgb` | ~3 s | optional experiment |
| Evaluation + comparison | `python -m fraud.model.evaluate` / `compare` | ~2 s | 1,500 test rows |
| Test suite | `pytest case1_fraud/tests` | ~80 s | includes per-test regeneration |

## Extrapolated costs (stated assumptions, not measurements)

Assumptions: 10,000 transactions/day; retrain weekly; serve 1 req/s peak;
cloud VM ≈ USD 0.05/hour (2 vCPU); no GPU required (LR/HGB are CPU models).

| Item | Assumption | Estimated monthly cost |
| --- | --- | --- |
| Training | 4 retrains/month × 5 s × $0.05/3600 s | < $0.01 (negligible) |
| Serving API | 1 req/s × 730 h (always-on smallest VM) | ~$3.65 (VM floor dominates) |
| Storage | datasets + artifacts < 50 MB | < $0.01 |

**Total prototype-scale estimate: ≈ USD 4/month**, dominated by the
always-on serving VM, not compute.

## Sensitivity

- 100× data (1M transactions): generation/training scale roughly linearly
  (expanding-window features are the main cost); still minutes, still CPU.
- The per-request inference cost is < 1 ms CPU; API cost is entirely the
  always-on process floor at this scale.
- An external LLM provider (not used in Case 1) would change the cost
  profile per request; Case 1 uses none.

## What is NOT included

- Human review cost of blocked queues (ops modeling out of scope).
- Infrastructure redundancy, monitoring, or multi-region serving.
- Any GPU-based modeling (none used).
