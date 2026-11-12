"""Deterministic PII masking before LLM context (task 2.3).

Replaces fabricated-but-personal-looking values (emails, phones, account
references) with «PII_N» tokens; returns masked text + a local token map so
the pipeline can restore values in-process. The map is NEVER serialized into
provider context. Business fields (amounts, dates, invoice number) are
deliberately left unmasked — the extractor must read them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

PATTERNS: list[tuple[str, re.Pattern]] = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"\+\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("account_reference", re.compile(r"\bACC-\d{4}-\d{4}\b")),
]


@dataclass
class MaskResult:
    text: str
    token_map: dict[str, str] = field(default_factory=dict)  # token -> original


def mask_pii(text: str) -> MaskResult:
    out = text
    token_map: dict[str, str] = {}
    counter = 0
    for kind, pattern in PATTERNS:
        for match in pattern.finditer(out):
            raw = match.group(0)
            token = f"«PII_{counter}»"
            token_map[token] = raw
            out = out.replace(raw, token, 1)
            counter += 1
    return MaskResult(text=out, token_map=token_map)


def unmask(text: str, token_map: dict[str, str]) -> str:
    out = text
    for token, original in token_map.items():
        out = out.replace(token, original)
    return out
