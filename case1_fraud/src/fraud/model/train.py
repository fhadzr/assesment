"""Logistic Regression training (task 3.2) + optional HGB (task 3.3).

Trains on the `blocked` label (noisy proxy — noise assumption recorded in
metadata and cited from the dataset manifest). Deterministic: fixed
random_state, deterministic split via fraud.split, pinned sklearn version.

Optional HistGradientBoosting experiment behind --with-hgb: additive only;
writes its own artifact dir, never replaces baseline/LR outputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from fraud.features import FEATURES, build_features, load_tables
from fraud.split import split_transactions, _load_transactions, _clean_exact_duplicates

TRAIN_VERSION = "1.0.0"
RANDOM_STATE = 42


def _manifest_hash(data_dir: Path) -> tuple[str, dict]:
    raw = (data_dir / "transactions_manifest.json").read_bytes()
    return hashlib.sha256(raw).hexdigest()[:16], json.loads(raw)


def _pipeline(model: str) -> Pipeline:
    if model == "logreg":
        clf = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)
    elif model == "hgb":
        clf = HistGradientBoostingClassifier(random_state=RANDOM_STATE)
    else:
        raise ValueError(f"unknown model {model}")
    return Pipeline([("scaler", StandardScaler()), ("clf", clf)])


def train_model(data_dir: Path, out_dir: Path, model: str = "logreg") -> dict:
    manifest_hash, manifest = _manifest_hash(data_dir)

    # required schema fields present?
    import csv as _csv
    with (data_dir / "transactions.csv").open(newline="", encoding="utf-8") as f:
        header = next(_csv.reader(f))
    missing = [c for c in ("amount", "ts", "customer_id", "blocked", "confirmed_fraud") if c not in header]
    if missing:
        raise ValueError(f"dataset missing declared schema fields: {missing}")

    rows = _load_transactions(data_dir)
    rows, removed = _clean_exact_duplicates(rows)
    tables = load_tables(data_dir)
    # align feature build to dedup'd frame: rebuild transactions table from rows
    import pandas as pd
    tables["transactions"] = pd.DataFrame(rows)
    feats = build_features(tables)
    splits = split_transactions(
        feats.sort_values("ts", kind="mergesort").to_dict("records")
    )
    train_df = splits["train"]
    import numpy as np
    X = np.array([[r[f] for f in FEATURES] for r in train_df], dtype=float)
    y = np.array([1 if r["blocked"] == "True" else 0 for r in train_df])

    pipe = _pipeline(model).fit(X, y)

    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, out_dir / "model.joblib")
    meta = {
        "model_type": "logistic_regression" if model == "logreg" else "hist_gradient_boosting",
        "model_version": TRAIN_VERSION,
        "sklearn_version": sklearn.__version__,
        "feature_list": FEATURES,
        "random_state": RANDOM_STATE,
        "training_label": "blocked",
        "blocked_label_noise_assumption": {
            "fraud_catch_rate": 0.80,
            "legit_false_positive_tail": "top-2% amounts, 50% flagged",
            "source": "transactions_manifest.json label_semantics",
        },
        "dataset_manifest_hash": manifest_hash,
        "blocked_prevalence_train": float(y.mean()),
        "removed_duplicates": removed,
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "optional_experiment": model == "hgb",
    }
    (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("case1_fraud/data"))
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--model", choices=["logreg", "hgb"], default="logreg")
    parser.add_argument("--with-hgb", action="store_true", help="additionally train the optional HGB experiment")
    args = parser.parse_args(argv)

    try:
        if args.model == "logreg" or args.out is not None and "model_lr" in str(args.out):
            meta = train_model(args.data_dir, args.out or Path("case1_fraud/outputs/model_lr"), "logreg")
            print(f"wrote model_lr ({meta['model_type']}, label=blocked)")
        if args.model == "hgb" or args.with_hgb:
            meta = train_model(args.data_dir, args.out or Path("case1_fraud/outputs/model_hgb"), "hgb")
            print(f"wrote model_hgb (optional experiment)")
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
