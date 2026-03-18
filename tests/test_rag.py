import json
import tempfile
import unittest
from pathlib import Path


class CorpusLoaderTest(unittest.TestCase):
    def test_load_corpus_reads_jsonl_and_json_documents(self) -> None:
        from battery_agent.rag.corpus_loader import load_corpus

        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_dir = Path(tmp_dir)
            (corpus_dir / "docs.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "document_id": "doc-1",
                                "company": "LG에너지솔루션",
                                "title": "LG report",
                                "text": "battery diversification strategy",
                                "source_type": "report",
                                "page_count": 4,
                                "topics": ["strategy"],
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "document_id": "doc-2",
                                "company": "CATL",
                                "title": "CATL report",
                                "text": "cathode supply chain",
                                "source_type": "web",
                                "page_count": 2,
                                "topics": ["supply-chain"],
                            },
                            ensure_ascii=False,
                        ),
                    ]
                ),
                encoding="utf-8",
            )
            (corpus_dir / "single.json").write_text(
                json.dumps(
                    {
                        "document_id": "doc-3",
                        "company": "LG에너지솔루션",
                        "title": "LG note",
                        "text": "risk and pricing pressure",
                        "source_type": "memo",
                        "page_count": 1,
                        "topics": ["risk"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            documents = load_corpus(corpus_dir)

        self.assertEqual([document.document_id for document in documents], ["doc-1", "doc-2", "doc-3"])
        self.assertEqual(documents[0].page_count, 4)


class ChunkerTest(unittest.TestCase):
    def test_chunk_documents_respects_page_limit_and_writes_artifact(self) -> None:
        from battery_agent.rag.chunker import chunk_documents, write_chunk_artifact
        from battery_agent.rag.corpus_loader import CorpusDocument

        documents = [
            CorpusDocument(
                document_id="doc-1",
                company="LG에너지솔루션",
                title="LG report",
                text="alpha beta gamma delta epsilon zeta",
                source_type="report",
                page_count=60,
                topics=["strategy"],
            ),
            CorpusDocument(
                document_id="doc-2",
                company="CATL",
                title="CATL report",
                text="eta theta iota kappa lambda mu",
                source_type="report",
                page_count=50,
                topics=["risk"],
            ),
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_path = Path(tmp_dir) / "chunks.json"
            chunks = chunk_documents(documents, chunk_size=3, chunk_overlap=1, max_total_pages=100)
            write_chunk_artifact(artifact_path, chunks)

            payload = json.loads(artifact_path.read_text(encoding="utf-8"))

        self.assertTrue(all(chunk.chunk_id.startswith(chunk.document_id) for chunk in chunks))
        self.assertTrue(all(chunk.document_id != "doc-2" for chunk in chunks))
        self.assertGreater(len(payload), 0)


class EmbedderAndVectorIndexTest(unittest.TestCase):
    def test_embedder_uses_cache_and_vector_index_returns_best_match(self) -> None:
        from battery_agent.rag.embedder import HashingEmbedder, embed_texts
        from battery_agent.rag.vector_index import InMemoryVectorIndex, VectorRecord

        with tempfile.TemporaryDirectory() as tmp_dir:
            embedder = HashingEmbedder(cache_dir=Path(tmp_dir), dimensions=8)
            first = embed_texts(embedder, ["battery strategy", "supply chain"])
            second = embed_texts(embedder, ["battery strategy", "supply chain"])

            index = InMemoryVectorIndex()
            index.add(
                [
                    VectorRecord(
                        record_id="chunk-1",
                        document_id="doc-1",
                        text="battery strategy",
                        embedding=first[0],
                        metadata={"company": "LG에너지솔루션"},
                    ),
                    VectorRecord(
                        record_id="chunk-2",
                        document_id="doc-2",
                        text="supply chain",
                        embedding=first[1],
                        metadata={"company": "CATL"},
                    ),
                ]
            )

            hits = index.search(first[0], top_k=1)

        self.assertEqual(first, second)
        self.assertEqual(hits[0].record_id, "chunk-1")

    def test_index_refresh_policy_uses_corpus_fingerprint(self) -> None:
        from battery_agent.rag.vector_index import (
            compute_corpus_fingerprint,
            should_rebuild_index,
            write_index_metadata,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_dir = Path(tmp_dir) / "corpus"
            corpus_dir.mkdir()
            (corpus_dir / "docs.jsonl").write_text('{"id":"1"}\n', encoding="utf-8")
            index_path = Path(tmp_dir) / "index.json"
            metadata_path = Path(tmp_dir) / "index.meta.json"
            fingerprint = compute_corpus_fingerprint(corpus_dir)

            self.assertTrue(should_rebuild_index(index_path, metadata_path, fingerprint))

            index_path.write_text("[]", encoding="utf-8")
            write_index_metadata(metadata_path, fingerprint)

            self.assertFalse(should_rebuild_index(index_path, metadata_path, fingerprint))

            (corpus_dir / "docs.jsonl").write_text('{"id":"2"}\n', encoding="utf-8")
            updated_fingerprint = compute_corpus_fingerprint(corpus_dir)

            self.assertTrue(should_rebuild_index(index_path, metadata_path, updated_fingerprint))
