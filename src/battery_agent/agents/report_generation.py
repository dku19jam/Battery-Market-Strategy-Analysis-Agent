"""Report generation agent."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path

from battery_agent.agents._prompt_builders import (
    report_schema,
    report_system_prompt,
    report_user_prompt,
)
from battery_agent.agents.references import format_reference_block
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


def _localize_sections_to_korean(
    sections: dict[str, str],
    llm_client: StructuredOpenAIClient | object,
    model: str,
) -> dict[str, str]:
    localized_payload = llm_client.generate_json(
        model=model,
        system_prompt=(
            "You are a professional Korean report editor. "
            "모든 항목을 한국어로만 작성해 다시 작성한다. "
            "수치, 문헌 ID, URL, 보고서명 및 표의 수치값은 그대로 유지한다."
        ),
        user_prompt=(
            "다음 최종 보고서 초안을 한국어 버전으로 번역/보정해 JSON으로 반환하세요. "
            "키는 summary, market_background, lg_strategy, catl_strategy, strategy_comparison, swot, "
            "company_metrics, insights 그대로 유지해야 합니다. "
            "MARKET_BACKGROUND, LG_STRATEGY, CATL_STRATEGY, STRATEGY_COMPARISON은 문단형식으로 유지하고, "
            "SWOT는 기존 섹션 텍스트 내의 Strengths/Weaknesses/Opportunities/Threats를 한국어로 정리하세요. "
            "반드시 JSON 만 반환하세요.\n\n"
            f"Draft:{sections}"
        ),
        schema_name="final_report_sections",
        schema=report_schema(),
    )
    localized = {
        "SUMMARY": str(localized_payload.get("summary", "")).strip(),
        "MARKET_BACKGROUND": str(localized_payload.get("market_background", "")).strip(),
        "LG_STRATEGY": str(localized_payload.get("lg_strategy", "")).strip(),
        "CATL_STRATEGY": str(localized_payload.get("catl_strategy", "")).strip(),
        "STRATEGY_COMPARISON": str(localized_payload.get("strategy_comparison", "")).strip(),
        "COMPANY_METRICS": str(localized_payload.get("company_metrics", "")).strip(),
        "SWOT": str(localized_payload.get("swot", "")).strip(),
        "INSIGHTS": str(localized_payload.get("insights", "")).strip(),
    }
    # Merge with original sections and allow empty return fallbacks.
    merged = dict(sections)
    for key, value in localized.items():
        merged[key] = value or sections[key]
    return merged


def _normalize_swot_text(text: str, fallback: str) -> str:
    normalized = text.strip()
    if not normalized:
        return fallback
    json_fragment = None
    if normalized.startswith("{") and normalized.endswith("}"):
        json_fragment = normalized
    else:
        matched = re.search(r"\{.*\}", normalized, flags=re.S)
        if matched:
            json_fragment = matched.group(0)
    if json_fragment is not None:
        try:
            payload = json.loads(json_fragment)
            strengths = payload.get("strengths", [])
            weaknesses = payload.get("weaknesses", [])
            opportunities = payload.get("opportunities", [])
            threats = payload.get("threats", [])
            if all(isinstance(value, list) for value in (strengths, weaknesses, opportunities, threats)):
                parts: list[str] = []
                for title, items in (
                    ("Strengths", strengths),
                    ("Weaknesses", weaknesses),
                    ("Opportunities", opportunities),
                    ("Threats", threats),
                ):
                    parts.append(f"### {title}")
                    if items:
                        parts.extend(f"- {item}" for item in items)
                    else:
                        parts.append("- 자료 부족")
                    parts.append("")
                return "\n".join(parts).strip()
        except (json.JSONDecodeError, AttributeError):
            return fallback
    return normalized


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
        "COMPANY_METRICS": _build_metrics_table(comparison),
        "SWOT": _build_swot_markdown(comparison),
        "INSIGHTS": "\n".join(comparison.insights),
        "REFERENCE": format_reference_block(references.entries),
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

    sections = {
        "SUMMARY": summary or default_sections["SUMMARY"],
        "MARKET_BACKGROUND": str(payload.get("market_background", "")).strip()
        or default_sections["MARKET_BACKGROUND"],
        "LG_STRATEGY": str(payload.get("lg_strategy", "")).strip() or default_sections["LG_STRATEGY"],
        "CATL_STRATEGY": str(payload.get("catl_strategy", "")).strip()
        or default_sections["CATL_STRATEGY"],
        "STRATEGY_COMPARISON": str(payload.get("strategy_comparison", "")).strip()
        or default_sections["STRATEGY_COMPARISON"],
        "COMPANY_METRICS": default_sections["COMPANY_METRICS"],
        "SWOT": default_sections["SWOT"],
        "INSIGHTS": str(payload.get("insights", "")).strip() or default_sections["INSIGHTS"],
        "REFERENCE": default_sections["REFERENCE"],
    }

    try:
        sections = _localize_sections_to_korean(sections, llm_client, model)
    except Exception:
        return sections

    sections["SWOT"] = _normalize_swot_text(sections["SWOT"], default_sections["SWOT"])
    return sections



def _build_swot_markdown(comparison: ComparisonResult) -> str:
    parts: list[str] = []
    for title, items in (
        ("Strengths", comparison.swot.strengths),
        ("Weaknesses", comparison.swot.weaknesses),
        ("Opportunities", comparison.swot.opportunities),
        ("Threats", comparison.swot.threats),
    ):
        parts.append(f"### {title}")
        if items:
            parts.extend(f"- {item}" for item in items)
        else:
            parts.append("- 자료 부족")
        parts.append("")
    return "\n".join(parts).strip()


def _build_metrics_table(comparison: ComparisonResult) -> str:
    if not comparison.company_metrics:
        return "정량 지표 근거가 충분하지 않아 표를 생략한다."

    lines = [
        "| 회사 | 지표 | 값 | 출처 |",
        "| --- | --- | --- | --- |",
    ]
    for item in comparison.company_metrics:
        lines.append(
            f"| {item.company} | {item.metric} | {item.value} | {item.source_hint or '-'} |"
        )
    return "\n".join(lines)
