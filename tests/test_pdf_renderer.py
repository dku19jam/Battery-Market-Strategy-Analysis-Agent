import tempfile
import unittest
from pathlib import Path


class PdfRendererTest(unittest.TestCase):
    def test_pdf_renderer_supports_markdown_text(self) -> None:
        from battery_agent.reporting.pdf_renderer import render_pdf_report

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "report.pdf"
            result = render_pdf_report("# 제목\n\n한글 보고서", output_path)
            pdf_bytes = output_path.read_bytes()

        self.assertTrue(result.success)
        self.assertTrue(output_path.name.endswith(".pdf"))
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_pdf_renderer_supports_markdown_file(self) -> None:
        from battery_agent.reporting.pdf_renderer import render_pdf_report

        with tempfile.TemporaryDirectory() as tmp_dir:
            markdown_path = Path(tmp_dir) / "report.md"
            markdown_path.write_text("# 제목\n\n한글 보고서", encoding="utf-8")
            output_path = Path(tmp_dir) / "report.pdf"

            result = render_pdf_report(markdown_path, output_path)
            pdf_bytes = output_path.read_bytes()

        self.assertTrue(result.success)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
