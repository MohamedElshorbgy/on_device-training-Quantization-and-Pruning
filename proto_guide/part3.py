"""Part III - Low-Speed Peripheral Protocols (Chapters 11-16) of the protocols guide.

Every Verilog/SystemVerilog design and testbench in SRC was compiled with Icarus
Verilog 12 (iverilog -g2012 -Wall) and simulated with vvp; the py_* entries are
Python 3 reference models. OUT holds the captured output verbatim (only the
trailing "$finish called" line is omitted).
"""

from proto_guide.common import *  # noqa: F401,F403

# --- sources and REAL simulator / Python output (generated from the scratch runs) ---
SRC = {
    'uart': r'''
// Fractional (NCO) baud-tick generator: tick rate = f_clk * INC / 2^24
module baud_nco (
  input  logic        clk, rst_n,
  input  logic [23:0] inc,              // = 2^24 * 16 * baud / f_clk
  output logic        tick16            // one pulse per 1/16 bit
);
  logic [24:0] acc;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin acc <= '0; tick16 <= 1'b0; end
    else begin
      acc    <= {1'b0, acc[23:0]} + inc;
      tick16 <= acc[24];                // carry out = one tick
    end
endmodule

module uart_tx (                        // 8N1 transmitter
  input  logic       clk, rst_n, tick16,
  input  logic       start, input logic [7:0] data,
  output logic       txd, busy
);
  logic [9:0] sh;  logic [3:0] nbit, ph;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin sh <= '1; busy <= 0; nbit <= 0; ph <= 0; end
    else if (!busy && start) begin
      sh <= {1'b1, data, 1'b0};         // stop, D7..D0, start (LSB goes first)
      busy <= 1; nbit <= 0; ph <= 0;
    end else if (busy && tick16) begin
      ph <= ph + 1;
      if (ph == 15) begin               // 16 ticks = one bit time
        sh <= {1'b1, sh[9:1]};
        nbit <= nbit + 1;
        if (nbit == 9) busy <= 0;       // start + 8 data + stop sent
      end
    end
  assign txd = busy ? sh[0] : 1'b1;
endmodule

module uart_rx (                        // 8N1 receiver, 16x oversampling
  input  logic       clk, rst_n, tick16, rxd_async,
  output logic       valid, ferr,       // one-cycle pulses
  output logic [7:0] data
);
  typedef enum logic [1:0] {IDLE, START, DATA, STOP} st_t;
  st_t st;  logic [3:0] ph;  logic [2:0] nbit;  logic r1, rxd;
  always_ff @(posedge clk or negedge rst_n)      // 2-flop synchronizer
    if (!rst_n) {rxd, r1} <= 2'b11; else {rxd, r1} <= {r1, rxd_async};
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin st <= IDLE; ph <= 0; nbit <= 0; valid <= 0; ferr <= 0; data <= 0; end
    else begin
      valid <= 0; ferr <= 0;
      if (tick16) case (st)
        IDLE:  if (!rxd) begin st <= START; ph <= 0; end   // falling edge seen
        START: if (ph == 7) begin                // middle of the start bit
                 st <= rxd ? IDLE : DATA;        // high again = glitch, not a start
                 ph <= 0; nbit <= 0;
               end else ph <= ph + 1;
        DATA:  if (ph == 15) begin               // 16 ticks later = middle of next bit
                 data <= {rxd, data[7:1]};       // LSB first
                 ph <= 0; nbit <= nbit + 1;
                 if (nbit == 7) st <= STOP;
               end else ph <= ph + 1;
        STOP:  if (ph == 15) begin
                 valid <= rxd;  ferr <= !rxd;    // stop bit must be 1
                 st <= IDLE;  ph <= 0;
               end else ph <= ph + 1;
      endcase
    end
endmodule''',
    'tb_uart': r'''
module tb;
  logic clk = 0, rst_n = 0;  always #5 clk = ~clk;          // 100 MHz
  localparam real NOM = 16.0 * 115200.0 * 16777216.0 / 100.0e6;
  logic [23:0] inc_tx, inc_rx;  logic t_tx, t_rx;
  logic start = 0, busy, txd, valid, ferr;  logic [7:0] d, q;
  baud_nco gtx (.clk, .rst_n, .inc(inc_tx), .tick16(t_tx));
  baud_nco grx (.clk, .rst_n, .inc(inc_rx), .tick16(t_rx));
  uart_tx  tx  (.clk, .rst_n, .tick16(t_tx), .start, .data(d), .txd, .busy);
  uart_rx  rx  (.clk, .rst_n, .tick16(t_rx), .rxd_async(txd), .valid, .ferr, .data(q));
  int ERR[] = '{-60, -55, -50, -45, -30, 0, 30, 45, 50, 55, 60};
  byte exp_q[$];  int good, bad, fe;
  always @(posedge clk) if (valid || ferr) begin
    if (valid && q == exp_q[0]) good++; else bad++;
    if (ferr) fe++;
    void'(exp_q.pop_front());
  end
  initial begin
    inc_rx = $rtoi(NOM);
    $display("TX baud error  sent  rx_ok  rx_bad  framing_err");
    foreach (ERR[k]) begin  int e;  e = ERR[k];     // TX error in 0.1 % steps
      inc_tx = $rtoi(NOM * (1.0 + e / 1000.0));
      rst_n = 0; good = 0; bad = 0; fe = 0; exp_q.delete();
      repeat (4) @(posedge clk); rst_n = 1;
      for (int i = 0; i < 64; i++) begin              // back-to-back frames
        d = (i % 2) ? 8'h00 : 8'($urandom);
        exp_q.push_back(d);
        @(posedge clk) start = 1; @(posedge clk) start = 0;
        wait (busy == 0);
      end
      repeat (3000) @(posedge clk);
      $display("   %5.1f %%      64     %2d      %2d       %2d", e / 10.0, good, bad, fe);
    end
    $finish;
  end
endmodule''',
    'spi': r'''
module spi_master #(parameter int HALF = 2) (   // SCLK half-period in clk cycles
  input  logic       clk, rst_n,
  input  logic       cpol, cpha,               // mode = {cpol, cpha}
  input  logic       start, input logic [7:0] tx,
  output logic       done,  output logic [7:0] rx,
  output logic       sclk, mosi, cs_n,
  input  logic       miso
);
  logic [7:0] sh;  logic [4:0] edges;  logic [$clog2(HALF+1)-1:0] cnt;
  logic       lvl, busy;                         // lvl: SCLK before CPOL inversion
  wire        tick    = busy && (cnt == HALF-1);
  wire        leading = (lvl == 1'b0);           // edge about to be made is leading
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      busy <= 0; cs_n <= 1; lvl <= 0; cnt <= 0; edges <= 0; done <= 0;
      sh <= 0; rx <= 0; mosi <= 0;
    end else begin
      done <= 0;
      cnt  <= tick ? '0 : (busy ? cnt + 1 : '0);
      if (!busy && start) begin
        busy <= 1; cs_n <= 0; edges <= 0; lvl <= 0;
        sh <= tx;  mosi <= cpha ? 1'b0 : tx[7];  // CPHA=0: first bit valid at CS fall
      end else if (tick && edges == 16) begin   // half-period CS hold, then finish
        busy <= 0; cs_n <= 1; done <= 1;
      end else if (tick) begin
        lvl   <= ~lvl;  edges <= edges + 1;
        if (leading ^ cpha) rx <= {rx[6:0], miso};           // sample edge
        else if (cpha)       begin mosi <= sh[7]; sh <= {sh[6:0], 1'b0}; end
        else if (edges != 15) begin mosi <= sh[6]; sh <= {sh[6:0], 1'b0}; end
      end
    end
  assign sclk = lvl ^ cpol;                      // CPOL just inverts the idle level
endmodule''',
    'tb_spi': r'''
module tb;
  logic clk = 0, rst_n = 0;  always #5 clk = ~clk;
  logic cpol, cpha, start = 0, done, sclk, mosi, cs_n, miso;
  logic [7:0] tx, rx;
  spi_master #(.HALF(2)) m (.*);
  // ---- behavioural slave for any mode: leading edge = posedge of (sclk ^ cpol) ----
  logic [7:0] s_sh, s_tx, s_rx;  int nb;
  wire  sck_l = sclk ^ cpol;
  always @(negedge cs_n) begin s_sh = s_tx; nb = 0; if (!cpha) miso = s_sh[7]; end
  always @(posedge sck_l) if (!cs_n) begin                  // leading edge
    if (!cpha) begin s_rx = {s_rx[6:0], mosi}; nb++; end
    else       miso = s_sh[7];
  end
  always @(negedge sck_l) if (!cs_n) begin                  // trailing edge
    if (cpha)  begin s_rx = {s_rx[6:0], mosi}; nb++; s_sh = {s_sh[6:0], 1'b0}; end
    else       begin s_sh = {s_sh[6:0], 1'b0}; miso = s_sh[7]; end
  end
  // ---- simple waveform printer: one character per clk ----
  string w_cs, w_sck, w_mosi;
  always @(posedge clk) if (cpol == cpha) begin
    w_cs   = {w_cs,   cs_n ? "~" : "_"};
    w_sck  = {w_sck,  sclk ? "~" : "_"};
    w_mosi = {w_mosi, cs_n ? "-" : (mosi ? "1" : "0")};
  end
  initial begin
    repeat (2) @(posedge clk); rst_n = 1;
    for (int mode = 0; mode < 4; mode++) begin
      {cpol, cpha} = mode[1:0];
      tx = 8'hA0 | mode;  s_tx = 8'h5C ^ mode;
      repeat (2) @(posedge clk);  w_cs = ""; w_sck = ""; w_mosi = "";
      @(posedge clk) start <= 1;  @(posedge clk) start <= 0;
      @(posedge done); repeat (3) @(posedge clk);
      $display("mode %0d (CPOL=%0d CPHA=%0d): M->S %h got %h | S->M %h got %h  %s",
               mode, cpol, cpha, tx, s_rx, s_tx, rx,
               (s_rx == tx && rx == s_tx && nb == 8) ? "PASS" : "FAIL");
      if (mode == 0 || mode == 3) begin
        $display("   CS_n %s", w_cs);  $display("   SCLK %s", w_sck);
        $display("   MOSI %s", w_mosi);
      end
    end
    $finish;
  end
endmodule''',
    'qspi': r'''
// Fast Read Quad Output (6Bh), 1-1-4: command and address on IO0, 8 dummy clocks,
// data on IO[3:0]. SCLK = clk/2 (mode 0). rx_dly moves the capture point by 1 clk.
module qspi_rd (
  input  logic        clk, rst_n, start, rx_dly,
  input  logic [23:0] addr,  input logic [3:0] nbytes,
  output logic        sclk, cs_n, done,
  output logic [3:0]  io_o, io_oe,  input logic [3:0] io_i,
  output logic [63:0] rdata                      // up to 8 bytes, first byte in [63:56]
);
  typedef enum logic [1:0] {IDLE, CMDADR, DUMMY, DATA} st_t;
  st_t st;  logic [31:0] sh;  logic [5:0] n;  logic [4:0] nib, ncap;  logic cap_d;
  wire rise = (st != IDLE) && !sclk;             // this clk edge makes SCLK rise
  wire fall = (st != IDLE) &&  sclk;
  wire cap  = rx_dly ? cap_d : (rise && st == DATA);   // capture strobe
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin st <= IDLE; sclk <= 0; cs_n <= 1; done <= 0; io_oe <= 0; io_o <= 0;
                      sh <= 0; n <= 0; nib <= 0; ncap <= 0; cap_d <= 0; rdata <= 0; end
    else begin
      done  <= 0;
      cap_d <= rise && st == DATA;
      if (cap) begin rdata <= {rdata[59:0], io_i}; ncap <= ncap + 1; end
      case (st)
        IDLE: if (start) begin
                st <= CMDADR; cs_n <= 0; sh <= {8'h6B, addr}; n <= 0; ncap <= 0;
                io_oe <= 4'b0001; io_o <= 4'b0;     // bit 7 of 6Bh (=0) valid at CS fall
              end else if (cs_n == 0 && ncap == 2*nbytes) begin
                cs_n <= 1; done <= 1;                          // last nibble captured
              end
        default: begin
          sclk <= ~sclk;
          if (fall) begin                                      // launch on falling edge
            n <= n + 1;
            case (st)
              CMDADR: if (n == 31) begin st <= DUMMY; n <= 0; io_oe <= 0; end
                      else begin sh <= {sh[30:0], 1'b0}; io_o[0] <= sh[30]; end
              DUMMY:  if (n == 7) begin st <= DATA; n <= 0; nib <= 0; end
              DATA:   if (nib == 2*nbytes - 1) st <= IDLE;
                      else nib <= nib + 1;
              default: ;
            endcase
          end
        end
      endcase
    end
endmodule''',
    'tb_qspi': r'''
module tb;
  logic clk = 0, rst_n = 0;  always #2.5 clk = ~clk;       // 200 MHz -> SCLK 100 MHz
  logic start = 0, rx_dly, sclk, cs_n, done;  logic [3:0] io_o, io_oe;
  logic [63:0] rdata;  real t_rt;                          // board + flash round trip
  wire  [3:0] io;
  qspi_rd dut (.clk, .rst_n, .start, .rx_dly, .addr(24'h000100), .nbytes(4'd8),
               .sclk, .cs_n, .done, .io_o, .io_oe, .io_i(io), .rdata);
  for (genvar i = 0; i < 4; i++) assign io[i] = io_oe[i] ? io_o[i] : 1'bz;
  // ---------------- flash model: 32 clocks of cmd+addr, 8 dummy, then nibbles -------------
  logic [7:0] mem [0:511];  logic [3:0] f_out;  logic f_oe;  int clks;  logic [31:0] ca;
  logic [23:0] fa;  int nibc;
  assign io = f_oe ? f_out : 4'bz;
  initial for (int i = 0; i < 512; i++) mem[i] = 8'(i * 7 + 8'h31);
  always @(negedge cs_n) begin clks = 0; f_oe = 0; ca = 0; nibc = 0; end
  always @(posedge cs_n) f_oe <= #(t_rt) 0;
  always @(posedge sclk) if (!cs_n) begin
    if (clks < 32) ca = {ca[30:0], io[0]};
    clks++;
  end
  always @(negedge sclk) if (!cs_n && clks >= 40) begin     // after 32 + 8 dummy clocks
    fa = ca[23:0] + nibc / 2;
    f_oe  <= #(t_rt) 1;
    f_out <= #(t_rt) (nibc % 2) ? mem[fa][3:0] : mem[fa][7:4];
    nibc++;
  end
  logic [63:0] exp_d;
  initial begin
    for (int i = 0; i < 8; i++) exp_d = {exp_d[55:0], 8'(( 256 + i) * 7 + 8'h31)};
    repeat (2) @(posedge clk); rst_n = 1;
    $display("round trip  rx_dly  opcode addr    data read          result");
    for (int k = 0; k < 6; k++) begin
      t_rt   = 3.0 + 3.0 * (k % 3);                     // 3, 6, 9 ns
      rx_dly = (k >= 3);
      @(posedge clk) start <= 1; @(posedge clk) start <= 0;
      @(posedge done); repeat (4) @(posedge clk);
      $display("  %4.1f ns     %0d     %h    %h  %h  %s", t_rt, rx_dly, ca[31:24], ca[23:0],
               rdata, rdata == exp_d ? "PASS" : "FAIL");
    end
    $display("SCLK cycles per 8-byte read: 8 cmd + 24 addr + 8 dummy + 16 data = %0d", clks);
    $finish;
  end
endmodule''',
    'i2c': r'''
// Byte-command I2C master. Pads are open-drain: *_oe = 1 pulls the line low.
module i2c_master #(parameter int QTR = 25) (   // clk cycles per quarter of an SCL period
  input  logic       clk, rst_n,
  input  logic       go,  input logic [1:0] cmd, // 0 START/rep.START 1 WRITE 2 READ 3 STOP
  input  logic [7:0] wdata, input logic nack_send, // for READ: 1 = answer with NACK
  output logic       done, output logic [7:0] rdata, output logic nack_rcvd,
  output logic       scl_oe, sda_oe,
  input  logic       scl_i, sda_i
);
  typedef enum logic [1:0] {IDLE, START, BITS, STOP} st_t;
  st_t st;  logic [1:0] q, c;  logic [3:0] bitn;  logic [8:0] sh;  logic rd;
  logic [$clog2(QTR)-1:0] t;  logic [1:0] scl_s, sda_s;
  always_ff @(posedge clk) begin scl_s <= {scl_s[0], scl_i}; sda_s <= {sda_s[0], sda_i}; end
  wire scl = scl_s[1], sda = sda_s[1];
  // a quarter ends after QTR cycles; SCL is released at the end of quarter 1, and in
  // quarter 2 time only runs once SCL is really high: clock stretching pauses us here
  wire qend = (t == QTR-1);
  wire hold = (q == 2) && !scl;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      st <= IDLE; q <= 0; t <= 0; scl_oe <= 0; sda_oe <= 0; done <= 0;
      bitn <= 0; sh <= 0; rd <= 0; rdata <= 0; nack_rcvd <= 0; c <= 0;
    end else begin
      done <= 0;
      if (st == IDLE) begin
        if (go) begin
          c <= cmd;  q <= 0; t <= 0; bitn <= 0;  rd <= (cmd == 2);
          sh <= (cmd == 2) ? {8'hFF, nack_send} : {wdata, 1'b1};  // 1 = release SDA
          st <= (cmd == 0) ? START : (cmd == 3) ? STOP : BITS;
        end
      end else if (!hold) begin
        t <= qend ? '0 : t + 1;
        if (qend) begin
          q <= q + 1;
          case (st)
            START: case (q)                    // SDA falls while SCL is high
                     0: sda_oe <= 0;           // release SDA (repeated START case)
                     1: scl_oe <= 0;           // release SCL, wait until high
                     2: sda_oe <= 1;           // START condition
                     3: begin scl_oe <= 1; st <= IDLE; done <= 1; end
                   endcase
            STOP:  case (q)                    // SDA rises while SCL is high
                     0: begin scl_oe <= 1; sda_oe <= 1; end
                     1: scl_oe <= 0;
                     2: sda_oe <= 0;           // STOP condition
                     3: begin st <= IDLE; done <= 1; end
                   endcase
            BITS:  case (q)                    // 9 bits: 8 data + ACK
                     0: begin scl_oe <= 1; sda_oe <= ~sh[8]; end   // change SDA, SCL low
                     1: scl_oe <= 0;                              // rising edge
                     2: sh <= {sh[7:0], sda};                     // sample while high
                     3: begin
                          scl_oe <= 1;                            // falling edge
                          bitn <= bitn + 1;
                          if (bitn == 8) begin
                            st <= IDLE; done <= 1; sda_oe <= 0;
                            if (rd) rdata <= sh[8:1]; else nack_rcvd <= sh[0];
                          end
                        end
                   endcase
            default: ;
          endcase
        end
      end
    end
endmodule''',
    'tb_i2c': r'''
module tb;
  logic clk = 0, rst_n = 0;  always #10 clk = ~clk;         // 50 MHz, QTR=125 -> 100 kHz
  wire  scl, sda;  pullup (scl);  pullup (sda);             // wired-AND bus + pull-ups
  logic go = 0, done, nack_rcvd, m_scl_oe, m_sda_oe, nack_send = 0;
  logic [1:0] cmd;  logic [7:0] wdata, rdata;
  i2c_master #(.QTR(125)) m (.clk, .rst_n, .go, .cmd, .wdata, .nack_send, .done, .rdata,
       .nack_rcvd, .scl_oe(m_scl_oe), .sda_oe(m_sda_oe), .scl_i(scl), .sda_i(sda));
  assign scl = m_scl_oe ? 1'b0 : 1'bz;
  assign sda = m_sda_oe ? 1'b0 : 1'bz;
  // ---------------- behavioural slave at address 0x50 with 256 byte registers --------------
  localparam logic [6:0] MY = 7'h50;
  typedef enum {S_IDLE, S_ADDR, S_WR, S_RD} sst_t;
  sst_t ss;  int bitc;  bit in_ack, first, m_nack;  logic [7:0] ssh, ptr, regs [256];
  logic s_sda_low = 0, s_scl_low = 0;
  assign sda = s_sda_low ? 1'b0 : 1'bz;
  assign scl = s_scl_low ? 1'b0 : 1'bz;
  always @(negedge sda) if (scl === 1'b1) begin ss = S_ADDR; bitc = 0; in_ack = 0; end
  always @(posedge sda) if (scl === 1'b1) begin ss = S_IDLE; s_sda_low = 0; end
  always @(posedge scl) if (ss != S_IDLE) begin
    if (!in_ack && bitc < 8) begin if (ss != S_RD) ssh = {ssh[6:0], sda}; bitc++; end
    else if (in_ack && ss == S_RD) m_nack = sda;           // master's ACK/NACK
  end
  always @(negedge scl) if (ss != S_IDLE) begin
    if (!in_ack && bitc == 8) begin                       // 8 bits done -> ACK slot
      in_ack = 1;
      case (ss)
        S_ADDR: if (ssh[7:1] == MY) s_sda_low = 1; else ss = S_IDLE;   // not me: NACK
        S_WR:   begin s_sda_low = 1; if (first) ptr = ssh; else regs[ptr++] = ssh;
                      first = 0; end
        S_RD:   s_sda_low = 0;                            // master drives ACK
        default: ;
      endcase
    end else if (in_ack) begin                            // ACK slot finished
      in_ack = 0; bitc = 0; s_sda_low = 0;
      if (ss == S_ADDR) begin
        if (ssh[0]) begin                                 // read: stretch, then data
          s_scl_low = 1;  ss = S_RD;  ssh = regs[ptr++];
          #20000 s_sda_low = ~ssh[7];                     // data ready after 20 us
          #500   s_scl_low = 0;                           // ... then release SCL
        end else begin ss = S_WR; first = 1; end
      end else if (ss == S_RD) begin
        if (m_nack) ss = S_IDLE; else begin ssh = regs[ptr++]; s_sda_low = ~ssh[7]; end
      end
    end else if (ss == S_RD && bitc < 8) s_sda_low = ~ssh[7 - bitc];
  end
  // ---------------- command helpers ----------------
  task automatic op(input logic [1:0] c, input logic [7:0] d = 0, input logic nk = 0);
    @(posedge clk) begin go <= 1; cmd <= c; wdata <= d; nack_send <= nk; end
    @(posedge clk) go <= 0;
    @(posedge done);
    case (c)
      0: $display("%8.2f us  START", $realtime / 1000);
      1: $display("%8.2f us  WRITE %h -> %0s", $realtime / 1000, d,
                  nack_rcvd ? "NACK" : "ACK");
      2: $display("%8.2f us  READ  %h <- master answers %0s", $realtime / 1000, rdata,
                  nk ? "NACK" : "ACK");
      3: $display("%8.2f us  STOP", $realtime / 1000);
    endcase
  endtask
  initial begin
    repeat (3) @(posedge clk); rst_n = 1;
    $display("-- write 5A, C3 to registers 10h, 11h of device 50h");
    op(0); op(1, 8'hA0); op(1, 8'h10); op(1, 8'h5A); op(1, 8'hC3); op(3);
    $display("-- random read from 10h: write pointer, repeated START, read 2 bytes");
    op(0); op(1, 8'hA0); op(1, 8'h10); op(0); op(1, 8'hA1);
    op(2, 0, 0); op(2, 0, 1); op(3);
    $display("-- address 51h: nobody answers");
    trace = 1;  op(0); op(1, 8'hA2); op(3);  #5000 trace = 0;
    $display("   SCL %s", w_scl);  $display("   SDA %s", w_sda);
    $finish;
  end
  // one character per 2.5 us (a quarter SCL period) while trace = 1
  bit trace = 0;  string w_scl = "", w_sda = "";
  always #2500 if (trace) begin
    w_scl = {w_scl, scl ? "~" : "_"};  w_sda = {w_sda, sda ? "~" : "_"};
  end
  // measure the stretched low time of SCL
  realtime tfall;
  always @(negedge scl) tfall = $realtime;
  always @(posedge scl) if ($realtime - tfall > 6000)
    $display("           (SCL held low %0.2f us by the slave: clock stretching)",
             ($realtime - tfall) / 1000);
endmodule''',
    'i3c': r'''
// ENTDAA arbitration: each unaddressed target shifts out {PID[47:0], BCR, DCR} MSB first
// in open-drain mode. A target that sends 1 but sees 0 has lost and waits for next round.
module daa_target #(parameter logic [63:0] ID = '0) (
  input  logic       clk, rst_n,
  input  logic       rnd_start,             // controller starts an arbitration round
  input  logic       bit_en,  input logic [5:0] bitn,  input logic sda,
  input  logic       assign_en, input logic [6:0] new_addr,
  output logic       sda_low,               // open-drain drive
  output logic       has_addr, output logic [6:0] dyn_addr
);
  logic lost;
  wire  my_bit = ID[63 - bitn];
  assign sda_low = bit_en && !lost && !has_addr && !my_bit;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin lost <= 0; has_addr <= 0; dyn_addr <= 0; end
    else if (rnd_start) lost <= has_addr;    // addressed targets stay silent
    else if (bit_en && !lost && my_bit && !sda) lost <= 1;   // sent 1, saw 0
    else if (assign_en && !lost && !has_addr) begin has_addr <= 1; dyn_addr <= new_addr; end
endmodule

// T-bit for SDR write data and the parity bit after a DAA address: both are ODD parity
function automatic logic odd_par(input logic [7:0] d);
  return ~^d;                                // makes the count of ones (data + bit) odd
endfunction''',
    'tb_i3c': r'''
module tb;
  logic clk = 0, rst_n = 0;  always #5 clk = ~clk;
  // PID = MIPI mfr ID(15) | type(1) | part ID(16) | instance(4) | extra(12); then BCR, DCR
  localparam logic [63:0] ID_A = {15'h011A, 1'b0, 16'h4A10, 4'h2, 12'h000, 8'h06, 8'h44};
  localparam logic [63:0] ID_B = {15'h011A, 1'b0, 16'h4A10, 4'h1, 12'h000, 8'h06, 8'h44};
  localparam logic [63:0] ID_C = {15'h0105, 1'b0, 16'h7702, 4'h0, 12'h001, 8'h27, 8'h63};
  logic rnd_start = 0, bit_en = 0, assign_en = 0;  logic [5:0] bitn = 0;  logic [6:0] na;
  wire  [2:0] low;  wire [2:0] has;  wire [6:0] da [3];
  wire  sda = ~|low;                          // wired-AND with the pull-up
  daa_target #(ID_A) ta (.clk, .rst_n, .rnd_start, .bit_en, .bitn, .sda, .assign_en,
                         .new_addr(na), .sda_low(low[0]), .has_addr(has[0]), .dyn_addr(da[0]));
  daa_target #(ID_B) tb_ (.clk, .rst_n, .rnd_start, .bit_en, .bitn, .sda, .assign_en,
                         .new_addr(na), .sda_low(low[1]), .has_addr(has[1]), .dyn_addr(da[1]));
  daa_target #(ID_C) tc (.clk, .rst_n, .rnd_start, .bit_en, .bitn, .sda, .assign_en,
                         .new_addr(na), .sda_low(low[2]), .has_addr(has[2]), .dyn_addr(da[2]));
  logic [63:0] seen;  bit fin = 0;
  initial begin
    repeat (2) @(posedge clk); rst_n = 1;
    na = 7'h08;
    for (int r = 0; r < 4 && !fin; r++) begin
      @(posedge clk) rnd_start <= 1;  @(posedge clk) rnd_start <= 0;
      seen = '1;
      for (int b = 0; b < 64; b++) begin    // 64 open-drain bits
        @(posedge clk) begin bit_en <= 1; bitn <= b[5:0]; end
        @(negedge clk) seen[63 - b] = sda;  // controller reads the bus
      end
      @(posedge clk) bit_en <= 0;
      if (seen == '1) begin                // nobody pulled low: no target left
        $display("round %0d: all ones -> no target left, controller ends ENTDAA", r);
        fin = 1;
      end else begin
        @(posedge clk) assign_en <= 1;  @(posedge clk) assign_en <= 0;
        $display("round %0d: PID=%h BCR=%h DCR=%h wins -> dyn addr %h, sent as %b_%b",
                 r, seen[63:16], seen[15:8], seen[7:0], na, na, odd_par({1'b0, na}));
        @(negedge clk) na = na + 1;
      end
    end
    $display("final: A=%h B=%h C=%h", da[0], da[1], da[2]);
    $display("SDR T-bit (odd parity): 00->%b  01->%b  A5->%b  FF->%b",
             odd_par(8'h00), odd_par(8'h01), odd_par(8'hA5), odd_par(8'hFF));
    $finish;
  end
endmodule''',
    'can': r'''
module can_crc15 (                        // serial CRC-15: x^15+x^14+x^10+x^8+x^7+x^4+x^3+1
  input  logic clk, clr, en, din,
  output logic [14:0] crc
);
  wire fb = din ^ crc[14];
  always_ff @(posedge clk)
    if (clr)     crc <= '0;
    else if (en) crc <= {crc[13:0], 1'b0} ^ (fb ? 15'h4599 : 15'h0);
endmodule

module can_stuff (                        // inserts a complement bit after 5 equal bits
  input  logic clk, clr, en, din,
  output logic dout, take                  // take = 0: this cycle is a stuff bit, hold din
);
  logic [2:0] run;  logic last;
  assign take = (run != 5);
  assign dout = take ? din : ~last;
  always_ff @(posedge clk)
    if (clr) begin run <= 0; last <= 1'b1; end
    else if (en) begin
      run  <= (!take || dout != last) ? 3'd1 : run + 1;   // stuff bit starts a new run
      last <= dout;
    end
endmodule

module can_destuff (                      // drops stuff bits; flags 6 equal bits
  input  logic clk, clr, en, din,
  output logic keep, stuff_err            // keep = 0: din was a stuff bit
);
  logic [2:0] run;  logic last;
  assign keep      = (run != 5);
  assign stuff_err = en && (run == 5) && (din == last);
  always_ff @(posedge clk)
    if (clr) begin run <= 0; last <= 1'b1; end
    else if (en) begin
      run  <= (din != last || run == 5) ? 3'd1 : run + 1;
      last <= din;
    end
endmodule''',
    'tb_can': r'''
module tb;
  logic clk = 0;  always #5 clk = ~clk;
  // SOF, ID=123h, RTR, IDE, r0, DLC=2, data 00 FF  (35 bits, sent MSB first)
  localparam logic [34:0] HDR = {1'b0, 11'h123, 3'b000, 4'd2, 8'h00, 8'hFF};
  logic clr = 1, c_en = 0, c_din = 0, s_en = 0, s_din, d_en = 0, d_din;
  logic [14:0] crc;  logic s_out, take, keep, serr;
  logic [49:0] frame;  logic [99:0] stuffed;  logic [49:0] unst;  int ns, nu, errs;
  string s_str = "", m_str = "";
  can_crc15   c (.clk, .clr, .en(c_en), .din(c_din), .crc);
  can_stuff   s (.clk, .clr, .en(s_en), .din(s_din), .dout(s_out), .take);
  can_destuff d (.clk, .clr, .en(d_en), .din(d_din), .keep, .stuff_err(serr));
  initial begin
    @(posedge clk) clr <= 0;
    for (int i = 34; i >= 0; i--) begin @(negedge clk) begin c_en = 1; c_din = HDR[i]; end end
    @(negedge clk) c_en = 0;
    frame = {HDR, crc};
    $display("verilog: CRC-15 = %h", crc);
    // ---- stuff SOF .. CRC sequence ----
    ns = 0;  clr = 1; @(negedge clk) clr = 0;
    for (int i = 49; i >= 0; ) begin
      @(negedge clk) begin s_en = 1; s_din = frame[i]; end
      #1 s_str = {s_str, s_out ? "1" : "0"};  m_str = {m_str, take ? " " : "^"};
      stuffed[99 - ns] = s_out; ns++;
      if (take) i--;
    end
    @(negedge clk) s_en = 0;
    $display("verilog: %0d stuffed bits", ns);
    $display("verilog: %s", s_str);
    $display("         %s  (^ = stuff bit)", m_str);
    // ---- destuff and compare, then corrupt one stuff bit ----
    for (int pass = 0; pass < 2; pass++) begin
      clr = 1; @(negedge clk) clr = 0;  nu = 0;  errs = 0;
      for (int i = 0; i < ns; i++) begin
        @(negedge clk) begin
          d_en = 1;  d_din = stuffed[99 - i];
          if (pass == 1 && i == 17) d_din = ~d_din;       // bit 17 is the first stuff bit
        end
        #1 if (serr) errs++;
        if (keep) begin unst[49 - nu] = d_din; nu++; end
      end
      @(negedge clk) d_en = 0;
      if (pass == 0) $display("destuffed %0d bits, equal to original: %s", nu,
                              unst == frame ? "yes" : "NO");
      else           $display("stuff bit corrupted -> stuff errors detected: %0d", errs);
    end
    $finish;
  end
endmodule''',
    'can_arb': r'''
module can_arb_node (                     // transmits SOF + 11-bit ID + RTR, watches the bus
  input  logic        clk, rst_n, go,  input logic [11:0] id_rtr,   // {ID, RTR}
  input  logic        bus,               // wired-AND of all transmitters (0 = dominant)
  output logic        tx, lost
);
  logic [12:0] sh;  logic active;
  assign tx = (active && !lost) ? sh[12] : 1'b1;      // recessive once it has lost
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin sh <= '1; active <= 0; lost <= 0; end
    else if (go) begin sh <= {1'b0, id_rtr}; active <= 1; lost <= 0; end
    else if (active) begin
      if (!lost && tx && !bus) lost <= 1;  // sent recessive, read dominant: back off
      sh <= {sh[11:0], 1'b1};
    end
endmodule''',
    'tb_can_arb': r'''
module tb;
  logic clk = 0, rst_n = 0, go = 0;  always #5 clk = ~clk;
  logic [11:0] a_id, b_id;  logic ta, tb_, la, lb;
  wire bus = ta & tb_;                   // open-collector transceivers: wired-AND
  can_arb_node na (.clk, .rst_n, .go, .id_rtr(a_id), .bus, .tx(ta),  .lost(la));
  can_arb_node nb (.clk, .rst_n, .go, .id_rtr(b_id), .bus, .tx(tb_), .lost(lb));
  string sa, sb, sbus;
  task automatic run(input logic [11:0] a, input logic [11:0] b);
    a_id = a; b_id = b;  sa = ""; sb = ""; sbus = "";
    @(negedge clk) go = 1;  @(negedge clk) go = 0;
    repeat (13) begin                                // look at each bit mid-period
      sa   = {sa,   ta  ? "1 " : "0 "};  sb = {sb, tb_ ? "1 " : "0 "};
      sbus = {sbus, bus ? "1 " : "0 "};
      @(negedge clk);
    end
    $display("          S 1 9 8 7 6 5 4 3 2 1 0 R");
    $display("          O 0                     T");
    $display("          F                       R");
    $display("node A    %s  ID=%h RTR=%0d %0s", sa,  a[11:1], a[0], la ? "LOST" : "WINS");
    $display("node B    %s  ID=%h RTR=%0d %0s", sb,  b[11:1], b[0], lb ? "LOST" : "WINS");
    $display("bus       %s", sbus);
  endtask
  initial begin
    repeat (2) @(posedge clk); rst_n = 1;
    run({11'h123, 1'b0}, {11'h12B, 1'b0});           // different IDs
    run({11'h123, 1'b0}, {11'h123, 1'b1});           // same ID: data frame vs remote frame
    $finish;
  end
endmodule''',
    'i2s': r'''
// Philips I2S, 64 SCK per frame (32-bit slots), W-bit samples MSB first.
// WS: 0 = left, 1 = right; it changes one SCK before the MSB of the new channel.
module i2s_tx #(parameter int W = 16) (
  input  logic         clk, rst_n,          // clk = 2 x SCK
  input  logic [W-1:0] left, right,
  output logic         load,                // pulse: left/right captured, give next pair
  output logic         sck, ws, sd
);
  logic [5:0] pos;  logic [W-1:0] l_q, r_q;
  wire  [5:0] nxt = pos + 1;
  wire  [4:0] idx = nxt[4:0];               // bit position inside the next slot
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin sck <= 0; pos <= 6'd63; ws <= 0; sd <= 0; load <= 0;
                      l_q <= 0; r_q <= 0; end
    else begin
      sck  <= ~sck;
      load <= 0;
      if (sck) begin                        // falling SCK: transmitter changes outputs
        pos <= nxt;
        if (nxt == 0) begin l_q <= left; r_q <= right; load <= 1; end
        ws  <= (6'(nxt + 1) >= 32);          // leads the slot by one bit
        if (idx < W) sd <= nxt[5] ? r_q[W-1-idx] : ((nxt == 0) ? left[W-1] : l_q[W-1-idx]);
        else         sd <= 1'b0;             // unused slot bits are zero
      end
    end
endmodule

module i2s_rx #(parameter int W = 16) (     // lives in the SCK domain
  input  logic         sck, rst_n, ws, sd,
  output logic         valid, right,        // valid for one SCK: word just completed
  output logic [W-1:0] data
);
  logic ws_d;  logic [5:0] cnt;  logic [W-1:0] sh;
  wire  [W-1:0] sh_n = (cnt < W) ? {sh[W-2:0], sd} : sh;
  always_ff @(posedge sck or negedge rst_n)
    if (!rst_n) begin ws_d <= 0; cnt <= 6'd63; sh <= 0; valid <= 0; data <= 0; right <= 0; end
    else begin
      ws_d  <= ws;
      valid <= 0;
      if (ws != ws_d) begin                 // this is the last bit of the old slot
        if (cnt != 63) begin data <= sh_n; right <= ws_d; valid <= 1; end
        cnt <= 0;
      end else begin
        sh  <= sh_n;
        if (cnt != 63) cnt <= cnt + 1;
      end
    end
endmodule''',
    'tb_i2s': r'''
module pair #(parameter int W = 16) (input logic clk, rst_n);
  logic [W-1:0] L [4], R [4], l, r, rx;  logic load, sck, ws, sd, valid, right;
  int k = 0, rk = 0, errs = 0, words = 0;  string w_ws = "", w_sd = "";
  i2s_tx #(W) tx (.clk, .rst_n, .left(l), .right(r), .load, .sck, .ws, .sd);
  i2s_rx #(W) rxu (.sck, .rst_n, .ws, .sd, .valid, .right, .data(rx));
  initial for (int i = 0; i < 4; i++) begin
    L[i] =  W'(64'hA5C3_F10E_9B27_D4E8 >> (8 * i));
    R[i] = ~W'(64'h1234_5678_9ABC_DEF0 >> (4 * i));
  end
  assign l = L[k % 4];  assign r = R[k % 4];
  always @(posedge clk) if (load) k++;
  always @(posedge sck) if (valid) begin
    // the receiver needs one WS edge to lock, so the first full left word is frame 1
    if (!right && rk == 0) rk = 1;
    if (rk > 0) begin
      if (rx !== (right ? R[rk % 4] : L[rk % 4])) errs++;
      words++;
      if (words <= 2) $display("W=%0d  %s word %h", W, right ? "R" : "L", rx);
      if (right) rk++;
    end
  end
  always @(posedge sck) if (k == 3 && w_ws.len() < 64) begin       // frame 2 as RX sees it
    w_ws = {w_ws, ws ? "1" : "0"};  w_sd = {w_sd, sd ? "1" : "0"};
  end
endmodule

module tb;
  logic clk = 0, rst_n = 0;  always #5 clk = ~clk;
  pair #(16) p16 (.clk, .rst_n);
  pair #(24) p24 (.clk, .rst_n);
  initial begin
    repeat (3) @(posedge clk); rst_n = 1;
    repeat (64 * 2 * 10) @(posedge clk);
    $display("W=16: %0d words checked, %0d errors;  W=24: %0d words checked, %0d errors",
             p16.words, p16.errs, p24.words, p24.errs);
    $display("W=16 frame 2 (L=%h R=%h), one char per SCK rising edge:", p16.L[2], p16.R[2]);
    $display("  WS %s", p16.w_ws);  $display("  SD %s", p16.w_sd);
    $finish;
  end
endmodule''',
    'ow': r'''
// Maxim/Dallas 1-Wire CRC-8: x^8 + x^5 + x^4 + 1, bits processed LSB first
// (the order they appear on the wire), register shifts right, reflected poly 8Ch.
module ow_crc8 (
  input  logic       clk, clr, en, din,
  output logic [7:0] crc
);
  wire fb = din ^ crc[0];
  always_ff @(posedge clk)
    if (clr)     crc <= 8'h00;
    else if (en) crc <= {1'b0, crc[7:1]} ^ (fb ? 8'h8C : 8'h00);
endmodule''',
    'tb_ow': r'''
module tb;
  logic clk = 0, clr = 1, en = 0, din = 0;  logic [7:0] crc;
  always #5 clk = ~clk;
  ow_crc8 u (.clk, .clr, .en, .din, .crc);
  // 64-bit ROM codes; byte 0 (family code) is sent first, byte 7 is the stored CRC.
  // The third code has a corrupted CRC byte (2c instead of 2b).
  logic [63:0] rom [3];
  initial begin
    rom[0] = 64'hA2_000000_01B81C_02;  rom[1] = 64'h30_031691_624CFF_28;
    rom[2] = 64'h2C_000802_0D078A_10;
  end
  task automatic run(input int r, input int nbytes, output logic [7:0] c);
    @(negedge clk) clr = 1;  @(negedge clk) clr = 0;
    for (int b = 0; b < nbytes; b++)
      for (int i = 0; i < 8; i++) begin                 // LSB of each byte first
        @(negedge clk) begin en = 1; din = rom[r][8*b + i]; end
      end
    @(negedge clk) en = 0;  c = crc;
  endtask
  logic [7:0] c7, c8;
  initial begin
    for (int r = 0; r < 3; r++) begin
      run(r, 7, c7);  run(r, 8, c8);
      $display("ROM (wire order) %h %h %h %h %h %h %h | stored %h  crc(7)=%h  crc(8)=%h %0s",
               rom[r][7:0], rom[r][15:8], rom[r][23:16], rom[r][31:24], rom[r][39:32],
               rom[r][47:40], rom[r][55:48], rom[r][63:56], c7, c8, c8 == 0 ? "OK" : "BAD");
    end
    $finish;
  end
endmodule''',
    'py_baud': r'''
# Integer 16550-style divisor vs a divisor with a 4-bit fraction (1/16 steps)
print("f_clk(MHz)   baud    int_div  err_int   frac_div   err_frac")
for fclk in (1.8432e6, 48e6, 50e6):
    for baud in (9600, 115200, 921600, 3000000):
        if baud > fclk / 16:
            continue
        ideal = fclk / (16 * baud)
        di = max(1, round(ideal))
        df = max(1, round(ideal * 16) / 16)
        ei = 100 * (fclk / (16 * di) - baud) / baud
        ef = 100 * (fclk / (16 * df) - baud) / baud
        print("%8.4f  %7d  %7d  %+6.2f%%  %9.4f  %+6.2f%%" % (fclk / 1e6, baud, di, ei, df, ef))''',
    'py_can': r'''
# Python reference: classic CAN base frame, CRC-15 (poly 0x4599) and bit stuffing
def bits(v, n): return [(v >> (n - 1 - i)) & 1 for i in range(n)]
ID, DLC, DATA = 0x123, 2, [0x00, 0xFF]
f = [0] + bits(ID, 11) + [0, 0, 0] + bits(DLC, 4)      # SOF, ID, RTR, IDE, r0, DLC
for d in DATA: f += bits(d, 8)
crc = 0
for b in f:                                             # CRC over SOF .. data field
    fb = b ^ ((crc >> 14) & 1)
    crc = (crc << 1) & 0x7FFF
    if fb: crc ^= 0x4599
f += bits(crc, 15)
out, mark, run, last = [], [], 0, None
for b in f:                                             # stuff SOF .. CRC sequence
    out.append(b); mark.append(' ')
    run = run + 1 if b == last else 1; last = b
    if run == 5:
        out.append(1 - b); mark.append('^'); last = 1 - b; run = 1
print("python: %d unstuffed bits, CRC-15 = %04x, %d stuffed bits (%d stuff bits)"
      % (len(f), crc, len(out), len(out) - len(f)))
print("python: " + "".join(map(str, out)))
# independent check: remainder of (message * x^15) mod generator by long division
m = int("".join(map(str, f[:-15])), 2) << 15
g = 0xC599                                              # x^15 + 0x4599 terms
for s in range(m.bit_length() - 1, 14, -1):
    if (m >> s) & 1: m ^= g << (s - 15)
print("python: long-division remainder = %04x" % m)''',
    'py_ow': r'''
def crc8_maxim(data):                    # reflected x^8+x^5+x^4+1, init 0
    c = 0
    for b in data:
        for _ in range(8):
            mix = (c ^ b) & 1
            c >>= 1
            if mix: c ^= 0x8C
            b >>= 1
    return c
for rom in ([0x02, 0x1C, 0xB8, 0x01, 0x00, 0x00, 0x00],
            [0x28, 0xFF, 0x4C, 0x62, 0x91, 0x16, 0x03],
            [0x10, 0x8A, 0x07, 0x0D, 0x02, 0x08, 0x00]):
    print("python: " + " ".join("%02x" % b for b in rom) + "  crc8 = %02x" % crc8_maxim(rom))''',
    'py_pullup': r'''
# I2C pull-up window (UM10204 method): Rp_max = tr / (0.8473 * Cb),
# Rp_min = (VDD - VOL_max) / IOL. 0.8473 = ln(0.7/0.3): time from 30 % to 70 % VDD.
VDD, VOL = 3.3, 0.4
for mode, tr, iol in (("Sm  100k", 1000e-9, 3e-3), ("Fm  400k", 300e-9, 3e-3),
                      ("Fm+ 1M  ", 120e-9, 20e-3)):
    for cb in (50e-12, 200e-12, 400e-12):
        rmax = tr / (0.8473 * cb)
        rmin = (VDD - VOL) / iol
        ok = "ok" if rmin <= rmax else "no solution with a 3 mA sink"
        print("%s  Cb=%3.0f pF  Rp_min=%5.0f ohm  Rp_max=%6.0f ohm  %s"
              % (mode, cb * 1e12, rmin, rmax, ok))''',
    'py_lin': r'''
# LIN protected identifier and checksums (LIN 2.x / ISO 17987)
def pid(i):
    b = [(i >> k) & 1 for k in range(6)]
    p0 = b[0] ^ b[1] ^ b[2] ^ b[4]
    p1 = 1 - (b[1] ^ b[3] ^ b[4] ^ b[5])
    return i | (p0 << 6) | (p1 << 7)
def checksum(bytes_):                       # 8-bit sum with end-around carry, inverted
    s = 0
    for b in bytes_:
        s += b
        if s > 0xFF: s -= 0xFF
    return (~s) & 0xFF
for i in (0x00, 0x10, 0x3C, 0x3D):
    print("ID %02x -> PID %02x" % (i, pid(i)))
data = [0x4A, 0x55, 0x93, 0xE5]
print("data", " ".join("%02x" % d for d in data))
print("classic  checksum (data only)     = %02x" % checksum(data))
print("enhanced checksum (PID %02x + data) = %02x" % (pid(0x10), checksum([pid(0x10)] + data)))''',
}

