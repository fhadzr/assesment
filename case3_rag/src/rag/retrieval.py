"""ACL-first deterministic simplified TF-IDF retrieval (task 2.1).

Order of operations (design D3/D4):
  validate role → filter eligible by allowed() → compute N/df over eligible
  only → score (simplified TF-IDF) → rank → top-K.

A restricted document never enters the candidate pool nor the statistics, so it
cannot affect score/rank/prompt/citations/evidence.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

from rag.roles import CALLER_ROLES, allowed

# Version-controlled stopword list (design D3). frozenset, tested.
STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "is", "are",
    "be", "on", "at", "by", "with", "as", "from", "that", "this", "it",
    "its", "which", "who", "whom", "what", "when", "where", "how", "all",
    "any", "each", "every", "not", "no", "but", "if", "then", "than",
    "so", "will", "shall", "must", "may", "can", "should", "would", "could",
})

_PUNCT_EDGE = re.compile(r"^[^\w]+|[^\w]+$")


def tokenize(text: str) -> list[str]:
    tokens = []
    for raw in text.lower().split():
        t = _PUNCT_EDGE.sub("", raw)
        if t and t not in STOPWORDS:
            tokens.append(t)
    return tokens


class InvalidRoleError(ValueError):
    pass


def load_kb(kb_path: Path) -> list[dict]:
    docs = json.loads(kb_path.read_text(encoding="utf-8"))
    for d in docs:
        if not d.get("allowed_roles"):
            raise ValueError(f"document {d.get('doc_id', '?')} missing allowed_roles")
        if not d.get("doc_id") or not d.get("section"):
            raise ValueError(f"document missing doc_id/section: {d.get('doc_id', '?')}")
    return docs


def _sections(docs: list[dict]) -> list[dict]:
    # each doc is one section in this KB model; return a flat list of section views
    return docs


def _compute_tf(term: str, section_tokens: list[str]) -> float:
    return section_tokens.count(term) / len(section_tokens) if section_tokens else 0.0


def retrieve(query: str, role: str, docs: list[dict], k: int = 3) -> list[dict]:
    # 1. validate role (fail-closed)
    if role not in CALLER_ROLES:
        raise InvalidRoleError(f"invalid role {role!r}; valid: {list(CALLER_ROLES)}")

    # 2. filter eligible sections by ACL FIRST
    eligible = [d for d in docs if allowed(d, role)]

    # 3. compute N and df over eligible only
    eligible_tokens = [tokenize(d["content"]) for d in eligible]
    N = len(eligible)
    df: dict[str, int] = {}
    for toks in eligible_tokens:
        for t in set(toks):
            df[t] = df.get(t, 0) + 1

    # 4. score with simplified TF-IDF over unique query terms
    q_tokens = tokenize(query)
    scores = []
    for d, toks in zip(eligible, eligible_tokens):
        score = 0.0
        for t in set(q_tokens):  # duplicate query terms do not double-count
            if t in toks:
                tf = _compute_tf(t, toks)
                idf = math.log((N + 1) / (df[t] + 1)) + 1
                score += tf * idf
        scores.append((score, d))

    # 5. rank: score desc, doc_id asc, section asc
    scores.sort(key=lambda p: (-p[0], p[1]["doc_id"], p[1]["section"]))

    # 6. top-K (only authorized hits)
    return [d for _score, d in scores[:k]]
