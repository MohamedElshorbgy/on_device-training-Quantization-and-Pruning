"""Part IV - Implementation-Aware RTL (Chapters 17-21).

Every synthesizable Verilog example and testbench in this part was compiled
with Icarus Verilog 12 (iverilog -g2012 -Wall) and the out() cards are pasted
from the actual vvp runs. SDC, UPF and Tcl scripts are shown without
simulation.
"""

from rtl_guide.common import *  # noqa: F401,F403


def _eqa(lines, caption=None):
    """eq() centres each line; pad them to one width so columns stay aligned."""
    w = max(len(l) for l in lines)
    eq([l.ljust(w) for l in lines], caption)


# =============================================================================
#                 CHAPTER 17 - LOGIC SYNTHESIS: WHAT YOUR RTL BECOMES
# =============================================================================
def _ch17():
    chapter("Logic Synthesis: What Your RTL Becomes", newpage=False)
    p("Up to now the book has treated RTL as a description of behaviour that "
      "a simulator executes. From this chapter on we look at the other "
      "consumer of your code - the **synthesis tool** - which reads exactly "
      "the same text and turns it into a netlist of standard cells: NAND "
      "gates, flip-flops, multiplexers and adders drawn from a library "
      "characterised by the foundry. The simulator and the synthesis tool do "
      "not interpret your code in the same way, and almost every expensive "
      "RTL bug in industry lives in the gap between them.")
    p("A good RTL designer can look at any `always` block and sketch the "
      "gates it will become, estimate their delay to within a factor of two, "
      "and predict which lines will produce warnings. This chapter builds "
      "that skill: the steps inside a synthesis tool, the library it maps "
      "to, what each coding idiom infers, what synthesis silently ignores, "
      "and how to read the reports that tell you whether your design is any "
      "good.")

    h2("The synthesis pipeline")
    diagram([
        "   RTL (.sv/.v)     constraints (.sdc)      libraries (.lib/.db, LEF)",
        "        |                  |                          |",
        "        v                  |                          |",
        "  +-------------+          |                          |",
        "  | 1. analyze  |  parse, syntax + semantic checks   |",
        "  +-------------+          |                          |",
        "        v                  |                          |",
        "  +-------------+          |                          |",
        "  | 2. elaborate|  resolve params/generate, build hierarchy,",
        "  |             |  infer flops/latches/memories, operators -> generic",
        "  +-------------+  (GTECH in DC, 'generic gates' in Genus, $-cells in Yosys)",
        "        v                  v                          |",
        "  +--------------------------------+                  |",
        "  | 3. high-level optimization     |  constant propagation, resource",
        "  |    (technology independent)    |  sharing, FSM extraction, datapath",
        "  +--------------------------------+  architecture selection",
        "        v                                             v",
        "  +--------------------------------+  +-----------------------------+",
        "  | 4. technology mapping          |<-| std cells: NAND2X1, DFFRX2, |",
        "  |    generic gates -> real cells |  | AOI22X1, ICG, MUX2X4 ...    |",
        "  +--------------------------------+  +-----------------------------+",
        "        v",
        "  +--------------------------------+",
        "  | 5. timing/area/power opt.      |  sizing, buffering, Vt swap,",
        "  |    (incremental, constraint-   |  restructuring, clock gating,",
        "  |     driven)                    |  scan-flop substitution",
        "  +--------------------------------+",
        "        v",
        "  gate-level netlist (.v) + SDC out + reports (timing, area, power, QoR)",
    ], "Figure 17.1 - The stages every synthesis tool goes through. Steps 3-5 "
       "are iterated and interleaved in modern tools, but the conceptual split "
       "is the same in Design Compiler, Genus and Yosys.")
    tbl(["Step", "What happens", "What you see if your RTL is wrong"],
        [["Analyze", "Lexing and parsing of each file; per-file semantic "
          "checks; results stored in a work library",
          "Syntax errors, undeclared identifiers (with `default_nettype "
          "none`), illegal SV constructs for that tool"],
         ["Elaborate", "Top-down instantiation: parameters resolved, "
          "`generate` expanded, every `always` block analysed for its "
          "storage type; arithmetic becomes generic operators",
          "'Latch inferred', 'multiple drivers', 'width mismatch', "
          "'unresolved module', 'combinational loop'"],
         ["High-level optimization", "Constants propagated, unused logic "
          "removed, common subexpressions shared, adder/multiplier "
          "architectures chosen (ripple, carry-lookahead, Booth/Wallace)",
          "Registers 'removed because constant' or 'unloaded' - often a "
          "sign of a missing connection"],
         ["Technology mapping", "Generic logic covered by cells from the "
          "target library, minimising a cost function (delay, area)",
          "Unmapped cells (a `dont_use` list too strict); huge area from a "
          "`/` or `%` by a variable"],
         ["Optimization", "Constraint-driven: upsizing cells on critical "
          "paths, buffering high fanout, restructuring, swapping Vt "
          "flavours, inserting ICGs, replacing flops with scan flops",
          "Negative slack that the tool cannot fix - the fix is in the RTL "
          "(Chapter 18)"]],
        widths=[16, 44, 40], bold_first=True)
    box("key", "Synthesis is constraint-driven",
        "Without an SDC file a synthesis tool has no notion of 'fast enough' "
        "and will produce a small, slow netlist. With a clock period it "
        "trades area for speed only on paths that need it. This is why the "
        "same RTL can produce a 20k-gate block at 200 MHz and a 35k-gate "
        "block at 800 MHz, and why area numbers quoted without a frequency "
        "are meaningless.")

    h2("Standard-cell libraries: what the tool maps to")
    p("The target of mapping is a **standard-cell library**: a few hundred "
      "to a few thousand pre-designed, pre-characterised cells of equal "
      "height that abut in rows. The foundry or an IP vendor provides each "
      "cell in several views; synthesis reads the **Liberty** (`.lib`, "
      "compiled to `.db` for Synopsys tools) timing and power model, and "
      "physically-aware synthesis additionally reads **LEF** (abstract "
      "layout) and technology files.")
    code(r'''cell (NAND2X1) {
  area : 0.532 ;
  pin (A) { direction : input ; capacitance : 0.0012 ; }
  pin (B) { direction : input ; capacitance : 0.0013 ; }
  pin (Y) {
    direction : output ;
    function  : "!(A & B)" ;
    timing () {
      related_pin : "A" ;
      timing_sense : negative_unate ;
      cell_rise (delay_template_5x5) {          /* NLDM table */
        index_1 ("0.01, 0.03, 0.08, 0.20, 0.50"); /* input slew, ns */
        index_2 ("0.001, 0.004, 0.01, 0.03, 0.08"); /* load, pF */
        values ("...", "...") ;  /* 5 x 5 delays */
      }
      rise_transition (delay_template_5x5) { ... }
    }
  }
  leakage_power () { when : "!A&!B" ; value : 1.8 ; }
}''', "An abridged Liberty cell. Delay is a lookup table indexed by input "
      "slew and output load - which is why the same gate is faster when it "
      "drives less. Advanced nodes add CCS/ECSM current-source models and "
      "LVF statistical tables, but the idea is unchanged.")
    tbl(["Library dimension", "Typical choices", "Why an RTL designer cares"],
        [["**PVT corner**",
          "Process ss/tt/ff (plus ssg/ffg), voltage e.g. 0.72/0.80/0.88 V, "
          "temperature -40/25/125 degC; file names like `ss_0p72v_125c`",
          "Setup is signed off at the slow corner, hold at the fast corner; "
          "at advanced nodes **temperature inversion** can make the cold "
          "corner the slow one"],
         ["**Threshold voltage (Vt)**",
          "ULVT, LVT, SVT/RVT, HVT (and sometimes eLVT)",
          "Lower Vt is faster but leaks exponentially more; tools use HVT by "
          "default and swap LVT onto critical paths"],
         ["**Drive strength**", "X1, X2, X4 ... X16 (or D1, D2 ...)",
          "Sizing fixes load-dominated delay; very high fanout needs a "
          "buffer tree, not a bigger gate"],
         ["**Track height**", "e.g. 6T, 7.5T, 9T, 12T libraries",
          "Short cells are dense and low power; tall cells are fast"],
         ["**Channel length**", "C-poly variants (e.g. +4 nm) in some nodes",
          "Another leakage/speed knob, used like Vt swapping"],
         ["**Special cells**",
          "ICG (clock gate), retention flops, level shifters, isolation, "
          "always-on buffers, tie-hi/lo, spare and ECO cells, synchronizer "
          "flops", "Chapters 11, 19, 20 and 21 instantiate or rely on them"]],
        widths=[18, 40, 42], bold_first=True)
    box("tip", "The NAND2 gate equivalent (GE)",
        "Area is often quoted in **gate equivalents**: total cell area "
        "divided by the area of a NAND2X1 in the same library. It lets you "
        "compare designs across nodes. Rough rules of thumb: a D flip-flop "
        "is 4.5-6 GE, a scan flop with reset 6-8 GE, a full adder about 6-8 "
        "GE, and an N x N array multiplier roughly 6-8 x N^{2} GE before "
        "optimisation.")

    h2("What infers what")
    p("Synthesis tools recognise a small set of **templates**. Code that "
      "matches a template maps cleanly; code that does not either fails or, "
      "worse, maps to something you did not intend. The following module "
      "exercises the most common templates in one place:")
    code(r'''module infer_zoo (
  input  wire       clk, rst_n, en, sel,
  input  wire [7:0] a, b,
  output reg  [7:0] q_rst,   // DFF with async reset
  output reg  [7:0] q_en,    // DFF + enable (mux feedback or ICG)
  output wire [7:0] m,       // 2:1 mux
  output wire [8:0] s,       // adder (carry out)
  output wire       lt       // comparator
);
  assign m  = sel ? a : b;
  assign s  = a + b;
  assign lt = a < b;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) q_rst <= 8'h00;
    else        q_rst <= m;
  always @(posedge clk)
    if (en) q_en <= s[7:0];
endmodule''')
    code(r'''module tb_zoo;
  reg clk = 0, rst_n = 0, en = 0, sel = 1;
  reg [7:0] a = 8'd200, b = 8'd100;
  wire [7:0] q_rst, q_en, m; wire [8:0] s; wire lt;
  infer_zoo dut (.*);
  always #5 clk = ~clk;
  initial begin
    #12 rst_n = 1; en = 1;
    @(posedge clk); #1;
    $display("m=%0d s=%0d lt=%b q_rst=%0d q_en=%0d", m, s, lt, q_rst, q_en);
    $finish;
  end
endmodule''')
    out(["m=200 s=300 lt=0 q_rst=200 q_en=44"],
        "Simulated with iverilog. `q_en` holds the low 8 bits of 300 (= 44): "
        "the 9-bit sum was truncated by the part-select exactly as the "
        "hardware will truncate it.")
    tbl(["RTL idiom", "Inferred hardware", "Notes"],
        [["`assign y = s ? a : b;`", "MUX2 (or AND-OR / AOI)",
          "Wide or nested `?:` chains become priority muxes"],
         ["`always @* case (s) ...` fully assigned", "Parallel mux / decoder",
          "If items overlap, a priority chain"],
         ["`always @*` with a missing assignment on some path",
          "**Latch** (level-sensitive storage)",
          "Almost always a bug in ASIC RTL - Chapter 5"],
         ["`always @(posedge clk) q <= d;`", "D flip-flop", ""],
         ["`... or negedge rst_n) if (!rst_n)`", "DFF with async clear/preset",
          "Reset value picks DFFR vs DFFS"],
         ["`if (!rst_n) q <= 0;` in a posedge-only block",
          "DFF + AND gate on D (sync reset)",
          "Some libraries have sync-reset flops; `sync_set_reset` pragma "
          "keeps the reset next to the flop"],
         ["`if (en) q <= d;`", "DFF + MUX2 feedback, **or** an ICG",
          "Tool-selected: clock gating replaces the mux for wide banks "
          "(Chapter 19)"],
         ["`+`, `-`", "Adder / subtractor", "Architecture picked by timing: "
          "ripple, carry-select, Kogge-Stone..."],
         ["`*`", "Multiplier (Booth + Wallace/Dadda tree + final adder)",
          "Large; constants multiply into shift-add networks"],
         ["`/`, `%` by a variable", "Array divider - huge and slow",
          "Use a sequential divider (Chapter 8); powers of two are free"],
         ["`<<` by a variable", "Barrel shifter (log2(N) mux levels)",
          "Constant shifts are just wiring"],
         ["`==`, `<`", "Comparator (XNOR tree / subtractor carry)", ""],
         ["`reg [W-1:0] mem [0:D-1]` with sync write",
          "Flop array + read mux, or a memory macro if a compiler is used",
          "Large arrays belong in SRAM macros (Chapter 9)"],
         ["`for` loop with constant bounds", "Unrolled replicated logic",
          "A loop is **space**, not time"],
         ["Tri-state `assign y = oe ? d : 'z;`", "Tri-state buffer",
          "Only at pads; internal tri-states are banned in most flows"]],
        widths=[33, 33, 34])

    h2("Constructs synthesis ignores or rejects")
    p("The simulator executes the full IEEE 1800 language; synthesis "
      "implements a subset defined (loosely) by IEEE 1800 plus each vendor's "
      "manual. The dangerous category is not the constructs that are "
      "rejected - you will find those on day one - but those that are "
      "**accepted and silently ignored**, because the simulation you "
      "trusted no longer describes the chip.")
    tbl(["Construct", "Simulator", "Synthesis (ASIC)"],
        [["`#5` delays", "Waits 5 time units", "**Ignored** (warning at most)"],
         ["`initial` blocks", "Run once at time 0",
          "**Ignored** for ASIC; FPGA tools use them for power-up values"],
         ["Register initialiser `reg q = 1'b0;`", "Initial value",
          "**Ignored** for ASIC - the flop powers up random"],
         ["Incomplete sensitivity list `@(a)`", "Evaluates only on `a`",
          "Builds full combinational logic - **mismatch**"],
         ["`x` assignments (`y = 'x;`)", "Propagates X",
          "Don't-care: the tool picks whatever value is cheapest"],
         ["`===`, `!==`, `casex` on X", "4-state compare",
          "Treated as `==`/`!=` or rejected"],
         ["`// synopsys full_case / parallel_case`", "**Ignored** (comment)",
          "Changes the logic - **mismatch**"],
         ["`$display`, `$random`, `force`, `fork/join`, `wait`",
          "Executed", "Rejected or ignored"],
         ["`while` with data-dependent bound", "Executes", "Rejected"],
         ["`real`, `time`, classes, dynamic arrays", "Supported", "Rejected"]],
        widths=[33, 27, 40], bold_first=True)

    h3("Example: the incomplete sensitivity list")
    code(r'''module and_bad (input wire a, b, output reg y);
  always @(a) y = a & b;      // b missing from the sensitivity list
endmodule

module and_good (input wire a, b, output reg y);
  always @* y = a & b;        // complete by construction
endmodule

module tb_sens;
  reg a = 0, b = 0;
  wire y_bad, y_good;
  and_bad  u_bad  (.a(a), .b(b), .y(y_bad));
  and_good u_good (.a(a), .b(b), .y(y_good));
  initial begin
    #1 a = 1;  #1 $display("a=1 b=0 : y_bad=%b y_good=%b", y_bad, y_good);
    #1 b = 1;  #1 $display("a=1 b=1 : y_bad=%b y_good=%b  <- mismatch", y_bad, y_good);
    #1 a = 0;  #1 a = 1;
    #1 $display("a toggled: y_bad=%b y_good=%b", y_bad, y_good);
    $finish;
  end
endmodule''')
    out(["a=1 b=0 : y_bad=0 y_good=0",
         "a=1 b=1 : y_bad=0 y_good=1  <- mismatch",
         "a toggled: y_bad=1 y_good=1"],
        "The RTL simulation of `and_bad` misses the change on `b`. The "
        "synthesised AND gate does not - so the netlist behaves like "
        "`and_good`, and RTL simulation was lying. Note that `iverilog -Wall` "
        "did not warn; lint tools (Chapter 25) do.")
    box("warn", "Pitfall: 'it passed simulation' is not the same as 'it works'",
        "Incomplete sensitivity lists, `full_case` pragmas, `x`-assignments "
        "and `initial` values all produce **RTL-vs-gate mismatches**. They "
        "are caught by three independent nets: lint (rules such as "
        "'incomplete sensitivity list', 'synthesis pragma used'), "
        "**logical equivalence checking** of RTL against the netlist, and "
        "gate-level simulation (Chapters 25-26). Use `always_comb` and "
        "`always_ff` and most of this category disappears: `always_comb` "
        "infers its own sensitivity and tools must flag latches in it.")

    h2("full_case and parallel_case: pragmas that lie")
    p("The two most notorious synthesis directives are comments that "
      "change the hardware. `full_case` tells synthesis 'the listed items "
      "cover every value that will ever occur, so unlisted values are "
      "don't-care'. `parallel_case` tells it 'the items never overlap, so "
      "build a parallel mux instead of a priority chain'. The simulator "
      "reads both as comments.")
    code(r'''module dec_fc (input wire [1:0] sel, output reg [2:0] y);
  always @* begin
    case (sel)  // synopsys full_case   <- a promise the RTL does not keep
      2'b00: y = 3'b001;
      2'b01: y = 3'b010;
      2'b10: y = 3'b100;
    endcase
  end
endmodule

module dec_ok (input wire [1:0] sel, output reg [2:0] y);
  always @* begin
    y = 3'b000;                 // default assignment first: no latch, no pragma
    case (sel)
      2'b00: y = 3'b001;
      2'b01: y = 3'b010;
      2'b10: y = 3'b100;
      default: ;
    endcase
  end
endmodule''')
    code(r'''module tb_fc;
  reg  [1:0] sel;
  wire [2:0] y_fc, y_ok;
  dec_fc u_fc (.sel(sel), .y(y_fc));
  dec_ok u_ok (.sel(sel), .y(y_ok));
  initial begin
    sel = 2'b10; #1 $display("sel=10 : y_fc=%b y_ok=%b", y_fc, y_ok);
    sel = 2'b11; #1 $display("sel=11 : y_fc=%b y_ok=%b  (RTL sim holds old y)", y_fc, y_ok);
    $finish;
  end
endmodule''')
    out(["sel=10 : y_fc=100 y_ok=100",
         "sel=11 : y_fc=100 y_ok=000  (RTL sim holds old y)"],
        "In simulation `dec_fc` behaves like a latch for `sel=11`. Synthesis, "
        "told the case is full, builds no latch and treats `sel=11` as "
        "don't-care: the gates may output any value. Neither matches the "
        "other, and neither is probably what the designer meant.")
    tbl(["Mechanism", "Effect on synthesis", "Effect on simulation", "Verdict"],
        [["`// synopsys full_case`", "Unlisted values = don't-care; no latch",
          "None", "Avoid - mismatch"],
         ["`// synopsys parallel_case`", "Parallel mux, even if items overlap",
          "None (priority order kept)", "Avoid - mismatch"],
         ["Default assignment before `case`", "Defined value, no latch",
          "Same", "**Preferred**"],
         ["SV `unique case`", "Like full + parallel",
          "Run-time warning if no item or >1 item matches",
          "Good - the promise is checked"],
         ["SV `unique0 case`", "Parallel only", "Warning if >1 matches",
          "Good for one-hot decoders"],
         ["SV `priority case`", "Like full_case (priority kept)",
          "Warning if no item matches", "Use when you mean it"]],
        widths=[24, 28, 28, 20], bold_first=True)
    box("expert", "Interview insight",
        "'What is the difference between `unique case` and `// synopsys "
        "parallel_case full_case`?' The synthesis result is the same; the "
        "difference is that SystemVerilog makes the simulator **check** the "
        "assumption and report a violation, so the optimisation is backed "
        "by verification instead of hope. Formal equivalence checkers also "
        "honour the `unique` semantics.")

    h2("Hierarchy, uniquification and boundary optimization")
    p("Synthesis can keep your module hierarchy or **flatten** (ungroup) it. "
      "Flattening lets the optimiser move logic across module boundaries - "
      "merging a comparator in one block with a mux in the next - and "
      "typically improves timing and area by a few percent. Keeping "
      "hierarchy preserves debuggability, lets you apply per-block "
      "constraints, and is **required** where the hierarchy carries "
      "meaning: power domains (UPF refers to instance names), DFT wrappers, "
      "hard macros, clock-gating cells you instantiated on purpose, and "
      "blocks that will be ECOed later.")
    bul(["**Uniquification.** If `fifo` is instantiated four times, each "
         "instance may need different optimisation (one drives a long wire, "
         "one is on a critical path). Tools create unique copies "
         "(`fifo_0`, `fifo_1`, ...) automatically during compile. This is "
         "why netlist module names differ from your RTL.",
         "**Boundary optimization.** Constants and unused outputs are "
         "propagated across ports: a port tied to 0 by the parent simplifies "
         "the child's logic. It is a big win - and the reason a "
         "`dont_touch` or `set_boundary_optimization false` is needed on "
         "blocks you intend to ECO or to connect differently later.",
         "**Auto-ungrouping.** Small modules (a few hundred gates) are often "
         "dissolved into their parent by default; keep a hierarchy only if "
         "you need it.",
         "**Naming.** Registers in the netlist are named from the RTL "
         "(`u_core/state_reg_2_`), which is why meaningful signal names pay "
         "off at gate-level debug and in timing reports."])

    h2("A synthesis script in three dialects")
    p("Every commercial flow is a Tcl script (see the companion Tcl book "
      "for the language). The command names differ between Synopsys Design "
      "Compiler, Cadence Genus and open-source Yosys, but the structure is "
      "identical: set up libraries, read RTL, elaborate, apply constraints, "
      "compile, write outputs, report.")
    code(r'''# ---------------- Synopsys Design Compiler (dc_shell / dcnxt_shell) ----------
set_app_var search_path    ". ./lib ./rtl"
set_app_var target_library "stdcell_ss_0p72v_125c.db"
set_app_var link_library   "* stdcell_ss_0p72v_125c.db sram_ss_0p72v_125c.db"
define_design_lib WORK -path ./work

analyze   -format sverilog [list pkg.sv fifo.sv core.sv top.sv]
elaborate top -parameters "DATA_W=32"
current_design top
link
check_design                      ;# unresolved refs, multiple drivers, loops
source constraints/top.sdc        ;# clocks, IO delays, exceptions (Ch. 18)

set_dont_use [get_lib_cells */*ULVT*]   ;# e.g. keep leakage in check
compile_ultra -gate_clock -scan   ;# clock gating + scan-ready flops

change_names -rules verilog -hierarchy
write -format verilog -hierarchy -output out/top.syn.v
write_sdc out/top.syn.sdc
report_qor                 > rpt/qor.rpt
report_timing -max_paths 20 -nworst 1 > rpt/timing.rpt
report_area -hierarchy     > rpt/area.rpt
report_power               > rpt/power.rpt
report_clock_gating        > rpt/cg.rpt''', "A minimal Design Compiler "
      "flow. Production scripts add multi-corner setup, SAIF-driven power "
      "optimisation, physical guidance (DC-Topographical/NXT with a "
      "floorplan) and many checks.")
    code(r'''# ---------------- Cadence Genus ------------------------------------------------
set_db init_lib_search_path ./lib
set_db init_hdl_search_path ./rtl
read_libs stdcell_ss_0p72v_125c.lib
read_hdl -sv {pkg.sv fifo.sv core.sv top.sv}
elaborate top
check_design -unresolved
read_sdc constraints/top.sdc
set_db lp_insert_clock_gating true
syn_generic                    ;# RTL -> generic gates
syn_map                        ;# generic -> library cells
syn_opt                        ;# incremental timing/area optimisation
write_hdl > out/top.syn.v
write_sdc > out/top.syn.sdc
report_timing > rpt/timing.rpt
report_area   > rpt/area.rpt
report_gates  > rpt/gates.rpt''')
    code(r'''# ---------------- Yosys (open source) ------------------------------------------
read_verilog -sv rtl/top.sv rtl/core.sv
hierarchy -check -top top
synth -top top                       ;# generic synthesis + internal cell lib
dfflibmap -liberty lib/cells.lib     ;# map flops to library flops
abc -liberty lib/cells.lib -D 1250   ;# map logic, delay target 1250 ps
opt_clean
stat -liberty lib/cells.lib          ;# cell counts and area
write_verilog -noattr out/top.syn.v''', "Yosys runs the same conceptual "
      "flow. Yosys has limited SystemVerilog support on its own (plugins "
      "such as yosys-slang or a Surelog/UHDM front end extend it).")
    box("tip", "Try it with open-source tools",
        "You do not need a commercial licence to learn implementation. "
        "**Yosys** (synthesis) + **OpenROAD** (floorplan, placement, CTS, "
        "routing, STA with OpenSTA) are packaged as **OpenLane 2** and the "
        "**OpenROAD-flow-scripts** (ORFS), with open PDKs such as SkyWater "
        "sky130, GF180MCU, IHP SG13G2 and the predictive ASAP7. Taking one "
        "of your own blocks from RTL to GDS - and reading every report on the "
        "way - teaches more about this Part than any book. (Yosys was not "
        "installed in the environment used to build this book, so no Yosys "
        "output is shown.)")

    h2("Reading QoR reports")
    p("After compile, the first report to read is the **quality of results** "
      "(QoR) summary. The excerpt below is illustrative - the format follows "
      "Design Compiler's `report_qor`, the numbers are made up - but every "
      "field in it is one you must be able to interpret.")
    code(r'''  Timing Path Group 'core_clk'
  -----------------------------------
  Levels of Logic:              23.00
  Critical Path Length:          1.21
  Critical Path Slack:          -0.08
  Critical Path Clk Period:      1.25
  Total Negative Slack:         -3.42
  No. of Violating Paths:      117.00

  Cell Count
  -----------------------------------
  Hierarchical Cell Count:         41
  Leaf Cell Count:              58233
  Buf/Inv Cell Count:            9210
  Sequential Cell Count:         7412
  Macro Count:                      4

  Area
  -----------------------------------
  Combinational Area:       31022.51
  Noncombinational Area:    28140.88
  Macro/Black Box Area:    112400.00
  Total Cell Area:         171563.39''', "Illustrative QoR excerpt "
      "(synthetic numbers). Units follow the library: ns and um^2 here.")
    tbl(["Field", "What it tells you", "Red flags"],
        [["**WNS** (critical path slack)",
          "Worst negative slack: how far the worst path misses",
          "Beyond ~10% of the period at synthesis: an RTL/architecture "
          "problem, not a tool problem"],
         ["**TNS**, violating paths",
          "Sum of all negative slacks: breadth of the problem",
          "Small WNS but huge TNS means a whole bus or datapath is slow"],
         ["Levels of logic",
          "Gates on the critical path", "Far above your budget for the node "
          "and frequency: pipeline or restructure"],
         ["Buf/Inv count", "Buffering for fanout and wire load",
          "A large fraction (>20-25%) suggests high-fanout nets or long "
          "wires"],
         ["Sequential count / area", "Flops and latches",
          "Unexpected latches; flop count far from your estimate (logic "
          "removed as unloaded, or memories built from flops)"],
         ["Combinational vs non-combinational area",
          "Balance between logic and state",
          "Wide muxes and big arithmetic dominate combinational area"]],
        widths=[22, 38, 40], bold_first=True)
    box("tip", "Triage order for a fresh netlist",
        "1) `check_design` / elaboration warnings: latches, multiple "
        "drivers, unconnected ports, constant registers. 2) Sequential cell "
        "count versus your expectation. 3) Timing: WNS/TNS per path group, "
        "then the **top 10 critical paths** - their start/end points tell "
        "you which RTL lines to change. 4) Area by hierarchy. 5) Clock-"
        "gating coverage and power. Never tune constraints to hide a path "
        "you have not understood.")

    h2("Summary")
    bul(["Synthesis = analyze -> elaborate -> technology-independent "
         "optimisation -> technology mapping -> constraint-driven "
         "optimisation, producing a netlist of library cells.",
         "Liberty libraries define cell function, NLDM/CCS timing and power "
         "per PVT corner; Vt flavour, drive strength and track height are "
         "the knobs the tool turns.",
         "Each RTL idiom maps to a template; `/` and `%` by variables, "
         "variable shifts and wide multipliers are expensive.",
         "Delays, `initial` blocks and register initialisers are ignored for "
         "ASIC; incomplete sensitivity lists and `full_case` / "
         "`parallel_case` cause RTL-vs-gate mismatches. Prefer "
         "`always_comb`, default assignments and `unique case`.",
         "Hierarchy is a trade between optimisation across boundaries and "
         "debuggability, UPF/DFT/ECO requirements.",
         "Read QoR in order: warnings, flop count, WNS/TNS and critical "
         "paths, area by hierarchy, power."])
    h2("Exercises")
    bul(["Sketch the gate-level hardware for `infer_zoo` including the "
         "enable mux and the reset tree, and estimate its area in GE using "
         "the rules of thumb from this chapter.",
         "Write a 4:1 mux three ways (`case`, nested `?:`, AND-OR of one-hot "
         "selects). Which one is a priority structure? Which one would "
         "synthesise to the same gates under `unique case`?",
         "Explain precisely why `dec_fc` can produce a different output value "
         "in gate-level simulation than in RTL simulation for `sel=2'b11`, "
         "and how an equivalence checker would report it.",
         "Install Yosys (or use an online Yosys playground), synthesise a "
         "16-bit adder with `synth` and then with `abc -D` at two delay "
         "targets, and compare the `stat` cell counts.",
         "A block has 12,000 flops and a critical path of 31 logic levels "
         "at 1 GHz, with 30% of cells being buffers. List the three most "
         "likely RTL causes and what you would inspect first."],
        ordered=True)


