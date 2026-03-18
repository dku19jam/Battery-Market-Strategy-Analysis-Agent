"""Report and comparison models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class NormalizedCompanyAnalysis:
    company: str
    strategy_summary: str
    strengths: list[str]
    risks: list[str]
    citations: list[str] = field(default_factory=list)
    partial: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "NormalizedCompanyAnalysis":
        return cls(
            company=str(data["company"]),
            strategy_summary=str(data["strategy_summary"]),
            strengths=list(data.get("strengths", [])),
            risks=list(data.get("risks", [])),
            citations=list(data.get("citations", [])),
            partial=bool(data.get("partial", False)),
        )


@dataclass(frozen=True)
class ReferenceEntry:
    document_id: str
    source_type: str
    formatted_reference: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ReferenceEntry":
        return cls(
            document_id=str(data["document_id"]),
            source_type=str(data["source_type"]),
            formatted_reference=str(data["formatted_reference"]),
        )


@dataclass(frozen=True)
class ReferenceResult:
    entries: list[ReferenceEntry]
    next_action: str = "report_generation"

    def to_dict(self) -> dict[str, object]:
        return {
            "entries": [entry.to_dict() for entry in self.entries],
            "next_action": self.next_action,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ReferenceResult":
        return cls(
            entries=[ReferenceEntry.from_dict(item) for item in data.get("entries", [])],
            next_action=str(data.get("next_action", "report_generation")),
        )


@dataclass(frozen=True)
class ComparisonResult:
    normalized_companies: list[NormalizedCompanyAnalysis]
    strategy_differences: list[str]
    strengths_weaknesses: list[str]
    swot: list[str]
    insights: list[str]
    refinement_requests: list[str] = field(default_factory=list)
    next_action: str = "reference"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ComparisonResult":
        return cls(
            normalized_companies=[
                NormalizedCompanyAnalysis.from_dict(item)
                for item in data.get("normalized_companies", [])
            ],
            strategy_differences=list(data["strategy_differences"]),
            strengths_weaknesses=list(data["strengths_weaknesses"]),
            swot=list(data["swot"]),
            insights=list(data["insights"]),
            refinement_requests=list(data.get("refinement_requests", [])),
            next_action=str(data.get("next_action", "reference")),
        )


@dataclass(frozen=True)
class ReportArtifact:
    title: str
    markdown_path: str
    pdf_path: str
    partial: bool = False

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "ReportArtifact":
        return cls(**data)
