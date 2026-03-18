"""Embedding layer abstractions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EmbeddingRecord:
    text: str
    vector: list[float]


class HashingEmbedder:
    """Deterministic local embedder with file cache for development and tests."""

    def __init__(self, cache_dir: Path, dimensions: int = 16) -> None:
        self.cache_dir = cache_dir
        self.dimensions = dimensions
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, text: str) -> Path:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        cache_path = self._cache_path(text)
        if cache_path.exists():
            return list(json.loads(cache_path.read_text(encoding="utf-8")))

        vector = [0.0] * self.dimensions
        for token in text.split():
            token_digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index in range(self.dimensions):
                vector[index] += token_digest[index] / 255.0

        norm = sum(value * value for value in vector) ** 0.5 or 1.0
        normalized = [value / norm for value in vector]
        cache_path.write_text(json.dumps(normalized), encoding="utf-8")
        return normalized


def embed_texts(embedder: HashingEmbedder, texts: list[str]) -> list[list[float]]:
    return embedder.embed(texts)
