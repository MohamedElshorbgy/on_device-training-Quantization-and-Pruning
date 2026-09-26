"""Part III - SoC Architecture in RTL (Chapters 11-16) of the RTL guide.

Every Verilog/SystemVerilog design and testbench in SRC was compiled with
Icarus Verilog 12 (iverilog -g2012 -Wall) and simulated with vvp; OUT holds the
captured simulator output verbatim (only the trailing "$finish called" line is
omitted).
"""

from rtl_guide.common import *  # noqa: F401,F403

# --- Verilog sources and REAL Icarus Verilog 12 output (generated) ---
SRC = {
    'afifo': r'''
module async_fifo #(parameter int W = 8, parameter int AW = 4) (   // depth = 2**AW
  input  logic         wclk, wrst_n, winc,
  input  logic [W-1:0] wdata,
  output logic         wfull,
  input  logic         rclk, rrst_n, rinc,
  output logic [W-1:0] rdata,
  output logic         rempty
);
  logic [W-1:0] mem [2**AW];
  logic [AW:0]  wbin, wgray, rbin, rgray;        // one extra bit: wrap indicator
  logic [AW:0]  rgray_w1, rgray_w2;              // rgray synchronized into wclk
  logic [AW:0]  wgray_r1, wgray_r2;              // wgray synchronized into rclk

  function automatic logic [AW:0] b2g(input logic [AW:0] b);
    return b ^ (b >> 1);
  endfunction

  // ---------------- write domain ----------------
  logic [AW:0] wbin_nxt, wgray_nxt;
  assign wbin_nxt  = wbin + (winc & ~wfull);
  assign wgray_nxt = b2g(wbin_nxt);
  always_ff @(posedge wclk or negedge wrst_n)
    if (!wrst_n) begin
      wbin <= '0; wgray <= '0; wfull <= 1'b0; {rgray_w2, rgray_w1} <= '0;
    end else begin
      {rgray_w2, rgray_w1} <= {rgray_w1, rgray};
      wbin  <= wbin_nxt;
      wgray <= wgray_nxt;                        // registered: glitch-free when sampled
      // full: next wgray equals rgray with the two MSBs inverted
      wfull <= (wgray_nxt == {~rgray_w2[AW:AW-1], rgray_w2[AW-2:0]});
    end
  always_ff @(posedge wclk)
    if (winc && !wfull) mem[wbin[AW-1:0]] <= wdata;

  // ---------------- read domain -----------------
  logic [AW:0] rbin_nxt, rgray_nxt;
  assign rbin_nxt  = rbin + (rinc & ~rempty);
  assign rgray_nxt = b2g(rbin_nxt);
  always_ff @(posedge rclk or negedge rrst_n)
    if (!rrst_n) begin
      rbin <= '0; rgray <= '0; rempty <= 1'b1; {wgray_r2, wgray_r1} <= '0;
    end else begin
      {wgray_r2, wgray_r1} <= {wgray_r1, wgray};
      rbin   <= rbin_nxt;
      rgray  <= rgray_nxt;
      rempty <= (rgray_nxt == wgray_r2);         // empty: pointers identical
    end
  assign rdata = mem[rbin[AW-1:0]];              // FWFT-style combinational read
endmodule''',
    'apb': r'''
module apb_regs (
  input  logic        pclk, presetn,
  input  logic        psel, penable, pwrite,
  input  logic [11:0] paddr,
  input  logic [31:0] pwdata,
  input  logic [3:0]  pstrb,             // APB4 byte strobes
  output logic [31:0] prdata,
  output logic        pready, pslverr,
  input  logic [7:0]  hw_status          // read-only status from the hardware
);
  localparam logic [11:0] A_CTRL = 12'h000, A_STAT = 12'h004,
                          A_DATA = 12'h008, A_ID   = 12'h00C;
  logic [31:0] ctrl, data;
  logic        wait_done;                // DATA accesses take one wait state
  wire  access = psel &  penable;
  wire  ro     = (paddr == A_STAT) || (paddr == A_ID);
  wire  hit    = ro || (paddr == A_CTRL) || (paddr == A_DATA);
  wire  slow   = (paddr == A_DATA);

  // PREADY: low for exactly one ACCESS cycle when the slow register is addressed
  always_ff @(posedge pclk or negedge presetn)
    if (!presetn)                          wait_done <= 1'b0;
    else if (access && slow && !wait_done) wait_done <= 1'b1;
    else                                   wait_done <= 1'b0;
  assign pready  = access ? (!slow || wait_done) : 1'b1;
  assign pslverr = access && pready && (!hit || (pwrite && ro));

  // writes commit in the last ACCESS cycle (PREADY high), honouring PSTRB
  wire wr_en = access && pready && pwrite && !pslverr;
  always_ff @(posedge pclk or negedge presetn)
    if (!presetn) begin ctrl <= '0; data <= '0; end
    else if (wr_en)
      for (int b = 0; b < 4; b++) if (pstrb[b]) begin
        if (paddr == A_CTRL) ctrl[8*b +: 8] <= pwdata[8*b +: 8];
        if (paddr == A_DATA) data[8*b +: 8] <= pwdata[8*b +: 8];
      end

  always_comb
    case (paddr)
      A_CTRL:  prdata = ctrl;
      A_STAT:  prdata = {24'h0, hw_status};
      A_DATA:  prdata = data;
      A_ID:    prdata = 32'hA9B0_0101;
      default: prdata = '0;
    endcase
endmodule''',
    'axil': r'''
module axil_regs #(parameter int N = 4) (          // N 32-bit RW registers
  input  logic        aclk, aresetn,
  // write address / write data / write response
  input  logic        awvalid, output logic awready, input logic [7:0] awaddr,
  input  logic        wvalid,  output logic wready,  input logic [31:0] wdata,
  input  logic [3:0]  wstrb,
  output logic        bvalid,  input  logic bready,  output logic [1:0] bresp,
  // read address / read data
  input  logic        arvalid, output logic arready, input logic [7:0] araddr,
  output logic        rvalid,  input  logic rready,  output logic [31:0] rdata,
  output logic [1:0]  rresp
);
  localparam logic [1:0] OKAY = 2'b00, SLVERR = 2'b10;
  logic [31:0] regs [N];
  // ---------------- write path: AW and W may arrive in any order ----------------
  logic       aw_full, w_full;          // one-entry skid holders
  logic [7:0] aw_q;  logic [31:0] w_q;  logic [3:0] s_q;
  assign awready = !aw_full;
  assign wready  = !w_full;
  wire   do_write = aw_full && w_full && (!bvalid || bready);   // B slot free
  wire   aw_ok    = (aw_q[7:2] < N) && (aw_q[1:0] == 2'b00);
  always_ff @(posedge aclk or negedge aresetn)
    if (!aresetn) begin
      aw_full <= 0; w_full <= 0; bvalid <= 0; bresp <= OKAY;
      aw_q <= '0; w_q <= '0; s_q <= '0;
      for (int i = 0; i < N; i++) regs[i] <= '0;
    end else begin
      if (awvalid && awready) begin aw_q <= awaddr; aw_full <= 1; end
      if (wvalid  && wready)  begin w_q  <= wdata;  s_q <= wstrb; w_full <= 1; end
      if (bvalid && bready) bvalid <= 0;
      if (do_write) begin
        if (aw_ok) for (int b = 0; b < 4; b++)
          if (s_q[b]) regs[aw_q[7:2]][8*b +: 8] <= w_q[8*b +: 8];
        bresp <= aw_ok ? OKAY : SLVERR;
        bvalid <= 1; aw_full <= 0; w_full <= 0;
      end
    end
  // ---------------- read path: one outstanding read --------------------------
  assign arready = !rvalid || rready;   // accept when R slot is (becoming) free
  always_ff @(posedge aclk or negedge aresetn)
    if (!aresetn) begin rvalid <= 0; rdata <= '0; rresp <= OKAY; end
    else if (arvalid && arready) begin
      rvalid <= 1;
      if ((araddr[7:2] < N) && (araddr[1:0] == 2'b00)) begin
        rdata <= regs[araddr[7:2]]; rresp <= OKAY;
      end else begin
        rdata <= 32'hDEAD_BEEF;     rresp <= SLVERR;
      end
    end else if (rvalid && rready) rvalid <= 0;
endmodule''',
    'cmux': r'''
// Glitch-free 2:1 clock mux for unrelated clocks (behavioural model; in silicon the
// AND/OR gates are hand-instantiated clock-gating/clock-mux cells, never inferred).
module clk_mux_gf (
  input  logic clk0, clk1, rst_n,
  input  logic sel,                 // asynchronous select: 0 -> clk0, 1 -> clk1
  output logic clk_out
);
  logic [1:0] s0, s1;               // per-domain 2-flop synchronizers
  logic       en0, en1;             // enable, changed only while its clock is low
  always_ff @(posedge clk0 or negedge rst_n)
    if (!rst_n) s0 <= 2'b11; else s0 <= {s0[0], ~sel & ~en1};
  always_ff @(negedge clk0 or negedge rst_n)
    if (!rst_n) en0 <= 1'b1; else en0 <= s0[1];
  always_ff @(posedge clk1 or negedge rst_n)
    if (!rst_n) s1 <= 2'b00; else s1 <= {s1[0],  sel & ~en0};
  always_ff @(negedge clk1 or negedge rst_n)
    if (!rst_n) en1 <= 1'b0; else en1 <= s1[1];
  assign clk_out = (clk0 & en0) | (clk1 & en1);
endmodule''',
    'csr': r'''
// Simple register interface (e.g. behind an APB/AXI-Lite adapter): 1-cycle access.
module irq_csr (
  input  logic        clk, rst_n,
  input  logic        req, we,
  input  logic [4:0]  addr,
  input  logic [31:0] wdata,
  output logic [31:0] rdata,          // valid in the cycle after req (registered)
  input  logic [3:0]  hw_event,       // 1-cycle event pulses from the hardware
  output logic [3:0]  ctrl,
  output logic        irq             // level interrupt to the interrupt controller
);
  localparam logic [4:0] CTRL = 5'h00, STATUS = 5'h04, ENABLE = 5'h08,
                         SET  = 5'h0C, EVTCNT = 5'h10;
  logic [3:0] status, enable;
  logic [7:0] evtcnt;
  wire wr = req &  we, rd = req & ~we;

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      ctrl <= '0; status <= '0; enable <= '0; evtcnt <= '0; rdata <= '0;
    end else begin
      if (wr && addr == CTRL)   ctrl   <= wdata[3:0];                    // RW
      if (wr && addr == ENABLE) enable <= wdata[3:0];                    // RW
      // STATUS: W1C from software, W1S via SET (test hook), set by hardware.
      // Hardware set has priority so an event in the clear cycle is never lost.
      status <= (status & ~((wr && addr == STATUS) ? wdata[3:0] : 4'h0))
                | ((wr && addr == SET) ? wdata[3:0] : 4'h0)
                | hw_event;
      // EVTCNT: RC - counts events, cleared by a read (side effect!)
      if (rd && addr == EVTCNT) evtcnt <= 8'(|hw_event);
      else if (|hw_event)       evtcnt <= evtcnt + 1'b1;
      // registered read mux
      if (rd)
        case (addr)
          CTRL:    rdata <= {28'h0, ctrl};
          STATUS:  rdata <= {28'h0, status};
          ENABLE:  rdata <= {28'h0, enable};
          EVTCNT:  rdata <= {24'h0, evtcnt};
          default: rdata <= '0;                                          // SET is WO
        endcase
    end
  assign irq = |(status & enable);
endmodule''',
    'hs': r'''
// 4-phase req/ack handshake: moves a W-bit word safely between unrelated clocks.
module hs_cdc #(parameter int W = 8) (
  input  logic         s_clk, s_rst_n,
  input  logic         s_valid,        // request to send s_data
  input  logic [W-1:0] s_data,
  output logic         s_ready,        // idle: may accept a new word
  input  logic         d_clk, d_rst_n,
  output logic         d_valid,        // 1-cycle strobe with d_data
  output logic [W-1:0] d_data
);
  logic         req, ack;            // control: each crosses through 2 flops
  // ---- source domain ----
  logic [W-1:0] hold;                // data: crosses UNsynchronized, stable while req=1
  logic [1:0]   ack_s;               // ack synchronized into s_clk
  assign s_ready = !req && !ack_s[1];
  always_ff @(posedge s_clk or negedge s_rst_n)
    if (!s_rst_n) begin req <= 0; hold <= '0; ack_s <= '0; end
    else begin
      ack_s <= {ack_s[0], ack};
      if (s_valid && s_ready) begin hold <= s_data; req <= 1; end
      else if (ack_s[1])      req  <= 0;               // phase 3: drop req
    end
  // ---- destination domain ----
  logic [1:0]   req_d;               // req synchronized into d_clk
  always_ff @(posedge d_clk or negedge d_rst_n)
    if (!d_rst_n) begin req_d <= '0; ack <= 0; d_valid <= 0; d_data <= '0; end
    else begin
      req_d   <= {req_d[0], req};
      d_valid <= 0;
      if (req_d[1] && !ack) begin d_data <= hold; d_valid <= 1; ack <= 1; end
      else if (!req_d[1])   ack <= 0;                  // phase 4: drop ack
    end
endmodule''',
    'psync': r'''
module pulse_sync (
  input  logic src_clk, src_rst_n, src_pulse,   // 1-cycle pulse in source domain
  input  logic dst_clk, dst_rst_n,
  output logic dst_pulse                        // 1-cycle pulse in destination domain
);
  logic src_tgl;                                // flips once per event
  always_ff @(posedge src_clk or negedge src_rst_n)
    if (!src_rst_n)     src_tgl <= 1'b0;
    else if (src_pulse) src_tgl <= ~src_tgl;

  logic [2:0] dst_sr;                           // 2 sync flops + 1 history flop
  always_ff @(posedge dst_clk or negedge dst_rst_n)
    if (!dst_rst_n) dst_sr <= '0;
    else            dst_sr <= {dst_sr[1:0], src_tgl};

  assign dst_pulse = dst_sr[2] ^ dst_sr[1];     // edge detect on synchronized toggle
endmodule''',
    'pwm': r'''
module pwm #(parameter int W = 8) (
  input  logic         clk, rst_n, en,
  input  logic [W-1:0] period,     // counter wraps at period  (PWM period = period+1 clks)
  input  logic [W-1:0] duty,       // output high while cnt < duty
  output logic         pwm_out,
  output logic         wrap        // 1-cycle pulse per period (e.g. timer interrupt)
);
  logic [W-1:0] cnt, duty_sh;      // duty is shadowed: updates only at period boundary
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin cnt <= '0; duty_sh <= '0; pwm_out <= 0; wrap <= 0; end
    else if (en) begin
      wrap <= (cnt == period);
      if (cnt == period) begin cnt <= '0; duty_sh <= duty; end
      else                cnt <= cnt + 1'b1;
      pwm_out <= (cnt == period) ? (duty != 0) : (cnt + 1'b1 < duty_sh);
    end else begin
      cnt <= '0; pwm_out <= 0; wrap <= 0;
    end
endmodule''',
    'rr': r'''
module rr_arb #(parameter int N = 4) (
  input  logic         clk, rst_n,
  input  logic [N-1:0] req,
  input  logic         advance,        // e.g. end of the granted transfer
  output logic [N-1:0] gnt             // one-hot (or zero)
);
  logic [N-1:0] mask;                  // 1s at positions ABOVE the last winner
  // fixed-priority (LSB wins) picker: x & -x isolates the lowest set bit
  function automatic logic [N-1:0] lsb1(input logic [N-1:0] x);
    return x & (~x + 1'b1);
  endfunction
  wire [N-1:0] req_m = req & mask;
  assign gnt = (req_m != 0) ? lsb1(req_m) : lsb1(req);
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) mask <= '1;
    else if (advance && gnt != 0)
      mask <= ~((gnt << 1) - 1'b1);    // all bits strictly above the one-hot winner
endmodule''',
    'rsync': r'''
// Asynchronous assert, synchronous de-assert reset synchronizer.
module rst_sync #(parameter int STAGES = 2) (
  input  logic clk,
  input  logic arst_n,        // raw asynchronous reset (pad, POR, reset controller)
  input  logic scan_mode,     // DFT: bypass so the tester controls reset directly
  input  logic scan_rst_n,
  output logic rst_n_out      // drives the async reset pins of this domain's flops
);
  (* ASYNC_REG = "TRUE" *) logic [STAGES-1:0] sr;
  always_ff @(posedge clk or negedge arst_n)
    if (!arst_n) sr <= '0;                        // assert immediately, no clock needed
    else         sr <= {sr[STAGES-2:0], 1'b1};    // release after STAGES clock edges
  assign rst_n_out = scan_mode ? scan_rst_n : sr[STAGES-1];
endmodule''',
    'spi': r'''
// SPI master, mode 0 (CPOL=0, CPHA=0), MSB first, 8-bit frames.
// SCLK = clk / (2*(DIV+1)).  MOSI changes on falling SCLK, MISO sampled on rising SCLK.
module spi_master #(parameter int DIV = 1) (
  input  logic       clk, rst_n,
  input  logic       start,             // pulse: begin a frame with tx_byte
  input  logic [7:0] tx_byte,
  output logic [7:0] rx_byte,
  output logic       busy, done,        // done: 1-cycle pulse at end of frame
  output logic       sclk, mosi, cs_n,
  input  logic       miso
);
  logic [$clog2(DIV+1)-1:0] div_cnt;
  logic [7:0] sh;                        // one shift register for TX and RX
  logic [3:0] bits;                      // rising edges still to come
  logic       miso_q;                    // sample taken on the rising edge
  wire        tick = (div_cnt == DIV);   // half-period elapsed
  assign mosi = sh[7];
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      div_cnt <= '0; sh <= '0; bits <= '0; busy <= 0; done <= 0;
      sclk <= 0; cs_n <= 1; rx_byte <= '0; miso_q <= 0;
    end else begin
      done <= 0;
      if (!busy) begin
        div_cnt <= '0;
        if (start) begin sh <= tx_byte; bits <= 4'd8; busy <= 1; cs_n <= 0; end
      end else begin
        div_cnt <= tick ? '0 : div_cnt + 1'b1;
        if (tick) begin
          if (!sclk && bits != 0) begin            // rising edge: sample MISO
            sclk <= 1; miso_q <= miso; bits <= bits - 1'b1;
          end else if (sclk) begin                 // falling edge: next MOSI bit out,
            sclk <= 0;                             // captured MISO bit in
            sh   <= {sh[6:0], miso_q};
          end
          if (!sclk && bits == 0) begin            // all 8 bits shifted: end frame
            busy <= 0; cs_n <= 1; done <= 1; rx_byte <= sh;
          end
        end
      end
    end
endmodule''',
    'sync': r'''
module sync_2ff #(parameter int W = 1, parameter logic [W-1:0] RST_VAL = '0) (
  input  logic         clk,
  input  logic         rst_n,
  input  logic [W-1:0] d_async,   // from another clock domain (quasi-static bits only!)
  output logic [W-1:0] q_sync
);
  (* ASYNC_REG = "TRUE" *) logic [W-1:0] meta;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin meta <= RST_VAL; q_sync <= RST_VAL; end
    else        begin meta <= d_async; q_sync <= meta;    end
endmodule''',
    'tb_afifo': r'''
module tb_afifo;
  logic wclk = 0, rclk = 0, rst_n = 0, winc = 0, rinc = 0, wfull, rempty;
  logic [7:0] wdata = 0, rdata, expect_v = 0;
  int nw = 0, nr = 0, errs = 0, full_seen = 0;
  always #5  wclk = ~wclk;                     // 100 MHz writer
  always #13 rclk = ~rclk;                     // ~38 MHz reader (unrelated)
  async_fifo #(.W(8), .AW(3)) dut (.*, .wrst_n(rst_n), .rrst_n(rst_n));
  // writer: tries to write every cycle, honours wfull
  always @(posedge wclk) if (rst_n) begin
    if (winc && !wfull) begin nw++; wdata <= wdata + 1; end
    if (wfull) full_seen++;
    winc <= (nw < 200);
  end
  // reader: random-ish throttling, checks order
  always @(posedge rclk) if (rst_n) begin
    if (rinc && !rempty) begin
      if (rdata !== expect_v) errs++;
      expect_v <= expect_v + 1; nr++;
    end
    rinc <= ($urandom % 4) != 0;
  end
  initial begin
    #40 rst_n = 1;
    wait (nr == 200);
    $display("written=%0d read=%0d order_errors=%0d wclk_cycles_full=%0d",
             nw, nr, errs, full_seen);
    $finish;
  end
endmodule''',
    'tb_apb': r'''
module tb_apb;
  logic pclk = 0, presetn = 0, psel = 0, penable = 0, pwrite = 0, pready, pslverr;
  logic [11:0] paddr = 0; logic [31:0] pwdata = 0, prdata, rd; logic [3:0] pstrb = 0;
  int cyc = 0;
  always #5 pclk = ~pclk;
  apb_regs dut (.*, .hw_status(8'h5A));
  always @(posedge pclk) begin
    cyc++;
    if (psel) begin
      string wd, rdat;
      wd = "--------"; rdat = "--------";
      if (pwrite)                        wd   = $sformatf("%h", pwdata);
      if (penable && pready && !pwrite)  rdat = $sformatf("%h", prdata);
      $display("%2d   %b   %b  %b  %h  %s %b   %s %b",
               cyc, psel, penable, pwrite, paddr, wd, pready, rdat, pslverr);
    end
  end
  task automatic apb(input bit wr, input [11:0] a, input [31:0] d, output [31:0] q);
    @(negedge pclk) begin psel = 1; penable = 0; pwrite = wr; paddr = a; pwdata = d;
                          pstrb = wr ? 4'hF : 4'h0; end            // SETUP phase
    @(negedge pclk) penable = 1;                                     // ACCESS phase
    @(posedge pclk); while (!pready) @(posedge pclk);                // wait states
    q = prdata;
    @(negedge pclk) begin psel = 0; penable = 0; end
  endtask
  initial begin
    $display("cyc SEL EN WR ADDR PWDATA   RDY PRDATA   ERR");
    #12 presetn = 1;
    apb(1, 12'h000, 32'h0000_0003, rd);      // write CTRL
    apb(0, 12'h000, 0, rd);                  // read CTRL
    apb(1, 12'h008, 32'hCAFE_F00D, rd);      // write DATA (1 wait state)
    apb(0, 12'h004, 0, rd);                  // read STATUS
    apb(1, 12'h00C, 32'h1234_5678, rd);      // write to read-only ID -> PSLVERR
    apb(0, 12'h010, 0, rd);                  // unmapped -> PSLVERR
    $finish;
  end
endmodule''',
    'tb_axil': r'''
module tb_axil;
  logic aclk = 0, aresetn = 0;
  logic awvalid = 0, awready, wvalid = 0, wready, bvalid, bready = 0;
  logic arvalid = 0, arready, rvalid, rready = 0;
  logic [7:0] awaddr = 0, araddr = 0; logic [31:0] wdata = 0, rdata; logic [3:0] wstrb = 0;
  logic [1:0] bresp, rresp;
  always #5 aclk = ~aclk;
  axil_regs dut (.*);
  // bounded "valid stays high until ready" protocol drivers
  task automatic send_aw(input [7:0] a);
    awaddr <= a; awvalid <= 1; do @(posedge aclk); while (!awready); awvalid <= 0;
  endtask
  task automatic send_w(input [31:0] d, input [3:0] s);
    wdata <= d; wstrb <= s; wvalid <= 1; do @(posedge aclk); while (!wready); wvalid <= 0;
  endtask
  task automatic get_b(input int stall);
    repeat (stall) @(posedge aclk);                   // master back-pressure on B
    bready <= 1; do @(posedge aclk); while (!bvalid); bready <= 0;
    $display("t=%0t  B  bresp=%b", $time, bresp);
  endtask
  task automatic read(input [7:0] a);
    araddr <= a; arvalid <= 1; do @(posedge aclk); while (!arready); arvalid <= 0;
    rready <= 1; do @(posedge aclk); while (!rvalid); rready <= 0;
    $display("t=%0t  R  addr=%h rdata=%h rresp=%b", $time, a, rdata, rresp);
  endtask
  initial begin
    repeat (2) @(posedge aclk); aresetn <= 1; @(posedge aclk);
    fork send_aw(8'h04); send_w(32'h1122_3344, 4'hF); get_b(0); join   // together
    fork send_w(32'hAABB_CCDD, 4'b0011); get_b(3);                      // W first,
         begin repeat (4) @(posedge aclk); send_aw(8'h04); end join     // AW late
    fork send_aw(8'h40); send_w(32'h0, 4'hF); get_b(0); join           // bad address
    read(8'h04);
    read(8'h41);
    $finish;
  end
endmodule''',
    'tb_cmux': r'''
module tb_cmux;
  logic c0 = 0, c1 = 0, rst_n = 0, sel = 0, co;
  realtime t_edge = 0, min_hi = 1e9, min_lo = 1e9;
  always #5 c0 = ~c0;                       // 10 ns period: phases of 5 ns
  always #7 c1 = ~c1;                       // 14 ns period: phases of 7 ns
  clk_mux_gf u (.clk0(c0), .clk1(c1), .rst_n, .sel, .clk_out(co));
  always @(co) if (rst_n && $realtime > 30) begin
    if (co == 0 && $realtime - t_edge < min_hi) min_hi = $realtime - t_edge;
    if (co == 1 && $realtime - t_edge < min_lo) min_lo = $realtime - t_edge;
    t_edge = $realtime;
  end
  initial begin
    #23 rst_n = 1;
    repeat (20) begin
      #($urandom_range(80, 200)) sel = ~sel;   // switch at random times
    end
    #200 $display("switches=20  shortest high=%0.1f ns  shortest low=%0.1f ns",
                  min_hi, min_lo);
    $finish;
  end
endmodule''',
    'tb_csr': r'''
module tb_csr;
  logic clk = 0, rst_n = 0, req = 0, we = 0, irq;
  logic [4:0] addr = 0; logic [31:0] wdata = 0, rdata; logic [3:0] ev = 0, ctrl;
  always #5 clk = ~clk;
  irq_csr dut (.clk, .rst_n, .req, .we, .addr, .wdata, .rdata, .hw_event(ev), .ctrl, .irq);
  task automatic wr(input [4:0] a, input [31:0] d);
    @(negedge clk) begin req = 1; we = 1; addr = a; wdata = d; end
    @(negedge clk) req = 0;
  endtask
  task automatic rd(input [4:0] a, input string name);
    @(negedge clk) begin req = 1; we = 0; addr = a; end
    @(negedge clk) begin req = 0; $display("%-7s = %h   irq=%b", name, rdata, irq); end
  endtask
  task automatic pulse(input [3:0] e);
    @(negedge clk) ev = e; @(negedge clk) ev = 0;
  endtask
  initial begin
    #12 rst_n = 1;
    wr(5'h08, 32'h5);               // enable sources 0 and 2
    pulse(4'b0010);                 // source 1 fires (masked)
    rd(5'h04, "STATUS");
    pulse(4'b0100);                 // source 2 fires (enabled) -> irq
    rd(5'h04, "STATUS");
    wr(5'h04, 32'h4);               // W1C: clear bit 2 only
    rd(5'h04, "STATUS");
    // race: software clears bit 1 in the same cycle hardware sets it again
    @(negedge clk) begin req = 1; we = 1; addr = 5'h04; wdata = 32'h2; ev = 4'b0010; end
    @(negedge clk) begin req = 0; ev = 0; end
    rd(5'h04, "STATUS");
    rd(5'h10, "EVTCNT");
    rd(5'h10, "EVTCNT");            // read-to-clear: second read returns 0
    $finish;
  end
endmodule''',
    'tb_hs': r'''
module tb_hs;
  logic sclk = 0, dclk = 0, rst_n = 0, sv = 0, sr, dv;
  logic [7:0] sd = 0, dd;
  int errs = 0, n = 0;
  always #3 sclk = ~sclk;
  always #8 dclk = ~dclk;
  hs_cdc u (.s_clk(sclk), .s_rst_n(rst_n), .s_valid(sv), .s_data(sd), .s_ready(sr),
            .d_clk(dclk), .d_rst_n(rst_n), .d_valid(dv), .d_data(dd));
  always @(posedge dclk) if (dv) begin
    if (dd != 8'h10 + n) errs++;
    n++;
  end
  initial begin
    #30 rst_n = 1;
    for (int i = 0; i < 6; i++) begin
      @(posedge sclk); while (!sr) @(posedge sclk);
      sv <= 1; sd <= 8'h10 + i;
      @(posedge sclk); sv <= 0;
    end
    repeat (20) @(posedge dclk);
    $display("words received=%0d errors=%0d last=%h at t=%0t", n, errs, dd, $time);
    $finish;
  end
endmodule''',
    'tb_psync': r'''
module tb_psync;
  logic sclk = 0, dclk = 0, rst_n = 0, sp = 0;
  logic dp;
  int   sent = 0, got = 0;
  always #2  sclk = ~sclk;   // 250 MHz source
  always #7  dclk = ~dclk;   // ~71 MHz destination
  pulse_sync u (.src_clk(sclk), .src_rst_n(rst_n), .src_pulse(sp),
                .dst_clk(dclk), .dst_rst_n(rst_n), .dst_pulse(dp));
  always @(posedge dclk) if (dp) got++;
  initial begin
    #20 rst_n = 1;
    repeat (5) begin                       // events spaced >= 3 dst cycles apart
      @(posedge sclk) sp <= 1; sent++;
      @(posedge sclk) sp <= 0;
      repeat (12) @(posedge sclk);
    end
    repeat (10) @(posedge dclk);
    $display("sent=%0d received=%0d", sent, got);
    $finish;
  end
endmodule''',
    'tb_pwm': r'''
module tb_pwm;
  logic clk = 0, rst_n = 0, en = 0, o, wrap;
  logic [7:0] duty = 3;
  string s = "";
  always #5 clk = ~clk;
  pwm #(.W(8)) dut (.clk, .rst_n, .en, .period(8'd9), .duty, .pwm_out(o), .wrap);
  initial begin
    #12 rst_n = 1; en = 1;
    @(posedge wrap) #1;                                   // first cycle of a period
    for (int i = 1; i <= 30; i++) begin
      s = {s, o ? "#" : "_"};
      if (i % 10 == 0) s = {s, " "};                      // one period per group
      if (i == 15) duty = 7;                              // change duty mid-period
      @(posedge clk) #1;
    end
    $display("pwm_out: %s", s);
    $finish;
  end
endmodule''',
    'tb_rr': r'''
module tb_rr;
  logic clk = 0, rst_n = 0; logic [3:0] req = 0, gnt, g;
  int cnt [4], wait_c [4], worst = 0, bad = 0;
  always #5 clk = ~clk;
  rr_arb #(.N(4)) dut (.clk, .rst_n, .req, .advance(1'b1), .gnt);
  initial begin
    foreach (cnt[i]) begin cnt[i] = 0; wait_c[i] = 0; end
    #12 rst_n = 1;
    req = 4'b1111;
    repeat (6) @(posedge clk) #1 $display("req=%b gnt=%b", req, gnt);
    // random traffic: a requester keeps its request until granted
    repeat (2000) begin
      @(posedge clk) g = gnt;                // the grant this edge commits
      #1;
      if ($countones(g) > 1 || (g & ~req) != 0) bad++;
      for (int i = 0; i < 4; i++) begin
        if (g[i]) begin cnt[i]++; wait_c[i] = 0; req[i] = $urandom % 2; end
        else if (req[i]) begin wait_c[i]++; if (wait_c[i] > worst) worst = wait_c[i]; end
        else req[i] = $urandom % 2;
      end
    end
    $display("grants=%0d/%0d/%0d/%0d  worst wait=%0d cycles  protocol errors=%0d",
             cnt[0], cnt[1], cnt[2], cnt[3], worst, bad);
    $finish;
  end
endmodule''',
    'tb_rsync': r'''
module tb_rsync;
  logic clk = 0, arst_n = 1, rn;
  always #5 clk = ~clk;
  rst_sync u (.clk, .arst_n, .scan_mode(1'b0), .scan_rst_n(1'b1), .rst_n_out(rn));
  initial begin
    $monitor("t=%3t arst_n=%b sr=%b rst_n_out=%b", $time, arst_n, u.sr, rn);
    #13 arst_n = 0;          // assert between edges -> output drops at once
    #24 arst_n = 1;          // release at t=37, between edges
    #40 $finish;
  end
endmodule''',
    'tb_spi': r'''
module tb_spi;
  logic clk = 0, rst_n = 0, start = 0, busy, done, sclk, mosi, cs_n, miso;
  logic [7:0] tx = 0, rx, slave_tx, slave_rx;
  always #5 clk = ~clk;
  spi_master #(.DIV(1)) dut (.clk, .rst_n, .start, .tx_byte(tx), .rx_byte(rx),
                              .busy, .done, .sclk, .mosi, .cs_n, .miso);
  // behavioural mode-0 SPI slave: drive on falling edge / CS fall, sample on rising
  logic [7:0] sreg;
  assign miso = cs_n ? 1'bz : sreg[7];
  always @(negedge cs_n) sreg = slave_tx;
  always @(posedge sclk) if (!cs_n) slave_rx = {slave_rx[6:0], mosi};
  always @(negedge sclk) if (!cs_n) sreg = {sreg[6:0], 1'b0};
  task automatic xfer(input [7:0] m, input [7:0] s);
    slave_tx = s;
    @(negedge clk) begin tx = m; start = 1; end
    @(negedge clk) start = 0;
    @(posedge done);
    #1 $display("master sent %h, slave got %h | slave sent %h, master got %h",
                m, slave_rx, s, rx);
  endtask
  initial begin
    #12 rst_n = 1;
    xfer(8'h3C, 8'hA5);
    xfer(8'h81, 8'h7E);
    $finish;
  end
endmodule''',
    'tb_sync': r'''
module tb_sync;
  logic clk = 0, rst_n = 0, a = 0;
  logic q;
  always #5 clk = ~clk;                       // 100 MHz destination clock
  sync_2ff u (.clk, .rst_n, .d_async(a), .q_sync(q));
  initial begin
    #12 rst_n = 1;
    #21 a = 1;                                // changes at t=33, between edges
    repeat (4) @(posedge clk) #1 $display("t=%0t a=%b meta=%b q=%b", $time, a, u.meta, q);
    $finish;
  end
endmodule''',
}

