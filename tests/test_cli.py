import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class CLITest(unittest.TestCase):
    def test_main_prints_stub_message(self) -> None:
        from battery_agent.cli import main

        stdout = io.StringIO()
        fake_state = SimpleNamespace(
            status="completed",
            report_artifact=SimpleNamespace(
                markdown_path="artifacts/run-001/reports/final_report.md",
                pdf_path="artifacts/run-001/reports/final_report.pdf",
            ),
        )
        with patch("battery_agent.cli.run_analysis_workflow", return_value=fake_state), redirect_stdout(stdout):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        self.assertIn("battery-agent", stdout.getvalue())

    def test_main_writes_run_log_file(self) -> None:
        from battery_agent.cli import main
        from battery_agent.config import Settings

        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = Settings(
                openai_api_key="test-key",
                default_companies=("LG에너지솔루션", "CATL"),
                default_model="gpt-4o-mini",
                embedding_model_id="Qwen/Qwen3-Embedding-0.6B",
                default_topic="배터리 시장 전략 비교",
                local_corpus_dir=Path("corpus"),
                output_root=Path(tmp_dir),
                tavily_api_key=None,
                web_search_enabled=False,
                web_search_max_calls=3,
                web_search_max_results=5,
            )
            fake_state = SimpleNamespace(
                status="completed",
                report_artifact=SimpleNamespace(
                    markdown_path=str(Path(tmp_dir) / "run-001" / "reports" / "final_report.md"),
                    pdf_path=str(Path(tmp_dir) / "run-001" / "reports" / "final_report.pdf"),
                ),
            )
            log_path = Path(tmp_dir) / "run-001" / "logs" / "run.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text("seed", encoding="utf-8")
            with patch("battery_agent.cli.Settings.from_env", return_value=settings), patch(
                "battery_agent.cli.run_analysis_workflow",
                return_value=fake_state,
            ):
                exit_code = main(["--run-id", "run-001"])

            log_exists = log_path.exists()

        self.assertEqual(exit_code, 0)
        self.assertTrue(log_exists)
