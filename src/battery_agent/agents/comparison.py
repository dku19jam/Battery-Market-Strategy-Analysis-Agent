"""Comparison evaluation agent."""

from __future__ import annotations

from battery_agent.models.analysis import CompanyAnalysisResult
from battery_agent.models.report import ComparisonResult


def run_comparison(
    lg_analysis: CompanyAnalysisResult,
    catl_analysis: CompanyAnalysisResult,
) -> ComparisonResult:
    refinement_requests: list[str] = []
    if lg_analysis.partial:
        refinement_requests.append("LG에너지솔루션")
    if catl_analysis.partial:
        refinement_requests.append("CATL")

    return ComparisonResult(
        strategy_differences=[
            f"LG: {lg_analysis.strategy_summary}",
            f"CATL: {catl_analysis.strategy_summary}",
        ],
        strengths_weaknesses=[
            f"LG 강점: {', '.join(lg_analysis.strengths)}",
            f"CATL 강점: {', '.join(catl_analysis.strengths)}",
            f"LG 리스크: {', '.join(lg_analysis.risks)}",
            f"CATL 리스크: {', '.join(catl_analysis.risks)}",
        ],
        swot=[
            f"Strength: {lg_analysis.strengths[0]}",
            f"Strength: {catl_analysis.strengths[0]}",
            f"Risk: {lg_analysis.risks[0]}",
            f"Risk: {catl_analysis.risks[0]}",
        ],
        insights=[
            "두 기업 모두 다각화 전략과 리스크 관리 역량 비교가 핵심이다.",
        ],
        refinement_requests=refinement_requests,
        next_action="reference" if not refinement_requests else "analysis_refinement",
    )
