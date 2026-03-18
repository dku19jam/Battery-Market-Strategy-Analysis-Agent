import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class PdfCorpusLoaderTest(unittest.TestCase):
    def test_load_pdf_corpus_reads_company_directories(self) -> None:
        from battery_agent.rag.pdf_corpus_loader import load_pdf_corpus

        class FakePage:
            def __init__(self, text: str) -> None:
                self._text = text

            def extract_text(self) -> str:
                return self._text

        class FakePdfReader:
            def __init__(self, path: Path) -> None:
                self.pages = [
                    FakePage(f"{path.stem} page one"),
                    FakePage(f"{path.stem} page two"),
                ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_dir = Path(tmp_dir)
            lg_dir = corpus_dir / "LG에너지솔루션"
            catl_dir = corpus_dir / "CATL"
            lg_dir.mkdir()
            catl_dir.mkdir()
            (lg_dir / "lg-report.pdf").write_bytes(b"%PDF-1.4")
            (catl_dir / "catl-report.pdf").write_bytes(b"%PDF-1.4")

            documents = load_pdf_corpus(corpus_dir, reader_factory=FakePdfReader)

        self.assertEqual([document.company for document in documents], ["CATL", "LG에너지솔루션"])
        self.assertEqual(documents[0].source_type, "pdf")
        self.assertEqual(documents[1].page_count, 2)
        self.assertIn("page one", documents[1].text)


class QwenEmbeddingClientTest(unittest.TestCase):
    def test_qwen_embedding_client_prefers_mps_and_normalizes_vectors(self) -> None:
        from battery_agent.rag.qwen_embedder import QwenEmbeddingClient

        class FakeTensor:
            def __init__(self, values: list[list[float]]) -> None:
                self.values = values

            def __getitem__(self, item: object) -> "FakeTensor":
                return self

            def masked_fill(self, mask: object, value: float) -> "FakeTensor":
                return self

            def sum(self, dim: int) -> "FakeTensor":
                if dim == 1:
                    return FakeTensor([[sum(row), sum(row)] for row in self.values])
                return self

            def __truediv__(self, other: object) -> "FakeTensor":
                return self

            def cpu(self) -> "FakeTensor":
                return self

            def tolist(self) -> list[list[float]]:
                return [[0.6, 0.8] for _ in self.values]

        class FakeTokenizer:
            def __call__(self, texts: list[str], **kwargs: object) -> dict[str, object]:
                return {
                    "input_ids": FakeTensor([[1.0, 2.0] for _ in texts]),
                    "attention_mask": FakeTensor([[1.0, 1.0] for _ in texts]),
                }

        class FakeModelOutput:
            def __init__(self, batch_size: int) -> None:
                self.last_hidden_state = FakeTensor([[1.0, 2.0] for _ in range(batch_size)])

        class FakeModel:
            def to(self, device: str) -> "FakeModel":
                self.device = device
                return self

            def eval(self) -> "FakeModel":
                return self

            def __call__(self, **kwargs: object) -> FakeModelOutput:
                input_ids = kwargs["input_ids"]
                return FakeModelOutput(len(input_ids.values))

        class FakeNoGrad:
            def __enter__(self) -> None:
                return None

            def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
                return None

        fake_torch = SimpleNamespace(
            backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: True)),
            cuda=SimpleNamespace(is_available=lambda: False),
            no_grad=lambda: FakeNoGrad(),
            clamp=lambda tensor, min=0.0: tensor,
            nn=SimpleNamespace(functional=SimpleNamespace(normalize=lambda tensor, p=2, dim=1: tensor)),
        )

        client = QwenEmbeddingClient(
            model_id="Qwen/Qwen3-Embedding-0.6B",
            device="auto",
            batch_size=2,
            tokenizer=FakeTokenizer(),
            model=FakeModel(),
            torch_module=fake_torch,
        )

        vectors = client.embed_documents(["doc 1", "doc 2"])

        self.assertEqual(client.resolved_device, "mps")
        self.assertEqual(vectors, [[0.6, 0.8], [0.6, 0.8]])

    def test_qwen_embedding_client_handles_real_torch_tensors(self) -> None:
        import torch

        from battery_agent.rag.qwen_embedder import QwenEmbeddingClient

        class FakeTokenizer:
            def __call__(self, texts: list[str], **kwargs: object) -> dict[str, object]:
                batch_size = len(texts)
                return {
                    "input_ids": torch.tensor([[1, 2]] * batch_size),
                    "attention_mask": torch.tensor([[1, 1]] * batch_size),
                }

        class FakeModelOutput:
            def __init__(self, batch_size: int) -> None:
                self.last_hidden_state = torch.tensor([[[1.0, 2.0], [1.0, 2.0]]] * batch_size)

        class FakeModel:
            def to(self, device: str) -> "FakeModel":
                return self

            def eval(self) -> "FakeModel":
                return self

            def __call__(self, **kwargs: object) -> FakeModelOutput:
                input_ids = kwargs["input_ids"]
                return FakeModelOutput(int(input_ids.shape[0]))

        client = QwenEmbeddingClient(
            model_id="Qwen/Qwen3-Embedding-0.6B",
            device="cpu",
            batch_size=1,
            tokenizer=FakeTokenizer(),
            model=FakeModel(),
            torch_module=torch,
        )

        vectors = client.embed_documents(["doc 1"])

        self.assertEqual(len(vectors), 1)
        self.assertAlmostEqual(sum(value * value for value in vectors[0]), 1.0, places=5)

    def test_qwen_embedding_client_retries_with_smaller_batches_after_oom(self) -> None:
        from battery_agent.rag.qwen_embedder import QwenEmbeddingClient

        class FakeTensor:
            def __init__(self, values: list[list[float]]) -> None:
                self.values = values

            def __getitem__(self, item: object) -> "FakeTensor":
                return self

            def sum(self, dim: int) -> "FakeTensor":
                if dim == 1:
                    return FakeTensor([[sum(row), sum(row)] for row in self.values])
                return self

            def __truediv__(self, other: object) -> "FakeTensor":
                return self

            def cpu(self) -> "FakeTensor":
                return self

            def to(self, device: str) -> "FakeTensor":
                return self

            def tolist(self) -> list[list[float]]:
                return [[0.6, 0.8] for _ in self.values]

        class FakeTokenizer:
            def __call__(self, texts: list[str], **kwargs: object) -> dict[str, object]:
                return {
                    "input_ids": FakeTensor([[1.0, 2.0] for _ in texts]),
                    "attention_mask": FakeTensor([[1.0, 1.0] for _ in texts]),
                }

        class FakeModelOutput:
            def __init__(self, batch_size: int) -> None:
                self.last_hidden_state = FakeTensor([[1.0, 2.0] for _ in range(batch_size)])

        class FakeModel:
            def __init__(self) -> None:
                self.batch_sizes: list[int] = []

            def to(self, device: str) -> "FakeModel":
                return self

            def eval(self) -> "FakeModel":
                return self

            def __call__(self, **kwargs: object) -> FakeModelOutput:
                input_ids = kwargs["input_ids"]
                batch_size = len(input_ids.values)
                self.batch_sizes.append(batch_size)
                if batch_size > 1:
                    raise RuntimeError("MPS backend out of memory")
                return FakeModelOutput(batch_size)

        class FakeNoGrad:
            def __enter__(self) -> None:
                return None

            def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
                return None

        fake_torch = SimpleNamespace(
            backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: True)),
            cuda=SimpleNamespace(is_available=lambda: False),
            no_grad=lambda: FakeNoGrad(),
            clamp=lambda tensor, min=0.0: tensor,
            nn=SimpleNamespace(functional=SimpleNamespace(normalize=lambda tensor, p=2, dim=1: tensor)),
        )
        model = FakeModel()
        client = QwenEmbeddingClient(
            model_id="Qwen/Qwen3-Embedding-0.6B",
            device="auto",
            batch_size=4,
            tokenizer=FakeTokenizer(),
            model=model,
            torch_module=fake_torch,
        )

        vectors = client.embed_documents(["a", "b", "c"])

        self.assertEqual(len(vectors), 3)
        self.assertEqual(model.batch_sizes[0], 3)
        self.assertIn(1, model.batch_sizes[1:])


