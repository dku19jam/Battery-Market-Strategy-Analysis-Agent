import unittest


class ModelsTest(unittest.TestCase):
    def test_model_round_trip_serialization(self) -> None:
        from battery_agent.models.analysis import CompanyAnalysisResult
        from battery_agent.models.evidence import EvidenceBundle, EvidenceItem
        from battery_agent.models.report import ComparisonResult, NormalizedCompanyAnalysis, ReportArtifact
        from battery_agent.models.retrieval import RetrievalItem, RetrievalResult
        from battery_agent.models.run_context import RunContext

        run_context = RunContext(
            run_id="run-001",
            topic="배터리 시장 전략 비교",
            output_dir="artifacts/run-001",
        )
        retrieval_item = RetrievalItem(
            document_id="doc-1",
            chunk_id="doc-1-chunk-1",
            title="LG Strategy",
            text="battery diversification",
            score=0.9,
            source_type="report",
            source="local",
            topics=["strategy"],
        )
        retrieval = RetrievalResult(
            company="LG에너지솔루션",
            queries=["LG diversification"],
            items=[retrieval_item],
            next_action="curation",
            used_web_search=False,
            partial=False,
        )
        evidence_item = EvidenceItem(
            document_id="doc-1",
            snippet="battery diversification",
            source_type="report",
            source="local",
            topics=["strategy"],
            score=0.9,
        )
        evidence = EvidenceBundle(
            company="LG에너지솔루션",
            topics=["strategy"],
            entries=[evidence_item],
            topic_buckets={"strategy": [evidence_item]},
            missing_topics=["risk"],
            next_action="analysis",
        )
        analysis = CompanyAnalysisResult(
            company="LG에너지솔루션",
            strategy_summary="요약",
            strengths=["생산 역량"],
            risks=["원가 부담"],
            citations=["doc-1"],
            analysis_notes="analysis note",
            next_action="comparison",
            partial=False,
        )
        comparison = ComparisonResult(
            normalized_companies=[
                NormalizedCompanyAnalysis(
                    company="LG에너지솔루션",
                    strategy_summary="요약",
                    strengths=["생산 역량"],
                    risks=["원가 부담"],
                    citations=["doc-1"],
                    partial=False,
                )
            ],
            strategy_differences=["LG는 북미 집중, CATL은 공급망 다변화"],
            strengths_weaknesses=["LG는 생산 역량 강점, CATL은 가격 경쟁력 강점"],
            swot=["Strength: scale", "Risk: pricing"],
            insights=["시장 변동성 대응이 핵심"],
            refinement_requests=[],
            next_action="reference",
        )
        report = ReportArtifact(
            title="최종 보고서",
            markdown_path="artifacts/run-001/report.md",
            pdf_path="artifacts/run-001/report.pdf",
        )

        self.assertEqual(RunContext.from_dict(run_context.to_dict()), run_context)
        self.assertEqual(RetrievalResult.from_dict(retrieval.to_dict()), retrieval)
        self.assertEqual(EvidenceBundle.from_dict(evidence.to_dict()), evidence)
        self.assertEqual(CompanyAnalysisResult.from_dict(analysis.to_dict()), analysis)
        self.assertEqual(ComparisonResult.from_dict(comparison.to_dict()), comparison)
        self.assertEqual(ReportArtifact.from_dict(report.to_dict()), report)
