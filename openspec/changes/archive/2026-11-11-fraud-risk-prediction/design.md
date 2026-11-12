# Design

## Context

The foundation (archived change `assessment-foundation`) established per-case venvs, pytest infra, convention checkers, and evidence routing. Case 1 currently contains only a package skeleton (`fraud` package, smoke test, `pytest==8.3.4`). The matrix rows C1-01…C1-09 define the deliverables; a rubric-completeness review added mandatory requirements (relational data quality, temporal validity, dual labels, model comparison, richer metrics, CLI + reason codes, pseudonymization/roles). Python is 3.10.8 — every pin must support it. See proposal.md for scope motivation.

## Goals / Non-Goals

**Goals:**
- One vertical slice: `generate → quality-report → split → features → compare (baseline/LR/HGB) → evaluate → serve (API+CLI)`, runnable via Makefile targets with reproducible outputs.
- Temporal honesty: no future information in any feature; enforced by automated leakage tests, not convention.
- Label honesty: blocked (noisy) and confirmed_fraud (sparse, trusted) stay distinct end to end.
- Every metric from an executable script; every rubric deliverable traceable to a real artifact.

**Non-Goals:**
- Model performance beyond honest reporting (no threshold/data manipulation to hit floors — shortfalls are reported, not hidden).
- Streaming inference, model registry, retraining pipelines, a real authentication system (role is a declared attribute, not verified identity).
- Case 2/3 shared abstractions; any foundation modification.

## Decisions

### D1: Relational CSV tables with a strictly-typed schema module
Four tables as CSV (stdlib `csv` + pandas for processing): `customers.csv` (spine), `transactions.csv` (temporal spine for splits/joins), `devices.csv`, `logins.csv`. Schema lives in `fraud/data/schema.py` as a per-table field registry (name, type, role, PII class) used by generator, quality report, trainer, and both inference surfaces — one source of truth, so the data map is generated from code. Alternative: parquet (rejected — pyarrow adds weight; CSV keeps the malformed-input requirements testable in the raw).

### D2: Rule-constructed synthetic signal with dual ground truth
Seeded `numpy.random.Generator`. Each transaction draws a latent fraud flag from `--fraud-rate`; fraud rows get shifted feature distributions (amount, hour-of-day, foreign merchant, velocity). Two observed labels: `confirmed_fraud` = ground truth thinned by `--confirmed-rate` (sparse, trusted); `blocked` = noisy proxy (false positives from legitimate tail + misses). Deterministic: fixed column order, sorted writes, no set iteration. Signal tuned so held-out AUC > 0.85 on ground truth (spec scenario = test).

### D3: Defects as a deterministic generation stage
After clean generation, a seeded defect pass injects: dangling customer/device ids (mismatch), exact duplicate transaction rows, NaT-style empty timestamps in devices/logins. Rates are CLI-configurable (`--duplicate-rate`, `--mismatch-rate`, `--missing-ts-rate`), recorded in the manifest. The quality-report script measures what was actually injected — the manifest and report must agree (testable).

### D4: Point-in-time features via sorted expanding aggregates
`fraud/features.py`: sort by timestamp, group by customer, compute expanding-window aggregates (count/mean/std of amount, time-since-last, distinct devices seen so far) using cumulative operations that never look ahead; join device/login events with `merge_asof`-style backward joins on timestamp. Leakage tests: featurize → perturb/delete strictly-future rows → featurize again → assert feature vectors for earlier transactions identical (sampled). Whole-dataset statistics are structurally impossible (features never receive the full frame), and the test names any feature that regresses.

### D5: Chronological split with recorded cut points
`fraud/split.py`: cut points at quantiles of transaction timestamps (default 70/15/15 train/val/test); assert strict ordering (max(train) < min(val) < max(val) < min(test)); write `outputs/split_summary.json` (boundaries, counts, label prevalence per split) → evidence copy. Degenerate time ranges (zero-span, duplicated timestamps at boundaries) exit non-zero rather than overlap.

### D6: Model comparison — baseline and LR required, HGB optional
`fraud/model/baseline.py`: transparent rule score (weighted feature rules, no fitting). `fraud/model/train.py`: LogisticRegression (primary, `Pipeline(StandardScaler → LR)`, fixed `random_state`); HistGradientBoosting behind `--with-hgb` as an optional experiment. `fraud/model/compare.py` evaluates all available models on the **same** test split (same row set asserted by transaction-id equality) and writes `outputs/comparison.json` (per-model metrics + test-set manifest reference) → evidence copy. The comparison refuses to run without baseline+LR artifacts (required-pair enforcement).

### D7: Label policy is structural, not conventional
Train target = `blocked` (documented noise rate in metadata, cited from manifest). Evaluation reports both `confirmed_fraud` (primary, trusted) and `blocked` (context). No code path writes `confirmed_fraud`; evaluation loads it read-only from the generator's output. The "no silent conversion" test compares evaluation-set confirmed labels to the generated table cell-by-cell.

