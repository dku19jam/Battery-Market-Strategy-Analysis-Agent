import os
import tempfile
import unittest
from pathlib import Path
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

    def test_from_env_reads_dotenv_file(self) -> None:
        from battery_agent.config import Settings

        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "OPENAI_API_KEY=dotenv-key",
                        "BATTERY_AGENT_OUTPUT_DIR=custom-artifacts",
                        "BATTERY_AGENT_WEB_SEARCH=true",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                settings = Settings.from_env(env_path=env_path)

        self.assertEqual(settings.openai_api_key, "dotenv-key")
        self.assertEqual(settings.output_root, Path("custom-artifacts"))
        self.assertTrue(settings.web_search_enabled)

    def test_os_environment_overrides_dotenv_file(self) -> None:
        from battery_agent.config import Settings

        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text("OPENAI_API_KEY=dotenv-key", encoding="utf-8")

            with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}, clear=True):
                settings = Settings.from_env(env_path=env_path)

        self.assertEqual(settings.openai_api_key, "env-key")
