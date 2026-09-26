"""
Verilog & SystemVerilog for SoC & ASIC - The Complete Guide (Beginner to Expert)
===============================================================================
Generates a single, detailed, self-contained PDF textbook on the two hardware
languages of the SoC/ASIC roadmap: Verilog (IEEE 1364-2005) and SystemVerilog
(IEEE 1800). It covers the lexical rules, data types, 4-state semantics,
expression sizing and signedness, the event scheduler, procedural code,
parameters and generate, compiler directives, gate-level modelling and timing
checks, system tasks, the synthesizable subset, SystemVerilog design features
(types, arrays, packages, interfaces), and SystemVerilog verification (OOP,
constrained random, processes and IPC, clocking and program blocks, SVA,
functional coverage, DPI and VPI), then builds a layered testbench, explains
how UVM uses the language, catalogues pitfalls and lays out a learning roadmap.

Examples that the open-source tools can run were compiled and run with Icarus
Verilog 12 or Verilator 5.020; the output shown on green cards is the output
they actually produced. Code those tools cannot run (constraint solving,
covergroups, most concurrent SVA, UVM) is shown without an output card.

Companion to gen_rtl_guide_pdf.py; the chapters live in the sv_guide/ package.

Usage:
    pip install reportlab
    python gen_sv_guide_pdf.py

Output:
    Verilog_and_SystemVerilog_for_SoC_and_ASIC_Complete_Guide.pdf
"""

import os

