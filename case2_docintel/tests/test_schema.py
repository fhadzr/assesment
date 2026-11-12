"""Task 1.2 verification: schema registry completeness."""

from docintel.corpus.schema import (
    CURRENCIES,
    DATE_FORMATS,
    FIELD_NAMES,
    FIELDS,
    INVARIANTS,
    LABEL_VARIANTS,
    MASKABLE_PII_FIELDS,
)

REQUIRED_EIGHT = {
    "invoice_number", "invoice_date", "vendor_name", "subtotal",
    "tax", "total", "currency", "due_date",
}
VALID_TYPES = {"str", "iso-date", "decimal", "currency"}
VALID_PII = {"business", "identifier"}


def test_exactly_the_eight_required_fields():
    assert set(FIELD_NAMES) == REQUIRED_EIGHT and len(FIELDS) == 8


def test_every_field_documented_and_typed():
    for f in FIELDS:
        assert f.type in VALID_TYPES, f.name
        assert f.pii in VALID_PII, f.name
        assert len(f.meaning) > 15, f.name


def test_label_variants_cover_every_field():
    assert set(LABEL_VARIANTS) == REQUIRED_EIGHT
    for name, variants in LABEL_VARIANTS.items():
        assert len(variants) >= 3 and all(v.strip() for v in variants), name


def test_cross_field_invariants_documented():
    assert any("subtotal + tax = total" in i for i in INVARIANTS)
    assert any("invoice_date <= due_date" in i for i in INVARIANTS)


def test_maskable_pii_is_distinct_from_business_fields():
    assert not set(MASKABLE_PII_FIELDS) & set(FIELD_NAMES)
    assert len(MASKABLE_PII_FIELDS) == 3


def test_variation_config_exists():
    assert len(DATE_FORMATS) == 3
    assert len(CURRENCIES) >= 3
