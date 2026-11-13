# Case 3 — Enterprise RAG Chatbot

## Setup

```bash
make setup-case3
```

## Generate the knowledge base and evaluation dataset

```bash
make case3-corpus
# or:
case3_rag/.venv/Scripts/python -m rag.generate_kb --seed 42 --n-docs 10 --out case3_rag/data
case3_rag/.venv/Scripts/python -m rag.generate_eval --seed 42 --n-questions 36 --data-dir case3_rag/data
```

## Run tests

```bash
make test-case3
# or:
case3_rag/.venv/Scripts/pytest case3_rag/tests -q
```

## Run evaluation (mock provider, offline)

```bash
make case3-evaluate
# or:
case3_rag/.venv/Scripts/python -m rag.evaluate --eval case3_rag/data/eval.json --kb case3_rag/data/kb.json --provider mock --out case3_rag/outputs/evaluation.json
```

## Run the service

```bash
make case3-serve
# POST /ask with {"question": "...", "role": "hr"|"finance"|"exec"}
```

## Run the CLI batch

```bash
case3_rag/.venv/Scripts/python -m rag.cli --in case3_rag/data/eval.json --kb case3_rag/data/kb.json --out case3_rag/outputs/cli_results.json --provider mock
```

## Convention and security checks

```bash
make check
python scripts/export_security_results.py case3_rag
```
