# Spec Delta

## Purpose

Temporally valid training, honest multi-model comparison, executable evaluation with the required metric set, and dual-surface inference (FastAPI + CLI) with reason codes, pseudonymization, role-based output detail, and a tested security posture.

## ADDED Requirements

### Requirement: Temporal train/validation/test split
The training pipeline SHALL split the transaction data chronologically: every transaction in the validation set SHALL be strictly later than every training transaction, and every test transaction strictly later than every validation transaction; split boundaries SHALL be determined by timestamp cut points and recorded in a split summary artifact.

#### Scenario: Chronological ordering holds
- **WHEN** the split summary is inspected after training-data preparation
- **THEN** max(train timestamp) < min(validation timestamp) and max(validation timestamp) < min(test timestamp), and the summary records each split's boundary timestamps and row counts

#### Scenario: Split is deterministic
- **WHEN** split preparation runs twice on the same dataset with the same parameters
- **THEN** the split assignments are identical

#### Scenario: Negative - degenerate time range rejected
- **WHEN** split preparation runs on a dataset whose time span cannot satisfy the configured proportions
- **THEN** it exits non-zero with an error explaining the constraint, rather than producing overlapping splits

### Requirement: Point-in-time feature construction without leakage
Features for any transaction SHALL be computed only from data with timestamps at or before that transaction's timestamp (e.g., customer historical aggregates up to time T, not full-dataset statistics); the feature builder SHALL expose its cutoff contract, and automated leakage tests SHALL assert that no feature value changes when strictly-future rows are altered.

#### Scenario: Features use only past information
- **WHEN** a transaction at time T is featurized, and any rows strictly after T are modified or removed
- **THEN** that transaction's feature vector is unchanged

#### Scenario: Automated leakage test in CI
- **WHEN** the leakage test suite runs on the generated dataset
- **THEN** it perturbs future rows for a sample of transactions and asserts feature-vector equality, and fails if any feature reacts to future data

