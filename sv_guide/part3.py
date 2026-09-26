"""Part III - SystemVerilog for Design (Chapters 12-17) of the Verilog &
SystemVerilog guide.

Every listing followed by an out() card was compiled and run in this
repository's environment: Icarus Verilog 12 (iverilog -g2012 -Wall / vvp)
where it supports the construct, otherwise Verilator 5.020
(verilator --binary --timing -Wall); synthesis results come from Yosys 0.33.
Constructs that neither tool supports (tagged unions, some interface
features) are shown without output and labelled as needing a commercial
simulator.
"""

from sv_guide.common import *  # noqa: F401,F403


def part3():
    part("SystemVerilog for Design",
         "SystemVerilog turned Verilog from a netlist-era description language "
         "into a modern design language: a single `logic` type, strong enums, "
         "structs and unions, packages, interfaces, intent-carrying always "
         "blocks and a rich set of operators. This part covers every "
         "design-side feature at the level of the IEEE 1800 rules, shows what "
         "each one becomes in hardware, which tools accept it, and how the "
         "open-source RTL of real SoCs (lowRISC, PULP, OpenTitan) uses it.")
    ch12()
    ch13()
    ch14()
    ch15()
    ch16()
    ch17()


# =============================================================================
#     Chapter 12 - SystemVerilog data types
# =============================================================================
def ch12():
    chapter("SystemVerilog Data Types: logic, 2-State Types, Enums, Typedefs, "
            "Structs, Unions, Strings and Casting", newpage=False)
    p("Chapter 3 described the Verilog-2005 type system: nets and variables, "
      "four-valued logic, vectors and arrays. That system has two famous "
      "weaknesses. First, the keyword `reg` suggests a register but only means "
      "\"a variable\", so every beginner has to unlearn it. Second, everything "
      "is an untyped bit vector: there is no way to say that a signal is a "
      "state of an FSM, an AXI response code or a packet header, so the "
      "compiler cannot catch mistakes. SystemVerilog fixes both. It separates "
      "the **kind** of an object (net or variable) from its **data type**, adds "
      "2-state integer types for fast testbenches, and adds user-defined types: "
      "enumerations, structures, unions and typedefs. It also adds a real "
      "`string` type and a disciplined casting system.")
    p("Everything in this chapter is used daily on an SoC project. RTL "
      "designers use `logic`, enums, packed structs and typedefs; DV engineers "
      "additionally use the 2-state types, strings, unpacked structs and "
      "`$cast`. Examples were run with Icarus Verilog 12 where it supports the "
      "construct and with Verilator 5.020 otherwise; the chapter notes where "
      "the two tools differ, because those differences are exactly the "
      "portability traps you will meet in industry.")

    # ------------------------------------------------------------------
    h2("logic, reg and wire: kind versus data type")
    p("In IEEE 1800 every declared object has a **kind** - net or variable - "
      "and a **data type** - the set of values it can hold. `logic` is a data "
      "type: the 4-state (0, 1, x, z) single bit, extended to vectors with a "
      "packed range. `reg` is simply a synonym for `logic` kept for backward "
      "compatibility. `wire` is a net kind whose default data type is "
      "`logic`. The rules that decide what a declaration is are:")
    tbl(["Declaration", "Kind", "Data type", "Notes"],
        [["`logic [7:0] a;`", "variable", "logic [7:0]",
          "`logic` alone (outside a port) always declares a variable"],
         ["`reg [7:0] a;`", "variable", "logic [7:0]", "identical to the line above"],
         ["`wire [7:0] a;`", "net", "logic [7:0]", "`wire` is shorthand for `wire logic`"],
         ["`wire logic [7:0] a;`", "net", "logic [7:0]", "explicit form"],
         ["`var logic [7:0] a;`", "variable", "logic [7:0]",
          "explicit form; `var` alone implies logic"],
         ["`input logic [7:0] a`", "net", "logic [7:0]",
          "input/inout ports with only a data type are nets (default net type)"],
         ["`output logic [7:0] y`", "variable", "logic [7:0]",
          "output ports with a data type are variables"],
         ["`wire bit b;`", "-", "-", "illegal: a net's data type must be 4-state"]],
        widths=[24, 12, 16, 48])
    p("The practical difference between a net and a variable is **how it may "
      "be driven**. A net resolves any number of drivers (continuous "
      "assignments, primitive outputs, port connections) with the resolution "
      "function of its net type - this is how tri-state buses and `inout` pads "
      "work. A variable has no resolution function, so IEEE 1800 (6.5) allows "
      "a variable to be written **either** by any number of procedural "
      "assignments **or** by exactly one continuous assignment or one output "
      "port - never both, and never two continuous drivers. `always_comb`, "
      "`always_ff` and `always_latch` tighten this further: a variable written "
      "by one of them may not be written by any other process (Chapter 14).")
    code([
        'module t12_multi(input logic a, b, output logic y);',
        '  assign y = a;        // first continuous driver',
        '  assign y = b;        // second continuous driver: illegal on a variable',
        'endmodule',
    ], "Two continuous drivers on a `logic` variable.")
    out([
        't12_multi.sv:3: error: Unresolved net/uwire y cannot have multiple drivers.',
        '1 error(s) during elaboration.',
    ], "Icarus Verilog 12: a hard elaboration error, as IEEE 1800 requires.")
    out([
        "%Warning-MULTIDRIVEN: t12_multi.sv:1:49: Bits [0:0] of signal 'y' have multiple",
        '    combinational drivers',
    ], "Verilator 5.020: only a lint warning; the model is still built.")
    box("warn", "Pitfall: the single-driver rule is enforced unevenly",
        ["The rule \"a variable may not have multiple continuous drivers\" is "
         "what makes `logic` safer than `wire`: an accidental second `assign` "
         "or two instances driving the same signal becomes a compile error "
         "instead of a silent x in simulation. Commercial simulators and "
         "synthesis tools report it as an error; Verilator only warns "
         "(MULTIDRIVEN), so a design that is clean in a Verilator-only flow "
         "can fail the first time it meets VCS, Xcelium or Design Compiler. "
         "Treat MULTIDRIVEN as an error in lint."])
    box("tip", "House style used on most SoC projects",
        ["Declare everything as `logic` - ports, internal signals, flops. Use "
         "`wire` (or `tri`) only for signals that genuinely have several "
         "drivers: bidirectional pads, tri-state test buses and analog-ish "
         "top-level connections. Put the directive `default_nettype none` (written with a "
         "leading grave accent, as in the listings) at the top of every file so that a typo cannot create an implicit 1-bit wire "
         "(Chapter 8). lowRISC and PULP style guides both mandate `logic`."])

    # ------------------------------------------------------------------
    h2("Integer and real types: 2-state versus 4-state")
    p("SystemVerilog adds C-like integer types. The 2-state types store only "
      "0 and 1; they need half the memory of 4-state types and let simulators "
      "use native machine arithmetic, which is why testbench code uses them. "
      "The table lists every built-in integral and real type.")
    tbl(["Type", "States", "Width", "Default signedness", "Typical use"],
        [["`bit`", "2", "1 (vector with range)", "unsigned", "TB flags, 2-state vectors"],
         ["`byte`", "2", "8", "signed", "characters, byte buffers in TB"],
         ["`shortint`", "2", "16", "signed", "C interoperability (DPI)"],
         ["`int`", "2", "32", "signed", "loop counters, TB arithmetic"],
         ["`longint`", "2", "64", "signed", "addresses, cycle counts, DPI"],
         ["`logic` / `reg`", "4", "1 (vector with range)", "unsigned", "all RTL"],
         ["`integer`", "4", "32", "signed", "legacy Verilog loop variables"],
         ["`time`", "4", "64", "unsigned", "simulation time values"],
         ["`real` / `realtime`", "-", "64-bit IEEE double", "-", "models, delays, analog"],
         ["`shortreal`", "-", "32-bit IEEE float", "-", "C float in DPI"]],
        widths=[16, 8, 20, 16, 40], bold_first=True)
    code([
        'module t12_types;',
        "  logic [3:0] l;          // 4-state, starts as 'x",
        '  bit   [3:0] b;          // 2-state, starts as 0',
        '  integer     ig;         // 4-state, 32-bit signed',
        '  int         i;          // 2-state, 32-bit signed',
        '  byte        by;         // 2-state,  8-bit signed',
        '  byte unsigned ub;       // 2-state,  8-bit unsigned',
        '  shortint    si;',
        '  longint     li;',
        '  real        r;',
        '  shortreal   sr;',
        '  initial begin',
        '    $display("init : l=%b b=%b ig=%0d i=%0d", l, b, ig, i);',
        "    l = 4'b1x0z;  b = l;                  // x/z become 0 in a 2-state variable",
        '    $display("x->2s: l=%b b=%b", l, b);',
        "    by = 8'hFF;  ub = 8'hFF;",
        '    $display("byte : by=%0d ub=%0d (by>0)=%0d", by, ub, by > 0);',
        "    si = 16'h8000;  li = 64'sd1 <<< 62;",
        '    $display("width: $bits(si)=%0d si=%0d $bits(li)=%0d", $bits(si), si, $bits(li));',
        '    i = -7;  $display("int  : i/2=%0d i>>>1=%0d i>>1=%0h", i/2, i >>> 1, i >> 1);',
        '    r = 1.0/3;  sr = r;',
        '    $display("real : r=%.10f sr=%.10f", r, sr);',
        '    $finish;',
        '  end',
        'endmodule',
    ], "Initial values, 4-to-2-state conversion, signedness and "
         "arithmetic of the built-in types.")
    out([
        'init : l=xxxx b=0000 ig=x i=0',
        'x->2s: l=1x0z b=1000',
        'byte : by=-1 ub=255 (by>0)=0',
        'width: $bits(si)=16 si=-32768 $bits(li)=64',
        'int  : i/2=-3 i>>>1=-4 i>>1=7ffffffc',
        'real : r=0.3333333333 sr=0.3333333333',
        't12_types.sv:23: $finish called at 0 (1s)',
    ], "Icarus Verilog 12 (a 4-state simulator).")
    out([
        'init : l=0000 b=0000 ig=0 i=0',
        'x->2s: l=0000 b=0000',
    ], "Verilator 5.020 (a 2-state simulator) - the same code, first two lines.")
    p("Read the Icarus output line by line. A 4-state variable starts at x; a "
      "2-state variable starts at 0. Assigning `4'b1x0z` to a `bit [3:0]` "
      "converts each x and z to 0, giving `1000` - IEEE 1800 defines this "
      "conversion and no warning is issued. `byte` is signed, so `8'hFF` "
      "stored in it is -1 and `by > 0` is false; the `unsigned` keyword "
      "changes that. Integer division truncates toward zero (-7/2 = -3) while "
      "the arithmetic shift `>>>` of a signed value rounds toward minus "
      "infinity (-4); the logical shift `>>` shifts in zeros. Verilator, "
      "which models every type in 2 states, prints `l=0000` where every "
      "4-state simulator prints `xxxx` - a first hint that it cannot be your "
      "only simulator for reset and X-propagation checks.")
    box("warn", "Pitfall: 2-state types hide missing resets",
        ["If a flop is declared `bit` and its reset is forgotten, simulation "
         "starts it at 0 and everything looks fine; real silicon powers up "
         "with a random value. With `logic` the missing reset shows up as x "
         "that propagates to outputs and assertions. For the same reason a "
         "DUT output sampled into a `bit` or `int` in the testbench silently "
         "turns x into 0, so a scoreboard can pass while the DUT drives x. "
         "Rule: RTL uses 4-state `logic`; testbench code checks "
         "`$isunknown(dut_sig)` before copying a DUT value into a 2-state "
         "variable. In Verilator flows, use `--x-assign unique` and "
         "`--x-initial unique` to randomize would-be-x values."])
    box("expert", "Interview insight: what does 2-state buy you?",
        ["Speed and memory in the testbench (a large `int` array needs "
         "half the memory of an `integer` one), exact "
         "matching of C types across DPI (`int` is `int32_t`, `longint` is "
         "`int64_t`, `byte` is `char`), and no x-pessimism in reference "
         "models. What it costs: the loss of x as a bug detector. Gate-level "
         "simulation, X-propagation (\"X-prop\") modes of VCS and Xcelium, and "
         "formal reset checks exist precisely to recover that detector."])

    # ------------------------------------------------------------------
    h2("Signedness defaults")
    p("Signedness is part of the data type, and it changes the result of "
      "comparisons, extensions, division, `>>>` and the conversion to real "
      "(Chapter 4). The defaults are easy to forget: `byte`, `shortint`, "
      "`int`, `longint` and `integer` are **signed**; `bit`, `logic`, `reg` "
      "and `time` are **unsigned**; user types built from them inherit the "
      "base type's signedness unless overridden.")
    code(["int unsigned  count;          // 32-bit 2-state unsigned",
          "logic signed [15:0] sample;   // 16-bit 4-state two's complement",
          "byte unsigned  ch;            // 0..255",
          "typedef logic signed [7:0] s8_t;",
          "",
          "// Mixed expressions are unsigned if ANY operand is unsigned (Ch 4):",
          "//   int i = -1;  bit [31:0] u = 1;",
          "//   (i < u)  is FALSE: i is reinterpreted as 32'hFFFF_FFFF"],
         "Overriding default signedness.")
    box("warn", "Pitfall: comparing an int loop index with an unsigned size",
        ["`for (int i = 0; i < n - 1; i++)` with `int unsigned n = 0` does not "
         "run zero times: `n - 1` wraps to 4294967295 and the loop never "
         "terminates. Keep loop bounds and indices of the same signedness, or "
         "cast explicitly: `int'(n) - 1`. Lint rules (Verilator WIDTH, "
         "the width and sign rules of Spyglass or Ascent Lint) exist for exactly this."])

    # ------------------------------------------------------------------
    h2("Enumerated types")
    p("An enumeration declares a set of named values together with a base "
      "type. It is the single most useful SystemVerilog feature for RTL "
      "readability: FSM states, opcodes and response codes become names that "
      "appear in waveforms and log messages, and the compiler refuses to "
      "assign a raw number to an enum variable without a cast.")
    code(["typedef enum {RED, GREEN, BLUE} color_e;             // base type int: 0,1,2",
          "typedef enum logic [1:0] {IDLE, RUN, HALT} st_e;     // explicit 2-bit base",
          "typedef enum logic [2:0] {A = 3'd1, B, C = 3'd6, D} e3_e;   // 1,2,6,7",
          "typedef enum bit [3:0] {OFF = 4'h0, ON = 4'hF} pwr_e;",
          "typedef enum logic [1:0] {S0 = 2'b00, SX = 2'bxx} xs_e;  // x only with 4-state base",
          "typedef enum {R0, R[2:4], REG[3]} regs_e;   // R0, R2,R3,R4, REG0,REG1,REG2",
          "typedef enum {P[4] = 10} p_e;               // P0=10, P1=11, P2=12, P3=13"],
         "Enum declarations: default, explicit base types, explicit values and ranges.")
    p("The rules (IEEE 1800 6.19): the default base type is `int`. Unassigned "
      "names take the previous value plus one, starting at 0. Every value must "
      "fit in the base type and all values must be unique - `enum logic [1:0] "
      "{A = 3, B}` is an error because B would be 4. An x or z value is allowed "
      "only with a 4-state base type, and the name following it must have an "
      "explicit value. `name[N]` generates N names name0..name(N-1) and "
      "`name[N:M]` generates nameN..nameM. Enum literals live in the scope "
      "where the enum is declared, so two enums in the same scope cannot both "
      "define `IDLE` - hence the common prefixing convention (`ST_IDLE`, "
      "`AXI_OKAY`) or putting each enum in its own package.")
    tbl(["Method", "Returns"],
        [["`first()` / `last()`", "the first / last member (declaration order)"],
         ["`next(N=1)` / `prev(N=1)`",
          "the member N positions later / earlier, wrapping around; for a value "
          "that is not a member the result is the default initial value of the "
          "base type (x for a 4-state base, 0 for 2-state)"],
         ["`num()`", "number of members"],
         ["`name()`", "the member's name as a string; \"\" if the value is not a member"]],
        widths=[28, 72])
    code([
        'module t12_enum;',
        "  typedef enum logic [1:0] {IDLE, BUSY, DONE = 2'd3} state_t;",
        '  typedef enum {R0, R[2:4], REG[3]} regs_t;          // enum ranges',
        '  state_t s;',
        '  regs_t  r;',
        '  initial begin',
        '    $display("uninit s=%b name=\'%s\'", s, s.name());',
        '    s = s.first();',
        '    do begin',
        '      $display("s=%0d %-4s next=%s prev=%s", s, s.name(), s.next().name(), s.prev().name());',
        '      s = s.next();',
        '    end while (s != s.first());',
        '    s = IDLE;  s = s.next(2);',
        '    $display("num=%0d last=%s IDLE.next(2)=%s", s.num(), s.last().name(), s.name());',
        '    for (r = r.first(); ; r = r.next()) begin',
        '      $write("%s=%0d ", r.name(), r);',
        '      if (r == r.last()) break;',
        '    end',
        '    $display("");',
        "    s = state_t'(2);                          // static cast: no check",
        '    $display("state_t\'(2) -> %0d name=\'%s\'", s, s.name());',
        '    if (!$cast(s, 2)) $display("$cast(s,2) failed, s still %0d", s);',
        '    $finish;',
        '  end',
        'endmodule',
    ], "Enum methods, ranges, and static versus dynamic casts to an enum.")
    out([
        "uninit s=00 name='IDLE'",
        's=0 IDLE next=BUSY prev=DONE',
        's=1 BUSY next=DONE prev=IDLE',
        's=3 DONE next=IDLE prev=BUSY',
        'num=3 last=DONE IDLE.next(2)=DONE',
        'R0=0 R2=1 R3=2 R4=3 REG0=4 REG1=5 REG2=6 ',
        "state_t'(2) -> 2 name=''",
        '$cast(s,2) failed, s still 2',
        '- t12_enum.sv:23: Verilog $finish',
    ], "Verilator 5.020.")
    p("Several details deserve attention. `next()` and `prev()` follow "
      "**declaration order**, not numerical order, and wrap around - after "
      "DONE comes IDLE even though value 2 is skipped. The static cast "
      "`state_t'(2)` compiles and stores 2, which is not a member, so "
      "`name()` returns an empty string: static casts to an enum are not "
      "checked. `$cast(s, 2)` checks at run time, returns 0 and leaves `s` "
      "unchanged. Finally, the first line shows a Verilator artefact: an "
      "uninitialized 2-bit 4-state enum is `2'bxx` in any 4-state simulator, "
      "whose `name()` is \"\", but Verilator starts it at 0 and reports IDLE.")
    box("key", "Strong typing rules for enums",
        ["An enum value is automatically converted to its base type in "
         "expressions (`s + 1` is an int). The reverse is not automatic: "
         "assigning an integer expression, a different enum type or even "
         "`s + 1` back to an enum variable is a compile error without a cast. "
         "Use `s.next()` for sequencing, `st_e'(expr)` when you know the "
         "value is legal, and `$cast` when it comes from outside (a register, "
         "a file, a random number). Some tools accept the illegal assignment "
         "with a warning - do not rely on it."])
    box("intuit", "What an enum is in hardware",
        ["Nothing more than its base type: an `enum logic [1:0]` is a 2-bit "
         "vector and synthesizes to 2 flops. The encoding is exactly the "
         "values you wrote, unless the synthesis tool's FSM extraction "
         "re-encodes the state register (one-hot, Gray) - Design Compiler and "
         "Genus do that only when told to; FPGA tools such as Vivado and "
         "Quartus do it by default for recognized FSMs. If the encoding must be fixed (a state visible "
         "on a debug bus or in a register), give explicit values and disable "
         "FSM re-encoding for that register."])

    # ------------------------------------------------------------------
    h2("typedef")
    p("`typedef` gives a name to any type. Its value is not saving keystrokes "
      "but making the type a single point of truth: change `addr_t` in one "
      "package and every port, register and function using it follows. "
      "Common conventions are `_t` for types, `_e` for enums and `_s` for "
      "structs (lowRISC), or `_t` for everything (PULP).")
    code(["typedef logic [31:0]           word_t;",
          "typedef logic [AW-1:0]         addr_t;       // AW from a package parameter",
          "typedef word_t                 regfile_t [32];",
          "typedef struct packed {logic v; addr_t a;} req_t;",
          "typedef struct req_fwd_s;                    // forward declaration",
          "typedef class  my_driver;                    // forward class declaration (Ch 18)",
          "typedef enum logic [1:0] {OKAY, EXOKAY, SLVERR, DECERR} resp_e;"],
         "Typical typedefs.")
    p("Typedefs obey normal scoping: a typedef in a module is local to that "
      "module and cannot be used in its port list unless the type comes from "
      "a package or from `$unit`. That is why real projects put every shared "
      "type in a package (Chapter 15).")

    # ------------------------------------------------------------------
    h2("Structures: packed and unpacked")
    p("A `struct` groups named members. The keyword `packed` makes the "
      "struct a single contiguous bit vector; without it, the struct is a "
      "collection of independent variables, like a C struct.")
    tbl(["Property", "struct packed", "struct (unpacked)"],
        [["Storage", "one vector; first member = most significant bits",
          "separate members; layout is tool-defined"],
         ["Member types", "only packed/integral types (logic, bit, int, enums, "
          "packed structs/unions, packed arrays)",
          "any type: real, string, class handles, unpacked arrays, queues"],
         ["Use as a vector", "yes: slicing, arithmetic, `==`, assign to/from vectors",
          "no; whole-struct copy and `==` only"],
         ["`signed` qualifier", "allowed (whole vector signed)", "not applicable"],
         ["Member default values", "not allowed", "allowed: `int n = 4;`"],
         ["Synthesis", "fully supported by all mainstream tools",
          "supported by most ASIC/FPGA tools for simple members; avoid for ports"],
         ["Typical use", "bus payloads, register maps, pipeline bundles",
          "testbench transactions, configuration records"]],
        widths=[20, 42, 38], bold_first=True)
    code([
        'module t12_struct;',
        '  typedef enum logic [1:0] {RD, WR, RMW} op_t;',
        '  typedef struct packed {          // first member = most significant bits',
        '    op_t         op;               // [15:14]',
        '    logic        err;              // [13]',
        '    logic [4:0]  id;               // [12:8]',
        '    logic [7:0]  data;             // [7:0]',
        '  } req_t;',
        '  typedef struct {                 // unpacked: members are separate variables',
        '    string       name;',
        '    int          addr;',
        '    logic [7:0]  mask [4];',
        '  } cfg_t;',
        '  typedef union packed {           // all members must have the same width',
        '    logic [15:0] raw;',
        '    req_t        req;',
        '    struct packed { logic [7:0] hi, lo; } b;',
        '  } word_u;',
        '',
        '  req_t  r;  cfg_t c;  word_u w;',
        '  initial begin',
        "    r = '{op: WR, id: 5'd3, data: 8'hA5, default: '0};",
        '    $display("r=%h $bits=%0d op=%s id=%0d r[15:14]=%b", r, $bits(r), r.op.name(),',
        '             r.id, r[15:14]);',
        "    r = 16'h8123;                  // a packed struct is also a plain vector",
        '    $display("r.op=%s r.err=%b r.id=%0d r.data=%h", r.op.name(), r.err, r.id, r.data);',
        '    c = \'{name: "uart0", addr: 32\'h4000_0000, mask: \'{default: 8\'hFF}};',
        '    $display("c.name=%s addr=%h mask[3]=%h", c.name, c.addr, c.mask[3]);',
        "    w.raw = 16'h4A5B;",
        '    $display("w.req.op=%s w.req.data=%h w.b.hi=%h", w.req.op.name(), w.req.data, w.b.hi);',
        '    $finish;',
        '  end',
        'endmodule',
    ], "Packed struct layout, unpacked struct, packed union and "
         "assignment patterns.")
    out([
        'r=43a5 $bits=16 op=WR id=3 r[15:14]=01',
        'r.op=RMW r.err=0 r.id=1 r.data=23',
        'c.name=uart0 addr=40000000 mask[3]=ff',
        'w.req.op=WR w.req.data=5b w.b.hi=4a',
        '- t12_struct.sv:31: Verilog $finish',
    ], "Verilator 5.020 (Icarus 12 does not support unpacked structs).")
    p("With `'{op: WR, id: 5'd3, data: 8'hA5, default: '0}` the packed "
      "struct is `01 0 00011 10100101` = 16'h43A5: `op` occupies bits "
      "[15:14] because it is declared first. Assigning `16'h8123` to the "
      "same struct and reading the members back decodes that vector: bits "
      "[15:14] = 2'b10 = RMW. The packed union `word_u` gives three views of "
      "the same 16 bits - raw, as a request, or as two bytes - which is how "
      "RTL overlays different formats onto one register or bus field.")

    h3("Assignment patterns")
    p("An **assignment pattern** `'{...}` builds a struct or array value from "
      "its elements. It is not a concatenation: each element is matched to a "
      "member or array element and converted to its type as if by assignment, "
      "so widths need not match exactly. Four forms exist and may be mixed "
      "(IEEE 1800 10.9):")
    tbl(["Form", "Example", "Meaning"],
        [["positional", "`'{2'b01, 1'b0, 5'd3, 8'hA5}`", "members in declaration order"],
         ["member label", "`'{op: WR, data: 8'hA5, ...}`", "by name, any order"],
         ["type key", "`'{logic: '0, int: -1}`", "every member of that type"],
         ["default", "`'{default: '0}`", "every remaining member (recursively)"],
         ["array index", "`'{0: 8'h1, 3: 8'hFF, default: 0}`", "for arrays"],
         ["replication", "`'{4{8'h00}}`", "for arrays: N copies"]],
        widths=[18, 42, 40])
    box("warn", "Pitfall: '{} versus {}",
        ["`{a, b}` is a **concatenation**: it produces a self-determined packed "
         "vector whose width is the sum of the operand widths, and unsized "
         "constants are not allowed in it. `'{a, b}` is an **assignment "
         "pattern** whose elements are assigned to members. For a packed "
         "struct both may work, but for an unpacked struct or unpacked array "
         "only the pattern is legal. Writing `'{default: 0}` versus `'0` also "
         "differs: `'0` fills a packed value with zeros; `'{default: 0}` works "
         "for unpacked types too."])

    # ------------------------------------------------------------------
    h2("Unions: packed, unpacked and tagged")
    p("A union stores several members in the same storage. A **packed "
      "union** requires every member to have the same width (IEEE 1800-2023 "
      "adds `union soft`, which relaxes this and right-justifies narrower "
      "members); writing one member and reading another is well defined "
      "because they are all views of the same bits. Packed unions are fully "
      "synthesizable and are the right tool for multi-format fields. An "
      "**unpacked union** may hold members of any type, but reading a member "
      "other than the one last written is undefined; it is rarely used and "
      "poorly supported by synthesis.")
    p("A **tagged union** stores a hidden tag recording which member is "
      "valid, and the language checks every read against the tag. Members "
      "can be `void`, giving a type-safe \"optional\" value:")
    code(["typedef union tagged {",
          "  void        Invalid;",
          "  logic [31:0] Valid;",
          "} maybe_word_t;",
          "",
          "maybe_word_t m;",
          "initial begin",
          "  m = tagged Valid 32'hCAFE;            // sets tag + value",
          "  case (m) matches                       // pattern matching on the tag",
          "    tagged Invalid:    $display(\"empty\");",
          "    tagged Valid .v:   $display(\"value %h\", v);",
          "  endcase",
          "  if (m matches tagged Valid .v &&& v > 0) $display(\"positive\");",
          "end"],
         "Tagged union and pattern matching (IEEE 1800 7.3.2, 12.6). Neither "
         "Icarus 12 nor Verilator 5.020 supports tagged unions; run on a "
         "commercial simulator. Expected output: \"value 0000cafe\" then \"positive\".")
    p("Tagged unions come from the Bluespec heritage of SystemVerilog and are "
      "almost never used in industrial RTL, because tool support is patchy; "
      "know that they exist for interviews and code reading.")

    # ------------------------------------------------------------------
    h2("The string type")
    p("A `string` variable holds a dynamically sized sequence of bytes. There "
      "is no terminating null character and no fixed length; assignment copies "
      "the value. Indexing `s[i]` returns a byte (0 if `i` is out of range). "
      "A string **literal** such as \"abc\" is not a string variable: it is a "
      "packed integral constant with 8 bits per character, which is why "
      "`logic [8*5:1] name = \"hello\";` is legal Verilog-2005.")
    tbl(["Method", "Effect"],
        [["`len()`", "number of characters"],
         ["`putc(i, c)` / `getc(i)`", "write / read the byte at index i"],
         ["`toupper()` / `tolower()`", "return a converted copy"],
         ["`compare(s)` / `icompare(s)`",
          "like C strcmp (negative, 0, positive); icompare ignores case"],
         ["`substr(i, j)`", "characters i..j inclusive (\"\" if out of range)"],
         ["`atoi()` `atohex()` `atooct()` `atobin()` `atoreal()`",
          "parse a number from the start of the string; stop at the first bad character"],
         ["`itoa(i)` `hextoa(i)` `octtoa(i)` `bintoa(i)` `realtoa(r)`",
          "set the string to the text form of a number"],
         ["operators", "`==`, `!=`, `<`, `>` (lexical), `{a, b}` concatenation, "
          "`{N{s}}` replication"]],
        widths=[42, 58])
    code([
        'module t12_str;',
        '  string s, t;',
        '  int    n;',
        '  initial begin',
        '    s = "uart";',
        '    t = {s, "_", $sformatf("%0d", 3)};          // concatenation builds a new string',
        '    $display("t=%s len=%0d t[0]=%s upper=%s", t, t.len(), t[0], t.toupper());',
        '    $display("substr(0,3)=%s compare=%0d icompare=%0d", t.substr(0, 3),',
        '             s.compare("uarT"), s.icompare("UART"));',
        '    s = "0x1F"; n = s.substr(2, 3).atohex();',
        '    t = "42abc";',
        '    $display("atohex=%0d atoi=%0d", n, t.atoi());',
        '    s.itoa(-17);  t = {4{"ab"}};',
        '    $display("itoa=%s replicate=%s ==: %0d", s, t, t == "abababab");',
        '    s = "";  $display("empty len=%0d", s.len());',
        '    $finish;',
        '  end',
        'endmodule',
    ], "String methods.")
    out([
        't=uart_3 len=6 t[0]=u upper=UART_3',
        'substr(0,3)=uart compare=32 icompare=0',
        'atohex=31 atoi=42',
        'itoa=-17 replicate=abababab ==: 1',
        'empty len=0',
        '- t12_str.sv:16: Verilog $finish',
    ], "Verilator 5.020.")
    p("Note that `compare(\"uarT\")` returns 32, the difference between 't' "
      "and 'T': only the sign of the result is specified. `$sformatf` is the "
      "workhorse for building messages and is how UVM builds every report. "
      "Strings are not synthesizable as signals, but `parameter string` is "
      "accepted by most synthesis tools for names and modes (for example a "
      "Xilinx primitive's `SIM_DEVICE` parameter).")

    # ------------------------------------------------------------------
    h2("void, chandle and event")
    bul(["**void** - the absence of a value: the return type of a function "
         "with no result (`function void f();`, Chapter 14), a member of a "
         "tagged union, and the cast `void'(f())` that discards a result.",
         "**chandle** - an opaque pointer-sized handle that can hold a C "
         "pointer passed through DPI (Chapter 24). It can only be compared, "
         "tested against `null`, assigned and passed back to C.",
         "**event** - a synchronization object; `->e` triggers it and `@e` "
         "or `wait(e.triggered)` waits for it. In SystemVerilog an event "
         "variable is a handle, so events can be assigned, passed to tasks "
         "and compared (Chapter 20)."])

    # ------------------------------------------------------------------
    h2("Casting")
    p("SystemVerilog has two kinds of cast. A **static cast** `T'(expr)` is "
      "resolved at compile time and never fails; it converts the value as if "
      "it were assigned to a variable of the target type. A **dynamic cast** "
      "`$cast(dest, src)` is checked at run time: it is needed for enums and "
      "for class handles (downcasting, Chapter 18).")
    tbl(["Form", "Meaning", "Example"],
        [["`type'(e)`", "convert to a type", "`int'(r)`, `state_e'(v)`, `addr_t'(x)`"],
         ["`N'(e)`", "change width to N bits (truncate or extend by the "
          "signedness of `e`)", "`12'(a)`, `$bits(t)'(0)`"],
         ["`signed'(e)` / `unsigned'(e)`", "change signedness, same bits", "`signed'(a)`"],
         ["`const'(e)`", "treat as constant (for const ref arguments)", "rare"],
         ["`$cast(d, s)` as function", "returns 1 on success, 0 on failure; d unchanged "
          "on failure", "`if (!$cast(st, v)) ...`"],
         ["`$cast(d, s);` as task", "run-time error on failure", "`$cast(h_ext, h_base);`"]],
        widths=[26, 44, 30])
    code([
        'module t12_cast;',
        '  typedef enum logic [1:0] {IDLE, RUN, STOP} st_t;',
        '  typedef logic [11:0] u12_t;',
        "  logic [7:0]  a = 8'hF0;",
        "  logic [3:0]  n = 4'hC;",
        '  int          i;',
        '  st_t         st;',
        '  initial begin',
        '    $display("size\'   : 12\'(a)=%h  4\'(a)=%h", 12\'(a), 4\'(a));',
        '    $display("signed\' : %0d  unsigned\': %0d", signed\'(a), unsigned\'(signed\'(n)));',
        '    $display("sext    : %h", u12_t\'(signed\'(n)));            // sign-extend 4 -> 12',
        '    $display("type\'   : int\'(3.7)=%0d int\'(-3.5)=%0d", int\'(3.7), int\'(-3.5));',
        '    $display("width   : $bits(a+n)=%0d $bits(9\'(a+n))=%0d", $bits(a + n), $bits(9\'(a + n)));',
        "    i = 2;  st = st_t'(i);                                    // compile-time, unchecked",
        '    $display("static  : st=%s", st.name());',
        '    i = 3;',
        '    if ($cast(st, i)) $display("$cast ok: %s", st.name());',
        '    else              $display("$cast(st, 3) failed");',
        '    $finish;',
        '  end',
        'endmodule',
    ], "Static size, sign and type casts, and $cast.")
    out([
        "size'   : 12'(a)=0f0  4'(a)=0",
        "signed' : -16  unsigned': 12",
        'sext    : ffc',
        "type'   : int'(3.7)=4 int'(-3.5)=-4",
        "width   : $bits(a+n)=8 $bits(9'(a+n))=9",
        'static  : st=STOP',
        '$cast(st, 3) failed',
        '- t12_cast.sv:19: Verilog $finish',
    ], "Verilator 5.020 (Icarus 12 does not implement $cast).")
    p("`12'(a)` zero-extends because `a` is unsigned, while "
      "`u12_t'(signed'(n))` sign-extends 4'hC to 12'hFFC because the operand "
      "of the outer cast is signed - the extension follows the **source** "
      "signedness, exactly like an assignment. `int'(3.7)` is 4: real to "
      "integer conversion **rounds** to nearest, with ties away from zero "
      "(-3.5 becomes -4); it does not truncate like C. `$bits(a + n)` is 8, "
      "the self-determined width of the addition; a size cast `9'(a + n)` is "
      "the idiomatic way to keep the carry of an addition inside a larger "
      "expression. Verilator's width warnings about these lines are exactly "
      "the lint checks you want on in an RTL flow.")
    box("tip", "Casting in RTL",
        ["Size casts replace the old trick of padding with concatenations: "
         "`sum = 9'(a) + 9'(b);` keeps the carry and documents the intent. "
         "Width casts to a parameter-dependent size are legal as long as the "
         "size is a constant expression: `AW'(base + ofs)`. Keep `$cast` in "
         "testbench code; synthesis tools do not support it."])

    h2("Summary")
    bul(["`logic` is a 4-state data type; `reg` is a synonym. Nets (`wire`) "
         "resolve multiple drivers; variables allow procedural writers or one "
         "continuous driver. Use `logic` everywhere except true multi-driver nets.",
         "2-state types (`bit`, `byte`, `shortint`, `int`, `longint`) are fast "
         "and match C types, but convert x/z to 0 and can hide missing resets; "
         "keep RTL 4-state.",
         "`byte`, `shortint`, `int`, `longint` and `integer` are signed by "
         "default; `bit`, `logic` and `reg` are unsigned.",
         "Enums carry a base type and explicit or implicit values, provide "
         "first/last/next/prev/num/name, and are strongly typed: integer to "
         "enum requires a cast; `$cast` checks membership.",
         "Packed structs and unions are vectors with named fields - the "
         "backbone of SoC bus payloads; unpacked structs hold arbitrary types "
         "for testbenches. Assignment patterns `'{...}` build them.",
         "`string` is a dynamic byte sequence with rich methods; string "
         "literals are packed constants.",
         "Static casts (`T'()`, `N'()`, `signed'()`) never fail; real-to-int "
         "rounds; `$cast` performs run-time checked conversion."])
    h2("Exercises")
    bul(["Declare a packed struct for a 32-bit RISC-V I-type instruction "
         "(imm[11:0], rs1, funct3, rd, opcode) so that assigning the "
         "instruction word to it decodes all fields. Verify with a test of "
         "`addi x1, x0, 5` (32'h00500093).",
         "Write an enum for the AXI response codes with explicit values and a "
         "function that converts a raw 2-bit value to the enum using `$cast`, "
         "returning SLVERR for anything illegal. Why is the static cast not "
         "enough if the base type is `logic [2:0]`?",
         "Predict and then check the output of: `int i = -1; bit [31:0] u = 1; "
         "$display(i < u, int'(i) < int'(u));`.",
         "An FSM register is declared `bit [2:0] state;` and its reset branch "
         "is accidentally deleted. What does RTL simulation show, what does "
         "gate-level simulation show, and which lint rule catches it?",
         "Use string methods to parse the plusarg string \"addr=0x40001000\" "
         "into an `int unsigned` (hint: `substr` and `atohex`).",
         "Explain the difference between `'{default: 0}`, `'0` and `{0}` "
         "when assigned to (a) a packed struct and (b) an unpacked array."],
        ordered=True)


