"""Local corpus loading contract."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


SUPPORTED_CORPUS_EXTENSIONS = (".json", ".jsonl")


@dataclass(frozen=True)
class CorpusDocument:
    document_id: str
    company: str
    title: str
    text: str
    source_type: str
    page_count: int = 1
    topics: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _validate_record(record: dict[str, object], source_path: Path) -> CorpusDocument:
    required = ("document_id", "company", "title", "text", "source_type")
    missing = [key for key in required if key not in record]
    if missing:
        raise ValueError(f"{source_path.name} is missing required fields: {', '.join(missing)}")

    metadata = dict(record.get("metadata", {}))
    return CorpusDocument(
        document_id=str(record["document_id"]),
        company=str(record["company"]),
        title=str(record["title"]),
        text=str(record["text"]),
        source_type=str(record["source_type"]),
        page_count=int(record.get("page_count", 1)),
        topics=list(record.get("topics", [])),
        metadata=metadata,
    )


def load_corpus(corpus_dir: Path) -> list[CorpusDocument]:
    if not corpus_dir.exists():
        raise FileNotFoundError(f"Corpus directory does not exist: {corpus_dir}")

    documents: list[CorpusDocument] = []
    for path in sorted(corpus_dir.iterdir()):
        if path.suffix not in SUPPORTED_CORPUS_EXTENSIONS:
            continue

        if path.suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            records = payload if isinstance(payload, list) else [payload]
        else:
            records = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        documents.extend(_validate_record(record, path) for record in records)

    return documents
