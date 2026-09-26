"""Part I - Foundations (chapters 1-5) of the ASIC design guide.

Every out() card is real output: the Python models were run with Python 3.11,
the Liberty/LEF excerpts come from the real SkyWater SKY130 high-density
library (sky130_fd_sc_hd, typical corner tt_025C_1v80, as distributed with
OpenROAD-flow-scripts), and the synthesis run used Yosys 0.33 against that
Liberty file. The scripts and their captured output are stored verbatim at
the bottom of this module.
"""

from asic_guide.common import *  # noqa: F401,F403


def L(s):
    """Multi-line string -> list of lines without the leading/trailing newline."""
    return s.strip("\n").split("\n")


def excerpt(s, keep):
    """Keep only the lines whose text contains one of the `keep` substrings,
    marking each gap with '...'. Used to shorten long real tool reports."""
    res, gap = [], False
    for ln in L(s):
        if any(k in ln for k in keep):
            if gap and res:
                res.append("   ...")
            res.append(ln)
            gap = False
        else:
            gap = True
    return res


def part1():
    part("Foundations",
         "What an ASIC is and why companies build one; the economics and the "
         "end-to-end flow from an idea to a shipping part; the physics of the "
         "MOSFET and the CMOS gate that set every delay and every milliwatt; "
         "how wafers are actually made and what a PDK hands you; the standard "
         "cells, Liberty and LEF files and IP blocks you build with; and how "
         "a specification becomes an architecture with PPA targets.")
    _ch1()
    _ch2()
    _ch3()
    _ch4()
    _ch5()


# =============================================================================
#  Chapter 1 - The ASIC landscape
# =============================================================================
def _ch1():
    chapter("The ASIC Landscape: What an ASIC Is, Design Styles, Economics "
            "and the End-to-End Flow", newpage=False)
    p("An **application-specific integrated circuit** (ASIC) is a chip "
      "designed to do one job, or one family of jobs, for one product line: "
      "the image signal processor in a phone camera, the controller in an "
      "SSD, a bitcoin miner, a 5G baseband, the neural accelerator in a "
      "car. It is the opposite of a general-purpose part such as an "
      "off-the-shelf microcontroller or an FPGA, which is designed once and "
      "sold to thousands of customers who program it for their own needs.")
    p("Building an ASIC is one of the most capital-intensive and "
      "schedule-critical activities in engineering. A modern project "
      "involves architects, RTL designers, verification engineers, DFT, "
      "physical design, analog, package, test, software and product "
      "engineers; it consumes millions of dollars of tool licences, IP and "
      "masks before the first chip exists; and a single escaped bug can "
      "cost a re-spin of several months. This chapter draws the whole map: "
      "what an ASIC and an SoC are, the ways a chip can be built, when "
      "building one makes economic sense, who does what in the industry, "
      "and the end-to-end flow that the rest of this book walks through "
      "step by step.")

    h2("ASIC, SoC, ASSP: the vocabulary")
    p("The terms overlap and are used loosely, so it pays to be precise:")
    tbl(["Term", "Meaning", "Example"], [
        ["ASIC", "A chip designed for a specific application, usually for "
         "one customer or one product line. Strictly, the term says nothing "
         "about complexity: a 10k-gate sensor interface is an ASIC too.",
         "An automotive radar front-end controller"],
        ["ASSP", "Application-specific standard product: application-"
         "specific, but sold on the open market to many customers.",
         "A USB-to-Ethernet bridge chip, a Wi-Fi combo chip"],
        ["SoC", "System-on-chip: an ASIC or ASSP that integrates processors, "
         "memories, interconnect, peripherals and often analog/RF on one "
         "die, so that it runs software and forms a whole system.",
         "A phone application processor; an edge-AI camera SoC"],
        ["Custom silicon / XPU", "In-house ASICs built by system companies "
         "(hyperscalers, phone makers, carmakers) for their own products.",
         "Datacentre AI accelerators, video transcoders"],
        ["Chiplet", "A die designed to be packaged together with other dies "
         "(Chapter 20) rather than as a stand-alone chip.",
         "CPU compute die plus separate I/O die"],
    ], widths=[1.3, 4.2, 2.6], bold_first=True)
    p("In this book 'ASIC' means any chip that goes through the "
      "cell-based implementation flow described here - which covers "
      "almost every digital or mixed-signal SoC made today.")
    h3("Anatomy of a typical SoC")
    p("Every SoC contains the same broad ingredients: processing (CPU, "
      "DSP, accelerators), memory (on-chip SRAM plus an external DRAM "
      "interface), an interconnect (buses or a network-on-chip), "
      "high-speed and low-speed peripherals, infrastructure (clocks, "
      "resets, power management, always-on logic, sensors), security, and "
      "test/debug logic. The differentiating block - the thing that "
      "justifies the chip - is often a small fraction of the area; the "
      "rest is infrastructure that must nevertheless be integrated, "
      "verified and signed off with the same rigour.")
    diagram([
        "  +------------------------------------------------------------------------+",
        "  | I/O ring: GPIO, power/ground pads, ESD                                 |",
        "  |  +-----------+  +-----------+  +-------------+  +-------------------+  |",
        "  |  | CPU       |  | NPU / DSP |  | ISP / video |  | Security: crypto, |  |",
        "  |  | cluster   |  | accel.    |  | codec       |  | OTP keys, TRNG    |  |",
        "  |  | + L1/L2   |  | + SRAM    |  | + buffers   |  +-------------------+  |",
        "  |  +-----+-----+  +-----+-----+  +------+------+           |             |",
        "  |        |              |               |                  |             |",
        "  |  ======+==============+===============+==================+=====  NoC   |",
        "  |        |              |               |                  |             |",
        "  |  +-----+-----+  +-----+------+  +-----+--------+  +------+---------+   |",
        "  |  | DDR ctrl  |  | PCIe/USB   |  | Peripherals  |  | PMU, clocks,   |   |",
        "  |  | + PHY     |  | ctrl + PHY |  | UART,SPI,I2C |  | PLLs, resets,  |   |",
        "  |  | (hard IP) |  | (hard IP)  |  | GPIO, timers |  | sensors, AON   |   |",
        "  |  +-----------+  +------------+  +--------------+  +----------------+   |",
        "  |   DFT: scan chains, compression, MBIST, JTAG/IEEE 1500 across all      |",
        "  +------------------------------------------------------------------------+",
    ], "Block diagram of a representative SoC. Soft IP, in-house RTL, "
       "compiled memories and hard analog/mixed-signal IP all meet on one die.")

    h2("Design styles: from full custom to FPGA")
    p("There are several ways to turn a logic design into a physical chip. "
      "They differ in how many mask layers are unique to your design (and "
      "therefore in non-recurring engineering cost, NRE), how long it takes, "
      "and how dense, fast and power-efficient the result is.")
    h3("Full custom")
    p("Every transistor is drawn by hand (or by a generator) and every "
      "wire is placed deliberately. All mask layers are unique. This gives "
      "the highest density and speed, but costs enormous engineering "
      "effort. Today full custom is used for things that are replicated "
      "millions of times or that are extremely performance-critical: SRAM "
      "bitcells, register files, high-speed SerDes, analog blocks, the "
      "datapaths of flagship CPUs, and the standard cells themselves.")
    h3("Standard cell (cell-based) design")
    p("The dominant style for digital logic. A library of pre-designed, "
      "pre-characterised gates (standard cells, Chapter 4) of equal height "
      "is placed in rows and connected by automatic place-and-route tools. "
      "All masks are still unique to the design, so NRE is the same order as "
      "full custom, but engineering effort is far lower because the "
      "design is described in RTL and implemented largely by EDA tools. "
      "Nearly everything in this book is about the standard-cell flow.")
    h3("Gate array and structured ASIC")
    p("A **gate array** pre-fabricates wafers with a regular sea of "
      "transistors (the 'base' layers) and only the top metal layers are "
      "customised per design. Fewer unique masks means lower NRE and a "
      "faster turnaround (weeks instead of months from tapeout to parts), "
      "at the cost of density and speed. A **structured ASIC** extends the "
      "idea: the base contains pre-built logic cells, memories, PLLs and "
      "I/Os, and only a few via/metal layers are customised. Structured "
      "ASICs were popular as an FPGA-to-ASIC conversion path; they "
      "survive in niche offerings (e.g. via-programmable platforms) but "
      "have largely been squeezed out by cheaper FPGAs and mature-node "
      "cell-based ASICs.")
    h3("FPGA and eFPGA")
    p("A **field-programmable gate array** is a standard product with "
      "configurable logic blocks (look-up tables and flip-flops), DSP "
      "blocks, block RAM and programmable routing, configured by a "
      "bitstream. There is zero silicon NRE and a design can be changed in "
      "minutes, but the per-unit price is high and the fabric is typically "
      "an order of magnitude or more worse than an ASIC in area, several "
      "times worse in dynamic power, and noticeably slower for the same "
      "logic, because most of the silicon is programmable routing and "
      "configuration memory. An **embedded FPGA** (eFPGA) is an FPGA fabric "
      "delivered as a hard IP block inside an ASIC, used where part of the "
      "logic must stay changeable after tapeout (evolving protocols, "
      "customer-specific accelerators, security patches).")
    tbl(["Style", "Custom masks", "NRE", "Time to parts", "Density / speed / power",
         "Typical use"], [
        ["Full custom", "All", "Highest", "Months", "Best", "Bitcells, SerDes, analog, "
         "critical datapaths, the cells themselves"],
        ["Standard cell", "All", "High", "Months (tapeout -> parts ~2-4 months "
         "in mature nodes, longer in advanced nodes)", "Very good",
         "Almost all digital ASICs and SoCs"],
        ["Gate array", "Metal only", "Medium", "Weeks", "Moderate",
         "Legacy, rad-hard, quick-turn"],
        ["Structured ASIC", "A few via/metal", "Low-medium", "Weeks", "Moderate",
         "FPGA conversion, niche volumes"],
        ["FPGA", "None", "None", "Minutes", "Worst (large area and power "
         "overhead)", "Prototyping, low volume, fast-changing standards"],
        ["eFPGA in ASIC", "(part of ASIC)", "IP licence", "-", "FPGA-like "
         "inside the block", "Post-silicon programmability"],
    ], widths=[1.3, 1.1, 0.9, 1.9, 1.6, 2.6], bold_first=True,
       caption="Design styles compared. Ratios vary by generation and design; "
               "the ordering is what matters.")
    box("key", "Most real SoCs are a mix of styles",
        "A typical SoC is cell-based digital logic, plus compiler-generated "
        "SRAMs (full-custom bitcells tiled by a generator), plus hard IP "
        "(PLLs, SerDes, DDR PHYs, ADCs) that were designed full custom by "
        "specialists, plus a custom I/O ring. Integrating these pieces "
        "correctly is a large part of ASIC engineering.")

    h2("When does building an ASIC make sense?")
    p("An ASIC is justified when it wins on at least one of: **unit cost** "
      "at volume, **power** (battery life, thermals, datacentre electricity), "
      "**performance** (functions no FPGA or CPU can reach), **form factor** "
      "(one chip instead of a board), or **differentiation and security** "
      "(IP that competitors cannot buy). The cost argument is the one that "
      "can be computed, and it is the classic interview question.")
    h3("NRE versus unit cost")
    p("Total cost for a volume V is simply NRE + V x (unit cost). "
      "**NRE** includes engineering salaries, EDA licences, IP licences, "
      "the mask set, prototype wafers, package and test development, and "
      "qualification. **Unit cost** includes the die (wafer cost divided "
      "by good dies), package, assembly, test time and yield loss. An FPGA "
      "has almost no NRE and a high unit price; an ASIC has a large NRE and "
      "a low unit price; an advanced-node ASIC has an even larger NRE.")
    eq(["Total(V) = NRE + V * C_unit",
        "Break-even volume  V* = (NRE_ASIC - NRE_FPGA) / (C_unit,FPGA - C_unit,ASIC)"],
       "Cost model and break-even volume between two implementation options.")
    code(L(SRC_BREAKEVEN), caption="breakeven.py - total cost of three options "
         "(illustrative round numbers, not quotes).")
    out(L(OUT_BREAKEVEN), caption="Real output of breakeven.py.")
    p("With these (illustrative) numbers the 28 nm ASIC beats the FPGA "
      "above roughly 130k units, while the 5 nm ASIC never makes sense "
      "for __this__ product: its NRE is so large that only a design that "
      "genuinely needs 5 nm density, speed or power - and sells in the "
      "millions or tens of millions - can recover it. In practice the "
      "advanced node is chosen for performance per watt (a datacentre "
      "accelerator, a phone SoC), not because it makes a simple chip "
      "cheaper.")
    box("warn", "PITFALL: comparing unit prices only",
        ["Teams often compare the FPGA's price with the ASIC die cost and "
         "forget NRE, schedule and risk. Include: the probability of a "
         "re-spin (a second mask set and 3-6 months), the cost of delay to "
         "market, the engineering team for 18-30 months, and the "
         "qualification cost. Conversely, FPGA-based products often forget "
         "the board cost, the configuration flash and the power supply "
         "rails an FPGA needs."])
    box("expert", "Interview insight: the three questions behind 'ASIC or not?'",
        "1) What volume and over how many years? 2) Is there a hard PPA "
        "requirement an FPGA or merchant chip cannot meet (power in a "
        "battery device, throughput per watt in a datacentre)? 3) Is the "
        "specification stable enough to freeze in silicon for the product "
        "lifetime? A 'no' to all three means do not build an ASIC.")

    h2("The industry: fabless, foundry, IDM, OSAT and the EDA/IP ecosystem")
    p("Very few companies do everything themselves. The modern "
      "semiconductor industry is a layered supply chain:")
    tbl(["Player", "What they do", "Examples of the category"], [
        ["IDM (integrated device manufacturer)", "Design and manufacture "
         "their own chips in their own fabs (often also offering foundry "
         "services).", "Intel, Samsung, Texas Instruments, Infineon"],
        ["Foundry", "Manufacture wafers for others; publish a PDK (Chapter 3) "
         "and design rules; do not sell their own chips.",
         "TSMC, GlobalFoundries, UMC, SMIC, Samsung Foundry, Intel Foundry"],
        ["Fabless company", "Design chips, own the product and the "
         "customer; outsource all manufacturing.", "NVIDIA, Qualcomm, "
         "AMD, Broadcom, MediaTek, most start-ups"],
        ["System company with in-house silicon", "Designs chips for its own "
         "products, usually fabless.", "Apple, Google, Amazon, Tesla"],
        ["Design-services house / ASIC vendor", "Takes a customer's RTL or "
         "spec through physical design, tapeout and production "
         "('turnkey' ASIC).", "Various; many foundries have partner "
         "ecosystems"],
        ["IP vendor", "Licenses pre-designed blocks: CPUs, interfaces, PHYs, "
         "memory compilers, standard-cell libraries.", "Arm, Synopsys, "
         "Cadence, Rambus, Alphawave"],
        ["EDA vendor", "Sells the design and verification tools.",
         "Synopsys, Cadence, Siemens EDA; open-source Yosys/OpenROAD"],
        ["OSAT", "Outsourced semiconductor assembly and test: packaging and "
         "production test (Chapters 20-21).", "ASE, Amkor, JCET"],
        ["Mask shop", "Writes the photomasks from the tapeout data "
         "(Chapter 19).", "Captive foundry mask shops, Photronics, Toppan"],
    ], widths=[2.1, 3.6, 2.8], bold_first=True)
    diagram([
        "  Fabless company (spec, RTL, verification, PD)      IP vendors  EDA vendors",
        "        |  licenses IP, buys tools  <-------------------+-----------+",
        "        |",
        "        |  GDSII/OASIS + tapeout forms",
        "        v",
        "  Mask shop --- masks ---> Foundry fab ---- wafers ----> Wafer sort (probe)",
        "                                                              |",
        "                                            known-good dies   v",
        "                                     OSAT: dice, package, final test, burn-in",
        "                                                              |",
        "                                                              v",
        "                                     Fabless company ships parts to customers",
    ], "The fabless supply chain: design data flows down, parts flow back.")

    h2("The end-to-end ASIC flow")
    p("The flow below is the backbone of this book. Each box is a stage "
      "with an owning team, inputs, outputs (the 'hand-off' files) and a "
      "sign-off criterion. Arrows back upward - timing or area that cannot "
      "be met, bugs found late, power over budget - are the iterations "
      "that dominate real schedules.")
    diagram([
        "  STAGE                         OWNER             HAND-OFF / KEY OUTPUTS",
        "  ----------------------------  ----------------  --------------------------------",
        "  1  Product requirements       Marketing/PM      MRD, PRD (features, cost, power)",
        "        |",
        "  2  Architecture               Architects        Arch spec, perf model, PPA target",
        "        |",
        "  3  Micro-architecture         Design leads      uArch specs, interface specs",
        "        |",
        "  4  RTL design                 RTL designers     Verilog/SV RTL, SDC, UPF, lint",
        "        |<------------------------------------+",
        "  5  Functional verification    DV engineers     Testbench, coverage, sign-off rpt",
        "        |                                     | bugs",
        "  6  Logic synthesis            Synthesis/PD     Gate netlist, reports, SDC",
        "        |",
        "  7  DFT insertion + ATPG       DFT engineers    Scan netlist, test protocol, pats",
        "        |",
        "  8  Floorplan + power plan     Physical design  DEF/ODB floorplan, PG grid, pins",
        "        |",
        "  9  Placement + optimisation   Physical design  Placed DB, timing/congestion",
        "        |",
        " 10  Clock tree synthesis       PD / clock team  Clock tree, skew/latency reports",
        "        |",
        " 11  Routing                    Physical design  Routed DB, SPEF (parasitics)",
        "        |<------------------------------------+",
        " 12  Sign-off: STA, IR/EM,      STA, PI, PV      Clean STA, IR/EM, DRC/LVS/ERC,",
        "     DRC/LVS, equivalence       engineers        LEC reports; ECOs if needed",
        "        |                                     | ECO",
        " 13  Tapeout                    PD + mgmt        GDSII/OASIS, tapeout checklist",
        "        |",
        " 14  Mask making + fab          Foundry          Masks, wafers (8-16+ weeks)",
        "        |",
        " 15  Wafer sort + packaging     Test/OSAT        Probe results, packaged parts",
        "        |",
        " 16  Final test + bring-up      Test, validation Test program, first-silicon rpt",
        "        |",
        " 17  Char., qual, production    Product eng.     Datasheet, qual report, PPAP",
    ], "The end-to-end ASIC flow with owners and hand-offs. Stages 4-12 run "
       "with heavy overlap and iteration.")
    p("The front end (stages 2-7, Part II of this book) turns a "
      "specification into a verified gate-level netlist. The back end "
      "(stages 8-13, Parts III and IV) turns the netlist into polygons on "
      "masks. Post-silicon (stages 14-17, Part V) turns masks into "
      "qualified, tested parts in customers' hands.")
    h3("The files that move between teams")
    tbl(["File / format", "What it carries", "Produced by -> used by"], [
        ["Verilog/SystemVerilog RTL", "Behaviour at register-transfer level",
         "RTL -> DV, synthesis, DFT, emulation"],
        ["SDC", "Timing constraints: clocks, I/O delays, exceptions",
         "RTL/arch -> synthesis, PD, STA"],
        ["UPF (IEEE 1801)", "Power intent: domains, switches, isolation, "
         "retention", "Arch/RTL -> DV, synthesis, PD, sign-off"],
        ["Liberty (.lib/.db)", "Cell timing, power, function", "Library/IP "
         "vendor -> synthesis, STA, power"],
        ["LEF", "Abstract cell/macro geometry, routing layers",
         "Library/IP vendor -> PD"],
        ["Gate-level netlist (.v)", "Cells and nets", "Synthesis/DFT -> PD, "
         "LEC, gate-level sim"],
        ["DEF / OpenDB / tool DB", "Placement, routing, floorplan",
         "PD -> PD, extraction"],
        ["SPEF", "Extracted parasitics (R, C)", "Extraction -> STA, power"],
        ["SDF", "Annotated delays", "STA -> gate-level timing simulation"],
        ["GDSII / OASIS", "Final mask polygons", "PD -> PV, foundry"],
        ["STIL / WGL", "Test patterns", "ATPG -> tester"],
    ], widths=[2.1, 3.3, 3.0], bold_first=True,
       caption="Hand-off files. Appendix A has a format reference.")

    h2("What a typical project schedule looks like")
    p("Schedules vary enormously - a small mature-node mixed-signal chip "
      "can take 12 months with a team of ten, a flagship SoC 24-36 months "
      "with hundreds - but the shape is always the same: long front-end "
      "and verification, overlapping back-end, a fixed fab cycle and a "
      "bring-up/qualification tail.")
    diagram([
        "  Month:        0    3    6    9    12   15   18   21   24   27   30",
        "                |----|----|----|----|----|----|----|----|----|----|",
        "  Spec/arch     ########",
        "  RTL                ###############~~~~~          (~ = bug fixes/ECO)",
        "  Verification         #######################~~~",
        "  DFT                          ########",
        "  Synth + PD trial                ######",
        "  PD final                             ##########",
        "  Sign-off/tapeout                              ####  TO",
        "  Fab (+ masks)                                     ######",
        "  Package/test dev                     ###############",
        "  Bring-up + validation                                   #######",
        "  Char./qual/ramp                                              ######",
    ], "An illustrative 30-month schedule for a mid-size SoC. The critical "
       "path is almost always verification -> sign-off -> fab.")
    box("tip", "Milestones you will hear about",
        ["**Arch freeze / spec freeze**: features locked. **RTL freeze** "
         "(or 'RTL 0.9/1.0'): all features coded, only bug fixes after. "
         "**Netlist freeze**: only ECOs after. **Tapeout (TO)**: GDSII sent "
         "to the foundry. **First silicon / A0**: first wafers back. "
         "**ES / CS / MP**: engineering samples, customer samples, mass "
         "production. Stepping names such as A0, A1, B0 identify silicon "
         "revisions: a metal-only fix usually bumps the number (A0 -> A1), "
         "a base-layer change bumps the letter (A1 -> B0)."])

    h2("Who does what: the roles in an ASIC team")
    tbl(["Role", "Main responsibility", "Key skills", "Chapters"], [
        ["Architect", "Features, performance/power targets, partitioning",
         "Modelling, workloads, system trade-offs", "1, 5, 23"],
        ["RTL / design engineer", "Micro-architecture and RTL of blocks",
         "SV, timing-aware RTL, CDC, low power", "5, 6, 11"],
        ["Design verification (DV)", "Prove the RTL matches the spec",
         "UVM, SVA, coverage, formal", "7"],
        ["DFT engineer", "Scan, ATPG, compression, MBIST, JTAG",
         "Test theory, fault models, test protocols", "10, 21"],
        ["Synthesis / STA engineer", "Netlist, constraints, timing sign-off",
         "SDC, Liberty, OCV, corners", "4, 8, 9, 18"],
        ["Physical design (PD)", "Floorplan to GDSII for blocks/top",
         "P&R tools, CTS, routing, ECO", "13-17, 19"],
        ["Power integrity / PV", "IR drop, EM, DRC, LVS, ERC",
         "Extraction, rule decks, debugging layout", "3, 18"],
        ["Low-power / UPF", "Power intent and its verification",
         "IEEE 1801, power analysis", "11"],
        ["Analog / mixed-signal", "PLLs, ADCs, regulators, I/O, ESD",
         "Circuit design, SPICE, layout", "2, 12"],
        ["Package / SI-PI", "Package, substrate, signal/power integrity",
         "3D EM, thermal", "20"],
        ["Test / product engineer", "Test programs, yield, qualification",
         "ATE, statistics, reliability", "21, 22"],
        ["Post-silicon validation", "Bring-up, debug, characterisation",
         "Lab, firmware, debug infrastructure", "22"],
        ["CAD / methodology", "Flows, scripts, tool infrastructure",
         "Tcl/Python, EDA internals", "13, 23, 24"],
    ], widths=[1.9, 2.8, 2.6, 0.9], bold_first=True)

    h2("Roadmap: how this book is organised")
    tbl(["Part", "Chapters", "What you learn", "Most relevant to"], [
        ["I Foundations", "1-5", "Flow and economics, device physics, "
         "fabrication and PDKs, libraries and IP, spec to architecture",
         "Everyone"],
        ["II Front-End", "6-10", "RTL for implementation, verification "
         "strategy, synthesis, STA, DFT", "RTL, DV, synthesis, STA, DFT"],
        ["III Power, AMS, PD setup", "11-14", "UPF, mixed-signal/I/O/ESD, "
         "PD data and flows, floorplan and power grid", "Low-power, AMS, PD"],
        ["IV Implementation and sign-off", "15-19", "Placement, CTS, "
         "routing/SI, sign-off, ECO, tapeout and masks", "PD, STA, PV"],
        ["V After tapeout", "20-23", "Packaging and chiplets, test/yield/"
         "reliability, bring-up and qualification, methodology and "
         "economics", "Test, product, validation, management"],
        ["VI Practice and roadmap", "24-26", "Open-source flow, full case "
         "study, career and interviews", "Everyone"],
    ], widths=[1.8, 0.9, 3.8, 2.0], bold_first=True)
    p("RTL coding style, SystemVerilog language details and on-chip "
      "protocols (AXI, APB, PCIe and friends) are covered in the companion "
      "RTL Design, Verilog & SystemVerilog and Communication Protocols "
      "guides; this book focuses on everything else and on how the whole "
      "flow fits together.")

    h2("Summary")
    bul([
        "An ASIC is a chip built for a specific application; an SoC "
        "integrates processors, memory, interconnect and peripherals into one "
        "die; an ASSP is an application-specific chip sold to many customers.",
        "Design styles trade NRE and turnaround against density, speed and "
        "power: full custom > standard cell > structured ASIC/gate array > "
        "FPGA. Almost every digital SoC is standard-cell logic plus "
        "custom/compiled macros and hard IP.",
        "The ASIC decision is driven by volume (NRE amortisation), hard PPA "
        "requirements and specification stability; compute the break-even "
        "volume V* = dNRE / dC_unit, and include re-spin risk.",
        "The industry is layered: fabless designers, foundries, IDMs, IP and "
        "EDA vendors, mask shops and OSATs.",
        "The flow runs spec -> architecture -> RTL -> verification -> "
        "synthesis -> DFT -> floorplan -> place -> CTS -> route -> sign-off -> "
        "tapeout -> fab -> package -> test -> bring-up -> production, with "
        "well-defined owners and hand-off files (RTL, SDC, UPF, Liberty, "
        "LEF, netlist, DEF, SPEF, GDSII, test patterns).",
    ])
    h2("Exercises")
    bul([
        "Using breakeven.py, find the break-even volume between the 28 nm "
        "ASIC and the FPGA if the ASIC needs one full re-spin (add $3M to "
        "its NRE). How sensitive is the answer to the FPGA unit price?",
        "List three products for which an FPGA is the right answer even at "
        "high volume, and explain why in terms of the three questions in "
        "Section 1.4.",
        "For each stage of the flow diagram, name one thing that can force "
        "an iteration back to RTL.",
        "Explain why a metal-only ECO is cheaper and faster than a base-layer "
        "change, and which stepping name each would produce.",
        "A start-up has $20M of funding. Sketch the NRE budget of a 28 nm "
        "mixed-signal SoC (engineering, EDA, IP, masks, package, test, "
        "qualification) and decide whether a re-spin is affordable.",
    ], ordered=True)


