"""Part V - Putting It Together (Chapters 25-28) of the Verilog & SystemVerilog guide.

Every listing shown with an out() card was compiled and run in this repo's
tool set: the layered FIFO testbench (Ch. 25) and the mini factory/phasing
model (Ch. 26) with Verilator 5.020 (--binary --timing); the pitfall demos
(Ch. 27) with Icarus Verilog 12 and/or Verilator 5.020 as captioned; lint
output from verilator --lint-only -Wall, iverilog -Wall and Yosys 0.33.
UVM code and constraint blocks are shown without output (they need a
commercial simulator with UVM and a constraint solver).
"""

from sv_guide.common import *  # noqa: F401,F403


def part5():
    part("Putting It Together",
         "The first four parts taught the language one construct at a time. "
         "This part assembles them. Chapter 25 builds a complete layered, "
         "class-based testbench from scratch and runs it; Chapter 26 shows "
         "that UVM is nothing more than a disciplined use of the same "
         "language features; Chapter 27 collects the pitfalls, portability "
         "traps and lint rules that separate working code from code that "
         "only appears to work; and Chapter 28 lays out a study roadmap for "
         "RTL, DV, DFT and formal roles on SoC and ASIC teams.")
    ch25()
    ch26()
    ch27()
    ch28()


# =============================================================================
#            Chapter 25 - A layered class-based testbench from scratch
# =============================================================================
def ch25():
    chapter("A Layered Class-Based Testbench from Scratch", newpage=False)
    p("Every industrial verification environment - hand-written, UVM, or a "
      "company's in-house methodology - is built from the same half-dozen "
      "roles: something that decides __what__ to send, something that turns "
      "it into __pin activity__, something that __watches__ the pins, and "
      "something that __decides__ whether what it saw was right. This "
      "chapter builds that architecture in plain SystemVerilog, without any "
      "library, for a small synchronous FIFO. Every class is short, every "
      "language feature is one you have already met (classes in Chapter 18, "
      "mailboxes and fork/join in Chapter 20, interfaces and virtual "
      "interfaces in Chapter 16), and the whole thing is compiled and run "
      "with Verilator 5.020, including a deliberately broken DUT that the "
      "scoreboard catches.")
    p("Building one environment by hand is the single best preparation for "
      "UVM. When you later meet `uvm_driver`, `uvm_monitor`, "
      "`uvm_scoreboard`, `uvm_env` and `uvm_test`, you will recognise them "
      "as exactly the classes written here, plus a factory, a configuration "
      "database and a phase scheduler (Chapter 26).")

    # ------------------------------------------------------------------
    h2("The layers and their responsibilities")
    diagram([
        "  +------------------------------------------------------------------+",
        "  |  TEST        base_test / fill_test : picks knobs, runs the env   |",
        "  +------------------------------------------------------------------+",
        "  |  ENVIRONMENT  env : builds components, connects mailboxes,       |",
        "  |               forks threads, decides when the test is over       |",
        "  +------------------------------------------------------------------+",
        "  |  SCENARIO    generator --(mailbox gen2drv, bounded)--+           |",
        "  +-----------------------------------------------------|------------+",
        "  |  FUNCTIONAL                        scoreboard <--+   |            |",
        "  |                                  (ref model:   |   |            |",
        "  |                                   a queue)     |   |            |",
        "  +------------------------------------------------|---|------------+",
        "  |  COMMAND     monitor --(mailbox mon2scb)-------+   v            |",
        "  |                 ^                              driver           |",
        "  +-----------------|--------------------------------|---------------+",
        "  |  SIGNAL          +-------- virtual interface ----+                |",
        "  |                        fifo_if bus  <-->  sync_fifo (DUT)        |",
        "  +------------------------------------------------------------------+",
        "    static world: module top, interface instance, DUT, clock",
    ], "Figure 25.1 - The classic layered testbench. Classes above the line are "
       "dynamic objects created at time 0; the signal layer is static hardware.")
    p("The split between the __static__ world (modules, interfaces, the DUT, "
      "the clock) and the __dynamic__ world (class objects created with "
      "`new` at run time) is fundamental. Classes cannot contain modules or "
      "interfaces, and cannot refer to hierarchical signals portably. The "
      "only bridge is a **virtual interface**: a class member that holds a "
      "handle to an interface instance, assigned once at time 0 by the "
      "static top module.")
    tbl(["Component", "Responsibility", "SV features used", "UVM class"],
        [["transaction", "One unit of stimulus: operation + data",
          "class, rand, enum, $urandom", "uvm_sequence_item"],
         ["generator", "Creates a stream of transactions",
          "class, mailbox put, loop", "uvm_sequence + uvm_sequencer"],
         ["driver", "Transaction -> pin wiggles on the clock",
          "virtual interface, NBA, @(posedge)", "uvm_driver #(REQ)"],
         ["monitor", "Pins -> observed items, never drives",
          "virtual interface sampling, mailbox", "uvm_monitor + analysis port"],
         ["scoreboard", "Predicts expected results, compares",
          "queue as reference model, !==", "uvm_scoreboard"],
         ["environment", "Builds and connects, runs threads",
          "constructors, fork/join_none, wait", "uvm_env"],
         ["test", "Chooses configuration and scenario",
          "inheritance, virtual methods", "uvm_test"]],
        widths=[16, 32, 30, 22], bold_first=True,
        caption="Table 25.1 - Roles in a layered testbench and their UVM equivalents.")
    box("key", "Why layers pay off",
        "Each layer changes for a different reason. A new protocol changes the "
        "driver and monitor only; a new scenario changes the generator or test "
        "only; a spec change to the data path changes the reference model only. "
        "The monitor and scoreboard never depend on the stimulus, so the same "
        "checking works for directed, random and replayed traffic - and for "
        "traffic from a neighbouring block when the environment is reused at "
        "SoC level with the driver switched off (a passive agent).")

    # ------------------------------------------------------------------
    h2("The design under test")
    p("The DUT is a 4-entry, 8-bit synchronous FIFO with a "
      "first-word-fall-through read port: `rdata` always shows the oldest "
      "entry, and `pop` removes it at the clock edge. A write is accepted "
      "when `push && !full`; a read when `pop && !empty`; both may happen in "
      "the same cycle. A compile-time macro `BUG` plants a realistic defect "
      "in the write enable, which we will use later.")
    code(r"""// sync_fifo.sv - DUT: synchronous FIFO, first-word-fall-through read port
module sync_fifo #(parameter int W = 8, parameter int D = 4) (
  input  logic                 clk, rst_n,
  input  logic                 push, pop,
  input  logic [W-1:0]         wdata,
  output logic [W-1:0]         rdata,
  output logic                 full, empty,
  output logic [$clog2(D):0]   count
);
  logic [W-1:0]           mem [D];
  logic [$clog2(D)-1:0]   wp, rp;
  logic                   do_push, do_pop;

`ifdef BUG
  assign do_push = push && !full && !pop;   // BUG: write lost on simultaneous push+pop
`else
  assign do_push = push && !full;
`endif
  assign do_pop  = pop && !empty;

  always_ff @(posedge clk)                   // storage: no reset needed
    if (do_push) mem[wp] <= wdata;

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      wp <= '0;  rp <= '0;  count <= '0;
    end else begin
      if (do_push) wp <= wp + 1'b1;          // D is a power of 2: pointers wrap
      if (do_pop)  rp <= rp + 1'b1;
      unique case ({do_push, do_pop})
        2'b10:   count <= count + 1'b1;
        2'b01:   count <= count - 1'b1;
        default: ;                         // 00 or 11: occupancy unchanged
      endcase
    end

  assign rdata = mem[rp];
  assign full  = (count == ($clog2(D)+1)'(D));
  assign empty = (count == '0);
endmodule""", "sync_fifo.sv - lint-clean under verilator --lint-only -Wall. The size "
       "cast in the full comparison avoids a WIDTHEXPAND warning against the "
       "32-bit parameter D.")
    p("Note the language details that keep this lint-clean and synthesizable: "
      "`count` is one bit wider than the pointers so that it can represent "
      "D; the occupancy update uses a `unique case` on the two enables "
      "rather than `count + do_push - do_pop` (legal, and correct, but it "
      "mixes 1-bit and 3-bit operands and draws width warnings); and the "
      "storage array has no reset, which is what you want for a RAM-like "
      "structure in an ASIC (Chapter 11). The FIFO's micro-architecture is "
      "treated in depth in the companion RTL Design guide; here it is just a "
      "target.")

    # ------------------------------------------------------------------
    h2("The interface and the virtual interface")
    code(r"""// fifo_if.sv - the pin-level boundary between the class world and the DUT
interface fifo_if #(parameter int W = 8, parameter int D = 4) (input logic clk);
  logic              rst_n;
  logic              push, pop;
  logic [W-1:0]      wdata, rdata;
  logic              full, empty;
  logic [$clog2(D):0] count;
  modport dut (input clk, rst_n, push, pop, wdata, output rdata, full, empty, count);
  modport tb  (input clk, rdata, full, empty, count, output rst_n, push, pop, wdata);
endinterface""", "fifo_if.sv - one bundle of signals, instantiated once in the top module.")
    p("Inside the testbench package the interface is referred to only "
      "through a type: `typedef virtual fifo_if vif_t;`. A virtual "
      "interface variable is a __reference__ - it holds nothing until the "
      "top module passes the instance `bus` into the test constructor, and "
      "from then on `vif.push <= 1` in a class drives the real signal of "
      "that instance. The rules (IEEE 1800-2017 25.9) are: the virtual "
      "interface type must match the instance, including parameter values; "
      "an uninitialised virtual interface is `null` and dereferencing it is "
      "a run-time fatal error; and assignments through it obey the normal "
      "rules for the target (variables may be assigned procedurally with "
      "`=` or `<=`; nets may not).")
    box("warn", "PITFALL (portability): parameterized virtual interfaces",
        "`typedef virtual fifo_if #(W, D) vif_t;` is legal SystemVerilog, and "
        "commercial simulators accept it. Verilator 5.020 crashed with an "
        "internal fault on exactly that line while this chapter was being "
        "written. The portable workaround used here is to give the interface "
        "default parameter values that match the instance and declare "
        "`virtual fifo_if` without a parameter list, which denotes the default "
        "specialization. On large projects the usual alternative is an "
        "interface without parameters whose widths come from a package.")

    # ------------------------------------------------------------------
    h2("Transactions, and where the constraints would go")
    p("The transaction is the unit of communication between the upper "
      "layers. It carries an operation and a data byte, plus an id for "
      "debug. The members are declared `rand` so that the class is ready for "
      "a constraint solver, but because Verilator 5.020 ignores constraints "
      "(it compiles `randomize()` yet does not honour `constraint` blocks) "
      "this chapter fills the fields with `$urandom_range` and weights "
      "chosen by the test.")
    code(r"""  typedef enum bit [1:0] {IDLE, PUSH, POP, BOTH} op_e;

  class fifo_txn;
    rand op_e          op;
    rand bit [W-1:0]   data;
    int                id;
    // Constraints would go here (ignored by Verilator 5.020, so we use $urandom):
    //   constraint c_op { op dist {PUSH := push_w, POP := pop_w, BOTH := 2, IDLE := 1}; }
    function void rand_fill(int push_w, int pop_w);
      int r = $urandom_range(push_w + pop_w + 2, 0);   // weights + BOTH(2) + IDLE(1)
      if      (r < push_w)            op = PUSH;
      else if (r < push_w + pop_w)    op = POP;
      else if (r < push_w + pop_w + 2) op = BOTH;
      else                            op = IDLE;
      data = W'($urandom);
    endfunction
    function string sprint();
      return $sformatf("#%0d %s 0x%02h", id, op.name(), data);
    endfunction
  endclass""", "tb_pkg.sv (excerpt) - the transaction as run. $urandom_range(max, min) "
       "returns an unsigned value in [min:max] inclusive.")
    p("With a constraint solver (VCS, Xcelium, Questa, Riviera-PRO), the same "
      "intent is expressed declaratively and the manual weighting code "
      "disappears. The knobs become non-random members that the test "
      "sets before calling `randomize()`:")
    code(r"""class fifo_txn;                          // constrained version - commercial simulator
  rand op_e        op;
  rand bit [7:0]   data;
  int unsigned     push_w = 3, pop_w = 3; // knobs, set by the test (not rand)
  constraint c_op   { op dist { PUSH := push_w, POP := pop_w, BOTH := 2, IDLE := 1 }; }
  constraint c_data { op == IDLE -> data == 0; }   // keep idle cycles tidy in waves
endclass
// generator:  fifo_txn t = new();  t.push_w = 6;
//             if (!t.randomize()) $fatal(1, "randomize failed");
//             if (!t.randomize() with { op != IDLE; }) ...   // inline constraint""",
         "Not run: constraint solving needs a commercial simulator (Chapter 19). "
         "dist weights may be non-constant expressions of state variables.")
    box("tip", "Randomness you can reproduce",
        "$urandom in a class is seeded from the thread that constructs it and "
        "the simulator's global seed, so a failing run is reproducible by "
        "re-running with the same seed: +verilator+seed+N for Verilator, "
        "+ntb_random_seed=N (VCS), -svseed N (Xcelium), -sv_seed N (Questa). "
        "Always print the seed at the start of a regression test. Never use "
        "$random for stimulus in new code: it is signed, and without an explicit "
        "seed argument all calls share one global seed, so adding a call "
        "anywhere changes every later value (no random stability, Chapter 27).")

    # ------------------------------------------------------------------
    h2("The generator and mailboxes")
    code(r"""  class generator;
    mailbox #(fifo_txn) out;
    int n = 20, push_w = 3, pop_w = 3;
    function new(mailbox #(fifo_txn) out);  this.out = out;  endfunction
    task run();
      for (int i = 0; i < n; i++) begin
        fifo_txn t = new();
        t.id = i;
        t.rand_fill(push_w, pop_w);     // with constraints: if (!t.randomize()) $fatal;
        if (i < 3) $display("GEN: %s", t.sprint());
        out.put(t);                     // blocks when the bounded mailbox is full
      end
    endtask
  endclass""", "tb_pkg.sv (excerpt) - the generator.")
    p("Two details matter. First, a **new object is constructed for every "
      "item** (`fifo_txn t = new();` inside the loop body, which is an "
      "automatic scope because a class method is automatic). Re-using one "
      "handle and re-randomizing it is a classic bug: the mailbox stores "
      "handles, not copies, so every queued entry would point at the same "
      "object and the driver would see the last values N times. Second, the "
      "mailbox is **parameterized** (`mailbox #(fifo_txn)`), so a `put` of "
      "the wrong type is a compile error instead of a run-time surprise.")
    tbl(["Method", "Blocks?", "Behaviour"],
        [["new(bound)", "-", "bound 0 (default) = unbounded; bound N = at most N items"],
         ["put(item)", "Yes, if full", "Append in FIFO order"],
         ["get(ref item)", "Yes, if empty", "Remove the oldest item"],
         ["peek(ref item)", "Yes, if empty", "Copy the oldest handle, do not remove"],
         ["try_put / try_get / try_peek", "No", "Return 1 on success, 0 otherwise"],
         ["num()", "No", "Current number of items (a snapshot; may change at once)"]],
        widths=[30, 18, 52], bold_first=True,
        caption="Table 25.2 - std::mailbox methods (IEEE 1800-2017 15.4).")
    p("The environment gives `gen2drv` a bound of 2. The generator can "
      "therefore run at most two items ahead of the driver, which keeps "
      "memory bounded, keeps the generator's `$display` roughly aligned with "
      "what is on the pins, and - more importantly - makes it possible for a "
      "__reactive__ generator to base the next item on the current DUT "
      "state. UVM reaches the same effect with the sequence/driver "
      "handshake (`get_next_item`/`item_done`), which is effectively a "
      "mailbox of depth one.")

    # ------------------------------------------------------------------
    h2("The driver")
    code(r"""  class driver;
    vif_t vif;
    mailbox #(fifo_txn) in;
    int n_driven;
    function new(vif_t vif, mailbox #(fifo_txn) in);
      this.vif = vif;  this.in = in;
    endfunction
    task reset();
      vif.rst_n <= 0;  vif.push <= 0;  vif.pop <= 0;  vif.wdata <= '0;
      repeat (2) @(posedge vif.clk);
      vif.rst_n <= 1;
    endtask
    task run();
      forever begin
        fifo_txn t;
        in.get(t);
        @(posedge vif.clk);
        vif.push  <= t.op inside {PUSH, BOTH};
        vif.pop   <= t.op inside {POP, BOTH};
        vif.wdata <= t.data;
        n_driven++;
      end
    endtask
  endclass""", "tb_pkg.sv (excerpt) - the driver: one transaction per clock cycle.")
    p("The driver waits for a rising edge and then updates the interface "
      "with **nonblocking** assignments. That is the key to a race-free "
      "testbench without clocking blocks: at a given edge, the DUT's "
      "`always_ff` blocks and the monitor all wake up in the Active region "
      "and read the __old__ values of `push`, `pop` and `wdata`; the "
      "driver's new values only land in the NBA region of that same time "
      "step, exactly like the output of a flip-flop. Had the driver used "
      "blocking `=`, whether the DUT saw the old or new value at that edge "
      "would depend on which process the simulator happened to run first "
      "(Chapter 5).")
    box("expert", "Clocking blocks: the industrial version of the same idea",
        "Production drivers usually go through a clocking block "
        "(`vif.cb.push <= ...; @(vif.cb);`) with an output skew, and monitors "
        "sample through it with an input skew (`#1step` by default, i.e. the "
        "value just before the edge in the Preponed region). This makes the "
        "sampling point explicit and independent of process order, and is "
        "what a UVM agent normally uses (Chapter 21). Clocking-block support "
        "still varies between tools, so this chapter uses the equivalent "
        "'drive with NBA after the edge, sample at the edge' discipline, "
        "which is race-free for a single synchronous clock and portable.")

    # ------------------------------------------------------------------
    h2("The monitor")
    code(r"""  class monitor;
    vif_t vif;
    mailbox #(obs_item) out;
    int n_push_full, n_pop_empty;
    function new(vif_t vif, mailbox #(obs_item) out);
      this.vif = vif;  this.out = out;
    endfunction
    task run();
      forever begin
        @(posedge vif.clk);
        if (vif.rst_n) begin            // sample pre-edge values: what the DUT saw
          if (vif.pop && !vif.empty) send(0, vif.rdata);
          if (vif.push && !vif.full) send(1, vif.wdata);
          if (vif.push &&  vif.full) n_push_full++;    // poor man's coverage
          if (vif.pop  &&  vif.empty) n_pop_empty++;
        end
      end
    endtask
    function void send(bit w, bit [W-1:0] d);
      obs_item o = new();
      o.is_write = w;  o.data = d;
      void'(out.try_put(o));            // unbounded mailbox: never fails
    endfunction
  endclass""", "tb_pkg.sv (excerpt) - the monitor. obs_item is a two-field class "
       "{bit is_write; bit [W-1:0] data;}.")
    p("The monitor is completely passive: it reads the interface and never "
      "drives it. It applies the **protocol** rule - a write happens when "
      "`push && !full` at a clock edge - which comes from the interface "
      "specification, not from the RTL. That independence is what allows it "
      "to detect a DUT that __claims__ to accept a write and then loses it. "
      "Note also the order: the read is reported before the write of the "
      "same edge, because for a first-word-fall-through FIFO a simultaneous "
      "push and pop must return the __old__ head. The monitor is a function "
      "of pin values only, so it is also correct when the DUT is driven by "
      "some other block in a larger system.")
    p("The two counters are a stand-in for functional coverage (Chapter 23), "
      "which Verilator does not implement. They answer the question every "
      "passing test must answer: did we actually exercise the interesting "
      "cases - here, pushing into a full FIFO and popping an empty one?")

    # ------------------------------------------------------------------
    h2("The scoreboard and reference model")
    code(r"""  class scoreboard;
    mailbox #(obs_item) in;
    bit [W-1:0] model[$];               // reference model: a queue
    int n_wr, n_rd, n_err;
    function new(mailbox #(obs_item) in);  this.in = in;  endfunction
    task run();
      forever begin
        obs_item o;
        in.get(o);
        if (o.is_write) begin
          model.push_back(o.data);  n_wr++;
        end else begin
          bit [W-1:0] exp;
          n_rd++;
          if (model.size() == 0) error($sformatf("read 0x%02h from empty model", o.data));
          else begin
            exp = model.pop_front();
            if (o.data !== exp)
              error($sformatf("data mismatch: got 0x%02h exp 0x%02h", o.data, exp));
          end
        end
      end
    endtask
    function void error(string msg);
      n_err++;
      if (n_err <= 3) $display("[%0t] SCB ERROR: %s", $time, msg);
    endfunction
    function void check_final(int unsigned dut_count);   // end-of-test check
      if (dut_count != model.size())
        error($sformatf("final occupancy: DUT %0d model %0d", dut_count, model.size()));
    endfunction
    function void report();
      $display("SCB: writes=%0d reads=%0d left_in_model=%0d errors=%0d",
               n_wr, n_rd, model.size(), n_err);
      if (n_err == 0) $display("*** TEST PASSED ***");
      else            $display("*** TEST FAILED ***");
    endfunction
  endclass""", "tb_pkg.sv (excerpt) - scoreboard with a queue-based reference model.")
    p("A FIFO's reference model is a queue, which is why SystemVerilog "
      "queues (`[$]` with `push_back`/`pop_front`, Chapter 13) are the most "
      "used data structure in scoreboards. For a more complex DUT the model "
      "might be a function, a transaction-level class, or a C model called "
      "through DPI (Chapter 24). Three details are worth copying:")
    bul(["The comparison uses `!==`, not `!=`. If the DUT returns X (an "
         "unwritten RAM location, an uninitialised pointer), `!=` yields X, "
         "the `if` takes the false branch, and the error is silently missed "
         "(Chapter 27). `!==` compares all four states.",
         "Errors are counted but only the first few are printed. After the "
         "first mismatch a FIFO is usually out of step, and 500 follow-on "
         "messages hide the one that matters.",
         "There is an **end-of-test check** (`check_final`): data still in "
         "the model must also be in the DUT. Without it a DUT that drops the "
         "last few writes passes whenever the test ends before they would "
         "have been read."])

    # ------------------------------------------------------------------
    h2("The environment: construction, threads and end of test")
    code(r"""  class env;
    vif_t vif;
    generator  gen;   driver drv;   monitor mon;   scoreboard scb;
    mailbox #(fifo_txn) gen2drv;
    mailbox #(obs_item) mon2scb;
    function new(vif_t vif);
      this.vif = vif;
      gen2drv = new(2);                 // bounded: generator runs just ahead
      mon2scb = new();                  // unbounded
      gen = new(gen2drv);
      drv = new(vif, gen2drv);
      mon = new(vif, mon2scb);
      scb = new(mon2scb);
    endfunction
    task run();
      drv.reset();
      fork                              // long-lived component threads
        drv.run();
        mon.run();
        scb.run();
      join_none
      gen.run();                        // returns when all items are in the mailbox
      wait (drv.n_driven == gen.n);     // end-of-test: all stimulus applied
      @(posedge vif.clk);
      vif.push <= 0;  vif.pop <= 0;
      repeat (3) @(posedge vif.clk);    // drain: let the monitor/scoreboard catch up
      disable fork;                     // kill driver, monitor, scoreboard
      scb.check_final(int'(vif.count));
      $display("MON: push-while-full=%0d pop-while-empty=%0d",
               mon.n_push_full, mon.n_pop_empty);
      scb.report();
    endtask
  endclass""", "tb_pkg.sv (excerpt) - the environment builds, connects and orchestrates.")
    p("The constructor is the **build and connect** step: it creates both "
      "mailboxes and hands the same mailbox handle to its producer and its "
      "consumer. `run()` is the **run** step, and it shows the standard "
      "fork/join pattern for testbench components:")
    bul(["Components whose `run()` loops `forever` (driver, monitor, "
         "scoreboard) are launched with `fork ... join_none`: the parent "
         "continues immediately and the children run as independent "
         "processes.",
         "The finite activity - the generator - runs in the parent thread, "
         "so its return marks 'all stimulus created'.",
         "**End of test** is a condition, not a delay: wait until the driver "
         "has applied every item, idle the inputs, wait a few drain cycles "
         "for in-flight results, then stop the forever-threads with `disable "
         "fork` and run the final checks. A fixed `#10000` would be either "
         "too short (false pass - checks never ran) or too long (wasted "
         "simulation), and silently wrong when the test length changes.",
         "The final checks and the report come __after__ the threads are "
         "stopped, so nothing changes the scoreboard state while it is being "
         "summarized."], ordered=True)
    diagram([
        "  time ->   reset    |<------------- run ------------->|<- drain ->| report",
        "  parent    drv.reset  fork..join_none  gen.run() ....  wait  3 clk  disable fork",
        "  driver                 get / drive / get / drive ...........X",
        "  monitor                sample every posedge .........................X",
        "  scoreboard             get / compare .................................X",
    ], "Figure 25.2 - Thread timeline of env.run(). X marks where disable fork "
       "terminates the forever loops.")
    box("warn", "PITFALL: disable fork kills more than you think",
        "`disable fork` terminates __all__ active descendants of the calling "
        "process, not just those created by the most recent fork. If a test "
        "had launched, say, a watchdog thread earlier from the same initial "
        "block, it would die too. The defensive idiom isolates the children "
        "in their own process: `fork begin fork a(); b(); join_none; ...; "
        "disable fork; end join`. UVM avoids the issue by ending phases with "
        "objections and killing only the run-phase processes it created. The "
        "alternative - `process` handles obtained with `process::self()` "
        "and `p.kill()` - gives precise control (Chapter 20).")

    # ------------------------------------------------------------------
    h2("Tests and the top module")
    code(r"""  class base_test;
    env e;
    function new(vif_t vif);  e = new(vif);  endfunction
    virtual function void configure();  endfunction
    task run();
      configure();
      $display("TEST %s: %0d items, push_w=%0d pop_w=%0d",
               name(), e.gen.n, e.gen.push_w, e.gen.pop_w);
      e.run();
    endtask
    virtual function string name();  return "base_test";  endfunction
  endclass

  class fill_test extends base_test;     // push-heavy: reaches full and overflow
    function new(vif_t vif);  super.new(vif);  endfunction
    virtual function void configure();
      e.gen.n = 200;  e.gen.push_w = 6;  e.gen.pop_w = 2;
    endfunction
    virtual function string name();  return "fill_test";  endfunction
  endclass
endpackage""", "tb_pkg.sv (end) - a test is a configuration of the environment, "
       "specialised by overriding virtual methods.")
    code(r"""// top.sv - static world: clock, interface, DUT; then hand the vif to the test
module top;
  import tb_pkg::*;
  logic clk = 0;
  always #5 clk = ~clk;

  fifo_if bus (clk);                     // default W=8, D=4 matches vif_t
  sync_fifo #(.W(W), .D(D)) dut (
    .clk(clk), .rst_n(bus.rst_n), .push(bus.push), .pop(bus.pop), .wdata(bus.wdata),
    .rdata(bus.rdata), .full(bus.full), .empty(bus.empty), .count(bus.count));

  initial begin
    string    tname;
    base_test t;
    if (!$value$plusargs("TEST=%s", tname)) tname = "base_test";
    case (tname)                         // a hand-made "factory" (see Chapter 26)
      "fill_test": begin fill_test f = new(bus); t = f; end
      default:     t = new(bus);
    endcase
    t.run();
    $finish;
  end
endmodule""", "top.sv - the only module in the testbench.")
    p("The test is chosen at run time with a plusarg, so one compiled "
      "executable runs the whole regression. The base-class handle `t` can "
      "hold a `fill_test`, and because `configure()` and `name()` are "
      "`virtual`, `t.run()` calls the derived versions - polymorphism doing "
      "real work. The `case` statement is a hand-written factory: it maps a "
      "string to a constructor. Adding a test means editing it, which is "
      "exactly the coupling UVM's factory removes (Chapter 26). The DUT "
      "ports are connected to interface members individually because the "
      "FIFO is written with plain ports, as most IP is; a DUT with an "
      "interface port would take `bus.dut` directly.")

    # ------------------------------------------------------------------
    h2("Building and running")
    code(r"""FL="--binary --timing -Wall -Wno-fatal"
FL="$FL -Wno-DECLFILENAME -Wno-VARHIDDEN -Wno-UNUSEDSIGNAL -Wno-UNDRIVEN"
verilator $FL --top-module top sync_fifo.sv fifo_if.sv tb_pkg.sv top.sv -o Vtop
./obj_dir/Vtop                          # base_test
./obj_dir/Vtop +TEST=fill_test
./obj_dir/Vtop +verilator+seed+7        # a different random stream""",
         "Build and run with Verilator 5.020. File order matters: the interface "
         "before the package that names it, the package before the module that "
         "imports it.")
    p("The waived warnings are testbench noise, not design problems: "
      "`VARHIDDEN` fires on every constructor argument named like the member "
      "it initialises (`this.vif = vif`), `UNDRIVEN`/`UNUSEDSIGNAL` fire on "
      "interface signals that are driven or read only from classes through "
      "a virtual interface, which Verilator's static analysis cannot see. "
      "The one remaining warning, `BLKSEQ` on `always #5 clk = ~clk`, is "
      "harmless for a clock generator. Here is the real output:")
    out(r"""TEST base_test: 20 items, push_w=3 pop_w=3
GEN: #0 IDLE 0x9c
GEN: #1 PUSH 0xe4
GEN: #2 POP 0xbc
MON: push-while-full=0 pop-while-empty=6
SCB: writes=9 reads=9 left_in_model=0 errors=0
*** TEST PASSED ***
- top.sv:21: Verilog $finish""", "Verilator 5.020: ./obj_dir/Vtop (base_test, default seed).")
    out(r"""TEST fill_test: 200 items, push_w=6 pop_w=2
GEN: #0 POP 0x9c
GEN: #1 POP 0xe4
GEN: #2 PUSH 0xbc
MON: push-while-full=72 pop-while-empty=5
SCB: writes=76 reads=73 left_in_model=3 errors=0
*** TEST PASSED ***
- top.sv:21: Verilog $finish""", "Verilator 5.020: ./obj_dir/Vtop +TEST=fill_test.")
    out(r"""TEST base_test: 20 items, push_w=3 pop_w=3
GEN: #0 BOTH 0xff
GEN: #1 POP 0x02
GEN: #2 BOTH 0x28""", "Verilator 5.020: first lines with +verilator+seed+7 - "
       "a different, reproducible stream.")
    p("Read the coverage line before you believe the PASS. The base test "
      "never pushed into a full FIFO (`push-while-full=0`), so it says "
      "nothing about overflow protection; only `fill_test` exercised it (72 "
      "times). The fill test also ends with three entries in the FIFO, and "
      "the end-of-test check confirmed that the DUT's `count` agreed with "
      "the model.")

    # ------------------------------------------------------------------
    h2("Catching a bug")
    p("Now compile the same testbench against the defective RTL by defining "
      "`BUG`, which drops a write whenever `pop` is asserted in the same "
      "cycle. This is a realistic bug: it passes every directed test that "
      "pushes a batch and then pops it, because those never overlap push "
      "and pop.")
    code(r"""verilator $FL -DBUG --Mdir obj_bug --top-module top sync_fifo.sv fifo_if.sv \
          tb_pkg.sv top.sv -o Vtop
./obj_bug/Vtop
for s in 1 2 3 4 5; do ./obj_bug/Vtop +verilator+seed+$s | grep -E "SCB:|\*\*\*"; done""",
         "Same testbench, buggy DUT.")
    out(r"""TEST base_test: 20 items, push_w=3 pop_w=3
GEN: #0 IDLE 0x9c
GEN: #1 PUSH 0xe4
GEN: #2 POP 0xbc
[95] SCB ERROR: data mismatch: got 0xe1 exp 0x53
[155] SCB ERROR: data mismatch: got 0x58 exp 0xe1
[255] SCB ERROR: final occupancy: DUT 0 model 6
MON: push-while-full=0 pop-while-empty=12
SCB: writes=9 reads=3 left_in_model=6 errors=3
*** TEST FAILED ***
- top.sv:21: Verilog $finish""", "Verilator 5.020: ./obj_bug/Vtop - the scoreboard catches "
       "the lost writes three different ways.")
    out(r"""SCB: writes=6 reads=3 left_in_model=3 errors=1
*** TEST FAILED ***
SCB: writes=11 reads=6 left_in_model=5 errors=7
*** TEST FAILED ***
SCB: writes=12 reads=5 left_in_model=7 errors=4
*** TEST FAILED ***
SCB: writes=8 reads=6 left_in_model=2 errors=4
*** TEST FAILED ***
SCB: writes=10 reads=5 left_in_model=5 errors=1
*** TEST FAILED ***""", "Verilator 5.020: five seeds, five failures.")
    p("Look at how the failure presents. The monitor recorded 9 writes "
      "because 9 times the pins satisfied `push && !full`; the DUT kept only "
      "some of them. The data comparison fails as soon as a lost entry "
      "should have been read, and the end-of-test check fails because the "
      "DUT reports 0 entries while the model holds 6. Note too that the "
      "first error is at 95 ns, not at the edge where the write was lost: a "
      "scoreboard detects the __symptom__. The debug step is to find the "
      "first lost write in the waveform (Verilator `--trace`, then GTKWave "
      "or Surfer) and walk back to `do_push`.")
    box("intuit", "Why random found it and a directed test would not",
        "The bug needs push and pop in the same cycle while the FIFO is "
        "non-empty. Random stimulus with a BOTH weight produces that "
        "combination constantly; a hand-written 'write four, read four' test "
        "never does. This is the whole argument for constrained-random "
        "verification in one example - and also the argument for coverage: "
        "if a regression shows the (push, pop, not-empty) cross has never "
        "been hit, the PASS is worthless.")
    box("key", "Interview insight: what makes a scoreboard trustworthy",
        "(1) The model is written from the specification, not copied from "
        "the RTL. (2) The monitor derives transactions from pins using the "
        "protocol, never from DUT internals. (3) Comparisons are 4-state "
        "(!==). (4) There is an end-of-test check for outstanding items. "
        "(5) The test proves it can fail - running it against a planted bug, "
        "as here, is called __mutation__ or __fault seeding__ and is the "
        "cheapest sanity check of a new environment.")

    # ------------------------------------------------------------------
    h2("From here to a production environment")
    tbl(["What is missing here", "Language feature", "Where covered"],
        [["Declarative stimulus", "constraint, dist, inline with, pre/post_randomize",
          "Ch. 19"],
         ["Measured completeness", "covergroup, coverpoint, cross", "Ch. 23"],
         ["Cycle-level protocol checks in the interface",
          "concurrent assertions (assert property)", "Ch. 22"],
         ["Race-free sampling with skews", "clocking blocks, program blocks", "Ch. 21"],
         ["Test selection without editing top.sv", "static registry, factory", "Ch. 26"],
         ["Configuration without long constructor lists",
          "parameterized class with static associative array (config_db)", "Ch. 26"],
         ["Clean, cooperative end of test", "objections over phases", "Ch. 26"],
         ["Broadcast to several subscribers", "analysis ports calling write()", "Ch. 26"]],
        widths=[36, 44, 20], bold_first=True,
        caption="Table 25.3 - The distance between this chapter and an industrial testbench.")
    p("Everything in the right-hand column is a language feature you "
      "already know. A UVM environment for this FIFO would have the same "
      "seven classes, with base classes supplied by the library.")

    h2("Summary")
    bul(["A layered testbench separates the static world (top module, "
         "interface, DUT) from dynamic class objects; a virtual interface is "
         "the only bridge.",
         "Transactions flow downward through a bounded mailbox to the "
         "driver; observed items flow upward from a passive monitor through "
         "a second mailbox to the scoreboard.",
         "Drive with nonblocking assignments after the clock edge (or a "
         "clocking block) and sample at the edge; that makes the testbench "
         "race-free with respect to the DUT's flip-flops.",
         "The scoreboard's reference model is written from the spec; for a "
         "FIFO it is a queue. Compare with `!==` and check for outstanding "
         "items at the end of the test.",
         "Long-lived components start with `fork ... join_none`; the test "
         "ends on a condition (all items driven, drain), not a fixed delay, "
         "and `disable fork` kills every descendant of the calling process.",
         "Verilator 5.020 ran the whole environment; randomization used "
         "`$urandom_range` because it ignores constraints; a parameterized "
         "virtual interface typedef crashed it, so default parameters were "
         "used instead.",
         "A planted bug (write lost on simultaneous push and pop) was caught "
         "on every seed by random stimulus, while a simple directed test "
         "would have missed it."])

    h2("Exercises")
    bul(["Add a `peek`-based check to the monitor: whenever `empty` is 0, "
         "`rdata` must equal the head of the model queue even when no pop "
         "happens. Which extra class of bug does this catch?",
         "Replace the unbounded `mon2scb` mailbox by direct calls: give the "
         "monitor a scoreboard handle and call `scb.write(o)` from "
         "`send()`. What does this gain and lose? (Hint: this is how a UVM "
         "analysis port works.)",
         "Plant a second bug: `full` asserted at `count == D-1`. Does the "
         "current scoreboard detect it? If not, add the check that does, and "
         "decide whether it belongs in the monitor, the scoreboard or an "
         "assertion in the interface.",
         "Make the generator reactive: when the monitor has seen 10 "
         "consecutive cycles with `full` high, bias the next 20 items toward "
         "POP. Which component needs a handle to which, and how do you avoid "
         "a race on the shared counter?",
         "Rewrite `disable fork` using `process` handles: store the three "
         "component processes in a queue and `kill()` them explicitly. Show "
         "a situation in which the two versions behave differently.",
         "Port the testbench to a commercial simulator (EDA Playground "
         "offers free access) and replace `rand_fill` with the constrained "
         "`fifo_txn` shown earlier. Verify that the op distribution matches "
         "the weights by counting 10,000 items."], ordered=True)


