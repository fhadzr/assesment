# Spec Delta

## Purpose

Serves document extraction through FastAPI and a CLI sharing one core, with an upload security posture, and evaluates the pipeline with executable scripts: field accuracy, missing rate, error breakdown, latency, and actual token/cost reporting.

## ADDED Requirements

### Requirement: FastAPI extraction endpoint
The system SHALL expose `POST /extract` accepting a document upload (PDF or image) with validation: allowed extensions AND magic-byte type check, a configurable maximum file size (default 5 MB), and rejection of anything failing either check with 4xx and a clear message; the response SHALL include the eight fields with statuses, the document-level status, and — for image documents requiring unavailable OCR — the honest `ocr_unavailable` status.

#### Scenario: Valid upload extracts
- **WHEN** a valid PDF invoice within the size limit is uploaded
- **THEN** the response is 200 with all eight fields and per-field statuses

#### Scenario: Negative - oversized upload rejected
- **WHEN** an upload exceeds the size limit
- **THEN** the response is 413 and no file content is persisted

#### Scenario: Negative - disguised file rejected by magic bytes
- **WHEN** a file named `.pdf` whose content is an executable or script is uploaded
- **THEN** the response is 422 citing the content-type mismatch

#### Scenario: Negative - unsupported extension rejected
- **WHEN** an upload has an extension outside the allowlist
- **THEN** the response is 422 listing allowed types

### Requirement: CLI batch extraction sharing the core
A CLI SHALL accept an input directory (or single file) and produce a JSON/CSV results artifact, using the same core logic as the API so results agree; malformed inputs SHALL produce per-file errors with names and reasons, and no partial output file on total failure.

#### Scenario: Batch over corpus
- **WHEN** the CLI runs over the generated corpus with the mock provider
- **THEN** it writes a results artifact with one entry per document including fields, statuses, and review flags

#### Scenario: CLI and API agree
- **WHEN** the same document is extracted via CLI and via API with identical provider configuration
- **THEN** the field values and statuses match

#### Scenario: Negative - unreadable directory fails clearly
- **WHEN** the CLI is pointed at a path with no supported documents
- **THEN** it exits non-zero stating no supported files were found

### Requirement: Upload and process security posture
The service SHALL enforce upload validation before any parsing, SHALL log no PII or file contents (request id + outcome only), SHALL expose no debug endpoints, and the security test suite SHALL include at least: disguised-upload rejection, size-limit rejection, and PII-safe logging assertions; results SHALL be exported to the evidence security directory.

#### Scenario: No PII in logs
- **WHEN** uploads (valid, rejected, oversized) are processed with logging enabled
- **THEN** logs contain request ids and outcomes only — no file bytes, extracted values, or PII

#### Scenario: Security evidence exists
- **WHEN** the security suite runs
- **THEN** an artifact under `evidence/security_test_results/` lists each security assertion with pass/fail for case2

#### Scenario: Negative - undeclared route 404
- **WHEN** a request targets an undeclared path
- **THEN** the response is 404 and the route is absent from the OpenAPI schema

### Requirement: Executable evaluation with actual cost reporting
Evaluation SHALL run as a script over the corpus producing per-field accuracy (vs expected JSON), missing rate, error-type breakdown by field and cause, and per-document latency; token usage and cost SHALL be reported from actual provider response metadata only (mock reports zero tokens/cost and is labeled mock; ollama/groq report their real usage fields), with no estimated or invented numbers; the output SHALL include provider name, model, and configuration for reproducibility.

#### Scenario: Field accuracy computed from expected labels
- **WHEN** evaluation runs over the corpus with the mock provider
- **THEN** the report contains accuracy for each of the eight fields computed against `expected/*.json`, plus corpus size and provider label `mock`

#### Scenario: Error breakdown present
- **WHEN** evaluation output is inspected
- **THEN** errors are broken down by field and cause (missing, invalid, ocr_unavailable) matching the field statuses

#### Scenario: Latency recorded
- **WHEN** evaluation runs
- **THEN** per-document extraction latency (milliseconds) is recorded, derived from actual measured durations

#### Scenario: Cost is actual or labeled mock
- **WHEN** provider metadata is available
- **THEN** token counts and cost come from the provider's response fields; when the provider is mock, the report states zero tokens/zero cost by construction rather than estimating

#### Scenario: Missing metadata is null, never zero
- **WHEN** a real provider's response carries no usage metadata
- **THEN** the evaluation reports tokens and cost as null with an explicit unavailable cost basis, not zeros or estimates

#### Scenario: Negative - evaluation without corpus fails
- **WHEN** the evaluation script runs with no corpus present
- **THEN** it exits non-zero stating the corpus is missing
