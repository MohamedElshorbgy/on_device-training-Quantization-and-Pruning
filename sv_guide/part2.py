"""Part II - Verilog in Depth (Chapters 7-11) of the Verilog & SystemVerilog guide.

Every example shown with an out() card was compiled and run with the tools
installed in this environment: Icarus Verilog 12 (iverilog -g2012 -Wall / vvp,
including -gspecify, -T min/typ/max, $sdf_annotate and a VPI module built with
iverilog-vpi), Verilator 5.020 (for %p formatting) and Yosys 0.33 (synthesis
of the simulation/synthesis mismatch demos, whose netlists were re-simulated
with Icarus against Yosys' simcells.v). Configurations and timing-check
violations are not supported by these tools; they are shown without output
and the expected behaviour of a commercial simulator is described in prose.
"""

from sv_guide.common import *  # noqa: F401,F403
from rtl_guide.common import G


def vcode(lines, caption=None):
    """Like code(), but only // lines are comment-coloured, so that Verilog
    statements starting with a delay (#10 a = 1;) are not shown as comments."""
    if isinstance(lines, str):
        lines = lines.split("\n")
    paras = []
    for ln in lines:
        ln = ln.rstrip("\n")
        esc = G.xe(ln).replace(" ", "&nbsp;")
        if ln.strip().startswith("//"):
            esc = '<font color="#2e7d32"><i>%s</i></font>' % esc
        paras.append(G.Paragraph(esc if esc else "&nbsp;", G.S_CODE))
    t = G.Table([[pp] for pp in paras], colWidths=[G.CONTENT_W])
    t.setStyle(G.TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), G.C_CODE_BG),
        ("BOX", (0, 0), (-1, -1), 0.7, G.C_CODE_BD),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 0.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.6),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, G.C_MID),
    ]))
    tail = G.Paragraph(G.mk(caption), G.S_CAP) if caption else G.Spacer(1, 6)
    if len(paras) <= 18:
        add(G.KeepTogether([G.Spacer(1, 3), t, tail]))
    else:
        add(G.Spacer(1, 3), t, tail)


def part2():
    part("Verilog in Depth",
         "Part I taught the core of the language. This part covers the rest "
         "of IEEE 1364 that every professional meets sooner or later: "
         "parameterisation and generate, the preprocessor, the gate-level "
         "and timing constructs that standard-cell libraries and gate-level "
         "simulation are built on, the system tasks that testbenches live "
         "on, and - most important of all for a designer - the synthesizable "
         "subset and the ways RTL simulation can disagree with the hardware "
         "that synthesis actually builds.")
    ch7()
    ch8()
    ch9()
    ch10()
    ch11()


# =============================================================================
#            Chapter 7 - Parameters, generate and configurations
# =============================================================================
def ch7():
    chapter("Parameters, Generate and Configurations", newpage=False)
    p("A block of silicon IP is almost never written for one size. The same "
      "FIFO is instantiated 40 times in an SoC with a dozen different depths "
      "and widths; the same AXI interconnect is built with 3 masters in one "
      "chip and 11 in the next; a DSP datapath is generated with 4, 8 or 16 "
      "lanes. Verilog supports this with three mechanisms that all act at "
      "**elaboration time** - after parsing, before simulation or "
      "synthesis starts: **parameters** (named constants that can differ per "
      "instance), **generate constructs** (structure that is replicated or "
      "selected according to parameters) and **configurations** (which "
      "source description is bound to which instance). Understanding exactly "
      "when and how these are evaluated is what separates a reusable IP from "
      "a block that has to be edited by hand for every project.")
    diagram([
        "  source files --> parse --> ELABORATION -----------------------------> simulate",
        "                              |  1. build hierarchy from the top       |  or",
        "                              |  2. resolve parameter values per inst. |  synthesize",
        "                              |     (#() overrides, defparam)          |",
        "                              |  3. evaluate constant expressions      |",
        "                              |     ($clog2, constant functions)       |",
        "                              |  4. expand generate for/if/case        |",
        "                              |  5. bind cells via config/libraries    |",
        "                              v                                        v",
        "                        one flat, fully-sized design (no parameters left)",
    ], "Everything in this chapter is resolved during elaboration. Nothing "
       "here exists at run time: a parameter is never a register.")

    # ------------------------------------------------------------------
    h2("parameter and localparam")
    p("A `parameter` is a named constant of a module (or interface, program "
      "or class in SystemVerilog) whose value may be changed for each "
      "instance when the design is elaborated. A `localparam` is identical "
      "except that it can **never** be overridden from outside; it is "
      "normally derived from other parameters. Both may only be assigned "
      "**constant expressions**: literals, other parameters, `localparam`s, "
      "`genvar`s, constant function calls and constant system functions such "
      "as `$clog2`, `$bits`, `$signed` and the math functions. A variable, a "
      "net or a hierarchical reference is never allowed.")
    p("Parameters may be declared in two places. The Verilog-2001 **parameter "
      "port list** `#( ... )` after the module name is the modern style and "
      "the only one you should write; body declarations are the Verilog-1995 "
      "style. IEEE 1800 adds a rule that surprises people: if a module has a "
      "parameter port list, **every** `parameter` declared in its body is "
      "treated as a `localparam` and cannot be overridden. SystemVerilog "
      "also allows `localparam` inside the port list, which keeps derived "
      "values next to the parameters they depend on (Icarus, Verilator and "
      "all commercial tools accept it).")
    vcode(r"""module fifo #(
  parameter  integer DEPTH  = 16,          // typed parameter
  parameter  [7:0]   WIDTH  = 8,           // ranged parameter (8-bit, unsigned)
  parameter          NAME   = "fifo",      // untyped: takes type of its value
  localparam integer AW     = $clog2(DEPTH) // derived; cannot be overridden
) ();
  initial $display("%m: DEPTH=%0d WIDTH=%0d AW=%0d NAME=%0s", DEPTH, WIDTH, AW, NAME);
endmodule

module top;
  fifo                           u_default ();
  fifo #(64, 32)                 u_pos     ();   // positional: DEPTH=64, WIDTH=32
  fifo #(.DEPTH(1000), .NAME("rx")) u_named ();  // named: WIDTH keeps its default
  fifo                           u_defp    ();
  defparam u_defp.DEPTH = 5;                     // legal but deprecated
endmodule""", "p1.v - the three ways of giving an instance its own parameter "
               "values.")
    out(["top.u_default: DEPTH=16 WIDTH=8 AW=4 NAME=fifo",
         "top.u_pos: DEPTH=64 WIDTH=32 AW=6 NAME=fifo",
         "top.u_named: DEPTH=1000 WIDTH=8 AW=10 NAME=rx",
         "top.u_defp: DEPTH=5 WIDTH=8 AW=3 NAME=fifo"],
        "iverilog -g2012 -Wall p1.v && vvp - note that AW is recomputed for "
        "every instance.")

    h3("The type and size of a parameter")
    p("A parameter declaration may carry a data type, a range, a sign, all "
      "of these or none. The rules (IEEE 1800-2017 6.20.2, same as 1364-2005 "
      "12.2) decide what an overriding value turns into, and they are a "
      "classic source of silent truncation:")
    tbl(["Declaration", "Type/size of the parameter", "Effect of an override"],
        [["`parameter P = 8'd200`", "Untyped: takes the type, size and sign "
          "of the **final** value", "Takes the size of the overriding value "
          "(pass 12'd10 and P becomes 12 bits)"],
         ["`parameter [3:0] P = ...`", "Unsigned, exactly the range given",
          "Override is converted: truncated or zero-extended to 4 bits"],
         ["`parameter signed [7:0] P`", "Signed, range given",
          "Converted to 8-bit signed"],
         ["`parameter signed P = ...`", "Signed, size from the final value",
          "Size follows value, sign forced signed"],
         ["`parameter integer P`", "32-bit signed integer",
          "A real value is rounded, not truncated"],
         ["`parameter real P`", "Real", "An integer value is converted to "
          "real"],
         ["`parameter type T = logic`", "SystemVerilog type parameter",
          "A type, not a value (Chapter 17)"]],
        widths=[27, 36, 37])
    vcode(r"""module p2;
  parameter        P_U   = 8'd200;      // untyped: 8-bit unsigned from value
  parameter [3:0]  P_R   = 8'd200;      // ranged: value truncated to 4 bits
  parameter signed [7:0] P_S = 8'd200;  // signed 8-bit: reads as -56
  parameter real   P_F   = 2.5;
  parameter integer P_I  = 2.9;         // real converted to integer: rounds
  initial begin
    $display("P_U=%0d bits=%0d", P_U, $bits(P_U));
    $display("P_R=%0d bits=%0d", P_R, $bits(P_R));
    $display("P_S=%0d", P_S);
    $display("P_F=%0.2f P_I=%0d", P_F, P_I);
  end
endmodule""", "p2.v - what the declared type does to a value.")
    out(["P_U=200 bits=8", "P_R=8 bits=4", "P_S=-56", "P_F=2.50 P_I=3"],
        "Icarus Verilog 12. 200 = 1100_1000b: truncated to 4 bits it is 8; "
        "as signed 8-bit it is -56.")
    box("warn", "Pitfall: untyped parameters change width when overridden",
        "A bare `parameter W = 8` is a 32-bit integer by default - but if an "
        "integrator overrides it with a sized literal such as `4'd12`, W "
        "becomes a 4-bit unsigned value and every expression using W is now "
        "evaluated with different sizing rules (Chapter 4). Arithmetic such "
        "as `W*2` or `W-1` can then wrap. Give parameters that are used as "
        "numbers an explicit type (`parameter int W = 8` in SystemVerilog, "
        "`parameter integer W = 8` in Verilog) and give parameters that are "
        "used as bit patterns an explicit range (`parameter [31:0] RST_VAL`).")

    # ------------------------------------------------------------------
    h2("Overriding parameters: #(), named association and defparam")
    p("There are two legal ways to change a parameter of an instance. The "
      "**instance parameter value assignment** `#( ... )` is part of the "
      "instantiation and comes in two forms, exactly like port connections: "
      "**positional** (`#(64, 32)` - values assigned in declaration order, "
      "you cannot skip one) and **named** (`#(.DEPTH(64))` - any subset, in "
      "any order). Named association is the only style that survives a "
      "reordering of the parameter list in the next IP release, so every "
      "coding guideline requires it. A parameter that is not mentioned keeps "
      "its default, and `localparam`s cannot be named at all:")
    vcode(r"""module m #(parameter A = 4, localparam B = A * 2) ();
  initial $display("%m A=%0d B=%0d", A, B);
endmodule
module top3;
  m #(.A(3), .B(9)) u ();
endmodule""", "p3.v - attempting to override a localparam.")
    out(["p3.v:5: error: Cannot override localparam `B` in `top3.u`.",
         "2 error(s) during elaboration."], "iverilog -g2012 -Wall p3.v")
    p("The second mechanism is the **defparam** statement, which assigns a "
      "new value to any parameter anywhere in the design through a "
      "**hierarchical name**. It was the only override mechanism in the "
      "earliest Verilog and it still works in every tool, but IEEE 1800-2017 "
      "lists it in Annex C as **deprecated**, and it is banned by virtually "
      "every company coding standard. The example shows why:")
    vcode(r"""module leaf #(parameter W = 1) ();
  initial $display("%m W=%0d", W);
endmodule
module mid;
  leaf u_leaf ();
endmodule
module top4;
  mid u_a ();
  mid u_b ();
  defparam u_a.u_leaf.W = 8;        // reaches down two levels, from outside
endmodule
module other;                         // another top-level module...
  defparam top4.u_b.u_leaf.W = 16;  // ...silently changes a design it does not own
endmodule""", "p4.v - defparam is action at a distance.")
    out(["top4.u_a.u_leaf W=8", "top4.u_b.u_leaf W=16"],
        "Icarus: both overrides take effect, one of them from a completely "
        "unrelated top-level module.")
    bul(["**Action at a distance.** Reading `mid` or `leaf` tells you "
         "nothing about the value W will have; it can be changed from any "
         "file in the compile list, including a testbench file that the "
         "synthesis tool never sees - a guaranteed simulation/synthesis "
         "mismatch.",
         "**Precedence surprises.** If a parameter is set both by `#()` and by "
         "`defparam`, the `defparam` wins; if two `defparam`s target the "
         "same parameter the result depends on source order.",
         "**Elaboration complexity.** A `defparam` can change a parameter "
         "that controls a generate construct, which creates new hierarchy "
         "that may contain further `defparam`s. The LRM needs special rules "
         "(a `defparam` inside a generate block or instance array may only "
         "affect its own sub-hierarchy) and tools elaborate it iteratively.",
         "**Tool support.** Several synthesis and formal tools reject it, "
         "or only accept it when it targets a direct child instance."])
    box("key", "House rule",
        "Override parameters only with named `#(.NAME(value))` association "
        "at the point of instantiation. Derived constants are `localparam`. "
        "Never write `defparam` in new code; when you inherit it in legacy IP, "
        "convert it to `#()` overrides before the first synthesis run.")

    # ------------------------------------------------------------------
    h2("Parameter dependencies and constant expressions")
    p("A parameter's default may refer to parameters declared before it. "
      "The default expression is evaluated **after** overrides are applied, "
      "so a dependent parameter automatically follows an overridden one - "
      "unless the dependent parameter is itself overridden, at which point "
      "the relationship is broken silently. This is the real reason derived "
      "values should be `localparam`:")
    vcode(r"""module cfg_reg #(
  parameter W     = 8,               // untyped: becomes whatever is passed in
  parameter MAX   = (1 << W) - 1,    // depends on W: re-evaluated after override
  parameter [W-1:0] RST = MAX        // its range also follows W
) ();
  initial $display("%m: W=%0d MAX=%0d RST=%h  $bits(W)=%0d", W, MAX, RST, $bits(W));
endmodule
module top5;
  cfg_reg                     a ();
  cfg_reg #(.W(4))            b ();  // MAX and RST follow W
  cfg_reg #(.W(4), .MAX(100)) c ();  // MAX overridden -> no longer tied to W
  cfg_reg #(.W(12'd10))       d ();  // untyped W now has 12 bits
endmodule""", "p5.v - dependent parameters.")
    out(["top5.a: W=8 MAX=255 RST=ff  $bits(W)=32",
         "top5.b: W=4 MAX=15 RST=f  $bits(W)=32",
         "top5.c: W=4 MAX=100 RST=4  $bits(W)=32",
         "top5.d: W=10 MAX=1023 RST=3ff  $bits(W)=12"],
        "Instance c: 100 does not fit in 4 bits, so RST silently becomes 4. "
        "Instance d: W changed its own width to 12 bits.")
    h3("Constant functions")
    p("When a derived constant needs more than an expression - a log2, a "
      "maximum over a list, a CRC table entry - Verilog-2001 lets you call a "
      "**constant function**: an ordinary function of the same module that is "
      "called with constant arguments in a place where a constant is "
      "required. The LRM (1364-2005 10.4.5, 1800-2017 13.4.3) restricts it so "
      "the elaborator can execute it: it may use only its arguments, its own "
      "locals, parameters and other constant functions; no hierarchical "
      "references, no timing controls, no non-constant system functions, and "
      "(Verilog) it must be declared in the module that calls it. The "
      "built-in **$clog2** (ceiling of log2, added in 1364-2005) replaced "
      "the hand-written version in most code, but the pattern is still "
      "useful and appears in older IP:")
    vcode(r"""module enc #(parameter N = 8) (input [N-1:0] req, output [$clog2(N)-1:0] idx);
  // Constant function: legal in a constant expression because it is
  // side-effect free and uses only its arguments and parameters.
  function integer clog2(input integer v);
    integer k;
    begin
      clog2 = 0;
      for (k = v - 1; k > 0; k = k >> 1) clog2 = clog2 + 1;
    end
  endfunction
  localparam W = clog2(N);
  reg [W-1:0] r; integer j;
  always @* begin
    r = {W{1'b0}};
    for (j = N-1; j >= 0; j = j - 1) if (req[j]) r = j[W-1:0];   // lowest index wins
  end
  assign idx = r;
  initial $display("%m: N=%0d -> W=%0d (builtin $clog2=%0d)", N, W, $clog2(N));
endmodule""", "g3.v (part 1) - a constant function sizing a localparam. The "
               "port uses the built-in $clog2, because referring to a "
               "function before its declaration is not portable.")
    tbl(["You need a width that can hold...", "Expression", "Gotcha"],
        [["an index 0 .. N-1 (address of an N-entry RAM)", "`$clog2(N)`",
          "N = 1 gives 0: a zero-width vector `[-1:0]`. Use "
          "`(N > 1) ? $clog2(N) : 1`"],
         ["a count 0 .. N (FIFO occupancy, N inclusive)", "`$clog2(N+1)`",
          "`$clog2(16)` = 4 cannot hold 16"],
         ["a value up to MAX", "`$clog2(MAX+1)`", "Same off-by-one"],
         ["N items, N a power of two, one extra wrap bit", "`$clog2(N)+1`",
          "Classic FIFO pointer (companion RTL Design guide)"]],
        widths=[40, 22, 38], caption="Sizing with $clog2.")

    # ------------------------------------------------------------------
    h2("Generate constructs")
    p("A **generate construct** is structure that is created, replicated or "
      "discarded during elaboration according to constant expressions. Since "
      "1364-2005 a generate construct can appear directly in the module "
      "body; the `generate ... endgenerate` keywords that enclose it "
      "(a **generate region**) are optional and have no semantic effect. "
      "There are three kinds:")
    tbl(["Construct", "Chooses/replicates", "Typical SoC use"],
        [["**Loop generate** `for (genvar ...)`", "N copies of the body, one "
          "scope per iteration", "Per-lane datapaths, bit-slices, arrays of "
          "FIFOs, per-master arbitration logic, synchronizer banks"],
         ["**Conditional generate** `if`", "At most one of the branches",
          "Optional features (ECC on/off), technology selection (behavioural "
          "model vs. hard macro), small/large implementations"],
         ["**Case generate** `case`", "At most one of the items",
          "Selecting among several architectures by an integer or string "
          "parameter"]], widths=[27, 30, 43])
    p("A generate block may contain almost any **module item**: net and "
      "variable declarations, continuous assignments, `always` and `initial` "
      "blocks, module/primitive instances, functions, tasks, `localparam`s "
      "and nested generate constructs. It may **not** contain port "
      "declarations, `specify` blocks or `specparam`s, and a parameter "
      "declared inside it can never be overridden - write `localparam`.")
    h3("Loop generate and genvar")
    p("The loop variable must be a **genvar**: an integer that exists only "
      "during elaboration. It can be declared before the loop (`genvar i;`) "
      "or, in SystemVerilog, inline (`for (genvar i = 0; ...)`). The "
      "initialisation, condition and step must be constant expressions, the "
      "genvar may not be assigned anywhere else, and two nested loops may not "
      "use the same genvar. Each iteration produces a separate **generate "
      "block instance** named `name[i]`; declarations inside the block are "
      "local to that iteration, which is what makes `wire p` below a "
      "different net for every bit:")
    vcode(r"""// Ripple-carry adder built with a generate-for loop
module rca #(parameter N = 4) (
  input  [N-1:0] a, b, input cin,
  output [N-1:0] s, output cout);
  wire [N:0] c;
  assign c[0] = cin;
  genvar i;
  generate
    for (i = 0; i < N; i = i + 1) begin : g_bit     // named block -> g_bit[0..N-1]
      wire p = a[i] ^ b[i];                          // local net, one per iteration
      assign s[i]   = p ^ c[i];
      assign c[i+1] = (a[i] & b[i]) | (p & c[i]);
    end
  endgenerate
  assign cout = c[N];
endmodule

module tb;
  reg  [3:0] a, b; reg cin; wire [3:0] s; wire co;
  rca #(4) dut (.a(a), .b(b), .cin(cin), .s(s), .cout(co));
  initial begin
    a = 4'd9; b = 4'd8; cin = 1'b1; #1;
    $display("9+8+1 = %0d (cout=%b s=%0d)", {co, s}, co, s);
    $display("propagate of bit 3 = %b  (tb.dut.g_bit[3].p)", dut.g_bit[3].p);
  end
endmodule""", "g1.v - a loop generate and a hierarchical reference into "
               "one of its iterations.")
    out(["9+8+1 = 18 (cout=1 s=2)",
         "propagate of bit 3 = 0  (tb.dut.g_bit[3].p)"], "Icarus Verilog 12.")
    box("tip", "Loop generate or procedural for loop?",
        "A `for` loop inside an `always @*` block is also unrolled by "
        "synthesis, and is often simpler (the priority encoder above uses "
        "one). Use a **generate** loop when each iteration needs its own "
        "**instances**, its own `always` block or its own continuous "
        "assignments, or when you need a hierarchical name per iteration "
        "(for debug, for SDF back-annotation, for a UPF power domain or for "
        "a DFT insertion script). Use a procedural loop for pure "
        "combinational functions of vectors.")

    h3("Conditional generate, case generate and block names")
    p("In a conditional generate the condition is evaluated once; only the "
      "chosen branch exists in the elaborated design. A useful idiom is to "
      "give **every branch the same block name**: because only one branch "
      "survives, the name is unique, and scripts, assertions and hierarchical "
      "references work whichever implementation was chosen. An `else if` "
      "chain does not create an extra level of hierarchy (the LRM's "
      "\"direct nesting\" rule), so all branches below are siblings:")
    vcode(r"""module mult #(parameter W = 8, parameter IMPL = "FAST") (
  input [W-1:0] a, b, output [2*W-1:0] y);
  generate                                      // 'generate' keyword is optional
    if (W <= 4) begin : g_impl                  // same name in every branch:
      assign y = a * b;                         // the path is g_impl whichever
      initial $display("%m: small LUT multiplier");  // branch is chosen
    end else if (IMPL == "FAST") begin : g_impl
      assign y = a * b;
      initial $display("%m: fast (Booth/Wallace) multiplier");
    end else begin : g_impl
      assign y = a * b;
      initial $display("%m: slow iterative multiplier");
    end
  endgenerate
  if (W > 16) begin                             // unnamed: tool names it genblkN
    initial $display("%m: wide!");
  end
endmodule

module tb2;
  wire [7:0] y4; wire [15:0] y8; wire [47:0] y24;
  mult #(4)          m4  (4'd3, 4'd5, y4);
  mult #(8, "SLOW")  m8  (8'd3, 8'd5, y8);
  mult #(24)         m24 (24'd3, 24'd5, y24);
  initial #1 $display("y4=%0d y8=%0d y24=%0d", y4, y8, y24);
endmodule""", "g2.v - conditional generate; a string parameter compared at "
               "elaboration time.")
    out(["tb2.m4.g_impl: small LUT multiplier",
         "tb2.m8.g_impl: slow iterative multiplier",
         "tb2.m24.g_impl: fast (Booth/Wallace) multiplier",
         "tb2.m24.genblk2: wide!",
         "y4=15 y8=15 y24=15"], "Icarus Verilog 12.")
    p("The last line shows the rule for **unnamed** generate blocks "
      "(1800-2017 27.6): each generate construct in a scope is numbered "
      "1, 2, 3... in source order - named or not - and an unnamed block of "
      "construct number n is called `genblk<n>`. Our `if (W > 16)` is the "
      "second generate construct in `mult`, hence `genblk2`. If that name "
      "clashes with a user identifier, leading zeros are inserted "
      "(`genblk02`). Because inserting a new construct above it renumbers "
      "the block, and because older tools used different schemes, **never "
      "leave a generate block that contains declarations or instances "
      "unnamed**: its hierarchical path appears in waveform setups, SDF "
      "files, UPF, synthesis constraints and formal scripts.")
    p("The generate `case` works the same way and is the natural choice when "
      "a parameter selects among more than two architectures:")
    vcode(r"""module rst_sync #(parameter STYLE = 1) (input clk, rst_n, output q);
  generate
    case (STYLE)                                 // generate-case
      0:       begin : g_s  assign q = rst_n;                 end
      1:       begin : g_s  reg [1:0] f = 0;
                            always @(posedge clk) f <= {f[0], rst_n};
                            assign q = f[1];                  end
      default: begin : g_s  reg [2:0] f = 0;
                            always @(posedge clk) f <= {f[1:0], rst_n};
                            assign q = f[2];                  end
    endcase
  endgenerate
  initial $display("%m: STYLE=%0d", STYLE);
endmodule

module tb3;
  reg [11:0] req; wire [3:0] idx; wire [2:0] i5;
  enc #(12) e12 (.req(req), .idx(idx));
  enc #(5)  e5  (.req(5'b10100), .idx(i5));
  reg clk = 0; wire q0, q2;
  rst_sync #(0) r0 (clk, 1'b1, q0);
  rst_sync #(3) r3 (clk, 1'b1, q2);
  always #5 clk = ~clk;
  initial begin
    req = 12'b0010_1000_0000;
    #1 $display("idx=%0d i5=%0d", idx, i5);
    #30 $display("q0=%b q2=%b bits(r3.g_s.f)=%0d", q0, q2, $bits(r3.g_s.f));
    $finish;
  end
endmodule""", "g3.v (part 2) - generate-case; the testbench also exercises "
               "the enc module shown earlier.")
    out(["tb3.e12: N=12 -> W=4 (builtin $clog2=4)",
         "tb3.e5: N=5 -> W=3 (builtin $clog2=3)",
         "tb3.r0: STYLE=0", "tb3.r3: STYLE=3",
         "idx=7 i5=2", "q0=1 q2=1 bits(r3.g_s.f)=3",
         "g3.v:48: $finish called at 31 (1s)"],
        "Icarus Verilog 12. For STYLE=3 the default item built a 3-flop "
        "synchronizer; $bits sees its 3-bit register through the g_s scope.")
    box("warn", "Pitfall: a generate condition is not a run-time condition",
        "`if (MODE == 1)` at module level is a **generate** if - MODE must be "
        "a constant and the branch is chosen once. The same text inside an "
        "`always` block is a procedural if and synthesizes to a multiplexer. "
        "If MODE is accidentally a signal, the module-level form is an "
        "elaboration error, which is good; but a parameter that was meant to "
        "be a run-time register field silently becomes hard-wired logic.")
    h3("Instance arrays")
    p("For the common case of N identical instances with sliced ports, "
      "Verilog also has **arrays of instances**: `inv u_inv [7:0] (.a(a), "
      ".y(y));` connects an 8-bit `a` bit-by-bit to eight 1-bit instances "
      "named `u_inv[7]` ... `u_inv[0]`. The port-slicing rule is simple (a "
      "vector whose width equals N x port width is divided evenly; a signal "
      "of exactly the port width is broadcast to all), but a generate loop "
      "is more flexible and more readable, and it is what most teams use.")

    # ------------------------------------------------------------------
    h2("Configurations and libraries")
    p("Parameters decide the __values__ inside a module; a **configuration** "
      "decides __which description__ of a module is used for each instance. "
      "Verilog-2001 introduced the concept to solve a real problem of "
      "mixed-level simulation: you want the CPU subsystem as gates (to check "
      "the netlist from synthesis) while the rest of the SoC stays at RTL, "
      "and both descriptions define a module called `cpu_core`.")
    p("Two pieces are involved. A **library map file** (tool option, "
      "e.g. `-libmap lib.map`) assigns source files to named **libraries**; "
      "a module compiled from those files becomes the **cell** `lib.module`. "
      "The **config** block then gives binding rules that the elaborator "
      "applies while it builds the hierarchy from the top:")
    vcode(r"""// lib.map - which files go into which library
library rtl_lib  "rtl/*.v";
library gate_lib "netlist/*.v";
library tb_lib   "tb/*.sv";

// cfg.v - the binding rules
config soc_gate_cpu;
  design tb_lib.tb_top;                          // the top-level cell(s)
  default liblist rtl_lib gate_lib;              // search order for every instance
  instance tb_top.dut.u_cpu liblist gate_lib;    // this instance (and below): netlist
  cell     sram_32x1024     use rtl_lib.sram_model;  // every sram_32x1024 -> a model
  instance tb_top.dut.u_dma use rtl_lib.dma_v2;  // bind one instance to another cell
endconfig""", "A library map and a configuration. Simulating the "
               "configuration (instead of a top module) elaborates tb_top "
               "with the CPU from the netlist and everything else from RTL.")
    tbl(["Clause", "Meaning"],
        [["`design lib.cell`", "Top-level cell(s) the configuration "
          "elaborates"],
         ["`default liblist a b`", "Libraries searched, in order, for any "
          "cell not bound by a more specific rule"],
         ["`instance path liblist ...`", "Search list for one instance "
          "and, by inheritance, its sub-hierarchy"],
         ["`instance path use lib.cell`", "Bind one instance to a specific "
          "cell (optionally `:config` to use another configuration "
          "hierarchically)"],
         ["`cell name use lib.cell`", "Bind every instance of a cell name"],
         ["`cell name liblist ...`", "Search list for every instance of a "
          "cell name"]], widths=[32, 68])
    out(["cfg.v:3: sorry: config declarations are not supported and will be skipped."],
        "Icarus Verilog 12 (Verilator 5.020 reports \"Unsupported: Verilog "
        "2001-config reserved word not implemented\"). Configurations need "
        "a commercial simulator such as VCS, Xcelium or Questa.")
    p("In practice many teams achieve the same effect with simpler "
      "mechanisms: compiling different file lists (the netlist file instead "
      "of the RTL file), tool-specific library options (`-y`, `-v`, "
      "`-L lib`), or a macro that selects which `include` or instance to "
      "use. Configurations remain valuable in large mixed-signal and "
      "gate-level regressions where many variants of the same testbench "
      "must be elaborated from one set of compiled libraries. SystemVerilog "
      "extended them only slightly (for example with parameter overrides "
      "inside a config in 1800-2009).")

    # ------------------------------------------------------------------
    h2("Where this is used on the SoC/ASIC roadmap")
    tbl(["Role", "What you do with parameters and generate"],
        [["RTL designer", "Write IP once with typed, named, documented "
          "parameters; derive every width with `localparam` and $clog2; use "
          "generate for per-lane/per-port structure; add elaboration-time "
          "checks for illegal combinations"],
         ["SoC integrator", "Instantiate IP with named overrides; generate "
          "the top level (often from IP-XACT or a Python script) with the "
          "right parameter sets"],
         ["DV engineer", "Run the regression over several parameter sets; "
          "bind assertions into generate scopes; read hierarchical names "
          "like `g_lane[3].u_fifo` in failures"],
         ["Synthesis / STA", "Constraints and reports use elaborated names "
          "(`u_dma/g_ch_2__u_fifo/...` after uniquification) - unnamed "
          "genblks make scripts fragile"],
         ["Gate-level / DFT", "Configurations or file lists swap RTL for "
          "netlists; SDF instance paths must match generate block names"]],
        widths=[20, 80], bold_first=True)
    box("expert", "Interview insight: checking parameters at elaboration",
        "A robust IP rejects illegal parameter values instead of silently "
        "building broken hardware. In SystemVerilog use an elaboration-time "
        "system task inside a generate if: `if (DEPTH < 2) $error(\"DEPTH "
        "must be >= 2\");` (1800-2009 onwards, reported during "
        "elaboration). In plain Verilog the classic trick is to instantiate "
        "a non-existent module inside the failing branch so that elaboration "
        "stops with a readable module name such as "
        "`DEPTH_must_be_a_power_of_2 u_err();`.")

    h2("Summary")
    bul(["Parameters, generate and configurations are all resolved during "
         "**elaboration**; afterwards the design is flat and fully sized.",
         "`parameter` can be overridden per instance; `localparam` cannot. "
         "With a parameter port list, body `parameter`s become local (1800).",
         "The declared type/range decides what an override becomes; untyped "
         "parameters take the width of whatever value is passed in.",
         "Override with named `#(.P(v))`. `defparam` is deprecated "
         "(1800 Annex C), acts at a distance and takes precedence over `#()`.",
         "Dependent defaults are re-evaluated after overrides; derive with "
         "`localparam` so the relationship cannot be broken.",
         "Constant functions and $clog2 compute widths; watch the N=1 and "
         "count-to-N off-by-one cases.",
         "Loop/if/case generate create named scopes; name every block "
         "(`begin : g_name`) - unnamed blocks become `genblk<n>`.",
         "Configurations bind instances to library cells for mixed RTL/gate "
         "simulation; open-source tools do not support them."])
    h2("Exercises")
    bul(["Write a parameterized `onehot_mux #(N, W)` using a generate loop "
         "that ANDs each input with its select bit and ORs the results. "
         "Verify with N=1, 3 and 8.",
         "A colleague writes `parameter WIDTH = 8; parameter MAXV = "
         "2**WIDTH - 1;` and instantiates with `#(.WIDTH(4'd12))`. What are "
         "WIDTH, MAXV and $bits(WIDTH)? Check your answer with Icarus.",
         "Explain what `genblk3` in a waveform refers to, and why adding an "
         "`if` generate at the top of the module changes the name of an "
         "unrelated block. How do you prevent this?",
         "Implement a FIFO whose depth may be any integer >= 2 and add an "
         "elaboration-time check that rejects DEPTH < 2 (both the SV "
         "$error way and the Verilog-2001 missing-module trick).",
         "Rewrite a legacy testbench that uses three `defparam` statements "
         "so that it uses only `#()` overrides. What changes if one of the "
         "targets is inside a generate loop?",
         "Write the config block that simulates `tb.dut` at RTL except "
         "for every instance of cell `pll_wrap`, which must use "
         "`ams_lib.pll_wrap`."], ordered=True)


