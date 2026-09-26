"""Part II - Front-End Design (Chapters 6-10).

Real runs used in this part (all pasted verbatim into out() cards):
  * Yosys 0.33 + its bundled ABC against the real SkyWater SKY130
    sky130_fd_sc_hd__tt_025C_1v80 Liberty file (area in um^2, ABC delay in ps).
  * Icarus Verilog 12 for the self-checking constrained-random testbench.
  * Small Python models (NLDM static timing on real SKY130 tables, stuck-at
    fault simulation, March C- memory test, scan test-time arithmetic).
Commercial-tool reports (Design Compiler, PrimeTime, Tessent...) are shown
only as clearly labelled illustrative excerpts.
"""

from asic_guide.common import *  # noqa: F401,F403


def _eqa(lines, caption=None):
    """eq() centres each line; pad them to one width so columns stay aligned."""
    w = max(len(l) for l in lines)
    eq([l.ljust(w) for l in lines], caption)


# =============================================================================
#        CHAPTER 6 - RTL DESIGN FOR ASIC: WHAT THE BACK END NEEDS
# =============================================================================
def _ch6():
    chapter("RTL Design for ASIC: What the Back End Needs from Your RTL",
            newpage=False)
    p("The companion RTL Design guide teaches how to write correct, "
      "synthesizable RTL. This chapter asks a different question: once the "
      "RTL simulates correctly, what does everybody **downstream** of the "
      "RTL designer need from it? In an ASIC project the RTL is read by at "
      "least eight other tools and five other teams - synthesis, static "
      "timing, DFT insertion, formal equivalence, power analysis, "
      "floorplanning, emulation and the software team's models. An RTL "
      "block that is functionally perfect but ignores their needs will "
      "cost weeks in implementation, and in the worst case forces a late "
      "RTL change that re-opens verification.")
    p("An FPGA engineer moving to ASIC usually discovers the differences "
      "the hard way: there is no block RAM to infer, flip-flops do not "
      "power up to the value in your `initial` statement, every reset flop "
      "costs area and a slice of a very large reset tree, and nothing "
      "can be fixed with a bitstream update after tapeout. We go through "
      "these differences one by one, measure some of them with a real "
      "synthesis run against the SkyWater SKY130 library, and finish with "
      "the quality gates and the hand-off package that front-end design "
      "delivers to synthesis.")

    h2("Who consumes your RTL")
    diagram([
        "                               +------------------+",
        "                               |   RTL (.sv/.v)   |",
        "                               |  + filelist      |",
        "                               +--------+---------+",
        "        +-------------+-------------+---+---------+--------------+-------------+",
        "        v             v             v             v              v             v",
        "  +-----------+ +-----------+ +-----------+ +-----------+ +------------+ +-----------+",
        "  | simulation| | lint/CDC/ | | synthesis | | formal    | | emulation/ | | power     |",
        "  | (DV team) | | RDC tools | | (DC/Genus)| | (FPV, LEC)| | FPGA proto | | (RTL est.)|",
        "  +-----------+ +-----------+ +-----+-----+ +-----------+ +------------+ +-----------+",
        "                                    v",
        "                 netlist -> DFT insertion -> STA -> place & route -> sign-off",
        "                 (every one of these inherits the structure of your RTL)",
    ], "Figure 6.1 - The RTL is a shared source. Its structure (hierarchy, "
       "clocks, resets, memories, register boundaries) propagates all the way "
       "to layout.")
    tbl(["Consumer (owner)", "What it needs from the RTL",
         "Symptom when the RTL ignores it"],
        [["Synthesis (implementation / synthesis engineer)",
          "Synthesizable subset, no simulation-only constructs, clean "
          "clock and reset structure, memories as macros, reasonable logic "
          "depth per stage",
          "Latches, huge mux trees, unmet timing that no tool option fixes"],
         ["STA (timing sign-off)",
          "Few, well-defined clocks from known generator modules; "
          "registered block boundaries; documented false/multicycle paths",
          "Hundreds of exceptions, unconstrained paths, clock-on-data "
          "warnings"],
         ["DFT (DFT engineer)",
          "Controllable clocks and resets in test mode, no combinational "
          "loops, no clock-gating without test enable, memory BIST ports",
          "Low scan coverage, un-scannable flops, ATPG DRC violations"],
         ["Formal equivalence (LEC)",
          "Stable register names, no functionality hidden in "
          "`translate_off`, synthesis-compatible semantics",
          "Non-equivalent points, aborted compare points on big datapaths"],
         ["Physical design (PD team)",
          "Hierarchy that maps to a floorplan, registered interfaces "
          "between distant blocks, no giant high-fanout control nets",
          "Congestion, long wires that cannot meet timing, reset/enable "
          "fanout problems"],
         ["Power (power / low-power architect)",
          "Clock enables that can become clock gates, clean power-domain "
          "boundaries, operand isolation opportunities",
          "High dynamic power, isolation cells on thousands of signals"]],
        [2.2, 3.4, 3.2], "Table 6.1 - Downstream consumers of RTL and "
                         "what each one expects.", bold_first=True)

    h2("ASIC versus FPGA coding: the differences that bite")
    p("Most RTL constructs mean the same thing on both targets, but an "
      "FPGA is a pre-fabricated sea of look-up tables, flip-flops with "
      "configurable initial values, block RAMs, DSP slices and a dedicated "
      "global clock network. An ASIC has none of these ready-made: every "
      "flip-flop, every clock buffer and every memory is something you "
      "(or the flow) must choose, place and verify. Table 6.2 lists the "
      "differences that most often break a design that was 'proven on "
      "FPGA'.")
    tbl(["Topic", "FPGA habit", "ASIC reality and rule"],
        [["Initial values",
          "`reg [7:0] cnt = 8'd0;` works: the bitstream loads the value",
          "Ignored by synthesis (or rejected). Silicon flops power up to a "
          "random value. **Every state that matters needs a reset.**"],
         ["Reset style",
          "Often no reset at all (GSR does it), or synchronous reset "
          "(cheaper in LUT fabrics)",
          "Explicit reset strategy: which flops, sync or async, "
          "assertion/de-assertion synchronisation, reset tree built by CTS"],
         ["Memories",
          "Arrays infer block RAM or distributed RAM automatically",
          "Arrays become thousands of flops + muxes. Real memories are "
          "**compiled SRAM macros** instantiated through a wrapper"],
         ["Clock gating",
          "Discouraged; use clock enables (CE pins)",
          "Encouraged, but only through **integrated clock-gating (ICG) "
          "cells**, inserted by the tool or instantiated via a wrapper"],
         ["Clocks",
          "PLL/MMCM primitives, global buffers (BUFG)",
          "Clock generation is analog IP (PLL) plus RTL dividers and "
          "muxes built from dedicated glitch-free cells; the tree is "
          "synthesised by CTS"],
         ["Tri-states",
          "Internal tri-states converted to muxes by the tool",
          "No internal tri-state buses. Tri-states exist only in I/O pads"],
         ["Arithmetic",
          "DSP slices do multiply-accumulate for free",
          "Every multiplier is real area and power; datapath synthesis "
          "chooses architectures (chapter 8)"],
         ["Vendor primitives",
          "Direct instantiation of LUT6, SRL16, IDDR...",
          "Only library cells or technology-independent wrappers; keep "
          "technology cells out of functional RTL"],
         ["Bug fixing",
          "Re-synthesise and reload in minutes",
          "A post-tapeout bug costs a metal or full respin: months and "
          "a large fraction of a mask set cost (chapter 19)"]],
        [1.3, 2.6, 4.2], "Table 6.2 - FPGA habits versus ASIC rules.",
        bold_first=True)
    box("warn", "PITFALL - the initial value that only existed on FPGA",
        ["A classic escape: a state machine written with `reg [2:0] state "
         "= IDLE;` and no reset works for months on the FPGA prototype. On "
         "silicon the register powers up to a random code, often an "
         "unused one, and the FSM never leaves it. Gate-level simulation "
         "shows X, but only if somebody runs it with the right power-up "
         "sequence. Lint rules (for example 'initial statement in "
         "synthesizable code') catch this in seconds - enable them."])

    h2("Reset strategy: which flops need a reset")
    p("Resets are the first place where ASIC RTL differs in cost. A "
      "resettable flop is a larger cell, and the reset net itself is one "
      "of the largest nets on the chip: it reaches a large fraction of all "
      "flops, must be buffered like a clock, and its de-assertion must be "
      "timed (recovery and removal checks) against every clock domain it "
      "reaches. The standard strategy in industry is:")
    bul(["**Reset control state, not data.** FSM state, valid bits, "
         "counters, pointers, configuration registers and anything that "
         "is observed before it is written must be reset. Pure datapath "
         "registers whose content is qualified by a valid bit do not need "
         "one.",
         "**Asynchronous assertion, synchronous de-assertion.** The reset "
         "reaches the flops immediately (works without a clock), but is "
         "released through a 2-flop reset synchroniser per clock domain "
         "so that de-assertion meets recovery/removal timing. The "
         "companion RTL Design guide shows the synchroniser circuit.",
         "**One reset synchroniser per clock domain and per reset "
         "domain**, owned by a dedicated reset-controller module - never "
         "sprinkled in functional blocks.",
         "**Reset sequencing** is a system decision: which domains come "
         "out of reset first (PLL lock, memory repair load, fuse read), "
         "documented in the architecture spec (chapter 5)."])
    p("How much does 'reset everything' cost? The two variants below "
      "implement the same 4-stage, 32-bit pipeline. Variant A resets all "
      "100 flops; variant B resets only the four valid bits. Both were "
      "synthesised with Yosys against the real SKY130 high-density "
      "library (typical corner, 25 C, 1.8 V).")
    code([
        "// Variant A: every flop has an asynchronous reset (FPGA-style 'reset everything')",
        "always @(posedge clk or negedge rst_n)",
        "  if (!rst_n) begin",
        "    {v1, v2, v3, out_vld} <= 4'b0;",
        "    d1 <= 32'd0; d2 <= 32'd0; d3 <= 32'd0; out_dat <= 32'd0;",
        "  end else begin",
        "    v1 <= in_vld; v2 <= v1; v3 <= v2; out_vld <= v3;",
        "    d1 <= in_dat; d2 <= d1 + 32'd1; d3 <= d2 ^ {d2[15:0], d2[31:16]};",
        "    out_dat <= d3;",
        "  end",
        "",
        "// Variant B: only the control (valid) bits are reset; the datapath is not",
        "always @(posedge clk or negedge rst_n)",
        "  if (!rst_n) {v1, v2, v3, out_vld} <= 4'b0;",
        "  else begin v1 <= in_vld; v2 <= v1; v3 <= v2; out_vld <= v3; end",
        "always @(posedge clk) begin               // no reset: data qualified by valid",
        "  d1 <= in_dat; d2 <= d1 + 32'd1; d3 <= d2 ^ {d2[15:0], d2[31:16]};",
        "  out_dat <= d3;",
        "end",
    ], "Two reset strategies for the same pipeline (pipe_a.v / pipe_b.v).")
    code([
        "read_verilog pipe_a.v",
        "synth -top pipe_a -flatten",
        "dfflibmap -liberty hd_tt_du.lib      # map flops to real SKY130 flip-flops",
        "abc -liberty hd_tt_du.lib            # map logic to real SKY130 gates",
        "opt_clean",
        "stat -liberty hd_tt_du.lib           # area from the Liberty 'area' attributes",
    ], "Yosys script. hd_tt_du.lib is the SKY130 hd tt Liberty with clock, "
       "delay, probe and lpflow cells removed - a crude dont_use list.")
    out([
        "=== pipe_b ===",
        "   Number of cells:                190",
        "     sky130_fd_sc_hd__a21oi_1        7",
        "     sky130_fd_sc_hd__a31oi_1        1",
        "     sky130_fd_sc_hd__and3_1         3",
        "     sky130_fd_sc_hd__and4_1         1",
        "     sky130_fd_sc_hd__dfrtp_1        4",
        "     sky130_fd_sc_hd__dfxtp_1       96",
        "     sky130_fd_sc_hd__inv_1         13",
        "     sky130_fd_sc_hd__nand2_1        3",
        "     sky130_fd_sc_hd__nand3_1        2",
        "     sky130_fd_sc_hd__nand4_1        5",
        "     sky130_fd_sc_hd__nor2_1        12",
        "     sky130_fd_sc_hd__nor4_1         4",
        "     sky130_fd_sc_hd__xnor2_1       14",
        "     sky130_fd_sc_hd__xor2_1        25",
        "   Chip area for module '\\pipe_b': 2603.747200",
    ], "Real Yosys 0.33 stat -liberty output for variant B (areas in um^{2}).")
    out([
        "=== pipe_a ===",
        "   Number of cells:                190",
        "     sky130_fd_sc_hd__dfrtp_1      100",
        "     (all 12 combinational cell types and counts identical to pipe_b)",
        "   Chip area for module '\\pipe_a': 3084.208000",
    ], "Real Yosys output for variant A (excerpt: only the lines that differ).")
    p("The combinational logic is identical; the only change is that 96 "
      "flops moved from `dfrtp_1` (D flop with active-low async reset, "
      "25.02 um^{2} in the Liberty file) to `dfxtp_1` (plain D flop, "
      "20.02 um^{2}). That is 5.0 um^{2} per flop, 480 um^{2} in total, "
      "**15.6% of the block area**. In a real chip the saving is larger "
      "than the cell area suggests, because every removed reset pin is "
      "one less sink on the reset tree that CTS must buffer and balance, "
      "and one less recovery/removal timing check.")
    box("expert", "INTERVIEW INSIGHT - sync or async reset?",
        ["Asynchronous reset works without a running clock (needed at "
         "power-up and for clock-gated or PLL-bypassed domains), and it "
         "keeps the reset out of the D-input logic cone, so it does not "
         "add delay to the data path. Its costs are a larger flop, a "
         "reset tree that must be timed for recovery/removal, and "
         "glitch sensitivity. Synchronous reset uses a plain flop plus an "
         "AND gate in the data path and needs the clock running. The "
         "safe default in most ASIC teams is async assert / sync "
         "de-assert, applied only to the flops that need it - but the "
         "decision belongs to the project's RTL guidelines, and **mixing "
         "styles inside a block is the real mistake**."])

    h2("Memories: macros and wrappers instead of inferred arrays")
    p("On an FPGA, `reg [15:0] mem [0:63]` becomes a block RAM. In an "
      "ASIC flow, a synthesis tool has no memory primitives: the array "
      "becomes discrete flip-flops plus write-enable and read muxes. This "
      "is acceptable for small register files (tens to a few hundred "
      "bits); beyond that it is a disaster for area, power and "
      "routability. The same 64x16 array synthesised against SKY130:")
    out([
        "=== rf64x16 ===",
        "   Number of cells:               2596",
        "     sky130_fd_sc_hd__dfxtp_1     1040",
        "     sky130_fd_sc_hd__mux2_1      1024",
        "     sky130_fd_sc_hd__mux2i_1      144",
        "     sky130_fd_sc_hd__mux4_2       288",
        "     ... (93 small decode gates omitted)",
        "   Chip area for module '\\rf64x16': 40767.849600",
    ], "Real Yosys output (excerpt): a 1 Kbit memory written as an array "
       "costs about 40,800 um^{2} in SKY130 - roughly 40 um^{2} per bit.")
    p("Look at the cells. 1040 flops (1024 storage bits plus the 16-bit "
      "read register), **1024 mux2 cells** that implement 'hold the old "
      "value unless written' (because this mapping flow could not use an "
      "enable flop), and 432 mux2/mux4 cells forming the 64:1 read "
      "multiplexer. A compiled SRAM macro stores a bit in a 6-transistor "
      "bitcell that is typically several times to an order of magnitude "
      "smaller than a flop plus its muxes, and its peripheral circuits "
      "(sense amplifiers, decoders) amortise over thousands of bits. The "
      "rule most teams use: **above a few hundred bits, use a memory "
      "compiler macro**; below that, a latch- or flop-based register "
      "file generated by a register-file compiler or by synthesis.")
    h3("The memory wrapper")
    p("Functional RTL should never instantiate a foundry memory macro "
      "directly. Instead it instantiates a **technology-independent "
      "wrapper** with a clean interface. Inside the wrapper, a "
      "`generate`/`ifdef` selects a behavioural model for simulation and "
      "FPGA, or the real macro(s) for the ASIC netlist. The wrapper is "
      "where all the ASIC-only plumbing lives:")
    diagram([
        "  functional RTL             mem_wrap_1024x32 (owned by the memory/DFT team)",
        "  +--------------+   +--------------------------------------------------------+",
        "  | ce, we, addr |-->| +---------+   +----------------+   +----------------+  |",
        "  | wdata, bwe   |   | | BIST mux|-->| ASIC: SRAM     |-->| ECC / parity   |--+--> rdata",
        "  | rdata  <-----|---| | (test / |   | macro(s), e.g. |   | check (option) |  |",
        "  +--------------+   | | func)   |   | 2 x 512x32     |   +----------------+  |",
        "                     | +----^----+   +---^----^---^---+                       |",
        "   MBIST controller -+------+            |    |   +-- repair bus (from fuses) |",
        "   (chapter 10)      |                   |    +------ power: retention/sleep  |",
        "                     |                   +----------- margin / timing adjust  |",
        "                     |  FPGA/sim: behavioural array model in the same wrapper |",
        "                     +--------------------------------------------------------+",
    ], "Figure 6.2 - A memory wrapper hides the macro and carries the BIST, "
       "repair, power-management and ECC hooks.")
    code([
        "module mem_wrap_1024x32 (input  logic clk, ce, we,",
        "                         input  logic [9:0]  addr,",
        "                         input  logic [31:0] wdata, bwe,     // bit-write enable",
        "                         output logic [31:0] rdata,",
        "                         mbist_if.mem        bist,           // test port",
        "                         input  logic        ls, ds);        // light/deep sleep",
        "`ifdef ASIC",
        "  // two 512x32 compiler instances + BIST mux, repair and power pins",
        "  sram_sp_512x32 u_bank0 (...);  sram_sp_512x32 u_bank1 (...);",
        "`else",
        "  logic [31:0] mem [0:1023];                  // behavioural model",
        "  always_ff @(posedge clk) if (ce) begin",
        "    if (we) for (int i = 0; i < 32; i++) if (bwe[i]) mem[addr][i] <= wdata[i];",
        "    rdata <= mem[addr];                       // read-first, 1-cycle latency",
        "  end",
        "`endif",
        "endmodule",
    ], "Skeleton of a memory wrapper. Port names of real compiled macros "
       "differ per memory compiler; the wrapper isolates the design from "
       "them.")
    bul(["**Match the macro's behaviour exactly** in the model: read "
         "latency, read-during-write behaviour, bit-write granularity and "
         "what happens to `rdata` when `ce` is low. Mismatches here are a "
         "favourite source of silicon bugs because the model is what DV "
         "verified.",
         "**BIST and repair ports** are planned from day one (chapter 10). "
         "Adding them after floorplanning moves macros and wires.",
         "**Power pins** (light sleep, deep sleep, shut-down, retention) "
         "are controlled by the power controller defined in the UPF "
         "(chapter 11).",
         "**Macro count and aspect ratio** are a floorplan decision: two "
         "512-deep instances may place better than one 1024-deep."])

    h2("Clock gating in RTL")
    p("Clock gating is the single most effective dynamic-power technique "
      "in digital ASICs (chapter 11): a register bank that loads only "
      "occasionally should not see a toggling clock. In ASIC RTL you "
      "almost never build the gate yourself. Instead you write a clean "
      "**enable** and let synthesis replace the feedback multiplexer "
      "with an **integrated clock-gating (ICG) cell** - a latch plus AND "
      "gate characterised as one cell with a setup/hold check on the "
      "enable. SKY130 provides `dlclkp` (17.5 um^{2} for the _1 size) and "
      "the test-enabled `sdlclkp` (18.8 um^{2}).")
    diagram([
        "  RTL you write:                        What synthesis builds (ICG cell, e.g. sdlclkp):",
        "                                        +--------------------------------------+",
        "  always_ff @(posedge clk)              |  en --+                              |",
        "    if (en) q <= d;                     |       | OR   +--------+              |",
        "                                        |       +----->| D    Q |--+   +-----+ |",
        "                                        |  te --+      | latch  |  +-->|     | |",
        "                                        |              | (open  |      | AND |-+--> gclk",
        "                                        |  clk ---+--->| G low) |  +-->|     | |",
        "                                        |         |    +--------+  |   +-----+ |",
        "                                        |         +----------------+           |",
        "                                        +--------------------------------------+",
        "  Without gating: a mux in front of every flop, and the clock toggles every cycle.",
        "  With gating: one ICG drives N flops, the muxes disappear, gclk toggles only when en=1.",
    ], "Figure 6.3 - A latch-based ICG. The latch is transparent while the "
       "clock is low, so the enable cannot change while gclk is high: no "
       "glitches. te (test enable) forces the clock on during scan shift.")
    bul(["Write enables at the **group level** (a whole 32-bit register "
         "loads together) - synthesis gates only banks whose width "
         "exceeds a minimum (commonly 3-8 flops).",
         "Never build a clock gate from an AND or OR gate in RTL. A "
         "combinational gate on the clock glitches, is invisible to "
         "STA's clock-gating checks unless constrained, and breaks scan.",
         "If you must gate explicitly (for example to gate an entire "
         "sub-system), instantiate a **clock-gate wrapper** module "
         "(`cg_wrap`) that maps to the library ICG and has a `test_en` "
         "port tied to the DFT scan-enable/test-mode signal.",
         "Clock muxes and dividers likewise use dedicated glitch-free "
         "wrapper cells owned by the clocking team."])

    h2("No internal tri-states, and synchronous design")
    p("Internal tri-state buses were common in the 1990s. Modern flows "
      "forbid them: they cannot be timed cleanly, create contention "
      "during scan shift (two drivers enabled by random scan data), "
      "float to mid-rail and burn crowbar current when no driver is "
      "enabled, and complicate equivalence checking. Use multiplexers "
      "or AND-OR buses. Tri-states survive only in I/O pad cells.")
    p("The ASIC flow also assumes a **fully synchronous** design style: "
      "registers clocked by a small number of well-defined clocks, with "
      "all asynchronous interactions confined to reviewed synchroniser "
      "cells. Things that are illegal or strongly discouraged:")
    bul(["Combinational feedback loops (STA cannot time them, ATPG "
         "cannot handle them).",
         "Using data signals as clocks (ripple counters, 'clock = "
         "counter[3]') outside the clock-generation module.",
         "Latches, except intentional ones (ICGs, latch-based register "
         "files, time-borrowing designs) that are reviewed and "
         "constrained.",
         "Delay chains built from buffers to 'fix' a race: delay varies "
         "by 2x or more over PVT corners (chapter 9).",
         "Asynchronous set **and** reset on the same flop, and resets "
         "generated from combinational logic without a synchroniser."])

    h2("Hierarchy for physical design")
    p("The RTL hierarchy becomes the starting point of the floorplan. "
      "Synthesis may flatten small modules, but large blocks usually keep "
      "their hierarchy (for runtime, for hierarchical implementation, "
      "and for ECO traceability). A few structural rules make physical "
      "design dramatically easier:")
    diagram([
        "  chip_top  (pads, I/O ring, only instantiations - no logic)",
        "   |-- chip_core",
        "   |    |-- clk_rst_gen      PLL wrapper, dividers, clock muxes, reset synchronisers",
        "   |    |-- pmu / power_ctl  power switches, isolation/retention control (UPF)",
        "   |    |-- dft_top          TAP, test-mode decode, OCCs, compression, MBIST ctrl",
        "   |    |-- cpu_ss           <- hard partition: implemented separately, reused",
        "   |    |-- npu_ss           <- hard partition, its own power domain",
        "   |    |-- noc / interconnect   registered at every partition boundary",
        "   |    |-- periph_ss        UART/SPI/I2C/timers (soft, flattened)",
        "   |    +-- mem_ss           SRAM wrappers grouped where the floorplan wants them",
        "   +-- io_ring               pad cells, ESD, level shifters (chapter 12)",
    ], "Figure 6.4 - A physically aware chip hierarchy. The top level only "
       "connects; each subsystem is a candidate floorplan region or hard "
       "partition.")
    bul(["**No glue logic at the top level.** Top-level logic becomes "
         "orphan cells that the floorplan must place somewhere and time "
         "against every partition.",
         "**Register the interfaces** of blocks that will be far apart. A "
         "wire across a 10 mm die can take a large fraction of a "
         "nanosecond even with repeaters (chapter 17); flops at both ends "
         "keep the path budget local.",
         "**Keep clocks, resets and test control in dedicated modules** "
         "so their special handling (dont_touch, CTS exceptions, DFT "
         "overrides) is applied to one place.",
         "**Group by power domain and by clock domain**: one module "
         "should not straddle two power domains.",
         "**Stable, meaningful instance and register names**: timing "
         "constraints, UPF, LEC mapping and post-silicon debug all refer "
         "to them by name.",
         "**Parameterise, but elaborate once**: the implementation team "
         "needs to know exactly which parameter set is taped out."])

    h2("Clocks, resets, CDC and RDC in one page")
    p("Clock-domain crossing (CDC) and reset-domain crossing (RDC) are "
      "covered in depth in the companion RTL Design guide; here is what "
      "matters for the ASIC flow and sign-off:")
    tbl(["Item", "RTL rule", "Checked by"],
        [["Single-bit control crossing", "2- or 3-flop synchroniser cell "
          "from a library wrapper (named, so STA can find it)",
          "Structural CDC tool (Spyglass CDC, Questa CDC, Meridian)"],
         ["Multi-bit data crossing", "Gray-coded pointers (async FIFO) or "
          "req/ack handshake with data held stable", "CDC tool + formal"],
         ["Reconvergence", "Never synchronise related bits separately and "
          "recombine them", "CDC tool (reconvergence rule)"],
         ["Reset de-assertion", "Per-domain reset synchroniser; async "
          "assert, sync de-assert", "RDC tool, STA recovery/removal"],
         ["Reset-domain crossing", "Flop in domain reset A feeding a flop "
          "in reset domain B must be isolated or B must be reset too",
          "RDC tool"],
         ["Timing of crossings", "Constrained with `set_max_delay "
          "-datapath_only` or clock groups, never left unconstrained by "
          "accident", "STA constraint review"]],
        [1.6, 3.6, 2.4], "Table 6.3 - CDC/RDC rules and the tools that "
                         "sign them off.", bold_first=True)

    h2("Pipelining for timing: logic depth per stage")
    p("Synthesis can size gates, restructure logic and even retime "
      "registers, but it cannot rescue a design whose pipeline stage "
      "holds three times more logic than the clock period allows. The "
      "front-end designer must budget **logic depth per stage** early. "
      "A useful technology-independent unit is the **FO4 delay**: the "
      "delay of an inverter driving four copies of itself.")
    _eqa(["cycle time  ~  (logic depth in FO4) x t_FO4",
          "            + clk->Q + setup + clock skew/uncertainty  (roughly 3-6 FO4)",
          "",
          "typical budgets: very high-speed CPU pipelines ~ 12-20 FO4 per stage;",
          "                 ASIC SoC logic ~ 25-50 FO4; low-power MCUs ~ 60+ FO4"],
         "Rule-of-thumb cycle budget (the numbers are indicative, they "
         "vary by design style and team).")
    p("In SKY130 at the typical corner, a small gate with a realistic "
      "load is on the order of 50-100 ps (the real NLDM lookups in "
      "chapter 9 give 40-100 ps per stage), so a 100 MHz clock (10 ns) "
      "comfortably fits 50+ gate levels, while at 500 MHz the whole "
      "budget, including clock-to-Q and setup, is 2 ns. Guidelines:")
    bul(["**Register outputs of every block** and, for high-speed "
         "blocks, inputs as well.",
         "Split wide comparators, priority encoders and multi-level muxes "
         "into two stages when they sit between other heavy logic.",
         "Keep **retiming-friendly** structure: a pipeline register "
         "placed after a large arithmetic block with no reset and no "
         "observation in between can be moved by synthesis retiming "
         "(chapter 8); a register with reset, enable and debug "
         "visibility usually cannot.",
         "Watch **high-fanout control** (stall, flush, global enables): "
         "an enable driving 2,000 flops needs a buffer tree that alone "
         "costs several gate delays. Replicate or pipeline it.",
         "Put memories on stage boundaries: SRAM access time is often the "
         "longest single delay in a pipeline; drive macro inputs directly "
         "from flops and register the outputs."])

    h2("DFT-friendly RTL")
    p("Scan insertion (chapter 10) turns every flop into a scan flop and "
      "stitches them into chains. It works automatically **if** the RTL "
      "obeys a short list of rules; otherwise the ATPG tool reports DRC "
      "violations and the affected flops are excluded, lowering test "
      "coverage.")
    tbl(["Rule", "Why", "Typical fix in RTL"],
        [["All clocks controllable from a test clock",
          "ATPG must pulse the clock at will during shift and capture",
          "Clock mux (test_mode) in clk_rst_gen; OCC for at-speed"],
         ["Async set/reset controllable",
          "A reset driven by functional logic can fire during shift and "
          "corrupt the chain",
          "Gate internally generated resets with test_mode / scan_en"],
         ["ICGs have a test enable",
          "Otherwise gated flops cannot be shifted",
          "Use `sdlclkp`-style ICG, TE tied to scan_en or test_mode"],
         ["No combinational loops", "ATPG cannot evaluate loops",
          "Break with a flop, or with a test-mode mux"],
         ["Avoid latches in data paths",
          "Latches need special handling (transparent in test)",
          "Replace with flops, or make them transparent in test mode"],
         ["Memories bypassable",
          "Macro outputs are X-sources for logic test",
          "Memory wrapper with bypass / 'observe-through' mode"],
         ["Black boxes and analog outputs",
          "Unknown values (X) propagate and destroy compression",
          "Tie-off or register analog outputs in test mode (X-bounding)"]],
        [2.1, 2.8, 2.9], "Table 6.4 - RTL rules that keep scan and ATPG "
                         "clean.", bold_first=True)

    h2("Low-power-friendly RTL")
    p("Most power is decided by the architecture and the RTL, long "
      "before any implementation tool sees the design (chapter 11 goes "
      "into UPF, power gating and DVFS). The RTL designer controls:")
    bul(["**Clock enables everywhere they are natural** - load registers "
         "only when their value changes, so synthesis can insert ICGs. "
         "Clock-tree and flop power are often a third or more of dynamic "
         "power in SoC logic.",
         "**Operand isolation**: hold the inputs of a large multiplier or "
         "adder stable when its result is not used, so the datapath does "
         "not toggle for nothing.",
         "**Memory access discipline**: do not assert chip-enable every "
         "cycle 'because it is simpler'; an SRAM read typically costs far "
         "more energy than the logic around it.",
         "**Avoid glitchy structures**: long chains of XORs and ripple "
         "arithmetic generate spurious transitions; balanced trees and "
         "pipelining reduce glitch power.",
         "**Power-domain-clean interfaces**: signals leaving a domain that "
         "can be switched off must be isolatable (clamp value defined in "
         "the spec), and retention requirements known per register."])

    h2("RTL quality gates")
    p("Before RTL is handed to synthesis for a milestone, it must pass a "
      "set of automated quality gates. Mature teams run them in "
      "continuous integration on every commit, and track violations and "
      "waivers per block.")
    tbl(["Gate", "What it checks", "Typical tools"],
        [["Lint", "Synthesizability, width mismatches, latches, "
          "multiple drivers, unused signals, naming and coding rules",
          "Spyglass Lint, Ascent Lint, Verilator --lint-only, Verible"],
         ["CDC", "Unsynchronised crossings, reconvergence, glitchy "
          "synchroniser inputs, data stability of handshakes",
          "Spyglass CDC, Questa CDC, Meridian CDC"],
         ["RDC", "Reset-domain crossings, reset synchroniser structure, "
          "reset ordering", "Spyglass RDC, Questa RDC, Meridian RDC"],
         ["Synthesis sanity", "Elaborates in the real synthesis tool, no "
          "unexpected latches, no black boxes, area/timing roughly as "
          "budgeted, no constant-propagated logic you expected to keep",
          "DC/Genus quick run, Yosys"],
         ["X-propagation", "Reset values complete; X from uninitialised "
          "state does not reach outputs under X-pessimistic/optimistic "
          "semantics", "Simulator X-prop modes, formal X-prop app"],
         ["DFT rule check (RTL)", "Clock/reset controllability, loops, "
          "ICG test enables", "Tessent / DFT Compiler RTL DRC"],
         ["Power lint", "Enable efficiency, UPF consistency",
          "PowerArtist, Joules, SpyGlass Power"]],
        [1.3, 4.0, 2.6], "Table 6.5 - RTL quality gates.", bold_first=True)
    box("warn", "PITFALL - the waiver file nobody reads",
        ["Lint and CDC tools produce thousands of messages on a large "
         "design. Teams respond with waiver files; after a few months the "
         "waivers hide real bugs. Good practice: every waiver has an "
         "owner, a reason and a pattern that is as narrow as possible "
         "(instance + signal, never a whole rule), and waivers are "
         "reviewed at each milestone like code."])

    h2("The hand-off package to synthesis")
    p("The RTL freeze for a milestone is not 'the Git tag'. It is a "
      "package with a defined content that the implementation team can "
      "run without asking questions.")
    tbl(["Deliverable", "Content", "Owner"],
        [["RTL + filelist", "Tagged source, one filelist per top, all "
          "defines/parameters for the taped-out configuration",
          "RTL lead"],
         ["Constraints (SDC)", "Clocks, generated clocks, I/O delays, "
          "clock groups, exceptions with justification",
          "RTL designer + timing owner"],
         ["Power intent (UPF)", "Domains, supplies, isolation, retention, "
          "level shifters (chapter 11)", "Low-power architect"],
         ["Memory and IP list", "Macro configurations, compiler versions, "
          "hard IP views (LEF, Liberty, GDS, models)", "IP/memory owner"],
         ["DFT specification", "Test modes, scan chain count, compression "
          "ratio, MBIST grouping, OCC locations", "DFT lead"],
         ["Quality reports", "Lint/CDC/RDC clean or waived, synthesis "
          "sanity area/timing, coverage status", "RTL + DV leads"],
         ["Known issues / ECO list", "Open bugs, planned late changes, "
          "blocks expected to change", "Project lead"]],
        [1.6, 4.2, 1.6], "Table 6.6 - The front-end hand-off package.",
        bold_first=True)
    checklist("RTL ready-for-synthesis checklist", [
        "No `initial` blocks, delays (#), `force`, or simulation-only "
        "constructs outside `translate_off` regions that do not change "
        "function.",
        "Every flop that holds control state has a documented reset; "
        "datapath flops without reset are qualified by valid.",
        "All memories above the agreed size go through wrappers with "
        "BIST, repair and power ports.",
        "No clock or reset generated outside clk_rst_gen; all clock "
        "gating via ICG wrappers or tool-inferred enables.",
        "No internal tri-states, combinational loops or unreviewed "
        "latches.",
        "Lint, CDC, RDC and DFT-RTL checks clean or waived with owner and "
        "reason.",
        "Quick synthesis meets area and timing budgets within the agreed "
        "margin; SDC and UPF delivered and reviewed.",
    ])

    h2("Summary")
    bul(["RTL is read by synthesis, STA, DFT, LEC, PD, power and "
         "emulation; its structure propagates all the way to layout.",
         "ASIC silicon has no initial values, no block RAM and no global "
         "clock buffers: resets, memory macros and clock gating are "
         "explicit design decisions.",
         "Reset only what needs it: in our SKY130 run, removing reset "
         "from 96 datapath flops saved 15.6% of block area.",
         "A 1 Kbit array synthesised to flops cost about 40 um^{2} per bit; "
         "memories go through wrappers that carry BIST, repair, power and "
         "ECC hooks.",
         "Code clock enables and let synthesis insert ICGs; never gate "
         "clocks with plain logic.",
         "Plan hierarchy for the floorplan: no top-level glue, registered "
         "interfaces, dedicated clock/reset/test/power modules.",
         "Budget logic depth per stage, follow DFT and low-power rules, "
         "and pass lint/CDC/RDC/X-prop gates before the hand-off package "
         "goes to synthesis."])

    h2("Exercises")
    bul(["A block has 12,000 flops, of which 1,800 hold control state. "
         "Using the SKY130 areas from this chapter (dfrtp_1 = 25.02 um^{2}, "
         "dfxtp_1 = 20.02 um^{2}), estimate the area saved by resetting "
         "only the control flops. What other costs go away?",
         "Rewrite `reg [3:0] state = 4'd0;` for an ASIC and explain what "
         "happens on silicon and in gate-level simulation if you do not.",
         "Sketch the memory wrapper ports for a 4096x64 single-port SRAM "
         "with byte-write enables, MBIST, redundancy repair and a "
         "light-sleep mode. Which team owns each port?",
         "Explain why a clock gate built from an AND gate glitches, and "
         "why a latch-based ICG does not. Draw the waveforms.",
         "Your block must run at 800 MHz in a node where t_FO4 is about "
         "15 ps. How many FO4 of logic fit in a stage after 5 FO4 of "
         "overhead? Is a 32-bit ripple-carry adder feasible in one stage?",
         "List five RTL constructs that make scan insertion fail or lower "
         "coverage, and the fix for each."], ordered=True)


