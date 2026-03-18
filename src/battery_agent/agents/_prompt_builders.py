"""Dynamic prompt construction helpers for analysis and comparison."""

from __future__ import annotations

import json

from battery_agent.models.analysis import CompanyAnalysisResult
from battery_agent.models.evidence import EvidenceBundle, EvidenceItem
from battery_agent.models.report import ComparisonResult, NormalizedCompanyAnalysis


def analysis_system_prompt(company: str) -> str:
    return (
        f"You are the {company} analysis agent. "
        "Analyze only the target company. "
        "Do not mention the competitor directly. "
        "Use only provided evidence. "
        "If the evidence includes quantified company data, extract it into structured metrics. "
        "Return valid JSON that matches the schema."
    )


def analysis_user_prompt(bundle: EvidenceBundle) -> str:
    payload = {
        "company": bundle.company,
        "topics": bundle.topics,
        "missing_topics": bundle.missing_topics,
        "topic_buckets": {
            topic: [_serialize_evidence(entry) for entry in entries]
            for topic, entries in bundle.topic_buckets.items()
        },
        "citation_candidates": sorted({entry.document_id for entry in bundle.entries}),
        "partial": bool(bundle.missing_topics),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def analysis_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "strategy_summary": {"type": "string"},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "risks": {"type": "array", "items": {"type": "string"}},
            "citations": {"type": "array", "items": {"type": "string"}},
            "metrics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "metric": {"type": "string"},
                        "value": {"type": "string"},
                        "source_hint": {"type": "string"},
                    },
                    "required": ["metric", "value", "source_hint"],
                    "additionalProperties": False,
                },
            },
            "analysis_notes": {"type": "string"},
        },
        "required": ["strategy_summary", "strengths", "risks", "citations", "metrics", "analysis_notes"],
        "additionalProperties": False,
    }


def comparison_system_prompt() -> str:
    return (
        "You are the comparison evaluation agent. "
        "Compare only the two structured company analyses provided. "
        "Do not invent evidence. "
        "Provide SWOT broken down by strengths, weaknesses, opportunities, and threats. "
        "If quantified company data is present, include company_metrics using only provided evidence. "
        "Return valid JSON that matches the schema."
    )


def comparison_user_prompt(
    lg_analysis: CompanyAnalysisResult,
    catl_analysis: CompanyAnalysisResult,
) -> str:
    normalized = [
        _normalize_company_analysis(lg_analysis).to_dict(),
        _normalize_company_analysis(catl_analysis).to_dict(),
    ]
    return json.dumps({"normalized_companies": normalized}, ensure_ascii=False, indent=2)


def comparison_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "normalized_companies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "company": {"type": "string"},
                        "strategy_summary": {"type": "string"},
                        "strengths": {"type": "array", "items": {"type": "string"}},
                        "risks": {"type": "array", "items": {"type": "string"}},
                        "metrics": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "metric": {"type": "string"},
                                    "value": {"type": "string"},
                                    "source_hint": {"type": "string"},
                                },
                                "required": ["metric", "value", "source_hint"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["company", "strategy_summary", "strengths", "risks", "metrics"],
                    "additionalProperties": False,
                },
            },
            "strategy_differences": {"type": "array", "items": {"type": "string"}},
            "strengths_weaknesses": {"type": "array", "items": {"type": "string"}},
            "swot": {
                "type": "object",
                "properties": {
                    "strengths": {"type": "array", "items": {"type": "string"}},
                    "weaknesses": {"type": "array", "items": {"type": "string"}},
                    "opportunities": {"type": "array", "items": {"type": "string"}},
                    "threats": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["strengths", "weaknesses", "opportunities", "threats"],
                "additionalProperties": False,
            },
            "insights": {"type": "array", "items": {"type": "string"}},
            "company_metrics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "company": {"type": "string"},
                        "metric": {"type": "string"},
                        "value": {"type": "string"},
                        "source_hint": {"type": "string"},
                    },
                    "required": ["company", "metric", "value", "source_hint"],
                    "additionalProperties": False,
                },
            },
            "refinement_requests": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "normalized_companies",
            "strategy_differences",
            "strengths_weaknesses",
            "swot",
            "insights",
            "company_metrics",
            "refinement_requests",
        ],
        "additionalProperties": False,
    }


