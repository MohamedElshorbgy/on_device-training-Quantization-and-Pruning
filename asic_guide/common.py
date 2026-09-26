"""Shared helpers for the ASIC design guide (gen_asic_guide_pdf.py).

Same layout engine and helpers as the RTL guide (rtl_guide/common.py), with
this book's running header and title.
"""

from rtl_guide.common import *  # noqa: F401,F403
from rtl_guide.common import G, build as _build

G.HEADER_TEXT = "ASIC Design - The Complete Guide: From Specification to Silicon"
G.FOOTER_TEXT = "Beginner to Expert"

TITLE = "ASIC Design - The Complete Guide: From Specification to Silicon"


def build(output, funcs, title=TITLE):
    _build(output, funcs, title=title,
           subject="A beginner-to-expert guide to the complete ASIC design "
                   "flow, from specification and architecture through "
                   "synthesis, timing, test, physical design, sign-off, "
                   "tapeout, packaging, manufacturing test and bring-up",
           creator="gen_asic_guide_pdf.py")
