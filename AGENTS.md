# Repository Guidelines

## Project Structure & Module Organization
The mono-repo splits application services under `apps/`, shared SDKs in `packages/`, and infrastructure as code under `infra/`. Docs and runbooks live in `docs/` with ops runbooks in `docs/runbooks/`. Keep environment profiles in `environments/`, data fixtures in `data/`, and place unit, integration, and scenario suites in `tests/unit/`, `tests/integration/`, and `tests/scenarios/` respectively. Review `DevOps_LLM_Agent_Plan.md` before large updates to align with the active roadmap.

## Build, Test, and Development Commands
Run `make bootstrap` from the repo root to create the virtualenv and install Node/Python deps. Use `make lint` to execute Ruff checks and Prettier formatting across languages. `make test` runs `python -m unittest discover` and `pnpm test` where applicable. Validate configuration with `make validate-environments`, and use `make clean` for a fresh bootstrap cycle.

## Coding Style & Naming Conventions
Python code uses 4-space indentation, snake_case identifiers, and must pass `ruff format`. TypeScript, Markdown, YAML, and JSON files use 2 spaces formatted via `pnpm exec prettier --write`. Prefer descriptive kebab-case directories (`observability-stack/`) and explicit filenames such as `executor_agent.py` or `cluster-rollout.ts`.

## Testing Guidelines
Add tests alongside features, naming Python modules `test_<feature>.py`. Stub external systems and place fixtures in `data/`. Maintain coverage expectations by running `make test` before commits and document intentionally skipped cases in PR descriptions.

## Commit & Pull Request Guidelines
Write Conventional Commits (e.g., `feat(env): add staging profile validator`). PRs should cite relevant plan sections or issues, explain behavioural changes, and include logs or screenshots for UI/API updates. Update runbooks or environment profiles whenever behaviour or configuration shifts.

## Security & Configuration Tips
Never commit secrets; store credentials in `environments/<env>.yaml` and verify them with `make validate-environments`. Mirror CI by running `make bootstrap`, `make validate-environments`, and `make test` locally before pushing changes.
