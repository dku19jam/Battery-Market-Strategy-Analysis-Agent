"""Analysis result models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class AnalysisMetric:
    metric: str
    value: str
    source_hint: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "AnalysisMetric":
        return cls(
            metric=str(data["metric"]),
            value=str(data["value"]),
            source_hint=str(data.get("source_hint", "")),
        )


@dataclass(frozen=True)
class CompanyAnalysisResult:
    company: str
    strategy_summary: str
    strengths: list[str]
    risks: list[str]
    citations: list[str] = field(default_factory=list)
    metrics: list[AnalysisMetric] = field(default_factory=list)
    analysis_notes: str = ""
    next_action: str = "comparison"
    partial: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CompanyAnalysisResult":
        return cls(
            company=str(data["company"]),
            strategy_summary=str(data["strategy_summary"]),
            strengths=list(data["strengths"]),
            risks=list(data["risks"]),
            citations=list(data.get("citations", [])),
            metrics=[AnalysisMetric.from_dict(item) for item in data.get("metrics", [])],
            analysis_notes=str(data.get("analysis_notes", "")),
            next_action=str(data.get("next_action", "comparison")),
            partial=bool(data.get("partial", False)),
        )
