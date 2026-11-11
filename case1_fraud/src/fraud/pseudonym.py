"""Deterministic keyed pseudonymization (task 5.3).

blake2b keyed hash: deterministic (same id -> same pseudonym), non-reversible
without the key. The key is loaded from the FRAUD_PSEUDONYM_KEY environment
variable when set; a documented default is used otherwise.

IMPORTANT: this key is NOT treated as a secret guarding real data — the
dataset is fully synthetic. Its purpose is to demonstrate pseudonymization
discipline (raw ids never appear in outputs). Per the assessment's
"no secrets in source" rule, production usage must set FRAUD_PSEUDONYM_KEY.
"""

from __future__ import annotations

import hashlib
import os

# Default is a fixed demo key for the synthetic dataset (documented in
# docs/limitations.md + docs/conventions/security.md). Override via env var.
_DEFAULT_KEY = b"vteki-case1-demo-pseudonym-key-v1"
ENV_VAR = "FRAUD_PSEUDONYM_KEY"


def _key() -> bytes:
    return os.environ.get(ENV_VAR, "").encode() or _DEFAULT_KEY


def pseudonymize(raw_id: str) -> str:
    """Stable pseudonym: same input -> same output; different inputs differ."""
    digest = hashlib.blake2b(raw_id.encode("utf-8"), key=_key(), digest_size=8).hexdigest()
    return f"PS-{digest}"


def pseudonymize_fields(record: dict, fields: tuple[str, ...] = ("customer_id", "transaction_id", "device_id")) -> dict:
    out = dict(record)
    for f in fields:
        if f in out and out[f]:
            out[f] = pseudonymize(str(out[f]))
    return out
