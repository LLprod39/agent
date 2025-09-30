# Environment Profiles

Store YAML documents that describe access patterns, proxies, and defaults for each managed environment.

- Follow the schema at `packages/shared/env_schema/environment-profile.schema.json`.
- Reuse `packages.shared.env_schema.validate_environment_profile_file` in tooling, CI, or `python -m packages.shared.env_schema` to enforce the schema.
- Start from the samples `environments/dev-k8s.example.yaml`, `environments/dev-vm.example.yaml`, or `environments/prod-k8s.example.yaml` and tailor them for конкретные окружения.
