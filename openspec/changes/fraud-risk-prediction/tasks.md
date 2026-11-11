# Tasks

## 1. Data pipeline

- [x] 1.1 Create `fraud/data/schema.py` per-table field registry (name, type, role, PII class) and verify its unit test asserts every field of all four tables is documented and typed
- [x] 1.2 Implement `fraud/data/generate.py` CLI (`--seed --n-customers --n-transactions --fraud-rate --confirmed-rate --duplicate-rate --mismatch-rate --missing-ts-rate --out`) writing four deterministic sorted CSVs (customers, transactions, devices, logins) + per-table manifests, and verify `tests/test_data_generation.py` passes (determinism, different-seed, manifest contents incl. defect rates and both label prevalences, invalid-arg exits incl. `--confirmed-rate 0.9`)
- [x] 1.3 Implement dual-label generation semantics (`blocked` noisy proxy, `confirmed_fraud` sparse trusted, never derived one from the other) and verify `tests/test_labels.py` passes (some blocked-not-confirmed, some confirmed-not-blocked, confirmed count matches generator ground truth, no conversion path)
- [x] 1.4 Verify the fraud-signal scenario and add `tests/test_data_signal.py`: run generation at defaults, compare point-in-time feature class distributions, assert held-out AUC > 0.85 on ground-truth labels and ±20% fraud-rate accuracy
- [x] 1.5 Implement deterministic defect injection (dangling ids, duplicate rows, missing timestamps) and verify `tests/test_data_quality.py` passes (defect counts reproducible per seed, empirical duplicate rate within 20% relative of `--duplicate-rate`, rates ≥ 1 rejected)
- [x] 1.6 Implement `fraud/data/quality.py` join match-rate + data-quality report (per-table counts, match rates for the four declared joins, duplicate/missing counts, label prevalence) writing `outputs/quality_report.json`, and verify its tests pass (match rates in [0,1], counts equal actual sizes, report consistent with manifest defect rates); copy to `evidence/experiment_log/case1_quality_report.json`
- [x] 1.7 Run `make check-data` on generated output and verify R1/R2/R3 pass with manifests tracked

## 2. Temporal splitting and features

- [x] 2.1 Add pinned case1 deps (scikit-learn, numpy, pandas, joblib, fastapi, uvicorn, pydantic, httpx, pytest — all 3.10-compatible) to `case1_fraud/requirements.txt`, reinstall the case venv, and verify `make test-case1` still passes
- [x] 2.2 Implement `fraud/split.py` chronological split (timestamp quantile cut points 70/15/15, strict-order assertion, `outputs/split_summary.json` with boundaries/counts/label prevalence) and verify `tests/test_split.py` passes (max(train)<min(val)<max(val)<min(test), deterministic, degenerate-range exit non-zero); copy summary to `evidence/experiment_log/case1_split_summary.json`
- [x] 2.3 Implement `fraud/features.py` point-in-time feature builder (expanding per-customer aggregates, backward device/login joins, documented cutoff contract) and verify `tests/test_features.py` passes (schema-valid vectors, no NaN leakage into model inputs)
- [x] 2.4 Add automated leakage tests `tests/test_leakage.py` (featurize → perturb strictly-future rows → assert unchanged feature vectors; a deliberately leaky full-dataset-statistic variant is detected and named) and verify they pass

## 3. Models and comparison

- [x] 3.1 Implement `fraud/model/baseline.py` rule-based scorer (fixed transparent rules, no fitting) persisting `outputs/model_baseline/` with metadata, and verify its tests pass (deterministic scores in [0,1], provenance recorded)
- [x] 3.2 Implement `fraud/model/train.py` LogisticRegression pipeline (StandardScaler → LR, fixed random_state, training label `blocked` with documented noise assumption) writing `outputs/model_lr/{model.joblib, metadata.json}` with provenance (feature list, seed, label, dataset manifest hash), and verify `tests/test_model.py` passes (reproducibility, provenance fields, corrupted-data failure names missing field)
- [x] 3.3 Add optional HistGradientBoosting experiment behind `--with-hgb` writing `outputs/model_hgb/`, and verify it is additive-only: comparison artifacts still contain baseline and LR blocks unchanged
- [x] 3.4 Implement `fraud/model/compare.py` evaluating baseline + LR ( + optional HGB) on the identical test split (transaction-id equality asserted, test-set manifest recorded) writing `outputs/comparison.json`, and verify `tests/test_comparison.py` passes (both required blocks present, same row counts, missing-LR exits non-zero); copy to `evidence/experiment_log/case1_model_comparison.json`

## 4. Evaluation

