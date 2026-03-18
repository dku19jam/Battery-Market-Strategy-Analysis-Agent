import tempfile
import unittest
from pathlib import Path


class MarkdownRendererTest(unittest.TestCase):
    def test_summary_is_first_reference_is_last_and_summary_is_trimmed(self) -> None:
        from battery_agent.reporting.markdown_renderer import (
            REQUIRED_SECTIONS,
            render_report_markdown,
            save_report_markdown,
        )

        sections = {
            "SUMMARY": "a" * 800,
            "MARKET_BACKGROUND": "market",
            "LG_STRATEGY": "lg",
            "CATL_STRATEGY": "catl",
            "STRATEGY_COMPARISON": "comparison",
            "SWOT": "swot",
            "INSIGHTS": "insight",
            "REFERENCE": "- ref 1",
        }
        markdown = render_report_markdown(
            title="Battery Report",
            sections=sections,
            partial=False,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "report.md"
            save_report_markdown(path, markdown)
            written = path.read_text(encoding="utf-8")

        self.assertEqual(REQUIRED_SECTIONS[0], "SUMMARY")
        self.assertEqual(REQUIRED_SECTIONS[-1], "REFERENCE")
        self.assertTrue(written.index("## 요약") < written.index("## 시장 배경"))
        self.assertTrue(written.index("## 참고자료") > written.index("## 핵심 시사점"))
        self.assertLess(written.count("a"), 1201)
