"""CLI entrypoint for the battery agent project."""

from __future__ import annotations

import argparse
from typing import Sequence

from battery_agent.logging_utils import build_console_logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="battery-agent")
    parser.add_argument(
        "--topic",
        default="배터리 시장 전략 비교",
        help="Analysis topic to run",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logger = build_console_logger("battery-agent.cli")
    logger.info("battery-agent execution started")
    print(f"battery-agent: {args.topic}")
    logger.info("battery-agent execution finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
