"""Task 2.2 verification: chronological split invariants."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from fraud.data.generate import generate
from fraud.split import run as split_run

GEN = dict(
    seed=42, n_customers=60, n_transactions=1000, fraud_rate=0.05, confirmed_rate=0.5,
    duplicate_rate=0.0, mismatch_rate=0.0, missing_ts_rate=0.0,
)


def _gen_dir(tmp_path: Path) -> Path:
    out = tmp_path / "data"
    generate(type("Args", (), GEN)(), out)
    return out


def _rows(data_dir: Path) -> list[dict]:
    with (data_dir / "transactions.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_strict_chronological_ordering(tmp_path):
    data_dir = _gen_dir(tmp_path)
    summary = split_run(data_dir, tmp_path / "split")
    b = summary["boundaries"]
    assert b["train_max_ts"] < b["validation_min_ts"]
    assert b["validation_max_ts"] < b["test_min_ts"]


def test_split_deterministic(tmp_path):
    data_dir = _gen_dir(tmp_path)
    s1 = split_run(data_dir, tmp_path / "s1")
    s2 = split_run(data_dir, tmp_path / "s2")
    assert s1 == s2


def test_counts_match_proportions(tmp_path):
    data_dir = _gen_dir(tmp_path)
    summary = split_run(data_dir, tmp_path / "split")
    total = sum(summary["counts"].values())
    assert summary["counts"]["train"] / total == pytest.approx(0.70, abs=0.03)
    assert summary["counts"]["test"] / total == pytest.approx(0.15, abs=0.03)


def test_label_prevalence_per_split_recorded(tmp_path):
    summary = split_run(_gen_dir(tmp_path), tmp_path / "split")
    for part in ("train", "validation", "test"):
        assert set(summary["label_prevalence"][part]) == {"ground_truth_fraud", "confirmed_fraud", "blocked"}


def test_degenerate_time_range_rejected(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    # single-timestamp dataset cannot satisfy 70/15/15 quantiles
    rows = [
        {
            "transaction_id": f"TXN-{i:04d}", "customer_id": "CUST-000001", "ts": "2026-03-01T00:00:00Z",
            "amount": "10.0", "hour_of_day": "1", "is_foreign_merchant": "False", "channel": "card",
            "device_id": "DEV-000001", "ground_truth_fraud": "False", "blocked": "False", "confirmed_fraud": "False",
        }
        for i in range(50)
    ]
    import csv as _csv
    with (data_dir / "transactions.csv").open("w", newline="", encoding="utf-8") as f:
        w = _csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(ValueError):
        split_run(data_dir, tmp_path / "split")
