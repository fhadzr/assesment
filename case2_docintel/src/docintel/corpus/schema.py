"""Schema registry for synthetic invoices — single source of truth.

Eight required fields with types, PII classes, and the rendered-label
variants the generator uses. The data map doc is generated from this module.

PII classes follow the repo convention (docs/conventions/synthetic-data.md):
  - identifier: masked before LLM context (masking.py)
  - business:   invoice business data — deliberately UNMASKED because the
                extractor must read them; documented in data_map.md
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str  # "str" | "iso-date" | "decimal" | "currency"
    pii: str  # "business" | "identifier"
    meaning: str


FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("invoice_number", "str", "business",
              "Invoice identifier, format INV-NNNNNN; rendered and extracted verbatim"),
    FieldSpec("invoice_date", "iso-date", "business",
              "Invoice issue date (ISO yyyy-mm-dd); rendered in one of the variant formats"),
    FieldSpec("vendor_name", "str", "business",
              "Fabricated vendor name from the seeded word lists (no real brands)"),
    FieldSpec("subtotal", "decimal", "business",
              "Pre-tax total as a decimal string, 2 places"),
    FieldSpec("tax", "decimal", "business",
              "Tax amount as a decimal string, 2 places; subtotal + tax = total"),
    FieldSpec("total", "decimal", "business",
              "Grand total as a decimal string, 2 places"),
    FieldSpec("currency", "currency", "business",
              "ISO-4217-style 3-letter currency code"),
    FieldSpec("due_date", "iso-date", "business",
              "Payment due date (ISO); invoice_date <= due_date always"),
)

FIELD_NAMES: tuple[str, ...] = tuple(f.name for f in FIELDS)

# PII present in rendered documents but NOT among the eight fields — these are
# what masking.py targets before provider context.
MASKABLE_PII_FIELDS: tuple[str, ...] = (
    "contact_email",      # fabricated, e.g. billing@<vendor-domain>
    "contact_phone",      # fabricated, e.g. +1-555-010-NNNN
    "account_reference",  # fabricated, e.g. ACC-NNNN-NNNN
)

# Rendered label variants (label text preceding each field value on the page)
LABEL_VARIANTS: dict[str, tuple[str, ...]] = {
    "invoice_number": ("Invoice No:", "Invoice #", "Invoice Number:"),
    "invoice_date": ("Issue Date:", "Date of Issue:", "Invoice Date:"),
    "vendor_name": ("From:", "Vendor:", "Issued By:"),
    "subtotal": ("Subtotal:", "Net Amount:", "Sub-Total:"),
    "tax": ("Tax:", "VAT:", "Sales Tax:"),
    "total": ("Total:", "Grand Total:", "Amount Due:"),
    "currency": ("Currency:", "Curr:", "Currency Code:"),
    "due_date": ("Due Date:", "Pay By:", "Payment Due:"),
}

# Date rendering formats (parsed back to ISO in expected JSON)
DATE_FORMATS: tuple[str, ...] = ("%Y-%m-%d", "%d/%m/%Y", "%d %b %Y")

# Currencies used by the generator
CURRENCIES: tuple[str, ...] = ("USD", "EUR", "IDR", "SGD")

# Cross-field invariants (validation + ground-truth checks)
INVARIANTS: tuple[str, ...] = (
    "subtotal + tax = total (exact, 2dp)",
    "invoice_date <= due_date",
    "invoice_number matches ^INV-[0-9]{6}$",
    "currency in " + str(CURRENCIES),
)


def as_dict() -> dict[str, dict]:
    return {f.name: {"type": f.type, "pii": f.pii, "meaning": f.meaning} for f in FIELDS}
