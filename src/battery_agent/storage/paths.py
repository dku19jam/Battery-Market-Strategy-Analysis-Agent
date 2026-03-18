"""Artifact directory path helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunPaths:
    root: Path
    logs_dir: Path
    evidence_dir: Path
    reports_dir: Path


def build_run_paths(base_dir: Path, run_id: str) -> RunPaths:
    root = base_dir / run_id
    return RunPaths(
        root=root,
        logs_dir=root / "logs",
        evidence_dir=root / "evidence",
        reports_dir=root / "reports",
    )


def ensure_run_directories(run_paths: RunPaths) -> None:
    run_paths.root.mkdir(parents=True, exist_ok=True)
    run_paths.logs_dir.mkdir(parents=True, exist_ok=True)
    run_paths.evidence_dir.mkdir(parents=True, exist_ok=True)
    run_paths.reports_dir.mkdir(parents=True, exist_ok=True)
