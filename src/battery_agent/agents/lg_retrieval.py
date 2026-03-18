"""LG retrieval agent."""

from __future__ import annotations

from pathlib import Path

from battery_agent.agents._retrieval_base import (
    LocalRetrieverLike,
    WebSearcherLike,
    run_retrieval_agent,
)
from battery_agent.models.retrieval import RetrievalResult


def run_lg_retrieval(
    topic: str,
    local_retriever: LocalRetrieverLike,
    web_searcher: WebSearcherLike | None = None,
    artifact_path: Path | None = None,
    min_hits: int = 2,
) -> RetrievalResult:
    return run_retrieval_agent(
        company="LG에너지솔루션",
        topic=topic,
        local_retriever=local_retriever,
        web_searcher=web_searcher,
        artifact_path=artifact_path,
        min_hits=min_hits,
    )
