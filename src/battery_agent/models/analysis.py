"""Analysis result model."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CompanyAnalysisResult:
    company: str
    strategy_summary: str
    strengths: list[str]
    risks: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CompanyAnalysisResult":
        return cls(
            company=str(data["company"]),
            strategy_summary=str(data["strategy_summary"]),
            strengths=list(data["strengths"]),
            risks=list(data["risks"]),
        )
