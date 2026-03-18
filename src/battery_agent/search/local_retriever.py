"""Local corpus retrieval."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from battery_agent.rag.vector_index import InMemoryVectorIndex, SearchMatch


@dataclass(frozen=True)
class RetrievalHit:
    document_id: str
    chunk_id: str
    score: float
    text: str
    company: str
    topics: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class LocalRetriever:
    def __init__(
        self,
        index: InMemoryVectorIndex,
        embed_query: Callable[[str], list[float]],
    ) -> None:
        self.index = index
        self.embed_query = embed_query

    def search(
        self,
        company: str,
        queries: list[str],
        top_k: int = 5,
        artifact_path: Path | None = None,
    ) -> list[RetrievalHit]:
        aggregated: dict[str, RetrievalHit] = {}
        for query in queries:
            query_embedding = self.embed_query(query)
            matches = self.index.search(query_embedding, top_k=top_k * 2)
            for match in matches:
                if match.metadata.get("company") != company:
                    continue
                keyword_bonus = _keyword_bonus(query, match.text)
                score = match.score + keyword_bonus
                hit = RetrievalHit(
                    document_id=match.document_id,
                    chunk_id=match.record_id,
                    score=score,
                    text=match.text,
                    company=str(match.metadata.get("company", "")),
                    topics=list(match.metadata.get("topics", [])),
                )
                current = aggregated.get(hit.chunk_id)
                if current is None or hit.score > current.score:
                    aggregated[hit.chunk_id] = hit

        results = sorted(aggregated.values(), key=lambda item: item.score, reverse=True)[:top_k]
        if artifact_path is not None:
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps([result.to_dict() for result in results], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return results


def _keyword_bonus(query: str, text: str) -> float:
    text_lower = text.lower()
    return sum(0.05 for token in query.lower().split() if token in text_lower)
