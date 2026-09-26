"""Part I - Foundations (chapters 1-4) of the RTL guide.

Every Verilog/SystemVerilog example paired with an out() card was simulated
with Icarus Verilog 12 (iverilog -g2012 -Wall / vvp) and the output pasted.
"""

from rtl_guide.common import *  # noqa: F401,F403


def V(s):
    """Verilog source as a code() block: strip the leading/trailing newline."""
    return s.strip("\n").split("\n")


def part1():
    part("Foundations",
         "Where RTL sits in the journey from a product idea to working silicon; "
         "the digital-logic facts every RTL line depends on; the synthesizable "
         "core of Verilog and SystemVerilog; and the simulation semantics - "
         "the event scheduler, blocking versus non-blocking assignment, and "
         "races - that separate RTL that merely simulates from RTL that is "
         "correct.")
    _ch1()
    _ch2()
    _ch3()
    _ch4()


# =============================================================================
#  Chapter 1 - RTL in the SoC/ASIC flow, and the roadmap
# =============================================================================
def _ch1():
    chapter("RTL in the SoC/ASIC Flow, and the Roadmap", newpage=False)
    p("Every modern chip - the application processor in a phone, the "
      "controller in an SSD, the neural accelerator in a smart camera - "
      "began life as text. Not as a schematic, and not as transistors, but "
      "as tens or hundreds of thousands of lines of **register-transfer "
      "level** (RTL) code written in Verilog, SystemVerilog or VHDL. That "
      "text is the single most important artefact in a chip project: it is "
      "the contract between the architects who decided what the chip does "
      "and the implementation tools that decide how it is built.")
    p("This book teaches you to write that text well - from the first "
      "`always_ff` to AXI interconnect, clock-domain crossings, low-power "
      "intent and timing closure - and to see, behind every line, the "
      "hardware it becomes. This first chapter draws the map: what RTL is, "
      "where it sits in the flow from specification to silicon, who the "
      "people around you are, and which chapter teaches which skill.")

    h2("What 'register-transfer level' means")
    p("A synchronous digital design is a set of **registers** (flip-flops) "
      "separated by clouds of **combinational logic**. On every active clock "
      "edge each register captures a new value, computed by the logic from "
      "the current register values and the primary inputs. RTL describes a "
      "design in exactly those terms: __which registers exist__, and __what "
      "function of the current state is transferred into each register on "
      "each clock edge__. It deliberately says nothing about which gates, "
      "which transistors, or where on the die.")
    diagram([
        "              +-----------------+            +-----------------+",
        "  inputs ---->|                 |            |                 |----> outputs",
        "              |  combinational  |   +---+    |  combinational  |",
        "   +--------->|  logic  (next-  |-->| D |--->|  logic  (output |",
        "   |          |  state function)|   |   |    |  function)      |",
        "   |          +-----------------+   |>  |    +-----------------+",
        "   |                                +---+ Q",
        "   |          state register ---------|--------------------+",
        "   +---------------------------------------------------------+",
        "",
        "   RTL = 'on each clock edge, register <= f(registers, inputs)'",
    ], "Figure 1.1 - The register-transfer abstraction: registers hold state, "
       "combinational logic computes the next state between clock edges.")
    p("A one-line example makes the idea concrete. The statement below says: "
      "on each rising edge of `clk`, the register `count` takes the value "
      "`count + 1` unless `clear` is asserted. From it a synthesis tool "
      "infers an adder, a 2:1 multiplexer and a bank of flip-flops - and "
      "chooses the adder architecture (ripple, carry-lookahead, "
      "prefix) that meets your clock period.")
    code(V("""
always_ff @(posedge clk)
  if (clear) count <= '0;
  else       count <= count + 1'b1;
"""), "The essence of RTL: state (count), a clock edge, and a transfer "
      "function. Chapter 6 builds on exactly this pattern.")

    h2("Levels of abstraction")
    p("Hardware is described at several levels, each trading detail for "
      "speed of thought and simulation. RTL occupies a sweet spot: detailed "
      "enough that a tool can build the hardware automatically and predict "
      "its timing, abstract enough that one engineer can describe a million "
      "gates.")
    tbl(["Level", "What is described", "Typical language / artefact",
         "Who works here"],
        [["System / algorithm", "Functions and data flow, no timing or clocks",
          "C/C++, Python, MATLAB, SystemC untimed", "Architects, algorithm "
          "engineers"],
         ["Transaction level (TLM)", "Components exchanging transactions "
          "(a whole burst, a whole packet); approximate timing",
          "SystemC TLM-2.0, SV classes", "Architects, virtual-platform and "
          "software teams"],
         ["**Register-transfer (RTL)**", "Registers, clocks, and the "
          "combinational logic between them; cycle-accurate",
          "Verilog, SystemVerilog, VHDL; also HLS output, Chisel",
          "**RTL designers**, DV engineers"],
         ["Gate level", "A netlist of standard cells (NAND2, DFF, MUX2) from "
          "a specific library", "Verilog netlist, .lib timing models",
          "Synthesis, DFT, STA engineers"],
         ["Transistor level", "MOSFETs, sizes, parasitics",
          "SPICE netlists", "Circuit and library designers"],
         ["Layout / physical", "Polygons on mask layers; placement and "
          "routing", "GDSII / OASIS, DEF, LEF", "Physical-design and layout "
          "engineers"]],
        widths=[19, 32, 27, 22], bold_first=True,
        caption="Table 1.1 - Abstraction levels. Each step down is performed "
                "largely automatically by tools, guided by constraints.")
    box("key", "RTL is the last level a human writes by hand",
        "Below RTL, almost everything is generated: synthesis produces the "
        "gate netlist, place-and-route produces the layout. That is why RTL "
        "quality dominates chip quality. A clumsy RTL architecture cannot be "
        "rescued by a tool; a well-structured one lets every downstream tool "
        "do its best work.")

    h2("The ASIC flow, from specification to silicon")
    p("A chip project is a pipeline of transformations, each with its own "
      "specialists, tools and sign-off criteria. The diagram below is the "
      "backbone of this whole book; keep it in mind, because every RTL "
      "decision is judged by what it does to the stages after it.")
    diagram([
        "  +--------------+   +---------------+   +------------------+",
        "  | Specification|-->| Architecture  |-->| Microarchitecture|",
        "  | (what & why) |   | (blocks, PPA  |   | (pipelines, FSMs,|",
        "  +--------------+   |  budget, bus) |   |  FIFOs, timing)  |",
        "                     +---------------+   +--------+---------+",
        "                                                  |",
        "        +-----------------------------------------+",
        "        v",
        "  +-----------+    +---------------------+    +------------------+",
        "  |    RTL    |<-->| Functional verif.   |    | Static checks:   |",
        "  | (Verilog/ |    | (sim, UVM, formal,  |<-->| lint, CDC, RDC   |",
        "  |  SV code) |    |  coverage closure)  |    |                  |",
        "  +-----+-----+    +---------------------+    +------------------+",
        "        | RTL freeze",
        "        v",
        "  +-----------+    +-----------+    +-----------------+    +------------+",
        "  | Synthesis |--->| DFT       |--->| Place & route   |--->| STA, power,|",
        "  | + LEC     |    | (scan,    |    | (floorplan, CTS,|    | IR/EM, DRC/|",
        "  | (Ch 17)   |    |  BIST)    |    |  routing)       |    | LVS signoff|",
        "  +-----------+    +-----------+    +-----------------+    +-----+------+",
        "                                                                  |",
        "  +-------------------+    +-------------------+    +------------+",
        "  | Silicon bring-up, |<---| Fab, package,     |<---|  Tapeout   |",
        "  | characterisation  |    | wafer test (ATE)  |    |  (GDSII)   |",
        "  +-------------------+    +-------------------+    +------------+",
    ], "Figure 1.2 - The ASIC flow. Arrows between RTL and verification "
       "iterate hundreds of times; after RTL freeze, changes become ECOs "
       "(engineering change orders) and get very expensive.")
    tbl(["Stage", "Input -> output", "Main question answered",
         "Where in this book"],
        [["Specification", "Market/customer needs -> spec document",
          "What must the chip do, at what cost, power and speed?", "Ch 30"],
         ["Architecture", "Spec -> block diagram, memory map, PPA budgets",
          "Which blocks, which buses, how much memory, what clock rates?",
          "Ch 13-16, 21"],
         ["Microarchitecture", "Architecture -> per-block design doc",
          "How many pipeline stages, which FSMs, how deep the FIFOs?",
          "Ch 5-10"],
         ["RTL coding", "Microarchitecture -> synthesizable SV",
          "Is the hardware described exactly, and only, as intended?",
          "Ch 3-16, 27"],
         ["Functional verification", "RTL + spec -> coverage, bug reports",
          "Does the RTL do what the spec says in all cases?", "Ch 22-26"],
         ["Synthesis + LEC", "RTL + SDC + library -> gate netlist",
          "Can this RTL be built at the target frequency and area?", "Ch 17"],
         ["DFT", "Netlist -> scan-inserted netlist, test patterns",
          "Can every manufactured die be tested for defects?", "Ch 20"],
         ["Place & route", "Netlist -> placed, clock-treed, routed layout",
          "Does it physically fit, and can the wires be routed?", "Ch 21"],
         ["STA / signoff", "Layout parasitics -> timing, power, IR reports",
          "Does it meet timing in every corner and mode?", "Ch 18, 19"],
         ["Tapeout", "Signed-off GDSII -> mask set",
          "Is everything clean? (a mask set can cost millions)", "-"],
         ["Bring-up", "First silicon -> working product",
          "Does the real chip boot, and do the numbers match?", "Ch 26"]],
        widths=[16, 27, 38, 12], bold_first=True,
        caption="Table 1.2 - Flow stages, their artefacts and the chapters "
                "that prepare you for each.")
    box("note", "Front end and back end",
        "Industry splits the flow into the **front end** (spec, architecture, "
        "RTL, verification - up to a synthesizable, verified RTL release) and "
        "the **back end** (synthesis onwards). RTL designers live in the "
        "front end, but the best ones think constantly about the back end: "
        "timing paths, congestion, clock gating, testability. Part IV of "
        "this book exists to build that instinct.")
    box("expert", "Why late bugs cost so much",
        "A bug found in simulation costs minutes to fix. After RTL freeze it "
        "needs a netlist ECO and re-verification of timing. After tapeout it "
        "needs a metal-layer respin (weeks, and a partial mask set) or a full "
        "respin (months, and millions of dollars) - or a software "
        "workaround that ships forever. This cost curve is why verification "
        "consumes more engineering effort than design on most projects, and "
        "why good RTL designers write code that is easy to verify.")

    h2("Anatomy of a System-on-Chip")
    p("A **System-on-Chip (SoC)** integrates what used to be a board full of "
      "chips: processors, memory, interconnect and peripherals on one die. "
      "Most of an SoC's RTL is not the CPU - which is usually licensed IP - "
      "but the glue, the peripherals, the accelerators and the "
      "infrastructure around them. That is where most RTL designers work.")
    diagram([
        "  +----------------------------------------------------------------------+",
        "  |  +--------+  +--------+  +------------+  +------------------------+  |",
        "  |  | CPU    |  | CPU    |  | GPU / DSP  |  | ML accelerator (NPU)   |  |",
        "  |  | core 0 |  | core 1 |  |            |  | MAC array + SRAM       |  |",
        "  |  +---+----+  +---+----+  +-----+------+  +-----------+------------+  |",
        "  |      |  L2 cache |             |                     |               |",
        "  |  ====+===========+=============+=====================+=====(AXI)==   |",
        "  |      |        main interconnect / NoC (Ch 13-14)     |               |",
        "  |  ====+==========+==============+==========+===========+============   |",
        "  |      |          |              |          |           |               |",
        "  |  +---+----+ +---+-----+  +-----+----+ +---+----+ +----+----------+   |",
        "  |  | DDR    | | on-chip |  | DMA      | | AXI-to | | security,     |   |",
        "  |  | ctrl + | | SRAM,   |  | engine   | | APB    | | debug (JTAG)  |   |",
        "  |  | PHY    | | ROM     |  | (Ch 16)  | | bridge | |               |   |",
        "  |  +--------+ +---------+  +----------+ +---+----+ +---------------+   |",
        "  |                                          | APB (low-speed bus)      |",
        "  |           +--------+--------+--------+---+----+--------+             |",
        "  |           | UART   | SPI    | I2C    | GPIO    | timers |             |",
        "  |           +--------+--------+--------+---------+--------+             |",
        "  |  clock gen (PLLs), reset ctrl, power ctrl (PMU), interrupt ctrl      |",
        "  +----------------------------------------------------------------------+",
    ], "Figure 1.3 - A representative SoC. High-bandwidth masters and slaves "
       "sit on AXI; slow peripherals hang off APB behind a bridge.")
    tbl(["Subsystem", "Role", "Typical RTL work"],
        [["Processor complex", "CPU cores, caches, interrupt controller",
          "Integration, wrappers, debug and interrupt wiring (Ch 16)"],
         ["Interconnect", "Moves transactions between masters and slaves",
          "Crossbars, arbiters, bridges, width/clock converters (Ch 13-14)"],
         ["Memories", "SRAMs, ROM, register files, DDR controller",
          "Memory wrappers, ECC, FIFOs, arbitration (Ch 9)"],
         ["Peripherals", "UART, SPI, I2C, GPIO, timers, watchdog",
          "Complete blocks with CSRs and interrupts (Ch 15, 28)"],
         ["Accelerators", "Fixed-function engines: crypto, video, ML",
          "Datapaths, pipelines, streaming interfaces (Ch 8, 10, 29)"],
         ["Clock / reset / power", "PLLs, dividers, reset sequencing, power "
          "domains", "CDC synchronizers, reset controllers, UPF (Ch 11, 12, 19)"],
         ["Test and debug", "Scan, MBIST, JTAG, trace",
          "Mostly inserted by tools, but RTL must allow it (Ch 20)"]],
        widths=[20, 36, 44], bold_first=True)

    h2("FPGA versus ASIC")
    p("The same RTL can target an **FPGA** (a field-programmable gate array: "
      "a sea of lookup tables, flip-flops, block RAMs and DSP slices, "
      "configured by a bitstream) or an **ASIC** (application-specific "
      "integrated circuit: standard cells fabricated for you). The language "
      "is the same; the priorities are not.")
    tbl(["Aspect", "FPGA", "ASIC"],
        [["Up-front cost", "Low: buy a board", "Very high: masks, EDA "
          "licences, IP, team"],
         ["Unit cost / power / speed", "High / high / 100s of MHz",
          "Low / low / GHz possible"],
         ["Iteration time", "Minutes to hours (rebuild the bitstream)",
          "Months per silicon spin"],
         ["Primitives", "LUTs, FFs, BRAM, DSP48-style slices",
          "Standard-cell library, SRAM compilers, analog IP"],
         ["Resets", "Global set/reset free at configuration; sync reset "
          "often preferred", "Reset is a design decision with area and "
          "timing cost (Ch 12)"],
         ["Clocking", "Dedicated clock networks, MMCMs/PLLs; clock gating "
          "discouraged", "Clock tree built by CTS; clock gating is the main "
          "power lever (Ch 19)"],
         ["Testability", "Not needed (the fabric is pre-tested)",
          "Scan and BIST mandatory (Ch 20)"],
         ["Role in ASIC projects", "Prototyping and emulation (Ch 26)",
          "The product"]],
        widths=[22, 39, 39], bold_first=True)
    box("tip", "Write portable RTL",
        "Code that is clean for ASIC is almost always clean for FPGA, not "
        "the other way round. Keep technology-specific cells (clock gates, "
        "SRAM macros, synchronizers) behind small wrapper modules so the "
        "same RTL can be prototyped on an FPGA and taped out as an ASIC.")

    h2("The people around the RTL designer")
    tbl(["Role", "Owns", "What they need from your RTL"],
        [["Architect", "Spec, block partitioning, PPA budgets",
          "Faithful implementation; early feedback when a budget is "
          "unrealistic"],
         ["**RTL / design engineer**", "Microarchitecture and RTL of blocks",
          "- (this book)"],
         ["Design verification (DV)", "Testbenches, UVM, coverage, formal",
          "Clear interfaces, assertions, a microarchitecture document, "
          "debuggable code"],
         ["DFT engineer", "Scan, compression, MBIST, JTAG, ATPG",
          "Controllable clocks and resets, no untestable structures (Ch 20)"],
         ["Synthesis / STA engineer", "Constraints, netlist, timing closure",
          "Sensible pipelining, clean SDC-friendly clocking, no "
          "combinational loops (Ch 17-18)"],
         ["Physical design (PD)", "Floorplan, placement, CTS, routing",
          "Reasonable fan-out and congestion, registered block boundaries "
          "(Ch 21)"],
         ["Firmware / software", "Drivers, boot code",
          "A sane register map, documented reset values and interrupts "
          "(Ch 15)"],
         ["Post-silicon validation", "Bring-up, characterisation",
          "Debug visibility: status registers, counters, trace (Ch 26)"]],
        widths=[22, 33, 45], bold_first=True,
        caption="Table 1.3 - Your RTL is consumed by everyone in this table. "
                "Senior designers are defined by how well they serve them.")

    h2("The roadmap: how this book is organised")
    p("The chapters follow the flow. Part I lays the foundations; Part II "
      "builds the blocks every design is made of; Part III assembles them "
      "into an SoC; Part IV makes the RTL implementable; Part V proves it "
      "correct; Part VI ties everything together in projects and a career "
      "plan. Each row below names the skill a chapter builds and the flow "
      "stage it serves.")
    tbl(["Ch", "Topic", "Skill you gain", "Flow stage"],
        [["1", "RTL in the SoC/ASIC flow", "The map; vocabulary", "All"],
         ["2", "Digital logic essentials", "Timing, number systems, "
          "flops vs latches", "Microarch., RTL"],
         ["3", "Verilog & SystemVerilog", "The synthesizable language", "RTL"],
         ["4", "Simulation semantics", "Race-free coding; NBA vs blocking",
          "RTL, DV"],
         ["5", "Combinational logic", "Muxes, decoders, priority logic, "
          "latch avoidance", "RTL"],
         ["6", "Sequential logic", "Flops, resets, enables, counters", "RTL"],
         ["7", "Finite state machines", "FSM styles, encoding, safety",
          "Microarch., RTL"],
         ["8", "Datapath & arithmetic", "Adders, multipliers, fixed point",
          "Microarch., RTL"],
         ["9", "Memories & FIFOs", "SRAM inference, register files, FIFOs",
          "Microarch., RTL"],
         ["10", "Pipelining & handshakes", "valid/ready, back-pressure, skid "
          "buffers", "Microarch., RTL"],
         ["11", "Clocks & CDC", "Synchronizers, async FIFOs", "Arch., RTL, "
          "signoff"],
         ["12", "Reset architecture & RDC", "Sync/async reset, sequencing",
          "Arch., RTL"],
         ["13", "On-chip buses", "APB, AHB, AXI4, AXI-Lite, AXI-Stream",
          "Arch., RTL"],
         ["14", "Interconnect & NoCs", "Arbitration, decoding, memory maps",
          "Arch., RTL"],
         ["15", "CSRs & interrupts", "Register maps, generation flows",
          "RTL, firmware"],
         ["16", "Peripherals, DMA, CPU integration", "SoC assembly", "RTL, "
          "integration"],
         ["17", "Logic synthesis", "What RTL becomes; QoR", "Synthesis"],
         ["18", "Timing: STA & SDC", "Constraints, timing closure from RTL",
          "Synthesis, STA"],
         ["19", "Low-power RTL & UPF", "Clock gating, power domains",
          "RTL, implementation"],
         ["20", "Design for test", "Scan, BIST, JTAG awareness", "DFT"],
         ["21", "PPA & PD hand-off", "Floorplan-aware RTL", "Implementation"],
         ["22", "Self-checking testbenches", "Stimulus, checkers, scoreboards",
          "DV"],
         ["23", "Assertions & coverage", "SVA, covergroups", "DV, formal"],
         ["24", "UVM", "Agents, sequences, environments", "DV"],
         ["25", "Static signoff", "Lint, CDC/RDC, formal, LEC", "Signoff"],
         ["26", "Debug, GLS, FPGA, emulation", "Finding bugs at every level",
          "DV, bring-up"],
         ["27", "Coding guidelines & reviews", "Professional RTL style",
          "RTL"],
         ["28", "Project: APB UART", "A complete verified peripheral",
          "Full front end"],
         ["29", "Project: AXI-Stream MAC", "An ML accelerator datapath",
          "Full front end"],
         ["30", "Career roadmap", "Study plan, portfolio, interviews", "-"],
         ["A-D", "Appendices", "Quick reference, glossary, 100 interview "
          "questions, tools", "-"]],
        widths=[6, 28, 40, 18],
        caption="Table 1.4 - The roadmap. Read Parts I-II in order; later "
                "parts can be read by need.")
    box("tip", "How to use this book",
        "Type in and run the examples. Every design and testbench with a "
        "green output card was simulated with the free Icarus Verilog "
        "simulator (`iverilog -g2012 -Wall`, then `vvp`); the output shown "
        "is the real output. Pair it with a waveform viewer (GTKWave or "
        "Surfer) and the free Yosys synthesizer to see the gates your code "
        "produces - Chapter 17 shows how.")

    h2("Summary")
    bul([
        "RTL describes a design as registers plus the combinational logic "
        "that computes their next values on each clock edge. It is the last "
        "level engineers write by hand.",
        "The ASIC flow runs spec -> architecture -> microarchitecture -> RTL "
        "-> verification -> synthesis -> DFT -> P&R -> STA/signoff -> "
        "tapeout -> bring-up. The cost of a bug rises steeply along it.",
        "An SoC is CPUs, interconnect, memories, peripherals and "
        "accelerators, held together by clock, reset and power "
        "infrastructure - most RTL work is in that infrastructure.",
        "FPGA and ASIC share the language but differ in cost, speed, "
        "resets, clocking and testability.",
        "Good RTL serves its consumers: DV, DFT, synthesis, STA, PD and "
        "firmware.",
    ])
    h2("Exercises")
    bul([
        "Name the six abstraction levels and, for each, one artefact a chip "
        "project produces at that level.",
        "Draw the ASIC flow from memory. Mark where an RTL bug would be "
        "found by (a) simulation, (b) equivalence checking, (c) STA, (d) "
        "silicon bring-up, and estimate the relative cost of each fix.",
        "For the SoC of Figure 1.3, list which blocks are masters and which "
        "are slaves on the interconnect. Why does a DMA engine need to be "
        "both?",
        "Give three reasons an FPGA prototype of an ASIC might run a design "
        "at 50 MHz when the ASIC targets 1 GHz, and one bug class the "
        "prototype can still find.",
        "Pick a chip you use daily (phone SoC, microcontroller, SSD "
        "controller). Using public datasheets, sketch its block diagram in "
        "the style of Figure 1.3.",
    ], ordered=True)