OUT = {
    'uart': ['TX baud error  sent  rx_ok  rx_bad  framing_err', '    -6.0 %      64     15      49       49', '    -5.5 %      64     48      16       16', '    -5.0 %      64     64       0        0', '    -4.5 %      64     64       0        0', '    -3.0 %      64     64       0        0', '     0.0 %      64     64       0        0', '     3.0 %      64     64       0        0', '     4.5 %      64     64       0        0', '     5.0 %      64      1      61       54', '     5.5 %      64      0      61       51', '     6.0 %      64      0      61       53'],
    'spi': ['mode 0 (CPOL=0 CPHA=0): M->S a0 got a0 | S->M 5c got 5c  PASS', '   CS_n ~~__________________________________~~', '   SCLK ____~~__~~__~~__~~__~~__~~__~~__~~____', '   MOSI --1111000011110000000000000000000000--', 'mode 1 (CPOL=0 CPHA=1): M->S a1 got a1 | S->M 5d got 5d  PASS', 'mode 2 (CPOL=1 CPHA=0): M->S a2 got a2 | S->M 5e got 5e  PASS', 'mode 3 (CPOL=1 CPHA=1): M->S a3 got a3 | S->M 5f got 5f  PASS', '   CS_n ~~~__________________________________~~', '   SCLK ~~~~~__~~__~~__~~__~~__~~__~~__~~__~~~~', '   MOSI ---0011110000111100000000000011111111--'],
    'qspi': ['round trip  rx_dly  opcode addr    data read          result', '   3.0 ns     0     6b    000100  31383f464d545b62  PASS', '   6.0 ns     0     6b    000100  z31383f464d545b6  FAIL', '   9.0 ns     0     6b    000100  z31383f464d545b6  FAIL', '   3.0 ns     1     6b    000100  31383f464d545b62  PASS', '   6.0 ns     1     6b    000100  31383f464d545b62  PASS', '   9.0 ns     1     6b    000100  31383f464d545b62  PASS', 'SCLK cycles per 8-byte read: 8 cmd + 24 addr + 8 dummy + 16 data = 56'],
    'i2c': ['-- write 5A, C3 to registers 10h, 11h of device 50h', '   10.09 us  START', '  100.49 us  WRITE a0 -> ACK', '  190.89 us  WRITE 10 -> ACK', '  281.29 us  WRITE 5a -> ACK', '  371.69 us  WRITE c3 -> ACK', '  381.77 us  STOP', '-- random read from 10h: write pointer, repeated START, read 2 bytes', '  391.81 us  START', '  482.21 us  WRITE a0 -> ACK', '  572.61 us  WRITE 10 -> ACK', '  582.69 us  START', '  673.09 us  WRITE a1 -> ACK', '           (SCL held low 20.50 us by the slave: clock stretching)', '  778.93 us  READ  5a <- master answers ACK', '  869.33 us  READ  c3 <- master answers NACK', '  879.41 us  STOP', '-- address 51h: nobody answers', '  889.45 us  START', '  979.85 us  WRITE a2 -> NACK', '  989.93 us  STOP', '   SCL ~~~~__~~__~~__~~__~~__~~__~~__~~__~~__~~__~~~~', '   SDA ~~~__~~~~____~~~~____________~~~~____~~~~__~~~'],
    'i3c': ['round 0: PID=020a77020001 BCR=27 DCR=63 wins -> dyn addr 08, sent as 0001000_0', 'round 1: PID=02344a101000 BCR=06 DCR=44 wins -> dyn addr 09, sent as 0001001_1', 'round 2: PID=02344a102000 BCR=06 DCR=44 wins -> dyn addr 0a, sent as 0001010_1', 'round 3: all ones -> no target left, controller ends ENTDAA', 'final: A=0a B=09 C=08', 'SDR T-bit (odd parity): 00->1  01->0  A5->1  FF->1'],
    'can': ['verilog: CRC-15 = 63e6', 'verilog: 55 stuffed bits', 'verilog: 0001001000110000011000001000011111011111000011111000110', '                          ^      ^         ^     ^        ^       (^ = stuff bit)', 'destuffed 50 bits, equal to original: yes', 'stuff bit corrupted -> stuff errors detected: 1'],
    'can_arb': ['          S 1 9 8 7 6 5 4 3 2 1 0 R', '          O 0                     T', '          F                       R', 'node A    0 0 0 1 0 0 1 0 0 0 1 1 0   ID=123 RTR=0 WINS', 'node B    0 0 0 1 0 0 1 0 1 1 1 1 1   ID=12b RTR=0 LOST', 'bus       0 0 0 1 0 0 1 0 0 0 1 1 0', '          S 1 9 8 7 6 5 4 3 2 1 0 R', '          O 0                     T', '          F                       R', 'node A    0 0 0 1 0 0 1 0 0 0 1 1 0   ID=123 RTR=0 WINS', 'node B    0 0 0 1 0 0 1 0 0 0 1 1 1   ID=123 RTR=1 LOST', 'bus       0 0 0 1 0 0 1 0 0 0 1 1 0'],
    'i2s': ['W=24  L word 9b27d4', 'W=16  L word 27d4', 'W=24  R word 543210', 'W=16  R word 3210', 'W=16: 17 words checked, 0 errors;  W=24: 17 words checked, 0 errors', 'W=16 frame 2 (L=9b27 R=4321), one char per SCK rising edge:', '  WS 0000000000000000000000000000000111111111111111111111111111111110', '  SD 1001101100100111000000000000000001000011001000010000000000000000'],
    'ow': ['ROM (wire order) 02 1c b8 01 00 00 00 | stored a2  crc(7)=a2  crc(8)=00 OK', 'ROM (wire order) 28 ff 4c 62 91 16 03 | stored 30  crc(7)=30  crc(8)=00 OK', 'ROM (wire order) 10 8a 07 0d 02 08 00 | stored 2c  crc(7)=2b  crc(8)=83 BAD'],
    'py_baud': ['f_clk(MHz)   baud    int_div  err_int   frac_div   err_frac', '  1.8432     9600       12   +0.00%    12.0000   +0.00%', '  1.8432   115200        1   +0.00%     1.0000   +0.00%', ' 48.0000     9600      312   +0.16%   312.5000   +0.00%', ' 48.0000   115200       26   +0.16%    26.0625   -0.08%', ' 48.0000   921600        3   +8.51%     3.2500   +0.16%', ' 48.0000  3000000        1   +0.00%     1.0000   +0.00%', ' 50.0000     9600      326   -0.15%   325.5000   +0.01%', ' 50.0000   115200       27   +0.47%    27.1250   +0.01%', ' 50.0000   921600        3  +13.03%     3.3750   +0.47%', ' 50.0000  3000000        1   +4.17%     1.0625   -1.96%'],
    'py_can': ['python: 50 unstuffed bits, CRC-15 = 63e6, 55 stuffed bits (5 stuff bits)', 'python: 0001001000110000011000001000011111011111000011111000110', 'python: long-division remainder = 63e6'],
    'py_ow': ['python: 02 1c b8 01 00 00 00  crc8 = a2', 'python: 28 ff 4c 62 91 16 03  crc8 = 30', 'python: 10 8a 07 0d 02 08 00  crc8 = 2b'],
    'py_pullup': ['Sm  100k  Cb= 50 pF  Rp_min=  967 ohm  Rp_max= 23604 ohm  ok', 'Sm  100k  Cb=200 pF  Rp_min=  967 ohm  Rp_max=  5901 ohm  ok', 'Sm  100k  Cb=400 pF  Rp_min=  967 ohm  Rp_max=  2951 ohm  ok', 'Fm  400k  Cb= 50 pF  Rp_min=  967 ohm  Rp_max=  7081 ohm  ok', 'Fm  400k  Cb=200 pF  Rp_min=  967 ohm  Rp_max=  1770 ohm  ok', 'Fm  400k  Cb=400 pF  Rp_min=  967 ohm  Rp_max=   885 ohm  no solution with a 3 mA sink', 'Fm+ 1M    Cb= 50 pF  Rp_min=  145 ohm  Rp_max=  2833 ohm  ok', 'Fm+ 1M    Cb=200 pF  Rp_min=  145 ohm  Rp_max=   708 ohm  ok', 'Fm+ 1M    Cb=400 pF  Rp_min=  145 ohm  Rp_max=   354 ohm  ok'],
    'py_lin': ['ID 00 -> PID 80', 'ID 10 -> PID 50', 'ID 3c -> PID 3c', 'ID 3d -> PID 7d', 'data 4a 55 93 e5', 'classic  checksum (data only)     = e6', 'enhanced checksum (PID 50 + data) = 96'],
}


