"""Integration tests for environment API endpoints."""

import json
import os
import tempfile
import textwrap
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.dependencies import (
    _build_environment_service,
    get_settings as api_get_settings,
)
from config.settings import Settings, get_settings


class EnvironmentAPITests(unittest.TestCase):
    """Exercise the environment router via HTTP."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.profiles_dir = Path(self.temp_dir.name)

        # Ensure fresh settings/service instances for each test run.
        get_settings.cache_clear()
        _build_environment_service.cache_clear()

        custom_settings = Settings(
            environment_profiles_dir=self.profiles_dir,
            environment_cache_ttl=0,
            llm_providers=[{"name": "local", "type": "local", "enabled": True, "config": {}}],
        )

        app.dependency_overrides[api_get_settings] = lambda: custom_settings
        self.client = TestClient(app)

    def tearDown(self) -> None:  # pragma: no cover - cleanup hook
        self.client.close()
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        _build_environment_service.cache_clear()
        self.temp_dir.cleanup()

    def _write_profile(self, name: str = "dev") -> None:
        profile_yaml = textwrap.dedent(
            """
            id: {name}
            type: k8s
            networking:
              proxy:
                http: http://proxy.local:3128
            auth:
              vault_role: {name}/admin
            policies:
              risk_level: low
              require_approval: false
            """
        ).strip().format(name=name)
        (self.profiles_dir / f"{name}.yaml").write_text(profile_yaml, encoding="utf-8")

    def test_list_environments_returns_profiles(self):
        self._write_profile("dev")

        response = self.client.get("/api/v1/environments/")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["success"], True)
        self.assertEqual(len(payload["environments"]), 1)
        self.assertEqual(payload["environments"][0]["id"], "dev")

    def test_create_environment_persists_profile(self):
        request_payload = {
            "id": "qa",
            "type": "k8s",
            "display_name": "QA Cluster",
            "networking": {
                "proxy": {"http": "http://qa-proxy:3128"}
            },
            "auth": {"vault_role": "qa/admin"},
            "policies": {"risk_level": "low", "require_approval": False},
        }

        response = self.client.post("/api/v1/environments/", json=request_payload)
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["id"], "qa")
        self.assertTrue((self.profiles_dir / "qa.yaml").exists())

        # Fetch the newly created profile
        get_response = self.client.get("/api/v1/environments/qa")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["environment"]["id"], "qa")

    def test_get_invalid_profile_returns_422(self):
        invalid_profile = textwrap.dedent(
            """
            id: broken
            type: k8s
            auth:
              vault_role: broken/admin
            policies:
              risk_level: low
              require_approval: false
            """
        ).strip()
        (self.profiles_dir / "broken.yaml").write_text(invalid_profile, encoding="utf-8")

        response = self.client.get("/api/v1/environments/broken")
        self.assertEqual(response.status_code, 422, response.text)
        response_data = response.json()
        # Check that error message contains "invalid"
        self.assertIn("error", response_data)
        self.assertIn("invalid", response_data["error"].lower())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
