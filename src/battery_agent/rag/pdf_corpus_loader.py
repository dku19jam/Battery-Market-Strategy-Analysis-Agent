"""PDF corpus loading for company-scoped directories."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Callable

from battery_agent.rag.corpus_loader import CorpusDocument


PdfReaderFactory = Callable[[Path], object]


def load_pdf_corpus(
    corpus_dir: Path,
    reader_factory: PdfReaderFactory | None = None,
    min_document_words: int = 0,
    min_page_words: int = 0,
    focus_keywords: Iterable[str] | None = None,
) -> list[CorpusDocument]:
    if not corpus_dir.exists():
        raise FileNotFoundError(f"Corpus directory does not exist: {corpus_dir}")

    resolved_reader = reader_factory or _default_reader_factory
    documents: list[CorpusDocument] = []
    focus = _normalize_keywords(focus_keywords or ())

    for company_dir in sorted(path for path in corpus_dir.iterdir() if path.is_dir()):
        for pdf_path in sorted(company_dir.glob("*.pdf")):
            reader = resolved_reader(pdf_path)
            pages = list(getattr(reader, "pages", []))
            extracted_pages = _extract_pages(pages)
            if not extracted_pages:
                continue

            meaningful_pages = _filter_meaningful_pages(
                text_pages=extracted_pages,
                min_tokens=min_page_words,
            )
            if not meaningful_pages:
                continue

            page_texts = [text for _, text in meaningful_pages]
            document_text = _clean_text("\n".join(page_texts)).strip()
            if len(document_text.split()) < max(min_document_words, 0):
                continue

            inferred_topics = _infer_topics(document_text, focus)
            documents.append(
                CorpusDocument(
                    document_id=pdf_path.stem,
                    company=company_dir.name,
                    title=_infer_title(pdf_path.stem, document_text),
                    text=document_text,
                    source_type="pdf",
                    page_count=max(len(pages), 1),
                    topics=inferred_topics,
                    metadata={
                        "file_path": str(pdf_path),
                        "source": company_dir.name,
                        "extracted_pages": len(extracted_pages),
                        "meaningful_pages": len(meaningful_pages),
                        "page_texts": page_texts,
                        "page_numbers": [index for index, _ in meaningful_pages],
                        "focus_matches": sum(
                            1 for keyword in focus if keyword and keyword in document_text.lower()
                        ),
                    },
                )
            )
    return documents


def _default_reader_factory(path: Path) -> object:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required for PDF corpus loading.") from exc
    return PdfReader(path)


def _extract_pages(pages: list[object]) -> list[str]:
    text_pages: list[str] = []
    for page in pages:
        raw_text = getattr(page, "extract_text", lambda: None)() or ""
        cleaned = _clean_text(raw_text).strip()
        if cleaned:
            text_pages.append(cleaned)
    return text_pages


def _filter_meaningful_pages(
    text_pages: list[str],
    min_tokens: int = 50,
) -> list[tuple[int, str]]:
    if min_tokens <= 0:
        return [
            (index, text)
            for index, text in enumerate(text_pages, start=1)
            if text.strip()
        ]

    meaningful = [
        (index, text)
        for index, text in enumerate(text_pages, start=1)
        if len(text.split()) >= min_tokens and _is_valid_content_block(text)
    ]

    if meaningful:
        return meaningful

    fallback = [
        (index, text)
        for index, text in enumerate(text_pages, start=1)
        if len(text.split()) >= max(12, min_tokens // 3) and _is_valid_content_block(text)
    ]
    return fallback


def _is_valid_content_block(text: str) -> bool:
    if len(text) < 100:
        return False
    if _is_noise(text):
        return False
    return _ratio_of_alpha(text) >= 0.35


def _ratio_of_alpha(text: str) -> float:
    stripped = re.sub(r"\s+", "", text)
    if not stripped:
        return 0.0
    alpha = sum(1 for char in stripped if char.isalpha())
    return alpha / max(len(stripped), 1)


def _is_noise(text: str) -> bool:
    normalized = text.lower().strip()
    noise_patterns = (
        r"^\d+$",
        r"^\s*\d+\s*/\s*\d+\s*$",
        r"^copyright",
        r"^powered by ",
        r"^contents",
        r"^table of contents",
    )
    return any(re.search(pattern, normalized) for pattern in noise_patterns)


def _clean_text(text: str) -> str:
    normalized = text.replace("\r", "\n")
    lines = []
    for line in normalized.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if _looks_like_header_footer(stripped):
            continue
        if len(stripped) >= 6:
            lines.append(stripped)
    return "\n".join(lines)


def _looks_like_header_footer(text: str) -> bool:
    line = text.lower().strip()
    if not line:
        return True
    return any(
        re.search(pattern, line)
        for pattern in (
            r"^\s*\d+\s*$",
            r"^page\s*\d+",
            r"^copyright\s+",
            r"^서울|^부산|^korea|^china|^japan",
            r"\s*\|\s*",
        )
    )


def _infer_title(filename: str, document_text: str) -> str:
    for line in document_text.splitlines():
        if line.strip():
            return line.strip()[:120]
    return filename


def _normalize_keywords(keywords: Iterable[str]) -> tuple[str, ...]:
    values = tuple(
        str(item).strip().lower() for item in keywords if isinstance(item, str) and item.strip()
    )
    return tuple(dict.fromkeys(values))


def _infer_topics(text: str, keywords: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    topics: list[str] = []
    for keyword in keywords:
        if keyword and keyword in lowered:
            topics.append(keyword)
    return sorted(set(topics))
