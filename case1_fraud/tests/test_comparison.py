"""Task 3.4 verification: comparison on identical test set."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fraud.data.generate import generate
from fraud.model.baseline import persist_metadata
from fraud.model.compare import run_compare
from fraud.model.train import train_model
from fraud.features import FEATURES

GEN = dict(
    seed=29, n_customers=60, n_transactions=1500, fraud_rate=0.06, confirmed_rate=0.5,
    duplicate_rate=0.01, mismatch_rate=0.0, missing_ts_rate=0.0,
)


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    data_dir = tmp_path_factory.mktemp("data")
    generate(type("Args", (), GEN)(), data_dir)
    out = tmp_path_factory.mktemp("out")
    import hashlib
    mh = hashlib.sha256((data_dir / "transactions_manifest.json").read_bytes()).hexdigest()[:16]
    persist_metadata(out / "model_baseline", FEATURES, mh)
    train_model(data_dir, out / "model_lr")
    return data_dir, out


def test_comparison_contains_both_required_models(trained, tmp_path):
    data_dir, out = trained
    comp = run_compare(data_dir, out, tmp_path / "comparison.json")
    assert {"rule_baseline", "logistic_regression"} <= set(comp["models"])


def test_same_test_rows_across_models(trained, tmp_path):
    data_dir, out = trained
    comp = run_compare(data_dir, out, tmp_path / "comparison.json")
    n = comp["test_set"]["n_rows"]
    for name, entry in comp["models"].items():
        assert entry["n_test_rows"] == n, name


def test_test_set_manifest_recorded(trained, tmp_path):
    data_dir, out = trained
    comp = run_compare(data_dir, out, tmp_path / "comparison.json")
    assert comp["test_set"]["manifest_hash"]
    assert comp["test_set"]["identical_row_set_asserted"] is True


def test_missing_lr_exits_nonzero(trained, tmp_path):
    data_dir, out = trained
    empty = tmp_path / "empty_out"
    empty.mkdir()
    import hashlib
    mh = hashlib.sha256((data_dir / "transactions_manifest.json").read_bytes()).hexdigest()[:16]
    persist_metadata(empty / "model_baseline", FEATURES, mh)
    from fraud.model.compare import main as compare_main
    rc = compare_main([
        "--data-dir", str(data_dir), "--outputs-dir", str(empty),
        "--out", str(tmp_path / "c2.json"),
    ])
    assert rc == 2


def test_hgb_additive_in_comparison(trained, tmp_path):
    data_dir, out = trained
    before = run_compare(data_dir, out, tmp_path / "before.json")
    train_model(data_dir, out / "model_hgb", "hgb")
    after = run_compare(data_dir, out, tmp_path / "after.json")
    # required blocks unchanged
    for m in ("rule_baseline", "logistic_regression"):
        assert before["models"][m] == after["models"][m], m
    assert "hist_gradient_boosting" in after["models"]
