"""Part I - Verilog Fundamentals (Chapters 1-6) of the Verilog & SystemVerilog guide.

Every example shown with an out() card was compiled and run for this book with
Icarus Verilog 12 (iverilog -g2005 or -g2012 -Wall / vvp), and where stated with
Verilator 5.020 (verilator --binary --timing) or Yosys 0.33. The printed output
is pasted verbatim from those runs.
"""

from sv_guide.common import *  # noqa: F401,F403


def part1():
    part("Verilog Fundamentals",
         "Every SystemVerilog design, testbench and UVM environment still rests "
         "on the Verilog core: modules and ports, nets and variables, four-state "
         "values, the sizing and signedness rules of expressions, and the event "
         "scheduler that decides what a simulation means. This part teaches that "
         "core at the level of the IEEE standard, with every rule demonstrated by "
         "code that was actually simulated, so that later parts can build the "
         "SystemVerilog design and verification layers on solid ground.")
    _ch1()
    _ch2()
    _ch3()
    _ch4()
    _ch5()
    _ch6()


# =============================================================================
#        Chapter 1 - HDLs, Verilog and SystemVerilog
# =============================================================================
def _ch1():
    chapter("HDLs, Verilog and SystemVerilog: History, Standards, Tools and "
            "the SoC/ASIC Flow", newpage=False)
    p("A modern system-on-chip contains billions of transistors, yet almost "
      "none of them was drawn by hand. They were __described__ - in a hardware "
      "description language (HDL) - and then simulated, checked, synthesized "
      "into gates, placed and routed by tools that read that description. For "
      "digital design and verification in industry, that language is, in the "
      "overwhelming majority of projects, **Verilog** and its successor "
      "**SystemVerilog**. Every RTL designer writes it, every verification "
      "engineer writes it (more of it, in fact), and DFT, physical design, "
      "emulation and silicon-validation engineers read it every day.")
    p("This chapter sets the scene: what an HDL is and how it differs from a "
      "programming language, where Verilog and SystemVerilog came from and "
      "what each revision of the standard added, how they compare with VHDL, "
      "which tools consume them, and - most importantly for your career - "
      "which __subset__ of the language is used at each step of the SoC/ASIC "
      "flow. It ends with a first module and testbench, simulated with two "
      "different simulators and synthesized to gates.")

    # ------------------------------------------------------------------
    h2("What a hardware description language is")
    p("An HDL looks like a programming language - it has variables, "
      "operators, `if`, `for` and functions - but it describes something "
      "fundamentally different: a set of hardware blocks that all operate "
      "**at the same time**, connected by wires, whose values change as "
      "**simulated time** advances. Three ideas separate an HDL from C or "
      "Python, and all three appear in the very first Verilog you write:")
    bul(["**Concurrency.** Every `assign`, every `always` block and every "
         "module instance is an independent process. There is no \"next "
         "line\" between two `always` blocks; they run in parallel, and the "
         "simulator interleaves them according to precise scheduling rules "
         "(Chapter 5).",
         "**Time.** Statements can wait: `#10` waits ten time units, "
         "`@(posedge clk)` waits for a clock edge, `wait (ready)` waits for "
         "a condition. A program runs as fast as it can; a model advances "
         "through simulated nanoseconds.",
         "**Hardware values.** A Verilog bit is not a Boolean. It is one of "
         "four values - `0`, `1`, `x` (unknown) and `z` (high impedance, "
         "undriven) - and nets carry drive strengths so that several "
         "drivers on one wire can be resolved (Chapter 3). Vectors have an "
         "exact bit width that the language tracks through every "
         "expression (Chapter 4)."])
    tbl(["Aspect", "Software language (C, Python)", "Verilog / SystemVerilog"],
        [["Execution model", "Sequential; one thread unless you ask for more",
          "Thousands of concurrent processes; sequential only inside a "
          "procedural block"],
         ["Time", "Wall-clock time is incidental",
          "Simulated time is explicit (`#`, `@`, `wait`) and ordered by a "
          "scheduler"],
         ["Data", "Integers, floats, pointers",
          "Bit vectors of any width, 4-state values, strengths; SV adds "
          "classes, queues, strings"],
         ["Result", "An executable program",
          "(a) a simulation model, and (b) for the synthesizable subset, a "
          "netlist of gates and flip-flops"],
         ["Typical bug", "Crash, wrong answer",
          "Wrong answer only in some cycle, X-propagation, race between "
          "processes, simulation/synthesis mismatch"]],
        widths=[16, 36, 48], bold_first=True)
    p("The last row of that table matters most. Verilog has **two readers "
      "with different semantics**: a simulator executes the full language "
      "event by event, while a synthesis tool recognises a restricted set "
      "of coding patterns and maps them onto hardware. The same line of code "
      "can mean slightly different things to the two - a missing signal in "
      "a sensitivity list, an `x` in a `casex`, an initial value on a "
      "register. Much of this book is about knowing, for each construct, "
      "exactly what both readers will do.")
    box("key", "Design subset versus verification subset",
        "Roughly a quarter of SystemVerilog is synthesizable: modules, nets, "
        "logic and packed types, `always_ff`/`always_comb`, functions, "
        "parameters, generate, interfaces, packages. The rest - delays, "
        "`initial` blocks with timing, classes, dynamic arrays, queues, "
        "constrained random, coverage, most assertions, DPI - exists to "
        "**verify** hardware and runs only in simulation (or in formal and "
        "emulation tools). Knowing which side of this line a construct lives "
        "on is the first skill of a professional.")

    # ------------------------------------------------------------------
    h2("A short history of Verilog")
    p("Verilog was created in 1983-1984 at **Gateway Design Automation** by "
      "Phil Moorby, with Prabhu Goel, as the input language for a fast "
      "logic simulator, **Verilog-XL**. It borrowed its expression syntax "
      "from C, which helped its adoption by engineers who already knew C, "
      "and its key technical asset was a gate-level simulation engine fast "
      "enough for sign-off. When logic synthesis arrived (Synopsys Design "
      "Compiler, late 1980s) and accepted Verilog as input, the language "
      "became the natural bridge from description to gates.")
    tbl(["Year", "Event", "Why it mattered"],
        [["1984", "Gateway Design Automation releases Verilog and the "
          "Verilog-XL simulator", "A single language for gate-level and "
          "behavioural models"],
         ["1989-90", "Cadence acquires Gateway", "Verilog becomes the "
          "language of the market-leading simulator"],
         ["1990-91", "Cadence places the language in the public domain; "
          "**Open Verilog International (OVI)** is formed to maintain it",
          "Other vendors can build Verilog simulators and synthesis tools"],
         ["1995", "**IEEE 1364-1995**", "First IEEE standard; basis of "
          "every tool for the next decade"],
         ["2001", "**IEEE 1364-2001** (\"Verilog-2001\")", "The largest "
          "revision: ANSI ports, `signed`, `generate`, multi-dimensional "
          "arrays, `@*`, `**`, `+:`/`-:` part-selects, automatic tasks, "
          "configurations, file I/O"],
         ["2005", "**IEEE 1364-2005**", "Clarifications plus `uwire`, "
          "`$clog2`, `pragma`, `begin_keywords`; the last stand-alone "
          "Verilog standard"],
         ["2009", "1364 merged into **IEEE 1800-2009**", "Verilog is now "
          "formally a subset of SystemVerilog; 1364 is no longer "
          "maintained"]],
        widths=[10, 45, 45], bold_first=True)
    p("Standards bodies merged as well: in 2000 OVI and VHDL International "
      "combined to form **Accellera**, which incubated SystemVerilog before "
      "handing it to the IEEE. Accellera still develops UVM, SystemC, the "
      "Portable Stimulus Standard and IP-XACT, so you will meet its name "
      "throughout a verification career.")

    # ------------------------------------------------------------------
    h2("From Verilog to SystemVerilog")
    p("By the early 2000s, Verilog-2001 was adequate for RTL but weak for two "
      "jobs that had grown enormously: describing large designs concisely "
      "(no structs, no enums, no interfaces, no packages) and verifying them "
      "(no classes, no random constraints, no coverage, no assertions). "
      "Verification teams had moved to separate **hardware verification "
      "languages** - Synopsys **Vera** and Verisity **e** - coupled to the "
      "Verilog simulator through PLI. SystemVerilog was created to put all "
      "of that back into one language:")
    bul(["**SystemVerilog 3.0** (Accellera, 2002) added design features "
         "largely from **Superlog**, donated by Co-Design Automation: "
         "`logic`, 2-state types, `typedef`, `enum`, `struct`, `always_ff`/"
         "`always_comb`, interfaces.",
         "**SystemVerilog 3.1 / 3.1a** (2003-2004) added the verification "
         "layer, drawing on Synopsys' donations of **OpenVera** (classes, "
         "constrained random, coverage), **OpenVera Assertions** (the basis "
         "of SVA) and **DirectC** (the basis of DPI).",
         "**IEEE 1800-2005** standardised SystemVerilog as an extension "
         "document on top of IEEE 1364-2005.",
         "**IEEE 1800-2009** merged the two documents; from then on there is "
         "one language, SystemVerilog, and \"Verilog\" names its "
         "Verilog-2005-compatible subset."])
    tbl(["Standard", "Main additions (not exhaustive)"],
        [["1800-2005", "Everything above: data types, OOP, randomization, "
          "covergroups, SVA, DPI, interfaces, packages, program blocks, "
          "clocking blocks"],
         ["1800-2009", "Merge with 1364; checkers, `let`, `unique0`, "
          "`global clocking`, improved assertion semantics (`s_eventually`, "
          "`accept_on`...), `$fatal` elaboration tasks"],
         ["1800-2012", "Interface classes (multiple inheritance of "
          "interfaces), soft constraints, `uniqueness` constraints, "
          "coverage enhancements, `timeunit` rules clarified"],
         ["1800-2017", "Corrections and clarifications only; no major new "
          "features. The version most tools claim to support, and "
          "available at no cost through the IEEE GET program"],
         ["1800-2023", "Further clarifications plus some enhancements (for "
          "example triple-quoted multi-line string literals and class "
          "method qualifiers such as `:initial`, `:extends`, `:final`); "
          "tool support is still arriving"]],
        widths=[14, 86], bold_first=True)
    box("note", "Which standard does this book follow?",
        "The Verilog chapters (Parts I and II) follow IEEE 1364-2005, which is "
        "also the Verilog subset of IEEE 1800. The SystemVerilog chapters "
        "follow IEEE 1800-2017, the version every major tool supports, and "
        "call out 1800-2023 differences where they matter. When this book "
        "says \"the LRM\" (Language Reference Manual) it means these "
        "documents. UVM is a separate standard, IEEE 1800.2 (2017, revised "
        "2020), built on top of the language (Chapter 26).")

    # ------------------------------------------------------------------
    h2("Verilog versus VHDL, and the other HDLs")
    p("VHDL (IEEE 1076, first standardised in 1987 from the US Department "
      "of Defense VHSIC programme; revised 1993, 2002, 2008 and 2019) is the "
      "other mainstream HDL. Both describe the same hardware and both are "
      "fully supported by commercial simulation and synthesis tools; the "
      "choice is mostly regional and industrial. VHDL is strong in Europe, "
      "in aerospace and defence and in some FPGA houses; Verilog and "
      "SystemVerilog dominate ASIC and SoC work, especially verification, "
      "where UVM is SystemVerilog-only.")
    tbl(["Topic", "Verilog / SystemVerilog", "VHDL"],
        [["Typing", "Weak: widths and signedness converted implicitly "
          "(Chapter 4 exists because of this)", "Strong: explicit "
          "conversions (`resize`, `unsigned()`), fewer silent surprises"],
         ["Syntax style", "C-like, compact", "Ada-like, verbose"],
         ["Four-state logic", "Built in (`0 1 x z`)", "`std_logic` is a "
          "9-value enumerated type from a library (IEEE 1164)"],
         ["Scheduling", "Stratified event queue; races possible "
          "(Chapter 5)", "Delta cycles with signal/variable separation; "
          "deterministic by construction"],
         ["Verification", "Classes, constraints, coverage, SVA, UVM in the "
          "language", "OSVVM and UVVM libraries; PSL for assertions"],
         ["Gate-level / SDF", "Native gate primitives, specify blocks, "
          "SDF back-annotation (Chapter 9)", "VITAL (IEEE 1076.4)"],
         ["Market", "Most ASIC/SoC design and nearly all ASIC "
          "verification", "FPGA, defence, parts of Europe"]],
        widths=[18, 42, 40], bold_first=True)
    p("Mixed-language simulation is routine: commercial simulators compile "
      "Verilog, SystemVerilog and VHDL into one model, so a VHDL IP block can "
      "sit inside a SystemVerilog SoC testbench. Other languages you may "
      "encounter compile __to__ Verilog: **Chisel** (Scala), **SpinalHDL**, "
      "**Amaranth** (Python) and high-level synthesis from C++/SystemC all "
      "emit Verilog netlists, so reading generated Verilog is a useful skill "
      "even for engineers who never write it. **Verilog-AMS** extends "
      "Verilog for analog and mixed-signal modelling, and **SystemC** (IEEE "
      "1666) is a C++ library used for transaction-level architecture "
      "models.")

    # ------------------------------------------------------------------
    h2("The tool landscape")
    p("No single tool implements the whole of IEEE 1800, and every tool "
      "implements a different part of it. The table lists the main "
      "categories. The open-source tools in the last column are the ones "
      "used to run every example in this book; the commercial tools are "
      "what you will use on a production chip.")
    tbl(["Category", "What it does with the language", "Commercial",
         "Open source"],
        [["Event-driven simulator", "Executes the full language, 4-state, "
          "with timing", "Synopsys VCS, Cadence Xcelium, Siemens Questa",
          "Icarus Verilog"],
         ["Cycle-based / compiled simulator", "Translates RTL to C++; fast, "
          "2-state, limited timing", "(modes of the above)", "Verilator"],
         ["Logic synthesis", "Maps the synthesizable subset to gates",
          "Synopsys Design Compiler / Fusion Compiler, Cadence Genus",
          "Yosys"],
         ["Lint", "Static rule checks on coding style and semantics",
          "Synopsys SpyGlass, Cadence JasperGold Superlint, Siemens Questa "
          "Lint", "Verilator --lint-only, Verible"],
         ["Formal verification", "Proves SVA properties exhaustively",
          "Cadence Jasper, Synopsys VC Formal, Siemens Questa Formal",
          "SymbiYosys (Yosys)"],
         ["Equivalence checking", "Proves RTL == netlist", "Synopsys "
          "Formality, Cadence Conformal", "Yosys (equiv, limited)"],
         ["CDC / RDC", "Structural clock/reset-domain crossing checks",
          "SpyGlass CDC, Questa CDC, Jasper CDC", "-"],
         ["Emulation / prototyping", "Maps synthesizable RTL (and "
          "synthesizable testbench parts) to hardware", "Cadence Palladium "
          "and Protium, Synopsys ZeBu and HAPS, Siemens Veloce", "FPGA "
          "boards with open flows"]],
        widths=[18, 30, 32, 20], bold_first=True)
    box("warn", "Pitfall: \"it compiles\" is not portability",
        "Tools differ in what they accept and in what they warn about. Icarus "
        "Verilog is a faithful 4-state event-driven simulator but supports "
        "only part of SystemVerilog (no classes with constraints, no "
        "covergroups). Verilator accepts much of the verification language but "
        "is 2-state (it turns `x` and `z` into 0/1 values), and version 5.020 "
        "compiles `randomize()` while ignoring constraints. Synthesis tools "
        "silently ignore delays and `initial` blocks for ASIC targets. "
        "Production teams therefore run the same RTL through several tools "
        "- lint, two simulators, synthesis, equivalence - and code in the "
        "portable subset. Chapter 27 is devoted to this problem.")

    # ------------------------------------------------------------------
    h2("Where each part of the language is used in the SoC/ASIC flow")
    p("The same language serves very different engineers. The flow below "
      "shows the main steps of a digital ASIC project and, for each step, "
      "which part of Verilog/SystemVerilog is written or read. The companion "
      "RTL Design guide covers the flow itself in depth; here the question is "
      "__which language features__ each step depends on.")
    diagram([
        "  spec / architecture (C++, SystemC, Python models)",
        "        |",
        "        v",
        "  +------------------+   synthesizable SV: modules, logic, always_ff/comb,",
        "  | RTL design       |   packages, interfaces, structs, parameters, generate",
        "  +------------------+",
        "        |        \\",
        "        |         +--> DV: full SV - classes, constraints, coverage, SVA,",
        "        |              clocking blocks, DPI, UVM (simulation + formal)",
        "        v",
        "  +------------------+   lint / CDC / formal read RTL + SVA",
        "  | static sign-off  |",
        "  +------------------+",
        "        |",
        "        v",
        "  +------------------+   synthesis reads RTL, writes a structural Verilog",
        "  | synthesis + DFT  |   netlist; DFT inserts scan chains, MBIST, JTAG (Verilog",
        "  +------------------+   netlists; test patterns simulated in Verilog)",
        "        |",
        "        v",
        "  +------------------+   gate-level simulation: Verilog netlist + cell library",
        "  | gate-level sim / |   models (primitives, UDPs, specify blocks) + SDF timing",
        "  | equivalence      |",
        "  +------------------+",
        "        |",
        "        v",
        "  +------------------+   emulation / FPGA prototyping: synthesizable RTL and",
        "  | emulation, PnR,  |   synthesizable (transactor) testbench code;",
        "  | silicon bring-up |   post-silicon tests often reuse DV sequences",
        "  +------------------+",
    ], "The SoC/ASIC flow and the language subset consumed at each step.")
    tbl(["Flow step", "Language subset used", "Chapters"],
        [["RTL design", "Verilog-2005 core + synthesizable SV: `logic`, "
          "`always_ff/comb`, enums, structs, packages, interfaces, "
          "parameters, generate", "2-7, 11-17"],
         ["Design verification (DV)", "Full SV: classes, randomization, "
          "coverage, SVA, clocking blocks, mailboxes, DPI; UVM library",
          "18-26"],
         ["Formal verification", "SVA properties (`assert/assume/cover "
          "property`) bound to RTL", "22"],
         ["Gate-level simulation", "Structural Verilog netlists, gate "
          "primitives, UDPs, `specify` blocks, timing checks, SDF, "
          "`timescale`", "8-10"],
         ["DFT", "Verilog netlists with scan/MBIST; pattern testbenches "
          "(often generated) in Verilog", "9-11"],
         ["Emulation / prototyping", "Synthesizable RTL plus synthesizable "
          "transactors (SCE-MI, DPI-based)", "11, 17, 24"],
         ["Architecture / modelling", "Behavioural SV, DPI-C to C/C++ "
          "models", "24"]],
        widths=[20, 62, 18], bold_first=True)

    h3("The roadmap through this book")
    diagram([
        " Part I   Verilog fundamentals ....... every role (ch 1-6)",
        "    |",
        " Part II  Verilog in depth ........... design, DFT, gate-level (ch 7-11)",
        "    |",
        " Part III SystemVerilog for design ... RTL designers (ch 12-17)",
        "    |                                 \\",
        "    |                                  +-- (designers may stop here,",
        "    v                                      then read ch 22 and 27)",
        " Part IV  SystemVerilog for verification ... DV engineers (ch 18-24)",
        "    |",
        " Part V   putting it together: TB from scratch, UVM, pitfalls, roles (ch 25-28)",
    ], "Suggested reading paths. Parts I-III are needed by everyone; "
       "verification engineers continue through Part IV.")

    # ------------------------------------------------------------------
    h2("Your first module and testbench")
    p("Every Verilog description is built from **modules**. A module has a "
      "name, a list of **ports** (its pins), and a body describing its "
      "behaviour or structure. A **testbench** is simply another module - "
      "usually with no ports - that instantiates the design under test "
      "(DUT), drives its inputs and checks its outputs. Below is a one-bit "
      "full adder and a self-checking testbench that applies all eight input "
      "combinations.")
    code([
        '`timescale 1ns/1ns',
        '// A 1-bit full adder: the "hello world" of hardware',
        'module full_adder (',
        '  input  wire a, b, cin,',
        '  output wire sum, cout',
        ');',
        '  assign sum  = a ^ b ^ cin;',
        '  assign cout = (a & b) | (cin & (a ^ b));',
        'endmodule',
        '',
        'module tb_full_adder;',
        '  reg  a, b, cin;',
        '  wire sum, cout;',
        '  integer i, errors = 0;',
        '',
        '  full_adder dut (.a(a), .b(b), .cin(cin), .sum(sum), .cout(cout));',
        '',
        '  initial begin',
        '    for (i = 0; i < 8; i = i + 1) begin',
        '      {a, b, cin} = i[2:0];',
        '      #1;                                    // let the assigns settle',
        '      if ({cout, sum} !== a + b + cin) begin',
        '        errors = errors + 1;',
        '        $display("MISMATCH a=%b b=%b cin=%b -> %b%b", a, b, cin, cout, sum);',
        '      end',
        '      $display("t=%0t a=%b b=%b cin=%b | cout=%b sum=%b", $time, a, b, cin, cout, sum);',
        '    end',
        '    if (errors == 0) $display("PASS"); else $display("FAIL: %0d errors", errors);',
        '    $finish;',
        '  end',
        'endmodule',
    ], "File c1_hello.v: a full adder (the design) "
         "and its exhaustive, self-checking testbench.")
    p("Reading it top to bottom:")
    bul(["The compiler directive `timescale` (all compiler directives start "
         "with a grave accent) sets the time unit to 1 ns and the precision "
         "to 1 ns, so `#1` means one nanosecond (Chapter 8).",
         "`module full_adder (...)` declares the ports in the **ANSI style** "
         "of Verilog-2001: direction, type and name together (Chapter 2).",
         "The two `assign` statements are **continuous assignments**: they "
         "behave like gates, re-evaluating whenever an operand changes "
         "(Chapter 5). This is pure combinational hardware.",
         "In the testbench, `reg` variables hold the stimulus and `wire` nets "
         "carry the DUT outputs. The instance `full_adder dut (...)` connects "
         "ports **by name**.",
         "The `initial` block is a process that runs once from time 0. "
         "`{a, b, cin} = i[2:0]` assigns three bits at once through a "
         "**concatenation** on the left-hand side.",
         "`#1` lets simulated time advance so that the continuous assignments "
         "settle before the check. Without it, the check would read the old "
         "outputs - the most common beginner bug.",
         "The check compares `{cout, sum}` with `a + b + cin`. It works only "
         "because of Verilog's **expression sizing** rule: the comparison "
         "is evaluated in the width of its widest operand - two bits - so "
         "the carry of the addition is kept (Chapter 4). `!==` is the "
         "4-state case inequality, so an `x` output also counts as a "
         "mismatch."])
    p("Compile and run it with Icarus Verilog, the event-driven simulator used "
      "for most examples in this book:")
    code(["$ iverilog -g2005 -Wall -o sim c1_hello.v     # compile + elaborate",
          "$ vvp -n sim                                  # run the simulation"])
    out([
        't=1 a=0 b=0 cin=0 | cout=0 sum=0',
        't=2 a=0 b=0 cin=1 | cout=0 sum=1',
        't=3 a=0 b=1 cin=0 | cout=0 sum=1',
        't=4 a=0 b=1 cin=1 | cout=1 sum=0',
        't=5 a=1 b=0 cin=0 | cout=0 sum=1',
        't=6 a=1 b=0 cin=1 | cout=1 sum=0',
        't=7 a=1 b=1 cin=0 | cout=1 sum=0',
        't=8 a=1 b=1 cin=1 | cout=1 sum=1',
        'PASS',
        'c1_hello.v:29: $finish called at 8 (1ns)',
    ], "Output (Icarus Verilog 12). The testbench "
        "decides PASS/FAIL by itself - nobody has to read waveforms.")
    p("The same source runs unchanged on Verilator, which translates the "
      "design into C++ and compiles it. The `--timing` option enables delays "
      "and event controls in the testbench:")
    code(["$ verilator --binary --timing -Wall --top-module tb_full_adder fa_tb.v",
          "$ ./obj_dir/Vtb_full_adder"])
    out([
        't=8 a=1 b=1 cin=1 | cout=1 sum=1',
        'PASS',
        '- fa_tb.v:29: Verilog $finish',
    ], "Last lines of the Verilator 5.020 run of the "
        "same testbench (copied to fa_tb.v): identical result.")
    p("Finally, a synthesis tool reads only the design module and produces a "
      "gate-level **netlist**, itself written in (structural) Verilog. Asking "
      "Yosys to map onto simple AND/OR/XOR gates gives:")
    code(["$ yosys -q -p \"read_verilog fa.v; synth -top full_adder;"
          " abc -g AND,OR,XOR; opt_clean; write_verilog -noattr fa_net.v\""])
    out([
        '  assign cout = _0_ | _2_;',
        '  assign _0_ = b & a;',
        '  assign _1_ = b ^ a;',
        '  assign _2_ = cin & _1_;',
        '  assign sum = cin ^ _1_;',
    ], "Excerpt of the netlist written by Yosys "
        "0.33: five gates. The testbench, `initial`, `$display` and `#1` "
        "are not synthesizable and are simply not part of this flow.")
    box("intuit", "One source, three readers",
        "The adder was consumed by an event-driven simulator, a cycle-based "
        "simulator and a synthesis tool, and each produced something "
        "consistent with the others. That consistency is not automatic - it "
        "holds because the design uses only constructs whose simulation "
        "semantics match their synthesis semantics. Chapter 11 catalogues the "
        "constructs where they do not.")

    # ------------------------------------------------------------------
    h2("The same example in SystemVerilog")
    p("SystemVerilog is a superset, so the Verilog above is already legal "
      "SystemVerilog. Rewritten in the style used in modern projects, the "
      "same idea looks like this - a parameterized adder and a "
      "random-stimulus testbench with an immediate assertion:")
    code([
        'module adder #(parameter int W = 8) (',
        '  input  logic [W-1:0] a, b,',
        '  output logic [W:0]   sum',
        ');',
        '  always_comb sum = a + b;                // SV: always_comb, logic',
        'endmodule',
        '',
        'module tb_adder;',
        '  localparam int W = 8;',
        '  logic [W-1:0] a, b;',
        '  logic [W:0]   sum;',
        '  int           errors = 0;               // SV: 2-state int',
        '  adder #(.W(W)) dut (.*);                // SV: .* port connection',
        '  initial begin',
        '    repeat (1000) begin',
        "      a = W'($urandom);  b = W'($urandom); // SV: size cast",
        '      #1;',
        '      assert (sum == a + b)               // SV: immediate assertion',
        '        else $error("a=%0d b=%0d sum=%0d", a, b, sum);',
        "      errors += int'(sum != a + b);       // SV: += and a type cast",
        '    end',
        '    $display("%s: 1000 random vectors, %0d errors", (errors != 0) ? "FAIL" : "PASS", errors);',
        '    $finish;',
        '  end',
        'endmodule',
    ], "File c1_sv.sv. Features new in SystemVerilog are "
         "marked; each is explained in Parts III and IV.")
    out([
        'PASS: 1000 random vectors, 0 errors',
        'c1_sv.sv:23: $finish called at 1000 (1s)',
    ], "Output with Icarus Verilog 12 "
        "(iverilog -g2012 -Wall).")
    out([
        'PASS: 1000 random vectors, 0 errors',
        '- c1_sv.sv:23: Verilog $finish',
    ], "Output with Verilator 5.020 "
        "(verilator --binary --timing --assert).")
    box("warn", "Pitfall: tool bugs are real",
        "While preparing this example, an earlier version that incremented "
        "`errors++` inside the assertion's `else begin ... end` action block "
        "failed to compile in Verilator 5.020 with `--assert` (a C++ code "
        "generation error) and reported 1000 false failures without it. The "
        "version shown is legal in both forms, but the lesson is general: "
        "when a result looks impossible, reproduce it on a second simulator "
        "before you debug the design.")

    # ------------------------------------------------------------------
    h2("Conventions used in this book")
    bul(["Code in grey boxes is complete and was compiled; code followed by a "
         "green box was also __run__, and the green box is the verbatim "
         "output of the tool named in its caption.",
         "Code that needs a commercial simulator (constraint solving, "
         "covergroups, concurrent assertions, UVM) is shown without output "
         "and says so.",
         "`reg` and `wire` are used in the Verilog chapters; from Part III on, "
         "designs use `logic`. Both styles appear in real projects, and you "
         "must read both fluently.",
         "PITFALL boxes flag simulation/synthesis mismatches and portability "
         "problems; EXPERT boxes give the interview-grade detail behind a "
         "rule."])

    h2("Summary")
    bul(["An HDL describes concurrent hardware in simulated time with "
         "4-state, fixed-width values; it has two readers - simulation and "
         "synthesis - whose semantics must agree.",
         "Verilog (Gateway, 1984) was standardised as IEEE 1364-1995, greatly "
         "extended in 1364-2001 and finalised in 1364-2005.",
         "SystemVerilog (Accellera 3.0/3.1a from Superlog, Vera, OVA and "
         "DirectC; IEEE 1800-2005) merged with Verilog in 1800-2009; 2012 "
         "added interface classes and soft constraints; 2017 is the "
         "reference version; 2023 is the newest.",
         "VHDL is the strongly typed alternative; SystemVerilog dominates ASIC "
         "design and nearly all ASIC verification through UVM.",
         "Each flow step uses a different language subset: synthesizable RTL, "
         "full SV for DV, SVA for formal, structural Verilog with primitives "
         "and specify blocks for gate-level and DFT.",
         "A testbench is just a module; a self-checking one decides pass or "
         "fail itself."])

    h2("Exercises")
    bul(["List four constructs that belong only to the verification subset "
         "and four that are synthesizable. For each, say which flow step "
         "(Section 1.6) consumes it.",
         "Remove the `#1` from the testbench in Section 1.7 and predict what "
         "is printed. Run it and explain the result in terms of processes "
         "and time.",
         "Change the check to `if ({cout, sum} !== {a + b + cin})` (note "
         "the extra braces). Predict the outcome before running it, then "
         "explain it using the sizing rule you will meet in Chapter 4.",
         "Which revision of the standard introduced each of: ANSI port "
         "lists, `signed`, `uwire`, classes, interface classes, soft "
         "constraints?",
         "Your team receives an IP block written in VHDL and a UVM "
         "testbench. Describe how the two are simulated together and which "
         "tools can do it.",
         "Synthesize the full adder with Yosys without the `abc -g` option "
         "and compare the cell count with Section 1.7. Why can the counts "
         "differ?"], ordered=True)


