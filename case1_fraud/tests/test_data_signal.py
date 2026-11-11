"""Task 1.4 verification: learnable signal + fraud-rate accuracy.

Uses simple point-in-time-free raw features (generation features) for the
AUC sanity check; the real point-in-time builder is validated in test_features.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from fraud.data.generate import generate

GEN = dict(
    n_customers=80, n_transactions=2000, fraud_rate=0.05, confirmed_rate=0.5,
    duplicate_rate=0.0, mismatch_rate=0.0, missing_ts_rate=0.0, seed=99,
)

FEATURES = ["amount", "hour_of_day", "is_foreign_merchant"]


def _load(tmp_path: Path) -> tuple[np.ndarray, np.ndarray]:
    out = tmp_path / "data"
    generate(type("Args", (), GEN)(), out)
    with (out / "transactions.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    X = np.array(
        [
            [float(r["amount"]), float(r["hour_of_day"]), float(r["is_foreign_merchant"] == "True")]
            for r in rows
        ]
    )
    y = np.array([r["ground_truth_fraud"] == "True" for r in rows])
    return X, y


def test_fraud_rate_accuracy(tmp_path):
    X, y = _load(tmp_path)
    empirical = y.mean()
    assert abs(empirical - 0.05) / 0.05 <= 0.20, f"empirical {empirical}"


def test_learnable_signal_auc_above_085(tmp_path):
    X, y = _load(tmp_path)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, random_state=0, stratify=y)
    clf = LogisticRegression(max_iter=1000).fit(X_tr, y_tr)
    auc = roc_auc_score(y_te, clf.predict_proba(X_te)[:, 1])
    assert auc > 0.85, f"AUC {auc:.3f} not above 0.85"


def test_at_least_two_features_separate_classes(tmp_path):
    X, y = _load(tmp_path)
    gaps = []
    for j in range(X.shape[1]):
        med_diff = abs(np.median(X[y, j]) - np.median(X[~y, j]))
        spread = np.std(X[:, j]) + 1e-9
        gaps.append(med_diff / spread)
    assert sum(g > 0.2 for g in gaps) >= 2, f"distributional gaps {gaps}"