def report_system_prompt() -> str:
    return (
        "You are the final report generation agent. "
        "반드시 결과물을 한국어로 만들어낼것. "
        "summary 생성 시 증거가 부족해도 만들어 낼 수 있는 최선의 결과물을 만들어내고 "
        "증거가 조금 부족하다는 정도의 코멘트를 추가할 것. "
        "각 항목의 내용은 최종 보고서만으로도 파악이 가능하게 세세히 작성할 것. "
        "SWOT은 반드시 Strengths, Weaknesses, Opportunities, Threats 항목별로 나누어 작성할 것. "
        "회사별 수치화된 데이터가 있으면 Markdown 표 형식으로 COMPANY_METRICS 섹션에 정리할 것. "
        "Do not invent sources that are not included in the input. "
        "Return valid JSON that matches the schema."
    )


def report_user_prompt(
    topic: str,
    lg_analysis: CompanyAnalysisResult,
    catl_analysis: CompanyAnalysisResult,
    comparison: ComparisonResult,
    references: list[str],
    partial: bool,
) -> str:
    payload = {
        "topic": topic,
        "partial": partial,
        "lg_analysis": {
            "company": lg_analysis.company,
            "strategy_summary": lg_analysis.strategy_summary,
            "strengths": lg_analysis.strengths,
            "risks": lg_analysis.risks,
            "citations": lg_analysis.citations,
            "metrics": [metric.to_dict() for metric in lg_analysis.metrics],
            "analysis_notes": lg_analysis.analysis_notes,
            "partial": lg_analysis.partial,
        },
        "catl_analysis": {
            "company": catl_analysis.company,
            "strategy_summary": catl_analysis.strategy_summary,
            "strengths": catl_analysis.strengths,
            "risks": catl_analysis.risks,
            "citations": catl_analysis.citations,
            "metrics": [metric.to_dict() for metric in catl_analysis.metrics],
            "analysis_notes": catl_analysis.analysis_notes,
            "partial": catl_analysis.partial,
        },
        "comparison": comparison.to_dict() if hasattr(comparison, "to_dict") else comparison,
        "references": references,
        "requirements": {
            "language": "ko",
            "summary_must_be_best_effort_even_if_evidence_is_limited": True,
            "include_short_limitations_note_when_evidence_is_limited": True,
            "sections_must_be_self_contained_and_detailed": True,
            "swot_must_be_written_by_category": True,
            "include_company_metrics_markdown_table_when_available": True,
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def report_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "market_background": {"type": "string"},
            "lg_strategy": {"type": "string"},
            "catl_strategy": {"type": "string"},
            "strategy_comparison": {"type": "string"},
            "swot": {"type": "string"},
            "company_metrics": {"type": "string"},
            "insights": {"type": "string"},
        },
        "required": [
            "summary",
            "market_background",
            "lg_strategy",
            "catl_strategy",
            "strategy_comparison",
            "swot",
            "company_metrics",
            "insights",
        ],
        "additionalProperties": False,
    }


def _serialize_evidence(entry: EvidenceItem) -> dict[str, object]:
    return {
        "document_id": entry.document_id,
        "snippet": entry.snippet[:500],
        "source_type": entry.source_type,
        "source": entry.source,
        "topics": entry.topics,
        "score": entry.score,
    }


def _normalize_company_analysis(result: CompanyAnalysisResult) -> NormalizedCompanyAnalysis:
    return NormalizedCompanyAnalysis(
        company=result.company,
        strategy_summary=result.strategy_summary,
        strengths=list(result.strengths),
        risks=list(result.risks),
        citations=list(result.citations),
        metrics=[metric.to_dict() for metric in result.metrics],
        partial=result.partial,
    )