def _v(name, caption=None):
    """Show a verified Verilog/SystemVerilog source (or Python model) from SRC."""
    code(SRC[name].split("\n"), caption)


def _o(name, caption=None):
    """Show the real output captured for a testbench or Python model."""
    out(OUT[name], caption)


# =============================================================================
#                 PART III - LOW-SPEED PERIPHERAL PROTOCOLS
# =============================================================================
def part3():
    part("Low-Speed Peripheral Protocols",
         "Every SoC, from a 50-cent microcontroller to a data-centre CPU, is "
         "ringed with slow serial buses: a UART console, SPI boot flash, I2C "
         "sensors and power regulators, I3C on modern phones and DDR5 DIMMs, "
         "CAN and LIN in cars, I2S to the audio codec, MDIO to the Ethernet "
         "PHY. They run at kilobits to a few hundred megabits per second, "
         "but they are where bring-up starts, where many field bugs live, "
         "and where interview questions love to probe. This part takes each "
         "one down to the bit: frame formats, timing, electrical behaviour, "
         "error handling, controller RTL that was actually simulated, and "
         "the integration traps that catch real chips.")
    _ch11()
    _ch12()
    _ch13()
    _ch14()
    _ch15()
    _ch16()


# ---------------------------------------------------------------- Ch 11 ---
def _ch11():
    chapter("UART, RS-232 and RS-485", newpage=False)
    p("The Universal Asynchronous Receiver/Transmitter is the oldest serial "
      "link still found on every SoC. It has no clock wire: transmitter "
      "and receiver each run from their own clock and merely **agree** on a "
      "bit rate. Every character re-synchronizes the receiver with its "
      "start-bit edge, so the two clocks only need to stay aligned for "
      "about ten bit times. That single idea - resynchronize on every "
      "character, sample in the middle of each bit - explains the frame "
      "format, the oversampling receiver, the clock-tolerance budget and "
      "nearly every UART bug. The UART itself is only the logic layer; the "
      "voltages on the wire are set by separate standards (TTL/CMOS levels "
      "on the board, RS-232 to a PC, RS-422/RS-485 across a factory).")
    tbl(["Where you find it", "Typical use", "Who owns what"],
        [["Debug console", "Boot ROM messages, bootloader, Linux console, "
          "firmware logs; often the first thing alive after reset",
          "RTL: UART IP + pad mux; FW: divisor, driver; board: level shifter"],
         ["Companion chips", "Bluetooth/Wi-Fi combo (HCI UART with RTS/CTS "
          "at 3-4 Mbit/s), GNSS receivers, cellular modems",
          "RTL: flow control, FIFOs, DMA; DV: long-burst and flow tests"],
         ["Industrial / automotive", "RS-485 Modbus, DMX512, LIN (a UART "
          "with a special header, Chapter 15)", "Board: transceiver and "
          "termination; RTL: driver-enable timing, break detection"],
         ["Manufacturing / security", "Test-mode access, secure-boot "
          "recovery console", "Security: console must be lockable "
          "(fuses, debug authentication)"]],
        widths=[20, 46, 34], bold_first=True)

    h2("The asynchronous frame")
    p("The line **idles high** (logic 1, historically called **mark**). A "
      "character is sent as:")
    bul(["one **start bit** (logic 0, **space**) - its falling edge is the "
         "timing reference for the entire character;",
         "**5 to 9 data bits, least-significant bit first** (8 is by far the "
         "most common; 9-bit mode is used for multiprocessor addressing, the "
         "ninth bit marking an address byte);",
         "an optional **parity bit**: even, odd, or the rarely used "
         "mark (always 1) / space (always 0) parity;",
         "**1, 1.5 or 2 stop bits** (logic 1). The stop bit guarantees an "
         "idle-high period so the next start bit produces a falling edge.",
         ])
    diagram([
        "   idle start   D0    D1    D2    D3    D4    D5    D6    D7    P    stop  idle",
        "  ~~~~~~|     |~~~~~|     |~~~~~~~~~~~|           |~~~~~|           |~~~~~~~~~~~",
        "        |_____|     |_____|           |___________|     |___________|",
        "        ^ falling edge = time 0 (bit times: start 0-1, D0 1-2, ... stop 10-11)",
        "  receiver samples at 0.5 (confirm start), 1.5, 2.5 ... 9.5 (parity), 10.5 (stop)",
        "",
        "  character 0x4D = 0100_1101b is sent D0..D7 = 1,0,1,1,0,0,1,0 ; even parity P = 0",
    ], "An 8E1 frame (8 data bits, even parity, 1 stop): 11 bit times per "
       "character. 8N1 (no parity) is 10 bit times, so 115200 baud carries "
       "at most 11520 bytes/s.")
    p("The shorthand **8N1**, **7E1**, **8E1**, **8N2** gives data bits, "
      "parity (None/Even/Odd/Mark/Space) and stop bits. Efficiency is "
      "8/10 = 80 % for 8N1 and 8/11 = 73 % for 8E1. **Baud** is symbols per "
      "second; on a UART one symbol is one bit, so baud = bit/s here, but "
      "the distinction matters once multi-level line codes appear "
      "(Chapter 2).")
    box("note", "Why LSB first?",
        "The earliest teleprinters and UART chips shifted characters out of "
        "a shift register toward bit 0, and every later standard kept it. "
        "Almost everything else in this book (SPI, I2C, CAN, Ethernet "
        "headers aside) is MSB first, so LSB-first order is a classic source "
        "of bit-reversed data when a UART frame is decoded by hand or with "
        "a logic analyser configured for the wrong order.")

    h2("Baud-rate generation and divisor error")
    p("A UART needs a tick at a multiple of the baud rate - normally 16x, "
      "sometimes 8x or 4x at high rates. The classic 16550 divides its "
      "input clock by a 16-bit integer divisor (DLL/DLM registers):")
    eq(["divisor = round( f_clk / (16 x baud) )",
        "actual  = f_clk / (16 x divisor)",
        "error % = 100 x (actual - baud) / baud"],
       "Integer divisor arithmetic of a 16x-oversampling UART.")
    p("The 1.8432 MHz crystal (and its multiples 3.6864, 7.3728, 14.7456, "
      "18.432 MHz) exists precisely because 1.8432 MHz / 16 = 115200 divides "
      "evenly into every standard rate. An SoC rarely has such a clock; it "
      "has 24, 48, 50 or 100 MHz, and the integer divisor error can be "
      "large at high baud rates. Modern UARTs add a **fractional divisor** "
      "(a 4-bit or larger fraction, dithered by an accumulator) or a "
      "fully programmable **NCO** (numerically controlled oscillator), as "
      "the RTL below does. The Python model shows why:")
    _v("py_baud", "Divisor error for integer and 1/16-fractional dividers "
       "(Python 3).")
    _o("py_baud")
    p("With a 50 MHz clock an integer divisor gives +13 % at 921600 baud - "
      "a guaranteed failure - while a 1/16 fraction brings it to 0.47 %. "
      "Note also 3 Mbaud from 50 MHz: the ideal divisor is 1.04, so even "
      "the fraction leaves -1.96 %, which eats most of the budget computed "
      "next. That is why high-speed UARTs support 8x or 4x oversampling "
      "(more divisor resolution per bit) or a dedicated baud clock.")

    h2("Receiver: 16x oversampling and mid-bit sampling")
    p("The receiver knows nothing about the transmitter's clock. It "
      "oversamples the (synchronized) RX pin at 16 ticks per bit and runs "
      "this algorithm:")
    bul(["**Idle**: wait for a 1 -> 0 transition (the start edge). It is "
         "observed with up to one tick (1/16 bit) of uncertainty.",
         "**Confirm start**: count 8 ticks to the middle of the start bit "
         "and check the line is still 0. If it is 1, it was a glitch "
         "(false start) - go back to idle. This is a free noise filter.",
         "**Data**: every 16 ticks thereafter the counter is at the middle "
         "of the next bit; sample it. Better receivers take three samples "
         "(ticks 7, 8, 9) and use a **majority vote**, and flag noise if "
         "they disagree.",
         "**Parity / stop**: sample parity and stop the same way. A 0 where "
         "the stop bit should be is a **framing error**.",
         "Return to idle **at the middle of the stop bit** - not the end - "
         "so that the next start edge, which may come as early as the end "
         "of the stop bit from a slightly fast transmitter, is not missed."])
    diagram([
        "  RX (after 2-FF sync)  ~~~~~~\\_______________ start ______________/~~~~ D0 ~~~~",
        "  16x ticks              | | | | | | | | | | | | | | | | | | | | | | | | | |",
        "  counter                0 1 2 3 4 5 6 7 8                 0 1 2 ... 15",
        "                                       ^ mid-start: still 0?    ^ mid-D0: sample",
        "  edge detected up to 1 tick late -> every sample point may be up to 1/16 bit late",
    ], "The 16x receiver. After confirming the start bit, every subsequent "
       "sample is exactly 16 ticks later.")

    h2("The clock tolerance budget")
    p("Because the receiver resynchronizes only at the start edge, the "
      "timing error accumulates across the character. The last sample - "
      "the middle of the stop bit - is 9.5 bit times after the edge for "
      "8N1 (10.5 for 8E1 or 9-bit data). For that sample to land inside "
      "the correct bit, the accumulated drift must stay below half a bit, "
      "minus the edge-detection uncertainty:")
    eq(["|df/f| x 9.5 bits  <  0.5 bit - 1/16 bit (edge quantization, 16x)",
        "|df/f|  <  (0.5 - 0.0625) / 9.5  =  4.6 %     (8N1, total of both ends)",
        "|df/f|  <  (0.5 - 0.0625) / 10.5 =  4.2 %     (8E1 / 9-bit data)"],
       "Total allowable baud mismatch between transmitter and receiver.")
    p("That total is shared by **both** ends, and it must also absorb "
      "asymmetric rise/fall times, transceiver skew and noise, which shift "
      "the effective edge. The practical engineering rule is therefore "
      "**about 2 % per side, preferably under 1-1.5 %** - a crystal-based "
      "clock (tens of ppm) is effortless, an on-chip RC oscillator "
      "(often +/-1 % to +/-5 % uncalibrated) is not. This is the single "
      "number to remember: when a customer reports 'garbled characters at "
      "high baud rates', compute the divisor error first.")
    p("The testbench below proves the budget with real RTL. The transmitter "
      "and receiver each have their own NCO baud generator; the receiver is "
      "exact (115200 baud at 100 MHz) and the transmitter's increment is "
      "offset in 0.5 % steps. 64 back-to-back characters are sent - the "
      "worst case, because there is no idle time to absorb drift - "
      "alternating random data with 0x00 (whose stop bit follows eight "
      "zeros).")
    _v("uart", "An NCO baud-tick generator plus 8N1 transmitter and 16x "
       "oversampling receiver with false-start rejection and framing-error "
       "detection. The receiver samples once per bit at tick 7/15 (a "
       "production design would take a 3-sample majority vote and add "
       "parity and break detection).")
    _v("tb_uart", "Testbench: sweep the transmitter's baud error and "
       "count good characters, bad characters and framing errors.")
    _o("uart", "Real Icarus Verilog output. Error-free from -5.0 % to "
       "+4.5 %; at +5 % (transmitter fast) almost everything is lost, at "
       "-5.5 % (transmitter slow) framing errors appear.")
    p("The measured window, about -5.0 % to +4.5 % with zero errors, sits "
      "right around the 4.6 % theory; it is slightly asymmetric because "
      "the 2-flop synchronizer and the tick phase delay every sample point "
      "by a fraction of a tick, which helps a slow transmitter and hurts a "
      "fast one. On a real board that margin is consumed by the other end's "
      "error and by edge distortion - never design to the simulated edge.")
    box("warn", "PITFALL: the fast transmitter and the missing start edge",
        "When the transmitter is fast, its next start bit begins before the "
        "receiver has finished the stop bit. A receiver that waits until the "
        "**end** of the stop bit before looking for the next falling edge "
        "will miss it (or sample it late) on back-to-back characters. Leave "
        "the stop state at mid-bit, as the RTL above does. Similarly, a "
        "transmitter should honour the programmed stop-bit count exactly - "
        "some FIFO-less designs 'save a cycle' and send short stop bits.")

    h2("Line conditions: errors and break")
    tbl(["Condition", "Detected when", "Typical cause", "Reported as"],
        [["**Framing error**", "Stop bit sampled as 0", "Baud mismatch, "
          "noise, wrong frame format, a break", "LSR.FE, per character in "
          "the RX FIFO"],
         ["**Parity error**", "Received parity does not match",
          "Noise, wrong parity setting", "LSR.PE, per character"],
         ["**Overrun error**", "A character completes while the receive "
          "buffer/FIFO is full; it (or the oldest) is lost", "Software or "
          "DMA too slow; no flow control", "LSR.OE"],
         ["**Break**", "Line held at 0 for longer than a full character "
          "(start + data + parity + stop)", "Deliberate signal (SysRq, "
          "LIN header, bootloader entry) or a disconnected RS-232 cable",
          "LSR.BI with a 0x00 character"],
         ["**Noise / glitch**", "Majority-vote samples disagree, or start "
          "bit not confirmed", "EMI, slow edges", "Some UARTs flag it; "
          "others silently filter"],
         ["**RX timeout**", "Characters in the FIFO but no new one for "
          "about 4 character times", "End of a message shorter than the "
          "FIFO trigger level", "Timeout interrupt (not an error)"]],
        widths=[16, 28, 30, 26], bold_first=True)
    p("A **break** is sent by forcing TX low (LCR bit 6 on a 16550) for at "
      "least one character time, usually longer. Receivers detect it as a "
      "0x00 character with a framing error and all-zero bits, and then "
      "must wait for the line to return high before looking for a new "
      "start bit - otherwise the long low is decoded as a stream of "
      "garbage characters.")

    h2("Hardware flow control: RTS/CTS")
    p("A UART has no acknowledgement, so the receiver throttles the sender "
      "with two extra wires. Each side drives **RTS** (request to send - "
      "in modern use 'ready to receive') and reads the other's RTS on its "
      "**CTS** input. The transmitter only starts a new character while "
      "CTS is asserted (active low on the wire).")
    diagram([
        "     SoC UART                         BT module",
        "   +-----------+  TX  ------------>  RX  +-----------+",
        "   |  TX FIFO  |  RX  <------------  TX  |           |",
        "   |  RX FIFO  |  RTS ------------>  CTS |  (stops   |",
        "   |           |  CTS <------------  RTS |  sending) |",
        "   +-----------+                         +-----------+",
        "",
        "   RX FIFO level >= threshold  ->  deassert RTS  (\"stop\")",
        "   RX FIFO level <  threshold  ->  assert RTS    (\"go\")",
        "   remote may still send 1-2 characters (+ its own FIFO pipeline) after RTS drops",
    ], "RTS/CTS crossed between two UARTs (null-modem wiring).")
    bul(["**Auto flow control** (16750/16950-class UARTs and most SoC "
         "UARTs): hardware drives RTS from the RX FIFO level and gates the "
         "TX engine with CTS, with no software in the loop. Software-driven "
         "RTS cannot react within one character at 3 Mbit/s (a character "
         "is 3.3 us).",
         "Set the RTS threshold with **headroom**: the remote will finish "
         "the character in flight and may already have committed the next "
         "one. Leave at least 2-4 free FIFO entries.",
         "CTS is asynchronous - synchronize it, and sample it only at a "
         "character boundary; stopping mid-character corrupts the frame.",
         "**Software flow control** (XON = 0x11, XOFF = 0x13) sends control "
         "characters in-band; it is slow and cannot carry binary data "
         "without escaping.",
         "RS-232 also defines DTR/DSR/DCD/RI modem-control lines; on SoCs "
         "they are usually GPIOs or absent."])

    h2("The 16550 register model")
    p("The National Semiconductor 16550 (and its 8250 ancestor) defined a "
      "register interface that is still emulated by countless SoC UARTs, "
      "virtual machines and the Linux `8250` driver. Eight byte-wide "
      "registers occupy eight addresses (often at a 4-byte stride on a "
      "32-bit APB bus); the **DLAB** bit in LCR re-maps offsets 0 and 1 to "
      "the divisor latch.")
    tbl(["Off", "Read", "Write", "Key bits"],
        [["0", "RBR receive buffer (DLAB=0) / DLL", "THR transmit holding "
          "(DLAB=0) / DLL", "DLL/DLM = 16-bit divisor, low/high byte"],
         ["1", "IER / DLM (DLAB=1)", "IER / DLM", "IER: RX data, THR empty, "
          "line status, modem status interrupt enables"],
         ["2", "IIR interrupt identification", "FCR FIFO control",
          "FCR: FIFO enable, reset RX/TX FIFO, RX trigger 1/4/8/14; IIR: "
          "pending interrupt by priority"],
         ["3", "LCR line control", "LCR", "Word length 5-8, stop bits, "
          "parity enable/even/stick, break (bit 6), DLAB (bit 7)"],
         ["4", "MCR modem control", "MCR", "DTR, RTS, OUT1/OUT2, loopback "
          "(bit 4); auto-flow enable on 16750-class"],
         ["5", "LSR line status", "-", "DR, OE, PE, FE, BI, THRE, TEMT, "
          "RX FIFO error (bit 7)"],
         ["6", "MSR modem status", "-", "CTS, DSR, RI, DCD and their "
          "delta (changed) bits"],
         ["7", "SCR scratch", "SCR", "No function; used to probe presence"]],
        widths=[6, 26, 24, 44])
    p("IIR reports the highest-priority pending interrupt: receiver line "
      "status (errors/break) first, then received data available (FIFO at "
      "trigger level), then **character timeout**, then THR empty, then "
      "modem status. Two behaviours trip up RTL re-implementations: reading "
      "IIR clears a pending THR-empty interrupt, and reading LSR clears the "
      "error bits - so these reads have **side effects** that a register "
      "model and a DV scoreboard must replicate exactly (and that a "
      "debugger reading registers can disturb).")
    box("expert", "Interview insight: why a TEMT bit as well as THRE?",
        "THRE says the transmit holding register (or FIFO) is empty - "
        "software can write more. TEMT says the **shift register** is empty "
        "too, i.e. the last stop bit has left the pin. Anything that must "
        "wait for the line to be truly idle - turning an RS-485 driver off, "
        "changing baud rate, entering sleep - must wait for TEMT, not THRE. "
        "Waiting for THRE and then disabling the RS-485 driver cuts off the "
        "last character, a bug found in many drivers.")

    h2("Electrical layers: TTL, RS-232, RS-422 and RS-485")
    p("The SoC pad speaks CMOS levels (idle high = 1.8 V or 3.3 V). "
      "Everything else is a transceiver on the board:")
    tbl(["Standard", "Signalling", "Logic 1 / 0", "Topology", "Rate x distance "
         "(typical)"],
        [["TTL/CMOS UART", "Single-ended, ground referenced", "VDD / 0 V",
          "Point-to-point, same board", "Mbit/s over cm"],
         ["**RS-232** (TIA-232)", "Single-ended, **inverted**, bipolar",
          "Mark (1) = -3 to -15 V; space (0) = +3 to +15 V; drivers "
          "typically +/-5 to +/-12 V", "Point-to-point", "Specified to 20 "
          "kbit/s over ~15 m; in practice 115-1000 kbit/s over short cables"],
         ["**RS-422** (TIA-422)", "Differential, one driver", "A-B > +200 "
          "mV = 1, < -200 mV = 0", "1 driver, up to 10 receivers",
          "10 Mbit/s over ~12 m; ~100 kbit/s over 1200 m"],
         ["**RS-485** (TIA-485)", "Differential, **multi-driver**, tri-state",
          "Same thresholds; driver >= 1.5 V into 54 ohm", "Multi-drop bus, "
          "32 unit loads (more with 1/4-1/8 UL receivers)", "Same "
          "rate-distance family as RS-422; common-mode -7 to +12 V"]],
        widths=[15, 20, 26, 18, 21], bold_first=True)
    diagram([
        "     node 1           node 2                    node N",
        "    +------+         +------+                  +------+",
        "    | DE RE|         | DE RE|                  | DE RE|     DE = driver enable",
        "    +-+--+-+         +-+--+-+                  +-+--+-+     RE_n = receiver enable",
        "      |  |             |  |                      |  |",
        "  +---+--+-------------+--+----------------------+--+---+   A (non-inverting)",
        " 120                                                   120  twisted pair,",
        " ohm                                                   ohm  terminated at",
        "  +---------------------------------------------------+---+  both ends   B",
        "  failsafe bias: pull A up / B down (e.g. ~500-750 ohm) so an idle bus reads 1",
    ], "RS-485 two-wire half-duplex bus. Only one node drives at a time; "
       "termination matches the ~120 ohm cable impedance.")
    p("RS-485 two-wire is **half duplex**: every node's transmitter shares "
      "the pair, so the UART must switch its transceiver's **driver enable "
      "(DE)** on only while it transmits. The timing is critical:")
    bul(["Assert DE a little before the start bit (a 'pre-delay' of a "
         "fraction of a bit) so the driver's output has settled.",
         "Deassert DE only after the **last stop bit has left** (TEMT, not "
         "THRE), optionally plus a post-delay; too early truncates the "
         "stop bit, too late collides with a fast responder.",
         "Many SoC UARTs have an **RS-485 mode** that drives DE from the "
         "transmitter FSM in hardware with programmable assertion/"
         "de-assertion times - far more reliable than toggling a GPIO from "
         "an interrupt handler.",
         "When the node's own receiver is enabled while it transmits it "
         "hears its own echo; either disable RE or discard the echo (it "
         "is also a handy collision check).",
         "An idle, undriven bus floats near 0 V differential, which is "
         "inside the +/-200 mV undefined band: **failsafe biasing** "
         "resistors or failsafe receivers make idle read as 1."])

    h2("Modbus RTU: a protocol on top of RS-485")
    p("Modbus RTU is the lingua franca of industrial RS-485. A master polls "
      "slaves (addresses 1-247; 0 is broadcast) with frames delimited by "
      "**silence**: a gap of at least **3.5 character times** starts a new "
      "frame, and a gap of more than 1.5 character times inside a frame "
      "is an error. The frame is `address, function code, data, CRC-16` "
      "(the Modbus CRC uses polynomial 0x8005 in reflected form, 0xA001, "
      "initial value 0xFFFF, sent low byte first). Standard characters are "
      "11 bits (8E1, or 8N2 when parity is off). Common function codes: 03 "
      "read holding registers, 04 read input registers, 06 write single "
      "register, 16 (0x10) write multiple registers; an exception response "
      "sets bit 7 of the function code.")
    box("tip", "Hardware help for Modbus",
        "The 3.5-character silence is awkward in software at high baud rates "
        "(at 115200 baud it is only ~330 us; the Modbus spec fixes it at "
        "1.75 ms above 19200 baud for that reason). SoC UARTs aimed at "
        "industrial use provide a programmable **receiver idle timeout** "
        "interrupt and sometimes an address-match mode, so software sees "
        "whole frames. That is the same RX-timeout logic as the 16550's "
        "character timeout, with a programmable length.")

    h2("Auto-baud detection")
    p("A receiver that does not know the rate can measure it. The simplest "
      "method times the **start bit** (the first low period) of a known "
      "character with a fast counter; better methods time several edges "
      "of a known pattern. The pattern must begin with a single 0 bit "
      "followed by a 1: 0x55 ('U') alternates perfectly (`0 1 0 1 0 1 0 1 "
      "0 1` on the wire), and the 'A'/'a' of the Hayes 'AT' command also "
      "starts with a single-bit low. LIN's sync byte is exactly 0x55 for "
      "this reason (Chapter 15). In RTL, auto-baud is a counter that runs "
      "from the falling edge to the rising edge, divides by the number of "
      "bits measured, and loads the result into the NCO or divisor - with "
      "a guard against glitches and a timeout.")

    h2("Building and verifying a UART in an SoC")
    diagram([
        "  APB  +-------------+   +----------+   +----------+       +--------+",
        "  <--->|  CSR block  |-->| TX FIFO  |-->| TX FSM   |--TXD->|  pad   |",
        "       | (16550-like)|   +----------+   | + parity |       +--------+",
        "  IRQ<-|  interrupt  |   +----------+   +----------+       +--------+",
        "       |  logic      |<--| RX FIFO  |<--| RX FSM   |<-RXD--|  pad   |",
        "  DMA<-|  req/ack    |   | + error  |   | 16x, vote|  2FF  +--------+",
        "       +-------------+   |  flags   |   +----------+  sync",
        "              |          +----------+        ^",
        "              +--> baud NCO / divisor -------+----> RTS/CTS, RS-485 DE",
    ], "Block diagram of a typical SoC UART.")
    bul(["**Clocking**: the UART usually has its own functional clock "
         "(for an exact baud reference) separate from the APB bus clock; "
         "the CSR block then crosses domains (Chapter 4). Keeping the "
         "baud clock alive in low-power modes allows wake-on-RX.",
         "**FIFOs** store per-character error flags alongside the data so "
         "software knows which byte had the parity error.",
         "**DMA**: RX request at the FIFO trigger level, plus the "
         "character-timeout interrupt to flush short messages - the classic "
         "bug is a DMA RX path that stalls with the last few bytes of a "
         "message stuck below the trigger level.",
         "**DV**: a UART VIP (a behavioural transmitter/receiver with "
         "programmable baud error, glitch and break injection), a scoreboard "
         "that models the 16550 side effects, coverage on every "
         "data-bits/parity/stop combination and on each error type, and "
         "**loopback mode** tests (MCR bit 4) that firmware reuses on "
         "silicon.",
         "**Silicon bring-up**: a UART is often driven by the boot ROM "
         "before PLLs are configured, so its divisor must be correct for "
         "the reset-default reference clock (for example 24 MHz or 38.4 "
         "MHz) - check the ROM's baud table against the actual crystal."])
    checklist("UART integration checklist", [
        "Divisor/NCO error computed for every supported baud rate and every "
        "reference clock the product uses (<= ~1.5 %).",
        "RX pin 2-FF synchronized; start confirmed at mid-bit; stop state "
        "exits at mid-stop-bit.",
        "Break detection waits for the line to return high.",
        "TEMT (not THRE) used for RS-485 DE and for baud-rate changes.",
        "RTS threshold leaves headroom; CTS sampled only between characters.",
        "RX timeout interrupt works with DMA; per-character error flags "
        "stored in the FIFO.",
        "Pad has a pull-up on RX so an unconnected console does not produce "
        "break storms; console can be disabled for secure products."])

    h2("Summary")
    bul(["A UART frame is idle-high, start bit (0), 5-9 data bits LSB first, "
         "optional parity, 1-2 stop bits (1); every character resynchronizes "
         "the receiver on its start edge.",
         "Receivers oversample (usually 16x), confirm the start bit at "
         "mid-bit, then sample every 16 ticks; the last sample is 9.5 bits "
         "(8N1) after the edge.",
         "Total baud mismatch must stay below about 4.6 % (8N1, 16x); budget "
         "about 2 % per side. The simulated RTL worked from -5.0 % to +4.5 % "
         "and failed beyond.",
         "Integer divisors give large errors at high baud rates on "
         "non-UART-friendly clocks; use fractional dividers or an NCO.",
         "Errors: framing, parity, overrun, break; plus the RX character "
         "timeout that makes FIFOs and DMA usable.",
         "RTS/CTS provides back-pressure; RS-232 is inverted bipolar "
         "single-ended; RS-422/485 are differential, and RS-485 is a "
         "half-duplex multi-drop bus that needs precise driver-enable "
         "timing and failsafe biasing."])

    h2("Exercises")
    bul(["A UART runs from a 26 MHz clock. Compute the integer divisor and "
         "the error for 115200 and 460800 baud with 16x oversampling. Would "
         "8x oversampling help at 460800?",
         "Derive the maximum tolerable total baud mismatch for 7E2 frames "
         "with 8x oversampling. Which term grew and which shrank?",
         "Modify the `uart_rx` in this chapter to take a 3-sample majority "
         "vote at ticks 7, 8 and 9 and to report a noise flag. Re-run the "
         "baud sweep; does the window change?",
         "Design the RS-485 DE control for a UART: DE rises one-half bit "
         "before the start bit and falls one bit after TEMT. Draw the FSM "
         "and list the corner cases (back-to-back writes, FIFO refilled "
         "during the post-delay).",
         "A customer sees one corrupted byte every few thousand when a "
         "Bluetooth module streams at 3 Mbaud with RTS/CTS enabled. List "
         "three possible root causes and how you would distinguish them "
         "on silicon.",
         "Write the Modbus RTU CRC-16 in Python and compute it for the "
         "request `01 03 00 00 00 0A` (read 10 holding registers from slave "
         "1). Which byte is transmitted first?"], ordered=True)


