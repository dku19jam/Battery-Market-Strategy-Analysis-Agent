import unittest


class ModelsTest(unittest.TestCase):
    def test_model_round_trip_serialization(self) -> None:
        from battery_agent.models.analysis import CompanyAnalysisResult
        from battery_agent.models.evidence import EvidenceBundle
        from battery_agent.models.report import ReportArtifact
        from battery_agent.models.retrieval import RetrievalResult
        from battery_agent.models.run_context import RunContext

        run_context = RunContext(
            run_id="run-001",
            topic="배터리 시장 전략 비교",
            output_dir="artifacts/run-001",
        )
        retrieval = RetrievalResult(
            company="LG에너지솔루션",
            queries=["LG diversification"],
            document_ids=["doc-1"],
        )
        evidence = EvidenceBundle(
            company="LG에너지솔루션",
            topics=["시장 배경"],
            document_ids=["doc-1"],
        )
        analysis = CompanyAnalysisResult(
            company="LG에너지솔루션",
            strategy_summary="요약",
            strengths=["생산 역량"],
            risks=["원가 부담"],
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
        self.assertEqual(ReportArtifact.from_dict(report.to_dict()), report)
