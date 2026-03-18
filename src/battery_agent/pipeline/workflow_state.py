"""Workflow state models."""

from __future__ import annotations

from dataclasses import dataclass, field

from battery_agent.models.analysis import CompanyAnalysisResult
from battery_agent.models.evidence import EvidenceBundle
from battery_agent.models.report import ComparisonResult, ReferenceResult, ReportArtifact
from battery_agent.models.retrieval import RetrievalResult
from battery_agent.models.run_context import RunContext


@dataclass
class LaneState:
    company: str
    retrieval_result: RetrievalResult | None = None
    evidence_bundle: EvidenceBundle | None = None
    analysis_result: CompanyAnalysisResult | None = None
    retries: dict[str, int] = field(default_factory=dict)
    partial: bool = False
    used_sources: list[str] = field(default_factory=list)
    last_action: str | None = None
    status: str = "initialized"


@dataclass
class WorkflowState:
    run_context: RunContext
    model_name: str
    corpus_fingerprint: str
    search_params: dict[str, object]
    lg_lane: LaneState
    catl_lane: LaneState
    comparison_result: ComparisonResult | None = None
    reference_result: ReferenceResult | None = None
    report_artifact: ReportArtifact | None = None
    status: str = "initialized"