class ChromaVectorStoreTest(unittest.TestCase):
    def test_chroma_vector_store_upserts_and_searches_by_company(self) -> None:
        from battery_agent.rag.chroma_store import ChromaVectorStore, ChromaRecord

        class FakeCollection:
            def __init__(self) -> None:
                self.upserts: list[dict[str, object]] = []

            def upsert(self, **kwargs: object) -> None:
                self.upserts.append(kwargs)

            def query(self, **kwargs: object) -> dict[str, object]:
                self.query_kwargs = kwargs
                return {
                    "ids": [["chunk-1"]],
                    "documents": [["battery strategy"]],
                    "distances": [[0.1]],
                    "metadatas": [[{"company": "LG에너지솔루션", "topics": ["strategy"]}]],
                }

        collection = FakeCollection()
        store = ChromaVectorStore(collection=collection)
        store.upsert_records(
            [
                ChromaRecord(
                    record_id="chunk-1",
                    document_id="doc-1",
                    text="battery strategy",
                    embedding=[0.1, 0.2],
                    metadata={"company": "LG에너지솔루션", "topics": ["strategy"]},
                )
            ]
        )

        hits = store.search(query_embedding=[0.1, 0.2], company="LG에너지솔루션", top_k=3)

        self.assertEqual(collection.upserts[0]["ids"], ["chunk-1"])
        self.assertEqual(collection.query_kwargs["where"], {"company": "LG에너지솔루션"})
        self.assertEqual(hits[0].document_id, "chunk-1")
        self.assertEqual(hits[0].metadata["topics"], ["strategy"])

    def test_chroma_vector_store_serializes_list_metadata_for_upsert(self) -> None:
        from battery_agent.rag.chroma_store import ChromaVectorStore, ChromaRecord

        class FakeCollection:
            def upsert(self, **kwargs: object) -> None:
                self.kwargs = kwargs

            def query(self, **kwargs: object) -> dict[str, object]:
                return {
                    "ids": [["chunk-1"]],
                    "documents": [["battery strategy"]],
                    "distances": [[0.1]],
                    "metadatas": [[{"company": "LG에너지솔루션", "topics": "[\"strategy\", \"risk\"]"}]],
                }

        collection = FakeCollection()
        store = ChromaVectorStore(collection=collection)
        store.upsert_records(
            [
                ChromaRecord(
                    record_id="chunk-1",
                    document_id="doc-1",
                    text="battery strategy",
                    embedding=[0.1, 0.2],
                    metadata={"company": "LG에너지솔루션", "topics": ["strategy", "risk"]},
                )
            ]
        )
        hits = store.search(query_embedding=[0.1, 0.2], company="LG에너지솔루션", top_k=1)

        self.assertEqual(
            collection.kwargs["metadatas"][0]["topics"],
            "[\"strategy\", \"risk\"]",
        )
        self.assertEqual(hits[0].metadata["topics"], ["strategy", "risk"])

    def test_chroma_vector_store_can_replace_collection(self) -> None:
        from battery_agent.rag.chroma_store import ChromaVectorStore

        class FakeClient:
            def __init__(self) -> None:
                self.deleted: list[str] = []
                self.created: list[str] = []

            def get_or_create_collection(self, name: str) -> object:
                self.created.append(name)
                return object()

            def delete_collection(self, name: str) -> None:
                self.deleted.append(name)

        client = FakeClient()
        store = ChromaVectorStore.open(
            chroma_dir=Path("/tmp/fake-chroma"),
            collection_name="battery-agent",
            client=client,
        )

        store.replace_collection()

        self.assertEqual(client.deleted, ["battery-agent"])
        self.assertEqual(client.created, ["battery-agent", "battery-agent"])