# =============================================================================
#                 Chapter 8 - Compiler directives and macros
# =============================================================================
def ch8():
    chapter("Compiler Directives and Macros")
    p("Before a Verilog compiler parses a single module, a **preprocessor** "
      "reads the source text and acts on **compiler directives** - lines "
      "introduced by the grave accent character (ASCII 0x60, the \"back-"
      "tick\"). Directives define text macros, include other files, "
      "select code conditionally, and set compilation state such as the "
      "time unit or the default net type. They are not part of any module "
      "and they do not respect module boundaries: a directive stays in "
      "effect from the point where it is read **until it is changed, "
      "across file boundaries**, for the rest of the compilation unit. That "
      "single fact explains most of the pitfalls in this chapter.")
    box("note", "Notation in this chapter",
        "In running text the leading grave accent of a directive is omitted "
        "and the name is set in code font: the `define` directive, the "
        "`timescale` directive. Code listings show the real syntax, "
        "including the grave accent.")
    tbl(["Directive", "Purpose", "Standard"],
        [["`define`, `undef`, `undefineall`", "Text macros (with arguments "
          "since 1364-1995, default arguments since 1800-2009)",
          "1364 / 1800-2009"],
         ["`ifdef`, `ifndef`, `elsif`, `else`, `endif`",
          "Conditional compilation", "1364-2001"],
         ["`include`", "Textual file inclusion", "1364"],
         ["`timescale`", "Time unit and precision for delays", "1364"],
         ["`default_nettype`", "Type of implicitly declared nets "
          "(`wire`, `none`, ...)", "1364-2001"],
         ["`resetall`", "Reset all directives except macros to defaults",
          "1364"],
         ["`celldefine`, `endcelldefine`", "Mark modules as library cells",
          "1364"],
         ["`unconnected_drive`, `nounconnected_drive`", "Pull unconnected "
          "input ports up or down", "1364"],
         ["`line`", "Set file name and line number for messages",
          "1364-2005"],
         ["`__FILE__`, `__LINE__`", "Current file name / line number",
          "1800-2009"],
         ["`pragma`", "Tool-specific directives with standard syntax "
          "(e.g. `protect` encryption envelopes)", "1364-2005"],
         ["`begin_keywords`, `end_keywords`", "Select the reserved-word "
          "set of a given standard", "1364-2005 / 1800"]],
        widths=[36, 48, 16], caption="The complete directive set.")

    # ------------------------------------------------------------------
    h2("Text macros: define, arguments and undef")
    p("`define NAME text` defines a **text macro**; every later use of the "
      "name preceded by a grave accent is replaced by the text. The text runs "
      "to the end of the line; a backslash immediately before the newline "
      "continues it on the next line. A macro may take **formal arguments** "
      "in parentheses directly after its name (no space is allowed between "
      "the name and the parenthesis, otherwise the parenthesis becomes part "
      "of the text). SystemVerilog adds **default argument values**: a "
      "formal written as `msg = \"text\"` may be omitted at the call site. "
      "Macro substitution is purely textual - there is no type checking, no "
      "scoping and no evaluation, which gives both the power and the "
      "danger of macros.")
    vcode(r"""`ifndef DEFS_VH
`define DEFS_VH
`define DATA_W 32
`define MAX(a, b)  ((a) > (b) ? (a) : (b))
`define BAD_MAX(a, b)  a > b ? a : b
`define SQ(x) ((x) * (x))
`define BAD_SQ(x) x * x
`endif""", "defs.vh - a header with an include guard and two good and two "
            "bad macros.")
    vcode(r"""`include "defs.vh"
`include "defs.vh"          // second include is harmless thanks to the guard
`define CHECK(cond, msg = "check failed") \
  if (!(cond)) $display("ERROR %s:%0d: %s", `__FILE__, `__LINE__, msg);
`define STR(x) `"x`"
`define REG(name, w) reg [w-1:0] name``_q, name``_d;
module m1;
  `REG(cnt, 4)                        // declares cnt_q and cnt_d
  initial begin
    cnt_q = 4'd9; cnt_d = 4'd3;
    $display("MAX=%0d  1+MAX*2=%0d  1+BAD_MAX*2=%0d",
             `MAX(cnt_q, cnt_d), 1 + `MAX(cnt_q, cnt_d) * 2, 1 + `BAD_MAX(cnt_q, cnt_d) * 2);
    $display("SQ(1+2)=%0d  BAD_SQ(1+2)=%0d", `SQ(1+2), `BAD_SQ(1+2));
    $display("DATA_W=%0d  stringified: %s", `DATA_W, `STR(cnt_q + 1));
    `CHECK(cnt_q < 8, "cnt_q out of range")
    `CHECK(cnt_d == 0)                // uses the default message
`ifdef FAST_SIM
    $display("FAST_SIM build");
`elsif GATE_SIM
    $display("GATE_SIM build");
`else
    $display("default RTL build");
`endif
  end
endmodule""", "m1.sv - macros with arguments, a default argument, "
               "stringification, token pasting and conditional compilation.")
    out(["MAX=9  1+MAX*2=19  1+BAD_MAX*2=9",
         "SQ(1+2)=9  BAD_SQ(1+2)=5",
         "DATA_W=32  stringified: cnt_q + 1",
         "ERROR m1.sv:15: cnt_q out of range",
         "ERROR m1.sv:16: check failed",
         "default RTL build"],
        "iverilog -g2012 -Wall m1.sv && vvp. With -DGATE_SIM the last line "
        "becomes \"GATE_SIM build\".")
    p("Read the results carefully - each line illustrates a rule:")
    bul(["`BAD_MAX` expands to `1 + cnt_q > cnt_d ? cnt_q : cnt_d * 2`. "
         "Because `+` binds tighter than `>` and `?:` binds loosest, this is "
         "`(10 > 3) ? 9 : 6` = 9. **Parenthesise the whole body and every use "
         "of every argument**, as `MAX` and `SQ` do.",
         "`BAD_SQ(1+2)` expands to `1+2 * 1+2` = 5, not 9. The argument is "
         "text, not a value.",
         "The SystemVerilog **stringification** escape (a grave accent "
         "followed by a double quote) lets the macro argument be substituted "
         "inside a string literal; without it, text inside quotes is never "
         "substituted. The escape (grave accent + backslash + double quote) "
         "produces a literal quote inside such a string.",
         "The **token-pasting** escape (two grave accents) joins text "
         "without whitespace: `name`, the escape and `_q` with name = cnt "
         "become the single identifier `cnt_q`. It is the basis of register-bank and "
         "UVM field macros.",
         "`__FILE__` and `__LINE__` expand to the file and line **where the "
         "macro is used** (lines 15 and 16), which makes them ideal in "
         "checker macros."])
    h3("Redefinition and undef")
    p("A macro may be redefined; the new text applies from that point on "
      "(most tools warn). `undef NAME` removes one definition and "
      "`undefineall` (1800-2009) removes all of them. Because macros are "
      "global across files, a macro defined in one IP's file is visible - "
      "and can be clobbered - in every file compiled after it:")
    vcode(r"""`define W 8
module ud1; initial $display("ud1 sees W=%0d", `W); endmodule
`undef W
`define W 16                         // redefinition (tools may warn if not undef'd)
module ud2; initial $display("ud2 sees W=%0d", `W); endmodule
module udt; ud1 a(); ud2 b(); endmodule""", "ud.v - the value of a macro "
                                            "depends on where in the text it "
                                            "is used, not on the hierarchy.")
    out(["ud1 sees W=8", "ud2 sees W=16"], "Icarus Verilog 12.")
    box("warn", "Pitfall: global macro names collide between IPs",
        "Two vendors' IPs both define `WIDTH` or `ADDR_BITS`. Whichever file "
        "is compiled last wins for every file after it, and the result "
        "changes when the file list is reordered. Rules used by every SoC "
        "team: prefix every macro with the IP name (`DMA_ADDR_W`); prefer "
        "parameters and package constants (Chapter 15) for anything that is "
        "a value; `undef` local helper macros at the end of the file that "
        "defines them.")

    # ------------------------------------------------------------------
    h2("Conditional compilation")
    p("`ifdef NAME` compiles the following text if a macro called NAME is "
      "defined (its value is irrelevant); `ifndef` is the opposite; `elsif` "
      "and `else` provide alternatives and `endif` closes the group. Groups "
      "may nest. The text in a group that is not selected is skipped by the "
      "preprocessor and need only be lexically valid. Macros are usually "
      "defined from the command line: `+define+NAME=value` (VCS, Xcelium, "
      "Questa) or `-DNAME=value` (Icarus, Verilator, Yosys).")
    tbl(["Typical guard", "Used for"],
        [["`ifdef SYNTHESIS` / `ifndef SYNTHESIS`", "Excluding "
          "simulation-only code (assertions, $display, models) from "
          "synthesis. Most synthesis tools define SYNTHESIS automatically; "
          "Yosys does, and Verilator defines VERILATOR"],
         ["`ifdef GATE_SIM`", "Different stimulus or checks for gate-level "
          "simulation (e.g. SDF annotation, X-handling)"],
         ["`ifdef ASIC` / `ifdef FPGA`", "Technology selection: SRAM macro "
          "wrapper vs. inferred block RAM, clock gating cell vs. enable"],
         ["`ifdef NO_ASSERT`", "Turning checkers off in long runs"],
         ["Include guard `ifndef X_VH` `define X_VH` ... `endif`",
          "Making a header safe to include more than once"]],
        widths=[40, 60])
    box("warn", "Pitfall: ifdef-ed RTL is a sim/synth mismatch generator",
        "Code under `ifndef SYNTHESIS` is simulated but never built. If it "
        "contains anything that affects functionality - an initial value, a "
        "forced signal, a behavioural model - the netlist behaves "
        "differently from the RTL you verified. Keep such regions to pure "
        "observation (messages, assertions, coverage), and make lint check "
        "both configurations. Prefer generate-if on a parameter for "
        "legitimate architectural variants: both branches are then parsed and "
        "type-checked by every tool, and the choice is visible in the "
        "hierarchy.")

    # ------------------------------------------------------------------
    h2("include and include guards")
    p("`include \"file\"` inserts the complete contents of the file in "
      "place of the directive, exactly as if it had been typed there. The "
      "file is searched first relative to the current directory (tool "
      "dependent: the current working directory or the including file's "
      "directory) and then in the include directories given with "
      "`+incdir+dir` or `-I dir`. The angle-bracket form `include <file>` "
      "(1800-2009) searches only the tool's own library directories. "
      "Includes may nest (the LRM requires at least 15 levels).")
    p("Use includes for **declarations shared textually**: macro headers, "
      "register address maps generated from IP-XACT, and - in "
      "SystemVerilog - class files that are included into one package. Do "
      "**not** include module definitions into other modules' files; list "
      "them on the command line instead, so that every module is compiled "
      "exactly once. Every header must have an **include guard**, as "
      "`defs.vh` above does; otherwise a second inclusion redefines every "
      "macro (a warning) or declares every item twice (an error).")

    # ------------------------------------------------------------------
    h2("timescale: time units, precision and compile-order dependence")
    p("`timescale unit / precision` gives delays in the following modules a "
      "**time unit** (what `#1` means) and a **precision** (to what "
      "granularity delays are rounded). Both are 1, 10 or 100 followed by "
      "s, ms, us, ns, ps or fs, and the precision must be at least as fine "
      "as the unit. The simulator's global time step is the finest "
      "precision of any module in the design. Delays are rounded to the "
      "module's precision; `$time` returns the current time **rounded to "
      "the module's unit** as a 64-bit integer, `$realtime` returns it as a "
      "real in units, and `%t` formats a time according to `$timeformat` "
      "(Chapter 10).")
    vcode(r"""`timescale 1ns/100ps
module ts1;
  initial begin
    #1.55 $display("ts1: $time=%0d $realtime=%0.2f", $time, $realtime);
    #0.04 $display("ts1: after #0.04 more, $realtime=%0.2f", $realtime);
  end
endmodule""", "ts1.v - rounding to the precision.")
    vcode(r"""module ts2;                       // no `timescale of its own!
  initial #10 $display("ts2: #10 done; $realtime=%0.1f in ts2 units", $realtime);
endmodule""", "ts2.v - a file that relies on whatever timescale is in "
               "effect when it is compiled.")
    vcode(r"""module tstop;
  ts1 a(); ts2 b();
  initial begin
    $timeformat(-9, 1, " ns", 12);
    #20 $display("tstop: simulation time is %t", $realtime);
  end
endmodule""", "tstop.v - also has no timescale.")
    out(["== iverilog ts1.v ts2.v tstop.v ==",
         "ts1: $time=2 $realtime=1.60",
         "ts1: after #0.04 more, $realtime=1.60",
         "ts2: #10 done; $realtime=10.0 in ts2 units",
         "tstop: simulation time is       20.0 ns",
         "== iverilog ts2.v tstop.v ts1.v ==",
         "warning: Found both default and explicit timescale based delays. Use",
         "       : -Wtimescale to find the design element(s) with no explicit",
         "       : timescale.",
         "ts1: $time=2 $realtime=1.60",
         "ts1: after #0.04 more, $realtime=1.60",
         "ts2: #10 done; $realtime=10.0 in ts2 units",
         "tstop: simulation time is 20000000000.0 ns"],
        "Same three files, two compile orders, different simulations.")
    p("The first run shows the rounding rules: `#1.55` with 100 ps "
      "precision becomes 1.6 ns, `$time` rounds 1.6 to 2, and `#0.04` "
      "rounds to zero delay. The second run shows the **compile-order "
      "dependence**. In the first order, ts2 and tstop inherit `1ns/100ps` "
      "from ts1 because the directive is still in effect. In the second "
      "order they are compiled before any `timescale` and receive the "
      "tool's default (1 s in Icarus), so `#20` in tstop now means 20 "
      "seconds. The LRM says it is an error for some modules to have a "
      "timescale and others not; most tools only warn, and the behaviour of "
      "modules without one is tool-specific.")
    box("key", "Robust time units",
        "Put a `timescale` directive in **every** file that contains delays "
        "(or in none, and give the default on the command line - for "
        "example Verilator's `--timescale 1ns/1ps` or the `-timescale` "
        "option of the commercial simulators - which applies only to files "
        "without one). "
        "In SystemVerilog, prefer the `timeunit 1ns; timeprecision 1ps;` "
        "declarations inside the module or package: they belong to the "
        "scope, not to the compilation order. Choose a precision fine "
        "enough for your fastest clock (1 ps for multi-GHz designs) but no "
        "finer than needed - a 1 fs global precision slows some simulators "
        "measurably.")
    tbl(["Symptom", "Likely timescale cause"],
        [["Clock runs 1000x too slow or fast in one sub-block",
          "That file compiled with a different inherited timescale"],
         ["Gate-level sim: all cell delays are zero or huge",
          "Library cell files carry their own timescale (often 1ns/1ps) that "
          "differs from the SDF TIMESCALE or the testbench"],
         ["`#0.5` behaves like `#0` or `#1`", "Precision coarser than the "
          "delay: rounded"],
         ["Waveform timestamps disagree with printed $time",
          "$time is rounded to the unit of the module that calls it"]],
        widths=[45, 55])

    # ------------------------------------------------------------------
    h2("default_nettype, resetall, celldefine and unconnected_drive")
    p("Verilog creates an **implicit net** whenever an undeclared identifier "
      "is used in a port connection or on the left of a continuous "
      "assignment (Chapter 3). By default the implicit net is a 1-bit "
      "`wire`, which turns every typo into a silent floating signal. "
      "`default_nettype none` disables implicit nets so that the typo "
      "becomes a compile error:")
    vcode(r"""`ifdef STRICT
`default_nettype none
`endif
module and2 (input a, b, output y); assign y = a & b; endmodule
module dn;
  reg a = 1, b = 1;
  wire y;
  and2 u (.a(a), .b(b), .y(y_out));   // typo: y_out was never declared
  initial #1 $display("y=%b", y);
endmodule
`default_nettype wire                 // restore for files compiled after this one""",
         "dn.v - an implicit net hides a typo.")
    out(["== default ==",
         "dn.v:8: warning: implicit definition of wire 'y_out'.",
         "y=z",
         "== -DSTRICT ==",
         "dn.v:8: error: Net y_out is not defined in this context.",
         "dn.v:8: error: Output port expression must support continuous assignment.",
         "dn.v:8:      : Port 3 (y) of and2 is connected to y_out",
         "2 error(s) during elaboration."], "Icarus Verilog 12 with -Wall.")
    p("Note the last line of `dn.v`: because the directive stays in effect "
      "for the rest of the compilation, a file that sets `none` should "
      "restore `wire` at its end, otherwise third-party files compiled "
      "later - which often rely on implicit nets in port lists of the "
      "Verilog-1995 style - stop compiling. Other values are `tri`, `tri0`, "
      "`tri1`, `wand`, `wor`, `triand`, `trior`, `trireg` and (1364-2005) `uwire`.")
    tbl(["Directive", "Effect and use"],
        [["`resetall`", "Resets every directive except text macros to its "
          "default (timescale, default_nettype, celldefine, "
          "unconnected_drive). Some teams start every file with it; it must "
          "not appear inside a module."],
         ["`celldefine` ... `endcelldefine`", "Marks the enclosed modules "
          "as **cells**. Tools use it to treat them as leaves: `$dumpvars` "
          "and coverage can exclude them, PLI's `acc_object_of_type(accCell)` "
          "and VPI's `vpiCellInstance` report them. Every standard-cell "
          "simulation library uses it (Chapter 9)."],
         ["`unconnected_drive pull1` / `pull0` ... `nounconnected_drive`",
          "Unconnected **input** ports of modules in the region are pulled "
          "to 1 or 0 instead of floating to z. Found in old libraries; "
          "explicit tie-offs are better practice."],
         ["`begin_keywords \"1364-2005\"` ... `end_keywords`", "Parses the "
          "enclosed code with the reserved words of that standard, so that "
          "legacy code using identifiers such as `logic` or `bit` still "
          "compiles in a SystemVerilog tool."],
         ["`pragma name ...`", "Standard syntax for tool pragmas; IEEE "
          "1364-2005 defines `pragma protect` for IP encryption envelopes."]],
        widths=[33, 67])

    # ------------------------------------------------------------------
    h2("line, __FILE__ and __LINE__")
    p("`line number \"file\" level` tells the compiler to report subsequent "
      "lines as coming from another file and line - used by code generators "
      "(register-map generators, SystemVerilog-to-Verilog converters, "
      "Chisel/SpinalHDL emitters) so that error messages point to the "
      "original source. The level is 0, 1 (entering an include file) or 2 "
      "(leaving one). SystemVerilog's `__FILE__` and `__LINE__` expand to a "
      "string literal and a decimal number and follow any `line` directive:")
    vcode(r"""module ln;
  initial begin
    $display("A: %s line %0d", `__FILE__, `__LINE__);
`line 100 "generated_regs.v" 0
    $display("B: %s line %0d", `__FILE__, `__LINE__);
  end
endmodule""", "ln.v")
    out(["A: ln.v line 3", "B: generated_regs.v line 100"],
        "Icarus Verilog 12.")

    # ------------------------------------------------------------------
    h2("Macro pitfalls and good practice")
    p("Because macros are text, a macro that expands to several statements "
      "behaves differently from a function call in control flow:")
    vcode(r"""`define INC2_BAD(v)  v = v + 1; v = v + 1;
`define INC2(v)      begin v = v + 1; v = v + 1; end
module mp;
  integer x, y;
  initial begin
    x = 0; y = 0;
    if (0) `INC2_BAD(x)      // expands to: if (0) x = x + 1; x = x + 1;
    if (0) `INC2(y)          // whole body is guarded
    $display("x=%0d (expected 0)  y=%0d", x, y);
  end
endmodule""", "mp.v - a multi-statement macro under an if.")
    out(["x=1 (expected 0)  y=0"], "Icarus Verilog 12.")
    tbl(["Pitfall", "Remedy"],
        [["Operator precedence inside the expansion", "Parenthesise the "
          "body and each argument use"],
         ["Argument evaluated twice (`MAX(i++, j)`) - side effects doubled",
          "Use a function; macros are not functions"],
         ["Multi-statement body under `if`/`else`", "Wrap the body in `begin ... "
          "end` (the C idiom `do begin ... end while (0)` is also legal "
          "SystemVerilog)"],
         ["Trailing semicolon: `MACRO(x);` adds an empty statement, which "
          "breaks `if (c) M(x); else ...`", "Decide once whether the macro "
          "includes the semicolon and be consistent"],
         ["Name collisions between IPs; redefinition order", "Prefix "
          "names; `undef` local helpers; use packages"],
         ["Comments inside a macro body: a `//` comment ends the macro "
          "text at the end of that line", "Use `/* */` inside multi-line "
          "macros, or put comments outside"],
         ["Space between name and `(` in the definition", "`define F (x) "
          "x` defines F with **no** argument whose text is `(x) x`"],
         ["Macros are invisible in waveforms and hard to debug", "Keep them "
          "small; most tools can write out the preprocessed text (for "
          "example `iverilog -E`, `verilator -E`)"]],
        widths=[55, 45])
    box("expert", "Where macros are the right tool",
        "UVM's `uvm_info`, `uvm_error` and field-automation macros; "
        "assertion shorthands such as `ASSERT_KNOWN(name, sig, clk, rst)` "
        "(used in OpenTitan and many SoC code bases) that expand into a "
        "labelled concurrent assertion and capture `__FILE__`/`__LINE__`; "
        "register-bank declarations built with token pasting; and "
        "portable wrappers around vendor-specific constructs. Everything "
        "that is merely a constant should be a parameter or a package "
        "`localparam`: it has a type, a scope, and it shows up in the "
        "debugger.")

    h2("Summary")
    bul(["Directives are processed before parsing and stay in effect across "
         "file boundaries until changed; compile order therefore matters.",
         "Macros are pure text substitution: parenthesise, wrap statements "
         "in begin/end, prefix names, `undef` helpers.",
         "SystemVerilog adds default macro arguments, stringification with "
         "the grave-accent-quote escape, token pasting with a double grave "
         "accent, `__FILE__`/`__LINE__` and `undefineall`.",
         "`ifdef` selects code; keep `ifndef SYNTHESIS` regions free of "
         "functional behaviour.",
         "Every header needs an include guard; include declarations, not "
         "modules.",
         "The `timescale` directive sets unit/precision; modules without "
         "one inherit from whatever was compiled earlier - use it in every "
         "file or use `timeunit`/`timeprecision`.",
         "`default_nettype none` turns implicit-net typos into errors - "
         "restore `wire` at the end of the file.",
         "`celldefine` marks library cells; `line` and `resetall` exist "
         "for code generators and hygiene."])
    h2("Exercises")
    bul(["Write a macro `CLAMP(x, lo, hi)` that is safe against precedence "
         "problems. Show a call for which it still misbehaves because an "
         "argument has a side effect.",
         "A macro DBL takes one argument x and its text is `x+x`. Predict "
         "the value of the expression `3*DBL(2)` (DBL invoked with its "
         "grave accent) and verify it with Icarus.",
         "Two files are compiled in the order a.v, b.v. a.v starts with "
         "`timescale 1ns/1ps` and b.v has no timescale but contains `#5`. "
         "What does `#5` mean in b.v? What if the order is reversed? How "
         "do you make it order-independent?",
         "Write a `DECLARE_REG(name, width, rst)` macro that uses token "
         "pasting to declare `name_q` and `name_d` and a flop with "
         "asynchronous reset to `rst`. Use it twice in a module and simulate.",
         "Explain why wrapping a flop's power-up value `initial q = 0;` in "
         "an ifndef SYNTHESIS region is dangerous, and what the correct "
         "design fix is.",
         "Your SoC compiles 300 third-party files. After adding a new IP, a "
         "previously clean block reports \"implicit net\" errors. What "
         "directive is the most likely culprit and how do you confirm it?"],
        ordered=True)


