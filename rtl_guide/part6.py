"""Part VI - Projects and the Roadmap (Chapters 27-30).

All Verilog/SystemVerilog below was simulated with Icarus Verilog 12
(iverilog -g2012 -Wall; vvp) and every out() card is pasted from that run.
"""

from rtl_guide.common import *  # noqa: F401,F403

# ---------------------------------------------------------------------------
# Verified sources (kept verbatim so the listings match what was simulated)
# ---------------------------------------------------------------------------
TMR_SV = r"""
`timescale 1ns/1ps
// ----------------------------------------------------------------------------
// Module   : tmr_timeout
// Purpose  : Counts enabled cycles; o_expired rises when the count hits i_limit
// Clocking : single domain i_clk
// Reset    : i_rst_n, active low, async assert / sync deassert (see Ch. 12)
// ----------------------------------------------------------------------------
module tmr_timeout #(
  parameter int unsigned CNT_W = 16              // counter width in bits
) (
  input  logic             i_clk,
  input  logic             i_rst_n,
  input  logic             i_en,                 // count enable
  input  logic             i_clr,                // sync clear, beats i_en
  input  logic [CNT_W-1:0] i_limit,              // must be static while i_en
  output logic             o_expired             // registered level output
);
  logic [CNT_W-1:0] cnt_q, cnt_d;
  logic             expired_q, expired_d;

  // Next-state logic: combinational only, every output defaulted first
  always_comb begin
    cnt_d     = cnt_q;
    expired_d = expired_q;
    if (i_clr) begin
      cnt_d     = '0;
      expired_d = 1'b0;
    end else if (i_en && !expired_q) begin
      cnt_d     = cnt_q + 1'b1;
      expired_d = (cnt_d == i_limit);
    end
  end

  // State: flops only, nothing else in this block
  always_ff @(posedge i_clk or negedge i_rst_n)
    if (!i_rst_n) begin
      cnt_q     <= '0;
      expired_q <= 1'b0;
    end else begin
      cnt_q     <= cnt_d;
      expired_q <= expired_d;
    end

  assign o_expired = expired_q;
endmodule
"""

TB_TMR = r"""
`timescale 1ns/1ps
module tb_tmr;
  logic clk = 0, rst_n = 0, en = 0, clr = 0, expired;
  tmr_timeout #(.CNT_W(4)) dut (.i_clk(clk), .i_rst_n(rst_n), .i_en(en),
                                .i_clr(clr), .i_limit(4'd5), .o_expired(expired));
  always #5 clk = ~clk;
  always @(posedge expired) $display("%0d ns: expired, cnt=%0d", $time, dut.cnt_q);
  initial begin
    #12 rst_n = 1;
    @(negedge clk) en = 1;
    repeat (8) @(negedge clk);
    $display("%0d ns: still expired=%0b, cnt=%0d (saturates)", $time, expired, dut.cnt_q);
    clr = 1; @(negedge clk) clr = 0;
    $display("%0d ns: after clr expired=%0b cnt=%0d", $time, expired, dut.cnt_q);
    repeat (6) @(negedge clk);
    $finish;
  end
endmodule
"""

UART_FIFO = r"""
`timescale 1ns/1ps
// Synchronous first-word-fall-through FIFO: rdata shows the head entry.
module uart_fifo #(parameter int W = 8, parameter int AW = 3) (
  input  logic         clk, rst_n,
  input  logic         push, pop,
  input  logic [W-1:0] wdata,
  output logic [W-1:0] rdata,
  output logic         empty, full
);
  logic [W-1:0] mem [2**AW];
  logic [AW:0]  wptr_q, rptr_q;              // extra MSB tells full from empty
  assign empty = (wptr_q == rptr_q);
  assign full  = (wptr_q == {~rptr_q[AW], rptr_q[AW-1:0]});
  assign rdata = mem[rptr_q[AW-1:0]];
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      wptr_q <= '0;
      rptr_q <= '0;
    end else begin
      if (push && !full)  wptr_q <= wptr_q + 1'b1;
      if (pop  && !empty) rptr_q <= rptr_q + 1'b1;
    end
  always_ff @(posedge clk)                   // storage: no reset needed
    if (push && !full) mem[wptr_q[AW-1:0]] <= wdata;
endmodule
"""

UART_TX = r"""
`timescale 1ns/1ps
// 8N1 transmitter. tick16 is a 1-cycle enable at 16x the baud rate.
module uart_tx (
  input  logic       clk, rst_n,
  input  logic       tick16,
  input  logic       start,        // 1-cycle: load data and begin a frame
  input  logic [7:0] data,
  output logic       busy,
  output logic       txd           // registered: glitch-free pad output
);
  typedef enum logic [1:0] {IDLE, START, DATA, STOP} state_t;
  state_t     st_q;
  logic [3:0] os_q;                // oversample count 0..15 = one bit time
  logic [2:0] bit_q;
  logic [7:0] sh_q;
  assign busy = (st_q != IDLE);
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      st_q <= IDLE; os_q <= '0; bit_q <= '0; sh_q <= '0; txd <= 1'b1;
    end else case (st_q)
      IDLE:  if (start) begin
               sh_q <= data; os_q <= '0; txd <= 1'b0; st_q <= START;
             end
      START: if (tick16) begin
               os_q <= os_q + 1'b1;
               if (os_q == 4'd15) begin
                 txd <= sh_q[0]; bit_q <= '0; st_q <= DATA;
               end
             end
      DATA:  if (tick16) begin
               os_q <= os_q + 1'b1;
               if (os_q == 4'd15) begin
                 sh_q <= {1'b0, sh_q[7:1]};           // LSB first
                 if (bit_q == 3'd7) begin txd <= 1'b1; st_q <= STOP; end
                 else begin txd <= sh_q[1]; bit_q <= bit_q + 1'b1; end
               end
             end
      STOP:  if (tick16) begin
               os_q <= os_q + 1'b1;
               if (os_q == 4'd15) st_q <= IDLE;
             end
      default: st_q <= IDLE;
    endcase
endmodule
"""

UART_RX = r"""
`timescale 1ns/1ps
// 8N1 receiver: 2-flop synchronizer, 16x oversampling, mid-bit sampling.
module uart_rx (
  input  logic       clk, rst_n,
  input  logic       tick16,
  input  logic       rxd_async,    // straight from the pad: asynchronous
  output logic       valid,        // 1-cycle pulse with a good byte
  output logic [7:0] data,
  output logic       frame_err     // 1-cycle pulse: stop bit was 0
);
  logic [1:0] sync_q;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) sync_q <= 2'b11;                    // idle line is high
    else        sync_q <= {sync_q[0], rxd_async};
  wire rxd = sync_q[1];

  typedef enum logic [1:0] {IDLE, START, DATA, STOP} state_t;
  state_t     st_q;
  logic [3:0] os_q;
  logic [2:0] bit_q;
  logic [7:0] sh_q;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      st_q <= IDLE; os_q <= '0; bit_q <= '0; sh_q <= '0;
      valid <= 1'b0; data <= '0; frame_err <= 1'b0;
    end else begin
      valid <= 1'b0; frame_err <= 1'b0;
      case (st_q)
        IDLE:  if (!rxd) begin os_q <= '0; st_q <= START; end
        START: if (tick16) begin
                 if (os_q == 4'd7) begin                // middle of start bit
                   if (rxd) st_q <= IDLE;               // glitch: false start
                   else begin os_q <= '0; bit_q <= '0; st_q <= DATA; end
                 end else os_q <= os_q + 1'b1;
               end
        DATA:  if (tick16) begin
                 if (os_q == 4'd15) begin               // 16 ticks later = mid-bit
                   os_q <= '0; sh_q <= {rxd, sh_q[7:1]};
                   if (bit_q == 3'd7) st_q <= STOP;
                   else bit_q <= bit_q + 1'b1;
                 end else os_q <= os_q + 1'b1;
               end
        STOP:  if (tick16) begin
                 if (os_q == 4'd15) begin
                   st_q <= IDLE; data <= sh_q;
                   valid <= rxd; frame_err <= !rxd;
                 end else os_q <= os_q + 1'b1;
               end
        default: st_q <= IDLE;
      endcase
    end
endmodule
"""

UART_APB = r"""
`timescale 1ns/1ps
// APB UART subsystem: registers, baud generator, FIFOs, TX, RX, interrupt.
module uart_apb (
  input  logic        pclk, presetn,
  input  logic        psel, penable, pwrite,
  input  logic [4:0]  paddr,
  input  logic [31:0] pwdata,
  output logic [31:0] prdata,
  output logic        pready, pslverr,
  output logic        irq,
  output logic        txd,
  input  logic        rxd
);
  localparam logic [4:0] A_DATA = 5'h00, A_STAT = 5'h04, A_CTRL = 5'h08,
                         A_BAUD = 5'h0C, A_IEN  = 5'h10, A_ISTAT = 5'h14;
  logic [2:0]  ctrl_q;              // [0] TX_EN [1] RX_EN [2] LOOPBACK
  logic [15:0] baud_q, bcnt_q;
  logic [3:0]  ien_q, ist_q;
  logic        tick16, tx_busy, tx_busy_q, rx_valid, rx_ferr;
  logic        txf_empty, txf_full, rxf_empty, rxf_full;
  logic [7:0]  txf_dout, rxf_dout, rx_data;

  wire wr = psel & penable &  pwrite;              // APB access phase
  wire rd = psel & penable & ~pwrite;
  assign pready  = 1'b1;                           // zero-wait-state slave
  assign pslverr = 1'b0;

  // Baud generator: one tick16 every (BAUD_DIV + 1) pclk cycles
  assign tick16 = (bcnt_q >= baud_q);
  always_ff @(posedge pclk or negedge presetn)
    if (!presetn)    bcnt_q <= '0;
    else if (tick16) bcnt_q <= '0;
    else             bcnt_q <= bcnt_q + 1'b1;

  // TX path: APB write to DATA pushes; the FSM pops when idle
  wire tx_start = ctrl_q[0] & ~txf_empty & ~tx_busy;
  uart_fifo u_txf (.clk(pclk), .rst_n(presetn), .push(wr && paddr == A_DATA),
                   .pop(tx_start), .wdata(pwdata[7:0]), .rdata(txf_dout),
                   .empty(txf_empty), .full(txf_full));
  uart_tx u_tx (.clk(pclk), .rst_n(presetn), .tick16(tick16), .start(tx_start),
                .data(txf_dout), .busy(tx_busy), .txd(txd));

  // RX path: the FSM pushes; an APB read of DATA pops
  wire rx_in   = ctrl_q[2] ? txd : rxd;            // internal loopback mux
  wire rx_push = rx_valid & ctrl_q[1];
  uart_rx u_rx (.clk(pclk), .rst_n(presetn), .tick16(tick16), .rxd_async(rx_in),
                .valid(rx_valid), .data(rx_data), .frame_err(rx_ferr));
  uart_fifo u_rxf (.clk(pclk), .rst_n(presetn), .push(rx_push),
                   .pop(rd && paddr == A_DATA), .wdata(rx_data), .rdata(rxf_dout),
                   .empty(rxf_empty), .full(rxf_full));

  // Interrupts: sticky event bits, write-1-to-clear, set wins over clear
  // [0] RX_DONE  [1] TX_DONE  [2] RX_OVERRUN  [3] FRAME_ERR
  wire [3:0] evt = {rx_ferr, rx_push & rxf_full, tx_busy_q & ~tx_busy & txf_empty,
                    rx_push & ~rxf_full};
  wire [3:0] w1c = (wr && paddr == A_ISTAT) ? pwdata[3:0] : 4'h0;
  always_ff @(posedge pclk or negedge presetn)
    if (!presetn) begin ist_q <= '0; tx_busy_q <= 1'b0; end
    else begin
      ist_q     <= (ist_q & ~w1c) | evt;
      tx_busy_q <= tx_busy;
    end
  assign irq = |(ist_q & ien_q);

  // Read/write control registers
  always_ff @(posedge pclk or negedge presetn)
    if (!presetn) begin
      ctrl_q <= 3'b011; baud_q <= 16'd26; ien_q <= '0;   // 115200 @ 50 MHz
    end else if (wr) begin
      case (paddr)
        A_CTRL: ctrl_q <= pwdata[2:0];
        A_BAUD: baud_q <= pwdata[15:0];
        A_IEN:  ien_q  <= pwdata[3:0];
        default: ;
      endcase
    end

  always_comb
    case (paddr)
      A_DATA:  prdata = {24'h0, rxf_dout};
      A_STAT:  prdata = {27'h0, tx_busy, txf_full, txf_empty, rxf_full, ~rxf_empty};
      A_CTRL:  prdata = {29'h0, ctrl_q};
      A_BAUD:  prdata = {16'h0, baud_q};
      A_IEN:   prdata = {28'h0, ien_q};
      A_ISTAT: prdata = {28'h0, ist_q};
      default: prdata = 32'h0;
    endcase
endmodule
"""

