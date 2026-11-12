"""Tasks 2.6 + 2.7 verification: validation + review queue."""

from docintel.validation import ReviewEntry, validate_fields

GOOD = {
    "invoice_number": "INV-100001",
    "invoice_date": "2026-03-15",
    "vendor_name": "Amberline Trading",
    "subtotal": "3754.80",
    "tax": "413.03",
    "total": "4167.83",
    "currency": "USD",
    "due_date": "2026-03-22",
}


def test_valid_all_extracted_no_queue():
    statuses, queue = validate_fields(dict(GOOD))
    assert all(s == "extracted" for s in statuses.values())
    assert queue == []


def test_missing_field():
    bad = dict(GOOD, due_date=None)
    statuses, queue = validate_fields(bad)
    assert statuses["due_date"] == "missing"
    assert any(e.field == "due_date" and e.status == "missing" for e in queue)


def test_invalid_field_type():
    bad = dict(GOOD, invoice_number="WRONG")
    statuses, queue = validate_fields(bad)
    assert statuses["invoice_number"] == "invalid"


def test_cross_field_inconsistency():
    bad = dict(GOOD, total="1.00")
    statuses, queue = validate_fields(bad)
    assert statuses["subtotal"] == "invalid"
    assert statuses["tax"] == "invalid"
    assert statuses["total"] == "invalid"
    assert any("subtotal + tax" in e.reason for e in queue)


def test_date_order_violation():
    bad = dict(GOOD, due_date="2026-03-01")
    statuses, queue = validate_fields(bad)
    assert statuses["due_date"] == "invalid"
    assert any("invoice_date after due_date" in e.reason for e in queue)


def test_low_confidence():
    statuses, queue = validate_fields(dict(GOOD), confidence={"vendor_name": 0.5})
    assert statuses["vendor_name"] == "low_confidence"


def test_review_entry_is_self_contained():
    bad = dict(GOOD, tax=None)
    _, queue = validate_fields(bad)
    e = next(e for e in queue if e.field == "tax")
    # adjudicable without re-opening: id + field + value + status + reason
    assert {"document_id", "field", "value", "status", "reason"} <= set(vars(e))
