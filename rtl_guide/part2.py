"""Part II - Core RTL Building Blocks (Chapters 5-10).

Every synthesizable example and testbench below was compiled with
`iverilog -g2012 -Wall` (Icarus Verilog 12) and every out() card is pasted
from the actual `vvp` run.
"""

from rtl_guide.common import *  # noqa: F401,F403


def part2():
    part("Core RTL Building Blocks",
         "The handful of structures from which every chip is assembled: "
         "combinational logic that does not accidentally remember, flops "
         "with the right reset, state machines that cannot get lost, "
         "arithmetic that does not silently overflow, memories and FIFOs, "
         "and the valid/ready pipelines that move data through an SoC "
         "at one word per clock.")
    _ch5()
    _ch6()
    _ch7()
    _ch8()
    _ch9()
    _ch10()


# =============================================================================
#                      CHAPTER 5 - COMBINATIONAL LOGIC
# =============================================================================
def _ch5():
    chapter("Combinational Logic", newpage=False)
    p("Combinational logic is the part of a design whose outputs depend only "
      "on its **current** inputs. It has no memory, no clock and no state - and "
      "the single most common way beginners break a design is by writing "
      "something they believe is combinational that the synthesis tool "
      "correctly interprets as having memory. This chapter shows how to "
      "describe combinational hardware so that simulation, synthesis and "
      "your intent all agree, and what gates each coding style produces.")
    box("key", "The contract of a combinational block",
        "For every possible input combination, every output is assigned a "
        "value, and that value is a pure function of the inputs. If any path "
        "through the code leaves an output unassigned, the output must "
        "'remember' its previous value - and the only hardware that remembers "
        "without a clock edge is a **latch**.")

    h2("assign versus always_comb")
    p("There are two ways to write combinational logic in SystemVerilog. A "
      "continuous `assign` describes one net as an expression; it is ideal for "
      "short Boolean equations, muxes written with `?:`, and wiring. An "
      "`always_comb` block describes one or more variables procedurally, "
      "which is clearer as soon as there are `case` statements, loops or "
      "intermediate values.")
    code(r'''module mux4_assign (
  input  logic [7:0] a, b, c, d,
  input  logic [1:0] sel,
  output logic [7:0] y
);
  assign y = (sel == 2'd0) ? a :
             (sel == 2'd1) ? b :
             (sel == 2'd2) ? c : d;
endmodule

module mux4_case (
  input  logic [7:0] a, b, c, d,
  input  logic [1:0] sel,
  output logic [7:0] y
);
  always_comb begin
    case (sel)
      2'd0:    y = a;
      2'd1:    y = b;
      2'd2:    y = c;
      default: y = d;
    endcase
  end
endmodule''', "Two descriptions of the same 4:1 multiplexer. Synthesis produces "
       "identical netlists: the tool recognises that the `sel` values are "
       "mutually exclusive and builds a balanced mux, not a chain.")
    tbl(["Property", "`always @*` (Verilog-2001)", "`always_comb` (SystemVerilog)"],
        [["Sensitivity list", "Inferred, but misses variables read inside "
          "called functions", "Inferred, **including** function bodies"],
         ["Runs at time 0", "No - output is X until an input changes",
          "Yes - evaluates once at time zero, so constants propagate"],
         ["Multiple drivers", "Allowed (a bug)", "Illegal: a variable written "
          "in `always_comb` may not be written anywhere else"],
         ["Latch check", "None", "Tools warn if the block infers storage"],
         ["Blocking `=`", "Required by convention", "Required by convention"]],
        widths=[22, 39, 39], bold_first=True,
        caption="Always prefer `always_comb`; use `always_latch` in the rare "
        "case you really want a latch, so your intent is explicit.")
    box("tip", "Use blocking assignments in combinational blocks",
        "Inside `always_comb`, write `=` (blocking). The block then reads like "
        "software: a later statement sees the value an earlier statement "
        "assigned, which is exactly how the default-then-override idiom works. "
        "Non-blocking `<=` in combinational code creates simulation/synthesis "
        "mismatches and extra delta cycles (Chapter 4).")

    h2("Priority logic versus parallel logic")
    p("An `if / else if` chain has **priority** semantics: the first true "
      "condition wins, so the second condition is only evaluated when the "
      "first is false. In hardware that becomes a chain of 2:1 muxes whose "
      "depth grows with the number of branches. A `case` whose items are "
      "mutually exclusive describes **parallel** selection: an AND-OR mux "
      "whose depth grows only with log of the number of inputs.")
    diagram([
        "  if (c0) y=a; else if (c1) y=b; else if (c2) y=c; else y=d;",
        "",
        "  d ---|0\\",
        "       | |---+",
        "  c ---|1/   +--|0\\",
        "        c2      | |---+",
        "  b ------------|1/   +--|0\\",
        "                 c1      | |---- y      3 mux levels in series: c0 has the",
        "  a ---------------------|1/            shortest path to y, d and c the longest",
        "                          c0",
        "",
        "  case (sel) 0:a 1:b 2:c 3:d    ->  decode sel once, then one AND-OR level",
        "",
        "      a & (sel==0) --+",
        "      b & (sel==1) --+--[ OR ]---- y     every input has the same path length",
        "      c & (sel==2) --+",
        "      d & (sel==3) --+",
    ], "Priority chain versus parallel mux. Use priority only where the "
       "specification really has priority (interrupts, arbiters, exception "
       "ordering).")
    p("Modern synthesis tools are good at restructuring: if they can prove the "
      "`if` conditions are mutually exclusive (for example because they all "
      "compare the same signal against different constants), they flatten the "
      "chain. They **cannot** do this when the conditions are independent "
      "signals, because then the priority is real functionality. The RTL "
      "designer's job is therefore to write priority only when it is intended "
      "- and to put the late-arriving (timing-critical) signal in the "
      "**first** `if`, closest to the output.")
    box("expert", "Interview insight: 'where would you put a late signal?'",
        "In a priority chain, the condition tested **first** drives the final "
        "mux nearest the output, so it has the shortest path. If static timing "
        "reports that `c2` arrives late, restructure so that `c2` selects "
        "between two precomputed results at the output: "
        "`y = c2 ? y_if_c2 : y_if_not_c2;`. This 'late-select' transformation is "
        "a standard timing fix you will use in Chapter 18.")

    h2("unique, priority, and the dangers of parallel_case")
    p("SystemVerilog adds two qualifiers that let you state what you know "
      "about a `case` or `if` chain. They are **checked in simulation** and "
      "used as **optimisation permission** by synthesis.")
    tbl(["Qualifier", "What you promise", "Simulation check",
         "Synthesis may"],
        [["`unique case`", "Exactly one item matches (items are mutually "
          "exclusive AND complete)", "Warning if zero or more than one item "
          "matches", "Build a parallel mux; treat unmatched values as "
          "don't-care"],
         ["`unique0 case`", "At most one item matches", "Warning if more "
          "than one matches", "Build a parallel mux"],
         ["`priority case`", "At least one item matches; order matters",
          "Warning if none matches", "Treat unmatched values as "
          "don't-care, keep priority"],
         ["`// synopsys parallel_case full_case`", "Same as `unique`, but "
          "only the synthesis tool reads it", "**None** - simulation still "
          "has priority and latch behaviour", "Optimise as told - creating "
          "a sim/synth mismatch if you were wrong"]],
        widths=[20, 28, 26, 26], bold_first=True)
    code(r'''module alu_unique (
  input  logic [1:0] op,
  input  logic [7:0] a, b,
  output logic [7:0] y
);
  always_comb begin
    y = '0;
    unique case (op)
      2'b00: y = a + b;
      2'b01: y = a - b;
      2'b10: y = a & b;
      2'b11: y = a | b;
    endcase
  end
endmodule''', "`unique` documents that the four items are exhaustive and "
       "exclusive; if `op` were ever X, simulators flag a violation instead "
       "of silently keeping the default.")
    box("warn", "PITFALL - the old full_case / parallel_case pragmas",
        "These comments change what synthesis builds without changing what "
        "simulation does. If the promise is false, the gate-level netlist "
        "behaves differently from the RTL you verified - the classic "
        "'works in RTL sim, fails in gate sim' bug. Many companies ban them in "
        "their coding guidelines (Chapter 27). `unique` and `priority` are "
        "safe replacements because the simulator checks the promise.")

    h2("casez, casex and don't-cares")
    p("`casez` treats `z` and `?` in the case items as don't-care bits. It is "
      "the standard way to write a priority encoder or an instruction decoder "
      "compactly. `casex` also treats `x` in the **selector** as don't-care, "
      "which means an X on the input can silently match a branch and hide a "
      "bug; avoid `casex` in design code.")
    code(r'''// 8-input priority encoder: highest set bit wins
module prienc8 (
  input  logic [7:0] req,
  output logic [2:0] idx,
  output logic       valid
);
  always_comb begin
    idx   = '0;            // default assignments: no latch possible
    valid = 1'b1;
    casez (req)
      8'b1???????: idx = 3'd7;
      8'b01??????: idx = 3'd6;
      8'b001?????: idx = 3'd5;
      8'b0001????: idx = 3'd4;
      8'b00001???: idx = 3'd3;
      8'b000001??: idx = 3'd2;
      8'b0000001?: idx = 3'd1;
      8'b00000001: idx = 3'd0;
      default:     valid = 1'b0;
    endcase
  end
endmodule''')
    p("A table like this does not scale to 64 requesters. The parameterised "
      "form uses a loop in which the **last** assignment wins - so iterating "
      "upward gives the highest index priority. Synthesis unrolls the loop "
      "into exactly the same priority structure.")
    code(r'''// Same function written as a parameterised loop (last assignment wins)
module prienc_loop #(parameter int N = 8) (
  input  logic [N-1:0]         req,
  output logic [$clog2(N)-1:0] idx,
  output logic                 valid
);
  localparam int W = $clog2(N);
  always_comb begin
    idx = '0;
    for (int i = 0; i < N; i++)
      if (req[i]) idx = W'(i);
    valid = |req;
  end
endmodule''')

    h2("Decoders, encoders and one-hot logic")
    p("A **decoder** turns an n-bit binary code into a 2^{n}-bit one-hot "
      "vector; an **encoder** does the reverse. They are the glue of every "
      "SoC: address decoders select peripherals (Chapter 14), register-file "
      "write ports decode the destination register (Chapter 9), and arbiters "
      "produce one-hot grants that must be encoded back to an index.")
    code(r'''module dec3to8 (
  input  logic [2:0] a,
  input  logic       en,
  output logic [7:0] y
);
  assign y = en ? (8'b1 << a) : 8'b0;
endmodule

// One-hot -> binary encoder: an OR tree, no priority
module oh2bin #(parameter int N = 8) (
  input  logic [N-1:0]         oh,
  output logic [$clog2(N)-1:0] bin
);
  localparam int W = $clog2(N);
  always_comb begin
    bin = '0;
    for (int i = 0; i < N; i++)
      bin |= oh[i] ? W'(i) : '0;
  end
endmodule''')
    p("Notice the difference between `oh2bin` and `prienc_loop`. Because the "
      "one-hot encoder **assumes** at most one bit is set, it can simply OR "
      "together the indices of the set bits: bit k of the output is the OR of "
      "all input bits whose index has bit k set. That is a single OR level of "
      "N/2 inputs per output bit - much smaller and faster than a priority "
      "encoder. The cost is that it returns garbage if two bits are set. Use "
      "it when the one-hot property is guaranteed by construction (an "
      "arbiter's grant, a one-hot FSM) and protect the guarantee with an "
      "assertion (Chapter 23).")
    code(r'''module tb_ch5;
  logic [7:0] req;
  logic [2:0] i1, i2, b;
  logic       v1, v2;
  int errors = 0;
  prienc8        u1 (.req(req), .idx(i1), .valid(v1));
  prienc_loop #(8) u2 (.req(req), .idx(i2), .valid(v2));
  oh2bin     #(8) u3 (.oh(req), .bin(b));
  initial begin
    for (int k = 0; k < 256; k++) begin
      req = k[7:0];
      #1;
      if (i1 !== i2 || v1 !== v2) errors++;
      if ($countones(req) == 1 && b !== i1) errors++;
      if (k == 0 || k == 1 || k == 8'h12 || k == 8'h80 || k == 8'hFF)
        $display("req=%b  prienc idx=%0d valid=%b  loop idx=%0d", req, i1, v1, i2);
    end
    $display("exhaustive check of 256 vectors: %0d errors", errors);
    $finish;
  end
endmodule''', "An exhaustive self-checking testbench: with only 8 inputs, all "
       "256 combinations are cheap, so there is no excuse for anything less.")
    out(["req=00000000  prienc idx=0 valid=0  loop idx=0",
         "req=00000001  prienc idx=0 valid=1  loop idx=0",
         "req=00010010  prienc idx=4 valid=1  loop idx=4",
         "req=10000000  prienc idx=7 valid=1  loop idx=7",
         "req=11111111  prienc idx=7 valid=1  loop idx=7",
         "exhaustive check of 256 vectors: 0 errors"],
        "Icarus Verilog output. The table-driven and loop-based encoders agree "
        "on every input, and the one-hot encoder agrees wherever its "
        "precondition holds.")
    p("The one-hot mux is the data-path counterpart of the one-hot encoder: "
      "AND each input with its select bit and OR the results. It is the "
      "fastest possible mux for a wide select and it appears in every "
      "crossbar and arbiter.")
    code(r'''module onehot_mux #(parameter int N = 4, W = 8) (
  input  logic [N-1:0]      sel,     // must be one-hot (or zero)
  input  logic [N-1:0][W-1:0] din,
  output logic [W-1:0]      y
);
  always_comb begin
    y = '0;
    for (int i = 0; i < N; i++)
      y |= din[i] & {W{sel[i]}};
  end
endmodule''')

    h2("Unintended latches, and how never to write one")
    p("A latch is inferred whenever a variable assigned in a combinational "
      "block is **not assigned on every path**. The two classic causes are an "
      "incomplete `case` and an `if` without an `else`.")
    code(r'''// BUG: latch inferred on y when sel == 2'd3, on grant when req == 0
module latch_bug (
  input  logic [1:0] sel,
  input  logic [7:0] a, b, c,
  input  logic       req,
  output logic [7:0] y,
  output logic       grant
);
  always @* begin
    case (sel)
      2'd0: y = a;
      2'd1: y = b;
      2'd2: y = c;
    endcase
    if (req) grant = 1'b1;
  end
endmodule''', "Two latches: `y` keeps its value when `sel` is 3, and `grant` "
       "once set can never be cleared. Icarus compiles this without "
       "complaint - latch detection is a job for synthesis and lint.")
    code(r'''module latch_fixed (
  input  logic [1:0] sel,
  input  logic [7:0] a, b, c,
  input  logic       req,
  output logic [7:0] y,
  output logic       grant
);
  always_comb begin
    y     = '0;        // default first ...
    grant = 1'b0;
    case (sel)         // ... then override
      2'd0: y = a;
      2'd1: y = b;
      2'd2: y = c;
      default: ;       // explicit: keep the default
    endcase
    if (req) grant = 1'b1;
  end
endmodule''', "The default-assignment idiom: assign every output at the top "
       "of the block, then override. It is impossible to create a latch this "
       "way, however the branches are later edited.")
    box("warn", "PITFALL - why latches are bad in an ASIC flow",
        "A latch is not wrong in itself - high-performance custom designs use "
        "them deliberately. Unintended latches are wrong because: (1) they are "
        "**transparent** while enabled, so a combinational loop through them "
        "can oscillate; (2) their enable is a data-derived signal that glitches, "
        "so they capture garbage; (3) static timing uses time-borrowing rules "
        "for latches that no one on your team planned for; (4) scan insertion "
        "and ATPG handle them poorly (Chapter 20); (5) the behaviour differs "
        "between RTL and gate-level simulation. Treat every synthesis "
        "'latch inferred' message as an error.")
    checklist("Latch-free combinational code", [
        "Use `always_comb`, never `always @(a or b)` with a hand-written list.",
        "Assign a default value to every output at the top of the block.",
        "Give every `case` a `default`, even when all values are listed "
        "(it costs nothing and survives later edits).",
        "Every `if` that assigns an output either has an `else` or is covered "
        "by a default.",
        "Never read a variable in the same `always_comb` before it has been "
        "assigned in that block (that is a loop or a latch).",
    ])

    h2("Parity, comparators and other everyday functions")
    code(r'''module parity_cmp (
  input  logic [31:0] d,
  input  logic [15:0] x, y,
  output logic        even_par,   // 1 when the number of ones is odd -> makes total even
  output logic        eq, lt_u, lt_s
);
  assign even_par = ^d;
  assign eq       = (x == y);
  assign lt_u     = (x < y);
  assign lt_s     = ($signed(x) < $signed(y));
endmodule''')
    tbl(["Function", "Hardware", "Depth for N bits", "Notes"],
        [["`^d` parity", "XOR tree", "log2(N) XOR levels",
          "Used in memory parity and bus protection (Chapter 9)"],
         ["`x == y`", "N XNORs + AND tree", "1 + log2(N)",
          "Cheap; equality against a constant is even cheaper"],
         ["`x < y`", "A subtractor's carry-out (or a dedicated comparator tree)",
          "~log2(N) with a fast carry", "Signedness changes the logic - see "
          "Chapter 8"],
         ["`|v`, `&v`", "OR / AND reduction tree", "log2(N)",
          "'Any bit set' / 'all bits set'"],
         ["`$countones(v)`", "Adder tree (population count)", "~log2(N) adder "
          "levels", "Much larger than it looks - avoid on wide buses"]],
        widths=[16, 30, 20, 34], bold_first=True)

    h2("Combinational loops and logic depth")
    p("A **combinational loop** is a path from a signal back to itself through "
      "gates only, with no flop in between. It is almost always a bug: the "
      "circuit either oscillates or latches in an unpredictable state, static "
      "timing cannot analyse it (the tool breaks the loop arbitrarily), and "
      "simulators may hang in an infinite delta-cycle loop. Loops usually "
      "appear across module boundaries - module A's output feeds B, whose "
      "output combinationally feeds back into A. The valid/ready handshake is "
      "the most common place this happens; Chapter 10 gives the rules that "
      "prevent it.")
    diagram([
        "   +-------- module A --------+        +------- module B -------+",
        "   |  ready_out = f(valid_in) |------->|  valid_out = g(ready) |---+",
        "   +--------------------------+        +------------------------+   |",
        "              ^                                                    |",
        "              +---------------- no flop anywhere ------------------+",
    ], "A combinational loop created by two individually reasonable modules. "
       "Lint tools (Chapter 25) find these; code reviews should too.")
    p("**Logic depth** is the number of gate levels between two flops. At a "
      "given process node, one gate level (an FO4 inverter delay) costs "
      "roughly 10-20 ps in an advanced node and 50-100 ps in an older one, so "
      "a 1 GHz clock allows roughly 20-40 levels after flop overhead, and a "
      "fast CPU pipeline stage perhaps 12-20. As an RTL designer you control "
      "depth by choosing structures: a parallel mux instead of a priority "
      "chain, a one-hot encoder instead of a priority encoder, a tree instead "
      "of a chain, and - when nothing else works - an extra pipeline stage "
      "(Chapter 10).")
    box("intuit", "Think in levels, not lines",
        "Ten lines of `assign` can be two levels of logic; one line containing "
        "`a * b + c` can be forty. When you write RTL, keep a rough gate-level "
        "picture in mind for every expression. Synthesis is powerful, but it "
        "cannot change the fundamental depth of the function you asked for.")

    h2("Summary")
    bul([
        "Combinational means every output is assigned on every path and "
        "depends only on current inputs; anything else infers a latch.",
        "Use `always_comb` with blocking assignments and the "
        "default-then-override idiom; use `assign` for simple equations.",
        "`if/else if` chains imply priority (a mux chain); mutually exclusive "
        "`case` items imply a parallel mux. Put late signals first in a chain.",
        "`unique` and `priority` document intent and are checked in "
        "simulation; never use the `full_case`/`parallel_case` pragmas.",
        "Use `casez` for don't-cares, never `casex`. Know the hardware behind "
        "decoders, one-hot encoders, priority encoders and one-hot muxes.",
        "Avoid combinational loops (especially across modules) and control "
        "logic depth by choosing the right structure.",
    ])
    h2("Exercises")
    bul([
        "Write a parameterised priority encoder where the **lowest** set bit "
        "wins, and verify it exhaustively for N = 8 against a behavioural "
        "model.",
        "Rewrite `latch_bug` so that `grant` genuinely needs to hold state "
        "(set by `req`, cleared by `clr`). What kind of element should hold it, "
        "and where must that code live?",
        "Draw the gate-level structure of `oh2bin` for N = 8. How many OR "
        "gates, and how many levels, does each output bit need?",
        "An `if` chain tests `a`, then `b`, then `c`, all independent 1-bit "
        "signals. Timing shows `c` arrives very late. Rewrite the logic so "
        "`c` drives only the final 2:1 mux, and prove equivalence with an "
        "exhaustive testbench.",
        "Explain precisely what goes wrong in simulation and in synthesis if "
        "`unique case` is used but two items can match at the same time.",
    ], ordered=True)


