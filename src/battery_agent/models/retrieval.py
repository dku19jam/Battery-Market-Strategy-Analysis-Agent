"""Retrieval result model."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RetrievalResult:
    company: str
    queries: list[str]
    document_ids: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "RetrievalResult":
        return cls(
            company=str(data["company"]),
            queries=list(data["queries"]),
            document_ids=list(data["document_ids"]),
        )