# =============================================================================
#  Chapter 2 - Digital logic essentials
# =============================================================================
def _ch2():
    chapter("Digital Logic Essentials for RTL Designers")
    p("RTL is a notation for digital logic, and every line you write inherits "
      "the physics and arithmetic underneath it. This chapter is a focused "
      "refresher on the facts that matter most when writing and reviewing "
      "RTL: how numbers are represented, which gates and building blocks "
      "your code turns into, how latches differ from flip-flops, and the "
      "timing equations that decide how fast a design can run. If you have "
      "taken a digital-logic course, skim it - but do not skip the timing "
      "section.")

    h2("Number systems and notation")
    p("Hardware stores bits; humans read decimal. RTL uses binary for bit "
      "patterns, hexadecimal for wide buses (one hex digit = 4 bits), and "
      "decimal for counts and constants. Verilog literals carry an explicit "
      "width and base: `8'hA5`, `4'b1010`, `12'd100`. The underscore is a "
      "visual separator: `32'hDEAD_BEEF`.")
    tbl(["Decimal", "Binary (8-bit)", "Hex", "Verilog literal"],
        [["5", "0000_0101", "05", "`8'd5`, `8'h05`, `8'b101`"],
         ["165", "1010_0101", "A5", "`8'hA5`"],
         ["255", "1111_1111", "FF", "`8'hFF`, `'1` (all ones, any width)"],
         ["-1 (signed)", "1111_1111", "FF", "`-8'sd1`"],
         ["-128 (signed)", "1000_0000", "80", "`-8'sd128`"]],
        widths=[18, 22, 12, 48])
    box("warn", "Unsized literals are 32 bits",
        "A literal without a width, such as `5` or `'hFF`, is at least 32 "
        "bits wide and (for plain decimals) signed. This silently widens "
        "expressions, as Chapter 3 shows. In RTL, size every literal: "
        "`4'd5`, not `5`. The fill literals `'0`, `'1`, `'x`, `'z` are the "
        "exception - they deliberately stretch to the width of their "
        "context.")

    h2("Two's complement")
    p("Nearly all hardware represents signed integers in **two's "
      "complement**. An N-bit pattern represents the value in which the "
      "most significant bit has __negative__ weight:")
    eq(["value = -b[N-1] x 2^(N-1) + sum(i=0..N-2) b[i] x 2^i",
        "range  = -2^(N-1)  ...  2^(N-1) - 1          (8 bits: -128 ... 127)",
        "-x     = ~x + 1                              (invert, add one)"],
       "Two's-complement definitions.")
    p("Its great virtue is that **addition and subtraction are the same "
      "circuit for signed and unsigned numbers** - only the interpretation "
      "of the result and the overflow rule differ. That is why an ALU "
      "needs one adder, not two. Its cost is asymmetry: there is one more "
      "negative number than positive, so negating the most negative value "
      "overflows back to itself.")
    code(V("""
module tb;
  logic signed [7:0] a, b, s;
  initial begin
    a = 8'sd100;  b = 8'sd27;  s = a + b;
    $display("100 + 27  = %0d  (bits %b)", s, s);
    a = 8'sd100;  b = 8'sd28;  s = a + b;
    $display("100 + 28  = %0d  (bits %b)  <- overflow", s, s);
    a = -8'sd1;
    $display("-1        = %b = 0x%h", a, a);
    a = -8'sd128;  s = -a;
    $display("-(-128)   = %0d  (no +128 in 8 bits)", s);
  end
endmodule
"""))
    out(["100 + 27  = 127  (bits 01111111)",
         "100 + 28  = -128  (bits 10000000)  <- overflow",
         "-1        = 11111111 = 0xff",
         "-(-128)   = -128  (no +128 in 8 bits)"],
        "Output (Icarus Verilog 12). Signed overflow wraps silently - "
        "hardware never raises an exception.")
    tbl(["Operation", "Rule", "Hardware"],
        [["Zero extension (unsigned)", "Pad with 0s on the left",
          "Wires tied to 0"],
         ["**Sign extension** (signed)", "Replicate the MSB: "
          "`{{8{x[7]}}, x}`", "Wires fanned out from the MSB - free"],
         ["Unsigned overflow", "Carry out of the MSB", "`cout` of the adder"],
         ["Signed overflow", "Operands have equal signs and the result's "
          "sign differs", "`cout XOR carry-into-MSB`"],
         ["Saturation", "Clamp to max/min on overflow", "Overflow detect + "
          "mux (Ch 8)"],
         ["Truncation", "Drop MSBs (wrap) or LSBs (divide by 2^k)",
          "Wires simply not connected"]],
        widths=[25, 43, 32], bold_first=True)
    box("intuit", "Fixed point is just integers with an agreed binary point",
        "An 8-bit signed value interpreted as Q1.7 (one integer bit including "
        "the sign, seven fraction bits) represents -1.0 ... +0.992 in steps of "
        "1/128. The adder does not know or care; only the designer tracks "
        "where the binary point is. Quantized ML accelerators (Chapter 29) "
        "are built entirely on this idea, and Chapter 8 treats fixed-point "
        "arithmetic, rounding and saturation in depth.")

    h2("Boolean algebra and the gates it maps to")
    p("Combinational logic is Boolean algebra. You rarely minimize by hand - "
      "synthesis does that far better - but you must be able to read an "
      "expression and see its cost, and recognise identities that make "
      "code clearer.")
    tbl(["Law", "AND form", "OR form"],
        [["Identity", "a & 1 = a", "a | 0 = a"],
         ["Null", "a & 0 = 0", "a | 1 = 1"],
         ["Idempotent", "a & a = a", "a | a = a"],
         ["Complement", "a & ~a = 0", "a | ~a = 1"],
         ["Distributive", "a & (b | c) = a&b | a&c", "a | (b & c) = (a|b) & "
          "(a|c)"],
         ["Absorption", "a & (a | b) = a", "a | (a & b) = a"],
         ["**De Morgan**", "~(a & b) = ~a | ~b", "~(a | b) = ~a & ~b"],
         ["Consensus", "a&b | ~a&c | b&c = a&b | ~a&c", "(dual)"]],
        widths=[20, 40, 40], bold_first=True)
    p("In CMOS the natural gates are **inverting**: NAND and NOR need four "
      "transistors, while AND and OR are a NAND/NOR plus an inverter. "
      "Standard-cell libraries also offer complex gates such as AOI "
      "(AND-OR-INVERT) and OAI, XOR/XNOR, multiplexers and full adders. "
      "Synthesis maps your Boolean expressions onto whichever cells give "
      "the best timing and area, so write for clarity, not for a "
      "particular gate.")
    tbl(["Gate", "Verilog", "Relative cost (NAND2 = 1)", "Notes"],
        [["INV", "`~a`", "~0.7", "Also used as a buffer stage"],
         ["NAND2 / NOR2", "`~(a & b)` / `~(a | b)`", "1 / ~1", "The "
          "universal gates"],
         ["AND2 / OR2", "`a & b` / `a | b`", "~1.3", "NAND/NOR + INV"],
         ["XOR2", "`a ^ b`", "~2-2.5", "Adders, parity, CRC, comparators"],
         ["MUX2", "`s ? b : a`", "~2-2.5", "Every if/else and ?: becomes muxes"],
         ["Full adder", "`{co,s} = a+b+ci`", "~5-7", "Building block of "
          "arithmetic"],
         ["DFF (no reset)", "`always_ff`", "~4-6", "Flops dominate many "
          "designs' area"],
         ["DFF with async reset", "`always_ff ... or negedge rst_n`", "~5-7",
          "Reset costs area (Ch 12)"]],
        widths=[20, 30, 20, 30], bold_first=True,
        caption="Table 2.1 - Typical relative cell areas. Exact numbers "
                "depend on the library, but the ratios are a useful mental "
                "model.")

    h2("Multiplexers, decoders and encoders")
    p("Three building blocks appear inside almost every RTL block. A "
      "**multiplexer** selects one of N inputs; a **decoder** turns an "
      "n-bit index into a one-hot vector of 2^n bits; an **encoder** does "
      "the reverse, and a **priority encoder** resolves several active "
      "requests by picking the highest (or lowest) index. Here they are in "
      "SystemVerilog, with a testbench:")
    code(V("""
module mux4 (input logic [1:0] sel, input logic [3:0] d, output logic y);
  assign y = d[sel];                            // 4:1 mux
endmodule
module dec2to4 (input logic [1:0] a, input logic en, output logic [3:0] y);
  assign y = en ? (4'b0001 << a) : 4'b0000;     // one-hot decoder
endmodule
module prio_enc (input logic [3:0] req, output logic [1:0] idx, output logic vld);
  always_comb begin
    vld = |req;
    idx = 2'd0;
    for (int i = 0; i < 4; i++)                 // last match wins -> highest index
      if (req[i]) idx = 2'(i);
  end
endmodule
"""), "Three combinational building blocks. The priority encoder's loop "
      "unrolls into a chain of muxes: later iterations override earlier "
      "ones.")
    code(V("""
module tb;
  logic [1:0] sel, idx; logic [3:0] d, dec, req; logic y, vld;
  mux4     u_m (.sel(sel), .d(d), .y(y));
  dec2to4  u_d (.a(sel), .en(1'b1), .y(dec));
  prio_enc u_p (.req(req), .idx(idx), .vld(vld));
  initial begin
    d = 4'b1010;
    for (int i = 0; i < 4; i++) begin
      sel = i[1:0]; req = 4'(i * 5);
      #1 $display("sel=%0d y=%b dec=%b | req=%b idx=%0d vld=%b",
                  sel, y, dec, req, idx, vld);
    end
  end
endmodule
"""))
    out(["sel=0 y=0 dec=0001 | req=0000 idx=0 vld=0",
         "sel=1 y=1 dec=0010 | req=0101 idx=2 vld=1",
         "sel=2 y=0 dec=0100 | req=1010 idx=3 vld=1",
         "sel=3 y=1 dec=1000 | req=1111 idx=3 vld=1"])
    diagram([
        "   d[0] --|0 \\                      req[3] ---------------+",
        "   d[1] --|1  |                     req[2] -------+       |",
        "   d[2] --|2  |-- y                 req[1] --+    |       |",
        "   d[3] --|3 /                               v    v       v",
        "           |                         0 ->[mux]->[mux]->[mux]-> idx",
        "          sel[1:0]                     1^    2^     3^",
        "                                 (each mux selects its constant",
        "   4:1 mux: log2(4)=2 levels      when its req bit is 1 -> the",
        "   of MUX2 cells                  highest index wins)",
    ], "Figure 2.1 - Hardware inferred for mux4 (left) and prio_enc "
       "(right). The priority chain is a serial structure: its delay grows "
       "linearly with the number of requesters unless synthesis restructures "
       "it into a tree.")
    box("key", "Priority costs delay",
        "An `if / else if / else if` chain describes priority, and priority "
        "is inherently serial logic. When the conditions are mutually "
        "exclusive (for example, one-hot selects), say so - with a `case` on "
        "a one-hot vector, `unique case`, or an AND-OR mux - and synthesis "
        "can build a parallel structure. Chapter 5 develops this.")

    h2("Karnaugh maps, briefly")
    p("A Karnaugh map arranges a truth table in Gray-code order so that "
      "adjacent cells differ in one variable; circling groups of 1s of size "
      "1, 2, 4, 8... yields a minimal sum of products. Below is the 3-input "
      "**majority** function (the carry-out of a full adder):")
    diagram([
        "               bc = 00   01   11   10",
        "       a = 0  |    0     0  [ 1 ]  0        groups:",
        "       a = 1  |    0  [ 1 ][ 1 ][ 1 ]         column bc=11   -> b&c",
        "                                              a=1, bc=01,11  -> a&c",
        "                                              a=1, bc=11,10  -> a&b",
        "",
        "       maj(a,b,c) = a&b | a&c | b&c     (= cout of a full adder)",
    ], "Figure 2.2 - K-map for the majority function.")
    p("K-maps stop being practical beyond about five variables, and "
      "synthesis tools use far more powerful algorithms (two-level "
      "minimization, BDDs, AIG rewriting). The value for an RTL designer is "
      "conceptual: they explain **don't-cares** (inputs that cannot occur "
      "let the tool pick 0 or 1 to simplify logic - the reason for "
      "`default: y = 'x` in some coding styles) and **hazards**, below.")

    h2("Latches and flip-flops")
    p("Storage comes in two flavours. A **D latch** is __level-sensitive__: "
      "while its enable is high it is transparent (Q follows D); when the "
      "enable falls it holds. A **D flip-flop** is __edge-triggered__: it "
      "samples D only at the clock edge and holds Q constant for the rest "
      "of the cycle. A flip-flop is internally two latches back to back "
      "(master and slave) on opposite clock phases.")
    code(V("""
module d_latch (input logic en, d, output logic q);
  always_latch if (en) q = d;         // transparent while en=1
endmodule
module d_flop (input logic clk, d, output logic q);
  always_ff @(posedge clk) q <= d;    // samples d only at the rising edge
endmodule
module tb;
  logic clk = 0, d = 0, ql, qf;
  d_latch u_l (.en(clk), .d(d), .q(ql));
  d_flop  u_f (.clk(clk), .d(d), .q(qf));
  always #5 clk = ~clk;
  initial begin
    $display(" t  clk d | latch flop");
    #2  d = 1;  #1 $display("%2t   %b  %b |   %b    %b", $time, clk, d, ql, qf);
    #4          $display("%2t   %b  %b |   %b    %b", $time, clk, d, ql, qf);
    #1  d = 0;  #1 $display("%2t   %b  %b |   %b    %b", $time, clk, d, ql, qf);
    #1  d = 1;  #1 $display("%2t   %b  %b |   %b    %b", $time, clk, d, ql, qf);
    #6          $display("%2t   %b  %b |   %b    %b", $time, clk, d, ql, qf);
    $finish;
  end
endmodule
"""))
    out([" t  clk d | latch flop",
         " 3   0  1 |   x    x",
         " 7   1  1 |   1    1",
         " 9   1  0 |   0    1",
         "11   0  1 |   0    1",
         "17   1  1 |   1    1"],
        "At t=9 the clock is still high: the latch follows d down to 0, the "
        "flop keeps the value captured at t=5. At t=11 the clock is low and "
        "both hold.")
    tbl(["Property", "Latch", "Flip-flop"],
        [["Sensitivity", "Level (transparent while enabled)",
          "Edge (samples at one instant)"],
         ["Area", "Smaller (~half a flop)", "Larger"],
         ["Timing analysis", "Time borrowing across the transparent phase: "
          "powerful but complex", "Simple: one launch, one capture per cycle"],
         ["Glitch sensitivity", "A glitch on D or enable passes through",
          "Only the value at the edge matters"],
         ["Use in ASIC RTL", "Clock-gating cells, some high-speed custom "
          "designs, latch-based register files", "**The default for "
          "everything**"],
         ["How it appears by accident", "Incomplete assignment in "
          "combinational `always` (Ch 5)", "-"]],
        widths=[22, 39, 39], bold_first=True)
    box("warn", "Unintended latches",
        "If a combinational block does not assign an output on every path "
        "(an `if` without `else`, a `case` without `default`), the output "
        "must remember its old value - and synthesis builds a latch. It is "
        "one of the most common RTL bugs. Using `always_comb` makes tools "
        "warn about it; Chapter 5 shows how to avoid it by construction.")

    h2("Setup, hold and clock-to-Q")
    p("A flip-flop only works if D is stable in a window around the clock "
      "edge. Three numbers from the cell library describe it:")
    bul([
        "**Setup time** t_{su}: D must be stable this long __before__ the "
        "edge.",
        "**Hold time** t_{h}: D must stay stable this long __after__ the "
        "edge.",
        "**Clock-to-Q** t_{cq}: after the edge, Q changes this much later.",
    ])
    diagram([
        "             setup  hold",
        "            |<-->|<->|",
        "  clk  _____________/~~~~~~~~~~~~~~~~\\_____________/~~~~~~~",
        "  D    xxxxxxx|=====STABLE=====|xxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "  Q    ===========old===========|<tcq>|=========new========",
        "                                ^",
        "                                active edge",
    ], "Figure 2.3 - The sampling window. A change of D inside the "
       "setup/hold window can make the flop metastable.")

    h2("The critical path and maximum frequency")
    p("Consider two flops with combinational logic between them, both "
      "clocked by the same clock. Data launched at one edge must arrive at "
      "the capturing flop a setup time before the __next__ edge; that is "
      "the **setup** (max-delay) constraint. Data launched at an edge must "
      "__not__ arrive so quickly that it corrupts the value the capture flop "
      "is sampling at that same edge; that is the **hold** (min-delay) "
      "constraint.")
    diagram([
        "      launch                                   capture",
        "     +-----+      +------------------+       +-----+",
        "  -->| D Q |----->|  combinational   |------>| D Q |-->",
        "     |     |      |  logic (t_logic) |       |     |",
        "     +-^---+      +------------------+       +-^---+",
        "       |                                       |",
        "  clk -+---------------(clock tree)------------+  (skew = arrival difference)",
    ], "Figure 2.4 - A register-to-register timing path.")
    eq(["Setup:   T_clk >= t_cq + t_logic(max) + t_su - t_skew",
        "Hold:    t_cq + t_logic(min) >= t_h + t_skew",
        "f_max  = 1 / (t_cq + t_logic(max) + t_su - t_skew)",
        "",
        "Example: t_cq = 80 ps, t_logic = 600 ps, t_su = 50 ps, skew = 0",
        "         T_min = 730 ps  ->  f_max = 1 / 730 ps = 1.37 GHz"],
       "The two fundamental timing equations (t_skew = capture clock arrival "
       "minus launch clock arrival; clock uncertainty is subtracted from the "
       "budget in the same way).")
    p("The **critical path** is the register-to-register path with the "
      "least slack; it sets f_{max}. Notice two deep facts:")
    bul([
        "**Setup depends on the clock period; hold does not.** A setup "
        "violation can be fixed by slowing the clock (or by pipelining, "
        "Chapter 10). A hold violation cannot - the chip fails at any "
        "frequency - so back-end tools fix hold by inserting delay buffers.",
        "**Positive skew helps setup and hurts hold** by the same amount. "
        "Clock-tree synthesis balances skew; 'useful skew' deliberately "
        "exploits it.",
        "**RTL controls t_logic.** The number of logic levels you write "
        "between flops is the main lever the RTL designer has on frequency. "
        "A rule of thumb in a modern process at 1 GHz is roughly 20-30 "
        "gate levels per cycle; Chapter 18 makes this quantitative.",
    ])
    box("expert", "Interview favourite: 'Can a design have negative hold slack "
        "and still work if you slow the clock?'",
        "No. The hold check compares the earliest data arrival with the "
        "same clock edge's capture window, so the clock period does not "
        "appear in the inequality. Slowing the clock fixes setup, never hold. "
        "(Hold issues on real silicon are fixed by ECOs that add delay, or "
        "sometimes worked around by raising voltage, which changes the cell "
        "delays - not by frequency.)")

    h2("Metastability: a preview")
    p("If D changes inside the setup/hold window, the flop's internal "
      "node can hang between 0 and 1 for an unbounded time before resolving "
      "randomly - **metastability**. Inside one synchronous clock domain, "
      "static timing analysis guarantees this never happens. But a signal "
      "arriving from another clock domain, or an asynchronous input such as "
      "a button or a reset release, has no fixed timing relationship to "
      "the capture clock and __will__ eventually violate the window.")
    eq(["MTBF = exp(t_r / tau) / (T_0 x f_clk x f_data)",
        "",
        "t_r  : time allowed for resolution (about one clock period per sync stage)",
        "tau, T_0 : flop technology constants"],
       "Mean time between synchronizer failures. It grows exponentially with "
       "resolution time - which is why a second flop stage helps so much.")
    p("The standard cure is a **two-flop synchronizer**: the first flop may "
      "go metastable, but it has a whole clock period to resolve before the "
      "second flop samples it. Multi-bit values need more care (Gray codes, "
      "handshakes, asynchronous FIFOs). Chapter 11 is devoted to clock-domain "
      "crossing; Chapter 12 to the reset version of the same problem.")

    h2("Fan-out, glitches and hazards")
    h3("Fan-out")
    p("**Fan-out** is the number of gate inputs a signal drives. Every "
      "input adds capacitance, and delay grows with load. A single "
      "register driving 2,000 flops (a global enable, a reset, a mode bit) "
      "cannot switch quickly; synthesis and physical design build a "
      "**buffer tree** for it, adding delay and area. RTL designers help by "
      "keeping high-fan-out controls registered close to their loads and, "
      "for timing-critical paths, **replicating** the driving register.")
    h3("Glitches and hazards")
    p("Different paths through combinational logic have different delays, "
      "so an output can pulse briefly to a wrong value while inputs "
      "change: a **glitch**. A **static hazard** is a glitch on an output "
      "that should have stayed constant. The classic example is a 2:1 mux "
      "built from gates, `y = a&s | b&~s`, with `a = b = 1` while `s` "
      "switches: for an instant both AND terms can be 0, and y dips to 0.")
    diagram([
        "  a=1 ---[AND]---+                 s     ~~~~~~~\\_____________",
        "  s   ---/       |                 ~s    _______/~~~~~~~~~~~~~   (late: inverter delay)",
        "                 +--[OR]--- y      a&s   ~~~~~~~\\_____________",
        "  b=1 ---[AND]---+                 b&~s  ________/~~~~~~~~~~~~",
        "  ~s  ---/                         y     ~~~~~~~\\_/~~~~~~~~~~~~   <- glitch",
        "",
        "  Fix (if the output really must be glitch-free): add the consensus term a&b.",
    ], "Figure 2.5 - A static-1 hazard in a gate-level multiplexer.")
    box("key", "Why synchronous design tolerates glitches - and where it does "
        "not",
        "In a synchronous design glitches are harmless on data paths: the "
        "capturing flop only looks at its input at the clock edge, after "
        "everything has settled (that is what the setup check guarantees). "
        "Glitches are **fatal** on anything used as a clock, an asynchronous "
        "reset, or a signal crossing into another clock domain, and they "
        "**waste dynamic power** everywhere. Hence the golden rules: never "
        "generate clocks or resets from combinational logic, and always "
        "register a signal before it crosses a clock domain.")

    h2("Summary")
    bul([
        "Size every literal; unsized literals are 32-bit and silently widen "
        "expressions.",
        "Two's complement makes signed and unsigned add/subtract the same "
        "hardware; sign-extend by replicating the MSB; overflow wraps "
        "silently.",
        "Muxes, decoders and priority encoders are the vocabulary of RTL; "
        "priority logic is serial and slower than parallel selection.",
        "Latches are level-sensitive and appear by accident from incomplete "
        "assignments; flip-flops are the default storage element.",
        "Setup: T >= t_cq + t_logic,max + t_su - skew. Hold: t_cq + "
        "t_logic,min >= t_h + skew. Hold does not depend on frequency.",
        "Metastability is unavoidable across asynchronous boundaries and "
        "is managed with synchronizers (Chapter 11). Glitches are harmless "
        "on synchronous data paths but fatal on clocks and resets.",
    ])
    h2("Exercises")
    bul([
        "Write -37 as an 8-bit two's-complement number in binary and hex. "
        "Sign-extend it to 12 bits. What unsigned value does the 8-bit "
        "pattern represent?",
        "Show that 8-bit signed overflow on addition can be detected as "
        "`(a[7] == b[7]) && (s[7] != a[7])`, and derive the equivalent "
        "expression using the carry into and out of the MSB.",
        "A path has t_cq = 90 ps, 14 gates of 45 ps each, t_su = 40 ps, "
        "clock uncertainty 30 ps and skew +20 ps. What is f_max? Which "
        "numbers would change if the same path had a hold problem?",
        "Modify `prio_enc` so the __lowest__ index wins. How does the "
        "inferred mux chain change?",
        "Draw the K-map for the 3-input XOR function. Why can no two 1s be "
        "grouped, and what does that tell you about the cost of parity "
        "trees?",
        "Explain, with a timing diagram, why a glitch on the enable of a "
        "latch-based clock gate can corrupt a design, whereas the same "
        "glitch on the D input of a flop does not.",
    ], ordered=True)