# ---------------------------------------------------------------- Ch 12 ---
def _ch12():
    chapter("SPI, Quad/Octal SPI and xSPI")
    p("The Serial Peripheral Interface is the opposite of the UART: it "
      "carries its own clock, has no framing, no addressing, no "
      "acknowledgement and no formal standard - just a controller that "
      "toggles a clock and two shift registers that exchange bits. That "
      "simplicity lets it scale from a 1 MHz ADC link to a 200 MHz "
      "double-data-rate octal flash that an application processor boots "
      "and executes from. This chapter starts with the four-wire bus and "
      "its four clock modes, then follows the flash market's evolution: "
      "Dual and Quad I/O, QPI, Octal DDR with a data strobe (JEDEC xSPI) "
      "and HyperBus, and the execute-in-place controllers that make serial "
      "flash look like memory.")
    tbl(["Where you find it", "Examples"],
        [["Boot and code storage", "SPI NOR / Quad / Octal flash holding the "
          "boot loader, firmware or the whole MCU program (XIP)"],
         ["Data converters and sensors", "ADCs, DACs, IMUs, touch "
          "controllers - streams with tight timing, often 10-50 MHz"],
         ["Displays and radios", "Small LCD/OLED panels, Wi-Fi/BLE and "
          "sub-GHz radio chips, Ethernet controllers"],
         ["Inside the SoC ecosystem", "PMIC configuration, secure elements, "
          "TPMs (TPM over SPI), FPGA configuration, DDR5-era sideband "
          "components use I3C instead (Chapter 14)"]],
        widths=[28, 72], bold_first=True)

    h2("Four wires, two shift registers")
    p("SPI signals (the industry has moved from master/slave to "
      "controller/peripheral naming; both appear in datasheets):")
    tbl(["Signal", "Also called", "Driven by", "Function"],
        [["SCLK", "SCK, CLK", "Controller", "Serial clock; only toggles "
          "during a transfer"],
         ["MOSI", "SDO (at controller), SDI (at peripheral), PICO, COPI",
          "Controller", "Data from controller to peripheral"],
         ["MISO", "SDI (at controller), SDO (at peripheral), POCI, CIPO",
          "Selected peripheral", "Data to the controller; tri-stated when "
          "the peripheral is not selected"],
         ["CS_n", "SS_n, CE_n, nCS", "Controller", "Active-low chip select, "
          "one per peripheral; frames the transaction"]],
        widths=[12, 34, 18, 36], bold_first=True)
    diagram([
        "        controller                                 peripheral",
        "   +---------------------+                  +---------------------+",
        "   |  7 6 5 4 3 2 1 0    |---- MOSI ------->|  7 6 5 4 3 2 1 0    |",
        "   |  shift register  <--|<--- MISO --------|  shift register     |",
        "   |                     |---- SCLK ------->|                     |",
        "   |                     |---- CS_n ------->|                     |",
        "   +---------------------+                  +---------------------+",
        "   after 8 clocks the two registers have swapped contents",
    ], "SPI is an exchange: every clock moves one bit each way, so reading "
       "requires clocking out (dummy) bits and writing always receives bits.")
    p("SPI is inherently **full duplex**, but most protocols built on it use "
      "it half-duplex in practice: a command goes out, then data comes "
      "back while the controller sends don't-care bits. Word length is "
      "whatever the peripheral expects (8, 12, 16, 24 or 32 bits); CS_n "
      "delimits the transaction and, for many devices, the falling edge of "
      "CS_n resets the peripheral's bit counter - which is why SPI is "
      "fairly robust to a missed clock: the next CS_n cycle resynchronizes.")

    h2("CPOL, CPHA and the four modes")
    p("Two configuration bits define the clock: **CPOL** is the idle level "
      "of SCLK and **CPHA** selects whether data is sampled on the first "
      "(leading) or second (trailing) edge of each clock period. Both "
      "ends must agree; the mode is a property of the peripheral's "
      "datasheet.")
    tbl(["Mode", "CPOL", "CPHA", "SCLK idle", "Sample on", "Shift out on",
         "Common for"],
        [["0", "0", "0", "low", "rising (leading)", "falling; first bit "
          "at CS_n fall", "Most flash, most peripherals"],
         ["1", "0", "1", "low", "falling (trailing)", "rising", "Some ADCs "
          "and sensors"],
         ["2", "1", "0", "high", "falling (leading)", "rising; first bit "
          "at CS_n fall", "Rare"],
         ["3", "1", "1", "high", "rising (trailing)", "falling", "Flash "
          "(modes 0 and 3 both supported), SD in SPI mode"]],
        widths=[7, 7, 7, 10, 18, 26, 25])
    diagram([
        "  CS_n  ~~~\\__________________________________________________/~~~",
        "",
        "  mode 0 SCLK ______/~~~\\___/~~~\\___/~~~\\___ ... ___/~~~\\_________",
        "  mode 1 SCLK ______/~~~\\___/~~~\\___/~~~\\___ ... ___/~~~\\_________",
        "  mode 2 SCLK ~~~~~~\\___/~~~\\___/~~~\\___/~~~ ... ~~~\\___/~~~~~~~~~",
        "  mode 3 SCLK ~~~~~~\\___/~~~\\___/~~~\\___/~~~ ... ~~~\\___/~~~~~~~~~",
        "",
        "  CPHA=0 data  -<  b7  X  b6  X  b5  X ... X  b0  >---------      first bit set up",
        "                    ^ sample   ^         ^           (leading edges)  before 1st edge",
        "  CPHA=1 data  -------<  b7  X  b6  X  b5 ... X  b0  >------      first bit driven",
        "                          ^ sample  ^          ^     (trailing edges) on 1st edge",
    ], "The four SPI modes. CPOL only inverts the clock; CPHA shifts the "
       "data by half a clock. Modes 0 and 3 sample on rising edges, which "
       "is why flash devices can support both.")
    box("intuit", "One rule for all four modes",
        "Treat `sclk XOR CPOL` as the internal clock. Then there are only "
        "two cases: CPHA=0 - data must be ready **before** the first edge "
        "and is sampled on every leading edge; CPHA=1 - data is driven on "
        "every leading edge and sampled on every trailing edge. The RTL "
        "below and its slave model are written exactly this way.")
    _v("spi", "An SPI controller supporting all four modes. A half-period "
       "counter generates edges; the edge type (leading/trailing) and CPHA "
       "decide whether each edge samples MISO or shifts MOSI.")
    _v("tb_spi", "Testbench with a behavioural peripheral that works in "
       "any mode, plus a one-character-per-clock waveform printer.")
    _o("spi", "Real Icarus Verilog output: every mode exchanges a byte in "
       "both directions correctly. In mode 0 MOSI carries bit 7 of A0h "
       "before the first rising edge; in mode 3 the controller drives "
       "bit 7 of A3h at the first (falling) edge.")
    box("warn", "PITFALL: mode mismatch that almost works",
        "Using mode 0 against a mode-1 device shifts all data by one bit: "
        "reads come back doubled or halved and the top bit is lost - which "
        "looks like a data or register-map bug rather than a clocking one. "
        "When SPI data is 'off by a factor of two', check CPHA first.")

    h2("Multiple peripherals: chip selects and daisy chains")
    diagram([
        "  independent chip selects                 daisy chain (shared CS_n)",
        "  ctrl SCLK ---+------+------+              ctrl MOSI -> [dev A] -> [dev B] -> [dev C] -+",
        "       MOSI ---+------+------+                                                        |",
        "       MISO <--+------+------+  (tri-state) ctrl MISO <-----------------------------------+",
        "       CS0_n -> dev A                       all devices share SCLK and one CS_n;",
        "       CS1_n ----------> dev B              3 devices x 8 bits = 24 clocks per update",
        "       CS2_n -----------------> dev C",
    ], "Two ways to connect several peripherals.")
    bul(["**One CS_n per device** is the norm: simple, any device can be "
         "addressed alone, but costs a pin per device and the MISO line "
         "is shared, so every unselected device must tri-state its output.",
         "**Daisy chain**: each device's output feeds the next device's "
         "input, forming one long shift register (common for LED drivers, "
         "shift registers, some ADC/DAC arrays and JTAG-like chains). One "
         "CS_n, but every update must shift the whole chain.",
         "A CS_n decoder or a GPIO can extend chip selects, but hardware "
         "CS timing (setup before the first edge, hold after the last, "
         "minimum high time between transactions) is then software's "
         "problem - a frequent source of flaky peripherals."])

    h2("How fast can SPI go? The round-trip limit")
    p("Writes are easy: the controller launches both SCLK and MOSI, so "
      "they travel together and skew is small. **Reads are the problem.** "
      "In mode 0 the peripheral launches MISO on the falling SCLK edge and "
      "the controller samples it on the next rising edge - half a period "
      "later. But the falling edge seen by the peripheral is late (output "
      "pad and board delay), the peripheral adds its clock-to-output time "
      "(tV / tCLQV in flash datasheets, typically 5-8 ns), and MISO then "
      "travels back through the board and the input pad:")
    eq(["t_rt = t_pad_out(SCLK) + t_board + t_CO(peripheral) + t_board + t_pad_in(MISO)",
        "requirement:  t_rt + t_setup  <  T_SCLK / 2",
        "e.g. t_rt = 12 ns, t_setup = 2 ns  ->  T_SCLK > 28 ns  ->  f_SCLK < ~35 MHz"],
       "The read round-trip budget for sampling on the opposite edge.")
    p("The standard fixes, in increasing sophistication:")
    bul(["**Delayed (late) sampling**: sample MISO one or more system-clock "
         "cycles after the nominal edge, or on the **next** falling edge "
         "(a full period after launch). Controllers expose this as a "
         "'sample delay' or 'RX capture edge' register.",
         "**Feedback / loopback clock**: route SCLK out through a pad and "
         "back in (or use a dummy pad), so the capture clock experiences "
         "the same pad delay as the data.",
         "**Programmable delay lines (DLL)** that place the capture point "
         "in the middle of the data eye; the delay is trained at boot by "
         "reading a known pattern.",
         "**A data strobe (DQS)** driven by the memory alongside the data, "
         "as in Octal xSPI and HyperBus: the strobe has the same round trip "
         "as the data, so the controller captures with it (source "
         "synchronous, like DDR DRAM)."])
    p("The QSPI testbench below reproduces the problem and the first fix. "
      "SCLK runs at 100 MHz (10 ns period, from a 200 MHz controller "
      "clock), and the flash model's total round-trip delay is 3, 6 or "
      "9 ns. With `rx_dly = 0` the controller captures at the rising edge "
      "5 ns after launch; with `rx_dly = 1` it captures one controller "
      "clock later, at the falling edge 10 ns after launch.")

    h2("SPI NOR flash: the command set")
    p("Serial NOR flash is the dominant SPI device, and its command set is "
      "a de-facto standard shared by most vendors (Winbond, Macronix, "
      "Micron, Infineon, GigaDevice, ISSI...), with the **SFDP** table "
      "(Serial Flash Discoverable Parameters, JEDEC JESD216) letting a "
      "controller discover sizes, erase types and fast-read opcodes at "
      "runtime. A transaction is `CS_n low, opcode, [address], [mode/dummy "
      "clocks], [data], CS_n high`.")
    tbl(["Opcode", "Command", "Format", "Notes"],
        [["03h", "READ", "cmd + 3-byte addr + data", "No dummy cycles; "
          "limited to a lower clock (often ~50 MHz)"],
         ["0Bh", "FAST READ", "cmd + addr + 8 dummy clocks + data", "Dummy "
          "clocks give the array access time; full speed"],
         ["3Bh / BBh", "Dual Output / Dual I/O read", "1-1-2 / 1-2-2",
          "Two data lines"],
         ["6Bh / EBh", "Quad Output / Quad I/O read", "1-1-4 / 1-4-4",
          "Four data lines; EBh sends the address on 4 lines too"],
         ["06h / 04h", "WREN / WRDI", "cmd only", "Write enable latch "
          "must be set before every program/erase"],
         ["02h", "PAGE PROGRAM", "cmd + addr + 1-256 bytes", "Within one "
          "256-byte page; wraps at the page end"],
         ["20h / 52h / D8h", "Erase 4 KB / 32 KB / 64 KB", "cmd + addr",
          "Milliseconds to hundreds of ms"],
         ["60h or C7h", "Chip erase", "cmd", "Seconds to minutes"],
         ["05h", "READ STATUS REGISTER", "cmd + data", "Bit 0 = WIP/BUSY, "
          "bit 1 = WEL; poll until WIP = 0"],
         ["9Fh", "READ JEDEC ID", "cmd + 3 bytes", "Manufacturer, type, "
          "capacity"],
         ["5Ah", "READ SFDP", "cmd + addr + 8 dummy + data", "Parameter "
          "tables (JESD216)"],
         ["66h + 99h", "Reset enable + reset", "cmd, cmd", "Return to a "
          "known state (e.g. after a warm reset mid-command)"],
         ["B7h / E9h", "Enter / exit 4-byte address mode", "cmd", "For "
          "devices > 16 MB; dedicated 4-byte opcodes (13h, 0Ch, 12h, "
          "21h, DCh...) avoid mode state"]],
        widths=[14, 25, 28, 33])
    diagram([
        "  CS_n  ~~\\________________________________________________________________/~~",
        "  SCLK  ___/~\\_/~\\_ ... _/~\\_/~\\_ ... _/~\\_/~\\_/~\\_ ... _/~\\_/~\\_/~\\_/~\\_ ...",
        "  IO0   --< 0 1 1 0 1 0 1 1 >< A23 ... A0 >------ dummy -----< 4 >< 0 >< 4 >< 0 >",
        "  IO1   ------------------------------------------------------< 5 >< 1 >< 5 >< 1 >",
        "  IO2   ------------------------------------------------------< 6 >< 2 >< 6 >< 2 >",
        "  IO3   ------------------------------------------------------< 7 >< 3 >< 7 >< 3 >",
        "           opcode 6Bh (8)      address (24)    8 clocks      byte 0    byte 1",
        "  IO3..0 carry bits 7..4 of each byte, then bits 3..0 (high nibble first)",
    ], "Fast Read Quad Output (6Bh, 1-1-4): command and address on IO0, "
       "then two clocks per byte on four lines. IO2/IO3 are WP_n/HOLD_n "
       "in single-bit modes, which is why the Quad Enable (QE) status bit "
       "must be set first.")
    p("A controller for this sequence is a small FSM - command/address "
      "shifting on IO0, a dummy counter, then nibble capture - plus the "
      "tri-state control that hands IO0 from the controller to the flash "
      "after the address. The version below also has the programmable "
      "capture delay discussed above.")
    _v("qspi", "A Fast Read Quad Output (6Bh) controller: SCLK = clk/2, "
       "launch on the falling edge, capture on the rising edge or one "
       "controller clock later (`rx_dly`).")
    _v("tb_qspi", "Testbench: a flash model that decodes the opcode and "
       "address and returns data after 8 dummy clocks with a configurable "
       "round-trip delay; the read is repeated for three delays with and "
       "without late sampling.")
    _o("qspi", "Real Icarus Verilog output. Nominal-edge capture fails "
       "once the round trip exceeds half an SCLK period (5 ns): the first "
       "nibble is captured as z and the data slips by one nibble. "
       "Capturing one clock later passes for all three delays.")
    p("Note the throughput arithmetic in the last line: the 8-byte quad "
      "read costs 56 SCLK cycles, of which only 16 move data. The same read "
      "with 03h would cost 8 + 24 + 64 = 96 cycles, with 1-4-4 (EBh) it "
      "would be 8 + 6 + (mode+dummy, typically 6) + 16 = 36. For short, "
      "random reads - exactly what an instruction cache miss produces - "
      "**command and address overhead dominate**, which is what drove "
      "the industry to 4-4-4 and 8-8-8 modes and continuous-read tricks.")

    h2("Dual, Quad and QPI modes")
    p("Multi-line modes are written **x-y-z**: the number of lines used for "
      "command, address and data.")
    tbl(["Mode", "Command", "Address", "Data", "Example opcode", "Remarks"],
        [["1-1-1", "1", "1", "1", "03h, 0Bh", "Classic SPI"],
         ["1-1-2", "1", "1", "2", "3Bh", "Dual output"],
         ["1-2-2", "1", "2", "2", "BBh", "Dual I/O"],
         ["1-1-4", "1", "1", "4", "6Bh", "Quad output"],
         ["1-4-4", "1", "4", "4", "EBh", "Quad I/O; with 'mode bits' "
          "(continuous read) the next read skips the opcode"],
         ["4-4-4", "4", "4", "4", "EBh in QPI", "**QPI**: entered with a "
          "vendor-specific command (for example 38h or 35h); everything "
          "on 4 lines"],
         ["1S-8S-8S / 8S-8S-8S", "8", "8", "8", "vendor", "Octal SDR"],
         ["8D-8D-8D", "8 (DDR)", "8 (DDR)", "8 (DDR)", "vendor/xSPI",
          "Octal DDR with DQS: 2 bytes per clock"]],
        widths=[15, 10, 10, 10, 18, 37])
    box("warn", "PITFALL: mode state that survives your reset",
        "QPI mode, 4-byte address mode, continuous-read (XIP) mode and "
        "volatile dummy-cycle settings live **inside the flash** and survive "
        "an SoC reset that does not power-cycle the flash. The boot ROM then "
        "sends a 1-1-1 03h read to a device that expects 4-4-4, reads "
        "garbage and bricks the board after a watchdog or warm reset. "
        "Robust designs route the SoC reset to the flash RESET_n pin, or "
        "have the boot ROM issue the reset sequence (66h/99h, sent in "
        "every possible mode) before the first read.")

    h2("Octal SPI, xSPI (JESD251) and HyperBus")
    p("For execute-in-place application processors and automotive "
      "cluster displays, quad SPI ran out of bandwidth. Two related "
      "solutions appeared, both with eight data lines, double data rate "
      "and a strobe for read capture:")
    tbl(["", "Octal xSPI (JEDEC JESD251)", "HyperBus (Infineon/Cypress)"],
        [["Data", "DQ[7:0], SDR or DDR (8D-8D-8D)", "DQ[7:0], DDR"],
         ["Clock", "SCLK (optionally differential)", "CK/CK_n (differential "
          "at 1.8 V)"],
         ["Strobe", "DQS - driven by the memory on reads", "RWDS - read "
          "strobe on reads, write mask / latency indicator otherwise"],
         ["Header", "Opcode (often 2 bytes in DDR: code + inverse) + 4-byte "
          "address + latency", "48-bit command-address (CA) word"],
         ["Typical peak", "200 MHz DDR = 400 MB/s", "200 MHz DDR = 400 MB/s"
          " (HyperBus); 16-bit HyperBus variants exist"],
         ["Devices", "Octal NOR flash, some PSRAM", "HyperFlash (NOR), "
          "HyperRAM (self-refresh DRAM)"]],
        widths=[14, 43, 43], bold_first=True)
    p("JESD251 standardized the Octal/xSPI electrical interface, command "
      "structure and profiles (profile 1.0 is the command-based SPI "
      "evolution; profile 2.0 is HyperBus-like), and JESD251-1 adds a "
      "4-line variant. The controller side looks much like a small DDR "
      "memory controller: a DQS-based capture path with a delay line, "
      "DQS preamble handling, variable latency, and training at boot.")
    diagram([
        "  CS_n  ~~\\_____________________________________________________________",
        "  SCLK  ____/~~~\\___/~~~\\___/~~~\\___/~~~\\___/ .. \\___/~~~\\___/~~~\\___/~~~",
        "  DQ    --<C0><C1><A3><A2><A1><A0>--- latency (dummy) ---<D0><D1><D2><D3><D4><D5>",
        "  DQS   ---------------------------------------------\\___/~~~\\___/~~~\\___/~~",
        "        opcode+inv  4-byte addr        N clocks            data: 2 bytes / clock",
    ], "Octal DDR (8D-8D-8D) read: two bytes per SCLK cycle, and the memory "
       "drives DQS edge-aligned with the data; the controller delays DQS by "
       "about a quarter period (DLL) to capture in the middle of each "
       "byte.")

    h2("Execute in place (XIP) controllers")
    p("An XIP controller maps the flash into the processor's address space: "
      "an AXI or AHB read to, say, 0x6000_0000 + offset becomes a flash read "
      "command with that offset. It is one of the most performance-critical "
      "peripherals in a microcontroller or cluster SoC.")
    diagram([
        "   CPU / I-cache --AXI/AHB--> +---------------------------------------------+",
        "                              | XIP controller                              |",
        "                              |  address remap + region decode              |",
        "                              |  prefetch buffer / small cache (lines)      |",
        "                              |  optional on-the-fly decryption (AES-CTR)   |",
        "                              |  command sequencer (LUT of opcode/phases)   |",
        "   APB (config, indirect ---> |  indirect mode: program/erase via FIFO      |",
        "        program/erase)        |  PHY: DDR I/O, DLL, DQS capture, IO muxing  |",
        "                              +---------------------------------------------+",
        "                                   | SCLK, CS_n, DQ[7:0], DQS",
    ], "Anatomy of a serial-flash XIP controller.")
    bul(["**Sequence LUT**: firmware programs the opcode, address width, "
         "dummy count, lane count and DDR/SDR for each phase, so one "
         "controller supports every vendor's flash.",
         "**Continuous read / mode bits**: after the first 1-4-4 or 8D read, "
         "the flash stays in read mode and subsequent reads send only the "
         "address, saving the opcode.",
         "**Prefetch and wrap reads**: fetch a whole cache line, critical "
         "word first, using the flash's wrap-around burst mode.",
         "**Writes** are not memory-mapped on NOR (program/erase takes "
         "milliseconds and needs WREN); software uses an indirect mode. "
         "While an erase runs, XIP reads of the same device stall or "
         "fault - code that erases flash must run from RAM.",
         "**On-the-fly decryption** (AES in counter mode keyed per region) "
         "protects code at rest; the counter is derived from the address "
         "so random access works."])
    box("expert", "Interview insight: why XIP performance is about latency, "
        "not bandwidth",
        "A 200 MHz Octal DDR flash streams 400 MB/s, but a random 32-byte "
        "cache-line read still pays CS_n high time + opcode + address + "
        "latency (often 10-20 clocks) before the first byte - on the order "
        "of 100-150 ns, comparable to DRAM. XIP-heavy systems therefore "
        "live or die by the I-cache hit rate, prefetching and placing "
        "hot code in on-chip SRAM.")

    h2("Verification and integration notes")
    bul(["**VIP**: a flash model (vendors ship Verilog models for their "
         "parts) is the gold reference; also test against a generic SPI VIP "
         "in all four modes with random word lengths and CS_n timing.",
         "**Timing sign-off**: SPI I/O constraints use a generated clock on "
         "the SCLK output pin, with MOSI as output delay and MISO as "
         "input delay relative to it; for DDR/DQS paths the constraints "
         "resemble a DDR PHY's (Chapter 20). Many SPI read failures on "
         "silicon are simply missing or wrong I/O constraints.",
         "**Boot ROM**: the SPI/QSPI boot path is usually hard-coded in ROM "
         "at a conservative clock and 1-1-1 mode, then the second stage "
         "switches to quad/octal after reading SFDP. The ROM must survive "
         "every flash state (see the mode-state pitfall).",
         "**Pads**: IO2/IO3 double as WP_n/HOLD_n - pull-ups are required, "
         "and pad slew/drive strength directly affects signal integrity at "
         "100+ MHz.",
         "**Ownership**: RTL owns the controller and sequencer; the PHY/IO "
         "team owns the DLL and pads; firmware owns the LUT, SFDP parsing "
         "and flash-state recovery; board designers own trace lengths."])

    h2("Summary")
    bul(["SPI is a clocked exchange of two shift registers framed by CS_n; "
         "there is no addressing, ACK, flow control or error detection at "
         "the bus level.",
         "CPOL sets the SCLK idle level and CPHA chooses leading- or "
         "trailing-edge sampling; modes 0 and 3 (sampling on rising edges) "
         "are the most common. The RTL in this chapter handles all four.",
         "Read speed is limited by the round trip SCLK-out -> peripheral "
         "tCO -> MISO-in; late sampling, feedback clocks, DLLs and data "
         "strobes extend it (the simulation failed at 6 ns round trip with "
         "nominal capture and passed with one clock of capture delay).",
         "SPI NOR flash commands: 03h/0Bh reads, 3Bh/BBh/6Bh/EBh multi-I/O "
         "reads, 06h WREN, 02h page program, 20h/52h/D8h erases, 05h status "
         "(WIP), 9Fh ID, 5Ah SFDP.",
         "x-y-z notation gives the lanes for command, address and data; QPI "
         "is 4-4-4, Octal DDR is 8D-8D-8D with DQS; xSPI (JESD251) and "
         "HyperBus reach about 400 MB/s.",
         "XIP controllers turn flash into memory: sequence LUTs, continuous "
         "read, prefetch, decryption, and careful handling of flash "
         "internal mode state across resets."])

    h2("Exercises")
    bul(["A peripheral samples on the falling edge and changes data on the "
         "rising edge, with SCLK idle low. Which mode is it? Draw the first "
         "two bits.",
         "Pad delays are 3 ns out and 2.5 ns in, board flight time is 1 ns "
         "each way, the flash tCLQV is 6 ns and the controller needs 1.5 ns "
         "setup. What is the highest SCLK for mode-0 nominal sampling? With "
         "sampling moved a full SCLK period after launch?",
         "Count SCLK cycles for a 32-byte cache-line fill using 03h, 0Bh, "
         "6Bh, EBh (with 2 mode + 4 dummy clocks) and 8D-8D-8D (2-byte "
         "opcode, 4-byte address, 16 latency clocks). At 100 MHz SDR / "
         "DDR, what fraction of each is data?",
         "Extend `qspi_rd` to the 1-4-4 EBh command: the address and mode "
         "bits go out on four lines. What changes in the IO tri-state "
         "control?",
         "Write the recovery sequence a boot ROM should send to a flash that "
         "may be in QPI, 4-byte or continuous-read mode before issuing 9Fh.",
         "Three 12-bit DACs are daisy-chained. How many clocks per update? "
         "How would you update just one DAC?"], ordered=True)


