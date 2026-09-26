"""Shared helpers for the RTL guide (gen_rtl_guide_pdf.py).

Reuses the layout engine of gen_ml_dl_guide_pdf.py and adds `out()` for
simulator output captured from Icarus Verilog.
"""

import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import gen_ml_dl_guide_pdf as G
from gen_ml_dl_guide_pdf import (  # noqa: F401  (re-exported for the parts)
    add, p, h2, h3, bul, code, eq, box, tbl, diagram, checklist, chapter,
    part, pb, sp, mk, xe, appendix, ah2,
    Paragraph, Table, TableStyle, Spacer, PageBreak, HRFlowable, KeepTogether,
    TableOfContents, colors, mm, CONTENT_W,
    C_DARK, C_MID, C_LGREY, S_TITLE, S_SUBTITLE, S_H1, S_TD, S_TDB, S_CAP,
    S_TOC1, S_TOC2, S_TOC3, _ps,
)

from reportlab.platypus import CondPageBreak


def h2(title):
    """Numbered section heading that never sits alone at a page bottom."""
    add(CondPageBreak(32 * mm))
    G.h2(title)


def h3(title):
    add(CondPageBreak(22 * mm))
    G.h3(title)


def ah2(title):
    add(CondPageBreak(32 * mm))
    G.ah2(title)


def appendix(title):
    """Appendix heading; avoids a blank page right after the divider."""
    if G.STORY and isinstance(G.STORY[-1], PageBreak):
        G.STORY.pop()
    G.appendix(title)


G.HEADER_TEXT = "RTL Design for SoC & ASIC - The Complete Guide"
G.FOOTER_TEXT = "Beginner to Expert"

S_OUT = _ps("OUT", fontSize=8.0, leading=10.6, fontName="Courier",
            textColor=colors.HexColor("#14532d"))


def out(lines, caption=None):
    """Render captured simulator output on a green card below a testbench."""
    if isinstance(lines, str):
        lines = lines.split("\n")
    rows = [[Paragraph(xe(l).replace(" ", "&nbsp;") or "&nbsp;", S_OUT)]
            for l in lines]
    t = Table(rows, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f8f2")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#2e7d32")),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, colors.HexColor("#2e7d32")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 0.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.6),
    ]))
    tail = Paragraph(mk(caption), S_CAP) if caption else Spacer(1, 6)
    items = [Spacer(1, 2), t, tail]
    if len(rows) <= 16:
        add(KeepTogether(items))
    else:
        add(*items)


def build(output, funcs, title="RTL Design for SoC & ASIC - The Complete Guide"):
    """Run the given part functions and write the PDF (used for smoke tests
    of a single part as well as for the full book)."""
    for f in funcs:
        f()
    doc = G.Book(output, title=title, author="Generated with Claude Code",
                 subject="A beginner-to-expert guide to RTL design for SoC "
                         "and ASIC development",
                 creator="gen_rtl_guide_pdf.py")
    doc.multiBuild(G.STORY)
    print("Wrote %s (%.0f KB)" % (output, os.path.getsize(output) / 1024.0))
