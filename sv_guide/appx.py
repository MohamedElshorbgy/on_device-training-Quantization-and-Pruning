"""Appendices A-D of "Verilog & SystemVerilog for SoC & ASIC - The Complete Guide".

A  Keywords and syntax quick reference
B  Operators, sizing rules and system tasks reference
C  100 Verilog/SystemVerilog interview questions with answers
D  Standards, tools and resources

Every snippet with an output card was compiled and run with Icarus Verilog 12
(`iverilog -g2012`) or Verilator 5.020 (`verilator --binary --timing`), and the
output pasted from that run. Templates that no open simulator here executes
(covergroups, concurrent SVA, constraints, program/clocking blocks) were
parsed and fully elaborated with the open-source slang front end (pyslang 11)
with zero errors and zero warnings.
"""

from sv_guide.common import *  # noqa: F401,F403


def _kw(words):
    """Render a list of keywords as a comma-separated run of code spans."""
    return ", ".join("`%s`" % w for w in words.split())


# =============================================================================
# Appendix A - keywords and syntax quick reference
# =============================================================================
def _appx_a():
    appendix("Keywords and Syntax Quick Reference")
    p("This appendix is the page you keep open while writing code. It lists every "
      "reserved word of Verilog-2005 and every word SystemVerilog added, grouped by "
      "what the word is for, and then gives a compact, correct template for each "
      "major construct. Each template was checked by a tool: the design subset with "
      "Icarus Verilog and Verilator, and the verification-only constructs "
      "(covergroups, properties, clocking blocks, programs, constraints) by full "
      "elaboration in the open-source **slang** compiler, because neither open "
      "simulator here executes them. Chapter numbers point to the full treatment.")

    ah2("Verilog-2005 reserved words (IEEE 1364-2005, Annex B)")
    p("Verilog-2005 has 123 reserved words. Keywords are lower case and "
      "case-sensitive: `Module` is a legal identifier, `module` is not. A reserved "
      "word can still be used as a name by writing it as an __escaped identifier__ "
      "(`\\module ` - backslash, the name, then white space), which is how netlist "
      "writers cope with names from other languages.")
    tbl(["Category", "Keywords"],
        [["Design units and blocks",
          _kw("module macromodule endmodule primitive endprimitive table endtable "
              "function endfunction task endtask specify endspecify generate "
              "endgenerate genvar begin end fork join")],
         ["Ports, nets and variables",
          _kw("input output inout wire uwire tri tri0 tri1 wand wor triand trior "
              "trireg supply0 supply1 reg integer real realtime time event "
              "signed unsigned scalared vectored automatic")],
         ["Parameters",
          _kw("parameter localparam defparam specparam")],
         ["Procedural code",
          _kw("initial always assign deassign force release if else case casex "
              "casez endcase default for forever repeat while wait disable "
              "posedge negedge edge")],
         ["Gate and switch primitives",
          _kw("and nand or nor xor xnor not buf bufif0 bufif1 notif0 notif1 nmos "
              "pmos rnmos rpmos cmos rcmos tran tranif0 tranif1 rtran rtranif0 "
              "rtranif1 pullup pulldown")],
         ["Drive and charge strengths",
          _kw("supply0 supply1 strong0 strong1 pull0 pull1 weak0 weak1 highz0 "
              "highz1 small medium large")],
         ["Specify blocks and pulse control",
          _kw("ifnone pulsestyle_onevent pulsestyle_ondetect showcancelled "
              "noshowcancelled")],
         ["Configurations (Chapter 7)",
          _kw("config endconfig design instance cell use liblist library incdir "
              "include")]],
        widths=[24, 76], bold_first=True,
        caption="Verilog-2005 keywords by category (`supply0`/`supply1` appear twice "
        "because they are both net types and strengths). `uwire` is the only word "
        "new in 1364-2005; the rest date from 1995 or 2001.")

    ah2("Words SystemVerilog added (IEEE 1800)")
    p("SystemVerilog is a superset of Verilog, so every word above stays reserved "
      "and about 130 more join it. The additions arrived in three waves: IEEE "
      "1800-2005 (the bulk), 1800-2009 (temporal logic, checkers, `let`) and "
      "1800-2012 (interface classes, soft constraints, user-defined nets). "
      "1800-2017 added no keywords, and 1800-2023 expresses its new features "
      "with existing words (for example the `:initial`, `:extends` and `:final` "
      "method qualifiers), so a 2012 keyword list is still complete for practical "
      "work - but check Annex B of the edition your tools claim.")
    tbl(["Category", "Keywords (edition in brackets if after 2005)"],
        [["Data types and declarations",
          _kw("bit byte shortint int longint logic shortreal chandle string enum "
              "struct union packed tagged typedef type var void const static") +
          ", `nettype` `interconnect` [2012], `untyped` [2009]"],
         ["Procedural blocks and statements",
          _kw("always_comb always_ff always_latch final unique priority do break "
              "continue return foreach inside iff join_any join_none wait_order "
              "randcase randsequence matches alias") + ", `unique0` [2009]"],
         ["Structure and scoping",
          _kw("interface endinterface modport package endpackage import export "
              "program endprogram clocking endclocking bind timeunit timeprecision "
              "extern context forkjoin") +
          ", `checker` `endchecker` `let` `global` [2009]"],
         ["Classes (OOP)",
          _kw("class endclass extends new null this super local protected pure "
              "virtual") + ", `implements` [2012]"],
         ["Randomization",
          _kw("rand randc constraint solve before dist with") + ", `soft` [2012]"],
         ["Assertions (SVA)",
          _kw("assert assume cover expect property endproperty sequence "
              "endsequence first_match intersect throughout within") + ", " +
          _kw("restrict implies until s_until until_with s_until_with nexttime "
              "s_nexttime s_always eventually s_eventually accept_on reject_on "
              "sync_accept_on sync_reject_on strong weak") + " [2009]"],
         ["Functional coverage",
          _kw("covergroup endgroup coverpoint cross bins illegal_bins ignore_bins "
              "binsof wildcard")]],
        widths=[24, 76], bold_first=True,
        caption="SystemVerilog keyword additions by category.")
    box("warn", "PITFALL - legacy code that stops compiling",
        ["Moving a Verilog file to SV mode (`.sv` suffix, `-sv`, `-g2012`) can break "
         "it because ordinary-looking names are now keywords: `bit`, `byte`, `int`, "
         "`logic`, `type`, `ref`, `do`, `final`, `class`, `new`, `this`, `soft`, "
         "`global`, `matches`, `interface`, `package`, `program`, `sequence`. Even "
         "pure Verilog bites: `small`, `medium` and `large` are charge strengths "
         "and `cell`, `design`, `instance`, `library`, `use` are configuration "
         "words (this very appendix hit `small`, `large` and `matches` while its "
         "templates were being checked).",
         "Fix it per file by bracketing the old code with the `begin_keywords "
         "\"1364-2005\"` and `end_keywords` directives (each written with a leading "
         "grave accent, Chapter 8), which tell the compiler which keyword set the "
         "enclosed text was written against."])

    ah2("Lexical cheat sheet")
    tbl(["Item", "Form", "Notes"],
        [["Comments", "`// line`   `/* block */`", "Block comments do not nest"],
         ["Identifiers", "`[a-zA-Z_][a-zA-Z0-9_$]*`, escaped `\\any_chars `",
          "Case-sensitive; `$` cannot start a user name (reserved for system tasks)"],
         ["Sized literal", "`<size>'<s?><base><digits>`: `8'hA5`, `4'sb1010`, "
          "`12'o7_7_7`", "Base `b o d h` (either case); `x z ?` legal in b/o/h"],
         ["Unsized literal", "`42`, `'hFF`, `'b1`", "At least 32 bits; plain "
          "decimal is signed, based is unsigned"],
         ["Fill literal (SV)", "`'0 '1 'x 'z`", "Every bit of the context width"],
         ["Real", "`3.14`, `1.5e-9`, `2E3`", "`.5` and `5.` are illegal"],
         ["Time literal (SV)", "`10ns`, `2.5us`, `1step`", "No space before the "
          "unit; units `s ms us ns ps fs`"],
         ["String", "`\"text\\n\"`", "8 bits per character when assigned to a "
          "vector; SV adds `\\v \\f \\a \\x41`"],
         ["System name", "`$display`, `$clog2`", "Built-in or PLI/VPI tasks and "
          "functions"],
         ["Directive", "`define`, `ifdef`, `timescale`, `include` preceded by a "
          "grave accent", "Processed before parsing (Chapter 8)"],
         ["Attribute", "`(* keep = 1 *)`", "Tool hints attached to the next item"]],
        widths=[18, 42, 40], bold_first=True)

    ah2("Template: package and module")
    p("A package holds shared types, parameters and functions (Chapter 15). The "
      "module header uses the ANSI style with the parameter port list first; "
      "a `localparam` in the parameter port list (legal in SystemVerilog) "
      "cannot be overridden. Imports in the header make package names visible to the port "
      "list.")
    code(['package bus_pkg;',
          '  parameter int AW = 32;                     // package parameters are constants',
          '  typedef logic [AW-1:0] addr_t;',
          '  typedef enum logic [1:0] {IDLE, BUSY, DONE, ERR} state_e;',
          '  typedef struct packed {',
          '    addr_t      addr;',
          '    logic [7:0] len;',
          '    logic       write;',
          '  } req_t;',
          '  function automatic logic [7:0] parity8(logic [7:0] d);',
          "    return {7'b0, ^d};",
          '  endfunction',
          'endpackage'], caption="Package template (Verilator lint and slang "
         "elaboration clean)")
    code(['module fifo_ctrl',
          '  import bus_pkg::*;                         // import in the module header',
          '#(',
          '  parameter  int DEPTH = 8,                  // overridable',
          '  localparam int PW    = $clog2(DEPTH)       // not overridable',
          ') (',
          '  input  logic          clk,',
          '  input  logic          rst_n,',
          '  input  logic          push, pop,',
          '  input  req_t          wdata,',
          '  output req_t          rdata,',
          '  output logic [PW:0]   count',
          ');',
          '  req_t       mem [DEPTH];                   // unpacked array: DEPTH entries',
          '  logic [PW-1:0] wp, rp;',
          '',
          '  always_ff @(posedge clk or negedge rst_n)',
          '    if (!rst_n) begin',
          "      wp <= '0; rp <= '0; count <= '0;",
          '    end else begin',
          "      if (push) begin mem[wp] <= wdata; wp <= wp + 1'b1; end",
          "      if (pop)  rp <= rp + 1'b1;",
          "      count <= count + (PW+1)'(push) - (PW+1)'(pop);",
          '    end',
          '',
          '  assign rdata = mem[rp];',
          'endmodule',
          '',
          'module top;',
          '  import bus_pkg::*;',
          '  logic clk = 0, rst_n = 0, push = 0, pop = 0;',
          "  req_t wdata = '0, rdata;",
          '  logic [3:0] count;',
          '  fifo_ctrl #(.DEPTH(8)) u_fifo (.clk, .rst_n, .push, .pop,    // .name implicit',
          '                                 .wdata, .rdata, .count(count)); // named',
          'endmodule'], caption="Module template with header import, "
         "parameters, `.name` implicit connections and a named connection "
         "(Icarus, Verilator and slang clean)")
    tbl(["Port connection style", "Example", "Rule"],
        [["Positional", "`fifo_ctrl u (clk, rst_n, ...);`", "Order must match; "
          "fragile - avoid beyond primitives"],
         ["Named", "`.count(count)`", "Explicit; unconnected ports allowed "
          "(`.x()`)"],
         ["Implicit `.name` (SV)", "`.clk`", "Same name and compatible type "
          "must exist; no implicit nets created"],
         ["Wildcard `.*` (SV)", "`fifo_ctrl u (.*);`", "Connects every port to a "
          "same-named signal; explicit connections override"]],
        widths=[22, 34, 44], bold_first=True)

    ah2("Template: interface, modport and clocking block")
    code(['interface bus_if #(parameter int DW = 32) (input logic clk);',
          '  logic          valid, ready;',
          '  logic [DW-1:0] data;',
          '',
          '  clocking cb @(posedge clk);                // testbench view, race-free',
          '    default input #1step output #1;',
          '    output valid, data;',
          '    input  ready;',
          '  endclocking',
          '',
          '  modport mst  (output valid, data, input  ready);',
          '  modport slv  (input  valid, data, output ready);',
          '  modport tb   (clocking cb);',
          '',
          '  function automatic bit fire();             // methods may live in interfaces',
          '    return valid && ready;',
          '  endfunction',
          'endinterface',
          '',
          'module sink (bus_if.slv b);                  // modport-typed port',
          "  assign b.ready = 1'b1;",
          'endmodule',
          '',
          'module top_if;',
          '  logic clk = 0;',
          '  bus_if #(.DW(16)) b (.clk);',
          '  sink u_sink (.b(b));                       // connect instance, modport chosen above',
          'endmodule'], caption="Interface template (slang clean; Verilator "
         "5.020 rejects `modport ... (clocking cb)` as unsupported)")
    p("Instantiate an interface like a module; pass it through a port typed "
      "`bus_if.slv` (restricted by the modport) or `bus_if` (full access). A class "
      "reaches it through a __virtual interface__ handle, `virtual bus_if.tb vif;` "
      "(Chapter 16).")

    ah2("Template: typedef, enum, struct and union")
    code(['module t_types;',
          "  typedef enum logic [2:0] {RD = 3'b001, WR = 3'b010, NOP = 3'b100} op_e;",
          '  typedef struct packed {                    // packed: a 16-bit vector, first field = MSBs',
          '    op_e        op;                          // [15:13]',
          '    logic [4:0] reg_id;                      // [12:8]',
          '    logic [7:0] imm;                         // [7:0]',
          '  } instr_t;',
          '  typedef union packed {                     // all members must be the same width',
          '    instr_t      f;',
          '    logic [15:0] raw;',
          '  } instr_u;',
          '  typedef struct {                           // unpacked: may hold any types',
          '    string name;',
          '    real   delay;',
          '    int    beats[4];',
          '  } txn_t;',
          '',
          '  instr_u u;',
          '  txn_t   t;',
          '  op_e    o;',
          '  initial begin',
          "    u.f = '{op: WR, reg_id: 5'd3, imm: 8'hA5};           // assignment pattern",
          '    $display("raw=%h op=%s reg=%0d", u.raw, u.f.op.name(), u.f.reg_id);',
          "    o = op_e'(3'b100);                                  // static cast to the enum",
          '    $display("o=%s first=%s num=%0d", o.name(), o.first().name(), o.num());',
          '    o = o.next();                                       // wraps from last to first',
          '    $display("o.next()=%s", o.name());',
          '    t = \'{name: "burst", delay: 2.5, beats: \'{default: 0}};',
          '    $display("%s has %0d beats, $bits(instr_t)=%0d", t.name, $size(t.beats), $bits(instr_t));',
          '    $finish;',
          '  end',
          'endmodule'], caption="User-defined types (Verilator 5.020)")
    out(['raw=43a5 op=WR reg=3',
         'o=NOP first=RD num=3',
         'o.next()=RD',
         'burst has 4 beats, $bits(instr_t)=16'])
    p("`next()` wraps from the last member to the first; the static cast "
      "`op_e'(...)` is unchecked, so use `$cast` when the value might not be a "
      "legal member (Appendix B, casting table).")

    ah2("Template: always_comb, always_ff and always_latch")
    code(['module t_alw (',
          '  input  logic       clk, rst_n, en, g,',
          '  input  logic [1:0] sel,',
          '  input  logic [7:0] a, b, c, d,',
          '  output logic [7:0] y, q, l',
          ');',
          '  always_comb begin                          // combinational: runs at time 0, full sensitivity',
          '    unique case (sel)                        // parallel + full: warns if no/multiple match',
          "      2'd0: y = a;",
          "      2'd1: y = b;",
          "      2'd2: y = c;",
          "      2'd3: y = d;",
          '    endcase',
          '  end',
          '',
          '  always_ff @(posedge clk or negedge rst_n)  // exactly one event control; flops only',
          "    if (!rst_n)  q <= '0;",
          "    else if (en) q <= q + 8'd1;",
          '',
          '  always_latch                               // intended latch (tools check it is one)',
          '    if (g) l <= a;',
          'endmodule'], caption="The three intent-specific processes "
         "(Icarus, Verilator and slang clean)")
    tbl(["Process", "Sensitivity", "Rules enforced", "Infers"],
        [["`always_comb`", "Implicit: every value read, including inside called "
          "functions", "Runs once at time 0; no timing controls; no other process "
          "may write its outputs", "Combinational logic (tools warn on a latch)"],
         ["`always_latch`", "Implicit, as `always_comb`", "Same rules",
          "Level-sensitive latch"],
         ["`always_ff`", "Exactly one event control at the top", "No blocking "
          "timing controls inside; outputs written by this block only", "Flip-flops"],
         ["`always @*`", "Implicit, but not inside functions", "None", "Whatever "
          "you wrote - often an accidental latch"],
         ["`always`", "Whatever you write", "None", "Testbench clocks, legacy RTL"]],
        widths=[16, 28, 34, 22], bold_first=True)

    ah2("Template: function and task")
    code(['module t_ft;',
          '  // function: zero time, returns a value (or void); SV allows output/ref args',
          '  function automatic int unsigned popcnt(input logic [31:0] v, input int start = 0);',
          '    int unsigned n = 0;',
          "    for (int i = start; i < 32; i++) n += 32'(v[i]);",
          '    return n;',
          '  endfunction',
          '',
          '  function automatic void swap(ref int a, ref int b);   // ref: pass by reference',
          '    int t = a; a = b; b = t;',
          '  endfunction',
          '',
          '  // task: may consume time; outputs are copied back when the task returns',
          '  task automatic pulse(output logic sig, input int unsigned width);',
          "    sig = 1'b1; #width; sig = 1'b0;",
          '  endtask',
          '',
          '  int x = 3, y = 7;',
          '  logic p;',
          '  initial begin',
          '    $display("popcnt=%0d popcnt(start=8)=%0d", popcnt(32\'hF0F0), popcnt(32\'hF0F0, 8));',
          '    swap(x, y);',
          '    $display("after swap x=%0d y=%0d", x, y);',
          '    pulse(p, 5);',
          '    $display("t=%0t p=%b", $time, p);',
          "    void'(popcnt(1));                                    // discard a return value",
          '  end',
          'endmodule'], caption="Functions, tasks, default arguments and "
         "`ref` (Verilator 5.020; Icarus 12 does not support `ref` arguments)")
    out(['popcnt=8 popcnt(start=8)=4',
         'after swap x=7 y=3',
         't=5 p=0'])
    tbl(["Feature", "function", "task"],
        [["Consumes time (`#`, `@`, `wait`)", "Never", "May"],
         ["Returns a value", "Yes, or `void`", "No (use `output`/`ref` arguments)"],
         ["Can call", "Functions only (and fork/join_none in SV)",
          "Functions and tasks"],
         ["Default lifetime in a module", "static", "static"],
         ["Argument directions", "`input output inout ref` (SV)",
          "`input output inout ref`"],
         ["Synthesizable", "Yes, as combinational logic", "Yes if it has no timing "
          "control"]],
        widths=[34, 33, 33], bold_first=True)

    ah2("Template: generate")
    code(['module t_gen #(parameter int N = 4, parameter bit USE_FAST = 1) (',
          '  input  logic [N-1:0] a, b,',
          '  output logic [N-1:0] y,',
          '  output logic [N:0]   sum',
          ');',
          '  // generate-for: genvar loop, named block gives hierarchical names g_bit[i]',
          '  for (genvar i = 0; i < N; i++) begin : g_bit',
          '    assign y[i] = a[i] ^ b[i];',
          '  end',
          '',
          '  // generate-if: elaboration-time choice between implementations',
          '  if (USE_FAST) begin : g_fast',
          '    assign sum = a + b;',
          '  end else begin : g_ripple',
          '    logic [N:0] c;',
          "    assign c[0] = 1'b0;",
          '    for (genvar i = 0; i < N; i++) begin : g_fa',
          '      assign {c[i+1], sum[i]} = a[i] + b[i] + c[i];',
          '    end',
          '    assign sum[N] = c[N];',
          '  end',
          '',
          '  // generate-case',
          '  case (N)',
          '    1:       begin : g_one  initial $display("N=1");      end',
          '    default: begin : g_many initial $display("N=%0d", N); end',
          '  endcase',
          'endmodule',
          '',
          'module t_gen_tb;',
          "  logic [3:0] a = 4'd9, b = 4'd12, y1, y2;",
          '  logic [4:0] s1, s2;',
          '  t_gen #(.N(4), .USE_FAST(1)) u1 (.a, .b, .y(y1), .sum(s1));',
          '  t_gen #(.N(4), .USE_FAST(0)) u2 (.a, .b, .y(y2), .sum(s2));',
          '  initial #1 $display("fast=%0d ripple=%0d xor=%b carries=%b", s1, s2, y2, u2.g_ripple.c);',
          'endmodule'], caption="generate-for, generate-if and generate-case; "
         "the `generate`/`endgenerate` keywords are optional since 1364-2005 "
         "(Icarus 12)")
    out(['N=4',
         'N=4',
         'fast=21 ripple=21 xor=0101 carries=10000'])
    p("Label every generate block: the label is part of the hierarchical name "
      "(`u2.g_ripple.c`), unlabeled blocks get tool-specific `genblkN` names that "
      "break scripts, waveforms and SDC constraints.")

    ah2("Template: class")
    code(['package tb_pkg;',
          '  typedef class scoreboard;                  // forward declaration',
          '',
          '  virtual class base_item;                   // abstract: cannot be constructed',
          '    static int count;                        // one copy shared by all objects',
          '    local  int id;                           // visible only inside base_item',
          '    function new();',
          '      id = count++;',
          '    endfunction',
          '    pure virtual function string convert2string();',
          '    function int get_id(); return id; endfunction',
          '  endclass',
          '',
          '  class bus_item extends base_item;',
          '    rand bit [31:0] addr;',
          '    rand bit [7:0]  len;',
          '    randc bit [1:0] kind;                    // cyclic random',
          '    constraint c_len  { len inside {[1:16]}; }',
          "    constraint c_addr { addr[1:0] == 2'b00; soft addr < 32'h1000; }",
          '    function new();',
          '      super.new();',
          '    endfunction',
          '    virtual function string convert2string();',
          '      return $sformatf("#%0d addr=%h len=%0d", get_id(), addr, len);',
          '    endfunction',
          '    function void post_randomize();          // callback after randomize()',
          '    endfunction',
          '  endclass',
          '',
          '  class fifo #(type T = int, int DEPTH = 4); // parameterized class',
          '    protected T q[$];',
          '    function bit put(T t);',
          '      if (q.size() >= DEPTH) return 0;',
          '      q.push_back(t);',
          '      return 1;',
          '    endfunction',
          '    extern function T get();                 // out-of-block definition below',
          '  endclass',
          '  function fifo::T fifo::get();',
          '    return q.pop_front();',
          '  endfunction',
          '',
          '  interface class printable;                 // SV-2012 interface class',
          '    pure virtual function void print();',
          '  endclass',
          '',
          '  class scoreboard implements printable;',
          '    int unsigned n_match;',
          '    virtual function void print(); $display("n_match=%0d", n_match); endfunction',
          '  endclass',
          'endpackage'], caption="Class template: abstract base, static and "
         "local members, pure virtual method, constraints, parameterized class with "
         "an `extern` method, interface class (slang clean)")

    ah2("Template: program block")
    code(['program automatic test (bus_if.tb bif);      // program block: runs in the Reactive region',
          '  initial begin',
          "    bif.cb.valid <= 1'b0;",
          '    repeat (2) @(bif.cb);',
          "    bif.cb.valid <= 1'b1;",
          "    bif.cb.data  <= 32'hCAFE;",
          '    @(bif.cb iff bif.cb.ready);              // wait for a sampled ready',
          "    bif.cb.valid <= 1'b0;",
          '  end                                        // implicit $finish when all program',
          'endprogram                                   // initial blocks have ended'], caption="Program block driving through a clocking "
         "block (slang clean, elaborated together with the interface template)")

    ah2("Template: covergroup")
    code(['module cov_demo (input logic clk, input logic [3:0] op, input logic [1:0] mode,',
          '                 input logic valid);',
          '  covergroup cg_op @(posedge clk iff valid);',
          '    option.per_instance = 1;',
          '    cp_op : coverpoint op {',
          '      bins zero      = {0};',
          '      bins low[]     = {[1:3]};              // one bin per value',
          '      bins high      = {[4:14]};',
          '      illegal_bins bad = {15};',
          '    }',
          '    cp_mode : coverpoint mode;               // automatic bins: 4 values',
          '    x_op_mode : cross cp_op, cp_mode {',
          '      ignore_bins no_zero = binsof(cp_op.zero);',
          '    }',
          '  endgroup',
          '  cg_op cg = new();                          // must be constructed',
          '',
          '  covergroup cg_trans with function sample(logic [1:0] m);',
          '    coverpoint m { bins up = (0 => 1 => 2); bins wrap = (3 => 0); }',
          '  endgroup',
          '  cg_trans ct = new();',
          '  always @(posedge clk) if (valid) ct.sample(mode);',
          'endmodule'], caption="Covergroups with an event, explicit bins, "
         "cross with `ignore_bins`, and a `sample()` override with transition bins "
         "(slang clean; needs a commercial simulator to execute)")

    ah2("Template: sequence, property and assertion statements")
    code(['module sva_demo (input logic clk, rst_n, req, gnt, done, input logic [7:0] data);',
          '  default clocking dcb @(posedge clk); endclocking',
          '  default disable iff (!rst_n);',
          '',
          '  sequence s_handshake;',
          '    req ##[1:4] gnt;                         // gnt 1 to 4 cycles after req',
          '  endsequence',
          '',
          '  property p_req_gets_gnt;',
          '    req |-> s_handshake;                     // overlapping implication',
          '  endproperty',
          '',
          '  property p_stable_until_done(sig);',
          '    $rose(req) |=> $stable(sig) throughout done [->1];',
          '  endproperty',
          '',
          '  a_gnt    : assert property (p_req_gets_gnt) else $error("req not granted");',
          '  a_stable : assert property (p_stable_until_done(data));',
          '  m_in     : assume property (gnt |-> req);  // constraint for formal',
          '  c_b2b    : cover  property (req ##1 !req ##1 req);',
          '  a_known  : assert property (!$isunknown({req, gnt}));',
          '',
          '  always_comb begin                          // immediate (non-temporal) assertion',
          '    a_imm : assert (!(gnt && !rst_n)) else $warning("gnt in reset");',
          '  end',
          'endmodule'], caption="Concurrent and immediate assertions (slang "
         "clean; Verilator 5.020 rejects the `##[m:n]` range, run on a commercial "
         "simulator or SymbiYosys with a commercial front end)")

    ah2("Template: fork variants")
    code(['module t_fork;',
          '  task automatic worker(string name, int d);',
          '    #d $display("%3t  %s done", $time, name);',
          '  endtask',
          '  initial begin',
          '    fork worker("A", 10); worker("B", 20); join        // wait for all',
          '    $display("%3t  join finished", $time);',
          '    fork worker("C", 10); worker("D", 20); join_any    // wait for first',
          '    $display("%3t  join_any finished", $time);',
          '    fork worker("E", 5); join_none                     // do not wait',
          '    $display("%3t  join_none returned", $time);',
          '    wait fork;                                         // D and E still running',
          '    $display("%3t  wait fork finished", $time);',
          '    fork worker("F", 10); worker("G", 50); join_any',
          '    disable fork;                                      // kill G',
          '    $display("%3t  disable fork: G killed", $time);',
          '    #100 $finish;',
          '  end',
          'endmodule'], caption="All four fork endings plus `wait fork` and "
         "`disable fork`")
    out([' 10  A done',
         ' 20  B done',
         ' 20  join finished',
         ' 30  C done',
         ' 30  join_any finished',
         ' 30  join_none returned',
         ' 35  E done',
         ' 40  D done',
         ' 40  wait fork finished',
         ' 50  F done',
         ' 50  disable fork: G killed'], caption="Identical output from Verilator 5.020 and Icarus 12")
    tbl(["Construct", "Parent continues when", "Children after parent resumes"],
        [["`fork ... join`", "All children finished", "None left"],
         ["`fork ... join_any`", "First child finished", "Keep running"],
         ["`fork ... join_none`", "Immediately (children start when the parent "
          "next blocks)", "Keep running"],
         ["`wait fork;`", "All children of the current process finished",
          "-"],
         ["`disable fork;`", "Immediately", "All descendants of the current process "
          "killed - wrap in `fork begin ... end join` to limit the scope"]],
        widths=[22, 40, 38], bold_first=True)


