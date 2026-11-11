"""Join match-rate + data-quality report (task 1.6).

Reads the four generated tables, computes:
  - per-table row counts
  - join match rates: transactions->customers, devices->customers,
    logins->customers, transactions->devices, logins->devices
  - exact-duplicate transaction counts
  - missing-timestamp counts (devices.first_seen_ts, logins.ts)
  - label prevalence (all three label columns)

Writes outputs/quality_report.json. Idempotent: deduplicating then re-running
reports zero duplicates (dedup idempotence contract).
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

REPORT_VERSION = "1.0.0"

JOINS = [
    ("transactions", "customer_id", "customers", "customer_id"),
    ("devices", "customer_id", "customers", "customer_id"),
    ("logins", "customer_id", "customers", "customer_id"),
    ("transactions", "device_id", "devices", "device_id"),
    ("logins", "device_id", "devices", "device_id"),
]


def _load(data_dir: Path, table: str) -> list[dict]:
    with (data_dir / f"{table}.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _match_rate(left: list[dict], lkey: str, right: list[dict], rkey: str) -> float:
    right_keys = {r[rkey] for r in right}
    matched = sum(1 for l in left if l[lkey] in right_keys)
    return matched / len(left) if left else 0.0


def build_report(data_dir: Path, dedup: bool = False) -> dict:
    tables = {name: _load(data_dir, name) for name in ("customers", "transactions", "devices", "logins")}

    if dedup:
        seen: set[tuple] = set()
        kept: list[dict] = []
        for row in tables["transactions"]:
            key = tuple(sorted(row.items()))
            if key not in seen:
                seen.add(key)
                kept.append(row)
        tables["transactions"] = kept

    row_counts = {name: len(rows) for name, rows in tables.items()}

    match_rates = {
        f"{lt}.{lk}->{rt}.{rk}": round(_match_rate(tables[lt], lk, tables[rt], rk), 6)
        for lt, lk, rt, rk in JOINS
    }

    dup_counter = Counter(tuple(sorted(r.items())) for r in tables["transactions"])
    duplicates = sum(c - 1 for c in dup_counter.values() if c > 1)

    missing_ts = {
        "devices.first_seen_ts": sum(1 for r in tables["devices"] if not r["first_seen_ts"]),
        "logins.ts": sum(1 for r in tables["logins"] if not r["ts"]),
    }

    label_prevalence = {}
    for label in ("ground_truth_fraud", "confirmed_fraud", "blocked"):
        pos = sum(1 for r in tables["transactions"] if r[label] == "True")
        label_prevalence[label] = round(pos / len(tables["transactions"]), 6)

    return {
        "report_version": REPORT_VERSION,
        "data_dir": str(data_dir),
        "dedup_applied": dedup,
        "row_counts": row_counts,
        "join_match_rates": match_rates,
        "duplicate_transactions": duplicates,
        "missing_timestamps": missing_ts,
        "label_prevalence": label_prevalence,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("case1_fraud/data"))
    parser.add_argument("--out", type=Path, default=Path("case1_fraud/outputs/quality_report.json"))
    parser.add_argument("--dedup", action="store_true", help="report on deduplicated transactions")
    args = parser.parse_args(argv)
    report = build_report(args.data_dir, dedup=args.dedup)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print(f"  match rates: {report['join_match_rates']}")
    print(f"  duplicates: {report['duplicate_transactions']}, missing_ts: {sum(report['missing_timestamps'].values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
