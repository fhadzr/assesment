"""Deterministic validation with per-field status + review routing (tasks 2.6, 2.7).

Statuses: extracted | missing | invalid | low_confidence.
Cross-field rules: subtotal + tax = total (±0.01); invoice_date <= due_date.
A review queue entry carries: document id, field name, extracted value,
validation status, and reason(s) — adjudicable without re-opening the doc.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from docintel.corpus.schema import FIELD_NAMES

FIELD_STATUSES = ("extracted", "missing", "invalid", "low_confidence")


@dataclass
class ReviewEntry:
    document_id: str
    field: str
    value: str | None
    status: str
    reason: str


def _is_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def _is_decimal(value: str) -> bool:
    try:
        Decimal(value)
        return True
    except (InvalidOperation, ValueError, TypeError):
        return False


def _is_currency(value: str) -> bool:
    return isinstance(value, str) and len(value) == 3 and value.isalpha() and value.upper() == value


def _is_invoice_number(value: str) -> bool:
    import re

    return bool(re.fullmatch(r"INV-\d{6}", value or ""))


FIELD_VALIDATOR = {
    "invoice_number": _is_invoice_number,
    "invoice_date": _is_date,
    "due_date": _is_date,
    "vendor_name": lambda v: bool(v and str(v).strip()),
    "subtotal": _is_decimal,
    "tax": _is_decimal,
    "total": _is_decimal,
    "currency": _is_currency,
}


def validate_fields(fields: dict[str, str | None], confidence: dict[str, float] | None = None,
                    confidence_threshold: float = 0.7) -> tuple[dict[str, str], list[ReviewEntry]]:
    statuses: dict[str, str] = {}
    queue: list[ReviewEntry] = []
    confidence = confidence or {}

    for name in FIELD_NAMES:
        value = fields.get(name)
        if value is None or value == "":
            statuses[name] = "missing"
            queue.append(ReviewEntry(document_id="", field=name, value=None, status="missing",
                                     reason="field not present in extraction"))
            continue
        if not FIELD_VALIDATOR[name](value):
            statuses[name] = "invalid"
            queue.append(ReviewEntry(document_id="", field=name, value=value, status="invalid",
                                     reason=f"failed {name} type/format validation"))
            continue
        if name in confidence and confidence[name] < confidence_threshold:
            statuses[name] = "low_confidence"
            queue.append(ReviewEntry(document_id="", field=name, value=value, status="low_confidence",
                                     reason=f"provider confidence {confidence[name]:.2f} below {confidence_threshold}"))
            continue
        statuses[name] = "extracted"

    # cross-field rules
    if statuses["subtotal"] == "extracted" and statuses["tax"] == "extracted" and statuses["total"] == "extracted":
        try:
            ok = abs(Decimal(fields["subtotal"]) + Decimal(fields["tax"]) - Decimal(fields["total"])) <= Decimal("0.01")
        except (InvalidOperation, ValueError, TypeError):
            ok = False
        if not ok:
            for f in ("subtotal", "tax", "total"):
                statuses[f] = "invalid"
                queue.append(ReviewEntry(document_id="", field=f, value=fields[f], status="invalid",
                                         reason="subtotal + tax != total (cross-field)"))
    if statuses["invoice_date"] == "extracted" and statuses["due_date"] == "extracted":
        if fields["invoice_date"] > fields["due_date"]:
            statuses["due_date"] = "invalid"
            queue.append(ReviewEntry(document_id="", field="due_date", value=fields["due_date"], status="invalid",
                                     reason="invoice_date after due_date"))

    return statuses, queue