# =============================================================================
#          CHAPTER 6 - SEQUENTIAL LOGIC: FLIP-FLOPS, RESETS AND ENABLES
# =============================================================================
def _ch6():
    chapter("Sequential Logic: Flip-Flops, Resets and Enables")
    p("Sequential logic is where a design gets its memory and its sense of "
      "time. In a synchronous ASIC almost all state lives in edge-triggered "
      "D flip-flops that update on the rising edge of a clock. How you write "
      "a flop decides which standard cell the synthesis tool picks - with or "
      "without a reset pin, with or without an enable mux - and those choices "
      "ripple into area, timing, power, testability and reset-domain safety. "
      "This chapter covers the flop itself, the families of counters and "
      "registers built from it, and the small utility circuits every SoC "
      "reuses.")

    h2("Coding the D flip-flop")
    p("The rules are short. Use `always_ff`, trigger on `posedge clk` (plus "
      "the reset edge for an asynchronous reset), use non-blocking `<=` for "
      "every assignment, and assign each register in exactly one block. "
      "`always_ff` lets tools check that the block really describes flops: "
      "an assignment path without a clock edge becomes an error rather than a "
      "silent latch.")
    code(r'''// Flop styles
module dff_styles (
  input  logic       clk, rst_n, srst, en,
  input  logic [7:0] d,
  output logic [7:0] q_async, q_sync, q_en, q_norst
);
  // async active-low reset: maps to a DFF with a reset pin (DFFR)
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) q_async <= '0;
    else        q_async <= d;

  // sync active-high reset: plain DFF + AND gate in front of D
  always_ff @(posedge clk)
    if (srst) q_sync <= '0;
    else      q_sync <= d;

  // enable: recirculating mux (or an enable-flop / clock gate)
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n)  q_en <= '0;
    else if (en) q_en <= d;

  // datapath flop, no reset: smallest, fastest cell
  always_ff @(posedge clk)
    q_norst <= d;
endmodule''', "Four flop flavours. Each maps to different cells; knowing which "
       "is the difference between an RTL coder and an RTL designer.")
    diagram([
        "  async reset -> DFFR cell               sync reset -> DFF + gate in D path",
        "         +-------+                                       +-------+",
        "  d -----| D   Q |----- q_async          srst -[NOT]-+   |       |",
        "  clk ---|>      |                                 [AND]-| D   Q |----- q_sync",
        "         |  RN   |                       d ----------+   |       |",
        "         +---+---+                                 clk --|>      |",
        "             |                                           +-------+",
        "           rst_n",
        "",
        "  enable -> DFF + recirculating mux            no reset -> plain DFF",
        "           +-----+    +-------+                                +-------+",
        "  d -------|1    |    |       |                d --------------| D   Q |--- q_norst",
        "           | MUX |----| D   Q |---+--- q_en              clk --|>      |",
        "      +----|0    |    |       |   |                            +-------+",
        "      |    +-----+ clk|>      |   |",
        "      |       ^       +-------+   |",
        "      |       en                  |",
        "      +---------------------------+",
    ], "What each style becomes. Synchronous reset and enable are logic in "
       "front of D; asynchronous reset is a pin on the cell itself.")

    h2("Synchronous versus asynchronous reset")
    tbl(["Aspect", "Asynchronous reset", "Synchronous reset"],
        [["Cell", "DFF with reset/set pin (larger, slightly slower clk->Q)",
          "Plain DFF; reset is an AND gate in the D path"],
         ["Needs a clock to reset?", "**No** - resets immediately, even with "
          "the clock stopped or not yet running", "**Yes** - reset must be "
          "held for at least one active clock edge"],
         ["Timing", "Reset path is timed with recovery/removal checks on "
          "**deassertion**", "Reset is ordinary data; it adds a gate to the D "
          "path, which can hurt critical paths"],
         ["Glitch sensitivity", "A glitch on the reset net resets the flop - "
          "the net must be clean", "Glitches are filtered by the clock edge"],
         ["Reset fan-out", "Large distribution tree, built like a clock tree",
          "Also large, but treated as data by synthesis and timing"],
         ["DFT", "Reset must be controllable in scan mode (Chapter 20)",
          "Transparent to scan"],
         ["Typical use", "Most ASIC control logic, power-on reset, anything "
          "that must be safe before clocks run", "FPGA designs (flop reset "
          "pins are often synchronous), some high-speed ASIC datapaths"]],
        widths=[20, 40, 40], bold_first=True)
    p("The deciding question in an ASIC is usually: **must this flop be in a "
      "known state before the clock is running?** Output enables of pads, "
      "power-switch controls and clock-gating controls must be, so they get "
      "asynchronous reset. The danger of an asynchronous reset is not its "
      "assertion but its **deassertion**: if reset releases too close to a "
      "clock edge, some flops leave reset in this cycle and some in the next, "
      "or a flop goes metastable. The universal solution is **asynchronous "
      "assert, synchronous deassert** - reset asserts immediately, but the "
      "release is passed through a two-flop synchroniser in each clock "
      "domain. Chapter 12 builds this reset synchroniser and the complete "
      "reset architecture of an SoC.")
    box("warn", "PITFALL - mixing reset and non-reset flops in one block",
        "If a single `always_ff` resets `ctrl` but not `data`, synthesis must "
        "keep `data` unchanged during reset - so it adds an enable mux on "
        "`data` driven by `rst_n`, turning the reset into a data-path signal. "
        "Put flops with reset and flops without reset in separate `always_ff` "
        "blocks.")

    h2("Flops without reset")
    p("Not every flop needs a reset. A pipeline data register, a memory array, "
      "or a shift register whose contents are always qualified by a "
      "separately reset **valid** bit can start with any value. Removing the "
      "reset from these flops saves the reset pin (area), removes a load from "
      "the reset tree (power and routing), and removes a gate from the data "
      "path (timing). In a large accelerator, datapath flops outnumber control "
      "flops by ten to one, so this is a significant saving.")
    box("key", "The rule",
        "**Reset the control, not the data.** Every flop whose value can "
        "influence control flow or be observed before it is written (FSM "
        "state, valid bits, counters, configuration registers, anything that "
        "drives an output pin) must be reset. Pure data that is always "
        "qualified by a reset valid bit need not be. The price is X in "
        "simulation until the first write - which is a feature: X propagation "
        "reveals any place where unqualified data leaks into control.")

    h2("Enables, and a first look at clock gating")
    p("`else if (en) q <= d;` describes a flop that holds its value when `en` "
      "is low. Synthesis implements this as a 2:1 recirculating mux in front "
      "of D or as a library enable-flop. Both still clock the flop every cycle "
      "and so still burn clock power. For a bank of flops sharing one enable, "
      "the power tool can instead insert an **integrated clock-gating cell** "
      "(ICG) that stops the clock altogether - often the single largest "
      "dynamic-power saving in a chip. Writing clean, shared enables is what "
      "makes this automatic insertion possible; Chapter 19 covers clock "
      "gating in depth.")

    h2("Shift registers")
    code(r'''module shreg #(parameter int W = 8, D = 4) (
  input  logic         clk, en, sin,
  input  logic [W-1:0] din,
  output logic [W-1:0] dout,
  output logic [D-1:0] sr
);
  logic [W-1:0] pipe [D];
  always_ff @(posedge clk) begin
    if (en) sr <= {sr[D-2:0], sin};     // serial-in, parallel-out
    pipe[0] <= din;                     // D-deep delay line (maps to SRL on FPGA)
    for (int i = 1; i < D; i++) pipe[i] <= pipe[i-1];
  end
  assign dout = pipe[D-1];
endmodule''', "Non-blocking assignments make the order of statements "
       "irrelevant: every stage samples its predecessor's **old** value, "
       "exactly as real flops do. With blocking `=` the loop would collapse "
       "into a single stage.")

    h2("Counters")
    p("Counters are the most common sequential structure after plain "
      "registers: timers, address generators, FIFO pointers, baud-rate "
      "dividers and watchdogs are all counters. The encoding of the count is a "
      "design choice with real consequences.")
    tbl(["Counter", "States with N flops", "Next-state logic",
         "Property that matters"],
        [["Binary", "2^{N}", "An incrementer (carry chain)",
          "Dense; several bits toggle at once (e.g. 0111 -> 1000)"],
         ["Gray", "2^{N}", "Binary increment + XOR", "**One bit changes per "
          "step** - safe to sample in another clock domain (Chapter 11)"],
         ["Johnson (twisted ring)", "2N", "One inverter", "Glitch-free decode "
          "with 2-input gates; no carry chain"],
         ["Ring (one-hot)", "N", "None (a rotate)", "Output is already decoded; "
          "fastest possible"],
         ["LFSR", "2^{N} - 1", "A few XORs", "Pseudo-random sequence; tiny and "
          "fast; used for BIST, scramblers, CRCs, test patterns"]],
        widths=[18, 16, 26, 40], bold_first=True)
    code(r'''module up_down_counter #(parameter int W = 4) (
  input  logic         clk, rst_n, en, up,
  output logic [W-1:0] cnt
);
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n)  cnt <= '0;
    else if (en) cnt <= up ? cnt + 1'b1 : cnt - 1'b1;
endmodule

// Gray counter: keep a binary register, register its Gray code
module gray_counter #(parameter int W = 4) (
  input  logic         clk, rst_n, en,
  output logic [W-1:0] gray
);
  logic [W-1:0] bin, bin_nxt;
  assign bin_nxt = bin + 1'b1;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      bin  <= '0;
      gray <= '0;
    end else if (en) begin
      bin  <= bin_nxt;
      gray <= bin_nxt ^ (bin_nxt >> 1);   // registered: glitch-free output
    end
endmodule''')
    code(r'''module johnson_counter #(parameter int W = 4) (
  input  logic         clk, rst_n,
  output logic [W-1:0] q
);
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) q <= '0;
    else        q <= {q[W-2:0], ~q[W-1]};
endmodule

// 8-bit maximal-length Fibonacci LFSR, taps x^8 + x^6 + x^5 + x^4 + 1
module lfsr8 (
  input  logic       clk, rst_n, en,
  output logic [7:0] q
);
  logic fb;
  assign fb = q[7] ^ q[5] ^ q[4] ^ q[3];
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n)  q <= 8'h01;          // any non-zero seed; all-zero locks up
    else if (en) q <= {q[6:0], fb};
endmodule''')
    box("warn", "PITFALL - the Gray output must come from a flop",
        "Computing `gray = bin ^ (bin >> 1)` combinationally from a binary "
        "register gives the right **value**, but when several `bin` bits "
        "toggle, the XOR outputs can glitch through intermediate codes before "
        "settling. A synchroniser in another domain can sample a glitch. The "
        "counter above registers the Gray code itself - this is exactly how "
        "the asynchronous FIFO pointers of Chapter 11 are built.")
    p("Ring and Johnson counters have the opposite weakness: most of their "
      "2^{N} possible states are **illegal**. An SEU (a particle strike) or a "
      "glitch that puts a ring counter into 0110 leaves it cycling two hot "
      "bits forever. Production designs add self-correction - for example, "
      "force the state back to the reset value whenever the "
      "`$onehot` property is violated - the same 'safe FSM' idea as Chapter 7.")

    h2("Edge detectors, pulse stretchers and debouncers")
    code(r'''module edge_detect (
  input  logic clk, rst_n, sig,
  output logic rise, fall, any
);
  logic sig_d;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) sig_d <= 1'b0;
    else        sig_d <= sig;
  assign rise = sig & ~sig_d;
  assign fall = ~sig & sig_d;
  assign any  = sig ^ sig_d;
endmodule

// Stretch a 1-cycle pulse to N cycles (retriggerable)
module pulse_stretch #(parameter int N = 4) (
  input  logic clk, rst_n, pin,
  output logic pout
);
  logic [$clog2(N+1)-1:0] cnt;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n)          cnt <= '0;
    else if (pin)        cnt <= N[$clog2(N+1)-1:0];
    else if (cnt != '0)  cnt <= cnt - 1'b1;
  assign pout = (cnt != '0);
endmodule''', "The edge detector compares the signal with its value one "
       "clock ago. `sig` must already be synchronous to `clk` - an "
       "asynchronous input needs a synchroniser first (Chapter 11).")
    code(r'''// Debouncer: output follows input only after it is stable for STABLE cycles.
// 'din' must already be synchronised to clk (Chapter 11).
module debounce #(parameter int STABLE = 4) (
  input  logic clk, rst_n, din,
  output logic dout
);
  logic [$clog2(STABLE)-1:0] cnt;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      cnt  <= '0;
      dout <= 1'b0;
    end else if (din == dout) begin
      cnt  <= '0;                                // no change pending
    end else if (cnt == $clog2(STABLE)'(STABLE-1)) begin
      dout <= din;                               // stable long enough
      cnt  <= '0;
    end else begin
      cnt  <= cnt + 1'b1;
    end
endmodule''', "A real button debouncer uses STABLE of about 10-20 ms worth of "
       "clock cycles, i.e. a counter of 18-22 bits at tens of MHz; the logic "
       "is identical.")
    p("The testbench below instantiates all of these blocks side by side and "
      "prints them cycle by cycle, measures the LFSR period, and feeds the "
      "debouncer a glitchy input followed by a clean one.")
    code(r'''module tb_ch6;
  logic clk = 0, rst_n = 0, en = 1, up = 1;
  logic [3:0] cnt, gray, john;
  logic [7:0] lf;
  logic sig = 0, rise, fall, any, pout, db_in = 0, db_out;
  always #5 clk = ~clk;
  up_down_counter #(4) u_cnt (.clk, .rst_n, .en, .up, .cnt);
  gray_counter    #(4) u_gry (.clk, .rst_n, .en, .gray);
  johnson_counter #(4) u_jon (.clk, .rst_n, .q(john));
  lfsr8                u_lf  (.clk, .rst_n, .en, .q(lf));
  edge_detect          u_ed  (.clk, .rst_n, .sig, .rise, .fall, .any);
  pulse_stretch   #(3) u_ps  (.clk, .rst_n, .pin(rise), .pout);
  debounce        #(4) u_db  (.clk, .rst_n, .din(db_in), .dout(db_out));

  int period = 0;
  logic [7:0] seed;
  initial begin
    repeat (2) @(posedge clk);
    rst_n <= 1;
    $display("cyc bin gray john lfsr | sig rise fall pout");
    for (int c = 0; c < 9; c++) begin
      @(posedge clk);
      sig <= (c == 2 || c == 3 || c == 4);
      #1 $display("%3d %b %b %b %h  |  %b   %b    %b    %b",
                  c, cnt, gray, john, lf, sig, rise, fall, pout);
    end
    // LFSR period
    seed = lf;
    do begin @(posedge clk); #1 period++; end while (lf != seed);
    $display("LFSR period = %0d", period);
    // debouncer: glitchy press then a clean one
    db_in <= 1; @(posedge clk); db_in <= 0; @(posedge clk);
    db_in <= 1; @(posedge clk); db_in <= 0; @(posedge clk);
    $display("after glitches   : dout=%b", db_out);
    db_in <= 1; repeat (6) @(posedge clk);
    $display("after 6 stable 1s: dout=%b", db_out);
    $finish;
  end
endmodule''')
    out(["cyc bin gray john lfsr | sig rise fall pout",
         "  0 0001 0001 0001 02  |  0   0    0    0",
         "  1 0010 0011 0011 04  |  0   0    0    0",
         "  2 0011 0010 0111 08  |  1   1    0    0",
         "  3 0100 0110 1111 11  |  1   0    0    1",
         "  4 0101 0111 1110 23  |  1   0    0    1",
         "  5 0110 0101 1100 47  |  0   0    1    1",
         "  6 0111 0100 1000 8e  |  0   0    0    0",
         "  7 1000 1100 0000 1c  |  0   0    0    0",
         "  8 1001 1101 0001 38  |  0   0    0    0",
         "LFSR period = 255",
         "after glitches   : dout=0",
         "after 6 stable 1s: dout=1"],
        "Icarus Verilog output. Check the Gray column: exactly one bit changes "
        "per row. The Johnson counter walks 0001 -> 0011 -> 0111 -> 1111 -> "
        "1110 -> ... with period 2N = 8. The LFSR visits all 255 non-zero "
        "states. `rise` is a one-cycle pulse; `pout` stretches it to 3 "
        "cycles, starting one cycle later because the stretcher is "
        "registered.")
    box("tip", "Why the testbench waits #1 before printing",
        "At `@(posedge clk)` the non-blocking updates of that edge have not "
        "happened yet, so a `$display` in the same time step would print the "
        "**old** values - a race by design (Chapter 4). A small delay after "
        "the edge (or sampling at the opposite edge) makes the output "
        "unambiguous. An early version of this very testbench measured an "
        "'LFSR period of 1' because the loop compared `lf` before it updated.")

    h2("Register retiming")
    p("**Retiming** moves flops backward or forward across combinational "
      "logic without changing the cycle-level behaviour seen at the module's "
      "outputs. If a path has 30 levels of logic before a register and 5 "
      "after, moving the register back by 12 levels balances the two stages. "
      "Synthesis tools can retime automatically (Chapter 17), but only across "
      "logic they are allowed to touch: flops with asynchronous reset, flops "
      "with `dont_touch`, and flops that are observed by other modules or "
      "debug logic often cannot move. A practical RTL technique is to add "
      "one or two extra register stages at the end of a deep function and let "
      "the tool redistribute them.")
    diagram([
        "   before:  [FF] --- 30 levels --- [FF] --- 5 levels --- [FF]     max stage = 30",
        "   after :  [FF] --- 18 levels --- [FF] --- 17 levels -- [FF]     max stage = 18",
        "            same latency (2 cycles), same outputs, ~1.6x higher clock",
    ], "Retiming changes where registers sit, never how many sit on each path.")

    h2("Summary")
    bul([
        "Code flops with `always_ff`, non-blocking `<=`, one block per "
        "register group; separate reset and non-reset flops.",
        "Asynchronous reset uses a reset pin and works without a clock; its "
        "deassertion must be synchronised (Chapter 12). Synchronous reset is "
        "data-path logic that needs a clock edge.",
        "Reset the control, not the data: datapath flops qualified by a "
        "valid bit need no reset.",
        "Enables become recirculating muxes or clock gates (Chapter 19).",
        "Choose counter encodings deliberately: binary (dense), Gray (one bit "
        "changes, CDC-safe when registered), Johnson/ring (fast decode, need "
        "self-correction), LFSR (tiny pseudo-random).",
        "Edge detectors, pulse stretchers and debouncers are small, reusable "
        "blocks - but all require an already-synchronised input.",
    ])
    h2("Exercises")
    bul([
        "Write a modulo-10 (BCD) counter with a carry output and chain two of "
        "them into a 00-99 counter. Verify every transition in a testbench.",
        "Convert `lfsr8` to the Galois form (XORs inside the shift path) and "
        "show by simulation that it also has period 255. Which form has the "
        "shorter critical path, and why?",
        "Add self-correction to `johnson_counter`: detect any of the 8 illegal "
        "4-bit states and return to 0000. Inject an illegal state with `force` "
        "in the testbench to prove recovery.",
        "Explain, with a gate-level sketch, what synthesis builds for an "
        "`always_ff` that resets `state` but not `data` in the same block.",
        "A 32-bit datapath register loads every cycle when `valid` is high. "
        "Estimate the area saving of removing its reset in a library where a "
        "DFFR is 20% larger than a DFF, and list what must be true for the "
        "change to be safe.",
    ], ordered=True)


