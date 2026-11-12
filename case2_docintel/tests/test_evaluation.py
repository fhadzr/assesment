"""Task 5.1 verification: evaluation correctness + honest cost."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from docintel.corpus.generate import generate
from docintel.evaluate import evaluate, main as eval_main


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("case2")
    generate(42, 15, out)
    return out


def test_accuracy_computed_correctly(corpus):
    report = evaluate(corpus, "mock")
    assert report["corpus"]["n_documents"] == 15
    assert set(report["field_accuracy"]) == {
        "invoice_number", "invoice_date", "vendor_name", "subtotal", "tax", "total", "currency", "due_date",
    }
    # mock is deterministic regex on clean synthetic text: invoice_number/subtotal
    # are always recoverable; assert they're perfect, others >= 0
    assert report["field_accuracy"]["invoice_number"] == 1.0
    assert report["field_accuracy"]["subtotal"] == 1.0
    for v in report["field_accuracy"].values():
        assert v is None or 0.0 <= v <= 1.0


def test_mock_usage_labeled_zero_by_construction(corpus):
    report = evaluate(corpus, "mock")
    assert report["usage"]["tokens"] == 0
    assert report["usage"]["cost"] == 0.0
    assert report["usage"]["basis"] == "mock-zero-by-construction"


def test_error_breakdown_and_latency_recorded(corpus):
    report = evaluate(corpus, "mock")
    assert report["error_breakdown"]
    assert report["latency_ms"]["per_document"]
    assert report["latency_ms"]["mean"] is not None


def test_missing_corpus_exits_nonzero(tmp_path):
    rc = eval_main(["--corpus", str(tmp_path / "nope"), "--out", str(tmp_path / "o.json")])
    assert rc == 2


def test_real_provider_missing_metadata_null_not_zero(monkeypatch):
    # simulate a real provider response with no usage metadata via a stub provider
    from docintel import evaluate as ev

    class NoMetaProvider:
        name = "groq"

        def extract(self, masked_text):
            from docintel.providers import ExtractionOutput
            return ExtractionOutput(
                fields={f: None for f in ["invoice_number", "invoice_date", "vendor_name", "subtotal", "tax", "total", "currency", "due_date"]},
                usage={"tokens": None, "cost": None, "cost_basis": "metadata-unavailable", "provider": "groq"},
            )

    monkeypatch.setattr(ev, "make_provider", lambda name, model=None: NoMetaProvider())
    report = ev.evaluate(Path("case2_docintel"), "groq")
    # after a real provider with no metadata, tokens stay accumulated-only;
    # cost must be null (never zero), basis metadata-unavailable
    assert report["usage"]["cost"] is None
    assert report["usage"]["basis"] == "metadata-unavailable"
