"""Task 5.2 verification: FastAPI surface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fraud.data.generate import generate
from fraud.features import FEATURES, build_features, load_tables
from fraud.model.train import train_model
from fraud.service.app import MAX_BODY_BYTES, create_app

GEN = dict(
    seed=41, n_customers=40, n_transactions=800, fraud_rate=0.08, confirmed_rate=0.5,
    duplicate_rate=0.0, mismatch_rate=0.0, missing_ts_rate=0.0,
)


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    data = tmp_path_factory.mktemp("data")
    generate(type("Args", (), GEN)(), data)
    out = tmp_path_factory.mktemp("out")
    train_model(data, out / "model_lr")
    app = create_app(out / "model_lr")
    return TestClient(app), build_features(load_tables(data))


def _payload(features_frame, i=0) -> dict:
    row = features_frame.iloc[i]
    return {
        "transaction_id": "TXN-TEST-1",
        "customer_id": "CUST-TEST-1",
        "features": {f: float(row[f]) for f in FEATURES},
    }


def test_valid_prediction_200(client):
    tc, frame = client
    r = tc.post("/predict", json=_payload(frame))
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["probability"] <= 1.0
    assert body["risk_band"] in {"low", "medium", "high"}
    assert body["reasons"]


def test_model_info(client):
    tc, _ = client
    r = tc.get("/model-info")
    assert r.status_code == 200
    info = r.json()
    assert info["model_type"] == "logistic_regression"
    assert info["feature_list"] == FEATURES
    assert info["training_label"] == "blocked"


def test_invalid_feature_value_422_no_stacktrace(client):
    tc, frame = client
    bad = _payload(frame)
    bad["features"]["amount"] = "not_a_number"
    r = tc.post("/predict", json=bad)
    assert r.status_code == 422
    assert "Traceback" not in r.text


def test_missing_feature_422(client):
    tc, frame = client
    bad = _payload(frame)
    bad["features"].pop("amount")
    r = tc.post("/predict", json=bad)
    assert r.status_code == 422


def test_unknown_feature_422(client):
    tc, frame = client
    bad = _payload(frame)
    bad["features"]["mystery_feature"] = 1.0
    r = tc.post("/predict", json=bad)
    assert r.status_code == 422


def test_malformed_json_4xx_never_500(client):
    tc, _ = client
    r = tc.post(
        "/predict",
        content=b"{not json",
        headers={"Content-Type": "application/json", "X-Role": "analyst"},
    )
    assert 400 <= r.status_code < 500, r.status_code


def test_oversized_body_4xx_never_500(client):
    tc, frame = client
    payload = _payload(frame)
    payload["features"]["amount"] = float(MAX_BODY_BYTES)  # huge value but valid float
    big = json.dumps(payload) + " " * (MAX_BODY_BYTES + 100)
    r = tc.post(
        "/predict",
        content=big.encode(),
        headers={"Content-Type": "application/json", "X-Role": "analyst"},
    )
    assert 400 <= r.status_code < 500, r.status_code


def test_unknown_role_422(client):
    tc, frame = client
    r = tc.post("/predict", json=_payload(frame), headers={"X-Role": "admin"})
    assert r.status_code == 422


def test_auditor_role_gets_pseudonymous_ids(client):
    tc, frame = client
    r = tc.post("/predict", json=_payload(frame), headers={"X-Role": "auditor"})
    assert r.status_code == 200
    body = r.json()
    assert body["transaction_id"].startswith("PS-")
    assert body["customer_id"].startswith("PS-")
    assert "TXN-TEST-1" not in json.dumps(body)


def test_analyst_role_omits_ids(client):
    tc, frame = client
    r = tc.post("/predict", json=_payload(frame), headers={"X-Role": "analyst"})
    body = r.json()
    assert "transaction_id" not in body
    assert "customer_id" not in body