# =============================================================================
#  Chapter 2 - Semiconductor device fundamentals
# =============================================================================
def _ch2():
    chapter("Semiconductor Device Fundamentals: MOSFETs, CMOS, Delay, Power "
            "and Scaling")
    p("Every number an ASIC engineer works with - a cell delay in a "
      "Liberty table, a leakage figure in a power report, the supply "
      "voltage of a low-power mode, the reason a hold violation appears "
      "only at the fast corner - comes from the physics of the MOSFET. You "
      "do not need to be a device physicist, but you do need a correct "
      "mental model of how a transistor conducts, what makes it fast or "
      "leaky, and how that changed as transistors went from planar to "
      "FinFET to nanosheet. This chapter builds that model and connects it "
      "to the gate-level quantities used everywhere else in the book.")

    h2("Silicon, doping and the pn junction")
    p("Silicon has four valence electrons and forms a diamond-cubic "
      "crystal. At room temperature pure (intrinsic) silicon has very few "
      "free carriers - about 10^{10} per cm^{3} - so it is a poor conductor. "
      "Its **band gap** (about 1.12 eV) is the energy an electron needs to "
      "break free from a bond into the conduction band, leaving a mobile "
      "'hole' behind.")
    p("**Doping** replaces a tiny fraction of silicon atoms with impurities. "
      "Group-V donors (phosphorus, arsenic) add a free electron: **n-type**. "
      "Group-III acceptors (boron) create a hole: **p-type**. Typical "
      "doping levels are 10^{15} to 10^{20} atoms/cm^{3}, i.e. from about one "
      "in ten million to one in a few hundred silicon atoms, and they "
      "change conductivity by many orders of magnitude.")
    p("Where p-type meets n-type, electrons and holes diffuse across and "
      "recombine, leaving a **depletion region** of fixed ionised dopants "
      "and a built-in potential (roughly 0.6-0.9 V). Forward bias shrinks "
      "the barrier and current grows exponentially (the diode equation "
      "I = I_{s}(e^{V/(n kT/q)} - 1)); reverse bias widens the depletion "
      "region and only a small leakage flows. Every MOSFET contains two "
      "such junctions (source-body and drain-body) that must stay reverse "
      "biased - which is why the p-substrate is tied to the lowest supply "
      "and n-wells to the highest, through the **tap cells** of Chapter 4. "
      "The parasitic pnpn structure formed by neighbouring n- and "
      "p-MOSFETs can latch up into a low-impedance path if those taps are "
      "too far apart; the foundry's latch-up rules set the maximum tap "
      "spacing.")

    h2("The MOSFET: structure and operation")
    p("A metal-oxide-semiconductor field-effect transistor has four "
      "terminals: **gate**, **source**, **drain** and **body** (bulk). In "
      "an nMOS device the source and drain are heavily n-doped regions in "
      "a p-type body. The gate sits on a thin insulator above the channel "
      "region between them. A positive gate voltage attracts electrons to "
      "the surface; above the **threshold voltage** Vth the surface "
      "inverts to n-type and forms a conducting channel from source to "
      "drain. A pMOS device is the complement: p+ source/drain in an "
      "n-well, conducting when the gate is pulled below the source by more "
      "than |Vth|.")
    diagram([
        "                         gate (G)",
        "                            |",
        "        source (S)   +-------------+    drain (D)",
        "            |        | metal gate  |       |",
        "            |        +-------------+       |",
        "      ======|=====   | high-k oxide|  =====|=====   <- spacers / contacts",
        "   +--------v--------+-------------+-------v--------+",
        "   |    n+ source    |  channel    |    n+ drain    |",
        "   |   ++++++++++++  |  -- -- -- - |  ++++++++++++  |  <- inversion layer",
        "   |                    (L = gate length)           |     when Vgs > Vth",
        "   |                p-type body / p-well            |",
        "   +------------------------------------------------+",
        "                            |",
        "                        body (B) -> tied to VSS via tap cells",
    ], "Cross-section of a planar nMOS transistor. W (width) is into the page.")
    h3("Regions of operation")
    tbl(["Region", "Condition (nMOS)", "Behaviour", "Where it matters"], [
        ["Cutoff / subthreshold", "Vgs < Vth", "Only weak diffusion current, "
         "exponential in Vgs", "Leakage power, retention, sleep modes"],
        ["Linear (triode)", "Vgs > Vth, Vds < Vgs - Vth",
         "Acts like a voltage-controlled resistor", "On-resistance of a "
         "switch, pass gates, power switches"],
        ["Saturation", "Vgs > Vth, Vds >= Vgs - Vth",
         "Current roughly independent of Vds (pinch-off / velocity "
         "saturation)", "Charging and discharging loads: gate delay"],
    ], widths=[1.6, 2.0, 2.6, 2.4], bold_first=True)
    h3("The square-law (long-channel) model")
    eq(["Linear:      Id = mu Cox (W/L) [ (Vgs - Vth) Vds - Vds^2 / 2 ]",
        "Saturation:  Id = (1/2) mu Cox (W/L) (Vgs - Vth)^2 (1 + lambda Vds)",
        "",
        "mu = carrier mobility, Cox = eps_ox / t_ox (gate capacitance per area),",
        "lambda = channel-length modulation"],
       "Shockley square-law model. Accurate for long channels only.")
    p("Two consequences are worth memorising. Current is proportional to "
      "**W/L**, which is why wider transistors (or more fins) drive harder "
      "and why cells come in drive strengths x1, x2, x4... And electrons "
      "have roughly 2-3x the mobility of holes in bulk silicon, which is "
      "why planar pMOS devices were made wider than nMOS to balance rise "
      "and fall. (In FinFETs strain engineering narrows the gap, so "
      "modern cells often use equal fin counts.)")
    h3("Velocity saturation and the alpha-power law")
    p("In short channels the lateral field is so high that carriers reach "
      "a saturation velocity (about 10^{7} cm/s in silicon) before the "
      "drain. Current then grows roughly linearly, not quadratically, with "
      "overdrive. Sakurai and Newton's **alpha-power law** captures this "
      "with a fitted exponent alpha between 1 (fully velocity saturated) "
      "and 2 (square law); modern devices are typically around 1.1-1.4.")
    eq(["Id,sat = K (W/L) (Vgs - Vth)^alpha            1 < alpha < 2",
        "t_d  ~  C_L * Vdd / Id,sat  ~  C_L * Vdd / (Vdd - Vth)^alpha"],
       "Alpha-power law and the resulting gate-delay dependence on supply.")
    code(L(SRC_ALPHA), caption="alpha.py - normalised delay, energy and "
         "energy-delay product versus Vdd.")
    out(L(OUT_ALPHA), caption="Real output of alpha.py.")
    p("The table shows the essence of voltage scaling: dropping from 0.8 V "
      "to 0.6 V costs about 60 % in speed but saves 44 % of switching "
      "energy; the energy-delay product is flat over a wide range, which "
      "is why DVFS (Chapter 11) is so effective. It also shows that at low "
      "voltage the same 30 mV threshold shift hurts delay two and a half "
      "times more than at nominal - the reason near-threshold designs "
      "suffer badly from variation and why low-voltage corners dominate "
      "sign-off for such designs.")

    h2("Threshold voltage, body effect and subthreshold conduction")
    p("Vth is set by the gate work function, the channel doping and the "
      "oxide. Foundries offer several **threshold flavours** of the same "
      "transistor - typically ULVT, LVT, SVT (RVT) and HVT - by changing "
      "the work-function metal or implants. Lower Vth means faster and "
      "leakier devices (see below).")
    h3("Body effect")
    p("If the source is above the body (as in the upper nMOS of a stack), "
      "the depletion charge increases and Vth rises:")
    eq(["Vth = Vth0 + gamma ( sqrt(2 phi_F + Vsb) - sqrt(2 phi_F) )"],
       "Body effect. gamma = body-effect coefficient, phi_F = Fermi potential.")
    p("The body effect is why stacked transistors are slower, and it is "
      "the physical basis of **body biasing** (Section 2.11): applying a "
      "reverse body bias raises Vth and cuts leakage, forward body bias "
      "lowers Vth and speeds the device up. In FinFETs the thin, fully "
      "depleted fin makes the body effect weak, so body biasing is "
      "largely ineffective there.")
    h3("Subthreshold conduction and the 60 mV/decade limit")
    p("Below Vth the transistor does not switch off abruptly. Current "
      "flows by diffusion and falls exponentially with gate voltage:")
    eq(["Id,sub = I0 * 10^( (Vgs - Vth) / S )",
        "S = n * (kT/q) * ln(10)     [mV per decade of current]",
        "kT/q = 25.9 mV at 300 K  ->  S >= 59.6 mV/dec at 300 K (n = 1)"],
       "Subthreshold swing. n >= 1 depends on how well the gate controls the channel.")
    p("S is the gate voltage needed to change the off-current by 10x. Its "
      "theoretical minimum at room temperature is about 60 mV/decade "
      "(n = 1), set by the Boltzmann distribution of carriers - no "
      "conventional MOSFET can beat it, which is the fundamental reason "
      "supply voltage stopped scaling. Planar bulk devices at advanced "
      "nodes degraded to 90-100 mV/dec; FinFETs and nanosheets recover "
      "roughly 65-75 mV/dec because the gate wraps the channel.")
    code(L(SRC_LEAK), caption="leak.py - subthreshold swing versus temperature, "
         "and off-current versus Vth.")
    out(L(OUT_LEAK), caption="Real output of leak.py.")
    box("key", "The rule of thumb every power engineer uses",
        "With S around 75-100 mV/dec, each 100 mV reduction of Vth costs "
        "roughly 10-20x more subthreshold leakage, and leakage grows "
        "strongly with temperature (both kT/q and Vth itself change). This "
        "is why HVT cells are the default in leakage-sensitive designs and "
        "why leakage is always signed off at the hot corner.")
    h3("Other leakage mechanisms")
    bul([
        "**Gate leakage**: tunnelling through the gate dielectric. It "
        "exploded with 1-2 nm SiO_{2} and was tamed by high-k/metal-gate "
        "(HKMG) stacks from the 45 nm generation onward.",
        "**Junction leakage and GIDL** (gate-induced drain leakage): "
        "band-to-band tunnelling at the heavily doped drain, worse at high "
        "Vdg; it limits how far reverse body bias can reduce leakage.",
        "**Punch-through**: in very short channels the source and drain "
        "depletion regions merge.",
    ])

    h2("Short-channel effects and DIBL")
    p("As L shrinks, the drain's electric field reaches into the channel "
      "and helps the gate to lower the source barrier. The results are "
      "collectively called **short-channel effects**:")
    bul([
        "**Vth roll-off**: Vth decreases as L decreases, so gate-length "
        "variation becomes Vth variation (and leakage variation).",
        "**DIBL** (drain-induced barrier lowering): Vth drops as Vds "
        "rises, typically quoted in mV/V (tens of mV/V in a good FinFET, "
        "much more in a poor planar device). High DIBL means high off "
        "current at full Vds and poor output resistance.",
        "**Channel-length modulation**: the pinch-off point moves, so "
        "saturation current keeps rising with Vds.",
        "**Mobility degradation** from high vertical fields and **velocity "
        "saturation** from high lateral fields (previous section).",
        "**Hot-carrier injection** (HCI): energetic carriers damage the "
        "oxide near the drain, shifting Vth over the lifetime (Chapter 21).",
    ])
    p("Good electrostatic control - the gate dominating the channel "
      "potential rather than the drain - is the single goal behind every "
      "device-architecture change from planar to FinFET to gate-all-around "
      "(Section 2.10).")

    h2("The CMOS inverter")
    p("Complementary MOS combines a pMOS pull-up and an nMOS pull-down. In "
      "either stable state one device is off, so ideally no static current "
      "flows - the property that made CMOS the dominant logic family.")
    diagram([
        "            Vdd                       Vout",
        "             |                       ^",
        "          |--+  pMOS              Vdd|*******",
        "  Vin ---o|                          |       *",
        "     |    |--+                       |        *   <- both devices on:",
        "     |       +------ Vout            |         *     high gain region",
        "     |    |--+                       |          *",
        "     +----|     nMOS                 |           *******",
        "          |--+                       +---+-------+-------+--> Vin",
        "             |                          VIL     VM      VIH   Vdd",
        "            Vss",
    ], "CMOS inverter and its voltage-transfer characteristic (VTC).")
    p("The **switching threshold** VM is the input voltage where Vout = Vin; "
      "it is centred (VM = Vdd/2) when pull-up and pull-down strengths are "
      "equal. The unity-gain points VIL and VIH (where dVout/dVin = -1) "
      "define the **noise margins**:")
    eq(["NM_H = VOH - VIH          NM_L = VIL - VOL",
        "(for a full-swing CMOS gate VOH = Vdd, VOL = 0)"],
       "Noise margins: how much noise a logic level can absorb.")
    p("Because each CMOS gate restores levels to the rails, noise does not "
      "accumulate along a logic path. Noise-margin erosion from crosstalk "
      "and supply droop is nevertheless a sign-off concern (Chapters 17-18), "
      "and low-voltage designs must check that margins survive local "
      "variation - the classic failure being an SRAM or a latch that no "
      "longer flips.")

    h2("Switching delay: RC and Elmore")
    p("To first order a switching transistor is an effective resistance "
      "R_{eff} charging or discharging a capacitance C_{L} made of the "
      "next gates' input capacitance, the wire, and the driver's own "
      "drain (parasitic) capacitance. For a step input the 50 % delay of "
      "a single RC is ln(2) RC = 0.69 RC.")
    p("For an RC tree (a wire with branches, or a transistor stack) the "
      "**Elmore delay** is a simple, pessimistic but surprisingly good "
      "estimate: sum over every capacitor the capacitance times the "
      "resistance shared between the source-to-output path and the "
      "source-to-that-capacitor path.")
    eq(["t_Elmore(out) = sum_k  C_k * R_shared(k, out)",
        "Uniform wire of length l (r, c per unit length):  t = r c l^2 / 2",
        "Driver R_d + wire + load C_L:  t = R_d (c l + C_L) + r l (c l / 2 + C_L)"],
       "Elmore delay. The quadratic l^2 term is why long wires need repeaters.")
    code(L(SRC_ELMORE), caption="elmore.py - Elmore delay of a driver "
         "driving a distributed RC wire (generic thin-metal values).")
    out(L(OUT_ELMORE), caption="Real output of elmore.py.")
    p("Up to a few hundred microns the driver resistance dominates; beyond "
      "that the wire's own r c l^{2}/2 grows quadratically and takes over. "
      "Inserting repeaters makes delay linear in length again - optimum "
      "repeater spacing is a classic physical-design calculation revisited "
      "in Chapters 15 and 17. STA tools use more accurate models than "
      "Elmore (effective capacitance, current-source models, Chapter 9), "
      "but Elmore remains the right mental model and the basis of many "
      "placement and CTS heuristics.")

    h2("Logical effort: sizing a path by hand")
    p("Sutherland and Sproull's **logical effort** method expresses the "
      "delay of a gate, in units of tau (the delay of an ideal inverter "
      "driving an identical inverter with no parasitics), as:")
    eq(["d = g * h + p",
        "g = logical effort  (input cap / inverter input cap for equal drive)",
        "h = electrical effort = C_out / C_in        p = parasitic delay",
        "",
        "Path:  G = prod g_i,  B = prod b_i (branching),  H = C_load / C_in",
        "       F = G B H,  optimal stage effort f = F^(1/N),",
        "       D_min = N F^(1/N) + P,  best N ~ log_4(F)"],
       "Logical effort. With a pMOS/nMOS mobility ratio of 2: g(INV) = 1, "
       "g(NAND2) = 4/3, g(NOR2) = 5/3, g(NAND3) = 5/3.")
    p("The key result is that a path is fastest when every stage bears the "
      "same effort f, and that the optimal f is about 4 (the famous "
      "'fanout-of-4', FO4). The worked example sizes a four-stage path "
      "INV -> NAND2 -> NOR2 -> INV driving a load 64x its input capacitance:")
    code(L(SRC_LE), caption="le.py - logical-effort sizing of a four-stage path.")
    out(L(OUT_LE), caption="Real output of le.py.")
    p("Each stage gets an effort of 3.45 and the minimum path delay is "
      "19.8 tau; sizes grow geometrically towards the load. Since log_{4}(F) "
      "is 3.6, four stages is close to optimal; forcing it into two stages "
      "would need a stage effort near 12 and be much slower. Synthesis "
      "and placement tools do this sizing automatically, but logical "
      "effort explains __why__ they insert buffers, why high-fanout nets "
      "become buffer trees and why NOR-heavy logic is slow.")
    box("expert", "FO4 delay as a technology yardstick",
        "Designers quote cycle times in FO4 inverter delays because the "
        "number is roughly technology independent: a high-performance CPU "
        "pipeline stage is on the order of 10-20 FO4, a relaxed ASIC "
        "pipeline 30-60 FO4. Knowing the FO4 delay of your library at the "
        "sign-off corner lets you sanity-check a target frequency before "
        "writing any RTL (Chapter 5).")

    h2("Power: dynamic, short-circuit and leakage")
    eq(["P_total = P_dynamic + P_short-circuit + P_leakage",
        "P_dynamic  = alpha * C_sw * Vdd^2 * f          (alpha = activity factor)",
        "P_short    ~ proportional to input slew, Vdd and f (both devices briefly on)",
        "P_leakage  = Vdd * (I_sub + I_gate + I_junction/GIDL)",
        "Energy per transition from the supply = C Vdd^2 (half stored, half burned)"],
       "The three components of CMOS power.")
    p("**Dynamic power** dominates active operation: every 0 -> 1 "
      "transition draws C Vdd^{2} from the supply, half dissipated in the "
      "pull-up, and the stored half is dissipated in the pull-down on the "
      "next 1 -> 0 transition. The quadratic dependence on Vdd makes "
      "voltage the strongest power lever; clock gating attacks alpha; "
      "careful floorplanning attacks wire C. **Short-circuit power** is "
      "usually 5-10 % of dynamic if slews are controlled - one reason "
      "Liberty libraries impose max_transition limits. **Leakage** flows "
      "whenever the chip is powered, dominates in standby, and rises "
      "steeply with temperature; it is attacked with HVT cells, power "
      "gating and body bias (Chapter 11). In Liberty, dynamic power appears "
      "as internal-power tables plus switching of the load, and leakage "
      "as state-dependent leakage_power values (Chapter 4).")

    h2("Scaling: Dennard and its end")
    p("In 1974 Dennard et al. showed that if all dimensions and voltages "
      "shrink by a factor k (about 1.4 per generation), transistors get "
      "faster by k, density rises by k^{2}, and power density stays "
      "constant. For thirty years this 'free lunch' powered the industry.")
    tbl(["Quantity", "Ideal Dennard scaling", "Post-2005 reality"], [
        ["Dimensions (L, W, t_ox)", "1/k", "Scaled, but gate oxide stalled "
         "(replaced by high-k)"],
        ["Supply Vdd", "1/k", "Nearly flat around 0.7-1.0 V (subthreshold "
         "slope limit, variation)"],
        ["Vth", "1/k", "Cannot drop without exponential leakage"],
        ["Density", "k^2", "Still improves, but more slowly and via "
         "DTCO tricks (fewer tracks, backside power)"],
        ["Gate delay", "1/k", "Modest gains; wires increasingly dominate"],
        ["Power density", "Constant", "Rises -> 'dark silicon', power-"
         "limited design"],
    ], widths=[2.0, 2.0, 4.0], bold_first=True)
    p("Once Vdd stopped scaling (roughly the 90-65 nm era), power density "
      "rose and frequency plateaued. The industry responded with "
      "multi-core, specialised accelerators, aggressive power management "
      "(clock and power gating, DVFS), and new device structures. Wire "
      "resistance also rises sharply as cross-sections shrink (Chapter 3), "
      "so interconnect, not transistors, often limits performance today.")

    h2("Device architectures: planar, FinFET, GAA/nanosheet, CFET")
    diagram([
        "  PLANAR (bulk)          FinFET                 GAA / NANOSHEET        CFET",
        "                                                                   (stacked n/p)",
        "   gate on top          gate wraps 3 sides     gate wraps all 4       nFET sheets",
        "  +----------+           +--+   +--+            +-------------+       over pFET",
        "  |   gate   |        +--|  |---|  |--+         | ==sheet==   |       sheets",
        "  +----------+        |  |f |   |f |  |         | ==sheet==   |       +-------+",
        "  ~~channel~~         |  |i |   |i |  |         | ==sheet==   |       | n n n |",
        "   substrate          |  |n |   |n |  |         +-------------+       | p p p |",
        "                      +--+--+---+--+--+          sheets stacked       +-------+",
        "  Control: 1 side      Control: 3 sides        Control: 4 sides      Footprint /2",
        "  <= 28/20 nm          22/16 nm .. 3 nm        ~3/2 nm and below     research",
    ], "Evolution of the transistor for better electrostatic control.")
    tbl(["Architecture", "Key idea", "Design implications"], [
        ["Planar bulk", "Gate above a flat channel", "Continuous W; body "
         "biasing works; poor control below ~28/20 nm"],
        ["FD-SOI (planar)", "Very thin silicon on buried oxide", "Good "
         "control without fins; strong body bias via back gate"],
        ["FinFET", "Channel is a vertical fin; gate on three sides",
         "Width quantised in fins; cells sized in fins; strong drive, low "
         "leakage; higher gate/parasitic capacitance; self-heating"],
        ["GAA / nanosheet (RibbonFET, MBCFET)", "Stacked horizontal "
         "sheets surrounded by gate", "Sheet width is variable again; better "
         "control; often paired with backside power delivery"],
        ["CFET", "nFET stacked on pFET", "Roughly halves cell footprint; "
         "research/early development"],
    ], widths=[2.0, 2.6, 4.0], bold_first=True)
    p("For the ASIC engineer, the practical consequences are: in FinFET "
      "nodes transistor width comes in integer fins, so drive strengths "
      "and cell heights are quantised; parasitic capacitance and wire "
      "resistance matter more than intrinsic device speed; and "
      "__self-heating__ and electromigration limits are tighter "
      "(Chapter 18).")

    h2("Multi-Vt, SOI/FD-SOI and body bias")
    p("**Multi-Vt design** is the most widely used leakage technique: "
      "synthesis and placement use LVT/ULVT cells on critical paths and "
      "HVT/SVT everywhere else. Typical ratios per Vt step are roughly "
      "2-3x in leakage and 10-20 % in delay, but these vary by node. "
      "Most flows cap the fraction of LVT/ULVT cells (for example a few "
      "percent to twenty percent) and track it as a design metric.")
    p("**Silicon-on-insulator** places the transistor in a thin silicon "
      "layer on a buried oxide (BOX). **FD-SOI** (fully depleted, e.g. 28 nm "
      "and 22 nm offerings) uses a film only a few nanometres thick, so "
      "the channel is fully depleted and short-channel control is good. "
      "Because the BOX is thin, the substrate under it acts as a second "
      "gate: **body bias** can shift Vth by tens of mV per volt over a "
      "wide range (on the order of +-1 V or more in some flavours, far beyond "
      "what junction limits allow in bulk). This allows forward body bias "
      "for speed in active mode and reverse body bias for low leakage in "
      "standby, or compensation of process corners after manufacture - a "
      "powerful knob for IoT and automotive designs.")
    box("warn", "PITFALL: assuming body bias works everywhere",
        "Body bias is strong in FD-SOI, moderate in older planar bulk and "
        "weak in FinFET/GAA. Also, bias generators, well isolation (deep "
        "n-well), extra bias pins on every cell (the VPB/VNB pins seen in "
        "the SKY130 LEF in Chapter 4) and multi-bias sign-off corners all "
        "cost area and schedule. Decide at architecture time (Chapter 5).")

    h2("Summary")
    bul([
        "Doping creates n and p regions; pn junctions must be kept reverse "
        "biased with well/substrate taps, and tap spacing prevents latch-up.",
        "A MOSFET works in cutoff, linear or saturation. The square law "
        "fails in short channels; the alpha-power law t_d ~ C Vdd / "
        "(Vdd - Vth)^alpha captures velocity saturation and explains why "
        "low-voltage operation is slow and variation-sensitive.",
        "Subthreshold swing cannot beat ~60 mV/dec at room temperature, so "
        "every 100 mV of Vth trades ~10-20x in leakage; leakage rises "
        "steeply with temperature.",
        "DIBL and other short-channel effects drove the move from planar to "
        "FinFET to GAA; CFET is next.",
        "Gate delay is R_eff x C_load to first order; Elmore delay handles "
        "RC trees and shows quadratic wire delay; logical effort sizes paths "
        "for minimum delay (equal stage effort ~4).",
        "Power = alpha C Vdd^2 f + short-circuit + leakage. Dennard scaling "
        "ended when Vdd and Vth stopped scaling.",
        "Multi-Vt libraries, FD-SOI body bias and power gating are the main "
        "device-level power knobs.",
    ])
    h2("Exercises")
    bul([
        "Using alpha.py, find the Vdd that minimises the energy-delay "
        "product for alpha = 1.3 and Vth = 0.35 V. How does it move if Vth "
        "is 0.25 V?",
        "A design has 20 mW of leakage at 25 deg C with S = 80 mV/dec. "
        "Estimate the leakage change if all cells are swapped from a "
        "Vth of 0.30 V to 0.38 V. What else changes?",
        "Size a path NAND2 -> INV -> NAND3 -> INV driving 100x the input "
        "capacitance with logical effort. Would adding two more inverters help?",
        "Compute the Elmore delay at the far end of a 2 mm wire (2 ohm/um, "
        "0.2 fF/um) driven by a 1 kohm driver, then with one repeater "
        "(same driver) at the midpoint. Ignore the repeater's own delay first, "
        "then add 20 ps.",
        "Explain, using the subthreshold-swing limit, why supply voltage "
        "stopped scaling while dimensions kept shrinking.",
        "Why is body biasing ineffective in FinFETs but effective in FD-SOI?",
    ], ordered=True)


