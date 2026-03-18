"""Artifact directory path helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunPaths:
    root: Path
    logs_dir: Path
    metadata_dir: Path
    retrieval_dir: Path
    evidence_dir: Path
    analysis_dir: Path
    reports_dir: Path


def build_run_paths(base_dir: Path, run_id: str) -> RunPaths:
    root = base_dir / run_id
    return RunPaths(
        root=root,
        logs_dir=root / "logs",
        metadata_dir=root / "metadata",
        retrieval_dir=root / "retrieval",
        evidence_dir=root / "evidence",
        analysis_dir=root / "analysis",
        reports_dir=root / "reports",
    )


def ensure_run_directories(run_paths: RunPaths) -> None:
    run_paths.root.mkdir(parents=True, exist_ok=True)
    run_paths.logs_dir.mkdir(parents=True, exist_ok=True)
    run_paths.metadata_dir.mkdir(parents=True, exist_ok=True)
    run_paths.retrieval_dir.mkdir(parents=True, exist_ok=True)
    run_paths.evidence_dir.mkdir(parents=True, exist_ok=True)
    run_paths.analysis_dir.mkdir(parents=True, exist_ok=True)
    run_paths.reports_dir.mkdir(parents=True, exist_ok=True)


def artifact_path_for(run_paths: RunPaths, stage: str, name: str, suffix: str = "json") -> Path:
    stage_dirs = {
        "metadata": run_paths.metadata_dir,
        "retrieval": run_paths.retrieval_dir,
        "evidence": run_paths.evidence_dir,
        "analysis": run_paths.analysis_dir,
        "reports": run_paths.reports_dir,
        "logs": run_paths.logs_dir,
    }
    if stage not in stage_dirs:
        raise ValueError(f"Unsupported artifact stage: {stage}")
    return stage_dirs[stage] / f"{name}.{suffix}"
