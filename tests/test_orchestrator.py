import json
import tempfile
import unittest
from pathlib import Path


class OrchestratorTest(unittest.TestCase):
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
