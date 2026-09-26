"""
ASIC Design - The Complete Guide: From Specification to Silicon
===============================================================
Generates a single, detailed, self-contained PDF textbook covering every topic
of ASIC design: the business and the end-to-end flow; MOSFET and CMOS device
fundamentals; process technology, PDKs and variation; standard cells, Liberty,
LEF, memories and IP; specification and architecture; front-end design (RTL for
ASIC, verification strategy, logic synthesis, static timing analysis, design
for test); low power and UPF; analog/mixed-signal, I/O and ESD integration;
the whole physical-design flow (design planning, floorplan and power grid,
placement, clock tree synthesis, routing, SI and DFM); sign-off (timing, IR/EM,
reliability, DRC/LVS/ERC/antenna, LEC); ECOs, tapeout and mask making;
packaging, 2.5D/3D and chiplets; manufacturing test, yield and reliability;
bring-up, characterisation and qualification; methodology and economics; the
open-source flow; a worked RTL-to-GDSII case study; and a career roadmap.

Where an open-source tool could demonstrate a step (Yosys synthesis against the
real SkyWater SKY130 standard-cell library, Icarus Verilog / Verilator
simulation, Python models of device, timing, power, IR drop, placement, routing,
yield and cost), it was run and the output on green cards is the real output.

Fourth book of the series, with gen_rtl_guide_pdf.py, gen_sv_guide_pdf.py and
gen_proto_guide_pdf.py; the chapters live in the asic_guide/ package.

Usage:
    pip install reportlab
    python gen_asic_guide_pdf.py

Output:
    ASIC_Design_Complete_Guide.pdf
"""

import os

from asic_guide.common import (
    add, p, h3, bul, box, tbl, pb, mk, build,
    Paragraph, Table, TableStyle, Spacer, HRFlowable, TableOfContents,
    colors, mm, CONTENT_W, C_DARK, C_MID, C_LGREY, S_TITLE, S_SUBTITLE, S_H1,
    S_TD, S_TDB, S_TOC1, S_TOC2, S_TOC3,
)
from asic_guide.part1 import part1
from asic_guide.part2 import part2
from asic_guide.part3 import part3
from asic_guide.part4 import part4
from asic_guide.part5 import part5
from asic_guide.part6 import part6
from asic_guide.appx import appendices

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(
    HERE, "ASIC_Design_Complete_Guide.pdf")


