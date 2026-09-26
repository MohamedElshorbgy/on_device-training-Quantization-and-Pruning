"""Part V - Verification (Chapters 22-26) of the RTL guide.

Every testbench shown with an out() card was run with Icarus Verilog 12
(iverilog -g2012 -Wall / vvp); lint and formal outputs come from Verilator
5.020 and Yosys 0.33. SVA concurrent assertions, covergroups, constrained
randomization, clocking blocks, virtual interfaces and UVM are shown without
output because Icarus does not support them.
"""

from rtl_guide.common import *  # noqa: F401,F403


def part5():
    part("Verification",
         "Verification consumes more engineering effort than design on every "
         "modern chip. This part teaches the craft from the ground up: "
         "self-checking testbenches, assertions and coverage, the UVM "
         "methodology used across the industry, the static sign-off checks "
         "(lint, CDC, formal, equivalence) that catch what simulation "
         "misses, and the debug, gate-level, FPGA-prototyping and emulation "
         "techniques that carry a design all the way to silicon.")
    ch22()
    ch23()
    ch24()
    ch25()
    ch26()


# =============================================================================
#                 Chapter 22 - Self-checking testbenches
# =============================================================================
def ch22():
    chapter("Self-Checking Testbenches in SystemVerilog", newpage=False)
    p("A design that has not been verified does not work - it only has not "
      "failed yet. On a typical SoC project there are two to three "
      "verification engineers for every designer, and the verification code "
      "base is larger than the RTL it checks. Even so, the most important "
      "verification skill for an RTL designer is not UVM or formal: it is "
      "the ability to write a small, **self-checking** testbench in an "
      "afternoon that proves a block does what the spec says, and keeps "
      "proving it every night in regression.")
    p("A testbench is __self-checking__ when it decides pass or fail by "
      "itself, by comparing what the DUT (device under test) does against an "
      "independent prediction. Nobody looks at waveforms to decide whether "
      "the test passed; waveforms are for debugging a test that has already "
      "failed. This chapter builds that discipline with plain SystemVerilog "
      "that runs on any simulator, including the open-source Icarus Verilog "
      "used throughout this book. Chapter 23 adds assertions and coverage, "
      "and Chapter 24 scales the same architecture up to UVM.")

    h2("Why self-checking, and what it must check")
    tbl(["Approach", "How pass/fail is decided", "Scales to"],
        [["Eyeball the waveform", "A human looks at signals once",
          "One block, one afternoon, never again"],
         ["Golden log diff", "Compare a printed log with a saved 'good' log",
          "Breaks on every harmless change of print format or timing"],
         ["**Self-checking**", "TB predicts every output and compares "
          "automatically; ends with PASS/FAIL and an error count",
          "Thousands of seeds in nightly regression, CI gating"],
         ["Self-checking + assertions + coverage",
          "Plus protocol rules checked every cycle and a measure of what was "
          "exercised", "Sign-off of an IP or SoC (Chapters 23-24)"]],
        widths=[22, 45, 33], bold_first=True)
    p("A good self-checking testbench answers three questions, and a weak one "
      "answers only the first: **(1)** Did every output that should have "
      "appeared appear, with the right value? **(2)** Did nothing appear that "
      "should not have (spurious outputs, duplicated beats, wrong flags)? "
      "**(3)** Did the test actually exercise the interesting cases (full, "
      "empty, overflow, back-pressure, reset in the middle)? Question 3 is "
      "the job of functional coverage (Chapter 23).")

    h2("Testbench architecture")
    p("Every serious testbench - from a 60-line module to a million-line UVM "
      "environment - has the same layers. Learning them once, on a small "
      "example, is the fastest way to understand UVM later, because UVM is "
      "only this picture expressed as reusable classes.")
    diagram([
        "  +-----------------+      transactions      +-------------------------+",
        "  | stimulus / test | ---------------------> | driver (BFM)            |",
        "  | directed+random |                        | txn -> pin wiggles      |",
        "  +-----------------+                        +-----------+-------------+",
        "           |                                             | pins",
        "           | (same txns)                                 v",
        "           |                                   +-------------------+",
        "           |                                   |       DUT         |",
        "           |                                   +---------+---------+",
        "           v                                             | pins",
        "  +-----------------+   expected    +------------+       v",
        "  | reference model | ------------> | scoreboard | <-- +-------------+",
        "  | (spec, not RTL) |               | compare,   |     | monitor     |",
        "  +-----------------+               | count errs |     | pins -> txn |",
        "                                    +------------+     +-------------+",
        "                                       |  PASS / FAIL + error count",
    ], "The layered testbench. The monitor observes pins passively; the "
       "reference model predicts from the spec; the scoreboard compares.")
    tbl(["Component", "Responsibility", "Typical form in plain SV"],
        [["Clock/reset generator", "Free-running clock; reset asserted, "
          "then released synchronously", "`always #5 clk = ~clk;` + an "
          "`initial` block"],
         ["Stimulus (test)", "Decides WHAT to send: directed sequences, "
          "random mixes, corner cases", "`initial` block calling tasks"],
         ["Driver / BFM", "Decides HOW: converts a transaction into "
          "cycle-accurate pin activity, obeys the protocol", "A `task` per "
          "transaction type (`push`, `apb_write`)"],
         ["Monitor", "Passively watches pins and reconstructs transactions; "
          "never drives", "`always @(posedge clk)` sampling handshakes"],
         ["Reference model", "Predicts correct behaviour from the spec, at "
          "transaction level", "Queue, associative array, function, or a C "
          "model via DPI"],
         ["Scoreboard", "Compares observed with predicted, counts errors, "
          "reports at the end", "Queue compare + `$error` + counter"],
         ["Checkers", "Protocol rules every cycle", "Immediate or concurrent "
          "assertions (Chapter 23)"]],
        widths=[20, 45, 35], bold_first=True)
    box("key", "The reference model must be independent of the RTL",
        "If the same engineer writes the RTL and the model from the same "
        "mental picture, the two will agree on the same misunderstanding of "
        "the spec. Write the model at a higher level of abstraction (a queue "
        "for a FIFO, a `+` for an adder, a dictionary for a register file), "
        "from the spec rather than from the RTL, and ideally have someone "
        "else write it. A model that copies the RTL's pointer arithmetic "
        "verifies nothing.")

    h2("Clock and reset generation, and driving without races")
    code([
        "`timescale 1ns/1ps",
        "localparam real CLK_PERIOD = 10.0;           // 100 MHz",
        "logic clk = 1'b0, rst_n = 1'b0;",
        "always #(CLK_PERIOD/2) clk = ~clk;",
        "",
        "initial begin",
        "  rst_n = 1'b0;",
        "  repeat (5) @(posedge clk);                 // hold reset for several cycles",
        "  @(negedge clk) rst_n = 1'b1;               // release away from the active edge",
        "end",
    ], "A generic clock/reset block. Releasing reset on the inactive edge "
       "avoids a race with the DUT's flops sampling it.")
    p("The single most common testbench bug is a **race** between the "
      "testbench driving an input and the DUT sampling it on the same clock "
      "edge (Chapter 4). If the TB does `@(posedge clk) wr_en = 1;` with a "
      "blocking assignment, whether the DUT's `always_ff` sees the old or "
      "the new value depends on process ordering - it can differ between "
      "simulators and even between two runs of one simulator after an "
      "unrelated edit. Three race-free conventions are used in practice:")
    bul(["**Drive on the opposite edge** (`@(negedge clk)`), sample on the "
         "active edge. Simple and robust; used in all examples here.",
         "**Drive with non-blocking assignments** at the active edge "
         "(`@(posedge clk) wr_en <= 1;`), so the update lands in the NBA "
         "region after every flop has sampled.",
         "**Clocking blocks** (section 22.10) with explicit input and output "
         "skews - the standard in UVM agents."])

    h2("Tasks for bus transactions")
    p("The driver layer is a set of tasks, one per transaction type, that "
      "hide the protocol from the test. The test then reads like the spec: "
      "`apb_write(addr, data)`, `apb_check(addr, expected)`. Below is a "
      "complete, verified register test for a small APB slave (the APB "
      "protocol itself is covered in Chapter 13).")
    code([
        '`timescale 1ns/1ps',
        'module apb_regs (',
        '  input  logic        pclk, presetn,',
        '  input  logic        psel, penable, pwrite,',
        '  input  logic [3:0]  paddr,',
        '  input  logic [31:0] pwdata,',
        '  output logic [31:0] prdata,',
        '  output logic        pready',
        ');',
        '  logic [31:0] regs [4];',
        "  assign pready = 1'b1;                                  // zero-wait-state slave",
        '  always_ff @(posedge pclk or negedge presetn)',
        "    if (!presetn) foreach (regs[i]) regs[i] <= '0;",
        '    else if (psel && penable && pwrite) regs[paddr[3:2]] <= pwdata;',
        '  assign prdata = regs[paddr[3:2]];',
        'endmodule',
        ], "The DUT: four 32-bit registers on APB, zero wait "
         "states.")
    code([
        '`timescale 1ns/1ps',
        'module tb_apb;',
        '  logic pclk = 0, presetn = 0, psel = 0, penable = 0, pwrite = 0, pready;',
        "  logic [3:0] paddr = '0;",
        "  logic [31:0] pwdata = '0, prdata;",
        '  int errors = 0;',
        '  apb_regs dut (.*);',
        '  always #5 pclk = ~pclk;',
        '',
        '  // One APB write: SETUP phase, then ACCESS phase until PREADY.',
        '  task automatic apb_write(input logic [3:0] addr, input logic [31:0] data);',
        '    @(negedge pclk); psel = 1; penable = 0; pwrite = 1; paddr = addr; pwdata = data;',
        '    @(negedge pclk); penable = 1;',
        '    @(posedge pclk); while (!pready) @(posedge pclk);',
        '    @(negedge pclk); psel = 0; penable = 0;',
        '  endtask',
        '',
        '  task automatic apb_read(input logic [3:0] addr, output logic [31:0] data);',
        '    @(negedge pclk); psel = 1; penable = 0; pwrite = 0; paddr = addr;',
        '    @(negedge pclk); penable = 1;',
        '    @(posedge pclk); while (!pready) @(posedge pclk);',
        '    data = prdata;                                       // sample in ACCESS',
        '    @(negedge pclk); psel = 0; penable = 0;',
        '  endtask',
        '',
        '  // Read-and-compare wrapper: the building block of every register test.',
        '  task automatic apb_check(input logic [3:0] addr, input logic [31:0] exp);',
        '    logic [31:0] got;',
        '    apb_read(addr, got);',
        '    if (got !== exp) begin',
        '      errors++;',
        '      $error("APB rd @%h: got %h exp %h", addr, got, exp);',
        '    end',
        '  endtask',
        '',
        '  initial begin                                          // watchdog',
        '    #10us $fatal(1, "TIMEOUT - DUT hung (pready never asserted?)");',
        '  end',
        '',
        '  initial begin',
        '    $timeformat(-9, 0, " ns", 0);                        // %t prints in ns',
        '    #22 presetn = 1;',
        "    apb_check(4'h0, 32'h0);                              // reset value",
        "    apb_write(4'h4, 32'hCAFE_F00D);",
        "    apb_write(4'hC, 32'h1234_5678);",
        "    apb_check(4'h4, 32'hCAFE_F00D);",
        "    apb_check(4'hC, 32'h1234_5678);",
        "    apb_check(4'h8, 32'h0);                              // untouched register",
        '    $display("[%t] APB register test: %0d errors", $time, errors);',
        '    $finish;',
        '  end',
        'endmodule',
        ], "An APB testbench built from transaction tasks, with "
         "a watchdog and a read-compare wrapper.")
    out(["[200 ns] APB register test: 0 errors",
         "tb_apb.sv:50: $finish called at 200000 (1ps)"])
    p("To prove the testbench can fail - always do this once - we mutate the "
      "DUT so that writes keep only the low 16 bits "
      "(`regs[...] <= pwdata & 32'h0000_FFFF`) and rerun:")
    out(["ERROR: tb_apb.sv:32: APB rd @4: got 0000f00d exp cafef00d",
         "       Time: 140000  Scope: tb_apb.apb_check",
         "ERROR: tb_apb.sv:32: APB rd @c: got 00005678 exp 12345678",
         "       Time: 170000  Scope: tb_apb.apb_check",
         "[200 ns] APB register test: 2 errors",
         "tb_apb.sv:50: $finish called at 200000 (1ps)"],
        "Mutation testing: a testbench that has never been seen to fail "
        "has not been shown to check anything.")
    box("tip", "Details that separate a professional task from a fragile one",
        "Declare tasks `automatic` so that concurrent calls from two threads "
        "get separate copies of their locals. Always wait for the handshake "
        "(`while (!pready) @(posedge pclk);`) rather than assuming zero wait "
        "states - the next DUT revision will add one. Put a **watchdog** in "
        "every test: a hung handshake otherwise burns a regression slot "
        "until the farm's wall-clock limit kills it, with no useful message.")

    h2("Reporting: $display, $error, $fatal and friends")
    tbl(["System task", "Severity", "Effect", "Use for"],
        [["`$display` / `$write`", "-", "Print (with / without newline)",
          "Progress, summaries"],
         ["`$info`", "info", "Print with file:line and scope",
          "Milestones in long tests"],
         ["`$warning`", "warning", "Print; simulation continues",
          "Suspicious but legal behaviour"],
         ["`$error`", "error", "Print; continues; tools count it",
          "A mismatch - keep going to collect more evidence"],
         ["`$fatal(n, ...)`", "fatal", "Print, then end simulation (exit "
          "code n on most tools)", "Unrecoverable: timeout, bad config, "
          "file not found"],
         ["`$finish` / `$stop`", "-", "End simulation / break to the "
          "interactive prompt", "Normal end of test / debugging"]],
        widths=[20, 11, 34, 35], bold_first=True)
    p("Regression scripts decide pass/fail by scanning the log, so make the "
      "verdict machine-readable: print exactly one `TEST PASSED` or `TEST "
      "FAILED` line, and make the script treat any `ERROR`/`FATAL` string, "
      "a missing verdict line, or a non-zero exit code as a failure. A test "
      "that crashes before printing its verdict must never count as a pass.")
    box("warn", "PITFALL: the test that passes because it did nothing",
        "A scoreboard that compares zero transactions reports zero errors. "
        "Always count checks as well as errors, and fail the test if the "
        "count is below what the stimulus should have produced. Likewise, a "
        "queue-based scoreboard must check at the end that the expected "
        "queue is **empty** - leftover entries are outputs the DUT dropped.")

    h2("File I/O: vectors in, logs out")
    tbl(["Task", "Purpose"],
        [["`$readmemh(file, mem)` / `$readmemb`", "Load a memory array from a "
          "hex/binary text file: test vectors, ROM contents, golden results "
          "produced by a Python or C model"],
         ["`fd = $fopen(file, \"w\")`", "Open a file; returns 0 on failure - "
          "check it"],
         ["`$fdisplay(fd, ...)` / `$fwrite`", "Write a formatted line"],
         ["`$fscanf(fd, fmt, ...)` / `$fgets`", "Read formatted data or a "
          "line; returns the number of items matched, and `$feof(fd)` tells "
          "you when to stop"],
         ["`$fclose(fd)`", "Flush and close"],
         ["`$sformatf(fmt, ...)`", "Format into a `string` (for messages)"],
         ["`$value$plusargs(\"SEED=%d\", s)`", "Read `+SEED=42` from the "
          "simulator command line - how regressions pass knobs to tests"]],
        widths=[36, 64], bold_first=True)
    p("A common industrial pattern is to generate vectors and expected "
      "results with a bit-accurate Python or C model, dump both as hex files, "
      "and let the testbench `$readmemh` them. It is the cheapest way to "
      "reuse an algorithm team's golden model; DPI-C (Chapter 24) is the "
      "next step when the model must run in lock-step.")

    h2("Randomization: $urandom and constrained-random classes")
    p("Directed tests check the cases you thought of. **Random** tests find "
      "the ones you did not - the overflow at the same cycle as a read, the "
      "back-pressure during a burst. The simplest source of randomness works "
      "everywhere:")
    code([
        "wr_en = ($urandom_range(99) < 60);     // 60% probability",
        "wdata = $urandom;                      // 32 random bits, truncated",
        "len   = $urandom_range(16, 1);         // uniform in [1:16]",
        "if (!$value$plusargs(\"SEED=%d\", seed)) seed = 1;",
        "void'($urandom(seed));                 // seed the thread's generator",
    ], "Procedural randomization - supported by every simulator, including "
       "Icarus.")
    p("SystemVerilog's real strength is **constrained randomization**: you "
      "declare the legal space with `rand` variables and `constraint` "
      "blocks, and a constraint solver picks values. Icarus Verilog does not "
      "implement constraints (`sorry: Constraint declarations not "
      "supported`), so the following is shown without output; it is "
      "standard IEEE 1800 and runs on VCS, Xcelium, Questa and Riviera.")
    code([
        "class bus_txn;",
        "  typedef enum bit [1:0] {READ, WRITE, IDLE} kind_e;",
        "  rand  kind_e     kind;",
        "  rand  bit [31:0] addr;",
        "  rand  bit [31:0] data;",
        "  rand  bit [3:0]  len;",
        "  randc bit [2:0]  id;          // cyclic: all 8 values before any repeats",
        "",
        "  constraint c_align { addr[1:0] == 2'b00; }",
        "  constraint c_range { addr inside {[32'h4000_0000 : 32'h4000_0FFF]}; }",
        "  constraint c_kind  { kind dist {READ := 45, WRITE := 45, IDLE := 10}; }",
        "  constraint c_len   { (kind == IDLE) -> (len == 0);",
        "                       len <= 8; }",
        "  constraint c_order { solve kind before len; }",
        "",
        "  function void post_randomize();",
        "    if (kind == READ) data = '0;             // don't-care for reads",
        "  endfunction",
        "endclass",
        "",
        "// in the test",
        "bus_txn t;",
        "t = new();",
        "repeat (1000) begin",
        "  if (!t.randomize()) $fatal(1, \"randomize() failed\");",
        "  drive(t);",
        "end",
        "// inline constraints for a directed-random corner case",
        "if (!t.randomize() with { kind == WRITE; addr == 32'h4000_0FFC; })",
        "  $fatal(1, \"inline randomize failed\");",
        "t.c_range.constraint_mode(0);                // switch a constraint off",
        "t.id.rand_mode(0);                           // freeze one field",
    ], "Constrained-random transaction (not runnable on Icarus).")
    tbl(["Construct", "Meaning"],
        [["`rand` / `randc`", "Random each call / random-cyclic (a "
          "permutation before repeating)"],
         ["`inside {[a:b], c}`", "Set membership, including ranges"],
         ["`dist {v := w}` / `{[a:b] :/ w}`", "Weighted distribution: `:=` "
          "gives each value weight w; `:/` splits w across the range"],
         ["`a -> b`", "Implication: if a then b must hold"],
         ["`solve a before b`", "Changes the probability distribution, not "
          "the legal space"],
         ["`randomize() with {...}`", "Add constraints for one call"],
         ["`pre_/post_randomize()`", "Hooks to compute derived fields"],
         ["return value of `randomize()`", "0 if the constraints are "
          "unsatisfiable - **always check it**"]],
        widths=[32, 68], bold_first=True)
    tbl(["", "Directed testing", "Constrained-random testing"],
        [["Written as", "Explicit sequences for each feature",
          "Legal space + a few knobs; seeds do the rest"],
         ["Finds", "Bugs in cases you anticipated", "Bugs in interactions "
          "you did not anticipate"],
         ["Checking", "Can be hard-coded per test", "Needs a reference model "
          "and scoreboard"],
         ["Knowing when done", "Test plan checklist", "Functional coverage "
          "(Chapter 23)"],
         ["Best for", "Bring-up, reset values, specific corners, "
          "regressions of fixed bugs", "Bulk of verification of any "
          "block with a rich input space"]],
        widths=[16, 40, 44], bold_first=True)
    box("intuit", "Coverage-driven verification in one sentence",
        "Randomize within legal constraints, check everything automatically, "
        "measure what was hit with coverage, and write directed or "
        "further-constrained tests only for the holes. The methodology, not "
        "the language, is what makes it work.")

    h2("A complete self-checking testbench: synchronous FIFO")
    p("We now put every layer together for a 4-deep synchronous FIFO with "
      "show-ahead (first-word-fall-through) reads, the kind designed in "
      "Chapter 9. The reference model is a SystemVerilog **queue**; the "
      "monitor and scoreboard are merged in one clocked block that updates "
      "the model with exactly the handshake rules of the spec.")
    code([
        'module sync_fifo #(parameter int W = 8, parameter int DEPTH = 4) (',
        '  input  logic         clk, rst_n,',
        '  input  logic         wr_en, rd_en,',
        '  input  logic [W-1:0] wdata,',
        '  output logic [W-1:0] rdata,',
        '  output logic         full, empty',
        ');',
        '  localparam int AW = $clog2(DEPTH);',
        '  logic [W-1:0]  mem [DEPTH];',
        '  logic [AW:0]   wptr, rptr;             // extra MSB distinguishes full/empty',
        '  assign empty = (wptr == rptr);',
        '  assign full  = (wptr[AW] != rptr[AW]) && (wptr[AW-1:0] == rptr[AW-1:0]);',
        '  assign rdata = mem[rptr[AW-1:0]];      // show-ahead (FWFT) read',
        '  always_ff @(posedge clk or negedge rst_n)',
        '    if (!rst_n) begin',
        "      wptr <= '0; rptr <= '0;",
        '    end else begin',
        '      if (wr_en && !full) begin',
        '        mem[wptr[AW-1:0]] <= wdata;',
        "        wptr <= wptr + 1'b1;",
        '      end',
        "      if (rd_en && !empty) rptr <= rptr + 1'b1;",
        '    end',
        'endmodule',
        ], "DUT: 4-entry FIFO with an extra pointer bit to "
         "distinguish full from empty.")
    code([
        'module tb_fifo;',
        '  localparam int W = 8, DEPTH = 4;',
        '  logic clk = 0, rst_n = 0;',
        '  logic wr_en = 0, rd_en = 0;',
        "  logic [W-1:0] wdata = '0, rdata;",
        '  logic full, empty;',
        '  int errors = 0, checks = 0;',
        '  logic [W-1:0] model_q[$];                   // reference model: a queue',
        '',
        '  sync_fifo #(.W(W), .DEPTH(DEPTH)) dut (.*);',
        '',
        '  always #5 clk = ~clk;                       // 100 MHz clock',
        '',
        '  // ---------------- monitor + scoreboard (samples at the active edge)',
        '  always @(posedge clk) if (rst_n) begin',
        '    if (full  !== (model_q.size() == DEPTH)) begin',
        '      errors++; $error("full=%b but model holds %0d", full, model_q.size());',
        '    end',
        '    if (empty !== (model_q.size() == 0)) begin',
        '      errors++; $error("empty=%b but model holds %0d", empty, model_q.size());',
        '    end',
        '    if (rd_en && !empty) begin',
        '      checks++;',
        '      if (rdata !== model_q[0]) begin',
        '        errors++; $error("rdata=%h expected %h", rdata, model_q[0]);',
        '      end',
        "      void'(model_q.pop_front());",
        '    end',
        '    if (wr_en && !full) model_q.push_back(wdata);',
        '  end',
        '',
        '  // ---------------- driver tasks (drive on the inactive edge)',
        '  task automatic push(input logic [W-1:0] d);',
        '    @(negedge clk); wr_en = 1; wdata = d; rd_en = 0;',
        '    @(negedge clk); wr_en = 0;',
        '  endtask',
        '',
        '  task automatic pop();',
        '    @(negedge clk); rd_en = 1; wr_en = 0;',
        '    @(negedge clk); rd_en = 0;',
        '  endtask',
        '',
        '  initial begin',
        '    repeat (2) @(negedge clk);',
        '    rst_n = 1;',
        '    // ---- directed tests: fill to full, overflow attempt, drain, underflow',
        "    for (int i = 0; i < DEPTH + 1; i++) push(8'hA0 + i);   // 5th push is dropped",
        '    if (!full) $fatal(1, "FIFO not full after %0d pushes", DEPTH);',
        '    repeat (DEPTH + 1) pop();                               // 5th pop is ignored',
        '    $display("[%0t] directed phase done: checks=%0d errors=%0d", $time, checks, errors);',
        '    // ---- constrained-random phase: random mix of push/pop every cycle',
        '    repeat (2000) begin',
        '      @(negedge clk);',
        '      wr_en = ($urandom_range(99) < 60);                    // 60% write',
        '      rd_en = ($urandom_range(99) < 50);                    // 50% read',
        '      wdata = $urandom;',
        '    end',
        '    @(negedge clk); wr_en = 0; rd_en = 0;',
        '    @(negedge clk);',
        '    $display("[%0t] random phase done:   checks=%0d errors=%0d", $time, checks, errors);',
        '    if (errors == 0) $display("TEST PASSED");',
        '    else             $display("TEST FAILED");',
        '    $finish;',
        '  end',
        'endmodule',
        ], "Self-checking FIFO testbench: directed phase "
         "(fill, overflow, drain, underflow) then 2000 constrained-random "
         "cycles.")
    out(["[220] directed phase done: checks=4 errors=0",
         "[20240] random phase done:   checks=931 errors=0",
         "TEST PASSED",
         "tb_fifo.sv:63: $finish called at 20240 (1s)"])
    p("Note what the scoreboard checks: not only the data, but the `full` "
      "and `empty` flags **every cycle** against the model's occupancy, and "
      "it updates the model only when the DUT is allowed to accept the "
      "operation (`wr_en && !full`). The random mix of 60% writes and 50% "
      "reads keeps the FIFO oscillating around full, where the bugs live. "
      "Now inject the classic bug - dropping the MSB comparison from the "
      "full flag, so that `full` is also true when the FIFO is empty:")
    code(["assign full  = (wptr[AW-1:0] == rptr[AW-1:0]);   // BUG: MSB check removed"])
    out(["ERROR: tb_fifo.sv:17: full=1 but model holds 0",
         "       Time: 25  Scope: tb_fifo",
         "ERROR: tb_fifo.sv:17: full=1 but model holds 0",
         "       Time: 35  Scope: tb_fifo",
         "ERROR: tb_fifo.sv:17: full=1 but model holds 0",
         "       Time: 45  Scope: tb_fifo"],
        "First lines of the failing run: the bug is caught on the first "
        "clock after reset.")

    h2("Class-based transactions, a reference function and file vectors")
    p("The second example checks a combinational ALU. The transaction is a "
      "class (Icarus supports classes, but not `randomize()`, so a "
      "`rand_fill()` method stands in for it and biases 10% of `b` values "
      "to the `8'hFF` corner). Directed vectors come from a hex file, results "
      "go to a log file, and the reference model is a function written from "
      "the spec.")
    code([
        'module alu (',
        '  input  logic [1:0] op,          // 0:ADD 1:SUB 2:AND 3:XOR',
        '  input  logic [7:0] a, b,',
        '  output logic [7:0] y,',
        '  output logic       c            // carry-out / borrow-out',
        ');',
        '  always_comb begin',
        "    c = 1'b0;",
        '    unique case (op)',
        "      2'd0: {c, y} = a + b;",
        "      2'd1: {c, y} = {1'b0, a} - {1'b0, b};",
        "      2'd2: y = a & b;",
        "      2'd3: y = a ^ b;",
        '    endcase',
        '  end',
        'endmodule',
        ], "DUT: 8-bit ALU with carry/borrow.")
    code([
        '0_ff_01',
        '1_00_01',
        '2_f0_3c',
        '3_aa_55',
        ], "vectors.hex - {op, a, b}; underscores are legal "
         "in $readmemh files.")
    code([
        'class alu_txn;',
        '  bit [1:0] op;',
        '  bit [7:0] a, b;',
        '  function void rand_fill();              // stand-in for randomize()',
        '    op = $urandom_range(3);',
        '    a  = $urandom;',
        "    b  = ($urandom_range(9) == 0) ? 8'hFF : $urandom;   // bias 10% to a corner",
        '  endfunction',
        '  function string sprint();',
        '    return $sformatf("op=%0d a=%h b=%h", op, a, b);',
        '  endfunction',
        'endclass',
        '',
        'module tb_alu;',
        '  logic [1:0] op; logic [7:0] a, b, y; logic c;',
        '  logic [17:0] vec [4];                   // {op[1:0], a[7:0], b[7:0]}',
        '  int fd, errors = 0, n = 0;',
        '  alu dut (.*);',
        '',
        '  // Reference model: written independently of the RTL, from the spec.',
        '  function automatic logic [8:0] alu_ref(logic [1:0] o, logic [7:0] x, z);',
        '    case (o)',
        "      2'd0:    return {1'b0, x} + {1'b0, z};",
        "      2'd1:    return {1'b0, x} - {1'b0, z};",
        "      2'd2:    return {1'b0, x & z};",
        "      default: return {1'b0, x ^ z};",
        '    endcase',
        '  endfunction',
        '',
        '  task automatic check(alu_txn t);',
        '    logic [8:0] exp;',
        '    op = t.op; a = t.a; b = t.b;',
        '    #1;                                   // let combinational logic settle',
        '    exp = alu_ref(t.op, t.a, t.b);',
        '    n++;',
        '    if ({c, y} !== exp) begin',
        '      errors++;',
        '      $error("%s: got %h exp %h", t.sprint(), {c, y}, exp);',
        '    end',
        '    $fdisplay(fd, "%s -> c=%b y=%h", t.sprint(), c, y);',
        '  endtask',
        '',
        '  initial begin : main',
        '    alu_txn t;',
        '    t = new();',
        '    fd = $fopen("alu_log.txt", "w");',
        '    if (fd == 0) $fatal(1, "cannot open log file");',
        '    $readmemh("vectors.hex", vec);        // directed vectors from a file',
        '    foreach (vec[i]) begin',
        '      t.op = vec[i][17:16];  t.a = vec[i][15:8];  t.b = vec[i][7:0];',
        '      check(t);',
        '    end',
        '    repeat (1000) begin                   // random vectors',
        '      t.rand_fill();',
        '      check(t);',
        '    end',
        '    $fclose(fd);',
        '    $display("ALU: %0d vectors, %0d errors -> %s", n, errors, errors ? "FAIL" : "PASS");',
        '    $finish;',
        '  end',
        'endmodule',
        ], "ALU testbench: class transaction, reference "
         "function, $readmemh, $fopen/$fdisplay.")
    out(["ALU: 1004 vectors, 0 errors -> PASS",
         "tb_alu.sv:59: $finish called at 1004 (1s)"])
    out(["op=0 a=ff b=01 -> c=1 y=00",
         "op=1 a=00 b=01 -> c=1 y=ff",
         "op=2 a=f0 b=3c -> c=0 y=30",
         "op=3 a=aa b=55 -> c=0 y=ff"],
        "First lines of alu_log.txt: the four directed vectors, including "
        "carry-out and borrow corners.")
    p("Swapping the operands of the subtraction in the RTL "
      "(`{1'b0, b} - {1'b0, a}`) is caught immediately:")
    out(["ERROR: tb_alu.sv:38: op=1 a=00 b=01: got 001 exp 1ff",
         "       Time: 2  Scope: tb_alu.check",
         "ERROR: tb_alu.sv:38: op=1 a=c5 b=e5: got 020 exp 1e0",
         "       Time: 9  Scope: tb_alu.check"])
    box("warn", "PITFALL: == versus === in checkers",
        "`if (y != exp)` is **false** when `y` is X, because `!=` returns X "
        "and an `if` treats X as false - an X output silently passes. Always "
        "compare with the case-equality operators `===` / `!==`, which "
        "treat X and Z as values. Every check in this chapter uses `!==`.")
    box("note", "Icarus-specific notes",
        "Icarus 12 aborted on a `case` statement over a class property inside "
        "a class method, and did not assign a concatenation of class "
        "properties used as an lvalue; both are simulator limitations, which "
        "is why the reference model is a module-level function and the "
        "vector fields are assigned by slices. Commercial simulators accept "
        "either form.")

    h2("Interfaces, modports, clocking blocks and virtual interfaces")
    p("An `interface` bundles the signals of one protocol, so that a "
      "valid/ready channel is one port instead of three, and it can carry "
      "the protocol's tasks with it. Icarus supports interfaces with tasks "
      "accessed hierarchically, which is enough for this verified example:")
    code([
        'interface vr_if #(parameter int W = 8) (input logic clk);',
        '  logic         valid, ready;',
        '  logic [W-1:0] data;',
        '  // Driver task lives with the signals it wiggles.',
        '  task automatic send(input logic [W-1:0] d);',
        '    @(negedge clk); valid = 1; data = d;',
        '    @(posedge clk); while (!ready) @(posedge clk);   // wait for the handshake',
        '    @(negedge clk); valid = 0;',
        '  endtask',
        'endinterface',
        '',
        'module acc_sink (input  logic        clk, rst_n, valid,',
        '                 input  logic [7:0]  data,',
        '                 output logic [15:0] sum);',
        '  always_ff @(posedge clk or negedge rst_n)',
        "    if (!rst_n)     sum <= '0;",
        '    else if (valid) sum <= sum + data;   // ready is driven by the TB below',
        'endmodule',
        '',
        'module tb_if;',
        '  logic clk = 0, rst_n = 0;',
        '  logic [15:0] sum;',
        '  int exp = 0;',
        '  always #5 clk = ~clk;',
        '  vr_if #(.W(8)) bus (.clk(clk));',
        '  acc_sink u_sink (.clk, .rst_n, .valid(bus.valid && bus.ready),',
        '                   .data(bus.data), .sum);',
        '',
        '  // Backpressure: ready on a pseudo-random ~70% of cycles.',
        '  always @(negedge clk) bus.ready <= ($urandom_range(9) < 7);',
        '',
        '  initial begin',
        "    bus.valid = 0; bus.data = '0;",
        '    repeat (2) @(negedge clk); rst_n = 1;',
        "    for (int i = 1; i <= 20; i++) begin bus.send(8'(i)); exp += i; end",
        '    @(negedge clk);',
        '    if (sum !== exp) $fatal(1, "sum=%0d expected %0d", sum, exp);',
        '    $display("[%0t] sum=%0d matches model - PASS", $time, sum);',
        '    $finish;',
        '  end',
        'endmodule',
        ], "An interface that carries its own driver task, "
         "exercised under random back-pressure.")
    out(["[480] sum=210 matches model - PASS",
         "tb_vr_if.sv:39: $finish called at 480 (1s)"])
    p("The full SystemVerilog feature set goes further. **Modports** give "
      "each side of the interface a direction view; **clocking blocks** "
      "define when the testbench samples inputs and drives outputs relative "
      "to the clock, which removes races by construction; and a **virtual "
      "interface** is a handle to an interface instance that a class can "
      "hold, which is how class-based drivers and monitors (and all of UVM) "
      "reach the pins. Icarus does not support clocking blocks, interface "
      "ports or virtual interfaces, so this is shown without output:")
    code([
        "interface vr_if #(parameter int W = 8) (input logic clk, input logic rst_n);",
        "  logic         valid, ready;",
        "  logic [W-1:0] data;",
        "  clocking drv_cb @(posedge clk);",
        "    default input #1step output #1;   // sample just before, drive just after",
        "    output valid, data;",
        "    input  ready;",
        "  endclocking",
        "  clocking mon_cb @(posedge clk);",
        "    default input #1step;",
        "    input valid, ready, data;",
        "  endclocking",
        "  modport dut_snk (input valid, data, output ready);",
        "  modport tb_drv  (clocking drv_cb, input rst_n);",
        "  modport tb_mon  (clocking mon_cb, input rst_n);",
        "endinterface",
        "",
        "class vr_driver #(int W = 8);",
        "  virtual vr_if #(W) vif;                     // handle to the real interface",
        "  function new(virtual vr_if #(W) vif);",
        "    this.vif = vif;",
        "  endfunction",
        "  task send(bit [W-1:0] d);",
        "    vif.drv_cb.valid <= 1'b1;                  // clocking drives use <=",
        "    vif.drv_cb.data  <= d;",
        "    do @(vif.drv_cb); while (!vif.drv_cb.ready);   // handshake on this edge",
        "    vif.drv_cb.valid <= 1'b0;",
        "  endtask",
        "endclass",
        "",
        "module tb_top;",
        "  logic clk = 0, rst_n = 0;",
        "  always #5 clk = ~clk;",
        "  vr_if #(8) bus (.clk(clk), .rst_n(rst_n));",
        "  my_sink dut (.s(bus.dut_snk));              // DUT sees only its modport",
        "  vr_driver #(8) drv;",
        "  initial begin",
        "    drv = new(bus);                           // actual -> virtual interface",
        "    repeat (2) @(negedge clk); rst_n = 1;",
        "    repeat (10) drv.send($urandom);",
        "  end",
        "endmodule",
    ], "Clocking blocks and a virtual-interface driver (IEEE 1800; runs on "
       "commercial simulators, not on Icarus).")
    diagram([
        "          clk  ____/~~~~~~~~\\________/~~~~~~~~\\____",
        "                   ^ edge                ^ edge",
        "   input  #1step:  | sampled in the Preponed region (value just before edge)",
        "   output #1    :  |--1ns--> driven here, well after every flop sampled",
        "",
        "   => TB reads what the DUT flops saw; TB drives never race DUT sampling",
    ], "Clocking-block skews: #1step input sampling and a small output skew.")
    p("**Program blocks** (`program ... endprogram`) are a related "
      "SystemVerilog construct whose `initial` blocks execute in the "
      "Reactive region, after the design has settled, so testbench code "
      "cannot race the design even without clocking blocks. They were "
      "popular in VMM-era testbenches; UVM does not use them, and most teams "
      "today rely on clocking blocks and non-blocking drives instead. Know "
      "what they are for interviews; you will rarely write one.")
    box("expert", "Interview angle: why do classes need virtual interfaces?",
        "Classes are dynamic objects created at run time; interfaces and "
        "modules are static hierarchy elaborated before time zero. A class "
        "cannot contain an interface instance, so it holds a **reference** "
        "to one - a virtual interface - assigned at run time (in UVM, "
        "through `uvm_config_db`). That one level of indirection is what "
        "lets the same driver class be reused on any number of interface "
        "instances.")

    h2("Summary")
    bul(["A self-checking TB decides pass/fail itself by comparing DUT "
         "behaviour with an independent reference model; waveforms are for "
         "debug only.",
         "Layers: stimulus, driver, DUT, monitor, reference model, "
         "scoreboard - the same picture UVM implements with classes.",
         "Avoid TB/DUT races: drive on the inactive edge, with non-blocking "
         "assignments, or through clocking blocks.",
         "Hide protocols in `automatic` tasks; add a watchdog to every test; "
         "count checks as well as errors; use `!==` in comparisons.",
         "Mix directed tests (corners, bring-up) with constrained-random "
         "stimulus; always check the return value of `randomize()`.",
         "Prove every testbench can fail by mutating the DUT at least once.",
         "Interfaces bundle protocols; virtual interfaces connect class-based "
         "testbenches to them."])
    h2("Exercises")
    bul(["Extend the FIFO testbench with a final check that the model queue "
         "is empty after draining, and a minimum-checks threshold that fails "
         "a test which compared fewer than 500 reads.",
         "Add a `+SEED=` plusarg to `tb_fifo` and run 20 seeds from a shell "
         "loop; grep the logs for the verdict line.",
         "Write `apb_write`/`apb_read` for an APB slave with random wait "
         "states (PREADY low for 0-3 cycles) and show that the tasks still "
         "pass while a version that assumes zero wait states fails.",
         "Inject three different bugs into the ALU (wrong carry for ADD, XOR "
         "implemented as OR, `unique case` missing an item) and confirm the "
         "testbench catches each. Which one needs the biased corner values?",
         "Rewrite `bus_txn` constraints so that 4 KB boundary crossings are "
         "impossible for a burst of `len` words starting at `addr`.",
         "Explain, with a timing sketch, what goes wrong if the FIFO "
         "testbench drives `wr_en` with a blocking assignment at "
         "`@(posedge clk)`."], ordered=True)


