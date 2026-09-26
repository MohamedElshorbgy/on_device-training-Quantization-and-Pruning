"""Part IV (b) - Display/camera, chip-to-chip/die-to-die and debug/test (Chapters 21-23).

Every Verilog/SystemVerilog source in SRC was compiled with Icarus Verilog 12
(iverilog -g2012 -Wall) and simulated with vvp; OUT holds the captured output verbatim
(only the trailing "$finish called" line is omitted). Python references were run with
Python 3 and their printed output is also in OUT.
"""

from proto_guide.common import *  # noqa: F401,F403

SRC = {
    'vtg': r'''
module vtg #(parameter int HA = 640, HFP = 16, HS = 96, HBP = 48,   // horizontal, in pixels
             parameter int VA = 480, VFP = 10, VS = 2,  VBP = 33)   // vertical, in lines
( input  logic        pclk, rst_n,
  output logic        hsync_n, vsync_n, de,        // 640x480: both syncs active-low
  output logic [11:0] x, y );                     // position of the current pixel
  localparam int HT = HA + HFP + HS + HBP;        // 800 pixels per line
  localparam int VT = VA + VFP + VS + VBP;        // 525 lines per frame
  logic [11:0] hc, vc;
  always_ff @(posedge pclk or negedge rst_n)
    if (!rst_n) begin hc <= '0; vc <= '0; end
    else if (hc == HT-1) begin
      hc <= '0;
      vc <= (vc == VT-1) ? '0 : vc + 1'b1;
    end else hc <= hc + 1'b1;
  // active region first, then front porch, sync, back porch
  assign de      = (hc < HA) && (vc < VA);
  assign hsync_n = !((hc >= HA+HFP) && (hc < HA+HFP+HS));
  assign vsync_n = !((vc >= VA+VFP) && (vc < VA+VFP+VS));
  assign x = hc;  assign y = vc;
endmodule''',
    'tb_vtg': r'''
module tb;
  logic pclk = 0, rst_n = 0;  always #20 pclk = ~pclk;     // 25 MHz stand-in for 25.175
  logic hs_n, vs_n, de;  logic [11:0] x, y;
  vtg dut (.pclk, .rst_n, .hsync_n(hs_n), .vsync_n(vs_n), .de, .x, .y);
  int clocks, de_cnt, hs_pulses, vs_pulses, hs_width, max_hs_width, de_lines;
  logic hs_d = 1, vs_d = 1, de_d = 0;
  initial begin
    repeat (2) @(negedge pclk); rst_n = 1;     // release: first sample sees x=y=0
    // count exactly two frames starting at the first pixel of frame 0
    repeat (2 * 800 * 525) begin
      clocks++;  de_cnt += de;
      if (!hs_n && hs_d)  hs_pulses++;
      if (!vs_n && vs_d)  vs_pulses++;
      if (de && !de_d)    de_lines++;
      hs_width = hs_n ? 0 : hs_width + 1;
      if (hs_width > max_hs_width) max_hs_width = hs_width;
      hs_d = hs_n; vs_d = vs_n; de_d = de;
      @(negedge pclk);                                     // sample mid-pixel
    end
    $display("clocks=%0d  (2 frames x 800 x 525)", clocks);
    $display("active pixels=%0d  (2 x 640 x 480 = %0d)", de_cnt, 2*640*480);
    $display("active lines=%0d  hsync pulses=%0d  vsync pulses=%0d", de_lines, hs_pulses,
             vs_pulses);
    $display("hsync width=%0d pclk  frame rate at 25.175 MHz = %.3f Hz", max_hs_width,
             25.175e6 / (800.0*525.0));
    $finish;
  end
endmodule''',
    'ecc': r'''
// MIPI CSI-2 / DSI packet-header ECC (6 parity bits over the 24-bit header; P7=P6=0)
function automatic logic [5:0] hdr_ecc(input logic [23:0] d);
  hdr_ecc[0] = ^(d & 24'hF12CB7);   // D0 1 2 4 5 7 10 11 13 16 20 21 22 23
  hdr_ecc[1] = ^(d & 24'hF2555B);   // D0 1 3 4 6 8 10 12 14 17 20 21 22 23
  hdr_ecc[2] = ^(d & 24'h749A6D);   // D0 2 3 5 6 9 11 12 15 18 20 21 22
  hdr_ecc[3] = ^(d & 24'hB8E38E);   // D1 2 3 7 8 9 13 14 15 19 20 21 23
  hdr_ecc[4] = ^(d & 24'hDF03F0);   // D4..9 16..20 22 23
  hdr_ecc[5] = ^(d & 24'hEFFC00);   // D10..19 21 22 23
endfunction

module csi_hdr_rx (                       // receive side: correct 1 error, flag 2
  input  logic [31:0] hdr_in,             // {ECC byte, WC[15:8], WC[7:0], DataID}
  output logic [23:0] hdr_out,
  output logic        corrected, uncorrectable );
  logic [5:0] syn;  logic [23:0] fix;
  assign syn = hdr_ecc(hdr_in[23:0]) ^ hdr_in[29:24];
  always_comb begin
    fix = '0;
    for (int b = 0; b < 24; b++)                 // syndrome equals the column of bit b
      if (syn == hdr_ecc(24'(1) << b)) fix[b] = 1'b1;
  end
  assign hdr_out       = hdr_in[23:0] ^ fix;
  // a data-bit error matches a column; an ECC-bit error gives a weight-1 syndrome
  assign corrected     = (syn != 0) && ((fix != 0) || ($countones(syn) == 1));
  assign uncorrectable = (syn != 0) && !corrected;
endmodule''',
    'tb_ecc': r'''
module tb;
  logic [31:0] gold [1000];                 // {hdr[23:0], ecc} from the Python model
  logic [31:0] rx_in;  logic [23:0] rx_hdr;  logic corr, unc;
  csi_hdr_rx rx (.hdr_in(rx_in), .hdr_out(rx_hdr), .corrected(corr), .uncorrectable(unc));
  int mism, fixed1, bad1, det2, bad2;
  initial begin
    $readmemh("golden.hex", gold);
    $display("spec example DI=37 WC=01F0 -> ECC=%h", hdr_ecc(24'h01F037));
    foreach (gold[i]) if (hdr_ecc(gold[i][31:8]) !== gold[i][5:0]) mism++;
    $display("encoder vs Python on 1000 random headers: mismatches=%0d", mism);
    foreach (gold[i]) begin
      logic [29:0] cw;  int a, b;
      cw = {gold[i][5:0], gold[i][31:8]};           // 30-bit code word
      a = $urandom_range(29);  b = (a + 1 + $urandom_range(28)) % 30;
      rx_in = {2'b00, cw ^ (30'(1) << a)};  #1;       // single-bit error
      if (corr && !unc && rx_hdr == gold[i][31:8]) fixed1++; else bad1++;
      rx_in = {2'b00, cw ^ (30'(1) << a) ^ (30'(1) << b)};  #1;   // double error
      if (unc) det2++; else bad2++;
    end
    $display("single-bit errors corrected=%0d failed=%0d", fixed1, bad1);
    $display("double-bit errors flagged  =%0d missed=%0d", det2, bad2);
    $finish;
  end
endmodule''',
    'tmds': r'''
module tmds_enc (                        // DVI 1.0 / HDMI TMDS 8b/10b encoder, one channel
  input  logic       clk, rst_n,
  input  logic       de,                 // 1: video data, 0: control period
  input  logic [7:0] d,
  input  logic [1:0] c,                  // {C1,C0}: HSYNC/VSYNC on the blue channel
  output logic [9:0] q );
  logic [8:0] qm;  logic [3:0] n1q;  logic signed [4:0] cnt, diff;
  function automatic logic [8:0] stage1(input logic [7:0] v);   // transition minimisation
    logic xn;  logic [7:0] m;
    xn = ($countones(v) > 4) || ($countones(v) == 4 && !v[0]);
    m  = v;                                          // m[0] = v[0]
    for (int i = 1; i < 8; i++) m[i] = xn ? ~(m[i-1] ^ v[i]) : (m[i-1] ^ v[i]);
    return {!xn, m};                                 // bit 8: 1 = XOR used, 0 = XNOR used
  endfunction
  assign qm   = stage1(d);
  assign n1q  = 4'($countones(qm[7:0]));
  assign diff = 5'(n1q) - 5'(8 - n1q);               // N1 - N0 of qm[7:0]
  always_ff @(posedge clk or negedge rst_n)            // stage 2: DC balance
    if (!rst_n) begin q <= '0; cnt <= '0; end
    else if (!de) begin
      cnt <= '0;
      case (c)
        2'b00: q <= 10'b1101010100;   2'b01: q <= 10'b0010101011;
        2'b10: q <= 10'b0101010100;   default: q <= 10'b1010101011;
      endcase
    end else if (cnt == 0 || diff == 0) begin
      q   <= {~qm[8], qm[8], qm[8] ? qm[7:0] : ~qm[7:0]};
      cnt <= qm[8] ? cnt + diff : cnt - diff;
    end else if ((cnt > 0 && diff > 0) || (cnt < 0 && diff < 0)) begin
      q   <= {1'b1, qm[8], ~qm[7:0]};                  // invert to pull cnt back
      cnt <= cnt + (qm[8] ? 5'sd2 : 5'sd0) - diff;
    end else begin
      q   <= {1'b0, qm[8], qm[7:0]};
      cnt <= cnt - (qm[8] ? 5'sd0 : 5'sd2) + diff;
    end
endmodule''',
    'tb_tmds': r'''
module tb;
  localparam int N = 6024;
  logic [9:0] mem [2*N];                    // pairs: data byte, expected 10-bit symbol
  logic clk = 0, rst_n = 0, de = 0;  always #5 clk = ~clk;
  logic [7:0] d;  logic [1:0] c = 2'b00;  logic [9:0] q;
  tmds_enc dut (.clk, .rst_n, .de, .d, .c, .q);
  int mism, rd, rd_min, rd_max, run, max_run, tr, max_tr;  logic last;
  initial begin
    $readmemh("tmds_gold.hex", mem);
    @(negedge clk) rst_n = 1;
    @(negedge clk) c = 2'b01;                                   // HSYNC=1 control period
    @(negedge clk) $display("control C1C0=01 -> %b (expect 0010101011)", q);
    for (int i = 0; i < N; i++) begin
      de = 1;  d = mem[2*i][7:0];
      @(negedge clk);
      if (q !== mem[2*i+1]) mism++;
      tr = 0;
      for (int b = 0; b < 10; b++) begin                        // LSB is sent first
        rd += q[b] ? 1 : -1;
        if (rd < rd_min) rd_min = rd;  if (rd > rd_max) rd_max = rd;
        if (b > 0 && q[b] != q[b-1]) tr++;
        run = (i + b > 0 && q[b] == last) ? run + 1 : 1;  last = q[b];
        if (run > max_run) max_run = run;
      end
      if (tr > max_tr) max_tr = tr;
    end
    $display("symbols=%0d  mismatches vs Python=%0d", N, mism);
    $display("running disparity of the line: min=%0d max=%0d final=%0d", rd_min, rd_max, rd);
    $display("longest run of equal bits=%0d  max transitions in a symbol=%0d",
             max_run, max_tr);
    $finish;
  end
endmodule''',
    'pcs': r'''
// 64b/66b PCS pieces (IEEE 802.3 Clause 49 style). Bit 0 is transmitted first.
module scr58 #(parameter bit DESCR = 0) (    // self-synchronous x^58 + x^39 + 1
  input  logic        clk, rst_n, en,
  input  logic [63:0] din,
  output logic [63:0] dout );
  logic [57:0] s;                            // s[0] = most recent line bit
  function automatic logic [121:0] step(input logic [57:0] st, input logic [63:0] d);
    logic [63:0] o;
    for (int i = 0; i < 64; i++) begin
      o[i] = d[i] ^ st[38] ^ st[57];
      st   = {st[56:0], DESCR ? d[i] : o[i]};      // always shift in the LINE bit
    end
    return {st, o};
  endfunction
  logic [57:0] s_n;
  assign {s_n, dout} = step(s, din);
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) s <= DESCR ? '0 : '1;          // TX seed all-ones; RX needs no seed
    else if (en) s <= s_n;
endmodule

module block_lock (                          // 1 bit in per clock, finds the 66-bit boundary
  input  logic        clk, rst_n,
  input  logic        bit_in,
  output logic        blk_valid,             // pulses when a 66-bit block is assembled
  output logic [65:0] blk,                   // blk[1:0] = sync header, blk[65:2] = payload
  output logic        block_lock,
  output logic [15:0] slips );
  logic [65:0] sr;  logic [6:0] bitcnt;  logic [6:0] sh_cnt;  logic [4:0] bad_cnt;
  wire [65:0] win   = {bit_in, sr[65:1]};    // newest bit enters at the top
  wire        sh_ok = win[0] ^ win[1];       // 01 or 10 is a legal sync header
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      sr <= '0; bitcnt <= '0; sh_cnt <= '0; bad_cnt <= '0;
      block_lock <= 1'b0; slips <= '0; blk_valid <= 1'b0; blk <= '0;
    end else begin
      sr <= win;  blk_valid <= 1'b0;
      if (bitcnt != 65) bitcnt <= bitcnt + 1'b1;
      else begin                               // a candidate block boundary
        bitcnt <= '0;  blk <= win;  blk_valid <= 1'b1;
        if (!block_lock) begin
          if (!sh_ok) begin                    // SLIP: discard one bit, restart counting
            bitcnt <= 7'd127;  // wraps to 0 on the next clock -> window moves by 1 bit
            sh_cnt <= '0;  slips <= slips + 1'b1;
          end else if (sh_cnt == 63) begin block_lock <= 1'b1; sh_cnt <= '0; end
          else sh_cnt <= sh_cnt + 1'b1;
        end else begin                         // locked: 16 bad headers in 64 -> lose lock
          if (!sh_ok && bad_cnt == 15) begin
            block_lock <= 1'b0; sh_cnt <= '0; bad_cnt <= '0;
            bitcnt <= 7'd127;  slips <= slips + 1'b1;
          end else if (sh_cnt == 63) begin sh_cnt <= '0; bad_cnt <= '0; end
          else begin sh_cnt <= sh_cnt + 1'b1; bad_cnt <= bad_cnt + !sh_ok; end
        end
      end
    end
endmodule''',
    'tb_pcs': r'''
module tb;
  localparam int NB = 700, JUNK = 37;
  logic clk = 0, rst_n = 0, rx_rst_n = 0;  always #1 clk = ~clk;
  function automatic logic [63:0] payload(int i);
    return {32'(i), 32'(i) * 32'h9E3779B9};
  endfunction
  // ---------------- transmitter: scramble payloads, prepend sync header ----------------
  logic [63:0] gold [NB];  logic [63:0] tx_in, tx_out;  logic tx_en = 0;
  scr58 #(.DESCR(0)) tx (.clk, .rst_n, .en(tx_en), .din(tx_in), .dout(tx_out));
  logic [65:0] line [NB];
  bit q [$];                                        // serial line, bit 0 first
  // ---------------- receiver: block lock + descrambler ----------------
  logic rx_bit = 0, bv, lock;  logic [65:0] blk;  logic [15:0] slips;  logic [63:0] rx_pl;
  block_lock bl (.clk, .rst_n(rx_rst_n), .bit_in(rx_bit), .blk_valid(bv), .blk,
                 .block_lock(lock), .slips);
  scr58 #(.DESCR(1)) rx (.clk, .rst_n(rx_rst_n), .en(bv), .din(blk[65:2]), .dout(rx_pl));
  int mism, nbit, exp_i = -1, errs, good_blks;  logic lock_d = 0;
  initial begin
    $readmemh("scr_gold.hex", gold);
    @(negedge clk) rst_n = 1;
    for (int i = 0; i < NB; i++) begin
      tx_in = payload(i);  #0;
      if (tx_out !== gold[i]) mism++;
      line[i] = {tx_out, (i % 16 == 0) ? 2'b01 : 2'b10};  // line order: 01 data, 10 ctrl
      tx_en = 1;  @(negedge clk);  tx_en = 0;
    end
    $display("TX scrambler vs Python, %0d blocks: mismatches=%0d", NB, mism);
    for (int i = 0; i < JUNK; i++) q.push_back(1'($urandom));   // unknown bit offset
    for (int i = 0; i < NB; i++) begin
      if (i >= 250 && i < 290) line[i][1:0] = 2'b11;        // burst of bad headers
      if (i == 640) line[i] = line[i] ^ (66'(1) << 12);    // one line bit error
      for (int b = 0; b < 66; b++) q.push_back(line[i][b]);
    end
    nbit = q.size();  rx_rst_n = 1;                        // start the receiver
    for (int n = 0; n < nbit; n++) begin
      rx_bit = q.pop_front();  @(negedge clk);
      if (lock != lock_d)
        $display("bit %5d: block_lock=%0d  slips so far=%0d", n, lock, slips);
      lock_d = lock;
      if (bv && lock) begin                                // aligned block, descrambled
        if (exp_i < 0) exp_i = int'(rx_pl[63:32]);        // first block after lock
        else exp_i++;
        if (rx_pl == payload(exp_i)) good_blks++;
        else begin
          errs = $countones(rx_pl ^ payload(exp_i));
          $display("block %0d: %0d bit errors after descrambling", exp_i, errs);
        end
      end
      if (bv && !lock) exp_i = -1;
    end
    $display("blocks descrambled correctly while locked: %0d", good_blks);
    $finish;
  end
endmodule''',
    'tap': r'''
module jtag_tap #(parameter logic [31:0] IDCODE = {4'h1, 16'hA5B3, 11'h0AB, 1'b1},
                  parameter int NBSC = 8)             // boundary-scan cells (= pins)
( input  logic tck, tms, tdi, trst_n,
  output logic tdo, tdo_en,
  input  logic [NBSC-1:0] pin_in,                     // what the pads see
  output logic [NBSC-1:0] pin_out, input logic [NBSC-1:0] core_out,
  output logic [3:0] state_o );
  localparam logic [3:0] TLR = 0, RTI = 1, SEL_DR = 2, CAP_DR = 3, SH_DR = 4, EX1_DR = 5,
      PA_DR = 6, EX2_DR = 7, UPD_DR = 8, SEL_IR = 9, CAP_IR = 10, SH_IR = 11, EX1_IR = 12,
      PA_IR = 13, EX2_IR = 14, UPD_IR = 15;
  localparam logic [3:0] I_EXTEST = 4'b0000, I_IDCODE = 4'b0001, I_SAMPLE = 4'b0010,
                         I_BYPASS = 4'b1111;
  logic [3:0] st, nx;
  always_comb case (st)                               // the 16-state TAP controller
    TLR:    nx = tms ? TLR    : RTI;     RTI:    nx = tms ? SEL_DR : RTI;
    SEL_DR: nx = tms ? SEL_IR : CAP_DR;  CAP_DR: nx = tms ? EX1_DR : SH_DR;
    SH_DR:  nx = tms ? EX1_DR : SH_DR;   EX1_DR: nx = tms ? UPD_DR : PA_DR;
    PA_DR:  nx = tms ? EX2_DR : PA_DR;   EX2_DR: nx = tms ? UPD_DR : SH_DR;
    UPD_DR: nx = tms ? SEL_DR : RTI;     SEL_IR: nx = tms ? TLR    : CAP_IR;
    CAP_IR: nx = tms ? EX1_IR : SH_IR;   SH_IR:  nx = tms ? EX1_IR : SH_IR;
    EX1_IR: nx = tms ? UPD_IR : PA_IR;   PA_IR:  nx = tms ? EX2_IR : PA_IR;
    EX2_IR: nx = tms ? UPD_IR : SH_IR;   default: nx = tms ? SEL_DR : RTI;   // UPD_IR
  endcase
  always_ff @(posedge tck or negedge trst_n) st <= !trst_n ? TLR : nx;
  assign state_o = st;

  logic [3:0] ir_sr, ir;  logic [31:0] id_sr;  logic by_sr;
  logic [NBSC-1:0] bs_sr, bs_upd;
  always_ff @(posedge tck) begin                      // capture / shift on rising TCK
    if (st == CAP_IR) ir_sr <= 4'b0101;               // 1149.1: two LSBs must be 01
    if (st == SH_IR)  ir_sr <= {tdi, ir_sr[3:1]};
    case (st)
      CAP_DR: begin id_sr <= IDCODE; by_sr <= 1'b0; bs_sr <= pin_in; end
      SH_DR:  case (ir)
                I_IDCODE:           id_sr <= {tdi, id_sr[31:1]};
                I_SAMPLE, I_EXTEST: bs_sr <= {tdi, bs_sr[NBSC-1:1]};
                default:            by_sr <= tdi;      // BYPASS and unused codes
              endcase
      default: ;
    endcase
  end
  always_ff @(negedge tck or negedge trst_n)          // update + TDO on falling TCK
    if (!trst_n) begin ir <= I_IDCODE; bs_upd <= '0; tdo <= 1'b0; tdo_en <= 1'b0; end
    else begin
      if (st == TLR)    ir <= I_IDCODE;               // IDCODE is selected after reset
      if (st == UPD_IR) ir <= ir_sr;
      if (st == UPD_DR && (ir == I_SAMPLE || ir == I_EXTEST)) bs_upd <= bs_sr;
      tdo_en <= (st == SH_IR) || (st == SH_DR);
      tdo    <= (st == SH_IR) ? ir_sr[0] :
                (ir == I_IDCODE) ? id_sr[0] :
                (ir == I_SAMPLE || ir == I_EXTEST) ? bs_sr[0] : by_sr;
    end
  assign pin_out = (ir == I_EXTEST) ? bs_upd : core_out;   // EXTEST drives the pads
endmodule''',
    'tb_tap': r'''
module tb;
  logic tck = 0, tms = 1, tdi = 0, trst_n = 0, tdo, tdo_en;
  logic [7:0] pin_in = 8'hC3, pin_out, core_out = 8'h00;  logic [3:0] st;
  jtag_tap dut (.*, .state_o(st));
  logic tdo_s;                                            // TDO sampled at rising TCK
  task automatic clk(input logic m, input logic d = 0);   // one TCK period
    tms = m; tdi = d; #5 tdo_s = tdo; tck = 1; #5 tck = 0;
  endtask
  task automatic shift(input int n, input logic [63:0] din, output logic [63:0] dout);
    dout = '0;                         // enter from Capture-xR; leave in Exit1-xR
    for (int i = 0; i < n; i++) begin
      clk(i == n-1, din[i]);
      dout[i] = tdo_s;
    end
  endtask
  logic [63:0] r;  int bad;
  initial begin
    #1 trst_n = 1;
    repeat (5) clk(1);  clk(0);                              // Test-Logic-Reset -> RTI
    clk(1); clk(0); clk(0);                                  // Select-DR, Capture-DR, Shift-DR
    shift(32, '0, r);  clk(1); clk(0);                       // Update-DR, RTI
    $display("IDCODE after reset = %h  (LSB=%0d, manuf=%h, part=%h, ver=%h)",
             r[31:0], r[0], r[11:1], r[27:12], r[31:28]);
    clk(1); clk(1); clk(0); clk(0);                          // Sel-DR, Sel-IR, Cap-IR, Sh-IR
    shift(4, 64'hF, r);  clk(1); clk(0);                     // load BYPASS
    $display("IR capture value     = %b  (1149.1 requires xx01)", r[3:0]);
    clk(1); clk(0); clk(0);
    shift(8, 64'hB5, r);  clk(1); clk(0);
    $display("BYPASS: in 10110101 -> out %b (in << 1: one-bit delay)", r[7:0]);
    clk(1); clk(1); clk(0); clk(0);  shift(4, 64'h2, r); clk(1); clk(0);  // SAMPLE/PRELOAD
    clk(1); clk(0); clk(0);  shift(8, 64'h5A, r); clk(1); clk(0);        // capture + preload
    $display("SAMPLE: pins=%b captured=%b, preloaded 01011010", pin_in, r[7:0]);
    clk(1); clk(1); clk(0); clk(0);  shift(4, 64'h0, r); clk(1); clk(0);  // EXTEST
    $display("EXTEST: pads now driven with %b", pin_out);
    for (int t = 0; t < 2000; t++) begin                     // any state + 5 x TMS=1 -> TLR
      repeat ($urandom_range(1, 12)) clk(1'($urandom));
      repeat (5) clk(1);
      if (st != 4'd0) bad++;
    end
    $display("random walks ending in 5 x TMS=1 that missed Test-Logic-Reset: %0d/2000", bad);
    $finish;
  end
endmodule''',
    'swd': r'''
// Arm SWD (ADIv5) request packet: 8 bits, sent LSB first on SWDIO
//   bit: 0 Start=1 | 1 APnDP | 2 RnW | 3 A[2] | 4 A[3] | 5 Parity | 6 Stop=0 | 7 Park=1
function automatic logic [7:0] swd_req(input logic apndp, rnw, input logic [3:2] a);
  logic par;
  par = apndp ^ rnw ^ a[2] ^ a[3];             // even parity over bits 1..4
  return {1'b1, 1'b0, par, a[3], a[2], rnw, apndp, 1'b1};
endfunction
// data phase: 32 data bits LSB first, then one even-parity bit
function automatic logic [32:0] swd_data(input logic [31:0] d);
  return {^d, d};
endfunction''',
    'tb_swd': r'''
module tb;
  logic [7:0] gold [16];  int mism;  logic [7:0] r;  logic [32:0] dp;
  initial begin
    $readmemh("swd_gold.hex", gold);           // generated by the Python reference
    for (int n = 0; n < 16; n++) begin         // n = {APnDP, RnW, A2, A3}
      r = swd_req(n[3], n[2], {n[0], n[1]});
      if (r !== gold[n]) mism++;
    end
    $display("16 request packets vs Python: mismatches=%0d", mism);
    $display("APnDP RnW A[3:2]  packet  on the wire (first bit left)");
    for (int k = 0; k < 4; k++) for (int rw = 0; rw < 2; rw++) begin   // DP 0x0..0xC
      r = swd_req(1'b0, rw[0], k[1:0]);
      $display("  0     %0d   %b     0x%h   %b%b%b%b%b%b%b%b", rw, k[1:0], r,
               r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]);
    end
    r = swd_req(1'b1, 1'b1, 2'b11);
    $display("AP read of 0xC (e.g. MEM-AP DRW) = 0x%h", r);
    dp = swd_data(32'h2BA01477);
    $display("data 0x2BA01477 -> parity bit %0d (ones in data = %0d)", dp[32],
             $countones(dp[31:0]));
    $finish;
  end
endmodule''',
    'py_ecc': r'''
P = [
 [0,1,2,4,5,7,10,11,13,16,20,21,22,23],
 [0,1,3,4,6,8,10,12,14,17,20,21,22,23],
 [0,2,3,5,6,9,11,12,15,18,20,21,22],
 [1,2,3,7,8,9,13,14,15,19,20,21,23],
 [4,5,6,7,8,9,16,17,18,19,20,22,23],
 [10,11,12,13,14,15,16,17,18,19,21,22,23]]
def ecc(h):
    e=0
    for i,bits in enumerate(P):
        v=0
        for b in bits: v^=(h>>b)&1
        e|=v<<i
    return e
cols=[sum(((b in P[i])<<i) for i in range(6)) for b in range(24)]
print("cols unique",len(set(cols))==24, "min weight",min(bin(c).count('1') for c in cols))
print(hex(ecc(0x01F037)))
for h in [0x000000,0x01F037,0x0A0000|0x2B, 0x780012,0x000001]:
    print(hex(h),hex(ecc(h)))''',
    'py_tmds': r'''
import random
def tmds(d, cnt):
    n1 = bin(d).count('1')
    xnor = n1 > 4 or (n1 == 4 and not (d & 1))
    qm = d & 1
    for i in range(1, 8):
        b = ((qm >> (i-1)) ^ (d >> i)) & 1
        qm |= ((b ^ 1) if xnor else b) << i
    qm8 = 0 if xnor else 1
    n1q = bin(qm).count('1'); diff = n1q - (8 - n1q)
    if cnt == 0 or diff == 0:
        q = ((qm8 ^ 1) << 9) | (qm8 << 8) | (qm if qm8 else qm ^ 0xFF)
        cnt = cnt + diff if qm8 else cnt - diff
    elif (cnt > 0 and diff > 0) or (cnt < 0 and diff < 0):
        q = (1 << 9) | (qm8 << 8) | (qm ^ 0xFF); cnt = cnt + 2*qm8 - diff
    else:
        q = (qm8 << 8) | qm; cnt = cnt - 2*(1-qm8) + diff
    return q, cnt
random.seed(7)
data = [random.getrandbits(8) for _ in range(4000)] + [0x00]*500 + [0xFF]*500 \
       + list(range(256))*4
cnt = 0
with open('tmds_gold.hex', 'w') as f:
    for d in data:
        q, cnt = tmds(d, cnt); f.write('%02x %03x\n' % (d, q))
print(len(data))''',
    'py_scr': r'''
M = (1 << 64) - 1
def payload(i): return (i << 32) | ((i * 0x9E3779B9) & 0xFFFFFFFF)
s = [1] * 58                              # s[0] = most recent bit; seed all ones
def scramble(d):
    global s
    o = 0
    for i in range(64):
        b = ((d >> i) & 1) ^ s[38] ^ s[57]
        o |= b << i
        s = [b] + s[:57]
    return o
with open('scr_gold.hex', 'w') as f:
    for i in range(700):
        f.write('%016x\n' % scramble(payload(i)))
print(open('scr_gold.hex').read().split()[:3])''',
    'py_crc': r'''
def csi2_crc16(data):                 # x^16+x^12+x^5+1, seed 0xFFFF, LSB first
    c = 0xFFFF
    for byte in data:
        c ^= byte
        for _ in range(8):
            c = (c >> 1) ^ 0x8408 if c & 1 else c >> 1
    return c
pay = bytes.fromhex("FF000002B9DCF372BBD4B85AC875C27C81F805DFFF000001")
print("payload of %d bytes -> CRC-16 = 0x%04X" % (len(pay), csi2_crc16(pay)))
pay2 = bytes.fromhex("FF000001B9DCF372BBD4B85AC875C27C81F805DFFF000001")
print("byte 3 changed 02 -> 01 -> CRC-16 = 0x%04X" % csi2_crc16(pay2))''',
    'py_bw': r'''
w, h, fps = 3840, 2160, 60
for name, bpp in [("RAW10", 10), ("RAW12", 12), ("YUV422-8", 16)]:
    act = w * h * fps * bpp / 1e9
    print("%-9s active payload %6.2f Gb/s" % (name, act))
raw10 = w * h * fps * 10
link = raw10 * 1.20                    # ~20% for blanking, packet overhead, margin
for lanes in (2, 4):
    print("D-PHY %d lanes: %.2f Gb/s per lane" % (lanes, link / lanes / 1e9))
print("C-PHY 3 trios: %.2f Gsym/s per trio (16 bits / 7 symbols)"
      % (link / 3 / (16 / 7) / 1e9))''',
}

