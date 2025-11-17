.PHONY: help install dev run test clean db-up db-down db-reset db-logs db-shell lint format

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -r requirements.txt

dev: ## Install dependencies in development mode
	pip install -r requirements.txt
	pip install -e .

run: db-up ## Run the development server with database
	uvicorn app.main:app --reload --host 0.0.0.0 --port 3000

run-prod: ## Run the production server
	uvicorn app.main:app --host 0.0.0.0 --port 3000

test: ## Run tests (placeholder)
	@echo "Tests not yet implemented"

clean: ## Clean Python cache files
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true

db-up: ## Start PostgreSQL database
	docker compose up -d

db-down: ## Stop PostgreSQL database
	docker compose down

db-reset: ## Reset database (WARNING: deletes all data)
	docker compose down -v
	docker compose up -d

db-logs: ## Show database logs
	docker compose logs -f postgres

db-shell: ## Access database shell
	docker compose exec postgres psql -U mrcap -d mrcap_dashboard

setup: ## Initial setup: create venv and install dependencies
	python3 -m venv venv
	@echo "Virtual environment created. Activate it with: source venv/bin/activate"
	@echo "Then run: make install"

lint: ## Run linter
	ruff check app/

lint-fix: ## Run linter and auto-fix issues
	ruff check --fix app/

format: ## Format code
	ruff format app/

format-check: ## Check code formatting without making changes
	ruff format --check app/