# =============================================================================
#          CHAPTER 7 - FUNCTIONAL VERIFICATION STRATEGY AND SIGN-OFF
# =============================================================================
def _ch7():
    chapter("Functional Verification Strategy and Sign-off")
    p("An ASIC cannot be patched. Every functional bug that escapes to "
      "silicon costs either a software workaround (lost features or "
      "performance), a metal-layer ECO respin, or a full respin - months "
      "of schedule and, at advanced nodes, mask sets costing millions of "
      "dollars (chapter 19). This is why **functional verification is "
      "typically the largest single effort on an ASIC project**: industry "
      "surveys consistently report that verification engineers outnumber "
      "design engineers, and that verification consumes on the order of "
      "half to two-thirds of the front-end effort.")
    p("The companion Verilog & SystemVerilog guide teaches the language "
      "machinery: classes, constraints, covergroups, assertions and UVM. "
      "This chapter is about **strategy**: how a project decides what to "
      "verify, at which level, with which technique (simulation, formal, "
      "emulation, prototyping), how it measures progress, and what "
      "evidence it must show before the verification lead signs the "
      "tapeout checklist.")

    h2("Why verification dominates, and how it is organised")
    tbl(["Metric", "Typical range (indicative)", "Comment"],
        [["DV : design engineer ratio", "about 1:1 to 3:1",
          "Higher for CPUs, GPUs, safety-critical and protocol-heavy IP"],
         ["Share of front-end effort", "roughly 50-70%",
          "Includes testbench development, debug, coverage closure"],
         ["Bugs found per phase", "most in block level; the costly ones "
          "at SoC level", "Integration bugs: connectivity, clocks, resets, "
          "address maps, power sequencing"],
         ["First-silicon success", "a minority of projects are fully "
          "functional on first silicon",
          "Logic/functional bugs are the leading cause of respins in "
          "published surveys"]],
        [2.1, 2.6, 3.5], "Table 7.1 - Verification in numbers. Figures "
                         "are ranges commonly quoted in industry surveys, "
                         "not precise statistics.", bold_first=True)
    p("Ownership is clear in a mature organisation: the **DV lead** owns "
      "the verification plan and sign-off; **block DV engineers** own "
      "testbenches per IP; an **SoC DV team** owns integration tests, "
      "often together with **firmware/validation engineers** who run "
      "real software on emulation; a **formal team** (or formal-trained "
      "DV engineers) owns property proofs and formal apps; the "
      "**methodology/infrastructure team** owns the regression system, "
      "coverage database and verification IP (VIP) licences.")

    h2("The verification plan")
    p("Everything starts from the **verification plan** (vPlan, testplan). "
      "It is written in parallel with the micro-architecture specification "
      "and reviewed by designers, architects and DV together. It turns "
      "each feature of the spec into measurable verification goals.")
    diagram([
        "  Specification            Verification plan                      Evidence",
        "  (features)               (what + how + done-criteria)           (metrics)",
        "  +--------------+        +-----------------------------------+   +------------------+",
        "  | F1 DMA burst |------->| F1.1 all burst lengths 1..256      |-->| covergroup bins  |",
        "  |   transfers  |        | F1.2 4KB boundary crossing         |-->| cover property   |",
        "  |              |        | F1.3 error response mid-burst      |-->| directed test ID |",
        "  | F2 low-power |------->| F2.1 entry/exit with traffic       |-->| emulation run    |",
        "  |   modes      |        | F2.2 isolation clamps correct      |-->| PA-sim + formal  |",
        "  | F3 register  |------->| F3.1 reset values, access policies |-->| UVM RAL test     |",
        "  |   map        |        | F3.2 connectivity to SoC map       |-->| formal conn. app |",
        "  +--------------+        +-----------------------------------+   +------------------+",
        "                                 |                                        |",
        "                                 +----> tracked in the vPlan tool <-------+",
        "                                        (% of items closed = progress)",
    ], "Figure 7.1 - From spec features to plan items to coverage evidence. "
       "Tools such as Verisium Manager, VC Execution Manager or in-house "
       "dashboards link each plan item to coverage.")
    bul(["**Feature list** extracted from the spec, including error and "
         "corner cases, configuration parameters, clock/reset/power "
         "scenarios and performance requirements.",
         "**Technique per feature**: constrained-random simulation, "
         "directed test, formal proof, emulation with software, or "
         "'covered by reuse' of pre-verified IP.",
         "**Level per feature**: block, subsystem or SoC - verify each "
         "thing at the lowest level where it is observable.",
         "**Done criteria**: coverage targets, number of clean regression "
         "cycles, bug-rate thresholds, reviewed waivers.",
         "**Resources and schedule**: VIP to buy, testbench components to "
         "build, emulation capacity, who owns what."])

    h2("Testbench tiers")
    p("A single monolithic SoC testbench would be too slow to reach "
      "corner cases in each block and too late to start. Verification is "
      "therefore layered, and components (agents, scoreboards, "
      "reference models, VIP) are built for reuse from one level to the "
      "next.")
    tbl(["Tier", "Scope and typical approach", "Speed / what it finds"],
        [["Unit", "One module or small function, often by the designer: "
          "directed tests, formal property checks, quick assertions",
          "Very fast; syntax-level and micro-architectural bugs"],
         ["Block (IP)", "Complete IP with UVM environment: agents per "
          "interface, reference model, scoreboard, functional coverage, "
          "constrained-random stimulus", "Fast (thousands of tests per "
          "night); most functional bugs, corner cases"],
         ["Subsystem", "Several IPs plus interconnect (e.g. CPU cluster + "
          "caches + coherent fabric); reuses block agents in passive mode",
          "Medium; interaction and performance bugs"],
         ["SoC / chip", "Full chip, often with real CPU running C tests "
          "or an embedded test program; checks connectivity, boot, "
          "clocks, resets, power modes, pin muxing, DFT modes",
          "Slow in simulation (Hz to kHz of chip clock); integration bugs; "
          "moves to emulation for software"],
         ["System", "Chip + firmware + OS on emulator or FPGA prototype, "
          "or silicon", "MHz; software-visible and performance bugs"]],
        [1.1, 4.4, 2.7], "Table 7.2 - Testbench tiers.", bold_first=True)

    h2("UVM in one page")
    p("The Universal Verification Methodology (UVM, standardised as IEEE "
      "1800.2) is the SystemVerilog class library used by nearly every "
      "ASIC DV team for block and subsystem environments. The companion "
      "SystemVerilog guide builds a complete UVM environment; the "
      "architecture to remember is:")
    diagram([
        "  uvm_test (selects config + sequences)",
        "   +-- env",
        "        +-- agent (active) ------------------+      +--------------------------+",
        "        |    sequencer -> driver --> [ interface ] --> |          DUT           |",
        "        |               monitor <--- [ interface ] <-- |                        |",
        "        +--------------------|-------------+      +--------------------------+",
        "        +-- agent (passive): monitor only  |            ^",
        "        +-- scoreboard <---------+---------+            |",
        "        |     (compares DUT output with reference model predictions)",
        "        +-- coverage collector (covergroups fed by monitors)",
        "        +-- register model (RAL) - front-door / back-door register access",
    ], "Figure 7.2 - The UVM environment structure. Agents are reused "
       "from block to SoC level; sequences are layered to build scenarios.")
    box("tip", "When UVM is overkill",
        ["For small blocks, a SystemVerilog testbench with a task-based "
         "driver, a reference model function and a few covergroups is "
         "faster to write and easier to debug. For many control blocks, "
         "formal property verification replaces most simulation. Use UVM "
         "where reuse and scale pay off: standard interfaces, complex "
         "protocols, subsystem integration."])

    h2("Constrained-random stimulus and functional coverage: a real run")
    p("Constrained-random verification generates legal but random "
      "stimulus, checks every result against a reference model, and "
      "measures **functional coverage** - have we exercised the "
      "scenarios listed in the plan? The small example below captures "
      "the whole loop. The DUT is a signed 8-bit saturating add/subtract "
      "unit. A buggy variant computes `a - b` as `a + (-b)` in 8 bits - "
      "wrong exactly when b = -128, because -(-128) overflows back to "
      "-128. This is the kind of bug that random testing hits only with "
      "probability 1/512 per transaction.")
    code([
        "// satalu.v - signed 8-bit saturating add/subtract (DUT)",
        "module satalu (input clk, input op,              // op: 0 = add, 1 = sub",
        "               input signed [7:0] a, b, output reg signed [7:0] y, output reg sat);",
        "`ifdef BUG",
        "  wire signed [7:0] bn = op ? -b : b;           // BUG: -(-128) overflows to -128",
        "  wire signed [8:0] s  = a + bn;",
        "`else",
        "  wire signed [8:0] s  = op ? a - b : a + b;    // 9-bit exact result",
        "`endif",
        "  always @(posedge clk) begin",
        "    sat <= (s > 127) || (s < -128);",
        "    y   <= (s > 127) ? 8'sd127 : (s < -128) ? -8'sd128 : s[7:0];",
        "  end",
        "endmodule",
    ], "The DUT, with the bug selectable by a define.")
    code([
        "// tb.sv - self-checking constrained-random testbench with functional coverage",
        "module tb;",
        "  reg clk = 0; always #5 clk = ~clk;",
        "  reg op; reg signed [7:0] a, b; wire signed [7:0] y; wire sat;",
        "  satalu dut (.clk(clk), .op(op), .a(a), .b(b), .y(y), .sat(sat));",
        "  integer seed, seed0, n, i, bias, errs = 0, exp; integer cov [0:13];  // 14 coverage bins",
        "  function signed [7:0] pick(input integer r);             // corner-biased operand",
        "    reg signed [7:0] c [0:4];",
        "    begin c[0] = -128; c[1] = -1; c[2] = 0; c[3] = 1; c[4] = 127;",
        "      pick = (bias && r % 4 == 0) ? c[($unsigned($random(seed))) % 5] : $random(seed); end",
        "  endfunction",
        "  initial begin",
        "    if (!$value$plusargs(\"seed=%d\", seed)) seed = 1;",
        "    if (!$value$plusargs(\"n=%d\", n)) n = 200;",
        "    seed0 = seed;",
        "    if (!$value$plusargs(\"bias=%d\", bias)) bias = 1;",
        "    for (i = 0; i < 14; i = i + 1) cov[i] = 0;",
        "    for (i = 0; i < n; i = i + 1) begin",
        "      op = $random(seed); a = pick($random(seed)); b = pick($random(seed));",
        "      @(posedge clk); #1;",
        "      exp = op ? a - b : a + b;                          // reference model",
        "      exp = (exp > 127) ? 127 : (exp < -128) ? -128 : exp;",
        "      if (y !== exp[7:0] || sat !== (op ? (a-b > 127 || a-b < -128)",
        "                                        : (a+b > 127 || a+b < -128))) begin",
        "        errs = errs + 1;",
        "        if (errs <= 2) $display(\"ERROR seed=%0d op=%0d a=%0d b=%0d y=%0d exp=%0d\",",
        "                                seed0, op, a, b, y, exp);",
        "      end",
        "      cov[op*3 + (exp == 127 && sat ? 1 : exp == -128 && sat ? 2 : 0)]++;  // 0-5",
        "      cov[6 + (a == -128 ? 0 : a == 127 ? 1 : a == 0 ? 2 : 3)]++;         // 6-9",
        "      if (b == -128) cov[10]++;  if (b == 127) cov[11]++;",
        "      if (op && b == -128) cov[12]++;  if (y == 0) cov[13]++;",
        "    end",
        "    $write(\"RESULT seed=%0d n=%0d errors=%0d bins=\", seed0, n, errs);",
        "    for (i = 0; i < 14; i = i + 1) $write(\"%0d\", cov[i] > 0);",
        "    $display(\"\"); $finish;",
        "  end",
        "endmodule",
    ], "A compact self-checking testbench: random stimulus with an optional "
       "25% bias towards corner values, a reference model, a checker and "
       "14 hand-rolled coverage bins (a covergroup in a real SV "
       "environment).")
    code([
        "# regress.py - run a seed regression, merge coverage, report closure and failures",
        "import subprocess, re",
        "NAMES = [\"add/none\", \"add/+sat\", \"add/-sat\", \"sub/none\", \"sub/+sat\", \"sub/-sat\",",
        "         \"a=-128\", \"a=127\", \"a=0\", \"a=other\", \"b=-128\", \"b=127\", \"sub&b=-128\", \"y=0\"]",
        "def regress(build, bias, seeds=20, n=40):",
        "    merged, fails = [0] * len(NAMES), 0",
        "    print(\"== %s, corner bias=%d, %d seeds x %d txns ==\" % (build, bias, seeds, n))",
        "    for seed in range(1, seeds + 1):",
        "        r = subprocess.run([\"vvp\", \"-n\", build, \"+seed=%d\" % seed, \"+n=%d\" % n,",
        "                            \"+bias=%d\" % bias], capture_output=True, text=True).stdout",
        "        m = re.search(r\"errors=(\\d+) bins=([01]+)\", r)",
        "        merged = [x | int(c) for x, c in zip(merged, m.group(2))]",
        "        fails += int(m.group(1)) > 0",
        "        if seed in (1, 2, 5, 10, 20):",
        "            print(\"  %2d seeds: coverage %2d/%d (%5.1f%%)  failing seeds: %d\"",
        "                  % (seed, sum(merged), len(NAMES), 100.0 * sum(merged) / len(NAMES), fails))",
        "    print(\"  holes: %s\\n\" % ([k for k, h in zip(NAMES, merged) if not h] or \"none\"))",
        "regress(\"sim_ok\", 1); regress(\"sim_bug\", 1); regress(\"sim_bug\", 0)",
    ], "A miniature regression manager: runs seeds, merges coverage across "
       "runs (union of bins), counts failing seeds and lists holes.")
    out([
        "$ iverilog -g2012 -Wall -o sim_ok satalu.v tb.sv",
        "$ iverilog -g2012 -DBUG -o sim_bug satalu.v tb.sv",
        "$ python3 regress.py",
        "== sim_ok, corner bias=1, 20 seeds x 40 txns ==",
        "   1 seeds: coverage 11/14 ( 78.6%)  failing seeds: 0",
        "   2 seeds: coverage 14/14 (100.0%)  failing seeds: 0",
        "   5 seeds: coverage 14/14 (100.0%)  failing seeds: 0",
        "  10 seeds: coverage 14/14 (100.0%)  failing seeds: 0",
        "  20 seeds: coverage 14/14 (100.0%)  failing seeds: 0",
        "  holes: none",
        "",
        "== sim_bug, corner bias=1, 20 seeds x 40 txns ==",
        "   1 seeds: coverage 11/14 ( 78.6%)  failing seeds: 0",
        "   2 seeds: coverage 14/14 (100.0%)  failing seeds: 1",
        "   5 seeds: coverage 14/14 (100.0%)  failing seeds: 4",
        "  10 seeds: coverage 14/14 (100.0%)  failing seeds: 8",
        "  20 seeds: coverage 14/14 (100.0%)  failing seeds: 15",
        "  holes: none",
        "",
        "== sim_bug, corner bias=0, 20 seeds x 40 txns ==",
        "   1 seeds: coverage  8/14 ( 57.1%)  failing seeds: 0",
        "   2 seeds: coverage  9/14 ( 64.3%)  failing seeds: 0",
        "   5 seeds: coverage 11/14 ( 78.6%)  failing seeds: 0",
        "  10 seeds: coverage 11/14 ( 78.6%)  failing seeds: 0",
        "  20 seeds: coverage 13/14 ( 92.9%)  failing seeds: 0",
        "  holes: ['sub&b=-128']",
        "",
        "$ vvp -n sim_bug +seed=3 +n=40",
        "ERROR seed=3 op=1 a=77 b=-128 y=-51 exp=127",
        "RESULT seed=3 n=40 errors=1 bins=11111110111110",
        "tb.sv:36: $finish called at 396 (1s)",
    ], "Real Icarus Verilog 12 runs driven by the Python regression script.")
    p("The three regressions tell the whole story of coverage-driven "
      "verification:")
    bul(["With corner bias, the correct DUT reaches **100% functional "
         "coverage after 2 seeds** and never fails - but that alone does not "
         "prove anything: coverage only says the scenarios were exercised.",
         "The same biased stimulus on the buggy DUT exposes the bug in 15 "
         "of 20 seeds. The checker (reference model + compare) detects the "
         "failure; the coverage model told us the triggering scenario "
         "(`sub&b=-128`) was reached.",
         "With **pure random** stimulus the buggy DUT **passes every test** "
         "- 800 transactions, zero failures. A team that only tracked the "
         "pass rate would sign off a broken design. The coverage report "
         "shows exactly one hole: the scenario that contains the bug. "
         "**Pass rate measures the DUT; coverage measures the "
         "testbench.** You need both."])
    box("key", "The two questions of verification",
        ["**Did we check?** - checkers, scoreboards and assertions must "
         "detect every wrong behaviour that is stimulated. A test with no "
         "checker that 'passes' is worthless.",
         "**Did we stimulate?** - coverage (code and functional) must "
         "show that every planned scenario was actually exercised. A "
         "coverage hole is a place where bugs can hide."])

    h2("Formal verification")
    p("Simulation checks the behaviours that the stimulus happens to "
      "produce. **Formal verification** proves properties for **all** "
      "possible input sequences, using SAT/BDD-based model checking. It "
      "has moved from a niche technique to a standard part of the DV "
      "plan, in two forms: **formal property verification (FPV)** on "
      "design-specific assertions, and push-button **formal apps**.")
    code([
        "// Example SVA properties for an arbiter, checked by a formal tool",
        "a_onehot:   assert property (@(posedge clk) disable iff (!rst_n) $onehot0(gnt));",
        "a_no_gnt:   assert property (@(posedge clk) disable iff (!rst_n)",
        "                             (gnt & ~req) == '0);            // only grant requesters",
        "a_fair:     assert property (@(posedge clk) disable iff (!rst_n)",
        "                             req[0] |-> ##[0:3] gnt[0]);      // bounded latency",
        "m_req_hold: assume property (@(posedge clk) req[1] && !gnt[1] |=> req[1]);  // env",
        "c_all:      cover  property (@(posedge clk) gnt == 4'b1000 ##1 gnt == 4'b0001);",
    ], "Assertions, assumptions and covers: the three kinds of formal "
       "properties.")
    tbl(["Result", "Meaning", "What to do"],
        [["Proven", "Holds for all reachable states from reset",
          "Check the assumptions are not over-constraining (covers must "
          "still be reachable)"],
         ["Failed (CEX)", "Tool shows a counter-example trace",
          "Debug like a simulation failure; fix RTL or the property"],
         ["Bounded proof (k cycles)", "No failure within k cycles of reset",
          "Acceptable if k exceeds the design's sequential depth; "
          "otherwise add abstractions or helper assertions"],
         ["Inconclusive", "State-space explosion", "Decompose, black-box "
          "datapaths, use abstractions or invariants"]],
        [1.6, 3.0, 3.6], "Table 7.3 - Interpreting formal results.",
        bold_first=True)
    tbl(["Formal app", "What it proves", "Typical use"],
        [["Connectivity", "Signal A at the top reaches pin B of an "
          "instance under condition C (pin-mux, test mux, interrupt "
          "wiring)", "SoC integration; replaces thousands of directed "
          "tests"],
         ["X-propagation", "X from uninitialised flops or X-sources cannot "
          "reach specified outputs", "Reset-value sign-off, low-power "
          "corruption"],
         ["Sequential equivalence (SEC)", "Two designs produce the same "
          "outputs even though their state encoding/pipelining differs",
          "Clock-gating insertion, retiming, power optimisations in RTL"],
         ["Register / CSR", "Access policies and reset values match the "
          "register spec (IP-XACT)", "Register map sign-off"],
         ["Unreachability / coverage", "Code coverage items that can never "
          "be hit", "Justify coverage waivers automatically"],
         ["Security / taint", "Secret data cannot reach insecure outputs",
          "Crypto keys, debug locks"]],
        [1.7, 3.6, 2.9], "Table 7.4 - Formal apps.", bold_first=True)
    box("expert", "INTERVIEW INSIGHT - where formal wins",
        ["Formal is strongest on **control logic with deep corner cases "
         "and narrow interfaces**: arbiters, FIFOs, credit counters, "
         "cache-coherence protocol controllers, interrupt controllers, "
         "clock-gating and power-control sequencers. It struggles with "
         "wide datapaths (multipliers, floating point) where the state "
         "space is huge - there, simulation plus specialised datapath "
         "equivalence tools are used. A strong answer names both the "
         "technique and the kind of logic it fits."])

    h2("Emulation and FPGA prototyping")
    p("A full SoC in an RTL simulator runs at roughly hertz to a few "
      "kilohertz of chip clock. Booting Linux takes billions of cycles - "
      "years in simulation. Two hardware-assisted platforms close the "
      "gap:")
    tbl(["Platform", "Typical speed", "Strengths", "Weaknesses"],
        [["RTL simulation", "~1 Hz - 10 kHz (SoC)", "Full visibility, "
          "4-state, fast compile, cheap per seat", "Too slow for software"],
         ["Emulation (Palladium, Veloce, ZeBu)", "~0.5 - 5 MHz",
          "Large capacity, fast compile (hours), good debug visibility, "
          "transaction-based testbenches, power estimation on real "
          "workloads", "Expensive, shared capacity"],
         ["FPGA prototype (HAPS, S2C, in-house boards)", "~5 - 100 MHz",
          "Runs real software and real I/O at near-system speed; "
          "can be shipped to software teams", "Long bring-up, partitioning "
          "across FPGAs, limited visibility, ASIC-only structures "
          "(memories, clock gating) need remodelling"]],
        [1.8, 1.4, 3.1, 2.5], "Table 7.5 - Verification platforms. Speeds "
                              "are orders of magnitude and depend strongly "
                              "on design size.", bold_first=True)
    p("Here the ASIC RTL rules of chapter 6 pay off again: a design with "
      "memories behind wrappers and clock gating behind ICG wrappers maps "
      "to an emulator or FPGA by swapping the wrapper implementation, "
      "without touching functional RTL.")

    h2("Hardware/software co-verification")
    p("Modern SoCs are defined as much by firmware as by RTL. Boot ROM "
      "code, power management firmware, drivers and the hardware "
      "abstraction layer must be verified **against the RTL before "
      "tapeout** - a boot ROM bug is a mask bug. Typical approaches:")
    bul(["**Virtual platforms** (SystemC/TLM models) let software start "
         "months before RTL exists; they must be kept consistent with the "
         "register map (generated from the same IP-XACT/SystemRDL "
         "source).",
         "**Hybrid emulation**: CPU subsystem as a fast model, the rest as "
         "RTL in the emulator.",
         "**C tests on the SoC testbench**: the real CPU RTL executes "
         "compiled test code, with a small mailbox to the SV testbench "
         "for pass/fail and stimulus coordination.",
         "**Boot ROM sign-off**: every boot path (fuse settings, boot "
         "devices, secure boot, recovery modes) is exercised on RTL "
         "and gate-level netlist."])

    h2("Coverage closure")
    tbl(["Coverage type", "Measures", "Pitfall"],
        [["Line / statement", "Each executable line was executed",
          "100% line coverage says nothing about values"],
         ["Branch", "Each if/case branch taken", "Default branches of full "
          "cases are unreachable - waive with reason"],
         ["Condition / expression", "Each sub-condition independently "
          "affected the outcome (focused expression coverage)",
          "Grows quickly; needs targeted tests"],
         ["Toggle", "Each bit toggled 0->1 and 1->0",
          "Useful for connectivity and tie-offs at SoC level"],
         ["FSM", "States and transitions visited", "Illegal states must be "
          "unreachable, not merely unvisited"],
         ["Functional (covergroups)", "Planned scenarios, values and "
          "crosses from the vPlan", "Only as good as the plan: cannot find "
          "what nobody thought of"],
         ["Assertion / cover property", "Temporal scenarios happened; "
          "assertions were active and not vacuous",
          "Vacuous passes (antecedent never true)"]],
        [1.8, 3.4, 3.0], "Table 7.6 - Code and functional coverage "
                         "types.", bold_first=True)
    p("Closure is iterative: run regressions, merge coverage from all "
      "tests and seeds, analyse holes, then either **write a targeted "
      "test or constraint**, **prove the hole unreachable** (formal "
      "unreachability) and waive it, or **file a bug** if the hole reveals "
      "dead or broken logic. Typical sign-off targets are 100% of "
      "functional coverage items in the plan (with reviewed waivers) and "
      "very high code coverage (often 95-100% after justified exclusions), "
      "but the exact targets are a project decision.")

    h2("Bug tracking and trend curves")
    p("Every failure goes into a bug tracker (JIRA, Bugzilla, in-house) "
      "with severity, owner, block and the test and seed that reproduce "
      "it. Project management watches two curves: the **cumulative bugs "
      "found** and the **open bug count**. A healthy project shows an "
      "S-shaped cumulative curve that flattens as the design matures.")
    diagram([
        "  bugs",
        "   ^                                   cumulative found",
        "   |                           . . . . o o o o o o o o o o   <- flattening: design",
        "   |                    . o o o                                 is converging",
        "   |               o o o",
        "   |            o o",
        "   |          o         x x",
        "   |        o         x     x          open bugs",
        "   |      o         x         x x",
        "   |    o         x               x x x                       ",
        "   |  o       x x                       x x x . . . _ _ _ _   <- near zero at sign-off",
        "   +--o---x-x-------------------------------------------------------------> weeks",
        "      RTL start   feature complete    code freeze          tapeout",
    ], "Figure 7.3 - Bug trend curves (schematic). A late spike in found bugs "
       "after 'feature complete' is a warning that verification started "
       "late or the design is still changing.")
    bul(["**Bug rate per week** should trend down over the last few weeks "
         "before sign-off; many teams require no new high-severity bugs "
         "for N consecutive regression cycles.",
         "**Bugs per block** point to risky IP - a block with many late "
         "bugs deserves a formal review or extra testing.",
         "**Root-cause categories** (spec ambiguity, RTL coding, "
         "integration, testbench bug) show where the process leaks."])

    h2("Regression management")
    bul(["**Tiers of regression**: a smoke/sanity set on every commit "
         "(minutes), a nightly regression (thousands of tests, random "
         "seeds), a weekly full regression including gate-level and "
         "power-aware runs.",
         "**Seed management**: failing seeds are saved and replayed; "
         "random stability (the same seed reproduces the same stimulus "
         "after unrelated code changes) matters for debug.",
         "**Triage**: failures are auto-bucketed by error signature so "
         "that one RTL bug that fails 500 tests is one ticket.",
         "**Compute farm**: regressions run on hundreds to thousands of "
         "cores under a job scheduler (LSF, Slurm, cloud); licences are "
         "often the real bottleneck.",
         "**Metrics dashboard**: pass rate, coverage trend, runtime, "
         "flaky tests - reviewed weekly by the DV lead."])

    h2("Gate-level simulation")
    p("After synthesis and after place-and-route, the netlist is "
      "simulated again. Formal equivalence (LEC, chapter 8) already "
      "proves the netlist implements the RTL, so gate-level simulation "
      "(GLS) is **not** for functional coverage. It catches what LEC and "
      "STA cannot:")
    tbl(["GLS flavour", "What it catches"],
        [["Zero-delay (unit-delay) netlist", "Reset and initialisation "
          "problems hidden by RTL X-optimism (an `if (x)` in RTL takes "
          "the else-branch; gates propagate X), missing resets, "
          "power-up sequences, scan/DFT mode functionality, netlist "
          "connectivity to macros and pads"],
         ["SDF back-annotated (min/max corners)", "Timing-check "
          "violations on asynchronous interfaces, reset release, "
          "synchronisers, un-timed paths with wrong exceptions, "
          "glitches on clock muxes; validates the SDC exceptions"],
         ["Scan / ATPG pattern simulation", "The test patterns work on the "
          "real netlist with timing (chapter 10) before they go to the "
          "tester"]],
        [2.3, 6.0], "Table 7.7 - Gate-level simulation flavours.",
        bold_first=True)
    box("warn", "PITFALL - 'GLS passes' with timing checks disabled",
        ["SDF simulation with `+notimingchecks`, or with every "
         "synchroniser's first flop excluded from X-generation carelessly, "
         "hides the problems GLS exists to find. The correct approach is "
         "to disable timing checks only on the **first stage of known "
         "synchronisers** (by instance list generated from the CDC "
         "report) and keep them everywhere else."])

    h2("Power-aware simulation")
    p("When a design has switchable power domains (chapter 11), the "
      "simulator reads the UPF and models what RTL alone cannot: when a "
      "domain is off, its registers and outputs are **corrupted** (driven "
      "to X); isolation cells clamp outputs to their specified value; "
      "retention registers save and restore state; level shifters and "
      "supply states are checked. Power-aware simulation finds missing "
      "isolation, wrong isolation enables, sequencing errors in the "
      "power controller and software that accesses a switched-off block. "
      "It runs at RTL (with the UPF) and at gate level (with the "
      "implemented power network and cells).")

    h2("Verification sign-off")
    checklist("Functional verification sign-off checklist (tapeout gate)", [
        "Verification plan reviewed and 100% of plan items closed, "
        "deferred with sign-off from architecture, or covered by reuse.",
        "Functional coverage targets met; all holes analysed; waivers "
        "reviewed and signed.",
        "Code coverage (line, branch, condition, toggle, FSM) at target "
        "with justified exclusions, preferably backed by formal "
        "unreachability.",
        "Formal: all planned properties proven or bounded beyond the "
        "sequential depth; connectivity and X-prop apps clean.",
        "Regression: N consecutive clean nightly regressions on the final "
        "RTL tag; no open severity-1/2 bugs; bug rate trend flat.",
        "SoC tests: boot paths, clocks, resets, power modes, pin-mux, "
        "DFT and debug modes exercised.",
        "Software: boot ROM and key firmware run on emulation/prototype "
        "on the final RTL.",
        "GLS: zero-delay and SDF (min/max) runs clean; scan patterns "
        "simulated.",
        "Power-aware simulation clean for all power-state transitions.",
        "LEC RTL-to-netlist clean (chapter 8), ECO changes re-verified.",
    ])

    h2("Summary")
    bul(["Verification is typically the largest front-end effort; DV "
         "engineers often outnumber designers.",
         "The verification plan maps every spec feature to a technique, a "
         "level and measurable done-criteria.",
         "Testbenches are tiered unit -> block -> subsystem -> SoC -> "
         "system, with UVM components reused across tiers.",
         "Our Icarus run showed a buggy DUT passing 100% of purely random "
         "tests while coverage showed the one hole containing the bug: "
         "pass rate measures the DUT, coverage measures the testbench.",
         "Formal proves properties exhaustively and its apps "
         "(connectivity, X-prop, SEC, unreachability) replace large "
         "amounts of directed simulation.",
         "Emulation and FPGA prototypes provide the MHz speed needed for "
         "software; GLS and power-aware simulation catch what RTL "
         "simulation, LEC and STA cannot.",
         "Sign-off is an evidence-based checklist: plan closure, coverage, "
         "formal results, regression and bug trends, software, GLS and "
         "power-aware results."])

    h2("Exercises")
    bul(["Write verification plan entries (feature, technique, level, "
         "done-criteria) for an asynchronous FIFO with almost-full and "
         "almost-empty flags.",
         "In the saturating-ALU example, compute the probability that 800 "
         "purely random transactions contain at least one subtraction "
         "with b = -128. Why did our 20-seed run miss it?",
         "Give two bugs that 100% line and branch coverage cannot find, "
         "and the functional coverage or assertion that would.",
         "Your arbiter proof returns 'bounded proof, k = 25'. What do you "
         "need to know to decide whether this is sufficient?",
         "Explain why gate-level simulation still exists when LEC proves "
         "RTL and netlist equivalent. Give three bug classes found only "
         "in GLS.",
         "A project has 20 open bugs one week before tapeout and the "
         "weekly find rate is 8. What would you recommend, and what data "
         "would you ask for?"], ordered=True)


