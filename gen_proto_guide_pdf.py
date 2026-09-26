"""
Communication Protocols for SoC & ASIC - The Complete Guide (Beginner to Expert)
===============================================================================
Generates a single, detailed, self-contained PDF textbook on every
communication protocol on the SoC/ASIC roadmap: signalling, line coding,
SerDes, handshakes, flow control and error detection; the on-chip AMBA family
(APB, AHB, AXI4, AXI4-Lite, AXI4-Stream, ACE, CHI) and other on-chip buses and
NoCs; the peripheral buses (UART, SPI/QSPI/xSPI, I2C/SMBus, I3C, CAN/CAN FD/LIN/
FlexRay, I2S/PDM/S/PDIF, 1-Wire, MDIO); the high-speed links (USB, PCI Express
and CXL, Ethernet); memory interfaces (DDR/LPDDR/HBM, DFI, NAND/eMMC/SD/UFS);
display and camera (MIPI D-PHY/C-PHY, CSI-2, DSI, HDMI, DisplayPort);
chip-to-chip and die-to-die links (JESD204, Aurora, Interlaken, UCIe); debug and
trace (JTAG, IEEE 1500/1687, CoreSight, SWD, RISC-V debug); and how controllers
are architected, verified, secured and budgeted in a real SoC.

Protocol building blocks (encoders, CRCs, serializers, controller FSMs) were
written in Verilog/SystemVerilog and run with Icarus Verilog 12 or Verilator
5.020, and CRC/coding results were cross-checked against Python references;
the output shown on green cards is the output the tools actually produced.

Companion to gen_rtl_guide_pdf.py and gen_sv_guide_pdf.py; the chapters live
in the proto_guide/ package.

Usage:
    pip install reportlab
    python gen_proto_guide_pdf.py

Output:
    Communication_Protocols_for_SoC_and_ASIC_Complete_Guide.pdf
"""

import os

