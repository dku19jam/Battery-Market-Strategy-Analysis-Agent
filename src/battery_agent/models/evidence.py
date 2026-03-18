"""Evidence bundle model."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class EvidenceBundle:
    company: str
    topics: list[str]
    document_ids: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "EvidenceBundle":
        return cls(
            company=str(data["company"]),
            topics=list(data["topics"]),
            document_ids=list(data["document_ids"]),
        )
