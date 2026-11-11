"""Seeded synthetic relational fraud-data generator (task 1.2, 1.3, 1.5).

Writes four tables (customers, transactions, devices, logins) as deterministic
sorted CSVs plus per-table manifests. Dual labels:
  - ground_truth_fraud: latent fraud flag (ground truth)
  - confirmed_fraud: ground truth thinned by --confirmed-rate (sparse, trusted;
    NEVER derived from blocked)
  - blocked: noisy operational proxy (legit-tail false positives + fraud misses)
Controlled defects (deterministic per seed): dangling ids, duplicate transaction
rows, missing timestamps in devices/logins.

Determinism contract: same args -> byte-identical outputs. Achieved by seeded
numpy Generator, fixed column order, sorted writes, no set/dict iteration in
row construction.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from fraud.data.schema import TABLES

GENERATOR_VERSION = "1.0.0"
CHANNELS = ["card", "transfer", "wallet"]
DEVICE_TYPES = ["mobile", "desktop", "tablet"]
COUNTRIES = ["ID", "MY", "SG", "US", "DE", "BR", "JP", "IN"]


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _tok(rng: np.random.Generator, prefix: str, n: int) -> str:
    return f"{prefix}-{rng.integers(10**6, 10**7 - 1):06d}"[: len(prefix) + 7]


def _validate(args: argparse.Namespace) -> None:
    problems = []
    if args.n_customers <= 0 or args.n_transactions <= 0:
        problems.append("--n-customers and --n-transactions must be positive integers")
    if not 0.01 <= args.fraud_rate <= 1.0:
        problems.append("--fraud-rate must be within [0.01, 1.0]")
    if not 0.0 <= args.confirmed_rate <= 0.5:
        problems.append("--confirmed-rate must be within [0.0, 0.5] (sparse trusted range)")
    for name in ("duplicate_rate", "mismatch_rate", "missing_ts_rate"):
        value = getattr(args, name)
        if not 0.0 <= value < 1.0:
            problems.append(f"--{name.replace('_', '-')} must be within [0.0, 1.0)")
    if problems:
        raise ValueError("; ".join(problems))


def generate(args: argparse.Namespace, out_dir: Path) -> dict[str, dict]:
    _validate(args)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    # ---- customers (spine) ----
    countries = rng.choice(COUNTRIES, size=args.n_customers)
    customers = []
    for i in range(args.n_customers):
        signup = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(
            minutes=int(rng.integers(0, 60 * 24 * 90))
        )
        customers.append(
            {
                "customer_id": f"CUST-{i:06d}",
                "signup_ts": _iso(signup),
                "home_country": str(countries[i]),
                "account_age_days": int((datetime(2026, 6, 1, tzinfo=timezone.utc) - signup).days),
            }
        )

    # ---- devices: 1-3 per customer ----
    devices = []
    dev_idx = 0
    for cust in customers:
        for _ in range(int(rng.integers(1, 4))):
            first_seen = datetime(2026, 1, 5, tzinfo=timezone.utc) + timedelta(
                minutes=int(rng.integers(0, 60 * 24 * 120))
            )
            devices.append(
                {
                    "device_id": f"DEV-{dev_idx:06d}",
                    "customer_id": cust["customer_id"],
                    "first_seen_ts": _iso(first_seen),
                    "device_type": str(rng.choice(DEVICE_TYPES)),
                }
            )
            dev_idx += 1

    # ---- transactions: latent fraud with shifted distributions ----
    n = args.n_transactions
    latent = rng.random(n) < args.fraud_rate
    n_fraud = int(latent.sum())
    amounts = np.where(
        latent,
        rng.lognormal(mean=6.2, sigma=0.5, size=n),          # fraud: higher amounts
        rng.lognormal(mean=4.2, sigma=0.7, size=n),
    )
    hours = np.where(
        latent,
        rng.choice([0, 1, 2, 3, 4, 22, 23], size=n),          # fraud: odd hours
        rng.choice(np.arange(24), size=n),
    )
    foreign = np.where(latent, rng.random(n) < 0.75, rng.random(n) < 0.10)
    channel = rng.choice(CHANNELS, size=n)
    cust_ix = rng.integers(0, args.n_customers, size=n)
    base_time = datetime(2026, 3, 1, tzinfo=timezone.utc)
    offsets = np.sort(rng.integers(0, 60 * 24 * 90, size=n))  # sorted -> temporal spread
    device_ix = np.array([int(rng.integers(0, len(devices))) for _ in range(n)])

    transactions = []
    for i in range(n):
        ts = base_time + timedelta(minutes=int(offsets[i]))
        country = customers[cust_ix[i]]["home_country"]
        transactions.append(
            {
                "transaction_id": f"TXN-{i:06d}",
                "customer_id": customers[cust_ix[i]]["customer_id"],
                "ts": _iso(ts),
                "amount": round(float(amounts[i]), 2),
                "hour_of_day": int(hours[i]),
                "is_foreign_merchant": bool(foreign[i] and rng.random() < 0.8) or False,
                "channel": str(channel[i]),
                "device_id": devices[device_ix[i]]["device_id"],
                "ground_truth_fraud": bool(latent[i]),
                # labels filled after (dual semantics, task 1.3)
                "blocked": False,
                "confirmed_fraud": False,
            }
        )

    # ---- dual labels (task 1.3) ----
    # confirmed_fraud: ground truth thinned by confirmed_rate (trusted, sparse)
    confirm_draw = rng.random(n) < args.confirmed_rate
    for row, is_fraud, confirmed in zip(transactions, latent, latent & confirm_draw):
        row["confirmed_fraud"] = bool(confirmed)
    # blocked: noisy proxy — catches most fraud (miss rate 20%) + false-flags
    # 2% of the legitimate tail (high-amount legit looks fraudy)
    blocked = []
    for row in transactions:
        if row["ground_truth_fraud"]:
            blocked.append(bool(rng.random() < 0.80))
        else:
            legit_flag = row["amount"] > float(np.quantile(amounts[~latent], 0.98)) and rng.random() < 0.5
            blocked.append(bool(legit_flag))
    for row, b in zip(transactions, blocked):
        row["blocked"] = b

    # ---- logins ----
    logins = []
    for i in range(n // 3):
        cust = customers[int(rng.integers(0, args.n_customers))]
        ts = base_time + timedelta(minutes=int(rng.integers(0, 60 * 24 * 90)))
        logins.append(
            {
                "login_id": f"LOG-{i:06d}",
                "customer_id": cust["customer_id"],
                "ts": _iso(ts),
                "login_ok": bool(rng.random() < 0.9),
                "device_id": devices[int(rng.integers(0, len(devices)))]["device_id"],
            }
        )

    # ---- defect injection (task 1.5, deterministic per seed) ----
    injected = {"dangling_ids": 0, "duplicate_transactions": 0, "missing_timestamps": 0}
    # dangling customer/device refs
    n_dangling = int(round(args.mismatch_rate * len(transactions)))
    for row_ix in rng.choice(len(transactions), size=n_dangling, replace=False):
        which = rng.random()
        if which < 0.5:
            transactions[int(row_ix)]["customer_id"] = f"CUST-{10**6:06d}"  # nonexistent
            injected["dangling_ids"] += 1
        else:
            transactions[int(row_ix)]["device_id"] = f"DEV-{10**6:06d}"
            injected["dangling_ids"] += 1
    n_dang_dev = int(round(args.mismatch_rate * len(devices)))
    for row_ix in rng.choice(len(devices), size=n_dang_dev, replace=False):
        devices[int(row_ix)]["customer_id"] = f"CUST-{10**6:06d}"
        injected["dangling_ids"] += 1
    n_dang_log = int(round(args.mismatch_rate * len(logins)))
    for row_ix in rng.choice(len(logins), size=n_dang_log, replace=False):
        logins[int(row_ix)]["customer_id"] = f"CUST-{10**6:06d}"
        injected["dangling_ids"] += 1
    # duplicate transaction rows: copy random rows (exact duplicates)
    n_dup = int(round(args.duplicate_rate * len(transactions)))
    dup_sources = [transactions[int(i)] for i in rng.choice(len(transactions), size=n_dup, replace=False)]
    transactions.extend(dup_sources)
    injected["duplicate_transactions"] = n_dup
    # missing timestamps in devices/logins
    n_miss_dev = int(round(args.missing_ts_rate * len(devices)))
    for row_ix in rng.choice(len(devices), size=n_miss_dev, replace=False):
        devices[int(row_ix)]["first_seen_ts"] = ""
        injected["missing_timestamps"] += 1
    n_miss_log = int(round(args.missing_ts_rate * len(logins)))
    for row_ix in rng.choice(len(logins), size=n_miss_log, replace=False):
        logins[int(row_ix)]["ts"] = ""
        injected["missing_timestamps"] += 1

    # ---- write sorted CSVs + manifests ----
    tables = {
        "customers": (customers, "customer_id"),
        "transactions": (transactions, "transaction_id"),
        "devices": (devices, "device_id"),
        "logins": (logins, "login_id"),
    }
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifests: dict[str, dict] = {}
    for name, (rows, sort_key) in tables.items():
        rows_sorted = sorted(rows, key=lambda r: r[sort_key])
        csv_path = out_dir / f"{name}.csv"
        fieldnames = [f.name for f in TABLES[name]]
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_sorted)
        manifest = {
            "table": name,
            "seed": args.seed,
            "rows": len(rows_sorted),
            "generator_version": GENERATOR_VERSION,
            "generated_at_utc": now,
        }
        if name == "transactions":
            n_gt = sum(r["ground_truth_fraud"] for r in rows_sorted)
            manifest.update(
                {
                    "fraud_rate": args.fraud_rate,
                    "confirmed_rate": args.confirmed_rate,
                    "duplicate_rate": args.duplicate_rate,
                    "mismatch_rate": args.mismatch_rate,
                    "missing_ts_rate": args.missing_ts_rate,
                    "label_prevalence": {
                        "ground_truth_fraud": n_gt / len(rows_sorted),
                        "confirmed_fraud": sum(r["confirmed_fraud"] for r in rows_sorted) / len(rows_sorted),
                        "blocked": sum(r["blocked"] for r in rows_sorted) / len(rows_sorted),
                    },
                    "defects_injected": injected,
                    "label_semantics": {
                        "blocked": "noisy operational proxy (80% fraud catch-rate + legit-tail false positives)",
                        "confirmed_fraud": "ground-truth fraud thinned by confirmed_rate; never derived from blocked",
                    },
                }
            )
        manifests[name] = manifest
        (out_dir / f"{name}_manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
    return manifests


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--n-customers", type=int, default=200)
    parser.add_argument("--n-transactions", type=int, default=10000)
    parser.add_argument("--fraud-rate", type=float, default=0.02)
    parser.add_argument("--confirmed-rate", type=float, default=0.5,
                        help="fraction of ground-truth fraud that becomes confirmed_fraud (sparse trusted)")
    parser.add_argument("--duplicate-rate", type=float, default=0.01)
    parser.add_argument("--mismatch-rate", type=float, default=0.01)
    parser.add_argument("--missing-ts-rate", type=float, default=0.01)
    parser.add_argument("--out", type=Path, default=Path("case1_fraud/data"))
    args = parser.parse_args(argv)
    try:
        manifests = generate(args, args.out)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for name, m in manifests.items():
        print(f"wrote {args.out}/{name}.csv ({m['rows']} rows, manifest ok)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
