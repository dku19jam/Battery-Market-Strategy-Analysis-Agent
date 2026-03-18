import unittest


class ReferenceFormattingTest(unittest.TestCase):
    def test_reference_agent_formats_only_used_sources(self) -> None:
        from battery_agent.agents.references import build_references
        from battery_agent.models.analysis import CompanyAnalysisResult
        from battery_agent.models.evidence import EvidenceBundle, EvidenceItem
        from battery_agent.models.report import ComparisonResult, NormalizedCompanyAnalysis

        lg_bundle = EvidenceBundle(
            company="LG에너지솔루션",
            topics=["strategy"],
            entries=[
                EvidenceItem(
                    document_id="lg-report",
                    snippet="report evidence",
                    source_type="report",
                    source="LGES IR",
                    topics=["strategy"],
                    score=0.9,
                ),
                EvidenceItem(
                    document_id="lg-paper",
                    snippet="paper evidence",
                    source_type="paper",
                    source="Journal of Batteries",
                    topics=["strategy"],
                    score=0.8,
                ),
            ],
            topic_buckets={},
            missing_topics=[],
            next_action="analysis",
        )
        catl_bundle = EvidenceBundle(
            company="CATL",
            topics=["strategy"],
            entries=[
                EvidenceItem(
                    document_id="catl-web",
                    snippet="web evidence",
                    source_type="web",
                    source="example.com",
                    topics=["strategy"],
                    score=0.7,
                )
            ],
            topic_buckets={},
            missing_topics=[],
            next_action="analysis",
        )
        lg_analysis = CompanyAnalysisResult(
            company="LG에너지솔루션",
            strategy_summary="summary",
            strengths=["strength"],
            risks=["risk"],
            citations=["lg-report"],
            analysis_notes="done",
            next_action="comparison",
            partial=False,
        )
        catl_analysis = CompanyAnalysisResult(
            company="CATL",
            strategy_summary="summary",
            strengths=["strength"],
            risks=["risk"],
            citations=["catl-web"],
            analysis_notes="done",
            next_action="comparison",
            partial=False,
        )
        comparison = ComparisonResult(
            normalized_companies=[
                NormalizedCompanyAnalysis(
                    company="LG에너지솔루션",
                    strategy_summary="summary",
                    strengths=["strength"],
                    risks=["risk"],
                    citations=["lg-report"],
                    partial=False,
                ),
                NormalizedCompanyAnalysis(
                    company="CATL",
                    strategy_summary="summary",
                    strengths=["strength"],
                    risks=["risk"],
                    citations=["catl-web"],
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

        result = build_references(
            evidence_bundles=[lg_bundle, catl_bundle],
            analyses=[lg_analysis, catl_analysis],
            comparison=comparison,
        )

        self.assertEqual(result.next_action, "report_generation")
        self.assertEqual(len(result.entries), 2)
        self.assertIn("LGES IR", result.entries[0].formatted_reference)
        self.assertIn("https://example.com", result.entries[1].formatted_reference)