- [x] 4.1 Implement `fraud/model/evaluate.py` computing per (model, label): PR-AUC, precision, recall, F1, confusion matrix, Precision@K, Recall@K (`--k`, default 100), ROC-AUC marked supplementary, floors reported as pass/fail flags only, provenance embedded (command, manifest hash, split ref), sparse-label interpretation note included, writing `outputs/metrics.json`, and verify `tests/test_evaluation.py` passes (all required metrics non-null, P@K correct on a hand-checkable fixture, identical across reruns, missing-artifact exits non-zero, note present)
- [x] 4.2 Verify label policy end to end and add the no-conversion assertion to `tests/test_evaluation.py` (evaluation-set `confirmed_fraud` matches generated table cell-for-cell; metadata records training label `blocked` + noise rate)

## 5. Inference (API + CLI)

- [x] 5.1 Implement `fraud/predictor.py` shared prediction core (probability, band, human-readable reason codes from LR feature directions) and verify `tests/test_predictor.py` passes (reasons name concrete features and directions, deterministic)
- [x] 5.2 Implement `fraud/service/app.py` app factory (`create_app(model_path)`) with Pydantic request model from the schema registry, POST predict (probability + band + reasons), GET model-info, 1 MB body-limit dependency, and verify `tests/test_api.py` passes (200 valid, 422 invalid, model-info contents, oversized body 4xx-never-500)
- [x] 5.3 Implement `fraud/pseudonym.py` (deterministic keyed blake2b) and role-based output (`analyst` vs `auditor`, `X-Role` header / `--role` flag, raw ids never in output), and verify `tests/test_pseudonym_roles.py` passes (determinism, uniqueness, role gating, unknown-role 422/CLI error, no raw ids in any payload)
- [x] 5.4 Implement `fraud/infer.py` CLI (CSV in → CSV out with probability/band/reasons, row-and-field-level errors for malformed CSV, `--role`), and verify `tests/test_cli.py` passes (valid batch output, malformed CSV exits non-zero listing offending rows/fields with no partial output, CLI probability/band equal API for same transaction and artifact)

## 6. Security

- [x] 6.1 Implement the logging redaction filter (request id + outcome only, API and CLI) and verify `tests/test_security.py` log-content assertions pass after driving valid, rejected, and malformed requests through both surfaces
- [x] 6.2 Add undeclared-route assertions (404 on `/debug`, `/admin`; absent from OpenAPI schema) to `tests/test_security.py` and verify they pass
- [x] 6.3 Create the pytest-JSON → evidence export runner and verify `evidence/security_test_results/case1_security.json` is generated by running it, listing each assertion (API + CLI) with pass/fail

## 7. Docs and evidence

- [x] 7.1 Write `case1_fraud/docs/architecture.md` with a data-flow diagram (generator → quality → split → features → models → comparison → evaluation → API/CLI) and verify each diagram node names a real module path
- [x] 7.2 Write `case1_fraud/docs/data_map.md` from the schema registry (four tables: field, type, source, PII class, label semantics for both label columns) and verify it matches `schema.py` exactly
- [x] 7.3 Write `case1_fraud/docs/label_policy.md` (blocked noise model, confirmed sparsity, train/evaluate policy, no-conversion guarantee) and verify every claim maps to a test
- [x] 7.4 Write `case1_fraud/docs/cost_estimate.md` (training/serving cost assumptions, `evidence/cost_analysis/case1_cost.md` copy) and verify numbers cite stated assumptions only
- [x] 7.5 Write `case1_fraud/docs/limitations.md` (label noise, confirmed sparsity volatility, demo scale, role spoofing, fixed threshold, CSV typing, expanding-feature scaling) and verify every limitation maps to a design decision in design.md
- [x] 7.6 Record evidence: copy `metrics.json`, `comparison.json`, split summary, quality report to `evidence/experiment_log/` with generating commands documented, and generate sample predictions with reason codes (`evidence/experiment_log/case1_sample_predictions.csv`) from the CLI; verify copies match outputs byte-for-byte

## 8. Matrix and integration

- [x] 8.1 Update matrix C1 rows with real implementation/test/evidence locations, flipping each to `verified` only where paths exist and its tests pass (doc rows only after docs exist); verify `make check-evidence` passes
- [x] 8.2 Add Makefile targets `case1-generate`, `case1-quality`, `case1-train`, `case1-serve`, `case1-infer` using the case venv and verify `make case1-generate && make case1-quality && make case1-train` end-to-end succeeds, then `make test` and `make check` all pass

## Workflow follow-up

- Archive the change after review requirements are satisfied (`openspec archive fraud-risk-prediction`).
- Verify the archived result (main specs gain `fraud-data-pipeline` and `fraud-model-service`).
