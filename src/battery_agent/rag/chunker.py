"""Chunking helpers for corpus documents."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from battery_agent.rag.corpus_loader import CorpusDocument


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    document_id: str
    company: str
    text: str
    page_start: int
    page_end: int
    topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def chunk_documents(
    documents: list[CorpusDocument],
    chunk_size: int = 200,
    chunk_overlap: int = 40,
    max_total_pages: int = 100,
) -> list[TextChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be between 0 and chunk_size - 1")

    chunks: list[TextChunk] = []
    used_pages = 0
    for document in documents:
        if used_pages + document.page_count > max_total_pages:
            break
        used_pages += document.page_count

        tokens = document.text.split()
        step = max(chunk_size - chunk_overlap, 1)
        for offset in range(0, len(tokens), step):
            window = tokens[offset : offset + chunk_size]
            if not window:
                continue
            chunk_index = len(chunks) + 1
            chunks.append(
                TextChunk(
                    chunk_id=f"{document.document_id}-chunk-{chunk_index}",
                    document_id=document.document_id,
                    company=document.company,
                    text=" ".join(window),
                    page_start=1,
                    page_end=document.page_count,
                    topics=list(document.topics),
                )
            )
            if offset + chunk_size >= len(tokens):
                break

    return chunks


def write_chunk_artifact(path: Path, chunks: list[TextChunk]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([chunk.to_dict() for chunk in chunks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