# =============================================================================
#        Chapter 2 - Lexical conventions, modules, ports and hierarchy
# =============================================================================
def _ch2():
    chapter("Lexical Conventions, Modules, Ports and Hierarchy")
    p("Before a simulator can do anything with a design it must **parse** "
      "the text into tokens, **elaborate** the module hierarchy - create "
      "every instance, resolve every parameter, connect every port - and only "
      "then **simulate**. This chapter covers the first two steps: the "
      "lexical rules that decide what a token is, the structure of a module, "
      "the many ways to declare and connect ports, and the hierarchy that "
      "results. These are the rules you use on every line you write, and "
      "most of the confusing compile errors and silent connection bugs of a "
      "beginner come from them.")

    # ------------------------------------------------------------------
    h2("Lexical conventions")
    p("A Verilog source file is a stream of **tokens**: white space, "
      "comments, operators, numbers, strings, identifiers and keywords. The "
      "language is **case-sensitive** (`Data` and `data` are different "
      "names) and **free-format**: spaces, tabs and newlines separate tokens "
      "but are otherwise ignored, except inside strings and where they "
      "terminate an escaped identifier.")
    tbl(["Token class", "Rules", "Examples"],
        [["White space", "Space, tab, newline, form feed; separates tokens",
          "-"],
         ["Comments", "`//` to end of line; `/* ... */` block comments do "
          "**not** nest (a `/*` inside a block comment is ignored, the first "
          "`*/` ends it)", "`// note`, `/* a */`"],
         ["Operators", "One, two or three characters", "`+ ~& === <<< ?:`"],
         ["Numbers", "Sized or unsized, with optional base and sign "
          "(Chapter 3)", "`8'hFF`, `'b1x0z`, `12`, `4'sd3`, `1.5e-3`"],
         ["Strings", "Double-quoted, one line; escapes `\\n \\t \\\\ \\\" "
          "\\ddd` (octal)", "`\"hello\\n\"`"],
         ["Identifiers", "Letters, digits, `$` and `_`; must start with a "
          "letter or `_`; up to at least 1024 characters", "`clk`, `_tmp`, "
          "`data_$1`, `u_core`"],
         ["Escaped identifiers", "Start with a backslash, end at the first "
          "white space; may contain any printable ASCII character",
          "`\\bus[0] `, `\\a+b `, `\\cpu/alu/q_reg `"],
         ["Keywords", "Reserved, always lower case", "`module wire reg "
          "always begin end`"],
         ["System tasks / functions", "Identifier starting with `$`",
          "`$display`, `$time`, `$signed`"],
         ["Compiler directives", "Grave accent followed by a name",
          "`timescale`, `define`, `ifdef` (Chapter 8)"]],
        widths=[20, 50, 30], bold_first=True)
    code([
        'module tb_lex;',
        '  reg [7:0] \\bus[0] ;          // escaped identifier: the name is  bus[0]',
        '  reg       \\a+b ;             // name is  a+b  (terminated by whitespace)',
        '  reg [7:0] data_$1;           // $ is legal after the first character',
        '  reg [31:0] _big;',
        '  initial begin',
        "    \\bus[0]  = 8'hA5;",
        "    \\a+b     = 1'b1;",
        "    data_$1  = 8'b1010_0101;   // underscores are ignored in numbers",
        "    _big     = 32'd1_000_000;",
        '    $display("%s=%h  %s=%b  data_$1=%h  _big=%0d",',
        '             "\\\\bus[0]", \\bus[0] , "\\\\a+b", \\a+b , data_$1, _big);',
        '    /* block comment',
        '       // nested line comment inside a block comment is fine */',
        '    $display("12\'o7_7 = %b   \'hF = %b", 12\'o7_7, \'hF);',
        '  end',
        'endmodule',
    ], "Identifiers, escaped identifiers, underscores in "
         "numbers and comments (c2_lex.v).")
    out([
        '\\bus[0]=a5  \\a+b=1  data_$1=a5  _big=1000000',
        "12'o7_7 = 000000111111   'hF = 00000000000000000000000000001111",
    ], "Output (Icarus Verilog 12). The backslash and "
        "the terminating space are not part of the name.")
    p("Three details in this example trip people up:")
    bul(["An escaped identifier **must** be followed by white space: `\\a+b ;` "
         "is the identifier `a+b` followed by `;`. Without the space, the "
         "semicolon would become part of the name.",
         "`\\cpu ` and `cpu` are the **same** identifier - escaping a name "
         "that would be legal anyway changes nothing.",
         "The octal literal `12'o7_7` is `000_000_111_111`: underscores are "
         "ignored inside numbers, and each octal digit is three bits."])
    box("expert", "Where escaped identifiers come from",
        "You will rarely type an escaped identifier, but you will read "
        "thousands of them. Synthesis tools flatten the hierarchy and keep "
        "the original names in the netlist: a flip-flop that was bit 3 of "
        "`q_reg` inside instance `u_alu` of `u_cpu` becomes a cell named "
        "`\\u_cpu/u_alu/q_reg[3] `. Gate-level simulation, SDF "
        "back-annotation, DFT scan-chain reports and ECO scripts all refer to "
        "such names, and a missing trailing space in a hand-written force or "
        "SDF path is a classic gate-level debugging trap.")
    box("warn", "Pitfall: SystemVerilog keywords in old Verilog code",
        "SystemVerilog reserves many new keywords: `logic`, `bit`, `byte`, "
        "`int`, `string`, `class`, `interface`, `program`, `priority`, "
        "`unique`, `do`, `break`, `final`, `ref`, `type`, `chandle` and more. "
        "Legacy Verilog that uses them as signal names (`wire bit;`, "
        "`reg final;`) fails to compile in SystemVerilog mode. The directive "
        "pair `begin_keywords \"1364-2005\"` / `end_keywords` tells the "
        "compiler which keyword set applies to a region of code (Chapter 8); "
        "the robust fix is to rename the signals.")

    # ------------------------------------------------------------------
    h2("Modules")
    p("A **module** is the unit of design. It is a __definition__, like a "
      "class or a schematic symbol: nothing exists until the module is "
      "**instantiated**, and it can be instantiated any number of times, "
      "each instance having its own copy of every net, variable and "
      "process inside it. The general shape is:")
    code([
        "module name #(parameter_list)        // optional parameters (Chapter 7)",
        "             (port_list);            // ports",
        "  // module items, in any order (declare before use):",
        "  //   net and variable declarations      wire, reg, integer ...",
        "  //   parameter / localparam              Chapter 7",
        "  //   continuous assignments              assign ...",
        "  //   procedural blocks                   initial, always",
        "  //   module / primitive instances        and u1 (y, a, b); sub u2 (...);",
        "  //   generate regions                    Chapter 7",
        "  //   task and function definitions       Chapter 6",
        "  //   specify blocks                      Chapter 9",
        "endmodule",
    ], "Module skeleton (Verilog-2005).")
    bul(["Module definitions cannot be nested in Verilog (SystemVerilog allows "
         "nested module declarations, rarely used). All modules live in one "
         "global name space, the **definitions name space**, so two modules "
         "with the same name anywhere in the compiled files collide.",
         "Declaration order matters in one direction only: a net or variable "
         "must be declared before it is referenced (implicit nets aside, "
         "Section 2.6). Modules themselves may be instantiated before their "
         "definition appears, even in a later file.",
         "Everything inside a module runs **concurrently**: the order of "
         "`assign` statements, `always` blocks and instances in the text has "
         "no meaning for the hardware described (and should have none in "
         "simulation - Chapter 5 shows where it leaks)."])

    h3("Compilation, elaboration, simulation")
    tbl(["Phase", "What happens", "Typical errors"],
        [["Parse / compile", "Tokenise, check syntax, build a model of each "
          "module", "Syntax errors, undeclared identifiers (with "
          "`default_nettype none`)"],
         ["Elaborate", "Pick the top module(s), instantiate the tree, "
          "evaluate parameters and generate blocks, connect ports, resolve "
          "hierarchical names", "Unknown module, port mismatch, width "
          "warnings, multiple drivers on a `uwire` or variable"],
         ["Simulate", "Execute processes under the event scheduler",
          "Functional bugs, races, `x` propagation, `$fatal`"]],
        widths=[16, 50, 34], bold_first=True)
    p("Icarus runs compile and elaborate in `iverilog` and simulation in "
      "`vvp`; commercial simulators expose the same split as separate "
      "commands (for example `xrun` does all three, `vcs` compiles and "
      "elaborates into an executable `simv`).")

    # ------------------------------------------------------------------
    h2("Port declarations: ANSI and non-ANSI style")
    p("Verilog-1995 declared ports twice: the header lists only the names, "
      "and the body gives each port a direction, and optionally a width and "
      "a type. Verilog-2001 introduced the **ANSI style** (named after ANSI C "
      "function prototypes), where direction, type, signedness and width "
      "all go in the header. A module must use one style or the other; "
      "mixing them in one header is illegal.")
    code([
        '// Non-ANSI (Verilog-1995) header: port list, then declarations in the body',
        'module mux2_1995 (y, a, b, sel);',
        '  output y;',
        '  input  a, b, sel;',
        '  wire   y;',
        '  assign y = sel ? b : a;',
        'endmodule',
        '',
        '// ANSI (Verilog-2001) header: direction, type and width in the port list',
        'module mux2 (',
        '  input  wire [3:0] a, b,',
        '  input  wire       sel,',
        '  output wire [3:0] y',
        ');',
        '  assign y = sel ? b : a;',
        'endmodule',
        '',
        'module tb_ports;',
        "  reg  [3:0] a = 4'h3, b = 4'hC;",
        "  reg        sel = 1'b1;",
        '  wire [3:0] y_ord, y_name, y_dot, y_star;',
        '  wire       y1;',
        '',
        '  mux2      u_ord  (a, b, sel, y_ord);                        // by position (fragile)',
        '  mux2      u_name (.y(y_name), .sel(sel), .a(a), .b(b));     // by name (any order)',
        '  mux2      u_dot  (.a, .b, .sel, .y(y_dot));                 // SV .name implicit',
        '  mux2      u_star (.y(y_star), .*);                          // SV .* wildcard',
        '  mux2_1995 u_old  (.y(y1), .a(a[0]), .b(b[0]), .sel(sel));',
        '',
        '  initial begin',
        '    #1 $display("ord=%h name=%h dot=%h star=%h old=%b", y_ord, y_name, y_dot, y_star, y1);',
        '  end',
        'endmodule',
    ], "Both header styles, and the four ways to "
         "connect ports (c2_ports.sv, compiled with -g2012 for the SV "
         "`.name` and `.*` forms).")
    out([
        'ord=c name=c dot=c star=c old=0',
    ], "Output (Icarus Verilog 12): all connection "
        "styles produce the same hardware.")
    tbl(["Direction", "Inside the module it may be", "Driven from outside by",
         "Notes"],
        [["`input`", "A net (Verilog). SV also allows a variable, which then "
          "may not be written inside", "Any expression", "Default kind is a "
          "net (`wire`); even `input logic a` is a net in SV"],
         ["`output`", "A net or a variable (`output reg [7:0] q`)",
          "Must connect to a net (Verilog) or net/variable (SV)",
          "Driving an output from two places is a multiple-driver bug"],
         ["`inout`", "A net only - never a variable", "A net only",
          "Bidirectional; resolved like any multi-driver net"]],
        widths=[12, 34, 26, 28], bold_first=True)
    box("tip", "House style for new code",
        "Use ANSI headers, one port per line, grouped by interface (clock and "
        "reset first, then each bus), with a comment per port. Declare "
        "outputs as `output logic` (SV) or `output reg`/`output wire` "
        "(Verilog) explicitly rather than relying on the default. Lint tools "
        "and IP-XACT generators parse this layout easily, and code review is "
        "far easier when the header is the documentation.")

    # ------------------------------------------------------------------
    h2("Bidirectional ports and tri-state buses")
    p("An `inout` port is a net that both the module and the outside world "
      "may drive. When several drivers are active the net **resolves** "
      "their values (Chapter 3): a driver that outputs `z` - high impedance - "
      "is effectively disconnected. The classic use is an I/O pad.")
    code([
        'module bidir_pad (',
        '  inout  wire       pad,      // bidirectional: must be a net',
        '  input  wire       oe,       // output enable',
        '  input  wire       dout,     // value to drive when oe=1',
        '  output wire       din       // what is on the pad',
        ');',
        "  assign pad = oe ? dout : 1'bz;   // tri-state driver",
        '  assign din = pad;',
        'endmodule',
        '',
        'module tb_inout;',
        '  wire bus;',
        '  reg  oe_a, d_a, oe_b, d_b;',
        '  wire in_a, in_b;',
        '  bidir_pad A (.pad(bus), .oe(oe_a), .dout(d_a), .din(in_a));',
        '  bidir_pad B (.pad(bus), .oe(oe_b), .dout(d_b), .din(in_b));',
        '  initial begin',
        '    $display("oe_a d_a oe_b d_b | bus in_a in_b");',
        "    {oe_a, d_a, oe_b, d_b} = 4'b0000; #1 show;",
        "    {oe_a, d_a, oe_b, d_b} = 4'b1100; #1 show;",
        "    {oe_a, d_a, oe_b, d_b} = 4'b0010; #1 show;",
        "    {oe_a, d_a, oe_b, d_b} = 4'b1110; #1 show;    // contention",
        '  end',
        '  task show;',
        '    $display("  %b    %b    %b    %b  |  %b    %b    %b",',
        '             oe_a, d_a, oe_b, d_b, bus, in_a, in_b);',
        '  endtask',
        'endmodule',
    ], "Two bidirectional pads on one shared net "
         "(c2_inout.v).")
    out([
        'oe_a d_a oe_b d_b | bus in_a in_b',
        '  0    0    0    0  |  z    z    z',
        '  1    1    0    0  |  1    1    1',
        '  0    0    1    0  |  0    0    0',
        '  1    1    1    0  |  x    x    x',
    ], "Output (Icarus Verilog 12). With nobody "
        "driving, the bus floats at `z`; two conflicting drivers give `x`.")
    box("warn", "Pitfall: tri-states inside an ASIC",
        "Internal tri-state buses are almost never used in modern ASIC "
        "design: they complicate timing analysis, testability (scan) and "
        "equivalence checking, and a floating bus burns power. Synthesis "
        "tools typically convert internal tri-states into multiplexers or "
        "flag them. `inout` belongs at the chip boundary (pads, where the "
        "library provides bidirectional I/O cells) and in testbenches that "
        "model open-drain buses such as I2C. Inside the core, use separate "
        "input and output buses with an explicit mux.")

    # ------------------------------------------------------------------
    h2("Connecting ports")
    p("An instance connects each port of the child module to an expression "
      "in the parent. Verilog offers two styles and SystemVerilog adds two "
      "shorthands:")
    tbl(["Style", "Syntax", "Rules and risks"],
        [["By position (ordered)", "`mux2 u (a, b, sel, y);`", "Matches the "
          "order of the port list. Legal but fragile: reordering the "
          "module's ports silently reconnects every instance. Acceptable "
          "only for gate primitives and tiny cells"],
         ["By name", "`mux2 u (.a(a), .y(y), ...);`", "Order-independent, "
          "self-documenting; the industry default. `.p()` leaves port `p` "
          "explicitly unconnected"],
         ["Implicit `.name` (SV)", "`mux2 u (.a, .b, .sel, .y(y2));`",
          "`.a` means `.a(a)`. A net or variable named `a` must exist in the "
          "parent and be of a compatible type and **equal width**; no "
          "implicit net is created"],
         ["Wildcard `.*` (SV)", "`mux2 u (.y(y2), .*);`", "Connects every "
          "remaining port to a same-named signal. Same checks as `.name`. "
          "Explicit connections listed with it take precedence. Great for "
          "testbenches and wrappers; some teams ban it in RTL because the "
          "connectivity is invisible in the text"]],
        widths=[18, 30, 52], bold_first=True)
    p("A port connection behaves like a continuous assignment from the "
      "driver side to the receiving side. Consequently:")
    bul(["If widths differ, the value is **zero-extended or truncated** "
         "exactly as in an assignment (sign-extended if the source is "
         "signed). The LRM makes this legal; every lint tool warns about it, "
         "and so should your review checklist.",
         "An unconnected `input` floats at `z`; inside the module a `z` on "
         "a gate input reads as `x`, so a forgotten connection usually "
         "shows up as `x` propagation in simulation. Synthesis may tie it "
         "off - or not - so fix every unconnected input warning.",
         "An unconnected `output` is simply unused, which is legal and "
         "common (`.overflow()`)."])
    box("expert", "Interview question: can an output port be a variable in "
        "the parent?",
        "In Verilog, the parent side of an `output` or `inout` connection "
        "must be a net, because a port connection is a continuous "
        "assignment and only nets can be continuously driven. SystemVerilog "
        "relaxes this: a variable may be connected to an output port, "
        "provided it has no other driver (a variable written by a port "
        "connection or a continuous assignment may have only that one "
        "driver). This is one reason `logic` is so convenient: it can be "
        "used on either side.")

    # ------------------------------------------------------------------
    h2("Implicit nets and the default_nettype directive")
    p("Verilog creates a net **implicitly** when an undeclared identifier "
      "appears (a) in a port connection of an instance, or (b) on the "
      "left-hand side of a continuous assignment. The implicit net is a "
      "scalar (1-bit) `wire`. This was a convenience for gate-level netlists, "
      "but in RTL it turns every typo into a silent bug:")
    code([
        'module and_or (input wire [3:0] a, b, output wire [3:0] y);',
        '  wire [3:0] t;',
        "  assign tmp = a & b;          // typo: 'tmp' instead of 't' -> implicit 1-bit wire!",
        "  assign y   = t | 4'b0000;",
        'endmodule',
        'module tb_implicit;',
        "  reg [3:0] a = 4'b1100, b = 4'b1010; wire [3:0] y;",
        '  and_or u (.a(a), .b(b), .y(y));',
        '  initial #1 $display("y = %b  (expected 1000)", y);',
        'endmodule',
    ], "A one-character typo (c2_implicit.v).")
    out([
        "c2_implicit.v:3: warning: implicit definition of wire 'tmp'.",
        'y = xxxx  (expected 1000)',
    ], "Icarus warns under -Wall, but the "
        "simulation runs and produces x.")
    p("The typo creates a 1-bit wire `tmp` that receives the truncated AND "
      "result, while the intended `t` is never driven, stays `z`, and "
      "`z | 0` evaluates to `x`. In a larger design, the effect is often "
      "subtler - a bus that works for bit 0 only. The cure is the compiler "
      "directive `default_nettype none`, which turns implicit net creation "
      "into an error:")
    code([
        '`default_nettype none',
        'module and_or (input wire [3:0] a, b, output wire [3:0] y);',
        '  wire [3:0] t;',
        "  assign tmp = a & b;          // typo: 'tmp' instead of 't' -> implicit 1-bit wire!",
        "  assign y   = t | 4'b0000;",
    ], "The same file with "
         "`default_nettype none` at the top (c2_implicit_none.v); the "
         "directive is set back to `wire` before the testbench.")
    out([
        'c2_implicit_none.v:4: error: Net tmp is not defined in this context.',
        '1 error(s) during elaboration.',
    ], "Output (Icarus Verilog 12): the typo "
        "is now a compile error.")
    out([
        "%Warning-IMPLICIT: c2_implicit.v:3:10: Signal definition not found, creating implicitly: 'tmp'",
    ], "Verilator 5.020 `--lint-only -Wall` "
        "on the original file flags it too (first message shown).")
    box("warn", "Pitfall: default_nettype none leaks across files",
        "Compiler directives are not scoped to a file or module: they remain "
        "in effect for all following source text in the same compilation, "
        "including files compiled afterwards. Once `default_nettype none` is "
        "active, every port must be declared with an explicit type in the "
        "ANSI header (`input wire a`, not just `input a`) and third-party "
        "code that relies on implicit nets breaks. The usual convention is "
        "to put `default_nettype none` at the top of each of your files and "
        "`default_nettype wire` at the bottom.")

    # ------------------------------------------------------------------
    h2("Hierarchy, top-level modules and hierarchical references")
    p("Elaboration builds a tree of instances. Every instance has a "
      "**hierarchical path** made of instance names separated by dots, "
      "starting with a **top-level module**: any module that is compiled but "
      "never instantiated. A simulation may have several tops (a testbench "
      "and a separate monitor or a `bind` target), and the format specifier "
      "`%m` prints the path of the scope that executes it.")
    code([
        'module counter (input wire clk, rst, output reg [3:0] q);',
        '  reg [3:0] next;                                // internal, not a port',
        "  always @* next = q + 4'd1;",
        "  always @(posedge clk) q <= rst ? 4'd0 : next;",
        '  initial $display("instance path: %m");',
        'endmodule',
        '',
        'module top;',
        '  reg clk = 0, rst = 1;',
        '  wire [3:0] q0, q1;',
        '  counter c0 (.clk(clk), .rst(rst), .q(q0));',
        '  counter c1 (.clk(clk), .rst(rst), .q(q1));',
        '  always #5 clk = ~clk;',
        '  initial begin',
        '    #12 rst = 0;',
        '    #30 $display("c0.q=%0d  c0.next=%0d (peeked)", q0, top.c0.next);  // downward ref',
        "    force top.c1.next = 4'd9;                    // DV: poke an internal node",
        '    #10 $display("c1.q=%0d after force", q1);',
        '    release top.c1.next;',
        '    $finish;',
        '  end',
        'endmodule',
        '',
        'module monitor_top;                              // never instantiated -> 2nd top',
        '  initial #20 $display("%m sees top.c0.q = %0d", top.c0.q);   // cross-top reference',
        'endmodule',
    ], "Two instances of one module, a second top-level "
         "module, downward and cross-top hierarchical references, and "
         "`force`/`release` (c2_hier.v).")
    out([
        'instance path: top.c0',
        'instance path: top.c1',
        'monitor_top sees top.c0.q = 1',
        'c0.q=3  c0.next=4 (peeked)',
        'c1.q=9 after force',
        'c2_hier.v:20: $finish called at 52 (1s)',
    ], "Output (Icarus Verilog 12). `monitor_top` is "
        "a second top: nothing instantiates it.")
    p("Any object can be referenced by its full path from anywhere in the "
      "design: `top.c0.next` reads a signal that is not a port. Names are "
      "resolved in a precise order: a reference `a.b.c` is first looked "
      "up **downward** from the current scope (is there a child instance "
      "`a`?), then **upward** - the name `a` is searched for in the "
      "parent, grandparent and so on - and finally as a top-level module "
      "name. Upward resolution is what lets `c0.next` inside `top` and "
      "`top.c0.next` anywhere else refer to the same object.")
    tbl(["Use", "Where hierarchical references are normal"],
        [["Testbench probes", "Reading internal state for checking or debug "
          "(`top.dut.u_fifo.count`)"],
         ["`force` / `release`", "Fault injection, bypassing a PLL or a "
          "clock gate in simulation, gate-level debugging"],
         ["Backdoor memory access", "`$readmemh` into `tb.dut.u_rom.mem`, "
          "UVM register backdoor paths"],
         ["Assertions", "SVA `bind` attaches a checker module inside an RTL "
          "instance without editing the RTL (Chapter 22)"]],
        widths=[25, 75], bold_first=True)
    box("warn", "Pitfall: hierarchical references in RTL",
        "Synthesis tools generally do not support hierarchical references "
        "across module boundaries in design code (some accept limited "
        "downward references), and they break encapsulation: a renamed "
        "instance silently breaks a testbench probe only at elaboration "
        "time. Keep them out of RTL; in testbenches, collect them in one "
        "place (a probe module, or an interface bound into the design) so "
        "that a hierarchy change is fixed once.")

    # ------------------------------------------------------------------
    h2("Multiple instances and arrays of instances")
    p("Instantiating a module several times is just several instance "
      "statements. For regular structures, Verilog-2001 added **arrays of "
      "instances**: a range after the instance name creates one instance per "
      "index. Port connections are distributed by width: if a connected "
      "expression has exactly `N` times the port width, each instance gets "
      "its own slice (the leftmost instance index gets the leftmost slice); "
      "if it has exactly the port width, it is replicated to every "
      "instance; any other width is an error.")
    code([
        'module nand2 (output wire y, input wire a, b);',
        '  assign y = ~(a & b);',
        'endmodule',
        '',
        'module tb_array;',
        "  reg  [3:0] a = 4'b1100, b = 4'b1010;",
        "  reg        en = 1'b1;",
        '  wire [3:0] y, g;',
        '  // Array of instances: u[3], u[2], u[1], u[0]; vectors are split one bit per instance',
        '  nand2 u [3:0] (.y(y), .a(a), .b(b));',
        '  // A 1-bit signal on an array port is replicated to every instance',
        '  nand2 gate [3:0] (.y(g), .a(a), .b(en));',
        '  initial #1 $display("y = %b   g = %b   u[2].y = %b", y, g, u[2].y);',
        'endmodule',
    ], "Arrays of instances (c2_array.v).")
    out([
        'y = 0111   g = 0011   u[2].y = 1',
    ], "Output (Icarus Verilog 12). With `en` "
        "replicated, `g = ~(a & 1) = ~a`.")
    p("Arrays of instances are compact but limited: every instance must be "
      "identical and connections follow the slicing rule above. The "
      "`generate` construct (Chapter 7) is the general tool - it can "
      "instantiate conditionally, compute per-instance parameters and "
      "connect arbitrary expressions - and is what most RTL uses today. "
      "Arrays of instances remain common in gate-level netlists and pad "
      "rings.")

    h2("Summary")
    bul(["Verilog is case-sensitive and free-format; block comments do not "
         "nest; escaped identifiers begin with a backslash and end at white "
         "space, and appear everywhere in netlists.",
         "A module is a definition; instances create copies. Compilation, "
         "elaboration and simulation are separate phases with their own "
         "errors.",
         "Use ANSI port headers. Inputs are nets, `inout` ports are always "
         "nets, outputs may be variables.",
         "Connect by name (or `.name`/`.*` in SV); port connections behave "
         "like continuous assignments, so widths are silently extended or "
         "truncated.",
         "Implicit nets turn typos into 1-bit wires; use `default_nettype "
         "none` and reset it at the end of each file.",
         "Hierarchical paths reach any object; they are for testbenches, "
         "`force`, backdoors and binds - not for RTL.",
         "Arrays of instances split or replicate connections by width; "
         "`generate` is the general mechanism."])

    h2("Exercises")
    bul(["Which of these are legal identifiers, and what name does each "
         "declare: `2fast`, `_2fast`, `$fast`, `fast$`, `\\2fast `, "
         "`\\fast `, `\\a b `?",
         "Rewrite `mux2_1995` from Section 2.3 in ANSI style with a "
         "4-bit data path. Then connect a 3-bit signal to its `a` port and "
         "an 8-bit signal to `y`; what happens to the missing and extra "
         "bits, and what does your lint tool report?",
         "Explain why `.*` is safe against the typo of Section 2.6 while "
         "positional connection is not. What error do you get if a port has "
         "no same-named signal in the parent?",
         "In `c2_hier.v`, a module `monitor_top` refers to `top.c0.q`. "
         "Explain how the name is resolved. What changes if you also add a "
         "local instance named `top` inside `monitor_top`?",
         "Build a 16-bit bitwise NAND from `nand2` using (a) an array of "
         "instances and (b) a `generate for` loop (look ahead to Chapter 7). "
         "Compare the hierarchical names of the resulting instances.",
         "Write an open-drain I2C-style bus model with two devices and a "
         "pull-up using `inout` ports, and show that either device can pull "
         "the line low."], ordered=True)


