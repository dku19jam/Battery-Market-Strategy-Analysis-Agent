"""Markdown rendering helpers."""

from __future__ import annotations

from pathlib import Path

from battery_agent.storage.json_store import write_markdown


REQUIRED_SECTIONS = [
    "SUMMARY",
    "MARKET_BACKGROUND",
    "LG_STRATEGY",
    "CATL_STRATEGY",
    "STRATEGY_COMPARISON",
    "COMPANY_METRICS",
    "SWOT",
    "INSIGHTS",
    "REFERENCE",
]
SUMMARY_CHAR_LIMIT = 1200


def render_report_markdown(
    title: str,
    sections: dict[str, str],
    partial: bool,
    partial_message: str | None = None,
    failure_message: str | None = None,
) -> str:
    normalized_sections = dict(sections)
    normalized_sections["SUMMARY"] = normalized_sections.get("SUMMARY", "")[:SUMMARY_CHAR_LIMIT]
    parts = [f"# {title}", ""]
    if partial and partial_message:
        parts.extend([f"> PARTIAL REPORT: {partial_message}", ""])
    if failure_message:
        parts.extend([f"> FAILURE NOTICE: {failure_message}", ""])
    for section in REQUIRED_SECTIONS:
        parts.append(f"## {section}")
        parts.append(normalized_sections.get(section, ""))
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def save_report_markdown(path: Path, markdown: str) -> None:
    write_markdown(path, markdown)
