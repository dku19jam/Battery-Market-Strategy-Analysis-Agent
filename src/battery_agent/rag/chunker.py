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
    title: str = ""
    source_type: str = "local"
    source: str = ""
    url: str = ""
    topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def chunk_documents(
    documents: list[CorpusDocument],
    chunk_size: int = 200,
    chunk_overlap: int = 40,
    max_total_pages: int | None = 100,
) -> list[TextChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be between 0 and chunk_size - 1")

    def _coerce_chunk_source(document: CorpusDocument) -> str:
        source = getattr(document, "metadata", {}).get("source")
        if source is None or not str(source).strip():
            return str(document.source_type or "")
        return str(source)

    def _coerce_chunk_source_type(document: CorpusDocument) -> str:
        return str(document.source_type or "local")

    def _coerce_chunk_url(document: CorpusDocument) -> str:
        source_url = getattr(document, "metadata", {}).get("url")
        if source_url is None:
            return ""
        return str(source_url)

    chunks: list[TextChunk] = []
    used_pages = 0
    for document in documents:
        if max_total_pages is not None and used_pages + document.page_count > max_total_pages:
            break
        used_pages += document.page_count
        source = _coerce_chunk_source(document)
        source_type = _coerce_chunk_source_type(document)
        source_url = _coerce_chunk_url(document)
        title = str(document.title or document.document_id)

        page_tokens, token_pages = _build_token_stream(
            document_text=document.text,
            page_texts=_coerce_chunk_page_texts(document),
        )
        if not page_tokens:
            continue

        step = max(chunk_size - chunk_overlap, 1)
        for offset in range(0, len(page_tokens), step):
            window = page_tokens[offset : offset + chunk_size]
            if not window:
                continue
            chunk_pages = token_pages[offset : offset + len(window)]
            if not chunk_pages:
                page_start = 1
                page_end = 1
            else:
                page_start = min(chunk_pages)
                page_end = max(chunk_pages)
            chunk_index = len(chunks) + 1
            chunks.append(
                TextChunk(
                    chunk_id=f"{document.document_id}-chunk-{chunk_index}",
                    document_id=document.document_id,
                    company=document.company,
                    title=title,
                    source_type=source_type,
                    source=source,
                    url=source_url,
                    text=" ".join(window),
                    page_start=page_start,
                    page_end=page_end,
                    topics=list(document.topics),
                )
            )
            if offset + chunk_size >= len(page_tokens):
                break

    return chunks


def _coerce_chunk_page_texts(document: CorpusDocument) -> list[str]:
    raw = getattr(document, "metadata", {}).get("page_texts")
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if isinstance(item, str) and item.strip()]


def _build_token_stream(document_text: str, page_texts: list[str]) -> tuple[list[str], list[int]]:
    if not page_texts:
        tokens = document_text.split()
        return tokens, [1] * len(tokens)

    tokens: list[str] = []
    token_pages: list[int] = []
    for page_index, page_text in enumerate(page_texts, start=1):
        page_tokens = page_text.split()
        tokens.extend(page_tokens)
        token_pages.extend([page_index] * len(page_tokens))

    if not tokens:
        return [], []

    return tokens, token_pages


def write_chunk_artifact(path: Path, chunks: list[TextChunk]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([chunk.to_dict() for chunk in chunks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