# =============================================================================
#                     CHAPTER 7 - FINITE STATE MACHINES
# =============================================================================
def _ch7():
    chapter("Finite State Machines")
    p("A finite state machine (FSM) is the control brain of almost every "
      "block: bus interfaces, DMA engines, protocol controllers, power "
      "sequencers and arbiters are all FSMs steering a datapath. An FSM is a "
      "state register plus two pieces of combinational logic - one computing "
      "the **next state** from the current state and inputs, the other "
      "computing the **outputs**. The art lies in coding it so that it is "
      "readable, glitch-free where it matters, fast, and impossible to lock "
      "up.")
    diagram([
        "                +-------------------+        +---------+",
        "  inputs ------>|  next-state logic |--nxt-->|  state  |---+---- state",
        "          +---->|   (always_comb)   |        |  flops  |   |",
        "          |     +-------------------+   clk->|         |   |",
        "          |                                  +---------+   |",
        "          +------------------------------------------------+",
        "          |     +-------------------+",
        "          +---->|   output logic    |------> outputs   (Moore: state only)",
        "  inputs - - - >|                   |                  (Mealy: state + inputs)",
        "                +-------------------+",
    ], "The canonical FSM structure. Moore outputs depend on the state only; "
       "Mealy outputs also depend on the current inputs (dashed path).")

    h2("Moore versus Mealy")
    tbl(["", "Moore", "Mealy"],
        [["Outputs depend on", "Current state only", "Current state **and** "
          "current inputs"],
         ["Reaction to an input", "One cycle later (after the state changes)",
          "Same cycle - combinational path from input to output"],
         ["Number of states", "Often more", "Often fewer"],
         ["Glitches on outputs", "Only from state decoding; none if outputs "
          "are registered or one-hot", "Input glitches pass straight through"],
         ["Timing across modules", "Clean: output starts at a flop (or near "
          "one)", "Creates input-to-output combinational paths that chain "
          "across modules and may form loops"],
         ["Typical use", "Most SoC control; anything leaving the block",
          "Fast internal handshakes, where one cycle of latency matters"]],
        widths=[22, 39, 39], bold_first=True)

    h2("Coding styles: one, two or three always blocks")
    p("There are three common ways to code an FSM. All are legal and "
      "synthesise well; the differences are readability and where the outputs "
      "come from.")
    tbl(["Style", "Structure", "Strengths", "Weaknesses"],
        [["Three-block", "`always_ff` state register; `always_comb` next "
          "state; separate `always_comb`/`assign` outputs",
          "Clearest mapping to hardware; easy to review; Moore/Mealy obvious",
          "Outputs are combinational (decoded from state) unless registered "
          "separately"],
         ["Two-block", "`always_ff` for state (and registered outputs); one "
          "`always_comb` for next state (and any combinational outputs)",
          "Compact; the most common industrial style",
          "Mixing outputs into the next-state block can hide latches without "
          "defaults"],
         ["One-block", "Everything in one `always_ff`",
          "Short; every output automatically registered",
          "Outputs lag the state by one cycle unless you assign them on the "
          "transition; harder to read and review"]],
        widths=[14, 34, 26, 26], bold_first=True)
    p("The first example is a serial pattern detector for the bit sequence "
      "**1011**, allowing overlaps (so 1011011 contains two matches). It uses "
      "the three-block style and an `enum` state type.")
    code(r'''// Moore detector for serial pattern 1011 (overlapping), 3-block style
module seq1011_moore (
  input  logic clk, rst_n, din,
  output logic hit
);
  typedef enum logic [2:0] {S0, S1, S10, S101, S1011} state_t;
  state_t state, nxt;

  // 1) state register
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) state <= S0;
    else        state <= nxt;

  // 2) next-state logic
  always_comb begin
    nxt = state;                         // default: stay
    case (state)
      S0:    if (din) nxt = S1; else nxt = S0;
      S1:    if (din) nxt = S1; else nxt = S10;
      S10:   if (din) nxt = S101; else nxt = S0;
      S101:  if (din) nxt = S1011; else nxt = S10;
      S1011: if (din) nxt = S1; else nxt = S10; // overlap: "1" or "10" already seen
      default: nxt = S0;                 // illegal codes 5..7 recover
    endcase
  end

  // 3) output logic: Moore -> function of state only
  assign hit = (state == S1011);
endmodule''', "State names describe the history seen so far. The `default` "
       "item sends the three unused 3-bit codes back to S0.")
    tbl(["State (history seen)", "Next if din = 0", "Next if din = 1", "hit"],
        [["S0 (nothing useful)", "S0", "S1", "0"],
         ["S1 (\"1\")", "S10", "S1", "0"],
         ["S10 (\"10\")", "S0", "S101", "0"],
         ["S101 (\"101\")", "S10", "S1011", "0"],
         ["S1011 (match)", "S10", "S1", "**1**"]],
        widths=[30, 25, 25, 20], bold_first=True,
        caption="State-transition table of the Moore 1011 detector. After a "
        "match, the final '1' can start a new pattern (-> S1), and "
        "a following '0' already gives '10' (-> S10): that is what "
        "'overlapping' means.")
    p("The Mealy version needs one state fewer: instead of entering a "
      "'found it' state, it raises `hit` during the cycle in which the final "
      "'1' is on the input.")
    code(r'''// Mealy detector for the same pattern: one fewer state, one cycle earlier
module seq1011_mealy (
  input  logic clk, rst_n, din,
  output logic hit
);
  typedef enum logic [1:0] {S0, S1, S10, S101} state_t;
  state_t state, nxt;

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) state <= S0;
    else        state <= nxt;

  always_comb begin
    nxt = state;
    hit = 1'b0;
    case (state)
      S0:    if (din) nxt = S1; else nxt = S0;
      S1:    if (din) nxt = S1; else nxt = S10;
      S10:   if (din) nxt = S101; else nxt = S0;
      S101: begin
              if (din) nxt = S1; else nxt = S10;
              hit = din;                 // Mealy: depends on the input
            end
      default: nxt = S0;
    endcase
  end
endmodule''')
    code(r'''module tb_seq;
  logic clk = 0, rst_n = 0, din = 0, hit_moore, hit_mealy;
  logic [15:0] stim = 16'b1011_0110_1101_1000;  // sent MSB first
  logic [3:0]  hist = '0;
  int exp_hits = 0, moore_hits = 0, mealy_hits = 0;
  always #5 clk = ~clk;
  seq1011_moore u_moore (.clk, .rst_n, .din, .hit(hit_moore));
  seq1011_mealy u_mealy (.clk, .rst_n, .din, .hit(hit_mealy));
  initial begin
    @(negedge clk) rst_n = 1;
    $display("bit din | mealy moore");
    for (int i = 15; i >= 0; i--) begin
      din = stim[i];
      hist = {hist[2:0], din};
      exp_hits += (hist == 4'b1011);     // reference model
      #1 $display("%3d  %b  |   %b     %b", 15 - i, din, hit_mealy, hit_moore);
      mealy_hits += hit_mealy;
      @(negedge clk);
      moore_hits += hit_moore;
    end
    $display("expected %0d, Mealy saw %0d, Moore saw %0d",
             exp_hits, mealy_hits, moore_hits);
    $finish;
  end
endmodule''', "Inputs change on the falling edge, so the rising edge always "
       "samples stable data. A 4-bit history register is the reference model.")
    out(["bit din | mealy moore",
         "  0  1  |   0     0",
         "  1  0  |   0     0",
         "  2  1  |   0     0",
         "  3  1  |   1     0",
         "  4  0  |   0     1",
         "  5  1  |   0     0",
         "  6  1  |   1     0",
         "  7  0  |   0     1",
         "  8  1  |   0     0",
         "  9  1  |   1     0",
         " 10  0  |   0     1",
         " 11  1  |   0     0",
         " 12  1  |   1     0",
         " 13  0  |   0     1",
         " 14  0  |   0     0",
         " 15  0  |   0     0",
         "expected 4, Mealy saw 4, Moore saw 4"],
        "Icarus Verilog output. Four overlapping matches (bits 0-3, 3-6, 6-9, "
        "9-12). The Mealy output fires in the same cycle as the last '1'; the "
        "Moore output fires one cycle later, after the state register has "
        "moved to S1011.")

    h2("State encoding")
    p("An `enum` lets you write the FSM with names and leave the encoding to a "
      "later decision - either by giving explicit values or by letting the "
      "synthesis tool re-encode (FSM extraction). The choice matters:")
    tbl(["Encoding", "Flops for S states", "Next-state / output logic",
         "Best for"],
        [["Binary", "ceil(log2 S)", "Denser decode; outputs need a comparator "
          "on several bits", "Area-critical ASIC FSMs with many states"],
         ["One-hot", "S", "Very simple: each state flop's input is an OR of "
          "its incoming transitions; outputs are ORs of state bits",
          "Speed; FPGAs (flops are free); FSMs with many transitions"],
         ["Gray", "ceil(log2 S)", "Like binary; one bit changes on each "
          "**sequential** transition", "Linear FSMs, lower toggle power, "
          "state observed across a CDC"],
         ["Johnson", "S/2", "Two-bit decode per state", "Small sequencers"],
         ["Output-encoded", "Varies", "Outputs are state bits directly - no "
          "decode at all", "Glitch-free registered outputs at zero cost"]],
        widths=[16, 16, 38, 30], bold_first=True)
    code(r'''// One-hot FSM coded explicitly: one flop per state, "reverse case" on 1'b1
module arb_onehot (
  input  logic clk, rst_n, req, gnt_ack, err,
  output logic busy
);
  localparam int IDLE = 0, WAIT = 1, XFER = 2, ERR = 3;
  logic [3:0] st, nx;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) st <= 4'b0001;
    else        st <= nx;
  always_comb begin
    nx = '0;
    unique case (1'b1)
      st[IDLE]: if (req)     nx[WAIT] = 1'b1; else nx[IDLE] = 1'b1;
      st[WAIT]: if (gnt_ack) nx[XFER] = 1'b1; else nx[WAIT] = 1'b1;
      st[XFER]: if (err)     nx[ERR]  = 1'b1; else nx[IDLE] = 1'b1;
      st[ERR]:                nx[IDLE] = 1'b1;
      default:                nx[IDLE] = 1'b1;   // 0 or >1 hot bits: recover
    endcase
  end
  assign busy = st[WAIT] | st[XFER];            // one OR gate: fast outputs
endmodule''', "The 'reverse case' idiom compares the constant `1'b1` against "
       "each state bit. With `unique`, synthesis knows only one bit is hot "
       "and builds per-bit logic without priority.")
    box("expert", "What synthesis really does with your enum",
        "Tools such as Design Compiler and Genus recognise FSMs (a register "
        "whose next value is a function of itself through a `case`) and may "
        "re-encode them - to one-hot for speed, or Gray/binary for area - "
        "unless told not to. Re-encoding is safe for function but has two side "
        "effects: the state bits you probe in gate-level simulation no longer "
        "match your enum values, and the 'safe' recovery logic for illegal "
        "states can be optimised away because, from the tool's point of view, "
        "unreachable states do not exist. The next section shows how to keep it.")

    h2("Safe FSMs and illegal-state recovery")
    p("With binary encoding and S states that are not a power of two, some "
      "codes are unused; with one-hot encoding, all codes with zero or more "
      "than one hot bit are illegal - 12 of the 16 codes in `arb_onehot`. "
      "In normal operation these states are unreachable. But a single-event "
      "upset from a particle strike, a supply glitch, or a reset released "
      "asynchronously without synchronisation can put the register into one. "
      "A **safe** FSM guarantees it returns to a known state within a bounded "
      "number of cycles.")
    bul([
        "**Default branch.** Always code `default: nxt = IDLE;` (and `nx = "
        "'0` plus a recovery branch for one-hot). This is necessary but not "
        "sufficient, because synthesis may remove logic for unreachable states.",
        "**Tell the tool.** Use the tool's safe-FSM option (for example a "
        "`fsm_encoding`/`safe_implementation` attribute or a `set_fsm_...` "
        "command, depending on the vendor) or disable FSM re-encoding for "
        "that register so your recovery logic survives.",
        "**Detect and report.** For safety-critical designs (ISO 26262 "
        "automotive, IEC 61508), add an explicit illegal-state detector "
        "(`!$onehot(st)`) that raises an error flag or interrupt, and consider "
        "parity or triple-modular redundancy (TMR) on the state register.",
        "**Verify it.** Use `force` in simulation or a formal check "
        "(Chapter 25) to prove every illegal code recovers.",
    ])

    h2("Registered outputs")
    p("Outputs decoded combinationally from state bits can glitch when "
      "several state bits change at once - harmless inside a synchronous "
      "block, fatal if the output is a clock enable, an asynchronous reset, "
      "a pad or a signal crossing a clock domain. There are three standard "
      "cures: (1) one-hot encoding, where a Moore output that depends on a "
      "single state is just a flop output; (2) **register the outputs**, "
      "computing them from the **next** state so they are not delayed a "
      "cycle; (3) output encoding, where the state code is chosen so that "
      "output bits are state bits. The handshake controller below uses "
      "technique (2).")
    code(r'''// 4-phase req/ack initiator with registered outputs (2-block style:
// one always_ff for state AND outputs, one always_comb for next state)
module hs4_master (
  input  logic clk, rst_n,
  input  logic start,       // request a transfer (sampled in IDLE)
  input  logic ack,         // from the responder (already synchronised)
  output logic req,         // registered -> glitch-free
  output logic done         // 1-cycle pulse, registered
);
  typedef enum logic [1:0] {IDLE, REQ_HI, REQ_LO} state_t;
  state_t state, nxt;

  always_comb begin
    nxt = state;
    case (state)
      IDLE:    if (start) nxt = REQ_HI;
      REQ_HI:  if (ack)   nxt = REQ_LO;   // phase 2 seen: drop req
      REQ_LO:  if (!ack)  nxt = IDLE;     // phase 4 seen: finished
      default:            nxt = IDLE;
    endcase
  end

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      state <= IDLE;
      req   <= 1'b0;
      done  <= 1'b0;
    end else begin
      state <= nxt;
      req   <= (nxt == REQ_HI);            // output decoded from NEXT state
      done  <= (state == REQ_LO) && !ack;  // registered: aligned with IDLE
    end
endmodule''', "A four-phase handshake: req rises, ack rises, req falls, ack "
       "falls. Because `req` is computed from `nxt`, it rises on the same "
       "edge that the state enters REQ_HI - registered, yet with no extra "
       "latency.")
    code(r'''  // slow responder in the testbench: ack follows req after 2 clocks
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) {ack, req_d} <= '0;
    else        {ack, req_d} <= {req_d, req};
  always @(posedge clk) if (mon)
    $display("t=%3t start=%b req=%b ack=%b done=%b state=%s",
             $time, start, req, ack, done, u_hs.state.name());''',
         "Excerpt of the testbench (the full file also drives `start` and "
         "tests the GCD FSMD below). `.name()` prints the enum label.")
    out(["t= 25 start=0 req=0 ack=0 done=0 state=IDLE",
         "t= 35 start=1 req=0 ack=0 done=0 state=IDLE",
         "t= 45 start=0 req=1 ack=0 done=0 state=REQ_HI",
         "t= 55 start=0 req=1 ack=0 done=0 state=REQ_HI",
         "t= 65 start=0 req=1 ack=0 done=0 state=REQ_HI",
         "t= 75 start=0 req=1 ack=1 done=0 state=REQ_HI",
         "t= 85 start=0 req=0 ack=1 done=0 state=REQ_LO",
         "t= 95 start=0 req=0 ack=1 done=0 state=REQ_LO",
         "t=105 start=0 req=0 ack=1 done=0 state=REQ_LO",
         "t=115 start=0 req=0 ack=0 done=0 state=REQ_LO",
         "t=125 start=0 req=0 ack=0 done=1 state=IDLE"],
        "Icarus Verilog output, sampled at each rising edge. `req` and the "
        "state change on the same edge; `done` pulses as the FSM returns to "
        "IDLE.")

    h2("FSMD: a state machine with a datapath")
    p("Real blocks are rarely a bare FSM. An **FSMD** (FSM with datapath) "
      "combines a controller with registers and arithmetic that it sequences. "
      "The classic example is Euclid's GCD algorithm, which also introduces "
      "the valid/ready interface used throughout the rest of the book.")
    code(r'''// FSMD: Euclid's GCD by subtraction. Controller + datapath in one module.
module gcd_fsmd #(parameter int W = 16) (
  input  logic         clk, rst_n,
  input  logic         in_valid,
  output logic         in_ready,
  input  logic [W-1:0] a_in, b_in,
  output logic         out_valid,
  output logic [W-1:0] result
);
  typedef enum logic [1:0] {IDLE, CALC, DONE} state_t;
  state_t state;
  logic [W-1:0] a, b;

  assign in_ready  = (state == IDLE);
  assign out_valid = (state == DONE);
  assign result    = a;

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      state <= IDLE;
      a <= '0;
      b <= '0;
    end else begin
      case (state)
        IDLE: if (in_valid) begin
                a <= a_in;  b <= b_in;  state <= CALC;
              end
        CALC: if (b == '0)  state <= DONE;
              else if (a >= b) a <= a - b;
              else begin a <= b;  b <= a; end      // swap
        DONE: state <= IDLE;
        default: state <= IDLE;
      endcase
    end
endmodule''', "One-block style suits an FSMD: each state describes what the "
       "datapath does in that cycle. `in_ready` and `out_valid` are decoded "
       "from state only (Moore).")
    out(["gcd(48,18) = 6  after 9 cycles",
         "gcd(1071,462) = 21  after 16 cycles"],
        "Icarus Verilog output. The latency depends on the data - typical of "
        "iterative FSMDs, and the reason they need a handshake rather than a "
        "fixed pipeline delay.")
    box("intuit", "Controller + datapath is how you should see every block",
        "When you read a specification, separate **what is computed** "
        "(datapath: registers, adders, muxes) from **when it is computed** "
        "(control: an FSM that drives mux selects and register enables). Draw "
        "the datapath first, list its control signals, then write the FSM that "
        "drives them. Chapter 16's DMA engine and Chapter 28's UART are built "
        "exactly this way.")

    h2("FSM pitfalls")
    tbl(["Pitfall", "Symptom", "Fix"],
        [["No default next state", "Latch on `nxt`, or lock-up in an "
          "illegal state", "`nxt = state;` at the top and a `default` item"],
         ["Outputs assigned in only some states of a comb block",
          "Latches on outputs", "Default all outputs at the top of the block"],
         ["Mealy outputs leaving the block", "Long input-to-output paths, "
          "combinational loops between modules", "Register outputs or use "
          "Moore outputs at module boundaries"],
         ["Asynchronous input used directly in next-state logic",
          "Different state bits see different values -> illegal state",
          "Synchronise every asynchronous input first (Chapter 11)"],
         ["Enum ternary like `nxt = din ? S1 : S0;`",
          "Some tools reject it without a cast; readability suffers",
          "Use `if/else` or a cast `state_t'(...)`"],
         ["Relying on enum value order (e.g. `state > S2`)",
          "Breaks when states are added or the tool re-encodes",
          "Compare against named states only"],
         ["Huge monolithic FSM", "Unreviewable, slow next-state logic",
          "Split into hierarchical or communicating FSMs, or use counters "
          "for repetitive sequences"]],
        widths=[28, 34, 38], bold_first=True)

    h2("Summary")
    bul([
        "An FSM is a state register, next-state logic and output logic. Moore "
        "outputs depend on state only; Mealy outputs also on inputs and react "
        "a cycle earlier.",
        "Use an `enum` state type, `nxt = state` defaults, and a `default` "
        "item. Three-block style is clearest; two-block with registered "
        "outputs is the most common in industry.",
        "Binary encoding minimises flops; one-hot minimises logic depth; Gray "
        "minimises toggles; output encoding gives free registered outputs.",
        "Make FSMs safe: illegal states must recover, and the recovery logic "
        "must survive synthesis.",
        "Register outputs that leave the block by computing them from the "
        "next state.",
        "Think of every block as an FSMD: a controller sequencing a datapath.",
    ])
    h2("Exercises")
    bul([
        "Design a Moore detector for the pattern 1101 **without** overlap "
        "and verify it against a reference model with 10000 random bits.",
        "Re-code `seq1011_moore` with explicit one-hot encoding. Count the "
        "flops and write the Boolean equation for each next-state bit.",
        "Add an `error` output to `arb_onehot` that is high when the state "
        "register is not one-hot, and show in simulation (using `force`) that "
        "the FSM recovers from 4'b0110.",
        "Modify `gcd_fsmd` so that it accepts a new input in the same cycle "
        "that it presents a result (i.e. no idle cycle between jobs). What "
        "must be true of the downstream consumer?",
        "Explain why a Mealy output of one module feeding the Mealy input of "
        "another can create a combinational loop, and give a concrete example "
        "using valid/ready signals.",
    ], ordered=True)


