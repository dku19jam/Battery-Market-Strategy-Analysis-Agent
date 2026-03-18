"""LG analysis agent."""

from __future__ import annotations

from pathlib import Path

from battery_agent.agents._analysis_base import StructuredLlmLike, run_analysis_agent
from battery_agent.models.analysis import CompanyAnalysisResult
from battery_agent.models.evidence import EvidenceBundle


def run_lg_analysis(
    bundle: EvidenceBundle,
    llm_client: StructuredLlmLike | None = None,
    model: str | None = None,
    artifact_path: Path | None = None,
) -> CompanyAnalysisResult:
    return run_analysis_agent(
        bundle,
        llm_client=llm_client,
        model=model,
        artifact_path=artifact_path,
    )
