"""PDF ingest pipeline for Chroma."""

from __future__ import annotations

from battery_agent.config import Settings
from battery_agent.rag.chroma_store import ChromaRecord, ChromaVectorStore
from battery_agent.rag.chunker import chunk_documents
from battery_agent.rag.pdf_corpus_loader import load_pdf_corpus
from battery_agent.rag.qwen_embedder import QwenEmbeddingClient


def ingest_pdf_corpus(settings: Settings) -> int:
    documents = load_pdf_corpus(settings.local_corpus_dir)
    chunks = chunk_documents(documents)
    embedder = QwenEmbeddingClient(
        model_id=settings.embedding_model_id,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
    )
    embeddings = embedder.embed_documents([chunk.text for chunk in chunks])
    store = ChromaVectorStore.open(
        chroma_dir=settings.chroma_dir,
        collection_name=settings.chroma_collection,
    )
    store.upsert_records(
        [
            ChromaRecord(
                record_id=chunk.chunk_id,
                document_id=chunk.document_id,
                text=chunk.text,
                embedding=embedding,
                metadata={
                    "company": chunk.company,
                    "topics": chunk.topics,
                    "source_type": "pdf",
                    "source": "pdf-corpus",
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                },
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]
    )
    return len(chunks)