# =============================================================================
#             Chapter 23 - SystemVerilog assertions and coverage
# =============================================================================
def ch23():
    chapter("SystemVerilog Assertions and Functional Coverage")
    p("A scoreboard checks the **end-to-end** result of a transaction: the "
      "right data came out. It says nothing about **how** the data got "
      "there - whether valid was withdrawn and re-asserted, whether a "
      "one-hot state vector briefly had two bits set, whether a grant was "
      "issued without a request. Assertions check those internal and "
      "protocol-level rules every cycle, at the exact place and time they "
      "are violated. Functional coverage is their counterpart: it measures "
      "which of the interesting scenarios the tests actually exercised. "
      "Together they turn 'we ran a lot of tests' into 'we can show what "
      "was checked and what was exercised'.")

    h2("Why assertions pay for themselves")
    tbl(["Benefit", "Explanation"],
        [["**Observability**", "A bug inside a block may take thousands of "
          "cycles to reach an output, or be masked entirely. An assertion "
          "fires at the cycle and the signal where the rule broke"],
         ["**Localization**", "The message names the violated property, "
          "file and line - debug starts at the root cause, not at a "
          "corrupted packet 10 microseconds later"],
         ["**Executable specification**", "`valid && !ready |=> valid` is "
          "unambiguous in a way that a paragraph of spec is not"],
         ["**Reuse across engines**", "The same properties run in "
          "simulation, in formal property verification (Chapter 25) and, "
          "synthesized, in emulation and FPGA prototypes (Chapter 26)"],
         ["**Integration safety**", "Assertions bound to an IP's interface "
          "catch misuse by the SoC team who integrates it"]],
        widths=[25, 75], bold_first=True)
    box("key", "Who writes which assertions",
        "Designers write **white-box** assertions about their own "
        "implementation (FSM encodings, pointer invariants, no FIFO overflow "
        "inside the block) as they write the RTL - they know the assumptions "
        "and it costs minutes. Verification engineers write **black-box** "
        "interface and end-to-end properties from the spec. A good rule of "
        "thumb for designers: every time you think 'this can never happen', "
        "write an assertion that says so.")

    h2("Immediate versus concurrent assertions")
    tbl(["", "Immediate", "Concurrent"],
        [["Syntax", "`assert (expr) else ...;` inside procedural code",
          "`assert property (@(posedge clk) ...)` as a module item"],
         ["Evaluated", "When the statement executes, on current values",
          "At each clock tick, on values **sampled** in the Preponed region "
          "(just before the edge)"],
         ["Spans time?", "No - one instant", "Yes - sequences over many "
          "cycles"],
         ["Glitch sensitivity", "Plain immediate: fires on transient zero-"
          "time glitches; **deferred** `assert #0` / `assert final` report "
          "only the settled value", "None - sampled once per clock"],
         ["Formal tools", "Supported (mostly as combinational invariants)",
          "Native form"],
         ["Icarus Verilog 12", "Plain immediate supported; deferred not",
          "Not supported"]],
        widths=[18, 41, 41], bold_first=True)
    p("Because immediate assertions run on every simulator, they are the "
      "portable way to put checks into RTL and testbenches. With a few "
      "registered copies of past values they can even express simple "
      "multi-cycle rules, as the next verified example shows.")

    h2("Immediate assertions in practice: a protocol checker")
    p("The checker below enforces the two AXI-style valid/ready rules from "
      "Chapter 10: once `valid` is asserted it must stay asserted until "
      "`ready`, and the payload must not change while stalled. It also "
      "checks that the control signals are never X after reset. It is a "
      "separate module, so it can be instantiated next to any valid/ready "
      "port - or attached with `bind` (section 23.9).")
    code([
        '// Protocol checker for a valid/ready channel, written with immediate',
        '// assertions so that it runs on any simulator (including Icarus).',
        'module vr_checker #(parameter int W = 8) (',
        '  input logic clk, rst_n, valid, ready,',
        '  input logic [W-1:0] data',
        ');',
        '  logic         pend;          // "valid && !ready" seen last cycle',
        '  logic [W-1:0] data_q;',
        '  always_ff @(posedge clk or negedge rst_n)',
        "    if (!rst_n) pend <= 1'b0;",
        '    else begin',
        '      pend   <= valid && !ready;',
        '      data_q <= data;',
        '    end',
        '',
        '  always @(posedge clk) if (rst_n) begin',
        '    // No X/Z on control signals out of reset (XOR-reduce is X if any bit is)',
        "    assert ((^{valid, ready}) !== 1'bx)",
        '      else $error("X on valid/ready");',
        '    // Once offered, a transfer must stay offered with stable data (AXI rule)',
        '    if (pend) begin',
        '      assert (valid)',
        '        else $error("valid dropped before ready (data %h lost)", data_q);',
        '      assert (!valid || data == data_q)',
        '        else $error("data changed %h -> %h while stalled", data_q, data);',
        '    end',
        '  end',
        'endmodule',
        ], "A portable valid/ready protocol checker using "
         "immediate assertions and registered history.")
    code([
        'module tb_chk;',
        '  logic clk = 0, rst_n = 0, valid = 0, ready = 0;',
        "  logic [7:0] data = '0;",
        '  always #5 clk = ~clk;',
        '  vr_checker #(.W(8)) u_chk (.*);',
        '',
        '  initial begin',
        '    repeat (2) @(negedge clk); rst_n = 1;',
        "    // Legal: offer 8'h11, stall two cycles, then accept",
        "    @(negedge clk); valid = 1; data = 8'h11; ready = 0;",
        '    repeat (2) @(negedge clk);',
        '    ready = 1;',
        '    @(negedge clk); valid = 0; ready = 0;',
        '    // Illegal #1: change data while stalled (t=85 edge)',
        "    @(negedge clk); valid = 1; data = 8'h22;",
        "    @(negedge clk); data = 8'h23;",
        '    // Illegal #2: withdraw valid while stalled (t=95 edge)',
        '    @(negedge clk); valid = 0;',
        '    @(negedge clk);',
        '    $finish;',
        '  end',
        'endmodule',
        ], "A directed test: one legal stalled transfer, then "
         "two deliberate violations.")
    out(["ERROR: vr_checker.sv:25: data changed 22 -> 23 while stalled",
         "       Time: 85  Scope: tb_chk.u_chk",
         "ERROR: vr_checker.sv:23: valid dropped before ready (data 23 lost)",
         "       Time: 95  Scope: tb_chk.u_chk",
         "tb_chk.sv:20: $finish called at 100 (1s)"],
        "The legal stall passes silently; each violation is reported at the "
        "clock edge where it becomes observable.")
    box("warn", "PITFALL: X-checks on concatenations",
        "The natural form `assert (!$isunknown({valid, ready}))` returned a "
        "wrong result for a concatenation of nets in Icarus 12 and fired on "
        "every clock. The portable Verilog-2001 idiom used above - "
        "XOR-reduce and compare with `1'bx` - works everywhere, because an "
        "XOR reduction is X if and only if some input bit is X or Z. On "
        "commercial simulators `$isunknown` is the idiomatic choice. Either "
        "way: test your checkers with a known-good stimulus before trusting "
        "a failure.")
    p("The same check as a concurrent assertion is one line per rule, and "
      "the sampling semantics take care of the history registers and of "
      "the reset: this is exactly why SVA exists.")
    code([
        "a_hold:   assert property (@(posedge clk) disable iff (!rst_n)",
        "                           valid && !ready |=> valid);",
        "a_stable: assert property (@(posedge clk) disable iff (!rst_n)",
        "                           valid && !ready |=> $stable(data));",
    ], "The concurrent equivalents (not runnable on Icarus).")

    h2("Anatomy of a concurrent assertion")
    code([
        "//  label      directive          clock            reset",
        "a_req_gnt: assert property (@(posedge clk) disable iff (!rst_n)",
        "             $rose(req) |-> ##[1:4] gnt)          // antecedent |-> consequent",
        "           else $error(\"gnt did not follow req within 4 cycles\");",
        "",
        "// The same, with named sequence and property for reuse:",
        "sequence s_req;  $rose(req);  endsequence",
        "property p_handshake(int max);",
        "  @(posedge clk) disable iff (!rst_n) s_req |-> ##[1:max] gnt;",
        "endproperty",
        "a_req_gnt4: assert property (p_handshake(4));",
    ])
    p("Each clock tick **starts a new attempt** of the property. An attempt "
      "whose antecedent does not match succeeds **vacuously** and is "
      "discarded; an attempt whose antecedent matches spawns a thread that "
      "tracks the consequent over the following cycles. Several attempts "
      "can be in flight at once, which is why SVA is far more compact than "
      "the equivalent hand-written FSM checker.")
    diagram([
        "cycle      1    2    3    4    5    6    7    8",
        "req      __/~~~~~~~~~~~~~~\\_______/~~~~~~~~~~~~~",
        "gnt      ____________/~~~~\\______________________   (never for 2nd req)",
        "",
        "attempt @2: $rose(req)=1 -> look for gnt in cycles 3..6 -> gnt@4: PASS",
        "attempt @3: $rose(req)=0 -> vacuous success",
        "attempt @6: $rose(req)=1 -> no gnt in 7..10             -> FAIL at 10",
    ], "Evaluation of `$rose(req) |-> ##[1:4] gnt`: one attempt per clock; "
       "values are sampled just before each edge.")
    box("key", "Sampled values: the source of most SVA confusion",
        "A concurrent assertion sees each signal's value from the **Preponed** "
        "region - the value it had just before the clock edge, i.e. the same "
        "value the design's flops sampled. If a waveform viewer shows `gnt` "
        "rising exactly at edge 4, the assertion sees it at edge 5. When an "
        "assertion 'fires one cycle late', this is almost always why.")

    h2("Sequence operators")
    tbl(["Operator", "Meaning", "Example"],
        [["`##n`", "Exactly n clock ticks later", "`a ##2 b`: b two cycles "
          "after a"],
         ["`##[m:n]`, `##[m:$]`", "Between m and n ticks; `$` = eventually",
          "`req ##[1:4] gnt`"],
         ["`s [*n]`, `[*m:n]`", "Consecutive repetition", "`busy [*3]`: "
          "busy for exactly 3 consecutive cycles"],
         ["`b [->n]`", "Goto repetition: the n-th occurrence of b (not "
          "necessarily consecutive); ends **on** the n-th", "`start ##1 "
          "done [->3]`"],
         ["`b [=n]`", "Non-consecutive repetition; may end after the n-th",
          "`wr [=2] ##1 flush`"],
         ["`s1 and s2`, `s1 or s2`", "Both / either sequence matches",
          "-"],
         ["`s1 intersect s2`", "Both match with the same start and end", "-"],
         ["`b throughout s`", "b holds at every cycle of s",
          "`!rst throughout (req ##[1:$] gnt)`"],
         ["`s1 within s2`", "s1 matches somewhere inside s2", "-"],
         ["`first_match(s)`", "Only the earliest match of s", "Bounds "
          "open-ended ranges in antecedents"]],
        widths=[24, 42, 34], bold_first=True)
    diagram([
        "cycle         1   2   3   4   5   6   7",
        "done          0   1   0   1   0   1   0",
        "done [->3]    |---------------------^         matches at cycle 6",
        "done [=3]     |---------------------^---^--   matches at 6 and 7 (and later,",
        "                                              while done stays 0)",
        "busy [*3]     needs busy=1 in three consecutive cycles",
    ], "Goto versus non-consecutive repetition.")

    h2("Implication: |-> and |=>")
    p("`A |-> B` (**overlapping**): if A matches, B must start in the "
      "**same** cycle in which A ended. `A |=> B` (**non-overlapping**): B "
      "starts in the **next** cycle; it is exactly `A |-> ##1 B`. If A does "
      "not match, the property is vacuously true.")
    diagram([
        "cycle            1      2      3",
        "valid&&!ready    1      .      .",
        "",
        "|->  consequent checked at 1        e.g. 'valid |-> !$isunknown(data)'",
        "|=>  consequent checked at 2        e.g. 'valid && !ready |=> valid'",
    ])
    box("warn", "PITFALL: vacuous success hides dead assertions",
        "An assertion whose antecedent never occurs 'passes' forever. If the "
        "reset polarity in `disable iff` is wrong, or a signal name is bound "
        "to a constant, the assertion checks nothing and nobody notices. "
        "Every important assertion should have a matching `cover property` "
        "on its antecedent, and assertion reports should list attempts, "
        "vacuous and real successes. Formal tools report vacuity directly.")
    box("warn", "PITFALL: implication inside cover",
        "`cover property (a |-> b)` is satisfied vacuously by every cycle in "
        "which `a` is false, so it proves nothing. Cover **sequences**: "
        "`cover property (a ##1 b)`.")

    h2("Sampled-value functions")
    tbl(["Function", "True when (sampled at this tick)", "Note"],
        [["`$rose(x)`", "LSB of x went 0 -> 1 since the previous tick",
          "On a bus uses the **LSB only** - use `$changed` or compare "
          "values for buses"],
         ["`$fell(x)`", "LSB went 1 -> 0", "-"],
         ["`$stable(x)`", "x equals its value at the previous tick",
          "Whole vector"],
         ["`$changed(x)`", "`!$stable(x)`", "SV-2009"],
         ["`$past(x, n)`", "Value of x n ticks ago (default 1)",
          "Before n ticks have elapsed it returns the initial value - guard "
          "with reset"],
         ["`$onehot(x)`, `$onehot0(x)`", "Exactly one / at most one bit set",
          "FSM encodings, grants, mux selects"],
         ["`$isunknown(x)`", "Any bit is X or Z", "X-checks on control"],
         ["`$countones(x)`", "Number of 1 bits", "Credits, occupancy"]],
        widths=[24, 44, 32], bold_first=True)

    h2("assert, assume, cover - and disable iff")
    tbl(["Directive", "In simulation", "In formal verification"],
        [["`assert property`", "Error if the property fails",
          "Goal to prove for all legal inputs"],
         ["`assume property`", "Checked like an assert (flags illegal "
          "stimulus)", "**Constraint** on inputs: only traces that satisfy "
          "it are explored"],
         ["`cover property`", "Counts matches; shows a scenario happened",
          "Tool must find a trace that reaches it (reachability)"],
         ["`restrict property`", "Ignored", "Constraint, but not checked "
          "in simulation"]],
        widths=[20, 40, 40], bold_first=True)
    p("`disable iff (expr)` asynchronously aborts every in-flight attempt "
      "while the expression is true - almost always the reset. A module can "
      "declare `default clocking` and `default disable iff` once, so the "
      "individual assertions stay short, as in the library below. The same "
      "interface properties are **assumptions** when you formally verify the "
      "block that receives the interface and **assertions** when you verify "
      "the block that drives it - which is why good assertion IP is written "
      "with a parameter that switches between the two.")

    h2("Binding assertions without touching the RTL")
    p("`bind` instantiates a checker module inside another module (or one "
      "instance of it) from outside, as if the instantiation were written "
      "in the target's source. The checker's ports can connect to any "
      "signal in the target's scope, including internal ones. Verification "
      "teams use it to add assertions to frozen or third-party RTL, and to "
      "keep checkers out of the files that go to synthesis.")
    code([
        "// In a verification-only file, compiled with the testbench:",
        "bind sync_fifo fifo_sva #(.DEPTH(DEPTH)) u_fifo_sva (",
        "  .clk   (clk),   .rst_n (rst_n),",
        "  .wr_en (wr_en), .rd_en (rd_en),",
        "  .full  (full),  .empty (empty),",
        "  .count (wptr - rptr)              // expression over internal signals",
        ");",
        "// bind to one instance only:",
        "bind tb_top.u_soc.u_dma.u_fifo fifo_sva #(.DEPTH(16)) u_chk (.*);",
    ], "bind: every `sync_fifo` instance gets a `fifo_sva` checker.")

    h2("A library of useful assertions")
    p("The following modules collect properties that appear on almost every "
      "project. They parse cleanly with Verilator 5 (which reports several "
      "operators as unsupported for simulation) and are standard IEEE "
      "1800-2017; run them on a commercial simulator or formal tool.")
    code([
        'module vr_sva #(parameter int W = 8) (',
        '  input logic clk, rst_n, valid, ready,',
        '  input logic [W-1:0] data',
        ');',
        '  default clocking cb @(posedge clk); endclocking',
        '  default disable iff (!rst_n);',
        '',
        '  // 1. Once asserted, valid stays high until ready (no withdrawal)',
        '  a_valid_hold: assert property (valid && !ready |=> valid)',
        '    else $error("valid withdrawn before handshake");',
        '  // 2. Payload stable while stalled',
        '  a_data_stable: assert property (valid && !ready |=> $stable(data));',
        '  // 3. No X on valid after reset',
        '  a_no_x: assert property (!$isunknown(valid));',
        '  // 4. Liveness-style bound: a stalled transfer completes within 16 cycles',
        '  a_no_starve: assert property (valid |-> ##[0:16] ready);',
        '  // 5. Cover: see a back-to-back transfer and a 3-cycle stall',
        '  c_b2b:   cover property (valid && ready ##1 valid && ready);',
        '  c_stall: cover property ((valid && !ready) [*3] ##1 (valid && ready));',
        'endmodule',
        '',
        'module fifo_sva #(parameter int DEPTH = 4) (',
        '  input logic clk, rst_n, wr_en, rd_en, full, empty,',
        '  input logic [$clog2(DEPTH):0] count',
        ');',
        '  default clocking cb @(posedge clk); endclocking',
        '  default disable iff (!rst_n);',
        '  a_no_ovf:  assert property (full  |-> !wr_en);          // env obligation',
        '  a_no_udf:  assert property (empty |-> !rd_en);',
        '  a_excl:    assert property (!(full && empty));',
        '  a_cnt_up:  assert property (wr_en && !rd_en && !full |=> count == $past(count) + 1);',
        '  a_full_ok: assert property (count == DEPTH |-> full);',
        '  c_full:    cover  property (full ##1 !full);',
        'endmodule',
        '',
        'module misc_sva (input logic clk, rst_n, req, gnt, start, done,',
        '                 input logic [3:0] state, input logic [7:0] irq);',
        '  default clocking cb @(posedge clk); endclocking',
        '  default disable iff (!rst_n);',
        '  a_onehot:   assert property ($onehot(state));',
        '  a_req_gnt:  assert property ($rose(req) |-> ##[1:4] gnt);',
        '  a_gnt_req:  assert property (gnt |-> req);',
        '  a_done_3rd: assert property (start |-> ##1 done [->3] ##1 !done);',
        '  a_irq_pls:  assert property ($rose(irq[0]) |=> $fell(irq[0]));',
        '  m_env:      assume property (start |=> !start);',
        'endmodule',
        ], "Reusable valid/ready, FIFO and miscellaneous "
         "properties.")
    tbl(["Property", "Catches"],
        [["`a_valid_hold`, `a_data_stable`", "Sources that drop or change a "
          "transfer under back-pressure - the most common AXI/stream bug"],
         ["`a_no_starve`", "Deadlock or starvation (bounded liveness; "
          "unbounded `##[1:$]` is a true liveness property, better handled "
          "by formal)"],
         ["`a_no_ovf`, `a_no_udf`", "Writes when full / reads when empty - "
          "use as assertions on the **user** of a FIFO whose spec forbids "
          "them (the FIFO of Chapter 22 tolerates them by design)"],
         ["`a_excl`, `a_full_ok`, `a_cnt_up`", "Pointer arithmetic errors "
          "inside the FIFO"],
         ["`a_onehot`", "FSM corruption, glitchy state updates, missing "
          "default in a one-hot FSM"],
         ["`a_req_gnt`, `a_gnt_req`", "Arbiter response bound; grant "
          "without request"],
         ["`a_done_3rd`", "Protocols that count events (bursts, credits)"],
         ["`a_irq_pls`", "Pulse-type signals that must last exactly one "
          "cycle"]],
        widths=[32, 68], bold_first=True)

    h2("Functional coverage: covergroups, coverpoints, bins and crosses")
    p("Code coverage tells you which lines ran. **Functional coverage** "
      "tells you which **features** were exercised, as defined by a human "
      "from the spec and the test plan: every opcode, operands at their "
      "extremes, the FIFO being full while a read and a write arrive "
      "together. A `covergroup` samples variables on an event and counts "
      "hits in **bins**; a `cross` counts combinations.")
    code([
        'module cg_demo (input logic clk, rst_n, valid, ready, input logic [1:0] op,',
        '                input logic [7:0] a, b);',
        '  covergroup alu_cg @(posedge clk iff (rst_n && valid && ready));',
        '    option.per_instance = 1;',
        '    cp_op: coverpoint op {',
        "      bins add = {2'd0};",
        "      bins sub = {2'd1};",
        "      bins log[] = {2'd2, 2'd3};",
        '    }',
        '    cp_a: coverpoint a {',
        "      bins zero   = {8'h00};",
        "      bins max    = {8'hFF};",
        "      bins low    = {[8'h01:8'h7F]};",
        "      bins high   = {[8'h80:8'hFE]};",
        '    }',
        '    cp_b: coverpoint b {',
        '      bins zero = {0};',
        '      bins max  = {255};',
        '      bins other = default;',
        '    }',
        '    x_op_a: cross cp_op, cp_a {',
        '      ignore_bins logic_extremes = binsof(cp_op.log) && binsof(cp_a.low);',
        '    }',
        '  endgroup',
        '  alu_cg cg = new();',
        'endmodule',
        ], "A covergroup for the ALU of Chapter 22 (IEEE 1800; not "
         "supported by Icarus or Verilator 5.020).")
    code([
        "covergroup fifo_cg @(posedge clk iff rst_n);",
        "  cp_occ: coverpoint count {",
        "    bins empty    = {0};",
        "    bins mid[]    = {[1:DEPTH-1]};           // one bin per value",
        "    bins full     = {DEPTH};",
        "    illegal_bins over = {[DEPTH+1:$]};      // error if ever sampled",
        "  }",
        "  cp_ops: coverpoint {wr_en, rd_en} {",
        "    bins idle = {2'b00}; bins rd = {2'b01}; bins wr = {2'b10}; bins both = {2'b11};",
        "  }",
        "  x_occ_ops: cross cp_occ, cp_ops;          // e.g. 'both' while full",
        "  cp_seq: coverpoint count {                // transition bins",
        "    bins fill_up   = (DEPTH-1 => DEPTH);",
        "    bins drain     = (DEPTH => DEPTH-1);",
        "    bins blip      = (0 => 1 => 0);",
        "    bins stay_full = (DEPTH [*3]);          // full for 3 samples",
        "  }",
        "endgroup",
        "fifo_cg cg = new();          // instantiate; sample() can also be called by hand",
    ], "FIFO coverage with illegal bins, a cross and transition bins.")
    tbl(["Bin kind", "Syntax", "Purpose"],
        [["Automatic", "`coverpoint x;`", "One bin per value (up to "
          "`auto_bin_max`, default 64 buckets)"],
         ["Explicit / range", "`bins lo = {[0:15]};`", "One bin for a set"],
         ["Array", "`bins v[] = {[0:7]};`", "One bin per value in the set"],
         ["Default", "`bins other = default;`", "Catch-all, excluded from "
          "the coverage score"],
         ["Transition", "`bins t = (1 => 2 => 3);`", "Value sequences "
          "across samples"],
         ["ignore_bins", "`ignore_bins x = {...};`", "Excluded - "
          "unreachable or irrelevant"],
         ["illegal_bins", "`illegal_bins x = {...};`", "Run-time error if "
          "hit - a cheap checker"],
         ["Cross", "`cross a, b;`", "Cartesian product; trim with "
          "`binsof(...) intersect {...}` and ignore/illegal bins"]],
        widths=[18, 34, 48], bold_first=True)
    box("tip", "Crosses explode - design them",
        "A cross of three 16-bin coverpoints has 4096 bins, most of them "
        "meaningless. Cross only the dimensions whose **interaction** matters "
        "in the spec (opcode x operand corner, occupancy x operation), and "
        "remove impossible combinations with `ignore_bins` so the report "
        "shows real holes instead of noise.")
    p("`cover property` complements covergroups for **temporal** scenarios "
      "(a 3-cycle stall followed by a transfer, back-to-back bursts); "
      "covergroups are better for **value** spaces and crosses.")

    h2("Coverage closure")
    bul(["**Test plan first.** List features from the spec; for each, "
         "decide how it is checked (scoreboard, assertion) and how it is "
         "measured (coverpoint, cover property). This 'vplan' is reviewed "
         "with designers and architects.",
         "**Run constrained-random regressions** with many seeds; merge the "
         "coverage databases of all runs.",
         "**Analyse holes.** For each unhit bin decide: the stimulus cannot "
         "reach it (tighten or add constraints, write a directed test), it is "
         "unreachable by design (exclude with a documented reason), or the "
         "coverage model is wrong (fix the model).",
         "**Iterate** until the agreed goals are met - typically 100% "
         "functional coverage with reviewed exclusions, and high code "
         "coverage with every unhit line explained.",
         "**Rank tests** by unique coverage contribution to build a fast "
         "'smoke' regression and to drop redundant tests."], ordered=True)
    box("key", "Coverage measures stimulus, not correctness",
        "A bin is hit when the scenario occurred, whether or not anything "
        "checked the result. 100% coverage with a scoreboard that compares "
        "nothing is 0% verification. Coverage is only meaningful together "
        "with checkers - and the checkers must be proven to fire (mutation "
        "testing, Chapter 22).")

    h2("Code coverage types")
    tbl(["Metric", "Measures", "Blind spot"],
        [["**Line / statement**", "Each executable statement ran",
          "Says nothing about values or combinations"],
         ["**Branch**", "Each if/else arm and case item was taken",
          "Missing branches (the unwritten `else`) cannot be measured"],
         ["**Condition / expression**", "Each sub-condition independently "
          "flipped the outcome (FEC/MC-DC-like)", "Expensive; noisy on wide "
          "expressions"],
         ["**Toggle**", "Every bit went 0->1 and 1->0", "A toggling bus "
          "can still carry wrong values; key for connectivity at SoC level"],
         ["**FSM**", "Every state and every transition visited",
          "Tools extract FSMs heuristically - check the extraction"],
         ["**Assertion**", "Each assertion attempted, succeeded non-"
          "vacuously, failed", "Only as good as the assertions"]],
        widths=[22, 42, 36], bold_first=True)
    box("expert", "Interview angle: code versus functional coverage",
        "Code coverage is automatic and objective but only tells you what "
        "the **implementation** did; it cannot detect a missing feature, "
        "because missing code has no lines. Functional coverage is written "
        "by hand from the **spec**, so it can reveal that a feature was never "
        "exercised - or never implemented - but it is only as good as the "
        "person who wrote it. Sign-off needs both: high code coverage with "
        "reviewed exclusions and 100% of the agreed functional coverage.")

    h2("Summary")
    bul(["Assertions check rules every cycle where they are violated; "
         "coverage measures which scenarios were exercised.",
         "Immediate assertions run anywhere (including Icarus); concurrent "
         "assertions sample values before the clock edge and express "
         "multi-cycle behaviour compactly.",
         "Know the operators: `##n`, `##[m:n]`, `[*n]`, `[->n]`, `[=n]`, "
         "`throughout`, and the implications `|->` (same cycle) and `|=>` "
         "(next cycle).",
         "`$rose/$fell` use only the LSB; `$past` needs a reset guard; "
         "`disable iff` aborts attempts during reset.",
         "assert/assume/cover mean different things to simulation and formal; "
         "watch for vacuous passes and never cover an implication.",
         "`bind` attaches checkers without editing RTL.",
         "Close coverage from a reviewed test plan; coverage without "
         "checking is meaningless."])
    h2("Exercises")
    bul(["Write concurrent assertions for APB (Chapter 13): PENABLE only in "
         "the cycle after PSEL rises, PADDR/PWRITE/PWDATA stable from SETUP "
         "to the end of ACCESS, and PSEL held until PREADY.",
         "Extend `vr_checker` with an immediate-assertion check that `data` "
         "is not X whenever `valid` is high. Verify it with Icarus using a "
         "stimulus that drives `8'hxx` with valid.",
         "For `$rose(req) |-> ##[1:4] gnt`, draw a waveform where two "
         "attempts are in flight at the same time and state when each "
         "passes or fails.",
         "Design a covergroup for a round-robin arbiter with 4 requesters: "
         "which crosses are meaningful, and which bins should be illegal?",
         "Explain why `assert property (@(posedge clk) a |-> b)` passes in a "
         "simulation where `a` is stuck at 0, and add the cover property that "
         "would expose it."], ordered=True)