TB_UART = r"""
`timescale 1ns/1ps
module tb_uart;
  logic        pclk = 0, presetn = 0;
  logic        psel = 0, penable = 0, pwrite = 0;
  logic [4:0]  paddr = '0;
  logic [31:0] pwdata = '0, prdata;
  logic        pready, pslverr, irq, txd, ext_lb = 1;
  wire         rxd = ext_lb ? txd : 1'b1;          // external loopback wire
  int          errors = 0, checked = 0;
  byte         exp_q[$];

  uart_apb dut (.*);
  always #5 pclk = ~pclk;                          // 100 MHz

  task automatic apb_write(input logic [4:0] a, input logic [31:0] d);
    @(posedge pclk); psel <= 1; penable <= 0; pwrite <= 1; paddr <= a; pwdata <= d;
    @(posedge pclk); penable <= 1;
    @(posedge pclk); psel <= 0; penable <= 0;
  endtask
  task automatic apb_read(input logic [4:0] a, output logic [31:0] d);
    @(posedge pclk); psel <= 1; penable <= 0; pwrite <= 0; paddr <= a;
    @(posedge pclk); penable <= 1;
    @(negedge pclk); d = prdata;                   // sample before the edge
    @(posedge pclk); psel <= 0; penable <= 0;
  endtask
  // Send one byte: wait for TX FIFO space, write DATA, remember the byte
  task automatic send(input byte b);
    logic [31:0] st;
    do apb_read(5'h04, st); while (st[3]);         // STATUS.TX_FULL
    apb_write(5'h00, {24'h0, b});
    exp_q.push_back(b);
  endtask
  // Drain: pop every received byte and compare against the model queue
  task automatic drain(input int n);
    logic [31:0] st, d;
    repeat (n) begin
      do apb_read(5'h04, st); while (!st[0]);      // STATUS.RX_AVAIL
      apb_read(5'h00, d);
      checked++;
      if (d[7:0] !== exp_q[0]) begin
        errors++;
        $display("  MISMATCH: got %h expected %h", d[7:0], exp_q[0]);
      end
      void'(exp_q.pop_front());
    end
  endtask

  initial begin
    logic [31:0] st;
    repeat (3) @(posedge pclk);
    presetn = 1;
    apb_write(5'h0C, 32'd3);                       // BAUD_DIV: tick16 every 4 clk
    apb_write(5'h10, 32'h1);                       // INT_EN: RX_DONE
    // Test 1: directed bytes, one at a time; check irq and W1C
    send(8'h55);
    wait (irq);
    $display("[%0d ns] irq after first byte, INT_STATUS read next", $time);
    apb_read(5'h14, st);
    $display("  INT_STATUS = %b", st[3:0]);
    apb_write(5'h14, 32'h1);                       // W1C the RX_DONE bit
    @(posedge pclk);
    $display("  after W1C irq = %0b", irq);
    drain(1);
    // Test 2: 40 random bytes, streamed through both 8-deep FIFOs
    apb_write(5'h10, 32'h0);
    for (int i = 0; i < 40; i++) begin             // one bus master thread:
      send($urandom);                              // interleave TX writes
      apb_read(5'h04, st);                         // with opportunistic
      if (st[0]) drain(1);                         // RX reads
    end
    drain(exp_q.size());
    $display("[%0d ns] random stream done, %0d bytes checked so far", $time, checked);
    // Test 3: internal loopback, external wire held idle
    ext_lb = 0;
    apb_write(5'h08, 32'b111);
    repeat (4) send($urandom);
    drain(4);
    // Test 4: overrun - send 10 bytes without reading; FIFO keeps the first 8
    ext_lb = 1; apb_write(5'h08, 32'b011);
    repeat (10) send($urandom);
    do apb_read(5'h04, st); while (st[4] || !st[2]); // TX_BUSY or !TX_EMPTY
    repeat (100) @(posedge pclk);
    apb_read(5'h14, st);
    $display("[%0d ns] after 10 unread bytes: STATUS.RX_FULL=%0b OVERRUN=%0b",
             $time, dut.rxf_full, st[2]);
    drain(8);
    exp_q.delete();
    $display("RESULT: %0d bytes checked, %0d errors -> %s", checked, errors,
             errors == 0 ? "PASS" : "FAIL");
    $finish;
  end
  initial begin #5ms $display("TIMEOUT"); $finish; end
endmodule
"""

MAC_SV = r"""
`timescale 1ns/1ps
// int8 x int8 dot-product engine with requantization and zero-skipping.
// s_tdata = {w[L-1],...,w[0], a[L-1],...,a[0]}; s_tlast ends a vector.
module mac_accel #(parameter int L = 4) (
  input  logic              clk, rst_n,
  input  logic              csr_we,              // simple CSR port
  input  logic [4:0]        csr_addr,
  input  logic [31:0]       csr_wdata,
  output logic [31:0]       csr_rdata,
  input  logic              s_tvalid,            // AXI4-Stream slave
  output logic              s_tready,
  input  logic [16*L-1:0]   s_tdata,
  input  logic              s_tlast,
  output logic              m_tvalid,            // AXI4-Stream master
  input  logic              m_tready,
  output logic [7:0]        m_tdata
);
  localparam logic [4:0] A_CTRL = 5'h00, A_MULT = 5'h04, A_SHIFT = 5'h08,
                         A_ZP   = 5'h0C, A_BIAS = 5'h10, A_SKIP  = 5'h14,
                         A_MACS = 5'h18;
  logic               zskip_q;                   // CTRL[0]: zero-skip enable
  logic [15:0]        mult_q;                    // requant multiplier (Q0.16)
  logic [4:0]         shift_q;                   // requant right shift
  logic signed [7:0]  zp_q;                      // output zero point
  logic signed [31:0] bias_q;
  logic [31:0]        skip_cnt_q, mac_cnt_q;

  // Global-stall pipeline: every stage advances unless the output is blocked
  wire en   = !m_tvalid || m_tready;
  assign s_tready = en;
  wire take = s_tvalid && s_tready;

  // ---------------- S1: operand registers with operand isolation ----------
  logic [L-1:0]      nz_in, nz1_q;               // lane has a non-zero weight
  logic signed [7:0] a1_q [L], w1_q [L];
  logic              v1_q, last1_q;
  int                nskip;
  always_comb begin
    nskip = 0;
    for (int i = 0; i < L; i++) begin
      nz_in[i] = !zskip_q || (s_tdata[8*(L+i) +: 8] != 8'h00);
      nskip    = nskip + {31'b0, !nz_in[i]};
    end
  end
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin v1_q <= 1'b0; last1_q <= 1'b0; nz1_q <= '0; end
    else if (en) begin
      v1_q <= take; last1_q <= s_tlast;
      if (take) nz1_q <= nz_in;
    end
  always_ff @(posedge clk)                       // skipped lanes hold their
    for (int i = 0; i < L; i++)                  // operands: the multiplier
      if (take && nz_in[i]) begin                // inputs do not toggle
        a1_q[i] <= s_tdata[8*i     +: 8];
        w1_q[i] <= s_tdata[8*(L+i) +: 8];
      end

  // ---------------- S2: multiply, adder tree, int32 accumulator -----------
  logic signed [31:0] sum2, acc_q, acc2_q;
  logic               v2_q;
  always_comb begin
    sum2 = '0;
    for (int i = 0; i < L; i++)
      if (nz1_q[i]) sum2 = sum2 + a1_q[i] * w1_q[i];   // 8x8 -> 16 bit, signed
  end
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin acc_q <= '0; acc2_q <= '0; v2_q <= 1'b0; end
    else if (en) begin
      v2_q <= v1_q && last1_q;
      if (v1_q && last1_q) begin acc2_q <= acc_q + sum2; acc_q <= '0; end
      else if (v1_q)       acc_q <= acc_q + sum2;
    end

  // ---------------- S3: requant multiply (acc + bias) * M -----------------
  logic signed [49:0] prod3_q;
  logic               v3_q;
  wire  signed [32:0] biased = 33'(acc2_q) + 33'(bias_q);
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin prod3_q <= '0; v3_q <= 1'b0; end
    else if (en) begin
      v3_q <= v2_q;
      if (v2_q) prod3_q <= biased * $signed({1'b0, mult_q});
    end

  // ---------------- S4: round, shift, add zero point, saturate ------------
  logic signed [49:0] rnd, shd;
  always_comb begin
    rnd = (shift_q == 5'd0) ? prod3_q : prod3_q + (50'sd1 <<< (shift_q - 5'd1));
    shd = (rnd >>> shift_q) + 50'(zp_q);
  end
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin m_tvalid <= 1'b0; m_tdata <= '0; end
    else if (en) begin
      m_tvalid <= v3_q;
      if (v3_q) m_tdata <= (shd >  50'sd127) ? 8'h7F :
                           (shd < -50'sd128) ? 8'h80 : shd[7:0];
    end

  // ---------------- CSRs and performance counters -------------------------
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      zskip_q <= 1'b1; mult_q <= 16'd1; shift_q <= '0; zp_q <= '0; bias_q <= '0;
      skip_cnt_q <= '0; mac_cnt_q <= '0;
    end else begin
      if (take) begin
        mac_cnt_q  <= mac_cnt_q  + L;
        skip_cnt_q <= skip_cnt_q + nskip;
      end
      if (csr_we)
        case (csr_addr)
          A_CTRL:  zskip_q    <= csr_wdata[0];
          A_MULT:  mult_q     <= csr_wdata[15:0];
          A_SHIFT: shift_q    <= csr_wdata[4:0];
          A_ZP:    zp_q       <= csr_wdata[7:0];
          A_BIAS:  bias_q     <= csr_wdata;
          A_SKIP:  skip_cnt_q <= '0;             // write = clear (wins)
          A_MACS:  mac_cnt_q  <= '0;
          default: ;
        endcase
    end
  always_comb
    case (csr_addr)
      A_CTRL:  csr_rdata = {31'b0, zskip_q};
      A_MULT:  csr_rdata = {16'b0, mult_q};
      A_SHIFT: csr_rdata = {27'b0, shift_q};
      A_ZP:    csr_rdata = 32'(zp_q);                // sign-extends
      A_BIAS:  csr_rdata = bias_q;
      A_SKIP:  csr_rdata = skip_cnt_q;
      A_MACS:  csr_rdata = mac_cnt_q;
      default: csr_rdata = '0;
    endcase
endmodule
"""

TB_MAC = r"""
`timescale 1ns/1ps
module tb_mac;
  localparam int L = 4;
  logic clk = 0, rst_n = 0;
  logic csr_we = 0; logic [4:0] csr_addr = '0; logic [31:0] csr_wdata = '0, csr_rdata;
  logic s_tvalid = 0, s_tready, s_tlast = 0; logic [16*L-1:0] s_tdata = '0;
  logic m_tvalid, m_tready = 0; logic [7:0] m_tdata;
  mac_accel #(.L(L)) dut (.*);
  always #5 clk = ~clk;

  int  mult, shift, zp, bias, ready_pct;          // current configuration
  byte exp_q[$];
  int  errors = 0, outs = 0, sats = 0;
  longint exp_skip;

  // Golden model: exactly the arithmetic the spec defines, in 64-bit integers
  function automatic byte requant(longint acc);
    longint v = (acc + bias) * mult;
    if (shift > 0) v = v + (longint'(1) <<< (shift - 1));   // round half up
    v = (v >>> shift) + zp;
    if (v > 127 || v < -128) sats++;
    return (v > 127) ? 8'sd127 : (v < -128) ? -8'sd128 : byte'(v);
  endfunction

  task automatic csr_write(input logic [4:0] a, input logic [31:0] d);
    @(posedge clk); csr_we <= 1; csr_addr <= a; csr_wdata <= d;
    @(posedge clk); csr_we <= 0;
  endtask
  task automatic csr_read(input logic [4:0] a, output logic [31:0] d);
    @(posedge clk); csr_addr <= a; @(negedge clk); d = csr_rdata;
  endtask

  // Drive one vector of n beats; weights are zero with probability sp_pct
  task automatic send_vec(input int n, input int sp_pct, input bit zskip);
    longint acc = 0;
    for (int b = 0; b < n; b++) begin
      logic [16*L-1:0] d;
      for (int i = 0; i < L; i++) begin
        byte a = $urandom, w = ($urandom_range(0, 99) < sp_pct) ? 0 : $urandom;
        d[8*i +: 8] = a; d[8*(L+i) +: 8] = w;
        acc += a * w;
        if (zskip && w == 0) exp_skip++;
      end
      while ($urandom_range(0, 99) < 30) @(posedge clk);  // random idle gaps
      s_tvalid <= 1; s_tdata <= d; s_tlast <= (b == n - 1);
      do @(posedge clk); while (!s_tready);        // hold until handshake
      s_tvalid <= 0;
    end
    exp_q.push_back(requant(acc));
  endtask

  always @(posedge clk) begin                      // random backpressure
    m_tready <= ($urandom_range(0, 99) < ready_pct);
    if (m_tvalid && m_tready) begin                // scoreboard
      outs++;
      if (m_tdata !== exp_q[0]) begin
        errors++;
        if (errors < 5) $display("  MISMATCH got %0d exp %0d", $signed(m_tdata), exp_q[0]);
      end
      void'(exp_q.pop_front());
    end
  end

  task automatic run(string name, bit zs, int m, int s, int z, int bi, int sp, int nv);
    logic [31:0] skips, macs; int t0 = $time, e0 = errors, o0 = outs, s0 = sats;
    mult = m; shift = s; zp = z; bias = bi; exp_skip = 0;
    csr_write(5'h00, zs); csr_write(5'h04, m); csr_write(5'h08, s);
    csr_write(5'h0C, z);  csr_write(5'h10, bi);
    csr_write(5'h14, 0);  csr_write(5'h18, 0);    // clear counters
    repeat (nv) send_vec($urandom_range(1, 16), sp, zs);
    while (exp_q.size() != 0) @(posedge clk);      // drain the pipeline
    csr_read(5'h14, skips); csr_read(5'h18, macs);
    $display("%-9s vec=%0d out=%0d err=%0d sat=%0d MACs=%0d skipped=%0d (exp %0d) %0d ns",
             name, nv, outs - o0, errors - e0, sats - s0, macs, skips, exp_skip,
             ($time - t0));
    if (skips != exp_skip) errors++;
  endtask

  initial begin
    repeat (2) @(posedge clk); rst_n = 1;
    ready_pct = 100;
    run("dense",   0, 16384, 24,  0,    0,  0, 200);  // scale 1/1024
    ready_pct = 60;
    run("pruned",  1, 16384, 24,  3, -500, 75, 200);  // 75% zero weights
    run("saturate",1, 65535, 23, -5, 1000, 50, 100);
    $display("RESULT: %0d vectors checked, %0d errors -> %s", outs, errors,
             errors == 0 ? "PASS" : "FAIL");
    $finish;
  end
  initial begin #10ms $display("TIMEOUT"); $finish; end
endmodule
"""

DIV3_SV = r"""
`timescale 1ns/1ps
// Serial input, MSB first: o_div3 is 1 when the bits seen so far form a
// number divisible by 3.  State = remainder; next = (2*rem + bit) mod 3.
module div3_detect (
  input  logic i_clk, i_rst_n, i_valid, i_bit,
  output logic o_div3
);
  logic [1:0] rem_q, rem_d;
  always_comb
    case ({rem_q, i_bit})
      3'b00_0: rem_d = 2'd0;   3'b00_1: rem_d = 2'd1;
      3'b01_0: rem_d = 2'd2;   3'b01_1: rem_d = 2'd0;
      3'b10_0: rem_d = 2'd1;   3'b10_1: rem_d = 2'd2;
      default: rem_d = 2'd0;                    // 2'b11 unreachable: recover
    endcase
  always_ff @(posedge i_clk or negedge i_rst_n)
    if (!i_rst_n)     rem_q <= 2'd0;
    else if (i_valid) rem_q <= rem_d;
  assign o_div3 = (rem_q == 2'd0);
endmodule
"""

TB_DIV3 = r"""
`timescale 1ns/1ps
module tb_div3;
  logic clk = 0, rst_n = 0, valid = 0, b = 0, div3;
  int   errors = 0;
  div3_detect dut (.i_clk(clk), .i_rst_n(rst_n), .i_valid(valid), .i_bit(b),
                   .o_div3(div3));
  always #5 clk = ~clk;
  initial begin
    logic [7:0] n;
    #12 rst_n = 1;
    for (int k = 0; k < 256; k++) begin
      n = k[7:0];
      rst_n = 0; #1 rst_n = 1;                  // restart for each number
      for (int i = 7; i >= 0; i--) begin
        @(negedge clk) valid = 1; b = n[i];
      end
      @(negedge clk) valid = 0;
      if (div3 !== (n % 3 == 0)) errors++;
      if (k == 9 || k == 10 || k == 255) $display("n=%3d bits=%b div3=%0b", n, n, div3);
    end
    $display("all 256 8-bit numbers checked, %0d errors", errors);
    $finish;
  end
endmodule
"""