# =============================================================================
#        Chapter 3 - Data types: nets, variables, 4-state, strengths, literals
# =============================================================================
def _ch3():
    chapter("Data Types: Nets, Variables, 4-State Logic, Strengths, Vectors, "
            "Arrays and Literals")
    p("Verilog's data types model two physical things: **wires**, which "
      "carry whatever their drivers put on them, and **storage**, which keeps "
      "a value until something writes a new one. On top of that it layers a "
      "four-valued logic system, a strength system for resolving conflicts "
      "between drivers, arbitrary-width vectors and arrays, and a literal "
      "syntax with precise sizing rules. SystemVerilog adds many more types "
      "(Chapters 12 and 13), but every one of them is defined in terms of "
      "the concepts in this chapter.")

    # ------------------------------------------------------------------
    h2("Two kinds of data object: nets and variables")
    tbl(["", "Nets (`wire`, `tri`, `wand`, ...)", "Variables (`reg`, "
         "`integer`, `real`, `time`, ...)"],
        [["Models", "A physical connection", "A storage element in the model "
          "(not necessarily a flip-flop)"],
         ["Assigned by", "Continuous assignments, primitive and module "
          "outputs, port connections - i.e. **drivers**", "Procedural "
          "assignments in `initial`/`always` blocks, tasks and functions"],
         ["Holds a value?", "No: its value is recomputed from its drivers "
          "(except `trireg`)", "Yes: until the next procedural assignment"],
         ["Multiple sources", "Yes: resolved by the net type and strengths",
          "Last write wins (multiple processes writing one variable is a "
          "race)"],
         ["Undriven value", "`z` (or 0/1 for `tri0`/`tri1`, charge for "
          "`trireg`)", "`x` for `reg`/`integer`/`time`; 0.0 for `real`"],
         ["Default width", "1 bit", "`reg` 1 bit; `integer` 32; `time` 64"]],
        widths=[18, 41, 41], bold_first=True)
    box("key", "reg does not mean register",
        "A `reg` is simply a variable - the name is a historical accident. "
        "Whether it becomes a flip-flop, a latch or plain combinational logic "
        "depends entirely on how it is assigned: `always @(posedge clk) q <= "
        "d;` infers a flip-flop; `always @* y = a & b;` gives an AND gate "
        "whose output is declared `reg`. SystemVerilog replaced the "
        "misleading keyword with `logic` (Chapter 12), which may be used for "
        "both variables and, with a net keyword, nets.")

    # ------------------------------------------------------------------
    h2("The four-state value set")
    tbl(["Value", "Meaning", "Typical origin"],
        [["`0`", "Logic zero, false", "Driver outputs 0"],
         ["`1`", "Logic one, true", "Driver outputs 1"],
         ["`x`", "Unknown: could be 0, 1, or in transition; the simulator "
          "cannot tell", "Uninitialised variable, contention between drivers, "
          "`z` read by a gate input, out-of-range index, division by zero, "
          "timing-check violation in gate-level sim"],
         ["`z`", "High impedance: no driver is driving", "Tri-state driver "
          "disabled, unconnected port, undriven net"]],
        widths=[10, 40, 50], bold_first=True)
    p("`x` is a **simulation** concept. Real hardware always has a 0 or a 1 "
      "(or an analog value in between), and a synthesis tool treats an `x` "
      "you assign as a don't-care it may optimise. That asymmetry is the "
      "root of X-optimism and X-pessimism (Chapter 11): simulation can hide "
      "a bug that silicon exhibits, or show `x` where silicon would be "
      "fine. The operators of Chapter 4 each have exact rules for `x` and "
      "`z` inputs; the general principle is that a result is `x` whenever "
      "the unknown bits could change it.")

    # ------------------------------------------------------------------
    h2("Net types and resolution")
    tbl(["Net type", "Resolution of multiple drivers", "Use"],
        [["`wire`, `tri`", "Standard: equal strength 0 vs 1 gives `x`; `z` "
          "loses to anything", "Default; `tri` documents intended tri-state "
          "use (identical semantics)"],
         ["`wand`, `triand`", "Wired-AND: any 0 wins", "Open-collector "
          "buses (rare)"],
         ["`wor`, `trior`", "Wired-OR: any 1 wins", "Wired-OR buses (rare)"],
         ["`tri0`, `tri1`", "Like `wire`, but reads 0 / 1 (pull strength) "
          "when all drivers are `z`", "Pull-down / pull-up modelling, "
          "testbenches"],
         ["`supply0`, `supply1`", "Constant 0 / 1 at supply strength",
          "Ground and power in netlists and switch-level models"],
         ["`trireg`", "Stores its last driven value as a **charge** when "
          "all drivers go to `z`; charge decays only if a decay time is "
          "given", "Switch-level models of dynamic nodes, precharged buses"],
         ["`uwire` (2005)", "Unresolved: more than one driver is an "
          "elaboration error", "Enforcing single-driver connectivity"]],
        widths=[18, 48, 34], bold_first=True)
    p("The following testbench drives every net type from two continuous "
      "assignments and walks through all combinations of driven values:")
    code([
        'module tb_nets;',
        '  reg  d1, d2;                       // values placed on two drivers',
        '  wire w;   wand wa;   wor wo;   tri0 t0;   tri1 t1;',
        '  assign w = d1;   assign w = d2;    // two continuous drivers on each net',
        '  assign wa = d1;  assign wa = d2;',
        '  assign wo = d1;  assign wo = d2;',
        '  assign t0 = d1;  assign t0 = d2;',
        '  assign t1 = d1;  assign t1 = d2;',
        '  integer i, j;',
        '  reg [3:0] v [0:3];',
        '  initial begin',
        "    v[0] = 0; v[1] = 1; v[2] = 1'bx; v[3] = 1'bz;",
        '    $display("d1 d2 | wire wand wor tri0 tri1");',
        '    for (i = 0; i < 4; i = i + 1)',
        '      for (j = i; j < 4; j = j + 1) begin',
        '        d1 = v[i]; d2 = v[j]; #1;',
        '        $display(" %b  %b |  %b    %b    %b    %b    %b", d1, d2, w, wa, wo, t0, t1);',
        '      end',
        '  end',
        'endmodule',
    ], "Two drivers on each net type (c3_nets.v).")
    out([
        'd1 d2 | wire wand wor tri0 tri1',
        ' 0  0 |  0    0    0    0    0',
        ' 0  1 |  x    0    1    x    x',
        ' 0  x |  x    0    x    x    x',
        ' 0  z |  0    0    0    0    0',
        ' 1  1 |  1    1    1    1    1',
        ' 1  x |  x    x    1    x    x',
        ' 1  z |  1    1    1    1    1',
        ' x  x |  x    x    x    x    x',
        ' x  z |  x    x    x    x    x',
        ' z  z |  z    z    z    0    1',
    ], "Output (Icarus Verilog 12): the resolution "
        "functions of wire, wand, wor, tri0 and tri1.")
    p("For a plain `wire` with two drivers of equal strength, the result is "
      "given by the table below - the one every DV engineer should be able "
      "to write from memory. It is symmetric, `z` is the identity, and any "
      "disagreement produces `x`.")
    tbl(["wire", "0", "1", "x", "z"],
        [["**0**", "0", "x", "x", "0"],
         ["**1**", "x", "1", "x", "1"],
         ["**x**", "x", "x", "x", "x"],
         ["**z**", "0", "1", "x", "z"]],
        widths=[20, 20, 20, 20, 20], caption="Resolution of two equal-"
        "strength drivers on a wire/tri net.")
    p("A `uwire` refuses a second driver at elaboration time, which is "
      "exactly what you want for a signal that must have one source:")
    code([
        'module tb_uwire;',
        '  reg a = 1, b = 0;',
        '  uwire u;',
        '  assign u = a;',
        '  assign u = b;       // second driver on a uwire is illegal',
        'endmodule',
    ], "Two drivers on a uwire (c3_uwire.v).")
    out([
        'c3_uwire.v:5: error: Unresolved net/uwire u cannot have multiple drivers.',
        '1 error(s) during elaboration.',
    ], "Icarus Verilog 12 rejects the design. (Verilator "
        "5.020 --lint-only accepted this file silently.)")
    box("expert", "Why SystemVerilog made single drivers the default for "
        "variables",
        "Resolved nets make multiple drivers legal, so a copy-paste error "
        "that drives a bus from two `assign` statements simply produces `x` "
        "at run time - if the two ever disagree during the test. "
        "SystemVerilog attacks this from the other side: a variable (`logic` "
        "without a net keyword) may be written by **either** any number of "
        "procedural blocks **or** exactly one continuous driver, and "
        "`always_comb`/`always_ff` outputs may not be written by any other "
        "process. The tool then reports multiple drivers at compile time. "
        "This is the main reason modern RTL declares almost everything as "
        "`logic` and reserves `wire`/`tri` for genuinely multi-driven nets.")

    # ------------------------------------------------------------------
    h2("Drive strength and charge strength")
    p("When drivers conflict, Verilog compares **strengths** before values. "
      "Each driven value carries a strength for its 0 and its 1; the "
      "stronger driver wins, and equal strengths with opposite values give "
      "`x` (carrying that strength). Eight levels exist:")
    tbl(["Level", "Name", "Keyword (0 / 1)", "Kind", "Typical source"],
        [["7", "Supply", "`supply0` / `supply1`", "Drive", "Power rails"],
         ["6", "Strong", "`strong0` / `strong1`", "Drive", "Default for gates "
          "and continuous assignments"],
         ["5", "Pull", "`pull0` / `pull1`", "Drive", "Pull resistors, `tri0`/"
          "`tri1`, `pullup`/`pulldown` primitives"],
         ["4", "Large", "`large`", "Charge", "`trireg` with large "
          "capacitance"],
         ["3", "Weak", "`weak0` / `weak1`", "Drive", "Weak keepers"],
         ["2", "Medium", "`medium`", "Charge", "Default `trireg` charge"],
         ["1", "Small", "`small`", "Charge", "Small `trireg`"],
         ["0", "High impedance", "`highz0` / `highz1`", "-", "No drive"]],
        widths=[8, 16, 26, 10, 40], bold_first=True)
    p("Strengths are written in parentheses after `assign` or a gate "
      "keyword, one for 0 and one for 1. The format `%v` prints a net's "
      "strength and value as a three-character code (`St0`, `We1`, `PuX`, "
      "`HiZ`...).")
    code([
        'module tb_strength;',
        '  reg  en, d;',
        '  wire bus;',
        '  // An open-drain style bus: a weak pull-up plus a driver that only pulls low',
        "  assign (weak0, weak1)    bus = 1'b1;                    // pull-up resistor model",
        "  assign (strong0, highz1) bus = (en & ~d) ? 1'b0 : 1'b1; // '1' becomes highz1",
        '  wire   x_bus;',
        "  assign (pull0, pull1)    x_bus = 1'b0;                  // two equal-strength",
        "  assign (pull0, pull1)    x_bus = 1'b1;                  // opposite drivers",
        '  supply0 gnd;  supply1 vdd;',
        '  initial begin',
        '    en = 0; d = 0; #1 $display("en=0     : bus=%b %v", bus, bus);',
        '    en = 1; d = 0; #1 $display("en=1 d=0 : bus=%b %v", bus, bus);',
        '    en = 1; d = 1; #1 $display("en=1 d=1 : bus=%b %v", bus, bus);',
        '    $display("pull0 vs pull1: x_bus=%b %v", x_bus, x_bus);',
        '    $display("supply nets   : gnd=%b %v  vdd=%b %v", gnd, gnd, vdd, vdd);',
        '  end',
        'endmodule',
    ], "An open-drain bus with a weak pull-up, a "
         "conflict between equal strengths, and supply nets (c3_str.v).")
    out([
        'en=0     : bus=1 We1',
        'en=1 d=0 : bus=0 St0',
        'en=1 d=1 : bus=1 We1',
        'pull0 vs pull1: x_bus=x PuX',
        'supply nets   : gnd=0 Su0  vdd=1 Su1',
    ], "Output (Icarus Verilog 12) using %v to show "
        "strength.")
    p("The open-drain driver specifies `highz1`, so when it \"drives\" a 1 "
      "it actually drives nothing, and the weak pull-up makes the bus a "
      "weak 1 (`We1`). When it drives 0 at strong strength, it overpowers "
      "the pull-up (`St0`). Two pull-strength drivers of opposite value "
      "resolve to `PuX`: unknown, at pull strength - which would still lose "
      "to a strong driver.")
    h3("trireg and charge storage")
    code([
        "trireg (medium) #(0, 0, 50) node;     // charge decays to x after 50 time units",
        "assign node = en ? d : 1'bz;          // when en falls, node keeps d as a charge",
    ], "A charge-storage net. Shown without output: Icarus Verilog 12 "
       "reports 'sorry: trireg nets not supported'; commercial simulators "
       "support it.")
    p("A `trireg` holds its last driven value, at its charge strength, when "
      "all drivers turn off; the optional third delay is the charge decay "
      "time after which it becomes `x`. Charge strengths (`large`, `medium`, "
      "`small`) only compete with other charge strengths; any driven value "
      "overrides them.")
    box("note", "Who uses strengths today",
        "RTL designers essentially never do: synthesis ignores strengths, and "
        "RTL uses one driver per signal. Strengths matter in **gate-level and "
        "switch-level** models - standard-cell and I/O library Verilog "
        "models, pad rings, pull-ups on bidirectional pins, analog-ish "
        "behavioural models - and in testbenches that model open-drain "
        "buses (I2C, 1-Wire, MDIO). Chapter 9 revisits them with the "
        "`nmos`/`pmos`/`tran` switch primitives.")

    # ------------------------------------------------------------------
    h2("Variables: reg, integer, real, time and realtime")
    tbl(["Type", "Width / encoding", "States", "Signed?", "Initial value",
         "Typical use"],
        [["`reg [n:0]`", "Any width vector", "4", "No, unless `reg signed`",
          "`x`", "All RTL storage and combinational outputs"],
         ["`integer`", "32 bits (at least)", "4", "Yes", "`x`", "Loop "
          "counters, testbench arithmetic"],
         ["`real`", "IEEE 754 double", "2 (no x/z)", "Yes", "0.0",
          "Behavioural and analog models, statistics"],
         ["`realtime`", "Same as `real`", "2", "Yes", "0.0", "Storing "
          "`$realtime` values"],
         ["`time`", "64 bits", "4", "No", "`x`", "Storing `$time` values"]],
        widths=[13, 17, 10, 16, 11, 33], bold_first=True)
    bul(["A variable declaration may include an initial value (`reg [3:0] q = "
         "4'd5;`). In Verilog this behaves like an `initial` assignment at "
         "time 0 - whose ordering relative to other time-0 processes is not "
         "defined (Chapter 5 shows a consequence). In SystemVerilog the "
         "initialiser is applied before any process starts.",
         "`real` variables cannot be bit- or part-selected, cannot be used "
         "as edge-event operands (`@(posedge r)`), and are not "
         "synthesizable. Assigning a real to an integral variable **rounds** "
         "to the nearest integer, ties away from zero (Chapter 4).",
         "An `integer` is equivalent to `reg signed [31:0]`; use it for loop "
         "variables in Verilog-2005 (SystemVerilog code uses `int`, which is "
         "2-state).",
         "In an ASIC, initial values on variables are **not** implemented "
         "(there is no power-on value); only a reset gives a register a "
         "known value. FPGA flows do honour initial values."])

    # ------------------------------------------------------------------
    h2("Vectors, bit-selects and part-selects")
    p("A vector is declared with a range `[msb:lsb]`. The **left** index is "
      "always the most significant bit, whatever its numeric value: "
      "`[7:0]` is the usual \"little-endian\" numbering (MSB has the "
      "highest index), `[0:7]` is \"big-endian\" (MSB is bit 0), and ranges "
      "need not start at zero (`[15:8]`). Values are always transferred "
      "MSB to MSB, so the index numbering matters only when you select "
      "bits.")
    tbl(["Syntax", "Meaning", "Constraints"],
        [["`v[i]`", "Bit-select", "`i` may be a variable; out of range or "
          "`x`/`z` index reads `x`, writes are ignored"],
         ["`v[m:l]`", "Constant part-select", "Both bounds constant; must "
          "follow the declaration direction (`[7:0]` allows `v[5:2]`, not "
          "`v[2:5]`)"],
         ["`v[base +: w]`", "Indexed part-select, ascending: `w` bits "
          "starting at `base` going up", "`w` must be a positive constant; "
          "`base` may be variable"],
         ["`v[base -: w]`", "Indexed part-select, descending: `w` bits "
          "starting at `base` going down", "Same"]],
        widths=[20, 42, 38], bold_first=True)
    code([
        'module tb_vec;',
        '  reg [7:0]  le;              // "little endian": MSB is bit 7',
        '  reg [0:7]  be;              // "big endian"   : MSB is bit 0',
        '  reg [31:0] word;',
        '  reg [15:8] hi;              // ranges need not start at 0',
        '  integer    k;',
        '  initial begin',
        "    le = 8'b1100_0000;  be = 8'b1100_0000;   // assignment is always MSB-to-MSB",
        '    $display("le[7]=%b le[0]=%b | be[0]=%b be[7]=%b", le[7], le[0], be[0], be[7]);',
        "    word = 32'hDEAD_BEEF;",
        '    $display("word[15:8]=%h  word[8+:8]=%h  word[15-:8]=%h",',
        '             word[15:8], word[8+:8], word[15-:8]);',
        '    for (k = 0; k < 4; k = k + 1)',
        '      $display("byte %0d = %h", k, word[k*8 +: 8]);     // variable base, constant width',
        "    be = 8'b0000_1111;",
        '    $display("be[0+:4]=%b (bits 0..3)  be[7-:4]=%b (bits 4..7)", be[0+:4], be[7-:4]);',
        "    hi = 8'hA5;",
        '    $display("hi[15]=%b hi[8]=%b  out-of-range hi[3]=%b", hi[15], hi[8], hi[3]);',
        '    k = 40;',
        '    $display("word[k] with k=40 -> %b ; word[k+:4] -> %b", word[k], word[k+:4]);',
        '  end',
        'endmodule',
    ], "Endianness, indexed part-selects and "
         "out-of-range selects (c3_vec.v).")
    out([
        'c3_vec.v:18: warning: Constant bit select [3] is before vector hi[15:8].',
        "c3_vec.v:18:        : Replacing select with a constant 1'bx.",
        'le[7]=1 le[0]=0 | be[0]=1 be[7]=0',
        'word[15:8]=be  word[8+:8]=be  word[15-:8]=be',
        'byte 0 = ef',
        'byte 1 = be',
        'byte 2 = ad',
        'byte 3 = de',
        'be[0+:4]=0000 (bits 0..3)  be[7-:4]=1111 (bits 4..7)',
        'hi[15]=1 hi[8]=1  out-of-range hi[3]=x',
        'word[k] with k=40 -> x ; word[k+:4] -> xxxx',
    ], "Output (Icarus Verilog 12), including its "
        "compile-time warning for the constant out-of-range select.")
    p("For a little-endian vector, `v[b +: w]` is `v[b+w-1 : b]` and "
      "`v[b -: w]` is `v[b : b-w+1]`. The indexed forms exist because "
      "Verilog does not allow a part-select with two variable bounds "
      "(`v[k*8+7 : k*8]` is illegal - the width must be constant); "
      "`v[k*8 +: 8]` expresses the same byte lane with a constant width "
      "and a variable base, which synthesizes to a multiplexer.")
    box("warn", "Pitfall: +: on a big-endian vector",
        "For `reg [0:7] be`, `be[0 +: 4]` is `be[0:3]` - the four **most** "
        "significant bits - because `+:` counts upward in index, and index 0 "
        "is the MSB of a big-endian vector. The output above shows it. Mixing "
        "endianness is legal but a rich source of byte-lane bugs; most "
        "coding standards require `[N-1:0]` everywhere, with big-endian "
        "numbering allowed only when matching a protocol specification.")
    p("Two more vector properties: the `signed` keyword (`reg signed [7:0] "
      "s;`) makes arithmetic on the vector two's complement (Chapter 4), "
      "and a selection of a vector - even of all its bits, `s[7:0]` - is "
      "always **unsigned**. The rarely used keywords `vectored` and "
      "`scalared` on a net declaration tell the tool whether bit-selects of "
      "the net may be forced or driven individually.")

    # ------------------------------------------------------------------
    h2("Arrays and memories")
    p("Verilog-2001 allows **arrays** of nets or variables with any number of "
      "**unpacked** dimensions, declared after the name. A one-dimensional "
      "array of `reg` vectors is traditionally called a **memory**. The "
      "dimensions before the name (the vector range) and after it (the array "
      "range) are fundamentally different: the vector is one value you can "
      "operate on as a whole; an array in Verilog can only be accessed one "
      "element at a time.")
    code([
        'module tb_mem;',
        '  reg [7:0] mem [0:15];            // memory: 16 words of 8 bits (unpacked dimension)',
        '  reg [7:0] cube [0:1][0:2];       // 2-D array of bytes (Verilog-2001)',
        '  reg [3:0] nib;',
        '  integer   i, j;',
        '  initial begin',
        '    for (i = 0; i < 16; i = i + 1) mem[i] = i * 17;   // 0x00, 0x11, 0x22, ...',
        '    $display("mem[3]=%h  mem[3][7:4]=%h  mem[3][0]=%b", mem[3], mem[3][7:4], mem[3][0]);',
        '    for (i = 0; i < 2; i = i + 1)',
        "      for (j = 0; j < 3; j = j + 1) cube[i][j] = 8'h10 * i + j;",
        '    $display("cube[1][2]=%h", cube[1][2]);',
        '    $display("mem[16] (out of range read) = %h", mem[16]);',
        "    nib = 4'bxx01;",
        '    $display("mem[nib] with x in index = %h", mem[nib]);',
        '    $writememh("mem.hex", mem, 0, 3);',
        '    $readmemh("mem.hex", mem, 8, 11);                   // copy words 0..3 to 8..11',
        '    $display("after readmemh: mem[8..11] = %h %h %h %h", mem[8], mem[9], mem[10], mem[11]);',
        '  end',
        'endmodule',
    ], "Memories, a 2-D array, out-of-range and "
         "x-index reads, and $readmemh/$writememh (c3_mem.v).")
    out([
        "c3_mem.v:12: warning: returning 'bx for out of bounds array access mem[16].",
        'mem[3]=33  mem[3][7:4]=3  mem[3][0]=1',
        'cube[1][2]=12',
        'mem[16] (out of range read) = xx',
        'mem[nib] with x in index = xx',
        'after readmemh: mem[8..11] = 00 11 22 33',
    ], "Output (Icarus Verilog 12).")
    bul(["`mem[3][7:4]` first selects element 3, then a part-select of it; "
         "Verilog-2001 allows bit- and part-selects of array elements.",
         "Reading an address outside the declared range, or an address "
         "containing `x`/`z`, returns `x` for 4-state types; writing to such "
         "an address does nothing. Synthesized hardware has no such check - "
         "an out-of-range address aliases to some real location (Chapter 11).",
         "Verilog has no whole-array assignment, comparison or port "
         "connection (`mem = other;` is illegal); SystemVerilog adds all of "
         "these for unpacked arrays (Chapter 13).",
         "`$readmemh`/`$readmemb` load an array from a text file of hex/binary "
         "words (with optional `@address` lines); `$writememh`/`$writememb` "
         "(1364-2005) dump one. They are the standard way to initialise "
         "ROMs and instruction memories in simulation, and FPGA synthesis "
         "tools honour `$readmemh` in an `initial` block to fill block RAM "
         "(Chapter 10)."])
    box("tip", "How a memory becomes hardware",
        "A synthesis tool maps an array with a clocked write and a "
        "(clocked or combinational) read either to flip-flops plus "
        "multiplexers (a register file) or, in an FPGA, to block RAM. In an "
        "ASIC, large memories are never synthesized from RTL arrays: they are "
        "SRAM macros from a memory compiler, instantiated as black boxes, "
        "with the RTL array used only as the simulation model. Chapter 11 "
        "and the companion RTL Design guide cover the coding templates.")

    # ------------------------------------------------------------------
    h2("Integer literals: formats, sizing, padding and truncation")
    p("An integer literal has up to four parts: an optional **size** in "
      "bits (a decimal number), an apostrophe, an optional `s` for signed, "
      "a **base** letter (`b`, `o`, `d`, `h`, upper or lower case), and the "
      "digits, which may include `x`, `z`, `?` (a synonym for `z`) and `_` "
      "separators.")
    tbl(["Literal", "Size", "Signed?", "Value / rule"],
        [["`12`", "32 (at least)", "Yes", "A plain decimal number is a "
          "signed 32-bit integer"],
         ["`'d12`, `'hC`", "32 (at least)", "No", "Unsized based literal: "
          "unsigned"],
         ["`8'd12`", "8", "No", "Sized based literal"],
         ["`8'sd12`", "8", "Yes", "`s` makes it signed (two's complement)"],
         ["`-8'd12`", "8", "No", "Unary minus applied to `8'd12`: the bit "
          "pattern of -12 in 8 bits, but unsigned"],
         ["`8'hx`, `8'bz`", "8", "No", "All bits x / z"],
         ["`4'b1?0?`", "4", "No", "`?` is `z` (useful in `casez`)"],
         ["`1.5e3`, `2.0`", "-", "-", "Real literals; must have a digit on "
          "both sides of the point"],
         ["`\"AB\"`", "16", "No", "A string used as a number: 8 bits per "
          "character, first character in the MSBs"]],
        widths=[16, 14, 10, 60], bold_first=True)
    p("The value of a sized literal is adjusted to its declared size by "
      "three rules:")
    bul(["**Padding.** If the digits specify fewer bits than the size, the "
         "value is extended on the left with 0 - unless the leftmost digit "
         "is `x` or `z`, in which case it is extended with `x` or `z`.",
         "**Truncation.** If the digits specify more bits than the size, the "
         "leftmost bits are dropped (tools warn).",
         "**Unsized x/z.** An unsized literal whose leftmost digit is `x` or "
         "`z` (`'hx`, `'bz`) is extended to the full width of the expression "
         "it appears in. (In Verilog-1995 it stopped at 32 bits - a known "
         "incompatibility for wide buses.) SystemVerilog adds the fill "
         "literals `'0`, `'1`, `'x`, `'z`, which fill any width."])
    code([
        'module tb_lit;',
        '  reg [11:0] r;',
        '  reg [7:0]  b;',
        '  reg signed [7:0] s;',
        '  initial begin',
        '    r = 8\'hA5;        $display("8\'hA5 into 12 bits      -> %b (zero-padded)", r);',
        '    r = \'hx;          $display("\'hx into 12 bits        -> %b (x-extended)", r);',
        '    r = 4\'bz01;       $display("4\'bz01 into 12 bits     -> %b", r);',
        '    r = 8\'bx1;        $display("8\'bx1                   -> %b", r);',
        '    b = 12\'hABC;      $display("12\'hABC into 8 bits     -> %h (MSBs truncated)", b);',
        '    b = 3\'d9;         $display("3\'d9                    -> %0d (value too big for size)", b);',
        '    s = -8\'d3;        $display("-8\'d3                   -> %b = %0d", s, s);',
        '    s = 4\'shF;        $display("4\'shF (signed, = -1)    -> %b = %0d (sign-extended)", s, s);',
        '    s = 4\'hF;         $display("4\'hF  (unsigned)        -> %b = %0d (zero-extended)", s, s);',
        '    $display("unsized \'d5 is %0d bits; 12 is %0d bits", $bits(\'d5), $bits(12));',
        '    $display("?-as-z: 4\'b1?0? = %b", 4\'b1?0?);',
        '  end',
        'endmodule',
    ], "Padding, truncation, x/z extension and signed "
         "literals (c3_lit.v; compiled with -g2012 for $bits).")
    out([
        'c3_lit.v:11: warning: Numeric constant truncated to 3 bits.',
        "8'hA5 into 12 bits      -> 000010100101 (zero-padded)",
        "'hx into 12 bits        -> xxxxxxxxxxxx (x-extended)",
        "4'bz01 into 12 bits     -> 00000000zz01",
        "8'bx1                   -> 0000xxxxxxx1",
        "12'hABC into 8 bits     -> bc (MSBs truncated)",
        "3'd9                    -> 1 (value too big for size)",
        "-8'd3                   -> 11111101 = -3",
        "4'shF (signed, = -1)    -> 11111111 = -1 (sign-extended)",
        "4'hF  (unsigned)        -> 00001111 = 15 (zero-extended)",
        "unsized 'd5 is 32 bits; 12 is 32 bits",
        "?-as-z: 4'b1?0? = 1z0z",
    ], "Output (Icarus Verilog 12).")
    p("Read each line carefully - these are standard interview questions:")
    bul(["`4'bz01`: three digits for four bits; the leftmost digit is `z`, so "
         "the literal is `zz01`. Assigned to 12 bits, that **4-bit unsigned "
         "value** is then zero-extended: the `z` extension stops at the "
         "literal's own size.",
         "`8'bx1` becomes `xxxxxxx1` (x-extended to 8 bits), then "
         "zero-extended to 12 bits.",
         "`3'd9` truncates 1001 to 001. Icarus warns; many tools do not.",
         "`4'shF` is the signed 4-bit value -1, so it is **sign**-extended "
         "to `11111111`; `4'hF` is unsigned 15 and zero-extended. The only "
         "difference is the `s`.",
         "Unsized literals are 32 bits wide in every tool used here (the "
         "LRM says \"at least 32\"), which is why `'d5` in a 64-bit context "
         "is safe but `'hFFFF_FFFF_F` (36 bits of digits, unsized) is not "
         "portable."])
    box("warn", "Pitfall: a negative literal is not a signed literal",
        "`-8'd3` is unary minus applied to the **unsigned** literal "
        "`8'd3`. Its bit pattern is `11111101`, but the expression is "
        "unsigned, so in a wider context it zero-extends to 253, not -3. "
        "For a genuinely negative constant write `-8'sd3` or use a plain "
        "decimal `-3` (which is signed 32-bit). Chapter 4 shows how one "
        "unsigned operand turns a whole expression unsigned.")

    h2("Summary")
    bul(["Nets model connections and are driven continuously; variables "
         "store values written by procedural code. `reg` is a variable, not "
         "necessarily a register.",
         "Values are 0, 1, x (unknown) and z (undriven). `x` is a simulation "
         "artefact that synthesis treats as don't-care.",
         "Net types differ in how they resolve multiple drivers: wire/tri "
         "(conflict -> x), wand/wor, tri0/tri1 (pulled), supply0/1, trireg "
         "(charge), uwire (single driver enforced).",
         "Strength levels (supply > strong > pull > weak, plus charge levels) "
         "decide conflicts before values; used in gate-level, pad and "
         "open-drain models.",
         "Vector ranges fix which index is the MSB; `+:`/`-:` give "
         "variable-base, constant-width part-selects; any select is "
         "unsigned; out-of-range reads return x.",
         "Arrays are accessed element by element in Verilog; `$readmemh` "
         "loads them.",
         "Literals: plain decimal is signed 32-bit; based literals are "
         "unsigned unless marked `s`; values are zero-padded (x/z-padded if "
         "the leftmost digit is x/z) or truncated to their size."])

    h2("Exercises")
    bul(["Write the resolution table for a `wand` and a `wor` net with two "
         "drivers, and check it against the output in Section 3.3.",
         "A bus has a `pull1` pull-up, a device driving `strong0` and a "
         "second device driving `weak1`. What is the resolved value and "
         "strength? Verify with `%v`.",
         "Given `reg [31:0] w = 32'h12345678;` and `integer k = 2;`, "
         "evaluate `w[k*8 +: 8]`, `w[31 -: 4]`, `w[k]`, and `w[k*16 +: 16]`. "
         "Which of them is illegal, if any, and why?",
         "What values do `12'hx5`, `12'h5x`, `6'o7z`, `4'b1` and `'bz` take "
         "when assigned to a 16-bit `reg`?",
         "Declare a 256 x 32-bit memory, load it from a hex file with "
         "`$readmemh`, and write a loop that computes a checksum of its "
         "words. What does the checksum become if one line of the file is "
         "missing, and why?",
         "Explain the difference between `reg signed [7:0] a = -3;` and "
         "`reg [7:0] b = -3;` when each is added to a 16-bit `reg signed` "
         "variable holding 0."], ordered=True)


