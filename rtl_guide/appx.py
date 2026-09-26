"""Appendices A-D of "RTL Design for SoC & ASIC - The Complete Guide".

A  Verilog/SystemVerilog quick reference
B  Glossary
C  100 RTL interview questions with answers
D  Tools, standards and resources

All synthesizable snippets were compiled with `iverilog -g2012 -Wall`
(Icarus Verilog 12) and exercised by small self-checking testbenches.
"""

from rtl_guide.common import *  # noqa: F401,F403


# =============================================================================
# Appendix A - quick reference
# =============================================================================
def _appx_a():
    appendix("Verilog/SystemVerilog Quick Reference")
    p("A dense, look-it-up-fast summary of the language as used for design "
      "(Chapters 3-4) and testbenches (Chapter 22). Everything marked "
      "__synth__ is accepted by mainstream synthesis tools; the rest is "
      "simulation-only.")

    ah2("Data types")
    tbl(["Type", "States / width", "Signed?", "Use"],
        [["`logic`", "4-state, user width (default 1)", "no",
          "The default for all RTL signals; one driver (procedural or one "
          "continuous assign)"],
         ["`wire` / `tri`", "4-state net, resolved", "no",
          "Multiple drivers (tri-state buses), port connections; `wire` is "
          "a net kind, `logic` is a data type"],
         ["`reg`", "4-state variable", "no",
          "Legacy Verilog name for a variable - **not** necessarily a register"],
         ["`bit`", "2-state, user width", "no",
          "Testbench / modelling; X and Z become 0 - hides X bugs in RTL"],
         ["`byte` `shortint` `int` `longint`", "2-state, 8/16/32/64", "yes",
          "Loop indices, TB counters"],
         ["`integer`", "4-state, 32", "yes", "Legacy loop variable"],
         ["`time` / `realtime` / `real`", "64-bit / double", "-",
          "Simulation only (delays, measurements)"],
         ["`string`", "dynamic", "-", "TB only; `$sformatf`, `.len()`, "
          "`.substr()`"],
         ["`enum`", "base type (default `int`)", "base",
          "FSM states, opcodes; `.name()`, `.next()`, strong typing"],
         ["`struct packed`", "sum of fields, MSB = first field", "opt.",
          "Bus payloads; can be sliced as a vector"],
         ["`union packed`", "all members same width", "opt.",
          "Several views of one vector"],
         ["Packed array `logic [3:0][7:0] w`", "contiguous bits", "no",
          "32-bit vector viewed as 4 bytes; `w[0]` is the LS byte"],
         ["Unpacked array `logic [7:0] m [0:255]`", "array of elements", "-",
          "Memories, register files (Chapter 9)"],
         ["Dynamic `[]`, queue `[$]`, assoc `[key]`", "resizable", "-",
          "TB only (scoreboards, sparse memories)"]],
        widths=[26, 20, 9, 45], bold_first=True)
    tbl(["Literal", "Meaning"],
        [["`8'hA5`, `4'b10x1`, `12'o777`, `16'd255`",
          "Sized, unsigned, based; `x`/`z`/`?` allowed in b/o/h"],
         ["`8'sh80`", "Sized **signed** literal (-128)"],
         ["`255`", "Unsized decimal: 32-bit **signed**"],
         ["`'hFF`", "Unsized based: at least 32 bits, **unsigned**"],
         ["`'0 '1 'x 'z`", "Fill every bit of the context width (SV)"],
         ["`W'(expr)`, `signed'(x)`, `type_t'(x)`",
          "Size, sign and type casts (SV)"],
         ["`1_000_000`, `32'hDEAD_BEEF`", "Underscores are ignored"]],
        widths=[40, 60], bold_first=True)

    ah2("Operators and precedence")
    tbl(["Prec.", "Operators", "Notes"],
        [["1 (highest)", "`()` `[]` `::` `.`", "Grouping, select, scope, member"],
         ["2", "unary `+ - ! ~ & ~& | ~| ^ ~^` , `++ --`",
          "Unary `&`/`|`/`^` are reductions -> 1 bit"],
         ["3", "`**`", "Power; exponent is self-determined"],
         ["4", "`* / %`", "Division/modulo by non-constant is expensive in HW"],
         ["5", "binary `+ -`", ""],
         ["6", "`<< >> <<< >>>`", "`>>>` is arithmetic only if the operand "
          "is signed"],
         ["7", "`< <= > >=` `inside` `dist`", "Relational; result 1 bit"],
         ["8", "`== != === !== ==? !=?`",
          "`===` compares X/Z exactly (TB only); `==?` wildcard"],
         ["9", "binary `&`", ""],
         ["10", "binary `^ ~^ ^~`", ""],
         ["11", "binary `|`", ""],
         ["12", "`&&`", "Logical, short-circuit"],
         ["13", "`||`", ""],
         ["14", "`?:`", "Right-associative; X select merges both arms"],
         ["15", "`-> <->`", "Logical implication / equivalence (constraints)"],
         ["16 (lowest)", "`= += -= ... <=` and `{ }` `{{ }}`",
          "Assignments; concatenation / replication"]],
        widths=[12, 38, 50], bold_first=True)
    box("warn", "PITFALL - precedence traps",
        ["`a & b == c` parses as `a & (b == c)`; `x << 1 + y` shifts by `1 + y`; "
         "`!a == b` is `(!a) == b`. When in doubt, parenthesise - reviewers "
         "will thank you."])

    ah2("Expression sizing and signedness rules")
    tbl(["Rule", "Consequence"],
        [["Context-determined width = max of all operand widths **and** the "
          "LHS", "`sum = a + b` with 8-bit a, b and 9-bit sum keeps the carry; "
          "`{c, s} = a + b` also works"],
         ["Self-determined operands: concatenation members, shift amount, "
          "`**` exponent, reduction/relational/logical operands",
          "`{a + b}` is only max(La, Lb) bits wide - the carry is lost"],
         ["Comparison operands are sized to each other, result is 1 bit",
          "`if (cnt == 4'd10)` - fine; comparing 4-bit to 32-bit int extends "
          "the 4-bit one"],
         ["If **any** operand is unsigned the whole expression is unsigned",
          "`s8 + u8` is unsigned; `-1 > 8'd0` evaluates **true**"],
         ["Part-selects and concatenations are always unsigned",
          "`a[7:0]` of a signed `a` is unsigned; use `$signed()`"],
         ["Extension: signed operands sign-extend, unsigned zero-extend",
          "Happens **before** evaluation, based on the final expression type"],
         ["Truncation on assignment keeps the LSBs",
          "`-Wall` / lint flags width mismatches - fix every one"]],
        widths=[48, 52])

    ah2("Procedural blocks and assignments")
    tbl(["Construct", "Infers", "Rule of thumb"],
        [["`always_ff @(posedge clk or negedge rst_n)`", "Flip-flops",
          "Only `<=`; one clock; tool checks one-event-control"],
         ["`always_comb`", "Combinational logic",
          "Only `=`; default every output first; runs at time 0; no "
          "sensitivity list to forget"],
         ["`always_latch`", "Latches", "Intentional latches only (ICGs, "
          "latch-based designs)"],
         ["`always @(*)`", "Comb (Verilog-2001)", "Prefer `always_comb`"],
         ["`assign y = expr;`", "Comb wire", "Continuous; one per net bit"],
         ["`initial`", "Nothing (FPGA: init values)", "TB only in ASIC RTL"],
         ["`final`", "-", "End-of-sim reporting"],
         ["`a = b;` (blocking)", "-", "Comb blocks; TB sequential code"],
         ["`a <= b;` (non-blocking)", "-",
          "Every clocked assignment (Chapter 4 explains the scheduler)"],
         ["`function automatic`", "Comb logic", "No timing controls; "
          "`return`; `void` functions allowed"],
         ["`task`", "Usually TB only", "May consume time (`@`, `#`, `wait`)"]],
        widths=[38, 20, 42], bold_first=True)

    ah2("case variants")
    tbl(["Form", "Matching", "Synthesis meaning"],
        [["`case`", "Exact 4-state (`x` matches only `x`)",
          "Priority mux unless items are mutually exclusive"],
         ["`casez`", "`z`/`?` in items **or** expression are don't-care",
          "Priority encoders: `4'b1???`"],
         ["`casex`", "`x` and `z` both don't-care",
          "**Avoid** - an X on the selector matches anything and hides bugs"],
         ["`case (...) inside`", "Wildcards only in items, ranges `[0:7]`",
          "The safe modern `casez`"],
         ["`unique case`", "Error if 0 or >1 items match (at run time)",
          "Parallel mux, no priority; replaces `parallel_case full_case`"],
         ["`unique0 case`", "Error if >1 match; no-match allowed",
          "Parallel, outputs keep defaults when nothing matches"],
         ["`priority case`", "Error if no item matches",
          "Keeps priority but asserts completeness"]],
        widths=[20, 38, 42], bold_first=True)

    ah2("System tasks and functions")
    tbl(["Group", "Tasks / functions"],
        [["Printing", "`$display` (newline), `$write`, `$strobe` (end of time "
          "step, sees NBA results), `$monitor`, `$sformatf`; formats `%d %h %b "
          "%o %t %s %e %m %0d`"],
         ["Control", "`$finish`, `$stop`, `$fatal(1, msg)`, `$error`, "
          "`$warning`, `$info`"],
         ["Time", "`$time` (64-bit int), `$realtime`, `$stime`, "
          "`$timeformat`, `$printtimescale`"],
         ["Random", "`$urandom`, `$urandom_range(max, min)`, `$random(seed)`, "
          "`std::randomize()`, `obj.randomize()`"],
         ["Files", "`$fopen`, `$fclose`, `$fdisplay`, `$fwrite`, `$fscanf`, "
          "`$fgets`, `$feof`, `$readmemh`, `$readmemb`, `$writememh`"],
         ["Waveforms", "`$dumpfile`, `$dumpvars(0, top)`, `$dumpoff/on` (VCD)"],
         ["Plusargs", "`$test$plusargs(\"DBG\")`, "
          "`$value$plusargs(\"SEED=%d\", s)`"],
         ["Math / sizing (elaboration-time, synth)",
          "`$clog2`, `$bits`, `$size`, `$left`, `$right`, `$high`, `$low`, "
          "`$signed`, `$unsigned`"],
         ["Bit queries (synth in most tools)", "`$countones`, "
          "`$countbits(v, 1'b1)`, `$onehot`, `$onehot0`, `$isunknown`"],
         ["Assertions (SVA, Chapter 23)",
          "`$past`, `$rose`, `$fell`, `$stable`, `$changed`, `$sampled`, "
          "`$assertoff`/`$asserton`"],
         ["Types", "`$cast(dst, src)`, `$typename`"]],
        widths=[24, 76], bold_first=True)

    ah2("Modules, parameters and generate")
    code(["module fifo #(",
          "  parameter  int W     = 32,          // overridable",
          "  parameter  int DEPTH = 16,",
          "  localparam int AW    = $clog2(DEPTH) // derived, not overridable",
          ") (",
          "  input  logic         clk, rst_n,",
          "  input  logic [W-1:0] wdata,",
          "  output logic [W-1:0] rdata",
          ");",
          "// instantiation: named parameter and port binding; .clk is shorthand for .clk(clk)",
          "fifo #(.W(64), .DEPTH(8)) u_fifo (.clk, .rst_n, .wdata(din), .rdata(dout));"],
        caption="ANSI header with parameters, and an instance. `.*` connects "
        "every same-named port but hides mistakes; prefer explicit binding.")
    code(["module gen_ex #(parameter int N = 4, parameter bit REG_OUT = 1) (",
          "  input  logic         clk,",
          "  input  logic [N-1:0] a, b,",
          "  output logic [N-1:0] y",
          ");",
          "  logic [N-1:0] s;",
          "  for (genvar i = 0; i < N; i++) begin : g_bit     // generate-for",
          "    assign s[i] = a[i] ^ b[i];",
          "  end",
          "  if (REG_OUT) begin : g_reg                      // generate-if",
          "    always_ff @(posedge clk) y <= s;",
          "  end else begin : g_comb",
          "    assign y = s;",
          "  end",
          "endmodule"],
        caption="Generate loops and conditionals (the `generate` keyword is "
        "optional in SV). Always name generate blocks: hierarchical paths "
        "become `g_bit[2].` instead of `genblk1[2].`. Verified with Icarus.")

    ah2("Packages, typedef, enum, struct")
    code(["package bus_pkg;",
          "  localparam int AW = 32;",
          "  typedef logic [AW-1:0] addr_t;",
          "  typedef enum logic [1:0] {OKAY = 2'b00, EXOKAY = 2'b01,",
          "                            SLVERR = 2'b10, DECERR = 2'b11} resp_e;",
          "  typedef struct packed {",
          "    addr_t      addr;       // bits [36:5]",
          "    logic       write;      // bit  [4]",
          "    logic [3:0] strb;       // bits [3:0]",
          "  } req_t;",
          "  function automatic logic is_err(resp_e r);",
          "    return r[1];",
          "  endfunction",
          "endpackage",
          "",
          "module pkg_user",
          "  import bus_pkg::*;          // header import: types usable in the port list",
          "(",
          "  input  req_t  req,",
          "  input  resp_e resp,",
          "  output addr_t word_addr,",
          "  output logic  bad",
          ");",
          "  assign word_addr = {req.addr[AW-1:2], 2'b00};",
          "  assign bad       = is_err(resp);",
          "endmodule"],
        caption="A package shared by RTL and TB. Compile packages first; avoid "
        "`import *` in `$unit` (file) scope. Verified with Icarus.")

    ah2("Interfaces and modports")
    code(["interface vr_if #(parameter int W = 8) (input logic clk);",
          "  logic         valid, ready;",
          "  logic [W-1:0] data;",
          "  modport src (output valid, data, input  ready);",
          "  modport snk (input  valid, data, output ready);",
          "endinterface",
          "",
          "module sink (vr_if.snk s, output logic [7:0] last);",
          "  assign s.ready = 1'b1;",
          "  always_ff @(posedge s.clk)",
          "    if (s.valid && s.ready) last <= s.data;",
          "endmodule",
          "",
          "// in the parent:  vr_if #(8) bus (.clk);   sink u_sink (.s(bus), .last);"],
        caption="An interface bundles a protocol's wires; modports give each "
        "side its direction. IEEE 1800-legal and supported by all commercial "
        "tools and Verilator; Icarus 12 does not accept interface ports, so "
        "this listing was not simulated.")

    ah2("Synthesizable subset at a glance")
    tbl(["Synthesizable", "Not synthesizable (TB / model only)"],
        [["`always_ff/_comb/_latch`, `assign`, module instances",
          "`initial` (except FPGA init / ROM `$readmemh` in some flows)"],
         ["`if`, `case` family, `for` with constant bounds, `generate`",
          "`#` delays (ignored by synthesis - a sim/synth mismatch source)"],
         ["`function automatic`, tasks without timing",
          "`wait`, `@` inside tasks, `fork/join`, `forever` without a clock"],
         ["Packed/unpacked arrays, structs, unions, enums, packages",
          "Classes, dynamic arrays, queues, associative arrays, `string`"],
         ["Arithmetic `+ - *`, shifts, compares; `/` and `%` by constants "
          "or powers of 2", "`real`, `$random`, file I/O, `$display` (ignored)"],
         ["Parameters, `localparam`, `$clog2`, `$bits`",
          "`===`/`!==` (X is not a hardware value), `force/release`"],
         ["Interfaces with modports (most tools)",
          "SVA concurrent assertions (ignored by synthesis, used by formal)"]],
        widths=[50, 50])

    ah2("Common idioms (all verified with Icarus)")
    h3("Flop with asynchronous active-low reset and enable")
    code(["module dff_en #(parameter int W = 8) (",
          "  input  logic         clk, rst_n, en,",
          "  input  logic [W-1:0] d,",
          "  output logic [W-1:0] q",
          ");",
          "  always_ff @(posedge clk or negedge rst_n)",
          "    if (!rst_n)  q <= '0;",
          "    else if (en) q <= d;          // enable -> mux or clock gate",
          "endmodule"])
    h3("Combinational block with defaults (no latches)")
    code(["always_comb begin",
          "  onehot = '0;                    // defaults first: every path assigns",
          "  err    = 1'b0;",
          "  if (valid) begin",
          "    unique case (sel)",
          "      2'd0: onehot = 4'b0001;",
          "      2'd1: onehot = 4'b0010;",
          "      2'd2: onehot = 4'b0100;",
          "      2'd3: onehot = 4'b1000;",
          "      default: err = 1'b1;        // reached only on X/Z in simulation",
          "    endcase",
          "  end",
          "end"])
    h3("FSM template (two processes, enumerated state)")
    code(["typedef enum logic [1:0] {IDLE, RUN, FLUSH} state_e;",
          "state_e state_q, state_d;",
          "",
          "always_ff @(posedge clk or negedge rst_n)",
          "  if (!rst_n) state_q <= IDLE;",
          "  else        state_q <= state_d;",
          "",
          "always_comb begin",
          "  state_d = state_q;              // default: stay",
          "  busy    = 1'b0;                 // default outputs",
          "  case (state_q)",
          "    IDLE:  if (start) state_d = RUN;",
          "    RUN:   begin busy = 1'b1; if (done) state_d = FLUSH; end",
          "    FLUSH: state_d = IDLE;",
          "    default: state_d = IDLE;",
          "  endcase",
          "end"])
    h3("Two-flop synchronizer (single-bit level signal only)")
    code(["(* ASYNC_REG = \"TRUE\" *) logic [1:0] ff;   // keep flops adjacent (FPGA)",
          "always_ff @(posedge clk or negedge rst_n)",
          "  if (!rst_n) ff <= '0;",
          "  else        ff <= {ff[0], d_async};",
          "assign q_sync = ff[1];"])
    h3("Modulo-N counter with terminal-count pulse")
    code(["module cnt_mod #(parameter int N = 10) (",
          "  input  logic                 clk, rst_n, en,",
          "  output logic [$clog2(N)-1:0] cnt,",
          "  output logic                 tc",
          ");",
          "  assign tc = en && (cnt == $clog2(N)'(N-1));",
          "  always_ff @(posedge clk or negedge rst_n)",
          "    if (!rst_n)  cnt <= '0;",
          "    else if (tc) cnt <= '0;",
          "    else if (en) cnt <= cnt + 1'b1;",
          "endmodule"])
    h3("Other one-liners")
    tbl(["Need", "Idiom"],
        [["Sign-extend 8 -> 32", "`{{24{a[7]}}, a}` or `32'(signed'(a))`"],
         ["Rising-edge pulse", "`rise = a & ~a_q;` (`a_q` is `a` delayed "
          "one clock)"],
         ["Isolate lowest set bit / fixed-priority grant",
          "`gnt = req & (~req + 1'b1);`"],
         ["Power of two?", "`(x != 0) && ((x & (x - 1)) == 0)`"],
         ["Binary -> Gray", "`g = b ^ (b >> 1);`"],
         ["Round up to multiple of 4", "`(x + 3) & ~32'd3`"],
         ["Bit reverse", "`for (int i=0;i<W;i++) r[i] = a[W-1-i];` or "
          "`{<<{a}}` (streaming)"],
         ["Parity", "`^data` (even parity bit)"],
         ["Saturating add (unsigned)",
          "`{c, s} = a + b; y = c ? '1 : s;`"],
         ["Register slice without reset (datapath)",
          "`always_ff @(posedge clk) if (v_in) d_q <= d_in;`"]],
        widths=[34, 66], bold_first=True)


