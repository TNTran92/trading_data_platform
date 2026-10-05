.DEFAULT_GOAL := help
.PHONY: help sync test lint run-dag dashboard clean

help:
	@echo "Targets: sync | test | lint | run-dag | dashboard | clean"

sync:
	uv sync --all-extras

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run mypy src

run-dag:
	docker compose up airflow

dashboard:
	uv run streamlit run src/spx_momentum/ui/dashboard.py

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