# =============================================================================
#                        Chapter 24 - UVM methodology
# =============================================================================
def ch24():
    chapter("UVM Methodology")
    p("The testbenches of Chapter 22 work, but they do not scale. When ten "
      "engineers verify a 50-block SoC, each block's testbench must be "
      "reusable at subsystem and chip level, agents for standard protocols "
      "must be shared across projects, and tests must be selectable from the "
      "command line without recompiling. The **Universal Verification "
      "Methodology** (UVM, standardized as IEEE 1800.2) is the industry's "
      "answer: a SystemVerilog class library plus a set of conventions for "
      "building layered, configurable, reusable testbenches. Nearly every "
      "ASIC verification job description asks for it.")
    p("UVM does not change **what** a testbench does - it is still stimulus, "
      "driver, monitor, reference model and scoreboard. It standardizes "
      "**how** those pieces are built, connected, configured and run. If "
      "Chapter 22 made sense, UVM is mostly vocabulary. Icarus Verilog "
      "cannot run UVM, so the code in this chapter is shown without output; "
      "it is written against the IEEE 1800.2 / UVM 1.2 API and runs on "
      "Questa, VCS, Xcelium and Riviera-PRO.")

    h2("Why UVM")
    tbl(["Problem in ad-hoc testbenches", "UVM mechanism"],
        [["Each block's TB is monolithic and cannot be reused at SoC level",
          "**Agents** (driver + monitor + sequencer per interface) and "
          "**environments** that nest"],
         ["Changing stimulus means editing and recompiling the TB",
          "**Sequences** run on sequencers; tests chosen with "
          "`+UVM_TESTNAME=`"],
         ["Swapping a component (error-injecting driver, extended "
          "transaction) needs code edits", "**Factory** overrides by type "
          "or instance"],
         ["Passing parameters and interface handles through levels of "
          "constructors", "**uvm_config_db** - hierarchical configuration "
          "database"],
         ["Deciding when the test is finished", "**Objections** - the run "
          "phase ends when nobody objects"],
         ["Ordering build, connect and run across hundreds of components",
          "**Phases** executed in lock-step by the UVM kernel"],
         ["Inconsistent messages and verbosity", "**Report server**: "
          "`uvm_info/warning/error/fatal` with IDs and verbosity control"],
         ["Register tests rewritten for every block", "**RAL** register "
          "model with built-in sequences"]],
        widths=[50, 50])

    h2("The class hierarchy")
    diagram([
        "uvm_void",
        " +-- uvm_object                      (data: copy/compare/print/pack, factory)",
        "      +-- uvm_transaction",
        "      |    +-- uvm_sequence_item      <- your transactions",
        "      |         +-- uvm_sequence_base",
        "      |              +-- uvm_sequence #(REQ,RSP)   <- your sequences",
        "      +-- uvm_reg, uvm_reg_block, uvm_reg_field ...  (RAL)",
        "      +-- uvm_report_object",
        "           +-- uvm_component          (hierarchy, phases, config)",
        "                +-- uvm_driver #(REQ)      uvm_monitor     uvm_sequencer #(REQ)",
        "                +-- uvm_agent              uvm_scoreboard  uvm_env",
        "                +-- uvm_test",
    ], "Objects are transient data; components form the static testbench "
       "tree built during the build phase.")
    tbl(["", "uvm_object", "uvm_component"],
        [["Lifetime", "Created and discarded freely during the run",
          "Created once in build_phase, lives for the whole simulation"],
         ["Hierarchy", "None (no parent)", "Has a parent and a full "
          "hierarchical name, e.g. `uvm_test_top.env.in_agt.drv`"],
         ["Phases", "No", "Yes"],
         ["Constructor", "`new(string name = \"...\")`",
          "`new(string name, uvm_component parent)`"],
         ["Registration macro", "`uvm_object_utils(T)`",
          "`uvm_component_utils(T)`"],
         ["Examples", "Sequence items, sequences, configuration objects",
          "Drivers, monitors, agents, envs, tests, scoreboards"]],
        widths=[18, 41, 41], bold_first=True)

    h2("Phases")
    tbl(["Phase", "Kind", "Order", "Typical work"],
        [["`build_phase`", "function", "top-down", "Create children with "
          "the factory; read config_db"],
         ["`connect_phase`", "function", "bottom-up", "Connect TLM ports "
          "(driver-sequencer, monitor-scoreboard)"],
         ["`end_of_elaboration_phase`", "function", "bottom-up", "Print "
          "topology, final sanity checks"],
         ["`start_of_simulation_phase`", "function", "bottom-up", "Print "
          "configuration, open files"],
         ["`run_phase`", "**task**", "parallel", "All time-consuming "
          "activity; runs in parallel with the 12 run-time sub-phases "
          "(reset, configure, main, shutdown ... - rarely used)"],
         ["`extract_phase`", "function", "bottom-up", "Collect final "
          "state, coverage"],
         ["`check_phase`", "function", "bottom-up", "End-of-test checks "
          "(scoreboard queues empty)"],
         ["`report_phase`", "function", "bottom-up", "Print results"],
         ["`final_phase`", "function", "top-down", "Close files"]],
        widths=[36, 10, 12, 42], bold_first=True)
    p("Build is top-down because a parent must exist - and must have "
      "published its configuration - before its children are created. Every "
      "other function phase is bottom-up. `run_phase` of every component "
      "starts at the same time and the phase ends when all **objections** "
      "have been dropped.")

    h2("Testbench topology")
    diagram([
        '+------------------------------ uvm_test_top (vr_base_test) -----------------------------+',
        '| +------------------------------------- env (vr_env) ---------------------------------+ |',
        '| |  +---- in_agt (active) ----+                          +---- out_agt (sink) ----+   | |',
        '| |  |  sqr <-> drv     mon    |                          |  drv(ready)     mon    |   | |',
        '| |  +---------|--------|------+                          +------|-----------|-----+   | |',
        '| |            |        | ap       +------------+                |           | ap      | |',
        '| |            |        +--------->|     sb     |<---------------------------+         | |',
        '| |            |          exp_imp  +------------+  act_imp       |                     | |',
        '| +------------|-------------------------------------------------|---------------------+ |',
        '+--------------|-------------------------------------------------|-----------------------+',
        '             in_if -------> [ DUT: skid buffer ] ------------> out_if',
    ], "The minimal environment built in this chapter: two valid/ready "
       "agents around a pass-through DUT (e.g. the skid buffer of Chapter "
       "10) and an in-order scoreboard.")

    h2("Sequence items and sequences")
    p("A **sequence item** is one transaction. A **sequence** is a class "
      "whose `body()` task generates items and hands them to a sequencer "
      "through the `start_item` / `finish_item` handshake. Sequences can "
      "start other sequences, which is how complex scenarios are layered "
      "from simple ones.")
    code([
        "`include \"uvm_macros.svh\"",
        "package vr_pkg;",
        "  import uvm_pkg::*;",
        "",
        "  class vr_item extends uvm_sequence_item;",
        "    `uvm_object_utils(vr_item)",
        "    rand bit [7:0]    data;",
        "    rand int unsigned delay;                  // idle cycles before the transfer",
        "    constraint c_delay { delay dist {0 := 6, [1:3] := 3, [4:10] :/ 1}; }",
        "",
        "    function new(string name = \"vr_item\");",
        "      super.new(name);",
        "    endfunction",
        "    virtual function string convert2string();",
        "      return $sformatf(\"data=%02h delay=%0d\", data, delay);",
        "    endfunction",
        "    virtual function void do_copy(uvm_object rhs);",
        "      vr_item t;",
        "      super.do_copy(rhs);",
        "      if (!$cast(t, rhs)) `uvm_fatal(\"CAST\", \"do_copy: wrong type\")",
        "      data  = t.data;",
        "      delay = t.delay;",
        "    endfunction",
        "    virtual function bit do_compare(uvm_object rhs, uvm_comparer comparer);",
        "      vr_item t;",
        "      if (!$cast(t, rhs)) return 0;",
        "      return super.do_compare(rhs, comparer) && (data == t.data);  // not delay",
        "    endfunction",
        "  endclass",
        "",
        "  class vr_rand_seq extends uvm_sequence #(vr_item);",
        "    `uvm_object_utils(vr_rand_seq)",
        "    rand int unsigned n_items = 20;",
        "    constraint c_n { n_items inside {[1:1000]}; }",
        "    function new(string name = \"vr_rand_seq\");",
        "      super.new(name);",
        "    endfunction",
        "    virtual task body();",
        "      repeat (n_items) begin",
        "        req = vr_item::type_id::create(\"req\");   // factory, never new()",
        "        start_item(req);                           // wait for the driver",
        "        if (!req.randomize()) `uvm_fatal(\"RAND\", \"vr_item randomize failed\")",
        "        finish_item(req);                          // wait for item_done()",
        "      end",
        "    endtask",
        "  endclass",
    ], "Transaction and sequence (vr_pkg, part 1). `do_compare` deliberately "
       "ignores the timing-only field `delay`.")
    box("tip", "Field macros versus do_* methods",
        "`uvm_field_int(data, UVM_ALL_ON)` inside "
        "`uvm_object_utils_begin/end` generates copy, compare, print and "
        "pack automatically. It is convenient but slow and hard to debug; "
        "many companies' coding guidelines require hand-written "
        "`do_copy`, `do_compare` and `convert2string`, as above.")

    h2("Driver, monitor and the sequencer handshake")
    code([
        "interface vr_if (input logic clk, input logic rst_n);",
        "  logic       valid, ready;",
        "  logic [7:0] data;",
        "  clocking src_cb @(posedge clk);             // used by a source driver",
        "    default input #1step output #1;",
        "    output valid, data;  input ready;",
        "  endclocking",
        "  clocking snk_cb @(posedge clk);             // used by a sink driver",
        "    default input #1step output #1;",
        "    input valid, data;   output ready;",
        "  endclocking",
        "  clocking mon_cb @(posedge clk);             // passive sampling",
        "    default input #1step;",
        "    input valid, ready, data;",
        "  endclocking",
        "endinterface",
    ], "The interface shared by both agents (compiled before vr_pkg).")
    code([
        "  class vr_driver extends uvm_driver #(vr_item);",
        "    `uvm_component_utils(vr_driver)",
        "    virtual vr_if vif;",
        "    bit is_sink;                              // 1: drive ready, not valid/data",
        "    function new(string name, uvm_component parent);",
        "      super.new(name, parent);",
        "    endfunction",
        "    virtual function void build_phase(uvm_phase phase);",
        "      super.build_phase(phase);",
        "      if (!uvm_config_db#(virtual vr_if)::get(this, \"\", \"vif\", vif))",
        "        `uvm_fatal(\"NOVIF\", \"virtual interface 'vif' not set\")",
        "      void'(uvm_config_db#(bit)::get(this, \"\", \"is_sink\", is_sink));",
        "    endfunction",
        "    virtual task run_phase(uvm_phase phase);",
        "      if (is_sink) drive_ready(); else drive_items();",
        "    endtask",
        "    task drive_items();",
        "      vif.src_cb.valid <= 1'b0;",
        "      @(posedge vif.rst_n);",
        "      forever begin",
        "        seq_item_port.get_next_item(req);      // blocks until a sequence sends",
        "        repeat (req.delay) @(vif.src_cb);",
        "        vif.src_cb.valid <= 1'b1;",
        "        vif.src_cb.data  <= req.data;",
        "        do @(vif.src_cb); while (!vif.src_cb.ready);",
        "        vif.src_cb.valid <= 1'b0;",
        "        seq_item_port.item_done();             // unblocks finish_item()",
        "      end",
        "    endtask",
        "    task drive_ready();                        // random back-pressure",
        "      forever begin",
        "        @(vif.snk_cb);",
        "        vif.snk_cb.ready <= ($urandom_range(3) != 0);",
        "      end",
        "    endtask",
        "  endclass",
        "",
        "  class vr_monitor extends uvm_monitor;",
        "    `uvm_component_utils(vr_monitor)",
        "    virtual vr_if vif;",
        "    uvm_analysis_port #(vr_item) ap;           // broadcast to any subscribers",
        "    function new(string name, uvm_component parent);",
        "      super.new(name, parent);",
        "    endfunction",
        "    virtual function void build_phase(uvm_phase phase);",
        "      super.build_phase(phase);",
        "      ap = new(\"ap\", this);",
        "      if (!uvm_config_db#(virtual vr_if)::get(this, \"\", \"vif\", vif))",
        "        `uvm_fatal(\"NOVIF\", \"virtual interface 'vif' not set\")",
        "    endfunction",
        "    virtual task run_phase(uvm_phase phase);",
        "      forever begin",
        "        @(vif.mon_cb);",
        "        if (vif.rst_n && vif.mon_cb.valid && vif.mon_cb.ready) begin",
        "          vr_item t = vr_item::type_id::create(\"t\");   // NEW object each time",
        "          t.data = vif.mon_cb.data;",
        "          ap.write(t);",
        "        end",
        "      end",
        "    endtask",
        "  endclass",
    ], "Driver and monitor (vr_pkg, part 2).")
    diagram([
        "  sequence (body)              sequencer (arbitration)         driver",
        "  start_item(req)  ----------> grant when driver asks <------- get_next_item(req)",
        "  randomize req",
        "  finish_item(req) ----------> item delivered ----------------> drive pins ...",
        "        | blocks                                                 ...",
        "        +<---------------------- done <------------------------- item_done()",
    ], "The sequence-sequencer-driver handshake. Late randomization (between "
       "start_item and finish_item) lets an item react to the current state.")
    box("warn", "PITFALL: the monitor that reuses one object",
        "Analysis ports pass a **handle**. A monitor that creates one "
        "`vr_item` in build_phase and overwrites its fields for every "
        "transfer corrupts every item already queued in the scoreboard, "
        "which then compares an object with itself. Create a new object per "
        "transaction (or clone it before `write`).")

    h2("Agent, scoreboard, environment and TLM connections")
    code([
        "  class vr_agent extends uvm_agent;",
        "    `uvm_component_utils(vr_agent)",
        "    vr_driver                drv;",
        "    vr_monitor               mon;",
        "    uvm_sequencer #(vr_item) sqr;",
        "    function new(string name, uvm_component parent);",
        "      super.new(name, parent);",
        "    endfunction",
        "    virtual function void build_phase(uvm_phase phase);",
        "      super.build_phase(phase);",
        "      mon = vr_monitor::type_id::create(\"mon\", this);",
        "      if (get_is_active() == UVM_ACTIVE) begin",
        "        drv = vr_driver::type_id::create(\"drv\", this);",
        "        sqr = uvm_sequencer#(vr_item)::type_id::create(\"sqr\", this);",
        "      end",
        "    endfunction",
        "    virtual function void connect_phase(uvm_phase phase);",
        "      if (get_is_active() == UVM_ACTIVE)",
        "        drv.seq_item_port.connect(sqr.seq_item_export);",
        "    endfunction",
        "  endclass",
        "",
        "  `uvm_analysis_imp_decl(_exp)                  // creates uvm_analysis_imp_exp",
        "  `uvm_analysis_imp_decl(_act)",
        "  class vr_scoreboard extends uvm_scoreboard;",
        "    `uvm_component_utils(vr_scoreboard)",
        "    uvm_analysis_imp_exp #(vr_item, vr_scoreboard) exp_imp;",
        "    uvm_analysis_imp_act #(vr_item, vr_scoreboard) act_imp;",
        "    vr_item exp_q[$];",
        "    int     n_match, n_err;",
        "    function new(string name, uvm_component parent);",
        "      super.new(name, parent);",
        "    endfunction",
        "    virtual function void build_phase(uvm_phase phase);",
        "      super.build_phase(phase);",
        "      exp_imp = new(\"exp_imp\", this);",
        "      act_imp = new(\"act_imp\", this);",
        "    endfunction",
        "    // Reference model: a pass-through DUT must deliver the same data in order",
        "    function void write_exp(vr_item t);",
        "      exp_q.push_back(t);",
        "    endfunction",
        "    function void write_act(vr_item t);",
        "      vr_item e;",
        "      if (exp_q.size() == 0) begin",
        "        `uvm_error(\"SB\", {\"unexpected output: \", t.convert2string()})",
        "        n_err++;",
        "        return;",
        "      end",
        "      e = exp_q.pop_front();",
        "      if (t.compare(e)) n_match++;",
        "      else begin",
        "        `uvm_error(\"SB\", $sformatf(\"got %s exp %s\",",
        "                   t.convert2string(), e.convert2string()))",
        "        n_err++;",
        "      end",
        "    endfunction",
        "    virtual function void check_phase(uvm_phase phase);",
        "      if (exp_q.size() != 0)",
        "        `uvm_error(\"SB\", $sformatf(\"%0d items never came out\", exp_q.size()))",
        "      if (n_match == 0) `uvm_error(\"SB\", \"no transfers were checked\")",
        "    endfunction",
        "    virtual function void report_phase(uvm_phase phase);",
        "      `uvm_info(\"SB\", $sformatf(\"matches=%0d errors=%0d\", n_match, n_err), UVM_LOW)",
        "    endfunction",
        "  endclass",
        "",
        "  class vr_env extends uvm_env;",
        "    `uvm_component_utils(vr_env)",
        "    vr_agent      in_agt, out_agt;",
        "    vr_scoreboard sb;",
        "    function new(string name, uvm_component parent);",
        "      super.new(name, parent);",
        "    endfunction",
        "    virtual function void build_phase(uvm_phase phase);",
        "      super.build_phase(phase);",
        "      uvm_config_db#(bit)::set(this, \"out_agt.drv\", \"is_sink\", 1'b1);",
        "      in_agt  = vr_agent::type_id::create(\"in_agt\", this);",
        "      out_agt = vr_agent::type_id::create(\"out_agt\", this);",
        "      sb      = vr_scoreboard::type_id::create(\"sb\", this);",
        "    endfunction",
        "    virtual function void connect_phase(uvm_phase phase);",
        "      in_agt.mon.ap.connect(sb.exp_imp);",
        "      out_agt.mon.ap.connect(sb.act_imp);",
        "    endfunction",
        "  endclass",
    ], "Agent, scoreboard and environment (vr_pkg, part 3).")
    tbl(["TLM element", "Direction / semantics"],
        [["`uvm_seq_item_pull_port` (`seq_item_port`)", "Driver pulls items "
          "from the sequencer: `get_next_item`, `item_done`, `try_next_item`"],
         ["`uvm_analysis_port #(T)`", "One-to-many broadcast; `write()` is "
          "a **function** (no blocking); zero subscribers is legal"],
         ["`uvm_analysis_imp #(T, IMP)`", "Terminates a connection; calls "
          "`IMP::write(T)`. `uvm_analysis_imp_decl(_sfx)` makes variants "
          "with `write_sfx` for components with several inputs"],
         ["`uvm_tlm_analysis_fifo #(T)`", "Unbounded FIFO with an analysis "
          "export; lets a scoreboard `get()` items in its own run_phase"],
         ["`uvm_blocking_put/get_port`", "Point-to-point, may block - "
          "used between stimulus layers"]],
        widths=[38, 62], bold_first=True)

    h2("Tests, config_db, the factory and objections")
    code([
        "  class vr_base_test extends uvm_test;",
        "    `uvm_component_utils(vr_base_test)",
        "    vr_env env;",
        "    function new(string name, uvm_component parent);",
        "      super.new(name, parent);",
        "    endfunction",
        "    virtual function void build_phase(uvm_phase phase);",
        "      super.build_phase(phase);",
        "      env = vr_env::type_id::create(\"env\", this);",
        "    endfunction",
        "    virtual function void end_of_elaboration_phase(uvm_phase phase);",
        "      uvm_top.print_topology();",
        "    endfunction",
        "    virtual task run_phase(uvm_phase phase);",
        "      vr_rand_seq seq;",
        "      phase.raise_objection(this);             // keep run_phase alive",
        "      seq = vr_rand_seq::type_id::create(\"seq\");",
        "      if (!seq.randomize() with { n_items == 200; })",
        "        `uvm_fatal(\"RAND\", \"sequence randomize failed\")",
        "      seq.start(env.in_agt.sqr);",
        "      phase.get_objection().set_drain_time(this, 200ns);  // let outputs drain",
        "      phase.drop_objection(this);",
        "    endtask",
        "  endclass",
        "",
        "  // A test that changes the stimulus without touching the environment:",
        "  class vr_b2b_item extends vr_item;",
        "    `uvm_object_utils(vr_b2b_item)",
        "    constraint c_b2b { delay == 0; }           // back-to-back transfers",
        "    function new(string name = \"vr_b2b_item\");",
        "      super.new(name);",
        "    endfunction",
        "  endclass",
        "",
        "  class vr_b2b_test extends vr_base_test;",
        "    `uvm_component_utils(vr_b2b_test)",
        "    function new(string name, uvm_component parent);",
        "      super.new(name, parent);",
        "    endfunction",
        "    virtual function void build_phase(uvm_phase phase);",
        "      vr_item::type_id::set_type_override(vr_b2b_item::get_type());",
        "      super.build_phase(phase);",
        "    endfunction",
        "  endclass",
        "endpackage : vr_pkg",
    ], "Tests (vr_pkg, part 4): the factory override replaces every "
       "`vr_item` the sequence creates with a `vr_b2b_item`.")
    code([
        "module tb_top;",
        "  import uvm_pkg::*;",
        "  import vr_pkg::*;",
        "  logic clk = 1'b0, rst_n = 1'b0;",
        "  always #5 clk = ~clk;",
        "  initial #50 rst_n = 1'b1;",
        "",
        "  vr_if in_if  (.clk(clk), .rst_n(rst_n));",
        "  vr_if out_if (.clk(clk), .rst_n(rst_n));",
        "",
        "  skid_buffer #(.W(8)) dut (",
        "    .clk, .rst_n,",
        "    .s_valid(in_if.valid),  .s_ready(in_if.ready),  .s_data(in_if.data),",
        "    .m_valid(out_if.valid), .m_ready(out_if.ready), .m_data(out_if.data));",
        "",
        "  initial begin",
        "    uvm_config_db#(virtual vr_if)::set(null, \"uvm_test_top.env.in_agt*\",",
        "                                       \"vif\", in_if);",
        "    uvm_config_db#(virtual vr_if)::set(null, \"uvm_test_top.env.out_agt*\",",
        "                                       \"vif\", out_if);",
        "    run_test();                              // test named by +UVM_TESTNAME=...",
        "  end",
        "endmodule",
        "",
        "// Run:  <sim> ... +UVM_TESTNAME=vr_b2b_test +UVM_VERBOSITY=UVM_MEDIUM",
    ], "The static top: the only module in a UVM testbench besides the DUT "
       "and interfaces.")
    tbl(["Mechanism", "Key API", "Remember"],
        [["config_db", "`uvm_config_db#(T)::set(ctx, \"path\", \"field\", "
          "val)` / `::get(this, \"\", \"field\", var)`", "Type, path and "
          "field name must all match exactly; `get` returns 0 on a miss - "
          "check it. Higher-level (earlier) sets win in build_phase"],
         ["Factory", "`T::type_id::create(name, parent)`; "
          "`set_type_override`, `set_inst_override`", "Only objects created "
          "through `type_id::create` can be overridden; `new()` bypasses the "
          "factory silently"],
         ["Objections", "`phase.raise_objection(this)` / "
          "`drop_objection(this)`, drain time", "No objection raised -> "
          "run_phase ends at time 0 and the test 'passes' having done "
          "nothing"],
         ["Reporting", "`uvm_info(ID, msg, UVM_LOW)`, "
          "`uvm_error`, `uvm_fatal`", "Test status = no "
          "UVM_ERROR/UVM_FATAL in the report summary"]],
        widths=[16, 44, 40], bold_first=True)

    h2("The register abstraction layer (RAL)")
    p("Every block has control/status registers (Chapter 15), and every "
      "register must be tested for reset values, access policies and "
      "connectivity. UVM's **register layer** models the register map as "
      "objects - `uvm_reg_field` inside `uvm_reg` inside `uvm_reg_block` - "
      "normally **generated** from the same IP-XACT/SystemRDL source that "
      "generates the RTL. Tests then access registers by name, independent "
      "of the bus protocol.")
    code([
        "class ctrl_reg extends uvm_reg;",
        "  `uvm_object_utils(ctrl_reg)",
        "  rand uvm_reg_field en, mode;",
        "  function new(string name = \"ctrl_reg\");",
        "    super.new(name, 32, UVM_NO_COVERAGE);",
        "  endfunction",
        "  virtual function void build();",
        "    en = uvm_reg_field::type_id::create(\"en\");",
        "    //           parent size lsb access volatile reset has_rst is_rand indiv",
        "    en.configure(this, 1,   0,  \"RW\",  0,       1'b0, 1,      1,      0);",
        "    mode = uvm_reg_field::type_id::create(\"mode\");",
        "    mode.configure(this, 2, 1, \"RW\", 0, 2'b00, 1, 1, 0);",
        "  endfunction",
        "endclass",
        "",
        "// in a sequence or test:",
        "uvm_status_e status;  uvm_reg_data_t v;",
        "regmodel.ctrl.write(status, 32'h3);           // frontdoor: real bus cycles",
        "regmodel.ctrl.read (status, v);",
        "regmodel.ctrl.mirror(status, UVM_CHECK);      // read and compare with model",
        "regmodel.ctrl.peek(status, v);                // backdoor: HDL path, zero time",
    ], "A generated-style register class and typical accesses.")
    tbl(["RAL piece", "Role"],
        [["Register model (`uvm_reg_block`)", "Mirror of the DUT's "
          "registers with reset values and access policies (RW, RO, W1C ...)"],
         ["Adapter (`uvm_reg_adapter`)", "`reg2bus` / `bus2reg`: converts "
          "generic register operations to the bus agent's sequence items "
          "(APB, AXI-Lite)"],
         ["Predictor (`uvm_reg_predictor`)", "Updates the mirror from "
          "transactions observed by the bus monitor (explicit prediction)"],
         ["Frontdoor / backdoor", "Access through the bus / directly through "
          "HDL paths (fast init, checking without bus traffic)"],
         ["Built-in sequences", "`uvm_reg_hw_reset_seq`, "
          "`uvm_reg_bit_bash_seq`, `uvm_reg_access_seq`, "
          "`uvm_mem_walk_seq` - free register tests for every block"]],
        widths=[32, 68], bold_first=True)

    h2("Debugging UVM testbenches")
    tbl(["Symptom", "Likely cause", "Tool / fix"],
        [["Test ends at time 0, passes", "No objection raised in any "
          "run_phase", "`+UVM_OBJECTION_TRACE`"],
         ["Simulation hangs forever", "Driver never calls `item_done`; "
          "handshake waits for a ready that never comes", "Global timeout "
          "`+UVM_TIMEOUT=`, watchdog, check the driver loop"],
         ["`NOVIF` fatal / null handle", "config_db path, field name or "
          "type mismatch (`virtual vr_if` vs `virtual vr_if#(8)`)",
          "`+UVM_CONFIG_DB_TRACE`, `print_config()`"],
         ["Override has no effect", "Object created with `new()`, or "
          "override set after creation", "`factory.print()`, set overrides "
          "before `super.build_phase`"],
         ["Scoreboard compares object with itself", "Monitor reuses one "
          "item handle", "Create or clone per transaction"],
         ["Components missing", "Typo in create name; agent passive",
          "`uvm_top.print_topology()`"],
         ["Too much / too little log", "Verbosity", "`+UVM_VERBOSITY=`, "
          "`set_report_verbosity_level_hier`, per-ID "
          "`+uvm_set_verbosity`"],
         ["Phase ordering surprises", "Work done in the wrong phase",
          "`+UVM_PHASE_TRACE`"]],
        widths=[25, 40, 35], bold_first=True)
    box("expert", "What interviewers probe on UVM",
        "Explain the difference between `uvm_object` and `uvm_component`; "
        "why build_phase is top-down; what happens if you forget "
        "`raise_objection`; how the sequencer and driver hand items back and "
        "forth (`start_item`/`finish_item`, `get_next_item`/`item_done`); "
        "type versus instance overrides; `p_sequencer` versus `m_sequencer`; "
        "how a virtual interface gets from `tb_top` into a driver; and how "
        "RAL prediction works. Being able to sketch this chapter's topology "
        "on a whiteboard from memory covers most of it.")
    box("note", "UVM for a designer's own block tests",
        "UVM's overhead pays off for reusable, multi-engineer environments. "
        "For a designer's quick unit tests, the plain SystemVerilog of "
        "Chapter 22 or Python-based **cocotb** are often faster to write. "
        "Knowing all three - and when each fits - is the mark of a senior "
        "engineer.")

    h2("Summary")
    bul(["UVM standardizes how testbench components are built, connected, "
         "configured and run; the architecture is the same as Chapter 22's.",
         "Objects (items, sequences) are transient data; components (driver, "
         "monitor, sequencer, agent, env, test) form the static tree.",
         "Phases: build (top-down), connect, ..., run (task, objection-"
         "controlled), check, report.",
         "Sequences generate items; the driver pulls them via "
         "`seq_item_port`; monitors broadcast via analysis ports.",
         "config_db distributes virtual interfaces and settings; the factory "
         "allows overrides; always create with `type_id::create`.",
         "RAL models registers and gives free, protocol-independent "
         "register tests."])
    h2("Exercises")
    bul(["Add a functional covergroup to `vr_monitor` (data value ranges, "
         "delay 0 versus non-zero) and sample it on every transfer.",
         "Write a `vr_burst_seq` that runs `vr_rand_seq` three times with "
         "different `n_items`, using `uvm_do_with`-free code "
         "(`start_item`/`finish_item` only).",
         "Make the out agent configurable as a **passive** agent (monitor "
         "only) and explain what then must drive `ready`.",
         "Replace the `uvm_analysis_imp_decl` scoreboard with two "
         "`uvm_tlm_analysis_fifo`s and a run_phase that compares "
         "`get()` results. What changes about when mismatches are reported?",
         "Write the `reg2bus` and `bus2reg` functions of an APB adapter for "
         "an APB agent whose item has fields `addr`, `data`, `write`."],
        ordered=True)


