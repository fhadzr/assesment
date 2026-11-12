# Case 2 Architecture — Document Intelligence

## Data flow

```
docintel/corpus/generate.py --seed 42 --n-invoices 20
        │ writes (deterministic; SOURCE_DATE_EPOCH pins PDF metadata)
        ▼
case2_docintel/samples/{inv_NNNN.pdf, inv_NNNN.png} + expected/{inv_NNNN.json} + corpus_manifest.json
        │
        ▼
docintel/core.py: extract_document(...)
        │
        ├─ ingest (docintel/pipeline.py): is_pdf / is_image (magic bytes)
        │      ├─ PDF  → extract_pdf_text (pypdf)
        │      └─ image → extract_image_text_ocr (pytesseract; ocr_available() probe)
        │
        ├─ mask_pii (docintel/masking.py): email/phone/account → «PII_N» + token map
        │      (business fields — amounts, dates, invoice #, vendor — stay unmasked)
        │
        ├─ provider.extract (docintel/providers.py): mock | ollama | groq
        │      (masked text only; real usage metadata when available)
        │
        ├─ validate (docintel/validation.py): types + cross-field + confidence
        │      → per-field status + review queue (id/field/value/status/reason)
        │
        ▼
ExtractionResult (docintel/core.py)
        ├──► service/app.py  POST /extract (upload validation first)
        ├──► cli.py          batch mode (same core)
        └──► evaluate.py ──► outputs/evaluation.json ──► evidence/experiment_log/case2_*.json
                 └─ security suite ──► evidence/security_test_results/case2_security.json
```

## Module inventory

| Module | Responsibility |
| --- | --- |
| `docintel/corpus/schema.py` | Eight-field registry + label/date/currency variants + invariants |
| `docintel/corpus/generate.py` | Seeded PDF+image corpus + expected JSON + manifests |
| `docintel/pipeline.py` | Ingest + PDF text / OCR extraction + `ocr_available()` probe |
| `docintel/masking.py` | Deterministic PII masking + local token map |
| `docintel/providers.py` | mock / ollama / groq providers + usage metadata contract |
| `docintel/validation.py` | Field validation + statuses + review entries |
| `docintel/core.py` | Shared `extract_document` composing all stages |
| `docintel/service/app.py` | FastAPI app factory + upload validation + PII-safe logging |
| `docintel/cli.py` | Batch CLI on the same core |
| `docintel/evaluate.py` | Executable evaluation + honest token/cost reporting |
