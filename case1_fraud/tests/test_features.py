"""Task 2.3 verification: schema-valid vectors, no NaN into model inputs."""

from __future__ import annotations

import numpy as np

from fraud.data.generate import generate
from fraud.features import FEATURES, build_features, feature_matrix, load_tables

GEN = dict(
    seed=13, n_customers=40, n_transactions=600, fraud_rate=0.08, confirmed_rate=0.5,
    duplicate_rate=0.0, mismatch_rate=0.0, missing_ts_rate=0.05,
)


def _features(tmp_path):
    out = tmp_path / "data"
    generate(type("Args", (), GEN)(), out)
    tables = load_tables(out)
    return build_features(tables)


def test_all_feature_columns_exist(tmp_path):
    df = _features(tmp_path)
    for col in FEATURES:
        assert col in df.columns, col


def test_matrix_has_no_nan_or_inf(tmp_path):
    df = _features(tmp_path)
    X = feature_matrix(df)
    assert np.isfinite(X).all(), "NaN/Inf leaked into model inputs"


def test_labels_carried_through(tmp_path):
    df = _features(tmp_path)
    assert {"blocked", "confirmed_fraud", "ground_truth_fraud"} <= set(df.columns)


def test_first_customer_transaction_cold_start_neutral(tmp_path):
    df = _features(tmp_path)
    first = df.groupby("customer_id").first().reset_index()
    assert (first["prior_txn_count"] == 0).all()
    assert (first["amount_z_vs_history"] == 0.0).all()