# =============================================================================
# Appendix B - glossary
# =============================================================================
_GLOSS = [
    ("ACE / CHI", "AMBA coherency protocols: ACE extends AXI with snoop "
     "channels; CHI is a packetised, layered protocol for scalable coherent "
     "meshes."),
    ("Activity factor (alpha)", "Probability that a node toggles per clock; "
     "dynamic power = alpha C V^{2} f."),
    ("AHB", "AMBA Advanced High-performance Bus: pipelined address/data "
     "phases, single outstanding transfer, bursts, `HREADY` wait states."),
    ("Always-on domain", "A power domain that stays powered while others "
     "are gated; hosts the power controller, wake-up logic and retention "
     "control."),
    ("Antenna effect", "Charge collected by long metal during fabrication "
     "that can damage thin gate oxide; fixed by diodes or layer jumping."),
    ("APB", "AMBA Advanced Peripheral Bus: two-phase (setup/access), "
     "unpipelined, for low-bandwidth register access."),
    ("Arbiter", "Logic that grants one of several requesters a shared "
     "resource: fixed priority, round-robin, weighted, or QoS-based."),
    ("ASIC", "Application-Specific Integrated Circuit: a chip fabricated "
     "for one design, as opposed to a programmable FPGA."),
    ("Assertion", "An executable property of the design (SVA); checked in "
     "simulation and proven or refuted by formal tools."),
    ("Async FIFO", "FIFO with read and write in different clock domains; "
     "Gray-coded pointers are synchronized across (Chapter 11)."),
    ("ATPG", "Automatic Test Pattern Generation: computes scan patterns "
     "that detect modelled manufacturing faults."),
    ("At-speed test", "Testing with launch/capture at functional clock "
     "frequency to detect delay (transition, path-delay) faults."),
    ("AXI4", "AMBA Advanced eXtensible Interface: five independent "
     "valid/ready channels (AW, W, B, AR, R), bursts, IDs, outstanding and "
     "out-of-order transactions."),
    ("AXI4-Lite", "Single-beat, 32/64-bit subset of AXI4 for registers; no "
     "bursts or IDs."),
    ("AXI4-Stream", "Unidirectional data streaming with `TVALID/TREADY`, "
     "`TDATA`, `TLAST`, `TKEEP`, `TUSER`; no addresses."),
    ("Back-annotation", "Loading extracted delays (SDF) or parasitics "
     "(SPEF) into simulation or STA."),
    ("Backpressure", "A downstream stage stalling an upstream one, e.g. by "
     "deasserting `ready`."),
    ("BIST", "Built-In Self-Test: on-chip pattern generation and response "
     "compaction - MBIST for memories, LBIST for logic."),
    ("Blocking assignment", "`=`: updates the variable immediately in the "
     "active region; use in combinational blocks."),
    ("Boundary scan", "IEEE 1149.1 chain of cells at the chip pins, "
     "controlled through the JTAG TAP, for board interconnect test."),
    ("Burst", "A multi-beat bus transaction issued with a single address "
     "(AXI: INCR, WRAP, FIXED; max 4 KB boundary)."),
    ("CDC", "Clock-Domain Crossing: any signal launched in one clock domain "
     "and captured in an asynchronous one; needs a synchronization scheme."),
    ("Clock gating (ICG)", "Stopping the clock to idle registers with an "
     "Integrated Clock Gating cell (latch + AND) - the main dynamic-power "
     "lever."),
    ("Clock jitter", "Cycle-to-cycle variation of the clock edge; modelled "
     "as clock uncertainty."),
    ("Clock skew", "Difference in clock arrival time at two flops; helps "
     "setup or hold depending on its sign."),
    ("Clock tree synthesis (CTS)", "Building the buffered clock "
     "distribution network to meet skew, latency and transition targets."),
    ("Clock uncertainty", "SDC margin (`set_clock_uncertainty`) covering "
     "jitter and pre-CTS skew estimates."),
    ("Combinational loop", "A feedback path with no storage element; "
     "oscillates or latches, breaks STA; lint error."),
    ("Congestion", "Routing demand exceeding available tracks in a region; "
     "caused by dense, highly connected logic (big muxes, crossbars)."),
    ("Constrained random", "Stimulus generated randomly within declared "
     "constraints, steered by coverage feedback."),
    ("Corner (PVT)", "A process/voltage/temperature combination at which "
     "timing and power are analysed (e.g. SS 0.72 V 125C)."),
    ("Covergroup", "SystemVerilog construct sampling values and crosses to "
     "measure functional coverage."),
    ("Coverage", "Metrics of verification completeness: code (line, branch, "
     "toggle, FSM, expression) and functional (covergroups, cover "
     "properties)."),
    ("Credit-based flow control", "Sender holds credits equal to receiver "
     "buffer space; sends only with credit - tolerates long wire latency."),
    ("Critical path", "The timing path with the worst slack; sets the "
     "maximum clock frequency."),
    ("Crosstalk (SI)", "Coupling between adjacent wires changing delay or "
     "causing glitches; analysed in signal-integrity STA."),
    ("CSR", "Control and Status Register: software-visible register mapped "
     "into the address space (Chapter 15)."),
    ("Decap", "Decoupling capacitor cells that stabilize the local supply "
     "against dynamic IR drop."),
    ("DEF / LEF", "Design Exchange Format (placed/routed design) and Library "
     "Exchange Format (cell abstracts and technology rules)."),
    ("Delta cycle", "A zero-time simulation iteration; many deltas can "
     "occur in one time step while events settle."),
    ("DFT", "Design for Test: scan, compression, BIST, JTAG and test "
     "access so manufactured parts can be screened."),
    ("DMA", "Direct Memory Access engine: moves data between memory and "
     "peripherals without CPU involvement."),
    ("DRC", "Design Rule Check: verifies layout geometry against foundry "
     "rules. Also: electrical design rules (max cap/transition/fanout)."),
    ("DVFS", "Dynamic Voltage and Frequency Scaling: lowering V and f under "
     "light load; power scales roughly with V^{2} f."),
    ("ECC", "Error-Correcting Code (e.g. SECDED Hamming) protecting "
     "memories and buses against bit flips."),
    ("ECO", "Engineering Change Order: a late, minimal netlist or layout "
     "patch, often using spare cells."),
    ("Elaboration", "Building the design hierarchy: resolving parameters, "
     "generate blocks and instances after parsing."),
    ("Electromigration (EM)", "Metal atoms displaced by high current "
     "density over time; limits wire widths and via counts."),
    ("Emulation", "Running the design mapped onto a dedicated hardware "
     "platform (Palladium, ZeBu, Veloce) at MHz speeds."),
    ("Equivalence checking (LEC)", "Formal proof that two representations "
     "(RTL vs netlist, netlist vs netlist) implement the same function."),
    ("False path", "A structurally present path that never propagates in "
     "operation; excluded from STA with `set_false_path`."),
    ("Fanout", "Number of inputs driven by one output; high fanout nets are "
     "buffered into trees."),
    ("Fault coverage", "Detected faults divided by total modelled faults; "
     "production targets are typically > 99% stuck-at."),
    ("FIFO", "First-In First-Out buffer decoupling producer and consumer "
     "rates (Chapter 9)."),
    ("FinFET", "Multi-gate 3D transistor used from ~22/16 nm; followed by "
     "gate-all-around (nanosheet) devices at 3/2 nm."),
    ("Flip-flop", "Edge-triggered storage element: samples D at the clock "
     "edge; characterised by setup, hold and clock-to-Q."),
    ("Floorplan", "Placement of macros, IO, power grid and block outlines "
     "before standard-cell placement."),
    ("Formal verification", "Mathematical proof of properties over all "
     "input sequences (model checking), without test vectors."),
    ("Foundry", "The company that fabricates wafers (TSMC, Samsung, Intel "
     "Foundry, GlobalFoundries, SkyWater, IHP ...)."),
    ("FPGA prototyping", "Mapping the ASIC RTL onto FPGAs to run software "
     "at tens of MHz before silicon."),
    ("FSM", "Finite State Machine: state register plus next-state and "
     "output logic (Moore or Mealy)."),
    ("Functional coverage", "User-defined coverage of features and "
     "scenarios from the verification plan."),
    ("Gate-level simulation (GLS)", "Simulating the synthesized or "
     "post-layout netlist, optionally with SDF timing."),
    ("GDSII / OASIS", "Binary layout formats delivered to the foundry at "
     "tapeout."),
    ("Glitch", "A spurious short pulse from unequal path delays; harmless "
     "on synchronous data, fatal on clocks, resets and async inputs."),
    ("Glitch-free clock mux", "Clock switch that disables the old clock on "
     "its own falling edge before enabling the new one."),
    ("Gray code", "Encoding where consecutive values differ in one bit; "
     "makes multi-bit counters safe to synchronize."),
    ("Handshake synchronizer", "Req/ack protocol across domains, each "
     "direction through a 2-flop synchronizer; for multi-bit data."),
    ("Hold time", "Minimum time data must be stable **after** the clock "
     "edge; hold violations are frequency-independent and kill silicon."),
    ("HLS", "High-Level Synthesis: generating RTL from C/C++/SystemC."),
    ("IJTAG", "IEEE 1687: network of instruments accessed via "
     "reconfigurable scan paths (SIBs) described in ICL/PDL."),
    ("Interconnect", "The fabric (crossbar, bus matrix, NoC) that routes "
     "transactions between managers and subordinates."),
    ("Interrupt controller", "Collects, prioritizes and routes interrupts "
     "to cores (RISC-V PLIC/CLIC, Arm GIC/NVIC)."),
    ("IP-XACT", "IEEE 1685 XML schema describing IP interfaces, registers "
     "and memory maps for tool automation."),
    ("IR drop", "Voltage loss across the power grid (static or dynamic) "
     "that slows cells."),
    ("Isolation cell", "Clamps outputs of a powered-down domain to a "
     "known value so live domains do not see X."),
    ("JTAG / TAP", "IEEE 1149.1 Test Access Port: TCK, TMS, TDI, TDO, "
     "optional TRST; a 16-state controller selects IR/DR scans."),
    ("Latch", "Level-sensitive storage; transparent while enabled. "
     "Unintended latches come from incomplete combinational assignment."),
    ("Latency", "Cycles (or time) from input to corresponding output."),
    ("Leakage power", "Static power from subthreshold and gate leakage; "
     "grows with temperature and lower Vt."),
    ("Level shifter", "Cell translating a signal between voltage domains."),
    ("Liberty (.lib)", "Standard-cell library timing/power/area models "
     "(NLDM, CCS, ECSM) used by synthesis and STA."),
    ("Lint", "Static rule checking of RTL for coding, synthesis and "
     "simulation-mismatch issues."),
    ("Lockup latch", "Latch inserted between scan flops of different clock "
     "domains/skews to avoid hold failures during shift."),
    ("LVS", "Layout Versus Schematic: checks the layout's extracted netlist "
     "matches the source netlist."),
    ("Macro", "A large pre-built block placed as a unit: SRAM, PLL, "
     "SerDes, analog IP."),
    ("Mask / reticle", "The photomask set used per layer; full-mask costs "
     "are millions of dollars at advanced nodes."),
    ("Memory compiler", "Foundry/IP tool generating SRAM/ROM/register-file "
     "macros of a requested size with views (.lib, LEF, GDS, Verilog)."),
    ("Memory map", "Assignment of address ranges to subordinates and "
     "registers (Chapter 14)."),
    ("Metastability", "A flop left between 0 and 1 after a setup/hold "
     "violation; resolves in a random time. Synchronizers make failure "
     "improbable, not impossible."),
    ("MPW / shuttle", "Multi-Project Wafer: many designs share one mask set "
     "to cut prototype cost."),
    ("MTBF", "Mean Time Between Failures of a synchronizer: "
     "exp(t_{r} / tau) / (T_{0} f_{clk} f_{data})."),
    ("Multicycle path", "A path allowed more than one clock period, "
     "declared with `set_multicycle_path` (adjust hold too)."),
    ("Multi-Vt", "Libraries with low/standard/high threshold cells traded "
     "between speed and leakage."),
    ("Netlist", "Structural description of cells and nets produced by "
     "synthesis."),
    ("NoC", "Network-on-Chip: packet-switched interconnect with routers "
     "and links, scaling beyond crossbars."),
    ("Non-blocking assignment (NBA)", "`<=`: RHS sampled now, LHS updated "
     "in the NBA region; models flops without races."),
    ("OCC", "On-Chip Clock Controller: generates at-speed launch/capture "
     "pulses from a PLL during scan test."),
    ("OCV / AOCV / POCV", "On-Chip Variation models: flat derates, "
     "depth/distance-based, or statistical (per-cell sigma)."),
    ("One-hot", "Encoding with exactly one bit set; fast decode, more "
     "flops; popular for FSMs and grants."),
    ("Operand isolation", "Gating datapath inputs when the result is unused "
     "to cut toggle power."),
    ("Outstanding transactions", "Requests issued but not yet completed; "
     "AXI allows many, bounded by ID and buffer resources."),
    ("Parasitic extraction (SPEF)", "Computing wire R and C from layout "
     "for sign-off timing and power."),
    ("PDK", "Process Design Kit: device models, rules, cell libraries and "
     "tech files for a foundry process."),
    ("Pipelining", "Inserting registers to split long logic, trading "
     "latency for clock frequency and throughput."),
    ("Place and route (P&R)", "Placement, CTS, routing and optimization "
     "that turn a netlist into layout."),
    ("Power domain", "A group of logic sharing a supply that can be "
     "switched or scaled independently (UPF)."),
    ("Power gating", "Cutting a domain's supply with header/footer switch "
     "cells to eliminate leakage."),
    ("PPA", "Power, Performance, Area - the three competing metrics of an "
     "implementation."),
    ("Priority encoder", "Outputs the index of the highest (or lowest) "
     "priority set bit."),
    ("Pulse synchronizer", "Converts a source pulse to a toggle, "
     "synchronizes the toggle, and edge-detects it in the destination."),
    ("QoS", "Quality of Service: priority/bandwidth/latency controls in "
     "interconnects (AXI `AxQOS`)."),
    ("RDC", "Reset-Domain Crossing: paths from flops reset by one reset to "
     "flops on another, which can go metastable on asynchronous "
     "assertion (Chapter 12)."),
    ("Reconvergence", "Separately synchronized signals recombined in the "
     "destination; they may arrive in different cycles."),
    ("Recovery / removal", "Setup/hold-like checks for an asynchronous "
     "reset's **deassertion** relative to the clock."),
    ("Register file", "Small multi-ported storage array, often built from "
     "flops or custom bitcells."),
    ("Reset synchronizer", "Asserts reset asynchronously, deasserts it "
     "synchronously through two flops."),
    ("Retention register", "Flop with a shadow latch on always-on supply "
     "that keeps state while its domain is gated."),
    ("Retiming", "Moving registers across combinational logic to balance "
     "stages without changing behaviour at the boundaries."),
    ("RTL", "Register-Transfer Level: describing hardware as registers and "
     "the combinational transfers between them."),
    ("Scan chain", "Flops converted to scan flops (mux-D) and stitched "
     "into shift registers for test."),
    ("Scan compression", "Decompressor/compactor around many short "
     "internal chains to cut test time and pins (e.g. EDT, DFTMAX)."),
    ("Scoreboard", "Testbench component comparing DUT outputs with a "
     "reference model's predictions."),
    ("SDC", "Synopsys Design Constraints: Tcl-based clocks, IO delays and "
     "exceptions used by synthesis, P&R and STA."),
    ("SDF", "Standard Delay Format (IEEE 1497): cell and interconnect "
     "delays for timing simulation."),
    ("Setup time", "Minimum time data must be stable **before** the clock "
     "edge; violations are fixed by slowing the clock or the logic."),
    ("Sign-off", "Final verification against all criteria (timing, power, "
     "DRC, LVS, EM/IR) before tapeout."),
    ("Skid buffer", "Two-entry buffer that registers `ready` in a "
     "valid/ready pipeline without losing throughput (Chapter 10)."),
    ("Slack", "Required time minus arrival time; negative slack is a "
     "timing violation."),
    ("SoC", "System-on-Chip: processors, memories, interconnect and "
     "peripherals integrated on one die."),
    ("Spare cells", "Unused gates scattered in the layout for metal-only "
     "ECOs."),
    ("SRAM", "Static RAM macro; single- or dual-port, synchronous read "
     "with one-cycle latency."),
    ("STA", "Static Timing Analysis: exhaustive path-based timing check "
     "without vectors (Chapter 18)."),
    ("Standard cell", "Pre-characterized logic gate or flop of fixed "
     "height placed in rows."),
    ("Stuck-at fault", "Fault model where a node is permanently 0 or 1."),
    ("Synchronizer", "Chain of flops in the destination domain giving a "
     "metastable value time to resolve."),
    ("Synthesis", "Translating RTL into an optimized gate-level netlist "
     "under constraints (Chapter 17)."),
    ("SystemRDL", "Accellera register description language from which "
     "RTL, headers, docs and UVM register models are generated."),
    ("Tapeout", "Releasing the final layout database to the foundry for "
     "mask making."),
    ("Testbench", "The non-synthesizable environment that drives, checks "
     "and measures the DUT."),
    ("Throughput", "Results per cycle (or per second) in steady state."),
    ("Timing arc", "A modelled delay/check between two pins of a cell in "
     "Liberty."),
    ("Toggle coverage", "Whether each bit has transitioned 0->1 and 1->0 "
     "in simulation."),
    ("Transition fault", "Delay fault model: a node is slow to rise or "
     "fall; needs at-speed launch/capture."),
    ("Unique / priority", "SystemVerilog `case`/`if` qualifiers that add "
     "run-time checks and guide synthesis."),
    ("UPF", "Unified Power Format (IEEE 1801): power domains, supplies, "
     "isolation, retention, level shifters (Chapter 19)."),
    ("Utilization", "Cell area divided by core area; typical targets "
     "60-80% to leave room for routing and buffering."),
    ("UVM", "Universal Verification Methodology (IEEE 1800.2): class "
     "library for reusable SystemVerilog testbenches (Chapter 24)."),
    ("Valid/ready", "Two-signal handshake; a transfer happens on each clock "
     "where both are high."),
    ("Verilator", "Open-source compiler of SystemVerilog to C++; very fast, "
     "cycle-based, 2-state."),
    ("Wafer", "Silicon disc (300 mm for advanced nodes) carrying hundreds "
     "of dies."),
    ("Well tap / endcap", "Physical-only cells tying wells and ending rows "
     "to prevent latch-up and edge effects."),
    ("WNS / TNS", "Worst and Total Negative Slack - the headline timing "
     "metrics."),
    ("Write strobe", "Byte-enable mask on a write (`WSTRB`, `PSTRB`)."),
    ("X-propagation", "How unknowns flow through logic in simulation; "
     "`if` is X-optimistic, which can hide reset bugs."),
    ("Yield", "Fraction of dies that are functional; depends on defect "
     "density and die area."),
]


