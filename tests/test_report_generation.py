import unittest


class ReportGenerationTest(unittest.TestCase):
    def test_build_report_uses_llm_generated_korean_sections(self) -> None:
        from battery_agent.agents.report_generation import build_report
        from battery_agent.models.analysis import CompanyAnalysisResult
        from battery_agent.models.report import (
            ComparisonResult,
            NormalizedCompanyAnalysis,
            ReferenceEntry,
            ReferenceResult,
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
                    "swot": "LG에너지솔루션은 기술 포트폴리오가 강점이고, CATL은 시장 지배력과 공급망 통합이 강점이다. 두 회사 모두 경쟁 심화와 기술 전환 리스크를 안고 있다.",
                    "insights": "최종 보고서만 읽어도 의사결정자가 이해할 수 있도록 핵심 전략과 차이를 정리하면, LG에너지솔루션은 선택과 집중, CATL은 확장과 지배력 강화로 요약된다.",
                }

        lg_analysis = CompanyAnalysisResult(
            company="LG에너지솔루션",
            strategy_summary="lg summary",
            strengths=["strength"],
            risks=["risk"],
            citations=["doc-1"],
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
            swot=["swot"],
            insights=["insight"],
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
        self.assertIn("SUMMARY", report.markdown)
        self.assertIn("근거가 다소 제한적", report.markdown)
        self.assertIn("최종 보고서만 읽어도", report.markdown)

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
