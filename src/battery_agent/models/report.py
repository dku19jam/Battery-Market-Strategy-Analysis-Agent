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
    metrics: list[dict[str, object]] = field(default_factory=list)
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
            metrics=list(data.get("metrics", [])),
            partial=bool(data.get("partial", False)),
        )


@dataclass(frozen=True)
class SWOTSection:
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    opportunities: list[str] = field(default_factory=list)
    threats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "SWOTSection":
        return cls(
            strengths=list(data.get("strengths", [])),
            weaknesses=list(data.get("weaknesses", [])),
            opportunities=list(data.get("opportunities", [])),
            threats=list(data.get("threats", [])),
        )


@dataclass(frozen=True)
class CompanyMetric:
    company: str
    metric: str
    value: str
    source_hint: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CompanyMetric":
        return cls(
            company=str(data["company"]),
            metric=str(data["metric"]),
            value=str(data["value"]),
            source_hint=str(data.get("source_hint", "")),
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
    swot: SWOTSection
    insights: list[str]
    company_metrics: list[CompanyMetric] = field(default_factory=list)
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
            swot=SWOTSection.from_dict(data.get("swot", {})),
            insights=list(data["insights"]),
            company_metrics=[CompanyMetric.from_dict(item) for item in data.get("company_metrics", [])],
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