# =============================================================================
#     Chapter 13 - Arrays
# =============================================================================
def ch13():
    chapter("Arrays: Packed, Unpacked, Dynamic, Associative, Queues and "
            "Array Methods")
    p("Verilog-2005 had one kind of array: a fixed-size collection of "
      "elements indexed by integers, used for memories and register files. "
      "SystemVerilog keeps it, generalizes packed (vector) dimensions to any "
      "number of levels, and adds three **dynamic** collections - dynamic "
      "arrays, associative arrays and queues - plus a library of built-in "
      "methods for searching, sorting and reducing arrays. The fixed-size "
      "forms are the RTL designer's tools; the dynamic forms are the "
      "verification engineer's, and they are what makes scoreboards, "
      "reference models and sparse memory models a few lines long instead of "
      "a few hundred.")
    tbl(["Kind", "Declaration", "Size", "Index", "Synthesizable"],
        [["packed array", "`logic [3:0][7:0] w;`", "fixed", "integer", "yes"],
         ["fixed unpacked", "`logic [7:0] m [256];`", "fixed", "integer", "yes (memories, regfiles)"],
         ["dynamic", "`int d[];`", "set at run time with `new[]`", "integer from 0", "no"],
         ["associative", "`int aa[string];`", "grows per written key", "any key type", "no"],
         ["queue", "`int q[$];` / `int q[$:15];`", "grows/shrinks at both ends",
          "integer from 0; `$` = last", "no (bounded queues: a few tools, avoid)"]],
        widths=[16, 26, 22, 18, 18], bold_first=True)

    # ------------------------------------------------------------------
    h2("Packed versus unpacked dimensions")
    p("Dimensions written **before** the identifier are **packed**; those "
      "written **after** it are **unpacked**. A packed array is a single "
      "contiguous vector: it can be used anywhere an integral value can - "
      "arithmetic, comparison, assignment to a vector of another shape - and "
      "only single-bit types (`logic`, `bit`, `reg`), other packed arrays, "
      "packed structs and enums can be its elements. An unpacked array is a "
      "collection of separate elements of any type; the whole array can only "
      "be copied, compared for equality, or passed to a task or function.")
    diagram([
        "  logic  [3:0][7:0]   mem   [0:1][0:2];",
        "         \\________/          \\________/",
        "          packed               unpacked",
        "          dims 3,4             dims 1,2",
        "",
        "  Index order in an expression:   mem [u1][u2] [p3][p4]",
        "                                        |   |    |   |",
        "                          dimension:    1   2    3   4",
        "  Unpacked dimensions first (left to right), then packed (left to right).",
        "  The RIGHTMOST packed dimension varies fastest: mem[i][j][p3] is a byte,",
        "  mem[i][j][p3][p4] is a bit, and mem[i][j] is one 32-bit word.",
    ], "Dimension numbering and index order of a mixed array.")
    p("Each dimension is written either as a range `[msb:lsb]` or, for "
      "unpacked dimensions only, as a C-style size `[N]` meaning `[0:N-1]`. "
      "The query functions `$dimensions`, `$unpacked_dimensions`, `$size`, "
      "`$left`, `$right`, `$low`, `$high` and `$increment` take a dimension "
      "number counted as in the figure, and `$bits` returns the total number "
      "of bits.")
    code([
        'module t13_fixed;',
        '  //        packed dims        unpacked dims',
        '  logic [3:0][7:0] mem  [0:1][0:2];   // 2x3 array of 32-bit words made of 4 bytes',
        '  logic [3:0][7:0] w;',
        '  logic [7:0]      a [4], b [4];      // C-style size [4] == [0:3]',
        '  initial begin',
        '    $display("$dimensions=%0d $unpacked_dimensions=%0d $bits(mem)=%0d",',
        '             $dimensions(mem), $unpacked_dimensions(mem), $bits(mem));',
        '    $display("$size(mem,1)=%0d $size(mem,2)=%0d $size(mem,3)=%0d $size(mem,4)=%0d",',
        '             $size(mem, 1), $size(mem, 2), $size(mem, 3), $size(mem, 4));',
        "    w = 32'hDDCC_BBAA;",
        '    mem[1][2] = w;                       // unpacked indices first, then packed',
        '    $display("mem[1][2][3]=%h  mem[1][2][0][3:0]=%h  w[2:1]=%h", mem[1][2][3],',
        '             mem[1][2][0][3:0], w[2:1]);  // w[2:1] is a 2-byte packed slice',
        "    a = '{8'h10, 8'h20, 8'h30, 8'h40};",
        '    b = a;                               // whole-array copy (same shape)',
        '    $display("a==b: %0d", a == b);',
        "    b[1:2] = '{8'hEE, 8'hFF};            // unpacked slice assignment",
        '    $display("a==b: %0d  b=%p", a == b, b);',
        '    $finish;',
        '  end',
        'endmodule',
    ], "Mixed packed/unpacked array, slicing, whole-array "
         "assignment and comparison.")
    out([
        '$dimensions=4 $unpacked_dimensions=2 $bits(mem)=192',
        '$size(mem,1)=2 $size(mem,2)=3 $size(mem,3)=4 $size(mem,4)=8',
        'mem[1][2][3]=dd  mem[1][2][0][3:0]=a  w[2:1]=ccbb',
        'a==b: 1',
        "a==b: 0  b='{'h10, 'hee, 'hff, 'h40} ",
        '- t13_fixed.sv:20: Verilog $finish',
    ], "Verilator 5.020. Icarus 12 reports \"sorry: Assignment to an "
        "entire array or to an array slice is not yet supported\".")
    p("`mem[1][2][3]` selects unpacked element [1][2] (a 32-bit word) and then "
      "its packed byte 3, `8'hDD`. A **slice** selects a contiguous range of "
      "one dimension: `w[2:1]` is the two middle bytes of the packed word "
      "(16'hCCBB); `b[1:2]` is a two-element unpacked slice that can be "
      "assigned from another two-element unpacked array or pattern. Whole "
      "unpacked arrays of the same shape can be assigned and compared with "
      "`==`/`!=`; the element types must be equivalent and the number of "
      "elements in each dimension equal (the ranges need not be identical: "
      "`[0:3]` and `[4:1]` match element by element from the left).")
    box("key", "When to pack, when to unpack",
        ["Pack a dimension when the elements form one value that is moved, "
         "compared or operated on as a whole: bytes of a data word, lanes of a "
         "SIMD vector, fields of a bus. Unpack a dimension when elements are "
         "addressed individually by an index that changes at run time: memory "
         "words, register-file entries, per-channel state. Synthesis maps "
         "unpacked arrays that are read with a variable index to RAM or to a "
         "flop array plus a read mux, and packed arrays to plain wires. "
         "Simulators also store them differently: a large packed vector is "
         "slow to update bit by bit."])
    box("warn", "Pitfall: memories and reset",
        ["A `logic [31:0] mem [1024]` written in an `always_ff` with a reset "
         "branch that clears every word cannot be mapped to SRAM - RAM "
         "macros have no reset. Synthesis then builds 32768 flops. Reset only "
         "the valid bits or pointers, never the storage, and keep RAM "
         "inference templates (single write port, registered or "
         "unregistered read) exactly as the target library expects "
         "(companion RTL Design guide, memories chapter)."])

    # ------------------------------------------------------------------
    h2("Dynamic arrays")
    p("A dynamic array is an unpacked array whose single (rightmost "
      "unpacked) dimension is sized at run time. It starts empty. `new[N]` "
      "allocates N default-valued elements; `new[N](src)` allocates N "
      "elements and copies as many as fit from `src` - the idiom for "
      "resizing while keeping contents. Assignment from another array or "
      "pattern resizes automatically; `size()` returns the length and "
      "`delete()` empties it.")
    code([
        'module t13_dyn;',
        '  int d[], e[];',
        '  initial begin',
        '    $display("empty: size=%0d", d.size());',
        '    d = new[4];                        // 4 elements, default value 0',
        '    foreach (d[i]) d[i] = i * 10;',
        '    e = new[6](d);                     // resize-and-copy: old 4 kept, 2 new = 0',
        '    $display("d=%p e=%p", d, e);',
        '    d = new[2](d);                     // shrink: keeps d[0:1]',
        '    e = d;                             // assignment copies elements (not a handle)',
        '    e[0] = 99;',
        '    $display("d=%p e=%p size=%0d", d, e, e.size());',
        "    d = '{1, 2, 3};                    // assignment pattern resizes automatically",
        '    d.delete();',
        '    $display("after delete: size=%0d", d.size());',
        '    $finish;',
        '  end',
        'endmodule',
    ], "Dynamic array allocation, copy-resize, value semantics and delete.")
    out([
        'empty: size=0',
        "d='{'h0, 'ha, 'h14, 'h1e}  e='{'h0, 'ha, 'h14, 'h1e, 'h0, 'h0} ",
        "d='{'h0, 'ha}  e='{'h63, 'ha}  size=2",
        'after delete: size=0',
        '- t13_dyn.sv:16: Verilog $finish',
    ], "Verilator 5.020 (%p prints elements in hex; the format of %p "
        "is tool-specific).")
    p("Notice `e = d; e[0] = 99;` did not change `d`: array assignment copies "
      "elements. Arrays are values, not references - only class objects "
      "(Chapter 18) are handled by reference. Dynamic arrays are the natural "
      "container for a packet payload whose length is only known after "
      "randomization, and for the `data[]` field of a bus transaction class.")

    # ------------------------------------------------------------------
    h2("Associative arrays")
    p("An associative array stores only the elements that have been written, "
      "indexed by a key of any type: `int aa[string]`, "
      "`logic [31:0] mem [bit [63:0]]`, `txn_c by_id [int]`, or even "
      "class-handle keys. It behaves as an ordered map: iteration always "
      "visits keys in ascending order, as the standard requires. The classic "
      "use is a **sparse memory model** - a 64-bit address space where only "
      "the touched words cost memory - and a scoreboard keyed by transaction "
      "ID.")
    tbl(["Method", "Effect"],
        [["`num()` / `size()`", "number of entries"],
         ["`exists(k)`", "1 if key k has an entry"],
         ["`delete()` / `delete(k)`", "remove all entries / the entry k"],
         ["`first(k)` / `last(k)`", "set k to the smallest / largest key; return 0 if empty"],
         ["`next(k)` / `prev(k)`", "set k to the next larger / smaller key; return 0 at the end"]],
        widths=[30, 70])
    code([
        'module t13_assoc;',
        '  logic [31:0] mem [bit [31:0]];      // sparse memory: index type bit[31:0]',
        '  int          cnt [string];          // string-indexed',
        '  bit   [31:0] k;',
        '  string       s;',
        '  initial begin',
        "    mem[32'h0000_0010] = 32'hAAAA;  mem[32'h8000_0000] = 32'hBBBB;",
        "    mem[32'h0000_0004] = 32'hCCCC;",
        '    $display("num=%0d exists(4)=%0d exists(8)=%0d", mem.num(), mem.exists(4), mem.exists(8));',
        '    if (mem.first(k)) do $display("  mem[%h] = %h", k, mem[k]); while (mem.next(k));',
        "    mem.delete(32'h10);",
        '    $display("after delete(10h): num=%0d  %p", mem.num(), mem);',
        '    cnt["apb"]++;  cnt["axi"] += 3;  cnt["apb"]++;',
        '    foreach (cnt[name]) $display("  cnt[%s] = %0d", name, cnt[name]);',
        '    if (cnt.last(s)) $display("last key = %s", s);',
        '    $finish;',
        '  end',
        'endmodule',
    ], "A sparse memory and a string-keyed counter.")
    out([
        'num=3 exists(4)=1 exists(8)=0',
        '  mem[00000004] = 0000cccc',
        '  mem[00000010] = 0000aaaa',
        '  mem[80000000] = 0000bbbb',
        "after delete(10h): num=2  '{'h4:'hcccc, 'h80000000:'hbbbb} ",
        '  cnt[apb] = 2',
        '  cnt[axi] = 3',
        'last key = axi',
        '- t13_assoc.sv:16: Verilog $finish',
    ], "Verilator 5.020.")
    p("Iteration with `first`/`next` or `foreach` visits keys in ascending "
      "order (numerical for integral keys, lexicographical for strings). "
      "`cnt[\"apb\"]++` on a missing key works because reading a missing "
      "entry returns the default value of the element type and the write "
      "then creates it. The index type matters: with `[int]` keys negative "
      "numbers sort before positive ones; with a `string` key, "
      "\"10\" sorts before \"9\".")
    p("The **wildcard index** `int aa[*]` accepts any integral key and is a "
      "Verilog-era relic kept for compatibility: the key type is not known, "
      "so `foreach` and the iteration methods cannot declare the loop "
      "variable safely, and string keys are not allowed. Prefer an explicit "
      "key type in new code.")
    box("warn", "Pitfall: reading a missing key",
        ["IEEE 1800 (7.8.6) says that reading a nonexistent entry returns the "
         "default value of the element type (x for 4-state, 0 for 2-state), "
         "may issue a warning, and does **not** create the entry. Tools "
         "differ in practice. Verilator 5.020 creates it:"])
    code([
        'module t13_x;',
        "  byte by[] = '{100, 100, 100};",
        '  int  s1, s2, s3;',
        '  logic [31:0] mem [bit [31:0]];',
        '  logic [31:0] v;',
        '  initial begin',
        '    s1 = by.sum();',
        "    s2 = by.sum() with (int'(item));",
        "    s3 = by.sum(x) with (32'(x));",
        '    $display("s1=%0d s2=%0d s3=%0d", s1, s2, s3);',
        '    mem[4] = 1;',
        '    $display("num=%0d", mem.num());',
        '    v = mem[8];',
        '    $display("num=%0d exists(8)=%0d v=%h", mem.num(), mem.exists(8), v);',
        '    $finish;',
        '  end',
        'endmodule',
    ], "Two tool-dependent corners: the width of a byte-array sum and "
         "a read of a missing associative-array key.")
    out([
        's1=44 s2=44 s3=44',
        'num=1',
        'num=2 exists(8)=1 v=00000000',
    ], "Verilator 5.020. The first line belongs to the sum() "
        "pitfall later in this chapter; for the last line a compliant "
        "simulator prints num=1 exists(8)=0.")
    p("Portable code always tests `exists()` before reading: "
      "`v = mem.exists(a) ? mem[a] : '0;`. The same rule makes a memory "
      "model return a predictable value for uninitialized addresses instead "
      "of relying on the tool.")

    # ------------------------------------------------------------------
    h2("Queues")
    p("A queue `T q[$]` is an ordered, variable-length collection with "
      "constant-time insertion and removal at both ends - a deque. It is "
      "indexed like an array, with `0` the first element and `$` the last. "
      "A **bounded** queue `T q[$:N]` holds at most N+1 elements; writes that "
      "would exceed the bound are ignored (with a warning in most tools).")
    tbl(["Operation", "Method form", "Operator form"],
        [["append", "`q.push_back(x)`", "`q = {q, x};`"],
         ["prepend", "`q.push_front(x)`", "`q = {x, q};`"],
         ["remove first / last", "`x = q.pop_front()` / `q.pop_back()`",
          "`x = q[0]; q = q[1:$];`"],
         ["insert at i", "`q.insert(i, x)`", "`q = {q[0:i-1], x, q[i:$]};`"],
         ["delete element i / all", "`q.delete(i)` / `q.delete()`", "`q = {};`"],
         ["length", "`q.size()`", "`$size(q)`"]],
        widths=[22, 40, 38])
    code([
        'module t13_queue;',
        "  int q[$] = '{2, 4, 6};",
        '  int b[$:3];                          // bounded queue: at most 4 elements',
        '  int x;',
        '  initial begin',
        '    q.push_front(0);  q.push_back(8);  q.insert(2, 3);',
        '    $display("q=%p size=%0d q[$]=%0d", q, q.size(), q[$]);',
        '    x = q.pop_front();  $display("pop_front=%0d q=%p", x, q);',
        '    x = q.pop_back();   $display("pop_back=%0d  q=%p", x, q);',
        '    $display("q[1:$]=%p  q[0:1]=%p", q[1:$], q[0:1]);',
        '    q = {q, 10};        q = {-1, q};  // concatenation also works',
        '    q.delete(1);  $display("q=%p", q);',
        '    for (int i = 0; i < 6; i++) b.push_back(i);',
        '    $write("bounded b size=%0d:", b.size());  foreach (b[i]) $write(" %0d", b[i]);',
        '    $display("");',
        '    q = {};  $display("empty size=%0d", q.size());',
        '    $finish;',
        '  end',
        'endmodule',
    ], "Queue operations, slices and a bounded queue.")
    out([
        "q='{'h0, 'h2, 'h3, 'h4, 'h6, 'h8}  size=6 q[$]=8",
        "pop_front=0 q='{'h2, 'h3, 'h4, 'h6, 'h8} ",
        "pop_back=8  q='{'h2, 'h3, 'h4, 'h6} ",
        "q[1:$]='{'h3, 'h4, 'h6}   q[0:1]='{'h2, 'h3} ",
        "q='{'hffffffff, 'h3, 'h4, 'h6, 'ha} ",
        'bounded b size=4: 0 1 2 3',
        'empty size=0',
        '- t13_queue.sv:17: Verilog $finish',
    ], "Verilator 5.020 (-1 prints as 'hffffffff in %p).")
    p("Queue slices `q[a:b]` return a new queue; indices out of range are "
      "clipped, and `q[a:b]` with a > b is empty. Popping an empty queue "
      "returns the default value and may issue a warning - always check "
      "`size()` first. Queues are the standard container for expected-"
      "transaction lists in scoreboards (push the prediction, pop and "
      "compare when the DUT produces output) and for the `mailbox`-free "
      "communication inside one component.")
    box("expert", "Interview insight: queue versus dynamic array versus associative array",
        ["**Queue**: in-order streams, FIFO/LIFO models, scoreboards of "
         "in-order protocols. **Dynamic array**: a payload or table whose size "
         "is chosen once and then indexed randomly; cheapest element access. "
         "**Associative array**: sparse or keyed data - memory models, "
         "out-of-order scoreboards keyed by AXI ID, coverage of seen values. "
         "A classic question is how to model an out-of-order AXI scoreboard: "
         "an associative array keyed by ID whose elements are queues, "
         "`txn_c by_id [int][$]`, an associative array of queues."])

    # ------------------------------------------------------------------
    h2("Array manipulation methods")
    p("IEEE 1800 (7.12) defines built-in methods on every unpacked array "
      "(fixed, dynamic, queue and, for most, associative). Many take an "
      "optional **with clause**: an expression evaluated for each element, "
      "in which the element is called `item` by default or the name given in "
      "parentheses (`find(x) with (x > 5)`); `item.index` gives its index.")
    tbl(["Group", "Methods", "Result"],
        [["Locator", "`find`, `find_index`, `find_first`, `find_first_index`, "
          "`find_last`, `find_last_index` (with clause required)",
          "a queue of elements or of indices (empty if nothing matches)"],
         ["Locator", "`min`, `max`, `unique`, `unique_index` (with clause optional)",
          "a queue (min/max: one element, or empty for an empty array)"],
         ["Ordering", "`sort`, `rsort` (with clause optional), `reverse`, `shuffle`",
          "reorders in place; not for associative arrays"],
         ["Reduction", "`sum`, `product`, `and`, `or`, `xor` (with clause optional)",
          "a single value"]],
        widths=[14, 50, 36], bold_first=True)
    code([
        'module t13_meth;',
        "  int  a[] = '{7, 3, 9, 3, 1, 12};",
        '  int  r[$];',
        "  byte by[] = '{100, 100, 100};",
        '  typedef struct { string n; int lat; } ip_t;',
        '  ip_t ips[] = \'{\'{"dma", 12}, \'{"uart", 3}, \'{"ddr", 40}};',
        '  ip_t ir[$];',
        '  int  acc;',
        '  initial begin',
        '    r = a.find(x) with (x > 5);           $display("find >5        %p", r);',
        '    r = a.find_index with (item == 3);    $display("find_index ==3 %p", r);',
        '    r = a.find_first with (item < 5);     $display("find_first <5  %p", r);',
        '    r = a.min();  $display("min %p", r);  r = a.max();  $display("max %p", r);',
        '    r = a.unique();                       $display("unique         %p", r);',
        '    $display("sum=%0d product=%0d xor=%0d  sum(x>5)=%0d", a.sum(), a.product(),',
        "             a.xor(), a.sum() with (int'(item > 5)));",
        '    $display("byte sum=%0d  sum with int\'=%0d", by.sum(), by.sum() with (int\'(item)));',
        '    acc = 0;  foreach (by[i]) acc += by[i];   // portable: accumulate in an int',
        '    $display("foreach accumulate=%0d", acc);',
        '    a.sort();    $display("sort    %p", a);',
        '    a.rsort();   $display("rsort   %p", a);',
        '    a.reverse(); $display("reverse %p", a);',
        '    ips.sort(x) with (x.lat);',
        '    foreach (ips[i]) $write("%s:%0d ", ips[i].n, ips[i].lat);',
        '    ir = ips.find(x) with (x.lat > 10);   $display("\\nslow IPs: %0d", ir.size());',
        '    $finish;',
        '  end',
        'endmodule',
    ], "Locator, reduction and ordering methods, including sort by a "
         "struct member.")
    out([
        "find >5        '{'h7, 'h9, 'hc} ",
        "find_index ==3 '{'h1, 'h3} ",
        "find_first <5  '{'h3} ",
        "min '{'h1} ",
        "max '{'hc} ",
        "unique         '{'h7, 'h3, 'h9, 'h1, 'hc} ",
        'sum=35 product=6804 xor=3  sum(x>5)=3',
        "byte sum=44  sum with int'=44",
        'foreach accumulate=300',
        "sort    '{'h1, 'h3, 'h3, 'h7, 'h9, 'hc} ",
        "rsort   '{'hc, 'h9, 'h7, 'h3, 'h3, 'h1} ",
        "reverse '{'h1, 'h3, 'h3, 'h7, 'h9, 'hc} ",
        'uart:3 dma:12 ddr:40 ',
        'slow IPs: 2',
        '- t13_meth.sv:26: Verilog $finish',
    ], "Verilator 5.020.")
    p("Locator methods always return a **queue**, even `min()` and "
      "`find_first` - assign them to a queue, not to a scalar. `unique()` "
      "keeps the first occurrence of each value in original order. "
      "`sort(x) with (x.lat)` sorts an array of structs by a key expression "
      "- the standard way to order transactions by time stamp or priority. "
      "The reductions return the array's element type, and that is the "
      "trap explained next.")
    box("warn", "Pitfall: the width of sum() and product()",
        ["A reduction method returns a value of the **element type** unless a "
         "`with` clause is given, in which case the result has the type of the "
         "`with` expression (IEEE 1800 7.12.3). Summing three `byte` values of "
         "100 overflows the 8-bit signed result: 300 mod 256 = 44. The "
         "standard fix is `by.sum() with (int'(item))`, which a compliant "
         "simulator evaluates in 32 bits and returns 300. As the output above "
         "shows, Verilator 5.020 still returns 44 for the `with` form "
         "(first line of the t13_x output, where the result was even "
         "assigned to an `int`). The only fully portable form is an explicit "
         "loop into a wide accumulator, as the foreach line does. The same "
         "trap applies to `bit` arrays: `flags.sum()` over `bit flags[16]` "
         "is 1 bit wide, so counting set flags needs `flags.sum() with "
         "(int'(item))`."])

    # ------------------------------------------------------------------
    h2("Arrays in RTL: what synthesizes")
    tbl(["Construct", "Synthesis", "Notes"],
        [["Multi-dimensional packed arrays", "yes, all tools", "pure wiring"],
         ["Fixed unpacked arrays", "yes", "RAM or flop inference depending on coding"],
         ["Unpacked arrays as ports", "yes in DC/Genus/Vivado/Quartus; "
          "Yosys 0.33 rejects them", "prefer packed arrays or structs for ports"],
         ["Whole-array assignment / `==`", "yes (DC, Genus, Vivado)",
          "unrolled into per-element logic"],
         ["Array assignment patterns `'{...}`", "yes in commercial tools",
          "Yosys 0.33 rejects them (Chapter 17)"],
         ["`foreach` over a fixed array", "yes", "unrolled like a for loop"],
         ["Dynamic arrays, queues, associative arrays", "no",
          "testbench only"],
         ["Array methods (`sum`, `find`, ...)", "generally no",
          "some tools accept reductions on fixed arrays; write loops in RTL"]],
        widths=[32, 30, 38], bold_first=True)
    box("tip", "RTL idiom: the reduction you actually want",
        ["In RTL write reductions over fixed arrays as a loop in an "
         "`always_comb`, with an explicitly sized accumulator: "
         "`cnt = '0; foreach (req[i]) cnt += CW'(req[i]);`. Synthesis turns "
         "it into an adder tree and the width is under your control. For "
         "packed vectors the unary reduction operators (`&v`, `|v`, `^v`) "
         "remain the simplest form."])

    h2("Summary")
    bul(["Packed dimensions (before the name) form one vector; unpacked "
         "dimensions (after the name) form a collection. Index order: "
         "unpacked left to right, then packed left to right.",
         "Fixed unpacked arrays support slices, whole-array copy and "
         "equality; they are the RTL memory and register-file construct.",
         "Dynamic arrays (`new[N]`, `new[N](old)`), associative arrays "
         "(`exists`, `first`/`next`, `delete`) and queues (`push`/`pop`, "
         "`insert`, `[a:$]` slices, bounded `[$:N]`) are testbench "
         "containers with value semantics.",
         "Locator methods return queues; ordering methods work in place; "
         "reductions return the element type unless a `with` clause changes "
         "it - beware 8-bit sums.",
         "Tools differ at the edges (missing associative keys, `with` "
         "result width, `%p` format): write code whose result does not "
         "depend on them."])
    h2("Exercises")
    bul(["For `logic [1:0][3:0] x [2][3];` give `$bits(x)`, "
         "`$dimensions(x)`, `$size(x, 3)` and the width of `x[1][2][0]`. "
         "Check your answers in Verilator.",
         "Write a sparse 64-bit-address memory model class with `write`, "
         "`read` (returning 32'hDEAD_BEEF for never-written words, without "
         "creating entries) and `dump` (ascending address order).",
         "Build an out-of-order scoreboard: expected transactions go into "
         "`exp_q [int][$]` keyed by ID; actual ones are matched against "
         "`exp_q[id].pop_front()`. Report leftovers at the end of the test.",
         "Given `int lat[] = '{12, 40, 3, 40, 7};` use array methods only "
         "to compute: the index of every maximum, the number of values "
         "above 10, and the average as a real.",
         "Show that `bit flags[16]` summed with `flags.sum()` gives a wrong "
         "count, then fix it two ways. Which fix works in Verilator 5.020?",
         "Write synthesizable RTL for a 32-entry population count of "
         "`logic [31:0] v` using `foreach` and a 6-bit accumulator; "
         "synthesize it with Yosys and report the cell count."],
        ordered=True)


