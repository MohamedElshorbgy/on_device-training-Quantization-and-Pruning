"""Shared helpers for the communication-protocols guide (gen_proto_guide_pdf.py).

Same layout engine and helpers as the RTL guide (rtl_guide/common.py), with
this book's running header and title.
"""

from rtl_guide.common import *  # noqa: F401,F403
from rtl_guide.common import G, build as _build

G.HEADER_TEXT = "Communication Protocols for SoC & ASIC - The Complete Guide"
G.FOOTER_TEXT = "Beginner to Expert"

TITLE = "Communication Protocols for SoC & ASIC - The Complete Guide"


def build(output, funcs, title=TITLE):
    _build(output, funcs, title=title,
           subject="A beginner-to-expert guide to the on-chip, peripheral, "
                   "high-speed, memory and debug protocols of SoC and ASIC "
                   "design",
           creator="gen_proto_guide_pdf.py")
