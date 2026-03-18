"""Retrieval result models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class RetrievalItem:
    document_id: str
    chunk_id: str
    title: str
    text: str
    score: float
    source_type: str
    source: str
    topics: list[str] = field(default_factory=list)
    url: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "RetrievalItem":
        return cls(
            document_id=str(data["document_id"]),
            chunk_id=str(data["chunk_id"]),
            title=str(data["title"]),
            text=str(data["text"]),
            score=float(data["score"]),
            source_type=str(data["source_type"]),
            source=str(data["source"]),
            topics=list(data.get("topics", [])),
            url=data.get("url") if data.get("url") else None,
        )


@dataclass(frozen=True)
class RetrievalResult:
    company: str
    queries: list[str]
    items: list[RetrievalItem]
    next_action: str
    used_web_search: bool = False
    partial: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "company": self.company,
            "queries": self.queries,
            "items": [item.to_dict() for item in self.items],
            "next_action": self.next_action,
            "used_web_search": self.used_web_search,
            "partial": self.partial,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "RetrievalResult":
        return cls(
            company=str(data["company"]),
            queries=list(data["queries"]),
            items=[RetrievalItem.from_dict(item) for item in data.get("items", [])],
            next_action=str(data["next_action"]),
            used_web_search=bool(data.get("used_web_search", False)),
            partial=bool(data.get("partial", False)),
        )
