"""Part IV (second half) - Chapters 22-24 of the Verilog & SystemVerilog guide.

Chapter 22  SystemVerilog Assertions (SVA) in depth
Chapter 23  Functional coverage
Chapter 24  DPI-C, VPI and co-simulation with C and Python

Every out() card was pasted from a real run in this environment:
  - Verilator 5.020 (--binary --timing --assert) for immediate assertions, the
    subset of concurrent SVA it supports (boolean |-> / |=>, $past, $rose,
    $stable, disable iff, bind) and the DPI-C example;
  - Icarus Verilog 12 for the VPI application;
  - cocotb 2.1.0 on top of Icarus Verilog 12 for the Python testbench.
Sequence operators, covergroups, $assertoff and friends are shown without
output: they need a commercial simulator (or a formal tool).
"""

from sv_guide.common import *  # noqa: F401,F403


def part4b():
    ch22()
    ch23()
    ch24()


# =============================================================================
#                 Chapter 22 - SystemVerilog Assertions in depth
# =============================================================================
def ch22():
    chapter("SystemVerilog Assertions (SVA) in Depth", newpage=True)
    p("An assertion is an executable statement of intent: a property the "
      "design must always satisfy, written in a form a simulator can check "
      "every cycle and a formal tool can try to prove for every possible "
      "input. SystemVerilog Assertions (SVA, IEEE 1800 clauses 16 and 17) "
      "are a small temporal language embedded in SystemVerilog. They are "
      "the single most productive verification feature of the language: "
      "a ten-line assertion bound into a block catches the bug at the cycle "
      "and the signal where it happens, instead of hundreds of cycles later "
      "as a scoreboard mismatch at the far end of the chip.")
    p("This chapter covers the language precisely: the two families of "
      "assertions and where they execute in the event scheduler (Chapter 5), "
      "sequences and their repetition operators, the sequence and property "
      "operators, implication and vacuity, sampled-value functions, reset "
      "handling, local variables, multi-clock properties, the four "
      "verification directives, and the packaging constructs (`bind`, "
      "`checker`) that let a DV engineer attach checks to RTL without "
      "touching it. It ends with a reusable library of SoC protocol "
      "assertions. Examples that the open-source tools can execute were run "
      "with Verilator 5.020; the rest are written to the IEEE 1800-2017 "
      "grammar and need a commercial simulator (VCS, Xcelium, Questa, "
      "Riviera-PRO) or a formal tool (JasperGold, VC Formal, Questa Formal, "
      "SymbiYosys with a commercial front end).")

    # ------------------------------------------------------------------
    h2("Two families: immediate and concurrent assertions")
    tbl(["Aspect", "Immediate assertion", "Concurrent assertion"],
        [["Syntax", "`assert (expr) [pass] [else fail];`",
          "`assert property (prop) [pass] [else fail];`"],
         ["Where", "Procedural code (and, for deferred forms, also as a "
          "module item)", "Module, interface, program, checker, or "
          "procedural code (clock then inferred)"],
         ["When evaluated", "When execution reaches it (simple) or at the "
          "end of the time step (deferred)", "On every tick of its clock"],
         ["Values used", "Current values", "Values **sampled** in the "
          "Preponed region"],
         ["Temporal?", "No - a single instant", "Yes - sequences span many "
          "clock ticks, many attempts overlap"],
         ["Formal tools", "Mostly ignored (some treat as an invariant)",
          "The native input of property checkers"],
         ["Typical use", "Checking function arguments, TB invariants, "
          "combinational sanity", "Protocol rules, latency, stability, "
          "FSM legality, data integrity"]],
        widths=[18, 41, 41], bold_first=True)
    p("Both families share the same verification directives: `assert` "
      "(the property must hold), `assume` (the property is a constraint on "
      "the environment), `cover` (tell me when this happens) and, for "
      "concurrent properties only, `restrict` (a formal-only constraint). "
      "Every assertion may carry a label (`a_req_ack:`), which becomes its "
      "hierarchical name in reports, waveform viewers and coverage "
      "databases - always label your assertions.")

    # ------------------------------------------------------------------
    h2("Immediate assertions: simple and deferred")
    h3("Simple immediate assertions")
    p("A **simple immediate assertion** is a procedural statement. When "
      "control reaches it, the expression is evaluated like the condition "
      "of an `if`: a value of 0, X or Z is a failure, any known non-zero "
      "value is a success. The optional pass statement runs on success; the "
      "statement after `else` runs on failure. With no `else`, a failure "
      "calls `$error` with a tool-specific message. The action statements "
      "may be any procedural statement, but in practice they are one of the "
      "four **severity tasks**: `$fatal(finish_number, fmt, ...)` "
      "(terminates the run; `finish_number` 0, 1 or 2 selects the "
      "statistics printed as for `$finish`), `$error` (run-time error, "
      "counted), `$warning` and `$info`. All four print the file, line, "
      "scope and time in a tool-specific format.")
    code(r"""module imm;
  logic [3:0] a, b;
  logic       sel;
  logic [3:0] y;
  assign y = sel ? a : b;

  // deferred immediate assertion: evaluated after the glitches settle
  always_comb a_def: assert #0 (y == (sel ? a : b)) else $error("mux mismatch");

  initial begin
    a = 4'd3; b = 4'd9; sel = 1'b0;
    #1;
    a_imm: assert (y == 4'd9) $info("y=%0d as expected", y);
           else $error("y=%0d", y);
    sel = 1'b1; #1;
    assert (y == 4'd9) else $warning("warning: y=%0d, sel=%b", y, sel);
    assert (!$isunknown(y)) else $fatal(1, "X on y");
    $display("done at %0t", $time);
    $finish;
  end
endmodule""", "imm.sv - simple and deferred immediate assertions with severity tasks. Built "
       "with `verilator --binary --timing --assert imm.sv`.")
    out(r"""[1] -Info: imm.sv:13: TOP.imm.a_imm: y=9 as expected
[2] %Warning: imm.sv:16: TOP.imm: warning: y=3, sel=1
done at 2
- imm.sv:19: Verilog $finish""", "Verilator 5.020 output. The labelled assertion "
        "reports its hierarchical name `TOP.imm.a_imm`; the unlabelled one only "
        "its scope.")
    box("warn", "PITFALL: assertions are silently off unless you enable them",
        "Verilator compiles assertions only with `--assert` (without it the "
        "run above prints nothing but `done at 2`). Commercial simulators "
        "enable them by default but offer switches to disable them "
        "(`-assert disable`, `-nosva`, `+nosva`...), and regressions have "
        "shipped for months with assertions off. Add a deliberately failing "
        "smoke assertion to a sanity test so the flow proves the checkers "
        "are alive. Icarus Verilog 12 accepts unlabelled simple immediate "
        "assertions (and prints `INFO:`/`WARNING:` lines for the same test) "
        "but rejects labels on them and the deferred forms `assert #0` and "
        "`assert final` with a syntax error.")
    h3("Deferred immediate assertions: #0 and final")
    p("A simple immediate assertion inside `always_comb` is fragile: a "
      "combinational process may execute several times in one time step "
      "while its inputs settle (a 0-delay glitch), and an intermediate "
      "evaluation can fail even though the final, settled value is correct. "
      "**Deferred** immediate assertions solve this. When a deferred "
      "assertion executes, its result is not reported at once: the failure "
      "(or pass) report is placed in a deferred queue for that process. If "
      "the process executes again in the same time step, the queue is "
      "**flushed** and the new evaluation replaces the old one. Only the "
      "evaluation that survives to the end matures and is reported.")
    tbl(["Form", "Since", "Report matures in", "Action block rules"],
        [["`assert #0 (e)` (observed deferred)", "1800-2009",
          "Observed region; the action runs in the Reactive region, so it "
          "sees values after the Active/NBA settling of this time slot",
          "A single subroutine call (e.g. `$error(...)`), arguments are "
          "evaluated when the assertion executes"],
         ["`assert final (e)` (final deferred)", "1800-2012",
          "Postponed region - after everything, including program/"
          "testbench reactions, has settled", "A single subroutine call; "
          "no time-consuming or state-changing actions are allowed "
          "(it runs in Postponed)"],
         ["`assert (e)` (simple)", "1800-2005",
          "Immediately, when executed", "Any statement"]],
        widths=[27, 11, 34, 28], bold_first=True)
    p("A deferred assertion may also be written directly as a module item, "
      "outside any procedural block; it then behaves as if it were inside "
      "its own `always_comb`. That makes `a_onehot: assert final "
      "($onehot0(grant));` a one-line combinational checker that is "
      "immune to delta-cycle glitches. In the SoC flow, deferred "
      "assertions are the right tool for combinational invariants in RTL "
      "(one-hot selects, mutually exclusive enables, legal encodings) that "
      "are not tied to any clock, e.g. inside an interconnect decoder.")
    box("expert", "Interview insight: why the action block is restricted",
        "Because a deferred report can be flushed, its action cannot be an "
        "arbitrary statement whose side effects might already have happened "
        "for an evaluation that is later cancelled. The LRM therefore allows "
        "only one subroutine call, whose arguments are captured when the "
        "assertion executes and which is called only when the report "
        "matures.")

    # ------------------------------------------------------------------
    h2("Concurrent assertions and the scheduler")
    p("A concurrent assertion describes behaviour over time relative to a "
      "**clock**. At every tick of that clock a new **attempt** starts; an "
      "attempt may take many ticks to complete, so many attempts are in "
      "flight at once. Three regions of the time slot (Chapter 5) matter:")
    diagram([
        "  one time slot of the clock edge                                     ",
        "  +-----------+  +--------+  +-----+  +----------+  +----------+  +----------+",
        "  | Preponed  |->| Active |->| NBA |->| Observed |->| Reactive |->| Postponed|",
        "  +-----------+  +--------+  +-----+  +----------+  +----------+  +----------+",
        "   sample all     RTL runs,   flops    evaluate      pass/fail      $strobe,",
        "   values used    clock edge  update   properties    action blocks  assert final",
        "   by properties  happens              (on samples)  (TB reacts)    reports",
    ], "Concurrent assertions use the values sampled in Preponed (the values just "
       "before the clock edge), evaluate in Observed and run their action blocks in "
       "Reactive.")
    p("Because of **sampling**, a concurrent assertion sees exactly what a "
      "flip-flop sees: the value a signal had just before the clock edge. "
      "This makes assertions race-free with respect to the RTL they check "
      "and consistent with formal tools, which reason on the same cycle-"
      "based model. The flip side is the most common beginner confusion: "
      "an assertion that fails 'one cycle late' in the waveform is usually "
      "correct - it reports at the edge where the sampled values violate "
      "the rule, and the failing values are the ones plotted just "
      "**before** that edge.")
    h3("Clocking a property")
    tbl(["How the clock is specified", "Example", "Notes"],
        [["Explicit clocking event", "`assert property (@(posedge clk) a |=> b);`",
          "Most portable; any event expression, e.g. `@(posedge clk iff en)`"],
         ["Inside a named property/sequence", "`property p; @(posedge clk) "
          "a |=> b; endproperty`", "The declaration carries its clock"],
         ["Default clocking", "`default clocking cb @(posedge clk); "
          "endclocking`", "Applies to all un-clocked assertions in the module, "
          "interface or checker (one default per scope)"],
         ["Inferred from a procedure", "`always @(posedge clk) if (en) assert "
          "property (a |=> b);`", "Procedural concurrent assertion: clock is "
          "inferred from the `always`, the enclosing `if` becomes an implicit "
          "antecedent condition"],
         ["Clocking block event", "`assert property (@(cb) ...)`",
          "Uses the event of a clocking block (Chapter 21)"]],
        widths=[25, 42, 33], bold_first=True)
    p("The example below uses the explicit form and the constructs that "
      "Verilator 5.020 executes: Boolean antecedents and consequents joined "
      "by `|->` or `|=>`, `disable iff`, `$past`, `$rose` and `$stable`. "
      "The stimulus deliberately breaks each rule once.")
    code(r"""module top;
  logic clk = 0, rst_n = 0;
  logic req = 0, ack = 0, valid = 0, ready = 0;
  logic [7:0] data = 0;
  always #5 clk = ~clk;

  // req must be answered by ack on the next cycle
  a_req_ack: assert property (@(posedge clk) disable iff (!rst_n) req |=> ack)
    else $error("req at %0t not acked", $time);

  // valid held until ready, data stable while stalled
  a_stable: assert property (@(posedge clk) disable iff (!rst_n)
                             valid && !ready |=> valid && $stable(data))
    else $error("stall rule broken at %0t", $time);

  // on a rising edge of ack, previous-cycle req must have been 1
  a_rose: assert property (@(posedge clk) $rose(ack) |-> $past(req))
    else $error("spurious ack at %0t", $time);

  c_hs: cover property (@(posedge clk) valid && ready);

  initial begin
    repeat (2) @(negedge clk); rst_n = 1;
    @(negedge clk) req = 1;
    @(negedge clk) begin req = 0; ack = 1; end
    @(negedge clk) ack = 0;
    @(negedge clk) req = 1;          // cycle: no ack follows -> failure
    @(negedge clk) req = 0;
    @(negedge clk) begin valid = 1; data = 8'hA5; end
    @(negedge clk) data = 8'h5A;     // changes while stalled -> failure
    @(negedge clk) ready = 1;
    @(negedge clk) begin valid = 0; ready = 0; end
    @(negedge clk) ack = 1;          // spurious ack
    @(negedge clk) ack = 0;
    #20 $finish;
  end
endmodule""", "top.sv - three concurrent assertions and a cover. Run: `verilator "
       "--binary --timing --assert top.sv && ./obj_dir/Vtop +verilator+error+limit+100`.")
    out(r"""[75] %Error: top.sv:9: Assertion failed in TOP.top.a_req_ack: req at 75 not acked
[95] %Error: top.sv:14: Assertion failed in TOP.top.a_stable: stall rule broken at 95
[125] %Error: top.sv:18: Assertion failed in TOP.top.a_rose: spurious ack at 125
- top.sv:35: Verilog $finish""", "Verilator 5.020 output (the '-Info: ... $stop "
        "ignored' line printed after each failure is omitted). Without "
        "`+verilator+error+limit` the first `$error` stops the run.")
    p("Read the times carefully. The clock rises at 5, 15, 25, ... The "
      "second `req` pulse is driven at 60 and sampled high at the edge at "
      "65; `|=>` requires `ack` at the **next** edge, 75, where the sampled "
      "`ack` is 0 - so the attempt that started at 65 fails at 75. The data "
      "is changed at 90 while `valid && !ready` was sampled at 85, so "
      "`$stable(data)` is false at 95. The spurious `ack` is driven at 120: "
      "at 125 `$rose(ack)` is true but `$past(req)` (the value sampled at "
      "115) is 0. Note also that `c_hs` produced no text: `cover` directives "
      "are counted into the coverage database, not printed.")

    # ------------------------------------------------------------------
    h2("Sequences: delays and repetition")
    p("A **sequence** is a pattern of Boolean expressions over consecutive "
      "clock ticks. A sequence **matches** over an interval of ticks "
      "(possibly several different intervals: a sequence can have multiple "
      "matches from one start point). The building blocks are cycle delays "
      "and repetition operators.")
    tbl(["Operator", "Meaning", "Example and match"],
        [["`a ##1 b`", "b one tick after a", "a@t, b@t+1"],
         ["`a ##0 b`", "Fusion: b at the same tick as the end of a",
          "a and b both @t"],
         ["`a ##n b`", "b exactly n ticks after a (n constant >= 0)",
          "`req ##2 gnt`: gnt@t+2"],
         ["`a ##[m:n] b`", "b between m and n ticks after a; one match per "
          "tick where b holds", "`req ##[1:3] gnt`"],
         ["`a ##[m:$] b`", "Unbounded upper limit: b at some tick >= m later",
          "Weak by default in assertions (see strong/weak)"],
         ["`##[*]` / `##[+]`", "Shorthand for `##[0:$]` / `##[1:$]`",
          "`start ##[+] done`"],
         ["`b[*n]`", "Consecutive repetition: b on n consecutive ticks",
          "`busy[*3]` = busy ##1 busy ##1 busy"],
         ["`b[*m:n]`, `b[*]`, `b[+]`", "Consecutive, m to n times; `[*]` = "
          "`[*0:$]`; `[+]` = `[*1:$]`", "`[*0]` is the empty sequence"],
         ["`b[->n]`", "Goto repetition: n (not necessarily consecutive) "
          "occurrences of b; the match **ends at** the n-th b",
          "`a ##1 b[->2] ##1 c`: c right after 2nd b"],
         ["`b[=n]`", "Non-consecutive repetition: n occurrences of b; the "
          "match may **extend past** the n-th b over ticks where b is false",
          "`a ##1 b[=2] ##1 c`: c any time after 2nd b, with no 3rd b "
          "before it"]],
        widths=[20, 45, 35])
    diagram([
        "tick:        1   2   3   4   5   6   7",
        "b:           1   0   1   0   0   1   0",
        "",
        "b[*2]        no match starting at 1 (b is 0 at tick 2)",
        "b[->2]       from tick 1: matches exactly [1..3]    (ends ON the 2nd b)",
        "b[=2]        from tick 1: matches [1..3], [1..4] and [1..5]",
        "             (may continue while b stays 0; stops before the 3rd b at 6)",
        "",
        "a ##1 b[->2] ##1 c  : c must be true at the tick right after the 2nd b",
        "a ##1 b[=2]  ##1 c  : c may come later, but before a 3rd b occurs",
    ], "Goto versus non-consecutive repetition on the same waveform, starting at "
       "tick 1.")
    p("Precisely: `b[->n]` is defined as `(!b[*0:$] ##1 b)[*n]` - each "
      "occurrence is preceded by any number of ticks with `b` false and "
      "ends on a tick with `b` true. `b[=n]` is `b[->n] ##1 !b[*0:$]`, "
      "i.e. goto repetition followed by any number of ticks without `b`. "
      "Delay and repetition bounds must be elaboration-time constants "
      "(parameters, literals, `$`); you cannot write `##[1:max_lat]` with "
      "a variable. When a latency is programmable, check it with a local "
      "variable counter (shown later) or generate one assertion per legal "
      "value.")
    box("tip", "Named sequences are reusable, parameterised building blocks",
        "`sequence s_hs(v, r); v ##0 r; endsequence` declares a sequence "
        "with formal arguments; arguments may be untyped (substituted "
        "textually, so they can be expressions, events or other sequences) "
        "or typed. Named sequences can be instantiated inside other "
        "sequences and properties, and expose the methods `s.triggered` "
        "(the sequence reached its end point in the current time step; "
        "usable in procedural code and in `wait (s.triggered)`) and "
        "`s.matched` (for synchronising across clock domains).")

    # ------------------------------------------------------------------
    h2("Sequence operators")
    tbl(["Operator", "Semantics (both operands are sequences unless noted)"],
        [["`s1 and s2`", "Both start at the same tick and both match; they "
          "may end at different ticks, and the composite match ends when "
          "the later one ends"],
         ["`s1 intersect s2`", "Like `and`, but both must match over the "
          "**same interval** (same start and same end tick). Used to bound "
          "length: `s intersect (1'b1[*1:8])` = s completes within 8 ticks"],
         ["`s1 or s2`", "At least one of them matches; the composite has the "
          "union of their matches"],
         ["`s1 within s2`", "s1 matches somewhere inside the interval of a "
          "match of s2 (s1 starts no earlier and ends no later than s2)"],
         ["`e throughout s`", "Boolean `e` is true on **every** tick of the "
          "match of s. `e` must be an expression, not a sequence"],
         ["`first_match(s)`", "Keeps only the earliest-ending match(es) of s; "
          "discards later matches from the same start tick"],
         ["`s1 ##n s2`", "Concatenation (see delays)"],
         ["`e[*n]`, `[->]`, `[=]`", "Repetition; `[->]`/`[=]` operate on "
          "Boolean expressions only, `[*]` works on sequences too"]],
        widths=[20, 80])
    code(r"""// A burst of exactly 4 data beats while 'grant' stays high the whole time
sequence s_burst;
  start ##1 (grant throughout (beat[->4]));
endsequence

// The response must arrive 1..15 cycles after the request (intersect bounds the length)
property p_resp_bound;
  @(posedge clk) req |-> (##[1:$] resp) intersect (1'b1[*1:16]);
endproperty

// Only the FIRST ack after a request counts as its completion
property p_first_ack;
  @(posedge clk) first_match(req ##[1:8] ack) |=> idle;
endproperty

// An error pulse must never be seen inside a transfer
property p_no_err_in_xfer;
  @(posedge clk) not (err[->1] within (sof ##1 !eof[*0:$] ##1 eof));
endproperty""", "Sequence operators in typical DV properties (IEEE 1800-2017; needs "
       "a simulator with full SVA support - Verilator 5.020 rejects `##` delays "
       "and repetition operators as unsupported).")
    box("warn", "PITFALL: unbounded ranges in an antecedent without first_match",
        "`a ##[1:$] b |-> c` starts a separate check for **every** match of "
        "the antecedent, i.e. for every later tick where `b` is true, and "
        "the attempt never finishes while `b` can still occur. That costs "
        "simulation performance and gives surprising multiple failures. "
        "Write `first_match(a ##[1:$] b) |-> c` when you mean the first "
        "occurrence, or bound the range.")

    # ------------------------------------------------------------------
    h2("Implication and vacuity")
    p("Most properties are **implications**: `antecedent |-> consequent`. "
      "The antecedent is a sequence; for each of its matches, the "
      "consequent property must hold. With `|->` (**overlapping**) the "
      "consequent starts at the tick where the antecedent match ends; with "
      "`|=>` (**non-overlapping**) it starts one tick later, i.e. "
      "`s |=> p` is exactly `s ##1 1'b1 |-> p`.")
    p("If the antecedent has no match, the implication is **vacuously "
      "true**: nothing was required, so nothing failed. Vacuity is "
      "essential (a `req |-> ##1 ack` property must not fail on cycles "
      "without `req`) but also dangerous: an assertion whose antecedent "
      "never occurs in any test passes forever and proves nothing. Tools "
      "report vacuous and non-vacuous passes separately; always pair "
      "important assertions with a `cover property` on the antecedent (or "
      "on the whole sequence) and check the cover is hit in regression.")
    tbl(["Result of an attempt", "Meaning"],
        [["Non-vacuous pass", "Antecedent matched and the consequent held"],
         ["Vacuous pass", "Antecedent never matched - no obligation arose"],
         ["Failure", "Antecedent matched and the consequent was violated"],
         ["Disabled", "`disable iff` became true during the attempt - "
          "neither pass nor fail"],
         ["Incomplete / unfinished", "Simulation ended before the attempt "
          "finished: a failure for a **strong** property, not a failure for "
          "a **weak** one"]],
        widths=[28, 72], bold_first=True)
    box("key", "Weak and strong",
        "A property is **weak** if it only requires that no bad thing is "
        "seen within the observed trace, and **strong** if it also requires "
        "the good thing to actually happen before the trace ends. "
        "`req |-> ##[1:$] ack` is weak by default: if simulation ends while "
        "waiting for `ack`, no failure is reported. Write `req |-> "
        "strong(##[1:$] ack)` or `req |-> s_eventually ack` to require the "
        "`ack`. A sequence used as a property is weak in `assert`/`assume` "
        "and strong in `cover` unless wrapped in `strong()`/`weak()`. In "
        "formal verification strong properties are liveness properties, "
        "which need fairness assumptions and different proof engines.")

    # ------------------------------------------------------------------
    h2("Property operators")
    tbl(["Operator", "Meaning"],
        [["`not p`", "p does not hold (swaps weak/strong: `not` of a weak "
          "property is strong)"],
         ["`p1 and p2`, `p1 or p2`", "Property-level conjunction/disjunction"],
         ["`p1 implies p2`, `p1 iff p2`", "Property-level logic (1800-2009)"],
         ["`if (e) p1 else p2`", "Choose the property to check from a "
          "Boolean at the start tick; `case` is also allowed"],
         ["`nexttime p`, `nexttime [n] p`", "p holds at the next (n-th next) "
          "tick; weak - passes if there is no next tick"],
         ["`s_nexttime p`", "Strong: the next tick must exist"],
         ["`always p`, `always [m:n] p`", "p holds at every tick (in the "
          "range). Weak form; the range may be unbounded"],
         ["`s_always [m:n] p`", "Strong, bounded range only"],
         ["`s_eventually p`, `s_eventually [m:$] p`", "p holds at some tick "
          "(strong: must actually happen)"],
         ["`eventually [m:n] p`", "Weak form, bounded range required"],
         ["`p until q`", "p holds on every tick until (not including) the "
          "tick where q holds; weak - q need never occur"],
         ["`p s_until q`", "Strong: q must eventually hold"],
         ["`p until_with q`, `s_until_with`", "p holds up to **and "
          "including** the tick where q holds"],
         ["`s #-# p`, `s #=# p`", "Followed-by: the dual of implication; "
          "requires a match of s (no vacuous success)"],
         ["`accept_on (e) p`, `reject_on (e) p`", "Abort: e true -> the "
          "attempt passes / fails immediately (sync_ variants sample e)"]],
        widths=[35, 65])
    code(r"""// Once 'lock' is taken it is held until 'unlock', inclusive of that cycle
a_lock:  assert property (@(posedge clk) $rose(lock) |-> lock until_with unlock);

// Grant must eventually follow request (liveness - strong)
a_live:  assert property (@(posedge clk) req |-> s_eventually gnt);

// Mode-dependent latency
a_mode:  assert property (@(posedge clk)
           start |-> if (fast) ##1 done else ##4 done);

// After reset release, 'ready' rises within 8 cycles and then stays high forever
// (#-# is 'followed-by': the sequence must match, then the property must hold)
a_boot:  assert property (@(posedge clk) $rose(rst_n) |->
           first_match(##[0:8] ready) #-# always ready);""",
         "Property operators (IEEE 1800-2017, commercial simulator or formal tool).")

    # ------------------------------------------------------------------
    h2("Sampled-value functions")
    p("Sampled-value functions let a Boolean expression refer to the history "
      "of a signal. They use the **sampled** value at each tick of the "
      "clock of the property that contains them (or the explicit clock "
      "argument), so they are safe to use in assertions and also callable "
      "from procedural code with an explicit clock.")
    tbl(["Function", "Returns true / value", "Notes"],
        [["`$sampled(e)`", "The sampled value of e", "Implicit inside "
          "assertions; useful in action blocks to print what was checked"],
         ["`$rose(e)`", "LSB of e changed to 1 since the previous tick",
          "Only the LSB: `$rose(bus)` for a vector is a common bug; X->1 "
          "counts as a rise"],
         ["`$fell(e)`", "LSB changed to 0", ""],
         ["`$stable(e)`", "Whole value unchanged since the previous tick",
          "Compares all bits (with `===`-like 4-state comparison)"],
         ["`$changed(e)`", "`!$stable(e)`", "1800-2009"],
         ["`$past(e, n, gate, clk)`", "Value of e n ticks ago (n default 1)",
          "With `gate`, counts only ticks where gate was true"],
         ["`$rose_gclk`, `$future_gclk`...", "Global-clocking variants",
          "Used mainly in formal, relative to `global clocking`"]],
        widths=[24, 38, 38])
    p("At the first tick there is no history; `$past` then returns the "
      "value the expression would have had before the first sample (the "
      "declaration initial value, typically X for 4-state variables), and "
      "`$rose`/`$fell`/`$stable` compare against that. Guard assertions "
      "that use `$past` with the reset (`disable iff`) or with a "
      "`past_valid` flag so the first cycles after reset do not report "
      "garbage. The gating argument is how you express 'the value when the "
      "pipeline last advanced': `$past(din, 1, en)` is the value of `din` at "
      "the previous tick where `en` was high - exactly what an enable-gated "
      "register holds, so `q == $past(din, 1, en)` is a one-line reference "
      "model of such a register.")

    # ------------------------------------------------------------------
    h2("disable iff and reset")
    p("`disable iff (cond)` is the asynchronous abort of a property. "
      "Unlike every other expression in a concurrent assertion, `cond` is "
      "evaluated on **current**, not sampled, values: as soon as it becomes "
      "true, every in-flight attempt is **disabled** (reported as neither "
      "pass nor fail) and no new attempt produces a result while it stays "
      "true. It may appear only once, at the top of a property (not in "
      "sequences, not nested). A scope-wide default is available:")
    code(r"""module axi_checks (input logic aclk, aresetn /* ... */);
  default clocking cb @(posedge aclk); endclocking
  default disable iff (!aresetn);          // applies to every assertion below

  a_awvalid_hold: assert property (awvalid && !awready |=> awvalid);
  a_override:     assert property (disable iff (1'b0) !aresetn |-> !awvalid);
endmodule""", "Default clocking and default disable iff (1800-2009). An explicit "
       "`disable iff` in a property overrides the default. Verilator 5.020 "
       "reports 'Unsupported: default disable iff'.")
    box("warn", "PITFALL: checking reset behaviour with a reset-disabled property",
        "A property such as `!aresetn |-> !awvalid` (AXI: VALID must be low "
        "during reset) can never fail if it inherits `disable iff "
        "(!aresetn)`; it is disabled exactly when it matters. Override with "
        "`disable iff (1'b0)`, as `a_override` does. Conversely, a "
        "`$past`-based property evaluated just after reset release may read "
        "pre-reset X values: disable it one extra cycle, or AND the "
        "antecedent with `$past(aresetn)`.")

    # ------------------------------------------------------------------
    h2("Local variables")
    p("A sequence or property can declare **local variables** that capture "
      "a value at one point of a match and compare it later. They are "
      "assigned by a comma-separated list after a sub-sequence in "
      "parentheses: `(expr, v = data, n = n + 1)`. Each attempt (indeed "
      "each thread of each attempt) has its own copy, so overlapping "
      "transactions do not interfere. This is how SVA checks data "
      "integrity through a pipeline without writing a scoreboard.")
    code(r"""// The value entering a 3-stage pipeline must appear at the output 3 cycles later
property p_pipe_data;
  logic [31:0] v;
  @(posedge clk) disable iff (!rst_n)
    (in_valid, v = in_data) |-> ##3 (out_valid && out_data == v);
endproperty
a_pipe: assert property (p_pipe_data);

// Programmable latency: count cycles with a local variable (bounds need not be constants)
property p_prog_lat;
  int cnt;
  @(posedge clk) (start, cnt = cfg_lat) |->
    (cnt > 0, cnt = cnt - 1)[*0:$] ##1 (cnt == 0 && done);
endproperty

// Tag matching for out-of-order responses (ID-based)
property p_id_resp;
  logic [3:0] id;
  @(posedge clk) (arvalid && arready, id = arid) |->
    ##[1:64] (rvalid && rready && rlast && rid == id);
endproperty""", "Local variables in properties (IEEE 1800-2017; Verilator 5.020 fails "
       "to parse a local variable declaration in a property).")
    p("Rules worth knowing: local variables cannot be referenced in `disable "
      "iff` or in action blocks directly (copy to a module variable via a "
      "subroutine call in a match item, e.g. `(a, v = d, log(v))`); a local "
      "variable assigned in one branch of `or` is not visible after the "
      "`or` unless it is assigned in both branches; and they may be passed "
      "as arguments to named sequences declared with `local input` or "
      "`local inout` formals.")

    # ------------------------------------------------------------------
    h2("Multi-clock sequences and properties")
    p("A sequence can change clocks at a concatenation or implication. The "
      "boundary uses `##1` (the next tick of the new clock **strictly after** "
      "the previous match ends) or `##0` (the new clock tick that coincides "
      "with, or follows, the end point); other delay values are not allowed "
      "across a clock change.")
    code(r"""// A pulse captured in the fast domain must be seen in the slow domain
a_cdc_pulse: assert property (
  @(posedge clk_fast) $rose(evt_fast) |=> @(posedge clk_slow) ##[0:2] evt_slow);

// Multiply-clocked sequence: request in domain A, ack in domain B
sequence s_req_ack_x;
  @(posedge clk_a) req ##1 @(posedge clk_b) ack;
endsequence""", "Multi-clock properties (commercial simulators and formal tools).")
    p("Multi-clock assertions are used on CDC boundaries, but they check the "
      "protocol only - they cannot detect metastability. Structural CDC "
      "checking (synchroniser recognition, reconvergence) is the job of a "
      "CDC tool; the companion RTL Design guide treats CDC design itself.")

    # ------------------------------------------------------------------
    h2("assert, assume, cover, restrict and action blocks")
    tbl(["Directive", "In simulation", "In formal"],
        [["`assert property (p)`", "Checked; failures run the else-action "
          "(default `$error`)", "Proof target: prove it holds for all legal "
          "inputs, or produce a counter-example trace"],
         ["`assume property (p)`", "Checked like an assertion (reports "
          "environment violations)", "Constraint: only input traces that "
          "satisfy p are explored"],
         ["`cover property (p)` / `cover sequence (s)`", "Counts matches "
          "(the pass action runs on each); reported in coverage", "Reachability: "
          "find a trace that reaches p, or prove it unreachable"],
         ["`restrict property (p)`", "Ignored", "Constraint like assume, but "
          "never checked in simulation; no action block allowed"]],
        widths=[27, 36, 37], bold_first=True)
    p("The action block syntax is `assert property (p) pass_stmt; else "
      "fail_stmt;` - the pass statement is rarely used because it runs on "
      "every successful attempt, including vacuous ones on some tools. The "
      "fail statement typically calls a severity task with a message "
      "built from `$sampled()` values. Because the action runs in the "
      "Reactive region, it may also increment a testbench error counter, "
      "trigger an event, or call a function that dumps extra state. "
      "Assume/assert duality is the backbone of **assume-guarantee** "
      "reasoning in formal: the same property file is used as `assume` "
      "when verifying the consumer and as `assert` when verifying the "
      "producer, usually selected by a macro or a parameter.")
    box("tip", "Severity policy in a real flow",
        "Protocol violations by the DUT: `$error` (counted, the test fails "
        "at the end, other checks still run). Environment/assumption "
        "violations: `$fatal` (the stimulus is illegal, nothing after it can "
        "be trusted). Informational covers: no message at all. UVM flows "
        "often route the else-branch through the `uvm_error` macro so assertion "
        "failures appear in the same report summary and obey the same "
        "verbosity/severity overrides as the rest of the testbench.")

    # ------------------------------------------------------------------
    h2("bind, checkers and assertion control")
    h3("bind: attaching assertions without touching the RTL")
    p("`bind` instantiates a module, interface, program or checker "
      "**inside** another module as if the instantiation had been written "
      "in its body. The target can be a module name (every instance), "
      "specific instances (`bind fifo:u_rx_fifo,u_tx_fifo ...`) or a "
      "hierarchical instance path. Port connections are resolved in the "
      "scope of the target, so the checker can see internal signals such "
      "as a FIFO's `count`. This is how DV teams keep assertion IP in "
      "their own files, compile it only in verification builds, and never "
      "risk changing the RTL that goes to synthesis.")
    code(r"""// A 4-entry FIFO with a deliberate bug: 'full' is computed one entry too late.
module fifo #(parameter int DEPTH = 4, parameter int W = 8) (
  input  logic         clk, rst_n,
  input  logic         push, pop,
  input  logic [W-1:0] din,
  output logic [W-1:0] dout,
  output logic         full, empty
);
  logic [W-1:0] mem [DEPTH];
  logic [2:0]   count;
  logic [1:0]   wp, rp;
  assign full  = (count > DEPTH);          // BUG: should be (count == DEPTH)
  assign empty = (count == 0);
  assign dout  = mem[rp];
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin count <= '0; wp <= '0; rp <= '0; end
    else begin
      if (push && !full) begin mem[wp] <= din; wp <= wp + 1'b1; end
      if (pop && !empty) rp <= rp + 1'b1;
      count <= count + 3'(push && !full) - 3'(pop && !empty);
    end
endmodule""", "fifo.sv - the design under test (RTL, owned by the designer).")
    code(r"""// Protocol checker: written by DV, attached with 'bind' - the RTL is untouched.
module fifo_sva #(parameter int DEPTH = 4) (
  input logic clk, rst_n, push, pop, full, empty,
  input logic [2:0] count
);
  default clocking cb @(posedge clk); endclocking

  a_no_overflow:  assert property (disable iff (!rst_n) count <= DEPTH)
    else $error("overflow: count=%0d", count);
  a_full_flag:    assert property (disable iff (!rst_n) full == (count == DEPTH))
    else $error("full=%b count=%0d", full, count);
  a_not_both:     assert property (disable iff (!rst_n) !(full && empty));
  a_empty_stable: assert property (disable iff (!rst_n) empty && !push |=> empty);
  c_full:         cover  property (disable iff (!rst_n) full);
endmodule

bind fifo fifo_sva #(.DEPTH(DEPTH)) chk (.*);""",
         "sva.sv - the checker and the bind statement. `.*` connects each checker "
         "port to the signal of the same name inside `fifo`, including the internal "
         "`count`; `DEPTH` is resolved in the target's scope.")
    code(r"""module tb;
  logic clk = 0, rst_n = 0, push = 0, pop = 0;
  logic [7:0] din = 0, dout;
  logic full, empty;
  always #5 clk = ~clk;
  fifo dut (.*);
  initial begin
    repeat (2) @(negedge clk); rst_n = 1;
    push = 1;
    repeat (6) @(negedge clk) din++;
    push = 0;
    @(negedge clk) $finish;
  end
endmodule""", "tb.sv - pushes six words into the 4-entry FIFO. Run: `verilator "
       "--binary --timing --assert --top-module tb tb.sv fifo.sv sva.sv`.")
    out(r"""[65] %Error: sva.sv:11: Assertion failed in TOP.tb.dut.chk.a_full_flag: full=0 count=4
[75] %Error: sva.sv:9: Assertion failed in TOP.tb.dut.chk.a_no_overflow: overflow: count=5
[75] %Error: sva.sv:11: Assertion failed in TOP.tb.dut.chk.a_full_flag: full=1 count=5
[85] %Error: sva.sv:9: Assertion failed in TOP.tb.dut.chk.a_no_overflow: overflow: count=5
[85] %Error: sva.sv:11: Assertion failed in TOP.tb.dut.chk.a_full_flag: full=1 count=5
- tb.sv:12: Verilog $finish""", "Verilator 5.020 (with +verilator+error+limit+100; "
        "the '-Info' lines are omitted). The checker instance appears as "
        "`TOP.tb.dut.chk` - inside the DUT, although the DUT source never "
        "mentions it.")
    p("The first failure pinpoints the bug exactly: at the edge at 65 the "
      "FIFO holds four entries and `full` is still 0, so the fifth push is "
      "accepted and the FIFO overflows at 75 (overwriting entry 0 because "
      "the 2-bit write pointer wrapped). An end-to-end scoreboard would "
      "only have seen a missing word much later, after a pop.")
    h3("The checker construct")
    p("A `checker` (1800-2009) is a container designed for assertion IP. "
      "Compared with a module it can be instantiated **inside procedural "
      "code** (the enclosing `always` supplies the clock and enable), its "
      "formal arguments may be sequences, properties or untyped "
      "expressions, it can infer the clock and reset of its context with "
      "`$inferred_clock` and `$inferred_disable`, and it may declare `rand` "
      "**free variables** that formal tools treat as unconstrained inputs "
      "(useful for abstract models such as 'pick any address and track "
      "it').")
    code(r"""checker c_valid_ready (logic valid, logic ready, logic [63:0] payload,
                       event clk = $inferred_clock,
                       untyped rst = $inferred_disable);
  default clocking @clk; endclocking
  default disable iff (rst);
  a_hold:   assert property (valid && !ready |=> valid);
  a_stable: assert property (valid && !ready |=> $stable(payload));
  c_stall:  cover  property (valid && !ready ##1 valid && ready);
endchecker

module producer (input logic clk, rst, /* ... */);
  default clocking @(posedge clk); endclocking
  default disable iff (rst);
  // clock and reset inferred from the defaults above
  c_valid_ready u_chk (m_valid, m_ready, m_data);
endmodule""", "A reusable handshake checker (IEEE 1800-2017; checkers are not "
       "supported by Icarus or Verilator 5.020).")
    h3("Assertion control system tasks")
    tbl(["Task", "Effect"],
        [["`$assertoff(levels, scope_or_assertion, ...)`", "Stop checking: "
          "new attempts are not started; in-flight attempts continue"],
         ["`$assertkill(...)`", "Like `$assertoff`, and also abort all "
          "attempts currently in flight"],
         ["`$asserton(...)`", "Resume checking"],
         ["`$assertpassoff/on`, `$assertfailoff/on`, `$assertvacuousoff`",
          "Enable/disable the pass or fail action blocks, or vacuous-pass "
          "actions (1800-2009)"],
         ["`$assertcontrol(control_type, assertion_type, directive_type, "
          "levels, list)`", "The general form (1800-2012) of all of the above; "
          "can target only asserts, only covers, only concurrent, etc."]],
        widths=[45, 55])
    p("`levels` works like `$dumpvars`: 0 means the named scope and "
      "everything below it, n means n levels. A typical use is "
      "`initial begin $assertoff(0, tb.dut); @(posedge init_done); "
      "$asserton(0, tb.dut); end` to silence checks during a "
      "power-on/initialisation phase, or turning off a known-broken check "
      "for one test while a bug is fixed. Neither Icarus nor Verilator "
      "5.020 implement these tasks (Verilator: 'Unsupported or unknown PLI "
      "call: $assertoff').")

    # ------------------------------------------------------------------
    h2("A library of SoC protocol assertions")
    p("The same dozen rule shapes appear on every SoC interface. The block "
      "below is written to IEEE 1800-2017 and is typical of what DV teams "
      "keep in an assertion package bound onto every instance of an "
      "interface. Rule numbers refer to the AMBA AXI specification (ARM "
      "IHI 0022), whose handshake rules apply equally to AXI-Stream and "
      "most valid/ready interfaces.")
    code(r"""module axi_hs_sva #(parameter int W = 64) (
  input logic aclk, aresetn,
  input logic valid, ready, last,
  input logic [W-1:0] payload
);
  default clocking cb @(posedge aclk); endclocking
  default disable iff (!aresetn);

  // AXI A3.2.1: once VALID is asserted it stays asserted until the handshake
  a_valid_hold:   assert property (valid && !ready |=> valid);
  // Payload (and LAST) must not change while waiting for READY
  a_payload_stbl: assert property (valid && !ready |=> $stable({payload, last}));
  // No X on control; no X on payload while VALID
  a_valid_known:  assert property (!$isunknown(valid));
  a_pl_known:     assert property (valid |-> !$isunknown(payload));
  // A3.1.2: VALID low during reset (reset-disabled default must be overridden)
  a_reset_valid:  assert property (disable iff (1'b0) !aresetn |-> !valid);
  // Coverage of the interesting handshake shapes
  c_back2back:    cover property (valid && ready ##1 valid && ready);
  c_stall3:       cover property ((valid && !ready)[*3] ##1 ready);
endmodule

module soc_misc_sva (input logic clk, rst_n, req, ack, push, pop, full, empty,
                     input logic [7:0] gnt, input logic [2:0] fsm);
  default clocking cb @(posedge clk); endclocking
  default disable iff (!rst_n);
  a_gnt_onehot:  assert property ($onehot0(gnt));               // arbiter grant
  a_req_ack_lat: assert property (req |-> ##[1:4] ack);         // bounded latency
  a_ack_has_req: assert property (ack |-> $past(req) || $past(req, 2) ||
                                  $past(req, 3) || $past(req, 4));
  a_req_held:    assert property (req && !ack |=> req);         // 4-phase handshake
  a_no_ovf:      assert property (full  |-> !push || pop);
  a_no_unf:      assert property (empty |-> !pop);
  a_fsm_legal:   assert property (fsm inside {3'd0, 3'd1, 3'd2, 3'd4});
  a_fsm_nodead:  assert property (fsm == 3'd4 |-> s_eventually fsm == 3'd0);
endmodule""", "A small SoC assertion library (IEEE 1800-2017; commercial simulator "
       "or formal tool).")
    p("When only an open-source simulator is available, many of these rules "
      "can be rewritten in the subset Verilator 5.020 executes: a fixed "
      "delay `req |-> ##2 ack` becomes `$past(req, 2) |-> ack`, and pure "
      "invariants need no temporal operator at all. The run below also "
      "illustrates an important limitation of 2-state simulation.")
    code(r"""module top;
  logic clk = 0, rst_n = 0, req = 0, ack = 0;
  logic [3:0] gnt = '0;
  always #5 clk = ~clk;

  // Portable form of "req |-> ##2 ack" for tools without sequence support:
  a_lat2:   assert property (@(posedge clk) disable iff (!rst_n) $past(req, 2) |-> ack)
    else $error("ack missing 2 cycles after req");
  a_onehot: assert property (@(posedge clk) disable iff (!rst_n) $onehot0(gnt))
    else $error("gnt=%b not one-hot-0", gnt);
  a_known:  assert property (@(posedge clk) disable iff (!rst_n) !$isunknown(gnt))
    else $error("gnt has X/Z: %b", gnt);

  initial begin
    repeat (3) @(negedge clk); rst_n = 1;
    req = 1; @(negedge clk) req = 0;
    @(negedge clk) ack = 1; @(negedge clk) ack = 0;          // latency 2: pass
    req = 1; @(negedge clk) req = 0;
    @(negedge clk); @(negedge clk) ack = 1;                  // latency 3: fail
    @(negedge clk) begin ack = 0; gnt = 4'b0110; end         // two grants
    @(negedge clk) gnt = 4'b00x0;                            // X on the bus
    @(negedge clk) gnt = 4'b0000;
    @(negedge clk) $finish;
  end
endmodule""", "Portable forms of latency and one-hot checks (run with Verilator 5.020).")
    out(r"""[85] %Error: top.sv:8: Assertion failed in TOP.top.a_lat2: ack missing 2 cycles after req
[105] %Error: top.sv:10: Assertion failed in TOP.top.a_onehot: gnt=0110 not one-hot-0
- top.sv:23: Verilog $finish""", "Verilator 5.020 output ('-Info' lines "
        "omitted). The X injected on `gnt` at 110 is NOT reported.")
    box("warn", "PITFALL: X-checks are meaningless in a 2-state simulator",
        "Verilator is a 2-state simulator: the assignment `gnt = 4'b00x0` "
        "stores 0 in place of X, so `a_known` can never fail. A 4-state "
        "simulator reports it at the edge at 115. X-propagation checks, "
        "reset-value checks and `$isunknown` assertions must run on a "
        "4-state simulator (or on formal tools with X modelling). Also note "
        "that `$past(req,2) |-> ack` is equivalent to `req |-> ##2 ack` "
        "only away from reset: the `$past` form reads values from inside "
        "the reset window during the first two cycles after release.")

    # ------------------------------------------------------------------
    h2("Tool support at a glance")
    p("The following matrix was established by compiling one-line "
      "properties with Verilator 5.020 (`--lint-only --assert --timing`) "
      "and Icarus Verilog 12 in this environment. Commercial simulators and "
      "formal tools support the full clause 16 language.")
    tbl(["Construct", "Verilator 5.020", "Icarus 12"],
        [["Simple immediate `assert` + severity tasks", "Yes (`--assert`)",
          "Yes, unlabelled only"],
         ["`assert #0`, `assert final`", "Yes", "No (syntax error)"],
         ["Boolean `|->`, `|=>`, `not`, `disable iff`", "Yes", "No"],
         ["`$past(e,n)`, `$rose`, `$fell`, `$stable`, `$changed`", "Yes",
          "No"],
         ["`$past` with gating/clock arguments", "No", "No"],
         ["`##n`, `##[m:n]`, `[*n]`, `[->n]`, `[=n]`", "No", "No"],
         ["Sequence `and`/`or`/`intersect`/`within`/`throughout`/"
          "`first_match`", "No", "No"],
         ["`always`, `s_eventually`, `until`, `nexttime`, `if`/`else`",
          "No", "No"],
         ["Local variables in properties", "No", "No"],
         ["`default disable iff`", "No", "No"],
         ["`bind` of a module with assertions", "Yes", "No concurrent SVA"],
         ["`$assertoff/on/kill`", "No", "No"]],
        widths=[52, 24, 24], bold_first=True)

    # ------------------------------------------------------------------
    h2("Summary")
    bul(["Immediate assertions check a Boolean when executed; deferred forms "
         "(`#0`, `final`) report only the settled result of a time step and "
         "are the right choice in combinational code.",
         "Concurrent assertions sample in Preponed, evaluate in Observed and "
         "act in Reactive; they see what a flop sees, and a new attempt "
         "starts on every clock tick.",
         "Sequences combine delays (`##n`, `##[m:n]`) and repetitions "
         "(`[*n]` consecutive, `[->n]` goto ending on the last hit, `[=n]` "
         "non-consecutive that may extend past it) with `and`, `or`, "
         "`intersect`, `within`, `throughout` and `first_match`.",
         "`|->` checks the consequent at the antecedent's end tick, `|=>` one "
         "tick later; a missing antecedent is a vacuous pass - pair "
         "assertions with covers.",
         "Weak properties may remain unfinished at the end of simulation; "
         "strong ones (`s_eventually`, `strong()`, `s_until`) may not.",
         "`disable iff` uses current values and disables (does not pass) an "
         "attempt; local variables carry data through a pipeline check.",
         "`bind` and `checker` package assertion IP without editing RTL; "
         "`$assertoff/$asserton/$assertkill/$assertcontrol` control it at "
         "run time.",
         "Verilator 5.020 runs only Boolean implication with sampled-value "
         "functions; it is 2-state, so X checks need a 4-state simulator."])

    h2("Exercises")
    bul(["For the waveform b = 1,0,1,0,0,1,0 (ticks 1-7) list every match "
         "of `b[*1:2]`, `b[->2]` and `b[=2]` starting at tick 1. Which "
         "matches does `first_match(b[=2])` keep?",
         "Write a property that says 'after `start`, `busy` stays high until "
         "and including the cycle where `done` rises, and `done` must "
         "come within 20 cycles'. State which parts are weak and which "
         "strong.",
         "Explain why `assert property (@(posedge clk) disable iff (!rst_n) "
         "!rst_n |-> !valid);` can never fail, and fix it.",
         "Rewrite `a_req_ack` from the first concurrent example so that a "
         "request must be acknowledged within 1 to 3 cycles, once using "
         "`##[1:3]` and once using only constructs Verilator 5.020 accepts "
         "(hint: `$past` with several depths). Where do the two forms "
         "differ?",
         "Write a checker with a local variable that verifies a "
         "store-and-forward buffer: every word pushed with ID n must pop "
         "with the same data, in order, within 32 cycles. Add a cover for "
         "a full buffer.",
         "Your regression reports 0 failures and 100% passes for "
         "`a_axi_rlast`. What additional data do you need before trusting "
         "that result?"], ordered=True)


