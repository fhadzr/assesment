# Case 3 Limitations

Each limitation maps to a design decision in `openspec/changes/enterprise-rag-chatbot/design.md`.

| # | Limitation | Design decision | Honesty note |
| --- | --- | --- | --- |
| 1 | **Lexical retrieval is weak for paraphrase**: simplified TF-IDF only matches surface tokens; semantically-equivalent questions without shared words miss relevant docs. | D3 | Recall@3 measured and reported honestly; a low value would trigger an index improvement, never metric faking. |
| 2 | **Mock provider is deterministic and near-perfect on the synthetic KB** (grounded sentence selection with ≥2-token overlap), not representative of real LLMs. | D5 | Mock results labeled `mock`; the mock-vs-real gap is documented, not hidden. |
| 3 | **Role is a declared attribute, not authentication**: the API validates the role value but performs no identity verification; anyone can claim `exec`. | D4/D7, non-goals | Documented demo posture; spec wording avoids claiming authentication. |
| 4 | **Real LLM could hallucinate or follow injection despite grounding**: citation post-filter only proves a citation is inside the retrieved set, not that the whole answer is supported. | D5/D6, risks | Optional lexical-overlap signal is a heuristic; protection against memorized restricted content is explicitly NOT claimed. |
| 5 | **No embedding/semantic recall**: recall is bounded by lexical overlap. | D11 | Same as #1; measured, not fabricated. |
| 6 | **Single generic refusal for unanswerable and restricted**: the runtime cannot (and by design does not) distinguish the two, to avoid leaking whether a restricted document exists. | D5 | Evaluation labels still distinguish them at ground-truth time. |
| 7 | **Injection defense is strongest on the mock**: the mock cannot be tricked because it only extracts grounded sentences; real providers remain an open robustness question. | D6 | Adversarial tests pin the mock; real-provider robustness is an honest open limitation. |
| 8 | **Windows-first**: tested on Windows 10.0.26200; POSIX assumed compatible but not CI-tested here. | foundation D7/D8 | Raw pip/pytest fallbacks in docs/README.md. |
