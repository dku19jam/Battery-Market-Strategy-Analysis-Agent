import tempfile
import unittest
from pathlib import Path


class EndToEndDryRunTest(unittest.TestCase):
    def test_cli_dry_run_with_sample_corpus_generates_all_outputs(self) -> None:
        from battery_agent.cli import main
        from battery_agent.config import Settings

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
                        "citations": ["lg-001" if "LG" in user_prompt else "catl-001"],
                        "analysis_notes": "done",
                    }
                if schema_name == "final_report_sections":
                    return {
                        "summary": "근거가 다소 제한적이지만 현재 확보된 자료 기준 핵심 전략을 한국어로 요약한다.",
                        "market_background": "배터리 시장 환경과 비교 목적을 설명한다.",
                        "lg_strategy": "LG 전략 상세 설명이다.",
                        "catl_strategy": "CATL 전략 상세 설명이다.",
                        "strategy_comparison": "두 회사 전략 차이를 상세히 설명한다.",
                        "swot": "SWOT을 종합 정리한다.",
                        "insights": "실무 시사점을 정리한다.",
                    }
                return {
                    "normalized_companies": [],
                    "strategy_differences": ["차이점"],
                    "strengths_weaknesses": ["강점/약점"],
                    "swot": ["SWOT"],
                    "insights": ["시사점"],
                    "refinement_requests": [],
                }

        fixtures_dir = Path(__file__).parent / "fixtures" / "sample_corpus"
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = Settings(
                openai_api_key="test-key",
                default_companies=("LG에너지솔루션", "CATL"),
                default_model="gpt-4o-mini",
                embedding_model_id="Qwen/Qwen3-Embedding-0.6B",
                default_topic="배터리 시장 전략 비교",
                local_corpus_dir=fixtures_dir,
                output_root=Path(tmp_dir) / "artifacts",
                tavily_api_key=None,
                web_search_enabled=False,
                web_search_max_calls=3,
                web_search_max_results=5,
            )

            from unittest.mock import patch

            with patch("battery_agent.cli.Settings.from_env", return_value=settings), patch(
                "battery_agent.cli.StructuredOpenAIClient",
                return_value=FakeStructuredLlm(),
            ):
                exit_code = main(["--run-id", "e2e-run", "--topic", "배터리 시장 전략 비교"])

            run_root = Path(tmp_dir) / "artifacts" / "e2e-run"
            markdown_exists = (run_root / "reports" / "final_report.md").exists()
            pdf_exists = (run_root / "reports" / "final_report.pdf").exists()
            retrieval_exists = (run_root / "retrieval" / "lg_retrieval.json").exists()

        self.assertEqual(exit_code, 0)
        self.assertTrue(markdown_exists)
        self.assertTrue(pdf_exists)
        self.assertTrue(retrieval_exists)