OUT = {
    'sync': ['t=36 a=1 meta=1 q=0', 't=46 a=1 meta=1 q=1', 't=56 a=1 meta=1 q=1', 't=66 a=1 meta=1 q=1'],
    'psync': ['sent=5 received=5'],
    'hs': ['words received=6 errors=0 last=15 at t=936'],
    'afifo': ['written=200 read=200 order_errors=0 wclk_cycles_full=429'],
    'cmux': ['switches=20  shortest high=5.0 ns  shortest low=5.0 ns'],
    'cmux_fast': ['switches=20  shortest high=5.0 ns  shortest low=1.0 ns'],
    'rsync': ['t=  0 arst_n=1 sr=xx rst_n_out=x', 't=  5 arst_n=1 sr=x1 rst_n_out=x', 't= 13 arst_n=0 sr=00 rst_n_out=0', 't= 37 arst_n=1 sr=00 rst_n_out=0', 't= 45 arst_n=1 sr=01 rst_n_out=0', 't= 55 arst_n=1 sr=11 rst_n_out=1'],
    'apb': ['cyc SEL EN WR ADDR PWDATA   RDY PRDATA   ERR', ' 3   1   0  1  000  00000003 1   -------- 0', ' 4   1   1  1  000  00000003 1   -------- 0', ' 6   1   0  0  000  -------- 1   -------- 0', ' 7   1   1  0  000  -------- 1   00000003 0', ' 9   1   0  1  008  cafef00d 1   -------- 0', '10   1   1  1  008  cafef00d 0   -------- 0', '11   1   1  1  008  cafef00d 1   -------- 0', '13   1   0  0  004  -------- 1   -------- 0', '14   1   1  0  004  -------- 1   0000005a 0', '16   1   0  1  00c  12345678 1   -------- 0', '17   1   1  1  00c  12345678 1   -------- 1', '19   1   0  0  010  -------- 1   -------- 0', '20   1   1  0  010  -------- 1   00000000 1'],
    'axil': ['t=55  B  bresp=00', 't=125  B  bresp=00', 't=155  B  bresp=10', 't=175  R  addr=04 rdata=1122ccdd rresp=00', 't=195  R  addr=41 rdata=deadbeef rresp=10'],
    'rr': ['req=1111 gnt=0010', 'req=1111 gnt=0100', 'req=1111 gnt=1000', 'req=1111 gnt=0001', 'req=1111 gnt=0010', 'req=1111 gnt=0100', 'grants=504/501/507/485  worst wait=3 cycles  protocol errors=0'],
    'csr': ['STATUS  = 00000002   irq=0', 'STATUS  = 00000006   irq=1', 'STATUS  = 00000002   irq=0', 'STATUS  = 00000002   irq=0', 'EVTCNT  = 00000003   irq=0', 'EVTCNT  = 00000000   irq=0'],
    'spi': ['master sent 3c, slave got 3c | slave sent a5, master got a5', 'master sent 81, slave got 81 | slave sent 7e, master got 7e'],
    'pwm': ['pwm_out: ###_______ ###_______ #######___ '],
}