# =============================================================================
#     Chapter 14 - Procedural enhancements
# =============================================================================
def ch14():
    chapter("Procedural Enhancements: always_comb/ff/latch, unique/priority, "
            "New Operators, Loops, inside, Streaming and Argument Passing")
    p("Verilog's procedural language has one general-purpose `always` block, "
      "a C-like but incomplete set of statements, and functions whose "
      "arguments can only be copied in. SystemVerilog adds constructs that "
      "state the designer's **intent** - this block is combinational, this "
      "one is a flop, this case is one-hot - so that simulators, synthesis "
      "and lint can check it; it completes the C statement set; and it adds "
      "operators for set membership, wildcard comparison and bit-stream "
      "packing. This chapter covers them in the order an RTL engineer meets "
      "them, then the subroutine features that testbench code relies on.")

    # ------------------------------------------------------------------
    h2("always_comb versus always @*")
    p("`always_comb` models combinational logic. Compared with the "
      "Verilog-2001 `always @*`, IEEE 1800 (9.2.2.2) gives it four extra "
      "properties:")
    bul(["**Time-zero evaluation.** It runs once at time 0, after all "
         "`initial` and `always` processes have started, so its outputs are "
         "consistent with its inputs even if no input ever changes. "
         "`always @*` waits for the first event and may never run.",
         "**Complete sensitivity, including functions.** It is sensitive to "
         "every variable read in the block **and in any function it calls**; "
         "`always @*` only looks inside the block, so a function that reads a "
         "module-level signal directly leaves the block stale.",
         "**Single writer.** Variables written by an `always_comb` may not be "
         "written by any other process - multiple drivers become a compile "
         "error rather than a race.",
         "**No timing controls.** `#`, `@`, `wait` and blocking calls that "
         "consume time are illegal inside it; it must be pure logic."],
        ordered=True)
    code([
        'module t14_comb;',
        "  localparam logic K = 1'b0;",
        "  logic a = 1'b0, inv = 1'b0;         // 'inv' is read only inside the function",
        '  logic y_star, y_comb, z_star, z_comb;',
        '  function automatic logic f(input logic x);',
        '    return x ^ inv;                   // reads a signal that is not an argument',
        '  endfunction',
        '  always @*    z_star = ~K;           // no signals in the expression: never runs',
        '  always_comb  z_comb = ~K;           // always_comb runs once at time 0',
        "  always @*    y_star = f(a);         // sensitive to 'a' only",
        "  always_comb  y_comb = f(a);         // sensitive to 'a' AND 'inv' (read in f)",
        '  initial begin',
        '    #1 $display("t=1 z_star=%b z_comb=%b y_star=%b y_comb=%b", z_star, z_comb, y_star, y_comb);',
        '    a = 1;   #1 $display("a=1   : y_star=%b y_comb=%b", y_star, y_comb);',
        '    inv = 1; #1 $display("inv=1 : y_star=%b y_comb=%b  <- always @* is stale", y_star, y_comb);',
        '    $finish;',
        '  end',
        'endmodule',
    ], "Time-zero evaluation and function sensitivity.")
    out([
        't14_comb.sv:8: warning: @* found no sensitivities so it will never trigger.',
        't14_comb.sv:9: warning: always_comb process has no sensitivities.',
        't=1 z_star=x z_comb=1 y_star=x y_comb=0',
        'a=1   : y_star=1 y_comb=1',
        'inv=1 : y_star=1 y_comb=0  <- always @* is stale',
        't14_comb.sv:16: $finish called at 3 (1s)',
    ], "Icarus Verilog 12: the IEEE-defined behaviour.")
    p("`z_star` stays x forever because `~K` contains no signal to trigger "
      "`always @*` (Icarus even warns about it); `always_comb` evaluated it at "
      "time 0. When `inv` changes, only `always_comb` re-evaluates, because "
      "it is sensitive to what `f` reads. In silicon both blocks are the "
      "same XOR gate, so the `always @*` version is a genuine "
      "**simulation/synthesis mismatch** that gate-level simulation or "
      "equivalence checking would expose.")
    out([
        't=1 z_star=1 z_comb=1 y_star=0 y_comb=0',
        'a=1   : y_star=1 y_comb=1',
        'inv=1 : y_star=0 y_comb=0  <- always @* is stale',
        '- t14_comb.sv:16: Verilog $finish',
    ], "Verilator 5.020 on the same file: no x, and no stale value.")
    p("Verilator does not reproduce either symptom: it is a 2-state, "
      "cycle-based simulator that schedules combinational logic by static "
      "analysis rather than by the event-driven rules. That is convenient but "
      "means a Verilator-only flow can never catch this class of bug - one "
      "more reason sign-off regressions run on an event-driven simulator.")
    box("key", "always_latch and always_ff",
        ["`always_latch` has exactly the semantics of `always_comb` (time-0 "
         "run, inferred sensitivity, single writer) but documents that a latch "
         "is intended; tools warn if the logic is not a latch, and warn on "
         "`always_comb` blocks that do infer one. `always_ff` must contain "
         "exactly one event control, at the top, and no other timing control; "
         "its variables must not be written elsewhere, and synthesis reports "
         "an error or warning if it does not infer flip-flops. Neither adds "
         "anything to simulation semantics beyond these checks - their value "
         "is that intent becomes checkable."])
    code(["always_ff @(posedge clk or negedge rst_n)     // async active-low reset flop",
          "  if (!rst_n) q <= '0;",
          "  else if (en) q <= d;",
          "",
          "always_latch                                  // transparent-high latch",
          "  if (g) lq <= d;",
          "",
          "always_comb begin                             // default first: no latch",
          "  nxt = st;",
          "  if (go) nxt = st.next();",
          "end"],
         "Canonical forms of the three intent-specific blocks.")

    # ------------------------------------------------------------------
    h2("unique, unique0 and priority")
    p("The keywords `unique`, `unique0` and `priority` in front of `if` or "
      "`case` make two claims about the decision: whether the branch "
      "conditions are **mutually exclusive** and whether they are "
      "**complete** (some branch always matches). The simulator checks the "
      "claims at run time and reports a **violation**; synthesis uses them to "
      "simplify logic. Since IEEE 1800-2009 the checks are deferred: a "
      "violation is only reported if it is still present at the end of the "
      "time step, so zero-delay glitches while inputs settle are ignored.")
    tbl(["Qualifier", "Claims exclusive", "Claims complete", "Synthesis meaning",
         "Violation reported when"],
        [["(none)", "no", "no", "priority logic in branch order; latch if incomplete",
          "never"],
         ["`unique`", "yes", "yes", "parallel_case + full_case",
          "no branch matches (and no else/default), or more than one matches"],
         ["`unique0`", "yes", "no", "parallel_case", "more than one branch matches"],
         ["`priority`", "no (first wins)", "yes", "full_case",
          "no branch matches (and no else/default)"]],
        widths=[12, 13, 13, 28, 34], bold_first=True)
    code([
        'module t14_uniq;',
        '  logic [2:0] sel;',
        '  logic [1:0] u, p;',
        '  always_comb begin',
        "    u = 2'd0;",
        '    unique casez (sel)                 // claims: items are mutually exclusive AND complete',
        "      3'b1??:  u = 2'd3;",
        "      3'b?1?:  u = 2'd2;",
        "      3'b??1:  u = 2'd1;",
        '    endcase',
        '  end',
        '  always_comb begin',
        "    p = 2'd0;",
        '    priority casez (sel)               // claims: complete; first match wins',
        "      3'b1??:  p = 2'd3;",
        "      3'b?1?:  p = 2'd2;",
        "      3'b??1:  p = 2'd1;",
        '    endcase',
        '  end',
        '  initial begin',
        '    sel = 3\'b010; #1 $display("sel=%b u=%0d p=%0d", sel, u, p);',
        '    sel = 3\'b110; #1 $display("sel=%b u=%0d p=%0d", sel, u, p);',
        '    sel = 3\'b000; #1 $display("sel=%b u=%0d p=%0d", sel, u, p);',
        '    $finish;',
        '  end',
        'endmodule',
    ], "A unique and a priority casez over overlapping patterns.")
    out([
        't14_uniq.sv:6: vvp.tgt sorry: Case unique/unique0 qualities are ignored.',
        'sel=010 u=2 p=2',
        'sel=110 u=3 p=3',
        'WARNING: t14_uniq.sv:14: value is unhandled for priority or unique case statement',
        '         Time: 2  Scope: t14_uniq',
        'WARNING: t14_uniq.sv:6: value is unhandled for priority or unique case statement',
        '         Time: 2  Scope: t14_uniq',
        'sel=000 u=0 p=0',
        't14_uniq.sv:24: $finish called at 3 (1s)',
    ], "Icarus Verilog 12.")
    p("For sel = 3'b110 the first two items of the `unique casez` both match, "
      "a uniqueness violation - but Icarus announces at compile time that it "
      "ignores the exclusivity check and only reports the no-match case "
      "(sel = 000) for both statements. Verilator, run with `--assert`, does "
      "check exclusivity and stops on the first violation with \"Assertion "
      "failed in TOP.t14_uniq: synthesis parallel_case, but multiple matches "
      "found\" at time 1. Commercial simulators (VCS, Xcelium, Questa) "
      "report both kinds of violation as run-time warnings with the file, "
      "line and time.")
    box("warn", "Pitfall: unique is a promise to synthesis, not a check in silicon",
        ["With `unique case`, synthesis may build an AND-OR mux that assumes "
         "one-hot select - for the overlapping input 110 the hardware ORs two "
         "branch values, while RTL simulation picks the first matching item. "
         "With a missing default, full_case lets synthesis treat unlisted "
         "values as don't-care, so the gates can output anything where "
         "simulation holds the previous or default value. Both are "
         "simulation/synthesis mismatches that only the run-time violation "
         "reports protect you from - so never ignore those reports, and never "
         "use the `// synopsys parallel_case full_case` comments, which give "
         "synthesis the same freedom with no simulation check at all."])
    box("tip", "When to use which",
        ["`unique case` for decoders whose select is one-hot or fully "
         "decoded by design (FSM state decode with an enum covering all "
         "values, one-hot mux selects). `priority if` for arbitration where "
         "order matters but some request is guaranteed. Plain `case` with a "
         "`default` when unsure - it is always safe. `unique0` for one-hot "
         "selects that may legally be all zero."])

    # ------------------------------------------------------------------
    h2("Assignment operators, ++ and -- and their blocking nature")
    p("SystemVerilog adds the C operators `++`, `--`, `+=`, `-=`, `*=`, `/=`, "
      "`%=`, `&=`, `|=`, `^=`, `<<=`, `>>=`, `<<<=` and `>>>=`. IEEE 1800 "
      "(11.4.1-11.4.2) specifies that they **behave as blocking "
      "assignments**. That is harmless in `always_comb` and in testbench "
      "code, and wrong in `always_ff`, where every other process reading the "
      "variable at the same clock edge races with the update.")
    code([
        'module t14_ffpit;',
        '  logic clk = 0;',
        '  int   cnt_b = 0, cnt_nb = 0, snap_b, snap_nb;',
        '  always #5 clk = ~clk;',
        '  always_ff @(posedge clk) cnt_b++;              // ++ is a BLOCKING assignment',
        '  always_ff @(posedge clk) cnt_nb <= cnt_nb + 1; // nonblocking: the flop idiom',
        '  always_ff @(posedge clk) begin',
        '    snap_b  <= cnt_b;                            // race: old or new value?',
        '    snap_nb <= cnt_nb;                           // always the old value',
        '  end',
        '  initial begin',
        '    repeat (3) @(negedge clk)',
        '      $display("cnt_b=%0d snap_b=%0d | cnt_nb=%0d snap_nb=%0d", cnt_b, snap_b,',
        '               cnt_nb, snap_nb);',
        '    $finish;',
        '  end',
        'endmodule',
    ], "`cnt_b++` in an always_ff versus the nonblocking idiom.")
    out([
        'cnt_b=1 snap_b=0 | cnt_nb=1 snap_nb=0',
        'cnt_b=2 snap_b=2 | cnt_nb=2 snap_nb=1',
        'cnt_b=3 snap_b=2 | cnt_nb=3 snap_nb=2',
        't14_ffpit.sv:15: $finish called at 30 (1s)',
    ], "Icarus Verilog 12: snap_b sees the old value on cycles 1 "
        "and 3 but the new value on cycle 2.")
    p("The nonblocking pair (`cnt_nb`, `snap_nb`) behaves like two flops: the "
      "snapshot is always one behind. The blocking pair gives an answer that "
      "depends on the order in which the simulator happens to run the two "
      "processes - Icarus even changes its mind between cycles, and "
      "Verilator prints `snap_b` equal to `cnt_b` on every cycle. Synthesis "
      "builds two ordinary flops in both cases, so the RTL simulation of the "
      "blocking version does not match the netlist. Lint catches it "
      "(Verilator warns on blocking assignments in `always_ff` via BLKSEQ).")
    box("warn", "Pitfall: ++ inside always_ff",
        ["Write `cnt <= cnt + 1'b1;` in sequential blocks, never `cnt++` or "
         "`cnt += 1`. The same applies to `i++` in a `for` loop only if `i` "
         "is a module-level variable read by another process - a loop "
         "variable declared in the `for` header is local and safe."])

    # ------------------------------------------------------------------
    h2("Loops and jump statements")
    p("SystemVerilog completes the loop set: `do ... while` (body runs at "
      "least once), `foreach` over any array (the index variables are "
      "declared implicitly, are automatic and read-only), loop variables "
      "declared in the `for` header (`for (int i = 0; ...)`, local to the "
      "loop), and the jump statements `break`, `continue` and `return`. "
      "`disable` is still available for named blocks but `break`/`continue` "
      "are clearer and synthesizable in loops with static bounds.")
    code([
        'module t14_sub;',
        "  int data[8] = '{3, -1, 7, 0, 5, -4, 9, 2};",
        '',
        '  // default argument values, return, void function',
        '  function automatic int clip(int v, int lo = 0, int hi = 7);',
        '    if (v < lo) return lo;',
        '    if (v > hi) return hi;',
        '    return v;',
        '  endfunction : clip',
        '',
        '  function automatic void show(string tag, const ref int a[8]);  // no copy, read-only',
        '    $write("%s:", tag);',
        '    foreach (a[i]) $write(" %0d", a[i]);',
        '    $display("");',
        '  endfunction',
        '',
        "  task automatic bump(ref int a[8], input int by = 1);          // modifies caller's array",
        '    foreach (a[i]) a[i] += by;',
        '  endtask',
        '',
        '  initial begin : main',
        '    int sum, i;',
        '    sum = 0;  i = 0;',
        '    show("orig ", data);',
        '    foreach (data[k]) begin : scan',
        '      if (data[k] < 0) continue;          // skip negatives',
        '      if (data[k] == 0) break;            // stop at the first zero',
        '      sum += data[k];',
        '    end : scan',
        '    $display("sum before first 0 (positives only) = %0d", sum);',
        '    do i++; while (data[i] != 5);         // body runs at least once',
        '    $display("first 5 at index %0d", i);',
        '    $display("clip(9)=%0d clip(-2)=%0d clip(9,.hi(4))=%0d clip(.v(2),.lo(3))=%0d",',
        '             clip(9), clip(-2), clip(9, .hi(4)), clip(.v(2), .lo(3)));',
        '    bump(data, 10);',
        '    show("bump ", data);',
        "    void'(clip(100));                     // explicitly discard a return value",
        '    $finish;',
        '  end : main',
        'endmodule',
    ], "foreach, continue/break, do-while, default and named "
         "arguments, const ref and ref, named end labels.")
    out([
        'orig : 3 -1 7 0 5 -4 9 2',
        'sum before first 0 (positives only) = 10',
        'first 5 at index 4',
        'clip(9)=7 clip(-2)=0 clip(9,.hi(4))=4 clip(.v(2),.lo(3))=3',
        'bump : 13 9 17 10 15 6 19 12',
        '- t14_sub.sv:38: Verilog $finish',
    ], "Verilator 5.020 (Icarus 12 rejects `const ref` and `break`).")
    p("The listing also shows **named end labels** (`end : scan`, "
      "`endfunction : clip`, `end : main`): the name after the colon must "
      "match the block's name, and the compiler checks it - worthwhile on "
      "long generate blocks and FSMs. For a multidimensional array, "
      "`foreach (m[i, j])` iterates both dimensions with i outermost.")
    tbl(["Statement", "Synthesizable?", "Note"],
        [["`for`, `foreach` with constant bounds", "yes", "unrolled"],
         ["`break`, `continue` in such loops", "commercial tools; Yosys 0.33 rejects `break`",
          "becomes enable logic on later iterations"],
         ["`while`, `do-while`", "only if the tool can bound the iterations",
          "avoid in RTL"],
         ["`return` in a function", "yes", "early exit logic"],
         ["`repeat (N)`", "yes with constant N", "mostly used in testbenches"]],
        widths=[36, 30, 34])

    # ------------------------------------------------------------------
    h2("Functions and tasks: the SystemVerilog additions")
    bul(["**Void functions** return nothing and are called as statements; a "
         "non-void function called as a statement must be cast to void: "
         "`void'(f(x));`.",
         "**return** exits a function (with a value) or a task (without).",
         "**Default argument values**: `int lo = 0` - the argument may be "
         "omitted in a call; a missing positional argument can be skipped "
         "with an empty comma, `f(1, , 3)`.",
         "**Named argument binding**: `clip(.v(2), .lo(3))`, like port "
         "connections; positional and named arguments may be mixed with the "
         "positional ones first.",
         "**Functions with output/inout arguments** and functions that call "
         "tasks through `fork ... join_none` are legal, but a function still "
         "cannot consume time.",
         "**begin/end is optional** around multiple statements in a "
         "function or task body.",
         "**Lifetime**: in modules, interfaces and packages, tasks and "
         "functions are static by default (Verilog heritage) - declare them "
         "`automatic` unless you need shared storage. Methods of classes "
         "are **automatic by default** and cannot be static-lifetime."])
    h3("Argument directions and passing by reference")
    tbl(["Direction", "Mechanism", "Typical use"],
        [["`input` (default)", "copied in at the call", "values"],
         ["`output`", "copied out when the subroutine returns", "results of a task"],
         ["`inout`", "copied in at the call and out at the return", "rare"],
         ["`ref`", "passed by reference: the subroutine sees and changes the "
          "caller's variable immediately, even while it waits for time to pass",
          "large arrays, signals a task must watch while it runs"],
         ["`const ref`", "by reference, read-only", "large arrays and "
          "objects passed for reading, without a copy"]],
        widths=[16, 54, 30])
    p("Two rules matter for `ref`. First, it is only allowed in subroutines "
      "with **automatic** lifetime. Second, the actual argument must be a "
      "variable of an equivalent type - not a net, not an expression, and "
      "not a part-select. The difference with `output` is visible when time "
      "passes: an `output` argument updates the caller's variable only at "
      "the end of the task, whereas with `ref` every assignment is seen "
      "immediately, and a task waiting on a `ref` argument (`@(sig)`) sees "
      "changes the caller makes.")
    box("expert", "Interview insight: why can't ref be used with static tasks?",
        ["A static task has one set of argument variables shared by all "
         "calls; a reference would have to be rebound on every call while "
         "another caller might still be using it. Automatic subroutines "
         "allocate a fresh frame per call, so each call can hold its own "
         "reference. The same reason makes UVM declare every task and "
         "function in classes, which are automatic by default."])

    # ------------------------------------------------------------------
    h2("Set membership: inside")
    p("`expr inside {set}` is 1 if the expression equals any member of the "
      "set. Members can be single values, ranges `[lo:hi]` (inclusive, `$` "
      "for an open end), and whole arrays, whose elements are all members. "
      "Comparison uses wildcard equality in one direction: x and z bits in a "
      "**set member** are don't-cares, x or z in the tested expression are "
      "not. The result is 1 on a match, 0 if nothing matches, and x if "
      "nothing matches but some comparison was x.")
    code([
        'module t14_inside;',
        '  logic [7:0] op;',
        '  logic [3:0] a, b;',
        "  int         lst[] = '{2, 3, 5, 7};",
        '  initial begin',
        "    op = 8'h25;",
        '    $display("op inside {[8\'h20:8\'h2F], 8\'h40} = %b", op inside {[8\'h20:8\'h2F], 8\'h40});',
        '    $display("3 inside lst=%b  4 inside lst=%b", 3 inside {lst}, 4 inside {lst});',
        '    $display("op inside {8\'b0010_??01} = %b", op inside {8\'b0010_??01});',
        "    a = 4'b1010;",
        '    $display("a ==? 4\'b1?1? : %b   a !=? 4\'b0??? : %b", a ==? 4\'b1?1?, a !=? 4\'b0???);',
        '    $display("a ==  4\'b1x10 : %b   a ==? 4\'b1x10 : %b", a == 4\'b1x10, a ==? 4\'b1x10);',
        "    b = 4'b1x10;",
        '    $display("b ==? 4\'b1?10 : %b   b ==? 4\'b1010 : %b", b ==? 4\'b1?10, b ==? 4\'b1010);',
        '    $display("b inside {4\'b1010, 4\'b1110} : %b", b inside {4\'b1010, 4\'b1110});',
        '    $finish;',
        '  end',
        'endmodule',
    ], "inside with ranges, arrays and wildcards; wildcard "
         "equality.")
    out([
        "op inside {[8'h20:8'h2F], 8'h40} = 1",
        '3 inside lst=1  4 inside lst=0',
        "op inside {8'b0010_??01} = 1",
        "a ==? 4'b1?1? : 1   a !=? 4'b0??? : 1",
        "a ==  4'b1x10 : 1   a ==? 4'b1x10 : 1",
        "b ==? 4'b1?10 : 1   b ==? 4'b1010 : 1",
        "b inside {4'b1010, 4'b1110} : 1",
        '- t14_inside.sv:16: Verilog $finish',
    ], "Verilator 5.020 (Icarus 12: \"sorry: inside expressions not "
        "supported yet\").")
    p("`inside` replaces long OR-chains of comparisons in RTL decode "
      "(`addr inside {[BASE:BASE+SIZE-1]}`) and is synthesizable in all "
      "commercial tools and Verilator; constant ranges become comparators. "
      "It is also the membership operator of constraints (Chapter 19).")

    h3("Wildcard equality ==? and !=?")
    p("`a ==? b` compares bit by bit, treating x and z bits **of the "
      "right-hand operand** as wildcards. An x or z in the left operand in a "
      "non-wildcard position makes the result x. This is the operator that "
      "`casez`-style matching should have been, and it is synthesizable when "
      "the right-hand side is a constant.")
    code([
        'module t14_wild4;',
        "  logic [3:0] a = 4'b1010, b = 4'b1x10;",
        '  initial begin',
        '    $display("a ==  4\'b1x10 : %b   a ==? 4\'b1x10 : %b   a === 4\'b1x10 : %b",',
        "             a == 4'b1x10, a ==? 4'b1x10, a === 4'b1x10);",
        '    $display("b ==? 4\'b1?10 : %b   b ==? 4\'b1010 : %b   b !=? 4\'b1010 : %b",',
        "             b ==? 4'b1?10, b ==? 4'b1010, b !=? 4'b1010);",
        '  end',
        'endmodule',
    ], "Wildcard equality with 4-state operands.")
    out([
        "a ==  4'b1x10 : x   a ==? 4'b1x10 : 1   a === 4'b1x10 : 0",
        "b ==? 4'b1?10 : 1   b ==? 4'b1010 : x   b !=? 4'b1010 : x",
    ], "Icarus Verilog 12 (4-state). Verilator, being 2-state, turns "
        "the x of b into 0 and prints 1 for the same comparisons (last lines above).")
    tbl(["Operator", "x/z in left operand", "x/z in right operand", "Result can be x?"],
        [["`==`, `!=`", "unknown -> result x", "unknown -> result x", "yes"],
         ["`===`, `!==`", "compared literally", "compared literally", "no"],
         ["`==?`, `!=?`", "unknown -> result x", "wildcard (don't care)", "yes"],
         ["`inside`", "unknown -> result x", "set members: wildcard", "yes"]],
        widths=[16, 28, 30, 26])

    # ------------------------------------------------------------------
    h2("Streaming operators")
    p("The streaming operators pack the bits of one or more expressions into "
      "a stream and unpack it into a target, optionally reordering. "
      "`{>> slice {a, b}}` streams left to right; `{<< slice {a, b}}` takes "
      "the stream in blocks of `slice` bits (default 1, or the width of a "
      "type given as slice) and reverses the order of the blocks. The "
      "operator is a bit-stream cast: sources and targets can be vectors, "
      "packed or unpacked structs and arrays, and, in commercial simulators, "
      "dynamic arrays and queues.")
    code([
        'module t14_stream;',
        "  logic [7:0]  b  = 8'b1100_0101;",
        "  logic [31:0] w  = 32'h1122_3344;",
        '  logic [3:0]  ver, crc;',
        '  logic [7:0]  len;',
        '  logic [3:0]  n1, n2;',
        '  logic [15:0] pkt;',
        '  initial begin',
        '    $display("{<<{b}}     = %b   (bit reverse)", {<<{b}});',
        '    $display("{<<8{w}}    = %h   (byte swap / endian)", {<<8{w}});',
        '    $display("{<<16{w}}   = %h   (half-word swap)", {<<16{w}});',
        '    $display("{>>{w}}     = %h   (no reordering)", {>>{w}});',
        "    {n1, n2} = {<<4{8'hA5}};               // stream into a concatenation of targets",
        '    $display("{n1,n2}     = %h %h", n1, n2);',
        "    pkt = {>>{4'hF, 8'h0C, 4'h3}};         // concatenate fields into a packet",
        '    $display("pkt         = %h", pkt);',
        "    {>>{ver, len, crc}} = 16'h7A53;        // unpack: stream on the left-hand side",
        '    $display("unpack      : ver=%h len=%h crc=%h", ver, len, crc);',
        '    $finish;',
        '  end',
        'endmodule',
    ], "Bit reversal, byte swap, packing and unpacking with "
         "streaming operators.")
    out([
        '{<<{b}}     = 10100011   (bit reverse)',
        '{<<8{w}}    = 44332211   (byte swap / endian)',
        '{<<16{w}}   = 33441122   (half-word swap)',
        '{>>{w}}     = 11223344   (no reordering)',
        '{n1,n2}     = 5 a',
        'pkt         = f0c3',
        'unpack      : ver=7 len=a5 crc=3',
        '- t14_stream.sv:19: Verilog $finish',
    ], "Verilator 5.020 (Icarus 12: \"sorry: Streaming "
        "concatenation not supported\").")
    p("Note the rules. With `<<`, the **order of the slices** is reversed, "
      "not the bits within a slice: `{<<8{w}}` is a byte swap and "
      "`{<<{b}}` (slice 1) a bit reversal. `{>>{...}}` does not reorder and "
      "behaves like a concatenation that is allowed to be the target of an "
      "assignment. If the stream is wider than a fixed-size target, it is "
      "an error. If the target is wider, IEEE 1800 (11.4.14) left-justifies "
      "the stream and fills the remaining bits on the right with zeros - "
      "unlike an ordinary assignment, which zero-extends on the left. Tools "
      "do not agree on this corner:")
    code([
        'module t14_pad;',
        '  logic [15:0] y;',
        '  initial begin',
        "    y = {<<{8'hA5}};",
        '    $display("y=%h", y);',
        '    $finish;',
        '  end',
        'endmodule',
    ], "An 8-bit stream assigned to a 16-bit target.")
    out([
        'y=00a5',
        '- t14_pad.sv:6: Verilog $finish',
    ], "Verilator 5.020 right-justifies (16'h00A5, where the "
        "standard gives 16'hA500). Size streams to their targets exactly.")
    box("warn", "Pitfall: streaming into unpacked and dynamic containers",
        ["Unpacking a word into a byte array or queue (`bytes = {>>8{w}};`) "
         "is the typical testbench use - serializing a transaction into a "
         "payload. It is legal IEEE 1800 and supported by VCS, Xcelium and "
         "Questa, but Verilator 5.020 rejects it (\"Unsupported: Stream "
         "operation on a variable of a type 'logic[7:0]$[0:3]'\" for an "
         "unpacked array, and a C++ compile error for a queue). In RTL, "
         "`{<<8{w}}` for byte swapping is synthesizable in all major "
         "tools; streaming with a variable slice size is not."])

    h2("Summary")
    bul(["`always_comb` runs at time 0, is sensitive to everything read "
         "including inside called functions, and enforces a single writer; "
         "`always @*` does none of that. `always_ff` and `always_latch` "
         "document and check intent.",
         "`unique` (exclusive + complete), `unique0` (exclusive) and "
         "`priority` (complete, first wins) produce run-time violation "
         "reports and give synthesis parallel/full-case freedom - mismatches "
         "if the claims are false.",
         "`++`, `--` and the compound assignments are blocking: do not use "
         "them on flops in `always_ff`.",
         "SystemVerilog adds do-while, foreach, break, continue, return, "
         "named end labels, void functions, default and named arguments, "
         "and `ref`/`const ref` (automatic subroutines only).",
         "`inside` tests set membership with ranges and wildcards; `==?`/`!=?` "
         "treat x/z of the right operand as don't-care.",
         "Streaming operators pack, unpack and reorder bit streams: `{<<8{w}}` "
         "swaps bytes, `{<<{v}}` reverses bits."])
    h2("Exercises")
    bul(["Write a function `parity_ok()` that reads a module-level signal "
         "directly and call it from both `always @*` and `always_comb`. Show "
         "in Icarus which block goes stale and explain how a lint tool "
         "would flag the `always @*` version.",
         "Code a 4-requester fixed-priority arbiter with `priority casez` "
         "and a one-hot grant decoder with `unique case`. Add a stimulus "
         "that violates each claim and record the reports from Icarus and "
         "from Verilator `--assert`.",
         "Rewrite `for (i = 0; i < 16; i++) if (v[i]) begin idx = i; break; end` "
         "for synthesis, and explain whether it finds the first or the last "
         "set bit. Synthesize with Yosys.",
         "Write a task `wait_for(ref logic sig, input int max_cycles)` that "
         "returns early when `sig` rises. Why would it not work with "
         "`input logic sig`?",
         "Using only streaming operators, convert a 32-bit little-endian word "
         "to big-endian, reverse the bit order of each byte while keeping "
         "the byte order, and pack three fields (4, 8 and 4 bits) into a "
         "16-bit header.",
         "Predict the result of `4'b10x1 inside {4'b1??1, 4'b0000}` and of "
         "`4'b10x1 ==? 4'b1001`, then check them in Icarus."],
        ordered=True)


