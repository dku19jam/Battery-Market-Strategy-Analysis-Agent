"""In-memory vector index."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class VectorRecord:
    record_id: str
    document_id: str
    text: str
    embedding: list[float]
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SearchMatch:
    record_id: str
    document_id: str
    score: float
    text: str
    metadata: dict[str, object]


class InMemoryVectorIndex:
    def __init__(self) -> None:
        self._records: list[VectorRecord] = []

    def add(self, records: list[VectorRecord]) -> None:
        self._records.extend(records)

    def dump(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps([record.to_dict() for record in self._records], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "InMemoryVectorIndex":
        payload = json.loads(path.read_text(encoding="utf-8"))
        index = cls()
        index.add([VectorRecord(**item) for item in payload])
        return index

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[SearchMatch]:
        scored = [
            SearchMatch(
                record_id=record.record_id,
                document_id=record.document_id,
                score=_cosine_similarity(query_embedding, record.embedding),
                text=record.text,
                metadata=record.metadata,
            )
            for record in self._records
        ]
        return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = sum(value * value for value in left) ** 0.5 or 1.0
    right_norm = sum(value * value for value in right) ** 0.5 or 1.0
    return numerator / (left_norm * right_norm)
