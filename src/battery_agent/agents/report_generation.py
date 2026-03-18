"""Report generation agent."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from battery_agent.agents._prompt_builders import (
    report_schema,
    report_system_prompt,
    report_user_prompt,
)
from battery_agent.llm.openai_structured import StructuredOpenAIClient
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
    llm_client: StructuredOpenAIClient | object | None = None,
    model: str = "gpt-4o-mini",
    markdown_path: Path | None = None,
) -> GeneratedReport:
    partial = bool(
        lg_analysis.partial
        or catl_analysis.partial
        or comparison.next_action != "reference"
        or not references.entries
    )
    sections = _build_sections(
        topic=topic,
        lg_analysis=lg_analysis,
        catl_analysis=catl_analysis,
        comparison=comparison,
        references=references,
        partial=partial,
        llm_client=llm_client,
        model=model,
    )
    markdown = render_report_markdown(
        title="배터리 시장 전략 분석 보고서",
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


def _build_sections(
    *,
    topic: str,
    lg_analysis: CompanyAnalysisResult,
    catl_analysis: CompanyAnalysisResult,
    comparison: ComparisonResult,
    references: ReferenceResult,
    partial: bool,
    llm_client: StructuredOpenAIClient | object | None,
    model: str,
) -> dict[str, str]:
    default_sections = {
        "SUMMARY": _build_summary(topic, comparison, partial),
        "MARKET_BACKGROUND": f"주제: {topic}",
        "LG_STRATEGY": lg_analysis.strategy_summary,
        "CATL_STRATEGY": catl_analysis.strategy_summary,
        "STRATEGY_COMPARISON": "\n".join(comparison.strategy_differences),
        "SWOT": "\n".join(comparison.swot),
        "INSIGHTS": "\n".join(comparison.insights),
        "REFERENCE": "\n".join(f"- {entry.formatted_reference}" for entry in references.entries),
    }
    if llm_client is None:
        return default_sections

    payload = llm_client.generate_json(
        model=model,
        system_prompt=report_system_prompt(),
        user_prompt=report_user_prompt(
            topic=topic,
            lg_analysis=lg_analysis,
            catl_analysis=catl_analysis,
            comparison=comparison,
            references=[entry.formatted_reference for entry in references.entries],
            partial=partial,
        ),
        schema_name="final_report_sections",
        schema=report_schema(),
    )
    summary = str(payload.get("summary", "")).strip()
    if partial and "근거" not in summary:
        summary = f"{summary} 근거가 다소 제한적이므로 해석은 보수적으로 제시한다.".strip()

    return {
        "SUMMARY": summary or default_sections["SUMMARY"],
        "MARKET_BACKGROUND": str(payload.get("market_background", "")).strip()
        or default_sections["MARKET_BACKGROUND"],
        "LG_STRATEGY": str(payload.get("lg_strategy", "")).strip() or default_sections["LG_STRATEGY"],
        "CATL_STRATEGY": str(payload.get("catl_strategy", "")).strip()
        or default_sections["CATL_STRATEGY"],
        "STRATEGY_COMPARISON": str(payload.get("strategy_comparison", "")).strip()
        or default_sections["STRATEGY_COMPARISON"],
        "SWOT": str(payload.get("swot", "")).strip() or default_sections["SWOT"],
        "INSIGHTS": str(payload.get("insights", "")).strip() or default_sections["INSIGHTS"],
        "REFERENCE": default_sections["REFERENCE"],
    }
