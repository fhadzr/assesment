"""Task 3.4 verification: shared core result shape."""

from __future__ import annotations

from rag.core import ask

DOCS = [
    {"doc_id": "hr-000", "section": "leave_policy", "domain": "HR", "allowed_roles": ["all"],
     "content": "Annual leave entitlement is 20 days per year."},
    {"doc_id": "fin-000", "section": "audit_retention", "domain": "Finance", "allowed_roles": ["finance"],
     "content": "Financial audit records are retained for 7 years."},
]


def test_shared_result_shape():
    r = ask("annual leave", "hr", DOCS)
    assert set(vars(r)) >= {"answer", "citations", "refusal", "hits", "usage"}


def test_refusal_flags_set_for_restricted():
    r = ask("audit retention", "hr", DOCS)
    assert r.refusal is True
    assert r.answer.startswith("REFUSAL")


def test_usage_metadata_present():
    r = ask("annual leave", "hr", DOCS)
    assert r.usage["provider"] == "mock"
    assert r.usage["cost_basis"] == "mock-zero-by-construction"


def test_invalid_role_returns_error_refusal():
    r = ask("q", "superuser", DOCS)
    assert r.refusal is True
    assert r.error and "invalid role" in r.error