OUT = {
    'vtg': ['clocks=840000  (2 frames x 800 x 525)', 'active pixels=614400  (2 x 640 x 480 = 614400)', 'active lines=960  hsync pulses=1050  vsync pulses=2', 'hsync width=96 pclk  frame rate at 25.175 MHz = 59.940 Hz'],
    'ecc': ['spec example DI=37 WC=01F0 -> ECC=3f', 'encoder vs Python on 1000 random headers: mismatches=0', 'single-bit errors corrected=1000 failed=0', 'double-bit errors flagged  =1000 missed=0'],
    'tmds': ['control C1C0=01 -> 0010101011 (expect 0010101011)', 'symbols=6024  mismatches vs Python=0', 'running disparity of the line: min=-10 max=10 final=0', 'longest run of equal bits=13  max transitions in a symbol=5'],
    'pcs': ['TX scrambler vs Python, 700 blocks: mismatches=0', 'bit  8946: block_lock=1  slips so far=37', 'bit 18450: block_lock=0  slips so far=38', 'bit 30726: block_lock=1  slips so far=103', 'block 640: 2 bit errors after descrambling', 'block 641: 1 bit errors after descrambling', 'blocks descrambled correctly while locked: 378'],
    'tap': ['IDCODE after reset = 1a5b3157  (LSB=1, manuf=0ab, part=a5b3, ver=1)', 'IR capture value     = 0101  (1149.1 requires xx01)', 'BYPASS: in 10110101 -> out 01101010 (in << 1: one-bit delay)', 'SAMPLE: pins=11000011 captured=11000011, preloaded 01011010', 'EXTEST: pads now driven with 01011010', 'random walks ending in 5 x TMS=1 that missed Test-Logic-Reset: 0/2000'],
    'swd': ['16 request packets vs Python: mismatches=0', 'APnDP RnW A[3:2]  packet  on the wire (first bit left)', '  0     0   00     0x81   10000001', '  0     1   00     0xa5   10100101', '  0     0   01     0xa9   10010101', '  0     1   01     0x8d   10110001', '  0     0   10     0xb1   10001101', '  0     1   10     0x95   10101001', '  0     0   11     0x99   10011001', '  0     1   11     0xbd   10111101', 'AP read of 0xC (e.g. MEM-AP DRW) = 0x9f', 'data 0x2BA01477 -> parity bit 0 (ones in data = 14)'],
    'crc': ['payload of 24 bytes -> CRC-16 = 0x00F0', 'byte 3 changed 02 -> 01 -> CRC-16 = 0x5944'],
    'bw': ['RAW10     active payload   4.98 Gb/s', 'RAW12     active payload   5.97 Gb/s', 'YUV422-8  active payload   7.96 Gb/s', 'D-PHY 2 lanes: 2.99 Gb/s per lane', 'D-PHY 4 lanes: 1.49 Gb/s per lane', 'C-PHY 3 trios: 0.87 Gsym/s per trio (16 bits / 7 symbols)'],
}


def _v(name, caption=None):
    """Show a verified source (Verilog/SV or Python) from SRC."""
    code(SRC[name].strip("\n").split("\n"), caption)


def _o(name, caption=None):
    """Show real captured output."""
    out(OUT[name], caption)


# =============================================================================
#     PART IV (b) - chapters 21-23 (the part divider is opened by part4a)
# =============================================================================
def part4b():
    _ch21()
    _ch22()
    _ch23()


