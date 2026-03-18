"""Evidence bundle models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class EvidenceItem:
    document_id: str
    snippet: str
    source_type: str
    source: str
    topics: list[str] = field(default_factory=list)
    score: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "EvidenceItem":
        return cls(
            document_id=str(data["document_id"]),
            snippet=str(data["snippet"]),
            source_type=str(data["source_type"]),
            source=str(data["source"]),
            topics=list(data.get("topics", [])),
            score=float(data.get("score", 0.0)),
        )


@dataclass(frozen=True)
class EvidenceBundle:
    company: str
    topics: list[str]
    entries: list[EvidenceItem]
    topic_buckets: dict[str, list[EvidenceItem]]
    missing_topics: list[str]
    next_action: str

    def to_dict(self) -> dict[str, object]:
        return {
            "company": self.company,
            "topics": self.topics,
            "entries": [entry.to_dict() for entry in self.entries],
            "topic_buckets": {
                topic: [entry.to_dict() for entry in entries]
                for topic, entries in self.topic_buckets.items()
            },
            "missing_topics": self.missing_topics,
            "next_action": self.next_action,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "EvidenceBundle":
        return cls(
            company=str(data["company"]),
            topics=list(data["topics"]),
            entries=[EvidenceItem.from_dict(entry) for entry in data.get("entries", [])],
            topic_buckets={
                str(topic): [EvidenceItem.from_dict(entry) for entry in entries]
                for topic, entries in dict(data.get("topic_buckets", {})).items()
            },
            missing_topics=list(data.get("missing_topics", [])),
            next_action=str(data["next_action"]),
        )