# =============================================================================
#                 Chapter 26 - How UVM uses the language
# =============================================================================
def ch26():
    chapter("How UVM Uses the Language")
    p("The Universal Verification Methodology (UVM, standardised as IEEE "
      "1800.2) is not a language extension. It is a class library - a "
      "package called `uvm_pkg` plus a file of macros, `uvm_macros.svh` - "
      "written entirely in IEEE 1800 SystemVerilog. Every mechanism that "
      "makes UVM look magical to a newcomer (the factory, `type_id::create`, "
      "the configuration database, phases, objections, sequences, TLM "
      "ports) is built from a handful of features you already know: class "
      "inheritance and virtual methods, parameterized classes, static "
      "members, associative arrays, macros, and processes. This chapter maps "
      "each mechanism to the feature beneath it, gives a complete UVM "
      "skeleton for the FIFO of Chapter 25, and ends with a 120-line "
      "'mini UVM' in plain SystemVerilog that runs on Verilator and "
      "demystifies the factory, config_db, phasing and objections.")
    box("note", "Tool support for this chapter",
        "UVM needs a simulator that supports the full class, randomization and "
        "process feature set: VCS, Xcelium, Questa and Riviera-PRO ship UVM "
        "pre-compiled, and EDA Playground lets you run it in a browser. "
        "Verilator 5.020 cannot compile the UVM library, and Icarus cannot "
        "either, so the UVM code here is shown without output. The mini-UVM "
        "model at the end of the chapter was run with Verilator 5.020.")

    # ------------------------------------------------------------------
    h2("The map: UVM mechanism -> SystemVerilog feature")
    tbl(["UVM mechanism", "SystemVerilog feature underneath", "Book chapter"],
        [["uvm_object / uvm_component hierarchy", "class inheritance, virtual methods, "
          "virtual (abstract) classes", "18"],
         ["uvm_driver #(REQ,RSP), TLM ports, uvm_config_db #(T)",
          "parameterized classes (type parameters)", "18"],
         ["factory, type_id::create, overrides",
          "static members, singleton proxies, associative arrays keyed by string, "
          "$cast", "13, 18"],
         ["uvm_component_utils and the other utility macros",
          "text macros with argument stringification", 
          "8"],
         ["config_db, resources", "parameterized class with static associative arrays",
          "13, 18"],
         ["virtual interfaces via config_db", "virtual interface as a type parameter",
          "16"],
         ["phases", "virtual functions (zero-time) and virtual tasks (run phases), "
          "called by a scheduler", "6, 18"],
         ["objections", "counters + events + wait, per phase", "20"],
         ["sequences, sequencer arbitration", "tasks, fork/join, process class, "
          "semaphores/events", "20"],
         ["analysis ports", "parameterized port class calling write() on a "
          "list of subscribers", "18"],
         ["uvm_reg (RAL) backdoor", "DPI-C / VPI access by HDL path", "24"],
         ["uvm_report_* messages", "$sformatf, $display, static report server", "10"]],
        widths=[33, 50, 17], bold_first=True,
        caption="Table 26.1 - Every UVM mechanism is a SystemVerilog idiom.")

    # ------------------------------------------------------------------
    h2("Class hierarchy and polymorphism")
    diagram([
        "  uvm_void                               (virtual, empty: the common root)",
        "   +-- uvm_object                        name, copy/compare/print/pack, create()",
        "        +-- uvm_transaction",
        "        |    +-- uvm_sequence_item       your transactions",
        "        |         +-- uvm_sequence_base",
        "        |              +-- uvm_sequence #(REQ, RSP)   your sequences: body()",
        "        +-- uvm_report_object            messaging",
        "        |    +-- uvm_component           parent/children, phases, config",
        "        |         +-- uvm_driver #(REQ, RSP)",
        "        |         +-- uvm_sequencer #(REQ, RSP)",
        "        |         +-- uvm_monitor, uvm_scoreboard, uvm_agent, uvm_env",
        "        |         +-- uvm_test",
        "        +-- uvm_reg, uvm_reg_block, ...  register model (RAL)",
    ], "Figure 26.1 - The core of the UVM class tree (IEEE 1800.2).")
    p("Two branches matter. **Objects** (`uvm_object`) are transient data: "
      "transactions, sequences, configuration objects. They are created and "
      "destroyed freely and have no position in the testbench. "
      "**Components** (`uvm_component`) are the permanent structure: they "
      "are created once during the build phase, each has a parent and a "
      "hierarchical name (for example `uvm_test_top.env.agt.drv`), and they "
      "take part in phasing. The distinction is visible in their "
      "constructors: `new(string name = \"\")` for objects and `new(string "
      "name, uvm_component parent)` for components.")
    p("Polymorphism is the engine. The library holds everything through base-"
      "class handles and calls virtual methods: the phase scheduler calls "
      "`comp.build_phase(phase)` on a `uvm_component` handle and your "
      "override runs; `uvm_object::copy()` is non-virtual and calls the "
      "virtual `do_copy()`, which you override. The standard idiom inside "
      "such an override uses `$cast` to recover the derived type:")
    code(r"""class fifo_item extends uvm_sequence_item;
  rand bit push, pop;  rand bit [7:0] data;
  `uvm_object_utils(fifo_item)
  function new(string name = "fifo_item");  super.new(name);  endfunction
  virtual function void do_copy(uvm_object rhs);
    fifo_item that;
    if (!$cast(that, rhs)) `uvm_fatal("CAST", "do_copy: wrong type")
    super.do_copy(rhs);                        // copy base-class fields first
    push = that.push;  pop = that.pop;  data = that.data;
  endfunction
  virtual function bit do_compare(uvm_object rhs, uvm_comparer comparer);
    fifo_item that;
    return $cast(that, rhs) && super.do_compare(rhs, comparer) &&
           push == that.push && pop == that.pop && data == that.data;
  endfunction
  virtual function string convert2string();
    return $sformatf("push=%0b pop=%0b data=0x%02h", push, pop, data);
  endfunction
endclass""", "Not run (needs UVM). The do_* hooks are the virtual-method pattern "
       "'non-virtual public API calls virtual protected hook'.")
    box("tip", "Field macros versus do_* methods",
        "The `uvm_field_int` family of macros generates copy/compare/print "
        "code automatically, but it expands into a large generic function "
        "that is slow and hard to debug. Many companies ban field macros and "
        "require hand-written do_copy, do_compare and convert2string. Knowing "
        "that the macro only writes these methods for you makes the choice "
        "easy.")

    # ------------------------------------------------------------------
    h2("Parameterized classes: drivers, sequencers and ports")
    p("A driver must know the type of item it receives, but the library "
      "cannot know your item type in advance. The solution is a type "
      "parameter: `class uvm_driver #(type REQ = uvm_sequence_item, type RSP "
      "= REQ) extends uvm_component;`. Inside, the library declares `REQ "
      "req;` and a port `uvm_seq_item_pull_port #(REQ, RSP) seq_item_port;`. "
      "When you write `class fifo_driver extends uvm_driver #(fifo_item);` "
      "you create a __specialization__, a distinct class in which `req` has "
      "type `fifo_item`, so `req.data` compiles without a cast.")
    p("TLM ports are parameterized the same way, and one of them uses a "
      "trick worth knowing. An analysis imp is declared `uvm_analysis_imp "
      "#(fifo_obs, fifo_scoreboard)`: the second parameter is the type of "
      "the component that implements `write()`. Inside, the imp stores a "
      "handle of that type and its own `write(t)` calls `m_imp.write(t)`. "
      "The call is resolved when the specialization is elaborated, so if "
      "`fifo_scoreboard` has no `write` method the compile fails. This is "
      "'duck typing at elaboration time' through type parameters; the "
      "language did not have interface classes (Chapter 18) when the "
      "pattern was designed.")
    code(r"""// simplified from the UVM reference implementation
class uvm_analysis_port #(type T = int) extends uvm_port_base #(uvm_tlm_if_base #(T,T));
  function void write(input T t);                 // broadcast: zero time, never blocks
    uvm_tlm_if_base #(T,T) tif;
    for (int i = 0; i < this.size(); i++) begin
      tif = this.get_if(i);                       // every connected subscriber
      tif.write(t);
    end
  endfunction
endclass

class uvm_analysis_imp #(type T = int, type IMP = int)
    extends uvm_port_base #(uvm_tlm_if_base #(T,T));
  local IMP m_imp;                                // the component that owns the imp
  function new(string name, IMP imp);  super.new(name, imp, UVM_IMPLEMENTATION, 1, 1);
    m_imp = imp;
  endfunction
  function void write(input T t);  m_imp.write(t);  endfunction   // IMP must have write()
endclass""", "Not run. Simplified: the real classes add macros for the port "
       "boilerplate. Because write() is a function, analysis traffic cannot "
       "consume time.")
    p("When a component needs two analysis inputs (for example the expected "
      "and actual streams of a scoreboard), both imps would call the same "
      "`write()`. The macro `uvm_analysis_imp_decl(_exp)` (invoked with a "
      "leading backtick) solves this by declaring a new imp class, "
      "`uvm_analysis_imp_exp`, whose `write()` calls `write_exp()` - text "
      "macros generating classes, nothing more. The alternative is to "
      "instantiate `uvm_tlm_analysis_fifo #(T)` members, which contain a "
      "mailbox, and `get()` from them in the run phase.")

    # ------------------------------------------------------------------
    h2("Static registries and the factory")
    p("The factory solves the problem Chapter 25 solved with a `case` "
      "statement: create an object whose concrete type is chosen at run "
      "time, without the code that creates it knowing all the possible "
      "types. The rule in UVM is **never call new() for components or "
      "items directly; call T::type_id::create()**. That one level of "
      "indirection lets a test replace any type anywhere in the hierarchy "
      "without editing the environment.")
    p("The mechanism has three pieces:")
    bul(["A **proxy** (wrapper) class per registered type. "
         "`uvm_component_registry #(T, \"T\")` is a parameterized class; its "
         "specialization for `fifo_driver` knows how to call `new` for a "
         "`fifo_driver`. It extends the abstract `uvm_object_wrapper`, whose "
         "virtual `create_component()` it implements.",
         "A **singleton** instance of each proxy, created and registered by "
         "a static member initializer (`local static this_type me = get();` "
         "in UVM 1.2; IEEE 1800.2 releases defer the same registration to "
         "`uvm_init`). Static initialization runs before any `initial` "
         "block, so every type is registered before `run_test()` starts.",
         "The **factory** singleton, which holds associative arrays mapping "
         "type names and proxy handles to proxies, plus override tables. "
         "`create()` looks up the requested type, follows any override "
         "chain, asks the final proxy to construct the object and returns "
         "it through a base-class handle; the static `create()` in the "
         "registry then `$cast`s it back to T."], ordered=True)
    code(r"""// In a test: replace every fifo_item created anywhere by fifo_full_item
class fill_test extends base_test;
  `uvm_component_utils(fill_test)
  function new(string name, uvm_component parent);  super.new(name, parent);  endfunction
  virtual function void build_phase(uvm_phase phase);
    fifo_item::type_id::set_type_override(fifo_full_item::get_type());
    // or only under one instance path:
    // fifo_item::type_id::set_inst_override(fifo_full_item::get_type(), "env.agt.*", this);
    super.build_phase(phase);                  // overrides must precede creation
  endfunction
endclass

class fifo_full_item extends fifo_item;       // same constraint name overrides the base one
  `uvm_object_utils(fifo_full_item)
  constraint c_mix { {push, pop} dist { 2'b10 := 8, 2'b01 := 1, 2'b11 := 1 }; }
  function new(string name = "fifo_full_item");  super.new(name);  endfunction
endclass""", "Not run (needs UVM). A factory override plus constraint override by name "
       "turns the base test into a fill test without touching the sequence.")
    box("warn", "PITFALL: calling new() defeats the factory",
        "`drv = new(\"drv\", this);` compiles and works - until someone "
        "overrides fifo_driver and nothing happens, because `new` always "
        "constructs exactly the declared class. Code review rule: in UVM "
        "code, `new` appears only inside constructors (super.new) and for "
        "ports, FIFOs and covergroups, which are not factory-registered. A "
        "related pitfall: an override set __after__ the object was created "
        "has no effect, so overrides go at the top of build_phase before "
        "super.build_phase().")

    # ------------------------------------------------------------------
    h2("What the utility macros expand to")
    p("The registration code is identical for every class except the type "
      "name, which is exactly what text macros are for (Chapter 8). A "
      "simplified expansion of `uvm_component_utils(fifo_driver)`:")
    code(r"""// `uvm_component_utils(fifo_driver)   expands (simplified) to:
typedef uvm_component_registry #(fifo_driver, "fifo_driver") type_id;
static function type_id get_type();
  return type_id::get();                         // the singleton proxy
endfunction
virtual function uvm_object_wrapper get_object_type();
  return type_id::get();
endfunction
const static string type_name = "fifo_driver";
virtual function string get_type_name();
  return type_name;
endfunction""", "The type name string is produced by stringifying the macro argument "
       "(a grave accent followed by a double quote) inside the macro body. uvm_object_utils is the same with uvm_object_registry and an "
       "extra create() method.")
    tbl(["Macro", "For", "Adds"],
        [["uvm_object_utils(T)", "non-parameterized objects",
          "type_id (uvm_object_registry), get_type, get_type_name, create"],
         ["uvm_object_param_utils(T)", "parameterized objects",
          "same, but registered without a string name (by type only)"],
         ["uvm_component_utils(T)", "components", "type_id (uvm_component_registry), "
          "get_type, get_type_name"],
         ["uvm_component_param_utils(T)", "parameterized components", "type only"],
         ["uvm_*_utils_begin, uvm_field_*, uvm_*_utils_end", "objects or components",
          "above + generated copy/compare/print/pack code"],
         ["uvm_info, uvm_warning, uvm_error, uvm_fatal", "any code",
          "a verbosity check, then uvm_report_* with `__FILE__` and `__LINE__`"]],
        widths=[36, 22, 42], bold_first=True,
        caption="Table 26.2 - The common UVM macros (invoked with a leading backtick).")
    p("The parameterized variants exist because a specialization such as "
      "`my_driver #(8)` has no single name string; a stringified `T` would "
      "contain the parameter text, and different specializations must be "
      "different registry entries. Such classes can be created and "
      "overridden only by type, not by name. The reporting macros exist so "
      "that the message is formatted only if its verbosity is enabled, "
      "which keeps expensive `$sformatf` calls out of fast regressions.")

    # ------------------------------------------------------------------
    h2("config_db: a parameterized class with static storage")
    p("`uvm_config_db #(type T = int)` is a class with only static methods. "
      "Each specialization - `uvm_config_db #(int)`, `uvm_config_db "
      "#(virtual fifo_if)`, `uvm_config_db #(fifo_cfg)` - is a separate "
      "class with its own static state, which is how the database is "
      "type-safe: a value set as `int` can only be retrieved as `int`. "
      "Underneath, entries live in a global resource pool whose lookup "
      "tables are associative arrays keyed by field name, each entry "
      "carrying the scope pattern (a glob or regular expression over "
      "hierarchical names) to which it applies.")
    code(r"""static function void set(uvm_component cntxt, string inst_name, string field_name,
                         T value);
static function bit  get(uvm_component cntxt, string inst_name, string field_name,
                         inout T value);
// scope = {cntxt.get_full_name(), ".", inst_name}   (cntxt == null -> uvm_root)
uvm_config_db #(int)::set(this, "env.agt*", "is_active", UVM_PASSIVE);  // from a test
if (!uvm_config_db #(int)::get(this, "", "n_items", n)) n = 50;        // in a component""",
         "Not run. The signatures (IEEE 1800.2) and typical calls.")
    bul(["**Precedence during build:** a `set` from a component higher in the "
         "hierarchy wins over one from lower down, so the test can override "
         "what the environment configures for its children. Among sets from "
         "the same context, the last one wins.",
         "**get in build_phase:** configuration is read top-down as the tree "
         "is built, so a component's parent has already run its "
         "build_phase (and its sets) before the child reads.",
         "**Failed get:** `get` returns 0 and leaves `value` unchanged; always "
         "check the return value and either default or `uvm_fatal`.",
         "**Typos are silent:** a wrong field name or path pattern simply "
         "never matches. `+UVM_CONFIG_DB_TRACE` prints every set and get and "
         "is the first debugging step."])
    h3("Virtual interfaces through config_db")
    p("The static top module is the only place that can see the interface "
      "instance, and the driver is a class created later by the factory, so "
      "the two meet through the database, with `virtual fifo_if` as the "
      "type parameter:")
    code(r"""module tb_top;
  import uvm_pkg::*;
  logic clk = 0;  always #5 clk = ~clk;
  fifo_if bus (clk);
  sync_fifo dut (.clk, .rst_n(bus.rst_n), .push(bus.push), .pop(bus.pop),
                 .wdata(bus.wdata), .rdata(bus.rdata), .full(bus.full),
                 .empty(bus.empty), .count(bus.count));
  initial begin
    uvm_config_db #(virtual fifo_if)::set(null, "uvm_test_top.env.agt.*", "vif", bus);
    run_test();                               // test name from +UVM_TESTNAME=...
  end
endmodule
// in the driver / monitor:
//   if (!uvm_config_db #(virtual fifo_if)::get(this, "", "vif", vif))
//     `uvm_fatal("NOVIF", "no virtual interface for this agent")""",
         "Not run. The set must happen before run_test() starts the build phase.")

    # ------------------------------------------------------------------
    h2("Phases: virtual methods called by a scheduler")
    tbl(["Phase", "Kind", "Order", "Typical use"],
        [["build", "function", "top-down", "create children with type_id::create, get config"],
         ["connect", "function", "bottom-up", "connect ports: drv.seq_item_port.connect(...)"],
         ["end_of_elaboration", "function", "bottom-up", "print topology, final checks of setup"],
         ["start_of_simulation", "function", "bottom-up", "print banners, open files"],
         ["run (and 12 run-time sub-phases)", "task", "parallel",
          "drive, monitor, run sequences - the only phases that consume time"],
         ["extract", "function", "bottom-up", "gather final state from DUT and models"],
         ["check", "function", "bottom-up", "end-of-test checks (outstanding items)"],
         ["report", "function", "bottom-up", "print results"],
         ["final", "function", "top-down", "close files, $finish handling"]],
        widths=[26, 12, 14, 48], bold_first=True,
        caption="Table 26.3 - The common UVM phases.")
    p("Each phase is a virtual method of `uvm_component` with an empty "
      "default body; you override the ones you need. The scheduler walks "
      "the component tree and calls the function phases in the order shown. "
      "Build is top-down because a parent must exist - and must have run "
      "its build - before it can create its children; the others are "
      "bottom-up. For the run phase the scheduler forks one process per "
      "component, calling each `run_phase(phase)` task, and all of them run "
      "concurrently. The 12 run-time sub-phases (pre_reset, reset, "
      "post_reset, pre_configure, configure, post_configure, pre_main, main, "
      "post_main, pre_shutdown, shutdown, post_shutdown) run in sequence, "
      "in parallel with run_phase; most projects use only run_phase.")
    h3("Objections: ending a run phase")
    p("A task phase has no natural end - drivers and monitors loop forever. "
      "UVM ends it by **objection**: any component (or sequence) that has "
      "work to do calls `phase.raise_objection(this)` before starting and "
      "`phase.drop_objection(this)` when done. When the count for the phase "
      "returns to zero (after an optional drain time), the scheduler kills "
      "the run-phase processes it forked and moves on to extract. "
      "Underneath this is a counter per component that propagates up the "
      "tree, and events that the scheduler `wait`s on.")
    code(r"""class base_test extends uvm_test;
  `uvm_component_utils(base_test)
  fifo_env env;
  function new(string name, uvm_component parent);  super.new(name, parent);  endfunction
  virtual function void build_phase(uvm_phase phase);
    env = fifo_env::type_id::create("env", this);
  endfunction
  virtual task run_phase(uvm_phase phase);
    fifo_rand_seq seq = fifo_rand_seq::type_id::create("seq");
    phase.raise_objection(this, "running fifo_rand_seq");   // BEFORE any delay
    if (!seq.randomize()) `uvm_fatal("RAND", "sequence randomize failed")
    seq.start(env.agt.sqr);                                // returns when body() ends
    phase.drop_objection(this);
  endtask
endclass""", "Not run. The test owns the objection; drivers and monitors normally "
       "do not raise any.")
    box("warn", "PITFALL: the test that ends at time zero",
        "If no objection is raised by the end of the first delta cycles of "
        "the run phase, UVM ends the phase immediately and the test 'passes' "
        "having done nothing. The usual cause is a raise placed after a "
        "delay or after a wait for reset. The mini model at the end of this "
        "chapter reproduces it. The opposite bug - an objection never "
        "dropped - hangs until the global timeout (+UVM_TIMEOUT or "
        "set_timeout) fires.")

    # ------------------------------------------------------------------
    h2("Sequences and sequencer arbitration")
    p("A sequence is an object (not a component) whose virtual task "
      "`body()` generates items. `seq.start(sqr)` runs `body()` in the "
      "__caller's__ process; each item goes through a handshake with the "
      "driver, arbitrated by the sequencer:")
    diagram([
        "  sequence (body)                sequencer                    driver (run_phase)",
        "  start_item(it)  ---- wait_for_grant -->  arbitration queue",
        "                                           picks one sequence  <-- get_next_item(req)",
        "  randomize it    <---- grant ------------",
        "  finish_item(it) ---- send_request ----->  hands item over  ----> req = it",
        "                                                                    drive pins",
        "                  <---- item_done ------------------------------  item_done()",
    ], "Figure 26.2 - The sequence/sequencer/driver handshake. start_item blocks until "
       "the sequencer grants this sequence; finish_item blocks until the driver "
       "calls item_done.")
    p("Several sequences may run on one sequencer at once - typically "
      "started from a __virtual sequence__ with `fork seq_a.start(sqr); "
      "seq_b.start(sqr); join`. Each one blocks in `start_item`, the "
      "sequencer keeps a queue of waiting requests, and when the driver asks "
      "for an item it grants one according to the arbitration mode set "
      "with `sqr.set_arbitration()`: UVM_SEQ_ARB_FIFO (default, request "
      "order), UVM_SEQ_ARB_WEIGHTED, UVM_SEQ_ARB_RANDOM, UVM_SEQ_ARB_STRICT_"
      "FIFO and UVM_SEQ_ARB_STRICT_RANDOM (highest priority first), or "
      "UVM_SEQ_ARB_USER (override `user_priority_arbitration`). A sequence "
      "can take exclusive access with `lock()` (queued) or `grab()` "
      "(immediate). The language machinery is ordinary: blocking tasks, "
      "events and `wait` for the handshake, and the `process` class so that "
      "`seq.kill()` and phase ends can terminate a sequence's thread.")
    code(r"""class fifo_rand_seq extends uvm_sequence #(fifo_item);
  `uvm_object_utils(fifo_rand_seq)
  rand int unsigned n = 50;
  constraint c_n { n inside {[20:200]}; }
  function new(string name = "fifo_rand_seq");  super.new(name);  endfunction
  virtual task body();
    repeat (n) begin
      fifo_item it = fifo_item::type_id::create("it");
      start_item(it);                          // wait for grant
      if (!it.randomize()) `uvm_fatal("RAND", "item randomize failed")
      finish_item(it);                         // wait for item_done
    end
  endtask
endclass""", "Not run. Randomizing between start_item and finish_item (late "
       "randomization) lets constraints see the latest state.")

    # ------------------------------------------------------------------
    h2("The register layer (RAL) in one page")
    p("UVM's register abstraction layer models a DUT's memory-mapped "
      "registers as a tree of objects: `uvm_reg_block` contains `uvm_reg` "
      "objects, which contain `uvm_reg_field` objects, placed at addresses "
      "by a `uvm_reg_map`. Tests then write `regmodel.ctrl.enable.set(1); "
      "regmodel.ctrl.update(status);` instead of bus transactions. The "
      "language features involved are all familiar:")
    tbl(["RAL piece", "What it is in SV"],
        [["uvm_reg / uvm_reg_field", "classes with a mirrored and a desired value, "
          "access policy strings (\"RW\", \"RO\", \"W1C\", ...)"],
         ["generated register model", "thousands of lines of classes generated from "
          "IP-XACT or a spreadsheet by a script"],
         ["uvm_reg_adapter", "a class with virtual reg2bus()/bus2reg() converting "
          "generic register operations to your bus item and back"],
         ["uvm_reg_predictor #(T)", "a parameterized component with an analysis imp: "
          "updates the mirror from observed bus traffic"],
         ["frontdoor access", "a sequence run on the bus agent's sequencer"],
         ["backdoor access", "HDL-path strings resolved through DPI-C/VPI "
          "(uvm_hdl_deposit / uvm_hdl_read) - Chapter 24"],
         ["built-in sequences", "uvm_reg_hw_reset_seq, uvm_reg_bit_bash_seq, "
          "uvm_reg_access_seq: generic tests driven by the model"]],
        widths=[30, 70], bold_first=True, caption="Table 26.4 - RAL building blocks.")

    # ------------------------------------------------------------------
    h2("A compact but complete UVM environment")
    p("Here is a full UVM testbench for the FIFO of Chapter 25, using every "
      "mechanism above. It is deliberately minimal - one agent, one "
      "scoreboard, one sequence - and compiles as-is on a UVM-capable "
      "simulator together with `sync_fifo.sv` and `fifo_if.sv` from Chapter "
      "25, the `fifo_item` class shown earlier in this chapter and the "
      "`tb_top` module above. Compare it line by line with Chapter 25: the "
      "roles are the same, the plumbing is the library's.")
    code(r"""`include "uvm_macros.svh"
package fifo_uvm_pkg;
  import uvm_pkg::*;
  // fifo_item and fifo_rand_seq as shown earlier in this chapter

  class fifo_obs extends uvm_sequence_item;         // what the monitor publishes
    bit is_write;  bit [7:0] data;
    `uvm_object_utils(fifo_obs)
    function new(string name = "fifo_obs");  super.new(name);  endfunction
  endclass

  class fifo_driver extends uvm_driver #(fifo_item);
    `uvm_component_utils(fifo_driver)
    virtual fifo_if vif;
    function new(string name, uvm_component parent);  super.new(name, parent);  endfunction
    virtual function void build_phase(uvm_phase phase);
      if (!uvm_config_db #(virtual fifo_if)::get(this, "", "vif", vif))
        `uvm_fatal("NOVIF", "vif not set")
    endfunction
    virtual task run_phase(uvm_phase phase);
      vif.push <= 0;  vif.pop <= 0;
      forever begin
        seq_item_port.get_next_item(req);           // req is a fifo_item (REQ)
        @(posedge vif.clk);
        vif.push <= req.push;  vif.pop <= req.pop;  vif.wdata <= req.data;
        seq_item_port.item_done();
      end
    endtask
  endclass

  class fifo_monitor extends uvm_monitor;
    `uvm_component_utils(fifo_monitor)
    virtual fifo_if vif;
    uvm_analysis_port #(fifo_obs) ap;
    function new(string name, uvm_component parent);
      super.new(name, parent);  ap = new("ap", this);
    endfunction
    virtual function void build_phase(uvm_phase phase);
      if (!uvm_config_db #(virtual fifo_if)::get(this, "", "vif", vif))
        `uvm_fatal("NOVIF", "vif not set")
    endfunction
    virtual task run_phase(uvm_phase phase);
      forever begin
        @(posedge vif.clk);
        if (vif.rst_n) begin
          if (vif.pop  && !vif.empty) publish(0, vif.rdata);
          if (vif.push && !vif.full)  publish(1, vif.wdata);
        end
      end
    endtask
    function void publish(bit w, bit [7:0] d);
      fifo_obs o = fifo_obs::type_id::create("o");
      o.is_write = w;  o.data = d;
      ap.write(o);                                  // broadcast to all subscribers
    endfunction
  endclass""", "Not run (needs a UVM simulator). Part 1: items, driver, monitor.")
    code(r"""  class fifo_agent extends uvm_agent;
    `uvm_component_utils(fifo_agent)
    uvm_sequencer #(fifo_item) sqr;
    fifo_driver                drv;
    fifo_monitor               mon;
    function new(string name, uvm_component parent);  super.new(name, parent);  endfunction
    virtual function void build_phase(uvm_phase phase);
      super.build_phase(phase);                    // reads is_active from config_db
      mon = fifo_monitor::type_id::create("mon", this);
      if (get_is_active() == UVM_ACTIVE) begin
        sqr = uvm_sequencer #(fifo_item)::type_id::create("sqr", this);
        drv = fifo_driver::type_id::create("drv", this);
      end
    endfunction
    virtual function void connect_phase(uvm_phase phase);
      if (get_is_active() == UVM_ACTIVE) drv.seq_item_port.connect(sqr.seq_item_export);
    endfunction
  endclass

  class fifo_scoreboard extends uvm_scoreboard;
    `uvm_component_utils(fifo_scoreboard)
    uvm_analysis_imp #(fifo_obs, fifo_scoreboard) imp;
    bit [7:0] model[$];
    function new(string name, uvm_component parent);
      super.new(name, parent);  imp = new("imp", this);
    endfunction
    virtual function void write(fifo_obs o);        // called by the imp, zero time
      bit [7:0] exp;
      if (o.is_write) begin model.push_back(o.data); return; end
      if (model.size() == 0) begin `uvm_error("SCB", "read from empty FIFO") return; end
      exp = model.pop_front();
      if (o.data !== exp)
        `uvm_error("SCB", $sformatf("got 0x%02h exp 0x%02h", o.data, exp))
    endfunction
    virtual function void check_phase(uvm_phase phase);
      `uvm_info("SCB", $sformatf("%0d items left in model", model.size()), UVM_LOW)
    endfunction
  endclass

  class fifo_env extends uvm_env;
    `uvm_component_utils(fifo_env)
    fifo_agent agt;  fifo_scoreboard scb;
    function new(string name, uvm_component parent);  super.new(name, parent);  endfunction
    virtual function void build_phase(uvm_phase phase);
      agt = fifo_agent::type_id::create("agt", this);
      scb = fifo_scoreboard::type_id::create("scb", this);
    endfunction
    virtual function void connect_phase(uvm_phase phase);
      agt.mon.ap.connect(scb.imp);
    endfunction
  endclass
  // base_test and fill_test as shown earlier in this chapter
endpackage
// run: +UVM_TESTNAME=base_test  or  +UVM_TESTNAME=fill_test""",
         "Not run (needs a UVM simulator). Part 2: agent, scoreboard, environment.")
    p("Notice what is __not__ there compared to Chapter 25: no mailboxes "
      "(the sequencer handshake and the analysis port replace them), no "
      "`fork` (the phase scheduler forks the run phases), no `disable fork` "
      "or end-of-test wait (objections), no hand-written test `case` "
      "(`run_test()` creates the class named by +UVM_TESTNAME through the "
      "factory), and no constructor argument lists for the virtual "
      "interface (config_db).")

    # ------------------------------------------------------------------
    h2("Demystified: a mini UVM in plain SystemVerilog")
    p("The best way to believe that the factory, config_db and phasing are "
      "just language features is to build small versions of them. The "
      "package below implements a string-keyed factory with type "
      "overrides, a type-safe config_db, a global objection counter and a "
      "phase scheduler (build top-down, run in parallel until objections "
      "drop, report bottom-up), plus a `comp_utils` macro that plays the "
      "role of `uvm_component_utils`. It compiles and runs on Verilator "
      "5.020.")
    code(r"""// mini_uvm.sv - a 120-line model of the UVM machinery, in plain SystemVerilog
package mini_uvm;
  typedef class component;

  // ---- factory: a static registry of "proxy" objects, keyed by type name ----
  virtual class proxy_base;                       // like uvm_object_wrapper
    pure virtual function component create_comp(string name, component parent);
    pure virtual function string    type_name();
  endclass

  class factory;
    static proxy_base registry [string];          // type name -> proxy
    static string     overrides[string];          // type name -> replacement name
    static function void register(proxy_base p);
      registry[p.type_name()] = p;
    endfunction
    static function void set_type_override(string orig, string repl);
      overrides[orig] = repl;
    endfunction
    static function component create(string tname, string name, component parent);
      while (overrides.exists(tname)) tname = overrides[tname];   // follow overrides
      if (!registry.exists(tname)) $fatal(1, "factory: type '%s' not registered", tname);
      return registry[tname].create_comp(name, parent);
    endfunction
  endclass

  // one specialization of this class exists per registered type T
  class registry #(type T = component, string TNAME = "") extends proxy_base;
    typedef registry #(T, TNAME) this_type;
    local static this_type me = get();            // static init registers the type
    static function this_type get();
      if (me == null) begin me = new(); factory::register(me); end
      return me;
    endfunction
    virtual function component create_comp(string name, component parent);
      T obj = new(name, parent);
      return obj;
    endfunction
    virtual function string type_name();  return TNAME;  endfunction
    static function T create(string name, component parent);   // T::type_id::create
      component c = factory::create(TNAME, name, parent);
      if (!$cast(create, c)) $fatal(1, "factory: override of %s is not a subtype", TNAME);
    endfunction
  endclass""", "mini_uvm.sv (part 1) - the factory: proxies, a static registry and overrides.")
    code(r"""  // ---- config_db: parameterized class, static associative array per type ----
  class config_db #(type T = int);
    static T db[string];
    static function void set(string path, string field, T value);
      db[{path, ".", field}] = value;
    endfunction
    static function bit get(string path, string field, output T value);
      if (db.exists({path, ".", field})) begin value = db[{path, ".", field}]; return 1; end
      if (db.exists({"*.", field}))      begin value = db[{"*.", field}];      return 1; end
      return 0;
    endfunction
  endclass

  // ---- objections: a global counter (UVM keeps one per phase and component) ----
  class objection;
    static int count;
    static function void raise();  count++;  endfunction
    static function void drop();   count--;  endfunction
  endclass

  // ---- component tree and phases (virtual methods called by the "kernel") ----
  class component;
    string name;  component parent;  component children[$];
    function new(string name, component parent);
      this.name = name;  this.parent = parent;
      if (parent != null) parent.children.push_back(this);
    endfunction
    function string full_name();
      return (parent == null) ? name : {parent.full_name(), ".", name};
    endfunction
    virtual function string get_type_name();  return "component";  endfunction
    virtual function void build_phase();   endfunction
    virtual function void connect_phase(); endfunction
    virtual task          run_phase();     endtask
    virtual function void report_phase();  endfunction
  endclass

  class kernel;                                   // the phase scheduler
    static function void do_build(component c);            // top-down
      c.build_phase();
      foreach (c.children[i]) do_build(c.children[i]);
    endfunction
    static function void do_report(component c);           // bottom-up
      foreach (c.children[i]) do_report(c.children[i]);
      c.report_phase();
    endfunction
    static function void collect(component c, ref component all[$]);
      all.push_back(c);
      foreach (c.children[i]) collect(c.children[i], all);
    endfunction
  endclass

  task automatic run_test(string test_name);
    component top = factory::create(test_name, "test", null);
    component all[$];
    kernel::do_build(top);
    kernel::collect(top, all);
    foreach (all[i]) all[i].connect_phase();
    foreach (all[i])
      fork
        automatic int k = i;                    // capture the loop index per thread
        all[k].run_phase();
      join_none
    #0;                                         // let run_phases raise objections
    wait (objection::count == 0);               // run phase ends when all objections drop
    disable fork;
    kernel::do_report(top);
  endtask
endpackage

`define comp_utils(T) \
  typedef mini_uvm::registry #(T, `"T`") type_id; \
  virtual function string get_type_name();  return `"T`";  endfunction""",
         "mini_uvm.sv (part 2) - config_db, objections, components, the phase kernel "
         "and the registration macro.")
    p("A few language points deserve comment. `typedef class component;` "
      "is a forward declaration, needed because the factory refers to "
      "`component` before it is defined. `proxy_base` is a `virtual class` "
      "with `pure virtual` methods - an abstract base that the parameterized "
      "`registry` implements once per registered type. The line `local "
      "static this_type me = get();` is the heart of self-registration: "
      "each specialization of `registry` has its own static `me`, and its "
      "initializer runs during static initialization, before time 0. The "
      "`$cast(create, c)` assigns to the function's implicit return "
      "variable. The kernel's recursive functions are static class methods "
      "(Verilator 5.020 hit an internal error on the same code written as "
      "recursive package functions - another portability note). The macro "
      "stringifies its argument (a grave accent followed by a double quote "
      "around T in the listing) so that `comp_utils(driver)` produces the "
      "string \"driver\".")
    code(r"""// demo.sv - a "UVM-like" test built on mini_uvm
package demo_pkg;
  import mini_uvm::*;

  class driver extends component;
    `comp_utils(driver)
    int n = 2;
    function new(string name, component parent);  super.new(name, parent);  endfunction
    virtual function void build_phase();
      void'(config_db#(int)::get(full_name(), "n_items", n));
    endfunction
    virtual task run_phase();
      objection::raise();
      for (int i = 0; i < n; i++) begin
        #10 $display("[%0t] %s (%s) drives item %0d", $time, full_name(), get_type_name(), i);
      end
      objection::drop();
    endtask
  endclass

  class slow_driver extends driver;                  // a replacement for driver
    `comp_utils(slow_driver)
    function new(string name, component parent);  super.new(name, parent);  endfunction
    virtual task run_phase();
      objection::raise();                            // raise BEFORE consuming time
      #25 super.run_phase();
      objection::drop();
    endtask
  endclass

  class env extends component;
    `comp_utils(env)
    driver drv;
    function new(string name, component parent);  super.new(name, parent);  endfunction
    virtual function void build_phase();
      drv = driver::type_id::create("drv", this);    // never "new" directly
    endfunction
    virtual function void report_phase();
      $display("[%0t] %s: report, drv is a %s", $time, full_name(), drv.get_type_name());
    endfunction
  endclass

  class base_test extends component;
    `comp_utils(base_test)
    env e;
    function new(string name, component parent);  super.new(name, parent);  endfunction
    virtual function void build_phase();
      config_db#(int)::set("test.e.drv", "n_items", 3);
      e = env::type_id::create("e", this);
    endfunction
  endclass

  class slow_test extends base_test;
    `comp_utils(slow_test)
    function new(string name, component parent);  super.new(name, parent);  endfunction
    virtual function void build_phase();
      factory::set_type_override("driver", "slow_driver");   // before env is built
      super.build_phase();
    endfunction
  endclass
endpackage

module tb;
  import mini_uvm::*;
  import demo_pkg::*;
  initial begin
    string t;
    if (!$value$plusargs("TEST=%s", t)) t = "base_test";
    $display("registered types: %0d", factory::registry.num());
    run_test(t);                                    // like UVM's run_test()
  end
endmodule""", "demo.sv - components, a config_db setting, and a test that overrides "
       "the driver type through the factory.")
    code(r"""verilator --binary --timing -Wno-fatal -Wno-WIDTHTRUNC --top-module tb \
          mini_uvm.sv demo.sv -o Vtb
./obj_dir/Vtb                    # base_test
./obj_dir/Vtb +TEST=slow_test""", "Build and run with Verilator 5.020.")
    out(r"""registered types: 5
[10] test.e.drv (driver) drives item 0
[20] test.e.drv (driver) drives item 1
[30] test.e.drv (driver) drives item 2
[30] test.e: report, drv is a driver""", "Verilator 5.020: base_test. Five types were "
       "registered before time 0; config_db set n_items=3 for test.e.drv.")
    out(r"""registered types: 5
[35] test.e.drv (slow_driver) drives item 0
[45] test.e.drv (slow_driver) drives item 1
[55] test.e.drv (slow_driver) drives item 2
[55] test.e: report, drv is a slow_driver""", "Verilator 5.020: +TEST=slow_test. env "
       "still calls driver::type_id::create, but gets a slow_driver.")
    p("Everything UVM promises is visible here in miniature: the test was "
      "selected by a string at run time; `env` was not edited, yet it built "
      "a different driver; the driver read its configuration from a "
      "database populated by an ancestor; and the run phase ended exactly "
      "when the last objection dropped (at 55, not at a fixed time). A "
      "misspelled test name reaches the `$fatal` in the factory:")
    out(r"""registered types: 5
[0] %Fatal: mini_uvm.sv:22: Assertion failed in TOP.mini_uvm.factory.create:
    factory: type 'nope' not registered""",
        "Verilator 5.020: ./obj_dir/Vtb +TEST=nope (first line of the fatal message, "
        "wrapped at the indent).")
    p("Finally, the objection pitfall. Remove the two objection calls from "
      "`slow_driver::run_phase` so that it relies on the base class's "
      "raise, which now happens only after the `#25`:")
    code(r"""    virtual task run_phase();
      #25 super.run_phase();          // base raises its objection only at t=25
    endtask""", "demo_late.sv - slow_driver without its own objection.")
    out(r"""registered types: 5
[0] test.e: report, drv is a slow_driver""", "Verilator 5.020: +TEST=slow_test with "
       "demo_late.sv. The run phase ended at time 0; nothing was driven, and "
       "nothing reported an error.")
    box("expert", "What the real library adds",
        "Compared with this model, UVM adds instance-specific overrides (path "
        "patterns), regular-expression scopes and precedence in the config "
        "database, per-phase objection objects with hierarchy propagation, "
        "drain times and timeouts, phase jumping, domains for independently "
        "phased sub-systems, the report server with verbosity and "
        "severity actions, and the sequencer. None of it needs a language "
        "feature not used here.")

    h2("Summary")
    bul(["UVM is a SystemVerilog class library (IEEE 1800.2); every mechanism "
         "maps onto classes, virtual methods, parameterized classes, static "
         "members, associative arrays, macros and processes.",
         "uvm_object is for transient data (items, sequences, configs); "
         "uvm_component is for the permanent, phased hierarchy.",
         "The factory is a static registry of singleton proxy objects, one "
         "per registered type, created by static initialization; "
         "type_id::create() looks up the proxy, applies overrides and $casts "
         "the result. Calling new() bypasses it.",
         "The utility macros only generate the type_id typedef and "
         "get_type/get_type_name methods (and, for field macros, "
         "copy/compare/print code).",
         "uvm_config_db #(T) is a parameterized class with static storage; "
         "each T is a separate, type-safe database. Virtual interfaces are "
         "passed from the top module this way.",
         "Phases are virtual methods called by a scheduler; run_phase tasks "
         "run in parallel and end when all objections drop - raise before "
         "any delay.",
         "Sequences run body() in the caller's process; the sequencer "
         "arbitrates between them; analysis ports broadcast by calling "
         "write() on each subscriber; RAL is a generated class model with "
         "adapters and DPI-based backdoor access.",
         "A 120-line mini UVM ran on Verilator and reproduced factory "
         "overrides, config_db and the objection-at-time-zero bug."])

    h2("Exercises")
    bul(["Extend the mini factory with instance overrides: "
         "`set_inst_override(\"test.e.drv\", \"driver\", \"slow_driver\")`. "
         "What must `create()` know that it does not know now, and how does "
         "UVM supply it?",
         "Add a `connect_phase` to the mini model that connects a tiny "
         "analysis port (a class holding a queue of subscriber handles with "
         "a `write()` function) from a monitor to two subscribers. Why must "
         "write() be a function rather than a task?",
         "Write the macro expansion of `uvm_object_utils(fifo_item)` by "
         "hand, including create(). Explain why a parameterized class must "
         "use the _param_ variant.",
         "Given `uvm_config_db#(int)::set(this, \"env.*\", \"n\", 5)` in "
         "the test and `uvm_config_db#(int)::set(this, \"agt\", \"n\", 9)` in "
         "the env, which value does the agent get in build_phase, and why?",
         "Add a second sequence that writes only (push) and run it in "
         "parallel with fifo_rand_seq from a virtual sequence. Predict the "
         "interleaving under UVM_SEQ_ARB_FIFO and under "
         "UVM_SEQ_ARB_STRICT_FIFO with priorities 100 and 200.",
         "Run the full UVM environment of this chapter on EDA Playground "
         "with a planted bug and confirm that `uvm_error` messages make the "
         "test fail. Then remove the objection from base_test and observe the "
         "result."], ordered=True)