def _v(name, caption=None):
    """Show a verified Verilog/SystemVerilog source from SRC."""
    code(SRC[name].split("\n"), caption)


def _o(name, caption=None):
    """Show the real vvp output captured for a testbench."""
    out(OUT[name], caption)


# =============================================================================
#                   PART III - SOC ARCHITECTURE IN RTL
# =============================================================================
def part3():
    part("SoC Architecture in RTL",
         "Part II built blocks that live inside one clock domain. A real "
         "system-on-chip has dozens of clocks, several reset domains, a "
         "hierarchy of buses and an interconnect joining processors, "
         "accelerators, memories and peripherals. This part is about the "
         "glue: crossing clock and reset domains safely, speaking the AMBA "
         "protocols (APB, AHB, AXI), building arbiters, memory maps and "
         "networks-on-chip, specifying registers and interrupts, and "
         "integrating peripherals, DMA and a RISC-V core into a working SoC.")
    _ch11()
    _ch12()
    _ch13()
    _ch14()
    _ch15()
    _ch16()


# ---------------------------------------------------------------- Ch 11 ---
def _ch11():
    chapter("Clocks and Clock-Domain Crossing", newpage=False)
    p("Every flop in Part II shared one clock, so every path had a full, "
      "known period to settle and static timing analysis (Chapter 18) could "
      "prove it correct. Put two clocks on a chip whose edges bear no fixed "
      "relationship and that guarantee disappears for every signal that "
      "passes between them. Sooner or later such a signal changes inside a "
      "receiving flop's setup/hold window, and the flop goes **metastable**. "
      "Clock-domain crossing (CDC) design is the discipline of making that "
      "event harmless. CDC bugs are the classic silicon escape: they pass "
      "every RTL simulation, show up as a one-in-a-week field failure, and "
      "cost a respin. That is why CDC sign-off (Chapter 25) is mandatory on "
      "every SoC tapeout.")

    h2("Where clocks come from")
    p("A modern SoC typically has one or two crystal references (for "
      "example 24 MHz or 38.4 MHz) and derives everything else on chip:")
    tbl(["Source", "What it does", "RTL designer's concern"],
        [["**PLL / FLL**", "Multiplies a reference: f_out = f_ref x N / (M x P). "
          "Low jitter, needs lock time (tens of us)", "Nothing is clocked until "
          "`pll_lock`; the reset controller waits for it (Chapter 12)"],
         ["**Integer divider**", "Counter/toggle flop producing f/2, f/4, ...; "
          "usually related (synchronous) to its source", "Must be a **generated "
          "clock** in SDC; never build it from arbitrary logic"],
         ["**Clock mux**", "Selects between sources (PLL vs. reference, "
          "low-power clock)", "A plain mux glitches when switching; use a "
          "glitch-free mux (Section 11.10)"],
         ["**Clock gate (ICG)**", "Latch + AND cell that stops the clock to "
          "idle logic", "Instantiate the library ICG; never AND a clock with "
          "a flop output (Chapter 19)"],
         ["**External / recovered clocks**", "JTAG TCK, SPI SCLK, PHY RX "
          "clocks, audio MCLK", "Fully asynchronous to everything on chip"]],
        widths=[20, 42, 38], bold_first=True)
    box("warn", "PITFALL: clocks made in RTL",
        "Writing `assign clk_div2 = cnt[0];` and using it as a clock, or "
        "`assign gclk = clk & en;`, creates a clock that STA cannot reason "
        "about, glitches on enable changes, and skews against its source. "
        "Rule: clocks are produced only by dedicated, instantiated cells "
        "(PLL, ICG, clock mux, divider flop marked as a generated clock) in a "
        "small, reviewed clock-generation module, and everything else uses "
        "**clock enables** (Chapter 6).")

    h2("How two clocks can be related")
    tbl(["Relationship", "Definition", "Example", "Crossing technique"],
        [["Synchronous", "Same source, fixed integer ratio and phase; STA "
          "times the paths", "clk and clk/2 from one PLL",
          "None needed - normal timing, maybe multicycle constraints"],
         ["Mesochronous", "Same frequency, unknown but constant phase",
          "Same PLL distributed over a large die without balancing",
          "Small FIFO or phase-detect retiming"],
         ["Plesiochronous", "Nominally equal frequency, slightly different "
          "(ppm)", "Two Ethernet ports on separate crystals",
          "Async FIFO with elastic buffering / rate adaptation"],
         ["**Asynchronous**", "No relationship at all", "CPU PLL vs. USB PHY "
          "clock", "Synchronizers, handshakes, async FIFOs"]],
        widths=[16, 30, 26, 28], bold_first=True)
    p("In practice, unless two clocks come from the same source with a "
      "guaranteed ratio **and** the paths between them are timed by STA, "
      "treat them as asynchronous. The SDC then declares them in different "
      "clock groups (`set_clock_groups -asynchronous`) and STA stops timing "
      "those paths - which is exactly why the RTL must make them safe by "
      "construction.")

    h2("Metastability and MTBF")
    p("A flop is a bistable loop. If its input changes inside the "
      "setup/hold aperture, the loop can be left balanced near the midpoint "
      "voltage, and it resolves to 0 or 1 only after a random, "
      "exponentially-distributed time. Metastability cannot be prevented; "
      "it can only be given enough time to resolve before anyone looks at "
      "the value. The standard model gives the mean time between failures:")
    eq(["MTBF = exp(t_r / tau) / (T_0 x f_clk x f_data)",
        "",
        "t_r    = resolution time available = T_clk - t_setup - t_clk->q (- logic delay)",
        "tau    = regeneration time constant of the flop (process/cell dependent, ~10 ps)",
        "T_0    = effective metastability window (~tens of ps, from the library)",
        "f_clk  = receiving clock frequency;  f_data = toggle rate of the async input"],
       "Resolution time is in the exponent. Every extra picosecond of slack "
       "multiplies MTBF; every extra gate after the first flop divides it.")
    p("Put numbers in: `tau` = 12 ps, `T_0` = 20 ps, a 1 GHz receiving clock "
      "and data toggling at 100 MHz, so the denominator is 2 x 10^{6} per "
      "second.")
    tbl(["Design", "t_r", "MTBF"],
        [["One flop, then 800 ps of logic", "200 ps", "about **8.7 seconds**"],
         ["Two flops back-to-back (2FF synchronizer)", "900 ps",
          "about 1.9 x 10^{26} s (6 x 10^{18} years)"],
         ["Three flops", "1800 ps", "about 7 x 10^{58} s"]],
        widths=[46, 16, 38], bold_first=True)
    box("math", "Why the second flop is enough (usually)",
        "The first flop may go metastable; the second flop samples it one "
        "full period later, by which time the probability that it has not "
        "resolved is exp(-t_r/tau) - astronomically small. Note the system "
        "MTBF is the per-synchronizer MTBF divided by the number of "
        "synchronizers: 10 000 synchronizers on a chip shipped in 10 million "
        "units need each one to be very, very good. At high frequencies (>1 "
        "GHz) or on older/low-voltage processes where `tau` grows, designs "
        "use 3 stages. The library team, not the RTL designer, provides "
        "`tau` and `T_0`.")

    h2("The two-flop synchronizer")
    p("The workhorse for a **single, slowly changing control bit**: an "
      "enable, a mode bit, a level interrupt, a status flag.")
    _v("sync", "`sync_2ff`: the basic synchronizer. The `ASYNC_REG` "
       "attribute (Vivado) keeps the flops adjacent and excluded from "
       "retiming; ASIC flows use a dedicated synchronizer cell instead.")
    diagram([
        "  src_clk domain         |            dst_clk domain",
        "                         |",
        "  +-----+   d_async      |   +-----+  meta   +-----+   q_sync",
        "  | FF  |----------------+-->| FF1 |-------->| FF2 |-----------> logic",
        "  +--^--+    NO logic     |   +--^--+ NO logic +--^--+",
        "     |       between      |      |   no fanout    |",
        "  src_clk    src FF & FF1 |   dst_clk ---------+--+",
    ], "Rules encoded in this picture: the source is a **flop** (no "
       "combinational glitches can be caught), there is **no logic** between "
       "domains, FF1 feeds only FF2, and the two flops sit next to each other.")
    _v("tb_sync")
    _o("sync", "The async input rises at t=33; `meta` captures it at the edge "
       "at t=35 and `q_sync` follows one cycle later at t=45 - a latency of "
       "1 to 2 destination cycles depending on where the change lands.")
    box("warn", "PITFALL: logic in front of the synchronizer",
        "`sync_2ff u(.d_async(a & b), ...)` with `a` and `b` from the source "
        "domain looks harmless, but the AND can **glitch** when both inputs "
        "change, and the synchronizer can catch the glitch - a pulse that "
        "never existed in the source domain. Always register the value in "
        "the source domain and send the flop output across.")

    h2("What must never cross unsynchronized")
    bul(["**Any single-bit control signal** feeding logic in another domain "
         "(enables, valids, requests, interrupts, FSM inputs).",
         "**Multi-bit buses**, even through individual 2FF synchronizers: "
         "each bit resolves independently, so a counter going 0111 -> 1000 "
         "can be seen as 1111 or 0000 for a cycle (Section 11.8).",
         "**Short pulses** from a faster domain: a 1-cycle pulse at 400 MHz "
         "may fall entirely between two 100 MHz edges and be missed.",
         "**Reset de-assertion**: the edge that releases reset is an "
         "asynchronous event for the flops it reaches (Chapter 12).",
         "**Clock-gating enables** and **clock-mux selects**: these must be "
         "synchronized to the clock they gate or select.",
         "The exception: **quasi-static** configuration registers written "
         "once while the destination is idle or in reset may be marked "
         "static - but that is a documented CDC waiver, not a default."])

    h2("Pulse (toggle) synchronizer")
    p("To send an **event** rather than a level, convert it to a level "
      "change in the source domain, synchronize the level, and detect the "
      "change in the destination:")
    _v("psync", "Toggle-based pulse synchronizer: each source pulse flips "
       "`src_tgl`; the destination edge-detects the synchronized toggle.")
    _v("tb_psync")
    _o("psync")
    box("key", "The pulse synchronizer's contract",
        "Events must be spaced at least ~2-3 **destination** clock cycles "
        "apart; two pulses closer than that flip the toggle twice and the "
        "destination sees nothing. If the source can burst faster, either "
        "add feedback (a busy/ack back to the source) or use an async FIFO. "
        "Unlike a direct pulse, the toggle works from fast to slow domains "
        "because a level cannot be missed.")

    h2("Request/acknowledge handshake")
    p("The four-phase handshake moves a **multi-bit word** with only two "
      "synchronized control bits. The data sits in a source-domain register "
      "that is held stable for the whole transfer, so the destination can "
      "sample it directly - it was stable long before `req` got through the "
      "synchronizer.")
    diagram([
        "  phase:      1 req=1     2 ack=1      3 req=0      4 ack=0",
        "  req  ______/~~~~~~~~~~~~~~~~~~~~~~~~\\___________________________",
        "  ack  _________________/~~~~~~~~~~~~~~~~~~~~~~~~~\\_______________",
        "  data ==X=== stable =====================================X=========",
        "          ^ load hold           ^ dst samples hold   ^ src idle again",
    ], "Four-phase (return-to-zero) handshake. Each phase costs two "
       "synchronizer delays, so a transfer takes ~4-6 cycles of the slower "
       "clock: great for configuration and status, too slow for streaming.")
    _v("hs", "`hs_cdc`: `req` and `ack` are the only synchronized signals; "
       "`hold` crosses unsynchronized but is guaranteed stable when sampled. "
       "CDC tools recognise this as a 'data held by control' scheme.")
    _v("tb_hs")
    _o("hs")
    p("A **two-phase** (non-return-to-zero) variant treats every toggle of "
      "`req` as a new request and every toggle of `ack` as its completion; it "
      "halves the latency at the cost of XOR-based edge detection on both "
      "sides - the same trick as the toggle synchronizer.")

    h2("Multi-bit crossings and reconvergence")
    p("Passing a bus through per-bit synchronizers fails because the bits "
      "resolve independently: with skew and metastability, the destination "
      "may see a mixture of old and new bits for a cycle - a value that "
      "never existed. The same hazard appears in a subtler form called "
      "**reconvergence**: two separately synchronized signals that are "
      "combined later (for example `valid` and `mode`, each through its own "
      "2FF) can arrive a cycle apart, so logic that relies on their "
      "relationship sees an impossible combination.")
    tbl(["Technique", "Use when", "How it keeps the value coherent"],
        [["**Gray code + 2FF per bit**", "Counters / pointers that change by "
          "+-1", "Only one bit changes per step, so a mis-sample yields "
          "either the old or the new value, both legal"],
         ["**Handshake (req/ack)**", "Occasional words, config, status",
          "Data held stable; only one control bit crosses"],
         ["**MUX recirculation (data-enable)**", "A bus with a qualifying "
          "valid", "Synchronize only the valid; use it to load the bus into "
          "a destination register (below)"],
         ["**Async FIFO**", "Streaming data, bursts",
          "Gray-coded pointers + dual-port memory"],
         ["**Single synchronized control, derived locally**",
          "Several related control bits", "Encode them in the source into one "
          "bit or a Gray-coded state, then decode after synchronizing"]],
        widths=[28, 26, 46], bold_first=True)
    code([
        "// MUX-recirculation (enable-based) synchronizer: only 'load' is synchronized.",
        "// 'bus' must be held stable by the source from before load toggles until",
        "// the destination has captured it (typically guaranteed by a handshake).",
        "always_ff @(posedge dst_clk)",
        "  if (load_pulse_dst) bus_dst <= bus_src;   // else recirculate (hold)",
    ], "The mux in front of `bus_dst` recirculates its value until the "
       "synchronized enable arrives; all bus bits are sampled on the same edge "
       "long after they settled.")

    h2("The asynchronous FIFO")
    p("The async FIFO is the standard answer for streaming data between "
      "unrelated clocks. The memory is a dual-port RAM written in the write "
      "domain and read in the read domain. The only things that cross are "
      "the **pointers**, and they cross in **Gray code**, so each "
      "synchronized pointer is always either current or slightly stale - "
      "never garbage. A stale pointer is always **conservative**: the writer "
      "may think the FIFO is fuller than it is, and the reader may think it "
      "is emptier, but neither can overflow or underflow.")
    diagram([
        "        write domain (wclk)                        read domain (rclk)",
        "  winc -->+-------+  wbin  +-------------------+  rbin +-------+<-- rinc",
        "  wdata ->| wptr  |------->|  dual-port RAM    |<------| rptr  |",
        "          | logic |        |  2^AW x W         |------>| logic |--> rdata",
        "  wfull <-|       |        +-------------------+       |       |--> rempty",
        "          +-------+ wgray -------> 2FF sync ---------->|       |",
        "          |       |<------ 2FF sync <---------- rgray  +-------+",
        "          +-------+",
    ], "Pointers are N+1 bits (AW address bits plus a wrap bit). Each side "
       "compares its own pointer with the synchronized Gray pointer of the "
       "other side.")
    tbl(["Flag", "Computed in", "Condition (Gray pointers, AW+1 bits)"],
        [["empty", "read domain", "`rgray_next == wgray_synced` - identical, "
          "including the wrap bit"],
         ["full", "write domain", "`wgray_next == {~rgray_synced[AW:AW-1], "
          "rgray_synced[AW-2:0]}` - top two bits inverted, rest equal "
          "(the binary pointers differ by exactly the depth)"]],
        widths=[12, 16, 72], bold_first=True)
    _v("afifo", "A Cummings-style asynchronous FIFO. Flags are registered "
       "from the **next** pointer so they are glitch-free and assert in the "
       "same cycle as the pointer update.")
    _v("tb_afifo", "The testbench runs a 100 MHz writer against a ~38 MHz "
       "reader that randomly stalls, so the FIFO fills and throttles the "
       "writer hundreds of times.")
    _o("afifo", "Real run: 200 words through an 8-deep FIFO across two "
       "unrelated clocks, in order, with the full flag exercised 429 times.")
    box("warn", "PITFALLS in async FIFOs",
        "(1) Synchronizing the **binary** pointer: several bits change at "
        "once, so the far side can see a wildly wrong count. (2) Gray-coding "
        "a pointer through **combinational** logic and sending that across - "
        "the encoder output can glitch; the Gray pointer must come straight "
        "from a flop (`wgray` here). (3) Non-power-of-two depths break the "
        "single-bit-change property unless you use a special Gray sequence. "
        "(4) Reading `rdata` from the RAM is a timing path from the write "
        "clock's memory to the read clock - it is safe because the reader only "
        "looks at entries whose write completed two synchronizer delays ago; "
        "constrain it with `set_max_delay -datapath_only`, not a false path.")
    box("expert", "Sizing an async FIFO",
        "Depth must cover the **round-trip latency** of the flags (about 2 "
        "synchronizer delays + 1-2 cycles each way) plus the largest burst "
        "that can arrive while the reader is slower: for a burst of B words "
        "written at f_w and read at f_r < f_w, at least B x (1 - f_r/f_w) + "
        "the latency slack. Interviewers love this calculation.")

    h2("Glitch-free clock multiplexing")
    p("Switching a clock with an ordinary mux can produce a runt pulse "
      "shorter than either clock's high or low phase, which violates the "
      "minimum pulse width of every flop downstream. The glitch-free mux "
      "disables the old clock on its falling edge, waits until that is "
      "known in the new clock's domain, and only then enables the new clock, "
      "also on a falling edge.")
    _v("cmux", "Cross-coupled glitch-free clock mux. Each enable is "
       "synchronized in its own domain and updated on the falling edge, so "
       "the AND gates only open or close while their clock is low.")
    _v("tb_cmux", "The testbench measures the shortest high and low phase "
       "at the output while toggling `sel` at random times.")
    _o("cmux", "With `sel` held for at least 80 ns between switches, no "
       "phase is shorter than the source clocks' own 5 ns: no glitches.")
    p("Now shorten the hold time to 5-30 ns by changing the range to "
      "`$urandom_range(5, 30)` and run again:")
    _o("cmux_fast", "A 1 ns runt pulse. The select changed back before the "
       "previous switch completed, so both enables were briefly on.")
    box("key", "Clock-mux contract",
        "A glitch-free mux needs **both clocks running** while it switches "
        "(a dead clock can never release its enable - real designs add a "
        "clock-fail override), and `sel` must be held stable until the switch "
        "completes (about 3 cycles of each clock). In silicon the gating is "
        "done by library clock-mux/ICG cells, and the RTL module is written "
        "once, reviewed and reused everywhere.")

    h2("Summary")
    bul(["Treat any clocks not timed together by STA as asynchronous; STA "
         "will ignore those paths, so correctness must be by construction.",
         "Metastability is unavoidable; MTBF grows exponentially with "
         "resolution time. A 2FF synchronizer with no logic between stages "
         "is the baseline; 3 stages at very high frequencies.",
         "Single-bit levels: 2FF. Events: toggle/pulse synchronizer. "
         "Occasional words: req/ack handshake or MUX recirculation. Streams: "
         "async FIFO with Gray pointers.",
         "Never synchronize a multi-bit binary value bit-by-bit, never put "
         "combinational logic in front of a synchronizer, and watch for "
         "reconvergence of separately synchronized signals.",
         "Clock generation, gating and muxing use instantiated cells in a "
         "dedicated module; the glitch-free mux needs both clocks alive and "
         "a stable select."])

    h2("Exercises")
    bul(["Recompute the MTBF table for a 2 GHz receiving clock with the same "
         "`tau` and `T_0`. How many synchronizer stages do you need for an "
         "MTBF above 10^{9} years across 5 000 synchronizers?",
         "Modify `pulse_sync` to return a `busy` signal to the source that "
         "stays high until the event has been seen in the destination. "
         "Simulate back-to-back source pulses.",
         "Prove (by enumerating all 16 values) that a 4-bit Gray counter "
         "changes exactly one bit per increment including the wrap, and show "
         "why a 6-entry Gray sequence built from the first 6 codes does not.",
         "Add `wr_count` (write-domain fill level) to `async_fifo`. Which "
         "pointer must be converted from Gray back to binary, and where?",
         "In `hs_cdc`, what happens if the source changes `s_data` while "
         "`req` is high? Why is `hold` needed instead of using `s_data` "
         "directly?",
         "A 1 GHz source sends 200-cycle bursts into a 600 MHz reader. "
         "Estimate the minimum async FIFO depth."], ordered=True)


