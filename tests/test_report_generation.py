import unittest


class ReportGenerationTest(unittest.TestCase):
    def test_build_report_marks_partial_when_references_are_missing(self) -> None:
        from battery_agent.agents.report_generation import build_report
        from battery_agent.models.analysis import CompanyAnalysisResult
        from battery_agent.models.report import ComparisonResult, NormalizedCompanyAnalysis, ReferenceResult

        lg_analysis = CompanyAnalysisResult(
            company="LG에너지솔루션",
            strategy_summary="lg summary",
            strengths=["strength"],
            risks=["risk"],
            citations=["doc-1"],
            analysis_notes="done",
            next_action="comparison",
            partial=False,
        )
        catl_analysis = CompanyAnalysisResult(
            company="CATL",
            strategy_summary="catl summary",
            strengths=["strength"],
            risks=["risk"],
            citations=["doc-2"],
            analysis_notes="done",
            next_action="comparison",
            partial=False,
        )
        comparison = ComparisonResult(
            normalized_companies=[
                NormalizedCompanyAnalysis(
                    company="LG에너지솔루션",
                    strategy_summary="lg summary",
                    strengths=["strength"],
                    risks=["risk"],
                    citations=["doc-1"],
                    partial=False,
                ),
                NormalizedCompanyAnalysis(
                    company="CATL",
                    strategy_summary="catl summary",
                    strengths=["strength"],
                    risks=["risk"],
                    citations=["doc-2"],
                    partial=False,
                ),
            ],
            strategy_differences=["difference"],
            strengths_weaknesses=["comparison"],
            swot=["swot"],
            insights=["insight"],
            refinement_requests=[],
            next_action="reference",
        )

        report = build_report(
            topic="배터리 시장 전략 비교",
            lg_analysis=lg_analysis,
            catl_analysis=catl_analysis,
            comparison=comparison,
            references=ReferenceResult(entries=[]),
        )

        self.assertTrue(report.partial)
        self.assertIn("PARTIAL REPORT", report.markdown)
        self.assertIn("FAILURE NOTICE", report.markdown)
