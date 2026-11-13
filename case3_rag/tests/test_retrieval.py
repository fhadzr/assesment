"""Task 2.1 verification: ACL-first simplified TF-IDF retrieval."""

from __future__ import annotations

import pytest

from rag.retrieval import InvalidRoleError, STOPWORDS, load_kb, retrieve, tokenize

DOCS = [
    {"doc_id": "hr-000", "section": "leave_policy", "domain": "HR", "allowed_roles": ["all"],
     "content": "Annual leave entitlement is 20 days per year for all full-time employees."},
    {"doc_id": "hr-001", "section": "salary_bands", "domain": "HR", "allowed_roles": ["hr"],
     "content": "HR salary bands start at band 1 and rise to band 9 for directors."},
    {"doc_id": "fin-000", "section": "audit_retention", "domain": "Finance", "allowed_roles": ["finance"],
     "content": "Financial audit records are retained for 7 years per regulation."},
    {"doc_id": "exec-000", "section": "exec_budget", "domain": "Finance", "allowed_roles": ["exec"],
     "content": "The executive discretionary budget is capped at 5 percent of annual revenue."},
]


def test_top_hit_correct_on_known_query():
    hits = retrieve("How many annual leave days?", "hr", DOCS)
    assert hits[0]["doc_id"] == "hr-000"


def test_restricted_doc_excluded_from_candidate_pool():
    # finance-only doc must not appear for role hr
    hits = retrieve("audit records retention period", "hr", DOCS)
    assert all(h["doc_id"] != "fin-000" for h in hits)


def test_restricted_doc_does_not_affect_statistics():
    # adding a restricted doc must not change scores/rank of permitted docs
    base = retrieve("annual leave days", "hr", DOCS)
    extra = DOCS + [{"doc_id": "fin-001", "section": "secret", "domain": "Finance",
                     "allowed_roles": ["finance"], "content": "annual leave days secret finance"}]
    with_extra = retrieve("annual leave days", "hr", extra)
    assert [h["doc_id"] for h in base] == [h["doc_id"] for h in with_extra]


def test_unknown_role_rejected():
    with pytest.raises(InvalidRoleError):
        retrieve("x", "superuser", DOCS)
    with pytest.raises(InvalidRoleError):
        retrieve("x", "all", DOCS)  # "all" is not a selectable caller role


def test_citations_resolve():
    hits = retrieve("leave entitlement", "hr", DOCS)
    for h in hits:
        assert h["doc_id"] and h["section"]


def test_stopwords_is_frozenset_and_nonempty():
    assert isinstance(STOPWORDS, frozenset)
    assert STOPWORDS


def test_tokenize_lowercase_strip_punctuation_no_stopwords():
    toks = tokenize("The Policy, for annual leave!")
    assert toks == ["policy", "annual", "leave"]


def test_duplicate_query_terms_do_not_double_count():
    # "leave leave leave" should rank identically to "leave"
    a = retrieve("leave leave leave", "hr", DOCS)
    b = retrieve("leave", "hr", DOCS)
    assert [h["doc_id"] for h in a] == [h["doc_id"] for h in b]


def test_loader_rejects_missing_role_metadata(tmp_path):
    import json
    p = tmp_path / "kb.json"
    p.write_text(json.dumps([{"doc_id": "x", "section": "s", "content": "c"}]))
    with pytest.raises(ValueError, match="allowed_roles"):
        load_kb(p)
