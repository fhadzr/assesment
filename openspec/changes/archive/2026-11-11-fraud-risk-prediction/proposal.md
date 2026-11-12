# Proposal

## Why

Case 1 (Fraud Risk Prediction) is the assessment's top priority, and its rubric rows (C1-01…C1-09 in the traceability matrix) are entirely unimplemented: the case currently holds only a package skeleton with a smoke test. Building it now delivers the first end-to-end vertical slice — synthetic relational data → leak-free temporal training → honest model comparison → evaluated API/CLI inference — that Cases 2 and 3 will pattern-match on, and it exercises the foundation's conventions (seeded generators, reproducible metrics, evidence routing) with real content.

## What Changes

- Add a seeded **relational** synthetic-data generator covering four tables (customers, transactions, devices, login events) with controlled data-quality defects (mismatched IDs, duplicate records, missing timestamps), deterministic per-seed defect rates, and a join match-rate / data-quality report. No real PII.
- Generate **two distinct label columns**: `blocked` (noisy proxy, denser) and `confirmed_fraud` (trusted, sparse). They are never conflated: no silent conversion of blocked → confirmed, no fabricated confirmations.
- Add a **temporally valid** training pipeline: chronological train < validation < test split by timestamp, point-in-time feature construction (no future information), and automated leakage tests.
- Add a **model comparison** on one shared temporal test set: a rule-based baseline (required), Logistic Regression (required primary model), and HistGradientBoosting as an optional additional experiment — never a replacement for the required pair.
- Add evaluation with the required metric set: PR-AUC, precision, recall, F1, confusion matrix, Precision@K, Recall@K (ROC-AUC optional/supplementary), reported per label subset with an explicit note on how sparse confirmed-fraud labels affect interpretation. Metrics come only from executable reproducible experiments; data and thresholds are never manipulated to satisfy floors.
- Add **two inference surfaces sharing one predictor core**: the FastAPI service (existing scope) and a CLI (`python -m fraud.infer`) — both emitting human-readable reason codes, pseudonymized identifiers, and lightweight role-based output detail (no full auth system). Malformed CSV inputs are rejected with clear errors.
- Add security tests (invalid input, oversized payloads, no-PII-in-logs including CLI logs, route hygiene) with results routed to `evidence/security_test_results/`.
- Add Case 1 docs: architecture diagram, data map (four tables + labels + PII classes), cost estimate, limitations (incl. label-noise and sparsity limitations).
- Add evidence artifacts: model comparison results, temporal split summary, data-quality/join match-rate report, sample predictions with reason codes, confusion matrix and metrics; update the traceability matrix C1 rows only as implementation and tests are actually verified.

Out of scope: production-grade tuning, streaming/real-time inference, external model registry, a full authentication system, Cases 2 and 3, and any modification to the completed foundation.

## Capabilities

### New Capabilities
- `fraud-data-pipeline`: Seeded, reproducible synthetic relational data (customers, transactions, devices, login events) with dual fraud labels, controlled quality defects, join match-rate reporting, schema documentation, and no real PII.
- `fraud-model-service`: Temporally valid training, honest multi-model comparison, executable evaluation with the required metric set, and dual-surface inference (FastAPI + CLI) with reason codes, pseudonymization, role-based output, and a tested security posture.

### Modified Capabilities
- (none — the four foundation capabilities' requirements are unchanged; this change implements *within* them.)

## Impact

- **Code**: `case1_fraud/src/fraud/` grows modules (relational data generation, quality reporting, point-in-time features, baseline/LR training, comparison, evaluation, API, CLI); `case1_fraud/requirements.txt` gains pinned scikit-learn, numpy, pandas, joblib, fastapi, uvicorn, pydantic, httpx (all Python-3.10-compatible pins); new tests under `case1_fraud/tests/`.
- **Data/artifacts**: generated tables under `case1_fraud/data/` (gitignored except manifests), models + metrics + comparison under `case1_fraud/outputs/` (gitignored; evidence copies under `evidence/`).
- **Docs/evidence**: `case1_fraud/docs/` populated; matrix C1 rows updated only when verified; experiment log, data-quality report, split summary, comparison results, sample predictions added under `evidence/`.
- **Rubric mapping**: C1-01→`fraud-data-pipeline` (now relational); C1-02/03/04/07→`fraud-model-service` (now comparison + temporal + dual-surface); C1-05/06/08/09→docs deliverables tracked in tasks.
- **Dependencies**: all new pins in case1's isolated venv only; foundation packages and specs untouched.
