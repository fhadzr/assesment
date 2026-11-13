"""Task 6.1 verification: evaluation correctness + honesty."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rag.evaluate import evaluate, main as eval_main
from rag.generate_eval import generate as eval_generate
from rag.generate_kb import generate as kb_generate


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    out = tmp_path_factory.mktemp("data")
    kb_generate(42, 10, out)
    eval_generate(42, 36, out)
    return out


def test_metrics_present_and_per_label(data):
    report = evaluate(data / "eval.json", data / "kb.json", "mock")
    assert set(report["per_label"]) == {"answerable", "unanswerable", "restricted"}
    for lbl, m in report["per_label"].items():
        assert m and m["n"] > 0
        assert "recall3" in m and "citation_precision" in m and "refusal_quality" in m


def test_refusal_quality(data):
    report = evaluate(data / "eval.json", data / "kb.json", "mock")
    rq = report["refusal_quality"]
    assert rq["correct_refusal_rate"] == 1.0
    assert rq["answerable_non_refusal_rate"] == 1.0


def test_mock_zero_labeled(data):
    report = evaluate(data / "eval.json", data / "kb.json", "mock")
    assert report["provider"] == "mock"


def test_missing_dataset_exits_nonzero(tmp_path):
    rc = eval_main(["--eval", str(tmp_path / "nope.json"), "--kb", str(tmp_path / "kb.json"),
                    "--out", str(tmp_path / "o.json")])
    assert rc == 2


def test_citation_metrics_defined(data):
    report = evaluate(data / "eval.json", data / "kb.json", "mock")
    ans = report["per_label"]["answerable"]
    assert ans["citation_recall"] is not None


def test_restricted_recall_is_null_not_zero(data):
    """A.1: Recall@3 for `restricted` is N/A (null) — the expected doc is
    intentionally withheld by ACL; 0.0 must not be read as retrieval failure
    or double-counted as security success (security is correct_refusal_rate)."""
    report = evaluate(data / "eval.json", data / "kb.json", "mock")
    restricted = report["per_label"]["restricted"]
    assert restricted["recall3"] is None
    assert restricted["citation_recall"] is None


def test_metric_definitions_documented(data):
    report = evaluate(data / "eval.json", data / "kb.json", "mock")
    defs = report["metric_definitions"]
    for name in ("recall3", "citation_precision", "citation_recall",
                 "correct_refusal_rate", "answerable_non_refusal_rate", "faithfulness_heuristic"):
        assert name in defs and defs[name]


def test_latency_submillisecond_representative(data):
    """A.5: sub-ms latency is kept with decimals and displayed as '<1 ms',
    not truncated to 0.0."""
    report = evaluate(data / "eval.json", data / "kb.json", "mock")
    lat = report["latency_ms"]
    assert lat["mean"] is not None
    if lat["mean"] < 1.0:
        assert lat["display"] == "<1 ms"
        assert lat["mean"] > 0  # actual fractional value preserved
    else:
        assert lat["display"].endswith("ms")
