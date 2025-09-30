"""Unit tests for configuration settings."""

import unittest

from config.settings import Settings, get_settings


class SettingsTests(unittest.TestCase):
    """Validate the behaviour of the Settings loader."""

    def test_local_provider_enabled_by_default(self):
        settings = get_settings()
        enabled_providers = [p.name for p in settings.llm_providers if p.enabled]
        self.assertIn("local", enabled_providers)
        self.assertGreaterEqual(len(settings.llm_providers), 1)

    def test_orchestrator_defaults_present(self):
        settings = get_settings()
        self.assertEqual(settings.orchestrator.planner.name, "planner")
        self.assertEqual(settings.orchestrator.executor.name, "executor")
        self.assertEqual(settings.orchestrator.verifier.name, "verifier")

    def test_remote_providers_disabled_by_default(self):
        settings = Settings(
            llm_providers=[
                {"name": "local", "type": "local", "enabled": True, "config": {}},
                {"name": "gemini", "type": "gemini", "enabled": True, "config": {}},
                {"name": "ollama", "type": "ollama", "enabled": True, "config": {}},
            ]
        )
        providers = {provider.name: provider for provider in settings.llm_providers}
        self.assertTrue(providers["local"].enabled)
        self.assertFalse(providers["gemini"].enabled)
        self.assertFalse(providers["ollama"].enabled)

    def test_remote_provider_can_be_enabled_via_flag(self):
        settings = Settings(
            enable_gemini_provider=True,
            llm_providers=[
                {"name": "local", "type": "local", "enabled": True, "config": {}},
                {"name": "gemini", "type": "gemini", "enabled": False, "config": {}},
            ],
        )
        providers = {provider.name: provider for provider in settings.llm_providers}
        self.assertTrue(providers["gemini"].enabled)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