# ---------------------------------------------------------------- Ch 13 ---
def _ch13():
    chapter("I2C, SMBus and PMBus")
    p("I2C (Inter-Integrated Circuit), created by Philips in 1982 and now "
      "specified in NXP's UM10204, connects dozens of low-speed devices "
      "with just two wires, and does it with **addressing, "
      "acknowledgement, multi-master arbitration and flow control** "
      "(clock stretching) - all by exploiting one electrical trick: "
      "**open-drain outputs with pull-up resistors**. SMBus (System "
      "Management Bus) is a stricter profile of I2C for PC and server "
      "management, and PMBus layers a power-supply command set on top of "
      "SMBus. On a typical SoC board the I2C buses reach the PMIC and "
      "voltage regulators, temperature sensors, EEPROMs, camera sensors "
      "(control path), touch and audio codecs, battery gauges, HDMI DDC, "
      "and DIMM SPD EEPROMs.")

    h2("Open drain and the wired-AND bus")
    p("Neither SCL nor SDA is ever driven high. Each device can only pull "
      "a line **low** (open-drain NMOS) or let go; a **pull-up resistor** "
      "returns the line high. The line is therefore the logical AND of all "
      "devices' outputs: any device writing 0 wins.")
    diagram([
        "        VDD                     VDD",
        "         |                       |",
        "        [Rp]                    [Rp]",
        "         |                       |",
        "  SDA ---+-----+--------+--------+----- ...   line = AND of all outputs",
        "               |        |",
        "            +--+--+  +--+--+",
        "   out=0 -> |NMOS |  |NMOS | <- out=1 (off)    0 dominates: any device",
        "   (on)     +--+--+  +--+--+                   can pull low, none drives high",
        "               |        |",
        "              GND      GND        Cb = total bus capacitance (pins + wiring)",
    ], "The wired-AND I2C bus. The rising edge is an RC charge through Rp "
       "into Cb, which is what limits speed.")
    p("Three features fall directly out of wired-AND: the **ACK** (a "
      "receiver pulls SDA low while the transmitter releases it), "
      "**clock stretching** (a slow slave holds SCL low and the master "
      "waits) and **arbitration** (two masters talking at once detect the "
      "collision without damaging anything). In RTL, an I2C pin is "
      "modelled as an output-enable that pulls low: `assign sda = sda_oe ? "
      "1'b0 : 1'bz;` with a `pullup` on the net in simulation and an "
      "open-drain pad on silicon.")

    h2("START, STOP and the bit rules")
    p("Normally SDA may change only while SCL is **low**, and is stable "
      "while SCL is high. Two exceptions are the bus's framing signals:")
    bul(["**START (S)**: SDA falls while SCL is high. The bus is busy from "
         "here.",
         "**STOP (P)**: SDA rises while SCL is high. The bus is free after "
         "tBUF.",
         "**Repeated START (Sr)**: a START without a preceding STOP; it "
         "keeps the bus while changing direction or target, which is how a "
         "'write register pointer then read' is done atomically."])
    diagram([
        "        S    A6   A5   A4   A3   A2   A1   A0   R/W  ACK  D7  ...  D0  ACK   P",
        " SCL ~~~~~\\__/~~\\__/~~\\__/~~\\__/~~\\__/~~\\__/~~\\__/~~\\__/~~\\__/~~\\ .. /~~\\__/~~\\__/~~~~",
        " SDA ~~~\\____X====X====X====X====X====X====X====X____X====X ..  ===X____X_____/~~~",
        "        ^ START: SDA falls, SCL high         ^ slave pulls  ^ data         ^ STOP:",
        "                                               SDA low=ACK                   SDA rises,",
        "                                                                             SCL high",
    ], "An I2C write: START, 7-bit address MSB first, R/W = 0, ACK from the "
       "slave, data bytes each followed by ACK, STOP. Every byte is 9 clocks.")

    h2("Addressing, ACK/NACK and transactions")
    p("The first byte after START is the **7-bit address** plus the R/W "
      "bit (0 = write, 1 = read), so device 0x50 appears on the wire as "
      "0xA0 (write) or 0xA1 (read) - a permanent source of confusion "
      "between 7-bit and 8-bit address conventions in datasheets and "
      "driver APIs. The ninth clock of every byte is the **acknowledge**: "
      "the receiver pulls SDA low (ACK) or leaves it high (NACK).")
    tbl(["NACK means...", "Situation"],
        [["No device has this address", "After the address byte: absent, "
          "unpowered, or busy device (EEPROMs NACK during their internal "
          "write cycle - 'ACK polling')"],
         ["The receiver cannot accept more", "Slave rejects a data byte "
          "(invalid register, buffer full)"],
         ["The master wants no more data", "On a **read**, the master "
          "NACKs the last byte so the slave releases SDA and the master can "
          "generate STOP or Sr"]],
        widths=[32, 68], bold_first=True)
    tbl(["Address (7-bit)", "R/W", "Meaning"],
        [["0000 000", "0", "General call (e.g. 0x06 = reset and "
          "re-read address pins)"],
         ["0000 000", "1", "START byte (for slow, polling receivers)"],
         ["0000 001", "x", "Reserved for CBUS"],
         ["0000 010", "x", "Reserved for a different bus format"],
         ["0000 011", "x", "Reserved for future use"],
         ["0000 1xx", "x", "Hs-mode master code"],
         ["1111 1xx", "1/0", "Device ID"],
         ["1111 0xx", "x", "10-bit slave addressing (first byte)"]],
        widths=[20, 10, 70], caption="Reserved 7-bit addresses (UM10204). "
        "Usable addresses are 0x08-0x77.")
    p("**10-bit addressing** sends `11110 A9 A8 R/W` followed by the "
      "lower eight address bits as a second byte (each ACKed). For a "
      "10-bit read, the master writes both address bytes, then sends Sr "
      "and only the first byte again with R/W = 1. It is rarely used in "
      "practice.")
    diagram([
        "  write N bytes:  S | ADR,W | A | reg | A | d0 | A | d1 | A | ... | P",
        "  random read:    S | ADR,W | A | reg | A | Sr | ADR,R | A | d0 | A | d1 | N | P",
        "  current read:   S | ADR,R | A | d0 | A | ... | dn | N | P",
        "                  (master drives S, Sr, address, reg, write data, final N, P;",
        "                   slave drives A after address/writes and the read data)",
    ], "The three transaction shapes every I2C driver implements. A = ACK, "
       "N = NACK. Register-based devices auto-increment their pointer.")

    h2("Clock stretching and arbitration")
    p("SCL is also wired-AND. After driving SCL low, a master releases it "
      "and must then **wait until SCL actually reads high** before timing "
      "the high period. A slave that needs time (to fetch data, finish an "
      "ADC conversion, or because its firmware is servicing an interrupt) "
      "simply holds SCL low - **clock stretching**. Masters with multiple "
      "devices also synchronize their clocks this way: the low period is "
      "set by the slowest device, the high period by the fastest.")
    p("**Arbitration**: two masters may start at the same time. Each "
      "compares what it sends with what it reads on SDA while SCL is "
      "high. A master that sends 1 (releases) but reads 0 has lost: it "
      "stops driving immediately and becomes a receiver; the winner's "
      "message is uncorrupted. The lowest address (more leading zeros) "
      "wins. The same principle is used by CAN (Chapter 15) and I3C "
      "dynamic address assignment (Chapter 14).")
    box("warn", "PITFALL: masters that ignore SCL",
        "A bit-banged or simplistic master that times SCL purely from its "
        "own counter, without reading SCL back, breaks with any stretching "
        "slave: it shortens the high period or misses the ACK. Many "
        "microcontroller peripherals (and some I2C slaves implemented in "
        "firmware) stretch, so a master must always synchronize on the "
        "actual SCL level. Conversely, an SoC's **slave** controller should "
        "stretch whenever software has not yet supplied read data rather "
        "than sending stale bytes.")

    h2("An I2C master in RTL, against an open-drain slave")
    p("A practical master is split into a **bit controller** (generates "
      "START, STOP, and one data bit as four quarter-periods of SCL) and a "
      "**byte controller** (sequences 8 data bits + ACK). The version below "
      "combines them into one FSM driven by byte commands: START (also used "
      "for Sr), WRITE, READ (with ACK or NACK) and STOP. Pins are pure "
      "open-drain enables; SCL and SDA inputs are synchronized, and "
      "quarter 2 (SCL released) does not advance until SCL really is high "
      "- that is the clock-stretching support.")
    diagram([
        "                q0          q1          q2          q3",
        "  data bit:  SCL low,     release     SCL high:   pull SCL",
        "             set SDA      SCL (rise)  wait for    low (fall)",
        "                                      SCL=1, then",
        "                                      sample SDA",
        "  START:     release SDA  release SCL pull SDA    pull SCL",
        "  STOP:      SDA, SCL low release SCL release SDA done",
    ], "Quarter-period phases of the bit controller.")
    _v("i2c", "Byte-command I2C master (open-drain pins, input "
       "synchronizers, clock-stretching aware).")
    _v("tb_i2c", "Testbench: the bus is two `wire`s with `pullup`s; the "
       "slave (address 50h, 256 registers with an auto-incrementing "
       "pointer) is behavioural, stretches SCL for 20 us before its first "
       "read byte, and the third transaction addresses a device that does "
       "not exist.")
    _o("i2c", "Real Icarus Verilog output at 100 kHz (50 MHz clock, QTR = "
       "125): register write, random read with repeated START and clock "
       "stretching, and a NACKed address. The waveform is the NACK "
       "transaction sampled every quarter period: START, A2h = 1010 0010, "
       "SDA left high in the ninth clock (NACK), STOP.")
    p("Each byte takes 90.4 us: 9 SCL periods of 10 us plus synchronizer "
      "latency - which is why 100 kHz I2C moves at most about 11 kB/s. The "
      "stretched byte took 20.5 us longer, and the master's quarter-2 wait "
      "absorbed it without any special case.")

    h2("Speed modes, rise time and pull-up sizing")
    tbl(["Mode", "Max rate", "Bus cap. max", "tr max", "Drivers",
         "Notes"],
        [["Standard (Sm)", "100 kbit/s", "400 pF", "1000 ns", "open drain",
          "Original mode"],
         ["Fast (Fm)", "400 kbit/s", "400 pF", "300 ns", "open drain",
          "Most common today; 50 ns spike filter"],
         ["Fast-mode Plus (Fm+)", "1 Mbit/s", "550 pF", "120 ns", "open "
          "drain, 20 mA sink", "Stronger drivers allow lower Rp"],
         ["High-speed (Hs)", "3.4 Mbit/s", "100 pF (400 pF at 1.7 "
          "Mbit/s)", "tens of ns", "current-source pull-up on master SCL",
          "Entered with master code 00001xxx at Fm speed"],
         ["Ultra-fast (UFm)", "5 Mbit/s", "-", "-", "**push-pull**",
          "Unidirectional (write-only), no ACK; USCL/USDA; not compatible "
          "with other modes"]],
        widths=[17, 12, 14, 10, 18, 29], bold_first=True)
    p("Rise time is the RC charge from 30 % to 70 % of VDD through the "
      "pull-up: t = Rp x Cb x ln(0.7/0.3) = 0.8473 Rp Cb. That gives a "
      "**maximum Rp** for a given capacitance, while the driver's sink "
      "current at VOL(max) = 0.4 V gives a **minimum Rp**:")
    _v("py_pullup", "Pull-up resistor window for a 3.3 V bus (Python 3).")
    _o("py_pullup", "At Fm with 400 pF there is no valid resistor for a 3 mA "
       "driver - you must reduce capacitance (split the bus with a "
       "buffer/mux), use Fm+ drivers or an active pull-up.")
    box("tip", "Choosing Rp in practice",
        "Pick a value near the low end of the window for speed margin but "
        "not at it (sink current, VOL and power when the line is held "
        "low). Common results: 4.7 kohm for 100 kHz, 2.2 kohm for 400 kHz "
        "on short board buses, ~1 kohm or less for Fm+. Remember every "
        "device on the bus, the connector and each board trace adds "
        "capacitance - on the order of 10 pF per device pin.")

    h2("Timing parameters")
    p("UM10204 specifies a set of named timing parameters. Their meaning "
      "matters more than memorizing values; the key ones for Sm/Fm/Fm+:")
    tbl(["Parameter", "Meaning", "Sm", "Fm", "Fm+"],
        [["fSCL", "SCL clock frequency (max)", "100 kHz", "400 kHz",
          "1 MHz"],
         ["tLOW", "SCL low period (min)", "4.7 us", "1.3 us", "0.5 us"],
         ["tHIGH", "SCL high period (min)", "4.0 us", "0.6 us", "0.26 us"],
         ["tHD;STA", "Hold time after (repeated) START before first SCL "
          "fall", "4.0 us", "0.6 us", "0.26 us"],
         ["tSU;STA", "Setup time for a repeated START (SCL high to SDA "
          "fall)", "4.7 us", "0.6 us", "0.26 us"],
         ["tSU;DAT", "Data setup before SCL rises", "250 ns", "100 ns",
          "50 ns"],
         ["tHD;DAT", "Data hold after SCL falls (min 0; devices provide "
          "internal hold to bridge the SCL fall time)", "0 ns", "0 ns",
          "0 ns"],
         ["tSU;STO", "Setup time for STOP (SCL high to SDA rise)", "4.0 us",
          "0.6 us", "0.26 us"],
         ["tBUF", "Bus free time between STOP and next START", "4.7 us",
          "1.3 us", "0.5 us"],
         ["tSP", "Spikes shorter than this must be suppressed", "-",
          "50 ns", "50 ns"]],
        widths=[13, 47, 13, 13, 14], bold_first=True)
    p("Notice that tLOW(min) + tHIGH(min) at Fm is 1.9 us, less than "
      "the 2.5 us period, but only barely: with realistic rise and fall "
      "times, 400 kHz is only achievable if the controller's low phase is "
      "longer than half the period. Controllers therefore program SCL low "
      "and high counts separately (for example 60:40), and the rise time "
      "adds to the high count when the controller waits for SCL to go "
      "high, as ours does.")
    box("warn", "PITFALL: tHD;DAT = 0 and the SCL fall time",
        "Because a device may change SDA immediately after SCL falls, a "
        "receiver seeing a slow SCL fall (or a synchronizer-delayed one) "
        "can sample SDA that has already changed - interpreted as a "
        "spurious START or STOP. The fix, mandatory for slaves, is an "
        "internal SDA hold delay (the spec requires devices to provide at "
        "least 300 ns internally to bridge SCL's undefined region) and "
        "filtering SCL/SDA before edge detection.")

    h2("Glitch filters and bus recovery")
    bul(["**Glitch (spike) filters**: Fm and Fm+ inputs must reject pulses "
         "shorter than 50 ns. In RTL this is a digital filter: a signal "
         "must be stable for N samples of a fast clock before it is "
         "accepted (N x T_clk >= 50 ns). It is applied before START/STOP "
         "detection.",
         "**Bus recovery**: if a master is reset mid-transaction while a "
         "slave is driving a 0 (an ACK, or a data bit of a read), the "
         "slave holds SDA low forever waiting for clocks. The standard "
         "remedy is to send **up to nine SCL pulses** with SDA released "
         "until the slave finishes its byte and releases SDA, then "
         "generate STOP. Good controllers do this in hardware and report "
         "'bus stuck'. If SCL itself is stuck low, only a reset of the "
         "offending device (or a power cycle) helps.",
         "**Software reset**: general call address 0x00 followed by 0x06 "
         "resets devices that support it."])
    diagram([
        "  master reset here --v",
        "  SCL ~~\\__/~~\\__/~~\\__ (stopped)          __/~~\\__/~~\\__/~~\\__/~~   P",
        "  SDA =========X_______________ (slave holds SDA low until it gets clocks)~~~/~~~",
        "                               recovery: clock SCL up to 9 times with SDA",
        "                               released, stop as soon as SDA reads 1, then STOP",
    ], "Nine-clock bus recovery.")

    h2("SMBus: I2C with rules")
    p("The System Management Bus (SMBus, originally Intel/Duracell, now "
      "maintained by the SBS Implementers Forum) uses I2C signalling but "
      "tightens it for reliable system management in PCs, servers and "
      "batteries:")
    tbl(["Topic", "I2C", "SMBus"],
        [["Clock range", "0 to 100/400/1000 kHz", "10 kHz minimum to "
          "100 kHz (SMBus 3.x also defines 400 kHz and 1 MHz classes)"],
         ["Timeout", "None - a slave may stretch forever", "**tTIMEOUT "
          "25-35 ms**: a device seeing SCL low > 25 ms must reset its "
          "interface; limits on cumulative stretching per byte and per "
          "message"],
         ["Logic levels", "Relative to VDD", "Fixed thresholds (so 1.8 V-"
          "3.3 V devices mix)"],
         ["ACK", "Optional semantics", "A device must ACK its own address "
          "at all times (so presence can be detected)"],
         ["Error check", "None", "**PEC**: optional CRC-8 (x^8+x^2+x+1) "
          "over every byte of the message, including addresses"],
         ["Protocols", "Free-form", "Defined: Quick Command, Send/Receive "
          "Byte, Write/Read Byte/Word, Process Call, Block Write/Read, "
          "Block Process Call"],
         ["Extras", "-", "**SMBALERT_n** interrupt line with Alert "
          "Response Address 0x0C; Host Notify; **ARP** (Address "
          "Resolution Protocol) assigns addresses using a 128-bit UDID via "
          "the default address 0x61"]],
        widths=[15, 25, 60], bold_first=True)
    p("The timeout is the key difference for RTL: an SMBus controller or "
      "target needs a counter that detects SCL low for longer than 25 ms "
      "and resets the interface, which also makes SMBus self-recovering "
      "from the stuck-bus scenario that plagues plain I2C. PEC generation "
      "is a serial CRC-8 identical in structure to the CAN CRC shown in "
      "Chapter 15, run over the address byte(s), command and data.")

    h2("PMBus: power management on SMBus")
    p("PMBus (Power Management Bus) standardizes the **commands** for "
      "digital power supplies, regulators and PMICs on top of SMBus "
      "transport, so one driver can configure, monitor and log faults for "
      "any compliant device. Each command is an SMBus command code:")
    tbl(["Code", "Command", "Purpose"],
        [["00h", "PAGE", "Select the output rail on a multi-rail device"],
         ["01h", "OPERATION", "On/off, margin high/low"],
         ["03h", "CLEAR_FAULTS", "Clear latched status bits"],
         ["20h / 21h", "VOUT_MODE / VOUT_COMMAND", "Output-voltage data "
          "format and set-point"],
         ["78h / 79h", "STATUS_BYTE / STATUS_WORD", "Summary fault status"],
         ["88h / 8Bh / 8Ch", "READ_VIN / READ_VOUT / READ_IOUT",
          "Telemetry"],
         ["8Dh", "READ_TEMPERATURE_1", "Telemetry"]],
        widths=[16, 34, 50])
    p("Values use compact formats: **LINEAR11** (a 5-bit two's-complement "
      "exponent and an 11-bit mantissa, value = m x 2^{e}), **LINEAR16** "
      "for output voltage (16-bit mantissa with the exponent in VOUT_MODE) "
      "and DIRECT (coefficients m, b, R). PMBus 1.3 also added AVSBus, a "
      "fast point-to-point interface for adaptive voltage scaling from the "
      "SoC to its regulator. In an SoC this is a firmware-heavy protocol: "
      "the RTL is a standard I2C/SMBus controller with PEC and timeouts, "
      "and a power-management microcontroller runs the PMBus stack.")

    h2("I2C in an SoC: controllers, slaves and verification")
    bul(["**Controller features**: separate SCL low/high counters, FIFOs "
         "for TX/RX, command queue (so DMA can run whole transactions), "
         "10-bit addressing, repeated START, clock-stretch timeout, bus "
         "recovery, arbitration-loss interrupt, SMBus PEC/timeouts.",
         "**Target (slave) mode**: address match (often two addresses plus "
         "general call), stretching until software/DMA supplies data, "
         "wake-up on address match from low-power states.",
         "**Pads**: true open-drain (or a push-pull pad with the output "
         "tied to 0 and the enable toggled), 5 V-tolerant or fail-safe "
         "when the SoC is unpowered (a powered-off SoC must not clamp the "
         "bus through its ESD diodes).",
         "**DV**: an I2C VIP with stretching, arbitration and NACK "
         "injection; checkers for tHD;STA/tSU;STO/tBUF; tests of recovery "
         "from a stuck SDA; a real pull-up model (`pullup` or `tri1`) - "
         "simulations that drive 1 instead of Z hide wired-AND bugs.",
         "**Ownership**: RTL owns controller/target logic and filters; PD "
         "and IO own open-drain pads; board designers own Rp and "
         "capacitance; firmware owns addresses, retries and recovery."])

    h2("Summary")
    bul(["I2C uses two open-drain lines with pull-ups; wired-AND gives "
         "ACK, clock stretching and lossless arbitration.",
         "START/STOP are SDA edges while SCL is high; otherwise SDA changes "
         "only while SCL is low. Every byte is 8 bits + ACK/NACK.",
         "7-bit addresses are sent as address<<1 | R/W; 10-bit addressing "
         "uses the 11110xx prefix; several address ranges are reserved.",
         "Speed modes: Sm 100k, Fm 400k, Fm+ 1M, Hs 3.4M (open drain with "
         "current-source pull-up), UFm 5M (push-pull, write-only). Rise "
         "time 0.8473 Rp Cb bounds the pull-up; bus capacitance limits "
         "speed.",
         "Our RTL master performed writes, a repeated-START read with "
         "clock stretching and detected a NACK against an open-drain slave.",
         "Recovery: up to nine SCL pulses then STOP; glitch filters reject "
         "< 50 ns spikes; SMBus adds 25-35 ms timeouts, PEC CRC-8, ARP and "
         "SMBALERT_n; PMBus defines power-management commands and data "
         "formats."])

    h2("Exercises")
    bul(["Draw SCL and SDA for a random read of register 0x2C from device "
         "0x68 returning 0x5A, marking which device drives SDA in every "
         "bit.",
         "A bus has 6 devices at 10 pF each plus 60 pF of wiring. Compute "
         "the Rp window at 400 kHz and 3.3 V. Would 1.8 V change it?",
         "Add arbitration-loss detection to the `i2c_master` in this "
         "chapter: in quarter 2 of a data bit, if SDA reads 0 while the "
         "master released it, abort and report `arb_lost`. Where else can "
         "arbitration be lost?",
         "Implement a 50 ns glitch filter for a 100 MHz sampling clock and "
         "explain why it must precede START/STOP detection.",
         "Compute the SMBus PEC for a Write Byte of 0x55 to command 0x10 "
         "at 7-bit address 0x16 (hint: the CRC covers 0x2C, 0x10, 0x55).",
         "Why must an SMBus device ACK its own address even when busy, "
         "whereas an I2C EEPROM may NACK during a write cycle?"],
        ordered=True)