# ---------------------------------------------------------------- Ch 12 ---
def _ch12():
    chapter("Reset Architecture and RDC")
    p("Chapter 6 covered the flop-level choice between synchronous and "
      "asynchronous reset. At the SoC level, reset is a **system**: several "
      "sources, a controller that sequences them, a distribution network as "
      "large as a clock tree, and domains that can be reset independently "
      "while their neighbours keep running. That last property creates a "
      "failure class of its own - **reset-domain crossing (RDC)** - which "
      "is invisible to both functional simulation and ordinary CDC analysis.")

    h2("Kinds of reset in an SoC")
    tbl(["Reset", "Trigger", "Scope", "Notes"],
        [["**Power-on reset (POR)**", "Analog POR cell detects the supply "
          "ramp / brown-out", "Everything, including always-on logic",
          "Only reset that may clear sticky 'reset reason' registers"],
         ["**External / pad reset**", "RESET_N pin, debugger", "Usually "
          "everything except the POR-only state", "Debounced and synchronized "
          "before use"],
         ["**Warm reset**", "Software request, fatal error", "Cores and "
          "peripherals; keeps PLL, always-on domain, reset-reason, some memory",
          "Fast recovery without re-locking PLLs"],
         ["**Watchdog reset**", "Watchdog timer expiry (Chapter 16)",
          "Usually a warm reset", "Latches the cause so boot code can report it"],
         ["**Software / block reset**", "A CSR bit (e.g. `PERIPH_RST[3]`)",
          "One IP block or subsystem", "The main source of RDC hazards"],
         ["**Domain reset**", "Power-domain turn-on (Chapter 19), clock "
          "domain start-up", "Everything in one power or clock domain",
          "Must be asserted while isolation is on and released after power "
          "is good"],
         ["**Debug reset**", "Debug module `ndmreset` / `hartreset`",
          "Cores and system, but not the debug module itself",
          "The debugger must stay connected across it"]],
        widths=[20, 26, 26, 28], bold_first=True)

    h2("Asynchronous assert, synchronous de-assert")
    p("Most ASIC SoCs use flops with asynchronous reset pins (so reset works "
      "with the clock stopped and does not lengthen data paths) but release "
      "reset **synchronously**. The reason is the reset equivalent of setup "
      "and hold: **recovery** and **removal** time. If the reset de-asserts "
      "too close to a clock edge, some flops leave reset in this cycle and "
      "some in the next, or go metastable - a state machine can wake up in "
      "an illegal state. The reset synchronizer asserts immediately and "
      "releases only on a clock edge of the domain it serves.")
    _v("rsync", "Reset synchronizer, one per clock domain. The `scan_mode` "
       "mux gives the tester direct control of reset for DFT (Chapter 20).")
    diagram([
        "                   +------+     +------+",
        "        1'b1 ----->|D   Q |---->|D   Q |-----+---------> rst_n_out",
        "                   |  FF1 |     |  FF2 |     |          (to CLR pins of",
        "        clk ------>|>     |  +->|>     |     |           the domain)",
        "                   | CLR  |  |  | CLR  |     |",
        "                   +--o---+  |  +--o---+   (scan mux omitted)",
        "        arst_n -------+------|-----+",
        "        clk -----------------+",
    ], "Assertion reaches both flops' CLR pins at once (no clock needed). "
       "De-assertion lets a 1 ripple through two flops, so the domain leaves "
       "reset on a clock edge, and any metastability of FF1 is resolved by "
       "FF2 - exactly a 2FF synchronizer with a constant input.")
    _v("tb_rsync")
    _o("rsync", "Before reset the flops are X (a real hazard in simulation - "
       "see Section 12.8). Assertion at t=13 is immediate; the release at t=37 "
       "reaches `rst_n_out` two clock edges later, at t=55.")
    box("warn", "PITFALLS with reset synchronizers",
        "(1) One synchronizer shared by two clock domains - the release is "
        "synchronous to only one of them. (2) Glitches on `arst_n`: a "
        "combinational reset source (`assign arst_n = a & b;`) can glitch and "
        "reset a domain spuriously; generate reset sources from flops. "
        "(3) Forgetting the clock must be **running** for de-assertion - a "
        "gated or not-yet-locked clock holds its domain in reset forever. "
        "(4) Synchronous reset in the reset synchronizer itself - it would "
        "need a clock to assert.")

    h2("Reset distribution trees")
    p("The synchronized reset of a large domain fans out to hundreds of "
      "thousands of flops. Physical design builds a **reset tree** with "
      "buffers, like a clock tree but with relaxed skew requirements. The "
      "de-assertion edge must still meet recovery/removal at every flop in a "
      "single cycle, which STA checks automatically for synchronous release. "
      "When the tree is too big to meet recovery in one cycle, the usual "
      "fixes are:")
    bul(["**Pipeline the reset**: add further flops after the synchronizer "
         "(and per sub-block) so each segment drives a smaller load. Reset "
         "latency grows by a few cycles, which nobody notices.",
         "**Hierarchical synchronizers**: one synchronizer per major block, "
         "fed from a central reset controller.",
         "**Multicycle recovery**: only when the design guarantees that no "
         "flop acts on the first cycles after release, and documented in SDC."])

    h2("Reset sequencing")
    p("A reset controller is a small FSM in the always-on domain that "
      "releases resets in a defined order, each step waiting for its "
      "precondition:")
    diagram([
        " POR/pad  PLL lock   clocks on   interconnect   memories init   CPU core",
        "   |         |           |             |              |             |",
        "   v         v           v             v              v             v",
        " [ASSERT ALL] -> [PLL lock wait] -> [release NoC/bus] -> [release periph]",
        "      -> [BIST/mem init done?] -> [release CPU (fetches boot ROM)]",
        "      -> [release debug-held cores on request]",
    ], "A typical boot sequence. The CPU comes last so that everything it can "
       "reach answers when the first instruction is fetched.")
    tbl(["Rule", "Why"],
        [["Release a slave before its masters", "A master that issues a "
          "transaction into a block still in reset gets no response - the "
          "bus hangs"],
         ["Keep clocks running for N cycles with reset asserted",
          "Synchronous-reset flops and memories with sync reset need edges "
          "to be cleared"],
         ["Record the reset cause in a POR-only register", "Boot code must "
          "distinguish watchdog, brown-out, software and pad resets"],
         ["Stretch short reset requests", "A 1-cycle software reset pulse may "
          "be shorter than a slow domain's period"]],
        widths=[40, 60], bold_first=True)

    h2("Reset-domain crossing (RDC)")
    p("An RDC path goes from a flop reset by reset A to a flop reset by a "
      "different reset B, **in the same clock domain**. CDC analysis says "
      "it is fine - one clock. The danger appears when A is asserted while B "
      "is not: the source flop's output changes **asynchronously** (the "
      "reset pin acts immediately, not on a clock edge), and the destination "
      "flop, still running, can sample the change inside its setup/hold "
      "window and go metastable, or capture a value that corrupts its state.")
    diagram([
        "     rst_a (block soft reset)                rst_b (system reset)",
        "         |                                        |",
        "     +---o---+     data/valid      +-------+  +---o---+",
        "     | FF_A  |-------------------->| logic |->| FF_B  |   clk common",
        "     +-------+                     +-------+  +-------+",
        "   rst_a asserts mid-cycle -> FF_A.Q changes asynchronously -> FF_B",
        "   may go metastable or latch a half-transaction.",
    ], "The RDC hazard. Classic real case: resetting a UART while the "
       "interconnect is mid-transaction - the bus sees a response channel "
       "valid drop without a handshake.")
    tbl(["RDC fix", "How it works"],
        [["**Isolate before reset**", "Gate the crossing signals with an "
          "enable (e.g. `valid & ~iso`) driven from the destination domain; "
          "assert isolation, wait, then assert the source reset"],
         ["**Quiesce first**", "Stop traffic to the block (bus 'drain' or "
          "clock gating) before resetting it; the software reset sequence "
          "becomes: stop -> wait idle -> reset -> release -> re-enable"],
         ["**Reset the destination too**", "If B is always asserted "
          "whenever A is (A is a superset), the crossing is safe"],
         ["**Synchronize the crossing**", "Treat the signal as asynchronous "
          "and put a synchronizer on it in the destination"]],
        widths=[28, 72], bold_first=True)
    box("expert", "RDC in sign-off",
        "Dedicated RDC checkers (Chapter 25) enumerate reset domains from "
        "the reset tree, find every flop-to-flop path whose resets differ, "
        "and require one of the fixes above or an explicit waiver citing the "
        "reset ordering constraint (for example 'rst_b always asserted when "
        "rst_a is'). Many silicon bugs surfaced by the first software-reset "
        "test on a real board are RDC bugs.")

    h2("Which flops need a reset?")
    p("Reset is not free: every reset pin costs area, reset-tree buffers "
      "and routing, and forces the async-reset flop variant, which is "
      "larger and slower. Good designers reset **control**, not **data**.")
    tbl(["Needs reset", "Usually does not"],
        [["FSM state registers", "Datapath pipeline registers qualified by a "
          "reset valid bit"],
         ["Valid bits, request/grant flags, counters that control behaviour",
          "Data payload registers, FIFO/RAM contents"],
         ["CSRs (software expects documented reset values)",
          "Shift registers whose contents are fully overwritten before use"],
         ["Interrupt status and enables", "Multiplier / MAC internal "
          "registers in accelerators"],
         ["Anything that drives an output port or another block's control",
          "Large register-file arrays (use a valid or init sequence)"]],
        widths=[50, 50])
    box("tip", "Mixing reset and non-reset flops in one always block",
        "If one always block resets `valid` but not `data`, synthesis must "
        "implement 'hold `data` during reset' - it adds an enable mux on "
        "every data bit driven by `rst_n`. Write reset and non-reset flops "
        "in **separate** always blocks (as `async_fifo` does for its memory "
        "in Chapter 11).")

    h2("Reset and DFT")
    p("During scan test (Chapter 20) the tester must control every "
      "asynchronous reset directly, or flops would be reset unpredictably "
      "while shifting. That is what `scan_mode`/`scan_rst_n` do in "
      "`rst_sync`. Additional rules: no reset may be generated from a "
      "flop's output in functional logic without a scan-mode bypass; reset "
      "synchronizer flops are usually excluded from scan chains or "
      "controlled; and the ATPG tool may test the reset network itself by "
      "pulsing `scan_rst_n` in capture.")

    h2("X-propagation and reset")
    p("In RTL simulation, flops without reset start as `X`. Verilog's "
      "optimistic semantics can hide the problem: an `if (x_signal)` takes "
      "the else branch, and a `case` on an `X` matches `default`, so the "
      "simulation looks clean while silicon may start in any state. The "
      "reverse also happens: pessimistic X propagation in gate-level "
      "simulation flags X on non-reset datapath flops that silicon never "
      "actually uses.")
    bul(["Enable an X-propagation mode (commercial simulators offer "
         "T-merge/X-prop modes) for RTL regressions.",
         "Assert that key control outputs are never X after reset: "
         "`assert property (@(posedge clk) disable iff (!rst_n) !$isunknown(state));` "
         "(Chapter 23).",
         "Do not 'fix' X by adding resets everywhere - fix the logic that "
         "consumes an uninitialized value, or qualify it with a valid.",
         "Randomize initial values of non-reset flops in simulation "
         "(tools offer +initreg-style options) to catch reset-dependent bugs."])

    h2("Summary")
    bul(["An SoC has many resets (POR, pad, warm, watchdog, software, domain, "
         "debug); a reset controller in the always-on domain sequences them.",
         "Assert asynchronously, release synchronously: one reset synchronizer "
         "per clock domain, with a DFT bypass.",
         "Release slaves before masters; keep clocks running during reset; "
         "record the reset cause.",
         "RDC: an asynchronous reset in one domain can corrupt flops in a "
         "same-clock domain with a different reset. Isolate or quiesce first.",
         "Reset control, not data; separate reset and non-reset flops; use "
         "X-propagation checks to find reset-dependent bugs."])

    h2("Exercises")
    bul(["Extend `rst_sync` with a `STAGES` parameter of 3 and a "
         "`rst_n_out` that is additionally stretched to at least 16 cycles "
         "after release of `arst_n`. Simulate it.",
         "Draw the reset sequence (as a waveform) for a chip with a PLL, an "
         "AXI interconnect, a DDR controller that needs 200 us of stable clock "
         "before its own reset release, and a CPU.",
         "A DMA engine has a software reset bit and talks to an AXI "
         "interconnect under system reset. List the RDC paths and design the "
         "reset sequence that makes the software reset safe.",
         "Why is `always_ff @(posedge clk or negedge rst_n) if (!rst_n) q <= 0; "
         "else q <= d;` combined with a `data` register in the same block a "
         "synthesis-quality problem? Show the inferred hardware.",
         "Write a SystemVerilog assertion that `rst_n_out` never de-asserts "
         "except in the cycle after a rising clock edge sampled `arst_n` high "
         "twice."], ordered=True)