# =============================================================================
#              CHAPTER 18 - TIMING: STA, SDC AND CLOSING TIMING FROM RTL
# =============================================================================
def _ch18():
    chapter("Timing: STA, SDC and Closing Timing from RTL")
    p("A synchronous design works if, and only if, every flip-flop sees a "
      "stable input for a short window around each active clock edge. "
      "**Static timing analysis** (STA) proves this for every path in the "
      "design without a single simulation vector, by adding up worst-case "
      "and best-case delays from the library. Its inputs are the netlist, "
      "the libraries (one per corner), parasitics once the design is "
      "placed and routed, and the constraints you write in **SDC** (Synopsys "
      "Design Constraints, a Tcl-based de facto standard read by every "
      "synthesis, place-and-route and STA tool).")
    p("As an RTL designer you meet timing three times: when you choose an "
      "architecture (how many logic levels fit in a cycle), when you write "
      "the SDC that tells the tools your intent, and when the "
      "implementation team hands back a list of failing paths that can only "
      "be fixed in RTL. This chapter covers all three.")

    h2("Timing paths")
    diagram([
        "         chip / block boundary",
        "   +---------------------------------------------------------------+",
        "   |                                                               |",
        "in +--[ comb A ]--> D  FF1  Q --[ comb B ]--> D  FF2  Q --[ comb C ]+--> out",
        "   |                   ^                         ^                 |",
        "   |                   | clk                     | clk             |",
        "   |                                                               |",
        "in +---------------------------[ comb D ]------------------------+--> out",
        "   +---------------------------------------------------------------+",
        "",
        "   in2reg : input port -> comb A -> FF1.D     (constrained by set_input_delay)",
        "   reg2reg: FF1.CK -> Q -> comb B -> FF2.D    (constrained by the clock period)",
        "   reg2out: FF2.CK -> Q -> comb C -> output   (constrained by set_output_delay)",
        "   in2out : input -> comb D -> output         (feed-through: both IO delays)",
    ], "Figure 18.1 - The four path types. Every path starts at a clock pin "
       "or an input port and ends at a data pin of a sequential element or "
       "an output port. Clock paths (source -> tree -> CK pins) are analysed "
       "separately and feed the launch and capture times.")
    box("key", "Why good blocks register their outputs",
        "reg2out and in2out paths split the cycle between two blocks - and "
        "the two designers - so both sides must agree on a budget. If every "
        "block registers its outputs (and ideally its inputs), inter-block "
        "timing is almost free and each team can close timing alone. "
        "In2out combinational feed-throughs are the most fragile paths on "
        "a chip; avoid them across block boundaries.")

    h2("Setup and hold, with skew and uncertainty")
    p("Consider a launch flop FF1 and a capture flop FF2 on the same clock "
      "of period T. Let L1 and L2 be the clock arrival times (insertion "
      "delay) at their clock pins, and define the **skew** as "
      "`skew = L2 - L1` (positive when the capture clock arrives late). "
      "Uncertainty models jitter and margin the tools cannot compute.")
    _eqa(["Setup:  L1 + t_cq + t_comb,max  <=  T + L2 - t_setup - t_unc,setup",
        "",
        "        slack_setup = (T + skew - t_setup - t_unc) - (t_cq + t_comb,max)",
        "",
        "Hold:   L1 + t_cq,min + t_comb,min  >=  L2 + t_hold + t_unc,hold",
        "",
        "        slack_hold  = (t_cq,min + t_comb,min) - (skew + t_hold + t_unc,hold)",
        "",
        "f_max = 1 / (t_cq + t_comb,max + t_setup + t_unc - skew)"],
       "Positive skew helps setup and hurts hold. Setup depends on the clock "
       "period; **hold does not** - a hold violation cannot be fixed by "
       "slowing the clock, which is why it is fatal in silicon.")
    diagram([
        "              T = 1000 ps",
        "      |<------------------------------------------>|",
        "clk1  _/~~~~~~~~~~~~~~~~~~~~~\\_____________________/~~~~   launch at L1 = 0",
        "clk2  ___/~~~~~~~~~~~~~~~~~~~~~\\_____________________/~~   capture at L2 = 30",
        "         .                                           .",
        "FF1.Q  ==X=== new data ==================================   t_cq = 60",
        "FF2.D  ======== old =========================X== new ====   arrives 780",
        "                                             |        |",
        "                                   arrival 780|  req 940|  slack = +160",
        "                                              (T+30-40-50)",
    ], "Figure 18.2 - The setup check of the worked example below on a "
       "timing diagram.")
    h3("Worked example")
    p("A 1 GHz clock (T = 1000 ps). Library and extraction give: t_cq = 60 "
      "ps (max) / 45 ps (min), setup 40 ps, hold 25 ps. The comb logic "
      "between the flops is 720 ps on its longest path and 20 ps on its "
      "shortest. The clock tree delivers the capture clock 30 ps late "
      "(skew = +30). Uncertainty is 50 ps for setup and 20 ps for hold.")
    _eqa(["Setup arrival  = 60 + 720                 = 780 ps",
        "Setup required = 1000 + 30 - 40 - 50      = 940 ps",
        "Setup slack    = 940 - 780                = +160 ps   (met)",
        "",
        "Hold arrival   = 45 + 20                  =  65 ps",
        "Hold required  = 30 + 25 + 20             =  75 ps",
        "Hold slack     = 65 - 75                  = -10 ps    (VIOLATED)",
        "",
        "f_max = 1 / (60 + 720 + 40 + 50 - 30) ps = 1 / 840 ps = 1.19 GHz"],
       "The same skew that gave setup 30 ps of help causes the hold "
       "violation.")
    p("Physical design fixes the hold violation by inserting delay cells on "
      "the short path (cheap, automatic). But if the shortest path is a "
      "**direct flop-to-flop connection** - a shift register, or a "
      "synchronizer - between flops with large skew, hold fixing adds many "
      "buffers. RTL can help by avoiding long direct chains across "
      "distant clock-tree branches.")
    h3("On-chip variation and derating")
    p("The equations above assume each cell has one delay per corner. Real "
      "silicon varies across the die, so signoff STA is pessimistic in a "
      "controlled way: for setup, the launch clock and data paths are "
      "slowed (late derate, e.g. x1.05) and the capture clock is sped up "
      "(early derate, e.g. x0.95); hold is the reverse. Modern flows use "
      "**AOCV** (derate depends on path depth and distance) or **POCV / "
      "LVF** (each cell carries a statistical sigma). **CRPR** (clock "
      "reconvergence pessimism removal) gives back the pessimism on the "
      "common part of the launch and capture clock paths - which is why "
      "flops that talk to each other should share as much clock tree as "
      "possible.")
    tbl(["Term", "Meaning"],
        [["**Slack**", "Required time minus arrival time; negative = "
          "violation"],
         ["**WNS / TNS**", "Worst / total negative slack over a path group"],
         ["**MCMM**", "Multi-corner multi-mode: every mode (functional, "
          "scan shift, scan capture, low-power) at every corner"],
         ["**Recovery / removal**", "Setup/hold-like checks for the "
          "de-assertion of asynchronous resets (Chapter 12)"],
         ["**Clock gating check**", "Setup/hold of the enable at an "
          "ICG or gating cell (Chapter 19)"],
         ["**Max transition / capacitance / fanout**", "Design-rule checks: "
          "slow edges burn power, degrade delay models and hurt reliability"]],
        widths=[28, 72], bold_first=True)

    h2("SDC: telling the tools what you mean")
    p("SDC describes the environment and the intent: the clocks, what "
      "happens outside the block, and which paths are **exceptions** to the "
      "default single-cycle rule. It is written in Tcl, so `get_ports`, "
      "`get_pins`, `get_clocks` and `get_cells` return object collections "
      "that the constraint commands consume.")
    tbl(["Command", "Purpose"],
        [["`create_clock`", "Defines a clock on a port or pin: name, period, "
          "waveform"],
         ["`create_generated_clock`", "A clock derived from another "
          "(divider, mux output) - keeps the phase relationship known"],
         ["`set_clock_uncertainty`", "Jitter + margin (larger before CTS)"],
         ["`set_clock_latency` / `set_clock_transition`", "Pre-CTS estimates "
          "of insertion delay and slew (ideal clocks)"],
         ["`set_input_delay` / `set_output_delay`", "How much of the cycle "
          "the outside world uses before/after this block"],
         ["`set_driving_cell` / `set_load`", "Electrical environment of IO"],
         ["`set_false_path`", "Path is never timed (static config, "
          "asynchronous resets into synchronizers, test-only)"],
         ["`set_multicycle_path`", "Path has N cycles to settle by design"],
         ["`set_clock_groups`", "Clocks that are asynchronous, or exclusive "
          "(never active together)"],
         ["`set_max_delay` / `set_min_delay`", "Point-to-point limits, e.g. "
          "on CDC data buses"],
         ["`set_case_analysis`", "Tie a pin to a constant for a mode "
          "(e.g. `test_mode = 0`)"]],
        widths=[36, 64], bold_first=True)

    h3("Multicycle paths: the -setup / -hold rule")
    p("Suppose a register updates only every second cycle (it has a "
      "clock-enable that toggles every other cycle) and its consumer "
      "samples it only on the following enable. The path has two cycles. "
      "`set_multicycle_path 2 -setup` moves the **capture** edge from 1T to "
      "2T. But the hold check is performed, by default, one edge **before** "
      "the setup capture edge - which is now at 1T, making the hold "
      "requirement a whole period larger and impossible to meet sensibly. "
      "So you must also move the hold edge back to 0.")
    code(r'''# Two-cycle path: ALWAYS pair the setup multiplier with a hold multiplier of N-1
set_multicycle_path 2 -setup -from [get_cells u_ctl/slow_reg*] -to [get_cells u_dp/acc_reg*]
set_multicycle_path 1 -hold  -from [get_cells u_ctl/slow_reg*] -to [get_cells u_dp/acc_reg*]''')
    diagram([
        "edge:        0T            1T            2T",
        "clk     ____/~~~~~\\______/~~~~~\\______/~~~~~\\____",
        "default:     L------------>S            (setup at 1T, hold at 0T)",
        "MCP 2 setup: L-------------------------->S  (setup at 2T, hold moves to 1T !)",
        "+ MCP 1 hold:H<- hold back at 0T         S  (correct)",
    ], "Figure 18.3 - Why `-setup N` must be accompanied by `-hold N-1` "
       "when launch and capture use the same clock.")
    box("warn", "Pitfall: exceptions are promises nobody checks",
        "STA believes every false path and multicycle path you write. A "
        "wrong exception hides a real failure until silicon. Rules: "
        "(1) every exception must be justified by an RTL mechanism "
        "(an enable, a synchronizer, a static configuration) and documented "
        "next to the RTL; (2) prefer `-from/-to` on specific registers, "
        "never on whole clocks, unless the clocks are truly asynchronous; "
        "(3) verify multicycle paths with assertions or formal (Chapter 23) "
        "and review them at every hand-off.")

    h3("Asynchronous clocks and CDC constraints")
    p("For clocks with no fixed phase relationship, the crossing must be "
      "handled by a synchronizer in RTL (Chapter 11), and timing between "
      "the domains should not be analysed as if it were synchronous. There "
      "are two tools:")
    bul(["`set_clock_groups -asynchronous` - declares that no path between "
         "the groups is timed. Simple, but it removes **all** checks, "
         "including ones you want.",
         "`set_max_delay` on the crossing paths - keeps a bound on the data "
         "bus skew of a gray-coded pointer or a mux-recirculation "
         "synchronizer, so that all bits arrive within one destination "
         "period. In Synopsys tools use `-ignore_clock_latency` "
         "(Xilinx XDC uses `-datapath_only`)."])
    box("expert", "Precedence matters",
        "Exceptions have a priority order: `set_clock_groups` and "
        "`set_false_path` override `set_max_delay`, which overrides "
        "`set_multicycle_path`. If you declare two clocks asynchronous with "
        "`set_clock_groups`, a `set_max_delay` you later write between them "
        "is silently ignored. For crossings that need a skew bound, "
        "constrain them with `set_max_delay` and do not put the clocks in "
        "asynchronous groups (or use false paths only on the paths that "
        "really need none).")

    h3("A complete block-level SDC file")
    code(r'''# ============ top.sdc - block 'dsp_top', 1 GHz core, 100 MHz APB, 50 MHz JTAG
set CORE_T 1.000
set APB_T  10.000

# ---- clocks ------------------------------------------------------------------
create_clock -name core_clk -period $CORE_T -waveform {0 0.5} [get_ports core_clk]
create_clock -name apb_clk  -period $APB_T  [get_ports pclk]
create_clock -name tck      -period 20.0    [get_ports tck]

# divide-by-2 clock made by a flop in u_clkdiv (a generated clock, not a new one)
create_generated_clock -name core_clk_div2 -source [get_ports core_clk] \
    -divide_by 2 [get_pins u_clkdiv/div2_reg/Q]

# pre-CTS: ideal clocks with estimated latency, slew and margin
set_clock_latency    -source 0.20 [get_clocks core_clk]
set_clock_transition 0.05  [all_clocks]
set_clock_uncertainty -setup 0.060 [get_clocks core_clk]
set_clock_uncertainty -hold  0.020 [get_clocks core_clk]

# ---- IO: 60% of the cycle is used outside the block (APB ports p* done below) --
set core_in  [remove_from_collection [all_inputs] \
                 [get_ports {core_clk pclk tck rst_n p*}]]
set_input_delay  -max [expr 0.6*$CORE_T] -clock core_clk $core_in
set_input_delay  -min 0.050              -clock core_clk $core_in
set_output_delay -max [expr 0.6*$CORE_T] -clock core_clk [get_ports m_axis_*]
set_output_delay -min 0.000              -clock core_clk [get_ports m_axis_*]
set_input_delay  -max 4.0 -clock apb_clk [get_ports {psel penable pwrite paddr* pwdata*}]
set_output_delay -max 4.0 -clock apb_clk [get_ports {prdata* pready pslverr}]
set_driving_cell -lib_cell BUFX4 [all_inputs]
set_load 0.010 [all_outputs]

# ---- clock-domain crossings ----------------------------------------------------
# tck is fully asynchronous and only reaches 2-flop synchronizers
set_clock_groups -asynchronous -group {tck} -group {core_clk core_clk_div2 apb_clk}
# APB <-> core go through gray-coded FIFOs: bound the pointer skew instead
set_max_delay 1.0 -ignore_clock_latency -from [get_clocks apb_clk] -to [get_clocks core_clk]
set_max_delay 1.0 -ignore_clock_latency -from [get_clocks core_clk] -to [get_clocks apb_clk]
set_min_delay 0.0 -from [get_clocks apb_clk] -to [get_clocks core_clk]
set_min_delay 0.0 -from [get_clocks core_clk] -to [get_clocks apb_clk]

# ---- exceptions ----------------------------------------------------------------
# asynchronous reset input goes to a reset synchronizer (Chapter 12)
set_false_path -from [get_ports rst_n]
# coefficients are static while the filter runs (documented in dsp_regs.sv)
set_false_path -from [get_cells u_regs/coef_q_reg*]
# accumulator is enabled every 2nd cycle by acc_en (see u_dp/acc_en_q)
set_multicycle_path 2 -setup -from [get_cells u_dp/prod_reg*] -to [get_cells u_dp/acc_reg*]
set_multicycle_path 1 -hold  -from [get_cells u_dp/prod_reg*] -to [get_cells u_dp/acc_reg*]

# ---- modes and design rules ----------------------------------------------------
set_case_analysis 0 [get_ports test_mode]
set_max_transition 0.150 [current_design]
set_max_fanout 32 [current_design]''', "A complete functional-mode SDC. A "
      "separate scan-mode SDC sets `test_mode = 1`, defines the scan clock "
      "and constrains shift and capture (Chapter 20).")
    box("note", "Constraining the reset",
        "`set_false_path -from rst_n` is correct only because the port feeds "
        "a reset synchronizer: the **synchronized** reset that drives the "
        "flops must still be timed (recovery/removal checks). A false path "
        "on the internal reset net itself is a classic silicon bug.")

    h2("Closing timing from RTL")
    p("When a path fails by more than the tools can recover (roughly 5-10% "
      "of the period after synthesis), the fix is architectural. The "
      "levers, from the most to the least invasive:")
    tbl(["Technique", "What it does", "Cost"],
        [["**Pipelining**", "Insert registers to split the path; latency "
          "+1 per stage", "Flops, control changes (valid bits, stalls, "
          "forwarding)"],
         ["**Retiming**", "Move existing registers across logic to balance "
          "stages (tool option: `compile_ultra -retime`, Genus `retime`)",
          "Registers change names; reset values and equivalence checking "
          "get harder"],
         ["**Logic restructuring**", "Balanced trees instead of chains; "
          "carry-save instead of carry-propagate; precompute",
          "Design effort"],
         ["**Late-arriving signal last**", "Shannon expansion: compute both "
          "outcomes, select with the late signal", "Duplicated logic"],
         ["**One-hot encoding**", "State decode becomes a single bit; next-"
          "state logic shallower", "More flops"],
         ["**Register duplication**", "Split a high-fanout register into "
          "copies near each load", "Flops; must stop tools merging them"],
         ["**Precompute / look-ahead**", "Compute next cycle's condition "
          "one cycle early, register it", "Flops, reasoning"],
         ["**Narrow the problem**", "Smaller counters, fewer compare bits, "
          "split wide muxes", "Architecture"]],
        widths=[24, 50, 26], bold_first=True)

    h3("Pipelining a multiply-accumulate datapath")
    code(r'''// Before: multiply and add in one cycle -> critical path = MULT + ADD
module dot2_1c (
  input  wire        clk,
  input  wire [15:0] a, b, c, d,
  output reg  [32:0] y
);
  always @(posedge clk) y <= a*b + c*d;
endmodule

// After: two stages -> critical path = MULT (stage 1) or ADD (stage 2)
module dot2_2c (
  input  wire        clk, rst_n, in_vld,
  input  wire [15:0] a, b, c, d,
  output reg  [32:0] y,
  output reg         y_vld
);
  reg [31:0] p0, p1;
  reg        s1_vld;
  always @(posedge clk) begin
    p0 <= a * b;                  // stage 1: multipliers only
    p1 <= c * d;
    y  <= p0 + p1;                // stage 2: adder only
  end
  always @(posedge clk or negedge rst_n)   // valid bits travel with the data
    if (!rst_n) {y_vld, s1_vld} <= 2'b00;
    else        {y_vld, s1_vld} <= {s1_vld, in_vld};
endmodule''')
    diagram([
        " before:   a,b --[ MULT 16x16 ]--+                     path = t_mult + t_add",
        "           c,d --[ MULT 16x16 ]--+--[ ADD 33 ]--> [y]",
        "",
        " after:    a,b --[ MULT ]--> [p0] --+                   path = max(t_mult, t_add)",
        "           c,d --[ MULT ]--> [p1] --+--[ ADD ]--> [y]",
        "           in_vld ---------> [s1_vld] ---------> [y_vld]",
    ], "Figure 18.4 - The pipeline register cuts the path. Data registers "
       "need no reset; the valid bits do (Chapter 10).")
    p("Pipelining changes latency, so the check must compare against the "
      "one-cycle version **delayed by one cycle**. The testbench also "
      "checks a Shannon-expanded adder (below) against its original form:")
    code(r'''module tb_timing;
  reg clk = 0, rst_n = 0, in_vld = 0;
  reg [15:0] a, b, c, d;
  wire [32:0] y1, y2; wire y2_vld;
  dot2_1c u1 (.clk(clk), .a(a), .b(b), .c(c), .d(d), .y(y1));
  dot2_2c u2 (.clk(clk), .rst_n(rst_n), .in_vld(in_vld),
              .a(a), .b(b), .c(c), .d(d), .y(y2), .y_vld(y2_vld));
  reg [32:0] y1_q;                 // 1-cycle model output, delayed to align
  always @(posedge clk) y1_q <= y1;
  always #5 clk = ~clk;
  integer n = 0, err = 0, i;
  always @(posedge clk) if (y2_vld) begin
    n = n + 1;
    if (y2 !== y1_q) err = err + 1;
  end
  // Shannon check
  reg [15:0] base, x, z; reg late; wire [15:0] sb, sa; integer serr = 0;
  late_before lb (.base(base), .x(x), .z(z), .late(late), .sum(sb));
  late_after  la (.base(base), .x(x), .z(z), .late(late), .sum(sa));
  initial begin
    {a, b, c, d} = 0;
    #12 rst_n = 1;
    for (i = 0; i < 200; i = i + 1) begin
      @(negedge clk);
      in_vld = 1; a = $random; b = $random; c = $random; d = $random;
    end
    @(negedge clk) in_vld = 0;
    repeat (3) @(posedge clk);
    $display("dot2: %0d results compared, %0d mismatches, latency 1 -> 2 cycles",
             n, err);
    for (i = 0; i < 1000; i = i + 1) begin
      {base, x, z, late} = {$random, $random};
      #1 if (sa !== sb) serr = serr + 1;
    end
    $display("shannon: 1000 random vectors, %0d mismatches", serr);
    $finish;
  end
endmodule''')
    out(["dot2: 200 results compared, 0 mismatches, latency 1 -> 2 cycles",
         "shannon: 1000 random vectors, 0 mismatches"])

    h3("Moving a late-arriving signal to the end of the cone")
    p("If one input arrives late - it comes from another block's output, or "
      "from a long wire - restructure the logic so that the late signal "
      "passes through as few gates as possible. **Shannon expansion** "
      "`f(late, x) = late ? f(1, x) : f(0, x)` computes both cofactors in "
      "parallel with the late signal's journey and uses it only as a final "
      "mux select:")
    code(r'''// Late-arriving select: Shannon expansion moves 'late' to the last mux
module late_before (input wire [15:0] base, x, z, input wire late,
                    output wire [15:0] sum);
  assign sum = base + (late ? x : z);         // late -> mux -> adder -> out
endmodule
module late_after (input wire [15:0] base, x, z, input wire late,
                   output wire [15:0] sum);
  wire [15:0] s_x = base + x;                  // both adders start early
  wire [15:0] s_z = base + z;
  assign sum = late ? s_x : s_z;               // late -> one mux -> out
endmodule''', "Functionally identical (checked above on 1000 random "
      "vectors); the second costs one extra adder and removes a 16-bit "
      "carry chain from the late signal's path.")
    box("tip", "Synthesis will not always do this for you",
        "Tools restructure logic within their timing view, but they do not "
        "know that an input will be late unless the SDC says so (input "
        "delays) or the block is synthesised in context. They also will "
        "not duplicate a whole adder speculatively. When you know a signal "
        "is late, write the RTL so that the structure is already right.")

    h3("Register duplication for high fanout")
    code(r'''// High fanout: register duplication (keep the copies from being merged)
module fanout_dup (
  input  wire        clk, en_d,
  input  wire [63:0] d0, d1,
  output reg  [63:0] q0, q1
);
  (* keep = "true" *) reg en_a;   // drives the q0 bank
  (* keep = "true" *) reg en_b;   // drives the q1 bank
  always @(posedge clk) begin
    en_a <= en_d;
    en_b <= en_d;
    if (en_a) q0 <= d0;
    if (en_b) q1 <= d1;
  end
endmodule''', "Compiled with iverilog -Wall. Synthesis merges equivalent "
      "registers by default; the attribute (tool-specific: `keep`, "
      "`dont_touch`, or `set_register_merging false` in the script) keeps "
      "both. Physical synthesis can also duplicate registers itself.")
    p("A single enable flop driving 128 flops needs a buffer tree of "
      "log4(128) ~ 3-4 levels, plus the wire to reach loads spread across "
      "the block. Two copies placed near each bank halve the load and the "
      "distance. The same idea applies to pipeline stall signals, FSM state "
      "bits used as datapath selects, and reset trees.")

    h3("One-hot state and precomputed flags")
    bul(["**One-hot FSMs** make 'are we in state S' a single flop output "
         "rather than a decode of the binary state; next-state logic for "
         "each bit is a small OR of AND terms. For control FSMs on "
         "critical paths the extra flops are cheap (Chapter 7).",
         "**Precompute flags.** Instead of `if (count == LIMIT-1)` on a "
         "critical path, register `almost_done <= (count == LIMIT-2)` one "
         "cycle earlier. FIFOs precompute `full`/`empty` the same way.",
         "**Carry-save arithmetic** keeps sums in redundant form through a "
         "chain of additions and resolves the carry once (Chapter 8).",
         "**Balanced trees.** `a+b+c+d` written as `(a+b)+(c+d)` is two "
         "adder levels instead of three; tools usually find this, but a "
         "long `for` loop accumulation written as a chain may not be "
         "rebalanced across a generate hierarchy."])
    box("expert", "Logic depth budgets",
        "Designers express the cycle in **FO4 delays** (the delay of an "
        "inverter driving four copies of itself), which roughly cancels out "
        "the process node. High-frequency CPU pipelines target on the order "
        "of 15-25 FO4 per cycle including flop overhead; typical SoC "
        "control logic has far more slack. Knowing your budget in logic "
        "levels lets you judge an RTL change before running synthesis.")

    h2("Summary")
    bul(["STA checks every path statically: in2reg, reg2reg, reg2out and "
         "in2out, for setup at slow corners and hold at fast corners, in "
         "every mode.",
         "Setup slack = (T + skew - t_setup - t_unc) - (t_cq + t_comb,max); "
         "hold slack is independent of the period and is fatal in silicon.",
         "OCV derates, AOCV/POCV and CRPR make signoff realistic; flops that "
         "talk should share clock tree.",
         "SDC defines clocks, IO budgets and exceptions; pair `-setup N` "
         "with `-hold N-1`; remember that clock groups override "
         "`set_max_delay`.",
         "Fix timing in RTL by pipelining, retiming, restructuring, "
         "putting late signals last, one-hot encoding, register duplication "
         "and precomputation - and prove the change with a self-checking "
         "testbench."])
    h2("Exercises")
    bul(["For the worked example, how much skew can the design tolerate "
         "before hold fails with zero comb delay? What is the maximum comb "
         "delay for setup?",
         "Write the SDC for a path from a register updated every 4th cycle "
         "to a register sampled on the same enable, and draw the setup and "
         "hold edges with and without the hold multiplier.",
         "Pipeline `dot2_2c` further so that each 16x16 multiplier is split "
         "into two 8-bit partial-product stages. Extend the testbench to "
         "check the new latency.",
         "Apply Shannon expansion to `y = ((a == b) & late) ? p : q` where "
         "`late` arrives 70% into the cycle. Verify your version against "
         "the original with random vectors.",
         "Explain why `set_false_path -to [get_pins */rst_n_sync_reg*/D]` "
         "is dangerous, and write the correct constraints for a reset "
         "synchronizer."],
        ordered=True)


