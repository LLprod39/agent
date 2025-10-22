SHELL := /bin/bash
VENV := .venv
PYTHON := python3
PNPM := pnpm

.PHONY: bootstrap bootstrap-python bootstrap-node
bootstrap: bootstrap-python bootstrap-node

bootstrap-python:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating Python virtualenv at $(VENV)"; \
		$(PYTHON) -m venv $(VENV); \
	fi
	@if [ -f requirements.txt ] && grep -q "^[^#[:space:]]" requirements.txt; then \
		echo "Installing Python dependencies from requirements.txt"; \
		"$(VENV)/bin/python" -m pip install -r requirements.txt; \
	else \
		echo "No Python dependency list detected; skipping install"; \
	fi

bootstrap-node:
	@if [ -f package.json ]; then \
		echo "Installing Node.js dependencies with $(PNPM)"; \
		$(PNPM) install; \
	else \
		echo "No package.json found; skipping Node.js dependency install"; \
	fi

.PHONY: test test-python test-node
test: test-python test-node

# Runs the Python unit test suite when tests are present; otherwise prints a skip message.
test-python:
	@if find tests -name 'test_*.py' -print -quit | grep -q .; then \
		if [ -f "$(VENV)/bin/python" ]; then \
			echo "Running unittest discovery via $(VENV)"; \
			"$(VENV)/bin/python" -m unittest discover -s tests -t .; \
		else \
			echo "Running unittest discovery via system interpreter"; \
			$(PYTHON) -m unittest discover -s tests -t .; \
		fi; \
	else \
		echo "No Python tests found; skipping"; \
	fi

# Runs pnpm test when package.json defines it; otherwise prints a skip message.
test-node:
	@if [ -f package.json ]; then \
		echo "Running pnpm test"; \
		$(PNPM) test; \
	else \
		echo "No package.json found; skipping Node.js tests"; \
	fi

.PHONY: lint lint-python lint-node
lint: lint-python lint-node

lint-python:
	@if [ -f "$(VENV)/bin/ruff" ]; then \
		echo "Running ruff via $(VENV)"; \
		"$(VENV)/bin/ruff" check . && "$(VENV)/bin/ruff" format --check .; \
	elif command -v ruff >/dev/null 2>&1; then \
		echo "Running ruff via system interpreter"; \
		ruff check . && ruff format --check .; \
	else \
		echo "ruff not installed; skipping Python lint"; \
	fi

lint-node:
	@if [ -f package.json ]; then \
		echo "Running pnpm lint"; \
		$(PNPM) lint; \
	else \
		echo "No package.json found; skipping Node.js lint"; \
	fi

.PHONY: clean
clean:
	@echo "Removing virtual environment and temporary build artifacts"
	@rm -rf "$(VENV)" node_modules apps/ui/node_modules apps/ui/.next .pytest_cache .mypy_cache .ruff_cache
	@find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	@find . -name '*.log' -delete

.PHONY: validate-environments
validate-environments:
	@if [ -f "$(VENV)/bin/python" ]; then \
		echo "Validating environments using $(VENV)"; \
		"$(VENV)/bin/python" -m packages.shared.env_schema; \
	else \
		echo "Validating environments using system Python"; \
		$(PYTHON) -m packages.shared.env_schema; \
	fi

.PHONY: db-migrate db-status db-init dev run-api
# Database migration commands
db-init:
	@echo "Initializing database and running migrations"
	@if [ -f "$(VENV)/bin/python" ]; then \
		"$(VENV)/bin/python" -c "import asyncio; from apps.database.connection import DatabaseManager; from apps.database.migrations import MigrationManager; from config.settings import get_settings; \
		async def init(): \
			settings = get_settings(); \
			db = DatabaseManager(settings.database_url, settings.database_echo); \
			await db.initialize(); \
			mm = MigrationManager(db.engine); \
			await mm.migrate(); \
			status = await mm.status(); \
			print(f'Migration status: {status}'); \
			await db.close(); \
		asyncio.run(init())"; \
	else \
		echo "Virtual environment not found. Run 'make bootstrap-python' first."; \
		exit 1; \
	fi

db-migrate:
	@echo "Running database migrations"
	@if [ -f "$(VENV)/bin/python" ]; then \
		"$(VENV)/bin/python" -c "import asyncio; from apps.database.connection import DatabaseManager; from apps.database.migrations import MigrationManager; from config.settings import get_settings; \
		async def migrate(): \
			settings = get_settings(); \
			db = DatabaseManager(settings.database_url, settings.database_echo); \
			await db.initialize(); \
			mm = MigrationManager(db.engine); \
			await mm.migrate(); \
			print('Migrations completed successfully'); \
			await db.close(); \
		asyncio.run(migrate())"; \
	else \
		echo "Virtual environment not found. Run 'make bootstrap-python' first."; \
		exit 1; \
	fi

db-status:
	@echo "Checking database migration status"
	@if [ -f "$(VENV)/bin/python" ]; then \
		"$(VENV)/bin/python" -c "import asyncio; from apps.database.connection import DatabaseManager; from apps.database.migrations import MigrationManager; from config.settings import get_settings; \
		async def status(): \
			settings = get_settings(); \
			db = DatabaseManager(settings.database_url, settings.database_echo); \
			await db.initialize(); \
			mm = MigrationManager(db.engine); \
			status = await mm.status(); \
			print('Migration Status:'); \
			print(f'  Total migrations: {status[\"total_migrations\"]}'); \
			print(f'  Applied: {status[\"applied_migrations\"]}'); \
			print(f'  Pending: {status[\"pending_migrations\"]}'); \
			if status['applied']: print(f'  Applied versions: {status[\"applied\"]}'); \
			if status['pending']: print(f'  Pending versions: {status[\"pending\"]}'); \
			await db.close(); \
		asyncio.run(status())"; \
	else \
		echo "Virtual environment not found. Run 'make bootstrap-python' first."; \
		exit 1; \
	fi

# Development server commands
run-api:
	@echo "Starting API server in development mode"
	@if [ -f "$(VENV)/bin/uvicorn" ]; then \
		cd apps/api && ../../$(VENV)/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000; \
	else \
		echo "uvicorn not found. Run 'make bootstrap-python' first."; \
		exit 1; \
	fi

dev: db-migrate run-api
