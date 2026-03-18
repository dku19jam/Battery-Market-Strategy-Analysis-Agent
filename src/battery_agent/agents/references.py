"""Reference agent."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from battery_agent.agents.evidence_quality import evidence_quality, is_quality_reference
from battery_agent.models.analysis import CompanyAnalysisResult
from battery_agent.models.evidence import EvidenceBundle, EvidenceItem
from battery_agent.models.report import ComparisonResult, ReferenceEntry, ReferenceResult
from battery_agent.storage.json_store import write_json

REFERENCE_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("report", "기관 보고서"),
    ("paper", "학술 논문"),
    ("web", "웹페이지"),
)

SOURCE_TYPE_ALIASES: dict[str, str] = {
    "pdf": "report",
    "local": "report",
    "memo": "report",
}


def format_reference_block(entries: list[ReferenceEntry]) -> str:
    if not entries:
        return "참고문헌이 없습니다."

    grouped: dict[str, list[str]] = {
        source_type: [] for source_type, _ in REFERENCE_CATEGORIES
    }
    for entry in entries:
        source_type = SOURCE_TYPE_ALIASES.get(entry.source_type, entry.source_type)
        grouped.setdefault(source_type, []).append(entry.formatted_reference)

    lines: list[str] = []
    for source_type, label in REFERENCE_CATEGORIES:
        refs = grouped.get(source_type, [])
        if not refs:
            continue
        lines.append(f"### {label}")
        lines.extend(f"◦ {ref}" for ref in refs)
        lines.append("")
    return "\n".join(lines).strip()


def build_references(
    evidence_bundles: list[EvidenceBundle],
    analyses: list[CompanyAnalysisResult],
    comparison: ComparisonResult,
    artifact_path: Path | None = None,
) -> ReferenceResult:
    used_doc_ids: list[str] = []
    for analysis in analyses:
        for citation in analysis.citations:
            if citation not in used_doc_ids:
                used_doc_ids.append(citation)
    for company in comparison.normalized_companies:
        for citation in company.citations:
            if citation not in used_doc_ids:
                used_doc_ids.append(citation)

    evidence_map: dict[str, EvidenceItem] = {}
    for bundle in evidence_bundles:
        for entry in bundle.entries:
            evidence_map.setdefault(entry.document_id, entry)

    candidate_reference_items: list[tuple[EvidenceItem, ReferenceEntry]] = []
    for document_id in used_doc_ids:
        entry = evidence_map.get(document_id)
        if entry is None:
            continue
        candidate_reference_items.append(
            (
                entry,
                ReferenceEntry(
                    document_id=document_id,
                    source_type=SOURCE_TYPE_ALIASES.get(entry.source_type, entry.source_type),
                    formatted_reference=_format_reference(entry),
                ),
            )
        )

    prioritized_items = [
        item
        for entry, item in candidate_reference_items
        if is_quality_reference(entry)
    ]
    if not prioritized_items:
        prioritized_items = [item for _, item in candidate_reference_items]

    entries = sorted(
        prioritized_items,
        key=lambda item: evidence_quality(evidence_map[item.document_id]),
        reverse=True,
    )
    result = ReferenceResult(entries=entries)
    if artifact_path is not None:
        write_json(artifact_path, result.to_dict())
    return result


def _format_reference(entry: EvidenceItem) -> str:
    source_type = SOURCE_TYPE_ALIASES.get(entry.source_type, entry.source_type)
    if source_type == "report":
        return _format_report_reference(entry=entry)
    if source_type == "paper":
        return _format_paper_reference(entry=entry)
    if source_type == "web":
        return _format_web_reference(entry=entry)
    return _format_generic_reference(entry=entry)


def _format_report_reference(entry: EvidenceItem) -> str:
    year = _infer_year(entry)
    source = _normalize_report_source(entry.source, fallback_id=entry.document_id)
    title = _strip_empty(entry.title) or _strip_empty(entry.document_id)
    return f"{source}({year}). {title}. {source}"


def _format_paper_reference(entry: EvidenceItem) -> str:
    year = _infer_year(entry)
    author = entry.source or "저자·매체 미상"
    title = _strip_empty(entry.title) or _strip_empty(entry.document_id)
    return f"{author}({year}). {title}. {entry.source}"


def _format_web_reference(entry: EvidenceItem) -> str:
    year = _infer_year(entry)
    title = _strip_empty(entry.title) or _strip_empty(entry.document_id)
    url = _normalize_web_url(entry.url or entry.source)
    source = _strip_empty(entry.source) or _extract_domain(url)
    if source == url:
        return f"{source}({year}). {title}. {url}"
    return f"{source}({year}). {title}. {url}"


def _normalize_report_source(value: str, fallback_id: str) -> str:
    if value:
        if value.startswith("http://") or value.startswith("https://"):
            parsed = urlparse(value)
            return parsed.netloc or fallback_id
        if "/" in value or value.endswith(".pdf"):
            normalized = Path(value).stem or value
            return normalized
        return value
    return fallback_id


def _format_generic_reference(entry: EvidenceItem) -> str:
    return f"{_strip_empty(entry.source) or _strip_empty(entry.document_id)}({_infer_year(entry)}). {_strip_empty(entry.title) or _strip_empty(entry.document_id)}"


def _infer_year(entry: EvidenceItem) -> str:
    for candidate in (entry.title, entry.source, entry.document_id):
        if not candidate:
            continue
        match = re.search(r"(?:19|20)\d{2}", str(candidate))
        if match:
            return match.group(0)
    return "연도미상"


def _strip_empty(value: str) -> str:
    return value.strip() if value else ""


def _extract_domain(value: str) -> str:
    if not value:
        return ""
    if "://" in value:
        return value.split("://", 1)[1].split("/", 1)[0]
    return value


def _normalize_web_url(value: str) -> str:
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("www."):
        return f"https://{value}"
    if "." in value and " " not in value:
        return f"https://{value}"
    return value
