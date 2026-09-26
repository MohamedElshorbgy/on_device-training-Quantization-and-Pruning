"""Part VI - Practice and Roadmap (Chapters 24-26).

Chapter 24 surveys the open-source ASIC flow and runs what a plain Linux
container can run against real SkyWater SKY130 files (Liberty corners and
LEFs from the OpenROAD / OpenROAD-flow-scripts sky130hd platforms, per-cell
JSON timing and cell GDS from google/skywater-pdk-libs-sky130_fd_sc_hd).
Chapter 25 takes an int8 MAC block from spec to the GDSII hand-off:
Icarus Verilog 12 simulation, Verilator 5.020 lint, Yosys 0.33 synthesis,
zero-delay gate-level simulation, and Python timing/floorplan/power models
reading the real Liberty data. Every out() card is pasted verbatim from
those runs; OpenROAD steps are shown as commands and marked as not run.
Chapter 26 is the career roadmap and interview preparation.
"""

from asic_guide.common import *  # noqa: F401,F403

# ---------------------------------------------------------------------------
# Sources and captured outputs (generated from the files that were run)
# ---------------------------------------------------------------------------
LEF_SRC = [
    '# lefstack.py - summarise the SKY130 routing stack from the technology LEF',
    'import re',
    't = open("sky130_fd_sc_hd.tlef").read()',
    'site = re.search(r"SITE unithd\\s+(.*?)END unithd", t, re.S).group(1)',
    'print("SITE unithd:", " ".join(re.search(r"SIZE ([\\d.]+) BY ([\\d.]+)", site).groups()), "um")',
    'print("%-6s %-8s %-10s %7s %7s %9s"',
    '      % ("layer", "type", "direction", "pitch", "width", "min area"))',
    'for m in re.finditer(r"\\nLAYER (\\w+)\\s+(.*?)\\nEND \\1", t, re.S):',
    '    name, body = m.groups()',
    '    typ = re.search(r"TYPE (\\w+)", body).group(1)',
    '    if typ not in ("ROUTING", "CUT"): continue',
    '    d = re.search(r"DIRECTION (\\w+)", body)',
    '    p = re.search(r"\\n\\s*PITCH ([\\d.]+)", body)',
    '    w = re.search(r"\\n\\s*WIDTH ([\\d.]+)", body)',
    '    a = re.search(r"\\n\\s*AREA ([\\d.]+)", body)',
    '    print("%-6s %-8s %-10s %7s %7s %9s" % (name, typ, d.group(1) if d else "-",',
    '          p.group(1) if p else "-", w.group(1) if w else "-", a.group(1) if a else "-"))',
]

LEF_OUT = [
    'SITE unithd: 0.46 2.72 um',
    'layer  type     direction    pitch   width  min area',
    'li1    ROUTING  VERTICAL      0.46    0.17    0.0561',
    'mcon   CUT      -                -    0.17         -',
    'met1   ROUTING  HORIZONTAL    0.34    0.14     0.083',
    'via    CUT      -                -    0.15         -',
    'met2   ROUTING  VERTICAL      0.46    0.14    0.0676',
    'via2   CUT      -                -     0.2         -',
    'met3   ROUTING  HORIZONTAL    0.68     0.3      0.24',
    'via3   CUT      -                -     0.2         -',
    'met4   ROUTING  VERTICAL      0.92     0.3      0.24',
    'via4   CUT      -                -     0.8         -',
    'met5   ROUTING  HORIZONTAL     3.4     1.6         4',
]

GDS_SRC = [
    '# gdsrep.py - inspect SKY130 standard-cell GDS files with the KLayout Python API',
    'import sys, re',
    'import klayout.db as db',
    'NAMES = {(64, 20): "nwell", (65, 20): "diff", (66, 20): "poly", (66, 44): "licon1",',
    '         (67, 20): "li1", (67, 44): "mcon", (68, 20): "met1", (78, 44): "hvtp",',
    '         (81, 4): "areaid.sc", (93, 44): "nsdm", (94, 20): "psdm", (95, 20): "npc",',
    '         (236, 0): "prBoundary"}',
    'lef = open("sky130_fd_sc_hd_merged.lef").read()',
    'for f in sys.argv[1:]:',
    '    ly = db.Layout(); ly.read(f); top = ly.top_cell()',
    '    size = re.search(r"MACRO %s\\s.*?SIZE\\s+([\\d.]+) BY\\s+([\\d.]+)" % top.name, lef, re.S)',
    '    w, h = float(size.group(1)), float(size.group(2))',
    '    print("%s: LEF SIZE %.2f x %.2f um" % (top.name, w, h))',
    '    rows = []',
    '    for li in ly.layer_indexes():',
    '        inf = ly.get_info(li); key = (inf.layer, inf.datatype)',
    '        if key not in NAMES: continue                 # skip pin/label purposes',
    '        r = db.Region(top.begin_shapes_rec(li)); n = r.count(); r.merge()',
    '        bb = r.bbox()',
    '        rows.append((key, NAMES[key], n, r.area() * ly.dbu ** 2,',
    '                     bb.width() * ly.dbu, bb.height() * ly.dbu))',
    '    for key, nm, n, a, w, h in sorted(rows):',
    '        print("  %3d/%-2d %-10s %3d shapes  %7.3f um^2   extent %5.2f x %4.2f"',
    '              % (key[0], key[1], nm, n, a, w, h))',
]

GDS_OUT = [
    'sky130_fd_sc_hd__inv_1: LEF SIZE 1.38 x 2.72 um',
    '   64/20 nwell        1 shapes    2.825 um^2   extent  1.76 x 1.60',
    '   65/20 diff         2 shapes    1.105 um^2   extent  0.67 x 2.25',
    '   66/20 poly         1 shapes    0.469 um^2   extent  0.43 x 2.51',
    '   66/44 licon1      11 shapes    0.318 um^2   extent  0.59 x 2.11',
    '   67/20 li1          6 shapes    1.646 um^2   extent  1.38 x 2.89',
    '   67/44 mcon         6 shapes    0.173 um^2   extent  1.09 x 2.89',
    '   68/20 met1         2 shapes    1.325 um^2   extent  1.38 x 3.20',
    '   78/44 hvtp         1 shapes    2.029 um^2   extent  1.38 x 1.47',
    '   81/4  areaid.sc    1 shapes    3.754 um^2   extent  1.38 x 2.72',
    '   93/44 nsdm         1 shapes    1.663 um^2   extent  1.38 x 1.21',
    '   94/20 psdm         1 shapes    2.146 um^2   extent  1.38 x 1.55',
    '   95/20 npc          1 shapes    0.511 um^2   extent  1.38 x 0.37',
    '  236/0  prBoundary   1 shapes    3.754 um^2   extent  1.38 x 2.72',
    'sky130_fd_sc_hd__dfxtp_1: LEF SIZE 7.36 x 2.72 um',
    '   66/20 poly        14 shapes    5.511 um^2   extent  6.88 x 2.51',
    '   66/44 licon1      50 shapes    1.445 um^2   extent  6.99 x 2.13',
    '  236/0  prBoundary   1 shapes   20.019 um^2   extent  7.36 x 2.72',
]

DU_SRC = [
    '# Remove cells a synthesis run must not use (power-domain, probe, clock-tree,',
    '# delay and tri-state cells) - the same idea as ORFS DONT_USE_CELLS.',
    'import re, sys',
    "DONT = re.compile(r'sky130_fd_sc_hd__(lpflow_|probe|clkinv|clkbuf|clkdly|dlygate|'",
    "                  r'dlymetal|dlclkp|sdlclkp|einv|ebuf|macro|dlx|dlrt|dlrbn|dlrbp)')",
    'for src, dst in zip(sys.argv[1::2], sys.argv[2::2]):',
    "    lines = open(src).read().split('\\n'); out = []; i = 0; kept = drop = 0",
    '    while i < len(lines):',
    '        m = re.match(r\'\\s*cell\\s*\\(\\s*"?(\\w+)"?\\s*\\)\', lines[i])',
    '        if m and DONT.search(m.group(1)):',
    '            d = 0',
    '            while True:',
    "                d += lines[i].count('{') - lines[i].count('}'); i += 1",
    '                if d == 0: break',
    '            drop += 1; continue',
    '        if m: kept += 1',
    '        out.append(lines[i]); i += 1',
    "    open(dst, 'w').write('\\n'.join(out))",
    '    print("%-36s kept %3d cells, dropped %3d" % (src, kept, drop))',
]

DU_OUT = [
    'sky130_fd_sc_hd__tt_025C_1v80.lib    kept 329 cells, dropped  99',
]

LIBSUM_OUT = [
    'tt_025C_1v80: 428 cells in 158 functional families',
    'inverter drive strengths: [1, 2, 4, 6, 8, 12, 16]',
    'corner           inv_1  nand2_1   xor2_1  dfxtp_1   (ns, input slew 0.1 ns, load 0.01 pF)',
    'ss_n40C_1v40     0.291    0.355    0.827    1.418',
    'ss_100C_1v60     0.153    0.194    0.400    0.715',
    'tt_100C_1v80     0.106    0.114    0.231    0.365',
    'tt_025C_1v80     0.114    0.123    0.241    0.368',
    'ff_n40C_1v95     0.093    0.099    0.163    0.238',
]

CNT_V = [
    'module counter (input clk, input rst_n, input en, output reg [7:0] q);',
    '  always @(posedge clk or negedge rst_n)',
    "    if (!rst_n)  q <= 8'd0;",
    "    else if (en) q <= q + 8'd1;",
    'endmodule',
]

CNT_YS = [
    'read_liberty -lib ../tt.lib',
    'read_verilog counter.v',
    'synth -top counter',
    'dfflibmap -liberty ../tt.lib',
    'abc -liberty ../tt.lib',
    'opt_clean',
    'stat -liberty ../tt.lib',
    'write_verilog -noattr counter_net.v',
]

CNT_STAT = [
    '=== counter ===',
    '   Number of wires:                 19',
    '   Number of wire bits:             26',
    '   Number of public wires:           4',
    '   Number of public wire bits:      11',
    '   Number of cells:                 23',
    '     sky130_fd_sc_hd__a21oi_1        1',
    '     sky130_fd_sc_hd__a31oi_1        1',
    '     sky130_fd_sc_hd__and3_1         1',
    '     sky130_fd_sc_hd__and4_1         1',
    '     sky130_fd_sc_hd__dfrtp_1        8',
    '     sky130_fd_sc_hd__nand2_1        2',
    '     sky130_fd_sc_hd__nand3_1        1',
    '     sky130_fd_sc_hd__nor2_1         2',
    '     sky130_fd_sc_hd__xnor2_1        3',
    '     sky130_fd_sc_hd__xor2_1         3',
    "   Chip area for module '\\counter': 299.036800",
]

MAC_SV = [
    '`timescale 1ns/1ps',
    '// mac_int8: streaming signed int8 dot-product engine (Chapter 25 case study)',
    '// One (a,b) pair per accepted input beat; in_last marks the final pair of a',
    '// vector. The block returns sum(a*b) on the output channel, then restarts.',
    'module mac_int8 #(',
    '  parameter int ACC_W = 24                // 24 bits: <= 511 terms never overflow',
    ') (',
    '  input  logic                    clk,',
    '  input  logic                    rst_n,     // async assert, sync deassert',
    '  // input stream (valid/ready)',
    '  input  logic                    in_valid,',
    '  output logic                    in_ready,',
    '  input  logic signed [7:0]       in_a,',
    '  input  logic signed [7:0]       in_b,',
    '  input  logic                    in_last,',
    '  // output stream (valid/ready)',
    '  output logic                    out_valid,',
    '  input  logic                    out_ready,',
    '  output logic signed [ACC_W-1:0] out_acc',
    ');',
    '  // ---- stage 1: registered product -------------------------------------',
    '  logic               p_valid, p_last;',
    '  logic signed [15:0] p_q;',
    '  // ---- stage 2: accumulator and output register ------------------------',
    '  logic signed [ACC_W-1:0] acc_q;',
    '  logic signed [ACC_W-1:0] sum;',
    '  logic                    s2_fire, s1_ready;',
    '',
    '  // a non-last product can always retire; a last one needs the output slot',
    '  assign s2_fire  = p_valid && (!p_last || !out_valid || out_ready);',
    '  assign s1_ready = !p_valid || s2_fire;',
    '  assign in_ready = s1_ready;',
    "  assign sum      = acc_q + ACC_W'(p_q);     // sign-extending add",
    '',
    '  always_ff @(posedge clk or negedge rst_n)',
    "    if (!rst_n)        p_valid <= 1'b0;",
    '    else if (s1_ready) p_valid <= in_valid;',
    '',
    '  // datapath flops without reset: smaller cells, no reset-tree load',
    '  always_ff @(posedge clk)',
    '    if (s1_ready && in_valid) begin',
    '      p_q    <= in_a * in_b;                 // 8x8 signed -> 16 bits',
    '      p_last <= in_last;',
    '    end',
    '',
    '  always_ff @(posedge clk or negedge rst_n)',
    '    if (!rst_n) begin',
    "      acc_q     <= '0;",
    "      out_valid <= 1'b0;",
    "      out_acc   <= '0;",
    '    end else begin',
    "      if (out_valid && out_ready) out_valid <= 1'b0;",
    '      if (s2_fire) begin',
    '        if (p_last) begin',
    '          out_acc   <= sum;',
    "          out_valid <= 1'b1;",
    "          acc_q     <= '0;",
    '        end else begin',
    '          acc_q     <= sum;',
    '        end',
    '      end',
    '    end',
    'endmodule',
]

TB_SV = [
    '`timescale 1ns/1ps',
    'module tb_mac;',
    '  logic clk = 0, rst_n = 0;',
    '  always #5 clk = ~clk;                          // 100 MHz',
    '  logic in_valid = 0, in_last = 0, out_ready = 0;',
    '  logic signed [7:0] in_a = 0, in_b = 0;',
    '  logic in_ready, out_valid;',
    '  logic signed [23:0] out_acc;',
    '  mac_int8 dut (.*);',
    '',
    '  integer exp_q [0:1023];                         // expected-result FIFO',
    '  integer wr = 0, rd = 0, errors = 0, beats = 0, stalls = 0;',
    '  integer n, len, i, sum, maxv = 0;',
    '',
    '  // consumer: random back-pressure, checks every result in order',
    '  always @(posedge clk) begin',
    '    out_ready <= ($urandom % 4) != 0;            // ready 75% of cycles',
    '    if (out_valid && !out_ready) stalls = stalls + 1;',
    '    if (out_valid && out_ready) begin',
    '      if (out_acc !== exp_q[rd]) begin',
    '        errors = errors + 1;',
    '        $display("MISMATCH vec %0d: got %0d exp %0d", rd, out_acc, exp_q[rd]);',
    '      end',
    '      if (out_acc > maxv) maxv = out_acc;',
    '      rd = rd + 1;',
    '    end',
    '  end',
    '',
    '  task automatic send(input logic signed [7:0] a, b, input logic last);',
    '    in_valid <= 1; in_a <= a; in_b <= b; in_last <= last;',
    '    @(posedge clk);',
    '    while (!in_ready) @(posedge clk);',
    '    beats = beats + 1;',
    '    in_valid <= 0;',
    '    if ($urandom % 3 == 0) @(posedge clk);       // random idle gaps',
    '  endtask',
    '',
    '  initial if ($test$plusargs("vcd")) begin     // activity for power estimation',
    '    $dumpfile("mac.vcd"); $dumpvars(1, dut);',
    '  end',
    '',
    '  initial begin',
    '    repeat (3) @(posedge clk);',
    '    rst_n <= 1;',
    '    // directed corners: 1-term vector, worst-case 511 x (-128 * -128)',
    '    send(-128, -128, 1); exp_q[wr] = 16384; wr = wr + 1;',
    '    for (i = 0; i < 511; i = i + 1) send(-128, -128, i == 510);',
    '    exp_q[wr] = 511 * 16384; wr = wr + 1;',
    '    send(127, -128, 0); send(-1, 1, 1); exp_q[wr] = -16257; wr = wr + 1;',
    '    // 200 random vectors of random length 1..64',
    '    for (n = 0; n < 200; n = n + 1) begin',
    '      len = 1 + $urandom % 64; sum = 0;',
    '      for (i = 0; i < len; i = i + 1) begin',
    '        in_a = $urandom; in_b = $urandom;        // blocking: sample now',
    '        sum = sum + in_a * in_b;',
    '        send(in_a, in_b, i == len - 1);',
    '      end',
    '      exp_q[wr] = sum; wr = wr + 1;',
    '    end',
    '    wait (rd == wr);',
    '    repeat (2) @(posedge clk);',
    '    $display("vectors=%0d beats=%0d out_stall_cycles=%0d errors=%0d",',
    '             wr, beats, stalls, errors);',
    '    $display("largest result checked: %0d (2^23-1 = %0d)", maxv, 2**23-1);',
    '    if (errors == 0) $display("TEST PASSED"); else $display("TEST FAILED");',
    '    $finish;',
    '  end',
    'endmodule',
]