STYLE_SNIP = r"""
`timescale 1ns/1ps
`default_nettype none
module fifo_cfg #(
  parameter int unsigned DEPTH = 8,
  parameter int unsigned W     = 32
) (
  input  wire logic         i_clk,
  input  wire logic [W-1:0] i_data,
  output      logic [W-1:0] o_data
);
  localparam int unsigned AW = $clog2(DEPTH);       // derived, not overridable
  // Elaboration-time check (IEEE 1800-2009): stops the build in lint/synthesis
  if (DEPTH < 2 || (DEPTH & (DEPTH - 1)) != 0) begin : g_bad_depth
    $error("fifo_cfg: DEPTH=%0d must be a power of two >= 2", DEPTH);
  end
  // Simulation-time twin for simulators that ignore elaboration tasks
  // synopsys translate_off
  initial if (DEPTH < 2 || (DEPTH & (DEPTH - 1)) != 0)
    $fatal(1, "fifo_cfg: DEPTH=%0d must be a power of two >= 2", DEPTH);
  // synopsys translate_on
  logic [AW-1:0] ptr_q = '0;
  always_ff @(posedge i_clk) ptr_q <= ptr_q + 1'b1;
  assign o_data = i_data;
endmodule
module mix_bad (input wire logic clk, rst_n, in_valid, input wire logic [7:0] in_data,
                output logic valid_q, output logic [7:0] data_q);
  // BAD: data_q has no reset but shares a block with a reset flop
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) valid_q <= 1'b0;
    else begin
      valid_q <= in_valid;
      data_q  <= in_data;      // rst_n silently becomes a hold-enable
    end
endmodule
module mix_good (input wire logic clk, rst_n, in_valid, input wire logic [7:0] in_data,
                 output logic valid_q, output logic [7:0] data_q);
  always_ff @(posedge clk or negedge rst_n)      // control: reset
    if (!rst_n) valid_q <= 1'b0;
    else        valid_q <= in_valid;
  always_ff @(posedge clk)                       // datapath: no reset
    if (in_valid) data_q <= in_data;
endmodule
`default_nettype wire
module top; logic [31:0] a,b,b2; logic c=0;
  fifo_cfg #(.DEPTH(8)) ok (.i_clk(c), .i_data(a), .o_data(b));
  fifo_cfg #(.DEPTH(6)) bad (.i_clk(c), .i_data(a), .o_data(b2));
endmodule
"""


def _lines(src):
    return src.strip("\n").split("\n")


def _seg(src, start=None, end=None):
    """Lines of src from the first line containing `start` (or the top) up to,
    not including, the first later line containing `end` (or the bottom)."""
    ls = _lines(src)
    i = 0
    if start is not None:
        i = next(k for k, l in enumerate(ls) if start in l)
    j = len(ls)
    if end is not None:
        j = next(k for k, l in enumerate(ls) if k > i and end in l)
    while j > i and not ls[j - 1].strip():
        j -= 1
    return ls[i:j]


# =============================================================================
#                     PART VI - PROJECTS AND THE ROADMAP
# =============================================================================
def part6():
    part("Projects and the Roadmap",
         "The habits that make RTL reviewable and reusable; two complete, "
         "simulated projects - an APB UART subsystem and an AXI-Stream int8 MAC "
         "accelerator for on-device ML - that put every earlier chapter to "
         "work; and a staged career roadmap with a study plan, portfolio ideas "
         "and an honest look at how RTL interviews are run.")
    _ch27()
    _ch28()
    _ch29()
    _ch30()


