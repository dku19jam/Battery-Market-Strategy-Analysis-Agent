import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ConfigTest(unittest.TestCase):
    def test_from_env_loads_defaults_and_api_key(self) -> None:
        from battery_agent.config import Settings

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            settings = Settings.from_env(env_path=Path("/tmp/definitely-missing-battery-agent.env"))

        self.assertEqual(settings.openai_api_key, "test-key")
        self.assertEqual(settings.default_companies, ("LG에너지솔루션", "CATL"))
        self.assertEqual(settings.default_model, "gpt-4o-mini")
        self.assertEqual(settings.embedding_model_id, "Qwen/Qwen3-Embedding-0.6B")
        self.assertEqual(settings.local_corpus_dir, Path("corpus"))
        self.assertIsNone(settings.tavily_api_key)
        self.assertEqual(settings.web_search_max_calls, 3)
        self.assertEqual(settings.web_search_max_results, 5)
        self.assertTrue(settings.web_search_enabled)

    def test_from_env_raises_clear_error_without_api_key(self) -> None:
        from battery_agent.config import ConfigError, Settings

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigError) as ctx:
                Settings.from_env(env_path=Path("/tmp/definitely-missing-battery-agent.env"))

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
                        "TAVILY_API_KEY=tavily-dotenv-key",
                        "BATTERY_AGENT_WEB_SEARCH=true",
                        "BATTERY_AGENT_WEB_SEARCH_MAX_CALLS=7",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                settings = Settings.from_env(env_path=env_path)

        self.assertEqual(settings.openai_api_key, "dotenv-key")
        self.assertEqual(settings.output_root, Path("custom-artifacts"))
        self.assertEqual(settings.tavily_api_key, "tavily-dotenv-key")
        self.assertEqual(settings.web_search_max_calls, 7)
        self.assertTrue(settings.web_search_enabled)

    def test_os_environment_overrides_dotenv_file(self) -> None:
        from battery_agent.config import Settings

        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "OPENAI_API_KEY=dotenv-key",
                        "BATTERY_AGENT_EMBEDDING_MODEL=custom-model",
                        "BATTERY_AGENT_CORPUS_DIR=data/corpus",
                        "TAVILY_API_KEY=dotenv-tavily-key",
                        "BATTERY_AGENT_WEB_SEARCH_MAX_RESULTS=9",
                        "BATTERY_AGENT_WEB_SEARCH_MAX_CALLS=11",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {"OPENAI_API_KEY": "env-key", "TAVILY_API_KEY": "env-tavily-key"},
                clear=True,
            ):
                settings = Settings.from_env(env_path=env_path)

        self.assertEqual(settings.openai_api_key, "env-key")
        self.assertEqual(settings.embedding_model_id, "custom-model")
        self.assertEqual(settings.local_corpus_dir, Path("data/corpus"))
        self.assertEqual(settings.tavily_api_key, "env-tavily-key")
        self.assertEqual(settings.web_search_max_calls, 11)
        self.assertEqual(settings.web_search_max_results, 9)
