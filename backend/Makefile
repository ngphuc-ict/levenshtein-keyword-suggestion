PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

.PHONY: install dev test bench lint

install:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements-dev.txt

dev:
	$(BIN)/uvicorn app.main:app --reload --no-access-log --port 8000

test:
	$(BIN)/pytest

bench:
	$(BIN)/python benchmarks/benchmark.py

lint:
	$(BIN)/ruff check app tests benchmarks
	$(BIN)/ruff format --check app tests benchmarks
