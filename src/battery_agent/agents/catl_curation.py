"""CATL evidence curation agent."""

from __future__ import annotations

from battery_agent.agents._curation_base import run_curation_agent
from battery_agent.models.evidence import EvidenceBundle
from battery_agent.models.retrieval import RetrievalResult


def run_catl_curation(retrieval: RetrievalResult) -> EvidenceBundle:
    return run_curation_agent(retrieval)