# ------------------------------------------------------------------ Ch 27 ---
def _ch27():
    chapter("RTL Coding Guidelines and Design Reviews", newpage=False)
    p("Every serious chip company has an RTL coding guideline, and on the surface "
      "they look like a list of style preferences: suffixes, indentation, where "
      "the reset goes. They are not. Each rule exists because someone, somewhere, "
      "shipped a bug, lost a week in a CDC review, or taped out a latch. A "
      "guideline is a compressed record of expensive mistakes, and the design "
      "review is the process that enforces it where tools cannot.")
    p("This chapter collects the rules that almost every company shares, explains "
      "the reason behind each, and then turns them into a working review "
      "process: a micro-architecture spec template, a review checklist, the "
      "findings reviewers raise most often, and the git and regression "
      "discipline that keeps a design healthy for the two years between the "
      "first commit and tapeout.")

    h2("Why guidelines exist")
    tbl(["Audience", "What consistent RTL buys them"],
        [["**Reviewers**", "A reviewer who knows that every `_q` is a flop and "
          "every `_d` is its next-state value can read a 2000-line module in an "
          "hour instead of a day, and spots the one signal that breaks the pattern"],
         ["**Lint, CDC and RDC tools** (Ch. 25)", "Tools classify signals by name "
          "and structure: clock and reset naming lets them infer domains, and "
          "consistent synchronizer cells let CDC tools recognize approved "
          "crossings instead of flagging hundreds of false violations"],
         ["**Synthesis and STA** (Ch. 17-18)", "Predictable structure gives "
          "predictable netlists: register names survive into the netlist, so "
          "`u_rx/st_q_reg[1]` in a timing report maps straight back to the RTL"],
         ["**Verification** (Ch. 22-24)", "Uniform handshakes and register "
          "conventions let one agent or one register model serve every block"],
         ["**Your future self**", "Blocks are reused across three or four chip "
          "generations. The engineer who modifies your FIFO in 2029 may be you"]],
        widths=[28, 72], bold_first=False)
    box("key", "The one-sentence philosophy",
        "Write RTL so that **the hardware is obvious from the text**: a reader "
        "should be able to draw every flop, every mux and every clock domain "
        "without simulating anything. Every rule below serves that goal.")

    h2("Naming conventions")
    p("Names carry type information that Verilog itself does not. The table is a "
      "composite of widely used industrial conventions (lowRISC/OpenTitan, many "
      "in-house guides); individual companies differ in details, but **pick one "
      "convention per project and apply it without exception** - a convention "
      "applied 90% of the time is worse than none, because readers trust it.")
    tbl(["Pattern", "Meaning", "Example"],
        [["`_q`", "Output of a flop (current state)", "`cnt_q`, `st_q`"],
         ["`_d`", "Next-state value computed combinationally, input of the `_q` flop",
          "`cnt_d`"],
         ["`_n` / `_ni`", "Active-low signal (lowRISC uses `_ni`/`_no` for "
          "active-low ports)", "`rst_n`, `cs_n`"],
         ["`i_` / `o_` / `io_` prefix, or `_i` / `_o` suffix",
          "Port direction, visible at every use inside the module",
          "`i_valid`, `o_ready`"],
         ["`clk_<domain>`, `rst_<domain>_n`", "One name per clock and reset "
          "domain; the domain name travels with every signal of that domain",
          "`clk_axi`, `rst_apb_n`"],
         ["`_sync`, `_meta`", "Output and first stage of a synchronizer; CDC "
          "reviewers search for these", "`rxd_sync`"],
         ["`_async`", "Signal not yet synchronized to the local clock",
          "`rxd_async`"],
         ["`UPPER_CASE`", "Parameters, localparams, enum literals, macros",
          "`DEPTH`, `IDLE`"],
         ["`_t`", "User-defined type (typedef, enum, struct)", "`state_t`"],
         ["`u_` / `g_`", "Instance name / generate-block label", "`u_txf`, `g_lane`"],
         ["`<ip>_` module prefix", "All modules of one IP share a prefix, so "
          "names never collide at SoC integration", "`uart_tx`, `uart_rx`"]],
        widths=[30, 50, 20], caption="A representative naming convention. "
        "Direction prefixes and suffixes are equivalent; mixing them is not.")
    p("The `_q`/`_d` pair deserves a sentence of its own. It forces the "
      "**two-process** style (Ch. 6): one `always_comb` computes every `_d` from "
      "the current `_q`s and the inputs, one `always_ff` does nothing but "
      "`x_q <= x_d`. The payoff is that every flop's next-state logic is in one "
      "place, the register boundary is explicit, and the netlist names match. "
      "Many teams relax this for simple counters and pipeline registers written "
      "in a single `always_ff`, which is fine as long as the `_q` suffix still "
      "marks every flop - the Chapter 28 UART does exactly that.")
    box("warn", "PITFALL - names that lie",
        "A signal called `valid_q` that is actually combinational, or `rst_n` "
        "that is active high after an inverter somebody added later, is worse "
        "than an arbitrary name. Reviewers read names, not drivers. When a "
        "signal's nature changes, **rename it** in the same commit.")

    h2("File and module organization")
    bul(["**One module per file, file named after the module** (`uart_tx.sv` "
         "holds `module uart_tx`). Tools, filelists, code search and reviewers "
         "all assume it; a second module hidden at the bottom of a file is how "
         "two versions of the same module end up in one build.",
         "**Packages for shared types and constants** (`uart_pkg.sv`), compiled "
         "before their users. Prefer package parameters over global "
         "text macros (`define`), which leak across files in compilation order.",
         "The `default_nettype none` directive at the top of each RTL file (restored "
         "to `wire` at the bottom) **turns every typo in a port connection into a "
         "compile error** instead of a silently created 1-bit net.",
         "Include files (`.svh`) **get include guards** (`ifndef`/`define` directives), "
         "and contain declarations only.",
         "Filelists (`.f`) **are the single source of truth** for what is in the "
         "design; simulation, lint, synthesis and CDC all read the same list.",
         "**No testbench code in RTL files.** Assertions go in a separate bind "
         "file (Ch. 23) or behind a clearly marked `ifdef`."])
    diagram([
        "uart/                          one IP = one self-contained tree",
        "|-- doc/      uart_uarch.md    micro-architecture spec (27.9)",
        "|-- rtl/      uart_pkg.sv  uart_apb.sv  uart_tx.sv  uart_rx.sv  uart_fifo.sv",
        "|-- rdl/      uart.rdl         register description -> generated RTL/C/UVM",
        "|-- sva/      uart_sva.sv  uart_bind.sv",
        "|-- tb/       tb_uart.sv   (UVM env in tb/uvm/)",
        "|-- lint/     waivers.tcl      every waiver has a reason and an owner",
        "|-- syn/      uart.sdc         block-level constraints (Ch. 18)",
        "|-- uart.f                     filelist: package first, then leaf modules",
        "`-- Makefile                   make sim | lint | cdc | syn | regress",
    ], "A typical IP directory. The point is that an integrator can take the "
       "whole directory and nothing else.")

    h2("Parameterization")
    p("Parameters make a block reusable; badly chosen parameters make it "
      "unverifiable. The rules: give every parameter a **type** and a sensible "
      "**default**; expose only what an integrator should change; compute "
      "everything else as a `localparam`; and **check illegal values at "
      "elaboration** so a bad configuration fails the build rather than the "
      "silicon.")
    code(_seg(STYLE_SNIP, "module fifo_cfg", "logic [AW-1:0]")
         + ["  // ... pointers and storage ...", "endmodule"],
         "Typed parameters, a derived localparam, and two layers of checking.")
    out(["FATAL: snip.sv:19: fifo_cfg: DEPTH=6 must be a power of two >= 2",
         "       Time: 0  Scope: top.bad"],
        "Instantiating `fifo_cfg #(.DEPTH(6))` in Icarus Verilog 12. Icarus "
        "silently ignores the elaboration-time `$error` in the generate block, "
        "which is exactly why the `initial` twin exists; Verilator, lint tools "
        "and commercial simulators honor the elaboration check.")
    bul(["Every parameter combination you allow is a design you must verify. "
         "Document the **supported** range and regress at least the corners "
         "(minimum, maximum, one typical value).",
         "Never let a parameter change the **interface protocol**; change widths "
         "and depths, not behavior. Two behaviors belong in two modules or an "
         "explicit mode port.",
         "Use `$clog2` for pointer widths, and remember `$clog2(1) = 0` - a "
         "zero-width vector is illegal, which is one reason DEPTH >= 2 is enforced."])

    h2("Reset and clock rules")
    tbl(["Rule", "Why"],
        [["One clock per `always_ff`, named `clk_<domain>`", "Each flop belongs "
          "to exactly one domain; STA, CDC and DFT tools all depend on it"],
         ["No logic, muxes or dividers on clock nets in RTL; use the library "
          "clock-gating (ICG) cell through a wrapper", "Gated clocks built from "
          "AND gates glitch and break STA and scan (Ch. 19-20)"],
         ["Asynchronous assert, synchronous de-assert resets (Ch. 12)",
          "Reset works with no clock, and release never violates recovery/removal"],
         ["Reset control flops; do not reset pure datapath flops", "Reset flops "
          "are larger and add reset-tree load; data qualified by a reset valid "
          "bit does not need a reset"],
         ["Never mix reset and non-reset flops in one `always_ff`",
          "The reset becomes a load-enable on the non-reset flops (see below)"],
         ["No `initial` blocks or declaration initializers in RTL",
          "FPGA tools honor them, ASIC synthesis ignores them: the simulation "
          "then lies about power-up state"],
         ["Every CDC goes through an approved synchronizer cell or module",
          "CDC tools recognize the cell; hand-written double flops get "
          "optimized, retimed or mis-constrained"],
         ["No `#` delays in RTL", "Ignored by synthesis; they hide races that "
          "reappear in gate-level simulation"]],
        widths=[45, 55])
    code(_seg(STYLE_SNIP, "module mix_bad", "`default_nettype wire"),
         "The mixed-reset bug and its fix (both compiled with iverilog -Wall).")
    box("warn", "PITFALL - the reset that became an enable",
        "In `mix_bad`, `data_q` has no reset branch, so while `rst_n` is low the "
        "block must **hold** `data_q`. Synthesis implements that with a feedback "
        "mux controlled by `rst_n` - an extra gate per bit, a timing path from the "
        "reset tree into the datapath, and a flop that is neither reset nor "
        "free-running for DFT. Lint tools flag it (for example as a "
        "'reset used as data' or 'partial reset' rule); good reviewers flag it "
        "faster. The fix is always two blocks.")

    h2("A module written to the guideline")
    p("The small timeout counter below applies every rule so far: a header "
      "block, typed parameter, direction prefixes, documented ports, "
      "`_d`/`_q` two-process style with defaults at the top of `always_comb`, "
      "an async-assert reset used only on control state, and a registered "
      "output.")
    code(_lines(TMR_SV), "tmr_timeout.sv - a reference module in house style.")
    code(_lines(TB_TMR), "A minimal directed testbench.")
    out(["65 ns: expired, cnt=5",
         "100 ns: still expired=1, cnt=5 (saturates)",
         "110 ns: after clr expired=0 cnt=0",
         "155 ns: expired, cnt=5",
         "tb_tmr.sv:16: $finish called at 170000 (1ps)"],
        "The counter saturates at the limit, `i_clr` wins over `i_en`, and "
        "counting resumes after the clear.")
    box("expert", "Why the defaults sit at the top of always_comb",
        "Assigning `cnt_d = cnt_q` before any `if` makes it impossible to leave a "
        "path unassigned, so no latch can be inferred no matter how the "
        "conditions are later edited. It also documents the flop's default "
        "behavior - hold - in one line. `always_comb` then adds a tool check: "
        "lint and synthesis warn if a latch is still inferred.")

    h2("Rules that prevent silicon bugs")
    tbl(["Rule", "What goes wrong without it"],
        [["`always_ff` with `<=`; `always_comb` with `=`", "Simulation races "
          "and simulation/synthesis mismatch (Ch. 4)"],
         ["Default every output of `always_comb`", "Inferred latches; timing "
          "loops; X in gate-level simulation"],
         ["`case` with `default`; no `casex`; `casez` only with `?` wildcards",
          "`casex` treats X from the input as don't-care and hides real X bugs"],
         ["`unique`/`priority` only when the condition is truly guaranteed",
          "They grant synthesis permission to optimize; if the assumption is "
          "false, silicon differs from RTL"],
         ["Match widths explicitly; size every literal", "Silent truncation or "
          "zero-extension; `a + b` losing its carry"],
         ["Cast signed arithmetic deliberately (`$signed`, `33'(x)`)", "One "
          "unsigned operand makes the whole expression unsigned (Ch. 8)"],
         ["One driver per signal; one `always` block per signal", "Multiple "
          "drivers are X in simulation and a short circuit or error in synthesis"],
         ["No combinational loops, including through module boundaries",
          "Oscillation, untimeable paths; often created by valid/ready "
          "handshakes that depend on each other (Ch. 10)"],
         ["Register module outputs where practical", "Unbounded combinational "
          "paths across block boundaries make top-level timing unpredictable"],
         ["Full FSM encoding with a safe `default` transition", "An illegal "
          "state reached by an upset or a bug locks the FSM forever (Ch. 7)"]],
        widths=[42, 58])

    h2("Comments and documentation")
    bul(["**Comment the why, not the what.** `cnt_q <= cnt_q + 1  // increment` "
         "is noise; `// count to 15: 16x oversampling = one bit time` is the "
         "sentence the next engineer needs.",
         "**Every port gets a one-line comment** with its meaning, units and "
         "timing constraints (\"level\", \"1-cycle pulse\", \"must be static while "
         "enabled\").",
         "**Every module gets a header**: purpose, clocks, resets, parameters, "
         "and a pointer to the micro-architecture spec section.",
         "**Every waiver, magic number and workaround gets a ticket reference.** "
         "`// TODO` without an owner and a ticket is a bug nobody will fix.",
         "**Registers are documented from a single source** (SystemRDL or "
         "IP-XACT, Ch. 15) that generates the RTL, the C header, the UVM "
         "register model and the HTML documentation. Hand-maintained register "
         "tables drift from the RTL within weeks.",
         "**Diagrams live next to the code** (in `doc/`), under version control, "
         "in a text-diffable format where possible (WaveDrom JSON for "
         "waveforms, Markdown/AsciiDoc for specs)."])

    h2("The micro-architecture specification")
    p("The architecture spec says **what** a block does; the micro-architecture "
      "spec says **how** - the pipeline, the FSMs, the storage, the corner "
      "cases - at a level where a reviewer can find bugs **before** a line of "
      "RTL exists. Writing it is not bureaucracy: it is the cheapest "
      "verification you will ever do. A template that works:")
    tbl(["Section", "Contents"],
        [["1. Overview", "Purpose, features, non-goals, target PPA, standards "
          "followed (AMBA version, UART framing)"],
         ["2. Interfaces", "Every port: direction, width, protocol, timing; "
          "reference to the bus spec"],
         ["3. Clocks and resets", "Domains, frequencies, crossings and how each "
          "is synchronized; reset sequence and values"],
         ["4. Block diagram", "Sub-blocks, the datapath, every flop stage on "
          "the critical path"],
         ["5. Datapath", "Widths, number formats, rounding and saturation, "
          "pipeline timing diagram"],
         ["6. Control", "FSM state diagrams, arbitration, flow control and "
          "back-pressure behavior"],
         ["7. Registers", "Generated register map; side effects (W1C, "
          "read-to-pop); reset values"],
         ["8. Performance", "Latency, throughput, buffering calculations "
          "(e.g. FIFO depth vs. interrupt latency)"],
         ["9. Errors and corner cases", "Overflow, underflow, illegal "
          "configuration, what software sees"],
         ["10. Power, DFT, safety", "Clock-gating points, power domains, scan "
          "exceptions, parity/ECC"],
         ["11. Verification hooks", "Assertions to write, coverage points, "
          "features that need formal"],
         ["12. Open issues", "Decisions still to make, with owners"]],
        widths=[24, 76])

    h2("Design reviews")
    p("A project runs several kinds of review, each with a different question. "
      "The **spec review** asks 'is this the right block?'; the "
      "**micro-architecture review** asks 'will this design meet its "
      "requirements?'; the **RTL code review** asks 'does this code implement "
      "the micro-architecture cleanly and safely?'; the **verification plan "
      "review** asks 'how will we know?'; the **sign-off review** asks 'is "
      "every report clean or waived with a reason?'. Mixing these questions in "
      "one meeting is the most common reason reviews are long and useless.")
    checklist("RTL design-review checklist", [
        "Micro-architecture spec exists, is current, and matches the RTL block diagram",
        "Every port documented; directions, widths and active levels match the spec",
        "Naming convention followed: `_q`, `_d`, `_n`, domain names on clocks and resets",
        "Every clock-domain crossing uses an approved synchronizer; CDC report clean",
        "Reset strategy correct: async assert / sync release; no mixed reset blocks",
        "No latches, no combinational loops, no multiple drivers (lint clean)",
        "All `case` statements have `default`; FSMs recover from illegal states",
        "Arithmetic widths, signedness, overflow and saturation reviewed",
        "Valid/ready: no combinational ready-to-valid dependency; data stable while "
        "valid and not ready",
        "Register map generated from the single source; side effects (W1C, RC) "
        "match the spec",
        "Every parameter value range checked at elaboration",
        "Critical paths estimated (logic levels per stage) against the target clock",
        "Clock-gating enables and power-domain boundaries identified (Ch. 19)",
        "No DFT blockers: no gated clocks outside ICGs, resets controllable in test mode",
        "Assertions for key protocol and FSM properties exist and are bound",
        "Every lint/CDC waiver has a reason, an owner and a ticket",
        "Code coverage and functional coverage targets agreed with verification"])
    box("tip", "How to run a code review that finds bugs",
        "Keep each review under about 400 lines of change and 60-90 minutes; "
        "defect-finding rate drops sharply beyond that. Have the author walk "
        "through the **data path first**, then the control. Reviewers should "
        "read with the spec open, and ask 'what happens when...' about every "
        "input: back-pressure during the last beat, reset in the middle of a "
        "frame, a write and an event on the same W1C bit in the same cycle.")

    h2("Common review findings")
    tbl(["Finding", "Symptom", "Fix"],
        [["Incomplete `always_comb` assignment", "Latch inferred; lint warning",
          "Default assignments at the top of the block"],
         ["Reset and non-reset flops in one block", "Reset used as data enable",
          "Split into two `always_ff` blocks"],
         ["Combinational `ready` depends on `valid`", "Loop across modules at "
          "integration", "Register ready or insert a skid buffer (Ch. 10)"],
         ["Unsynchronized async input", "Metastability; random field failures",
          "2-flop synchronizer; CDC tool sign-off"],
         ["Multi-bit bus crossing through 2-flop syncs", "Bits arrive in different "
          "cycles: corrupted values", "Gray code, handshake or async FIFO (Ch. 11)"],
         ["W1C bit loses an event that arrives with the clear", "Missed "
          "interrupts under load", "Make set win over clear: `(q & ~w1c) | evt`"],
         ["Counter or pointer width off by one", "Wrap at wrong value; FIFO "
          "full/empty confusion", "Extra MSB pointer scheme; assertions"],
         ["Signed/unsigned mix", "Wrong results only for negative values",
          "Explicit casts; directed negative tests"],
         ["Output driven combinationally from inputs", "Top-level timing "
          "failure", "Register outputs or budget the path"],
         ["Magic numbers", "Next change breaks one of three copies",
          "`localparam` or package constant"],
         ["Clock gating written as `clk & en`", "Glitches, STA and scan break",
          "Library ICG through a wrapper module"]],
        widths=[30, 33, 37])

    h2("A git workflow for RTL")
    p("RTL is software in its workflow even if it is hardware in its result. "
      "The practices that matter most are small, reviewed changes; a CI "
      "pipeline that runs lint and a smoke regression on every push; and "
      "**tags on milestones** so that any netlist can be traced back to the "
      "exact RTL it came from.")
    code([
        "# feature branch per change, named after the ticket",
        "git switch -c uart/1234-rx-overrun-irq",
        "# ... edit RTL, testbench and the register description together ...",
        "make lint sim TEST=uart_overrun          # local gate before pushing",
        "git commit -m \"uart: add RX overrun interrupt (W1C, set wins) [#1234]\"",
        "git push -u origin uart/1234-rx-overrun-irq",
        "# CI: lint + CDC + smoke regression; reviewer approves; squash-merge",
        "",
        "# milestone: freeze the RTL that goes to synthesis",
        "git tag -a uart_rtl_v1.0_freeze -m \"RTL freeze for block synthesis\"",
    ], "A typical change flow. The tag is what synthesis, DFT and STA reports "
       "reference.")
    bul(["**Commit the source, generate the rest**: register RTL, C headers and "
         "filelists generated in CI from the single source - unless your flow "
         "requires the generated RTL to be frozen and reviewed, in which case "
         "commit it with the generator version recorded.",
         "**Never commit simulator databases, waveforms or netlists**; keep them "
         "in `.gitignore` and store sign-off artifacts in a release area.",
         "**Change RTL, testbench and spec in the same pull request** - a spec "
         "that lags the RTL by one commit is already wrong.",
         "**Write commit messages for the bug hunter** two years from now: which "
         "block, what behavior changed, which ticket."])

    h2("Regression discipline")
    tbl(["Tier", "When", "Contents", "Budget"],
        [["Smoke", "Every push (CI)", "Lint, compile, 10-50 directed tests",
          "< 15 min"],
         ["Nightly", "Every night on main", "Full directed + constrained-random "
          "suite, many seeds, coverage merge", "Hours"],
         ["Weekly", "Weekend", "Long random runs, formal proofs, CDC/RDC, "
          "gate-level smoke (Ch. 26)", "Days"],
         ["Milestone", "Before each freeze", "Everything above, plus "
          "equivalence (Ch. 25) and power-aware simulation", "As needed"]],
        widths=[14, 20, 48, 18])
    bul(["**Record the seed** of every random test and make any failure "
         "reproducible from one command line.",
         "**A red regression is the top priority** of the team that broke it. "
         "Two days of ignored failures and nobody knows which commit broke what.",
         "**Never accept 'flaky'.** A test that fails 1 time in 50 is a race in "
         "the testbench or a real corner case in the design - both must be fixed.",
         "**Track trends, not snapshots**: pass rate, coverage and bug arrival "
         "rate over time are what tell management the design is converging "
         "toward tapeout."])

    h2("Summary")
    bul(["Coding guidelines are compressed experience: each rule prevents a "
         "known class of bug or tool problem.",
         "Names carry hardware meaning: `_q`/`_d` for flops and next state, "
         "`_n` for active low, direction prefixes, domain-tagged clocks and resets.",
         "One module per file, typed parameters with elaboration checks, "
         "`default_nettype none`, and filelists as the single source of truth.",
         "Reset and clock rules exist for STA, CDC and DFT; never mix reset and "
         "non-reset flops in one block.",
         "A micro-architecture spec and focused reviews find bugs when they are "
         "cheapest; checklists keep reviews complete.",
         "Small reviewed changes, milestone tags and tiered regressions keep a "
         "design converging for its whole life."])

    h2("Exercises")
    bul(["Rewrite `tmr_timeout` in single-process style (one `always_ff`). Which "
         "names change, and what does a reviewer lose?",
         "Take any 100-line module you have written and review it against the "
         "checklist in 27.10. List every finding with a proposed fix.",
         "Draw the gate-level circuit synthesis produces for `mix_bad` for one "
         "bit of `data_q`, and explain why it hurts scan insertion.",
         "Write a micro-architecture spec (sections 1-9 of the template) for the "
         "synchronous FIFO of Chapter 9, including the full/empty timing diagram.",
         "Design a regression plan for a 6-person team working on an AXI "
         "interconnect: which tests in which tier, and how do you keep the "
         "smoke tier under 15 minutes?"], ordered=True)