# ---------------------------------------------------------------- Ch 21 ---
def _ch21():
    chapter("Display and Camera: MIPI D-PHY/C-PHY, CSI-2, DSI, HDMI and "
            "DisplayPort", newpage=True)
    p("Pixels are the largest continuous data streams most SoCs handle. A "
      "phone application processor ingests several camera streams at once, "
      "each several gigabits per second, and pushes a high-refresh panel at "
      "similar rates, all while the rest of the chip sleeps as much as it "
      "can. Two families of interfaces dominate. For the short, "
      "power-critical links inside a device, the MIPI Alliance defines the "
      "physical layers **D-PHY** and **C-PHY** and the protocols **CSI-2** "
      "(camera) and **DSI/DSI-2** (display). For links that leave the box, "
      "or that must interoperate with any monitor or TV, **HDMI** and "
      "**DisplayPort** (plus its embedded variant **eDP**) rule. This "
      "chapter starts from the one concept they all share - video timing - "
      "then works up the MIPI stack and finishes with the consumer display "
      "links. Along the way we build and run a video timing generator, a "
      "CSI-2 packet-header ECC encoder/corrector and an HDMI TMDS encoder, "
      "each cross-checked against a Python model.")

    h2("Where display and camera links sit in an SoC")
    diagram([
        "  image sensor                                             panel / monitor",
        "  +---------+  CSI-2 over    +-------------+   +-------+   +----------+",
        "  | pixel   |  D-PHY/C-PHY   | CSI-2 RX    |   |       |   | display  |  DSI (D/C-PHY)",
        "  | array + |===============>| PHY + PPI + |-->|  ISP  |   | ctrl     |=========> phone",
        "  | CSI-2 TX|  2-4 lanes     | protocol    |   |       |   | (DPU)    |  eDP -> laptop",
        "  +---------+                +------+------+   +---+---+   +----+-----+  HDMI/DP ->",
        "       ^  I2C / I3C (CCI) control   |              |            |          TV/monitor",
        "       +----------------------------+          AXI to DDR  <----+ (frame buffers)",
        "  CSI-2 RX -> ISP -> DRAM -> GPU/NPU/encoder -> DRAM -> display controller -> PHY",
    ], "The camera-to-display data path of a typical application processor.")
    p("The camera side is **receive**: a CSI-2 receiver deserializes lanes, "
      "reassembles packets, checks ECC and CRC, and writes pixel lines "
      "either to an image signal processor (ISP) or straight to memory. "
      "The sensor itself is configured over a separate low-speed bus - I2C "
      "or I3C, called CCI (Camera Control Interface) in the MIPI documents "
      "(see Chapters 13 and 14). The display side is **transmit**: a display "
      "processing unit (DPU) fetches frame buffers over AXI, composes "
      "layers, and a timing engine feeds a DSI, eDP, HDMI or DP transmitter.")
    tbl(["Interface", "Owner body", "Typical use", "PHY", "Rough peak rate"],
        [["CSI-2", "MIPI", "Camera sensor -> SoC", "D-PHY, C-PHY, A-PHY",
          "Several Gb/s per lane or trio; 4 lanes/3 trios typical"],
         ["DSI / DSI-2", "MIPI", "SoC -> phone/tablet panel", "D-PHY, C-PHY",
          "Same PHYs as CSI-2"],
         ["eDP", "VESA", "SoC -> laptop panel", "DP main link + AUX",
          "Up to 4 lanes at HBR3 (8.1 Gb/s) in eDP 1.4/1.5"],
         ["DisplayPort", "VESA", "PC/monitor, USB-C Alt Mode", "Main link + AUX",
          "Up to 4 x 20 Gb/s (UHBR20) in DP 2.1"],
         ["HDMI", "HDMI Forum / LA", "TVs, set-top boxes, consoles",
          "TMDS or FRL", "18 Gb/s (2.0), 48 Gb/s (2.1)"],
         ["MIPI A-PHY", "MIPI", "Automotive camera/display, up to ~15 m",
          "Asymmetric SerDes", "Up to ~16 Gb/s downlink in v1.x"]],
        widths=[1.2, 1.1, 2.0, 1.4, 2.6], bold_first=True,
        caption="The display and camera interface landscape.")

    # ------------------------------------------------------------------
    h2("Video timing: the raster every link carries")
    p("Every display interface, whether it sends pixels as a continuous "
      "stream (HDMI TMDS, DSI video mode) or as packets (DisplayPort, CSI-2), "
      "is describing a **raster**: a frame is a set of lines, a line is a "
      "set of pixels, and between them there are **blanking intervals** "
      "inherited from CRT displays that needed time for the beam to fly "
      "back. The horizontal line is divided into **active** pixels, a "
      "**front porch**, a **sync pulse** and a **back porch**; the frame is "
      "divided the same way in lines. A **data-enable** (DE) signal is high "
      "only during active pixels.")
    diagram([
        '  one line, counted in pixel clocks (x = 0 at the first active pixel)',
        '              |<------- active -------->|<--HFP-->|<-- HSYNC -->|<--HBP-->|',
        '  DE           _________________________                                   ____',
        '            __|                         |_________________________________|',
        '  HSYNC_n   ______________________________________               __________',
        '                                                  |_____________| (active-low)',
        '              |<------------------------ H total ------------------------>|',
        '  x:          0                         HA        HA+HFP        +HS       HT',
        '  one frame: the same structure counted in lines (V active, VFP, VSYNC, VBP)',
    ], "Horizontal timing. The vertical axis has the same structure, counted in lines.")
    eq(["pixel clock = H_total x V_total x frame rate",
        "640x480@60 : 800 x 525 x 59.94 Hz  = 25.175 MHz",
        "1080p60    : 2200 x 1125 x 60 Hz    = 148.5 MHz",
        "2160p60    : 4400 x 2250 x 60 Hz    = 594 MHz"],
       "The pixel-clock equation; the totals include blanking.")
    tbl(["Mode", "H act/FP/sync/BP", "V act/FP/sync/BP", "Totals", "Pixel clock",
         "Sync pol."],
        [["640x480@60 (VGA)", "640/16/96/48", "480/10/2/33", "800 x 525",
          "25.175 MHz", "-/-"],
         ["1280x720@60 (CEA-861)", "1280/110/40/220", "720/5/5/20", "1650 x 750",
          "74.25 MHz", "+/+"],
         ["1920x1080@60 (CEA-861)", "1920/88/44/148", "1080/4/5/36", "2200 x 1125",
          "148.5 MHz", "+/+"],
         ["3840x2160@60 (CTA-861)", "3840/176/88/296", "2160/8/10/72", "4400 x 2250",
          "594 MHz", "+/+"]],
        widths=[1.9, 1.6, 1.4, 1.2, 1.1, 0.8], bold_first=True,
        caption="Common timings (VESA DMT / CTA-861). Reduced-blanking (CVT-RB) "
                "modes shrink the porches to save bandwidth on digital links.")
    p("The timing generator is the heartbeat of every display controller: "
      "two counters and a few comparators. Its outputs drive the pixel "
      "fetch pipeline and the transmitter. Here is a parameterized version "
      "set up for 640x480@60, with a testbench that counts two full frames "
      "and checks every number against the table.")
    _v("vtg", "A parameterized video timing generator (active region first).")
    _v("tb_vtg", "Testbench: count clocks, DE pixels, lines and sync pulses over two frames.")
    _o("vtg", "Icarus Verilog output: 800 x 525 clocks per frame, 307200 active pixels, "
              "525 HSYNC pulses and one VSYNC per frame, 96-clock HSYNC.")
    box("warn", "Pitfall: off-by-one porches and the wrong sync polarity",
        ["The two classic bring-up bugs are (1) counting porches from the "
         "wrong reference - e.g. placing sync immediately after active video "
         "and forgetting the front porch - which shifts the picture by a few "
         "pixels or makes a monitor reject the mode, and (2) wrong HSYNC/VSYNC "
         "polarity. VGA uses negative syncs, the CEA/CTA HD modes positive. "
         "Always self-check a timing generator by counting, exactly as the "
         "testbench above does, and compare with the EDID detailed timing "
         "descriptor the monitor reports."])
    box("expert", "Expert corner: the pixel clock is a PLL problem",
        ["25.175 MHz and 148.5 MHz (and the NTSC-derived 1000/1001 variants "
         "such as 148.35 MHz for 59.94 Hz) are not integer ratios of a "
         "typical 19.2 or 24 MHz reference. Display PLLs therefore use "
         "fractional-N synthesis, and a DPU usually has its own PLL per "
         "output so an external monitor and the internal panel can run "
         "unrelated rates. Packetized links (DP, CSI-2, DSI burst mode) "
         "decouple the link clock from the pixel clock with FIFOs, but the "
         "sink must still regenerate the pixel clock - DisplayPort sends "
         "M/N values for exactly that purpose."])

    # ------------------------------------------------------------------
    h2("MIPI D-PHY: the physical layer")
    p("D-PHY is a **source-synchronous** PHY: one **clock lane** plus one "
      "to four **data lanes** (implementations sometimes go beyond four), "
      "each a pair of wires. Its trick is that the same two wires operate in "
      "two completely different electrical modes:")
    bul(["**High-Speed (HS) mode**: low-swing differential signalling, about "
         "200 mV differential swing around a ~200 mV common mode (SLVS-400 "
         "style), terminated with 100 ohm differential at the receiver. "
         "Data is sent as bursts; the clock lane carries a **DDR clock** "
         "(clock frequency = bit rate / 2), so a 2.5 Gb/s lane uses a 1.25 GHz "
         "clock, which the transmitter places in quadrature (90 degrees) with "
         "the data.",
         "**Low-Power (LP) mode**: each wire is an independent, unterminated "
         "1.2 V LVCMOS-like single-ended signal. The pair's two bits form "
         "**line states** named LP-ab, e.g. LP-11 (both high) is the "
         "**Stop** state, LP-01 and LP-10 and LP-00 are used in sequences. "
         "LP mode signals at a few tens of Mb/s at most and costs almost no "
         "static power."])
    p("A lane rests in LP-11. To send an HS burst the transmitter walks a "
      "fixed sequence of LP states, turns on HS drivers, sends a known "
      "**sync** pattern (Start-of-Transmission, SoT), the payload, and a "
      "trailer (End-of-Transmission, EoT), then returns to LP-11.")
    diagram([
        '  phase      Stop    HS-Rqst  HS-Prepare   HS-Zero    SoT sync   payload     HS-Trail   Stop',
        '  line       LP-11   LP-01    LP-00        HS-0       00011101   bytes       ~last bit  LP-11',
        '  Dp / Dn    1.2/1.2 0/1.2    0/0          <---- HS differential, ~200 mV swing ---->  1.2/1.2',
        '  RX term.   off     off      turns on     on         on         on          on         off',
        '  timing     >TLPX   TLPX     THS-PREPARE  THS-ZERO   8 UI       8 UI/byte   THS-TRAIL THS-EXIT',
        '  (LP-ab: a = Dp, b = Dn.  The sync byte is 0xB8 sent LSB first.)',
    ], "D-PHY data-lane HS burst: LP-11 -> LP-01 -> LP-00 -> HS-0 -> sync -> data -> trail -> LP-11.")
    p("The receiver enables its termination during HS-Prepare, waits out "
      "HS-Zero (long enough for its HS receiver and deserializer to settle), "
      "and then hunts for the sync sequence `00011101` in bit-transmission "
      "order (the byte 0xB8 sent LSB first). That hunt gives it **byte "
      "alignment**: everything after the sync is a byte stream on that "
      "lane. At the end the transmitter holds the inverse of the last data "
      "bit for **HS-Trail**, then drives LP-11; the receiver discards the "
      "trailing bits it may have sampled after the true payload. The PPI "
      "(PHY-Protocol Interface) presents this to the controller as an 8- "
      "(or 16/32-) bit word per lane with `RxActiveHS`, `RxValidHS`, "
      "`RxSyncHS`-style signals, so the protocol layer never sees raw bits.")
    h3("Clock lane, escape mode and bus turnaround")
    bul(["**Clock lane**: continuous (always in HS) or **non-continuous** "
         "(enters LP between bursts to save power). A non-continuous clock "
         "has its own HS entry/exit sequence with parameters such as "
         "TCLK-PREPARE, TCLK-ZERO, TCLK-PRE (clock must run before data "
         "starts) and TCLK-POST (after data ends).",
         "**Escape mode**: an LP-mode signalling scheme entered by "
         "LP-11 -> LP-10 -> LP-00 -> LP-01 -> LP-00 followed by an 8-bit entry "
         "command sent as spaced-one-hot LP symbols. Commands select "
         "**Low-Power Data Transmission (LPDT)** - used by DSI to send "
         "commands to a panel without starting HS - **Ultra-Low Power State "
         "(ULPS)** or a remote **trigger** (e.g. a reset trigger).",
         "**ULPS**: the deepest lane state (LP-00 held). The PHY can switch "
         "off its PLL; waking takes a TWAKEUP of about a millisecond, so "
         "power management firmware must budget it.",
         "**Bus turnaround (BTA)**: DSI needs the panel to answer reads and "
         "acknowledgements, so data lane 0 is **bidirectional in LP mode**. "
         "A BTA sequence hands control of the lane to the other side. CSI-2 "
         "is unidirectional (sensor to SoC) and does not need it.",
         "**Deskew**: above 1.5 Gb/s (D-PHY v1.2 and later) the transmitter "
         "sends a periodic **deskew calibration** burst so the receiver can "
         "trim each lane's sampling point against the clock. Lane-to-lane "
         "skew is the D-PHY PHY team's number one closure item at high rates."])
    tbl(["D-PHY version", "Year (approx.)", "Max rate per lane", "Notable additions"],
        [["v1.0 / v1.1", "2009 / 2011", "1.0 / 1.5 Gb/s", "Base spec; the mobile workhorse"],
         ["v1.2", "2014", "2.5 Gb/s", "Deskew calibration"],
         ["v2.0 / v2.1", "2016 / 2017", "4.5 Gb/s", "Equalization, spread-spectrum "
          "clocking; 2.1 better channel/ESD models"],
         ["v2.5", "2019", "4.5 Gb/s", "Alternate Low Power (ALP): LP signalling "
          "replaced by HS-side signals for longer channels"],
         ["v3.0 / v3.5", "2021 / 2023", "around 9 Gb/s / around 11 Gb/s "
          "(check the release notes)", "Stronger TX/RX equalization, embedded "
          "clock options for longer reach"]],
        widths=[1.3, 1.2, 1.9, 3.4], bold_first=True,
        caption="D-PHY generations. Rates are the maximum; most products run far "
                "below them and a channel sets the real limit.")
    box("warn", "Pitfall: timing parameters in the wrong unit",
        ["D-PHY HS entry/exit parameters are specified as a mix of absolute "
         "nanoseconds and multiples of the unit interval UI (e.g. THS-PREPARE "
         "= 40 ns + 4 UI to 85 ns + 6 UI in v1.x). Driver code that programs "
         "them in byte-clock cycles must recompute them whenever the lane rate "
         "changes. A too-short HS-Zero or HS-Prepare typically shows up as "
         "occasional SoT sync errors - intermittent, rate dependent, and "
         "blamed on signal integrity for weeks."])

    # ------------------------------------------------------------------
    h2("MIPI C-PHY: three wires, three levels, embedded clock")
    p("C-PHY attacks two D-PHY limits: the dedicated clock lane (wires and "
      "skew) and the 1 bit per wire-pair efficiency. A C-PHY **lane** is a "
      "**trio** of three wires A, B, C. At every symbol each wire is driven "
      "to one of three levels (high, mid, low) with exactly one wire at "
      "each level, giving **six wire states** named +x, -x, +y, -y, +z, -z. "
      "The receiver uses three differential comparators (A-B, B-C, C-A).")
    diagram([
        "  wire state  A     B     C        receivers A-B  B-C  C-A",
        "     +x      high  low   mid                 +     -    ...",
        "     -x      low   high  mid       a symbol is the TRANSITION from the",
        "     +y      mid   high  low       current state to one of the 5 others:",
        "     -y      mid   low   high      3 bits = Flip, Rotation, Polarity",
        "     +z      low   mid   high      (the 'no change' case is illegal,",
        "     -z      high  mid   low        so every symbol carries a clock edge)",
        "",
        "  16-bit word -> mapper -> 7 symbols    (5^7 = 78125 >= 2^16 = 65536)",
        "  efficiency = 16 / 7 = 2.28 bits/symbol  (log2(5) = 2.32 is the ceiling)",
    ], "C-PHY states and symbol coding (level assignment shown schematically).")
    p("Because every symbol is a state change, the receiver recovers the "
      "clock from the data itself: **no clock lane, no lane-to-lane "
      "deskew**. The cost is analog complexity (three-level drivers, "
      "multi-comparator clock recovery) and a more intricate PCS: each "
      "burst starts with a preamble and a sync word, and the mapper "
      "converts 16-bit words into 7-symbol groups. Speeds are quoted in "
      "symbols per second: roughly 2.5 Gsym/s in v1.0, 3.5 Gsym/s in v1.2, "
      "and around 6 Gsym/s and beyond in the v2.x generation. At 2.28 "
      "bits/symbol, a 3-trio (9-wire) link at 6 Gsym/s carries about 41 Gb/s, "
      "where a 4-lane D-PHY needs 10 wires. Many SoCs ship a **combo PHY** "
      "that can be configured as D-PHY (4 data + clock = 10 wires) or C-PHY "
      "(3 trios = 9 wires) on the same pads.")
    box("key", "Key idea: D-PHY vs C-PHY in one sentence",
        ["D-PHY forwards a clock and sends 1 bit per pair per UI; C-PHY "
         "embeds the clock in guaranteed transitions and sends 16 bits per 7 "
         "symbols on each 3-wire trio - fewer wires, no skew budget, more "
         "analog complexity. The CSI-2/DSI protocol layers sit on either."])

    # ------------------------------------------------------------------
    h2("CSI-2: the camera protocol")
    p("CSI-2 is a layered protocol. From the bottom: the PHY; **lane "
      "management** (byte striping over lanes); the **low-level protocol** "
      "(packets, ECC, CRC); **pixel/byte packing**; and the application "
      "layer (frames, lines, virtual channels). Lane management is simple "
      "round-robin: byte 0 on lane 0, byte 1 on lane 1, and so on; the last "
      "bytes of a packet may leave some lanes idle, and each lane ends its "
      "burst independently (and the receiver merges them).")
    diagram([
        "  SHORT PACKET (4 bytes)                    LONG PACKET (6 + WC bytes)",
        "  +--------+--------+--------+-------+      +--------+-------+-------+-------+--//--+-------+",
        "  | DataID | Data field 16 b | ECC   |      | DataID | WC lo | WC hi | ECC   | data | CRC16 |",
        "  +--------+--------+--------+-------+      +--------+-------+-------+-------+--//--+-------+",
        "     DI byte = [7:6] VC  [5:0] DT          |<------ packet header (PH) ---->|      | footer|",
        "  frame/line number in the data field      WC = payload byte count; CRC over payload only",
        "",
        "  one frame:   FS | LS  line0  LE | LS  line1  LE | ...  | LS  lineN  LE | FE",
        "               (FS/FE/LS/LE are short packets; LS/LE are optional)",
        "  LP-11 between packets is allowed; each packet is typically one HS burst",
    ], "CSI-2 packet formats (D-PHY) and frame structure.")
    p("Every packet begins with a 32-bit **packet header**. The Data "
      "Identifier byte carries a **virtual channel** (VC) number in its two "
      "top bits and a 6-bit **data type** (DT). For short packets, the next "
      "16 bits are data (for Frame Start/End the frame number, for Line "
      "Start/End the line number); for long packets they are the **word "
      "count** (WC), the payload length in bytes. The fourth byte is an "
      "**ECC** that protects the 24 header bits. Long packets carry a "
      "**CRC-16** footer over the payload.")
    tbl(["Data type (hex)", "Meaning", "Notes"],
        [["0x00 / 0x01", "Frame Start / Frame End (short)", "Data field = frame number"],
         ["0x02 / 0x03", "Line Start / Line End (short)", "Optional; data = line number"],
         ["0x08 - 0x0F", "Generic short packets", "Application specific (e.g. shutter sync)"],
         ["0x10 / 0x11 / 0x12", "Null / blanking / embedded 8-bit non-image data",
          "Embedded data = sensor register dump per frame"],
         ["0x18 - 0x1F", "YUV formats", "0x1E = YUV422 8-bit, 0x18 = YUV420 8-bit"],
         ["0x20 - 0x24", "RGB formats", "0x22 = RGB565, 0x24 = RGB888"],
         ["0x28 - 0x2F", "RAW formats", "0x2A = RAW8, 0x2B = RAW10, 0x2C = RAW12, "
          "0x2D = RAW14, 0x2E = RAW16, 0x2F = RAW20"],
         ["0x30 - 0x37", "User-defined 8-bit data", "e.g. JPEG or metadata"]],
        widths=[1.4, 2.6, 3.4], bold_first=True,
        caption="Selected CSI-2 data types.")
    p("Pixel packing is part of the spec. **RAW10** packs 4 pixels into 5 "
      "bytes: the first four bytes hold bits [9:2] of pixels 0..3, the fifth "
      "holds their 2 LSBs. A 3840-pixel RAW10 line is therefore 4800 bytes "
      "(WC = 4800). **RAW12** packs 2 pixels into 3 bytes. The receiver's "
      "unpacker (bytes -> pixels, often into 16-bit containers in memory) is "
      "a classic RTL block and a classic source of bugs when the line length "
      "is not a multiple of the packing group.")
    h3("Virtual channels")
    p("With 2 VC bits a single link carries up to 4 independent streams - "
      "e.g. long and short HDR exposures, or embedded data and image. CSI-2 "
      "v2.0 added **VC extension** bits (on D-PHY stored in the top two ECC "
      "bits, which were previously reserved zeros) for 16 channels, and more "
      "on C-PHY, which is how aggregator/serializer chips funnel several "
      "sensors into one SoC port. The receiver demultiplexes on (VC, DT) "
      "into separate DMA contexts.")
    h3("The packet-header ECC")
    p("The header ECC is a (30,24) Hamming-style code with 6 parity bits "
      "(P0..P5; P6 and P7 are zero or, from v2.0, carry VC extension). Each "
      "parity bit is the XOR of a fixed subset of the 24 header bits. The "
      "24 columns of the parity-check matrix are distinct and all have odd "
      "weight (3 or 5), so the code is **SEC-DED**: a single bit error in "
      "the 24 data bits produces a syndrome equal to that bit's column and "
      "is corrected, a single error in a parity bit produces a weight-1 "
      "syndrome, and any double error produces a non-zero even-weight "
      "syndrome that matches no column - detected, not corrected. The "
      "spec's worked example is DI = 0x37, WC = 0x01F0 -> ECC = 0x3F.")
    _v("ecc", "Header ECC function and a receive-side single-error corrector / "
              "double-error detector.")
    _v("py_ecc", "Python reference: the parity-bit subsets, a check that all columns are "
                 "unique, and 1000 random golden vectors written for the testbench.")
    _v("tb_ecc", "Testbench: encoder vs Python, then 1000 single- and 1000 double-bit "
                 "error injections.")
    _o("ecc", "Icarus Verilog output: the spec example matches (0x3F), the encoder agrees "
              "with Python on all 1000 headers, all single errors are corrected and all "
              "double errors flagged.")
    h3("The payload CRC")
    p("The long-packet footer is a CRC-16 with generator "
      "x^{16} + x^{12} + x^{5} + 1 (the CCITT polynomial), seeded with "
      "0xFFFF, processed LSB-first (so in software it is the reflected "
      "polynomial 0x8408) with no final inversion. The spec includes a "
      "24-byte worked example, which our Python reference reproduces; the "
      "RTL implementation is the parallel CRC of Chapter 3, usually 8, 16 or "
      "32 bits per clock to match the PPI width times lanes.")
    _v("py_crc", "Python reference for the CSI-2 payload CRC.")
    _o("crc", "Python output: 0x00F0 matches the worked example; a changed byte gives a "
              "completely different CRC.")
    box("warn", "Pitfall: ECC is not optional on the receive side",
        ["A receiver that only checks ECC for errors but does not correct "
         "silently drops packets on a single-bit error; worse, one that "
         "ignores it trusts a corrupted WC and then consumes the next packet's "
         "header as payload - a whole frame lost from one flipped bit. Correct "
         "single errors, drop the packet on double errors, count both in "
         "status registers, and resynchronise at the next SoT. The CRC error, "
         "by contrast, is normally reported but the line is still delivered, "
         "because dropping a line would shift the whole image."])

    # ------------------------------------------------------------------
    h2("Bandwidth math: a 4K60 camera over CSI-2")
    p("Sizing the link is the first architecture question for any camera "
      "port. The steps are: active pixel payload, then add horizontal and "
      "vertical blanking (sensors need line time for readout; typically 5-20% "
      "overhead), packet overhead (6 bytes per line for header and footer - "
      "negligible), LP transitions between packets if the transmitter uses "
      "them, and margin. Then divide by lanes.")
    _v("py_bw", "Python: link sizing for 3840 x 2160 at 60 fps.")
    _o("bw", "Python output. 20% covers blanking, SoT/EoT and margin.")
    p("A 4K60 RAW10 sensor needs about 6 Gb/s of link, i.e. about 1.5 Gb/s "
      "per lane on 4 D-PHY lanes - comfortably inside D-PHY v1.2 (2.5 Gb/s "
      "per lane) - or 3 Gb/s per lane on 2 lanes, which needs v1.2 at "
      "full rate with deskew. On C-PHY, three trios at under 1 Gsym/s "
      "suffice. The same arithmetic flags HDR: a sensor sending two "
      "exposures per frame on two VCs doubles the load. And the receiver "
      "side must be sized too: 6 Gb/s is 750 MB/s of DRAM write bandwidth "
      "per camera, which the NoC and DDR controller (Chapter 20) have to "
      "absorb alongside everything else.")
    box("tip", "Practical tip: size the receiver's line buffer for the worst burst",
        ["The CSI-2 receiver writes to memory through AXI whose latency can "
         "spike when the DDR is busy, while the sensor cannot be paused. The "
         "receive FIFO must absorb the longest AXI stall at the full link "
         "rate: at 750 MB/s a 10 us stall is 7.5 KB. Size it from measured "
         "worst-case interconnect latency with QoS enabled, and give the "
         "camera path real-time QoS priority - overflow here means corrupt "
         "frames, not just slow ones."])

    # ------------------------------------------------------------------
    h2("DSI and DSI-2: driving a panel")
    p("The Display Serial Interface reuses the D-PHY (DSI) or C-PHY/D-PHY "
      "(DSI-2) and a packet format nearly identical to CSI-2 (same header, "
      "ECC and CRC), but in the other direction and with a command set for "
      "the panel. Its central choice is the **operating mode**:")
    tbl(["", "Video mode", "Command mode"],
        [["Panel has frame memory?", "No (or minimal)", "Yes (a GRAM in the driver IC)"],
         ["Host sends", "A continuous raster: sync events/pulses, blanking "
          "and pixel packets every frame", "Only updated regions, via DCS "
          "`write_memory_start` / `write_memory_continue`"],
         ["Timing master", "Host (like HDMI)", "Panel; it reports its scan "
          "position through a tearing-effect (TE) signal or DSI packet"],
         ["Power", "Link active every frame", "Link idle (ULPS) while the "
          "picture is static"],
         ["Typical", "Large/high-refresh panels", "Smart watches, small or "
          "always-on displays"]],
        widths=[1.6, 3.0, 3.0], bold_first=True,
        caption="DSI video mode vs command mode.")
    p("Video mode has three sub-flavours: **non-burst with sync pulses** "
      "(sync start and end packets mirror HSYNC/VSYNC edges exactly), "
      "**non-burst with sync events** (only sync-start packets), and "
      "**burst mode**, where pixel data is sent at a higher link rate than "
      "needed and the lanes drop to LP during the saved time. Command "
      "mode relies on the **Display Command Set (DCS)**, a standard "
      "command vocabulary: `exit_sleep_mode` (0x11), `set_display_on` "
      "(0x29), `set_column_address` (0x2A), `set_page_address` (0x2B), "
      "`write_memory_start` (0x2C), `set_tear_on` (0x35), "
      "`set_pixel_format` (0x3A). They travel in DCS short-write (DT 0x05 "
      "or 0x15 with one parameter), DCS long-write (0x39) or DCS read (0x06) "
      "packets; reads use a bus turnaround so the panel can answer on lane "
      "0 in LP mode. Panel initialisation sequences are long lists of such "
      "commands, often sent in LPDT before HS video starts.")
    box("warn", "Pitfall: tearing in command mode",
        ["If the host writes the panel's frame memory while the panel is "
         "scanning the same region, the user sees a tear line. The fix is to "
         "synchronise updates to the TE signal (start writing just after the "
         "panel's scan passes the top line and write faster than it scans). "
         "Forgetting to enable TE (`set_tear_on`) or mis-routing the TE GPIO "
         "is one of the most common display bring-up bugs."])
    p("High-resolution panels increasingly compress the stream with VESA "
      "**Display Stream Compression (DSC)** - visually lossless at around "
      "3:1 - which DSI carries in its own packet type. The DSC encoder sits "
      "in the DPU just before the DSI controller.")

    # ------------------------------------------------------------------
    h2("HDMI: TMDS, FRL and HDCP")
    p("HDMI grew out of DVI and keeps DVI's **TMDS** (Transition-Minimized "
      "Differential Signalling) link: three data channels (blue, green, red) "
      "plus a clock channel at the character rate. Each channel sends one "
      "10-bit character per pixel clock (for 8-bit colour), so at 1080p60 "
      "each channel runs at 1.485 Gb/s. The link is DC-coupled current-mode "
      "logic pulled up to 3.3 V at the sink. Three kinds of period "
      "alternate on the wire:")
    bul(["**Video data period**: pixels, each byte TMDS-encoded 8b -> 10b.",
         "**Control period**: during blanking, 2 bits per channel (HSYNC and "
         "VSYNC on channel 0) sent as four special high-transition 10-bit "
         "characters that the receiver uses for character alignment.",
         "**Data island period** (HDMI addition): audio samples and "
         "InfoFrames (AVI, audio, vendor-specific) in packets using **TERC4** "
         "(4 bits -> 10) with BCH error correction, bracketed by guard bands."])
    h3("TMDS 8b/10b encoding")
    p("TMDS 8b/10b is **not** the IBM 8b/10b of PCIe/USB (Chapter 2). It "
      "works in two stages. Stage 1 **minimises transitions**: it builds 8 "
      "bits by chaining XOR (or XNOR, chosen when the byte has many ones) of "
      "each data bit with the previous encoded bit, and records the choice "
      "in bit 8. Stage 2 **balances DC**: it keeps a running disparity "
      "counter and, if the new word would push the line further from "
      "balance, inverts bits [7:0] and sets bit 9. The receiver undoes both "
      "from bits 9 and 8. The four control characters have many "
      "transitions, so they cannot be confused with data and give the "
      "receiver an alignment reference.")
    _v("tmds", "A TMDS encoder following the DVI 1.0 / HDMI algorithm.")
    _v("py_tmds", "Python reference model of the same algorithm; it generates 6024 golden "
                  "input/output pairs (random bytes, long runs of 0x00 and 0xFF, and every "
                  "byte value).")
    _v("tb_tmds", "Testbench: compare every symbol against Python and measure the line's "
                  "running disparity bit by bit.")
    _o("tmds", "Icarus Verilog output: bit-exact against Python, and the running disparity "
               "of the serial stream stays within +/-10 and returns to 0 - DC balanced.")
    p("Note what TMDS does **not** guarantee: the longest run of equal bits "
      "(13 here) is much longer than IBM 8b/10b's 5, because stage 1 "
      "minimises transitions on purpose (fewer transitions = less EMI on a "
      "cable). The receiver's clock comes from the forwarded clock channel, "
      "so it does not need data transitions for CDR - a key difference from "
      "embedded-clock SerDes.")
    h3("HDMI versions, FRL and the side channels")
    tbl(["Version", "Signalling", "Max rate", "Highlights"],
        [["1.4", "TMDS", "340 MHz TMDS clock, 10.2 Gb/s total",
          "4K30, ARC, HDMI Ethernet channel"],
         ["2.0", "TMDS + scrambling", "600 Mchar/s, 18 Gb/s total",
          "4K60; clock channel at 1/40 of the character rate above 340 MHz; "
          "SCDC registers"],
         ["2.1", "FRL (Fixed Rate Link)", "Up to 4 lanes x 12 Gb/s = 48 Gb/s",
          "3 or 4 lanes at 3/6/8/10/12 Gb/s, 16b/18b coding, RS FEC, the "
          "clock channel becomes a 4th data lane; 4K120, 8K60 (with DSC)"],
         ["2.2", "FRL", "Up to 96 Gb/s (announced 2025)", "Higher-bandwidth cables"]],
        widths=[0.8, 1.6, 2.4, 3.6], bold_first=True, caption="HDMI generations.")
    p("Besides the fast lanes the connector carries: **DDC**, an I2C bus "
      "(100 kHz) used to read the sink's **EDID** at address 0x50 and, from "
      "HDMI 2.0, the **SCDC** status/control registers at 0x54; **HPD** "
      "(hot-plug detect); **+5 V**; and **CEC**, a slow single-wire bus for "
      "remote-control commands. **HDCP** encrypts the content: HDCP 1.4 "
      "uses a legacy 56-bit key scheme, HDCP 2.2/2.3 uses RSA-based "
      "authentication, a locality check (round-trip time) and AES-128 in "
      "counter mode. HDCP keys live in secure storage (OTP/secure enclave) "
      "and the cipher sits between the DPU and the TMDS/FRL encoder "
      "(Chapter 26 covers link encryption more broadly).")

    # ------------------------------------------------------------------
    h2("DisplayPort and eDP")
    p("DisplayPort was designed as a **packetized** link from the start. "
      "The **main link** has 1, 2 or 4 AC-coupled differential lanes with "
      "an **embedded clock** (no clock lane). Pixel data, audio and "
      "secondary packets are mapped into **transfer units (TUs)** and "
      "striped across lanes; the source also sends **M/N** values from which "
      "the sink regenerates the pixel clock from the link clock. Beside "
      "the main link run the **AUX channel** and **HPD**.")
    tbl(["Link rate", "Per-lane rate", "Coding", "4-lane payload", "Spec"],
        [["RBR", "1.62 Gb/s", "8b/10b", "5.18 Gb/s", "DP 1.0"],
         ["HBR", "2.7 Gb/s", "8b/10b", "8.64 Gb/s", "DP 1.0/1.1"],
         ["HBR2", "5.4 Gb/s", "8b/10b", "17.28 Gb/s", "DP 1.2"],
         ["HBR3", "8.1 Gb/s", "8b/10b", "25.92 Gb/s", "DP 1.3/1.4"],
         ["UHBR10 / 13.5 / 20", "10 / 13.5 / 20 Gb/s", "128b/132b",
          "about 38.7 / 52.4 / 77.6 Gb/s", "DP 2.0/2.1"]],
        widths=[1.6, 1.5, 1.1, 2.2, 1.2], bold_first=True,
        caption="DisplayPort link rates (payload excludes coding overhead only).")
    bul(["**AUX channel**: a half-duplex, AC-coupled differential pair at "
         "about 1 Mb/s using Manchester-II coding. The source is the "
         "master; it reads/writes the sink's **DPCD** register space "
         "(capabilities, link status, training requests) with native AUX "
         "transactions and tunnels I2C (for EDID and MCCS) through "
         "I2C-over-AUX. Its 20-bit address and burst-of-16-bytes limit are "
         "familiar to anyone who has written a DP driver.",
         "**Link training**: the source cannot know the channel, so it "
         "negotiates. Phase 1, **clock recovery**, sends training pattern "
         "TPS1 (a D10.2 clock-like pattern) while the sink reports lock per "
         "lane and requests voltage-swing and pre-emphasis levels through "
         "DPCD. Phase 2, **channel equalization**, sends TPS2/TPS3/TPS4 "
         "(TPS4 is scrambled, required at HBR3) until symbol lock, "
         "inter-lane alignment and EQ are done. On failure the source "
         "lowers the link rate or lane count and retries. UHBR (128b/132b) "
         "has its own LANEx_EQ / CDS sequence.",
         "**MST (Multi-Stream Transport)**, DP 1.2: the link is divided into "
         "a Multi-Stream Transport Packet of 64 time slots; each stream gets "
         "slots, and branch devices (hubs, daisy-chained monitors) route "
         "them. A sideband message protocol over AUX discovers the topology.",
         "**eDP (embedded DP)**: the laptop panel variant. It drops "
         "hot-plug assumptions and adds power features: **Panel Self Refresh "
         "(PSR/PSR2)** - the panel keeps a copy of the frame and the source "
         "shuts down the main link while the image is static - "
         "**ALPM** and fast link training shortcuts, plus backlight control "
         "through DPCD.",
         "**DSC**: DP 1.4 and later carry VESA DSC-compressed streams, "
         "which is how 8K60 or 4K240 fit through HBR3. **USB-C Alt Mode** "
         "carries DP main-link lanes over the USB-C high-speed pairs "
         "(Chapter 17), and USB4 tunnels DP packets."])
    diagram([
        "  source                           AUX (native / I2C-over-AUX)            sink",
        "  1. HPD rises  <-------------------------------------------------------- HPD",
        "  2. read DPCD caps (max rate, lanes)  -------------------------------->",
        "  3. write LINK_BW_SET, LANE_COUNT_SET, TRAINING_PATTERN_SET = TPS1 ---->",
        "     main link: TPS1 on all lanes  ==================================>  CDR locks?",
        "  4. poll LANE_STATUS (CR_DONE)  <---------------------------------  adjust request",
        "     apply requested swing / pre-emphasis, repeat until CR_DONE or give up",
        "  5. TPS2/3/4 ==========================>  poll EQ_DONE, SYMBOL_LOCKED, ALIGNED",
        "  6. TRAINING_PATTERN_SET = 0 ; start video  (on failure: lower rate/lanes, retry)",
    ], "DisplayPort 8b/10b link training in outline.")
    box("expert", "Expert corner: who owns the display link",
        ["The **PHY/analog team** owns the SerDes, swing/pre-emphasis tables "
         "and the AUX transceiver. The **RTL team** owns the timing engine, "
         "the DP/HDMI link layer (TU packing, secondary-data packets, "
         "scrambler, encoder), the CSI-2/DSI protocol cores and the DSC codec. "
         "**Firmware/driver** owns link training, EDID/DPCD parsing, mode "
         "selection, HDCP and PSR policy - link training is software on "
         "almost every SoC. **DV** buys VIP for DP/HDMI/CSI-2/DSI "
         "(Chapter 25) because the protocols are large and compliance "
         "(VESA CTS, HDMI CTS, MIPI conformance) is gated on those corner "
         "cases, and runs pixel-accurate end-to-end tests comparing captured "
         "frames with a reference model."])

    # ------------------------------------------------------------------
    h2("Integration and verification checklist")
    checklist("Display / camera port bring-up checklist", [
        "Link budget computed for the worst mode (resolution x fps x bpp + "
        "blanking + margin) and the matching DRAM bandwidth reserved with "
        "real-time QoS.",
        "D-PHY/C-PHY timing parameters recomputed per lane rate; deskew "
        "enabled above 1.5 Gb/s; lane swap/polarity-swap muxes match the board.",
        "CSI-2 receiver corrects single-bit header errors, drops on double, "
        "counts CRC errors, and recovers at the next Frame Start after any "
        "error (test by injection).",
        "Unpacker verified for line lengths that are not multiples of the "
        "packing group (RAW10: 4 pixels, RAW12: 2 pixels).",
        "Timing generator self-checked by counting; sync polarities match EDID.",
        "TMDS/8b10b/128b132b encoders compared bit-exactly with a reference "
        "model; DC balance measured.",
        "DSI: TE signal wired and enabled; panel init sequence sent in the "
        "correct mode (LP vs HS); BTA tested for reads.",
        "DP: link training retried at lower rates; HPD IRQ pulses (short "
        "pulses signalling sink events) handled separately from unplug.",
        "HDCP keys provisioned securely; HDCP failure does not hang the "
        "pipeline (the sink sees blank/snow content instead).",
    ])

    h2("Summary")
    bul(["Every display link carries a **raster**: active pixels plus front "
         "porch, sync and back porch in both directions; pixel clock = "
         "H_total x V_total x fps. A timing generator is two counters and "
         "comparators - verify it by counting.",
         "**D-PHY** switches each lane between low-swing HS differential bursts "
         "and 1.2 V LP single-ended states; HS bursts start LP-11 -> LP-01 -> "
         "LP-00 -> HS-zero -> sync 0xB8 and end with HS-trail. Escape mode, "
         "ULPS and BTA use LP signalling.",
         "**C-PHY** uses 3-wire trios, six wire states and state transitions as "
         "symbols: 16 bits per 7 symbols (2.28 bits/symbol) with an embedded "
         "clock.",
         "**CSI-2** sends short packets (FS/FE/LS/LE) and long packets "
         "(DI + WC + ECC header, payload, CRC-16 footer); VC/DT in the DI byte; "
         "the header ECC is SEC-DED, the payload CRC is CCITT x^{16}+x^{12}+x^{5}+1 "
         "seeded 0xFFFF.",
         "A 4K60 RAW10 camera needs about 5 Gb/s of payload, about 1.5 Gb/s per "
         "lane on a 4-lane D-PHY with margin.",
         "**DSI** is CSI-2's sibling towards the panel: video mode streams a "
         "raster; command mode writes a panel frame buffer with DCS commands "
         "and synchronises with TE.",
         "**HDMI** uses TMDS (8b/10b transition-minimised, DC-balanced) up to "
         "18 Gb/s and FRL (16b/18b, FEC) up to 48 Gb/s, with DDC/EDID, SCDC, "
         "CEC, HPD and HDCP around it.",
         "**DisplayPort** is packetized with an embedded clock, AUX-based "
         "training, MST, eDP power features and DSC; UHBR rates use 128b/132b."])

    h2("Exercises")
    bul(["Compute the pixel clock for 2560x1440@144 with CVT reduced blanking "
         "v2 (H blank 80 pixels, V blank at least 460 us). How many HDMI 2.0 "
         "TMDS channels' worth of bandwidth is that at 8 bits per colour?",
         "Extend the timing generator with programmable registers (APB) and "
         "a double-buffered update that only takes effect at the start of "
         "vertical blanking. Why is the double-buffering necessary?",
         "Using the ECC function, show by exhaustive simulation that every "
         "double-bit error in the 30-bit code word is detected. What happens "
         "with a triple-bit error? Explain from the column weights.",
         "Write the RAW10 unpacker (5 bytes in, 4 x 10-bit pixels out) for a "
         "32-bit PPI word stream, and test it with line lengths of 3840, 3842 "
         "and 3844 pixels.",
         "A 12-bit HDR sensor sends two exposures of 4000x3000 at 30 fps on two "
         "virtual channels. Size a 4-lane D-PHY link and the DRAM write "
         "bandwidth, and choose the minimum D-PHY version.",
         "Modify the TMDS testbench to count the maximum |cnt| reached by the "
         "encoder's internal disparity counter. Is a 5-bit signed counter "
         "sufficient? Prove it."], ordered=True)