# =============================================================================
#  Chapter 3 - Process technology and fabrication
# =============================================================================
def _ch3():
    chapter("Process Technology and Fabrication: Wafers, Lithography, "
            "FEOL/MEOL/BEOL, Design Rules, PDKs and Variation")
    p("A design engineer never touches a wafer, yet the fab shapes every "
      "decision: the design rules that the router must obey, the metal "
      "stack that sets wire delay, the variation that sets timing "
      "margins, the density rules that force fill, the mask count that "
      "sets NRE. This chapter walks through how a chip is actually made, "
      "then through what the foundry hands the design team - the process "
      "design kit - and how manufacturing variation is modelled.")

    h2("From sand to wafers")
    p("Chip-grade silicon starts as quartz sand reduced to metallurgical "
      "silicon, purified through a gas phase (trichlorosilane) to "
      "'eleven nines' (99.999999999 %) polysilicon, then melted and grown "
      "into a single-crystal **ingot** by the Czochralski process: a seed "
      "crystal is dipped into the melt and slowly pulled and rotated. "
      "Dopant added to the melt sets the substrate type (lightly p-type "
      "for most CMOS). The ingot is ground to diameter, notched to mark "
      "the crystal orientation, sliced with wire saws into wafers "
      "(about 775 um thick for 300 mm), then lapped, etched and "
      "polished to a mirror finish. Some processes add an epitaxial layer "
      "or use SOI wafers (Chapter 2).")
    tbl(["Wafer diameter", "Typical use today"], [
        ["150 mm (6 in)", "Power, MEMS, compound semiconductors, old analog"],
        ["200 mm (8 in)", "Mature nodes (350-90 nm): analog, power, "
         "sensors, many automotive and IoT parts"],
        ["300 mm (12 in)", "All leading-edge logic and memory, and many "
         "mature nodes (e.g. 65-28 nm). Area is 2.25x a 200 mm wafer."],
    ], widths=[1.4, 5.0], bold_first=True)
    p("Wafers are processed in **cleanrooms** in which the air is filtered "
      "to ISO class 1-5 levels (a few particles of 0.1 um or larger per cubic "
      "metre in the best areas), temperature and humidity are tightly "
      "controlled, and lithography bays use yellow light. Modern 300 mm "
      "fabs move wafers in sealed pods (FOUPs) on overhead transport so "
      "that the wafer itself sees an even cleaner mini-environment. A "
      "leading-edge wafer passes through well over a thousand process "
      "steps and spends roughly three months or more in the fab.")

    h2("The unit processes")
    p("Every structure on a chip is made by repeating a handful of unit "
      "processes: add material, pattern it, remove material, modify it, "
      "and flatten.")
    tbl(["Process", "What it does", "Examples"], [
        ["Oxidation", "Grow SiO_{2} by heating in O_{2}/H_{2}O", "Pad oxide, "
         "legacy gate oxide, liners"],
        ["Deposition", "Add thin films: CVD, PECVD, ALD (atomic-layer, "
         "angstrom control), PVD/sputtering, electroplating, epitaxy",
         "High-k by ALD, barrier/seed by PVD, copper by electroplating, "
         "SiGe S/D by epitaxy"],
        ["Lithography", "Transfer a mask pattern into photoresist", "Every "
         "patterned layer (Section 3.3)"],
        ["Etch", "Remove material where resist is open. Dry (plasma, "
         "anisotropic) or wet (isotropic)", "Fin etch, gate etch, via and "
         "trench etch"],
        ["Ion implantation", "Accelerate dopant ions into the silicon, "
         "then anneal to activate and repair damage", "Wells, Vt adjust, "
         "source/drain extensions, halos"],
        ["Anneal", "Heat to activate dopants (rapid thermal, spike, laser)",
         "After implants; thermal budget limits later steps"],
        ["CMP", "Chemical-mechanical polishing: planarise the wafer",
         "After STI fill, after every copper layer"],
        ["Clean / metrology", "Remove particles and residues; measure "
         "thickness, CD, overlay, defects", "Between almost all steps"],
    ], widths=[1.4, 3.6, 3.2], bold_first=True)

    h2("Photolithography")
    p("Lithography is the most expensive and most critical step. A wafer "
      "is coated with photoresist, exposed through a **photomask** (reticle) "
      "in a scanner that projects a reduced (typically 4x) image, then "
      "developed so that the pattern remains in resist. Etch or implant "
      "then transfers the pattern into the wafer. A scanner exposes one "
      "field (at most 26 mm x 33 mm for standard 4x systems - this "
      "**reticle limit** caps the size of a single die, about 858 mm^{2}) "
      "then steps to the next.")
    eq(["Resolution (half-pitch)  R = k1 * lambda / NA",
        "Depth of focus           DOF = k2 * lambda / NA^2",
        "",
        "lambda = wavelength, NA = numerical aperture (n sin theta), k1 >= 0.25"],
       "Rayleigh criteria. Everything in lithography is a fight to lower k1 "
       "or lambda or to raise NA.")
    code(L(SRC_LITHO), caption="litho.py - printable half-pitch for each "
         "lithography generation.")
    out(L(OUT_LITHO), caption="Real output of litho.py.")
    p("Immersion lithography (ArF, 193 nm, with water between lens and "
      "wafer so NA can exceed 1) printed everything down to about 80 nm "
      "pitch in a single exposure. Tighter pitches needed "
      "**multi-patterning**: LELE (litho-etch-litho-etch, two masks with "
      "the layout split into two 'colours'), and self-aligned double or "
      "quadruple patterning (SADP/SAQP) where spacers deposited on a "
      "mandrel define lines at half or a quarter of the printed pitch. "
      "Multi-patterning adds masks, cost and layout restrictions: "
      "**colouring** rules (no two same-colour shapes too close), "
      "unidirectional metal, and cut masks.")
    p("**EUV** lithography (13.5 nm, reflective optics in vacuum, NA 0.33) "
      "entered volume production around the 7 nm/5 nm generation and "
      "replaced many multi-patterning steps with single exposures; "
      "high-NA EUV (0.55) is being introduced for the following nodes. "
      "EUV brings its own issues: stochastic defects (few photons per "
      "feature), mask defects that cannot be covered by a pellicle as "
      "easily, and high tool cost.")
    h3("Resolution enhancement techniques")
    bul([
        "**OPC** (optical proximity correction): the mask shapes are "
        "deliberately distorted - serifs, hammerheads, biasing - so that "
        "the printed shape matches the drawn one. Done by the foundry or "
        "mask flow after tapeout (Chapter 19).",
        "**SRAFs** (sub-resolution assist features): tiny non-printing "
        "shapes that improve the process window of isolated lines.",
        "**Phase-shift masks** and **off-axis / source-mask optimised "
        "illumination** improve contrast.",
        "**Restricted design rules**: fixed pitches, unidirectional "
        "layers and gridded placement make patterns regular and printable.",
    ])

    h2("FEOL: building the transistors")
    p("Front-end-of-line (FEOL) processing builds the devices in the "
      "silicon. A simplified modern sequence (details vary widely by "
      "foundry and node):")
    bul([
        "**Wells**: implant n-wells (for pMOS) and p-wells (for nMOS); deep "
        "n-well where a p-well must be isolated from the substrate.",
        "**Isolation**: shallow trench isolation (STI) - etch trenches, "
        "fill with oxide, CMP flat - separates active areas. In FinFET "
        "processes the fins are etched first (often by SADP/SAQP) and "
        "oxide fills between them.",
        "**Gate stack**: modern nodes use high-k dielectric (hafnium-based) "
        "and metal gates. In the common **replacement-metal-gate** "
        "(gate-last) flow a sacrificial polysilicon gate is patterned, "
        "spacers are formed, source/drain are built, then the dummy gate "
        "is removed and replaced by high-k and work-function metals (whose "
        "choice sets the Vt flavours).",
        "**Source/drain**: extension and halo implants, spacers, then "
        "raised S/D grown by epitaxy - SiGe for pMOS (compressive strain "
        "boosts hole mobility), Si:P for nMOS.",
        "**Anneal and silicide**: activate dopants; form a low-resistance "
        "silicide at contacts.",
    ], ordered=True)
    diagram([
        "          nMOS (in p-well)                           pMOS (in n-well)",
        "         S       G       D                          S       G       D",
        "         |    +-----+    |                          |    +-----+    |",
        "         |    | gate|    |                          |    | gate|    |",
        "  +-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+",
        "  | STI | n+  | ch. | n+  | STI | p+  | STI | n+  | STI | p+  | ch. | p+  |",
        "  |#####+-----+-----+-----+#####| tap |#####| tap |#####+-----+-----+-----+",
        "  |               p-well              |                n-well              |",
        "  +-----------------------------------+------------------------------------+",
        "  |            p-substrate  (p+ tap -> VSS,  n+ tap in n-well -> VDD)      |",
        "  +------------------------------------------------------------------------+",
        "   ##### = shallow trench isolation (oxide)      ch. = channel under the gate",
    ], "Simplified FEOL cross-section: wells, STI, gates and source/drain.")

    h2("MEOL: the local interconnect")
    p("Middle-of-line (MEOL) connects the devices to the first metal. "
      "It consists of **trench contacts** to source/drain, **gate "
      "contacts**, and sometimes a **local interconnect** layer. In SKY130 "
      "this is the 'li1' local-interconnect layer (visible in the LEF of "
      "Chapter 4) with 'mcon' contacts up to met1. At advanced nodes the "
      "MEOL contacts are tiny and highly resistive; contact resistance "
      "has become a large fraction of total device resistance, and tricks "
      "such as **contact over active gate** (COAG) are used to shrink "
      "cells.")

    h2("BEOL: the metal stack")
    p("Back-end-of-line (BEOL) builds the wiring. Since the late 1990s "
      "copper has been used, patterned by the **damascene** process "
      "because copper cannot be dry-etched easily: etch trenches (and "
      "vias, in **dual damascene**) into the dielectric, line them with a "
      "barrier (Ta/TaN) and seed, electroplate copper to overfill, then "
      "CMP back to the dielectric. Dielectrics are **low-k** "
      "(carbon-doped oxide, porous films, k around 2.5-3.0 versus 3.9 "
      "for SiO_{2}) to reduce capacitance, at the cost of mechanical "
      "weakness that matters for packaging (Chapter 20).")
    diagram([
        "  Layer group          pitch           used for",
        "  -------------------  -------------   -----------------------------------------",
        "  RDL / AP (Al pad)    ~ several um    bond pads, bumps, redistribution",
        "  Mz  top thick Cu     ~ 1-10 um       global power grid, clock spines",
        "  Mx  intermediate     ~ 2-4x min      block routing, long signals",
        "  M2..M4  thin (1x)    minimum         local routing inside std-cell areas",
        "  M1                   minimum         cell internal wiring, pins",
        "  ---- MEOL ----       contacts / local interconnect",
        "  ---- FEOL ----       transistors (fins / sheets, gates, S/D)",
        "",
        "           thick  ||||||||     ||||||||      (low R: power, clock)",
        "     intermediate  ||| ||| ||| ||| |||",
        "     thin (1x)     | | | | | | | | | | | | | | (high R, dense)",
        "     contacts      . . . . . . . . . . . . .",
        "     devices       ==== ==== ==== ==== ====",
    ], "A generic BEOL stack: thin, dense layers at the bottom; thick, "
       "low-resistance layers at the top.")
    p("Wire resistance per unit length grows roughly as 1/(width x "
      "thickness), and at advanced nodes even faster because the barrier "
      "does not scale and electrons scatter at surfaces and grain "
      "boundaries (effective copper resistivity at the thinnest layers "
      "is several times bulk). A typical advanced-node stack has 10-18 "
      "metal layers; the physical-design engineer chooses which layers "
      "carry power, clocks and long signals (Chapters 14-17). Alternative "
      "metals (cobalt, ruthenium) and **backside power delivery** - moving "
      "the power grid under the transistors - are recent answers to "
      "interconnect resistance.")
    h3("A real stack: SKY130")
    p("The open SkyWater 130 nm process has one local interconnect (li1) "
      "and five aluminium metal layers. From its technology LEF "
      "(`sky130_fd_sc_hd.tlef`) the routing pitches are:")
    tbl(["Layer", "Direction", "Pitch (um)", "Min width (um)"], [
        ["li1", "vertical", "0.46 x 0.34", "0.17"],
        ["met1", "horizontal", "0.34", "0.14"],
        ["met2", "vertical", "0.46", "0.14"],
        ["met3", "horizontal", "0.68", "0.30"],
        ["met4", "vertical", "0.92", "0.30"],
        ["met5", "horizontal", "3.40", "1.60"],
    ], widths=[1, 1.4, 1.4, 1.4], bold_first=True,
       caption="SKY130 routing layers as defined in the real sky130_fd_sc_hd.tlef "
               "(pitches and widths in um).")
    p("Note the alternating preferred directions (each layer routes mostly "
      "in one direction, and its neighbours in the other) and the thick, "
      "wide top layer used for the power grid.")

    h2("Node names versus real dimensions")
    p("Up to roughly 0.35 um the node name matched the drawn gate length. "
      "Since then it has become a **marketing label** for a generation: "
      "a '5 nm' or '3 nm' process has no 5 nm or 3 nm feature that "
      "defines it. Meaningful density metrics are the **contacted poly "
      "pitch** (CPP, gate-to-gate spacing), the **minimum metal pitch** "
      "(MMP) and the **cell height** (tracks x metal pitch).")
    tbl(["Node label (approximate)", "CPP (order of)", "Min metal pitch (order of)",
         "Device"], [
        ["130 nm (e.g. SKY130)", "~ 0.4-0.5 um", "~ 0.3-0.4 um", "Planar"],
        ["28 nm", "~ 110-120 nm", "~ 90 nm", "Planar (HKMG)"],
        ["16/14 nm", "~ 80-90 nm", "~ 64 nm", "FinFET"],
        ["7 nm", "~ 55-60 nm", "~ 36-40 nm", "FinFET"],
        ["5 nm", "~ 50 nm", "~ 28-30 nm", "FinFET (EUV)"],
        ["3 nm / 2 nm class", "~ 45-48 nm", "~ 21-24 nm", "FinFET / GAA"],
    ], widths=[1.8, 1.4, 1.8, 1.4], bold_first=True,
       caption="Published/estimated ranges from public sources; exact values differ "
               "per foundry. Always use your PDK's numbers.")
    box("warn", "PITFALL: comparing nodes across foundries by name",
        "Two foundries' '7 nm' processes can differ substantially in "
        "density and performance. Compare CPP x MMP, cell height, SRAM "
        "bitcell area and published PPA of a reference design - not the "
        "label.")

    h2("Design rules")
    p("The foundry guarantees yield only for layouts that obey its "
      "**design rules**, documented in the **design rule manual** (DRM) "
      "and encoded in the DRC rule deck (Chapter 18). The basic rule "
      "types:")
    diagram([
        "  WIDTH        SPACING          ENCLOSURE           EXTENSION      AREA",
        "  +----+       +---+   +---+    +------------+      +---+          +------+",
        "  |    |       |   |<->|   |    |  +------+  |      |   |          |######|",
        "  |<-->|       |   | s |   |    |  | via  |  |      |===|===>      |######|",
        "  | w  |       +---+   +---+    |  +------+  |      |   | e        +------+",
        "  +----+                        +--<-e->-----+      +---+          >= A_min",
        "  w >= Wmin    s >= Smin(w,l)   metal encloses via   poly past     min polygon",
        "                (wide-metal     by >= e (end-of-line  diffusion     area",
        "                 & EOL rules)    rules differ)        by >= e",
    ], "Basic design-rule types.")
    bul([
        "**Width, spacing, enclosure, extension, area** - geometric rules "
        "per layer and between layers.",
        "**Wide-metal and end-of-line spacing** - wider or longer wires need "
        "more space; line ends need extra space for printability.",
        "**Density rules** - each layer must have a minimum and maximum "
        "pattern density within sliding windows (for uniform CMP and "
        "etch); met by inserting **fill** (dummy metal/poly/diffusion).",
        "**Antenna rules** - the ratio of metal area connected to a gate "
        "during manufacturing (before the upper layers connect it to a "
        "diffusion) must stay below a limit to avoid plasma charging "
        "damage to the gate oxide; fixed with layer jumping or diodes "
        "(Chapters 4 and 17).",
        "**Multi-patterning (colouring) rules, grid rules, via rules** - "
        "advanced nodes add hundreds of context-dependent rules.",
        "**Latch-up and ESD rules** - tap spacing, guard rings, I/O rules "
        "(Chapter 12).",
    ])
    h3("DFM: design for manufacturability")
    p("Beyond the mandatory rules, foundries publish **recommended rules** "
      "and DFM guidelines: redundant (double) vias, wire spreading, "
      "wider line ends, litho-friendly patterns checked by litho "
      "simulation or pattern matching (hotspot detection), and critical "
      "area analysis to estimate random-defect yield. DFM work improves "
      "yield and reliability and is discussed in Chapters 17 and 21.")

    h2("The process design kit (PDK)")
    p("The PDK is the contract between the foundry and the design team. "
      "It is usually licensed under NDA and qualified for specific tool "
      "versions. Open PDKs such as SKY130, GF180MCU and IHP SG13G2 let "
      "anyone see what one contains.")
    tbl(["PDK component", "Content", "Used by"], [
        ["Design rule manual (DRM)", "All layout rules, layer definitions, "
         "recommended rules", "Layout, PD, PV"],
        ["Device models", "SPICE models (BSIM-CMG for FinFET, BSIM4 for "
         "planar, BSIM-IMG for FD-SOI), corner and Monte Carlo statistical "
         "models, aging models", "Circuit designers, library characterisation"],
        ["Layer map and tech files", "GDS layer numbers; technology files "
         "for layout editors and P&R (tech LEF, routing rules)", "Layout, PD"],
        ["Rule decks", "DRC, LVS, antenna, ERC, fill, parasitic extraction "
         "(RC tech files, e.g. ITF/ICT/qrcTechFile), DFM", "PV, extraction"],
        ["PCells", "Parameterised layout generators for transistors, "
         "resistors, capacitors, inductors", "Analog/custom layout"],
        ["Primitive libraries", "Symbols, schematics, device cells",
         "Analog design"],
        ["Foundation IP (often separate)", "Standard cells, I/Os, memory "
         "compilers (Chapter 4)", "Everyone"],
        ["Reliability docs", "EM limits, TDDB, HCI, BTI, self-heating "
         "guidelines", "Sign-off (Chapter 18)"],
    ], widths=[1.9, 4.0, 2.2], bold_first=True)
    box("tip", "PDK versions matter",
        "PDKs are released in versions (0.1, 0.5, 0.9, 1.0...). Early "
        "versions carry preliminary models and rules; designs started on "
        "0.5 must be re-verified when 1.0 arrives. Track the PDK version in "
        "every sign-off report, and read the release notes - a changed "
        "rule deck can create thousands of DRC violations late in a "
        "project.")

    h2("Process variation")
    p("No two transistors are identical. Variation is classified two ways:")
    tbl(["", "Global (die-to-die, wafer-to-wafer, lot-to-lot)",
         "Local (within-die, device-to-device)"], [
        ["Systematic", "Equipment drift, wafer-level gradients, lens "
         "aberrations", "Layout-dependent effects: well proximity, STI "
         "stress, density, litho context, OPC residue"],
        ["Random", "Lot-to-lot fluctuations", "Random dopant fluctuation, "
         "line-edge roughness, work-function granularity, fin variability"],
    ], widths=[1.0, 3.2, 3.6], bold_first=True)
    h3("Corners")
    p("Global variation is captured by **process corners**, named by the "
      "speed of nMOS then pMOS: **TT** (typical), **FF** (fast-fast), "
      "**SS** (slow-slow), **FS** and **SF** (skewed). Combined with "
      "voltage (e.g. nominal +- 10 %) and temperature (e.g. -40 to 125 "
      "deg C) they form the **PVT corners** at which libraries are "
      "characterised and timing is signed off (Chapter 9). Setup is "
      "usually worst at SS/low-V, hold at FF/high-V, leakage at FF/high-T, "
      "dynamic power at FF/high-V. Skewed corners stress ratioed circuits "
      "(SRAM write/read, level shifters, latches).")
    h3("Temperature inversion")
    p("Higher temperature lowers mobility (slower) but also lowers Vth "
      "(faster). At high Vdd mobility wins and hot is slow. At low Vdd - "
      "where overdrive Vdd - Vth is small - the Vth effect wins and "
      "**cold is slow**. This **temperature inversion** is pronounced in "
      "FinFET nodes and low-voltage designs, so sign-off must include the "
      "cold corners (e.g. SS/0.72 V/-40 C) as potential worst-setup "
      "corners, not just the hot ones.")
    h3("Local variation: Pelgrom's law and Monte Carlo")
    p("Random local variation of Vth between two identically drawn "
      "devices follows **Pelgrom's law**: the standard deviation is "
      "inversely proportional to the square root of the gate area.")
    eq(["sigma(delta Vth) = A_VT / sqrt(W * L)"],
       "Pelgrom mismatch. A_VT (mV*um) is a technology constant from the PDK.")
    code(L(SRC_PELGROM), caption="pelgrom.py - Vth mismatch versus device "
         "size, checked with a Monte Carlo draw.")
    out(L(OUT_PELGROM), caption="Real output of pelgrom.py.")
    p("A minimum-size device has tens of millivolts of random Vth "
      "mismatch; a 6-sigma excursion is well over 100 mV - comparable to "
      "the overdrive at low voltage. Halving sigma costs 4x the area. This "
      "is why SRAM bitcells (millions of minimum devices, each needing to "
      "work at 6-sigma or beyond) set the minimum operating voltage of "
      "many chips, why analog designers use large devices, and why STA "
      "uses statistical on-chip variation models (AOCV, POCV/LVF, "
      "Chapter 9). SPICE **Monte Carlo** simulation draws global and local "
      "parameters from the PDK's statistical models to verify such "
      "circuits; library characterisation uses it to produce LVF tables "
      "(Chapter 4).")
    box("expert", "Interview insight: why does variation get worse with scaling?",
        "Fewer dopant atoms per channel (a few tens in a planar device), "
        "line-edge roughness that does not shrink with the feature, and "
        "smaller gate area (Pelgrom). FinFETs reduced random dopant "
        "fluctuation (undoped fins) but added fin-width and work-function "
        "granularity. Meanwhile lower Vdd means the same mV of variation is "
        "a larger fraction of overdrive.")

    h2("Summary")
    bul([
        "Wafers are grown as single-crystal ingots, sliced and polished; "
        "300 mm is standard for advanced and many mature nodes. "
        "Processing takes 1000+ steps and roughly three months.",
        "Lithography resolution is k1 lambda / NA. 193i needs "
        "multi-patterning below ~80 nm pitch; EUV (13.5 nm) restored "
        "single-exposure patterning for critical layers. The reticle limits "
        "a die to about 26 x 33 mm.",
        "FEOL builds transistors (wells, STI/fins, HKMG gates, epitaxial "
        "S/D); MEOL makes contacts/local interconnect; BEOL builds a copper "
        "damascene stack from thin, dense layers to thick top layers.",
        "Node names are labels; compare CPP, metal pitch and cell height.",
        "Design rules (width, spacing, enclosure, density, antenna, "
        "colouring) and DFM guidelines protect yield; the PDK packages "
        "rules, models, tech files, rule decks and PCells.",
        "Variation is global or local, systematic or random; corners model "
        "global variation, temperature inversion makes cold corners "
        "critical, and Pelgrom's law sigma = A_VT / sqrt(WL) sets local "
        "mismatch.",
    ])
    h2("Exercises")
    bul([
        "With 193i immersion (NA = 1.35) and k1 = 0.30, what is the finest "
        "single-exposure pitch? How many exposures (or which self-aligned "
        "scheme) would a 32 nm pitch need?",
        "Using the SKY130 pitches above, how many met2 tracks cross a "
        "100 um wide channel? How many met4 tracks?",
        "An SRAM needs sigma(delta Vth) <= 15 mV between the two pull-down "
        "devices. With A_VT = 1.5 mV um and L = 30 nm, what minimum W is "
        "required? What does that do to bitcell area?",
        "Explain why the worst setup corner of a 0.6 V FinFET design may be "
        "SS/-40 C rather than SS/125 C.",
        "List five PDK deliverables and the team that consumes each.",
        "Why must metal density be kept within minimum and maximum limits, "
        "and what does the PD flow do to meet them?",
    ], ordered=True)


