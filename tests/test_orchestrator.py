import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class OrchestratorTest(unittest.TestCase):
    def test_maybe_run_refinement_retries_only_low_quality_lane(self) -> None:
        from battery_agent.config import Settings
        from battery_agent.models.analysis import CompanyAnalysisResult
        from battery_agent.models.evidence import EvidenceBundle, EvidenceItem
        from battery_agent.models.report import ComparisonResult, SWOTSection
        from battery_agent.models.retrieval import RetrievalItem, RetrievalResult
        from battery_agent.models.run_context import RunContext
        from battery_agent.pipeline.orchestrator import maybe_run_refinement_retries
        from battery_agent.pipeline.workflow_state import LaneState, WorkflowState

        low_analysis = CompanyAnalysisResult(
            company="CATL",
            strategy_summary="전략 근거 부족",
            strengths=["전략 근거 부족"],
            risks=["리스크 근거 부족"],
            citations=[],
            partial=True,
        )
        low_bundle = EvidenceBundle(
            company="CATL",
            topics=["strategy"],
            entries=[
                EvidenceItem(
                    document_id="catl-1",
                    snippet="short",
                    source_type="web",
                    source="unknown",
                    topics=["strategy"],
                    score=0.1,
                )
            ],
            topic_buckets={},
            missing_topics=["risk"],
            next_action="analysis",
        )
        low_retrieval = RetrievalResult(
            company="CATL",
            queries=["q"],
            items=[
                RetrievalItem(
                    document_id="catl-1",
                    chunk_id="chunk-1",
                    title="t",
                    text="short",
                    score=0.1,
                    source_type="web",
                    source="unknown",
                    topics=["strategy"],
                )
            ],
            next_action="curation",
            used_web_search=False,
            partial=False,
        )
        high_analysis = CompanyAnalysisResult(
            company="LG에너지솔루션",
            strategy_summary="요약",
            strengths=["강점1", "강점2"],
            risks=["리스크1", "리스크2"],
            citations=["doc-1", "doc-2", "doc-3"],
            partial=False,
        )
        high_bundle = EvidenceBundle(
            company="LG에너지솔루션",
            topics=["strategy", "risk"],
            entries=[
                EvidenceItem(
                    document_id="doc-1",
                    snippet="a",
                    source_type="report",
                    source="trusted",
                    topics=["strategy"],
                    score=0.9,
                ),
                EvidenceItem(
                    document_id="doc-2",
                    snippet="b",
                    source_type="report",
                    source="trusted",
                    topics=["risk"],
                    score=0.8,
                ),
                EvidenceItem(
                    document_id="doc-3",
                    snippet="c",
                    source_type="report",
                    source="trusted",
                    topics=["strategy", "risk"],
                    score=0.7,
                ),
            ],
            topic_buckets={},
            missing_topics=[],
            next_action="analysis",
        )
        high_retrieval = RetrievalResult(
            company="LG에너지솔루션",
            queries=["q"],
            items=[],
            next_action="curation",
            used_web_search=True,
            partial=False,
        )
        comparison = ComparisonResult(
            normalized_companies=[],
            strategy_differences=["d"],
            strengths_weaknesses=["s"],
            swot=SWOTSection(),
            insights=["i"],
            refinement_requests=["LG에너지솔루션", "CATL"],
            next_action="analysis_refinement",
        )
        state = WorkflowState(
            run_context=RunContext(run_id="r1", topic="t", output_dir="o"),
            model_name="gpt-4o-mini",
            corpus_fingerprint="abc",
            search_params={},
            lg_lane=LaneState(
                company="LG에너지솔루션",
                retrieval_result=high_retrieval,
                evidence_bundle=high_bundle,
                analysis_result=high_analysis,
            ),
            catl_lane=LaneState(
                company="CATL",
                retrieval_result=low_retrieval,
                evidence_bundle=low_bundle,
                analysis_result=low_analysis,
            ),
            comparison_result=comparison,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = Settings(
                openai_api_key="test-key",
                default_companies=("LG에너지솔루션", "CATL"),
                default_model="gpt-4o-mini",
                embedding_model_id="Qwen/Qwen3-Embedding-0.6B",
                default_topic="배터리 시장 전략 비교",
                local_corpus_dir=Path(tmp_dir) / "corpus",
                output_root=Path(tmp_dir) / "artifacts",
                tavily_api_key=None,
                web_search_enabled=False,
                web_search_max_calls=6,
                web_search_max_results=5,
            )
            settings.local_corpus_dir.mkdir(parents=True, exist_ok=True)
            run_root = settings.output_root / "run-1"
            run_root.mkdir(parents=True, exist_ok=True)
            run_paths = type("RunPaths", (), {"root": run_root})

            with patch(
                "battery_agent.pipeline.orchestrator.run_lane_pipeline",
            ) as run_lane_pipeline_mock:
                reran = maybe_run_refinement_retries(
                    state=state,
                    settings=settings,
                    topic="배터리 시장 전략 비교",
                    run_paths=run_paths,
                    local_retriever=object(),
                    structured_llm=object(),
                    logger=None,
                )

        self.assertTrue(reran)
        self.assertEqual(run_lane_pipeline_mock.call_count, 1)
        self.assertEqual(run_lane_pipeline_mock.call_args.kwargs["lane"].company, "CATL")

    def test_lane_quality_score_and_relaxed_refinement_retry_policy(self) -> None:
        from battery_agent.models.analysis import CompanyAnalysisResult
        from battery_agent.models.evidence import EvidenceBundle, EvidenceItem
        from battery_agent.models.retrieval import RetrievalItem, RetrievalResult
        from battery_agent.pipeline.orchestrator import (
            lane_quality_score,
            should_retry_refinement,
        )

        low_quality_analysis = CompanyAnalysisResult(
            company="CATL",
            strategy_summary="전략 근거 부족",
            strengths=["전략 근거 부족"],
            risks=["리스크 근거 부족"],
            citations=[],
            analysis_notes="insufficient",
            partial=True,
        )
        low_quality_bundle = EvidenceBundle(
            company="CATL",
            topics=["strategy"],
            entries=[
                EvidenceItem(
                    document_id="doc-1",
                    snippet="short",
                    source_type="web",
                    source="unknown",
                    topics=["strategy"],
                    score=0.1,
                )
            ],
            topic_buckets={},
            missing_topics=["risk"],
            next_action="analysis",
        )
        low_quality_retrieval = RetrievalResult(
            company="CATL",
            queries=["q"],
            items=[
                RetrievalItem(
                    document_id="doc-1",
                    chunk_id="chunk-1",
                    title="t",
                    text="short",
                    score=0.1,
                    source_type="web",
                    source="unknown",
                    topics=["strategy"],
                )
            ],
            next_action="curation",
            used_web_search=False,
            partial=False,
        )
        high_quality_analysis = CompanyAnalysisResult(
            company="LG에너지솔루션",
            strategy_summary="전략 요약",
            strengths=["강점 1", "강점 2"],
            risks=["리스크 1", "리스크 2"],
            citations=["doc-a", "doc-b", "doc-c"],
            analysis_notes="ok",
            partial=False,
        )
        high_quality_bundle = EvidenceBundle(
            company="LG에너지솔루션",
            topics=["strategy", "risk"],
            entries=[
                EvidenceItem(
                    document_id="doc-a",
                    snippet="e1",
                    source_type="report",
                    source="trusted",
                    topics=["strategy"],
                    score=0.9,
                ),
                EvidenceItem(
                    document_id="doc-b",
                    snippet="e2",
                    source_type="report",
                    source="trusted",
                    topics=["risk"],
                    score=0.8,
                ),
                EvidenceItem(
                    document_id="doc-c",
                    snippet="e3",
                    source_type="report",
                    source="trusted",
                    topics=["strategy", "risk"],
                    score=0.7,
                ),
            ],
            topic_buckets={},
            missing_topics=[],
            next_action="analysis",
        )
        high_quality_retrieval = RetrievalResult(
            company="LG에너지솔루션",
            queries=["q"],
            items=[
                RetrievalItem(
                    document_id="doc-a",
                    chunk_id="chunk-a",
                    title="t",
                    text="e1",
                    score=0.9,
                    source_type="report",
                    source="trusted",
                    topics=["strategy"],
                )
            ],
            next_action="curation",
            used_web_search=True,
            partial=False,
        )

        self.assertLess(
            lane_quality_score(low_quality_analysis, low_quality_bundle, low_quality_retrieval),
            lane_quality_score(high_quality_analysis, high_quality_bundle, high_quality_retrieval),
        )
        self.assertTrue(
            should_retry_refinement(
                quality_score=lane_quality_score(
                    low_quality_analysis,
                    low_quality_bundle,
                    low_quality_retrieval,
                ),
                retries=0,
                max_retries=1,
            )
        )
        self.assertFalse(
            should_retry_refinement(
                quality_score=lane_quality_score(
                    high_quality_analysis,
                    high_quality_bundle,
                    high_quality_retrieval,
                ),
                retries=0,
                max_retries=1,
            )
        )

    def test_allocate_web_search_calls_splits_evenly(self) -> None:
        from battery_agent.pipeline.orchestrator import allocate_web_search_calls

        self.assertEqual(allocate_web_search_calls(6), (3, 3))
        self.assertEqual(allocate_web_search_calls(5), (2, 3))
        self.assertEqual(allocate_web_search_calls(1), (1, 1))

    def test_build_company_web_searchers_builds_two_searchers(self) -> None:
        from battery_agent.config import Settings
        from battery_agent.pipeline.orchestrator import build_company_web_searchers

        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = Settings(
                openai_api_key="test-key",
                default_companies=("LG에너지솔루션", "CATL"),
                default_model="gpt-4o-mini",
                embedding_model_id="Qwen/Qwen3-Embedding-0.6B",
                default_topic="배터리 시장 전략 비교",
                local_corpus_dir=Path(tmp_dir) / "corpus",
                output_root=Path(tmp_dir) / "artifacts",
                tavily_api_key="tvly-test",
                web_search_enabled=True,
                web_search_max_calls=6,
                web_search_max_results=5,
            )
            settings.local_corpus_dir.mkdir(parents=True, exist_ok=True)

            with patch(
                "battery_agent.pipeline.orchestrator.build_tavily_web_searcher",
                side_effect=["lg", "catl"],
            ) as build_mock:
                lg_searcher, catl_searcher = build_company_web_searchers(settings)

        self.assertEqual(lg_searcher, "lg")
        self.assertEqual(catl_searcher, "catl")
        self.assertEqual(build_mock.call_count, 2)
        self.assertEqual(build_mock.call_args_list[0].kwargs["max_calls"], 3)
        self.assertEqual(build_mock.call_args_list[1].kwargs["max_calls"], 3)

    def test_orchestrator_runs_end_to_end_and_writes_outputs(self) -> None:
        from battery_agent.config import Settings
        from battery_agent.pipeline.orchestrator import run_analysis_workflow

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
                if schema_name == "company_analysis":
                    return {
                        "strategy_summary": "요약",
                        "strengths": ["강점"],
                        "risks": ["리스크"],
                        "citations": ["doc-1"],
                        "analysis_notes": "done",
                    }
                if schema_name == "final_report_sections":
                    return {
                        "summary": "근거가 다소 제한적이지만 두 회사 전략 차이를 한국어로 요약한다.",
                        "market_background": "배터리 시장 전략 비교 배경이다.",
                        "lg_strategy": "LG 전략 상세 설명이다.",
                        "catl_strategy": "CATL 전략 상세 설명이다.",
                        "strategy_comparison": "두 회사 전략 비교 설명이다.",
                        "swot": "강점, 약점, 기회, 위협 설명이다.",
                        "insights": "의사결정에 필요한 시사점 설명이다.",
                    }
                return {
                    "normalized_companies": [],
                    "strategy_differences": ["차이점"],
                    "strengths_weaknesses": ["강점/약점"],
                    "swot": ["SWOT"],
                    "insights": ["시사점"],
                    "refinement_requests": [],
                }

        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = Settings(
                openai_api_key="test-key",
                default_companies=("LG에너지솔루션", "CATL"),
                default_model="gpt-4o-mini",
                embedding_model_id="Qwen/Qwen3-Embedding-0.6B",
                default_topic="배터리 시장 전략 비교",
                local_corpus_dir=Path(tmp_dir) / "corpus",
                output_root=Path(tmp_dir) / "artifacts",
                tavily_api_key=None,
                web_search_enabled=False,
                web_search_max_calls=3,
                web_search_max_results=5,
            )
            settings.local_corpus_dir.mkdir(parents=True, exist_ok=True)
            (settings.local_corpus_dir / "docs.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "document_id": "doc-1",
                                "company": "LG에너지솔루션",
                                "title": "LG Report",
                                "text": "strategy growth risk",
                                "source_type": "report",
                                "topics": ["strategy", "risk"],
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "document_id": "doc-2",
                                "company": "CATL",
                                "title": "CATL Report",
                                "text": "strategy scale risk",
                                "source_type": "report",
                                "topics": ["strategy", "risk"],
                            },
                            ensure_ascii=False,
                        ),
                    ]
                ),
                encoding="utf-8",
            )

            result = run_analysis_workflow(
                settings=settings,
                topic="배터리 시장 전략 비교",
                run_id="run-001",
                llm_client=FakeStructuredLlm(),
            )

            markdown_path = Path(tmp_dir) / "artifacts" / "run-001" / "reports" / "final_report.md"
            pdf_path = Path(tmp_dir) / "artifacts" / "run-001" / "reports" / "final_report.pdf"
            markdown_exists = markdown_path.exists()
            pdf_exists = pdf_path.exists()

        self.assertEqual(result.status, "completed")
        self.assertTrue(markdown_exists)
        self.assertTrue(pdf_exists)

    def test_orchestrator_prefers_chroma_retriever_when_available(self) -> None:
        from battery_agent.config import Settings
        from battery_agent.pipeline.orchestrator import build_local_retriever

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
            settings.local_corpus_dir.mkdir(parents=True, exist_ok=True)
            (settings.local_corpus_dir / "LG에너지솔루션").mkdir()
            (settings.local_corpus_dir / "LG에너지솔루션" / "lg.pdf").write_bytes(b"%PDF-1.4")
            run_dir = settings.output_root / "run-001"
            run_dir.mkdir(parents=True, exist_ok=True)

            chroma_retriever = object()

            with unittest.mock.patch(
                "battery_agent.pipeline.orchestrator.open_chroma_retriever",
                return_value=chroma_retriever,
            ) as chroma_mock, unittest.mock.patch(
                "battery_agent.pipeline.orchestrator.load_corpus",
            ) as load_corpus_mock:
                retriever = build_local_retriever(settings=settings, run_root=run_dir, logger=None)

        self.assertIs(retriever, chroma_retriever)
        chroma_mock.assert_called_once()
        load_corpus_mock.assert_not_called()

    def test_orchestrator_falls_back_to_in_memory_for_non_pdf_corpus(self) -> None:
        from battery_agent.config import Settings
        from battery_agent.pipeline.orchestrator import build_local_retriever

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
            settings.local_corpus_dir.mkdir(parents=True, exist_ok=True)
            (settings.local_corpus_dir / "docs.jsonl").write_text(
                '{"document_id":"doc-1","company":"LG에너지솔루션","title":"t","text":"alpha beta","source_type":"report"}\n',
                encoding="utf-8",
            )
            run_dir = settings.output_root / "run-001"
            run_dir.mkdir(parents=True, exist_ok=True)

            with patch(
                "battery_agent.pipeline.orchestrator.open_chroma_retriever",
            ) as chroma_mock:
                retriever = build_local_retriever(settings=settings, run_root=run_dir, logger=None)

        self.assertIsNotNone(retriever)
        chroma_mock.assert_not_called()
