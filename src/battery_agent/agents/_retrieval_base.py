"""Shared retrieval agent logic."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from battery_agent.models.retrieval import RetrievalItem, RetrievalResult
from battery_agent.search.query_builder import build_company_queries, rewrite_query
from battery_agent.search.web_search import WebSearchResult
from battery_agent.storage.json_store import write_json


class LocalRetrieverLike(Protocol):
    def search(self, company: str, queries: list[str], top_k: int = 5) -> list[RetrievalItem]:
        ...


class WebSearcherLike(Protocol):
    def search(self, query: str) -> list[WebSearchResult]:
        ...


def run_retrieval_agent(
    company: str,
    topic: str,
    local_retriever: LocalRetrieverLike,
    web_searcher: WebSearcherLike | None = None,
    artifact_path: Path | None = None,
    min_hits: int = 2,
) -> RetrievalResult:
    queries = build_company_queries(company, topic)
    items = list(local_retriever.search(company=company, queries=queries, top_k=max(min_hits, 5)))
    used_web_search = False

    if len(items) < min_hits and web_searcher is not None:
        web_query = rewrite_query(f"{company} {topic}", "portfolio diversification")
        web_items = [
            RetrievalItem(
                document_id=result.url,
                chunk_id=f"web-{index}",
                title=result.title,
                text=result.snippet,
                score=0.5,
                source_type="web",
                source=result.source,
                topics=["strategy"],
                url=result.url,
            )
            for index, result in enumerate(web_searcher.search(web_query), start=1)
        ]
        items.extend(web_items)
        used_web_search = bool(web_items)

    result = RetrievalResult(
        company=company,
        queries=queries,
        items=items,
        next_action="curation" if items else "partial",
        used_web_search=used_web_search,
        partial=not bool(items),
    )
    if artifact_path is not None:
        write_json(artifact_path, result.to_dict())
    return result