# =============================================================================
#  Chapter 4 - Standard cells, libraries and IP
# =============================================================================
def _ch4():
    chapter("Standard Cells, Libraries and IP: Cell Design, Liberty, LEF, "
            "Memories, I/O and IP Integration")
    p("Synthesis, placement, clock-tree synthesis, routing, STA, power "
      "analysis and ATPG never look at transistors. They see a design as "
      "instances of **cells** and **macros**, each described by a handful of "
      "abstract views: a Liberty file for timing, power and function, a LEF "
      "file for geometry, a Verilog model for simulation, and GDS for the "
      "final layout. The quality of these libraries bounds the quality of "
      "the chip. This chapter looks inside them, using the real SkyWater "
      "SKY130 high-density library (`sky130_fd_sc_hd`) wherever possible.")

    h2("Standard-cell architecture")
    p("A standard cell is a small, fixed-height layout implementing one "
      "logic function. Cells have the same height so that they abut in "
      "**rows**, sharing power rails at the top (VDD) and bottom (VSS). "
      "Alternate rows are flipped (mirrored about the x-axis) so that "
      "adjacent rows share a rail and an n-well.")
    diagram([
        '  <--------- width = N x placement site (0.46 um in SKY130 hd) ---------->',
        '  +======================================================================+ VPWR (met1 rail)',
        '  |  n-well        pMOS devices (pull-up network)                        |',
        '  |                ===|===|===    ===|===|===                            |',
        '  |                   |   |          |   |              o Y  (output pin)|  height',
        '  |     o A        poly gates run vertically                             |  2.72 um',
        '  |     o B           |   |          |   |                               |  (8 met1',
        '  |  p-well        ===|===|===    ===|===|===                            |  pitches)',
        '  |                nMOS devices (pull-down network)                      |',
        '  +======================================================================+ VGND (met1 rail)',
        '',
        '  next row is flipped: it shares the VGND rail (or VPWR rail) with this row',
    ], "Anatomy of a standard cell: rails, wells, gates and pins.")
    h3("Key architectural parameters")
    bul([
        "**Cell height** in routing **tracks**: height / M1 (or M2) pitch. "
        "Typical libraries range from about 12 tracks (older, high-drive) "
        "down to 6 or fewer tracks at advanced nodes. SKY130 hd cells are "
        "2.72 um tall = 8 met1 pitches of 0.34 um. Taller cells drive "
        "harder and route more easily; shorter cells are denser.",
        "**Placement site**: the width quantum. Cells are an integer number "
        "of sites wide (0.46 um in SKY130 hd; one contacted poly pitch in "
        "FinFET libraries).",
        "**Fins per device** (FinFET): a 6-track cell might allow only 2 "
        "fins per device, a 7.5-track cell 3, which quantises drive strength.",
        "**Pin access**: at advanced nodes pins are small shapes on M1 or "
        "M0 and the router must reach each with a limited number of via "
        "positions; poor pin access is a major cause of routing congestion "
        "(Chapter 17).",
        "**Power rails**: on M1 (or buried/backside at the newest nodes); "
        "the PD flow later straps them to the power grid (Chapter 14).",
    ])

    h2("Cell families")
    tbl(["Family", "Purpose", "SKY130 hd examples"], [
        ["Combinational logic", "INV, BUF, NAND/NOR, AND/OR, XOR/XNOR, "
         "AOI/OAI complex gates, MUX, full/half adders, majority",
         "`inv`, `nand2`, `a21oi`, `o22ai`, `xor2`, `mux2`, `fa`, `maj3`"],
        ["Flip-flops", "D flops with/without reset/set, enable, scan mux "
         "(scan flops, Chapter 10)", "`dfxtp` (plain), `dfrtp` (async reset), "
         "`sdfxtp` (scan), `edfxtp` (enable)"],
        ["Latches", "Level-sensitive storage", "`dlxtp`, `dlrtp`"],
        ["Clock cells", "Balanced clock buffers/inverters, integrated clock "
         "gates (ICG)", "`clkbuf`, `clkinv`, `dlclkp` (ICG), `sdlclkp`"],
        ["Delay cells", "Deliberate delay for hold fixing", "`dlygate4sd3`, "
         "`clkdlybuf4s50`"],
        ["Low-power cells", "Level shifters, isolation, retention, "
         "always-on buffers, power switches (Chapter 11)",
         "`lpflow_isobufsrc`, `lpflow_inputiso0p`, `lpflow_lsbuf_lh_isowell`"],
        ["Tie cells", "Drive constant 0/1 through a device, never directly "
         "from the rail (protects gate oxide from ESD)", "`conb` (tie hi/lo)"],
        ["Physical-only cells", "Fill, decap (on-die decoupling), well-tap, "
         "endcap/boundary, antenna diodes", "`decap_4`, `diode_2`, "
         "`tapvpwrvgnd_1`, `fill_1`"],
        ["Spare cells", "Unused gates sprinkled for metal-only ECOs "
         "(Chapter 19)", "`macro_sparecell`"],
    ], widths=[1.6, 3.4, 3.4], bold_first=True)
    box("note", "Why so many special cells?",
        "The physical-only cells exist because of the process: taps bias "
        "wells and prevent latch-up (Chapter 2); endcaps terminate rows so "
        "that the edge devices see the same environment as inner ones "
        "(layout-dependent effects, Chapter 3); decaps supply charge for "
        "local current spikes (Chapter 18); antenna diodes discharge plasma "
        "charge (Chapter 3); fill keeps densities legal.")

    h2("Drive strengths, Vt flavours and variants")
    p("Each function comes in several **drive strengths** (x1, x2, x4...) "
      "built with wider devices or parallel fingers/fins. Larger drives "
      "have proportionally larger input capacitance and area - the "
      "logical-effort trade-off of Chapter 2. A library usually also comes "
      "in several **Vt flavours** with identical footprints (so they can "
      "be swapped late without re-placement) and sometimes in several "
      "**channel lengths** (e.g. a 'long-L' variant for lower leakage) or "
      "track heights. The real library summary below was produced by "
      "parsing the SKY130 hd Liberty file:")
    code(L(SRC_LIBSUM), caption="libsum.py - summarise the real "
         "sky130_fd_sc_hd typical-corner Liberty file.")
    out(L(OUT_LIBSUM), caption="Real output of libsum.py (area in um^2, "
        "capacitance converted from pF to fF, leakage in the library's nW).")
    p("Note how area and input capacitance scale almost linearly with "
      "drive (nand2_1 -> nand2_8: area x5.3, input capacitance x7.3), and "
      "that a flip-flop is about five times the area of a NAND2. Area "
      "divided by the NAND2 area gives the **NAND2-equivalent gate count** "
      "(GE) used to size designs (Chapter 5).")

    h2("Characterisation: how a Liberty file is made")
    p("Each cell is simulated in SPICE (with the PDK's device models and the "
      "extracted parasitics of the cell layout) at every PVT corner, "
      "sweeping **input slew** and **output load**. For every timing arc "
      "(input pin -> output pin, and for sequential cells clock -> output "
      "and data -> clock constraints) the tool measures:")
    bul([
        "**Delay**: from the input crossing its threshold (typically 50 % "
        "of Vdd) to the output crossing its threshold.",
        "**Output transition (slew)**: typically 10-90 % or 20-80 % of the "
        "swing (scaled back to full swing using slew_derate_from_library).",
        "**Setup, hold, recovery, removal** and **minimum pulse width** "
        "constraints of sequential cells, found by bisection on the "
        "data-to-clock offset until the output degrades by a defined "
        "criterion (in SKY130 note `violation_delay_degrade_pct : 10`).",
        "**Internal energy** per transition, **leakage** per input state, "
        "and **pin capacitance**.",
    ])
    diagram([
        "  cell netlist + extracted RC      PDK SPICE models      PVT corner list",
        "            \\                           |                    /",
        "             +-------------> characterisation tool <--------+",
        "                              (SPICE runs: slews x loads x arcs x states)",
        "                                          |",
        "        +----------------+----------------+----------------+---------------+",
        "        v                v                v                v               v",
        "   NLDM tables      CCS / ECSM       LVF / POCV sigma   power tables     noise",
        "   (delay, slew)    (current/volt.   (local variation)   (internal,       (CCSN)",
        "                     waveforms)                          leakage)",
        "        +---------------- Liberty .lib per corner -----> compiled .db / tool DB",
    ], "Library characterisation flow.")
    p("A full library at an advanced node is characterised at dozens of "
      "corners (process x voltage x temperature x extraction corner), "
      "consuming very large compute farms; every new corner requested late "
      "in a project costs schedule.")

    h2("Liberty in depth")
    p("Liberty (.lib) is a human-readable, group-and-attribute text format "
      "originally from Synopsys and now a de-facto standard. The structure "
      "is hierarchical: `library` -> `cell` -> `pin` -> `timing` / "
      "`internal_power` groups, with lookup-table templates declared at "
      "the library level.")
    h3("The library header")
    code(L(LIB_HEAD), caption="Real excerpt: header of "
         "the SKY130 hd typical-corner Liberty file (units, operating condition, a "
         "table template).")
    p("Units matter: in this library time is in ns, capacitance in pF and "
      "leakage in nW. A wrong unit assumption is a classic cause of "
      "absurd reports when mixing libraries. The template `del_1_7_7` "
      "declares a 7 x 7 table indexed by input transition (index_1) and "
      "total output capacitance (index_2).")
    h3("A combinational cell: the SKY130 nand2_1")
    code(L(LIB_NAND2), caption="Real excerpt of the nand2_1 cell group "
         "(long lines cut at ' ...'; everything else verbatim).")
    tbl(["Construct", "Meaning"], [
        ["`area`", "Cell area in um^2 (here 1.38 x 2.72 um = 3.7536)"],
        ["`cell_footprint`", "Cells with the same footprint are "
         "interchangeable in layout (used for sizing/Vt swaps)"],
        ["`leakage_power` + `when`", "State-dependent leakage: 7.9 pW with "
         "both inputs high (A&B, output low) versus 0.03 pW with both low - "
         "stacking two off nMOS devices cuts leakage by orders of magnitude "
         "(the stack effect)"],
        ["`pin` / `direction` / `capacitance`", "Pin capacitance in pF, "
         "separately for rise and fall"],
        ["`function`", "Boolean function (used by synthesis, LEC, ATPG)"],
        ["`max_transition`, `max_capacitance`", "Design-rule limits: the "
         "tables are valid only inside them; exceeding them is a DRV "
         "(design-rule violation) that STA reports and PD must fix"],
        ["`timing()` + `related_pin`", "A timing arc from related_pin to "
         "this pin"],
        ["`timing_sense`", "positive_unate, negative_unate or non_unate "
         "(e.g. XOR)"],
        ["`timing_type`", "combinational, rising_edge, setup_rising, "
         "hold_rising, recovery/removal, min_pulse_width, "
         "three_state_enable..."],
        ["`cell_rise`/`cell_fall`", "Delay tables for output rising/falling"],
        ["`rise_transition`/`fall_transition`", "Output slew tables"],
        ["`internal_power`", "Energy tables per transition (excludes the "
         "C Vdd^2 of the external load, which power tools add from the "
         "net capacitance)"],
    ], widths=[2.6, 5.6])
    h3("Sequential cells and constraint arcs")
    code(L(LIB_DFF), caption="Real excerpt: the D-pin constraint arcs of "
         "the SKY130 hd flip-flop dfxtp_1.")
    p("The `ff` group declares the internal state (IQ, IQ_N) and its "
      "next-state function. Constraint tables live on the __data__ pin with "
      "`related_pin : \"CLK\"`; `setup_rising` and `hold_rising` mean "
      "checks against the rising clock edge. The template `vio_3_3_1` is "
      "indexed by related-pin (clock) transition and constrained-pin "
      "(data) transition. Negative hold values are normal - they mean data "
      "may change slightly __before__ the clock edge without violation - "
      "because of the flop's internal clock-path delay.")
    h3("Integrated clock gate")
    code(L(LIB_ICG), caption="Real excerpt: the ICG cell "
         "the SKY130 hd cell dlclkp_1 (latch-based, rising-edge clock gate).")
    p("Attributes such as `clock_gating_integrated_cell`, "
      "`clock_gate_enable_pin` and `clock_gate_out_pin` tell synthesis this "
      "cell can implement clock gating (Chapter 11) and tell STA to perform "
      "clock-gating checks on GATE. The `statetable` models the internal "
      "latch: M0 follows GATE while CLK is low (the 'L L -> L', 'L H -> H' "
      "rows) and holds (N = no change) while CLK is high.")

    h2("Looking up an NLDM table")
    p("An STA tool computes a cell delay by finding the input slew and "
      "the output load of the instance, then interpolating (bilinearly, "
      "inside the grid; extrapolating outside, which is inaccurate and "
      "flagged) in the relevant table. The script below does exactly that "
      "on the real SKY130 tables:")
    code(L(SRC_NLDM), caption="nldm.py - parse a Liberty timing table and "
         "interpolate it like an STA tool.")
    out(L(OUT_NLDM), caption="Real output of nldm.py on the real "
        "SKY130 typical-corner tables.")
    eq(["u = (x1 - x1_i) / (x1_(i+1) - x1_i),     w = (x2 - x2_j) / (x2_(j+1) - x2_j)",
        "D = (1-u)(1-w) T[i][j] + u(1-w) T[i+1][j] + (1-u)w T[i][j+1] + uw T[i+1][j+1]"],
       "Bilinear interpolation between the four surrounding grid points.")
    p("So a nand2_1 driven with an 80 ps slew into 5 fF has a falling delay "
      "of about 66 ps and a rising delay of about 83 ps at the typical "
      "corner (the pMOS pull-up is weaker). The output slew then becomes "
      "the input slew of the next stage - which is how slew propagates "
      "through a path (Chapter 9).")
    h3("Beyond NLDM: CCS, ECSM, LVF and power")
    tbl(["Model", "What it adds", "Why"], [
        ["NLDM", "Delay and slew tables vs (slew, load)", "Simple, fast; "
         "assumes a ramp input and a lumped C load"],
        ["CCS (Synopsys) / ECSM (Cadence)", "Output current (CCS) or voltage "
         "(ECSM) waveforms vs time for each (slew, load); receiver "
         "capacitance tables", "Accurate with resistive wires (effective "
         "capacitance), non-ramp waveforms, and below ~65 nm; also CCS "
         "noise (CCSN) and CCS power"],
        ["LVF (Liberty Variation Format)", "Sigma tables (ocv_sigma_cell_rise, "
         "...) per arc, optionally with mean shift and skewness", "Statistical "
         "local variation for POCV/SOCV analysis (Chapter 9)"],
        ["Power tables", "internal_power (energy per event vs slew/load), "
         "state-dependent leakage_power", "Dynamic and leakage power "
         "analysis"],
        ["Aging / reliability", "Libraries characterised with aged models "
         "(e.g. 10-year BTI/HCI) or EM limits per pin", "Lifetime sign-off "
         "(Chapter 18)"],
    ], widths=[1.8, 3.6, 3.0], bold_first=True)

    h2("Using a library: dont_use lists and a real synthesis")
    p("Not every cell in a library should be used by synthesis. Clock "
      "cells should appear only in clock trees, delay cells only for hold "
      "fixing, isolation and level-shifter cells only where the UPF puts "
      "them, and some cells are simply poor or unreliable at a given "
      "corner. Flows therefore maintain a **dont_use** list. To show why, "
      "a 16x16 multiply-accumulate block was synthesised with Yosys against "
      "the real SKY130 Liberty, first as-is:")
    code(L(SRC_MAC_V), caption="mac.v - a registered 16 x 16 -> 40-bit MAC.")
    out(excerpt(OUT_STAT_RAW, ["Number of cells", "lpflow", "dfrtp",
                               "Chip area"]),
        caption="Real Yosys 0.33 'stat -liberty' excerpt, full library: the "
                "mapper picked lpflow isolation cells as ordinary gates.")
    p("ABC chose `lpflow_inputiso1p` and `lpflow_isobufsrc` cells - "
      "isolation cells that happen to compute an AND/OR function - for "
      "ordinary logic. In a real flow those cells would confuse power-intent "
      "verification and may have unsuitable characteristics. Marking them "
      "`dont_use : true` fixes it:")
    code(L(SRC_DONTUSE), caption="dontuse.py - mark special-purpose cells "
         "dont_use in a copy of the Liberty file.")
    out(L(OUT_DONTUSE), caption="Real output of dontuse.py.")
    code(L(SRC_MAC_YS), caption="mac2.ys - the Yosys script (synthesis, "
         "flop mapping, ABC mapping with a 5 ns delay target, statistics).")
    out(excerpt(OUT_STAT_DU, ["Number of cells", "dfrtp", "nand2_1 ",
                              "xnor2_1", "maj3", "Chip area"]),
        caption="Real Yosys 0.33 'stat -liberty' excerpt with dont_use applied.")
    p("The result is 1416 cells and 10768 um^2, i.e. about 2870 NAND2 "
      "equivalents (10768 / 3.7536), of which the 40 reset flops "
      "(`dfrtp_1`) are a significant share. We will reuse this number in "
      "Chapter 5.")
    box("warn", "PITFALL: trusting the full library",
        "Always review the dont_use list shipped with the library and add "
        "your own (weak x0/x1 cells at the slow corner, cells with known "
        "silicon issues, clock and delay cells in data paths). Also check "
        "that dont_use is applied consistently in synthesis, PD and ECO "
        "tools - a mismatch lets an ECO reintroduce a forbidden cell.")

    h2("LEF: the physical abstract")
    p("Place-and-route tools do not need the full transistor layout; they "
      "need outlines, pins and blockages. LEF (Library Exchange Format) "
      "provides this in two parts:")
    bul([
        "**Technology LEF**: units, manufacturing grid, placement `SITE`s, "
        "routing `LAYER`s (direction, pitch, width, spacing tables, "
        "resistance and capacitance per square), `VIA` definitions and "
        "via rules. Produced from the PDK.",
        "**Cell/macro LEF**: for each cell a `MACRO` with `CLASS` (CORE, "
        "BLOCK, PAD, ENDCAP...), `SIZE`, `SITE`, `SYMMETRY`, `PIN`s with "
        "their `PORT` geometry and direction/use, antenna information, "
        "and `OBS` (obstructions: metal the router must avoid).",
    ])
    code(L(TLEF), caption="Real excerpt of sky130_fd_sc_hd.tlef: the "
         "placement site and the met1 routing layer.")
    code(L(LEF_NAND2), caption="Real excerpt of the cell LEF for "
         "the SKY130 hd nand2_1.")
    p("The nand2_1 is 1.38 um wide = 3 sites of 0.46 um. Its signal pins "
      "are on li1 (the local interconnect), its power pins are met1 rails "
      "that extend 0.24 um beyond the cell edge so that they merge with "
      "the neighbour row (`SHAPE ABUTMENT`), `ANTENNAGATEAREA` feeds the "
      "router's antenna checks (Chapter 17), and the VPB/VNB pins are the "
      "separate n-well and p-well bias connections mentioned in Chapter 2. "
      "A cell's LEF, Liberty, Verilog model and GDS must agree exactly on "
      "names, pins and size - checking this is part of library QA.")

    h2("Memories: SRAM compilers, register files and ROM")
    p("Memories typically occupy a large fraction of an SoC's area - "
      "often a third to more than half. They are delivered by "
      "**memory compilers**: generators that tile a full-custom bitcell "
      "array with custom periphery (decoders, sense amplifiers, write "
      "drivers, timing control) for a requested words x bits "
      "configuration and emit all views.")
    diagram([
        "              WL (word line)",
        "     ----+-------------------------+----",
        "         |    Vdd        Vdd       |",
        "       +-+-+  |PU1        |PU2   +-+-+",
        "  BL --| PG1 |-+---+   +---+-| PG2 |-- BLB",
        "       +-----+ |   |   |   | +-----+",
        "               | Q o---X---o QB |        cross-coupled inverters",
        "               |PD1    |    PD2 |        hold Q and QB",
        "              Vss      |      Vss",
        "",
        "  read: precharge BL/BLB high, raise WL, the side storing 0 discharges its",
        "        bit line slightly, the sense amplifier resolves the difference.",
        "  write: drive BL/BLB to opposite values strongly enough to overpower PU.",
    ], "The 6T SRAM bitcell: two cross-coupled inverters (PU/PD) and two "
       "pass gates (PG).")
    p("The bitcell is sized for a delicate balance: PD must be stronger "
      "than PG for **read stability** (a read must not flip the cell), and "
      "PG stronger than PU for **writability**. Local mismatch "
      "(Pelgrom, Chapter 3) disturbs both, so bitcells set the minimum "
      "voltage (Vmin) of many chips and often need **assist circuits** "
      "(word-line underdrive, negative bit line) and sometimes a separate, "
      "higher memory supply. Foundry bitcells use special 'pushed' "
      "design rules that are denser than logic rules - which is why you "
      "cannot build a competitive SRAM out of standard cells.")
    tbl(["Memory type", "Characteristics", "Typical use"], [
        ["High-density SRAM (single-port)", "Smallest bitcell, slower, "
         "one access per cycle", "Large buffers, caches L2/L3"],
        ["High-speed / dual-port SRAM", "Larger 8T/dual-port cells, "
         "separate read/write ports", "L1 caches, FIFOs, frame buffers"],
        ["Register file (compiler)", "Small, fast, multi-port arrays",
         "CPU register files, small FIFOs"],
        ["Flop/latch-based arrays", "Built from standard cells; large but "
         "flexible and testable by scan", "Tiny memories (< ~1 kbit)"],
        ["ROM", "Contents programmed by a mask layer (via/diffusion)",
         "Boot code, look-up tables"],
        ["OTP / eFuse / eFlash / MRAM", "Non-volatile; special process "
         "options or IP", "Trimming, keys, firmware"],
    ], widths=[2.2, 3.4, 2.6], bold_first=True)
    p("A memory compiler delivers: Liberty (per corner, often with "
      "separate array and periphery supplies), LEF/abstract, GDS, "
      "behavioural Verilog, a **BIST/repair** interface (MBIST and "
      "redundant rows/columns, Chapter 10), and datasheets. Memory "
      "power-down modes (light sleep, deep sleep, shut-down) must be wired "
      "to the power-management logic and described in UPF (Chapter 11).")

    h2("I/O libraries")
    p("I/O cells connect the core to the package: digital I/O buffers "
      "(with programmable drive, slew, pull-up/down, Schmitt trigger), "
      "analog pads, power/ground pads for core and I/O supplies, corner "
      "cells, filler/spacer cells and **power-cut** cells that split the "
      "ring into voltage domains. Each I/O contains ESD protection and "
      "level shifting between the thick-oxide I/O voltage (1.8, 2.5, 3.3 V) "
      "and the core voltage. I/O rings, bump-pitch versus pad-pitch "
      "limits and ESD are covered in Chapters 12 and 14.")

    h2("IP: soft, firm and hard")
    tbl(["Type", "Delivered as", "Flexibility", "Examples"], [
        ["Soft IP", "Synthesisable RTL + constraints + testbench",
         "Portable to any node; you own timing closure", "CPU cores, "
         "interconnect, controllers (USB, DDR controller), crypto"],
        ["Firm IP", "Gate-level netlist, sometimes with placement guidance",
         "Node/library specific; some flexibility", "Pre-hardened "
         "subsystems, obfuscated cores"],
        ["Hard IP", "GDS + LEF abstract + Liberty (+ models)", "Fixed layout "
         "for one process; no changes", "PLLs, SerDes/PHYs, ADCs, SRAMs, "
         "I/Os, eFuse"],
    ], widths=[1.1, 2.4, 2.4, 2.6], bold_first=True)
    h3("IP qualification and integration")
    p("Buying IP transfers design effort, not responsibility: if the PHY "
      "fails, your chip fails. A disciplined team qualifies each IP before "
      "committing to it:")
    checklist("IP qualification and integration deliverables", [
        "Silicon proven? In which exact process/PDK version and metal stack, "
        "with test-chip characterisation data and errata.",
        "Complete views: RTL or netlist, Liberty for every sign-off corner "
        "you need, LEF, GDS, Verilog/behavioural models, SPICE/IBIS for "
        "analog and I/O, CDL netlist for LVS.",
        "Constraints: SDC for soft IP, timing models (ETM) for hard IP, "
        "UPF/power-intent fragments, CDC/RDC waivers.",
        "Verification collateral: testbenches, VIP, coverage reports, "
        "assertion packs, protocol compliance results.",
        "DFT: scan-ready, MBIST, test modes, JTAG/IEEE 1500 wrappers, "
        "test patterns for hard IP.",
        "Integration guide: floorplan and routing blockages, power supply "
        "and decap requirements, noise sensitivity, keep-out zones, "
        "bump/pad assignments.",
        "Clean DRC/LVS/antenna reports in the target PDK version, and "
        "the EM/IR data needed for chip-level sign-off.",
        "Deliverable quality checks: consistent pin names across all views, "
        "correct units, dont_touch/dont_use requirements, licence terms "
        "(per-design, royalty), support and export control.",
    ])
    box("expert", "Interview insight: the integration bugs that escape",
        "Common real-world IP problems: Liberty corners that do not match "
        "your sign-off corners (so STA extrapolates), a LEF abstract whose "
        "OBS does not match the GDS (routing shorts found only at full-chip "
        "DRC), reset or clock requirements hidden in a footnote, and an IP "
        "that was 'silicon proven' in a different metal stack. Qualify "
        "early and run the IP through your own flow in a test harness.")

    h2("Summary")
    bul([
        "Standard cells are fixed-height layouts in rows sharing rails; key "
        "parameters are track height, site width, fins per device and pin "
        "access. SKY130 hd: 0.46 x 2.72 um site.",
        "Libraries contain logic, sequential, clock, delay, low-power, tie "
        "and physical-only cells, in several drive strengths and Vt "
        "flavours with common footprints.",
        "Characterisation runs SPICE over slews x loads x corners; Liberty "
        "stores function, pin caps, NLDM (or CCS/ECSM) delay and slew "
        "tables, constraints (setup/hold via timing_type and related_pin), "
        "state-dependent power (when) and LVF sigma tables.",
        "STA interpolates tables bilinearly; the real SKY130 nand2_1 gives "
        "~66 ps fall delay at 80 ps slew and 5 fF.",
        "Use dont_use lists - a real Yosys run mapped logic onto isolation "
        "cells without one.",
        "LEF provides the tech (sites, layers, vias) and cell/macro "
        "abstracts (size, pins, OBS, antenna data).",
        "Memories come from compilers around 6T/8T bitcells that set Vmin; "
        "I/O libraries provide pads with ESD; IP is soft, firm or hard and "
        "must be qualified with a full deliverable checklist.",
    ])
    h2("Exercises")
    bul([
        "Using nldm.py, compute the nand2_1 A->Y rise and fall delays at "
        "(20 ps, 2 fF) and (400 ps, 50 fF). Which is limited by the input "
        "slew and which by the load?",
        "Why does the Liberty leakage of nand2_1 differ by more than two "
        "orders of magnitude between input states A&B and !A&!B?",
        "Explain the meaning of a negative hold constraint in the dfxtp_1 "
        "table. Under which conditions would STA report a hold violation "
        "anyway?",
        "List the LEF and Liberty attributes that must agree for a hard "
        "macro, and describe the failure that results if each disagrees.",
        "Estimate how many SKY130 hd sites and rows a block of 10768 um^2 "
        "needs at 70 % utilisation, and the side of a square core.",
        "Write a dont_use policy for a design with UPF power domains and "
        "explain each entry.",
    ], ordered=True)


