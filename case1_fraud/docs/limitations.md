# Case 1 Limitations

Each limitation maps to the design decision (design.md) that produced it and,
where applicable, the spec scenario that bounds it.

| # | Limitation | Source (design decision) | Mitigation / honesty note |
| --- | --- | --- | --- |
| 1 | **Blocked label is noisy** (80% catch, false-positive tail). Model learns the proxy, not exact fraud. | D2, D7 | Dual-label evaluation quantifies the gap (metrics.json reports both); label_policy.md documents semantics; never conflated. |
| 2 | **confirmed_fraud is sparse** (~1%): PR-AUC and Precision@K are volatile; small absolute positives. | D2, D8 | Sparsity interpretation note embedded in every metrics output; absolute positive counts reported with every rate. |
| 3 | **Metric floors are informative, not enforced.** At confirmed-label sparsity, PR-AUC ≥ 0.80 is not realistically achievable; we report the shortfall honestly rather than tuning data/thresholds to hit it. | D8, spec honesty requirement | Floor flags recorded pass/fail; no manipulation anywhere in the code path (evaluate.py). |
| 4 | **Demo scale.** 10k transactions, 200 customers; conclusions do not automatically transfer to production volume. | Context (assessment scope) | Scaling behavior documented; cost_estimate.md extrapolates under stated assumptions. |
| 5 | **Role-based output is a prototype access-control demonstration, NOT authentication.** X-Role is a declared attribute; anyone can claim auditor. No passwords, tokens, or identity verification. | D10 | Documented as demo posture; spec wording avoids claiming auth. Production would need real identity + authorization. |
| 6 | **Pseudonymization key** defaults to a checked-in demo constant (synthetic data only); production must set FRAUD_PSEUDONYM_KEY from a secret store. | D10 | Env-var override implemented; per assessment rule 10, the key guards output-sharing discipline here, not real data. |
| 7 | **Fixed threshold 0.5 and fixed bands** (<0.3 low, 0.3–0.7 medium, >0.7 high). No cost-of-fraud calibration. | D9 | Threshold calibration noted as deferrable design question; not silently tuned. |
| 8 | **CSV typing**: schema lives in code (`fraud/data/schema.py`), not in the file format; malformed CSVs are rejected with row/field errors (CLI) but the format itself is untyped. | D1 | Loader validates/coerces on read; parquet rejected as over-engineering for this scale. |
| 9 | **Expanding-window features** are O(n log n) per customer with a Python-level login join loop; acceptable at 10k rows, would need vectorization (merge_asof) at 100×. | D4 | Point-in-time correctness was prioritized over raw speed; leakage tests pin the contract. |
| 10 | **HGB optional experiment is untuned.** Its comparison block is informational; the required pair (baseline + LR) is authoritative. | D6 | Comparison asserts required pair present and unchanged when HGB added. |
| 11 | **Windows-first development.** Paths and Makefile verified on Windows (MinGW make); POSIX assumed compatible (no shell branching) but not CI-tested here. | Foundation D7/D8 | Raw pip/pytest commands documented in README as make-free fallback. |
| 12 | **Temporal split is quantile-based**; boundary transactions share timestamps across adjacent splits only at exact ties (rejected at degenerate ranges). | D5 | Split summary records exact boundaries; strict ordering asserted in tests. |