# =============================================================================
#      Chapter 25 - Static sign-off: lint, CDC/RDC, formal, equivalence
# =============================================================================
def ch25():
    chapter("Static Sign-off: Lint, CDC/RDC, Formal and Equivalence Checking")
    p("Simulation answers 'does the design do the right thing **for the "
      "stimulus I applied**?'. Static methods answer questions simulation "
      "structurally cannot: is there **any** input sequence that breaks this "
      "property; is **every** clock-domain crossing synchronized; is the "
      "netlist **equivalent** to the RTL for **all** inputs. They read the "
      "design rather than run it, so they need no testbench and they are "
      "exhaustive within their scope. On a real tape-out, clean lint, CDC, "
      "RDC and equivalence reports - with every waiver reviewed - are "
      "mandatory sign-off gates alongside timing (Chapter 18) and power "
      "(Chapter 19).")

    h2("Where static checks fit")
    tbl(["Check", "Question answered", "Runs on", "When"],
        [["**Lint**", "Is the RTL well-formed, synthesizable, free of "
          "suspicious constructs?", "RTL", "Every commit (seconds)"],
         ["**CDC**", "Is every signal crossing between asynchronous clocks "
          "correctly synchronized?", "RTL (+ netlist)", "Weekly, then at "
          "every milestone"],
         ["**RDC**", "Can an asynchronous reset in one domain corrupt flops "
          "in another reset domain?", "RTL (+ netlist)", "With CDC"],
         ["**Formal (FPV)**", "Does a property hold for all legal input "
          "sequences?", "RTL + SVA", "Block level, during design"],
         ["**LEC**", "Is the netlist logically equivalent to the RTL?",
          "RTL vs netlist, netlist vs netlist", "After synthesis, DFT, "
          "every ECO"],
         ["**X-prop**", "Can X values hide bugs in simulation or appear in "
          "silicon?", "RTL", "Block and SoC level"]],
        widths=[15, 42, 20, 23], bold_first=True)
    box("key", "Why static checks catch what simulation cannot",
        "A CDC bug is a **probability**: a synchronizer-less crossing may "
        "work in a billion simulated cycles because RTL simulation has no "
        "metastability and no skew between bits. A lint issue such as an "
        "incomplete sensitivity list makes simulation **disagree with the "
        "hardware**, so the simulation that passed is irrelevant. Only a tool "
        "that reasons about structure or about all inputs finds these.")

    h2("Lint: rule categories")
    tbl(["Category", "Examples of rules", "Why it matters"],
        [["Synthesizability", "Delays `#5` in RTL, `initial` blocks, "
          "unsupported loops, real types", "Tool silently ignores or "
          "rejects"],
         ["Sim/synth mismatch", "Incomplete sensitivity list, `full_case`/"
          "`parallel_case` pragmas, X assignments used as don't-care",
          "RTL simulation no longer predicts the gates"],
         ["Inferred latches", "Incomplete `if`/`case` in combinational "
          "blocks", "Unintended storage, timing problems (Chapter 5)"],
         ["Width", "Truncation, extension, sign mismatch, unsized constants",
          "Silent arithmetic bugs"],
         ["Assignments", "Blocking in sequential blocks, non-blocking in "
          "combinational, multiple drivers", "Races and ordering bugs "
          "(Chapter 4)"],
         ["Clocks and resets", "Clock used as data, gated clocks built from "
          "logic, mixed async/sync resets, reset not synchronized",
          "Glitches, timing and DFT problems"],
         ["Structure", "Combinational loops, undriven/unloaded nets, "
          "floating inputs, implicit nets", "Oscillation, X, dead logic"],
         ["FSM", "Unreachable states, no default, terminal states",
          "Lock-ups"],
         ["Naming / style", "Suffix conventions (`_n`, `_q`), one module per "
          "file, header present", "Reviewability, automation"],
         ["DFT readiness", "Uncontrollable async resets/clocks, latches in "
          "scan paths", "Scan insertion problems (Chapter 20)"]],
        widths=[18, 48, 34], bold_first=True)
    p("The file below contains five classic mistakes. We run it through the "
      "two free tools available in this book's environment: Icarus with "
      "`-Wall`, and Verilator's dedicated linter.")
    code([
        'module lint_bait (',
        '  input  wire       clk,',
        '  input  wire [1:0] sel,',
        '  input  wire [7:0] a, b,',
        '  output reg  [7:0] y,',
        '  output reg  [3:0] q,',
        '  output wire [7:0] sum',
        ');',
        '  reg [7:0] t;',
        '  // (1) incomplete case in combinational block -> latch on y',
        '  always @(*)',
        '    case (sel)',
        "      2'd0: y = a;",
        "      2'd1: y = b;",
        '    endcase',
        '  // (2) incomplete sensitivity list -> sim/synth mismatch',
        '  always @(a)',
        '    t = a & b;',
        '  // (3) width truncation: 9-bit result into 8-bit net',
        "  assign sum = a + b + 9'd1;",
        '  // (4) blocking assignment in a clocked block',
        '  always @(posedge clk)',
        '    q = t[3:0];',
        '  // (5) implicit net from a typo',
        '  assign carr = a[7] & b[7];',
        'endmodule',
        ], "lint_bait.v - five deliberate problems.")
    code(["$ iverilog -g2012 -Wall -o /dev/null lint_bait.v",
          "$ verilator --lint-only -Wall lint_bait.v"])
    out(["lint_bait.v:25: warning: implicit definition of wire 'carr'."],
        "Icarus -Wall: a simulator's warnings are not a linter - only the "
        "implicit net is reported.")
    out(["%Warning-IMPLICIT: lint_bait.v:25:10: Signal definition not found, "
         "creating implicitly: 'carr'",
         "%Warning-WIDTHTRUNC: lint_bait.v:20:14: Operator ASSIGNW expects 8 "
         "bits on the Assign RHS, but",
         "                     Assign RHS's ADD generates 9 bits.",
         "%Warning-UNUSEDSIGNAL: lint_bait.v:9:13: Bits of signal are not used: "
         "'t'[7:4]",
         "%Warning-UNUSEDSIGNAL: lint_bait.v:25:10: Signal is not used: 'carr'",
         "%Warning-CASEINCOMPLETE: lint_bait.v:12:5: Case values incompletely "
         "covered (example pattern 0x2)",
         "%Warning-BLKSEQ: lint_bait.v:18:7: Blocking assignment '=' in "
         "sequential logic process",
         "%Warning-BLKSEQ: lint_bait.v:23:7: Blocking assignment '=' in "
         "sequential logic process",
         "%Error: Exiting due to 7 warning(s)"],
        "Verilator 5.020 --lint-only -Wall (one long line wrapped for the "
        "page).")
    p("Verilator found four of the five problems, but read the report "
      "critically. It reports the latch-producing `case` as "
      "CASEINCOMPLETE rather than as a latch; it classifies `always @(a)` "
      "as a **sequential** process (hence the BLKSEQ at line 18) instead of "
      "flagging the missing `b` in the sensitivity list, which is the real "
      "bug; and it has no opinion about the async/sync reset style. "
      "Commercial linters (Synopsys SpyGlass/VC SpyGlass, Real Intent "
      "Ascent Lint, Siemens Questa Lint, Cadence HAL/JasperGold Superlint) "
      "apply thousands of configurable rules, including the company's own "
      "coding guidelines (Chapter 27).")
    box("tip", "Cheap habits that remove whole lint categories",
        "Put `default_nettype none` at the top of every RTL file (and "
        "`default_nettype wire` at the end) - implicit nets become "
        "compile errors. Use `always_comb`/`always_ff`, which make "
        "sensitivity lists automatic and let tools check intent. Write "
        "explicitly sized constants and use `unique`/`priority` instead of "
        "synthesis pragmas.")
    box("note", "Waivers",
        "Not every lint message is a bug; the width warning on a deliberate "
        "carry drop is intended. Such messages are **waived** in a waiver "
        "file, with the rule, the exact location or signal, a reason and a "
        "reviewer. Blanket waivers ('turn off WIDTH everywhere') are how "
        "real bugs ship. Waivers are re-reviewed when the RTL changes.")

    h2("CDC verification")
    p("Chapter 11 designed the synchronizers; CDC sign-off proves that "
      "they are present and used correctly on **every** crossing of a chip "
      "that may have hundreds of clocks and tens of thousands of crossings. "
      "The flow of every commercial tool (Synopsys VC SpyGlass CDC, Siemens "
      "Questa CDC, Cadence Conformal/Jasper CDC, Real Intent Meridian CDC) "
      "is the same:")
    bul(["**Setup.** Define clocks and their relationships (asynchronous, "
         "synchronous, divided), resets, constant/static signals (mode pins "
         "that never toggle in function), and the synchronizer cells of the "
         "library. Much of this comes from the SDC (Chapter 18). A wrong "
         "setup gives either thousands of false violations or, worse, "
         "silently missed ones.",
         "**Structural analysis.** Find every crossing and classify it: "
         "synchronized by a recognized scheme (2-flop, pulse, handshake, "
         "async FIFO, MUX-enable) or not. Report missing synchronizers, "
         "combinational logic before a synchronizer, fan-out of a "
         "synchronizer input to several synchronizers (divergence), "
         "re-convergence of separately synchronized signals, and multi-bit "
         "buses crossing without a safe scheme.",
         "**Functional analysis.** Structural recognition assumes a "
         "protocol: the data of a MUX/handshake crossing is stable while "
         "sampled; a Gray-coded pointer changes one bit at a time; a pulse "
         "is wide enough for the destination clock. The tool generates "
         "assertions for these and checks them formally or in simulation.",
         "**Review and waive.** Every remaining violation is fixed or "
         "waived with a reason (for example, a quasi-static configuration "
         "register written only while the destination is idle).",
         "**Netlist CDC** repeats the analysis after synthesis, because "
         "synthesis can insert glitch-prone logic in front of a synchronizer "
         "or duplicate a synchronizer flop."], ordered=True)
    code([
        'module cdc_bad (',
        '  input  logic       clk_a, clk_b, rst_b_n,',
        '  input  logic       req_a, en_a,          // both in the clk_a domain',
        '  input  logic [3:0] cnt_a,                // binary counter in clk_a domain',
        '  output logic       go_b,',
        '  output logic [3:0] cnt_b',
        ');',
        '  // VIOLATION 1: combinational logic in front of a synchronizer.',
        '  // req_a & en_a can glitch between clk_a edges; clk_b may capture the glitch.',
        '  logic s1, s2;',
        '  always_ff @(posedge clk_b or negedge rst_b_n)',
        "    if (!rst_b_n) {s2, s1} <= '0;",
        '    else          {s2, s1} <= {s1, req_a & en_a};',
        '  assign go_b = s2;',
        '',
        '  // VIOLATION 2: multi-bit binary value through per-bit synchronizers.',
        '  // On 0111 -> 1000 each bit may resolve differently: clk_b can see 1111.',
        '  logic [3:0] c1, c2;',
        '  always_ff @(posedge clk_b or negedge rst_b_n)',
        "    if (!rst_b_n) {c2, c1} <= '0;",
        '    else          {c2, c1} <= {c1, cnt_a};',
        '  assign cnt_b = c2;',
        'endmodule',
        ], "Two violations every CDC tool reports (compiles and "
         "simulates fine - which is exactly the problem).")
    code([
        'module cdc_good (',
        '  input  logic       clk_a, rst_a_n, clk_b, rst_b_n,',
        '  input  logic       req_a, en_a,',
        '  input  logic [3:0] cnt_a,',
        '  output logic       go_b,',
        '  output logic [3:0] cnt_gray_b            // decode to binary in clk_b if needed',
        ');',
        '  // FIX 1: register the combinational term in the source domain first.',
        '  logic go_a, s1, s2;',
        '  always_ff @(posedge clk_a or negedge rst_a_n)',
        "    if (!rst_a_n) go_a <= 1'b0;",
        '    else          go_a <= req_a & en_a;',
        '  always_ff @(posedge clk_b or negedge rst_b_n)',
        "    if (!rst_b_n) {s2, s1} <= '0;",
        '    else          {s2, s1} <= {s1, go_a};',
        '  assign go_b = s2;',
        '',
        '  // FIX 2: Gray-code in the source domain (one bit changes per increment),',
        '  // register it, then synchronize. Valid only if cnt_a moves by +/-1 per clk_a.',
        '  logic [3:0] gray_a, g1, g2;',
        '  always_ff @(posedge clk_a or negedge rst_a_n)',
        "    if (!rst_a_n) gray_a <= '0;",
        '    else          gray_a <= cnt_a ^ (cnt_a >> 1);',
        '  always_ff @(posedge clk_b or negedge rst_b_n)',
        "    if (!rst_b_n) {g2, g1} <= '0;",
        '    else          {g2, g1} <= {g1, gray_a};',
        '  assign cnt_gray_b = g2;',
        'endmodule',
        ], "The fixes: register in the source domain, and "
         "Gray-code multi-bit counters before synchronizing.")
    diagram([
        "   clk_a domain                      clk_b domain",
        "  en_a --+",
        "         +--[AND]--X-->[s1]-->[s2]--> go_b    X = glitch can be captured",
        "  req_a -+",
        "",
        "  en_a --+",
        "         +--[AND]-->[go_a]--->[s1]-->[s2]--> go_b   registered: glitch-free",
        "  req_a -+           clk_a    clk_b",
        "",
        "  re-convergence:  a_q --sync--> x_b --+",
        "                                       +--[logic]--> may see (x_b,y_b) never",
        "                   b_q --sync--> y_b --+             produced in clk_a",
    ], "Combinational logic before a synchronizer, its fix, and "
       "re-convergence of independently synchronized signals.")
    box("warn", "PITFALL: 'it passed in simulation' is not CDC sign-off",
        "RTL simulation models a synchronizer as two ideal flops: a 1-cycle "
        "latency uncertainty and bit-to-bit skew simply do not exist. "
        "Re-convergence bugs therefore never appear in RTL simulation. Some "
        "simulators offer **metastability injection** (randomly adding a "
        "cycle of delay at synchronizers) to expose them - use it, but it is "
        "a complement to structural CDC, not a replacement.")

    h2("RDC verification")
    p("Reset-domain crossing (Chapter 12) is CDC's less famous sibling. "
      "Even with a single clock, when an **asynchronous reset** asserts in "
      "one reset domain, the flops it resets change at an arbitrary time "
      "relative to the clock. A flop in a different reset domain that is "
      "**not** being reset may sample that change during its setup/hold "
      "window and go metastable.")
    code([
        'module rdc_example (',
        '  input  logic clk, por_n, sw_rst_n,       // same clock, two reset domains',
        '  input  logic d,',
        '  output logic q_b',
        ');',
        '  // Flop A is reset by a software-controlled reset; flop B only by power-on reset.',
        '  logic q_a;',
        '  always_ff @(posedge clk or negedge sw_rst_n)',
        "    if (!sw_rst_n) q_a <= 1'b0;",
        '    else           q_a <= d;',
        '  // RDC: when sw_rst_n asserts asynchronously, q_a changes at an arbitrary time',
        '  // relative to clk, and flop B (NOT in reset) may sample it while it changes.',
        '  always_ff @(posedge clk or negedge por_n)',
        "    if (!por_n) q_b <= 1'b0;",
        '    else        q_b <= q_a;',
        'endmodule',
        ], "An RDC violation: sw_rst_n asserting can corrupt q_b, "
         "which is still in functional mode.")
    tbl(["Fix", "How"],
        [["Reset ordering", "Guarantee by design that the receiving domain "
          "is also in reset (or idle) whenever the source reset asserts - "
          "e.g. software resets only asserted after traffic is quiesced; "
          "RDC tools accept this as a constraint"],
         ["Isolation", "Gate the crossing data (AND with an 'isolate' "
          "signal) or gate the receiving clock while the source reset "
          "asserts"],
         ["Synchronization", "Treat the crossing like a CDC path and "
          "synchronize it in the receiving domain"],
         ["Same domain", "Put both flops in the same reset domain if the "
          "architecture allows"]],
        widths=[22, 78], bold_first=True)
    p("RDC tools (Synopsys VC SpyGlass RDC, Siemens Questa RDC, Real Intent "
      "Meridian RDC) need the reset tree, reset sequencing and isolation "
      "signals as setup, exactly as CDC tools need clocks.")

    h2("Formal property verification")
    p("A formal tool translates the RTL and its properties into a "
      "mathematical problem (usually Boolean satisfiability, SAT, or SMT) "
      "and asks: **is there any sequence of legal inputs that violates an "
      "assertion?** If yes, it returns a **counterexample** trace - "
      "typically a few cycles long, which is far easier to debug than a "
      "random simulation failure. If no, the property is **proven** for all "
      "inputs, for all time.")
    tbl(["Concept", "Meaning"],
        [["**BMC** (bounded model checking)", "Search all input sequences "
          "up to k cycles from reset. Finds bugs fast; a pass only means "
          "'no bug within k cycles' - a **bounded proof**"],
         ["**Induction**", "Base: property holds for the first k cycles "
          "from reset. Step: if it holds for any k consecutive cycles, it "
          "holds on the next. Both pass -> **full proof**"],
         ["**Induction failure**", "The step can fail from an **unreachable** "
          "state - a false counterexample. Fix by adding helper assertions "
          "(invariants) or increasing k"],
         ["**Assumptions**", "`assume property` restricts inputs to legal "
          "behaviour. Too few: false failures. Too many "
          "(**over-constraint**): real bugs hidden, even vacuous proofs"],
         ["**Cover**", "`cover property` asks the tool to **reach** a "
          "scenario - the sanity check that assumptions still allow "
          "interesting behaviour"],
         ["**State explosion**", "Proof effort grows with state; deep "
          "counters and memories are handled with abstraction, cut-points "
          "and black-boxing"]],
        widths=[26, 74], bold_first=True)
    p("We can demonstrate both outcomes with the open-source Yosys SAT "
      "engine. The design is a BCD counter with one safety property: it "
      "never leaves 0-9. Properties go inside `ifdef FORMAL` so that "
      "synthesis and simulation ignore them.")
    code([
        'module bcd_cnt (',
        '  input  logic       clk, rst,',
        '  input  logic       en,',
        '  output logic [3:0] q',
        ');',
        '  always_ff @(posedge clk)',
        "    if (rst)          q <= 4'd0;",
        "    else if (en)      q <= (q == 4'd9) ? 4'd0 : q + 4'd1;",
        '',
        '`ifdef FORMAL',
        '  // Safety property: the counter never leaves the BCD range 0..9.',
        "  always_comb if (!rst) assert (q <= 4'd9);",
        '`endif',
        'endmodule',
        ], "A BCD counter with an embedded immediate assertion "
         "(Yosys treats it as a formal property).")
    code(["$ yosys -p \"read_verilog -sv -formal bcd.sv; prep -top bcd_cnt; \\",
          "           sat -tempinduct -prove-asserts -set-at 1 rst 1 -maxsteps 20\""],
         "k-induction, with reset forced in the first cycle.")
    out(["[base case 1] Solving problem with 167 variables and 442 clauses..",
         "Base case for induction length 1 proven.",
         "[induction step 1] Solving problem with 340 variables and 911 clauses..",
         "Induction step proven: SUCCESS!"],
        "Excerpt of the Yosys log: a full proof by 1-induction - q stays in "
        "0..9 for every input sequence, forever.")
    p("Without `-set-at 1 rst 1` the base case fails immediately with "
      "`init q = 10`: the tool is free to start in any state, and an "
      "unreset flop can power up as 10. This is the formal view of why "
      "reset matters. Now introduce a bug - wrap at 10 instead of 9:")
    code(["    else if (en)      q <= (q == 4'd10) ? 4'd0 : q + 4'd1;   // BUG"])
    out(["Base case for induction length 11 proven.",
         "[induction step 11] Solving problem with 2969 variables and 8493 clauses..",
         "Induction step failed. Incrementing induction length.",
         "[base case 12] Solving problem with 2985 variables and 8544 clauses..",
         "SAT temporal induction proof finished - model found for base case: FAIL!",
         "  Time Signal Name             Dec       Hex           Bin",
         "  init \\q                       12         c          1100",
         "     1 \\q                       12         c          1100",
         "     2 \\q                        0         0          0000",
         "     3 \\q                        1         1          0001",
         "    11 \\q                        9         9          1001",
         "    12 \\q                       10         a          1010"],
        "Abridged log (separator lines and steps 4-10 removed): the 12-cycle counterexample - reset, "
        "count 0..9, then the illegal 10.")
    p("Notice the induction steps that failed first: from an arbitrary "
      "(possibly unreachable) state the step fails until k is long enough to "
      "force the trace back through reset. This is the typical "
      "'induction failure is not a bug' situation; production tools report "
      "such steps as **undetermined** and the engineer adds an invariant to "
      "close the proof.")
    h3("SymbiYosys and the commercial tools")
    p("For real projects, the open-source front end is **SymbiYosys** "
      "(`sby`), which drives Yosys and SMT solvers (Yices, Boolector, Z3) "
      "with BMC, k-induction and PDR/IC3 engines and full SVA support in "
      "its commercial variant. A job file looks like this (shown without "
      "output):")
    code([
        "[tasks]",
        "prove",
        "cover",
        "",
        "[options]",
        "prove: mode prove",
        "prove: depth 20",
        "cover: mode cover",
        "cover: depth 40",
        "",
        "[engines]",
        "smtbmc yices",
        "",
        "[script]",
        "read -formal fifo.sv fifo_props.sv",
        "prep -top sync_fifo",
        "",
        "[files]",
        "fifo.sv",
        "fifo_props.sv",
    ], "fifo.sby - a SymbiYosys job with a proof task and a cover task.")
    p("Industrial formal is done with Cadence JasperGold, Synopsys VC "
      "Formal and Siemens Questa Formal. Beyond hand-written properties "
      "they offer push-button **apps**: connectivity checking (SoC pin-mux "
      "and top-level wiring), X-propagation, register (CSR) checking, "
      "sequential equivalence, unreachability analysis to exclude dead "
      "coverage bins, security/information-flow and deadlock checks.")
    box("expert", "Where formal beats simulation - and where it does not",
        "Formal excels on **control-dominated** blocks with deep corner "
        "cases: arbiters, FIFOs and credit logic, cache-coherence and "
        "interrupt controllers, CDC protocols, and anything where one "
        "counterexample in a trillion is still a bug. It struggles with "
        "**wide datapaths** (multipliers, floating point) and very deep "
        "sequential behaviour, where specialized datapath equivalence "
        "(C-to-RTL) or simulation are better. Mature teams plan which "
        "blocks are 'formal-signed-off' at the start of the project.")

    h2("Equivalence checking")
    p("**Logic equivalence checking (LEC)** proves that two representations "
      "of a design implement the same Boolean function: RTL versus the "
      "synthesized netlist, pre- versus post-scan-insertion netlist, "
      "netlist versus post-layout netlist, and before versus after every "
      "ECO. It is the check that allows the team to trust that the "
      "gates sent to the foundry are the RTL that was verified. Tools: "
      "Cadence Conformal LEC, Synopsys Formality, Siemens FormalPro.")
    diagram([
        "  golden (RTL)                        revised (netlist)",
        "  inputs --+--[comb cone]--> flop A    inputs --+--[gate cone]--> flop A'",
        "           |                                    |",
        "           +--[comb cone]--> output             +--[gate cone]--> output",
        "",
        "  1. map key points:  flop A <-> flop A', output <-> output (by name/structure)",
        "  2. for every compare point prove: cone(golden) == cone(revised) for all inputs",
        "  3. non-equivalent -> counterexample input vector",
    ], "Combinational equivalence: registers become cut points, so only "
       "combinational cones are compared.")
    p("Combinational LEC maps registers one-to-one, which is why it is "
      "fast and why it breaks when synthesis **retimes** registers, "
      "re-encodes FSMs, merges or duplicates flops, or inserts clock "
      "gating. Those optimizations need **sequential equivalence checking** "
      "(SEC), which compares behaviour at the outputs over time without a "
      "register mapping - also the method for verifying a hand-optimized "
      "or low-power version of a block against the original RTL. The "
      "synthesis tool helps LEC by writing a 'guidance' file (SVF in "
      "Synopsys flows) that records its transformations.")
    p("A miniature LEC with Yosys: prove that a hand-optimized ALU with one "
      "shared adder for ADD and SUB is equivalent to the reference ALU of "
      "Chapter 22. The miter compares the outputs of both for identical "
      "inputs and the SAT solver searches for any input that makes them "
      "differ.")
    code([
        '// Hand-optimized ALU: one shared adder does both ADD and SUB.',
        'module alu_opt (',
        '  input  logic [1:0] op,',
        '  input  logic [7:0] a, b,',
        '  output logic [7:0] y,',
        '  output logic       c',
        ');',
        '  logic       sub;',
        '  logic [8:0] sum;',
        "  assign sub = (op == 2'd1);",
        "  assign sum = {1'b0, a} + {1'b0, b ^ {8{sub}}} + 9'(sub);   // a + ~b + 1",
        '  always_comb begin',
        "    c = 1'b0;",
        '    case (op)',
        "      2'd0, 2'd1: begin y = sum[7:0]; c = sum[8] ^ sub; end   // borrow = !carry",
        "      2'd2:       y = a & b;",
        '      default:    y = a ^ b;',
        '    endcase',
        '  end',
        'endmodule',
        ], "Revised design: one adder computes a + b or "
         "a + ~b + 1 (also passes the Chapter 22 testbench).")
    code([
        '# Combinational equivalence: golden RTL vs hand-optimized RTL',
        'read_verilog -sv alu.sv alu_opt.sv',
        'proc; opt_clean',
        'miter -equiv -flatten -make_assert alu alu_opt miter',
        'sat -verify -prove-asserts -show-inputs miter',
        ], "lec.ys")
    out(["Solving problem with 951 variables and 2573 clauses..",
         "SAT proof finished - no model found: SUCCESS!"],
        "Excerpt: no input distinguishes the designs - proven for all "
        "2^{18} input combinations at once.")
    p("If the optimizer forgets that the borrow of a subtraction is the "
      "**inverted** carry (`c = sum[8]` instead of `sum[8] ^ sub`), the "
      "check returns a counterexample in milliseconds:")
    out(["SAT proof finished - model found: FAIL!",
         "  Signal Name             Dec       Hex           Bin",
         "  --------------- ----------- --------- -------------",
         "  \\in_a                    42        2a      00101010",
         "  \\in_b                    50        32      00110010",
         "  \\in_op                    1         1            01",
         "  \\trigger                  1         1             1"],
        "42 - 50 must borrow; the buggy design reports no borrow. A random "
        "test would find this too - but LEC proves the fixed version has no "
        "other such input.")
    p("Finally the real use: RTL versus the gate-level netlist produced by "
      "synthesis.")
    code([
        '# 1. Synthesize the RTL to a generic gate netlist (the "revised" design)',
        'read_verilog -sv alu.sv',
        'synth -flatten -top alu',
        'abc -g AND,NAND,OR,NOR,XOR,XNOR,MUX',
        'stat',
        'rename alu alu_gate',
        'write_verilog -noattr alu_gate.v',
        'design -reset',
        '# 2. Compare golden RTL against the netlist',
        'read_verilog -sv alu.sv',
        'read_verilog alu_gate.v',
        'proc; opt_clean',
        'miter -equiv -flatten -make_assert alu alu_gate miter',
        'sat -verify -prove-asserts miter',
        ], "lec_gate.ys - synthesize, then prove the netlist "
         "equivalent to the RTL.")
    out(["   Number of cells:                139",
         "     $_AND_                         30",
         "     $_NAND_                        67",
         "     $_NOR_                          1",
         "     $_NOT_                          9",
         "     $_OR_                          15",
         "     $_XNOR_                         3",
         "     $_XOR_                         14",
         "Solving problem with 1482 variables and 3866 clauses..",
         "SAT proof finished - no model found: SUCCESS!"],
        "Excerpt: 139 generic gates, formally equivalent to the 16-line RTL.")
    box("warn", "PITFALL: LEC setup that proves the wrong thing",
        "LEC must be run with the **functional** mode constrained: scan "
        "enable and test mode tied inactive, otherwise the scan-inserted "
        "netlist is (correctly) not equivalent. Conversely, over-"
        "constraining - tying off a pin that is not really constant - makes "
        "LEC pass on a broken netlist. Every LEC constraint and every "
        "'black-boxed' module (memories, analog macros) must be reviewed; "
        "unmapped and unreachable key points are warnings to read, not to "
        "ignore.")

    h2("X-propagation checking")
    p("RTL simulation handles unknown values optimistically: an `if` with "
      "an X condition takes the else branch, a `case` with an X selector "
      "matches nothing, so an uninitialized flop can silently produce a "
      "**clean** output in RTL simulation while real silicon powers up to a "
      "random 0 or 1 (Chapter 26 demonstrates this with Icarus). The "
      "opposite, **X-pessimism**, appears in gate-level simulation, where a "
      "MUX with an X select and equal data inputs outputs X although "
      "hardware would output the data value.")
    tbl(["Technique", "What it does"],
        [["Simulator X-prop modes", "VCS `-xprop`, Xcelium X-propagation "
          "options: `if`/`case` with X conditions merge both branches "
          "(T-merge/X-merge), making RTL simulation pessimistic like "
          "hardware"],
         ["Formal X-prop apps", "Prove that no X from uninitialized "
          "registers or X-assignments can reach outputs or specified "
          "control points after reset"],
         ["Reset-less flop review", "List every flop without reset (common "
          "in datapaths for area/power) and prove its value is written "
          "before it is used - typically with a 'valid' qualifier"],
         ["Assertions", "`!$isunknown(ctrl)` checks on every control signal "
          "and interface (Chapter 23)"],
         ["Randomized initialization", "Simulator options that initialize "
          "unreset flops to random 0/1 instead of X, across seeds"]],
        widths=[26, 74], bold_first=True)

    h2("A sign-off checklist")
    checklist("Static sign-off before RTL freeze and tape-out", [
        "Lint clean against the project rule set; every waiver has a reason "
        "and a reviewer.",
        "CDC setup reviewed (clocks, resets, constants, synchronizer cells); "
        "zero unwaived structural violations; functional CDC assertions "
        "proven or simulated.",
        "RDC clean, with reset sequencing constraints documented.",
        "Formal: planned properties proven or bounded to an agreed depth; "
        "covers reachable; no vacuous proofs.",
        "LEC: RTL vs synthesis netlist, synthesis vs DFT netlist, DFT vs "
        "post-layout netlist, and after every ECO - all equivalent, with "
        "reviewed constraints and black boxes.",
        "X-prop: unreset flops reviewed; X-prop simulation or formal app "
        "clean.",
        "Netlist-level CDC and gate-level simulation (Chapter 26) run on the "
        "final netlist.",
    ])

    h2("Summary")
    bul(["Static checks are exhaustive within their scope and need no "
         "testbench; they are mandatory sign-off gates.",
         "Lint catches synthesizability, sim/synth mismatch, width, latch "
         "and style issues; free tools find a subset - read reports "
         "critically and waive precisely.",
         "CDC flow: setup -> structural -> functional -> review/waive -> "
         "netlist CDC. RDC checks asynchronous-reset crossings the same way.",
         "Formal: BMC finds bugs and gives bounded proofs; induction gives "
         "full proofs; assumptions constrain inputs and must be covered to "
         "avoid over-constraint.",
         "LEC proves RTL and netlists equivalent after every transformation; "
         "sequential equivalence handles retiming, re-encoding and clock "
         "gating.",
         "X-propagation checking closes the gap between optimistic RTL "
         "simulation and real power-up behaviour."])
    h2("Exercises")
    bul(["Fix all five problems in `lint_bait.v` and get Verilator "
         "`--lint-only -Wall` to report nothing, without any lint_off "
         "pragma.",
         "Write the formal property 'the FIFO of Chapter 22 is never full "
         "and empty at once' inside `ifdef FORMAL`, and prove it with "
         "`sat -tempinduct`. Does 1-induction succeed? If not, which helper "
         "invariant closes it?",
         "In `cdc_good.sv`, the Gray-code fix is valid only if `cnt_a` "
         "changes by at most one per `clk_a` cycle. Write an assertion that "
         "checks this assumption.",
         "Modify `alu_opt.sv` so that it is equivalent for ADD, SUB and AND "
         "but not XOR, and read the LEC counterexample. How many "
         "counterexamples exist in total?",
         "List three synthesis transformations that break combinational "
         "LEC key-point mapping and explain how each is handled in a "
         "production flow."], ordered=True)