# =============================================================================
#                     CHAPTER 8 - DATAPATH AND ARITHMETIC
# =============================================================================
def _ch8():
    chapter("Datapath and Arithmetic")
    p("Datapaths are where the area and the critical paths of most chips "
      "live: adders, multipliers, shifters and the muxes that connect them. "
      "You will rarely hand-build an adder in production RTL - you write `+` "
      "and the synthesis tool picks an architecture from its library of "
      "arithmetic generators. But you must know what those architectures are, "
      "because they explain why `+` costs what it costs, why a 64-bit compare "
      "can fail timing, and why a single missing `signed` keyword can corrupt "
      "an entire ML accelerator's output.")

    h2("Adders: from ripple-carry to parallel prefix")
    p("Every adder computes, for each bit, a **generate** `g = a & b` (this "
      "bit creates a carry) and a **propagate** `p = a ^ b` (this bit passes "
      "an incoming carry on). The sum bit is `p ^ c`. The whole problem of "
      "fast addition is computing all the carries quickly.")
    code(r'''module rca #(parameter int W = 8) (
  input  logic [W-1:0] a, b,
  input  logic         cin,
  output logic [W-1:0] s,
  output logic         cout
);
  logic [W:0] c;
  assign c[0] = cin;
  for (genvar i = 0; i < W; i++) begin : g_fa
    assign s[i]   = a[i] ^ b[i] ^ c[i];
    assign c[i+1] = (a[i] & b[i]) | (c[i] & (a[i] ^ b[i]));
  end
  assign cout = c[W];
endmodule''', "Ripple-carry adder: W full adders in a chain. Smallest possible "
       "adder, but the carry ripples through all W bits - O(W) delay.")
    code(r'''// 4-bit carry-lookahead block: every carry is a 2-level function of g, p, cin
module cla4 (
  input  logic [3:0] a, b,
  input  logic       cin,
  output logic [3:0] s,
  output logic       cout
);
  logic [3:0] g, p;
  logic [4:0] c;
  assign g = a & b;             // generate
  assign p = a ^ b;             // propagate
  assign c[0] = cin;
  assign c[1] = g[0] | (p[0] & cin);
  assign c[2] = g[1] | (p[1] & g[0]) | (p[1] & p[0] & cin);
  assign c[3] = g[2] | (p[2] & g[1]) | (p[2] & p[1] & g[0]) | (p[2] & p[1] & p[0] & cin);
  assign c[4] = g[3] | (p[3] & g[2]) | (p[3] & p[2] & g[1]) | (p[3] & p[2] & p[1] & g[0])
              | (p[3] & p[2] & p[1] & p[0] & cin);
  assign s    = p ^ c[3:0];
  assign cout = c[4];
endmodule''', "Carry-lookahead: carries are flattened into sum-of-products. "
       "The gates grow quickly with width, so real CLAs use 4-bit groups and "
       "a second level of lookahead between groups.")
    code(r'''// Carry-select: compute the upper half twice, pick with the real carry
module csel16 (
  input  logic [15:0] a, b,
  output logic [15:0] s,
  output logic        cout
);
  logic       c8, c_hi0, c_hi1;
  logic [7:0] s_hi0, s_hi1;
  assign {c8, s[7:0]}     = a[7:0]  + b[7:0];
  assign {c_hi0, s_hi0}   = a[15:8] + b[15:8];          // assumes carry-in 0
  assign {c_hi1, s_hi1}   = a[15:8] + b[15:8] + 8'd1;   // assumes carry-in 1
  assign {cout, s[15:8]}  = c8 ? {c_hi1, s_hi1} : {c_hi0, s_hi0};
endmodule''', "Carry-select trades area (the upper half is duplicated) for "
       "delay (the upper half no longer waits for the lower carry). It is the "
       "same speculation idea as the late-select trick of Chapter 5.")
    out(["rca8 + cla4 exhaustive, csel16 random: 0 errors"],
        "Icarus Verilog output: the ripple adder and CLA block were checked "
        "against `+` for all 2^{17} input combinations, the carry-select adder "
        "for 131072 random pairs.")
    p("**Parallel-prefix** adders (Kogge-Stone, Brent-Kung, Sklansky, "
      "Han-Carlson) generalise lookahead. They combine (g, p) pairs with an "
      "associative operator `(g1,p1) o (g0,p0) = (g1 | p1&g0, p1&p0)` in a "
      "tree, giving all carries in log2(W) levels. The variants differ in how "
      "many operator cells they use and how much wiring and fan-out they "
      "tolerate.")
    tbl(["Architecture", "Delay", "Area", "Where it is used"],
        [["Ripple-carry", "O(W)", "Smallest", "Slow paths, small widths, "
          "counters with relaxed timing"],
         ["Carry-lookahead (grouped)", "O(log W)", "Medium", "Textbook; "
          "basis of prefix adders"],
         ["Carry-select", "O(sqrt W) or better", "~1.5-2x ripple",
          "Mid-speed designs; conditional-sum variants"],
         ["Brent-Kung prefix", "2 log2 W", "Small (~2W cells)",
          "Low-power, area-constrained paths"],
         ["Kogge-Stone prefix", "log2 W", "Large (W log W cells), heavy wiring",
          "The fastest adders: CPU ALUs, address generation"],
         ["Carry-save (3:2 compressors)", "O(1) per stage", "One FA per bit",
          "Inside multipliers and multi-operand sums: defers carries"]],
        widths=[24, 18, 24, 34], bold_first=True)
    box("key", "What synthesis does with the + operator",
        "The tool replaces `a + b` with an arithmetic generator (DesignWare in "
        "Synopsys tools, similar libraries elsewhere) and then chooses an "
        "architecture per instance **based on timing**: a ripple adder where "
        "there is slack, a prefix adder where there is not. It also merges "
        "chains like `a + b + c + d` into a carry-save tree with one final "
        "adder. So write arithmetic at the highest level you can - `+`, `-`, "
        "`*` - and let the tool optimise; hand-built adders defeat these "
        "optimisations. Hand-structure only to express something the tool "
        "cannot infer, such as sharing, pipelining or a known-late input.")

    h2("Subtraction, overflow and saturation")
    p("In two's complement, `a - b = a + ~b + 1`: an adder with inverted `b` "
      "and carry-in 1, so subtractors cost the same as adders and an "
      "add/subtract unit costs one XOR per bit extra. The carry-out of an "
      "unsigned subtraction is the inverted borrow, so `a < b` (unsigned) is "
      "just `~cout` of `a - b`.")
    eq(["unsigned overflow (add):  carry out of the MSB = 1",
        "signed overflow (add)  :  operands have the same sign AND the sum's sign differs",
        "                          = c_in(MSB) XOR c_out(MSB)",
        "result width           :  N-bit + N-bit needs N+1 bits;  N x M needs N+M bits"],
       "Overflow rules. Growing the result by one bit and checking whether the "
       "top two bits differ is the easiest way to detect signed overflow in RTL.")
    p("When a result overflows, a datapath can **wrap** (modular arithmetic - "
      "what `+` does by default, correct for addresses, counters and "
      "checksums) or **saturate** (clamp to the most positive or negative "
      "value - required for audio, video, control loops and quantised neural "
      "networks, where a wrap from +max to -max is a catastrophic error).")

    h2("Signed and unsigned: the rules that cause real bugs")
    p("Verilog's expression rules are the source of more silent datapath bugs "
      "than anything else. The two rules to memorise: (1) **if any operand is "
      "unsigned, the whole expression is evaluated unsigned**; (2) operands "
      "are extended to the width of the **context** (including the "
      "left-hand side) before the operation, and signedness decides whether "
      "that extension is sign- or zero-extension.")
    code(r'''module tb_signed_pitfalls;
  logic        [7:0] u8 = 8'd200;
  logic signed [7:0] s8 = -8'sd3;
  logic signed [15:0] r1, r2, r3;
  logic        [3:0] a4 = 4'd9, b4 = 4'd8;
  logic        [3:0] sum4;
  logic        [4:0] sum5;
  initial begin
    // 1. One unsigned operand makes the whole expression unsigned
    r1 = s8 + u8;             // s8 zero-extended: 253 + 200
    r2 = s8 + $signed({1'b0, u8});   // correct: -3 + 200
    $display("s8 + u8          = %0d   (expected 197)", r1);
    $display("s8 + signed(u8)  = %0d", r2);
    // 2. Comparisons follow the same rule
    $display("s8 < 8'd1        = %b     (-3 < 1 ?)", s8 < 8'd1);
    $display("s8 < 8'sd1       = %b", s8 < 8'sd1);
    // 3. Width of the result is set by the LHS context, not the operands
    sum4 = a4 + b4;
    sum5 = a4 + b4;
    $display("4-bit sum = %0d, 5-bit sum = %0d", sum4, sum5);
    // 4. Part-selects are always unsigned, even of a signed vector
    r3 = s8[7:0];
    $display("s8[7:0] into 16b = %0d", r3);
    // 5. >>> is only arithmetic on a signed operand
    $display("s8 >>> 1 = %0d,  u8 >>> 1 = %0d", s8 >>> 1, u8 >>> 1);
  end
endmodule''')
    out(["s8 + u8          = 453   (expected 197)",
         "s8 + signed(u8)  = 197",
         "s8 < 8'd1        = 0     (-3 < 1 ?)",
         "s8 < 8'sd1       = 1",
         "4-bit sum = 1, 5-bit sum = 17",
         "s8[7:0] into 16b = 253",
         "s8 >>> 1 = -2,  u8 >>> 1 = 100"],
        "Icarus Verilog output - every line is standard-conforming behaviour, "
        "and every line has shipped in a real chip as a bug.")
    box("warn", "PITFALL - unsized and unsigned literals",
        "`s8 < 1` is fine (the integer literal 1 is signed), but `s8 < 8'd1` "
        "is unsigned and `s8 < 1'b1` too. Likewise `x + 1'b1` is unsigned. In "
        "signed datapaths use `'sd` literals or `$signed()`, and when you "
        "convert unsigned to signed, prepend a 0 bit first "
        "(`$signed({1'b0, u})`), otherwise values with the MSB set become "
        "negative. Lint tools (Chapter 25) flag mixed-signedness expressions - "
        "enable that rule.")

    h2("Multipliers")
    p("An N x M multiplier forms N x M partial-product bits (AND gates for "
      "unsigned) and sums them. The architectures differ in how the summing is "
      "done:")
    bul([
        "**Array multiplier** - rows of adders, one per partial product. "
        "Regular and easy to lay out, but O(N) adder delays.",
        "**Wallace / Dadda tree** - reduce the partial products with layers "
        "of carry-save adders (3:2 compressors, or 4:2) until two rows remain, "
        "then one fast final adder. O(log N) delay; the standard for "
        "high-speed multipliers.",
        "**Radix-4 (modified) Booth encoding** - recode the multiplier in "
        "digits {-2,-1,0,+1,+2}, halving the number of partial products; "
        "handles signed operands naturally. Almost every production "
        "multiplier combines Booth encoding with a Wallace/Dadda tree.",
        "**Sequential (shift-and-add)** - one partial product per cycle: tiny, "
        "N cycles per result. Used when throughput is irrelevant.",
    ])
    diagram([
        "  a[3:0] x b[3:0]                    Booth radix-4 + Dadda tree (16 x 16):",
        "",
        "          a3b0 a2b0 a1b0 a0b0         16 PPs -> Booth -> 9 PPs",
        "     a3b1 a2b1 a1b1 a0b1              9 -> 6 -> 4 -> 3 -> 2 rows (3:2 / 4:2 CSAs)",
        "  a3b2 a2b2 a1b2 a0b2                 2 rows -> one 32-bit prefix adder",
        " ...                                  levels ~ log base 1.5 of #PPs, + 1 fast add",
        "  sum the columns -> 8-bit product",
    ], "Partial products and the reduction tree. Carry-save reduction is why "
       "a multiplier is only a few times slower than an adder despite being "
       "an order of magnitude larger.")
    box("tip", "Multiplier sizing in practice",
        "A 16 x 16 multiplier is roughly 15-25 times the area of a 16-bit "
        "adder. In ML accelerators the multipliers dominate: an INT8 MAC array "
        "of 1024 units is mostly partial-product logic. That is why "
        "quantisation from FP32 to INT8 or INT4 saves so much silicon - "
        "multiplier area scales roughly with the **product** of operand "
        "widths. Chapter 29 returns to this.")

    h2("Shifters and the barrel shifter")
    p("A shift by a constant is free - it is just wiring. A shift by a "
      "variable amount is a mux network. The **barrel shifter** (strictly, a "
      "logarithmic shifter) uses log2(W) stages; stage k shifts by 2^{k} if "
      "bit k of the amount is set.")
    code(r'''module barrel_rotl #(parameter int W = 32) (
  input  logic [W-1:0]         din,
  input  logic [$clog2(W)-1:0] amt,
  output logic [W-1:0]         dout
);
  // log2(W) stages of 2:1 muxes: stage k rotates by 2^k if amt[k]
  logic [W-1:0] stage [0:$clog2(W)];
  assign stage[0] = din;
  for (genvar k = 0; k < $clog2(W); k++) begin : g_stage
    assign stage[k+1] = amt[k] ? {stage[k][W-1-(1<<k):0], stage[k][W-1 -: (1<<k)]}
                               : stage[k];
  end
  assign dout = stage[$clog2(W)];
endmodule''', "A 32-bit rotator: 5 stages x 32 two-input muxes = 160 muxes. "
       "Writing `din << amt` gives the tool the same structure for a plain "
       "shift.")
    p("Arithmetic right shift (`>>>` on a signed operand) fills with the sign "
      "bit; logical shifts fill with zeros; rotates wrap around. A "
      "general-purpose ALU shifter supports all of them with a little extra "
      "fill logic around the same log-depth network.")

    h2("Division")
    p("Division has no fast, cheap combinational implementation. A "
      "combinational `/` by a non-constant synthesises into W stages of "
      "subtract-and-select - large and very slow - so ASIC RTL either divides "
      "by a constant (which the tool turns into a multiply by the "
      "reciprocal and shifts), divides by a power of two (a shift), or uses "
      "an **iterative** divider that produces one (or, with radix-4 SRT, two) "
      "quotient bits per cycle.")
    code(r'''// Unsigned restoring divider: one quotient bit per clock, W cycles
module div_iter #(parameter int W = 8) (
  input  logic         clk, rst_n,
  input  logic         start,
  input  logic [W-1:0] dividend, divisor,
  output logic         busy, done,
  output logic [W-1:0] quot, rem
);
  logic [W-1:0]         d;          // divisor copy
  logic [W:0]           r;          // partial remainder, one extra bit
  logic [W-1:0]         q;          // shifts in quotient, shifts out dividend
  logic [$clog2(W):0]   n;
  logic [W:0]           r_sh, diff;

  assign r_sh = {r[W-1:0], q[W-1]};        // shift remainder left, bring down bit
  assign diff = r_sh - {1'b0, d};

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      busy <= 1'b0;  done <= 1'b0;
      r <= '0;  q <= '0;  d <= '0;  n <= '0;
    end else begin
      done <= 1'b0;
      if (start && !busy) begin
        busy <= 1'b1;
        r <= '0;  q <= dividend;  d <= divisor;
        n <= ($clog2(W)+1)'(W);
      end else if (busy) begin
        if (diff[W]) begin                  // negative: restore
          r <= r_sh;  q <= {q[W-2:0], 1'b0};
        end else begin
          r <= diff;  q <= {q[W-2:0], 1'b1};
        end
        n <= n - 1'b1;
        if (n == 1) begin busy <= 1'b0;  done <= 1'b1; end
      end
    end

  assign quot = q;
  assign rem  = r[W-1:0];
endmodule''', "The dividend shifts out of `q` as quotient bits shift in, so "
       "one register serves both. A single W+1-bit subtractor is reused W "
       "times.")
    out(["200 / 7 = 28 rem 4  (9 cycles)",
         "divider: 500 random divisions, 0 errors",
         "barrel rotator: 1000 random vectors, 0 errors"],
        "Icarus Verilog output. The testbench compares against the "
        "simulator's `/` and `%` and a reference rotate. Division by zero "
        "returns quotient all-ones and remainder = dividend; a real design "
        "must define and document that case.")

    h2("Fixed-point arithmetic and Q formats")
    p("Most signal-processing and ML inference hardware uses **fixed-point** "
      "numbers: integers with an implied binary point. The notation "
      "**Qm.n** means m integer bits (including the sign) and n fraction bits; "
      "the value is the integer divided by 2^{n}. Q1.15 (16-bit, range "
      "[-1, 1 - 2^{-15}]) is the classic DSP format; INT8 with a per-tensor "
      "scale is its modern ML cousin.")
    tbl(["Operation", "Rule", "Example"],
        [["Add / subtract", "Align binary points first; result Q(m+1).n",
          "Q1.15 + Q1.15 -> Q2.15 (17 bits)"],
         ["Multiply", "Integer bits add, fraction bits add",
          "Q1.15 x Q1.15 -> Q2.30 (32 bits)"],
         ["Back to Q1.15", "Drop n fraction bits (with rounding), then "
          "saturate the extra integer bit", "Q2.30 >> 15 -> Q2.15 -> sat -> "
          "Q1.15"],
         ["Accumulate K products", "Add ceil(log2 K) guard bits",
          "1024 Q2.30 products need a 42-bit accumulator"]],
        widths=[20, 44, 36], bold_first=True)
    tbl(["Rounding mode", "RTL", "Bias", "Cost"],
        [["Truncate (floor)", "drop the bits", "-0.5 LSB on average "
          "(accumulates!)", "Free"],
         ["Round half up", "add 2^{k-1}, then drop k bits", "Tiny positive "
          "bias at exact halves", "One adder"],
         ["Round half to even (convergent)", "as above, but ties go to the "
          "even value", "Unbiased", "Adder + tie detection"],
         ["Round toward zero", "truncate magnitude", "Toward zero",
          "Sign-dependent add"]],
        widths=[26, 30, 26, 18], bold_first=True)
    code(r'''// Q1.15 x Q1.15 -> Q1.15 with round-half-up and saturation
module q15_mul (
  input  logic signed [15:0] a, b,
  output logic signed [15:0] y
);
  logic signed [31:0] p;        // Q2.30
  logic signed [32:0] pr;       // + rounding constant, one guard bit
  logic signed [17:0] t;        // Q2.30 >> 15 -> Q3.15 candidate
  assign p  = a * b;
  assign pr = p + 33'sd16384;   // add half an LSB of the result (2^14)
  assign t  = pr[32:15];        // drop 15 fraction bits
  always_comb begin
    if      (t >  18'sd32767)  y = 16'sh7FFF;   // only -1 x -1 overflows
    else if (t < -18'sd32768)  y = 16'sh8000;
    else                       y = 16'(t);
  end
endmodule''')
    out([" 0.50000 x  0.50000 =  0.25000  (0x2000)",
         "-0.50000 x  0.50000 = -0.25000  (0xe000)",
         "-1.00000 x -1.00000 =  0.99997  (0x7fff)",
         " 0.00003 x  0.50000 =  0.00003  (0x0001)",
         " 0.99997 x  0.99997 =  0.99994  (0x7ffe)"],
        "Icarus Verilog output. The only Q1.15 product that overflows is "
        "(-1) x (-1) = +1, which saturates to 0x7FFF. 1 LSB x 0.5 = 0.5 LSB "
        "rounds up to 1 LSB rather than truncating to zero.")
    box("warn", "PITFALL - truncation bias in accumulators",
        "Truncation always rounds toward minus infinity, so the error of each "
        "operation averages -0.5 LSB. In a filter or a neural network layer "
        "that sums thousands of truncated products, the bias adds up to a "
        "visible DC offset or an accuracy drop. Keep full precision inside the "
        "accumulator and round **once**, at the output.")

    h2("Resource sharing")
    p("If two operations are never needed in the same cycle, one operator can "
      "serve both behind muxes. Synthesis does this automatically within a "
      "single `always` block when the operations are in mutually exclusive "
      "branches; you can also do it explicitly.")
    code(r'''// Unshared: two adders feeding one mux
assign y_unshared = sel ? a + b : c + d;
// Shared: two muxes feeding one adder
assign y_shared   = (sel ? a : c) + (sel ? b : d);''',
         "Sharing saves an adder but adds muxes before it, lengthening the "
         "path through the select. Worth it for multipliers and dividers, "
         "rarely for small adders.")

    h2("A verified saturating MAC")
    p("The multiply-accumulate (MAC) is the atom of DSP and of neural-network "
      "inference: acc = acc + a x b, repeated over a dot product. The version "
      "below uses signed operands, a guard bit to detect overflow, "
      "saturation, and a sticky flag that software can read (Chapter 15) to "
      "learn that clipping occurred.")
    code(r'''// Signed saturating multiply-accumulate: acc <= sat(acc + a*b)
module sat_mac #(
  parameter int DW = 8,               // operand width (signed)
  parameter int AW = 20               // accumulator width (signed)
) (
  input  logic                 clk, rst_n,
  input  logic                 clr,    // synchronous clear of the accumulator
  input  logic                 en,     // accumulate this cycle
  input  logic signed [DW-1:0] a, b,
  output logic signed [AW-1:0] acc,
  output logic                 sat     // sticky: saturation has occurred
);
  localparam logic signed [AW-1:0] MAXV = {1'b0, {(AW-1){1'b1}}};
  localparam logic signed [AW-1:0] MINV = {1'b1, {(AW-1){1'b0}}};

  logic signed [2*DW-1:0] prod;
  logic signed [AW:0]     sum;        // one guard bit catches overflow

  assign prod = a * b;                // both operands signed -> signed multiply
  assign sum  = acc + prod;           // sign-extended to AW+1 bits

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      acc <= '0;
      sat <= 1'b0;
    end else if (clr) begin
      acc <= '0;
      sat <= 1'b0;
    end else if (en) begin
      // overflow iff the two top bits of the (AW+1)-bit sum differ
      if (sum[AW] != sum[AW-1]) begin
        acc <= sum[AW] ? MINV : MAXV;
        sat <= 1'b1;
      end else begin
        acc <= sum[AW-1:0];
      end
    end
endmodule''', "One guard bit is enough because |prod| < 2^{AW-1} whenever "
       "AW >= 2 DW, so a single addition can overshoot the range by less than "
       "a factor of two.")
    code(r'''module tb_sat_mac;
  localparam int DW = 8, AW = 16;
  logic clk = 0, rst_n = 0, clr = 0, en = 0, sat;
  logic signed [DW-1:0] a, b;
  logic signed [AW-1:0] acc;
  longint model;
  int errors = 0;
  always #5 clk = ~clk;
  sat_mac #(DW, AW) dut (.*);

  task automatic step(input logic signed [DW-1:0] x, y);
    @(negedge clk) begin a = x; b = y; en = 1; end
    model = model + x * y;
    if (model >  32767) model =  32767;
    if (model < -32768) model = -32768;
    @(negedge clk) en = 0;
    if (acc !== model) errors++;
  endtask

  initial begin
    model = 0;
    repeat (2) @(negedge clk);
    rst_n = 1;
    step(100, 100);  $display("acc=%6d sat=%b", acc, sat);
    step(127, 127);  $display("acc=%6d sat=%b", acc, sat);
    step(127, 127);  $display("acc=%6d sat=%b  <- clipped at +max", acc, sat);
    step(-128, 127); $display("acc=%6d sat=%b  <- recovers from the rail", acc, sat);
    @(negedge clk) clr = 1;  @(negedge clk) clr = 0;  model = 0;
    for (int i = 0; i < 2000; i++) step($urandom, $urandom);
    $display("2000 random MACs vs model: %0d errors, final acc=%0d sat=%b",
             errors, acc, sat);
    $finish;
  end
endmodule''', "A 16-bit accumulator is deliberately small so that saturation "
       "happens often. The model saturates after every step, exactly like "
       "the hardware.")
    out(["acc= 10000 sat=0",
         "acc= 26129 sat=0",
         "acc= 32767 sat=1  <- clipped at +max",
         "acc= 16511 sat=1  <- recovers from the rail",
         "2000 random MACs vs model: 0 errors, final acc=-23003 sat=1"],
        "Icarus Verilog output. 26129 + 16129 = 42258 exceeds 32767 and "
        "clips; the next product (-16256) is applied to the clipped value, "
        "giving 16511. The random run exercises both rails.")
    box("expert", "Interview insight: saturate every step or only at the end?",
        "Saturating arithmetic is **not associative**: (MAX + 1) - 1 gives "
        "MAX - 1 with per-step saturation but MAX with a wide accumulator. "
        "Most ML accelerators therefore accumulate in a wide register (e.g. "
        "32 bits for INT8 x INT8 over thousands of terms) that cannot "
        "overflow, and saturate only once when requantising the result. "
        "Per-step saturation, as above, matches DSP instruction semantics "
        "(e.g. saturating MAC instructions) where bit-exactness with a "
        "software model is required.")

    h2("Summary")
    bul([
        "Adders compute generate/propagate and then carries; ripple is small "
        "and slow, prefix adders are fast and large. Synthesis picks the "
        "architecture per instance from timing - write `+`.",
        "Signed overflow = top two bits of a one-bit-wider result differ. "
        "Choose wrap or saturate deliberately.",
        "One unsigned operand makes the whole expression unsigned; context "
        "width and signedness determine extension. Part-selects are unsigned.",
        "Multipliers = partial products + carry-save tree + final adder; "
        "Booth halves the partial products. Area scales with the product of "
        "widths.",
        "Variable shifts are log-depth mux networks; division is iterative.",
        "Track Q formats through every operation, round once, and size "
        "accumulators with guard bits.",
    ])
    h2("Exercises")
    bul([
        "Write a parameterised 16-bit Kogge-Stone adder using a generate loop "
        "for the prefix tree and verify it against `+` with random vectors.",
        "Extend `barrel_rotl` into a full shifter supporting logical left, "
        "logical right and arithmetic right shifts, with a 2-bit `op` input.",
        "Modify `sat_mac` to use round-half-to-even when producing a Q8 "
        "output from the accumulator. Verify ties explicitly.",
        "Make `div_iter` handle signed operands (divide magnitudes, then fix "
        "the signs, with the remainder taking the sign of the dividend). Test "
        "all four sign combinations.",
        "An expression `y = a * b + c` has 8-bit unsigned `a`, `b`, a signed "
        "16-bit `c` and a signed 17-bit `y`. What does Verilog actually "
        "compute? Rewrite it so that the result is correct and prove it in "
        "simulation.",
    ], ordered=True)