#### Scenario: Negative - full-dataset statistics rejected
- **WHEN** a candidate feature implementation uses whole-dataset aggregations (e.g., a customer's lifetime mean including the future)
- **THEN** the leakage test detects the change and fails with the offending feature named

### Requirement: Model comparison on a shared temporal test set
The system SHALL train and compare, on one identical temporal test split: (a) a rule-based baseline scoring transactions by fixed feature rules, (b) Logistic Regression as the required primary model, and (c) optionally an additional experiment such as HistGradientBoosting; the comparison SHALL be produced by an executable script writing per-model metrics side by side, and the optional experiment SHALL never replace the baseline or Logistic Regression results.

#### Scenario: Both required models evaluated
- **WHEN** the comparison script runs
- **THEN** the comparison artifact contains a metrics block for the rule-based baseline and for Logistic Regression, each computed on the identical test-split row set

#### Scenario: Identical test set across models
- **WHEN** model predictions are compared across models
- **THEN** all models are scored on the same test transactions (same row count and identical transaction ids) and the comparison artifact records the test-set manifest

#### Scenario: Optional experiment is additive
- **WHEN** HistGradientBoosting is enabled
- **THEN** the comparison artifact gains its block while baseline and Logistic Regression blocks remain present and unchanged

#### Scenario: Negative - missing required model fails
- **WHEN** the comparison script runs without a Logistic Regression artifact
- **THEN** it exits non-zero stating the required model artifact is missing

### Requirement: Label policy for training and evaluation
Training SHALL use the `blocked` label as the primary noisy training target and evaluation SHALL report against `confirmed_fraud` as the trusted label, with both reported; the pipeline SHALL NOT convert blocked transactions into confirmed fraud, SHALL NOT fabricate confirmed labels, and SHALL document the blocked-label noise assumption in the training metadata.

#### Scenario: Train on blocked, evaluate on confirmed
- **WHEN** training and evaluation artifacts are inspected
- **THEN** the model metadata records training label `blocked`, and evaluation reports metrics against `confirmed_fraud` (and additionally against `blocked`) without any label conversion step

#### Scenario: No silent conversion
- **WHEN** the evaluation dataset is compared to the generated data
- **THEN** every `confirmed_fraud` value matches the generator's ground truth exactly — no blocked-but-unconfirmed transaction has become confirmed

#### Scenario: Noise assumption documented
- **WHEN** model metadata is read
- **THEN** it states the blocked-label noise rate used at generation time and cites the data manifest

### Requirement: Executable evaluation with the required metric set
The evaluation script SHALL compute, per evaluated label and per model: PR-AUC, precision, recall, F1, confusion matrix, Precision@K, and Recall@K (K configurable, default 100); ROC-AUC SHALL be included only as a supplementary metric.

#### Scenario: Required metrics all present
- **WHEN** the evaluation script runs for any model
- **THEN** the metrics JSON contains non-null PR-AUC, precision, recall, F1, a 2×2 confusion matrix, Precision@K, and Recall@K, with K recorded

#### Scenario: Precision@K correctness
- **WHEN** Precision@100 is computed on a known small fixture
- **THEN** the value equals the fraction of true positives among the model's top-100 scored transactions, verifiable by hand

#### Scenario: Negative - evaluation without a trained model fails
- **WHEN** the evaluation script runs with no model artifact present
- **THEN** it exits non-zero stating the artifact is missing

### Requirement: Evaluation honesty under label sparsity
All reported metrics SHALL come from the script's own computation on reproducible artifacts; the script SHALL NOT manipulate data, labels, or thresholds to satisfy any metric floor, and the output SHALL include a note explaining how sparse confirmed-fraud labels affect metric interpretation.

#### Scenario: Metrics from actual experiments only
- **WHEN** any metrics artifact is produced
- **THEN** it records the dataset manifest hash, split summary reference, and the exact command that generated it

#### Scenario: Sparse-label interpretation note present
- **WHEN** evaluation output is inspected
- **THEN** it contains an interpretation note on confirmed-fraud sparsity (small absolute positive counts make Precision@K/PR-AUC volatile)

#### Scenario: Required metrics all present
- **WHEN** the evaluation script runs for any model
- **THEN** the metrics JSON contains non-null PR-AUC, precision, recall, F1, a 2×2 confusion matrix, Precision@K, and Recall@K, with K recorded

#### Scenario: Precision@K correctness
- **WHEN** Precision@100 is computed on a known small fixture
- **THEN** the value equals the fraction of true positives among the model's top-100 scored transactions, verifiable by hand

#### Scenario: Metrics from actual experiments only
- **WHEN** any metrics artifact is produced
- **THEN** it records the dataset manifest hash, split summary reference, and the exact command that generated it

#### Scenario: Sparse-label interpretation note present
- **WHEN** evaluation output is inspected
- **THEN** it contains an interpretation note on confirmed-fraud sparsity (small absolute positive counts make Precision@K/PR-AUC volatile)

#### Scenario: Negative - evaluation without a trained model fails
- **WHEN** the evaluation script runs with no model artifact present
- **THEN** it exits non-zero stating the artifact is missing

### Requirement: Deterministic training pipeline
The system SHALL train the Logistic Regression model (and any optional experiment) from the generated dataset using a fixed random state, persist fitted models with version metadata, and produce identical evaluation metrics across re-runs on the same data and seed.

#### Scenario: Reproducible metrics
- **WHEN** the training/evaluation script runs twice on the same dataset and seed
- **THEN** the reported metrics are identical

#### Scenario: Artifact carries provenance
- **WHEN** training completes
- **THEN** each persisted artifact records model type, feature list, training seed, training label, dataset manifest hash, and creation timestamp

#### Scenario: Negative - training on corrupted data fails loudly
- **WHEN** the training script runs against a dataset missing a declared schema field
- **THEN** it exits non-zero with an error naming the missing field, rather than silently producing a model

### Requirement: FastAPI prediction service
The system SHALL expose an HTTP service with a POST endpoint accepting transaction features and returning a fraud probability with a risk band, plus a GET model-info endpoint returning model version and feature list; requests SHALL be validated with Pydantic models and invalid requests SHALL be rejected with 422 responses and no stack traces in responses, with a request-body size limit of 1 MB.

#### Scenario: Valid prediction request
- **WHEN** a POST request with schema-valid features is sent
- **THEN** the response is 200 with a probability in [0,1] and a risk band in {low, medium, high}

#### Scenario: Model info endpoint
- **WHEN** a GET request hits the model-info endpoint
- **THEN** the response includes model version, type, and the ordered feature list

#### Scenario: Negative - invalid feature values rejected
- **WHEN** a POST request contains a wrong-typed or out-of-range feature value
- **THEN** the service responds 422 without an internal stack trace

#### Scenario: Negative - malformed payload rejected
- **WHEN** a POST request sends invalid JSON or a body larger than 1 MB
- **THEN** the service responds 4xx and never 500

### Requirement: CLI inference with reason codes
The system SHALL provide a command-line inference interface accepting a CSV of transactions (and a model artifact path), rejecting malformed CSV with clear field-level errors, and emitting per-transaction probability, risk band, and human-readable reason codes derived from feature contributions; the CLI and API SHALL share one prediction core so their outputs agree.

#### Scenario: CSV batch inference
- **WHEN** the CLI runs on a schema-valid transactions CSV
- **THEN** it writes an output CSV with probability, risk band, and at least one human-readable reason per transaction, exits 0

#### Scenario: Reason codes are human-readable and derived
- **WHEN** a high-risk prediction's reason codes are inspected
- **THEN** they name concrete features and directions (e.g., "amount far above customer's historical average"), not opaque identifiers

#### Scenario: Negative - malformed CSV rejected with field errors
- **WHEN** the CLI runs on a CSV missing a required column or containing unparseable values
- **THEN** it exits non-zero listing the offending row numbers and field names, and writes no partial output file

#### Scenario: CLI and API agree
- **WHEN** the same transaction is scored by the CLI and the API with the same artifact
- **THEN** the probabilities and risk bands are equal

### Requirement: Pseudonymization and role-based output
Identifiers in predictions (customer id, transaction id, device id) SHALL be pseudonymized with a keyed, deterministic hash before appearing in any output; prediction outputs SHALL vary detail by caller role — `analyst` sees probabilities, bands, and reason codes; `auditor` additionally sees pseudonymous identifiers — without a full authentication system (role supplied as a request parameter/header, no password verification), and raw identifiers SHALL NOT appear in outputs for either role.

#### Scenario: Deterministic pseudonymization
- **WHEN** the same customer id is pseudonymized twice
- **THEN** the pseudonyms are identical; different ids yield different pseudonyms

#### Scenario: Role gates output detail
- **WHEN** an `analyst`-role prediction and an `auditor`-role prediction for the same transaction are compared
- **THEN** the analyst output omits pseudonymous identifiers while the auditor output includes them, and both omit raw identifiers

#### Scenario: Negative - unknown role rejected
- **WHEN** a request supplies an unrecognized role
- **THEN** it is rejected with 422 (API) or a clear CLI error, not defaulted to the most privileged role

### Requirement: Security posture of the service
The service and CLI SHALL log no personal identifiers or secrets, SHALL expose no debug endpoints, and the security test suite SHALL assert input-validation behavior, body-size limits, route hygiene, and log-content hygiene for both surfaces; results SHALL be exported to the evidence security directory.

#### Scenario: No PII in logs
- **WHEN** prediction requests (including rejected ones) are processed with logging enabled across API and CLI
- **THEN** logs contain no card numbers, account ids, raw request bodies, or raw customer/transaction identifiers — only request ids and coarse outcomes

#### Scenario: Security test evidence exists
- **WHEN** the security test suite runs
- **THEN** a results artifact is written under `evidence/security_test_results/` for case1 listing each assertion and its pass/fail outcome

#### Scenario: Negative - attempt to reach non-declared endpoint
- **WHEN** a request targets an undeclared path such as `/debug` or `/admin`
- **THEN** the service responds 404 and no such route exists in the OpenAPI schema
