"""Shared company analysis logic."""

from __future__ import annotations

from pathlib import Path

from battery_agent.models.analysis import CompanyAnalysisResult
from battery_agent.models.evidence import EvidenceBundle
from battery_agent.storage.json_store import write_json


def run_analysis_agent(
    bundle: EvidenceBundle,
    artifact_path: Path | None = None,
) -> CompanyAnalysisResult:
    strategy_entries = [entry for entry in bundle.entries if "strategy" in entry.topics]
    risk_entries = [entry for entry in bundle.entries if "risk" in entry.topics]

    strategy_summary = (
        f"{bundle.company}은(는) {strategy_entries[0].snippet} 기반으로 포트폴리오 다각화를 추진한다."
        if strategy_entries
        else f"{bundle.company} 전략 근거가 제한적이다."
    )
    strengths = [entry.snippet for entry in strategy_entries[:2]] or ["전략 근거 부족"]
    risks = [entry.snippet for entry in risk_entries[:2]] or ["리스크 근거 부족"]
    citations = [entry.document_id for entry in bundle.entries]
    partial = bool(bundle.missing_topics)
    notes = "missing topics: " + ", ".join(bundle.missing_topics) if bundle.missing_topics else "analysis complete"

    result = CompanyAnalysisResult(
        company=bundle.company,
        strategy_summary=strategy_summary,
        strengths=strengths,
        risks=risks,
        citations=citations,
        analysis_notes=notes,
        next_action="comparison",
        partial=partial,
    )
    if artifact_path is not None:
        write_json(artifact_path, result.to_dict())
    return result