class CliIngestTest(unittest.TestCase):
    def test_ingest_pdfs_subcommand_runs_ingest_pipeline(self) -> None:
        from battery_agent.cli import main
        from battery_agent.config import Settings

        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = Settings(
                openai_api_key="test-key",
                default_companies=("LG에너지솔루션", "CATL"),
                default_model="gpt-4o-mini",
                embedding_model_id="Qwen/Qwen3-Embedding-0.6B",
                default_topic="배터리 시장 전략 비교",
                local_corpus_dir=Path(tmp_dir) / "corpus",
                output_root=Path(tmp_dir) / "artifacts",
                chroma_dir=Path(tmp_dir) / "chroma",
                chroma_collection="battery-agent",
                tavily_api_key=None,
                web_search_enabled=False,
                web_search_max_calls=3,
                web_search_max_results=5,
                embedding_device="auto",
                embedding_batch_size=4,
            )
            stdout = io.StringIO()
            with patch("battery_agent.cli.Settings.from_env", return_value=settings), patch(
                "battery_agent.cli.ingest_pdf_corpus",
                return_value=2,
            ) as ingest_mock, redirect_stdout(stdout):
                exit_code = main(["ingest-pdfs"])

        self.assertEqual(exit_code, 0)
        ingest_mock.assert_called_once()
        self.assertIn("ingested", stdout.getvalue())

    def test_ingest_pdf_corpus_replaces_collection_and_skips_page_limit(self) -> None:
        from battery_agent.config import Settings
        from battery_agent.rag.pdf_ingest import ingest_pdf_corpus

        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = Settings(
                openai_api_key="test-key",
                default_companies=("LG에너지솔루션", "CATL"),
                default_model="gpt-4o-mini",
                embedding_model_id="Qwen/Qwen3-Embedding-0.6B",
                default_topic="배터리 시장 전략 비교",
                local_corpus_dir=Path(tmp_dir) / "corpus",
                output_root=Path(tmp_dir) / "artifacts",
                chroma_dir=Path(tmp_dir) / "chroma",
                chroma_collection="battery-agent",
                tavily_api_key=None,
                web_search_enabled=False,
                web_search_max_calls=3,
                web_search_max_results=5,
                embedding_device="auto",
                embedding_batch_size=4,
            )

            documents = [
                SimpleNamespace(
                    document_id="doc-1",
                    company="LG에너지솔루션",
                    title="LG report",
                    text="alpha beta gamma delta epsilon zeta",
                    source_type="pdf",
                    page_count=70,
                    topics=["strategy"],
                ),
                SimpleNamespace(
                    document_id="doc-2",
                    company="CATL",
                    title="CATL report",
                    text="eta theta iota kappa lambda mu",
                    source_type="pdf",
                    page_count=70,
                    topics=["risk"],
                ),
            ]

            class FakeStore:
                def __init__(self) -> None:
                    self.replaced = False
                    self.records = []

                def replace_collection(self) -> None:
                    self.replaced = True

                def upsert_records(self, records: list[object]) -> None:
                    self.records = records

            fake_store = FakeStore()

            with patch("battery_agent.rag.pdf_ingest.load_pdf_corpus", return_value=documents), patch(
                "battery_agent.rag.pdf_ingest.ChromaVectorStore.open",
                return_value=fake_store,
            ), patch(
                "battery_agent.rag.pdf_ingest.QwenEmbeddingClient",
            ) as embedder_cls:
                embedder_cls.return_value.embed_documents.return_value = [[0.1, 0.2], [0.3, 0.4]]
                ingested = ingest_pdf_corpus(settings)

        self.assertTrue(fake_store.replaced)
        self.assertEqual(ingested, 2)
        self.assertEqual(len(fake_store.records), 2)
