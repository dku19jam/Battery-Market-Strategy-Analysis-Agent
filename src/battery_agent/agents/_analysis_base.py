"""Shared company analysis logic."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from battery_agent.agents._prompt_builders import (
    analysis_schema,
    analysis_system_prompt,
    analysis_user_prompt,
)
from battery_agent.config import Settings
from battery_agent.llm.openai_structured import StructuredOpenAIClient
from battery_agent.models.analysis import CompanyAnalysisResult
from battery_agent.models.evidence import EvidenceBundle
from battery_agent.storage.json_store import write_json


class StructuredLlmLike(Protocol):
    def generate_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        schema_name: str,
        schema: dict[str, object],
    ) -> dict[str, object]:
        ...


def run_analysis_agent(
    bundle: EvidenceBundle,
    llm_client: StructuredLlmLike | None = None,
    model: str | None = None,
    artifact_path: Path | None = None,
) -> CompanyAnalysisResult:
    settings = Settings.from_env() if llm_client is None or model is None else None
    client = llm_client or StructuredOpenAIClient(api_key=settings.openai_api_key)
    selected_model = model or settings.default_model
    payload = client.generate_json(
        model=selected_model,
        system_prompt=analysis_system_prompt(bundle.company),
        user_prompt=analysis_user_prompt(bundle),
        schema_name="company_analysis",
        schema=analysis_schema(),
    )
    valid_citations = {entry.document_id for entry in bundle.entries}
    citations = [
        citation
        for citation in payload.get("citations", [])
        if citation in valid_citations
    ]
    strategy_entries = bundle.topic_buckets.get("strategy", [])
    risk_entries = bundle.topic_buckets.get("risk", [])
    strategy_summary = str(payload.get("strategy_summary", "")).strip() or (
        f"{bundle.company}은(는) {strategy_entries[0].snippet} 기반으로 포트폴리오 다각화를 추진한다."
        if strategy_entries
        else f"{bundle.company} 전략 근거가 제한적이다."
    )
    strengths = [str(item).strip() for item in payload.get("strengths", []) if str(item).strip()]
    risks = [str(item).strip() for item in payload.get("risks", []) if str(item).strip()]
    if not strengths:
        strengths = [entry.snippet for entry in strategy_entries[:2]] or ["전략 근거 부족"]
    if not risks:
        risks = [entry.snippet for entry in risk_entries[:2]] or ["리스크 근거 부족"]
    partial = bool(bundle.missing_topics)
    notes = str(payload.get("analysis_notes", "")).strip() or (
        "missing topics: " + ", ".join(bundle.missing_topics)
        if bundle.missing_topics
        else "analysis complete"
    )

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
