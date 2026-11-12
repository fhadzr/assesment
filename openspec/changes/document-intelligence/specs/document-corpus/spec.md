# Spec Delta

## Purpose

Provides a seeded synthetic invoice corpus (PDF and image variants) with machine-checkable expected JSON labels for the eight required fields, covering extraction and evaluation without real vendors or PII.

## ADDED Requirements

### Requirement: Seeded invoice corpus generation
The system SHALL generate a synthetic invoice corpus via a CLI generator accepting `--seed`, `--n-invoices` (supported range 15–30, default 20), and an output directory; each invoice SHALL be rendered as a text-based PDF and an image-based variant (rendered text in pixels), with deterministic content per seed recorded in per-invoice and corpus manifests.

#### Scenario: Corpus size honored
- **WHEN** the generator runs with `--n-invoices 25`
- **THEN** exactly 25 PDF/image pairs plus 25 expected JSON files exist, and the corpus manifest records 25

#### Scenario: Deterministic regeneration
- **WHEN** the generator runs twice with identical arguments on the same environment
- **THEN** every PDF, image, and expected JSON is byte-identical across runs (rendered outputs may embed no timestamps or random ids)

#### Scenario: Different seed yields different invoices
- **WHEN** the generator runs twice with different seeds
- **THEN** invoice numbers, vendor names, amounts, or dates differ between corpora

#### Scenario: Negative - out-of-range corpus size rejected
- **WHEN** the generator runs with `--n-invoices 10` or `--n-invoices 40`
- **THEN** it exits non-zero with a message stating the supported 15–30 range

### Requirement: Expected JSON labels for the eight fields
Every generated invoice SHALL have an expected JSON label file containing exactly the eight required fields (invoice_number, invoice_date, vendor_name, subtotal, tax, total, currency, due_date) whose values equal what is rendered in the document, with types (string, ISO date, decimal string, currency code) documented in the schema.

#### Scenario: Labels match rendered content
- **WHEN** any invoice's rendered text is compared with its expected JSON
- **THEN** each of the eight field values appears verbatim in the document text and the JSON parses against the published schema

#### Scenario: Cross-field consistency in ground truth
- **WHEN** expected labels are validated
- **THEN** subtotal + tax = total (as decimals) and invoice_date ≤ due_date for every invoice

#### Scenario: Negative - malformed expected JSON fails the corpus check
- **WHEN** an expected JSON file is corrupted (missing field, wrong type)
- **THEN** the corpus validation script exits non-zero naming the invoice and field

### Requirement: Controlled variation and no real PII
The corpus SHALL include controlled layout variation (field labels, ordering, date formats, currency placement) drawn from a fixed variation set per seed, and SHALL contain no real vendor names, addresses, or person identifiers — all names SHALL be fabricated from seeded word lists.

#### Scenario: Variation exists across the corpus
- **WHEN** corpus documents are compared
- **THEN** at least three distinct layout/date-format variants are present in a 20-invoice corpus

#### Scenario: No real-world vendor or personal data
- **WHEN** corpus text is scanned against a real-brand/person watchlist and the repo PII patterns
- **THEN** no real vendor brands or personal identifiers appear; all entity names come from the seeded fabricated word lists

### Requirement: Image variants are genuinely pixel-based
Image-based variants SHALL render the invoice text into an image format such that naive PDF text extraction returns no usable field text, forcing the OCR path.

#### Scenario: Text extraction fails on image variants
- **WHEN** the PDF text extractor runs on an image-based variant
- **THEN** it yields fewer than 3 of the 8 field values, demonstrating the document requires OCR

#### Scenario: Corpus passes repo data conventions
- **WHEN** `make check-data` runs after generation
- **THEN** no R1/R2/R3 violations are reported for the case2 corpus
