# evidence-management Specification

## Purpose

Defines where assessment evidence lives, the traceability matrix's columns and statuses, and the maintenance rules that keep every rubric requirement mapped to implementation, tests, and evidence artifacts.

## Requirements

### Requirement: Evidence directory conventions
Assessment evidence SHALL live under `evidence/` in four locations: `assessment_traceability.csv` (the traceability matrix), `experiment_log/` (one entry per experiment/metric run), `security_test_results/` (security test outputs), and `cost_analysis/` (cost estimates with their assumptions). Evidence files SHALL NOT be scattered elsewhere in the repository.

#### Scenario: Evidence found in expected locations
- **WHEN** an assessor looks for a security test result, experiment log, or cost estimate
- **THEN** it is found under the corresponding `evidence/` subdirectory and nowhere else

#### Scenario: Misplaced evidence is flagged
- **WHEN** an evidence artifact is created outside `evidence/` (for example a metrics JSON in a case's root)
- **THEN** the convention check reports it as misplaced

### Requirement: Traceability matrix columns and statuses
The traceability matrix SHALL have these columns: requirement id, rubric area, criterion, points, case, scenario id, implementation location, test location, evidence artifact, and verification status. The verification status SHALL be one of `pending`, `verified`, or `failed` and SHALL be set to `verified` only when a real artifact exists at the referenced path and its tests pass.

#### Scenario: Column contract
- **WHEN** the matrix file is parsed
- **THEN** it contains exactly the ten defined columns in order with no malformed rows

#### Scenario: Verification requires an existing artifact
- **WHEN** a row's status is changed to `verified`
- **THEN** every non-empty path in that row (implementation, test, evidence) resolves to an existing file; otherwise the status change is rejected

#### Scenario: No row starts verified
- **WHEN** the matrix is created or a new requirement is added
- **THEN** its initial status is `pending`

### Requirement: Matrix completeness against the rubric
The matrix SHALL contain one row per assessment requirement covering all three cases, privacy and security, architecture and engineering, and all six critical thinking scenarios. Adding or changing a requirement in any approved change SHALL update the matrix in the same change.

#### Scenario: Rubric areas all covered
- **WHEN** the matrix rows are grouped by rubric area
- **THEN** Case 1, Case 2, Case 3, Privacy & Security, Architecture & Engineering, and six scenario rows are all present

#### Scenario: Change updates the matrix in lockstep
- **WHEN** an approved change adds a new requirement
- **THEN** the same change's tasks include updating the matrix, and the archived change shows the new row

### Requirement: Experiment log entries are reproducible
Each experiment log entry SHALL record the command run, the seed or version identifiers needed to reproduce it, and the result, and SHALL be generated or verifiable from an executable script rather than hand-typed.

#### Scenario: Log entry reproducibility
- **WHEN** an assessor follows an experiment log entry's recorded command on a clean checkout
- **THEN** the recorded result can be regenerated within documented tolerance

#### Scenario: Fabricated entry is detectable
- **WHEN** a log entry's recorded result cannot be produced by its recorded command
- **THEN** the discrepancy is treated as an integrity violation, not a rounding difference
