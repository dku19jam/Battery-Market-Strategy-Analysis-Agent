"""PDF corpus loading for company-scoped directories."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from battery_agent.rag.corpus_loader import CorpusDocument


PdfReaderFactory = Callable[[Path], object]


def load_pdf_corpus(
    corpus_dir: Path,
    reader_factory: PdfReaderFactory | None = None,
) -> list[CorpusDocument]:
    if not corpus_dir.exists():
        raise FileNotFoundError(f"Corpus directory does not exist: {corpus_dir}")

    resolved_reader = reader_factory or _default_reader_factory
    documents: list[CorpusDocument] = []
    for company_dir in sorted(path for path in corpus_dir.iterdir() if path.is_dir()):
        for pdf_path in sorted(company_dir.glob("*.pdf")):
            reader = resolved_reader(pdf_path)
            pages = list(getattr(reader, "pages", []))
            text = "\n".join((page.extract_text() or "").strip() for page in pages).strip()
            documents.append(
                CorpusDocument(
                    document_id=pdf_path.stem,
                    company=company_dir.name,
                    title=pdf_path.stem,
                    text=text,
                    source_type="pdf",
                    page_count=max(len(pages), 1),
                    topics=[],
                    metadata={"file_path": str(pdf_path)},
                )
            )
    return documents


def _default_reader_factory(path: Path) -> object:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required for PDF corpus loading.") from exc
    return PdfReader(path)