# =============================================================================
#     Chapter 15 - Packages, compilation units and name resolution
# =============================================================================
def ch15():
    chapter("Packages, Compilation Units, Scoping and Name Resolution")
    p("In Verilog-2005 there was no clean way to share a type, a constant or "
      "a function between modules: engineers used `include` files and "
      "`define` macros, which are textual, global and order-dependent. "
      "SystemVerilog adds **packages** - named, compiled scopes whose "
      "contents are imported by name - and precisely defines how an "
      "identifier is resolved when several scopes could supply it. On a "
      "large SoC with hundreds of IPs these rules decide whether the build "
      "is robust or breaks every time someone adds a file, so this chapter "
      "treats them with LRM precision.")

    # ------------------------------------------------------------------
    h2("Packages")
    p("A package is declared at the outermost level of a source file, "
      "between `package name;` and `endpackage`. It may contain parameters "
      "and localparams, typedefs (enums, structs, unions), functions and "
      "tasks, classes, variable declarations, `let` declarations, "
      "covergroups, DPI imports and imports of other packages. It may "
      "**not** contain processes (`initial`, `always`), module, interface or "
      "program instances, or hierarchical references - a package must be "
      "self-contained apart from references to other packages.")
    tbl(["Package item", "Notes"],
        [["`parameter` / `localparam`", "a `parameter` in a package behaves as a "
          "`localparam`: packages cannot be parameterized or overridden"],
         ["`typedef`", "the main content: bus structs, enums, register maps"],
         ["functions and tasks", "declare them `automatic`; static ones share "
          "storage across every caller in the design"],
         ["classes", "verification packages: transactions, drivers, UVM components"],
         ["variables", "legal but global state shared by all importers; not "
          "synthesizable; avoid"],
         ["`import` / `export`", "packages can build on other packages"]],
        widths=[28, 72])
    code([
        'package bus_pkg;',
        '  parameter int AW = 32;',
        '  typedef logic [AW-1:0] addr_t;',
        '  typedef enum logic [1:0] {OKAY, EXOKAY, SLVERR, DECERR} resp_t;',
        '  function automatic bit is_err(resp_t r);',
        '    return r inside {SLVERR, DECERR};',
        '  endfunction',
        'endpackage',
        '',
        'package uart_pkg;',
        '  parameter int AW = 12;                    // same name as bus_pkg::AW',
        '  localparam int FIFO_D = 16;',
        'endpackage',
        '',
        'package soc_pkg;',
        '  import bus_pkg::*;',
        '  export bus_pkg::*;                        // re-export what soc_pkg uses from bus_pkg',
        '  typedef struct packed { addr_t addr; resp_t resp; } txn_t;',
        'endpackage',
        '',
        'typedef int unsigned u32_t;                 // $unit scope: visible to later code in this unit',
        '',
        'module t15_pkg;',
        '  import soc_pkg::*;                        // gets txn_t and (re-exported) addr_t, resp_t',
        '  import uart_pkg::FIFO_D;                  // explicit import of one name',
        '  import uart_pkg::*;                       // wildcard: AW is only a *candidate*',
        '  localparam int AW = 8;                    // local declaration hides the wildcard candidate',
        '  txn_t t;',
        '  u32_t n;',
        '  initial begin',
        "    t = '{addr: 32'h4000_1000, resp: bus_pkg::SLVERR};",
        '    n = $bits(t);',
        '    $display("AW=%0d bus_pkg::AW=%0d uart_pkg::AW=%0d FIFO_D=%0d", AW, bus_pkg::AW,',
        '             uart_pkg::AW, FIFO_D);',
        '    $display("txn=%h bits=%0d is_err=%0d", t, n, bus_pkg::is_err(t.resp));',
        '    $finish;',
        '  end',
        'endmodule',
    ], "Three packages, a re-export, a $unit typedef, and the four "
         "ways of referring to package items.")
    out([
        'AW=8 bus_pkg::AW=32 uart_pkg::AW=12 FIFO_D=16',
        'txn=100004002 bits=34 is_err=1',
        '- t15_pkg.sv:36: Verilog $finish',
    ], "Verilator 5.020 (Icarus 12 supports packages and imports "
        "but not `export` or `inside`).")
    p("The listing uses all four referencing mechanisms. `bus_pkg::AW` is a "
      "**scope-resolution** reference: always unambiguous, needs no import, "
      "and is the recommended style for occasional use of a name. "
      "`import uart_pkg::FIFO_D;` is an **explicit import**. "
      "`import uart_pkg::*;` is a **wildcard import**. `export bus_pkg::*;` "
      "inside `soc_pkg` **re-exports** the names that `soc_pkg` itself "
      "imported from `bus_pkg`, so that users of `soc_pkg` see `addr_t` and "
      "`resp_t` without importing `bus_pkg` themselves.")

    # ------------------------------------------------------------------
    h2("Explicit versus wildcard import: the exact rules")
    p("The two import forms look similar but follow different rules "
      "(IEEE 1800 26.3), and most package-related build failures come from "
      "not knowing the difference.")
    tbl(["", "Explicit: `import p::x;`", "Wildcard: `import p::*;`"],
        [["What is imported", "the name x, immediately",
          "nothing yet: every name of p becomes a **candidate**"],
         ["When a name is actually imported", "at the import",
          "when it is referenced and not found as a local declaration or "
          "explicit import of this scope"],
         ["Local declaration of the same name", "error (two declarations)",
          "legal if it comes before any reference: the local name hides the "
          "candidate"],
         ["Same name from two packages", "error, even if never used",
          "error only if the name is referenced (ambiguous)"],
         ["Search order", "like a local declaration",
          "after local declarations of the scope, **before** enclosing scopes"]],
        widths=[24, 32, 44], bold_first=True)
    p("In the listing, `localparam int AW = 8;` is legal because `AW` is only "
      "a wildcard candidate from `uart_pkg` and has not been referenced yet; "
      "the local declaration wins. The next two files show the two classic "
      "errors.")
    code([
        'package a_pkg; parameter int W = 8;  endpackage',
        'package b_pkg; parameter int W = 16; endpackage',
        'module t15_amb;',
        '  import a_pkg::*;',
        '  import b_pkg::*;',
        '  logic [W-1:0] x;          // W is a candidate from both packages: ambiguous',
        '  initial $display("%0d", $bits(x));',
        'endmodule',
    ], "Two wildcard imports supply the same referenced name.")
    out([
        "t15_amb.sv:6: error: Ambiguous use of 'W'. It is exported by both 'a_pkg' and by 'b_pkg'.",
    ], "Icarus Verilog 12.")
    code([
        'package a_pkg; parameter int W = 8; endpackage',
        'module t15_late;',
        '  import a_pkg::*;',
        '  logic [W-1:0] x;          // W referenced: a_pkg::W is now imported',
        '  localparam int W = 4;     // too late: conflicts with the imported W',
        '  initial $display("%0d", $bits(x));',
        'endmodule',
    ], "A local declaration after the wildcard candidate was already "
         "used.")
    out([
        "t15_late.sv:5: error: 'W' has already been imported into this scope from package 'a_pkg'.",
    ], "Icarus Verilog 12.")
    box("warn", "Pitfall: tools that accept illegal imports",
        ["Verilator 5.020 builds both files above without an error - the "
         "ambiguous one silently, the late declaration with only a "
         "VARHIDDEN warning - and picks one of the candidates. Code that is "
         "\"clean\" in one tool fails in the next. The robust style avoids "
         "the question: import explicitly the few names a module needs, use "
         "`pkg::name` for the rest, and never wildcard-import two packages "
         "that may define the same identifier (every `_pkg` in an SoC "
         "defines `AW`, `DW` or `IDLE` sooner or later)."])
    box("warn", "Pitfall: export and enum literals",
        ["`export pkg::*;` exports only the names that were actually "
         "imported into the exporting package - and with a wildcard import "
         "that means only the names that package referenced. `soc_pkg` "
         "references the type `resp_t` but none of its literals, so "
         "`SLVERR` is **not** exported: the listing uses `bus_pkg::SLVERR`. "
         "Exporting or importing an enum type never brings its literals "
         "along; they are separate names. Use `export *::*;` together with "
         "explicit imports of the literals, or tell users to import the "
         "defining package."])

    # ------------------------------------------------------------------
    h2("Where to put an import")
    code(["// 1. Inside the module: visible in the body only (NOT in the port list)",
          "module a (input logic [31:0] x);",
          "  import bus_pkg::*;",
          "  ...",
          "",
          "// 2. In the module header (IEEE 1800-2009): visible in the parameter",
          "//    list, the port list and the body - the recommended form",
          "module b import bus_pkg::*; #(parameter int N = 2) (input addr_t addr);",
          "",
          "// 3. At file level, outside any module: goes into $unit and leaks into",
          "//    every later module of the same compilation unit - avoid",
          "import bus_pkg::*;",
          "module c (input addr_t addr);"],
         "The three places an import can appear.")
    p("Form 2 is what lowRISC, PULP and OpenTitan use for module ports typed "
      "with package types. Form 3 works, but its effect depends on which "
      "files end up in the same compilation unit, which is a tool option, so "
      "the same file list can compile under one simulator and fail under "
      "another.")

    # ------------------------------------------------------------------
    h2("Compilation units, $unit and compile order")
    p("A **compilation unit** is the set of source files compiled together "
      "as one unit. IEEE 1800 (3.12.1) lets the tool decide: either each "
      "file is its own unit or all files on one command line form a single "
      "unit. Questa, for example, defaults to one unit per file and merges "
      "them with `-mfcu`; other tools default the other way. Declarations "
      "made outside any module, interface, program or package - typedefs, "
      "functions, parameters, imports - belong to the compilation-unit scope, "
      "called `$unit`, and are visible to the design elements that follow "
      "them in the same unit (the `u32_t` typedef in the listing is one). "
      "`$unit::name` refers to such a declaration explicitly.")
    box("key", "Compile-order rules",
        ["A package must be compiled before any code that refers to it, and a "
         "package that imports another must come after it; the file list is "
         "therefore ordered: packages (in dependency order), then interfaces, "
         "then modules and the testbench. Modules and interfaces themselves "
         "may be compiled in any order, because instance names are resolved "
         "at elaboration. `define` macros are different again: they are "
         "text, visible from the point of definition onward in compile order "
         "across files, regardless of compilation units (Chapter 8). Build "
         "systems such as FuseSoC and Bender exist largely to compute this "
         "order from per-IP dependency files."])

    # ------------------------------------------------------------------
    h2("Name resolution")
    p("A **simple identifier** (no dots) is resolved lexically, in this "
      "order (IEEE 1800 23.9 and 26.3):")
    bul(["declarations and explicit imports in the current scope (block, "
         "task, function, module...);",
         "wildcard-import candidates of the current scope;",
         "the same two steps in each enclosing lexical scope, up to the "
         "module, interface or package;",
         "the compilation-unit scope `$unit` (and its imports);",
         "for task and function calls, and for names used as the first part "
         "of a hierarchical name, an **upward search** through the instance "
         "hierarchy (see below)."],
        ordered=True)
    code([
        'package cfg_pkg;',
        '  localparam int DEPTH = 16;',
        '  localparam int WIDTH = 32;',
        'endpackage',
        '',
        'localparam int DEPTH = 4;                    // $unit declaration',
        'localparam int LANES = 2;                    // $unit declaration',
        '',
        'module t15_scope;',
        '  import cfg_pkg::*;                         // candidates: DEPTH, WIDTH',
        '  localparam int WIDTH = 8;                  // local declaration hides cfg_pkg::WIDTH',
        '  initial begin : outer',
        '    int LANES;                               // block-local, hides $unit::LANES',
        '    LANES = 99;',
        '    $display("DEPTH=%0d  (wildcard candidate beats the outer $unit scope)", DEPTH);',
        '    $display("WIDTH=%0d  (local declaration beats the wildcard candidate)", WIDTH);',
        '    $display("LANES=%0d $unit::LANES=%0d cfg_pkg::WIDTH=%0d", LANES, $unit::LANES,',
        '             cfg_pkg::WIDTH);',
        '    begin : inner',
        '      int WIDTH;                             // nested block: hides module WIDTH',
        '      WIDTH = 1;',
        '      $display("inner WIDTH=%0d  outer.LANES=%0d  t15_scope.WIDTH=%0d", WIDTH,',
        '               outer.LANES, t15_scope.WIDTH);',
        '    end',
        '    $finish;',
        '  end',
        'endmodule',
    ], "Local declarations, wildcard candidates, $unit and nested "
         "block scopes competing for the same names.")
    out([
        'DEPTH=16  (wildcard candidate beats the outer $unit scope)',
        'WIDTH=8  (local declaration beats the wildcard candidate)',
        'LANES=99 $unit::LANES=2 cfg_pkg::WIDTH=32',
        'inner WIDTH=1  outer.LANES=99  t15_scope.WIDTH=8',
        't15_scope.sv:25: $finish called at 0 (1s)',
    ], "Icarus Verilog 12.")
    p("Each line exercises one rule. `DEPTH` is not declared in the module, "
      "so the module's wildcard candidates are searched **before** the "
      "enclosing `$unit` scope: the package value 16 wins over the `$unit` "
      "value 4 - a surprise for anyone who expects \"the closer "
      "declaration\" to win, because textually the `$unit` one is in the "
      "same file. `WIDTH` is declared locally, which hides the candidate. "
      "Inside the named blocks, block-level declarations hide module-level "
      "ones, and the hidden names remain reachable through the block or "
      "module name (`outer.LANES`, `t15_scope.WIDTH`) or `$unit::` - "
      "hierarchical names are resolved from the scope names outward, as "
      "described next.")
    box("tip", "Reading a name-resolution error",
        ["When a tool reports an unexpected width or value, find which "
         "declaration it bound: most simulators can print the resolved "
         "declaration (for example with a cross-reference or debug-info "
         "option), and lint tools warn when a local declaration hides a "
         "package or outer name (Verilator: VARHIDDEN). Treat such warnings "
         "as errors in shared RTL."])
    p("A **hierarchical name** (`a.b.c`) is resolved by first finding `a`. "
      "If `a` is a scope visible from the current scope (a local instance, "
      "generate block or named block), the reference is **downward**. If "
      "not, the search moves up the instance tree: `a` may be the instance "
      "name or the **module name** of any ancestor, and the reference "
      "continues from there - this is **upward name referencing** (23.8). A "
      "name starting with `$root.` is absolute from the top of the "
      "hierarchy.")
    code([
        'module leaf;',
        '  int v = 1;',
        '  function void hello();',
        '    $display("hello from %m, mid.tag=%0d", mid.tag);   // upward name reference',
        '  endfunction',
        'endmodule',
        'module mid;',
        '  int tag = 7;',
        '  leaf u_leaf();',
        'endmodule',
        'module t15_hier;',
        '  mid u_mid0();',
        '  mid u_mid1();',
        '  initial begin',
        '    u_mid1.tag = 9;',
        '    #1;',
        '    $display("down: u_mid0.u_leaf.v=%0d", u_mid0.u_leaf.v);   // downward reference',
        '    u_mid0.u_leaf.hello();',
        '    u_mid1.u_leaf.hello();',
        '    $finish;',
        '  end',
        'endmodule',
    ], "Downward references from the top, and an upward reference by "
         "module name from inside `leaf`.")
    out([
        'down: u_mid0.u_leaf.v=1',
        'hello from t15_hier.u_mid0.u_leaf.hello, mid.tag=7',
        'hello from t15_hier.u_mid1.u_leaf.hello, mid.tag=9',
        't15_hier.sv:20: $finish called at 1 (1s)',
    ], "Icarus Verilog 12.")
    p("`mid.tag` inside `leaf` does not name any local scope, so the "
      "simulator walks up: the parent of `u_leaf` is an instance of module "
      "`mid`, so `mid.tag` resolves to that instance's `tag` - 7 for "
      "`u_mid0` and 9 for `u_mid1`. The same text refers to different "
      "variables in different instances. `%m` prints the full hierarchical "
      "path of the current scope.")
    tbl(["Use of hierarchical names", "Where", "Synthesizable?"],
        [["Probing internal signals from a testbench", "DV, debug", "no"],
         ["Backdoor register/memory access (UVM HDL paths)", "DV", "no"],
         ["`bind` of assertion modules into RTL", "DV, formal", "the bound checker only"],
         ["Forcing and releasing internal nets", "DV, gate-level debug", "no"],
         ["Upward references in RTL", "legacy code", "no - most synthesis tools reject them"]],
        widths=[46, 26, 28])
    box("warn", "Pitfall: hierarchical references in RTL",
        ["Synthesis tools either reject cross-module references or silently "
         "create unwanted ports, and they break when the hierarchy is "
         "flattened, uniquified or renamed by the backend. Keep them out of "
         "RTL; in testbenches, collect them in one place (an interface or a "
         "`bind` module) so that a hierarchy change is fixed once."])

    # ------------------------------------------------------------------
    h2("The timescale directive versus timeunit and timeprecision")
    p("`timescale 1ns/1ps` is a compiler directive: it applies to every "
      "design element that follows it in compile order, across file "
      "boundaries, until the next `timescale`. A file without its own "
      "directive therefore inherits whatever the previous file set - the "
      "classic order-dependent bug. SystemVerilog adds the declarations "
      "`timeunit` and `timeprecision` (or the combined "
      "`timeunit 1ns / 1ps;`), which must appear first inside a module, "
      "interface, program or package, or at `$unit` level, and apply only "
      "to that scope. They take precedence over `timescale`.")
    code([
        '`timescale 1ns/1ns',
        'module tu_a;',
        '  timeunit 1ns;  timeprecision 1ps;          // overrides `timescale for this module',
        '  initial begin',
        '    #1.2345;  $display("tu_a: $realtime=%0.4f (unit 1ns, precision 1ps)", $realtime);',
        '  end',
        'endmodule',
        'module t15_time;                              // uses `timescale 1ns/1ns',
        '  tu_a u_a();',
        '  initial begin',
        '    #1.2345;  $display("top : $realtime=%0.4f (unit 1ns, precision 1ns)", $realtime);',
        '    $printtimescale(t15_time);  $printtimescale(t15_time.u_a);',
        '    #2 $finish;',
        '  end',
        'endmodule',
    ], "timeunit/timeprecision override the timescale directive for one module.")
    out([
        'top : $realtime=1.0000 (unit 1ns, precision 1ns)',
        'Time scale of (t15_time) is 1ns / 1ns',
        'Time scale of (t15_time.u_a) is 1ns / 1ps',
        'tu_a: $realtime=1.2350 (unit 1ns, precision 1ps)',
        't15_time.sv:13: $finish called at 3000 (1ps)',
    ], "Icarus Verilog 12.")
    p("The top module works with 1 ns precision, so the delay 1.2345 ns is "
      "rounded to 1 ns; `tu_a` has 1 ps precision and waits 1.235 ns (1234.5 "
      "ps rounded). The simulator's global time step is the finest precision "
      "of any module, 1 ps here, which is why `$finish` reports time 3000 in "
      "ps units. A finer global precision slows simulation, which is a real "
      "concern on large SoC gate-level runs.")
    box("tip", "Time-unit hygiene on an SoC",
        ["Put `timeunit 1ns; timeprecision 1ps;` in every package and in the "
         "top-level testbench, or pass one `-timescale=1ns/1ps` default to "
         "the simulator for files without any declaration - but never rely "
         "on file order. Delays in RTL (`#1` in flop models) are a "
         "simulation-only convenience that synthesis ignores."])

    # ------------------------------------------------------------------
    h2("Best practices for SoC projects")
    bul(["**One package per IP**, named after it: `uart_pkg` for types and "
         "parameters, `uart_reg_pkg` for the (usually generated) register "
         "map. A top-level `soc_pkg` holds the address map, interrupt "
         "numbers and global widths.",
         "**One package per file**, file named after the package "
         "(`uart_pkg.sv`), compiled before its users; the IP's dependency file "
         "(FuseSoC `.core`, Bender.yml) lists packages first.",
         "**Prefix exported names** with the IP (`UART_FIFO_DEPTH`, "
         "`uart_cfg_t`) or rely on `uart_pkg::` qualification; enum literals "
         "especially need unique names.",
         "**Import in the module header** for port types; import explicitly "
         "or qualify with `::` inside bodies; never import at file level.",
         "**Packages cannot be parameterized.** A per-instance width belongs "
         "in a module parameter, a type parameter (Chapter 17), a "
         "parameterized class, or a typedef macro - not in a package.",
         "**Functions in packages are automatic and pure**: no global state, "
         "so they synthesize and can be reused in RTL and testbench.",
         "**Separate RTL and DV packages**: RTL packages must be "
         "synthesizable; verification packages (classes, `string`, queues) "
         "import them, never the reverse."])

    h2("Summary")
    bul(["Packages hold shared parameters, types, functions and classes; "
         "they cannot contain processes or instances and cannot be "
         "parameterized.",
         "`pkg::name` always works; explicit imports behave like local "
         "declarations; wildcard imports create candidates that are imported "
         "on first reference and are searched before enclosing scopes.",
         "Ambiguous wildcard references and local declarations after use "
         "are errors in compliant tools - Verilator 5.020 accepts both.",
         "`export` re-exports only names actually imported; enum literals "
         "need their own import.",
         "Compilation units and `$unit` are tool-dependent; order packages "
         "first and avoid file-level declarations.",
         "Hierarchical names resolve downward or upward (by instance or "
         "module name); keep them out of RTL.",
         "`timeunit`/`timeprecision` are scoped and order-independent, "
         "unlike `timescale`."])
    h2("Exercises")
    bul(["Create `a_pkg` and `b_pkg`, both defining `typedef logic [7:0] "
         "data_t;` and `parameter int N`. Write a module that wildcard-imports "
         "both and uses only `data_t`. Is it legal? What if it also declares "
         "`localparam int N = 4;` before any use? After a use?",
         "Build `soc_pkg` that re-exports `axi_pkg` so that "
         "`import soc_pkg::*;` alone gives access to `axi_pkg::resp_e` and all "
         "its literals. Test it in Icarus and in Verilator.",
         "Two files each start with a different `timescale`; a third "
         "has none. Show that reordering the file list changes the "
         "behaviour of the third, then fix it with `timeunit`.",
         "Write a checker module that is bound into every instance of a FIFO "
         "and reports its depth through an upward reference to the parent "
         "module's parameter. Why is this acceptable in a testbench but not "
         "in RTL?",
         "Sketch the package structure (names, contents, dependencies and "
         "compile order) for an SoC with a RISC-V core, an AXI crossbar, "
         "a UART and a DMA."],
        ordered=True)


