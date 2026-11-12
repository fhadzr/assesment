# Case 2 Limitations

Each limitation maps to the design decision (design.md) that produced it and,
where applicable, the spec scenario that bounds it.

| # | Limitation | Source (design decision) | Honesty note |
| --- | --- | --- | --- |
| 1 | **Tesseract not installed**: image documents report `ocr_unavailable` and are excluded from OCR-path evaluation — never simulated. | D3 | `docs/ocr_setup.md` documents Windows install; evaluation's `error_breakdown` shows the honest count (20/40 docs for the default corpus). |
| 2 | **Mock provider is "too good"**: deterministic regex on clean synthetic text yields near-perfect extraction (20/20 text PDFs ok); this does not generalize to real invoices. | D5, D8 | Evaluation labels provider `mock`; the mock-vs-real gap is itself a documented finding, not hidden. |
| 3 | **OCR on clean synthetic renders ≠ scanned documents**: image variants are crisp Pillow rasters, far easier than real scans/noise. | D1, risks | Stated explicitly; OCR results only become meaningful after Tesseract install, and even then only on this clean corpus. |
| 4 | **Masking regexes may miss novel PII shapes**: only email/phone/account-reference patterns are masked; adversarial inputs with other PII would pass through. | D4 | Boundary tests assert the corpus's known PII never reaches providers; unknown shapes are an open limitation. |
| 5 | **Business fields unmasked by design**: amounts, dates, invoice number, vendor are not PII-masked because the extractor must read them. | D4, data map | These are synthetic fabrications; if real invoices were ingested, this boundary would need re-review. |
| 6 | **Review queue is JSON, not a UI**: human review is a report artifact (id/field/value/status/reason), not an interactive tool. | D6, non-goals | Spec requires review *routing*, satisfied; a UI is explicitly out of scope. |
| 7 | **Real-provider cost evidence absent**: no Ollama/Groq run has been executed, so only the mock's true zero-cost is reported. | D8, cost.md | `docs/cost.md` gives exact reproduce commands; absence of real numbers is honest, not replaced by estimates. |
| 8 | **Provider abstraction is httpx-only, no SDK**: fine for these two APIs, but not a general LLM client. | D5 | Chosen deliberately for auditability and offline-testability. |
| 9 | **Windows-first**: tested on Windows 10.0.26200; POSIX assumed compatible (no shell branching in Makefile) but not CI-tested here. | Foundation D7/D8 | Raw pip/pytest fallbacks documented in README. |
| 10 | **Determinism depends on pinned renderers + SOURCE_DATE_EPOCH**: changing reportlab/Pillow versions could change rendered bytes. | D1, risks | Exact pins + regeneration test; manifest records generator version. |
