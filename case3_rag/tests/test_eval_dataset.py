"""Task 1.3 verification: evaluation dataset contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rag.generate_eval import MAX_Q, MIN_Q, generate
from rag.generate_kb import generate as kb_generate

LABELS = {"answerable", "unanswerable", "restricted"}


def _gen(tmp_path: Path, seed: int = 42, n: int = 36) -> list[dict]:
    kb_generate(seed, 10, tmp_path)
    generate(seed, n, tmp_path)
    return json.loads((tmp_path / "eval.json").read_text())


def test_size_and_labels(tmp_path):
    qs = _gen(tmp_path, n=36)
    assert len(qs) == 36
    assert {q["label"] for q in qs} == LABELS


def test_all_three_labels_present(tmp_path):
    qs = _gen(tmp_path)
    for lbl in LABELS:
        assert any(q["label"] == lbl for q in qs), lbl


def test_deterministic(tmp_path):
    kb_generate(3, 10, tmp_path / "da")
    kb_generate(3, 10, tmp_path / "db")
    generate(3, 36, tmp_path / "da")
    generate(3, 36, tmp_path / "db")
    assert (tmp_path / "da" / "eval.json").read_bytes() == (tmp_path / "db" / "eval.json").read_bytes()


def test_cross_role_questions(tmp_path):
    qs = _gen(tmp_path)
    docs = json.loads((tmp_path / "kb.json").read_text())
    by_id = {d["doc_id"]: d for d in docs}
    cross = 0
    for q in qs:
        if q["label"] == "restricted":
            cross += 1
            for c in q["expected_citations"]:
                doc_id = c.split(" § ")[0]
                assert q["role"] not in by_id[doc_id]["allowed_roles"]
    assert cross >= 3


@pytest.mark.parametrize("n", [MIN_Q - 1, MAX_Q + 1])
def test_out_of_range_rejected(tmp_path, n):
    with pytest.raises(ValueError, match="30"):
        generate(42, n, tmp_path)


def test_expected_citations_resolve(tmp_path):
    qs = _gen(tmp_path)
    docs = json.loads((tmp_path / "kb.json").read_text())
    by_id_section = {(d["doc_id"], d["section"]) for d in docs}
    for q in qs:
        for c in q["expected_citations"]:
            doc_id, _, section = c.partition(" § ")
            assert (doc_id, section) in by_id_section


def test_invalid_label_rejected():
    from rag.generate_eval import LABELS as L

    assert "bogus" not in L