# =============================================================================
# Appendix B - operators, sizing rules and system tasks
# =============================================================================
def _appx_b():
    appendix("Operators, Sizing Rules and System Tasks Reference")
    p("The rules in this appendix are the ones that decide what a line of RTL "
      "actually computes: how wide an expression is, whether it is signed, what "
      "happens to X and Z, and which built-in tasks exist. They are condensed from "
      "IEEE 1800-2017 clause 11 (operators and expressions) and clauses 20-21 "
      "(system tasks). Chapter 4 derives them with examples; Chapter 10 covers the "
      "system tasks in depth.")

    ah2("Operator precedence and associativity")
    tbl(["Level", "Operators", "Associativity"],
        [["1 (highest)", "`()` `[]` `::` `.`", "Left"],
         ["2", "Unary `+ - ! ~ & ~& | ~| ^ ~^ ^~`, `++ --`", "-"],
         ["3", "`**`", "Left"],
         ["4", "`* / %`", "Left"],
         ["5", "Binary `+ -`", "Left"],
         ["6", "`<< >> <<< >>>`", "Left"],
         ["7", "`< <= > >=`, `inside`, `dist`", "Left"],
         ["8", "`== != === !== ==? !=?`", "Left"],
         ["9", "Binary `&`", "Left"],
         ["10", "Binary `^ ~^ ^~`", "Left"],
         ["11", "Binary `|`", "Left"],
         ["12", "`&&`", "Left"],
         ["13", "`||`", "Left"],
         ["14", "`?:` (conditional)", "Right"],
         ["15", "`->` `<->` (implication, equivalence)", "Right"],
         ["16", "`= += -= *= /= %= &= ^= |= <<= >>= <<<= >>>=`, `:=` `:/`, `<=`",
          "None"],
         ["17 (lowest)", "`{}` `{{}}` (concatenation, replication)", "Concatenation"]],
        widths=[14, 66, 20], bold_first=True,
        caption="IEEE 1800-2017 Table 11-2. `**` is left-associative in the LRM, "
        "unlike mathematics: `2**3**2` is 64 in both Icarus and Verilator. "
        "Parenthesise.")

    ah2("Operator reference")
    tbl(["Group", "Operators", "Result", "Notes"],
        [["Arithmetic", "`+ - * / % **`", "max(L(i), L(j)) bits",
          "Any X/Z bit makes the whole result X; `/` truncates toward zero; "
          "sign of `%` follows the first operand"],
         ["Increment (SV)", "`i++ ++i i-- --i`", "L(i)", "Blocking side effect; "
          "undefined if the variable is used twice in one expression"],
         ["Assignment ops (SV)", "`+= -= *= /= %= &= |= ^= <<= >>= <<<= >>>=`",
          "L(lhs)", "Blocking; `a += b` is `a = a + b` with `a` evaluated once"],
         ["Relational", "`< <= > >=`", "1 bit", "X if any operand bit is X/Z; "
          "unsigned unless both operands signed"],
         ["Logical equality", "`== !=`", "1 bit", "X/Z anywhere -> X "
          "(unless a known bit already differs -> 0/1)"],
         ["Case equality", "`=== !==`", "1 bit", "Compares X and Z literally; never "
          "X; not synthesizable"],
         ["Wildcard equality (SV)", "`==? !=?`", "1 bit", "X/Z in the **right** "
          "operand are don't-cares"],
         ["Logical", "`! && || -> <->`", "1 bit", "`&&` and `||` short-circuit; "
          "operands reduced to 0/1/X"],
         ["Bitwise", "`~ & | ^ ~^ ^~`", "max(L(i), L(j))", "Per-bit 4-state tables "
          "below"],
         ["Reduction", "`& ~& | ~| ^ ~^`", "1 bit", "Unary; `^v` is even/odd parity"],
         ["Logical shift", "`<< >>`", "L(i)", "Fill with 0; shift amount "
          "self-determined, treated as unsigned; X amount -> all X"],
         ["Arithmetic shift", "`<<< >>>`", "L(i)", "`>>>` fills with the sign bit "
          "only if the **expression** is signed"],
         ["Conditional", "`c ? a : b`", "max(L(a), L(b))", "If `c` is X, the "
          "result merges `a` and `b` bit by bit (equal bits kept, others X)"],
         ["Concatenation", "`{a, b}`", "L(a) + L(b)", "Operands self-determined; "
          "unsized constants illegal; result unsigned"],
         ["Replication", "`{n{a}}`", "n x L(a)", "`n` must be a constant; `{0{a}}` "
          "is legal only inside a larger concatenation"],
         ["Streaming (SV)", "`{<<{a}}`, `{>>8{a}}`", "Sum of operand bits",
          "`<<` reverses in slices (default 1 bit); `>>` keeps order"],
         ["Set membership (SV)", "`a inside {1, [4:7], arr}`", "1 bit",
          "Uses `==` for singular values (`==?` style for X/Z in the set)"],
         ["Distribution (SV)", "`x dist {0 := 3, [1:9] :/ 1}`", "-",
          "Constraints only; `:=` weight per value, `:/` weight shared by range"],
         ["Cast (SV)", "`T'(e)`, `8'(e)`, `signed'(e)`", "Target", "See casting table"]],
        widths=[18, 26, 16, 40], bold_first=True)

    ah2("Expression bit-length rules (IEEE 1800-2017 Table 11-21)")
    p("Every operand is either **context-determined** (it is extended to the width "
      "of the whole expression, including the assignment target) or "
      "**self-determined** (its width is fixed by itself alone). The table gives "
      "L, the bit length of each expression form; i, j, k are operands.")
    tbl(["Expression", "Bit length", "Comment"],
        [["Unsized constant", "Same as `integer` (at least 32)", ""],
         ["Sized constant", "As given", ""],
         ["`i op j`, op in `+ - * / % & | ^ ^~ ~^`", "max(L(i), L(j))",
          "Operands context-determined"],
         ["`op i`, op in `+ - ~`", "L(i)", ""],
         ["`i op j`, op in `=== !== == != > >= < <= ==? !=?`", "1",
          "Operands sized to max(L(i), L(j)) - to each other, not to the LHS"],
         ["`i op j`, op in `&& || -> <->`", "1", "All operands self-determined"],
         ["`op i`, op in `& ~& | ~| ^ ~^ ^~ !`", "1", "Operand self-determined"],
         ["`i op j`, op in `>> << ** >>> <<<`", "L(i)", "j is self-determined"],
         ["`i ? j : k`", "max(L(j), L(k))", "i is self-determined"],
         ["`{i, ..., j}`", "L(i) + ... + L(j)", "All operands self-determined"],
         ["`{i{j, ..., k}}`", "i x (L(j) + ... + L(k))", "All self-determined"],
         ["`lhs = rhs`", "-", "RHS evaluated at max(L(lhs), L(rhs)), then "
          "truncated or extended to L(lhs)"]],
        widths=[40, 24, 36])
    code(['module sz;',
          "  logic [7:0] a = 8'd200, b = 8'd100;",
          '  logic [8:0] s9;',
          '  logic [7:0] s8;',
          "  logic signed [7:0] sa = -8'sd4;",
          "  logic [3:0] u4 = 4'd3;",
          '  initial begin',
          '    s9 = a + b;               // context: 9 bits -> carry kept',
          '    $display("s9 = a + b        = %0d", s9);',
          '    s9 = {a + b};             // concatenation: self-determined 8 bits',
          '    $display("s9 = {a + b}      = %0d", s9);',
          '    s9 = (a + b) >> 1;        // context 9 bits: carry kept, then shifted',
          '    $display("s9 = (a+b)>>1     = %0d", s9);',
          '    s8 = (a + b) >> 1;        // context 8 bits: carry lost',
          '    $display("s8 = (a+b)>>1     = %0d", s8);',
          '    $display("$bits(a+b)        = %0d", $bits(a + b));',
          '    $display("sa + u4 (unsigned)= %0d", sa + u4);',
          '    $display("sa + $signed(u4)  = %0d", sa + $signed(u4));',
          '    $display("-1 > 8\'d0         = %b", -1 > 8\'d0);',
          '    $display("sa >>> 1          = %0d", sa >>> 1);',
          '    $display("sa[7:0] >>> 1     = %0d", sa[7:0] >>> 1);',
          '  end',
          'endmodule'], caption="Width and sign rules in action (Icarus 12)")
    out(['s9 = a + b        = 300',
         's9 = {a + b}      = 44',
         's9 = (a+b)>>1     = 150',
         's8 = (a+b)>>1     = 22',
         '$bits(a+b)        = 8',
         'sa + u4 (unsigned)= 255',
         'sa + $signed(u4)  = -1',
         "-1 > 8'd0         = 1",
         'sa >>> 1          = -2',
         'sa[7:0] >>> 1     = 126'])
    box("key", "How to read the output",
        ["`{a + b}` is a concatenation, so its operand is self-determined at 8 bits "
         "and the carry is gone before the 9-bit target sees it. `(a + b) >> 1` "
         "keeps the carry only because the 9-bit LHS widens the whole context. "
         "`sa + u4` is unsigned because one operand is, so `-4` becomes 252. "
         "`sa[7:0]` is a part-select and therefore unsigned even though it selects "
         "all of a signed variable, so `>>>` zero-fills."])

    ah2("Signedness rules (IEEE 1800-2017 11.8)")
    bul(["The type of an expression depends **only on its operands**, never on the "
         "assignment target: `logic signed [15:0] y = a + b;` with unsigned `a`, "
         "`b` is an unsigned addition.",
         "Decimal numbers without a base (`-5`, `42`) are signed; based numbers are "
         "unsigned unless written with `s` (`8'sh80`).",
         "Bit-selects, part-selects (even of the full width), concatenations, "
         "comparison and reduction results are **unsigned**.",
         "If **any** operand of a context-determined operator is unsigned, the "
         "whole expression is unsigned; signed operands are then zero-extended.",
         "`integer`, `int`, `shortint`, `longint`, `byte` are signed; `reg`, "
         "`logic`, `bit`, `time` and nets are unsigned unless declared `signed`.",
         "The evaluation steps are: (1) determine the expression size by Table "
         "11-21, (2) determine its signedness, (3) propagate size and type down "
         "to every context-determined operand, (4) extend each such operand "
         "(sign-extend if the expression is signed, zero-extend otherwise), "
         "(5) evaluate.",
         "If any operand is `real`, the result is real and integer operands are "
         "converted first; `shortreal` mixed with `real` gives `real`.",
         "`$signed(x)` and `$unsigned(x)` (or `signed'(x)`, `unsigned'(x)`) change "
         "only the interpretation, not the bits."])
    box("warn", "PITFALL - the silent unsigned contagion",
        ["`if (count - 1 < 0)` is never true when `count` is a `logic [7:0]`: the "
         "expression is unsigned. `for (int i = N - 1; i >= 0; i--)` is fine "
         "because `int` is signed, but the same loop with an `unsigned int` or a "
         "`logic` index never terminates. Lint tools flag both (Chapter 27)."])

    ah2("Four-state truth tables")
    p("The bitwise operators work on each bit with the tables below; `z` on an "
      "input behaves as `x`. A controlling value wins regardless of the other "
      "input: `0` for AND, `1` for OR. XOR has no controlling value, so any unknown "
      "input gives `x`. The tables were printed by the simulator itself:")
    code(['module tt;',
          "  logic [3:0] v = 4'bzx10;              // v[0]=0 v[1]=1 v[2]=x v[3]=z",
          '  string n = "01xz";',
          '  initial begin',
          '    $display("AND | 0 1 x z    OR | 0 1 x z    XOR | 0 1 x z");',
          '    for (int i = 0; i < 4; i++)',
          '      $display(" %s  | %b %b %b %b     %s | %b %b %b %b     %s  | %b %b %b %b",',
          '        n.substr(i,i), v[i]&v[0], v[i]&v[1], v[i]&v[2], v[i]&v[3],',
          '        n.substr(i,i), v[i]|v[0], v[i]|v[1], v[i]|v[2], v[i]|v[3],',
          '        n.substr(i,i), v[i]^v[0], v[i]^v[1], v[i]^v[2], v[i]^v[3]);',
          '    $display("NOT: ~0=%b ~1=%b ~x=%b ~z=%b", ~v[0], ~v[1], ~v[2], ~v[3]);',
          '  end',
          'endmodule'], caption="Generating the 4-state tables (Icarus 12)")
    out(['AND | 0 1 x z    OR | 0 1 x z    XOR | 0 1 x z',
         ' 0  | 0 0 0 0     0 | 0 1 x x     0  | 0 1 x x',
         ' 1  | 0 1 x x     1 | 1 1 1 1     1  | 1 0 x x',
         ' x  | 0 x x x     x | x 1 x x     x  | x x x x',
         ' z  | 0 x x x     z | x 1 x x     z  | x x x x',
         'NOT: ~0=1 ~1=0 ~x=x ~z=x'], caption="Rows are the left operand, columns the right operand")
    tbl(["Operator", "0", "1", "x", "z"],
        [["Logical `!a`", "1", "0", "x", "x"],
         ["Reduction `&{a, 1'b1}`", "0", "1", "x", "x"],
         ["`a && 1'b0`", "0", "0", "0", "0"],
         ["`a || 1'b1`", "1", "1", "1", "1"],
         ["`if (a)` takes the", "else", "then", "else", "else"]],
        widths=[36, 16, 16, 16, 16], bold_first=True,
        caption="Other operators with an unknown operand. An `if` treats X and Z "
        "as false - the root of X-optimism (Chapter 11).")

    ah2("Equality and matching variants")
    tbl(["Form", "X/Z in left operand", "X/Z in right operand", "Result can be X?",
         "Synthesizable"],
        [["`a == b`, `a != b`", "Unknown -> X", "Unknown -> X", "Yes", "Yes"],
         ["`a === b`, `a !== b`", "Must match exactly", "Must match exactly", "No",
          "No"],
         ["`a ==? b`, `a !=? b`", "Unknown -> X", "Don't care", "Yes",
          "Yes (constant `b`)"],
         ["`a inside {b, ...}`", "Unknown -> X", "Don't care (like `==?`)", "Yes",
          "Yes"],
         ["`case` item match", "Exact (as `===`)", "Exact", "No", "Yes"],
         ["`casez` item match", "`z`/`?` don't care", "`z`/`?` don't care", "No",
          "Yes"],
         ["`casex` item match", "`x`/`z` don't care", "`x`/`z` don't care", "No",
          "Yes - but dangerous"],
         ["`case (...) inside`", "Exact", "`x`/`z`/`?` don't care", "No", "Yes"]],
        widths=[20, 20, 20, 16, 24], bold_first=True)
    code(['module eqv;',
          "  logic [3:0] a = 4'b10x1, b = 4'b10x1, c = 4'b1001;",
          '  initial begin',
          '    $display("a==b  %b   a===b %b   a!==b %b", a == b, a === b, a !== b);',
          '    $display("a==c  %b   a===c %b", a == c, a === c);',
          '    $display("c==?a %b   a==?c %b   c==?4\'b1??1 %b", c ==? a, a ==? c, c ==? 4\'b1??1);',
          '  end',
          'endmodule'], caption="Equality operators with an X bit (Icarus 12)")
    out(['a==b  x   a===b 1   a!==b 0',
         'a==c  x   a===c 0',
         "c==?a 1   a==?c x   c==?4'b1??1 1"])
    box("warn", "PITFALL - casex treats X in the selector as a match",
        ["With `casex`, an X on the case expression (an uninitialised register, "
         "for instance) matches the first item whose other bits agree, so "
         "simulation silently takes a branch that hardware might not. Prefer "
         "`case ... inside` or `casez` with `?` in the items, never `casex`."])

    ah2("Casting and conversion")
    tbl(["Cast", "Example", "Effect"],
        [["Size cast", "`16'(u)`, `4'(u)`", "Extend (by the signedness of `u`) or "
          "truncate to N bits"],
         ["Sign cast", "`signed'(u)`, `unsigned'(s)`", "Same bits, new "
          "interpretation; same as `$signed`/`$unsigned`"],
         ["Type cast", "`int'(r)`, `op_e'(3)`, `my_t'(v)`", "Converts to the type; "
          "real to integer **rounds** to nearest, ties away from zero; no range "
          "check for enums"],
         ["Const cast", "`const'(x)`", "Value treated as constant (used in "
          "assertions/let)"],
         ["Dynamic cast", "`$cast(dst, src)`", "Checked at run time: enum range, "
          "class down-cast; as a function returns 0 on failure and leaves `dst` "
          "unchanged; as a task a failure is a run-time error"],
         ["Bit-stream cast", "`pkt_t'(bit_array)`", "Between types of equal total "
          "bits (packed or unpacked, including queues/dynamic arrays of bits)"],
         ["Streaming", "`{>>{obj_fields}}`", "Pack/unpack in chosen order "
          "(Chapter 14)"],
         ["Real conversions", "`$rtoi(3.9)`, `$itor(3)`", "`$rtoi` truncates toward "
          "zero; contrast `int'()` which rounds"],
         ["Real bit patterns", "`$realtobits`, `$bitstoreal`, `$shortrealtobits`, "
          "`$bitstoshortreal`", "Move IEEE-754 bits through ports and DPI"]],
        widths=[18, 30, 52], bold_first=True)
    code(['module q_cast;',
          '  typedef enum logic [1:0] {A = 0, B = 1, C = 2} abc_e;',
          '  abc_e e;',
          "  logic [7:0] u = 8'hF0;",
          '  initial begin',
          '    $display("signed\'(u)=%0d  16\'(u)=%h  4\'(u)=%h  int\'(2.6)=%0d", signed\'(u), 16\'(u),',
          "             4'(u), int'(2.6));",
          '    if ($cast(e, 2)) $display("$cast(e,2) ok  -> %s", e.name());',
          '    if (!$cast(e, 3)) $display("$cast(e,3) failed, e still %s", e.name());',
          "    e = abc_e'(3);                               // static cast: no check",
          '    $display("abc_e\'(3) -> value %0d, name \'%s\'", e, e.name());',
          '    $finish;',
          '  end',
          'endmodule'], caption="Static and dynamic casts (Verilator 5.020)")
    out(["signed'(u)=-16  16'(u)=00f0  4'(u)=0  int'(2.6)=3",
         '$cast(e,2) ok  -> C',
         '$cast(e,3) failed, e still C',
         "abc_e'(3) -> value 3, name ''"])

    ah2("System tasks and functions by group")
    p("Entries marked (SV) are SystemVerilog additions. All of these "
      "are simulation constructs except the constant functions (`$clog2`, `$bits`, "
      "array queries) which synthesis evaluates at elaboration time.")
    tbl(["Group", "Tasks / functions", "Notes"],
        [["Display", "`$display $displayb $displayo $displayh`, `$write` (+ b/o/h), "
          "`$strobe` (+ b/o/h), `$monitor` (+ b/o/h), `$monitoron $monitoroff`",
          "`$display` prints now (Active region), `$strobe` at the end of the time "
          "step (Postponed), `$monitor` whenever an argument changes; only one "
          "`$monitor` active at a time"],
         ["String formatting", "`$sformat $swrite` (+ b/o/h), `$sformatf`",
          "(SV) `$sformatf` returns a string; `$psprintf` is a non-standard alias"],
         ["Severity", "`$fatal $error $warning $info`", "(SV) Print with "
          "location; `$fatal(n, ...)` ends simulation with `$finish(n)`"],
         ["File I/O", "`$fopen $fclose $fdisplay $fwrite $fstrobe $fmonitor "
          "$fgetc $ungetc $fgets $fscanf $sscanf $fread $ftell $fseek $rewind "
          "$fflush $feof $ferror`", "`$fopen(name)` returns a multichannel "
          "descriptor; `$fopen(name, \"r\")` a file descriptor (modes as C "
          "`fopen`)"],
         ["Memory load/dump", "`$readmemb $readmemh $writememb $writememh`",
          "Optional start/end addresses; `@addr` in the file"],
         ["Waveform dump", "`$dumpfile $dumpvars $dumpon $dumpoff $dumpall "
          "$dumplimit $dumpflush $dumpports`", "VCD / extended VCD (Chapter 10)"],
         ["Simulation control", "`$finish $stop $exit`", "`$finish(0|1|2)` "
          "sets the statistics printed; `$exit` ends a program block"],
         ["Time", "`$time $stime $realtime $printtimescale $timeformat`",
          "Scaled to the calling module's time unit; `$time` is rounded 64-bit, "
          "`$stime` 32-bit, `$realtime` real"],
         ["Conversion", "`$signed $unsigned $rtoi $itor $realtobits $bitstoreal "
          "$shortrealtobits $bitstoshortreal $cast`", "See casting table"],
         ["Integer math", "`$clog2`", "Ceiling of log2; `$clog2(1)` = 0; constant "
          "function"],
         ["Real math", "`$ln $log10 $exp $sqrt $pow $floor $ceil $sin $cos $tan "
          "$asin $acos $atan $atan2 $hypot $sinh $cosh $tanh $asinh $acosh $atanh`",
          "Real arguments and results, same as the C library"],
         ["Data query", "`$bits $typename $isunbounded`", "`$bits` works on any "
          "type or expression; (SV) `$typename` returns a string"],
         ["Array query", "`$dimensions $unpacked_dimensions $left $right $low "
          "$high $increment $size`", "Optional dimension number (1 = leftmost "
          "unpacked); `$increment` is 1 if `$left >= $right`, else -1"],
         ["Bit vector", "`$countbits $countones $onehot $onehot0 $isunknown`",
          "`$countbits(v, '1, 'x)` counts any listed values; used heavily in SVA"],
         ["Sampled values (SVA)", "`$sampled $rose $fell $stable $changed $past`, "
          "`$past_gclk $rose_gclk $future_gclk ...`", "Use Preponed-region values; "
          "`$past(e, n, gate, clk)`"],
         ["Assertion control", "`$asserton $assertoff $assertkill $assertcontrol "
          "$assertpasson $assertpassoff $assertfailon $assertfailoff "
          "$assertnonvacuouson $assertvacuousoff`", "Scope- and level-selectable; "
          "turn checks off during reset or error injection"],
         ["Coverage", "`$coverage_control $coverage_get_max $coverage_get "
          "$coverage_merge $coverage_save $get_coverage $set_coverage_db_name "
          "$load_coverage_db`", "Tool support varies; covergroup methods "
          "(`sample`, `get_coverage`, `get_inst_coverage`, `start`, `stop`) are "
          "more portable"],
         ["Random", "`$random $urandom $urandom_range`, `$dist_uniform "
          "$dist_normal $dist_exponential $dist_poisson $dist_chi_square $dist_t "
          "$dist_erlang`", "`$random` is signed 32-bit with a seed variable; "
          "(SV) `$urandom` is unsigned and thread-stable"],
         ["Plusargs", "`$test$plusargs $value$plusargs`", "Read `+NAME` and "
          "`+NAME=value` from the command line"],
         ["Misc.", "`$system $stacktrace`, PLA tasks (`$async$and$array` ...), "
          "stochastic queues (`$q_initialize` ...)", "`$system` runs a shell "
          "command (standard in IEEE 1800); `$stacktrace` was added in "
          "1800-2023; the PLA and queue tasks are legacy"]],
        widths=[16, 44, 40], bold_first=True)
    code(['module st;',
          '  logic [7:0]  mem [1:16];',
          '  logic [3:0][7:0] pk;',
          "  logic [7:0] v = 8'b0010_1100;",
          "  logic [3:0] u = 4'b01x0;",
          '  real r;',
          '  initial begin',
          '    $display("$size=%0d $left=%0d $right=%0d $low=%0d $high=%0d $dimensions=%0d",',
          '             $size(mem), $left(mem), $right(mem), $low(mem), $high(mem), $dimensions(mem));',
          '    $display("$bits(pk)=%0d $size(pk,1)=%0d $size(pk,2)=%0d $increment(mem)=%0d",',
          '             $bits(pk), $size(pk,1), $size(pk,2), $increment(mem));',
          '    $display("$countones=%0d $onehot=%b $onehot0=%b $isunknown(u)=%b $clog2(17)=%0d",',
          "             $countones(v), $onehot(v), $onehot0(8'h00), $isunknown(u), $clog2(17));",
          '    r = $sqrt(2.0);',
          '    $display("$sqrt(2)=%f $ln(10)=%f $pow(2,10)=%0.1f $floor(-1.5)=%0.1f", r, $ln(10.0),',
          '             $pow(2.0, 10.0), $floor(-1.5));',
          '    $display("$rtoi(3.9)=%0d $itor(3)=%0.1f $realtobits(1.0)=%h", $rtoi(3.9), $itor(3),',
          '             $realtobits(1.0));',
          '    $display("%%h=%h %%d=%d %%0d=%0d %%b=%b %%o=%o %%e=%e %%s=%s %%c=%c", v, v, v, v, v,',
          '             1234.5, "ok", 8\'h41);',
          '  end',
          'endmodule'], caption="Array-query, bit-vector, math, conversion and format "
         "functions (Icarus 12)")
    out(['$size=16 $left=1 $right=16 $low=1 $high=16 $dimensions=2',
         '$bits(pk)=32 $size(pk,1)=4 $size(pk,2)=8 $increment(mem)=-1',
         '$countones=3 $onehot=0 $onehot0=1 $isunknown(u)=1 $clog2(17)=5',
         '$sqrt(2)=1.414214 $ln(10)=2.302585 $pow(2,10)=1024.0 $floor(-1.5)=-2.0',
         '$rtoi(3.9)=3 $itor(3)=3.0 $realtobits(1.0)=3ff0000000000000',
         '%h=2c %d= 44 %0d=44 %b=00101100 %o=054 %e=1.234500e+03 %s=ok %c=A'])
    code(['module q_fio;',
          '  integer fd, n, code, addr, data;',
          '  string  line;',
          '  initial begin',
          '    fd = $fopen("vec.txt", "w");',
          '    for (int i = 0; i < 3; i++) $fdisplay(fd, "%h %h", 16 * i, i * i + 1);',
          '    $fclose(fd);',
          '    fd = $fopen("vec.txt", "r");',
          '    while (!$feof(fd)) begin',
          '      code = $fgets(line, fd);                   // returns chars read, 0 at EOF',
          '      if (code && $sscanf(line, "%h %h", addr, data) == 2)',
          '        $display("addr=%0d data=%0d", addr, data);',
          '    end',
          '    $fclose(fd);',
          '    if (!$value$plusargs("SEED=%d", n)) n = 1;   // run with +SEED=42',
          '    $display("seed=%0d verbose=%0d", n, $test$plusargs("VERBOSE"));',
          '    $finish;',
          '  end',
          'endmodule'], caption="File I/O and plusargs (Verilator 5.020, run "
         "with `+SEED=42 +VERBOSE`)")
    out(['addr=0 data=1',
         'addr=16 data=2',
         'addr=32 data=5',
         'seed=42 verbose=1'])

    ah2("Format specifiers and escapes")
    tbl(["Spec", "Meaning", "Spec", "Meaning"],
        [["`%h %H %x %X`", "Hexadecimal", "`%c`", "ASCII character"],
         ["`%d %D`", "Decimal (padded to max width)", "`%s`", "String"],
         ["`%o %O`", "Octal", "`%t`", "Time, per `$timeformat`"],
         ["`%b %B`", "Binary", "`%m`", "Hierarchical name of the scope (no argument)"],
         ["`%e %f %g`", "Real: exponent, fixed, shorter", "`%v`", "Net signal strength"],
         ["`%0d`, `%0h`", "Minimum width (no padding)", "`%l`", "Library binding "
          "(config)"],
         ["`%5d`, `%-8s`", "Field width, left-justify", "`%p`", "(SV) Assignment-pattern "
          "print of any aggregate"],
         ["`%u` `%z`", "Unformatted 2-state / 4-state binary (files)", "`%%`",
          "Percent sign"]],
        widths=[16, 34, 12, 38])
    p("Escapes in strings: `\\n` newline, `\\t` tab, `\\\\` backslash, `\\\"` quote, "
      "`\\ddd` octal character; SystemVerilog adds `\\v`, `\\f`, `\\a` and `\\xHH`. "
      "`%h` and `%d` print `x`/`z` when all bits of a digit are unknown and `X`/`Z` "
      "when only some are.")

    ah2("Array methods (IEEE 1800-2017 7.12)")
    tbl(["Kind", "Methods", "Returns / notes"],
        [["Locator", "`find find_index find_first find_first_index find_last "
          "find_last_index` (need `with`), `min max unique unique_index`",
          "Always a **queue** (possibly empty); `item` and `item.index` usable in "
          "the `with` clause"],
         ["Ordering", "`reverse sort rsort shuffle`", "In place; `sort`/`rsort` "
          "accept `with (key)`; not for associative arrays"],
         ["Reduction", "`sum product and or xor`", "Result has the **element "
          "type** - `bit` arrays sum to 1 bit unless you write `sum() with "
          "(int'(item))`"],
         ["Queue", "`size insert delete push_front push_back pop_front pop_back`",
          "`delete()` with no index empties it; `q[$]` is the last element"],
         ["Dynamic array", "`new[n]`, `new[n](old)`, `size delete`",
          "`new[n](old)` resizes and copies"],
         ["Associative array", "`num size delete exists first last next prev`",
          "Traversal functions take a `ref` key and return 0/1 (or -1 if the key "
          "had to be truncated)"]],
        widths=[16, 44, 40], bold_first=True)

    ah2("String methods (IEEE 1800-2017 6.16)")
    tbl(["Method", "Effect", "Method", "Effect"],
        [["`len()`", "Number of characters", "`substr(i, j)`", "Characters i..j "
          "(inclusive)"],
         ["`putc(i, c)`", "Replace character i", "`getc(i)`", "Character i as byte"],
         ["`toupper()` `tolower()`", "Case-converted copy", "`compare(s)`",
          "Like C `strcmp` (<0, 0, >0)"],
         ["`icompare(s)`", "Case-insensitive compare", "`atoi() atohex() atooct() "
          "atobin()`", "Parse leading digits to integer"],
         ["`atoreal()`", "Parse to real", "`itoa(i) hextoa(i) octtoa(i) bintoa(i)`",
          "Format integer into the string"],
         ["`realtoa(r)`", "Format a real", "Operators", "`== != < <= > >=`, `{s1, s2}`, "
          "`{n{s}}`, `s[i]`"]],
        widths=[20, 24, 26, 30])
    code(['module am;',
          "  int q[$] = '{5, 3, 9, 3, 7};",
          '  int r[$];',
          '  int aa[string];',
          '  string s = "Hello,SoC";',
          '  function automatic string L(int a[$]);',
          '    string t = "";',
          '    foreach (a[i]) t = {t, $sformatf(" %0d", a[i])};',
          '    return t;',
          '  endfunction',
          '  initial begin',
          '    r = q.find(x) with (x > 4);          $display("find >4     : %s", L(r));',
          '    r = q.find_first_index(x) with (x == 3); $display("first idx 3 : %s", L(r));',
          '    r = q.unique();                      $display("unique      : %s", L(r));',
          '    r = q.min();                         $display("min         : %s", L(r));',
          '    $display("sum=%0d product=%0d", q.sum(), q.product());',
          '    $display("sum with (x>4)=%0d", q.sum(x) with (int\'(x > 4)));',
          '    q.sort();                            $display("sort        : %s", L(q));',
          '    q.rsort();                           $display("rsort       : %s", L(q));',
          '    q.reverse();                         $display("reverse     : %s", L(q));',
          '    q.push_front(1); q.push_back(10);    $display("push        : %s size=%0d", L(q), q.size());',
          '    $display("pop_front=%0d pop_back=%0d", q.pop_front(), q.pop_back());',
          '    q.insert(1, 42); q.delete(0);        $display("insert/del  : %s", L(q));',
          '    aa["b"] = 2; aa["a"] = 1; aa["c"] = 3;',
          '    $display("num=%0d exists(\\"a\\")=%0d", aa.num(), aa.exists("a"));',
          '    foreach (aa[k]) $write("%s=%0d ", k, aa[k]);',
          '    $display("");',
          '    $display("len=%0d upper=%s lower=%s substr(6,8)=%s", s.len(), s.toupper(), s.tolower(),',
          '             s.substr(6, 8));',
          '    $display("getc(0)=%s compare=%0d icompare=%0d", s.getc(0), s.compare("Hello"),',
          '             s.icompare("HELLO,SOC"));',
          '    s = "123"; $display("atoi=%0d atohex=%0d", s.atoi(), s.atohex());',
          '    s.itoa(-77); $display("itoa=%s", s); s.hextoa(255); $display("hextoa=%s", s);',
          '    $finish;',
          '  end',
          'endmodule'], caption="Queue, associative-array and string methods "
         "(Verilator 5.020)")
    out(['find >4     :  5 9 7',
         'first idx 3 :  1',
         'unique      :  5 3 9 7',
         'min         :  3',
         'sum=27 product=2835',
         'sum with (x>4)=3',
         'sort        :  3 3 5 7 9',
         'rsort       :  9 7 5 3 3',
         'reverse     :  3 3 5 7 9',
         'push        :  1 3 3 5 7 9 10 size=7',
         'pop_front=1 pop_back=10',
         'insert/del  :  42 3 5 7 9',
         'num=3 exists("a")=1',
         'a=1 b=2 c=3',
         'len=9 upper=HELLO,SOC lower=hello,soc substr(6,8)=SoC',
         'getc(0)=H compare=44 icompare=0',
         'atoi=123 atohex=291',
         'itoa=-77',
         'hextoa=ff'])
    p("`compare` is only specified by sign; Verilator returns the C `strcmp` "
      "difference (44 here), another simulator may return 1. Note that "
      "`q.sum(x) with (int'(x > 4))` counts elements: the `with` expression is "
      "summed instead of the elements.")


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
    _Q["n"] = 0
    appendix("100 Verilog/SystemVerilog Interview Questions with Answers")
    p("These are the language questions asked in RTL design, design-verification "
      "and DFT interviews, grouped from screening level to on-site puzzles. Answer "
      "each one out loud before reading the answer. Answers are deliberately short; "
      "the chapter in brackets has the full story. Code with an output card was run "
      "with Icarus Verilog 12 or Verilator 5.020 as noted; constraint and assertion "
      "code was elaborated with slang and needs a commercial simulator to execute.")

    # ------------------------------------------------------------ basics (10)
    ah2("Verilog basics")
    qa("What is the difference between a `wire` and a `reg`?",
       "A `wire` is a net: it has no storage and continuously takes the resolved "
       "value of its drivers (continuous assignments, ports, primitives). A `reg` "
       "is a variable: it holds the last value assigned by procedural code. `reg` "
       "does **not** mean flip-flop - a `reg` written in a combinational `always` "
       "block is plain logic. SystemVerilog's `logic` is a variable type that can "
       "also be driven by one continuous assignment, which removes most of the "
       "confusion (Chapter 3).")
    qa("What is the difference between `logic` and `wire` in SystemVerilog?",
       "`logic` is a 4-state **data type**; `wire` is a **net kind**. A plain "
       "`logic x;` declares a variable, which allows either procedural writes or a "
       "single continuous driver. A net (`wire logic x;` or `wire x;`) allows "
       "multiple drivers resolved by strength - needed for tri-state buses and "
       "`inout` ports. Use `logic` everywhere except multi-driver nets.")
    qa("What are the four values of Verilog logic and what does each mean?",
       "`0` and `1` are logic levels; `x` is unknown (uninitialised, conflicting "
       "drivers, or undefined result); `z` is high impedance (undriven net). "
       "Variables start at `x`; nets with no driver are `z`. 2-state types (`bit`, "
       "`int`) hold only 0/1 and start at 0.")
    qa("What is the difference between `initial` and `always`?",
       "Both start at time 0 as independent processes. `initial` runs once; "
       "`always` loops forever, so it must contain a timing control or it hangs "
       "the simulator. Synthesis ignores `initial` for ASICs (FPGA flows may use it "
       "for power-up values).")
    qa("How does the `timescale` directive work, and what is the precision for?",
       ["`timescale 1ns/10ps` (with its leading grave accent) sets the time **unit** for delays in the "
        "following modules (`#5` = 5 ns) and the **precision** to which delays "
        "are rounded. The simulator runs at the finest precision of all modules, "
        "so one `1fs` precision slows everything. SystemVerilog's `timeunit` and "
        "`timeprecision` inside a module avoid the order dependence of the "
        "directive (Chapter 8)."])
    qa("What does the directive `default_nettype none` do and why use it?",
       "It turns off implicit net declaration, so a misspelled identifier in a port "
       "connection or continuous assignment becomes a compile error instead of a "
       "silently created 1-bit wire. Restore `wire` at the end of the file so "
       "third-party code that relies on implicit nets still compiles.")
    qa("What are `parameter`, `localparam`, `defparam` and `specparam`?",
       "`parameter`: overridable per instance with `#(...)`. `localparam`: "
       "derived constant, not overridable. `defparam`: overrides a parameter by "
       "hierarchical path from anywhere - deprecated, avoid. `specparam`: timing "
       "value inside a `specify` block, can be back-annotated from SDF (Chapters 7 "
       "and 9).")
    qa("What is the difference between a task and a function?",
       "A function executes in zero time, cannot contain `#`, `@` or `wait`, and "
       "returns a value (or `void`). A task may consume time, returns results "
       "through `output`/`inout`/`ref` arguments and can call tasks. Both are "
       "static by default in modules; declare them `automatic` for recursion or "
       "concurrent calls (Chapter 6).")
    qa("What is the difference between `==` and `===`?",
       "`==` returns `x` if any compared bit is `x` or `z` and the result is "
       "otherwise ambiguous; `===` compares all four values literally and always "
       "returns 0 or 1. `===` is for testbenches (e.g. `if (bus === 'z)`); "
       "synthesis either rejects it or treats it as `==`.")
    qa("What is a hierarchical reference, and where is it acceptable?",
       "A dotted path such as `tb.dut.u_fifo.count` that reads or writes a signal "
       "anywhere in the design. It is fine in testbenches, `bind` files and "
       "assertions, but not in synthesizable RTL (most synthesis tools reject "
       "cross-module references), and it couples code to the hierarchy.")

    # ------------------------------------------------------ data types (10)
    ah2("Data types and sizing")
    qa("What is the difference between packed and unpacked arrays?",
       "Packed dimensions (before the name, `logic [3:0][7:0] w`) form one "
       "contiguous vector that can be sliced, used in arithmetic and assigned as a "
       "whole. Unpacked dimensions (after the name, `logic [7:0] m [256]`) are an "
       "array of separate elements - memories, register files. Only packed types "
       "can be packed struct members (Chapter 13).")
    qa("Compare fixed, dynamic, associative arrays and queues.",
       "Fixed: size set at elaboration, synthesizable. Dynamic `[]`: size set at run "
       "time with `new[n]`, contiguous. Associative `[key_t]`: sparse, indexed by any "
       "type, only written entries exist - ideal for a memory model. Queue `[$]`: "
       "ordered, grows at both ends with `push_*`/`pop_*` - ideal for scoreboards. "
       "Only fixed arrays are synthesizable.")
    qa("What is `$bits(8'd1 + 8'd1 + 32'd0)`?",
       "32. The expression width is the maximum operand width (Table 11-21), so the "
       "three operands are all evaluated at 32 bits.")
    qa("`a` and `b` are `logic [7:0]` with values 200 and 100. What is "
       "`sum` for `logic [8:0] sum = a + b;` and for `sum = {a + b};`?",
       "300 and 44. In the first the 9-bit LHS makes the addition 9 bits wide and "
       "keeps the carry. In the second the concatenation makes `a + b` "
       "self-determined (8 bits), so the carry is lost before assignment "
       "(Appendix B shows the simulator output).")
    qa("Why can `-1 > 8'd0` be true?",
       "Mixing a signed operand (`-1`, a 32-bit signed decimal) with an unsigned one "
       "makes the whole comparison unsigned. `-1` becomes 32'hFFFF_FFFF, which is "
       "larger than 0. Keep both operands signed (`8'sd0`) or cast.")
    qa("Is a part-select of a signed variable signed?",
       "No. Bit-selects and part-selects - even `s[7:0]` covering the whole of a "
       "signed 8-bit `s` - are unsigned, as are concatenations. Wrap them in "
       "`$signed()` when the sign matters (for example before `>>>`).")
    qa("What is the difference between `int` and `integer`?",
       "`integer` is Verilog's 4-state signed 32-bit variable; `int` is "
       "SystemVerilog's 2-state signed 32-bit type. `int` is faster in simulation "
       "and starts at 0, but hides X: an X assigned to an `int` becomes 0.")
    qa("Why are 2-state types risky in RTL?",
       "X is how simulation tells you something is uninitialised or multiply "
       "driven. A `bit` register without reset simply reads 0, so reset bugs and "
       "X-propagation problems disappear in RTL simulation and reappear in "
       "gate-level simulation or silicon. Use 4-state `logic` for design; 2-state "
       "types are for testbench data.")
    qa("What are `'0`, `'1`, `'x` and `'z`?",
       "SystemVerilog fill literals: every bit of the context width is set to that "
       "value, whatever the width. `'1` is all ones - unlike `-1` or `1`, it never "
       "depends on sign extension or 32-bit truncation, so it is the safe way to "
       "write a parameterized all-ones constant.")
    qa("What is a packed union, and what is a tagged union?",
       "A packed union overlays members of **equal** width on the same bits, giving "
       "several views of one vector (e.g. raw word versus decoded fields); it is "
       "synthesizable. A tagged union stores which member was last written and "
       "type-checks reads (`matches` in `case`); it is a verification construct "
       "with patchy tool support.")

    # -------------------------------------------------- scheduling (9)
    ah2("Blocking, non-blocking and scheduling")
    qa("Explain blocking versus non-blocking assignment. What does this print?",
       ["`=` updates the variable immediately; `<=` evaluates the RHS now and "
        "schedules the update for the NBA region, after all Active events of the "
        "time step. So the blocking pair copies (both become 2) while the "
        "non-blocking pair swaps. `$display` runs in the Active region and still "
        "sees the old `c`, `d`; `$strobe` runs at the end of the time step and "
        "sees the swap."], ['module q_nba;',
                            "  logic [3:0] a = 4'd1, b = 4'd2, c = 4'd1, d = 4'd2;",
                            '  initial begin',
                            '    a = b;  b = a;                       // blocking: both end up 2',
                            '    c <= d; d <= c;                      // non-blocking: true swap',
                            '    $display("t=0 display: a=%0d b=%0d c=%0d d=%0d", a, b, c, d);',
                            '    $strobe ("t=0 strobe : a=%0d b=%0d c=%0d d=%0d", a, b, c, d);',
                            '  end',
                            'endmodule'])
    out(['t=0 display: a=2 b=2 c=1 d=2',
         't=0 strobe : a=2 b=2 c=2 d=1'], caption="Icarus 12")
    qa("List the SystemVerilog scheduling regions in order.",
       "For each time slot: **Preponed** (assertion sampling), **Active** "
       "(blocking assignments, continuous assignments, `$display`), **Inactive** "
       "(`#0` events), **NBA** (non-blocking updates), **Observed** (concurrent "
       "assertion evaluation), **Reactive** (program blocks, assertion action "
       "blocks), **Re-Inactive**, **Re-NBA** (clocking-block drives, NBAs from "
       "programs), **Postponed** (`$strobe`, `$monitor`, read-only). Active through "
       "NBA iterate until empty, then the reactive set, then back if new active "
       "events appear (Chapter 5).")
    qa("What are the coding rules that avoid simulation races in RTL?",
       ["(1) Sequential logic: non-blocking. (2) Combinational `always`: blocking. "
        "(3) Never mix `=` and `<=` in one block. (4) Never assign a variable from "
        "more than one `always` block. (5) Use `$strobe` or check after the edge "
        "to display NBA results. (6) No `#0`. These are Cummings' guidelines "
        "(SNUG 2000) and `always_ff`/`always_comb` enforce several of them."])
    qa("What is a race condition? Give an example.",
       "The result depends on which of two processes scheduled in the same region "
       "runs first, which the LRM leaves undefined. Example: `always @(posedge "
       "clk) a = b;` and `always @(posedge clk) b = a;` - the pair may swap, or "
       "both may get the same value, depending on the simulator. Using `<=` in both "
       "removes the race.")
    qa("Why is `#0` considered harmful?",
       "It moves a process to the Inactive region, which fixes one ordering and "
       "creates another; code that needs it usually has a race. In testbenches, "
       "clocking blocks and program blocks provide a defined ordering instead.")
    qa("What is the difference between `$display`, `$write`, `$strobe` and `$monitor`?",
       "`$display` prints immediately with a newline, `$write` without. `$strobe` "
       "prints at the end of the time step (Postponed region), so it shows NBA "
       "results. `$monitor` prints whenever any of its arguments changes; only one "
       "is active at a time.")
    qa("How does `always @(a or b)` differ from `always @*` and `always_comb`?",
       "A hand-written list misses signals added later: simulation then behaves as "
       "a latch while synthesis builds combinational logic - a sim/synth mismatch. "
       "`@*` infers the list from the block. `always_comb` also includes signals "
       "read inside called functions, runs once at time 0 (so outputs are valid "
       "even if inputs never change), forbids timing controls and forbids other "
       "processes writing its outputs.")
    qa("What does intra-assignment delay `a = #5 b;` do compared with `#5 a = b;`?",
       "`a = #5 b;` samples `b` now and assigns it 5 units later (the process "
       "blocks). `#5 a = b;` waits 5 units, then samples and assigns. "
       "`a <= #5 b;` samples now and schedules the update 5 units later without "
       "blocking - it models transport delay. None are synthesizable; synthesis "
       "ignores delays.")
    qa("When should you use static versus automatic variables? What does this print?",
       ["Variables in module-level functions and tasks are static by default: one "
        "copy, initialised once at time 0 and shared by every call and every "
        "concurrent caller. `automatic` gives each call its own storage, required "
        "for recursion, re-entrant tasks and fork loops. Classes' methods are "
        "automatic by default. The LRM requires the explicit `static` keyword when "
        "a variable in a static function has an initialiser."],
       ['module q_static;',
        '  function int cnt_s();                  // static by default in a module',
        '    static int n = 0;                    // initialised ONCE, at time 0',
        '    n++;',
        '    return n;',
        '  endfunction',
        '  function automatic int cnt_a();        // fresh storage per call',
        '    int n = 0;',
        '    n++;',
        '    return n;',
        '  endfunction',
        '  initial begin',
        '    repeat (3) $write("%0d ", cnt_s());',
        '    repeat (3) $write("%0d ", cnt_a());',
        '    $display("");',
        '  end',
        'endmodule'])
    out(['1 2 3 1 1 1'], caption="Icarus 12")

    # --------------------------------------------------- synthesis (9)
    ah2("Synthesis")
    qa("How is a latch inferred unintentionally, and how do you prevent it?",
       "A combinational block that does not assign an output on every path (an "
       "`if` without `else`, a `case` without `default`) must remember the old "
       "value, so synthesis builds a latch. Prevent it with default assignments at "
       "the top of the block, complete `case`/`if`, and `always_comb` so tools "
       "warn.")
    qa("Which constructs are not synthesizable?",
       "Delays (`#`, ignored), `initial` (ASIC), `force`/`release`, `fork`/`join`, "
       "`wait` on arbitrary expressions, `===`/`!==`, real arithmetic, "
       "dynamic/associative arrays, queues, classes, strings, file I/O and most "
       "system tasks. Loops are synthesizable only with a static bound (they are "
       "unrolled).")
    qa("What are `full_case` and `parallel_case`, and what replaced them?",
       "Synthesis pragmas: `full_case` says unlisted values never occur (outputs "
       "may be don't-care), `parallel_case` says items never overlap (no priority "
       "logic). Because simulation ignores comments, they cause sim/synth "
       "mismatches (Cummings: 'the evil twins'). SystemVerilog's `unique` and "
       "`priority` state the same intent **and** make simulation check it.")
    qa("Explain `unique`, `unique0` and `priority`.",
       "`unique case`/`unique if`: exactly one item must match - a run-time "
       "violation warning if none or more than one does; synthesis may build "
       "parallel logic and treat unmatched values as don't-care. `unique0`: at "
       "most one may match (no warning for none). `priority`: first match wins, "
       "but at least one must match. All checks happen in simulation after the "
       "inputs settle in the time step.")
    qa("How does synthesis treat a `for` loop?",
       "It unrolls it at elaboration: each iteration becomes a copy of the "
       "hardware. The bound must be a constant. A loop is therefore a way to "
       "describe replicated or reduction logic, never a sequence in time.")
    qa("What is a simulation/synthesis mismatch? Name four causes.",
       "RTL simulation behaves differently from the synthesized netlist. Causes: "
       "incomplete sensitivity lists; `full_case`/`parallel_case` pragmas; "
       "X-optimism in `if`/`case` (X takes the else branch in RTL but propagates "
       "in gates); `initial` values; delays in RTL; blocking assignments in "
       "sequential blocks read before written; `casex` with X inputs. Gate-level "
       "simulation and equivalence checking catch them (Chapter 11).")
    qa("Synchronous versus asynchronous reset - how is each coded?",
       ["Synchronous: `always_ff @(posedge clk) if (!rst_n) q <= '0; else ...` - "
        "reset is just another data input. Asynchronous: `always_ff @(posedge clk "
        "or negedge rst_n) if (!rst_n) ...` - the reset must be the first `if` and "
        "the only other event. Asynchronous assertion needs synchronised "
        "deassertion (a reset synchronizer) to avoid recovery/removal violations."])
    qa("What is X-optimism and X-pessimism?",
       "X-optimism: RTL treats X as a known value, e.g. `if (x)` takes the `else` "
       "branch, hiding an X that hardware would propagate. X-pessimism: gate-level "
       "simulation produces X where real hardware would be deterministic, e.g. a "
       "mux with equal inputs and an X select. Both waste debug time; reset every "
       "control flop and use X-propagation modes or assertions (`$isunknown`).")
    qa("Why must a combinational block not read a variable before writing it?",
       "Reading first implies the old value is needed - a latch or a "
       "combinational loop in hardware, and simulation that depends on execution "
       "order. Assign defaults first, then compute; `always_comb` plus lint "
       "catch the pattern.")

    # ------------------------------------------ SV design features (9)
    ah2("SystemVerilog design features")
    qa("What are interfaces and modports for?",
       "An interface bundles the signals (and optionally tasks, functions, "
       "assertions and clocking blocks) of a protocol so a port list shrinks to "
       "one line. A modport gives each side its direction view (`mst`, `slv`), "
       "which is checked at compile time. Interfaces synthesize; the signals are "
       "flattened into ports (Chapter 16).")
    qa("What is a virtual interface and why is it needed?",
       "A class variable that holds a handle to an interface **instance**. Classes "
       "are created at run time and cannot have ports, so a virtual interface is "
       "the bridge from dynamic testbench objects to static design signals. UVM "
       "passes it through `uvm_config_db`.")
    qa("Package versus the `include` directive - which and why?",
       "A package is a named scope compiled once; importing it gives every user the "
       "**same** types, so type checking across modules works. `include` pastes "
       "text, so each includer gets its own copy of a typedef - two identical "
       "declarations are different types in different scopes. Use packages for "
       "shared types, `include` only for macros and class files inside a "
       "package.")
    qa("What is the compilation-unit scope `$unit`?",
       "Declarations outside any module, interface or package go into `$unit`. "
       "Whether each file is its own unit or all files share one is "
       "tool-dependent, so code that relies on it breaks between tools. Put "
       "declarations in packages.")
    qa("Wildcard import versus explicit import?",
       "`import p::*;` makes names visible only when used and not otherwise "
       "declared locally; a local declaration silently wins. `import p::name;` "
       "imports that name immediately and conflicts with a local declaration. "
       "Explicit imports and `p::name` references are clearer in large SoCs.")
    qa("How do you reverse the bits of a vector in one line?",
       "With the streaming operator: `rev = {<<{x}};`. `{<<8{w}}` reverses bytes "
       "(endianness swap). Streaming is synthesizable when widths are static. The "
       "coding-puzzles section shows it running.")
    qa("What is `let` and how does it differ from a macro?",
       "`let name(args) = expr;` (1800-2009) declares a scoped, typed expression "
       "template that follows normal name resolution; a macro is textual "
       "substitution with no scope. `let` is ideal for reusable expressions in "
       "assertions and RTL.")
    qa("How are type parameters used?",
       "`module fifo #(parameter type T = logic [7:0])` lets one module store any "
       "type, including structs. Combined with `$bits(T)`, it replaces width "
       "parameters for bus payloads (Chapter 17).")
    qa("What does the `inside` operator do in RTL?",
       "`if (op inside {ADD, SUB, [8:11]})` tests set membership, with ranges and "
       "array elements; X/Z in the set values are don't-cares. `case (x) inside` "
       "gives range items in a `case`. Both are synthesizable.")

    # -------------------------------------------------------- OOP (9)
    ah2("Object-oriented programming")
    qa("What is the difference between a class handle and an object?",
       "The handle is a typed reference variable (initially `null`); `new()` "
       "allocates an object and returns a handle to it. Assigning a handle copies "
       "the reference, not the object. Objects are freed automatically when no "
       "handle refers to them.")
    qa("Shallow copy versus deep copy - what does this print, and why is "
       "`kind()` 'animal'?",
       ["`new a` copies the properties of `a`; a nested object handle is copied as "
        "a handle, so both copies share the inner object - that is a shallow copy. "
        "A deep copy must also construct new nested objects. (`new this` inside a "
        "method is the usual idiom; Verilator 5.020 rejects it, so the method "
        "below copies fields explicitly.) `speak()` is virtual, so the base handle "
        "dispatches to `dog::speak`; `kind()` is not virtual, so the handle type "
        "decides."], ['module q_oop;',
                      '  class inner; int v = 1; endclass',
                      '  class outer;',
                      '    int    x = 5;',
                      '    inner  h = new();',
                      '    function outer deep_copy();',
                      '      outer c = new();',
                      '      c.x = x;',
                      '      c.h = new h;                       // copy the nested object too',
                      '      return c;',
                      '    endfunction',
                      '  endclass',
                      '',
                      '  class animal;',
                      '    virtual function string speak(); return "..."; endfunction',
                      '    function string kind(); return "animal"; endfunction      // NOT virtual',
                      '  endclass',
                      '  class dog extends animal;',
                      '    virtual function string speak(); return "woof"; endfunction',
                      '    function string kind(); return "dog"; endfunction',
                      '  endclass',
                      '',
                      '  initial begin',
                      '    outer a = new(), s, d;',
                      '    animal an;',
                      '    dog    dg = new();',
                      '    s = new a;                           // shallow: s.h and a.h are the same object',
                      '    d = a.deep_copy();',
                      '    a.x = 9; a.h.v = 7;',
                      '    $display("shallow: x=%0d h.v=%0d   deep: x=%0d h.v=%0d", s.x, s.h.v, d.x, d.h.v);',
                      '    an = dg;                             // base handle, derived object',
                      '    $display("speak=%s kind=%s", an.speak(), an.kind());',
                      '    $finish;',
                      '  end',
                      'endmodule'])
    out(['shallow: x=5 h.v=7   deep: x=5 h.v=1',
         'speak=woof kind=animal'], caption="Verilator 5.020")
    qa("What does `virtual` mean for a method, and can a constructor be virtual?",
       "A virtual method is dispatched on the **object** type at run time; once "
       "virtual, it stays virtual in all derived classes and overrides must keep "
       "the same signature. Constructors cannot be virtual; factories (as in UVM) "
       "provide the equivalent of a virtual constructor.")
    qa("What is an abstract class and a pure virtual method?",
       "`virtual class` cannot be instantiated. A `pure virtual` method has no body "
       "and must be implemented by every non-abstract derived class. Used for "
       "base transactions and components that define an API.")
    qa("What do `local` and `protected` mean?",
       "`local` members are visible only inside the class itself; `protected` "
       "members also in derived classes. Everything else is public. `const` "
       "properties are read-only after construction.")
    qa("What is `$cast` used for with classes?",
       "Down-casting: assigning a base-class handle to a derived-class handle. "
       "`if (!$cast(pkt, base_h))` checks at run time that the object really is a "
       "`pkt` (or derived) and returns 0 otherwise. Up-casting needs no cast.")
    qa("How do static members behave, including in parameterized classes?",
       "A static property has one copy per class, shared by all objects; a static "
       "method can only touch static members. Each **specialization** of a "
       "parameterized class is a separate class with its own statics - UVM's "
       "factory registration relies on this.")
    qa("What is an interface class?",
       "(1800-2012) A class containing only pure virtual methods, types and "
       "parameters. A class `implements` any number of them, giving multiple "
       "inheritance of API without inheritance of implementation, as in Java.")
    qa("What are `this` and `super`, and when is `typedef class` needed?",
       "`this` refers to the current object (to disambiguate a property from an "
       "argument of the same name); `super` to the parent class's members, e.g. "
       "`super.new()` must be the first statement of a derived constructor if the "
       "parent's constructor takes arguments. `typedef class c;` forward-declares "
       "a class used before its definition.")

    # ------------------------------------------------ randomization (8)
    ah2("Constrained randomization")
    qa("`rand` versus `randc`?",
       "`rand` values are independent draws, so repeats are possible. `randc` "
       "cycles through every value of its range in random order before repeating; "
       "it is meant for small ranges (tools limit its width) and is solved before "
       "`rand` variables.")
    qa("What is the difference between `:=` and `:/` in `dist`?",
       "`[1:3] := 30` gives weight 30 to **each** value (total 90); `[1:3] :/ 30` "
       "shares 30 across the range (10 each). `dist` is a soft preference shape, "
       "not a hard guarantee in any single draw.")
    qa("What does `solve a before b` do?",
       "It changes the probability distribution, not the solution space: `a` is "
       "picked uniformly among its legal values first. Without it, the solver picks "
       "uniformly over all legal (a, b) pairs, so for `is_long -> len > 64` the "
       "rare `is_long == 0` combinations dominate. It cannot make an unsolvable "
       "set solvable and does not apply to `randc`.")
    qa("How do you write constraints for a packet class? Show common idioms.",
       ["The class below uses a weighted `dist`, implications, `solve ... before`, "
        "an array size constraint, `foreach`, a `soft` default that an inline "
        "`with` constraint overrides, and the run-time switches `constraint_mode` "
        "and `rand_mode`. (Elaborated with slang; Verilator 5.020 ignores "
        "constraints, so run it on a commercial simulator.)"],
       ['class packet;',
        '  rand bit [3:0]  kind;',
        '  rand bit [7:0]  len;',
        '  rand bit [7:0]  payload[];',
        '  rand bit        is_long;',
        '  constraint c_kind { kind dist {0 := 60, [1:3] :/ 30, [4:15] :/ 10}; }',
        '  constraint c_len  { is_long -> len > 64;               // implication',
        '                      !is_long -> len inside {[1:16]};',
        '                      solve is_long before len; }         // shape distribution only',
        "  constraint c_pay  { payload.size() == int'(len);",
        "                      foreach (payload[i]) payload[i] != 8'hFF; }",
        '  constraint c_def  { soft len < 32; }                    // yields to inline constraints',
        'endclass',
        '',
        'module q_rand;',
        '  initial begin',
        '    packet p;',
        '    p = new();',
        '    if (!p.randomize() with { len == 100; }) $error("randomize failed");',
        '    p.c_def.constraint_mode(0);                           // switch a block off',
        '    p.kind.rand_mode(0);                                  // freeze one variable',
        '  end',
        'endmodule'])
    qa("What happens when `randomize()` fails?",
       "It returns 0 and leaves all random variables unchanged; nothing else "
       "happens unless you check. Always write `if (!obj.randomize()) "
       "$fatal(...)` or an `assert` - but not `assert(obj.randomize())` if "
       "assertions might be disabled, because the call would disappear with it.")
    qa("What are `pre_randomize` and `post_randomize`?",
       "Callbacks the solver calls automatically before and after solving, "
       "recursively for rand sub-objects. Use them to set up state variables or to "
       "compute derived fields (a CRC, a parity) from the random values.")
    qa("What is random stability?",
       "Every thread and object has its own random number generator seeded from "
       "its parent, so adding a new `randomize` call or thread elsewhere does not "
       "change the sequence seen by existing ones. That is why `$urandom` and "
       "`randomize()` are preferred to `$random`, and why a failing test reproduces "
       "with the same seed.")
    qa("How do you randomize a variable that is not in a class?",
       "`std::randomize(x, y) with { x < y; };` randomizes local or module "
       "variables with inline constraints. `$urandom_range(max, min)` covers "
       "simple uniform ranges.")

    # -------------------------------------------------------------- IPC (7)
    ah2("Processes and inter-process communication")
    qa("Explain `fork...join`, `join_any` and `join_none`.",
       "`join` waits for all children; `join_any` for the first (the others keep "
       "running); `join_none` does not wait (children start when the parent "
       "blocks or finishes). `wait fork` waits for all descendants; `disable "
       "fork` kills them. Appendix A shows all of them running.")
    qa("What does this loop print, and how do you fix it?",
       ["IEEE 1800 semantics: the three threads of the first loop are created by "
        "`join_none` but only start when the parent blocks at `#2`; by then the "
        "single loop variable `i` is 3, so all print `A3`. The fix declares an "
        "`automatic` copy per iteration, captured when the fork executes, giving "
        "`B0 B1 B2`. Commercial simulators print `A3 A3 A3` and `B0 B1 B2`. "
        "Beware tool differences: Verilator 5.020 prints `A0 A1 A2` for the first "
        "loop and Icarus 12 does not support the `automatic` declaration here - so "
        "no output card is shown."], ['module q_forkloop;',
                                      '  initial begin',
                                      '    for (int i = 0; i < 3; i++)',
                                      '      fork',
                                      '        #1 $write("A%0d ", i);           // all threads see the final i',
                                      '      join_none',
                                      '    #2 $display("");',
                                      '    for (int i = 0; i < 3; i++) begin',
                                      '      automatic int k = i;               // per-iteration copy captured by the thread',
                                      '      fork',
                                      '        #1 $write("B%0d ", k);',
                                      '      join_none',
                                      '    end',
                                      '    #2 $display("");',
                                      '    $finish;',
                                      '  end',
                                      'endmodule'])
    qa("What is the difference between `@(ev)` and `wait(ev.triggered)`?",
       "`@(ev)` blocks until the next trigger, so if `->ev` executes earlier in the "
       "same time step the waiter misses it and may hang. `wait(ev.triggered)` "
       "is true for the whole time step in which `ev` was triggered, removing that "
       "race. `->>ev` triggers in the NBA region.")
    qa("How do mailboxes and semaphores work? What does this print?",
       ["A mailbox is a FIFO between processes: `put` (blocks when a bounded mailbox "
        "is full), `get` (blocks when empty), `try_put`/`try_get`/`peek` "
        "(non-blocking). `mailbox #(T)` is type-checked. A semaphore is a bucket of "
        "keys: `get(n)` blocks until n keys are available, `put(n)` returns them. "
        "With a bound of 2 the producer stalls on its third item until the consumer "
        "frees space; the semaphore serialises P1 and P2."], ['module q_mbx;',
                                                              '  mailbox #(int) mb = new(2);            // bounded: put() blocks when 2 items queued',
                                                              '  semaphore      key = new(1);',
                                                              '  initial begin',
                                                              '    fork',
                                                              '      for (int i = 1; i <= 4; i++) begin mb.put(i); $display("%0t put %0d", $time, i); end',
                                                              '      repeat (4) begin int v; #10 mb.get(v); $display("%0t   got %0d", $time, v); end',
                                                              '    join',
                                                              '    fork',
                                                              '      begin key.get(1); $display("%0t P1 has key", $time); #5 key.put(1); end',
                                                              '      begin key.get(1); $display("%0t P2 has key", $time); #5 key.put(1); end',
                                                              '    join',
                                                              '    $finish;',
                                                              '  end',
                                                              'endmodule'])
    out(['0 put 1',
         '0 put 2',
         '10   got 1',
         '10 put 3',
         '20   got 2',
         '20 put 4',
         '30   got 3',
         '40   got 4',
         '40 P1 has key',
         '45 P2 has key'], caption="Verilator 5.020")
    qa("How do you implement a timeout around a task call?",
       ["Race the task against a delay inside an isolating fork:",
        "`fork begin fork do_xfer(); begin #1us; $error(\"timeout\"); end join_any "
        "disable fork; end join` - the outer `fork begin ... end join` limits "
        "`disable fork` to these two threads."])
    qa("What does `disable` do on a named block versus `disable fork`?",
       "`disable blk;` terminates the named block (or task) - in every process "
       "executing it, which surprises people with re-entrant tasks. `disable "
       "fork;` terminates all child processes of the calling process. `break` and "
       "`continue` (SV) replace `disable` for loop control.")
    qa("How do you get a handle to a process and control it?",
       "`process p = process::self();` inside the thread; then `p.status()`, "
       "`p.kill()`, `p.suspend()`, `p.resume()`, `p.await()`, `p.srandom(seed)`. "
       "This gives finer control than `disable fork`.")

    # -------------------------------------------------------------- SVA (8)
    ah2("SystemVerilog Assertions")
    qa("Immediate versus concurrent versus deferred assertions?",
       "Immediate (`assert (expr)`) is procedural, checks at once, no clock. "
       "Concurrent (`assert property (...)`) is clocked, samples values in the "
       "Preponed region and can span many cycles. Deferred immediate "
       "(`assert #0` / `assert final`) reports only after the values settle in the "
       "time step, avoiding glitches from zero-delay ordering.")
    qa("`|->` versus `|=>`?",
       "`a |-> b` (overlapping): `b` checked in the same cycle as the end of `a`. "
       "`a |=> b` (non-overlapping): one cycle later; it equals `a |-> ##1 b`.")
    qa("What is a vacuous pass?",
       "An implication whose antecedent never matches passes vacuously. An "
       "assertion that only ever passes vacuously checked nothing, so pair "
       "important assertions with `cover property` on the antecedent.")
    qa("Explain `[*n]`, `[->n]` and `[=n]`.",
       "`a[*3]`: `a` on 3 **consecutive** cycles. `a[->3]` (goto): 3 not "
       "necessarily consecutive occurrences, ending **on** the third. `a[=3]` "
       "(non-consecutive): 3 occurrences, and the match may extend past the third "
       "while `a` stays low.")
    qa("How do `$rose`, `$fell`, `$stable` and `$past` evaluate?",
       "They compare the sampled value in the current clock tick with the "
       "previous one: `$rose(a)` means the LSB went to 1. `$past(a, n)` returns the "
       "value n ticks ago (X or the initial value before n ticks exist). All use "
       "Preponed-region samples, so they see values before the clock edge "
       "updates.")
    qa("What does `disable iff` do?",
       "It asynchronously aborts an in-flight evaluation when its condition is "
       "true (typically reset), so neither pass nor fail is reported. `default "
       "disable iff (!rst_n);` applies it to every assertion in the scope.")
    qa("How do you attach assertions to a design without editing it?",
       "`bind dut_module sva_checker u_chk (.*);` instantiates the checker inside "
       "every instance of `dut_module` (or a specific instance path). Verification "
       "engineers keep assertions in separate files that way.")
    qa("`assert`, `assume`, `cover`, `restrict` - differences in formal and simulation?",
       "`assert`: must hold - a proof target. `assume`: environment constraint; "
       "formal uses it to limit inputs and simulation checks it like an assert. "
       "`cover`: must be reachable - proves a scenario is possible. `restrict` "
       "(2009): constrains formal only and is ignored in simulation.")

    # ---------------------------------------------------------- coverage (6)
    ah2("Functional coverage")
    qa("Code coverage versus functional coverage?",
       "Code coverage (line, branch, condition, toggle, FSM) is collected "
       "automatically and tells you which code executed. Functional coverage is "
       "written by the engineer from the verification plan and tells you which "
       "**features** were exercised. 100% code coverage with missing functional "
       "coverage means untested scenarios; the reverse means missing features or "
       "dead code.")
    qa("What are bins, and what are `illegal_bins` and `ignore_bins`?",
       "Bins are counters for values or ranges of a coverpoint (`bins b[] = "
       "{[0:3]}` creates one per value). `ignore_bins` excludes values from the "
       "coverage goal; `illegal_bins` excludes them and reports an error if hit.")
    qa("How is a covergroup sampled?",
       "By a clocking event in its declaration (`covergroup cg @(posedge clk);`), "
       "by calling `cg_inst.sample()`, or by a user-defined `sample` function with "
       "arguments (`with function sample(...)`). A covergroup must be constructed "
       "with `new()` or nothing is collected.")
    qa("What are transition bins and cross coverage?",
       "Transition bins cover sequences of values: `(0 => 1 => 2)`, `(3 => 0)`, "
       "`(1 [*3])`. `cross` counts combinations of coverpoints; use `binsof` with "
       "`ignore_bins` to remove impossible combinations, otherwise the cross can "
       "never reach 100%.")
    qa("What do `option.per_instance`, `at_least` and `goal` control?",
       "`per_instance = 1` keeps separate coverage per covergroup instance (else "
       "only the merged type coverage is reported); `at_least` is the hit count "
       "for a bin to be covered (default 1); `goal` the target percentage.")
    qa("How do you know when verification is done?",
       "When the functional coverage model derived from the plan is closed (or "
       "each gap is waived), code coverage holes are explained, all assertions "
       "have covered antecedents, bug rate has flattened and regressions pass "
       "across seeds. Coverage without checkers proves nothing - a scenario must be "
       "both reached and checked.")

    # ------------------------------------------------- DPI / UVM-language (7)
    ah2("DPI and how UVM uses the language")
    qa("How do you call C from SystemVerilog and vice versa?",
       ["`import \"DPI-C\"` declares a C function callable from SV; `export "
        "\"DPI-C\"` makes an SV function or task callable from C. Arguments map "
        "directly for C-compatible types (`int` -> `int`, `real` -> `double`, "
        "`string` -> `const char*`, `chandle` -> `void*`) and through `svBit`, "
        "`svLogic`, `svBitVecVal`, `svLogicVecVal` for packed types. A C "
        "function that calls an export must be imported `context`. The example "
        "was compiled with Verilator 5.020, which builds the C file as C++, hence "
        "the `extern \"C\"` guard."], ['module q_dpi;',
                                       '  import "DPI-C" function int c_add(input int a, input int b);   // C: int c_add(int, int)',
                                       '  import "DPI-C" context function void c_run(input string name); // may call exports',
                                       '  export "DPI-C" function sv_log;                                // callable from C',
                                       '  function void sv_log(string msg); $display("[from C] %s", msg); endfunction',
                                       '  initial begin',
                                       '    $display("c_add(2, 3) = %0d", c_add(2, 3));',
                                       '    c_run("dma_test");',
                                       '    $finish;',
                                       '  end',
                                       'endmodule'])
    code(['#include <stdio.h>',
          '#include "svdpi.h"',
          '#ifdef __cplusplus',
          'extern "C" {                  /* Verilator compiles this file as C++ */',
          '#endif',
          'extern void sv_log(const char *msg);           /* prototype of the SV export */',
          'int c_add(int a, int b) { return a + b; }',
          'void c_run(const char *name) {',
          '  char buf[64];',
          '  snprintf(buf, sizeof buf, "running %s", name);',
          "  sv_log(buf);                                  /* legal: import is 'context' */",
          '}',
          '#ifdef __cplusplus',
          '}',
          '#endif'])
    out(['c_add(2, 3) = 5',
         '[from C] running dma_test'], caption="Verilator 5.020: `verilator --binary q_dpi.sv q_dpi.c`")
    qa("What is the difference between `pure` and `context` imports?",
       "`pure`: result depends only on inputs, no side effects - the simulator may "
       "optimise or skip calls. `context`: the C code may call exported SV "
       "functions or access the calling scope via `svGetScope` and VPI; the "
       "simulator must preserve scope information, which costs speed. Default is "
       "neither.")
    qa("How does the UVM factory work in language terms?",
       "The macro call `uvm_component_utils(my_drv)` expands to a `typedef "
       "uvm_component_registry #(my_drv, \"my_drv\") type_id;` whose static "
       "member registers a proxy object with the factory at time 0 (static "
       "initialisation of a parameterized class specialization). `type_id::create` "
       "asks the factory, which checks overrides and calls the proxy's `create`, "
       "which calls `new` of the right class - a virtual constructor built from "
       "parameterized classes and statics (Chapter 26).")
    qa("How does UVM get a virtual interface to a driver?",
       "The top module calls `uvm_config_db #(virtual bus_if)::set(null, "
       "\"uvm_test_top.*\", \"vif\", bus_if_inst);` and the driver's "
       "`build_phase` calls `get` with the same type and name. The config DB is a "
       "parameterized class built on a static resource database keyed by scope and name strings.")
    qa("Why are UVM phases functions or tasks?",
       "`build_phase`, `connect_phase` and the other setup/report phases are "
       "functions because they must take zero time; `run_phase` and the runtime "
       "sub-phases are tasks because they consume simulation time. Objections "
       "(`raise_objection`/`drop_objection`) decide when the time-consuming "
       "phases end.")
    qa("How do TLM ports connect components in UVM?",
       "Ports, exports and imps are parameterized classes (`uvm_analysis_port "
       "#(T)`); `connect()` stores the target handle and `write(t)` calls the "
       "implementing component's `write` method through it - plain handles and "
       "virtual methods, no signals.")
    qa("What is a `uvm_sequence` in language terms?",
       "A class whose `body()` task generates items; `start_item`/`finish_item` "
       "handshake with the sequencer (which arbitrates with semaphores/queues) and "
       "the driver's `get_next_item`/`item_done`. The `uvm_do` family of macros wraps "
       "`create`, `randomize` and that handshake.")

    # --------------------------------------------------- coding puzzles (8)
    ah2("Coding puzzles")
    qa("Test whether `x` is a power of two, isolate its lowest set bit, reverse its "
       "bits, swap bytes, convert binary to Gray and count ones - one line each.",
       ["`x & (x - 1)` clears the lowest set bit, so it is 0 exactly for powers of "
        "two (exclude `x == 0`). `x & (~x + 1)` (that is `x & -x`) keeps only the "
        "lowest set bit. Streaming reverses bits or bytes. Gray is `x ^ (x >> 1)`. "
        "`$countones` counts (synthesizable in most tools)."],
       ['module q_bits;',
        "  logic [7:0] x = 8'b0110_1000;",
        '  initial begin',
        '    $display("pow2(x)=%b pow2(64)=%b", (x != 0) && ((x & (x - 8\'d1)) == 0),',
        "             (8'd64 & (8'd64 - 8'd1)) == 0);",
        '    $display("lowest set bit  = %b", x & (~x + 8\'d1));',
        '    $display("bit-reverse     = %b", {<<{x}});',
        '    $display("byte-swap       = %h", {<<8{16\'hABCD}});',
        '    $display("bin->gray       = %b", x ^ (x >> 1));',
        '    $display("popcount        = %0d", $countones(x));',
        '    $finish;',
        '  end',
        'endmodule'])
    out(['pow2(x)=0 pow2(64)=1',
         'lowest set bit  = 00001000',
         'bit-reverse     = 00010110',
         'byte-swap       = cdab',
         'bin->gray       = 01011100',
         'popcount        = 3'], caption="Verilator 5.020")
    qa("How do `case`, `casez` and `casex` treat an X in the selector?",
       ["`case` matches X only against an item with X in the same position. "
        "`casez` treats `z`/`?` in either side as don't-care, but X is still an "
        "exact value. `casex` treats X as don't-care, so `2'b1x` matches `2'b10`. "
        "An `if (s == 2'b10)` gets X and takes the else branch."],
       ['module q_case;',
        "  logic [1:0] s = 2'b1x;",
        '  initial begin',
        '    case  (s) 2\'b10: $display("case : 10");  2\'b1x: $display("case : 1x");',
        '              default: $display("case : default"); endcase',
        '    casez (s) 2\'b1?: $display("casez: 1?");  default: $display("casez: default"); endcase',
        '    casex (s) 2\'b10: $display("casex: 10");  default: $display("casex: default"); endcase',
        '    if (s == 2\'b10) $display("if   : taken"); else $display("if   : else (s==10 is x)");',
        '  end',
        'endmodule'])
    out(['case : 1x',
         'casez: 1?',
         'casex: 10',
         'if   : else (s==10 is x)'], caption="Icarus 12")
    qa("Write a parameterized N-bit synchronous counter with enable and "
       "active-low async reset.",
       "One `always_ff`: `always_ff @(posedge clk or negedge rst_n) if (!rst_n) "
       "cnt <= '0; else if (en) cnt <= cnt + 1'b1;` with `logic [N-1:0] cnt`. "
       "`'0` scales with N; `1'b1` extends to N bits in context.")
    qa("How do you write a combinational priority encoder that synthesizes cleanly?",
       "In `always_comb`: default the outputs (`idx = '0; valid = 1'b0;`), then "
       "`for (int i = 0; i < N; i++) if (req[i]) begin idx = i[IW-1:0]; valid = "
       "1'b1; end` - the last match wins, so this gives highest-index priority; "
       "loop downward for lowest. The loop unrolls into a mux chain.")
    qa("Swap two variables without a temporary in RTL.",
       "`a <= b; b <= a;` in the same clocked block - non-blocking assignments "
       "sample both RHS values before either update. In procedural testbench code, "
       "`{a, b} = {b, a};` also works because the RHS concatenation is evaluated "
       "first.")
    qa("What is wrong with `assign y = sel ? a : 8'bz;` driving an internal bus?",
       "Nothing in simulation, but internal tri-states are not supported in most "
       "ASIC flows (and poorly in FPGAs): synthesis converts them to muxes or "
       "fails. Keep `z` for top-level pads and use muxes internally.")
    qa("Generate a 50 MHz clock and a reset that deasserts after 3 edges in a "
       "testbench.",
       "`initial clk = 0; always #10ns clk = ~clk;` (20 ns period), and "
       "`initial begin rst_n = 0; repeat (3) @(posedge clk); rst_n <= 1; end`. The "
       "non-blocking release avoids a race with flops sampling `rst_n` on the "
       "same edge.")
    qa("Detect a rising edge of an input `d` synchronously.",
       "Register it and compare: `always_ff @(posedge clk) d_q <= d;` and `assign "
       "rise = d & ~d_q;`. If `d` is asynchronous, pass it through a 2-flop "
       "synchronizer first and detect the edge on the synchronized value.")
    assert _Q["n"] == 100, _Q["n"]