# =============================================================================
#                      CHAPTER 19 - LOW-POWER RTL AND UPF
# =============================================================================
def _ch19():
    chapter("Low-Power RTL and UPF")
    p("For a phone SoC, a wearable or an always-listening ML accelerator, "
      "power is the first-class constraint: it sets battery life, the "
      "thermal envelope that limits sustained performance, and the cost of "
      "the package and power-delivery network. Most power savings are "
      "decided **before** synthesis - by the architecture and the RTL - "
      "because tools can only optimise the switching you describe. This "
      "chapter covers where power goes, the RTL techniques that reduce it, "
      "and how multi-voltage and power-gated designs are described with "
      "the Unified Power Format (UPF, IEEE 1801).")

    h2("Where the power goes")
    _eqa(["P_total   = P_dynamic + P_short-circuit + P_leakage",
        "",
        "P_dynamic = alpha x C_L x V_DD^2 x f        (per node, summed over the design)",
        "",
        "P_leakage = V_DD x I_leak,   I_leak ~ exp(-V_t / (n x kT/q))  (subthreshold)"],
       "alpha = activity factor (transitions per clock that charge the "
       "node, 0..1 for data, 1 for a clock net); C_L = switched capacitance; "
       "V_DD = supply; f = clock frequency.")
    tbl(["Term", "Depends on", "Knobs at RTL / architecture level"],
        [["**Dynamic (switching)**", "alpha, C, V^{2}, f",
          "Clock gating (alpha of clock nets), data gating, operand "
          "isolation, avoiding glitches, memory access reduction, lower f "
          "and V (DVFS)"],
         ["**Short-circuit**", "Input slew, V", "Mostly physical (slew "
          "limits); ~10% of dynamic"],
         ["**Leakage**", "V_t, V, temperature, total transistor width",
          "Power gating, HVT cells (tool), fewer/smaller memories, "
          "retention only where needed, body bias"]],
        widths=[20, 26, 54], bold_first=True)
    box("key", "Three facts that drive every low-power decision",
        "(1) V is squared: dropping supply 10% saves ~19% dynamic power, "
        "and because f must also drop, DVFS gives roughly cubic savings. "
        "(2) The **clock network** has alpha = 1 and large capacitance: it "
        "is often a third or more of dynamic power, so clock gating is the "
        "single most effective RTL technique. (3) Leakage does not care "
        "whether you are busy: in always-on products that are mostly idle, "
        "leakage dominates energy and only **power gating** removes it.")

    h2("Clock gating")
    p("A register with an enable keeps its value when `en = 0`, but its "
      "clock pin still toggles every cycle, burning clock-tree and internal "
      "flop power. **Clock gating** stops the clock to the whole bank when "
      "the enable is low. The gating element must not create glitches on "
      "the clock - which rules out a plain AND gate.")
    diagram([
        "  WRONG: plain AND                       RIGHT: integrated clock gate (ICG)",
        "",
        "  en ----+                                en ----+  +-------+",
        "         | AND --> gclk                  te ---OR+--| D   Q |--+  (latch: transparent",
        "  clk ---+                                         | latch |  |   while clk is LOW)",
        "                                          clk -+--o| EN    |  |",
        "  en changing while clk=1                      |   +-------+  |",
        "  -> glitch or runt pulse on gclk               +--------------AND--> gclk",
        "",
        "  clk   __/~~~~~\\____/~~~~~\\___            clk    __/~~~~~\\____/~~~~~\\___",
        "  en    ______/~~\\______________            en_l   (frozen while clk HIGH)",
        "  gclk  ______/~~\\______________ glitch!    gclk   __/~~~~~\\_____________ clean",
    ], "Figure 19.1 - The latch in the ICG only passes the enable while the "
       "clock is low, so the enable seen by the AND gate is stable for the "
       "whole high phase. `te` (test enable) forces the clock on during "
       "scan shift (Chapter 20).")
    code(r'''// Behavioural model of an integrated clock-gating cell (latch + AND).
// In a real design you instantiate the library ICG (e.g. a CKLNQD-type cell);
// this model is for simulation only.
module icg (
  input  wire clk,
  input  wire en,        // functional enable
  input  wire test_en,   // scan: force the clock on during shift
  output wire gclk
);
  reg en_l;
  always @(clk or en or test_en)
    if (!clk) en_l = en | test_en;   // transparent while clk is LOW
  assign gclk = clk & en_l;          // en_l is stable while clk is HIGH
endmodule

// RTL style that synthesis turns into an ICG automatically
module reg_en (input wire clk, en, input wire [31:0] d, output reg [31:0] q);
  always @(posedge clk)
    if (en) q <= d;
endmodule

// The same register with an explicit (hand-instantiated) gate
module reg_gated (input wire clk, en, test_en, input wire [31:0] d,
                  output reg [31:0] q);
  wire gclk;
  icg u_icg (.clk(clk), .en(en), .test_en(test_en), .gclk(gclk));
  always @(posedge gclk) q <= d;
endmodule

// The WRONG way: a plain AND gate on the clock
module reg_and_gate (input wire clk, en, input wire [31:0] d,
                     output reg [31:0] q);
  wire gclk = clk & en;              // en changing while clk=1 -> glitch
  always @(posedge gclk) q <= d;
endmodule''')
    code(r'''module tb_cg;
  reg clk = 0, en = 0;
  reg [31:0] d = 0;
  wire [31:0] q_en, q_g, q_and;
  integer err = 0, i, g_edges = 0, and_edges = 0;
  reg_en       r0 (.clk(clk), .en(en), .d(d), .q(q_en));
  reg_gated    r1 (.clk(clk), .en(en), .test_en(1'b0), .d(d), .q(q_g));
  reg_and_gate r2 (.clk(clk), .en(en), .d(d), .q(q_and));
  always #5 clk = ~clk;
  always @(posedge r1.gclk) g_edges = g_edges + 1;
  always @(posedge r2.gclk) and_edges = and_edges + 1;
  initial begin
    for (i = 0; i < 100; i = i + 1) begin
      @(negedge clk); en = $random; d = $random;   // en changes while clk low
      @(posedge clk); #1 if (q_g !== q_en) err = err + 1;
    end
    $display("ICG vs enable-flop: 100 cycles, %0d mismatches", err);
    // now let en change while clk is HIGH (as a late glitchy enable would)
    g_edges = 0; and_edges = 0;
    @(negedge clk) en = 0;
    @(posedge clk) #2 en = 1;  #1 en = 0;          // pulse inside the high phase
    @(negedge clk);
    $display("en pulse during clk high: ICG edges=%0d, AND-gate edges=%0d",
             g_edges, and_edges);
    $finish;
  end
endmodule''')
    out(["ICG vs enable-flop: 100 cycles, 0 mismatches",
         "en pulse during clk high: ICG edges=0, AND-gate edges=1"],
        "The ICG-gated register is cycle-equivalent to the enable flop. A "
        "short enable pulse during the high phase creates a spurious clock "
        "edge through the AND gate - a real flop would capture garbage or "
        "go metastable on the runt pulse - while the ICG ignores it.")
    h3("Let synthesis do it: the enable style")
    p("You rarely instantiate ICGs by hand. Write registers with a clean "
      "enable (`if (en) q <= d;` with no `else`) and ask the tool for clock "
      "gating (`compile_ultra -gate_clock` with `set_clock_gating_style`, "
      "or Genus `set_db lp_insert_clock_gating true`). The tool groups "
      "flops that share an enable into banks and replaces the feedback "
      "muxes with one ICG per bank - but only above a minimum bank width "
      "(typically 3-8 bits), because an ICG costs area and its own power.")
    bul(["**Share enables.** Forty 32-bit registers each with a different "
         "enable give forty ICGs; the same registers updated by one "
         "`load` signal give one. Architect enables at the granularity of "
         "real activity (a whole pipeline stage, a whole register slice).",
         "**Make enables real.** `if (en) q <= d;` where `en` is almost "
         "always 1 saves nothing. Use valid bits: a pipeline stage whose "
         "`valid` is 0 need not clock its data registers (Chapter 10).",
         "**Watch enable timing.** The enable must meet setup to the ICG "
         "latch, which closes at the rising edge **earlier than** the flops "
         "it drives (the gated clock has less insertion delay). The "
         "**clock-gating check** in STA reports this; late enables need "
         "restructuring, not a bigger ICG.",
         "**Coarse-grain gating** by hand: a block-level clock-control unit "
         "with instantiated ICGs switches whole subsystems off. Keep it in a "
         "dedicated module so that CDC, DFT and STA tools recognise it.",
         "**Test enable.** The ICG `te` pin is tied to scan enable (or "
         "test mode) so that every flop is clocked during scan shift. An ICG "
         "without a controllable `te` makes its flops untestable."])
    box("warn", "Pitfall: gating a clock with logic in RTL",
        "`assign gclk = clk & en;` in RTL is wrong (as shown) and so is "
        "`always @(posedge (clk & en))`. Gated clocks must come from library "
        "ICG cells, instantiated in a clearly named wrapper (`cg_cell`) that "
        "has a behavioural model for simulation and FPGA and maps to the "
        "real cell in the ASIC netlist.")

    h2("Operand isolation and data gating")
    p("A combinational block whose output is not used this cycle still "
      "switches whenever its inputs change. **Operand isolation** freezes "
      "its inputs (AND-gating, or holding them in registers that are not "
      "enabled) so it does not toggle. It pays off for large arithmetic "
      "units - multipliers, dividers, wide comparators - fed by busy buses.")
    code(r'''// Operand isolation: freeze the multiplier inputs when its result is unused
module mac_iso (
  input  wire        clk, use_mul,
  input  wire [15:0] a, b, c,
  output reg  [31:0] y
);
  wire [15:0] a_i = a & {16{use_mul}};    // AND-isolation: inputs held at 0
  wire [15:0] b_i = b & {16{use_mul}};
  wire [31:0] prod = a_i * b_i;
  always @(posedge clk)
    y <= use_mul ? prod : {16'd0, c};
endmodule

module tb_iso;
  reg clk = 0, use_mul = 0; reg [15:0] a, b, c;
  wire [31:0] y; integer i, err = 0, toggles = 0;
  reg [31:0] exp_y; reg [31:0] prod_q;
  mac_iso dut (.*);
  always #5 clk = ~clk;
  always @(dut.prod) toggles = toggles + 1;
  initial begin
    for (i = 0; i < 400; i = i + 1) begin
      @(negedge clk);
      use_mul = (i < 100); a = $random; b = $random; c = $random;
      exp_y = use_mul ? a * b : {16'd0, c};
      @(posedge clk); #1 if (y !== exp_y) err = err + 1;
      if (i == 99) begin
        $display("after 100 mul cycles : product-bus changes = %0d", toggles);
        toggles = 0;
      end
    end
    $display("after 300 idle cycles: product-bus changes = %0d, errors = %0d",
             toggles, err);
    $finish;
  end
endmodule''')
    out(["after 100 mul cycles : product-bus changes = 101",
         "after 300 idle cycles: product-bus changes = 1, errors = 0"],
        "While the multiplier is idle its output bus changes once (to zero) "
        "and then stays quiet, although `a` and `b` keep changing. The "
        "count is a proxy for switching activity; a power tool would weight "
        "every internal node of the multiplier the same way.")
    box("note", "Isolation has a cost",
        "The AND gates add area and a gate of delay on the operand path, "
        "and `use_mul` must arrive early. Tools can insert operand isolation "
        "automatically (`set_operand_isolation_style` in DC), but the "
        "decision whether a unit is idle often long enough is architectural.")
    h3("Other RTL power techniques")
    tbl(["Technique", "Idea", "Where"],
        [["**Memory access reduction**", "Assert SRAM chip-enable only when "
          "reading/writing; never read 'just in case'; cache the last word "
          "read", "Every SRAM: an access costs far more than a flop toggle"],
         ["**Memory banking**", "Split a big SRAM into banks and enable one",
          "Buffers in ML accelerators, frame stores"],
         ["**SRAM low-power modes**", "Light sleep (periphery off), deep "
          "sleep (array at retention voltage), shutdown", "Driven by the "
          "power controller; check wake-up latency"],
         ["**Data gating on buses**", "Hold bus values when `valid = 0` "
          "instead of driving don't-care data", "Wide datapaths, AXI data"],
         ["**Glitch reduction**", "Balance paths, register outputs of deep "
          "XOR/arithmetic cones before long wires", "Multipliers, CRCs"],
         ["**Encoding**", "Gray code for counters on buses, bus-invert "
          "coding, one-hot where it lowers toggles", "Address buses, "
          "pointers"],
         ["**Reduce precision**", "INT8/INT4 instead of FP32 - capacitance "
          "and toggles scale with width", "ML datapaths (Chapter 29)"]],
        widths=[24, 48, 28], bold_first=True)

    h2("Multi-voltage design and power gating")
    p("Beyond gating the clock, a design can run different blocks at "
      "different supply voltages (**multi-voltage**, MV) and switch off the "
      "supply of idle blocks entirely (**power gating**, or power shut-off, "
      "PSO). These techniques need special cells and a precise description "
      "of the power architecture that every tool shares.")
    diagram([
        "  VDD_AON (0.8 V, always on)                       VDD_CPU (0.8 V)",
        "  ======================================           =============",
        "       |                                                 |",
        "  +----+------------------------------+        +---------+----------+",
        "  | PD_TOP (always-on)                |        |  header switches   |",
        "  |                                   |        |  (PMOS, daisy-     |",
        "  |  +-----------+   pwr_en ------------------>|   chained)  -> ack |",
        "  |  |  PMU /    |   iso_en ---+      |        +---------+----------+",
        "  |  |  pd_seq   |   save/restore    |                  | VDD_CPU_SW",
        "  |  +-----------+          |  |      |        +---------+----------+",
        "  |                         v  |      |        | PD_CPU (switchable)|",
        "  |   [ISO] <---------------+--|------|--------|  outputs           |",
        "  |   clamp 0                  +------|------->|  retention flops   |",
        "  |   [LS] <------------------------- |--------|  (save/restore)    |",
        "  +-----------------------------------+        +--------------------+",
    ], "Figure 19.2 - A switchable CPU domain. Isolation cells clamp its "
       "outputs while it is off, retention flops keep selected state on the "
       "always-on supply, and level shifters (LS) are needed if the two "
       "domains run at different voltages.")
    tbl(["Special cell", "Why it is needed", "RTL designer's responsibility"],
        [["**Power switch** (header/footer)",
          "Connects the domain's virtual supply to the real one; many small "
          "switches are daisy-chained to limit inrush current",
          "Generate `pwr_en`, wait for `pwr_ack` before continuing"],
         ["**Isolation cell**", "An off domain's outputs float to X and can "
          "cause crowbar current and wrong values downstream; isolation "
          "clamps them to 0/1/latched", "Decide safe clamp values (a "
          "request must clamp to 'no request'); drive `iso_en` from "
          "always-on logic"],
         ["**Retention flop**", "A flop with a shadow (balloon) latch on "
          "the always-on supply: `save` copies state out, `restore` copies "
          "it back", "Choose what must be retained (costs area and leakage); "
          "reinitialise the rest after power-up"],
         ["**Level shifter**", "Signals from low to high voltage domains do "
          "not switch the receiving PMOS fully off", "Know every crossing; "
          "avoid needless crossings in the architecture"],
         ["**Always-on buffers**", "Buffers inside a switchable domain that "
          "carry always-on signals", "Minimise such feed-throughs"]],
        widths=[20, 44, 36], bold_first=True)
    h3("The power-down / power-up sequence")
    p("The sequence is the heart of a power-gated design, and it is ordinary "
      "RTL: an FSM in the always-on domain. Power down: **stop clocks -> "
      "isolate -> save -> switch off**. Power up: **switch on and wait for "
      "ack -> restore -> de-isolate -> start clocks**. (Some flows also "
      "assert reset to the non-retained flops during power-up.)")
    code(r'''// Power-gating sequencer for one switchable domain (lives in always-on logic)
module pd_seq (
  input  wire clk, rst_n,          // always-on clock and reset
  input  wire sleep_req, wake_req,
  input  wire pwr_ack,             // from the last switch in the daisy chain
  output reg  clk_en,              // 1 = domain clock running
  output reg  iso_en,              // 1 = outputs clamped
  output reg  save,                // pulse: retention flops save state
  output reg  restore,             // pulse: retention flops restore state
  output reg  pwr_en,              // 1 = power switches on
  output reg  [2:0] st
);
  localparam [2:0] ON = 3'd0, STOP = 3'd1, ISO = 3'd2, SAVE = 3'd3,
                   OFF = 3'd4, PWRUP = 3'd5, RESTORE = 3'd6, UNISO = 3'd7;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      st <= ON; clk_en <= 1; iso_en <= 0; save <= 0; restore <= 0; pwr_en <= 1;
    end else begin
      save <= 0; restore <= 0;
      case (st)
        ON:      if (sleep_req) begin clk_en <= 0; st <= STOP; end
        STOP:    begin iso_en <= 1;  st <= ISO;  end      // 1. clocks off
        ISO:     begin save   <= 1;  st <= SAVE; end      // 2. isolate
        SAVE:    begin pwr_en <= 0;  st <= OFF;  end      // 3. save, 4. off
        OFF:     if (wake_req) begin pwr_en <= 1; st <= PWRUP; end
        PWRUP:   if (pwr_ack) begin restore <= 1; st <= RESTORE; end
        RESTORE: begin iso_en <= 0;  st <= UNISO; end
        UNISO:   begin clk_en <= 1;  st <= ON;   end
      endcase
    end
endmodule''')
    code(r'''module tb_pmu;
  reg clk = 0, rst_n = 0, sleep_req = 0, wake_req = 0, pwr_ack = 1;
  wire clk_en, iso_en, save, restore, pwr_en; wire [2:0] st;
  pd_seq dut (.*);
  always #5 clk = ~clk;
  always @(posedge pwr_en)  #30 pwr_ack = 1;       // switches take 3 cycles
  always @(negedge pwr_en)  pwr_ack = 0;
  reg [5*8-1:0] nm [0:7];
  initial begin
    nm[0]="ON"; nm[1]="STOP"; nm[2]="ISO"; nm[3]="SAVE";
    nm[4]="OFF"; nm[5]="PWRUP"; nm[6]="REST"; nm[7]="UNISO";
  end
  always @(negedge clk) if (rst_n)
    $display("%-5s clk_en=%b iso=%b save=%b restore=%b pwr_en=%b ack=%b",
             nm[st], clk_en, iso_en, save, restore, pwr_en, pwr_ack);
  initial begin
    #12 rst_n = 1;
    @(negedge clk) sleep_req = 1; @(negedge clk) sleep_req = 0;
    repeat (4) @(negedge clk);
    wake_req = 1; @(negedge clk) wake_req = 0;
    repeat (6) @(negedge clk);
    $finish;
  end
endmodule''')
    out(["ON    clk_en=1 iso=0 save=0 restore=0 pwr_en=1 ack=1",
         "STOP  clk_en=0 iso=0 save=0 restore=0 pwr_en=1 ack=1",
         "ISO   clk_en=0 iso=1 save=0 restore=0 pwr_en=1 ack=1",
         "SAVE  clk_en=0 iso=1 save=1 restore=0 pwr_en=1 ack=1",
         "OFF   clk_en=0 iso=1 save=0 restore=0 pwr_en=0 ack=0",
         "OFF   clk_en=0 iso=1 save=0 restore=0 pwr_en=0 ack=0",
         "PWRUP clk_en=0 iso=1 save=0 restore=0 pwr_en=1 ack=0",
         "PWRUP clk_en=0 iso=1 save=0 restore=0 pwr_en=1 ack=0",
         "PWRUP clk_en=0 iso=1 save=0 restore=0 pwr_en=1 ack=0",
         "REST  clk_en=0 iso=1 save=0 restore=1 pwr_en=1 ack=1",
         "UNISO clk_en=0 iso=0 save=0 restore=0 pwr_en=1 ack=1",
         "ON    clk_en=1 iso=0 save=0 restore=0 pwr_en=1 ack=1"],
        "The sequencer waits in PWRUP until the switch chain acknowledges. "
        "Isolation is asserted before `save` and power-off, and released "
        "only after `restore` - exactly the order UPF-aware simulation "
        "and static checkers (Synopsys VC LP, Cadence Conformal Low Power) "
        "verify.")
    box("warn", "Pitfall: a plain RTL simulation does not model power",
        "In the simulation above nothing is actually switched off. Only a "
        "**power-aware simulation** (the simulator reads the UPF and "
        "corrupts the state of an off domain to X) shows that a missing "
        "isolation cell lets X leak into the always-on logic, or that a "
        "register you forgot to retain comes back as garbage. Run "
        "power-aware simulation for every power-state transition.")

    h2("UPF: describing power intent")
    p("RTL describes function; the **UPF** file (IEEE 1801, a Tcl-based "
      "format) describes power intent: supplies, domains, switches, "
      "isolation, retention, level shifting and legal power states. The "
      "same UPF drives power-aware simulation, synthesis (which inserts "
      "the special cells), place-and-route, static low-power checks and "
      "equivalence checking. Keeping the intent out of the RTL means the "
      "same RTL can be reused with a different power architecture.")
    code(r'''# ============ soc_top.upf  (IEEE 1801-2013 / UPF 2.1 style) ======================
upf_version 2.1
set_scope /

# ---- supply ports, nets and sets ---------------------------------------------
create_supply_port VDD_AON
create_supply_port VDD_CPU
create_supply_port VSS
create_supply_net  VDD_AON
create_supply_net  VDD_CPU
create_supply_net  VDD_CPU_SW          ;# virtual supply after the switch
create_supply_net  VSS
connect_supply_net VDD_AON -ports VDD_AON
connect_supply_net VDD_CPU -ports VDD_CPU
connect_supply_net VSS     -ports VSS
create_supply_set SS_AON -function {power VDD_AON}    -function {ground VSS}
create_supply_set SS_CPU -function {power VDD_CPU_SW} -function {ground VSS}

# ---- power domains -------------------------------------------------------------
create_power_domain PD_TOP -include_scope -supply {primary SS_AON}
create_power_domain PD_CPU -elements {u_cpu} -supply {primary SS_CPU} \
                           -supply {default_isolation SS_AON} \
                           -supply {default_retention SS_AON}

# ---- power switch (controlled by the always-on sequencer) --------------------
create_power_switch SW_CPU -domain PD_CPU \
    -input_supply_port  {vin  VDD_CPU} \
    -output_supply_port {vout VDD_CPU_SW} \
    -control_port       {sw_en  u_pmu/u_seq/pwr_en} \
    -ack_port           {sw_ack u_pmu/cpu_pwr_ack} \
    -on_state           {on_s  vin {sw_en}} \
    -off_state          {off_s {!sw_en}}

# ---- isolation: clamp CPU outputs to 0 while it is off ----------------------
set_isolation iso_cpu_out -domain PD_CPU -applies_to outputs \
    -isolation_supply_set SS_AON -clamp_value 0 \
    -isolation_signal u_pmu/u_seq/iso_en -isolation_sense high \
    -location parent
# an active-low output must clamp to its INACTIVE value, 1
set_isolation iso_cpu_err -domain PD_CPU -elements {u_cpu/err_n} \
    -isolation_supply_set SS_AON -clamp_value 1 \
    -isolation_signal u_pmu/u_seq/iso_en -isolation_sense high \
    -location parent

# ---- retention of the architectural state only -----------------------------
set_retention ret_cpu -domain PD_CPU -retention_supply_set SS_AON \
    -elements {u_cpu/u_regfile u_cpu/u_csr} \
    -save_signal    {u_pmu/u_seq/save    high} \
    -restore_signal {u_pmu/u_seq/restore high}

# ---- power states ----------------------------------------------------------------
add_power_state SS_AON -state ON  {-supply_expr {power == `{FULL_ON, 0.80}}}
add_power_state SS_CPU -state ON  {-supply_expr {power == `{FULL_ON, 0.80}}}
add_power_state SS_CPU -state OFF {-supply_expr {power == `{OFF}} -simstate CORRUPT}
add_power_state PD_CPU -state RUN   {-logic_expr {SS_CPU == ON}}
add_power_state PD_CPU -state SLEEP {-logic_expr {SS_CPU == OFF}}''',
        "A single-voltage, power-gated CPU domain. With a second voltage "
        "(e.g. VDD_CPU at 0.65 V for low-performance modes) you would add "
        "`set_level_shifter` rules. UPF 3.0 renames some options "
        "(`-isolation_supply`, `-retention_supply`); check the version your "
        "tools accept. Older flows use a power-state table "
        "(`create_pst` / `add_pst_state`).")
    tbl(["UPF command", "Describes"],
        [["`create_supply_port/net`, `connect_supply_net`", "The supply "
          "network: pins of the block and nets inside it"],
         ["`create_supply_set`", "A named bundle (power, ground, optional "
          "wells) that domains and strategies refer to"],
         ["`create_power_domain`", "Which instances share a primary supply "
          "and power behaviour"],
         ["`create_power_switch`", "Switch cells, their control and ack "
          "signals, and on/off conditions"],
         ["`set_isolation`", "Which ports get isolation cells, clamp value, "
          "control signal, where the cells go"],
         ["`set_retention`", "Which registers are retention flops and their "
          "save/restore controls"],
         ["`set_level_shifter`", "Crossings between different voltages"],
         ["`add_power_state`", "Legal supply combinations - the basis for "
          "checking that isolation and shifting cover every state"]],
        widths=[40, 60], bold_first=True)

    h2("DVFS: dynamic voltage and frequency scaling")
    p("DVFS runs a domain at a set of **operating performance points** "
      "(OPPs), e.g. 1.2 GHz @ 0.90 V, 800 MHz @ 0.75 V, 400 MHz @ 0.60 V. "
      "Software (the OS governor) picks the OPP; the hardware changes the "
      "PLL/divider and asks the PMIC or an on-chip regulator for the new "
      "voltage - **raise voltage before frequency, lower frequency before "
      "voltage**. RTL implications:")
    bul(["Glitch-free clock switching between sources (Chapter 11) and "
         "clean handshakes with the voltage regulator (with timeouts).",
         "Every OPP is a separate timing-signoff scenario: the slowest "
         "corner at the lowest voltage often sets the design, and hold "
         "must be met at every voltage.",
         "Asynchronous interfaces to fixed-voltage domains need level "
         "shifters and CDC treatment, because their relative frequencies "
         "change at run time.",
         "**AVS** (adaptive voltage scaling) closes the loop with on-die "
         "delay monitors (ring oscillators, critical-path replicas) to "
         "trim the margin for each chip."])

    h2("Power estimation flow")
    p("Power numbers are only as good as the activity that drives them. "
      "Tools default to **vectorless** estimation (a guessed toggle rate "
      "such as 10-20% on inputs, propagated through the logic), which is "
      "fine for early comparison and useless for signoff.")
    diagram([
        "  testbench running a REAL workload window (boot, inference, idle ...)",
        "        |                                  |",
        "        v                                  v",
        "  VCD / FSDB (every transition,       SAIF (toggle counts + time at 0/1",
        "   time-based, huge)                   per net, compact, averaged)",
        "        |                                  |",
        "        v                                  v",
        "  time-based power: peak / di-dt,     average power: synthesis power",
        "  IR-drop vectors (PrimePower,        optimisation, PrimePower/Joules/",
        "  Voltus, Joules)                     PowerArtist averages",
    ], "Figure 19.3 - Activity files. RTL activity can be mapped onto the "
       "netlist by name, which is another reason to keep register names "
       "stable through synthesis.")
    code(r'''# Averaged power with SAIF activity (Design Compiler / PrimePower style)
read_saif -input sim/inference.saif -instance_name tb_top/u_dut
report_power -hierarchy > rpt/power_hier.rpt

# Time-based power from a VCD window in PrimePower
set_app_var power_analysis_mode time_based
read_vcd -strip_path tb_top/u_dut sim/inference.vcd
update_power
report_power''', "Tool-specific commands differ; the concepts are the "
      "same everywhere. Simulators (including Icarus via `$dumpfile` / "
      "`$dumpvars`) write VCD; commercial simulators also write SAIF "
      "directly.")
    box("tip", "Power is an RTL review item",
        "Early RTL power tools (PowerArtist, Joules, PrimePower RTL) report "
        "clock-gating efficiency, wasted memory reads and redundant "
        "toggles per register - with pointers to RTL lines. Run them at "
        "each milestone, not after tapeout.")

    h2("Summary")
    bul(["P_dyn = alpha x C x V^{2} x f and leakage grows exponentially as "
         "Vt drops and temperature rises; clocks are the largest single "
         "dynamic consumer.",
         "Clock gating uses latch-based ICG cells, never AND gates; write "
         "clean shared enables and let synthesis insert ICGs; tie `te` for "
         "scan.",
         "Operand isolation, data gating, memory-access reduction and "
         "narrower datapaths cut switching at the source.",
         "Power gating needs switches, isolation, retention and a "
         "sequencer: stop clocks, isolate, save, off - and the reverse.",
         "UPF describes supplies, domains, switches, isolation, retention, "
         "level shifters and power states for every tool in the flow.",
         "DVFS trades voltage and frequency at run time; each OPP is a "
         "signoff scenario. Estimate power with SAIF/VCD from real "
         "workloads."])
    h2("Exercises")
    bul(["A block has C = 2 nF of switched capacitance with alpha = 0.15 at "
         "1 GHz and 0.8 V. Compute its dynamic power, then at 700 MHz and "
         "0.7 V. What fraction is saved?",
         "Extend `icg` into a negative-edge version (for flops clocked on "
         "the falling edge). Which gate and which latch phase do you need?",
         "Add a `pwr_ack` timeout to `pd_seq` that raises an error flag if "
         "the switches do not acknowledge within 64 cycles, and test it.",
         "Choose clamp values for these outputs of a powered-off DMA: "
         "`req`, `busy`, `irq`, `err_n`, `axi_awvalid`. Justify each.",
         "Write the UPF lines needed if `PD_CPU` runs at 0.65 V while "
         "`PD_TOP` stays at 0.8 V. Which direction of crossing strictly "
         "requires a level shifter, and why?"],
        ordered=True)


