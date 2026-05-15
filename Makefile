# ============================================================================
# SEO Operations Platform — Monorepo Makefile
# ============================================================================
# Design axiom: AI proposes. Deterministic systems execute.
# ============================================================================

.PHONY: help dev-up dev-down dev-reset backend-install backend-dev backend-test \
        backend-lint backend-format migrate-create migrate-run migrate-rollback \
        frontend-install frontend-dev docker-build clean \
        dev-worker-all dev-worker-onboarding dev-worker-ai dev-worker-seo \
        dev-worker-backlink dev-worker-communication dev-worker-reporting

SHELL := /bin/bash
.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
PYTHON := python3.12
BACKEND_DIR := backend
FRONTEND_DIR := frontend
INFRA_DIR := infrastructure

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Local Development Environment (Docker)
# ---------------------------------------------------------------------------
dev-setup: ## Initial setup for zero-cost development (installs all, sets up playwright)
	$(MAKE) backend-install
	$(MAKE) frontend-install
	cd $(BACKEND_DIR) && uv run playwright install chromium
	@echo "✅ Setup complete. Run 'make dev-up' to start infra."

dev-up: ## Start all infrastructure services (Postgres, Redis, Kafka, Temporal, MinIO, etc.)
	docker compose -f $(INFRA_DIR)/docker/docker-compose.yml \
	               -f $(INFRA_DIR)/docker/docker-compose.dev.yml up -d
	@echo "✅ Zero-Cost Dev infrastructure is up"
	@echo "   PostgreSQL:    localhost:5432"
	@echo "   Redis:         localhost:6379"
	@echo "   Kafka:         localhost:9092"
	@echo "   Temporal UI:   http://localhost:8233"
	@echo "   Mailhog UI:    http://localhost:8025"
	@echo "   MinIO Console: http://localhost:9001"
	@echo "   Grafana:       http://localhost:3001"

dev-down: ## Stop all infrastructure services
	docker compose -f $(INFRA_DIR)/docker/docker-compose.yml \
	               -f $(INFRA_DIR)/docker/docker-compose.dev.yml down
	@echo "✅ Dev infrastructure stopped"

dev-reset: ## Stop + remove volumes + restart (full data reset)
	docker compose -f $(INFRA_DIR)/docker/docker-compose.yml \
	               -f $(INFRA_DIR)/docker/docker-compose.dev.yml down -v
	$(MAKE) dev-up
	@echo "✅ Dev infrastructure reset complete"

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------
backend-install: ## Install backend dependencies
	cd $(BACKEND_DIR) && uv pip install -e ".[dev]"

dev-api: ## Run backend dev server with hot reload
	cd $(BACKEND_DIR) && uv run uvicorn seo_platform.main:app --reload --host 0.0.0.0 --port 8000

dev-worker: ## Run backend temporal worker (defaults to onboarding)
	cd $(BACKEND_DIR) && uv run python -m seo_platform.cli worker $(QUEUE)

dev-worker-onboarding: ## Run onboarding task queue worker
	cd $(BACKEND_DIR) && uv run python -m seo_platform.cli worker seo-platform-onboarding

dev-worker-ai: ## Run AI orchestration task queue worker
	cd $(BACKEND_DIR) && uv run python -m seo_platform.cli worker seo-platform-ai-orchestration

dev-worker-seo: ## Run SEO intelligence task queue worker
	cd $(BACKEND_DIR) && uv run python -m seo_platform.cli worker seo-platform-seo-intelligence

dev-worker-backlink: ## Run backlink engine task queue worker
	cd $(BACKEND_DIR) && uv run python -m seo_platform.cli worker seo-platform-backlink-engine

dev-worker-communication: ## Run communication task queue worker
	cd $(BACKEND_DIR) && uv run python -m seo_platform.cli worker seo-platform-communication

dev-worker-reporting: ## Run reporting task queue worker
	cd $(BACKEND_DIR) && uv run python -m seo_platform.cli worker seo-platform-reporting

dev-worker-all: ## Run all 6 task queue workers in background
	@echo "Starting all 6 Temporal workers..."
	@cd $(BACKEND_DIR) && uv run python -m seo_platform.cli worker seo-platform-onboarding & echo "$$!" > /tmp/worker-onboarding.pid
	@cd $(BACKEND_DIR) && uv run python -m seo_platform.cli worker seo-platform-ai-orchestration & echo "$$!" > /tmp/worker-ai.pid
	@cd $(BACKEND_DIR) && uv run python -m seo_platform.cli worker seo-platform-seo-intelligence & echo "$$!" > /tmp/worker-seo.pid
	@cd $(BACKEND_DIR) && uv run python -m seo_platform.cli worker seo-platform-backlink-engine & echo "$$!" > /tmp/worker-backlink.pid
	@cd $(BACKEND_DIR) && uv run python -m seo_platform.cli worker seo-platform-communication & echo "$$!" > /tmp/worker-communication.pid
	@cd $(BACKEND_DIR) && uv run python -m seo_platform.cli worker seo-platform-reporting & echo "$$!" > /tmp/worker-reporting.pid
	@echo "All workers started. Run 'make dev-worker-stop' to stop them."

dev-worker-stop: ## Stop all background workers
	@for pidfile in /tmp/worker-*.pid; do \
		if [ -f "$$pidfile" ]; then \
			kill "$$(cat "$$pidfile")" 2>/dev/null && rm "$$pidfile"; \
		fi \
	done
	@echo "All workers stopped."

backend-test: ## Run backend test suite
	cd $(BACKEND_DIR) && pytest tests/ -v --tb=short

backend-lint: ## Lint backend code
	cd $(BACKEND_DIR) && ruff check src/ tests/
	cd $(BACKEND_DIR) && mypy src/seo_platform/ --ignore-missing-imports

backend-format: ## Format backend code
	cd $(BACKEND_DIR) && ruff format src/ tests/

# ---------------------------------------------------------------------------
# Database Migrations (Alembic)
# ---------------------------------------------------------------------------
migrate-create: ## Create a new migration (usage: make migrate-create MSG="add users table")
	cd $(BACKEND_DIR) && uv run alembic revision --autogenerate -m "$(MSG)"

migrate-run: ## Run all pending migrations
	cd $(BACKEND_DIR) && uv run alembic upgrade head

migrate-rollback: ## Rollback last migration
	cd $(BACKEND_DIR) && uv run alembic downgrade -1

db-seed: ## Seed the database with mock tenant and campaign data
	cd $(BACKEND_DIR) && uv run python -m seo_platform.scripts.seed

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------
frontend-install: ## Install frontend dependencies
	cd $(FRONTEND_DIR) && pnpm install

dev-frontend: ## Run frontend dev server
	cd $(FRONTEND_DIR) && pnpm dev

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------
docker-build: ## Build all service Docker images
	docker compose -f $(INFRA_DIR)/docker/docker-compose.yml build

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
clean: ## Remove generated files and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleaned"
