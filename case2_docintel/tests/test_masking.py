"""Task 2.3 verification: masking determinism, reversibility, no raw PII."""

from docintel.masking import PATTERNS, mask_pii, unmask

TEXT = (
    "INVOICE\nInvoice Number: INV-100001\nInvoice Date: 15 Mar 2026\n"
    "Issued By: Amberline Trading\nSub-Total: 3754.80 USD\nTax: 413.03 USD\n"
    "Total: 4167.83 USD\nCurrency: USD\nDue Date: 22 Mar 2026\n"
    "Billing contact: billing@amberline-example.com\nPhone: +1-555-010-0692\n"
    "Account ref: ACC-8935-1424\n"
)


def test_masking_is_deterministic():
    a = mask_pii(TEXT)
    b = mask_pii(TEXT)
    assert a.text == b.text
    assert a.token_map == b.token_map


def test_masked_text_contains_no_raw_pii():
    result = mask_pii(TEXT)
    for kind, pattern in PATTERNS:
        assert not pattern.search(result.text), kind
    assert "billing@amberline-example.com" not in result.text
    assert "+1-555-010-0692" not in result.text
    assert "ACC-8935-1424" not in result.text


def test_reversible_via_token_map():
    result = mask_pii(TEXT)
    assert unmask(result.text, result.token_map) == TEXT


def test_business_fields_unmasked_by_design():
    result = mask_pii(TEXT)
    for business in ("INV-100001", "3754.80", "USD", "Amberline Trading"):
        assert business in result.text, business
