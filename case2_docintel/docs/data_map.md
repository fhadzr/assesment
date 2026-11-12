# Case 2 Data Map

Generated from `docintel/corpus/schema.py` (the registry is authoritative).

## Eight extracted business fields

| Field | Type | PII class | Masked? | Meaning |
| --- | --- | --- | --- | --- |
| invoice_number | str | business | **no** | `INV-NNNNNN`; extractor must read it |
| invoice_date | iso-date | business | **no** | Invoice issue date (ISO yyyy-mm-dd in JSON) |
| vendor_name | str | business | **no** | Fabricated vendor name |
| subtotal | decimal | business | **no** | Pre-tax total (2dp) |
| tax | decimal | business | **no** | Tax amount (2dp) |
| total | decimal | business | **no** | Grand total (2dp); subtotal+tax=total |
| currency | currency | business | **no** | ISO-4217-style 3-letter code |
| due_date | iso-date | business | **no** | Payment due date; invoice_date ≤ due_date |

## Masked PII (present in documents, NOT among the eight fields)

| Field | Type | Masked before LLM? | Example |
| --- | --- | --- | --- |
| contact_email | str | **yes** | `billing@<vendor>-example.com` |
| contact_phone | str | **yes** | `+1-555-010-NNNN` |
| account_reference | str | **yes** | `ACC-NNNN-NNNN` |

## The masking boundary

Only these three contact-level PII shapes are masked (deterministically, via
`docintel/masking.py`) before any LLM context construction. The eight business
fields are deliberately **unmasked** because the extractor's whole job is to
read them; they are synthetic fabrications with no real-world referent. This
boundary is enforced by `tests/test_masking.py` (business fields survive
masking) and by captured-payload tests (raw PII never reaches a provider).

## Variation dimensions

- **3 layout variants** (label wording): e.g. "Invoice Number:" / "Invoice #" / "Invoice Number:"
- **3 date formats**: `%Y-%m-%d`, `%d/%m/%Y`, `%d %b %Y`
- **4 currencies**: USD, EUR, IDR, SGD
- **2 render paths**: text PDF (reportlab) and raster image (Pillow PNG)
