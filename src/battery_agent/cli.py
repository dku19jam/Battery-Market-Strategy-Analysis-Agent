"""CLI entrypoint for the battery agent project."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from battery_agent.config import Settings
from battery_agent.logging_utils import build_console_logger
from battery_agent.logging_utils import build_run_logger
from battery_agent.storage.paths import build_run_paths, ensure_run_directories


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="battery-agent")
    parser.add_argument(
        "--topic",
        default="배터리 시장 전략 비교",
        help="Analysis topic to run",
    )
    parser.add_argument(
        "--run-id",
        default="manual-run",
        help="Run identifier used for artifact directories",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    run_paths = build_run_paths(settings.output_root, args.run_id)
    ensure_run_directories(run_paths)

    logger = build_console_logger("battery-agent.cli")
    run_logger = build_run_logger("battery-agent.cli.run", run_paths.logs_dir / "run.log")
    logger.info("battery-agent execution started")
    run_logger.info("battery-agent execution started")
    print(f"battery-agent: {args.topic}")
    logger.info("battery-agent execution finished")
    run_logger.info("battery-agent execution finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
