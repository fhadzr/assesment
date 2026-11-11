"""Task 1.5 verification: deterministic defect injection at configured rates."""

from __future__ import annotations

import csv
import filecmp
from pathlib import Path

from fraud.data.generate import generate

GEN = dict(
    n_customers=50, n_transactions=600, fraud_rate=0.05, confirmed_rate=0.5,
    duplicate_rate=0.05, mismatch_rate=0.03, missing_ts_rate=0.04,
)


def _rows(path: Path, name: str) -> list[dict]:
    with (path / f"{name}.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _gen(tmp_path: Path, seed: int) -> Path:
    ns = type("Args", (), {**GEN, "seed": seed})()
    out = tmp_path / "data"
    generate(ns, out)
    return out


def test_defects_reproducible_per_seed(tmp_path):
    a = _gen(tmp_path / "a", seed=11)
    b = _gen(tmp_path / "b", seed=11)
    for name in ("transactions", "devices", "logins"):
        assert filecmp.cmp(a / f"{name}.csv", b / f"{name}.csv", shallow=False), name


def test_duplicate_rate_within_tolerance(tmp_path):
    out = _gen(tmp_path, seed=21)
    rows = _rows(out, "transactions")
    seen: set[tuple] = set()
    dupes = 0
    for r in rows:
        key = tuple(sorted(r.items()))
        if key in seen:
            dupes += 1
        seen.add(key)
    empirical = dupes / len(rows)
    assert abs(empirical - 0.05) / 0.05 <= 0.20, f"empirical {empirical} vs 0.05"


def test_dangling_ids_present(tmp_path):
    out = _gen(tmp_path, seed=31)
    cust_ids = {r["customer_id"] for r in _rows(out, "customers")}
    dangling = sum(r["customer_id"] not in cust_ids for r in _rows(out, "transactions"))
    assert dangling > 0


def test_missing_timestamps_present(tmp_path):
    out = _gen(tmp_path, seed=41)
    devices = _rows(out, "devices")
    logins = _rows(out, "logins")
    missing = sum(not r["first_seen_ts"] for r in devices) + sum(not r["ts"] for r in logins)
    assert missing > 0


def test_zero_rates_produce_clean_data(tmp_path):
    ns = type("Args", (), {**GEN, "seed": 51, "duplicate_rate": 0.0, "mismatch_rate": 0.0, "missing_ts_rate": 0.0})()
    out = tmp_path / "clean"
    generate(ns, out)
    rows = _rows(out, "transactions")
    seen: set[tuple] = set()
    for r in rows:
        key = tuple(sorted(r.items()))
        assert key not in seen, "duplicates at zero rate"
        seen.add(key)
