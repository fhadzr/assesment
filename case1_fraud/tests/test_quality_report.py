"""Task 1.6 verification: quality report correctness + dedup idempotence."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from fraud.data.generate import generate
from fraud.data.quality import build_report

GEN = dict(
    seed=5, n_customers=40, n_transactions=400, fraud_rate=0.05, confirmed_rate=0.5,
    duplicate_rate=0.03, mismatch_rate=0.02, missing_ts_rate=0.02,
)


def _gen(tmp_path: Path) -> Path:
    out = tmp_path / "data"
    generate(type("Args", (), GEN)(), out)
    return out


def _count(data_dir: Path, table: str) -> int:
    with (data_dir / f"{table}.csv").open(newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


def test_row_counts_equal_actual_sizes(tmp_path):
    data_dir = _gen(tmp_path)
    report = build_report(data_dir)
    for table, count in report["row_counts"].items():
        assert count == _count(data_dir, table), table


def test_match_rates_in_unit_interval(tmp_path):
    report = build_report(_gen(tmp_path))
    assert report["join_match_rates"]
    for join, rate in report["join_match_rates"].items():
        assert 0.0 <= rate <= 1.0, join


def test_report_consistent_with_manifest_defects(tmp_path):
    data_dir = _gen(tmp_path)
    report = build_report(data_dir)
    manifest = json.loads((data_dir / "transactions_manifest.json").read_text())
    injected_dups = manifest["defects_injected"]["duplicate_transactions"]
    assert report["duplicate_transactions"] == injected_dups
    # mismatch-rate > 0 must show up as < 1.0 transaction->customer match rate
    assert report["join_match_rates"]["transactions.customer_id->customers.customer_id"] < 1.0


def test_dedup_idempotent(tmp_path):
    data_dir = _gen(tmp_path)
    first = build_report(data_dir, dedup=True)
    assert first["duplicate_transactions"] == 0
    second = build_report(data_dir, dedup=True)
    assert first["row_counts"] == second["row_counts"]


def test_missing_ts_counts_positive_when_injected(tmp_path):
    report = build_report(_gen(tmp_path))
    assert sum(report["missing_timestamps"].values()) > 0
