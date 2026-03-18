"""Chroma-backed vector storage."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ChromaRecord:
    record_id: str
    document_id: str
    text: str
    embedding: list[float]
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ChromaSearchHit:
    chunk_id: str
    document_id: str
    score: float
    text: str
    metadata: dict[str, object]


class ChromaVectorStore:
    def __init__(
        self,
        collection: object,
        client: object | None = None,
        collection_name: str = "",
    ) -> None:
        self.client = client
        self.collection_name = collection_name
        self.collection = collection

    @classmethod
    def open(
        cls,
        chroma_dir: Path,
        collection_name: str,
        client: object | None = None,
    ) -> "ChromaVectorStore":
        resolved_client = client or _build_client(chroma_dir)
        collection = resolved_client.get_or_create_collection(name=collection_name)
        return cls(
            collection=collection,
            client=resolved_client,
            collection_name=collection_name,
        )

    def has_records(self) -> bool:
        count = getattr(self.collection, "count", None)
        if callable(count):
            return bool(count())
        return True

    def replace_collection(self) -> None:
        if self.client is None or not self.collection_name:
            raise RuntimeError("replace_collection requires a managed Chroma client and collection name.")
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    def upsert_records(self, records: list[ChromaRecord]) -> None:
        self.collection.upsert(
            ids=[record.record_id for record in records],
            documents=[record.text for record in records],
            embeddings=[record.embedding for record in records],
            metadatas=[
                _serialize_metadata(
                    {
                        **record.metadata,
                        "document_id": record.document_id,
                    }
                )
                for record in records
            ],
        )

    def search(
        self,
        query_embedding: list[float],
        company: str,
        top_k: int = 5,
    ) -> list[ChromaSearchHit]:
        payload = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"company": company},
        )
        ids = payload.get("ids", [[]])[0]
        documents = payload.get("documents", [[]])[0]
        distances = payload.get("distances", [[]])[0]
        metadatas = payload.get("metadatas", [[]])[0]
        hits: list[ChromaSearchHit] = []
        for chunk_id, text, distance, metadata in zip(ids, documents, distances, metadatas):
            resolved_metadata = _deserialize_metadata(dict(metadata or {}))
            hits.append(
                ChromaSearchHit(
                    chunk_id=str(chunk_id),
                    document_id=str(resolved_metadata.get("document_id", chunk_id)),
                    score=1.0 - float(distance),
                    text=str(text),
                    metadata=resolved_metadata,
                )
            )
        return hits


def _build_client(chroma_dir: Path) -> object:
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
    except ImportError as exc:
        raise RuntimeError("chromadb is required for Chroma vector storage.") from exc
    chroma_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(chroma_dir),
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def _serialize_metadata(metadata: dict[str, object]) -> dict[str, object]:
    serialized: dict[str, object] = {}
    for key, value in metadata.items():
        if isinstance(value, list):
            serialized[key] = json.dumps(value, ensure_ascii=False)
        else:
            serialized[key] = value
    return serialized


def _deserialize_metadata(metadata: dict[str, object]) -> dict[str, object]:
    deserialized: dict[str, object] = {}
    for key, value in metadata.items():
        if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                deserialized[key] = value
                continue
            deserialized[key] = decoded
        else:
            deserialized[key] = value
    return deserialized