# =============================================================================
#                    CHAPTER 8 - LOGIC SYNTHESIS IN DEPTH
# =============================================================================
def _ch8():
    chapter("Logic Synthesis in Depth")
    p("Logic synthesis translates RTL into a gate-level netlist of "
      "standard cells that meets timing, area, power and design-rule "
      "constraints. The companion RTL Design guide explains what each "
      "RTL idiom becomes; this chapter opens the tool itself: the "
      "steps of a production flow, the algorithms behind mapping and "
      "optimisation, how datapaths are synthesised, why wire-load "
      "models failed and physical-aware synthesis replaced them, how to "
      "read QoR reports and warnings, and how the result is proven "
      "equivalent to the RTL.")
    p("Synthesis is owned by the **synthesis / implementation engineer** "
      "(in some companies the RTL designer runs it for blocks, and a "
      "central team runs the full chip). Inputs: RTL + filelist, SDC, "
      "UPF, Liberty (.lib/.db) for every corner used, physical data "
      "(LEF/tech file, floorplan DEF) for physical-aware runs, and the "
      "DFT specification. Outputs: netlist, updated SDC, UPF, scan "
      "definition (SCANDEF), reports and a LEC setup. All numbers in "
      "this chapter's runs are from **Yosys 0.33 with ABC** against the "
      "real **SKY130 sky130_fd_sc_hd tt_025C_1v80** Liberty file.")

    h2("The production synthesis flow")
    diagram([
        "  +-----------------+  +-------------+  +-----------------+  +-------------------+",
        "  | RTL + filelist  |  | SDC         |  | Liberty (all    |  | LEF / tech / DEF  |",
        "  | defines, params |  | (+ UPF)     |  | used corners)   |  | (physical-aware)  |",
        "  +--------+--------+  +------+------+  +--------+--------+  +---------+---------+",
        "           v                  |                  |                     |",
        "   1 analyze (parse)          |                  |                     |",
        "   2 elaborate (generic/GTECH netlist, inferred flops, operators)       |",
        "   3 link (resolve cells/macros against libraries)                     |",
        "           |<-----------------+ 4 read constraints, check_design/timing|",
        "   5 compile: generic opt -> technology mapping -> timing/area/power ---+",
        "      opt (sizing, buffering, restructuring, Vt swap, clock gating)",
        "   6 DFT: scan replacement + insert_dft (chains, compression, OCC hooks)",
        "   7 incremental compile (fix what DFT and physical estimates broke)",
        "   8 reports: QoR, timing, area, power, constraints, check_design",
        "   9 write: netlist (.v), SDC, UPF, SCANDEF, SAIF mapping, LEC guide file",
    ], "Figure 8.1 - Steps of a production synthesis flow.")
    code([
        "# Illustrative Design Compiler (Tcl) flow - commands are standard, paths generic",
        "set_app_var target_library \"stdcell_ss_0p72v_125c.db\"    ;# mapping + timing",
        "set_app_var link_library   \"* $target_library sram_macros.db\"",
        "analyze   -format sverilog -vcs \"-f rtl.f\"",
        "elaborate soc_top",
        "link",
        "read_sdc  constraints/soc_top.sdc",
        "load_upf  soc_top.upf",
        "check_design ; check_timing",
        "set_dont_use [get_lib_cells */*_X0P5*]             ;# no weak cells",
        "compile_ultra -gate_clock -retime -spg             ;# topographical / physical guide",
        "insert_dft",
        "compile_ultra -incremental -scan",
        "report_qor > rpt/qor.rpt ; report_timing -max_paths 50 > rpt/timing.rpt",
        "write -format verilog -hierarchy -output out/soc_top.vg",
        "write_sdc out/soc_top.sdc ; write_scan_def -output out/soc_top.scandef",
    ], "A typical Design Compiler script. The Cadence Genus equivalent is "
       "read_hdl / elaborate / read_sdc / syn_generic / syn_map / syn_opt "
       "/ write_hdl; Yosys uses read_verilog / synth / dfflibmap / abc.")

    h2("Elaboration and the generic (GTECH) netlist")
    p("Elaboration builds a technology-independent netlist. Operators such "
      "as `+`, `*` and `<` become **high-level operator cells** (Synopsys "
      "keeps them as DesignWare/GTECH operators, Yosys as `$add`, `$alu`, "
      "`$mul`); flops become generic sequential cells with reset and "
      "enable attributes; control logic becomes generic Boolean gates. "
      "Yosys lets us watch the 32-bit adder `assign s = a + b;` pass "
      "through these stages:")
    out([
        "# after the 'coarse' stage (operators still abstract)",
        "   Number of cells:                  1",
        "     $alu                            1",
        "# after the 'fine' stage (techmap to generic gates, before library mapping)",
        "   Number of cells:                235",
        "     $_ANDNOT_                      53",
        "     $_AND_                         11",
        "     $_NAND_                        21",
        "     $_NOR_                         34",
        "     $_ORNOT_                       11",
        "     $_OR_                          42",
        "     $_XNOR_                        27",
        "     $_XOR_                         36",
    ], "Real Yosys stat output for add32 at two stages of synth. The "
       "generic gate library ($_AND_, $_XOR_...) plays the role of GTECH.")
    p("Keeping arithmetic abstract as long as possible is what allows "
      "**datapath synthesis** (section 8.6) to choose an architecture per "
      "operator later, with timing information. Premature flattening into "
      "gates loses that choice.")

    h2("Boolean optimisation and technology mapping")
    p("Most modern synthesis engines represent combinational logic as an "
      "**And-Inverter Graph (AIG)**: a DAG of 2-input AND nodes with "
      "optional inversion on edges. The AIG is a compact, canonical-ish "
      "form on which fast rewriting algorithms run:")
    bul(["**Structural hashing** merges identical nodes; **constant "
         "propagation** and **SAT sweeping / fraiging** merge nodes proven "
         "functionally equivalent.",
         "**Rewriting and refactoring** replace small sub-graphs (for "
         "example 4-input cuts) by smaller pre-computed equivalents; "
         "**balancing** reduces logic depth.",
         "**Don't-care optimisation** uses satisfiability and observability "
         "don't-cares to simplify logic whose value does not matter.",
         "**Technology mapping** covers the optimised AIG with library "
         "cells. The classic formulation is tree covering by dynamic "
         "programming (DAGON, 1987); modern mappers enumerate **cuts** "
         "(small sub-graphs with k inputs), match each cut's Boolean "
         "function against library cells, and pick the cover minimising "
         "delay, then recover area on non-critical paths."])
    diagram([
        "   AIG fragment                         Library cells matched to cuts",
        "",
        "      a   b    c   d                     cut {a,b,c,d}: f = !((a&b)|(c&d))",
        "       \\ /      \\ /                         -> a22oi_1 (one cell)         area 7.5 um^2",
        "      AND1     AND2                        or  nand2 + nand2 + and2      area 13.8 um^2",
        "        o\\     /o      (o = inverted edge)",
        "          AND3                           the mapper chooses per cut, per delay target",
        "            o-> f",
    ], "Figure 8.2 - Cut-based mapping: the same AIG sub-graph can be covered "
       "by one complex cell (AOI) or several simple ones. (Areas: SKY130 "
       "a22oi_1 = 7.51 um^{2}; nand2_1 = 3.75 um^{2}; and2_1 = 6.26 um^{2}.)")
    p("ABC, the open-source engine from UC Berkeley that Yosys uses, "
      "exposes these steps as commands (`strash`, `dc2`, `dch`, `map`, "
      "`&nf`, `buffer`, `upsize`, `dnsize`, `stime`). Commercial engines "
      "use the same ideas with far larger libraries of transformations, "
      "better timing models and tight coupling to placement.")

    h2("Timing-driven optimisation")
    p("After mapping, the tool times the netlist with its internal STA "
      "engine (the same NLDM delay calculation as chapter 9) and "
      "repeatedly applies transformations to the worst paths:")
    tbl(["Transformation", "What it does", "Cost"],
        [["Gate sizing", "Swap a cell for a stronger/weaker drive of the "
          "same function (nand2_1 -> nand2_4); upsizing speeds the driven "
          "net but loads the previous stage", "Area, leakage, input cap"],
         ["Buffering / fanout splitting", "Insert buffers or build a buffer "
          "tree on high-fanout or long nets; isolate critical sinks from "
          "non-critical load", "Area, power"],
         ["Restructuring", "Re-express logic so late-arriving signals pass "
          "through fewer levels (e.g. Shannon expansion on a late input, "
          "re-balancing a chain)", "Area"],
         ["Pin swapping", "Connect the latest signal to the fastest input "
          "pin of a cell (pins of a NAND stack are not equal)", "None"],
         ["Multi-Vt assignment", "Use low-Vt (fast, leaky) cells only on "
          "critical paths, high-Vt (slow, low leakage) elsewhere",
          "Leakage (roughly exponential in Vth)"],
         ["Logic duplication", "Duplicate a driver so each copy drives "
          "fewer, better-placed sinks", "Area"],
         ["Area recovery", "Downsize and re-map cells on paths with "
          "positive slack", "Timing margin"]],
        [1.7, 4.6, 1.6], "Table 8.1 - Timing-driven optimisation moves.",
        bold_first=True)
    box("intuit", "Why low-Vt everywhere is not the answer",
        ["Subthreshold leakage grows roughly exponentially as Vth drops "
         "(about a decade per 60-100 mV of Vth at room temperature, "
         "chapter 2), and grows further with temperature. A typical "
         "multi-Vt flow starts with the high- or standard-Vt library and "
         "allows low-Vt swaps only where the setup slack is negative, "
         "often with a budget such as 'no more than a few percent of "
         "cells in ulvt'. Leakage is then reported per Vt class."])

    h2("A real run: the area-delay trade-off of a 32-bit adder")
    p("To see timing-driven mapping at work, we synthesised two 32-bit "
      "adders against the SKY130 library with a sweep of ABC delay "
      "targets (`abc -D <ps>`). Both compute the same function: `add32` "
      "is `assign s = a + b;` (Yosys decomposes `$alu` into its default "
      "carry-lookahead structure), and `ks32` is a hand-written "
      "**Kogge-Stone** parallel-prefix adder.")
    code([
        "// 32-bit Kogge-Stone parallel-prefix adder (structural generate/propagate tree)",
        "module ks32 (input [31:0] a, b, output [32:0] s);",
        "  wire [31:0] g0 = a & b, p0 = a ^ b;",
        "  wire [31:0] g [0:5];",
        "  wire [31:0] p [0:5];",
        "  assign g[0] = g0; assign p[0] = p0;",
        "  genvar l, i;",
        "  generate for (l = 0; l < 5; l = l + 1) begin : lvl",
        "    for (i = 0; i < 32; i = i + 1) begin : bit",
        "      if (i >= (1 << l)) begin : op",
        "        assign g[l+1][i] = g[l][i] | (p[l][i] & g[l][i-(1<<l)]);",
        "        assign p[l+1][i] = p[l][i] & p[l][i-(1<<l)];",
        "      end else begin : pass",
        "        assign g[l+1][i] = g[l][i];",
        "        assign p[l+1][i] = p[l][i];",
        "      end",
        "    end",
        "  end endgenerate",
        "  assign s[0]    = p0[0];",
        "  assign s[31:1] = p0[31:1] ^ g[5][30:0];",
        "  assign s[32]   = g[5][31];",
        "endmodule",
    ], "ks32.v: log2(32) = 5 prefix levels; every level has up to 32 "
       "black cells, which gives minimum depth at the price of area and "
       "wiring.")
    code([
        "# sweep.sh (core): one Yosys run per delay target D",
        "read_verilog $f",
        "synth -top $t -flatten",
        "dfflibmap -liberty hd_tt_du.lib",
        "abc -fast -liberty hd_tt_du.lib -constr constr.txt -D $D   # -D omitted for 'none'",
        "opt_clean",
        "stat -liberty hd_tt_du.lib",
        "",
        "# constr.txt - driving cell and output load seen by ABC's timer",
        "set_driving_cell sky130_fd_sc_hd__inv_2",
        "set_load 0.01",
    ], "Delay-target sweep. With -constr, the ABC script is 'strash; dretime; "
       "map {D}; buffer; upsize {D}; dnsize {D}; stime -p', i.e. mapping, "
       "buffering and gate sizing towards the target D.")
    out([
        "add32  none     cells=238   area_um2=1326.272000 abc_delay_ps=1460.14",
        "add32  4000     cells=233   area_um2=1204.905600 abc_delay_ps=2246.78",
        "add32  2000     cells=232   area_um2=1212.412800 abc_delay_ps=1962.67",
        "add32  1800     cells=230   area_um2=1213.664000 abc_delay_ps=1750.37",
        "add32  1600     cells=223   area_um2=1251.200000 abc_delay_ps=1591.88",
        "add32  1400     cells=229   area_um2=1296.243200 abc_delay_ps=1558.49",
        "add32  1200     cells=238   area_um2=1326.272000 abc_delay_ps=1460.14",
        "add32  1000     cells=238   area_um2=1326.272000 abc_delay_ps=1460.14",
        "add32  900      cells=238   area_um2=1326.272000 abc_delay_ps=1460.14",
        "ks32   none     cells=548   area_um2=3178.048000 abc_delay_ps=1014.37",
        "ks32   4000     cells=422   area_um2=2019.436800 abc_delay_ps=1329.48",
        "ks32   2000     cells=422   area_um2=2019.436800 abc_delay_ps=1329.48",
        "ks32   1800     cells=422   area_um2=2019.436800 abc_delay_ps=1329.48",
        "ks32   1600     cells=423   area_um2=2026.944000 abc_delay_ps=1409.97",
        "ks32   1400     cells=397   area_um2=1948.118400 abc_delay_ps=1289.69",
        "ks32   1200     cells=387   area_um2=2036.953600 abc_delay_ps=1192.82",
        "ks32   1000     cells=468   area_um2=2418.569600 abc_delay_ps=1061.02",
        "ks32   900      cells=548   area_um2=3178.048000 abc_delay_ps=1014.37",
    ], "Real results: cell count and stat -liberty area (um^{2}) from Yosys, "
       "delay (ps) from ABC's 'stime' timer with SKY130 NLDM tables.")
    diagram([
        "  area (um^2)",
        " 3300 |",
        "      |     k",
        "      |",
        " 2860 |",
        "      |",
        "      |",
        " 2420 |",
        "      |       k",
        "      |",
        " 1980 |             k     k  k",
        "      |                 k",
        "      |",
        " 1540 |",
        "      |",
        "      |                         r   r r",
        " 1100 |                                      r        r            r",
        "      +----------------------------------------------------------------",
        "         1000     1200     1400     1600     1800     2000     2200   ABC delay (ps)",
    ], "Figure 8.3 - The same data plotted: r = add32 (a + b), k = ks32 "
       "(Kogge-Stone). Each architecture traces its own area-delay curve; "
       "the fastest point costs about 63% more area than the smallest "
       "Kogge-Stone point and about 2.6x the smallest add32 point.")
    p("What the numbers teach:")
    bul(["**Tight targets cost area.** For add32 the delay-optimal mapping "
         "(no target, or targets below what is reachable) gives 1460 ps "
         "at 1326 um^{2}; relaxing the target to 4000 ps lets the mapper "
         "recover area down to 1205 um^{2} at 2247 ps. That is the "
         "classic 'banana curve' every synthesis engineer knows.",
         "**Architecture beats optimisation.** No delay target made add32 "
         "faster than about 1.46 ns, while the Kogge-Stone structure "
         "reached 1.01 ns - at 2.4x the area. The mapper optimises "
         "locally around the structure it is given; choosing the adder "
         "architecture is a datapath synthesis decision (next section).",
         "**Heuristics are noisy.** The ks32 points at 1600 ps and 1400 ps "
         "are not monotonic: a tighter target produced a smaller netlist. "
         "Real tools show the same effect, which is why teams run several "
         "strategies and keep the best result, and why 1-2% QoR "
         "differences between runs are not significant.",
         "**Unconstrained is not 'smallest'.** ABC's default (no -D) aims "
         "for minimum delay. A production tool without a clock constraint "
         "behaves differently (it optimises area), which is one reason "
         "check_timing must report zero unconstrained endpoints."])
    out([
        "=== add32 ===  (D = 1600 ps)",
        "   Number of cells:                223",
        "     sky130_fd_sc_hd__a21boi_0       3",
        "     sky130_fd_sc_hd__a21oi_1       11",
        "     sky130_fd_sc_hd__and2_1         9",
        "     sky130_fd_sc_hd__inv_1         26",
        "     sky130_fd_sc_hd__nand2_1       40",
        "     sky130_fd_sc_hd__nor2_1        54",
        "     sky130_fd_sc_hd__o21ai_0        8",
        "     sky130_fd_sc_hd__o21ai_4        2",
        "     sky130_fd_sc_hd__xnor2_1       11",
        "     sky130_fd_sc_hd__xor2_1        27",
        "     ... (22 further cell types with 1-3 instances each)",
        "   Chip area for module '\\add32': 1251.200000",
        "ABC: ... Gates = 223 ... Area = 1251.20 ... Delay = 1591.88 ps",
    ], "Real stat -liberty excerpt: note the mix of drive strengths (_0, _1, "
       "_4) chosen by sizing, and the dominance of NAND/NOR/AOI/OAI - "
       "inverting CMOS cells are the fastest and smallest per function.")

    h2("Datapath synthesis")
    p("Arithmetic dominates the area of many blocks (DSP, ML "
      "accelerators, GPUs). Commercial tools therefore contain a "
      "dedicated **datapath synthesis** engine (Synopsys DesignWare "
      "Foundation / 'DW' components and datapath extraction; Cadence "
      "Genus datapath synthesis) which: extracts clusters of arithmetic "
      "(sums of products, comparators, shifters) from the RTL; merges "
      "them into a single **carry-save** tree so that only one "
      "carry-propagate adder is needed at the end; and picks each "
      "operator's architecture from a library of implementations "
      "according to the timing context.")
    tbl(["Structure", "Delay", "Area", "When chosen"],
        [["Ripple-carry adder", "O(n)", "O(n), smallest",
          "Non-critical, narrow adders"],
         ["Carry-lookahead / carry-select", "O(log n) / O(sqrt n)",
          "Moderate", "Medium widths, moderate timing"],
         ["Parallel prefix: Brent-Kung", "2 log2 n - 1 levels",
          "O(n), low fanout", "Area/power-aware fast adders"],
         ["Parallel prefix: Kogge-Stone", "log2 n levels",
          "O(n log n), many wires", "Fastest adders, when wiring allows"],
         ["Parallel prefix: Sklansky", "log2 n levels",
          "O(n/2 log n), high fanout", "Fast with buffering"],
         ["Array multiplier", "O(n)", "O(n^2)", "Rare in ASIC today"],
         ["Booth (radix-4) + Wallace/Dadda tree", "O(log n)",
          "O(n^2), fewer partial products", "Standard for fast multipliers"],
         ["Carry-save accumulation (MAC)", "one CPA per result",
          "Saves adders", "a*b + c, dot products, FIR filters"]],
        [2.6, 1.6, 2.2, 2.6], "Table 8.2 - Datapath architectures a "
                              "synthesis tool chooses from.",
        bold_first=True)
    p("A 16x16 signed multiply-accumulate with a 40-bit accumulator, "
      "synthesised the same way, shows how much a datapath costs and how "
      "strongly its area depends on the timing target:")
    code([
        "module mac16 (input clk, rst_n, clr, en, input signed [15:0] a, b,",
        "              output reg signed [39:0] acc);",
        "  always @(posedge clk or negedge rst_n)",
        "    if (!rst_n)   acc <= 40'sd0;",
        "    else if (clr) acc <= 40'sd0;",
        "    else if (en)  acc <= acc + a * b;",
        "endmodule",
    ], "mac16.v")
    out([
        "mac16  none     cells=3855  area_um2=21052.691200 abc_delay_ps=3731.33",
        "mac16  8000     cells=2410  area_um2=14776.672000 abc_delay_ps=5745.17",
        "mac16  6000     cells=2410  area_um2=14776.672000 abc_delay_ps=5745.17",
        "mac16  5000     cells=2404  area_um2=14869.260800 abc_delay_ps=4971.30",
        "mac16  4000     cells=2407  area_um2=15292.166400 abc_delay_ps=4242.06",
        "mac16  3500     cells=2882  area_um2=16605.926400 abc_delay_ps=3975.57",
        "mac16  3000     cells=3647  area_um2=19942.876800 abc_delay_ps=3740.92",
    ], "Real sweep for mac16 (40 dfrtp_1 flops included in every point; "
       "delay is the combinational register-to-register logic as seen by "
       "ABC).")
    p("Going from 5.75 ns to 3.73 ns (-35% delay) costs +42% area. Yosys "
      "has no Booth recoding or carry-save merging in this version, so "
      "these numbers are for a simple array-style multiplier followed by "
      "an adder; a commercial datapath engine would merge the "
      "accumulator into the partial-product tree and do considerably "
      "better. The lesson for the RTL designer: **write arithmetic as "
      "expressions** (`acc + a * b`) so the tool can merge it, rather "
      "than hand-instantiating adders, unless you need a specific "
      "architecture.")

    h2("Retiming, clock-gating insertion and sequential optimisations")
    h3("Retiming")
    p("**Retiming** moves registers across combinational logic without "
      "changing the cycle-level behaviour at the outputs, to balance "
      "stage delays. It is invaluable for deep arithmetic pipelines: "
      "write `result = f(x)` followed by N register stages, and let the "
      "tool distribute the registers inside f. Restrictions: registers "
      "with different reset/enable conditions, registers visible to "
      "software/debug, and registers crossing hierarchy or used by "
      "constraints usually cannot move; LEC then needs sequential "
      "equivalence checking or retiming-aware guidance.")
    diagram([
        "  before:  --[comb 6 ns]--[comb 2 ns]--|FF|--|FF|--     stage delays 8 ns, 0 ns",
        "  after :  --[comb 4 ns]--|FF|--[comb 4 ns]--|FF|--     stage delays 4 ns, 4 ns",
        "           (same latency, same function at the outputs, register count may change)",
    ], "Figure 8.4 - Retiming balances pipeline stages.")
    h3("Clock-gating insertion")
    p("With clock gating enabled (`compile_ultra -gate_clock` in DC, "
      "`lp_insert_clock_gating` in Genus), the tool looks for groups of "
      "flops that share an enable, removes the feedback multiplexers and "
      "inserts an ICG cell. Controls: minimum bit-width per gate (e.g. "
      "3 or 4), maximum fanout per ICG, the ICG cell to use, and whether "
      "the test-enable pin connects to scan-enable or test-mode. Timing "
      "of the enable path to the ICG (clock-gating setup check) is often "
      "critical because the ICG sits early in the clock tree.")
    h3("Other sequential optimisations")
    bul(["**Constant-flop removal**: flops that can never change (tied "
         "inputs) are removed - a frequent source of 'my register "
         "disappeared' questions and of LEC unmapped points.",
         "**Equivalent-flop merging**: two flops with identical inputs are "
         "merged unless marked `dont_touch` (redundant flops used for "
         "fanout or safety must be protected).",
         "**FSM re-encoding**: extracted FSMs may be re-encoded (one-hot, "
         "Gray); keep it off for safety-critical or observed state "
         "registers.",
         "**Scan-flop replacement**: in DFT-aware compile, flops are "
         "mapped directly to scan flops so timing sees the mux delay "
         "from the start (chapter 10)."])

    h2("Hierarchy, boundary optimisation and ungrouping")
    p("Synthesis can keep the RTL hierarchy or dissolve it. Each choice "
      "has consequences downstream:")
    tbl(["Option", "Effect", "Trade-off"],
        [["Keep hierarchy, no boundary optimisation", "Each module "
          "optimised in isolation; ports preserved exactly",
          "Worst QoR; easiest LEC, ECO and debug"],
         ["Boundary optimisation", "Constants propagated and unused ports "
          "removed across boundaries; inverters pushed through ports",
          "Better QoR; LEC needs guidance; port behaviour changes"],
         ["Ungroup / flatten (auto-ungroup small modules)", "Hierarchy "
          "dissolved, global optimisation", "Best QoR; names change, "
          "harder ECO and UPF/constraint mapping"],
         ["Hard boundaries (dont_touch, hierarchical blocks)",
          "Block implemented separately, abstract model at the top",
          "Required for hierarchical implementation and IP reuse"]],
        [2.5, 3.4, 2.6], "Table 8.3 - Hierarchy handling.", bold_first=True)
    box("warn", "PITFALL - hierarchy that UPF and SDC depend on",
        ["Power domains in UPF and many SDC exceptions reference "
         "hierarchical instance names. If synthesis ungroups a module "
         "that defines a power domain boundary, or a path exception "
         "points to a pin that no longer exists, the constraint silently "
         "stops applying. Mark power-domain and constraint-anchor "
         "hierarchies as preserved, and check 'ignored constraints' "
         "reports after every compile."])

    h2("From wire-load models to physical-aware synthesis")
    p("Before placement, synthesis does not know how long each wire will "
      "be. Classic flows used **wire-load models (WLMs)**: a statistical "
      "table giving wire length (hence R and C) as a function of fanout "
      "and block size. The SKY130 Liberty file still contains them:")
    code([
        "wire_load(\"Small\") {",
        "  capacitance : 1.42e-05;",
        "  resistance : 0.0745;",
        "  slope : 8.3631;",
        "  fanout_length( 1, 23.2746);",
        "  fanout_length( 2, 32.1136);",
        "  fanout_length( 3, 48.4862);",
        "  fanout_length( 4, 64.0974);",
        "  fanout_length( 5, 86.2649);",
        "  fanout_length( 6, 84.2649);",
        "}",
    ], "Wire-load table from `sky130_fd_sc_hd__tt_025C_1v80.lib` (verbatim): "
       "length per fanout, plus capacitance and resistance per unit "
       "length. Note the non-monotonic entry at fanout 6 - such tables "
       "are statistical fits, not physics.")
    p("WLMs worked when gate delay dominated. From roughly the 130-90 nm "
      "generations on, wire delay became a large share of path delay and "
      "WLMs failed for fundamental reasons:")
    bul(["A net's length depends on **where its pins are placed**, not on "
         "its fanout. A fanout-2 net between distant blocks can be "
         "millimetres long; a fanout-10 net inside a cluster can be tiny.",
         "WLMs are **pessimistic on average and optimistic on the worst "
         "nets** - precisely the ones that fail after placement.",
         "Result: synthesis timing no longer correlated with place-and-"
         "route timing, and designs looped between synthesis and layout "
         "('timing closure crisis')."])
    p("The replacement is **physical-aware synthesis**: the synthesis "
      "tool runs a fast, coarse placement internally, using the real "
      "floorplan (die size, macro positions, blockages, pin locations) "
      "and the technology's RC per layer, and estimates each wire from "
      "its placed pins. Examples: Synopsys **DC Topographical** (DC-T), "
      "**DC-NXT/DC Graphical** (adds congestion awareness and can pass "
      "placement guidance to ICC2 - 'SPG'), **Fusion Compiler** (synthesis "
      "and P&R in one data model), and Cadence **Genus iSpatial** (runs "
      "Innovus placement/optimisation engines inside Genus). Typical "
      "claims are timing correlation to post-placement within a few "
      "percent, versus tens of percent with WLMs.")
    diagram([
        "  WLM flow:        RTL -> synth (WLM guess) -> netlist -> place -> timing surprise",
        "                                   ^                                   |",
        "                                   +------------ re-synthesise <-------+",
        "",
        "  physical-aware:  RTL + floorplan DEF + tech/LEF -> synth with virtual placement",
        "                   -> netlist (+ placement guidance) -> P&R starts close to closure",
    ], "Figure 8.5 - Why the industry moved to physical-aware synthesis.")

    h2("Synthesis constraints and design rules")
    p("Synthesis reads the same SDC as STA (chapter 9 explains each "
      "command) plus design-rule and optimisation constraints. "
      "**Design rule constraints (DRCs)** have priority over timing: the "
      "tool fixes them first, because a violation means the library "
      "tables are being used outside their characterised range.")
    code([
        "create_clock -name clk -period 2.0 [get_ports clk]",
        "set_clock_uncertainty -setup 0.15 [get_clocks clk]     ;# jitter + margin pre-CTS",
        "set_clock_transition 0.10 [get_clocks clk]             ;# ideal clock slew pre-CTS",
        "set_input_delay  0.8 -clock clk [remove_from_collection [all_inputs] [get_ports clk]]",
        "set_output_delay 0.6 -clock clk [all_outputs]",
        "set_driving_cell -lib_cell sky130_fd_sc_hd__buf_2 [all_inputs]",
        "set_load 0.02 [all_outputs]                            ;# pF, from the next block",
        "# design rule constraints",
        "set_max_transition 1.0  [current_design]   ;# ns - within Liberty table range",
        "set_max_capacitance 0.2 [current_design]   ;# pF",
        "set_max_fanout 20       [current_design]   ;# optimisation guide, not a physical law",
        "# optimisation controls",
        "set_dont_use  [get_lib_cells */sky130_fd_sc_hd__probe_*]",
        "set_dont_touch [get_cells u_sync*/u_meta_ff]            ;# synchroniser flops",
        "group_path -name io -from [all_inputs] -to [all_outputs]",
    ], "Synthesis constraint set (SDC plus Synopsys-style optimisation "
       "commands). Values are examples, not recommendations.")
    tbl(["Design rule", "Source", "Why it matters"],
        [["max_transition", "Liberty default_max_transition (1.5 ns in "
          "the SKY130 hd tt file), pin max_transition, SDC", "Beyond the "
          "table the delay is extrapolated; slow slews raise short-circuit "
          "power and noise sensitivity"],
         ["max_capacitance", "Liberty per output pin (e.g. 0.162 pF for "
          "dfxtp_1 Q in SKY130 tt), SDC", "Cell driving beyond its "
          "characterised load; also EM limits"],
         ["max_fanout", "SDC / library fanout_load", "Proxy for load and "
          "placement spread; modern flows rely more on cap and "
          "transition"]],
        [1.5, 3.3, 3.6], "Table 8.4 - Design rule constraints.",
        bold_first=True)

    h2("Reading QoR reports")
    p("After every compile, the synthesis engineer reads a small set of "
      "reports in a fixed order: constraint problems first, then design "
      "rules, then timing, then area and power. The excerpt below shows "
      "the structure of a Design Compiler `report_qor`.")
    code([
        "# ---- ILLUSTRATIVE report_qor excerpt (generic numbers, not from a real run) ----",
        "  Timing Path Group 'clk'",
        "  -----------------------------------",
        "  Levels of Logic:              24.00     <- depth of the worst path",
        "  Critical Path Length:          1.93     <- ns, data arrival",
        "  Critical Path Slack:          -0.07     <- WNS for this group",
        "  Critical Path Clk Period:      2.00",
        "  Total Negative Slack:         -1.84     <- TNS: sum over failing endpoints",
        "  No. of Violating Paths:       61.00",
        "  Cell Count / Area",
        "  Combinational Area:       182345.1",
        "  Noncombinational Area:     96210.4     <- flops, latches, ICGs",
        "  Macro/Black Box Area:     410000.0",
        "  Design Rules",
        "  Total Number of Nets:       61234",
        "  Nets With Violations:           3     <- max_trans / max_cap: fix before timing",
    ], "How to read a QoR report (illustrative, not from a real run).")
    bul(["**WNS / TNS / number of violating paths** per path group. A "
         "small WNS with a large TNS means many near-critical paths - a "
         "structural problem, not a single bad path.",
         "**Levels of logic** on the worst path: compare with the FO4 "
         "budget of chapter 6. Twice the budget means RTL must change.",
         "**Area split**: combinational vs sequential vs macro; watch for "
         "unexpected sequential area (inferred memories).",
         "**DRC violations**: max transition/capacitance must be zero or "
         "explained (e.g. ideal nets before CTS).",
         "**check_timing**: unconstrained endpoints, missing input delays, "
         "combinational loops, multiple clocks on a register."])

    h2("Common synthesis warnings and what they mean")
    p("Real synthesis logs contain thousands of lines. Knowing which "
      "warnings are harmless and which indicate broken RTL is a core "
      "skill. A deliberately broken module run through Yosys:")
    code([
        "module warn (input clk, input [1:0] sel, input [7:0] a, b, output reg [7:0] y,",
        "             output [7:0] z, output w);",
        "  wire [7:0] nc;                        // declared, never driven",
        "  always @* case (sel)                  // incomplete: no default, sel=3 not covered",
        "    2'd0: y = a;  2'd1: y = b;  2'd2: y = a & b;",
        "  endcase",
        "  assign z = nc ^ a;",
        "  assign w = a[0];",
        "  assign w = b[0];                      // second driver on w",
        "endmodule",
    ], "warn.v - three classic RTL mistakes.")
    out([
        "Latch inferred for signal `\\warn.\\y' from process `\\warn.$proc$warn.v:4$1':"
        " $auto$...",
        "Warning: multiple conflicting drivers for warn.\\a [0]:",
        "Warning: Wire warn.\\nc [7] is used but has no driver.",
        "Warning: Wire warn.\\nc [6] is used but has no driver.",
        "  ... (same for bits 5..0)",
        "Found and reported 9 problems.",
        "     $_DLATCH_N_                     8",
    ], "Real Yosys 0.33 messages (excerpt; long internal names shortened). "
       "Note that the conflicting-driver warning names a[0], because w "
       "and a[0] were merged into one net before the check ran.")
    tbl(["Message (paraphrased, any tool)", "Meaning", "Action"],
        [["Latch inferred", "A combinational block does not assign a "
          "variable on every path", "Add default assignment or default "
          "case unless the latch is intended"],
         ["Multiple drivers / conflicting drivers", "Two assignments or "
          "instances drive the same net", "Always a bug in ASIC RTL (no "
          "internal tri-states)"],
         ["Net has no driver / undriven input", "Floating wire; tools tie "
          "it to 0 or X", "Connect or tie explicitly"],
         ["Constant register removed", "Flop input is constant", "Check "
          "intent; a tied-off mode pin may have been wrong"],
         ["Unloaded / unused output, cell removed", "Logic with no "
          "observable output is deleted", "Usually fine; bad if the logic "
          "was a debug or safety feature (dont_touch it)"],
         ["Sensitivity list incomplete", "Simulation and synthesis "
          "disagree", "Use always_comb / always @*"],
         ["Width mismatch / truncation", "Operand sizes differ",
          "Fix in RTL; lint catches it earlier"],
         ["Timing loop detected / broken", "Combinational loop; the tool "
          "disables an arc to time it", "Never acceptable unless it is a "
          "known false loop, constrained explicitly"],
         ["Unresolved reference / black box", "Module or macro view "
          "missing at link", "Fix the filelist or library setup; never "
          "tape out with black boxes"]],
        [2.4, 3.0, 3.0], "Table 8.5 - Warnings every synthesis engineer "
                         "must recognise.", bold_first=True)

    h2("Logic equivalence checking after synthesis")
    p("Synthesis is a complex optimiser, and synthesis tools have bugs "
      "too. Before any netlist is used, **logic equivalence checking "
      "(LEC)** formally proves that the netlist implements the RTL. "
      "Tools: Synopsys Formality, Cadence Conformal LEC (and open-source "
      "Yosys `equiv_*` / eqy for small cases).")
    diagram([
        "     reference (RTL)                         implementation (netlist)",
        "  +----------------------+                +-----------------------------+",
        "  | in -> [cone] -> FF_a |  <== map ==>   | in -> [gates] -> FF_a_reg   |",
        "  |       [cone] -> FF_b |  <== map ==>   |       [gates] -> FF_b_reg   |",
        "  |       [cone] -> out  |  <== map ==>   |       [gates] -> out        |",
        "  +----------------------+                +-----------------------------+",
        "  1. map compare points (flops, latches, outputs, black-box pins) by name",
        "     + structure + function",
        "  2. prove each pair of logic cones equivalent with SAT/BDD engines",
        "  3. report: equivalent / non-equivalent (with counter-example) / aborted",
    ], "Figure 8.6 - Combinational equivalence checking: map state points, "
       "then compare the combinational cones between them.")
    bul(["**Guidance files** (Synopsys SVF, Cadence mapping files) record "
         "the transformations synthesis made - register merges, "
         "inversions, retiming, FSM re-encoding - so the LEC tool can "
         "map points that changed name or polarity.",
         "**Retiming, clock gating and sequential optimisations** break "
         "the one-to-one flop mapping; they need guidance or sequential "
         "equivalence checking.",
         "**Aborted points** (typically large multipliers) are resolved "
         "with datapath-aware LEC, partitioning or cut-points - never "
         "ignored.",
         "LEC is run RTL -> synthesised netlist, synthesised -> DFT-inserted "
         "netlist (in test-mode-off setup), and netlist -> post-layout "
         "netlist, and after every ECO (chapter 19)."])
    box("expert", "INTERVIEW INSIGHT - LEC versus simulation",
        ["LEC proves that two designs are the same; it says nothing about "
         "whether either is correct. A bug in the RTL is faithfully "
         "reproduced in the netlist and LEC passes. That is why DV signs "
         "off the RTL and LEC carries that sign-off to the netlist and "
         "layout."])

    h2("Summary")
    bul(["A production flow: analyze, elaborate, link, constrain, compile "
         "(generic opt, mapping, timing/area/power optimisation), DFT "
         "insertion, incremental compile, reports, netlist + SDC + UPF + "
         "SCANDEF.",
         "Logic is optimised as an AIG and mapped by cut enumeration and "
         "library matching; timing-driven moves are sizing, buffering, "
         "restructuring, pin swapping and multi-Vt assignment.",
         "Real SKY130 runs: a 32-bit adder spans 1205-1326 um^{2} and "
         "1.46-2.25 ns depending on the delay target; a Kogge-Stone "
         "structure reaches 1.01 ns at 2.4x the area. Architecture beats "
         "optimisation.",
         "Datapath synthesis picks adder/multiplier architectures and "
         "merges arithmetic into carry-save trees; retiming and clock-"
         "gating insertion are sequential optimisations that LEC must be "
         "told about.",
         "Wire-load models failed because wire length depends on placement, "
         "not fanout; physical-aware synthesis (DC-T/NXT, Fusion Compiler, "
         "Genus iSpatial) uses a real floorplan.",
         "Read reports in order: constraint checks, DRCs, WNS/TNS/levels, "
         "area; know the classic warnings; prove every netlist with LEC."])

    h2("Exercises")
    bul(["In the add32 sweep, why does a target of 900 ps produce the same "
         "netlist as no target at all? What would a commercial tool report "
         "for that run?",
         "Estimate, from Table 8.2, the number of prefix (black) cells in "
         "32-bit Kogge-Stone and Brent-Kung adders. Relate the difference "
         "to the ks32 area in the sweep.",
         "A design has WNS = -0.05 ns and TNS = -350 ns with 12,000 "
         "violating endpoints. What does this suggest and what would you "
         "try first?",
         "Explain why a synthesised netlist's timing with wire-load models "
         "can be optimistic for some nets and pessimistic for others.",
         "Your LEC run reports 40 unmapped flops after synthesis with "
         "retiming enabled. List the likely causes and fixes.",
         "Write the SDC design-rule constraints for a library whose tables "
         "stop at 1.2 ns input slew and whose largest output load index "
         "is 0.25 pF, keeping a 20% margin."], ordered=True)


