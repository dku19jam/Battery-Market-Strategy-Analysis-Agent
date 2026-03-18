import os
import unittest
from unittest.mock import patch


class ConfigTest(unittest.TestCase):
    def test_from_env_loads_defaults_and_api_key(self) -> None:
        from battery_agent.config import Settings

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            settings = Settings.from_env()

        self.assertEqual(settings.openai_api_key, "test-key")
        self.assertEqual(settings.default_companies, ("LG에너지솔루션", "CATL"))
        self.assertEqual(settings.default_model, "gpt-4o-mini")
        self.assertFalse(settings.web_search_enabled)

    def test_from_env_raises_clear_error_without_api_key(self) -> None:
        from battery_agent.config import ConfigError, Settings

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigError) as ctx:
                Settings.from_env()

        self.assertIn("OPENAI_API_KEY", str(ctx.exception))