# ---------------------------------------------------------------- Ch 13 ---
def _ch13():
    chapter("On-Chip Buses: APB, AHB, AXI4, AXI4-Lite, AXI4-Stream")
    p("Blocks in an SoC talk to each other through standard bus protocols, "
      "so that a CPU from one vendor, an interconnect generator from another "
      "and a hundred in-house peripherals plug together. By far the most "
      "common family is Arm's **AMBA** (Advanced Microcontroller Bus "
      "Architecture), whose specifications are freely available. Knowing "
      "APB and AXI signal-by-signal is a baseline expectation for any RTL "
      "role - interviewers routinely ask you to draw a handshake or write a "
      "slave on a whiteboard.")

    h2("The AMBA family at a glance")
    tbl(["Protocol", "Typical use", "Key properties"],
        [["**APB** (APB3/APB4/APB5)", "Low-bandwidth peripherals and CSRs: "
          "UART, timers, GPIO, config registers", "Unpipelined, 2+ cycles per "
          "transfer, no bursts, tiny slave logic"],
         ["**AHB / AHB-Lite** (AHB5)", "Older/MCU-class system bus, on-chip "
          "SRAM, flash controllers", "Pipelined address/data, single master "
          "(Lite), bursts, one outstanding transfer"],
         ["**AXI4** (AXI5)", "High-performance memory-mapped: CPU, DMA, DDR, "
          "accelerators", "5 independent channels, bursts up to 256 beats, "
          "IDs, many outstanding transactions, out-of-order completion"],
         ["**AXI4-Lite**", "Register access for high-speed IP", "AXI4 "
          "handshakes but single beat, no IDs; simple slave"],
         ["**AXI4-Stream**", "Point-to-point data streams: video, DSP, "
          "networking, ML accelerators", "No addresses; TVALID/TREADY "
          "handshake, TLAST framing, optional side-band"],
         ["**ACE / CHI**", "Cache-coherent interconnect for multi-core",
          "Snoop channels / packetized coherent protocol (Chapter 14)"]],
        widths=[20, 38, 42], bold_first=True)

    h2("APB: the peripheral bus")
    p("APB is the simplest AMBA protocol and the one you will implement most "
      "often, because every block needs control/status registers. There is "
      "one requester (the **APB bridge**, usually converting from AXI or "
      "AHB) and many completers, each selected by its own `PSEL`.")
    tbl(["Signal", "Driver", "Meaning"],
        [["`PCLK`, `PRESETn`", "system", "Clock; active-low reset"],
         ["`PADDR[31:0]`", "requester", "Byte address"],
         ["`PSELx`", "requester (decoder)", "This completer is selected"],
         ["`PENABLE`", "requester", "0 in the SETUP cycle, 1 in ACCESS cycles"],
         ["`PWRITE`", "requester", "1 = write, 0 = read"],
         ["`PWDATA[31:0]`", "requester", "Write data"],
         ["`PSTRB[3:0]`", "requester (APB4)", "Byte-lane write strobes"],
         ["`PPROT[2:0]`", "requester (APB4)", "Privileged / secure / "
          "instruction attributes"],
         ["`PREADY`", "completer", "Extends the ACCESS phase (wait states) "
          "while low"],
         ["`PRDATA[31:0]`", "completer", "Read data, valid when "
          "`PENABLE & PREADY` on a read"],
         ["`PSLVERR`", "completer", "Error response, valid only in the last "
          "ACCESS cycle"]],
        widths=[22, 22, 56])
    diagram([
        "            T1       T2       T3       T4       T5       T6",
        "  PCLK   _/~~\\__/~~\\__/~~\\__/~~\\__/~~\\__/~~\\__",
        "  PSEL   ___/~~~~~~~~~~~~~~~~~~~~~~~~~~\\_______________",
        "  PENABLE_________/~~~~~~~~~~~~~~~~~~~~\\_______________",
        "  PADDR  ---< addr A                   >---------------",
        "  PREADY ~~~~~~~~~~~~\\_______/~~~~~~~~~~~~~~~~~~~~~~~~~",
        "  PRDATA ---------------------< data  >----------------",
        "          |  IDLE  | SETUP  | ACCESS | ACCESS |  IDLE",
        "                              (wait)   (done: sampled at end of T4)",
    ], "APB read with one wait state. The transfer completes at the rising "
       "edge where PSEL, PENABLE and PREADY are all high.")
    bul(["**SETUP** (one cycle): `PSEL=1`, `PENABLE=0`, address/control/"
         "write data valid.",
         "**ACCESS** (one or more cycles): `PENABLE=1`; all signals from "
         "SETUP must stay stable. The transfer ends on the edge where "
         "`PREADY=1`.",
         "Back-to-back transfers go ACCESS -> SETUP directly (PSEL stays high, "
         "PENABLE drops) - so an APB transfer takes at least 2 cycles."])
    _v("apb", "An APB4 completer with four registers: CTRL (RW), STATUS (RO, "
       "from hardware), DATA (RW, one wait state to demonstrate PREADY) and "
       "ID (RO constant). Unmapped addresses and writes to read-only "
       "registers return PSLVERR.")
    _v("tb_apb", "A requester task that drives SETUP and ACCESS on the "
       "falling edge and prints one line per cycle in which PSEL is high.")
    _o("apb", "A waveform in table form, from the real run. Note the "
       "SETUP/ACCESS pairs, the extra ACCESS cycle 10 (RDY=0) for the DATA "
       "register, and PSLVERR in the final ACCESS cycle of the two bad "
       "transfers.")
    box("warn", "PITFALLS in APB completers",
        "(1) Writing on **every** ACCESS cycle instead of only when "
        "`PREADY=1` - harmless with zero wait states, a double write with "
        "side effects (FIFO push, W1C) otherwise. (2) Acting in the SETUP "
        "cycle - the requester may still change the address in a later "
        "SETUP. (3) Driving PSLVERR outside the last ACCESS cycle. (4) A read "
        "with side effects (read-to-clear, FIFO pop) must also fire exactly "
        "once, in the completing cycle.")

    h2("AHB-Lite: pipelined address and data")
    p("AHB overlaps the **address phase** of one transfer with the **data "
      "phase** of the previous one, so a zero-wait-state slave sustains one "
      "transfer per cycle. `HREADY` low stretches the current data phase "
      "**and** holds the next address phase.")
    diagram([
        "  HCLK    _/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_",
        "  HADDR   --< A >< B >< C >-------------",
        "  HTRANS  --<NSEQ><SEQ><SEQ>< IDLE >----",
        "  HWDATA  -------< dA >< dB    >< dC >--",
        "  HREADY  ~~~~~~~~~~~~~~\\___/~~~~~~~~~~~  (slave inserts 1 wait in B's data)",
        "              addr A | data A / addr B | data B (wait) | data B / addr C ...",
    ], "Pipelined AHB. The slave must register address and control in the "
       "address phase (when `HREADY` is high) because they change in the next "
       "cycle.")
    tbl(["Signal", "Meaning"],
        [["`HTRANS[1:0]`", "IDLE, BUSY, NONSEQ (first/single), SEQ "
          "(subsequent beats of a burst)"],
         ["`HBURST[2:0]`", "SINGLE, INCR, WRAP4/INCR4, WRAP8/INCR8, "
          "WRAP16/INCR16"],
         ["`HSIZE[2:0]`", "Bytes per beat (1 to 128)"],
         ["`HREADY` / `HREADYOUT`", "Global ready (from the mux) / this "
          "slave's ready"],
         ["`HRESP`", "OKAY or ERROR; ERROR is a two-cycle response"]],
        widths=[26, 74])
    box("note", "Where AHB still lives",
        "Microcontrollers (Cortex-M buses are AHB-Lite), flash and SRAM "
        "controllers, and legacy IP. New high-performance designs choose AXI, "
        "but you will meet AHB bridges in almost every SoC.")

    h2("AXI4: five independent channels")
    p("AXI4 separates a transaction into five channels, each a "
      "**valid/ready** stream exactly like those in Chapter 10. Because "
      "channels are independent, reads and writes proceed in parallel, "
      "address issue is decoupled from data, and many transactions can be "
      "in flight.")
    diagram([
        "   MANAGER (master)                                SUBORDINATE (slave)",
        "   +-------------+  AW: AWADDR AWLEN AWSIZE AWBURST AWID ..  +-------------+",
        "   |             |------------------------------------------>|             |",
        "   |             |  W:  WDATA WSTRB WLAST                     |             |",
        "   |   write     |------------------------------------------>|   write     |",
        "   |             |  B:  BRESP BID                             |             |",
        "   |             |<------------------------------------------|             |",
        "   |             |  AR: ARADDR ARLEN ARSIZE ARBURST ARID ..  |             |",
        "   |   read      |------------------------------------------>|   read      |",
        "   |             |  R:  RDATA RRESP RLAST RID                 |             |",
        "   |             |<------------------------------------------|             |",
        "   +-------------+   each channel: xVALID ->  <- xREADY      +-------------+",
    ], "The five AXI channels. Write = AW + W + B; read = AR + R.")
    h3("Handshake rules (the ones interviews ask about)")
    bul(["A transfer occurs on a rising edge where **VALID and READY are "
         "both high**.",
         "The source **must not wait for READY before asserting VALID** - "
         "otherwise two blocks that each wait for the other deadlock.",
         "Once VALID is asserted it must **stay asserted**, with payload "
         "stable, until the handshake completes.",
         "The destination **may** wait for VALID before asserting READY, and "
         "may drop READY freely while VALID is low.",
         "Dependencies: the slave may wait for AW **and** W before giving B "
         "(it must wait for WLAST); it may wait for AR before R; a manager "
         "must not make W depend on AWREADY (write data may even arrive "
         "before the address).",
         "No combinational path from input VALID to output READY is required, "
         "and good IP registers both (Chapter 10's skid buffer)."])
    h3("Bursts")
    tbl(["Field", "Meaning"],
        [["`AxLEN[7:0]`", "Beats minus one: 1-256 beats for INCR, 1-16 for "
          "FIXED, exactly 2, 4, 8 or 16 for WRAP"],
         ["`AxSIZE[2:0]`", "Bytes per beat = 2^{AxSIZE}, up to the data "
          "bus width"],
         ["`AxBURST`", "**FIXED** (same address every beat - FIFOs), **INCR** "
          "(incrementing - normal memory), **WRAP** (incrementing, wraps at a "
          "boundary of len x size - cache-line fills, critical word first)"],
         ["Rule", "An INCR burst must not cross a **4 KB** boundary, so a "
          "burst never spans two slaves or pages"],
         ["`WSTRB`", "One bit per byte lane; unaligned and narrow writes"],
         ["`xRESP`", "OKAY, EXOKAY (exclusive success), SLVERR (slave "
          "error), DECERR (no slave at this address - from the interconnect)"]],
        widths=[20, 80])
    eq(["INCR : addr_n = start + n x 2^size                 (aligned after the first beat)",
        "WRAP : lower = floor(start / (len x 2^size)) x (len x 2^size)",
        "       addr_n wraps from lower + len x 2^size back to lower",
        "e.g. WRAP4, 4-byte beats, start 0x38 -> 0x38, 0x3C, 0x30, 0x34"],
       "Burst address generation (len = AxLEN+1 beats).")
    h3("IDs, ordering and outstanding transactions")
    p("Each address carries an ID (`AWID`/`ARID`). Responses with the "
      "**same ID** must return in order; responses with **different IDs** "
      "may return out of order. A DMA engine can thus issue reads to a fast "
      "SRAM and a slow DDR and use whichever answers first. Write data has "
      "no ID in AXI4 (the AXI3 `WID` signal was removed), so write data must follow "
      "the order of write addresses. The number of transactions a manager "
      "may have outstanding is a design parameter; latency x bandwidth "
      "determines how many you need:")
    eq(["outstanding reads needed ~ (latency_cycles x bytes_per_cycle) / bytes_per_burst",
        "e.g. 200-cycle DDR latency, 16 B/cycle, 64 B bursts -> ~50 outstanding"],
       "Little's law applied to a bus: without enough outstanding "
       "transactions, a high-latency memory can never be kept busy.")
    box("expert", "Other AXI attributes",
        "`AxCACHE` (bufferable, modifiable, allocate hints), `AxPROT` "
        "(privileged/secure/instruction), `AxLOCK` (exclusive access for "
        "atomics - EXOKAY), `AxQOS` (priority hint for the interconnect, "
        "Chapter 14), `AxREGION` and `xUSER` side-band. AXI5 adds atomics, "
        "poison, parity/ECC signalling and more.")

    h2("An AXI4-Lite slave")
    p("AXI4-Lite keeps the five channels and the handshake rules but "
      "removes bursts (every transaction is one beat), IDs, and most "
      "attributes. It is the standard register interface for "
      "high-performance IP, and the classic place to make one mistake: "
      "assuming AW and W arrive together.")
    _v("axil", "An AXI4-Lite register slave. AW and W are captured "
       "independently into one-entry holders; the write happens only when "
       "both are present and the B channel can take the response. Reads "
       "support back-to-back accesses at one per cycle.")
    _v("tb_axil", "The testbench sends AW and W together, then W four "
       "cycles before AW with B back-pressure, then an unmapped address, "
       "and reads back.")
    _o("axil", "The second write used WSTRB=0011, so only the low half "
       "changed: 0x11223344 -> 0x1122CCDD. Out-of-range accesses return "
       "SLVERR (10).")
    box("warn", "PITFALLS in AXI slaves (frequent protocol-checker hits)",
        "(1) `assign awready = awvalid && wvalid;` - legal for a slave, but "
        "it builds combinational VALID -> READY paths through the "
        "interconnect and deadlocks against a (non-compliant, yet common) "
        "master that waits for AWREADY before driving WVALID; accept each "
        "channel independently, as `axil_regs` does. (2) Dropping BVALID or RVALID before READY. "
        "(3) Accepting a second AW while the previous B is still pending, "
        "then losing it. (4) Ignoring WSTRB. (5) Forgetting that the "
        "response ordering with IDs is per-ID, not global. Run an AXI "
        "protocol checker (assertion IP, Chapter 23) on every AXI port.")

    h2("AXI4-Stream")
    p("AXI4-Stream has no addresses and no responses - just a single "
      "valid/ready channel carrying data from a source to a sink. It is the "
      "natural interface between pipeline stages of a DSP chain, a video "
      "pipeline or an ML accelerator (the Chapter 29 project uses it).")
    tbl(["Signal", "Meaning"],
        [["`TVALID` / `TREADY`", "Handshake, with exactly the AXI rules"],
         ["`TDATA[8n-1:0]`", "Payload"],
         ["`TLAST`", "Last transfer of a packet/frame/row"],
         ["`TKEEP[n-1:0]`", "Byte is part of the stream (0 = null byte "
          "removed, e.g. at the end of a packet)"],
         ["`TSTRB[n-1:0]`", "Byte is data (1) or position byte (0)"],
         ["`TID`, `TDEST`", "Stream identifier and routing destination for "
          "interleaved streams"],
         ["`TUSER`", "User side-band (e.g. start-of-frame for video)"]],
        widths=[26, 74])
    code([
        "// AXI4-Stream pass-through register stage with packet counter.",
        "// Data advances when the output is empty or being drained (Chapter 10).",
        "assign s_tready = !m_tvalid || m_tready;",
        "always_ff @(posedge aclk or negedge aresetn)",
        "  if (!aresetn) begin m_tvalid <= 1'b0; pkt_cnt <= '0; end",
        "  else if (s_tready) begin",
        "    m_tvalid <= s_tvalid;",
        "    if (s_tvalid && s_tlast) pkt_cnt <= pkt_cnt + 1'b1;",
        "  end",
        "always_ff @(posedge aclk)                     // payload: no reset needed",
        "  if (s_tready && s_tvalid) {m_tdata, m_tkeep, m_tlast} <= {s_tdata, s_tkeep, s_tlast};",
    ], "The same register slice from Chapter 10 with AXI-Stream names; the "
       "handshake logic is identical.")

    h2("Choosing a protocol")
    tbl(["Criterion", "APB", "AHB-Lite", "AXI4-Lite", "AXI4", "AXI4-Stream"],
        [["Addressed", "yes", "yes", "yes", "yes", "no"],
         ["Pipelined", "no", "yes", "yes (channels)", "yes", "yes"],
         ["Bursts", "no", "up to 16 / INCR", "no", "up to 256", "unbounded packets"],
         ["Outstanding", "1", "1", "1+ (impl.)", "many, with IDs", "n/a"],
         ["Out-of-order", "no", "no", "no", "yes (by ID)", "no (TID interleave)"],
         ["Slave cost", "tiny", "small", "small", "large", "tiny"],
         ["Typical use", "CSRs, slow periph.", "MCU system", "IP registers",
          "memory, DMA, CPU", "datapaths"]],
        widths=[16, 14, 16, 16, 18, 20], bold_first=True)

    h2("Bridges")
    p("Real SoCs mix all of these, joined by bridges generated by the "
      "interconnect tool or taken from an IP library:")
    bul(["**AXI -> APB bridge**: accepts AXI(-Lite) transactions, serializes "
         "them into APB SETUP/ACCESS pairs, maps PSLVERR to SLVERR, and "
         "splits bursts into single transfers. It also decodes PSEL for each "
         "peripheral.",
         "**AXI <-> AHB bridges**: convert burst types (AHB WRAP4 vs. AXI "
         "WRAP) and handle AHB's single outstanding transfer.",
         "**Protocol converters** AXI4 -> AXI4-Lite: split bursts, drop IDs "
         "(while returning the right ID to the manager).",
         "**Width converters, clock converters (async FIFOs per channel) and "
         "register slices** are covered in Chapter 14."])

    h2("Summary")
    bul(["APB: SETUP then ACCESS, PREADY for wait states, PSLVERR for "
         "errors; commit writes and read side effects only in the completing "
         "cycle.",
         "AHB-Lite overlaps address and data phases; a slave samples address "
         "and control when HREADY is high.",
         "AXI4: five independent valid/ready channels; VALID never waits for "
         "READY; bursts FIXED/INCR/WRAP, 4 KB rule; per-ID ordering; enough "
         "outstanding transactions to cover latency.",
         "AXI4-Lite slaves must accept AW and W in either order; AXI4-Stream "
         "is a bare handshake plus TLAST/TKEEP framing.",
         "Bridges and converters glue protocols together; understand their "
         "latency and ordering behaviour."])

    h2("Exercises")
    bul(["Extend `apb_regs` so that a write to a new address 0x010 pushes "
         "into a 4-entry FIFO and a read from 0x014 pops it. Make sure a "
         "wait state cannot cause a double push.",
         "List the addresses of an AXI WRAP8 burst with 4-byte beats starting "
         "at 0x1014, and of an INCR8 burst starting at 0x0FF8. Is the INCR "
         "burst legal?",
         "Modify `axil_regs` to accept a new write while the previous B "
         "response is still waiting for BREADY (a two-deep response queue). "
         "What is the throughput gain?",
         "Explain with a timing diagram why an AXI master that waits for "
         "AWREADY before asserting WVALID can deadlock against a legal slave.",
         "Design (block diagram and FSM) an AXI4-Lite to APB bridge. Where "
         "does the latency go, and how are errors mapped?"], ordered=True)


