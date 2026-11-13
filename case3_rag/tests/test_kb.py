"""Task 1.2 verification: KB generation contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rag.generate_kb import MAX_DOCS, MIN_DOCS, generate

VOCAB = {"all", "hr", "finance", "exec"}


def _gen(tmp_path: Path, seed: int = 42, n: int = 10) -> list[dict]:
    generate(seed, n, tmp_path)
    return json.loads((tmp_path / "kb.json").read_text())


def test_size_honored_and_all_domains(tmp_path):
    docs = _gen(tmp_path, n=12)
    assert len(docs) == 12
    domains = {d["domain"] for d in docs}
    assert domains == {"HR", "IT", "Finance", "Legal"}


def test_deterministic_regeneration(tmp_path):
    generate(7, 10, tmp_path / "a")
    generate(7, 10, tmp_path / "b")
    assert (tmp_path / "a" / "kb.json").read_bytes() == (tmp_path / "b" / "kb.json").read_bytes()


def test_different_seed_differs(tmp_path):
    generate(1, 10, tmp_path / "a")
    generate(2, 10, tmp_path / "b")
    a = json.loads((tmp_path / "a" / "kb.json").read_text())
    b = json.loads((tmp_path / "b" / "kb.json").read_text())
    assert [d["content"] for d in a] != [d["content"] for d in b]


@pytest.mark.parametrize("n", [MIN_DOCS - 1, MAX_DOCS + 1])
def test_out_of_range_rejected(tmp_path, n):
    with pytest.raises(ValueError, match="8"):
        generate(42, n, tmp_path)


def test_role_vocabulary_and_required_fields(tmp_path):
    docs = _gen(tmp_path)
    for d in docs:
        assert {"doc_id", "section", "content", "domain", "allowed_roles", "metadata"} <= set(d)
        assert d["allowed_roles"] and set(d["allowed_roles"]) <= VOCAB
        assert d["content"].strip()


def test_restricted_docs_per_role(tmp_path):
    docs = _gen(tmp_path)
    for role in ("hr", "finance", "exec"):
        restricted = [d for d in docs if role in d["allowed_roles"] and "all" not in d["allowed_roles"]]
        assert restricted, f"no doc restricted to {role}"


def test_injection_doc_present_and_flagged(tmp_path):
    docs = _gen(tmp_path)
    flagged = [d for d in docs if d["metadata"]["contains_prompt_injection"]]
    assert flagged
    assert any("Ignore all previous instructions" in d["content"] for d in flagged)
    # injection does not alter metadata semantics: allowed_roles still from generator
    for d in flagged:
        assert set(d["allowed_roles"]) <= VOCAB


def test_missing_role_metadata_rejected(tmp_path):
    # the corpus validator (rag/kb_load, implemented with retrieval) must reject
    # a doc lacking allowed_roles; here we assert the generator always emits it,
    # and the loader-level check is covered in test_retrieval.py
    docs = _gen(tmp_path)
    assert all("allowed_roles" in d and d["allowed_roles"] for d in docs)