# =============================================================================
#   Chapter 9 - Gate-level modelling: primitives, UDPs, delays, specify, timing
# =============================================================================
def ch9():
    chapter("Gate-Level Modelling: Primitives, UDPs, Delays, Specify Blocks "
            "and Timing Checks")
    p("Nobody designs a modern SoC by instantiating AND gates. Yet the "
      "constructs in this chapter are executed billions of times a day: "
      "every **standard-cell simulation library** is written with them, "
      "every **synthesized netlist** is a gate-level Verilog file that "
      "instantiates those cells, and every **gate-level simulation (GLS)** "
      "with **SDF back-annotation** relies on specify blocks and timing "
      "checks. A DV or DFT engineer who debugs GLS, a physical-design "
      "engineer who reads a netlist, and a library engineer who writes cell "
      "models all need to read this part of the language fluently. It is "
      "also a favourite source of interview questions (inertial delay, "
      "UDP tables, $setuphold, notifiers).")
    diagram([
        "  RTL --synthesis--> gate-level netlist (.v) -- instantiates --> std-cell library (.v)",
        "                          |                                      | primitives, UDPs,",
        "                          | place & route, STA                   | specify blocks,",
        "                          v                                      | timing checks",
        "                     SDF file (delays + limits) ---$sdf_annotate--+",
        "                                                                  v",
        "                                     gate-level simulation with real timing",
    ], "Where gate-level constructs live in the ASIC flow.")

    # ------------------------------------------------------------------
    h2("Built-in gate and switch primitives")
    p("Verilog has 26 built-in **primitives**. They are instantiated like "
      "modules but with three differences: the instance name is optional, "
      "the **output terminal(s) come first**, and ports can only be "
      "connected by position. Inputs may be driven by expressions. Every "
      "primitive terminal is scalar (an array of instances can be used for "
      "vectors).")
    tbl(["Group", "Primitives", "Terminal order", "Notes"],
        [["N-input gates", "`and nand or nor xor xnor`", "(out, in1, in2, "
          "...)", "Any number of inputs; z on an input is treated as x"],
         ["N-output gates", "`buf not`", "(out1, ..., outN, in)",
          "One input fans out to several outputs"],
         ["Three-state", "`bufif0 bufif1 notif0 notif1`", "(out, in, "
          "ctrl)", "Output z when not enabled; L/H values when ctrl is x"],
         ["MOS switches", "`nmos pmos rnmos rpmos`", "(out, data, gate)",
          "Unidirectional; r-versions reduce strength"],
         ["CMOS switches", "`cmos rcmos`", "(out, data, ngate, pgate)",
          "Transmission gate"],
         ["Bidirectional", "`tran rtran tranif0 tranif1 rtranif0 "
          "rtranif1`", "(io1, io2 [, ctrl])", "Pass values both ways; no "
          "delay on tran/rtran"],
         ["Pull sources", "`pullup pulldown`", "(out)", "Drive pull1/pull0 "
          "strength"]],
        widths=[16, 31, 20, 33])
    vcode(r"""`timescale 1ns/1ps
module mux2_gates (output y, input a, b, s);    // output first for primitives style
  wire sn, t0, t1;
  not #1       g0 (sn, s);
  and #(2, 1)  g1 (t0, a, sn);                  // rise 2, fall 1
  and #(2, 1)  g2 (t1, b, s);
  or  #1       g3 (y, t0, t1);
endmodule

module gp;
  reg a, b, s, en;
  wire y, bus;
  mux2_gates m (y, a, b, s);
  bufif1 #(1, 1, 3) d0 (bus, a, en);            // rise, fall, turn-off (to z)
  bufif1            d1 (bus, b, ~en);           // second driver: enabled when en=0
  initial begin
    $timeformat(-9, 0, "ns", 5);
    $monitor("%4t a=%b b=%b s=%b en=%b | y=%b bus=%b", $time, a, b, s, en, y, bus);
    a = 1; b = 0; s = 0; en = 1;
    #10 s = 1;
    #10 en = 0;
    #10 b = 1'bx;
    #10 $finish;
  end
endmodule""", "gp.v - a gate-level multiplexer with rise/fall delays and a "
               "two-driver three-state bus.")
    out([" 0ns a=1 b=0 s=0 en=1 | y=x bus=x",
         " 1ns a=1 b=0 s=0 en=1 | y=x bus=1",
         " 4ns a=1 b=0 s=0 en=1 | y=1 bus=1",
         "10ns a=1 b=0 s=1 en=1 | y=1 bus=1",
         "13ns a=1 b=0 s=1 en=1 | y=0 bus=1",
         "20ns a=1 b=0 s=1 en=0 | y=0 bus=x",
         "23ns a=1 b=0 s=1 en=0 | y=0 bus=0",
         "30ns a=1 b=x s=1 en=0 | y=0 bus=x",
         "32ns a=1 b=x s=1 en=0 | y=x bus=x",
         "gp.v:23: $finish called at 40000 (1ps)"], "Icarus Verilog 12.")
    p("Trace the delays: at 0 ns `sn` becomes 1 after 1 ns, `t0` rises 2 ns "
      "later and `y` 1 ns after that - so y is x until 4 ns. At 10 ns s "
      "rises: `sn` falls at 11, `t0` falls (fall delay 1) at 12, y falls at "
      "13. At 20 ns the second driver switches on immediately (no delay) "
      "while the first needs its **turn-off delay** of 3 ns to release the "
      "bus: for 3 ns two strong drivers fight and the bus is x - the "
      "gate-level picture of **bus contention**, which real hardware turns "
      "into crowbar current. Finally, x on b propagates through `and` "
      "because s selects b.")
    h3("Logic tables and switch-level modelling")
    vcode(r"""module andx;
  reg a, b; wire y_and, y_or, y_xor;
  and (y_and, a, b); or (y_or, a, b); xor (y_xor, a, b);
  initial begin
    $display(" a b | and or xor");
    a = 0; b = 1'bx; #1 $display(" %b %b |  %b   %b   %b", a, b, y_and, y_or, y_xor);
    a = 1; b = 1'bx; #1 $display(" %b %b |  %b   %b   %b", a, b, y_and, y_or, y_xor);
    a = 1; b = 1'bz; #1 $display(" %b %b |  %b   %b   %b", a, b, y_and, y_or, y_xor);
  end
endmodule""", "andx.v - controlling values beat x; z inputs act as x.")
    out([" a b | and or xor", " 0 x |  0   x   x", " 1 x |  x   1   x",
         " 1 z |  x   1   x"], "Icarus Verilog 12.")
    p("Switch primitives model transistors and propagate **strength** "
      "(Chapter 3) as well as value. `nmos` conducts when its gate is 1, "
      "`pmos` when it is 0; a `supply` or `strong` input passes through as "
      "`strong`, while the resistive `r` versions reduce the strength by "
      "one or more levels (strong to pull, pull to weak, ...). This is how "
      "library developers model pass-gate logic, and how analog-ish "
      "structures such as pads with keepers or wired-OR open-drain buses "
      "are simulated.")
    vcode(r"""module sw;
  reg  in, ctl;
  wire n_out, p_out, c_out;
  supply1 vdd; supply0 gnd;
  nmos (n_out, in, ctl);            // passes 'in' when ctl=1
  pmos (p_out, in, ctl);            // passes 'in' when ctl=0
  cmos (c_out, in, ctl, ~ctl);      // transmission gate: nmos gate ctl, pmos gate ~ctl
  // CMOS inverter from two switches
  wire inv_y;
  pmos (inv_y, vdd, in);
  nmos (inv_y, gnd, in);
  // bidirectional pass switch with strength reduction on the resistive version
  wire l, r; reg drv;
  assign (strong0, strong1) l = drv;
  rtran (l, r);                     // r sees drv with strength reduced (strong->pull)
  initial begin
    in = 1; ctl = 1; drv = 1;
    #1 $display("ctl=1: nmos=%b pmos=%b cmos=%b inv(1)=%b r=%v",
                n_out, p_out, c_out, inv_y, r);
    ctl = 0; in = 0;
    #1 $display("ctl=0: nmos=%b pmos=%b cmos=%b inv(0)=%b l=%v",
                n_out, p_out, c_out, inv_y, l);
  end
endmodule""", "sw.v - switch-level primitives; %v prints the strength.")
    out(["ctl=1: nmos=1 pmos=z cmos=1 inv(1)=0 r=Pu1",
         "ctl=0: nmos=z pmos=0 cmos=z inv(0)=1 l=St1"], "Icarus Verilog 12.")
    box("note", "Switch-level in practice",
        "Synthesis tools ignore switch primitives, and Verilator does not "
        "model strengths. Switch-level code survives in standard-cell and "
        "I/O-pad simulation models, in custom-circuit (full-custom SRAM, "
        "register file) behavioural views, and in mixed-signal "
        "testbenches. For digital SoC work, being able to read it is enough.")

    # ------------------------------------------------------------------
    h2("User-defined primitives (UDPs)")
    p("A **UDP** describes a new primitive with a truth table. UDPs are "
      "evaluated very efficiently by simulators, which is why vendors model "
      "the internal state element of every flop and latch in a cell library "
      "as a UDP. The rules (1364-2005 clause 8, 1800-2017 clause 29):")
    bul(["A UDP has exactly **one scalar output**, listed first, and one or "
         "more scalar inputs (at least 9 must be supported for sequential, "
         "10 for combinational UDPs). Ports cannot be vectors or `inout`.",
         "Table values are 0, 1 and x only; a z on an input is treated as "
         "x. The output can never be z.",
         "**Combinational** UDP rows are `inputs : output;`. Any input "
         "combination that matches no row produces **x**.",
         "**Sequential** UDPs declare the output as `reg`, may give it an "
         "`initial` value, and have rows `inputs : current_state : "
         "next_state;`. A next state of `-` means \"no change\".",
         "Sequential rows may be **level-sensitive** or **edge-sensitive**: "
         "an edge such as `(01)` or the shorthand `r` (rise), `f` (fall), "
         "`p` (potential positive edge: 01, 0x, x1), `n` (potential negative "
         "edge) or `*` (any change). At most one edge per row. Level-"
         "sensitive rows take precedence over edge rows when both match.",
         "`?` matches 0, 1 or x; `b` matches 0 or 1."])
    vcode(r"""primitive udp_mux2 (y, s, a, b);      // combinational UDP: output first, scalar ports
  output y; input s, a, b;
  table
  // s  a  b  :  y
     0  0  ?  :  0;
     0  1  ?  :  1;
     1  ?  0  :  0;
     1  ?  1  :  1;
     x  0  0  :  0;                   // pessimism reduction: equal inputs -> known
     x  1  1  :  1;
  endtable                            // any other combination -> x
endprimitive

primitive udp_dff (q, clk, d, rst_n);  // sequential, edge-sensitive UDP
  output q; reg q; input clk, d, rst_n;
  initial q = 1'b0;
  table
  // clk   d  rst_n : q(now) : q(next)
     ?     ?  0     :  ?     :  0;     // async reset (level)
     (01)  0  1     :  ?     :  0;     // rising edge captures d
     (01)  1  1     :  ?     :  1;
     (0?)  1  1     :  1     :  1;     // 0->x with d==q: stays (pessimism reduction)
     (0?)  0  1     :  0     :  0;
     (?0)  ?  1     :  ?     :  -;     // falling edge: no change
     ?     *  1     :  ?     :  -;     // d changes without clock edge: no change
     ?     ?  (?1)  :  ?     :  -;     // reset release: no change
  endtable
endprimitive""", "udp.v (part 1) - a combinational and a sequential UDP.")
    vcode(r"""module tb_udp;
  reg s, a, b, clk, d, rst_n; wire y, q;
  udp_mux2 m (y, s, a, b);
  udp_dff  f (q, clk, d, rst_n);
  initial begin
    s = 1'bx; a = 1; b = 1; #1 $display("mux s=x a=b=1 -> y=%b", y);
    b = 0;               #1 $display("mux s=x a=1 b=0 -> y=%b", y);
    clk = 0; d = 1; rst_n = 1;
    #1 clk = 1; #1 $display("after posedge d=1: q=%b", q);
    d = 0;      #1 $display("d=0, no edge: q=%b", q);
    clk = 0;    #1 $display("negedge: q=%b", q);
    rst_n = 0;  #1 $display("rst_n=0: q=%b", q);
  end
endmodule""", "udp.v (part 2) - testbench.")
    out(["mux s=x a=b=1 -> y=1", "mux s=x a=1 b=0 -> y=x",
         "after posedge d=1: q=1", "d=0, no edge: q=1", "negedge: q=1",
         "rst_n=0: q=0"], "Icarus Verilog 12.")
    p("The two `x` rows of the multiplexer are a deliberate **X-pessimism "
      "reduction**: real hardware outputs 1 when both data inputs are 1, "
      "whatever the select, and a good library model says so. The `(0?)` "
      "rows of the flop do the same for a clock going to x when D already "
      "equals Q. Library quality is judged partly by how carefully these "
      "rows are written, because every missing row becomes an x in GLS.")
    box("warn", "Pitfall: incomplete sequential tables",
        "Any combination of input values and edges that matches no row sets "
        "the output to **x**. Forgetting the \"data changes while the clock "
        "is stable: no change\" row (`? * 1 : ? : -;`) makes the flop go x "
        "on every data toggle - a bug that only shows up in gate-level "
        "simulation. Cover every edge of every input, or use `*` and `?` "
        "rows for the no-change cases.")

    # ------------------------------------------------------------------
    h2("Delays on gates, nets and assignments")
    p("A delay can be attached to a gate instance, a continuous assignment "
      "or a net declaration with `#`. It may have one, two or three values "
      "(for three-state and MOS devices), each of which may be a "
      "**min:typ:max** triplet:")
    tbl(["Delay spec", "0 -> 1", "1 -> 0", "-> z", "-> x"],
        [["`#d`", "d", "d", "d", "d"],
         ["`#(r, f)`", "r", "f", "min(r, f)", "min(r, f)"],
         ["`#(r, f, t)`", "r", "f", "t", "min(r, f, t)"]],
        widths=[25, 15, 15, 20, 25],
        caption="Which delay is used for which output transition "
                "(1364-2005 7.14). Transitions from x use the pessimistic "
                "(shortest) rule analogously.")
    vcode(r"""`timescale 1ns/1ps
module mtm;
  reg a = 0; wire y; realtime t0;
  buf #(1:2:3, 4:5:6) g (y, a);        // (rise min:typ:max, fall min:typ:max)
  initial begin
    #10 a = 1; t0 = $realtime; @(y) $display("rise delay = %0.1f ns", $realtime - t0);
    #10 a = 0; t0 = $realtime; @(y) $display("fall delay = %0.1f ns", $realtime - t0);
  end
endmodule""", "mtm.v - one source, three corners. The simulator chooses the "
               "corner (Icarus -Tmin|-Ttyp|-Tmax; commercial tools "
               "+mindelays/+typdelays/+maxdelays).")
    out(["-Tmin: rise delay = 1.0 ns fall delay = 4.0 ns",
         "-Ttyp: rise delay = 2.0 ns fall delay = 5.0 ns",
         "-Tmax: rise delay = 3.0 ns fall delay = 6.0 ns"],
        "for T in min typ max; do iverilog -g2012 -T$T -o mtm mtm.v && "
        "echo \"-T$T:\" $(vvp mtm); done")
    p("A **net delay** (`wire #3 w;`) delays every change of the net's "
      "resolved value, in addition to the delays of its drivers - a crude "
      "model of wire delay. It is rarely written by hand; in GLS, "
      "interconnect delays come from SDF `INTERCONNECT` entries instead.")
    h3("Inertial versus transport delay")
    p("Gate delays, continuous-assignment delays and net delays are "
      "**inertial**: when the input changes again before the scheduled "
      "output change has happened, the pending change is cancelled, so "
      "pulses shorter than the delay are **filtered** - like a real gate "
      "whose output cannot swing in less than its propagation time. "
      "**Transport** delay passes every pulse, however short, and is "
      "modelled with a non-blocking assignment with an intra-assignment "
      "delay. A delay placed **before** a blocking assignment behaves like "
      "neither: the process sleeps and misses input changes while it waits.")
    vcode(r"""`timescale 1ns/1ns
module dly;
  reg a = 0;
  wire       w_inertial;
  reg        r_transport, r_blocking;
  wire       g_out;
  assign #5 w_inertial = a;                     // continuous assign: inertial
  buf    #5 g (g_out, a);                       // gate: inertial
  always @(a) r_transport <= #5 a;              // NBA intra-delay: transport
  always @(a) #5 r_blocking = a;                // delay BEFORE sampling: misses events
  initial begin
    $monitor("%3t a=%b inertial=%b gate=%b transport=%b blocking=%b",
             $time, a, w_inertial, g_out, r_transport, r_blocking);
    #10 a = 1; #3 a = 0;                        // 3 ns pulse  (< 5 ns delay)
    #10 a = 1; #7 a = 0;                        // 7 ns pulse  (> 5 ns delay)
    #20 $finish;
  end
endmodule""", "dly.v - the four delay behaviours side by side.")
    out(["  0 a=0 inertial=x gate=x transport=x blocking=x",
         "  5 a=0 inertial=0 gate=0 transport=x blocking=x",
         " 10 a=1 inertial=0 gate=0 transport=x blocking=x",
         " 13 a=0 inertial=0 gate=0 transport=x blocking=x",
         " 15 a=0 inertial=0 gate=0 transport=1 blocking=0",
         " 18 a=0 inertial=0 gate=0 transport=0 blocking=0",
         " 23 a=1 inertial=0 gate=0 transport=0 blocking=0",
         " 28 a=1 inertial=1 gate=1 transport=1 blocking=1",
         " 30 a=0 inertial=1 gate=1 transport=1 blocking=1",
         " 35 a=0 inertial=0 gate=0 transport=0 blocking=0",
         "dly.v:16: $finish called at 50 (1ns)"], "Icarus Verilog 12.")
    bul(["The 3 ns pulse at 10-13 ns disappears on the inertial outputs and "
         "appears, shifted by 5 ns, on the transport output (15-18 ns).",
         "The blocking version woke at 10, slept 5 ns and sampled `a` at 15 "
         "- by then a was 0 again, so the pulse is lost and the 13 ns change "
         "was never seen by the waiting process.",
         "The 7 ns pulse passes through all four models.",
         "`transport` and `blocking` stay x until 15/28 ns: `reg a = 0` "
         "initialises a at time 0 **without an event** that the `always "
         "@(a)` processes can see (a time-0 race, Chapter 5)."])
    box("expert", "Pulse control in specify paths",
        "Module path delays (next section) are inertial too, but with finer "
        "control: a pulse shorter than the **reject limit** is filtered, a "
        "pulse between the reject and **error limit** produces an x, and "
        "longer pulses pass. By default both limits equal the path delay; "
        "they can be set per path with `PATHPULSE$` specparams, globally with "
        "options such as `+pulse_r/percent` and `+pulse_e/percent`, or from "
        "SDF (`PATHPULSE`). `pulsestyle_onevent` / `pulsestyle_ondetect` and "
        "`showcancelled` (1364-2001) control when that x appears.")

    # ------------------------------------------------------------------
    h2("Specify blocks and module path delays")
    p("Distributed delays on the gates inside a cell are hard to "
      "characterise. Library vendors instead give each cell **module path "
      "delays** - pin-to-pin delays from an input port to an output port - "
      "in a `specify ... endspecify` block, and keep the functional model "
      "zero-delay. The characterised numbers come from the Liberty (.lib) "
      "file and, after layout, from SDF.")
    tbl(["Construct", "Syntax", "Meaning"],
        [["Parallel connection", "`(A => Y) = d;`", "Bit i of A to bit i of "
          "Y; source and destination must have the same width"],
         ["Full connection", "`(A, B *> Y) = d;`", "Every bit of every "
          "source to every bit of every destination"],
         ["Edge-sensitive path", "`(posedge CK => (Q +: D)) = d;`",
          "Path from a clock edge; `+:`/`-:` give the data polarity "
          "(non-inverting / inverting) for the tool"],
         ["State-dependent path", "`if (S) (A => Y) = d1;` and "
          "`ifnone (A => Y) = d2;`", "Different delays depending on the "
          "state of other inputs (e.g. XOR, mux select)"],
         ["Polarity", "`(A +=> Y)`, `(A -=> Y)`", "Declares a (non-)inverting "
          "path"],
         ["Delay values", "1, 2, 3, 6 or 12 values", "rise/fall/z; 6 values "
          "for 01,10,0z,z1,1z,z0; 12 add the x transitions"],
         ["specparam", "`specparam tpd = 0.12;`", "Constants for the "
          "specify block (not overridable like parameters)"]],
        widths=[20, 36, 44])
    p("If a module has both distributed delays and a path delay for the "
      "same input-output pair, the simulator uses the larger of the path "
      "delay and the distributed delay along that path (1364-2005 14.4). "
      "Icarus applies specify-block delays only when invoked with "
      "`-gspecify`; without it, and in Verilator and synthesis, specify "
      "blocks are ignored.")

    h2("Timing checks and notifiers")
    p("Timing checks are system tasks that may appear only inside a specify "
      "block. They monitor the ports of the cell and report a **violation** "
      "when a timing limit from the library is broken; they do not change "
      "any value by themselves. To make the violation affect simulation, "
      "each check can toggle a **notifier** - a 1-bit `reg` passed as the "
      "last argument - and the cell model uses the notifier to drive its "
      "state element to x. This is how a setup violation in GLS turns into "
      "an x that propagates through the design and makes the test fail.")
    tbl(["Check", "Arguments", "Violation when"],
        [["`$setup`", "(data, ref_edge, limit[, notifier])", "data changes "
          "less than `limit` **before** the reference edge"],
         ["`$hold`", "(ref_edge, data, limit[, notifier])", "data changes "
          "less than `limit` **after** the reference edge (note the swapped "
          "argument order)"],
         ["`$setuphold`", "(ref, data, setup, hold[, notifier, ...])",
          "Either; allows **negative** setup or hold values with the "
          "optional delayed_ref / delayed_data arguments"],
         ["`$recovery`", "(ref, data, limit[, notifier])", "An "
          "asynchronous control (e.g. reset) is released too close "
          "**before** the clock edge (reset-release \"setup\")"],
         ["`$removal`", "(ref, data, limit[, notifier])", "Released too "
          "close **after** the clock edge (reset-release \"hold\")"],
         ["`$recrem`", "(ref, data, rec, rem[, notifier, ...])",
          "Either, with negative-limit support"],
         ["`$width`", "(ref_edge, limit[, threshold, notifier])", "A pulse "
          "starting with ref_edge is narrower than `limit` (min pulse "
          "width)"],
         ["`$period`", "(ref_edge, limit[, notifier])", "Two consecutive "
          "reference edges are closer than `limit`"],
         ["`$skew`, `$timeskew`, `$fullskew`", "(ref, data, limit, ...)",
          "Skew between two signals exceeds the limit"],
         ["`$nochange`", "(ref, data, start, end[, notifier])", "data "
          "changes while ref is at a level (e.g. memory address stable "
          "while WE is high)"]],
        widths=[20, 36, 44])
    p("Timing check events may carry a condition with `&&&`, e.g. "
      "`$setup(D, posedge CK &&& SE_n, 0.05, ntfr);` checks D only when "
      "scan enable is inactive - library models use this to switch between "
      "functional and scan-path checks.")
    h3("How a standard-cell library looks in Verilog")
    vcode(r"""`timescale 1ns/1ps
`celldefine
module NAND2X1 (output Y, input A, B);
  nand g (Y, A, B);                      // zero-delay functional model
  specify
    specparam tpd_rise = 0.12, tpd_fall = 0.08;
    (A => Y) = (tpd_rise, tpd_fall);     // parallel path, rise/fall
    (B => Y) = (0.10, 0.07);
  endspecify
endmodule
`endcelldefine

`celldefine
module DFFX1 (output reg Q, input D, CK);
  reg notifier;
  always @(posedge CK) Q <= D;
  always @(notifier) Q <= 1'bx;          // violation -> corrupt state
  specify
    (posedge CK => (Q +: D)) = (0.20, 0.18);   // edge-sensitive path
    $setup(D, posedge CK, 0.05, notifier);
    $hold (posedge CK, D, 0.03, notifier);
    $width(posedge CK, 0.25);
  endspecify
endmodule
`endcelldefine""", "spec.v (part 1) - two simplified library cells. "
                     "Production libraries model the flop's state with a "
                     "sequential UDP that takes the notifier as an extra "
                     "input, and add scan, set/reset and power pins.")
    vcode(r"""module tb_spec;
  reg a, b, d, ck; wire y, q;
  NAND2X1 u1 (.Y(y), .A(a), .B(b));
  DFFX1   u2 (.Q(q), .D(d), .CK(ck));
  initial begin
    $timeformat(-9, 3, "ns", 9);
    $monitor("%t a=%b b=%b y=%b | d=%b ck=%b q=%b", $realtime, a, b, y, d, ck, q);
    a = 1; b = 1; d = 0; ck = 0;
    #1 a = 0;                            // y rises after 0.12
    #1 a = 1;                            // y falls after 0.08
    #1 d = 1; #1 ck = 1;                 // clean capture
    #1 ck = 0; #1 d = 0; #0.02 ck = 1;   // setup violation: D changed 0.02 before CK
    #1 $finish;
  end
endmodule""", "spec.v (part 2) - testbench with a deliberate setup violation.")
    out(["  0.000ns a=1 b=1 y=x | d=0 ck=0 q=x",
         "  0.070ns a=1 b=1 y=0 | d=0 ck=0 q=x",
         "  1.000ns a=0 b=1 y=0 | d=0 ck=0 q=x",
         "  1.120ns a=0 b=1 y=1 | d=0 ck=0 q=x",
         "  2.000ns a=1 b=1 y=1 | d=0 ck=0 q=x",
         "  2.080ns a=1 b=1 y=0 | d=0 ck=0 q=x",
         "  3.000ns a=1 b=1 y=0 | d=1 ck=0 q=x",
         "  4.000ns a=1 b=1 y=0 | d=1 ck=1 q=x",
         "  4.200ns a=1 b=1 y=0 | d=1 ck=1 q=1",
         "  5.000ns a=1 b=1 y=0 | d=1 ck=0 q=1",
         "  6.000ns a=1 b=1 y=0 | d=0 ck=0 q=1",
         "  6.020ns a=1 b=1 y=0 | d=0 ck=1 q=1",
         "  6.200ns a=1 b=1 y=0 | d=0 ck=1 q=0",
         "spec.v:39: $finish called at 7020 (1ps)"],
        "iverilog -g2012 -gspecify: path delays are applied (0.12 / 0.08 / "
        "0.20 / 0.18 ns) but Icarus parses and ignores timing checks.")
    p("The path delays are exactly the specify values (at time 0 both inputs "
      "switch together and the fall at 0.070 ns uses the faster B arc). The setup violation at "
      "6.020 ns is **not** reported, because Icarus does not execute timing "
      "checks, and the flop cleanly captures 0. **Expected behaviour in a "
      "commercial simulator** (VCS, Xcelium, Questa): a message naming "
      "`$setup`, the instance `tb_spec.u2`, the two event times and the "
      "0.05 ns limit is printed at 6.020 ns, the notifier toggles, and q "
      "becomes x instead of 0 - and stays x until the next clean capture. "
      "Those simulators also offer switches to turn checks off globally "
      "(`+notimingcheck`), to keep the message but not the x "
      "(`+no_notifier`), or to disable them per instance.")

    # ------------------------------------------------------------------
    h2("SDF back-annotation")
    p("The **Standard Delay Format** (IEEE 1497) is the text file in which "
      "static timing analysis (PrimeTime, Tempus) or place-and-route writes "
      "the actual delays of every cell instance and wire in a netlist, "
      "for a specific corner. The simulator reads it with the system task "
      "`$sdf_annotate(\"file.sdf\", scope [, config, log, mtm, scale, "
      "type])` - usually at time 0 in the testbench - and overwrites the "
      "specify-block values of the matching instances. `IOPATH` entries "
      "map to module paths, `INTERCONNECT` to port-to-port wire delays, "
      "and `TIMINGCHECK` entries (`SETUP`, `HOLD`, `SETUPHOLD`, `WIDTH`, "
      "`RECOVERY`, ...) to the limits of the corresponding checks.")
    vcode(r"""(DELAYFILE
  (SDFVERSION "3.0")
  (DESIGN "tb_sdf")
  (TIMESCALE 1ns)
  (CELL (CELLTYPE "NAND2X1") (INSTANCE u1)
    (DELAY (ABSOLUTE
      (IOPATH A Y (0.30:0.35:0.40) (0.20:0.25:0.30))
      (IOPATH B Y (0.30:0.35:0.40) (0.20:0.25:0.30)))))
)""", "top.sdf - rise and fall triplets for both arcs of one NAND instance.")
    vcode(r"""`timescale 1ns/1ps
module NAND2X1 (output Y, input A, B);
  nand g (Y, A, B);
  specify
    (A => Y) = (0.12, 0.08);
    (B => Y) = (0.10, 0.07);
  endspecify
endmodule
module tb_sdf;
  reg a, b; wire y;
  NAND2X1 u1 (.Y(y), .A(a), .B(b));
  initial begin
`ifdef SDF
    $sdf_annotate("top.sdf", tb_sdf);
`endif
    $timeformat(-9, 3, "ns", 9);
    a = 1; b = 1;
    #1 a = 0; @(y) $display("%t y rose  (A->Y)", $realtime);
    #1 a = 1; @(y) $display("%t y fell  (A->Y)", $realtime);
  end
endmodule""", "sdf.v")
    out(["== without SDF ==", "  1.120ns y rose  (A->Y)",
         "  2.200ns y fell  (A->Y)",
         "== with -DSDF ==", "  1.350ns y rose  (A->Y)",
         "  2.600ns y fell  (A->Y)"],
        "iverilog -g2012 -gspecify [-DSDF] sdf.v; vvp (headers echoed by "
        "the run script). The typical values "
        "0.35/0.25 replaced the library's 0.12/0.08.")
    box("warn", "Pitfall: silent SDF mismatches",
        "An SDF entry whose instance path or pin names do not match the "
        "netlist is skipped with a warning buried among thousands of lines, "
        "leaving that cell at its library default delay (often zero). Always "
        "check the annotation log/coverage report (tools print how many "
        "IOPATHs and timing checks were annotated), make sure the SDF "
        "TIMESCALE and the library's `timescale` directives agree, and annotate at the "
        "scope that matches the SDF's DESIGN hierarchy.")

    # ------------------------------------------------------------------
    h2("Gate-level simulation issues")
    p("GLS is slow and painful, so it is run on a small set of tests - reset "
      "and boot, clock and power-mode switching, DFT patterns, and anything "
      "timing-sensitive such as asynchronous interfaces. Its value lies "
      "exactly in the problems RTL simulation cannot see. The recurring "
      "issues are:")
    tbl(["Issue", "What happens", "Typical fix"],
        [["X-pessimism", "A mux or AND-OR tree in the netlist outputs x "
          "where the RTL (and silicon) gives a known value; flops without "
          "reset start at x and never clear", "Reset or initialise all "
          "control flops; review x sources; tool X-propagation options"],
         ["X-optimism in RTL hidden", "RTL `if (x)` took the else branch; "
          "the netlist propagates x and fails", "A real bug - fix the RTL "
          "(Chapter 11)"],
         ["Zero-delay races", "Without SDF, clock-tree buffers make the "
          "clock arrive a delta later than data at some flops: data "
          "races through two stages", "Unit-delay mode or SDF; never "
          "hand-insert #1 in RTL to \"fix\" it"],
         ["Timing checks on synchronizers", "The first flop of a CDC "
          "synchronizer legitimately violates setup; its notifier makes "
          "the whole design x", "Disable checks on those instances (tool "
          "option or SDF/timing-check exclusion list)"],
         ["Negative timing checks", "Libraries use negative setup/hold; "
          "without delayed-signal support the checks are wrong",
          "Enable negative timing check support in the simulator"],
         ["Unannotated or mis-annotated SDF", "Some cells at library "
          "defaults", "Check annotation reports; same netlist version as "
          "the SDF"],
         ["Memories and macros", "SRAM/PLL/analog models have their own "
          "timing and x behaviour", "Use the vendor's verification models "
          "and their documented options"]],
        widths=[20, 44, 36])
    box("key", "What GLS verifies that RTL cannot",
        "Synthesis correctness in the presence of sim/synth mismatches "
        "(Chapter 11), X-propagation from uninitialised state, reset "
        "sequencing, DFT/scan-chain and test-mode logic inserted after RTL, "
        "clock-gating and power-switch cells, and - with SDF - real timing "
        "on paths that STA constrains as exceptions. Equivalence checking "
        "(LEC) covers most of the logical risk far faster, which is why GLS "
        "runs are few but still mandatory before tape-out.")

    h2("Summary")
    bul(["26 built-in primitives: gates, three-state buffers, MOS/CMOS and "
         "bidirectional switches, pullup/pulldown. Output first, positional "
         "connections, optional instance name.",
         "UDPs: one scalar output, table of 0/1/x; unmatched rows give x; "
         "sequential UDPs add current/next state and edge entries; libraries "
         "use them for flops and latches.",
         "Delays: 1/2/3 values, min:typ:max chosen by a tool option; gate, "
         "net and assign delays are inertial; NBA intra-assignment delay is "
         "transport.",
         "Specify blocks give pin-to-pin path delays (=> parallel, *> full, "
         "edge and state-dependent paths) and hold timing checks.",
         "Timing checks ($setup, $hold, $setuphold, $recovery, $removal, "
         "$width, $period, ...) report violations and toggle a notifier that "
         "the model turns into x.",
         "SDF (IEEE 1497) back-annotates real delays and limits via "
         "$sdf_annotate; check the annotation report.",
         "GLS catches x-propagation, reset, DFT and real-timing problems; "
         "its classic traps are x-pessimism, zero-delay races and "
         "synchronizer timing checks."])
    h2("Exercises")
    bul(["Build a 2:1 multiplexer from `nand` gates only, with a delay of "
         "1 ns per gate, and measure (in simulation) the glitch on the output "
         "when the select toggles with both data inputs at 1. Add the "
         "consensus term and show that the glitch disappears.",
         "Write a sequential UDP for a positive-level latch with active-low "
         "asynchronous clear, including pessimism-reduction rows. Test the "
         "clear-while-enabled case.",
         "What does `bufif1 #(2, 3, 5)` do when its control goes from 1 to "
         "0? From 0 to x? Check the LRM table and confirm with Icarus.",
         "A 4 ns pulse drives `assign #5 y = a;` and `always @(a) y2 <= #5 a;`. "
         "Draw both waveforms. Which one models a real buffer, and which one "
         "models a delay line?",
         "Write the specify block for a 2-input XOR cell whose A-to-Y delay "
         "depends on B (state-dependent paths with `if` and `ifnone`), and a "
         "$setuphold check with a negative hold limit for a flop.",
         "Your GLS reset test goes all-x shortly after reset release, but "
         "only with SDF. List three plausible causes and how you would "
         "distinguish them."], ordered=True)


