"""Shared retrieval agent logic."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from battery_agent.models.retrieval import RetrievalItem, RetrievalResult
from battery_agent.search.query_builder import (
    build_company_queries,
    build_web_search_queries,
)
from battery_agent.search.web_search import WebSearchResult
from battery_agent.storage.json_store import write_json


class LocalRetrieverLike(Protocol):
    def search(self, company: str, queries: list[str], top_k: int = 5) -> list[object]:
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
    items = [
        _coerce_retrieval_item(item)
        for item in local_retriever.search(company=company, queries=queries, top_k=max(min_hits, 5))
    ]
    used_web_search = False

    if web_searcher is not None:
        web_items: list[RetrievalItem] = []
        seen_urls: set[str] = set()
        web_index = 1
        for web_query in build_web_search_queries(company, topic):
            for result in web_searcher.search(web_query):
                if result.url in seen_urls:
                    continue
                web_items.append(
                    RetrievalItem(
                        document_id=result.url,
                        chunk_id=f"web-{web_index}",
                        title=result.title,
                        text=result.snippet,
                        score=0.5,
                        source_type="web",
                        source=result.source,
                        topics=["strategy"],
                        url=result.url,
                    )
                )
                web_index += 1
                seen_urls.add(result.url)

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


def _coerce_retrieval_item(item: object) -> RetrievalItem:
    if isinstance(item, RetrievalItem):
        return item
    return RetrievalItem(
        document_id=str(getattr(item, "document_id")),
        chunk_id=str(getattr(item, "chunk_id")),
        title=str(getattr(item, "title", getattr(item, "document_id", ""))),
        text=str(getattr(item, "text")),
        score=float(getattr(item, "score")),
        source_type=str(getattr(item, "source_type", "local")),
        source=str(getattr(item, "source", "")) or "local",
        topics=list(getattr(item, "topics", [])),
        url=getattr(item, "url", None),
    )