# =============================================================================
# Appendix D - standards, tools and resources
# =============================================================================
def _appx_d():
    appendix("Standards, Tools and Resources")
    p("This appendix maps the documents, tools and code bases you will meet "
      "when working with Verilog and SystemVerilog professionally. Product names "
      "and ownership change often (vendors merge and rename tools); the "
      "standards numbers are the stable anchors.")

    ah2("Verilog: IEEE 1364")
    tbl(["Edition", "Key content"],
        [["Pre-IEEE (1984-1995)", "Gateway Design Automation created Verilog-XL in "
          "1984; Cadence acquired Gateway (1989) and released the language to "
          "Open Verilog International (OVI) in 1990, which led to "
          "standardisation."],
         ["IEEE 1364-1995", "First standard: modules, nets and `reg`, gate "
          "primitives and UDPs, `specify` blocks, the PLI (tf/acc routines and "
          "VPI)."],
         ["IEEE 1364-2001", "The big update (Verilog-2001): ANSI-style ports, "
          "`generate`/`genvar`, `signed` types and `$signed`, `**`, `>>>`/`<<<`, "
          "multi-dimensional arrays, `always @*`, `localparam`, configurations, "
          "file I/O (`$fopen` modes, `$fscanf`...), the `ifndef` and `elsif` "
          "directives, `automatic` tasks/functions, an extended VPI."],
         ["IEEE 1364-2005", "Corrections and clarifications; `uwire`, the "
          "keyword-version directives, generate-scope naming rules; the old tf/acc "
          "PLI routines deprecated in favour of VPI. The last standalone Verilog "
          "standard."],
         ["IEEE 1364.1-2002", "RTL synthesis subset: what synthesis tools must "
          "accept and how they interpret it."],
         ["After 2009", "IEEE 1364 was merged into IEEE 1800-2009 and is no longer "
          "maintained; 'Verilog' today means the Verilog subset of 1800."]],
        widths=[20, 80], bold_first=True)

    ah2("SystemVerilog: IEEE 1800")
    tbl(["Edition", "Key additions"],
        [["Accellera SV 3.0 / 3.1 / 3.1a (2002-2004)", "Donations from Co-Design "
          "(Superlog), Synopsys (Vera verification language and OpenVera "
          "assertions), Novas (debug API) and others were merged into Verilog by "
          "Accellera, then handed to IEEE."],
         ["IEEE 1800-2005", "First IEEE SystemVerilog, published as an **extension** "
          "to 1364-2005: `logic`, 2-state types, enums, structs, unions, typedefs, "
          "packages, interfaces and modports, `always_comb/ff/latch`, "
          "`unique`/`priority`, classes, constrained random, dynamic and "
          "associative arrays, queues, strings, mailboxes/semaphores/events, "
          "clocking and program blocks, SVA, covergroups, DPI."],
         ["IEEE 1800-2009", "Merged with 1364 into a single language document. "
          "Checkers, `let`, global clocking, strong/weak properties and LTL "
          "operators (`until`, `s_eventually`, `nexttime`, `accept_on`...), deferred "
          "immediate assertions, `unique0`, macros with default arguments."],
         ["IEEE 1800-2012", "Interface classes (`implements`, multiple inheritance "
          "of API), `soft` constraints, `unique` constraints, user-defined nettypes "
          "and `interconnect`, covergroup enhancements (`with` clause on bins, "
          "cross-bin select expressions), `$assertcontrol`, real number modelling "
          "improvements. Free download through the IEEE GET program, sponsored "
          "by Accellera."],
         ["IEEE 1800-2017", "Corrections and clarifications only - no significant "
          "new features. The reference most tools and this book target; free "
          "through IEEE GET."],
         ["IEEE 1800-2023", "Published early 2024 (also free through IEEE GET). "
          "Additions include method override qualifiers (`:initial`, `:extends`, "
          "`:final`), triple-quoted multi-line string literals, boolean expressions "
          "in the `ifdef` directive, coverpoints of `real` type, and further class and "
          "constraint refinements; tool support lags by several years, so check "
          "your simulators before using them."]],
        widths=[24, 76], bold_first=True)

    ah2("Related standards")
    tbl(["Standard", "What it is", "Where you meet it"],
        [["IEEE 1800.2 (UVM)", "Universal Verification Methodology class library "
          "API: 1800.2-2017 and 1800.2-2020. Accellera maintains the open-source "
          "reference implementation (UVM 1.1d and 1.2 were the pre-IEEE Accellera "
          "releases; the '2017-x.y' and '2020-x.y' releases track the IEEE "
          "editions).",
          "Every commercial DV environment (Chapter 26)"],
         ["IEEE 1801 (UPF)", "Unified Power Format: power domains, supply networks, "
          "isolation, retention, level shifters (editions 2009, 2013, 2015, 2018 "
          "and later).", "Power-aware simulation, synthesis, P&R"],
         ["IEEE 1735", "Recommended practice for encryption and rights "
          "management of IP (`pragma protect` envelopes).", "Encrypted vendor IP, "
          "memory models"],
         ["IEEE 1497 (SDF)", "Standard Delay Format for back-annotating delays and "
          "timing checks.", "Gate-level simulation (Chapter 9)"],
         ["IEEE 1685 (IP-XACT)", "XML description of IP: ports, bus interfaces, "
          "register maps.", "SoC integration, register generation"],
         ["Accellera SystemRDL 2.0", "Register description language from which RTL, "
          "UVM register models, C headers and docs are generated.",
          "CSR blocks (tools: PeakRDL, commercial generators)"],
         ["IEEE 1850 (PSL)", "Property Specification Language; largely superseded "
          "by SVA for SV users.", "Older VHDL/mixed flows"],
         ["IEEE 1666 (SystemC)", "C++ class library for system-level and TLM "
          "modelling.", "Architecture models, virtual prototypes"],
         ["Accellera PSS", "Portable Test and Stimulus Standard: abstract "
          "scenario models retargeted to UVM, C tests and post-silicon.",
          "SoC-level test generation"],
         ["Accellera UCIS", "Unified Coverage Interoperability Standard (coverage "
          "database API).", "Coverage merging across tools"]],
        widths=[20, 50, 30], bold_first=True)

    ah2("Simulators")
    tbl(["Simulator", "Type", "Notes"],
        [["Synopsys VCS", "Commercial", "Full SV/UVM, constraint solver, "
          "coverage, SVA; Verdi debugger"],
         ["Cadence Xcelium", "Commercial", "Full SV/UVM, multi-core; SimVision/"
          "Verisium debug"],
         ["Siemens Questa (and ModelSim)", "Commercial", "Full SV/UVM in Questa; "
          "ModelSim editions shipped with FPGA tools have limited SV verification "
          "support"],
         ["Aldec Riviera-PRO / Active-HDL", "Commercial", "Full SV/UVM; popular "
          "in FPGA and mixed-language work; available on EDA Playground"],
         ["AMD Vivado simulator (xsim)", "Free with Vivado", "SV design and much "
          "of verification including UVM"],
         ["Altair DSim (formerly Metrics)", "Commercial, free tier", "Cloud/desktop "
          "SV/UVM simulator"],
         ["Verilator", "Open source", "Compiles SV to multithreaded C++; fastest "
          "open simulator; 2-state; strong on design, growing on verification "
          "(classes, timing, fork); limited SVA, no constraint solving or "
          "covergroups in 5.020"],
         ["Icarus Verilog", "Open source", "Event-driven 4-state interpreter; "
          "excellent Verilog-2005, partial SV (limited classes; no `ref` "
          "arguments or unpacked structs in v12)"],
         ["CVC / Tachyon", "Open source", "Compiled Verilog-2005 simulator with "
          "full 4-state and timing"]],
        widths=[28, 18, 54], bold_first=True)

    ah2("Front ends, lint and formal")
    tbl(["Tool", "Type", "Use"],
        [["slang", "Open source", "Complete, fast SV parser and elaborator with "
          "excellent diagnostics; `pyslang` Python bindings (used to check this "
          "book's templates)"],
         ["Surelog / UHDM", "Open source", "SV front end producing a universal "
          "hardware data model for other tools"],
         ["sv2v", "Open source", "Converts SV design code to Verilog-2005 for "
          "older tools"],
         ["Verible", "Open source", "Parser, style linter, formatter and language "
          "server (from Google/CHIPS Alliance)"],
         ["svlint", "Open source", "Configurable rule-based SV linter"],
         ["Verilator `--lint-only -Wall`", "Open source", "Quick width/latch/"
          "multi-driver lint"],
         ["Yosys + SymbiYosys (sby)", "Open source", "Synthesis, equivalence and "
          "formal property checking (immediate assertions and a subset of SVA in "
          "the open front end)"],
         ["EBMC", "Open source", "Bounded model checker for SV with SVA support"],
         ["Synopsys SpyGlass / VC SpyGlass", "Commercial", "Lint, CDC, RDC, "
          "constraints"],
         ["Siemens Questa Lint / CDC / Formal", "Commercial", "Lint, clock-domain "
          "crossing, property checking"],
         ["Cadence Jasper", "Commercial", "Formal apps (FPV, connectivity, "
          "sequential equivalence, X-prop)"],
         ["Synopsys VC Formal", "Commercial", "Formal property and equivalence apps"],
         ["Real Intent Ascent / Meridian", "Commercial", "Lint, X-propagation, CDC, "
          "RDC"],
         ["Cadence Conformal / Synopsys Formality", "Commercial", "Logical "
          "equivalence checking RTL vs netlist"]],
        widths=[30, 16, 54], bold_first=True)

    ah2("Online playgrounds and references")
    tbl(["Resource", "What it offers"],
        [["EDA Playground (edaplayground.com)", "Browser-based editor with free "
          "access to commercial and open simulators, UVM libraries and waveform "
          "viewing; ideal for trying a construct on several tools and sharing a "
          "reproducible example."],
         ["CHIPS Alliance sv-tests", "Per-LRM-clause test suite with a public table "
          "of which open tools support which SV feature - check here before "
          "relying on a construct in an open flow."],
         ["HDLBits", "Graded Verilog practice problems from gates to FSMs."],
         ["Verification Academy (Siemens)", "UVM, coverage and formal courses and "
          "the UVM cookbook."],
         ["Accellera and IEEE GET", "Free IEEE 1800-2017/2023 and 1800.2 PDFs; UVM "
          "reference implementation downloads."],
         ["Sunburst Design paper archive", "Cummings' SNUG and "
          "DVCon papers (see below)."],
         ["DVCon and SNUG proceedings", "Industrial papers on SV, UVM, SVA and "
          "coverage methodology; the best source for 'how teams really do it'."],
         ["Doulos KnowHow, ChipVerify", "Short tutorials and examples for most "
          "language features."]],
        widths=[32, 68], bold_first=True)

    ah2("Books")
    tbl(["Book", "Authors", "Why read it"],
        [["Verilog HDL: A Guide to Digital Design and Synthesis (2nd ed.)",
          "Samir Palnitkar", "Classic Verilog-2001 introduction with gate-level, "
          "switch-level and PLI coverage"],
         ["SystemVerilog for Design (2nd ed.)", "Stuart Sutherland, Simon "
          "Davidmann, Peter Flake", "The design subset of SV explained by members "
          "of the standards committee"],
         ["RTL Modeling with SystemVerilog for Simulation and Synthesis",
          "Stuart Sutherland", "Modern synthesizable coding, with tool results"],
         ["Verilog and SystemVerilog Gotchas", "Stuart Sutherland, Don Mills",
          "101 language traps with explanations - interview gold"],
         ["SystemVerilog for Verification (3rd ed.)", "Chris Spear, Greg Tumbush",
          "The standard DV textbook: OOP, randomization, IPC, coverage"],
         ["SVA: The Power of Assertions in SystemVerilog (2nd ed.)", "Eduard Cerny, "
          "Surrendra Dudani, John Havlicek, Dmitry Korchemny", "Definitive, "
          "formal-semantics-level treatment of SVA by its designers"],
         ["SystemVerilog Assertions and Functional Coverage", "Ashok B. Mehta",
          "Practical, example-driven SVA and covergroup guide"],
         ["The UVM Primer", "Ray Salemi", "Gentle path from SV OOP to UVM with a "
          "small complete testbench"],
         ["Writing Testbenches using SystemVerilog", "Janick Bergeron",
          "Verification methodology foundations"],
         ["A Practical Guide to Adopting the Universal Verification Methodology",
          "Sharon Rosenberg, Kathleen Meade", "UVM architecture from Cadence "
          "authors"]],
        widths=[38, 26, 36])

    ah2("Clifford Cummings' SNUG papers worth reading")
    bul(["__Nonblocking Assignments in Verilog Synthesis, Coding Styles That Kill!__ "
         "(SNUG 2000) - the origin of the blocking/non-blocking rules (Chapter 5).",
         "__\"full_case parallel_case\", the Evil Twins of Verilog Synthesis__ "
         "(SNUG 1999) - why pragmas cause mismatches (Chapter 11).",
         "__Synchronous Resets? Asynchronous Resets? I am so confused!__ (with Don "
         "Mills, SNUG 2002) and its sequel __Asynchronous and Synchronous Reset "
         "Design Techniques - Part Deux__ (with Mills and Steve Golson, SNUG 2003).",
         "__Simulation and Synthesis Techniques for Asynchronous FIFO Design__ "
         "(SNUG 2002) and __Clock Domain Crossing (CDC) Design and Verification "
         "Techniques Using SystemVerilog__ (SNUG 2008).",
         "__Verilog Nonblocking Assignments With Delays, Myths and Mysteries__ "
         "(SNUG 2002) - scheduling details behind `#` in NBAs.",
         "__SystemVerilog Logic Specific Processes for Synthesis - Benefits and "
         "Proper Usage__ (SNUG 2016) - `always_comb`/`always_ff` in depth.",
         "Papers on SV implicit port connections, UVM transaction coding styles "
         "and the UVM factory - all at sunburst-design.com."])

    ah2("Open-source SystemVerilog code bases to read")
    tbl(["Project", "What to learn from it"],
        [["lowRISC Ibex", "Small, production-quality RV32 core in clean SV; its "
          "DV uses UVM-style environments, riscv-dv random instruction generation "
          "and formal; read with the lowRISC Verilog coding style guide."],
         ["OpenTitan", "Complete open silicon root-of-trust SoC: comportable IP "
          "template, register generation from HJSON, TL-UL bus, DV methodology "
          "with UVM, assertions and coverage at scale."],
         ["PULP platform (ETH Zurich / Bologna)", "`common_cells` (FIFOs, arbiters, "
          "CDC), the `axi` library with type-parameterized structs, Snitch and "
          "CV32E40P cores - excellent SV design idioms (Chapter 17)."],
         ["CVA6 (OpenHW Group)", "64-bit application-class RISC-V core (formerly "
          "Ariane) with MMU and caches; industrial verification in core-v-verif."],
         ["Verilator test suite (`test_regress/t`)", "Thousands of tiny, "
          "self-checking SV programs, one feature each - the fastest way to see "
          "how a construct is supposed to behave in an open tool."],
         ["Accellera UVM reference implementation", "The `uvm-core` source: how "
          "factories, config DB, phasing and TLM are built from classes, "
          "parameterization and static members (Chapter 26)."],
         ["CHIPS Alliance sv-tests and slang tests", "Minimal examples keyed to "
          "LRM clauses."]],
        widths=[30, 70], bold_first=True)

    ah2("How to use these resources")
    bul(["Keep the free IEEE 1800-2017 (or 2023) PDF open and look up the clause "
         "whenever a rule in this book matters to your code.",
         "Try every unfamiliar construct on at least two tools (EDA Playground "
         "makes that free); if they disagree, the LRM decides - and your code "
         "should avoid the construct until both agree.",
         "Lint continuously (Verilator, Verible or a commercial linter) and read "
         "each warning as a lesson in the sizing and signedness rules of "
         "Appendix B.",
         "Read one real code base end to end - Ibex is the right size - before "
         "writing your first large block.",
         "Revisit the interview questions of Appendix C after each part of the "
         "book; the ones you cannot answer point to the chapter to reread."],
        ordered=True)


def appendices():
    part("Appendices",
         numbered=False,
         blurb="A keyword and syntax quick reference, the operator, sizing and "
         "system-task rules in table form, 100 interview questions with "
         "answers, and the standards, tools, books and code bases of the "
         "Verilog and SystemVerilog world.")
    _appx_a()
    _appx_b()
    _appx_c()
    _appx_d()
