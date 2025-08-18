.PHONY: help install test lint format clean run

help:
	@echo "🎯 Simple Magic Card Generator Commands:"
	@echo ""
	@echo "  make install    Install all dependencies"
	@echo "  make test       Run tests"
	@echo "  make lint       Check code style"
	@echo "  make format     Auto-format code"
	@echo "  make clean      Clean up cache files"
	@echo "  make run        Run the application"

install:
	poetry install
	poetry run pre-commit install

test:
	poetry run pytest -v --cov=src --cov-report=term-missing --cov-report=html

lint:
	poetry run ruff check src tests

format:
	poetry run black src tests
	poetry run ruff check --fix src tests

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov .pytest_cache .mypy_cache .ruff_cache

run:
	@echo "Example: Generate a creature card"
	poetry run python -m magic_tg_card_generator generate "Dragon" --type Creature --mana-cost "4RR" --color Red --power 5 --toughness 5
