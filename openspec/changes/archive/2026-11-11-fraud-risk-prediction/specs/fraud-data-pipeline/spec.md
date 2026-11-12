# Spec Delta

## Purpose

Provides seeded, reproducible synthetic relational fraud data (customers, transactions, devices, login events) with dual fraud labels, controlled data-quality defects, join match-rate reporting, a documented schema, and no real PII.

## ADDED Requirements

### Requirement: Seeded relational dataset generation
The system SHALL generate a synthetic relational dataset via a command-line generator that accepts `--seed`, table size parameters, and an output directory; it SHALL write four tables (customers, transactions, devices, login events) as deterministic CSV files plus per-table manifests recording seed, row counts, and UTC timestamp, and the transaction table SHALL be the temporal spine every other table joins against.

#### Scenario: Deterministic regeneration
- **WHEN** the generator runs twice with identical arguments on the same environment
- **THEN** every output table is byte-identical across the two runs

#### Scenario: Different seed yields different data
- **WHEN** the generator runs twice with different `--seed` values
- **THEN** the transaction table differs in content between runs

#### Scenario: Manifests record generation parameters
- **WHEN** the generator completes
- **THEN** each table has a manifest recording seed, row count, generator version, and UTC timestamp, and the transaction manifest's seed matches the `--seed` argument

#### Scenario: Negative - invalid arguments rejected
- **WHEN** the generator runs with `--n-transactions 0` or a non-integer seed
- **THEN** it exits non-zero with a clear error message and writes no partial tables

### Requirement: Dual fraud labels with distinct semantics
The transaction table SHALL carry two label columns with distinct generation semantics: `blocked` (operational intervention proxy — generated with non-trivial noise relative to ground truth) and `confirmed_fraud` (trusted ground-truth label — sparse). The generator SHALL never derive `confirmed_fraud` from `blocked`, and confirmed-fraud prevalence SHALL be configurable and low (default ≤ 2%).

#### Scenario: Labels are distinct columns with distinct semantics
- **WHEN** the generated transaction table is inspected
- **THEN** `blocked` and `confirmed_fraud` are separate columns, some transactions are blocked-but-not-confirmed, and some confirmed-fraud transactions are not blocked

#### Scenario: No fabricated confirmations
- **WHEN** label generation is audited via the manifest
- **THEN** the confirmed-fraud count is derived only from the generator's ground-truth process, and the manifest records both label prevalence rates

#### Scenario: Negative - infeasible confirmed rate rejected
- **WHEN** the generator runs with `--confirmed-rate 0.9`
- **THEN** it exits non-zero with a validation error stating the supported sparse range

### Requirement: Fraud signal in the data
The generated transactions SHALL contain adjustable signal (default fraud rate ≥ 1% on ground truth) such that fraud differs measurably from legitimate traffic in at least two point-in-time features, sufficient for a held-out classifier to recover AUC above 0.85 on ground-truth labels.

#### Scenario: Fraud rate is honored
- **WHEN** the generator runs with `--fraud-rate 0.05`
- **THEN** the empirical ground-truth fraud proportion of the output is within 20% relative of 0.05

#### Scenario: Model-learnable signal exists
- **WHEN** point-in-time feature distributions of fraud vs legitimate classes are compared
- **THEN** at least two features show a distributional gap such that a simple held-out classifier recovers AUC above 0.85 on ground-truth labels

#### Scenario: Negative - extreme fraud rate rejected
- **WHEN** the generator runs with `--fraud-rate 1.5`
- **THEN** it exits non-zero with a validation error

### Requirement: Controlled data-quality defects
The generator SHALL inject reproducible quality defects at configurable rates: device/login records referencing nonexistent customers (mismatched IDs), duplicate transaction rows, and missing timestamps in device/login events; defect rates SHALL be recorded in the manifest, and defect injection SHALL be deterministic per seed.

#### Scenario: Defects present and reproducible
- **WHEN** the generator runs twice with the same seed
- **THEN** the count and placement of mismatched IDs, duplicates, and missing timestamps are identical across runs

#### Scenario: Defect rates honored
- **WHEN** the generator runs with `--duplicate-rate 0.02`
- **THEN** the empirical duplicate proportion of the transaction table is within 20% relative of 0.02

#### Scenario: Negative - defect rate above 1 rejected
- **WHEN** the generator runs with any defect rate ≥ 1
- **THEN** it exits non-zero with a validation error

### Requirement: Join match-rate and data-quality reporting
The system SHALL produce a data-quality report from the generated tables quantifying: per-table row counts, join match rates (transactions→customers, devices→customers, logins→customers, and transactions→devices/logins where applicable), duplicate counts, missing-timestamp counts, and label prevalence; the report SHALL be written by an executable script to the outputs directory and copied as evidence.

#### Scenario: Match rates computed
- **WHEN** the quality-report script runs on the generated tables
- **THEN** the report JSON states a match rate in [0,1] for each declared join and row counts that equal the actual table sizes

#### Scenario: Quality report reflects injected defects
- **WHEN** the generator runs with a nonzero duplicate rate and the quality report runs
- **THEN** the report's duplicate count is greater than zero and consistent with the manifest's recorded defect rate

### Requirement: Schema documentation and no real PII
The schemas of all four tables SHALL be documented in the generator (field names, types, meaning, PII class), and the data SHALL contain no real personal identifiers: person-like fields SHALL be synthetic fabrications and no field SHALL contain SSN-like or Luhn-valid card-like values.

#### Scenario: Schema is available
- **WHEN** a consumer reads the schema registry module or its emitted schema file
- **THEN** every field of every table has a documented name, type, meaning, and PII class

#### Scenario: Data passes the repo data-convention check
- **WHEN** `make check-data` runs after generation
- **THEN** no R1/R2/R3 violations are reported for any case1 table
