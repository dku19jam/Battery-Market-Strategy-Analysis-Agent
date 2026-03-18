"""Chroma-based local retrieval."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from battery_agent.rag.chroma_store import ChromaVectorStore


@dataclass(frozen=True)
class ChromaRetrievalHit:
    document_id: str
    chunk_id: str
    score: float
    text: str
    company: str
    topics: list[str]
    source_type: str = "pdf"
    source: str = "chroma"
    url: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class ChromaRetriever:
    def __init__(
        self,
        store: ChromaVectorStore,
        embed_query: Callable[[str], list[float]],
        logger: logging.Logger | None = None,
    ) -> None:
        self.store = store
        self.embed_query = embed_query
        self.logger = logger

    def search(
        self,
        company: str,
        queries: list[str],
        top_k: int = 5,
        artifact_path: Path | None = None,
    ) -> list[ChromaRetrievalHit]:
        aggregated: dict[str, ChromaRetrievalHit] = {}
        for query in queries:
            if self.logger is not None:
                self.logger.info("chroma retrieval company=%s query=%s", company, query)
            query_embedding = self.embed_query(query)
            hits = self.store.search(query_embedding=query_embedding, company=company, top_k=top_k * 2)
            for hit in hits:
                resolved = ChromaRetrievalHit(
                    document_id=hit.document_id,
                    chunk_id=hit.chunk_id,
                    score=hit.score,
                    text=hit.text,
                    company=str(hit.metadata.get("company", company)),
                    topics=list(hit.metadata.get("topics", [])),
                    source_type=str(hit.metadata.get("source_type", "pdf")),
                    source=str(hit.metadata.get("source", "chroma")),
                    url=hit.metadata.get("url"),
                )
                current = aggregated.get(resolved.chunk_id)
                if current is None or resolved.score > current.score:
                    aggregated[resolved.chunk_id] = resolved

        results = sorted(aggregated.values(), key=lambda item: item.score, reverse=True)[:top_k]
        if artifact_path is not None:
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps([result.to_dict() for result in results], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return results