# ---------------------------------------------------------------- Ch 22 ---
def _ch22():
    chapter("Chip-to-Chip and Die-to-Die: SerDes Links, JESD204B/C, Aurora, "
            "Interlaken, UCIe and BoW")
    p("PCIe, Ethernet and USB (Chapters 17-19) are general-purpose, "
      "standardised and heavy: they bring enumeration, configuration "
      "space, transaction layers and big compliance suites. Many links in a "
      "system do not want any of that. An RF transceiver needs to stream "
      "ADC samples into an FPGA with **known latency**; two FPGAs need a "
      "lightweight pipe; a network processor needs a packet interface to a "
      "traffic manager with **per-channel flow control**; and a modern "
      "processor made of **chiplets** needs die-to-die links with the "
      "bandwidth of on-chip wires and the energy of a few tenths of a "
      "picojoule per bit. This chapter covers those links, from the common "
      "SerDes and PCS building blocks, through JESD204, Aurora and "
      "Interlaken, to UCIe, BoW and the advanced packages that make "
      "chiplets possible. The run example is the heart of most modern "
      "PCS layers: a 64b/66b encoder with the self-synchronous scrambler "
      "x^{58} + x^{39} + 1 and a block-lock state machine.")

    h2("The SerDes link, reviewed")
    p("Chapter 2 introduced SerDes; here is the block diagram a link "
      "designer keeps in mind, split the way responsibilities are split in "
      "an SoC team. The **PMA** (physical medium attachment) is analog/mixed "
      "signal and belongs to the PHY team; the **PCS** (physical coding "
      "sublayer) is digital RTL; above it the protocol-specific link layer.")
    diagram([
        "  TX  parallel data (e.g. 64b @ 390.625 MHz)                         RX",
        "  +-----------+  +-----------+  +--------+  +---------+     +------+  +-----+  +--------+",
        "  | link layer|->| PCS: enc. |->|gearbox |->| PMA: SER|~~~~>| CTLE |->| CDR |->|  DES   |",
        "  | framing,  |  | scramble, |  |66->64/ |  | FFE     | ch. | +DFE |  | +PLL|  |        |",
        "  | CRC, flow |  | lane dist.|  | 32 bit |  | driver  |     +------+  +-----+  +---+----+",
        "  +-----------+  +-----------+  +--------+  +----+----+                           |",
        "                                                 ^ TX PLL (ref clock)            v",
        "  +-----------+  +--------------------------------------------+    +--------------+",
        "  | link layer|<-| PCS: block lock, descramble, decode, deskew, |<---| gearbox 32->66|",
        "  |           |  | elastic buffer (clock compensation)          |    +--------------+",
        "  +-----------+  +--------------------------------------------+",
    ], "A SerDes link split into link layer, PCS and PMA.")
    bul(["**TX equalization (FFE)** pre-distorts the signal (pre/post-cursor "
         "taps); **RX CTLE** boosts high frequencies; **DFE** cancels "
         "post-cursor ISI using past decisions.",
         "**CDR** recovers a sampling clock from data transitions - so the "
         "line code must guarantee transitions (8b/10b, scrambling).",
         "The **gearbox** adapts a 66-bit (or 67-bit) block to the PMA's "
         "32/40/64-bit parallel width: 33 PMA words carry 32 blocks of 66 "
         "bits, so the PCS must stall one cycle in 33.",
         "The **elastic buffer** absorbs the ppm difference between the "
         "transmitter's and receiver's reference clocks by inserting or "
         "deleting idle/skip symbols - unless the system distributes a common "
         "reference clock, as JESD204 subclass 1 and many die-to-die links do.",
         "**Lane deskew**: multi-lane links send alignment markers (8b/10b "
         "/A/ or ||A|| characters, 64b/66b alignment blocks, Interlaken "
         "metaframe sync words) so the receiver can line lanes up again."])

    h2("A protocol-agnostic PCS")
    p("FPGA transceivers and many ASIC SerDes IPs expose a **raw** or "
      "**protocol-agnostic PCS**: configurable encoders, scramblers, "
      "comma/block aligners and elastic buffers from which several protocols "
      "can be assembled. The main choices are summarized below.")
    tbl(["Line code", "Overhead", "DC balance / transitions", "Alignment", "Used by"],
        [["8b/10b", "25%", "Guaranteed: disparity control, max run 5",
          "Comma K28.5", "PCIe 1-2, USB 3.0, SATA, JESD204B, Aurora 8B/10B, DP 1.x"],
         ["64b/66b", "3.125%", "Statistical: scrambler x^58+x^39+1",
          "2-bit sync header", "10/25/40/100G Ethernet, JESD204C, Aurora 64B/66B"],
         ["64b/67b", "4.7%", "Scrambler + inversion bit bounds disparity",
          "2-bit sync + metaframe", "Interlaken"],
         ["128b/130b / 128b/132b", "1.5% / 3%", "Scrambler", "Sync header + "
          "ordered sets", "PCIe 3-5, USB 3.2 (128b/132b), DP 2.x"],
         ["PAM4 + FEC flits", "FEC-dependent", "Scrambler, Gray coding",
          "Flit/FEC framing", "PCIe 6/7, 200G/400G Ethernet, JESD204D"]],
        widths=[1.3, 0.8, 2.2, 1.4, 2.4], bold_first=True,
        caption="Line codes available in a typical configurable PCS.")

    # ------------------------------------------------------------------
    h2("64b/66b in depth: blocks, scrambler and block lock")
    p("A 64b/66b **block** is a 2-bit **sync header** followed by a 64-bit "
      "payload. Sync header `01` (in transmission order) marks a **data "
      "block** - all 8 bytes are data; `10` marks a **control block** whose "
      "first payload byte is a **block type** field (in 802.3 Clause 49 "
      "e.g. 0x1E = all idle/control characters, 0x78 = start of packet in "
      "lane 0, 0x87..0xFF = terminate variants). `00` and `11` are illegal, "
      "and that is the key to alignment: at the correct boundary every "
      "block has a sync header with exactly one transition.")
    diagram([
        "   bit 0 first on the wire",
        "   +----+-----------------------------------------------------------------+",
        "   | 01 |  D0  D1  D2  D3  D4  D5  D6  D7        (data block)              |",
        "   +----+-----------------------------------------------------------------+",
        "   | 10 | type |  56 bits of control codes / data  (control block)          |",
        "   +----+-----------------------------------------------------------------+",
        "   sync  <------------ 64-bit payload, SCRAMBLED ------------------------->",
        "  header",
        "  (not scrambled: it must stay a guaranteed 0->1 or 1->0 transition)",
    ], "The 64b/66b block.")
    p("The payload is scrambled with the **self-synchronous** scrambler "
      "G(x) = 1 + x^{39} + x^{58}: each transmitted bit is the data bit XOR "
      "the line bits sent 39 and 58 bit-times earlier. The descrambler "
      "applies the same XOR using **received** line bits, so after 58 bits it "
      "is automatically in step with the transmitter - no seed exchange, no "
      "reset alignment. The price is **error multiplication**: one line-bit "
      "error corrupts the output three times (at the bit itself and 39 and 58 "
      "bits later), which CRCs such as Ethernet's CRC-32 are designed to "
      "tolerate.")
    diagram([
        "  TX scrambler                               RX descrambler",
        "  d --->(+)------------+---> line            line ---+-------------->(+)---> d",
        "         ^             |                             |                ^",
        "         |      +------v------------------+          |  +-------------+--------+",
        "         +------| S0 S1 ... S38 ... S57   |          +->| S0 S1 ... S38 ... S57|",
        "        S38^S57 +-------------------------+             +----------------------+",
        "  out = d ^ S38 ^ S57, shift in OUT            out = line ^ S38 ^ S57, shift in LINE",
    ], "Self-synchronous scrambler and descrambler (S0 = most recent line bit).")
    p("The receiver finds block boundaries with the **block lock** state "
      "machine of IEEE 802.3 Clause 49 (JESD204C, Aurora 64B/66B and others "
      "use the same idea). It tests the two bits at the candidate boundary "
      "of each 66-bit window. While unlocked, an invalid header causes a "
      "**slip** - the boundary moves by one bit - and the valid-header count "
      "restarts; 64 consecutive valid headers declare lock. While locked, "
      "the machine counts headers in windows of 64 and drops lock (and "
      "slips) if 16 of them are invalid, which tolerates the occasional "
      "bit error but reacts quickly to a real loss of alignment.")
    diagram([
        "              +------------------+   sh invalid: SLIP (move 1 bit), sh_cnt=0",
        "   reset ---->|    UNLOCKED      |<------------------------------+",
        "              | test each 66 bits|--+ sh valid: sh_cnt++          |",
        "              +--------+---------+  | (loop)                      |",
        "                       | sh_cnt == 64 valid in a row             |",
        "                       v                                         |",
        "              +------------------+  16 invalid within a window   |",
        "              |     LOCKED       |-------------------------------+",
        "              | windows of 64    |  else: at 64 headers reset both counters",
        "              +------------------+",
    ], "Block-lock state machine (simplified from IEEE 802.3 Clause 49).")
    p("The RTL below implements the scrambler (parameterised to be the "
      "descrambler as well) and a serial-input block-lock unit. Real designs "
      "work on 32- or 64-bit words from the PMA with a barrel-shifter "
      "gearbox, but the one-bit-per-clock version shows the algorithm "
      "plainly.")
    _v("pcs", "64b/66b PCS pieces: a 64-bit-parallel self-synchronous scrambler/descrambler "
              "and a block-lock state machine.")
    _v("py_scr", "Python reference: the same scrambler, bit by bit, producing golden "
                 "scrambled payloads.")
    p("The testbench scrambles 700 blocks (every 16th a control block) and "
      "compares each against Python, prepends 37 junk bits so the receiver "
      "starts at an unknown offset, corrupts the sync headers of blocks "
      "250-289 to force loss of lock, flips one payload bit of block 640, "
      "and checks every descrambled payload while locked.")
    _v("tb_pcs", "Testbench: TX vs Python, then serial RX with offset, a header-error burst "
                 "and a single line-bit error.")
    _o("pcs", "Icarus Verilog output.")
    p("Read the output carefully, because every number is explainable:")
    bul(["The TX scrambler matches Python on all 700 blocks.",
         "Lock is found after exactly **37 slips** - the 37-bit junk prefix. "
         "It took about 8900 bits because each slip requires an invalid "
         "header to be observed, and a wrong boundary in scrambled data "
         "still shows a 'valid' header half the time.",
         "The 40 corrupted headers produce lock loss (one more slip). The "
         "machine then has to walk all the way round: 65 further slips "
         "(38 -> 103) bring it back to the same boundary, 66 positions later.",
         "The single line-bit error at payload bit 10 of block 640 appears "
         "as **three** output errors - bits 10 and 49 of block 640 and bit 4 "
         "of block 641 (10 + 58 = 68 = 64 + 4): error multiplication, "
         "exactly as predicted.",
         "No other block is wrong: the descrambler, fed with aligned "
         "received bits, was synchronised long before lock was declared."])
    box("warn", "Pitfall: scrambling the sync header or the wrong bit order",
        ["The sync header must bypass the scrambler, and the scrambler must "
         "run in transmission-bit order (bit 0 first). A parallel "
         "implementation that loops over bits in the wrong direction still "
         "round-trips against its own descrambler - both ends are wrong the "
         "same way - and only fails against a third-party device. Always "
         "compare against an independent reference model or a known test "
         "vector, as the Python cross-check does here."])

    # ------------------------------------------------------------------
    h2("JESD204B and JESD204C: data converters")
    p("JEDEC JESD204 connects high-speed **ADCs and DACs** to FPGAs and "
      "ASICs (baseband processors, radar front-ends, test equipment). "
      "Before it, converters used wide parallel LVDS buses; JESD204 "
      "replaces them with a few SerDes lanes. JESD204A (2008) was capped at "
      "3.125 Gb/s; **JESD204B** (2011) added up to 12.5 Gb/s and, above all, "
      "**deterministic latency**; **JESD204C** (2017) reaches 32 Gb/s and "
      "adds 64b/66b coding; **JESD204D** moves to PAM4 with FEC for lane "
      "rates on the order of 100 Gb/s.")
    h3("Parameters and framing")
    tbl(["Parameter", "Meaning"],
        [["L", "Lanes per converter device (link)"],
         ["M", "Converters per device (an I/Q pair counts as 2)"],
         ["N / N'", "Converter resolution / bits per sample on the link incl. "
          "control and tail bits (e.g. N = 14, N' = 16)"],
         ["S", "Samples per converter per frame cycle"],
         ["F", "Octets per frame per lane: F = M x S x N' / (8 x L)"],
         ["K", "Frames per multiframe (204B): F x K between 17 and 1024 octets, "
          "K at most 32"],
         ["CS / CF / HD", "Control bits per sample / control words per frame / "
          "high-density mode (samples may span lanes)"],
         ["E (204C)", "Multiblocks per extended multiblock"]],
        widths=[1.2, 6.0], bold_first=True, caption="JESD204 link parameters.")
    eq(["lane rate = M x N' x S x (frame clock) x (encoding) / L = M x N' x Fs x enc / L",
        "example: M = 2, N' = 16, Fs = 1 GS/s, L = 4, 8b/10b:",
        "         2 x 16 x 1e9 x 10/8 / 4 = 10 Gb/s per lane,  F = 2 x 1 x 16 / 32 = 1"],
       "The fundamental JESD204 sizing equation.")
    p("Samples are packed into **frames** (F octets per lane per frame "
      "clock) and frames into **multiframes** (K frames) in 204B. The "
      "multiframe is the unit of alignment and of deterministic latency.")
    h3("JESD204B link bring-up: CGS, ILAS, data")
    diagram([
        "  RX (FPGA)      SYNC~  ~~~~~~|_____________________|~~~~~~~~~~~~~~~~~~~~~~~~~~~~~",
        "                                 (low = request sync)  (high from next LMFC edge)",
        "  TX (ADC) lane  ... /K/ /K/ /K/ /K/ /K/ /K/ /K/ | /R/ ... /A/ | /R/ /Q/ cfg /A/ | ...",
        "                     Code Group Synchronization  |<-- ILAS: 4 multiframes ---------->|",
        "                     (K28.5 commas)              then user data, with /F/ and /A/",
        "                                                 character replacement at frame and",
        "                                                 multiframe ends",
    ], "JESD204B link start-up (8b/10b).")
    bul(["**CGS (code group synchronization)**: the receiver pulls the "
         "active-low **SYNC~** signal low; the transmitter sends K28.5 "
         "commas; each lane receiver aligns its 8b/10b decoder; after the "
         "required number of good commas on all lanes, SYNC~ is released.",
         "**ILAS (initial lane alignment sequence)**: four multiframes, each "
         "starting with /R/ (K28.0) and ending with /A/ (K28.3); the second "
         "multiframe carries /Q/ (K28.4) and the **link configuration octets** "
         "(L, M, F, K, N, N', S, lane IDs, checksum) so the receiver can "
         "verify its settings match the transmitter's. The /A/ positions "
         "let the receiver align lanes through per-lane elastic buffers.",
         "**User data**: optionally scrambled with 1 + x^{14} + x^{15}. "
         "In place of repeated octets, the transmitter substitutes /F/ "
         "(K28.7) at frame ends and /A/ at multiframe ends; the receiver "
         "uses them to monitor alignment continuously."])
    h3("Deterministic latency, subclasses and SYSREF")
    p("For beamforming, phased-array radar or multi-channel instruments, "
      "the latency from antenna to logic must be the **same on every power "
      "cycle and on every device**, otherwise channels cannot be combined "
      "coherently. JESD204B achieves this by referencing everything to a "
      "**local multiframe clock (LMFC)** in each device and aligning all "
      "LMFCs:")
    tbl(["Subclass", "LMFC alignment", "Deterministic latency?"],
        [["0", "None", "No (compatible with JESD204A behaviour)"],
         ["1", "**SYSREF**: a signal distributed with the device clock, "
          "sampled by the device clock in every converter and FPGA, resets "
          "the LMFC phase", "Yes - the common choice; SYSREF must meet "
          "setup/hold to the device clock at every device"],
         ["2", "The SYNC~ deassertion itself, sampled by the device clock",
          "Yes, but only at lower rates because SYNC~ timing is hard to "
          "control"]],
        widths=[0.8, 4.0, 2.6], bold_first=True,
        caption="JESD204B subclasses.")
    p("The receiver buffers each lane's data in an elastic buffer and "
      "releases all lanes together at an LMFC edge (optionally plus a "
      "programmable **RBD**, release buffer delay). Since lane skew is "
      "absorbed inside one multiframe period, the total latency is fixed "
      "regardless of when each lane happened to lock.")
    h3("JESD204C: 64b/66b and multiblocks")
    p("JESD204C keeps 8b/10b as an option and adds **64b/66b** (plus a "
      "64b/80b mode for rate-plan flexibility). With 64b/66b there are no "
      "commas and no SYNC~ handshake for alignment: each lane uses the "
      "sync-header block lock of the previous section. 32 blocks form a "
      "**multiblock**; E multiblocks form an **extended multiblock**, and the "
      "**LEMC** replaces the LMFC for subclass 1. The sequence of sync "
      "headers across a multiblock forms a low-rate **sync header stream** "
      "carrying a pilot for extended-multiblock alignment plus, selectably, "
      "a CRC-12, a CRC-3, or FEC bits, and a command channel. The scrambler "
      "is the same x^{58} + x^{39} + 1 as Ethernet - the RTL above is directly "
      "reusable.")
    box("warn", "Pitfall: SYSREF is a board-level timing path",
        ["Subclass-1 determinism only holds if SYSREF is captured on the "
         "same device-clock edge at every converter and in the FPGA/ASIC. "
         "Trace-length mismatches, a clock chip with wrong SYSREF delay "
         "settings, or an ASIC capturing SYSREF on a CDC-synchronised path "
         "(adding one cycle of uncertainty) break determinism - and the "
         "symptom is a latency that differs by one LMFC period on some power "
         "cycles only. Capture SYSREF directly with the device clock, check "
         "its phase with a status register, and test across hundreds of "
         "power cycles."])

    # ------------------------------------------------------------------
    h2("Aurora 8B/10B and 64B/66B")
    p("**Aurora** is a lightweight, openly published link-layer protocol "
      "from Xilinx (now AMD) for point-to-point links between FPGAs or "
      "between an FPGA and an ASIC. It gives you lane bonding, framing and "
      "flow control on top of a SerDes, with none of PCIe's complexity:")
    bul(["Two flavours: **Aurora 8B/10B** (8b/10b, comma alignment, K-codes "
         "for idles, start/end of frame and clock compensation) and **Aurora "
         "64B/66B** (64b/66b blocks, scrambling, sync-header block lock).",
         "Single lane or multi-lane **channel bonding**, full-duplex or "
         "simplex.",
         "**Framing** interface (frames with start/end marks, like "
         "AXI4-Stream with TLAST) or **streaming** interface (an endless "
         "word stream).",
         "**Flow control**: native flow control (NFC) lets the receiver "
         "pause the far transmitter; user flow control (UFC) sends "
         "high-priority short messages that bypass data. Aurora 64B/66B "
         "optionally adds a CRC.",
         "Clock compensation sequences at a fixed interval handle the "
         "ppm difference between reference clocks."])
    p("Because the spec is public, Aurora is a common choice when an ASIC "
      "must talk to an FPGA prototype or test board: the ASIC team "
      "implements the (small) link layer in RTL and the FPGA side uses the "
      "vendor's IP core.")

    h2("Interlaken")
    p("**Interlaken** (Cortina Systems and Cisco, 2006; now maintained by "
      "an industry alliance) is the standard chip-to-chip **packet** "
      "interface of networking silicon: NPUs, traffic managers, switches, "
      "FPGAs. It replaced the parallel SPI-4.2 and scales by adding lanes "
      "(1 to dozens, each typically 6-25 Gb/s or more).")
    bul(["**Channels**: up to 256 logical channels (more with extensions), "
         "each with its own **flow control**, multiplexed over one link.",
         "**Bursts**: packets are segmented into bursts up to **BurstMax** "
         "(e.g. 256 bytes), with a **BurstMin** rule preventing tiny bursts "
         "from killing efficiency. Each burst is delimited by a **control "
         "word** carrying the channel number, SOP/EOP flags, the byte count "
         "of the last word, in-band flow control bits and a **CRC-24** "
         "covering the preceding burst.",
         "**64b/67b** coding: a 2-bit framing header as in 64b/66b plus a "
         "third bit that says whether the payload was **inverted** to bound "
         "the running disparity - a cheap DC-balance guarantee on top of "
         "scrambling.",
         "**Metaframes**: each lane periodically sends a metaframe framing "
         "layer - a **synchronization word**, a **scrambler state word** (the "
         "scrambler x^{58}+x^{39}+1 is run as a synchronous, not "
         "self-synchronous, scrambler, so its state is transmitted), a "
         "**skip word** for clock compensation and a **diagnostic word** with "
         "a per-lane CRC-32 and status. Metaframe sync words also deskew "
         "the lanes.",
         "**Flow control**: in-band (XON/XOFF bits for a calendar of channels "
         "in each control word) or out-of-band (a separate slow interface). "
         "**Interlaken Look-Aside** is a variant for lookup coprocessors "
         "(e.g. TCAMs)."])
    box("intuit", "Intuition: why Interlaken uses a synchronous scrambler",
        ["A self-synchronous scrambler multiplies errors by three, which "
         "would break the per-burst CRC-24's error-detection guarantees. A "
         "synchronous (additive) scrambler does not multiply errors - one "
         "line error is one data error - but both ends must share the "
         "scrambler state. Interlaken solves that by sending the state in "
         "every metaframe. Ethernet chose the opposite trade-off because "
         "CRC-32 over a whole frame is robust to the tripled errors."])
    p("**SerialLite** (Altera, now Intel) is a comparable vendor protocol "
      "for FPGA-to-FPGA streaming - lightweight framing, lane bonding and "
      "optional CRC/retry over transceivers - in the same design space as "
      "Aurora.")

    # ------------------------------------------------------------------
    h2("Chiplets and die-to-die interfaces")
    p("Reticle limits, yield and cost push large designs to split into "
      "**chiplets**: several dies in one package, often in different "
      "process nodes (compute on the leading node, I/O and analog on an "
      "older one). The links between them are unlike board-level SerDes: "
      "channels are millimetres long, bumps are tens of microns apart, and "
      "the goals are **bandwidth per millimetre of die edge** "
      "(shoreline), **energy per bit** and **latency** close to on-die wires. "
      "Most die-to-die (D2D) PHYs therefore use many **parallel, "
      "single-ended, clock-forwarded** wires at moderate rates rather than a "
      "few long-reach SerDes lanes.")
    h3("UCIe")
    p("**UCIe (Universal Chiplet Interconnect Express)**, launched in 2022 "
      "by a consortium including Intel, AMD, Arm, TSMC, Samsung and others, "
      "is the leading open D2D standard. It is layered:")
    diagram([
        "  +-----------------------------------------------------------------+",
        "  | Protocol layer: PCIe | CXL | Streaming (user/raw protocol)     |",
        "  +------------------------- FDI (flit-aware D2D interface) -------+",
        "  | Die-to-Die Adapter: link state management, parameter           |",
        "  |   negotiation, CRC + retry (when needed), ARB/MUX of protocols  |",
        "  +------------------------- RDI (raw D2D interface) --------------+",
        "  | Physical layer: logical PHY (link training, lane repair,        |",
        "  |   (de)scrambling) + electrical AFE; clock-forwarded, sideband   |",
        "  +-----------------------------------------------------------------+",
        "  module = N data lanes + forwarded clock + valid + track + sideband",
    ], "UCIe layers and interfaces.")
    tbl(["", "Standard package", "Advanced package"],
        [["Substrate", "Organic substrate (2D)", "Silicon interposer, bridge "
          "(EMIB-like), or fan-out RDL (2.5D)"],
         ["Data lanes per module", "16", "64"],
         ["Bump pitch", "about 100-130 um", "about 25-55 um"],
         ["Reach", "up to about 25 mm", "up to about 2 mm"],
         ["Data rates", "4 - 32 GT/s per lane (UCIe 1.x/2.0); higher rates in "
          "later revisions", "same"],
         ["Lane repair", "Not required (width degrade instead)",
          "Spare lanes for repair"],
         ["Rough energy target", "under 1 pJ/bit", "around 0.5 pJ/bit or less"]],
        widths=[1.6, 2.8, 3.0], bold_first=True,
        caption="UCIe standard vs advanced package (UCIe 1.x figures; check the "
                "current spec for exact limits).")
    bul(["The protocol layer maps **PCIe** and **CXL** (Chapter 18) flits "
         "directly - 68-byte and 256-byte flit formats - so a chiplet can "
         "appear as a PCIe/CXL device to software, or uses **streaming** mode "
         "for a vendor's own coherent fabric (e.g. CHI-based, Chapter 9).",
         "The **D2D adapter** adds CRC and retry when the raw bit error rate "
         "requires it, negotiates parameters, manages link states "
         "(active, low power L1/L2-like states) and arbitrates between "
         "protocol stacks.",
         "A low-speed **sideband** carries link training, register access "
         "and management messages; the main band is forwarded-clock, "
         "single-ended, DDR data plus a **valid** and a **track** signal.",
         "UCIe 2.0 (2024) added a manageability architecture and "
         "**UCIe-3D** for hybrid-bonded stacks with very fine bump pitch; "
         "later revisions push per-lane data rates further (check the "
         "consortium's current releases)."])
    h3("BoW, AIB, OpenHBI and others")
    tbl(["Interface", "Origin", "Character"],
        [["**AIB** (Advanced Interface Bus)", "Intel; released via CHIPS "
          "Alliance", "Wide parallel, clock-forwarded, single-ended; around 1-2 "
          "Gb/s per wire in AIB 1.0, higher in AIB 2.0; used in Intel "
          "FPGA tiles on EMIB"],
         ["**BoW** (Bunch of Wires)", "OCP Open Domain-Specific "
          "Architecture (ODSA)", "Deliberately simple: slices of 16 data wires "
          "with forwarded clock, unterminated at low rates, a few Gb/s up to "
          "around 16 Gb/s per wire; targets standard organic packages"],
         ["**OpenHBI**", "OCP ODSA", "Derived from the HBM3 PHY and its "
          "interposer channel; reuses a proven HBM-style wide parallel "
          "interface for logic-to-logic"],
         ["**XSR / USR SerDes**", "OIF (CEI-112G-XSR etc.)", "Short-reach "
          "SerDes, few wires at very high rates; good for organic packages "
          "where bumps are scarce"],
         ["**Proprietary**", "e.g. AMD Infinity Fabric on-package, Apple "
          "UltraFusion, NVIDIA NV-HBI", "Tuned to one product family; UCIe "
          "aims to replace these at the ecosystem level"]],
        widths=[1.8, 2.0, 4.2],
        caption="Other die-to-die interfaces.")
    box("key", "Key idea: the three D2D figures of merit",
        ["**Shoreline bandwidth density** (Gb/s per mm of die edge) - "
         "determined by bump pitch, wires per module and rate. "
         "**Energy efficiency** (pJ/bit) - determined by swing, termination "
         "and SerDes vs parallel choice. **Latency** (ns) - parallel "
         "clock-forwarded links add only a few ns, far less than a PCIe "
         "SerDes hop. Advanced packaging buys density; simplicity buys energy "
         "and latency."])

    h2("Advanced packaging: 2.5D and 3D")
    tbl(["Technology", "What it is", "Examples"],
        [["2.5D silicon interposer", "Dies side by side on a passive silicon "
          "die with fine-pitch wiring and TSVs down to the substrate",
          "TSMC CoWoS-S; GPU + HBM stacks"],
         ["Embedded bridge", "Small silicon bridges embedded in the organic "
          "substrate only under die edges", "Intel EMIB; TSMC CoWoS-L (local "
          "silicon interconnect)"],
         ["Fan-out / RDL interposer", "Redistribution layers built on a "
          "moulded wafer instead of silicon", "TSMC InFO, CoWoS-R"],
         ["3D stacking (micro-bump)", "Dies stacked face-to-face or face-to-back "
          "with micro-bumps and TSVs", "HBM DRAM stacks, Intel Foveros"],
         ["3D hybrid bonding", "Direct copper-to-copper bonding at pitches of "
          "~10 um and below: thousands of connections per mm^2",
          "TSMC SoIC, AMD 3D V-Cache, Intel Foveros Direct"]],
        widths=[1.8, 3.8, 2.4], bold_first=True, caption="Packaging options for chiplets.")
    p("Packaging changes the test and integration story as much as the "
      "electrical one. Each chiplet must be **known good die (KGD)** before "
      "assembly, so D2D PHYs include loopback, pattern generators and "
      "checkers; die-to-die lanes have **repair** muxes controlled by fuses "
      "or training; and the whole package needs a test access architecture "
      "reaching every die (IEEE 1838 for 3D stacks builds on the 1149.1 and "
      "1500 infrastructure of Chapter 23).")
    box("expert", "Expert corner: who owns a chiplet link",
        ["The **PHY/analog team** owns the AFE, clocking and bump map; the "
         "**package team** owns the channel (interposer/bridge routing, "
         "SI/PI, thermal and warpage); **RTL** owns the adapter, protocol "
         "layer and the logical PHY state machines; **DV** runs "
         "multi-die simulations with both dies' RTL (or a VIP on one side) and "
         "UCIe compliance; **DFT** owns KGD tests, lane repair and the "
         "package-level test network; **firmware** owns training, margining "
         "and repair policy. The biggest integration risk is the "
         "**bump map / lane order contract** between two dies designed by "
         "different teams (or companies) - freeze it early and check it "
         "automatically."])

    h2("Summary")
    bul(["A SerDes link = link layer + PCS (coding, scrambling, alignment, "
         "deskew, clock compensation) + PMA (serializer, equalization, CDR, "
         "PLL); a protocol-agnostic PCS supplies the reusable pieces.",
         "**64b/66b**: 2-bit unscrambled sync header (01 data, 10 control) + "
         "64-bit payload scrambled by self-synchronous x^{58}+x^{39}+1; block "
         "lock slips one bit per invalid header, locks after 64 valid, "
         "unlocks on 16 invalid in 64; one line error becomes three data errors.",
         "**JESD204B**: 8b/10b, CGS with K28.5 and SYNC~, ILAS with "
         "configuration data, frames and multiframes, deterministic latency "
         "via LMFC alignment - SYSREF in subclass 1. **JESD204C**: 64b/66b, "
         "multiblocks, sync-header stream with CRC/FEC, up to 32 Gb/s.",
         "**Aurora** is a light, public link layer (8B/10B or 64B/66B, "
         "framing/streaming, NFC/UFC); **Interlaken** is the packet "
         "interface of networking chips (channels, bursts, control words "
         "with CRC-24, 64b/67b, metaframes, per-channel flow control).",
         "**UCIe** layers PCIe/CXL/streaming over a D2D adapter and a "
         "clock-forwarded parallel PHY; standard (16 lanes, ~100+ um bumps) "
         "and advanced (64 lanes, ~25-55 um) packages; BoW, AIB and OpenHBI "
         "are simpler alternatives.",
         "Advanced packaging (interposers, bridges, RDL, 3D micro-bump and "
         "hybrid bonding) sets bump density and therefore D2D bandwidth."])

    h2("Exercises")
    bul(["A 16-bit DAC pair (M = 2, N' = 16, S = 1) runs at 3 GS/s over "
         "JESD204C with 64b/66b. Compute the lane rate for L = 4 and L = 8 and "
         "decide which fits under 24.75 Gb/s.",
         "Modify the block-lock testbench so the junk prefix is 65 bits. How "
         "many slips occur and why? What is the worst-case lock time in "
         "blocks for a clean link?",
         "Prove that a self-synchronous descrambler resynchronises after 58 "
         "error-free bits regardless of its initial state, and use the "
         "testbench to measure it by starting the RX descrambler with a "
         "random seed.",
         "Add a gearbox to the block-lock design so it accepts 32 bits per "
         "clock instead of 1 (hint: keep a 97-bit history and a 6-bit "
         "offset; a slip increments the offset).",
         "An Interlaken link has 8 lanes at 12.5 Gb/s, BurstMax = 256 bytes, "
         "and a metaframe of 2048 words. Estimate the efficiency for 64-byte "
         "and 1500-byte packets, counting 64b/67b, control words and metaframe "
         "overhead.",
         "Compare the shoreline bandwidth density (Gb/s per mm) of a UCIe "
         "advanced-package module (64 lanes, 32 GT/s, module width about "
         "0.4 mm assumed) with a x16 PCIe Gen5 port occupying about 6 mm of "
         "die edge."], ordered=True)


