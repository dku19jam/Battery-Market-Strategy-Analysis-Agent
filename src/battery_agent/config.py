"""Runtime configuration loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    """Raised when required configuration is missing."""


def _load_dotenv(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def _env_value(name: str, dotenv_values: dict[str, str]) -> str | None:
    return os.getenv(name, dotenv_values.get(name))


def _env_flag(name: str, dotenv_values: dict[str, str], default: bool = False) -> bool:
    value = _env_value(name, dotenv_values)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    default_companies: tuple[str, str]
    default_model: str
    embedding_model_id: str
    default_topic: str
    local_corpus_dir: Path
    output_root: Path
    web_search_enabled: bool
    web_search_max_results: int

    @classmethod
    def from_env(cls, env_path: Path | None = None) -> "Settings":
        dotenv_path = env_path or Path(".env")
        dotenv_values = _load_dotenv(dotenv_path)

        api_key = _env_value("OPENAI_API_KEY", dotenv_values)
        if not api_key:
            raise ConfigError("OPENAI_API_KEY is required to run battery-agent.")

        return cls(
            openai_api_key=api_key,
            default_companies=("LG에너지솔루션", "CATL"),
            default_model="gpt-4o-mini",
            embedding_model_id=(
                _env_value("BATTERY_AGENT_EMBEDDING_MODEL", dotenv_values)
                or "Qwen/Qwen3-Embedding-0.6B"
            ),
            default_topic="배터리 시장 전략 비교",
            local_corpus_dir=Path(
                _env_value("BATTERY_AGENT_CORPUS_DIR", dotenv_values) or "corpus"
            ),
            output_root=Path(
                _env_value("BATTERY_AGENT_OUTPUT_DIR", dotenv_values) or "artifacts"
            ),
            web_search_enabled=_env_flag(
                "BATTERY_AGENT_WEB_SEARCH",
                dotenv_values,
                default=False,
            ),
            web_search_max_results=int(
                _env_value("BATTERY_AGENT_WEB_SEARCH_MAX_RESULTS", dotenv_values) or "5"
            ),
        )