# =============================================================================
#                 Chapter 23 - Functional coverage
# =============================================================================
def ch23():
    chapter("Functional Coverage", newpage=True)
    p("Constrained-random stimulus (Chapter 19) answers the question 'how do "
      "I generate a million interesting tests?'; assertions and scoreboards "
      "(Chapter 22) answer 'did anything go wrong?'. Neither answers the "
      "question every verification sign-off review asks: **what did we "
      "actually test?** A random test that passes has proved nothing about "
      "the corner cases it never reached. Functional coverage is the "
      "language feature that measures this. The engineer writes down, as "
      "executable code, the list of scenarios that must be exercised - "
      "the **coverage model** - and the simulator counts how often each "
      "one occurred across the whole regression.")
    p("This chapter covers the `covergroup` language of IEEE 1800 clause 19 "
      "in detail: declaration and sampling, coverpoints and every kind of "
      "bin, transitions, crosses, options, the coverage calculation and the "
      "query API, covergroups in classes, and how coverage drives closure "
      "in a real SoC project. None of the open-source tools used in this "
      "book executes covergroups (Verilator 5.020 reports 'Unsupported: "
      "covergroup'; Icarus Verilog 12 reports a syntax error), so the "
      "examples here carry no simulator output. Instead, each one is "
      "followed by the result the LRM rules require, worked out by hand "
      "and labelled as such; any commercial simulator (VCS, Xcelium, "
      "Questa, Riviera-PRO) will report the same numbers.")

    # ------------------------------------------------------------------
    h2("Code coverage versus functional coverage")
    tbl(["", "Code coverage", "Functional coverage"],
        [["Source", "Generated automatically by the simulator from the RTL",
          "Written by the verification engineer from the specification"],
         ["Metrics", "Line/statement, branch, condition/expression, toggle, "
          "FSM state and arc", "Covergroup bins and crosses, `cover property`"
          " / `cover sequence` hits"],
         ["Answers", "Which parts of the **implementation** were executed?",
          "Which **features and scenarios** of the spec were exercised?"],
         ["Blind spot", "Cannot see missing functionality: code that was "
          "never written has 100% coverage", "Only as good as the plan: "
          "scenarios nobody thought of are never measured"],
         ["Cost", "Free (a compile switch); some simulation slowdown",
          "Engineering effort to write and review the model"],
         ["Typical sign-off target", "Line ~100%, branch/condition 95-100% "
          "with reviewed exclusions, toggle on ports", "100% of the "
          "verification plan items, with reviewed waivers"]],
        widths=[16, 42, 42], bold_first=True)
    p("The two are complementary and both are required at sign-off. High "
      "code coverage with low functional coverage means the stimulus runs "
      "the code but not the scenarios (for example every FIFO line executed "
      "but never 'full while a flush arrives'). High functional coverage "
      "with low code coverage means the coverage model is incomplete, or "
      "there is dead or unreachable RTL that should be removed or waived.")

    # ------------------------------------------------------------------
    h2("Declaring and sampling a covergroup")
    p("A `covergroup` is a user-defined **type**, like a class: the "
      "declaration describes the coverage model, and each `new` creates an "
      "**instance** that counts independently. A covergroup can be declared "
      "in a module, interface, program, package, or class (Section 23.9). "
      "It contains coverpoints, crosses and options, and it specifies how it "
      "is sampled:")
    tbl(["Sampling style", "Syntax", "When to use"],
        [["Clocking event", "`covergroup cg @(posedge clk);`",
          "Signal-level coverage in a module or interface; sampled "
          "automatically every event"],
         ["Block event", "`covergroup cg @@(begin mon.write);`",
          "Sample when a named task/function begins or ends execution"],
         ["Explicit `sample()`", "`covergroup cg; ... endgroup` then "
          "`cg_inst.sample();`", "Transaction-level coverage from a monitor "
          "or scoreboard: sample exactly once per transaction"],
         ["`sample()` with arguments", "`covergroup cg with function "
          "sample(bit [3:0] len, bit wr);`", "1800-2009: pass the values to "
          "cover, so the group need not reference any variable"],
         ["Constructor arguments", "`covergroup cg (ref logic [7:0] v, input "
          "int max) @(posedge clk);`", "Reusable groups: `ref` arguments are "
          "read at every sample, `input` arguments once at `new`"]],
        widths=[20, 44, 36], bold_first=True)
    code(r"""module bus_cov (input logic clk, rst_n, valid, ready, input logic [1:0] kind,
                input logic [3:0] len);
  // Signal-level: sampled on every clock edge, guarded by iff
  covergroup cg_hs @(posedge clk);
    cp_kind: coverpoint kind iff (rst_n && valid && ready);
    cp_stall: coverpoint (valid && !ready) iff (rst_n);
  endgroup
  cg_hs u_cg_hs = new();                  // must be instantiated to count anything

  // Transaction-level: the monitor calls sample() with the values
  covergroup cg_txn with function sample(bit [3:0] len, bit wr);
    cp_len: coverpoint len;
    cp_wr:  coverpoint wr;
  endgroup
  cg_txn u_cg_txn = new();
  always @(posedge clk) if (rst_n && valid && ready) u_cg_txn.sample(len, kind[0]);
endmodule""", "Two ways of sampling. `iff (expr)` on a coverpoint (or on a cross) "
       "disables sampling of that point when the guard is false.")
    box("warn", "PITFALL: sampling races and the forgotten new()",
        "A covergroup sampled by `@(posedge clk)` reads the **current** "
        "values when the event fires, in the Active region - it is not "
        "Preponed-sampled like an assertion. If the same edge also updates "
        "the covered flops, the result depends on process ordering. Sample "
        "through a clocking block, on the opposite edge, or with `sample()` "
        "from a monitor that has already captured the transaction. And a "
        "covergroup that is declared but never constructed with `new` "
        "silently contributes nothing - the report still lists the type, "
        "with 0 instances.")

    # ------------------------------------------------------------------
    h2("Coverpoints and bins")
    p("A **coverpoint** names an integral expression to cover (a variable, "
      "a part-select, or any expression, e.g. `coverpoint a + b`). Its "
      "values are counted into **bins**. A bin is **covered** when its hit "
      "count reaches `option.at_least` (default 1), and the coverpoint's "
      "coverage is the percentage of its bins that are covered.")
    h3("Automatic bins")
    p("With no bin specification the tool creates automatic bins. For an "
      "enum expression, one bin per named value. Otherwise, let N be the "
      "number of possible values (2^{n} for an n-bit expression): if N <= "
      "`option.auto_bin_max` (default 64) there is one bin per value, named "
      "`auto[0]`, `auto[1]`, ...; if N is larger, the value range is split "
      "into `auto_bin_max` bins of equal size (the last one absorbing any "
      "remainder), named like `auto[0:3]`. Values containing X or Z are not "
      "counted in any bin. Automatic bins are fine for a 1-bit flag or a "
      "small enum; for a 32-bit address they are useless (64 bins of 64M "
      "addresses each), so real coverage models declare explicit bins.")
    h3("Explicit bins")
    code(r"""covergroup cg_len with function sample(bit [3:0] len, bit wr);
  cp_len: coverpoint len {
    bins zero     = {0};            // one bin for one value
    bins lo[]     = {[1:3]};        // array: one bin per value -> lo[1], lo[2], lo[3]
    bins mid[2]   = {[4:9]};        // fixed count: values split into 2 bins
    bins hi       = {[10:14]};      // one bin for a range
    illegal_bins bad = {15};        // length 15 is reserved in this protocol
  }
  cp_wr: coverpoint wr;             // automatic bins auto[0], auto[1]
  x_len_wr: cross cp_len, cp_wr;
endgroup""", "A coverage model with explicit bins (IEEE 1800-2017; commercial "
       "simulator). Note: the bin names `small`, `medium` and `large` are "
       "illegal - they are Verilog charge-strength keywords.")
    tbl(["Bin form", "Bins created", "Rule"],
        [["`bins zero = {0};`", "1", "All listed values count into one bin"],
         ["`bins lo[] = {[1:3]};`", "3: lo[1], lo[2], lo[3]", "`[]` creates "
          "one bin per value in the set"],
         ["`bins mid[2] = {[4:9]};`", "2: mid[0] = {4,5,6}, mid[1] = {7,8,9}",
          "Values distributed evenly in order; if not divisible, the **last** "
          "bin gets the remainder (e.g. `[3] = {[0:10]}` gives {0,1,2}, "
          "{3,4,5}, {6..10})"],
         ["`bins hi = {[10:14]};`", "1", "Ranges `[lo:hi]`; `$` means the "
          "maximum value, e.g. `{[8:$]}`"],
         ["`bins others = default;`", "1 (not counted in coverage)",
          "Catches every value not in any other bin; excluded from the "
          "coverage percentage and from crosses"],
         ["`ignore_bins`", "0", "Values removed from all other bins; never "
          "counted"],
         ["`illegal_bins`", "0", "Values removed from all bins; sampling one "
          "is a run-time **error**; takes precedence over all other bins"]],
        widths=[27, 30, 43])
    p("Value sets may mix values and ranges, `{0, [2:5], 7, [12:$]}`, and "
      "since 1800-2009 may be given by an expression with a `with` filter, "
      "e.g. `bins even[] = {[0:15]} with (item % 2 == 0);`. A value may "
      "appear in several bins; it then counts in each of them.")
    h3("ignore_bins, illegal_bins and wildcard bins")
    code(r"""covergroup cg_op @(posedge clk iff valid);
  cp_opcode: coverpoint opcode {             // 8-bit opcode
    wildcard bins alu    = {8'b0000_????};   // ? (or x, z) = don't care in wildcard bins
    wildcard bins load   = {8'b0100_0???};
    wildcard bins store  = {8'b0100_1???};
    ignore_bins   dbg    = {8'hF0, 8'hF1};   // debug opcodes: not a DV goal
    illegal_bins  undef  = {[8'hF8:8'hFF]};  // decoding error if ever seen
    bins          misc   = default;          // everything else, reported but not scored
  }
endgroup""", "Wildcard, ignore and illegal bins (commercial simulator).")
    box("tip", "illegal_bins versus assertions",
        "An illegal bin is a convenient way to flag a value that must never "
        "occur, but it only fires when the covergroup is sampled, coverage "
        "is enabled and the group is instantiated. For a hard design rule, "
        "write an assertion too; many teams forbid illegal_bins entirely "
        "because coverage collection is sometimes switched off in "
        "regression for speed, which silently disables the check.")

    # ------------------------------------------------------------------
    h2("Transition bins")
    p("Transition bins count sequences of **successive sampled values** of "
      "one coverpoint. They are the covergroup counterpart of an SVA "
      "sequence, and are mostly used for FSM arcs and protocol orderings.")
    tbl(["Syntax", "Meaning"],
        [["`(IDLE => BUSY)`", "Value IDLE at one sample, BUSY at the next"],
         ["`(IDLE => BUSY => DONE)`", "Three successive samples"],
         ["`(1, 5 => 6, 7)`", "Set of transitions: 1=>6, 1=>7, 5=>6, 5=>7 "
          "(one bin unless declared with `[]`, then four bins)"],
         ["`(BUSY [*3])`", "Consecutive repetition: BUSY=>BUSY=>BUSY"],
         ["`(BUSY [*2:4])`", "BUSY repeated 2 to 4 consecutive samples"],
         ["`(ERR [-> 2])`", "Goto: ... => ERR => ... => ERR, any other values "
          "in between, ending on the second ERR"],
         ["`(ERR [= 2])`", "Non-consecutive: as goto, but may continue with "
          "non-ERR values after the second ERR"],
         ["`bins others = default sequence;`", "Catches transitions not "
          "matched by any other transition bin (not scored)"]],
        widths=[33, 67])
    code(r"""typedef enum logic [1:0] {IDLE, BUSY, WAIT, DONE} st_e;
covergroup cg_fsm @(posedge clk iff rst_n);
  cp_st: coverpoint state {
    bins states[]      = {IDLE, BUSY, WAIT, DONE};
    bins arcs[]        = (IDLE => BUSY), (BUSY => WAIT), (WAIT => BUSY),
                         (BUSY => DONE), (DONE => IDLE);
    bins long_wait     = (WAIT [*4:8]);          // stalled 4..8 samples
    bins retry_twice   = (BUSY => WAIT => BUSY => WAIT => BUSY);
    illegal_bins jump  = (IDLE => DONE);         // must pass through BUSY
  }
endgroup""", "FSM state and arc coverage with transition bins (commercial "
       "simulator).")
    p("**Expected result (by the LRM rules, not a simulation).** For the "
      "sampled sequence IDLE, BUSY, WAIT, WAIT, BUSY, DONE, IDLE: the four "
      "`states[]` bins are all hit; the arcs `arcs[IDLE=>BUSY]`, "
      "`arcs[BUSY=>WAIT]`, `arcs[WAIT=>BUSY]`, `arcs[BUSY=>DONE]` and "
      "`arcs[DONE=>IDLE]` are each hit once (5 of 5); `long_wait` is not "
      "hit (only 2 consecutive WAIT samples); `retry_twice` is not hit. "
      "cp_st therefore has 4 + 5 + 1 + 1 = 11 bins of which 9 are covered: "
      "9/11 = 81.82%. Note that transitions are measured between **samples**, "
      "not clock cycles: if the group is sampled only when `valid` is high, "
      "a repeated value may hide cycles where the state changed and changed "
      "back.")

    # ------------------------------------------------------------------
    h2("Cross coverage")
    p("A `cross` counts **combinations** of the bins of two or more "
      "coverpoints (or of variables, for which implicit coverpoints with "
      "automatic bins are created). By default it has one bin for every "
      "combination of the crossed coverpoints' bins, excluding their "
      "ignore, illegal and default bins. Crosses are where coverage models "
      "explode: three coverpoints with 16, 8 and 10 bins make 1280 cross "
      "bins, most of which may be meaningless. User-defined cross bins, "
      "built with `binsof` and `intersect`, select, merge or exclude "
      "combinations.")
    tbl(["Select expression", "Selects the cross products whose ..."],
        [["`binsof(cp_len)`", "cp_len component is any bin of cp_len"],
         ["`binsof(cp_len.hi)`", "cp_len component is the bin `hi`"],
         ["`binsof(cp_len) intersect {[0:3]}`", "cp_len bin contains at least "
          "one value in 0..3"],
         ["`!binsof(cp_len) intersect {0}`", "cp_len bin does not contain 0"],
         ["`binsof(a.x) && binsof(b.y)`", "Both conditions (AND of selections)"],
         ["`binsof(a.x) || binsof(b.y)`", "Either condition (union)"],
         ["`with (expr)`, `matches`", "1800-2012 filters on the crossed values"]],
        widths=[40, 60])
    code(r"""covergroup cg_len2 with function sample(bit [3:0] len, bit wr);
  cp_len: coverpoint len {
    bins zero = {0};  bins lo[] = {[1:3]};  bins mid[2] = {[4:9]};  bins hi = {[10:14]};
    illegal_bins bad = {15};
  }
  cp_wr: coverpoint wr;
  x_len_wr: cross cp_len, cp_wr {
    // long writes are not supported by this slave: not a coverage goal
    ignore_bins no_long_wr = binsof(cp_len.hi) && binsof(cp_wr) intersect {1};
    // all short reads count as one scenario
    bins short_rd = binsof(cp_len.lo) && binsof(cp_wr) intersect {0};
  }
endgroup""", "User-defined cross bins (commercial simulator).")
    p("**Expected bin count (by the LRM rules).** cp_len has 1 + 3 + 2 + 1 = "
      "7 bins and cp_wr 2, so the plain cross has 14 products. The ignore "
      "bin removes (hi, 1). The user bin `short_rd` absorbs the three "
      "products (lo[1..3], 0); automatically generated cross bins exclude "
      "any product already in a user-defined bin, so those three disappear "
      "as separate bins and one bin `short_rd` appears. Total: 14 - 1 - 3 + "
      "1 = **11** cross bins.")

    # ------------------------------------------------------------------
    h2("A worked example of the coverage calculation")
    p("Take `cg_len` from Section 23.3 (without the user-defined cross bins: "
      "7 cp_len bins, 2 cp_wr bins, 14 cross bins, all weights 1) and call "
      "`sample()` five times with (len, wr) = (0,1), (2,0), (2,1), (5,1), "
      "(12,0).")
    tbl(["Item", "Bins hit", "Coverage (expected, per LRM)"],
        [["cp_len", "zero, lo[2], mid[0] (5 is in {4,5,6}), hi", "4/7 = 57.14%"],
         ["cp_wr", "auto[0], auto[1]", "2/2 = 100.00%"],
         ["x_len_wr", "(zero,1), (lo[2],0), (lo[2],1), (mid[0],1), (hi,0)",
          "5/14 = 35.71%"],
         ["Instance (weighted average)", "(57.14 + 100 + 35.71) / 3",
          "**64.29%**"]],
        widths=[22, 48, 30], bold_first=True)
    p("A sixth call `sample(15, 0)` hits `illegal_bins bad`: the simulator "
      "reports a run-time error naming the bin, and the sample is not "
      "counted in cp_len or in the cross. The group coverage formula is the "
      "weighted average of its coverpoints and crosses, sum(w_{i} x C_{i}) / "
      "sum(w_{i}), where each C_{i} is the percentage of bins whose hit count "
      "reached `at_least`. Setting `option.weight = 0` on a coverpoint keeps "
      "it in the report but removes it from the group score - a common idiom "
      "for coverpoints that exist only to be crossed.")
    box("key", "Coverage is a percentage of bins, not of hits",
        "Hitting one bin a million times and another zero times gives 50%. "
        "That is why bin design is the real work: each bin should be one "
        "scenario a reviewer agrees must be seen. Too-coarse bins "
        "(automatic bins on wide buses) give meaningless 100% scores; "
        "too-fine crosses give coverage models that never close.")

    # ------------------------------------------------------------------
    h2("Options and type options")
    p("`option` members are **per instance** (set in the declaration, "
      "which applies to every instance, or procedurally on one instance: "
      "`u_cg.option.at_least = 4;`). `type_option` members are **static**, "
      "shared by all instances of the type, and set in the declaration or "
      "with `cg_len::type_option.goal = 90;`. Most can also be specified "
      "on an individual coverpoint or cross.")
    tbl(["Option", "Default", "Meaning"],
        [["`option.name`", "tool-generated", "Instance name in reports "
          "(also `set_inst_name()`)"],
         ["`option.comment`", "\"\"", "Text shown in reports; link to the "
          "verification-plan item"],
         ["`option.at_least`", "1", "Hits needed for a bin to count as covered"],
         ["`option.weight`", "1", "Weight of this instance (or coverpoint/"
          "cross) in the enclosing average"],
         ["`option.goal`", "100", "Target percentage"],
         ["`option.auto_bin_max`", "64", "Maximum number of automatic bins "
          "per coverpoint"],
         ["`option.cross_num_print_missing`", "0", "How many missing cross "
          "bins to list in reports"],
         ["`option.detect_overlap`", "0", "Warn if two bins of a coverpoint "
          "overlap"],
         ["`option.per_instance`", "0", "1: also keep and report per-instance "
          "coverage data (otherwise only type-level data is required)"],
         ["`option.get_inst_coverage`", "0", "1: `get_inst_coverage()` "
          "returns instance data when merge_instances is 1"],
         ["`type_option.weight`", "1", "Weight of the type in the overall "
          "coverage"],
         ["`type_option.goal`", "100", "Target for the type"],
         ["`type_option.comment`", "\"\"", "Comment for the type"],
         ["`type_option.strobe`", "0", "1: sample in the Postponed region "
          "(once per time step, like `$strobe`)"],
         ["`type_option.merge_instances`", "0", "0: type coverage is the "
          "average of instance coverages; 1: bins of all instances are "
          "merged before computing"]],
        widths=[33, 15, 52])
    box("warn", "PITFALL: per_instance and the meaning of 'type coverage'",
        "With default options a covergroup type instantiated in 8 ports "
        "reports one number for the type. If port 3 never saw a long burst "
        "but port 5 did, merged coverage can show the bin covered while "
        "port 3's logic was never exercised. Set `option.per_instance = 1` "
        "(and meaningful `option.name`s) when each instance is a distinct "
        "piece of hardware.")

    # ------------------------------------------------------------------
    h2("Querying and controlling coverage")
    tbl(["Method / function", "Returns / does"],
        [["`cg_inst.sample()`", "Sample now (with arguments if declared "
          "`with function sample`)"],
         ["`cg_inst.get_inst_coverage()`", "Real 0-100: coverage of this "
          "instance"],
         ["`cg_type::get_coverage()` or `cg_inst.get_coverage()`", "Real "
          "0-100: coverage of the type (all instances)"],
         ["`get_coverage(covered, total)`", "Optional `ref int` arguments "
          "receive the number of covered and total bins"],
         ["`cg_inst.cp_len.get_coverage()`", "Coverage of one coverpoint "
          "(or cross)"],
         ["`cg_inst.start()` / `stop()`", "Enable / disable collection for "
          "this instance"],
         ["`cg_inst.set_inst_name(\"rx0\")`", "Name the instance"],
         ["`$get_coverage()`", "Overall coverage of all covergroup types"],
         ["`$set_coverage_db_name(\"f\")`, `$load_coverage_db(\"f\")`",
          "Name / preload the coverage database"]],
        widths=[45, 55])
    code(r"""// Stop the test as soon as the coverage goal is reached (coverage-driven test length)
initial begin
  forever begin
    repeat (1000) @(posedge clk);
    if (u_cg_txn.get_inst_coverage() >= 95.0) begin
      $display("coverage goal reached: %0.2f%%", u_cg_txn.get_inst_coverage());
      $finish;
    end
  end
end""", "Using the query API to end a random test when it stops being "
       "productive (commercial simulator).")

    # ------------------------------------------------------------------
    h2("Covergroups in classes")
    p("In a class-based testbench, coverage lives in monitors, scoreboards "
      "or dedicated coverage collectors. A covergroup declared inside a "
      "class is an **embedded covergroup**: its name is simultaneously the "
      "type and the single instance variable, it can reference the class "
      "properties (including `local` and `protected` ones), and it must be "
      "constructed in the class constructor - the embedded covergroup "
      "variable may only be assigned in `new`. Each class object therefore "
      "owns exactly one instance.")
    code(r"""class axi_txn;
  rand bit [3:0]  len;
  rand bit [1:0]  burst;       // FIXED=0, INCR=1, WRAP=2
  rand bit        write;
endclass

class axi_cov;
  axi_txn t;                   // the transaction being sampled

  covergroup cg_axi;
    option.per_instance = 1;
    cp_len:   coverpoint t.len   { bins one = {0};       bins short_b[] = {[1:3]};
                                   bins mid = {[4:6]};   bins len8 = {7};
                                   bins long_b = {[8:14]}; bins len16 = {15}; }
    cp_burst: coverpoint t.burst { bins fixed = {0}; bins incr = {1}; bins wrap = {2};
                                   illegal_bins rsvd = {3}; }
    cp_dir:   coverpoint t.write;
    // WRAP bursts must have length 2, 4, 8 or 16 beats (len = 1, 3, 7, 15)
    x_burst_len: cross cp_burst, cp_len {
      ignore_bins wrap_bad = binsof(cp_burst.wrap) &&
                             binsof(cp_len) intersect {0, 2, [4:6], [8:14]};
    }
  endgroup

  function new(string name);
    cg_axi = new();            // mandatory, and only allowed here
    cg_axi.set_inst_name(name);
  endfunction

  function void write(axi_txn tr);   // called by the monitor for each transaction
    t = tr;
    cg_axi.sample();
  endfunction
endclass""", "An embedded covergroup in a coverage collector class (commercial "
       "simulator). In UVM this class would extend `uvm_subscriber` and "
       "`write()` would be its analysis-port callback (Chapter 26).")
    p("Notice why `cp_len` has separate bins `len8` and `len16`: "
      "`binsof(cp_len) intersect {...}` selects every **whole bin** that "
      "contains at least one of the listed values. Had `mid` been `{[4:7]}`, "
      "the ignore expression would have thrown away the legal 8-beat WRAP "
      "burst together with the illegal ones. Cross bins can only be as fine "
      "as the coverpoint bins they are built from.")
    p("Two design choices here are standard practice. Coverage samples "
      "**monitored** transactions (what the DUT actually saw), never the "
      "generated ones: a randomized transaction that a driver failed to "
      "send, or that the DUT rejected, must not count. And legality "
      "constraints of the protocol (reserved burst type, legal WRAP "
      "lengths) are mirrored as illegal or ignore bins so that the cross "
      "does not contain holes that can never close.")

    # ------------------------------------------------------------------
    h2("cover property versus covergroup")
    tbl(["", "`cover property` / `cover sequence`", "`covergroup`"],
        [["Measures", "Temporal scenarios: 'a stall of 3+ cycles followed "
          "by a back-to-back transfer'", "Values and value combinations at "
          "sample points; simple value transitions"],
         ["Strength", "Precise cycle-level ordering, overlaps, latencies",
          "Bins, crosses, ranges; compact models of large spaces"],
         ["Weakness", "One cover = one scenario; no binning", "Poor at "
          "timing relationships between different signals"],
         ["Where", "Modules/interfaces/checkers, bound to RTL", "Classes "
          "(monitors, collectors), modules, interfaces"],
         ["Formal", "Used as reachability targets", "Ignored"]],
        widths=[16, 42, 42], bold_first=True)
    p("A mature coverage model uses both: covergroups for the data space of "
      "transactions (sizes, types, addresses, IDs, response codes and their "
      "crosses) and cover properties for the timing space (back-pressure "
      "shapes, interleavings, arbitration fairness windows, reset in the "
      "middle of a burst).")

    # ------------------------------------------------------------------
    h2("Coverage closure and the verification plan")
    p("Coverage is only meaningful against a **verification plan** (vplan, "
      "testplan): a document, usually a spreadsheet or a tool-managed plan "
      "(Verdi/VC Planner, vManager, Questa Verification Management), that "
      "lists every feature of the specification, how it will be verified "
      "(random test, directed test, assertion, formal proof), and which "
      "coverage items prove it was exercised. Each coverpoint, cross or "
      "cover property carries an `option.comment` or naming convention that "
      "links it back to its plan item, and the tool back-annotates merged "
      "regression coverage onto the plan.")
    diagram([
        "  spec features --> verification plan --> coverage model (covergroups,",
        "        ^            (items, owners,        cover properties, code cov)",
        "        |             methods, goals)                 |",
        "        |                                             v",
        "  spec/plan review <-- hole analysis <-- merged coverage database",
        "        |              (why is it 0?)       (all seeds, all tests)",
        "        v                   |",
        "  waivers / exclusions      +--> constraint tuning, new directed tests,",
        "  (reviewed, signed)             formal proof of unreachability",
    ], "The coverage closure loop.")
    bul(["**Write the model early**, from the spec, before the stimulus is "
         "mature, and review it with the designer and architect; a "
         "coverage model is as much a spec review as a DV artifact.",
         "**Run the random regression first** and let it saturate; then "
         "analyse holes. Most holes have one of four causes: a constraint "
         "that makes the scenario impossible, a missing sequence/test, a "
         "bin that is actually unreachable in this configuration, or a "
         "genuine RTL bug that prevents the state being reached.",
         "**Close deliberately**: tune constraints or distributions, write "
         "directed or semi-directed tests for the remaining holes, and use "
         "formal tools to prove unreachable bins really are unreachable "
         "before waiving them.",
         "**Merge** coverage across all tests and seeds (UCIS-based "
         "databases) and track it per build; coverage that drops after an "
         "RTL change is a regression signal just like a failing test.",
         "**Rank tests** by unique coverage contribution to build a fast "
         "smoke/sanity regression out of the few seeds that hit the most "
         "bins.",
         "**Sign-off** needs 100% of plan items met (with every waiver "
         "reviewed), code-coverage targets met with reviewed exclusions, all "
         "assertions active and non-vacuous, and zero open failures."])
    box("expert", "Interview insight: '100% coverage but the chip has a bug'",
        "Coverage measures what was exercised, not what was checked. A bin "
        "can be hit while the scoreboard compares the wrong field, while an "
        "assertion is disabled, or while the bug's symptom is masked. That "
        "is why sign-off requires coverage **and** checkers **and** a "
        "reviewed plan, and why mature teams also use mutation/fault "
        "insertion (e.g. Certitude) to measure whether the testbench would "
        "detect a bug if one were present.")

    # ------------------------------------------------------------------
    h2("Summary")
    bul(["Code coverage is automatic and measures the implementation; "
         "functional coverage is written from the spec and measures "
         "scenarios. Sign-off needs both.",
         "A covergroup is a type; instances created with `new` count "
         "independently; sampling is by clocking event, block event or "
         "`sample()`, optionally with arguments.",
         "Bins: automatic (up to `auto_bin_max` = 64), single, arrays `[]`, "
         "fixed-count `[N]` (remainder in the last bin), `default`, "
         "`ignore_bins`, `illegal_bins` (run-time error), `wildcard`.",
         "Transition bins cover successive sampled values with `=>`, `[*]`, "
         "`[->]` and `[=]`; crosses cover combinations, shaped with "
         "`binsof`, `intersect`, `&&`, `||` and `!`.",
         "Coverage is the weighted average of coverpoint and cross "
         "percentages, each the fraction of bins with at least `at_least` "
         "hits; `option` is per instance, `type_option` static.",
         "Embedded covergroups live in classes and must be constructed in "
         "`new`; sample monitored, not generated, transactions.",
         "Closure is a loop: plan, model, regress, analyse holes, tune or "
         "direct, prove or waive, merge and track."])

    h2("Exercises")
    bul(["For `coverpoint addr[7:0]` with no bins and `option.auto_bin_max = "
         "10`, how many bins are created and which values are in the last "
         "one?",
         "Write bins for a 3-bit field such that value 7 is illegal, value "
         "6 is ignored, 0 has its own bin and 1-5 are covered by one bin per "
         "value. How many bins count toward coverage?",
         "Given samples IDLE, BUSY, BUSY, BUSY, WAIT, BUSY, DONE, IDLE, which "
         "of `(BUSY [*3])`, `(BUSY [*2:4])`, `(BUSY [-> 2])` and "
         "`(IDLE => BUSY => DONE)` are hit? Explain each.",
         "A cross of cp_a (4 bins) and cp_b (5 bins, one of them an "
         "ignore_bins) has one user bin selecting `binsof(cp_a) intersect "
         "{0}`. How many cross bins exist?",
         "Design the coverage model (covergroups and cover properties) for "
         "a 4-requester round-robin arbiter. Which items prove fairness?",
         "Explain three different reasons why a bin might remain at 0 after "
         "10 000 random seeds, and the right action for each."],
        ordered=True)


