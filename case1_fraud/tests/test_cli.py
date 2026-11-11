"""Task 5.4 verification: CLI inference + API/CLI agreement."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fraud.data.generate import generate
from fraud.features import FEATURES, build_features, load_tables
from fraud.infer import main as infer_main
from fraud.model.train import train_model
from fraud.service.app import create_app

GEN = dict(
    seed=43, n_customers=40, n_transactions=500, fraud_rate=0.08, confirmed_rate=0.5,
    duplicate_rate=0.0, mismatch_rate=0.0, missing_ts_rate=0.0,
)


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    data = tmp_path_factory.mktemp("data")
    generate(type("Args", (), GEN)(), data)
    out = tmp_path_factory.mktemp("out")
    train_model(data, out / "model_lr")
    feats = build_features(load_tables(data))
    # a small valid input CSV
    in_csv = out / "input.csv"
    cols = ["transaction_id"] + FEATURES
    with in_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i in range(10):
            row = feats.iloc[i]
            w.writerow([f"TXN-{i:03d}"] + [row[f] for f in FEATURES])
    return data, out, in_csv, feats


def test_valid_batch_output(env, tmp_path):
    _data, out, in_csv, _feats = env
    out_csv = tmp_path / "scored.csv"
    rc = infer_main(["--in", str(in_csv), "--model", str(out / "model_lr"), "--out", str(out_csv)])
    assert rc == 0
    with out_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 10
    for r in rows:
        assert 0.0 <= float(r["probability"]) <= 1.0
        assert r["risk_band"] in {"low", "medium", "high"}
        assert r["reasons"]


def test_malformed_csv_field_errors_no_partial_output(env, tmp_path):
    _data, out, in_csv, _feats = env
    bad = tmp_path / "bad.csv"
    with in_csv.open(newline="", encoding="utf-8") as f:
        content = f.read()
    lines = content.splitlines()
    lines[3] = lines[3].replace(lines[3].split(",")[1], "not_a_number", 1)  # row 3 amount
    bad.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out_csv = tmp_path / "should_not_exist.csv"
    rc = infer_main(["--in", str(bad), "--model", str(out / "model_lr"), "--out", str(out_csv)])
    assert rc == 2
    assert not out_csv.exists(), "partial output written despite malformed input"


def test_missing_column_rejected(env, tmp_path):
    _data, out, in_csv, _feats = env
    bad = tmp_path / "missing_col.csv"
    with in_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header = rows[0][1:]  # drop 'amount' (second column = first feature)
    del header[0]
    bad.write_text(
        ",".join(rows[0][:1] + header) + "\n" + "\n".join(",".join(r[:1] + r[2:]) for r in rows[1:]) + "\n",
        encoding="utf-8",
    )
    rc = infer_main(["--in", str(bad), "--model", str(out / "model_lr"), "--out", str(tmp_path / "o.csv")])
    assert rc == 2


def test_unknown_role_cli_error(env, tmp_path):
    _data, out, in_csv, _feats = env
    # argparse validates --role choices and exits non-zero with a clear message
    with pytest.raises(SystemExit) as excinfo:
        infer_main(["--in", str(in_csv), "--model", str(out / "model_lr"),
                    "--out", str(tmp_path / "o.csv"), "--role", "ceo"])
    assert excinfo.value.code != 0
    # the non-argparse path also rejects: run_inference direct
    from fraud.infer import run_inference
    rc = run_inference(in_csv, out / "model_lr", tmp_path / "o2.csv", role="wizard")
    assert rc == 2


def test_cli_and_api_agree(env, tmp_path):
    data, out, in_csv, feats = env
    # CLI
    out_csv = tmp_path / "cli.csv"
    rc = infer_main(["--in", str(in_csv), "--model", str(out / "model_lr"), "--out", str(out_csv)])
    assert rc == 0
    with out_csv.open(newline="", encoding="utf-8") as f:
        cli_rows = list(csv.DictReader(f))
    # API on the same rows
    app = create_app(out / "model_lr")
    tc = TestClient(app)
    for i in range(3):
        row = feats.iloc[i]
        payload = {
            "transaction_id": f"TXN-{i:03d}",
            "customer_id": "CUST-TEST",
            "features": {f: float(row[f]) for f in FEATURES},
        }
        r = tc.post("/predict", json=payload, headers={"X-Role": "analyst"})
        assert r.status_code == 200
        api_body = r.json()
        cli_row = cli_rows[i]
        assert float(cli_row["probability"]) == pytest.approx(api_body["probability"], abs=1e-9)
        assert cli_row["risk_band"] == api_body["risk_band"]