SIM_OUT = [
    'vectors=203 beats=7430 out_stall_cycles=70 errors=0',
    'largest result checked: 8372224 (2^23-1 = 8388607)',
    'TEST PASSED',
    'tb_mac.sv:66: $finish called at 98925000 (1ps)',
]

V1_OUT = [
    'MISMATCH vec 2: got 114815 exp -16257',
    'MISMATCH vec 3: got 193344 exp -3264',
    'MISMATCH vec 4: got 185953 exp -10655',
    'MISMATCH vec 5: got 1275441 exp 30257',
    '...',
    'vectors=203 beats=7430 out_stall_cycles=70 errors=201',
    'largest result checked: 8372224 (2^23-1 = 8388607)',
    'TEST FAILED',
    'tb_mac.sv:66: $finish called at 98925000 (1ps)',
]

LINT_V0 = [
    "%Warning-WIDTHEXPAND: mac_int8.sv:32:27: Operator ADD expects 24 bits on the RHS, but RHS's",
    "    VARREF 'p_q' generates 16 bits.",
    "                                       : ... note: In instance 'mac_int8'",
    '   32 |   assign sum      = acc_q + p_q;',
    '      |                           ^',
    "%Warning-UNUSEDSIGNAL: mac_int8.sv:21:40: Signal is not driven, nor used: 'dbg'",
    "                                        : ... note: In instance 'mac_int8'",
    '   21 |   logic               p_valid, p_last, dbg;',
    '      |                                        ^~~',
    '%Error: Exiting due to 2 warning(s)',
]

SYN_YS = [
    '# syn.ys - Yosys 0.33 synthesis of mac_int8 onto SKY130 hd (tt_025C_1v80)',
    '# ../tt.lib = sky130_fd_sc_hd__tt_025C_1v80.lib with dont-use cells removed',
    'read_verilog -sv mac_int8.sv',
    'synth -top mac_int8 -flatten          # generic synthesis: RTL -> $_AND_/$_DFF_ cells',
    'dfflibmap -liberty ../tt.lib          # map flops onto real Liberty flip-flops',
    'abc -liberty ../tt.lib -constr abc.constr -D 10000   # map logic, 10 ns target',
    'opt_clean',
    'hilomap -hicell sky130_fd_sc_hd__conb_1 HI -locell sky130_fd_sc_hd__conb_1 LO',
    "stat -liberty ../tt.lib               # cell count and area from Liberty 'area'",
    'write_verilog -noattr mac_net.v       # netlist for GLS and for the P&R flow',
    'write_json mac_net.json               # same netlist, for the Python STA/power models',
]

MAC_STAT = [
    '=== mac_int8 ===',
    '   Number of wires:                591',
    '   Number of wire bits:            666',
    '   Number of public wires:          15',
    '   Number of public wire bits:      90',
    '   Number of cells:                644',
    '     sky130_fd_sc_hd__a2111oi_0      1',
    '     sky130_fd_sc_hd__a211oi_1       1',
    '     sky130_fd_sc_hd__a21boi_0       2',
    '     sky130_fd_sc_hd__a21o_1         6',
    '     sky130_fd_sc_hd__a21oi_1       20',
    '     sky130_fd_sc_hd__a22o_1         8',
    '     sky130_fd_sc_hd__a22oi_1        3',
    '     sky130_fd_sc_hd__a31oi_1        4',
    '     sky130_fd_sc_hd__and2_1         8',
    '     sky130_fd_sc_hd__and3_1         9',
    '     sky130_fd_sc_hd__and4_1         3',
    '     sky130_fd_sc_hd__buf_1         29',
    '     sky130_fd_sc_hd__dfrtp_1       50',
    '     sky130_fd_sc_hd__dfxtp_1       17',
    '     sky130_fd_sc_hd__inv_1         10',
    '     sky130_fd_sc_hd__maj3_1        41',
    '     sky130_fd_sc_hd__mux2_2         4',
    '     sky130_fd_sc_hd__mux2i_1        1',
    '     sky130_fd_sc_hd__nand2_1      121',
    '     sky130_fd_sc_hd__nand2b_1       5',
    '     sky130_fd_sc_hd__nand3_1        6',
    '     sky130_fd_sc_hd__nand3b_1       1',
    '     sky130_fd_sc_hd__nand4_1        4',
    '     sky130_fd_sc_hd__nand4b_1       1',
    '     sky130_fd_sc_hd__nor2_1        44',
    '     sky130_fd_sc_hd__nor2b_1        9',
    '     sky130_fd_sc_hd__nor3_1         5',
    '     sky130_fd_sc_hd__o211a_1        1',
    '     sky130_fd_sc_hd__o21a_1         3',
    '     sky130_fd_sc_hd__o21ai_0       66',
    '     sky130_fd_sc_hd__o21bai_1       2',
    '     sky130_fd_sc_hd__o22ai_1        1',
    '     sky130_fd_sc_hd__o311a_1        2',
    '     sky130_fd_sc_hd__o31ai_1        7',
    '     sky130_fd_sc_hd__o32ai_1        1',
    '     sky130_fd_sc_hd__o41ai_1        1',
    '     sky130_fd_sc_hd__or2_2          5',
    '     sky130_fd_sc_hd__or3_1          8',
    '     sky130_fd_sc_hd__xnor2_1       76',
    '     sky130_fd_sc_hd__xnor3_1        6',
    '     sky130_fd_sc_hd__xor2_1        44',
    '     sky130_fd_sc_hd__xor3_1         8',
    "   Chip area for module '\\mac_int8': 5365.145600",
]

ABC_OUT = [
    'ABC: WireLoad = "none" Gates = 577 ( 6.8 %) Cap = 5.5 ff ( 6.0 %) Area = 3773.62 ( 82.5 %)',
    '    Delay = 6882.77 ps ( 7.6 %)',
]

CORNERS = [
    'ss_n40C_1v40   T=10.0  setup WNS -30.663  TNS -805.230  viol  53  | hold WNS  1.201',
    'ss_100C_1v60   T=10.0  setup WNS  -8.478  TNS -144.605  viol  34  | hold WNS  0.782',
    'tt_100C_1v80   T=10.0  setup WNS   1.117  TNS    0.000  viol   0  | hold WNS  0.366',
    'tt_025C_1v80   T=10.0  setup WNS   0.829  TNS    0.000  viol   0  | hold WNS  0.343',
    'ff_n40C_1v95   T=10.0  setup WNS   4.191  TNS    0.000  viol   0  | hold WNS  0.176',
    'ss_n40C_1v40   T=20.0  setup WNS -20.663  TNS -373.744  viol  38  | hold WNS  1.201',
    'ss_100C_1v60   T=20.0  setup WNS   1.522  TNS    0.000  viol   0  | hold WNS  0.782',
    'tt_100C_1v80   T=20.0  setup WNS  10.452  TNS    0.000  viol   0  | hold WNS  0.366',
    'tt_025C_1v80   T=20.0  setup WNS  10.166  TNS    0.000  viol   0  | hold WNS  0.343',
    'ff_n40C_1v95   T=20.0  setup WNS  11.850  TNS    0.000  viol   0  | hold WNS  0.176',
]

PATH_SS = [
    'ss_100C_1v60   T=20.0  setup WNS   1.522  TNS    0.000  viol   0  | hold WNS  0.782',
    'worst setup endpoint acc_q[23]/D: arrival 17.599, setup 0.379, slack 1.522',
    '     0.815  slew 0.166  dfrtp_1    CLK->Q',
    '     1.192  slew 0.318  xnor2_1    A->Y',
    '     1.751  slew 0.513  o21ai_0    A2->Y',
    '     2.751  slew 0.171  maj3_1     C->X',
    '     3.615  slew 0.172  maj3_1     C->X',
    '     4.478  slew 0.172  maj3_1     C->X',
    '     5.342  slew 0.172  maj3_1     C->X',
    '     6.205  slew 0.172  maj3_1     C->X',
    '     7.069  slew 0.172  maj3_1     C->X',
    '     7.932  slew 0.172  maj3_1     C->X',
    '     8.796  slew 0.172  maj3_1     C->X',
    '     9.659  slew 0.172  maj3_1     C->X',
    '    10.523  slew 0.172  maj3_1     C->X',
    '    11.386  slew 0.172  maj3_1     C->X',
    '    12.250  slew 0.172  maj3_1     C->X',
    '    13.113  slew 0.172  maj3_1     C->X',
    '    14.038  slew 0.232  maj3_1     C->X',
    '    14.300  slew 0.221  nand4_1    A->Y',
    '    15.487  slew 1.176  a2111oi_0  A1->Y',
    '    16.370  slew 0.583  o21ai_0    A1->Y',
    '    17.038  slew 0.437  a211oi_1   A2->Y',
    '    17.599  slew 0.336  o32ai_1    A2->Y',
    'worst hold endpoint p_q[5]/D: early arrival 0.819, hold req -0.063, slack 0.782',
]

GLS_YS = [
    'read_liberty -ignore_miss_func used_tt.lib',
    'read_verilog mac_net.v',
    'hierarchy -top mac_int8',
    'flatten',
    'opt_clean',
    'write_verilog -noattr gls_flat.v',
]

GLS_OUT = [
    'vectors=203 beats=7430 out_stall_cycles=70 errors=0',
    'largest result checked: 8372224 (2^23-1 = 8388607)',
    'TEST PASSED',
    'tb_mac.sv:66: $finish called at 98925000 (1ps)',
]

FP_SRC = [
    '# floorplan.py - size the core of mac_int8 from the real synthesized cell area',
    'import math',
    "CELL_AREA = 5365.1456            # um^2, Yosys 'stat -liberty' on tt_025C_1v80",
    'SITE_W, ROW_H = 0.46, 2.72       # unithd site from sky130_fd_sc_hd.tlef',
    'TAP_W, TAP_PITCH = 0.46, 14.0    # tapvpwrvgnd_1, ORFS tapcell -distance 14 (um)',
    'MARGIN = 10.0                    # core-to-die margin for pins and power ring (um)',
    'print("cell area from synthesis: %.1f um^2" % CELL_AREA)',
    'print(" util  core W x H (um)   rows  sites/row  taps  tap area  die W x H (um)  die mm^2")',
    'for util in (0.40, 0.50, 0.60, 0.70):',
    '    side = math.sqrt(CELL_AREA / util)             # aspect ratio 1',
    '    rows = math.ceil(side / ROW_H)',
    '    h = rows * ROW_H',
    '    sites = math.ceil((CELL_AREA / util / h) / SITE_W)',
    '    w = sites * SITE_W',
    '    taps = rows * (math.floor(w / TAP_PITCH) + 1)',
    '    dw, dh = w + 2 * MARGIN, h + 2 * MARGIN',
    '    print(" %3.0f%%  %6.2f x %6.2f  %4d  %9d  %4d  %8.1f  %6.2f x %6.2f  %8.4f"',
    '          % (util * 100, w, h, rows, sites, taps, taps * TAP_W * ROW_H, dw, dh, dw * dh / 1e6))',
]

FP_OUT = [
    'cell area from synthesis: 5365.1 um^2',
    ' util  core W x H (um)   rows  sites/row  taps  tap area  die W x H (um)  die mm^2',
    '  40%  115.00 x 116.96    43        250   387     484.2  135.00 x 136.96    0.0185',
    '  50%  101.20 x 106.08    39        220   312     390.4  121.20 x 126.08    0.0153',
    '  60%   94.30 x  95.20    35        205   245     306.5  114.30 x 115.20    0.0132',
    '  70%   85.56 x  89.76    33        186   231     289.0  105.56 x 109.76    0.0116',
]

PWR_OUT = [
    'simulated cycles: 9892',
    '  in_a     toggles/bit/cycle = 0.351',
    '  p_q      toggles/bit/cycle = 0.344',
    '  acc_q    toggles/bit/cycle = 0.224',
    '  sum      toggles/bit/cycle = 0.299',
    '  out_acc  toggles/bit/cycle = 0.010',
    'alpha (0->1 per cycle): registers 0.087  combinational (sum bus) 0.149',
    'tt_025C_1v80 @ 50 MHz: C_clk 0.128 pF, C_reg 0.483 pF, C_comb 3.493 pF',
    '   clock-net 0.0208 mW  flop-CLK internal 0.1351 mW  reg nets 0.0068 mW  comb nets 0.0846 mW',
    '   leakage 2.21 nW   total (excl. comb internal power) 0.2473 mW',
    'tt_100C_1v80 @ 50 MHz: C_clk 0.132 pF, C_reg 0.494 pF, C_comb 3.567 pF',
    '   clock-net 0.0214 mW  flop-CLK internal 0.1372 mW  reg nets 0.0070 mW  comb nets 0.0864 mW',
    '   leakage 684.05 nW   total (excl. comb internal power) 0.2526 mW',
    'ss_100C_1v60 @ 50 MHz: C_clk 0.121 pF, C_reg 0.481 pF, C_comb 3.454 pF',
    '   clock-net 0.0155 mW  flop-CLK internal 0.1036 mW  reg nets 0.0054 mW  comb nets 0.0661 mW',
    '   leakage 3173.22 nW   total (excl. comb internal power) 0.1937 mW',
    'ff_n40C_1v95 @ 50 MHz: C_clk 0.134 pF, C_reg 0.488 pF, C_comb 3.536 pF',
    '   clock-net 0.0255 mW  flop-CLK internal 0.1578 mW  reg nets 0.0081 mW  comb nets 0.1005 mW',
    '   leakage 3.80 nW   total (excl. comb internal power) 0.2918 mW',
]

STA_EX = [
    '# minista.py - a teaching-size NLDM static timing analyser (NOT sign-off STA)',
    '# Reads the Yosys-mapped netlist (JSON) and a SKY130 Liberty corner, propagates',
    '# late/early arrival and slew through the NLDM tables and checks setup/hold.',
    '...',
    'def look(tab, x, y):                    # bilinear interpolation / extrapolation',
    '    i1, i2, v = tab',
    '    def seg(ax, a):',
    '        if len(ax) == 1: return 0, 0.0',
    '        k = min(max(bisect.bisect(ax, a) - 1, 0), len(ax) - 2)',
    '        return k, (a - ax[k]) / (ax[k + 1] - ax[k])',
    '    r, fx = seg(i1, x); c, fy = seg(i2, y)',
    '    if len(i2) == 1: return v[r][0] * (1 - fx) + v[r + 1][0] * fx',
    '    return (v[r][c] * (1 - fx) * (1 - fy) + v[r + 1][c] * fx * (1 - fy)',
    '            + v[r][c + 1] * (1 - fx) * fy + v[r + 1][c + 1] * fx * fy)',
    '    ...',
    '    def arc_eval(a, slew, cap, late):',
    '        f = max if late else min',
    '        d = f(look(a["cell_rise"], slew, cap), look(a["cell_fall"], slew, cap))',
    '        s = f(look(a["rise_transition"], slew, cap), look(a["fall_transition"], slew, cap))',
    '        return d, s',
    '    ...',
    '                if a["type"] == "setup_rising":',
    '                    at, sl, _ = LATE[b]',
    '                    su = max(look(a["rise_constraint"], clk_slew, sl),',
    '                             look(a["fall_constraint"], clk_slew, sl))',
    '                    ends.append(("setup", T - unc_setup - su - at, n + "/" + p, b, at, su))',
    '                else:',
    '                    at, sl, _ = EARLY[b]',
    '                    ho = max(look(a["rise_constraint"], clk_slew, sl),',
    '                             look(a["fall_constraint"], clk_slew, sl))',
    '                    ends.append(("hold", at - ho - unc_hold, n + "/" + p, b, at, ho))',
]

PWR_EX = [
    '# power.py - first-order power estimate for mac_int8 (pre-layout, labelled assumptions)',
    '...',
    'reg = [tg[s] for s in ("p_q", "acc_q", "out_acc", "p_valid", "p_last", "out_valid")]',
    'alpha_reg = sum(n for n, w in reg) / sum(w for n, w in reg) / cycles / 2   # 0->1 per cycle',
    'alpha_cmb = tg["sum"][0] / tg["sum"][1] / cycles / 2',
    '...',
    '    wire = lambda k: wlc * (fl[min(k, 6)] + max(k - 6, 0) * 8.3631) if k else 0.0',
    '    c_clk = loads[clk] + wire(fo[clk])',
    '    c_reg = sum(loads[b] + wire(fo[b]) for b in drv if drv[b])',
    '    c_cmb = sum(loads[b] + wire(fo[b]) for b in drv if not drv[b])',
    '    p_clk = c_clk * V * V * f                     # alpha = 1 for a clock',
    '    p_reg = alpha_reg * c_reg * V * V * f',
    '    p_cmb = alpha_cmb * c_cmb * V * V * f',
    '    ...',
    '    p_int = e_int * f                                # pJ * GHz = mW',
]



