# Design

## Context

Foundation + Case 1 patterns are established: per-case venvs, schema-registry-as-source-of-truth, shared prediction core behind API+CLI, executable-script-only metrics, evidence routing, convention checkers. `case2_docintel/` holds only the skeleton (package `docintel`, smoke test, `pytest==8.3.4`). Host: Python 3.10.8, Pillow 11 + reportlab 4.2 available, **Tesseract NOT installed** (designs around it honestly). Groq/Ollama optional; tests must run offline with mocks (CLAUDE.md rule). See proposal.md for scope.

## Goals / Non-Goals

**Goals:**
- Case 1's vertical-slice pattern applied to documents: corpus → extraction → validation → service/CLI → evaluation → evidence.
- Privacy-by-design demonstrated concretely: masking **before** provider context, proven by captured-payload tests.
- Honest degradation: no Tesseract → explicit `ocr_unavailable`, never fake OCR or silent skips.
- Every number in evidence from a script run (tokens/cost from provider metadata or labeled mock-zero).

**Non-Goals:**
- Real OCR accuracy work (synthetic corpus, clean render); production review UI (queue + JSON report only); training/fine-tuning; touching case1 or foundation; adding infra beyond pip-installable libs.

## Decisions

### D1: Corpus via reportlab (PDF) + Pillow (image), pure-Python
Generator draws invoice content from seeded word lists (fabricated vendor names like "Bluepeak Services"), renders the SAME content twice: text PDF (reportlab) and image variant (Pillow raster of the text layout) — so expected JSON serves both paths. Determinism: no timestamps/ids in rendered bytes; fixed layout ordering; byte-identical regeneration is a test. Range 15–30 enforced at CLI. Variants: 4 label styles × 3 date formats × 3 currency placements from a fixed table. Alternative: scan real invoices (forbidden — synthetic-only rule).

### D2: Dependencies — minimal and pure-Python-first
Add to case2 venv (all exact-pinned, 3.10-compatible): `pypdf==5.1.0` (PDF text layer), `pillow==11.0.0` + `reportlab==4.2.5` (corpus rendering), `pytesseract==0.3.13` (thin wrapper; **optional at runtime** — degrades explicitly when the binary is missing), `python-multipart==0.0.20` (FastAPI multipart uploads), plus the existing stack pins (fastapi, uvicorn, pydantic, httpx, pytest). NOT added: OCR engines as Python deps (tesseract is a system binary), pdfplumber/pdfminer (pypdf suffices for our simple layouts), vector DBs (case 3 scope).

### D3: Extraction pipeline = staged, each stage pure and testable
`ingest → extract_text (pdf|ocr) → mask_pii → llm_extract (provider) → validate → status/route`. Each stage a module in `docintel/`, composing in `docintel/pipeline.py`. Document-level statuses: `ok`, `review`, `ocr_unavailable`, `extraction_error`, `ingest_error`. OCR check is one function (`ocr_available()`) probed once per run, reported per document — no exceptions swallowed.

**OCR must be genuinely runnable, not just degraded-to:** the OCR path is a real pytesseract implementation exercised whenever the binary exists. The host currently lacks Tesseract; installation is documented in `docs/ocr_setup.md` (Windows: UB-Mannheim installer or `choco install tesseract-credential-free`/`winget install UB-Mannheim.TesseractOCR`, set `TESSERACT_CMD` or PATH, verify with `tesseract --version`), and the test suite covers BOTH outcomes: when the binary is present, the available-path test runs real OCR over an image invoice; when absent, `ocr_available()` is monkeypatched so the available-path code is still executed and asserted, while the honest-unavailable test verifies the degradation. CI/assessor machines without the binary therefore still get full path coverage via the monkeypatch, and a machine with Tesseract exercises the real engine.

### D4: Masking = deterministic regex + token map, enforced at the boundary
`docintel/masking.py`: patterns (email, phone, IBAN-ish/account refs, name-adjacent ids from the corpus schema) → `«PII_1»` tokens; map returned alongside, never serialized into provider context. The provider abstraction wraps requests through a `MaskedContext` type that structurally cannot carry raw text — tests capture the wire payload (mock transport) and assert zero raw-PII occurrences. Amounts/dates/invoice numbers are business fields, not PII — deliberately unmasked (the LLM must extract them); this boundary is documented in the data map.

### D5: Providers = protocol + 3 impls; mock is rule-based on masked text
`docintel/providers/`: `MockProvider` (deterministic regex parsing of the masked text against corpus field patterns — genuinely exercises the pipeline, returns structured output + zero-token usage metadata), `OllamaProvider` (HTTP to localhost via httpx, `format: json`, reads usage from response), `GroqProvider` (env-key `GROQ_API_KEY`, JSON mode, real usage/cost from response). Selection via `DOCINTEL_PROVIDER` env or CLI flag; tests inject mock explicitly. No SDK dependencies — plain httpx keeps the surface auditable and offline-testable.

