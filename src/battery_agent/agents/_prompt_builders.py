"""Dynamic prompt construction helpers for analysis and comparison."""

from __future__ import annotations

import json

from battery_agent.models.analysis import CompanyAnalysisResult
from battery_agent.models.evidence import EvidenceBundle, EvidenceItem
from battery_agent.models.report import NormalizedCompanyAnalysis


def analysis_system_prompt(company: str) -> str:
    return (
        f"You are the {company} analysis agent. "
        "Analyze only the target company. "
        "Do not mention the competitor directly. "
        "Use only provided evidence. "
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
            "analysis_notes": {"type": "string"},
        },
        "required": ["strategy_summary", "strengths", "risks", "citations", "analysis_notes"],
        "additionalProperties": False,
    }


def comparison_system_prompt() -> str:
    return (
        "You are the comparison evaluation agent. "
        "Compare only the two structured company analyses provided. "
        "Do not invent evidence. "
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
                    },
                    "required": ["company", "strategy_summary", "strengths", "risks"],
                    "additionalProperties": True,
                },
            },
            "strategy_differences": {"type": "array", "items": {"type": "string"}},
            "strengths_weaknesses": {"type": "array", "items": {"type": "string"}},
            "swot": {"type": "array", "items": {"type": "string"}},
            "insights": {"type": "array", "items": {"type": "string"}},
            "refinement_requests": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "normalized_companies",
            "strategy_differences",
            "strengths_weaknesses",
            "swot",
            "insights",
            "refinement_requests",
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
        partial=result.partial,
    )
