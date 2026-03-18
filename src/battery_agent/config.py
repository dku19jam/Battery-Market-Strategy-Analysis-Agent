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


def _optional_env_value(name: str, dotenv_values: dict[str, str]) -> str | None:
    value = _env_value(name, dotenv_values)
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    default_companies: tuple[str, str]
    default_model: str
    embedding_model_id: str
    default_topic: str
    local_corpus_dir: Path
    output_root: Path
    tavily_api_key: str | None
    web_search_enabled: bool
    web_search_max_calls: int
    web_search_max_results: int
    web_search_max_per_source: int = 4
    chroma_dir: Path = Path("data/chroma")
    chroma_collection: str = "battery-agent"
    embedding_device: str = "auto"
    embedding_batch_size: int = 4
    pdf_min_document_words: int = 200
    pdf_min_page_words: int = 50
    pdf_focus_keywords: tuple[str, ...] = (
        "전략",
        "사업전략",
        "리스크",
        "공급망",
        "시장",
        "배터리",
        "매출",
        "실적",
        "경쟁력",
        "포트폴리오",
        "ESG",
        "수익",
        "글로벌",
        "파이낸스",
        "재무",
        "전기차",
        "ESS",
        "투자",
        "R&D",
    )

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
            chroma_dir=Path(
                _env_value("BATTERY_AGENT_CHROMA_DIR", dotenv_values) or "data/chroma"
            ),
            chroma_collection=(
                _env_value("BATTERY_AGENT_CHROMA_COLLECTION", dotenv_values) or "battery-agent"
            ),
            tavily_api_key=_optional_env_value("TAVILY_API_KEY", dotenv_values),
            web_search_enabled=_env_flag(
                "BATTERY_AGENT_WEB_SEARCH",
                dotenv_values,
                default=True,
            ),
            web_search_max_calls=int(
                _env_value("BATTERY_AGENT_WEB_SEARCH_MAX_CALLS", dotenv_values) or "6"
            ),
            web_search_max_results=int(
                _env_value("BATTERY_AGENT_WEB_SEARCH_MAX_RESULTS", dotenv_values) or "10"
            ),
            web_search_max_per_source=int(
                _env_value("BATTERY_AGENT_WEB_SEARCH_MAX_PER_SOURCE", dotenv_values) or "4"
            ),
            embedding_device=(
                _env_value("BATTERY_AGENT_EMBEDDING_DEVICE", dotenv_values) or "auto"
            ),
            embedding_batch_size=int(
                _env_value("BATTERY_AGENT_EMBEDDING_BATCH_SIZE", dotenv_values) or "4"
            ),
            pdf_min_document_words=int(
                _env_value("BATTERY_AGENT_PDF_MIN_DOCUMENT_WORDS", dotenv_values) or "200"
            ),
            pdf_min_page_words=int(
                _env_value("BATTERY_AGENT_PDF_MIN_PAGE_WORDS", dotenv_values) or "50"
            ),
            pdf_focus_keywords=_parse_comma_keywords(
                _env_value(
                    "BATTERY_AGENT_PDF_FOCUS_KEYWORDS",
                    dotenv_values,
                )
            ),
        )


def _parse_comma_keywords(value: str | None) -> tuple[str, ...]:
    fallback = ",".join(
        (
            "전략,사업전략,리스크,공급망,시장,배터리,매출,실적,경쟁력,포트폴리오,"
            "ESG,수익,글로벌,파이낸스,재무,전기차,ESS,투자,R&D"
        ).split(",")
    )
    raw_value = value if value is not None and value.strip() else fallback
    return tuple(item.strip() for item in raw_value.split(",") if item.strip())