# =============================================================================
#     Chapter 16 - Interfaces
# =============================================================================
def ch16():
    chapter("Interfaces, Modports and Virtual Interfaces")
    p("A bus is a set of signals that always travel together and obey one "
      "protocol. In Verilog each module on the bus declares every signal as "
      "a separate port and every instantiation connects every signal again; "
      "a 40-signal AXI port becomes 40 lines in the module header, 40 in "
      "each instantiation and 40 more in the testbench. A SystemVerilog "
      "**interface** declares the bundle once. Beyond wiring, an interface "
      "can hold the protocol's **modports** (the direction of each signal "
      "as seen by each kind of participant), **tasks and functions** (for "
      "example a bus-functional model), **assertions** checking the "
      "protocol, and **clocking blocks** for race-free testbench timing. "
      "Through **virtual interfaces** it is also the bridge between the "
      "static module world and class-based testbenches, which is why every "
      "UVM agent starts from one.")

    # ------------------------------------------------------------------
    h2("Declaring and instantiating an interface")
    p("An interface is a design element like a module: it has an optional "
      "parameter list, an optional port list (usually just the clock and "
      "reset shared by all participants), and a body declaring the bundled "
      "signals. It is instantiated like a module, and an instance is "
      "connected to a module port whose type is the interface name.")
    code([
        'interface vr_if #(parameter int W = 8) (input logic clk, input logic rst_n);',
        '  logic         valid, ready;',
        '  logic [W-1:0] data;',
        '',
        '  modport src (output valid, data, input  ready, input clk, rst_n);   // producer side',
        '  modport dst (input  valid, data, output ready, input clk, rst_n);   // consumer side',
        '  modport mon (input  valid, ready, data, clk);                        // passive',
        '',
        '  // Bus-functional-model tasks live with the signals they drive. Called at a',
        '  // falling edge: drive at the falling edge, sample 1 time unit later (all',
        '  // logic settled), so the DUT sees exactly the sampled values at the next',
        '  // rising edge - race-free in any simulator.',
        '  task automatic put(input logic [W-1:0] d);',
        '    logic hs;',
        "    data = d;  valid = 1'b1;",
        '    do begin #1 hs = ready; @(negedge clk); end while (!hs);',
        "    valid = 1'b0;",
        '  endtask',
        '  task automatic get(output logic [W-1:0] d);',
        '    logic hs;',
        "    ready = 1'b1;",
        '    do begin #1 hs = valid; d = data; @(negedge clk); end while (!hs);',
        "    ready = 1'b0;",
        '  endtask',
        'endinterface',
        '',
        '// DUT: a registered pipeline stage that adds one; ports are modports',
        'module incr_stage #(parameter int W = 8) (vr_if.dst s, vr_if.src m);',
        '  assign s.ready = !m.valid || m.ready;       // accept when output slot free/draining',
        '  always_ff @(posedge s.clk or negedge s.rst_n)',
        "    if (!s.rst_n)            m.valid <= 1'b0;",
        '    else if (s.ready) begin',
        '      m.valid <= s.valid;',
        "      if (s.valid) m.data <= s.data + 1'b1;",
        '    end',
        'endmodule',
        '',
        '// Passive monitor on the mon modport (a generic "interface i" port also works in',
        '// commercial tools; Verilator 5.020 rejects generic interface ports)',
        'module hs_counter (vr_if.mon i);',
        '  int n = 0;',
        '  always @(posedge i.clk) if (i.valid && i.ready) n++;',
        'endmodule',
        '',
        'module t16_vr;',
        '  logic clk = 0, rst_n = 0;',
        '  always #5 clk = ~clk;',
        '  vr_if #(8) a (.clk, .rst_n);                // into the DUT',
        '  vr_if #(8) b (.clk, .rst_n);                // out of the DUT',
        '  incr_stage #(8) dut (.s(a.dst), .m(b.src));',
        '  hs_counter cnt_b (.i(b.mon));',
        '  logic [7:0] got;',
        '  initial begin',
        "    a.valid = 1'b0;  b.ready = 1'b0;",
        "    repeat (2) @(negedge clk);  rst_n = 1'b1;",
        '    fork',
        "      for (int k = 0; k < 4; k++) a.put(8'h10 * k);          // producer thread",
        '      for (int k = 0; k < 4; k++) begin                      // consumer thread',
        '        b.get(got);',
        '        $display("[%0t] got %h", $time, got);',
        '      end',
        '    join',
        '    @(negedge clk) $display("handshakes on b: %0d", cnt_b.n);',
        '    $finish;',
        '  end',
        'endmodule',
    ], "A parameterized valid/ready interface with modports and BFM "
         "tasks, a DUT whose ports are modports, a passive monitor and a "
         "testbench.")
    out([
        '[40] got 01',
        '[50] got 11',
        '[60] got 21',
        '[70] got 31',
        'handshakes on b: 4',
        '- t16_vr.sv:64: Verilog $finish',
    ], "Verilator 5.020 (Icarus 12 does not support interface ports: "
        "\"syntax error ... Errors in port declarations\").")
    p("Each value leaves the one-stage pipeline incremented by one, and the "
      "monitor counts four handshakes. Note what the listing does not "
      "contain: no port list with individual valid/ready/data signals "
      "anywhere, even though three modules and a testbench share them. "
      "Changing `W` or adding a signal (say, a `last` flag) touches only the "
      "interface and the logic that uses the new signal.")
    tbl(["Element", "Syntax", "Notes"],
        [["Declaration", "`interface vr_if #(parameter int W = 8) (input logic clk, rst_n);`",
          "ports are shared by all users; body signals are normally `logic`"],
         ["Instance", "`vr_if #(8) a (.clk, .rst_n);`", "like a module instance"],
         ["Port of interface type", "`module m (vr_if s);`",
          "any modport; all signals accessible"],
         ["Port with modport", "`module m (vr_if.dst s);`",
          "only the modport's signals, with its directions"],
         ["Connection", "`m u (.s(a));` or `.s(a.dst)`",
          "the modport may be chosen in the port or at the connection, not "
          "differently in both"],
         ["Generic port", "`module m (interface s);`",
          "any interface type; modport chosen at connection"]],
        widths=[20, 44, 36])

    # ------------------------------------------------------------------
    h2("Modports")
    p("A **modport** lists the interface signals a participant may access "
      "and their direction **from that participant's point of view**. The "
      "producer's modport makes `valid` and `data` outputs and `ready` an "
      "input; the consumer's modport is the mirror image; a monitor's "
      "modport makes everything an input. Accessing a signal that is not in "
      "the modport, or writing an `input`, is a compile error - this is how "
      "interfaces recover the direction checking that loose ports had.")
    bul(["Modport ports can be interface signals, interface ports (the "
         "`clk` above) or **modport expressions** that rename or slice: "
         "`modport lo (input .d(data[3:0]));`.",
         "`import` in a modport gives the participant access to tasks or "
         "functions declared in the interface: "
         "`modport src (output valid, data, input ready, import put);`.",
         "`export` declares that the **module** connected through that modport "
         "provides the task or function body (`task s.put(...)` in the "
         "module, where `s` is its interface port), which the interface's other users can then call. Rarely "
         "used, poorly supported in synthesis.",
         "A modport may also name a clocking block "
         "(`modport tb (clocking cb);`) to give the testbench a view that "
         "only allows synchronous access (Chapter 21)."])
    box("warn", "Pitfall: interfaces without modports",
        ["If a module port is declared with the bare interface type and no "
         "modport is chosen anywhere, every signal is accessible in any "
         "direction. Simulation does not care, but synthesis must infer "
         "directions from use and may create inout ports or fail, and lint "
         "cannot detect two modules driving the same signal. Always give "
         "synthesizable interfaces modports and connect through them."])

    # ------------------------------------------------------------------
    h2("Generic interface ports and interface arrays")
    p("A port declared with the keyword `interface` instead of an interface "
      "name accepts an instance of **any** interface type; the module works "
      "as long as the names it references exist in whatever is connected. "
      "It is the interface counterpart of a type parameter and is used for "
      "protocol-agnostic monitors. Verilator 5.020 does not implement it:")
    code(["module hs_counter (interface i);      // generic interface port",
          "  int n = 0;",
          "  always @(posedge i.clk) if (i.valid && i.ready) n++;",
          "endmodule"],
         "The generic form of the monitor in the listing above.")
    out([
        '%Error-UNSUPPORTED: t16_vr.sv:34:20: Unsupported: generic interfaces',
        '%Error: Exiting due to 1 error(s)',
    ], "Verilator 5.020 on the generic version (commercial "
        "simulators and DC/Genus accept it).")
    p("Interfaces can be instantiated as arrays, and a module port can be an "
      "array of interfaces - the natural description of an N-port "
      "crossbar or an N-lane datapath:")
    code(["vr_if #(8) lane [4] (.clk, .rst_n);          // four instances lane[0..3]",
          "",
          "module rr_arbiter #(parameter int N = 4)",
          "  (vr_if.dst req [N], vr_if.src gnt);        // array of interface ports",
          "  ...",
          "endmodule",
          "",
          "rr_arbiter #(4) u_arb (.req(lane), .gnt(out_if));",
          "for (genvar i = 0; i < 4; i++) begin : gen_src",
          "  src_model u_src (.m(lane[i]));",
          "end"],
         "Interface arrays and array-of-interface ports (fragment). Indices "
         "used to select an element must be constant (genvars or literals).")
    box("warn", "Pitfall: interface-array elements need constant indices",
        ["`lane[i]` with a genvar or literal `i` is fine; a variable index "
         "(`lane[sel]` in procedural code) is illegal, because each element "
         "is a separate instance, not an element of a memory. To select "
         "among interfaces at run time, copy their signals into an unpacked "
         "array in a generate loop, or use virtual interfaces in a "
         "testbench. Tools are also uneven here: Verilator 5.020 failed to "
         "build the model (internal fault or C++ compile error) when an "
         "interface-array element was passed to a class constructor as a "
         "virtual interface, which is why the next "
         "example uses two named instances."])

    # ------------------------------------------------------------------
    h2("Tasks and functions in interfaces: bus-functional models")
    p("The `put` and `get` tasks in `vr_if` are a **bus-functional model** "
      "(BFM): they turn a transaction (\"send this byte\") into cycle-accurate "
      "pin activity, and they live in the interface next to the signals, so "
      "every testbench that instantiates the interface gets them. A task "
      "called through an interface instance (`a.put(8'h10)`) executes in the "
      "context of that instance and drives its signals. Declare them "
      "`automatic` so that concurrent calls do not share locals.")
    p("The tasks follow a strict timing discipline that makes them "
      "race-free in every simulator: they are called at a falling edge, "
      "drive signals there, sample the handshake one time unit later, and "
      "return at a falling edge. The DUT samples at the rising edge in the "
      "middle, when all these values are stable. The naive version - drive "
      "and sample right at the rising edge - produced a **different "
      "result** in Verilator when this example was first written (the DUT "
      "appeared to accept data one cycle early) because the order between "
      "the testbench process resuming after `@(posedge clk)` and the DUT's "
      "`always_ff` is not something to rely on.")
    code(["clocking cb @(posedge clk);          // inside vr_if (Chapter 21)",
          "  default input #1step output #1;   // sample just before, drive just after",
          "  output valid, data;",
          "  input  ready;",
          "endclocking",
          "",
          "task automatic put(input logic [W-1:0] d);",
          "  cb.data <= d;  cb.valid <= 1'b1;",
          "  do @(cb); while (!cb.ready);       // cb.ready = value sampled before the edge",
          "  cb.valid <= 1'b0;",
          "endtask"],
         "The same BFM with a clocking block - the standard solution. Verilator "
         "5.020 rejected this version (BLKANDNBLK on valid and data); it runs "
         "on commercial simulators.")
    box("key", "Clocking blocks in interfaces - preview of Chapter 21",
        ["A clocking block declares, for one clock, which signals the "
         "testbench samples and drives and with what skew. Inputs are "
         "sampled in the Preponed region (`#1step`: the value just before "
         "the edge, exactly what the DUT's flops see); outputs are driven "
         "after the edge. Placing the clocking block in the interface and "
         "exposing it through a testbench modport makes every driver and "
         "monitor race-free by construction, which is why UVM agents access "
         "DUT pins only through clocking blocks."])

    # ------------------------------------------------------------------
    h2("Virtual interfaces")
    p("Classes (Chapter 18) are created at run time and cannot have ports, "
      "so a class-based driver cannot be connected to an interface instance "
      "the way a module is. A **virtual interface** is a variable that holds "
      "a **reference to an interface instance**: `virtual apb_if vif;`. "
      "It is assigned from an instance (`vif = bus0;`), passed around like "
      "any handle, and used with the dot notation to read and drive the "
      "instance's signals and call its tasks.")
    code([
        'interface apb_if (input logic pclk);',
        '  logic        psel, penable, pwrite, pready;',
        '  logic [7:0]  paddr;',
        '  logic [31:0] pwdata, prdata;',
        '  modport slv (input psel, penable, pwrite, paddr, pwdata, pclk, output pready, prdata);',
        'endinterface',
        '',
        'module apb_ram (apb_if.slv bus);               // tiny APB slave: 4 words, no wait states',
        '  logic [31:0] mem [4];',
        "  assign bus.pready = 1'b1;",
        '  always_ff @(posedge bus.pclk) begin',
        '    if (bus.psel && bus.penable && bus.pwrite) mem[bus.paddr[3:2]] <= bus.pwdata;',
        '    if (bus.psel && !bus.penable && !bus.pwrite) bus.prdata <= mem[bus.paddr[3:2]];',
        '  end',
        'endmodule',
        '',
        'class apb_master;                              // class-based driver',
        '  virtual apb_if vif;                          // handle to a real interface instance',
        '  string         name;',
        '  logic [31:0]   rd_unused;',
        '  function new(string name, virtual apb_if vif);',
        '    this.name = name;  this.vif = vif;',
        '  endfunction',
        '  task write(logic [7:0] a, logic [31:0] d);    // call at a falling edge',
        '    vif.psel = 1;  vif.pwrite = 1;  vif.paddr = a;  vif.pwdata = d;   // setup',
        '    @(negedge vif.pclk) vif.penable = 1;                               // access',
        '    wait_ready(rd_unused);',
        '    vif.psel = 0;  vif.penable = 0;',
        '  endtask',
        '  task read(logic [7:0] a, output logic [31:0] d);',
        '    vif.psel = 1;  vif.pwrite = 0;  vif.paddr = a;',
        '    @(negedge vif.pclk) vif.penable = 1;',
        '    wait_ready(d);',
        '    vif.psel = 0;  vif.penable = 0;',
        '  endtask',
        '  task wait_ready(output logic [31:0] rd);        // sample 1 unit after the drive',
        '    logic rdy;',
        '    do begin #1 rdy = vif.pready; rd = vif.prdata; @(negedge vif.pclk); end while (!rdy);',
        '  endtask',
        'endclass',
        '',
        'module t16_vif;',
        '  logic clk = 0;',
        '  always #5 clk = ~clk;',
        '  apb_if  bus0 (.pclk(clk)), bus1 (.pclk(clk));   // two APB bus instances',
        '  apb_ram u_ram0 (.bus(bus0));',
        '  apb_ram u_ram1 (.bus(bus1));',
        '  apb_master m[2];',
        '  logic [31:0] d;',
        '  initial begin',
        '    m[0] = new("m0", bus0);                    // bind class handles to instances',
        '    m[1] = new("m1", bus1);',
        '    foreach (m[i]) begin m[i].vif.psel = 0; m[i].vif.penable = 0; end',
        '    @(negedge clk);',
        "    m[0].write(8'h4, 32'hCAFE_0000);",
        "    m[1].write(8'h4, 32'h0000_BEEF);",
        '    m[0].read(8\'h4, d);  $display("[%0t] %s read %h", $time, m[0].name, d);',
        '    m[1].read(8\'h4, d);  $display("[%0t] %s read %h", $time, m[1].name, d);',
        '    $finish;',
        '  end',
        'endmodule',
    ], "An APB interface, a small APB slave, and a class-based APB "
         "master that drives two bus instances through virtual interfaces.")
    out([
        '[70] m0 read cafe0000',
        '[90] m1 read 0000beef',
        '- t16_vif.sv:59: Verilog $finish',
    ], "Verilator 5.020.")
    p("The same class code drives two different buses; which one is decided "
      "by the handle passed to `new`. That is the whole idea of UVM's "
      "`uvm_config_db#(virtual apb_if)::set(...)` - the top-level module "
      "publishes each interface instance, and each agent's driver and "
      "monitor retrieve the handle for the bus they serve (Chapter 26).")
    tbl(["Rule", "Detail"],
        [["Type", "`virtual [interface] name[#(params)][.modport]`; the "
          "parameters must match the instance's"],
         ["Default value", "`null`; using a null virtual interface is a run-time "
          "fatal error - check it after retrieving it from a config database"],
         ["Assignment", "from an interface instance, another virtual interface of "
          "the same type, or `null`"],
         ["With a modport", "`virtual apb_if.mst vif;` restricts access to that "
          "modport's signals"],
         ["Clocking blocks", "`vif.cb.psel <= 1;` and `@(vif.cb)` are the normal "
          "way UVM drivers access pins (not supported by Verilator 5.020, which "
          "reported an internal error)"],
         ["Not allowed", "virtual interfaces in synthesizable code or as module "
          "ports"]],
        widths=[22, 78])

    # ------------------------------------------------------------------
    h2("Protocol assertions inside the interface")
    p("Because every participant of a bus connects through the interface, "
      "the interface is the ideal home for the protocol's rules: written "
      "once, they check every master and slave in every testbench, and "
      "formal tools pick them up as properties. The valid/ready rules of "
      "AXI-style handshakes are the classic example.")
    code(["// inside interface vr_if (concurrent assertions: Chapter 22)",
          "property p_hold_until_ready;           // once valid, hold it and the data",
          "  @(posedge clk) disable iff (!rst_n)",
          "    valid && !ready |=> valid && $stable(data);",
          "endproperty",
          "a_hold:  assert property (p_hold_until_ready)",
          "           else $error(\"%m: valid dropped or data changed before ready\");",
          "a_known: assert property (@(posedge clk) disable iff (!rst_n)",
          "                         !$isunknown(valid) && !$isunknown(ready));",
          "c_stall: cover property (@(posedge clk) (valid && !ready) [*3]);  // 3-cycle stall"],
         "Handshake rules as concurrent assertions and a cover property. "
         "Shown without output: run them on a commercial simulator or a "
         "formal tool (Verilator 5.020 supports only a small subset of SVA).")
    p("Assertions in an interface are ignored by synthesis tools (or "
      "removed with `ifndef SYNTHESIS` guards), so they cost nothing in "
      "silicon. The same properties are often packaged separately as a "
      "checker bound to the interface, which lets the verification team "
      "own them without editing the design's interface file.")

    # ------------------------------------------------------------------
    h2("Interfaces and synthesis")
    p("Synthesis tools treat an interface instance as a bundle of wires "
      "that is **flattened** during elaboration: each signal becomes an "
      "ordinary net named after the instance and the signal (the exact "
      "naming - `bus_psel`, `bus.psel`, `\\bus.psel` - depends on the tool). "
      "Modports provide the directions. Functions in an interface are "
      "synthesizable like any function; tasks with timing controls and "
      "clocking blocks are not and are ignored or rejected.")
    tbl(["Aspect", "Status", "Advice"],
        [["Interfaces with modports between RTL modules",
          "DC, Genus, Vivado, Quartus Pro: supported; Yosys 0.33: basic cases",
          "fine inside an IP or subsystem"],
         ["Interfaces on the top-level ports of a chip or FPGA design",
          "often unsupported or produces awkward port names",
          "use plain ports or structs at the top level"],
         ["Parameterized interfaces", "supported by the major ASIC tools",
          "keep parameters to widths"],
         ["Interface arrays and generic interface ports", "tool-dependent",
          "test with every tool in the flow first"],
         ["Netlist / gate-level simulation", "the interface is gone after "
          "synthesis", "gate-level testbenches need a wrapper that maps "
          "flattened ports back to an interface"]],
        widths=[30, 38, 32], bold_first=True)
    box("expert", "Interview insight: interfaces or structs for RTL buses?",
        ["Both appear in industry. Interfaces carry modports, tasks and "
         "assertions and read naturally; request/response **struct pairs** "
         "(Chapter 17) work in every tool, can be registered, multiplexed and "
         "stored in FIFOs with one statement, and have no direction ambiguity. "
         "Many teams therefore use structs for RTL ports (lowRISC, PULP) and "
         "interfaces for the testbench side, where virtual interfaces and "
         "clocking blocks are indispensable. A good answer mentions this "
         "split and the synthesis/netlist-naming concerns."])

    h2("Summary")
    bul(["An interface bundles signals, parameters, modports, tasks, "
         "assertions and clocking blocks; it is instantiated once and "
         "connected to module ports of interface type.",
         "Modports define per-participant directions and access, and can "
         "import interface tasks; connect through them in synthesizable code.",
         "Generic `interface` ports and interface arrays add flexibility "
         "but are unevenly supported (Verilator 5.020 rejects generic ports); "
         "interface-array selects need constant indices.",
         "BFM tasks in interfaces must follow a race-free timing discipline; "
         "clocking blocks provide it by construction.",
         "A virtual interface is a handle to an interface instance - the "
         "link between classes and the DUT, and the basis of every UVM agent.",
         "Interfaces synthesize by flattening; avoid them on top-level ports, "
         "and prefer struct pairs where every tool in the flow must agree."])
    h2("Exercises")
    bul(["Write a complete `apb_if` with `mst`, `slv` and `mon` modports "
         "and a `mon` modport that imports a function `bit is_access()`. "
         "Use it to connect an APB master model, the `apb_ram` of this "
         "chapter and a monitor that prints every transfer.",
         "Add a `last` signal to `vr_if` and extend the BFM with "
         "`put_pkt(byte q[$])`. How many files change?",
         "Remove the `#1` sampling delay from `vr_if.put` and `get` and run "
         "the example again in Verilator (and, if available, a commercial "
         "simulator). Explain every difference in the output.",
         "Build a 4-lane datapath with an interface array and a generate "
         "loop, then a monitor that counts handshakes on each lane. Why "
         "can't the monitor loop over `lane[i]` with a run-time index?",
         "Write a class `vr_driver` holding a `virtual vr_if #(8)` handle and "
         "a mailbox of bytes; it pulls bytes and calls the interface's `put` "
         "task. Instantiate two drivers for two interface instances.",
         "Synthesize `incr_stage` with Yosys 0.33 (with a wrapper that "
         "instantiates the interfaces) and inspect the flattened port and "
         "net names."],
        ordered=True)


