"""Shared helpers for the Verilog & SystemVerilog guide (gen_sv_guide_pdf.py).

Same layout engine and helpers as the RTL guide (rtl_guide/common.py), with
this book's running header and title.
"""

from rtl_guide.common import *  # noqa: F401,F403
from rtl_guide.common import G, build as _build

G.HEADER_TEXT = "Verilog & SystemVerilog for SoC & ASIC - The Complete Guide"
G.FOOTER_TEXT = "Beginner to Expert"

TITLE = "Verilog & SystemVerilog for SoC & ASIC - The Complete Guide"


def build(output, funcs, title=TITLE):
    _build(output, funcs, title=title,
           subject="A beginner-to-expert guide to the Verilog and "
                   "SystemVerilog languages for SoC and ASIC work",
           creator="gen_sv_guide_pdf.py")