# =============================================================================
#  Chapter 5 - Specification, architecture and micro-architecture
# =============================================================================
def _ch5():
    chapter("Specification, Architecture and Micro-architecture: From "
            "Requirements to PPA Targets")
    p("Most expensive ASIC failures are not caused by a timing violation "
      "or a DRC error. They are caused by building the wrong chip: a "
      "feature the customer needed was missing, the memory bandwidth could "
      "not feed the compute, the power budget was exceeded in a mode "
      "nobody modelled, the die came out 30 % larger than the cost model "
      "assumed. The front of the flow - requirements, architecture and "
      "micro-architecture - is where those decisions are made, cheaply, "
      "on paper and in models. This chapter describes how professional "
      "teams do it and how to put numbers on power, performance and area "
      "(PPA) before any RTL exists.")

    h2("Requirements: what the chip must do")
    p("Requirements come from customers, marketing, standards and "
      "regulations. They are captured in a **market requirements document** "
      "(MRD, the 'what and why': target market, use cases, competitors, "
      "price point, volumes, launch window) and refined into a **product "
      "requirements document** (PRD, the 'what exactly': measurable "
      "requirements the chip is designed and tested against).")
    tbl(["Category", "Examples of measurable requirements"], [
        ["Functional", "Supported interfaces and modes; algorithms; "
         "software/boot flow; debug features"],
        ["Performance", "Throughput (frames/s, TOPS, Gb/s), latency, "
         "clock frequencies, number of concurrent streams"],
        ["Power", "Active power per use case, idle and standby power, "
         "peak current, thermal design power, battery life"],
        ["Area / cost", "Die-size target, package size and type, bill of "
         "materials, target selling price and margin"],
        ["Schedule", "Tapeout, sample, qualification and production dates"],
        ["Standards / compliance", "PCIe/USB/MIPI/Ethernet compliance, "
         "JEDEC memory standards, EMC, RoHS"],
        ["Quality and reliability", "Operating temperature grade, lifetime "
         "(e.g. 10 years at a mission profile), DPPM target, AEC-Q100 "
         "for automotive"],
        ["Safety", "ISO 26262 ASIL level (automotive), IEC 61508 "
         "(industrial): safety mechanisms, diagnostic coverage"],
        ["Security", "Secure boot, key storage, side-channel and fault "
         "attack resistance, certifications (e.g. Common Criteria, FIPS)"],
    ], widths=[1.7, 6.3], bold_first=True)
    box("tip", "Write requirements you can test",
        "'Low power' is not a requirement. 'Average power <= 350 mW in "
        "use case UC-3 (1080p30 inference, 25 deg C ambient, typical "
        "silicon), measured at the board supply' is. Every PRD line should "
        "have an ID, a priority (must/should/may), a verification method "
        "(simulation, emulation, silicon measurement, analysis) and an "
        "owner.")

    h2("Architecture exploration")
    p("The architect's job is to find the cheapest structure that meets "
      "the requirements with margin. Exploration uses models of "
      "increasing fidelity:")
    tbl(["Model", "Fidelity / speed", "Answers"], [
        ["Spreadsheet / analytical", "Seconds; first-order", "Rough "
         "bandwidth, compute, memory size, power and area budgets"],
        ["Roofline and queueing models", "Seconds-minutes", "Compute- vs "
         "memory-bound, buffer depths, latency under load"],
        ["Python / C++ performance model", "Minutes; cycle-approximate",
         "Workload-driven throughput, utilisation, what-if studies"],
        ["SystemC/TLM virtual platform", "Near real time; transaction-"
         "level", "Software bring-up before RTL, interconnect contention, "
         "early firmware"],
        ["RTL simulation / emulation / FPGA prototype", "Cycle-accurate; "
         "slow (sim) to fast (emulation)", "Final performance validation, "
         "power estimation with real activity"],
    ], widths=[2.3, 2.1, 3.8], bold_first=True)
    p("SystemC (IEEE 1666) with TLM-2.0 lets architects build a virtual "
      "platform in which CPU instruction-set simulators run real software "
      "against loosely-timed or approximately-timed models of the "
      "accelerators and interconnect. It is also the input language of "
      "high-level synthesis tools.")
    h3("The roofline model")
    p("For compute engines the **roofline** answers the most important "
      "early question: is the design limited by compute or by memory "
      "bandwidth? Attainable throughput is the minimum of peak compute and "
      "bandwidth x **arithmetic intensity** (operations per byte moved "
      "to/from memory). The **ridge point** peak / bandwidth is the "
      "intensity above which the engine becomes compute-bound.")
    eq(["Attainable = min( Peak_ops ,  BW_mem * AI )      AI = ops / bytes",
        "Ridge point  AI* = Peak_ops / BW_mem"],
       "Roofline model.")
    code(L(SRC_ROOFLINE), caption="roofline.py - which neural-network layers "
         "can keep a 4 TOPS edge NPU busy on an LPDDR4x interface?")
    out(L(OUT_ROOFLINE), caption="Real output of roofline.py.")
    p("Only the dense convolution reaches peak; depthwise convolutions "
      "and batch-1 fully connected layers are badly memory-bound. This "
      "single table drives major architectural decisions: add on-chip "
      "SRAM so weights and activations stay local (raising effective "
      "intensity via reuse and layer fusion), widen the DRAM interface, "
      "add weight compression, or accept lower utilisation and shrink the "
      "MAC array to save area and leakage.")

    h2("Hardware/software partitioning")
    p("Every function can be implemented in software on a CPU, on a DSP "
      "or programmable accelerator, or in fixed-function hardware. The "
      "trade-off is flexibility versus efficiency: fixed-function logic is "
      "often orders of magnitude more energy-efficient than a general-"
      "purpose CPU for the same task, but it cannot be changed after "
      "tapeout.")
    bul([
        "Put in hardware: high-throughput, stable, regular kernels (video "
        "codecs, crypto, DSP filters, NN MAC arrays, packet parsing at line "
        "rate) and anything with hard real-time or security requirements.",
        "Keep in software: control, evolving algorithms, protocol upper "
        "layers, anything likely to change or rarely executed.",
        "Middle ground: programmable accelerators, DSPs with custom "
        "instructions, microcoded engines, eFPGA (Chapter 1).",
        "Define the HW/SW interface precisely: register map, interrupts, "
        "DMA descriptors, memory ordering, firmware responsibilities. The "
        "register map is typically generated from a single source "
        "(IP-XACT or SystemRDL) into RTL, C headers and documentation.",
    ])

    h2("Memory hierarchy and bandwidth budgets")
    p("Memory decisions dominate area, power and performance of most "
      "SoCs. The architect sizes each level - registers, local SRAM "
      "buffers, shared L2/L3 or system cache, external DRAM - from the "
      "workload's working set and reuse, and then budgets bandwidth at "
      "every interface.")
    diagram([
        "   DRAM (LPDDR/DDR/HBM)  --  34 GB/s peak, ~24 GB/s sustained (example)",
        "        |",
        "   memory controller + PHY",
        "        |                                   budget per master (GB/s)",
        "   system interconnect (NoC / AXI)          CPU cluster       4",
        "     |          |           |               NPU              14",
        "   CPU L2    NPU SRAM    ISP / video        ISP + video       4",
        "     |       (4 MB)      line buffers       display           1.5",
        "   CPU L1                                   misc. DMA         0.5",
        "                                            ---------------------",
        "                                            total            24.0  <= sustained",
    ], "A memory hierarchy with a bandwidth budget: the sum of concurrent "
       "demands must fit the sustained, not the peak, DRAM bandwidth.")
    bul([
        "Use **sustained** bandwidth: DRAM efficiency is typically 60-85 % "
        "of peak depending on access pattern, refresh and read/write "
        "turnarounds.",
        "Budget **concurrent** use cases: display refresh is real-time and "
        "must never starve; QoS and priority schemes in the interconnect "
        "follow from this analysis.",
        "Budget **latency** too: a CPU cache miss or a real-time DMA may "
        "need a bound, which drives outstanding-transaction counts and "
        "buffer depths (Little's law: outstanding = bandwidth x latency).",
        "Every on-chip SRAM adds area and leakage; every DRAM access costs "
        "roughly one to two orders of magnitude more energy than an on-chip "
        "SRAM access. Data movement, not arithmetic, usually dominates "
        "energy in data-intensive designs.",
    ])
    p("Little's law turns the bandwidth budget into hardware: to sustain "
      "bandwidth B through a memory system with round-trip latency T, a "
      "master must keep B x T bytes in flight, which sets the number of "
      "outstanding transactions its bus interface and the interconnect "
      "must support, and the size of reorder and data buffers. Real-time "
      "masters also need FIFOs deep enough to ride through the worst-case "
      "stall.")
    code(L(SRC_LITTLE), caption="little.py - outstanding transactions and "
         "FIFO depth from bandwidth and latency.")
    out(L(OUT_LITTLE), caption="Real output of little.py.")
    p("The NPU needs about 66 outstanding 64-byte bursts to reach its 14 "
      "GB/s share - an interconnect or memory controller that supports "
      "only 16 outstanding reads per master would silently cap it at "
      "roughly a quarter of the budget. Numbers like these go straight "
      "into the uArch specs of the DMA engines and the NoC configuration.")

    h2("Clock and power domain planning")
    p("Clocking and power architecture are decided at architecture time "
      "because they shape RTL, verification, DFT and physical design.")
    tbl(["Decision", "Considerations", "Detailed in"], [
        ["Clock sources and frequencies", "PLL count, reference clocks, "
         "frequency plan per block, integer ratios vs asynchronous "
         "domains, jitter needs of PHYs", "Chapters 12, 16"],
        ["Clock domain crossings", "Number of asynchronous domains, "
         "synchroniser strategy, CDC verification", "Companion RTL guide, "
         "Chapter 6"],
        ["Voltage domains", "Which blocks need independent supplies or "
         "DVFS; level shifters; I/O voltages", "Chapter 11"],
        ["Power gating", "Which blocks shut off, retention needs, wake-up "
         "latency, rush current", "Chapters 11, 18"],
        ["Power modes", "A mode table: which domains are on/off, at "
         "which voltage/frequency, in each system state", "Chapter 11"],
        ["Reset architecture", "Reset domains, sequencing, "
         "synchronisers, reset-domain crossings", "Chapter 6"],
    ], widths=[2.0, 4.4, 1.6], bold_first=True)

    h2("IP selection")
    p("Buy-versus-build is decided per block. Buy standard-heavy, "
      "verification-heavy or analog IP (CPU cores, PCIe/USB/DDR controllers "
      "and PHYs, PLLs, memory compilers) unless it is your "
      "differentiation. Build what differentiates you. Evaluate vendors "
      "with the qualification checklist of Chapter 4, and note that IP "
      "choice constrains node choice: the PHY you need may exist in only "
      "one foundry's process or one metal stack.")

    h2("Early die-size and power estimation")
    p("Long before synthesis, the architect must predict die size (it "
      "drives cost, package and yield) and power (it drives package, "
      "thermal solution and battery life). The method is simple and every "
      "input is refined as the project proceeds:")
    bul([
        "**Logic**: estimate each block in NAND2-equivalent gates (GE) "
        "from similar past designs or quick synthesis of key blocks. "
        "Area = GE x NAND2 area / utilisation. In Chapter 4 a real "
        "SKY130 synthesis of a 16-bit MAC gave about 2870 GE (10768 um^2 "
        "/ 3.7536 um^2), so a block of that complexity costs about 0.015 "
        "mm^2 at 70 % utilisation in SKY130.",
        "**Memory**: bits x bitcell area / array efficiency, or better, "
        "the compiler's datasheet for the exact configurations.",
        "**Hard IP**: the vendor's dimensions (PHYs are large and often "
        "fixed to die edges).",
        "**I/O ring and overheads**: pad ring or bump field, seal ring, "
        "scribe line; check whether the die is **pad-limited** (the "
        "perimeter needed by the I/O count exceeds the core-limited size).",
    ])
    code(L(SRC_DIESIZE), caption="diesize.py - early die area, dies per "
         "wafer, yield, die cost and logic power for an edge-AI SoC. All "
         "inputs are stated assumptions.")
    out(L(OUT_DIESIZE), caption="Real output of diesize.py.")
    eq(["Dies per wafer  ~  pi (d/2)^2 / A  -  pi d / sqrt(2 A)",
        "Yield (negative binomial)  Y = (1 + A D0 / alpha)^(-alpha)",
        "Die cost = wafer cost / (dies per wafer * Y)"],
       "Classic early cost formulas (A = die area, D0 = defect density, "
       "alpha = clustering parameter). Chapter 21 treats yield in depth.")
    p("The estimate says: roughly 21 mm^2, a few dollars of die cost, and "
      "about 2.5 W if all logic toggled at 1 GHz simultaneously. The power "
      "figure is a red flag for a fan-less edge device, and exactly the "
      "kind of early warning this exercise exists to produce: the "
      "architect now builds a per-use-case power table (which blocks are "
      "active, at what frequency and voltage), adds clock gating and "
      "power gating assumptions (Chapter 11), and negotiates the target "
      "with product management - long before RTL is written.")
    box("warn", "PITFALL: forgetting the overheads",
        "First estimates routinely miss: DFT logic (scan muxes, "
        "compression, MBIST: often ~5-15 % of logic area), clock tree and "
        "buffering, power-switch and isolation cells, decap and fill, "
        "memory BIST collars, spare cells, I/O and power pads, keep-out "
        "margins around macros, and the utilisation drop caused by routing "
        "congestion. Always carry an explicit margin (commonly 10-20 %) and "
        "revisit it at each milestone.")

    h2("PPA targets and the frequency sanity check")
    p("Architecture concludes with numeric targets per block: frequency "
      "(at the sign-off corner, not typical), area, power per mode, and "
      "latency. A useful sanity check converts the clock period into "
      "gate delays: if the library's FO4 delay at the slow corner is, say, "
      "25 ps, a 1 GHz clock leaves 1000 ps - clock uncertainty and flop "
      "overhead (clock-to-Q + setup, perhaps 100-150 ps) = roughly 34-36 FO4 "
      "of logic per stage. A 64-bit adder plus a mux and a comparator "
      "fits; a 32-bit multiplier does not, and must be pipelined. These "
      "decisions belong in the micro-architecture, not in a late timing "
      "fire-fight.")

    h2("The micro-architecture specification")
    p("Each block then gets a micro-architecture specification (uArch spec) "
      "written by the design owner and reviewed by architecture, "
      "verification, DFT and physical design. A good template:")
    checklist("Micro-architecture specification template", [
        "Overview: purpose, features, block diagram, references to PRD IDs.",
        "Interfaces: every port with direction, width, protocol, timing "
        "(which clock), reset value; bus protocols (see the companion "
        "Communication Protocols guide).",
        "Clocks and resets: domains, frequencies, CDC/RDC crossings and "
        "their synchronisation schemes, clock gating.",
        "Datapath: pipeline diagram with stage-by-stage operations, "
        "widths, latency and throughput; numerical formats and rounding.",
        "Control: FSMs with state diagrams, arbitration, flow control, "
        "back-pressure, error handling.",
        "Memories: sizes, types, ports, ECC/parity, power-down modes, BIST.",
        "Register map: addresses, fields, access types, reset values "
        "(generated from SystemRDL/IP-XACT).",
        "Power: domains, gating, retention, estimated power per mode.",
        "PPA targets: frequency, estimated GE and memory area, floorplan "
        "hints (aspect ratio, pin placement), critical paths.",
        "DFT: scan, test modes, MBIST, observability; debug hooks.",
        "Verification plan hooks: features to verify, assertions, coverage "
        "points, known corner cases.",
        "Safety/security mechanisms if applicable (ECC, lockstep, "
        "parity, access control).",
        "Open issues and revision history.",
    ])

    h2("Reviews, sign-offs and requirement traceability")
    p("Specifications are living documents under version control, and "
      "each major milestone has a formal review: architecture review, "
      "uArch reviews per block, RTL/verification-plan reviews, and later "
      "the tapeout review. Reviews include the downstream teams because "
      "they catch the problems the author cannot see: DFT sees untestable "
      "structures, PD sees a 2000-bit bus crossing the die, verification "
      "sees an unspecified corner case.")
    p("**Traceability** links each PRD requirement to architecture "
      "features, uArch sections, RTL blocks, verification items (tests, "
      "assertions, coverage points) and finally silicon validation tests. "
      "It is mandatory for safety-critical designs (ISO 26262 requires "
      "bidirectional traceability) and good practice everywhere: at "
      "tapeout, the question 'is every must-have requirement verified?' "
      "must have a data-backed answer.")
    diagram([
        "  PRD-017  'Decode 4 x 1080p60 H.264 streams'",
        "     |---> ARCH 3.2  video engine: 2 cores @ 600 MHz, 1.5 GB/s budget",
        "     |       |---> uARCH vdec 4.1  pipeline, 8 KB line buffer",
        "     |       |       |---> RTL  vdec_top.sv, vdec_mc.sv",
        "     |       |       |---> DV   vplan item VDEC-12: 4-stream test, cov 100 %",
        "     |       |---> PERF model run #231: 4 streams at 63 fps (margin 5 %)",
        "     |---> VALIDATION  silicon test VAL-VDEC-04 (post-silicon, Chapter 22)",
    ], "A requirement traced from PRD to silicon validation.")
    box("expert", "Interview insight: 'how would you architect X?'",
        "Architecture interview questions reward a structured answer: "
        "clarify requirements and use cases; estimate compute, memory and "
        "bandwidth with numbers; identify the bottleneck (roofline); "
        "propose a block diagram; state PPA estimates and the key trade-offs; "
        "and say how you would validate the architecture (model, "
        "prototype). Numbers - even rough ones - distinguish a senior answer.")

    h2("Summary")
    bul([
        "Requirements (functional, performance, power, area/cost, schedule, "
        "standards, quality, safety, security) are captured in the MRD and "
        "PRD and must be measurable and testable.",
        "Architecture exploration moves from spreadsheets and roofline "
        "models to performance models and SystemC/TLM virtual platforms. "
        "The roofline ridge point (peak / bandwidth) tells whether a "
        "workload is compute- or memory-bound.",
        "HW/SW partitioning trades flexibility for efficiency; the register "
        "map is the contract, ideally generated from one source.",
        "Size the memory hierarchy from working sets and budget sustained "
        "DRAM bandwidth across concurrent use cases.",
        "Plan clocks, resets, voltage and power domains and the IP list at "
        "architecture time.",
        "Estimate die size (GE x NAND2 area / utilisation + memories + "
        "hard IP + ring), dies per wafer, yield, die cost and power early, "
        "with explicit margins.",
        "Write a uArch spec per block, review it with all downstream teams, "
        "and maintain traceability from PRD to verification and silicon "
        "validation.",
    ])
    h2("Exercises")
    bul([
        "Using roofline.py, how much on-chip reuse (factor on intensity) "
        "would make the depthwise layer compute-bound? What SRAM size does "
        "that imply for a 112 x 112 x 32 INT8 tensor?",
        "Change diesize.py to a 28 nm-class node (NAND2 ~0.5 um^2, bitcell "
        "~0.13 um^2, wafer cost lower) and compare die area and cost. Which "
        "node is cheaper per good die for this design?",
        "Build a mode table (off/retention/on, voltage, frequency) for the "
        "edge-AI SoC with CPU, NPU, ISP and always-on sensor hub domains, "
        "and estimate standby power.",
        "Write the interface section of a uArch spec for a simple DMA engine "
        "with an AXI master port and an APB register port.",
        "Pick three PRD-level requirements of a product you know and show "
        "their traceability chain down to verification items.",
    ], ordered=True)