# =============================================================================
#        Chapter 4 - Operators and expressions
# =============================================================================
def _ch4():
    chapter("Operators and Expressions: Sizing, Signedness and Evaluation "
            "Rules")
    p("Verilog's operators look like C's, and that is the trap. In C, an "
      "`int` is an `int`. In Verilog, every operand has an exact bit width, "
      "a signedness and four-state bits, and the language silently extends, "
      "truncates and re-interprets them according to rules that are precise "
      "but not intuitive. More RTL bugs, more lint warnings and more "
      "interview questions come from this chapter than from any other. "
      "Every rule below is demonstrated with a simulation, including the "
      "surprising results - learn to predict them before reading the "
      "output.")

    # ------------------------------------------------------------------
    h2("The operators and their precedence")
    tbl(["Precedence", "Operators", "Kind"],
        [["1 (highest)", "`+ - ! ~ & ~& | ~| ^ ~^ ^~` (unary)", "Unary "
          "arithmetic, logical and bitwise negation, reduction"],
         ["2", "`**`", "Power"],
         ["3", "`* / %`", "Multiplicative"],
         ["4", "`+ -` (binary)", "Additive"],
         ["5", "`<< >> <<< >>>`", "Logical and arithmetic shifts"],
         ["6", "`< <= > >=` (SV adds `inside`, `dist`)", "Relational"],
         ["7", "`== != === !==` (SV adds `==? !=?`)", "Equality: logical, "
          "case (4-state), wildcard"],
         ["8", "`&` (binary)", "Bitwise AND"],
         ["9", "`^ ~^ ^~` (binary)", "Bitwise XOR / XNOR"],
         ["10", "`|` (binary)", "Bitwise OR"],
         ["11", "`&&`", "Logical AND"],
         ["12", "`||`", "Logical OR"],
         ["13", "`?:`", "Conditional (right-associative)"],
         ["(SV) 14", "`-> <->`", "Logical implication / equivalence"],
         ["(lowest)", "`{} {{}}`", "Concatenation and replication are "
          "delimiters, not ranked operators"]],
        widths=[14, 44, 42], bold_first=True,
        caption="Operator precedence (IEEE 1364-2005 Table 5-4, IEEE "
        "1800-2017 Table 11-2). All binary operators are left-associative; "
        "`?:` is right-associative.")
    code([
        'module tb_prec;',
        '  reg [3:0] a, b, c;',
        '  initial begin',
        "    a = 4'd3; b = 4'd2; c = 4'd2;",
        '    $display("a & b == c     -> %b  (== binds tighter: a & (b==c))", a & b == c);',
        '    $display("(a & b) == c   -> %b", (a & b) == c);',
        '    $display("a | b ^ c      -> %b  (^ before |)", a | b ^ c);',
        '    $display("a + b << 1     -> %0d    (+ before <<)", a + b << 1);',
        '    $display("!a == 0        -> %b     ((!a) == 0)", !a == 0);',
        '    $display("-2 ** 2        -> %0d    (unary minus binds tighter than **)", -2 ** 2);',
        '    $display("2 ** 3 ** 2    -> %0d  (** is left-assoc in 1364/1800-2017)", 2 ** 3 ** 2);',
        '    $display("a ? b : c ? 4\'d7 : 4\'d8 -> %0d (?: is right-assoc)", a ? b : c ? 4\'d7 : 4\'d8);',
        '  end',
        'endmodule',
    ], "Precedence surprises (c4_prec.v).")
    out([
        'a & b == c     -> 0001  (== binds tighter: a & (b==c))',
        '(a & b) == c   -> 1',
        'a | b ^ c      -> 0011  (^ before |)',
        'a + b << 1     -> 10    (+ before <<)',
        '!a == 0        -> 1     ((!a) == 0)',
        '-2 ** 2        -> 4    (unary minus binds tighter than **)',
        '2 ** 3 ** 2    -> 64  (** is left-assoc in 1364/1800-2017)',
        "a ? b : c ? 4'd7 : 4'd8 -> 2 (?: is right-assoc)",
    ], "Output (Icarus Verilog 12).")
    bul(["`a & b == c` parses as `a & (b == c)`: equality binds more tightly "
         "than bitwise AND - the reverse of what most people expect, and "
         "inherited from C. The 1-bit result of `==` is zero-extended to "
         "four bits before the AND.",
         "`a | b ^ c` is `a | (b ^ c)`: XOR binds more tightly than OR.",
         "`-2 ** 2` is 4, because unary minus has the highest precedence of "
         "all.",
         "`2 ** 3 ** 2` is `(2 ** 3) ** 2 = 64` because the standards list "
         "`**` as left-associative, unlike mathematics and Python (512).",
         "`?:` is right-associative, so chains of conditionals read as "
         "if/else-if ladders."])
    box("tip", "Parenthesise",
        "Nobody reviewing your code should need this table. Put parentheses "
        "around every mix of bitwise, equality and logical operators, around "
        "shifts inside arithmetic, and around every chained `**`. Lint tools "
        "flag many of these (for example Verilator's WIDTH warnings show "
        "where the `==` result is being extended).")

    # ------------------------------------------------------------------
    h2("Arithmetic operators, division, modulus and power")
    p("`+ - * / %` work on integral operands of any width. The rule for "
      "unknowns is blunt: **if any bit of any operand is x or z, the entire "
      "result is x**. The arithmetic itself is performed in the width and "
      "signedness determined by Sections 4.8 and 4.9; overflow simply wraps.")
    code([
        'module tb_div;',
        '  integer i;',
        '  reg [3:0] u;',
        '  initial begin',
        '    $display(" 7/2=%0d  -7/2=%0d  7/-2=%0d  -7/-2=%0d", 7/2, -7/2, 7/-2, -7/-2);',
        '    $display(" 7%%2=%0d  -7%%2=%0d  7%%-2=%0d  -7%%-2=%0d  (sign follows the dividend)",',
        '             7%2, -7%2, 7%-2, -7%-2);',
        "    u = 4'd9;",
        '    $display(" u/0=%b  u%%0=%b  (division by zero gives x)", u/4\'d0, u%4\'d0);',
        '    $display(" 2**10=%0d  2**-1=%0d  (-2)**3=%0d  (-1)**-3=%0d  0**-1=%0d",',
        '             2**10, 2**-1, (-2)**3, (-1)**-3, 0**-1);',
        '    $display(" 3\'d7**2 in 8 bits: %0d ;  4\'d3 ** 2\'d3 = %0d",',
        "             {8'd0 + 3'd7**2}, 4'd3 ** 2'd3);",
        '    $display(" 2.0**0.5 = %f   7.0/2 = %f   7/2.0 = %f", 2.0**0.5, 7.0/2, 7/2.0);',
        '    i = 6.5;  $write(" real->integer rounds half away from zero: 6.5->%0d", i);',
        '    i = -2.5; $display("  -2.5->%0d", i);',
        '  end',
        'endmodule',
    ], "Integer division and modulus with negative "
         "operands, division by zero, the power operator and reals "
         "(c4_div.v).")
    out([
        ' 7/2=3  -7/2=-3  7/-2=-3  -7/-2=3',
        ' 7%2=1  -7%2=-1  7%-2=1  -7%-2=-1  (sign follows the dividend)',
        ' u/0=xxxx  u%0=xxxx  (division by zero gives x)',
        ' 2**10=1024  2**-1=0  (-2)**3=-8  (-1)**-3=-1  0**-1=x',
        " 3'd7**2 in 8 bits: 49 ;  4'd3 ** 2'd3 = 11",
        ' 2.0**0.5 = 1.414214   7.0/2 = 3.500000   7/2.0 = 3.500000',
        ' real->integer rounds half away from zero: 6.5->7  -2.5->-3',
    ], "Output (Icarus Verilog 12).")
    bul(["Integer division **truncates toward zero** (`-7/2 = -3`), and the "
         "result of `%` takes the **sign of the first operand** (`-7 % 2 = "
         "-1`, `7 % -2 = 1`). This matches C99, but not Python, whose `//` "
         "and `%` floor toward minus infinity - a classic mismatch between a "
         "Python reference model and RTL.",
         "Division or modulus by zero yields `x` for integral types.",
         "The power operator's result has the width of its **left** operand "
         "(context-determined); the right operand is self-determined. That "
         "is why `4'd3 ** 2'd3` in a self-determined context prints 11: 27 "
         "does not fit in four bits.",
         "For integer operands, `**` with a negative exponent follows a small "
         "table: `0 ** -n` is `x`, `1 ** -n` is 1, `(-1) ** -n` is +1 or -1 "
         "(by parity), anything else to a negative power is 0.",
         "If either operand is `real`, the operation is performed in real "
         "arithmetic (`7/2.0 = 3.5`). A real assigned to an integral variable "
         "rounds to nearest, ties away from zero."])
    box("warn", "Pitfall: division in RTL",
        "`/` and `%` by a non-power-of-two are synthesizable in principle, "
        "but produce a huge combinational divider that will rarely meet "
        "timing; most coding standards forbid them in RTL except with "
        "constant power-of-two divisors (which become shifts and masks) or "
        "in constant expressions evaluated at elaboration. A real design uses "
        "a multi-cycle divider (see the companion RTL Design guide). `**` is "
        "likewise restricted to constant operands or a power-of-two base "
        "(`2 ** n` is a shift).")

    # ------------------------------------------------------------------
    h2("Equality, relational and logical operators")
    p("There are two families of equality. **Logical equality** `==`/`!=` "
      "models hardware comparators: it returns `x` whenever an `x` or `z` bit "
      "could affect the answer. **Case equality** `===`/`!==` compares all "
      "four states literally and always returns 0 or 1. Relational operators "
      "`< <= > >=` behave like `==`: any `x`/`z` bit gives `x`.")
    code([
        'module tb_eq;',
        '  reg [3:0] a, b;',
        '  initial begin',
        "    a = 4'b10x1; b = 4'b10x1;",
        '    $display("a==b  -> %b   a===b -> %b   a!=b -> %b   a!==b -> %b",',
        '             a==b, a===b, a!=b, a!==b);',
        "    a = 4'b10x1; b = 4'b0000;",
        '    $display("a==0  -> %b   (a differs in a known bit, so result is known)", a==b);',
        "    a = 4'b0101; b = 4'b0011;",
        '    $display("logical  a&&b=%b  a||b=%b  !a=%b", a && b, a || b, !a);',
        '    $display("bitwise  a&b=%b a|b=%b a^b=%b ~a=%b a~^b=%b", a & b, a | b, a ^ b, ~a, a ~^ b);',
        '    $display("reduce   &a=%b |a=%b ^a=%b ~&a=%b ~|a=%b ~^a=%b", &a, |a, ^a, ~&a, ~|a, ~^a);',
        "    a = 4'b00x0;",
        '    $display("x cases  |a=%b  &a=%b  a&&1=%b  !a=%b  4\'b10x0||0=%b",',
        "             |a, &a, a && 1'b1, !a, 4'b10x0 || 1'b0);",
        '    if (a == 4\'b0000) $display("if (x) took the THEN branch");',
        '    else              $display("if (a == 0) with x -> condition is x -> ELSE branch taken");',
        '  end',
        'endmodule',
    ], "Equality with unknowns, and logical, bitwise and "
         "reduction operators side by side (c4_eq.v).")
    out([
        'a==b  -> x   a===b -> 1   a!=b -> x   a!==b -> 0',
        'a==0  -> 0   (a differs in a known bit, so result is known)',
        'logical  a&&b=1  a||b=1  !a=0',
        'bitwise  a&b=0001 a|b=0111 a^b=0110 ~a=1010 a~^b=1001',
        'reduce   &a=0 |a=1 ^a=0 ~&a=1 ~|a=0 ~^a=1',
        "x cases  |a=x  &a=0  a&&1=x  !a=x  4'b10x0||0=1",
        'if (a == 0) with x -> condition is x -> ELSE branch taken',
    ], "Output (Icarus Verilog 12).")
    tbl(["Operator", "Result width", "x/z handling", "Synthesizable?"],
        [["`==`, `!=`", "1 bit", "x if any x/z bit could decide the result; "
          "known if a known bit differs (`4'b10x1 == 4'b0000` is 0)",
          "Yes: comparator"],
         ["`===`, `!==`", "1 bit", "Exact 4-state match, never x", "No (tools "
          "treat x/z literally or error); testbench only"],
         ["`==?`, `!=?` (SV)", "1 bit", "x/z bits in the **right** operand "
          "are wildcards", "Yes with constant wildcards"],
         ["`< <= > >=`", "1 bit", "x if any operand bit is x/z", "Yes"],
         ["`&& || !`", "1 bit", "Operands reduced to true/false/unknown: a "
          "vector is true if any bit is 1, false if all bits are 0, else x",
          "Yes"]],
        widths=[16, 12, 50, 22], bold_first=True)
    box("key", "if (x) takes the else branch",
        "An `if` condition that evaluates to `x` or `z` is treated as "
        "**false**: the `else` branch executes. This is X-optimism in its "
        "purest form. Hardware would pick one branch or the other; the "
        "simulator always picks the `else`, which can hide an uninitialised "
        "control signal. The same holds for `while`, `?:` is different "
        "(Section 4.7), and `case` has its own rules (Chapter 6). Use `===` "
        "or `$isunknown` (SV) in testbench checks, and assertions such as "
        "`assert (!$isunknown(sel))` in RTL to catch unknown controls.")

    # ------------------------------------------------------------------
    h2("Bitwise, reduction and logical operators")
    p("The same symbols play three different roles, and confusing them is a "
      "top source of bugs:")
    tbl(["Kind", "Syntax", "Operands -> result", "Example (a=0101, b=0011)"],
        [["Bitwise", "`a & b`, `a | b`, `a ^ b`, `~a`, `a ~^ b`", "Vectors -> "
          "vector, bit by bit", "`a & b = 0001`, `~a = 1010`"],
         ["Reduction", "`&a`, `|a`, `^a`, `~&a`, `~|a`, `~^a`", "One vector "
          "-> 1 bit, folding all its bits", "`&a = 0`, `|a = 1`, `^a = 0` "
          "(even parity)"],
         ["Logical", "`a && b`, `a || b`, `!a`", "Operands as truth values "
          "-> 1 bit", "`a && b = 1`, `!a = 0`"]],
        widths=[12, 32, 26, 30], bold_first=True)
    p("The 4-state truth tables of the bitwise operators follow the "
      "\"dominant value\" principle: 0 dominates AND, 1 dominates OR, and "
      "XOR is unknown whenever either input is unknown. A `z` input behaves "
      "as `x`.")
    tbl(["&", "0", "1", "x", "z"],
        [["**0**", "0", "0", "0", "0"], ["**1**", "0", "1", "x", "x"],
         ["**x**", "0", "x", "x", "x"], ["**z**", "0", "x", "x", "x"]],
        widths=[1, 1, 1, 1, 1], caption="Bitwise AND.")
    tbl(["|", "0", "1", "x", "z"],
        [["**0**", "0", "1", "x", "x"], ["**1**", "1", "1", "1", "1"],
         ["**x**", "x", "1", "x", "x"], ["**z**", "x", "1", "x", "x"]],
        widths=[1, 1, 1, 1, 1], caption="Bitwise OR.")
    tbl(["^", "0", "1", "x", "z"],
        [["**0**", "0", "1", "x", "x"], ["**1**", "1", "0", "x", "x"],
         ["**x**", "x", "x", "x", "x"], ["**z**", "x", "x", "x", "x"]],
        widths=[1, 1, 1, 1, 1], caption="Bitwise XOR (XNOR is its "
        "complement; ~x = x).")
    p("The output line `x cases` in the previous run shows the consequences "
      "for reduction and logical operators: for `a = 4'b00x0`, `|a` is `x` "
      "(the unknown bit could be the only 1), but `&a` is 0 (a known 0 "
      "decides the AND). `4'b10x0 || 0` is 1 because the vector has a known "
      "1 bit and is therefore true.")
    box("warn", "Pitfall: ! versus ~ on vectors",
        "`if (!status)` tests whether the whole vector is zero; `if (~status)` "
        "inverts every bit and then tests whether the __result__ is non-zero - "
        "true unless `status` is all ones. For a 1-bit signal the two agree, "
        "which is why the bug survives until someone widens the signal. Use "
        "`!` (or an explicit `== 0`) for conditions and `~` for data.")

    # ------------------------------------------------------------------
    h2("Shift operators")
    tbl(["Operator", "Name", "Vacated bits filled with"],
        [["`<<`", "Logical left shift", "0"],
         ["`>>`", "Logical right shift", "0"],
         ["`<<<`", "Arithmetic left shift", "0 (identical to `<<`)"],
         ["`>>>`", "Arithmetic right shift", "Copies of the MSB **if the "
          "expression is signed**, otherwise 0"]],
        widths=[14, 30, 56], bold_first=True)
    code([
        'module tb_shift;',
        '  reg        [7:0] u;',
        '  reg signed [7:0] s;',
        '  initial begin',
        "    u = 8'b1001_0110;  s = 8'sb1001_0110;         // s = -106",
        '    $display("u >>  2 = %b   u >>> 2 = %b  (unsigned: both logical)", u >> 2, u >>> 2);',
        '    $display("s >>  2 = %b   s >>> 2 = %b  (signed: >>> copies the sign)", s >> 2, s >>> 2);',
        '    $display("s >>> 2 = %0d  (-106/4 = -26.5 -> floor -> -27)", s >>> 2);',
        '    $display("s <<< 1 = %b   same as s << 1", s <<< 1);',
        '    $display("u >> 9  = %b   u << 4\'bx = %b", u >> 9, u << 4\'bx);',
        '    $display("{u[3:0], u[7:4]}  = %b   {3{2\'b10}} = %b", {u[3:0], u[7:4]}, {3{2\'b10}});',
        '    $display("{2{u[7]}, u[7:2]} (sign-ext manual) = %b", {{2{u[7]}}, u[7:2]});',
        '  end',
        'endmodule',
    ], "Logical and arithmetic shifts, concatenation "
         "and replication (c4_shift.v).")
    out([
        'u >>  2 = 00100101   u >>> 2 = 00100101  (unsigned: both logical)',
        's >>  2 = 00100101   s >>> 2 = 11100101  (signed: >>> copies the sign)',
        's >>> 2 = -27  (-106/4 = -26.5 -> floor -> -27)',
        's <<< 1 = 00101100   same as s << 1',
        "u >> 9  = 00000000   u << 4'bx = xxxxxxxx",
        "{u[3:0], u[7:4]}  = 01101001   {3{2'b10}} = 101010",
        '{2{u[7]}, u[7:2]} (sign-ext manual) = 11100101',
    ], "Output (Icarus Verilog 12).")
    bul(["`>>>` is an arithmetic shift only when the left operand - more "
         "precisely, the whole expression it belongs to - is **signed**. On "
         "the unsigned `u` it behaves exactly like `>>`. This is the most "
         "common reason for a broken fixed-point scaler.",
         "An arithmetic right shift is division by a power of two that "
         "rounds toward **minus infinity** (-106 >>> 2 = -27), whereas `/` "
         "truncates toward zero (-106 / 4 = -26). A reference model must "
         "use the same rounding as the RTL.",
         "The shift amount is always treated as unsigned and is "
         "self-determined; shifting by more than the width gives 0 (or all "
         "sign bits), and a shift amount containing `x`/`z` gives an all-`x` "
         "result.",
         "A shift by a constant is free in hardware (wiring); a shift by a "
         "variable is a barrel shifter (log2 N levels of multiplexers)."])

    # ------------------------------------------------------------------
    h2("Concatenation and replication")
    p("`{a, b, c}` joins operands MSB-first into one vector whose width is "
      "the sum of their widths; `{n{a}}` repeats `a` `n` times. Rules:")
    bul(["Every operand of a concatenation must be **sized**: `{a, 1}` is "
         "illegal because `1` has no defined width; write `{a, 1'b1}`.",
         "The replication count must be a non-negative constant expression. "
         "A count of zero is legal only inside a larger concatenation with at "
         "least one positive-width operand (1364-2005; SystemVerilog "
         "clarifies the same rule), which is useful in parameterized code.",
         "Operands are **self-determined**: an expression inside `{}` is "
         "evaluated in its own width, which is how `{a + b}` loses the carry "
         "in Section 4.8.",
         "The result of a concatenation is always unsigned.",
         "A concatenation may be the target of an assignment: `{cout, sum} = "
         "a + b + cin;` splits the result, the idiom used in Chapter 1."])
    p("Replication of the sign bit is the manual way to sign-extend: "
      "`{{2{u[7]}}, u[7:2]}` above produces the same bits as `s >>> 2`. Note "
      "the doubled braces: the replication `{2{u[7]}}` is itself an operand "
      "of the outer concatenation.")

    # ------------------------------------------------------------------
    h2("The conditional operator and unknown conditions")
    p("`c ? a : b` selects `a` if `c` is true and `b` if it is false. If `c` "
      "is `x` or `z`, the LRM requires both `a` and `b` to be evaluated and "
      "combined **bit by bit**: where the corresponding bits are equal the "
      "result takes that value, otherwise it is `x`.")
    code([
        'module tb_cond;',
        '  reg       sel;',
        '  reg [3:0] a, b;',
        '  initial begin',
        "    a = 4'b1100; b = 4'b1010;",
        '    sel = 1\'b0; $display("sel=0 : %b", sel ? a : b);',
        '    sel = 1\'b1; $display("sel=1 : %b", sel ? a : b);',
        '    sel = 1\'bx; $display("sel=x : %b   (bits where a and b agree survive)", sel ? a : b);',
        '    sel = 1\'bz; $display("sel=z : %b", sel ? a : b);',
        '  end',
        'endmodule',
    ], "The conditional operator with an unknown select "
         "(c4_cond.v).")
    out([
        'sel=0 : 1010',
        'sel=1 : 1100',
        'sel=x : 1xx0   (bits where a and b agree survive)',
        'sel=z : 1xx0',
    ], "Output (Icarus Verilog 12).")
    p("This is a realistic model of a multiplexer with an unknown select: if "
      "both inputs agree, the output does not depend on the select. It is "
      "therefore **less** optimistic than `if (sel) y = a; else y = b;`, "
      "which would silently return `b`. This difference - `?:` merges, `if` "
      "picks else - is an important one in X-propagation analysis and is "
      "why some teams prefer `?:` (or `unique case` with assertions) for "
      "data-path muxes. Commercial simulators also offer X-propagation "
      "modes that make `if`/`case` behave like `?:` (Chapter 11).")

    # ------------------------------------------------------------------
    h2("Expression bit-length rules")
    p("This is the heart of the chapter. Verilog evaluates every expression "
      "at a single width, chosen **before** evaluation from the widths of "
      "the operands and, for an assignment, of the left-hand side. Each "
      "operand is either **context-determined** (it takes part in choosing "
      "the width and is extended to it) or **self-determined** (it is "
      "evaluated in its own width and then used as a value).")
    tbl(["Expression", "Bit length", "Notes"],
        [["Unsized constant", "Same as `integer` (32)", ""],
         ["Sized constant", "As given", ""],
         ["`i op j`, op is `+ - * / % & | ^ ^~ ~^`", "max(L(i), L(j))",
          "Both operands context-determined"],
         ["`op i`, op is `+ - ~`", "L(i)", "Context-determined"],
         ["`i op j`, op is `=== !== == != > >= < <=`", "1 bit", "Operands "
          "sized to max(L(i), L(j)) between themselves"],
         ["`i op j`, op is `&& ||`", "1 bit", "Each operand self-determined"],
         ["`op i`, op is `& ~& | ~| ^ ~^ ^~ !`", "1 bit", "Operand "
          "self-determined"],
         ["`i op j`, op is `>> << >>> <<< **`", "L(i)", "`j` is "
          "self-determined"],
         ["`i ? j : k`", "max(L(j), L(k))", "`i` is self-determined"],
         ["`{i, ..., j}`", "L(i) + ... + L(j)", "All self-determined"],
         ["`{i{j, ..., k}}`", "i x (L(j) + ... + L(k))", "All "
          "self-determined"]],
        widths=[38, 22, 40], bold_first=True,
        caption="Bit lengths of expressions (IEEE 1364-2005 Table 5-22; the "
        "same table appears as Table 11-21 in IEEE 1800-2017).")
    p("The width of an expression is found in two passes. **Upward:** from "
      "the leaves, compute the maximum width of all context-determined "
      "operands, including the left-hand side of an assignment. **Downward:** "
      "extend every context-determined operand to that width, then evaluate. "
      "Finally, the result is truncated (or extended) to the left-hand "
      "side. Crucially, the left-hand side takes part in the first pass - "
      "which is why `sum9 = a + b` keeps its carry.")
    code([
        'module tb_size;',
        '  reg  [7:0] a, b;',
        '  reg  [8:0] sum9;',
        '  reg  [7:0] avg8;',
        '  reg [15:0] w;',
        '  initial begin',
        "    a = 8'd200; b = 8'd100;",
        '    sum9 = a + b;',
        '    $display("1) sum9 = a + b          = %0d (context is 9 bits)", sum9);',
        '    $display("2) a + b in $display     = %0d  (self-determined: 8 bits)", a + b);',
        '    $display("3) {a + b}               = %0d  (concat operand: self-determined)", {a + b});',
        '    avg8 = (a + b) >> 1;',
        '    $display("4) avg8 = (a+b)>>1       = %0d  (8-bit context: carry lost)", avg8);',
        "    avg8 = (a + b + 9'd0) >> 1;",
        '    $display("5) avg8 = (a+b+9\'d0)>>1  = %0d (a 9-bit operand widens all)", avg8);',
        '    w = a * b;',
        '    $display("6) w = a * b             = %0d (16-bit context)", w);',
        '    w = {a * b};',
        '    $display("7) w = {a * b}           = %0d  (20000 mod 256)", w);',
        '    $display("8) (a + b) > 8\'d255      = %b   (compared in 8 bits)", (a + b) > 8\'d255);',
        '    $display("9) (a + b) > 9\'d255      = %b   (9 bits: carry kept)", (a + b) > 9\'d255);',
        '    $display("10) ~a == 8\'d55          = %b   (8-bit compare)", ~a == 8\'d55);',
        '    $display("11) ~a == 9\'d55          = %b   (a widened to 9 bits BEFORE ~)", ~a == 9\'d55);',
        '  end',
        'endmodule',
    ], "Eleven sizing cases with a = 200 and b = 100 "
         "(c4_size.v).")
    out([
        '1) sum9 = a + b          = 300 (context is 9 bits)',
        '2) a + b in $display     = 44  (self-determined: 8 bits)',
        '3) {a + b}               = 44  (concat operand: self-determined)',
        '4) avg8 = (a+b)>>1       = 22  (8-bit context: carry lost)',
        "5) avg8 = (a+b+9'd0)>>1  = 150 (a 9-bit operand widens all)",
        '6) w = a * b             = 20000 (16-bit context)',
        '7) w = {a * b}           = 32  (20000 mod 256)',
        "8) (a + b) > 8'd255      = 0   (compared in 8 bits)",
        "9) (a + b) > 9'd255      = 1   (9 bits: carry kept)",
        "10) ~a == 8'd55          = 1   (8-bit compare)",
        "11) ~a == 9'd55          = 0   (a widened to 9 bits BEFORE ~)",
    ], "Output (Icarus Verilog 12).")
    tbl(["Case", "Why"],
        [["1) 300", "LHS is 9 bits, so `a` and `b` are extended to 9 bits "
          "before the add; the carry is kept"],
         ["2) 44", "Arguments of `$display` (and of any system task) are "
          "self-determined: 8 bits, 300 mod 256 = 44"],
         ["3) 44", "Concatenation operands are self-determined"],
         ["4) 22", "`>>` does not widen its left operand beyond the context: "
          "the context is max(8, 8, LHS 8) = 8, so the carry is lost before "
          "the shift - the classic averaging bug"],
         ["5) 150", "A 9-bit operand anywhere in the context widens every "
          "operand to 9 bits; the carry survives the shift"],
         ["6) 20000", "The 16-bit LHS widens `a` and `b` before the multiply"],
         ["7) 32", "Braces make the product self-determined: 8 bits"],
         ["8) 0", "A comparison sizes its operands only among themselves: "
          "max(8, 8, 8) = 8, so `a+b` is 44"],
         ["9) 1", "`9'd255` makes the comparison 9 bits wide"],
         ["10) 1", "8-bit compare: ~200 = 55"],
         ["11) 0", "`a` is extended to 9 bits **before** `~` is applied, so "
          "`~a` = 9'b1_0011_0111 = 311, not 55"]],
        widths=[12, 88], bold_first=True)
    box("expert", "Interview question: why does ~a == 9'd55 fail?",
        "Case 11 is the favourite trick question on sizing. The unary `~` is "
        "context-determined, so its operand is extended to the context width "
        "(9 bits, from `9'd55`) first - with a 0 - and the inversion then "
        "turns that 0 into a 1. The same happens with `-a`. Whenever an "
        "inverted or negated signal is compared against, or assigned to, "
        "something wider, the extra MSBs are ones. Lint tools report it as a "
        "width mismatch; the fix is to make widths equal or to isolate the "
        "operand: `{~a} == 9'd55`, or `8'(~a)` in SystemVerilog.")
    box("tip", "Rules of thumb for correct widths",
        "(1) Size the left-hand side to hold the full result (N+1 bits for "
        "an N-bit add, 2N for a multiply). (2) Never rely on the LHS to widen "
        "an intermediate that is shifted, compared or concatenated - widen "
        "explicitly: `({1'b0, a} + {1'b0, b}) >> 1`. (3) Treat every lint "
        "WIDTH warning as a bug until proven otherwise.")

    # ------------------------------------------------------------------
    h2("Signedness rules")
    p("Verilog-2001 added signed arithmetic via the `signed` keyword, signed "
      "literals (`'s`), `$signed()` and `$unsigned()`. The rules deciding "
      "whether an expression is evaluated as signed are short, strict and "
      "the cause of countless bugs:")
    bul(["The signedness of an expression depends **only on its operands**, "
         "never on the left-hand side of the assignment.",
         "**If any operand is unsigned, the whole expression is unsigned.** "
         "Only when all context-determined operands are signed is the "
         "operation signed.",
         "Bit-selects, part-selects (even of the whole vector), "
         "concatenations, and the results of comparison and reduction "
         "operators are **unsigned**.",
         "Based literals are unsigned unless they carry `s`; plain decimal "
         "numbers (`12`, `-3`) and `integer` variables are signed.",
         "Once the expression type is known it is propagated down to the "
         "context-determined operands, which are then extended: "
         "sign-extended if the expression is signed, zero-extended if not - "
         "regardless of each operand's own declaration.",
         "`$signed(x)` and `$unsigned(x)` return the same bits with the "
         "other interpretation; they do not change the width."])
    code([
        'module tb_sign;',
        '  reg signed [7:0]  s;',
        '  reg        [7:0]  u;',
        '  reg signed [15:0] r;',
        '  reg        [3:0]  n;',
        '  integer i;',
        '  initial begin',
        "    s = -8'sd4;  u = 8'd4;",
        '    $display("1) s < u  (s=-4, u=4)   -> %b  (u unsigned => s read as 252)", s < u);',
        '    $display("2) s < $signed(u)       -> %b", s < $signed(u));',
        '    r = s;              $display("3) r = s                -> %0d", r);',
        '    r = s + u;          $display("4) r = s + u            -> %0d (unsigned: s zero-ext)", r);',
        '    r = s + $signed(u); $display("5) r = s + $signed(u)   -> %0d", r);',
        "    n = 4'd3;",
        '    r = s + n;          $display("6) r = s + n (n=3)      -> %0d", r);',
        '    r = s + $signed(n); $display("7) r = s + $signed(n)   -> %0d", r);',
        "    n = 4'b1101;",
        '    r = s + $signed(n); $display("8) n=13: s + $signed(n) -> %0d (4\'b1101 read as -3)", r);',
        "    r = s + $signed({1'b0, n});",
        '                        $display("9) s + $signed({1\'b0,n})-> %0d (n kept positive)", r);',
        '    r = s * 2\'sd3;      $display("10) s * 2\'sd3           -> %0d  (2\'sd3 is -1)", r);',
        '    r = s[7:0];         $display("11) r = s[7:0]          -> %0d (part-select: UNSIGNED)", r);',
        '    i = -12 / 3;        $display("12) -12 / 3             -> %0d", i);',
        '    i = -\'d12 / 3;      $display("13) -\'d12 / 3           -> %0d", i);',
        '    i = -4\'sd12 / 3;    $display("14) -4\'sd12 / 3         -> %0d  (4\'sd12 is -4)", i);',
        '  end',
        'endmodule',
    ], "Fourteen signedness cases with s = -4 (signed) "
         "and u = 4 (unsigned) (c4_sign.v).")
    out([
        '1) s < u  (s=-4, u=4)   -> 0  (u unsigned => s read as 252)',
        '2) s < $signed(u)       -> 1',
        '3) r = s                -> -4',
        '4) r = s + u            -> 256 (unsigned: s zero-ext)',
        '5) r = s + $signed(u)   -> 0',
        '6) r = s + n (n=3)      -> 255',
        '7) r = s + $signed(n)   -> -1',
        "8) n=13: s + $signed(n) -> -7 (4'b1101 read as -3)",
        "9) s + $signed({1'b0,n})-> 9 (n kept positive)",
        "10) s * 2'sd3           -> 4  (2'sd3 is -1)",
        '11) r = s[7:0]          -> 252 (part-select: UNSIGNED)',
        '12) -12 / 3             -> -4',
        "13) -'d12 / 3           -> 1431655761",
        "14) -4'sd12 / 3         -> 1  (4'sd12 is -4)",
    ], "Output (Icarus Verilog 12).")
    tbl(["Case", "Explanation"],
        [["1) 0", "`u` is unsigned, so the comparison is unsigned: `s` is "
          "read as 252, and 252 < 4 is false"],
         ["3) -4", "All operands signed; `s` is sign-extended to 16 bits"],
         ["4) 256", "`u` makes the add unsigned; `s` is **zero**-extended to "
          "16 bits (252) and 252 + 4 = 256"],
         ["5) 0", "`$signed(u)` makes all operands signed: -4 + 4"],
         ["6) 255", "Same trap with a 4-bit `n`: 252 + 3"],
         ["8) -7", "`$signed(4'b1101)` is -3: casting reinterprets the bits, "
          "it does not add a sign bit"],
         ["9) 9", "Prepending a 0 (`{1'b0, n}`) before `$signed` keeps a "
          "positive unsigned value positive - the correct way to mix "
          "signed and unsigned operands"],
         ["10) 4", "`2'sd3` is the two-bit signed pattern 11, i.e. -1"],
         ["11) 252", "A part-select is unsigned even if it covers the whole "
          "signed vector"],
         ["12-14", "`-12/3` is signed; `-'d12` is an unsigned 32-bit "
          "pattern (4294967284) divided by 3; `4'sd12` is the 4-bit signed "
          "pattern 1100 = -4, negated to 4 and divided to 1"]],
        widths=[12, 88], bold_first=True)
    box("warn", "Pitfall: one unsigned operand poisons the expression",
        "Mixing a signed coefficient with an unsigned sample, a signed "
        "accumulator with an unsigned `count`, or a signed value with an "
        "unsized-but-based constant (`acc + 'd1`) silently turns the whole "
        "computation unsigned. The simulator gives no warning; the result is "
        "wrong only for negative values. Discipline: make every operand of a "
        "signed expression signed, convert unsigned operands with "
        "`$signed({1'b0, x})`, use plain decimal or `'sd` constants, and "
        "watch lint warnings about signed/unsigned mixing.")

    # ------------------------------------------------------------------
    h2("Evaluation order and short-circuiting")
    bul(["The LRM does not define the order in which the operands of most "
         "operators are evaluated. That matters only when an operand has a "
         "side effect, for example a function call that modifies a variable "
         "- so do not write such expressions.",
         "`&&`, `||` and `?:` short-circuit: IEEE 1800 requires that the "
         "right operand of `&&` is not evaluated when the left is false "
         "(and similarly for `||` when the left is true), which matters for "
         "function calls with side effects and for `null` handle checks in "
         "SystemVerilog testbenches (`if (h != null && h.valid)`).",
         "Integer expressions in constant contexts (parameters, ranges) are "
         "evaluated at elaboration time with exactly the same sizing and "
         "signedness rules - a parameter computed as `WIDTH-1` where `WIDTH` "
         "is an unsized decimal is a signed 32-bit value."])

    h2("Summary")
    bul(["Know the precedence traps: `==` binds tighter than `&`, `^` "
         "tighter than `|`, unary minus tighter than `**`; `**` is "
         "left-associative; `?:` is right-associative. Parenthesise.",
         "Arithmetic with any x/z bit gives all-x; `/` truncates toward zero, "
         "`%` takes the sign of the dividend, division by zero gives x.",
         "`==` returns x on unknowns, `===` never does; an `if` on x takes "
         "the else branch; `?:` with an x select merges both inputs.",
         "Bitwise, reduction and logical operators share symbols but not "
         "semantics; use `!` for conditions and `~` for data.",
         "`>>>` is arithmetic only in a signed expression, and rounds toward "
         "minus infinity.",
         "Expression width is the maximum of all context-determined operands "
         "and the LHS; concatenation operands, system-task arguments, shift "
         "amounts and conditions are self-determined; unary `~`/`-` extend "
         "before operating.",
         "One unsigned operand makes the whole expression unsigned; selects "
         "and concatenations are unsigned; `$signed`/`$unsigned` reinterpret "
         "without resizing."])

    h2("Exercises")
    bul(["With `reg [3:0] a = 4'b1010, b = 4'b0110;` evaluate: `a & b`, "
         "`a && b`, `&a`, `a ^ b`, `^a`, `!a`, `~a`, `a | b == 4'b1110`, "
         "`(a | b) == 4'b1110`.",
         "`reg [7:0] x = 8'hF0; reg [15:0] y;` What is `y` after each of "
         "`y = x << 4;`, `y = {x << 4};`, `y = (x << 4) >> 4;`, "
         "`y = ~x;`, `y = -x;`?",
         "Write a signed 8-bit average `avg = (p + q) / 2` that is correct for "
         "all inputs, where `p` and `q` are `reg signed [7:0]`. Then write "
         "it with `>>>` and explain why the two differ for negative odd sums.",
         "A designer writes `if (count - 1 < 0)` with `reg [3:0] count`. "
         "Explain why the branch is never taken, and give two fixes.",
         "Explain why `$display(\"%0d\", a + b)` and `sum = a + b; "
         "$display(\"%0d\", sum)` can print different values, citing the "
         "rule from the bit-length table.",
         "Predict, then verify, the result of `-4'sd1 >>> 1`, "
         "`$unsigned(-4'sd1) >> 1`, `4'sb1000 / -1` and `8'sd100 + 8'sd100` "
         "in an 8-bit signed context."], ordered=True)