# ---------------------------------------------------------------- Ch 23 ---
def _ch23():
    chapter("Debug, Test and Trace: JTAG, IEEE 1500, IJTAG, CoreSight, "
            "RISC-V Debug and Trace")
    p("Every protocol so far moves data for the application. The protocols "
      "in this chapter move data **about the chip itself**: they test the "
      "board connections and the silicon, let a debugger halt a core and "
      "read its registers, and stream a record of what the processors did. "
      "They are slow, old and unglamorous, and they are on every chip ever "
      "taped out - a device you cannot test or debug is a device you "
      "cannot ship. We start with IEEE 1149.1 **JTAG** and its descendants "
      "(1149.6, 1500, 1687), move to the processor-debug world of **Arm "
      "CoreSight** and **SWD** and the **RISC-V debug specification**, and "
      "finish with **trace** and cross-triggering. The run examples are a "
      "complete JTAG TAP controller with IDCODE, BYPASS and boundary scan, "
      "and an SWD request-packet builder cross-checked against Python.")

    h2("JTAG: IEEE 1149.1 boundary scan")
    p("The Joint Test Action Group standardised boundary scan in 1990 as "
      "IEEE 1149.1 (revised 2001 and 2013) to test solder joints on "
      "densely populated boards without a bed-of-nails tester. Its "
      "**Test Access Port (TAP)** turned out to be the perfect generic "
      "back door into a chip, so it now also carries processor debug, "
      "FPGA configuration, memory BIST control and fuse programming.")
    tbl(["Pin", "Direction", "Function"],
        [["TCK", "in", "Test clock. Inputs sampled on the rising edge; TDO changes on "
          "the falling edge."],
         ["TMS", "in", "Test mode select; steers the TAP state machine. Pulled up "
          "internally so an undriven TMS resets the TAP."],
         ["TDI", "in", "Serial data into the selected register (LSB first). Pulled up."],
         ["TDO", "out", "Serial data out; tri-stated except in Shift-IR/Shift-DR."],
         ["TRST*", "in", "Optional asynchronous reset of the TAP (active low). "
          "Without it, 5 TCKs with TMS = 1 reset the TAP."]],
        widths=[0.8, 0.9, 6.0], bold_first=True, caption="The TAP pins.")
    h3("The 16-state TAP controller")
    diagram([
        '        +--------------------+  1 (stay)',
        '        |  Test-Logic-Reset  |<--------------------------------------------+',
        '        +---------+----------+                                             |',
        '                0 |                                                        | 1',
        '                  v                   1                1                   |',
        '        +--------------------+    +-----------+    +---------------------+--+',
        '   0 +->|   Run-Test/Idle    |--->| Select-DR |--->| Select-IR: the IR     |',
        '     +--+--------------------+    +-----+-----+    | column, same 7 states |',
        '                  ^                   0 |          | as the DR column      |',
        '                  |                     v          +-----------------------+',
        '                  |               +------------+  1',
        '                  |               | Capture-DR |-----------+',
        '                  |               +-----+------+           |',
        '                  |                   0 |                  |',
        '                  |                     v                  |',
        '                  |               +------------+  0 (stay) |',
        '                  |          +--->|  Shift-DR  |<-+        |',
        '                  |          |    +-----+------+--+        |',
        '                  |          |        1 |                  |',
        '                  |          |          v                  |',
        '                  |          |    +------------+           |',
        '                  |          |    |  Exit1-DR  |<----------+',
        '                  |          |    +-----+------+-------------+ 1',
        '                  |          |        0 |                    |',
        '                  |          |          v                    |',
        '                  |          |    +------------+  0 (stay)   |',
        '                  |          |    |  Pause-DR  |<-+          |',
        '                  |          |    +-----+------+--+          |',
        '                  |          |        1 |                    |',
        '                  |          |          v                    |',
        '                  |          |  0 +------------+  1          |',
        '                  |          +----|  Exit2-DR  |-------+     |',
        '                  |               +------------+       |     |',
        '                  |                                    v     v',
        '                  |   0           +------------+     +-------+',
        '                  +---------------|  Update-DR |<----+',
        '                                  +-----+------+',
        '                                      1 +---> Select-DR',
    ], "The TAP controller. The IR column mirrors the DR column; from any state, five "
       "TCKs with TMS = 1 reach Test-Logic-Reset.")
    p("The state machine has two symmetric columns: one for the **instruction "
      "register (IR)** and one for the currently selected **data register "
      "(DR)**. **Capture** loads the register's parallel value into its "
      "shift stage, **Shift** moves bits from TDI towards TDO, **Pause** "
      "lets a slow tester stop mid-shift, and **Update** transfers the shift "
      "stage to the parallel output latch on the falling edge of TCK - so "
      "the chip's behaviour changes only at Update, never while bits ripple "
      "through. Its key property: **five TCKs with TMS high reach "
      "Test-Logic-Reset from any state**, which is why an unpowered or "
      "disconnected debugger (TMS pulled high) keeps the TAP harmlessly in "
      "reset.")
    h3("Instructions and data registers")
    tbl(["Instruction", "Status in 1149.1", "Selects", "Effect"],
        [["BYPASS", "Mandatory; opcode all ones", "1-bit bypass register (captures 0)",
          "Shortens a daisy chain to one bit per inactive device"],
         ["SAMPLE / PRELOAD", "Mandatory (separate or shared opcodes since 2001)",
          "Boundary-scan register", "Snapshot the pins without disturbing them / "
          "load values for a later EXTEST"],
         ["EXTEST", "Mandatory (all-zeros opcode required in 1990, no longer in 2001)",
          "Boundary-scan register", "Pins driven from the boundary cells: test the "
          "board interconnect"],
         ["IDCODE", "Optional but near-universal; selected at reset when present",
          "32-bit device ID register", "Identify each device in the chain"],
         ["USERCODE, INTEST, CLAMP, HIGHZ, RUNBIST", "Optional",
          "Various", "User ID, core test, safe pin states, BIST"],
         ["Private (e.g. DEBUG, DTM)", "Vendor defined", "Vendor DRs",
          "Debug port access, fuses, DFT controls"]],
        widths=[1.8, 2.2, 1.8, 2.6], bold_first=True,
        caption="1149.1 instructions. The IR is at least 2 bits; its captured value "
                "must end in binary 01, which lets software measure IR lengths in a chain.")
    diagram([
        "   31      28 27                      12 11                  1   0",
        "  +----------+--------------------------+---------------------+---+",
        "  | version  |       part number        |  manufacturer ID    | 1 |",
        "  |  4 bits  |         16 bits          | JEP106: [11:8] bank |   |",
        "  |          |                          | count, [7:1] code   |   |",
        "  +----------+--------------------------+---------------------+---+",
        "  LSB = 1 distinguishes IDCODE from BYPASS (captures 0) when a chain is",
        "  scanned blindly after reset: software counts devices and reads their IDs.",
    ], "The IDCODE register format.")
    h3("Boundary-scan cells and BSDL")
    diagram([
        "              shift stage                 update stage",
        "  from core --+----------------+          +--------+       +-----+",
        "  (or pin)    |   +--------+   |  scan    |        |       | MUX |--> to pin",
        "              +-->| capture|---+-- out -->| update |------>|1    |   (or core)",
        "  scan in ------->|  /shift|              | latch  |  core |0    |",
        "                  +--------+              +--------+  ---->|     |",
        "                    ^ ShiftDR, ClockDR       ^ UpdateDR    +--+--+",
        "                                                              | Mode (EXTEST)",
    ], "A classic output boundary-scan cell (BC_1 style).")
    p("Each I/O has one or more cells (input, output, output-enable). "
      "A device's register layout, opcodes, IR length and cell types are "
      "published in a **BSDL** file (Boundary Scan Description Language, a "
      "VHDL subset) that board-test tools read to generate interconnect "
      "tests automatically. Getting the BSDL to match the silicon is a "
      "sign-off item: tools compare it with the netlist, and a wrong cell "
      "order breaks every customer's board test.")
    code(["-- BSDL excerpt (illustrative)",
          "attribute INSTRUCTION_LENGTH of demo_soc : entity is 4;",
          "attribute INSTRUCTION_OPCODE of demo_soc : entity is",
          "  \"EXTEST (0000), IDCODE (0001), SAMPLE (0010), PRELOAD (0010), BYPASS (1111)\";",
          "attribute INSTRUCTION_CAPTURE of demo_soc : entity is \"0101\";",
          "attribute IDCODE_REGISTER of demo_soc : entity is",
          "  \"0001\" & \"1010010110110011\" & \"00001010101\" & \"1\";",
          "attribute BOUNDARY_LENGTH of demo_soc : entity is 8;"],
         "What the TAP below would publish in its BSDL file.")
    h3("A TAP controller in RTL")
    p("The design below implements the full 16-state controller, a 4-bit "
      "IR (capture value 0101), IDCODE, BYPASS, SAMPLE/PRELOAD and EXTEST "
      "over an 8-cell boundary register. Capture and shift happen on the "
      "rising edge of TCK; IR/boundary updates and TDO on the falling edge, "
      "as 1149.1 requires.")
    _v("tap", "An IEEE 1149.1 TAP controller with IDCODE, BYPASS, SAMPLE/PRELOAD and EXTEST.")
    _v("tb_tap", "Testbench: read IDCODE after reset, read IR capture, test BYPASS, SAMPLE and "
                 "EXTEST, and 2000 random TMS walks that must end in Test-Logic-Reset.")
    _o("tap", "Icarus Verilog output: IDCODE 0x1A5B3157 shifts out with LSB = 1, IR captures "
              "0101, BYPASS delays by one bit, SAMPLE captures the pins, EXTEST drives the "
              "preloaded pattern, and all 2000 random walks reset.")
    box("warn", "Pitfall: TDO timing, chains and JTAG clocks",
        ["TDO must change on the **falling** edge so the next device (or the "
         "probe) samples a stable value on the rising edge; changing it on "
         "the rising edge creates a hold race in daisy chains. TCK is an "
         "external, often slow and noisy clock: treat it as its own clock "
         "domain in CDC analysis, constrain it in STA, and synchronise every "
         "signal crossing into the functional domain. Finally, remember our "
         "own testbench bug: sampling TDO in the same time step as the "
         "falling edge read the old value - a race that real probes avoid "
         "by sampling at the rising edge, exactly as the fixed task does."])

    h2("IEEE 1149.6: AC-coupled and differential nets")
    p("1149.1 EXTEST assumes a DC path: the receiver sees the level the "
      "driver holds. High-speed SerDes lanes are **AC-coupled** through "
      "series capacitors, which block DC, so a static EXTEST value decays "
      "away. IEEE 1149.6 (2003) adds **EXTEST_PULSE** and **EXTEST_TRAIN** "
      "instructions that make drivers produce edges, and special **test "
      "receivers** with hysteresis that detect those edges through the "
      "capacitor. It lets board test find opens and shorts on PCIe, "
      "Ethernet or DP lanes. The test receiver sits in the PHY - a "
      "PHY/analog-team deliverable that is easy to forget until board-test "
      "engineers ask for the BSDL extension.")

    h2("IEEE 1500: embedded core test wrappers")
    p("1149.1 tests a chip's boundary; IEEE 1500 (2005) applies the same "
      "idea to **cores inside the chip**, so an IP block can be tested in "
      "isolation from the logic around it. Each core gets a **wrapper**:")
    bul(["**WSP (Wrapper Serial Port)**: WSI, WSO, WRCK, WRSTN and control "
         "signals SelectWIR, CaptureWR, ShiftWR, UpdateWR - the equivalent "
         "of a TAP's internal signals, but driven by a chip-level controller "
         "(usually the TAP) rather than a state machine in the core.",
         "**WIR (Wrapper Instruction Register)** selects the wrapper mode.",
         "**WBY (Wrapper Bypass)**: 1-bit bypass, like BYPASS.",
         "**WBR (Wrapper Boundary Register)**: cells on every core terminal, "
         "used to isolate the core (INTEST, testing the core from its wrapper) "
         "or its surroundings (EXTEST, testing the logic between cores).",
         "Optional **WPP (Wrapper Parallel Port)** for high-bandwidth scan "
         "test, and **WDRs** for core-specific data registers. Mandatory "
         "instructions include WS_BYPASS and WS_EXTEST plus at least one "
         "core-test instruction. The wrapper is described for tools in "
         "CTL (Core Test Language, IEEE 1450.6)."])
    p("In practice DFT tools insert 1500-style wrappers automatically as "
      "part of **hierarchical test** so that each core's scan patterns are "
      "generated once and reused wherever the core is instantiated.")

    h2("IEEE 1687 IJTAG: instrument access networks")
    p("A modern SoC contains thousands of **embedded instruments**: memory "
      "BIST controllers, PLL and SerDes test registers, temperature and "
      "voltage sensors, fuse controllers, ring oscillators. Putting each on "
      "its own JTAG instruction does not scale. IEEE 1687 (2014), "
      "**IJTAG**, defines a **reconfigurable scan network** behind the TAP "
      "and languages to describe and use it:")
    diagram([
        "   TDI --> [SIB A] --------------> [SIB B] --------------> [TDR] --> TDO",
        "              |  ^                    |  ^",
        "       open:  v  | (segment           v  |",
        "            [ MBIST ctrl TDR ]      [SIB C]-->[ PLL test TDR ]",
        "                                       |",
        "                                    [ thermal sensor TDR ]",
        "   SIB = Segment Insertion Bit: a 1-bit register; when set (and updated)",
        "   it splices its sub-network into the scan path, when clear it bypasses it",
    ], "An IJTAG network: SIBs open and close hierarchical segments.")
    bul(["**SIB (Segment Insertion Bit)**: a one-bit shift/update cell that "
         "either bypasses or inserts a sub-segment. The active scan path is "
         "only as long as the instruments you are using.",
         "**ICL (Instrument Connectivity Language)**: describes the network "
         "- registers, SIBs, muxes and their connections.",
         "**PDL (Procedure Description Language)**: describes how to operate "
         "an instrument at its own terminals: `iWrite`, `iRead`, `iApply`, "
         "`iCall`. The instrument vendor writes PDL once; a **retargeting** "
         "tool uses the ICL to translate it into TAP-level shift sequences "
         "for whatever network the SoC integrator built."])

    # ------------------------------------------------------------------
    h2("Arm CoreSight: the Debug Access Port")
    p("Processor debug needs far more than boundary scan: halting cores, "
      "reading registers and memory, setting breakpoints, controlling "
      "trace. Arm's **CoreSight** architecture standardises it. The entry "
      "point is the **Debug Access Port (DAP)** defined by the Arm Debug "
      "Interface architecture (**ADIv5**, and ADIv6 which allows APs to "
      "live in a memory map and to be nested).")
    diagram([
        "  debug probe                  DAP",
        "  JTAG or SWD  +---------------------------------+",
        "  ============>| DP: JTAG-DP, SW-DP or SWJ-DP    |",
        "               | regs: DPIDR, CTRL/STAT, SELECT, |",
        "               |       RDBUFF, ABORT             |",
        "               +----+-----------+-----------+----+",
        "                    | APSEL     |           |",
        "               +----v----+ +----v----+ +----v------+",
        "               | MEM-AP  | | MEM-AP  | | JTAG-AP   |",
        "               | (APB)   | | (AXI)   | | legacy    |",
        "               +----+----+ +----+----+ | TAPs      |",
        "                    |           |      +-----------+",
        "          debug APB bus:    system AXI: memory, peripherals",
        "          ROM table, core debug, CTI, ETM, funnels, TPIU, ETR",
    ], "A CoreSight DAP: one Debug Port, several Access Ports.")
    bul(["The **Debug Port (DP)** terminates the external protocol: a "
         "**JTAG-DP** (a JTAG TAP with DPACC/APACC instructions), a **SW-DP** "
         "(Serial Wire Debug) or an **SWJ-DP** that supports both on shared "
         "pins (TMS/SWDIO and TCK/SWCLK) and switches with a magic sequence.",
         "DP registers: **DPIDR** (identification, e.g. 0x2BA01477 for a "
         "common SW-DP), **CTRL/STAT** (power-up requests CDBGPWRUPREQ and "
         "CSYSPWRUPREQ with their ACKs, sticky error flags), **SELECT** (which "
         "AP and which 16-byte register bank), **RDBUFF** (result of the last "
         "posted AP read) and **ABORT** (clear sticky errors, abort a stuck "
         "transaction).",
         "An **Access Port (AP)** turns DP accesses into something useful. A "
         "**MEM-AP** masters a bus: the debugger writes **TAR** (transfer "
         "address), sets size and auto-increment in **CSW**, and reads or "
         "writes **DRW** (data read/write); **BD0-BD3** access four words "
         "around TAR without rewriting it. An APB-AP typically reaches the "
         "debug components, an AXI-AP reaches system memory.",
         "Discovery: every CoreSight system has **ROM tables** listing the "
         "components (cores, CTIs, ETMs, funnels) with their component and "
         "peripheral ID registers, so a debugger can find everything "
         "starting from the AP's BASE register."])
    box("warn", "Pitfall: posted AP reads and the debug power domain",
        ["AP reads through a DP are **posted**: the value returned by an AP "
         "read is the result of the **previous** AP read, and the last one "
         "must be collected from RDBUFF. Hand-written probe scripts that "
         "forget this are off by one. Also, the debug logic usually sits in "
         "its own power domain: until the debugger sets CDBGPWRUPREQ and sees "
         "CDBGPWRUPACK, AP accesses fault. SoC integrators must wire those "
         "handshakes to the power controller - a missing connection makes "
         "the chip undebuggable exactly when a core is in a low-power state."])

    h2("Serial Wire Debug (SWD)")
    p("SWD replaces the four or five JTAG wires with two: **SWCLK** (driven "
      "by the host) and bidirectional **SWDIO**. It carries exactly the DP "
      "and AP register accesses of ADIv5, nothing else, which makes it "
      "faster per pin and ideal for small microcontrollers. Each "
      "transaction has three phases:")
    diagram([
        "  host drives                        | target drives   | host or target drives",
        "  Start APnDP RnW A2 A3 Par Stop Park| Trn | ACK[0:2]  | Trn*| 32 data bits | Par",
        "    1    x    x   x  x   p   0    1  |  Z  | 1 0 0 =OK |  Z  | LSB first ...|  p",
        "  |<------ 8-bit request ----------->|     |<-3 bits ->|     |<-- 33 bits ------>|",
        "   Parity = even parity over APnDP, RnW, A2, A3 (so the 4 bits + Par have even ones)",
        "   ACK: OK = 1,0,0  WAIT = 0,1,0  FAULT = 0,0,1  (bit order on the wire)",
        "   Read:  no Trn* - the target drives data right after ACK; one Trn after Par",
        "   Write: Trn* after ACK, then the host drives data + parity",
    ], "SWD transaction: request, turnaround, acknowledge, data.")
    bul(["**Request**: 8 bits LSB first - Start (1), APnDP (0 = DP, 1 = AP), "
         "RnW (1 = read), A[2:3] (register address bits, word-aligned), "
         "Parity, Stop (0), Park (1: the host drives SWDIO high before "
         "releasing it).",
         "**Turnaround (Trn)**: one or more clock periods with neither side "
         "driving, whenever SWDIO changes direction.",
         "**ACK**: OK, WAIT (target busy: the host must retry - typically "
         "the AP bus transfer has not finished) or FAULT (a sticky error is "
         "set: the host clears it through ABORT). No response (all ones or "
         "all zeros) means the target is not listening - protocol error.",
         "**Data**: 32 bits LSB first plus one even-parity bit.",
         "**Line reset**: at least 50 SWCLK cycles with SWDIO high, followed by "
         "idle cycles, then a read of DPIDR (required after reset).",
         "**JTAG-to-SWD switching** on SWJ-DP: line reset, the 16-bit sequence "
         "0xE79E sent LSB first, line reset again. Newer parts (ADIv5.2 and "
         "later) also support a **dormant** state entered and left with a "
         "128-bit selection alert and an activation code, which lets several "
         "debug protocols share pins safely.",
         "**Multi-drop SWD (SWDv2)**: several targets on one SWD bus, "
         "selected by writing a TARGETSEL value right after a line reset."])
    p("The request byte is small enough to verify exhaustively. The builder "
      "below is a pair of SystemVerilog functions; the testbench compares "
      "all 16 combinations against a Python model and prints the DP "
      "request table that every SWD probe firmware writer ends up memorising "
      "(0xA5 = read DPIDR, 0x81 = write ABORT, 0xB1 = write SELECT, 0xBD = "
      "read RDBUFF).")
    _v("swd", "SWD request packet and data-parity builders.")
    code(["# Python reference used to generate swd_gold.hex",
          "def req(ap, rnw, a2, a3):",
          "    par = ap ^ rnw ^ a2 ^ a3",
          "    bits = [1, ap, rnw, a2, a3, par, 0, 1]      # wire order, bit 0 first",
          "    return sum(b << i for i, b in enumerate(bits))",
          "with open('swd_gold.hex', 'w') as f:",
          "    for n in range(16):                          # n = {APnDP, RnW, A2, A3}",
          "        ap, rnw, a2, a3 = (n >> 3) & 1, (n >> 2) & 1, (n >> 1) & 1, n & 1",
          "        f.write('%02x\\n' % req(ap, rnw, a2, a3))"],
         "Python reference for the SWD request byte.")
    _v("tb_swd", "Testbench: all 16 requests vs Python, the DP request table, and a "
                 "data-phase parity example.")
    _o("swd", "Icarus Verilog output. The 'on the wire' column shows the bit sequence in "
              "transmission order (Start first, Park last).")
    box("tip", "Practical tip: the SWD bring-up sequence",
        ["A robust probe does: line reset -> JTAG-to-SWD sequence -> line "
         "reset -> 2+ idle cycles -> read DPIDR (0xA5) -> write ABORT (0x81) "
         "to clear sticky errors -> write CTRL/STAT to request debug and "
         "system power-up -> poll the ACK bits -> write SELECT (0xB1) to pick "
         "an AP -> read the AP's IDR -> program CSW/TAR -> DRW accesses. On "
         "WAIT, retry; on FAULT, read CTRL/STAT, clear through ABORT and "
         "investigate. If DPIDR never answers, suspect pin muxing, a "
         "debug-disable fuse, or a core that disabled the SWD pins in "
         "firmware."])

    # ------------------------------------------------------------------
    h2("The RISC-V debug specification")
    p("RISC-V's **External Debug Support** specification (0.13 was the "
      "first widely implemented version, 1.0 ratified later) defines a "
      "layered, implementation-independent debug architecture:")
    diagram([
        "  debugger (OpenOCD/GDB)",
        "     | JTAG (or another transport)",
        "  +--v---------------------------+     DMI: address | data (32) | op (2)",
        "  | DTM: Debug Transport Module  |------------------------------------+",
        "  |  JTAG IR: IDCODE 0x01,       |                                    |",
        "  |  dtmcs 0x10, dmi 0x11,       |           +------------------------v------+",
        "  |  BYPASS 0x1f                 |           | DM: Debug Module              |",
        "  +------------------------------+           | dmcontrol 0x10  dmstatus 0x11 |",
        "                                             | abstractcs 0x16 command 0x17  |",
        "                                             | data0.. 0x04    progbuf0 0x20 |",
        "                                             | sbcs 0x38 (system bus access) |",
        "                                             +---+-------------+-------------+",
        "                                                 | halt/resume | system bus",
        "                                             hart0 .. hartN     memory",
    ], "RISC-V debug: DTM -> DMI -> Debug Module -> harts.")
    bul(["The **DTM** turns the external transport into **DMI** accesses. "
         "The standard JTAG DTM has a 5-bit IR; **dtmcs** reports the DMI "
         "address width and idle-cycle requirement, and **dmi** is a shift "
         "register of {address, 32-bit data, 2-bit op} where op = 1 is "
         "read, 2 is write, and on capture the op field returns status "
         "(0 success, 2 failed, 3 busy - retry with more idle cycles).",
         "The **Debug Module (DM)** controls harts: **dmcontrol** selects "
         "harts and requests halt/resume/reset; **dmstatus** reports "
         "state (allhalted, anyrunning, authenticated...).",
         "**Abstract commands** (written to **command**, arguments in "
         "data0..): Access Register (cmdtype 0; regno 0x1000+n for GPR xn, "
         "CSR numbers below 0x1000; aarsize 2 for 32-bit, 3 for 64-bit), "
         "Quick Access and Access Memory. **abstractcs** reports busy and "
         "an error code (cmderr) that must be cleared by writing ones.",
         "A **program buffer** lets the debugger run short instruction "
         "sequences on a halted hart (e.g. fence.i or CSR moves the abstract "
         "commands do not cover); **system bus access** (sbcs/sbaddress/sbdata) "
         "reads memory without halting any hart, much like a MEM-AP.",
         "In the hart, **debug mode** is entered on halt, with **dcsr** "
         "(cause, step, ebreak behaviour) and **dpc** (resume PC); the "
         "**Sdtrig** extension defines hardware triggers (breakpoints and "
         "watchpoints)."])
    box("intuit", "Intuition: CoreSight and RISC-V debug are the same shape",
        ["Probe protocol (JTAG/SWD vs JTAG DTM) -> a small register-access "
         "transport (DP/AP accesses vs DMI) -> a debug block that halts cores "
         "and a bus master that reads memory (core debug + MEM-AP vs DM "
         "abstract commands + system bus access). Once you know one, the "
         "other is a matter of register names - and SoCs mixing Arm and "
         "RISC-V cores often bridge a RISC-V DM behind a CoreSight APB-AP."])

    # ------------------------------------------------------------------
    h2("Trace: recording what happened")
    p("Halting a core changes the timing of the bug you are chasing. "
      "**Trace** records execution non-intrusively and streams it off-chip "
      "or into a buffer. CoreSight trace is a pipeline of **sources**, "
      "**links** and **sinks**, all joined by the **ATB** (AMBA Trace Bus):")
    diagram([
        "  sources                  links                       sinks",
        "  +------+ ATB                                         +-------+ TRACECLK +",
        "  | ETM  |-----+        +---------+    +------------+  | TPIU  |=========> TRACEDATA[n]",
        "  | core0|     +------->|         |    |            |->+-------+   external trace port",
        "  +------+              | funnel  |--->| replicator |",
        "  +------+  +---------->| (merge) |    |            |->+-------+",
        "  | ETM  |--+           +---------+    +------------+  | ETF / |  on-chip buffer",
        "  | core1|                   ^                          | ETR   |->  (ETR writes to DRAM",
        "  +------+  +------+        |                           +-------+      over AXI)",
        "            | STM  |--------+   SW/HW instrumentation",
        "            +------+            (ITM on Cortex-M, with SWO pin output)",
    ], "A CoreSight trace topology.")
    tbl(["Component", "Role"],
        [["**ETM / PTM**", "Embedded Trace Macrocell (PTM: Program Trace Macrocell, "
          "an older program-flow-only variant): compresses a core's instruction "
          "stream into packets - mainly taken/not-taken atoms and indirect "
          "branch targets; a decoder reconstructs the full flow using the "
          "program image. Optional data trace and cycle counts."],
         ["**ITM**", "Instrumentation Trace Macrocell (Cortex-M): software writes to "
          "stimulus ports (printf-style logging without a UART), plus hardware "
          "event and PC-sampling packets from the DWT. Often output over the "
          "single-pin **SWO** (Manchester or UART-style NRZ)."],
         ["**STM**", "System Trace Macrocell: many masters (cores, DMA, hardware "
          "events) write to memory-mapped stimulus channels; output uses the MIPI "
          "STP protocol with timestamps."],
         ["**Funnel / replicator**", "Merge several ATB streams (each tagged with a "
          "trace ID) / duplicate a stream to two sinks."],
         ["**TPIU**", "Trace Port Interface Unit: formats the ATB stream into 16-byte "
          "frames with IDs and drives a parallel trace port (TRACECLK + 1-32 "
          "TRACEDATA pins) to an external trace probe."],
         ["**ETB / ETF / ETR**", "On-chip sinks: ETB is a dedicated SRAM; the Trace "
          "Memory Controller configured as ETF (FIFO/buffer) or ETR (router) - "
          "the ETR writes trace to system DRAM through AXI, the usual choice on "
          "large SoCs since it needs no pins."],
         ["**RISC-V N-trace / E-trace**", "RISC-V trace encoders: **E-trace** "
          "(Efficient Trace) is a branch-trace format fed from a standard "
          "ingress port on the hart; **N-trace** uses the IEEE-ISTO 5001 "
          "Nexus message format. Both feed similar funnels and sinks."]],
        widths=[1.7, 6.0], bold_first=True, caption="Trace components.")
    box("math", "Math: trace bandwidth",
        ["Program-flow trace of a core at 2 GHz typically needs on the order "
         "of 1 bit or less per instruction after compression, so a few cores "
         "produce several Gb/s. A 16-pin TPIU at 300 MHz DDR gives about 9.6 "
         "Gb/s; an ETR into DRAM can sustain much more but eats memory "
         "bandwidth. Size trace sinks for the number of cores traced at "
         "once, and expect **overflow** packets when a burst of indirect "
         "branches exceeds the budget."])

    h2("Cross-triggering: CTI and CTM")
    p("To debug a multi-core or heterogeneous system, you want a "
      "breakpoint on one core to **halt all of them** within a few cycles, "
      "or a trace capture to start when a peripheral raises an event. "
      "CoreSight provides a **Cross Trigger Interface (CTI)** next to each "
      "core or trace component and a **Cross Trigger Matrix (CTM)** that "
      "broadcasts events on a small number of **channels** (typically 4) "
      "between CTIs. Each CTI maps its local trigger inputs (e.g. 'core "
      "halted', 'trace buffer full') onto channels and channels onto its "
      "trigger outputs (e.g. 'debug request', 'restart', 'trace start'). "
      "The CTIs are programmed by the debugger through the APB-AP; the "
      "handshakes cross clock and power domains, so trigger outputs are "
      "usually level signals with acknowledges rather than single pulses.")

    h2("Post-silicon debug and debug security")
    bul(["**Scan dump**: stop the clocks and shift out every scan flop "
         "through the test infrastructure - a full-state snapshot after a "
         "hang, mapped back to RTL signal names with the scan-chain map.",
         "**Embedded logic analyzers (ELA)** and **debug buses**: selectable "
         "internal signals muxed into a trace buffer with trigger logic "
         "(CoreSight ELA-500/600 is one product); chosen at design time, so "
         "the architecture team must predict which signals will matter.",
         "**On-chip performance monitors** and bus trace (e.g. CoreSight "
         "AXI trace / Catu, NoC probes) for interconnect deadlocks.",
         "**Security**: debug is the most powerful attack surface on the "
         "chip. Arm's authentication signals DBGEN, NIDEN, SPIDEN and SPNIDEN "
         "(invasive/non-invasive, non-secure/secure) are driven by a secure "
         "life-cycle controller; production parts lock or authenticate debug "
         "(challenge-response), keep TAP access to secure fuses and keys "
         "disabled, and allow re-opening only for authenticated failure "
         "analysis (RMA). The RISC-V DM has an 'authenticated' bit for the "
         "same purpose.",
         "**Ownership**: DFT owns 1149.1/1500/1687 and scan; the "
         "debug/SoC architecture team owns CoreSight topology, ROM tables "
         "and CTI wiring; RTL integrates; DV verifies with a JTAG/SWD VIP and "
         "by running real debugger scripts on the emulator; security reviews "
         "the life-cycle gating; the tools/firmware team delivers the debugger "
         "configuration files that describe it all."])
    box("warn", "Pitfall: debug that only works when nothing is wrong",
        ["Debug paths that depend on the functional system - a debug APB "
         "clocked by a gated clock, a MEM-AP behind an interconnect that "
         "deadlocked, trace written to DRAM that is not initialised yet - "
         "fail exactly when you need them. Keep the DAP, the ROM table and "
         "at least one path to core debug registers on always-on clocks and "
         "power, give the MEM-AP a path that bypasses congested NoC queues, "
         "and make sure JTAG/SWD can reset the system (a debug-requested "
         "reset) without software help."])

    h2("Summary")
    bul(["**1149.1 JTAG**: TCK/TMS/TDI/TDO (+ optional TRST*), a 16-state TAP "
         "controller with IR and DR columns, capture/shift on rising TCK and "
         "update/TDO on falling TCK, five TMS = 1 clocks reset from anywhere.",
         "Mandatory instructions BYPASS (all ones), SAMPLE, PRELOAD and EXTEST; "
         "IDCODE is optional but universal: version/part/JEP106 "
         "manufacturer/LSB = 1. The IR captures ...01. BSDL describes it all.",
         "**1149.6** adds pulse/train EXTEST for AC-coupled lanes; **1500** "
         "wraps cores (WSP, WIR, WBY, WBR); **1687 IJTAG** builds SIB-based "
         "instrument networks described in ICL and operated through PDL.",
         "**CoreSight DAP** = one DP (JTAG-DP, SW-DP, SWJ-DP) + APs (MEM-AP "
         "with CSW/TAR/DRW); AP reads are posted; debug power-up handshakes "
         "must be wired.",
         "**SWD**: 8-bit request (Start, APnDP, RnW, A[2:3], even parity, "
         "Stop, Park), turnaround, 3-bit ACK (OK/WAIT/FAULT), 32 data bits + "
         "parity; line reset and the 0xE79E JTAG-to-SWD switch.",
         "**RISC-V debug**: DTM (dtmcs/dmi) -> DMI -> Debug Module with "
         "abstract commands, program buffer and system bus access.",
         "**Trace**: ETM/PTM, ITM, STM sources; funnels/replicators; TPIU, "
         "ETB/ETF/ETR sinks; RISC-V E-trace/N-trace; CTI/CTM cross-triggering.",
         "Debug must be secure (life-cycle gated) and must survive the "
         "failures it is meant to diagnose."])

    h2("Exercises")
    bul(["A board has three devices in a JTAG chain with IR lengths 4, 5 "
         "and 8. After reset, how many bits must be shifted through Shift-DR "
         "to read all IDCODEs, and how does software discover the IR lengths "
         "without prior knowledge? (Hint: the 01 capture rule.)",
         "Add a USERCODE instruction and a 2-bit IJTAG-style SIB in front of "
         "an 8-bit instrument register to the TAP design. Write a testbench "
         "that opens the SIB, writes the instrument and reads it back.",
         "Write the SWD read-transaction engine: it sends a request built by "
         "`swd_req`, performs turnaround, samples ACK, reads 32 bits plus "
         "parity, and retries on WAIT. Test it against a target model that "
         "answers WAIT twice before OK.",
         "Using the RISC-V debug spec, write the sequence of DMI writes and "
         "reads needed to halt hart 0, read register x10 with an abstract "
         "command, and resume it.",
         "An SoC has 8 cores traced with ETM at an average of 0.6 bits per "
         "instruction and 2 instructions per cycle at 1.5 GHz. Can a 16-bit "
         "TPIU at 250 MHz DDR carry it? How large an ETR buffer captures "
         "10 ms?",
         "List every signal and condition that must be true for a debugger "
         "to halt a core that is currently in a power-down state in your "
         "favourite SoC, and identify which team owns each."], ordered=True)
