"""Render a findings markdown file to PDF.

    python -m scripts.findings_to_pdf ../PENTEST_FINDINGS.md ../PENTEST_FINDINGS.pdf

Kept as a script rather than a one-off so the PDF can be regenerated whenever the
findings change, instead of drifting out of sync with the markdown it came from.
"""
from __future__ import annotations

import sys
from pathlib import Path

from markdown_pdf import MarkdownPdf, Section

CSS = """
body { font-family: Georgia, 'Times New Roman', serif; line-height: 1.55; color: #1a1a1a; }
h1 { color: #14532d; border-bottom: 3px solid #14532d; padding-bottom: 5px; font-size: 1.6em; }
h2 { color: #166534; margin-top: 1.5em; font-size: 1.25em; }
h3 { color: #111827; background: #f3f4f6; padding: 5px 9px;
     border-left: 4px solid #16a34a; font-size: 1.02em; }
blockquote { background: #fefce8; border-left: 4px solid #ca8a04;
             padding: 7px 13px; margin: 11px 0; }
table { border-collapse: collapse; width: 100%; font-size: 0.86em; }
th, td { border: 1px solid #d1d5db; padding: 5px 8px; text-align: left; vertical-align: top; }
th { background: #f3f4f6; }
code { background: #f1f5f9; padding: 1px 3px; font-size: 0.88em; }
pre { background: #f8fafc; border: 1px solid #e2e8f0; padding: 9px; font-size: 0.78em; }
hr { border: none; border-top: 1px solid #e5e7eb; margin: 18px 0; }
"""


def main() -> None:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "PENTEST_FINDINGS.md")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else src.with_suffix(".pdf"))

    text = src.read_text(encoding="utf-8")

    # One Section per top-level part, so each starts on a fresh page.
    chunks: list[str] = []
    current: list[str] = []
    for line in text.split("\n"):
        if line.startswith("# ") and current:
            chunks.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        chunks.append("\n".join(current))

    pdf = MarkdownPdf(toc_level=2, optimize=True)
    for chunk in chunks:
        pdf.add_section(Section(chunk, toc=True), user_css=CSS)

    pdf.meta["title"] = "DataSport — adversarial analyst audit"
    pdf.meta["author"] = "DataSport"
    pdf.save(str(out))
    print(f"wrote {out} ({out.stat().st_size:,} bytes, {len(chunks)} sections)")


if __name__ == "__main__":
    main()