# =============================================================================
#        Chapter 5 - Assignments, procedural blocks, timing, scheduler
# =============================================================================
def _ch5():
    chapter("Assignments, Procedural Blocks, Timing Controls and the Event "
            "Scheduler")
    p("A Verilog model is a collection of **processes** that wake up, compute, "
      "update values and go back to sleep, all coordinated by an **event "
      "scheduler** that advances simulated time. This chapter explains the "
      "two families of assignment - continuous and procedural - the "
      "blocking and non-blocking forms, every kind of timing control, and "
      "the stratified event queue that gives them meaning. It ends with the "
      "races that appear when code depends on details the standard leaves "
      "unspecified, demonstrated by running the same source on two "
      "simulators and getting different answers.")

    # ------------------------------------------------------------------
    h2("Processes")
    tbl(["Process", "Starts", "Runs", "Typical use"],
        [["Continuous assignment `assign y = f(x);`", "Time 0", "Re-evaluates "
          "whenever an operand changes", "Combinational logic, wiring"],
         ["Gate / primitive instance", "Time 0", "Re-evaluates on input "
          "change", "Netlists (Chapter 9)"],
         ["`initial` block", "Time 0", "Once, from top to bottom, then "
          "terminates", "Testbench stimulus, initialisation"],
         ["`always` block", "Time 0", "Forever: at the end it loops back to "
          "the top", "Flip-flops, combinational logic, clock generators"],
         ["Port connection", "-", "Behaves as a continuous assignment", "-"],
         ["(SV) `always_comb`, `always_ff`, `always_latch`, `final`, forked "
          "threads", "See Chapters 14 and 20", "", ""]],
        widths=[32, 12, 30, 26], bold_first=True)
    p("All processes run concurrently. Inside one `initial` or `always` "
      "block, statements execute sequentially until the block reaches a "
      "**timing control** (`#`, `@`, `wait`), where it suspends and lets "
      "other processes run. An `always` block without any timing control is "
      "an infinite zero-delay loop that hangs the simulator at time 0: "
      "`always clk = ~clk;` is the classic example (the fix is "
      "`always #5 clk = ~clk;`).")

    # ------------------------------------------------------------------
    h2("Continuous assignments")
    p("A continuous assignment drives a **net** (in SystemVerilog also a "
      "variable, as its single driver) with the value of an expression, "
      "permanently. It can be written as a separate `assign` statement or "
      "folded into the net declaration (a **net declaration assignment**: "
      "`wire y = a & b;`). A net declaration assignment is legal only once "
      "per net and is __not__ an initialisation - it is a driver, exactly "
      "like `assign`. (For a variable, `reg r = 0;` __is__ an "
      "initialisation - the same syntax means two different things.)")
    p("A delay on a continuous assignment models a gate's propagation delay "
      "with **inertial** semantics: when the right-hand side changes, the "
      "update is scheduled `d` time units later, and any pending update is "
      "cancelled. Pulses shorter than the delay therefore vanish. Up to "
      "three delays can be given: rise (to 1), fall (to 0) and turn-off "
      "(to `z`); a transition to `x` uses the smallest.")
    code([
        '`timescale 1ns/1ns',
        'module tb_ca;',
        '  reg  a = 0;',
        '  wire #3 y_net = a;          // net declaration assignment with a 3 ns delay',
        '  wire    y_ca;',
        '  assign #3 y_ca = a;         // continuous assignment with a 3 ns delay',
        '  wire #(2,4) y_rf = a;       // rise delay 2, fall delay 4',
        '  initial begin',
        '    $monitor("t=%2t a=%b y_net=%b y_ca=%b y_rf=%b", $time, a, y_net, y_ca, y_rf);',
        '    #5  a = 1;                // long pulse: propagates',
        '    #10 a = 0;',
        '    #5  a = 1;                // 2 ns pulse: shorter than 3 ns -> filtered (inertial)',
        '    #2  a = 0;',
        '    #10 $finish;',
        '  end',
        'endmodule',
    ], "Continuous-assignment and net-declaration delays; "
         "a 2 ns pulse on a 3 ns path is filtered (c5_ca.v).")
    out([
        't= 0 a=0 y_net=x y_ca=x y_rf=x',
        't= 3 a=0 y_net=0 y_ca=0 y_rf=x',
        't= 4 a=0 y_net=0 y_ca=0 y_rf=0',
        't= 5 a=1 y_net=0 y_ca=0 y_rf=0',
        't= 7 a=1 y_net=0 y_ca=0 y_rf=1',
        't= 8 a=1 y_net=1 y_ca=1 y_rf=1',
        't=15 a=0 y_net=1 y_ca=1 y_rf=1',
        't=18 a=0 y_net=0 y_ca=0 y_rf=1',
        't=19 a=0 y_net=0 y_ca=0 y_rf=0',
        't=20 a=1 y_net=0 y_ca=0 y_rf=0',
        't=22 a=0 y_net=0 y_ca=0 y_rf=1',
        't=26 a=0 y_net=0 y_ca=0 y_rf=0',
        'c5_ca.v:14: $finish called at 32 (1ns)',
    ], "Output (Icarus Verilog 12).")
    bul(["At t=0 all outputs are `x`: the nets have no value until their "
         "delayed updates mature. `y_rf` settles at t=4 because x -> 0 uses "
         "the fall delay.",
         "The rising edge at t=5 appears at t=8 on `y_net`/`y_ca` (3 ns) and "
         "at t=7 on `y_rf` (rise delay 2).",
         "The pulse from t=20 to t=22 is shorter than 3 ns and never reaches "
         "`y_net` or `y_ca` - inertial filtering. It is exactly as long as "
         "the rise delay of `y_rf`, so it passes there (t=22 to 26, stretched "
         "by the longer fall delay)."])
    box("note", "Delays and synthesis",
        "Synthesis ignores every `#` delay (often with a warning). Delays in "
        "RTL are for simulation only: to model I/O timing in a testbench, to "
        "make waveforms readable, or in gate-level models where the real "
        "values come from SDF back-annotation (Chapter 9). Putting `#1` on "
        "RTL assignments to \"fix\" a race hides the real problem and slows "
        "simulation.")

    # ------------------------------------------------------------------
    h2("initial and always blocks")
    bul(["`initial` runs once. Testbenches are mostly `initial` blocks; in "
         "ASIC RTL, `initial` is ignored by synthesis (FPGA tools use it for "
         "power-up values and memory initialisation).",
         "`always @(posedge clk)` is the flip-flop template; `always @*` (or "
         "an explicit complete sensitivity list) is the combinational "
         "template; `always #5 clk = ~clk;` is a clock generator.",
         "Multiple `initial` and `always` blocks all start at time 0 in an "
         "**unspecified order**. Code that depends on which one runs first "
         "has a race (Section 5.8).",
         "A block contains one statement; `begin ... end` groups several "
         "sequentially, `fork ... join` groups them in parallel "
         "(Chapter 6)."])

    # ------------------------------------------------------------------
    h2("Blocking and non-blocking assignments")
    p("Procedural code assigns variables in two ways. A **blocking** "
      "assignment `a = b;` evaluates the right-hand side and updates `a` "
      "immediately, before the next statement runs - like a software "
      "assignment. A **non-blocking** assignment `a <= b;` evaluates the "
      "right-hand side immediately but **schedules** the update for later "
      "in the same time step (the NBA region, Section 5.7), so statements "
      "that follow still see the old value of `a`.")
    code([
        'module tb_ba;',
        '  reg clk = 0;',
        "  reg [3:0] in = 4'd5;",
        "  reg [3:0] b1, b2, b3;       // pipeline written with blocking '='",
        "  reg [3:0] n1, n2, n3;       // pipeline written with non-blocking '<='",
        '  reg [3:0] x = 1, y = 2;',
        '  always #5 clk = ~clk;',
        '  always @(posedge clk) begin b1 = in; b2 = b1; b3 = b2; end       // collapses!',
        '  always @(posedge clk) begin n1 <= in; n2 <= n1; n3 <= n2; end    // 3 flops',
        '  initial begin',
        '    @(posedge clk); #1',
        '      $display("after edge 1: blocking b3=%0d | nonblocking n1=%0d n2=%0d n3=%0d",',
        '               b3, n1, n2, n3);',
        "    in = 4'd9;",
        '    @(posedge clk); #1',
        '      $display("after edge 2: blocking b3=%0d | nonblocking n1=%0d n2=%0d n3=%0d",',
        '               b3, n1, n2, n3);',
        '    // swap: NBA reads all right-hand sides before any update',
        '    x <= y; y <= x;',
        '    #1 $display("swap with <= : x=%0d y=%0d", x, y);',
        '    x = y; y = x;',
        '    $display("swap with =  : x=%0d y=%0d", x, y);',
        '    $finish;',
        '  end',
        'endmodule',
    ], "A three-stage pipeline written with blocking and "
         "with non-blocking assignments, and a swap (c5_ba.v).")
    out([
        'after edge 1: blocking b3=5 | nonblocking n1=5 n2=x n3=x',
        'after edge 2: blocking b3=9 | nonblocking n1=9 n2=5 n3=x',
        'swap with <= : x=2 y=1',
        'swap with =  : x=1 y=1',
        'c5_ba.v:23: $finish called at 17 (1s)',
    ], "Output (Icarus Verilog 12).")
    p("With blocking assignments, `b1 = in; b2 = b1; b3 = b2;` passes the new "
      "input straight through all three variables in one edge: the "
      "\"pipeline\" collapses into a single register (and synthesis will "
      "build exactly that). With non-blocking assignments all right-hand "
      "sides are sampled before any variable changes, so each edge shifts "
      "the data by exactly one stage - three flip-flops. The swap shows the "
      "same effect in two lines.")
    tbl(["Guideline", "Reason"],
        [["Use `<=` in every clocked (`posedge`) block", "All flops sample "
          "their inputs before any output changes, independent of the order "
          "of `always` blocks - this is how real flip-flops behave"],
         ["Use `=` in combinational blocks (`always @*`)", "The block must "
          "compute its outputs from its inputs in one pass; `<=` would need "
          "extra evaluation passes and can model latches wrongly"],
         ["Do not mix `=` and `<=` on the same variable", "Lint error; "
          "simulation and synthesis may disagree"],
         ["Assign each variable from one `always` block only", "Otherwise a "
          "write-write race and, in synthesis, multiple drivers"],
         ["Temporaries inside a clocked block may use `=`", "Legal if they "
          "are read only later in the same block (they become wires); "
          "risky if read elsewhere"]],
        widths=[42, 58], bold_first=True,
        caption="The standard coding guidelines (after C. Cummings, "
        "\"Nonblocking Assignments in Verilog Synthesis, Coding Styles That "
        "Kill!\", SNUG 2000).")

    # ------------------------------------------------------------------
    h2("Delays: regular and intra-assignment")
    p("A delay can appear in two positions in a procedural assignment, with "
      "very different meanings:")
    tbl(["Form", "Samples RHS", "Updates LHS", "Process blocked?"],
        [["`#d a = b;` (regular delay)", "After the delay", "After the delay",
          "Yes, for d"],
         ["`a = #d b;` (intra-assignment, blocking)", "Now", "After d", "Yes, "
          "for d"],
         ["`#d a <= b;`", "After the delay", "NBA region after the delay",
          "Yes, for d"],
         ["`a <= #d b;` (intra-assignment, non-blocking)", "Now", "d later, "
          "in the NBA region", "**No**: the next statement runs at once"]],
        widths=[36, 18, 26, 20], bold_first=True)
    code([
        '`timescale 1ns/1ns',
        'module tb_delay;',
        '  reg a = 0, r1, r2, r3;',
        '  initial begin',
        '    #1 a = 1;',
        '    #2 a = 0;                            // a is 1 only during [1,3)',
        '  end',
        '  initial begin',
        '    #2 r1 = a;          // regular delay: wait 2, THEN sample a (=1)',
        '  end',
        '  initial begin',
        '    r2 = #2 a;          // intra-assignment: sample a NOW (t=0 -> 0), assign at t=2',
        '  end',
        '  initial begin',
        '    #1 r3 <= #5 a;      // sample at t=1 (a=1), update at t=6; process does NOT block',
        '    $display("t=%0t: the process continued immediately after r3 <= #5", $time);',
        '  end',
        '  initial begin',
        '    $monitor("t=%0t a=%b r1=%b r2=%b r3=%b", $time, a, r1, r2, r3);',
        '    #10 $finish;',
        '  end',
        'endmodule',
    ], "The four delay forms around a pulse on `a` "
         "from t=1 to t=3 (c5_delay.v).")
    out([
        't=0 a=0 r1=x r2=x r3=x',
        't=1: the process continued immediately after r3 <= #5',
        't=1 a=1 r1=x r2=x r3=x',
        't=2 a=1 r1=1 r2=0 r3=x',
        't=3 a=0 r1=1 r2=0 r3=x',
        't=6 a=0 r1=1 r2=0 r3=1',
        'c5_delay.v:20: $finish called at 10 (1ns)',
    ], "Output (Icarus Verilog 12).")
    p("`r1` waited 2 ns and then read `a` (1); `r2` read `a` at time 0 (0) "
      "and wrote it 2 ns later; `r3` read `a` at t=1 and was updated at t=6 "
      "while its process carried on immediately. A sequence of `a <= #d b;` "
      "statements therefore models a **transport** delay line - every "
      "change is delivered, however short - unlike the inertial delay of a "
      "continuous assignment.")
    box("warn", "Pitfall: q <= #1 d in RTL",
        "Some legacy RTL writes `q <= #1 d;` in flip-flops so that waveforms "
        "show a small clock-to-Q delay and to paper over races with "
        "zero-delay clock gating in the testbench. It is ignored by "
        "synthesis, it slows simulation, it hides genuine race bugs, and it "
        "makes RTL and gate-level behaviour differ. Modern coding standards "
        "ban it; fix races with correct blocking/non-blocking usage and "
        "clocking blocks (Chapter 21) instead.")

    # ------------------------------------------------------------------
    h2("Event control: @, edges, @*, wait and named events")
    p("`@(expression)` suspends a process until the expression **changes "
      "value**. `@(posedge e)` and `@(negedge e)` wait for specific "
      "transitions of the least significant bit of `e`. Several events can "
      "be combined with `or` or a comma: `@(posedge clk or negedge rst_n)`. "
      "The edges are defined over all four values:")
    tbl(["", "to 0", "to 1", "to x", "to z"],
        [["**from 0**", "-", "posedge", "posedge", "posedge"],
         ["**from 1**", "negedge", "-", "negedge", "negedge"],
         ["**from x**", "negedge", "posedge", "-", "-"],
         ["**from z**", "negedge", "posedge", "-", "-"]],
        widths=[20, 20, 20, 20, 20],
        caption="Transitions that count as posedge and negedge (IEEE 1364-"
        "2005 clause 9.7.2; unchanged in IEEE 1800).")
    code([
        '`timescale 1ns/1ns',
        'module tb_events;',
        '  reg  clk;                        // starts at x',
        '  reg  ready = 0;',
        '  reg  [1:0] v = 0;',
        '  event done;                      // named event: no value, only an occurrence',
        '  always @(posedge clk) $display("t=%0t posedge seen (clk=%b)", $time, clk);',
        '  always @(negedge clk) $display("t=%0t negedge seen (clk=%b)", $time, clk);',
        '  always @(v[0])        $display("t=%0t @(v[0]) woke: v=%b", $time, v);   // any change',
        '  initial begin',
        '    #1 clk = 0;                    // x -> 0 : a negedge',
        '    #1 clk = 1;                    // 0 -> 1 : a posedge',
        "    #1 clk = 1'bz;                 // 1 -> z : a negedge",
        '    #1 clk = 1;                    // z -> 1 : a posedge',
        "    #1 v = 2'b10;                  // v[0] did not change: no wake-up",
        "    #1 v = 2'b11;                  // v[0] changed",
        '    #1 ready = 1;',
        '  end',
        '  initial begin',
        '    wait (ready);                  // level-sensitive: blocks until ready is true',
        '    $display("t=%0t wait(ready) released", $time);',
        '    -> done;                       // trigger the named event',
        '  end',
        '  initial begin',
        '    @done $display("t=%0t named event \'done\' received", $time);',
        '    wait (ready) $display("t=%0t wait(ready) with ready already 1: no blocking", $time);',
        '  end',
        'endmodule',
    ], "Edges involving x and z, a value-change event "
         "on one bit, wait and a named event (c5_events.v).")
    out([
        't=0 @(v[0]) woke: v=00',
        't=1 negedge seen (clk=0)',
        't=2 posedge seen (clk=1)',
        't=3 negedge seen (clk=z)',
        't=4 posedge seen (clk=1)',
        't=6 @(v[0]) woke: v=11',
        't=7 wait(ready) released',
        "t=7 named event 'done' received",
        't=7 wait(ready) with ready already 1: no blocking',
    ], "Output (Icarus Verilog 12).")
    bul(["x -> 0 and 1 -> z are **negedges**, z -> 1 is a **posedge**. A "
         "clock that starts at `x` and goes to 1 produces a posedge at the "
         "first transition - one reason flip-flops can capture on the very "
         "first clock edge of a simulation.",
         "`@(v[0])` ignores changes to other bits of `v`; `@(v)` would wake "
         "on any bit.",
         "The first line is instructive: the declaration `reg [1:0] v = 0;` "
         "changed `v[0]` from x to 0 at time 0, and in Icarus that "
         "initialisation ran after the `always` block had started waiting, "
         "so the block woke up. Verilog does not define that order; "
         "SystemVerilog does - declaration initialisers are applied before "
         "any process starts, generating no event.",
         "`wait (expr)` is **level**-sensitive: it does not block at all if "
         "`expr` is already true. `@` is **edge**-sensitive: it always waits "
         "for the next change. Confusing them causes hangs "
         "(`@(ready)` when ready is already 1) or missed synchronisation.",
         "A named `event` carries no value. `-> e;` triggers it; processes "
         "blocked on `@e` resume. A trigger that happens before the waiter "
         "reaches `@e` is lost (SystemVerilog adds the persistent "
         "`e.triggered` property, Chapter 20)."])
    h3("@* and incomplete sensitivity lists")
    p("`@*` (also written `@(*)`) builds the sensitivity list automatically "
      "from every net and variable that is **read** by the statement: "
      "right-hand sides, `if`/`case` expressions, index expressions and "
      "function-call arguments. It does not include variables read only "
      "inside a called function's body, nor anything written only on the "
      "left-hand side.")
    code([
        'module tb_star;',
        '  reg a = 0, b = 0;',
        '  reg y_list, y_star;',
        '  always @(a)  y_list = a & b;       // incomplete list: b missing',
        '  always @*    y_star = a & b;       // @* = @(a or b): all RHS/condition signals',
        '  initial begin',
        '    #1 a = 1;',
        '    #1 b = 1;                        // only y_star re-evaluates',
        '    #1 $display("a=%b b=%b  y_list=%b (stale latch-like)  y_star=%b", a, b, y_list, y_star);',
        '  end',
        'endmodule',
    ], "An incomplete sensitivity list versus @* "
         "(c5_star.v).")
    out([
        'a=1 b=1  y_list=0 (stale latch-like)  y_star=1',
    ], "Output (Icarus Verilog 12).")
    box("warn", "Pitfall: sensitivity lists are ignored by synthesis",
        "Synthesis builds an AND gate from `always @(a) y = a & b;` - it does "
        "not model the missing `b`. The simulation shows a stale, latch-like "
        "output that the gates will never produce: a simulation/synthesis "
        "mismatch that equivalence checking will flag only if someone runs "
        "it on RTL-to-gates. Use `@*` in Verilog and `always_comb` in "
        "SystemVerilog (which also covers variables read inside functions "
        "and runs once at time zero).")

    # ------------------------------------------------------------------
    h2("The stratified event scheduler")
    p("Simulated time is divided into **time slots**. Within a slot, the "
      "Verilog standard (IEEE 1364-2005, clause 11) sorts pending events "
      "into **regions** that are processed in a fixed order:")
    tbl(["Region", "Contains", "Created by"],
        [["**Active**", "Events to process now, in any order", "Process "
          "resumptions, continuous-assignment and primitive updates, "
          "blocking assignments, RHS evaluation of `<=`, `$display`"],
         ["**Inactive**", "Events to process after all active events",
          "Explicit zero delays: `#0`"],
         ["**NBA** (non-blocking assign update)", "Variable updates from "
          "`<=`", "Non-blocking assignments issued in this slot"],
         ["**Monitor**", "End-of-slot observation", "`$monitor`, `$strobe`"],
         ["**Future**", "Events for later slots", "Delays `#d`, `<= #d`"]],
        widths=[22, 38, 40], bold_first=True)
    diagram([
        "        time slot t",
        "  +-----------------------------------------------------------+",
        "  |   +--------+   empty   +----------+   empty   +--------+  |",
        "  +-->| Active |---------->| Inactive |---------->|  NBA   |--+",
        "  ^   +--------+           +----------+           +--------+  |",
        "  |       ^   (moving an event into Active restarts the loop)  |",
        "  +--------------------------------------------------------------+",
        "      when Active, Inactive and NBA are all empty:",
        "                         +---------+",
        "                         | Monitor |  $monitor / $strobe print final values",
        "                         +---------+",
        "                              |",
        "                              v   advance to the next time slot with events",
    ], "The Verilog scheduling loop. NBA updates can wake new processes, "
       "so the loop iterates (delta cycles) until the slot is quiescent.")
    p("The algorithm is: while there are active events, execute one. When "
      "the active region is empty, move all inactive events to active; when "
      "both are empty, move all NBA updates to active. Updates wake more "
      "processes, which may issue more events, and the loop continues until "
      "nothing is left; then the monitor region runs and time advances. "
      "Each pass through Active -> NBA is informally called a **delta "
      "cycle**.")
    code([
        'module tb_regions;',
        '  reg [3:0] q = 0;',
        '  initial begin',
        '    #10;',
        "    q <= 4'd5;                                   // NBA region",
        '    $display ("display : q=%0d (active region: old value)", q);',
        '    $strobe  ("strobe  : q=%0d (postponed/monitor region: final value)", q);',
        '    #0 $display("after #0: q=%0d (inactive region: NBA not yet done)", q);',
        "    q = 4'd7;                                    // blocking, same time step",
        '    $display ("display : q=%0d after blocking q=7", q);',
        '  end',
        '  initial #10 $monitor("monitor : q=%0d at t=%0t (printed once per time step)", q, $time);',
        'endmodule',
    ], "What $display, #0, $strobe and $monitor see "
         "when a variable is written with <= and = in the same slot "
         "(c5_regions.v).")
    out([
        'display : q=0 (active region: old value)',
        'after #0: q=0 (inactive region: NBA not yet done)',
        'display : q=7 after blocking q=7',
        'strobe  : q=5 (postponed/monitor region: final value)',
        'monitor : q=5 at t=10 (printed once per time step)',
    ], "Output (Icarus Verilog 12).")
    bul(["`$display` runs in the active region, before the NBA update: it "
         "prints the old value 0.",
         "`#0` moves the process to the inactive region, which still runs "
         "before NBA: still 0. This is why `#0` does not fix races "
         "involving non-blocking assignments.",
         "The blocking `q = 7` takes effect immediately, but the NBA update "
         "to 5 scheduled earlier is applied afterwards and wins: the final "
         "value is 5 - mixing `=` and `<=` on one variable gives results "
         "that depend on region order, not text order.",
         "`$strobe` and `$monitor` run in the monitor region and see the "
         "final, settled value. Use them (or sample after the edge) when "
         "printing values of registers updated with `<=`."])
    box("key", "What the standard does and does not guarantee",
        "Guaranteed: statements inside one `begin-end` execute in order; "
        "NBA updates from one process are applied in the order they were "
        "issued; regions are processed in the order above. Not guaranteed: "
        "the order in which different processes that are active at the same "
        "time execute, and even whether a process runs to its next timing "
        "control without being interleaved (the LRM explicitly allows a "
        "simulator to suspend a process and run another). Any result that "
        "depends on the unguaranteed part is a **race**.")
    h3("Preview: the SystemVerilog scheduler")
    p("IEEE 1800 refines the scheduler into many more regions so that "
      "testbench code and assertions can run at well-defined points relative "
      "to the design (details in Chapters 21 and 22):")
    diagram([
        "  Preponed   sample values for assertions and clocking blocks (read-only)",
        "     |",
        "  Active -> Inactive -> NBA      design evaluation (same as Verilog)",
        "     |      ^__________________| iterate",
        "  Observed   evaluate concurrent assertion properties",
        "     |",
        "  Reactive -> Re-Inactive -> Re-NBA   program blocks, assertion action blocks,",
        "     |           ^________________|   testbench drives (iterate; may re-enter Active)",
        "  Postponed  $monitor, $strobe, end of slot (read-only)",
        "",
        "  (Pre-/Post- regions exist for the PLI/VPI and are not used by SV code.)",
    ], "Simplified IEEE 1800 time slot.")

    # ------------------------------------------------------------------
    h2("Races, demonstrated")
    p("A race occurs when the result depends on the order in which "
      "simultaneously active processes execute. The following example has "
      "two of them: two `always` blocks at the same edge, one writing `a` "
      "with `=` and one reading it; and a testbench that changes the DUT's "
      "input with `=` on the same edge that the DUT samples it. A macro "
      "swaps the textual order of the first two blocks.")
    code([
        'module tb_race;',
        '  reg clk = 0;',
        '  reg [3:0] a = 0, b = 0, d = 0, q = 0;',
        '  always #5 clk = ~clk;',
        '',
        '`ifdef SWAP',
        '  always @(posedge clk) b = a;         // reader first in the source',
        '  always @(posedge clk) a = a + 1;     // writer second',
        '`else',
        '  always @(posedge clk) a = a + 1;     // writer first in the source',
        '  always @(posedge clk) b = a;         // reader: old or new a?  Unspecified!',
        '`endif',
        '  always @(posedge clk) q <= d;        // a "DUT" flop',
        '  initial begin',
        "    @(posedge clk) d = 4'd9;           // racy stimulus: blocking on the sampling edge",
        '    #1 $display("after edge 1: a=%0d b=%0d q=%0d (flop saw %s d)",',
        '                a, b, q, (q == 9) ? "NEW" : "OLD");',
        '    $finish;',
        '  end',
        'endmodule',
    ], "Two classic races (c5_race.v). Compiled with "
         "and without -DSWAP.")
    tbl(["Simulator", "Source order", "b (reader of a)", "q (flop fed by "
         "racy d)"],
        [["Icarus Verilog 12", "writer first", "0 (old value)", "9 (new)"],
         ["Icarus Verilog 12", "reader first (SWAP)", "1 (new value)",
          "9 (new)"],
         ["Verilator 5.020", "writer first", "1 (new value)", "9 (new)"],
         ["Verilator 5.020", "reader first (SWAP)", "0 (old value)",
          "9 (new)"]],
        widths=[25, 25, 25, 25], bold_first=True,
        caption="Results of the four runs; each is a verbatim `after edge 1` "
        "line below.")
    out([
        'after edge 1: a=1 b=0 q=9 (flop saw NEW d)',
    ] + [
        'after edge 1: a=1 b=1 q=9 (flop saw NEW d)',
    ],
        "Icarus Verilog 12: default order, then with -DSWAP.")
    out([
        'after edge 1: a=1 b=1 q=9 (flop saw NEW d)',
    ] + [
        'after edge 1: a=1 b=0 q=9 (flop saw NEW d)',
    ],
        "Verilator 5.020: default order, then with -DSWAP.")
    p("The two simulators give **opposite** answers for the same source, "
      "and each changes its answer when two independent blocks are "
      "reordered - a change that means nothing in hardware. Both behaviours "
      "are legal. In the second race, both simulators happened to let the "
      "testbench write `d` before the flop sampled it, so the flop captured "
      "the new value on the same edge - one cycle earlier than real "
      "hardware would. That kind of \"luck\" typically flips when an "
      "unrelated change is made to the testbench, or when moving to a "
      "different simulator at the end of the project. Driving `d` with a "
      "non-blocking assignment removes the race:")
    code(["    @(posedge clk) d <= 4'd9;          // fixed: NBA"],
         "The one-line fix in c5_race_fix.v.")
    out([
        'after edge 1: a=1 b=0 q=0 (flop saw OLD d)',
    ], "Output (Icarus Verilog 12): the flop "
        "now sees the old value of d on edge 1, as real hardware would.")
    tbl(["Race", "Symptom", "Cure"],
        [["Write-read between `always` blocks at one edge", "Reader sees old "
          "or new value depending on order", "`<=` for all clocked "
          "assignments"],
         ["Write-write: two processes assign one variable", "Last writer "
          "wins, unpredictably", "One `always` block per variable"],
         ["Testbench vs DUT at the sampling edge", "DUT sees stimulus a "
          "cycle early, sometimes", "Drive with `<=`, drive on the opposite "
          "edge, or use clocking blocks (Chapter 21)"],
         ["Time-0 initialisation", "`always` blocks see or miss the "
          "initial x -> value event", "Reset logic; SV initialisers; avoid "
          "relying on time-0 events"],
         ["`$display` of `<=` targets", "Printed value is one cycle old",
          "`$strobe`, or sample after the edge"]],
        widths=[30, 35, 35], bold_first=True)
    box("expert", "Interview question: does a race exist in "
        "always @(posedge clk) a = b; always @(posedge clk) b = a;?",
        "Yes. If the first block runs first, both end up with the old `b`; if "
        "the second runs first, both end up with the old `a`. Neither is a "
        "swap. With non-blocking assignments, both right-hand sides are "
        "evaluated in the active region and both updates happen in the NBA "
        "region, so the values are swapped every clock regardless of order - "
        "which is also what the synthesized pair of flip-flops does.")

    h2("Summary")
    bul(["Every `assign`, primitive, `initial` and `always` is a concurrent "
         "process; procedural blocks suspend only at timing controls.",
         "Continuous-assignment delays are inertial (short pulses are "
         "filtered); `a <= #d b` gives transport behaviour.",
         "Blocking `=` updates immediately; non-blocking `<=` evaluates now "
         "and updates in the NBA region. Use `<=` for clocked logic and `=` "
         "for combinational logic.",
         "Regular delays wait before sampling; intra-assignment delays "
         "sample first and assign later.",
         "posedge/negedge include transitions through x and z; `wait` is "
         "level-sensitive, `@` edge-sensitive; named events are lost if "
         "nobody is waiting.",
         "The Verilog time slot runs Active -> Inactive -> NBA until "
         "quiescent, then Monitor; SystemVerilog adds Preponed, Observed, "
         "Reactive and Postponed regions.",
         "Process order within a region is unspecified; code that depends on "
         "it is a race and can give different results on different "
         "simulators, as demonstrated."])

    h2("Exercises")
    bul(["Rewrite the blocking pipeline of Section 5.4 so that it works with "
         "blocking assignments only, by reordering the statements. Why is "
         "this still a bad idea?",
         "What does `wire #5 y = a;` do with a 4 ns pulse on `a`? With a 6 ns "
         "pulse? Write a model of a 5 ns transport delay line and show "
         "that it passes the 4 ns pulse.",
         "Predict the output of `initial begin a = 0; a <= 1; $display(a); "
         "#0 $display(a); $strobe(a); a = 2; end`.",
         "A testbench generates a clock with `always #5 clk = ~clk;` and "
         "drives inputs with `@(posedge clk) data = $random;`. Explain the "
         "race and give three different fixes.",
         "Explain why `@(ready)` can hang where `wait (ready)` does not, and "
         "construct a case where the opposite causes a bug (the process "
         "fails to wait when it should).",
         "Draw the regions visited in one time slot for a design with one "
         "flip-flop (`q <= d`), a continuous assignment `assign d = ~q`, and "
         "a `$monitor` on `q`, starting from the posedge of the clock."],
        ordered=True)


