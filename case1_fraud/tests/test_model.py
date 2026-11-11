"""Tasks 3.1-3.3 verification: baseline, LR training, optional HGB."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pytest

from fraud.data.generate import generate
from fraud.model.baseline import RULES, persist_metadata, score_row
from fraud.model.train import train_model

GEN = dict(
    seed=23, n_customers=60, n_transactions=1200, fraud_rate=0.06, confirmed_rate=0.5,
    duplicate_rate=0.01, mismatch_rate=0.0, missing_ts_rate=0.0,
)


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("data")
    generate(type("Args", (), GEN)(), out)
    return out


# ---- baseline (3.1) ----


def test_baseline_scores_deterministic_and_bounded(data_dir, tmp_path):
    from fraud.features import FEATURES, build_features, load_tables
    tables = load_tables(data_dir)
    feats = build_features(tables)
    row = dict(zip(FEATURES, feats[FEATURES].iloc[0]))
    s1, s2 = score_row(row), score_row(row)
    assert s1 == s2 and 0.0 <= s1 <= 1.0


def test_baseline_rules_fire_on_fraudy_row():
    from fraud.features import FEATURES
    fraudy = dict(zip(FEATURES, [600.0, 2, 1.0, 1, 0, 0, 4.0, 5, 10.0, 0.5, 0.2, 3.0]))
    s = score_row(fraudy)
    assert s >= 0.8, f"fraudy row scored {s}"


def test_baseline_metadata_records_rules_and_provenance(data_dir, tmp_path):
    meta = persist_metadata(tmp_path / "model_baseline", ["f1"], "abcd1234")
    assert meta["model_type"] == "rule_based_baseline"
    assert len(meta["rules"]) == len(RULES)
    assert meta["dataset_manifest_hash"] == "abcd1234"
    assert meta["training_label"] is None


# ---- LR training (3.2) ----


def test_lr_reproducible_metrics(data_dir, tmp_path):
    m1 = train_model(data_dir, tmp_path / "m1")
    m2 = train_model(data_dir, tmp_path / "m2")
    assert m1["blocked_prevalence_train"] == m2["blocked_prevalence_train"]
    p1 = joblib.load(tmp_path / "m1" / "model.joblib")
    p2 = joblib.load(tmp_path / "m2" / "model.joblib")
    from fraud.features import FEATURES, build_features, load_tables
    tables = load_tables(data_dir)
    feats = build_features(tables)
    X = feats[FEATURES].to_numpy()[:50]
    np.testing.assert_array_equal(p1.predict_proba(X), p2.predict_proba(X))


def test_lr_provenance_fields(data_dir, tmp_path):
    meta = train_model(data_dir, tmp_path / "m")
    for field in ("model_type", "feature_list", "random_state", "training_label",
                  "blocked_label_noise_assumption", "dataset_manifest_hash", "created_at_utc"):
        assert field in meta, field
    assert meta["training_label"] == "blocked"
    assert meta["blocked_label_noise_assumption"]["source"].startswith("transactions_manifest")


def test_lr_corrupted_data_names_missing_field(tmp_path):
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    import csv
    with (bad_dir / "transactions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["transaction_id", "customer_id", "ts"])  # missing amount/blocked etc.
        w.writerow(["TXN-1", "CUST-1", "2026-03-01T00:00:00Z"])
    (bad_dir / "transactions_manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="amount"):
        train_model(bad_dir, tmp_path / "m")


# ---- optional HGB (3.3) ----


def test_hgb_is_additive_only(data_dir, tmp_path):
    train_model(data_dir, tmp_path / "model_lr", "logreg")
    train_model(data_dir, tmp_path / "model_hgb", "hgb")
    lr_meta = json.loads((tmp_path / "model_lr" / "metadata.json").read_text())
    assert lr_meta["optional_experiment"] is False
    hgb_meta = json.loads((tmp_path / "model_hgb" / "metadata.json").read_text())
    assert hgb_meta["optional_experiment"] is True
    assert (tmp_path / "model_lr" / "model.joblib").is_file(), "LR must remain"
