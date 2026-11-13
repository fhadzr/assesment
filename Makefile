# V-TEKI Assessment Makefile
# Portable across POSIX shells and Windows (Git Bash / MinGW make).
# Per-case venvs live in <case>/.venv; tests run with each case's own interpreter.
# PY is the interpreter used to bootstrap venvs (override if needed, e.g. PY=python3).

PY ?= python
CASES = case1_fraud case2_docintel case3_rag

# Resolve a case venv's interpreter. Only call after the venv exists
# (make expands recipes before running them, so creation uses scripts/setup_case.py).
define venv_py
$(if $(wildcard $(1)/.venv/Scripts/python.exe),$(1)/.venv/Scripts/python.exe,$(1)/.venv/bin/python)
endef

.PHONY: help setup $(addprefix setup-,$(CASES)) test $(addprefix test-,$(CASES)) check check-data check-evidence clean

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

# ---- setup ----

setup-case1: ## Create case1 venv and install editable + pinned deps
	@$(PY) scripts/setup_case.py case1_fraud

setup-case2: ## Create case2 venv and install editable + pinned deps
	@$(PY) scripts/setup_case.py case2_docintel

setup-case3: ## Create case3 venv and install editable + pinned deps
	@$(PY) scripts/setup_case.py case3_rag

setup: setup-case1 setup-case2 setup-case3 ## Create all case venvs

# ---- tests ----

test-case1: ## Run case1 tests + root checker tests in case1 venv
	@$(call venv_py,case1_fraud) -m pytest case1_fraud/tests tests -q

test-case2: ## Run case2 tests + root checker tests in case2 venv
	@$(call venv_py,case2_docintel) -m pytest case2_docintel/tests tests -q

test-case3: ## Run case3 tests + root checker tests in case3 venv
	@$(call venv_py,case3_rag) -m pytest case3_rag/tests tests -q

test: test-case1 test-case2 test-case3 ## Run all case tests + root checker tests

# ---- conventions ----

check-data: ## Enforce synthetic data conventions
	@python scripts/check_data_conventions.py

check-evidence: ## Enforce evidence + secret conventions
	@python scripts/check_evidence_conventions.py

check: check-data check-evidence ## Run all convention checks

# ---- case2 docintel workflow ----

case2-corpus: ## Generate case2 synthetic invoice corpus
	@$(call venv_py,case2_docintel) -m docintel.corpus.generate --seed 42 --n-invoices 20 --out case2_docintel

case2-evaluate: ## Run case2 evaluation (mock provider, offline)
	@$(call venv_py,case2_docintel) -m docintel.evaluate --corpus case2_docintel --provider mock --out case2_docintel/outputs/evaluation.json

case2-serve: ## Run case2 FastAPI service (manual)
	@$(call venv_py,case2_docintel) -m uvicorn docintel.service.app:create_app --factory --app-dir case2_docintel/src --host 127.0.0.1 --port 8001

# ---- case3 rag workflow ----

case3-corpus: ## Generate case3 KB + evaluation dataset (seeded)
	@$(call venv_py,case3_rag) -m rag.generate_kb --seed 42 --n-docs 10 --out case3_rag/data
	@$(call venv_py,case3_rag) -m rag.generate_eval --seed 42 --n-questions 36 --data-dir case3_rag/data

case3-evaluate: ## Run case3 evaluation (mock provider, offline)
	@$(call venv_py,case3_rag) -m rag.evaluate --eval case3_rag/data/eval.json --kb case3_rag/data/kb.json --provider mock --out case3_rag/outputs/evaluation.json

case3-serve: ## Run case3 FastAPI service (manual)
	@$(call venv_py,case3_rag) -m uvicorn rag.service.app:create_app --factory --app-dir case3_rag/src --host 127.0.0.1 --port 8002

# ---- case1 fraud workflow ----

case1-generate: ## Generate case1 relational dataset (seeded)
	@$(call venv_py,case1_fraud) -m fraud.data.generate --seed 42 --n-customers 200 --n-transactions 10000 --out case1_fraud/data

case1-quality: ## Build case1 join match-rate / data-quality report
	@$(call venv_py,case1_fraud) -m fraud.data.quality --data-dir case1_fraud/data --out case1_fraud/outputs/quality_report.json

case1-train: ## Train case1 models (baseline + LR + optional HGB), compare, evaluate
	@$(call venv_py,case1_fraud) -m fraud.model.baseline
	@$(call venv_py,case1_fraud) -m fraud.model.train
	@$(call venv_py,case1_fraud) -m fraud.model.train --model hgb --with-hgb --out case1_fraud/outputs/model_hgb
	@$(call venv_py,case1_fraud) -m fraud.model.compare
	@$(call venv_py,case1_fraud) -m fraud.model.evaluate --k 100

case1-serve: ## Run case1 FastAPI service (manual)
	@$(call venv_py,case1_fraud) -m uvicorn fraud.service.app:create_app --factory --app-dir case1_fraud/src --host 127.0.0.1 --port 8000

case1-infer: ## CLI batch inference (usage: make case1-infer IN=... OUT=...)
	@$(call venv_py,case1_fraud) -m fraud.infer --in $(IN) --model case1_fraud/outputs/model_lr --out $(OUT) --role $(or $(ROLE),analyst)

# ---- clean ----

clean: ## Remove venvs and caches
	@rm -rf case1_fraud/.venv case2_docintel/.venv case3_rag/.venv
	@rm -rf .pytest_cache tests/__pycache__ scripts/__pycache__
	@find . -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.egg-info" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "cleaned"
