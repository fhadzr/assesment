# Case 3 Architecture — Enterprise RAG Chatbot

## Data flow

```
rag/generate_kb.py --seed 42 --n-docs 10 ──► case3_rag/data/kb.json + kb_manifest.json
rag/generate_eval.py --seed 42 --n-questions 36 ──► case3_rag/data/eval.json + eval_manifest.json
        │
        ▼
rag/core.py  ask()
        │  ① malicious-query gate: clearly malicious prompt-injection queries
        │     → GENERIC_REFUSAL before retrieval/provider (denylist; see below)
        ▼
rag/retrieval.py  retrieve(query, role, k=3)
        │  validate role (fail-closed) → filter eligible by allowed() →
        │  compute N/df over eligible only → simplified TF-IDF → rank → top-K
        ▼
rag/answering.py  build_prompt(sanitized permitted hits) → provider(mock|ollama|groq)
        │  ② sanitize_content(): injection sentences stripped from hit content
        │     BEFORE any provider sees them (content-based, metadata-independent);
        │     instructions-only hits dropped; context wrapped in
        │     <untrusted_documents> framing (untrusted data, never instructions)
        │  MockProvider: grounded sentence selection (≥2 content-token overlap),
        │     never grounding on an injection-pattern sentence
        ▼
rag/core.py  citation post-filter → refusal if unsupported
        │  ③ output safeguard: if ANY sentence of the answer is an injection
        │     directive (start/middle/end of a multi-sentence answer), the
        │     whole answer → GENERIC_REFUSAL (provider-independent,
        │     sentence-scoped so benign sentences cannot combine into a match)
        │  ④ citation enforcement: a substantive answer requires ≥1 citation
        │     that survived the post-filter; otherwise → GENERIC_REFUSAL with
        │     empty citations (never an uncited substantive answer)
        ├──► rag/service/app.py  POST /ask (role enum, PII-safe logging)
        ├──► rag/cli.py          batch over eval.json (same core)
        └──► rag/evaluate.py ──► outputs/evaluation.json ──► evidence/experiment_log/case3_*.json
                 └─ security suite ──► evidence/security_test_results/case3_security.json
```

## Injection-hardening layers (rag-injection-hardening change)

Runtime API verification found that a malicious query could make the mock
provider return the injected directive sentence as the answer (token overlap,
not intent). The fix is layered; ACL-first retrieval is untouched:

| Layer | Where | What it guarantees |
| --- | --- | --- |
| ① Query gate | `rag/core.py ask()` | Clearly malicious queries (instruction-override AND exfiltration intent, conjunction to avoid over-refusal) get the generic refusal before retrieval/provider execution. Same marker as other refusals → no probing oracle. |
| ② Context sanitization | `rag/answering.py build_prompt()` | Injection sentences are stripped from every retrieved hit before it reaches any provider; legitimate sentences from the same document survive. Detection is content-based — `metadata.contains_prompt_injection` is never trusted. |
| ③ Output safeguard | `rag/core.py ask()` | If ANY sentence of a provider answer is itself an injection directive — start, middle, or end of a multi-sentence answer — the whole answer becomes the generic refusal (never partially returned). Sentence-scoped: a benign sentence cannot combine with a later one into a cross-sentence match. |
| ④ Citation enforcement | `rag/core.py ask()` | A substantive answer is returned only with ≥1 citation that survived the post-filter (resolved to a retrieved permitted hit); empty or all-invalid citations → generic refusal with empty citations. |
| (structural, pre-existing) | ACL-first retrieval + citation post-filter | Restricted docs never enter the candidate pool, prompt, or citations — this is what held during the finding and is unchanged. |

**Provider framing (Groq):** the assembled prompt is sent to the Groq
chat-completions API as two messages — fixed instruction text with the
`system` role, untrusted passages + question with the `user` role
(`groq_messages()`). A prompt without the framing delimiter degrades to a
single user message, so the `answer(prompt, hits, query)` contract is
unchanged; Ollama and the mock provider are unaffected. This is structural
framing that mirrors the prompt's untrusted-data boundary at the API level —
it does **not** guarantee resistance to prompt injection (see the security
boundary below and `docs/limitations.md`).

**Security boundary (explicit):** the ①/②/③ detectors are a high-confidence
denylist over known phrasings. Obfuscated, translated, or novel payloads may
evade them; such payloads remain constrained by ACL-first retrieval,
sanitization, the citation post-filter, and the output safeguard. Mock-provider
tests pin these deterministic controls only — they are **not** real-LLM
security validation (see `docs/limitations.md`).

## Module inventory

| Module | Responsibility |
| --- | --- |
| `rag/generate_kb.py` | Seeded synthetic KB (8–12 role-gated docs + injection doc) |
| `rag/generate_eval.py` | Seeded eval dataset (36 labeled questions + citations) |
| `rag/roles.py` | `allowed(doc, role)` predicate + role vocabulary |
| `rag/retrieval.py` | ACL-first simplified TF-IDF + `tokenize` + `load_kb` |
| `rag/answering.py` | injection detectors + `sanitize_content` + `build_prompt` (untrusted-data framing) + providers (mock/ollama/groq; groq system/user message split) + citation regex |
| `rag/core.py` | `ask()` — query gate → shared core with citation post-filter + enforcement, refusal, sentence-scoped output safeguard |
| `rag/service/app.py` | FastAPI `POST /ask` + PII-safe logging |
| `rag/cli.py` | CLI batch over eval.json |
| `rag/evaluate.py` | Per-label evaluation (Recall@3, citation, refusal, latency) |
