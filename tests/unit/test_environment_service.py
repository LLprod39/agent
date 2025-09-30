"""Tests for the environment profile service and dependencies."""

import asyncio
import tempfile
import textwrap
import unittest
from pathlib import Path

from fastapi import HTTPException

from apps.api.dependencies import get_environment_profile
from apps.api.services.environment_service import EnvironmentService


class EnvironmentServiceTests(unittest.TestCase):
    """Verify caching and error propagation for environment profiles."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.profiles_path = Path(self.temp_dir.name)
        self.profile_id = "test-env"
        profile_yaml = textwrap.dedent(
            """
            id: test-env
            type: k8s
            networking:
              proxy:
                http: http://proxy.local:3128
            auth:
              vault_role: test/role
            policies:
              risk_level: low
              require_approval: false
            """
        ).strip()
        (self.profiles_path / f"{self.profile_id}.yaml").write_text(profile_yaml, encoding="utf-8")
        self.service = EnvironmentService(self.profiles_path, cache_ttl=60)

    def tearDown(self) -> None:  # pragma: no cover - cleanup hook
        self.temp_dir.cleanup()

    def test_get_profile_returns_cached_data(self):
        async def run_flow():
            profile_data = await get_environment_profile(self.profile_id, service=self.service)
            self.assertEqual(profile_data["id"], self.profile_id)
            # Remove the file and fetch again; cached value should be returned
            (self.profiles_path / f"{self.profile_id}.yaml").unlink()
            cached_data = await get_environment_profile(self.profile_id, service=self.service)
            self.assertEqual(cached_data["id"], self.profile_id)

        asyncio.run(run_flow())

    def test_missing_profile_raises_http_404(self):
        async def run_flow():
            with self.assertRaises(HTTPException) as exc:
                await get_environment_profile("absent", service=self.service)
            self.assertEqual(exc.exception.status_code, 404)

        asyncio.run(run_flow())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