# =============================================================================
#                  CHAPTER 20 - DESIGN FOR TEST: SCAN, BIST, JTAG
# =============================================================================
def _ch20():
    chapter("Design for Test: Scan, BIST, JTAG")
    p("Verification asks 'is the design correct?'. **Manufacturing test** "
      "asks a different question about every single die that comes off the "
      "wafer: 'was this copy of the correct design built correctly?'. A "
      "particle, a thin via or a bridged metal line turns a perfect design "
      "into a broken chip, and a broken chip that reaches a customer costs "
      "orders of magnitude more than one caught at wafer sort. Automotive "
      "customers ask for defect rates in the low single-digit **DPPM** "
      "(defective parts per million).")
    p("Test is only possible if the design lets a tester **control** every "
      "internal node and **observe** its effect. Design for test (DFT) is "
      "the set of structures - scan chains, BIST engines, JTAG - and RTL "
      "rules that provide this. Much of it is inserted by tools, but the "
      "tools can only insert it into RTL that follows the rules, and the "
      "RTL designer owns the clocking, reset and memory decisions that "
      "make or break test coverage.")

    h2("Fault models")
    p("Physical defects are infinitely varied, so test generation targets "
      "abstract **fault models** that correlate well with real defects.")
    tbl(["Model", "Definition", "How it is tested"],
        [["**Stuck-at (SA0/SA1)**", "A pin or net is permanently 0 or 1",
          "Static patterns at slow speed; the baseline, targets > 99%"],
         ["**Transition (STR/STF)**", "A node is slow-to-rise or slow-to-"
          "fall by more than a cycle",
          "At-speed: launch a transition, capture one functional period "
          "later (launch-on-capture or launch-on-shift)"],
         ["**Path delay**", "Accumulated small delays along a specific path",
          "At-speed patterns on selected critical paths"],
         ["**Bridging**", "Two nets shorted (wired-AND/OR or dominant)",
          "Patterns using layout-extracted neighbour pairs"],
         ["**Cell-aware**", "Defects inside a standard cell (from transistor-"
          "level simulation of the layout)", "Extra patterns per cell type; "
          "significant DPPM improvement at advanced nodes"],
         ["**IDDQ**", "Abnormal quiescent current from a defect",
          "Current measurement; weak at advanced nodes because of leakage"]],
        widths=[20, 42, 38], bold_first=True)
    _eqa(["Fault coverage = detected faults / total faults",
        "",
        "Test coverage  = detected faults / (total faults - untestable faults)"],
       "Test coverage excludes faults that are provably untestable "
       "(redundant logic, tied nets). Coverage lost to **uncontrollable** or "
       "**unobservable** logic - the DFT-unfriendly RTL of Section 20.3 - "
       "counts against you in both.")

    h2("Scan: turning sequential test into combinational test")
    p("Testing a sequential circuit directly requires sequences of inputs "
      "to steer it into each state - intractable for millions of flops. "
      "**Scan** replaces every flop with a **scan flop** - a flop with a "
      "2:1 mux on its D input - and links them into shift registers "
      "(**scan chains**). In **shift** mode (scan enable = 1) the tester "
      "loads any state into every flop and unloads the previous contents; "
      "in **capture** mode (scan enable = 0) one functional clock captures "
      "the response of the combinational logic. Sequential test becomes "
      "combinational test between flop boundaries, which ATPG can solve.")
    diagram([
        "           SE                  SE                  SE",
        "           |                   |                   |",
        "  SI --->|\\ |  +-----+   +--->|\\ |  +-----+  +---->|\\ |  +-----+",
        "         |M|-->|D   Q|---+    |M|-->|D   Q|--+     |M|-->|D   Q|---+--> SO",
        "  d0 --->|/    |>    |   |  d1|/    |>    |  |   d2|/    |>    |   |",
        "          ^    +-----+   |     ^    +-----+  |      ^    +-----+   |",
        "          |      q0 -----+-----|------------------> logic         |",
        "      comb logic <-------------+----- q1 ----+----> logic         |",
        "",
        "  shift  (SE=1): SI -> q0 -> q1 -> q2 -> SO   (load new state, unload old)",
        "  capture(SE=0): q <= d  (combinational response captured into the flops)",
    ], "Figure 20.1 - Mux-D scan flops stitched into a chain. The scan "
       "path is a direct Q-to-SI connection, which is why scan chains are "
       "a classic source of hold violations.")
    p("The following model shows exactly what scan insertion produces for a "
      "4-bit incrementer, and the three-phase test procedure the tester "
      "runs: shift in a stimulus, capture once, shift out the response.")
    code(r'''// A mux-D scan flop: SE selects the scan input instead of functional D
module sdff (input wire clk, rst_n, d, si, se, output reg q);
  always @(posedge clk or negedge rst_n)
    if (!rst_n) q <= 1'b0;
    else        q <= se ? si : d;
endmodule

// A 4-bit incrementer register after scan insertion (what DFT tools produce)
module inc4_scan (
  input  wire clk, rst_n, se, si,
  output wire so,
  output wire [3:0] q
);
  wire [3:0] d = q + 4'd1;                  // functional logic under test
  sdff f0 (.clk(clk), .rst_n(rst_n), .d(d[0]), .si(si),   .se(se), .q(q[0]));
  sdff f1 (.clk(clk), .rst_n(rst_n), .d(d[1]), .si(q[0]), .se(se), .q(q[1]));
  sdff f2 (.clk(clk), .rst_n(rst_n), .d(d[2]), .si(q[1]), .se(se), .q(q[2]));
  sdff f3 (.clk(clk), .rst_n(rst_n), .d(d[3]), .si(q[2]), .se(se), .q(q[3]));
  assign so = q[3];
endmodule''')
    code(r'''module tb_scan;
  reg clk = 0, rst_n = 0, se = 0, si = 0;
  wire so; wire [3:0] q;
  inc4_scan dut (.*);
  always #5 clk = ~clk;
  integer i; reg [3:0] pat = 4'b0111, resp;
  initial begin
    #12 rst_n = 1;
    se = 1;                                 // 1) shift in: last bit in = q[0]
    for (i = 3; i >= 0; i = i - 1) begin
      @(negedge clk) si = pat[i];
    end
    @(negedge clk) se = 0;                  // 2) capture: one functional clock
    $display("loaded   q = %b", q);
    @(negedge clk) se = 1;
    $display("captured q = %b (expect %b)", q, pat + 4'd1);
    for (i = 3; i >= 0; i = i - 1) begin    // 3) shift out through so
      resp[i] = so;
      @(negedge clk);
    end
    $display("unloaded   = %b -> %s", resp, (resp == pat + 4'd1) ? "PASS" : "FAIL");
    $finish;
  end
endmodule''')
    out(["loaded   q = 0111",
         "captured q = 1000 (expect 1000)",
         "unloaded   = 1000 -> PASS"],
        "A stuck-at-0 on the carry into bit 3 would have unloaded 0000 - "
        "detected. The pattern 0111 was chosen to exercise the full carry "
        "chain; ATPG chooses patterns the same way, for every fault.")
    h3("Scan compression, ATPG and test time")
    p("A modern SoC has millions of flops but a tester offers only a "
      "handful of scan pins. **Scan compression** (Synopsys DFTMAX, "
      "Siemens Tessent EDT, Cadence Modus) places a decompressor between "
      "a few scan-in channels and hundreds of short internal chains, and a "
      "compactor (XOR network, with X-masking) on the way out. Compression "
      "ratios of 50-200x are common.")
    _eqa(["test time ~ patterns x (flops per chain + capture cycles) / f_shift",
        "",
        "example:  2,000,000 flops / 400 internal chains = 5,000 flops per chain",
        "          4,000 patterns x 5,000 / 50 MHz            = 0.4 s per die"],
       "Without compression, the same design on 8 external chains would "
       "need 250,000-flop chains and 50x the test time. Shift is usually "
       "slow (25-100 MHz) to limit IR drop from millions of flops toggling "
       "together.")
    p("**ATPG** (automatic test pattern generation) uses algorithms in the "
      "D-algorithm / PODEM / FAN family plus SAT solvers: for each fault it "
      "finds an input assignment that **activates** the fault (drives the "
      "opposite value onto the node) and **propagates** the difference to "
      "an observable flop. Compaction then merges patterns. The RTL "
      "designer's job is to make sure nothing blocks controllability or "
      "observability.")

    h2("DFT-friendly RTL rules")
    tbl(["Rule", "Why", "How"],
        [["**Clocks controllable from a pin in test mode**",
          "ATPG must pulse every flop's clock exactly when it wants; "
          "PLLs, dividers and gated clocks are not controllable",
          "Test-clock mux at the root of each clock (OCC - on-chip clock "
          "controllers - for at-speed); ICG `te` tied to scan enable"],
         ["**Async resets/sets controllable**",
          "An internally generated reset firing during shift corrupts the "
          "chain", "Mux the reset with a test pin; synchronizer outputs "
          "bypassed in test mode"],
         ["**No latches** (or transparent in test)",
          "Latches are not scannable and block propagation",
          "Use flops; force latches transparent with `test_mode`"],
         ["**No combinational loops**", "ATPG cannot model them",
          "Lint; break loops with a flop"],
         ["**No clocks used as data / data used as clocks**",
          "Unpredictable capture", "Synchronise instead"],
         ["**Handle memories and analog**",
          "SRAM outputs are X in scan unless modelled; macros are black "
          "boxes to ATPG", "MBIST plus bypass/observe logic around each "
          "macro; wrappers for analog"],
         ["**No X sources on scan paths**",
          "Uninitialised data corrupts compressed responses",
          "Initialise or mask; avoid floating tri-states"],
         ["**Static test signals**", "`test_mode` must be constant during "
          "test; `scan_en` must be timed", "Top-level pins or a TAP data "
          "register (JTAG) drive them"]],
        widths=[27, 38, 35], bold_first=True)
    code(r'''// DFT-friendly reset and clock control: the tester owns both in test mode
module dft_ctrl (
  input  wire func_clk,      // e.g. PLL output / divided clock
  input  wire test_clk,      // dedicated tester clock pin
  input  wire rst_n_sync,    // functional reset (after the reset synchronizer)
  input  wire test_rst_n,    // reset pin driven directly by the tester
  input  wire test_mode,     // static: tied by the tester for the whole test
  output wire core_clk,
  output wire core_rst_n
);
  // In a real netlist these are library clock-mux cells, instantiated and
  // marked dont_touch; the RTL form below is for simulation and lint.
  assign core_clk   = test_mode ? test_clk   : func_clk;
  assign core_rst_n = test_mode ? test_rst_n : rst_n_sync;
endmodule''', "Compiled and simulated with iverilog (a small testbench "
      "checks both modes). In functional mode STA sets `test_mode = 0` "
      "with `set_case_analysis`; a separate scan-mode SDC sets it to 1.")
    box("warn", "Pitfall: the clock divider that eats your coverage",
        "A block clocked by `clk_div2` from a flop-based divider has no "
        "controllable clock in scan mode: the divider flop is itself in a "
        "scan chain, so shifting scrambles the derived clock. Every flop "
        "downstream is lost to ATPG. The fix is the same as above: a "
        "test-clock mux after the divider, planned in the RTL.")

    h2("Memory BIST")
    p("Embedded SRAMs occupy a large fraction of an SoC's area and are the "
      "densest - hence most defect-prone - structures on it. They are "
      "tested by **MBIST**: an on-chip controller that writes and reads "
      "algorithmic patterns at speed and compares the results. Failures "
      "can drive **repair** (spare rows/columns programmed by eFuses). "
      "The standard algorithms are **March tests**: sequences of "
      "read/write elements applied to every address in ascending or "
      "descending order.")
    _eqa(["March C- :  {c(w0); up(r0,w1); up(r1,w0); dn(r0,w1); dn(r1,w0); c(r0)}",
        "",
        "operations = 1 + 2 + 2 + 2 + 2 + 1 = 10 per address  ->  10N",
        "detects: stuck-at, transition, address-decoder and most coupling faults"],
       "c = either address order. A March test with N = 64k words costs "
       "655,360 cycles - under 1 ms at 1 GHz.")
    code(r'''// March C- MBIST engine:  {c(w0); up(r0,w1); up(r1,w0); dn(r0,w1); dn(r1,w0); c(r0)}
// One operation per clock; the memory model here has a combinational read.
module mbist_marchc #(parameter int AW = 4, parameter int DW = 8) (
  input  wire          clk, rst_n, start,
  output reg           busy, done, fail,
  output reg  [AW-1:0] fail_addr,
  output wire          mem_we,
  output wire [AW-1:0] mem_addr,
  output wire [DW-1:0] mem_wdata,
  input  wire [DW-1:0] mem_rdata
);
  reg [2:0]    elem;             // March element 0..5
  reg          op;               // operation index inside the element
  reg [AW-1:0] cnt;              // address counter (always counts up)
  reg          nops2, up, rd, val;
  always @* begin                // element table
    nops2 = 1'b1; up = 1'b1;
    case (elem)
      3'd0: begin nops2 = 1'b0; rd = 1'b0;   val = 1'b0;   end  // c(w0)
      3'd1: begin rd = (op == 1'b0); val = op;             end  // up(r0,w1)
      3'd2: begin rd = (op == 1'b0); val = ~op;            end  // up(r1,w0)
      3'd3: begin rd = (op == 1'b0); val = op;  up = 1'b0; end  // dn(r0,w1)
      3'd4: begin rd = (op == 1'b0); val = ~op; up = 1'b0; end  // dn(r1,w0)
      default: begin nops2 = 1'b0; rd = 1'b1; val = 1'b0; end   // c(r0)
    endcase
  end
  assign mem_addr  = up ? cnt : ~cnt;
  assign mem_we    = busy & ~rd;
  assign mem_wdata = {DW{val}};
  wire last_op   = !nops2 || op;
  wire last_addr = &cnt;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      busy <= 0; done <= 0; fail <= 0; fail_addr <= '0;
      elem <= 0; op <= 0; cnt <= '0;
    end else if (start && !busy) begin
      busy <= 1; done <= 0; fail <= 0; elem <= 0; op <= 0; cnt <= '0;
    end else if (busy) begin
      if (rd && mem_rdata != {DW{val}} && !fail) begin
        fail <= 1; fail_addr <= mem_addr;          // log the first failure
      end
      if (!last_op) op <= 1'b1;
      else begin
        op <= 1'b0;
        cnt <= cnt + 1'b1;
        if (last_addr) begin
          if (elem == 3'd5) begin busy <= 0; done <= 1; end
          else elem <= elem + 1'b1;
        end
      end
    end
endmodule''')
    code(r'''// 16x8 RAM model with an optional stuck-at-1 fault on bit 3 of word 5
module ram_model #(parameter bit FAULT = 0) (
  input wire clk, we, input wire [3:0] addr, input wire [7:0] wdata,
  output wire [7:0] rdata
);
  reg [7:0] m [0:15];
  always @(posedge clk) if (we) m[addr] <= wdata;
  assign rdata = (FAULT && addr == 4'd5) ? (m[addr] | 8'h08) : m[addr];
endmodule

module tb_mbist;
  reg clk = 0, rst_n = 0, start = 0;
  always #5 clk = ~clk;
  wire b0, d0, f0, b1, d1, f1, we0, we1; wire [3:0] fa0, fa1, a0, a1;
  wire [7:0] wd0, wd1, rd0, rd1;
  mbist_marchc u0 (.clk(clk), .rst_n(rst_n), .start(start), .busy(b0), .done(d0),
                   .fail(f0), .fail_addr(fa0), .mem_we(we0), .mem_addr(a0),
                   .mem_wdata(wd0), .mem_rdata(rd0));
  ram_model #(0) m0 (.clk(clk), .we(we0), .addr(a0), .wdata(wd0), .rdata(rd0));
  mbist_marchc u1 (.clk(clk), .rst_n(rst_n), .start(start), .busy(b1), .done(d1),
                   .fail(f1), .fail_addr(fa1), .mem_we(we1), .mem_addr(a1),
                   .mem_wdata(wd1), .mem_rdata(rd1));
  ram_model #(1) m1 (.clk(clk), .we(we1), .addr(a1), .wdata(wd1), .rdata(rd1));
  integer cyc = 0;
  always @(posedge clk) if (b0) cyc = cyc + 1;
  initial begin
    #12 rst_n = 1;
    @(negedge clk) start = 1; @(negedge clk) start = 0;
    wait (d0 && d1);
    $display("good RAM  : done=%b fail=%b  (%0d cycles = 10N, N=16)", d0, f0, cyc);
    $display("faulty RAM: done=%b fail=%b  first fail at word %0d", d1, f1, fa1);
    $finish;
  end
endmodule''')
    out(["good RAM  : done=1 fail=0  (160 cycles = 10N, N=16)",
         "faulty RAM: done=1 fail=1  first fail at word 5"],
        "The engine executes exactly 10N operations and locates the injected "
        "stuck-at-1 fault. Production MBIST (Tessent MemoryBIST, Synopsys "
        "STAR Memory System) adds pipelined compare for synchronous-read "
        "SRAMs, multiple data backgrounds, diagnosis and repair analysis.")

    h2("Logic BIST")
    p("**LBIST** puts the tester on the chip: an LFSR-based **PRPG** "
      "(pseudo-random pattern generator) feeds the scan chains, and a "
      "**MISR** (multiple-input signature register) compacts the responses "
      "into a signature compared against a golden value - the STUMPS "
      "architecture. It needs no external patterns, so it runs in the "
      "field: automotive (ISO 26262) parts run LBIST at every key-on and "
      "periodically to detect latent faults. Costs: **X-bounding** (a "
      "single X corrupts the signature, so every X source must be blocked), "
      "**test points** to reach random-pattern-resistant logic (wide AND "
      "trees), and the area of the controller.")

    h2("JTAG: the TAP controller and boundary scan")
    p("IEEE 1149.1 (JTAG) defines a 4/5-wire serial port - TCK, TMS, TDI, "
      "TDO and optional TRST - and a **Test Access Port** (TAP) "
      "controller: a 16-state FSM advanced by TMS on every rising TCK. "
      "It was created for **boundary scan** (testing board interconnect), "
      "and became the universal access port for everything else: scan "
      "control, MBIST start/status, eFuse programming and processor debug.")
    diagram([
        "  Test-Logic-Reset --0--> Run-Test/Idle --1--> Select-DR --1--> Select-IR --1--> TLR",
        "                                                  | 0              | 0",
        "                                                  v                v",
        "                                             Capture-DR       Capture-IR",
        "                                                  | 0              | 0",
        "        (TMS=0 loops in Shift and Pause)          v                v",
        "                                              Shift-DR  <-+    Shift-IR  <-+",
        "                                                  | 1     |        | 1     |",
        "                                                  v       | 0      v       | 0",
        "                                              Exit1-DR    |    Exit1-IR    |",
        "                                                  | 0     |        | 0     |",
        "                                                  v       |        v       |",
        "                                              Pause-DR    |    Pause-IR    |",
        "                                                  | 1     |        | 1     |",
        "                                                  v       |        v       |",
        "                                              Exit2-DR ---+    Exit2-IR ---+",
        "                                                  | 1              | 1",
        "                                                  v                v",
        "                                              Update-DR        Update-IR",
        "",
        "  Also: Capture-xR --1--> Exit1-xR;  Exit1-xR --1--> Update-xR;",
        "        Update-xR --1--> Select-DR, --0--> Run-Test/Idle;  TLR and RTI loop on 1 / 0.",
    ], "Figure 20.2 - The 1149.1 TAP state diagram (the DR and IR columns are "
       "identical). Capture loads the selected register, Shift moves it one "
       "bit per TCK, Update transfers it to the parallel output. From any "
       "state, five TCKs with TMS = 1 reach Test-Logic-Reset.")
    p("The following implementation encodes the states with the widely "
      "used 4-bit codes from the standard's examples and adds a minimal "
      "instruction register with IDCODE (selected at reset, as the "
      "standard requires when IDCODE exists) and BYPASS (all ones).")
    code(r'''// IEEE 1149.1 TAP controller: 16 states, advanced by TMS on rising TCK
module tap_ctrl (
  input  wire       tck, trst_n, tms,
  output reg  [3:0] state
);
  localparam [3:0]
    TLR = 4'hF, RTI = 4'hC,
    SEL_DR = 4'h7, CAP_DR = 4'h6, SH_DR = 4'h2, EX1_DR = 4'h1,
    PAU_DR = 4'h3, EX2_DR = 4'h0, UPD_DR = 4'h5,
    SEL_IR = 4'h4, CAP_IR = 4'hE, SH_IR = 4'hA, EX1_IR = 4'h9,
    PAU_IR = 4'hB, EX2_IR = 4'h8, UPD_IR = 4'hD;
  reg [3:0] nxt;
  always @* begin
    case (state)
      TLR:    nxt = tms ? TLR    : RTI;
      RTI:    nxt = tms ? SEL_DR : RTI;
      SEL_DR: nxt = tms ? SEL_IR : CAP_DR;
      CAP_DR: nxt = tms ? EX1_DR : SH_DR;
      SH_DR:  nxt = tms ? EX1_DR : SH_DR;
      EX1_DR: nxt = tms ? UPD_DR : PAU_DR;
      PAU_DR: nxt = tms ? EX2_DR : PAU_DR;
      EX2_DR: nxt = tms ? UPD_DR : SH_DR;
      UPD_DR: nxt = tms ? SEL_DR : RTI;
      SEL_IR: nxt = tms ? TLR    : CAP_IR;
      CAP_IR: nxt = tms ? EX1_IR : SH_IR;
      SH_IR:  nxt = tms ? EX1_IR : SH_IR;
      EX1_IR: nxt = tms ? UPD_IR : PAU_IR;
      PAU_IR: nxt = tms ? EX2_IR : PAU_IR;
      EX2_IR: nxt = tms ? UPD_IR : SH_IR;
      UPD_IR: nxt = tms ? SEL_DR : RTI;
      default: nxt = TLR;
    endcase
  end
  always @(posedge tck or negedge trst_n)
    if (!trst_n) state <= TLR;
    else         state <= nxt;
endmodule''')
    code(r'''// Minimal TAP: 4-bit IR, IDCODE (default after reset) and BYPASS
module tap_top #(parameter [31:0] IDCODE = 32'h1234_5ACF) (  // bit 0 must be 1
  input  wire tck, trst_n, tms, tdi,
  output reg  tdo
);
  localparam [3:0] I_IDCODE = 4'b0001, I_BYPASS = 4'b1111;
  wire [3:0] st;
  tap_ctrl u_fsm (.tck(tck), .trst_n(trst_n), .tms(tms), .state(st));
  reg [3:0]  ir, ir_sh;
  reg [31:0] id_sh;
  reg        byp;
  always @(posedge tck or negedge trst_n)
    if (!trst_n) begin
      ir <= I_IDCODE; ir_sh <= 4'b0; id_sh <= 32'b0; byp <= 1'b0;
    end else begin
      case (st)
        4'hF: ir <= I_IDCODE;                       // Test-Logic-Reset
        4'hE: ir_sh <= 4'b0101;                     // Capture-IR: ...01 pattern
        4'hA: ir_sh <= {tdi, ir_sh[3:1]};           // Shift-IR
        4'hD: ir <= ir_sh;                          // Update-IR
        4'h6: begin id_sh <= IDCODE; byp <= 1'b0; end   // Capture-DR
        4'h2: begin id_sh <= {tdi, id_sh[31:1]}; byp <= tdi; end  // Shift-DR
        default: ;
      endcase
    end
  // TDO changes on the FALLING edge of TCK
  always @(negedge tck or negedge trst_n)
    if (!trst_n)          tdo <= 1'b0;
    else if (st == 4'hA)  tdo <= ir_sh[0];
    else if (st == 4'h2)  tdo <= (ir == I_BYPASS) ? byp : id_sh[0];
endmodule''', "Simplifications for brevity: a real TAP drives TDO only "
      "in Shift states (tri-state otherwise), decodes all IR values "
      "(unknown opcodes select BYPASS), implements the mandatory "
      "SAMPLE/PRELOAD and EXTEST instructions with a boundary-scan "
      "register, and uses the state names instead of raw codes.")
    code(r'''module tb_tap;
  reg tck = 0, trst_n = 0, tms = 1, tdi = 0;
  wire tdo;
  tap_top dut (.*);
  always #50 tck = ~tck;
  task clk_tms(input t, input d); begin
    @(negedge tck) begin tms = t; tdi = d; end
    @(posedge tck);
  end endtask
  integer i, k, fails = 0;
  reg [31:0] id; reg [7:0] bo;
  initial begin
    #120 trst_n = 1;
    // 1) read IDCODE: TLR -> RTI -> Sel-DR -> Cap-DR -> Shift-DR
    clk_tms(0,0); clk_tms(1,0); clk_tms(0,0); clk_tms(0,0);
    for (i = 0; i < 32; i = i + 1) begin
      @(negedge tck) tms = (i == 31);
      @(posedge tck) id[i] = tdo;
    end
    clk_tms(1,0); clk_tms(0,0);                 // Update-DR -> RTI
    $display("IDCODE read = %h", id);
    // 2) load BYPASS: Sel-DR -> Sel-IR -> Cap-IR -> Shift-IR (4 ones)
    clk_tms(1,0); clk_tms(1,0); clk_tms(0,0); clk_tms(0,0);
    for (i = 0; i < 4; i = i + 1) clk_tms(i == 3, 1);
    clk_tms(1,0); clk_tms(0,0);                 // Update-IR -> RTI
    clk_tms(1,0); clk_tms(0,0); clk_tms(0,0);   // -> Shift-DR
    for (i = 0; i < 8; i = i + 1) begin         // shift 8'b1011_0010 through
      @(negedge tck) begin tms = 0; tdi = (8'b1011_0010 >> i) & 1; end
      @(posedge tck) bo[i] = tdo;
    end
    $display("BYPASS: tdi 01001101 -> tdo %b (one TCK of delay)",
             {bo[0], bo[1], bo[2], bo[3], bo[4], bo[5], bo[6], bo[7]});
    // 3) from any state, five TMS=1 clocks reach Test-Logic-Reset
    for (k = 0; k < 200; k = k + 1) begin
      for (i = 0; i < ($random & 15); i = i + 1) clk_tms($random, 0);
      for (i = 0; i < 5; i = i + 1) clk_tms(1, 0);
      #1 if (dut.st !== 4'hF) fails = fails + 1;
    end
    $display("5 x TMS=1 from 200 random states -> TLR, failures = %0d", fails);
    $finish;
  end
endmodule''')
    out(["IDCODE read = 12345acf",
         "BYPASS: tdi 01001101 -> tdo 00100110 (one TCK of delay)",
         "5 x TMS=1 from 200 random states -> TLR, failures = 0"],
        "The IDCODE shifts out LSB first; BYPASS is the one-bit register "
        "that shortens the chain when many devices share a JTAG port; and "
        "the reset property holds from 200 random states.")
    tbl(["IDCODE field", "Bits", "Content"],
        [["Version", "[31:28]", "Silicon revision"],
         ["Part number", "[27:12]", "Assigned by the manufacturer"],
         ["Manufacturer ID", "[11:1]", "JEDEC JEP106 code (bank + ID)"],
         ["Marker", "[0]", "Always 1 - distinguishes IDCODE from BYPASS "
          "(which captures 0)"]],
        widths=[24, 16, 60], bold_first=True)
    h3("Boundary scan and the JTAG family of standards")
    p("**Boundary scan** places a scan cell between each pad and the core. "
      "With `EXTEST` the TAP drives values onto the board from one chip's "
      "output cells and captures them in another chip's input cells, "
      "testing solder joints and traces without any functional software; "
      "`SAMPLE/PRELOAD` snapshots pin values in normal operation. Each "
      "device is described by a **BSDL** file that board-test tools read.")
    tbl(["Standard", "Scope", "Key structures"],
        [["**IEEE 1149.1**", "Board/chip test access; the TAP", "TAP FSM, IR, "
          "BYPASS, IDCODE, boundary-scan register, BSDL"],
         ["**IEEE 1149.6**", "AC-coupled and differential high-speed IO",
          "EXTEST_PULSE/TRAIN"],
         ["**IEEE 1500**", "Test wrappers for embedded cores",
          "Wrapper instruction register (WIR), wrapper boundary register "
          "(WBR), WBY, serial and parallel ports - lets a core be tested in "
          "isolation from its neighbours"],
         ["**IEEE 1687 (IJTAG)**", "Access to on-chip instruments (MBIST, "
          "sensors, PLL tuning, trim registers)", "Reconfigurable scan "
          "networks with **SIBs** (segment insertion bits); ICL describes "
          "the network, PDL the procedures, retargeted automatically"],
         ["**IEEE 1838**", "Test access for 3D stacked dies", "Die wrapper "
          "and flexible parallel port"]],
        widths=[20, 34, 46], bold_first=True)
    box("expert", "Interview insight: why does TDO change on the falling edge?",
        "TDI and TMS are sampled on the rising edge of TCK and TDO is "
        "launched on the falling edge, giving half a TCK period of hold "
        "margin between chained devices on a board whose TCK arrives with "
        "different skews. It is the same reason scan-chain lock-up latches "
        "are inserted between flops in different clock domains on chip.")

    h2("Summary")
    bul(["Manufacturing test targets fault models - stuck-at, transition, "
         "path delay, bridging, cell-aware - and is measured by fault and "
         "test coverage.",
         "Scan replaces flops with mux-D scan flops in chains: shift, "
         "capture, shift. Compression and ATPG make it scale to millions "
         "of flops.",
         "DFT-friendly RTL: controllable clocks and resets in test mode, no "
         "latches or loops, ICG `te` connected, memories and X sources "
         "handled.",
         "MBIST runs March algorithms (March C- = 10N) at speed; LBIST uses "
         "PRPG + MISR for in-field self-test.",
         "The JTAG TAP is a 16-state FSM; IDCODE, BYPASS, boundary scan, "
         "IEEE 1500 wrappers and IEEE 1687 networks build on it."])
    h2("Exercises")
    bul(["List the stuck-at faults of `inc4_scan`'s bit-1 adder logic that "
         "the pattern 0111 does **not** detect, and find a second pattern "
         "that detects them.",
         "Estimate the test time of a 5M-flop design with 800 internal "
         "chains, 6,000 patterns and a 100 MHz shift clock. What happens if "
         "compression is removed and 16 external chains are used?",
         "Extend `mbist_marchc` for a synchronous-read SRAM (data valid one "
         "cycle after the address). Where must the compare be pipelined?",
         "Add a 4-bit user data register (opcode 4'b0100) to `tap_top` that "
         "drives an output `test_mode`, and a testbench that sets it through "
         "JTAG.",
         "Show that four TMS=1 clocks are **not** always enough to reach "
         "Test-Logic-Reset by finding a starting state that needs five."],
        ordered=True)