# =============================================================================
#          CHAPTER 9 - MEMORIES, REGISTER FILES AND SYNCHRONOUS FIFOS
# =============================================================================
def _ch9():
    chapter("Memories, Register Files and Synchronous FIFOs")
    p("On a modern SoC, embedded memory often occupies half of the die area. "
      "Caches, scratchpads, frame buffers, packet buffers, weight and "
      "activation buffers in ML accelerators - all are SRAM. Small, "
      "many-ported storage is built from flops as a register file. Between "
      "producers and consumers sit FIFOs. This chapter covers how each is "
      "described in RTL, what physical structure it becomes, and how to build "
      "a FIFO that is correct at the full and empty boundaries - the corner "
      "cases where most FIFO bugs live.")

    h2("Flop-based register files")
    p("A register file is an array of registers with a small number of read "
      "and write ports. Built from flops, each **write port** costs a decoder "
      "plus an enable per word, and each **read port** costs a full N:1 "
      "multiplexer of the whole array. Read ports are therefore the expensive "
      "part: a 32 x 32 register file with two read ports contains two 32-bit "
      "32:1 muxes - about 2 x 31 x 32 = 1984 2:1 mux equivalents.")
    code(r'''// 2-read / 1-write flop-based register file, x0 hard-wired to zero (RISC-V style)
module regfile_2r1w #(parameter int W = 32, N = 32, localparam int AW = $clog2(N)) (
  input  logic          clk,
  input  logic          we,
  input  logic [AW-1:0] waddr, raddr1, raddr2,
  input  logic [W-1:0]  wdata,
  output logic [W-1:0]  rdata1, rdata2
);
  logic [W-1:0] mem [N];
  always_ff @(posedge clk)
    if (we && waddr != '0) mem[waddr] <= wdata;
  // asynchronous (combinational) reads: a big mux per port
  assign rdata1 = (raddr1 == '0) ? '0 : mem[raddr1];
  assign rdata2 = (raddr2 == '0) ? '0 : mem[raddr2];
endmodule''', "No reset on the array: software never reads a register it has "
       "not written (and x0 is constant). Resetting 1024 flops would cost "
       "area and reset-tree load for nothing.")
    diagram([
        "  waddr --[decoder]--> we[0..31]   (one load enable per register)",
        "                          |",
        "  wdata --------+-----> [reg 0 ]--+",
        "                +-----> [reg 1 ]--+== all 32 words ==+==> [32:1 mux] --> rdata1",
        "                +-----> [ .... ]--+                  |         ^ raddr1",
        "                +-----> [reg 31]--+                  +==> [32:1 mux] --> rdata2",
        "                                                               ^ raddr2",
        "",
        "  cost ~ N x W flops + (write ports x N enables) + (read ports x W x (N-1) mux2)",
    ], "Structure of a flop-based register file. Adding a read port adds a "
       "whole mux tree; adding a write port adds a mux in front of every flop.")
    p("Multi-port register files are needed by superscalar CPUs (e.g. 6 read, "
      "3 write ports) and by some accelerators. Beyond two or three ports, "
      "flop-based implementations explode in area and wiring; designers then "
      "use custom multi-port SRAM bit-cells, **banking** (split registers into "
      "banks and arbitrate conflicts), or **replication** (two copies of a "
      "1-read file give 2 read ports, at the price of writing both).")
    box("tip", "Write-before-read bypass",
        "If a pipeline writes register r and reads it in the same cycle, "
        "the combinational-read file above returns the **old** value. CPUs "
        "add a bypass mux: `rdata1 = (we && waddr == raddr1) ? wdata : "
        "mem[raddr1]`. Whether you need it is an architectural decision, not "
        "a coding one - write it down in the specification.")

    h2("SRAM macros versus inferred memory")
    p("Above a few hundred bits, flops become far too large: a 6-transistor "
      "SRAM bit-cell is roughly 5-10 times smaller than a flop-based bit "
      "with its mux share. ASIC memories are therefore **hard macros** "
      "produced by a **memory compiler** from the foundry or an IP vendor. "
      "You give the compiler words, bits, number of ports, mux factor, and "
      "options (byte write, redundancy, power gating, BIST interface), and it "
      "generates the layout, a timing model (.lib), an abstract (LEF), and a "
      "Verilog behavioural model.")
    tbl(["", "FPGA", "ASIC"],
        [["How RAM is obtained", "Inferred from RTL templates into block RAM "
          "(BRAM/URAM) or LUT RAM", "Instantiated hard macros from a memory "
          "compiler; synthesis does **not** infer SRAM"],
         ["Portability trick", "Coding templates the tool recognises",
          "A **wrapper** module: behavioural model for simulation and FPGA, "
          "macro instance for the ASIC, chosen by a define or generate"],
         ["Read latency", "Synchronous read (1 cycle), optional output register",
          "Synchronous read; clock-to-Q of the macro is a large part of the "
          "cycle"],
         ["Test", "Not required", "Memory BIST, repair with redundant rows or "
          "columns (Chapter 20)"],
         ["Low power", "Little control", "Light sleep, deep sleep, shut-down "
          "pins; retention (Chapter 19)"]],
        widths=[20, 36, 44], bold_first=True)
    box("key", "Always wrap your memories",
        "Never instantiate a vendor SRAM macro directly throughout your RTL. "
        "Create one wrapper per memory type (e.g. `sp_ram_1024x32`) with a "
        "clean, technology-neutral interface. Inside it, select the macro for "
        "the ASIC, an inferred template for the FPGA prototype (Chapter 26), and "
        "a behavioural array for simulation. The wrapper is also where BIST "
        "muxes, ECC, and power-control pins are hidden from the functional "
        "logic.")

    h2("Single-port and dual-port RAMs, and read-during-write")
    tbl(["Type", "Ports", "Typical use"],
        [["Single-port (1RW)", "One address; read OR write each cycle",
          "Scratchpads, buffers that are filled then drained"],
         ["Simple dual-port (1R1W)", "One write port + one read port",
          "FIFOs, line buffers - the most common in datapaths"],
         ["True dual-port (2RW)", "Two independent ports, each read or write",
          "Shared memories, ping-pong buffers; larger bit-cell"],
         ["Two-port register file (macro)", "1R1W, small and fast",
          "Small high-bandwidth buffers"]],
        widths=[26, 36, 38], bold_first=True)
    p("When a read and a write hit the same address in the same cycle, the "
      "memory returns one of three things: the **old** data (read-first), the "
      "**new** data (write-first / write-through), or undefined data. Which "
      "one is a property of the macro and must match your RTL model exactly - "
      "otherwise RTL simulation and silicon disagree.")
    code(r'''// Single-port RAM, synchronous read, read-first (old data on a write)
module spram_rf #(parameter int W = 32, D = 1024, localparam int AW = $clog2(D)) (
  input  logic          clk, en, we,
  input  logic [AW-1:0] addr,
  input  logic [W-1:0]  wdata,
  output logic [W-1:0]  rdata
);
  logic [W-1:0] mem [D];
  always_ff @(posedge clk)
    if (en) begin
      if (we) mem[addr] <= wdata;
      rdata <= mem[addr];               // reads the value BEFORE this write
    end
endmodule''', "Because both assignments are non-blocking, `rdata` samples "
       "`mem[addr]` before the write lands: read-first behaviour.")
    code(r'''// Simple dual-port RAM with byte enables: one write port, one read port
module sdpram_be #(parameter int W = 32, D = 256, localparam int AW = $clog2(D)) (
  input  logic           clk,
  input  logic           we,
  input  logic [W/8-1:0] be,
  input  logic [AW-1:0]  waddr, raddr,
  input  logic [W-1:0]   wdata,
  input  logic           re,
  output logic [W-1:0]   rdata
);
  logic [W-1:0] mem [D];
  always_ff @(posedge clk) begin
    if (we)
      for (int i = 0; i < W/8; i++)
        if (be[i]) mem[waddr][8*i +: 8] <= wdata[8*i +: 8];
    if (re) rdata <= mem[raddr];
  end
endmodule''', "Byte enables let a 32-bit bus perform 8- and 16-bit stores "
       "without a read-modify-write - required behind AXI `WSTRB` and AHB "
       "`HSIZE` (Chapter 13).")
    out(["read during write of BBBB0002: rdata = aaaa0001 (old data)",
         "next plain read            : rdata = bbbb0002",
         "byte enables 0101 over 11223344 -> 11ff33ff"],
        "Icarus Verilog output: a second write to the same address returns "
        "the old word; byte enables 0101 overwrite only bytes 0 and 2.")

    h2("Parity and ECC basics")
    p("SRAM bits can flip - from alpha particles, neutrons or marginal "
      "voltage. Large memories are protected with codes stored alongside the "
      "data:")
    tbl(["Scheme", "Extra bits (64-bit word)", "Capability", "Where"],
        [["Parity", "1 (or 1 per byte = 8)", "Detects any odd number of flipped "
          "bits; no correction", "Caches that can refetch clean data, "
          "instruction RAMs, buses"],
         ["SECDED Hamming", "8", "Corrects 1-bit errors, detects 2-bit "
          "errors", "Main SoC SRAMs, DRAM controllers, automotive"],
         ["DECTED / BCH", "~15", "Corrects 2, detects 3", "High-reliability "
          "and advanced-node memories"]],
        widths=[18, 22, 32, 28], bold_first=True)
    p("RTL impact: the encoder is an XOR tree on the write path, the decoder "
      "an XOR tree (syndrome) plus a correction mux on the read path - often a "
      "full pipeline stage. Byte writes into an ECC-protected word require a "
      "**read-modify-write**, because the check bits cover the whole word. "
      "Corrected errors are counted and reported through status registers and "
      "interrupts (Chapter 15); a background **scrubber** reads and rewrites "
      "memory periodically so single errors are fixed before a second one "
      "accumulates in the same word.")

    h2("The synchronous FIFO")
    p("A FIFO decouples a producer from a consumer that run on the same clock "
      "but not in lock-step. It is a circular buffer: a write pointer, a read "
      "pointer and a dual-port memory. The only hard part is telling **full** "
      "from **empty**, because in both cases the pointers are equal.")
    diagram([
        "   DEPTH = 8, pointers have 3 index bits + 1 lap bit",
        "",
        "   empty:   wptr = 0_101   rptr = 0_101   same index, same lap      -> empty",
        "   full :   wptr = 1_101   rptr = 0_101   same index, different lap -> full",
        "   count = wptr - rptr  (mod 16)  -> 0..8, no ambiguity",
        "",
        "      +---+---+---+---+---+---+---+---+",
        "      | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |   write at mem[wptr[2:0]]",
        "      +---+---+---+---+---+---+---+---+   read  at mem[rptr[2:0]]",
        "                    ^rptr       ^wptr     count = 3",
    ], "The extra-bit trick: one more pointer bit than the address needs "
       "distinguishes 'writer has lapped the reader' (full) from 'caught up' "
       "(empty).")
    p("Alternative schemes exist - a separate occupancy counter, or a "
      "registered `full`/`empty` flag pair updated from the next-state "
      "pointers - and are sometimes preferred for timing or for "
      "non-power-of-two depths. The extra-bit scheme is the most common and "
      "is also the basis of the **asynchronous** FIFO in Chapter 11, where the "
      "pointers are Gray-coded before crossing clock domains.")
    code(r'''// Synchronous FIFO, standard (non-FWFT) read: rdata valid the cycle AFTER rd_en.
// DEPTH must be a power of two. Pointers carry one extra wrap bit.
module sync_fifo #(
  parameter int W = 8,
  parameter int DEPTH = 8,
  parameter int AF_LEVEL = DEPTH - 2,        // almost-full threshold
  localparam int AW = $clog2(DEPTH)
) (
  input  logic         clk, rst_n,
  input  logic         wr_en,
  input  logic [W-1:0] wdata,
  input  logic         rd_en,
  output logic [W-1:0] rdata,
  output logic         full, empty, almost_full,
  output logic [AW:0]  count
);
  logic [W-1:0] mem [DEPTH];
  logic [AW:0]  wptr, rptr;                  // AW+1 bits: MSB is the lap bit
  logic         do_wr, do_rd;

  assign do_wr = wr_en && !full;             // overflow-protected
  assign do_rd = rd_en && !empty;            // underflow-protected

  always_ff @(posedge clk)
    if (do_wr) mem[wptr[AW-1:0]] <= wdata;   // storage: no reset needed

  always_ff @(posedge clk)
    if (do_rd) rdata <= mem[rptr[AW-1:0]];

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      wptr <= '0;
      rptr <= '0;
    end else begin
      if (do_wr) wptr <= wptr + 1'b1;
      if (do_rd) rptr <= rptr + 1'b1;
    end

  // same index + same lap -> empty; same index + different lap -> full
  assign count       = wptr - rptr;
  assign empty       = (wptr == rptr);
  assign full        = (wptr == {~rptr[AW], rptr[AW-1:0]});
  assign almost_full = (count >= (AW+1)'(AF_LEVEL));
endmodule''', "Flags are combinational decodes of registered pointers - "
       "glitch-free enough for synchronous logic and only a comparator deep.")
    p("Note the design decisions: writes when full and reads when empty are "
      "**ignored** rather than corrupting the pointers (many designs instead "
      "flag them as errors or assert on them); the memory has no reset; and "
      "`almost_full` gives an upstream block with a pipeline of latency L "
      "enough warning to stop in time - set `AF_LEVEL = DEPTH - L`.")
    code(r'''module tb_fifo;
  localparam int W = 8, DEPTH = 8;
  logic clk = 0, rst_n = 0, wr_en = 0, rd_en = 0;
  logic [W-1:0] wdata, rdata;
  logic full, empty, almost_full;
  logic [3:0] count;
  logic [W-1:0] q[$];                        // reference model
  logic [W-1:0] exp_data;
  logic check = 0;
  int errors = 0, n_rd = 0;
  always #5 clk = ~clk;
  sync_fifo #(.W(W), .DEPTH(DEPTH)) dut (.*);

  // scoreboard: compare rdata one cycle after an accepted read
  always @(posedge clk) begin
    if (check) begin
      if (rdata !== exp_data) errors++;
      n_rd++;
    end
    check = 0;
    if (rd_en && !empty) begin exp_data = q.pop_front(); check = 1; end
    if (wr_en && !full) q.push_back(wdata);
  end

  initial begin
    repeat (2) @(negedge clk);
    rst_n = 1;
    // fill completely, then try one extra write
    for (int i = 0; i < DEPTH + 1; i++) begin
      wr_en = 1;  wdata = 8'hA0 + i[7:0];
      @(negedge clk);
      $display("wr %h  count=%0d full=%b afull=%b empty=%b",
               wdata, count, full, almost_full, empty);
    end
    wr_en = 0;
    // one read from the full FIFO: data appears the cycle after rd_en
    rd_en = 1;  @(negedge clk);  rd_en = 0;
    $display("rd -> rdata=%h  count=%0d full=%b", rdata, count, full);
    // random traffic
    for (int i = 0; i < 5000; i++) begin
      wr_en = $urandom_range(0, 1);  rd_en = $urandom_range(0, 1);
      wdata = $urandom;
      @(negedge clk);
      if (count !== q.size()) errors++;
    end
    wr_en = 0;  rd_en = 0;  @(negedge clk);
    $display("random: %0d reads checked, %0d errors", n_rd, errors);
    $finish;
  end
endmodule''', "A queue (`q[$]`) is the reference model; the scoreboard "
       "checks every read's data and every cycle's `count`.")
    out(["wr a0  count=1 full=0 afull=0 empty=0",
         "wr a1  count=2 full=0 afull=0 empty=0",
         "wr a2  count=3 full=0 afull=0 empty=0",
         "wr a3  count=4 full=0 afull=0 empty=0",
         "wr a4  count=5 full=0 afull=0 empty=0",
         "wr a5  count=6 full=0 afull=1 empty=0",
         "wr a6  count=7 full=0 afull=1 empty=0",
         "wr a7  count=8 full=1 afull=1 empty=0",
         "wr a8  count=8 full=1 afull=1 empty=0",
         "rd -> rdata=a0  count=7 full=0",
         "random: 2344 reads checked, 0 errors"],
        "Icarus Verilog output. The ninth write (a8) is dropped because the "
        "FIFO is full; the first read returns a0; 5000 cycles of random "
        "traffic produce no mismatches.")
    box("warn", "PITFALL - FIFO bugs live at the boundaries",
        "Classic FIFO bugs: simultaneous read and write when **empty** (a "
        "standard FIFO cannot return the word being written this cycle) or "
        "when **full** (is the write allowed because a slot is freed? in this "
        "design, no - `full` blocks it); pointer width off by one so full and "
        "empty alias; non-power-of-two depth with the extra-bit scheme (the "
        "pointers must then wrap explicitly at DEPTH, and the lap bit toggles "
        "on wrap); and flags derived from `count` with a different latency "
        "from the data. A random testbench with a queue model, run long "
        "enough to hit full and empty many times, finds all of them.")

    h2("Standard versus first-word-fall-through (FWFT)")
    p("In a **standard** FIFO, `rd_en` is a request and the data appears one "
      "cycle later. In a **first-word-fall-through** (show-ahead) FIFO, the "
      "head word is already on `rdata` whenever the FIFO is not empty, and a "
      "read (`pop`) acknowledges it. FWFT maps directly onto a valid/ready "
      "interface (`valid = !empty`, `pop = valid && ready`), which is why "
      "streaming designs prefer it (Chapter 10).")
    code(r'''// FWFT (show-ahead) FIFO: the head word is visible on rdata whenever !empty.
// Uses an asynchronous-read flop array; a 'pop' consumes the current word.
module fwft_fifo #(parameter int W = 8, DEPTH = 4, localparam int AW = $clog2(DEPTH)) (
  input  logic         clk, rst_n,
  input  logic         push,
  input  logic [W-1:0] wdata,
  input  logic         pop,
  output logic [W-1:0] rdata,
  output logic         full, empty
);
  logic [W-1:0] mem [DEPTH];
  logic [AW:0]  wptr, rptr;
  always_ff @(posedge clk)
    if (push && !full) mem[wptr[AW-1:0]] <= wdata;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      wptr <= '0;  rptr <= '0;
    end else begin
      if (push && !full) wptr <= wptr + 1'b1;
      if (pop && !empty) rptr <= rptr + 1'b1;
    end
  assign rdata = mem[rptr[AW-1:0]];          // head of queue, no read latency
  assign empty = (wptr == rptr);
  assign full  = (wptr == {~rptr[AW], rptr[AW-1:0]});
endmodule''')
    out(["empty=0 head=11   (visible before any pop)",
         "empty=0 head=22   (after one pop)",
         "empty=1"],
        "Icarus Verilog output: two pushes, then the head is visible without a "
        "read request.")
    p("With a flop array, FWFT is free. With an SRAM macro (synchronous "
      "read), FWFT needs a small **prefetch** stage: one or two output "
      "registers that are refilled from the SRAM whenever they are empty - "
      "effectively a standard FIFO followed by a skid buffer, which is the "
      "subject of the next chapter.")

    h2("Content-addressable memory (CAM), briefly")
    p("A CAM is searched by content rather than address: present a key, and "
      "every entry compares it in parallel, returning a hit and the matching "
      "index. CAMs implement TLBs, cache tag lookups in fully associative "
      "caches, network routing tables (TCAMs, with don't-care bits) and "
      "outstanding-transaction tables in bus interfaces. A small CAM in RTL "
      "is an array of registers, one equality comparator per entry, and a "
      "priority or one-hot encoder (Chapter 5) on the match vector. The "
      "parallel compare makes CAMs power-hungry and large; above a few dozen "
      "entries they are custom macros.")

    h2("Summary")
    bul([
        "Flop register files cost a mux tree per read port and an enable per "
        "word per write port; beyond a few ports use banking, replication or "
        "custom macros.",
        "ASIC SRAMs are compiled macros, not inferred - always hide them "
        "behind a technology-neutral wrapper.",
        "Know and model the read-during-write behaviour of each memory; use "
        "byte enables for sub-word writes.",
        "Parity detects, SECDED corrects single-bit errors; ECC forces "
        "read-modify-write for partial writes.",
        "A synchronous FIFO uses pointers with one extra lap bit: equal = "
        "empty, equal except the MSB = full, difference = count.",
        "Standard FIFOs return data a cycle after `rd_en`; FWFT FIFOs present "
        "the head word and fit valid/ready directly.",
    ])
    h2("Exercises")
    bul([
        "Add a write-to-read bypass to `regfile_2r1w` and write a test that "
        "reads and writes the same register in one cycle.",
        "Rewrite `sync_fifo` for DEPTH = 6 (not a power of two). Keep the "
        "lap-bit idea but wrap the index explicitly. Rerun the random "
        "testbench.",
        "Add registered `full` and `empty` flags computed from the next-state "
        "pointers, and prove with the testbench that they match the "
        "combinational versions every cycle.",
        "Design an 8-entry CAM with 16-bit keys, a write port and a search "
        "port returning `hit` and a 3-bit index (lowest matching entry wins).",
        "A memory compiler offers a 1024 x 64 macro with read-first or "
        "write-first behaviour. Write the behavioural model for write-first "
        "and a testbench that distinguishes the two.",
    ], ordered=True)


