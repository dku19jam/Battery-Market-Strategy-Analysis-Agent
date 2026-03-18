"""Minimal PDF rendering helper."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PdfRenderResult:
    success: bool
    warning: str | None = None


def render_pdf_report(markdown: str | Path, output_path: Path) -> PdfRenderResult:
    markdown_path: Path | None = None
    if isinstance(markdown, Path):
        markdown_path = markdown
    elif isinstance(markdown, str) and Path(markdown).exists():
        markdown_path = Path(markdown)
    markdown_text = markdown_path.read_text(encoding="utf-8") if markdown_path is not None else str(markdown)
    warning: str | None = None

    try:
        import markdown as md_lib  # type: ignore
        from weasyprint import HTML  # type: ignore

        body_html = md_lib.markdown(
            markdown_text,
            extensions=["extra", "sane_lists", "nl2br"],
            output_format="html5",
        )
        html = (
            "<!doctype html><html><head><meta charset='utf-8'></head>"
            "<body style='font-family: sans-serif; font-size: 12px; line-height: 1.4; margin: 24px;'>"
            f"{body_html}"
            "</body></html>"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        HTML(string=html).write_pdf(str(output_path))
        return PdfRenderResult(success=True, warning=warning)
    except Exception:
        warning = "External PDF renderer unavailable; fallback PDF writing was used."
        _write_fallback_pdf(markdown_text, output_path)
        return PdfRenderResult(
            success=True,
            warning=warning,
        )


def _write_fallback_pdf(markdown: str, output_path: Path) -> None:
    sanitized = (
        markdown.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )
    content = f"BT /F1 10 Tf 40 760 Td ({sanitized[:2000]}) Tj ET".encode("latin-1")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n",
        b"4 0 obj << /Length " + str(len(content)).encode("ascii") + b" >> stream\n" + content + b"\nendstream endobj\n",
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode(
            "ascii"
        )
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(bytes(pdf))