# ---------------------------------------------------------------- Ch 14 ---
def _ch14():
    chapter("Interconnect, Arbitration, Memory Maps and NoCs")
    p("Chapter 13 defined how two blocks talk. The **interconnect** decides "
      "who may talk to whom, when, and through which wires: it decodes "
      "addresses, arbitrates between masters, converts widths, clocks and "
      "protocols, and - in large chips - becomes a packet-switched "
      "network-on-chip. Interconnect is usually generated by a tool (Arm "
      "CoreLink, Arteris FlexNoC, open-source generators such as the PULP "
      "AXI library), but every RTL designer must understand its building "
      "blocks, because performance problems and deadlocks are diagnosed at "
      "this level.")

    h2("Memory maps and address decoding")
    p("The memory map assigns every slave a range of the physical address "
      "space. It is a contract between hardware, boot code, drivers and "
      "the device tree, and changing it late is expensive.")
    tbl(["Region", "Base", "Size", "Slave / notes"],
        [["Debug module", "0x0000_0000", "4 KB", "RISC-V debug ROM/RAM; "
          "accessible in debug mode"],
         ["Boot ROM", "0x0001_0000", "64 KB", "Reset vector; read-only"],
         ["On-chip SRAM", "0x1000_0000", "512 KB", "Tightly coupled or via "
          "AXI"],
         ["Peripherals (APB)", "0x4000_0000", "64 KB", "4 KB per peripheral: "
          "UART0 0x4000_0000, UART1 0x4000_1000, SPI 0x4000_2000 ..."],
         ["PLIC / interrupt ctrl", "0x0C00_0000", "64 MB", "Standard RISC-V "
          "location"],
         ["CLINT / timer", "0x0200_0000", "64 KB", "mtime, mtimecmp, msip"],
         ["Accelerator CSRs", "0x5000_0000", "64 KB", "AXI4-Lite"],
         ["DDR", "0x8000_0000", "2 GB", "Through the memory controller"]],
        widths=[22, 18, 12, 48], bold_first=True)
    box("tip", "Memory-map design rules",
        "Align every region to its size (a power of two) so decoding is a "
        "compare on the upper address bits. Give each peripheral at least 4 "
        "KB - the MMU page size - so an OS can map it to one driver with its "
        "own permissions. Leave holes for growth. Accesses to holes must get "
        "an **error response** (DECERR from a default slave) rather than hang "
        "the bus. Generate the C header, device tree and the RTL decoder from "
        "one source (Chapter 15).")
    code([
        "// One-hot address decoder for an APB bridge: 16 peripherals, 4 KB each.",
        "localparam logic [31:0] PERIPH_BASE = 32'h4000_0000;",
        "wire in_periph = (paddr[31:16] == PERIPH_BASE[31:16]);   // 64 KB window",
        "always_comb begin",
        "  psel_vec = '0;",
        "  if (psel && in_periph) psel_vec[paddr[15:12]] = 1'b1;   // 4 KB slots",
        "end",
        "wire decode_err = psel && !in_periph;                     // -> PSLVERR",
    ], "Decoding with aligned, power-of-two regions: no adders, no "
       "comparators beyond equality on the upper bits.")

    h2("Shared bus versus crossbar")
    diagram([
        "  SHARED BUS                               CROSSBAR (M masters x S slaves)",
        "  M0   M1   M2                             M0 ---+-------+-------+",
        "   |    |    |                                   |       |       |",
        "   +----+----+--> [arbiter] --+            M1 ---+-------+-------+",
        "                              |                  |       |       |",
        "          +-------+-------+---+            M2 ---+-------+-------+",
        "          |       |       |                     [arb]   [arb]   [arb]",
        "          S0      S1      S2                     S0      S1      S2",
        "  one transfer at a time                   up to min(M,S) in parallel",
    ], "A shared bus serializes everything behind one arbiter; a crossbar "
       "has an arbiter per slave port and a decoder per master port.")
    tbl(["Topology", "Bandwidth", "Area / wiring", "Used for"],
        [["Shared bus", "One transfer at a time", "Smallest", "APB peripheral "
          "segments, tiny MCUs"],
         ["Full crossbar", "Parallel transfers to different slaves",
          "Grows as M x S x width; wire-dominated", "CPU cluster <-> memories, "
          "up to ~8x8"],
         ["Partial crossbar / sparse", "Only needed paths", "Moderate",
          "Most AXI interconnects (not every master reaches every slave)"],
         ["Hierarchical", "Local traffic stays local", "Moderate",
          "High-speed AXI + bridge to low-speed APB"],
         ["Network-on-chip", "Scales to tens-hundreds of endpoints",
          "Routers + narrow links", "Large SoCs, many-core, AI chips"]],
        widths=[20, 28, 28, 24], bold_first=True)

    h2("Arbiters")
    p("Whenever several requesters share one resource - a slave port, a "
      "memory bank, a bus - an arbiter picks one per cycle (or per "
      "transaction). The key properties are **fairness**, **latency "
      "bound**, **starvation freedom** and **timing** (arbiters sit on "
      "critical paths).")
    tbl(["Arbiter", "Rule", "Pros / cons"],
        [["**Fixed priority**", "Lowest index wins: `gnt = req & -req`",
          "Minimal logic; low-priority requesters can **starve**"],
         ["**Round-robin**", "Priority rotates to just after the last winner",
          "Fair, worst-case wait N-1 grants; slightly more logic"],
         ["**Weighted round-robin**", "Each requester gets up to W_{i} "
          "consecutive grants or credits per round", "Bandwidth shares "
          "(e.g. 50/25/25); needs counters"],
         ["**Matrix (least-recently-granted)**", "N x N bit matrix: "
          "`W[i][j]=1` means i beats j; winner's row cleared, column set",
          "True LRG fairness, O(N^{2}) flops, fast"],
         ["**TDMA / slot-based**", "Fixed time slots", "Deterministic latency "
          "(real-time), wastes idle slots"],
         ["**QoS / priority classes**", "Priority from `AxQOS` or urgency, "
          "round-robin within a class", "Serves real-time masters (display) "
          "first; needs starvation guards"]],
        widths=[24, 38, 38], bold_first=True)
    h3("A round-robin arbiter")
    p("The compact implementation uses a **mask** holding ones above the "
      "last winner. The fixed-priority picker `x & (~x + 1)` isolates the "
      "lowest set bit; it is applied first to the masked requests (those "
      "'after' the last winner) and, if none, to all requests.")
    _v("rr", "Mask-based round-robin arbiter. `advance` lets the grant be "
       "held for a multi-cycle transaction (for example until WLAST).")
    diagram([
        "  req ----+---------------------------------+",
        "          |                                 v",
        "          +--> AND <-- mask   +---------------------+",
        "                |             | lsb1(req)           |---+",
        "                v             +---------------------+   |   +-----+",
        "          +------------+                               +-->| MUX |--> gnt",
        "          | lsb1(req_m)|------------------------------->|     |",
        "          +------------+    sel = (req_m != 0) ------->+-----+",
        "  mask register <- ~((gnt << 1) - 1)  when advance",
    ], "Two fixed-priority pickers and a mux. The mask update "
       "`~((gnt << 1) - 1)` produces ones strictly above the one-hot winner.")
    _v("tb_rr", "The testbench shows the rotation with all four requesting, "
       "then runs 2000 cycles of random traffic in which each requester holds "
       "its request until granted, checking one-hot grants and the worst "
       "wait.")
    _o("rr", "Grants rotate 1 -> 2 -> 3 -> 0 (requester 0 won the first edge). "
       "Under random load the shares are even and the worst-case wait is "
       "exactly N-1 = 3 cycles - the round-robin bound.")
    box("warn", "PITFALLS with arbiters",
        "(1) Changing the grant in the middle of a burst or packet - hold it "
        "until the last beat (`advance` = handshake of the last beat). "
        "(2) A requester that drops its request before being granted "
        "(violating 'hold until served') breaks fairness assumptions and "
        "may cause lost transactions. (3) Updating the pointer on every "
        "cycle instead of only when a grant is consumed - the arbiter "
        "'skips' requesters. (4) Fixed priority on a path that carries "
        "sustained traffic: the lowest priority master starves.")
    box("expert", "Arbiter timing",
        "The masked-priority structure is two N-bit carry chains (the "
        "`-x`) plus a mux: fast enough for N <= 16 at GHz rates. For larger "
        "N, use a parallel-prefix priority encoder, a tree of 4-input "
        "arbiters, or the matrix arbiter, whose grant is a single AND-OR "
        "level per requester.")

    h2("Starvation, QoS and deadlock at the transaction level")
    p("Round-robin is fair per **grant**, not per **byte**: a master issuing "
      "256-beat bursts gets 256x the bandwidth of one issuing single beats. "
      "Interconnects therefore add burst-length limits, bandwidth regulators "
      "(token buckets per master) and QoS priority driven by `AxQOS`, with "
      "aging so that low priority traffic is eventually promoted. Display "
      "controllers and audio are the classic latency-critical masters - an "
      "underflow is visible or audible.")
    p("Transaction-level deadlock appears when resources are acquired in "
      "different orders, for example: a master holds the W channel of slave "
      "A while waiting for AW acceptance at slave B, and another master does "
      "the reverse. AXI interconnects avoid this by forwarding write data "
      "only in the order write addresses were accepted, and by limiting the "
      "number of outstanding transactions per ID to prevent ordering "
      "dependencies across slaves.")

    h2("Bridges and converters")
    tbl(["Component", "Function", "Design notes"],
        [["**Register slice**", "Breaks long timing paths on all channels",
          "Full (2-entry skid) slices keep throughput 1/cycle (Chapter 10)"],
         ["**Width converter (upsizer)**", "e.g. 32-bit master -> 128-bit "
          "slave", "Packs beats; adjusts AxSIZE/AxLEN; merges WSTRB"],
         ["**Width converter (downsizer)**", "128-bit master -> 32-bit slave",
          "Splits each beat; may split bursts to respect AxLEN limits"],
         ["**Clock converter**", "Crosses AXI between clock domains",
          "One async FIFO per channel (AW, W, B, AR, R) - Chapter 11"],
         ["**Protocol converter**", "AXI4 <-> AXI4-Lite, AXI <-> AHB/APB",
          "Burst splitting, ID reflection, response mapping"],
         ["**Default slave**", "Responds to unmapped addresses",
          "Returns DECERR; absorbs write data; returns RLAST correctly"],
         ["**Firewall / MPU**", "Checks AxPROT / master ID against rules",
          "Security: TrustZone-style isolation of secure peripherals"]],
        widths=[26, 34, 40], bold_first=True)

    h2("Networks-on-chip")
    p("Beyond roughly a dozen masters, crossbar wiring explodes and a "
      "centralized arbiter cannot meet timing across a large die. A "
      "**network-on-chip** (NoC) packetizes transactions at **network "
      "interfaces** (NIs) that speak AXI to the IP, and routes the packets "
      "through small routers connected by point-to-point links.")
    diagram([
        "   [CPU]--NI      [GPU]--NI      [DMA]--NI",
        "           |              |              |",
        "         (R)-----------(R)------------(R)       R = router (5 ports in a mesh:",
        "           |              |              |           N, S, E, W, local)",
        "         (R)-----------(R)------------(R)",
        "           |              |              |",
        "   [DDR0]--NI     [SRAM]--NI     [DDR1]--NI",
        "",
        "   packet = head flit (route, ID, type) + body flits (address/data) + tail flit",
    ], "A 2 x 3 mesh NoC. Each NI converts AXI transactions to packets "
       "and back.")
    tbl(["Concept", "Meaning"],
        [["**Flit**", "Flow-control unit - the link width worth of a packet; "
          "head/body/tail flits"],
         ["**Topology**", "Ring (simple, long latency), 2-D mesh (regular, "
          "scalable), torus, tree, crossbar-of-rings, custom"],
         ["**Routing**", "Deterministic XY (route X first then Y - deadlock-"
          "free on a mesh) or adaptive"],
         ["**Switching**", "Wormhole: head flit reserves the path, flits "
          "follow; small buffers, but a blocked packet holds several links"],
         ["**Flow control**", "Credit-based: the sender tracks free buffer "
          "slots at the receiver and never sends without a credit"],
         ["**Virtual channels (VC)**", "Several logical queues share one "
          "physical link; break routing cycles and separate traffic classes"],
         ["**Deadlock**", "Cyclic buffer dependency; avoided by routing "
          "restrictions (XY / turn model) or VC ordering"],
         ["**Protocol deadlock**", "Requests blocking responses; avoided by "
          "separate request and response networks or VCs"]],
        widths=[24, 76], bold_first=True)
    box("key", "Why NoCs matter to RTL designers",
        "Even if the NoC is generated, you design the IP that sits at its "
        "edges. Your block must tolerate high and variable latency, must not "
        "create dependencies between its own requests and responses (for "
        "example refusing to accept R data until an unrelated AW is "
        "accepted), and should issue enough outstanding transactions to "
        "hide NoC latency (Chapter 13's Little's-law estimate).")

    h2("Cache coherency in one page")
    p("When several cores (or a core and a DMA-capable accelerator) cache "
      "the same memory, a write by one must invalidate or update the "
      "copies of the others. Coherency protocols (MESI, MOESI) keep a state "
      "per cache line; interconnect protocols carry the messages:")
    bul(["**ACE** (AXI Coherency Extensions): adds snoop channels (AC, CR, "
         "CD) to AXI so the interconnect can query and invalidate caches. "
         "**ACE-Lite** is for IO-coherent masters without caches (a DMA "
         "reading coherent data).",
         "**CHI** (Coherent Hub Interface): a layered, packet-based "
         "protocol (request, response, snoop and data channels as flits) "
         "designed for NoCs and many-core servers, with a home node managing "
         "a snoop filter or directory.",
         "**TileLink** (RISC-V ecosystem, e.g. Rocket/Chipyard) offers "
         "uncached (TL-UL/UH) and cached (TL-C) variants.",
         "Accelerators that are **not** coherent must rely on software cache "
         "maintenance (clean/invalidate) around DMA buffers - a classic "
         "source of driver bugs (Chapter 16)."])

    h2("Summary")
    bul(["Design memory maps with aligned power-of-two regions, 4 KB "
         "granularity for peripherals, and a default slave for holes; "
         "generate all views from one source.",
         "Shared buses are cheap but serial; crossbars give parallelism at "
         "M x S wiring cost; NoCs scale to large SoCs.",
         "Round-robin arbitration bounds wait to N-1 grants; hold grants for "
         "whole bursts; add QoS and bandwidth regulation for real-time masters.",
         "Register slices, width/clock/protocol converters and default slaves "
         "are standard interconnect components.",
         "NoCs move flits through routers with credit flow control; deadlock "
         "is prevented by routing rules, virtual channels and separate "
         "request/response classes. ACE and CHI add coherency."])

    h2("Exercises")
    bul(["Write a matrix (least-recently-granted) arbiter for N=4 and "
         "compare its grant sequence with `rr_arb` under the same random "
         "traffic.",
         "Add weights to `rr_arb`: requester i may win up to W[i] consecutive "
         "grants while it keeps requesting. Measure the bandwidth shares for "
         "weights 4/2/1/1.",
         "Design the memory map for an SoC with 2 CPUs, 256 KB SRAM, 12 APB "
         "peripherals, a 64 KB accelerator register space and 1 GB of DDR. "
         "Write the decoder for the APB segment.",
         "Show a four-router ring with wormhole switching that deadlocks, and "
         "explain how adding a second virtual channel with a 'dateline' "
         "removes the deadlock.",
         "A camera writes 1080p60 frames (2 bytes/pixel) into DDR through an "
         "interconnect shared with a CPU. What bandwidth does it need, and "
         "what QoS mechanism protects it?"], ordered=True)