# ------------------------------------------------------------------ Ch 28 ---
def _ch28():
    chapter("Project: An APB UART Subsystem, Designed and Verified")
    p("A UART is the 'hello world' of SoC peripherals, and for good reason: it "
      "is small enough to write in an afternoon, yet it contains nearly every "
      "idea of Parts II and III - an FSM, a datapath, FIFOs, an asynchronous "
      "input that must be synchronized, a clock-enable baud generator, a bus "
      "slave with side-effect registers, and an interrupt with W1C semantics. "
      "Getting all of them right **together** is what distinguishes a "
      "peripheral from a collection of exercises.")
    p("This chapter builds the complete subsystem in about 210 lines of "
      "SystemVerilog, verifies it with a self-checking testbench that sends "
      "53 bytes through the serial line and reads them back over APB, and then "
      "lists what a production UART adds. Every listing is the exact code that "
      "was simulated.")

    h2("Specification")
    bul(["**Bus**: AMBA APB slave (Ch. 13), 32-bit data, zero wait states, "
         "`PSLVERR` tied low, 5-bit word-aligned address space.",
         "**Line format**: 8N1 - one start bit (0), 8 data bits LSB first, one "
         "stop bit (1); idle line high.",
         "**Baud rate**: programmable divider producing a 16x oversampling "
         "enable; `baud = f_pclk / (16 x (BAUD_DIV + 1))`.",
         "**Buffering**: 8-entry TX FIFO and 8-entry RX FIFO.",
         "**Receiver**: 2-flop synchronizer, false-start rejection, mid-bit "
         "sampling, framing-error detection, overrun detection.",
         "**Interrupt**: one level-sensitive `irq` = OR of enabled sticky "
         "events; events are cleared by writing 1 (W1C).",
         "**Test feature**: internal loopback (TX line fed to RX inside the IP)."])
    tbl(["Offset", "Name", "Access", "Fields"],
        [["0x00", "DATA", "W: push TX FIFO / R: pop RX FIFO",
          "[7:0] byte. A read has a **side effect**: it pops the RX FIFO"],
         ["0x04", "STATUS", "RO", "[0] RX_AVAIL  [1] RX_FULL  [2] TX_EMPTY  "
          "[3] TX_FULL  [4] TX_BUSY"],
         ["0x08", "CTRL", "RW, reset 0x3", "[0] TX_EN  [1] RX_EN  [2] LOOPBACK"],
         ["0x0C", "BAUD_DIV", "RW, reset 26", "[15:0] divider (26 = 115200 baud "
          "at 50 MHz)"],
         ["0x10", "INT_EN", "RW, reset 0", "[3:0] enable per INT_STATUS bit"],
         ["0x14", "INT_STATUS", "RW1C, reset 0", "[0] RX_DONE  [1] TX_DONE  "
          "[2] RX_OVERRUN  [3] FRAME_ERR (sticky)"]],
        widths=[9, 14, 26, 51], caption="UART register map. In a real project "
        "this table is generated from a SystemRDL description (Ch. 15).")

    h2("Block diagram")
    diagram([
        "           +------------------------------ uart_apb ------------------------------+",
        " APB       |                                                                      |",
        " PSEL ---->| +------------+  push  +---------+ tx_start +---------+               |",
        " PENABLE ->| | APB decode |------->| TX FIFO |--------->| uart_tx |---+-----------+--> txd",
        " PWRITE -->| |   + CSRs   | DATA wr|  8 x 8  |   data   |   FSM   |   |           |",
        " PADDR --->| |            |        +---------+          +---------+   | loopback  |",
        " PWDATA -->| | CTRL  BAUD |                                ^ tick16  |            |",
        " PRDATA <--| | IEN  ISTAT |  pop   +---------+  push    +---------+ +-v-+         |",
        " PREADY <--| |   (W1C)    |<-------| RX FIFO |<---------| uart_rx |<|mux|<--------+--< rxd",
        "           | +------------+ DATA rd|  8 x 8  | rx_valid | 2FF sync| +---+ CTRL[2] |",
        "           |    |      ^           +---------+          +---------+               |",
        "           |    |      | events                             ^ tick16              |",
        " irq <-----+-- OR(IST & IEN)                  +--------------+----------+         |",
        "           |                                  | baud gen: /(BAUD_DIV+1) |         |",
        "           |                                  +-------------------------+         |",
        "           +----------------------------------------------------------------------+",
    ], "The subsystem. Everything runs on `pclk`; the only asynchronous signal "
       "is `rxd`, and it is synchronized inside `uart_rx`.")
    box("key", "One clock, one asynchronous input",
        "The baud generator produces a **clock enable** (`tick16`), not a "
        "clock. All flops run on `pclk`, so there is exactly one clock domain, "
        "STA is trivial, and the only CDC in the design is the `rxd` pin - "
        "handled by one 2-flop synchronizer. Generating a divided clock would "
        "create a second domain, a crossing on every FIFO access, and a "
        "clock-tree to build (Ch. 11, 17).")

    h2("Baud generation and the 16x oversampling budget")
    eq(["f_tick16 = f_pclk / (BAUD_DIV + 1)        baud = f_tick16 / 16",
        "BAUD_DIV = round( f_pclk / (16 x baud) ) - 1",
        "50 MHz, 115200 baud:  50e6 / (16 x 115200) = 27.13  ->  BAUD_DIV = 26",
        "actual = 50e6 / (16 x 27) = 115741 baud   error = +0.47 %"],
        "Integer division sets the baud error; production UARTs add a "
        "fractional divider to reduce it.")
    p("Why 16x? The receiver cannot see the transmitter's clock, so it must "
      "find the **middle** of each bit by counting from the falling edge of the "
      "start bit. With 16 samples per bit, the edge is located to within 1/16 "
      "of a bit (plus two `pclk` cycles of synchronizer latency), and every later "
      "sample is taken 16 ticks after the previous one. The last sample - the "
      "stop bit - is taken about 9.5 bit-times after the edge. If the two ends' "
      "clocks differ by a fraction e, that sample drifts by 9.5e bit-times; it "
      "must stay within the bit, so roughly 9.5e < 0.5 - 1/16, i.e. **e below "
      "about 4.6% total** between the two ends. That is the real reason a +0.47% "
      "divider error is harmless and why cheap RC oscillators are not.")

    h2("The FIFOs")
    code(_lines(UART_FIFO), "uart_fifo.sv - first-word-fall-through synchronous "
         "FIFO (the Ch. 9 design, specialized).")
    bul(["**Extra pointer MSB**: equal pointers mean empty; pointers equal "
         "except the MSB mean full. No separate counter, no ambiguity at "
         "8 entries.",
         "**First-word-fall-through**: `rdata` always shows the head entry, so "
         "the TX FSM can load it and the APB read can return it in the same "
         "cycle as the pop.",
         "**Storage has no reset**, pointers do - the reset rule from Ch. 27. "
         "The entries are meaningless until the pointers say otherwise.",
         "Push when full and pop when empty are **ignored** rather than "
         "corrupting state; the RX overrun interrupt reports the lost byte."])

    h2("The transmitter")
    diagram([
        "          start (FIFO not empty & TX_EN)",
        "   +------+ -------------------------> +-------+  16 ticks  +------+  8 bits x   +------+",
        "   | IDLE |   txd<=0, load shifter     | START | ---------> | DATA | -16 ticks-> | STOP |",
        "   +------+ <----------------------------------------------------------------- +------+",
        "      txd=1                        16 ticks with txd=1                    txd=1",
        "",
        "   txd: ~~~~~~|_start_|_d0_|_d1_|_d2_|_d3_|_d4_|_d5_|_d6_|_d7_|~stop~|~~~~~~ idle",
        "               16 tk   16   16   ...                           16",
    ], "TX FSM and the resulting 8N1 frame.")
    code(_lines(UART_TX), "uart_tx.sv")
    p("The oversample counter `os_q` counts `tick16` enables; 16 of them make "
      "one bit time. `txd` is a **flop**, not a decode of the state: an output "
      "pad driven from combinational logic glitches whenever the state "
      "changes, and a glitch on a serial line is a false start bit at the "
      "other end.")
    box("note", "A deliberate 1/16-bit imprecision",
        "`txd` falls as soon as `start` arrives, but the START state counts "
        "`tick16` enables, the first of which arrives 1 to BAUD_DIV+1 cycles "
        "later. The start bit is therefore between 15 and 16 ticks long - at "
        "most 1/16 of a bit short, well inside the receiver's budget. Aligning "
        "`start` to a tick would remove it at the cost of up to one tick of "
        "added latency; both choices are defensible, and the spec should state "
        "which one was made.")

    h2("The receiver: synchronize, find the edge, sample the middle")
    diagram([
        " rxd (sync)  ~~~~~~~\\_________________________/~~~~~~~~~~~~~~~~~~~~~~~~\\_____",
        "                    |<------ start bit ------->|<-------- d0 --------->|",
        " tick16 count:      0 1 2 3 4 5 6 7            ... 15 (after 16 more)",
        "                                  ^                              ^",
        "                     sample #1: still 0?         sample d0 at its middle,",
        "                     yes -> real start           then every 16 ticks",
        "                     no  -> glitch, back to IDLE",
    ], "Mid-bit sampling. The first check at tick 7-8 rejects short glitches; "
       "every later sample lands near the centre of its bit.")
    code(_lines(UART_RX), "uart_rx.sv")
    bul(["**2-flop synchronizer** (`sync_q`, reset to 1 = idle): `rxd` is "
         "asynchronous to `pclk`, and the first flop may go metastable. The "
         "second flop gives it a full cycle to resolve (Ch. 11). Every other "
         "flop sees only the clean `rxd`. The flops reset to 1 so reset release "
         "is not mistaken for a start bit.",
         "**False-start rejection**: a start bit must still be low at its "
         "middle; noise shorter than half a bit returns the FSM to IDLE.",
         "**Framing error**: a 0 where the stop bit should be means the "
         "receiver lost bit alignment, the baud rates differ, or the far end sent "
         "a BREAK. The byte is not pushed; `frame_err` pulses instead.",
         "Returning to IDLE in the **middle** of the stop bit is intentional: "
         "the receiver is ready half a bit early, which absorbs a transmitter "
         "that runs slightly fast."])
    box("warn", "PITFALL - synchronizing inside the FSM",
        "A common bug is to use the raw pin in the IDLE test (`if (!rxd_async)`) "
        "and the synchronized one elsewhere. The IDLE branch then samples an "
        "asynchronous signal into several flops (`st_q`, `os_q`) at once: "
        "if it changes near the clock edge, some flops see 0 and some see 1, and "
        "the FSM lands in an illegal combination. **Exactly one flop** may "
        "sample an asynchronous signal. CDC tools report this as a "
        "'divergence' or 'unsynchronized fan-out'.")

    h2("The APB interface, registers and interrupt")
    code(_seg(UART_APB, "// APB UART", "// Baud generator"),
         "uart_apb.sv (1/4): ports, declarations and APB decode.")
    p("APB is simple enough that the decode is two AND gates. A transfer spends "
      "one cycle in SETUP (`PSEL=1, PENABLE=0`) and one in ACCESS "
      "(`PSEL=1, PENABLE=1`); with `PREADY` tied high, every access completes "
      "in its first ACCESS cycle, so writes and read side effects happen "
      "exactly once, on `psel & penable`.")
    code(_seg(UART_APB, "// Baud generator", "// TX path"),
         "uart_apb.sv (2/4): the baud generator is a counter that emits an enable.")
    p("The comparison is `>=` rather than `==` on purpose: if software lowers "
      "BAUD_DIV while the counter is above the new value, `==` would let the "
      "counter run to 65535 and wrap - a 1-ms hiccup at 50 MHz that a "
      "`==` design only shows when someone reprograms the baud rate on the fly.")
    code(_seg(UART_APB, "// TX path", "// Interrupts"),
         "uart_apb.sv (3/4): TX and RX datapaths, and the loopback mux.")
    code(_seg(UART_APB, "// Interrupts"),
         "uart_apb.sv (4/4): W1C interrupt status, control registers and read mux.")
    bul(["**Set wins over clear**: `ist_q <= (ist_q & ~w1c) | evt`. If a new "
         "event arrives in the same cycle software clears the bit, the event "
         "survives. The opposite priority loses interrupts under load - one of "
         "the review findings of Chapter 27.",
         "**Level interrupt**: `irq` stays high until software clears the cause; "
         "a level is robust to an interrupt controller that is busy, whereas a "
         "pulse can be missed (Ch. 15).",
         "**TX_DONE** fires on the falling edge of `tx_busy` when the FIFO is "
         "empty - 'everything you gave me has left the pin', which is what a "
         "driver needs before it disables the transmitter or powers down.",
         "**Read side effect**: reading DATA pops the RX FIFO. Debuggers that "
         "read all registers for display will steal bytes - which is why many "
         "designs provide a side-effect-free debug alias, and why the register "
         "description must mark such fields (SystemRDL `rclr`/`rset`, or a "
         "user property for read-to-pop)."])

    h2("A self-checking testbench")
    p("The testbench behaves as software would: it programs the UART through "
      "APB, writes bytes to DATA, polls STATUS and reads bytes back. The serial "
      "line is looped back outside the IP (and in test 3, inside it), so every "
      "byte crosses the whole TX path, the line, the synchronizer and the RX "
      "path. A queue holds the bytes in flight - a one-line reference model "
      "(Ch. 22).")
    code(_seg(TB_UART, None, "  task automatic apb_write"),
         "tb_uart.sv (1/3): signals, the external loopback wire, DUT.")
    code(_seg(TB_UART, "  task automatic apb_write", "  initial begin"),
         "tb_uart.sv (2/3): APB bus-functional tasks and the checking tasks.")
    box("warn", "PITFALL - two threads on one bus",
        "A first version of this testbench forked `send` and `drain` as two "
        "parallel threads. Both called `apb_read`, both drove `psel`, `paddr` "
        "and `penable` in the same cycles, and the result was two corrupted "
        "bytes and a hung test. A bus-functional model is a **single master**: "
        "either serialize access (one thread, as below), or guard it with a "
        "semaphore - which is what a UVM sequencer does for you (Ch. 24).")
    code(_seg(TB_UART, "  initial begin"),
         "tb_uart.sv (3/3): four tests - interrupt and W1C, a 40-byte random "
         "stream, internal loopback, and overrun.")
    code(["iverilog -g2012 -Wall -o sim tb_uart.sv uart_fifo.sv uart_tx.sv \\",
          "         uart_rx.sv uart_apb.sv && vvp -n sim"])
    out(["[6275 ns] irq after first byte, INT_STATUS read next",
         "  INT_STATUS = 0001",
         "  after W1C irq = 0",
         "[262335 ns] random stream done, 41 bytes checked so far",
         "[353185 ns] after 10 unread bytes: STATUS.RX_FULL=1 OVERRUN=1",
         "RESULT: 53 bytes checked, 0 errors -> PASS",
         "tb_uart.sv:90: $finish called at 353665000 (1ps)"],
        "Real Icarus Verilog 12 output. With BAUD_DIV=3 a bit lasts 64 cycles "
        "(640 ns), so one frame takes 6.4 us - the first interrupt at 6275 ns "
        "is one frame after the write, as expected.")
    p("Reading the result critically: the first byte raised `irq` and the W1C "
      "write dropped it; 40 random bytes streamed through both FIFOs while the "
      "testbench interleaved writes and reads; internal loopback worked with "
      "the external line held idle; and ten unread bytes filled the 8-entry RX "
      "FIFO and set RX_OVERRUN, after which the first eight bytes were still "
      "intact. What it does **not** prove: framing-error detection, tolerance "
      "to baud mismatch, glitch rejection, or reset in the middle of a frame. "
      "Those are the exercises - and exactly what a verification plan review "
      "(Ch. 27) would demand before sign-off.")

    h2("What it costs")
    tbl(["Block", "Flops (approx.)", "Notes"],
        [["TX FIFO + RX FIFO", "2 x (64 + 8) = 144", "Storage dominates; at "
          "16+ entries a latch array or small SRAM macro wins on area"],
         ["uart_tx", "~18", "State, oversample and bit counters, shifter, `txd`"],
         ["uart_rx", "~29", "Synchronizer, state, counters, shifter, output byte"],
         ["Registers, baud counter, IRQ", "~50", "BAUD_DIV and its counter "
          "are 32 of them"],
         ["**Total**", "**~240 flops**", "A few thousand gate equivalents - "
          "negligible next to a CPU, which is why SoCs carry several UARTs"]],
        widths=[26, 22, 52], caption="Area estimate. Critical path: the 16-bit "
        "compare plus increment in the baud generator - trivially fast.")

    h2("From project to production")
    tbl(["Feature", "Why production UARTs have it"],
        [["Parity (even/odd/stick), 5-8 data bits, 1/1.5/2 stop bits",
          "Compatibility with legacy equipment and the 16550 register model "
          "that operating-system drivers expect"],
         ["Break detection and generation", "A line held low for a whole frame "
          "is a BREAK, used as an attention signal (e.g. LIN, debug consoles); "
          "must be distinguished from a framing error"],
         ["Majority-vote sampling (3 samples around mid-bit)",
          "Rejects single-sample noise on long cables"],
         ["RX timeout interrupt", "Tells software that fewer than a threshold "
          "of bytes are waiting and the line has gone quiet"],
         ["FIFO threshold interrupts", "Interrupt at 1/4, 1/2, 3/4 full: fewer "
          "interrupts per byte at high baud rates"],
         ["Fractional baud divider", "Reduces baud error at high rates and odd "
          "clock frequencies"],
         ["RTS/CTS hardware flow control", "Prevents overrun when the far end "
          "cannot keep up"],
         ["DMA request/acknowledge handshake", "Lets a DMA engine move bytes "
          "without CPU interrupts per byte (Ch. 16)"],
         ["Separate UART core clock with CDC", "Baud accuracy independent of "
          "bus-clock scaling (DVFS); requires async FIFOs (Ch. 11)"],
         ["`PSLVERR` on bad offsets, `PPROT` checks, `PSTRB`", "Security and "
          "robust software error handling"],
         ["Clock gating and a wake-on-start-bit feature", "Low power while idle "
          "(Ch. 19)"],
         ["UVM environment: APB agent + UART agent + RAL + scoreboard, SVA, "
          "coverage, formal on the FIFO", "The verification that turns a demo "
          "into IP someone else will tape out (Ch. 23-25)"]],
        widths=[40, 60])

    h2("Summary")
    bul(["A UART exercises FSMs, datapaths, FIFOs, CDC, bus slaves and "
         "interrupts at once; building one end to end is the best first project.",
         "Generate a 16x clock **enable**, not a clock: one domain, easy STA, "
         "one synchronizer.",
         "16x oversampling finds the middle of each bit and tolerates about "
         "4-5% total clock mismatch.",
         "Synchronize the asynchronous input into exactly one flop chain "
         "before any logic uses it.",
         "W1C interrupt status with set-wins-over-clear, a level `irq`, and "
         "documented read side effects are what make a peripheral usable by "
         "software.",
         "A self-checking testbench that acts like software, with a queue as "
         "reference model, verified 53 bytes across four scenarios."])

    h2("Exercises")
    bul(["Add a test that drives `rxd` directly from the testbench with a frame "
         "whose stop bit is 0, and check that FRAME_ERR is set and no byte is "
         "pushed.",
         "Drive frames from the testbench at a baud rate 3% fast and 3% slow; "
         "then find experimentally the mismatch at which bytes start failing "
         "and compare it with the 4.6% estimate.",
         "Add even parity with a CTRL enable bit and a PARITY_ERR interrupt. "
         "Update the register table, RTL and testbench together.",
         "Replace mid-bit sampling with a 3-sample majority vote (ticks 7, 8 "
         "and 9). How much logic does it cost?",
         "Write SVA properties (Ch. 23) for: `txd` is high whenever the TX FSM "
         "is IDLE; the RX FIFO never pushes when full; `irq` implies some "
         "enabled status bit is set.",
         "Sketch the UVM environment for this UART: agents, sequences, "
         "register model and scoreboard (Ch. 24)."], ordered=True)


