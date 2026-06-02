.PHONY: install etl test test-invariants test-golden lint format type-check \
        run docker-build docker-run clean help

PYTHON     := python
SRC        := src
APP        := app/app.py
IMAGE_NAME := nvidia-fpa-platform
PORT       := 8501

# ─────────────────────────────────────────────────────────────────────────────
help:          ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Setup ───────────────────────────────────────────────────────────────────
install:       ## Install all dependencies
	pip install -r requirements.txt

install-dev:   ## Install with dev tooling (ruff, mypy)
	pip install -r requirements.txt
	pip install ruff mypy

# ─── Pipeline ────────────────────────────────────────────────────────────────
etl:           ## Run ETL pipeline — build canonical Parquet tables from raw 10-K files
	PYTHONPATH=$(SRC) $(PYTHON) -m etl.pipeline

# ─── Testing ─────────────────────────────────────────────────────────────────
test:          ## Run full test suite with coverage report
	PYTHONPATH=$(SRC) pytest tests/ --cov=$(SRC) --cov-report=term-missing --cov-report=html

test-fast:     ## Run tests excluding slow integration tests
	PYTHONPATH=$(SRC) pytest tests/ -m "not integration" --tb=short

test-invariants: ## Run financial invariant checks only (BS, CF, RE)
	PYTHONPATH=$(SRC) pytest tests/test_financial_invariants.py -v

test-golden:   ## Run regression tests against known 10-K values
	PYTHONPATH=$(SRC) pytest tests/test_golden_output.py -v

test-modeling: ## Run modeling unit tests only
	PYTHONPATH=$(SRC) pytest tests/ -m "modeling" -v

# ─── Code quality ────────────────────────────────────────────────────────────
lint:          ## Lint with ruff
	ruff check $(SRC) tests

format:        ## Format with ruff
	ruff format $(SRC) tests

type-check:    ## Run mypy type checks
	mypy $(SRC)

# ─── App ─────────────────────────────────────────────────────────────────────
run:           ## Launch Streamlit dashboard (localhost:8501)
	PYTHONPATH=$(SRC) streamlit run $(APP) --server.port $(PORT)

# ─── Docker ──────────────────────────────────────────────────────────────────
docker-build:  ## Build Docker image
	docker build -t $(IMAGE_NAME):latest .

docker-run:    ## Run containerised dashboard
	docker run -p $(PORT):$(PORT) --rm $(IMAGE_NAME):latest

docker-shell:  ## Open shell inside container
	docker run -it --rm $(IMAGE_NAME):latest /bin/bash

# ─── Cleanup ─────────────────────────────────────────────────────────────────
clean:         ## Remove all generated artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	rm -rf data/processed/*.parquet data/processed/*.csv data/processed/*.json 2>/dev/null || true
	@echo "Clean complete."
