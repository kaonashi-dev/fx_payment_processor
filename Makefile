.PHONY: help install dev test clean lint format docker-build docker-up docker-down docker-logs docker-restart db-migrate db-upgrade db-downgrade db-seed run

help:
	@echo "Available commands:"
	@echo "  make install          - Install dependencies with uv"
	@echo "  make dev              - Run development server locally"
	@echo "  make test             - Run tests with pytest"
	@echo "  make clean            - Clean cache and temp files"
	@echo ""
	@echo "Docker commands:"
	@echo "  make docker-build     - Build Docker containers"
	@echo "  make docker-up        - Start Docker containers"
	@echo "  make docker-down      - Stop Docker containers"
	@echo ""
	@echo "Database commands:"
	@echo "  make db-migrate       - Run migrations"
	@echo "  make db-seed          - Seed database with test data"
	@echo ""
	@echo "  make run              - Run with docker-compose (build + up)"
	@echo "  make stop             - Stop docker-compose"

# Local development
install:
	uv sync

dev:
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 3700

run:
	uv run python -m src.main

test:
	uv run pytest

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

# Docker commands
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

# Database commands
db-migrate:
	uv run alembic upgrade head

db-seed:
	uv run python scripts/seed_db.py

# Combined command for quick start
run: install docker-build docker-up db-migrate db-seed
	@echo "Services are running!"
	@echo "API available at http://localhost:3700"
	@echo "API docs at http://localhost:3700/docs"

stop:
	docker-compose down