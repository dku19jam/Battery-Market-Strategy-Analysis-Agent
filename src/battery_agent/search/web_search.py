"""Limited web search adapter."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    source: str
    snippet: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class LimitedWebSearcher:
    def __init__(
        self,
        provider: Callable[[str], list[WebSearchResult]],
        max_results: int,
        max_per_source: int = 2,
        max_calls: int = 3,
    ) -> None:
        self.provider = provider
        self.max_results = max_results
        self.max_per_source = max_per_source
        self.max_calls = max_calls
        self.calls_made = 0

    def search(self, query: str, artifact_path: Path | None = None) -> list[WebSearchResult]:
        if self.calls_made >= self.max_calls:
            return []
        self.calls_made += 1
        source_counts: dict[str, int] = {}
        filtered: list[WebSearchResult] = []
        for result in self.provider(query):
            current = source_counts.get(result.source, 0)
            if current >= self.max_per_source:
                continue
            filtered.append(result)
            source_counts[result.source] = current + 1
            if len(filtered) >= self.max_results:
                break

        if artifact_path is not None:
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps([item.to_dict() for item in filtered], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return filtered


class TavilySearchProvider:
    def __init__(
        self,
        client: object,
        max_results: int,
        search_depth: str = "basic",
    ) -> None:
        self.client = client
        self.max_results = max_results
        self.search_depth = search_depth

    def __call__(self, query: str) -> list[WebSearchResult]:
        payload = self.client.search(
            query=query,
            max_results=self.max_results,
            search_depth=self.search_depth,
        )
        results: list[WebSearchResult] = []
        for item in payload.get("results", []):
            url = str(item.get("url", "")).strip()
            if not url:
                continue
            results.append(
                WebSearchResult(
                    title=str(item.get("title", "")).strip() or url,
                    url=url,
                    source=_source_from_url(url),
                    snippet=str(item.get("content", item.get("snippet", ""))).strip(),
                )
            )
        return results


def build_tavily_web_searcher(
    api_key: str,
    max_results: int,
    max_per_source: int = 2,
    max_calls: int = 3,
) -> LimitedWebSearcher:
    try:
        from tavily import TavilyClient
    except ImportError as exc:
        raise RuntimeError(
            "tavily-python is required for Tavily web search integration."
        ) from exc

    provider = TavilySearchProvider(
        client=TavilyClient(api_key=api_key),
        max_results=max_results,
    )
    return LimitedWebSearcher(
        provider=provider,
        max_results=max_results,
        max_per_source=max_per_source,
        max_calls=max_calls,
    )


def _source_from_url(url: str) -> str:
    return urlparse(url).netloc or "unknown"
