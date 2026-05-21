.PHONY: install test lint format typecheck check clean

install:
	pip install -e .[dev]

test:
	pytest

lint:
	ruff check src tests
	ruff format --check src tests

format:
	ruff check --fix src tests
	ruff format src tests

typecheck:
	mypy --strict src

check: lint typecheck test

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} +
