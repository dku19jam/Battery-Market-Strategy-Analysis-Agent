"""Handoff rules."""

from __future__ import annotations

from battery_agent.pipeline.workflow_state import LaneState


def next_stage_after_lanes(lg_lane: LaneState, catl_lane: LaneState) -> str:
    if lg_lane.status == "completed" and catl_lane.status == "completed":
        return "comparison"
    return "waiting"


def next_stage_after_references(has_references: bool) -> str:
    return "report_generation" if has_references else "partial_report"


def final_workflow_status(has_report: bool, partial: bool) -> str:
    if not has_report:
        return "failed"
    return "partial" if partial else "completed"
