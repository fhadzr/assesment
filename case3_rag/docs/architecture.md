# Case 3 Architecture — Enterprise RAG Chatbot

## Data flow

```
rag/generate_kb.py --seed 42 --n-docs 10 ──► case3_rag/data/kb.json + kb_manifest.json
rag/generate_eval.py --seed 42 --n-questions 36 ──► case3_rag/data/eval.json + eval_manifest.json
        │
        ▼
rag/retrieval.py  retrieve(query, role, k=3)
        │  validate role (fail-closed) → filter eligible by allowed() →
        │  compute N/df over eligible only → simplified TF-IDF → rank → top-K
        ▼
rag/answering.py  build_prompt(only permitted hits) → provider(mock|ollama|groq)
        │  MockProvider: grounded sentence selection (≥2 content-token overlap)
        ▼
rag/core.py  ask() → post-filter citations to permitted set → generic refusal if unsupported
        ├──► rag/service/app.py  POST /ask (role enum, PII-safe logging)
        ├──► rag/cli.py          batch over eval.json (same core)
        └──► rag/evaluate.py ──► outputs/evaluation.json ──► evidence/experiment_log/case3_*.json
                 └─ security suite ──► evidence/security_test_results/case3_security.json
```

## Module inventory

| Module | Responsibility |
| --- | --- |
| `rag/generate_kb.py` | Seeded synthetic KB (8–12 role-gated docs + injection doc) |
| `rag/generate_eval.py` | Seeded eval dataset (36 labeled questions + citations) |
| `rag/roles.py` | `allowed(doc, role)` predicate + role vocabulary |
| `rag/retrieval.py` | ACL-first simplified TF-IDF + `tokenize` + `load_kb` |
| `rag/answering.py` | `build_prompt` + providers (mock/ollama/groq) + citation regex |
| `rag/core.py` | `ask()` — shared core with citation post-filter + refusal |
| `rag/service/app.py` | FastAPI `POST /ask` + PII-safe logging |
| `rag/cli.py` | CLI batch over eval.json |
| `rag/evaluate.py` | Per-label evaluation (Recall@3, citation, refusal, latency) |