### D8: Evaluation metric set with explicit sparsity note
`fraud/model/evaluate.py` computes per (model, label): PR-AUC, precision, recall, F1, confusion matrix, Precision@K/Recall@K (default K=100, `--k`), ROC-AUC marked `supplementary`. Metrics JSON embeds provenance (command, manifest hash, split reference) and a standing interpretation note: with ≤2% confirmed prevalence and small absolute positives, PR-AUC and P@K are volatile — absolute counts are reported alongside rates. Floors from the earlier draft (PR-AUC ≥ 0.80) are **reported as pass/fail flags**, never enforced by data or threshold manipulation.

### D9: One predictor core, two surfaces
`fraud/predictor.py`: loads artifact, scores a feature row, produces `{probability, band, reasons}`. Reason codes: LR coefficient-direction rules evaluated against the row's standardized features (e.g., "amount_z=+3.2 far above customer historical average → +risk"), human-readable strings with feature names. Bands: <0.3 low, 0.3–0.7 medium, >0.7 high. API (`fraud/service/app.py`, `create_app(model_path)`, Pydantic from schema registry) and CLI (`fraud/infer.py`, csv in/out) both call the core — an equality test pins their agreement.

### D10: Pseudonymization and lightweight roles
`fraud/pseudonym.py`: `blake2b(key=PSEUDONYM_KEY, raw_id)` — deterministic, non-reversible without the key, key constant in code (it protects output sharing, not secrets; data is synthetic anyway). Roles: `analyst` (probability/band/reasons) vs `auditor` (+ pseudonymous ids); supplied via `X-Role` header (API) / `--role` flag (CLI); unknown role → 422/CLI error, never silent escalation. Raw ids never appear in any output payload.

### D11: Security posture across both surfaces
Redaction filter logs request id + outcome only. Body limit (1 MB) via size-checking dependency. No debug routes. Security suite (`tests/test_security.py`) drives both API and CLI, asserts log hygiene (capture handlers, scan for raw ids/bodies), exports pytest JSON → `evidence/security_test_results/case1_security.json`. No secrets: synthetic data, no env credentials.

### D12: Data flow

```
fraud/data/generate.py --seed S ... ──► data/{customers,transactions,devices,logins}.csv + manifests
        │
        ▼
fraud/data/quality.py ──► outputs/quality_report.json (match rates, dup counts, label prev) ──► evidence/
        │
        ▼
fraud/split.py ──► outputs/split_summary.json (chronological 70/15/15) ──► evidence/
        │
        ▼
fraud/features.py (point-in-time; leakage-tested)
        │
        ├──► fraud/model/baseline.py ──► outputs/model_baseline/
        ├──► fraud/model/train.py (LR; optional HGB) ──► outputs/model_lr[/ _hgb]/
        │
        ▼
fraud/model/compare.py ──► outputs/comparison.json (same test set) ──► evidence/
fraud/model/evaluate.py ──► outputs/metrics.json + P@K/R@K + notes ──► evidence/
        │
        ▼
fraud/predictor.py (probability, band, reason codes)
   ├──► fraud/service/app.py (FastAPI: role header, pseudonymized ids)
   └──► fraud/infer.py (CLI: CSV batch, malformed-CSV errors)
        │ security suite (API + CLI)
        ▼
evidence/security_test_results/case1_security.json
```

PII note (per foundation `synthetic-data` spec): all person-like fields are fabricated tokens; R3 checker guards SSN/Luhn patterns; outputs are pseudonymized (D10) before evidence.

### D13: Makefile integration
`case1-generate`, `case1-quality`, `case1-train` (split → baseline → LR → optional HGB → compare → evaluate), `case1-serve`, `case1-infer` — case-venv interpreters, no shell branching (foundation portability rules).

## Risks / Trade-offs

- [pandas join semantics can hide mismatches] → quality report computes match rates explicitly with assertions on expected rates; report-vs-manifest agreement is a test.
- [Expanding-window features are O(n log n) per customer] → acceptable at demo scale (10k rows); documented as scaling limitation.
- [LR may underperform HGB on interactions] → that is a legitimate comparison outcome, not a failure; optional-experiment framing keeps the required pair authoritative.
- [Sparse confirmed labels → volatile metrics] → absolute positive counts reported next to every rate; interpretation note embedded in metrics JSON (D8).
- [Role header without auth is spoofable] → documented limitation (demo posture, no real identities); spec wording avoids claiming authentication.
- [Blake2b key in code is not a secret] → acceptable: pseudonymization protects casual re-identification of synthetic ids, documented in security.md conventions.
- [CSV malformed-input error quality] → loader validates against schema registry row-by-row, accumulates errors with row numbers, fails before writing output.
- [Evidence copies drift from outputs] → matrix evidence paths point only at `evidence/` copies; checkers verify existence.

## Migration Plan

Greenfield within the case. Rollback = delete new modules + outputs; foundation untouched. Matrix C1 rows stay `pending` until artifacts exist and tests pass (`make check-evidence` verifies), then flip to `verified` — never before.

## Open Questions

None blocking. Deferrable: threshold calibration per fraud cost; HGB tuning (optional experiment stays untuned).
