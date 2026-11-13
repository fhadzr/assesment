"""Task 3.1 verification: grounded answering + refusal."""

from __future__ import annotations

from rag.answering import MockProvider, build_prompt

DOCS = [
    {"doc_id": "hr-000", "section": "leave_policy", "domain": "HR", "allowed_roles": ["all"],
     "content": "Annual leave entitlement is 20 days per year for all employees."},
    {"doc_id": "fin-000", "section": "audit_retention", "domain": "Finance", "allowed_roles": ["finance"],
     "content": "Financial audit records are retained for 7 years per regulation."},
]


def test_answerable_returns_answer_and_citations():
    prompt, hits = build_prompt("annual leave entitlement", "hr", DOCS)
    out = MockProvider().answer(prompt, hits, "annual leave entitlement")
    assert out["answer"]
    assert "REFUSAL" not in out["answer"]
    assert out["citations"] == ["[hr-000 § leave_policy]"]


def test_unanswerable_refuses():
    prompt, hits = build_prompt("pet insurance policy", "hr", DOCS)
    out = MockProvider().answer(prompt, hits, "pet insurance policy")
    assert out["answer"].startswith("REFUSAL")


def test_restricted_refuses():
    prompt, hits = build_prompt("audit retention", "hr", DOCS)  # fin-000 is finance-only
    out = MockProvider().answer(prompt, hits, "audit retention")
    assert out["answer"].startswith("REFUSAL")
    assert "7 years" not in out["answer"]


def test_citations_subset_of_retrieved_set():
    prompt, hits = build_prompt("annual leave", "hr", DOCS)
    out = MockProvider().answer(prompt, hits, "annual leave")
    hit_pairs = {(h["doc_id"], h["section"]) for h in hits}
    for c in out["citations"]:
        assert c.strip("[]").replace(" § ", " ")  # format sanity
        doc_id = c[1:c.index(" § ")]
        section = c[c.index(" § ") + 3:-1]
        assert (doc_id, section) in hit_pairs


def test_mock_usage_zero_by_construction():
    prompt, hits = build_prompt("annual leave", "hr", DOCS)
    out = MockProvider().answer(prompt, hits, "annual leave")
    assert out["usage"]["cost_basis"] == "mock-zero-by-construction"
    assert out["usage"]["tokens"] == 0