# =============================================================================
#                 Chapter 24 - DPI-C, VPI and co-simulation
# =============================================================================
def ch24():
    chapter("DPI-C, VPI and Co-Simulation with C and Python", newpage=True)
    p("No SoC is verified in SystemVerilog alone. The architecture team "
      "writes C/C++ reference models of the datapaths, the CPU team has an "
      "instruction-set simulator, the software team has drivers and "
      "firmware, and the algorithm team works in Python or MATLAB. The "
      "testbench must reuse all of them rather than re-implement them. "
      "SystemVerilog offers two standard foreign-language interfaces: the "
      "**Direct Programming Interface (DPI-C)**, which makes a C function "
      "callable like an SV function and vice versa, and the older "
      "**Verilog Procedural Interface (VPI)**, which gives C code a "
      "handle-based view of the whole simulation database. Python "
      "testbench frameworks such as cocotb are built on VPI.")
    p("This chapter explains both interfaces at LRM level (IEEE 1800 "
      "clauses 35-38 and Annex H/I), runs a DPI-C reference-model example "
      "with Verilator 5.020, a VPI application with Icarus Verilog 12 and a "
      "cocotb Python testbench with cocotb 2.1.0 on Icarus, and closes with "
      "how C/C++, SystemC and ISS golden models are co-simulated in "
      "industrial SoC DV flows. Chapter 10 introduced PLI/VPI from the "
      "Verilog side; here we go further.")

    tbl(["Interface", "Direction and granularity", "Typical use"],
        [["DPI-C import", "SV calls C: function-call granularity, "
          "argument passing, no knowledge of the design", "Reference models, "
          "checksums, file formats, OS services, ISS step()"],
         ["DPI-C export", "C calls SV functions/tasks (from within an "
          "imported context call)", "C test code driving a bus via an SV "
          "BFM task; firmware-driven tests"],
         ["VPI", "C inspects and controls the simulator: hierarchy, values, "
          "callbacks, time", "Debuggers, waveform dumpers, coverage tools, "
          "cocotb, custom system tasks"],
         ["Co-simulation", "Whole models (SystemC, ISS, Python) exchanging "
          "transactions with RTL through DPI/VPI/TLM", "Virtual platforms, "
          "lockstep CPU checking, HW/SW co-verification"]],
        widths=[18, 44, 38], bold_first=True)

    # ------------------------------------------------------------------
    h2("Importing C functions and tasks")
    p("An import declaration tells SV that a subroutine is implemented in a "
      "foreign language. It may appear wherever a function declaration may "
      "(module, interface, package, program, compilation unit), and the "
      "imported routine is then called exactly like a native SV function "
      "or task.")
    code(r"""// import "DPI-C" [pure | context] function <return_type> name(<args>);
import "DPI-C" pure    function int    crc8_byte(input int crc, input int data);
import "DPI-C"         function void   c_log(input string msg);
import "DPI-C" context function int    c_calls_sv(input int x);
import "DPI-C" context task            c_run_test(input int seed);  // may consume time
import "DPI-C" function chandle        model_new(input int cfg);    // opaque C pointer
import "DPI-C" function void           model_step(input chandle m, input int din,
                                                  output int dout);
// C name different from the SV name: "DPI-C" [property] c_name = function ...
import "DPI-C" pure sin = function real sv_sin(input real x);        // libm's sin()""",
         "Forms of the import declaration (IEEE 1800-2017 clause 35.5).")
    tbl(["Property", "Rule"],
        [["`pure` function", "Result depends only on inputs; no side "
          "effects, no I/O, no global state, no calls to exported SV. The "
          "simulator may skip calls whose results are unused or reuse "
          "results (constant folding). Only functions with a non-void "
          "result and no output/inout arguments can be pure"],
         ["`context`", "The C code may call exported SV subroutines, use "
          "VPI, or query the scope (`svGetScope`). The simulator must "
          "preserve the calling scope, which costs a little speed; calling an "
          "export from a non-context import is an error"],
         ["Neither", "May have side effects (printing, allocating) but must "
          "not call back into SV or VPI"],
         ["Imported task", "Implemented in C as a function returning `int`: "
          "0 normally, 1 if the task was disabled while inside an exported "
          "task it called (see `svIsDisabledState`). May call exported "
          "tasks that consume simulation time"],
         ["Return types", "Only `void`, `byte`, `shortint`, `int`, "
          "`longint`, `real`, `shortreal`, `chandle`, `string`, scalar `bit` "
          "and `logic`. Packed vectors and other larger "
          "results are returned through `output` arguments"],
         ["Arguments", "Directions `input`, `output`, `inout`; `ref` is not "
          "allowed"],
         ["Name space", "All DPI-C names share one global C name space: two "
          "packages importing the same C name must use the same signature"]],
        widths=[20, 80], bold_first=True)
    box("warn", "PITFALL: lying about purity",
        "Declaring a function `pure` when it keeps state (a random-number "
        "generator, a model with an internal register, a function that "
        "prints) is undefined behaviour: an optimising simulator may call it "
        "fewer times than the source suggests, reorder calls, or cache the "
        "result. Symptoms appear only at higher optimisation levels or on "
        "another vendor's simulator. Use `pure` only for true mathematical "
        "functions.")

    # ------------------------------------------------------------------
    h2("Data type mapping")
    p("The LRM (Annex H) defines exactly how each SV argument type appears "
      "in C. Small scalar types are passed by value for `input`, and by "
      "pointer for `output` and `inout`. Packed vectors and 4-state values "
      "use canonical types defined in `svdpi.h`. Do not guess: every "
      "simulator can generate a C header with the exact prototypes (Questa "
      "`vlog -dpiheader`, Verilator's `V<top>__Dpi.h`), and your C file "
      "should include it so the C compiler checks the signatures.")
    tbl(["SystemVerilog type", "C type (input)", "C type (output/inout)"],
        [["`byte`", "`char`", "`char*`"],
         ["`shortint`", "`short int`", "`short int*`"],
         ["`int`", "`int`", "`int*`"],
         ["`longint`", "`long long`", "`long long*`"],
         ["`real` / `shortreal`", "`double` / `float`", "`double*` / `float*`"],
         ["`chandle`", "`void*` (opaque)", "`void**`"],
         ["`string`", "`const char*`", "`const char**`"],
         ["`bit` (scalar)", "`svBit` (unsigned char, 0/1)", "`svBit*`"],
         ["`logic`, `reg` (scalar)", "`svLogic` (0,1,2=Z,3=X)", "`svLogic*`"],
         ["`bit [N-1:0]` (packed)", "`const svBitVecVal*`", "`svBitVecVal*`"],
         ["`logic [N-1:0]` (packed)", "`const svLogicVecVal*`",
          "`svLogicVecVal*`"],
         ["`enum`", "As its base type", "As its base type"],
         ["Packed struct/union", "As a packed vector of the same width",
          "Same"],
         ["Unpacked struct", "`const struct*` with matching member types",
          "`struct*`"],
         ["Sized unpacked array `int a[4]`", "`const int*` to the first "
          "element", "`int*`"],
         ["Open array `int a[]`", "`const svOpenArrayHandle`",
          "`svOpenArrayHandle`"]],
        widths=[30, 38, 32])
    p("Packed vectors are passed as arrays of 32-bit chunks, "
      "`SV_PACKED_DATA_NELEMS(N)` = (N + 31) / 32 of them, **least "
      "significant chunk first** (chunk 0 holds bits 31:0). `svBitVecVal` "
      "is a `uint32_t`. A 4-state vector uses `svLogicVecVal`, a struct of "
      "two words per chunk, `aval` and `bval`, encoding each bit as "
      "(aval,bval) = (0,0) for 0, (1,0) for 1, (0,1) for Z and (1,1) for X. "
      "Unused high bits of the last chunk are undefined on input: mask "
      "them. Bits of a packed vector can also be accessed with helper "
      "functions (`svGetBitselBit`, `svGetPartselLogic`, `svPutPartselBit`, "
      "...).")
    box("warn", "PITFALL: 4-state values collapse at the C boundary",
        "Passing a `logic` value to an `int` or `bit` argument converts X "
        "and Z to 0 silently, so a C model can happily 'agree' with an RTL "
        "output that is actually X. When a reference model compares RTL "
        "outputs, either pass them as `logic` vectors and check `bval`, or "
        "check `$isunknown()` in SV before calling C.")

    # ------------------------------------------------------------------
    h2("Open arrays and the svdpi.h API")
    p("An **open array** formal (`int a[]`, `bit [7:0] b[]`, or even an "
      "open packed dimension `bit [] v`) lets one C function accept arrays "
      "of any size. C receives an opaque `svOpenArrayHandle` and queries "
      "it:")
    tbl(["svdpi.h routine", "Purpose"],
        [["`svLow(h,d)`, `svHigh(h,d)`, `svLeft`, `svRight`, `svSize(h,d)`",
          "Bounds and size of dimension d (1 = leftmost unpacked dimension)"],
         ["`svDimensions(h)`", "Number of unpacked dimensions"],
         ["`svGetArrElemPtr1(h, i)` (and 2, 3, `svGetArrElemPtr`)",
          "Pointer to one element, indexed with SV indices"],
         ["`svGetArrayPtr(h)`, `svSizeOfArray(h)`", "Pointer to and size of "
          "the whole array if it is contiguous in memory (may be NULL)"],
         ["`svGetBitArrElem1`, `svPutLogicArrElem1VecVal`, ...",
          "Read/write elements of packed/4-state arrays"],
         ["`svGetScope()`, `svSetScope(s)`, `svGetNameFromScope(s)`",
          "Current SV scope of a context call; select the scope before "
          "calling an export"],
         ["`svPutUserData(s, key, data)`, `svGetUserData(s, key)`",
          "Attach C data to an SV scope (per-instance model state)"],
         ["`svIsDisabledState()`, `svAckDisabledState()`", "Handle `disable` "
          "of an imported task"]],
        widths=[48, 52])

    # ------------------------------------------------------------------
    h2("Worked example: calling a C reference model from SystemVerilog")
    p("The example below exercises the most common DPI patterns: a pure C "
      "golden model (CRC-8, polynomial 0x07) checked against an RTL-style "
      "SV implementation, a 64-bit packed vector argument, an open array, a "
      "string, and a context import that calls back into an exported SV "
      "function. The C source is simply added to the Verilator command "
      "line; `--binary` compiles and links it with the model.")
    code(r"""module dpi_tb;
  import "DPI-C" pure function int crc8_byte(input int crc, input int data);
  import "DPI-C" function int lane_sum(input bit [63:0] v);
  import "DPI-C" function int arr_sum(input int a[]);
  import "DPI-C" function void c_log(input string msg);
  import "DPI-C" context function int c_calls_sv(input int x);
  export "DPI-C" function sv_scale;

  function int sv_scale(input int x);
    return x * 10;
  endfunction

  // RTL-style CRC-8 the C model checks
  function automatic logic [7:0] crc8_rtl(logic [7:0] crc, logic [7:0] d);
    logic [7:0] c = crc ^ d;
    repeat (8) c = c[7] ? ((c << 1) ^ 8'h07) : (c << 1);
    return c;
  endfunction

  initial begin
    int ref_crc = 0; logic [7:0] rtl_crc = 0; int errors = 0;
    int a[5] = '{1, 2, 3, 4, 5};
    byte msg[] = '{8'h31, 8'h32, 8'h33, 8'h34, 8'h35, 8'h36, 8'h37, 8'h38, 8'h39};
    foreach (msg[i]) begin
      ref_crc = crc8_byte(ref_crc, int'(msg[i]) & 'hFF);
      rtl_crc = crc8_rtl(rtl_crc, msg[i]);
      if (rtl_crc != ref_crc[7:0]) errors++;
    end
    $display("CRC-8(\"123456789\"): rtl=%h model=%h errors=%0d",
             rtl_crc, ref_crc[7:0], errors);
    $display("lane_sum = %0d", lane_sum(64'h0004_0003_0002_0001));
    $display("arr_sum  = %0d", arr_sum(a));
    c_log($sformatf("hello from SV at t=%0t", $time));
    $display("c_calls_sv(7) = %0d", c_calls_sv(7));
    $finish;
  end
endmodule""", "dpi_tb.sv - the SV side: four imports, one export.")
    code(r"""// ref_model.c - C reference model called from SystemVerilog through DPI-C
#include <stdio.h>
#include <stdint.h>
#include "svdpi.h"

#ifdef __cplusplus          // Verilator compiles .c files with g++: keep C linkage
extern "C" {
#endif

// CRC-8 (poly 0x07) over one byte: a typical golden model for a datapath block
int crc8_byte(int crc, int data) {
    uint8_t c = (uint8_t)(crc ^ data);
    for (int i = 0; i < 8; i++)
        c = (c & 0x80) ? (uint8_t)((c << 1) ^ 0x07) : (uint8_t)(c << 1);
    return c;
}

// Packed 64-bit vector in, sum of its four 16-bit lanes out
int lane_sum(const svBitVecVal *v) {
    int s = 0;
    for (int w = 0; w < 2; w++)          // svBitVecVal = 32-bit chunks, LSB chunk first
        s += (v[w] & 0xFFFF) + (v[w] >> 16);
    return s;
}

// Open array: works for any unpacked size the SV caller passes
int arr_sum(const svOpenArrayHandle a) {
    int s = 0;
    for (int i = svLow(a, 1); i <= svHigh(a, 1); i++)
        s += *(int *)svGetArrElemPtr1(a, i);
    return s;
}

// String argument: C sees a const char *
void c_log(const char *msg) { printf("[C] %s\n", msg); }

// Imported 'context' function calling back into an exported SV function
int sv_scale(int x);                      // exported from SV (see Vdpi_tb__Dpi.h)
int c_calls_sv(int x) { return sv_scale(x) + 1; }

#ifdef __cplusplus
}
#endif""", "ref_model.c - the C side.")
    code(r"""$ verilator --binary -Wall -Wno-fatal dpi_tb.sv ref_model.c
$ ./obj_dir/Vdpi_tb""", "Build and run: the .c file is compiled and linked with the "
       "Verilated model.")
    out(r"""CRC-8("123456789"): rtl=f4 model=f4 errors=0
lane_sum = 10
arr_sum  = 15
[C] hello from SV at t=0
c_calls_sv(7) = 71
- dpi_tb.sv:35: Verilog $finish""", "Verilator 5.020 output. 0xF4 is the "
        "published check value of CRC-8/SMBUS for the string '123456789', so "
        "both the model and the RTL are right.")
    p("Verilator writes the prototypes it expects into "
      "`obj_dir/Vdpi_tb__Dpi.h`. An excerpt of the generated file shows the "
      "mapping rules of the previous section applied: the `bit [63:0]` "
      "became `const svBitVecVal*`, the open array `const "
      "svOpenArrayHandle` and the string `const char*`.")
    code(r"""    // DPI EXPORTS
    // DPI export at dpi_tb.sv:9:16
    extern int sv_scale(int x);

    // DPI IMPORTS
    // DPI import at dpi_tb.sv:4:31
    extern int arr_sum(const svOpenArrayHandle a);
    // DPI import at dpi_tb.sv:6:39
    extern int c_calls_sv(int x);
    // DPI import at dpi_tb.sv:5:32
    extern void c_log(const char* msg);
    // DPI import at dpi_tb.sv:2:36
    extern int crc8_byte(int crc, int data);
    // DPI import at dpi_tb.sv:3:31
    extern int lane_sum(const svBitVecVal* v);""",
         "Excerpt of the generated `obj_dir/Vdpi_tb__Dpi.h` (Verilator 5.020).")
    box("warn", "PITFALL: C++ name mangling",
        "The first build of this example failed at link time with "
        "'undefined reference to `c_log`' and 'undefined reference to "
        "`sv_scale(int)`': Verilator compiles `.c` files with the C++ "
        "compiler, which mangles names. DPI requires C linkage, hence the "
        "`extern \"C\"` block guarded by `__cplusplus`. The same applies to "
        "any C++ model: wrap the DPI entry points in `extern \"C\"`, or "
        "include the tool-generated header, which already contains the "
        "guard. Also note that without `$finish` a Verilator `--binary` "
        "model whose `initial` block ends does not terminate by itself here "
        "- always end tests explicitly.")

    # ------------------------------------------------------------------
    h2("Exporting SV functions and tasks to C")
    p("`export \"DPI-C\" function name;` (or `task name;`) makes an SV "
      "subroutine callable from C. The export declaration names a "
      "subroutine defined in the **same scope**; it does not declare its "
      "signature again. Exports may only be called from C code that is "
      "running inside a `context` import call (or from a VPI callback "
      "after setting a scope), because an SV function belongs to a "
      "particular module instance: C must know **which** instance's "
      "`sv_scale` it calls. Inside a context import the scope is the one "
      "where the import was declared; `svSetScope()` switches to another "
      "instance, typically using a scope saved with `svGetScope()` during an "
      "earlier registration call.")
    code(r"""// SV side: a bus-functional model that C test code can drive
module apb_bfm (input logic pclk /* ... APB pins ... */);
  export "DPI-C" task apb_write;
  export "DPI-C" task apb_read;
  import "DPI-C" context task c_test_main();      // the C test program
  import "DPI-C" context function void c_register_bfm(string name);

  task apb_write(input int addr, input int data);
    @(posedge pclk) /* drive psel, paddr, pwdata ... wait for pready */;
  endtask
  task apb_read(input int addr, output int data);
    @(posedge pclk) /* ... */ data = 0;
  endtask

  initial begin
    c_register_bfm($sformatf("%m"));     // C saves svGetScope() for this instance
    c_test_main();                       // C now runs the test, consuming time
    $finish;
  end
endmodule

// C side (firmware-like test): tasks return int, outputs are pointers
//   #include "svdpi.h"
//   extern int apb_write(int addr, int data);
//   extern int apb_read(int addr, int *data);
//   static svScope bfm;
//   void c_register_bfm(const char *name) { bfm = svGetScope(); }
//   int c_test_main(void) {
//       int v;
//       svSetScope(bfm);
//       apb_write(0x40001000, 0x1);         /* enable the UART */
//       apb_read (0x40001004, &v);          /* status */
//       return 0;                           /* 0 = not disabled */
//   }""", "Exported time-consuming tasks let C test code drive an SV BFM - the "
       "basis of HW/SW co-verification (IEEE 1800-2017; exported tasks that "
       "consume time need a simulator that supports them, such as the "
       "commercial ones).")
    p("This pattern is how SoC teams run the **same** C test program on "
      "three platforms: in RTL simulation (the `apb_write` calls go through "
      "DPI into a BFM), on an emulator or FPGA prototype (the same calls go "
      "through a transactor), and on silicon (the calls become real memory-"
      "mapped accesses). Only the thin access layer changes.")

    # ------------------------------------------------------------------
    h2("Compiling and linking across simulators")
    tbl(["Tool", "How the C code gets in", "Header generation"],
        [["Verilator", "List `.c/.cpp` files on the command line (or "
          "`-CFLAGS`, `-LDFLAGS`); compiled with the model by make",
          "Automatic: `obj_dir/V<top>__Dpi.h`"],
         ["Questa / ModelSim", "`vlog` for SV; C compiled into a shared "
          "library and loaded with `vsim -sv_lib <lib>` (or compiled "
          "automatically when the C file is given to `vlog`)",
          "`vlog -dpiheader dpi.h`"],
         ["Xcelium", "`xrun top.sv model.c` compiles and links the C; or "
          "prebuilt libraries with `-sv_lib`", "Tool option to dump the "
          "DPI header"],
         ["VCS", "`vcs -sverilog top.sv model.c` (C compiled and linked "
          "into simv); or `-sv_lib`/`-LDFLAGS`", "Tool option to dump the "
          "DPI header"],
         ["Any, precompiled", "`-sv_lib name` loads `name.so` at run time; "
          "`-sv_liblist` reads a list of libraries (LRM Annex J)", ""]],
        widths=[18, 52, 30], bold_first=True)
    p("Build C models with `-fPIC` when they go into shared libraries, use "
      "the same compiler major version as the simulator's runtime to avoid "
      "C++ ABI surprises, and compile with `-g` so `gdb` can attach to the "
      "simulator process and break inside the model.")

    # ------------------------------------------------------------------
    h2("VPI basics")
    p("VPI (IEEE 1800 clauses 36-38, header `vpi_user.h`, and "
      "`sv_vpi_user.h` for SV extensions) is the third generation of the "
      "Verilog Programming Language Interface, replacing the older TF and "
      "ACC routines (PLI 1.0). It is object-oriented in C: every design "
      "object (module, net, reg, port, parameter, task call, even a "
      "statement) is reached through an opaque `vpiHandle`, and "
      "relationships between objects are navigated with a small set of "
      "routines.")
    tbl(["Routine", "Purpose"],
        [["`vpi_register_systf(&s_vpi_systf_data)`", "Define a user system "
          "task or function (`$walk`) with `calltf`, `compiletf`, `sizetf` "
          "callbacks"],
         ["`vpi_handle(type, ref)`", "One-to-one relation, e.g. "
          "`vpi_handle(vpiSysTfCall, NULL)` = the current call"],
         ["`vpi_iterate(type, ref)` + `vpi_scan(it)`", "One-to-many: nets of "
          "a module, arguments of a call, sub-instances"],
         ["`vpi_handle_by_name(\"top.u.q\", NULL)`", "Look up by "
          "hierarchical name"],
         ["`vpi_get(prop, h)`, `vpi_get_str(prop, h)`", "Integer / string "
          "properties: `vpiSize`, `vpiType`, `vpiName`, `vpiFullName`, "
          "`vpiDefName`"],
         ["`vpi_get_value(h, &v)`, `vpi_put_value(h, &v, &t, flags)`",
          "Read / write values in many formats (`vpiIntVal`, `vpiHexStrVal`, "
          "`vpiVectorVal`...); `vpiNoDelay`, `vpiInertialDelay`, "
          "`vpiForceFlag`..."],
         ["`vpi_register_cb(&s_cb_data)`", "Callbacks on value change, time, "
          "simulation phases"],
         ["`vpi_get_time`, `vpi_printf`, `vpi_control(vpiFinish, ...)`",
          "Time, printing to the simulator log, stopping/finishing"],
         ["`vpi_chk_error`, `vpi_release_handle`", "Error checking; free "
          "handles (older name `vpi_free_object`)"]],
        widths=[42, 58])
    p("An application registers itself through the `vlog_startup_routines` "
      "array: the simulator calls each function in it at start-up, and "
      "these register the system tasks and any start-of-simulation "
      "callbacks. The example defines two system tasks: `$walk(scope)` "
      "recursively lists every scope with its nets and regs, and "
      "`$watch(signal)` installs a value-change callback.")
    code(r"""// walk.c - a VPI application: $walk(scope) lists the hierarchy, $watch(sig) adds a callback
#include <stdio.h>
#include <vpi_user.h>

static void walk(vpiHandle scope, int depth) {
    vpiHandle it, h;
    vpi_printf("%*sscope %s\n", 2 * depth, "", vpi_get_str(vpiFullName, scope));
    if ((it = vpi_iterate(vpiNet, scope)))
        while ((h = vpi_scan(it)))
            vpi_printf("%*s  net %s [%d bits]\n", 2 * depth, "", vpi_get_str(vpiName, h),
                       vpi_get(vpiSize, h));
    if ((it = vpi_iterate(vpiReg, scope)))
        while ((h = vpi_scan(it)))
            vpi_printf("%*s  reg %s [%d bits]\n", 2 * depth, "", vpi_get_str(vpiName, h),
                       vpi_get(vpiSize, h));
    if ((it = vpi_iterate(vpiModule, scope)))
        while ((h = vpi_scan(it))) walk(h, depth + 1);
}

static PLI_INT32 walk_calltf(PLI_BYTE8 *user) {
    vpiHandle systf = vpi_handle(vpiSysTfCall, NULL);
    vpiHandle args  = vpi_iterate(vpiArgument, systf);
    vpiHandle scope = vpi_scan(args);
    vpi_free_object(args);
    walk(scope, 0);
    return 0;
}

static PLI_INT32 on_change(p_cb_data cb) {
    s_vpi_value v = { vpiHexStrVal };
    vpi_get_value(cb->obj, &v);
    vpi_printf("  [cb] t=%u %s = %s\n", cb->time->low,
               vpi_get_str(vpiFullName, cb->obj), v.value.str);
    return 0;
}

static PLI_INT32 watch_calltf(PLI_BYTE8 *user) {
    vpiHandle systf = vpi_handle(vpiSysTfCall, NULL);
    vpiHandle args  = vpi_iterate(vpiArgument, systf);
    static s_vpi_time  t = { vpiSimTime };
    static s_vpi_value v = { vpiSuppressVal };
    s_cb_data cb = { cbValueChange, on_change, NULL, &t, &v, 0, NULL };
    cb.obj = vpi_scan(args);
    vpi_free_object(args);
    vpi_register_cb(&cb);
    return 0;
}

static void register_tasks(void) {
    s_vpi_systf_data tf = { vpiSysTask, 0, "$walk", walk_calltf, NULL, NULL, NULL };
    vpi_register_systf(&tf);
    tf.tfname = "$watch"; tf.calltf = watch_calltf;
    vpi_register_systf(&tf);
}

void (*vlog_startup_routines[])(void) = { register_tasks, 0 };""",
         "walk.c - hierarchy traversal and a value-change callback.")
    code(r"""module counter (input wire clk, input wire rst, output reg [3:0] q);
  always @(posedge clk) q <= rst ? 4'd0 : q + 4'd1;
endmodule

module top;
  reg clk = 0, rst = 1;
  wire [3:0] q;
  counter u_cnt (.clk(clk), .rst(rst), .q(q));
  always #5 clk = ~clk;
  initial begin
    $walk(top);
    $watch(q);
    #12 rst = 0;
    #30 $finish;
  end
endmodule""", "top.v - the design the VPI tasks inspect.")
    code(r"""$ iverilog-vpi walk.c                 # builds walk.vpi (a shared object)
$ iverilog -o top.vvp top.v
$ vvp -M. -mwalk top.vvp               # -M: search path, -m: load module walk.vpi""",
         "Building and loading a VPI module with Icarus Verilog.")
    out(r"""scope top
  net q [4 bits]
  reg clk [1 bits]
  reg rst [1 bits]
  scope top.u_cnt
    net clk [1 bits]
    net rst [1 bits]
    reg q [4 bits]
  [cb] t=5 top.q = 0
  [cb] t=15 top.q = 1
  [cb] t=25 top.q = 2
  [cb] t=35 top.q = 3
top.v:14: $finish called at 42 (1s)""", "Icarus Verilog 12 output. Inside "
        "`counter`, `q` is a reg while in `top` it is a net; the callback "
        "fires on every change of `top.q`, including the X -> 0 change at 5.")
    h3("Callbacks")
    tbl(["Callback reason", "Fires when"],
        [["`cbValueChange`", "The object (net, reg, variable, event) changes "
          "value"],
         ["`cbAfterDelay`", "After a relative delay - a C-side timer"],
         ["`cbReadWriteSynch`", "At a point in the current time step where "
          "values may still be written (before the end of the time step)"],
         ["`cbReadOnlySynch`", "At the end of the time step, when values "
          "are final; writing is not allowed"],
         ["`cbNextSimTime`", "At the start of the next time step"],
         ["`cbStartOfSimulation`, `cbEndOfSimulation`", "Simulation "
          "start/end: open and close files, print reports"],
         ["`cbEndOfCompile`", "After elaboration, before time 0"]],
        widths=[38, 62])
    box("note", "DPI or VPI?",
        "Use DPI for anything that looks like a function call: it is faster "
        "(no handle lookups, arguments go directly into C), type-checked, "
        "and portable between simulators. Use VPI when you need what DPI "
        "cannot give: discovering the hierarchy at run time, reading "
        "signals nobody passed to you, waiting on arbitrary value changes, "
        "or building a generic tool. VPI access to signals also disables "
        "some simulator optimisations: commercial tools require read/write "
        "access to be enabled explicitly (`+acc`/`-access +rwc`/debug "
        "switches), and Verilator needs `--vpi` and `/*verilator "
        "public*/` (or `--public-flat-rw`) on the signals VPI touches.")

    # ------------------------------------------------------------------
    h2("cocotb: Python testbenches over VPI")
    p("cocotb (COroutine based COsimulation TestBench) is an open-source "
      "framework that runs Python test code alongside any simulator with "
      "VPI, VHPI or FLI: Icarus, Verilator, Questa, Xcelium, VCS, Riviera, "
      "GHDL and others. The simulator runs the HDL top level as usual; "
      "cocotb's GPI library, loaded through VPI, embeds a Python "
      "interpreter and exposes the design hierarchy as Python objects "
      "(`dut.a`, `dut.u_core.pc`). Tests are `async` functions that "
      "`await` **triggers** - `RisingEdge(sig)`, `FallingEdge`, "
      "`Timer(10, unit=\"ns\")`, `ClockCycles`, `ReadOnly()`, `ReadWrite()` "
      "- which map directly onto VPI callbacks. Python's ecosystem then "
      "provides the golden model (NumPy, a Python ISS, a network stack) "
      "without any DPI glue.")
    code(r"""`timescale 1ns/1ps
// 8-bit saturating adder with a registered output
module sat_add (
  input  logic       clk,
  input  logic [7:0] a, b,
  output logic [7:0] y
);
  logic [8:0] s;
  assign s = a + b;
  always_ff @(posedge clk) y <= s[8] ? 8'hFF : s[7:0];
endmodule""", "sat_add.sv - the DUT. cocotb needs a timescale that can "
       "represent the clock period (without it, the first run failed with "
       "'Unable to accurately represent 10(ns) with the simulator precision "
       "of 1e0').")
    code(r"""# test_sat_add.py - a cocotb testbench: Python drives and checks the SV DUT through VPI
import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, ReadOnly

def model(a, b):                          # the golden model is plain Python
    return min(a + b, 255)

@cocotb.test()
async def random_adds(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    rng = random.Random(1)
    vectors = [(0, 0), (255, 1), (200, 55), (128, 128)]
    vectors += [(rng.randrange(256), rng.randrange(256)) for _ in range(96)]
    errors = 0
    for a, b in vectors:
        await FallingEdge(dut.clk)        # drive away from the active edge
        dut.a.value = a
        dut.b.value = b
        await RisingEdge(dut.clk)
        await ReadOnly()                  # sample after the flop has updated
        got = int(dut.y.value)
        if got != model(a, b):
            errors += 1
            dut._log.error("a=%d b=%d y=%d exp=%d", a, b, got, model(a, b))
    dut._log.info("checked %d vectors, %d errors", len(vectors), errors)
    assert errors == 0""", "test_sat_add.py - directed corner cases plus 96 "
       "random vectors against a Python model.")
    code(r"""# run.py - build with Icarus and run the cocotb test (cocotb 2.x runner API)
from cocotb_tools.runner import get_runner

runner = get_runner("icarus")
runner.build(sources=["sat_add.sv"], hdl_toplevel="sat_add",
             build_args=["-g2012"], always=True)
runner.test(hdl_toplevel="sat_add", test_module="test_sat_add")""",
         "run.py - the Python runner replaces the Makefile flow of cocotb 1.x "
         "(`pip install cocotb`; then `python run.py`).")
    out(r"""1000.00ns INFO cocotb.sat_add checked 100 vectors, 0 errors
1000.00ns INFO cocotb.regression test_sat_add.random_adds passed
** TESTS=1 PASS=1 FAIL=0 SKIP=0 1000.00 0.01 140698.11 **""",
        "cocotb 2.1.0 with Icarus Verilog 12: the relevant lines of the log "
        "(runs of spaces condensed).")
    p("To see the checker work, the saturation was removed from the RTL "
      "(`y <= s[7:0];`) and the test re-run:")
    out(r""" 20.00ns ERROR cocotb.sat_add a=255 b=1 y=0 exp=255
 40.00ns ERROR cocotb.sat_add a=128 b=128 y=0 exp=255
 70.00ns ERROR cocotb.sat_add a=253 b=230 y=227 exp=255
1000.00ns INFO cocotb.sat_add checked 100 vectors, 53 errors
1000.00ns WARNING cocotb.regression test_sat_add.random_adds failed
AssertionError: assert 53 == 0
** TESTS=1 PASS=0 FAIL=1 SKIP=0 1000.00 0.01 73906.80 **""",
        "Same test with the bug injected (first three of the 53 error lines "
        "shown; spaces condensed).")
    box("warn", "PITFALL: cocotb writes are not immediate",
        "Assigning `dut.a.value = 5` schedules a write that the simulator "
        "applies in a later write phase of the time step, so reading "
        "`dut.a.value` on the next line still returns the old value. Writing "
        "after `await ReadOnly()` is an error (the read-only phase forbids "
        "writes) - hence the `FallingEdge` at the top of the loop. The API "
        "also changed between major versions (cocotb 2.0 renamed `units=` "
        "to `unit=`, and the `cocotb_tools.runner` replaced "
        "`cocotb.runner`); pin the version in your project requirements.")
    p("Where cocotb fits on the roadmap: it is widely used in open-source "
      "hardware, startups, FPGA teams and for block-level tests where a "
      "Python model already exists; large SoC teams mostly use UVM in SV "
      "(Chapter 26) and sometimes cocotb for specific blocks. Its limits "
      "are speed (every trigger crosses the VPI boundary into Python) and "
      "the absence of SV-native constraints, covergroups and assertions - "
      "which is why cocotb projects typically keep SVA in the RTL "
      "(Chapter 22) and use Python libraries for randomisation and "
      "coverage.")

    # ------------------------------------------------------------------
    h2("Co-simulation with SystemC and golden models in SoC DV flows")
    tbl(["Model", "Connected via", "Used for"],
        [["C/C++ reference model of a block (DSP, codec, crypto, "
          "compression)", "DPI-C, transaction-level: one call per input "
          "transaction, results compared in the scoreboard", "Block and "
          "subsystem DV; often bit-accurate models from the architecture "
          "team"],
         ["Instruction-set simulator (e.g. Spike or a vendor ISS for a "
          "RISC-V/ARM core)", "DPI: `iss_step()` after every retired "
          "instruction, compare PC, registers, memory writes (lockstep); or "
          "offline trace comparison", "CPU core verification; the riscv-dv "
          "flow compares RTL and ISS instruction traces"],
         ["SystemC/TLM-2.0 virtual platform", "Simulator's native SystemC "
          "co-simulation, or TLM <-> RTL transactors", "Early software "
          "development, performance models, HW/SW co-verification"],
         ["Verilated RTL inside SystemC/C++", "Verilator `--sc` or `--cc` "
          "generates a SystemC/C++ class", "Fast cycle-based models of RTL in "
          "virtual platforms; open-source SoC flows"],
         ["Python / MATLAB algorithm models", "cocotb, DPI with an embedded "
          "interpreter, or C code generated from MATLAB", "Signal "
          "processing, ML accelerators, image pipelines"],
         ["Emulator / FPGA prototype", "Transactors (SCE-MI 2 function-"
          "based interface is built on DPI)", "Booting OS and firmware on "
          "the full SoC at MHz speeds"]],
        widths=[27, 38, 35])
    p("The recurring design decision is the **abstraction level of the "
      "boundary**. Cross it once per transaction (a packet, an instruction, "
      "a DMA descriptor), never once per clock per signal: every DPI call "
      "has a cost, and a per-cycle, per-signal interface is both slow and "
      "tightly coupled to the RTL timing. The SV side converts pin activity "
      "into transactions (monitor), calls the model with a transaction, "
      "and compares transactions in the scoreboard. For models with state, "
      "create them through a `chandle` factory (`model_new`) so that each "
      "SV instance or UVM component owns its own model object, and free "
      "them at the end of the test.")
    diagram([
        "  +------------ SystemVerilog testbench ------------+      +---------------+",
        "  | driver -> DUT pins -> monitor --txn--> scoreboard|<---->| C/C++ model   |",
        "  |                          |                 ^    | DPI  | (chandle per  |",
        "  |                          +-- txn --> model_step()| call | instance)     |",
        "  +--------------------------------------------------+      +---------------+",
        "                 one DPI call per transaction, not per clock",
    ], "Transaction-level coupling of a C reference model through DPI.")
    box("expert", "Interview insight: lockstep ISS comparison",
        "In CPU verification the testbench observes each retired instruction "
        "(through an RVFI-style trace port or internal probes), calls the ISS "
        "via DPI to execute the same instruction, and compares architectural "
        "state immediately. The hard parts are not the DPI calls but the "
        "**non-determinism**: interrupts, timers, memory-mapped I/O and "
        "multi-core memory ordering, where the RTL's behaviour is legal but "
        "different from the ISS. Mature flows let the RTL 'teach' the ISS "
        "(inject the interrupt at the same instruction, return the same MMIO "
        "read data) so the comparison stays exact.")

    # ------------------------------------------------------------------
    h2("Summary")
    bul(["DPI-C imports make C functions and tasks callable from SV; "
         "exports make SV subroutines callable from C inside a `context` "
         "call. `pure` means no side effects; `context` is required to call "
         "exports, VPI or scope routines.",
         "Types map by Annex H: small scalars by value, outputs by pointer, "
         "strings as `const char*`, packed vectors as `svBitVecVal`/"
         "`svLogicVecVal` 32-bit chunks (LSB chunk first, aval/bval for "
         "4-state), open arrays as `svOpenArrayHandle`.",
         "Always compile against the tool-generated header; wrap C++ in "
         "`extern \"C\"`; never lie about `pure`; watch X collapsing to 0.",
         "Verilator compiles C/C++ files given on its command line; "
         "commercial simulators compile them or load `-sv_lib` shared "
         "libraries.",
         "VPI is the handle-based API to the simulation database: "
         "`vpi_register_systf`, `vpi_handle`/`vpi_iterate`/`vpi_scan`, "
         "`vpi_get_value`/`vpi_put_value`, and callbacks.",
         "cocotb runs Python coroutine testbenches on top of VPI; it is "
         "productive for Python-modelled blocks and open-source flows.",
         "Co-simulate models at transaction level: C models, ISS lockstep, "
         "SystemC/TLM virtual platforms and emulator transactors all use the "
         "same idea."])

    h2("Exercises")
    bul(["Write the C prototype for `import \"DPI-C\" function void "
         "f(input logic [95:0] a, output bit [7:0] b, inout int c[]);` and "
         "explain how bit 70 of `a` is found in C, and how to test whether "
         "it is X.",
         "Extend the DPI example with an imported function that returns a "
         "128-bit result. Why can it not be the function's return value, and "
         "what does the declaration look like instead?",
         "Build a stateful C model with `chandle model_new(int)`, "
         "`model_step(chandle, int, output int)` and `model_free(chandle)`, "
         "and use two independent instances from two SV module instances.",
         "Extend `walk.c` with a `$force_zero(sig)` system task that uses "
         "`vpi_put_value` with `vpiForceFlag`, and a `cbEndOfSimulation` "
         "callback that prints how many value changes `$watch` observed.",
         "Port the cocotb test to check the adder in the same cycle with "
         "`ReadWrite()` instead of `FallingEdge`/`ReadOnly()` and explain "
         "what goes wrong.",
         "Sketch the DPI interface of a lockstep checker between a RISC-V "
         "core and an ISS. Which events must be passed from RTL to the ISS "
         "to keep them synchronised?"], ordered=True)
