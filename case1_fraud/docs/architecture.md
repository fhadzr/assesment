# Case 1 Architecture — Fraud Risk Prediction

## Data flow

```
fraud/data/generate.py  --seed 42 --n-transactions 10000 ...
        │  writes (sorted, deterministic)
        ▼
case1_fraud/data/{customers,transactions,devices,logins}.csv + *_manifest.json
        │
        ▼
fraud/data/quality.py ──► outputs/quality_report.json ──► evidence/experiment_log/case1_quality_report.json
   (join match rates, duplicates, missing ts, label prevalence)
        │
        ▼
fraud/split.py ──► outputs/split_summary.json (+ split_{train,validation,test}_ids.json)
        │            └──► evidence/experiment_log/case1_split_summary.json
        │  chronological 70/15/15 (strict ordering asserted)
        ▼
fraud/features.py  (point-in-time: expanding per-customer aggregates,
        │           backward device/login joins; leakage-tested)
        ├──► fraud/model/baseline.py ──► outputs/model_baseline/ (rules, no fitting)
        ├──► fraud/model/train.py    ──► outputs/model_lr/   (LogisticRegression, label=blocked)
        │                        └──► outputs/model_hgb/   (optional experiment, --with-hgb)
        ▼
fraud/model/compare.py ──► outputs/comparison.json ──► evidence/experiment_log/case1_model_comparison.json
   (baseline + LR [+ HGB] on the IDENTICAL test row set)
        │
        ▼
fraud/model/evaluate.py ──► outputs/metrics.json
   (PR-AUC, precision, recall, F1, confusion matrix, P@K, R@K;
    ROC-AUC supplementary; floor flags only; sparsity note)
        │            └──► evidence/experiment_log/ (task 7.6)
        ▼
fraud/predictor.py  (probability, risk band, reason codes)
   ├──► fraud/service/app.py   FastAPI: POST /predict, GET /model-info,
   │                           X-Role (analyst|auditor), 1 MB limit
   └──► fraud/infer.py         CLI: CSV in → CSV out, --role
        │  security suite (tests/test_security.py)
        ▼
scripts/export_security_results.py ──► evidence/security_test_results/case1_security.json
```

## Module inventory

| Module | Responsibility |
| --- | --- |
| `fraud/data/schema.py` | Per-table field registry: single source of truth for generator, quality, trainer, API validation, data map |
| `fraud/data/generate.py` | Seeded relational generation, dual labels, deterministic defect injection |
| `fraud/data/quality.py` | Join match rates, duplicate/missing counts, label prevalence; dedup-idempotent |
| `fraud/split.py` | Chronological split with recorded boundaries; rejects degenerate ranges |
| `fraud/features.py` | Point-in-time features (cutoff contract enforced by tests/test_leakage.py) |
| `fraud/model/baseline.py` | Transparent rule-based scorer (required comparison floor) |
| `fraud/model/train.py` | LogisticRegression (required); optional HistGradientBoosting experiment |
| `fraud/model/compare.py` | Same-test-set comparison; refuses missing required pair |
| `fraud/model/evaluate.py` | Required metric set + provenance + sparsity interpretation |
| `fraud/predictor.py` | Shared prediction core (API and CLI agree by construction) |
| `fraud/service/app.py` | FastAPI app factory; role-based detail; redaction-only logging |
| `fraud/infer.py` | CLI batch inference; malformed CSV → row/field errors |
| `fraud/pseudonym.py` | Deterministic keyed blake2b pseudonyms (env-overridable key) |
