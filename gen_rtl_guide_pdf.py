"""
RTL Design for SoC & ASIC - The Complete Guide (Beginner to Expert)
===================================================================
Generates a single, detailed, self-contained PDF textbook covering every RTL
topic on the road to SoC and ASIC design: digital logic, Verilog and
SystemVerilog, simulation semantics, combinational and sequential logic, FSMs,
datapaths, memories and FIFOs, pipelining and flow control, clock-domain
crossing, resets, AMBA buses, interconnect and arbitration, registers and
interrupts, peripherals and processor integration, synthesis, STA and SDC,
low-power design and UPF, DFT, PPA and the physical-design hand-off,
verification (testbenches, SVA, coverage, UVM, formal, lint, CDC), debug and
prototyping, two complete projects, and a career roadmap.

Every synthesizable example and testbench was compiled and simulated with
Icarus Verilog 12 (iverilog -g2012); the output shown on green cards is the
output the simulator actually produced.

The chapters live in the rtl_guide/ package; the layout engine is reused from
gen_ml_dl_guide_pdf.py.

Usage:
    pip install reportlab
    python gen_rtl_guide_pdf.py

Output:
    RTL_Design_for_SoC_and_ASIC_Complete_Guide.pdf
"""

import os

from rtl_guide.common import (
    add, p, h3, bul, box, tbl, pb, mk, build,
    Paragraph, Table, TableStyle, Spacer, HRFlowable, TableOfContents,
    colors, mm, CONTENT_W, C_DARK, C_MID, C_LGREY, S_TITLE, S_SUBTITLE, S_H1,
    S_TD, S_TDB, S_TOC1, S_TOC2, S_TOC3,
)
from rtl_guide.part1 import part1
from rtl_guide.part2 import part2
from rtl_guide.part3 import part3
from rtl_guide.part4 import part4
from rtl_guide.part5 import part5
from rtl_guide.part6 import part6
from rtl_guide.appx import appendices

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(HERE, "RTL_Design_for_SoC_and_ASIC_Complete_Guide.pdf")


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
    add(Spacer(1, 38 * mm))
    add(Paragraph("RTL Design for SoC &amp; ASIC", S_TITLE))
    add(Spacer(1, 4))
    add(HRFlowable(width="45%", thickness=2, color=C_MID, spaceAfter=10,
                   hAlign="CENTER"))
    add(Paragraph("The Complete Guide - From Beginner to Expert", S_SUBTITLE))
    add(Spacer(1, 6))
    add(Paragraph("Digital Logic &#183; Verilog &amp; SystemVerilog &#183; "
                  "Simulation Semantics &#183; FSMs &#183; Datapaths &#183; "
                  "FIFOs &#183; Pipelines &#183; Clock-Domain Crossing &#183; "
                  "Resets &#183; APB / AHB / AXI &#183; Interconnect &#183; "
                  "Registers &amp; Interrupts &#183; Peripherals &#183; "
                  "Synthesis &#183; STA &amp; SDC &#183; Low Power &amp; UPF "
                  "&#183; DFT &#183; PPA &#183; Testbenches &#183; SVA &#183; "
                  "UVM &#183; Formal &#183; Projects &#183; Career Roadmap",
                  S_SUBTITLE))
    add(Spacer(1, 14 * mm))
    rows = [
        ["Contents", "30 chapters in 6 parts, plus 4 appendices"],
        ["Level", "From your first `module` to micro-architecture, sign-off "
         "and tape-out readiness"],
        ["Goal", "Every RTL topic you need on the road to SoC and ASIC "
         "design, in the order you need it"],
        ["Every example runs", "All synthesizable RTL and testbenches were "
         "simulated with **Icarus Verilog 12**; the output on green cards is "
         "the output it actually produced"],
        ["Languages", "Verilog-2005 and the synthesizable subset of "
         "SystemVerilog (IEEE 1800), plus SVA, UVM, SDC, UPF and Tcl where "
         "the flow needs them"],
        ["Assumed", "Curiosity and basic programming. No prior hardware "
         "design experience."],
    ]
    t = Table([[Paragraph(mk(a), S_TDB), Paragraph(mk(b), S_TD)] for a, b in rows],
              colWidths=[42 * mm, CONTENT_W - 42 * mm])
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
    p("**RTL** - register-transfer level - is the level at which almost every "
      "digital chip is designed today. An RTL description says which "
      "**registers** exist, and what **combinational logic** transforms the "
      "values moving between them on every clock edge. Everything upstream "
      "of RTL (architecture, performance models) decides __what__ to build; "
      "everything downstream (synthesis, place and route, sign-off) turns "
      "your RTL into transistors. The RTL is the contract between the two, "
      "and it is where most of a chip's bugs, most of its timing problems "
      "and most of its power are decided.")
    p("This book follows that contract from both sides. Parts I and II teach "
      "the language and the building blocks until you can write any block "
      "correctly. Part III assembles blocks into an SoC. Part IV shows what "
      "the back end does with your code, so that you write RTL that closes "
      "timing, saves power and can be tested. Part V covers how the design is "
      "proven correct, and Part VI puts it all together in two complete, "
      "simulated projects and a career roadmap.")

    h3("The six parts")
    tbl(["Part", "Chapters", "What you get out of it"],
        [["I - Foundations", "1-4",
          "Where RTL sits in the SoC/ASIC flow; the digital logic you must "
          "know cold; Verilog and SystemVerilog for design; and the event "
          "scheduler that explains blocking vs non-blocking assignments."],
         ["II - Core Building Blocks", "5-10",
          "Combinational and sequential logic, resets, FSMs, arithmetic "
          "datapaths, memories and FIFOs, pipelines and valid/ready flow "
          "control."],
         ["III - SoC Architecture", "11-16",
          "Clock-domain crossing, reset architecture, AMBA buses (APB, AHB, "
          "AXI), interconnect and arbitration, register maps and interrupts, "
          "peripherals, DMA and processor integration."],
         ["IV - Implementation-Aware RTL", "17-21",
          "Synthesis, static timing and SDC, low-power design and UPF, design "
          "for test, PPA trade-offs and the physical-design hand-off."],
         ["V - Verification", "22-26",
          "Self-checking testbenches, assertions and coverage, UVM, static "
          "sign-off (lint, CDC, formal, LEC), debug, gate-level simulation, "
          "FPGA prototyping and emulation."],
         ["VI - Projects and Roadmap", "27-30",
          "Coding guidelines and reviews; an APB UART subsystem; an "
          "AXI-Stream int8 MAC accelerator for on-device ML; and the skills, "
          "study plan and interview preparation for an RTL/SoC career."]],
        widths=[26, 12, 62], bold_first=True)

    h3("Reading paths")
    bul([
        "**Complete beginner:** read Parts I and II in order, typing and "
        "simulating every example. Chapter 4 is the one most people skip and "
        "most regret skipping.",
        "**Software engineer moving to hardware:** 1, 2, 3, 4, 6, 10 - then "
        "Chapter 11 before you connect anything to a second clock.",
        "**FPGA designer moving to ASIC:** 1, 11, 12, 17-21 and 25 - the "
        "topics FPGA tools hide from you.",
        "**Verification engineer:** 3, 4, 10, 13, then all of Part V.",
        "**Preparing for interviews:** Chapters 2, 4, 7, 9, 11, 18, then "
        "Appendix C and Chapter 30.",
        "**Building an SoC for the first time:** 11-16 in order, then the "
        "projects in Chapters 28 and 29.",
    ])

    h3("Conventions")
    tbl(["Style", "Meaning"],
        [["A grey card", "RTL, a testbench, a constraint file or a script, "
          "exactly as you would save it"],
         ["A **green card**", "The output the code above it produced when "
          "simulated with Icarus Verilog 12 while this book was written"],
         ["An ASCII figure", "The hardware a piece of code infers, a block "
          "diagram, or a timing diagram"],
         ["Coloured boxes", "KEY IDEA = the one thing to remember. MATH = a "
          "derivation or equation. INTUITION = the mental picture. PRACTICAL "
          "TIP = what to do. PITFALL = a mistake that reaches silicon. EXPERT "
          "CORNER = depth you can skip on a first read."],
         ["`_q` / `_d` / `_n`", "Register output / next-state input / "
          "active-low signal (Chapter 27 gives the full naming convention)"]],
        widths=[22, 78], bold_first=True)
    box("tip", "Simulate as you read",
        "Install a free simulator - `iverilog` (Icarus Verilog) and `gtkwave` "
        "are one package-manager command away on Linux and macOS, and "
        "Verilator is the fastest open-source option. Type the examples, run "
        "them, change them and look at the waveforms. RTL design is learned "
        "at the simulator and the whiteboard, not by reading alone.")
    box("key", "The one habit that separates good RTL designers",
        "Before writing a line of code, **draw the hardware**: the registers, "
        "the logic between them, and the clock that drives them. RTL is a "
        "description of a circuit, not a program. Every chapter in this book "
        "shows the circuit behind the code for exactly this reason.")
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