# =============================================================================
#                  CHAPTER 9 - STATIC TIMING ANALYSIS IN DEPTH
# =============================================================================
def _ch9():
    chapter("Static Timing Analysis in Depth")
    p("Static timing analysis (STA) proves that every path in the design "
      "meets its timing requirements at every operating corner and mode, "
      "without simulating any vectors. It is the timing sign-off method "
      "for every digital ASIC. STA engines run inside synthesis and "
      "place-and-route for optimisation; sign-off STA is run in a "
      "dedicated tool - Synopsys **PrimeTime**, Cadence **Tempus**, "
      "Siemens/other tools, or the open-source **OpenSTA** used by "
      "OpenROAD. Timing sign-off is owned by the **STA / timing sign-off "
      "engineer**, with constraints owned jointly with the RTL designers "
      "who know the intent.")
    p("The companion RTL Design guide introduces setup/hold and SDC from "
      "the RTL designer's side. Here we go inside the engine: the timing "
      "graph, how a cell delay is computed from Liberty tables, wire "
      "models, the full setup and hold equations with clock latency, "
      "uncertainty and CRPR, exceptions, latches, on-chip variation "
      "models, multi-corner multi-mode analysis, signal integrity and "
      "hold fixing. Along the way we compute a real path by hand - in "
      "Python, using the actual SKY130 NLDM tables.")

    h2("The timing graph and timing arcs")
    p("STA converts the netlist into a directed acyclic **timing graph**: "
      "nodes are pins, edges are **timing arcs**. Arcs come from two "
      "sources:")
    tbl(["Arc type", "From - to", "Source of its delay / constraint"],
        [["Cell arc, combinational", "Input pin -> output pin of a gate "
          "(A -> Y of nand2), with a **timing sense**: positive unate "
          "(buffer, AND), negative unate (inverter, NAND, NOR) or non-unate "
          "(XOR, mux select)", "Liberty `cell_rise/cell_fall` and "
          "`rise/fall_transition` tables"],
         ["Cell arc, sequential (launch)", "Clock pin -> Q of a flop "
          "(timing_type rising_edge), or D -> Q of a transparent latch",
          "Liberty tables, as above"],
         ["Timing check (constraint) arc", "Clock pin -> D pin: setup, "
          "hold; recovery/removal on async pins; clock-gating checks; "
          "min pulse width", "Liberty `rise/fall_constraint` tables "
          "(setup_rising, hold_rising...)"],
         ["Net arc", "Driver pin -> each load pin", "Wire RC: estimated, "
          "or extracted (SPEF) and reduced by the delay calculator"]],
        [2.0, 3.8, 2.6], "Table 9.1 - Timing arcs.", bold_first=True)
    diagram([
        "  launch                                                        capture",
        "  +-------+   net   +------+  net  +-----+  net  +------+  net  +-------+",
        "  | FF1   |-------->| A    |------>| A   |------>| A    |------>| D FF2 |",
        "  |  CLK  |Q        | nand2|Y      | inv |Y      | nor2 |Y      |  CLK  |",
        "  +---^---+         +------+       +-----+       +------+       +---^---+",
        "      |  (CLK->Q)      (A->Y)        (A->Y)        (A->Y)   setup/hold",
        "      |                                                     check arcs",
        "  clock source --[launch clock path: buffers]--+--[capture clock path]--+",
        "                                               |  common part  (CRPR)  |",
        "",
        "  Startpoints: clock pins of flops/latches, primary inputs.",
        "  Endpoints  : data pins of flops/latches (setup/hold), primary outputs.",
        "  Path types : in2reg, reg2reg, reg2out, in2out (combinational feed-through).",
    ], "Figure 9.1 - A register-to-register timing path as the STA engine "
       "sees it: cell arcs, net arcs, check arcs and the launch/capture "
       "clock paths.")
    p("Because the graph is acyclic, arrival times are propagated forward "
      "in topological order (latest arrival for setup, earliest for hold) "
      "and required times backward; slack at each pin is required minus "
      "arrival. This is linear in the size of the graph, which is why STA "
      "handles billion-gate designs where simulation could not. The price "
      "is pessimism: STA assumes every path can be sensitised, which is "
      "why **false-path** and **multicycle** exceptions exist.")

    h2("Delay calculation: NLDM tables, slew propagation and beyond")
    p("A cell's delay depends mostly on two quantities: the **input "
      "transition time** (slew) and the **output load capacitance**. In "
      "the Non-Linear Delay Model (NLDM), the Liberty file stores for "
      "each arc a 2-D table of delay and a 2-D table of output "
      "transition, indexed by exactly those two variables. Here is the "
      "real `cell_fall` table of the SKY130 nand2_1 arc A -> Y (a "
      "negative-unate arc, so a rising A causes a falling Y):")
    out([
        "slew\\load  0.0005  0.0013  0.0035  0.0091  0.0240  0.0633  0.1666",
        " 0.0100     0.0206  0.0251  0.0363  0.0652  0.1404  0.3379  0.8628",
        " 0.0231     0.0244  0.0289  0.0403  0.0697  0.1447  0.3426  0.8634",
        " 0.0531     0.0327  0.0384  0.0505  0.0798  0.1552  0.3529  0.8773",
        " 0.1225     0.0428  0.0514  0.0698  0.1039  0.1794  0.3767  0.8969",
        " 0.2823     0.0525  0.0660  0.0938  0.1461  0.2370  0.4342  0.9574",
        " 0.6507     0.0551  0.0755  0.1174  0.1977  0.3329  0.5653  1.0821",
        " 1.5000     0.0332  0.0633  0.1272  0.2474  0.4578  0.8093  1.3854",
        "negative_unate",
    ], "SKY130 hd tt nand2_1, pin Y related to A, cell_fall (ns), rows = "
       "input slew (ns), columns = load (pF). Printed by the Python "
       "Liberty reader used later in this chapter, rounded to 4 decimals.")
    p("Reading the table: with a sharp input (10 ps) and a light load "
      "(0.5 fF), the NAND falls in 21 ps; driving 166 fF it takes 863 ps. "
      "Delay grows almost linearly with load (the output resistance "
      "charging the load) and more weakly with input slew. Delay "
      "calculation for an arbitrary point uses **bilinear interpolation** "
      "(and extrapolation outside the table - a reason to keep "
      "max_transition and max_capacitance inside the characterised range):")
    _eqa(["given x1 <= x <= x2 (slew) and y1 <= y <= y2 (load), table values Q11..Q22:",
          "",
          "fx = (x - x1)/(x2 - x1),  fy = (y - y1)/(y2 - y1)",
          "d(x,y) = Q11 (1-fx)(1-fy) + Q21 fx (1-fy) + Q12 (1-fx) fy + Q22 fx fy"],
         "Bilinear interpolation of NLDM tables.")
    p("**Slew propagation**: each arc also has an output transition table. "
      "The output slew of stage k becomes the input slew of stage k+1, "
      "so a weak driver early in a path slows every later stage. "
      "Pessimistic engines propagate the worst slew among all inputs "
      "of a gate ('worst-slew propagation'); more accurate modes "
      "propagate the slew belonging to the path being reported ('path-"
      "based analysis', PBA, versus graph-based analysis, GBA).")
    h3("Beyond NLDM: effective capacitance and current-source models")
    bul(["**Resistive shielding / effective capacitance.** When a driver "
         "sees a wire with significant resistance, the far-end capacitance "
         "is partly shielded; the driver behaves as if it drove a smaller "
         "**C_eff**. Delay calculators iterate to find C_eff that matches "
         "the charge delivered in the first part of the transition, and "
         "then look up the NLDM table at C_eff.",
         "**Current-source models (CCS from Synopsys, ECSM from Cadence)** "
         "store the output current waveform versus time for each "
         "(slew, load) point instead of a single delay number. The delay "
         "calculator drives the actual RC network with that current and "
         "gets an accurate waveform. This matters at advanced nodes where "
         "waveforms are far from ideal ramps and for noise analysis "
         "(CCS noise).",
         "**Liberty Variation Format (LVF)** adds per-arc sigma tables "
         "for statistical OCV (section 9.9)."])
    box("key", "Where the numbers come from",
        ["Every delay in STA comes from the Liberty tables that the "
         "library team characterised with SPICE at a given PVT corner "
         "(chapter 4). STA never simulates transistors; it interpolates. "
         "If the tables are wrong or used outside their range, sign-off "
         "is wrong - which is why library qualification and "
         "extrapolation checks are part of the sign-off methodology."])

    h2("Wire models: from lumped C to extracted RC")
    p("The net between two cells contributes capacitance (loading the "
      "driver) and, when long, resistance (adding delay along the wire "
      "and degrading slew). The model depends on the stage of the flow:")
    tbl(["Model", "Used when", "Delay"],
        [["Lumped C", "Short nets; early synthesis", "Only adds C to the "
          "driver load; no wire delay"],
         ["Wire-load model", "Legacy synthesis (chapter 8)", "Statistical "
          "R and C by fanout"],
         ["Lumped RC / Elmore", "Estimation after placement; hand analysis",
          "Elmore delay: sum over resistors of R_i times downstream C"],
         ["Distributed RC network (SPEF)", "Post-route sign-off",
          "Reduced order models (e.g. pi-model for driver, AWE/moment "
          "matching) for each driver-load pair"]],
        [1.8, 2.4, 3.8], "Table 9.2 - Interconnect models.", bold_first=True)
    _eqa(["Elmore delay to node k in an RC tree:",
          "  T_D(k) = sum over resistors R_i on the path from the driver to k of",
          "           R_i x (total capacitance downstream of R_i)",
          "",
          "uniform wire, length L, r and c per unit length:  T_Elmore = 0.5 r c L^2",
          "(the 50% point of the distributed line's step response is ~ 0.38 r c L^2)"],
         "Elmore delay. The quadratic dependence on length is why long wires "
         "need repeaters (chapter 17).")
    code([
        "*SPEF \"IEEE 1481-1998\"                       // illustrative structure only",
        "*T_UNIT 1 NS  *C_UNIT 1 FF  *R_UNIT 1 OHM",
        "*D_NET n42 5.23                              // net n42, total cap 5.23 fF",
        "*CONN",
        "*I u1:Y O *L 0 *D sky130_fd_sc_hd__nand2_1   // driver pin",
        "*I u2:A I *L 2.3                             // load pin, pin cap",
        "*CAP",
        "1 n42:1 0.91",
        "2 n42:2 1.12",
        "3 n42:1 n77:3 0.20                           // coupling cap to aggressor net n77",
        "*RES",
        "1 u1:Y n42:1 12.5",
        "2 n42:1 n42:2 38.0",
        "3 n42:2 u2:A 9.1",
        "*END",
    ], "Structure of a SPEF (Standard Parasitic Exchange Format, IEEE 1481) "
       "net from an extraction tool: ground caps, coupling caps and "
       "resistors forming the RC network (illustrative values).")

    h2("Setup and hold: the full equations")
    p("For a path launched by clock edge at time 0 at FF1 and captured by "
      "the next edge (period T) at FF2, with clock insertion delays "
      "(latencies) L_launch and L_capture from the clock source to each "
      "flop's clock pin:")
    _eqa(["arrival  A = L_launch + t_clk->q + t_logic + t_wire",
          "",
          "SETUP (max delays):",
          "  required R_s = T + L_capture - t_setup - U_setup + CRPR",
          "  slack_s = R_s - A_max  >= 0",
          "",
          "HOLD  (min delays, same clock edge):",
          "  required R_h = L_capture + t_hold + U_hold - CRPR",
          "  slack_h = A_min - R_h  >= 0",
          "",
          "skew  = L_capture - L_launch  (positive skew helps setup, hurts hold)"],
         "Setup and hold equations. U = clock uncertainty (jitter + margin; "
         "before CTS also estimated skew). CRPR = clock reconvergence "
         "pessimism removal (below).")
    diagram([
        "  CLK at FF1  ___|~~~~~~~~|________|~~~~~~~~|____     launch edge at L_launch",
        "                 ^ launch                   ^ next edge (T later)",
        "  FF1/Q        =====X================================ Q changes t_clk->q later",
        "  FF2/D        ================X===================== after t_logic + t_wire",
        "                               |<-- setup slack -->|<- t_setup ->| capture edge",
        "  CLK at FF2  ______|~~~~~~~~|________|~~~~~~~~|___   (shifted by skew, +/- U)",
        "                    ^ hold is checked here: new data must not arrive",
        "                      before t_hold after the SAME edge that launched it",
    ], "Figure 9.2 - Setup is checked against the next capture edge, hold "
       "against the same edge.")
    h3("CRPR - clock reconvergence pessimism removal")
    p("With on-chip variation, STA uses the **late** delay for the launch "
      "clock path and the **early** delay for the capture clock path in a "
      "setup check (and the reverse for hold). But the launch and capture "
      "clock paths share a common segment from the clock source to the "
      "point where they diverge. A physical buffer cannot be both slow "
      "and fast at the same moment, so the difference between its late "
      "and early delay on the common segment is pure pessimism. **CRPR** "
      "(also called CPPR) adds that difference back as a credit. It is "
      "significant: on a deep clock tree with derates, CRPR can be tens "
      "of picoseconds. For hold checks, where launch and capture use the "
      "same edge, the full common-path difference is removed; for setup "
      "(different edges), jitter-related components are not removed.")

    h2("A worked example: STA of a real SKY130 path in Python")
    p("To make the equations concrete we time the path of Figure 9.1 - "
      "FF1 (dfxtp_1) -> nand2_1 -> inv_1 -> nor2_1 -> FF2 (dfxtp_1) - "
      "using the real NLDM tables from the SKY130 tt Liberty file. The "
      "script parses the Liberty groups it needs, computes every load as "
      "pin capacitance of the next gate plus 2 fF of wire, propagates "
      "slew stage by stage, looks up the setup and hold constraint "
      "tables of the capturing flop (indexed by clock slew and data "
      "slew), and applies the equations above with a 1 ns clock, 0.30/0.35 "
      "ns launch/capture latency (50 ps of useful skew), and 80/30 ps "
      "setup/hold uncertainty. Both edges are analysed because the rise "
      "and fall delays differ.")
    code([
        '# sta3.py - tiny NLDM static timing analysis of one register-to-register path',
        'import re, bisect',
        'LIB = open("hd_tt.lib").read()',
        '',
        'def group(text, head):                      # return body of "head { ... }"',
        '    i = text.index(head); j = text.index("{", i) + 1; d = 1; k = j',
        '    while d:',
        '        d += {"{": 1, "}": -1}.get(text[k], 0); k += 1',
        '    return text[j:k - 1]',
        '',
        'def nums(s): return [float(x) for x in re.findall(r"-?[\\d.]+(?:e-?\\d+)?", s)]',
        '',
        'def table(body, kind):                      # index_1, index_2, values of one table',
        '    t = group(body, kind + " (")',
        '    ix = re.findall(r\'index_\\d\\("([^"]*)"\\)\', t)',
        '    v = nums(re.search(r"values\\((.*?)\\);", t, re.S).group(1))',
        '    i1 = nums(ix[0]); i2 = nums(ix[1]) if len(ix) > 1 else [0.0]',
        '    return i1, i2, [v[r * len(i2):(r + 1) * len(i2)] for r in range(len(i1))]',
        '',
        'def lookup(tab, x, y):                      # bilinear inter/extrapolation',
        '    i1, i2, v = tab',
        '    def seg(ax, a):',
        '        k = min(max(bisect.bisect(ax, a) - 1, 0), len(ax) - 2)',
        '        return k, (a - ax[k]) / (ax[k + 1] - ax[k])',
        '    r, fx = seg(i1, x); c, fy = seg(i2, y)',
        '    return (v[r][c] * (1 - fx) * (1 - fy) + v[r + 1][c] * fx * (1 - fy)',
        '            + v[r][c + 1] * (1 - fx) * fy + v[r + 1][c + 1] * fx * fy)',
        '',
        'def arc(cell, pin, rel, ttype=None):        # the timing() group for pin<-rel',
        '    body = group(group(LIB, \'cell ("sky130_fd_sc_hd__%s")\' % cell), \'pin ("%s")\' % pin)',
        '    for t in re.split(r"\\btiming \\(\\)", body)[1:]:',
        '        if \'related_pin : "%s"\' % rel in t and (ttype is None or ttype in t):',
        '            return t',
        '',
        'def cap(cell, pin):',
        '    body = group(group(LIB, \'cell ("sky130_fd_sc_hd__%s")\' % cell), \'pin ("%s")\' % pin)',
        '    return float(re.search(r"\\bcapacitance : ([\\d.]+)", body).group(1))',
        '',
        '# ---- the path: FF1/CLK -> Q -> nand2_1 -> inv_1 -> nor2_1 -> FF2/D ------------------',
        'T, LAT_L, LAT_C, UNC_S, UNC_H = 1.00, 0.30, 0.35, 0.08, 0.03   # ns: period, latencies, unc.',
        'CLK_SLEW, CWIRE = 0.10, 0.002                                  # ns, pF (2 fF per net)',
        'stages = [("dfxtp_1", "CLK", "Q", "nand2_1", "A"), ("nand2_1", "A", "Y", "inv_1", "A"),',
        '          ("inv_1", "A", "Y", "nor2_1", "A"), ("nor2_1", "A", "Y", "dfxtp_1", "D")]',
        'INV = {"rise": "fall", "fall": "rise"}',
        '',
        'def run(q_edge):',
        '    t, slew, edge = LAT_L, CLK_SLEW, None',
        '    print("%-22s %6s %6s %7s %7s  %s" % ("point", "load", "slew", "incr", "path", "edge"))',
        '    print("%-22s %6s %6.3f %7.3f %7.3f  %s"',
        '          % ("clock CLK (launch)", "", CLK_SLEW, LAT_L, t, "r"))',
        '    for cell, i, o, nxt, npin in stages:',
        '        edge = q_edge if edge is None else (edge if cell.startswith("buf") else INV[edge])',
        '        load = cap(nxt, npin) + CWIRE',
        '        a = arc(cell, o, i)',
        '        d = lookup(table(a, "cell_" + edge), slew, load)',
        '        slew = lookup(table(a, edge + "_transition"), slew, load)',
        '        t += d',
        '        print("%-22s %6.4f %6.3f %7.3f %7.3f  %s"',
        '              % (cell + "/" + o, load, slew, d, t, edge[0]))',
        '    su = lookup(table(arc("dfxtp_1", "D", "CLK", "setup_rising"), edge + "_constraint"),',
        '                CLK_SLEW, slew)',
        '    ho = lookup(table(arc("dfxtp_1", "D", "CLK", "hold_rising"), edge + "_constraint"),',
        '                CLK_SLEW, slew)',
        '    req = T + LAT_C - UNC_S - su',
        '    print("data arrival time %.3f | required = %.2f + %.2f - %.2f - setup %.3f = %.3f"',
        '          % (t, T, LAT_C, UNC_S, su, req))',
        '    print("SETUP slack (%s at D) = %+.3f ns   %s"',
        '          % (edge, req - t, "MET" if req >= t else "VIOLATED"))',
        '    hreq = LAT_C + UNC_H + ho',
        '    print("HOLD  slack           = %.3f - (%.2f + %.2f + hold %.3f) = %+.3f ns\\n"',
        '          % (t, LAT_C, UNC_H, ho, t - hreq))',
        '    return req - t',
        '',
        'w = min(run("rise"), run("fall"))',
        'print("worst setup slack %.3f ns -> max frequency ~ %.0f MHz" % (w, 1000 / (T - w)))',
    ], "sta3.py - a complete (if tiny) NLDM timing engine: Liberty reader, "
       "bilinear lookup, slew propagation, setup and hold checks.")
    out([
        'point                    load   slew    incr    path  edge',
        'clock CLK (launch)             0.100   0.300   0.300  r',
        'dfxtp_1/Q              0.0043  0.055   0.330   0.630  r',
        'nand2_1/Y              0.0043  0.042   0.055   0.686  f',
        'inv_1/Y                0.0044  0.047   0.056   0.742  r',
        'nor2_1/Y               0.0037  0.029   0.044   0.786  f',
        'data arrival time 0.786 | required = 1.00 + 0.35 - 0.08 - setup 0.091 = 1.179',
        'SETUP slack (fall at D) = +0.393 ns   MET',
        'HOLD  slack           = 0.786 - (0.35 + 0.03 + hold -0.034) = +0.440 ns',
        '',
        'point                    load   slew    incr    path  edge',
        'clock CLK (launch)             0.100   0.300   0.300  r',
        'dfxtp_1/Q              0.0043  0.034   0.318   0.618  f',
        'nand2_1/Y              0.0043  0.051   0.059   0.677  r',
        'inv_1/Y                0.0044  0.028   0.043   0.720  f',
        'nor2_1/Y               0.0037  0.093   0.101   0.821  r',
        'data arrival time 0.821 | required = 1.00 + 0.35 - 0.08 - setup 0.057 = 1.213',
        'SETUP slack (rise at D) = +0.392 ns   MET',
        'HOLD  slack           = 0.821 - (0.35 + 0.03 + hold -0.034) = +0.475 ns',
        '',
        'worst setup slack 0.392 ns -> max frequency ~ 1645 MHz',
    ], "Real output of sta3.py against the SKY130 hd tt_025C_1v80 Liberty file.")
    p("Points worth noticing, all from real library data:")
    bul(["**Clock-to-Q dominates** this short path: 318-330 ps of a total "
         "logic delay of about 490-520 ps. In real designs clock-to-Q plus "
         "setup is a fixed tax of every pipeline stage (chapter 6).",
         "**Rise and fall differ.** The nor2_1 output **rise** takes 101 ps "
         "with a 93 ps slew, versus 44 ps / 29 ps for its fall: a NOR "
         "pulls up through two series PMOS transistors (weak holes, "
         "stacked). Libraries and synthesis tools prefer NAND-based logic "
         "for exactly this reason.",
         "**The setup constraint depends on the data edge and slews**: "
         "91 ps for a falling D, 57 ps for a rising D.",
         "**Negative hold time** (-34 ps) is normal for flip-flops whose "
         "internal clock path delays capture; it makes hold easier to meet.",
         "**The useful skew** (capture clock 50 ps later) added 50 ps of "
         "setup slack and took 50 ps from hold slack - the trade-off CTS "
         "exploits deliberately (chapter 16).",
         "Real sign-off adds what the script leaves out: wire resistance "
         "(Elmore/C_eff), multiple fan-outs, OCV derates, CRPR, SI "
         "delta-delays and every other corner."])

    h2("Reading a timing report line by line")
    p("A sign-off report has exactly the structure the script printed. "
      "The excerpt below is in PrimeTime's `report_timing` format with "
      "generic numbers:")
    code([
        "# ---- ILLUSTRATIVE report_timing excerpt (generic numbers, not from a real run) ----",
        "  Startpoint: u_core/u_alu/res_reg_12_  (rising edge-triggered flip-flop",
        "              clocked by core_clk)",
        "  Endpoint: u_core/u_wb/data_reg_3_ (rising edge-triggered flip-flop clocked",
        "            by core_clk)",
        "  Path Group: core_clk      Path Type: max      Scenario: func_ss0p72v_125c",
        "",
        "  Point                                    Fanout  Cap   Trans   Incr    Path",
        "  clock core_clk (rise edge)                                     0.000   0.000",
        "  clock network delay (propagated)                               0.412   0.412",
        "  u_core/u_alu/res_reg_12_/CK (DFFQ_X1)                  0.045   0.000   0.412 r",
        "  u_core/u_alu/res_reg_12_/Q (DFFQ_X1)             2    3.1  0.038   0.091   0.503 f",
        "  u_core/u_alu/U3021/ZN (NAND2_X2)                 1    1.9  0.027   0.024 & 0.527 r",
        "  ... (14 more stages)",
        "  u_core/u_wb/data_reg_3_/D (DFFQ_X1)                    0.041   0.006 & 0.981 f",
        "  data arrival time                                                      0.981",
        "",
        "  clock core_clk (rise edge)                                     1.000   1.000",
        "  clock network delay (propagated)                               0.398   1.398",
        "  clock reconvergence pessimism                                  0.012   1.410",
        "  clock uncertainty                                             -0.030   1.380",
        "  library setup time                                            -0.035   1.345",
        "  data required time                                                     1.345",
        "  slack (MET)                                                            0.364",
    ], "Anatomy of a PrimeTime path report (illustrative). '&' marks "
       "increments that include annotated parasitics; r/f = rise/fall.")
    tbl(["Report item", "What to check"],
        [["Startpoint / endpoint / clock", "Are these the clocks you expect? "
          "A path between asynchronous clocks means a missing clock group"],
         ["Path type max/min, scenario", "Setup vs hold, and which corner/mode"],
         ["Clock network delay ideal/propagated", "Pre-CTS reports use ideal "
          "clocks; post-CTS must be propagated"],
         ["Trans and Cap columns", "Large transitions point to weak drivers "
          "or long wires; compare with max_transition"],
         ["Incr per stage", "Which stage dominates: a single big increment is "
          "a sizing/buffering fix, many small ones a logic-depth problem"],
         ["CRPR, uncertainty, library setup", "Plausible values for the "
          "stage of the flow"],
         ["Slack", "Sign and magnitude; compare GBA vs PBA for pessimism"]],
        [2.3, 5.5], "Table 9.3 - How an STA engineer reads a path.",
        bold_first=True)

    h2("Constraints: clocks, I/O, exceptions")
    p("STA is only as good as its constraints. The Synopsys Design "
      "Constraints (SDC) format is the industry standard, read by "
      "synthesis, P&R and sign-off tools alike.")
    code([
        "# primary and generated clocks",
        "create_clock -name core_clk -period 1.25 [get_ports clk_core]      ;# 800 MHz",
        "create_clock -name ref_clk  -period 40.0 [get_ports clk_ref]       ;# 25 MHz",
        "create_generated_clock -name core_div2 -source [get_ports clk_core] \\",
        "     -divide_by 2 [get_pins u_crg/u_div2/q_reg/Q]",
        "set_clock_groups -asynchronous -group {core_clk core_div2} -group {ref_clk}",
        "set_clock_uncertainty -setup 0.05 [get_clocks core_clk]   ;# post-CTS: jitter+margin",
        "set_clock_latency -source 0.2 [get_clocks core_clk]       ;# off-chip / PLL latency",
        "# I/O budgets relative to the board / neighbour block",
        "set_input_delay  -max 0.50 -clock core_clk [get_ports din*]",
        "set_input_delay  -min 0.10 -clock core_clk [get_ports din*]",
        "set_output_delay -max 0.40 -clock core_clk [get_ports dout*]",
        "# exceptions (each one needs a written justification)",
        "set_false_path -from [get_ports test_mode]                 ;# static in functional mode",
        "set_multicycle_path -setup 2 -from [get_cells u_mac/acc*] -to [get_cells u_out/r*]",
        "set_multicycle_path -hold  1 -from [get_cells u_mac/acc*] -to [get_cells u_out/r*]",
        "set_max_delay 1.0 -datapath_only -from [get_cells u_fifo/wptr_gray*] \\",
        "     -to [get_cells u_fifo/u_sync_w/meta*]                  ;# CDC bus skew bound",
        "set_case_analysis 0 [get_ports scan_mode]                  ;# functional mode",
    ], "A representative SDC. The multicycle pair is the classic idiom: "
       "move setup to the 2nd edge, then move hold back by 1 so it is "
       "checked at the original launch edge.")
    box("warn", "PITFALL - multicycle without the hold adjustment",
        ["`set_multicycle_path -setup 2` alone also moves the default hold "
         "check one cycle later, so the tool now demands that data be "
         "held for a whole cycle - producing hundreds of hold 'violations' "
         "that P&R will 'fix' by inserting large delay chains. Always pair "
         "it with `-hold 1` (in the usual same-clock case) and verify the "
         "RTL really holds the source stable for two cycles."])
    tbl(["Exception", "Meaning", "Risk"],
        [["set_false_path", "Path is never functionally exercised (static "
          "config, mutually exclusive modes, async groups)", "If wrong, a "
          "real path goes untimed - silicon failure"],
         ["set_multicycle_path", "Data is allowed N cycles (enable-based "
          "slow logic)", "RTL must guarantee it; verify with assertions"],
         ["set_max_delay / min_delay", "Point-to-point bounds (CDC buses, "
          "asynchronous interfaces)", "-datapath_only ignores clock "
          "latency; use deliberately"],
         ["set_clock_groups", "Clocks are asynchronous/exclusive", "Wrong "
          "grouping hides real synchronous paths"],
         ["set_case_analysis / set_disable_timing", "Constant values or "
          "disabled arcs define a mode", "Mode-specific; must match the "
          "chip's real configuration"]],
        [2.0, 3.6, 2.6], "Table 9.4 - Timing exceptions.", bold_first=True)

    h2("Latches and time borrowing")
    p("A positive level-sensitive latch is transparent while its clock is "
      "high. If data arrives at a latch **after** the opening edge but "
      "before the closing edge (minus setup), it passes through and the "
      "path simply continues into the next stage: the latch **borrows** "
      "time from the next stage. STA handles this by checking the "
      "arrival against the closing edge and passing the borrowed amount "
      "to the next path.")
    _eqa(["latch opens at t_open, closes at t_close (= t_open + high phase)",
          "if A <= t_open                  : no borrowing, next path starts at t_open",
          "if t_open < A <= t_close - t_su : borrow = A - t_open, next path starts at A",
          "if A > t_close - t_su           : setup violation at the latch",
          "max borrow is often further limited by set_max_time_borrow"],
         "Time borrowing through a transparent latch.")
    p("Latch-based design (two-phase clocking, pulsed latches) tolerates "
      "unbalanced stages and clock skew better than flop-based design and "
      "is used in high-performance CPU datapaths and some register files; "
      "the cost is harder hold analysis, more complex DFT and a much more "
      "careful constraint set.")

    h2("On-chip variation: derates, AOCV, POCV/SOCV and LVF")
    p("Transistors on the same die differ: random dopant fluctuation, "
      "line-edge roughness, local voltage drop and temperature gradients "
      "(chapters 2-3). A corner library describes the **global** process "
      "corner; **on-chip variation (OCV)** models the local spread "
      "around it. Four generations of models:")
    tbl(["Model", "How it works", "Weakness"],
        [["Flat OCV derate", "Multiply all late delays by, e.g., 1.05-1.10 "
          "and early delays by 0.90-0.95", "Over-pessimistic on long "
          "paths (random variation partly cancels), may be optimistic on "
          "short ones"],
         ["AOCV (advanced OCV)", "Derate from a table indexed by **path "
          "depth** (and distance/bounding box): deep paths get small "
          "derates because random variation averages out", "Table-based "
          "approximation; tables per cell type"],
         ["POCV / SOCV (parametric / statistical OCV)", "Each arc has a "
          "mean and a sigma; sigmas add in quadrature along a path; path "
          "delay = mean + n x sigma (n typically 3)", "Needs per-arc sigma "
          "data"],
         ["LVF (Liberty Variation Format)", "Liberty tables of sigma per "
          "arc, per slew/load point (and for constraints), used by POCV",
          "Characterisation cost; now standard at advanced nodes"]],
        [2.0, 4.0, 2.6], "Table 9.5 - Evolution of OCV modelling.",
        bold_first=True)
    _eqa(["flat OCV     : D_late = 1.08 x sum(d_i)         (example derate)",
          "POCV (path)  : mu_path = sum(mu_i),  sigma_path = sqrt( sum(sigma_i^2) )",
          "               D_late  = mu_path + 3 sigma_path",
          "",
          "N identical stages, each mu, sigma:  D = N mu + 3 sqrt(N) sigma",
          "  -> relative margin 3 sigma / (sqrt(N) mu) shrinks as 1/sqrt(N)"],
         "Why statistical OCV is less pessimistic on deep paths "
         "(independent random variation assumed).")

    h2("Multi-corner multi-mode (MCMM) analysis")
    p("A chip must work at every combination of process, voltage and "
      "temperature (PVT) and in every functional and test **mode**. Each "
      "combination with its RC extraction corner is a **scenario**. "
      "Setup is usually worst at slow process, low voltage, and high "
      "temperature - except that at advanced nodes **temperature "
      "inversion** can make low temperature the slow corner at low "
      "voltage. Hold is usually worst at fast process, high voltage, with "
      "the minimum-RC extraction.")
    tbl(["Scenario", "Process / V / T", "RC corner", "Checks"],
        [["func_setup_ss", "SS / Vnom-10% / 125 C (and -40 C)", "Cworst, "
          "RCworst", "Setup, max transition/cap"],
         ["func_hold_ff", "FF / Vnom+10% / -40 C and 125 C", "Cbest, "
          "RCbest", "Hold"],
         ["func_hold_ss", "SS / low V", "Cworst", "Hold (clock skew "
          "grows at slow corners)"],
         ["func_typ", "TT / Vnom / 25-85 C", "typical", "Power analysis, "
          "correlation"],
         ["scan_shift", "SS and FF", "worst/best", "Shift at test "
          "frequency: mostly hold"],
         ["scan_capture_atspeed", "SS / FF", "worst/best", "At-speed "
          "capture paths with OCC clocks"],
         ["low_power_mode (DVFS point)", "SS / reduced V", "Cworst",
          "Setup at the lower frequency and voltage"]],
        [2.0, 2.6, 1.4, 2.4], "Table 9.6 - A typical MCMM scenario table "
                              "(voltages and temperatures are examples; "
                              "the real list comes from the foundry "
                              "sign-off guide and the product spec).",
        bold_first=True)
    p("Modern tools analyse all scenarios concurrently. A mid-size SoC "
      "at an advanced node commonly has tens of scenarios; the "
      "implementation flow optimises with a representative subset and "
      "sign-off runs them all.")

    h2("Signal integrity: crosstalk delay and glitch")
    p("Adjacent wires are coupled by sidewall capacitance, which at "
      "advanced nodes is a large share of total wire capacitance. When a "
      "neighbour (**aggressor**) switches at the same time as the "
      "**victim** net:")
    bul(["**Opposite direction**: the effective coupling capacitance is "
         "up to doubled (Miller effect) - the victim slows down: a "
         "positive **delta delay** hurting setup.",
         "**Same direction**: the victim speeds up - negative delta delay "
         "hurting hold.",
         "**Quiet victim**: the aggressor injects a **glitch**. If the "
         "glitch is large and wide enough to propagate through the "
         "receiving gate and reach a flop or a clock/reset pin, it can "
         "flip state - a functional failure with no timing path involved."])
    p("SI-aware STA (PrimeTime SI, Tempus SI) uses coupling capacitances "
      "from SPEF and **timing windows**: an aggressor can only affect a "
      "victim if their switching windows overlap. Fixes are routing-"
      "level: spacing, shielding (especially clocks), layer changes, "
      "upsizing the victim driver, or downsizing aggressors (chapter 17).")

    h2("Hold fixing and timing ECOs")
    p("Setup violations are fixed by making paths faster; hold violations "
      "by making them **slower** - inserting delay cells or buffers on the "
      "data path near the capturing flop, or using slower (high-Vt, "
      "smaller) cells. Rules of thumb:")
    bul(["Fix hold **after CTS**, with propagated clocks: before CTS the "
         "skew is unknown and hold fixes are guesses.",
         "Fix hold at the **fast corner** while checking that the inserted "
         "delay does not break **setup at the slow corner** on the same "
         "path. Paths that fail both are a clock-tree (skew) problem.",
         "Prefer inserting delay at the endpoint side so the fix does not "
         "disturb other paths sharing the start of the path.",
         "Very large hold violations usually mean wrong constraints "
         "(missing clock groups, a multicycle path without -hold) or "
         "huge skew between clocks - fix the cause, not the symptom."])
    p("After sign-off STA, remaining violations are fixed by **timing "
      "ECOs**: the sign-off tool (PrimeTime ECO, Tempus ECO) proposes "
      "cell sizing, Vt swaps, buffer insertion and hold buffers that fit "
      "in the existing placement, writes a change list, and the P&R tool "
      "implements it with minimal disturbance (chapter 19). Late ECOs "
      "prefer **metal-only** changes using pre-placed spare cells.")

    h2("Constraint quality checks")
    checklist("SDC / STA setup quality checklist", [
        "check_timing clean: no unconstrained endpoints, no unclocked "
        "registers, no missing input/output delays, no combinational loops.",
        "Every clock has a defined source, period and waveform; generated "
        "clocks point to the right master and pin; clock relationships "
        "(groups) reviewed with the clocking architect.",
        "Every exception has a written reason and owner; false paths "
        "verified with CDC tool results or formal; wildcards reviewed.",
        "No 'ignored' or 'partially applied' constraints in the tool "
        "reports (objects renamed or removed by synthesis).",
        "I/O delays derived from a documented budget with the neighbouring "
        "block or board; not placeholder 0 or 50% values.",
        "set_case_analysis matches each mode; all modes and corners from "
        "the sign-off plan are present as scenarios.",
        "Design rule limits (max transition/capacitance) set within "
        "library table ranges; no extrapolation warnings.",
        "Correlation: synthesis vs P&R vs sign-off timing within the "
        "agreed margin on a reference set of paths.",
    ])

    h2("Summary")
    bul(["STA builds a timing graph of cell, net and check arcs, propagates "
         "arrival and required times, and proves every path meets setup "
         "and hold without vectors.",
         "Cell delays and slews come from Liberty NLDM tables indexed by "
         "input slew and load, interpolated bilinearly; CCS/ECSM and "
         "effective capacitance improve accuracy with resistive wires.",
         "Setup: L_launch + t_cq + t_logic <= T + L_capture - t_setup - U "
         "(+ CRPR); hold: L_launch + t_cq + t_logic >= L_capture + t_hold "
         "+ U (- CRPR).",
         "Our Python STA on real SKY130 tables found 0.39 ns setup slack "
         "at 1 GHz for a 3-gate path, with clock-to-Q the largest single "
         "delay and NOR rise transitions the slowest gate edge.",
         "Constraints (clocks, I/O delays, exceptions, modes) determine "
         "correctness; every exception is a risk that needs justification.",
         "OCV evolved from flat derates to AOCV and POCV/LVF; sign-off runs "
         "many MCMM scenarios, includes SI delta-delay and glitch, and "
         "closes remaining violations with timing ECOs."])

    h2("Exercises")
    bul(["Using the nand2_1 cell_fall table, interpolate the delay for an "
         "input slew of 0.08 ns and a load of 0.005 pF. Check your result "
         "by running `lookup()` from sta3.py.",
         "Modify sta3.py to give nor2_1 a 20 fF load (a long wire). How do "
         "the nor2 delay, the D slew and the setup time change? Why?",
         "Derive the hold equation for a path where launch and capture "
         "flops are clocked by opposite edges of the same clock.",
         "A path has 20 identical stages with mu = 30 ps and sigma = 3 ps. "
         "Compare the late delay with a flat 8% derate and with POCV at "
         "3 sigma.",
         "Explain why `set_multicycle_path -setup 2` must usually be paired "
         "with `-hold 1`. Draw the default and adjusted check edges.",
         "List four constraint errors that make STA optimistic (silicon "
         "fails although STA passes)."], ordered=True)


