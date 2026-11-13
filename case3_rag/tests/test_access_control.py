"""Task 2.2 verification: ACL is structural, not prompt-deferred."""

from __future__ import annotations

import pytest

from rag.answering import build_prompt
from rag.retrieval import InvalidRoleError, retrieve

DOCS = [
    {"doc_id": "hr-000", "section": "leave_policy", "domain": "HR", "allowed_roles": ["all"],
     "content": "Annual leave entitlement is 20 days per year."},
    {"doc_id": "fin-000", "section": "audit_retention", "domain": "Finance", "allowed_roles": ["finance"],
     "content": "Financial audit records are retained for 7 years."},
    {"doc_id": "exec-000", "section": "exec_budget", "domain": "Finance", "allowed_roles": ["exec"],
     "content": "The executive budget is capped at 5 percent."},
]


def test_retrieve_excludes_disallowed_docs():
    hits = retrieve("audit retention", "hr", DOCS)
    assert all(h["doc_id"] != "fin-000" for h in hits)


def test_prompt_contains_zero_restricted_text():
    prompt, _ = build_prompt("audit retention", "hr", DOCS)
    assert "retained for 7 years" not in prompt
    assert "fin-000" not in prompt
    assert "exec budget" not in prompt


def test_invalid_role_fail_closed():
    with pytest.raises(InvalidRoleError):
        build_prompt("q", "admin", DOCS)


def test_roles_hr_finance_exec_each_filter():
    for role in ("hr", "finance", "exec"):
        hits = retrieve("audit retention", role, DOCS)
        if role == "finance":
            assert any(h["doc_id"] == "fin-000" for h in hits)
        else:
            assert all(h["doc_id"] != "fin-000" for h in hits)