# ======================================================================
# Part VI entry point
# ======================================================================
def part6():
    part("Practice and Roadmap",
         "The open-source ASIC flow - Yosys, OpenROAD, OpenLane/LibreLane, "
         "Magic, KLayout, Netgen and the open SKY130, GF180MCU and IHP "
         "SG13G2 PDKs - run for real on the SkyWater libraries; a complete "
         "case study that takes an int8 MAC block from specification through "
         "simulation, lint, synthesis, multi-corner timing, floorplan and "
         "power numbers to the GDSII hand-off; and a career roadmap for every "
         "ASIC role, with a 12-month study plan and interview preparation.")
    _ch24()
    _ch25()
    _ch26()


# ======================================================================
# Chapter 24 - The open-source ASIC flow
# ======================================================================
def _ch24():
    chapter("The Open-Source ASIC Flow: Yosys, OpenROAD/OpenLane and Open PDKs",
            newpage=False)
    p("For forty years the ASIC flow was closed at both ends: the process "
      "design kit (PDK) was under a foundry NDA and the tools were licensed "
      "from three EDA vendors at prices only companies could pay. A student "
      "could write RTL and simulate it, but could not legally see a real "
      "design rule, a real Liberty file or a real standard-cell layout, let "
      "alone tape out. Since 2020 that has changed. There are now "
      "manufacturable open PDKs, an open RTL-to-GDSII tool chain that has "
      "produced hundreds of working chips, and shuttle programmes that put a "
      "small design on silicon for the price of a laptop.")
    p("This chapter explains what exists, how the pieces fit together and "
      "where the open flow stops being a substitute for the commercial one. "
      "Everything that can run in a plain Linux container is run for real "
      "here against the SkyWater SKY130 files: the Liberty corners, the "
      "technology LEF, a standard-cell GDS read through the KLayout API, "
      "and Yosys synthesis. OpenROAD itself is described, not run; the "
      "commands you would type are given exactly. Chapter 25 then pushes a "
      "complete block through every step.")

    # ------------------------------------------------------------------
    h2("Why an open flow matters, and who uses it")
    tbl(["User", "What the open flow gives them"],
        [["**Students and self-learners**", "Real PDK data (Liberty, LEF, "
          "GDS, DRC decks, SPICE models) and every step of the flow, "
          "inspectable down to the source code. The mapping from Chapters "
          "8-19 to real files becomes concrete"],
         ["**Universities and research groups**", "Tape-outs for courses and "
          "papers without NDAs; placement, routing and CTS algorithms can be "
          "modified and published (OpenROAD itself came out of research)"],
         ["**Start-ups and hobbyists**", "A cheap path to a first "
          "mature-node chip: a sensor interface, a small RISC-V "
          "microcontroller, a mixed-signal test chip"],
         ["**Industry engineers**", "Scriptable reference flows for "
          "experiments, CI regression of RTL through a real synthesis and "
          "place-and-route, design-space exploration without licence limits, "
          "and interview portfolios"],
         ["**Tool builders**", "A common, open database (OpenDB) and test "
          "designs to benchmark new algorithms - including machine-learning "
          "driven placement and routing research"]],
        widths=[28, 72])
    box("key", "The one-sentence summary",
        "The open flow is a **complete, working, mature-node RTL-to-GDSII "
        "flow** - good enough to tape out 130/180 nm chips that work - but it "
        "is **not a sign-off substitute** for a commercial flow at advanced "
        "nodes, where foundry-certified extraction, timing, power-integrity "
        "and physical-verification tools are contractually required.")

    # ------------------------------------------------------------------
    h2("A short history: from closed PDKs to open silicon")
    tbl(["Year", "Event", "Why it mattered"],
        [["1980s", "Berkeley **Magic** layout editor (John Ousterhout and "
          "others); later maintained for decades by Tim Edwards",
          "A free layout editor with interactive DRC and extraction - the "
          "backbone of academic VLSI courses"],
         ["2000s", "Berkeley **ABC** logic synthesis and verification "
          "(Alan Mishchenko)", "The technology-mapping engine used inside "
          "Yosys and many research tools"],
         ["2012-13", "**Yosys** open synthesis suite (Claire Wolf)",
          "A production-quality Verilog front end and synthesis script engine"],
         ["2018", "DARPA **IDEA** programme funds **OpenROAD** (led by UC "
          "San Diego) with the goal of a no-human-in-the-loop, 24-hour "
          "RTL-to-GDSII flow", "Placement, CTS, routing, extraction and STA "
          "released as open source; **OpenSTA** (Parallax Software) opened"],
         ["2020", "Google and SkyWater release the **SKY130** open PDK; "
          "Google-sponsored **Open MPW** shuttles run by **Efabless**; "
          "**OpenLane** flow published", "For the first time a manufacturable "
          "PDK is public (Apache-2.0) and designs can be fabricated for free"],
         ["2022", "**GF180MCU** open PDK (GlobalFoundries with Google); "
          "**Tiny Tapeout** starts (Matt Venn and collaborators)",
          "A second foundry; tiny designs on silicon for a small fee"],
         ["2022-24", "**IHP SG13G2** 130 nm SiGe BiCMOS open PDK; "
          "**OpenLane 2** (Python-based, step API)", "A European research "
          "foundry with fast HBTs and a thick top-metal stack; a more "
          "flexible flow framework"],
         ["2025", "Efabless ceases operations; OpenLane 2 continues as "
          "**LibreLane** under the FOSSi Foundation; shuttle access moves to "
          "other providers", "The ecosystem survived its main shuttle "
          "operator - but access routes changed and are still settling"]],
        widths=[10, 48, 42],
        caption="Dates are approximate to the year. Treat the 2025 row as a "
        "snapshot: check the project websites for the current state.")
    box("warn", "PITFALL - stale tutorials",
        "Most tutorials online were written for OpenLane 1 (a Docker/Tcl "
        "flow, `flow.tcl -design ...`) and for the Efabless Open MPW "
        "`caravel_user_project`. Variable names, directory layouts, the PDK "
        "installer (volare, now a successor called ciel in LibreLane) and "
        "shuttle logistics have all changed since. Always read the current "
        "documentation of the exact tool version you install.")

    # ------------------------------------------------------------------
    h2("The open PDKs")
    p("A PDK (Chapter 3) is the foundry's contract with the designer: device "
      "models, design rules and verification decks, and usually standard-cell "
      "and I/O libraries. The open PDKs contain the same kinds of files as a "
      "commercial one - only the licence differs.")
    tbl(["", "SkyWater SKY130", "GlobalFoundries GF180MCU", "IHP SG13G2"],
        [["Node / type", "130 nm bulk CMOS (derived from Cypress S8)",
          "180 nm bulk CMOS", "130 nm SiGe:C BiCMOS"],
         ["Core / I/O voltage", "1.8 V core; 3.3 V and 5 V devices",
          "3.3 V (also 5 V / 6 V devices)", "1.2 V core; 3.3 V I/O"],
         ["Interconnect", "Local interconnect `li1` + 5 Al metals "
          "(met1-met5)", "Up to 6 metals (3-6 configurable)",
          "5 thin metals + 2 thick top metals (TopMetal1/2)"],
         ["Open std-cell libraries", "`sky130_fd_sc_hd` (high density), "
          "`hs`, `ms`, `ls`, `lp`, `hdll`, `hvl`", "`gf180mcu_fd_sc_mcu7t5v0`, "
          "`mcu9t5v0`", "`sg13g2_stdcell`"],
         ["Special devices", "MiM caps, ReRAM option, SONOS, precision "
          "resistors", "MiM caps, poly resistors", "HBTs with fT in the "
          "hundreds of GHz, MiM caps"],
         ["Typical use", "Digital, mixed-signal, first tape-outs",
          "Higher-voltage, analog, MCU-style designs",
          "RF/mm-wave, analog, digital with thick-metal power"]],
        widths=[16, 28, 28, 28],
        caption="Key facts of the three open PDKs; all numbers are the "
        "published nominal values.")
    h3("How an open PDK is organised")
    diagram([
        "skywater-pdk (raw foundry data)          open_pdks (Tim Edwards)",
        "  libraries/sky130_fd_pr   devices    +--> builds a tool-ready PDK:",
        "  libraries/sky130_fd_sc_hd std cells |",
        "     cells/<cell>/  .gds .lef .v      |   $PDK_ROOT/sky130A/",
        "     timing/*.lib.json (per corner)   |     libs.tech/  <- tool setup files",
        "  libraries/sky130_fd_io   I/O cells  |        magic/  sky130A.tech, .magicrc",
        "  libraries/sky130_fd_pr_reram ...   -+        klayout/ DRC/LVS decks, .lyp",
        "                                              netgen/ LVS setup",
        "  volare / ciel: download a PREBUILT          ngspice/ model includes",
        "  open_pdks build by version hash             openlane/ flow config",
        "                                            libs.ref/   <- design views",
        "                                               sky130_fd_sc_hd/",
        "                                                 lib/ lef/ gds/ verilog/",
        "                                                 techlef/ spice/ cdl/"],
        "From raw foundry repositories to the libs.tech / libs.ref layout that "
        "every open tool expects. sky130A and sky130B differ in the back-end "
        "stack (sky130B adds the ReRAM layers).")
    p("`libs.ref` holds **design views** of each library (the same split as "
      "any commercial kit: Liberty for timing, LEF for abstracts, GDS for "
      "layout, Verilog for simulation, CDL/SPICE for LVS); `libs.tech` holds "
      "**tool set-ups** (the Magic tech file, KLayout DRC/LVS scripts, Netgen "
      "set-up, flow configuration). Because building open_pdks from source "
      "takes a long time, a version manager (**volare**, and for LibreLane "
      "its successor **ciel**) downloads a prebuilt PDK pinned to a commit "
      "hash - exactly the reproducibility a real project needs.")

    h3("Run: what is inside the SKY130 hd Liberty files")
    p("The raw `sky130_fd_sc_hd` repository stores timing as per-cell JSON; "
      "the assembled `.lib` files ship inside open_pdks and inside the "
      "OpenROAD and OpenROAD-flow-scripts platform directories, which is "
      "where the files used in this chapter were fetched from. First, what "
      "a synthesis tool is allowed to use. Real flows remove cells that "
      "must not appear in ordinary logic (power-domain `lpflow` cells, "
      "probe cells, clock-tree and delay cells reserved for CTS and hold "
      "fixing); OpenROAD-flow-scripts does it with `DONT_USE_CELLS`, this "
      "script does the same by deleting the cell groups:")
    code(DU_SRC, caption="dufilt.py - removing dont-use cells from a Liberty "
         "file before synthesis (run with python3).")
    out(DU_OUT, caption="Real output: 428 cells in the tt file, 329 left for "
        "logic synthesis.")
    p("Next, a summary of the library and the delay of four cells at five "
      "published PVT corners, looked up from the NLDM tables with bilinear "
      "interpolation (the same lookup an STA tool does; Chapter 9). Three "
      "corners are the assembled `.lib` files; `ss_100C_1v60` and "
      "`tt_100C_1v80` were rebuilt from the per-cell JSON files of the "
      "SkyWater repository, and the rebuild was validated by reproducing "
      "the tt results exactly.")
    out(LIBSUM_OUT, caption="Real output of libsum.py: the SKY130 hd library "
        "and cell delays across corners (NLDM lookup at 0.1 ns input slew, "
        "10 fF load).")
    bul(["**Voltage dominates.** From ff 1.95 V to ss 1.40 V the flip-flop "
         "clock-to-Q grows about 6x (0.238 -> 1.418 ns); the XOR about 5x. "
         "A corner list is a statement about the supply range your product "
         "guarantees, not a formality.",
         "**Temperature is not monotonic.** In this data `tt_100C` is "
         "slightly **faster** than `tt_025C` for the inverter and NAND. "
         "Threshold voltage falls with temperature while mobility also "
         "falls; which effect wins depends on overdrive (Chapter 2). Never "
         "assume the hot corner is the slow one - that is why sign-off "
         "covers both temperature extremes.",
         "**Complex cells degrade more.** The XOR (stacked, internally "
         "buffered) loses more speed at low voltage than the inverter, so "
         "the critical path can **change** between corners."])

    h3("Run: the technology LEF - rows, sites and the metal stack")
    p("Place-and-route never sees transistors. It sees the **technology "
      "LEF** (sites, routing layers, pitches, widths, via rules) and the "
      "**cell LEF** (each cell's size, pins and blockages). A dozen lines of "
      "Python print the parts that matter for floorplanning and routing:")
    code(LEF_SRC, caption="lefstack.py - summarise the SKY130 hd technology "
         "LEF.")
    out(LEF_OUT, caption="Real output: the unithd site and the routing stack "
        "(um). li1 has a two-value pitch (0.46 0.34); the first is shown.")
    p("Every hd cell is an integer number of 0.46 um sites wide and exactly "
      "one 2.72 um row tall; `SIZE 1.38 BY 2.72` for `sky130_fd_sc_hd__inv_1` "
      "is three sites. The direction alternates layer by layer (li1 and met2 "
      "and met4 vertical, met1, met3 and met5 horizontal), and the pitch grows "
      "towards the top of the stack - thin, dense wires below for local "
      "routing, thick wide wires above for power and long nets (Chapters 14 "
      "and 17). `li1` is SKY130's peculiar local interconnect: a resistive "
      "titanium-nitride layer that the cells use internally and the router "
      "uses only for very short hops.")

    h3("Run: looking inside a standard-cell GDS with KLayout")
    p("KLayout is both a layout viewer/editor and a Python-scriptable "
      "geometry engine; the `klayout` package on PyPI exposes the same "
      "database API without the GUI (`pip install klayout`). The script "
      "below reads the real GDS of two cells from the SkyWater repository, "
      "merges the shapes on each drawing layer and reports their area and "
      "extent, and checks the placement boundary against the LEF.")
    code(GDS_SRC, caption="gdsrep.py - read SKY130 cell GDS with the KLayout "
         "Python API (klayout 0.30).")
    out(GDS_OUT, caption="Real output for inv_1 (full) and dfxtp_1 (selected "
        "layers). GDS layer/datatype numbers are the SKY130 layer map.")
    bul(["The **prBoundary** (236/0) and **areaid.sc** layers are exactly "
         "the LEF size - 1.38 x 2.72 um for inv_1, 7.36 x 2.72 um for the "
         "flip-flop. The abstract and the layout agree by construction; LVS "
         "and the GDS merge rely on it.",
         "**met1** extends to 3.20 um in height: the VPWR/VGND rails are "
         "0.48 um wide and centred on the row edges, so abutting rows share "
         "them (the same 0.48 um width the ORFS PDN script uses for its "
         "met1 follow-pin stripes).",
         "**nwell** overhangs the cell (1.76 um wide versus 1.38) - wells of "
         "abutting cells merge. **hvtp** marks high-Vth PMOS: the hd library "
         "uses HVT PFETs throughout, part of why its leakage is so low.",
         "The flop has 14 poly shapes and 50 contacts against 1 and 11 for "
         "the inverter: sequential cells are the densest part of any "
         "standard-cell library, and at 20 um^2 one dfxtp_1 is 5.3 inverters."])
    box("tip", "Installing the layout tools",
        "Debian/Ubuntu package `klayout`, `magic` and `netgen-lvs` "
        "(`apt-get install klayout magic netgen-lvs`), but distribution "
        "versions are often years old; the flows pin specific versions. For "
        "scripting, `pip install klayout` is the quickest start. For "
        "everything at once, the **IIC-OSIC-TOOLS** Docker image (JKU Linz) "
        "bundles Yosys, OpenROAD, OpenLane, Magic, KLayout, Netgen, ngspice, "
        "xschem and the PDKs.")

    # ------------------------------------------------------------------
    h2("The tools and what each one does")
    tbl(["Tool", "Role in the flow", "Commercial counterpart"],
        [["**Yosys** + **ABC**", "RTL elaboration, generic synthesis, "
          "technology mapping to Liberty cells, netlist export; also "
          "formal (SymbiYosys) and equivalence (EQY)",
          "Design Compiler / Fusion Compiler, Genus"],
         ["**OpenROAD** (one binary, many tools)", "Floorplan, PDN, "
          "placement, resizing, CTS, global/detailed routing, extraction, "
          "STA, IR drop - on one database (OpenDB)",
          "Innovus, ICC2 / Fusion Compiler"],
         ["**OpenSTA**", "Static timing analysis: Liberty, Verilog, SDC, "
          "SPEF, SDF; multi-corner", "PrimeTime, Tempus"],
         ["**OpenRCX**", "Parasitic extraction from routed DEF to SPEF",
          "StarRC, Quantus"],
         ["**Magic**", "Layout editor, DRC, extraction (for LVS), GDS "
          "read/write, antenna checks", "Virtuoso (layout), Calibre (DRC)"],
         ["**KLayout**", "Viewer/editor, scripted DRC and LVS decks, GDS/OASIS "
          "merge, XOR", "Calibre DESIGNrev, Calibre DRC/LVS"],
         ["**Netgen**", "LVS: compare layout-extracted netlist to the "
          "schematic/netlist", "Calibre LVS, Pegasus"],
         ["**Icarus / Verilator**", "Event-driven and cycle-based simulation, "
          "lint", "VCS, Xcelium, Questa; SpyGlass lint"],
         ["**ngspice / Xyce**, **xschem**", "Circuit simulation and "
          "schematic capture for analog blocks", "Spectre, HSPICE; Virtuoso "
          "schematic"]],
        widths=[22, 48, 30])
    h3("Inside OpenROAD")
    p("OpenROAD is one executable with a Tcl (and Python) shell. Each "
      "sub-tool reads and writes the same in-memory OpenDB, so there are no "
      "file hand-offs between floorplan, placement, CTS and routing - the "
      "same architecture as the commercial implementation tools.")
    tbl(["Module", "Command(s)", "What it does (chapter)"],
        [["ifp", "`initialize_floorplan`, `make_tracks`", "Die/core size, "
          "rows from the site, routing tracks (Ch. 14)"],
         ["ppl", "`place_pins`", "I/O pin placement on the block edge"],
         ["tap", "`tapcell`", "Well-tap and end-cap cells in every row"],
         ["pdn", "`pdngen`, `add_pdn_stripe`", "Power grid: rails, stripes, "
          "rings, vias (Ch. 14)"],
         ["gpl (RePlAce)", "`global_placement`", "Analytic, electrostatics-"
          "based global placement, timing- and routability-driven (Ch. 15)"],
         ["rsz (Resizer)", "`repair_design`, `repair_timing`",
          "Buffering, gate sizing, max slew/cap/fanout repair, setup and hold "
          "fixing (Ch. 15, 16)"],
         ["dpl (OpenDP)", "`detailed_placement`, `check_placement`",
          "Legalisation onto sites and rows"],
         ["cts (TritonCTS)", "`clock_tree_synthesis`", "H-tree/clustering "
          "based clock tree (Ch. 16)"],
         ["grt (FastRoute)", "`global_route`", "Global routing on a GCell "
          "grid; congestion maps (Ch. 17)"],
         ["drt (TritonRoute)", "`detailed_route`", "Track assignment and "
          "DRC-aware detailed routing"],
         ["ant", "`check_antennas`, `repair_antennas`", "Antenna ratio check "
          "and diode insertion (Ch. 18)"],
         ["rcx (OpenRCX)", "`extract_parasitics`, `write_spef`",
          "Pattern-based RC extraction"],
         ["sta (OpenSTA)", "`report_checks`, `report_wns`, `report_power`",
          "Timing and power analysis, built in"],
         ["psm (PDNSim)", "`analyze_power_grid`", "Static IR drop and EM "
          "of the power grid (Ch. 18)"],
         ["mpl / mpl2", "`rtl_macro_placer`", "Automatic macro placement"]],
        widths=[16, 34, 50],
        caption="OpenROAD modules and their main commands (names as used in "
        "recent OpenROAD releases).")

    # ------------------------------------------------------------------
    h2("The flows: OpenLane, OpenLane 2 / LibreLane and ORFS")
    p("A flow is the script that calls the tools in the right order with the "
      "right files and checks each step. There are two mainstream open "
      "flows, and they share almost all tools.")
    diagram([
        " RTL (.v/.sv) + config + SDC",
        "        |",
        "  [1] Yosys + ABC synthesis ---------> netlist.v   (+ pre-PnR STA with OpenSTA)",
        "        |",
        "  [2] Floorplan (ifp) -> I/O pins (ppl) -> tap/endcap -> PDN (pdngen)",
        "        |",
        "  [3] Global placement (gpl) -> repair_design (rsz) -> detailed placement (dpl)",
        "        |",
        "  [4] CTS (TritonCTS) -> repair_timing -setup/-hold (rsz) -> dpl",
        "        |",
        "  [5] Global route (FastRoute) -> antenna repair -> detailed route (TritonRoute)",
        "        |",
        "  [6] Fill / decap -> RC extraction (OpenRCX) -> multi-corner STA (OpenSTA)",
        "        |                                    -> IR drop (PDNSim)",
        "  [7] GDS stream-out (Magic and/or KLayout) + merge std-cell GDS",
        "        |",
        "  [8] Sign-off: DRC (Magic + KLayout), LVS (Netgen), antenna, XOR",
        "        |",
        "      final/  gds  def  odb  spef  sdf  lib  netlist  metrics.json"],
        "The open RTL-to-GDSII flow. Steps 2-6 run inside OpenROAD on one "
        "database; steps 7-8 use the layout tools of the PDK.")
    tbl(["", "OpenLane 2 / LibreLane", "OpenROAD-flow-scripts (ORFS)"],
        [["Origin", "Efabless (OpenLane 1: 2020; OpenLane 2: 2023-24); "
          "continued as LibreLane", "The OpenROAD project (UCSD)"],
         ["Written in", "Python: every step is a class; flows are sequences "
          "of steps", "GNU make + Tcl + shell"],
         ["Configuration", "`config.json` / `config.yaml` with typed, "
          "documented variables", "`config.mk` (make variables) per design "
          "and per platform"],
         ["PDKs", "sky130, gf180mcu (IHP support added more recently)",
          "sky130hd/hs, gf180, ihp-sg13g2, asap7 (predictive 7 nm), "
          "nangate45"],
         ["Sign-off steps", "Built in: Magic and KLayout DRC, Netgen LVS, "
          "antenna, XOR, multi-corner STA", "Mostly up to routed GDS; DRC and "
          "LVS support vary per platform"],
         ["Best for", "Taping out on open shuttles (shuttle precheck "
          "expects its outputs)", "Tool research, PPA experiments, trying "
          "many designs and platforms quickly"]],
        widths=[16, 42, 42])
    h3("What a real platform configuration looks like")
    p("ORFS keeps everything technology-specific in a platform directory. "
      "This excerpt is from the real `flow/platforms/sky130hd/config.mk` "
      "fetched for this chapter; every variable is one decision from "
      "Chapters 13-18 made once for the whole technology:")
    code([
        "export TECH_LEF ?= $(PLATFORM_DIR)/lef/sky130_fd_sc_hd.tlef",
        "export SC_LEF   ?= $(PLATFORM_DIR)/lef/sky130_fd_sc_hd_merged.lef",
        "export LIB_FILES ?= $(PLATFORM_DIR)/lib/sky130_fd_sc_hd__tt_025C_1v80.lib",
        "# *probe* cells have metal on all layers; *lpflow* are multi-power-domain",
        "export DONT_USE_CELLS += sky130_fd_sc_hd__probe_p_8 ... (36 cells)",
        "export FILL_CELLS ?= sky130_fd_sc_hd__fill_1 sky130_fd_sc_hd__fill_2 ...",
        "export TIEHI_CELL_AND_PORT = sky130_fd_sc_hd__conb_1 HI",
        "export TIELO_CELL_AND_PORT = sky130_fd_sc_hd__conb_1 LO",
        "export ABC_DRIVER_CELL = sky130_fd_sc_hd__buf_1",
        "export PLACE_SITE = unithd",
        "export IO_PLACER_H ?= met3",
        "export IO_PLACER_V ?= met2",
        "export TAP_CELL_NAME = sky130_fd_sc_hd__tapvpwrvgnd_1",
        "export PLACE_DENSITY ?= 0.60",
        "export MIN_ROUTING_LAYER ?= met1",
        "export MIN_CLK_ROUTING_LAYER ?= met3",
        "export MAX_ROUTING_LAYER ?= met5"],
        caption="Excerpt of ORFS flow/platforms/sky130hd/config.mk (abridged; "
        "the DONT_USE list is shortened).")
    p("The companion `pdn.tcl` of the same platform defines the power grid "
      "as met1 follow-pin rails (0.48 um wide, pitch 5.44 um = two rows), "
      "met4 vertical stripes (1.6 um wide, 27.14 um pitch) and met5 "
      "horizontal stripes (1.6 um, 27.2 um pitch), connected met1-met4 and "
      "met4-met5; `tapcell.tcl` inserts `tapvpwrvgnd_1` well taps with "
      "`-distance 14` (um), which keeps every point of every well within the "
      "latch-up tap-distance rule (Chapter 12).")

    h3("OpenLane 2 / LibreLane configuration")
    code([
        "{",
        '  "DESIGN_NAME": "mac_int8",',
        '  "VERILOG_FILES": "dir::src/mac_int8.sv",',
        '  "CLOCK_PORT": "clk",',
        '  "CLOCK_PERIOD": 20.0,',
        '  "PNR_SDC_FILE": "dir::mac_int8.sdc",',
        '  "SIGNOFF_SDC_FILE": "dir::mac_int8.sdc",',
        '  "FP_SIZING": "absolute",',
        '  "DIE_AREA": [0, 0, 125, 130],',
        '  "PL_TARGET_DENSITY_PCT": 60',
        "}"],
        caption="config.json for the Chapter 25 block (OpenLane 2 variable "
        "names; not run here - check the documentation of your LibreLane "
        "version, names do change).")
    code([
        "# OpenLane 2 / LibreLane (inside the Nix shell, or with Docker)",
        "openlane config.json                 # or: librelane config.json",
        "openlane --dockerized config.json    # run the tools from the container",
        "openlane --flow Classic --to OpenROAD.STAPostPNR config.json   # stop early",
        "openlane --last-run --flow OpenInKLayout config.json           # view layout",
        "",
        "# ORFS",
        "cd OpenROAD-flow-scripts/flow",
        "make DESIGN_CONFIG=./designs/sky130hd/mac_int8/config.mk          # full flow",
        "make DESIGN_CONFIG=./designs/sky130hd/mac_int8/config.mk gui_final # GUI"],
        caption="How the flows are invoked (commands shown, not run in this "
        "book's container).")
    box("note", "Where the results land",
        "OpenLane 2 creates `runs/RUN_<timestamp>/`, one numbered directory "
        "per step (with its log, reports and the design state) and a "
        "`final/` directory with GDS, DEF, ODB, netlists, SPEF per corner, "
        "SDF and `metrics.json`. ORFS writes `logs/`, `reports/`, `results/` "
        "and `objects/` under `<platform>/<design>/<variant>/`, with stage "
        "prefixes 1_synth ... 6_final (for example `6_final.gds`). Learn to "
        "read the **metrics** first (WNS/TNS per corner, DRC count, LVS "
        "status, utilisation, wirelength) and open the logs only for what "
        "is red.")

    # ------------------------------------------------------------------
    h2("Run: synthesis with Yosys on the real SKY130 library")
    p("Synthesis is the one implementation step that runs in seconds on "
      "a laptop, so it is the best place to start. An 8-bit counter with "
      "asynchronous reset and enable:")
    code(CNT_V, caption="counter.v")
    code(CNT_YS, caption="syn.ys - the minimal Yosys script: generic "
         "synthesis, flop mapping, ABC logic mapping, statistics.")
    out(CNT_STAT, caption="Real output of `yosys syn.ys` (Yosys 0.33) against "
        "the dont-use-filtered sky130_fd_sc_hd tt_025C_1v80 Liberty.")
    p("Eight `dfrtp_1` (D flop, async active-low reset, 25.02 um^2 each) "
      "hold the count, and 15 small gates form the incrementer: the flops "
      "are two-thirds of the area (200 of 299 um^2), which is typical of "
      "control-dominated logic in this library. `read_liberty -lib` loads "
      "the cells as black boxes so the netlist can be checked; `dfflibmap` "
      "and `abc -liberty` do the mapping (Chapter 8 explains what happens "
      "inside); `stat -liberty` sums the `area` attribute of every cell. "
      "Chapter 25 extends this script with an ABC delay target and timing "
      "constraints.")
    box("warn", "PITFALL - Yosys stat is cell area, not block area",
        "The 299 um^2 is the sum of cell footprints. The placed block needs "
        "whitespace for routing and buffering (utilisation 50-70 %), well "
        "taps, fillers, a power grid and pin access - so the core is "
        "roughly 1.5-2x larger, and the die larger again. Chapter 25 does "
        "the arithmetic.")

    # ------------------------------------------------------------------
    h2("Tiny Tapeout, shuttles and getting a design onto silicon")
    p("**Tiny Tapeout** aggregates hundreds of tiny designs onto one chip. "
      "Each project gets one or more **tiles** (on the SKY130 shuttles a "
      "single tile was on the order of 160 x 100 um, room for a few hundred "
      "to a thousand-odd standard cells) with a fixed interface: 8 dedicated "
      "inputs, 8 dedicated outputs, 8 bidirectional I/Os, clock, reset and "
      "an enable. An on-chip multiplexer selects which project drives the "
      "pins, and a demo board lets you exercise the chip after delivery. "
      "You write Verilog (or draw an analog block), push to a GitHub "
      "template, and a GitHub Action runs the whole open flow and produces "
      "the GDS and a viewer of your tile.")
    tbl(["Route to silicon", "What you get", "Notes"],
        [["**Tiny Tapeout**", "A tile on a shared chip, a demo board",
          "Cheapest and quickest; a complete learning experience including "
          "bring-up. Shuttles have run on SKY130, IHP SG13G2 and GF180; the "
          "schedule and technologies change - check tinytapeout.com"],
         ["**Full MPW slot**", "A die area of several mm^2 (formerly the "
          "Caravel harness: RISC-V management core plus about 10 mm^2 of "
          "user area)", "The Efabless Open MPW/chipIgnite programmes ended "
          "with Efabless in 2025; successor programmes (for example "
          "ChipFoundry for SKY130, wafer.space for GF180) and IHP's own "
          "research MPWs have appeared. Verify current offers"],
         ["**University programmes**", "Europractice, MOSIS-style brokers, "
          "IHP research runs", "Commercial PDKs under NDA, or open PDKs; "
          "funded for education and research"],
         ["**Commercial MPW / dedicated mask set**", "Your own reticle or a "
          "share of one", "The production path of Chapters 19 and 23"]],
        widths=[22, 34, 44],
        caption="Access routes change year to year; this is a map of the "
        "kinds of options, not a price list.")
    box("expert", "Interview insight - what shuttle precheck teaches",
        "Shuttle operators run a **precheck** before accepting a design: "
        "correct top-level name and pin positions, no DRC or LVS errors, "
        "consistent power connections, no layer outside the allowed set, "
        "GDS size and hash. This is a miniature version of a foundry's "
        "tapeout intake (Chapter 19). Saying in an interview that you have "
        "closed a precheck - and what failed the first time - is a strong "
        "signal that you understand the sign-off hand-off, not just RTL.")

    # ------------------------------------------------------------------
    h2("Installing the flow")
    tbl(["Method", "Commands (outline)", "Pros and cons"],
        [["**Nix** (recommended for OpenLane 2 / LibreLane)",
          "Install Nix with the project's cache; `nix-shell` in the "
          "cloned repository; then `openlane --smoke-test`",
          "Bit-exact reproducible tool versions; first download is large"],
         ["**Docker**", "`pip install openlane` (or `librelane`), then "
          "`openlane --dockerized --smoke-test`; ORFS: "
          "`docker run` the published ORFS image",
          "Works on any OS with Docker; file permissions and GUI forwarding "
          "need care"],
         ["**Build ORFS locally**", "`git clone --recursive "
          "OpenROAD-flow-scripts`, `./build_openroad.sh --local`, "
          "`source env.sh`, `make -C flow`", "Fastest iteration for tool "
          "developers; long compile, many dependencies"],
         ["**All-in-one image**", "IIC-OSIC-TOOLS Docker/VNC image",
          "Everything including analog tools and PDKs; large"],
         ["**Distribution packages**", "`apt install yosys iverilog "
          "verilator klayout magic netgen-lvs ngspice`", "Good for learning "
          "individual tools; versions usually too old for the flows"]],
        widths=[20, 44, 36],
        caption="Commands outline the documented procedures and are not run "
        "here; they change between releases.")
    box("tip", "The smoke test first",
        "Before your own design, run the flow's smoke test (OpenLane 2 "
        "ships one; ORFS has `designs/sky130hd/gcd`). If the reference "
        "design does not reach a clean GDS, the problem is your "
        "installation or PDK, not your RTL - and you have saved a day of "
        "confused debugging.")

    # ------------------------------------------------------------------
    h2("Open-source versus commercial: an honest gap analysis")
    tbl(["Area", "Open flow today", "Commercial flow", "Consequence"],
        [["Nodes", "130/180 nm production PDKs; ASAP7 and FreePDK45/"
          "Nangate45 predictive kits for research", "Every node down to the "
          "leading edge, foundry-certified", "No open path to a production "
          "FinFET/GAA tape-out"],
         ["QoR (PPA)", "Good at mature nodes; timing-driven placement, "
          "resizing and CTS work", "Tighter optimisation, concurrent "
          "clock/data optimisation, more mature algorithms",
          "Expect larger area or lower frequency for the same RTL"],
         ["Timing sign-off", "OpenSTA: NLDM, multi-corner, SPEF; limited "
          "CCS/AOCV/POCV, SI", "PrimeTime/Tempus with CCS, POCV/LVF, SI "
          "crosstalk delta-delay and noise", "Add margin; no crosstalk "
          "sign-off"],
         ["Extraction", "OpenRCX pattern-based", "Field-solver-correlated, "
          "foundry-certified (StarRC, Quantus)", "Accuracy good enough for "
          "130 nm, not certified"],
         ["Power integrity", "PDNSim static IR", "Dynamic/vectorless IR, EM, "
          "RedHawk/Voltus", "Over-design the grid"],
         ["Physical verification", "Magic, KLayout DRC; Netgen LVS - "
          "foundry-quality decks for the open PDKs", "Calibre/Pegasus/ICV, "
          "certified decks", "Workable at 130/180 nm"],
         ["DFT", "Scan insertion in OpenROAD/Yosys plug-ins; limited ATPG "
          "(for example the Fault project)", "Full compression, ATPG, BIST, "
          "diagnosis", "Production test is the weakest link"],
         ["Verification", "Icarus, Verilator, cocotb, SymbiYosys, EQY; "
          "partial SystemVerilog/UVM support", "Full SV/UVM, formal apps, "
          "emulation", "Use Verilator + cocotb, or commercial simulators"],
         ["Support", "Community, GitHub issues", "Vendor AEs, contractual "
          "support", "You own the debugging"]],
        widths=[15, 30, 30, 25])
    box("key", "Where the open flow is genuinely excellent",
        "Learning (everything is inspectable), reproducible research, "
        "mature-node test chips, CI of RTL through a real back end, and "
        "**scripting culture**: engineers who learned on OpenROAD are "
        "usually strong at the Tcl/Python automation every commercial flow "
        "also needs.")

    h2("Summary")
    bul(["Open PDKs (SKY130, GF180MCU, IHP SG13G2) contain real device "
         "models, rules, decks and libraries; open_pdks builds the "
         "tool-ready libs.tech/libs.ref layout and volare/ciel pin versions.",
         "Yosys/ABC synthesise; OpenROAD (ifp, pdn, gpl, rsz, dpl, cts, grt, "
         "drt, rcx, sta, psm) implements on one database; Magic, KLayout and "
         "Netgen stream out and verify.",
         "OpenLane 2 / LibreLane is the tape-out-oriented Python flow; ORFS is "
         "the make-based research flow; both are configured, not "
         "programmed, for a design.",
         "Real SKY130 data shows the physics of earlier chapters: flop "
         "clock-to-Q 0.24-1.42 ns across corners, 0.46 x 2.72 um sites, "
         "alternating routing directions, 0.48 um met1 rails.",
         "Tiny Tapeout and successor shuttle services make a first tape-out "
         "possible for an individual; check the current schedule.",
         "The gap to commercial tools is in advanced nodes, certified "
         "sign-off (SI, CCS/POCV, dynamic IR), DFT/ATPG and QoR."])
    h2("Exercises")
    bul(["Run `dufilt.py` and `libsum.py` on the SKY130 **hs** (high-speed) "
         "library. How much faster and larger is `dfxtp_1` than in hd?",
         "Extend `lefstack.py` to print the via rules (`VIARULE ... GENERATE`) "
         "and compute the maximum number of met2 tracks over a 100 um wide "
         "block.",
         "Use `gdsrep.py` on `sky130_fd_sc_hd__nand2_1`. Predict the number "
         "of poly shapes before you run it, then explain the result.",
         "Install OpenLane 2 or ORFS and run the `gcd` or smoke-test design. "
         "Record WNS, cell count, utilisation and DRC count from the "
         "metrics, then halve the clock period and record them again.",
         "Write a one-page comparison of the three open PDKs for a 1 mm^2 "
         "sensor-interface chip with a 5 V output: which would you choose "
         "and why?"],
        ordered=True)