# =============================================================================
#  Chapter 3 - Verilog and SystemVerilog for design
# =============================================================================
def _ch3():
    chapter("Verilog and SystemVerilog for Design")
    p("Verilog was created in 1984 as a simulation language; synthesis came "
      "later and adopted a __subset__ of it. SystemVerilog (IEEE 1800, which "
      "absorbed Verilog in 2009) added a large verification language and a "
      "smaller but very valuable set of design features: `logic`, "
      "`always_ff`/`always_comb`, `typedef`, `enum`, `struct`, packages and "
      "interfaces. Modern RTL is written in SystemVerilog's design subset, "
      "and that is what this chapter teaches.")
    p("The mindset matters more than the syntax. You are not writing a "
      "program that executes line by line; you are writing a **description "
      "of hardware that exists all at once**. Every statement below should "
      "make you picture wires, gates and flops.")

    h2("Modules, ports and hierarchy")
    p("The **module** is the unit of hardware: a box with ports. A design is "
      "a tree of module **instances**; the top of the tree is the chip (or "
      "the testbench). Below, a full adder is instantiated eight times by a "
      "`generate` loop to build a parameterized ripple-carry adder:")
    code(V("""
module full_adder (input  logic a, b, cin,
                   output logic s, cout);
  assign s    = a ^ b ^ cin;
  assign cout = (a & b) | (cin & (a ^ b));
endmodule

module ripple_add #(parameter int W = 4) (
  input  logic [W-1:0] a, b,
  input  logic         cin,
  output logic [W-1:0] sum,
  output logic         cout
);
  logic [W:0] c;                     // carry chain, c[0] = cin
  assign c[0] = cin;
  for (genvar i = 0; i < W; i++) begin : g_bit
    full_adder u_fa (.a(a[i]), .b(b[i]), .cin(c[i]), .s(sum[i]), .cout(c[i+1]));
  end
  assign cout = c[W];
endmodule
"""), "ANSI-style port declarations, a parameter, and named port "
      "connections. Each loop iteration creates an instance with the "
      "hierarchical name `g_bit[i].u_fa`.")
    code(V("""
module tb;
  logic [7:0] a, b, s; logic co;
  ripple_add #(.W(8)) dut (.a(a), .b(b), .cin(1'b0), .sum(s), .cout(co));
  initial begin
    a = 8'd200; b = 8'd100;
    #1 $display("%0d + %0d = %0d carry=%b  {cout,sum}=%0d", a, b, s, co, {co, s});
    a = 8'd17;  b = 8'd25;
    #1 $display("%0d + %0d = %0d carry=%b  {cout,sum}=%0d", a, b, s, co, {co, s});
  end
endmodule
"""))
    out(["200 + 100 = 44 carry=1  {cout,sum}=300",
         "17 + 25 = 42 carry=0  {cout,sum}=42"])
    tbl(["Connection style", "Example", "Verdict"],
        [["**Named** (by port name)", "`.a(x), .b(y)`",
          "**Use this.** Order-independent, self-documenting, survives port "
          "reordering"],
         ["Positional (by order)", "`full_adder u (x, y, ci, s, co);`",
          "Avoid except for tiny primitives: a reordered port list silently "
          "miswires"],
         ["Implicit named", "`.clk, .rst_n` (same-name signal)",
          "Convenient; still checks that the names exist"],
         ["Wildcard", "`.*`", "Terse but hides connectivity; avoid in "
          "reviewed RTL"]],
        widths=[22, 34, 44], bold_first=True)
    box("warn", "Implicit nets: one typo, one silently wrong chip",
        "An undeclared identifier in a port connection is silently declared "
        "as a **1-bit wire**. Below, `data_inn` is a typo: the 8-bit port "
        "gets a single floating bit and the design still compiles. Put the "
        "compiler directive shown in the second listing at the top of every "
        "RTL file to turn this into an error.")
    code(V("""
module inv8 (input logic [7:0] a, output logic [7:0] y);
  assign y = ~a;
endmodule
module top (input logic [7:0] data_in, output logic [7:0] data_out);
  inv8 u_inv (.a(data_inn), .y(data_out));   // typo -> implicit 1-bit wire!
endmodule
"""))
    out(["c3_impl.sv:5: warning: implicit definition of wire 'data_inn'.",
         "c3_impl.sv:5: warning: Port 1 (a) of inv8 expects 8 bits, got 1.",
         "c3_impl.sv:5:        : Padding 7 high bits of the port."],
        "iverilog -Wall: only warnings - the build succeeds. Many flows "
        "never show warnings to anyone.")
    code(["`default_nettype none      // first line of every RTL file"])
    out(["c3_impl2.sv:6: error: Unable to bind wire/reg/memory `data_inn' in `top'",
         "c3_impl2.sv:6: error: Failed to elaborate port expression.",
         "2 error(s) during elaboration."],
        "With the directive the typo is a hard error. (If you must link "
        "legacy code that relies on implicit nets, re-enable them at the end "
        "of the file with the same directive and the value `wire`.)")

    h2("Data types: wire, reg, logic, and four-state values")
    p("Verilog had two kinds of signal: **nets** (`wire`), which are driven "
      "continuously by `assign` statements or instance outputs, and "
      "**variables** (`reg`), which hold the last value assigned to them in "
      "procedural code. The name `reg` misled generations of engineers: a "
      "`reg` is __not__ necessarily a register - a `reg` assigned in a "
      "combinational block is just a wire. SystemVerilog fixed this with "
      "`logic`, a four-state variable type that can be used in both places.")
    tbl(["Type", "Kind", "States", "Use"],
        [["`logic`", "Variable (or net type, with `wire logic`)", "0 1 x z",
          "**Default for all RTL signals** with a single driver"],
         ["`wire`", "Net", "0 1 x z", "Multiple drivers (tri-state buses), "
          "inout ports; otherwise `logic` is better because multiple "
          "drivers become a compile error"],
         ["`reg`", "Variable", "0 1 x z", "Legacy Verilog; identical to "
          "`logic`"],
         ["`bit`", "Variable", "0 1", "Testbenches, loop counters. Hides X "
          "in RTL - avoid for hardware signals"],
         ["`int` / `integer`", "Variable, 32-bit signed", "2-state / "
          "4-state", "Loop indices, parameters"],
         ["`byte`, `shortint`, `longint`", "8/16/64-bit signed, 2-state",
          "0 1", "Testbench modelling"]],
        widths=[20, 27, 14, 39])
    p("Four-state logic is how simulation represents uncertainty. **x** "
      "means 'unknown - could be 0 or 1' (an uninitialized flop, a "
      "conflict between drivers); **z** means 'high impedance - nobody is "
      "driving'. Synthesis maps real hardware only to 0 and 1; x and z are "
      "simulation concepts (except z for real tri-state pads).")
    code(V("""
module tb;
  logic [3:0] v;                   // 4-state: 0 1 x z
  bit   [3:0] b2;                  // 2-state: x/z become 0
  wire        bus;                 // net with two tri-state drivers
  logic       en0, en1, d0, d1;
  assign bus = en0 ? d0 : 1'bz;
  assign bus = en1 ? d1 : 1'bz;
  initial begin
    $display("uninit v=%b", v);
    v = 4'b10xz;  b2 = v;
    $display("v=%b  b2=%b  v==4'b10xz:%b  v===4'b10xz:%b", v, b2, v == 4'b10xz, v === 4'b10xz);
    $display("v+4'd1=%b  &4'b0x00=%b  |4'b1x00=%b", v + 4'd1, &4'b0x00, |4'b1x00);
    en0 = 0; en1 = 0; d0 = 0; d1 = 1; #1 $display("no driver : bus=%b", bus);
    en0 = 1;                           #1 $display("one driver: bus=%b", bus);
    en1 = 1;                           #1 $display("contention: bus=%b", bus);
  end
endmodule
"""))
    out(["uninit v=xxxx",
         "v=10xz  b2=1000  v==4'b10xz:x  v===4'b10xz:1",
         "v+4'd1=xxxx  &4'b0x00=0  |4'b1x00=1",
         "no driver : bus=z",
         "one driver: bus=0",
         "contention: bus=x"],
        "Note: `==` returns x when either side has x/z; the case-equality "
        "operator `===` compares x and z literally (testbench only - it "
        "is not synthesizable). Arithmetic with any x bit gives all x; "
        "logic ops are smarter: 0 AND x = 0, 1 OR x = 1.")

    h2("Vectors, part-selects and arrays")
    p("A vector is declared with a range, conventionally `[MSB:LSB]` with "
      "LSB = 0: `logic [31:0] addr`. Slices take a constant range: "
      "`addr[15:8]`. When the __position__ must be variable, use the "
      "**indexed part-select** `base +: width` (ascending from base) or "
      "`base -: width` (descending); the width must be constant, the base "
      "may be a variable - which infers a shifter/mux.")
    code(V("""
module tb;
  logic        [7:0] v = 8'b1011_0110;
  logic signed [7:0] s = -8'sd96;          // 8'b1010_0000
  logic       [31:0] word = 32'hDEAD_BEEF;
  int                k = 2;
  initial begin
    $display("v[7:4]=%b  v[3:0]=%b  v[0]=%b", v[7:4], v[3:0], v[0]);
    $display("word[8*k +: 8] = %h   word[31 -: 8] = %h", word[8*k +: 8], word[31 -: 8]);
    $display("&v=%b |v=%b ^v=%b ~&v=%b", &v, |v, ^v, ~&v);
    $display("{v[3:0],v[7:4]} = %b", {v[3:0], v[7:4]});
    $display("{4{2'b10}}      = %b", {4{2'b10}});
    $display("v >> 2  = %b   v >>> 2 = %b  (unsigned: both logical)", v >> 2, v >>> 2);
    $display("s >> 2  = %b   s >>> 2 = %b (%0d)", s >> 2, s >>> 2, s >>> 2);
    $display("!v = %b   ~v = %b", !v, ~v);
  end
endmodule
"""), "Part-selects, reduction, concatenation, replication and shifts.")
    out(["v[7:4]=1011  v[3:0]=0110  v[0]=0",
         "word[8*k +: 8] = ad   word[31 -: 8] = de",
         "&v=0 |v=1 ^v=1 ~&v=1",
         "{v[3:0],v[7:4]} = 01101011",
         "{4{2'b10}}      = 10101010",
         "v >> 2  = 00101101   v >>> 2 = 00101101  (unsigned: both logical)",
         "s >> 2  = 00101000   s >>> 2 = 11101000 (-24)",
         "!v = 0   ~v = 01001001"])
    p("**Arrays** add dimensions. SystemVerilog distinguishes **packed** "
      "dimensions (declared before the name; the bits are contiguous and "
      "the whole thing is a vector you can do arithmetic on) from "
      "**unpacked** dimensions (after the name; separate elements, like a "
      "memory).")
    tbl(["Declaration", "Meaning", "Typical hardware"],
        [["`logic [3:0][7:0] w;`", "Packed 2-D: a 32-bit vector viewed as "
          "4 bytes; `w[2]` is a byte, `w` is 32 bits", "A bus with "
          "sub-fields, byte lanes"],
         ["`logic [7:0] mem [0:255];`", "Unpacked array of 256 bytes; one "
          "element accessed at a time", "Register file or SRAM (Ch 9)"],
         ["`logic [7:0] m2 [4][4];`", "Unpacked 2-D, C-style sizes",
          "Coefficient tables, small matrices"],
         ["`logic [31:0] q [$];`", "Queue (dynamic)", "**Testbench only**"],
         ["`int aa [string];`", "Associative array", "**Testbench only**"]],
        widths=[30, 45, 25])

    h2("Operators")
    tbl(["Group", "Operators", "Result width / notes"],
        [["Bitwise", "`~ & | ^ ~^`", "Width of the widest operand; one gate "
          "per bit"],
         ["Reduction", "`&v |v ^v ~&v ~|v ~^v`", "1 bit; a tree of gates. "
          "`^v` is parity; `|v` is 'any bit set'"],
         ["Logical", "`! && ||`", "1 bit; operands are tested as 'non-zero'"],
         ["Relational / equality", "`< <= > >= == !=`", "1 bit; x if any "
          "operand bit is x/z. `=== !==` are testbench-only"],
         ["Arithmetic", "`+ - * / % **`", "`+ -` are cheap, `*` is large; "
          "`/ %` only by constants or powers of two in RTL"],
         ["Shift", "`<< >>` logical, `<<< >>>` arithmetic",
          "`>>>` fills with the sign bit __only if the operand is signed__"],
         ["Concatenation", "`{a, b, 2'b01}`", "Sum of widths; operands must "
          "be sized"],
         ["Replication", "`{4{x}}`, `{{8{s[7]}}, s}`", "Sign extension idiom"],
         ["Conditional", "`c ? a : b`", "A multiplexer"],
         ["Streaming", "`{<<{v}}`", "Bit reversal; supported by most modern "
          "synthesis tools"]],
        widths=[20, 34, 46], bold_first=True)
    box("warn", "The >>> operator does nothing special on unsigned values",
        "As the output above shows, `v >>> 2` on an unsigned `v` is a logical "
        "shift. Arithmetic right shift requires a **signed** operand: declare "
        "the signal `logic signed`, or cast with `$signed(v) >>> 2`. Also: "
        "`!v` is logical NOT (is v zero?), `~v` is bitwise NOT - confusing "
        "them in an `if` is a classic bug for multi-bit signals.")

    h2("Expression sizing and extension rules")
    p("This is where most subtle Verilog arithmetic bugs live. The rules "
      "(IEEE 1800 clause 11.6-11.8) are:")
    bul([
        "**Context-determined width.** For most operators the expression is "
        "evaluated at the width of the __largest operand, including the "
        "left-hand side of the assignment__. Operands are extended to that "
        "width __before__ the operation.",
        "**Self-determined operands** are evaluated at their own width, "
        "regardless of context: concatenation operands, the shift amount, "
        "the operand of a reduction, the condition of `?:`.",
        "**Signedness.** An expression is signed only if __all__ its "
        "operands are signed. One unsigned operand makes the whole "
        "expression unsigned, and signed operands are then zero-extended, "
        "not sign-extended.",
        "Extension then follows the expression's signedness: sign extension "
        "for signed, zero extension for unsigned. Truncation on assignment "
        "drops the MSBs.",
    ])
    code(V("""
module tb;
  logic        [7:0] a = 8'd200, b = 8'd100;
  logic        [7:0] sum8;
  logic        [8:0] sum9;
  logic       [15:0] prod;
  logic signed [7:0] sa = -8'sd4;
  logic        [3:0] u  = 4'd3;
  logic signed [15:0] r1, r2;
  initial begin
    sum8 = a + b;                    // context is 8 bits: carry lost
    sum9 = a + b;                    // context is 9 bits: operands extended first
    $display("sum8=%0d sum9=%0d", sum8, sum9);
    $display("(a+b)>>1 = %0d   {1'b0,a}+b >> 1 = %0d", (a + b) >> 1, ({1'b0, a} + b) >> 1);
    prod = a * b;  $display("prod=%0d", prod);
    r1 = sa * u;                     // mixed: sa treated as UNSIGNED 8-bit 252
    r2 = sa * $signed({1'b0, u});    // both signed: -4 * 3
    $display("r1=%0d  r2=%0d", r1, r2);
    $display("-4 < 3u ? %b    -4 < 3 ? %b", sa < u, sa < $signed({1'b0, u}));
    $display("4'hF + 1 in 4 bits = %0d, as literal expr = %0d", 4'(4'hF + 1), 4'hF + 1);
  end
endmodule
"""), "A gallery of sizing and signedness pitfalls.")
    out(["sum8=44 sum9=300",
         "(a+b)>>1 = 22   {1'b0,a}+b >> 1 = 150",
         "prod=20000",
         "r1=756  r2=-12",
         "-4 < 3u ? 0    -4 < 3 ? 1",
         "4'hF + 1 in 4 bits = 0, as literal expr = 16"])
    p("Read the output line by line - each is a real bug pattern:")
    bul([
        "`sum8`: the carry is lost because the context is 8 bits. `sum9` "
        "works because the 9-bit LHS widens the operands __before__ the add.",
        "`(a+b)>>1` inside `$display` has no LHS, so the context is 8 bits "
        "and the average of 200 and 100 comes out as 22. The fix makes one "
        "operand 9 bits wide. **Averages, midpoints and address arithmetic "
        "hit this constantly.**",
        "`r1`: multiplying a signed by an unsigned value makes the whole "
        "expression unsigned, so -4 is treated as 252 and zero-extended. "
        "The fix: make every operand signed. Note `$signed(u)` alone would "
        "reinterpret 4'd3 correctly, but `$signed(4'd12)` would become -4 - "
        "hence the `{1'b0, u}` idiom that adds an explicit zero sign bit.",
        "`-4 < 3u` is __false__ for the same reason - a comparator bug that "
        "passes most tests.",
        "`4'hF + 1` is 16, not 0: the unsized `1` is 32 bits, so the "
        "expression is 32 bits wide. A size cast `4'(...)` forces 4-bit "
        "wrap-around.",
    ])
    box("tip", "Rules that prevent sizing bugs",
        "(1) Size every literal. (2) Make result widths explicit: an N-bit + "
        "N-bit add needs N+1 bits; N x M needs N+M bits. (3) Never mix signed "
        "and unsigned operands in one expression - convert explicitly. (4) "
        "Use lint (Verilator `-Wall`, Spyglass, Ascent): width-mismatch "
        "warnings are real bugs more often than not (Chapter 25).")

    h2("Parameters, localparams and generate")
    p("**Parameters** make modules reusable: widths, depths and feature "
      "switches are set per instance with `#(.W(8))`. A **localparam** is "
      "a constant derived inside the module that callers cannot override - "
      "for example `localparam int AW = $clog2(DEPTH);`. Both are "
      "**elaboration-time** constants: they are resolved before simulation "
      "or synthesis starts, and cost no hardware.")
    p("**Generate** constructs build structure at elaboration time. A "
      "generate `for` replicates hardware (as in `ripple_add`); a generate "
      "`if` or `case` chooses between alternative structures. Always name "
      "generate blocks (`begin : g_name`) so hierarchical paths are stable "
      "for debug, constraints and assertions.")
    code(V("""
module pipe_reg #(
  parameter int W      = 8,
  parameter bit HAS_RST = 1'b1          // elaboration-time choice
) (
  input  logic         clk, rst_n, en,
  input  logic [W-1:0] d,
  output logic [W-1:0] q
);
  if (HAS_RST) begin : g_rst            // generate-if: only one branch is built
    always_ff @(posedge clk or negedge rst_n)
      if (!rst_n)  q <= '0;
      else if (en) q <= d;
  end else begin : g_norst              // cheaper flops for pure datapath
    always_ff @(posedge clk)
      if (en) q <= d;
  end
endmodule
"""), "A register with an elaboration-time choice of reset. Chapter 12 "
      "discusses when datapath flops may omit reset.")
    code(V("""
module tb;
  logic clk = 0, rst_n = 0, en = 0;
  logic [7:0] d = 8'h00, q1, q2;
  pipe_reg #(.W(8), .HAS_RST(1'b1)) u_r  (.clk(clk), .rst_n(rst_n), .en(en), .d(d), .q(q1));
  pipe_reg #(.W(8), .HAS_RST(1'b0)) u_nr (.clk(clk), .rst_n(rst_n), .en(en), .d(d), .q(q2));
  always #5 clk = ~clk;
  task automatic drive(input logic [7:0] val, input logic e);
    @(negedge clk);  d = val;  en = e;         // change inputs away from the edge
    @(posedge clk);  #1 $display("%3t en=%b d=%h | with_rst q=%h  no_rst q=%h",
                                 $time, en, d, q1, q2);
  endtask
  initial begin
    drive(8'h11, 1'b1);                      // still in reset
    rst_n = 1;
    drive(8'h22, 1'b1);
    drive(8'h33, 1'b0);                      // en=0 -> hold
    drive(8'h44, 1'b1);
    $finish;
  end
endmodule
"""), "A testbench task drives stimulus on the falling edge - a simple "
      "race-avoidance discipline explained in Chapter 4.")
    out([" 16 en=1 d=11 | with_rst q=00  no_rst q=11",
         " 26 en=1 d=22 | with_rst q=22  no_rst q=22",
         " 36 en=0 d=33 | with_rst q=22  no_rst q=22",
         " 46 en=1 d=44 | with_rst q=44  no_rst q=44"])
    diagram([
        "     d[W-1:0] ---->|1\\       +-------+",
        "                   |  |----->| D   Q |----+----> q",
        "              +--->|0/       |       |    |",
        "              |     |en      |  >clk |    |",
        "              |              +---R---+    |    (R: async clear, only in g_rst)",
        "              +---------------------------+",
    ], "Figure 3.1 - What pipe_reg infers: a flop with a recirculating "
       "enable mux (or, after synthesis, an enable flop or a clock gate - "
       "Chapter 19).")

    h2("Functions and tasks")
    p("A **function** returns a value, executes in zero time and cannot "
      "contain timing controls: it describes combinational logic and is "
      "synthesizable. Declare RTL functions `automatic` so each call has its "
      "own variables (and recursion works). A **task** may consume time "
      "(`@`, `#`, `wait`) and is primarily a testbench construct, like "
      "`drive` above; a task without timing controls is synthesizable but "
      "rarely useful in RTL.")

    h2("typedef, enum, struct and packages")
    p("SystemVerilog's user-defined types are the single biggest readability "
      "improvement over Verilog, and they are fully synthesizable. An "
      "`enum` gives names to FSM states and opcodes (and lets waveform "
      "viewers display them); a packed `struct` names the fields of a bus "
      "or a pipeline register while remaining a plain vector; a `package` "
      "shares types, constants and functions across modules.")
    code(V("""
package bus_pkg;
  typedef enum logic [1:0] {OP_READ = 2'b00, OP_WRITE = 2'b01, OP_IDLE = 2'b11} op_e;
  typedef struct packed {
    op_e         op;      // bits [41:40]
    logic [7:0]  id;      // bits [39:32]
    logic [31:0] addr;    // bits [31:0]
  } req_t;                // 42 bits total, usable like a vector
  localparam int unsigned REQ_W = $bits(req_t);
  function automatic logic parity(input logic [31:0] x);
    return ^x;
  endfunction
endpackage
"""), "A package with an enum, a packed struct, a derived constant and a "
      "function. The first struct member occupies the MSBs.")
    code(V("""
module tb;
  import bus_pkg::*;
  req_t        r;
  op_e         op;
  logic [7:0]  mem_unpk [0:3];     // unpacked: 4 separate bytes (a memory)
  logic [3:0][7:0] mem_pk;         // packed: one 32-bit vector made of 4 bytes
  initial begin
    r.op = OP_WRITE;  r.id = 8'h2A;  r.addr = 32'h4000_0010;
    op = r.op;
    $display("REQ_W=%0d  op=%s  raw=%h  parity(addr)=%b", REQ_W, op.name(), r, parity(r.addr));
    r.op = OP_IDLE;  op = r.op;
    $display("op=%s (%b)  r[41:40]=%b", op.name(), op, r[41:40]);
    mem_pk = 32'hA1B2_C3D4;
    foreach (mem_unpk[i]) mem_unpk[i] = mem_pk[i];
    $display("mem_pk[0]=%h mem_pk[3]=%h  mem_unpk[1]=%h  mem_pk=%h", mem_pk[0], mem_pk[3],
             mem_unpk[1], mem_pk);
  end
endmodule
"""))
    out(["REQ_W=42  op=OP_WRITE  raw=12a40000010  parity(addr)=0",
         "op=OP_IDLE (11)  r[41:40]=11",
         "mem_pk[0]=d4 mem_pk[3]=a1  mem_unpk[1]=c3  mem_pk=a1b2c3d4"],
        "The struct is a 42-bit vector with named fields; `name()` prints "
        "an enum's label. Packed element [0] is the least significant byte.")
    box("tip", "Style that scales",
        "Put interface types (request/response structs, opcode enums, "
        "address maps) in a package shared by RTL and testbench; name enums "
        "with an `_e` suffix and structs with `_t`; give enums an explicit "
        "base type (`enum logic [1:0]`) so their width is under your "
        "control. Assign a struct in RTL with an assignment pattern, e.g. "
        "`r = '{op: OP_WRITE, id: 8'h2A, addr: a};` (supported by all "
        "commercial tools; Icarus Verilog 12 lacks it, hence the field-by-"
        "field assignment above).")

    h2("always_comb, always_ff and always_latch")
    p("Verilog had one procedural block, `always`, whose meaning depended "
      "on its sensitivity list and coding style. SystemVerilog adds three "
      "**intent-carrying** variants. They simulate like `always`, but tools "
      "check that the hardware inferred matches the declared intent.")
    tbl(["Block", "Intent", "What the tools check / do"],
        [["`always_comb`", "Combinational logic",
          "Automatic complete sensitivity (including signals read inside "
          "called functions); runs once at time zero; warns if a latch is "
          "inferred; a variable it writes may not be written elsewhere"],
         ["`always_ff @(posedge clk ...)`", "Flip-flops",
          "Must have exactly one event control; warns if the logic is not "
          "a flop; single-writer rule"],
         ["`always_latch`", "Intentional latches", "Complete sensitivity; "
          "documents that the latch is deliberate"],
         ["`always @*`", "Legacy combinational", "Complete sensitivity but "
          "no time-zero run and no function-body sensitivity; prefer "
          "`always_comb`"],
         ["`assign`", "Continuous assignment", "Simple combinational "
          "expressions on one net or variable"]],
        widths=[25, 18, 57], bold_first=True)
    code(V("""
// The canonical two-block style: next-state logic + state register
always_comb begin
  cnt_d = cnt_q;                       // default: hold (prevents latches)
  if (load)     cnt_d = load_val;
  else if (inc) cnt_d = cnt_q + 1'b1;
end

always_ff @(posedge clk or negedge rst_n)
  if (!rst_n) cnt_q <= '0;
  else        cnt_q <= cnt_d;
"""), "Separate the combinational next-value logic (blocking `=`) from the "
      "register (non-blocking `<=`). The `_d`/`_q` naming mirrors the "
      "flop's D and Q pins. Chapter 4 explains why the assignment types "
      "matter.")

    h2("The synthesizable subset")
    p("Synthesis tools accept only constructs that map to hardware. The "
      "boundary is not arbitrary: anything that needs a notion of absolute "
      "time, dynamic memory allocation or file I/O has no gate-level "
      "equivalent.")
    tbl(["Construct", "Synthesizable?", "Notes"],
        [["module, ports, parameters, localparam", "Yes", ""],
         ["assign, always_comb, always_ff, always_latch", "Yes", "The core "
          "of RTL"],
         ["if / case / unique / priority, ?:", "Yes", "Become muxes and "
          "priority logic"],
         ["for loops with constant bounds", "Yes", "Unrolled into parallel "
          "hardware - not iteration in time"],
         ["generate for / if / case", "Yes", "Structural replication"],
         ["functions (automatic), constant functions", "Yes", "No timing "
          "controls"],
         ["typedef, enum, packed struct/union, packages", "Yes", ""],
         ["interfaces and modports", "Yes (most tools)", "Check your "
          "flow; many teams restrict them at top level"],
         ["+ - * and shifts; / % by powers of two", "Yes", "Full `/` and `%` "
          "infer huge combinational dividers - usually a bug"],
         ["initial blocks", "FPGA: often (RAM/flop init). ASIC: **no**",
          "ASIC state must come from reset"],
         ["#delays", "Ignored", "Causes sim/synth mismatch; never in RTL"],
         ["=== , !==, casex/casez with x", "No / partly", "`casez` with "
          "`?` wildcards is fine; avoid `casex`"],
         ["while / repeat / forever with timing, wait, @ inside logic",
          "No", "Testbench only"],
         ["$display, $finish, $random, file I/O", "No (ignored)", "Testbench "
          "only"],
         ["classes, dynamic arrays, queues, associative arrays, strings",
          "No", "Verification language (Part V)"],
         ["real / shortreal", "No", "Model analog or reference behaviour "
          "only"],
         ["force / release, fork / join", "No", "Testbench only"]],
        widths=[42, 22, 36],
        caption="Table 3.1 - The synthesizable subset of SystemVerilog "
                "(IEEE 1800-2017 plus common tool support).")
    box("expert", "A for loop is hardware replication, not time",
        "`for (int i = 0; i < 64; i++) sum += x[i];` inside `always_comb` does "
        "not take 64 cycles; it builds a 64-input adder chain that completes "
        "in one cycle - and may be your critical path. If you want a result "
        "computed over many cycles, you must build the counter and the "
        "accumulator register yourself. Interviewers use this to separate "
        "software thinking from hardware thinking.")

    h2("Summary")
    bul([
        "Use named port connections, name every generate block, and start "
        "every file with the default-nettype-none directive.",
        "`logic` is the default type; `wire` only for multiply-driven nets. "
        "x means unknown, z means undriven; `===` is testbench-only.",
        "Master part-selects (`base +: width`), reduction, concatenation and "
        "replication; `>>>` needs a signed operand.",
        "Expressions take the width of their largest operand including the "
        "LHS, and are unsigned if any operand is unsigned. Size literals; "
        "never mix signedness.",
        "Parameters and generate build configurable structure at "
        "elaboration time; enums, packed structs and packages make RTL "
        "readable and safe.",
        "Use `always_comb` for combinational logic, `always_ff` for flops, "
        "and stay inside the synthesizable subset.",
    ])
    h2("Exercises")
    bul([
        "Rewrite `ripple_add` without `generate`, using a single "
        "`always_comb` with a `for` loop. Is the hardware different?",
        "Predict, then check in a simulator: with `logic [3:0] a = 4'd9, "
        "b = 4'd9; logic [4:0] y;` what are `y = a + b`, `y = {a + b}` and "
        "`y = (a + b) >> 1`? Explain each using the sizing rules.",
        "Write a function `sat_add8` that adds two signed 8-bit values and "
        "saturates to -128/127. Test it on all 65,536 input pairs against a "
        "reference computed with `int`.",
        "Using `+:`, write a module that extracts byte `sel` (0-3) from a "
        "32-bit word. Sketch the hardware it infers.",
        "Define a packed struct for an AXI-Lite write-address beat (addr, "
        "prot) and a package holding it. What does `$bits` return?",
        "Classify each as synthesizable or not, and why: `#5 q <= d;`, "
        "`initial q = 0;`, `a / 3`, `a >> sh`, `$clog2(DEPTH)`, a `while` "
        "loop whose bound depends on an input.",
    ], ordered=True)


