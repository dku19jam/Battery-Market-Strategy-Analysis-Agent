import json
import tempfile
import unittest
from pathlib import Path


class QueryBuilderTest(unittest.TestCase):
    def test_query_builder_creates_company_queries_and_rewrite(self) -> None:
        from battery_agent.search.query_builder import build_company_queries, rewrite_query

        queries = build_company_queries("LG에너지솔루션", "배터리 시장 전략 비교")
        rewritten = rewrite_query("배터리 시장 전략 비교", "portfolio diversification")

        self.assertTrue(any("LG에너지솔루션" in query for query in queries))
        self.assertIn("portfolio diversification", rewritten)


class LocalRetrieverTest(unittest.TestCase):
    def test_local_retriever_filters_by_company_and_writes_results(self) -> None:
        from battery_agent.rag.corpus_loader import CorpusDocument
        from battery_agent.rag.chunker import TextChunk
        from battery_agent.rag.vector_index import InMemoryVectorIndex, VectorRecord
        from battery_agent.search.local_retriever import LocalRetriever

        chunks = [
            TextChunk(
                chunk_id="doc-1-chunk-1",
                document_id="doc-1",
                company="LG에너지솔루션",
                text="battery strategy and diversification",
                page_start=1,
                page_end=1,
                topics=["strategy"],
            ),
            TextChunk(
                chunk_id="doc-2-chunk-1",
                document_id="doc-2",
                company="CATL",
                text="battery supply chain efficiency",
                page_start=1,
                page_end=1,
                topics=["supply-chain"],
            ),
        ]
        index = InMemoryVectorIndex()
        index.add(
            [
                VectorRecord(
                    record_id=chunks[0].chunk_id,
                    document_id=chunks[0].document_id,
                    text=chunks[0].text,
                    embedding=[1.0, 0.0],
                    metadata={"company": chunks[0].company, "topics": chunks[0].topics},
                ),
                VectorRecord(
                    record_id=chunks[1].chunk_id,
                    document_id=chunks[1].document_id,
                    text=chunks[1].text,
                    embedding=[0.3, 0.7],
                    metadata={"company": chunks[1].company, "topics": chunks[1].topics},
                ),
            ]
        )

        def fake_embed(query: str) -> list[float]:
            if "strategy" in query:
                return [1.0, 0.0]
            return [0.0, 1.0]

        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_path = Path(tmp_dir) / "retrieval.json"
            retriever = LocalRetriever(index=index, embed_query=fake_embed)
            hits = retriever.search(
                company="LG에너지솔루션",
                queries=["battery strategy"],
                top_k=2,
                artifact_path=artifact_path,
            )

            payload = json.loads(artifact_path.read_text(encoding="utf-8"))

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].document_id, "doc-1")
        self.assertEqual(payload[0]["document_id"], "doc-1")


class WebSearchTest(unittest.TestCase):
    def test_web_search_limits_results_and_caps_single_source(self) -> None:
        from battery_agent.search.web_search import LimitedWebSearcher, WebSearchResult

        def provider(query: str) -> list[WebSearchResult]:
            return [
                WebSearchResult(title="a", url="https://same.com/1", source="same.com", snippet="x"),
                WebSearchResult(title="b", url="https://same.com/2", source="same.com", snippet="y"),
                WebSearchResult(title="c", url="https://same.com/3", source="same.com", snippet="z"),
                WebSearchResult(title="d", url="https://other.com/1", source="other.com", snippet="w"),
            ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_path = Path(tmp_dir) / "web.json"
            searcher = LimitedWebSearcher(provider=provider, max_results=3, max_per_source=2)
            results = searcher.search("battery strategy", artifact_path=artifact_path)
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))

        self.assertEqual(len(results), 3)
        self.assertEqual(sum(1 for result in results if result.source == "same.com"), 2)
        self.assertEqual(len(payload), 3)

    def test_tavily_provider_maps_api_results(self) -> None:
        from battery_agent.search.web_search import TavilySearchProvider

        class FakeTavilyClient:
            def search(self, **kwargs: object) -> dict[str, object]:
                self.kwargs = kwargs
                return {
                    "results": [
                        {
                            "title": "LG strategy",
                            "url": "https://example.com/lg",
                            "content": "portfolio diversification update",
                        },
                        {
                            "title": "Missing URL",
                            "url": "",
                            "content": "should be dropped",
                        },
                    ]
                }

        client = FakeTavilyClient()
        provider = TavilySearchProvider(client=client, max_results=4)

        results = provider("LG battery strategy")

        self.assertEqual(client.kwargs["query"], "LG battery strategy")
        self.assertEqual(client.kwargs["max_results"], 4)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "LG strategy")
        self.assertEqual(results[0].source, "example.com")
