# Proposal

## Why

Case 2 (Document Intelligence) is the assessment's second priority and its rubric rows (C2-01…C2-10 in the traceability matrix) are unimplemented — `case2_docintel/` holds only the foundation skeleton. Case 1 established the vertical-slice pattern (schema registry → pipeline → comparison/evaluation → dual-surface service → evidence); this change applies it to unstructured documents: synthetic invoices → text extraction/OCR → LLM structured extraction with PII masking → validated JSON → evaluated API/CLI. It is also the first change to exercise the assessment's privacy-by-design rule end to end (masking **before** external LLM context construction).

## What Changes

- Add a seeded synthetic invoice corpus generator: **15–30 invoices** (default 20), each rendered as **both** a text-based PDF and an image-based variant, with machine-checked `expected/*.json` labels for the eight required fields (invoice_number, invoice_date, vendor_name, subtotal, tax, total, currency, due_date), controlled layout variation, and manifests — all synthetic, no real vendors or PII.
- Add a document ingestion layer: PDF text extraction (pure-Python) and OCR for image-based documents behind one provider interface — Tesseract when the binary is available, with explicit honest degradation (missing binary reported, image docs excluded from OCR-path evaluation rather than silently skipped or faked).
- Add LLM structured extraction behind a provider abstraction with **three implementations**: `mock` (deterministic, used by all automated tests — offline per foundation rule), `ollama` (local, default real provider), and `groq` (optional external). Provider selection is configuration, never hardcoded.
- Add **PII masking before any LLM call**: deterministic regex-based masking of identifiers/amounts-adjacent personal data with a reversible token map kept local; masked text is what reaches provider context. No PII leaves the process boundary unmasked.
- Add deterministic field validation (type/range/cross-field consistency: subtotal + tax = total, date ordering), per-field confidence/status (`extracted` / `missing` / `invalid` / `low_confidence`), and a human-review queue for anything not confidently valid.
- Add two inference surfaces sharing one core (Case 1 pattern): FastAPI `POST /extract` (multipart upload + JSON) and a CLI batch mode.
- Add evaluation as executable scripts only: field accuracy per field, missing rate, error-type breakdown, extraction latency, and **actual token/cost reporting from provider responses** (no invented numbers; mock provider reports zero-cost by construction and is labeled as such).
- Add security tests: unsafe/disguised uploads (wrong magic bytes, renamed executables, polyglot attempts), file-size and type validation, PII-safe logging, plus the case floor of the repo-wide secret scan.
- Add docs and evidence: architecture + data-flow diagram, data map, cost report from actual runs, limitations, sample outputs in `evidence/experiment_log/`, matrix C2 rows updated only when verified.

Out of scope: production OCR accuracy tuning, multi-page complex invoices beyond the synthetic layouts, a review UI (review is a queue + JSON report), training custom models, touching Case 1 or the foundation.

## Capabilities

### New Capabilities
- `document-corpus`: Seeded synthetic invoice corpus (PDF + image variants) with expected JSON labels, schema documentation, and no real PII — feeds extraction and evaluation.
- `document-extraction`: Ingestion (PDF text + OCR with honest degradation), PII masking before LLM context, pluggable LLM providers (mock/ollama/groq), deterministic validation with per-field status and human-review routing.
- `document-service`: FastAPI + CLI sharing one extraction core, upload security posture, and executable evaluation (accuracy, missing rate, error breakdown, latency, actual token/cost).

### Modified Capabilities
- (none — foundation and fraud specs are untouched; this change implements within existing conventions.)

## Impact

- **Code**: `case2_docintel/src/docintel/` grows modules (corpus generation, extraction, masking, providers, validation, API, CLI, evaluation); `case2_docintel/requirements.txt` gains pinned pure-Python deps (see design D2); tests under `case2_docintel/tests/`.
- **Data/artifacts**: corpus under `case2_docintel/samples/` + `expected/` (gitignored except manifests, per foundation convention); outputs under `case2_docintel/outputs/` (gitignored; evidence copies under `evidence/`).
- **Docs/evidence**: `case2_docintel/docs/` populated; matrix C2 rows updated as verified; experiment log + cost analysis entries.
- **Rubric mapping**: C2-01→`document-corpus`; C2-02/03→`document-extraction`; C2-04/05→`document-service` (+ evaluation); C2-06…C2-10→docs/evidence deliverables tracked in tasks.
- **Dependencies**: new pins in case2's isolated venv only; no changes to case1 or the root.