# ---------------------------------------------------------------- Ch 14 ---
def _ch14():
    chapter("MIPI I3C")
    p("By the mid-2010s a flagship phone carried a dozen or more sensors "
      "(accelerometer, gyroscope, magnetometer, pressure, proximity, "
      "ambient light, fingerprint, touch, haptics...), each on I2C or SPI "
      "plus a separate interrupt GPIO. I2C was too slow and too "
      "power-hungry (every 0 bit burns current through a pull-up), SPI "
      "needed too many pins, and the GPIO count kept growing. The MIPI "
      "Alliance's answer, **I3C** (Improved Inter-Integrated Circuit, "
      "first released in 2016/2017), keeps the two-wire bus and I2C "
      "compatibility but adds push-pull signalling at up to 12.5 MHz, "
      "in-band interrupts, dynamic addressing and optional high-data-rate "
      "modes. JEDEC adopted the royalty-free **I3C Basic** subset for the "
      "DDR5 DIMM sideband bus (SPD hub, PMIC and temperature sensors), "
      "which has brought I3C into servers and PCs as well.")
    tbl(["Problem with I2C", "I3C answer"],
        [["Open-drain rising edges limit speed to 0.4-1 Mbit/s and waste "
          "power", "**Push-pull** data at 12.5 MHz SDR (open drain only "
          "where arbitration or ACK needs it)"],
         ["Every sensor needs an interrupt pin", "**In-band interrupts (IBI)** "
          "on SDA, with priority by address"],
         ["Static addresses collide; address pins cost pins", "**Dynamic "
          "address assignment** (ENTDAA) using a 48-bit provisioned ID"],
         ["No standard management commands", "**Common Command Codes "
          "(CCCs)** for enable/disable events, reset, max data length, "
          "status, timing"],
         ["Devices cannot join a running bus cleanly", "**Hot-join**"],
         ["No path beyond ~1 Mbit/s on two wires", "**HDR modes** (DDR, "
          "ternary, bulk transport)"],
         ["Clock stretching makes timing unbounded", "Targets may **not** "
          "stretch SCL; flow control is explicit (T-bit, IBI)"]],
        widths=[42, 58])

    h2("Bus roles and backward compatibility")
    p("An I3C bus has one **active controller** (optionally secondary "
      "controllers that can take over), I3C **targets**, and optionally "
      "**legacy I2C targets**. The controller always drives SCL - in I3C "
      "SCL is effectively push-pull - and SDA is shared.")
    bul(["I2C targets on an I3C bus must be Fm/Fm+ devices with the **50 ns "
         "spike filter** and must not stretch the clock. The controller "
         "keeps SCL high pulses short (well under 50 ns) during I3C-only "
         "traffic, so the legacy devices' filters simply never see a clock "
         "- they cannot misinterpret I3C traffic as their address.",
         "I2C traffic to legacy devices is still sent at Fm/Fm+ timing, "
         "open drain, on the same wires.",
         "The controller provides SDA's pull-up (often switchable and "
         "a weak 'high-keeper'), so boards do not need per-bus resistors "
         "tuned for speed.",
         "An I3C target can also have a **static I2C address** and behave "
         "as an I2C device until it is given a dynamic address."])

    h2("Open drain where needed, push-pull everywhere else")
    p("I3C switches SDA's driver type within a single message:")
    tbl(["Phase", "SDA driver", "Why"],
        [["START + address header 7Eh (or a target address) after START",
          "**Open drain**", "Targets may be arbitrating in parallel (IBI, "
          "hot-join, controller request)"],
         ["ACK/NACK after the address", "Open drain", "Target pulls low to "
          "ACK; nobody is harmed if several ACK"],
         ["Data bytes, CCC codes, T-bits", "**Push-pull**", "One driver at a "
          "time; fast edges independent of Rp"],
         ["Address after a Repeated START", "Push-pull", "No arbitration is "
          "possible after Sr"],
         ["Handoff (T-bit in reads)", "Target drives, then releases",
          "Allows the controller to abort a read (see below)"]],
        widths=[36, 18, 46])
    diagram([
        "        S   7E / W (open drain)   ACK  CCC code (push-pull)  T   Sr  DA / R ...",
        " SCL ~~~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/ .. \\_/~\\_/~\\_/~~\\_/~ ..",
        " SDA ~\\___X===X===X===X===X===X===X===X___X===X===X===X ..  ===X===X~~\\___X==",
        "            1   1   1   1   1   1   0    ^ target ACK                ^ odd parity",
        "      open drain + pull-up (slow edges)  | push-pull, SCL up to 12.5 MHz",
    ], "An SDR message: broadcast address 7Eh in open drain, then push-pull "
       "data with a T-bit in place of ACK. Repeated START lets the "
       "controller address a target without a STOP.")

    h2("SDR mode, the T-bit and the 9th bit")
    p("In **SDR** (single data rate) mode an I3C message looks like I2C: "
      "START, address + R/W, ACK, 8-bit bytes. SCL runs at up to "
      "**12.5 MHz**, giving a raw 12.5 Mbit/s and about 11 Mbit/s of "
      "payload after the ninth bits. The difference is the ninth bit of "
      "each data byte:")
    bul(["**Write data**: the ninth bit is a **T-bit = odd parity** of the "
         "byte, driven by the controller. The target checks it; there is "
         "no per-byte ACK. (A parity error is a detectable target error.)",
         "**Read data**: the ninth bit is an **end-of-data** signal driven "
         "by the target: T = 1 means 'more data follows', T = 0 means "
         "'this was the last byte'. When the target signals more data, "
         "it hands SDA back after driving the high level, and the "
         "controller may still abort by generating a Repeated START during "
         "that bit.",
         "Because targets cannot stretch SCL, a target that is not ready "
         "must NACK its address, or use its IBI to tell the controller "
         "when data is available."])
    box("intuit", "Why odd parity?",
        "With odd parity the T-bit is 1 whenever the byte has an even number "
        "of ones - in particular for 00h. A stuck-low SDA (all zeros) "
        "therefore always fails parity, and a byte plus T-bit always "
        "contains at least one 1, so the line keeps toggling. The run "
        "below shows T = 1 for 00h, A5h and FFh and T = 0 for 01h.")

    h2("Dynamic address assignment (ENTDAA)")
    p("Every I3C target carries a **48-bit Provisioned ID (PID)**: a 15-bit "
      "MIPI manufacturer ID, a type bit (random or vendor-fixed part "
      "value), a part ID, an instance ID and extra bits. It is followed by "
      "the **BCR** (Bus Characteristics Register: role, IBI capability, "
      "whether IBIs carry payload, speed limits, offline capability) and "
      "the **DCR** (Device Characteristics Register: device type code). "
      "After reset, targets without a static address have no address at "
      "all; the controller runs ENTDAA:")
    diagram([
        "  S 7E/W A  ENTDAA(07h) T",
        "  Sr 7E/R A   <- every unaddressed target ACKs (open drain)",
        "      targets send PID[47:0], BCR[7:0], DCR[7:0] MSB first, OPEN DRAIN:",
        "      a target that writes 1 but reads 0 has lost and drops out",
        "      controller sends dynamic address DA[6:0] + parity bit     target A",
        "  Sr 7E/R A   <- remaining targets arbitrate again ...",
        "  Sr 7E/R N   <- nobody ACKs: all targets have addresses -> P",
    ], "ENTDAA flow. The 64-bit arbitration uses the same wired-AND "
       "principle as I2C multi-master arbitration and CAN; the lowest "
       "{PID, BCR, DCR} value wins each round.")
    p("The RTL below models the arbitration core: three targets shift out "
      "their 64-bit IDs onto a wired-AND SDA, each drops out as soon as it "
      "sends a 1 but sees a 0, and the survivor accepts the next dynamic "
      "address. The controller keeps running rounds until the bus reads "
      "all ones (nobody arbitrating, i.e. the NACK case). The address is "
      "sent with an odd-parity bit computed by the same function as the "
      "SDR T-bit. (The surrounding framing - 7Eh header, ACKs, Sr - is "
      "omitted to keep the example short.)")
    _v("i3c", "Target-side DAA arbitration logic and the I3C odd-parity "
       "function.")
    _v("tb_i3c", "Three targets: two from the same manufacturer differing "
       "only in instance ID, and one from a manufacturer with a lower ID.")
    _o("i3c", "Real Icarus Verilog output. Target C wins first (lower "
       "manufacturer ID), then B (instance 1) before A (instance 2); the "
       "fourth round reads all ones and ends DAA.")
    p("Other ways to assign addresses: **SETDASA** (direct CCC: give a "
      "dynamic address to a target that has a known static I2C address), "
      "**SETAASA** (broadcast: all targets use their static address as "
      "dynamic address - quick, used by the DDR5 sideband bus), and "
      "**SETNEWDA** to change an address later. **RSTDAA** removes all "
      "dynamic addresses.")
    box("expert", "Interview insight: priority is baked into the address",
        "In IBI arbitration the lower dynamic address wins, exactly like in "
        "DAA. A controller therefore assigns the **lowest** dynamic "
        "addresses to the targets whose interrupts are most urgent - "
        "address assignment is also interrupt-priority assignment.")

    h2("Common Command Codes (CCCs)")
    p("CCCs are the bus-management language. A **broadcast CCC** (codes "
      "00h-7Fh) is sent after `S 7Eh/W` and applies to all targets; a "
      "**direct CCC** (80h-FEh) is followed by Sr and one or more "
      "target addresses, each with its own data. Some examples:")
    tbl(["Code (bcast / direct)", "Name", "Purpose"],
        [["00h / 80h", "ENEC", "Enable target events (IBI, controller "
          "request, hot-join)"],
         ["01h / 81h", "DISEC", "Disable target events"],
         ["06h", "RSTDAA", "Reset all dynamic addresses"],
         ["07h", "ENTDAA", "Enter dynamic address assignment"],
         ["08h", "DEFTGTS (DEFSLVS)", "Tell secondary controllers the "
          "list of targets"],
         ["09h / 89h, 0Ah / 8Ah", "SETMWL, SETMRL", "Set max write / read "
          "length"],
         ["20h-27h", "ENTHDR0-7", "Enter an HDR mode (0 = HDR-DDR)"],
         ["29h", "SETAASA", "Use static addresses as dynamic addresses"],
         ["87h, 88h", "SETDASA, SETNEWDA", "Assign / change a dynamic "
          "address"],
         ["8Dh, 8Eh, 8Fh", "GETPID, GETBCR, GETDCR", "Read identification"],
         ["90h", "GETSTATUS", "Read target status (pending interrupt, "
          "errors)"],
         ["94h, 95h", "GETMXDS, GETCAPS", "Max data speed and turnaround; "
          "capabilities (HDR modes supported)"]],
        widths=[25, 25, 50],
        caption="Selected CCCs (names from I3C v1.1; older documents use "
        "master/slave names such as DEFSLVS and GETHDRCAP).")

    h2("In-band interrupts and hot-join")
    p("With the bus idle (after a bus-available time), a target that needs "
      "attention **pulls SDA low** - a START request. The controller "
      "responds by clocking SCL, and the target sends its own **dynamic "
      "address with R/W = 1** in the open-drain arbitration header. If "
      "several targets request at once, the lowest address wins; the "
      "others retry later. The controller ACKs to accept (or NACKs to "
      "refuse and later disable with DISEC); if the target's BCR says "
      "its IBIs carry payload, it then sends a **Mandatory Data Byte** "
      "(and optionally more) in push-pull mode.")
    diagram([
        "  bus idle ~~~~~~~~~~~~~~~ SDA pulled low by target (START request)",
        "  SCL ~~~~~~~~~~~~~~~~~~~~~~~~~~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_ ...",
        "  SDA ~~~~~~~~~~~~~~~~~~~~\\_____X DA6 .. DA0 X R=1 X ACK X  MDB ... T  X  P",
        "                        target  arbitration (open drain)  ctrl  push-pull",
    ], "In-band interrupt: no extra wire, and the interrupt identifies its "
       "source and can carry a payload byte (e.g. 'FIFO watermark').")
    p("**Hot-join**: a target that powers up on a running bus waits for "
      "bus idle, then requests with the reserved address **02h** and R/W = "
      "0. The controller ACKs and later runs ENTDAA to give it an "
      "address. Similarly, a secondary controller asks for the bus with its "
      "own address and R/W = 0 (controller role request).")

    h2("HDR modes")
    p("After the controller enters an HDR mode with ENTHDRx, the bus "
      "uses a different encoding until the controller sends the **HDR Exit "
      "Pattern** (SDA toggling while SCL is held low), which every I3C "
      "device - including ones that do not implement that HDR mode - "
      "detects. Legacy I2C devices see no valid clock pulses throughout.")
    tbl(["Mode", "Idea", "Raw rate at 12.5 MHz (typical figures quoted)"],
        [["SDR", "One bit per SCL cycle", "12.5 Mbit/s (about 11 Mbit/s "
          "effective)"],
         ["HDR-DDR", "Data on both SCL edges; 16-bit words with a 2-bit "
          "preamble and parity; command/data/CRC words", "25 Mbit/s raw "
          "(about 20 Mbit/s effective)"],
         ["HDR-TSP / HDR-TSL", "Ternary symbols: both SCL and SDA carry "
          "information (transitions on either line); TSP for pure I3C buses, "
          "TSL when legacy I2C devices are present", "about 33 Mbit/s raw"],
         ["HDR-BT (v1.1)", "Bulk transport with larger blocks and optional "
          "multi-lane data (additional data lines)", "Highest; scales with "
          "lanes"]],
        widths=[16, 50, 34], bold_first=True)
    p("HDR-DDR is by far the most implemented HDR mode. Its framing "
      "(preamble bits that distinguish command, data and CRC words, a "
      "5-bit CRC at the end, and parity per word) is a good example of "
      "how a protocol adds robustness when it removes per-byte ACKs.")

    h2("Timing and electrical overview")
    bul(["SDR SCL up to 12.5 MHz (80 ns period); in mixed buses with legacy "
         "I2C devices, the SCL high time is kept short enough (well below "
         "the 50 ns spike filter) that I2C devices ignore it.",
         "Open-drain phases are slower (on the order of a few MHz) because "
         "they rely on the pull-up; the controller may use a faster "
         "open-drain timing when no legacy devices are present.",
         "Targets sample on SCL edges and the controller must allow for "
         "the target's clock-to-data turnaround on reads (GETMXDS reports "
         "it) - the same round-trip problem as SPI, solved by slowing "
         "reads or delaying capture.",
         "Voltage levels are typically 1.2 V or 1.8 V on phones and around "
         "1.0-1.2 V on the DDR5 sideband bus (varies by implementation).",
         "Energy per bit is far lower than I2C: push-pull edges do not "
         "dump current through a pull-up for every 0."])

    h2("I3C Basic versus full I3C")
    p("**I3C Basic** is a subset of the full specification that MIPI "
      "made available publicly and royalty-free (I3C Basic v1.0 in 2018, "
      "updated with later versions). It keeps what most systems need - "
      "SDR mode, dynamic addressing, IBIs, hot-join, the common CCCs and "
      "(depending on version) HDR-DDR - and omits some advanced "
      "features such as the ternary HDR modes. JEDEC's DDR5 sideband "
      "bus (JESD403) and SPD5 hub devices are built on I3C Basic, and "
      "MIPI's **I3C HCI** (Host Controller Interface) specification "
      "standardizes the controller's register/queue interface so one "
      "Linux/firmware driver can drive controllers from different "
      "vendors.")

    h2("Building an I3C controller")
    diagram([
        "  APB/AXI  +----------------+   +-----------------+   +-------------------+",
        "  <------->| HCI-style regs |-->| command queue   |-->| transfer engine   |",
        "           | + DMA rings    |   | response queue  |   | SDR / HDR-DDR     |",
        "  IRQ <----| IBI queue      |<--| IBI status/data |<--| arbitration, DAA  |",
        "           +----------------+   +-----------------+   +---------+---------+",
        "                                                                |",
        "                                  SCL (push-pull), SDA (od/pp)  | pull-up ctl",
    ], "Typical controller structure. Targets are simpler: address match, "
       "CCC decoder, IBI request logic, and a small register/FIFO "
       "interface.")
    bul(["The **SDA pad** must switch between open-drain and push-pull per "
         "bit, with a controllable pull-up; this is the main PHY-level "
         "difference from an I2C pad.",
         "An internal **clock** of 4x-8x the SCL rate (for example 100 MHz "
         "for 12.5 MHz SCL) lets the engine place edges precisely and "
         "sample SDA with programmable delay.",
         "**DV**: an I3C VIP is essential (DAA with colliding IDs, IBI "
         "races with controller-initiated messages, parity errors, HDR "
         "entry/exit, legacy devices on the bus); compliance testing uses "
         "the MIPI conformance test suites.",
         "**Firmware**: bus enumeration (DAA, GETPID/BCR/DCR), IBI "
         "handling, per-target max read/write lengths - most integration "
         "bugs are in this sequencing rather than in bit timing."])

    h2("Summary")
    bul(["I3C keeps two wires and I2C compatibility but uses push-pull "
         "data at up to 12.5 MHz SDR, falling back to open drain only for "
         "arbitration and ACK phases; targets cannot stretch SCL.",
         "Write data carries an odd-parity T-bit instead of ACK; read data "
         "uses the ninth bit as an end-of-data indicator.",
         "ENTDAA assigns 7-bit dynamic addresses by open-drain arbitration "
         "on the 48-bit PID + BCR + DCR (lowest wins); the simulated three "
         "targets were addressed in exactly that order.",
         "CCCs (broadcast 00h-7Fh, direct 80h-FEh) manage the bus; IBIs "
         "replace interrupt wires with address-prioritized in-band "
         "requests; hot-join uses address 02h.",
         "HDR modes (DDR, TSP/TSL, BT) raise throughput; all devices "
         "recognize the HDR exit pattern.",
         "I3C Basic is the public, royalty-free subset used by JEDEC DDR5 "
         "sideband devices; I3C HCI standardizes the controller software "
         "interface."])

    h2("Exercises")
    bul(["Compute the T-bits for the bytes 3Ch, 7Fh and 80h. Which single "
         "stuck-at fault of SDA does odd parity always detect?",
         "Four targets have PIDs whose first differing bit is bit 20. "
         "Explain why the order of DAA does not depend on the order in which "
         "they were powered up, and what happens if two targets have "
         "identical PID, BCR and DCR.",
         "An accelerometer must interrupt with priority over a temperature "
         "sensor. Which dynamic addresses would you give them and why?",
         "Estimate the time to read a 32-byte FIFO in SDR at 12.5 MHz "
         "(including S, header, address, T-bits, P) and compare with I2C "
         "Fm+ at 1 MHz.",
         "Why can an I3C controller use push-pull after a Repeated START "
         "but not after a START?",
         "Extend the DAA testbench so that a fourth target joins the bus "
         "after the first round (hot-join) and is addressed in the next "
         "ENTDAA."], ordered=True)


