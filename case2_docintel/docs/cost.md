# Case 2 Cost Report

Every number below is copied from an executable script's output — nothing is
hand-written. There are no estimated costs.

## Mock evaluation (actual run, this repository)

| Item | Value | Source |
| --- | --- | --- |
| Provider | mock | `evaluation.json` `usage.provider` |
| Total tokens | **0** | `usage.tokens` (mock-zero-by-construction) |
| Cost | **0.00** | `usage.cost` |
| Cost basis | `mock-zero-by-construction` | `usage.basis` |

The mock provider performs deterministic regex extraction with **no LLM call**,
so zero tokens and zero cost are real — not estimates.

## Real provider runs (not executed — reproduced on demand)

No real Ollama/Groq run has been executed, so **no real token or cost figures
exist yet**, and none are reported. To reproduce:

```bash
# Local Ollama (no metered cost; usage reported from response eval_count)
DOCINTEL_PROVIDER=ollama \
  case2_docintel/.venv/Scripts/python -m docintel.evaluate \
  --corpus case2_docintel --provider ollama --model llama3.2

# External Groq (key from env only; usage/cost from response usage metadata)
GROQ_API_KEY=<from environment> \
  case2_docintel/.venv/Scripts/python -m docintel.evaluate \
  --corpus case2_docintel --provider groq --model llama-3.3-70b-versatile
```

- **Ollama** reports `eval_count` (tokens) but has no metered cost → cost basis
  `local-provider-no-metered-cost`, `cost: null`.
- **Groq** reports `usage.total_tokens`; per-token cost is computed from
  Groq's published rate table at run time. If the response lacks usage
  metadata, tokens and cost are `null` with basis `metadata-unavailable` —
  never zero, never estimated.

## Honesty note

This cost report intentionally contains no invented per-provider cost lines.
The only cost figure in the repository is the mock evaluation's zero, which is
true by construction.