# =============================================================================
#  Real scripts and their captured output (run with Python 3.11; Liberty = SKY130
#  sky130_fd_sc_hd__tt_025C_1v80.lib; synthesis with Yosys 0.33).
# =============================================================================
SRC_BREAKEVEN = r"""
# Total cost of ownership: FPGA vs ASIC in a mature node vs ASIC in an advanced node.
# All numbers are illustrative round figures in US dollars.
options = {
    #  name              NRE (design+masks+IP)   unit cost (die+package+test)
    "FPGA (mid-range)": (   0.3e6,              120.0),
    "ASIC 28 nm":       (  15.0e6,                6.0),
    "ASIC 5 nm":        ( 120.0e6,                9.0),   # bigger masks, pricier wafers
}

def total(nre, unit, volume):
    return nre + unit * volume

def breakeven(a, b):
    # volume where option a and option b cost the same (None if never)
    (n1, u1), (n2, u2) = options[a], options[b]
    return None if u1 == u2 else (n2 - n1) / (u1 - u2)

print("volume      " + "".join("%18s" % k for k in options))
for vol in (1e4, 1e5, 1e6, 1e7):
    row = "".join("%16.1f M" % (total(*options[k], vol) / 1e6) for k in options)
    print("%-10.0e%s" % (vol, row))
v = breakeven("FPGA (mid-range)", "ASIC 28 nm")
print("FPGA vs 28 nm ASIC break-even : %9.0f units" % v)
print("per-unit cost at 1M units, 28 nm: $%.2f" % (total(*options["ASIC 28 nm"], 1e6) / 1e6))
print("per-unit cost at 1M units, 5 nm : $%.2f" % (total(*options["ASIC 5 nm"], 1e6) / 1e6))
"""

