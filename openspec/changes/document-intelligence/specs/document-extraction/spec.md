# Spec Delta

## Purpose

Ingests PDF and image invoices, extracts text (PDF layer or OCR with honest degradation), masks PII before any LLM context construction, runs pluggable LLM structured extraction (mock/ollama/groq), and validates fields deterministically with per-field status and human-review routing.

## ADDED Requirements

### Requirement: Document text extraction with two paths
The system SHALL extract document text via a PDF text layer extractor for text-based PDFs and an OCR path for image-based documents, behind one interface; when the OCR engine binary is unavailable on the host, the system SHALL report this explicitly per document (status `ocr_unavailable`) and SHALL NOT fabricate OCR text or silently skip image documents.

#### Scenario: Text PDF extracts fields
- **WHEN** a text-based PDF invoice is ingested
- **THEN** the extracted text contains at least 6 of the 8 expected field values verbatim

#### Scenario: Image document routed to OCR
- **WHEN** an image-based invoice variant is ingested and OCR is available
- **THEN** its text comes from the OCR path and contains at least 5 of the 8 expected field values

#### Scenario: OCR unavailable is honest
- **WHEN** the OCR binary is not installed and an image document is ingested
- **THEN** the result carries status `ocr_unavailable` for that document with a clear message, and no OCR text is invented

#### Scenario: Negative - unreadable file reported
- **WHEN** a corrupt or empty document is ingested
- **THEN** extraction returns a per-document error status instead of raising or returning empty success

### Requirement: PII masking before LLM context
Before any text is sent to an LLM provider, the system SHALL apply deterministic PII masking (emails, phone numbers, person-name-adjacent identifiers, account/reference numbers) producing masked text plus a local, in-process token map for unmasking; the unmasked text SHALL NOT be included in any provider request, and unmasked values SHALL NOT appear in provider-facing context or logs.

#### Scenario: Provider payload is masked
- **WHEN** extraction with any non-mock provider is intercepted at the provider boundary
- **THEN** the request text contains mask tokens and none of the original PII values

#### Scenario: Masking is deterministic and reversible locally
- **WHEN** the same document is masked twice
- **THEN** identical mask tokens are produced; and the token map restores original values within the process

#### Scenario: Negative - unmasked PII never reaches provider
- **WHEN** a test injects a document containing emails/phones/account numbers and captures the provider request
- **THEN** the captured request contains zero occurrences of those raw values

### Requirement: Pluggable LLM providers with mock as test default
Extraction SHALL run against a provider interface with three implementations: `mock` (deterministic, offline, default for all automated tests), `ollama` (local, default real provider when reachable), and `groq` (optional external, credentials from environment only); selection SHALL be by configuration, and no automated test SHALL require a real provider or network.

#### Scenario: Mock provider is deterministic
- **WHEN** the same masked text is extracted twice with the mock provider
- **THEN** identical structured output is returned with zero network calls

#### Scenario: Full suite runs offline
- **WHEN** the entire case2 test suite runs with network access disabled
- **THEN** all tests pass using the mock provider

#### Scenario: Unknown provider rejected
- **WHEN** configuration names a provider other than mock|ollama|groq
- **THEN** initialization fails with a clear error listing valid providers

#### Scenario: Groq credential handling
- **WHEN** the groq provider initializes
- **THEN** it reads its key from an environment variable only; no key literal exists in source, and absence of the variable is a clear configuration error, never a fallback to mock

### Requirement: Structured extraction of the eight fields
The LLM extraction SHALL return a structured record containing exactly the eight required fields, each carrying a value-or-null plus a provider confidence signal when available; output SHALL parse against the published JSON schema or fail as an extraction error, never as unvalidated free text.

#### Scenario: Eight fields always present in output
- **WHEN** extraction succeeds for a document
- **THEN** the output record contains all eight field keys, each with a value or explicit null

#### Scenario: Negative - malformed LLM output becomes an error
- **WHEN** a provider returns text that does not parse to the schema
- **THEN** the extraction result is an error status for that document with the parse failure reason, not a partial guess

### Requirement: Deterministic validation with field status and review routing
Extracted values SHALL pass deterministic validation independent of the LLM: type checks (date parses, decimal parses, currency is a 3-letter code), cross-field consistency (subtotal + tax = total within tolerance; invoice_date ≤ due_date), and format checks (invoice number matches corpus pattern); every field SHALL carry status `extracted` | `missing` | `invalid` | `low_confidence`, and any document with a non-`extracted` field SHALL be routed to a human-review queue with the reasons attached.

#### Scenario: Valid extraction passes validation
- **WHEN** all eight fields extract correctly for a text PDF with the mock provider
- **THEN** every field status is `extracted` and the document is not queued for review

#### Scenario: Cross-field inconsistency flagged
- **WHEN** extracted subtotal + tax ≠ total beyond tolerance
- **THEN** the affected fields are `invalid` with a cross-field reason and the document enters the review queue

#### Scenario: Missing field status
- **WHEN** a field returns null from extraction
- **THEN** its status is `missing` and the document enters the review queue

#### Scenario: Review queue is reviewable
- **WHEN** a batch produces documents with non-extracted fields
- **THEN** a review report lists each document, its fields' statuses, and reasons, writable as a JSON artifact