# =============================================================================
#     Chapter 10 - System tasks and functions, file I/O, VCD, PLI/VPI
# =============================================================================
def ch10():
    chapter("System Tasks and Functions, File I/O, VCD and an Introduction "
            "to PLI/VPI")
    p("Identifiers that start with a dollar sign are **system tasks** (used "
      "as statements, like `$display`) and **system functions** (return a "
      "value, like `$clog2`). They are the testbench's interface to the "
      "outside world: printing, reading stimulus files, writing logs and "
      "waveforms, random numbers, command-line options and simulation "
      "control. The standard set is defined in 1364-2005 clause 17 and "
      "1800-2017 clauses 20-21; simulators add their own (`$fsdbDumpvars` "
      "for Verdi waveforms, for example) and users add "
      "more through the **VPI**, the C interface at the end of this "
      "chapter. Except for the conversion and math functions, system tasks "
      "are ignored or rejected by synthesis.")

    # ------------------------------------------------------------------
    h2("Display tasks: $display, $write, $strobe and $monitor")
    tbl(["Task", "When it prints", "Newline", "Typical use"],
        [["`$display`", "Immediately, when executed (Active region)", "Yes",
          "Messages, checks"],
         ["`$write`", "Immediately", "No", "Building a line in pieces"],
         ["`$strobe`", "At the end of the current time step (Postponed "
          "region), with the values **after** all updates of this step",
          "Yes", "Printing settled values of NBA-updated registers"],
         ["`$monitor`", "At the end of every time step in which any of its "
          "arguments changed (except $time)", "Yes", "Quick console traces; "
          "only one $monitor is active at a time"],
         ["`$monitoron` / `$monitoroff`", "Enable/disable the active "
          "monitor; `on` prints immediately", "-", "Quiet phases"],
         ["`$displayb/h/o`, `$writeb`...", "As above with a different "
          "default radix for unformatted arguments", "", "Rarely used"]],
        widths=[22, 43, 10, 25])
    vcode(r"""`timescale 1ns/1ns
module strb;
  reg [3:0] c = 0; reg clk = 0;
  always #5 clk = ~clk;
  always @(posedge clk) c <= c + 1;
  initial begin
    $monitor("%0t monitor : c=%0d", $time, c);      // end of time step, on change only
    @(posedge clk);
    $display("%0t display : c=%0d  (before the NBA update)", $time, c);
    $strobe ("%0t strobe  : c=%0d  (Postponed region)", $time, c);
    @(posedge clk) $monitoroff;
    @(posedge clk) $display("%0t display : c=%0d  (monitor off)", $time, c);
    $monitoron;                                     // prints current values immediately
    #1 $finish;
  end
endmodule""", "strb.v - the same variable seen by three display tasks.")
    out(["0 monitor : c=0",
         "5 display : c=0  (before the NBA update)",
         "5 strobe  : c=1  (Postponed region)",
         "5 monitor : c=1",
         "25 display : c=2  (monitor off)",
         "25 monitor : c=3",
         "strb.v:14: $finish called at 26 (1ns)"], "Icarus Verilog 12.")
    p("At 5 ns `$display` runs in the Active region, before the NBA "
      "`c <= c + 1` has been applied, and prints the old value 0; `$strobe` "
      "and `$monitor` print in the Postponed region and see 1 (Chapter 5). "
      "The same reasoning explains the classic interview question "
      "\"why does my testbench print the value from the previous "
      "cycle?\".")
    h3("Format specifiers")
    tbl(["Spec", "Meaning", "Spec", "Meaning"],
        [["`%b %o %h %d`", "Binary, octal, hex, decimal", "`%e %f %g`",
          "Real: exponent, fixed, shorter of the two"],
         ["`%0d`, `%0h`", "Minimum width (no padding)", "`%t`",
          "Time, formatted by $timeformat"],
         ["`%5d`, `%-5d`", "Field width; left-justify", "`%s`",
          "String (8 bits per character)"],
         ["`%c`", "ASCII character", "`%m`", "Hierarchical name of the "
          "scope (no argument)"],
         ["`%v`", "Net strength (St1, Pu0, HiZ ...)", "`%l`",
          "Library binding (config)"],
         ["`%u`, `%z`", "Unformatted 2-/4-state binary (for files)",
          "`%p` (SV)", "Assignment-pattern format of any aggregate: "
          "struct, array, queue, class handle"],
         ["`%%`", "A literal percent sign", "`\\n \\t \\\\ \\\"`",
          "Newline, tab, backslash, quote"]],
        widths=[16, 34, 16, 34])
    vcode(r"""module fmt;
  reg  [11:0] v  = 12'hA5x;
  reg  signed [7:0] s = -8'sd5;
  real r = 3.14159e3;
  wire (weak1, highz0) w = 1'b1;
  initial begin
    $display("%%b=%b  %%h=%h  %%o=%o  %%d=%d", v, v, v, v);
    $display("width: [%d] [%0d] [%5d] [%-5d]|", 8'd7, 8'd7, 8'd7, 8'd7);
    $display("signed: %d %0d  %h", s, s, s);
    $display("real: %f %0.2f %e %g %10.3f|", r, r, r, r, r);
    $display("char/string: %c %s [%0s]", 8'h41, "hello", "x");
    $display("scope: %m   strength: %v", w);
    $write("no newline... ");
    $write("then newline\n");
  end
endmodule""", "fmt.sv")
    out(["%b=10100101xxxx  %h=a5x  %o=51Xx  %d=   X",
         "width: [  7] [7] [    7] [7    ]|",
         "signed:   -5 -5  fb",
         "real: 3141.590000 3141.59 3.141590e+03 3141.59   3141.590|",
         "char/string: A hello [x]",
         "scope: fmt   strength: We1",
         "no newline... then newline"], "Icarus Verilog 12.")
    bul(["**Default width.** Without a width, `%d` pads to the number of "
         "characters needed for the largest value of the expression (3 for "
         "8 bits: `[  7]`), `%h` and `%b` print all digits. `%0d` removes "
         "the padding - use it in almost every message.",
         "**Unknown digits.** A lower-case `x` or `z` means all bits of that "
         "digit are unknown/high-impedance; an upper-case `X` or `Z` means "
         "only some are. The octal digit `X` above covers bits 01x. With "
         "`%d`, any x bit makes the whole number `X`.",
         "**Signedness.** `%d` of a signed variable prints the negative "
         "value; `%h` always shows the raw two's-complement bits.",
         "**Strings** are packed 8-bit characters; `%s` right-justifies in "
         "the full width of the argument, so a string held in a wide `reg` "
         "gets leading spaces - `%0s` removes them."])
    p("`%p` is SystemVerilog-only and not implemented in Icarus 12; "
      "Verilator handles it:")
    vcode(r"""module pfmt;
  typedef struct { logic [3:0] op; logic [7:0] imm; } instr_t;   // unpacked struct
  typedef enum logic [1:0] {IDLE, BUSY, DONE} st_t;
  instr_t   ins = '{op: 4'h3, imm: 8'h2A};
  int       q[$] = '{1, 2, 3};
  st_t      st   = BUSY;
  initial begin
    $display("ins=%p  q=%p", ins, q);
    $display("st=%s (%0d)  $sformatf -> \"%s\"", st.name(), st,
             $sformatf("op%0d_%h", ins.op, ins.imm));
    $finish;
  end
endmodule""", "pfmt.sv - %p, enum names and $sformatf.")
    out(["ins='{op:'h3, imm:'h2a}  q='{'h1, 'h2, 'h3} ",
         "st=BUSY (1)  $sformatf -> \"op3_2a\"",
         "- pfmt.sv:11: Verilog $finish"],
        "verilator --binary -Wall pfmt.sv && ./obj_dir/Vpfmt")

    # ------------------------------------------------------------------
    h2("Simulation time and control: $time, $realtime, $timeformat, "
       "$finish and $stop")
    p("`$time` returns the current time as a 64-bit integer **in the time "
      "unit of the module that calls it, rounded**; `$stime` returns the "
      "same truncated to 32 bits; `$realtime` returns a `real`, also in the "
      "caller's unit but without rounding. `$timeformat(units, precision, "
      "suffix, min_width)` sets how `%t` prints: `units` is the exponent "
      "(-9 = ns, -12 = ps), `precision` the number of decimals. Before any "
      "`$timeformat` call, `%t` prints in the global simulation precision "
      "with a width of 20.")
    vcode(r"""`timescale 1ns/10ps
module tm;
  initial begin
    #12.345;
    $display("$time=%0d  $stime=%0d  $realtime=%0.3f", $time, $stime, $realtime);
    $display("%%t default   : [%t]", $realtime);
    $timeformat(-6, 4, " us", 12);          // units=us, 4 decimals, suffix, min width
    $display("%%t after fmt : [%t]", $realtime);
    $timeformat(-12, 0, " ps", 0);
    $display("%%t in ps     : [%t]", $time);
  end
endmodule""", "tm.v")
    out(["$time=12  $stime=12  $realtime=12.350",
         "%t default   : [                1235]",
         "%t after fmt : [   0.0123 us]",
         "%t in ps     : [12000 ps]"], "Icarus Verilog 12.")
    p("The delay `#12.345` was rounded to the 10 ps precision (12.35 ns). "
      "The default `%t` shows 1235 **units of the global precision** (10 ps). "
      "The last line is the trap: `$time` had already rounded 12.35 ns to "
      "12 ns, so printing it in picoseconds shows 12000 ps. Pass "
      "`$realtime` to `%t` in **any** design with sub-unit delays.")
    tbl(["Task", "Effect"],
        [["`$finish(n)`", "Ends the simulation. n = 0 prints nothing, 1 "
          "(default) prints time and location, 2 adds memory/CPU statistics. "
          "Final blocks (SV) run."],
         ["`$stop(n)`", "Suspends the simulation and enters the "
          "interactive prompt (in batch mode many tools just stop)"],
         ["`$exit` (SV)", "Ends a program block (Chapter 21)"],
         ["`$fatal(n, msg)` (SV)", "Prints an error and calls "
          "$finish(n); with `$error`, `$warning`, `$info` the severity "
          "tasks of Chapter 22"]], widths=[22, 78])
    box("tip", "Exit status in regressions",
        "Continuous-integration scripts judge a test by the simulator's exit "
        "code and by grepping for a PASS/FAIL line. `$finish` normally "
        "exits with 0 even if the test failed; `$fatal` makes most "
        "simulators exit non-zero. End every test with an explicit summary "
        "line and use `$fatal` for failures, or have the run script parse "
        "the log.")

    # ------------------------------------------------------------------
    h2("File I/O")
    p("Verilog-2001 added C-like file I/O. `$fopen(name, mode)` returns a "
      "32-bit **file descriptor** (0 on failure) with modes \"r\", \"w\", "
      "\"a\" and their \"+\" and \"b\" variants. The older form without a "
      "mode returns a **multichannel descriptor** (MCD): one bit per file, "
      "bit 0 = standard output, so several files can be written with one "
      "call by OR-ing descriptors. The output tasks `$fdisplay`, `$fwrite`, "
      "`$fstrobe` and `$fmonitor` take the descriptor as their first "
      "argument; the input functions mirror C: `$fgetc`, `$ungetc`, "
      "`$fgets`, `$fscanf`, `$fread`, plus `$feof`, `$ferror`, `$fseek`, "
      "`$ftell`, `$rewind`, `$fflush` and `$fclose`. `$sscanf` parses a "
      "string, `$sformat`/`$swrite` (and SV's `$sformatf` function) format "
      "into one.")
    code(r"""# a    b    expected_sum
0003 0004 0007
00ff 0001 0100
ffff 0001 0000""", "vectors.txt - a stimulus file with a comment line.")
    vcode(r"""module fio;
  integer fin, fout, n, errs, line_no;
  reg [15:0] a, b, exp_sum, sum;
  reg [8*80-1:0] line;                         // 80-character line buffer
  initial begin
    errs = 0; line_no = 0;
    fin  = $fopen("vectors.txt", "r");
    fout = $fopen("results.log", "w");
    if (fin == 0) begin $display("cannot open vectors.txt"); $finish; end
    while (!$feof(fin)) begin
      n = $fgets(line, fin);                   // read one whole line (incl. newline)
      line_no = line_no + 1;
      if (n != 0 && line[8*n-1 -: 8] != "#") begin   // first character of the line
        n = $sscanf(line, "%h %h %h", a, b, exp_sum);
        if (n == 3) begin
          sum = a + b;
          $fdisplay(fout, "line %0d: %h + %h = %h %0s", line_no, a, b, sum,
                    (sum === exp_sum) ? "OK" : "MISMATCH");
          if (sum !== exp_sum) errs = errs + 1;
        end
      end
    end
    $fclose(fin);
    $fwrite(fout, "errors=%0d\n", errs);
    $fclose(fout);
    fin = $fopen("results.log", "r");          // read the log back and echo it
    while ($fgets(line, fin)) $write("%0s", line);
    $fclose(fin);
  end
endmodule""", "fio.v - a file-driven self-checking test.")
    out(["line 2: 0003 + 0004 = 0007 OK", "line 3: 00ff + 0001 = 0100 OK",
         "line 4: ffff + 0001 = 0000 OK", "errors=0"], "Icarus Verilog 12.")
    bul(["`$fgets` fills the variable **right-justified**: the first "
         "character of an n-character line sits in bits `[8*n-1 -: 8]`. "
         "It returns the number of characters read (0 at end of file).",
         "`$fscanf`/`$sscanf` return the number of items matched; always "
         "check it - a malformed line otherwise leaves the old values in "
         "place and the test silently re-checks the previous vector.",
         "`$feof` becomes true only after a read has hit the end, so the "
         "loop above also processes one empty read; the `n != 0` check "
         "handles it.",
         "Multichannel descriptors are limited to 31 files and ordinary "
         "descriptors by the tool and the OS: close files, especially in "
         "tests that open one per transaction."])

    h3("Memory initialisation: $readmemh, $readmemb and $writememh")
    p("`$readmemh(file, mem [, start [, end]])` loads a memory array from "
      "a text file of hex numbers (`$readmemb` for binary) separated by "
      "white space, with `//` and `/* */` comments and `@addr` directives "
      "that jump to a (hex) address. Unmentioned words keep their value. "
      "It is the standard way to load boot ROM images, coefficient tables "
      "and test programs into processor memories, and - uniquely among "
      "system tasks - **synthesis tools honour it** in an initial block to "
      "set ROM/RAM contents on FPGAs. SystemVerilog adds `$writememh` and "
      "`$writememb` to dump a memory.")
    vcode(r"""// boot ROM image: one hex word per line, // comments allowed
DEAD BEEF
@4          // jump to address 4
1234
5678
@7 FFFF""", "rom.hex")
    vcode(r"""module rm;
  reg [15:0] rom [0:7];
  integer i;
  initial begin
    for (i = 0; i < 8; i = i + 1) rom[i] = 16'h0;
    $readmemh("rom.hex", rom);
    for (i = 0; i < 8; i = i + 1) $write("%h ", rom[i]);
    $write("\n");
    $writememh("dump.hex", rom, 4, 7);         // write addresses 4..7
    $readmemb("bits.bin", rom, 0, 1);          // file missing -> warning, rom unchanged
  end
endmodule""", "rm.v")
    out(["dead beef 0000 0000 1234 5678 0000 ffff ",
         "ERROR: rm.v:10: $readmemb: Unable to open bits.bin for reading.",
         "// 0x00000000", "1234", "5678", "0000", "ffff"],
        "Icarus Verilog 12, followed by cat dump.hex (the first line of the "
        "dump is Icarus' own address comment).")
    box("warn", "Pitfall: a missing memory file is not fatal",
        "Most simulators only warn when `$readmemh` cannot open its file or "
        "when the file has fewer words than the memory, and the simulation "
        "continues with x or zero contents - the processor then executes "
        "garbage and the failure is reported thousands of cycles later. "
        "Check the file in the testbench (`$fopen` it first and `$fatal` if "
        "that returns 0) and pass the path through a plusarg rather than "
        "relying on the current working directory.")

    # ------------------------------------------------------------------
    h2("Random numbers")
    tbl(["Function", "Returns", "Notes"],
        [["`$random[(seed)]`", "Signed 32-bit", "1364 algorithm is defined in "
          "the LRM, so a given seed gives the same sequence on every "
          "compliant simulator; seed is an inout integer variable"],
         ["`$urandom[(seed)]` (SV)", "Unsigned 32-bit", "Per-thread RNG "
          "(random stability, Chapter 19); sequence is tool-specific"],
         ["`$urandom_range(max[, min])` (SV)", "Unsigned in [min, max]",
          "Arguments may be given in either order"],
         ["`$dist_uniform(seed, lo, hi)`", "Integer", "Also: "
          "`$dist_normal(seed, mean, sd)`, `$dist_exponential`, "
          "`$dist_poisson`, `$dist_chi_square`, `$dist_t`, `$dist_erlang`"]],
        widths=[30, 18, 52])
    vcode(r"""module rnd;
  integer seed, i, r;
  integer hist [0:3];
  initial begin
    seed = 42;
    $write("$random(seed)       :");
    for (i = 0; i < 4; i = i + 1) $write(" %0d", $random(seed));
    $write("\n$random %% 10        :");
    for (i = 0; i < 4; i = i + 1) $write(" %0d", $random(seed) % 10);   // can be negative!
    $write("\n{$random} %% 10      :");
    for (i = 0; i < 4; i = i + 1) $write(" %0d", {$random(seed)} % 10); // unsigned: 0..9
    $write("\n$urandom_range(3,1) :");
    for (i = 0; i < 6; i = i + 1) $write(" %0d", $urandom_range(3, 1));
    $write("\n");
    for (i = 0; i < 4; i = i + 1) hist[i] = 0;
    for (i = 0; i < 1000; i = i + 1) begin
      r = $dist_poisson(seed, 1);                      // mean 1
      if (r > 3) r = 3;
      hist[r] = hist[r] + 1;
    end
    $display("$dist_poisson(mean=1) histogram 0,1,2,>=3: %0d %0d %0d %0d",
             hist[0], hist[1], hist[2], hist[3]);
  end
endmodule""", "rnd.sv")
    out(["$random(seed)       : -2144582656 646214477 38602500 -975846261",
         "$random % 10        : 7 -9 4 0",
         "{$random} % 10      : 5 2 8 9",
         "$urandom_range(3,1) : 2 1 1 1 2 3",
         "$dist_poisson(mean=1) histogram 0,1,2,>=3: 359 355 191 95"],
        "Icarus Verilog 12. The Poisson histogram is close to the "
        "theoretical 368/368/184/80 per 1000.")
    box("warn", "Pitfall: $random % N can be negative",
        "`$random` is signed, so `$random % 10` lies in -9..9. Wrap it in a "
        "concatenation (`{$random} % 10`), which is always unsigned, or use "
        "`$urandom_range`. Also, `$random` without a seed argument uses one "
        "global seed for the whole simulation, so adding one call anywhere "
        "changes every random value after it; pass a per-component seed "
        "variable, or use SystemVerilog's per-thread RNG and constrained "
        "`randomize()` (Chapter 19).")

    # ------------------------------------------------------------------
    h2("Plusargs: configuring a test from the command line")
    p("Arguments that start with `+` on the simulator command line are "
      "**plusargs**, visible to the design. `$test$plusargs(\"NAME\")` "
      "returns 1 if a plusarg beginning with NAME is present; "
      "`$value$plusargs(\"NAME=%d\", var)` also converts the rest of the "
      "argument with a format (`%d %h %o %b %s %f %e %g`) into a variable "
      "and returns 1 on success. Every regression system uses them for the "
      "seed, the test name, verbosity, timeouts and feature switches - "
      "UVM's `+UVM_TESTNAME` and `+UVM_VERBOSITY` are plusargs.")
    vcode(r"""module pa;
  integer seed, n_pkts; reg [8*32-1:0] test; real freq;
  initial begin
    if ($test$plusargs("VERBOSE")) $display("verbose mode on");
    if (!$value$plusargs("SEED=%d", seed))   seed = 1;          // default if absent
    if (!$value$plusargs("NPKT=%d", n_pkts)) n_pkts = 10;
    if (!$value$plusargs("TEST=%s", test))   test = "smoke";
    if (!$value$plusargs("FREQ=%f", freq))   freq = 100.0;
    $display("seed=%0d n_pkts=%0d test=%0s freq=%0.1f MHz", seed, n_pkts, test, freq);
  end
endmodule""", "pa.v")
    out(["$ vvp pa", "seed=1 n_pkts=10 test=smoke freq=100.0 MHz",
         "$ vvp pa +VERBOSE +SEED=7 +TEST=dma_stress +FREQ=312.5",
         "verbose mode on",
         "seed=7 n_pkts=10 test=dma_stress freq=312.5 MHz"],
        "Icarus Verilog 12 (command lines shown with $).")
    box("warn", "Pitfall: prefix matching",
        "Both functions match a **prefix**: `$test$plusargs(\"DEBUG\")` is "
        "also true for `+DEBUG_AXI=0`. Choose names that are not prefixes of "
        "each other, or always use the `NAME=` form.")

    # ------------------------------------------------------------------
    h2("Conversion, math and bit-vector system functions")
    vcode(r"""module cv;
  real r; reg [63:0] bits; integer i;
  reg [7:0] v;
  initial begin
    r = 2.7;
    $display("$rtoi(2.7)=%0d  int'(2.7)=%0d  $itor(5)/2=%0.1f",
             $rtoi(r), integer'(r), $itor(5) / 2);
    bits = $realtobits(1.0);
    $display("$realtobits(1.0)=%h  back=%0.1f", bits, $bitstoreal(bits));
    $display("$clog2: 1->%0d 2->%0d 5->%0d 1024->%0d 1025->%0d",
             $clog2(1), $clog2(2), $clog2(5), $clog2(1024), $clog2(1025));
    v = 8'b0010_1100;
    $display("v=%b $bits=%0d $countones=%0d $onehot=%b $onehot0=%b",
             v, $bits(v), $countones(v), $onehot(v), $onehot0(v));
    v = 8'b0000_1000;
    $display("v=%b $onehot=%b  $isunknown=%b", v, $onehot(v), $isunknown(v));
    v = 8'b0000_1z00;
    $display("v=%b $isunknown=%b  (v == 8) is %b", v, $isunknown(v), v == 8);
    $display("$signed(4'b1111)=%0d  $unsigned(-1) as 4 bits=%0d",
             $signed(4'b1111), 4'($unsigned(-1)));
  end
endmodule""", "cv.sv")
    out(["$rtoi(2.7)=2  int'(2.7)=3  $itor(5)/2=2.5",
         "$realtobits(1.0)=3ff0000000000000  back=1.0",
         "$clog2: 1->0 2->1 5->3 1024->10 1025->11",
         "v=00101100 $bits=8 $countones=3 $onehot=0 $onehot0=0",
         "v=00001000 $onehot=1  $isunknown=0",
         "v=00001z00 $isunknown=1  (v == 8) is x",
         "$signed(4'b1111)=-1  $unsigned(-1) as 4 bits=15"],
        "Icarus Verilog 12.")
    tbl(["Function", "Meaning", "Synthesizable?"],
        [["`$rtoi(r)`", "Real to integer by **truncation**", "No (real)"],
         ["`int'(r)`, assignment", "Real to integer by **rounding** (away "
          "from zero at .5)", "No (real)"],
         ["`$itor(i)`", "Integer to real", "No"],
         ["`$realtobits` / `$bitstoreal`", "Real <-> 64-bit IEEE-754 "
          "pattern (to pass reals through ports)", "No"],
         ["`$shortrealtobits` / `$bitstoshortreal` (SV)", "32-bit "
          "float pattern", "No"],
         ["`$signed(x)`, `$unsigned(x)`", "Reinterpret signedness (no bit "
          "change)", "Yes"],
         ["`$clog2(n)`", "Ceiling log2 (0 for n = 0 or 1)", "Yes, as a "
          "constant"],
         ["`$bits(x)`", "Number of bits of an expression or type", "Yes, "
          "constant"],
         ["`$countones`, `$countbits(x, '1, ...)`", "Population count "
          "(countbits: of given values, 1800-2012)", "Yes (adder tree)"],
         ["`$onehot`, `$onehot0`", "Exactly one bit set / at most one", "Yes"],
         ["`$isunknown(x)`", "Any bit is x or z", "Simulation only"],
         ["`$ln $log10 $exp $sqrt $pow $floor $ceil $sin ...`", "Real math "
          "(1364-2005)", "Only in constant expressions"]],
        widths=[36, 44, 20])
    p("`$onehot`, `$onehot0`, `$isunknown` and `$countones` were introduced "
      "for assertions (Chapter 22) - `assert property (@(posedge clk) "
      "$onehot0(grant));` is the canonical arbiter check - but they are "
      "equally useful in immediate checks and, apart from `$isunknown`, in "
      "RTL.")

    # ------------------------------------------------------------------
    h2("Value change dump (VCD)")
    p("**VCD** is the waveform format defined by the Verilog standard "
      "(1364 clause 18) and read by every waveform viewer (GTKWave, "
      "Surfer, and the commercial debuggers). It is a text file: a header "
      "that declares scopes and variables with short identifier codes, "
      "then a list of time stamps (`#t`) each followed by the value "
      "changes at that time. The tasks that control it:")
    tbl(["Task", "Effect"],
        [["`$dumpfile(\"f.vcd\")`", "Name the file (default dump.vcd); "
          "call before $dumpvars"],
         ["`$dumpvars(depth, scope, ...)`", "Select variables: depth 0 = "
          "all levels below the scope, 1 = only that scope, n = n levels. "
          "No arguments = entire design"],
         ["`$dumpoff` / `$dumpon`", "Pause and resume; at a pause all "
          "variables are dumped as x, at resume their current values"],
         ["`$dumpall`", "Checkpoint all current values"],
         ["`$dumplimit(bytes)`", "Stop dumping when the file reaches a size"],
         ["`$dumpflush`", "Flush the OS buffer (useful before a crash or "
          "while viewing a running simulation)"],
         ["`$dumpports(...)` (extended VCD)", "Port values with strength "
          "and direction, used for test-pattern exchange"]],
        widths=[32, 68])
    vcode(r"""`timescale 1ns/1ns
module cnt (input clk, output reg [1:0] q = 0);
  always @(posedge clk) q <= q + 1;
endmodule
module vcd;
  reg clk = 0;
  wire [1:0] q;
  cnt u (.clk(clk), .q(q));
  always #5 clk = ~clk;
  initial begin
    $dumpfile("wave.vcd");
    $dumpvars(0, vcd);          // depth 0 = this scope and everything below it
    #20 $dumpoff;               // stop recording (signals dumped as x)
    #20 $dumpon;                // resume: current values are dumped again
    #10 $finish;
  end
endmodule""", "vcd.v")
    out(["$timescale", "        1ns", "$end",
         "$scope module vcd $end",
         "$var wire 2 ! q [1:0] $end",
         "$var reg 1 \" clk $end",
         "$scope module u $end",
         "$var wire 1 \" clk $end",
         "$var reg 2 # q [1:0] $end",
         "$upscope $end", "$upscope $end", "$enddefinitions $end",
         "...",
         "#15", "b10 !", "b10 #", "1\"",
         "#20", "$dumpoff", "bx #", "x\"", "bx !", "$end",
         "#40", "$dumpon", "b0 #", "1\"", "b0 !", "$end"],
        "Excerpts of wave.vcd written by Icarus Verilog 12 (tab shown as "
        "spaces; \"...\" marks "
        "omitted lines).")
    p("Note that `vcd.clk` and `vcd.u.clk` share the identifier code `\"` "
      "- VCD stores a net once however many scopes it appears in. VCD is "
      "simple and universal but large and slow for SoC-size designs; "
      "production flows use compressed proprietary formats (FSDB for "
      "Verdi, SHM for Xcelium, WLF for Questa, VPD for VCS) or the open FST "
      "format that Icarus (`-fst`) and Verilator (`--trace-fst`) can write. "
      "Their dump tasks follow the same pattern: select a scope and depth, "
      "then window the dump in time to keep files manageable.")

    # ------------------------------------------------------------------
    h2("PLI and VPI: extending the simulator in C")
    p("The **Programming Language Interface** lets C code run inside the "
      "simulator, read and write signals, traverse the design hierarchy, "
      "and register new system tasks. It evolved in three generations, all "
      "still found in the field:")
    tbl(["Generation", "Routines", "Status"],
        [["PLI 1.0 **TF** routines", "`tf_getp`, `tf_putp`, `tf_nump` ...: "
          "access to the arguments of a user system task", "Deprecated, "
          "removed from 1364-2005"],
         ["PLI 1.0 **ACC** routines", "`acc_handle_object`, "
          "`acc_fetch_value` ...: access to design objects", "Deprecated, "
          "removed from 1364-2005"],
         ["PLI 2.0 = **VPI**", "`vpi_handle`, `vpi_iterate`, `vpi_scan`, "
          "`vpi_get_value`, `vpi_put_value`, `vpi_register_cb` ...",
          "The current standard (1364 clauses 26-27, 1800 clauses 36-38)"],
         ["**DPI-C** (SV)", "Direct import/export of C functions", "The "
          "preferred way to call C models from SystemVerilog (Chapter 24)"]],
        widths=[22, 50, 28])
    p("VPI is **object-oriented over handles**: every design object "
      "(module, net, reg, port, the call of a system task, even a callback) "
      "is reached through an opaque `vpiHandle`; relationships are "
      "navigated with `vpi_handle(relation, obj)` (one-to-one) and "
      "`vpi_iterate` + `vpi_scan` (one-to-many); properties are read with "
      "`vpi_get` (integers) and `vpi_get_str` (strings); values with "
      "`vpi_get_value` / `vpi_put_value` in a chosen format. New system "
      "tasks are registered by routines listed in the "
      "`vlog_startup_routines` array, which the simulator calls when it "
      "loads the shared library. Here is a complete, working example:")
    code(r"""#include <vpi_user.h>

/* $show_value(sig): print the full hierarchical name and value of a signal */
static PLI_INT32 show_value_calltf(PLI_BYTE8 *user_data) {
  (void)user_data;
  vpiHandle call = vpi_handle(vpiSysTfCall, NULL);   /* this $show_value call  */
  vpiHandle args = vpi_iterate(vpiArgument, call);   /* its argument list      */
  vpiHandle sig  = vpi_scan(args);                   /* first argument         */
  s_vpi_value v;  v.format = vpiBinStrVal;
  vpi_get_value(sig, &v);
  s_vpi_time t;   t.type = vpiSimTime;
  vpi_get_time(NULL, &t);
  vpi_printf("[VPI] t=%u %s (%d bits) = %s\n", t.low,
             vpi_get_str(vpiFullName, sig), vpi_get(vpiSize, sig), v.value.str);
  vpi_free_object(args);
  return 0;
}

static void register_tasks(void) {
  s_vpi_systf_data tf = {0};
  tf.type   = vpiSysTask;
  tf.tfname = "$show_value";
  tf.calltf = show_value_calltf;
  vpi_register_systf(&tf);
}

/* the simulator calls every routine in this null-terminated table at startup */
void (*vlog_startup_routines[])(void) = { register_tasks, 0 };""",
         "hello_vpi.c - a user-defined system task in 30 lines of C.")
    vcode(r"""module vpi_tb;
  reg [7:0] data = 8'hA5;
  initial begin
    #3 $show_value(data);
    data = data + 1;
    #2 $show_value(data);
  end
endmodule""", "vpi_tb.v")
    out(["$ iverilog-vpi hello_vpi.c",
         "Compiling hello_vpi.c...",
         "Making hello_vpi.vpi from  hello_vpi.o...",
         "$ iverilog -g2012 -o vpi_tb vpi_tb.v && vvp -M. -mhello_vpi vpi_tb",
         "[VPI] t=3 vpi_tb.data (8 bits) = 10100101",
         "[VPI] t=5 vpi_tb.data (8 bits) = 10100110"],
        "Built with iverilog-vpi and loaded into vvp with -m.")
    p("Beyond new system tasks, VPI is how a large part of the "
      "verification ecosystem works: **callbacks** (`vpi_register_cb` with "
      "`cbValueChange`, `cbReadWriteSynch`, `cbEndOfSimulation` ...) let "
      "C code react to signal changes and scheduling events; waveform "
      "dumpers such as the FSDB writer, code-coverage tools and debuggers "
      "are VPI applications; and the Python co-simulation framework "
      "**cocotb** drives Icarus, Verilator, VCS, Xcelium and Questa through "
      "VPI (or VHPI). Chapter 24 compares VPI with the simpler and faster "
      "DPI-C and shows cocotb-style co-simulation.")
    box("expert", "Interview insight: why DPI replaced most PLI code",
        "VPI is powerful because it can see everything, and slow for the "
        "same reason: every value access goes through handle lookups and "
        "format conversions, and it forces the simulator to keep objects "
        "visible (debug access, which disables optimisations). DPI-C "
        "passes arguments directly as C types, with no handles, and is the "
        "right choice for calling reference models. Use VPI when you need "
        "introspection: walking the hierarchy, callbacks on arbitrary "
        "signals, or tools that must work without modifying the HDL.")

    h2("Summary")
    bul(["$display prints immediately; $strobe and $monitor print settled "
         "values in the Postponed region; only one $monitor is active.",
         "Use %0d/%0h/%0s to avoid padding; upper-case X/Z in a digit means "
         "partly unknown; %m prints the scope, %p (SV) any aggregate.",
         "$time rounds to the caller's unit; pass $realtime to %t and set "
         "$timeformat once in the testbench.",
         "File I/O: $fopen returns 0 on failure; check $fscanf/$sscanf "
         "return counts; $fgets right-justifies; close what you open.",
         "$readmemh/$readmemb load memories (and FPGA ROM contents); a "
         "missing file only warns.",
         "$random is signed and LRM-defined; $urandom/$urandom_range are the "
         "SV per-thread RNG; $dist_* give distributions.",
         "$test$plusargs / $value$plusargs configure tests (prefix match!).",
         "$clog2, $bits, $signed, $countones, $onehot are synthesizable; "
         "$rtoi truncates while a cast rounds.",
         "VCD tasks select scope/depth and window time; production uses "
         "FSDB/FST. VPI is the C API behind custom tasks, dumpers and cocotb."])
    h2("Exercises")
    bul(["Write a testbench that reads a CSV file of `addr,data` pairs, "
         "writes them into a RAM model, and dumps the RAM with $writememh. "
         "Handle a missing file with $fatal and a malformed line with an "
         "error message that includes the line number.",
         "Predict, then check, what `$display(\"%d|%0d|%h|%s\", 8'sh80, "
         "8'sh80, 8'sh80, 16'h4142)` prints.",
         "A testbench prints `$time` with `%t` after `$timeformat(-12, 0, "
         "\" ps\", 10)` in a module with `timescale 1ns/1ps` and shows "
         "100000 ps where the waveform shows 100.4 ns. Explain and fix.",
         "Use $value$plusargs to implement `+TIMEOUT_NS=<n>` with a default "
         "of 1 ms, and a watchdog that ends the test with $fatal.",
         "Generate 10,000 values with `$dist_normal(seed, 100, 15)` and "
         "print a 10-bin histogram. Compare the mean and standard "
         "deviation with the requested values.",
         "Extend hello_vpi.c with a `$count_changes(sig)` task that "
         "registers a `cbValueChange` callback and prints the number of "
         "changes at the end of simulation (`cbEndOfSimulation`)."],
        ordered=True)