# =============================================================================
#   Chapter 26 - Debug, gate-level simulation, FPGA prototyping, emulation
# =============================================================================
def ch26():
    chapter("Debug, Gate-Level Simulation, FPGA Prototyping and Emulation")
    p("The previous chapters were about **finding** that something is wrong. "
      "This one is about finding **why**, and about the verification "
      "platforms that take over when RTL simulation becomes too slow or too "
      "idealized: gate-level simulation of the real netlist, FPGA "
      "prototypes and hardware emulators that run billions of cycles, "
      "hardware/software co-verification, and finally debug on the silicon "
      "itself. Debug skill is the most under-taught and most valued ability "
      "in the industry: a senior engineer is, above all, someone who "
      "reliably finds root causes quickly.")

    h2("A debugging methodology")
    bul(["**Reproduce.** Rerun the failing test with the same seed, the "
         "same build and the same command line. A bug you cannot reproduce "
         "you cannot fix - log the seed of every random run.",
         "**Find the first symptom.** The scoreboard error is usually far "
         "downstream of the cause. Look for the **earliest** assertion, "
         "error or divergence from the model; with transaction logs from "
         "every monitor, compare expected and actual streams to find the "
         "first bad transaction and its time.",
         "**Localize in time and space.** Dump waves only around that time "
         "and only for the relevant hierarchy. Trace the wrong value "
         "**backwards**: which driver produced it, from which inputs, in "
         "which cycle? Repeat until you reach a value that is wrong while "
         "its inputs are right - that is the bug.",
         "**Form a hypothesis and test it.** Predict what a change should "
         "do before making it ('if the full flag is late by one cycle, "
         "forcing it here will make the error disappear').",
         "**Fix, then generalize.** After the fix, ask: where else did the "
         "same pattern get written? Add an assertion that would have "
         "caught it at the source, and add the seed or a directed test to "
         "the regression.",
         "**Classify.** Is it a DUT bug, a testbench bug, a model bug or a "
         "spec ambiguity? Roughly half of all failures in a young "
         "environment are testbench bugs."], ordered=True)

    h2("Waveforms: $dumpfile, $dumpvars and GTKWave")
    tbl(["System task", "Purpose"],
        [["`$dumpfile(\"f.vcd\")`", "Name the VCD (Value Change Dump) file"],
         ["`$dumpvars(depth, scope)`", "Record changes in scope and "
          "`depth` levels below it; depth 0 = everything"],
         ["`$dumpoff` / `$dumpon`", "Pause and resume recording (skip "
          "long idle or initialization phases)"],
         ["`$dumplimit(bytes)`", "Cap the file size"],
         ["`$dumpall` / `$dumpflush`", "Checkpoint all values / flush to "
          "disk (useful before a crash)"]],
        widths=[32, 68], bold_first=True)
    code([
        '`timescale 1ns/1ps',
        'module tb_vcd;',
        '  logic clk = 0, rst_n = 0, wr_en = 0, rd_en = 0;',
        '  logic [7:0] wdata = 0, rdata;',
        '  logic full, empty;',
        '  sync_fifo #(.W(8), .DEPTH(4)) dut (.*);',
        '  always #5 clk = ~clk;',
        '  initial begin',
        '    $dumpfile("fifo.vcd");             // open the VCD file',
        '    $dumpvars(0, tb_vcd);              // depth 0 = everything below tb_vcd',
        '    #12 rst_n = 1;',
        "    repeat (3) begin @(negedge clk) wr_en = 1; wdata = wdata + 8'h11; end",
        '    @(negedge clk) begin wr_en = 0; rd_en = 1; end',
        '    #20 $dumpoff;                      // stop dumping (e.g. skip a long idle phase)',
        '    #100 $dumpon;',
        '    #20 $finish;',
        '  end',
        'endmodule',
        ], "Dumping the FIFO of Chapter 22 to a VCD file.")
    out(["VCD info: dumpfile fifo.vcd opened for output.",
         "tb_vcd.sv:16: $finish called at 190000 (1ps)"])
    code([
        "$timescale",
        "  1ps",
        "$end",
        "$scope module tb_vcd $end",
        "$var wire 8 ! rdata [7:0] $end",
        "$var wire 1 \" full $end",
        "$var wire 1 # empty $end",
        "$var reg 1 $ clk $end",
        "...",
        "$enddefinitions $end",
        "#0",
        "$dumpvars",
        "bx /",
        "b0 *",
    ], "Start of fifo.vcd (abridged): a header that maps short identifier "
       "codes to signals, then time stamps (#t) and value changes.")
    p("Open the file with `gtkwave fifo.vcd`, drag signals from the "
      "hierarchy into the wave pane, and save the signal list as a `.gtkw` "
      "file so the next debug session starts where this one ended. VCD is "
      "plain text and very large; Icarus can write the compact **FST** "
      "format (`vvp sim -fst`) that GTKWave also reads. Commercial flows "
      "use their own compressed databases - FSDB (Synopsys Verdi), SHM "
      "(Cadence SimVision) and WLF (Siemens Visualizer/Questa) - with "
      "driver/load tracing, schematic views and the ability to trace a "
      "value backwards through the design with one click.")
    box("tip", "Dump strategically",
        "Dumping every signal of a SoC for a long test can slow simulation "
        "by 2-10x and produce hundreds of gigabytes. Dump only the "
        "hierarchy under suspicion, start dumping shortly before the first "
        "symptom (`$dumpon` at a time given by a plusarg), and rely on "
        "transaction logs to find that time first.")

    h2("Common bug patterns")
    tbl(["Pattern", "Typical symptom", "Where to look"],
        [["Off-by-one in full/empty/count", "Overflow or lost data only at "
          "exact capacity", "Pointer compare, count update on simultaneous "
          "read+write"],
         ["Missing or wrong reset", "X after reset; works in one simulator "
          "only; GLS fails", "Flops without reset feeding control"],
         ["Blocking/non-blocking misuse", "Behaviour changes with code "
          "order or simulator", "`=` in clocked blocks (Chapter 4)"],
         ["Width truncation / sign", "Wrong results only for large or "
          "negative values", "Lint width warnings, `signed` mixing"],
         ["Inferred latch", "Holds stale value in some states",
          "Incomplete `if`/`case` in comb logic"],
         ["Handshake violations", "Duplicated or dropped beats under "
          "back-pressure", "valid depending on ready; data changing while "
          "stalled"],
         ["Pipeline hazard", "Wrong result when two operations are "
          "back-to-back", "Forwarding, stall/valid alignment"],
         ["FSM lock-up", "Hang after a rare sequence", "Missing transitions, "
          "unhandled simultaneous events"],
         ["CDC", "Rare, seed- or silicon-only failures", "Unsynchronized "
          "or re-converging crossings (Chapter 25)"],
         ["Endianness / bit order", "Bytes swapped at an interface",
          "Packing, `[0:7]` vs `[7:0]`"],
         ["Testbench race or model bug", "DUT looks right in the waves",
          "Sampling edge, reference model assumptions"]],
        widths=[25, 38, 37], bold_first=True)

    h2("X: optimism in RTL, pessimism in gates")
    p("Unknown values are the source of the most insidious gap between "
      "simulation and hardware. The experiment below leaves a select signal "
      "uninitialized - exactly what a flop without reset looks like at "
      "time zero - and evaluates the same multiplexer written four ways.")
    code([
        'module xprop_demo;',
        '  logic       sel;                 // never initialized: X, like a flop without reset',
        "  logic [3:0] a = 4'b1100, b = 4'b1010;",
        '  logic [3:0] y_if, y_case, y_tern, y_and;',
        '',
        '  always_comb if (sel) y_if = a; else y_if = b;     // if: X treated as FALSE',
        '  always_comb case (sel)                            // case: X matches no item',
        "                1'b1:    y_case = a;",
        '                default: y_case = b;',
        '              endcase',
        '  assign y_tern = sel ? a : b;                      // ?: merges a and b bitwise',
        '  assign y_and  = {4{sel}} & a | {4{~sel}} & b;     // what gates would compute',
        '',
        '  initial begin',
        '    #1 $display("sel=%b  if:%b  case:%b  ?::%b  gates:%b",',
        '                sel, y_if, y_case, y_tern, y_and);',
        "    sel = 1'b0;",
        '    #1 $display("sel=%b  if:%b  case:%b  ?::%b  gates:%b",',
        '                sel, y_if, y_case, y_tern, y_and);',
        '  end',
        'endmodule',
        ], "Four descriptions of one 2:1 multiplexer, "
         "evaluated with an X select.")
    out(["sel=x  if:1010  case:1010  ?::1xx0  gates:xxx0",
         "sel=0  if:1010  case:1010  ?::1010  gates:1010"])
    tbl(["Form", "Result with sel = X", "Behaviour"],
        [["`if (sel)`", "`1010` (= b)", "**X-optimism**: X treated as "
          "false; the uncertainty vanishes and a missing reset is hidden"],
         ["`case (sel)`", "`1010` (= b)", "X matches no item, so `default` "
          "is taken - also optimistic"],
         ["`sel ? a : b`", "`1xx0`", "LRM merge: bits where a and b agree "
          "are known, others X - the most accurate"],
         ["AND-OR gates", "`xxx0`", "**X-pessimism**: bit 3 is 1 in both "
          "inputs, so real hardware outputs 1, but gate evaluation gives X"],
         ["Real silicon", "a or b", "sel powers up as 0 or 1 - never X"]],
        widths=[18, 22, 60], bold_first=True)
    box("key", "Why this matters for sign-off",
        "RTL simulation can pass while silicon fails because an `if` "
        "swallowed an X from an unreset flop (optimism). Gate-level "
        "simulation can fail while silicon works because gate evaluation "
        "cannot resolve reconvergent X (pessimism). The cures are the "
        "X-propagation tools and reviews of Chapter 25, and resetting every "
        "flop whose value is used before it is written.")

    h2("Gate-level simulation")
    p("Gate-level simulation (GLS) runs the testbench on the synthesized "
      "or post-layout **netlist** instead of the RTL. Equivalence checking "
      "(Chapter 25) already proves the netlist's logic, and STA (Chapter 18) "
      "proves its timing, so GLS is run selectively for what they do not "
      "cover:")
    bul(["**Initialization and reset**: X-pessimism and unreset flops, "
         "reset sequencing through the real reset tree.",
         "**DFT structures**: scan chains, BIST controllers and test-mode "
         "muxing (pattern simulation of ATPG vectors).",
         "**Timing-dependent behaviour** STA does not model: asynchronous "
         "interfaces, multicycle and false-path exceptions that might be "
         "wrong (GLS with SDF will fail if an exception was not really "
         "safe), clock-gating and clock-switching glitches.",
         "**Power-aware** GLS with the UPF: isolation, retention and "
         "power-switch behaviour in the real netlist (Chapter 19).",
         "A **sanity check** that the netlist boots: a handful of tests, not "
         "the full regression - GLS is 10-100x slower than RTL."])
    p("In its simplest, **zero-delay** form, GLS just swaps the netlist in. "
      "The ALU netlist synthesized by Yosys in Chapter 25 (139 generic "
      "gates) runs unmodified with the Chapter 22 testbench:")
    out(["ALU: 1004 vectors, 0 errors -> PASS",
         "tb_alu_gate.sv:59: $finish called at 1004 (1s)"],
        "The Chapter 22 ALU testbench run on alu_gate.v (only the module name "
        "in the instantiation changed).")
    h3("Timing annotation with SDF")
    p("For timed GLS, every standard cell's simulation model has a "
      "`specify` block with path delays and timing checks, and the "
      "extraction/STA tool writes an **SDF** (Standard Delay Format) file "
      "with the actual delays of every cell and net instance in the "
      "layout. `$sdf_annotate` replaces the model's default delays with "
      "those values. The miniature example below - a toggle flop built from "
      "an inverter and a D flip-flop - runs in Icarus with `-gspecify`.")
    code([
        '`timescale 1ns/1ps',
        'module DFFQ_X1 (input CK, input D, output reg Q);',
        '  always @(posedge CK) Q <= D;',
        '  specify',
        '    (posedge CK => (Q +: D)) = (0.10, 0.12);   // clk-to-q rise, fall',
        '    $setup(D, posedge CK, 0.05);',
        '    $hold (posedge CK, D, 0.03);',
        '  endspecify',
        'endmodule',
        'module INV_X1 (input A, output ZN);',
        '  assign ZN = ~A;',
        '  specify',
        '    (A => ZN) = (0.02, 0.02);',
        '  endspecify',
        'endmodule',
        ], "cells.v - simplified library cell models with "
         "specify blocks.")
    code([
        '`timescale 1ns/1ps',
        'module toggle_net (input clk, output q);',
        '  wire d;',
        '  INV_X1  u_inv (.A(q), .ZN(d));',
        '  DFFQ_X1 u_ff  (.CK(clk), .D(d), .Q(q));',
        'endmodule',
        ], "net.v - the 'netlist'.")
    code([
        '(DELAYFILE',
        ' (SDFVERSION "3.0")',
        ' (DESIGN "toggle_net")',
        ' (TIMESCALE 1ns)',
        ' (CELL (CELLTYPE "INV_X1") (INSTANCE u_inv)',
        '   (DELAY (ABSOLUTE (IOPATH A ZN (0.35) (0.30)))))',
        ' (CELL (CELLTYPE "DFFQ_X1") (INSTANCE u_ff)',
        '   (DELAY (ABSOLUTE (IOPATH (posedge CK) Q (0.25) (0.28)))))',
        ')',
        ], "net.sdf - back-annotated delays (normally "
         "written by the STA tool).")
    code([
        '`timescale 1ns/1ps',
        'module tb;',
        '  reg clk = 0; wire q;',
        '  toggle_net dut (.clk(clk), .q(q));',
        '  always #5 clk = ~clk;',
        '  initial begin',
        '`ifdef SDF',
        '    $sdf_annotate("net.sdf", dut);',
        '`endif',
        '`ifdef INIT',
        "    force dut.u_ff.Q = 1'b0; #1 release dut.u_ff.Q;   // emulate a reset",
        '`endif',
        '    $monitor("%8.3f ns  clk=%b q=%b", $realtime, clk, q);',
        '    #22 $finish;',
        '  end',
        'endmodule',
        ], "tb.v - INIT emulates a reset; SDF enables "
         "annotation.")
    code(["$ iverilog -gspecify -DINIT -o g tb.v net.v cells.v && vvp g",
          "$ iverilog -gspecify -DINIT -DSDF -o g tb.v net.v cells.v && vvp g",
          "$ iverilog -gspecify -DSDF -o g tb.v net.v cells.v && vvp g"])
    out(["   5.000 ns  clk=1 q=0",
         "   5.100 ns  clk=1 q=1",
         "  10.000 ns  clk=0 q=1",
         "  15.000 ns  clk=1 q=1",
         "  15.120 ns  clk=1 q=0"],
        "Run 1 (excerpt): the library's default clock-to-Q delays, 100 ps "
        "rise and 120 ps fall.")
    out(["   5.000 ns  clk=1 q=0",
         "   5.250 ns  clk=1 q=1",
         "  10.000 ns  clk=0 q=1",
         "  15.000 ns  clk=1 q=1",
         "  15.280 ns  clk=1 q=0"],
        "Run 2 (excerpt): SDF-annotated delays of 250/280 ps from the layout.")
    out(["   0.000 ns  clk=0 q=x",
         "   5.000 ns  clk=1 q=x",
         "  10.000 ns  clk=0 q=x",
         "  15.000 ns  clk=1 q=x",
         "  20.000 ns  clk=0 q=x",
         "tb.v:14: $finish called at 22000 (1ps)"],
        "Run 3: no reset. The flop starts at X and the loop X -> NOT -> X "
        "never resolves. In silicon the flop would simply toggle from "
        "whatever value it powered up with.")
    p("Run 3 is the textbook GLS problem: RTL written as "
      "`always @(posedge clk) q <= ~q;` has the same X-lock in RTL "
      "simulation, but a slightly different RTL coding (an `if` on the "
      "value) would have hidden it by optimism and only GLS would show it. "
      "The right fix is a reset in the design, not a `force` in the "
      "testbench; for datapath flops that legitimately have no reset, "
      "simulators offer options to initialize them to random values.")
    tbl(["GLS issue", "Explanation and handling"],
        [["Timing-check violations", "`$setup`, `$hold`, `$width`, "
          "`$recovery` in cell models report violations and drive the flop "
          "output to X through a **notifier**. Real violations are bugs; "
          "violations on the first flop of a synchronizer are expected and "
          "are disabled for those instances only"],
         ["X-pessimism", "Reconvergent X through gates never resolves; "
          "requires resets or targeted initialization - never global "
          "'force everything to 0'"],
         ["Zero-delay races", "Without SDF, clock-tree buffers make the "
          "netlist race (data and clock change in the same time step); use "
          "unit-delay mode or SDF"],
         ["Corner selection", "Run SDF from min (hold) and max (setup) "
          "corners, as STA does"],
         ["Speed", "Run a small, targeted test list; save-and-restore after "
          "reset to skip initialization"]],
        widths=[22, 78], bold_first=True)
    box("warn", "PITFALL: GLS as a substitute for STA",
        "Timed GLS only checks the paths the test happens to exercise, with "
        "the vectors it happens to apply. STA checks every path. GLS "
        "complements STA by validating the **constraints** (a wrong false "
        "path shows up as a GLS failure) - it never replaces it.")

    h2("FPGA prototyping of ASIC RTL")
    p("An FPGA prototype maps the ASIC RTL onto one or more large FPGAs "
      "and runs it at 10-100 MHz - thousands of times faster than "
      "simulation - so that software teams can boot operating systems and "
      "run real workloads months before silicon, and so that the design "
      "can talk to real interfaces (Ethernet, USB, cameras). The RTL is the "
      "same, but ASIC-specific structures must be converted:")
    tbl(["ASIC construct", "FPGA conversion"],
        [["Gated clocks / ICG cells", "**Gated-clock conversion**: the "
          "prototyping synthesis tool (or a wrapper) turns clock gates into "
          "clock enables on the flops, keeping the design on a few global "
          "clocks; or map to `BUFGCE`-type global buffers"],
         ["PLLs, clock dividers", "FPGA MMCM/PLL primitives; generated "
          "clocks as enables where possible"],
         ["Memory-compiler SRAMs/ROMs", "Behavioural models inferring "
          "block RAM behind the same wrapper interface"],
         ["Standard-cell instances, pads, analog", "Behavioural models, "
          "FPGA I/O buffers, or external daughter cards for the analog"],
         ["Asynchronous resets everywhere", "Supported but costly; many "
          "teams convert to synchronous resets for the prototype"],
         ["Design too large for one FPGA", "**Partitioning** across FPGAs "
          "with **pin multiplexing** (TDM of many signals over one wire), "
          "which lowers the achievable clock"],
         ["DFT, power-management logic", "Tied off or removed "
          "(`ifdef FPGA`)"]],
        widths=[30, 70], bold_first=True)
    p("The key design-for-prototyping practice is to put every technology-"
      "specific element behind a **wrapper** with one RTL interface and two "
      "implementations selected at build time, so that neither the ASIC nor "
      "the prototype needs forked RTL.")
    code([
        'module sram_sp #(parameter int AW = 10, parameter int DW = 32) (',
        '  input  logic          clk, ce, we,',
        '  input  logic [AW-1:0] addr,',
        '  input  logic [DW-1:0] wdata,',
        '  output logic [DW-1:0] rdata',
        ');',
        '`ifdef ASIC',
        '  // Foundry memory-compiler macro (active-low enables, as most macros)',
        '  SRAM1RW1024X32 u_macro (.CLK(clk), .CEB(~ce), .WEB(~we),',
        '                          .A(addr), .D(wdata), .Q(rdata));',
        '`else',
        '  // FPGA and RTL simulation: behavioural model that infers block RAM.',
        '  // Same interface and 1-cycle read latency as the macro.',
        '  logic [DW-1:0] mem [2**AW];',
        '  always_ff @(posedge clk)',
        '    if (ce) begin',
        '      if (we) mem[addr] <= wdata;',
        '      rdata <= mem[addr];                 // read-before-write, like the macro',
        '    end',
        '`endif',
        'endmodule',
        ], "A single-port SRAM wrapper: foundry macro for "
         "the ASIC, inferred block RAM for FPGA and simulation.")
    code([
        'module clk_gate (',
        '  input  logic clk, en, test_en,',
        '  output logic gclk',
        ');',
        '`ifdef FPGA',
        '  // FPGA: gate with a global clock buffer (or convert to enables, see text)',
        '  BUFGCE u_bufgce (.I(clk), .CE(en | test_en), .O(gclk));',
        '`else',
        '  // ASIC: latch-based clock gate. In a real flow this is the library ICG cell.',
        '  logic en_lat;',
        '  always_latch',
        '    if (!clk) en_lat = en | test_en;      // transparent while clk is low',
        '  assign gclk = clk & en_lat;             // glitch-free: en only changes when clk=0',
        '`endif',
        'endmodule',
        ], "A clock-gate wrapper: latch-based ICG for the "
         "ASIC build, global clock buffer for the FPGA build.")
    p("The simulation branches of both wrappers were verified together "
      "(the testbench writes and reads back two SRAM locations and toggles "
      "the gate enable in the middle of a high clock phase, which must not "
      "produce a glitch):")
    out(["sram readback ok, gated clock pulses = 3 (expect 3)",
         "tb_wrap.sv:25: $finish called at 115 (1s)"])
    p("Multi-FPGA prototyping systems (Synopsys HAPS, Cadence Protium, S2C "
      "Prodigy, Siemens proFPGA) come with partitioning software, pin "
      "multiplexing IP and debug instrumentation. On-FPGA debug uses "
      "embedded logic analyzers - Xilinx ILA (ChipScope), Intel "
      "SignalTap - which capture a limited window of selected signals into "
      "on-chip RAM when a trigger fires; visibility is the prototype's "
      "main weakness.")

    h2("Hardware emulation")
    p("An **emulator** is a purpose-built machine that compiles the RTL "
      "(billions of gates) into a massively parallel hardware fabric and "
      "runs it at around 1 MHz, with **full visibility** of every signal "
      "and fast compile times compared with FPGA prototyping. Three "
      "architectures dominate:")
    tbl(["System", "Vendor", "Architecture"],
        [["Palladium", "Cadence", "Custom **processor-based**: thousands "
          "of Boolean processors evaluate the design; fast compile, high "
          "capacity"],
         ["Veloce", "Siemens", "Custom emulation chips (Veloce Strato), "
          "plus FPGA-based Primo for prototyping"],
         ["ZeBu", "Synopsys", "**FPGA-based** emulation with commercial "
          "FPGAs: higher speed, longer compile"]],
        widths=[16, 14, 70], bold_first=True)
    tbl(["", "RTL sim", "Emulation", "FPGA prototype", "Silicon"],
        [["Speed", "10 Hz - 1 kHz (SoC)", "~1 MHz", "10-100 MHz",
          "GHz"],
         ["Visibility", "Full", "Full (with trace depth limits)",
          "Very limited", "Minimal"],
         ["Capacity", "Unlimited, slow", "Billions of gates", "Needs "
          "partitioning", "-"],
         ["Turnaround after RTL change", "Minutes", "Hours", "Hours-days",
          "Months"],
         ["Typical use", "Block/SoC verification", "SoC verification, SW "
          "bring-up, power analysis", "SW development, real I/O",
          "Validation"]],
        widths=[20, 18, 22, 22, 18], bold_first=True)
    p("Emulators are used in two modes. In **in-circuit emulation (ICE)** "
      "the emulated design is cabled to real hardware through **speed "
      "bridges** that buffer traffic between the slow emulator and full-"
      "speed peripherals. In **transaction-based acceleration** the "
      "testbench stays on a workstation and talks to synthesizable "
      "transactors (BFMs) in the emulator through SCE-MI or DPI-style "
      "function calls - the whole UVM environment gets faster because only "
      "transactions, not every clock edge, cross the link. Designs must "
      "therefore keep synthesizable assertions and BFMs in mind.")

    h2("Hardware/software co-verification")
    p("A modern SoC is not correct until its firmware and drivers run on "
      "it. Co-verification starts long before silicon:")
    bul(["**Embedded C tests in RTL simulation**: the real CPU RTL executes "
         "a small C program compiled for the target and loaded into "
         "memory with `$readmemh`; the program writes pass/fail to a "
         "mailbox register the testbench monitors. This verifies "
         "integration, boot code, address maps and interrupts.",
         "**Virtual platforms**: instruction-accurate models (QEMU, SystemC "
         "TLM-2.0, Arm Fast Models) run the software stack at hundreds of "
         "MIPS before the RTL exists.",
         "**Hybrid emulation**: the CPU subsystem runs as a fast virtual "
         "model on the host while the new hardware runs in the emulator - "
         "Linux boots in minutes instead of days.",
         "**Portable Stimulus (Accellera PSS)**: one abstract scenario "
         "description generates UVM sequences for block level and C tests "
         "for SoC level, emulation and silicon."])

    h2("Post-silicon debug")
    p("When first silicon returns, visibility collapses to the pins. "
      "Everything that will be needed to debug it must have been designed "
      "in (Chapter 20):")
    tbl(["Feature", "What it provides"],
        [["JTAG (IEEE 1149.1) + debug access port", "Halt, step and "
          "inspect CPUs (Arm CoreSight DAP, RISC-V Debug Module); read and "
          "write memory and registers through the TAP"],
         ["On-chip trace", "Program-flow and data trace (Arm ETM/ETE, STM "
          "for software instrumentation) into an on-chip buffer (ETB/ETR) "
          "or off-chip through a trace port"],
         ["Embedded logic analyzers", "Trigger logic and trace RAM on "
          "selected internal buses, configured through JTAG"],
         ["Performance counters", "Count events (cache misses, stalls, bus "
          "retries) to debug performance, not just function"],
         ["Scan dump", "Stop the clocks and shift out every flop's state "
          "through the scan chains - a full snapshot of the chip"],
         ["Spare cells and metal ECO", "Unused gates scattered in the "
          "layout, so a fix can be made by changing only metal masks"],
         ["Shmoo plots", "Pass/fail across voltage and frequency to separate "
          "logic bugs from timing/power-integrity problems"]],
        widths=[30, 70], bold_first=True)
    box("expert", "The cost curve of a bug",
        "A bug found by the designer's own unit test costs minutes. In "
        "SoC regression it costs days of several people's time. In "
        "emulation or on the prototype, weeks. In silicon, a metal ECO "
        "costs months and a mask set; a full respin of an advanced-node "
        "chip costs tens of millions of dollars and a market window. Every "
        "technique in Part V exists to move bug discovery to the left of "
        "this curve.")

    h2("Summary")
    bul(["Debug systematically: reproduce, find the first symptom, trace "
         "backwards to the source, test a hypothesis, fix and generalize.",
         "Dump waves selectively (`$dumpvars`, `$dumpon/off`) and view them "
         "in GTKWave or a commercial debugger; lead with transaction logs.",
         "RTL simulation is X-optimistic (`if`, `case`), gate evaluation is "
         "X-pessimistic; silicon is neither - reset what you use.",
         "GLS checks initialization, DFT, SDF-timed asynchronous behaviour "
         "and constraints; it complements, never replaces, LEC and STA.",
         "FPGA prototypes need wrappers for memories, clock gating and "
         "technology cells; emulators trade speed for full visibility.",
         "Post-silicon debug relies on JTAG, trace, embedded analyzers, "
         "scan dump and spare cells designed in from the start."])
    h2("Exercises")
    bul(["Add a `+DUMP_START=<ns>` plusarg to `tb_vcd.sv` that starts "
         "dumping only at the given time, and verify the VCD begins there.",
         "Rewrite the X experiment with `unique case` and with `priority "
         "if`. Does your simulator warn when the selector is X?",
         "Add an active-low reset to the toggle flop cell model and rerun "
         "run 3 with a reset pulse instead of `force`. What changes in the "
         "SDF file if the reset-to-Q path has a delay?",
         "List everything in the FIFO of Chapter 22 that would need an "
         "FPGA wrapper or conversion if the FIFO were built with a "
         "foundry register-file macro and a clock-gated write port.",
         "Estimate how long a 10^{10}-cycle Linux boot takes in RTL "
         "simulation (100 Hz), emulation (1 MHz) and on a 50 MHz FPGA "
         "prototype."], ordered=True)
