# =============================================================================
# APF Makefile
# All commands assume you are running from the repository root.
# =============================================================================

SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

# Project settings
PROJECT_NAME    := apf
COMPOSE_FILE    := deploy/docker-compose.yml
COMPOSE_DEV     := deploy/docker-compose.dev.yml
ENV_FILE        := deploy/.env
OPENAPI_OUTPUT  := openapi.json

# Tool detection
UV              := uv
PNPM            := pnpm
DOCKER_COMPOSE  := docker compose
PYTHON          := $(UV) run python

.PHONY: help install dev test lint lint-python lint-frontend build clean \
        migrate migrate-create generate-openapi format pre-commit \
        logs shell-orchestrator shell-postgres

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  Usage: make <target>"

# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------
install: ## Install all Python and Node dependencies
	@echo ">>> Installing Python dependencies with uv..."
	$(UV) sync --all-packages --frozen
	@echo ">>> Installing Node dependencies with pnpm..."
	$(PNPM) install --frozen-lockfile
	@echo ">>> Installing pre-commit hooks..."
	$(UV) run pre-commit install --install-hooks
	@echo ">>> Done."

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------
dev: $(ENV_FILE) ## Start all services in development mode (hot-reload)
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) up --build

dev-detach: $(ENV_FILE) ## Start all services in development mode (detached)
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) up --build -d

down: ## Stop all running containers
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) down

logs: ## Tail logs for all services
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) logs -f --tail=100

$(ENV_FILE):
	@echo ">>> .env not found — copying from .env.example"
	cp deploy/.env.example $(ENV_FILE)
	@echo ">>> Please fill in the secrets in $(ENV_FILE) before running services."

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------
test: ## Run the full test suite (Python + Frontend)
	@echo ">>> Running Python tests..."
	$(UV) run pytest \
		--cov \
		--cov-report=term-missing \
		--cov-report=xml:coverage.xml \
		--cov-fail-under=80 \
		-q
	@echo ">>> Running frontend tests..."
	$(PNPM) --filter dashboard test --run

test-python: ## Run Python tests only
	$(UV) run pytest \
		--cov \
		--cov-report=term-missing \
		--cov-fail-under=80 \
		-q

test-frontend: ## Run frontend tests only
	$(PNPM) --filter dashboard test --run

test-watch: ## Run Python tests in watch mode
	$(UV) run pytest-watch -- -q

# ---------------------------------------------------------------------------
# Linting & Formatting
# ---------------------------------------------------------------------------
lint: lint-python lint-frontend ## Run all linters

lint-python: ## Run ruff and mypy
	@echo ">>> ruff check..."
	$(UV) run ruff check .
	@echo ">>> ruff format check..."
	$(UV) run ruff format --check .
	@echo ">>> mypy..."
	$(UV) run mypy \
		packages/agent-core/src \
		packages/db/src \
		packages/event-bus/src \
		services/orchestrator/src \
		services/agent-runner/src \
		services/artifact-store/src \
		services/github-integration/src \
		services/slack-connector/src \
		services/jira-connector/src \
		services/confluence-connector/src \
		services/aws-connector/src \
		cli/src \
		--ignore-missing-imports

lint-frontend: ## Run ESLint and Prettier check
	@echo ">>> ESLint..."
	$(PNPM) --filter dashboard lint
	@echo ">>> Prettier..."
	$(PNPM) --filter dashboard prettier --check "src/**/*.{ts,tsx,css}"

format: ## Auto-format all code (ruff + prettier)
	@echo ">>> ruff format..."
	$(UV) run ruff format .
	$(UV) run ruff check --fix .
	@echo ">>> Prettier..."
	$(PNPM) --filter dashboard prettier --write "src/**/*.{ts,tsx,css,json}"

pre-commit: ## Run all pre-commit hooks on all files
	$(UV) run pre-commit run --all-files

# ---------------------------------------------------------------------------
# Docker Build
# ---------------------------------------------------------------------------
build: ## Build all Docker images (no push)
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) build --parallel

build-service: ## Build a single service: make build-service SERVICE=orchestrator
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) build $(SERVICE)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
migrate: ## Run Alembic migrations (upgrade head)
	@echo ">>> Running database migrations..."
	$(UV) run alembic -c packages/db/alembic.ini upgrade head

migrate-create: ## Create a new Alembic migration: make migrate-create MSG="add user table"
	$(UV) run alembic -c packages/db/alembic.ini revision --autogenerate -m "$(MSG)"

migrate-history: ## Show migration history
	$(UV) run alembic -c packages/db/alembic.ini history --verbose

migrate-downgrade: ## Downgrade one revision
	$(UV) run alembic -c packages/db/alembic.ini downgrade -1

# ---------------------------------------------------------------------------
# OpenAPI
# ---------------------------------------------------------------------------
generate-openapi: ## Export OpenAPI spec from orchestrator to openapi.json
	@echo ">>> Generating OpenAPI spec..."
	$(PYTHON) -c "
import json
from orchestrator.main import app
spec = app.openapi()
with open('$(OPENAPI_OUTPUT)', 'w') as f:
    json.dump(spec, f, indent=2)
print('Written to $(OPENAPI_OUTPUT)')
"

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
clean: ## Remove all build artifacts, caches, and generated files
	@echo ">>> Cleaning Python artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@echo ">>> Cleaning Node artifacts..."
	find . -type d -name "node_modules" -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "coverage" -exec rm -rf {} + 2>/dev/null || true
	@echo ">>> Clean complete."

clean-docker: ## Remove stopped containers, dangling images, and unused volumes
	docker system prune -f
	docker volume prune -f

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
shell-orchestrator: ## Open a shell in the running orchestrator container
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec orchestrator bash

shell-postgres: ## Open a psql shell in the running postgres container
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) exec postgres \
		psql -U $${POSTGRES_USER:-apf} -d $${POSTGRES_DB:-apf}