# =============================================================================
#     CHAPTER 10 - PIPELINING, VALID/READY HANDSHAKES AND FLOW CONTROL
# =============================================================================
def _ch10():
    chapter("Pipelining, Valid/Ready Handshakes and Flow Control")
    p("A modern SoC is a network of blocks streaming data to each other: a "
      "camera interface feeding an ISP, a DMA feeding an accelerator, an "
      "accelerator feeding a memory controller. Each block is pipelined to "
      "reach its clock frequency, and each link between blocks must cope with "
      "the receiver sometimes being unable to accept data. This chapter "
      "develops the two ideas that make this work - **pipelining** and "
      "**flow control** - and the precise rules of the valid/ready handshake "
      "that AXI-Stream, AXI and nearly every internal interface are built on.")

    h2("Latency versus throughput")
    p("**Latency** is how many cycles a single item takes to pass through a "
      "block. **Throughput** is how many items the block completes per cycle "
      "(or per second). Pipelining cuts a long combinational path into S "
      "stages separated by registers: each stage is shorter, so the clock can "
      "be faster, and S items are in flight at once.")
    eq(["f_max    ~  1 / (t_logic / S + t_clk->q + t_setup + t_skew)",
        "latency  =  S cycles  =  S / f_max seconds  (slightly MORE time than unpipelined)",
        "throughput = 1 item per cycle when full  (S x more items per second, ideally)",
        "time for N items = (S - 1 + N) cycles"],
       "Pipelining buys throughput with latency and flops. The fixed per-stage "
       "overhead (flop delay, setup, clock skew) is why doubling the stages "
       "never quite doubles the frequency.")
    box("intuit", "The laundry analogy is exactly right",
        "Washer, dryer, folding: one load takes three hours regardless. But if "
        "you start the next load in the washer as soon as the first moves to "
        "the dryer, you finish a load every hour. The slowest stage sets the "
        "rate - which is why balancing pipeline stages (Chapter 6's retiming) "
        "matters.")

    h2("Pipeline registers and valid bits")
    p("The simplest pipeline has no backpressure: data enters every cycle it "
      "is valid, and a **valid bit** travels alongside the data through each "
      "stage. Only the valid bits need a reset; the data registers are "
      "enabled by valid, which prevents useless toggling and lets the power "
      "tool gate their clocks (Chapter 19).")
    code(r'''// y = a*b + c, 3-stage pipeline, valid travels with the data (no backpressure)
module mac_pipe (
  input  logic               clk, rst_n,
  input  logic               in_valid,
  input  logic signed [15:0] a, b,
  input  logic signed [31:0] c,
  output logic               out_valid,
  output logic signed [31:0] y
);
  logic               v1, v2;
  logic signed [15:0] a1, b1;
  logic signed [31:0] c1, c2, p2;
  // valid pipeline: the only part that needs a reset
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) {v1, v2, out_valid} <= '0;
    else        {v1, v2, out_valid} <= {in_valid, v1, v2};
  // data pipeline: no reset, enabled by valid to save power
  always_ff @(posedge clk) begin
    if (in_valid) begin a1 <= a;       b1 <= b;  c1 <= c;  end   // S1: register inputs
    if (v1)       begin p2 <= a1 * b1; c2 <= c1;           end   // S2: multiply
    if (v2)             y  <= p2 + c2;                           // S3: add
  end
endmodule''', "Note that `c` must be delayed through the pipeline too "
       "(`c1`, `c2`) so that it meets the product of the **same** item - "
       "forgetting to delay a side input is the most common pipelining bug.")
    out(["issue i=1 at t=30",
         "issue i=2 at t=40",
         "issue i=3 at t=50",
         "  result at t=60  y=-99",
         "  result at t=70  y=-198",
         "  result at t=80  y=-297"],
        "Icarus Verilog output (a = i, b = -100, c = i). Three items issued "
        "on consecutive cycles emerge three cycles later on consecutive "
        "cycles: latency 3, throughput 1 per cycle.")

    h2("Hazards in datapath pipelines")
    p("A pipeline is correct only if every item sees the right operands. "
      "Three kinds of hazard break this:")
    tbl(["Hazard", "Cause", "Datapath example", "Remedies"],
        [["Data (RAW)", "An item needs a result that a later stage has not "
          "produced yet", "Accumulator feedback: acc + x needs last cycle's "
          "acc, but the adder is 2 stages deep", "Forwarding/bypass muxes; "
          "stall; interleave independent streams (e.g. 2 accumulators)"],
         ["Structural", "Two items need one resource in the same cycle",
          "Single-port SRAM read and write in the same cycle",
          "Duplicate or bank the resource; arbitrate and stall"],
         ["Control", "The next item depends on a decision not yet made",
          "A branch; a packet whose length is in its header",
          "Speculate and flush; stall until resolved"]],
        widths=[14, 26, 32, 28], bold_first=True)
    box("expert", "The feedback-loop limit",
        "Pipelining cannot speed up a loop. If a result must feed back into "
        "the next computation (an accumulator, an IIR filter, a CRC, an "
        "arbiter's pointer), the entire loop must complete in one cycle, no "
        "matter how many registers you add elsewhere. Classic fixes are "
        "algebraic: carry-save accumulation (keep the accumulator in redundant "
        "form), look-ahead transformation of IIR filters, or processing K "
        "interleaved independent streams so that each loop has K cycles. "
        "Recognising the loop is the first step - in design reviews, ask "
        "'where are the feedback paths?'")

    h2("The valid/ready handshake")
    p("When a receiver can stall, the link needs **backpressure**. The "
      "valid/ready protocol (AXI's `VALID`/`READY`, AXI-Stream's "
      "`TVALID`/`TREADY`) uses two signals: the source drives `valid` "
      "together with the data; the sink drives `ready`. A **transfer** "
      "happens on every rising clock edge where both are high.")
    diagram([
        "  clock cycle  |  1  |  2  |  3  |  4  |  5  |  6  |  7  |",
        "  -------------+-----+-----+-----+-----+-----+-----+-----+",
        "  valid        |  0  |  1  |  1  |  1  |  0  |  1  |  1  |",
        "  data         |  -  | D0  | D0  | D1  |  -  | D2  | D2  |",
        "  ready        |  1  |  0  |  1  |  1  |  1  |  0  |  1  |",
        "  -------------+-----+-----+-----+-----+-----+-----+-----+",
        "  transfer     |     |stall| D0  | D1  |     |stall| D2  |",
        "",
        "  cycle 2: valid without ready -> source holds D0 (rule 2)",
        "  cycle 5: ready without valid -> allowed, nothing happens (rule 4)",
    ], "A transfer happens at the end of every cycle in which valid AND "
       "ready are both high. While stalled, the source holds valid high and "
       "the data stable.")
    tbl(["Rule", "Why"],
        [["1. A transfer occurs when `valid && ready` at a clock edge - and "
          "only then", "Both sides count transfers identically; no separate "
          "acknowledge is needed"],
         ["2. Once `valid` is asserted, the source must keep it asserted, and "
          "keep the data stable, until the transfer happens",
          "The sink may sample the data at any edge; a source that 'changes "
          "its mind' loses or corrupts data"],
         ["3. `valid` must **not** depend combinationally on `ready`",
          "Prevents deadlock (a source waiting for ready before raising valid, "
          "facing a sink that waits for valid) and combinational loops"],
         ["4. `ready` **may** depend combinationally on `valid`, and may be "
          "asserted before valid", "Allowed by AXI, but every such dependency "
          "lengthens the path and risks loops; registered ready is better"],
         ["5. After reset, `valid` must be low", "Ensures no phantom transfer "
          "during reset release"]],
        widths=[52, 48], bold_first=False,
        caption="The valid/ready rules (as in the AMBA AXI and AXI-Stream "
        "specifications). Chapter 13 applies them to all five AXI channels.")
    box("warn", "PITFALL - combinational loops through valid and ready",
        "If block A computes `valid_out = f(ready_in)` and block B computes "
        "`ready_out = g(valid_in)`, connecting them closes a loop through two "
        "modules that each looked fine alone. Rule 3 forbids the first half. "
        "More subtly, long chains where every stage passes `ready` "
        "combinationally upstream create a timing path from the last sink to "
        "the first source across the whole pipeline - legal, but often the "
        "critical path of the design. The skid buffer below cuts it.")

    h2("A pipeline register with ready propagation")
    p("To add a register stage to a valid/ready link, the stage must stall "
      "when downstream stalls. The simplest correct version accepts a new word "
      "when it is empty **or** when its current word is leaving this cycle:")
    code(r'''// Forward-registered pipeline stage: data/valid registered, ready is combinational
// (s_ready = !m_valid || m_ready). Full throughput, but a ready path runs through.
module pipe_reg #(parameter int W = 8) (
  input  logic         clk, rst_n,
  input  logic         s_valid,
  output logic         s_ready,
  input  logic [W-1:0] s_data,
  output logic         m_valid,
  input  logic         m_ready,
  output logic [W-1:0] m_data
);
  assign s_ready = !m_valid || m_ready;      // empty, or emptying this cycle
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n)       m_valid <= 1'b0;
    else if (s_ready) m_valid <= s_valid;
  always_ff @(posedge clk)
    if (s_ready && s_valid) m_data <= s_data; // datapath: no reset
endmodule''', "`s_` = slave (sink) side, `m_` = master (source) side, as in "
       "AXI naming. The stage sustains one word per cycle, but `m_ready` "
       "passes straight through to `s_ready`.")
    p("Two tempting simplifications are wrong. `s_ready = !m_valid` (accept "
      "only when empty) is correct but halves throughput: the stage "
      "alternates between full and empty. `s_ready = m_ready` (just forward "
      "ready) loses data when the stage holds a word and the source sends "
      "another while downstream is stalled - unless the stage is always "
      "emptied, which it is not.")

    h2("The skid buffer")
    p("To cut the ready path as well, `s_ready` must come from a flop. But a "
      "registered ready is one cycle late: when downstream stalls, upstream "
      "has already been told 'ready' for this cycle and sends one more word. "
      "The **skid buffer** has a second register to catch exactly that word "
      "- the data 'skids' into it like a car braking. It is the standard "
      "building block for timing-closing long valid/ready paths, and appears "
      "as the 'register slice' in commercial AXI interconnects.")
    code(r'''// Skid buffer: full throughput AND s_ready comes straight from a flop, so the
// ready path is cut. When downstream stalls, the word already accepted
// (because s_ready was promised a cycle earlier) lands in the skid register.
module skid_buffer #(parameter int W = 8) (
  input  logic         clk, rst_n,
  input  logic         s_valid,
  output logic         s_ready,
  input  logic [W-1:0] s_data,
  output logic         m_valid,
  input  logic         m_ready,
  output logic [W-1:0] m_data
);
  logic [W-1:0] skid_data;
  logic         skid_valid;                  // skid register occupied

  assign s_ready = !skid_valid;              // a flop output (plus inverter)

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      m_valid    <= 1'b0;
      skid_valid <= 1'b0;
    end else if (m_ready || !m_valid) begin  // output register free or draining
      m_valid    <= skid_valid || s_valid;   // skid first, else the input
      skid_valid <= 1'b0;
    end else if (s_valid && s_ready) begin   // output stalled: catch the word
      skid_valid <= 1'b1;
    end

  always_ff @(posedge clk) begin             // datapath: no reset
    if (m_ready || !m_valid)
      m_data <= skid_valid ? skid_data : s_data;
    if (s_valid && s_ready && m_valid && !m_ready)
      skid_data <= s_data;
  end
endmodule''', "Both outputs are registered: `m_valid`/`m_data` directly, "
       "`s_ready` as the inverse of the `skid_valid` flop. No combinational "
       "path exists from `m_ready` to `s_ready`.")
    tbl(["Output reg", "Skid reg", "s_ready", "What happens at the next edge"],
        [["empty", "empty", "1", "Input word (if valid) goes to the output register"],
         ["full, draining", "empty", "1", "Output takes the new input word; "
          "full throughput"],
         ["full, stalled", "empty", "1", "Input word is caught in the skid "
          "register; s_ready drops"],
         ["full, stalled", "full", "0", "Nothing moves; upstream sees ready "
          "low and holds"],
         ["full, draining", "full", "0", "Skid word moves to the output; "
          "s_ready returns next cycle"]],
        widths=[18, 14, 12, 56], bold_first=True,
        caption="The skid buffer's four reachable situations. The skid "
        "register can only fill when the output is stalled, and it always "
        "empties first when the output drains, so ordering is preserved.")
    p("The testbench chains a skid buffer and a pipeline register between a "
      "random source and a random sink. The source obeys rule 2 (it holds "
      "valid and data until accepted), a checker enforces the same rule on "
      "the skid buffer's output, and the sink verifies that the sequence "
      "0, 1, 2, ... arrives in order with nothing lost or duplicated.")
    code(r'''  // AXI-style source: once valid is raised, hold it and the data until accepted
  logic [W-1:0] nxt_word;
  assign nxt_word = next_in + (s_valid && s_ready);
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      s_valid <= 0;  s_data <= 0;
    end else if (!s_valid || s_ready) begin
      s_valid <= ($urandom_range(1, 100) <= p_valid) && nxt_word < limit;
      s_data  <= nxt_word;
    end
  always_ff @(posedge clk) next_in <= rst_n ? nxt_word : '0;
  // protocol check on the skid output: a stalled word must hold valid and data
  logic v1_q = 0, r1_q;  logic [W-1:0] d1_q;
  always_ff @(posedge clk) begin
    if (v1_q && !r1_q && (!v1 || d1 !== d1_q)) errors++;
    v1_q <= v1;  r1_q <= r1;  d1_q <= d1;
  end
  // sink: random ready; check in-order, no loss, no duplication
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) m_ready <= 0;
    else        m_ready <= ($urandom_range(1, 100) <= p_ready);
  always_ff @(posedge clk) if (rst_n) begin
    cycles <= cycles + 1;
    if (m_valid && m_ready) begin
      if (m_data !== next_out) errors++;
      next_out <= next_out + 1'b1;
    end
  end''', "The core of the testbench (source -> skid_buffer -> pipe_reg -> "
         "sink). A `run(p_valid, p_ready)` task sets the probabilities, "
         "sends 3000 words and reports the cycles taken.")
    out(["valid 100%  ready 100% : 3000 words in 3003 cycles, errors=0",
         "valid 100%  ready  50% : 3000 words in 5978 cycles, errors=0",
         "valid  50%  ready 100% : 3000 words in 5895 cycles, errors=0",
         "valid  70%  ready  70% : 3000 words in 4958 cycles, errors=0"],
        "Icarus Verilog output. With no stalls the chain sustains one word "
        "per cycle (3000 words + 3 cycles of fill latency). With random "
        "stalls the throughput is set by the less willing side, and no word "
        "is ever lost, duplicated or reordered.")
    box("tip", "How we know the testbench can fail",
        "A testbench that always passes proves nothing. Mutating the skid "
        "buffer so that it never captures the skid word (`skid_valid <= "
        "1'b0` in the stall branch) still passes the stall-free run - but in "
        "the first run with stalls the in-order check reported 1497 errors, "
        "and because words were lost the run never reached its word count "
        "(a watchdog timeout ended it). Always try a mutation on every "
        "checker you write, and always give testbenches a timeout "
        "(Chapter 22).")

    h2("Credit-based flow control")
    p("Valid/ready needs a round trip within one cycle: the sink's `ready` "
      "must reach the source before the next edge. Across long wires, chip "
      "partitions, clock-domain crossings or network-on-chip links (Chapter 14) "
      "that is impossible. **Credit-based** flow control replaces ready with "
      "a counter at the sender: it starts with as many credits as the "
      "receiver has buffer slots, spends one per word sent, and receives one "
      "back each time the receiver frees a slot. The sender can never "
      "overflow the receiver, however long the link latency.")
    code(r'''// Credit-based sender: may only send while it holds credits.
// The receiver returns one credit per buffer slot it frees.
module credit_tx #(parameter int CREDITS = 4, localparam int CW = $clog2(CREDITS+1)) (
  input  logic clk, rst_n,
  input  logic want_send,      // producer has a word
  input  logic credit_ret,     // pulse: receiver freed one slot
  output logic send,           // word goes on the link this cycle
  output logic [CW-1:0] credits
);
  assign send = want_send && (credits != '0);
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) credits <= CW'(CREDITS);   // = receiver buffer depth
    else        credits <= credits - CW'(send) + CW'(credit_ret);
endmodule''')
    out(["sent 4 words with 4 credits and no returns (credits=0)",
         "one credit returned -> send=1"],
        "Icarus Verilog output: the sender stops by itself after four words "
        "and resumes as soon as one credit comes back.")
    eq(["credits needed for full throughput  >=  round-trip latency in cycles",
        "   RTT = forward link latency + receiver processing + credit return latency",
        "   with fewer credits:  throughput = credits / RTT  words per cycle"],
       "Credit sizing. The receiver buffer must be as deep as the credit "
       "count, so long links cost buffering - the same bandwidth-delay "
       "product that governs network protocols.")

    h2("Elastic buffers and bubble collapsing")
    p("A pipeline built from `pipe_reg` or skid stages is **elastic**: each "
      "stage holds a word or a bubble (an empty slot), and stalls propagate "
      "backward only as far as necessary. Two properties follow:")
    bul([
        "**Bubble collapsing.** In `pipe_reg`, a stage accepts new data when "
        "it is empty even if downstream is stalled (`s_ready = !m_valid || "
        "m_ready`). Bubbles are squeezed out while the output is blocked, so "
        "the pipeline fills up completely and can restart at full rate. A "
        "naive pipeline that stalls **every** stage on a global stall signal "
        "keeps its bubbles forever and wastes throughput.",
        "**Buffering absorbs burstiness.** An elastic pipeline of S stages "
        "holds up to S words (2S with skid buffers). When a producer is "
        "bursty and a consumer is steady (or vice versa), the required depth "
        "is set by the longest burst minus what the consumer drains during it "
        "- if that exceeds a few stages, insert a FIFO (Chapter 9).",
        "**Global stall versus local handshakes.** A single global enable "
        "(`if (!stall) all_regs <= next`) is small but creates a high-fanout, "
        "timing-critical stall net. Local valid/ready handshakes cost more "
        "logic but scale; large designs mix both: global enables inside a "
        "tightly timed core, handshakes between blocks.",
    ])

    h2("Throughput math for handshaked pipelines")
    tbl(["Situation", "Throughput (words / cycle)"],
        [["No stalls, fully pipelined", "1"],
         ["Stage accepts only when empty (`s_ready = !m_valid`)", "1/2"],
         ["Source valid with probability p_v, sink ready with p_r, "
          "independent, deep buffering", "about min(p_v, p_r)"],
         ["Shallow buffering between random source and sink",
          "below min(p_v, p_r) - both must be willing in the same cycle "
          "more often"],
         ["Iterative block needing k cycles per item (e.g. `div_iter`)",
          "1/k - replicate k copies to get back to 1"],
         ["Credit link with C credits and round trip R cycles", "min(1, C/R)"]],
        widths=[62, 38], bold_first=False)
    p("The simulation above agrees: with valid at 100% and ready at 50%, "
      "3000 words took 5978 cycles, i.e. 0.50 words per cycle; with both at "
      "70%, 0.61 words per cycle - a little below 0.70 because the chain holds "
      "only three words, so it cannot fully absorb runs where the two sides "
      "are unwilling at different times.")
    checklist("Valid/ready design review checklist", [
        "`valid` never depends combinationally on `ready` in any module.",
        "Once asserted, `valid` and data are held until the transfer.",
        "Every register stage either sustains full throughput or documents "
        "why not.",
        "Long `ready` chains are cut with skid buffers or register slices at "
        "block boundaries.",
        "Data and sideband signals (last, keep, user, id) are pipelined with "
        "the same enables as the data.",
        "`valid` flops are reset; data flops normally are not.",
        "The testbench includes random stalls on both sides and a protocol "
        "checker (or SVA properties - Chapter 23).",
    ])

    h2("Summary")
    bul([
        "Pipelining trades latency and flops for throughput; the slowest "
        "stage and the per-stage overhead limit the gain; feedback loops "
        "cannot be pipelined away.",
        "Valid/ready transfers when both are high at a clock edge; valid must "
        "be held until accepted and must not depend on ready.",
        "`pipe_reg` gives full throughput with a combinational ready path; "
        "the skid buffer gives full throughput with every output registered.",
        "Credit-based flow control handles long-latency links; credits needed "
        "equal the round-trip latency.",
        "Elastic pipelines collapse bubbles; FIFOs absorb longer bursts.",
        "Always verify handshake logic with random stalls on both sides and "
        "an in-order, no-loss scoreboard.",
    ])
    h2("Exercises")
    bul([
        "Prove, by listing cases, that `s_ready = m_ready` (without the "
        "`!m_valid` term) in `pipe_reg` can lose data. Then demonstrate the "
        "loss with the testbench.",
        "Build a 4-stage pipeline of skid buffers and measure throughput with "
        "valid = 100% and ready = 70%. Compare with four `pipe_reg` stages.",
        "Convert `mac_pipe` to a valid/ready interface with backpressure, "
        "using a single stall-enable for the three stages. Why must "
        "`in_ready` then depend on `out_ready`?",
        "Design the receiver side of the credit link: a 4-entry FIFO that "
        "pulses `credit_ret` when a word is popped. Connect it to `credit_tx` "
        "through a 3-cycle delay line in each direction and find the minimum "
        "credits for full throughput.",
        "A source produces bursts of 64 words at one per cycle every 256 "
        "cycles; the sink accepts one word every 3 cycles. What FIFO depth "
        "prevents the source from ever stalling?",
    ], ordered=True)