def _banner(text):
    t = Table([[Paragraph(text, S_H1)]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
    add(t, Spacer(1, 8))


# =============================================================================
#                               FRONT MATTER
# =============================================================================
def front_matter():
    add(Spacer(1, 34 * mm))
    add(Paragraph("ASIC Design", S_TITLE))
    add(Spacer(1, 2))
    add(Paragraph("From Specification to Silicon", S_SUBTITLE))
    add(Spacer(1, 4))
    add(HRFlowable(width="45%", thickness=2, color=C_MID, spaceAfter=10,
                   hAlign="CENTER"))
    add(Paragraph("The Complete Guide - From Beginner to Expert", S_SUBTITLE))
    add(Spacer(1, 6))
    add(Paragraph("Devices &amp; CMOS &#183; Process &amp; PDKs &#183; Standard "
                  "Cells &amp; Liberty &#183; Architecture &#183; RTL for ASIC "
                  "&#183; Verification &#183; Synthesis &#183; STA &#183; DFT "
                  "&#183; Low Power &amp; UPF &#183; AMS &amp; ESD &#183; "
                  "Floorplan &amp; Power Grid &#183; Placement &#183; CTS "
                  "&#183; Routing &amp; SI &#183; Sign-off &#183; DRC/LVS "
                  "&#183; ECO &#183; Tapeout &#183; Packaging &amp; Chiplets "
                  "&#183; Test &amp; Yield &#183; Reliability &#183; Bring-up "
                  "&#183; Economics &#183; Open-Source Flow", S_SUBTITLE))
    add(Spacer(1, 12 * mm))
    rows = [
        ["Contents", "26 chapters in 6 parts, plus 4 appendices"],
        ["Scope", "The whole life of a chip: business case, device physics "
         "and process, front end, back end, sign-off, tapeout, packaging, "
         "manufacturing test, yield, reliability and bring-up"],
        ["Real numbers", "Synthesis was run with **Yosys** against the real "
         "**SkyWater SKY130** standard-cell library; timing, power, IR drop, "
         "placement, routing, yield and cost were modelled in **Python**. "
         "Green cards show the real output"],
        ["Honest about tools", "Commercial sign-off tools cannot be run here; "
         "any report excerpt that did not come from a real run is labelled "
         "illustrative"],
        ["Series", "Fourth book, with __RTL Design for SoC & ASIC__, "
         "__Verilog & SystemVerilog for SoC & ASIC__ and __Communication "
         "Protocols for SoC & ASIC__ in this repository"],
        ["Assumed", "Basic digital logic. Everything else is built up from "
         "first principles."],
    ]
    t = Table([[Paragraph(mk(a), S_TDB), Paragraph(mk(b), S_TD)] for a, b in rows],
              colWidths=[40 * mm, CONTENT_W - 40 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_LGREY),
        ("BOX", (0, 0), (-1, -1), 0.8, C_MID),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    add(t)
    pb()

    _banner("How To Use This Book")
    p("An **ASIC** - an application-specific integrated circuit - is a chip "
      "built for one job, from a phone's application processor to a network "
      "switch, an automotive controller or an AI accelerator. Designing one "
      "is a relay race run by a dozen specialist teams over one to three "
      "years: architects, RTL designers, verification engineers, DFT, "
      "synthesis and timing, physical design, physical verification, "
      "analog, packaging, test and product engineers. Each team hands the "
      "next a precise set of files, and a mistake at any hand-off can cost a "
      "mask set, a quarter of schedule, or the product.")
    p("This book follows that relay from start to finish. It explains what "
      "each team does and why, the physics and algorithms underneath its "
      "tools, the numbers it works to, the files it hands on, and the "
      "mistakes that reach silicon. The three companion books cover RTL "
      "design, the Verilog and SystemVerilog languages, and communication "
      "protocols in depth; this one covers everything else, and how it all "
      "fits together into a working chip.")

    h3("The six parts")
    tbl(["Part", "Chapters", "What you get out of it"],
        [["I - Foundations", "1-5",
          "The ASIC business and the end-to-end flow; transistors, CMOS, "
          "delay, power and scaling; how chips are manufactured and what a "
          "PDK contains; standard cells, Liberty, LEF, memories and IP; "
          "turning requirements into an architecture and PPA targets."],
         ["II - Front-End Design", "6-10",
          "What the back end needs from RTL; verification strategy and "
          "sign-off; logic synthesis; static timing analysis; design for "
          "test."],
         ["III - Power, AMS and PD Setup", "11-14",
          "Low-power techniques and UPF; analog, I/O and ESD integration; "
          "the physical-design data and flow; floorplanning, the power grid "
          "and the I/O ring."],
         ["IV - Implementation & Sign-off", "15-19",
          "Placement; clock tree synthesis; routing, signal integrity and "
          "DFM; timing, power, reliability and physical-verification "
          "sign-off; ECOs, tapeout and mask making."],
         ["V - After Tapeout", "20-23",
          "Packaging, 2.5D/3D and chiplets; manufacturing test, yield and "
          "reliability; bring-up, characterisation and qualification; "
          "methodology, project management and cost."],
         ["VI - Practice & Roadmap", "24-26",
          "The open-source flow on open PDKs; a complete RTL-to-GDSII case "
          "study; the career roadmap and interview preparation."]],
        widths=[28, 12, 60], bold_first=True)

    h3("Reading paths")
    bul([
        "**Beginner:** read Part I, then Chapters 8, 9, 13 and 25 for a "
        "first complete pass through the flow, then fill in the rest.",
        "**RTL or verification engineer:** 1, 4, 6-11, 13 and 18 - what "
        "happens to your code after you hand it off.",
        "**Aspiring physical-design engineer:** 2-4, 8, 9, then Parts III "
        "and IV in order, then 24-25.",
        "**Test, product or quality engineer:** 3, 10, 20-22.",
        "**Manager or architect:** 1, 5, 19, 21 and 23.",
        "**Interview preparation:** 2, 8, 9, 10, 14-18, then Appendix C.",
    ])

    h3("Conventions")
    tbl(["Style", "Meaning"],
        [["A grey card", "A script, netlist, constraint file, library "
          "excerpt or program, exactly as it was run or written"],
         ["A **green card**", "Real output from Yosys, Icarus Verilog, "
          "Verilator or Python, produced while this book was written"],
         ["\"Illustrative\"", "A report excerpt showing the shape of a "
          "commercial tool's output; not from a real run, and always "
          "labelled so"],
         ["Coloured boxes", "KEY IDEA = the one thing to remember. MATH = an "
          "equation or calculation. INTUITION = the mental picture. PRACTICAL "
          "TIP = what to do. PITFALL = a mistake that reaches silicon. EXPERT "
          "CORNER = depth you can skip on a first read."],
         ["Numbers", "Process and cost figures vary by foundry, node and "
          "year; where they do, they are given as typical values or orders "
          "of magnitude, never as foundry data"]],
        widths=[22, 78], bold_first=True)
    box("tip", "Run a real flow yourself",
        "The open-source SKY130, GF180MCU and IHP SG13G2 PDKs, together with "
        "Yosys, OpenROAD, Magic, KLayout and Netgen, let anyone take a design "
        "from RTL to a manufacturable GDSII on a laptop - and shuttle "
        "programmes have put such designs on real silicon. Chapter 24 shows "
        "how, and Chapter 25 walks a block through every step.")
    box("key", "The one idea that ties the flow together",
        "Every step trades **performance, power and area** (PPA) against "
        "**schedule and risk**, using models that get more accurate as the "
        "design gets more physical. Early steps estimate; later steps "
        "measure. The skill of ASIC design is making early estimates good "
        "enough that the measurements at sign-off hold no surprises.")
    pb()

    _banner("Table of Contents")
    toc = TableOfContents()
    toc.levelStyles = [S_TOC1, S_TOC2, S_TOC3]
    add(toc)


# =============================================================================
#                                  BUILD
# =============================================================================
def main():
    build(OUTPUT, [front_matter, part1, part2, part3, part4, part5, part6,
                   appendices])


if __name__ == "__main__":
    main()
