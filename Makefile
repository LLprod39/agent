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
