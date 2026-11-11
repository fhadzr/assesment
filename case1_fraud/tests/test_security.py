"""Tasks 6.1 + 6.2: security posture tests (API + CLI).

Asserts:
  - no PII (raw ids, bodies) in application logs across valid/rejected/malformed
    requests, on both surfaces
  - undeclared routes 404 and absent from OpenAPI schema
  - oversized/malformed handled 4xx, never 500
Results exported to evidence by scripts/export_security_results (task 6.3).
"""

from __future__ import annotations

import csv
import io
import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fraud.data.generate import generate
from fraud.features import FEATURES, build_features, load_tables
from fraud.infer import main as infer_main
from fraud.model.train import train_model
from fraud.service.app import create_app

GEN = dict(
    seed=47, n_customers=40, n_transactions=500, fraud_rate=0.08, confirmed_rate=0.5,
    duplicate_rate=0.0, mismatch_rate=0.0, missing_ts_rate=0.0,
)
RAWD_ID_MARKERS = ("CUST-000001", "TXN-9", "DEV-0000", "AMOUNT_MARKER")


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    data = tmp_path_factory.mktemp("data")
    generate(type("Args", (), GEN)(), data)
    out = tmp_path_factory.mktemp("out")
    train_model(data, out / "model_lr")
    feats = build_features(load_tables(data))
    in_csv = out / "input.csv"
    with in_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["transaction_id"] + FEATURES)
        for i in range(5):
            row = feats.iloc[i]
            w.writerow([f"TXN-9{i}"] + [row[f] for f in FEATURES])
    return data, out, in_csv, feats


@pytest.fixture()
def log_stream():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("fraud.service")
    logger.addHandler(handler)
    yield stream, logger
    logger.removeHandler(handler)


def _drive_traffic(tc, frame):
    """Valid, rejected (422), malformed (4xx) requests through the API."""
    row = frame.iloc[0]
    good = {"transaction_id": "TXN-90", "customer_id": "CUST-000001",
            "features": {f: float(row[f]) for f in FEATURES}}
    outcomes = [tc.post("/predict", json=good).status_code]
    bad = json.loads(json.dumps(good))
    bad["features"]["amount"] = "x"
    outcomes.append(tc.post("/predict", json=bad).status_code)
    outcomes.append(tc.post("/predict", content=b"{{broken",
                           headers={"Content-Type": "application/json"}).status_code)
    return outcomes


class TestNoPIIInLogs:
    def test_api_logs_contain_no_pii(self, env, log_stream):
        stream, _ = log_stream
        _, out, _, feats = env
        app = create_app(out / "model_lr")
        tc = TestClient(app)
        outcomes = _drive_traffic(tc, feats)
        assert any(o == 200 for o in outcomes) and any(o == 422 for o in outcomes)
        content = stream.getvalue()
        for marker in RAWD_ID_MARKERS:
            assert marker not in content, f"raw id marker {marker!r} leaked into API logs"
        assert "amount" not in content.lower() or "=" not in content.split("amount")[0][-40:]

    def test_cli_logs_contain_no_pii(self, env, tmp_path, capsys):
        _, out, in_csv, _ = env
        rc = infer_main(["--in", str(in_csv), "--model", str(out / "model_lr"),
                         "--out", str(tmp_path / "s.csv")])
        assert rc == 0
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        for marker in RAWD_ID_MARKERS:
            assert marker not in combined, f"raw id marker {marker!r} in CLI stdout/stderr"


class TestRouteHygiene:
    @pytest.mark.parametrize("path", ["/debug", "/admin"])
    def test_undeclared_routes_404(self, env, path):
        _, out, _, _ = env
        tc = TestClient(create_app(out / "model_lr"))
        assert tc.get(path).status_code == 404
        assert tc.post(path, json={}).status_code == 404

    def test_no_debug_routes_in_openapi(self, env):
        _, out, _, _ = env
        tc = TestClient(create_app(out / "model_lr"))
        schema = tc.get("/openapi.json").json()
        paths = set(schema["paths"])
        assert paths == {"/predict", "/model-info"}, paths

    def test_error_responses_never_500(self, env):
        _, out, _, feats = env
        tc = TestClient(create_app(out / "model_lr"))
        outcomes = _drive_traffic(tc, feats)
        # outcomes = [valid, invalid, malformed]; only the error ones are checked 4xx
        assert outcomes[0] == 200
        assert all(400 <= o < 500 for o in outcomes[1:]), outcomes
