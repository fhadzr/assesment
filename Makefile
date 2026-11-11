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

# ---- clean ----

clean: ## Remove venvs and caches
	@rm -rf case1_fraud/.venv case2_docintel/.venv case3_rag/.venv
	@rm -rf .pytest_cache tests/__pycache__ scripts/__pycache__
	@find . -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.egg-info" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "cleaned"
