import json
import tempfile
import unittest
from pathlib import Path


class RetrievalAgentTest(unittest.TestCase):
    def test_lg_retrieval_uses_web_fallback_when_local_evidence_is_thin(self) -> None:
        from battery_agent.models.retrieval import RetrievalItem
        from battery_agent.search.web_search import WebSearchResult

        class FakeLocalRetriever:
            def __init__(self) -> None:
                self.calls: list[tuple[str, list[str], int]] = []

            def search(self, company: str, queries: list[str], top_k: int = 5) -> list[RetrievalItem]:
                self.calls.append((company, queries, top_k))
                return [
                    RetrievalItem(
                        document_id="doc-1",
                        chunk_id="doc-1-chunk-1",
                        title="LG local",
                        text="local strategy evidence",
                        score=0.8,
                        source_type="report",
                        source="local",
                        topics=["strategy"],
                    )
                ]

        class FakeWebSearcher:
            def __init__(self) -> None:
                self.queries: list[str] = []

            def search(self, query: str) -> list[WebSearchResult]:
                self.queries.append(query)
                return [
                    WebSearchResult(
                        title="LG web",
                        url="https://example.com/lg",
                        source="example.com",
                        snippet="portfolio diversification update",
                    )
                ]

        from battery_agent.agents.lg_retrieval import run_lg_retrieval

        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_path = Path(tmp_dir) / "lg-retrieval.json"
            local_retriever = FakeLocalRetriever()
            web_searcher = FakeWebSearcher()

            result = run_lg_retrieval(
                topic="배터리 시장 전략 비교",
                local_retriever=local_retriever,
                web_searcher=web_searcher,
                artifact_path=artifact_path,
                min_hits=2,
            )

            payload = json.loads(artifact_path.read_text(encoding="utf-8"))

        self.assertEqual(result.company, "LG에너지솔루션")
        self.assertEqual(result.next_action, "curation")
        self.assertTrue(result.used_web_search)
        self.assertEqual(len(result.items), 2)
        self.assertEqual(web_searcher.queries, ["LG에너지솔루션 배터리 시장 전략 비교 portfolio diversification"])
        self.assertEqual(payload["next_action"], "curation")

    def test_catl_retrieval_stays_local_when_hits_are_sufficient(self) -> None:
        from battery_agent.models.retrieval import RetrievalItem

        class FakeLocalRetriever:
            def search(self, company: str, queries: list[str], top_k: int = 5) -> list[RetrievalItem]:
                return [
                    RetrievalItem(
                        document_id="doc-1",
                        chunk_id="doc-1-chunk-1",
                        title="CATL local",
                        text="catl strategy evidence",
                        score=0.95,
                        source_type="report",
                        source="local",
                        topics=["strategy"],
                    ),
                    RetrievalItem(
                        document_id="doc-2",
                        chunk_id="doc-2-chunk-1",
                        title="CATL risk",
                        text="catl risk evidence",
                        score=0.88,
                        source_type="report",
                        source="local",
                        topics=["risk"],
                    ),
                ]

        class FakeWebSearcher:
            def search(self, query: str) -> list[object]:
                raise AssertionError("web search should not be called")

        from battery_agent.agents.catl_retrieval import run_catl_retrieval

        result = run_catl_retrieval(
            topic="배터리 시장 전략 비교",
            local_retriever=FakeLocalRetriever(),
            web_searcher=FakeWebSearcher(),
            min_hits=2,
        )

        self.assertEqual(result.company, "CATL")
        self.assertEqual(result.next_action, "curation")
        self.assertFalse(result.used_web_search)
        self.assertEqual(len(result.items), 2)


