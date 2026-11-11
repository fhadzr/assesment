"""FastAPI prediction service (task 5.2).

App factory: create_app(model_path). Role-based output detail via X-Role
header (analyst | auditor) — a PROTOTYPE access-control demonstration, NOT
authentication (no identity verification; see docs/limitations.md).
Security posture: Pydantic validation, 1 MB body limit, redaction-only
logging, no debug routes.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError

from fraud.features import FEATURES
from fraud.predictor import Predictor
from fraud.pseudonym import pseudonymize

MAX_BODY_BYTES = 1024 * 1024  # 1 MB
VALID_ROLES = ("analyst", "auditor")

logger = logging.getLogger("fraud.service")


class RedactingFilter(logging.Filter):
    """Allow only coarse outcome lines; bodies/ids never reach the log."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name == "fraud.service" and getattr(record, "structured", False)


def _setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.addFilter(RedactingFilter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _new_request_id() -> str:
    """Opaque per-request id — never derived from payload contents."""
    import uuid

    return f"req-{uuid.uuid4().hex[:12]}"


def _log_outcome(outcome: str) -> None:
    logger.info(
        "request_id=%s outcome=%s", _new_request_id(), outcome,
        extra={"structured": True},
    )


class TransactionRequest(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=64)
    customer_id: str = Field(min_length=1, max_length=64)
    features: dict[str, float] = Field(...)


def _role(x_role: str | None = Header(default=None, alias="X-Role")) -> str:
    role = (x_role or "analyst").lower()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"unknown role '{x_role}'; expected analyst|auditor")
    return role


async def body_limited(request: Request) -> bytes:
    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="request body exceeds 1 MB limit")
    return raw


def create_app(model_path: str | Path = "case1_fraud/outputs/model_lr") -> FastAPI:
    _setup_logging()
    predictor = Predictor(Path(model_path))
    app = FastAPI(title="fraud-risk-prediction", version="1.0.0")
    app.state.predictor = predictor

    @app.post("/predict")
    async def predict(
        payload: TransactionRequest,
        role: str = Depends(_role),
        _body: bytes = Depends(body_limited),
    ):
        unknown = set(payload.features) - set(FEATURES)
        if unknown:
            raise HTTPException(status_code=422, detail=f"unknown feature(s): {sorted(unknown)}")
        missing = set(FEATURES) - set(payload.features)
        if missing:
            raise HTTPException(status_code=422, detail=f"missing feature(s): {sorted(missing)}")
        result = predictor.predict(payload.features)
        _log_outcome(f"predicted band={result['risk_band']}")
        if role == "auditor":
            result["transaction_id"] = pseudonymize(payload.transaction_id)
            result["customer_id"] = pseudonymize(payload.customer_id)
        return result

    @app.get("/model-info")
    async def model_info():
        return predictor.model_info

    return app
