"""CATL analysis agent."""

from __future__ import annotations

from pathlib import Path

from battery_agent.agents._analysis_base import run_analysis_agent
from battery_agent.models.analysis import CompanyAnalysisResult
from battery_agent.models.evidence import EvidenceBundle


def run_catl_analysis(
    bundle: EvidenceBundle,
    artifact_path: Path | None = None,
) -> CompanyAnalysisResult:
    return run_analysis_agent(bundle, artifact_path=artifact_path)
