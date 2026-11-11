"""Executable evaluation with the required metric set (task 4.1) and label
policy verification (task 4.2).

Per (model, label) computes: PR-AUC, precision, recall, F1, confusion matrix,
Precision@K, Recall@K (K configurable, default 100). ROC-AUC is included but
marked supplementary. Floors (PR-AUC >= 0.80, recall >= 0.70 on blocked) are
reported as pass/fail FLAGS ONLY — no data, label, or threshold manipulation
ever occurs to satisfy them.

Provenance embedded: exact command, dataset manifest hash, split reference.
Sparse-label interpretation note included in every output.
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
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from fraud.features import FEATURES, build_features, load_tables
from fraud.model.baseline import score_frame
from fraud.split import _clean_exact_duplicates, _load_transactions, split_transactions

EVAL_VERSION = "1.0.0"
DEFAULT_K = 100
SPARSITY_NOTE = (
    "Interpretation note: confirmed_fraud is sparse (n_positive can be small). "
    "With few absolute positives, PR-AUC and Precision@K are volatile: adding or "
    "removing a handful of positives can move them substantially. Treat them "
    "together with n_positive and Recall@K, not in isolation. Absolute positive "
    "counts are reported alongside every rate."
)


def _at_k(y: np.ndarray, scores: np.ndarray, k: int) -> tuple[float, float]:
    """Precision@K and Recall@K: top-k scored transactions."""
    k = min(k, len(scores))
    order = np.argsort(-scores, kind="stable")[:k]
    hits = int(y[order].sum())
    total_pos = int(y.sum())
    precision_k = hits / k if k else 0.0
    recall_k = hits / total_pos if total_pos else 0.0
    return precision_k, recall_k


def evaluate_scores(y: np.ndarray, scores: np.ndarray, k: int = DEFAULT_K) -> dict:
    pred = (scores >= 0.5).astype(int)
    p_at_k, r_at_k = _at_k(y, scores, k)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "n_positive": int(y.sum()),
        "n_total": int(len(y)),
        "pr_auc": round(float(average_precision_score(y, scores)), 6) if y.sum() else None,
        "precision": round(float(precision_score(y, pred, zero_division=0)), 6),
        "recall": round(float(recall_score(y, pred, zero_division=0)), 6),
        "f1": round(float(f1_score(y, pred, zero_division=0)), 6),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        f"precision_at_{k}": round(p_at_k, 6),
        f"recall_at_{k}": round(r_at_k, 6),
        "k": k,
        "roc_auc_supplementary": round(float(roc_auc_score(y, scores)), 6) if 0 < y.sum() < len(y) else None,
    }


def _floors(metrics: dict) -> dict:
    """Pass/fail flags only. Never enforced by manipulation."""
    return {
        "floor_pr_auc_0.80": None if metrics["pr_auc"] is None else metrics["pr_auc"] >= 0.80,
        "floor_recall_0.70": metrics["recall"] >= 0.70,
        "policy": "floors are reported as flags only; no data/threshold manipulation is performed",
    }


def run_evaluate(data_dir: Path, outputs_dir: Path, out_path: Path, k: int = DEFAULT_K,
                 command: str = "") -> dict:
    rows = _load_transactions(data_dir)
    rows, _removed = _clean_exact_duplicates(rows)
    # label-policy check (task 4.2): evaluation labels must match generated data
    # cell-for-cell — no conversion of blocked into confirmed_fraud anywhere.
    import csv as _csv
    with (data_dir / "transactions.csv").open(newline="", encoding="utf-8") as f:
        generated = {r["transaction_id"]: r for r in _csv.DictReader(f)}
    for r in rows:
        g = generated[r["transaction_id"]]
        assert r["confirmed_fraud"] == g["confirmed_fraud"], "label conversion detected!"

    tables = load_tables(data_dir)
    import pandas as pd
    tables["transactions"] = pd.DataFrame(rows)
    feats = build_features(tables)
    splits = split_transactions(feats.sort_values("ts", kind="mergesort").to_dict("records"))
    test = splits["test"]
    test_df = feats.set_index("transaction_id").loc[[r["transaction_id"] for r in test]].reset_index()
    X = test_df[FEATURES].to_numpy(dtype=float)

    manifest_hash = hashlib.sha256(
        (data_dir / "transactions_manifest.json").read_bytes()
    ).hexdigest()[:16]

    lr_dir = outputs_dir / "model_lr"
    if not lr_dir.joinpath("model.joblib").is_file():
        raise FileNotFoundError("required model artifact missing (outputs/model_lr)")

    model_scores: dict[str, np.ndarray] = {}
    baseline_meta = outputs_dir / "model_baseline" / "metadata.json"
    if baseline_meta.is_file():
        model_scores["rule_baseline"] = score_frame(test_df)
    model_scores["logistic_regression"] = joblib.load(lr_dir / "model.joblib").predict_proba(X)[:, 1]
    hgb = outputs_dir / "model_hgb" / "model.joblib"
    if hgb.is_file():
        model_scores["hist_gradient_boosting"] = joblib.load(hgb).predict_proba(X)[:, 1]

    results = {}
    for model_name, scores in model_scores.items():
        entry = {}
        for label_name in ("confirmed_fraud", "blocked"):
            y = np.array([1 if r[label_name] == "True" else 0 for r in test])
            m = evaluate_scores(y, scores, k)
            m["floor_flags"] = _floors(m)
            entry[label_name] = m
        results[model_name] = entry

    return {
        "eval_version": EVAL_VERSION,
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "command": command or "python -m fraud.model.evaluate",
        "provenance": {
            "dataset_manifest_hash": manifest_hash,
            "split_summary": "case1_fraud/outputs/split_summary.json",
            "sklearn_split": "chronological 70/15/15 via fraud.split",
        },
        "label_policy": {
            "training_label": "blocked",
            "primary_evaluation_label": "confirmed_fraud",
            "secondary_evaluation_label": "blocked",
            "no_conversion_asserted": True,
        },
        "sparse_label_interpretation_note": SPARSITY_NOTE,
        "models": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("case1_fraud/data"))
    parser.add_argument("--outputs-dir", type=Path, default=Path("case1_fraud/outputs"))
    parser.add_argument("--out", type=Path, default=Path("case1_fraud/outputs/metrics.json"))
    parser.add_argument("--k", type=int, default=DEFAULT_K)
    args = parser.parse_args(argv)
    try:
        report = run_evaluate(
            args.data_dir, args.outputs_dir, args.out, k=args.k,
            command=f"python -m fraud.model.evaluate --k {args.k}",
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}: models {list(report['models'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
