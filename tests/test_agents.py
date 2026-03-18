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
            def __init__(self) -> None:
                self.queries: list[str] = []

            def search(self, query: str) -> list[object]:
                self.queries.append(query)
                return []

        from battery_agent.agents.catl_retrieval import run_catl_retrieval

        web_searcher = FakeWebSearcher()
        result = run_catl_retrieval(
            topic="배터리 시장 전략 비교",
            local_retriever=FakeLocalRetriever(),
            web_searcher=web_searcher,
            min_hits=2,
        )

        self.assertEqual(result.company, "CATL")
        self.assertEqual(result.next_action, "curation")
        self.assertFalse(result.used_web_search)
        self.assertEqual(len(web_searcher.queries), 1)
        self.assertEqual(len(result.items), 2)

    def test_retrieval_always_runs_web_search_and_merges_results(self) -> None:
        from battery_agent.agents.lg_retrieval import run_lg_retrieval
        from battery_agent.models.retrieval import RetrievalItem
        from battery_agent.search.web_search import WebSearchResult

        class FakeLocalRetriever:
            def search(self, company: str, queries: list[str], top_k: int = 5) -> list[RetrievalItem]:
                return [
                    RetrievalItem(
                        document_id="local-doc",
                        chunk_id="local-doc-chunk-1",
                        title="LG local",
                        text="local strategy evidence",
                        score=0.95,
                        source_type="report",
                        source="local",
                        topics=["strategy"],
                    ),
                    RetrievalItem(
                        document_id="local-risk",
                        chunk_id="local-risk-chunk-1",
                        title="LG risk",
                        text="local risk evidence",
                        score=0.9,
                        source_type="report",
                        source="local",
                        topics=["risk"],
                    ),
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
                        snippet="web market evidence",
                    )
                ]

        web_searcher = FakeWebSearcher()
        result = run_lg_retrieval(
            topic="배터리 시장 전략 비교",
            local_retriever=FakeLocalRetriever(),
            web_searcher=web_searcher,
            min_hits=2,
        )

        self.assertTrue(result.used_web_search)
        self.assertEqual(len(web_searcher.queries), 1)
        self.assertEqual(len(result.items), 3)
        self.assertTrue(any(item.source_type == "web" for item in result.items))


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

        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_path = Path(tmp_dir) / "lg-curation.json"
            bundle = run_lg_curation(retrieval, artifact_path=artifact_path)
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))

        self.assertEqual(bundle.next_action, "analysis")
        self.assertEqual(len(bundle.entries), 2)
        self.assertEqual(bundle.missing_topics, [])
        self.assertEqual(sorted(bundle.topic_buckets.keys()), ["risk", "strategy"])
        self.assertEqual(len(bundle.topic_buckets["strategy"]), 1)
        self.assertEqual(payload["next_action"], "analysis")


