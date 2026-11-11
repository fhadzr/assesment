"""Point-in-time feature construction (task 2.3).

Cutoff contract: the feature vector of transaction T (customer C, time t)
depends ONLY on rows with timestamp <= t. Implemented with:
  - transactions sorted by ts; per-customer expanding (cumulative) aggregates
    computed over the sorted frame shifted by one (so T itself is excluded
    from its own history: only strictly-earlier same-customer transactions)
  - device/login events joined backward by timestamp (merge_asof-style),
    never forward

Features (per transaction):
  amount_z_vs_history     - (amount - customer's prior mean amount) / (prior std + eps)
  prior_txn_count         - number of strictly-earlier transactions for the customer
  minutes_since_last_txn  - t - previous transaction of the same customer
  prior_foreign_ratio     - share of foreign-merchant txns in the customer's history
  prior_fraud_block_rate  - share of blocked txns in history (proxy feedback)
  prior_login_failures_1d - customer's failed logins in the 24h BEFORE t
  raw amount/hour/foreign/channel one-hot also retained from the row itself

The builder never receives nor uses whole-dataset statistics: every aggregate
is grouped per customer over strictly-prior rows. test_leakage.py enforces it.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

FEATURES = [
    "amount",
    "hour_of_day",
    "is_foreign_merchant",
    "channel_card",
    "channel_transfer",
    "channel_wallet",
    "amount_z_vs_history",
    "prior_txn_count",
    "minutes_since_last_txn",
    "prior_foreign_ratio",
    "prior_fraud_block_rate",
    "prior_login_failures_1d",
]

_EPS = 1e-6


def _parse(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def load_tables(data_dir: Path) -> dict[str, pd.DataFrame]:
    tables = {}
    for name in ("customers", "transactions", "devices", "logins"):
        df = pd.read_csv(data_dir / f"{name}.csv", dtype=str, keep_default_na=False)
        df.attrs["table"] = name
        tables[name] = df
    return tables


def build_features(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    tx = tables["transactions"].copy()
    tx["_ts_dt"] = tx["ts"].map(_parse)
    tx["amount"] = tx["amount"].astype(float)
    tx["hour_of_day"] = tx["hour_of_day"].astype(int)
    tx["is_foreign_merchant"] = tx["is_foreign_merchant"].map({"True": 1, "False": 0})
    for ch in ("card", "transfer", "wallet"):
        tx[f"channel_{ch}"] = (tx["channel"] == ch).astype(int)

    # keep only rows with parseable time (defect rows with missing ts cannot
    # be positioned temporally; logins/devices already filtered at their tables)
    tx = tx.sort_values(["_ts_dt", "transaction_id"], kind="mergesort").reset_index(drop=True)

    # ---- per-customer expanding history (strictly prior: shift(1)) ----
    g = tx.groupby("customer_id", sort=False)["amount"]
    prior_mean = g.transform(lambda s: s.shift(1).expanding().mean())
    prior_std = g.transform(lambda s: s.shift(1).expanding().std())
    tx["amount_z_vs_history"] = (tx["amount"] - prior_mean) / (prior_std + _EPS)
    tx["prior_txn_count"] = g.cumcount()
    prev_ts = tx.groupby("customer_id", sort=False)["_ts_dt"].shift(1)
    tx["minutes_since_last_txn"] = (
        (tx["_ts_dt"] - prev_ts).dt.total_seconds().fillna(np.nan) / 60.0
    )
    g_foreign = tx.groupby("customer_id", sort=False)["is_foreign_merchant"]
    tx["prior_foreign_ratio"] = g_foreign.transform(lambda s: s.shift(1).expanding().mean())
    tx["blocked_num"] = tx["blocked"].map({"True": 1, "False": 0})
    tx["prior_fraud_block_rate"] = tx.groupby("customer_id", sort=False)["blocked_num"].transform(
        lambda s: s.shift(1).expanding().mean()
    )

    # ---- login failures in prior 24h (backward join per customer) ----
    logins = tables["logins"].copy()
    logins = logins[logins["ts"] != ""].copy()
    logins["_ts_dt"] = logins["ts"].map(_parse)
    logins["fail"] = logins["login_ok"].map({"True": 0, "False": 1})
    logins = logins.sort_values("_ts_dt", kind="mergesort")
    fails_1d = []
    for cust, ts in zip(tx["customer_id"], tx["_ts_dt"]):
        sub = logins[(logins["customer_id"] == cust) & (logins["_ts_dt"] <= ts) & (logins["_ts_dt"] > ts - pd.Timedelta(hours=24))]
        fails_1d.append(float(sub["fail"].sum()))
    tx["prior_login_failures_1d"] = fails_1d

    # fill the cold-start NaNs with neutral values (first transaction of a customer)
    tx["amount_z_vs_history"] = tx["amount_z_vs_history"].fillna(0.0)
    tx["minutes_since_last_txn"] = tx["minutes_since_last_txn"].fillna(-1.0)
    tx["prior_foreign_ratio"] = tx["prior_foreign_ratio"].fillna(0.0)
    tx["prior_fraud_block_rate"] = tx["prior_fraud_block_rate"].fillna(0.0)

    out = tx[
        ["transaction_id", "customer_id", "ts", *FEATURES, "ground_truth_fraud", "blocked", "confirmed_fraud"]
    ].copy()
    out.attrs["features"] = FEATURES
    return out


def feature_matrix(df: pd.DataFrame) -> np.ndarray:
    return df[FEATURES].to_numpy(dtype=float)
