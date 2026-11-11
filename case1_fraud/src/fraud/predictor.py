"""Shared prediction core (task 5.1).

Both the FastAPI service and the CLI call this module, so their outputs agree
by construction (pinned by tests). Produces probability, risk band, and
human-readable reason codes derived from standardized-feature directions of
the trained Logistic Regression.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np

from fraud.features import FEATURES

BANDS = ((0.3, "low"), (0.7, "medium"), (2.0, "high"))

# Human-readable feature explanations: direction text used when the
# standardized contribution of the feature supports the risk score.
REASON_TEXT = {
    "amount": ("amount {value:.2f} far above the pool baseline", "amount {value:.2f} low"),
    "hour_of_day": ("transaction at odd hour {value:.0f}", "hour {value:.0f} unremarkable"),
    "is_foreign_merchant": ("foreign merchant", "domestic merchant"),
    "channel_card": ("card channel", ""),
    "channel_transfer": ("transfer channel", ""),
    "channel_wallet": ("wallet channel", ""),
    "amount_z_vs_history": ("amount {value:+.1f} std above the customer's own history (burst)", "amount within customer's usual range"),
    "prior_txn_count": ("customer with {value:.0f} prior transactions", "first observed transactions for customer"),
    "minutes_since_last_txn": ("only {value:.0f} minutes since the customer's previous transaction (velocity)", "long gap since previous transaction"),
    "prior_foreign_ratio": ("{value:.0%} of customer's history is foreign-merchant", "rarely foreign merchant in history"),
    "prior_fraud_block_rate": ("{value:.0%} of customer's history was blocked before", "no prior blocks in history"),
    "prior_login_failures_1d": ("{value:.0f} failed logins in prior 24h", "no recent failed logins"),
}


def risk_band(probability: float) -> str:
    for upper, name in BANDS:
        if probability < upper:
            return name
    return "high"


class Predictor:
    def __init__(self, model_path: Path):
        self.pipe = joblib.load(Path(model_path) / "model.joblib")
        self.metadata = json.loads((Path(model_path) / "metadata.json").read_text(encoding="utf-8"))

    def predict(self, features: dict[str, float]) -> dict:
        x = np.array([[float(features.get(f, 0.0)) for f in FEATURES]])
        probability = float(self.pipe.predict_proba(x)[0, 1])
        reasons = self._reasons(features, x)
        return {
            "probability": round(probability, 6),
            "risk_band": risk_band(probability),
            "reasons": reasons,
        }

    def _reasons(self, features: dict[str, float], x: np.ndarray) -> list[str]:
        # standardized feature values from the pipeline's scaler
        scaler = self.pipe.named_steps.get("scaler")
        z = scaler.transform(x)[0] if scaler is not None else x[0]
        clf = self.pipe.named_steps["clf"]
        coefs = clf.coef_[0]
        reasons: list[str] = []
        for i, name in enumerate(FEATURES):
            contrib = float(z[i] * coefs[i])
            if name in REASON_TEXT and abs(contrib) >= 0.25:
                up, down = REASON_TEXT[name]
                value = float(features.get(name, 0.0))
                template = up if contrib > 0 else down
                if template:
                    try:
                        reasons.append(template.format(value=value))
                    except (KeyError, ValueError):
                        reasons.append(template)
        if not reasons:
            reasons.append("no single dominant risk factor; score from combined weak signals")
        return reasons[:5]

    @property
    def model_info(self) -> dict:
        return {
            "model_type": self.metadata["model_type"],
            "model_version": self.metadata["model_version"],
            "feature_list": self.metadata["feature_list"],
            "training_label": self.metadata.get("training_label"),
        }
