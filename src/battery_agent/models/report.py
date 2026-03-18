"""Report and comparison models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ComparisonResult:
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

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "ReportArtifact":
        return cls(**data)