# ------------------------------------------------------------------ Ch 29 ---
def _ch29():
    chapter("Project: An AXI-Stream MAC Accelerator for On-Device ML")
    p("This book lives in a repository about **on-device training, quantization "
      "and pruning** - the techniques that shrink neural networks until they "
      "fit on phones, microcontrollers and sensors. Those techniques only pay "
      "off if the hardware exploits them: an int8 model on a float32 datapath "
      "saves memory but not energy, and a 75%-pruned model on a dense engine "
      "saves nothing at all. This chapter closes the loop by building the "
      "hardware side: a pipelined int8 dot-product engine with requantization "
      "and zero-skipping for pruned weights, fed and drained by AXI4-Stream, "
      "configured through a register interface, and verified bit-exactly "
      "against a golden model.")

    h2("Why int8, and what the hardware must compute")
    p("Integer-only inference (the scheme popularized by Jacob et al., CVPR "
      "2018, and used by TensorFlow Lite and most NPUs) represents each real "
      "value r by an 8-bit integer q with a scale S and a zero point Z. With "
      "symmetric weights (Z_{w} = 0), a layer output becomes an integer dot "
      "product followed by a single rescale:")
    eq(["r = S x (q - Z)                                    (affine quantization)",
        "",
        "y_q = Z_y + M x ( bias_q + SUM_k a_q[k] x w_q[k] )    M = S_a x S_w / S_y",
        "",
        "M is a real number in (0, 1): hardware stores M ~= mult x 2^-shift",
        "int8 x int8 -> int16 products, summed in an int32 accumulator"],
        "The activation zero point Z_a is folded into the bias offline "
        "(its contribution is Z_a x SUM w, a per-channel constant), so the engine "
        "sees plain signed products.")
    tbl(["Operation (45 nm, Horowitz ISSCC 2014)", "Energy", "Relative to 8-bit add"],
        [["8-bit integer add", "0.03 pJ", "1x"],
         ["32-bit integer add", "0.1 pJ", "3x"],
         ["8-bit integer multiply", "0.2 pJ", "7x"],
         ["32-bit float multiply", "3.7 pJ", "~120x"],
         ["32-bit read from on-chip SRAM (cache)", "5 pJ", "~170x"],
         ["32-bit read from DRAM", "640 pJ", "~21000x"]],
        widths=[50, 20, 30], caption="Widely quoted energy figures. An int8 multiply "
        "is ~18x cheaper than a float32 multiply, and **every** arithmetic "
        "operation is cheap next to moving data.")
    box("intuit", "The two lessons of the energy table",
        "First, quantization pays twice: int8 arithmetic is an order of "
        "magnitude cheaper, and int8 data is 4x smaller to move. Second, data "
        "movement dominates - which is why accelerator design is mostly the "
        "art of **reusing** each operand fetched from memory many times "
        "(29.8), and why skipping a pruned weight saves more if you never "
        "fetch it at all.")

    h2("Specification")
    tbl(["Interface", "Signals", "Protocol"],
        [["Input stream", "`s_tvalid`, `s_tready`, `s_tdata[16L-1:0]`, `s_tlast`",
          "AXI4-Stream. One beat = L activations (low half) and L weights "
          "(high half), int8 each. `s_tlast` marks the last beat of a vector"],
         ["Output stream", "`m_tvalid`, `m_tready`, `m_tdata[7:0]`",
          "AXI4-Stream. One int8 result per input vector"],
         ["CSR port", "`csr_we`, `csr_addr[4:0]`, `csr_wdata`, `csr_rdata`",
          "Single-cycle write, combinational read; an APB or AXI-Lite bridge "
          "(Ch. 13) adapts it to the SoC bus"]],
        widths=[16, 40, 44])
    tbl(["Offset", "Name", "Access", "Description"],
        [["0x00", "CTRL", "RW, reset 1", "[0] ZSKIP_EN: skip lanes whose weight is 0"],
         ["0x04", "MULT", "RW, reset 1", "[15:0] requant multiplier (unsigned)"],
         ["0x08", "SHIFT", "RW, reset 0", "[4:0] requant right shift (rounding)"],
         ["0x0C", "ZP", "RW, reset 0", "[7:0] signed output zero point"],
         ["0x10", "BIAS", "RW, reset 0", "[31:0] signed bias added to the accumulator"],
         ["0x14", "SKIP_CNT", "RO, write clears", "Number of skipped MACs"],
         ["0x18", "MAC_CNT", "RO, write clears", "Number of MAC slots processed "
          "(L per accepted beat)"]],
        widths=[9, 13, 18, 60], caption="Accelerator CSRs. Configuration "
        "registers must only change while the engine is idle.")
    eq(["out = sat8( ((acc + BIAS) x MULT + 2^(SHIFT-1)) >>> SHIFT  +  ZP )",
        "sat8(v) = min(127, max(-128, v))    (no rounding term when SHIFT = 0)"],
       "The requantization the RTL and the golden model both implement "
       "(round half toward +infinity).")

    h2("Micro-architecture")
    diagram([
        " s_tdata --+-> nz = (w != 0) | !ZSKIP ------+",
        "           |                                v",
        "           |   S1: operand regs      S2: multiply + sum     S3: requant    S4: round,",
        "           |   (load only if nz)     + int32 accumulate      multiply       shift, sat",
        "           |  +-------------+      +------------------+   +----------+   +-----------+",
        "           +->| a1_q, w1_q  |----->| SUM nz?a*w : 0   |-->| (acc2 +  |-->| +2^(s-1)  |",
        "              | x L lanes   |      |  + acc_q         |   |  BIAS) x |   | >>> SHIFT |--> m_t*",
        "              | nz1_q, v1_q |      | on last: acc2_q, |   |  MULT    |   | + ZP, sat |",
        "              +-------------+      | acc_q <= 0       |   | prod3_q  |   | m_tdata   |",
        "                                   +------------------+   +----------+   +-----------+",
        "      en = !m_tvalid | m_tready  ---> enables every stage;  s_tready = en",
    ], "Four register stages. The result is valid three clock edges after the "
       "edge that accepts the last beat; throughput is one beat (L MACs) per cycle.")
    p("The **number formats** drive the widths. An int8 x int8 product lies in "
      "[-16256, 16384] and needs 16 signed bits (the extreme +16384 = (-128) x "
      "(-128) is why an 8x8 signed multiplier's output cannot be 15 bits). A "
      "sum of 4 products needs 18 bits. The int32 accumulator can then absorb "
      "at least 2^{31} / 2^{14} = 131072 worst-case products - far longer than "
      "any realistic layer - which is why int32 is the universal accumulator "
      "width for int8 inference. The requantization multiply takes a 33-bit "
      "biased sum times a 17-bit (zero-extended) multiplier: a 50-bit product.")

    h2("The RTL, stage by stage")
    code(_seg(MAC_SV, "// int8 x int8", "// Global-stall"),
         "mac_accel.sv (1/7): ports and CSR state. `L` is the number of lanes.")
    code(_seg(MAC_SV, "// Global-stall", "// ---------------- S1"),
         "mac_accel.sv (2/7): flow control.")
    p("This is the simplest correct valid/ready pipeline: **one global enable**. "
      "Every stage advances unless the output register holds a result the "
      "consumer has not taken. It is correct by construction - no stage can "
      "overwrite data that has not moved on - but it has two costs that a "
      "reviewer should raise: `s_tready` depends combinationally on "
      "`m_tready` (a path through the whole engine, and a potential loop if the "
      "consumer's ready depends on our valid), and `en` fans out to every flop. "
      "Chapter 10's skid buffer on the output removes both; exercise 3 asks you "
      "to add it.")
    code(_seg(MAC_SV, "// ---------------- S1", "// ---------------- S2"),
         "mac_accel.sv (3/7): stage 1 - operand registers with operand isolation.")
    box("key", "What zero-skipping saves in this design - and what it does not",
        "When ZSKIP_EN is set and a lane's weight is zero, that lane's operand "
        "registers are simply **not loaded**. The multiplier inputs keep their "
        "old values, so the multiplier's gates do not toggle and consume almost "
        "no dynamic power; `nz1_q` forces the lane's contribution to zero. "
        "This is **operand isolation**, a classic low-power technique (Ch. 19). "
        "It saves energy but not **time**: the stream is dense, so a beat with "
        "four zero weights still takes a cycle. Throughput gains from sparsity "
        "require the zeros to be removed from the stream itself (29.7).")
    code(_seg(MAC_SV, "// ---------------- S2", "// ---------------- S3"),
         "mac_accel.sv (4/7): stage 2 - multipliers, adder tree and accumulator.")
    p("The `for` loop describes L multipliers and an adder chain; synthesis "
      "rebalances the chain into a tree, and for large L a designer would "
      "write an explicit tree or use a carry-save compressor followed by one "
      "carry-propagate adder (Ch. 8). On the last beat the stage writes the "
      "**final** sum to `acc2_q` and clears `acc_q` in the same cycle, so the "
      "next vector can start on the very next beat - no dead cycle between "
      "vectors.")
    code(_seg(MAC_SV, "// ---------------- S3", "// ---------------- S4"),
         "mac_accel.sv (5/7): stage 3 - the requantization multiply gets its own "
         "stage.")
    code(_seg(MAC_SV, "// ---------------- S4", "// ---------------- CSRs"),
         "mac_accel.sv (6/7): stage 4 - rounding shift, zero point, saturation.")
    box("warn", "PITFALL - signedness in the requant stage",
        "Three details here each produce wrong answers only for negative "
        "values: `mult_q` is unsigned, so it is zero-extended with "
        "`$signed({1'b0, mult_q})` before multiplying a signed value - otherwise "
        "the whole product becomes unsigned; the shift must be `>>>` on a "
        "**signed** operand to be arithmetic; and the widening casts "
        "`33'(acc2_q)` preserve the sign because the operand is declared signed. "
        "Each of these is a finding in the Chapter 27 table ('signed/unsigned "
        "mix'), and each is caught only by tests with negative accumulators.")
    code(_seg(MAC_SV, "// ---------------- CSRs"),
         "mac_accel.sv (7/7): configuration registers and performance counters.")
    p("The two counters are what make the zero-skipping measurable: software "
      "reads SKIP_CNT / MAC_CNT after a layer and learns the effective sparsity "
      "the hardware exploited - the number a pruning algorithm designer wants "
      "to see. Writing a counter clears it, and the clear deliberately wins over "
      "a simultaneous increment.")

    h2("Verification against a golden model")
    p("An arithmetic engine is verified by comparing it, bit for bit, with a "
      "**reference model** of the same arithmetic written in the testbench "
      "language (Ch. 22). Here the model is ten lines of 64-bit integer "
      "arithmetic. Stimulus is constrained-random: vectors of 1-16 beats, "
      "random int8 activations, weights zeroed with a chosen probability to "
      "mimic pruning, random idle gaps on the input and random back-pressure on "
      "the output, so the global-stall logic is exercised in every cycle "
      "combination.")
    code(_seg(TB_MAC, None, "  task automatic csr_write"),
         "tb_mac.sv (1/3): the golden requantization model.")
    code(_seg(TB_MAC, "  task automatic csr_write", "  always @(posedge clk) begin"),
         "tb_mac.sv (2/3): CSR tasks and the AXI-Stream driver. The driver holds "
         "`s_tvalid` and data stable until the handshake, as AXI4-Stream requires.")
    code(_seg(TB_MAC, "  always @(posedge clk) begin"),
         "tb_mac.sv (3/3): back-pressure, the scoreboard, and three test phases.")
    out(["dense     vec=200 out=200 err=0 sat=0 MACs=6196 skipped=0 (exp 0) 22295 ns",
         "pruned    vec=200 out=200 err=0 sat=0 MACs=6436 skipped=4887 (exp 4887) 24300 ns",
         "saturate  vec=100 out=100 err=0 sat=42 MACs=3328 skipped=1647 (exp 1647) 12080 ns",
         "RESULT: 500 vectors checked, 0 errors -> PASS",
         "tb_mac.sv:88: $finish called at 58690000 (1ps)"],
        "Real output of `iverilog -g2012 -Wall -o sim tb_mac.sv mac_accel.sv && "
        "vvp -n sim`.")
    p("The three phases check different things. **dense** (zero-skipping off, "
      "no back-pressure) checks the arithmetic; SKIP_CNT must stay 0. "
      "**pruned** (75% zero weights, 40% back-pressure, non-zero bias and zero "
      "point) checks that skipping never changes a result and that the counter "
      "is exact: 4887 of 6436 MAC slots (76%) were skipped - the hardware saw "
      "the sparsity the pruning created. **saturate** raises the scale so that "
      "42 of 100 outputs clip, exercising both saturation limits.")
    h3("Does the testbench actually catch bugs?")
    p("A testbench that has never failed has not been shown to work. A quick "
      "check is **mutation**: inject a plausible bug and confirm the scoreboard "
      "fires. Here the rounding term was deleted (`rnd = prod3_q`), i.e. "
      "truncation instead of round-half-up - exactly the mismatch that occurs "
      "when RTL and a framework's reference disagree on rounding:")
    out(["  MISMATCH got 50 exp 51",
         "  MISMATCH got -25 exp -24",
         "  MISMATCH got -42 exp -41",
         "  MISMATCH got -15 exp -14",
         "dense     vec=200 out=200 err=105 sat=0 MACs=6196 skipped=0 (exp 0) 22295 ns",
         "pruned    vec=200 out=200 err=106 sat=0 MACs=6436 skipped=4887 (exp 4887) 24300 ns",
         "saturate  vec=100 out=100 err=31 sat=42 MACs=3328 skipped=1647 (exp 1647) 12080 ns",
         "RESULT: 500 vectors checked, 242 errors -> FAIL",
         "tb_mac.sv:88: $finish called at 58690000 (1ps)"],
        "Same testbench, mutated RTL. Off-by-one errors in about half the outputs.")
    box("expert", "Bit-exactness with the ML framework",
        "The golden model in a real project is not hand-written: it is the "
        "framework's own integer kernel (e.g. TFLite's reference int8 kernels), "
        "and the RTL must match it bit for bit. TFLite rounds with "
        "`SaturatingRoundingDoublingHighMul` and a rounding divide by a power of "
        "two (round half away from zero) using a 32-bit multiplier - not "
        "this chapter's 16-bit multiplier and round-half-up. Off-by-one "
        "differences like the ones above are invisible in accuracy metrics for "
        "one layer but compound across layers, and they are the most common "
        "accelerator bring-up bug. Agree on the rounding **in the spec**.")

    h2("PPA of the engine")
    tbl(["Aspect", "Estimate / trade-off"],
        [["Area", "Dominated by the L 8x8 multipliers (a few hundred gates each), "
          "the requant 33x17 multiplier (shared by all lanes, used once per "
          "vector - a candidate for a slower multi-cycle or serial "
          "implementation) and ~250 flops at L = 4"],
         ["Timing", "Critical path candidates: 8x8 multiply + 4-input add + "
          "32-bit accumulate in S2; the 33x17 multiply in S3. Splitting S2 "
          "(products registered, then accumulate) is the first retiming step"],
         ["Throughput", "L MACs per cycle; at 500 MHz and L = 4: 2 GMAC/s. Beats "
          "per vector set the overhead: none, thanks to back-to-back accumulation"],
         ["Power", "Multipliers and the accumulator toggle every beat; operand "
          "isolation removes multiplier toggling on pruned weights; clock-gating "
          "the pipeline when `s_tvalid` is low removes the rest (Ch. 19)"],
         ["Memory bandwidth", "Each beat consumes 2L bytes, and **no operand is "
          "reused**: a dot-product engine is bandwidth-bound. This is the "
          "limitation the systolic array removes"]],
        widths=[18, 82])

    h2("Exploiting sparsity for speed, not just power")
    tbl(["Sparsity form", "How hardware exploits it", "Cost"],
        [["Unstructured (any weight can be 0)", "Compressed formats (bitmap, "
          "CSR/CSC indices); zeros never fetched; gather logic selects matching "
          "activations", "Index storage and irregular access; load imbalance "
          "between lanes"],
         ["Structured N:M (e.g. 2:4)", "Store only 2 of every 4 weights plus "
          "2-bit indices; a 4:2 mux picks activations - a 2x MAC reduction "
          "with a regular datapath (the scheme used by NVIDIA's sparse tensor "
          "cores)", "Pruning must respect the pattern; small mux cost"],
         ["Block / channel pruning", "Remove whole rows, filters or channels: "
          "the layer is simply smaller", "Coarser pruning, more accuracy loss "
          "per removed weight"],
         ["Operand isolation (this chapter)", "Gate the multiplier on zeros",
          "Power only; no speedup"]],
        widths=[22, 52, 26])

    h2("Scaling up: from a dot-product engine to a systolic array")
    diagram([
        "              weights preloaded (weight-stationary), one per PE",
        "                  col 0        col 1        col 2        col 3",
        "  a[0] -------> [PE w00] --> [PE w01] --> [PE w02] --> [PE w03]",
        "                    |            |            |            |      activations flow",
        "  a[1] -[z1]--> [PE w10] --> [PE w11] --> [PE w12] --> [PE w13]    right, one PE",
        "                    |            |            |            |      per cycle",
        "  a[2] -[z2]--> [PE w20] --> [PE w21] --> [PE w22] --> [PE w23]",
        "                    |            |            |            |      partial sums",
        "                    v            v            v            v      flow down",
        "                  y[0]         y[1]         y[2]         y[3]",
        "",
        "  PE:  psum_out_q <= psum_in + a_in * w;   a_out_q <= a_in;",
    ], "A weight-stationary systolic array (the organization of Google's first TPU). "
       "zN = N-cycle input skew. Each PE is one lane of this chapter's S1-S2 "
       "with registered neighbours.")
    bul(["**Reuse**: each activation fetched once is used by every column; each "
         "weight is fetched once per tile and used for every activation that "
         "streams past. An N x N array does N^{2} MACs per cycle for about 2N "
         "operands - the energy table's lesson in hardware form.",
         "**Locality**: every wire connects neighbours, so the array scales to "
         "128 x 128 and beyond without long global wires; physical design "
         "tiles it (Ch. 21).",
         "**Requantization** moves to the array edge: one requant unit per "
         "column, which is exactly this chapter's S3-S4, shared.",
         "**Alternatives**: output-stationary (accumulators stay in the PEs), "
         "row-stationary (Eyeriss), and vector/SIMD engines with a local SRAM; "
         "the right choice depends on the layer shapes the product must run."])

    h2("Integrating the engine into an SoC")
    diagram([
        "  +-------+           AXI4 system interconnect",
        "  |  CPU  |<=====+=======================+========================+",
        "  +-------+      |                       |                        |",
        "      ^     +----+-----+         +-------+-------+         +------+------+",
        "      |     | SRAM /   |         |      DMA      |         | AXI-Lite or |",
        "      |     | DRAM     |         |  MM2S   S2MM  |         | APB bridge  |",
        "      |     +----------+         +--+--------^---+         +------+------+",
        "      |                             |        |                    | CSR port",
        "      |                  AXIS s_t*  v        |  AXIS m_t*         v",
        "      |                          +--+--------+--------------------+--+",
        "      |                          |              mac_accel            |",
        "      |                          +-----------------------------------+",
        "      +---- irq: DMA S2MM done (via the interrupt controller)",
    ], "A typical integration: a DMA streams operands in and results out; the CPU "
       "only configures and handles one interrupt per layer.")
    tbl(["Step", "Driver action"],
        [["1", "Write MULT, SHIFT, ZP, BIAS for the layer (per output channel in "
          "a real design - usually a small table in the engine)"],
         ["2", "Clean the data cache for the operand buffers so the DMA reads "
          "what the CPU wrote (or use a coherent port)"],
         ["3", "Program the MM2S channel with the packed operand buffer and the "
          "S2MM channel with the result buffer (Ch. 16)"],
         ["4", "Start S2MM first, then MM2S, so results are never back-pressured "
          "by an unarmed receiver"],
         ["5", "Sleep until the S2MM completion interrupt; invalidate the result "
          "buffer in the cache before reading it"],
         ["6", "Read SKIP_CNT and MAC_CNT for profiling; clear them for the next layer"]],
        widths=[6, 94])
    box("tip", "Where this project goes next",
        "Add a small weight SRAM so weights are loaded once per layer rather "
        "than streamed with every activation; move per-channel scale and bias "
        "into a table; add an int8 ReLU/clamp; then replace S1-S2 with a 4x4 "
        "systolic tile. Put the result on an FPGA (Ch. 26) behind a soft-CPU "
        "and run a real quantized, pruned model from this repository's "
        "notebooks end to end - that is a portfolio project interviewers "
        "remember (Ch. 30).")

    h2("Summary")
    bul(["Integer-only inference reduces a layer to int8 x int8 products, an "
         "int32 accumulator and a single requantization (multiply, rounding "
         "shift, zero point, saturation).",
         "A 4-stage valid/ready pipeline with a global stall is simple and "
         "correct; a skid buffer removes its combinational ready path.",
         "Zero-skipping by operand isolation saves dynamic power on pruned "
         "weights; speedups need compressed or N:M-structured sparsity.",
         "Signedness and rounding are where arithmetic RTL goes wrong; a "
         "bit-exact golden model and negative-value tests catch them.",
         "A constrained-random testbench with back-pressure checked 500 vectors "
         "bit-exactly, and a mutation test proved it can fail.",
         "Dot-product engines are bandwidth-bound; systolic arrays add operand "
         "reuse, and DMA-based integration keeps the CPU out of the data path."])

    h2("Exercises")
    bul(["Make `L` = 8 and 16 and rerun the testbench. What changes in the "
         "RTL, and which path becomes critical?",
         "Change the requantization to TFLite's scheme: a 32-bit multiplier with "
         "a rounding doubling high multiply and round-half-away-from-zero shift. "
         "Update the golden model first and watch the RTL fail, then fix it.",
         "Add a 2-entry skid buffer on the output so `s_tready` no longer "
         "depends combinationally on `m_tready`. Prove it with the unchanged "
         "testbench and measure throughput under 60% back-pressure.",
         "Implement 2:4 structured sparsity: each beat carries 2 weights and "
         "2-bit indices per group of 4 activations. How many multipliers do "
         "you save?",
         "Add an accumulator overflow sticky flag and a directed test that "
         "triggers it. Is overflow possible for vectors under 131072 MACs?",
         "Write the Linux-style driver pseudo-code for one layer using the "
         "integration steps above, including cache maintenance."], ordered=True)