# =============================================================================
#            Chapter 27 - Language pitfalls, portability and lint
# =============================================================================
def ch27():
    chapter("Language Pitfalls, Portability and Lint")
    p("Most expensive bugs in Verilog and SystemVerilog are not in exotic "
      "features. They come from a handful of language rules that are "
      "perfectly well defined but not what the author expected: how wide an "
      "expression is, whether it is signed, what an X does in an `if`, "
      "which process runs first in a time step, and whether a variable is "
      "static. The same rules also cause code to behave differently on "
      "different tools, either because the LRM leaves something "
      "unspecified or because a tool deviates from it. This chapter is a "
      "reference catalogue. Each pitfall is stated as a rule, shown with a "
      "bad and a good form, and - wherever a tool here could run it - "
      "demonstrated with real output from Icarus Verilog 12 and Verilator "
      "5.020. It ends with the lint tools and rule categories that catch "
      "these mistakes automatically, run on a deliberately buggy file.")

    tbl(["Category", "Typical damage", "Caught by"],
        [["Expression sizing and signedness", "Wrong arithmetic in RTL and models, "
          "silently", "Lint (width rules), careful review, simulation"],
         ["4-state / X semantics", "Bugs hidden in RTL simulation, found at gate "
          "level or in silicon", "X-propagation tools, assertions, gate-level sim"],
         ["RTL coding style", "Simulation/synthesis mismatch, latches, races",
          "Lint, synthesis reports, equivalence checking"],
         ["Scheduling and races", "Results that depend on the simulator or on "
          "file order", "Lint (BLKSEQ etc.), code review, race-free methodology"],
         ["Testbench (lifetimes, processes)", "Testbench checks the wrong thing or "
          "nothing", "Code review, mutation testing, multiple simulators"],
         ["Portability", "Code that works on one tool only", "Running more than one "
          "tool in CI"]],
        widths=[28, 38, 34], bold_first=True,
        caption="Table 27.1 - The pitfall families of this chapter.")

    # ------------------------------------------------------------------
    h2("Expression width and signedness")
    p("Recall the rules of Chapter 4. An expression is sized in two passes: "
      "the **context** width is the maximum of the operand widths __and "
      "the assignment target__; context-determined operands (arithmetic, "
      "bitwise, ?: branches) are extended to that width __before__ the "
      "operation; self-determined operands (concatenation members, shift "
      "counts, reduction and relational operands' results, casts' "
      "results) keep their own width. Signedness is decided separately: an "
      "expression is signed only if __all__ its context-determined operands "
      "are signed; a single unsigned operand makes the whole expression "
      "unsigned, and part-selects and concatenations are always unsigned. "
      "Extension happens after these decisions, by sign or by zero.")
    code(r"""// pit_expr.sv - expression pitfalls (run on Icarus 12 and Verilator 5.020)
module pit_expr;
  logic        [7:0] a = 8'd200, b = 8'd100, avg8;
  logic        [8:0] avg9, cat9;
  logic signed [7:0] x = -8'sd4;
  logic        [7:0] u = 8'd2;
  logic signed [15:0] y1, y2;
  initial begin
    // 1. width: the LHS is part of the context
    avg8 = (a + b) >> 1;          // context = 8 bits: carry lost before the shift
    avg9 = (a + b) >> 1;          // context = 9 bits: carry kept
    cat9 = {a + b};               // concatenation operand is self-determined: 8 bits
    $display("1: avg8=%0d avg9=%0d cat9=%0d", avg8, avg9, cat9);
    // 2. one unsigned operand makes the whole expression unsigned
    $display("2: x<u is %b   x<signed'(u) is %b", x < u, x < signed'(u));
    y1 = x;                       // signed source: sign-extended
    y2 = x + u;                   // unsigned expression: zero-extended
    $display("2: y1=%0d  y2=%0d", y1, y2);
    // 3. integer literal arithmetic
    $display("3: -8'd4 / 2 = %0d  -4 / 2 = %0d  8'hFF + 1 = %0d", -8'd4 / 2, -4 / 2,
             8'hFF + 1);
    $finish;
  end
endmodule""", "pit_expr.sv")
    out(r"""1: avg8=22 avg9=150 cat9=44
2: x<u is 0   x<signed'(u) is 1
2: y1=-4  y2=254
3: -8'd4 / 2 = 2147483646  -4 / 2 = -2  8'hFF + 1 = 256""",
        "Icarus 12 and Verilator 5.020 print identical results (the LRM is "
        "unambiguous here).")
    bul(["**avg8 = 22**: `a + b` is evaluated at 8 bits because both operands "
         "and the target are 8 bits; 300 wraps to 44 before the shift. With a "
         "9-bit target the same text gives 150. Moving an expression into a "
         "narrower variable can therefore change the value of its "
         "__intermediate__ results, not just truncate the final one.",
         "**cat9 = 44**: the operand of a concatenation is self-determined, "
         "so `{a + b}` is 8 bits whatever the target. Wrapping an expression "
         "in braces 'to be safe' is a bug.",
         "**x < u is 0**: `x` is signed, `u` is unsigned, so the comparison is "
         "unsigned and -4 becomes 252. The fix `signed'(u)` works here but "
         "reinterprets values of u >= 128 as negative; the robust form is "
         "`x < signed'({1'b0, u})`, which is 9 bits and signed.",
         "**y2 = 254**: `x + u` is unsigned, so the 8-bit result 0xFE is "
         "zero-extended to 16 bits. `y1 = x` alone is sign-extended to -4.",
         "**-8'd4 / 2 = 2147483646**: a sized literal written with a minus "
         "sign is still an __unsigned__ value (the minus is an operator "
         "applied to 8'd4). Combined with the signed 32-bit literal 2 the "
         "expression is unsigned 32-bit, so the operand is 4294967292. Use "
         "`-8'sd4` or plain integers.",
         "**8'hFF + 1 = 256**: the unsized literal 1 is 32 bits, so the "
         "addition is 32 bits wide. Width surprises go both ways."])

    code(r"""// pit_misc.sv - a few more silent surprises (Icarus 12 and Verilator 5.020)
module pit_misc;
  logic signed [7:0] s = -8'sd7;
  logic        [7:0] u = 8'hF0, mem [4];
  int                r;
  function int counter();             // module functions are STATIC by default
    int c = 0;                        // initialised once, at time 0 - not per call
    c++;
    return c;
  endfunction
  initial begin
    $display("-7/2=%0d  -7>>>1=%0d  8'hF0>>>2=%h  s[7:0]>>>1=%h", s / 2, s >>> 1, u >>> 2,
             s[7:0] >>> 1);
    r = int'(2.5);  $display("int'(2.5)=%0d  int'(-2.5)=%0d  $rtoi(2.5)=%0d", r, int'(-2.5),
                             $rtoi(2.5));
    mem[0] = 8'h11;
    $display("mem[7]=%h (index out of range reads the default value)", mem[7]);
    $display("counter() x3: %0d %0d %0d", counter(), counter(), counter());
    $finish;
  end
endmodule""", "pit_misc.sv")
    out(r"""pit_misc.sv:7: warning: Static variable initialization requires explicit lifetime in this context.
pit_misc.sv:17: warning: returning 'bx for out of bounds array access mem[7].
-7/2=-3  -7>>>1=-4  8'hF0>>>2=3c  s[7:0]>>>1=7c
int'(2.5)=3  int'(-2.5)=-3  $rtoi(2.5)=2
mem[7]=xx (index out of range reads the default value)
counter() x3: 1 2 3""".replace(" in this context.", "\n    in this context."),
        "Icarus 12 (iverilog -g2012; the first warning line is wrapped here).")
    out(r"""%Warning-IMPLICITSTATIC: pit_misc.sv:6:16: Function/task's lifetime implicitly set to static
%Warning-SELRANGE: pit_misc.sv:17:75: Selection index out of range: 7 outside 3:0
-7/2=-3  -7>>>1=-4  8'hF0>>>2=3c  s[7:0]>>>1=7c
int'(2.5)=3  int'(-2.5)=-3  $rtoi(2.5)=2
mem[7]=00 (index out of range reads the default value)
counter() x3: 3 2 1""", "Verilator 5.020 (--binary). Same arithmetic; different "
       "out-of-range value and a different order of evaluating the three calls.")
    bul(["Signed division truncates toward zero (-7/2 = -3) but an "
         "arithmetic shift rounds toward minus infinity (-7>>>1 = -4). "
         "Replacing a divide by a shift in signed RTL changes the answer for "
         "negative odd values.",
         "`>>>` is arithmetic only on a **signed** operand. `u` is unsigned, "
         "so 8'hF0>>>2 = 8'h3C, and a part-select of a signed variable "
         "(`s[7:0]`) is unsigned too, so it also shifts in zeros.",
         "Casting real to integer **rounds** (ties away from zero): "
         "int'(2.5) = 3. `$rtoi` truncates. Both appear in models of DSP "
         "blocks; mixing them up gives 1-LSB mismatches.",
         "An out-of-range read returns the default value of the element type: "
         "X for 4-state `logic` (Icarus) - but Verilator is a 2-state "
         "simulator and returns 0, so the same bug is visible on one tool "
         "and invisible on the other. Out-of-range writes are ignored.",
         "Functions and tasks declared in a module are **static** unless "
         "declared `automatic`: `int c = 0;` is initialised once, and the "
         "LRM requires an explicit `static` keyword on such an initialised "
         "declaration precisely because the behaviour surprises people. Both "
         "tools warn. And the order in which the three arguments of the "
         "`$display` were evaluated differs between tools - never write code "
         "whose result depends on it."])

    # ------------------------------------------------------------------
    h2("X, 4-state and 2-state pitfalls")
    code(r"""// pit_x.sv - X-optimism, 2-state types, == vs ===, casex (Icarus 12)
module pit_x;
  logic       sel = 1'bx;
  logic [3:0] p = 4'b10x0, q = 4'b10x0;
  logic       y_if, y_case;
  logic [1:0] y_tern;
  bit         b2;
  int         i2;
  logic [1:0] op;
  initial begin
    if (sel) y_if = 1'b1; else y_if = 1'b0;        // X takes the else branch
    case (sel) 1'b1: y_case = 1'b1; default: y_case = 1'b0; endcase
    y_tern = sel ? 2'b10 : 2'b11;                  // ?: merges: differing bits -> x
    $display("x-opt:  if->%b  case->%b  ?:->%b", y_if, y_case, y_tern);
    b2 = sel;  i2 = p;                             // 2-state targets turn X into 0
    $display("2state: bit<-x = %b   int<-4'b10x0 = %0d", b2, i2);
    $display("eq:     p==q -> %b   p===q -> %b   p!=q -> %b", p == q, p === q, p != q);
    if (p == q) $display("eq:     if (p==q) taken"); else $display("eq:     else taken");
    op = 2'bx1;                                     // e.g. an uninitialised opcode bit
    casex (op)
      2'b0x:   $display("casex:  op=%b matched 2'b0x (READ)", op);
      2'b11:   $display("casex:  op=%b matched 2'b11 (WRITE)", op);
      default: $display("casex:  default");
    endcase
    casez (op)
      2'b0?:   $display("casez:  op=%b matched 2'b0?", op);
      2'b11:   $display("casez:  op=%b matched 2'b11", op);
      default: $display("casez:  op=%b -> default (X not treated as don't-care)", op);
    endcase
  end
endmodule""", "pit_x.sv")
    out(r"""x-opt:  if->0  case->0  ?:->1x
2state: bit<-x = 0   int<-4'b10x0 = 8
eq:     p==q -> x   p===q -> 1   p!=q -> x
eq:     else taken
casex:  op=x1 matched 2'b0x (READ)
casez:  op=x1 -> default (X not treated as don't-care)""", "Icarus 12 (4-state).")
    bul(["**X-optimism of if/case**: an `if` whose condition is X (or Z) "
         "takes the else branch; a `case` whose selector is X matches no "
         "ordinary item and takes the default. The RTL simulation shows a "
         "clean 0 where real hardware might produce 0 or 1. The bug "
         "surfaces only in gate-level simulation or silicon. Guard critical "
         "selects with an assertion such as `assert (!$isunknown(sel))` and "
         "consider your simulator's X-propagation mode (VCS -xprop, Xcelium "
         "-xprop).",
         "**?: is X-pessimistic by comparison**: with an X condition it "
         "merges both branches bit by bit, giving `1x` - closer to hardware.",
         "**2-state types hide X**: assigning to `bit`, `int` or `byte` "
         "converts X and Z to 0. Declaring DUT outputs in a testbench as "
         "`bit` hides exactly the X you need to see. Rule: `logic` for "
         "everything that touches the DUT; 2-state types for loop counters "
         "and pure testbench data.",
         "**== versus ===**: logical equality with any X/Z bit yields X, and "
         "`if (X)` is false - so `if (p == q)` takes the else branch even "
         "though the values are bit-for-bit identical. In checkers use `===` "
         "and `!==`; in RTL use `==` (case equality has no hardware meaning "
         "and synthesis tools either reject it or treat it as ==).",
         "**casex hazards**: in `casex`, X and Z in the __selector__ are "
         "don't-cares too, so an unknown opcode silently matches the first "
         "item (here READ). `casez` treats only Z/? as don't-care. Better "
         "still in SystemVerilog: `case (op) inside 2'b0?: ... endcase`, "
         "where only the item side has wildcards."])
    box("warn", "PITFALL (portability): Verilator is a 2-state simulator",
        "Verilator maps X and Z to 0 or 1 (chosen by --x-assign and "
        "--x-initial: 0, 1, fast or unique/random). None of the X examples "
        "above behave the same way on it, and a testbench that relies on "
        "detecting X with `===` or `$isunknown` cannot find X bugs there. "
        "Run X-sensitive tests on a 4-state simulator, and on Verilator run "
        "regressions with --x-initial unique and several seeds so that "
        "uninitialised state is randomised rather than conveniently 0.")

    # ------------------------------------------------------------------
    h2("Races and scheduling")
    p("The event scheduler (Chapter 5) executes all processes woken at the "
      "same time step in the Active region in an **unspecified** order. "
      "Any design or testbench whose result depends on that order has a "
      "race, and different simulators - or the same simulator after a "
      "harmless edit - can resolve it differently.")
    code(r"""// race.sv - two classic races: order of initial blocks, blocking between always blocks
module race;
  logic clk = 0, d = 1, q1 = 0, q2 = 0;
  int   a;
  initial $display("initial race: a=%0d", a);      // runs before or after the next line?
  initial a = 5;

`ifdef SWAP
  always @(posedge clk) q1 = d;                      // stage 1 (blocking: BAD)
  always @(posedge clk) q2 = q1;                     // stage 2 (blocking: BAD)
`else
  always @(posedge clk) q2 = q1;                     // stage 2 (blocking: BAD)
  always @(posedge clk) q1 = d;                      // stage 1 (blocking: BAD)
`endif

  initial begin
    #1 clk = 1;
    #1 $display("after one edge: q1=%b q2=%b (a 2-stage pipe should give q2=0)", q1, q2);
    $finish;
  end
endmodule""", "race.sv - compiled with and without +define SWAP.")
    tbl(["Run", "initial race", "q2 after one edge"],
        [["Icarus 12, default order", "a=0", "q2=1 (wrong)"],
         ["Icarus 12, -DSWAP", "a=0", "q2=0"],
         ["Verilator 5.020, default order", "a=5", "q2=1 (wrong)"],
         ["Verilator 5.020, -DSWAP", "a=5", "q2=1 (wrong)"],
         ["Icarus 12, both stages changed to <=", "a=0", "q2=0 (correct)"]],
        widths=[44, 22, 34], bold_first=True,
        caption="Table 27.2 - Real results of race.sv. Source order and tool change "
                "the answer; nonblocking assignments remove the race.")
    p("The first race is between two `initial` blocks at time 0: whether "
      "the display sees 0 or 5 is unspecified, and the two tools disagree. "
      "The second is the classic reason for the nonblocking rule: with "
      "blocking assignments in two clocked processes, whether stage 2 reads "
      "the old or new value of `q1` depends on which process runs first. "
      "Swapping the source order flipped the Icarus result but not "
      "Verilator's (Verilator orders the whole design statically). With "
      "`<=`, all right-hand sides are sampled before any flop updates, and "
      "every simulator gives the same, hardware-accurate answer.")
    code(r"""// fork_static.sv - loop variable capture and static tasks
module f;
  task automatic show(string tag, int v);  $display("%s %0d", tag, v);  endtask
  task static tick(input int id);
    int v;
    v = id;
    #1 $display("static task: called with %0d, sees v=%0d", id, v);
  endtask
  initial begin
    for (int i = 0; i < 3; i++) fork show("fork (bad):", i); join_none
    #1;
    fork tick(1); tick(2); join
    $finish;
  end
endmodule""", "fork_static.sv")
    out(r"""fork (bad): 3
fork (bad): 3
fork (bad): 3
static task: called with 1, sees v=1
static task: called with 1, sees v=1""", "Icarus 12 - the LRM behaviour.")
    out(r"""fork (bad): 0
fork (bad): 1
fork (bad): 2
static task: called with 1, sees v=1
static task: called with 2, sees v=2""",
        "Verilator 5.020 - which does not follow the LRM here.")
    p("By the LRM, the three processes created by `fork ... join_none` "
      "inside the loop do not start until the parent blocks at `#1`, by "
      "which time the single loop variable `i` is 3, so every thread "
      "prints 3 - Icarus does exactly this, as do the commercial "
      "simulators. The fix is to give each thread its own copy with a "
      "declaration in the fork's declarative region, which is executed at "
      "fork time: `fork automatic int k = i; show(\"...\", k); join_none`. "
      "Verilator 5.020 happened to print 0, 1, 2 for the __buggy__ form, so "
      "a testbench developed only on Verilator can carry this bug unseen "
      "until it moves to another simulator.")
    p("The static task has one copy of its arguments and locals shared by "
      "all callers. Both concurrent calls write `id` and `v`; whichever "
      "writes last wins and both threads report it. Icarus shows the "
      "sharing (the value 2 is lost completely); Verilator 5.020 gave each "
      "call private storage, again differing from the LRM. Rule: declare "
      "every task and function in a module or interface `automatic`, or put "
      "`module automatic` on the module. Class methods are automatic "
      "already.")

    h3("The timescale directive and file order")
    p("The timescale directive (Chapter 8) is a compiler directive, not a "
      "module property: it applies to every module that follows it in the "
      "compilation, across file boundaries, until the next one. A module "
      "without its own directive therefore inherits whatever came last - "
      "which depends on the order of files on the command line.")
    code(r"""// ts_a.v
`timescale 1ns/1ps
module tb;
  initial begin #10 $display("tb:  t=%0t", $realtime); end
  sub u();
endmodule

// ts_b.v
module sub;                          // no `timescale: inherits whatever came last
  initial begin #10 $display("sub: t=%0t", $realtime); end
endmodule""", "ts_a.v and ts_b.v - two files, one directive.")
    out(r"""$ iverilog -Wall -o ts1.vvp ts_a.v ts_b.v && vvp -n ts1.vvp
ts_b.v:1: warning: timescale for sub inherited from another file.
ts_a.v:1: ...: The inherited timescale is here.
sub: t=10000
tb:  t=10000
$ iverilog -Wall -o ts2.vvp ts_b.v ts_a.v && vvp -n ts2.vvp
warning: Some modules have no timescale. This may cause
       : confusing timing results.  Affected modules are:
       :   -- module sub declared here: ts_b.v:1
warning: Found both default and `timescale based delays. Use
       : -Wtimescale to find the module(s) with no `timescale.
tb:  t=10000
sub: t=10000000000000""", "Icarus 12 (a tab in the output is shown as two spaces). "
       "Same source, different file order: sub's #10 is 10 ns in the first run "
       "and 10 s (the default unit) in the second. Times print in the 1 ps "
       "global precision.")
    p("Verilator refuses to guess: it reports TIMESCALEMOD ('Timescale "
      "missing on this module as other modules have it'). The robust fix "
      "is to declare `timeunit 1ns; timeprecision 1ps;` inside every "
      "module, interface and package, which binds the units to the "
      "design element itself, or to set a project-wide default with a "
      "tool option (for example -timescale=1ns/1ps in VCS, --timescale in "
      "Verilator).")

    # ------------------------------------------------------------------
    h2("Testbench-language pitfalls")
    code(r"""// pit_tb.sv - testbench-language pitfalls (Verilator 5.020 --binary)
module pit_tb;
  typedef enum logic [1:0] {IDLE, RUN, DONE} state_e;
  byte    arr[$] = '{100, 100, 100, 100};
  state_e st;
  int     n, total;
  initial begin
    // 1. array reduction methods return the ELEMENT type
    foreach (arr[i]) total += arr[i];                  // portable: accumulate in an int
    $display("sum()=%0d  sum() with (int'(item))=%0d  foreach into int=%0d",
             arr.sum(), arr.sum() with (int'(item)), total);
    // 2. enum from an integer
    if (!$cast(st, 3)) $display("$cast(st, 3) failed: 3 is not a state_e value");
    st = state_e'(3);                                  // static cast: no check at all
    $display("state_e'(3): value %0d, name '%s'", st, st.name());
    // 3. a 3-bit loop counter never reaches 8
    n = 0;
    for (bit [2:0] j = 0; j < 8; j++) begin
      n++;
      if (n == 20) break;                              // safety guard
    end
    $display("bit [2:0] j < 8 loop: %0d iterations before the guard fired", n);
    // 4. $random is signed; $urandom is unsigned
    begin
      int neg = 0;
      repeat (100) if ($random % 10 < 0) neg++;
      $display("$random %% 10 < 0 in %0d of 100 calls; $urandom %% 10 never", neg);
    end
    // 5. string literals in ?: without a string context are just integers
    $display(n > 0 ? "ok" : "fail");
    $display("%s", n > 0 ? "ok" : "fail");
    $finish;
  end
endmodule""", "pit_tb.sv - Icarus 12 does not support array reduction methods or "
       "break, so this one ran on Verilator only.")
    out(r"""sum()=-112  sum() with (int'(item))=144  foreach into int=400
$cast(st, 3) failed: 3 is not a state_e value
state_e'(3): value 3, name ''
bit [2:0] j < 8 loop: 20 iterations before the guard fired
$random % 10 < 0 in 44 of 100 calls; $urandom % 10 never
     28523
  ok""", "Verilator 5.020.")
    bul(["**sum() width**: array reduction methods return the element type, "
         "so four bytes of 100 sum to -112 (400 wrapped to signed 8 bits). "
         "The LRM fix is `sum() with (int'(item))`, whose result type is "
         "that of the `with` expression, so it should give 400; Verilator "
         "5.020 still returned an 8-bit result (144 = 400 mod 256) - a tool "
         "bug. The only fully portable form is an explicit `foreach` into an "
         "`int`.",
         "**enum from int**: `st = 3;` is a compile error (an enum variable "
         "accepts only its own type). `$cast(st, 3)` checks the value and "
         "fails; the static cast `state_e'(3)` does not check and leaves an "
         "illegal value whose `name()` is the empty string. Use `$cast` in "
         "testbenches when the integer comes from outside (a file, a DPI "
         "call, a register read).",
         "**loop counters**: `j < 8` is always true for a 3-bit unsigned "
         "variable (7 + 1 wraps to 0): an infinite loop. Loop variables are "
         "`int` unless there is a reason.",
         "**$random vs $urandom**: `$random` returns a signed 32-bit value, "
         "so `$random % 10` is negative almost half the time (44 of 100 "
         "here), which indexes arrays out of range. `$urandom` and "
         "`$urandom_range` are unsigned and thread-stable (each process and "
         "object has its own generator), which is what makes a "
         "regression seed reproducible after unrelated code changes.",
         "**string literals are integers**: a string literal is a packed "
         "array of 8-bit characters. In `$display(cond ? \"ok\" : \"fail\")` "
         "there is no format string, so the ?: result is printed as a number "
         "(\"ok\" = 16'h6F6B = 28523). With a `%s` format it prints text. "
         "The same happens when a string literal is assigned to a `logic` "
         "vector: it is right-justified and truncated on the left."])

    # ------------------------------------------------------------------
    h2("The catalogue")
    p("Table 27.3 collects the pitfalls of this chapter and of the whole "
      "book in one place, each with the bad form and the good form. Use it "
      "as a code-review checklist.")
    tbl(["#", "Pitfall", "Bad", "Good"],
        [["1", "Width of intermediate results set by the target",
          "`avg8 = (a+b)>>1`", "`s9 = a+b; avg8 = s9[8:1]`"],
         ["2", "Concatenation operand is self-determined",
          "`s9 = {a+b}`", "`s9 = a + b` or `{1'b0,a} + b`"],
         ["3", "Mixed signed/unsigned becomes unsigned",
          "`x < u`", "`x < signed'({1'b0,u})`"],
         ["4", "Negative sized literal is unsigned", "`-8'd4 / 2`", "`-8'sd4 / 2`"],
         ["5", "Part-select of a signed value is unsigned",
          "`s[7:0] >>> 1`", "`signed'(s[7:0]) >>> 1`"],
         ["6", "`>>>` on unsigned is logical", "`u >>> 2` expecting sign fill",
          "declare `logic signed` or cast"],
         ["7", "Divide vs arithmetic shift rounding", "`x >>> 1` as `x / 2`",
          "use `/` or add bias for negatives"],
         ["8", "Real-to-int rounds, $rtoi truncates", "`int'(r)` expecting floor",
          "`$rtoi(r)` or `$floor`"],
         ["9", "Loop counter too narrow", "`for (bit [2:0] j=0; j<8; j++)`",
          "`for (int j=0; j<8; j++)`"],
         ["10", "32-bit overflow in products", "`int p = a32 * b32`",
          "`longint p = 64'(a32) * b32`"],
         ["11", "X-optimism of if/case", "`if (sel)` with X sel",
          "`assert (!$isunknown(sel))`, xprop sim"],
         ["12", "2-state types hide X", "`bit [7:0] dout_tb`", "`logic [7:0] dout_tb`"],
         ["13", "== with X yields X", "`if (dout != exp) err++`",
          "`if (dout !== exp) err++`"],
         ["14", "casex matches X in the selector", "`casex (op)`",
          "`case (op) inside` or `casez`"],
         ["15", "Blocking in clocked processes", "`always_ff ... q2 = q1;`",
          "`q2 <= q1;`"],
         ["16", "NBA for temporaries in combinational code",
          "`t <= a & b; y <= t | c;` in always_comb", "`t = a & b; y = t | c;`"],
         ["17", "Missing default/else -> latch", "`case` without default in always_comb",
          "default assignments first, or `default:`"],
         ["18", "Incomplete sensitivity list", "`always @(a) y = a & b;`",
          "`always_comb y = a & b;`"],
         ["19", "Implicit nets from typos", "undeclared `sum_ab` becomes 1-bit wire",
          "default_nettype none directive at the top of every file"],
         ["20", "Multiple drivers", "two `assign y = ...`",
          "one driver; `always_comb` / `always_ff` enforce it"],
         ["21", "timescale directive depends on file order",
          "timescale directive in some files only",
          "`timeunit`/`timeprecision` in every module"],
         ["22", "Race between initial blocks", "`initial a = 5; initial use(a);`",
          "order with events, NBA, or one initial"],
         ["23", "Race between always blocks (blocking)", "stage-to-stage `=`",
          "`<=` for every flop"],
         ["24", "Loop variable captured by fork", "`fork show(i); join_none` in loop",
          "`fork automatic int k = i; show(k); join_none`"],
         ["25", "Static task/function variables", "`task t();` in a module",
          "`task automatic t();`"],
         ["26", "Initialiser in a static function runs once", "`int c = 0;` in "
          "static function", "`automatic` function, or assign in the body"],
         ["27", "Packed vs unpacked assignment", "`p32 = u8x4;` (unpacked)",
          "`p32 = {>>{u8x4}};` streaming"],
         ["28", "enum assigned from int", "`st = 3;` or `state_e'(v)` unchecked",
          "`if (!$cast(st, v)) error`"],
         ["29", "sum()/product() in element width", "`byte_q.sum()`",
          "foreach into `int`, or `sum() with (int'(item))`"],
         ["30", "$random is signed, unstable", "`idx = $random % N`",
          "`idx = $urandom_range(N-1)`"],
         ["31", "String literal in ?: printed as number",
          "`$display(c ? \"ok\" : \"bad\")`", "`$display(\"%s\", c ? ...)`"],
         ["32", "Variable initialisers ignored by ASIC synthesis",
          "`logic [3:0] cnt = 0;` as reset", "explicit reset in always_ff"],
         ["33", "Out-of-range index silently tolerated", "`mem[addr]` with addr >= depth",
          "assertion on the index; lint SELRANGE"],
         ["34", "Same object put in a mailbox repeatedly", "one handle, randomize + put "
          "in a loop", "`t = new();` for every item"],
         ["35", "disable fork kills unrelated threads", "`disable fork` in a shared "
          "process", "wrap in `fork begin ... end join`"],
         ["36", "Dependence on argument evaluation order", "`f(g(), g())` with side "
          "effects", "evaluate into temporaries first"]],
        widths=[5, 31, 32, 32],
        caption="Table 27.3 - Thirty-six pitfalls with bad and good forms.")
    box("warn", "PITFALL: initial values in RTL (row 32)",
        "`logic [3:0] cnt = 0;` initialises the variable at time 0 in "
        "simulation, so the RTL simulates as if the counter were reset. ASIC "
        "synthesis ignores the initialiser (there is no power-on value in a "
        "standard-cell flop), and the gate-level netlist starts at X. FPGA "
        "tools do honour initialisers through the bitstream, which is why "
        "code ported from FPGA to ASIC breaks here. In ASIC RTL, reset every "
        "flop that needs a known value explicitly and let lint flag "
        "initialisers.")

    # ------------------------------------------------------------------
    h2("Tool portability")
    p("The LRM is large, and every tool implements a different subset with "
      "a different interpretation of the unclear corners. Table 27.4 "
      "summarises the practical situation for the tools most used on SoC "
      "projects; check your tool's release notes for the exact version you "
      "run, because open-source tools in particular move quickly.")
    tbl(["Tool", "Kind", "Language coverage and notable behaviour"],
        [["Icarus Verilog 12", "4-state event-driven sim (open source)",
          "Verilog-2005 nearly complete; SV design subset good; limited classes; "
          "no constraints, covergroups, concurrent SVA, clocking blocks or UVM"],
         ["Verilator 5.x", "2-state cycle-based compiler to C++ (open source)",
          "very fast; broad SV incl. classes, queues, mailboxes, --timing; X "
          "mapped to 0/1; constraints ignored in 5.020; no covergroups; limited "
          "concurrent SVA; strong lint"],
         ["VCS (Synopsys)", "full 4-state sim", "full IEEE 1800 incl. UVM, "
          "constraints, coverage, SVA; xprop; commercial"],
         ["Xcelium (Cadence)", "full 4-state sim", "same class as VCS; "
          "multi-language; xprop; commercial"],
         ["Questa (Siemens)", "full 4-state sim", "same class as VCS; strong "
          "debug and formal integration; commercial"],
         ["Design Compiler / Fusion (Synopsys), Genus (Cadence)",
          "ASIC synthesis", "synthesizable SV subset (Chapter 17); ignore "
          "initial blocks and initialisers; honour unique/priority as "
          "optimisation hints; full_case/parallel_case pragmas"],
         ["Vivado (AMD)", "FPGA sim + synthesis", "synthesis accepts a broad SV "
          "design subset and honours initialisers; simulator supports UVM with "
          "limitations"],
         ["Yosys 0.x", "open-source synthesis/formal", "Verilog-2005 plus a "
          "growing SV subset (via plugins such as slang for full SV); used for "
          "open flows and formal (SymbiYosys)"]],
        widths=[22, 24, 54], bold_first=True,
        caption="Table 27.4 - Tool landscape (as of 2026; verify against your "
                "versions).")
    tbl(["Behaviour", "Observed in this book"],
        [["Loop variable captured by fork/join_none",
          "Icarus: 3,3,3 (LRM); Verilator 5.020: 0,1,2"],
         ["Concurrent calls of a static task", "Icarus: shared storage (LRM); "
          "Verilator 5.020: private copies"],
         ["Order of two initial blocks at time 0", "Icarus and Verilator disagree"],
         ["Blocking assignments between clocked processes",
          "Icarus result depends on source order; Verilator's does not"],
         ["Out-of-range read of a logic array", "Icarus: X; Verilator: 0 (2-state)"],
         ["Evaluation order of function-call arguments", "Icarus left-to-right; "
          "Verilator right-to-left"],
         ["sum() with (int'(item))", "Verilator 5.020 kept the 8-bit width"],
         ["typedef virtual fifo_if #(W, D)", "Verilator 5.020 internal fault (Ch. 25)"],
         ["Recursive package functions", "Verilator 5.020 internal error; static "
          "class methods worked (Ch. 26)"],
         ["randomize() with constraints", "Verilator 5.020 compiles but ignores "
          "constraints"]],
        widths=[42, 58], bold_first=True,
        caption="Table 27.5 - Portability differences actually hit while writing "
                "this book.")
    box("tip", "Portability habits that pay",
        "(1) Run at least two simulators in CI - for example Verilator for "
        "speed and lint plus a 4-state simulator for X behaviour and "
        "verification features. (2) Write race-free code (nonblocking for "
        "flops, clocking blocks or the NBA discipline in testbenches), so "
        "scheduling differences cannot matter. (3) Avoid relying on anything "
        "the LRM calls unspecified: process order, argument evaluation "
        "order, the value of a variable read at time 0. (4) Keep the "
        "synthesizable subset conservative (Chapter 17) and check every "
        "new construct against every tool in the flow, including lint, CDC, "
        "equivalence and emulation compilers, before adopting it.")

    # ------------------------------------------------------------------
    h2("Lint tools and rule categories")
    p("A linter checks source code against rules without simulating it. "
      "On SoC projects lint is a sign-off gate: RTL is not handed to "
      "synthesis until it is lint-clean against the project rule set, with "
      "every waiver reviewed. Commercial tools include Synopsys SpyGlass "
      "Lint and VC SpyGlass, Cadence Jasper Superlint and HAL, Siemens "
      "Questa Lint and Real Intent Ascent Lint. Open-source options are "
      "Verilator's `--lint-only`, Verible (a style linter and formatter "
      "from the CHIPS Alliance), slang (a fast, strict SV front end with "
      "good diagnostics) and Yosys for structural checks.")
    tbl(["Rule category", "Examples"],
        [["Syntax and semantics", "undeclared identifiers, implicit nets, "
          "port width/direction mismatch, duplicate declarations"],
         ["Width and sign", "truncation, extension, mixed signedness, "
          "unsized constants in concatenations"],
         ["Synthesis-ability", "initial blocks and delays in RTL, "
          "unsynthesizable constructs, real types, === in RTL"],
         ["Sim/synth mismatch", "incomplete sensitivity lists, full_case/"
          "parallel_case pragmas, casex, initialisers"],
         ["Inference", "latches, combinational loops, multiple drivers, "
          "undriven or unloaded signals, constant outputs"],
         ["Clocks and resets", "gated/derived clocks, async reset not "
          "synchronised, mixed edges, reset used as data"],
         ["Style and naming", "file/module name match, one module per "
          "file, naming conventions, default_nettype usage"],
         ["CDC / RDC (separate tools)", "unsynchronised crossings, "
          "reconvergence, reset-domain crossings (companion RTL guide)"]],
        widths=[28, 72], bold_first=True,
        caption="Table 27.6 - Lint rule categories found in every commercial rule set.")

    h2("Running lint on a buggy block")
    code(r"""// buggy.sv - one small block, many classic mistakes (for lint)
module buggy (
  input  logic       clk, rst_n, en,
  input  logic [1:0] sel,
  input  logic [7:0] a, b,
  output logic [7:0] y,
  output logic [3:0] cnt,
  output logic       q2
);
  logic [7:0] m;
  logic       q1;
  logic       unused_sig;

  assign sum_ab = a + b;              // typo'd / undeclared net: implicit 1-bit wire

  always_comb                         // no default: latch on m
    case (sel)
      2'd0: m = a;
      2'd1: m = b;
      2'd2: m = sum_ab;
    endcase

  always @(posedge clk) begin         // blocking assignments in a clocked block
    q1 = en;
    q2 = q1;
  end

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) cnt <= 0;
    else        cnt <= cnt + 1;       // 32-bit expression into 4 bits

  assign y = m;
  assign y = a & b;                   // second driver of y
endmodule""", "buggy.sv")
    out(r"""$ verilator --lint-only -Wall buggy.sv
%Warning-IMPLICIT: buggy.sv:14:10: Signal definition not found, creating implicitly: 'sum_ab'
%Warning-WIDTHTRUNC: buggy.sv:14:17: Operator ASSIGNW expects 1 bits on the Assign RHS,
    but Assign RHS's ADD generates 8 bits.
%Warning-WIDTHEXPAND: buggy.sv:20:15: Operator ASSIGN expects 8 bits on the Assign RHS,
    but Assign RHS's VARREF 'sum_ab' generates 1 bits.
%Warning-MULTIDRIVEN: buggy.sv:6:22: Bits [7:0] of signal 'y' have multiple combinational
    drivers
%Warning-CASEINCOMPLETE: buggy.sv:17:5: Case values incompletely covered (example pattern 0x3)
%Warning-BLKSEQ: buggy.sv:24:8: Blocking assignment '=' in sequential logic process
%Warning-BLKSEQ: buggy.sv:25:8: Blocking assignment '=' in sequential logic process
%Error: Exiting due to 7 warning(s)""", "Verilator 5.020 (context lines omitted; long "
       "lines wrapped at the indented continuation).")
    out(r"""$ iverilog -g2012 -Wall -o /dev/null buggy.sv
buggy.sv:14: warning: implicit definition of wire 'sum_ab'.
buggy.sv:33: error: Unresolved net/uwire y cannot have multiple drivers.
1 error(s) during elaboration.""", "Icarus 12.")
    out(r"""$ yosys -q -p "read_verilog -sv buggy2.sv; proc; check"     # buggy.sv minus line 33
buggy2.sv:14: Warning: Identifier `\sum_ab' is implicitly declared.
ERROR: Latch inferred for signal `\buggy2.\m' from always_comb process
    `\buggy2.$proc$buggy2.sv:0$2'.""", "Yosys 0.33 on a copy without the second "
       "driver of y (the module renamed buggy2).")
    p("Compare what each tool found:")
    tbl(["Bug in buggy.sv", "Verilator -Wall", "iverilog -Wall", "Yosys"],
        [["implicit net sum_ab", "IMPLICIT + width warnings", "warning", "warning"],
         ["latch on m (missing default)", "CASEINCOMPLETE (indirect)", "-",
          "ERROR: latch in always_comb"],
         ["blocking in clocked block", "BLKSEQ x2", "-", "-"],
         ["two drivers of y", "MULTIDRIVEN", "error", "(not run)"],
         ["cnt + 1 into 4 bits", "- (unsized constant exempt)", "-", "-"],
         ["unused_sig never used", "- (not reported in this run)", "-", "-"]],
        widths=[31, 27, 18, 24], bold_first=True,
        caption="Table 27.7 - No single tool caught everything.")
    p("Three lessons. First, the tools are complementary: Verilator gave the "
      "broadest set of warnings, Icarus refused the multiple drivers "
      "outright, and only Yosys reported the latch - because inferring a "
      "latch is a synthesis question and Yosys actually synthesizes the "
      "process. Second, `always_comb` made the latch an __error__ in Yosys "
      "rather than a silent inference: the SystemVerilog procedural "
      "keywords are machine-checkable statements of intent (Chapter 14). "
      "Third, a missing warning is not proof of correctness: the `cnt + 1` "
      "width change is intentional and conventional (and Verilator exempts "
      "it), and the unused signal was not reported in this run - commercial "
      "lint tools with a full rule set would flag both classes.")
    box("key", "Interview insight: how to run lint on a real project",
        "Run it early and often (pre-commit, not pre-tapeout). Start from the "
        "vendor's or company's standard rule set (for RTL sign-off typically "
        "a few hundred rules), never from 'everything on'. Fix, do not "
        "waive, anything in the synthesis-mismatch, latch, multi-driver and "
        "clock/reset categories. Every waiver is written in a waiver file "
        "with the rule, the exact location, a reason and a reviewer, so "
        "that a new instance of the same rule is still reported. Track the "
        "lint count per block as a project metric.")

    h2("Summary")
    bul(["Expression width comes from the operands __and__ the target; "
         "concatenation operands, shift counts and cast results are "
         "self-determined; one unsigned operand makes an expression "
         "unsigned; part-selects are unsigned.",
         "if/case are X-optimistic, ?: is X-pessimistic, 2-state types turn "
         "X into 0, and == with an X yields X: use !== in checkers and "
         "`case inside` instead of casex.",
         "Anything the LRM leaves unspecified - process order in a time step, "
         "argument evaluation order - differs between tools; the real runs "
         "here showed Icarus and Verilator disagreeing on initial-block "
         "order, fork loop capture, static tasks, out-of-range reads and "
         "argument order.",
         "Nonblocking assignments for flops, `automatic` for tasks and "
         "functions, a per-thread copy of loop variables in forks, and "
         "`$urandom` instead of `$random` remove whole classes of bugs.",
         "Variable initialisers are ignored by ASIC synthesis; reset "
         "explicitly.",
         "Lint is a sign-off gate with categories for syntax, width, "
         "synthesis-ability, mismatch, inference, clocks/resets and style; "
         "on the buggy block, Verilator, Icarus and Yosys each caught "
         "something the others missed."])

    h2("Exercises")
    bul(["Predict, then verify with Icarus, the value and width of each: "
         "`4'hF + 4'h1` assigned to a 4-bit and to an 8-bit variable; "
         "`{4'hF + 4'h1}` assigned to 8 bits; `-4'sd1 >>> 1` and "
         "`-4'sd1 >> 1` assigned to a `logic signed [3:0]`.",
         "Write a module where an X on a mux select produces 0 in RTL "
         "simulation but the synthesized gate-level netlist (use Yosys "
         "`synth` and `write_verilog`) produces X in Icarus. Explain which "
         "construct is X-optimistic.",
         "Fix `fork_static.sv` so that it prints 0, 1, 2 and 'called with 1' "
         "plus 'called with 2' on __every__ LRM-compliant simulator, and "
         "explain why each change is required.",
         "Add the directive default_nettype none to buggy.sv and rerun both linters. "
         "Then fix every warning without waivers and confirm that "
         "`verilator --lint-only -Wall` and the Yosys `check` pass are "
         "clean.",
         "Pick five rows of Table 27.3 and write a one-line lint rule for "
         "each (in words) that would detect the bad form. Which of them "
         "cannot be detected statically, and what would you use instead?",
         "Add a $finish to pit_x.sv and run it on Verilator with `--x-initial unique` and "
         "`--x-assign unique` and several seeds. Which lines change, and "
         "why can none of them print `x`?"], ordered=True)