# =============================================================================
#     Chapter 17 - SystemVerilog idioms for SoC RTL
# =============================================================================
def ch17():
    chapter("SystemVerilog Idioms for SoC RTL: Type Parameters, Struct-Based "
            "Bus Bundles, let, and the Synthesizable Subset Across Tools")
    p("The previous chapters described the language feature by feature. "
      "This chapter shows how the features combine in the RTL of real SoCs. "
      "Open-source projects such as lowRISC Ibex and OpenTitan, the PULP "
      "platform (CVA6, the `axi` and `common_cells` libraries) and many "
      "commercial code bases have converged on a small set of idioms: "
      "packages of bus typedefs, request/response struct pairs instead of "
      "dozens of loose wires, modules parameterized by **types** as well as "
      "by numbers, enum-typed state machines, register files described as "
      "structs, and assertions written next to the logic they check. The "
      "chapter ends with the question every team must answer before using "
      "any of this: which constructs do all the tools in the flow accept?")

    # ------------------------------------------------------------------
    h2("Type parameters")
    p("A module parameter can be a **type**: `parameter type T = logic [7:0]`. "
      "Inside the module, `T` is used like any typedef - for ports, "
      "variables and arrays - and each instance can override it with any "
      "type, including a packed struct from a package. Derived constants "
      "follow from the type with `$bits(T)`. A FIFO, a pipeline register, "
      "a clock-domain-crossing synchronizer or an arbiter written once this "
      "way serves every payload in the SoC.")
    code([
        '// ---------------- bus package: one package per protocol / IP -----------------',
        'package axil_pkg;',
        '  localparam int AW = 32, DW = 32, SW = DW / 8;',
        '  typedef logic [AW-1:0] addr_t;',
        '  typedef logic [DW-1:0] data_t;',
        '  typedef logic [SW-1:0] strb_t;',
        "  typedef enum logic [1:0] {OKAY = 2'b00, SLVERR = 2'b10, DECERR = 2'b11} resp_e;",
        '  typedef struct packed { addr_t addr; logic [2:0] prot; } ax_t;   // AW / AR payload',
        '  typedef struct packed { data_t data; strb_t strb; }      w_t;    // W payload',
        '  typedef struct packed { data_t data; resp_e resp; }      r_t;    // R payload',
        '  typedef struct packed {                                          // master -> slave',
        '    ax_t aw; logic aw_valid;  w_t w; logic w_valid;  logic b_ready;',
        '    ax_t ar; logic ar_valid;  logic r_ready;',
        '  } req_t;',
        '  typedef struct packed {                                          // slave -> master',
        '    logic aw_ready; logic w_ready;  resp_e b_resp; logic b_valid;',
        '    logic ar_ready; r_t r; logic r_valid;',
        '  } rsp_t;',
        'endpackage',
        '',
        '// ---------------- generic FIFO with a type parameter -------------------------',
        'module fifo_t #(parameter type T = logic [7:0], parameter int DEPTH = 4,',
        '                localparam int AW = $clog2(DEPTH))           // derived, not overridable',
        '  (input  logic clk, rst_n,',
        '   input  logic push, input T wdata, output logic full,',
        '   input  logic pop,  output T rdata, output logic empty);',
        '  T            mem [DEPTH];',
        '  logic [AW:0] wp, rp;                                        // extra MSB wrap bit',
        '  let ptr_eq(a, b) = (a[AW-1:0] == b[AW-1:0]);               // let: a scoped macro',
        '  assign empty = (wp == rp);',
        '  assign full  = ptr_eq(wp, rp) && (wp[AW] != rp[AW]);',
        '  assign rdata = mem[rp[AW-1:0]];',
        '  always_ff @(posedge clk or negedge rst_n)',
        "    if (!rst_n) begin wp <= '0; rp <= '0; end",
        '    else begin',
        "      if (push && !full)  begin mem[wp[AW-1:0]] <= wdata; wp <= wp + 1'b1; end",
        "      if (pop  && !empty) rp <= rp + 1'b1;",
        '    end',
        '`ifndef SYNTHESIS',
        '  always_ff @(posedge clk) if (rst_n) begin                  // RTL-embedded checks',
        '    a_no_ovf: assert (!(push && full))  else $error("%m: push while full");',
        '    a_no_udf: assert (!(pop && empty))  else $error("%m: pop while empty");',
        '  end',
        '`endif',
        'endmodule',
        '',
        'module t17_soc;',
        '  import axil_pkg::*;',
        '  logic clk = 0, rst_n = 0;',
        '  always #5 clk = ~clk;',
        '  logic push = 0, pop = 0, full, empty;',
        '  ax_t  wd, rd;',
        '  fifo_t #(.T(ax_t), .DEPTH(4)) u_awq (.clk, .rst_n, .push, .wdata(wd), .full,',
        '                                       .pop, .rdata(rd), .empty);',
        '  initial begin',
        '    $display("$bits: ax_t=%0d req_t=%0d rsp_t=%0d  fifo AW=%0d", $bits(ax_t), $bits(req_t),',
        '             $bits(rsp_t), u_awq.AW);',
        '    @(negedge clk) rst_n = 1;',
        '    for (int i = 0; i < 5; i++) begin                   // 5th push overflows',
        "      @(negedge clk) push = 1;  wd = '{addr: 32'h1000 + 4 * i, prot: 3'(i)};",
        '    end',
        '    @(negedge clk) push = 0;  pop = 1;',
        '    repeat (4) begin',
        '      @(posedge clk) $display("[%0t] pop addr=%h prot=%0d", $time, rd.addr, rd.prot);',
        '    end',
        '    @(negedge clk) $finish;',
        '  end',
        'endmodule',
    ], "An AXI4-Lite style bus package, a FIFO parameterized by type, "
         "a let declaration and embedded immediate assertions.")
    out([
        '$bits: ax_t=35 req_t=111 rsp_t=41  fifo AW=2',
        '[65] %Error: t17_soc.sv:41: Assertion failed in TOP.t17_soc.u_awq.a_no_ovf:',
        '     TOP.t17_soc.u_awq.a_no_ovf: push while full',
        '-Info: t17_soc.sv:41: Verilog $stop, ignored due to +verilator+error+limit',
        '[75] pop addr=00001000 prot=0',
        '[85] pop addr=00001004 prot=1',
        '[95] pop addr=00001008 prot=2',
        '[105] pop addr=0000100c prot=3',
        '- t17_soc.sv:66: Verilog $finish',
    ], "Verilator 5.020 with --assert (run with "
        "+verilator+error+limit+100 so the first assertion failure does not "
        "stop the test). Icarus 12 does not support let.")
    p("Points to notice in the listing:")
    bul(["`localparam int AW = $clog2(DEPTH)` sits **in the parameter port "
         "list** (legal since IEEE 1800-2009): it is visible to the ports but "
         "cannot be overridden by an instance. The pointer scheme with an "
         "extra wrap bit is only correct for power-of-two DEPTH - a real IP "
         "would add an elaboration-time check (`if (DEPTH != 2**AW) "
         "$error(...)` in a generate block, IEEE 1800 20.11).",
         "The instance overrides the type by name: `#(.T(ax_t), .DEPTH(4))`. "
         "The memory `T mem [DEPTH]` becomes 35 bits wide automatically.",
         "Every channel payload is a packed struct built from package "
         "typedefs, so `$bits(req_t)` = 111 is computed, never hand-counted.",
         "The fifth push while full triggers the embedded assertion at time "
         "65; the FIFO correctly drops it, and the four stored entries come "
         "out in order."])
    box("key", "Rules for type parameters",
        ["A type parameter's default and override must be data types; a "
         "value parameter cannot be passed where a type is expected, or vice "
         "versa. Two instances with different type overrides are different "
         "modules to elaboration and synthesis (uniquified). Inside the "
         "module, only operations valid for every intended type should be "
         "used: assignment and `==` work for any packed type, arithmetic "
         "only for integral types. `type(expr)` gives the type of an "
         "expression, useful for declaring a temporary of \"the same type as "
         "this port\"."])

    # ------------------------------------------------------------------
    h2("Struct-based bus bundles and packages of bus typedefs")
    p("An AXI4 master port has five channels and about 40 signals; an SoC "
      "interconnect has dozens of such ports. Declaring them signal by "
      "signal makes every port list hundreds of lines long and every "
      "protocol change a global edit. The dominant industrial idiom bundles "
      "the signals into **two packed structs per protocol**, one per "
      "direction: `req_t` (master to slave: all address, write data and "
      "ready-for-response signals) and `rsp_t` (slave to master). A port is "
      "then just `input req_t req_i, output rsp_t rsp_o`.")
    diagram([
        "              req_t  (aw, aw_valid, w, w_valid, b_ready, ar, ar_valid, r_ready)",
        "   +--------+ ------------------------------------------------------> +-------+",
        "   | master |                                                         | slave |",
        "   +--------+ <------------------------------------------------------ +-------+",
        "              rsp_t  (aw_ready, w_ready, b_resp, b_valid, ar_ready, r, r_valid)",
        "",
        "   OpenTitan TL-UL:  tl_h2d_t / tl_d2h_t        PULP AXI:  axi_req_t / axi_resp_t",
    ], "Two structs, one per direction, carry a whole protocol.")
    p("Why two structs rather than one or an interface? A packed struct port "
      "has a single direction, so signals flowing both ways must be split. "
      "Structs work with every synthesis tool, cross module boundaries "
      "without modports, can be registered with one statement "
      "(`req_q <= req_d;`), multiplexed with one `? :`, stored in a FIFO "
      "with a type parameter, and compared in assertions. OpenTitan names "
      "them `tl_h2d_t`/`tl_d2h_t`; PULP names them `axi_req_t`/`axi_resp_t` "
      "and generates them with typedef macros, because packages cannot be "
      "parameterized:")
    code(["// A typedef macro (style of PULP's axi/typedef.svh) builds the channel",
          "// structs for any address/data/ID width in the scope where it is used.",
          "`define AXIL_TYPEDEF_ALL(pfx, addr_t, data_t, strb_t)                     \\",
          "  typedef struct packed { addr_t addr; logic [2:0] prot; } pfx``_ax_t;     \\",
          "  typedef struct packed { data_t data; strb_t strb; }      pfx``_w_t;      \\",
          "  typedef struct packed { pfx``_ax_t aw; logic aw_valid;                  \\",
          "                          pfx``_w_t  w;  logic w_valid;  logic b_ready;   \\",
          "                          pfx``_ax_t ar; logic ar_valid; logic r_ready;   \\",
          "                        } pfx``_req_t;",
          "",
          "module soc_top;",
          "  typedef logic [31:0] addr32_t;  typedef logic [63:0] data64_t;",
          "  typedef logic [7:0]  strb8_t;",
          "  `AXIL_TYPEDEF_ALL(periph, addr32_t, data64_t, strb8_t)  // periph_req_t ...",
          "  periph_req_t periph_req;",
          "  // A generic crossbar takes the types as parameters:",
          "  // axil_xbar #(.req_t(periph_req_t), .rsp_t(periph_rsp_t)) u_xbar (...);",
          "endmodule"],
         "Typedef macros generate protocol structs for arbitrary widths "
         "(sketch; a double grave accent joins text in macro bodies, Chapter 8).")
    box("warn", "Pitfall: struct ports in waveforms and at the netlist boundary",
        ["After synthesis, a struct port becomes one flat vector (`req_i[110:0]`) "
         "or a set of escaped names, depending on the tool's naming options; "
         "gate-level testbenches and UPF/SDC constraints written against RTL "
         "member names may no longer match. Agree on the netlist naming "
         "convention early (for DC, `change_names` rules; for Genus, "
         "`hdl_*` naming attributes), and write SDC against clocks and "
         "top-level ports, not struct members. Older waveform viewers show "
         "struct ports as one long vector; current ones decode the members."])

    # ------------------------------------------------------------------
    h2("let: a scoped, typed macro")
    p("`let name(args) = expression;` (IEEE 1800 11.12) declares a named "
      "expression that is expanded at each use, like a macro - but it obeys "
      "scoping (it can live in a package or module and be imported), its "
      "arguments are checked expressions rather than text, and it cannot "
      "silently capture neighbouring code the way `define` expansion "
      "can. The FIFO's `ptr_eq(a, b)` is a typical use: a small helper that "
      "would otherwise be a macro or a function with fixed argument widths. "
      "`let` arguments are untyped by default, so the same `let` works for "
      "any width; they can also be given types.")
    code(["package util_pkg;",
          "  let max(a, b)        = (a > b) ? a : b;",
          "  let onehot0(v)       = ((v & (v - 1)) == '0);",
          "  let in_range(x, lo, hi) = (x >= lo) && (x <= hi);",
          "endpackage",
          "",
          "// in a module:  assign ok = util_pkg::onehot0(gnt);",
          "//               localparam int W = util_pkg::max(AW, DW);"],
         "A package of let helpers.")
    p("Tool support is the catch: Verilator handles `let` (the FIFO above), "
      "Icarus 12 and Yosys 0.33 reject it, and support in commercial "
      "synthesis tools depends on the release. Where portability matters, "
      "a package function declared `automatic` is the safe alternative for "
      "fixed widths.")

    # ------------------------------------------------------------------
    h2("Assertions embedded in RTL")
    p("The designer knows the assumptions a block makes - a FIFO is never "
      "pushed when full, a one-hot select is one-hot, an index is in range. "
      "Writing them as assertions **inside the RTL** turns them into checks "
      "that run in every simulation of every testbench that ever "
      "instantiates the block, and into properties a formal tool can prove. "
      "Two forms matter for RTL:")
    tbl(["Form", "Example", "Where it runs"],
        [["Immediate assertion (in a procedural block)",
          "`a_ovf: assert (!(push && full)) else $error(...);`",
          "every simulator, Verilator with `--assert`, Yosys formal flow"],
         ["Deferred immediate (`assert final`, `assert #0`)",
          "`assert final (onehot0(gnt));`",
          "same, but only reports the value at the end of the time step"],
         ["Concurrent assertion (Chapter 22)",
          "`assert property (@(posedge clk) disable iff (!rst_n) push |-> !full);`",
          "commercial simulators and formal; limited in Verilator"]],
        widths=[28, 42, 30])
    p("Synthesis tools ignore assertions or reject the system tasks in "
      "their action blocks, so RTL assertions are wrapped in "
      "`ifndef SYNTHESIS` (a macro every synthesis tool defines or can "
      "be told to define) or placed in a separate checker module attached "
      "with `bind` (Chapter 22), which keeps the RTL file clean. Labels "
      "(`a_no_ovf:`) give each assertion a stable hierarchical name for "
      "reports, waivers and coverage.")
    box("tip", "What to assert in RTL",
        ["Interface assumptions (no push when full, no pop when empty, valid "
         "stays high until ready), encoding invariants (one-hot state, legal "
         "enum values after reset), parameter legality at elaboration time "
         "(`$error` in a generate `if`), and X-checks on control signals "
         "(`assert (!$isunknown(valid))`). Do not duplicate the "
         "testbench's scoreboard - assertions check local rules, the "
         "scoreboard checks end-to-end function."])

    # ------------------------------------------------------------------
    h2("Enum FSMs and struct register files")
    p("The second listing combines three idioms: a register map described "
      "as a packed struct in a (normally generated) package, including a "
      "typed reset value built with an assignment pattern; a register "
      "block whose entire state is one struct-typed output port; and an "
      "FSM whose state variable has an enum type, so every log message and "
      "waveform shows state names.")
    code([
        'package tmr_reg_pkg;                                   // generated-style register package',
        '  typedef struct packed {',
        '    logic [7:0]  prescale;                             // [15:8]',
        '    logic [5:0]  rsvd;                                 // [7:2]',
        '    logic        irq_en;                               // [1]',
        '    logic        en;                                   // [0]',
        '  } ctrl_t;',
        '  typedef struct packed {',
        '    ctrl_t       ctrl;                                 // 0x0',
        '    logic [15:0] reload;                               // 0x4',
        '  } regs_t;',
        "  localparam regs_t RESET = '{ctrl: '{prescale: 8'd1, default: '0}, reload: 16'hFFFF};",
        'endpackage',
        '',
        'module tmr_regs import tmr_reg_pkg::*; (               // package import in the header',
        '  input  logic        clk, rst_n,',
        '  input  logic        wr, input logic [2:0] addr, input logic [15:0] wdata,',
        '  output regs_t       q);                              // whole register file as a port',
        '  always_ff @(posedge clk or negedge rst_n)',
        '    if (!rst_n) q <= RESET;',
        '    else if (wr)',
        '      unique case (addr)',
        "        3'h0:    q.ctrl   <= ctrl_t'(wdata & 16'hFF03);   // mask reserved bits",
        "        3'h4:    q.reload <= wdata;",
        '        default: ;',
        '      endcase',
        'endmodule',
        '',
        'module t17_regs;',
        '  import tmr_reg_pkg::*;',
        '  typedef enum logic [1:0] {IDLE, LOAD, COUNT} st_e;   // enum-typed FSM state',
        '  logic clk = 0, rst_n = 0, wr = 0;',
        '  logic [2:0] addr;  logic [15:0] wdata;',
        '  regs_t q;',
        '  st_e   st;',
        '  tmr_regs u_regs (.*);                                // .* works because names match',
        '  always #5 clk = ~clk;',
        '  always_ff @(posedge clk or negedge rst_n)',
        '    if (!rst_n) st <= IDLE;',
        '    else unique case (st)',
        '      IDLE:    if (q.ctrl.en) st <= LOAD;',
        '      LOAD:                   st <= COUNT;',
        '      COUNT:   if (!q.ctrl.en) st <= IDLE;',
        '      default:                st <= IDLE;',
        '    endcase',
        '  initial begin',
        '    @(negedge clk) $display("reset: ctrl=%h reload=%h st=%s", q.ctrl, q.reload, st.name());',
        '    rst_n = 1;',
        "    @(negedge clk) begin wr = 1; addr = 3'h0; wdata = 16'h04FF; end",
        '    @(negedge clk) wr = 0;',
        '    $display("wrote : ctrl=%h prescale=%0d en=%b irq_en=%b", q.ctrl, q.ctrl.prescale,',
        '             q.ctrl.en, q.ctrl.irq_en);',
        '    repeat (3) @(negedge clk) $display("st=%s", st.name());',
        '    $finish;',
        '  end',
        'endmodule',
    ], "Struct register file with a typed reset constant, package import "
         "in the module header, `.*` connection and an enum-typed FSM.")
    out([
        'reset: ctrl=0100 reload=ffff st=IDLE',
        'wrote : ctrl=0403 prescale=4 en=1 irq_en=1',
        'st=LOAD',
        'st=COUNT',
        'st=COUNT',
        '- t17_regs.sv:54: Verilog $finish',
    ], "Verilator 5.020 (Icarus 12 does not parse the nested "
        "assignment pattern of RESET).")
    p("`q.ctrl <= ctrl_t'(wdata & 16'hFF03)` writes a whole register with "
      "the reserved bits masked; reading `q.ctrl.prescale` needs no bit "
      "numbers. Adding a field means editing the struct only - the decode, "
      "the reset value (built with `default: '0`) and every reader follow. "
      "Register generators (OpenTitan's reggen, PeakRDL, Agnisys, Magillem) "
      "emit exactly this kind of package, plus the matching UVM register "
      "model, from one register description (SystemRDL or IP-XACT).")
    box("warn", "Pitfall: variable initializers and asynchronous reset at time 0",
        ["In this testbench `rst_n` is declared `logic rst_n = 0`. A "
         "declaration initializer is executed before any process starts and "
         "generates **no** event, so `always_ff @(posedge clk or negedge "
         "rst_n)` does not see a falling edge at time 0. The registers are "
         "reset here only because `rst_n` is still 0 at the first rising "
         "clock edge. A block with a truly asynchronous reset and no clock "
         "during reset would stay unreset in simulation. Drive resets from "
         "an `initial` block (`rst_n = 1; #1 rst_n = 0;`) or keep the clock "
         "running during reset."])

    # ------------------------------------------------------------------
    h2("Generate, $bits and $clog2 in SystemVerilog style")
    p("Generate constructs (Chapter 7) combine naturally with the SV types. "
      "Loop variables are declared in the loop (`for (genvar i = 0; ...)`), "
      "generate blocks should be named so that their instances have stable "
      "hierarchical names (`gen_lane[2].u_fifo`), and conditional generate "
      "can test type-derived constants.")
    code(["module lanes #(parameter int N = 4, parameter type T = logic [31:0],",
          "               localparam int IW = (N > 1) ? $clog2(N) : 1)  // never 0 wide",
          "  (input  logic          clk, rst_n,",
          "   input  T              in_data  [N],",
          "   input  logic [IW-1:0] sel,",
          "   output T              out_data);",
          "  T stage [N];",
          "  for (genvar i = 0; i < N; i++) begin : gen_lane",
          "    if ($bits(T) > 64) begin : gen_wide              // pipeline wide payloads",
          "      always_ff @(posedge clk) stage[i] <= in_data[i];",
          "    end else begin : gen_narrow",
          "      assign stage[i] = in_data[i];",
          "    end",
          "  end",
          "  assign out_data = stage[sel];",
          "endmodule"],
         "Named generate blocks, a type-dependent generate condition and a "
         "guarded $clog2 (IEEE 1800 constant functions in parameters).")
    box("warn", "Pitfall: $clog2(1) is 0",
        ["`$clog2(N)` is the number of bits needed to encode N distinct values "
         "- 0 for N = 1. A select `logic [$clog2(N)-1:0]` then becomes "
         "`[-1:0]`, a 2-bit vector with a reversed range, and the design "
         "silently misbehaves. Guard every such parameter "
         "(`(N > 1) ? $clog2(N) : 1`) and remember that `$clog2(5)` is 3 "
         "but a counter to 5 inclusive needs `$clog2(5 + 1)`."])

    # ------------------------------------------------------------------
    h2("The synthesizable SystemVerilog subset across tools")
    p("\"Synthesizable SystemVerilog\" is not one subset: each tool accepts a "
      "different one, and an SoC flow usually passes the same RTL through "
      "five or six of them (lint, simulation, FPGA prototyping, ASIC "
      "synthesis, equivalence checking, formal). The table combines two "
      "kinds of information. The **Yosys 0.33** and **Verilator 5.020** "
      "columns were measured in this book's environment with small test "
      "modules (Yosys: `read_verilog -sv` then `synth`). The commercial "
      "columns summarize the vendors' documented support in recent "
      "releases; check the exact version your project uses.")
    tbl(["Construct", "DC / Genus", "Vivado", "Quartus Pro", "Yosys 0.33", "Verilator"],
        [["`logic`, `always_ff/comb/latch`", "yes", "yes", "yes", "yes", "yes"],
         ["Enums, enum-typed FSM", "yes", "yes", "yes", "yes", "yes"],
         ["Packed structs and unions as ports", "yes", "yes", "yes", "yes", "yes"],
         ["Multi-dimensional packed arrays", "yes", "yes", "yes", "no", "yes"],
         ["Unpacked arrays as ports", "yes", "yes", "yes", "no", "yes"],
         ["Package `p::name` references", "yes", "yes", "yes", "yes", "yes"],
         ["`import p::*` (body or module header)", "yes", "yes", "yes", "no", "yes"],
         ["Functions in packages", "yes", "yes", "yes", "no", "yes"],
         ["Assignment patterns `'{...}`", "yes", "yes", "yes", "no", "yes"],
         ["`'0`, size casts `N'(x)`, `$clog2` params", "yes", "yes", "yes", "yes", "yes"],
         ["Type parameters", "yes", "yes", "yes", "no", "yes"],
         ["Interfaces with modports", "yes", "yes", "yes", "basic", "yes"],
         ["Generic `interface` ports", "yes", "check", "check", "no", "no"],
         ["`inside`, `==?`", "yes", "yes", "yes", "no", "yes"],
         ["Streaming `{<<8{x}}` (constant slice)", "yes", "yes", "yes", "no", "yes"],
         ["`foreach`, `break`, `continue`", "yes", "yes", "yes", "no", "yes"],
         ["`let`", "check", "check", "check", "no", "yes"],
         ["`unique`/`priority` case", "yes (parallel/full)", "yes", "yes", "accepted",
          "yes; checked with --assert"],
         ["Immediate assertions", "ignored", "ignored", "ignored", "used by formal",
          "checked with --assert"],
         ["Classes, strings, queues, dynamic arrays", "no", "no", "no", "no",
          "simulation only"]],
        widths=[31, 13, 10, 12, 13, 21], bold_first=True,
        caption="Synthesizable-subset matrix. Yosys and Verilator columns: "
                "tested here. Commercial columns: vendor documentation for "
                "recent releases (\"check\": support depends on version).")
    p("Two observations follow. First, the built-in Yosys frontend accepts "
      "less than half of the idioms in this chapter; open-source ASIC and "
      "FPGA flows therefore put a converter or a stronger frontend in front "
      "of it. Second, even among commercial tools the edges differ "
      "(generic interface ports, `let`, interfaces at the top level of an "
      "FPGA design), so the safe core for IP meant to be reused everywhere "
      "is: `logic`, the three `always_*` blocks, packages with typedefs, "
      "packed structs and enums, type and value parameters, and interfaces "
      "only inside the IP, never on its top-level ports.")
    box("expert", "sv2v, Synlig and yosys-slang",
        ["**sv2v** (open source, Haskell) converts synthesizable "
         "SystemVerilog - packages, interfaces, structs, enums, type "
         "parameters, assignment patterns - into plain Verilog-2005 that "
         "Yosys, Icarus or an old FPGA tool accept: "
         "`sv2v -DSYNTHESIS pkg.sv rtl.sv > rtl_v2005.v`. It is not "
         "installed in this environment. **Synlig** (formerly "
         "yosys-systemverilog, based on Surelog/UHDM) and the **yosys-slang** "
         "plugin replace the Yosys frontend with full IEEE 1800 parsers. "
         "OpenTitan and PULP designs are routinely pushed through these "
         "paths into Yosys-based flows such as OpenROAD."])

    # ------------------------------------------------------------------
    h2("A checklist for SoC-grade SystemVerilog RTL")
    checklist("Before an IP is released to integration", [
        "Every shared type, width and enum lives in the IP's package; no "
        "file-level declarations, no wildcard imports in `$unit`.",
        "Ports use package types or type parameters; bundles are "
        "`req_t`/`rsp_t` struct pairs where a protocol has many signals.",
        "Every derived constant is computed (`$bits`, `$clog2` with a "
        "guard); parameters have legality checks at elaboration.",
        "Only `always_ff`, `always_comb` and (intentionally) `always_latch`; "
        "nonblocking in sequential blocks; no `++` on flops.",
        "FSM states are enums with explicit base type; `unique case` only "
        "where exclusivity really holds, with a `default`.",
        "Assertions for local assumptions, labelled and guarded by "
        "`SYNTHESIS` or bound from a checker module.",
        "The RTL passes lint (Verilator -Wall or a commercial linter), "
        "compiles in the event-driven simulator, and has been read by the "
        "synthesis tool (or sv2v) used downstream."])

    h2("Summary")
    bul(["Type parameters (`parameter type T`) let one FIFO, register slice "
         "or arbiter serve every payload; derived constants come from "
         "`$bits(T)` and guarded `$clog2`.",
         "Industrial SoC RTL bundles protocols into two packed structs per "
         "direction (`req_t`/`rsp_t`), defined in packages or generated by "
         "typedef macros because packages cannot be parameterized.",
         "`let` is a scoped, checked replacement for expression macros - "
         "well supported in simulators, not yet everywhere in synthesis.",
         "Immediate assertions embedded in RTL check local assumptions in "
         "every simulation and feed formal tools; guard them from synthesis.",
         "Enum-typed FSMs and struct register files make RTL self-documenting "
         "and generator-friendly.",
         "Tool support defines the usable subset: Yosys 0.33's own frontend "
         "rejects packages imports, patterns, type parameters, `inside` and "
         "more - use sv2v or an SV frontend plugin; check commercial tool "
         "versions for `let` and generic interfaces."])
    h2("Exercises")
    bul(["Extend `fifo_t` with an elaboration-time check that rejects a "
         "non-power-of-two DEPTH, then generalize the pointers so that any "
         "DEPTH >= 2 works.",
         "Write a type-parameterized register slice "
         "`#(parameter type T = logic) (input T d, input logic valid_i, "
         "output logic ready_o, ...)` with a full valid/ready handshake, and "
         "instantiate it for the `ax_t` and `w_t` channels of `axil_pkg`.",
         "Complete `axil_pkg` with a `rsp_t` and write a 4-register AXI4-Lite "
         "slave whose ports are only `input req_t req_i, output rsp_t rsp_o`.",
         "Replace the `let` in `fifo_t` with an automatic function in a "
         "package. What must the function's argument type be, and why is "
         "the `let` version more general?",
         "Take the FIFO and the register block from this chapter and find, "
         "by trial with Yosys 0.33, the minimal set of edits that makes "
         "them synthesize with the built-in frontend. Compare with what "
         "sv2v would do automatically.",
         "For the table in this chapter, add a column for the simulator you "
         "use at work (or Icarus 12) by writing one test module per row."],
        ordered=True)