# =============================================================================
#          CHAPTER 21 - PPA TRADE-OFFS AND THE HAND-OFF TO PHYSICAL DESIGN
# =============================================================================
def _ch21():
    chapter("PPA Trade-offs and the Hand-Off to Physical Design")
    p("Every design decision is ultimately judged on **PPA** - power, "
      "performance and area - under the constraints of schedule and risk. "
      "The previous four chapters looked at each axis through a tool: "
      "synthesis (area), STA (performance), power analysis and UPF "
      "(power), and DFT (testability, which costs all three). This chapter "
      "puts them together: how to reason about trade-offs while the RTL is "
      "still cheap to change, how to write RTL that physical design can "
      "implement, what you hand over, and what happens between hand-off and "
      "tapeout.")

    h2("The PPA triangle")
    diagram([
        "                         Performance",
        "                        (f_max, IPC, latency, throughput)",
        "                              /\\",
        "        pipelining, parallel /  \\  deeper pipelines, LVT cells,",
        "        units, wide buses   /    \\  higher V (DVFS)",
        "                           /      \\",
        "                          /  your  \\",
        "                         /  design  \\",
        "                        /____________\\",
        "                  Area                 Power",
        "    (cost/die, yield, macros)   (dynamic, leakage, peak / IR)",
        "        resource sharing,          clock gating, HVT cells,",
        "        time-multiplexing          power gating, lower V and f",
    ], "Figure 21.1 - Improving one corner usually costs another. The art is "
       "choosing the corner your product needs and not paying for the "
       "others.")
    tbl(["Decision", "Performance", "Power", "Area"],
        [["Add a pipeline stage", "+ f_max, - latency", "+ flops & clock load, "
          "- glitching", "+ flops"],
         ["Duplicate a unit (2 MACs)", "+ throughput", "+ (or - via lower V/f "
          "for the same work)", "+ ~2x unit"],
         ["Share one unit (time-mux)", "- throughput", "- leakage, + muxes",
          "- area"],
         ["LVT instead of HVT cells", "+ speed", "++ leakage", "~0"],
         ["Wider SRAM word, fewer accesses", "+ bandwidth", "- energy per bit",
          "+ macro width"],
         ["Clock gating", "~0 (enable timing)", "-- dynamic", "+ ICGs"],
         ["Power gating", "- wake-up latency", "-- leakage when idle",
          "+ switches, isolation, retention (5-15% of domain)"],
         ["Reduce datapath precision", "+ (shorter carry chains)",
          "- (fewer toggles)", "- (quadratic for multipliers)"]],
        widths=[28, 24, 26, 22], bold_first=True)
    box("key", "Energy per operation is the metric that matters",
        "For battery devices and ML accelerators, compare architectures on "
        "**energy per task** (pJ/op, mJ/inference), not on power. A design "
        "that draws twice the power but finishes in a third of the time and "
        "then power-gates wins. This 'race to idle' argument is why fast "
        "cores with aggressive power gating often beat slow always-on ones.")

    h2("Estimating area from RTL")
    p("You should be able to predict a block's area to within ~30% before "
      "synthesis. Count the three things that dominate: flops, big "
      "arithmetic, and memories; add a multiplier for control logic.")
    _eqa(["cell area  ~  (N_flops x GE_flop + GE_arith + GE_logic) x A_GE  +  A_macros",
        "block area ~  cell area / utilization          (utilization ~ 0.6 - 0.8)",
        "",
        "example:  40,000 scan flops x 7 GE          = 280 kGE",
        "          4 x (16x16 multiplier ~ 2 kGE)      =   8 kGE",
        "          control + muxes (~1.2x flop GE)     = 336 kGE",
        "          total ~ 624 kGE x 0.5 um^2 (28nm-class GE, assumed)   = 0.31 mm^2",
        "          / 0.7 utilization                   = 0.45 mm^2  + SRAM macros"],
       "The GE area is illustrative (roughly 28 nm class); take the real "
       "NAND2X1 area from your library. SRAM area comes from the memory "
       "compiler's datasheet, including its periphery and required "
       "halo/keep-out.")
    tbl(["Structure", "Rough cost", "Remark"],
        [["Flop (scan, with reset)", "6-8 GE", "Often 30-50% of a control-"
          "heavy block"],
         ["N-bit adder", "~7-10 GE per bit (fast adders more)", "Grows when "
          "timing is tight"],
         ["N x N multiplier", "~6-8 x N^{2} GE", "A 32x32 multiplier is ~7-8 "
          "kGE before timing upsizing"],
         ["M:1 mux, W bits", "~(M-1) x W x 2 GE", "Plus wires - see "
          "congestion below"],
         ["Flop-based register file, D x W", "D x W flops + read muxes",
          "Above a few kbit an SRAM macro is smaller and lower power"],
         ["SRAM macro", "From compiler: bit cell ~0.1-0.2 um^2 at 7-16 nm "
          "plus periphery", "Small macros are periphery-dominated"]],
        widths=[28, 36, 36], bold_first=True)

    h2("Floorplan-aware RTL")
    p("Below ~28 nm, wires, not gates, dominate delay across a chip: gate "
      "delay shrinks with each node while the resistance of thin wires "
      "grows. A signal crossing a large SoC may need more than one clock "
      "cycle even with optimal repeaters. RTL written without the floorplan "
      "in mind produces paths that no amount of physical optimisation can "
      "fix.")
    diagram([
        "  +--------------------------------------------------------------+",
        "  | [SRAM][SRAM]                               [SRAM][SRAM]      |",
        "  |   CPU cluster        <---- 4 mm ---->        ML accelerator  |",
        "  |   (PD_CPU)                                   (PD_NPU)        |",
        "  |        \\                                        /            |",
        "  |         +-- [ff]--[ff]--> NoC router <--[ff]--+              |",
        "  |              pipeline flops placed along the route           |",
        "  |                                                              |",
        "  |  [PLL]  [PMU/AON]        DDR PHY + controller     [IO ring]  |",
        "  +--------------------------------------------------------------+",
    ], "Figure 21.2 - A floorplan dictates which paths are long. Register "
       "slices along inter-block routes make them timeable; hierarchy that "
       "mirrors the floorplan lets each partition be implemented alone.")
    bul(["**Hierarchy that matches the floorplan.** Physical partitions "
         "(hard or soft blocks) are cut along module boundaries. A module "
         "that mixes logic destined for opposite corners of the die forces "
         "a flat implementation or long wires.",
         "**Register at partition boundaries.** 'Flop in, flop out' makes "
         "inter-partition paths start and end at flops; the budget is the "
         "whole cycle for the wire. Combinational feed-throughs between "
         "partitions are the hardest paths on a chip.",
         "**Plan pipeline stages for distance.** A rough rule is that a "
         "well-buffered wire covers only a few millimetres per GHz-class "
         "cycle at advanced nodes (and much less on thin lower metals). "
         "Parameterise the number of stages so the physical team can tune "
         "them late without redesign.",
         "**Keep logic near its memory.** SRAM macros are placed first, "
         "usually at partition edges. Memory output data should be "
         "registered close to the macro before travelling.",
         "**Localise high-fanout control.** Broadcast configuration bits "
         "and stall signals should be re-registered locally (Chapter 18); a "
         "single global stall across a large accelerator rarely closes "
         "timing - use elastic buffers or credits instead."])
    code(r'''// Parameterized "wire pipeline": N flop stages that physical design can
// spread along a long route (one stage per ~1-2 mm in an advanced node).
module wire_pipe #(parameter int W = 32, parameter int N = 2) (
  input  wire         clk, rst_n,
  input  wire         in_vld,
  input  wire [W-1:0] in_dat,
  output wire         out_vld,
  output wire [W-1:0] out_dat
);
  reg [W-1:0] dat [0:N];
  reg         vld [0:N];
  always @* begin dat[0] = in_dat; vld[0] = in_vld; end
  genvar i;
  for (i = 1; i <= N; i = i + 1) begin : g_stage
    always @(posedge clk or negedge rst_n)
      if (!rst_n) vld[i] <= 1'b0;
      else        vld[i] <= vld[i-1];
    always @(posedge clk)
      if (vld[i-1]) dat[i] <= dat[i-1];     // data flops need no reset
  end
  assign out_vld = vld[N];
  assign out_dat = dat[N];
endmodule

module tb_wpipe;
  reg clk = 0, rst_n = 0, in_vld = 0; reg [31:0] in_dat = 0;
  wire out_vld; wire [31:0] out_dat;
  wire_pipe #(.W(32), .N(3)) dut (.*);
  always #5 clk = ~clk;
  integer t_in, t_out;
  initial begin
    #12 rst_n = 1;
    @(negedge clk) begin in_vld = 1; in_dat = 32'hCAFE_F00D; t_in = $time; end
    @(negedge clk) in_vld = 0;
    wait (out_vld); t_out = $time;
    $display("out_dat=%h after %0d cycles", out_dat, (t_out - t_in + 5) / 10);
    $finish;
  end
endmodule''')
    out(["out_dat=cafef00d after 3 cycles"],
        "A valid-only pipeline (no back-pressure). The data flops are "
        "enabled by the valid bit, which also gives synthesis a clean clock-"
        "gating enable (Chapter 19). If the path also carries `ready`, "
        "pipeline it with skid buffers or convert to credit-based flow "
        "control (Chapter 10) - a combinational `ready` across 4 mm is the "
        "same long wire in the other direction.")

    h2("Congestion: when RTL makes the chip unroutable")
    p("A netlist can meet timing on paper and still be impossible to route: "
      "there are more wires crossing a region than routing tracks. "
      "Congestion forces the placer to spread cells (worse timing, more "
      "area) or the router to detour (worse timing, DRC violations). Its "
      "root cause is usually a structure in the RTL.")
    tbl(["RTL structure", "Why it congests", "RTL-level remedy"],
        [["**Wide, many-input muxes** (e.g. 64:1 x 128 bits)",
          "All 8,192 input wires converge on one small area",
          "Split into staged muxes placed near their sources; one-hot "
          "AND-OR trees distributed along a bus"],
         ["**Full crossbars** (N x M x W)", "Wires grow as N x M x W; every "
          "master reaches every slave", "Partial crossbar, hierarchical "
          "interconnect, NoC (Chapter 14), narrower paths for rare masters"],
         ["**Barrel shifters / permutation networks**", "log N stages of "
          "long criss-crossing wires", "Restrict shift amounts; pipeline; "
          "use a logarithmic layout-friendly structure"],
         ["**Big register files with many ports**", "Each read port is a "
          "full mux over all entries", "Bank the file; replicate for read "
          "ports; use SRAM macros"],
         ["**Fully associative lookups (CAMs)**", "Every entry compares "
          "against a broadcast key", "Set-associative structures; hash"],
         ["**High-fanout broadcast**", "One net to thousands of pins",
          "Local re-registering, tree distribution"],
         ["**Pin-dense small modules**", "A tiny block with 2,000 ports "
          "cannot be placed without a wire jam", "Rebalance hierarchy; "
          "narrower interfaces"]],
        widths=[27, 35, 38], bold_first=True)
    box("tip", "Ask for an early floorplan trial",
        "Run a quick placement (DC-Topographical/NXT, Genus iSpatial, "
        "Fusion Compiler, or OpenROAD global placement) on early RTL and "
        "look at the congestion map. Hot spots almost always point to one "
        "module and one construct. Fixing it in RTL costs a day; fixing it "
        "after the floorplan is frozen costs weeks.")

    h2("The hand-off to physical design")
    p("Whether you hand off RTL (the physical team runs synthesis) or a "
      "netlist, the deliverable is not just code. The package must let "
      "someone who has never read your RTL implement it correctly, and it "
      "must be **consistent**: the same revision of RTL, constraints, "
      "power intent and DFT setup.")
    tbl(["Deliverable", "Content", "Checked by"],
        [["**RTL + file list**", "Tagged revision, include paths, defines, "
          "top-level parameters", "Lint, CDC/RDC clean (Chapter 25)"],
         ["**Gate-level netlist**", "Synthesised, scan-inserted Verilog",
          "Formal equivalence RTL vs netlist (LEC)"],
         ["**SDC per mode**", "Functional, scan shift, scan capture, "
          "MBIST, low-power modes; exceptions documented", "Constraint "
          "linting (e.g. Synopsys TCM/GCA, Cadence Conformal Constraint "
          "Designer); timing review"],
         ["**UPF**", "Power intent matching the netlist's hierarchy",
          "Static low-power checks; power-aware simulation"],
         ["**Scan DEF + DFT files**", "Scan chain definition (so P&R can "
          "reorder chains by placement), test protocol (.spf), ATPG setup",
          "DFT DRC; ATPG coverage report"],
         ["**Memory and IP list**", "Macro configurations, compiler "
          "versions, LEF/Liberty views, hard-IP integration notes",
          "View consistency checks"],
         ["**Clock specification**", "Clock tree roots, balancing groups, "
          "non-default rules, skew targets, generated clocks",
          "CTS team review"],
         ["**Floorplan guidance**", "Partitioning, macro placement "
          "preferences, pin placement, long-route pipeline stages",
          "Early trial placement"],
         ["**Activity files**", "SAIF/VCD from representative workloads",
          "Power signoff"],
         ["**Known issues / waivers**", "Every lint/CDC/LEC waiver with "
          "justification", "Design review"]],
        widths=[22, 48, 30], bold_first=True)

    h2("ECOs: changing a design after hand-off")
    p("An **engineering change order** (ECO) modifies the netlist directly "
      "instead of re-running synthesis and implementation, preserving months "
      "of timing closure. There are two kinds:")
    bul(["**Timing ECOs** (resize, buffer, swap Vt) made by the physical "
         "team to close the last paths; function unchanged, checked by "
         "equivalence.",
         "**Functional ECOs** fix a bug found late. The RTL is fixed first; "
         "then a tool (Cadence Conformal ECO, Synopsys Formality ECO) "
         "compares the old netlist with the new RTL and generates a minimal "
         "**patch**. The patch is implemented with the smallest possible "
         "physical disturbance and LEC must pass against the new RTL.",
         "**Pre-mask vs post-mask.** Before masks are made, any cell can be "
         "added. After the base layers are fabricated, a **metal-only ECO** "
         "can rewire only metal layers, using **spare cells** (NAND, NOR, "
         "inverters, muxes, flops sprinkled across the die and tied off) or "
         "**ECO filler / gate-array cells** that can be personalised in "
         "metal. A metal-only fix saves the cost and weeks of new base-layer "
         "masks."])
    box("expert", "Design for ECO from the RTL",
        "Experienced teams add **chicken bits** - configuration register "
        "bits that disable new or risky features (a prefetcher, an "
        "optimisation, a bypass path) - so a silicon bug can be worked "
        "around in software. They also keep ECO-prone logic in its own "
        "hierarchy with boundary optimisation off, reserve spare register "
        "bits in CSR blocks, and write RTL whose synthesised names are "
        "predictable, so that the patch touches only a few cells.")

    h2("Signoff, seen from the RTL seat")
    tbl(["Signoff check", "What it verifies", "How RTL can cause a failure"],
        [["**STA (MCMM, SI)**", "Setup/hold in every mode and corner "
          "including crosstalk delta-delay", "Too many logic levels, wrong "
          "exceptions, unregistered block boundaries"],
         ["**Formal equivalence (LEC)**", "RTL == netlist after every "
          "transformation", "Sim/synth mismatches, `x`-assignments, "
          "retiming without setup"],
         ["**IR drop (static/dynamic)**", "Supply droop under current "
          "draw", "Massive simultaneous switching (all MACs start on one "
          "edge, clock-gate wake-up of a whole domain, scan shift); "
          "stagger enables"],
         ["**Electromigration (EM)**", "Long-term wire wear from current "
          "density", "Very high-activity nets, big clock drivers"],
         ["**DRC / LVS / antenna**", "Layout obeys foundry rules and "
          "matches the netlist", "Rarely RTL - but congestion makes DRC "
          "closure hard"],
         ["**Low-power static checks**", "Isolation, level shifting, "
          "retention and always-on paths consistent with UPF", "Unisolated "
          "outputs, signals crossing domains outside the plan"],
         ["**DFT signoff**", "Coverage targets, pattern count, test time",
          "Uncontrollable clocks/resets, X sources"],
         ["**Gate-level simulation**", "Reset, X-propagation, timing "
          "(SDF) sanity", "Missing resets, reliance on initial values "
          "(Chapter 26)"]],
        widths=[22, 36, 42], bold_first=True)

    h2("The tapeout checklist")
    checklist("RTL owner's tapeout checklist", [
        "RTL frozen and tagged; every late change covered by regression "
        "and LEC against the tagged netlist.",
        "Lint, CDC and RDC clean with all waivers reviewed and signed.",
        "Functional and code coverage closed against the verification plan "
        "(Chapters 22-24).",
        "Every SDC exception traceable to an RTL mechanism; constraint "
        "checks clean in all modes.",
        "UPF reviewed: domains, isolation clamp values, retention list and "
        "power-state table match the architecture; power-aware sim of all "
        "transitions passed.",
        "DFT: coverage targets met (stuck-at, transition), MBIST passing "
        "on all memories, JTAG IDCODE correct, test modes documented.",
        "Gate-level simulations with SDF (min/max) passed for boot, reset "
        "and key test cases.",
        "Chicken bits and spare cells in place; ECO strategy agreed.",
        "Register map, IDCODE, version registers and documentation "
        "match the silicon revision.",
        "Silicon bring-up plan written: first tests, debug access, known "
        "risks and their workarounds."])

    h2("Summary")
    bul(["PPA decisions are made in the architecture and the RTL; compare "
         "alternatives on energy per task and area per throughput.",
         "Estimate area from flop count, arithmetic and memories before "
         "synthesis; know the cost of muxes and multipliers.",
         "Write floorplan-aware RTL: hierarchy that matches partitions, "
         "registered boundaries, parameterised wire pipelines, local "
         "control.",
         "Wide muxes, crossbars, shifters and multi-port register files "
         "cause congestion; fix them in RTL.",
         "The hand-off is a consistent package: RTL/netlist, SDC, UPF, scan "
         "DEF, memory list, clock spec and documented waivers.",
         "Functional ECOs use generated patches and spare cells; chicken "
         "bits provide software escape hatches; signoff covers timing, "
         "equivalence, power integrity, physical rules and test."])
    h2("Exercises")
    bul(["Estimate the area of a block with 25k flops, eight 16x16 "
         "multipliers, a 32:1 x 64-bit mux and 256 kbit of SRAM. State your "
         "assumptions.",
         "A 4x4 crossbar with 128-bit data is congested. Propose two RTL "
         "alternatives and compare their wire counts and latency.",
         "Extend `wire_pipe` with a `ready` input and skid buffers so that "
         "it supports back-pressure; verify that no data is lost or "
         "duplicated under random stalls.",
         "A metal-only ECO must invert the polarity of an interrupt output. "
         "Which spare cells are needed, and what checks must run afterwards?",
         "Write the hand-off README for the `dot2_2c` block of Chapter 18, "
         "listing every deliverable in the table above that applies to it."],
        ordered=True)


# =============================================================================
#                                  PART IV
# =============================================================================
def part4():
    part("Implementation-Aware RTL",
         "What happens to your RTL after you commit it: synthesis into "
         "standard cells, static timing analysis and the SDC that drives "
         "it, low-power techniques and UPF power intent, design for test "
         "from scan chains to JTAG, and the power-performance-area "
         "trade-offs and hand-off package that carry a design to tapeout.")
    _ch17()
    _ch18()
    _ch19()
    _ch20()
    _ch21()