# ======================================================================
# Chapter 25 - Case study: a block from RTL to GDSII
# ======================================================================
SDC = [
    "# mac_int8.sdc - timing intent for the case-study block",
    "create_clock -name core_clk -period 20.0 [get_ports clk]     ;# 50 MHz",
    "set_clock_uncertainty -setup 0.50 [get_clocks core_clk]     ;# jitter + pre-CTS skew",
    "set_clock_uncertainty -hold  0.10 [get_clocks core_clk]",
    "set_clock_transition 0.10 [get_clocks core_clk]              ;# ideal clock until CTS",
    "",
    "# I/O budget: 20 % of the period is used outside the block on each side",
    "set_input_delay  4.0 -clock core_clk [all_inputs -no_clocks]",
    "set_output_delay 4.0 -clock core_clk [all_outputs]",
    "set_driving_cell -lib_cell sky130_fd_sc_hd__buf_1 [all_inputs -no_clocks]",
    "set_load 0.005 [all_outputs]                                 ;# pF",
    "",
    "# rst_n is asserted asynchronously but released synchronously by a reset",
    "# synchroniser outside the block, so recovery/removal ARE timed (no false path)",
    "set_max_fanout 16 [current_design]",
    "set_max_transition 1.0 [current_design]                      ;# ns, below lib 1.5",
]