### D6: Validation independent of the LLM (trust but verify)
`docintel/validation.py`: per-field validators (date ISO-parse, decimal-parse, ISO-4217-style 3-letter check, invoice-number pattern) + cross-field rules (subtotal+tax=total ±0.01; invoice_date ≤ due_date). Status model exactly per spec: `extracted|missing|invalid|low_confidence` (low_confidence when provider confidence < 0.7 when the provider supplies one). Review queue = list in the batch result + JSON report artifact; **every queue entry carries**: invoice/document id, field name, extracted value (or null), validation status, and the review reason(s) — enough for a human to adjudicate without re-opening the document.

### D7: Service + CLI share `docintel/core.py`
Case 1 pattern: `ExtractCore` class (provider + pipeline config) → `extract(bytes, filename) → ExtractionResult`. FastAPI app factory `create_app(core)`; upload validation BEFORE parsing: extension allowlist {pdf, png, jpg, jpeg, tiff} + magic-byte check (pypdf parses PDFs; Pillow probes images; mismatch → 422) + 5 MB limit (413). CLI: `--in dir --out results.json --provider mock`. API≡CLI equality pinned by test. multipart via `python-multipart` (required by FastAPI uploads).

### D8: Evaluation = one script, honest numbers only
`docintel/evaluate.py` over corpus: per-field accuracy/missing (vs expected/*.json), error breakdown (from field statuses), per-doc latency (`time.perf_counter`), tokens/cost accumulated **only from actual provider response metadata**. Rules: mock reports `{tokens: 0, cost: 0, provider: "mock"}` with `"cost_basis": "mock-zero-by-construction"`; a real provider (ollama/groq) whose response carries NO usage metadata reports `tokens: null, cost: null` with `"cost_basis": "metadata-unavailable"` — never zeros, never estimates. Real-provider runs happen only when a human runs them; their outputs land in evidence with the exact command. No fabricated numbers anywhere (CLAUDE.md rule).

### D9: Security = upload surface + logging + evidence (case floor ≥ 2 suites)
`tests/test_security.py`: disguised uploads (renamed EXE/ELF magic bytes, polyglot-ish PDF header + script payload), size limit, PII-safe logs (capture handler, scan for bytes/PII), route hygiene. Export runner mirrors case1's (`scripts/export_security_results.py` parametrized per case → `evidence/security_test_results/case2_security.json`).

### D10: Data flow

```
docintel/corpus/generate.py --seed 42 --n-invoices 20
        │ writes (deterministic)
        ▼
case2_docintel/samples/{inv_NNNN.pdf, inv_NNNN.png} + expected/{inv_NNNN.json} + manifests
        │
        ▼
docintel/pipeline.py:
  ingest ─► text (pypdf | pytesseract[optional]) ─► masking ─► provider(mock|ollama|groq)
        │                                                        │ structured 8 fields
        ▼                                                        ▼
  validation (types, cross-field) ─► statuses ─► review queue ─► results artifact
        │
        ├──► service/app.py  POST /extract (upload validation first)
        ├──► cli.py          batch mode (same core)
        └──► evaluate.py ──► outputs/evaluation.json ──► evidence/experiment_log/case2_*.json
                                    └─ security suite ──► evidence/security_test_results/case2_security.json
```

Privacy note: masking fires before the provider arrow — enforced structurally (D4) and by captured-payload tests; logs see request ids/outcomes only.

### D11: Makefile + evidence conventions
Targets: `case2-corpus`, `case2-evaluate` (mock), `case2-serve`. Evidence: evaluation + sample outputs + cost report → `evidence/experiment_log/case2_*`; security JSON → `evidence/security_test_results/`; docs in `case2_docintel/docs/`; matrix C2 rows flipped only when artifacts exist and tests pass.

## Risks / Trade-offs

- [No Tesseract on host] → `ocr_available()` probe + honest `ocr_unavailable` status; image-path evaluation runs only when OCR exists, and its absence is reported in the evaluation artifact — never simulated (D3).
- [reportlab/Pillow determinism across versions] → pins exact versions; regeneration test guards byte-stability; corpus manifest records renderer versions.
- [Mock provider "too good" (regex on clean synthetic text)] → mock accuracy will be near-perfect by design; evaluation labels it mock and the report separates mock from real-provider runs; honest gap documented in limitations.
- [Masking regexes may miss novel PII shapes] → boundary test asserts raw corpus PII never reaches provider for the corpus's known shapes; documented as a limitation for adversarial inputs.
- [Image variants via Pillow raster text may be too clean for real OCR claims] → synthetic render only; limitations state OCR results are on clean synthetic images, not scanned documents.
- [Groq calls cost money and need network] → never in tests; evidence for real-provider runs optional and clearly labeled when absent (design records the exact command to reproduce).
- [PDF text extraction with pypdf on reportlab layouts] → simple single-page text; extraction test asserts ≥6/8 fields; fallback documented if layout variation hurts extraction (tune generator variants, never expected JSON).

## Migration Plan

Greenfield within case2. Rollback = delete new modules/outputs; case1 and foundation untouched. Matrix C2 rows stay `pending` until verified (checkers enforce).

## Open Questions

None blocking. Deferrable: which real provider (if any) to run for cost evidence before the deadline — the infrastructure supports both; absence of a real run is itself honestly reported.
