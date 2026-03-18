"""Limited web search adapter."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


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
    ) -> None:
        self.provider = provider
        self.max_results = max_results
        self.max_per_source = max_per_source

    def search(self, query: str, artifact_path: Path | None = None) -> list[WebSearchResult]:
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