from proto_guide.common import (
    add, p, h3, bul, box, tbl, pb, mk, build,
    Paragraph, Table, TableStyle, Spacer, HRFlowable, TableOfContents,
    colors, mm, CONTENT_W, C_DARK, C_MID, C_LGREY, S_TITLE, S_SUBTITLE, S_H1,
    S_TD, S_TDB, S_TOC1, S_TOC2, S_TOC3,
)
from proto_guide.part1 import part1
from proto_guide.part2 import part2
from proto_guide.part3 import part3
from proto_guide.part4a import part4a
from proto_guide.part4b import part4b
from proto_guide.part5 import part5
from proto_guide.appx import appendices

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(
    HERE, "Communication_Protocols_for_SoC_and_ASIC_Complete_Guide.pdf")


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
    add(Paragraph("Communication Protocols", S_TITLE))
    add(Spacer(1, 2))
    add(Paragraph("for SoC &amp; ASIC Design", S_SUBTITLE))
    add(Spacer(1, 4))
    add(HRFlowable(width="45%", thickness=2, color=C_MID, spaceAfter=10,
                   hAlign="CENTER"))
    add(Paragraph("The Complete Guide - From Beginner to Expert", S_SUBTITLE))
    add(Spacer(1, 6))
    add(Paragraph("Signalling &amp; SerDes &#183; Line Coding &#183; CRC &amp; "
                  "ECC &#183; APB &#183; AHB &#183; AXI4 &#183; AXI-Stream "
                  "&#183; ACE &amp; CHI &#183; TileLink &#183; NoC &#183; UART "
                  "&#183; SPI / QSPI / xSPI &#183; I2C &#183; I3C &#183; CAN "
                  "&#183; LIN &#183; I2S &#183; USB &#183; PCIe &amp; CXL "
                  "&#183; Ethernet &#183; DDR / LPDDR / HBM &#183; MIPI CSI-2 "
                  "&amp; DSI &#183; HDMI &#183; DisplayPort &#183; JESD204 "
                  "&#183; UCIe &#183; JTAG &#183; SWD &#183; CoreSight",
                  S_SUBTITLE))
    add(Spacer(1, 12 * mm))
    rows = [
        ["Contents", "27 chapters in 5 parts, plus 4 appendices"],
        ["Scope", "Every protocol an SoC talks through - on-chip buses, "
         "peripheral buses, high-speed serial links, memory, display and "
         "camera, chip-to-chip and die-to-die, debug and trace"],
        ["Depth", "Signals, framing, timing diagrams, state machines, flow "
         "control, error handling, performance numbers, controller and PHY "
         "architecture, verification and integration"],
        ["Every example runs", "Protocol building blocks were written in "
         "Verilog/SystemVerilog and simulated with **Icarus Verilog 12** or "
         "**Verilator 5.020**; CRCs and encodings were cross-checked against "
         "Python. Green cards show the real output"],
        ["Specifications", "Explained precisely but not reproduced; many are "
         "members-only. Where a number depends on a spec version it is "
         "labelled, and Appendix D lists the source documents"],
        ["Companions", "__RTL Design for SoC & ASIC__ and __Verilog & "
         "SystemVerilog for SoC & ASIC__ in this repository"],
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
    p("A modern SoC is as much a communication system as a computer. Inside "
      "it, dozens of blocks exchange data over **on-chip buses** and "
      "networks; at its edges, it talks to sensors, flash, memory, displays, "
      "cameras, other chips and the debugger over **off-chip protocols**, "
      "each with its own wires, timing, framing and rules. A large share of "
      "an SoC team's work - and a large share of its bugs - lives at these "
      "interfaces: a misread handshake rule, a CRC with the wrong bit order, "
      "a clock-domain crossing inside a controller, a burst that crosses a "
      "4 KB boundary, a link that trains in the lab and fails in the field.")
    p("This book explains every protocol on that map at the depth an SoC or "
      "ASIC engineer needs. For each one it shows the signals and the "
      "physical layer, the frame or transaction format, timing diagrams, "
      "the state machines, flow control and error handling, the numbers "
      "that matter for performance, how the controller and PHY are built "
      "in RTL, how they are verified, and which team owns which piece.")

    h3("The five parts")
    tbl(["Part", "Chapters", "What you get out of it"],
        [["I - Foundations", "1-4",
          "The protocol map of an SoC; signalling, clocking schemes, line "
          "coding and SerDes; handshakes, flow control, ordering, CRC and "
          "ECC; how protocols are implemented and verified in RTL."],
         ["II - On-Chip Protocols", "5-10",
          "APB, AHB, AXI4, AXI4-Lite and AXI4-Stream in depth; cache "
          "coherency with MESI/MOESI, ACE and CHI; Wishbone, Avalon, "
          "TileLink, OCP and networks-on-chip."],
         ["III - Peripheral Protocols", "11-16",
          "UART and RS-232/485; SPI, Quad/Octal SPI and xSPI; I2C, SMBus "
          "and PMBus; MIPI I3C; CAN, CAN FD, LIN, FlexRay and automotive "
          "Ethernet; I2S, PDM, S/PDIF, 1-Wire and MDIO."],
         ["IV - High-Speed & Memory", "17-23",
          "USB; PCI Express and CXL; Ethernet MACs, PHYs and the xMII "
          "family; DDR, LPDDR, HBM, DFI and flash interfaces; MIPI camera and "
          "display, HDMI and DisplayPort; JESD204, Interlaken and UCIe; "
          "JTAG, IEEE 1500/1687, CoreSight and trace."],
         ["V - Designing With Protocols", "24-27",
          "Controller architecture and PHY integration; verification IP, "
          "assertions and compliance; reliability, safety and link security; "
          "choosing and budgeting protocols for an SoC, and the learning "
          "roadmap."]],
        widths=[27, 12, 61], bold_first=True)

    h3("Reading paths")
    bul([
        "**Beginner:** 1-4, then 11, 12, 13 and 5 - the protocols you can "
        "build and test on an FPGA board in a weekend each - then 7.",
        "**RTL designer joining an SoC team:** 3, 5-8, then the peripheral "
        "or high-speed chapters your block touches, then 24.",
        "**Verification engineer:** 3, 4, 7, 25, then the chapter for the "
        "protocol you are verifying.",
        "**Architect or lead:** 1, 2, 9, 10, 17-22, 26 and 27.",
        "**Interview preparation:** 3, 5, 7, 11-13, 18, 20, then Appendix C.",
    ])

    h3("Conventions")
    tbl(["Style", "Meaning"],
        [["A grey card", "RTL, a testbench or a script, exactly as it was run"],
         ["A **green card**", "The output that code produced when run with "
          "Icarus Verilog 12, Verilator 5.020 or Python while this book was "
          "written"],
         ["An ASCII figure", "A timing diagram, frame or packet layout, state "
          "machine or block diagram"],
         ["Coloured boxes", "KEY IDEA = the one thing to remember. MATH = a "
          "formula or bandwidth calculation. INTUITION = the mental picture. "
          "PRACTICAL TIP = what to do. PITFALL = a bug that reaches silicon or "
          "the field. EXPERT CORNER = depth you can skip on a first read."],
         ["Speeds", "`Mb/s` and `Gb/s` are bits per second; `GT/s` is "
          "transfers (symbols) per second per lane, before line-coding "
          "overhead; `MB/s` and `GB/s` are bytes per second"]],
        widths=[22, 78], bold_first=True)
    box("tip", "Build the small ones",
        "UART, SPI, I2C and APB can each be written, simulated and run on a "
        "cheap FPGA board with a logic analyser in a few evenings. Nothing "
        "teaches protocol rules faster than watching your own controller "
        "fail against a real device - and every chapter in Part III gives "
        "you a working starting point.")
    box("key", "Three questions to ask of any protocol",
        "**Who may talk, and when?** (arbitration, handshake and flow "
        "control). **How does the receiver know where data starts and "
        "whether it is correct?** (clocking, framing, coding and error "
        "detection). **What happens when something goes wrong?** (errors, "
        "retry, timeouts and recovery). Every protocol in this book is a "
        "different set of answers to these three questions.")
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