# =============================================================================
#     CHAPTER 10 - DESIGN FOR TEST: SCAN, ATPG, COMPRESSION, BIST, ACCESS
# =============================================================================
def _ch10():
    chapter("Design for Test: Scan, ATPG, Compression, BIST and Test Access")
    p("Functional verification (chapter 7) asks whether the **design** is "
      "correct. Manufacturing test asks a different question for every "
      "single die: **was this particular chip built correctly?** A wafer "
      "contains random defects - particles, shorts, opens, voids, "
      "resistive vias - and a fraction of the dies are faulty. Test must "
      "find them quickly and cheaply on automatic test equipment (ATE), "
      "because every defective part that ships becomes a field return. "
      "Design for test (DFT) is the set of structures added to the chip "
      "to make that possible: scan chains, test compression, on-chip "
      "clock controllers, memory and logic BIST, and standard test access "
      "ports.")
    p("DFT is owned by the **DFT engineer / DFT team**: they write the DFT "
      "specification with the architects, insert the structures (usually "
      "during or right after synthesis), generate test patterns with ATPG, "
      "sign off coverage, and hand patterns to the **test/product "
      "engineering** team who run them on the ATE (chapter 21). The "
      "companion RTL Design guide shows scan and BIST from the RTL "
      "designer's perspective; this chapter covers the full DFT "
      "discipline.")

    h2("Why test: defects, faults and quality")
    p("A **defect** is a physical imperfection. A **fault** is a logical "
      "model of the defect's effect that a tool can reason about. A "
      "**failure** is the observable wrong behaviour. Test quality is "
      "measured in defective parts per million shipped (**DPPM**). The "
      "classic Williams-Brown model relates DPPM to yield Y and fault "
      "coverage T:")
    _eqa(["defect level  DL = 1 - Y^(1 - T)",
          "",
          "example: Y = 0.80,  T = 0.99  ->  DL = 1 - 0.8^0.01  = 0.00223  = 2230 DPPM",
          "         Y = 0.80,  T = 0.999 ->  DL = 1 - 0.8^0.001 = 0.000223 =  223 DPPM"],
         "Williams-Brown (1981). Automotive customers typically ask for "
         "single-digit DPPM or 'zero defects' programmes, which is why "
         "their test coverage targets are so high.")
    p("Every tenth of a percent of coverage matters at the high end, "
      "and stuck-at coverage alone is not enough: many real defects in "
      "modern processes are timing-related (resistive opens and vias) and "
      "only show at speed. Hence the portfolio of fault models below.")

    h2("Fault models")
    tbl(["Fault model", "Models", "Test requirement"],
        [["Stuck-at (SA0/SA1)", "A net permanently at 0 or 1 (shorts to "
          "supply, many opens)", "Activate the opposite value, propagate to "
          "an observable point; the workhorse, static patterns"],
         ["Transition (slow-to-rise/fall)", "A node that switches too "
          "slowly (resistive defects)", "Two-pattern test: launch a "
          "transition, capture one functional clock period later (at speed)"],
         ["Path delay", "Accumulated delay along a specific path exceeds the "
          "period", "Sensitise a whole path; used for the critical paths "
          "from STA"],
         ["Bridging", "Two nets shorted (wired-AND, wired-OR, dominant)",
          "Drive the two nets to opposite values; uses layout-extracted "
          "neighbour pairs"],
         ["Cell-aware (CAT)", "Defects **inside** standard cells (transistor "
          "opens/shorts) characterised by SPICE per cell", "Cell-specific "
          "input combinations; catches defects that SA/transition miss"],
         ["IDDQ", "Defects that cause elevated quiescent supply current",
          "Measure current in a static state; less useful at nodes with "
          "high leakage"],
         ["Memory faults", "Stuck cells, transition, coupling, address "
          "decoder, retention", "March algorithms in MBIST (section 10.9)"]],
        [1.8, 3.1, 3.5], "Table 10.1 - Fault models used in production test.",
        bold_first=True)

    h2("Scan design")
    p("The fundamental problem of testing sequential logic is that the "
      "internal state is neither controllable nor observable from the "
      "pins. **Scan** solves it by replacing every flip-flop with a **scan "
      "flip-flop** that has a second data input, and connecting them into "
      "**shift registers (scan chains)** in test mode. Then any state can "
      "be shifted in, one functional clock applied, and the captured "
      "state shifted out: sequential test reduces to combinational test "
      "of the logic between flops.")
    diagram([
        "   Mux-D scan flip-flop (e.g. SKY130 sdfxtp: pins D, SCD = SI, SCE = SE, CLK, Q)",
        "            +-----+",
        "   D  ------|0    |      +--------+",
        "            | MUX |----->| D    Q |----+---> Q  (to functional logic)",
        "   SI ------|1    |      |   FF   |    +---> SO (to SI of the next scan cell)",
        "            +--+--+      |>CK     |",
        "   SE ---------+         +--------+",
        "",
        "   Scan chain: scan_in -> [SFF] -> [SFF] -> [SFF] -> ... -> [SFF] -> scan_out",
        "     SE = 1 (shift):   the chain is a shift register, one bit per clock",
        "     SE = 0 (capture): every SFF loads its functional D (the logic's response)",
    ], "Figure 10.1 - The mux-D scan cell and a scan chain. SE selects "
       "shift (SI) or capture (D).")
    p("The **mux-D** style is used in almost all ASICs. The alternative, "
      "**LSSD** (level-sensitive scan design, from IBM), uses two "
      "non-overlapping scan clocks and latches (master/slave) and is "
      "robust against hold problems but needs more clock routing; it "
      "survives in some high-performance and latch-based designs. "
      "The cost of scan in SKY130 is visible directly in the Liberty file:")
    tbl(["SKY130 hd cell", "Function", "Area (um^{2})", "vs dfxtp_1"],
        [["dfxtp_1", "D flip-flop", "20.02", "-"],
         ["sdfxtp_1", "mux-D scan flip-flop", "26.28", "+31%"],
         ["dfrtp_1", "D flip-flop, async reset", "25.02", "+25%"],
         ["sdfrtp_1", "scan flip-flop, async reset", "31.28", "+56%"],
         ["dlclkp_1 / sdlclkp_1", "ICG / ICG with scan enable", "17.52 / 18.77",
          "-"]],
        [1.8, 2.8, 1.5, 1.2], "Table 10.2 - Scan overhead read from the "
                              "real SKY130 tt Liberty file (area "
                              "attribute).", bold_first=True)
    p("With flops often making up roughly 30-50% of logic area in SoC blocks, scan "
      "replacement alone costs on the order of 5-15% of standard-cell "
      "area in this library, plus the scan-enable tree and a small "
      "delay (the mux) on every flop's D path.")

    h2("Scan chains, shift and capture")
    diagram([
        "  SE      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~____________~~~~~~~~~~~~~~~~~~~~~",
        "  CLK     _|~|_|~|_|~|_ ... _|~|_|~|_______|~|________|~|_|~|_ ...",
        "           <--- shift L cycles (slow) --->    capture   <--- shift out L --->",
        "           load pattern k                  (1 pulse,    unload response k while",
        "                                            or 2 at-    loading pattern k+1",
        "                                            speed)",
    ], "Figure 10.2 - Scan test protocol. Unload of pattern k overlaps "
       "with load of pattern k+1, so each pattern costs about L shift "
       "cycles plus capture.")
    bul(["**Chain count and length** trade tester pins against test time: "
         "N scan cells split into c chains need about N/c shift cycles per "
         "pattern. Chains are balanced to equal length.",
         "**Shift frequency** is limited by scan-path timing and by shift "
         "power (section 10.14) - typically tens of MHz, well below "
         "functional speed.",
         "**Chain ordering** is done by the P&R tool after placement "
         "(scan reordering using SCANDEF) to minimise wiring; the netlist "
         "order from synthesis is only a starting point.",
         "**Lockup latches** are inserted where a chain crosses from one "
         "clock domain or clock-tree branch to another, to avoid hold "
         "violations in shift.",
         "**Scan-enable** is a high-fanout net treated almost like a "
         "clock: buffered, and sometimes pipelined for at-speed tests."])

    h2("At-speed test: launch-on-capture, launch-on-shift and OCCs")
    p("Transition and path-delay faults need two patterns: the first "
      "sets up the initial value, the second **launches** a transition, "
      "and the result is **captured** exactly one functional period "
      "later. Two launch styles exist:")
    tbl(["Style", "How the launch happens", "Pros", "Cons"],
        [["Launch-on-capture (LOC, 'broadside')", "Shift slowly, then two "
          "fast functional clock pulses: the first launches from the "
          "functional response, the second captures",
          "SE can be slow (not timed at speed); standard in industry",
          "Launch values restricted to functional responses: more patterns, "
          "somewhat lower coverage"],
         ["Launch-on-shift (LOS, 'skewed-load')", "The last shift pulse "
          "launches; SE drops within one fast cycle; next pulse captures",
          "Higher coverage, fewer patterns", "SE must switch at speed: "
          "timing-critical global net; may test non-functional paths"]],
        [1.7, 2.8, 1.9, 2.4], "Table 10.3 - At-speed launch styles.",
        bold_first=True)
    p("Testers cannot deliver GHz clocks with exact two-pulse bursts to "
      "every domain. The chip uses its own PLL, and an **on-chip clock "
      "controller (OCC)** per clock domain chooses between the slow "
      "shift clock from the tester and a burst of exactly N at-speed PLL "
      "pulses for capture, triggered by the tester.")
    diagram([
        "              +-----------------------------------------------+",
        "  PLL clk --->| sync + pulse counter (programmable 1..N pulses)|",
        "  ATE shift ->| glitch-free clock mux                          |---> domain clock",
        "  scan_en --->| control: shift -> slow clk, capture -> burst   |     (to CTS root)",
        "  test_mode ->| functional mode: PLL clock straight through    |",
        "              +-----------------------------------------------+",
    ], "Figure 10.3 - An OCC sits at the root of each clock domain; it is "
       "part of the clock architecture and must be planned with the "
       "clocking and CTS teams.")

    h2("ATPG: automatic test pattern generation")
    p("For each fault, ATPG must find an input pattern (scan state plus "
      "primary inputs) that **activates** the fault (drives the faulty net "
      "to the opposite of the stuck value) and **propagates** the "
      "difference to an observable scan cell or output. Classic "
      "algorithms:")
    bul(["**D-algorithm** (Roth, 1966): uses the 5-valued algebra {0, 1, X, "
         "D, D-bar}, where D means '1 in the good circuit, 0 in the faulty "
         "one'. It drives D forward (D-frontier) and justifies required "
         "values backward, backtracking on conflicts.",
         "**PODEM** (Goel, 1981): searches only over **primary input** "
         "assignments, simulating forward after each decision - a much "
         "smaller search space; the basis of most later algorithms (FAN, "
         "SOCRATES), now combined with SAT solvers.",
         "**Fault simulation** does the bulk of the work: every generated "
         "pattern is simulated against all remaining faults, and every "
         "fault it happens to detect is dropped. Random patterns first "
         "detect the easy faults cheaply; deterministic ATPG targets the "
         "rest.",
         "**Compaction**: static (merge compatible patterns) and dynamic "
         "(fill don't-care bits of a pattern to target more faults) keep "
         "the pattern count low."])
    p("The Python model below does all of this on two small circuits: "
      "ISCAS-85 **c17** (6 NAND gates) and a function with a redundant "
      "consensus term, f = ab + a'c + bc. It enumerates single stuck-at "
      "faults on every net (stems only, for brevity - real tools also "
      "model fanout branches and collapse equivalent faults), applies "
      "random patterns with fault dropping, then tops up with a "
      "deterministic search, which here is exhaustive because the "
      "circuits are tiny; real ATPG uses PODEM/SAT-style search.")
    code([
        '# faultsim.py - single stuck-at fault simulation + a brute-force "ATPG" top-up',
        'import random, itertools',
        'C17 = [("n10", "NAND", "i1", "i3"), ("n11", "NAND", "i3", "i6"),     # ISCAS-85 c17',
        '       ("n16", "NAND", "i2", "n11"), ("n19", "NAND", "n11", "i7"),',
        '       ("o22", "NAND", "n10", "n16"), ("o23", "NAND", "n16", "n19")]',
        'CONS = [("t1", "AND", "a", "b"), ("na", "NOT", "a", None),            # f = ab + a\'c + bc',
        '        ("t2", "AND", "na", "c"), ("t3", "AND", "b", "c"),            # (bc is redundant:',
        '        ("t4", "OR", "t1", "t2"), ("f", "OR", "t4", "t3")]            #  consensus term)',
        'OPS = {"NAND": lambda x, y: 1 - (x & y), "AND": lambda x, y: x & y,',
        '       "OR": lambda x, y: x | y, "NOT": lambda x, y: 1 - x}',
        '',
        'def simulate(ckt, pis, vec, fault=None):          # fault = (net, stuck_value)',
        '    v = dict(zip(pis, vec))',
        '    if fault and fault[0] in v: v[fault[0]] = fault[1]',
        '    for out, op, a, b in ckt:',
        '        v[out] = OPS[op](v[a], v[b] if b else 0)',
        '        if fault and fault[0] == out: v[out] = fault[1]',
        '    return v',
        '',
        'def run(name, ckt, pis, pos, n_random, seed=1):',
        '    nets = pis + [g[0] for g in ckt]',
        '    faults = [(n, s) for n in nets for s in (0, 1)]',
        '    good = lambda vec: [simulate(ckt, pis, vec)[o] for o in pos]',
        '    detects = lambda vec, f: good(vec) != [simulate(ckt, pis, vec, f)[o] for o in pos]',
        '    rng, left, pats = random.Random(seed), set(faults), []',
        '    print("%s: %d nets, %d stuck-at faults, %d PIs, %d POs" %',
        '          (name, len(nets), len(faults), len(pis), len(pos)))',
        '    for k in range(1, n_random + 1):                # random-pattern phase',
        '        vec = [rng.randint(0, 1) for _ in pis]',
        '        hit = {f for f in left if detects(vec, f)}',
        '        if hit: pats.append(vec); left -= hit',
        '        print("  random pattern %d %s  detected %2d new  FC=%5.1f%%" %',
        '              (k, "".join(map(str, vec)), len(hit), 100 * (1 - len(left) / len(faults))))',
        '    redundant = []',
        '    for f in sorted(left):                          # deterministic top-up (exhaustive)',
        '        if f not in left: continue                  # already caught by a top-up pattern',
        '        vec = next((list(v) for v in itertools.product((0, 1), repeat=len(pis))',
        '                    if detects(list(v), f)), None)',
        '        if vec is None: redundant.append(f); continue',
        '        pats.append(vec); left -= {g for g in left if detects(vec, g)}',
        '        print("  ATPG top-up for %s/SA%d: %s" % (f[0], f[1], "".join(map(str, vec))))',
        '    fc = 100 * (len(faults) - len(left)) / len(faults)',
        '    tc = 100 * (len(faults) - len(left)) / (len(faults) - len(redundant))',
        '    print("  patterns=%d  untestable(redundant)=%s" % (len(pats), redundant or "none"))',
        '    print("  fault coverage=%.1f%%  test coverage=%.1f%%\\n" % (fc, tc))',
        '',
        'run("c17", C17, ["i1", "i2", "i3", "i6", "i7"], ["o22", "o23"], n_random=4)',
        'run("consensus", CONS, ["a", "b", "c"], ["f"], n_random=3)',
    ], "faultsim.py - fault list, fault simulation with fault dropping, "
       "deterministic top-up and redundancy identification.")
    out([
        'c17: 11 nets, 22 stuck-at faults, 5 PIs, 2 POs',
        '  random pattern 1 00101  detected 10 new  FC= 45.5%',
        '  random pattern 2 11100  detected  3 new  FC= 59.1%',
        '  random pattern 3 10110  detected  5 new  FC= 81.8%',
        '  random pattern 4 11001  detected  0 new  FC= 81.8%',
        '  ATPG top-up for i3/SA1: 00011',
        '  ATPG top-up for i6/SA0: 00111',
        '  ATPG top-up for i7/SA1: 00000',
        '  patterns=6  untestable(redundant)=none',
        '  fault coverage=100.0%  test coverage=100.0%',
        '',
        'consensus: 9 nets, 18 stuck-at faults, 3 PIs, 1 POs',
        '  random pattern 1 001  detected  6 new  FC= 33.3%',
        '  random pattern 2 011  detected  0 new  FC= 33.3%',
        '  random pattern 3 110  detected  3 new  FC= 50.0%',
        '  ATPG top-up for b/SA1: 100',
        '  ATPG top-up for c/SA1: 000',
        '  ATPG top-up for na/SA1: 101',
        "  patterns=5  untestable(redundant)=[('t3', 0)]",
        '  fault coverage=94.4%  test coverage=100.0%',
    ], "Real output of faultsim.py.")
    bul(["Random patterns reached 82% coverage on c17 with three patterns; "
         "the fourth random pattern detected nothing new - the typical "
         "saturation of random testing. Three deterministic patterns closed "
         "the rest: **6 patterns for 22 faults**.",
         "In the consensus circuit, **t3 stuck-at-0 is undetectable**: the "
         "term bc is logically redundant (ab + a'c already covers it), so "
         "no input can show a difference. ATPG proves such faults "
         "**untestable (redundant)**; they lower fault coverage but not "
         "test coverage.",
         "Redundant logic is a design smell: besides costing area it hides "
         "defects. (Here the consensus term is sometimes intentional - it "
         "removes a static hazard - which is why test coverage excludes "
         "provably untestable faults.)"])

    h2("Fault coverage versus test coverage")
    _eqa(["fault coverage FC = detected / total faults",
          "test coverage  TC = detected / (total faults - untestable faults)",
          "",
          "consensus example:  FC = 17/18 = 94.4 %    TC = 17/17 = 100 %",
          "",
          "ATPG fault classes: DT detected, PT possibly detected (X at output),",
          "AU ATPG-untestable (constraints), UD undetectable (redundant, tied, unused),",
          "ND not detected (aborted / no pattern found)"],
         "Coverage definitions. Tool vendors differ slightly in how "
         "possibly-detected and ATPG-untestable faults are credited; "
         "always state the definition when quoting a number.")
    p("Sign-off targets are project-specific. Commonly quoted ranges are "
      "stuck-at test coverage above about 98-99% and transition coverage "
      "above about 90-95% for consumer products, with automotive "
      "(AEC-Q100 / ISO 26262 contexts) pushing higher and adding cell-"
      "aware and in-system test requirements.")

    h2("Test compression")
    p("A modern SoC has millions of scan cells. Without compression, "
      "test data volume and ATE time explode. **Compression** puts a "
      "**decompressor** between a few scan-in pins and hundreds of short "
      "internal chains, and a **compactor** (XOR tree / MISR) between the "
      "chains and the scan-out pins. It works because ATPG patterns are "
      "mostly don't-care bits: typically only a few percent of bits in a "
      "pattern are specified.")
    diagram([
        "  tester: 16 scan-in pins                                 16 scan-out pins",
        "     |                                                          ^",
        "     v                                                          |",
        "  +--------------+   400 short internal chains    +----------------------+",
        "  | decompressor |==> [SFF]-[SFF]-...-[SFF] ====> | compactor (XOR tree) |",
        "  | (LFSR/ring   |==> [SFF]-[SFF]-...-[SFF] ====> |  + X-masking logic   |",
        "  |  + phase    |==>        ...                   |                      |",
        "  |  shifter)   |==> [SFF]-[SFF]-...-[SFF] ====> |                      |",
        "  +--------------+                                 +----------------------+",
    ], "Figure 10.4 - Scan compression architecture (e.g. Siemens Tessent "
       "TestKompress/EDT, Synopsys DFTMAX / TestMAX, Cadence Modus).")
    bul(["**EDT** (embedded deterministic test) solves linear equations so "
         "that the decompressor produces the specified care bits; DFTMAX "
         "uses a combinational broadcast/mux network plus sequential "
         "variants. Compression ratios of tens to over a hundred are "
         "common.",
         "**X-masking**: unknown values (uninitialised memories, analog "
         "outputs, false/multicycle paths captured at speed, bus contention) "
         "corrupt the compactor output; X-sources must be bounded in the "
         "design or masked per pattern, otherwise compression and coverage "
         "collapse.",
         "Compression slightly increases pattern count (encoding "
         "limitations) but reduces data and time by roughly the chain-"
         "length ratio."])
    p("The arithmetic of test time and data volume, for a 2-million-flop "
      "design with 12,000 patterns, 16 scan-in and 16 scan-out pins at "
      "50 MHz shift:")
    code([
        '# testtime.py - scan test time and data volume, with and without compression',
        'import math',
        'FLOPS, PATTERNS, F_SHIFT = 2_000_000, 12_000, 50e6   # scan cells, ATPG patterns, Hz',
        'SCAN_PINS, COST_PER_S = 16, 0.03                     # scan-in pins (= scan-out), $/s tester',
        'def report(name, chains, pin_pairs):',
        '    L = math.ceil(FLOPS / chains)                    # longest chain length',
        '    cycles = (PATTERNS + 1) * L + PATTERNS * 4       # shift in/out overlapped + capture',
        '    t = cycles / F_SHIFT',
        '    vol = 2 * PATTERNS * L * pin_pairs / 8 / 2**20   # stimulus + expected response, MiB',
        '    print("%-16s chains=%5d L=%6d cycles=%10d t=%6.3f s $%.3f data=%6.1f MiB"',
        '          % (name, chains, L, cycles, t, t * COST_PER_S, vol))',
        '    return t',
        't0 = report("no compression", SCAN_PINS, SCAN_PINS)',
        'for ratio in (25, 50, 100):',
        '    t = report("compressed %3dx" % ratio, SCAN_PINS * ratio, SCAN_PINS)',
        '    print("%-16s -> test time and data volume reduced %.0fx" % ("", t0 / t))',
    ], "testtime.py - shift cycles, test time, tester cost and data volume "
       "(the tester cost per second is an assumed example value).")
    out([
        'no compression   chains=   16 L=125000 cycles=1500173000 t=30.003 s $0.900 data=5722.0 MiB',
        'compressed  25x  chains=  400 L=  5000 cycles=  60053000 t= 1.201 s $0.036 data= 228.9 MiB',
        '                 -> test time and data volume reduced 25x',
        'compressed  50x  chains=  800 L=  2500 cycles=  30050500 t= 0.601 s $0.018 data= 114.4 MiB',
        '                 -> test time and data volume reduced 50x',
        'compressed 100x  chains= 1600 L=  1250 cycles=  15049250 t= 0.301 s $0.009 data=  57.2 MiB',
        '                 -> test time and data volume reduced 100x',
    ], "Real output of testtime.py.")
    p("Without compression the test would take 30 s per die and 5.6 GiB "
      "of vector memory - far beyond any production budget, where logic "
      "scan time is typically a fraction of a second to a few seconds. "
      "100x compression brings it to 0.3 s. In reality compressed pattern "
      "counts grow somewhat, and at-speed (transition) patterns are "
      "usually several times more numerous than stuck-at patterns, so "
      "both sets are budgeted separately.")

    h2("Memory BIST and repair")
    p("Embedded SRAMs often occupy a large share of SoC area and have "
      "the densest layout on the die, so they have the highest defect "
      "density. They are tested by **memory BIST (MBIST)**: an on-chip "
      "controller generates addresses and data, runs **March algorithms** "
      "and compares read data, at full speed, with only a few control "
      "pins. A March test is a sequence of **March elements**, each "
      "visiting every address in ascending or descending order and "
      "applying a fixed sequence of reads and writes.")
    code([
        '# march.py - March C- on a 16-word x 1-bit memory model with injected faults',
        'N = 16',
        'MARCH_CM = [("up", ["w0"]), ("up", ["r0", "w1"]), ("up", ["r1", "w0"]),',
        '            ("down", ["r0", "w1"]), ("down", ["r1", "w0"]), ("any", ["r0"])]',
        'class Mem:',
        '    def __init__(s, fault=None): s.m, s.f = [0] * N, fault or {}',
        '    def write(s, a, v):',
        '        if s.f.get("saf") == (a, 1 - v): v = 1 - v            # stuck-at cell',
        '        if s.f.get("tf") == (a, v) and s.m[a] != v: return    # transition fault',
        '        old, s.m[a] = s.m[a], v',
        '        c = s.f.get("cfin")                                   # inversion coupling:',
        '        if c and c[0] == a and old == 0 and v == 1:           # aggressor 0->1 flips victim',
        '            s.m[c[1]] ^= 1',
        '    def read(s, a): return s.m[a]',
        'def march(mem):',
        '    for order, ops in MARCH_CM:',
        '        addrs = range(N - 1, -1, -1) if order == "down" else range(N)',
        '        for a in addrs:',
        '            for op in ops:',
        '                if op[0] == "w": mem.write(a, int(op[1]))',
        '                elif mem.read(a) != int(op[1]): return "FAIL at addr %2d, op %s" % (a, op)',
        '    return "pass"',
        'print("March C- = {up(w0); up(r0,w1); up(r1,w0); dn(r0,w1); dn(r1,w0); any(r0)}: 10N ops")',
        'for name, f in [("fault-free", None), ("stuck-at-0 cell 5", {"saf": (5, 0)}),',
        '                ("stuck-at-1 cell 9", {"saf": (9, 1)}),',
        '                ("up-transition fault cell 3", {"tf": (3, 1)}),',
        '                ("coupling 2 -> 11 (aggr. lower)", {"cfin": (2, 11)}),',
        '                ("coupling 12 -> 4 (aggr. higher)", {"cfin": (12, 4)})]:',
        '    print("  %-32s %s" % (name, march(Mem(f))))',
    ], "march.py - March C- on a behavioural memory with injected "
       "stuck-at, transition and inversion-coupling faults.")
    out([
        'March C- = {up(w0); up(r0,w1); up(r1,w0); dn(r0,w1); dn(r1,w0); any(r0)}: 10N ops',
        '  fault-free                       pass',
        '  stuck-at-0 cell 5                FAIL at addr  5, op r1',
        '  stuck-at-1 cell 9                FAIL at addr  9, op r0',
        '  up-transition fault cell 3       FAIL at addr  3, op r1',
        '  coupling 2 -> 11 (aggr. lower)   FAIL at addr 11, op r0',
        '  coupling 12 -> 4 (aggr. higher)  FAIL at addr  4, op r1',
    ], "Real output of march.py: every injected fault is detected, and the "
       "failing address and operation are reported (the basis for repair "
       "analysis).")
    p("March C- needs 10 operations per address (10N) and detects "
      "stuck-at, transition, address-decoder and a large class of coupling "
      "faults - note that the coupling fault with the aggressor at a "
      "**higher** address is caught by a descending element. Production "
      "MBIST uses several algorithms (March C-, March LR, checkerboards, "
      "retention tests with pauses) selected per memory type.")
    h3("Repair")
    bul(["Large memories include **redundant rows and/or columns**. "
         "MBIST with **built-in redundancy analysis (BIRA)** collects the "
         "failing addresses and computes a repair solution.",
         "The solution is programmed into **fuses** (laser fuses in older "
         "technologies, **eFuses** or anti-fuse OTP today) at wafer test. "
         "At every power-up a fuse controller reads the fuse box and "
         "shifts the repair data into each memory's repair register "
         "before the memories are used (**soft repair** can also be done "
         "at every boot without fuses).",
         "Repair turns memory defects from yield loss into good dies; for "
         "large-memory SoCs it is a first-order yield lever (chapter 21)."])

    h2("Logic BIST")
    p("**Logic BIST (LBIST)** tests the logic without an external "
      "tester: a **PRPG** (pseudo-random pattern generator, an LFSR) "
      "feeds the scan chains, a **MISR** (multiple-input signature "
      "register) compacts the responses, and at the end the signature "
      "is compared with the expected golden value.")
    diagram([
        "  +-------+  phase   +--------------------+       +------+",
        "  | PRPG  |--shifter>|  scan chains (CUT) |------>| MISR |---> signature == golden ?",
        "  | (LFSR)|          |  + test points     |       +------+",
        "  +-------+          +--------------------+",
        "      ^                        ^                        ",
        "      +----- LBIST controller: pattern counter, OCC capture control, X-bounding",
    ], "Figure 10.5 - Logic BIST architecture.")
    bul(["Used where in-field or power-on self-test is required: "
         "**automotive functional safety (ISO 26262)** requires periodic "
         "latent-fault checks, and LBIST at key-on/key-off is a standard "
         "safety mechanism.",
         "Random patterns miss **random-pattern-resistant faults** (wide "
         "AND/OR cones). **Test points** (control and observe points) are "
         "inserted to raise coverage.",
         "Any X reaching the MISR corrupts the signature, so LBIST requires "
         "strict **X-bounding** of memories, analog blocks and non-scan "
         "flops.",
         "Hybrid schemes use the same compression logic for both ATPG and "
         "LBIST."])

    h2("Test access: IEEE 1149.1, 1500 and 1687")
    tbl(["Standard", "Purpose", "Key elements"],
        [["IEEE 1149.1 (JTAG, boundary scan)", "Board-level interconnect "
          "test and a standard chip test/debug port", "TAP with TCK, TMS, "
          "TDI, TDO (optional TRST); 16-state TAP controller; instruction "
          "register; boundary-scan cells on I/Os; instructions such as "
          "BYPASS, EXTEST, SAMPLE/PRELOAD, IDCODE"],
         ["IEEE 1149.6", "AC-coupled and differential I/O test",
          "Extension of 1149.1 for high-speed links"],
         ["IEEE 1500", "Core-level test wrapper for embedded IP",
          "Wrapper boundary register, wrapper instruction register, serial "
          "and parallel test access; isolates a core for test"],
         ["IEEE 1687 (IJTAG)", "Access to embedded instruments (BIST "
          "controllers, sensors, PLL test)", "ICL (instrument connectivity "
          "language), PDL (procedural description language), segment "
          "insertion bits (SIBs) for reconfigurable scan networks"]],
        [2.0, 2.6, 4.0], "Table 10.4 - Test-access standards.",
        bold_first=True)
    diagram([
        "            TDI --> [ boundary-scan register around all I/O pads ] --> TDO",
        "  chip   TMS,TCK --> [ TAP controller ] --> [ instruction register ]",
        "                          |",
        "                          +--> IJTAG network (SIBs) --> MBIST ctrl, LBIST, PLL,",
        "                          |                            temperature sensors, eFuse",
        "                          +--> IEEE 1500 wrappers around cores (core test)",
    ], "Figure 10.6 - Test access built around the JTAG TAP.")

    h2("Test modes and pin muxing")
    p("A chip has far fewer pins available for test than it has test "
      "features, so functional pins are shared. A **test-mode controller** "
      "(entered via TAP instructions or dedicated test pins, usually "
      "locked after production for security) configures the chip:")
    tbl(["Mode", "Pin usage", "Notes"],
        [["Functional (mission)", "All pins functional", "DFT logic "
          "transparent; must be proven by LEC/STA in this mode"],
         ["Scan (stuck-at / at-speed)", "GPIOs become scan-in/out, SE, "
          "test clocks", "Compression active; OCCs control capture"],
         ["MBIST", "JTAG only", "Controller runs algorithms, reports "
          "pass/fail and repair"],
         ["Boundary scan", "JTAG + all I/O boundary cells", "Board test "
          "(EXTEST)"],
         ["IDDQ / burn-in / characterisation", "Special", "Static states, "
          "stress modes"],
         ["Debug / secure lock", "JTAG, trace", "Debug must be disabled or "
          "authenticated in production parts (security)"]],
        [2.0, 2.8, 3.4], "Table 10.5 - Typical test modes.", bold_first=True)
    box("warn", "PITFALL - DFT pins that nobody timed",
        ["Scan-out pins multiplexed onto GPIOs add a mux in the functional "
         "path; test clocks enter through functional input pads; OCC "
         "muxes sit in the clock tree. Each test mode needs its own SDC "
         "and STA scenario (chapter 9, Table 9.6). Missing test-mode "
         "constraints are a classic reason why first-silicon scan fails "
         "while functional mode works."])

    h2("DFT sign-off")
    checklist("DFT sign-off checklist", [
        "DFT DRC clean (or waived): all flops scannable, clocks and resets "
        "controllable, no combinational loops, X-sources bounded.",
        "Scan chains traced and verified in the final netlist (after "
        "reordering); chain lengths balanced; lockup latches present.",
        "Stuck-at, transition (and, if required, cell-aware, path-delay, "
        "bridging) coverage at target; untestable faults reviewed.",
        "Pattern counts and test time within budget; data volume fits the "
        "tester memory.",
        "Patterns simulated on the post-layout netlist with SDF at min "
        "and max corners (serial and parallel load); no mismatches.",
        "MBIST: all memories covered, algorithms reviewed, repair flow "
        "verified end-to-end including fuse programming and reload.",
        "LBIST (if present): signature stable across corners, X-bounding "
        "verified.",
        "Test modes: STA scenarios for shift and capture clean; LEC in "
        "functional mode clean; boundary scan BSDL generated and verified.",
        "Test-power analysis: shift and capture IR drop within limits "
        "(chapter 18).",
    ])

    h2("DFT impact on area, timing and power")
    tbl(["Aspect", "Impact", "Mitigation"],
        [["Area", "Scan flops (+31% per flop in SKY130), compression "
          "logic, OCCs, MBIST controllers and wrappers, TAP; commonly a "
          "few percent to over ten percent of logic area",
          "Share MBIST controllers; use compression to reduce pins, not "
          "logic"],
         ["Timing", "Scan mux on every D input; SE tree; OCC muxes in the "
          "clock path; wrapper muxes on memory interfaces",
          "Scan-aware synthesis (map to scan flops from the start); "
          "timing-aware chain ordering"],
         ["Shift power", "In shift, a large fraction of flops toggle every "
          "cycle - far more than in functional operation - causing IR drop "
          "and heating", "Lower shift frequency, low-power fill of don't-"
          "care bits (fill with adjacent values), gating flop outputs "
          "during shift, staggered chain groups"],
         ["Capture power", "At-speed capture of random patterns can switch "
          "more logic than any real workload: IR drop slows paths and "
          "causes false failures (yield loss)", "Power-aware ATPG "
          "(switching limits per pattern), clock-domain staggering, "
          "IR-drop-aware pattern validation"]],
        [1.3, 4.0, 3.2], "Table 10.6 - The cost of DFT.", bold_first=True)
    box("expert", "INTERVIEW INSIGHT - the most asked DFT questions",
        ["Why is launch-on-shift harder to implement than launch-on-capture? "
         "(Scan-enable must switch at functional speed.) Why do we need "
         "lockup latches? (To avoid shift hold violations across clock "
         "skews.) Why can scan cause yield loss? (Test power - IR drop in "
         "capture slows paths that are fine in the application.) What is "
         "the difference between fault coverage and test coverage? "
         "(Whether provably untestable faults are in the denominator.) "
         "Be ready to draw a scan cell, a scan chain waveform and an OCC."])

    h2("Summary")
    bul(["Test detects manufacturing defects in every die; quality is "
         "measured in DPPM and follows DL = 1 - Y^(1-T).",
         "Fault models: stuck-at, transition, path delay, bridging, "
         "cell-aware, IDDQ and memory faults, each with its own pattern "
         "type.",
         "Scan turns sequential test into combinational test; in SKY130 a "
         "scan flop costs 31% more area than a plain flop.",
         "At-speed test uses LOC or LOS launch with OCCs delivering PLL "
         "pulse bursts.",
         "ATPG = fault activation + propagation (D-algorithm, PODEM, SAT) "
         "plus fault simulation; our model reached 100% test coverage on "
         "c17 with 6 patterns and found the redundant consensus fault.",
         "Compression (EDT, DFTMAX) cut our 2M-flop example from 30 s to "
         "0.3 s of scan time; X-sources must be bounded or masked.",
         "MBIST with March algorithms, repair via eFuses, LBIST with "
         "PRPG/MISR, and IEEE 1149.1/1500/1687 access complete the DFT "
         "architecture; DFT sign-off covers DRC, coverage, patterns, "
         "timing modes and test power."])

    h2("Exercises")
    bul(["A product has 85% yield. What test coverage is needed for 100 "
         "DPPM according to Williams-Brown? For 10 DPPM?",
         "Extend faultsim.py to model fanout branches of c17 separately "
         "(e.g. i3 feeds two gates). How many faults are there now, and "
         "does the pattern count change?",
         "Using testtime.py, find the compression ratio needed to bring "
         "scan time below 0.5 s when the pattern count grows by 30% "
         "with compression.",
         "Show a coupling fault that March C- detects only with the "
         "descending elements, and explain why both address orders are "
         "needed.",
         "Explain why an uninitialised SRAM output reaching a compactor "
         "destroys coverage, and give two design fixes.",
         "Compare LOC and LOS: draw the SE and CLK waveforms for each and "
         "state which paths each can test that the other cannot."],
        ordered=True)


# =============================================================================
#                                  PART II
# =============================================================================
def part2():
    part("Front-End Design",
         "From RTL that the back end can implement, through verification "
         "strategy and sign-off, logic synthesis and static timing "
         "analysis, to design for test - the steps that turn an "
         "architecture into a verified, timed, testable netlist.")
    _ch6()
    _ch7()
    _ch8()
    _ch9()
    _ch10()
