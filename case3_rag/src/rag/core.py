"""Shared answering core (tasks 3.4, 4.1, 4.2).

Composes retrieval → prompt → provider → citation post-filter → refusal.

The post-filter enforces citation integrity: a citation is kept only if its
(doc_id, section) is in the retrieved permitted hit set. A format-valid but
unretrieved citation is stripped. If the answer becomes unsupported (empty or
all citations stripped), the result is the generic refusal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rag.answering import SYSTEM_PROMPT, build_prompt, extract_citations, make_provider
from rag.retrieval import InvalidRoleError

GENERIC_REFUSAL = "REFUSAL: insufficient permitted evidence"


@dataclass
class AnswerResult:
    answer: str
    citations: list[str]
    refusal: bool
    hits: list[dict]
    usage: dict = field(default_factory=dict)
    error: str | None = None


def _is_refusal(text: str) -> bool:
    return text.strip().upper().startswith("REFUSAL")


def ask(question: str, role: str, docs: list[dict], provider_name: str = "mock", k: int = 3, **provider_kwargs) -> AnswerResult:
    try:
        prompt, hits = build_prompt(question, role, docs, k=k)
    except InvalidRoleError as exc:
        return AnswerResult(answer="", citations=[], refusal=True, hits=[], error=str(exc))

    provider = make_provider(provider_name, **provider_kwargs)
    raw = provider.answer(prompt, hits, question)

    # citation post-filter: keep only citations in the retrieved permitted set
    hit_pairs = {(h["doc_id"], h["section"]) for h in hits}
    kept = []
    for c in raw.get("citations", []):
        # extract (doc_id, section) from the "[doc_id § section]" string
        parsed = extract_citations(c)
        if not parsed:
            continue
        doc_id, section = parsed.pop()
        if (doc_id, section) in hit_pairs:
            kept.append(c)
    answer = raw.get("answer", "").strip()

    # refusal if unsupported
    if _is_refusal(answer) or (not answer) or (not hits):
        return AnswerResult(answer=GENERIC_REFUSAL, citations=[], refusal=True, hits=hits, usage=raw.get("usage", {}))

    return AnswerResult(answer=answer, citations=kept, refusal=False, hits=hits, usage=raw.get("usage", {}))
