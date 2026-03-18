"""Report generation agent."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from battery_agent.models.analysis import CompanyAnalysisResult
from battery_agent.models.report import ComparisonResult, ReferenceResult
from battery_agent.reporting.markdown_renderer import render_report_markdown, save_report_markdown


PARTIAL_REPORT_MESSAGE = "일부 근거가 제한적이므로 해석은 보수적으로 제시한다."
FAILURE_REPORT_MESSAGE = "핵심 근거가 부족하여 전체 비교 결론을 확정할 수 없다."


@dataclass(frozen=True)
class GeneratedReport:
    markdown: str
    partial: bool
    next_action: str = "pdf_render"


def build_report(
    topic: str,
    lg_analysis: CompanyAnalysisResult,
    catl_analysis: CompanyAnalysisResult,
    comparison: ComparisonResult,
    references: ReferenceResult,
    markdown_path: Path | None = None,
) -> GeneratedReport:
    partial = bool(
        lg_analysis.partial
        or catl_analysis.partial
        or comparison.next_action != "reference"
        or not references.entries
    )
    sections = {
        "SUMMARY": _build_summary(topic, comparison, partial),
        "MARKET_BACKGROUND": f"주제: {topic}",
        "LG_STRATEGY": lg_analysis.strategy_summary,
        "CATL_STRATEGY": catl_analysis.strategy_summary,
        "STRATEGY_COMPARISON": "\n".join(comparison.strategy_differences),
        "SWOT": "\n".join(comparison.swot),
        "INSIGHTS": "\n".join(comparison.insights),
        "REFERENCE": "\n".join(f"- {entry.formatted_reference}" for entry in references.entries),
    }
    markdown = render_report_markdown(
        title="Battery Market Strategy Analysis",
        sections=sections,
        partial=partial,
        partial_message=PARTIAL_REPORT_MESSAGE if partial else None,
        failure_message=FAILURE_REPORT_MESSAGE if not references.entries else None,
    )
    if markdown_path is not None:
        save_report_markdown(markdown_path, markdown)
    return GeneratedReport(markdown=markdown, partial=partial)


def _build_summary(topic: str, comparison: ComparisonResult, partial: bool) -> str:
    base = comparison.insights[0] if comparison.insights else f"{topic} 비교 결과를 요약한다."
    if partial:
        return f"{base} {PARTIAL_REPORT_MESSAGE}"
    return base