ORFS_CFG = [
    "export DESIGN_NAME     = mac_int8",
    "export PLATFORM        = sky130hd",
    "export VERILOG_FILES   = $(DESIGN_HOME)/src/mac_int8/mac_int8.sv",
    "export SDC_FILE        = $(DESIGN_HOME)/$(PLATFORM)/mac_int8/constraint.sdc",
    "export CORE_UTILIZATION = 50",
    "export CORE_ASPECT_RATIO = 1",
    "export CORE_MARGIN     = 10",
    "export PLACE_DENSITY   = 0.60",
]

OR_TCL = [
    "# ---- set-up ------------------------------------------------------------",
    "read_lef sky130_fd_sc_hd.tlef ; read_lef sky130_fd_sc_hd_merged.lef",
    "read_liberty sky130_fd_sc_hd__tt_025C_1v80.lib",
    "read_verilog mac_net.v ; link_design mac_int8 ; read_sdc mac_int8.sdc",
    "# ---- floorplan and power -------------------------------------------------",
    "initialize_floorplan -utilization 50 -aspect_ratio 1 -core_space 10 -site unithd",
    "source sky130hd.tracks                 ;# make_tracks per routing layer",
    "place_pins -hor_layers met3 -ver_layers met2",
    "tapcell -distance 14 -tapcell_master sky130_fd_sc_hd__tapvpwrvgnd_1",
    "source pdn.tcl ; pdngen",
    "# ---- placement -----------------------------------------------------------",
    "global_placement -density 0.60 -timing_driven",
    "repair_design                          ;# max slew/cap/fanout: buffers rst_n etc.",
    "detailed_placement ; check_placement",
    "# ---- clock tree ----------------------------------------------------------",
    "clock_tree_synthesis -root_buf sky130_fd_sc_hd__clkbuf_16 \\",
    "                     -buf_list {sky130_fd_sc_hd__clkbuf_4 sky130_fd_sc_hd__clkbuf_8}",
    "set_propagated_clock [all_clocks]",
    "repair_timing -setup ; repair_timing -hold",
    "detailed_placement",
    "# ---- routing -------------------------------------------------------------",
    "global_route -congestion_report_file congestion.rpt",
    "repair_antennas ; detailed_route -output_drc route_drc.rpt",
    "filler_placement {sky130_fd_sc_hd__fill_*} ;# decap/fill in the gaps",
    "# ---- extraction and timing ------------------------------------------------",
    "extract_parasitics -ext_model_file rcx_patterns.rules ; write_spef mac_int8.spef",
    "report_checks -path_delay min_max ; report_wns ; report_tns ; report_power",
    "write_def mac_int8.def ; write_db mac_int8.odb",
]