from sv_guide.common import (
    add, p, h3, bul, box, tbl, pb, mk, build,
    Paragraph, Table, TableStyle, Spacer, HRFlowable, TableOfContents,
    colors, mm, CONTENT_W, C_DARK, C_MID, C_LGREY, S_TITLE, S_SUBTITLE, S_H1,
    S_TD, S_TDB, S_TOC1, S_TOC2, S_TOC3,
)
from sv_guide.part1 import part1
from sv_guide.part2 import part2
from sv_guide.part3 import part3
from sv_guide.part4a import part4a
from sv_guide.part4b import part4b
from sv_guide.part5 import part5
from sv_guide.appx import appendices

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(
    HERE, "Verilog_and_SystemVerilog_for_SoC_and_ASIC_Complete_Guide.pdf")


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
    add(Spacer(1, 36 * mm))
    add(Paragraph("Verilog &amp; SystemVerilog", S_TITLE))
    add(Spacer(1, 2))
    add(Paragraph("for SoC &amp; ASIC Design", S_SUBTITLE))
    add(Spacer(1, 4))
    add(HRFlowable(width="45%", thickness=2, color=C_MID, spaceAfter=10,
                   hAlign="CENTER"))
    add(Paragraph("The Complete Guide - From Beginner to Expert", S_SUBTITLE))
    add(Spacer(1, 6))
    add(Paragraph("Lexical Rules &#183; Data Types &#183; 4-State Logic &#183; "
                  "Sizing &amp; Signedness &#183; The Event Scheduler &#183; "
                  "Parameters &amp; Generate &#183; Directives &#183; "
                  "Gate-Level &amp; Timing Checks &#183; System Tasks &#183; "
                  "Synthesizable Subset &#183; SV Types &amp; Arrays &#183; "
                  "Packages &#183; Interfaces &#183; OOP &#183; Constrained "
                  "Random &#183; IPC &#183; Clocking Blocks &#183; SVA &#183; "
                  "Coverage &#183; DPI &#183; Testbenches &#183; UVM &#183; "
                  "Pitfalls &#183; Roadmap", S_SUBTITLE))
    add(Spacer(1, 12 * mm))
    rows = [
        ["Contents", "28 chapters in 5 parts, plus 4 appendices"],
        ["Level", "From your first `module` to classes, constraints, "
         "assertions, coverage and DPI - the whole language, design and "
         "verification"],
        ["Standards", "Verilog IEEE 1364-2005 and SystemVerilog IEEE 1800 "
         "(2017, with 2023 changes noted)"],
        ["Every example runs", "Where an open-source tool can run it, the "
         "example was run with **Icarus Verilog 12** or **Verilator 5.020**; "
         "the output on green cards is what the tool actually printed"],
        ["Honest about tools", "Code that needs a commercial simulator "
         "(constraint solving, covergroups, full SVA, UVM) is marked as such "
         "and shown without an output card"],
        ["Companion", "__RTL Design for SoC & ASIC__ in this repository "
         "covers micro-architecture; this book covers the languages"],
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
    p("Two languages carry a chip from idea to silicon. **Verilog** is the "
      "language almost every piece of synthesizable RTL is still written in, "
      "and the language of gate-level netlists and standard-cell models. "
      "**SystemVerilog** is its superset: it makes design code safer and "
      "more compact (`logic`, `always_ff`, enums, structs, packages, "
      "interfaces), and it adds a complete verification language - classes, "
      "constrained random stimulus, processes, assertions and coverage - on "
      "which UVM and nearly every modern verification environment is built.")
    p("Most engineers learn these languages by copying code that works, and "
      "pay for it later in bugs that come from rules they never learned: an "
      "expression evaluated at the wrong width, a signed value silently "
      "treated as unsigned, a race between two `initial` blocks, an `x` that "
      "a 2-state type hid, a loop variable captured by a `fork`. This book "
      "teaches the rules themselves, precisely, and shows every one of those "
      "failures happening in a real simulator.")

    h3("The five parts")
    tbl(["Part", "Chapters", "What you get out of it"],
        [["I - Verilog Fundamentals", "1-6",
          "History, standards and tools; lexical rules, modules and ports; "
          "nets, variables and 4-state values; operators with the exact "
          "sizing and signedness rules; assignments, timing controls and the "
          "scheduler; control flow, functions and tasks."],
         ["II - Verilog in Depth", "7-11",
          "Parameters and generate; compiler directives and macros; "
          "gate-level modelling, UDPs, specify blocks and timing checks; "
          "system tasks and file I/O; the synthesizable subset and "
          "simulation/synthesis mismatches."],
         ["III - SystemVerilog for Design", "12-17",
          "New data types, casting and assignment patterns; every kind of "
          "array; `always_comb`/`always_ff`, `unique`/`priority` and new "
          "operators; packages and scoping; interfaces and modports; idioms "
          "used in real SoC RTL."],
         ["IV - SystemVerilog for Verification", "18-24",
          "Classes and OOP; constrained random; fork/join, events, "
          "semaphores and mailboxes; clocking and program blocks; assertions "
          "(SVA); functional coverage; DPI-C, VPI and Python co-simulation."],
         ["V - Putting It Together", "25-28",
          "A complete layered testbench; how UVM is built from the language; "
          "a catalogue of pitfalls and portability issues; the learning "
          "roadmap for each SoC/ASIC role."]],
        widths=[27, 12, 61], bold_first=True)

    h3("Reading paths")
    bul([
        "**Complete beginner:** Parts I and II in order, running every "
        "example. Chapters 4 and 5 are the ones that separate people who "
        "know Verilog from people who have used it.",
        "**RTL designer:** 1-7, 11, then 12-17. Skip Part IV until you need "
        "to write assertions (Chapter 22).",
        "**Verification engineer:** 3-5 and 12-16 for the language core, "
        "then all of Part IV and Chapters 25-26.",
        "**Gate-level, DFT or library work:** 3, 5, 8, 9 and 10.",
        "**Interview preparation:** 4, 5, 11, 14, 18-20, 22, 27, then "
        "Appendix C.",
    ])

    h3("Conventions")
    tbl(["Style", "Meaning"],
        [["A grey card", "Code exactly as you would save it"],
         ["A **green card**", "The output that code produced when run with "
          "Icarus Verilog 12 or Verilator 5.020 while this book was written"],
         ["No green card", "Either a fragment, or code that needs a "
          "commercial simulator; the text says which"],
         ["Coloured boxes", "KEY IDEA = the one thing to remember. MATH = a "
          "rule or equation. INTUITION = the mental picture. PRACTICAL TIP = "
          "what to do. PITFALL = a mistake that reaches silicon or sign-off. "
          "EXPERT CORNER = depth you can skip on a first read."],
         ["LRM", "The IEEE language reference manual: 1364-2005 for Verilog, "
          "1800-2017/2023 for SystemVerilog"]],
        widths=[22, 78], bold_first=True)
    box("tip", "Run the examples yourself",
        "Icarus Verilog (`iverilog -g2012`) and Verilator (`verilator "
        "--binary --timing`) are free and install with one package-manager "
        "command. EDA Playground gives browser access to commercial "
        "simulators for the constraint, coverage and assertion examples no "
        "open-source tool fully runs yet.")
    box("key", "Two questions to ask of every line of code",
        "**What hardware does this describe?** - for design code, and "
        "**when does this execute, relative to everything else?** - for "
        "every line. The first question is answered by Chapters 11 and 17, "
        "the second by Chapters 5 and 21. Almost every bug in this book is a "
        "wrong answer to one of them.")
    pb()

    _banner("Table of Contents")
    toc = TableOfContents()
    toc.levelStyles = [S_TOC1, S_TOC2, S_TOC3]
    add(toc)


# =============================================================================
#                                  BUILD
# =============================================================================
def main():
    build(OUTPUT, [front_matter, part1, part2, part3, part4a, part4b, part5,
                   appendices])


if __name__ == "__main__":
    main()
