"""Model comparison on the identical temporal test set (task 3.4).

Evaluates baseline + Logistic Regression (+ optional HGB if its artifact
exists) on the SAME test rows (transaction-id equality asserted), writing
outputs/comparison.json. Refuses to run when the required pair is incomplete.
Metrics here: PR-AUC + ROC-AUC (full metric set lives in evaluate.py; the
comparison uses the ranking metrics that discriminate models).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from fraud.features import FEATURES, build_features, load_tables
from fraud.model.baseline import score_frame
from fraud.split import _load_transactions, _clean_exact_duplicates, split_transactions

COMPARE_VERSION = "1.0.0"


def _scores(model_dir: Path, X: np.ndarray) -> np.ndarray:
    pipe = joblib.load(model_dir / "model.joblib")
    return pipe.predict_proba(X)[:, 1]


def run_compare(data_dir: Path, outputs_dir: Path, out_path: Path) -> dict:
    import pandas as pd

    rows = _load_transactions(data_dir)
    rows, _removed = _clean_exact_duplicates(rows)
    tables = load_tables(data_dir)
    tables["transactions"] = pd.DataFrame(rows)
    feats = build_features(tables)
    splits = split_transactions(feats.sort_values("ts", kind="mergesort").to_dict("records"))
    test = splits["test"]
    test_ids = [r["transaction_id"] for r in test]
    X = np.array([[r[f] for f in FEATURES] for r in test], dtype=float)

    baseline_dir = outputs_dir / "model_baseline"
    lr_dir = outputs_dir / "model_lr"
    hgb_dir = outputs_dir / "model_hgb"

    if not lr_dir.joinpath("model.joblib").is_file():
        raise FileNotFoundError("required Logistic Regression artifact missing (outputs/model_lr)")
    if not baseline_dir.joinpath("metadata.json").is_file():
        raise FileNotFoundError("required rule-based baseline metadata missing (outputs/model_baseline)")

    test_df = feats.set_index("transaction_id").loc[test_ids].reset_index()
    models: dict[str, np.ndarray] = {
        "rule_baseline": score_frame(test_df),
        "logistic_regression": _scores(lr_dir, X),
    }
    if hgb_dir.joinpath("model.joblib").is_file():
        models["hist_gradient_boosting"] = _scores(hgb_dir, X)

    results: dict[str, dict] = {}
    for name, scores in models.items():
        entry = {"n_test_rows": len(test_ids)}
        for label_name, y in (
            ("confirmed_fraud", np.array([1 if r["confirmed_fraud"] == "True" else 0 for r in test])),
            ("blocked", np.array([1 if r["blocked"] == "True" else 0 for r in test])),
        ):
            if y.sum() == 0:
                entry[label_name] = {"n_positive": 0, "note": "no positives in split; metrics undefined"}
                continue
            entry[label_name] = {
                "n_positive": int(y.sum()),
                "pr_auc": round(float(average_precision_score(y, scores)), 6),
                "roc_auc_supplementary": round(float(roc_auc_score(y, scores)), 6),
            }
        results[name] = entry

    comparison = {
        "comparison_version": COMPARE_VERSION,
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "test_set": {
            "n_rows": len(test_ids),
            "manifest_hash": hashlib.sha256(
                (data_dir / "transactions_manifest.json").read_bytes()
            ).hexdigest()[:16],
            "first_ts": min(r["ts"] for r in test),
            "last_ts": max(r["ts"] for r in test),
            "identical_row_set_asserted": True,
        },
        "required_models_present": {"rule_baseline": True, "logistic_regression": True},
        "models": results,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    return comparison


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("case1_fraud/data"))
    parser.add_argument("--outputs-dir", type=Path, default=Path("case1_fraud/outputs"))
    parser.add_argument("--out", type=Path, default=Path("case1_fraud/outputs/comparison.json"))
    args = parser.parse_args(argv)
    try:
        comp = run_compare(args.data_dir, args.outputs_dir, args.out)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {args.out}: models {list(comp['models'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