def _appx_b():
    appendix("Glossary")
    p("Terms used across the book, in alphabetical order. Numbers in "
      "parentheses point to the chapter where the concept is treated in "
      "depth.")
    tbl(["Term", "Definition"],
        [[a, b] for a, b in sorted(_GLOSS, key=lambda t: t[0].lower())],
        widths=[24, 76], bold_first=True)


# =============================================================================
# Appendix C - interview questions
# =============================================================================
_Q = {"n": 0}


def qa(q, a, snippet=None):
    """One numbered interview question with its answer."""
    _Q["n"] += 1
    # bold the question text but keep `code` spans intact (mk does not nest)
    segs = ("Q%d. %s" % (_Q["n"], q)).split("`")
    p("".join(("**%s**" % s if s.strip() else s) if i % 2 == 0 else "`%s`" % s
              for i, s in enumerate(segs)))
    if isinstance(a, str):
        a = [a]
    for para in a:
        p(para)
    if snippet:
        code(snippet)


def _appx_c():
    appendix("100 RTL Interview Questions with Answers")
    p("Grouped by topic, roughly from screening questions to on-site design "
      "problems. Answer out loud first, then check. Every code answer was "
      "compiled and exercised with Icarus Verilog.")

    # --------------------------------------------------------- digital logic
    ah2("Digital logic fundamentals")
    qa("What is the difference between a latch and a flip-flop?",
       "A latch is level-sensitive: transparent while its enable is active, "
       "so data can race through. A flip-flop is edge-triggered: it samples "
       "only at the clock edge. Flops make timing analysis simple (one "
       "launch, one capture); latches allow time borrowing but complicate "
       "STA and testing.")
    qa("Define setup time, hold time and clock-to-Q.",
       "Setup: data must be stable a minimum time before the capturing edge. "
       "Hold: stable a minimum time after it. Clock-to-Q: delay from the "
       "edge until Q changes. Setup: T_{clk} >= t_{cq} + t_{logic} + "
       "t_{setup} - skew. Hold: t_{cq} + t_{logic,min} >= t_{hold} + skew.")
    qa("Why can a hold violation not be fixed by slowing the clock?",
       "The hold check compares launch and capture on the **same** edge; the "
       "clock period does not appear in the equation. It must be fixed by "
       "adding delay on the data path (buffers) or reducing skew.")
    qa("What is metastability and can it be eliminated?",
       "When setup/hold is violated the flop may hover at an intermediate "
       "level and resolve after an unbounded, exponentially distributed "
       "time. It cannot be eliminated, only made improbable: MTBF = "
       "exp(t_{r} / tau) / (T_{0} f_{clk} f_{data}), so each extra synchronizer "
       "stage multiplies MTBF by roughly exp(T / tau).")
    qa("Build a 2:1 mux from NAND gates only. How many?",
       "Four: n1 = NAND(s, s) gives s'; n2 = NAND(a, s'); n3 = NAND(b, s); "
       "y = NAND(n2, n3) = a s' + b s.")
    qa("Implement an XOR with 2:1 muxes; implement an inverter with a mux.",
       "XOR: y = b ? ~a : a (a mux with inputs a and ~a; ~a itself is a mux "
       "with inputs 1 and 0 selected by a). Inverter: mux(sel = a, in0 = 1, "
       "in1 = 0). Muxes are universal.")
    qa("What is a glitch (hazard) and when does it matter?",
       "A transient wrong output value caused by unequal path delays "
       "(static-1 hazard in a + a' style logic). In synchronous logic it "
       "settles before the edge and is harmless; on clocks, asynchronous "
       "resets, clock-gate enables or CDC paths it causes real failures.")
    qa("Compare binary, Gray and one-hot encoding.",
       "Binary: log2(N) flops, multi-bit transitions. Gray: log2(N) flops, "
       "one bit changes per step - safe to synchronize and low-power for "
       "counters. One-hot: N flops, trivial decode and fast next-state "
       "logic - favoured for FSMs in FPGAs and fast ASIC control.")
    qa("What limits the maximum frequency of a design?",
       "The worst register-to-register path: t_{cq} + t_{logic} + t_{route} + "
       "t_{setup} + uncertainty - useful skew. Also IO paths, memory access "
       "times and clock-tree/PLL limits.")
    qa("How do you convert two's complement to magnitude, and what is "
       "special about the most negative number?",
       "Invert and add one. For N bits the range is -2^{N-1} to 2^{N-1}-1, so "
       "negating -2^{N-1} overflows back to itself; absolute-value logic "
       "needs one extra bit or saturation.")

    # --------------------------------------------------- Verilog semantics
    ah2("Verilog and SystemVerilog semantics")
    qa("Blocking versus non-blocking: which, where, and why?",
       ["`=` executes immediately; `<=` samples the RHS now and updates in "
        "the NBA region after all active events. Use `<=` in clocked blocks "
        "so every flop sees pre-edge values (no race between blocks); use "
        "`=` in combinational blocks so later statements see earlier "
        "results. Never mix both on the same variable (Chapter 4)."])
    qa("What does this swap produce: `always @(posedge clk) begin a = b; "
       "b = a; end`?",
       "Both end up with the old `b`: after `a = b`, `a` already holds the "
       "new value. Written with `<=` it is a true swap. It also races with "
       "any other block reading `a` at the same edge.")
    qa("How does an unintended latch get inferred, and how do you prevent it?",
       "A combinational block that does not assign an output on every path "
       "(missing `else`, incomplete `case`) must remember the old value - a "
       "latch. Prevent with default assignments at the top of `always_comb`, "
       "complete `case` with `default`, and lint.")
    qa("What is the difference between `wire`, `reg` and `logic`?",
       "`wire` is a net (resolved, can have multiple drivers, continuous "
       "assignment). `reg` is a Verilog variable assigned procedurally - it "
       "does not imply a register. `logic` is SV's 4-state data type usable "
       "as either, but enforcing a single driver.")
    qa("`always_comb` versus `always @(*)`?",
       "`always_comb` runs once at time 0, is sensitive to variables read in "
       "called functions, forbids other processes writing its outputs, and "
       "lets tools warn about latches. `@(*)` misses all of these.")
    qa("What is the difference between `==` and `===`?",
       "`==` returns X if either operand has X/Z; `===` compares X and Z "
       "literally and always returns 0/1. `===` is for testbenches; it is "
       "not synthesizable in any meaningful way.")
    qa("How are `casez`, `casex` and `case inside` different, and which is "
       "safe?",
       "`casez` treats z/? as don't care in items and the selector; `casex` "
       "also treats x as don't care - an X selector then matches the first "
       "item and masks bugs. `case inside` applies wildcards only to the "
       "items and is the recommended form.")
    qa("What do `unique` and `priority` do?",
       "`unique case` asserts exactly one item matches (warning otherwise) "
       "and lets synthesis build a parallel mux; `unique0` allows none; "
       "`priority` asserts at least one matches but keeps order. They "
       "replace the dangerous `full_case`/`parallel_case` pragmas, which "
       "changed synthesis without changing simulation.")
    qa("What is a simulation/synthesis mismatch? Give three causes.",
       "RTL simulation behaving differently from the synthesized netlist: "
       "incomplete sensitivity lists, `#` delays (ignored by synthesis), "
       "`full_case`/`parallel_case` pragmas, X-optimism of `if`/`case`, "
       "`initial` blocks, and reading a variable before it is assigned in a "
       "combinational block.")
    qa("What width is `a + b` in `{a + b}` if `a` and `b` are 8 bits?",
       "8 bits: operands of a concatenation are self-determined, so the "
       "carry is dropped. Assigning `sum9 = a + b` keeps it because the "
       "9-bit LHS participates in context sizing.")
    qa("What does `-1 > 8'd0` evaluate to, and why?",
       "Mixing signed and unsigned makes the whole expression unsigned: the "
       "32-bit `-1` becomes 32'hFFFF_FFFF, so the compare is true. Keep "
       "both operands signed (`$signed`, `8'sd0`) when comparing signed "
       "values.")
    qa("What is the difference between a task and a function?",
       "Functions execute in zero time, return a value (or `void`) and may "
       "not contain timing controls; they synthesize to combinational "
       "logic. Tasks may consume time (`@`, `#`, `wait`) and return through "
       "output arguments; used mainly in testbenches.")
    qa("What is a delta cycle and why can a zero-delay clock divider cause "
       "a race?",
       "A delta is a zero-time iteration of the scheduler. A clock generated "
       "by a flop (`clk2 <= ~clk2`) changes one delta later than `clk`; "
       "data launched on `clk` with `=` or through continuous logic can be "
       "seen by `clk2` flops in the same time step, so results depend on "
       "event order.")
    qa("Is `for` synthesizable?",
       "Yes, when the bounds are constant at elaboration: it is unrolled "
       "into parallel hardware. It describes replicated logic, not a loop "
       "in time - a 32-iteration loop is 32 copies of the body.")

    # ---------------------------------------------------------------- FSMs
    ah2("Finite state machines")
    qa("Moore versus Mealy?",
       "Moore outputs depend only on the state (glitch-free if registered, "
       "one cycle later); Mealy outputs depend on state and inputs (react "
       "in the same cycle, fewer states, but create combinational input-to-"
       "output paths).")
    qa("Why separate state register and next-state logic into two processes?",
       "It keeps sequential and combinational code distinct, avoids "
       "accidental flops on outputs, and maps directly to the textbook "
       "structure. Registered outputs can then be added deliberately.")
    qa("How do you make an FSM safe against illegal states?",
       "Use a `default` that returns to a known state, enumerate all "
       "encodings, and if required by safety (radiation, ISO 26262) ask "
       "synthesis for a safe FSM (`syn_encoding safe` or equivalent), since "
       "optimizers otherwise remove unreachable-state recovery logic.")
    qa("Draw/describe an FSM that detects the overlapping sequence 1011.",
       "States S0 (nothing), S1 (1), S2 (10), S3 (101). On a 1 in S3 assert "
       "`hit` and go to S1 (the trailing 1 starts a new match); on a 0 in "
       "S3 go to S2 (the trailing 10). An equivalent shift-register form "
       "compares the last four bits:",
       ["module seq1011 (input logic clk, rst_n, din, output logic hit);",
        "  logic [2:0] h;                  // last three bits",
        "  always_ff @(posedge clk or negedge rst_n)",
        "    if (!rst_n) h <= '0;",
        "    else        h <= {h[1:0], din};",
        "  assign hit = ({h, din} == 4'b1011);   // Mealy output",
        "endmodule"])
    qa("When would you register FSM outputs?",
       "When they drive another block, IO pins or a clock gate: registering "
       "removes glitches and decouples timing. The cost is one cycle of "
       "latency, often absorbed by computing outputs from `state_d`.")
    qa("What is a one-hot FSM's `unique case (1'b1)` idiom?",
       "`case (1'b1) state[IDLE]: ... state[RUN]: ... endcase` with "
       "`unique` tells synthesis only one bit is set, so each branch "
       "decodes a single flop instead of a full compare.")
    qa("How would you verify an FSM?",
       "FSM state and transition coverage, assertions that states are legal "
       "(`$onehot(state)` for one-hot) and that key transitions happen "
       "(`req |-> ##[1:4] gnt`), plus formal reachability for deadlocks.")

    # ------------------------------------------------ datapath and FIFOs
    ah2("Datapath, pipelining and FIFOs")
    qa("Carry-ripple versus carry-lookahead versus prefix adders?",
       "Ripple: O(N) delay, minimal area. Lookahead: groups compute "
       "generate/propagate to skip carries. Parallel prefix (Kogge-Stone, "
       "Brent-Kung, Sklansky): O(log N) delay with different area/fanout "
       "trade-offs. Synthesis picks one from `+` according to timing.")
    qa("How do you implement a multiplier-accumulator at high frequency?",
       "Pipeline the multiplier (partial products, Wallace/Dadda tree, final "
       "adder), keep the accumulator in carry-save form or register the "
       "adder, and size the accumulator for N products: 2W + ceil(log2 N) "
       "bits.")
    qa("What is the difference between latency and throughput? Give an "
       "example where pipelining increases latency but helps.",
       "Latency is the time for one result; throughput is results per unit "
       "time. A 4-stage pipelined multiplier has 4 cycles latency but "
       "delivers one product per cycle at a much higher clock.")
    qa("In a valid/ready pipeline, why must valid not depend on ready?",
       "The AXI rule: a source must not wait for `ready` before asserting "
       "`valid`, otherwise two components that each wait for the other "
       "deadlock. `ready` may depend on `valid`.")
    qa("What is a skid buffer and when do you need one?",
       "A 2-entry buffer that lets you register the `ready` path. Because "
       "the upstream sees the registered `ready` a cycle late, one beat may "
       "arrive after the stall; the skid register holds it. It breaks the "
       "long combinational `ready` chain without losing throughput.")
    qa("How do you detect full and empty in a synchronous FIFO?",
       "Use pointers one bit wider than the address. Empty: pointers equal. "
       "Full: addresses equal but MSBs differ. Alternatively keep an "
       "occupancy counter.")
    qa("FIFO depth: writer 100 MHz, bursts of 80 words with no idle; reader "
       "at 50 MHz reads one word every cycle. Minimum depth?",
       "Burst time = 80 / 100 MHz = 800 ns. Words read in that time = "
       "800 ns x 50 MHz = 40. Depth >= 80 - 40 = 40 words (add margin for "
       "synchronizer latency in an async FIFO, typically a few entries).")
    qa("FIFO depth: writer 80 MHz writes 1 of every 2 cycles; reader 50 MHz "
       "reads 1 of every 4 cycles; one burst of 120 words. Depth?",
       ["Write rate = 40 Mwords/s, read rate = 12.5 Mwords/s. Burst lasts "
        "120 / 40 M = 3 us; reads in that time = 3 us x 12.5 M = 37.5, so 37 "
        "complete. Depth >= 120 - 37 = 83 words.",
        "Worst case for back-to-back bursts: if bursts can follow each other "
        "without idle time the average write rate exceeds the read rate and "
        "**no** finite FIFO suffices - always state the idle assumption."])

    # --------------------------------------------------------------- CDC
    ah2("Clock-domain crossing and resets")
    qa("Why is a two-flop synchronizer enough for a single bit but not for "
       "a bus?",
       "Each bit resolves independently and may arrive a cycle apart, so a "
       "bus can be sampled with a mix of old and new bits (data "
       "incoherency). Buses need Gray coding (only one bit changes), a "
       "handshake with a stable data bus, or an async FIFO.")
    qa("How do you pass a single-cycle pulse from a fast to a slow domain?",
       "A fast pulse may fall between slow edges. Convert it to a level "
       "toggle in the source, synchronize the toggle, and XOR the last two "
       "stages in the destination. Pulses must be spaced by more than about "
       "two destination cycles, or use a handshake.",
       ["module pulse_sync (",
        "  input  logic src_clk, src_rst_n, src_pulse,",
        "  input  logic dst_clk, dst_rst_n,",
        "  output logic dst_pulse",
        ");",
        "  logic       tgl;",
        "  logic [2:0] s;",
        "  always_ff @(posedge src_clk or negedge src_rst_n)",
        "    if (!src_rst_n)     tgl <= 1'b0;",
        "    else if (src_pulse) tgl <= ~tgl;",
        "  always_ff @(posedge dst_clk or negedge dst_rst_n)",
        "    if (!dst_rst_n) s <= '0;",
        "    else            s <= {s[1:0], tgl};",
        "  assign dst_pulse = s[2] ^ s[1];",
        "endmodule"])
    qa("Why are async FIFO pointers Gray-coded?",
       "An incrementing Gray pointer changes one bit, so a synchronizer "
       "captures either the old or the new value - never a wild one. The "
       "synchronized value is stale, which makes full/empty pessimistic "
       "(safe) but never wrong.")
    qa("Can you Gray-code a FIFO pointer for a depth of 6?",
       "Not with a plain Gray counter: wrapping from 5 to 0 changes more "
       "than one bit. Use a power-of-two depth, or a special symmetric Gray "
       "sequence for even depths, or a handshake-based design.")
    qa("What is reconvergence and why is it a CDC bug?",
       "Two signals synchronized separately and then combined: they may "
       "arrive one cycle apart, creating a transient state the designer "
       "never intended. Synchronize them together as one encoded value or "
       "one handshake.")
    qa("What must never be in front of a synchronizer?",
       "Combinational logic from the source domain: it can glitch and the "
       "destination may capture the glitch. Register the signal in the "
       "source domain first.")
    qa("Asynchronous or synchronous reset?",
       "Async: works without a clock, no data-path logic, but deassertion "
       "must be synchronized (recovery/removal) and it is sensitive to "
       "glitches. Sync: timed like data, glitch-filtered, but needs a "
       "running clock and adds a gate to the D path. Common practice is "
       "**async assert, sync deassert** via a reset synchronizer.")
    qa("Write a reset synchronizer.",
       "Both flops are asynchronously cleared; a constant 1 shifts in after "
       "release so deassertion is aligned to the clock:",
       ["always_ff @(posedge clk or negedge rst_async_n)",
        "  if (!rst_async_n) rff <= 2'b00;",
        "  else              rff <= {rff[0], 1'b1};",
        "assign rst_sync_n = rff[1];"])
    qa("What is a reset-domain crossing (RDC) problem?",
       "A flop reset by reset A drives a flop that is **not** reset by A. "
       "When A asserts asynchronously the source output changes at an "
       "arbitrary time relative to the destination clock, which can go "
       "metastable. Fix with reset sequencing, isolation of the path during "
       "reset, or synchronizing on the destination side.")
    qa("How do you switch between two asynchronous clocks without glitches?",
       "Glitch-free clock mux: each select path goes through a synchronizer "
       "clocked by (the falling edge of) its own clock, and is gated by the "
       "other path's disabled state - the old clock is turned off on its own "
       "low phase before the new one is enabled on its low phase.")

    # ---------------------------------------------------------------- STA
    ah2("Static timing analysis")
    qa("What are the four timing path types?",
       "Input port to register, register to register, register to output "
       "port, and input port to output port (combinational feed-through).")
    qa("What is slack? Write the setup slack equation.",
       "Slack = required - arrival. Setup: required = T + capture clock "
       "latency - t_{setup} - uncertainty; arrival = launch latency + t_{cq} "
       "+ t_{path}. Negative slack is a violation.")
    qa("Positive skew helps which check and hurts which?",
       "Capture clock later than launch (positive skew) gives setup more "
       "time and makes hold harder. Useful skew is used deliberately by CTS "
       "to borrow time.")
    qa("What is a multicycle path and why adjust hold too?",
       "`set_multicycle_path 2 -setup` moves the setup check to the second "
       "edge; the hold check moves with it by default (to one edge before), "
       "which is too strict, so `set_multicycle_path 1 -hold` brings it back "
       "to the launch edge. The RTL must really hold data for two cycles "
       "(e.g. via an enable).")
    qa("False path versus clock group?",
       "`set_false_path` removes specific paths; `set_clock_groups "
       "-asynchronous` declares whole clocks unrelated so no paths between "
       "them are timed. Both hide real bugs if the crossing is not "
       "synchronized - CDC tools, not STA, verify those crossings.")
    qa("What does `set_input_delay` model?",
       "The time after the clock edge at which external data arrives at the "
       "input port - the external launch flop's clock-to-Q plus board and "
       "logic delay - so the tool knows how much of the period is left "
       "inside the chip.")
    qa("What are OCV derates and CRPR?",
       "On-chip variation makes nominally equal paths differ; derates slow "
       "the data path and speed the capture path (or vice versa for hold). "
       "Clock Reconvergence Pessimism Removal credits back the common part "
       "of the launch and capture clock paths, which cannot be both fast and "
       "slow at once.")
    qa("Which corners do you check setup and hold at?",
       "Setup at slow corners (SS, low V, high or low T depending on "
       "temperature inversion); hold at fast corners (FF, high V) - but "
       "sign-off checks both at all corners in the MCMM set.")
    qa("How do you fix a setup violation from the RTL side?",
       "Pipeline or retime, reduce logic depth (one-hot, precompute, "
       "parallel compare), remove late-arriving signals from deep cones, "
       "duplicate high-fanout registers, and break false priority chains.")
    qa("What is the difference between a generated clock and a virtual "
       "clock?",
       "A generated clock (`create_generated_clock`) is derived from a "
       "master inside the design (divider, mux); its latency includes the "
       "source path. A virtual clock has no source in the design and "
       "references IO delays to an external clock.")
    qa("Why is a clock divider made from a flop a problem, and what is "
       "better?",
       "It creates a new clock domain with skew relative to the source and "
       "requires a generated-clock constraint and CTS balancing. Prefer a "
       "clock enable (one flop gets `en` every N cycles) or an ICG driven by "
       "a counter.")

    # ---------------------------------------------------------- low power
    ah2("Low power")
    qa("Write the dynamic power equation and name the levers.",
       "P_{dyn} = alpha C V^{2} f (+ short-circuit). Levers: lower V (DVFS, "
       "multi-voltage), lower f, lower alpha (clock gating, operand "
       "isolation, data encoding), lower C (smaller cells, shorter wires).")
    qa("Why is clock gating done with a latch-based ICG, not an AND gate?",
       "An enable changing while the clock is high would chop the clock "
       "pulse. The latch is transparent while the clock is low, so the "
       "enable is frozen during the high phase. The ICG is a characterized "
       "library cell so STA checks the enable against the clock:",
       ["always_latch",
        "  if (!clk) en_l = en | test_en;   // transparent while clk is low",
        "assign gclk = clk & en_l;"])
    qa("How does RTL enable clock gating automatically?",
       "Any flop bank with a common load enable (`if (en) q <= d;`) is a "
       "candidate; synthesis replaces the feedback mux with an ICG when the "
       "bank is wide enough (typically >= 3-8 bits).")
    qa("What is the difference between power gating and clock gating?",
       "Clock gating stops switching (dynamic power) but keeps leakage and "
       "state. Power gating removes the supply (dynamic and leakage), "
       "needs isolation, retention or state restore, and costs wake-up "
       "latency and rush-current management.")
    qa("What goes into a UPF file?",
       "Power domains and their elements, supply nets and ports, power "
       "switches, isolation strategies (clamp value, enable, location), "
       "retention strategies (save/restore), level shifters and the power "
       "state table.")
    qa("Why do you need isolation cells?",
       "Outputs of a switched-off domain float to unknown levels, which "
       "causes X in simulation and crowbar current in real receivers. "
       "Isolation clamps them to 0/1/latched before power-down.")
    ah2("Design for test")
    qa("What does scan insertion do to a flop?",
       "Replaces it by a mux-D scan flop (`SE` selects `SI` or `D`) and "
       "stitches flops into chains. In shift mode the chain is a shift "
       "register; in capture mode flops capture functional logic outputs.")
    qa("What RTL styles hurt testability?",
       "Internally generated clocks and resets without test bypass, "
       "latches, combinational loops, gated clocks without `test_en`, "
       "tri-state buses, and X sources (uninitialized memories) reaching "
       "scan flops.")
    qa("Stuck-at versus transition faults?",
       "Stuck-at: node permanently 0/1, detected with slow-speed scan. "
       "Transition: node too slow to rise/fall; detected with at-speed "
       "launch-on-capture or launch-on-shift patterns using an OCC.")
    qa("What is scan compression and why is it needed?",
       "A decompressor expands a few tester channels into many short "
       "internal chains, and a compactor merges their outputs. Test time "
       "and data volume drop by 10-100x.")
    qa("How are memories tested?",
       "By MBIST: an on-chip controller runs March algorithms (e.g. March "
       "C-) and compares data; failing addresses can drive repair with "
       "redundant rows/columns.")
    qa("Name the JTAG signals and the purpose of the TAP.",
       "TCK, TMS, TDI, TDO, optional TRST. The TAP state machine selects "
       "the instruction register or a data register (BYPASS, IDCODE, "
       "boundary scan, user registers) for serial access.")
    qa("What is IEEE 1500 and how does IEEE 1687 differ?",
       "1500 defines a wrapper around a core (wrapper boundary register, "
       "WIR) so the core can be tested in isolation. 1687 (IJTAG) defines "
       "networks of embedded instruments with reconfigurable scan paths "
       "and portable procedures (ICL/PDL).")

    # --------------------------------------------------------------- buses
    ah2("On-chip buses")
    qa("Describe an APB write.",
       "Setup phase: `PSEL` = 1, `PENABLE` = 0, address/data/`PWRITE` valid. "
       "Access phase: `PENABLE` = 1; the transfer completes on the first "
       "clock with `PREADY` = 1, with `PSLVERR` reporting errors.")
    qa("What does AHB pipelining mean?",
       "The address phase of transfer N+1 overlaps the data phase of "
       "transfer N. A subordinate stretches the data phase by driving "
       "`HREADY` low, which also holds the next address phase.")
    qa("Why does AXI have five channels?",
       "Separate write address, write data, write response, read address "
       "and read data allow reads and writes in parallel, data before or "
       "after address, multiple outstanding transactions and out-of-order "
       "completion by ID.")
    qa("What are the AXI ordering rules for IDs?",
       "Transactions with the same ID must complete in order (per "
       "direction); different IDs may complete out of order. Write data "
       "has no ID in AXI4, so it must follow the AW order.")
    qa("Why may an AXI burst not cross a 4 KB boundary?",
       "4 KB is the minimum page/subordinate address granularity; limiting "
       "bursts keeps one burst inside one subordinate so the interconnect "
       "decodes only the first address.")
    qa("Compute the addresses of an AXI WRAP burst: AxADDR = 0x34, "
       "AxSIZE = 4 bytes, AxLEN = 3 (4 beats).",
       "Wrap boundary = 16 bytes (4 x 4), lower boundary 0x30. Beats: 0x34, "
       "0x38, 0x3C, 0x30.")
    qa("AXI4-Lite versus AXI4?",
       "Lite: every transaction is one beat, full data width, no IDs, "
       "bursts, locks, cache or QoS attributes - simple register access. "
       "AXI4: bursts up to 256 beats, IDs, outstanding and out-of-order.")
    qa("What is a bus deadlock and how can an interconnect cause one?",
       "A cycle of waits no one can break, e.g. a manager with outstanding "
       "reads to two subordinates with the same ID whose responses must be "
       "reordered, or write data interleaved wrongly. Interconnects avoid "
       "it with per-ID single-subordinate rules and bounded outstanding "
       "counts (Chapter 14).")

    # --------------------------------------------------------- verification
    ah2("Verification")
    qa("What makes a testbench self-checking?",
       "It predicts expected results with a reference model, compares them "
       "automatically in a scoreboard, and reports pass/fail with an error "
       "count - no waveform inspection required.")
    qa("Code coverage 100% - are you done?",
       "No. Code coverage shows lines were executed, not that results were "
       "checked or that required scenarios and corner cases (crosses, "
       "back-pressure, error responses) occurred. Functional coverage and "
       "checkers close the gap.")
    qa("Immediate versus concurrent assertions?",
       "Immediate: procedural, checked when executed like an `if`. "
       "Concurrent: clocked properties over time using sequences "
       "(`req |-> ##[1:3] ack`), sampled in the preponed region and usable "
       "by formal tools.")
    qa("What does `|->` versus `|=>` mean?",
       "`a |-> b`: if `a` holds, `b` must hold in the same cycle "
       "(overlapping). `a |=> b`: `b` must hold in the next cycle; "
       "equivalent to `a |-> ##1 b`.")
    qa("Write an assertion: once `valid` is high it stays high with stable "
       "data until `ready`.",
       "Shown without simulation (concurrent SVA):",
       ["property p_hold;",
        "  @(posedge clk) disable iff (!rst_n)",
        "    valid && !ready |=> valid && $stable(data);",
        "endproperty",
        "a_hold: assert property (p_hold) else $error(\"valid dropped\");"])
    qa("What are the main UVM components?",
       "Sequence item, sequence, sequencer, driver, monitor, agent "
       "(sequencer + driver + monitor), scoreboard, coverage collector, "
       "environment and test; connected with TLM ports and configured "
       "through `uvm_config_db`.")
    qa("What is the UVM phasing order?",
       "build, connect, end_of_elaboration, start_of_simulation, run (with "
       "parallel runtime sub-phases), extract, check, report, final. Build and final "
       "are top-down; the others are bottom-up.")
    qa("What does formal verification give you that simulation cannot?",
       "Exhaustive proof over all inputs and sequences up to a depth or "
       "unbounded, counterexamples in a few cycles, and early bring-up "
       "without a testbench. Limits: state explosion on large datapaths.")
    qa("Why run gate-level simulation if equivalence checking passes?",
       "To verify things LEC does not: reset/initialization with real X "
       "behaviour, timing with SDF (async paths, CDC structures), DFT modes "
       "and power-up sequences.")
    qa("Why can RTL simulation hide a reset bug that silicon exposes?",
       "X-optimism: `if (x_signal)` takes the else branch and `case` picks a "
       "branch, so an unreset flop looks deterministic in RTL. Gate-level "
       "or X-pessimistic simulation (X-prop modes) and reset lint catch it.")

    # ------------------------------------------------------------ puzzles
    ah2("Design puzzles")
    qa("Design a divide-by-3 clock with 50% duty cycle.",
       ["Count 0, 1, 2 on the rising edge and produce a pulse high for one "
        "input period. Delay that pulse by half a period with a falling-edge "
        "flop, and OR the two: the output is high for 1.5 of 3 periods. The "
        "OR is glitch-free because the second pulse rises before the first "
        "falls. In a real ASIC the output needs a generated-clock constraint "
        "and the OR should be a library clock cell.",
        "The testbench below measures the output after reset with a 10 ns "
        "input clock."],
       ["module div3_50 (",
        "  input  logic clk, rst_n,",
        "  output logic clk_div3",
        ");",
        "  logic [1:0] cnt;",
        "  logic       q_pos, q_neg;",
        "  always_ff @(posedge clk or negedge rst_n)",
        "    if (!rst_n) cnt <= '0;",
        "    else        cnt <= (cnt == 2'd2) ? 2'd0 : cnt + 2'd1;",
        "  always_ff @(posedge clk or negedge rst_n)   // high for 1 of 3 cycles",
        "    if (!rst_n) q_pos <= 1'b0;",
        "    else        q_pos <= (cnt == 2'd0);",
        "  always_ff @(negedge clk or negedge rst_n)   // same, half a cycle later",
        "    if (!rst_n) q_neg <= 1'b0;",
        "    else        q_neg <= q_pos;",
        "  assign clk_div3 = q_pos | q_neg;            // 1.5 of 3 cycles high",
        "endmodule"])
    code(["module tb_div3;",
          "  logic clk = 0, rst_n = 0, y;",
          "  always #5 clk = ~clk;                       // 10 ns input clock",
          "  div3_50 dut (.clk, .rst_n, .clk_div3(y));",
          "  realtime tr = 0;",
          "  always @(posedge y) begin",
          "    if (tr > 0) $display(\"t=%0t period=%0t\", $realtime, $realtime - tr);",
          "    tr = $realtime;",
          "  end",
          "  always @(negedge y) if (rst_n) $display(\"t=%0t high=%0t\", $realtime, "
          "$realtime - tr);",
          "  initial begin",
          "    #12 rst_n = 1;",
          "    #75 $finish;",
          "  end",
          "endmodule"])
    out(["t=30 high=15",
         "t=45 period=30",
         "t=60 high=15",
         "t=75 period=30",
         "div3.sv:32: $finish called at 87 (1s)"],
        caption="Icarus output: 30 ns period, 15 ns high - exactly 50% duty.")
    qa("Detect a rising and a falling edge of a synchronous signal.",
       "Delay the signal by one flop and compare. The pulses are one clock "
       "wide. If the input is asynchronous, synchronize it first and detect "
       "the edge on the synchronizer output.",
       ["logic a_q;",
        "always_ff @(posedge clk or negedge rst_n)",
        "  if (!rst_n) a_q <= 1'b0;",
        "  else        a_q <= a;",
        "assign rise =  a & ~a_q;",
        "assign fall = ~a &  a_q;"])
    qa("Count the number of ones in a 16-bit word.",
       "A `for` loop of additions describes it; synthesis builds an adder "
       "tree (or use `$countones`). For wide words or high frequency, "
       "pipeline the tree. The output needs $clog2(W+1) bits: 5 for W = 16.",
       ["module popcount #(parameter int W = 16) (",
        "  input  logic [W-1:0]           x,",
        "  output logic [$clog2(W+1)-1:0] n",
        ");",
        "  always_comb begin",
        "    n = '0;",
        "    for (int i = 0; i < W; i++)",
        "      n = n + x[i];",
        "  end",
        "endmodule"])
    qa("Check whether a number is a power of two; find its lowest set bit.",
       "`x & (x - 1)` clears the lowest set bit, so a power of two gives "
       "zero. `x & -x` isolates the lowest set bit - also the grant vector "
       "of a fixed-priority arbiter where bit 0 has the highest priority.",
       ["assign is_pow2 = (x != '0) && ((x & (x - 1'b1)) == '0);",
        "assign lsb1    = x & (~x + 1'b1);"])
    qa("Convert binary to Gray and Gray to binary.",
       "Binary to Gray is one XOR level; Gray to binary is a prefix XOR from "
       "the MSB down (a serial chain of W-1 XORs):",
       ["assign gray_out = bin_in ^ (bin_in >> 1);",
        "always_comb begin",
        "  bin_out[W-1] = gray_in[W-1];",
        "  for (int i = W-2; i >= 0; i--)",
        "    bin_out[i] = bin_out[i+1] ^ gray_in[i];",
        "end"])
    qa("Design a round-robin arbiter for N requesters.",
       "Keep a one-hot pointer to the last winner. Mask requests above the "
       "pointer; if any masked request exists grant its lowest bit (`m & -m`), "
       "else grant the lowest bit of the unmasked requests. Update the "
       "pointer only when a grant is accepted. This is two fixed-priority "
       "arbiters and a mux - O(log N) depth with prefix logic.")
    qa("Design a circuit that outputs 1 when the serial input so far, read "
       "MSB first, is divisible by 3.",
       "Keep the remainder r in {0, 1, 2}. Each new bit b updates "
       "r = (2r + b) mod 3: a 3-state FSM. Output is `r == 0`. The same "
       "trick works for any modulus.")
    qa("How many flops and what logic for a 0-to-9 BCD counter that can "
       "count up and down?",
       "Four flops. Next state = up ? (q == 9 ? 0 : q + 1) : (q == 0 ? 9 : "
       "q - 1). Carry/borrow out = en & (up ? q == 9 : q == 0), used to "
       "enable the next decade.")
    qa("A signal arrives from a 200 MHz domain as a one-cycle pulse and must "
       "be counted in a 25 MHz domain. Pulses can come every cycle. What do "
       "you do?",
       "A pulse synchronizer cannot keep up (it needs pulses spaced by "
       "several destination cycles). Count in the source domain and pass the "
       "counter across as a Gray code (sampled value may be stale but never "
       "wrong), or use an async FIFO of events. Then compute differences in "
       "the destination.")

    box("key", "How to answer design questions in interviews",
        ["State assumptions (clock relationship, reset, widths, throughput), "
         "draw the block diagram before code, name the hardware each line "
         "infers, and finish with how you would verify it and what limits "
         "its timing. Interviewers grade the reasoning, not the syntax."])


