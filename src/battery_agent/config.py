"""Runtime configuration loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    """Raised when required configuration is missing."""


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    default_companies: tuple[str, str]
    default_model: str
    default_topic: str
    output_root: Path
    web_search_enabled: bool

    @classmethod
    def from_env(cls) -> "Settings":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ConfigError("OPENAI_API_KEY is required to run battery-agent.")

        return cls(
            openai_api_key=api_key,
            default_companies=("LG에너지솔루션", "CATL"),
            default_model="gpt-4o-mini",
            default_topic="배터리 시장 전략 비교",
            output_root=Path(os.getenv("BATTERY_AGENT_OUTPUT_DIR", "artifacts")),
            web_search_enabled=_env_flag("BATTERY_AGENT_WEB_SEARCH", default=False),
        )