# ------------------------------------------------------------------ Ch 30 ---
def _ch30():
    chapter("The RTL/SoC Career Roadmap: Skills, Study Plan, Portfolio and "
            "Interviews")
    p("The first 29 chapters describe what an RTL engineer knows. This one "
      "describes how people actually get there: what each career stage "
      "expects, a study plan that turns this book into a year of deliberate "
      "practice, the portfolio projects that get a resume read, the tools "
      "worth learning, and how RTL interviews are really structured. Titles and "
      "timelines vary between companies and countries; the progression of "
      "**scope** - from a block, to a subsystem, to a chip, to a product line - "
      "is remarkably consistent.")

    h2("The four stages")
    tbl(["Stage", "Typical scope", "Core skills", "You are ready to move on when..."],
        [["**Beginner** (student, career changer)",
          "Exercises and personal projects",
          "Digital logic, Verilog/SV syntax and simulation semantics, FSMs, "
          "basic testbenches, Linux, git, one scripting language",
          "You can write a FIFO, an FSM and a UART from a spec and verify them "
          "with a self-checking testbench"],
         ["**Junior RTL engineer** (0-3 years)",
          "Blocks and features inside an IP, under review",
          "Coding guidelines, bus protocols, CDC basics, lint/CDC cleanup, "
          "reading STA reports, debugging failing regressions",
          "Your blocks pass review with few findings and you close your own "
          "lint, CDC and timing issues"],
         ["**Senior RTL / IP owner** (3-8 years)",
          "A whole IP or subsystem, from micro-architecture to sign-off",
          "Micro-architecture, PPA trade-offs, timing closure with PD, low "
          "power, DFT collaboration, mentoring, schedule estimation",
          "You own an IP through tapeout and silicon bring-up, and others ask "
          "you to review their designs"],
         ["**Architect / principal** (8+ years)",
          "Chip or product-line architecture",
          "Performance modeling, workload analysis, memory systems, "
          "interconnect and coherency, hardware/software co-design, "
          "roadmaps, cross-team negotiation",
          "- (the scope keeps growing: platform, company technology strategy)"]],
        widths=[16, 20, 36, 28], caption="Years are indicative only; scope and "
        "independence define the stage, not time.")
    box("key", "The one skill that matters at every stage",
        "Debugging. A beginner debugs syntax, a junior debugs a failing test, a "
        "senior debugs a silicon failure from a few register dumps, and an "
        "architect debugs why a product misses its performance target. Every "
        "stage rewards the same habit: form a hypothesis, find the cheapest "
        "experiment that can falsify it, and never guess twice without new data "
        "(Ch. 26).")

    h2("Skills by stage, in detail")
    tbl(["Area", "Beginner", "Junior", "Senior", "Architect"],
        [["RTL coding", "Syntax, blocking vs. non-blocking", "Guideline-clean, "
          "reusable blocks", "Parameterized IP, PPA-aware structure",
          "Reviews for architecture fit"],
         ["Micro-architecture", "Reads block diagrams", "Implements a given "
          "uarch", "Writes the uarch spec", "Defines block partitioning"],
         ["Buses and SoC", "APB", "AXI4-Lite/Stream, CSRs, interrupts",
          "AXI4 full, interconnect, DMA", "Coherency, NoC, QoS"],
         ["Clocks and resets", "Single clock", "2-flop sync, async FIFO usage",
          "CDC/RDC architecture and sign-off", "Clock/power domain plan"],
         ["Implementation", "What synthesis is", "Reads timing reports",
          "Closes timing with PD, low power, DFT", "PPA budgets per block"],
         ["Verification", "Directed self-checking TB", "SVA, constrained "
          "random, coverage reading", "Verification planning with DV",
          "Performance and system validation"],
         ["Software", "Python, shell", "Makefiles, regression scripts, Tcl",
          "Firmware interface, drivers, bring-up", "HW/SW partitioning"]],
        widths=[16, 20, 21, 22, 21])

    h2("A 48-week study plan built on this book")
    p("The plan assumes about 10-12 hours per week alongside study or a job. "
      "Compressed to six months at 20+ hours a week it still works; the order "
      "matters more than the pace. Every block ends in a **deliverable** that "
      "goes into a public repository - by week 48 that repository is your "
      "portfolio.")
    tbl(["Weeks", "Topics", "Chapters", "Deliverable"],
        [["1-3", "Flow, digital logic refresher, Verilog/SV for design",
          "1-3", "Toolchain installed (Icarus/Verilator, GTKWave, Yosys); "
          "20 small modules compiled"],
         ["4-5", "Simulation semantics, races", "4", "Write and fix three "
          "deliberate race conditions"],
         ["6-9", "Combinational, sequential, FSMs, datapath", "5-8",
          "ALU, counters, sequence detectors, a multiplier - each with a "
          "self-checking TB"],
         ["10-12", "Memories, FIFOs, pipelines, valid/ready", "9-10",
          "Sync FIFO + skid buffer, verified with random back-pressure"],
         ["13-15", "Clocks, CDC, resets", "11-12", "Async FIFO with Gray "
          "pointers; reset synchronizer"],
         ["16-19", "Buses, interconnect, CSRs, peripherals", "13-16",
          "APB and AXI4-Lite slaves; **project: APB UART** (Ch. 28)"],
         ["20-23", "Synthesis, STA, low power, DFT, PPA", "17-21", "Run Yosys + "
          "OpenSTA on your UART; fix a timing path; read a gate netlist"],
         ["24-28", "Self-checking TBs, SVA, coverage", "22-23", "Add assertions "
          "and coverage to the UART and FIFO; formal proof of the FIFO with "
          "SymbiYosys"],
         ["29-32", "UVM, static sign-off, debug, FPGA", "24-26", "A small UVM "
          "environment (EDA Playground or a commercial trial); UART on an FPGA "
          "board talking to a PC"],
         ["33-40", "Big project: a RISC-V core", "3-10, 22-23", "RV32I "
          "5-stage pipeline with forwarding and hazards; passes riscv-tests"],
         ["41-46", "Big project: the ML accelerator", "29, 10, 16",
          "MAC engine + DMA + CPU on FPGA running a quantized layer"],
         ["47-48", "Interview preparation", "27, 30, App. C", "100 interview "
          "questions answered aloud; two mock interviews; portfolio polished"]],
        widths=[9, 33, 13, 45])
    box("tip", "Make the plan survive real life",
        "Track it in the same repository (a checklist in the README). Skip a "
        "week, not a topic. When a chapter feels easy, do its exercises anyway - "
        "interviews probe exactly the corner cases the exercises contain.")

    h2("Portfolio projects that get attention")
    tbl(["Project", "What it demonstrates", "Level"],
        [["APB/AXI-Lite UART, SPI or I2C controller with a real register map",
          "Spec-to-silicon discipline: CSRs, interrupts, CDC of an async pin, "
          "self-checking TB", "Beginner-junior"],
         ["Parameterized async FIFO with formal proofs", "CDC mastery; "
          "SymbiYosys or a commercial formal tool", "Junior"],
         ["RISC-V RV32I core (single-cycle, then 5-stage pipelined)",
          "Datapath, hazards, forwarding; passes riscv-tests; optionally "
          "riscv-formal", "Junior-senior"],
         ["AXI4 DMA engine or AXI crossbar", "Full AXI (bursts, IDs, "
          "outstanding transactions) - the protocol most interviews probe",
          "Senior"],
         ["ML accelerator (Ch. 29) extended to a systolic tile on FPGA",
          "PPA thinking, HW/SW co-design, the topic of this repository",
          "Senior"],
         ["Contribution to **OpenTitan**, **CVA6**, **Ibex**, **PULP** or "
          "**OpenHW** cores", "Working in an industrial-quality codebase with "
          "strict review, lint and DV - the closest thing to a job",
          "Junior-senior"],
         ["A **Tiny Tapeout** design through OpenLane to real silicon",
          "The full RTL-to-GDS flow on an open PDK (SkyWater SKY130, GF180MCU "
          "or IHP SG13G2) and a chip you can hold", "Any"]],
        widths=[36, 48, 16])
    p("Open-silicon shuttles have changed quickly: efabless, which ran the "
      "Google-sponsored OpenMPW and chipIgnite shuttles, ceased operations in "
      "2025, and Tiny Tapeout has since used other shuttle providers. Check the "
      "project's site for the current PDK and deadlines; the skills - "
      "OpenLane/OpenROAD, DRC/LVS, timing sign-off - transfer regardless.")
    bul(["**Present each project like IP**: a README with a block diagram, the "
         "register map, a verification summary (what is covered and what is "
         "not), synthesis area and Fmax numbers, and one command that runs the "
         "tests.",
         "**CI on every push** (GitHub Actions with Verilator/Icarus and "
         "Verible lint) shows discipline in one green badge.",
         "**Depth beats breadth**: one well-verified, documented core with "
         "formal proofs is worth more than ten half-finished repositories.",
         "**Be ready to defend every line** - interviewers pick a random module "
         "and ask why it is written that way."])

    h2("Tools to learn")
    tbl(["Category", "Free / open source", "Commercial (industry standard)"],
        [["Simulation", "Icarus Verilog, Verilator, GHDL (VHDL)", "Synopsys VCS, "
          "Cadence Xcelium, Siemens Questa"],
         ["Waveforms and debug", "GTKWave, Surfer", "Synopsys Verdi, Cadence "
          "SimVision / Indago"],
         ["Lint", "Verilator `--lint-only`, Verible", "Synopsys SpyGlass, Real "
          "Intent Ascent, Cadence HAL / Jasper Superlint"],
         ["CDC / RDC", "(limited open options)", "SpyGlass CDC, Questa CDC, "
          "Real Intent Meridian, Jasper CDC"],
         ["Formal", "SymbiYosys (Yosys + SMT solvers)", "Cadence Jasper, "
          "Synopsys VC Formal, Siemens Questa Formal"],
         ["Verification frameworks", "cocotb (Python), SV UVM on EDA Playground",
          "UVM with commercial simulators and VIP"],
         ["Synthesis", "Yosys", "Synopsys Design Compiler / Fusion Compiler, "
          "Cadence Genus"],
         ["STA", "OpenSTA", "Synopsys PrimeTime, Cadence Tempus"],
         ["Physical design", "OpenROAD / OpenLane", "Synopsys ICC2 / Fusion "
          "Compiler, Cadence Innovus"],
         ["FPGA", "Yosys + nextpnr; free editions of Vivado and Quartus",
          "Full Vivado / Quartus; emulation: Palladium, ZeBu, Veloce"],
         ["Glue", "Linux shell, Python, Tcl, Make, git", "(same - these are "
          "universal)"]],
        widths=[20, 38, 42])
    box("note", "Open-source tools are not a lesser path",
        "The concepts - elaboration, scheduling, synthesis, STA, formal - are "
        "the same in every tool. Engineers who learned on Yosys and OpenSTA "
        "switch to commercial tools in weeks; what takes years is the "
        "judgment the tools cannot give you. Tcl (for every commercial tool) "
        "and Python (for everything around them) are the two languages to be "
        "fluent in.")

    h2("How RTL interviews are structured")
    tbl(["Round", "What happens", "What they are really testing"],
        [["Recruiter screen", "Background, interests, logistics",
          "Communication; match to the team"],
         ["Technical phone screen", "Digital logic, Verilog semantics, a "
          "small design on a shared editor", "Fundamentals: blocking vs. "
          "non-blocking, latches, setup/hold, FSM encoding"],
         ["RTL coding", "Write synthesizable RTL for a FIFO, arbiter, edge "
          "detector, clock divider, sequence detector or credit counter",
          "Clean code, correct reset, no latches, handling of corner cases "
          "(full and empty at once, back-to-back requests)"],
         ["CDC and clocks", "Synchronize a pulse, a bus, a reset; design an "
          "async FIFO; explain metastability and MTBF",
          "Whether you know **why** each technique works (Ch. 11-12)"],
         ["Timing / STA", "Setup/hold equations, fix a violation, max "
          "frequency of a circuit, effect of skew",
          "Physical intuition about paths (Ch. 18)"],
         ["Architecture / micro-architecture", "Design a cache, a DMA, a "
          "pipelined unit; discuss trade-offs",
          "Structured thinking, PPA awareness, asking clarifying questions"],
         ["Puzzles", "Divisible-by-3 detector, divide-by-3 clock with 50% duty, "
          "count ones, gray code, one-hot checks", "Reasoning under pressure; "
          "state-machine thinking"],
         ["Project deep-dive", "Walk through your resume project in detail",
          "Ownership: can you defend decisions and explain bugs you found?"],
         ["Behavioral", "Conflicts, failures, deadlines", "Team fit, "
          "honesty, learning from mistakes"]],
        widths=[18, 42, 40])
    eq(["setup:  T_clk >= t_clk-q + t_logic,max + t_setup - t_skew",
        "hold:   t_clk-q + t_logic,min >= t_hold + t_skew",
        "        (t_skew = capture clock arrival - launch clock arrival)",
        "f_max = 1 / (t_clk-q + t_logic,max + t_setup - t_skew)"],
        "The two inequalities every timing question reduces to. Note that "
        "positive skew helps setup and hurts hold, and a hold violation cannot "
        "be fixed by slowing the clock.")

    h3("A classic puzzle, solved as an interviewer wants to see it")
    p("'Bits of a binary number arrive serially, MSB first. Assert an output "
      "whenever the number received so far is divisible by 3.' The key insight "
      "is that you never need the number - only its **remainder**. Appending a "
      "bit b maps value v to 2v + b, so the remainder r becomes "
      "(2r + b) mod 3: a 3-state FSM.")
    code(_lines(DIV3_SV), "div3_detect.sv - the remainder FSM, with a safe "
         "default for the unreachable encoding.")
    code(_seg(TB_DIV3, "module tb_div3"), "Exhaustive check of every 8-bit number.")
    out(["n=  9 bits=00001001 div3=1",
         "n= 10 bits=00001010 div3=0",
         "n=255 bits=11111111 div3=1",
         "all 256 8-bit numbers checked, 0 errors",
         "tb_div3.sv:22: $finish called at 23050000 (1ps)"])
    box("tip", "How to behave in a coding round",
        "Restate the problem and ask about the interface (reset polarity, "
        "valid signal, MSB or LSB first). Draw the state diagram or datapath "
        "**before** writing code. Write the reset and the defaults first. Then "
        "test out loud: walk one input sequence through your design, including "
        "a corner case. Interviewers score the process as much as the answer - "
        "a candidate who finds their own bug scores higher than one who never "
        "checked.")

    h2("Soft skills that separate good engineers from great ones")
    bul(["**Writing**: specs, review comments and bug reports that others can "
         "act on without a meeting. The micro-architecture spec (Ch. 27) is "
         "the most visible artifact of your thinking.",
         "**Reviewing well and being reviewed well**: comment on the code, not "
         "the author; accept findings without defending; thank the reviewer "
         "who found your bug before silicon did.",
         "**Estimating honestly**: break work into verifiable steps, add time "
         "for verification and sign-off, and report slips early.",
         "**Working across disciplines**: DV, PD, DFT, firmware and "
         "architecture all depend on your RTL. Learn enough of their language "
         "to ask the right questions (Parts IV and V exist for this reason).",
         "**Reading standards**: the AMBA specifications, IEEE 1800, and the "
         "RISC-V ISA manual are primary sources; an engineer who quotes the "
         "spec ends arguments.",
         "**Teaching**: mentoring juniors and writing internal notes is how "
         "seniors multiply their impact - and how they are recognized as senior."])

    h2("Specializations")
    tbl(["Specialization", "What you do", "Key skills", "Why RTL helps"],
        [["**Design verification (DV)**", "Prove the design matches the spec "
          "before tapeout", "SV/UVM, constrained random, coverage, SVA, "
          "formal, Python", "You know where designers make mistakes"],
         ["**DFT**", "Make the chip testable: scan, ATPG, MBIST, JTAG, "
          "test-mode clocking", "Test compression, fault models, ATE "
          "patterns, Tcl", "DFT fixes are RTL changes (Ch. 20)"],
         ["**Physical design (PD)**", "Floorplan, place, CTS, route, "
          "timing/power/IR sign-off", "STA, SDC, floorplanning, ECOs, "
          "scripting", "You can push back on - or fix - unroutable RTL"],
         ["**Architecture / performance**", "Define what to build; model "
          "performance and power", "C++/SystemC/Python models, workload "
          "analysis, statistics", "Your models are credible because you know "
          "what hardware costs"],
         ["**FPGA design**", "Designs that ship on FPGAs; prototyping and "
          "emulation", "Vendor tools, IP integration, timing on FPGA "
          "fabric, high-speed I/O", "Same RTL, different PPA rules"],
         ["**Static sign-off (lint/CDC/RDC)**", "Own methodology and sign-off "
          "for a chip", "Tool expertise, waiver discipline, "
          "clock/reset architecture", "Every violation is an RTL structure"],
         ["**Post-silicon validation**", "Bring up and debug real chips",
          "Lab equipment, debug infrastructure, firmware", "Root-causing needs "
          "the RTL in your head"]],
        widths=[20, 27, 29, 24])

    h2("Final checklist")
    checklist("Ready for a junior RTL role?", [
        "I can explain blocking vs. non-blocking assignment in terms of the event "
        "scheduler, and show the race that the wrong choice causes (Ch. 4)",
        "I write latch-free combinational logic and correctly reset sequential "
        "logic without thinking about it (Ch. 5-6)",
        "I can design and verify an FSM, a synchronous FIFO and a valid/ready "
        "pipeline stage with a skid buffer from scratch (Ch. 7, 9-10)",
        "I can explain metastability and design a pulse synchronizer and an "
        "async FIFO (Ch. 11)",
        "I can write an APB slave and describe AXI4 channels and handshake rules "
        "(Ch. 13)",
        "I can read a timing report and state the setup and hold equations "
        "(Ch. 18)",
        "I have written a self-checking testbench with a reference model, and "
        "SVA assertions for a protocol (Ch. 22-23)",
        "I have at least one complete, documented, verified project in a public "
        "repository (Ch. 28 or 29 extended)",
        "I have run a design through synthesis and looked at the netlist and the "
        "area/timing reports (Ch. 17)",
        "I use git, Linux, Make and Python or Tcl comfortably",
        "I have answered Appendix C's interview questions aloud",
        "I can walk through my portfolio project and defend every design decision"])

    h2("Summary")
    bul(["Careers progress by scope: block, IP, chip, product line; each stage "
         "has distinct skills and signals of readiness.",
         "A 48-week plan through this book, with a public deliverable per "
         "block, builds both the skills and the portfolio.",
         "The strongest portfolios are few, deep and well-verified: a "
         "peripheral, a RISC-V core, an accelerator, an open-source "
         "contribution, a tapeout.",
         "Learn the concepts on free tools; commercial tools follow quickly. "
         "Tcl and Python are mandatory.",
         "Interviews test fundamentals (semantics, CDC, STA, FSMs) and the "
         "process of design as much as the answer.",
         "Specializations - DV, DFT, PD, architecture, FPGA, sign-off, "
         "post-silicon - all build on a solid RTL foundation."])

    h2("Exercises")
    bul(["Place yourself in the skills table of 30.2. For each area, write the "
         "one concrete action that would move you one column to the right.",
         "Adapt the 48-week plan to your available hours and publish it as the "
         "README of your portfolio repository.",
         "Solve the divide-by-3 **clock** puzzle: design a divide-by-3 clock "
         "divider with 50% duty cycle, and explain why it needs both clock "
         "edges and what that means for STA and DFT.",
         "Write RTL in 30 minutes, without a simulator, for a 4-requester "
         "round-robin arbiter. Then simulate it and count your bugs.",
         "Pick one specialization from 30.8 and find three open-source projects "
         "or tools where you could practice it.",
         "Run a mock interview with a friend using five questions from Appendix "
         "C; record yourself and review how you explained your reasoning."],
        ordered=True)