# =============================================================================
#        Chapter 6 - Control flow, functions and tasks
# =============================================================================
def _ch6():
    chapter("Control Flow, Functions and Tasks")
    p("Inside `initial` and `always` blocks, Verilog offers the familiar "
      "statements of a structured language - `if`, `case`, loops, "
      "subroutines - with two twists: every condition is evaluated in "
      "four-state logic, and code that describes hardware must avoid "
      "constructs that cannot be unrolled into a fixed circuit. This chapter "
      "covers each statement with its exact semantics for `x` and `z`, its "
      "use in RTL and in testbenches, and the pitfalls that make functions "
      "and tasks behave differently from their software counterparts.")

    # ------------------------------------------------------------------
    h2("if / else")
    code([
        "if (cond) statement;                     // cond is x or z -> treated as false",
        "else if (cond2) begin ... end",
        "else statement;",
        "",
        "// dangling else: an 'else' binds to the NEAREST preceding 'if'",
        "if (a)",
        "  if (b) y = 1;",
        "else     y = 0;        // belongs to 'if (b)', despite the indentation!",
    ], "Syntax fragment; the last lines show the dangling-else rule.")
    bul(["The condition is true if it is non-zero and known; if it is zero, "
         "`x` or `z` the `else` branch runs (Chapter 4 demonstrated this). "
         "`if (a == b)` with an unknown bit in `a` therefore silently takes "
         "the else path.",
         "In combinational RTL, an `if` without `else` (or a variable not "
         "assigned on every path) implies storage: synthesis infers a "
         "**latch**. Assign defaults at the top of the block or cover every "
         "path.",
         "An `if-else if` chain describes a **priority** structure: the first "
         "true condition wins, and synthesis builds a chain of multiplexers "
         "(or equivalent logic) in that order.",
         "Always use `begin ... end` for multi-line branches; the "
         "dangling-else fragment above is a real bug pattern that the "
         "indentation hides."])

    # ------------------------------------------------------------------
    h2("case, casez and casex")
    p("A `case` statement compares its **case expression** with each **case "
      "item** in order and executes the first match; there is no fall-through "
      "and no `break`. Several items may share a statement (`2'b01, 2'b10: "
      "...`), and `default` catches everything else. The three variants "
      "differ only in how they compare:")
    tbl(["Statement", "Comparison", "x in expression or item", "z / ? in "
         "expression or item"],
        [["`case`", "Exact 4-state match (like `===`)", "Must match an `x` "
          "literally", "Must match a `z` literally"],
         ["`casez`", "z and ? bits are don't-care", "Must match literally",
          "**Don't care** - in either the item or the expression"],
         ["`casex`", "x, z and ? bits are don't-care", "**Don't care** - in "
          "either", "**Don't care** - in either"]],
        widths=[12, 28, 30, 30], bold_first=True)
    p("The phrase \"in either\" is what makes the variants dangerous: a "
      "don't-care bit in the __expression__, which is usually a signal, "
      "matches anything. The testbench below runs four selector values "
      "through all three variants:")
    code([
        'module tb_case;',
        '  reg [1:0] s;',
        '  integer i;',
        '  reg [1:0] vals [0:3];',
        '  task run;',
        '    begin',
        '      case (s)                    // exact 4-state match (=== per item)',
        '        2\'b00:   $write("case :00     ");',
        '        2\'b1x:   $write("case :1x     ");',
        '        2\'bzz:   $write("case :zz     ");',
        '        default: $write("case :dflt   ");',
        '      endcase',
        "      casez (s)                   // z / ? in item OR selector = don't care",
        '        2\'b0?:   $write("casez:0?     ");',
        '        2\'b1?:   $write("casez:1?     ");',
        '        default: $write("casez:dflt   ");',
        '      endcase',
        "      casex (s)                   // x AND z in item OR selector = don't care",
        '        2\'b00:   $display("casex:00");',
        '        2\'b1x:   $display("casex:1x");',
        '        default: $display("casex:dflt");',
        '      endcase',
        '    end',
        '  endtask',
        '  initial begin',
        "    vals[0] = 2'b10; vals[1] = 2'b1x; vals[2] = 2'bzz; vals[3] = 2'bx0;",
        '    for (i = 0; i < 4; i = i + 1) begin',
        '      s = vals[i]; $write("s=%b | ", s); run;',
        '    end',
        '  end',
        'endmodule',
    ], "case, casez and casex with known, x and z "
         "selectors (c6_case.v).")
    out([
        's=10 | case :dflt   casez:1?     casex:1x',
        's=1x | case :1x     casez:1?     casex:1x',
        's=zz | case :zz     casez:0?     casex:00',
        's=x0 | case :dflt   casez:dflt   casex:00',
    ], "Output (Icarus Verilog 12).")
    bul(["`s=10`: plain `case` finds no exact match (the item `2'b1x` "
         "requires a literal x) and takes the default; `casez` and `casex` "
         "match on the don't-care bits.",
         "`s=1x`: `case` matches the literal `2'b1x` - useful in testbenches "
         "to detect unknowns, meaningless in hardware.",
         "`s=zz`: in `casez` the selector's own z bits are wildcards, so it "
         "matches the **first** item `2'b0?`; in `casex` it matches `2'b00`.",
         "`s=x0`: an **unknown** selector makes `casex` match `2'b00` and "
         "execute that branch as if everything were fine. In RTL simulation "
         "this hides an uninitialised or corrupted control signal - the "
         "gates would do something else entirely."])
    box("warn", "Pitfall: casex in RTL",
        "Because `casex` treats an `x` in the selector as a wildcard, it "
        "turns X-propagation into X-masking: the simulation proceeds down a "
        "branch chosen by the item order, while real hardware might take any "
        "branch. Most coding standards ban `casex` in RTL. Use `casez` with "
        "`?` in the items for wildcard decoding (it still masks `z`, which is "
        "rare in RTL), or SystemVerilog's `case (...) inside` with `?` "
        "wildcards, which treats x/z in the **expression** as ordinary "
        "values (Chapter 14). Add an assertion that the selector is known.")
    box("expert", "full_case and parallel_case",
        "A case statement whose items do not cover all values implies a latch "
        "in a combinational block; one whose items overlap describes "
        "priority logic. The synthesis pragmas `// synopsys full_case` and "
        "`// synopsys parallel_case` tell synthesis to assume the case is "
        "complete or mutually exclusive __without telling the simulator__ - "
        "the textbook source of simulation/synthesis mismatch (Chapter 11). "
        "SystemVerilog's `unique` and `priority` keywords (Chapter 14) give "
        "the same optimisation with simulator checks, and replace the "
        "pragmas in modern code.")

    # ------------------------------------------------------------------
    h2("Loops")
    tbl(["Loop", "Form", "Notes"],
        [["`for`", "`for (i = 0; i < N; i = i + 1) stmt`", "Verilog-2005 has "
          "no `++`, no `+=` and no loop-local declaration (all added by SV); "
          "the variable is usually an `integer` or a `genvar` in generate"],
         ["`while`", "`while (cond) stmt`", "Condition re-evaluated before "
          "each iteration; x/z counts as false"],
         ["`repeat`", "`repeat (n) stmt`", "`n` is evaluated **once** at the "
          "start; x or z means zero iterations"],
         ["`forever`", "`forever stmt`", "Infinite; must contain a timing "
          "control; left only with `disable` or `$finish`"],
         ["(SV) `do ... while`, `foreach`, `break`, `continue`", "-",
          "Chapter 14"]],
        widths=[14, 36, 50], bold_first=True)
    code([
        'module tb_loops;',
        "  reg [7:0] data = 8'b0010_1100;",
        '  integer i, n, first_one;',
        '  reg clk = 0;',
        '  initial begin',
        '    // for: count ones',
        '    n = 0;',
        '    for (i = 0; i < 8; i = i + 1) n = n + data[i];',
        '    $display("for    : popcount = %0d", n);',
        '    // while + disable of a named block = "break"',
        '    first_one = -1; i = 0;',
        '    begin : search',
        '      while (i < 8) begin',
        '        if (data[i]) begin first_one = i; disable search; end',
        '        i = i + 1;',
        '      end',
        '    end',
        '    $display("while  : lowest set bit = %0d", first_one);',
        '    // disable of the inner named block = "continue"',
        '    n = 0;',
        '    for (i = 0; i < 8; i = i + 1) begin : body',
        '      if (i % 2) disable body;           // skip odd i',
        '      n = n + data[i];',
        '    end',
        '    $display("for    : ones in even positions = %0d", n);',
        '    // repeat: fixed count, expression evaluated once',
        '    n = 3; i = 0;',
        '    repeat (n) begin n = n + 1; i = i + 1; end',
        '    $display("repeat : ran %0d times although n grew to %0d", i, n);',
        '  end',
        '  // forever: clock generator stopped by disable from another process',
        '  initial begin : clkgen',
        '    forever #5 clk = ~clk;',
        '  end',
        '  initial begin',
        '    #23 disable clkgen;',
        '    #50 $display("forever: clk frozen at %b, t=%0t", clk, $time);',
        '  end',
        'endmodule',
    ], "Loops, and named blocks with disable used as "
         "break and continue (c6_loops.v).")
    out([
        'for    : popcount = 3',
        'while  : lowest set bit = 2',
        'for    : ones in even positions = 1',
        'repeat : ran 3 times although n grew to 6',
        'forever: clk frozen at 0, t=73',
    ], "Output (Icarus Verilog 12). "
        "data = 8'b0010_1100.")
    p("Verilog-2005 has no `break` or `continue`. Both are built from a "
      "**named block** and `disable`: `disable search;` terminates the "
      "named block `search` that encloses the loop (break), while "
      "`disable body;` inside the loop body ends only the current iteration, "
      "and the `for` continues with its step statement (continue). "
      "`disable clkgen;` from another process kills a `forever` loop.")
    h3("Loops in synthesizable code")
    p("Synthesis **unrolls** loops: every iteration becomes a copy of the "
      "hardware. A loop is therefore synthesizable only if its iteration "
      "count is fixed at elaboration (constant bounds), and its body must "
      "not contain timing controls. The popcount above synthesizes to an "
      "adder tree of eight 1-bit inputs; the `while` search to a priority "
      "encoder. A loop bound that depends on a signal (`while (x != 0)`) "
      "does not describe hardware of fixed size and is rejected - or "
      "worse, unrolled to a tool limit.")

    # ------------------------------------------------------------------
    h2("Named blocks and disable")
    p("Any `begin ... end` or `fork ... join` can be named with `: name`. A "
      "named block creates a new **scope**: it may declare local variables "
      "(in Verilog-2005 only in named blocks), appears in the hierarchy "
      "(`tb.search.k`), and can be terminated by `disable name` from inside "
      "or outside. `disable task_name` terminates a running task. "
      "Disabling a block that is not currently executing does nothing.")
    box("warn", "Pitfall: disable kills every activation",
        "`disable name` terminates all currently active executions of that "
        "block or task, from every caller - not just the one you meant. "
        "In a static task called from two processes, or a named block inside "
        "a task that runs concurrently, one `disable` stops them all. "
        "SystemVerilog's `disable fork`, process handles (`process::self()`, "
        "`kill()`) and `break`/`continue`/`return` provide finer control "
        "(Chapter 20).")

    # ------------------------------------------------------------------
    h2("Functions")
    p("A function computes a value in zero simulated time. It is called in "
      "an expression, returns a value through its own name (or `return` in "
      "SystemVerilog), and in synthesizable code becomes combinational "
      "logic inlined at every call.")
    tbl(["Rule (Verilog-2005)", "Consequence"],
        [["At least one `input` argument; no `output` or `inout` (SV allows "
          "them, and void functions)", "Functions return exactly one value"],
         ["No timing controls (`#`, `@`, `wait`), no task calls",
          "Always executes in zero time; can be used in continuous "
          "assignments"],
         ["No non-blocking assignments, no event triggers", "It cannot "
          "schedule side effects"],
         ["Return type given by a range, `integer`, `real`, `signed`...",
          "`function [7:0] f`; default 1 bit - a classic truncation bug"],
         ["Static by default: arguments and locals are allocated once per "
          "module instance", "Concurrent or recursive calls share storage"],
         ["`function automatic`: new storage for each call", "Recursion and "
          "reentrancy work; locals cannot be accessed hierarchically or "
          "assigned with `<=`"]],
        widths=[52, 48], bold_first=True)
    code([
        'module fifo_ctrl #(parameter DEPTH = 20) (output wire [AW-1:0] addr_w);',
        '  // Constant function: evaluated at elaboration to size a port/localparam',
        '  function integer clog2 (input integer value);',
        '    integer v;',
        '    begin',
        '      v = value - 1;',
        '      for (clog2 = 0; v > 0; clog2 = clog2 + 1) v = v >> 1;',
        '    end',
        '  endfunction',
        '  localparam AW = clog2(DEPTH);',
        "  assign addr_w = {AW{1'b0}};",
        'endmodule',
        '',
        'module tb_func;',
        '  wire [4:0] w;                         // 5 = clog2(20)',
        '  fifo_ctrl #(.DEPTH(20)) u (.addr_w(w));',
        '',
        '  function automatic integer fact (input integer n);   // recursion needs automatic',
        '    fact = (n <= 1) ? 1 : n * fact(n - 1);',
        '  endfunction',
        '',
        '  function integer fact_static (input integer n);      // static: one copy of n',
        '    fact_static = (n <= 1) ? 1 : fact_static(n - 1) * n;',
        '  endfunction',
        '',
        '  function [7:0] reverse (input [7:0] x);              // result width = 8',
        '    integer k;',
        '    for (k = 0; k < 8; k = k + 1) reverse[k] = x[7-k];',
        '  endfunction',
        '',
        '  initial begin',
        '    $display("AW for DEPTH=20 : %0d", u.AW);',
        '    $display("fact(5)         : %0d", fact(5));',
        '    $display("fact_static(5)  : %0d  (static: recursive calls share n)", fact_static(5));',
        '    $display("reverse(8\'b1101_0000) = %b", reverse(8\'b1101_0000));',
        '  end',
        'endmodule',
    ], "A constant function sizing a port, an automatic "
         "recursive function, the same function left static, and a bit "
         "reverser (c6_func.v).")
    out([
        'AW for DEPTH=20 : 5',
        'fact(5)         : 120',
        'fact_static(5)  : 1  (static: recursive calls share n)',
        "reverse(8'b1101_0000) = 00001011",
    ], "Output (Icarus Verilog 12).")
    bul(["`clog2` is a **constant function**: called with constant "
         "arguments in a constant expression (a `localparam`), it is "
         "evaluated during elaboration. Constant functions may use only "
         "their arguments, locals, parameters and other constant functions "
         "- no hierarchical references and no global variables. This is how "
         "legacy code computed address widths; IEEE 1364-2005 added the "
         "built-in `$clog2`, which new code should use.",
         "`fact` is `automatic`, so each recursive call has its own `n`: "
         "120.",
         "`fact_static` is identical except that it is static. Every "
         "recursive call overwrites the single shared `n`; by the time the "
         "multiplications run, `n` is 1 at every level, and the result is 1. "
         "(With the operands in the other order, `n * f(n-1)`, Icarus happens "
         "to read `n` before the call and prints 120 - the result depends on "
         "operand evaluation order, which is unspecified.)",
         "`reverse` shows the declared return width `[7:0]`; without it the "
         "function would return 1 bit."])

    # ------------------------------------------------------------------
    h2("Tasks")
    p("A task is a subroutine that may consume time. It is called as a "
      "statement, may have any number of `input`, `output` and `inout` "
      "arguments, may contain timing controls, may call other tasks and "
      "functions, and returns no value (SystemVerilog adds `return` and "
      "`ref` arguments). Tasks are the backbone of Verilog testbenches: bus "
      "functional models are sets of tasks such as `write(addr, data)` and "
      "`read(addr, data)` (Chapter 25).")
    p("Two semantic details cause most task bugs. First, arguments are "
      "passed **by value**: inputs are copied in when the task is called, and "
      "outputs are copied out **only when it returns**. Second, tasks are "
      "**static** by default, like functions: all concurrent callers share "
      "the same argument and local storage.")
    code([
        '`timescale 1ns/1ns',
        'module tb_task;',
        "  // STATIC task: one shared copy of 'id' and 'dly' for all callers",
        '  task send_static (input [7:0] id, input integer dly);',
        '    begin',
        '      #dly $display("t=%0t static    : finished id=%0d", $time, id);',
        '    end',
        '  endtask',
        '  // AUTOMATIC task: each call gets its own stack frame',
        '  task automatic send_auto (input [7:0] id, input integer dly);',
        '    begin',
        '      #dly $display("t=%0t automatic : finished id=%0d", $time, id);',
        '    end',
        '  endtask',
        '  // output arguments are copied back only when the task returns',
        '  task pulse (output reg q, input integer width);',
        '    begin',
        '      q = 1; #width q = 0;',
        '    end',
        '  endtask',
        '  reg p = 0;',
        '  initial begin',
        '    fork',
        "      send_static(8'd1, 10);        // both calls run concurrently...",
        "      send_static(8'd2, 3);         // ...the second overwrites id and dly",
        '    join',
        '    fork',
        "      send_auto(8'd1, 10);",
        "      send_auto(8'd2, 3);",
        '    join',
        '    fork',
        '      pulse(p, 5);',
        '      #2 $display("t=%0t p=%b inside pulse (output not copied yet)", $time, p);',
        '    join',
        '    $display("t=%0t p=%b after pulse returned", $time, p);',
        '  end',
        'endmodule',
    ], "A static task called concurrently, the same "
         "task declared automatic, and an output argument that never shows "
         "its pulse (c6_task.v).")
    out([
        't=3 static    : finished id=1',
        't=10 static    : finished id=1',
        't=13 automatic : finished id=2',
        't=20 automatic : finished id=1',
        't=22 p=0 inside pulse (output not copied yet)',
        't=25 p=0 after pulse returned',
    ], "Output (Icarus Verilog 12).")
    bul(["Both concurrent calls of the static `send_static` report `id=1`: "
         "the two calls share one `id` variable, and whichever call wrote it "
         "last wins (here the fork happened to start the second call first). "
         "The delays still differ because each `#dly` was evaluated when its "
         "call started.",
         "With `automatic`, each call has its own frame and both report their "
         "own `id` correctly.",
         "The `pulse` task sets its output `q` to 1 and back to 0, but the "
         "caller's `p` is updated only on return, with the final value 0: the "
         "pulse never appears. A task that must wiggle a signal over time "
         "has to assign the module-level signal directly (a side effect), or, "
         "in SystemVerilog, take it as a `ref` argument or drive it through a "
         "virtual interface."])
    box("key", "Make testbench tasks and functions automatic",
        "Any subroutine that may be called from more than one process at a "
        "time - which is every BFM task in a testbench with parallel "
        "threads - must be `automatic`. In SystemVerilog, subroutines "
        "declared inside classes are always automatic, and a whole module or "
        "program can be made automatic with `module automatic m;`. Static "
        "subroutines remain the default in modules for backward "
        "compatibility, and they remain appropriate for synthesizable "
        "functions, where static and automatic behave identically.")
    tbl(["", "Function", "Task"],
        [["Called as", "Expression operand", "Statement"],
         ["Timing controls", "Not allowed", "Allowed"],
         ["Arguments", "Inputs only (Verilog); SV adds output/inout/ref",
          "input, output, inout (SV adds ref)"],
         ["Returns", "One value", "Nothing (values through outputs)"],
         ["Can call", "Functions", "Functions and tasks"],
         ["Synthesizable", "Yes (combinational logic)", "Only without timing "
          "controls; rarely used in RTL"],
         ["Default lifetime", "Static in modules", "Static in modules"]],
        widths=[20, 40, 40], bold_first=True)

    # ------------------------------------------------------------------
    h2("fork ... join in Verilog")
    p("`begin ... end` executes its statements in sequence; `fork ... join` "
      "starts all of them **in parallel** at the same simulation time and "
      "continues only when **all** have finished. Each statement in the fork "
      "is a separate process, so delays inside different branches are all "
      "measured from the moment the fork started. Verilog has only `join`; "
      "SystemVerilog adds `join_any`, `join_none` and `disable fork` "
      "(Chapter 20).")
    code([
        '`timescale 1ns/1ns',
        'module tb_fork;',
        '  reg ack = 0;',
        '  initial #35 ack = 1;                         // the "DUT" answers at t=35',
        '  initial begin',
        '    fork                                       // all statements start at t=0',
        '      #10 $display("t=%0t branch A done", $time);',
        '      #30 $display("t=%0t branch B done", $time);',
        '      begin #5 $display("t=%0t branch C step 1", $time);',
        '            #5 $display("t=%0t branch C step 2", $time); end',
        '    join                                       // waits for the LAST branch',
        '    $display("t=%0t join complete", $time);',
        '    // Verilog timeout idiom: race a wait against a timer, kill the loser',
        '    fork : wait_or_timeout',
        '      begin @(posedge ack) $display("t=%0t ack received", $time);',
        '            disable wait_or_timeout; end',
        '      begin #50 $display("t=%0t TIMEOUT waiting for ack", $time);',
        '            disable wait_or_timeout; end',
        '    join',
        '    $display("t=%0t continuing after the race", $time);',
        '  end',
        'endmodule',
    ], "Parallel branches, and the Verilog idiom for a "
         "timeout: two branches race and the winner disables the named fork "
         "(c6_fork.v).")
    out([
        't=5 branch C step 1',
        't=10 branch A done',
        't=10 branch C step 2',
        't=30 branch B done',
        't=30 join complete',
        't=35 ack received',
        't=35 continuing after the race',
    ], "Output (Icarus Verilog 12).")
    bul(["The `join` completes at t=30, when the slowest branch (B) "
         "finishes. Branch C is itself sequential: its two steps run at t=5 "
         "and t=10.",
         "In the timeout idiom, whichever branch finishes first executes "
         "`disable wait_or_timeout`, which kills the other branch and ends "
         "the fork. Here `ack` rises at t=35, before the 50 ns timeout.",
         "The order in which simultaneous branches start is unspecified - "
         "the static task example above depended on it.",
         "`fork ... join` is not synthesizable; it belongs to testbenches "
         "and behavioural models."])

    h2("Summary")
    bul(["`if` treats x/z as false and takes the else branch; an incomplete "
         "`if` in combinational logic infers a latch; `else` binds to the "
         "nearest `if`.",
         "`case` compares with 4-state exactness; `casez` treats z/? as "
         "don't-care and `casex` also x - in the item **and** the selector, "
         "which makes `casex` mask unknowns. Prefer `casez` with `?`, or SV "
         "`case inside`.",
         "`for`, `while`, `repeat` (count evaluated once) and `forever`; "
         "`break`/`continue` are built with named blocks and `disable` in "
         "Verilog-2005. Synthesizable loops must have constant bounds.",
         "Functions: zero time, at least one input, one return value, static "
         "by default; `automatic` for recursion; constant functions run at "
         "elaboration ($clog2 replaces the hand-written ones).",
         "Tasks: may consume time; arguments copied in at call and out at "
         "return; static by default, so concurrent calls corrupt each other "
         "unless declared `automatic`.",
         "`fork ... join` runs branches in parallel and waits for all; a "
         "named fork plus `disable` implements timeouts."])

    h2("Exercises")
    bul(["Write a priority encoder for an 8-bit request vector three ways - "
         "`if-else if`, `casez` with `?` items, and a `for` loop - and "
         "verify that they agree on all 256 inputs. Which one gives an "
         "`x`-free output for an input containing `x`?",
         "Show a selector value for which `case`, `casez` and `casex` all "
         "choose different branches of the same item list.",
         "Rewrite `fact_static` so that it returns 120 while remaining static, "
         "without recursion. Then explain why a static function is fine in "
         "synthesizable code.",
         "Write a testbench task `apply_reset(input integer cycles)` and a "
         "task `send_byte` that drives a serial line bit by bit. Which of "
         "them must be automatic if two instances of a UART model call "
         "`send_byte` concurrently? What goes wrong otherwise?",
         "Implement a watchdog: a `fork` that waits for `done`, a timeout "
         "branch, and a third branch that prints a progress message every "
         "100 ns. Make sure all branches stop when the fork is left.",
         "A `repeat (count)` loop is used while `count` is modified inside the "
         "loop body. How many iterations run? What if `count` is `x`?"],
        ordered=True)

