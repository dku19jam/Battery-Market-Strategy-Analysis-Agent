"""Reference agent."""

from __future__ import annotations

from pathlib import Path

from battery_agent.models.analysis import CompanyAnalysisResult
from battery_agent.models.evidence import EvidenceBundle, EvidenceItem
from battery_agent.models.report import ComparisonResult, ReferenceEntry, ReferenceResult
from battery_agent.storage.json_store import write_json


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

    entries = [
        ReferenceEntry(
            document_id=document_id,
            source_type=evidence_map[document_id].source_type,
            formatted_reference=_format_reference(evidence_map[document_id]),
        )
        for document_id in used_doc_ids
        if document_id in evidence_map
    ]
    result = ReferenceResult(entries=entries)
    if artifact_path is not None:
        write_json(artifact_path, result.to_dict())
    return result


def _format_reference(entry: EvidenceItem) -> str:
    if entry.source_type == "report":
        return f"{entry.source}. {entry.document_id}. Corporate report."
    if entry.source_type == "paper":
        return f"{entry.source}. \"{entry.document_id}.\" Academic paper."
    if entry.source_type == "web":
        url = entry.source if entry.source.startswith("http") else f"https://{entry.source}"
        return f"{entry.document_id}. {url}"
    return f"{entry.source}. {entry.document_id}."