class AnalysisAndComparisonAgentTest(unittest.TestCase):
    def test_analysis_and_comparison_generate_reference_handoff(self) -> None:
        from battery_agent.agents.catl_analysis import run_catl_analysis
        from battery_agent.agents.comparison import run_comparison
        from battery_agent.agents.lg_analysis import run_lg_analysis
        from battery_agent.models.evidence import EvidenceBundle, EvidenceItem

        class FakeStructuredLlm:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []

            def generate_json(
                self,
                *,
                model: str,
                system_prompt: str,
                user_prompt: str,
                schema_name: str,
                schema: dict[str, object],
            ) -> dict[str, object]:
                self.calls.append(
                    {
                        "model": model,
                        "system_prompt": system_prompt,
                        "user_prompt": user_prompt,
                        "schema_name": schema_name,
                        "schema": schema,
                    }
                )
                if schema_name == "company_analysis":
                    return {
                        "strategy_summary": "북미 고객 기반 확대를 통한 성장 전략",
                        "strengths": ["북미 고객 기반 확대", "생산 역량"],
                        "risks": ["원가 부담", "수요 둔화"],
                        "citations": ["lg-1", "bad-doc-id"],
                        "metrics": [
                            {"metric": "매출", "value": "25.6조원", "source_hint": "2024 사업보고서"},
                            {"metric": "영업이익", "value": "5,754억원", "source_hint": "2024 사업보고서"},
                        ],
                        "analysis_notes": "evidence grouped by topic",
                    }
                return {
                    "normalized_companies": [
                        {
                            "company": "LG에너지솔루션",
                            "strategy_summary": "북미 고객 기반 확대를 통한 성장 전략",
                            "strengths": ["생산 역량"],
                            "risks": ["원가 부담"],
                        },
                        {
                            "company": "CATL",
                            "strategy_summary": "공급망 다변화 중심 전략",
                            "strengths": ["원가 경쟁력"],
                            "risks": ["지정학 리스크"],
                        },
                    ],
                    "strategy_differences": ["성장 지역과 공급망 접근이 다르다"],
                    "strengths_weaknesses": ["LG는 고객 기반, CATL은 원가 경쟁력이 강점"],
                    "swot": {
                        "strengths": ["LG는 고객 기반, CATL은 원가 경쟁력과 파트너십이 강점이다."],
                        "weaknesses": ["LG는 원가 부담, CATL은 지정학 리스크 노출이 약점이다."],
                        "opportunities": ["ESS 확대와 북미 공급망 재편은 추가 성장 기회다."],
                        "threats": ["시장 둔화와 기술 전환 속도는 공통 위협이다."],
                    },
                    "insights": ["시장 둔화 국면에서 공급망 안정성이 중요하다"],
                    "company_metrics": [
                        {"company": "LG에너지솔루션", "metric": "매출", "value": "25.6조원", "source_hint": "2024 사업보고서"},
                        {"company": "CATL", "metric": "시장점유율", "value": "27.0%", "source_hint": "2024 Annual Report"},
                    ],
                    "refinement_requests": [],
                }

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
            topic_buckets={},
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
            topic_buckets={},
            missing_topics=[],
            next_action="analysis",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            analysis_artifact_path = Path(tmp_dir) / "lg-analysis.json"
            comparison_artifact_path = Path(tmp_dir) / "comparison.json"
            fake_llm = FakeStructuredLlm()
            lg_analysis = run_lg_analysis(
                lg_bundle,
                llm_client=fake_llm,
                artifact_path=analysis_artifact_path,
            )
            catl_analysis = run_catl_analysis(
                catl_bundle,
                llm_client=fake_llm,
            )
            comparison = run_comparison(
                lg_analysis,
                catl_analysis,
                llm_client=fake_llm,
                artifact_path=comparison_artifact_path,
            )
            analysis_payload = json.loads(analysis_artifact_path.read_text(encoding="utf-8"))
            comparison_payload = json.loads(comparison_artifact_path.read_text(encoding="utf-8"))

        self.assertEqual(lg_analysis.next_action, "comparison")
        self.assertEqual(catl_analysis.next_action, "comparison")
        self.assertEqual(comparison.next_action, "reference")
        self.assertEqual(comparison.strategy_differences, ["성장 지역과 공급망 접근이 다르다"])
        self.assertEqual(lg_analysis.metrics[0].metric, "매출")
        self.assertEqual(comparison.swot.strengths[0], "LG는 고객 기반, CATL은 원가 경쟁력과 파트너십이 강점이다.")
        self.assertEqual(comparison.company_metrics[0].metric, "매출")
        self.assertEqual(comparison.refinement_requests, [])
        self.assertEqual(lg_analysis.citations, ["lg-1"])
        self.assertIn("strategy", fake_llm.calls[0]["user_prompt"])
        self.assertEqual(analysis_payload["company"], "LG에너지솔루션")
        self.assertEqual(comparison_payload["next_action"], "reference")

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

        class FakeStructuredLlm:
            def generate_json(
                self,
                *,
                model: str,
                system_prompt: str,
                user_prompt: str,
                schema_name: str,
                schema: dict[str, object],
            ) -> dict[str, object]:
                return {
                    "normalized_companies": [],
                    "strategy_differences": ["difference"],
                    "strengths_weaknesses": ["comparison"],
                    "swot": {
                        "strengths": ["strength"],
                        "weaknesses": ["weakness"],
                        "opportunities": ["opportunity"],
                        "threats": ["threat"],
                    },
                    "insights": ["insight"],
                    "company_metrics": [],
                    "refinement_requests": [],
                }

        comparison = run_comparison(lg_analysis, catl_analysis, llm_client=FakeStructuredLlm())

        self.assertEqual(comparison.next_action, "analysis_refinement")
        self.assertEqual(comparison.refinement_requests, ["LG에너지솔루션"])