# =============================================================================
# Appendix D - tools, standards and resources
# =============================================================================
def _appx_d():
    appendix("Tools, Standards and Resources")

    ah2("IEEE and industry standards")
    tbl(["Standard", "Title / scope", "Where in this book"],
        [["IEEE 1364-2005", "Verilog HDL (merged into 1800 since 2009; no "
          "longer maintained separately)", "Ch. 3-4"],
         ["IEEE 1800-2023", "SystemVerilog: design, assertions, coverage, "
          "classes, DPI", "Ch. 3, 22, 23"],
         ["IEEE 1800.2", "UVM class library reference (2017, 2020 revisions)",
          "Ch. 24"],
         ["IEEE 1801", "UPF - Unified Power Format (UPF 3.x in 1801-2018; "
          "newer revisions follow)", "Ch. 19"],
         ["IEEE 1149.1", "JTAG boundary scan and TAP (2013 revision)", "Ch. 20"],
         ["IEEE 1500", "Embedded core test wrapper", "Ch. 20"],
         ["IEEE 1687", "IJTAG - access to embedded instruments (ICL/PDL)",
          "Ch. 20"],
         ["IEEE 1685", "IP-XACT - XML description of IP, registers, memory "
          "maps (2014, 2022)", "Ch. 15"],
         ["IEEE 1497", "SDF - Standard Delay Format", "Ch. 18, 26"],
         ["IEEE 1735", "IP encryption and rights management", "Ch. 21"],
         ["IEEE 1666", "SystemC (TLM models, HLS input)", "Ch. 16"],
         ["IEEE 754", "Floating-point arithmetic", "Ch. 8"],
         ["Accellera SystemRDL 2.0", "Register description language", "Ch. 15"],
         ["Accellera PSS", "Portable Test and Stimulus Standard", "Ch. 24"],
         ["SDC", "Synopsys Design Constraints (openly licensed Tcl subset)",
          "Ch. 18"],
         ["Liberty, LEF/DEF, SPEF", "Library, physical and parasitic "
          "exchange formats", "Ch. 17, 21"],
         ["ISO 26262", "Automotive functional safety (ASIL, FMEDA, safety "
          "mechanisms)", "Ch. 27"]],
        widths=[20, 58, 22], bold_first=True)

    ah2("AMBA and other bus specifications")
    tbl(["Specification", "Arm document", "Notes"],
        [["AMBA APB (APB2 ... APB5)", "IHI 0024", "Registers and slow "
          "peripherals; APB4 added `PPROT`/`PSTRB`"],
         ["AMBA AHB / AHB5", "IHI 0033", "Pipelined single-outstanding bus; "
          "AHB-Lite is the single-manager subset"],
         ["AMBA AXI (AXI3, AXI4, AXI5) incl. AXI4-Lite and ACE", "IHI 0022",
          "Main SoC data bus; ACE adds coherency"],
         ["AMBA AXI-Stream (AXI4-Stream, AXI5-Stream)", "IHI 0051",
          "Streaming datapaths, accelerators"],
         ["AMBA CHI", "IHI 0050", "Coherent Hub Interface for meshes"],
         ["AMBA ATB, DTI, LTI", "various", "Trace, SMMU translation interfaces"],
         ["TileLink", "SiFive / CHIPS Alliance", "RISC-V ecosystem (Rocket, "
          "Chipyard); TL-UL used by OpenTitan"],
         ["Wishbone B4", "OpenCores", "Simple open bus, common in hobby SoCs"],
         ["Avalon", "Intel FPGA", "Memory-mapped and streaming, Platform "
          "Designer"]],
        widths=[36, 18, 46], bold_first=True)
    p("Arm AMBA specifications are free to download from the Arm developer "
      "site after registration; always read the issue letter in the "
      "document ID, as signal lists changed between issues.")

    ah2("Open-source tools")
    tbl(["Tool", "Purpose", "Notes"],
        [["Icarus Verilog", "Event-driven Verilog/SV simulator",
          "Used for every example in this book; good Verilog-2005, partial "
          "SV"],
         ["Verilator", "SV to C++ compiler/simulator and linter",
          "Fastest open simulator; `--lint-only -Wall` is an excellent free "
          "linter; supports timing and many SV features since v5"],
         ["Yosys", "RTL synthesis framework", "Generic, FPGA (iCE40, ECP5, "
          "Gowin ...) and ASIC flows; `read_verilog -sv`"],
         ["OpenROAD", "Floorplan-to-GDS physical design", "Placement, CTS, "
          "routing, OpenSTA timing"],
         ["OpenLane / OpenLane 2 / LibreLane", "Automated RTL-to-GDS flow",
          "Wraps Yosys + OpenROAD + Magic/KLayout + Netgen for open PDKs"],
         ["OpenSTA", "Static timing analyser", "Reads Liberty, SDC, SPEF"],
         ["SymbiYosys (sby)", "Formal verification front end", "BMC, "
          "k-induction, cover; SVA subset via Yosys (full SVA with the "
          "commercial Tabby CAD Suite)"],
         ["cocotb", "Python coroutine testbenches", "Drives Icarus, "
          "Verilator and commercial simulators"],
         ["GTKWave", "Waveform viewer", "VCD, FST, LXT2"],
         ["Surfer", "Modern waveform viewer", "Fast, runs natively or in a "
          "browser; VCD/FST/GHW"],
         ["Verible", "SV parser, formatter, linter", "From CHIPS Alliance"],
         ["slang / sv2v / Surelog", "SV front ends", "Full-language "
          "elaboration; `sv2v` converts SV to Verilog for older tools"],
         ["KLayout, Magic, Netgen", "Layout viewer/DRC, layout editor, LVS",
          "Open-PDK sign-off tools"],
         ["FuseSoC / Edalize", "IP package manager and tool launcher", "Used "
          "by OpenTitan and many cores"]],
        widths=[22, 28, 50], bold_first=True)

    ah2("Commercial tools by flow step")
    tbl(["Flow step", "Synopsys", "Cadence", "Siemens EDA"],
        [["RTL simulation", "VCS", "Xcelium", "Questa"],
         ["Debug", "Verdi", "SimVision, Verisium Debug", "Visualizer"],
         ["Lint", "VC SpyGlass Lint", "Jasper Superlint, HAL", "Questa Lint"],
         ["CDC / RDC", "VC SpyGlass CDC/RDC", "Jasper CDC App",
          "Questa CDC / RDC"],
         ["Formal property checking", "VC Formal", "Jasper Formal "
          "Verification Platform", "Questa Formal (PropCheck)"],
         ["Low-power static checks", "VC LP", "Conformal Low Power",
          "Questa Power Aware"],
         ["Emulation / prototyping", "ZeBu / HAPS", "Palladium / Protium",
          "Veloce"],
         ["Logic synthesis", "Design Compiler, Fusion Compiler", "Genus",
          "Catapult (HLS); Precision (FPGA)"],
         ["DFT insertion and ATPG", "TestMAX (DFTMAX, TetraMAX)", "Modus",
          "Tessent"],
         ["Equivalence checking", "Formality", "Conformal LEC",
          "Questa SLEC (sequential)"],
         ["Place and route", "IC Compiler II, Fusion Compiler", "Innovus",
          "Aprisa"],
         ["Sign-off STA", "PrimeTime", "Tempus", "-"],
         ["Parasitic extraction", "StarRC", "Quantus", "Calibre xACT"],
         ["Power analysis / IR-EM", "PrimePower, RedHawk-SC", "Joules, Voltus",
          "PowerPro (RTL power)"],
         ["Physical verification (DRC/LVS)", "IC Validator", "Pegasus",
          "Calibre"]],
        widths=[24, 26, 26, 24], bold_first=True)
    box("note", "Tool names change",
        ["Vendors rename and bundle products frequently (and acquire each "
         "other - Synopsys completed its acquisition of Ansys in 2025). The "
         "flow step is the stable concept; check the current product name "
         "before quoting it in a resume or interview."])

    ah2("Papers and books")
    h3("Cliff Cummings (Sunburst Design) SNUG papers - required reading")
    bul(["**Nonblocking Assignments in Verilog Synthesis, Coding Styles That "
         "Kill!** (SNUG 2000) - the eight rules behind Chapter 4.",
         "**Simulation and Synthesis Techniques for Asynchronous FIFO "
         "Design** (SNUG 2002) and the follow-up with Peter Alfke on "
         "asynchronous pointer comparison.",
         "**Clock Domain Crossing (CDC) Design & Verification Techniques "
         "Using SystemVerilog** (SNUG 2008).",
         "**Synthesis and Scripting Techniques for Designing "
         "Multi-Asynchronous Clock Designs** (SNUG 2001).",
         "**Synchronous Resets? Asynchronous Resets? I am so confused!** and "
         "**Asynchronous & Synchronous Reset Design Techniques - Part Deux** "
         "(with Mills and Golson, SNUG 2002/2003).",
         "**full_case parallel_case, the Evil Twins of Verilog Synthesis** "
         "(SNUG 1999) and **State Machine Coding Styles for Synthesis**."])
    h3("Books")
    tbl(["Book", "Level", "Why read it"],
        [["Harris & Harris, __Digital Design and Computer Architecture__ "
          "(RISC-V edition)", "Beginner", "Logic to a pipelined RISC-V in "
          "SystemVerilog"],
         ["Weste & Harris, __CMOS VLSI Design: A Circuits and Systems "
          "Perspective__", "Intermediate", "Transistors, timing, power, "
          "sequencing - what your RTL becomes"],
         ["Pong P. Chu, __FPGA Prototyping by SystemVerilog Examples__",
          "Beginner", "Hands-on RTL design with complete projects"],
         ["Stuart Sutherland, __RTL Modeling with SystemVerilog for "
          "Simulation and Synthesis__", "Intermediate", "Synthesis-oriented "
          "SV coding"],
         ["Sutherland & Mills, __Verilog and SystemVerilog Gotchas__",
          "Intermediate", "101 language traps"],
         ["Chris Spear & Greg Tumbush, __SystemVerilog for Verification__",
          "Intermediate", "OOP testbenches, randomization, coverage"],
         ["Ray Salemi, __The UVM Primer__", "Beginner (UVM)", "The shortest "
          "path into UVM"],
         ["Cerny et al., __SVA: The Power of Assertions in SystemVerilog__",
          "Advanced", "Complete SVA semantics"],
         ["Seligman, Schubert, Kumar, __Formal Verification: An Essential "
          "Toolkit__", "Advanced", "Practical formal methodology"],
         ["Bhasker & Chadha, __Static Timing Analysis for Nanometer "
          "Designs__", "Intermediate", "STA and SDC in depth"],
         ["Keating et al., __Low Power Methodology Manual__", "Intermediate",
          "Clock/power gating, multi-voltage"],
         ["Bushnell & Agrawal, __Essentials of Electronic Testing__",
          "Advanced", "Fault models, ATPG, BIST"],
         ["Kaeslin, __Top-Down Digital VLSI Design__", "Intermediate",
          "Architecture-to-silicon methodology"],
         ["Dally & Towles, __Principles and Practices of Interconnection "
          "Networks__", "Advanced", "NoC theory"],
         ["Hennessy & Patterson, __Computer Architecture: A Quantitative "
          "Approach__", "Advanced", "Pipelines, caches, memory systems"]],
        widths=[52, 16, 32])

    ah2("Open-source SoC and processor projects to study")
    tbl(["Project", "Language", "What to learn from it"],
        [["OpenTitan (lowRISC)", "SystemVerilog", "Production-quality "
          "silicon root of trust: style guide, reggen CSRs, TL-UL, full UVM "
          "and formal sign-off - the best public example of an industrial "
          "flow"],
         ["Ibex (lowRISC)", "SystemVerilog", "Small 2/3-stage RV32 core, "
          "extensively verified"],
         ["PULP Platform (ETH Zurich / Bologna)", "SystemVerilog",
          "AXI IP library (`pulp-platform/axi`), common_cells, clusters, "
          "PULPissimo, Cheshire"],
         ["CVA6 (OpenHW Group)", "SystemVerilog", "64-bit Linux-capable "
          "application core, MMU, caches"],
         ["Rocket Chip / Chipyard (Berkeley)", "Chisel (Scala)",
          "Generator-based SoCs, TileLink, BOOM out-of-order core"],
         ["VexRiscv", "SpinalHDL", "Highly configurable RV32 core "
          "via plugins"],
         ["PicoRV32", "Verilog", "Tiny, readable size-optimised RV32 core"],
         ["SERV", "Verilog", "Bit-serial RISC-V - the smallest core"]],
        widths=[26, 16, 58], bold_first=True)

    ah2("Getting real silicon: shuttles and open PDKs")
    tbl(["Program / PDK", "Details"],
        [["Tiny Tapeout", "Low-cost educational shuttle: many small designs "
          "share one chip behind a mux, submitted from a GitHub template with "
          "Verilog or cocotb tests. After Efabless closed in 2025 it moved to "
          "other fabrication routes, including IHP SG13G2 shuttles."],
         ["SkyWater SKY130", "Open 130 nm PDK (Google + SkyWater, 2020); "
          "powered the free Google/Efabless Open MPW shuttles and remains "
          "the most documented open PDK."],
         ["GlobalFoundries GF180MCU", "Open 180 nm PDK (Google + GF); good "
          "for mixed-signal and 5 V IO experiments."],
         ["IHP SG13G2", "Open 130 nm SiGe BiCMOS PDK from IHP; IHP runs "
          "open MPW runs, some free for research and education."],
         ["Europractice / MOSIS-style MPW", "Commercial-PDK shuttles for "
          "universities (TSMC, GF, UMC ...) under NDA; the normal academic "
          "route to advanced nodes."]],
        widths=[24, 76], bold_first=True)

    ah2("A suggested order of use")
    bul(["Write and simulate with **Icarus** or **Verilator**, view with "
         "**GTKWave** or **Surfer**, lint with `verilator --lint-only -Wall`.",
         "Test with **cocotb** or a SystemVerilog testbench (Chapter 22); "
         "prove small properties with **SymbiYosys**.",
         "Synthesize with **Yosys** and read the statistics and critical "
         "path (Chapter 17); run a block through **OpenLane/LibreLane** on "
         "SKY130 or IHP to see the full RTL-to-GDS picture.",
         "Put a design on **Tiny Tapeout** - nothing on a resume beats "
         "\"my RTL is in silicon\" (Chapter 30).",
         "Read OpenTitan and PULP RTL for style; read Cummings' papers for "
         "the reasons behind the style."], ordered=True)


def appendices():
    part("Appendices",
         numbered=False,
         blurb="A Verilog/SystemVerilog quick reference, a glossary of about "
         "150 terms, 100 interview questions with answers, and the tools, "
         "standards and resources that make up the RTL engineer's world.")
    _appx_a()
    _appx_b()
    _appx_c()
    _appx_d()
