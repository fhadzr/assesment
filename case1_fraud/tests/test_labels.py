"""Task 1.3 verification: dual-label semantics stay distinct."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from fraud.data.generate import generate

DEFAULTS = dict(
    seed=7, n_customers=60, n_transactions=800, fraud_rate=0.10,
    confirmed_rate=0.5, duplicate_rate=0.0, mismatch_rate=0.0, missing_ts_rate=0.0,
)


def _gen(tmp_path: Path) -> tuple[list[dict], dict]:
    ns = type("Args", (), DEFAULTS)()
    out = tmp_path / "data"
    generate(ns, out)
    with (out / "transactions.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    manifest = json.loads((out / "transactions_manifest.json").read_text())
    return rows, manifest


def test_blocked_and_confirmed_are_distinct_columns(tmp_path):
    rows, _ = _gen(tmp_path)
    assert rows[0].keys() >= {"blocked", "confirmed_fraud", "ground_truth_fraud"}


def test_some_blocked_not_confirmed(tmp_path):
    rows, _ = _gen(tmp_path)
    blocked_not_confirmed = [r for r in rows if r["blocked"] == "True" and r["confirmed_fraud"] == "False"]
    assert blocked_not_confirmed, "noisy proxy must produce blocked-but-not-confirmed rows"


def test_some_confirmed_not_blocked(tmp_path):
    rows, _ = _gen(tmp_path)
    confirmed_not_blocked = [r for r in rows if r["confirmed_fraud"] == "True" and r["blocked"] == "False"]
    assert confirmed_not_blocked, "80% catch-rate must leave confirmed fraud unblocked"


def test_confirmed_is_subset_of_ground_truth_never_fabricated(tmp_path):
    rows, _ = _gen(tmp_path)
    for r in rows:
        if r["confirmed_fraud"] == "True":
            assert r["ground_truth_fraud"] == "True", "confirmed invented outside ground truth"


def test_confirmed_count_matches_generator_ground_truth_process(tmp_path):
    rows, manifest = _gen(tmp_path)
    n_confirmed = sum(r["confirmed_fraud"] == "True" for r in rows)
    n_gt = sum(r["ground_truth_fraud"] == "True" for r in rows)
    # thinned by confirmed_rate=0.5 -> roughly half of ground truth, exact count recorded
    assert n_confirmed <= n_gt
    assert manifest["label_prevalence"]["confirmed_fraud"] == pytest_approx(n_confirmed / len(rows))


def test_manifest_documents_label_semantics(tmp_path):
    _, manifest = _gen(tmp_path)
    assert "proxy" in manifest["label_semantics"]["blocked"]
    assert "never derived from blocked" in manifest["label_semantics"]["confirmed_fraud"]


def pytest_approx(value):
    class _A:
        def __eq__(self, other):
            return abs(other - value) < 1e-9
    return _A()
