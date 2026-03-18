"""Shared evidence curation logic."""

from __future__ import annotations

from pathlib import Path

from battery_agent.models.evidence import EvidenceBundle, EvidenceItem
from battery_agent.models.retrieval import RetrievalResult
from battery_agent.storage.json_store import write_json
from battery_agent.agents.evidence_quality import evidence_sort_key


REQUIRED_TOPICS = ("strategy", "risk")


def run_curation_agent(
    retrieval: RetrievalResult,
    artifact_path: Path | None = None,
) -> EvidenceBundle:
    deduped: dict[tuple[str, str], EvidenceItem] = {}
    for item in retrieval.items:
        key = (item.document_id, item.text)
        candidate = EvidenceItem(
            document_id=item.document_id,
            snippet=item.text,
            source_type=item.source_type,
            source=item.source,
            title=getattr(item, "title", ""),
            url=str(getattr(item, "url", "")),
            topics=list(item.topics),
            score=item.score,
        )
        current = deduped.get(key)
        if current is None or _priority(candidate) > _priority(current):
            deduped[key] = candidate

    entries = sorted(deduped.values(), key=_priority, reverse=True)
    topics = sorted({topic for entry in entries for topic in entry.topics})
    topic_buckets = {
        topic: [entry for entry in entries if topic in entry.topics]
        for topic in topics
    }
    missing_topics = [topic for topic in REQUIRED_TOPICS if topic not in topics]
    next_action = "analysis" if "strategy" in topics else "retrieval"
    result = EvidenceBundle(
        company=retrieval.company,
        topics=topics,
        entries=entries,
        topic_buckets=topic_buckets,
        missing_topics=missing_topics if next_action == "analysis" else ["strategy"],
        next_action=next_action,
    )
    if artifact_path is not None:
        write_json(artifact_path, result.to_dict())
    return result


def _priority(entry: EvidenceItem) -> tuple[float, float]:
    quality_score, retrieval_score = evidence_sort_key(entry)
    return quality_score, retrieval_score
