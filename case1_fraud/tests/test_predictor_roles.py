"""Tasks 5.1 + 5.3 verification: predictor core, pseudonymization, roles."""

from __future__ import annotations

from pathlib import Path

import pytest

from fraud.data.generate import generate
from fraud.features import FEATURES, build_features, load_tables
from fraud.model.train import train_model
from fraud.predictor import Predictor, risk_band
from fraud.pseudonym import pseudonymize, pseudonymize_fields

GEN = dict(
    seed=37, n_customers=40, n_transactions=800, fraud_rate=0.08, confirmed_rate=0.5,
    duplicate_rate=0.0, mismatch_rate=0.0, missing_ts_rate=0.0,
)


@pytest.fixture(scope="module")
def model_dir(tmp_path_factory) -> Path:
    data = tmp_path_factory.mktemp("data")
    generate(type("Args", (), GEN)(), data)
    out = tmp_path_factory.mktemp("out")
    train_model(data, out / "model_lr")
    return out / "model_lr"


@pytest.fixture()
def features_frame(tmp_path):
    data = tmp_path / "data"
    generate(type("Args", (), GEN)(), data)
    return build_features(load_tables(data))


# ---- predictor (5.1) ----


def test_reasons_are_human_readable_and_feature_named(model_dir, features_frame):
    p = Predictor(model_dir)
    row = features_frame.iloc[5]
    feats = {f: float(row[f]) for f in FEATURES}
    result = p.predict(feats)
    assert result["reasons"], "no reasons emitted"
    joined = " ".join(result["reasons"]).lower()
    assert any(word in joined for word in ("amount", "hour", "foreign", "history", "login", "merchant", "channel", "velocity", "transactions"))


def test_prediction_deterministic(model_dir, features_frame):
    p = Predictor(model_dir)
    row = features_frame.iloc[10]
    feats = {f: float(row[f]) for f in FEATURES}
    assert p.predict(feats) == p.predict(feats)


def test_probability_bounded_and_band_valid(model_dir, features_frame):
    p = Predictor(model_dir)
    for i in (0, 3, 17):
        row = features_frame.iloc[i]
        result = p.predict({f: float(row[f]) for f in FEATURES})
        assert 0.0 <= result["probability"] <= 1.0
        assert result["risk_band"] in {"low", "medium", "high"}


def test_fraudy_row_scores_higher(model_dir, features_frame):
    p = Predictor(model_dir)
    row = features_frame.iloc[0]
    base = {f: float(row[f]) for f in FEATURES}
    fraudy = dict(base, amount=900.0, amount_z_vs_history=5.0, hour_of_day=2,
                  is_foreign_merchant=1.0, prior_login_failures_1d=3.0)
    assert p.predict(fraudy)["probability"] > p.predict(base)["probability"]


# ---- pseudonymization + roles (5.3) ----


def test_pseudonym_deterministic():
    assert pseudonymize("CUST-000001") == pseudonymize("CUST-000001")


def test_pseudonym_unique_per_input():
    assert pseudonymize("CUST-000001") != pseudonymize("CUST-000002")


def test_pseudonym_fields_covers_ids():
    rec = {"customer_id": "CUST-1", "transaction_id": "TXN-1", "device_id": "DEV-1", "amount": 5.0}
    out = pseudonymize_fields(rec)
    assert out["customer_id"].startswith("PS-")
    assert out["amount"] == 5.0
    assert "CUST-1" not in str(out)


def test_risk_band_boundaries():
    assert risk_band(0.1) == "low"
    assert risk_band(0.5) == "medium"
    assert risk_band(0.9) == "high"