# =============================================================================
#  Chapter 4 - Simulation semantics
# =============================================================================
def _ch4():
    chapter("Simulation Semantics: The Event Scheduler, Blocking vs "
            "Non-Blocking, and Races")
    p("Hardware is massively parallel: every gate and flop works at once. A "
      "simulator runs on a sequential CPU. The bridge between the two is "
      "the **event scheduler** defined in IEEE 1800 clause 4, and it "
      "decides what your RTL means in simulation. Understanding it turns "
      "the famous rules - 'use `<=` for flops, `=` for combinational logic' - "
      "from folklore into logic, and it is the key to races, "
      "simulation/synthesis mismatches and X bugs. It is also one of the "
      "most-asked topics in RTL interviews.")

    h2("Processes, events and time steps")
    p("A SystemVerilog simulation is a set of concurrent **processes**: "
      "every `always` and `initial` block, every continuous `assign`, every "
      "gate primitive. A process runs until it hits a timing control "
      "(`@`, `#`, `wait`) and then suspends. An **update event** is a "
      "change of value on a signal; it wakes every process sensitive to "
      "that signal (an **evaluation event**). Simulation time advances only "
      "when no events remain at the current time.")
    box("key", "The fundamental non-determinism",
        "When several processes are ready at the same time in the same "
        "region, the standard lets the simulator run them in **any order**. "
        "Code whose result depends on that order has a **race**: it may "
        "work in one simulator, fail in another, and change behaviour when "
        "an unrelated line is added. Correct RTL is race-free by "
        "construction.")

    h2("The stratified event queue")
    p("Each time step is divided into ordered **regions**. The simulator "
      "executes all events in a region, possibly adding new events to "
      "earlier regions, and loops until everything is empty before "
      "advancing time. The regions that matter to designers are:")
    tbl(["Region", "What executes there"],
        [["**Preponed**", "Sampling of values for concurrent assertions and "
          "clocking-block inputs: the values __before__ anything changes in "
          "this time step"],
         ["**Active**", "Blocking assignments, continuous assignments, "
          "evaluation of the RHS of non-blocking assignments, `$display`, "
          "resumption of processes"],
         ["**Inactive**", "Processes resumed after an explicit `#0` delay"],
         ["**NBA**", "Updates of the LHS of non-blocking assignments "
          "(`<=`), in the order the assignments executed"],
         ["**Observed**", "Evaluation of concurrent assertion properties "
          "using the preponed samples"],
         ["**Reactive** (+ Re-Inactive, Re-NBA)", "Program-block code, "
          "assertion action blocks; mirrors Active/Inactive/NBA for "
          "testbench code"],
         ["**Postponed**", "`$strobe`, `$monitor`; the final, settled values "
          "of the time step. No new events allowed"]],
        widths=[27, 73], bold_first=True,
        caption="Table 4.1 - Scheduling regions (the standard also defines "
                "PLI callback regions such as Pre-Active, omitted here).")
    diagram([
        "  time t:",
        "  +-----------+",
        "  | Preponed  |  sample for assertions",
        "  +-----+-----+",
        "        v",
        "  +-----------+ <-----------------------------------+",
        "  |  Active   |  blocking =, assign, RHS of <=      |",
        "  +-----+-----+                                     |",
        "        v   (Active empty)                          |",
        "  +-----------+                                     |  new events in",
        "  | Inactive  |  #0 resumptions  ----(if any)------>+  earlier regions",
        "  +-----+-----+                                     |  -> go back",
        "        v                                           |",
        "  +-----------+                                     |",
        "  |    NBA    |  LHS <= updates  ----(wake procs)-->+",
        "  +-----+-----+",
        "        v",
        "  +-----------+    +------------------------+    +-----------+",
        "  | Observed  |--->| Reactive/Re-Inact/Re-NBA|--->| Postponed |--> time t+1",
        "  +-----------+    +------------------------+    +-----------+",
    ], "Figure 4.1 - The stratified event queue for one time step. Each pass "
       "Active -> Inactive -> NBA and back is one delta cycle.")
    p("The following testbench makes the regions visible:")
    code(V("""
module tb;
  logic [3:0] a = 4'd0, b = 4'd0;
  initial begin
    a  = 4'd1;                         // blocking: updates now (active region)
    b <= 4'd7;                         // NBA: update scheduled for the NBA region
    $display("display: a=%0d b=%0d", a, b);   // active region: sees old b
    $strobe ("strobe : a=%0d b=%0d", a, b);   // postponed region: sees final values
    #0 $display("#0     : a=%0d b=%0d", a, b); // inactive region: still before NBA
    #1 $display("#1     : a=%0d b=%0d", a, b); // next time step
  end
endmodule
"""))
    out(["display: a=1 b=0",
         "#0     : a=1 b=0",
         "strobe : a=1 b=7",
         "#1     : a=1 b=7"],
        "`$display` prints immediately and sees the old `b`; `#0` defers "
        "only to the Inactive region, which is still before the NBA update; "
        "`$strobe` prints in Postponed, after all updates. Note that the "
        "strobe line appears after the `#0` line even though it was "
        "executed first.")

    h2("Delta cycles")
    p("A **delta cycle** is one iteration through the Active/Inactive/NBA "
      "loop without advancing time. A chain of continuous assignments "
      "`assign b = ~a; assign c = ~b;` settles in successive deltas: `a` "
      "changes, `b` updates in the next evaluation, then `c`. On a "
      "waveform all three change at the same time stamp, but they did so "
      "in a well-defined causal order. Delta cycles are how a simulator "
      "models zero-delay logic without an ordering paradox - and a "
      "combinational loop shows up as a simulation that never leaves the "
      "time step (an infinite delta loop, which simulators report as an "
      "iteration limit).")

    h2("Blocking versus non-blocking assignment")
    tbl(["", "Blocking `a = b;`", "Non-blocking `a <= b;`"],
        [["When the RHS is evaluated", "Immediately", "Immediately (Active)"],
         ["When the LHS is updated", "Immediately, before the next "
          "statement", "Later, in the NBA region, after all Active "
          "processes have run"],
         ["Next statement in the same block sees", "The **new** value",
          "The **old** value"],
         ["Models", "Wires and combinational intermediate values",
          "Flip-flops: every flop samples its D before any Q changes"],
         ["Use in", "`always_comb`", "`always_ff`"]],
        widths=[28, 36, 36], bold_first=True)
    p("The key insight is that **non-blocking assignment models the "
      "physics of a clock edge.** In real hardware, all flops on a clock "
      "sample their D inputs at the same instant, and only afterwards (a "
      "clock-to-Q delay later) do their outputs change. NBA reproduces "
      "exactly this: every `always_ff` evaluates its RHS with the old "
      "values in the Active region, and all LHS updates happen together "
      "in the NBA region. The order in which the simulator runs the blocks "
      "no longer matters.")

    h3("Example 1: the swap")
    code(V("""
module swap_bad (input logic clk, rst, output logic [3:0] a, b);
  always @(posedge clk) if (rst) a = 4'd1; else a = b;   // blocking: RACE
  always @(posedge clk) if (rst) b = 4'd2; else b = a;
endmodule

module swap_good (input logic clk, rst, output logic [3:0] a, b);
  always_ff @(posedge clk) if (rst) a <= 4'd1; else a <= b;
  always_ff @(posedge clk) if (rst) b <= 4'd2; else b <= a;
endmodule

module tb;
  logic clk = 0, rst = 1;
  logic [3:0] a1, b1, a2, b2;
  swap_bad  u_bad  (.clk(clk), .rst(rst), .a(a1), .b(b1));
  swap_good u_good (.clk(clk), .rst(rst), .a(a2), .b(b2));
  always #5 clk = ~clk;
  initial begin
    @(negedge clk) rst = 0;
    repeat (3) @(negedge clk)
      $display("%2t bad: a=%0d b=%0d   good: a=%0d b=%0d", $time, a1, b1, a2, b2);
    $finish;
  end
endmodule
"""))
    out(["20 bad: a=2 b=2   good: a=2 b=1",
         "30 bad: a=2 b=2   good: a=1 b=2",
         "40 bad: a=2 b=2   good: a=2 b=1"],
        "Two registers that should exchange values every cycle. With "
        "non-blocking assignments they do. With blocking assignments, "
        "whichever block runs first overwrites its register before the "
        "other reads it.")
    p("Icarus happened to run the `a` block first, so both became 2; "
      "another simulator - or the same one after an unrelated edit - may "
      "run the `b` block first and give 1 and 1. Synthesis, meanwhile, "
      "builds two cross-coupled flops for __both__ versions, which do swap. "
      "The blocking version is therefore not just wrong in simulation, it "
      "is a **simulation/synthesis mismatch**: the gates you tape out "
      "behave differently from the RTL you verified.")

    h3("Example 2: the shift register")
    code(V("""
module shift_bad (input logic clk, d, output logic q3);
  logic q1, q2;
  always @(posedge clk) begin      // blocking: each line sees the NEW value above it
    q1 = d;
    q2 = q1;
    q3 = q2;
  end
endmodule

module shift_good (input logic clk, d, output logic q3);
  logic q1, q2;
  always_ff @(posedge clk) begin   // NBA: every RHS is sampled before any update
    q1 <= d;
    q2 <= q1;
    q3 <= q2;
  end
endmodule
"""))
    code(V("""
module tb;
  logic clk = 0, d = 0, qb, qg;
  shift_bad  u_b (.clk(clk), .d(d), .q3(qb));
  shift_good u_g (.clk(clk), .d(d), .q3(qg));
  always #5 clk = ~clk;
  initial begin
    $display("cycle d | bad q3  good q3");
    for (int i = 1; i <= 7; i++) begin
      @(negedge clk) d = (i == 3);               // a single 1-cycle pulse
      @(posedge clk) #1 $display("  %0d   %b |   %b        %b", i, d, qb, qg);
    end
    $finish;
  end
endmodule
"""))
    out(["cycle d | bad q3  good q3",
         "  1   0 |   0        x",
         "  2   0 |   0        0",
         "  3   1 |   1        0",
         "  4   0 |   0        0",
         "  5   0 |   0        1",
         "  6   0 |   0        0",
         "  7   0 |   0        0"],
        "The correct shift register delays the pulse by three clock edges "
        "(it was captured at edge 3 and reaches q3 at edge 5, printed just "
        "after). The blocking version passes d straight through: it is one "
        "flop, not three - and synthesis agrees with the simulation this "
        "time, so the bug ships silently as a missing pipeline stage.")
    diagram([
        "  intended (NBA):   d -->[FF q1]-->[FF q2]-->[FF q3]--> q3     3-cycle delay",
        "",
        "  blocking, this order:  d --+--> q1 (FF)",
        "                             +--> q2 (FF)    q1, q2 are the same flop value;",
        "                             +--> q3 (FF)    synthesis merges them: 1-cycle delay",
    ], "Figure 4.2 - What the two shift-register versions infer.")
    box("warn", "Reversing the order 'fixes' it - do not do that",
        "Writing the blocking version bottom-up (`q3 = q2; q2 = q1; q1 = d;`) "
        "happens to model a shift register, and you will see it in old code. "
        "It is fragile: it breaks when the statements are reordered or split "
        "across blocks, and it relies on reasoning that NBA makes "
        "unnecessary. Use `<=` in every clocked block.")

    h3("The guidelines")
    p("Clifford Cummings' classic SNUG 2000 paper distilled these rules, and "
      "they remain the industry standard:")
    bul([
        "Sequential logic (flops, latches): **non-blocking** `<=`.",
        "Combinational logic in an `always` block: **blocking** `=`.",
        "Sequential and combinational logic in the same block: non-blocking "
        "- better still, split them (the `_d`/`_q` style of Chapter 3).",
        "Never mix `=` and `<=` for the same variable, or in the same block.",
        "Never assign the same variable from more than one `always` block "
        "(`always_ff`/`always_comb` make this a compile error).",
        "Use `$strobe` (or print after a small delay) to display values "
        "updated by NBAs.",
        "Do not use `#0` assignments.",
    ], ordered=True)

    h2("Why blocking for combinational logic")
    p("Inside `always_comb`, intermediate variables must behave like wires: "
      "a later statement must see the value computed by an earlier one "
      "__in the same evaluation__. Blocking assignment does exactly that. "
      "If you used `<=` in combinational logic, a statement reading an "
      "intermediate variable would see its stale value; the block would "
      "then re-trigger when the NBA update arrives and settle one delta "
      "later. The final value is usually right, but the simulation is "
      "slower, the waveform shows spurious transitions, and any code "
      "sampling the signal in between - for instance a `$display` or an "
      "assertion - sees garbage. And with `always @(a)`-style incomplete "
      "lists it can simply be wrong.")
    code(V("""
always_comb begin
  tmp = a & b;          // blocking: tmp is updated now...
  y   = tmp | c;        // ...so this sees the new tmp, like a wire
end
"""), "Correct: a two-gate network described with blocking assignments.")

    h2("Races between always blocks and between testbench and DUT")
    p("A race exists whenever two processes triggered by the same event "
      "communicate through a variable updated with a blocking assignment. "
      "Between RTL blocks, NBA removes the race (Example 1). The more "
      "insidious case is the **testbench-to-DUT race**: the testbench "
      "drives an input with a blocking assignment on the same clock edge "
      "at which the DUT samples it.")
    code(V("""
module dff (input logic clk, d, output logic q);
  always_ff @(posedge clk) q <= d;
endmodule

module tb;
  logic clk = 0, d_race = 0, d_safe = 0, q_race, q_safe;
  dff u_race (.clk(clk), .d(d_race), .q(q_race));
  dff u_safe (.clk(clk), .d(d_safe), .q(q_safe));
  always #5 clk = ~clk;
  initial begin
    @(posedge clk);
    d_race  = 1;          // blocking at the clock edge: races with the DUT's sampling
    d_safe <= 1;          // NBA at the edge: DUT always samples the OLD value
    @(posedge clk) #1;
    $display("after 2nd edge: q_race=%b q_safe=%b", q_race, q_safe);
    $finish;
  end
  initial begin
    @(posedge clk) #1;
    $display("after 1st edge: q_race=%b q_safe=%b", q_race, q_safe);
  end
endmodule
"""))
    out(["after 1st edge: q_race=1 q_safe=0",
         "after 2nd edge: q_race=1 q_safe=1"],
        "Here the testbench process ran before the flop's process, so the "
        "flop captured the new value at the very edge that 'produced' it - "
        "a zero-cycle path that real hardware can never have. The NBA "
        "version is deterministic.")
    p("Robust testbenches remove the race structurally:")
    bul([
        "Drive DUT inputs on the **opposite clock edge** (as the `drive` "
        "task in Chapter 3 does), or with NBAs at the active edge.",
        "Better, use a **clocking block**: it samples DUT outputs in the "
        "Preponed region (the values from just before the edge) and drives "
        "inputs with a specified skew after the edge - exactly like a real "
        "synchronous neighbour. Chapter 22 builds testbenches this way.",
        "Program blocks (Reactive region) were introduced for the same "
        "purpose; clocking blocks in modules are now the common practice.",
    ])
    box("warn", "#0 is not a fix",
        "Adding `#0` moves a process to the Inactive region, which runs "
        "after the Active region - so it can make one particular race "
        "disappear. But the next engineer who adds another `#0` restores "
        "the race one level deeper. The standard's own guidance is to avoid "
        "`#0`; treat it as a code smell in any review.")

    h2("Sensitivity lists and simulation/synthesis mismatch")
    p("Synthesis **ignores** sensitivity lists: it builds hardware from "
      "the statements in the block. Simulation obeys them literally: a "
      "block runs only when a listed signal changes. An incomplete list "
      "therefore makes the RTL simulate differently from the gates.")
    code(V("""
module and_incomplete (input logic a, b, output logic y);
  always @(a) y = a & b;          // b missing from the list: simulation-only bug
endmodule
module and_comb (input logic a, b, output logic y);
  always_comb y = a & b;          // implied complete sensitivity
endmodule
module tb;
  logic a = 0, b = 0, y1, y2;
  and_incomplete u1 (.a(a), .b(b), .y(y1));
  and_comb       u2 (.a(a), .b(b), .y(y2));
  initial begin
    #1 a = 1;  #1 $display("a=%b b=%b | @(a): y=%b  always_comb: y=%b", a, b, y1, y2);
    #1 b = 1;  #1 $display("a=%b b=%b | @(a): y=%b  always_comb: y=%b", a, b, y1, y2);
    #1 a = 0;  #1 $display("a=%b b=%b | @(a): y=%b  always_comb: y=%b", a, b, y1, y2);
  end
endmodule
"""))
    out(["a=1 b=0 | @(a): y=0  always_comb: y=0",
         "a=1 b=1 | @(a): y=0  always_comb: y=1",
         "a=0 b=1 | @(a): y=0  always_comb: y=0"],
        "When b rises, the incomplete block does not wake up, so y stays 0 "
        "- it behaves like a latch in simulation. The synthesized AND gate "
        "outputs 1. Gate-level simulation or silicon will disagree with "
        "your RTL regressions.")
    tbl(["Mismatch source", "Simulation does", "Synthesis builds",
         "Prevention"],
        [["Incomplete sensitivity list", "Holds old value", "Pure "
          "combinational logic", "`always_comb` / `@*`"],
         ["`#` delays in RTL", "Delays events", "Ignores delays",
          "No delays in RTL"],
         ["Blocking in flops (swap)", "Order-dependent race",
          "Correct flops", "`<=` in `always_ff`"],
         ["`initial` values (ASIC)", "Registers start known",
          "Registers start random", "Reset every control flop"],
         ["`casex`/`casez` with x inputs, `full_case`/`parallel_case` "
          "pragmas", "Matches/ignores x or unlisted items", "Different "
          "logic from the pragmas", "`unique`/`priority` case; no pragmas "
          "(Ch 5)"],
         ["X optimism (next section)", "Picks a branch for x",
          "Real 0/1 hardware", "X-prop sim, assertions, reset"]],
        widths=[25, 23, 22, 30], bold_first=True,
        caption="Table 4.2 - The usual sources of simulation/synthesis "
                "mismatch. Gate-level simulation and equivalence checking "
                "(Chapters 25-26) exist largely to catch these.")

    h2("X-propagation: optimism and pessimism")
    p("An x in simulation stands for a value that real hardware would have "
      "as a definite 0 or 1 - we just do not know which. Ideally x would "
      "propagate exactly as far as the uncertainty does in hardware. "
      "Verilog's semantics do not achieve that; they err in both "
      "directions.")
    code(V("""
module tb;
  logic sel, a, b, y_if, y_tern, y_case;
  always_comb begin
    if (sel) y_if = a;             // X on sel is treated as FALSE -> optimistic
    else     y_if = b;
  end
  assign y_tern = sel ? a : b;     // X on sel merges both inputs bit by bit
  always_comb begin
    case (sel)
      1'b1:    y_case = a;
      1'b0:    y_case = b;
      default: y_case = 1'bx;      // explicit X for "impossible" selects
    endcase
  end
  initial begin
    sel = 1'bx;
    a = 1; b = 0; #1 $display("sel=x a=1 b=0 | if: %b  ?: %b  case: %b", y_if, y_tern, y_case);
    a = 1; b = 1; #1 $display("sel=x a=1 b=1 | if: %b  ?: %b  case: %b", y_if, y_tern, y_case);
  end
endmodule
"""))
    out(["sel=x a=1 b=0 | if: 0  ?: x  case: x",
         "sel=x a=1 b=1 | if: 1  ?: 1  case: x"],
        "Three descriptions of the same 2:1 mux, three different X "
        "behaviours.")
    bul([
        "**X optimism** (`if`): an x condition is treated as false, so the "
        "`else` branch runs and y becomes a clean 0. Real hardware could "
        "have produced 1. The x - which might be an uninitialized register "
        "or a missing reset - is **hidden**, and the bug survives RTL "
        "simulation. The same happens with `case` when no item matches and "
        "there is no default assigning x.",
        "**Accurate** (`?:`): when the select is x, each output bit is x "
        "unless both inputs agree. With a=b=1 the result is 1, which is "
        "exactly what the hardware would do.",
        "**X pessimism** (`case` with default x): y is x even when a=b=1 and "
        "any hardware would output 1. Pessimism causes false failures - "
        "most painfully in gate-level simulation, where an AND-OR mux gives "
        "x for sel=x even with equal inputs, and a flop without reset that "
        "feeds back on itself (`q <= q ^ t`) stays x forever although "
        "silicon would settle.",
    ])
    box("expert", "How professional flows handle X",
        "Commercial simulators offer X-propagation modes (for example "
        "VCS `-xprop`, Xcelium `-xprop`) that make `if`/`case` merge both "
        "branches like `?:`, exposing optimism bugs in RTL. Teams combine "
        "this with: resets on all control flops, assertions such as "
        "`assert property (@(posedge clk) disable iff (!rst_n) !$isunknown(valid))` "
        "on key interface signals, formal X-checks, and a targeted "
        "gate-level simulation run. Chapter 12 discusses which flops need "
        "reset; Chapter 26 covers gate-level X-pessimism in detail.")

    h2("Summary")
    bul([
        "Simulation is a set of concurrent processes scheduled region by "
        "region; order within a region is undefined, which is the root of "
        "all races.",
        "Key regions: Preponed (sampling), Active (blocking, RHS of NBA), "
        "Inactive (#0), NBA (LHS updates), Observed (assertions), Reactive, "
        "Postponed ($strobe, $monitor).",
        "NBA models a clock edge: all flops sample before any updates. Use "
        "`<=` in `always_ff`, `=` in `always_comb`, and never mix them.",
        "Blocking assignments in clocked blocks cause races (swap) or wrong "
        "hardware (shift register). TB/DUT races are avoided with NBAs, "
        "opposite-edge driving, or clocking blocks - never with `#0`.",
        "Incomplete sensitivity lists, delays, initial values and case "
        "pragmas cause simulation/synthesis mismatches; `always_comb` "
        "removes the first.",
        "`if`/`case` are X-optimistic, `?:` is accurate, gate-level "
        "simulation is X-pessimistic. Use resets, X-prop modes and "
        "`$isunknown` assertions.",
    ])
    h2("Exercises")
    bul([
        "Predict the output order of `$display`, `$strobe`, `$monitor` and "
        "a `#0 $display` when all four are executed at time 0 after an NBA "
        "to a monitored variable. Verify in a simulator.",
        "Rewrite `swap_bad` so that it is race-free using only blocking "
        "assignments in a __single__ always block and a temporary variable. "
        "Is this good style? What does synthesis build?",
        "A colleague's shift register passes simulation with blocking "
        "assignments written bottom-up. List three edits that would "
        "silently break it.",
        "Write a testbench with a race that gives different results "
        "depending on the order of two `initial` blocks. Change the order "
        "of the blocks in the file - does Icarus's answer change?",
        "For `always @(a or b) y = sel ? a : b;` describe precisely when "
        "simulation and synthesized hardware disagree.",
        "Design a 4:1 mux whose RTL simulation is neither X-optimistic nor "
        "pessimistic for a single-bit X on either select bit. Test it with "
        "all combinations of sel containing one x.",
    ], ordered=True)