# =============================================================================
#   Chapter 28 - The Verilog/SystemVerilog learning roadmap for SoC and ASIC roles
# =============================================================================
def ch28():
    chapter("The Verilog/SystemVerilog Learning Roadmap for SoC and ASIC Roles")
    p("SystemVerilog is one language, but nobody on a chip team uses all of "
      "it. An RTL designer writes a strict synthesizable subset and must "
      "know it perfectly; a verification engineer lives in classes, "
      "randomization, assertions, coverage and UVM; a DFT or gate-level "
      "engineer reads netlists full of primitives, specify blocks and SDF; "
      "a formal engineer writes almost nothing but SVA. This final chapter "
      "turns the book into a plan: the stages of growth, the language "
      "subset each role needs, a week-by-week study schedule mapped to the "
      "chapters, practice projects, a free tool setup, how to use the IEEE "
      "1800 LRM, and what interviews actually test.")

    # ------------------------------------------------------------------
    h2("Stages of growth")
    tbl(["Stage", "You can...", "Language focus", "Book chapters"],
        [["1. Beginner", "write and simulate small modules and testbenches; read "
          "waveforms", "modules, ports, nets vs variables, operators, always/initial, "
          "blocking vs nonblocking", "1-6"],
         ["2. RTL designer", "write lint-clean, synthesizable, parameterized "
          "blocks; FSMs, FIFOs, bus interfaces; avoid sim/synth mismatch",
          "synthesizable Verilog + SV design subset: logic, always_ff/comb, enums, "
          "structs, packages, interfaces, generate, parameters", "7-17, 27"],
         ["3. DV engineer", "build self-checking, constrained-random, "
          "coverage-driven environments; write assertions; use UVM",
          "classes, randomization, processes/IPC, clocking blocks, SVA, "
          "covergroups, DPI, UVM", "18-26"],
         ["4. Senior / lead", "define methodology and coding rules, review "
          "others' code, debug across tools, own sign-off (lint, CDC, formal, "
          "GLS), mentor", "the whole LRM as a reference; portability; "
          "scheduling semantics; tool behaviour", "all, plus the LRM"]],
        widths=[15, 33, 37, 15], bold_first=True,
        caption="Table 28.1 - Four stages. Most engineers specialise at stage 2 or 3, "
                "then broaden at stage 4.")
    box("intuit", "Depth before breadth",
        "The fastest route to stage 2 is not reading about many features, "
        "but mastering a few rules completely: expression sizing and "
        "signedness (Chapter 4), the scheduler and nonblocking assignment "
        "(Chapter 5), and the synthesizable subset (Chapters 11 and 17). "
        "Interviewers and code reviewers probe exactly those, and almost "
        "every bug in Chapter 27 comes from one of them.")

    # ------------------------------------------------------------------
    h2("Which language subsets each role needs")
    diagram([
        "  +-----------------------------------------------------------------------+",
        "  |  UVM / methodology libraries                       (DV)               |",
        "  +-----------------------------------------------------------------------+",
        "  |  classes, constraints, covergroups, mailboxes, DPI  (DV, modelling)    |",
        "  +-------------------------------------+---------------------------------+",
        "  |  SVA: immediate + concurrent        |  clocking blocks, program       |",
        "  |  (DV, formal, RTL designers)        |  blocks (DV)                    |",
        "  +-------------------------------------+---------------------------------+",
        "  |  SV design subset: logic, always_ff/comb, enum, struct, package,       |",
        "  |  interface, unique/priority, inside, type parameters     (RTL, all)     |",
        "  +-----------------------------------------------------------------------+",
        "  |  Verilog-2005 core: modules, nets/variables, operators, generate,      |",
        "  |  parameters, tasks/functions, system tasks                (everyone)   |",
        "  +-----------------------------------------------------------------------+",
        "  |  gate level: primitives, UDPs, specify, timing checks, SDF (DFT, GLS)  |",
        "  +-----------------------------------------------------------------------+",
    ], "Figure 28.1 - The language as layers. Every role needs the core; each role "
       "then goes deep in a different layer.")
    tbl(["Role", "Must know deeply", "Should know", "Can skip at first"],
        [["RTL design", "synthesizable Verilog-2005; SV design subset (Ch. 12-17); "
          "sizing/signedness; NBA; generate; parameters; lint rules",
          "immediate and simple concurrent SVA; interfaces/modports; basic testbenches",
          "classes, constraints, UVM internals, PLI/VPI"],
         ["Design verification (DV)", "classes and OOP; constrained random; "
          "processes and IPC; clocking blocks; SVA; covergroups; UVM",
          "DPI-C; RTL subset (to read and debug the DUT); scheduling regions",
          "UDPs, specify blocks, switch-level modelling"],
         ["DFT and gate-level simulation", "primitives, UDPs, specify blocks, timing "
          "checks, SDF annotation (Ch. 9); 4-state/X behaviour; netlist reading",
          "RTL subset; testbenches; $sdf_annotate and notifiers; VPI basics",
          "UVM, covergroups"],
         ["Formal verification", "SVA in depth (Ch. 22): sequences, properties, "
          "assume/assert/cover, local variables, liveness; bind",
          "RTL subset; checkers; let; coverage of properties",
          "classes, randomization, UVM"],
         ["Architecture / performance modelling", "classes, queues, associative "
          "arrays, DPI-C to C++ models", "TLM-style transactions; UVM basics",
          "gate level, specify"],
         ["FPGA prototyping / emulation", "synthesizable subset as accepted by the "
          "FPGA/emulator compiler; portability", "SVA synthesizable subset; DPI "
          "for transactors", "UVM internals"]],
        widths=[19, 33, 26, 22], bold_first=True,
        caption="Table 28.2 - Language needs by role.")

    # ------------------------------------------------------------------
    h2("A 22-week study plan")
    p("The plan assumes 8-10 hours per week alongside a job or degree. Each "
      "week has a reading target, a coding target that must run on a free "
      "tool, and a checkpoint question you should be able to answer "
      "without notes. Weeks 1-12 make an RTL-ready engineer; weeks 13-22 "
      "add verification. An RTL-only track can stop after week 12 and spend "
      "weeks 13-16 on projects; a DV-track engineer with an HDL background "
      "can compress weeks 1-8 into four.")
    tbl(["Week", "Chapters", "Build and run", "Checkpoint"],
        [["1", "1-2", "Tool setup; hello-world module and testbench in Icarus and "
          "Verilator", "What does each tool in Table 27.4 do?"],
         ["2", "3", "4-state experiments; nets vs variables; strengths",
          "Why can a wire not be assigned in an always block?"],
         ["3", "4", "Width/sign puzzles from Ch. 27 - predict, then run",
          "Width and sign of a+b*c with mixed operands"],
         ["4", "5", "Scheduler experiments: races, #0, NBA", "Explain the "
          "Active/Inactive/NBA regions"],
         ["5", "6", "ALU with functions and tasks; automatic vs static",
          "When is a function static, and why does it matter?"],
         ["6", "7-8", "Parameterized FIFO with generate; macros; include guards",
          "localparam vs parameter vs a define macro"],
         ["7", "9-10", "Gate-level model with specify; $sdf_annotate "
          "reading; VCD dump", "What does a $setuphold violation do?"],
         ["8", "11", "Synthesize with Yosys; find and fix a latch and a "
          "mismatch", "Three causes of sim/synth mismatch"],
         ["9", "12-13", "Enum FSM with struct outputs; queues and associative "
          "arrays in a TB", "Packed vs unpacked; which are synthesizable?"],
         ["10", "14", "always_comb/ff, unique case, inside, streaming",
          "What does unique case promise the synthesizer?"],
         ["11", "15-16", "Package + interface with modports; virtual interface "
          "in a class", "Why is a virtual interface needed?"],
         ["12", "17, 27", "Refactor an older Verilog block to clean SV; lint "
          "it to zero warnings", "Which SV features are safe in every flow?"],
         ["13", "18", "Class hierarchy for transactions; copy, compare, "
          "polymorphism", "Virtual vs non-virtual method call"],
         ["14", "19", "Constraints on EDA Playground (commercial simulator)",
          "solve-before, dist, soft constraints"],
         ["15", "20-21", "Mailbox pipeline; clocking-block driver",
          "join vs join_any vs join_none; #1step"],
         ["16", "22", "Assertions for a handshake protocol; bind to RTL",
          "Overlapping vs non-overlapping implication"],
         ["17", "23", "Covergroups with crosses and bins; coverage closure",
          "Code vs functional coverage"],
         ["18", "24", "DPI-C reference model; cocotb test of the same DUT",
          "What types can cross DPI?"],
         ["19", "25", "Rebuild Chapter 25's testbench for your own DUT",
          "Where does end-of-test logic live?"],
         ["20", "26", "Port it to UVM on EDA Playground", "Factory, config_db, "
          "objections in your own words"],
         ["21-22", "Project", "One project from Table 28.4, end to end",
          "Present it as if in an interview"]],
        widths=[7, 11, 46, 36], bold_first=True,
        caption="Table 28.3 - A 22-week plan mapped to this book.")

    # ------------------------------------------------------------------
    h2("Practice projects")
    tbl(["Project", "Skills exercised", "Chapters", "Tools"],
        [["Parameterized synchronous and asynchronous FIFO with a self-checking TB",
          "generate, parameters, Gray code, CDC, scoreboard", "7, 11, 25",
          "Icarus, Verilator"],
         ["UART TX/RX with baud generator", "FSMs, counters, testbench tasks, "
          "file I/O for stimulus", "6, 10, 12", "Icarus, GTKWave/Surfer"],
         ["APB or AXI-Lite register block", "structs, packages, interfaces, "
          "address decode, reset values", "12-17", "Verilator, Yosys"],
         ["Pipelined MAC / FIR filter", "signed arithmetic, sizing, "
          "saturation, DPI-C golden model", "4, 24", "Verilator + C"],
         ["Round-robin arbiter with assertions", "SVA, formal proof of fairness "
          "and mutual exclusion", "22", "SymbiYosys (open) or commercial"],
         ["Layered class TB for the register block", "classes, mailboxes, "
          "virtual interfaces, end-of-test", "18, 20, 25", "Verilator"],
         ["UVM agent for APB with RAL", "UVM, factory, sequences, RAL",
          "26", "EDA Playground"],
         ["Tiny RISC-V core (RV32I subset)", "large RTL, decode, pipelines, "
          "self-checking programs", "11-17", "Verilator, Yosys"],
         ["Gate-level sim of a synthesized block", "netlists, SDF-style delays, "
          "X at reset", "9, 11", "Yosys, Icarus"],
         ["Lint-clean refactor of an open-source IP", "reading real code, "
          "portability, waivers", "27", "Verilator, Verible"]],
        widths=[30, 36, 13, 21], bold_first=True,
        caption="Table 28.4 - Practice projects. Publish them in a public repository "
                "with a README and a CI job that runs the tests.")

    # ------------------------------------------------------------------
    h2("Free tools setup")
    tbl(["Tool", "Purpose", "Notes"],
        [["Icarus Verilog", "4-state event-driven simulation", "best for Verilog "
          "and X behaviour; `iverilog -g2012 -Wall`"],
         ["Verilator", "fast 2-state simulation, lint", "`--binary --timing` "
          "builds a stand-alone executable; `--lint-only -Wall`"],
         ["Yosys", "synthesis, structural checks, formal front end",
          "`synth`, `stat`, `check`; SymbiYosys for formal"],
         ["GTKWave / Surfer", "waveform viewers", "VCD/FST from $dumpvars or "
          "Verilator --trace"],
         ["Verible, slang", "style lint/format; strict SV parsing", "good "
          "complements to Verilator lint"],
         ["cocotb", "Python testbenches driving Icarus or Verilator",
          "Chapter 24"],
         ["EDA Playground", "browser access to commercial simulators",
          "the free way to run UVM, constraints, covergroups, full SVA"]],
        widths=[20, 36, 44], bold_first=True,
        caption="Table 28.5 - A complete free tool kit.")
    code(r"""# Debian/Ubuntu (versions used in this book: Icarus 12, Verilator 5.020, Yosys 0.33)
sudo apt install iverilog verilator yosys gtkwave
pip install cocotb                     # optional: Python testbenches
# smoke test on the FIFO of Chapter 25
iverilog -V 2>&1 | head -1
verilator --version
yosys -V
iverilog -g2012 -Wall -o /dev/null sync_fifo.sv
verilator --lint-only -Wall sync_fifo.sv && echo "verilator lint: clean"
yosys -q -p "read_verilog -sv sync_fifo.sv; synth -top sync_fifo; tee -o stat.txt stat"
grep -E "Number of cells|DFF" stat.txt""", "Installation and a three-tool smoke test.")
    out(r"""Icarus Verilog version 12.0 (stable) ()
Verilator 5.020 2024-01-01 rev (Debian 5.020-1)
Yosys 0.33 (git sha1 2584903a060)
sync_fifo.sv:30: vvp.tgt sorry: Case unique/unique0 qualities are ignored.
verilator lint: clean
   Number of cells:                 91
     $_DFFE_PN0P_                    7
     $_DFFE_PP_                     32""", "The smoke test as run. Icarus notes that it "
       "does not check unique; Yosys maps the FIFO to 7 reset flops (pointers and "
       "count) and 32 non-reset flops (the 4 x 8 storage).")
    p("Even the smoke test teaches something: each tool has a different "
      "view of the same file. Icarus simulates it but ignores the `unique` "
      "qualifier; Verilator lints it clean; Yosys shows exactly which "
      "flops have a reset - the storage array has none, as intended. "
      "Setting up a Makefile that runs all three on every change is the "
      "first step toward the multi-tool CI habit of Chapter 27.")

    # ------------------------------------------------------------------
    h2("Reading the IEEE 1800 LRM efficiently")
    p("The IEEE 1800 standard (the Language Reference Manual, LRM) is the "
      "final authority on every question in this book. IEEE 1800-2017 and "
      "1800-2023 run to well over a thousand pages; nobody reads them cover "
      "to cover. They have been available at no cost through the IEEE GET "
      "Program, sponsored by Accellera. Use the standard as a reference, "
      "with a strategy:")
    bul(["**Start from the clause map** (Table 28.6) and go straight to the "
         "clause for your question.",
         "**Read the normative words.** 'Shall' is a requirement on tools and "
         "code; 'may' is permission; 'should' is a recommendation. Notes and "
         "examples are informative, not normative - useful, but they do not "
         "override the text.",
         "**Use Annex A (formal syntax)** to settle what is legal: if a "
         "construct cannot be derived from the BNF, it is not legal, whatever "
         "a tool accepts.",
         "**Look for 'unspecified', 'indeterminate' and 'implementation-"
         "dependent'.** These words mark exactly where tools may differ "
         "(Chapter 27).",
         "**Keep a short list of key tables**: the expression bit-length rules "
         "(Table 11-21 in 1800-2017), operator precedence (Table 11-2), and "
         "the scheduling-region figure in Clause 4.",
         "**Check the version.** Tools lag the standard; a feature new in "
         "1800-2023 may not be in your simulator yet. Test before adopting."])
    tbl(["Clause (1800-2017)", "Topic", "This book"],
        [["4", "Scheduling semantics (event regions)", "5, 21"],
         ["5-7", "Lexical conventions, data types, aggregate types", "2, 3, 12, 13"],
         ["8", "Classes", "18"],
         ["9-10", "Processes; assignment statements", "5, 14, 20"],
         ["11", "Operators and expressions (sizing, signedness)", "4"],
         ["12-13", "Procedural statements; tasks and functions", "6, 14"],
         ["14-15", "Clocking blocks; interprocess synchronization", "20, 21"],
         ["16-17", "Assertions; checkers", "22"],
         ["18-19", "Constrained random; functional coverage", "19, 23"],
         ["20-22", "Utility and I/O system tasks; compiler directives", "8, 10"],
         ["23-27", "Modules, programs, interfaces, packages, generate",
          "2, 7, 15, 16, 21"],
         ["28-33", "Gate/switch level, UDPs, specify, timing checks, SDF, "
          "configurations", "7, 9"],
         ["35", "Direct Programming Interface (DPI)", "24"],
         ["36-40", "PLI/VPI, object model, assertion and coverage APIs", "10, 24"],
         ["Annex A", "Formal syntax (BNF)", "Appendix A"]],
        widths=[20, 60, 20], bold_first=True,
        caption="Table 28.6 - LRM clause map (IEEE 1800-2017 numbering; 1800-2023 is "
                "organised the same way).")
    box("tip", "A 30-minute LRM habit",
        "Whenever this book or a colleague states a rule, find it in the LRM "
        "and read the surrounding paragraph. After a few weeks you will "
        "navigate the standard as quickly as a search engine, and you will "
        "be the person on the team who settles arguments with a clause "
        "number - a senior-level skill.")

    # ------------------------------------------------------------------
    h2("Interview preparation")
    p("Interviews for RTL and DV roles test language understanding far more "
      "than trivia. Expect to write code on a whiteboard or shared editor, "
      "predict the output of short snippets, and explain __why__. Appendix C "
      "has 100 questions with answers; Table 28.7 lists the topics that come "
      "up most.")
    tbl(["Area", "Topics that come up again and again"],
        [["Core language", "blocking vs nonblocking and the scheduler; wire vs "
          "reg vs logic; 4-state values; == vs ===; expression sizing and "
          "signedness puzzles; $display vs $strobe vs $monitor"],
         ["RTL design", "latch inference; FSM coding styles (one/two/three "
          "always blocks, one-hot vs binary); synchronous vs asynchronous "
          "reset; FIFO depth and full/empty logic; clock gating; CDC "
          "synchronizers and Gray code; sim/synth mismatch; parameterization "
          "and generate"],
         ["SystemVerilog design", "always_comb/ff/latch; unique/priority; "
          "packed vs unpacked; structs and unions; enums; interfaces and "
          "modports; packages and scoping"],
         ["Verification language", "classes, inheritance, virtual methods, "
          "polymorphism, shallow vs deep copy; static members; parameterized "
          "classes; virtual interfaces; fork/join variants and disable fork; "
          "mailboxes, semaphores, events; automatic vs static"],
         ["Randomization and coverage", "rand vs randc; constraint operators; "
          "solve-before; dist; soft; pre/post_randomize; covergroups, bins, "
          "crosses; code vs functional coverage"],
         ["Assertions", "immediate vs concurrent; implication operators; "
          "sequences, repetition, throughout, within; $rose/$fell/$stable/$past; "
          "disable iff; assume/cover; bind"],
         ["UVM", "component vs object; phases; factory and overrides; "
          "config_db; sequences, sequencer, driver handshake; TLM and analysis "
          "ports; objections; RAL basics"],
         ["Practical", "debug a failing test from a log; write a scoreboard; "
          "code a small block (arbiter, FIFO, edge detector, counter) live; "
          "explain a past project in depth"]],
        widths=[22, 78], bold_first=True,
        caption="Table 28.7 - Interview topics by area.")
    box("key", "How to answer a language question well",
        "State the rule, give a two-line example, name the consequence in "
        "hardware or in the testbench, and mention the pitfall or tool "
        "difference if there is one. For 'blocking vs nonblocking': the "
        "rule (NBA updates happen in the NBA region after all RHS are "
        "evaluated), the example (a two-flop shift register), the "
        "consequence (blocking in clocked logic can collapse pipeline "
        "stages and create races), and the pitfall (race.sv in Chapter 27 "
        "gave different answers on two simulators). That structure signals "
        "understanding rather than memorisation.")

    # ------------------------------------------------------------------
    h2("Final checklist")
    checklist("Before you call yourself fluent in Verilog and SystemVerilog", [
        "I can predict the width and signedness of any expression and explain "
        "every result in Chapter 27's pit_expr.sv.",
        "I can explain the event regions of one time step and why nonblocking "
        "assignments prevent races between flops.",
        "I write RTL that is lint-clean under Verilator -Wall, has no latches, "
        "no implicit nets, one driver per signal, and explicit resets.",
        "I use always_ff/always_comb, enums, structs, packages and interfaces "
        "in RTL, and know which SV features every tool in my flow accepts.",
        "I can read a gate-level netlist with primitives and specify blocks, "
        "and know what SDF annotation and timing-check notifiers do.",
        "I can build a layered class-based testbench with a monitor, "
        "scoreboard and end-of-test logic, and prove it fails on a planted bug.",
        "I can write constraints, covergroups and concurrent assertions, and "
        "know which simulator I need to run them.",
        "I can explain how the UVM factory, config_db, phases and objections "
        "work in terms of SystemVerilog classes and static members.",
        "I know the portability differences between at least two simulators "
        "and run more than one in my regression.",
        "I can find the answer to a language question in the IEEE 1800 LRM "
        "in a few minutes and cite the clause.",
    ])

    h2("Summary")
    bul(["Growth runs from beginner through RTL designer and DV engineer to "
         "senior/lead; each stage adds a layer of the language and a level of "
         "responsibility for quality.",
         "Every role needs the Verilog core and the scheduling and sizing "
         "rules; RTL goes deep on the synthesizable subset, DV on OOP, "
         "randomization, SVA, coverage and UVM, DFT/gate-level on primitives, "
         "specify and SDF, and formal on SVA.",
         "A 22-week plan maps weekly reading, a runnable exercise and a "
         "checkpoint question to the chapters of this book, followed by an "
         "end-to-end project.",
         "Icarus, Verilator and Yosys (plus a waveform viewer and EDA "
         "Playground for commercial-only features) form a complete free "
         "tool kit; run them together from the start.",
         "Use the IEEE 1800 LRM as a reference: clause map, normative words, "
         "Annex A syntax, and the words that mark tool-dependent behaviour.",
         "Interviews test understanding of rules and consequences; answer "
         "with rule, example, consequence and pitfall."])

    h2("Exercises")
    bul(["Place yourself in Table 28.1 honestly. List the three chapters whose "
         "checkpoint questions you cannot yet answer without notes and schedule "
         "them for the next two weeks.",
         "Set up a repository with a Makefile that runs Icarus, Verilator lint "
         "and Yosys synthesis on every RTL file, plus a CI job that fails on a "
         "new warning. Add the FIFO of Chapter 25 as the first block.",
         "Choose one project from Table 28.4 for your target role and write a "
         "one-page verification plan for it before writing any RTL: features, "
         "checks, coverage goals and the tool that will run each part.",
         "Find in the IEEE 1800 LRM the rules behind three results in Chapter "
         "27 (for example: why cat9 is 44, why the fork prints 3,3,3, why a "
         "static function initialiser runs once) and write down the clause "
         "numbers.",
         "Write your own answers to ten questions from Table 28.7 using the "
         "rule-example-consequence-pitfall structure, then compare them with "
         "Appendix C."], ordered=True)