class CurationAgentTest(unittest.TestCase):
    def test_lg_curation_deduplicates_and_requests_analysis(self) -> None:
        from battery_agent.agents.lg_curation import run_lg_curation
        from battery_agent.models.retrieval import RetrievalItem, RetrievalResult

        retrieval = RetrievalResult(
            company="LG에너지솔루션",
            queries=["LG query"],
            items=[
                RetrievalItem(
                    document_id="doc-1",
                    chunk_id="doc-1-a",
                    title="LG Strategy",
                    text="strategy evidence",
                    score=0.9,
                    source_type="report",
                    source="local",
                    topics=["strategy"],
                ),
                RetrievalItem(
                    document_id="doc-1",
                    chunk_id="doc-1-b",
                    title="LG Strategy duplicate",
                    text="strategy evidence",
                    score=0.7,
                    source_type="web",
                    source="example.com",
                    topics=["strategy"],
                ),
                RetrievalItem(
                    document_id="doc-2",
                    chunk_id="doc-2-a",
                    title="LG Risk",
                    text="risk evidence",
                    score=0.8,
                    source_type="report",
                    source="local",
                    topics=["risk"],
                ),
            ],
            next_action="curation",
            used_web_search=False,
            partial=False,
        )

        bundle = run_lg_curation(retrieval)

        self.assertEqual(bundle.next_action, "analysis")
        self.assertEqual(len(bundle.entries), 2)
        self.assertEqual(bundle.missing_topics, [])


class AnalysisAndComparisonAgentTest(unittest.TestCase):
    def test_analysis_and_comparison_generate_reference_handoff(self) -> None:
        from battery_agent.agents.catl_analysis import run_catl_analysis
        from battery_agent.agents.comparison import run_comparison
        from battery_agent.agents.lg_analysis import run_lg_analysis
        from battery_agent.models.evidence import EvidenceBundle, EvidenceItem

        lg_bundle = EvidenceBundle(
            company="LG에너지솔루션",
            topics=["strategy", "risk"],
            entries=[
                EvidenceItem(
                    document_id="lg-1",
                    snippet="북미 고객 기반 확대",
                    source_type="report",
                    source="local",
                    topics=["strategy"],
                    score=0.9,
                ),
                EvidenceItem(
                    document_id="lg-2",
                    snippet="원가 부담과 수요 둔화",
                    source_type="report",
                    source="local",
                    topics=["risk"],
                    score=0.8,
                ),
            ],
            missing_topics=[],
            next_action="analysis",
        )
        catl_bundle = EvidenceBundle(
            company="CATL",
            topics=["strategy", "risk"],
            entries=[
                EvidenceItem(
                    document_id="catl-1",
                    snippet="공급망 다변화와 원가 경쟁력",
                    source_type="report",
                    source="local",
                    topics=["strategy"],
                    score=0.92,
                ),
                EvidenceItem(
                    document_id="catl-2",
                    snippet="지정학 리스크 노출",
                    source_type="report",
                    source="local",
                    topics=["risk"],
                    score=0.75,
                ),
            ],
            missing_topics=[],
            next_action="analysis",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_path = Path(tmp_dir) / "lg-analysis.json"
            lg_analysis = run_lg_analysis(lg_bundle, artifact_path=artifact_path)
            catl_analysis = run_catl_analysis(catl_bundle)
            comparison = run_comparison(lg_analysis, catl_analysis)
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))

        self.assertEqual(lg_analysis.next_action, "comparison")
        self.assertEqual(catl_analysis.next_action, "comparison")
        self.assertEqual(comparison.next_action, "reference")
        self.assertGreater(len(comparison.strategy_differences), 0)
        self.assertEqual(comparison.refinement_requests, [])
        self.assertEqual(payload["company"], "LG에너지솔루션")

    def test_comparison_requests_refinement_for_partial_analysis(self) -> None:
        from battery_agent.agents.comparison import run_comparison
        from battery_agent.models.analysis import CompanyAnalysisResult

        lg_analysis = CompanyAnalysisResult(
            company="LG에너지솔루션",
            strategy_summary="LG summary",
            strengths=["strength"],
            risks=["risk"],
            citations=["lg-1"],
            analysis_notes="partial",
            next_action="comparison",
            partial=True,
        )
        catl_analysis = CompanyAnalysisResult(
            company="CATL",
            strategy_summary="CATL summary",
            strengths=["strength"],
            risks=["risk"],
            citations=["catl-1"],
            analysis_notes="complete",
            next_action="comparison",
            partial=False,
        )

        comparison = run_comparison(lg_analysis, catl_analysis)

        self.assertEqual(comparison.next_action, "analysis_refinement")
        self.assertEqual(comparison.refinement_requests, ["LG에너지솔루션"])
