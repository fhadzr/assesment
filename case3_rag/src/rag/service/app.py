"""FastAPI service (task 4.1). Shared core (rag.core.ask) + PII-safe logging."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag.core import ask
from rag.retrieval import InvalidRoleError, load_kb
from rag.roles import CALLER_ROLES

logger = logging.getLogger("rag.service")


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return getattr(record, "structured", False)


def _setup_logging() -> None:
    if any(getattr(h, "rag", False) for h in logger.handlers):
        return
    h = logging.StreamHandler()
    h.addFilter(RedactingFilter())
    h.rag = True
    logger.addHandler(h)
    logger.setLevel(logging.INFO)


def _log_outcome(outcome: str) -> None:
    logger.info("request_id=%s outcome=%s", f"req-{uuid.uuid4().hex[:12]}", outcome, extra={"structured": True})


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    role: str = Field(...)


def create_app(kb_path: str | Path = "case3_rag/data/kb.json", provider: str = "mock") -> FastAPI:
    _setup_logging()
    docs = load_kb(Path(kb_path))
    app = FastAPI(title="enterprise-rag-chatbot", version="1.0.0")
    app.state.docs = docs
    app.state.provider = provider

    @app.post("/ask")
    async def ask_endpoint(req: AskRequest):
        result = ask(req.question, req.role, app.state.docs, app.state.provider)
        if result.error:
            raise HTTPException(status_code=422, detail=result.error)
        _log_outcome(f"asked refusal={result.refusal}")
        return {
            "answer": result.answer,
            "citations": result.citations,
            "refusal": result.refusal,
            "hits": [{"doc_id": h["doc_id"], "section": h["section"]} for h in result.hits],
            "usage": result.usage,
        }

    @app.get("/model-info")
    async def model_info():
        return {"provider": app.state.provider, "roles": list(CALLER_ROLES)}

    return app