# ---------------------------------------------------------------- Ch 15 ---
def _ch15():
    chapter("Automotive and Industrial Buses: CAN, CAN FD, CAN XL, LIN, "
            "FlexRay and Automotive Ethernet")
    p("A modern car contains somewhere between tens and over a hundred "
      "electronic control units (ECUs) - engine, brakes, airbags, doors, "
      "seats, infotainment, cameras, radar - connected by a hierarchy of "
      "networks. The requirements are unlike those inside an SoC: long "
      "cables in an electrically hostile environment, dozens of nodes on "
      "one bus, hard real-time deadlines, and functional safety (ISO "
      "26262). Factories have similar needs. This chapter covers the "
      "bit-level design of CAN in depth, because its ideas - dominant/"
      "recessive signalling, bitwise arbitration, bit stuffing, CRC and "
      "fault confinement - are elegant and are asked about constantly, and "
      "then surveys CAN FD, CAN XL, LIN, FlexRay, automotive Ethernet and "
      "industrial fieldbuses.")
    tbl(["Network", "Rate", "Typical use", "Medium"],
        [["LIN", "up to 20 kbit/s", "Seats, mirrors, window lifts, "
          "switches, sensors (cheap sub-networks)", "1 wire, 12 V"],
         ["CAN (classic)", "up to 1 Mbit/s (125-500k typical)", "Body, "
          "powertrain, chassis; diagnostics (OBD-II)", "Twisted pair"],
         ["CAN FD", "~2-5 Mbit/s data phase (up to 8)", "Powertrain, "
          "ADAS, software updates", "Twisted pair"],
         ["CAN XL", "~10-20 Mbit/s data phase", "Zonal architectures, "
          "bridge to Ethernet", "Twisted pair"],
         ["FlexRay", "10 Mbit/s per channel", "Chassis/x-by-wire "
          "(legacy, declining)", "1-2 twisted pairs"],
         ["Automotive Ethernet", "10 Mbit/s - 10 Gbit/s", "Backbone, "
          "cameras, ADAS, infotainment, zonal", "Single twisted pair"]],
        widths=[18, 22, 42, 18], bold_first=True)

    h2("CAN physical layer: dominant and recessive")
    p("Classic CAN (Bosch, 1986; ISO 11898-1 for the data link, 11898-2 "
      "for the high-speed physical layer) uses a differential pair, "
      "CAN_H and CAN_L, terminated with 120 ohm at each end. A transceiver "
      "translates between the pair and the controller's logic-level TXD/"
      "RXD pins.")
    diagram([
        "  bit value      recessive (1)        dominant (0)        recessive (1)",
        "  CAN_H  3.5 V -              +-------------------+",
        "         2.5 V ---------------+                   +-------------------",
        "  CAN_L  2.5 V ---------------+                   +-------------------",
        "         1.5 V -              +-------------------+",
        "  Vdiff = CAN_H - CAN_L:   ~0 V            ~2 V            ~0 V",
        "  receiver: Vdiff > 0.9 V -> dominant ; Vdiff < 0.5 V -> recessive",
        "",
        "  node: MCU CAN controller --TXD/RXD--> transceiver --CAN_H/CAN_L--> bus",
        "  bus:  [120 ohm]===+=======+=======+=======+===[120 ohm]   (60 ohm total)",
    ], "High-speed CAN levels (nominal values).")
    p("Dominant (logic 0) is actively driven; recessive (logic 1) is the "
      "undriven state where the termination pulls the lines together. "
      "Electrically this is a **wired-AND** exactly like I2C: if any node "
      "transmits 0, the bus is 0. Every node always reads back the bus "
      "(RXD) while transmitting, which is the basis of arbitration and "
      "error detection. The maximum bus length shrinks with bit rate "
      "because each bit must propagate to the far end and back within the "
      "bit time (rule of thumb: ~40 m at 1 Mbit/s, ~100 m at 500 kbit/s, "
      "~500 m at 125 kbit/s).")

    h2("Frame formats")
    diagram([
        "  classic base (standard) data frame, 44 + 8N bits before stuffing",
        "  +---+-----------+---+---+--+-----+---------+-----------+--+---+--+-------+---+",
        "  |SOF| ID[10:0]  |RTR|IDE|r0| DLC | DATA    | CRC[14:0] |CD|ACK|AD|  EOF  |IFS|",
        "  | 1 |    11     | 1 | 1 |1 |  4  | 0..64   |    15     |1 | 1 |1 |   7   | 3 |",
        "  +---+-----------+---+---+--+-----+---------+-----------+--+---+--+-------+---+",
        "  |<----- arbitration ---->|<- control ->|             CD = CRC delimiter (1)",
        "  |<-------------------- bit stuffing applies ---------->|  AD = ACK delimiter (1)",
        "",
        "  extended data frame (29-bit ID):",
        "  |SOF| ID[28:18] |SRR|IDE| ID[17:0] |RTR|r1|r0| DLC | DATA | CRC | ...",
        "  | 1 |    11     | 1 | 1 |    18    | 1 | 1| 1|  4  |",
        "                    ^ recessive  ^ recessive = extended",
    ], "Classic CAN frames. ACK: the transmitter sends a recessive ACK slot; "
       "every receiver that got a correct CRC overwrites it with dominant.")
    bul(["**SOF**: one dominant bit; all nodes hard-synchronize to its edge.",
         "**Identifier**: 11 bits (CAN 2.0A base format) or 29 bits (2.0B "
         "extended). It identifies the **message content and priority**, "
         "not a node - any node may receive any message (acceptance "
         "filtering is local).",
         "**RTR**: dominant for data frames, recessive for **remote frames** "
         "(a request for a message with that ID; no data field). **IDE**: "
         "dominant for base format. **SRR** in extended frames is a "
         "recessive placeholder at the RTR position.",
         "**DLC**: 0-8 data bytes (codes 9-15 also mean 8 in classic CAN).",
         "**CRC**: 15-bit sequence + recessive delimiter. **ACK**: slot + "
         "delimiter. **EOF**: 7 recessive bits; then 3 bits of "
         "intermission before the next frame may start.",
         "**Error frames** (error flag of 6 bits + 8-bit delimiter) and "
         "**overload frames** are not data - they are signals, discussed "
         "below."])

    h2("Bitwise arbitration")
    p("CAN is multi-master: any node can start transmitting after the bus "
      "has been idle. If several start in the same bit time (all "
      "synchronized to the same SOF), they arbitrate **during the "
      "identifier, bit by bit**. A node sending recessive (1) that reads "
      "dominant (0) has lost: it stops transmitting at once and becomes a "
      "receiver of the winning frame. The winner never notices the "
      "contention - **non-destructive arbitration** - so no bandwidth is "
      "wasted and the frame with the **lowest numerical ID** (highest "
      "priority) always gets through with bounded latency.")
    _v("can_arb", "A minimal arbitration node: it shifts out SOF, 11-bit ID "
       "and RTR, reads back the wired-AND bus, and drops to recessive after "
       "losing.")
    _v("tb_can_arb", "Two nodes starting simultaneously: first with different "
       "IDs, then with the same ID as data frame vs. remote frame.")
    _o("can_arb", "Real Icarus Verilog output. 123h beats 12Bh at ID bit 3; "
       "with identical IDs the data frame (RTR dominant) beats the remote "
       "frame at the RTR bit.")
    p("Two more consequences: two nodes must **never** transmit the same "
      "ID with different data (arbitration would not resolve and a bit "
      "error would follow), and a base-format frame beats an extended "
      "frame with the same first 11 ID bits, because the extended frame "
      "sends a recessive SRR where the base frame has its dominant RTR.")
    box("expert", "Interview insight: why CAN latency is analysable",
        "Because arbitration is priority-based and non-destructive, "
        "worst-case response times can be computed with fixed-priority "
        "scheduling analysis (like tasks on an RTOS): a message waits at "
        "most for one lower-priority frame already on the bus (no "
        "pre-emption mid-frame) plus all higher-priority traffic. Classic "
        "Ethernet with random back-off had no such bound, which is why "
        "cars used CAN for control loops and why automotive Ethernet needed "
        "TSN before it could replace it.")

    h2("Bit stuffing and the CRC-15")
    p("CAN is NRZ-coded and self-clocked: receivers resynchronize on "
      "recessive-to-dominant edges. A long run of identical bits would "
      "give no edges, so the transmitter inserts a **stuff bit** of the "
      "opposite value after **five consecutive identical bits**, from SOF "
      "through the end of the CRC sequence. The receiver removes it. Six "
      "identical bits in that region is therefore illegal - a **stuff "
      "error** - which is exactly what an error flag (six equal bits) "
      "exploits to get everyone's attention.")
    p("The CRC is computed over the **unstuffed** bits from SOF through the "
      "data field with generator x^{15} + x^{14} + x^{10} + x^{8} + x^{7} + "
      "x^{4} + x^{3} + 1 (0x4599, initial value 0), giving a Hamming "
      "distance of 6 for classic frame lengths. The stuffing is then applied "
      "to the whole bit string including the CRC. The RTL below implements "
      "all three blocks as serial one-bit-per-clock engines, exactly as a "
      "CAN controller does:")
    _v("can", "CAN CRC-15 generator, bit stuffer and destuffer with "
       "stuff-error detection.")
    _v("tb_can", "Testbench: a base data frame with ID 123h, DLC 2, data "
       "00 FFh. The CRC is computed, the frame stuffed, destuffed and "
       "compared; then one stuff bit is corrupted.")
    _o("can", "Real Icarus Verilog output: CRC-15 = 63E6h; 50 bits become "
       "55 on the wire; destuffing restores the original; a corrupted "
       "stuff bit produces a stuff error.")
    _v("py_can", "An independent Python reference: the same frame, CRC by "
       "shift register and by polynomial long division, and the stuffed bit "
       "string.")
    _o("py_can", "Python output - identical CRC (by two methods) and "
       "identical stuffed bit string to the Verilog run.")
    p("Look at where the stuff bits fell: after the five zeros of RTR, IDE, "
      "r0 and the first two DLC bits; in the 00h data byte; inside the FFh "
      "byte; across the boundary between the FFh byte and the CRC; and "
      "inside the CRC itself. Worst-case stuffing adds one "
      "bit per four after the first five, so frame length - and therefore "
      "worst-case latency - depends on the data, a subtlety that schedule "
      "analyses must include.")
    box("warn", "PITFALL: the stuffing boundary and the CRC delimiter",
        "Stuffing covers SOF through the **CRC sequence** only; the CRC "
        "delimiter, ACK field and EOF are fixed-form and never stuffed. A "
        "controller that keeps stuffing into the delimiter, or whose "
        "destuffer still counts the last CRC bits into the delimiter, fails "
        "interoperability tests in a data-dependent way - exactly the kind "
        "of bug that random-data simulation finds and directed tests miss.")

    h2("Bit timing")
    p("Each bit is divided into **time quanta** (TQ) derived from the "
      "controller clock by a baud-rate prescaler: TQ = BRP / f_clk. A bit "
      "time consists of four segments:")
    diagram([
        "  |<------------------------------ one bit time ----------------------------->|",
        "  +------+--------------------+------------------------+----------------------+",
        "  | SYNC |     PROP_SEG       |      PHASE_SEG1        |     PHASE_SEG2       |",
        "  | 1 TQ | compensates bus +  | can be lengthened by   | can be shortened by  |",
        "  |      | transceiver delay  | resynchronization      | resynchronization    |",
        "  +------+--------------------+------------------------+----------------------+",
        "  ^ edge expected here                                 ^ SAMPLE POINT",
    ], "CAN bit timing. The sample point sits between PHASE_SEG1 and "
       "PHASE_SEG2, typically at 75-87.5 % of the bit.")
    bul(["**Hard synchronization** on the SOF edge restarts the bit timing.",
         "**Resynchronization** on every recessive-to-dominant edge: if the "
         "edge falls in PHASE_SEG1 it is lengthened, if in PHASE_SEG2 it is "
         "shortened, by at most the **SJW** (synchronization jump width, "
         "1-4 TQ classically).",
         "**PROP_SEG** must cover twice the one-way delay (bus plus "
         "transceiver), because during arbitration and ACK a node must see "
         "the far node's dominant bit before its own sample point.",
         "A later sample point tolerates more propagation delay; an earlier "
         "one tolerates more oscillator error. Automotive practice (CiA "
         "recommendations) favours about 87.5 %."])
    eq(["f_clk = 80 MHz, target 500 kbit/s  ->  160 clocks per bit",
        "BRP = 10  ->  TQ = 125 ns ;  16 TQ per bit",
        "SYNC = 1, PROP_SEG + PHASE_SEG1 = 13, PHASE_SEG2 = 2  ->  sample at 14/16 = 87.5 %",
        "SJW = 2 TQ"],
       "A worked bit-timing configuration.")

    h2("Error detection and fault confinement")
    tbl(["Error", "Detected by", "How"],
        [["Bit error", "Transmitter", "Reads back a different value than "
          "it sent (outside arbitration and the ACK slot)"],
         ["Stuff error", "Receivers", "Six equal bits in a stuffed field"],
         ["CRC error", "Receivers", "Computed CRC differs from received"],
         ["Form error", "Receivers", "A fixed-form bit (delimiter, EOF) has "
          "the wrong value"],
         ["ACK error", "Transmitter", "Nobody pulled the ACK slot dominant"]],
        widths=[16, 20, 64], bold_first=True)
    p("A node that detects an error transmits an **error flag**. In the "
      "normal **error-active** state this is six **dominant** bits, which "
      "deliberately violates stuffing so every other node also detects an "
      "error and discards the frame - a global, consistent rejection; the "
      "transmitter then retries automatically. To stop a faulty node from "
      "destroying all traffic, each node keeps two counters:")
    diagram([
        "  TEC (transmit error counter): +8 per transmit error, -1 per successful frame",
        "  REC (receive error counter):  +1 per receive error (+8 in some cases), -1 per good",
        "",
        "            TEC or REC > 127                 TEC > 255",
        "  +--------------+ ---------> +---------------+ ----------> +-----------+",
        "  | ERROR ACTIVE |            | ERROR PASSIVE |             |  BUS-OFF  |",
        "  | flags: 6 dom |<---------  | flags: 6 rec, |             | no TX/RX  |",
        "  +--------------+ both<=127  | extra 8-bit   |             +-----+-----+",
        "        ^                     | suspend TX    |                   |",
        "        |                     +---------------+                   |",
        "        +------ 128 x 11 consecutive recessive bits (+ SW request) +",
    ], "CAN fault confinement.")
    p("An **error-passive** node's flag is six **recessive** bits, which "
      "cannot disturb other nodes' frames, and it must wait an extra "
      "suspend-transmission time before retrying. A node whose TEC exceeds "
      "255 goes **bus-off** and stops participating until it has seen 128 "
      "occurrences of 11 recessive bits (and, in most controllers, "
      "software has requested recovery). The asymmetric +8/-1 weighting "
      "means a node with a broken transmitter removes itself quickly while "
      "occasional noise is forgiven.")

    h2("CAN FD")
    p("CAN FD (flexible data rate; Bosch 2012, in ISO 11898-1:2015) keeps "
      "arbitration at the classic nominal rate but can switch to a faster "
      "**data phase** and carries up to **64 bytes**:")
    diagram([
        "  |SOF|ID..|RRS|IDE|FDF|res|BRS|ESI|DLC|  DATA 0-64 B  |SC|  CRC-17/21  |CD|ACK|..",
        "  |<--- nominal bit rate (e.g. 500k) --->|<--- data bit rate (e.g. 2-5M) -->|<-nominal",
        "                          switch at BRS sample point ^   switch back at CRC delimiter ^",
    ], "CAN FD base frame. FDF (recessive) marks an FD frame at the old r0 "
       "position; BRS selects the fast data phase; ESI reports the "
       "transmitter's error-passive state; SC is the stuff count.")
    tbl(["DLC", "0-8", "9", "10", "11", "12", "13", "14", "15"],
        [["Bytes (CAN FD)", "0-8", "12", "16", "20", "24", "32", "48",
          "64"]],
        widths=[20, 10, 10, 10, 10, 10, 10, 10, 10])
    bul(["**Longer CRCs**: CRC-17 for up to 16 data bytes, CRC-21 for more, "
         "to keep the Hamming distance at the longer lengths.",
         "**Stuff count and fixed stuff bits (ISO CAN FD)**: the original "
         "non-ISO FD had a flaw - a stuff bit corrupted in a way that "
         "shifted the frame could escape the CRC. ISO CAN FD adds a 3-bit "
         "Gray-coded stuff-bit count with parity before the CRC, and uses "
         "**fixed stuff bits** (one every four bits) inside the CRC field. "
         "Non-ISO and ISO FD are not interoperable - a configuration bit "
         "in controllers.",
         "**No remote frames** in FD (the RTR position becomes RRS, always "
         "dominant).",
         "**Transmitter delay compensation (TDC)**: at several Mbit/s the "
         "transceiver loop delay exceeds a data-phase bit, so the "
         "transmitter checks its own bits at a **secondary sample point** "
         "delayed by the measured loop delay.",
         "The data-phase rate is limited in practice by ringing on the "
         "bus topology; 2 Mbit/s is common, 5 Mbit/s with careful design; "
         "'SIC' (signal improvement capability) transceivers extend this."])

    h2("CAN XL")
    p("CAN XL (CiA 610-1, being standardized in ISO 11898-1/-2 revisions) "
      "is the third generation: data fields of **1 to 2048 bytes**, data "
      "phase rates of roughly 10-20 Mbit/s, an 11-bit priority ID for "
      "arbitration (kept separate from a 32-bit **acceptance field**), an "
      "SDU-type field that says what the payload carries (for example a "
      "tunnelled Ethernet frame), a virtual CAN network ID, and stronger "
      "CRCs (a header CRC and a 32-bit frame CRC). New transceivers "
      "switch to a different signalling mode during the data phase. Its "
      "purpose is to bridge the gap between CAN FD and 10BASE-T1S "
      "Ethernet in zonal vehicle architectures while keeping CAN's "
      "deterministic arbitration.")

    h2("LIN")
    p("LIN (Local Interconnect Network; LIN 2.x, standardized as ISO 17987) "
      "is a cheap single-wire, 12 V, UART-based sub-bus for up to about 16 "
      "nodes at up to 20 kbit/s (19.2 kbit/s is typical). One **commander** "
      "(master) node schedules all traffic; **responders** (slaves) never "
      "talk unsolicited. That determinism lets responders be tiny state "
      "machines, often with an RC oscillator instead of a crystal.")
    diagram([
        "  |<------------------ header (commander) ----------------->|<- response (a responder) ->|",
        "  +------------------+---+----------------+-----------------+------+------+ .. +--------+",
        "  | BREAK >= 13 bits | d | SYNC = 55h     | PID = ID + P0P1 | D0   | D1   |    |checksum|",
        "  |   dominant (0)   | l | (UART 8N1)     | (UART 8N1)      | 8N1  | 8N1  |    |  8N1   |",
        "  +------------------+---+----------------+-----------------+------+------+ .. +--------+",
        "                       ^ break delimiter >= 1 recessive bit;  1-8 data bytes",
    ], "A LIN frame. Every byte is a normal 8N1 UART character.")
    bul(["**Break**: at least 13 dominant bit times - longer than any legal "
         "character - so it cannot be confused with data; responders detect "
         "it as a UART break / framing error.",
         "**Sync byte 55h**: alternating bits let a responder measure the "
         "commander's bit time and trim its baud generator (auto-baud, "
         "Chapter 11): responders may be about +/-14 % off before sync and "
         "must be within about +/-2 % after.",
         "**Protected identifier**: 6-bit frame ID (0-59 signal frames, 60 "
         "= 3Ch commander request and 61 = 3Dh responder response for "
         "diagnostics, 62-63 reserved) plus two parity bits: P0 = ID0 ^ ID1 "
         "^ ID2 ^ ID4 and P1 = NOT(ID1 ^ ID3 ^ ID4 ^ ID5).",
         "**Checksum**: inverted 8-bit sum with end-around carry, over the "
         "data (**classic**, LIN 1.x and diagnostic frames) or over PID + "
         "data (**enhanced**, LIN 2.x)."])
    _v("py_lin", "LIN PID parity and checksums (Python 3).")
    _o("py_lin", "Real Python output. The classic checksum E6h for data 4A "
       "55 93 E5 matches the worked example in the LIN specification; PID "
       "3Ch/7Dh are the familiar diagnostic identifiers.")
    p("In an SoC, LIN is almost always a mode of the UART (Chapter 11): "
      "break generation and detection, sync-field measurement for "
      "auto-baud, header/response timeouts and checksum hardware are added "
      "to a normal UART, with a LIN transceiver on the board.")

    h2("FlexRay")
    p("FlexRay (FlexRay Consortium, 2000s; ISO 17458) was designed for "
      "deterministic, fault-tolerant x-by-wire systems: 10 Mbit/s on each "
      "of **two channels** (A and B), which carry either redundant copies "
      "or different data. Communication is **time-triggered**: a global "
      "time base is maintained by clock synchronization, and a repeating "
      "communication cycle (typically 1-5 ms, counted 0-63) is divided "
      "into:")
    diagram([
        "  |<---------------------------- communication cycle n ---------------------->|",
        "  +--------------------------------+------------------------+--------+-------+",
        "  | STATIC SEGMENT                 | DYNAMIC SEGMENT        | SYMBOL | NIT   |",
        "  | slot1 | slot2 | slot3 | ...    | minislots (FTDMA):     | WINDOW | clock |",
        "  | fixed TDMA slots, each owned   | priority by frame ID,  |        | corr. |",
        "  | by one node: guaranteed timing | event-driven traffic   |        |       |",
        "  +--------------------------------+------------------------+--------+-------+",
        "  frame: header 5 B (flags, 11-bit frame ID, 7-bit length in words, 11-bit header",
        "         CRC, 6-bit cycle count) | payload 0-254 B | 24-bit frame CRC",
    ], "The FlexRay cycle and frame.")
    p("FlexRay's cost and complexity (bus guardians, star couplers, precise "
      "configuration of the whole cluster) limited it mostly to premium "
      "chassis applications; new designs use CAN FD/XL and time-sensitive "
      "Ethernet instead. It remains an excellent example of a TDMA "
      "protocol and of time-triggered architecture.")

    h2("Automotive Ethernet")
    tbl(["Standard", "Rate", "Encoding / medium", "Notes"],
        [["**100BASE-T1** (IEEE 802.3bw)", "100 Mbit/s full duplex",
          "PAM3 at 66.7 MBd, one unshielded twisted pair, ~15 m",
          "Origin: BroadR-Reach; the workhorse of in-vehicle Ethernet"],
         ["**1000BASE-T1** (802.3bp)", "1 Gbit/s full duplex", "PAM3 at "
          "750 MBd, one pair, 15 m (type A) / 40 m (type B)", "Cameras, "
          "ADAS, backbone"],
         ["**10BASE-T1S** (802.3cg)", "10 Mbit/s half duplex", "Differential "
          "Manchester, **multidrop** (at least 8 nodes over 25 m)",
          "**PLCA** (physical layer collision avoidance) gives each node a "
          "transmit opportunity in turn: deterministic, CAN-like buses"],
         ["10BASE-T1L (802.3cg)", "10 Mbit/s", "PAM3, point-to-point, up to "
          "1 km", "Industrial / process automation (Ethernet-APL)"],
         ["2.5/5/10GBASE-T1 (802.3ch)", "multi-gigabit", "PAM4, one pair",
          "Sensor and backbone links"]],
        widths=[24, 16, 32, 28], bold_first=True)
    p("Full-duplex twisted-pair PHYs use echo cancellation to send and "
      "receive on one pair simultaneously (Chapter 19 covers Ethernet PHYs "
      "and the xMII interfaces to the MAC). Vehicles add **TSN** "
      "(IEEE 802.1AS time synchronization, 802.1Qbv scheduled traffic, "
      "and related standards) for bounded latency, and MACsec (802.1AE) "
      "for security. The trend is **zonal architectures**: a few zone "
      "controllers on an Ethernet backbone, each bridging to local CAN FD/"
      "XL, LIN and 10BASE-T1S segments.")

    h2("Industrial buses in brief")
    tbl(["Protocol", "Layer", "Key idea"],
        [["Modbus RTU / TCP", "RS-485 / TCP port 502", "Simple register "
          "read/write polling (Chapter 11)"],
         ["PROFIBUS DP", "RS-485, up to 12 Mbit/s", "Cyclic master-slave "
          "token-passing fieldbus"],
         ["PROFINET RT / IRT", "Ethernet", "RT: prioritized frames; IRT: "
          "scheduled, time-synchronized cut-through switching in dedicated "
          "ASICs for sub-millisecond cycles"],
         ["EtherCAT", "Ethernet", "One frame visits every slave in a "
          "logical ring; each slave controller (ESC) reads and inserts its "
          "data **on the fly** as the frame passes, with distributed clocks "
          "for sub-microsecond synchronization"],
         ["EtherNet/IP", "Ethernet, TCP/UDP", "CIP object model over "
          "standard Ethernet"],
         ["IO-Link", "3-wire 24 V point-to-point", "Smart sensor/actuator "
          "link to a master (4.8/38.4/230.4 kbit/s)"]],
        widths=[20, 24, 56], bold_first=True)
    box("note", "Why these matter to SoC designers",
        "Industrial and automotive SoCs integrate these controllers directly: "
        "CAN FD controllers with message RAM, EtherCAT slave controllers, "
        "TSN-capable Ethernet MACs, LIN-capable UARTs. The protocol engines "
        "are often licensed IP (for example the widely used Bosch M_CAN "
        "CAN FD IP), and the integrator's work is the bus interface, "
        "message RAM with ECC, interrupts, timestamps and safety "
        "mechanisms.")

    h2("A CAN controller in an SoC")
    diagram([
        "  AXI/APB  +-------------+   +----------------------+   +-------------------+",
        "  <------->| registers   |   | message RAM (ECC)    |   | protocol engine   |",
        "           | interrupts  |<->| TX buffers / FIFOs   |<->| bit timing, sync  |",
        "  IRQ <----| timestamps  |   | RX FIFOs, filters    |   | stuff/destuff     |--TXD-->",
        "           +-------------+   | (ID/mask, ranges)    |   | CRC, arbitration  |<-RXD---",
        "                             +----------------------+   | TEC/REC, FD, TDC  |",
        "                                                        +-------------------+",
    ], "Structure of a CAN FD controller (transceiver external).")
    bul(["**Acceptance filtering** in hardware (ID/mask pairs, ranges) keeps "
         "the CPU from seeing every frame on a busy bus.",
         "**TX prioritization**: the controller must always offer the "
         "highest-priority pending message to arbitration, not the oldest - "
         "a FIFO-only TX queue causes **priority inversion**.",
         "**Timestamps** at SOF or EOF for time synchronization and "
         "diagnostics.",
         "**Safety** (Chapter 26): ECC on message RAM, loopback and bus "
         "monitoring self-tests, protected configuration registers.",
         "**DV**: a CAN VIP that injects every error type at every bit "
         "position, random stuffing-heavy data, arbitration with many nodes, "
         "and bit-timing tolerance (oscillator offsets, propagation delay); "
         "ISO 16845 defines conformance test plans for CAN controllers."])

    h2("Summary")
    bul(["CAN uses a differential wired-AND bus: dominant 0 overrides "
         "recessive 1, enabling non-destructive bitwise arbitration in "
         "which the lowest ID wins (demonstrated in RTL).",
         "Classic frames: SOF, 11/29-bit ID, RTR, IDE, DLC, 0-8 bytes, "
         "CRC-15, ACK, EOF; stuffing after five equal bits from SOF to the "
         "end of the CRC. The Verilog CRC-15 (63E6h) and stuffed stream "
         "matched a Python reference exactly.",
         "Bit timing: TQ from a prescaler; SYNC + PROP + PHASE1 + PHASE2; "
         "sample point ~75-87.5 %; resynchronization limited by SJW.",
         "Fault confinement: TEC/REC counters, error-active, error-passive "
         "(> 127) and bus-off (TEC > 255) states.",
         "CAN FD: up to 64 bytes, bit-rate switch, CRC-17/21, stuff count; "
         "CAN XL: up to 2048 bytes and ~10-20 Mbit/s.",
         "LIN: commander-scheduled UART frames with break, 55h sync, "
         "parity-protected ID and checksum; FlexRay: dual-channel TDMA; "
         "automotive Ethernet: 100BASE-T1, 1000BASE-T1, 10BASE-T1S (PLCA "
         "multidrop); industrial: Modbus, PROFINET, EtherCAT and others."])

    h2("Exercises")
    bul(["Three nodes start simultaneously with IDs 0x3A5, 0x3A4 and 0x1FF. "
         "Which wins, and at which ID bit does each loser drop out?",
         "Compute the worst-case number of stuff bits for a classic base "
         "frame with 8 data bytes, and the resulting worst-case frame time "
         "at 500 kbit/s including the 3-bit intermission.",
         "Choose BRP and segment lengths for 1 Mbit/s from a 40 MHz clock "
         "with a sample point near 80 %. What SJW would you pick?",
         "Modify `can_stuff`/`can_destuff` for the ISO CAN FD CRC field "
         "(fixed stuff bit every 4 bits, always the complement of the "
         "previous bit). Why can a fixed-position stuff bit not be lost "
         "undetected?",
         "Starting from error-active, how many consecutive transmit errors "
         "drive a node bus-off? How many to become error-passive?",
         "Compute the LIN PID and enhanced checksum for frame ID 0x22 with "
         "data 01 02 03 using the Python model, then verify by hand."],
        ordered=True)