# =============================================================================
#   Chapter 11 - Synthesizable Verilog: coding patterns and sim/synth mismatches
# =============================================================================
def ch11():
    chapter("Synthesizable Verilog: Coding Patterns and "
            "Simulation/Synthesis Mismatches")
    p("Verilog was designed as a simulation language; synthesis came later "
      "and adopted a **subset** of it, interpreted according to templates. "
      "The simulator executes your code literally, event by event. The "
      "synthesis tool instead **recognises patterns** - \"an always block "
      "triggered by a clock edge whose outputs are assigned with <= is a "
      "bank of flip-flops\" - and builds the hardware those patterns "
      "stand for. When the code matches the templates, simulation and "
      "hardware agree. When it does not, the tool may still produce a "
      "netlist, sometimes with only a warning, and the chip no longer "
      "behaves like the RTL you verified. This chapter gives the templates "
      "and then demonstrates, with real synthesis and real re-simulation of "
      "the netlist, each classic way the two can disagree.")
    box("note", "How the demos in this chapter were produced",
        "Each mismatch example was simulated as RTL with Icarus Verilog, "
        "synthesized with Yosys 0.33 (`synth -top <module>; write_verilog "
        "-noattr net.v`), and the resulting gate-level netlist was simulated "
        "with the same testbench against Yosys' cell library "
        "(`/usr/share/yosys/simcells.v`). Commercial synthesis tools (Design "
        "Compiler, Genus) behave the same way on these examples, usually "
        "with more warnings. The IEEE standard for the synthesizable subset "
        "is IEEE 1364.1-2002 (Verilog RTL synthesis); for SystemVerilog "
        "each tool documents its own subset (Chapter 17).")

    # ------------------------------------------------------------------
    h2("The synthesizable subset")
    tbl(["Construct", "Synthesis treatment"],
        [["module, ports, parameters, localparam, generate, functions",
          "Fully supported (functions become combinational logic, inlined)"],
         ["`assign`, `always @*`, `always @(posedge clk ...)`",
          "Supported by template: combinational logic, flops, latches"],
         ["Tasks", "Supported if they contain no timing controls; inlined"],
         ["`for` loops with constant bounds", "Unrolled; `while`/`repeat` "
          "only with constant iteration counts (tool-dependent)"],
         ["Operators `+ - * & | ^ << >> ?: == < ...`", "Supported; `/` "
          "and `%` usually only by constants or powers of two; `**` only "
          "with constant operands or base 2"],
         ["`case`, `casez`, `if`", "Supported; `casex` supported but "
          "dangerous (see below)"],
         ["Memories `reg [7:0] m [0:N-1]`", "Inferred as flops or mapped to "
          "RAM macros / FPGA block RAM"],
         ["`initial` blocks", "**Ignored** for ASIC (except that FPGA tools "
          "use them as power-up values and $readmem contents)"],
         ["Delays `#n`", "**Ignored** (with or without a warning)"],
         ["`x` and `z` literals", "`x` = don't care (optimiser picks); `z` "
          "= three-state driver"],
         ["`wait`, `@` inside a block, `fork/join`, events", "Not "
          "synthesizable"],
         ["`force/release`, `deassign`, `$display`, file I/O, `real`",
          "Not synthesizable (system tasks ignored, `real` only in constant "
          "expressions)"],
         ["`===`, `!==`", "Treated as `==`/`!=` or rejected - x cannot be "
          "detected in hardware"],
         ["UDPs, switch primitives, specify blocks", "Gate primitives are "
          "mapped; UDPs/switches/specify are for simulation libraries"],
         ["Hierarchical references, `defparam`", "Usually rejected or "
          "limited"]],
        widths=[42, 58], caption="The Verilog synthesizable subset "
                                 "(based on IEEE 1364.1 and common tool "
                                 "practice).")

    # ------------------------------------------------------------------
    h2("Templates for combinational logic")
    p("Combinational logic is written with continuous assignments or with "
      "`always @*` (SystemVerilog: `always_comb`, Chapter 14). Inside an "
      "`always @*` block three rules guarantee a clean result: (1) use "
      "**blocking** `=` assignments; (2) **assign every output on every "
      "path** through the block - most easily with default assignments at "
      "the top; (3) never read a variable before it is assigned in the "
      "block unless you intend a latch.")
    vcode(r"""module mux4 #(parameter W = 8) (input [1:0] sel, input [W-1:0] d0, d1, d2, d3,
                                output reg [W-1:0] y);
  always @* begin
    case (sel)
      2'd0: y = d0;
      2'd1: y = d1;
      2'd2: y = d2;
      default: y = d3;              // default covers 3 (and x/z in simulation)
    endcase
  end
endmodule

module dec #(parameter N = 3) (input [N-1:0] a, input en, output [(1<<N)-1:0] y);
  assign y = en ? ({{((1<<N)-1){1'b0}}, 1'b1} << a) : {(1<<N){1'b0}};
endmodule

module prienc (input [7:0] req, output reg [2:0] idx, output reg vld);
  integer i;
  always @* begin
    idx = 3'd0; vld = 1'b0;
    for (i = 0; i < 8; i = i + 1)   // loop unrolls into a priority chain
      if (req[i] && !vld) begin idx = i[2:0]; vld = 1'b1; end
  end
endmodule""", "more.v (part 1) - multiplexer, decoder and priority encoder "
               "templates. All compile warning-free in Icarus and synthesize "
               "to pure logic in Yosys.")
    bul(["**Multiplexers**: `case` with a `default`, or `?:` for two inputs. "
         "A `case` whose items are mutually exclusive synthesizes to a "
         "parallel mux; an `if/else if` chain to a priority mux - modern "
         "tools optimise both, but the priority form states intent.",
         "**Decoders**: a shifted one (`1 << a`) is the clearest; the "
         "replication above keeps the constant as wide as the output, so "
         "no bits are lost to sizing (Chapter 4).",
         "**Loops** are unrolled; the loop variable must have constant "
         "bounds. The `!vld` term makes the lowest index win; without it the last "
         "matching iteration - the highest index - would win.",
         "**Arithmetic**: `+`, `-`, `*` and comparisons map to library "
         "adders/multipliers (DesignWare in DC); size the result explicitly "
         "to keep the carry (`{c, s} = a + b;`)."])

    h2("Templates for sequential logic")
    vcode(r"""module ff_async (input clk, rst_n, en, input [7:0] d, output reg [7:0] q);
  always @(posedge clk or negedge rst_n)
    if (!rst_n)  q <= 8'h00;          // async reset: in sensitivity list, tested first
    else if (en) q <= d;              // enable: no else -> hold (mux or ICG, not a latch)
endmodule

module ff_sync (input clk, rst, input [7:0] d, output reg [7:0] q);
  always @(posedge clk)
    if (rst) q <= 8'h00;              // sync reset: just another data input
    else     q <= d;
endmodule""", "tmpl.v (part 1) - flip-flop templates.")
    p("The asynchronous-reset template is rigid, and the rules are "
      "LRM-independent conventions that every synthesis tool enforces: the "
      "sensitivity list contains **exactly** the clock edge and the reset "
      "edge(s); the first `if` tests the reset with the polarity matching "
      "the edge (`negedge rst_n` -> `if (!rst_n)`); the reset branch assigns "
      "constants only; and everything else goes in the final `else`. A "
      "register that is missing from the reset branch but assigned in the "
      "`else` branch gets its **reset used as an enable** (the tool adds "
      "logic to hold the value during reset) - a frequent lint warning.")
    vcode(r"""module counter #(parameter W = 8) (input clk, rst_n, en, load, input [W-1:0] din,
                                   output reg [W-1:0] cnt, output tc);
  always @(posedge clk or negedge rst_n)
    if (!rst_n)     cnt <= {W{1'b0}};
    else if (load)  cnt <= din;
    else if (en)    cnt <= cnt + 1'b1;
  assign tc = en & (&cnt);          // terminal count, for cascading
endmodule

module shreg #(parameter N = 4) (input clk, en, sin, output sout, output reg [N-1:0] q);
  always @(posedge clk)
    if (en) q <= {q[N-2:0], sin};   // one NBA per clock: no ordering issue
  assign sout = q[N-1];
endmodule

module lat (input g, input [7:0] d, output reg [7:0] q);
  always @*                         // intentional latch: transparent while g=1
    if (g) q = d;                   // (use only when the methodology allows latches)
endmodule""", "more.v (part 2) - counter, shift register and an "
               "intentional latch. Yosys maps them to 8 x $_DFFE_PN0P_ "
               "(enable flop, async reset to 0), 4 x $_DFFE_PP_ and "
               "8 x $_DLATCH_P_ respectively.")
    h3("Memories: inferring RAM and ROM")
    vcode(r"""module ram_sp #(parameter AW = 8, DW = 32) (
  input clk, we, input [AW-1:0] addr, input [DW-1:0] wdata, output reg [DW-1:0] rdata);
  reg [DW-1:0] mem [0:(1<<AW)-1];
  always @(posedge clk) begin
    if (we) mem[addr] <= wdata;
    rdata <= mem[addr];               // synchronous read -> maps to SRAM/BRAM
  end
endmodule

module rom_case (input [1:0] a, output reg [7:0] d);
  always @* case (a)
    2'd0: d = 8'h3C; 2'd1: d = 8'hA5; 2'd2: d = 8'h0F; default: d = 8'hFF;
  endcase
endmodule""", "tmpl.v (part 2) - a single-port RAM with synchronous read "
               "(read-first) and a case ROM.")
    out(["=== ff_async ===", "     $adffe                          1",
         "=== ff_sync ===", "     $sdff                           1",
         "=== ram_sp ===", "     $mem_v2                         1",
         "     $mux                            3",
         "=== rom_case ===", "     $eq                             2",
         "     $logic_not                      1",
         "     $pmux                           1"],
        "yosys -p \"read_verilog tmpl.v; hierarchy -check; proc; opt; "
        "memory -nomap; opt; stat\" | grep: the async-reset enable flop, the "
        "sync-reset flop, a recognised memory and a ROM as a parallel mux.")
    p("A memory is recognised when the array is accessed with the "
      "templates the target supports: synchronous write, and either "
      "synchronous read (registered address or data - maps to SRAM "
      "macros and FPGA block RAM) or asynchronous read (only small "
      "register files or LUT RAM). Read-during-write behaviour is part of "
      "the template: `rdata <= mem[addr]` in the same block as the write "
      "reads the **old** data (read-first); writing the read from a "
      "variable updated with blocking assignment gives write-first. In ASIC "
      "flows, large memories are not inferred at all: they are instantiated "
      "as compiler-generated SRAM macros through a wrapper, with the "
      "behavioural array used only in the simulation model. ROMs are "
      "written as a `case` statement or as an array initialised with "
      "`$readmemh` (FPGA) and are turned into logic.")
    h3("Finite state machines")
    vcode(r"""// "101" sequence detector, Moore, overlapping, two-process style
module det101 (input clk, rst_n, din, output reg hit);
  localparam [1:0] S0 = 2'd0, S1 = 2'd1, S10 = 2'd2, S101 = 2'd3;
  reg [1:0] state, nxt;
  always @(posedge clk or negedge rst_n)        // state register
    if (!rst_n) state <= S0;
    else        state <= nxt;
  always @* begin                               // next-state logic
    nxt = state;                                // default: stay
    case (state)
      S0:   if (din)  nxt = S1;
      S1:   if (!din) nxt = S10;
      S10:  nxt = din ? S101 : S0;
      S101: nxt = din ? S1 : S10;
      default: nxt = S0;
    endcase
  end
  always @* hit = (state == S101);              // Moore output
endmodule

module tb_fsm;
  reg clk = 0, rst_n = 0, din = 0; wire hit;
  reg [11:0] pattern = 12'b1101_0110_1010;      // shifted in MSB first
  integer i;
  det101 dut (.clk(clk), .rst_n(rst_n), .din(din), .hit(hit));
  always #5 clk = ~clk;
  initial begin
    #12 rst_n = 1;
    for (i = 11; i >= 0; i = i - 1) begin
      @(negedge clk) din = pattern[i];
      @(posedge clk) #1 $write("%b", hit);
    end
    $write("  <- hit after each bit of %b\n", pattern);
    $finish;
  end
endmodule""", "fsm.v - the canonical two-process FSM: a state register "
               "and a combinational next-state block with a default.")
    out(["000101001010  <- hit after each bit of 110101101010"],
        "Icarus Verilog 12: hits after bits 4, 6, 9 and 11 (overlapping "
        "matches).")
    p("State encodings are `localparam`s (SystemVerilog: an `enum`, "
      "Chapter 12). The `nxt = state;` default makes every path assign "
      "`nxt`, so no latch can appear, and the `default` item recovers from "
      "illegal states. Synthesis tools extract the FSM and may re-encode it "
      "(one-hot, Gray) unless told otherwise; the micro-architecture of "
      "FSMs, Mealy vs. Moore and output registering are covered in the "
      "companion RTL Design guide.")
    h3("Three-state buffers and bidirectional pins")
    vcode(r"""module gpio_pad (inout pad, input oe, input dout, output din);
  assign pad = oe ? dout : 1'bz;     // drive or release the pin
  assign din = pad;                  // always sample the pin
endmodule
module tb_tri;
  reg oe, dout, ext_en, ext_val;
  wire pad, din;
  gpio_pad u (.pad(pad), .oe(oe), .dout(dout), .din(din));
  assign pad = ext_en ? ext_val : 1'bz;   // the other chip on the board
  pullup (pad);                           // board pull-up resistor
  initial begin
    oe = 1; dout = 0; ext_en = 0; ext_val = 0;
    #1 $display("we drive 0       : pad=%b (%v) din=%b", pad, pad, din);
    oe = 0;
    #1 $display("nobody drives    : pad=%b (%v) din=%b", pad, pad, din);
    ext_en = 1;
    #1 $display("other chip: 0    : pad=%b (%v) din=%b", pad, pad, din);
    oe = 1; dout = 1;
    #1 $display("both drive 1 vs 0: pad=%b (%v) din=%b  <- contention", pad, pad, din);
  end
endmodule""", "tri.v - a bidirectional pad model.")
    out(["we drive 0       : pad=0 (St0) din=0",
         "nobody drives    : pad=1 (Pu1) din=1",
         "other chip: 0    : pad=0 (St0) din=0",
         "both drive 1 vs 0: pad=x (StX) din=x  <- contention"],
        "Icarus Verilog 12.")
    box("warn", "Three-states belong only at the chip boundary",
        "Inside an ASIC, internal three-state buses are forbidden by "
        "almost every methodology (they are hard to test, create contention "
        "and floating nodes, and complicate timing); use multiplexers. FPGAs "
        "have no internal three-states at all - tools convert them to muxes. "
        "The `inout` + `? : 1'bz` pattern is used only in the pad ring, "
        "where it maps onto a bidirectional I/O cell (the I/O cell's OE, A "
        "and Y pins correspond to `oe`, `dout` and `din`).")

    # ------------------------------------------------------------------
    h2("Simulation/synthesis mismatches")
    p("A **mismatch** exists when the netlist, simulated with the same "
      "stimulus, behaves differently from the RTL. Formal **equivalence "
      "checking** (Conformal LEC, Formality) catches many of them - it "
      "compares the RTL as the synthesis tool interprets it with the "
      "netlist - but it cannot catch cases where the RTL simulation itself "
      "differs from that interpretation. Only good coding style, lint and "
      "gate-level simulation catch those. The following demos each show "
      "one mechanism.")
    h3("1. Incomplete sensitivity list")
    vcode(r"""module sens (input a, b, c, output reg y);
  always @(a or b)          // BUG: c is missing from the sensitivity list
    y = (a & b) | c;
endmodule""", "sens.v")
    vcode(r"""module tb_sens;
  reg a, b, c; wire y;
  sens dut (.a(a), .b(b), .c(c), .y(y));
  initial begin
    a = 0; b = 0; c = 0;
    #1 c = 1;  #1 $display("a=%b b=%b c=%b -> y=%b", a, b, c, y);
    #1 a = 1;  #1 $display("a=%b b=%b c=%b -> y=%b", a, b, c, y);
  end
endmodule""", "tb_sens.v")
    out(["== RTL ==", "a=0 b=0 c=1 -> y=0", "a=1 b=0 c=1 -> y=1",
         "== gate netlist ==", "a=0 b=0 c=1 -> y=1", "a=1 b=0 c=1 -> y=1"],
        "Icarus on sens.v, then on the Yosys netlist (assign y = (b & a) | "
        "c). Yosys synthesized the intended logic without any warning.")
    p("The simulator only re-evaluates the block when a or b changes, so "
      "the RTL behaves like a latch on c; synthesis ignores the sensitivity "
      "list and builds the AND-OR. The RTL was wrong, the silicon right - "
      "but it was the RTL that was verified. **Fix**: `always @*` (or "
      "`always_comb`), which the LRM defines to include every variable read "
      "in the block. Verilator's lint flags this block (as a sequential "
      "process with blocking assignments); commercial lint reports "
      "\"incomplete sensitivity list\".")
    h3("2. Incomplete assignment: the unintended latch")
    vcode(r"""module latch_bug (input [1:0] sel, input a, b, output reg y);
  always @* begin
    case (sel)                 // sel == 2'b11 not covered, no default
      2'b00: y = a;
      2'b01: y = b;
      2'b10: y = a ^ b;
    endcase                    // -> y must hold its value -> LATCH
  end
endmodule
module latch_fix (input [1:0] sel, input a, b, output reg y);
  always @* begin
    y = 1'b0;                  // default assignment first: every path assigns y
    case (sel)
      2'b00: y = a;
      2'b01: y = b;
      2'b10: y = a ^ b;
    endcase
  end
endmodule""", "latch.v")
    out(["No latch inferred for signal `\\latch_fix.\\y' from process",
         "    `\\latch_fix.$proc$latch.v:11$3'.",
         "Latch inferred for signal `\\latch_bug.\\y' from process",
         "    `\\latch_bug.$proc$latch.v:2$1': $auto$proc_dlatch.cc:427:proc_dlatch$37"],
        "yosys -p \"read_verilog latch.v; proc; stat\" (lines wrapped).")
    p("This one is **not** a mismatch - the simulator also holds y when "
      "sel = 11 - but it is almost always a bug: a latch in a flop-based "
      "design is transparent while the enable is high, is hard to time and "
      "to test, and its enable is a glitch-prone combinational signal. "
      "Every synthesis log should be searched for \"latch inferred\". "
      "SystemVerilog's `always_comb` makes tools warn, and `always_latch` "
      "documents an intentional one.")
    h3("3. full_case and parallel_case")
    p("`// synopsys full_case` (or the attribute `(* full_case *)`) tells "
      "synthesis that the listed case items are **all that can occur**, "
      "so unlisted values are don't-cares and no latch is needed. "
      "`parallel_case` tells it the items are mutually exclusive, so no "
      "priority logic is needed. Both are **invisible to the simulator**, "
      "which is exactly the problem:")
    vcode(r"""module fc (input [1:0] sel, input a, b, output reg y);
  always @* begin
    (* full_case *)            // same meaning as the comment  // synopsys full_case
    case (sel)
      2'b00: y = a;
      2'b01: y = b;
      2'b10: y = a ^ b;
    endcase
  end
endmodule""", "fc.v - the latch_bug case with a full_case directive.")
    vcode(r"""module tb_fc;
  reg [1:0] sel; reg a, b; wire y;
  fc dut (.sel(sel), .a(a), .b(b), .y(y));
  initial begin
    a = 1; b = 0;
    sel = 2'b00; #1 $display("sel=%b a=%b b=%b -> y=%b", sel, a, b, y);
    sel = 2'b11; #1 $display("sel=%b a=%b b=%b -> y=%b", sel, a, b, y);
    a = 0;       #1 $display("sel=%b a=%b b=%b -> y=%b", sel, a, b, y);
  end
endmodule""", "tb_fc.v")
    out(["No latch inferred for signal `\\fc.\\y' from process `\\fc.$proc$fc.v:2$1'.",
         "== RTL ==", "sel=00 a=1 b=0 -> y=1", "sel=11 a=1 b=0 -> y=1",
         "sel=11 a=0 b=0 -> y=1",
         "== gates ==", "sel=00 a=1 b=0 -> y=1", "sel=11 a=1 b=0 -> y=1",
         "sel=11 a=0 b=0 -> y=0"],
        "Yosys honours full_case: no latch. RTL still holds y for sel = 11; "
        "the netlist (y = sel==11 ? a : ...) follows a. Mismatch.")
    box("warn", "Pitfall: full_case and parallel_case are evil twins",
        "Cliff Cummings' well-known paper of that title summarises the "
        "industry verdict: these directives change the hardware without "
        "changing the simulation, so any value outside the listed items (or "
        "any overlap between items) produces a netlist that nobody "
        "simulated. Instead: add a `default` (with a real value, or with "
        "`'x` if you deliberately want a don't-care, see below); write "
        "mutually exclusive items; and in SystemVerilog use `unique case` or "
        "`priority case` (Chapter 14), which give the same optimisation "
        "**and** make the simulator check the assumption at run time.")
    h3("4. casex and casez hide unknowns")
    vcode(r"""module cx (input [1:0] op, input [7:0] a, b, output reg [7:0] y);
  always @* begin
    casex (op)
      2'b00:   y = a + b;
      2'b01:   y = a - b;
      2'b1?:   y = a & b;
      default: y = 8'hEE;
    endcase
  end
endmodule
module cz (input [1:0] op, input [7:0] a, b, output reg [7:0] y);
  always @* begin
    case (op)                      // plain case: x in op matches no item
      2'b00:   y = a + b;
      2'b01:   y = a - b;
      2'b10,
      2'b11:   y = a & b;
      default: y = 8'hxx;          // make unknowns visible in simulation
    endcase
  end
endmodule
module tb_cx;
  reg [1:0] op; reg [7:0] a = 8'd12, b = 8'd10; wire [7:0] y1, y2;
  cx u1 (op, a, b, y1);
  cz u2 (op, a, b, y2);
  initial begin
    op = 2'b01; #1 $display("op=%b casex:y=%h  case:y=%h", op, y1, y2);
    op = 2'bx1; #1 $display("op=%b casex:y=%h  case:y=%h   <- uninitialised op", op, y1, y2);
    op = 2'bxx; #1 $display("op=%b casex:y=%h  case:y=%h", op, y1, y2);
  end
endmodule""", "cx.v")
    out(["op=01 casex:y=02  case:y=02",
         "op=x1 casex:y=02  case:y=xx   <- uninitialised op",
         "op=xx casex:y=16  case:y=xx"], "Icarus Verilog 12.")
    p("`casex` treats x and z as wildcards **in the case expression too**, "
      "not only in the items. An uninitialised or corrupted `op = xx` "
      "matches the first item and the simulation happily computes a + b = "
      "0x16, hiding the bug that silicon would expose. `casez` has the same "
      "problem for z (a floating input). Use plain `case`, or `casez` with "
      "`?` only in the items (the accepted idiom for priority decoders), "
      "or SystemVerilog's `case inside`, which treats x/z in the "
      "expression as non-matching.")
    h3("5. Blocking assignments in sequential logic")
    vcode(r"""module pipe2 (input clk, input [3:0] d, output reg [3:0] q2);
  reg [3:0] q1;
  always @(posedge clk) q1 = d;     // BUG: blocking assignment in clocked logic
  always @(posedge clk) q2 = q1;    // reads q1 - old or new value? order-dependent
endmodule""", "race.v (race_swapped.v has the two always blocks in the "
               "opposite order).")
    vcode(r"""module tb_race;
  reg clk = 0; reg [3:0] d = 0; wire [3:0] q2;
  pipe2 dut (.clk(clk), .d(d), .q2(q2));
  always #5 clk = ~clk;
  initial begin
    @(negedge clk) d = 4'd1;
    @(negedge clk) d = 4'd2;
    @(negedge clk) d = 4'd3;
    @(negedge clk) $display("after 3 edges: q2=%0d (a 2-stage pipe should show 2)", q2);
    $finish;
  end
endmodule""", "tb_race.v")
    out(["== RTL (iverilog) ==",
         "after 3 edges: q2=3 (a 2-stage pipe should show 2)",
         "== gates ==",
         "after 3 edges: q2=2 (a 2-stage pipe should show 2)",
         "== RTL, blocks swapped ==",
         "after 3 edges: q2=2 (a 2-stage pipe should show 2)"],
        "The same RTL gives different results depending on the order of two "
        "always blocks; the netlist always has two flops.")
    p("Both blocks wake on the same edge; the LRM leaves their order "
      "undefined (Chapter 5). If the first block runs first, q2 sees the "
      "**new** q1 and the pipeline collapses to one stage in simulation; "
      "synthesis always builds two flops. Another simulator, another "
      "compile option or an unrelated edit can flip the order. **Rule**: "
      "in clocked blocks use only non-blocking `<=`; in combinational "
      "blocks use only blocking `=`; never mix them for the same "
      "variable. (Blocking assignments inside a single clocked block, e.g. "
      "`q1 = d; q2 = q1;`, are not a race: both sim and synthesis collapse "
      "them to one flop - a different, but equally unintended, result.)")
    h3("6. Initial values, delays and x-assignments")
    vcode(r"""module cnt_noreset (input clk, output reg [3:0] cnt);
  initial cnt = 4'd0;              // works in RTL sim; an ASIC flop has no power-up value
  always @(posedge clk) cnt <= cnt + 4'd1;
endmodule""", "init.v - relying on an initial block instead of a reset.")
    out(["== RTL ==", "after 3 clocks: cnt=0011",
         "== gates (ASIC: init values dropped) ==",
         "after 3 clocks: cnt=xxxx"],
        "Yosys synth; setattr -unset init (as an ASIC flow does); "
        "re-simulated with Icarus. The x never clears: x + 1 = x.")
    vcode(r"""module xa (input [1:0] sel, input a, b, output reg y, output d);
  assign #2 d = a;                   // delay: ignored by synthesis
  always @* begin
    case (sel)
      2'b00:   y = a;
      2'b01:   y = b;
      default: y = 1'bx;             // "don't care": synthesis may pick 0 or 1
    endcase
  end
endmodule""", "xa.v - a delay and an x-assignment.")
    out(["  assign _0_ = sel[0] & ~(sel[1]);",
         "  assign y = _0_ ? b : a;",
         "  assign d = a;"],
        "The body of the Yosys netlist: the #2 is gone, and the don't-care "
        "was resolved to y = a for sel = 1x.")
    out(["== RTL ==", "t=1 sel=10 a=1 b=0 -> y=x d=x",
         "t=3 sel=10 a=1 b=0 -> y=x d=1",
         "== netlist ==", "t=1 sel=10 a=1 b=0 -> y=1 d=1",
         "t=3 sel=10 a=1 b=0 -> y=1 d=1"],
        "Same testbench on RTL and netlist: RTL shows x (and a 2 ns delay "
        "on d); the gates show a definite value immediately.")
    p("Assigning x is legitimate - it gives the optimiser freedom and makes "
      "the simulation show x if the \"impossible\" case happens - provided "
      "that the case really is impossible and a checker watches for it. "
      "The opposite RTL hazard is **X-optimism**: `if (sel_x) ... else ...` "
      "takes the else branch when sel_x is x, so RTL produces a clean value "
      "that the hardware may not. Delays in RTL are ignored by synthesis and "
      "only serve to hide races; the one accepted use is a small `#1` on "
      "non-blocking assignments in some legacy code bases to make waveforms "
      "readable, which modern teams avoid.")
    h3("7. Functions with side effects and other traps")
    p("A function that writes a module-level variable (a counter of calls, "
      "a debug flag) is executed by the simulator **each time** its "
      "expression is evaluated - which depends on events - while synthesis "
      "inlines it once per call site and turns the side effect into "
      "ordinary logic (Yosys built a register for such a counter). Keep "
      "functions pure: outputs depend only on inputs, no global writes, no "
      "static locals relied upon between calls (declare them `automatic`). "
      "Other classic mismatch sources:")
    tbl(["Mechanism", "Simulation", "Synthesis", "Prevention"],
        [["Missing sensitivity entry", "Latch-like on the missing input",
          "Combinational", "`always @*` / `always_comb`"],
         ["full_case / parallel_case", "Holds value / priority",
          "Don't care / parallel", "`default`; `unique`/`priority case`"],
         ["casex / casez with x/z input", "Wildcard match", "Real logic",
          "`case`, `case inside`, x-checks"],
         ["Blocking in clocked blocks", "Order-dependent race",
          "Flops", "`<=` in clocked logic"],
         ["initial values", "Known power-up", "Ignored (ASIC)",
          "Reset every control flop"],
         ["Delays `#n`", "Delayed", "Ignored", "No delays in RTL"],
         ["x-assignment / `if (x)`", "x or else-branch", "0 or 1",
          "Assertions, X-prop simulation"],
         ["`===` / `!==` in RTL", "Compares x/z exactly", "Treated as ==",
          "Use only in testbenches"],
         ["Function side effects", "Per evaluation", "Per call site",
          "Pure, automatic functions"],
         ["`ifdef SYNTHESIS` regions", "Code present", "Code absent",
          "Only non-functional code inside"],
         ["Out-of-range index", "Read gives x, write ignored",
          "Some value / aliasing", "Size arrays to powers of two or check"]],
        widths=[26, 22, 20, 32])
    box("key", "The mismatch safety net",
        "1) **Lint** every file (Verilator `--lint-only -Wall`, Spyglass, "
        "Ascent) with rules for sensitivity lists, latches, blocking/"
        "non-blocking use, case completeness and x-assignments. 2) Read the "
        "**synthesis log** for latches, ignored delays and constant "
        "registers. 3) Run **equivalence checking** RTL vs. netlist on every "
        "netlist. 4) Run a small set of **gate-level simulations** "
        "(Chapter 9), which catch what the first three cannot - notably "
        "reset and x-propagation problems.")

    # ------------------------------------------------------------------
    h2("Coding for reuse")
    p("Code that is synthesizable is necessary but not sufficient: IP is "
      "reused across projects, technologies and teams for a decade. The "
      "habits that make that possible:")
    bul(["**One module per file**, file named after the module; ANSI port "
         "lists with directions and widths; `default_nettype none` at the "
         "top and `wire` restored at the end (Chapter 8).",
         "**Parameterise** widths and depths with typed, named parameters; "
         "derive everything else with `localparam` and $clog2; check "
         "illegal parameter values at elaboration (Chapter 7).",
         "**Register outputs** of a block (or document which are "
         "combinational), so timing budgets at integration are predictable.",
         "**No technology cells in RTL**: clock gates, synchronizers, "
         "SRAMs and pads go behind thin wrapper modules with a behavioural "
         "model for simulation and a technology-specific implementation.",
         "**Explicit reset strategy**: reset control/state flops; leave pure "
         "datapath flops without reset if the methodology allows (saves "
         "area and routing), but never rely on initial values.",
         "**One clock per always block**, one edge; clock-domain crossings "
         "only through the approved synchronizer cells.",
         "**Naming conventions** that tools and people can parse: `_n` for "
         "active-low, `_q`/`_d` for flop outputs/inputs, `i_`/`o_` or `_i`/"
         "`_o` for ports, `u_` for instances, `g_` for generate blocks.",
         "**Keep the synthesizable subset of the target tools**, including "
         "the weakest one in the flow (lint, formal, emulation, FPGA "
         "prototyping)."])
    box("expert", "Interview insight: what is really wrong with this code?",
        "Interviewers love to show a 10-line always block and ask what "
        "hardware it builds. Answer in the order the tool thinks: (1) is it "
        "clocked (edge in the sensitivity list) or combinational? (2) for "
        "combinational: is every output assigned on every path (else "
        "latch)? is the sensitivity list complete? (3) for clocked: are "
        "assignments non-blocking? is the reset template exact? (4) what do "
        "case statements do with uncovered values and x? (5) is any "
        "variable assigned in two always blocks (multiple drivers - an error "
        "in synthesis, a race in simulation)?")

    h2("Summary")
    bul(["Synthesis recognises templates; simulation executes literally. "
         "Code to the templates so that both mean the same hardware.",
         "Combinational: `always @*`, blocking `=`, defaults first, every "
         "output on every path, case with default.",
         "Sequential: edge-triggered block, non-blocking `<=`, exact "
         "async/sync reset template, enable as `else if (en)`.",
         "Memories follow the target's RAM templates; ASIC SRAMs are "
         "instantiated macros behind wrappers. Three-states only in the "
         "pad ring.",
         "Mismatch mechanisms demonstrated: incomplete sensitivity lists, "
         "full_case, casex with x, blocking races, initial values, delays, "
         "x-assignment; plus side-effect functions, `===`, ifdef regions.",
         "The safety net is lint + synthesis-log review + equivalence "
         "checking + targeted gate-level simulation."])
    h2("Exercises")
    bul(["Write an 8-bit up/down counter with synchronous load, "
         "asynchronous active-low reset and saturation at 0 and 255. "
         "Synthesize it with Yosys, simulate RTL and netlist with the same "
         "testbench and compare.",
         "Take `latch_bug` from this chapter and fix it three different "
         "ways (default assignment, default item, SystemVerilog "
         "`always_comb` with `unique case`). Which fix still lets "
         "simulation detect sel = 11?",
         "Modify `pipe2` so that it uses blocking assignments inside a "
         "single always block in the order `q2 = q1; q1 = d;`. Does it "
         "work? Is it a race? Why do coding guidelines still forbid it?",
         "Write a module whose RTL simulation differs from its netlist "
         "because of an `ifdef SYNTHESIS` region. Show the mismatch with "
         "Yosys (which defines SYNTHESIS) and Icarus.",
         "Infer a 64 x 16 dual-port RAM (one write port, one synchronous "
         "read port on different addresses) and check with Yosys `stat` "
         "that it is recognised as a memory. What changes if the read is "
         "asynchronous?",
         "Review a given always block and list, in order, the five "
         "questions of the interview box above, answering each one."],
        ordered=True)