OUT_BREAKEVEN = r"""
volume        FPGA (mid-range)        ASIC 28 nm         ASIC 5 nm
1e+04                  1.5 M            15.1 M           120.1 M
1e+05                 12.3 M            15.6 M           120.9 M
1e+06                120.3 M            21.0 M           129.0 M
1e+07               1200.3 M            75.0 M           210.0 M
FPGA vs 28 nm ASIC break-even :    128947 units
per-unit cost at 1M units, 28 nm: $21.00
per-unit cost at 1M units, 5 nm : $129.00
"""

SRC_ALPHA = r"""
# Alpha-power law (Sakurai-Newton): Id_sat ~ (Vdd - Vth)^alpha, so
#   t_d  ~  C * Vdd / (Vdd - Vth)^alpha        E_switch = C * Vdd^2
VTH, ALPHA, VNOM = 0.35, 1.3, 0.80          # generic FinFET-like numbers

def delay(vdd, vth=VTH, a=ALPHA):
    return vdd / (vdd - vth) ** a

d0, e0 = delay(VNOM), VNOM ** 2
print(" Vdd   delay(norm)  energy(norm)  EDP(norm)")
for vdd in (0.50, 0.55, 0.60, 0.70, 0.80, 0.90, 1.00):
    d, e = delay(vdd) / d0, vdd ** 2 / e0
    print("%4.2f   %9.2f   %10.2f   %9.2f" % (vdd, d, e, d * e))
# Sensitivity: how much does a 30 mV Vth shift hurt at low vs nominal voltage?
for vdd in (0.55, 0.80):
    s = delay(vdd, VTH + 0.03) / delay(vdd) - 1
    print("Vdd=%.2f V: +30 mV Vth -> delay +%.1f %%" % (vdd, 100 * s))
"""

OUT_ALPHA = r"""
 Vdd   delay(norm)  energy(norm)  EDP(norm)
0.50        2.61         0.39        1.02
0.55        1.97         0.47        0.93
0.60        1.61         0.56        0.91
0.70        1.21         0.77        0.93
0.80        1.00         1.00        1.00
0.90        0.87         1.27        1.10
1.00        0.77         1.56        1.21
Vdd=0.55 V: +30 mV Vth -> delay +23.5 %
Vdd=0.80 V: +30 mV Vth -> delay +9.4 %
"""

SRC_LEAK = r"""
# Subthreshold leakage:  I_off = I0 * 10^(-Vth / S),  S = n * (kT/q) * ln(10)
import math
k, q = 1.380649e-23, 1.602176634e-19
for tc in (25, 125):
    vt = k * (tc + 273.15) / q
    print("T=%3d C: kT/q = %.1f mV, ideal S (n=1) = %.1f mV/dec, n=1.3 -> %.1f mV/dec"
          % (tc, 1e3 * vt, 1e3 * vt * math.log(10), 1e3 * 1.3 * vt * math.log(10)))
S = 1.3 * k * 298.15 / q * math.log(10)            # 77 mV/decade at 25 C
I0 = 5e-6                   # A/um at Vgs = Vth (constant-current Vth definition)
print("  Vth(mV)   Ioff (nA/um)   vs 400 mV")
for vth in (200, 250, 300, 350, 400, 450):
    ioff = I0 * 10 ** (-vth / 1e3 / S)
    ref = I0 * 10 ** (-0.400 / S)
    print("  %5d    %11.3f   %8.1fx" % (vth, ioff * 1e9, ioff / ref))
print("leakage ratio per 100 mV of Vth: %.1fx" % 10 ** (0.1 / S))
"""

OUT_LEAK = r"""
T= 25 C: kT/q = 25.7 mV, ideal S (n=1) = 59.2 mV/dec, n=1.3 -> 76.9 mV/dec
T=125 C: kT/q = 34.3 mV, ideal S (n=1) = 79.0 mV/dec, n=1.3 -> 102.7 mV/dec
  Vth(mV)   Ioff (nA/um)   vs 400 mV
    200         12.544      398.6x
    250          2.807       89.2x
    300          0.628       20.0x
    350          0.141        4.5x
    400          0.031        1.0x
    450          0.007        0.2x
leakage ratio per 100 mV of Vth: 20.0x
"""

SRC_LE = r"""
# Logical-effort sizing of a 4-stage path: INV -> NAND2 -> NOR2 -> INV -> load.
# g = logical effort, p = parasitic delay (units of an inverter's), gamma = 2 (Pmos/Nmos)
import math
stages = [("INV", 1.0, 1.0), ("NAND2", 4 / 3, 2.0), ("NOR2", 5 / 3, 2.0), ("INV", 1.0, 1.0)]
c_in, c_load, branching = 1.0, 64.0, 1.0          # capacitances in unit-inverter inputs

G = math.prod(g for _, g, _ in stages)
H = c_load / c_in
F = G * branching * H
N = len(stages)
f_hat = F ** (1 / N)
P = sum(p for _, _, p in stages)
print("G=%.3f  H=%.0f  F=%.1f  stage effort f=%.3f" % (G, H, F, f_hat))
print("minimum delay D = N*f + P = %.2f  (x tau)" % (N * f_hat + P))
# Work backwards from the load: Cin_i = g_i * Cout_i / f_hat
c_out, sizes = c_load, []
for name, g, p in reversed(stages):
    cin = g * c_out / f_hat
    sizes.append((name, cin, g * c_out / cin + p))
    c_out = cin
for name, cin, d in reversed(sizes):
    print("  %-6s input cap = %6.2f   stage delay = %.2f" % (name, cin, d))
print("best number of stages ~ log4(F) = %.2f" % math.log(F, 4))
"""

OUT_LE = r"""
G=2.222  H=64  F=142.2  stage effort f=3.453
minimum delay D = N*f + P = 19.81  (x tau)
  INV    input cap =   1.00   stage delay = 4.45
  NAND2  input cap =   3.45   stage delay = 5.45
  NOR2   input cap =   8.94   stage delay = 5.45
  INV    input cap =  18.53   stage delay = 4.45
best number of stages ~ log4(F) = 3.58
"""

SRC_ELMORE = r"""
# Elmore delay of a driver + distributed RC wire + load, wire cut into n pi-segments.
# Elmore: t = sum over every capacitor of C_k * (resistance shared with the path to it)
R_DRV, C_LOAD = 2000.0, 2e-15            # driver 2 kohm, receiver 2 fF
r_um, c_um = 2.0, 0.2e-15                # ~2 ohm/um, ~0.2 fF/um for a thin local metal

def elmore(length_um, n=50):
    rs, cs = r_um * length_um / n, c_um * length_um / n
    t, r_path = 0.0, R_DRV
    for _ in range(n):
        r_path += rs
        t += r_path * cs                 # each segment's cap sees all R upstream of it
    return t + r_path * C_LOAD

print(" length(um)  Elmore(ps)  wire-only RC/2 (ps)")
for L in (100, 250, 500, 1000, 2000):
    wire = 0.5 * r_um * L * c_um * L
    print("%10d  %10.1f  %12.1f" % (L, 1e12 * elmore(L), 1e12 * wire))
# Doubling length ~quadruples the wire term: this is why long wires get repeaters.
"""

OUT_ELMORE = r"""
 length(um)  Elmore(ps)  wire-only RC/2 (ps)
       100        46.4           2.0
       250       117.8          12.5
       500       257.0          50.0
      1000       612.0         200.0
      2000      1628.0         800.0
"""

SRC_PELGROM = r"""
# Pelgrom mismatch: sigma(dVth) = A_VT / sqrt(W * L)   (pair of identical devices)
# A_VT is typically ~1-5 mV*um for modern nodes; 1.5 mV*um is used here.
import math, random
A_VT = 1.5                                             # mV*um
print("  W(um)   L(um)   area(um2)  sigma_dVth(mV)  6-sigma(mV)")
for w, l in ((0.1, 0.03), (0.2, 0.03), (0.5, 0.05), (1.0, 0.1), (4.0, 0.5), (10, 1)):
    s = A_VT / math.sqrt(w * l)
    print("%7.2f %7.2f %10.4f %13.1f %12.1f" % (w, l, w * l, s, 6 * s))
# Monte Carlo check for the smallest device: draw 100k pairs, compare with formula.
random.seed(1)
s_pair = A_VT / math.sqrt(0.1 * 0.03)
s_dev = s_pair / math.sqrt(2)                          # each device carries 1/sqrt(2)
d = [random.gauss(0, s_dev) - random.gauss(0, s_dev) for _ in range(100000)]
mc = math.sqrt(sum(x * x for x in d) / len(d))
print("Monte Carlo sigma(dVth) = %.1f mV (formula %.1f mV)" % (mc, s_pair))
"""

OUT_PELGROM = r"""
  W(um)   L(um)   area(um2)  sigma_dVth(mV)  6-sigma(mV)
   0.10    0.03     0.0030          27.4        164.3
   0.20    0.03     0.0060          19.4        116.2
   0.50    0.05     0.0250           9.5         56.9
   1.00    0.10     0.1000           4.7         28.5
   4.00    0.50     2.0000           1.1          6.4
  10.00    1.00    10.0000           0.5          2.8
Monte Carlo sigma(dVth) = 27.5 mV (formula 27.4 mV)
"""

SRC_LITHO = r"""
# Rayleigh resolution: half-pitch = k1 * lambda / NA   (k1 >= 0.25 physical limit)
tools = [("KrF dry", 248, 0.93), ("ArF dry", 193, 0.93), ("ArF immersion", 193, 1.35),
         ("EUV (0.33 NA)", 13.5, 0.33), ("High-NA EUV", 13.5, 0.55)]
print("%-15s %6s %5s   hp@k1=0.40  hp@k1=0.28" % ("tool", "lambda", "NA"))
for name, lam, na in tools:
    print("%-15s %6.1f %5.2f   %7.1f nm  %7.1f nm" % (name, lam, na, 0.4 * lam / na,
                                                     0.28 * lam / na))
# A 28 nm metal pitch (14 nm half-pitch) printed with 193i in a single exposure:
k1 = 14 / (193 / 1.35)
print("193i: k1 needed for 14 nm half-pitch = %.3f (below the 0.25 limit)" % k1)
print("pitch must be split by ~%.1fx at k1=0.28 -> quadruple patterning (SAQP)"
      % (0.28 / k1))
"""

OUT_LITHO = r"""
tool            lambda    NA   hp@k1=0.40  hp@k1=0.28
KrF dry          248.0  0.93     106.7 nm     74.7 nm
ArF dry          193.0  0.93      83.0 nm     58.1 nm
ArF immersion    193.0  1.35      57.2 nm     40.0 nm
EUV (0.33 NA)     13.5  0.33      16.4 nm     11.5 nm
High-NA EUV       13.5  0.55       9.8 nm      6.9 nm
193i: k1 needed for 14 nm half-pitch = 0.098 (below the 0.25 limit)
pitch must be split by ~2.9x at k1=0.28 -> quadruple patterning (SAQP)
"""

SRC_LIBSUM = r"""
# Summarise the real SKY130 high-density library (typical corner, 25 C, 1.80 V).
import re, collections
lib = open("sky130_fd_sc_hd__tt_025C_1v80.lib").read()
cells = re.findall(r'cell \("sky130_fd_sc_hd__(\w+)"\)', lib)
print("cells in library:", len(cells))
fam = collections.Counter(re.sub(r"_\d+$", "", c) for c in cells)
print("distinct functions:", len(fam))
for f in ("inv", "clkbuf", "nand2", "dfxtp", "sdfxtp", "dlclkp", "decap",
          "lpflow_isobufsrc", "diode"):
    sizes = sorted(int(c.split("_")[-1]) for c in cells if re.fullmatch(f + r"_\d+", c))
    print("  %-17s drive/size variants: %s" % (f, " ".join(map(str, sizes))))

def cell_block(name):
    i = lib.index('cell ("sky130_fd_sc_hd__%s")' % name)
    depth, j = 0, lib.index("{", i)
    for k in range(j, len(lib)):
        depth += {"{": 1, "}": -1}.get(lib[k], 0)
        if depth == 0:
            return lib[i:k + 1]

print("cell        area(um2)  in cap(fF)  leakage(nW)")
for c in ("inv_1", "nand2_1", "nand2_2", "nand2_4", "nand2_8", "dfxtp_1"):
    b = cell_block(c)
    area = float(re.search(r"area : ([\d.]+)", b).group(1))
    pin = "A" if "nand" in c or "inv" in c else "D"
    cap = float(re.search(r'pin \("%s"\) \{\s*capacitance : ([\d.]+)' % pin, b).group(1))
    leak = float(re.search(r"cell_leakage_power : ([\d.e-]+)", b).group(1))
    print("%-10s %9.3f %10.2f %12.4f" % (c, area, cap * 1e3, leak))
"""

OUT_LIBSUM = r"""
cells in library: 428
distinct functions: 158
  inv               drive/size variants: 1 2 4 6 8 12 16
  clkbuf            drive/size variants: 1 2 4 8 16
  nand2             drive/size variants: 1 2 4 8
  dfxtp             drive/size variants: 1 2 4
  sdfxtp            drive/size variants: 1 2 4
  dlclkp            drive/size variants: 1 2 4
  decap             drive/size variants: 3 4 6 8 12
  lpflow_isobufsrc  drive/size variants: 1 2 4 8 16
  diode             drive/size variants: 2
cell        area(um2)  in cap(fF)  leakage(nW)
inv_1          3.754       2.30       0.0053
nand2_1        3.754       2.31       0.0021
nand2_2        6.256       4.43       0.0025
nand2_4       11.261       8.54       0.0071
nand2_8       20.019      16.93       0.0046
dfxtp_1       20.019       1.68       0.0084
"""

SRC_NLDM = r"""
# NLDM lookup exactly as an STA tool does it: find the surrounding 2x2 grid points
# in (input slew, output load) and interpolate bilinearly (extrapolate at the edges).
import re
lib = open("sky130_fd_sc_hd__tt_025C_1v80.lib").read()

def cell_block(name):                              # same brace matcher as before
    i, depth = lib.index('cell ("sky130_fd_sc_hd__%s")' % name), 0
    for k in range(lib.index("{", i), len(lib)):
        depth += {"{": 1, "}": -1}.get(lib[k], 0)
        if depth == 0:
            return lib[i:k + 1]

def table(block, pin, related, kind):
    # returns (index_1, index_2, values) of table `kind` on the arc related -> pin
    out = block[block.index('pin ("%s")' % pin):]
    for arc in out.split("timing ()")[1:]:
        if 'related_pin : "%s"' % related not in arc:
            continue
        t = arc[arc.index(kind + " ("):]
        nums = lambda key: [float(x) for x in
                            re.search(key + r'\("([^"]+)"\)', t).group(1).split(",")]
        i1, i2 = nums("index_1"), nums("index_2")
        rows = re.search(r'values\((.*?)\);', t, re.S).group(1)
        vals = [[float(x) for x in r.split(",")] for r in re.findall(r'"([^"]+)"', rows)]
        return i1, i2, vals

def seg(axis, x):
    i = max(0, min(len(axis) - 2, sum(1 for a in axis if a <= x) - 1))
    return i, (x - axis[i]) / (axis[i + 1] - axis[i])

def lookup(i1, i2, v, x1, x2):
    i, u = seg(i1, x1)
    j, w = seg(i2, x2)
    return ((1 - u) * (1 - w) * v[i][j] + u * (1 - w) * v[i + 1][j]
            + (1 - u) * w * v[i][j + 1] + u * w * v[i + 1][j + 1])

nand = cell_block("nand2_1")
i1, i2, v = table(nand, "Y", "A", "cell_fall")
print("index_1 (slew, ns):", i1[:4], "...")
print("index_2 (load, pF):", i2[:4], "...")
slew, load = 0.080, 0.0050                         # 80 ps input slew, 5 fF load
print("grid corners used: slew %.4f..%.4f  load %.5f..%.5f" % (i1[2], i1[3], i2[2], i2[3]))
print("A->Y cell_fall at (80 ps, 5 fF) = %.1f ps" % (1e3 * lookup(i1, i2, v, slew, load)))
for kind in ("cell_rise", "fall_transition", "rise_transition"):
    t = table(nand, "Y", "A", kind)
    print("A->Y %-15s = %.1f ps" % (kind, 1e3 * lookup(*t, slew, load)))
ff = cell_block("dfxtp_1")
s1, s2, sv = table(ff, "D", "CLK", "rise_constraint")   # first D arc is setup_rising
print("dfxtp_1 setup (D rise), CLK slew 0.1 ns, D slew 0.1 ns = %.1f ps"
      % (1e3 * lookup(s1, s2, sv, 0.1, 0.1)))
"""

