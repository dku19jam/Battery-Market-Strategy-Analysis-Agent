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
                    source="한국은행",
                    title="2024 금융안정 보고서",
                    topics=["strategy"],
                    score=0.9,
                ),
                EvidenceItem(
                    document_id="lg-paper",
                    snippet="paper evidence",
                    source_type="paper",
                    source="김철수",
                    title="AI 투자 전망",
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
                    source="IEA",
                    title="IEA 배터리 동향",
                    url="https://www.iea.org/reports/battery",
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
        self.assertIn("한국은행", result.entries[0].formatted_reference)
        self.assertIn("IEA", result.entries[1].formatted_reference)
        self.assertIn("https://www.iea.org/reports/battery", result.entries[1].formatted_reference)

    def test_build_references_prioritizes_and_filters_low_quality_entries(self) -> None:
        from battery_agent.agents.references import build_references
        from battery_agent.models.analysis import CompanyAnalysisResult
        from battery_agent.models.evidence import EvidenceBundle, EvidenceItem
        from battery_agent.models.report import ComparisonResult, NormalizedCompanyAnalysis

        lg_bundle = EvidenceBundle(
            company="LG에너지솔루션",
            topics=["strategy"],
            entries=[
                EvidenceItem(
                    document_id="high-trust",
                    snippet="preferred source with detailed strategic content",
                    source_type="web",
                    source="fitchratings.com",
                    title="Preferred strategic document",
                    url="https://fitchratings.com/research",
                    topics=["strategy"],
                    score=0.7,
                ),
                EvidenceItem(
                    document_id="low-trust",
                    snippet="short note",
                    source_type="web",
                    source="blog.naver.com",
                    title="Noisy source document",
                    url="https://blog.naver.com/noisy",
                    topics=["strategy"],
                    score=0.7,
                ),
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
            citations=["high-trust", "low-trust"],
            analysis_notes="done",
            next_action="comparison",
            partial=False,
        )
        catl_analysis = CompanyAnalysisResult(
            company="CATL",
            strategy_summary="summary",
            strengths=["strength"],
            risks=["risk"],
            citations=["low-trust"],
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
                    citations=["high-trust", "low-trust"],
                    partial=False,
                ),
                NormalizedCompanyAnalysis(
                    company="CATL",
                    strategy_summary="summary",
                    strengths=["strength"],
                    risks=["risk"],
                    citations=["low-trust"],
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
            evidence_bundles=[lg_bundle],
            analyses=[lg_analysis, catl_analysis],
            comparison=comparison,
        )

        self.assertEqual(len(result.entries), 1)
        self.assertIn("fitchratings.com", result.entries[0].formatted_reference)

    def test_reference_block_groups_by_source_type(self) -> None:
        from battery_agent.agents.references import ReferenceEntry, format_reference_block

        block = format_reference_block(
            [
                ReferenceEntry(document_id="d1", source_type="web", formatted_reference="IEA(2024). IEA. https://iea.org"),
                ReferenceEntry(document_id="d2", source_type="report", formatted_reference="한국은행(2024). 2024 금융안정 보고서."),
                ReferenceEntry(document_id="d3", source_type="paper", formatted_reference="김철수(2024). 인공지능 산업 전망."),
            ]
        )

        self.assertIn("### 기관 보고서", block)
        self.assertIn("### 학술 논문", block)
        self.assertIn("### 웹페이지", block)
        self.assertIn("◦ 한국은행(2024). 2024 금융안정 보고서.", block)

    def test_reference_block_treats_pdf_as_report(self) -> None:
        from battery_agent.agents.references import ReferenceEntry, format_reference_block

        block = format_reference_block(
            [
                ReferenceEntry(
                    document_id="catl-doc",
                    source_type="pdf",
                    formatted_reference="CATL(2025). 2025 분기 보고서. CATL_2025_Q1",
                )
            ]
        )

        self.assertIn("### 기관 보고서", block)
        self.assertNotIn("### pdf", block)
        self.assertIn("◦ CATL(2025). 2025 분기 보고서. CATL_2025_Q1", block)