def _ch25():
    chapter("Case Study: A Block from RTL to GDSII")
    p("This chapter takes one small, realistic block through the entire flow "
      "of this book. The block is a **streaming int8 multiply-accumulate "
      "(MAC) engine** - the inner loop of every quantized neural-network "
      "accelerator, and a natural fit for a repository about on-device "
      "training, quantization and pruning. It is small enough to reason "
      "about completely (a few hundred cells) and rich enough to show "
      "every real issue: a valid/ready handshake, signed arithmetic, "
      "overflow sizing, a carry chain that fails timing at the slow "
      "corner, a high-fanout reset, clock power, and hold at the fast "
      "corner.")
    p("Every result in a green card was produced for this chapter: Icarus "
      "Verilog 12 simulation, Verilator 5.020 lint, Yosys 0.33 synthesis "
      "against the real SKY130 `sky130_fd_sc_hd` Liberty files, a "
      "zero-delay gate-level simulation, and Python models for multi-corner "
      "timing, floorplan and power that read the same Liberty and netlist "
      "files. Placement, CTS, routing and sign-off were **not run** (no "
      "OpenROAD in this environment); for those steps the exact commands and "
      "the checks to make are given and clearly marked.")
    tbl(["Step", "Owner", "Tool used here", "Status in this chapter"],
        [["Spec and micro-architecture", "Architect / designer", "-",
          "Written"],
         ["RTL", "RTL designer", "SystemVerilog", "Written"],
         ["Simulation", "DV", "Icarus Verilog 12", "**Run**"],
         ["Lint", "RTL designer", "Verilator 5.020", "**Run**"],
         ["Synthesis", "Synthesis / RTL", "Yosys 0.33 + ABC, SKY130 hd",
          "**Run**"],
         ["Gate-level simulation", "DV", "Yosys + Icarus", "**Run** (zero delay)"],
         ["Multi-corner STA estimate", "STA", "Python NLDM model on real Liberty",
          "**Run** (pre-layout)"],
         ["SDC", "Designer / STA", "-", "Written, not run in a real STA tool"],
         ["Floorplan sizing", "PD", "Python on real cell area and site",
          "**Run**"],
         ["Power estimate", "Power / designer", "Python on real Liberty + VCD",
          "**Run**"],
         ["Place, CTS, route, extraction", "PD", "OpenROAD (ORFS / LibreLane)",
          "Commands given, **not run**"],
         ["DRC, LVS, antenna, sign-off STA", "PV / STA",
          "Magic, KLayout, Netgen, OpenSTA", "Checklist, **not run**"]],
        widths=[27, 18, 30, 25])

    # ------------------------------------------------------------------
    h2("Step 1 - Specification")
    p("A block spec (Chapter 5) states behaviour, interfaces, performance "
      "and the conditions under which the numbers must hold. Writing the "
      "corners and the overflow rule **before** the RTL is what makes the "
      "later steps checkable.")
    tbl(["Item", "Specification"],
        [["Function", "Signed int8 dot product: out = sum(a[i] * b[i]) over "
          "a vector of 1 to 511 element pairs; `in_last` marks the final pair"],
         ["Input interface", "valid/ready stream: `in_valid`, `in_ready`, "
          "`in_a[7:0]`, `in_b[7:0]` (two's complement), `in_last`; a beat "
          "transfers when valid and ready are both high"],
         ["Output interface", "valid/ready stream: `out_valid`, `out_ready`, "
          "`out_acc[23:0]` (two's complement); the result is held stable "
          "while `out_valid && !out_ready`"],
         ["Throughput", "One element pair per clock when not back-pressured"],
         ["Latency", "Two-stage pipeline: `out_valid` rises on the clock edge "
          "after the edge that accepts the last pair"],
         ["Clock / reset", "One clock `clk`; `rst_n` asynchronous assert, "
          "synchronous de-assert (synchroniser outside the block)"],
         ["Frequency", "50 MHz sign-off (20 ns); 100 MHz desirable at typical"],
         ["PVT", "SKY130, 1.8 V nominal, 1.60-1.95 V at the cells, -40 to "
          "100 deg C junction: setup at ss_100C_1v60, hold at ff_n40C_1v95, "
          "tt_025C_1v80 for reporting"],
         ["Area / power", "< 0.02 mm^2 die; < 0.5 mW at 50 MHz, typical"],
         ["Test", "Scan-insertable (all flops on `clk`, no internal "
          "resets or gated clocks)"]],
        widths=[20, 80], bold_first=True)
    box("math", "Sizing the accumulator",
        "The largest product magnitude is (-128) x (-128) = +16384 = 2^14. "
        "A signed accumulator of W bits holds at most 2^(W-1) - 1. With W = "
        "24: 2^23 - 1 = 8,388,607, and 8,388,607 / 16,384 = 511.99, so "
        "**511 worst-case terms fit and 512 overflow** by exactly one LSB. "
        "The spec therefore says 1 to 511, and the testbench checks the 511 "
        "x (-128 x -128) = 8,372,224 corner directly. In general W = 16 + "
        "ceil(log2(N)) for N terms, minus one bit if the -128 x -128 case is "
        "excluded.")

    h2("Step 2 - Micro-architecture and RTL")
    diagram([
        "            stage 1 (multiply)            stage 2 (accumulate)       output",
        "  in_a --+                                                         register",
        "  in_b --+--> [ 8x8 signed ] --> p_q[15:0] --+--> (+) --> sum --+--> out_acc[23:0]",
        "         |      multiplier       p_last      |     ^           |    out_valid",
        "  in_last+-----------------------> p_valid   |     |           +--> acc_q[23:0]",
        "                                              |     +--- acc_q --+   (cleared on last)",
        "  in_ready <-- s1_ready = !p_valid | s2_fire  |",
        "               s2_fire  = p_valid & (!p_last | !out_valid | out_ready)",
        "  out_ready ------------------------------------------------------------^"],
        "Two pipeline stages. A non-last product always retires into the "
        "accumulator; only a last product needs the output register to be free.")
    p("The multiplier and the adder are in separate stages so that each "
      "stage has one arithmetic operator in its critical path. The "
      "back-pressure logic is the **pipeline-ready** form from the companion "
      "RTL Design guide: stage 1 may load when it is empty or when stage 2 "
      "consumes its content in the same cycle. Data flops (`p_q`, `p_last`) "
      "have no reset - their contents are qualified by `p_valid` - which "
      "saves area and keeps them off the reset tree.")
    code(MAC_SV, caption="mac_int8.sv - the complete RTL of the case-study block.")

    h2("Step 3 - Simulation")
    p("The testbench is self-checking (the companion SystemVerilog guide "
      "covers the techniques): a producer task with random idle gaps, a "
      "consumer that de-asserts `out_ready` a quarter of the time, and a "
      "queue of expected results computed with 32-bit integer arithmetic. "
      "Directed corners come first: a one-element vector, the 511-term "
      "worst case, and a mixed-sign pair; then 200 random vectors of 1 to "
      "64 elements.")
    code(TB_SV, caption="tb_mac.sv - self-checking testbench with random "
         "back-pressure (the +vcd switch dumps activity for Step 9).")
    out(["$ iverilog -g2012 -Wall -o sim tb_mac.sv mac_int8.sv && vvp -n sim +vcd"]
        + SIM_OUT,
        caption="Real output: 203 vectors, 7430 accepted beats, 70 cycles of "
        "output back-pressure, no mismatches.")
    p("To see what the checker catches, one keyword was removed: `p_q` "
      "declared without `signed`. The product is still computed correctly "
      "(the operands are signed) but `ACC_W'(p_q)` now **zero-extends** a "
      "negative product before the add:")
    out(V1_OUT, caption="Real output with the bug injected: 201 of 203 "
        "results wrong. Only the two all-positive-product vectors pass.")
    box("warn", "PITFALL - signedness bugs are invisible to lint",
        "Verilator `-Wall` reports **nothing** for the unsigned `p_q` (it is "
        "legal, width-consistent code). Only a checker with negative "
        "operands finds it. A directed test with only positive values, or "
        "an FPGA demo that happened to use unsigned data, would have passed "
        "and the bug would have reached silicon.")

    h2("Step 4 - Lint")
    p("Lint is the cheapest static check (Chapter 7 and the companion RTL "
      "guide). The final RTL is clean:")
    out(["$ verilator --lint-only -Wall mac_int8.sv ; echo exit=$?", "exit=0"],
        caption="Real output: no warnings with -Wall.")
    p("An earlier draft (kept to show what lint is for) added the product "
      "without the explicit sign-extending cast and left a debug signal "
      "behind:")
    out(LINT_V0, caption="Real Verilator output on the draft (long lines "
        "wrapped). WIDTHEXPAND flags an implicit extension - here it happens "
        "to be correct because both operands are signed, but the reviewer "
        "should not have to work that out.")
    box("tip", "Lint waivers are design decisions",
        "Fix, do not waive, width warnings in arithmetic. Waive only with a "
        "comment explaining why (for example an intentionally unused bit of "
        "a standard bus), and review the waiver file like RTL.")

    h2("Step 5 - Synthesis on SKY130")
    p("Synthesis uses the dont-use-filtered `tt_025C_1v80` Liberty "
      "(Chapter 24). The ABC constraint file sets the input drive "
      "(`set_driving_cell sky130_fd_sc_hd__buf_1`) and output load "
      "(`set_load 0.005`, in pF); `-D 10000` gives ABC a 10 ns delay target.")
    code(SYN_YS, caption="syn.ys - synthesis script for mac_int8.")
    out(MAC_STAT, caption="Real output: Yosys 0.33 stat -liberty on "
        "sky130_fd_sc_hd tt_025C_1v80 - 644 cells, 5365 um^2.")
    out(ABC_OUT, caption="Real output: ABC's own summary of the combinational "
        "part (flops excluded; its internal load model, not an STA).")
    tbl(["Group", "Cells", "Area (um^2)", "Share", "Comment"],
        [["Reset flops `dfrtp_1`", "50", "1251.2", "23.3 %", "p_valid, acc_q, "
          "out_acc, out_valid"],
         ["Plain flops `dfxtp_1`", "17", "340.3", "6.3 %", "p_q, p_last"],
         ["Combinational", "577", "3773.6", "70.3 %", "Multiplier (xor/xnor/"
          "maj3/nand) and 24-bit adder (maj3 carry chain)"],
         ["**Total**", "**644**", "**5365.1**", "100 %", "ABC 3773.6 + flops "
          "1591.5 = stat total"]],
        widths=[24, 10, 14, 11, 41],
        caption="Area breakdown derived from the real stat output above.")
    bul(["**maj3_1 x 41** is the tell-tale of ripple-carry adders: a full "
         "adder's carry is majority(a, b, cin). Yosys' default `alumacc` "
         "mapping produces ripple adders; ABC restructures logic but cannot "
         "invent a parallel-prefix adder. Tightening `-D` from 10000 to 2000 "
         "was tried: area rose slightly (5391 um^2) and ABC's delay improved "
         "only from 6.88 to 5.89 ns. **Architecture, not synthesis effort, "
         "sets this critical path** (Chapter 8).",
         "**Reset cost**: `out_acc` has a reset it does not need (it is "
         "qualified by `out_valid`). Removing it turns 24 `dfrtp_1` "
         "(25.02 um^2) into `dfxtp_1` (20.02 um^2) and saves 24 x 5.0 = "
         "120 um^2, 2.2 % of the block - and 24 loads on the reset tree.",
         "**Scan cost** (DFT, Chapter 10): replacing every flop with its scan "
         "equivalent (`sdfrtp_1` 31.28 um^2, `sdfxtp_1` 26.28 um^2) adds "
         "50 x 6.26 + 17 x 6.26 = 419 um^2, about 7.8 %."])

    h3("Gate-level simulation of the netlist")
    p("Before trusting a netlist, simulate it with the same testbench. Yosys "
      "can import the Liberty `function` and `ff` groups of the cells it "
      "used as behavioural modules and flatten them into a plain-Verilog "
      "netlist:")
    code(GLS_YS, caption="gls.ys - build a flattened functional netlist "
         "(used_tt.lib is the tt Liberty reduced to the 42 cell types used).")
    out(["$ iverilog -g2012 -o gsim tb_mac.sv gls_flat.v && vvp -n gsim"] + GLS_OUT,
        caption="Real output: the synthesized netlist passes the same 203 "
        "vectors (zero-delay GLS).")
    box("note", "What zero-delay GLS does and does not prove",
        "It shows that synthesis preserved function for these vectors and "
        "that no X appears after reset in the netlist - a common failure "
        "when datapath flops have no reset. It proves nothing about timing, "
        "and it is not exhaustive: **formal equivalence checking** "
        "(Chapter 8; Yosys `equiv_*` or EQY in the open flow, Conformal or "
        "Formality commercially) is the sign-off check that netlist == RTL. "
        "Timing-annotated GLS with SDF comes after routing.")

    # ------------------------------------------------------------------
    h2("Step 6 - Constraints (SDC)")
    code(SDC, caption="mac_int8.sdc - written for this block (standard SDC as "
         "read by OpenSTA). Not run through a real STA tool here; the Python "
         "model in Step 7 applies the same period, uncertainty and I/O budget.")
    bul(["The I/O delays spend 20 % of the period outside the block on each "
         "side - a common starting budget until the SoC integrator provides "
         "real numbers (Chapter 9).",
         "Setup uncertainty 0.5 ns before CTS covers jitter plus an allowance "
         "for skew; after CTS it is reduced to jitter plus margin because "
         "skew is then computed from the real tree.",
         "`rst_n` stays timed. Its de-assertion must meet **recovery** and "
         "**removal** at 50 flops; with a fanout of 50 it will be buffered "
         "by `repair_design`. Falsely pathing a synchronously released reset "
         "is a classic silicon bug (Chapter 12 of the companion RTL guide)."])

    h2("Step 7 - Timing across corners (pre-layout estimate)")
    p("OpenSTA is not available in this container, so a compact NLDM timing "
      "analyser was written for this chapter. It reads the Yosys netlist "
      "(JSON) and a Liberty corner, computes each net's load from the "
      "input-pin capacitances plus the Liberty 'Small' wire-load model, "
      "propagates late and early arrival times and slews through the "
      "`cell_rise/cell_fall` and transition tables (worst of rise and "
      "fall), starts paths at flop clock-to-Q arcs and ends them at the "
      "`setup_rising`/`hold_rising` constraint tables - exactly the "
      "algorithm of Chapter 9, minus crosstalk, CRPR, OCV derates and "
      "unateness tracking. It was validated by reproducing identical "
      "results from the assembled tt `.lib` and from the per-cell JSON "
      "rebuild of the same corner.")
    code(STA_EX, caption="Excerpts of minista.py (about 200 lines in full): "
         "table lookup, arc evaluation and the setup/hold checks.")
    out(CORNERS, caption="Real output: worst negative slack (WNS), total "
        "negative slack (TNS), number of violating endpoints and worst hold "
        "slack at five SKY130 corners, for a 10 ns and a 20 ns clock "
        "(ns; ideal clock, pre-layout wire-load estimate).")
    out(PATH_SS, caption="Real output: the worst setup path at the sign-off "
        "corner ss_100C_1v60, 20 ns clock.")
    p("The table is a design review in itself:")
    bul(["**100 MHz passes only at typical.** At `ss_100C_1v60` the same "
         "netlist misses 10 ns by 8.5 ns with 34 failing endpoints. A block "
         "that is 'fast enough in simulation at tt' is not a product.",
         "**The critical path is the accumulator carry chain**: clock-to-Q of "
         "`acc_q`, one XNOR and OAI for the first bit, then 14 `maj3` carry "
         "stages at about 0.86 ns each at ss (0.40 ns at tt) and a "
         "multiplexing tail that selects between `sum`, hold and clear. The "
         "`a2111oi_0` in that tail has a 1.18 ns output slew at ss - close "
         "to the 1.5 ns library limit and above the 1.0 ns SDC limit - so "
         "`repair_design` will upsize it.",
         "**50 MHz meets the spec corner** with 1.52 ns of setup slack and "
         "hold is clean everywhere, smallest at ff (0.18 ns) as expected.",
         "**The ss_n40C_1v40 corner fails by 20 ns** - but 1.40 V is outside "
         "this spec's 1.60 V minimum, so it is **not a sign-off corner here**. "
         "It would be for a product whose regulator can droop that far. "
         "Choosing the corner list is a specification decision (Chapter 9).",
         "Pre-layout numbers ignore real wires and the clock tree. Keep "
         "**10-20 % of the period as margin** at this stage for a block "
         "of this size; at advanced nodes wires dominate and the margin must "
         "be larger."])
    box("expert", "How to reach 100 MHz at ss_100C_1v60",
        "Options, in order of preference: (1) a **parallel-prefix or "
        "carry-select adder** for the 24-bit accumulate (log-depth carry, "
        "roughly 5-8 stages instead of 24); (2) **carry-save accumulation** - "
        "keep the accumulator in redundant form and resolve it once per "
        "vector, which removes the carry chain from the loop entirely; (3) "
        "split the add across two cycles and accumulate two partial sums "
        "(changes latency, not throughput); (4) a faster library "
        "(`sky130_fd_sc_hs`) at the cost of area and leakage. A good "
        "interview answer names (2) - it is how real MAC arrays close timing.")

    # ------------------------------------------------------------------
    h2("Step 8 - Floorplan arithmetic")
    p("From the synthesized cell area, the site from the technology LEF and "
      "the tap-cell rule of the platform, the core and die size follow "
      "directly (Chapter 14):")
    code(FP_SRC, caption="floorplan.py")
    out(FP_OUT, caption="Real output: core and die size, row and site counts "
        "at four utilisation targets. Tap counts assume a tap every 14 um in "
        "every row - an upper bound, because OpenROAD's tapcell staggers "
        "taps between rows.")
    diagram([
        '  die 121.2 x 126.1 um (50 % utilisation)',
        '  +---------------------------------------------------------------+',
        '  |  10 um margin: pins on met2 (top/bottom) and met3 (sides)     |',
        '  |   +-------------------------------------------------------+   |',
        '  |   | row 39  VPWR =======================================  |   |',
        '  |   |   T  cells  T  cells  T  cells  T  cells  T  cells    |   |',
        '  |   | row 38  VGND =======================================  |   |',
        '  |   |   :      met4 stripes every 27.14 um (vertical)       |   |',
        '  |   |   :      met5 stripes every 27.2 um (horizontal)      |   |',
        '  |   | row 1   VGND =======================================  |   |',
        '  |   +--- core 101.2 x 106.1 um: 39 rows x 220 sites --------+   |',
        '  +---------------------------------------------------------------+',
        '   T = tapvpwrvgnd_1 well tap   ==== = met1 follow-pin rail (0.48 um)'],
        "The 50 % floorplan of mac_int8: 39 rows of 2.72 um, 220 sites of "
        "0.46 um, met1 rails, met4/met5 grid from the sky130hd PDN script.")
    bul(["At 50 % the block needs about **0.015 mm^2** of die, meeting the "
         "0.02 mm^2 spec; the core itself is 0.0107 mm^2.",
         "Utilisation is a trade-off, not a target: 70 % saves 25 % of die "
         "but leaves little room for the buffers `repair_design` and CTS "
         "will add (tens of cells here) and risks congestion over the "
         "multiplier. For a block this small, 50-60 % with `PLACE_DENSITY` "
         "0.6 is the usual starting point.",
         "Only about four met4 and four met5 stripes cross a 100 um core: "
         "IR drop is not an issue for 0.25 mW, but check it anyway - the "
         "same script on a 5 mm block is where grids fail."])

    # ------------------------------------------------------------------
    h2("Step 9 - Power estimate")
    p("Power (Chapter 11) is estimated from real Liberty data and real "
      "switching activity: the RTL simulation's VCD gives toggle rates per "
      "bit; the netlist and Liberty pin capacitances plus the wire-load "
      "model give the capacitance of every net; the Liberty "
      "`internal_power` tables on the flops' CLK pins give the energy each "
      "flop burns per clock cycle; `cell_leakage_power` gives leakage.")
    code(PWR_EX, caption="Excerpts of power.py: activity from the VCD, "
         "C V^2 f alpha switching power per net class, flop CLK internal "
         "energy.")
    out(PWR_OUT, caption="Real output at 50 MHz. Assumptions: activity from "
        "the RTL VCD (no glitches), wire-load-model wires, no clock tree "
        "(ideal clock), combinational-cell internal power omitted.")
    bul(["**The clock dominates**: clock-net switching plus flop clock-pin "
         "internal power is 0.156 of 0.247 mW at tt - 63 % - for a block "
         "whose data toggles only 9-15 % of the time. Each flop burns about "
         "40 fJ per clock edge pair just to exist. Clock gating the "
         "accumulator when `in_valid` is low (Chapter 11) is the first "
         "optimisation; with `dlclkp` integrated clock-gating cells it "
         "remains scan-friendly.",
         "**Energy per MAC**: 0.247 mW at 50 MHz with 75 % input utilisation "
         "(7430 beats in 9892 cycles) is about 0.247e-3 / (50e6 x 0.751) = "
         "**6.6 pJ per int8 MAC** at 130 nm and 1.8 V - before clock tree "
         "and glitch power. Modern 5-7 nm accelerators report well under 1 pJ "
         "per int8 MAC; scaling (Chapter 2) and aggressive data reuse are why.",
         "**Leakage is negligible at 25 deg C** (2.2 nW) and grows about "
         "300x at 100 deg C (0.68 uW at tt_100C). The SKY130 data gives an "
         "even higher value at ss_100C_1v60 (3.2 uW) than at tt_100C - "
         "counter-intuitive, since slow corners usually leak less; treat "
         "open-PDK leakage numbers as approximate and always check leakage "
         "at the hottest corner your spec allows.",
         "A real sign-off power run (OpenSTA `report_power` with a SAIF/VCD "
         "from gate-level simulation, or PrimePower/Voltus) includes the "
         "clock tree, glitches and internal power of every cell; expect it "
         "to be noticeably higher than this estimate."])

    # ------------------------------------------------------------------
    h2("Step 10 - Place, CTS and route (commands, not run)")
    p("The next steps need OpenROAD. With ORFS the whole back end is one "
      "`make`; the design configuration is a few lines:")
    code(ORFS_CFG, caption="designs/sky130hd/mac_int8/config.mk for ORFS "
         "(not run here). The SDC from Step 6 goes in constraint.sdc.")
    p("Doing the same steps by hand in the OpenROAD shell is the best way to "
      "learn what the flow does. The commands below are the real OpenROAD "
      "commands in their usual order; option details differ between "
      "versions, and the flows add many checks around them.")
    code(OR_TCL, caption="The back end of mac_int8 as OpenROAD Tcl commands "
         "(illustrative sequence, not run here; see the ORFS scripts for "
         "the production version).")
    tbl(["After...", "Check", "Good result for this block"],
        [["Floorplan", "Core area, rows, pin placement, PDN connectivity "
          "(`check_power_grid` or the PDN report)", "39 rows, all pins on "
          "legal tracks, no unconnected rails"],
         ["Global placement", "Overflow, density map, timing estimate "
          "(`report_wns` with placement parasitics)", "Overflow < 10 %; WNS "
          "close to the Step 7 estimate"],
         ["repair_design", "Max slew/cap/fanout violations, buffers added",
          "0 violations; `rst_n` split into a small buffer tree"],
         ["Detailed placement", "`check_placement`, displacement", "Legal, "
          "small average displacement"],
         ["CTS", "Skew, insertion latency, clock buffers, hold after "
          "`set_propagated_clock`", "Skew well under 0.1 ns for 67 sinks; "
          "hold fixed by repair_timing"],
         ["Global route", "GCell overflow, congestion report", "0 overflow"],
         ["Detailed route", "DRC count in `route_drc.rpt`, antenna",
          "0 DRCs, 0 antenna violations"],
         ["Extraction + STA", "WNS/TNS setup at ss, hold at ff, max "
          "slew/cap, per corner with SPEF", "Setup slack > 0 at ss_100C_1v60 "
          "(wires and the clock tree will eat part of the 1.5 ns estimate), "
          "hold > 0 at ff"]],
        widths=[16, 44, 40])

    h2("Step 11 - Sign-off and the GDSII hand-off (checklist, not run)")
    p("Sign-off (Chapter 18) is where the open flows call the PDK's layout "
      "tools. OpenLane 2 / LibreLane runs all of these automatically; in "
      "ORFS some are separate targets. What each check proves:")
    tbl(["Check", "Tool (open flow)", "Pass criterion"],
        [["GDS stream-out", "Magic and KLayout, merging the standard-cell "
          "GDS from the PDK", "Both produce a GDS; **XOR** of the two is "
          "empty"],
         ["DRC", "Magic (`drc check`) and KLayout decks from the PDK",
          "0 violations (density rules may need fill)"],
         ["LVS", "Magic extraction + Netgen `lvs` against the netlist",
          "'Circuits match uniquely'; no pin or property mismatches"],
         ["Antenna", "OpenROAD `check_antennas`, Magic", "0 violations after "
          "diode insertion"],
         ["Multi-corner STA", "OpenSTA with SPEF per corner",
          "Setup and hold met at all sign-off corners; max slew/cap/fanout "
          "clean"],
         ["IR drop", "PDNSim `analyze_power_grid`", "Worst static drop a few "
          "percent of VDD at most"],
         ["Timing-annotated GLS", "Icarus/Verilator with SDF (or commercial)",
          "Reset and a few vectors pass with back-annotated delays"],
         ["Equivalence", "Yosys `equiv_*` / EQY between RTL and final netlist",
          "Proven equivalent (catches ECO and optimisation errors)"]],
        widths=[20, 42, 38])
    checklist("mac_int8 tapeout checklist", [
        "Spec frozen: interfaces, overflow rule (<= 511 terms), corners, "
        "clock, area and power targets signed off by the architect",
        "RTL reviewed; lint clean with -Wall and no unexplained waivers",
        "Regression passes with random back-pressure; coverage of first/last "
        "beat, single-element vector, 511-term maximum, both stall types",
        "Synthesis log reviewed: no latches, no unmapped cells, no dont-use "
        "cells, tie cells for constants",
        "Formal equivalence RTL vs final netlist proven",
        "SDC reviewed: clock, I/O budget agreed with the integrator, reset "
        "recovery/removal timed, no unintended false paths",
        "Setup met at ss_100C_1v60 and hold at ff_n40C_1v95 with extracted "
        "parasitics and propagated clock",
        "Max transition / capacitance / fanout clean at all corners",
        "DRC, LVS, antenna clean; Magic/KLayout XOR empty",
        "IR drop and EM within limits; power estimate updated with the "
        "routed netlist and gate-level activity",
        "Scan inserted (or waiver agreed with the DFT owner) and test "
        "coverage reported",
        "Deliverables archived with tool and PDK versions: GDS, LEF abstract, "
        "Liberty model of the block, netlist, SPEF, SDC, reports, run "
        "configuration and git hash",
        "Shuttle/foundry precheck passed (names, pins, layers, GDS size)",
    ])

    h2("What the case study teaches")
    tbl(["Lesson", "Where it showed up"],
        [["Write the overflow rule and the corners into the spec first",
          "Step 1: 511 terms, ss_100C_1v60 setup / ff hold"],
         ["Only self-checking random tests catch data-dependent bugs",
          "Step 3: the missing `signed` was lint-clean"],
         ["Area is mostly logic, but flops and resets are not free",
          "Step 5: 30 % flops; 120 um^2 of unnecessary reset"],
         ["Architecture sets the critical path; synthesis effort does not",
          "Steps 5 and 7: ripple carry, ABC -D barely helps"],
         ["Corners change the answer by 2-6x", "Step 7: +0.83 ns slack at tt "
          "vs -8.5 ns at ss for 100 MHz"],
         ["Clock power dominates lightly active blocks", "Step 9: 63 % of the "
          "estimate is clock"],
         ["Floorplan numbers are arithmetic, not magic", "Step 8: rows, sites "
          "and die size from three inputs"]],
        widths=[50, 50])

    h2("Summary")
    bul(["A 644-cell, 5365 um^2 int8 MAC with valid/ready interfaces was "
         "specified, written, simulated (203 vectors), linted, synthesized "
         "on SKY130 hd and re-simulated at gate level - all for real.",
         "Multi-corner NLDM analysis on the real Liberty files shows 100 MHz "
         "at typical but only 50 MHz at the ss_100C_1v60 sign-off corner, "
         "limited by a 24-bit ripple-carry accumulator.",
         "At 50 % utilisation the block fits in a 121 x 126 um die with 39 "
         "rows of 220 sites; the pre-layout power estimate is about 0.25 mW "
         "at 50 MHz, two-thirds of it in the clock.",
         "Placement, CTS, routing, extraction and sign-off are driven by "
         "ORFS or LibreLane with the configuration and commands shown; each "
         "step has a concrete check before moving on.",
         "The tapeout checklist is the hand-off contract: frozen spec, clean "
         "static checks, timing at the right corners, clean DRC/LVS, and an "
         "archive that can reproduce the GDS."])
    h2("Exercises")
    bul(["Remove the reset from `out_acc`, re-run synthesis and GLS, and "
         "confirm the 120 um^2 saving. Does any X appear in simulation? Why "
         "not?",
         "Replace the accumulator with a carry-save form (keep sum and carry "
         "vectors, resolve on `in_last`). Estimate the new critical path and "
         "the area cost.",
         "Change `ACC_W` to 20. What is the new maximum vector length? Add a "
         "sticky `overflow` output and a test that provokes it.",
         "Using the floorplan script, find the utilisation at which the die "
         "is exactly 0.0125 mm^2, and argue whether you would accept it.",
         "Install ORFS or LibreLane, run the block through with the SDC of "
         "Step 6, and compare post-route WNS at ss_100C_1v60 with the "
         "1.52 ns pre-layout estimate. Explain the difference.",
         "Add clock gating for the accumulator using an integrated "
         "clock-gating cell and recompute the power estimate."],
        ordered=True)


