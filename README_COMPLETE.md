# DevOps LLM Agent

Autonomous assistant that executes DevOps and SRE workflows across heterogeneous infrastructure. The long-term architecture, roadmap, and operational guardrails live in `DevOps_LLM_Agent_Plan.md`.

## Getting Started
- Read `DevOps_LLM_Agent_Plan.md` to understand end-to-end capabilities, safety constraints, and current priorities.
- Use `make bootstrap` to set up Python and Node.js toolchains once the dependencies are defined.
- Run `make test` and `make lint` before submitting changes.

## Repository Layout
```
DevOps_LLM_Agent_Plan.md  # Canonical architecture and planning document
AGENTS.md                  # Contribution and workflow guidelines
README.md                  # High-level quickstart and repo map
docs/                      # Detailed architecture docs, runbooks, and ADRs
infra/                     # Terraform, Helm, and compose definitions
packages/                  # SDK implementations and shared schemas
data/                      # Knowledge base ingestion and seed fixtures
tests/                     # Unit, integration, and scenario test suites
environments/              # Environment profiles and overrides
.github/workflows/         # Continuous integration pipelines
```