# ---------------------------------------------------------------- Ch 15 ---
def _ch15():
    chapter("Control/Status Registers, Interrupts and Register Generation")
    p("Control and status registers (CSRs) are the hardware/software "
      "interface of every IP block: software configures the block through "
      "them, reads its state, and services its interrupts. A typical SoC has "
      "tens of thousands of register fields. They are simple individually, "
      "but their **access semantics** and **side effects** are where "
      "hardware and firmware disagree, so the industry specifies them "
      "formally and generates the RTL, the C headers, the documentation and "
      "the verification model from one source.")

    h2("Register access types")
    tbl(["Type", "Software write", "Software read", "Typical use"],
        [["**RW**", "Stores value", "Returns stored value", "Configuration, "
          "enables, thresholds"],
         ["**RO**", "Ignored (or error)", "Returns hardware value", "Status, "
          "counters, version/ID"],
         ["**WO**", "Triggers action / stores", "Returns 0", "Command "
          "registers, FIFO push, 'kick' registers"],
         ["**W1C**", "1 clears the bit, 0 no effect", "Returns value",
          "Interrupt status, sticky error flags"],
         ["**W1S**", "1 sets the bit, 0 no effect", "Returns value",
          "Set half of a set/clear pair; software-triggered interrupts"],
         ["**W0C / W1T**", "0 clears / 1 toggles", "Returns value", "Rare; "
          "legacy or GPIO toggles"],
         ["**RC** (read-clear)", "Ignored", "Returns value, then clears",
          "Event counters, legacy status"],
         ["**RS / RW1S**", "Various", "Read sets", "Semaphores / locks"],
         ["**RW, lock**", "Writable until a LOCK bit is set", "Returns value",
          "Security configuration frozen after boot"]],
        widths=[16, 26, 26, 32], bold_first=True)
    box("key", "Why W1C instead of RW for interrupt status",
        "With an RW status register, software clearing bit 2 has to do a "
        "read-modify-write: read 0b0110, write back 0b0010. If hardware sets "
        "bit 3 between the read and the write, the write of 0b0010 **clears "
        "the new event** before anyone saw it. With W1C, software writes 0b0100 - only the bit it "
        "means to clear - and cannot destroy events it has not seen. "
        "Similarly, set/clear register pairs (W1S at one address, W1C at "
        "another) avoid read-modify-write races between CPUs.")
    box("warn", "PITFALL: read side effects",
        "RC registers and FIFO-pop-on-read registers change state when "
        "**read**. A debugger memory window, a speculative or prefetching "
        "CPU read, or a `printf` of the register in a debug build silently "
        "consumes data. Modern guidelines avoid read side effects; if you "
        "must have them, map them to non-cacheable, non-speculative device "
        "memory, and document them loudly. The same applies to APB/AXI read "
        "logic: the side effect must fire once, in the completing cycle.")

    h2("Documenting a register map")
    p("A register specification lists, for every register: name, offset, "
      "width, reset value, and for every field its bit range, access type, "
      "reset value, description and side effects. A typical entry:")
    tbl(["Bits", "Field", "Access", "Reset", "Description"],
        [["31:4", "-", "RO", "0", "Reserved; reads 0, writes ignored"],
         ["3", "OVF", "W1C", "0", "RX FIFO overflowed. Write 1 to clear"],
         ["2", "TXE", "W1C", "0", "TX FIFO became empty"],
         ["1", "RXF", "W1C", "0", "RX FIFO reached the threshold in "
          "`CTRL.RXTH`"],
         ["0", "ERR", "W1C", "0", "Framing or parity error"]],
        widths=[10, 12, 12, 10, 56], caption="`INT_STATUS` @ offset 0x04 - "
        "an interrupt status register.")
    bul(["**Reserved bits** read as 0 and ignore writes, so software can "
         "safely write 0 and future versions can add fields.",
         "**Reset values** are part of the spec; firmware relies on them.",
         "**Atomicity**: fields that software updates together must live in "
         "the same register; wider-than-bus values (64-bit counters) need a "
         "defined read order with a shadow/latch.",
         "Separate **configuration**, **status** and **interrupt** registers; "
         "never mix W1C fields with RW fields in one register if you can "
         "avoid it."])

    h2("A CSR block with interrupts")
    p("The block below implements a common pattern: a raw interrupt status "
      "register (W1C) set by hardware events, an enable register (RW), a "
      "software set register (WO, for testing interrupt handlers), a "
      "read-to-clear event counter, and an interrupt output that is the OR "
      "of enabled pending bits. The host interface is a simple one-cycle "
      "request, as produced by an APB or AXI-Lite adapter (Chapter 13).")
    _v("csr", "A CSR block with RW, W1C, WO(W1S), RC and RO semantics. "
       "Hardware set wins over a simultaneous software clear, so no event "
       "is ever lost.")
    diagram([
        "  hw_event[i] ---------------------------------+",
        "                                               v",
        "  sw W1C (wdata[i] & wr STATUS) --> NOT --> AND --> OR --> [status[i]] --+",
        "  sw W1S (wdata[i] & wr SET) ---------------------> OR        ^          |",
        "                                         status[i] -----------+ (hold)   |",
        "  enable[i] ---------------------------------------------> AND <---------+",
        "                                                            |",
        "                               irq = OR over all i of (status & enable)",
    ], "One bit of the interrupt status register: next = (status & ~clear) "
       "| set | hw_event.")
    _v("tb_csr")
    _o("csr", "Source 1 is recorded but masked (irq=0); source 2 raises "
       "irq; the W1C write clears only bit 2; in the race cycle the hardware "
       "set of bit 1 wins over the software clear; EVTCNT counts 3 events and "
       "clears on read.")
    box("tip", "Raw status, masked status",
        "Many IPs expose both **raw** status (`INT_RAW`, events regardless of "
        "enable) and **masked** status (`INT_STATUS = RAW & ENABLE`). Drivers "
        "read the masked view in the handler; diagnostics and polling-mode "
        "drivers read the raw view. Keep the `irq` output a registered "
        "signal when it leaves the block, so it is glitch-free and can be "
        "synchronized if the interrupt controller is in another clock "
        "domain (Chapter 11).")

    h2("Interrupts and interrupt controllers")
    tbl(["Concept", "Meaning"],
        [["**Level-sensitive**", "The line stays high while the condition is "
          "pending; it drops only when software clears the source. Robust; "
          "shareable; the norm for SoC peripherals"],
         ["**Edge-triggered**", "A rising edge (or pulse) records a pending "
          "interrupt in the controller. Short pulses must be captured by a "
          "flop; lost if two events merge before capture"],
         ["**Mask / enable**", "Per-source and per-target gating"],
         ["**Pending**", "Latched request waiting for service"],
         ["**Priority / threshold**", "Only sources above a target's threshold "
          "interrupt it; highest priority is delivered first"],
         ["**Claim / complete**", "The handler claims the highest-priority "
          "pending source (atomically clearing pending) and signals completion "
          "when done"],
         ["**Vectored / non-vectored**", "Jump to a per-source handler vs. one "
          "handler that reads the source ID"]],
        widths=[26, 74], bold_first=True)
    diagram([
        "  UART.irq --+                        +-------------------------+",
        "  SPI.irq  --+--> [gateway: level/ ]--> pending[i] -> priority[i] |",
        "  DMA.irq  --+    [ edge capture   ]  |   enable[i][target]       |--> meip (hart 0)",
        "  GPIO.irq --+                        |   threshold[target]       |--> meip (hart 1)",
        "                                      |   claim/complete regs     |",
        "                                      +-------------------------+",
        "  RISC-V PLIC: gateways turn each source into at most one pending request;",
        "  a target reads CLAIM to get the ID, services the device, writes COMPLETE.",
    ], "Platform-level interrupt controller (PLIC). Arm's **GIC** is "
       "conceptually similar: distributor (sources, priority, routing) plus "
       "CPU interfaces (acknowledge = claim, end-of-interrupt = complete).")
    bul(["RISC-V also has the **CLINT/ACLINT** for timer (`mtip`) and "
         "software (`msip`) interrupts, and the newer **AIA** (APLIC + IMSIC) "
         "with message-signalled interrupts.",
         "**Message-signalled interrupts (MSI)**: a device writes to a "
         "doorbell address instead of driving a wire - no wires across the "
         "chip, naturally ordered after the data it announces (PCIe uses MSI).",
         "**Interrupt service sequence** for a level interrupt: claim -> read "
         "device status -> handle -> W1C the device status -> complete. "
         "Completing before clearing the device causes an immediate spurious "
         "re-entry.",
         "Interrupts crossing clock domains: level interrupts go through a 2FF "
         "synchronizer; pulses need a toggle synchronizer (Chapter 11)."])

    h2("Register generation: SystemRDL and IP-XACT")
    p("Hand-writing thousands of registers in RTL, C headers, documentation "
      "and testbench models guarantees that the four drift apart. Instead, "
      "registers are described once in a machine-readable format and "
      "everything is generated:")
    code([
        "// SystemRDL 2.0 (Accellera) description of the CSR block above",
        "addrmap irq_csr {",
        "  default regwidth = 32;",
        "  reg { field { sw = rw; hw = r; } CTRL[3:0] = 0; } ctrl @ 0x00;",
        "  reg {",
        "    field { sw = rw; hw = w; onwrite = woclr; intr; } EV[3:0] = 0;  // intr: sticky",
        "  } status @ 0x04;",
        "  reg { field { sw = rw; hw = r; } EN[3:0] = 0; } enable @ 0x08;",
        "  reg { field { sw = w; hw = r; singlepulse; } SET[3:0] = 0; } set @ 0x0C;",
        "  reg { field { sw = r; onread = rclr; counter; } CNT[7:0] = 0; } evtcnt @ 0x10;",
        "};",
    ], "The same register map in SystemRDL. Properties such as `onwrite = "
       "woclr` (W1C), `onread = rclr` (RC), `counter` and `intr` (a sticky "
       "field set by hardware) define the semantics.")
    tbl(["Format / tool", "What it is"],
        [["**SystemRDL 2.0**", "Accellera register description language; "
          "compact, human-writable; open-source compiler `systemrdl-compiler` "
          "and generators (PeakRDL: RTL, C headers, HTML, UVM)"],
         ["**IP-XACT (IEEE 1685)**", "XML standard for IP metadata: ports, "
          "bus interfaces, memory maps, registers; used for SoC assembly and "
          "tool exchange"],
         ["Spreadsheets / YAML / JSON", "Common in-house front ends (e.g. "
          "OpenTitan's `reggen` uses Hjson), converted to the formats above"],
         ["Commercial tools", "Agnisys IDesignSpec, Magillem, Semifore CSRCompiler"]],
        widths=[28, 72], bold_first=True)
    diagram([
        "                        +--> RTL register block (SV, with bus adapter)",
        "   SystemRDL / IP-XACT  +--> C header: #define UART_INT_STATUS_OFFSET 0x04 ...",
        "   (single source) -----+--> HTML/PDF register documentation",
        "                        +--> UVM register model (RAL) for the testbench",
        "                        +--> device tree / Rust / Python access layers",
    ], "Single source of truth for registers.")

    h2("Verification tie-in: the UVM register layer")
    p("The generated **UVM Register Abstraction Layer (RAL)** model mirrors "
      "every register and field, with access policies (\"RW\", \"W1C\", "
      "\"RC\" ...) and reset values. Tests then read and write registers by "
      "name, independent of the bus protocol, and built-in sequences check "
      "the whole map automatically: reset values (`uvm_reg_hw_reset_seq`), "
      "access policies and bit-bashing (`uvm_reg_bit_bash_seq`), and "
      "address aliasing. A predictor keeps the model's mirror in sync with "
      "observed bus traffic, so every read can be checked. Chapter 24 builds "
      "this in detail.")
    box("expert", "Interview favourite: W1C + hardware set in the same cycle",
        "State the policy explicitly in the spec (normally **set wins**, as in "
        "`irq_csr`), and make sure the RAL predictor knows it - otherwise the "
        "model predicts 0, the hardware returns 1, and the testbench reports a "
        "false mismatch. Such cases are marked 'volatile' in the model.")

    h2("Summary")
    bul(["Access types (RW, RO, WO, W1C, W1S, RC ...) define both the software "
         "view and the hardware logic; W1C and set/clear pairs avoid "
         "read-modify-write races.",
         "Avoid read side effects; commit any side effect exactly once, in the "
         "completing bus cycle.",
         "Interrupt status = sticky W1C bits set by hardware (set wins), gated "
         "by enables, ORed into a registered level interrupt.",
         "Interrupt controllers (PLIC, GIC) add gateways, priorities, "
         "thresholds and claim/complete; MSIs replace wires with writes.",
         "Describe registers once in SystemRDL or IP-XACT and generate RTL, "
         "headers, documentation and the UVM RAL model."])

    h2("Exercises")
    bul(["Add a 64-bit free-running counter to `irq_csr`, readable over a "
         "32-bit bus. Design the latch-on-read-of-low-word mechanism so "
         "software always gets a coherent value.",
         "Change `irq_csr` so that STATUS has edge-capture semantics for "
         "level inputs: a source that stays high must not re-set the bit "
         "after software clears it until it goes low and high again.",
         "Write the C interrupt handler for `irq_csr` and a PLIC, in the "
         "correct claim/clear/complete order. What goes wrong if the order "
         "is changed?",
         "Write SystemRDL for the APB register block of Chapter 13 "
         "(`apb_regs`) and run it through an open-source generator if you "
         "have one available.",
         "List three ways a debugger can corrupt device state through "
         "read side effects, and how the register design can prevent each."],
        ordered=True)


