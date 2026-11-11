"""Task 2.4: automated leakage tests.

Two guarantees:
1. Perturbing strictly-future rows never changes earlier transactions'
   feature vectors.
2. A deliberately leaky implementation (full-dataset statistic) IS detected
   by the same check — proving the test has teeth.
"""

from __future__ import annotations

import numpy as np
import pytest

from fraud.data.generate import generate
from fraud.features import FEATURES, build_features, load_tables

GEN = dict(
    seed=17, n_customers=30, n_transactions=500, fraud_rate=0.06, confirmed_rate=0.5,
    duplicate_rate=0.0, mismatch_rate=0.0, missing_ts_rate=0.0,
)


def _build(tmp_path):
    out = tmp_path / "data"
    generate(type("Args", (), GEN)(), out)
    tables = load_tables(out)
    return tables, build_features(tables)


def _perturb_future(tables, df, frac=0.3):
    """Randomly change amounts of the latest `frac` of transactions (by ts).

    Returns (future_ids, df_before, df_after, tables_perturbed).
    """
    tx = tables["transactions"].copy()
    tx_sorted = tx.sort_values("ts", kind="mergesort")
    n_future = int(len(tx_sorted) * frac)
    future_ids = set(tx_sorted["transaction_id"].tail(n_future))
    tx["amount"] = [
        str(round(float(a) * 5.0 + 123.0, 2)) if tid in future_ids else a
        for tid, a in zip(tx["transaction_id"], tx["amount"])
    ]
    tables2 = dict(tables)
    tables2["transactions"] = tx
    return future_ids, df, build_features(tables2), tables2


def test_future_perturbation_leaves_earlier_features_unchanged(tmp_path):
    tables, df = _build(tmp_path)
    future_ids, df_before, df_after, _ = _perturb_future(tables, df)
    check = df_before.set_index("transaction_id").loc[lambda d: ~d.index.isin(future_ids)]
    after = df_after.set_index("transaction_id").loc[check.index]
    X1 = check[FEATURES].to_numpy()
    X2 = after[FEATURES].to_numpy()
    np.testing.assert_array_equal(X1, X2, err_msg="features reacted to strictly-future rows")


def test_perturbation_actually_changed_future_rows(tmp_path):
    """Guard: the perturbation must be non-trivial, or the test above proves nothing."""
    tables, df = _build(tmp_path)
    future_ids, df_before, df_after, _ = _perturb_future(tables, df)
    before = df_before.set_index("transaction_id").loc[list(future_ids)]
    after = df_after.set_index("transaction_id").loc[list(future_ids)]
    assert not np.array_equal(before[FEATURES].to_numpy(), after[FEATURES].to_numpy())


def test_deleting_future_rows_leaves_earlier_features_unchanged(tmp_path):
    tables, df = _build(tmp_path)
    tx = tables["transactions"].sort_values("ts", kind="mergesort")
    n_future = int(len(tx) * 0.3)
    future_ids = set(tx["transaction_id"].tail(n_future))
    tables2 = dict(tables)
    tables2["transactions"] = tables["transactions"][
        ~tables["transactions"]["transaction_id"].isin(future_ids)
    ]
    df2 = build_features(tables2)
    idx = df.set_index("transaction_id").index.difference(list(future_ids))
    X1 = df.set_index("transaction_id").loc[idx][FEATURES].to_numpy()
    X2 = df2.set_index("transaction_id").loc[idx][FEATURES].to_numpy()
    np.testing.assert_array_equal(X1, X2)


# ---- deliberately leaky variant: must be CAUGHT ----


def _build_leaky_full_dataset_mean(tables):
    """Leaky feature: z-score against the FULL dataset mean (uses the future)."""
    import pandas as pd

    tx = tables["transactions"].copy()
    tx["amount"] = tx["amount"].astype(float)
    full_mean = tx["amount"].mean()  # <-- leaks: includes rows after T
    full_std = tx["amount"].std()
    tx["amount_z_vs_history"] = (tx["amount"] - full_mean) / (full_std + 1e-6)
    return tx


def test_leaky_full_dataset_statistic_is_detected(tmp_path):
    tables, df = _build(tmp_path)
    leaky = _build_leaky_full_dataset_mean(tables).set_index("transaction_id")
    # perturb future and rebuild the leaky variant
    future_ids, _, _, tables_perturbed = _perturb_future(tables, df)
    leaky2 = _build_leaky_full_dataset_mean(tables_perturbed).set_index("transaction_id")
    earlier = [i for i in df["transaction_id"] if i not in future_ids]
    before = leaky.loc[earlier, "amount_z_vs_history"].to_numpy()
    after = leaky2.loc[earlier, "amount_z_vs_history"].to_numpy()
    changed = int((~np.isclose(before, after)).sum())
    assert changed > 0, (
        "leakage detector failed: a full-dataset-statistic feature did not react "
        f"to future perturbation (would have masked leakage); {changed} of {len(earlier)} changed expected > 0"
    )