# ---------------------------------------------------------------- Ch 16 ---
def _ch16():
    chapter("Audio and Miscellaneous Links: I2S, TDM, PDM, S/PDIF, 1-Wire, "
            "MDIO and SWD")
    p("The last low-speed chapter collects a family of small but "
      "ubiquitous serial links. Digital audio uses its own clocked serial "
      "formats (I2S, TDM, PDM) inside the box and a self-clocked one "
      "(S/PDIF) between boxes. 1-Wire reaches ID chips and temperature "
      "sensors with a single wire, MDIO/MDC configures Ethernet PHYs, and "
      "SWD gives a debugger a two-wire path into an Arm SoC. Each teaches "
      "something distinct: continuous streaming with frame alignment, "
      "decimation of a 1-bit stream, biphase-mark self-clocking, "
      "time-slot signalling, turnaround cycles and packet-based debug "
      "access.")

    h2("I2S: the inter-IC sound bus")
    p("I2S (Philips, 1986) carries PCM audio between an SoC's audio "
      "interface and codecs, DACs, ADCs and amplifiers. It is a continuous "
      "stream, not a transaction bus - there is no address and no idle "
      "time. Three (or four) signals:")
    tbl(["Signal", "Also called", "Function"],
        [["SCK", "BCLK, bit clock", "One cycle per data bit: 64 x fs for "
          "two 32-bit slots, e.g. 3.072 MHz at 48 kHz"],
         ["WS", "LRCLK, frame clock", "Word select: 0 = left, 1 = right; "
          "runs at the sample rate fs"],
         ["SD", "SDATA, DIN/DOUT", "Two's-complement samples, MSB first; "
          "changes on the falling SCK edge, sampled on the rising edge"],
         ["MCLK", "system/master clock", "Optional oversampling clock for "
          "the codec's converters, typically 256 x fs (12.288 MHz at 48 "
          "kHz, 11.2896 MHz at 44.1 kHz)"]],
        widths=[12, 22, 66], bold_first=True)
    diagram([
        "  SCK  _/~\\_/~\\_/~\\_/~\\_/~\\_/ .. \\_/~\\_/~\\_/~\\_/~\\_/~\\_/ .. \\_/~\\_/~\\_/~\\_",
        "  WS   ~~~~\\_______________________ .. _______/~~~~~~~~~~~~~~~ .. ~~~~~~~~~\\___",
        "  SD   ==X  0  X MSB X B14 X .. X B0 X  0  X .. X  0  X MSB X B14 .. X  0  X MSB",
        "          last  <-- left: 16 data bits, 16 zeros -->  <-- right word ...",
        "          bit of the previous right slot",
        "  WS changes one SCK before the MSB: the MSB is delayed by one bit clock",
    ], "Philips I2S format (16-bit samples in 32-bit slots). The receiver "
       "does not need to know the word length: it takes the MSB after each "
       "WS edge and ignores or zero-fills extra bits.")
    p("Two common variants differ only in alignment, and a mismatch "
      "produces loud, distorted audio (samples shifted by one bit, or "
      "left/right swapped) rather than silence, which makes it easy to "
      "misdiagnose:")
    tbl(["Format", "MSB position", "WS polarity", "Notes"],
        [["**I2S (Philips)**", "One SCK after the WS edge", "0 = left",
          "Default for most codecs"],
         ["**Left-justified**", "Coincident with the WS edge", "Usually "
          "1 = left", "No one-bit delay; word length need not be known"],
         ["**Right-justified**", "LSB coincides with the end of the slot",
          "Usually 1 = left", "Receiver **must** know the word length "
          "(16/20/24) to find the MSB"]],
        widths=[20, 30, 18, 32], bold_first=True)
    p("The transmitter and receiver below implement the Philips format "
      "with 32-bit slots and a width parameter W. The transmitter is the "
      "clock master (it generates SCK = clk/2 and WS); the receiver lives "
      "entirely in the SCK domain, as codec receivers do, and aligns "
      "itself on WS transitions.")
    _v("i2s", "Parameterized I2S transmitter (clock master) and receiver. "
       "The WS edge is issued one bit before each slot; the receiver "
       "treats the bit sampled with a new WS value as the last bit of the "
       "previous word.")
    _v("tb_i2s", "Testbench: 16-bit and 24-bit transmitter/receiver pairs "
       "streaming stereo samples, a self-checking scoreboard and a trace of "
       "WS/SD for one frame.")
    _o("i2s", "Real Icarus Verilog output: both widths stream without "
       "error. In the trace, WS is 0 for 31 bits, 1 for 32 bits and 0 "
       "again one bit before the next left word; SD carries 9B27h "
       "(left) from the bit after the WS edge, then 4321h (right) from bit 32.")
    box("warn", "PITFALL: the first frame and word alignment",
        "The receiver discards everything before the first WS edge it sees "
        "(it cannot know where a word began), which is why the testbench "
        "starts scoring at frame 1. Real systems see the same effect after "
        "every stream start or clock switch: DMA must be started so that "
        "channel 0 lands in the correct buffer position, or left and right "
        "are swapped for the whole session - a very common audio driver "
        "bug.")
    bul(["**Clocking** is the hard part of audio SoC design: 48 kHz and "
         "44.1 kHz families need two MCLK frequencies (or a fractional "
         "audio PLL), and jitter on MCLK/SCK directly degrades converter "
         "SNR.",
         "**Master/slave roles**: either the SoC or the codec can generate "
         "SCK/WS; when the codec is master, the SoC's I2S block runs in "
         "an external clock domain and its FIFOs cross to the bus clock.",
         "**Asynchronous sample-rate conversion (ASRC)** hardware bridges "
         "two audio domains whose clocks are not locked (e.g. Bluetooth "
         "audio to a local DAC)."])

    h2("TDM: many channels on one data line")
    p("TDM (time-division multiplexed) audio, sometimes called DSP mode, "
      "puts N channel slots into each frame. A **frame sync** (FSYNC) "
      "marks the start of the frame - either a one-bit pulse or a 50 % "
      "duty clock - and slots follow back to back. Eight 32-bit slots at "
      "48 kHz need a 12.288 MHz bit clock. DSP mode A starts the first "
      "slot one BCLK after the FSYNC edge (like I2S); mode B starts it "
      "on the same edge (like left-justified). TDM is standard for "
      "microphone arrays, multi-channel codecs, smart amplifiers (which "
      "also return current/voltage sense data in spare slots) and "
      "automotive audio.")
    diagram([
        "  FSYNC _/~\\_____________________________________________________/~\\____",
        "  BCLK  _/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/\\/",
        "  DATA  ---< slot 0 >< slot 1 >< slot 2 >< ... >< slot 7 >---< slot 0 >",
    ], "TDM framing (8 slots per frame, DSP mode A).")

    h2("PDM microphones and decimation")
    p("Almost every phone and laptop microphone is a MEMS device with a "
      "**PDM** (pulse-density modulation) output: an on-chip sigma-delta "
      "modulator produces a **1-bit stream** at a high rate (typically 1 to "
      "3.2 MHz; 3.072 MHz = 64 x 48 kHz), in which the density of 1s "
      "follows the audio waveform and the quantization noise is pushed to "
      "high frequencies. Two microphones share one data line: a SEL pin "
      "makes one drive data after the rising clock edge and the other after "
      "the falling edge, so the SoC samples both on alternate edges.")
    p("The SoC must **decimate**: low-pass filter away the shaped noise and "
      "reduce the rate by 64. The first stage is almost always a **CIC** "
      "(cascaded integrator-comb, Hogenauer) filter, because it needs no "
      "multipliers: N integrators at the input rate, a rate change by R, "
      "then N combs (differentiators) at the output rate. Its response is "
      "sinc^{N}, with droop in the passband that a following FIR "
      "compensates; half-band FIR stages complete the decimation.")
    eq(["H(z) = [ (1 - z^-RM) / (1 - z^-1) ]^N          (CIC, R = decimation, M = diff. delay)",
        "gain = (R x M)^N  ->  output width = input width + N x log2(R x M)",
        "example: 1-bit PDM, N = 5, R = 32, M = 1  ->  1 + 5 x 5 = 26-bit integrators",
        "PDM 3.072 MHz --CIC /32--> 96 kHz --half-band FIR /2--> 48 kHz PCM --> I2S/DMA"],
       "CIC decimator sizing. Integrators rely on two's-complement "
       "wrap-around: overflow in them is harmless as long as the registers "
       "are as wide as the output requires.")

    h2("S/PDIF and AES3: self-clocked audio between boxes")
    p("S/PDIF (consumer, IEC 60958 Type II, over 75 ohm coax or optical "
      "TOSLINK) and AES3 (professional, 110 ohm balanced) carry stereo PCM "
      "(or compressed IEC 61937 streams) over **one** signal with no "
      "separate clock. They use **biphase mark coding (BMC)**: every bit "
      "cell begins with a transition, and a 1 has an extra transition in "
      "the middle. The signal is DC-free, polarity-insensitive, and the "
      "receiver recovers the clock with a PLL.")
    diagram([
        "  data      1     0     1     1     0     0     1",
        "  cells   |  .  |  .  |  .  |  .  |  .  |  .  |  .  |",
        "  BMC     ~~~___~~~~~~___~~~___~~~______~~~~~~___~~~",
        "          every cell starts with a transition; a 1 also toggles mid-cell",
        "",
        "  subframe (32 time slots):",
        "  | 0-3      | 4-7 | 8 ......................... 27 | 28 | 29 | 30 | 31 |",
        "  | preamble | aux | audio sample, LSB first (20 b)  | V  | U  | C  | P  |",
        "  preamble B/Z = channel A + block start, M/X = channel A, W/Y = channel B",
        "  (preambles deliberately violate BMC so they can never occur in data)",
        "  frame = 2 subframes; block = 192 frames -> 192-bit channel-status word from C",
    ], "Biphase-mark coding and the IEC 60958 subframe. Aux bits extend "
       "the sample to 24 bits. P gives even parity over slots 4-31.")
    p("The bit rate is 64 x fs (3.072 Mbit/s at 48 kHz), so the BMC cell "
      "rate is 128 x fs. A receiver in RTL oversamples the input, measures "
      "pulse widths (one, two or three half-cells - three only occurs in "
      "preambles), locks to the preambles, and extracts the samples; the "
      "channel-status block carries the sample rate, copy protection and "
      "whether the payload is PCM or compressed.")

    h2("1-Wire")
    p("Maxim's (now Analog Devices') 1-Wire bus uses **one** open-drain "
      "data line plus ground; devices can even be **parasitically powered** "
      "from the pull-up. Timing is everything: the master starts every "
      "slot by pulling the line low, and the **duration** of the low pulse "
      "encodes the information.")
    diagram([
        "  reset/presence:",
        "  master  ~~~\\______________ >= 480 us _______________/~~~~~~~~~~~~~~~~~~~~~~~~~",
        "  slave                                                  15-60 us \\_ 60-240 us _/",
        "",
        "  write 1:  ~~\\__/~~~~~~~~~~~~~~~~~~~~~~~~~   low 1-15 us, then release",
        "  write 0:  ~~\\________________________/~~~   low 60-120 us",
        "  read:     ~~\\__/  slave holds low (0) or not (1); master samples within 15 us",
        "              |<------------ time slot 60-120 us ------------>| recovery >= 1 us",
    ], "1-Wire standard-speed signalling (overdrive speed is roughly ten "
       "times faster).")
    bul(["**Reset/presence**: every transaction starts with a reset pulse; "
         "any device answers with a presence pulse.",
         "**ROM commands** select devices: Read ROM (33h, single device), "
         "Match ROM (55h + 64-bit ROM), Skip ROM (CCh, all devices), "
         "**Search ROM (F0h)** and Alarm Search (ECh). Search ROM walks "
         "the binary tree of all ROM codes: for each bit, all devices send "
         "the bit and its complement (wired-AND reveals whether both values "
         "exist) and the master chooses a branch - the same wired-AND trick "
         "as I2C and CAN arbitration.",
         "**Function commands** are device-specific (a DS18B20 "
         "thermometer uses 44h Convert T and BEh Read Scratchpad).",
         "Every device has a unique **64-bit ROM**: 8-bit family code, "
         "48-bit serial number and an 8-bit **CRC**, all sent LSB first."])
    p("The 1-Wire CRC-8 (often called 'Dallas/Maxim CRC') uses the "
      "polynomial x^{8} + x^{5} + x^{4} + 1 with the register shifting "
      "right (LSB first, reflected polynomial 8Ch) and initial value 0. "
      "Running the CRC over all 8 ROM bytes, including the stored CRC, "
      "gives 0 for a valid code.")
    _v("ow", "Serial 1-Wire CRC-8, one bit per clock, LSB first.")
    _v("tb_ow", "Testbench: the example ROM code from Maxim's application "
       "note on 1-Wire CRCs, a DS18B20-style code, and a code whose CRC "
       "byte has been corrupted.")
    _o("ow", "Real Icarus Verilog output: CRC(7 bytes) equals the stored "
       "byte for the valid codes and CRC(8 bytes) = 00h; the corrupted "
       "code is flagged.")
    _v("py_ow", "Python reference for the same CRC.")
    _o("py_ow", "Python output: A2h, 30h and 2Bh - identical to the "
       "Verilog results (A2h is also the value published in Maxim's "
       "application note for that ROM code).")

    h2("MDIO / MDC: managing Ethernet PHYs")
    p("Every Ethernet MAC configures and monitors its PHY over the "
      "**management interface** defined in IEEE 802.3: MDC (clock, driven "
      "by the MAC-side station management entity, STA) and MDIO "
      "(bidirectional data, with a pull-up). It is also called MIIM or "
      "**SMI** (serial management interface). Up to 32 PHY addresses share "
      "one bus. 802.3 specifies MDC up to 2.5 MHz; many PHYs accept "
      "faster clocks. Data is sampled on the rising edge of MDC.")
    diagram([
        "  Clause 22:",
        "  | PRE (32 x 1) | ST 01 | OP | PHYAD[4:0] | REGAD[4:0] | TA | DATA[15:0] | idle Z |",
        "       OP: 01 = write, 10 = read      TA: write = 10 (STA drives)",
        "                                          read  = Z0 (PHY drives 0 in 2nd bit)",
        "",
        "  Clause 45 (indirect, 16-bit register space per device):",
        "  | PRE | ST 00 | OP | PRTAD[4:0] | DEVAD[4:0] | TA | ADDRESS or DATA[15:0] |",
        "       OP: 00 = address, 01 = write, 11 = read, 10 = read + post-increment",
    ], "MDIO frame formats. The turnaround (TA) gives the bus one bit time "
       "to change driver on reads.")
    bul(["Clause 22 has 32 registers per PHY: 0 control (reset, loopback, "
         "speed, auto-negotiation enable), 1 status (link, AN complete), "
         "2-3 PHY identifier, 4-5 auto-negotiation advertisement and "
         "link-partner ability, 9-10 1000BASE-T control/status, 15 "
         "extended status.",
         "Clause 45 addresses a port, an **MMD** (MDIO manageable device, "
         "e.g. 1 = PMA/PMD, 3 = PCS, 7 = auto-negotiation) and a 16-bit "
         "register address - needed for 10G and multi-gig PHYs. A write "
         "or read is two frames: an address frame, then a data frame.",
         "RTL is simple: a shift register and a small FSM. The traps are "
         "the tri-state turnaround, sampling MDIO read data late enough "
         "after the MDC rising edge (the PHY may drive up to ~300 ns after "
         "it), and exclusive access when several software agents poll "
         "the PHY."])

    h2("SWD as a two-wire serial link")
    p("Arm's **Serial Wire Debug** replaces the four or five JTAG pins "
      "with SWCLK and a bidirectional SWDIO. It is a packet protocol with "
      "turnaround cycles, much like MDIO:")
    diagram([
        "  | Start=1 | APnDP | RnW | A[2:3] | Parity | Stop=0 | Park=1 | Trn | ACK[0:2] | Trn |",
        "  |<-------------------- 8-bit request (host) -------------->|     |<- target->|",
        "  then 32 data bits LSB first + 1 parity bit (from host on writes, target on reads)",
        "  ACK: OK = 001b, WAIT = 010b, FAULT = 100b  (bit 0 first on the wire)",
        "  line reset: >= 50 SWCLK cycles with SWDIO high",
    ], "An SWD transaction. Chapter 23 covers the Debug Access Port behind "
       "it, JTAG-to-SWD switching and CoreSight.")
    p("The protocol shows the recurring ideas of this part: a request "
      "protected by parity, an explicit turnaround when the direction "
      "changes, a three-bit acknowledgement that can ask the host to "
      "retry (WAIT - flow control) and a line reset of many 1s that "
      "recovers from any state. Its details, the debug port register "
      "model and the SoC debug architecture are in Chapter 23.")

    h2("GPIO bit-banging")
    p("Any of the protocols in this part can be generated by software "
      "toggling GPIOs - useful for bring-up, for a protocol no controller "
      "supports, or for bus recovery (the nine I2C clocks of Chapter 13 "
      "are often bit-banged). The limitations are timing and CPU cost:")
    bul(["Interrupts, cache misses and bus contention add jitter of "
         "microseconds; fine for I2C at 100 kHz or 1-Wire (with interrupts "
         "masked during a slot), hopeless for I2S or SPI at tens of MHz.",
         "GPIO registers are usually behind a slow peripheral bus; "
         "set/clear or bit-band registers avoid read-modify-write races "
         "between contexts.",
         "Open-drain protocols need the pin configured as open-drain (or "
         "emulated by toggling the output enable with the data fixed at 0).",
         "Many SoCs therefore include **programmable I/O engines** - small "
         "state machines with shift registers and cycle-exact timing "
         "(RP2040-style PIO, or timer-triggered DMA to GPIO) - which "
         "implement custom or legacy protocols in 'software' without "
         "CPU jitter."])

    h2("Where these blocks sit in an SoC")
    tbl(["Block", "Typical integration", "Owner concerns"],
        [["I2S/TDM/PDM", "Audio subsystem with its own DMA, audio PLL, "
          "often a DSP; always-on for voice wake-up", "Clock domains, "
          "jitter, FIFO depth vs. latency, low-power listening"],
         ["S/PDIF", "TV/set-top/AV-receiver SoCs, HDMI audio paths",
          "Clock recovery PLL, channel-status handling"],
         ["1-Wire", "Accessory/battery authentication, board ID; often a "
          "small controller or bit-banged", "Precise slot timing; strong "
          "pull-up for parasitic power"],
         ["MDIO", "Part of the Ethernet MAC subsystem", "Shared bus "
          "arbitration between MAC instances and software agents"],
         ["SWD", "Debug subsystem (DAP)", "Security: debug authentication "
          "and lock-out in production parts"]],
        widths=[16, 44, 40], bold_first=True)

    h2("Summary")
    bul(["I2S streams PCM on SCK/WS/SD (plus MCLK); Philips format delays "
         "the MSB one bit after WS, left-justified does not, and "
         "right-justified needs the word length. Our 16- and 24-bit RTL "
         "pairs streamed error-free.",
         "TDM packs N slots per frame behind a frame sync; PDM carries 1-bit "
         "sigma-delta audio that the SoC decimates with CIC and FIR "
         "filters.",
         "S/PDIF/AES3 are self-clocked with biphase mark coding; 32-slot "
         "subframes with BMC-violating preambles; 192-frame blocks carry "
         "channel status.",
         "1-Wire encodes bits in low-pulse durations on one open-drain wire; "
         "ROM commands and the Search ROM algorithm use wired-AND; its "
         "CRC-8 (x^8+x^5+x^4+1, LSB first) was verified in RTL against "
         "Python and the published example.",
         "MDIO/MDC manages Ethernet PHYs with clause 22 (ST=01) and "
         "clause 45 (ST=00) frames and a turnaround; SWD is a two-wire "
         "packet protocol with parity, turnaround, ACK/WAIT/FAULT and line "
         "reset.",
         "Bit-banging is fine for slow, jitter-tolerant links; programmable "
         "I/O engines give software flexibility with hardware timing."])

    h2("Exercises")
    bul(["A codec expects left-justified 24-bit data but the SoC sends "
         "Philips I2S. Describe exactly what the listener hears and why.",
         "Compute BCLK for 8-slot, 32-bit TDM at 96 kHz, and MCLK = 256 x fs "
         "for 44.1 kHz. Why do products often need two audio PLL settings?",
         "Size a CIC decimator (N = 4) that takes a 2.4 MHz PDM stream to "
         "75 kHz. What integrator width is needed, and where is the first "
         "passband droop compensated?",
         "Encode the byte 0xA5 (LSB first) in biphase-mark code starting from "
         "a high level, and show why the encoding is independent of wire "
         "polarity.",
         "Using the Python 1-Wire CRC model, find a single-bit error in the "
         "48-bit serial number that the CRC would not detect, or argue why "
         "none exists.",
         "Write the MDIO bit sequence (including preamble and turnaround) "
         "to read clause 22 register 1 of PHY address 3, and mark which "
         "side drives each bit."], ordered=True)
