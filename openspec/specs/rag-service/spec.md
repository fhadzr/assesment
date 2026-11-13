# rag-service Specification

## Purpose

Serves grounded RAG answers through a CLI and FastAPI sharing one core, with explicit validated roles, an executable evaluation suite (recall/correctness/faithfulness/citation/refusal/latency/cost), security tests, and evidence.

## Requirements

### Requirement: Shared answering core with validated role
A single core SHALL implement retrieval + answering and be used identically by the CLI and the API; the caller role SHALL be supplied explicitly, validated against `all|hr|finance|exec`, and SHALL NOT default silently to a privileged role.

#### Scenario: CLI and API agree
- **WHEN** the same question and role are submitted via CLI and API
- **THEN** the answer, citations, and refusal marker are identical

#### Scenario: Role validated
- **WHEN** a caller supplies an unknown or missing role
- **THEN** the service returns an explicit validation error and does not answer

#### Scenario: Negative - no privileged default
- **WHEN** role is omitted
- **THEN** the request is rejected rather than defaulting to `exec`

### Requirement: FastAPI and CLI surfaces
The system SHALL expose a `POST /ask` endpoint accepting a question and role and returning answer, citations, refusal marker, and retrieval provenance; and a CLI accepting the same inputs to a JSON output; error responses SHALL be non-500 for validation errors and contain no stack traces.

#### Scenario: Valid ask returns grounded answer
- **WHEN** a valid question+role is posted
- **THEN** the response contains answer text, a citations list, and a refusal flag

#### Scenario: CLI batch over dataset
- **WHEN** the CLI runs over the evaluation dataset
- **THEN** it writes one result per question with answer/citations/refusal

#### Scenario: Negative - malformed request 4xx
- **WHEN** a request has missing question or invalid role
- **THEN** the response is 4xx (not 500) with a clear message

### Requirement: Executable evaluation with honest cost
The evaluation SHALL compute, via a script: Recall@3, citation precision/recall, refusal quality, faithfulness/groundedness, and per-question latency, reported separately per label (answerable, unanswerable, restricted); token/cost SHALL come only from actual provider response metadata (mock = zero-by-construction labeled mock; real = usage fields, null when absent), and mock vs real results SHALL be reported separately.

#### Scenario: Recall@3 and citation metrics computed from labels
- **WHEN** evaluation runs over the labeled dataset
- **THEN** the report contains Recall@3 (expected citations found in top-3 / expected citations), citation precision (answer citations in the retrieved permitted set / total answer citations), and citation recall (expected citations in the answer / expected citations), each derived from the dataset labels and actual responses

#### Scenario: Results reported separately per label
- **WHEN** evaluation output is inspected
- **THEN** the metrics are broken out separately for `answerable`, `unanswerable`, and `restricted` subsets, in addition to any overall figures

#### Scenario: Refusal quality measured per subset
- **WHEN** evaluation runs
- **THEN** refusal quality reports the proportion correctly refused on `unanswerable ∪ restricted` and the proportion NOT refused on `answerable`

#### Scenario: Faithfulness reported honestly by provider
- **WHEN** provider is mock
- **THEN** faithfulness is measured deterministically from retrieved evidence and labeled mock; for a real provider, groundedness is a lexical-overlap heuristic or `unavailable`, never a fabricated faithfulness claim

#### Scenario: Edge cases reported as null, not forced
- **WHEN** a denominator is zero (no expected citations, or an answer with no citations)
- **THEN** the affected metric is `null`/`undefined` — Recall@3 and citation recall are null for empty expected citations, and citation precision is null (not perfect) for a no-citation answer

#### Scenario: Cost labeled mock or actual
- **WHEN** provider is mock
- **THEN** tokens/cost are zero and labeled mock; for real providers, values come from response metadata and missing metadata is null, never estimated

#### Scenario: Negative - evaluation without dataset fails
- **WHEN** the evaluation script runs with no dataset present
- **THEN** it exits non-zero stating the dataset is missing

### Requirement: Security tests and PII-safe logging
The security suite SHALL assert the six named security behaviors (restricted-doc exclusion from the prompt, injection ignored, out-of-KB refusal, cross-role refusal, citation integrity, role non-manipulation), exercise the roles hr/finance/exec, keep logs free of PII and document text, and export results to the evidence security directory.

#### Scenario: Six required security assertions present
- **WHEN** the security suite runs
- **THEN** all named assertions are exercised and their pass/fail exported to `evidence/security_test_results/case3_security.json`

#### Scenario: Prompt content is inspected, not only output
- **WHEN** the security suite verifies restricted-document exclusion
- **THEN** it captures the assembled provider prompt and asserts zero text from restricted documents, independent of the final answer

#### Scenario: Multiple roles exercised
- **WHEN** the security suite runs cross-role and injection tests
- **THEN** the roles hr, finance, and exec are each exercised, and an invalid role is rejected fail-closed

#### Scenario: Fabricated and format-valid-but-unretrieved citations rejected
- **WHEN** a provider emits a citation not in the retrieved permitted set (malformed or format-valid)
- **THEN** the core strips it and, if no supported citation remains, returns the generic refusal

#### Scenario: No PII in logs
- **WHEN** requests are processed with logging enabled
- **THEN** logs contain request ids and outcomes only — no document text, no PII

#### Scenario: Negative - undeclared route 404
- **WHEN** a request targets an undeclared path
- **THEN** the response is 404 and absent from the OpenAPI schema