# ---------------------------------------------------------------- Ch 16 ---
def _ch16():
    chapter("Peripherals, DMA and Processor Integration")
    p("This chapter assembles everything in Part III into a working "
      "system. Peripherals are where most RTL engineers start their "
      "careers - they are small, self-contained, and exercise every skill: "
      "FSMs, counters, CDC, CSRs, interrupts and bus interfaces. Then we "
      "move data without the CPU (DMA), integrate a RISC-V core, and look at "
      "caches and the memory hierarchy from the RTL designer's side.")
    diagram([
        "  Common peripheral skeleton",
        "  +-------------------------------------------------------------+",
        "  | APB slave -> CSR block (Ch 15) -> ctrl/config -+              |",
        "  |      ^                     ^                   v              |",
        "  |      | status               | irq      +--------------+  pins |",
        "  |      +---------------------+----------| core engine   |<----->|",
        "  |                                        | FSM + counters|       |",
        "  |      TX FIFO / RX FIFO (Ch 9) <------->| shift regs    |       |",
        "  |                                        +--------------+       |",
        "  +-------------------------------------------------------------+",
    ], "Almost every peripheral is a bus slave, a register block, FIFOs, "
       "and a protocol engine with an interrupt output.")

    h2("GPIO")
    p("General-purpose I/O is the simplest peripheral but has real "
      "subtleties at the pin boundary:")
    bul(["Registers: `DATA_OUT` (RW), `DIR`/`OUT_EN` (RW), `DATA_IN` (RO), "
         "plus **set/clear/toggle** aliases so different drivers can change "
         "different pins without read-modify-write races (Chapter 15).",
         "Inputs are **asynchronous**: every input passes through a 2FF "
         "synchronizer before use (Chapter 11), and optionally a debounce "
         "filter (counter-based: accept a new level only after it is stable "
         "for N samples).",
         "Interrupts per pin: rising, falling, both edges, or level - edge "
         "detection on the **synchronized** value, W1C status.",
         "The pad itself (output driver, input buffer, pull-ups, drive "
         "strength, pin mux) is an instantiated I/O cell in the chip top "
         "level, controlled by pad-control registers."])

    h2("Timers, PWM and watchdog")
    p("A timer is a counter plus comparators. The same structure gives "
      "periodic interrupts, input capture (latch the count on an external "
      "edge), output compare and **pulse-width modulation**, used for motor "
      "control, LED dimming and switching power converters.")
    _v("pwm", "A PWM generator. The duty cycle is **shadowed**: a new value "
       "written mid-period takes effect only at the next period boundary, so "
       "the output never produces a truncated or double pulse.")
    _v("tb_pwm", "The testbench prints one character per clock, grouped by "
       "10-cycle periods, and changes the duty from 3 to 7 in the middle of "
       "the second period.")
    _o("pwm", "Period 1 and 2: 3 of 10 cycles high. The change made in the "
       "middle of period 2 only appears in period 3 (7 of 10) thanks to the "
       "shadow register.")
    box("warn", "PITFALL: unshadowed compare registers",
        "Without `duty_sh`, lowering the duty from 7 to 3 while the counter "
        "is at 5 would end the pulse early and raising it would extend it - "
        "a glitch that a motor driver or DC/DC converter may not tolerate. "
        "The same applies to timer reload values: load them at the wrap.")
    p("The **watchdog timer** is a down-counter that resets the system when "
      "it reaches zero unless software 'kicks' (reloads) it in time. RTL "
      "guidelines for watchdogs: clock it from an always-on, independent "
      "oscillator so a stuck PLL cannot freeze it; require a **key sequence** "
      "(e.g. write 0x5555 then 0xAAAA) to kick or reconfigure it so runaway "
      "code cannot kick it accidentally; lock its configuration after boot; "
      "support a **window** mode where kicking too early is also a fault; "
      "and record 'watchdog' as the reset cause (Chapter 12). A pre-timeout "
      "interrupt gives software a chance to log state.")

    h2("UART")
    p("A UART sends asynchronous serial frames: idle high, one start bit "
      "(0), 5-9 data bits LSB first, optional parity, and 1-2 stop bits (1). "
      "There is no clock wire; both ends agree on a baud rate within ~2-3%.")
    diagram([
        "  idle ~~~~\\___ D0 _ D1 _ D2 _ D3 _ D4 _ D5 _ D6 _ D7 _ (P) _/~~~ stop ~~~ idle",
        "           start                                                ",
        "  RX samples: detect falling edge, wait 8 ticks (x16 oversampling) to",
        "  mid-start, check still 0, then sample every 16 ticks (majority of 3)",
    ], "UART frame, 8N1: 10 bit-times per byte.")
    bul(["**Baud generator**: fractional divider producing a 16x (or 8x) "
         "oversampling tick: `div = f_clk / (16 x baud)`, with a fractional "
         "part to keep error below 1%.",
         "**TX**: FSM IDLE -> START -> DATA(8) -> PARITY -> STOP, a shift "
         "register, and a TX FIFO.",
         "**RX**: the RX pin is asynchronous - 2FF synchronize it first; "
         "false-start rejection; majority vote of 3 samples around mid-bit; "
         "framing error if the stop bit is 0; overrun if the RX FIFO is full; "
         "break detection (line low for a whole frame).",
         "**CSRs and interrupts**: TX empty / below threshold, RX above "
         "threshold, RX timeout (data waiting, line idle for N characters), "
         "errors - all W1C. Chapter 28 builds a complete APB UART."])

    h2("SPI")
    p("SPI is a synchronous, full-duplex serial bus: the master drives "
      "`SCLK`, `MOSI` and a chip select per slave (`CS_n`); the slave drives "
      "`MISO`. Each clock shifts one bit each way, so a transfer is really "
      "an exchange between two shift registers. Four modes define clock "
      "polarity and phase:")
    tbl(["Mode", "CPOL (idle SCLK)", "CPHA", "Data sampled on", "Data changes on"],
        [["0", "0", "0", "rising edge", "falling edge (first bit at CS fall)"],
         ["1", "0", "1", "falling edge", "rising edge"],
         ["2", "1", "0", "falling edge", "rising edge (first bit at CS fall)"],
         ["3", "1", "1", "rising edge", "falling edge"]],
        widths=[10, 18, 10, 26, 36])
    _v("spi", "A mode-0 SPI master shift engine. One 8-bit shift register "
       "serves both directions: MOSI is its MSB; MISO is captured on the "
       "rising SCLK edge and shifted in on the falling edge.")
    diagram([
        "  CS_n ~~\\___________________________________________________/~~~",
        "  SCLK ____/~~\\__/~~\\__/~~\\__/~~\\__/~~\\__/~~\\__/~~\\__/~~\\______",
        "  MOSI --< b7 >< b6 >< b5 >< b4 >< b3 >< b2 >< b1 >< b0 >-------",
        "            ^ sample     ^ sample   ...                 ^ sample",
    ], "Mode 0: the first bit is valid when CS_n falls; the slave samples "
       "on rising edges, and both sides change data on falling edges.")
    _v("tb_spi", "A behavioural mode-0 slave exchanges a byte with the "
       "master; both directions are checked.")
    _o("spi")
    box("expert", "Why SPI masters get hard at high speed",
        "At tens of MHz the MISO round trip (SCLK out through the pad, board "
        "trace, slave clock-to-out, trace, pad back in) can exceed half an "
        "SCLK period. Fast controllers (QSPI flash, 100+ MHz) therefore "
        "sample MISO with a delayed or feedback clock, add programmable "
        "sampling delay, or use DDR sampling - and the I/O timing is "
        "constrained in SDC with generated clocks on the SCLK pin (Chapter 18).")

    h2("I2C")
    p("I2C uses two open-drain wires, `SCL` and `SDA`, with pull-up "
      "resistors: any device can pull a line low, nobody drives it high. "
      "That makes multi-master arbitration and clock stretching possible.")
    bul(["**START**: SDA falls while SCL is high. **STOP**: SDA rises while "
         "SCL is high. Otherwise SDA changes only while SCL is low.",
         "Frame: START, 7-bit address + R/W bit, ACK (receiver pulls SDA low "
         "in the 9th clock), data bytes each followed by ACK/NACK, STOP (or "
         "repeated START).",
         "**Clock stretching**: a slave holds SCL low to pause the master; the "
         "master must monitor SCL, not assume its own timing.",
         "**Arbitration**: a master that drives 1 but reads 0 on SDA has lost "
         "and backs off - no data is corrupted.",
         "RTL: pins are implemented as `oe` controls of open-drain pads "
         "(`assign sda_oe = ~sda_out;` - drive low only); inputs are 2FF "
         "synchronized and glitch-filtered (50 ns spike suppression in "
         "fast mode); a bit-level FSM generates SCL phases from a divider "
         "and a byte-level FSM sequences address, data and ACK.",
         "Speeds: 100 kHz standard, 400 kHz fast, 1 MHz fast-plus; I3C is "
         "the faster, push-pull-capable successor."])
    tbl(["", "UART", "SPI", "I2C"],
        [["Wires", "2 (TX, RX)", "3 + 1 CS per slave", "2 (shared)"],
         ["Clocking", "Asynchronous, agreed baud", "Master clock", "Master "
          "clock, slave can stretch"],
         ["Duplex", "Full", "Full", "Half"],
         ["Addressing", "Point-to-point", "Chip select", "7/10-bit address"],
         ["Typical speed", "115.2 kbit/s - few Mbit/s", "1-100+ MHz",
          "100 kHz - 1 MHz"],
         ["RTL difficulty", "RX sampling / oversampling", "I/O timing at "
          "speed", "Open-drain, stretching, arbitration"]],
        widths=[18, 26, 26, 30], bold_first=True)

    h2("DMA controllers")
    p("A DMA (direct memory access) controller is a bus **master** that "
      "moves data so the CPU does not have to. The CPU programs a "
      "transfer, the DMA executes it with long bursts and many outstanding "
      "transactions, and interrupts the CPU on completion.")
    diagram([
        "   CSR (APB slave)        +--------------------------------------+",
        "   src, dst, len, ctrl -->| channel regs  |  arbiter between      |",
        "   (or descriptor ptr)    | per channel   |  channels (Ch 14)     |",
        "                          +------+--------+----------+-----------+",
        "                                 v                   v",
        "                        read engine (AR/R)  --> data FIFO -->  write engine (AW/W/B)",
        "                                 |      (align / pack / width conv.)     |",
        "                                 +---------- AXI4 master port -----------+",
        "   peripheral handshake: dma_req (e.g. UART RX not empty) / dma_ack",
    ], "Block diagram of a multi-channel DMA engine.")
    tbl(["Feature", "What it means for the RTL"],
        [["Memory-to-memory", "Read bursts fill the FIFO, write bursts "
          "drain it; keep both engines busy with several outstanding bursts"],
         ["Peripheral flow control", "Transfers paced by `dma_req` from a "
          "peripheral FIFO level; FIXED-address bursts to the FIFO register"],
         ["**Descriptors**", "The transfer description (src, dst, length, "
          "control, **next pointer**) lives in memory; the DMA fetches it"],
         ["**Scatter-gather**", "A linked list of descriptors - e.g. one "
          "network packet in several buffers - processed without CPU "
          "intervention"],
         ["Alignment", "Unaligned src/dst need a byte-shifting barrel and "
          "WSTRB generation; the 4 KB boundary splits bursts"],
         ["Completion", "Per-descriptor interrupt flag, write-back of status "
          "into the descriptor, error reporting (SLVERR/DECERR)"]],
        widths=[26, 74], bold_first=True)
    code([
        "// A typical scatter-gather descriptor (in memory, 32-byte aligned)",
        "typedef struct packed {",
        "  logic [63:0] next;       // address of next descriptor, 0 = end of list",
        "  logic [63:0] src;        // source address",
        "  logic [63:0] dst;        // destination address",
        "  logic [31:0] len;        // bytes",
        "  logic [31:0] ctrl;       // [0] irq_on_done [1] src_fixed [2] dst_fixed",
        "} dma_desc_t;              //  ... status written back here on completion",
    ], "Descriptor layout. The DMA reads it with one burst, executes it, "
       "optionally writes status back, and follows `next`.")
    box("warn", "PITFALL: DMA and caches",
        "If the CPU has a write-back data cache and the DMA is not coherent "
        "(Chapter 14), a buffer the CPU just wrote may still sit in the "
        "cache when the DMA reads DDR, and a buffer the DMA just wrote may be "
        "shadowed by stale cache lines. Drivers must clean the cache before "
        "a DMA read of memory and invalidate after a DMA write - or the "
        "hardware must be IO-coherent (ACE-Lite). A second classic: "
        "raising the completion interrupt before the last write response (B) "
        "has returned - the CPU may read data that has not landed yet.")

    h2("Integrating a RISC-V core")
    p("Open RISC-V cores (Ibex, CV32E40P, CVA6, Rocket, VexRiscv, "
      "PicoRV32) make it practical to build a complete SoC in RTL. "
      "Integration is mostly about the environment around the core:")
    tbl(["Item", "What to provide"],
        [["**Memory interfaces**", "Instruction and data ports (AXI, AHB, "
          "OBI or TileLink depending on the core), connected through the "
          "interconnect to ROM, SRAM and peripherals"],
         ["**Boot ROM and reset vector**", "The core fetches its first "
          "instruction from a parameter/strap address (`boot_addr`); the ROM "
          "initializes the stack, clocks and memory and loads or jumps to "
          "the application"],
         ["**Memory map**", "Must match the linker script and device tree; "
          "mark device regions non-cacheable / non-idempotent (PMA)"],
         ["**Interrupts**", "Machine timer (`mtip`) and software (`msip`) "
          "from the CLINT; external (`meip`) from the PLIC (Chapter 15)"],
         ["**Debug**", "RISC-V Debug Spec: a **Debug Module** (DM) on the "
          "bus with abstract commands, program buffer and system bus access, "
          "reached from JTAG through a **Debug Transport Module** (DTM); "
          "`debug_req` into the core; works with OpenOCD + GDB"],
         ["**Clocks/resets**", "Core clock gating in WFI, reset released "
          "last (Chapter 12), `ndmreset` from the DM"],
         ["**Other**", "Hart ID strap, PMP configuration, performance "
          "counters, optional FPU / custom instruction interface"]],
        widths=[26, 74], bold_first=True)
    code([
        "// Integration sketch (port names follow a typical small core; check yours)",
        "riscv_core #(.BOOT_ADDR(32'h0001_0000)) u_cpu (",
        "  .clk_i (clk_cpu), .rst_ni (rst_cpu_n),",
        "  .hart_id_i (32'd0),",
        "  // instruction and data ports -> interconnect masters 0 and 1",
        "  .instr_req_o (ireq), .instr_addr_o (iaddr), .instr_rdata_i (irdata), ...",
        "  .data_req_o  (dreq), .data_we_o (dwe), .data_addr_o (daddr), ...",
        "  // interrupts",
        "  .irq_timer_i (mtip), .irq_software_i (msip), .irq_external_i (meip),",
        "  .debug_req_i (dm_debug_req)",
        ");",
    ], "Not a runnable listing - each core has its own port list - but the "
       "connections every integration needs.")

    h2("Caches and the memory hierarchy, from the RTL side")
    p("A cache keeps recently used lines of memory in fast SRAM next to the "
      "core. For an RTL designer it is a datapath (tag RAM, data RAM, "
      "comparators, way mux) plus a controller FSM (lookup, miss, refill, "
      "write-back, eviction).")
    diagram([
        "  address = | tag | index | offset |",
        "                    |        (selects byte in line)",
        "                    v",
        "   +---------------------------------+  +---------------------------+",
        "   | way0: V D tag | way1: V D tag   |  | data RAM way0 | way1      |",
        "   +---------------------------------+  +---------------------------+",
        "        |  == addr.tag ?   |  ==                  |         |",
        "        +-> hit0          +-> hit1  --------> way mux ----> rdata",
        "   miss -> FSM: pick victim (LRU) -> write back if D=1 -> refill (WRAP burst)",
    ], "A 2-way set-associative cache. The critical path is tag RAM read -> "
       "compare -> way select.")
    tbl(["Level", "Typical size / latency", "RTL notes"],
        [["Registers", "32 x 64 bit / 0 cycles", "Register file, Chapter 9"],
         ["L1 I/D cache", "16-64 KB / 1-4 cycles", "SRAM macros, often "
          "virtually indexed physically tagged; WRAP bursts for refills"],
         ["L2 / LLC", "256 KB - tens of MB / 10-40 cycles", "Banked, shared, "
          "often inclusive with a snoop filter"],
         ["On-chip SRAM / scratchpad", "KB-MB / few cycles", "Software-"
          "managed; common in accelerators and MCUs"],
         ["DDR / LPDDR", "GB / 100+ ns", "Memory controller + PHY IP; long "
          "latency needs many outstanding transactions"]],
        widths=[22, 30, 48], bold_first=True)
    bul(["**Write policies**: write-back (dirty bit, evictions write whole "
         "lines) vs. write-through (simpler, more bus traffic); "
         "write-allocate or not.",
         "**Non-cacheable regions**: device registers must never be cached - "
         "the PMA/MPU marks them, and the bus carries it in `AxCACHE`.",
         "**Accelerators** (Chapter 29) usually prefer software-managed "
         "scratchpads with DMA over caches: deterministic latency, no tag "
         "overhead, and double-buffering hides DDR latency."])

    h2("Putting it together: an example SoC")
    diagram([
        "                +---------------- always-on domain --------------------+",
        "   XTAL 24MHz ->| POR | reset ctrl (Ch 12) | PLL | clk gen/mux (Ch 11) |",
        "                +--------------------------------+----------------------+",
        "   JTAG --> [DTM]--[Debug Module]                  | clocks / resets",
        "                        |                          v",
        "   +--------+     +-----+----------------------------------------------+",
        "   | RISC-V |I/D  |          AXI4 crossbar / NoC (Ch 14)               |",
        "   | core   |====>|  M: cpu-I, cpu-D, DMA, debug   S: ROM SRAM DDR APB  |",
        "   | +L1$   |     +---+--------+--------+---------+------------+-------+",
        "   +--------+         |        |        |         |            |",
        "     ^ irq       [Boot ROM] [SRAM]  [DDR ctrl]  [AXI->APB]   [ML accel]",
        "     |                               + PHY       |           AXI-Lite CSR",
        "   [PLIC]<--- irqs ---+                          |           AXI-S datapath",
        "   [CLINT]            |          +------+-------+------+------+ (Ch 29)",
        "                      +----------| UART | SPI  | I2C  | GPIO | TIMER/PWM | WDT",
        "   [DMA] AXI master   (Ch 13-16) +------+------+------+------+",
    ], "A small but complete SoC. Every box is a topic of Part III; Parts IV "
       "and V turn it into silicon and prove it works.")
    checklist("SoC integration checklist", [
        "Every clock-domain crossing identified and synchronized; CDC tool clean",
        "One reset synchronizer per clock domain; reset sequence documented",
        "Memory map single-sourced; default slave returns DECERR for holes",
        "All bus ports pass protocol-checker assertions",
        "Every interrupt: W1C status, enable, routed to PLIC, synchronized if needed",
        "Boot ROM address = core boot vector; debug module reachable over JTAG",
        "Device regions non-cacheable; DMA buffers coherent or cache-managed",
        "Register map documentation, C headers and RAL model generated from RDL",
    ])

    h2("Summary")
    bul(["Peripherals share one skeleton: APB slave + CSRs + FIFOs + a "
         "protocol engine + interrupts; asynchronous pins are synchronized.",
         "Timers/PWM need shadowed compare values; watchdogs need an "
         "independent clock, key sequences and a recorded reset cause.",
         "UART: oversampled asynchronous frames; SPI: shift-register "
         "exchange with CPOL/CPHA modes; I2C: open-drain with START/STOP, "
         "ACK, clock stretching and arbitration.",
         "DMA engines are AXI masters with descriptors and scatter-gather; "
         "watch cache coherency and completion ordering.",
         "Integrating a RISC-V core means memory map, boot ROM, CLINT/PLIC "
         "interrupts, debug module and reset order; caches trade tag logic "
         "and complexity for latency."])

    h2("Exercises")
    bul(["Extend `spi_master` with CPOL and CPHA parameters supporting all "
         "four modes, and verify each mode against a matching slave model.",
         "Design the RX half of a UART with 16x oversampling, false-start "
         "rejection and majority voting. Test it with a transmitter whose "
         "baud rate is 2% fast and 2% slow.",
         "Add a `capture` input to `pwm` that latches the counter value on a "
         "rising edge of an asynchronous external signal. What CDC measures "
         "are needed?",
         "Write the FSM for a scatter-gather DMA channel: fetch descriptor, "
         "issue read bursts, issue write bursts, write back status, follow "
         "`next`. Where do errors abort the chain?",
         "Draw the address decode for the example SoC and write the linker "
         "script MEMORY section that matches it.",
         "For a 32 KB, 4-way cache with 64-byte lines and 32-bit addresses, "
         "compute the tag, index and offset widths and the tag RAM size."],
        ordered=True)