OUT_NLDM = r"""
index_1 (slew, ns): [0.01, 0.0230506, 0.0531329, 0.122474] ...
index_2 (load, pF): [0.0005, 0.00131655, 0.00346659, 0.00912787] ...
grid corners used: slew 0.0531..0.1225  load 0.00347..0.00913
A->Y cell_fall at (80 ps, 5 fF) = 66.4 ps
A->Y cell_rise       = 82.7 ps
A->Y fall_transition = 50.7 ps
A->Y rise_transition = 61.2 ps
dfxtp_1 setup (D rise), CLK slew 0.1 ns, D slew 0.1 ns = 58.7 ps
"""

SRC_ROOFLINE = r"""
# Roofline check for an edge NPU: attainable = min(peak compute, bandwidth * intensity)
PEAK_OPS = 4e12                       # 4 TOPS INT8 (2048 MACs x 2 ops x ~1 GHz)
BW = 2 * 4 * 4266e6                   # LPDDR4x, 2 channels x 32 bit (4 B) x 4266 MT/s
EFF = 0.70                            # sustained DRAM efficiency (refresh, page misses)
bw = BW * EFF
print("peak %.1f TOPS, DRAM %.1f GB/s (sustained %.1f), ridge = %.0f ops/byte"
      % (PEAK_OPS / 1e12, BW / 1e9, bw / 1e9, PEAK_OPS / bw))
# (name, ops, DRAM bytes moved) per layer, weights + activations, INT8
layers = [("conv3x3 64->64 @56x56", 2 * 56 * 56 * 64 * 64 * 9, 56 * 56 * 64 * 2 + 64 * 64 * 9),
          ("depthwise 3x3 @112x112x32", 2 * 112 * 112 * 32 * 9, 112 * 112 * 32 * 2 + 288),
          ("FC 4096->4096 (batch 1)", 2 * 4096 * 4096, 4096 * 4096 + 2 * 4096),
          ("FC 4096->4096 (batch 32)", 2 * 32 * 4096 * 4096, 4096 * 4096 + 64 * 4096)]
print("%-28s %8s %9s %8s" % ("layer", "ops/B", "TOPS", "bound"))
for name, ops, byts in layers:
    ai = ops / byts
    att = min(PEAK_OPS, bw * ai)
    print("%-28s %8.1f %9.2f %8s" % (name, ai, att / 1e12,
                                      "compute" if att == PEAK_OPS else "memory"))
"""

OUT_ROOFLINE = r"""
peak 4.0 TOPS, DRAM 34.1 GB/s (sustained 23.9), ridge = 167 ops/byte
layer                           ops/B      TOPS    bound
conv3x3 64->64 @56x56           527.6      4.00  compute
depthwise 3x3 @112x112x32         9.0      0.21   memory
FC 4096->4096 (batch 1)           2.0      0.05   memory
FC 4096->4096 (batch 32)         63.0      1.51   memory
"""

SRC_LITTLE = r"""
# Little's law sizing: outstanding data = bandwidth x latency
import math
BURST = 64                                       # bytes per AXI burst (e.g. 16 beats x 4 B)
print("%-22s %8s %9s %12s %10s" % ("master", "GB/s", "lat (ns)", "in flight", "bursts"))
for name, gbps, lat_ns in (("CPU cache refills", 4.0, 150), ("NPU weight fetch", 14.0, 300),
                           ("ISP/video DMA", 4.0, 400), ("display (worst lat.)", 1.5, 2000)):
    inflight = gbps * lat_ns                     # GB/s * ns = bytes
    print("%-22s %8.1f %9d %10.0f B %10d" % (name, gbps, lat_ns, inflight,
                                            math.ceil(inflight / BURST)))
# Display FIFO: must hide the worst DRAM stall (e.g. refresh + other masters) of 2 us
stall_ns, drain_gbps = 2000, 1.5
print("display FIFO to hide a %d ns stall: %.0f bytes -> %.1f KB SRAM"
      % (stall_ns, drain_gbps * stall_ns, drain_gbps * stall_ns / 1024))
"""

OUT_LITTLE = r"""
master                     GB/s  lat (ns)    in flight     bursts
CPU cache refills           4.0       150        600 B         10
NPU weight fetch           14.0       300       4200 B         66
ISP/video DMA               4.0       400       1600 B         25
display (worst lat.)        1.5      2000       3000 B         47
display FIFO to hide a 2000 ns stall: 3000 bytes -> 2.9 KB SRAM
"""

SRC_DIESIZE = r"""
# Early die-size, cost and power estimate for an edge-AI SoC. Every input is an
# ASSUMPTION to be replaced by your foundry/IP data; the method is what matters.
import math
NAND2_UM2 = 0.20       # NAND2-equivalent footprint, 16/12 nm-class order of magnitude
UTIL      = 0.65       # std-cell placement utilisation after CTS/buffering headroom
logic_ge  = {"CPU cluster": 6.0e6, "NPU": 9.0e6, "interconnect+periph": 3.0e6,
             "DDR/USB controllers": 1.5e6}
sram_bits = 8 * 8 * 2**20        # 8 MB of on-chip SRAM
BIT_UM2, ARRAY_EFF = 0.074, 0.55  # HD 6T bitcell; periphery shrinks usable fraction
hard_ip_mm2 = {"LPDDR4x PHY": 2.4, "USB3 PHY": 0.8, "PLLs+sensors": 0.4}
logic = sum(logic_ge.values()) * NAND2_UM2 / UTIL / 1e6
sram = sram_bits * BIT_UM2 / ARRAY_EFF / 1e6
core = logic + sram + sum(hard_ip_mm2.values())
die = core * 1.12                                    # IO ring, seal ring, scribe share
print("logic %.1f mm2 (%.1f M GE)  SRAM %.1f mm2  hard IP %.1f mm2"
      % (logic, sum(logic_ge.values()) / 1e6, sram, sum(hard_ip_mm2.values())))
print("die area ~ %.1f mm2  (%.2f mm x %.2f mm)" % (die, math.sqrt(die), math.sqrt(die)))
d = 300.0                                            # wafer diameter, mm
gross = math.pi * (d / 2) ** 2 / die - math.pi * d / math.sqrt(2 * die)
D0 = 0.10                                            # defects/cm2 on a mature line
y = (1 + die / 100 * D0 / 3) ** -3                   # negative binomial, alpha = 3
print("gross dies/wafer %.0f, yield %.1f %%, good dies %.0f" % (gross, 100 * y, gross * y))
print("die cost at $9000/wafer: $%.2f" % (9000 / (gross * y)))
# Dynamic power  P = a * C * V^2 * f  with ~1 fF switched per GE (cell + wire)
a, c_ge, v, f = 0.12, 1.0e-15, 0.80, 1.0e9
p_logic = a * c_ge * sum(logic_ge.values()) * v * v * f
p_clock = 0.35 * p_logic / 0.65                      # clock tree ~35 % of dynamic
p_leak = 0.10 * (p_logic + p_clock)
print("power: logic %.2f W + clock %.2f W + leakage %.2f W = %.2f W (+ SRAM, IO, PHY)"
      % (p_logic, p_clock, p_leak, p_logic + p_clock + p_leak))
"""

OUT_DIESIZE = r"""
logic 6.0 mm2 (19.5 M GE)  SRAM 9.0 mm2  hard IP 3.6 mm2
die area ~ 20.9 mm2  (4.57 mm x 4.57 mm)
gross dies/wafer 3242, yield 97.9 %, good dies 3175
die cost at $9000/wafer: $2.83
power: logic 1.50 W + clock 0.81 W + leakage 0.23 W = 2.53 W (+ SRAM, IO, PHY)
"""

SRC_DONTUSE = r"""
# Mark special-purpose cells dont_use so the mapper never picks them for plain logic.
import re
DONT_USE = r"lpflow_\w+|probe\w*|macro_sparecell|clkdlybuf\w+|dlygate\w+|dlymetal\w+"
src = open("sky130_fd_sc_hd__tt_025C_1v80.lib").read()
pat = re.compile(r'(cell \("sky130_fd_sc_hd__(?:%s)_\d+"\) \{)' % DONT_USE)
dst, n = pat.subn(r'\1\n        dont_use : true;', src)
open("hd_tt_dontuse.lib", "w").write(dst)
print("cells marked dont_use:", n)
"""

OUT_DONTUSE = r"""
cells marked dont_use: 50
"""

SRC_MAC_V = r"""
module mac16 (input clk, input rst_n, input en,
              input [15:0] a, b, output reg [39:0] acc);
  always @(posedge clk or negedge rst_n)
    if (!rst_n)  acc <= 40'd0;
    else if (en) acc <= acc + a * b;
endmodule
"""

SRC_MAC_YS = r"""
read_verilog mac.v
synth -top mac16 -flatten
dfflibmap -liberty hd_tt_dontuse.lib
abc -D 5000 -liberty hd_tt_dontuse.lib
opt_clean
stat -liberty hd_tt_dontuse.lib
"""

OUT_STAT_RAW = r"""
7. Printing statistics.

=== mac16 ===

   Number of wires:               1367
   Number of wire bits:           1436
   Number of public wires:           6
   Number of public wire bits:      75
   Number of memories:               0
   Number of memory bits:            0
   Number of processes:              0
   Number of cells:               1401
     sky130_fd_sc_hd__a21boi_0       3
     sky130_fd_sc_hd__a21o_1         7
     sky130_fd_sc_hd__a21oi_1       72
     sky130_fd_sc_hd__a22o_1        12
     sky130_fd_sc_hd__a22oi_1       48
     sky130_fd_sc_hd__a31o_1         1
     sky130_fd_sc_hd__a31oi_1       24
     sky130_fd_sc_hd__a32o_1         1
     sky130_fd_sc_hd__and2_0        19
     sky130_fd_sc_hd__and3_1        10
     sky130_fd_sc_hd__and4_1        29
     sky130_fd_sc_hd__clkinv_1      42
     sky130_fd_sc_hd__dfrtp_1       40
     sky130_fd_sc_hd__lpflow_inputiso1p_1     15
     sky130_fd_sc_hd__lpflow_isobufsrc_1     49
     sky130_fd_sc_hd__maj3_1       103
     sky130_fd_sc_hd__mux2_1         1
     sky130_fd_sc_hd__nand2_1      217
     sky130_fd_sc_hd__nand2b_1      14
     sky130_fd_sc_hd__nand3_1       14
     sky130_fd_sc_hd__nand4_1       29
     sky130_fd_sc_hd__nor2_1       116
     sky130_fd_sc_hd__nor2b_1       10
     sky130_fd_sc_hd__nor3_1        16
     sky130_fd_sc_hd__nor4b_1        1
     sky130_fd_sc_hd__o2111ai_1      1
     sky130_fd_sc_hd__o211ai_1       1
     sky130_fd_sc_hd__o21a_1        17
     sky130_fd_sc_hd__o21ai_0       62
     sky130_fd_sc_hd__o21ba_1        1
     sky130_fd_sc_hd__o21bai_1       7
     sky130_fd_sc_hd__o22ai_1       10
     sky130_fd_sc_hd__o2bb2ai_1     10
     sky130_fd_sc_hd__o31ai_1        1
     sky130_fd_sc_hd__or3_1          7
     sky130_fd_sc_hd__xnor2_1      198
     sky130_fd_sc_hd__xnor3_1       28
     sky130_fd_sc_hd__xor2_1       142
     sky130_fd_sc_hd__xor3_1        23

   Chip area for module '\mac16': 10720.281600
"""

OUT_STAT_DU = r"""
7. Printing statistics.

=== mac16 ===

   Number of wires:               1382
   Number of wire bits:           1451
   Number of public wires:           6
   Number of public wire bits:      75
   Number of memories:               0
   Number of memory bits:            0
   Number of processes:              0
   Number of cells:               1416
     sky130_fd_sc_hd__a21boi_0       6
     sky130_fd_sc_hd__a21o_1         8
     sky130_fd_sc_hd__a21oi_1       70
     sky130_fd_sc_hd__a22o_1        15
     sky130_fd_sc_hd__a22oi_1       45
     sky130_fd_sc_hd__a31o_1         1
     sky130_fd_sc_hd__a31oi_1       28
     sky130_fd_sc_hd__a32o_1         1
     sky130_fd_sc_hd__and2_0        19
     sky130_fd_sc_hd__and3_1        11
     sky130_fd_sc_hd__and4_1        31
     sky130_fd_sc_hd__clkinv_1      54
     sky130_fd_sc_hd__dfrtp_1       40
     sky130_fd_sc_hd__maj3_1       101
     sky130_fd_sc_hd__nand2_1      226
     sky130_fd_sc_hd__nand2b_1      18
     sky130_fd_sc_hd__nand3_1       15
     sky130_fd_sc_hd__nand4_1       27
     sky130_fd_sc_hd__nor2_1       133
     sky130_fd_sc_hd__nor2b_1       26
     sky130_fd_sc_hd__nor3_1        10
     sky130_fd_sc_hd__nor3b_1        1
     sky130_fd_sc_hd__o2111ai_1      1
     sky130_fd_sc_hd__o211ai_1       1
     sky130_fd_sc_hd__o21a_1        16
     sky130_fd_sc_hd__o21ai_0       62
     sky130_fd_sc_hd__o21ba_1        1
     sky130_fd_sc_hd__o21bai_1       9
     sky130_fd_sc_hd__o22ai_1        7
     sky130_fd_sc_hd__o2bb2ai_1     10
     sky130_fd_sc_hd__o31ai_1        1
     sky130_fd_sc_hd__o32a_1         1
     sky130_fd_sc_hd__or2_0         12
     sky130_fd_sc_hd__or3_1         10
     sky130_fd_sc_hd__or4b_1         1
     sky130_fd_sc_hd__xnor2_1      211
     sky130_fd_sc_hd__xnor3_1       29
     sky130_fd_sc_hd__xor2_1       135
     sky130_fd_sc_hd__xor3_1        23

   Chip area for module '\mac16': 10767.827200
"""
LIB_HEAD = r"""
library ("sky130_fd_sc_hd__tt_025C_1v80") {
    ...
technology("cmos");
delay_model : "table_lookup";
bus_naming_style : "%s[%d]";
time_unit : "1ns";
voltage_unit : "1V";
leakage_power_unit : "1nW";
current_unit : "1mA";
pulling_resistance_unit : "1kohm";
capacitive_load_unit(1.0000000000, "pf");
revision : 1.0000000000;
    ...
operating_conditions ("tt_025C_1v80") {
    voltage : 1.8000000000;
    process : 1.0000000000;
    temperature : 25.000000000;
    tree_type : "balanced_tree";
}
    ...
lu_table_template ("del_1_7_7") {
    variable_1 : "input_net_transition";
    variable_2 : "total_output_net_capacitance";
    index_1("1, 2, 3, 4, 5, 6, 7");
    index_2("1, 2, 3, 4, 5, 6, 7");
}
"""

LIB_NAND2 = r"""
cell ("sky130_fd_sc_hd__nand2_1") {
    leakage_power () {
        value : 0.0002796000;
        when : "!A&B";
    }
        ...   (3 more state-dependent leakage_power groups)
    area : 3.7536000000;
    cell_footprint : "sky130_fd_sc_hd__nand2";
    cell_leakage_power : 0.0021179600;
        ...   (pg_pin groups VGND, VNB, VPB, VPWR)
    pin ("A") {
        capacitance : 0.0023150000;
        clock : "false";
        direction : "input";
        fall_capacitance : 0.0022540000;
            ...   (internal_power tables)
        max_transition : 1.5000000000;
        related_ground_pin : "VGND";
        related_power_pin : "VPWR";
        rise_capacitance : 0.0023750000;
    }
        ...   (pin B is similar)
    pin ("Y") {
        direction : "output";
        function : "(!A) | (!B)";
            ...   (internal_power, one group per related_pin)
        max_capacitance : 0.1666360000;
        max_transition : 1.4963760000;
        timing () {
            cell_fall ("del_1_7_7") {
                index_1("0.0100000000, 0.0230506000, 0.0531329000, 0.1224740000, 0.282311 ...
                index_2("0.0005000000, 0.0013165500, 0.0034665900, 0.0091278700, 0.024034 ...
                values("0.0206305000, 0.0250594000, 0.0363371000, 0.0651531000, 0.1403625 ...
                    "0.0243797000, 0.0289316000, 0.0403352000, 0.0696727000, 0.1447142000 ...
                    "0.0327052000, 0.0384095000, 0.0504824000, 0.0797753000, 0.1551681000 ...
                    "0.0428315000, 0.0514229000, 0.0698132000, 0.1038626000, 0.1794323000 ...
                    "0.0525334000, 0.0659547000, 0.0937839000, 0.1461446000, 0.2370110000 ...
                    "0.0550564000, 0.0754976000, 0.1173683000, 0.1976946000, 0.3328764000 ...
                    "0.0332144000, 0.0632894000, 0.1271843000, 0.2473768000, 0.4578195000 ...
                ...   (cell_rise, fall_transition tables)
            related_pin : "A";
                ...   (rise_transition table)
            timing_sense : "negative_unate";
            timing_type : "combinational";
        }
            ...   (second timing group for related_pin "B")
"""

LIB_DFF = r"""
cell ("sky130_fd_sc_hd__dfxtp_1") {
        ...
    ff ("IQ","IQ_N") {
        clocked_on : "CLK";
        next_state : "D";
    }
        ...
    pin ("D") {
        capacitance : 0.0016780000;
            ...
        timing () {
            fall_constraint ("vio_3_3_1") {
                index_1("0.0100000000, 0.5000000000, 1.5000000000");
                index_2("0.0100000000, 0.5000000000, 1.5000000000");
                values("0.1033184000, 0.3187643000, 0.6206849000", \
                    "-0.010809200, 0.1997539000, 0.4980123000", \
                    "-0.096665400, 0.1090150000, 0.4036113000");
                ...   (rise_constraint table)
            timing_type : "setup_rising";
            }
            timing () { ...  related_pin : "CLK" ...
            timing_type : "hold_rising";
            }
"""

LIB_ICG = r"""
cell ("sky130_fd_sc_hd__dlclkp_1") {
        ...
    clock_gating_integrated_cell : "latch_posedge";
        ...
    pin ("CLK") {
        clock_gate_clock_pin : "true";
        direction : "input";
        ...
    pin ("GATE") {
        clock_gate_enable_pin : "true";
        direction : "input";
        ...
            timing_type : "setup_rising";
        ...
    pin ("GCLK") {
        clock_gate_out_pin : "true";
        direction : "output";
        ...
        state_function : "(CLK*M0)";
        ...
            timing_type : "combinational";
        ...
    pin ("M0") {
        direction : "internal";
        internal_node : "M0";
        ...
    statetable ("CLK GATE","M0") {
        table : "L L : - : L,L H : - : H,H - : - : N";
    }
"""

TLEF = r"""
SITE unithd
  SYMMETRY Y ;
  CLASS CORE ;
  SIZE 0.46 BY 2.72 ;
END unithd

LAYER met1
  TYPE ROUTING ;
  DIRECTION HORIZONTAL ;
  PITCH 0.34 ;
  OFFSET 0.17 ;
  WIDTH 0.14 ;                     # Met1 1
  # SPACING 0.14 ;                 # Met1 2
"""

LEF_NAND2 = r"""
MACRO sky130_fd_sc_hd__nand2_1
  CLASS CORE ;
  FOREIGN sky130_fd_sc_hd__nand2_1 ;
  ORIGIN  0.000000  0.000000 ;
  SIZE  1.380000 BY  2.720000 ;
  SYMMETRY X Y R90 ;
  SITE unithd ;
  PIN A
    ANTENNAGATEAREA  0.247500 ;
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER li1 ;
        RECT 0.940000 1.075000 1.275000 1.325000 ;
    END
  END A
  ...   (PIN B and PIN Y are similar)
  PIN VPWR
    DIRECTION INOUT ;
    SHAPE ABUTMENT ;
    USE POWER ;
    PORT
      LAYER met1 ;
        RECT 0.000000 2.480000 1.380000 2.960000 ;
    END
  END VPWR
  OBS
    LAYER li1 ;
      RECT 0.000000 -0.085000 1.380000 0.085000 ;
      RECT 0.000000  2.635000 1.380000 2.805000 ;
    ...
  END
END sky130_fd_sc_hd__nand2_1
"""
