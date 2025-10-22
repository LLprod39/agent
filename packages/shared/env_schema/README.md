# Environment Profile Schema

This module defines the JSON Schema (`environment-profile.schema.json`) used to validate YAML or JSON documents inside `environments/`. The helper utilities expose validation functions (implemented without external dependencies) that future services (CLI, env-config API, CI jobs) can reuse.

## Python Usage
```python
from packages.shared.env_schema import validate_environment_profile_file

profile = validate_environment_profile_file("environments/prod-k8s.example.yaml")
```