# ======================================================================
# Chapter 26 - The ASIC career roadmap and interview preparation
# ======================================================================
def _ch26():
    chapter("The ASIC Career Roadmap and Interview Preparation")
    p("An ASIC is built by a dozen specialisms that rarely sit in the same "
      "room: architects, RTL designers, verification engineers, DFT, "
      "synthesis and timing, physical design, physical verification, CAD, "
      "analog, test and post-silicon. This book walked through all of them "
      "in the order the chip needs them. This chapter turns the same map "
      "into a career: what each role does all day, what it takes to be "
      "hired into it, how people grow from a first job to principal "
      "engineer, a 12-month study plan that uses this book and its three "
      "companions, portfolio projects that prove the skills, and how "
      "interviews for each role are actually run.")
    p("Titles, levels and salaries differ between companies and countries; "
      "the **scope** of each stage - a task, a block, a subsystem, a chip, a "
      "product line - is remarkably consistent, and that is what this "
      "chapter uses.")

    # ------------------------------------------------------------------
    h2("The roles on an ASIC team")
    tbl(["Role", "What you own", "Main deliverables", "Chapters"],
        [["**Architecture**", "Performance, power and area targets; block "
          "partitioning; memory and interconnect choices",
          "Architecture spec, performance model, PPA budget", "1, 5, 23"],
         ["**RTL design**", "Micro-architecture and RTL of blocks or "
          "subsystems", "Micro-arch spec, lint/CDC-clean RTL, SDC and UPF "
          "inputs", "6, 11; RTL guide"],
         ["**Design verification (DV)**", "Proving the RTL does what the "
          "spec says", "Test plan, UVM/cocotb environment, coverage closure, "
          "sign-off", "7; SV guide"],
         ["**DFT**", "Making the chip testable in production", "Scan, "
          "compression, MBIST, JTAG/IEEE 1500, ATPG patterns, coverage", "10, 21"],
         ["**Synthesis / STA**", "Turning RTL into a netlist that meets "
          "timing; timing sign-off", "Synthesis scripts, constraints, "
          "timing reports, ECO lists", "8, 9, 18"],
         ["**Physical design (PD)**", "Floorplan to routed database",
          "Floorplan, PDN, placed/CTS/routed DB, closure at all corners",
          "13-17, 19"],
         ["**Physical verification (PV)**", "DRC, LVS, ERC, antenna, DFM "
          "sign-off", "Clean decks, waivers, tapeout GDS", "3, 18, 19"],
         ["**CAD / methodology**", "Flows, scripts, tool qualification, "
          "compute and licence efficiency", "Reference flows, regression "
          "infrastructure, QoR dashboards", "13, 23, 24"],
         ["**Analog / mixed-signal (AMS)**", "PLLs, ADCs, SerDes, "
          "regulators, I/O", "Schematics, layout, characterisation, "
          "behavioural models", "2, 12"],
         ["**Test / product engineering**", "Production test programs, "
          "yield, binning, cost", "ATE programs, yield reports, test-time "
          "reduction", "21, 22"],
         ["**Post-silicon validation**", "Bring-up and validation of real "
          "chips", "Bring-up plan, characterisation data, errata", "22"]],
        widths=[20, 30, 34, 16],
        caption="The ASIC roles, what each owns and where this book covers "
        "it. 'RTL guide', 'SV guide' and 'Protocols guide' are the "
        "companion books.")
    box("key", "Pick a home, keep a map",
        "Nearly everyone specialises - a PD engineer does not write UVM and "
        "a DV engineer does not close hold at ff. But the best engineers in "
        "every role understand the stage before and after theirs: the RTL "
        "designer who can read a timing report, the PD engineer who can "
        "read RTL, the DV engineer who knows what DFT did to the netlist. "
        "That breadth is what this book is for.")

    h2("Skills tables by role")
    h3("Front-end roles")
    tbl(["Skill", "Architecture", "RTL design", "DV", "DFT"],
        [["Digital logic, CMOS basics", "Strong", "Strong", "Good", "Strong"],
         ["Verilog / SystemVerilog design", "Read", "Expert", "Good",
          "Good (netlists)"],
         ["SV verification, UVM, SVA", "-", "Good (SVA)", "Expert", "Basic"],
         ["C/C++ and Python", "Expert (models)", "Good", "Strong", "Good"],
         ["Performance modelling", "Expert", "Good", "-", "-"],
         ["Bus protocols (AXI, PCIe...)", "Strong", "Strong", "Strong", "Basic"],
         ["CDC / RDC, lint", "Aware", "Expert", "Good", "Good"],
         ["STA and SDC", "Aware", "Good", "Basic", "Good (test modes)"],
         ["Low power / UPF", "Strong", "Good", "Good (power-aware sim)",
          "Good"],
         ["Scan, ATPG, MBIST, JTAG", "Aware", "Aware", "Basic", "Expert"],
         ["Tcl scripting", "-", "Good", "Good", "Strong"]],
        widths=[28, 18, 18, 18, 18])
    h3("Back-end and silicon roles")
    tbl(["Skill", "Synth/STA", "PD", "PV", "CAD", "AMS", "Test/Post-Si"],
        [["Device physics, process", "Good", "Good", "Strong", "Basic",
          "Expert", "Strong"],
         ["Liberty, LEF/DEF, SPEF, SDF", "Expert", "Expert", "Good", "Expert",
          "Good", "Basic"],
         ["SDC and STA", "Expert", "Expert", "Basic", "Strong", "Basic",
          "Good"],
         ["Floorplan, PDN, CTS, routing", "Good", "Expert", "Good", "Strong",
          "Basic", "-"],
         ["DRC/LVS decks, DFM", "-", "Good", "Expert", "Good", "Strong", "-"],
         ["IR drop, EM, SI", "Good", "Strong", "Good", "Good", "Good", "-"],
         ["Tcl and Python", "Expert", "Expert", "Strong", "Expert", "Good",
          "Strong"],
         ["SPICE, schematics", "Basic", "Basic", "Good", "Basic", "Expert",
          "Good"],
         ["ATE, lab equipment, stats", "-", "-", "-", "-", "Good", "Expert"]],
        widths=[24, 14, 11, 11, 11, 11, 18])
    box("tip", "The skill every table leaves out",
        "Scripting. Every role above spends a large part of its time "
        "writing Tcl and Python to drive tools, parse reports and automate "
        "checks. Being the person who turns a two-day manual review into a "
        "ten-minute script is the fastest way to be noticed in your first "
        "year - and it is exactly what the Python models of this book "
        "practise.")


    h2("Where ASIC engineers work")
    tbl(["Employer type", "Examples of the work", "What it means for you"],
        [["**Fabless semiconductor companies**", "Design chips and sell "
          "them; manufacturing outsourced to a foundry", "Every role from "
          "architecture to post-silicon; the classic ASIC career"],
         ["**Integrated device manufacturers (IDMs)**", "Design and "
          "manufacture (own fabs)", "Closer to process, device and test "
          "engineering; strong in analog, power, automotive"],
         ["**System companies and hyperscalers**", "Custom silicon for their "
          "own products (phones, servers, AI accelerators, networking)",
          "Architecture tightly coupled to software; large teams, often "
          "with outsourced back end"],
         ["**Foundries**", "Process development, PDKs, libraries, design "
          "enablement", "PDK, library, DRC/LVS deck and reference-flow work "
          "(Chapters 3-4)"],
         ["**EDA vendors**", "Build the tools: synthesis, P&R, STA, "
          "verification, PV", "CAD, algorithms and application-engineer "
          "(AE) roles supporting customers"],
         ["**IP vendors**", "Processors, interfaces (PCIe, DDR, USB), "
          "memories, PHYs", "Deep specialisation; the Protocols guide is "
          "directly relevant"],
         ["**Design-services companies**", "Execute parts of other "
          "companies' chips (PD, DV, DFT)", "Many projects quickly; excellent "
          "for breadth early in a career"],
         ["**Start-ups**", "First chip of a new architecture", "Wide scope "
          "and ownership; schedule and funding risk"]],
        widths=[26, 38, 36])

    # ------------------------------------------------------------------
    h2("A staged roadmap: student to principal")
    tbl(["Stage", "Scope", "Expected skills", "Ready for the next stage when"],
        [["**Student / beginner**", "Coursework and personal projects",
          "Digital logic, one HDL, simulation, Linux, git, Python; one "
          "complete project through synthesis", "You can take a small spec "
          "to verified RTL and a synthesized netlist with a timing report "
          "you can explain"],
         ["**Junior engineer** (about 0-3 years)", "Tasks and small blocks, "
          "reviewed by seniors", "The tools and methodology of one role; "
          "reading reports; debugging your own failures; team conventions",
          "You deliver blocks or partitions with few review findings and "
          "close your own lint/timing/DRC issues"],
         ["**Senior engineer** (about 3-8 years)", "A whole IP, partition "
          "or verification environment, through tapeout", "Owning trade-offs, "
          "estimating schedules, interfacing with adjacent teams, mentoring, "
          "silicon debug", "Others come to you for reviews; you have taken "
          "something through tapeout and bring-up"],
         ["**Staff / lead** (about 8+ years)", "A subsystem, a chip's "
          "implementation or verification strategy, a team", "Methodology "
          "decisions, cross-team planning, risk management, hiring",
          "Your decisions shape more than one project"],
         ["**Principal / architect / distinguished**", "Product lines, "
          "company technology direction", "Architecture, technology "
          "roadmaps, customer and foundry relationships, deep expertise that "
          "the company is known for", "-"]],
        widths=[18, 22, 32, 28],
        caption="Years are indicative only; scope, independence and "
        "judgement define the stage.")
    box("expert", "What changes at each step",
        "Junior -> senior is mostly **technical depth plus ownership**: you "
        "stop asking what to check and start deciding what matters. Senior "
        "-> staff is mostly **influence**: writing the methodology others "
        "follow, spotting schedule risk early, making other engineers "
        "productive. Staff -> principal is mostly **judgement under "
        "uncertainty**: choosing a node, an architecture or a vendor with "
        "incomplete data and being right more often than not.")

    # ------------------------------------------------------------------
    h2("A 12-month study plan")
    p("The plan assumes about 10 hours a week alongside a degree or a job. "
      "Each month pairs reading with a hands-on deliverable; the deliverables "
      "add up to the portfolio of the next section. 'RTL' is the companion "
      "__RTL Design for SoC & ASIC__, 'SV' the __Verilog & SystemVerilog "
      "for SoC & ASIC__ guide and 'Proto' the __Communication Protocols for "
      "SoC & ASIC__ guide.")
    tbl(["Month", "Read (this book)", "Read (companions)", "Build / practise"],
        [["1", "Ch. 1-2: landscape, devices", "RTL Ch. 1-4; SV Ch. 1-6",
          "Install Icarus, Verilator, Yosys; write and simulate a counter, "
          "an FSM and a FIFO"],
         ["2", "Ch. 3-4: process, cells, Liberty", "RTL Ch. 5-10; SV Ch. 7-11",
          "Re-run the Chapter 24 Liberty and LEF scripts; synthesize your "
          "FIFO on SKY130 and explain every cell"],
         ["3", "Ch. 5-6: spec, RTL for ASIC", "RTL Ch. 11-16; SV Ch. 12-17; Proto Ch. 1-8",
          "Write a spec and RTL for an APB peripheral (UART or timer) with "
          "CDC-safe reset"],
         ["4", "Ch. 7: verification", "SV Ch. 18-26; RTL Ch. 22-26",
          "A self-checking, constrained-random testbench with assertions and "
          "coverage for month 3's block (UVM or cocotb)"],
         ["5", "Ch. 8-9: synthesis, STA", "RTL Ch. 17-18, 21",
          "Constraints for your block; sweep clock period and ABC -D; write "
          "a small STA script like Chapter 25's and compare corners"],
         ["6", "Ch. 10-11: DFT, low power", "RTL Ch. 19-20",
          "Insert scan in your netlist (by hand or a tool), compute the area "
          "cost; add clock gating and measure power change from VCD"],
         ["7", "Ch. 12-14: AMS/IO, PD setup, floorplan and PDN",
          "Proto Ch. 23-24", "Install ORFS or LibreLane; run the reference "
          "design; floorplan your block by hand, then with the flow"],
         ["8", "Ch. 15-17: placement, CTS, routing", "Proto Ch. 9-16",
          "Take your block to a routed GDS; vary density and clock period; "
          "record WNS, skew, DRC count"],
         ["9", "Ch. 18-19: sign-off, ECO, tapeout", "Proto Ch. 25-27",
          "DRC/LVS with Magic, KLayout and Netgen; fix one real violation; "
          "do a functional ECO by hand and re-verify"],
         ["10", "Ch. 20-22: packaging, test, bring-up", "Proto Ch. 17-22",
          "Submit a Tiny Tapeout design (or prepare one to shuttle-precheck "
          "quality); write its bring-up plan"],
         ["11", "Ch. 23: methodology, economics", "RTL Ch. 27-30; SV Ch. 27-28",
          "Pick a specialisation; do a deep project in it (see portfolio) "
          "and one open-source contribution"],
         ["12", "Ch. 24-26; Appendices A-D", "Protocol and RTL appendices",
          "Mock interviews with Appendix C questions; polish portfolio, "
          "write-ups and resume"]],
        widths=[7, 27, 25, 41],
        caption="A 12-month plan mapped to this book and its three companion "
        "books. Compress it if you already work in one area.")
    box("warn", "PITFALL - reading without building",
        "Twelve months of reading produces an engineer who can recite the "
        "definitions of skew and recovery time. Interviewers hire the one "
        "who has **closed** a hold violation and can show the report. Every "
        "month above ends in something you ran; keep the logs.")

    # ------------------------------------------------------------------
    h2("Portfolio projects that get a resume read")
    tbl(["Project", "Demonstrates", "Target roles", "Effort"],
        [["**Tiny Tapeout design** (for example a small RISC-V ALU, a "
          "PWM/servo controller, a CORDIC, a tiny int8 MAC array)",
          "The whole flow to real silicon; shuttle precheck; bring-up",
          "All digital roles, PD especially", "4-8 weeks"],
         ["**Chapter 25 extended**: carry-save MAC, clock gating, scan, "
          "routed with ORFS; a write-up comparing estimate and post-route",
          "PPA reasoning, timing closure, power analysis", "RTL, synthesis/"
          "STA, PD", "3-6 weeks"],
         ["**UVM or cocotb environment** for an open IP (a UART, an AXI-Lite "
          "slave) with coverage closure and bugs found",
          "Verification methodology, coverage-driven thinking", "DV",
          "4-6 weeks"],
         ["**FPGA project** (camera pipeline, audio DSP, soft-core SoC "
          "running software)", "Real clocks, I/O, CDC, debug on hardware",
          "RTL, post-silicon", "4-10 weeks"],
         ["**Open-source contribution** (a Yosys pass fix, an OpenROAD "
          "issue with a test case, a PDK DRC deck fix, cocotb extension)",
          "Working in a large code base, code review, communication",
          "CAD, PD, DV", "Ongoing"],
         ["**Analysis scripts** (Liberty explorer, timing-report parser, "
          "IR-drop model, yield model)", "Automation, data skills",
          "CAD, STA, test", "1-3 weeks each"],
         ["**Analog block on an open PDK** (bandgap, ring oscillator, "
          "comparator) with xschem + ngspice + Magic, LVS clean",
          "Full-custom flow", "AMS, PV", "6-12 weeks"]],
        widths=[36, 28, 20, 16])
    box("tip", "How to present a project",
        "A public repository with a README that states the spec, a block "
        "diagram, how to run it in one command, the results (area, timing "
        "at named corners, coverage, power) and **what went wrong and how "
        "you fixed it**. Reviewers read the last section first.")

    # ------------------------------------------------------------------
    h2("How ASIC interviews are structured")
    p("Most companies run a similar pipeline: a recruiter screen, one or two "
      "technical phone/video screens, then an on-site or virtual loop of "
      "four to six interviews (mostly technical, one or two on behaviour and "
      "project depth), and a debrief where the panel decides level as well "
      "as yes/no. Expect whiteboard (or shared-document) problem solving "
      "rather than trivia, and expect every answer to be followed by 'why?' "
      "and 'what if?'.")
    tbl(["Role", "Typical technical rounds", "Sample topics"],
        [["**RTL design**", "Digital logic; RTL coding live; micro-"
          "architecture design; CDC; resume deep-dive",
          "Design a synchronous/asynchronous FIFO; valid/ready pipeline with "
          "back-pressure; clock-domain crossing of a multi-bit value; "
          "arbiter; count ones in a word; pipelining a MAC (Chapter 25)"],
         ["**DV**", "SystemVerilog/OOP; testbench architecture; "
          "constrained random and coverage; debugging; SVA",
          "Build a scoreboard for a FIFO; write constraints for a packet; "
          "coverage plan for an arbiter; race conditions; UVM phases and "
          "sequences; assertion for a handshake"],
         ["**DFT**", "Scan and ATPG theory; test modes; MBIST; JTAG",
          "Stuck-at vs transition faults; scan chain shift/capture; "
          "compression ratio; at-speed test with launch-on-capture; "
          "test-mode timing constraints"],
         ["**Synthesis / STA**", "Timing theory; SDC; report reading; ECOs",
          "Setup/hold equations with skew; multicycle and false paths; "
          "OCV/CRPR; fix a hold violation without breaking setup; generated "
          "clocks; why tt passes and ss fails"],
         ["**Physical design**", "Flow and each stage; floorplan and PDN "
          "reasoning; CTS; congestion and timing closure",
          "Size a floorplan from cell area; macro placement guidelines; "
          "IR-drop fixes; useful skew; routing congestion causes; antenna "
          "fixes; hold fixing after CTS"],
         ["**Physical verification**", "DRC/LVS concepts; debugging; "
          "DFM; decks", "LVS short/open debug; soft connections; latch-up "
          "rules; density and fill; antenna ratio"],
         ["**CAD / methodology**", "Coding (Python/Tcl) live; flow design; "
          "tool knowledge", "Parse a timing report and summarise by clock "
          "group; design a regression system; data structures for a "
          "netlist"],
         ["**AMS**", "Circuit analysis; device physics; layout; "
          "specific block design", "Op-amp stability; PLL loop dynamics; "
          "matching and layout; bandgap; ADC architectures; noise"],
         ["**Test / post-silicon**", "Test theory; statistics; lab "
          "debugging; ATE", "Yield models; DPPM vs coverage; shmoo "
          "interpretation; binning; debugging a failing part"]],
        widths=[18, 32, 50])
    box("expert", "The follow-up question is the real question",
        "Almost every interviewer starts easy ('what is setup time?') and "
        "then pushes until you reach the edge of your knowledge ('...and "
        "with a negative-edge capture flop? With a clock-gating cell on the "
        "path? At the ff corner?'). The goal is to find **where** your "
        "understanding stops and **how you reason** there. Say what you "
        "know, state assumptions, reason aloud, and say 'I would check X' "
        "rather than guessing. Appendix C collects 100 such questions with "
        "answers.")

    h2("Mini-problems by role, with model answers")
    p("Short numerical problems are a staple of phone screens because they "
      "separate people who have used a concept from people who have read "
      "about it. Four examples, one per major area:")
    h3("STA: setup and hold with skew")
    p("__Launch and capture flops on the same 2.0 ns clock. Clock-to-Q 0.15 "
      "ns (min 0.12 ns), maximum combinational delay 1.40 ns, minimum 0.02 "
      "ns, setup 0.10 ns, hold 0.05 ns. The capture clock arrives 0.10 ns "
      "later than the launch clock. Setup uncertainty 0.10 ns, hold "
      "uncertainty 0.05 ns. Compute both slacks.__")
    eq(["setup slack = (T + skew - unc_s) - (t_cq,max + t_comb,max + t_su)",
        "= (2.00 + 0.10 - 0.10) - (0.15 + 1.40 + 0.10) = 2.00 - 1.65 = +0.35 ns",
        "",
        "hold slack  = (t_cq,min + t_comb,min) - (t_h + skew + unc_h)",
        "= (0.12 + 0.02) - (0.05 + 0.10 + 0.05) = 0.14 - 0.20 = -0.06 ns"],
        "Positive (late-capture) skew helps setup and hurts hold by the same "
        "amount (Chapter 9).")
    p("The hold violation is independent of the clock period, so slowing "
      "the clock cannot fix it. Fix it with about 0.1 ns of delay on **that** "
      "data path (a delay cell or a sized-down buffer, checked at the fast "
      "corner), or by reducing the skew; then re-check setup, which has "
      "0.35 ns to give.")
    h3("Physical design: sizing a core with macros")
    p("__A block has 1.2 mm^2 of standard cells and four SRAM macros of "
      "0.2 mm^2 each. Target standard-cell utilisation is 70 % and each "
      "macro needs a 10 % halo. What core area do you start with?__")
    eq(["core = std-cell area / utilisation + macro area x (1 + halo)",
        "= 1.2 / 0.70 + 4 x 0.2 x 1.10 = 1.714 + 0.880 = 2.59 mm^2"],
        "Then check the macro aspect ratios fit, pins face the logic that "
        "uses them, and channels between macros are routable (Chapter 14).")
    h3("DV: a weighted constraint")
    code(["class pkt;",
          "  rand bit [6:0] len;                   // 1..64 bytes",
          "  constraint c_len {",
          "    len inside {[1:64]};",
          "    len dist { 64 := 10, [1:63] :/ 90 };  // 10 % maximum-size packets",
          "  }",
          "endclass"],
        caption="`:=` gives the weight to each value, `:/` spreads it over "
        "the whole range - a favourite interview trap (the SV guide covers "
        "dist in detail). Written for this chapter, not run.")
    h3("DFT: test time with and without compression")
    eq(["1,000,000 scan flops, 8 scan-in pins, 50 MHz shift, 2000 patterns",
        "No compression: chain length 1e6 / 8 = 125,000 -> 2.5 ms/pattern -> 5.0 s per die",
        "100x compression: chain length 1,250 -> 25 us/pattern -> 0.05 s per die"],
        "Shift dominates test time; compression (Chapter 10) is what makes "
        "large SoCs economic to test (Chapter 21).")

    h3("A worked interview answer")
    p("__'Your block meets timing at typical but fails at the slow corner "
      "by 8 ns at 100 MHz. What do you do?'__ A strong answer, based on "
      "Chapter 25, goes in layers:")
    bul(["**Confirm the problem**: is ss_100C_1v60 really a sign-off corner "
         "for this product (supply range, temperature)? Is the SDC right - "
         "I/O budget, uncertainty, no missing multicycle path?",
         "**Characterise the path**: it is a 24-bit ripple-carry "
         "accumulator loop, 14 majority cells deep; the failure is "
         "structural, so sizing and buffering will not recover 8 ns.",
         "**Offer architecture options with costs**: carry-save "
         "accumulation (best; adds a resolve step and area), a "
         "parallel-prefix adder (log depth, more area and wiring), a "
         "two-cycle accumulate (latency), a faster library (leakage and "
         "area), or a lower clock (throughput).",
         "**Pick and justify**: carry-save, because it removes the carry "
         "from the recurrence entirely; show the estimated new critical path "
         "and area; re-run the corners.",
         "**Close the loop**: update the spec and the SDC, re-verify, and "
         "record the decision."])

    # ------------------------------------------------------------------
    h2("Soft skills that decide careers")
    tbl(["Skill", "Why it matters in ASIC work", "How to practise"],
        [["**Written communication**", "Specs, review comments, bug "
          "reports and tapeout sign-offs are the permanent record; a "
          "misunderstood spec costs a respin", "Write a one-page spec and a "
          "results summary for every project; have someone else implement "
          "from it"],
         ["**Estimation and planning**", "Tapeout dates are fixed by "
          "shuttle and mask schedules; slips cost money (Chapter 23)",
          "Estimate every task before starting; record actuals; learn your "
          "bias"],
         ["**Reviewing and being reviewed**", "Most bugs are caught by "
          "people, not tools", "Review open-source pull requests; ask for "
          "reviews and thank reviewers"],
         ["**Debugging discipline**", "Silicon debug has few observables and "
          "no second chance", "Hypothesis, cheapest falsifying experiment, "
          "one change at a time, log everything"],
         ["**Cross-team empathy**", "Every hand-off (RTL -> PD, PD -> PV, "
          "design -> test) is a negotiation", "Spend a week learning the "
          "adjacent role's tools; read their reports"],
         ["**Saying 'I do not know yet'**", "Wrong confident answers cause "
          "respins", "Practise stating assumptions and confidence levels"]],
        widths=[20, 40, 40])


    h2("Your first 90 days on an ASIC team")
    bul(["**Weeks 1-2**: get the flow running end to end on a known-good "
         "block; learn where logs, reports and the bug tracker live; read "
         "the chip spec and your block's history.",
         "**Weeks 3-6**: own a small, real task (a lint cleanup, a timing "
         "partition, a coverage hole) and close it completely, including the "
         "report nobody asked for.",
         "**Weeks 7-12**: find one repetitive manual step and automate it; "
         "present it at a team meeting. Ask to shadow the adjacent role for "
         "a day.",
         "Throughout: keep a notebook of every command, every mistake and "
         "every answer a senior gave you. It becomes your personal "
         "methodology guide - and the source of your first promotion case."])
    box("tip", "Resume lines that work",
        "Quantified and specific: 'Closed timing on a 1.2 GHz CPU partition "
        "(WNS -180 ps to 0) by restructuring two paths and adding useful "
        "skew' beats 'Responsible for timing closure'. For students: "
        "'Designed and taped out (Tiny Tapeout) an 8-bit MAC; 644 cells, "
        "50 MHz at ss_100C_1v60 on SKY130' beats a list of courses.")

    # ------------------------------------------------------------------
    h2("Final checklist")
    checklist("Before you apply", [
        "I can explain the complete ASIC flow from specification to "
        "qualification and name the owner and hand-off of each step",
        "I have taken at least one design through synthesis with a real "
        "library and can explain every cell type and the critical path",
        "I have written SDC for a block and can derive setup and hold slack "
        "by hand from a timing report",
        "I have run (or can describe step by step) floorplan, placement, "
        "CTS, routing and sign-off in an open flow, with the checks after "
        "each step",
        "I have a self-checking testbench with random stimulus and "
        "coverage for one of my designs",
        "I understand scan, stuck-at and transition faults, and what DFT "
        "costs in area and timing",
        "I can estimate dynamic and leakage power and explain why the clock "
        "dominates many blocks",
        "My portfolio has 2-3 projects with READMEs, results at named "
        "corners and a 'what went wrong' section",
        "I have answered the Appendix C questions for my target role aloud, "
        "and reviewed the ones I got wrong",
        "I can describe one hard problem I solved, what I tried, and what I "
        "would do differently",
    ])
    box("key", "The last word",
        "Chips are built by teams under immovable deadlines with no undo "
        "button. The engineers who thrive are the ones who **check before "
        "they trust**: they run the corner, read the report, simulate the "
        "negative operand and ask the adjacent team. Everything in this book "
        "- every run, every checklist - is practice for that habit.")

    h2("Summary")
    bul(["An ASIC team spans architecture, RTL, DV, DFT, synthesis/STA, PD, "
         "PV, CAD, AMS, test and post-silicon; each owns specific "
         "deliverables and hands off to the next.",
         "Careers progress by scope and judgement: task, block, subsystem, "
         "chip, product line.",
         "A 12-month plan pairs this book's chapters and the three companion "
         "books with a monthly hands-on deliverable, ending in a portfolio.",
         "Tiny Tapeout designs, open-source contributions, FPGA projects and "
         "extended versions of Chapter 25 make a portfolio that proves "
         "skills rather than listing them.",
         "Interviews probe the edge of your knowledge with follow-up "
         "questions; reasoning aloud from first principles and knowing what "
         "to check matter more than recall.",
         "Communication, estimation, review and debugging discipline decide "
         "careers as much as technical depth."])
    h2("Exercises")
    bul(["Choose a target role. Fill in its skills table row by row with your "
         "own honest level and list the three biggest gaps.",
         "Turn the 12-month plan into a dated plan for your situation, with "
         "one measurable deliverable per month.",
         "Write the README for a portfolio project you have done (or will "
         "do) using the structure of this chapter: spec, how to run, "
         "results at named corners, what went wrong.",
         "Pick five Appendix C questions for your role, answer each aloud in "
         "under three minutes, then write down the follow-up question an "
         "interviewer would ask and answer that too.",
         "Find an open issue in Yosys, OpenROAD, cocotb or an open PDK "
         "repository, reproduce it, and write up what you found - even if "
         "you do not fix it."],
        ordered=True)
