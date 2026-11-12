# Tasks

## 1. Corpus

- [x] 1.1 Add pinned case2 deps (pypdf, pillow, reportlab, pytesseract, python-multipart + fastapi/uvicorn/pydantic/httpx/pytest stack) to `case2_docintel/requirements.txt`, reinstall the case venv, and verify `make test-case2` still passes (smoke)
- [x] 1.2 Create `docintel/corpus/schema.py` field registry (eight fields + types + PII class + rendered-label variants) and verify `tests/test_schema.py` asserts every field documented/typed and cross-field invariants documented
- [x] 1.3 Implement `docintel/corpus/generate.py` CLI (`--seed --n-invoices[15-30] --out`) writing deterministic PDF+image pairs + expected JSON + manifests, and verify `tests/test_corpus.py` passes (size honored, byte-identical rerun, different-seed differs, out-of-range exits non-zero)
- [x] 1.4 Add corpus content tests `tests/test_corpus_labels.py` (labels match rendered text verbatim, subtotal+tax=total, invoice_date ≤ due_date, ≥3 layout variants in 20, image variants yield <3 fields to PDF extraction) and verify they pass
- [x] 1.5 Run `make check-data` on the generated corpus and verify R1/R2/R3 pass with manifests tracked

## 2. Extraction pipeline

- [x] 2.1 Implement `docintel/pipeline.py` ingest + PDF text extraction (pypdf) with document-level statuses, and verify `tests/test_extraction.py` PDF-path tests pass (≥6/8 fields from text PDFs; corrupt file → `ingest_error`, no exception)
- [x] 2.2 Implement the OCR path behind `ocr_available()` probe (pytesseract when present, honest `ocr_unavailable` otherwise) and verify OCR tests pass on BOTH outcomes: real-engine path when the binary exists, probe-override path (≥5/8 fields) when it does not, plus honest `ocr_unavailable` with no invented text
- [x] 2.3 Implement `docintel/masking.py` (deterministic patterns → tokens + local map) and verify `tests/test_masking.py` passes (determinism, reversibility via map, masked text contains zero raw PII values)
- [x] 2.4 Implement provider protocol + `MockProvider` (regex structured extraction on masked text, zero-token usage metadata) and verify mock tests pass (deterministic output, schema-valid, offline)
- [x] 2.5 Implement `OllamaProvider` and `GroqProvider` (httpx, env-key for groq, JSON mode, real usage metadata) and verify unit tests pass offline with HTTP mocked (request shape, error handling, key handling — no live calls)
- [x] 2.6 Implement `docintel/validation.py` (per-field types, cross-field subtotal+tax=total and date order) with the four-status model, and verify `tests/test_validation.py` passes (valid → all `extracted`; inconsistency → `invalid` + reason; null → `missing`)
- [x] 2.7 Implement review-queue routing in the pipeline (any non-`extracted` field → queue entry with reasons) and verify queue tests pass including a JSON review-report artifact

## 3. Service and CLI

- [x] 3.1 Implement `docintel/core.py` shared ExtractCore + FastAPI `create_app` with `POST /extract` (multipart, extension allowlist, magic-byte check, 5 MB limit) and verify `tests/test_api.py` passes (200 valid, 413 oversized, 422 disguised/unsupported, `ocr_unavailable` surfaces honestly)
- [x] 3.2 Implement `docintel/cli.py` batch mode (`--in --out --provider`) using the same core, and verify `tests/test_cli.py` passes (batch artifact over corpus, CLI/API equality on same file, empty dir exits non-zero, per-file errors listed)

## 4. Security

- [x] 4.1 Add PII-safe logging (request id + outcome only) across API and CLI, and verify log-content tests pass after driving valid/rejected/oversized traffic through both surfaces
- [x] 4.2 Write `tests/test_security.py` (disguised uploads: renamed EXE/ELF + PDF-header/script polyglot; size limit; route hygiene incl. OpenAPI absence) and verify all pass
- [x] 4.3 Parametrize the security export runner for case2 and verify `evidence/security_test_results/case2_security.json` is generated listing each assertion with pass/fail

## 5. Evaluation and evidence

- [x] 5.1 Implement `docintel/evaluate.py` (per-field accuracy vs expected, missing rate, error breakdown, per-doc latency, tokens/cost from provider metadata with mock-zero labeled) and verify `tests/test_evaluation.py` passes (accuracy computed correctly on a hand-checkable mini-corpus, breakdown matches statuses, latency recorded, cost labeled, real-provider-missing-metadata reports null (never zero), missing-corpus exits non-zero)
- [x] 5.2 Run evaluation on the corpus with the mock provider, copy `outputs/evaluation.json` → `evidence/experiment_log/case2_evaluation_mock.json` byte-identical, and record the exact command in the evidence entry
- [x] 5.3 Produce sample outputs: pick 3 documents (clean, review-queued, ocr-unavailable-if-any), write CLI results + review report to `evidence/experiment_log/case2_sample_outputs.json`, and verify they match a fresh CLI run byte-for-byte

## 6. Docs and matrix

- [x] 6.1 Write `case2_docintel/docs/architecture.md` (data-flow diagram generator → extraction → masking → provider → validation → service/CLI → evaluation; every node names a real module) and verify node paths exist
- [x] 6.2 Write `case2_docintel/docs/data_map.md` (eight fields, types, sources, PII classes; explicit note that business fields are unmasked by design and what IS masked) and verify it matches `corpus/schema.py`
- [x] 6.3 Write `case2_docintel/docs/cost.md` (actual mock-zero report + the exact commands to reproduce a real ollama/groq run; no invented numbers) and verify every stated number cites a script output
- [x] 6.3b Write `case2_docintel/docs/ocr_setup.md` (Windows Tesseract install: UB-Mannheim/winget/choco, TESSERACT_CMD, `tesseract --version` verification, effect on image-path evaluation) and verify each documented command runs as written on this host or is marked as requiring the install
- [x] 6.4 Write `case2_docintel/docs/limitations.md` (no-tesseract honesty, mock-vs-real gap, clean-render OCR caveat, masking adversarial limits, review-queue-not-a-UI) and verify each limitation maps to a design decision
- [x] 6.5 Update matrix C2 rows (and new C2-1x rows for masking/providers/review) with real locations, flipping to `verified` only where paths exist and tests pass; verify `make check-evidence` passes
- [x] 6.6 Add Makefile targets `case2-corpus`, `case2-evaluate`, `case2-serve` and verify `make case2-corpus && make case2-evaluate` end-to-end, then `make test` and `make check` all pass

## Workflow follow-up

- Archive the change after review requirements are satisfied (`openspec archive document-intelligence`).
- Verify the archived result (main specs gain `document-corpus`, `document-extraction`, `document-service`).
