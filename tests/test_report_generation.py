import unittest


class ReportGenerationTest(unittest.TestCase):
    def test_build_report_uses_llm_generated_korean_sections(self) -> None:
        from battery_agent.agents.report_generation import build_report
        from battery_agent.models.analysis import AnalysisMetric, CompanyAnalysisResult
        from battery_agent.models.report import (
            CompanyMetric,
            ComparisonResult,
            NormalizedCompanyAnalysis,
            ReferenceEntry,
            ReferenceResult,
            SWOTSection,
        )

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
                    }
                )
                return {
                    "summary": "근거가 다소 제한적이지만 현재 확보된 자료 기준으로 LG에너지솔루션은 북미 중심 고수익 포트폴리오, CATL은 글로벌 대량 공급과 파트너십 우위를 보인다.",
                    "market_background": "전기차 수요 둔화와 ESS 확대, 공급망 재편이 동시에 진행되는 구간이다.",
                    "lg_strategy": "LG에너지솔루션은 북미 시장 대응, 고수익 제품 비중 확대, 차세대 전지 기술 투자에 집중하고 있다.",
                    "catl_strategy": "CATL은 LFP와 ESS를 포함한 폭넓은 포트폴리오와 글로벌 고객 네트워크를 활용해 점유율을 확대하고 있다.",
                    "strategy_comparison": "LG에너지솔루션은 수익성 중심 재편이 강하고, CATL은 규모와 고객 저변 확대 전략이 더 강하다.",
                    "swot": "### Strengths\n- LG에너지솔루션은 북미 대응력과 기술 포트폴리오가 강점이다.\n- CATL은 시장 지배력과 공급망 통합이 강점이다.\n\n### Weaknesses\n- LG에너지솔루션은 수익성 변동성이 약점이다.\n- CATL은 지정학 리스크 노출이 약점이다.\n\n### Opportunities\n- ESS 확대와 북미 현지화 수요는 기회다.\n\n### Threats\n- 가격 경쟁 심화와 기술 전환 속도는 위협이다.",
                    "company_metrics": "| 회사 | 지표 | 값 | 출처 |\n| --- | --- | --- | --- |\n| LG에너지솔루션 | 매출 | 25.6조원 | 2024 사업보고서 |\n| CATL | 시장점유율 | 27.0% | 2024 Annual Report |",
                    "insights": "최종 보고서만 읽어도 의사결정자가 이해할 수 있도록 핵심 전략과 차이를 정리하면, LG에너지솔루션은 선택과 집중, CATL은 확장과 지배력 강화로 요약된다.",
                }

        lg_analysis = CompanyAnalysisResult(
            company="LG에너지솔루션",
            strategy_summary="lg summary",
            strengths=["strength"],
            risks=["risk"],
            citations=["doc-1"],
            metrics=[AnalysisMetric(metric="매출", value="25.6조원", source_hint="2024 사업보고서")],
            analysis_notes="done",
            next_action="comparison",
            partial=True,
        )
        catl_analysis = CompanyAnalysisResult(
            company="CATL",
            strategy_summary="catl summary",
            strengths=["strength"],
            risks=["risk"],
            citations=["doc-2"],
            metrics=[AnalysisMetric(metric="시장점유율", value="27.0%", source_hint="2024 Annual Report")],
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
                    partial=True,
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
            swot=SWOTSection(
                strengths=["strength"],
                weaknesses=["weakness"],
                opportunities=["opportunity"],
                threats=["threat"],
            ),
            insights=["insight"],
            company_metrics=[
                CompanyMetric(
                    company="LG에너지솔루션",
                    metric="매출",
                    value="25.6조원",
                    source_hint="2024 사업보고서",
                ),
                CompanyMetric(
                    company="CATL",
                    metric="시장점유율",
                    value="27.0%",
                    source_hint="2024 Annual Report",
                ),
            ],
            refinement_requests=[],
            next_action="reference",
        )
        references = ReferenceResult(
            entries=[
                ReferenceEntry(
                    document_id="doc-1",
                    source_type="web",
                    formatted_reference="https://example.com/doc-1. https://example.com",
                )
            ]
        )
        fake_llm = FakeStructuredLlm()

        report = build_report(
            topic="배터리 시장 전략 비교",
            lg_analysis=lg_analysis,
            catl_analysis=catl_analysis,
            comparison=comparison,
            references=references,
            llm_client=fake_llm,
            model="gpt-4o-mini",
        )

        self.assertEqual(len(fake_llm.calls), 1)
        self.assertEqual(fake_llm.calls[0]["schema_name"], "final_report_sections")
        self.assertIn("반드시 결과물을 한국어로", str(fake_llm.calls[0]["system_prompt"]))
        self.assertIn("SWOT은 반드시 Strengths, Weaknesses, Opportunities, Threats", str(fake_llm.calls[0]["system_prompt"]))
        self.assertIn("Markdown 표 형식", str(fake_llm.calls[0]["system_prompt"]))
        self.assertIn("SUMMARY", report.markdown)
        self.assertIn("근거가 다소 제한적", report.markdown)
        self.assertIn("최종 보고서만 읽어도", report.markdown)
        self.assertIn("## COMPANY_METRICS", report.markdown)
        self.assertIn("| 회사 | 지표 | 값 | 출처 |", report.markdown)
        self.assertIn("### Strengths", report.markdown)

    def test_build_report_marks_partial_when_references_are_missing(self) -> None:
        from battery_agent.agents.report_generation import build_report
        from battery_agent.models.analysis import CompanyAnalysisResult
        from battery_agent.models.report import (
            ComparisonResult,
            NormalizedCompanyAnalysis,
            ReferenceResult,
            SWOTSection,
        )

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
            swot=SWOTSection(
                strengths=["strength"],
                weaknesses=["weakness"],
                opportunities=["opportunity"],
                threats=["threat"],
            ),
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

    def test_build_report_uses_structured_swot_and_metrics_fallback_when_llm_returns_jsonish_text(self) -> None:
        from battery_agent.agents.report_generation import build_report
        from battery_agent.models.analysis import AnalysisMetric, CompanyAnalysisResult
        from battery_agent.models.report import (
            CompanyMetric,
            ComparisonResult,
            NormalizedCompanyAnalysis,
            ReferenceEntry,
            ReferenceResult,
            SWOTSection,
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
                    "summary": "근거가 다소 제한적이지만 핵심 차이를 정리한다.",
                    "market_background": "시장 배경 설명",
                    "lg_strategy": "LG 전략 설명",
                    "catl_strategy": "CATL 전략 설명",
                    "strategy_comparison": "전략 비교 설명",
                    "swot": ': {"strengths":["raw"],"weaknesses":["raw"],"opportunities":["raw"],"threats":["raw"]}',
                    "company_metrics": "",
                    "insights": "시사점 설명",
                }

        lg_analysis = CompanyAnalysisResult(
            company="LG에너지솔루션",
            strategy_summary="lg summary",
            strengths=["strength"],
            risks=["risk"],
            citations=["doc-1"],
            metrics=[AnalysisMetric(metric="매출", value="25.6조원", source_hint="2024 사업보고서")],
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
            metrics=[AnalysisMetric(metric="시장점유율", value="27.0%", source_hint="2024 Annual Report")],
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
                    metrics=[{"metric": "매출", "value": "25.6조원", "source_hint": "2024 사업보고서"}],
                    partial=False,
                ),
                NormalizedCompanyAnalysis(
                    company="CATL",
                    strategy_summary="catl summary",
                    strengths=["strength"],
                    risks=["risk"],
                    citations=["doc-2"],
                    metrics=[{"metric": "시장점유율", "value": "27.0%", "source_hint": "2024 Annual Report"}],
                    partial=False,
                ),
            ],
            strategy_differences=["difference"],
            strengths_weaknesses=["comparison"],
            swot=SWOTSection(
                strengths=["LG 강점"],
                weaknesses=["LG 약점"],
                opportunities=["공통 기회"],
                threats=["공통 위협"],
            ),
            insights=["insight"],
            company_metrics=[
                CompanyMetric(
                    company="LG에너지솔루션",
                    metric="매출",
                    value="25.6조원",
                    source_hint="2024 사업보고서",
                )
            ],
            refinement_requests=[],
            next_action="reference",
        )
        references = ReferenceResult(
            entries=[
                ReferenceEntry(
                    document_id="doc-1",
                    source_type="web",
                    formatted_reference="https://example.com/doc-1. https://example.com",
                )
            ]
        )

        report = build_report(
            topic="배터리 시장 전략 비교",
            lg_analysis=lg_analysis,
            catl_analysis=catl_analysis,
            comparison=comparison,
            references=references,
            llm_client=FakeStructuredLlm(),
            model="gpt-4o-mini",
        )

        self.assertIn("### Strengths", report.markdown)
        self.assertIn("- LG 강점", report.markdown)
        self.assertIn("| LG에너지솔루션 | 매출 | 25.6조원 | 2024 사업보고서 |", report.markdown)
        self.assertNotIn(': {"strengths"', report.markdown)
