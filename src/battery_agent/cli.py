"""CLI entrypoint for the battery agent project."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from battery_agent.config import Settings
from battery_agent.llm.openai_structured import StructuredOpenAIClient
from battery_agent.logging_utils import build_console_logger
from battery_agent.logging_utils import build_run_logger
from battery_agent.pipeline.orchestrator import run_analysis_workflow
from battery_agent.rag.pdf_ingest import ingest_pdf_corpus
from battery_agent.storage.paths import build_run_paths, ensure_run_directories


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="battery-agent")
    parser.add_argument(
        "command",
        nargs="?",
        choices=("analyze", "ingest-pdfs"),
        default="analyze",
        help="Run analysis or ingest PDF corpus into Chroma",
    )
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
    parser.add_argument("--corpus-dir", help="Override corpus directory")
    parser.add_argument("--output-dir", help="Override output directory")
    parser.add_argument("--chroma-dir", help="Override Chroma directory")
    parser.add_argument("--web-search", action="store_true", help="Enable web search for this run")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    if args.corpus_dir:
        settings = type(settings)(**{**settings.__dict__, "local_corpus_dir": Path(args.corpus_dir)})
    if args.output_dir:
        settings = type(settings)(**{**settings.__dict__, "output_root": Path(args.output_dir)})
    if args.chroma_dir:
        settings = type(settings)(**{**settings.__dict__, "chroma_dir": Path(args.chroma_dir)})
    if args.web_search:
        settings = type(settings)(**{**settings.__dict__, "web_search_enabled": True})

    if args.command == "ingest-pdfs":
        ingested = ingest_pdf_corpus(settings)
        print(f"ingested: {ingested}")
        return 0

    run_paths = build_run_paths(settings.output_root, args.run_id)
    ensure_run_directories(run_paths)

    logger = build_console_logger("battery-agent.cli")
    run_logger = build_run_logger("battery-agent.cli.run", run_paths.logs_dir / "run.log")
    logger.info("battery-agent execution started")
    run_logger.info("battery-agent execution started")
    workflow_state = run_analysis_workflow(
        settings=settings,
        topic=args.topic,
        run_id=args.run_id,
        llm_client=StructuredOpenAIClient(api_key=settings.openai_api_key),
    )
    print(f"battery-agent: {args.topic}")
    print(f"status: {workflow_state.status}")
    if workflow_state.report_artifact is not None:
        print(f"markdown: {workflow_state.report_artifact.markdown_path}")
        print(f"pdf: {workflow_state.report_artifact.pdf_path}")
    logger.info("battery-agent execution finished")
    run_logger.info("battery-agent execution finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
