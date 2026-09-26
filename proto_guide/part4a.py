"""Part IV (first half) - High-Speed and Memory Interfaces: Chapters 17-20.

Chapter 17 USB, 18 PCI Express and CXL, 19 Ethernet, 20 Memory interfaces.
Every Verilog/SystemVerilog design and testbench in SRC was compiled with
Icarus Verilog 12 (iverilog -g2012 -Wall) and simulated with vvp; the
synthesizable modules were also linted with Verilator 5.020 (-Wall). The
Python references in SRC were run with Python 3. OUT holds the captured
output verbatim (only the trailing "$finish called" line is omitted).
"""

from proto_guide.common import *  # noqa: F401,F403

# --- sources and REAL simulator / Python output (generated) ---
SRC = {
    'usb_line': r'''
// USB 2.0 FS/LS line coding: bit stuffing + NRZI (transmit) and the inverse (receive).
// line = 1 means J (idle), line = 0 means K (full-speed polarity).
module usb_nrzi_tx (
  input  logic clk, rst_n,
  input  logic in_valid, in_bit,    // raw bits, LSB of each byte first
  output logic in_ready,            // low for one cycle while a stuff bit is sent
  output logic line                 // 1 = J, 0 = K
);
  logic [2:0] ones;                 // consecutive 1s sent so far
  wire stuff = (ones == 3'd6);      // six 1s in a row: next bit on the wire is a 0
  assign in_ready = !stuff;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin ones <= '0; line <= 1'b1; end          // bus idles in J
    else if (stuff) begin ones <= '0; line <= ~line; end     // stuffed 0 = transition
    else if (in_valid) begin
      if (in_bit) ones <= ones + 3'd1;                       // 1 = no transition
      else begin  ones <= '0; line <= ~line; end             // 0 = transition
    end
endmodule

module usb_nrzi_rx (
  input  logic clk, rst_n,
  input  logic line_valid, line,    // one recovered sample per bit time
  output logic out_valid, out_bit,
  output logic stuff_err            // seventh consecutive 1 seen
);
  logic       prev;
  logic [2:0] ones;
  wire  bit_now = (line == prev);   // NRZI: no change = 1
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      prev <= 1'b1; ones <= '0; out_valid <= 0; out_bit <= 0; stuff_err <= 0;
    end
    else begin
      out_valid <= 1'b0; stuff_err <= 1'b0;
      if (line_valid) begin
        prev <= line;
        if (ones == 3'd6) begin                  // this bit must be a stuffed 0
          ones <= '0;
          stuff_err <= bit_now;                  // a 1 here is a bit-stuff error
        end else begin
          out_valid <= 1'b1; out_bit <= bit_now;
          ones <= bit_now ? ones + 3'd1 : 3'd0;
        end
      end
    end
endmodule''',
    'tb_usb_line': r'''
module tb;
  logic clk = 0, rst_n = 0;
  always #5 clk = ~clk;
  // SYNC, PID DATA0, then data with long runs of 1s
  localparam int N = 6;
  logic [8*N-1:0] tx = 48'h00_3F_7F_FF_C3_80;      // sent from the low byte up
  logic in_valid, in_bit, in_ready, line;
  logic out_valid, out_bit, stuff_err;
  usb_nrzi_tx utx (.*);
  logic lv = 0;                                 // line carries a bit this cycle
  always @(posedge clk) lv <= in_valid;
  usb_nrzi_rx urx (.clk, .rst_n, .line_valid(lv), .line, .out_valid, .out_bit, .stuff_err);
  string wire_s = "";
  int nbits = 0, rx_n = 0, stuffed = 0, errs = 0;
  logic [7:0] rx_sr, rx_bytes [N];
  // receive side: rebuild bytes (LSB first)
  always @(posedge clk) if (rst_n) begin
    if (lv) wire_s = {wire_s, line ? "J" : "K"};
    if (out_valid) begin
      rx_sr = {out_bit, rx_sr[7:1]};
      if (++nbits % 8 == 0) begin rx_bytes[rx_n] = rx_sr; rx_n++; end
    end
    if (stuff_err) errs++;
  end
  initial begin
    in_valid = 0; in_bit = 0;
    repeat (2) @(posedge clk); rst_n = 1;
    for (int b = 0; b < N; b++)                 // drive on the falling edge
      for (int i = 0; i < 8; i++) begin
        @(negedge clk);
        while (!in_ready) begin stuffed++; @(negedge clk); end
        in_valid = 1; in_bit = tx[8*b+i];
      end
    @(negedge clk); in_valid = 0;
    repeat (3) @(posedge clk);
    $display("wire: %s", wire_s);
    $display("payload bits=%0d  stuffed bits=%0d  stuff errors=%0d", N*8, stuffed, errs);
    $write("decoded bytes:");
    for (int b = 0; b < rx_n; b++) $write(" %02h", rx_bytes[b]);
    $display("");
    $finish;
  end
endmodule''',
    'usb_crc': r'''
// Bit-serial USB CRC5 (tokens) and CRC16 (data), fed with the bits in wire order
// (LSB of every byte first).  Seed all ones; the transmitter sends the complement,
// MSB first. A receiver that runs the CRC across data + CRC checks for the residual.
module usb_crc (
  input  logic        clk, init, en, din,
  output logic [4:0]  crc5,  output logic [15:0] crc16,    // raw LFSR state
  output logic [4:0]  crc5_tx, output logic [15:0] crc16_tx,
  output logic        crc5_ok, crc16_ok
);
  wire fb5  = din ^ crc5[4];
  wire fb16 = din ^ crc16[15];
  always_ff @(posedge clk)
    if (init) begin crc5 <= '1; crc16 <= '1; end
    else if (en) begin
      crc5  <= {crc5[3:0], 1'b0}  ^ (fb5  ? 5'h05    : 5'h00);    // x^5 + x^2 + 1
      crc16 <= {crc16[14:0], 1'b0} ^ (fb16 ? 16'h8005 : 16'h0000); // x^16+x^15+x^2+1
    end
  assign crc5_tx  = ~crc5;
  assign crc16_tx = ~crc16;
  assign crc5_ok  = (crc5  == 5'b01100);            // residual after a good token
  assign crc16_ok = (crc16 == 16'h800D);            // residual after a good data packet
endmodule''',
    'tb_usb_crc': r'''
module tb;
  logic clk = 0, init, en, din;
  logic [4:0] crc5, crc5_tx;  logic [15:0] crc16, crc16_tx;  logic crc5_ok, crc16_ok;
  usb_crc dut (.*);
  always #5 clk = ~clk;
  task automatic send(input logic [63:0] v, input int n);   // n bits, LSB first
    for (int i = 0; i < n; i++) begin
      @(negedge clk); en = 1; din = v[i];
    end
    @(negedge clk); en = 0;
  endtask
  task automatic reset_crc; @(negedge clk); init = 1; @(negedge clk); init = 0; endtask
  function automatic logic [15:0] rev(input logic [15:0] v, input int n);
    rev = 0; for (int i = 0; i < n; i++) rev[i] = v[n-1-i];
  endfunction
  logic [54:0] toks = {11'h001, 4'h4, 7'h70, 4'hA, 7'h3A, 4'hE, 7'h15, 11'h000};
  logic [10:0] tok;
  logic [63:0] setup = 64'h0040_0000_0100_0680;   // bytes 80 06 00 01 00 00 40 00
  logic [15:0] field;
  initial begin
    init = 0; en = 0; din = 0;
    for (int k = 0; k < 5; k++) begin
      tok = toks[11*k +: 11];
      reset_crc(); send(tok, 11);
      field = {rev(crc5_tx, 5), tok};              // CRC5 goes out MSB first
      $write("token addr=%02h endp=%h  crc5=%02h  bytes after PID: %02h %02h",
             tok[6:0], tok[10:7], crc5_tx, field[7:0], field[15:8]);
      send(rev(crc5_tx, 5), 5);                       // receiver view: data + crc
      $display("  rx residual ok=%0d", crc5_ok);
    end
    reset_crc(); send(setup, 64);
    field = rev(crc16_tx, 16);
    $write("DATA0 GET_DESCRIPTOR  crc16=%04h  CRC bytes on the wire: %02h %02h",
           crc16_tx, field[7:0], field[15:8]);
    send(field, 16);
    $display("  rx residual ok=%0d", crc16_ok);
    reset_crc(); send(setup ^ 64'h1_0000, 64); send(field, 16);  // one data bit flipped
    $display("same packet, one bit flipped:  rx residual ok=%0d", crc16_ok);
    $finish;
  end
endmodule''',
    'ref_usb': r'''
def stuff_nrzi(data):
    bits = [(b >> i) & 1 for b in data for i in range(8)]   # LSB first
    out, ones, level = [], 0, 1                               # idle J (=1)
    for bit in bits:
        if bit: ones += 1
        else:   ones, level = 0, level ^ 1
        out.append(level)
        if ones == 6:                                         # stuff a 0
            ones, level = 0, level ^ 1
            out.append(level)
    return "".join("J" if v else "K" for v in out), len(out) - len(bits)

def crc5(value, nbits=11):            # token: 7-bit addr + 4-bit endp, LSB first
    crc = 0x1F
    for i in range(nbits):
        fb = ((value >> i) & 1) ^ (crc >> 4)
        crc = ((crc << 1) & 0x1F) ^ (0x05 if fb else 0)
    return crc ^ 0x1F                 # complemented; sent MSB (c4) first

def crc16(data):
    crc = 0xFFFF
    for b in data:
        for i in range(8):
            fb = ((b >> i) & 1) ^ (crc >> 15)
            crc = ((crc << 1) & 0xFFFF) ^ (0x8005 if fb else 0)
    return crc ^ 0xFFFF

w, n = stuff_nrzi([0x80, 0xC3, 0xFF, 0x7F, 0x3F, 0x00])
print("wire:", w, " stuffed:", n)
print("crc5(SETUP addr 0 ep 0) = %02x" % crc5(0))
print("crc16(GET_DESCRIPTOR) = %04x" % crc16([0x80, 6, 0, 1, 0, 0, 0x40, 0]))''',
    'tlp_pkg': r'''
// PCIe TLP header builder (non-flit mode, as used through Gen5).
// A header is returned as 4 DWs packed {DW0, DW1, DW2, DW3}; DW0 goes first on the
// link, most-significant byte first. Fmt[0] = 1 marks a 4DW header.
package tlp_pkg;
  typedef logic [127:0] hdr_t;
  // byte0 = {Fmt,Type}  byte1 = {T9,TC,T8,Attr2,LN,TH}  byte2 = {TD,EP,Attr,AT,Len[9:8]}
  function automatic logic [31:0] dw0(input logic [2:0] fmt, input logic [4:0] typ,
                                      input logic [2:0] tc, input logic [9:0] len);
    return {fmt, typ, 1'b0, tc, 4'b0000, 1'b0, 1'b0, 2'b00, 2'b00, len};
  endfunction

  // MRd / MWr from a byte address and byte count: DW length and byte enables.
  // 3DW header below 4 GB, 4DW above (a 4DW header below 4 GB is not allowed).
  function automatic hdr_t mem_req(input bit wr, input logic [63:0] addr,
      input logic [12:0] nbytes, input logic [15:0] rid, input logic [7:0] tag);
    logic [63:0] last;  logic [9:0] len;  logic [3:0] fbe, lbe;  bit four;
    last = addr + nbytes - 1;
    len  = 10'(last[63:2] - addr[63:2] + 1);      // DWs touched (1024 encodes as 0)
    fbe  = 4'b1111 << addr[1:0];
    lbe  = 4'b1111 >> (2'd3 - last[1:0]);
    four = (addr[63:32] != 0);
    if (len == 1) begin fbe = fbe & lbe; lbe = 4'b0000; end   // single-DW request
    return {dw0({1'b0, wr, four}, 5'b00000, 3'd0, len), rid, tag, lbe, fbe,
            four ? {addr[63:32], addr[31:2], 2'b00} : {addr[31:2], 2'b00, 32'h0}};
  endfunction

  // Type 0 configuration read (CfgRd0: Fmt 000, Type 00100), always 1 DW
  function automatic hdr_t cfg_rd0(input logic [7:0] bus, input logic [4:0] dev,
      input logic [2:0] fn, input logic [11:0] reg_byte, input logic [15:0] rid,
      input logic [7:0] tag);
    return {dw0(3'b000, 5'b00100, 3'd0, 10'd1), rid, tag, 4'b0000, 4'b1111,
            bus, dev, fn, 4'b0000, reg_byte[11:2], 2'b00, 32'h0};
  endfunction

  // Completion with data (CplD: Fmt 010, Type 01010), status SC = 000, BCM = 0
  function automatic hdr_t cpld(input logic [15:0] cid, input logic [15:0] rid,
      input logic [7:0] tag, input logic [11:0] byte_cnt, input logic [6:0] lower_addr,
      input logic [9:0] len);
    return {dw0(3'b010, 5'b01010, 3'd0, len), cid, 3'b000, 1'b0, byte_cnt,
            rid, tag, 1'b0, lower_addr, 32'h0};
  endfunction
endpackage''',
    'tb_tlp': r'''
module tb;
  import tlp_pkg::*;
  task automatic show(input string name, input hdr_t h);
    int ndw = h[125] ? 4 : 3;                         // Fmt[0]: 4DW header
    $write("%-32s", name);
    for (int i = 0; i < ndw; i++) $write(" %08h", h[127 - 32*i -: 32]);
    $display("");
  endtask
  initial begin
    show("MWr32 F0000104, 8 B, tag 05",  mem_req(1, 64'hF000_0104, 8, 16'h0100, 8'h05));
    show("MRd32 80000002, 2 B, tag 06",  mem_req(0, 64'h8000_0002, 2, 16'h0100, 8'h06));
    show("MRd64 1234567801, 256 B",      mem_req(0, 64'h12_3456_7801, 256, 16'h0100, 8'h07));
    show("MRd32 00001000, 4096 B",       mem_req(0, 64'h1000, 4096, 16'h0100, 8'h08));
    show("CfgRd0 01:00.0 reg 010 (BAR0)", cfg_rd0(8'h01, 5'd0, 3'd0, 12'h010, 16'h0, 8'h09));
    show("CplD 4 B for tag 09",           cpld(16'h0100, 16'h0, 8'h09, 12'd4, 7'h10, 10'd1));
  end
endmodule''',
    'ref_tlp': r'''
def dw0(fmt, typ, tc, length):
    return (fmt << 29) | (typ << 24) | (tc << 20) | (length & 0x3FF)

def mem_req(wr, addr, nbytes, rid, tag):
    last = addr + nbytes - 1
    length = (last >> 2) - (addr >> 2) + 1
    fbe = (0xF << (addr & 3)) & 0xF
    lbe = 0xF >> (3 - (last & 3))
    if length == 1:
        fbe, lbe = fbe & lbe, 0
    four = addr >= 1 << 32
    h = [dw0((wr << 1) | four, 0, 0, length),
         (rid << 16) | (tag << 8) | (lbe << 4) | fbe]
    h += [addr >> 32, addr & ~3 & 0xFFFFFFFF] if four else [addr & ~3]
    return h

def cfg_rd0(bus, dev, fn, reg, rid, tag):
    return [dw0(0, 0b00100, 0, 1), (rid << 16) | (tag << 8) | 0xF,
            (bus << 24) | (dev << 19) | (fn << 16) | (reg & 0xFFC)]

def cpld(cid, rid, tag, bc, la, length):
    return [dw0(0b010, 0b01010, 0, length), (cid << 16) | bc, (rid << 16) | (tag << 8) | la]

rows = [mem_req(1, 0xF0000104, 8, 0x100, 5), mem_req(0, 0x80000002, 2, 0x100, 6),
        mem_req(0, 0x1234567801, 256, 0x100, 7), mem_req(0, 0x1000, 4096, 0x100, 8),
        cfg_rd0(1, 0, 0, 0x10, 0, 9), cpld(0x100, 0, 9, 4, 0x10, 1)]
for r in rows:
    print(" ".join("%08x" % d for d in r))''',
    'fc': r'''
// PCIe flow-control gate for one credit type (e.g. Posted Header or Posted Data).
// Counters are modulo 2^F; F = 8 for header and 12 for data credits (no scaling).
// A TLP needing `need` credits may go if
//   (CREDIT_LIMIT - (CREDITS_CONSUMED + need)) mod 2^F <= 2^F / 2
module fc_gate #(parameter int F = 8) (
  input  logic         clk, rst_n,
  input  logic         init_valid,   input logic [F-1:0] init_credits, // InitFC
  input  logic         upd_valid,    input logic [F-1:0] upd_limit,    // UpdateFC
  input  logic [F-1:0] need,
  input  logic         consume,                                        // TLP sent
  output logic         ok,
  output logic [F-1:0] limit, consumed
);
  logic [F-1:0] diff;
  assign diff = limit - (consumed + need);
  assign ok   = (diff <= F'(1 << (F-1)));
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n)          begin limit <= '0; consumed <= '0; end
    else begin
      if (init_valid)     limit <= init_credits;       // CL starts at the advertised value
      else if (upd_valid) limit <= upd_limit;          // receiver's new CREDITS_ALLOCATED
      if (consume)        consumed <= consumed + need;
    end
endmodule''',
    'tb_fc': r'''
// Posted writes from a transmitter to a receiver with 4 header / 32 data credits of
// buffer (32 x 16 B = 512 B). The receiver drains one TLP every 12 cycles and returns
// the freed credits with an UpdateFC that arrives 8 cycles later.
module tb;
  localparam int NTLP = 300;
  logic clk = 0, rst_n = 0;  always #5 clk = ~clk;
  logic init = 0, h_ok, d_ok, send;  logic [7:0] h_lim, h_cc;  logic [11:0] d_lim, d_cc;
  logic upd = 0;  logic [7:0] h_alloc = 4, h_upd;  logic [11:0] d_alloc = 32, d_upd;
  logic [11:0] dneed;
  fc_gate #(8)  gh (.clk, .rst_n, .init_valid(init), .init_credits(8'd4),
                    .upd_valid(upd), .upd_limit(h_upd), .need(8'd1), .consume(send),
                    .ok(h_ok), .limit(h_lim), .consumed(h_cc));
  fc_gate #(12) gd (.clk, .rst_n, .init_valid(init), .init_credits(12'd32),
                    .upd_valid(upd), .upd_limit(d_upd), .need(dneed), .consume(send),
                    .ok(d_ok), .limit(d_lim), .consumed(d_cc));
  function automatic int size(input int i);   // payload bytes, cycled
    return (i % 4 == 0) ? 64 : (i % 4 == 1) ? 256 : (i % 4 == 2) ? 128 : 512;
  endfunction
  int  dsum = 0, k = 0, sent = 0, stall = 0, cyc = 0, drained = 0;
  int  q_hdr = 0, q_dat = 0, max_hdr = 0, max_dat = 0;   // receiver buffer occupancy
  int  pend [$];                                          // data credits of queued TLPs
  int  upd_at [$], d;                                     // UpdateFC arrival times
  logic [19:0] upd_v [$];                                 // {hdr, data} it carries
  assign dneed = 12'((size(k) + 15) / 16);                // 1 data credit = 16 bytes
  assign send  = rst_n && !init && h_ok && d_ok && sent < NTLP;
  always @(posedge clk) if (rst_n && !init) begin
    cyc++;
    if (send) begin
      q_hdr++; q_dat += dneed; dsum += dneed; pend.push_back(dneed);
      if (sent < 6) $display("cyc %3d  send MWr %3d B  CL/CC hdr %3d/%3d data %4d/%4d",
                             cyc, size(k), h_lim, h_cc + 8'd1, d_lim, d_cc + dneed);
      sent++; k++;
    end else if (sent < NTLP) stall++;
    max_hdr = (q_hdr > max_hdr) ? q_hdr : max_hdr;
    max_dat = (q_dat > max_dat) ? q_dat : max_dat;
    if (cyc % 12 == 0 && pend.size() > 0) begin           // receiver frees one TLP
      d = pend.pop_front();
      q_hdr--; q_dat -= d; drained++;
      h_alloc = h_alloc + 8'd1;  d_alloc = d_alloc + 12'(d);
      upd_at.push_back(cyc + 8); upd_v.push_back({h_alloc, d_alloc});
    end
    upd <= 1'b0;
    if (upd_at.size() > 0 && upd_at[0] == cyc) begin      // DLLP arrives: CL updates
      void'(upd_at.pop_front());
      {h_upd, d_upd} <= upd_v.pop_front();  upd <= 1'b1;
    end
  end
  initial begin
    repeat (2) @(posedge clk); rst_n = 1;
    @(negedge clk) init = 1; @(negedge clk) init = 0;
    wait (sent == NTLP); repeat (2) @(posedge clk);
    $display("sent=%0d TLPs in %0d cycles, stalled %0d cycles for credits", sent, cyc, stall);
    $display("receiver peak occupancy: %0d/4 headers, %0d/32 data credits (never exceeded)",
             max_hdr, max_dat);
    $display("counters mod 2^F: hdr CL=%0d CC=%0d, data CL=%0d CC=%0d (%0d data credits used)",
             h_lim, h_cc, d_lim, d_cc, dsum);
    $finish;
  end
endmodule''',
    'eth': r'''
// Byte-wide CRC-32 as used by the Ethernet FCS (reflected form of 0x04C11DB7).
package eth_crc_pkg;
  function automatic logic [31:0] crc32_byte(input logic [31:0] crc, input logic [7:0] d);
    crc = crc ^ {24'h0, d};
    for (int i = 0; i < 8; i++)
      crc = crc[0] ? (crc >> 1) ^ 32'hEDB8_8320 : (crc >> 1);
    return crc;
  endfunction
endpackage

// MAC transmit framer, GMII-style byte output (txd/tx_en), one byte per clock.
// Input: frame from destination MAC to end of payload, AXI-Stream-like handshake.
// Output: 7 x 55 preamble, D5 SFD, frame, zero pad to 60 bytes, FCS, 12-byte IFG.
module eth_tx_framer (
  input  logic       clk, rst_n,
  input  logic [7:0] s_data, input logic s_valid, s_last, output logic s_ready,
  output logic [7:0] txd,    output logic tx_en
);
  import eth_crc_pkg::*;
  typedef enum logic [2:0] {IDLE, PRE, SFD, DATA, PAD, FCS, IFG} st_t;
  st_t st;
  logic [31:0] crc;
  logic [5:0]  n;                           // byte counter within a state (or of frame)
  assign s_ready = (st == DATA);
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin st <= IDLE; tx_en <= 0; txd <= '0; n <= '0; crc <= '1; end
    else case (st)
      IDLE: begin tx_en <= 0; if (s_valid) begin st <= PRE; n <= '0; end end
      PRE:  begin tx_en <= 1; txd <= 8'h55; n <= n + 1'b1; if (n == 6) st <= SFD; end
      SFD:  begin txd <= 8'hD5; crc <= '1; n <= '0; st <= DATA; end
      DATA: if (s_valid) begin
              txd <= s_data; crc <= crc32_byte(crc, s_data);
              if (n != 6'd63) n <= n + 1'b1;          // saturate: only "< 60" matters
              if (s_last) st <= (n < 6'd59) ? PAD : FCS;
              if (s_last) n <= (n < 6'd59) ? n + 1'b1 : 6'd0;
            end
      PAD:  begin txd <= 8'h00; crc <= crc32_byte(crc, 8'h00); n <= n + 1'b1;
                  if (n == 6'd59) begin st <= FCS; n <= '0; end end
      FCS:  begin txd <= ~crc[8*n[1:0] +: 8];           // complement, LSB byte first
                  n <= n + 1'b1; if (n == 3) begin st <= IFG; n <= '0; end end
      IFG:  begin tx_en <= 0; n <= n + 1'b1; if (n == 11) st <= IDLE; end
      default: st <= IDLE;
    endcase
endmodule

// Receive FCS check: run the CRC over everything after the SFD, FCS included.
// For a good frame the (uncomplemented, reflected) register ends at 0xDEBB20E3.
module eth_rx_fcs (
  input  logic clk, rst_n,
  input  logic [7:0] rxd, input logic rx_dv,
  output logic done, fcs_ok, output logic [10:0] len
);
  import eth_crc_pkg::*;
  logic [31:0] crc;  logic in_frame, dv_q;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      crc <= '1; in_frame <= 0; dv_q <= 0; done <= 0; fcs_ok <= 0; len <= 0;
    end
    else begin
      dv_q <= rx_dv;  done <= 1'b0;
      if (rx_dv && !in_frame && rxd == 8'hD5) begin in_frame <= 1; crc <= '1; len <= 0; end
      else if (rx_dv && in_frame) begin crc <= crc32_byte(crc, rxd); len <= len + 1'b1; end
      if (!rx_dv && dv_q && in_frame) begin            // end of carrier
        in_frame <= 0; done <= 1'b1; fcs_ok <= (crc == 32'hDEBB_20E3);
      end
    end
endmodule''',
    'tb_eth': r'''
module tb;
  logic clk = 0, rst_n = 0;  always #4 clk = ~clk;         // 125 MHz GMII clock
  logic [7:0] s_data, txd, rxd;  logic s_valid = 0, s_last = 0, s_ready, tx_en, rx_dv;
  logic done, fcs_ok;  logic [10:0] len;
  logic flip = 0;                                       // corrupt one bit on the "wire"
  eth_tx_framer tx (.*);
  assign rxd = txd ^ {7'b0, flip};  assign rx_dv = tx_en;
  eth_rx_fcs rx (.clk, .rst_n, .rxd, .rx_dv, .done, .fcs_ok, .len);
  // ARP request: broadcast dst, src 02:00:00:00:00:01, EtherType 0806, 28-byte body
  logic [7:0] frm [42];
  int nb = 0;  string line = "";  bit dump = 1;
  always @(posedge clk) if (tx_en && dump) begin
    nb++; line = {line, $sformatf("%02h", txd)};
    if (nb % 36 == 0) begin $display("%s", line); line = ""; end
  end
  always @(posedge clk) if (done)
    if (fcs_ok) $display("RX: %0d bytes after SFD, FCS OK", len);
    else        $display("RX: %0d bytes after SFD, FCS BAD -> frame dropped", len);
  task automatic send_frame;
    for (int i = 0; i < 42; i++) begin
      s_data = frm[i]; s_valid = 1; s_last = (i == 41);
      @(posedge clk); while (!s_ready) @(posedge clk);
      #1;
    end
    s_valid = 0; s_last = 0;
  endtask
  initial begin
    for (int i = 0; i < 6; i++) frm[i] = 8'hFF;
    frm[6] = 8'h02; for (int i = 7; i < 11; i++) frm[i] = 8'h00; frm[11] = 8'h01;
    frm[12] = 8'h08; frm[13] = 8'h06;
    for (int i = 14; i < 42; i++) frm[i] = 8'(i - 14);     // stand-in ARP body 00..1B
    repeat (2) @(posedge clk); rst_n = 1; #1;
    send_frame();
    wait (done); @(posedge clk);
    if (line.len()) $display("%s", line);
    $display("TX: %0d bytes on GMII incl. preamble/SFD", nb);
    dump = 0;
    fork                                              // second frame: flip one bit
      send_frame();
      begin repeat (30) @(posedge clk); #1 flip = 1; @(posedge clk); #1 flip = 0; end
    join
    wait (done); repeat (2) @(posedge clk);
    $finish;
  end
endmodule''',
    'ref_eth': r'''
import zlib, struct
frame = bytes([0xFF]*6 + [0x02, 0, 0, 0, 0, 0x01] + [0x08, 0x06] + list(range(28)))
frame += bytes(60 - len(frame))                        # pad to 60 bytes
fcs = struct.pack("<I", zlib.crc32(frame))             # FCS sent LSB byte first
print("python zlib FCS bytes:", fcs.hex())
def crc_reg(data):                                     # register without final xor
    c = 0xFFFFFFFF
    for b in data:
        c ^= b
        for _ in range(8):
            c = (c >> 1) ^ (0xEDB88320 if c & 1 else 0)
    return c
print("residue over frame+FCS: %08x" % crc_reg(frame + fcs))''',
    'sdram_chk': r'''
// SDRAM command/timing checker: a passive monitor as used in DV or on a controller
// bench. Times in memory-clock cycles. Per bank: ACT->RD/WR >= tRCD, ACT->PRE >= tRAS,
// PRE->ACT >= tRP, ACT->ACT >= tRC, WR->PRE >= WL + BL/2 + tWR, and state legality.
// Across banks: ACT->ACT >= tRRD; REF needs every bank idle and precharged.
module sdram_chk #(parameter int NB = 4,
                   parameter int tRCD = 4, tRP = 4, tRAS = 10, tRC = 14,
                   parameter int tRRD = 2, tWR = 5, tCWL = 3, BL = 8, tRFC = 20) (
  input  logic clk,
  input  logic [2:0] cmd,                          // NOP, ACT, RD, WR, PRE, REF
  input  logic [$clog2(NB)-1:0] bank,
  input  logic [15:0] row,
  output int   errors
);
  localparam logic [2:0] NOP = 0, ACT = 1, RD = 2, WR = 3, PRE = 4, REF = 5;
  localparam int WREC = tCWL + BL/2 + tWR;         // last write data -> precharge
  longint cyc = 0, t_act [NB], t_pre [NB], t_wr [NB], t_any_act = -99, t_ref = -99;
  bit     is_open [NB];
  logic [15:0] open_row [NB];
  initial begin
    errors = 0;
    for (int b = 0; b < NB; b++) begin t_act[b] = -99; t_pre[b] = -99; t_wr[b] = -99; end
  end
  function automatic void need(input bit ok, input string msg);
    if (!ok) begin $display("  cyc %3d  VIOLATION: %s", cyc, msg); errors++; end
  endfunction
  always @(posedge clk) begin
    longint dA, dP, dW;
    cyc++;
    dA = cyc - t_act[bank];  dP = cyc - t_pre[bank];  dW = cyc - t_wr[bank];
    if (cmd != NOP) need(cyc - t_ref >= tRFC, "command inside tRFC after REF");
    case (cmd)
      ACT: begin
        need(!is_open[bank], $sformatf("ACT to open bank %0d", bank));
        need(dP >= tRP,  $sformatf("ACT %0d cycles after PRE < tRP=%0d", dP, tRP));
        need(dA >= tRC,  $sformatf("ACT->ACT same bank %0d < tRC=%0d", dA, tRC));
        need(cyc - t_any_act >= tRRD,
             $sformatf("ACT->ACT other bank %0d < tRRD=%0d", cyc - t_any_act, tRRD));
        is_open[bank] = 1; open_row[bank] = row; t_act[bank] = cyc; t_any_act = cyc;
      end
      RD, WR: begin
        need(is_open[bank], $sformatf("column command to idle bank %0d", bank));
        if (is_open[bank])
          need(dA >= tRCD, $sformatf("RD/WR %0d cycles after ACT < tRCD=%0d", dA, tRCD));
        if (cmd == WR) t_wr[bank] = cyc;
      end
      PRE: begin
        if (is_open[bank])
          need(dA >= tRAS, $sformatf("PRE %0d cycles after ACT < tRAS=%0d", dA, tRAS));
        need(dW >= WREC, $sformatf("PRE %0d cycles after WR < WL+BL/2+tWR=%0d", dW, WREC));
        is_open[bank] = 0; t_pre[bank] = cyc;
      end
      REF: begin
        for (int b = 0; b < NB; b++) begin
          need(!is_open[b], $sformatf("REF with bank %0d open", b));
          need(cyc - t_pre[b] >= tRP, "REF inside tRP of a PRE");
        end
        t_ref = cyc;
      end
      default: ;
    endcase
  end
endmodule''',
    'tb_sdram': r'''
module tb;
  logic clk = 1;  always #5 clk = ~clk;
  logic [2:0] cmd = 0;  logic [1:0] bank = 0;  logic [15:0] row = 0;  int errors;
  sdram_chk #(.NB(4)) chk (.*);
  function automatic string name(input logic [2:0] c);
    case (c) 1: return "ACT"; 2: return "RD"; 3: return "WR"; 4: return "PRE";
             5: return "REF"; default: return "NOP"; endcase
  endfunction
  int t = 0;
  task automatic issue(input int at, input logic [2:0] c, input logic [1:0] b,
                       input int r = 0);
    while (t < at - 1) begin @(negedge clk); cmd = 0; t++; end
    @(negedge clk); cmd = c; bank = b; row = 16'(r); t++;
    if (c == 1) $display("cyc %3d  %-3s bank %0d row %0h", t, name(c), b, r);
    else if (c == 5) $display("cyc %3d  REF (all banks)", t);
    else        $display("cyc %3d  %-3s bank %0d", t, name(c), b);
  endtask
  initial begin
    $display("-- legal sequence --");
    issue( 1, 1, 0, 'h12);   // ACT b0
    issue( 3, 1, 1, 'h40);   // ACT b1  (tRRD = 2 later)
    issue( 5, 2, 0);         // RD  b0  (tRCD = 4)
    issue( 7, 3, 1);         // WR  b1
    issue(11, 4, 0);         // PRE b0  (tRAS = 10)
    issue(19, 4, 1);         // PRE b1  (WR + 3 + 4 + 5 = 19)
    issue(24, 5, 0);         // REF     (all banks idle)
    $display("-- buggy sequence --");
    issue(45, 1, 2, 'h7);    // ACT b2
    issue(46, 1, 3, 'h8);    // ACT b3 one cycle later: tRRD
    issue(47, 2, 2);         // RD b2 too early: tRCD
    issue(50, 4, 2);         // PRE b2 too early: tRAS
    issue(52, 1, 2, 'h9);    // ACT b2: tRP and tRC
    issue(53, 2, 0);         // RD to idle bank 0
    issue(56, 1, 3, 'h1);    // ACT to already-open bank 3
    @(negedge clk); cmd = 0; @(negedge clk);
    $display("violations = %0d", errors);
    $finish;
  end
endmodule''',
}

OUT = {
    'usb': ['wire: KJKJKJKKKKJKJKKKKKKKJJJJJJJKKKKKKJJJJJJJKJKJKJKJKJK', 'payload bits=48  stuffed bits=3  stuff errors=0', 'decoded bytes: 80 c3 ff 7f 3f 00'],
    'crc': ['token addr=00 endp=0  crc5=08  bytes after PID: 00 10  rx residual ok=1', 'token addr=15 endp=e  crc5=17  bytes after PID: 15 ef  rx residual ok=1', 'token addr=3a endp=a  crc5=1c  bytes after PID: 3a 3d  rx residual ok=1', 'token addr=70 endp=4  crc5=0e  bytes after PID: 70 72  rx residual ok=1', 'token addr=01 endp=0  crc5=17  bytes after PID: 01 e8  rx residual ok=1', 'DATA0 GET_DESCRIPTOR  crc16=bb29  CRC bytes on the wire: dd 94  rx residual ok=1', 'same packet, one bit flipped:  rx residual ok=0'],
    'tlp': ['MWr32 F0000104, 8 B, tag 05      40000002 010005ff f0000104', 'MRd32 80000002, 2 B, tag 06      00000001 0100060c 80000000', 'MRd64 1234567801, 256 B          20000041 0100071e 00000012 34567800', 'MRd32 00001000, 4096 B           00000000 010008ff 00001000', 'CfgRd0 01:00.0 reg 010 (BAR0)    04000001 0000090f 01000010', 'CplD 4 B for tag 09              4a000001 01000004 00000910'],
    'fc': ['cyc   1  send MWr  64 B  CL/CC hdr   4/  1 data   32/   4', 'cyc   2  send MWr 256 B  CL/CC hdr   4/  2 data   32/  20', 'cyc   3  send MWr 128 B  CL/CC hdr   4/  3 data   32/  28', 'cyc  46  send MWr 512 B  CL/CC hdr   7/  4 data   60/  60', 'cyc  58  send MWr  64 B  CL/CC hdr   8/  5 data   92/  64', 'cyc  59  send MWr 256 B  CL/CC hdr   8/  6 data   92/  80', 'sent=300 TLPs in 3600 cycles, stalled 3298 cycles for credits', 'receiver peak occupancy: 3/4 headers, 32/32 data credits (never exceeded)', 'counters mod 2^F: hdr CL=47 CC=44, data CL=404 CC=404 (4500 data credits used)'],
    'eth': ['55555555555555d5ffffffffffff0200000000010806000102030405060708090a0b0c0d', '0e0f101112131415161718191a1b000000000000000000000000000000000000a95ab799', 'TX: 72 bytes on GMII incl. preamble/SFD', 'RX: 64 bytes after SFD, FCS OK', 'RX: 64 bytes after SFD, FCS BAD -> frame dropped'],
    'sd': ['-- legal sequence --', 'cyc   1  ACT bank 0 row 12', 'cyc   3  ACT bank 1 row 40', 'cyc   5  RD  bank 0', 'cyc   7  WR  bank 1', 'cyc  11  PRE bank 0', 'cyc  19  PRE bank 1', 'cyc  24  REF (all banks)', '-- buggy sequence --', 'cyc  45  ACT bank 2 row 7', 'cyc  46  ACT bank 3 row 8', '  cyc  46  VIOLATION: ACT->ACT other bank 1 < tRRD=2', 'cyc  47  RD  bank 2', '  cyc  47  VIOLATION: RD/WR 2 cycles after ACT < tRCD=4', 'cyc  50  PRE bank 2', '  cyc  50  VIOLATION: PRE 5 cycles after ACT < tRAS=10', 'cyc  52  ACT bank 2 row 9', '  cyc  52  VIOLATION: ACT 2 cycles after PRE < tRP=4', '  cyc  52  VIOLATION: ACT->ACT same bank 7 < tRC=14', 'cyc  53  RD  bank 0', '  cyc  53  VIOLATION: column command to idle bank 0', 'cyc  56  ACT bank 3 row 1', '  cyc  56  VIOLATION: ACT to open bank 3', '  cyc  56  VIOLATION: ACT->ACT same bank 10 < tRC=14', 'violations = 8'],
    'ref_usb': ['wire: KJKJKJKKKKJKJKKKKKKKJJJJJJJKKKKKKJJJJJJJKJKJKJKJKJK  stuffed: 3', 'crc5(SETUP addr 0 ep 0) = 08', 'crc16(GET_DESCRIPTOR) = bb29'],
    'ref_tlp': ['40000002 010005ff f0000104', '00000001 0100060c 80000000', '20000041 0100071e 00000012 34567800', '00000000 010008ff 00001000', '04000001 0000090f 01000010', '4a000001 01000004 00000910'],
    'ref_eth': ['python zlib FCS bytes: a95ab799', 'residue over frame+FCS: debb20e3'],
}


def _v(name, caption=None):
    """Show a verified source from SRC."""
    code(SRC[name].split("\n"), caption)


def _o(name, caption=None):
    """Show the real output captured for a run."""
    out(OUT[name], caption)



# =============================================================================
#              PART IV - HIGH-SPEED AND MEMORY INTERFACES (Ch 17-20)
# =============================================================================
def part4a():
    part("High-Speed and Memory Interfaces",
         "Part III dealt with links measured in kilobits and megabits. This "
         "part climbs to the interfaces that set an SoC's pin budget, power "
         "and performance: USB from 1.5 Mb/s to USB4's 80 Gb/s, PCI Express "
         "and CXL, Ethernet from the MAC down to the xMII pins, the DRAM and "
         "flash interfaces that feed every processor, then display and camera "
         "links, chip-to-chip and die-to-die interconnect, and finally the "
         "debug, test and trace ports every chip must carry. These are "
         "layered protocols with a PHY (usually a bought hard macro), a "
         "controller in RTL, and a large firmware stack on top; each chapter "
         "shows where that split falls and what the RTL, DV, PHY and firmware "
         "teams each own.")
    _ch17()
    _ch18()
    _ch19()
    _ch20()


# ---------------------------------------------------------------- Ch 17 ---
def _ch17():
    chapter("USB 2.0, USB 3.x and USB4", newpage=False)
    p("The Universal Serial Bus is the most widely deployed wired peripheral "
      "link in the world, and almost every application processor, "
      "microcontroller and PC chipset carries at least one USB controller. "
      "Its history also explains its complexity: USB 1.x and 2.0 are a "
      "half-duplex, host-polled bus on one differential pair; USB 3.x added "
      "a completely separate, full-duplex SerDes link beside the 2.0 pair; "
      "USB Type-C changed the connector and brought power negotiation; and "
      "USB4 turned the port into a tunnelling fabric that also carries "
      "PCI Express and DisplayPort. An SoC team that 'adds USB' therefore "
      "integrates two or three different protocol stacks, an analog PHY, a "
      "Type-C port controller and a large software stack.")

    h2("Versions, speeds and names")
    tbl(["Mode / marketing name", "Signalling rate", "Encoding", "Spec / year",
         "Wires used"],
        [["Low Speed (LS)", "1.5 Mb/s", "NRZI + bit stuffing", "USB 1.0, 1996",
          "D+/D- half duplex"],
         ["Full Speed (FS)", "12 Mb/s", "NRZI + bit stuffing", "USB 1.0/1.1",
          "D+/D- half duplex"],
         ["High Speed (HS)", "480 Mb/s", "NRZI + bit stuffing", "USB 2.0, 2000",
          "D+/D- half duplex"],
         ["SuperSpeed, USB 3.2 Gen 1", "5 Gb/s", "8b/10b", "USB 3.0, 2008",
          "1 TX + 1 RX pair"],
         ["SuperSpeedPlus, USB 3.2 Gen 2", "10 Gb/s", "128b/132b", "USB 3.1, 2013",
          "1 TX + 1 RX pair"],
         ["USB 3.2 Gen 2x2", "2 x 10 Gb/s", "128b/132b", "USB 3.2, 2017",
          "2 lanes (Type-C only)"],
         ["USB4 Gen 2x2 / Gen 3x2", "20 / 40 Gb/s", "64b/66b / 128b/132b",
          "USB4 v1, 2019", "2 lanes, Type-C"],
         ["USB4 Gen 4 (USB4 v2)", "80 Gb/s (120/40 asym.)", "PAM3",
          "USB4 v2, 2022", "2 lanes, Type-C"]],
        widths=[25, 17, 18, 16, 20], bold_first=True,
        caption="USB generations. Data rates are raw line rates; usable "
                "throughput is lower (encoding, protocol and software "
                "overhead). USB4 always also carries a USB 2.0 link on D+/D-.")
    p("The naming has been re-branded several times: 'USB 3.0' SuperSpeed "
      "became 'USB 3.1 Gen 1' and then 'USB 3.2 Gen 1', all meaning the same "
      "5 Gb/s link. In a specification or datasheet, trust the signalling "
      "rate, not the version number. A 'USB 3.2' device may legally be "
      "only a 5 Gb/s device.")

    h2("Topology: host, hubs, devices and tiers")
    diagram([
        "  tier 1        tier 2           tier 3                ...    tier 7",
        " +--------+   +---------+     +---------+",
        " |  HOST  |---| root hub|--+--|  hub    |--+-- device (function)",
        " | (xHCI) |   | (ports) |  |  +---------+  +-- hub -- hub -- ... -- device",
        " +--------+   +---------+  +-- device (compound: hub + functions)",
        "",
        " - one host per bus; all traffic is scheduled by the host",
        " - 7-bit device address: up to 127 devices (address 0 = default, unconfigured)",
        " - at most 5 external hubs between host and a device (7 tiers incl. root)",
        " - up to 16 endpoints per direction per device; EP0 is the control endpoint",
    ], "USB is a tiered star, not a shared multi-drop bus. Hubs repeat "
       "traffic downstream and aggregate it upstream.")
    p("USB 2.0 is **host-centric**: a device never speaks unless the host "
      "addresses it with a token. Interrupt endpoints are therefore "
      "__polled__ at an interval the device requests. USB 3.x keeps the host "
      "in charge of scheduling but lets a device send an asynchronous "
      "**ERDY** notification when it becomes ready, so the host does not "
      "waste link time polling. A hub is itself a device with a control "
      "endpoint and an interrupt endpoint that reports port status changes. "
      "An HS hub also contains one or more **Transaction Translators** (TT) "
      "that convert HS **split transactions** into FS/LS traffic for slow "
      "devices, so a keyboard does not throttle a 480 Mb/s bus.")

    h2("USB 2.0 electrical layer: D+, D-, J, K and SE0")
    p("LS and FS use single-ended 3.3 V CMOS-like drivers on the two wires "
      "of a twisted pair, received both differentially (for data) and "
      "single-ended (for SE0 and line state). The host's downstream port has "
      "a 15 kohm pull-down on each wire; a device announces itself with a "
      "1.5 kohm pull-up to about 3.3 V: on **D+ for full speed**, on **D- for "
      "low speed**. That pull-up is how attach and speed are detected.")
    tbl(["Line state", "D+ / D-", "Meaning"],
        [["Differential 1", "D+ > D-", "J for FS/HS; K for LS"],
         ["Differential 0", "D+ < D-", "K for FS/HS; J for LS"],
         ["SE0", "both low", "End of packet (2 bit times), reset (>= 10 ms from the host), "
                             "disconnect (long SE0 with no pull-up)"],
         ["SE1", "both high", "Illegal - must never be driven"],
         ["Idle", "J (held by pull-up)", "Bus idle between packets"],
         ["Resume", "K for >= 20 ms", "Wake a suspended bus (host drives it downstream)"]],
        widths=[16, 18, 66], bold_first=True)
    p("**High speed** is different electrically: it is a **current-mode** "
      "driver that steers about 17.78 mA into 45 ohm terminations at each "
      "end of the line (both D+ and D- terminated to ground), giving a "
      "differential swing of about 400 mV. HS capability is discovered after "
      "reset by the **chirp** handshake: an HS-capable device drives a "
      "'chirp K' for about 1-7 ms; an HS-capable host answers with "
      "alternating chirp K/J pairs; the device then removes its 1.5 kohm "
      "pull-up, turns on its 45 ohm terminations and both sides are in HS "
      "mode. A legacy host simply ignores the chirp and the device stays at "
      "FS - backward compatibility is built into the reset sequence.")
    diagram([
        "  FS attach and HS chirp (not to scale)",
        "",
        "  D+  ___/~~~~~~~~~~~\\_____________________/~\\_/~\\_/~\\_  ...  HS idle (SE0-like,",
        "  D-  _______________________/~~~~~~~\\_____/~\\_/~\\_/~\\_       ~0 V, terminated)",
        "         ^ pull-up   ^ host   ^ device    ^ host chirps K J K J K J",
        "         (FS device) | reset  | chirp K   | (>= 3 KJ pairs seen: device",
        "                     | SE0    | 1..7 ms   |  switches to HS terminations)",
    ], "Speed negotiation happens inside the bus reset. The PHY does the "
       "analog work; the link controller (and firmware timers) sequence it.")

    h3("NRZI and bit stuffing")
    p("Data is sent LSB first and **NRZI** coded: a 0 bit is sent as a "
      "**transition** (J->K or K->J), a 1 bit as **no transition**. NRZI "
      "makes the data polarity-independent, but a long run of 1s would give "
      "the receiver's clock-recovery DPLL no edges. So the transmitter "
      "**stuffs** a 0 after every six consecutive 1s (before NRZI), which "
      "forces a transition at least every seven bit times. The receiver "
      "removes the stuffed bit; if it sees seven 1s in a row it declares a "
      "**bit-stuff error**, which is also how an HS **EOP** is signalled - "
      "deliberately.")
    tbl(["Field", "FS / LS", "HS"],
        [["SYNC", "8 bits 00000001 (wire: KJKJKJKK)", "32 bits (15 KJ pairs then KK)"],
         ["EOP", "SE0 for 2 bit times, then J", "Deliberate bit-stuff error: 8 bits "
                                                "01111111 NRZI (40 bits after an SOF)"],
         ["Bit stuffing", "after six 1s", "after six 1s"],
         ["Inter-packet / turnaround", "on the order of 2-7.5 bit times gap, "
          "16-18 bit-time response timeout", "much longer in bit times (hundreds), "
          "same order in ns"]],
        widths=[22, 38, 40], bold_first=True)
    p("The line coder below is the part of a USB 2.0 PHY (or of the "
      "controller's FS/LS path) that implements this. The transmitter drops "
      "`in_ready` for one bit time whenever it inserts a stuff bit, which is "
      "exactly why UTMI has a `TxReady` handshake on its parallel interface. "
      "The receiver side takes one recovered sample per bit (in a real PHY "
      "a DPLL or oversampler produces them, see Chapter 4).")
    _v("usb_line", "usb_line.sv - FS/LS bit stuffing + NRZI encoder and decoder.")
    _v("tb_usb_line", "tb_usb_line.sv - sends SYNC, DATA0 PID and bytes with "
       "long runs of 1s through the encoder into the decoder.")
    _o("usb", "Real vvp output. The SYNC byte appears as the expected "
       "KJKJKJKK, three stuff bits were inserted (after the 0xFF, and in "
       "0x7F/0x3F runs), and the decoder returns the original bytes.")
    p("The same stream was run through an independent Python model; its "
      "wire string is identical, character for character, to the RTL's:")
    _v("ref_usb", "ref_usb.py - Python golden model for NRZI/bit stuffing and "
       "the two USB CRCs.")
    _o("ref_usb", "Real Python output. The wire string matches the vvp run "
       "exactly; the CRC values are used in the next section.")
    box("warn", "Pitfall: where stuffing ends",
        ["Bit stuffing applies to everything from SYNC to the end of the "
         "CRC, including the CRC bits. A classic bug is to stop counting "
         "ones at a byte boundary, or to reset the ones counter at the start "
         "of the CRC field. Another is forgetting that a stuff bit is "
         "required even when the next data bit would have been 0 anyway - "
         "look at the 0x3F byte above.",
         "On receive, the ones counter must survive across bytes, and the "
         "EOP detector must run before the stuff-error detector so that a "
         "normal HS EOP is not logged as an error."])

    h2("Packets: PIDs, tokens, data, handshakes and CRCs")
    p("Every USB 2.0 packet starts with SYNC and a **PID** byte: a 4-bit "
      "packet identifier followed by its one's complement, so a single-bit "
      "error in the PID is always detected. PIDs fall into four groups.")
    tbl(["Group", "PID name", "PID[3:0]", "Byte on bus", "Use"],
        [["Token", "OUT", "0001", "E1", "host -> device data follows"],
         ["", "IN", "1001", "69", "device -> host data requested"],
         ["", "SOF", "0101", "A5", "start of (micro)frame + 11-bit frame number"],
         ["", "SETUP", "1101", "2D", "control transfer setup stage"],
         ["Data", "DATA0 / DATA1", "0011 / 1011", "C3 / 4B", "data with toggle bit"],
         ["", "DATA2 / MDATA", "0111 / 1111", "87 / 0F", "HS high-bandwidth isochronous"],
         ["Handshake", "ACK", "0010", "D2", "received without error"],
         ["", "NAK", "1010", "5A", "not ready now - retry later"],
         ["", "STALL", "1110", "1E", "endpoint halted / request unsupported"],
         ["", "NYET", "0110", "96", "HS: accepted, but not ready for next"],
         ["Special", "PRE / ERR", "1100", "3C", "LS preamble (FS hub) / split error"],
         ["", "SPLIT", "1000", "78", "HS split transaction to a TT"],
         ["", "PING", "0100", "B4", "HS: flow-control probe for OUT/control"]],
        widths=[13, 20, 16, 14, 37], bold_first=True,
        caption="USB 2.0 PIDs. Byte on bus = {~PID, PID}, sent LSB first.")
    diagram([
        " Token   | SYNC | PID(8) | ADDR(7) | ENDP(4) | CRC5 | EOP |",
        " SOF     | SYNC | PID(8) |   Frame number(11) | CRC5 | EOP |",
        " Data    | SYNC | PID(8) |   DATA (0..1024 bytes)  | CRC16 | EOP |",
        " Handsh. | SYNC | PID(8) | EOP |",
        "",
        " A bulk IN transaction:  host: IN token   dev: DATA0/1   host: ACK",
        " A bulk OUT transaction: host: OUT token  host: DATA0/1  dev: ACK / NAK / STALL / NYET",
    ], "USB 2.0 packet formats. Every field is transmitted LSB first; CRCs "
       "are transmitted MSB first.")
    p("**CRC5** (generator x^5 + x^2 + 1) protects the 11 bits of a token; "
      "**CRC16** (x^16 + x^15 + x^2 + 1) protects the data field. Both "
      "registers are seeded with all ones, the complement of the remainder "
      "is transmitted, and a receiver that runs the same LFSR over data and "
      "CRC finds a fixed **residual**: 01100 for CRC5 and 0x800D for CRC16. "
      "The serial implementation is a few flops:")
    _v("usb_crc", "usb_crc.sv - serial CRC5 and CRC16 with receiver residual "
       "checks.")
    _v("tb_usb_crc", "tb_usb_crc.sv - five tokens and the standard "
       "GET_DESCRIPTOR(Device) setup packet, plus a corrupted copy.")
    _o("crc", "Real vvp output. The SETUP token to address 0, endpoint 0 is "
       "the well-known byte sequence 2D 00 10, and the 8-byte GET_DESCRIPTOR "
       "setup data carries the CRC bytes DD 94 seen on every USB analyzer "
       "trace. The Python model above gives the same values (08 and bb29).")
    box("intuit", "Why the CRC 'looks backwards' in a trace",
        ["The data bits go out LSB first but the CRC goes out MSB first "
         "(c4 first for CRC5). A protocol analyzer that shows the packet as "
         "LSB-first bytes therefore displays the bit-reversed CRC: CRC5 08 "
         "(00010 reversed is 01000) shows up as the top five bits of the "
         "second address byte, 0x10. Getting this bit order wrong is the "
         "most common reason a first-silicon SIE sees every token as "
         "corrupt."])

    h2("Transfer types and bandwidth")
    p("A **transfer** is made of **transactions**, and a transaction is "
      "token + data + handshake. Four transfer types exist; the endpoint "
      "descriptor fixes the type of each endpoint.")
    tbl(["Type", "Guarantees", "Max packet (FS / HS / SS)", "Typical use"],
        [["Control", "delivery, retries; 10-20% of bus reserved",
          "8-64 / 64 / 512", "enumeration, configuration, class requests"],
         ["Bulk", "delivery, no latency guarantee; uses leftover bandwidth",
          "8-64 / 512 / 1024 (bursts up to 16)", "mass storage, printers, network"],
         ["Interrupt", "bounded polling interval, retries",
          "64 / 1024 x up to 3 per uframe / 1024 x up to 3",
          "HID (keyboards, mice), status"],
         ["Isochronous", "reserved bandwidth, bounded latency, NO retry",
          "1023 / 1024 x up to 3 per uframe / 1024 x 16 x 3",
          "audio, video, webcams"]],
        widths=[13, 33, 27, 27], bold_first=True)
    p("Time is divided into 1 ms **frames** at FS (each starting with an SOF "
      "token carrying an 11-bit frame number) and 125 us **microframes** at "
      "HS (eight per frame, same frame number repeated). The host may "
      "reserve at most **90%** of an FS frame or **80%** of an HS microframe "
      "for periodic (isochronous + interrupt) transfers; the rest is shared "
      "by control and bulk. The best-case HS bulk rate is 13 packets of 512 "
      "bytes per microframe:")
    eq(["13 x 512 B / 125 us = 53.2 MB/s   (theoretical HS bulk ceiling)",
        "typical achieved: ~35-45 MB/s (host scheduling, NAKs, software)"],
       "Why a 480 Mb/s port rarely exceeds ~40 MB/s in practice.")
    p("Reliable transfer types use the **data toggle**: the sender "
      "alternates DATA0 and DATA1, and the receiver only advances its "
      "expected toggle when it accepts a packet. If an ACK is lost, the "
      "sender retransmits with the old toggle, the receiver sees a repeat, "
      "ACKs it again and discards the duplicate. The host retries a failed "
      "transaction up to three times ('three strikes') before reporting an "
      "error to software.")

    h2("Control transfers, enumeration and descriptors")
    diagram([
        " SETUP stage:   SETUP token   DATA0 (8-byte setup packet)     ACK",
        " DATA stage:    IN/OUT token  DATA1, DATA0, DATA1 ...        ACK   (optional)",
        " STATUS stage:  opposite-direction token, zero-length DATA1,  ACK",
        "",
        " setup packet: bmRequestType(1) bRequest(1) wValue(2) wIndex(2) wLength(2)",
        "   e.g. 80 06 00 01 00 00 40 00 = device-to-host, standard, device;",
        "        GET_DESCRIPTOR (06), type DEVICE (01) index 0, length 64",
    ], "The three stages of a control transfer. The status stage always "
       "uses DATA1 and runs in the opposite direction to the data stage.")
    p("When a device is plugged in, the host **enumerates** it. A typical "
      "sequence (details vary by operating system) is:")
    bul(["Hub reports a connect (pull-up seen); host waits for debounce "
         "(about 100 ms) and issues a **bus reset** (SE0 >= 10 ms), during "
         "which the HS chirp happens.",
         "Host sends GET_DESCRIPTOR(Device) to **address 0** to learn "
         "`bMaxPacketSize0` (8, 16, 32 or 64 at FS; 64 at HS; 512 at SS, "
         "encoded as 2^9).",
         "Host sends **SET_ADDRESS** (bRequest 05). The device must switch "
         "to the new address only __after__ the status stage completes, and "
         "has 2 ms of recovery time.",
         "Host reads the full 18-byte device descriptor, then the 9-byte "
         "configuration descriptor, then the whole configuration hierarchy "
         "(`wTotalLength` bytes), and string descriptors.",
         "The driver is chosen from VID/PID or class codes; it sends "
         "**SET_CONFIGURATION** (09) and class-specific requests. Only now "
         "may the device draw its configured current (up to 500 mA at USB 2.0, "
         "900 mA at USB 3.x; unconfigured it is limited to 100 mA / 150 mA)."],
        ordered=True)
    tbl(["Descriptor", "Type", "Length", "Key fields"],
        [["Device", "0x01", "18", "bcdUSB, class, bMaxPacketSize0, idVendor, idProduct, "
                                   "bNumConfigurations"],
         ["Configuration", "0x02", "9", "wTotalLength, bNumInterfaces, bmAttributes "
                                        "(self-powered, remote wakeup), bMaxPower"],
         ["String", "0x03", "var.", "UTF-16LE text; index 0 lists language IDs"],
         ["Interface", "0x04", "9", "bInterfaceNumber, bAlternateSetting, class/subclass/"
                                    "protocol, bNumEndpoints"],
         ["Endpoint", "0x05", "7", "bEndpointAddress (bit 7 = IN), bmAttributes (type), "
                                   "wMaxPacketSize, bInterval"],
         ["Device qualifier", "0x06", "10", "how the device would look at the other speed"],
         ["Interface association", "0x0B", "8", "groups interfaces of one function "
                                                "(e.g. UVC, CDC)"],
         ["BOS", "0x0F", "var.", "USB 2.0 LPM / SuperSpeed / USB4 capabilities"],
         ["SS endpoint companion", "0x30", "6", "bMaxBurst, streams / Mult, "
                                                "wBytesPerInterval"]],
        widths=[22, 9, 9, 60], bold_first=True)
    box("tip", "Interview insight: endpoints are the unit of hardware",
        ["An **endpoint** is a buffer plus state (type, max packet size, "
         "toggle, halt bit) inside the device controller, addressed by "
         "number and direction. Interfaces and configurations are software "
         "groupings described in descriptors. When sizing a device "
         "controller, count endpoints and their FIFO depth; when writing "
         "firmware, count interfaces and alternate settings."])

    h2("USB 3.x SuperSpeed")
    p("SuperSpeed is effectively a different protocol that happens to share "
      "the connector and the device framework (descriptors, requests, "
      "transfer types). It adds two differential pairs (SSTX+/- and "
      "SSRX+/-) for **dual-simplex** full-duplex operation, while the "
      "USB 2.0 pair stays alive in parallel: every SuperSpeed device must "
      "also work at USB 2.0.")
    bul(["**Physical layer**: 5 GT/s with **8b/10b** (Gen 1) or 10 GT/s with "
         "**128b/132b** (Gen 2), scrambled (Gen 1 uses x^16 + x^5 + x^4 + "
         "x^3 + 1), AC-coupled, spread-spectrum clocking allowed, receiver "
         "equalization. **LFPS** (low-frequency periodic signalling, bursts "
         "in the tens of MHz) is used out of band for polling, U1/U2 exit and "
         "warm reset because the high-speed receivers may be off.",
         "**Link layer**: a header packet is 12 bytes of header, a CRC-16 and "
         "a 2-byte link control word with its own CRC-5 (16 bytes, after a "
         "4-symbol start-of-packet framing); data payloads carry a CRC-32. Reliable delivery uses header sequence numbers and "
         "**link commands**: LGOOD_n (ACK of header n), LBAD (request retry), "
         "LRTY (retry follows), LCRD_A..D (return of one of four header "
         "buffer credits), LGO_U1/U2/U3, LAU/LXU (accept/reject), LUP/LDN "
         "(keep-alive).",
         "**Protocol layer**: transaction packets (ACK, NRDY, ERDY, STATUS, "
         "PING), data packets, ITP (isochronous timestamp) and LMPs. Packets "
         "are **unicast** with a 20-bit route string instead of broadcast; "
         "bulk endpoints may use **bursts** (up to 16 packets without waiting "
         "for each ACK) and **streams** (used by UASP storage)."])
    diagram([
        "              +-----------+      warm reset / timeouts       +------------+",
        "  power-on -> | Rx.Detect | ---> Polling ---> U0 <------+---> | Recovery   |",
        "              +-----------+   (LFPS, RxEq,    |  ^      |     +------------+",
        "                    ^          TSEQ,TS1,TS2)  v  |      |",
        "                    |                       U1  U2  U3 (suspend)",
        "               SS.Disabled / SS.Inactive / Compliance / Loopback / Hot Reset",
    ], "Simplified USB 3.x LTSSM. U0 is active; U1 and U2 are link low-power "
       "states with progressively longer exit latency; U3 is suspend.")
    p("The **link training and status state machine** (LTSSM) - the same "
      "idea as PCIe's, Chapter 18 - detects a far-end receiver by measuring "
      "the line's charge time (Rx.Detect), exchanges LFPS, trains the "
      "receiver equalizer with a TSEQ pattern and exchanges TS1/TS2 ordered "
      "sets in Polling, then enters **U0**. Idle links drop into U1/U2 under "
      "timer control (negotiated with LGO_Ux / LAU / LXU) and into U3 when "
      "the host suspends the device.")

    h2("USB Type-C and USB Power Delivery")
    p("The **Type-C** connector (24 pins, reversible) is defined by its own "
      "specification. Its **CC1/CC2** configuration-channel pins do three "
      "jobs: detect attach, detect the plug **orientation** (which of CC1 "
      "or CC2 sees the sink's pull-down), and advertise current. The source "
      "presents a pull-up **Rp** whose value signals Default USB power, "
      "1.5 A or 3.0 A at 5 V; the sink presents a 5.1 kohm pull-down "
      "**Rd**; an electronically marked cable presents **Ra** and draws "
      "**VCONN** on the unused CC pin. There are two SuperSpeed lane pairs "
      "(TX1/RX1, TX2/RX2), so an orientation mux (or a two-lane USB 3.2 "
      "Gen 2x2 / USB4 PHY) is needed behind the connector.")
    bul(["**USB Power Delivery (PD)** runs a half-duplex packet protocol on "
         "the CC wire: **BMC** (biphase mark) coding at about 300 kb/s, 4b5b "
         "symbols, CRC-32, GoodCRC acknowledgements. Source and sink "
         "negotiate a contract (Source_Capabilities -> Request -> Accept -> "
         "PS_RDY). Standard Power Range reaches 100 W (20 V, 5 A with a "
         "5 A cable); PD 3.1 **Extended Power Range** reaches 240 W (48 V, "
         "5 A). **PPS** allows fine-grained programmable voltage for direct "
         "battery charging.",
         "**Alternate modes** reuse the high-speed pairs for another "
         "protocol after a PD structured-VDM exchange (Discover Identity, "
         "Discover SVIDs, Discover Modes, Enter Mode). **DisplayPort Alt "
         "Mode** (Chapter 21) is the common one; Thunderbolt 3 was another.",
         "SoC split: the CC logic and PD PHY usually live in a small "
         "**Type-C port controller** (TCPC, separate chip or integrated), "
         "with the policy engine in firmware (TCPM) talking over I2C "
         "(Chapter 13); the SoC provides the orientation mux control and "
         "role (host/device, DRP) switching."])
    box("warn", "Pitfall: Type-C integration bugs",
        ["Common field failures: the orientation mux driven from a stale CC "
         "reading; dead-battery mode not supported (the sink's Rd must be "
         "present with no power); VBUS applied before the contract; USB 2.0 "
         "D+/D- stubs from the two connector rows left unshorted or routed "
         "as a long stub; data-role swap not propagated to the dual-role "
         "controller. These are system bugs that span PHY, board, firmware "
         "and RTL - put them in the integration test plan explicitly."])

    h2("USB4 and Thunderbolt tunnelling")
    p("USB4 is based on the Thunderbolt 3 protocol contributed by Intel. A "
      "USB4 port is a **router**: the link runs on both Type-C lane pairs "
      "(two lanes, 10 or 20 Gb/s each in USB4 v1; 40 Gb/s per lane with "
      "PAM3 in USB4 v2), and packets of different protocols are "
      "**tunnelled** through it. Adapters at each router convert native "
      "protocol traffic into tunnelled packets:")
    diagram([
        "   host router                                         device router",
        "  +--------------------------+   USB4 link (2 lanes)   +----------------------+",
        "  | USB3 adapter  <-- xHCI   |=========================| USB3 adapter -> hub  |",
        "  | PCIe adapter  <-- RC port|  transport layer:       | PCIe adapter -> sw.  |",
        "  | DP IN adapter <-- display|  paths, hop IDs,        | DP OUT -> monitor    |",
        "  | host interface (DMA)     |  credits, priority      | host iface (P2P net) |",
        "  +--------------------------+                         +----------------------+",
        "        + a native USB 2.0 link always runs in parallel on D+/D-",
    ], "USB4 multiplexes tunnelled USB 3.x, PCIe and DisplayPort traffic over "
       "one link, with bandwidth managed by a connection manager in software.")
    p("The USB4 **transport layer** carries fixed-size transport-layer "
      "packets with a hop ID that selects a **path** through the routers, "
      "per-path credit-based flow control and scheduling priorities. A "
      "**connection manager** (software in the host OS, or firmware) "
      "discovers routers, allocates bandwidth - for example reserving "
      "isochronous DisplayPort bandwidth before PCIe gets the rest - and "
      "sets up the paths. For an SoC this means a USB4 subsystem contains "
      "a USB4 router, an xHCI controller, a PCIe root port and a DisplayPort "
      "source, all behind one PHY.")

    h2("Controller architectures")
    h3("Host controllers: xHCI")
    p("The **eXtensible Host Controller Interface** (xHCI, from Intel) "
      "replaced the older OHCI/UHCI (USB 1.1) and EHCI (USB 2.0) register "
      "models and handles every speed with one controller. It is a "
      "descriptor-ring DMA engine: software writes **Transfer Request "
      "Blocks** (TRBs, 16 bytes each) into per-endpoint **transfer rings** "
      "in system memory and rings a **doorbell** register; the controller "
      "fetches TRBs, schedules transactions on the bus and writes "
      "completion TRBs to an **event ring**, raising an MSI/MSI-X or wired "
      "interrupt through one of its interrupters. A **device context** per "
      "attached device (slot context + up to 31 endpoint contexts) lives in "
      "memory and is pointed to by the Device Context Base Address Array.")
    diagram([
        "  CPU / driver                  system memory                  xHCI (AXI master)",
        "  write TRBs ---------------->  transfer ring  <---- fetch ---- scheduler / DMA",
        "  ring doorbell ------------------------------------------------> doorbell reg",
        "                                event ring  <----- write ----- event generator",
        "  interrupt <---------------------------------------------------- interrupter",
    ], "The xHCI programming model: rings in memory, doorbells in MMIO.")
    h3("Device controllers and dual role")
    p("A **device controller** contains the serial interface engine (SIE: "
      "PID decode, CRC, toggle, handshake generation), per-endpoint state, "
      "endpoint FIFOs (often a shared RAM partitioned in software), and a "
      "DMA engine with its own descriptor format. Phones and embedded SoCs "
      "almost always use a **dual-role** controller (historically USB OTG "
      "with the ID pin, today Type-C DRP) that is an xHCI host in one mode "
      "and a device in the other. Licensed IP from a few vendors dominates; "
      "in-house designs are rare because of the compliance effort.")
    tbl(["Team", "Owns"],
        [["PHY / analog", "HS transceiver, chirp, squelch/disconnect detectors, "
                          "SuperSpeed SerDes, LFPS, Rx.Detect, eye compliance"],
         ["RTL / integration", "controller configuration, AXI and interrupt hookup, "
                               "UTMI/PIPE wiring, clocks/resets/power domains, "
                               "Type-C mux control"],
         ["DV", "USB VIP (host and device models), protocol checkers, "
                "enumeration and power-state tests, xHCI ring tests"],
         ["Firmware / software", "xHCI and gadget drivers, class drivers, PD policy "
                                 "engine, USB4 connection manager"],
         ["Validation / compliance", "USB-IF electrical, link-layer and USBCV "
                                     "tests, interoperability plugfests"]],
        widths=[22, 78], bold_first=True)

    h2("PHY interfaces: UTMI, UTMI+, ULPI and PIPE")
    p("USB PHYs are almost always bought or reused as hard macros, so the "
      "controller-to-PHY interface is standardized:")
    tbl(["Interface", "Width / clock", "Key signals", "Notes"],
        [["UTMI", "8 bit @ 60 MHz or 16 bit @ 30 MHz",
          "DataIn/DataOut, TxValid, TxReady, RxValid, RxActive, RxError, "
          "XcvrSelect, TermSelect, OpMode, LineState[1:0], SuspendM",
          "USB 2.0 device PHY: PHY does SYNC/EOP, NRZI, bit stuffing, "
          "serialization and clock recovery"],
         ["UTMI+", "same", "adds DpPulldown/DmPulldown, VBUS valid/session, "
                           "ID, host-side signals",
          "levels 0-3 add host and OTG support"],
         ["ULPI", "8 data + CLK, DIR, STP, NXT (12 pins), 60 MHz",
          "register reads/writes and packets over one bus",
          "low pin count for an external PHY chip"],
         ["PIPE", "8/16/32(/64)-bit per lane, PCLK",
          "TxData/TxDataK, RxData/RxDataK, RxValid, RxStatus, PowerDown, "
          "Rate, PhyStatus, TxDetectRx, TxElecIdle, RxPolarity",
          "shared with PCIe and SATA (Chapter 18); PIPE 5+ adds a "
          "low-pin-count message bus and a thinner SerDes architecture"],
         ["eUSB2", "1.2 V signalling repeater",
          "eD+/eD-", "lets advanced-node SoCs avoid 3.3 V I/O; a repeater "
                     "chip restores USB 2.0 levels"]],
        widths=[11, 20, 36, 33], bold_first=True)
    box("expert", "Expert note: the 3.3 V problem",
        ["FS/LS signalling needs about 3.3 V swing and tolerance to 5 V "
         "shorts on the connector, which is increasingly expensive in "
         "5 nm-class processes whose thick-oxide devices top out near 1.8 V. "
         "That is why eUSB2 and repeaters exist, and why many SoCs place the "
         "USB 2.0 PHY on a companion chip or use special I/O devices. Plan "
         "the process option early."])

    h2("Verification and bring-up")
    bul(["Use a commercial USB VIP for the host and device side; write your "
         "own scoreboard for the SoC data path (DMA to memory).",
         "Test **reset during every state** (mid-enumeration, mid-transfer, "
         "during U1/U2 entry), unplug during DMA, and suspend/resume with "
         "remote wakeup - these are where controllers hang.",
         "Check toggle recovery (drop an ACK), NAK storms, STALL and "
         "clear-halt, and zero-length packet termination of transfers that "
         "are an exact multiple of the max packet size.",
         "In emulation/FPGA, boot the real Linux xHCI driver early: most "
         "integration bugs (cache coherency of rings, interrupt routing, "
         "64-bit addressing) only appear with real software."])

    h2("Summary")
    bul(["USB 2.0 is a host-polled, half-duplex bus: NRZI with bit stuffing "
         "after six 1s, SYNC/PID/data/CRC/EOP packets, CRC5 on tokens and "
         "CRC16 on data (both seeded with ones, complemented, sent MSB "
         "first).",
         "FS/LS speed is signalled by a 1.5 kohm pull-up; HS is negotiated by "
         "the chirp during reset and uses 400 mV current-mode signalling.",
         "Four transfer types: control (enumeration), bulk (throughput), "
         "interrupt (bounded polling), isochronous (reserved bandwidth, no "
         "retry); the data toggle gives exactly-once delivery.",
         "USB 3.x adds a full-duplex SerDes link with 8b/10b or 128b/132b, "
         "an LTSSM, link-level retry with credits, and U1/U2/U3 power states.",
         "Type-C adds CC-based orientation/current detection and PD "
         "negotiation; USB4 tunnels USB3, PCIe and DisplayPort over one link.",
         "Hosts use xHCI (TRB rings + doorbells); device controllers use "
         "endpoint FIFOs + DMA; PHYs attach through UTMI/ULPI (USB 2.0) and "
         "PIPE (SuperSpeed)."])

    h2("Exercises")
    bul(["Hand-encode the SOF packet for frame number 0x2A5: give the 11-bit "
         "field, the CRC5 (use `ref_usb.py`), and the NRZI line states from "
         "SYNC to EOP. How many stuff bits are inserted?",
         "Extend `usb_nrzi_rx` with an FS EOP detector (SE0 for 2 bit times "
         "followed by J) and a SYNC detector that aligns the byte counter. "
         "Add them to the testbench.",
         "A full-speed isochronous audio endpoint carries 48 kHz, 24-bit "
         "stereo. What `wMaxPacketSize` does it need, and what fraction of "
         "the FS frame does it reserve?",
         "Explain step by step what happens if the ACK for a bulk OUT DATA1 "
         "packet is corrupted. Which side detects the duplicate and how?",
         "Compute the maximum theoretical throughput of a USB 3.2 Gen 1 link "
         "after 8b/10b encoding, then estimate the protocol overhead per "
         "1024-byte data packet (header packet, CRC-32, framing). Compare "
         "with the ~400-450 MB/s seen by real storage devices.",
         "List the signals you would need to add to a UTMI-based device "
         "controller to make it work as a host (UTMI+ level 2)."],
        ordered=True)


# ---------------------------------------------------------------- Ch 18 ---
def _ch18():
    chapter("PCI Express and CXL")
    p("PCI Express (PCIe) is the backbone of every PC, server, GPU, NIC and "
      "SSD, and the physical basis of CXL. It kept the software model of "
      "the old parallel PCI bus - memory, I/O and configuration address "
      "spaces, Bus/Device/Function numbering, BARs and capability lists - so "
      "that a 2025 operating system still enumerates a Gen6 device with "
      "code written for PCI. Underneath, the hardware is a packet-switched, "
      "point-to-point, credit-flow-controlled serial network with a "
      "three-layer stack. An SoC engineer meets PCIe as a **root port** "
      "(the SoC is the host), as an **endpoint** (the SoC is an accelerator "
      "or SSD controller on a card), or as both.")

    h2("Generations, encoding and bandwidth")
    tbl(["Gen", "Year", "Rate / lane", "Encoding", "Per lane, per direction",
         "x16, per direction"],
        [["1.x", "2003", "2.5 GT/s NRZ", "8b/10b", "250 MB/s", "4 GB/s"],
         ["2.0", "2007", "5.0 GT/s NRZ", "8b/10b", "500 MB/s", "8 GB/s"],
         ["3.0", "2010", "8.0 GT/s NRZ", "128b/130b", "~985 MB/s", "~15.8 GB/s"],
         ["4.0", "2017", "16 GT/s NRZ", "128b/130b", "~1.97 GB/s", "~31.5 GB/s"],
         ["5.0", "2019", "32 GT/s NRZ", "128b/130b", "~3.94 GB/s", "~63 GB/s"],
         ["6.0", "2022", "64 GT/s PAM4", "1b/1b, 256 B FLIT + FEC + CRC",
          "~7.5 GB/s", "~121 GB/s"],
         ["7.0", "2025", "128 GT/s PAM4", "FLIT (as 6.0)", "~15 GB/s", "~242 GB/s"]],
        widths=[7, 8, 17, 26, 20, 20], bold_first=True,
        caption="PCIe generations. Gen6/7 figures use the 242/256 FLIT payload "
                "efficiency; TLP/DLLP overhead reduces all of these further.")
    p("Each doubling was achieved differently. Gen3 kept NRZ but dropped the "
      "25% overhead of 8b/10b for 128b/130b with scrambling, so 8 GT/s gives "
      "nearly double Gen2's bandwidth. Gen6 kept the Nyquist frequency of "
      "Gen5 (16 GHz) but sends two bits per symbol with **PAM4**; the higher "
      "raw bit-error rate (on the order of 1e-6 before correction) forced a "
      "lightweight **FEC** and a fixed 256-byte **FLIT** (flow-control unit) "
      "containing 236 bytes of TLP, 6 bytes of DLLP, 8 bytes of CRC and 6 "
      "bytes of FEC. A link is 1, 2, 4, 8 or 16 lanes wide in practice "
      "(x12 and x32 appear in older revisions but are essentially unused), "
      "each lane a TX and an RX differential pair.")
    eq(["BW(Gen3+) per lane = rate x 128/130 / 8   e.g. 16 GT/s -> 1.969 GB/s",
        "BW(Gen6)  per lane = 64 GT/s x 242/256 / 8 = 7.56 GB/s",
        "x16 Gen5 bidirectional = 2 x 63 GB/s = 126 GB/s (before TLP overhead)"],
       "Raw per-direction bandwidth. Real DMA throughput is typically 80-90% "
       "of this with 256-byte payloads.")

    h2("Topology: root complex, switches, endpoints and BDF")
    diagram([
        "          CPU cores / memory / IOMMU",
        "                 |",
        "       +---------------------+",
        "       |    Root Complex     |   bus 0: host bridge, RCiEPs",
        "       |  RP0     RP1    RP2 |   each Root Port = virtual PCI-PCI bridge",
        "       +--+-------+------+---+",
        "          |       |      |       (each link = one bus number below a bridge)",
        "        NVMe     GPU   +-------------------+",
        "        (EP)     (EP)  |     Switch        |  upstream port + N downstream",
        "                       |  USP  DSP DSP DSP |  ports, all virtual PCI-PCI bridges",
        "                       +-------+---+---+---+",
        "                               |   |   |",
        "                              NIC  EP  EP     BDF = Bus[7:0] : Dev[4:0] . Fn[2:0]",
    ], "PCIe topology. Software sees a tree of PCI-PCI bridges and "
       "functions; hardware sees point-to-point links.")
    bul(["The **Root Complex** connects the CPU/memory system to the PCIe "
         "hierarchy. Each **Root Port** is its own hierarchy domain root.",
         "A **switch** has one upstream port and several downstream ports; "
         "internally it looks to software like a set of PCI-PCI bridges on "
         "an internal bus. It routes TLPs by address, by ID or implicitly.",
         "An **endpoint** has up to 8 functions (up to 256 with **ARI**, "
         "which reuses the 5 device bits because a link has only device 0 "
         "below it). Each function is identified by **BDF** = "
         "Bus:Device.Function, which is also its **Requester ID**.",
         "Configuration space is reached through **ECAM**: a memory window of "
         "4 KB per function, 1 MB per bus, 256 MB for 256 buses."])

    h2("The layered stack")
    diagram([
        "  Transmit                                                 Receive",
        "  +------------------ Transaction Layer -------------------+",
        "  | build TLP header (+ data, + optional ECRC)             | check ECRC, route,",
        "  | FC credit check (P / NP / Cpl)  ordering, VCs          | ordering, return credits",
        "  +------------------- Data Link Layer --------------------+",
        "  | + 12-bit sequence number (2 B), + LCRC (4 B)           | check LCRC + seq,",
        "  | replay buffer, ACK/NAK, DLLPs (UpdateFC, PM, ...)      | send ACK/NAK",
        "  +------------------- Physical Layer ---------------------+",
        "  | framing (STP/SDP/END or tokens), byte striping,        | deskew, descramble,",
        "  | scrambling, 8b/10b or 128b/130b or FLIT+FEC, SerDes    | decode, CDR, LTSSM",
        "  +--------------------------------------------------------+",
        "",
        "  TLP on the wire (Gen1-5):",
        "  | STP | Seq# (2B) | Header 12/16 B | Data 0-4096 B | ECRC 4B opt. | LCRC 4B | END |",
    ], "Each layer adds its own fields. In Gen6 FLIT mode the sequence "
       "number and CRC move from per-TLP to per-FLIT.")

    h2("Transaction layer")
    h3("TLP types")
    tbl(["TLP", "Fmt", "Type", "Class", "Notes"],
        [["MRd (Memory Read)", "000 / 001", "0 0000", "non-posted",
          "3DW (32-bit address) / 4DW (64-bit) header; answered by CplD"],
         ["MWr (Memory Write)", "010 / 011", "0 0000", "posted",
          "no completion; the most common TLP (DMA, doorbells, MSI)"],
         ["IORd / IOWr", "000 / 010", "0 0010", "non-posted", "legacy I/O space"],
         ["CfgRd0 / CfgWr0", "000 / 010", "0 0100", "non-posted",
          "type 0: to a function on this bus"],
         ["CfgRd1 / CfgWr1", "000 / 010", "0 0101", "non-posted",
          "type 1: forwarded by bridges, converted to type 0"],
         ["Msg / MsgD", "001 / 011", "1 0rrr", "posted",
          "rrr = routing (to RC, by address, by ID, broadcast, local); "
          "INTx emulation, PM, errors, vendor"],
         ["Cpl / CplD", "000 / 010", "0 1010", "completion",
          "status SC, UR, CA, CRS; carries read data"],
         ["AtomicOp", "010 / 011", "0 1100-0 1110", "non-posted",
          "FetchAdd, Swap, CAS; returns CplD"]],
        widths=[20, 12, 13, 13, 42], bold_first=True,
        caption="Main TLP types (non-FLIT header encoding). Fmt[0] selects a "
                "4DW header, Fmt[1] means the TLP carries data.")
    diagram([
        "        byte 0            byte 1                   byte 2                    byte 3",
        "  DW0  |Fmt[2:0] Type[4:0]|T9 TC[2:0] T8 A2 LN TH|TD EP Attr[1:0] AT[1:0] L[9:8]|L[7:0]|",
        "  DW1  |   Requester ID (BDF, 16 bits)           |   Tag (8)   | LastBE | 1stBE |",
        "  DW2  |   Address[31:2]  (Address[63:32] in a 4DW header)             | PH[1:0] |",
        "  DW3  |   Address[31:2]  (4DW header only)                             | PH[1:0] |",
        "",
        "  Completion:  DW1 = Completer ID | Status(3) | BCM | Byte Count(12)",
        "               DW2 = Requester ID | Tag | R | Lower Address(7)",
        "  Config:      DW2 = Bus(8) | Dev(5) | Fn(3) | Rsvd | ExtReg(4) | Reg(6) | R",
    ], "TLP header layouts (bytes transmitted left to right, DW0 first). "
       "Length is in DWs, 0 meaning 1024; TD marks an ECRC; EP marks "
       "poisoned data.")
    p("Building these headers is the first job of a transmit-side "
      "transaction layer. The subtle part is converting a byte address and "
      "byte count into a DW length and first/last byte enables, and "
      "choosing a 3DW or 4DW header (a 4DW header must not be used for an "
      "address below 4 GB). The package below does exactly that:")
    _v("tlp_pkg", "tlp_pkg.sv - header builders for MRd/MWr, CfgRd0 and CplD.")
    _v("tb_tlp", "tb_tlp.sv - builds six headers and prints them as DWs.")
    _o("tlp", "Real vvp output: DW0, DW1, DW2 (and DW3 for the 64-bit read).")
    _v("ref_tlp", "ref_tlp.py - an independent Python packer for the same "
       "six requests.")
    _o("ref_tlp", "Real Python output - identical to the RTL, DW for DW "
       "(checked with diff).")
    p("Read the results: the 2-byte read at 0x80000002 is a single-DW "
      "request with First BE = 1100 and Last BE = 0000; the 256-byte read "
      "starting at byte 1 touches 65 DWs (0x41) with First BE 1110 and "
      "Last BE 0001; the 4096-byte read encodes Length as 0. The CfgRd0 "
      "targets bus 01, device 0, function 0, register 0x10 (BAR0).")

    h3("Traffic classes, virtual channels and ordering")
    p("Each TLP carries a 3-bit **Traffic Class** (TC). A port maps TCs to "
      "**Virtual Channels** (VC0 is mandatory; most devices implement only "
      "VC0), each with its own buffers and credits so that one class cannot "
      "block another. Within a VC, TLPs are split into three flow-control "
      "classes with ordering rules designed for the producer-consumer model "
      "and deadlock freedom:")
    tbl(["Row passes column?", "Posted (MWr, Msg)", "Non-posted (MRd, Cfg, IO)",
         "Completion"],
        [["Posted", "No (Yes if RO / IDO)", "Yes - must be able to", "Yes (may)"],
         ["Non-posted", "No (Yes if RO / IDO)", "Yes (may)", "Yes (may)"],
         ["Completion", "No (Yes if RO / IDO)", "Yes - must be able to",
          "Yes, except same-tag completions of one request"]],
        widths=[22, 26, 26, 26], bold_first=True,
        caption="Simplified ordering table. 'No' guarantees that a flag "
                "written after data is never seen before the data. Posted "
                "requests must be able to pass stalled non-posted ones to "
                "avoid deadlock.")
    p("**Relaxed Ordering** (Attr bit RO) allows a TLP to pass posted writes "
      "when software knows ordering is not needed (for example data "
      "buffers, but not the completion flag); **ID-Based Ordering** (IDO) "
      "relaxes ordering between different requesters; **No Snoop** tells "
      "the root complex that the access does not need a cache snoop.")

    h3("Flow control credits")
    p("The receiver advertises buffer space in **credits** for six types: "
      "PH, PD, NPH, NPD, CplH, CplD (header and data credits for posted, "
      "non-posted and completion). One header credit holds one TLP header; "
      "one data credit is **16 bytes** (4 DW). Initial values are exchanged "
      "with **InitFC1/InitFC2** DLLPs during link initialization; an "
      "advertisement of 0 means infinite (endpoints normally advertise "
      "infinite completion credits because they only receive completions "
      "for reads they issued and sized for). As buffers drain, the receiver "
      "sends **UpdateFC** DLLPs with its new cumulative CREDITS_ALLOCATED.")
    eq(["TX:  CREDIT_LIMIT (CL)      <- value from InitFC / UpdateFC",
        "     CREDITS_CONSUMED (CC)  += credits of every TLP sent",
        "     may send TLP needing n  if (CL - (CC + n)) mod 2^F <= 2^F / 2",
        "     F = 8 for header, 12 for data credits (larger with scaled FC in Gen4+)"],
       "The transmitter gate. Both counters wrap; the modulo compare works "
       "as long as fewer than half the counter range is ever outstanding.")
    _v("fc", "fc.sv - one credit-type gate with modulo-2^F counters.")
    _v("tb_fc", "tb_fc.sv - 300 posted writes of 64-512 bytes into a receiver "
       "with 4 PH / 32 PD credits of buffer that drains slowly.")
    _o("fc", "Real vvp output. The 512-byte write needs all 32 data credits "
       "and waits until the receiver has drained everything (cycle 46). "
       "Both counters wrapped (300 mod 256 = 44, 4500 mod 4096 = 404) and "
       "the receiver buffer was never overrun.")
    box("key", "Credits size the receive buffer, and vice versa",
        ["Throughput is capped at (credits advertised) / (credit round-trip "
         "time). The round trip includes the TLP transmission, receiver "
         "pipeline, UpdateFC scheduling, DLLP transmission and TX pipeline - "
         "typically hundreds of ns to a few us. A Gen5 x16 port moving about "
         "63 GB/s with a 1 us credit loop needs on the order of 64 KB of "
         "posted-data buffer to keep the link full. Undersized receive "
         "buffers are the number-one cause of 'PCIe link at full width but "
         "half speed' performance bugs."])

    h2("Data link layer: sequence numbers, LCRC and replay")
    p("The data link layer makes each link reliable. The transmitter "
      "prepends a 12-bit **sequence number**, appends a 32-bit **LCRC** and "
      "keeps a copy in the **replay buffer**. The receiver checks LCRC and "
      "sequence; it returns an **Ack** DLLP (acknowledging everything up to "
      "a sequence number, coalesced by an AckNak latency timer) or a **Nak** "
      "on error. On Nak or when the **REPLAY_TIMER** expires, the "
      "transmitter replays everything unacknowledged from the buffer. "
      "After four replays of the same TLP (REPLAY_NUM rollover) the link "
      "is retrained through Recovery.")
    tbl(["DLLP", "Purpose"],
        [["Ack / Nak", "acknowledge / negatively acknowledge up to a sequence number"],
         ["InitFC1 / InitFC2 (P, NP, Cpl)", "advertise initial credits at link-up"],
         ["UpdateFC (P, NP, Cpl)", "return credits as receive buffers drain"],
         ["PM_Enter_L1, PM_Enter_L23, PM_Active_State_Request_L1, PM_Request_Ack",
          "power-management handshakes"],
         ["Feature (Gen4+)", "negotiate Data Link features such as scaled flow control"],
         ["Vendor-specific", "implementation defined"]],
        widths=[42, 58], bold_first=True,
        caption="DLLPs are 6 bytes on Gen1-5 links: 4 bytes of content plus a "
                "16-bit CRC; they are not sequence-numbered or replayed.")
    p("The replay buffer must hold every TLP sent during one Ack round "
      "trip, so its size scales with bandwidth x latency, exactly like the "
      "credit buffers. In Gen6 **FLIT mode** the unit of retry becomes the "
      "FLIT, and most errors are corrected by FEC before retry is needed, "
      "keeping the added latency to a few ns.")

    h2("Physical layer: LTSSM, training sets and equalization")
    diagram([
        "      +--------+     +---------+     +---------------+     +------+",
        "  --> | Detect | --> | Polling | --> | Configuration | --> |  L0  | <----+",
        "      +--------+     +---------+     +---------------+     +------+      |",
        "        Quiet         Active           Linkwidth.Start      |  |  |       |",
        "        Active        Configuration    Lanenum.Wait/Accept  |  |  v       |",
        "      (receiver       (TS1, TS2;       Complete, Idle       | L0s  L1 -> L2",
        "       detection)      polarity)       (width, lane nums)   v            |",
        "                                                      +----------+       |",
        "   Hot Reset, Disabled, Loopback, Compliance          | Recovery | ------+",
        "                                                      +----------+",
        "                                         RcvrLock, RcvrCfg, Speed, Idle,",
        "                                         Equalization phases 0-3 (8 GT/s+)",
    ], "The PCIe LTSSM (simplified). Every link comes up at 2.5 GT/s and "
       "then changes speed through Recovery.")
    bul(["**Detect**: the transmitter measures the charge time of the "
         "AC-coupled line to find a receiver termination on each lane.",
         "**Polling**: lanes exchange **TS1** and **TS2** training ordered "
         "sets to achieve bit and symbol (or block) lock. A lane that "
         "receives inverted TS symbols sets **polarity inversion** - D+ and "
         "D- swapped on the board are legal.",
         "**Configuration**: link width and lane numbers are negotiated; "
         "**lane reversal** (lane 0 wired to lane 15) is detected and "
         "handled here.",
         "**L0** is the normal state. Speed changes go through **Recovery**: "
         "at 8 GT/s and above, a four-phase **equalization** procedure tunes "
         "the transmitter FIR (pre-cursor, main, post-cursor coefficients; "
         "presets P0-P10) using feedback from the far receiver's eye "
         "measurement.",
         "Ordered sets: TS1, TS2, **SKP** (clock compensation: inserted "
         "periodically so an elastic buffer can absorb up to +/-300 ppm "
         "reference difference, or up to 5600 ppm with SRIS), EIOS/EIEOS "
         "(electrical idle), FTS (L0s exit), SDS (start of data stream)."])
    box("warn", "Pitfall: 'the link trained at Gen1 x4 instead of Gen4 x8'",
        ["A degraded link almost never shows up as a failure: the LTSSM "
         "happily settles for fewer lanes or a lower rate. Always read the "
         "negotiated width and speed from the Link Status register in "
         "bring-up scripts and fail the test if they differ from expectations. "
         "Common causes: a lane map mismatch between package and board, "
         "reference-clock (100 MHz, SSC or not) configuration, an equalization "
         "preset table left at defaults, or a PHY firmware version mismatch."])

    h2("Configuration space")
    diagram([
        " Type 0 header (endpoint)                  Type 1 header (bridge / port)",
        " 00 Device ID     | Vendor ID              00 Device ID      | Vendor ID",
        " 04 Status        | Command                04 Status         | Command",
        " 08 Class Code (24)          | Rev ID      08 Class Code (24)           | Rev ID",
        " 0C BIST|HdrType|LatTmr|CacheLn            0C BIST|HdrType(01)|LatTmr|CacheLn",
        " 10 BAR0                                   10 BAR0",
        " 14 BAR1                                   14 BAR1",
        " 18 BAR2                                   18 SecLat|Subord|Second.|Prim. Bus",
        " 1C BAR3                                   1C Sec.Status | IO Limit|IO Base",
        " 20 BAR4                                   20 Memory Limit | Memory Base",
        " 24 BAR5                                   24 Pref. Mem Limit | Pref. Mem Base",
        " 28 CardBus CIS ptr                        28..30 Pref. upper 32 / IO upper 16",
        " 2C Subsys ID     | Subsys Vendor ID       34 Capabilities Pointer",
        " 30 Expansion ROM base                     38 Expansion ROM base",
        " 34 Capabilities Pointer                   3C BridgeCtl | IntPin | IntLine",
        " 3C MaxLat|MinGnt|IntPin|IntLine",
        " 40..FF  capability list (PM, MSI, MSI-X, PCI Express capability ...)",
        " 100..FFF extended capabilities (AER, SR-IOV, ATS, L1 PM Substates ...)",
    ], "The 64-byte PCI-compatible headers, then 192 bytes of capabilities, "
       "then 3840 bytes of PCIe extended configuration space per function.")
    p("A **BAR** tells software how much address space a function needs and "
      "where it was placed. Software writes all ones, reads back, and the "
      "number of low-order zeros (in the writable bits) gives the size; "
      "bit 0 marks I/O vs memory, bits 2:1 mark 32/64-bit, bit 3 marks "
      "prefetchable. In RTL a BAR is simply a register whose low bits are "
      "hard-wired to 0 - an easy place to create a bug by making them "
      "writable. Capabilities are a linked list: each has an ID and a next "
      "pointer; common IDs are 0x01 PM, 0x05 MSI, 0x10 PCI Express, 0x11 "
      "MSI-X, and extended IDs 0x0001 AER, 0x000D ACS, 0x000E ARI, 0x000F "
      "ATS, 0x0010 SR-IOV, 0x001E L1 PM Substates.")
    h3("Interrupts: INTx, MSI and MSI-X")
    bul(["**INTx** emulation: Assert_INTx/Deassert_INTx messages mimic the "
         "four legacy level-triggered wires. Avoid for new designs.",
         "**MSI**: the function performs a posted **memory write** of a "
         "16-bit data value to an address programmed by software; up to 32 "
         "vectors (a power of two, contiguous data values).",
         "**MSI-X**: up to 2048 vectors, each with its own address, data and "
         "mask bit, in a **table** located in a BAR, plus a Pending Bit "
         "Array. This is what NICs and NVMe use (one vector per queue).",
         "Because an MSI is a posted write, it is ordered behind the DMA "
         "writes that preceded it: the interrupt can never overtake its data. "
         "That property (and not a sideband wire) is what makes MSI safe."])

    h2("Power management")
    tbl(["State", "Link", "Exit latency (typical)", "How entered"],
        [["L0", "active", "-", "normal operation"],
         ["L0s", "TX side in electrical idle", "tens of ns to ~1 us (FTS)",
          "ASPM, per direction, hardware idle timer (removed in FLIT mode)"],
         ["L1", "both directions idle, PLL may stay on", "~2-10 us",
          "ASPM (idle timer) or PCI-PM D-state change"],
         ["L1.1 / L1.2", "L1 + CLKREQ# deasserted; L1.2 also turns off "
          "common-mode keepers", "~tens of us (L1.2)", "L1 PM Substates capability"],
         ["L2 / L3", "main power off (L2 keeps aux power for wake)", "ms",
          "D3cold, system sleep"]],
        widths=[12, 34, 20, 34], bold_first=True)
    p("Device power states (D0, D3hot, D3cold) are separate from link "
      "states but interact with them. **LTR** (Latency Tolerance Reporting) "
      "lets a device tell the platform how much latency it can tolerate so "
      "that deep states are used safely. L1.2 matters most for battery "
      "devices: an NVMe SSD in a laptop spends most of its life there, and "
      "it drops PHY power to a few mW or less.")

    h2("Errors, AER and advanced features")
    tbl(["Class", "Examples", "Handling"],
        [["Correctable", "Receiver Error, Bad TLP, Bad DLLP, Replay Timer "
                         "Timeout, REPLAY_NUM Rollover",
          "fixed by hardware (retry); logged and counted"],
         ["Uncorrectable non-fatal", "Poisoned TLP, Completion Timeout, "
          "Unexpected Completion, Unsupported Request, Completer Abort, ECRC Error",
          "transaction lost, link fine; driver recovery"],
         ["Uncorrectable fatal", "Data Link Protocol Error, Surprise Down, "
          "Flow Control Protocol Error, Receiver Overflow, Malformed TLP",
          "link unreliable; reset (or DPC contains it)"]],
        widths=[20, 50, 30], bold_first=True,
        caption="Error classes reported through the Advanced Error Reporting "
                "(AER) extended capability, which also logs the offending "
                "TLP header.")
    bul(["**Completion timeout**: every non-posted request needs a timer; "
         "the requester must release the tag and report an error if no "
         "completion arrives (ranges from 50 us to seconds are programmable).",
         "**DPC** (Downstream Port Containment) stops traffic below a port "
         "on a fatal error so that one bad device cannot crash the system.",
         "**SR-IOV**: a Physical Function (PF) exposes many **Virtual "
         "Functions** (VFs), each with its own Requester ID, BARs (carved "
         "from VF BARs) and MSI-X, so a VM can own a VF directly.",
         "**ATS/PRI/PASID**: a device caches address translations in an "
         "**ATC** by sending Translation Requests to the IOMMU (ATS), asks "
         "for pages to be made resident (PRI), and tags requests with a "
         "process address space ID (PASID prefix) for shared virtual memory.",
         "**IDE** (Integrity and Data Encryption) secures TLPs with AES-GCM "
         "per stream (Chapter 26)."])

    h2("PIPE: between controller and PHY")
    p("The **PIPE** specification (PHY Interface for PCI Express, SATA, USB "
      "and USB4 architectures, from Intel) standardizes the boundary between "
      "the controller's MAC (LTSSM, framing) and the PHY (SerDes). It is "
      "what lets an SoC team buy a PHY from one vendor and a controller from "
      "another.")
    tbl(["Signal group", "Examples", "Direction / notes"],
        [["Transmit data", "TxData[31:0], TxDataK / TxDataValid, TxStartBlock, "
                           "TxSyncHeader", "MAC -> PHY, at PCLK, width 8-64 bits"],
         ["Receive data", "RxData, RxDataK, RxValid, RxStartBlock, "
                          "RxSyncHeader, RxStatus[2:0]",
          "PHY -> MAC; RxStatus reports decode/disparity/elastic-buffer events"],
         ["Control", "PowerDown[3:0], Rate, Width, TxDetectRx/Loopback, "
                     "TxElecIdle, RxPolarity, TxDeemph / coefficients",
          "MAC -> PHY"],
         ["Status", "PhyStatus, RxElecIdle, RxEqEval feedback",
          "PHY -> MAC; PhyStatus acknowledges rate and power changes"],
         ["Message bus (PIPE 5+)", "M2P_MessageBus[7:0], P2M_MessageBus[7:0]",
          "register access replacing many sideband wires"]],
        widths=[20, 46, 34], bold_first=True)
    p("Two PIPE architectures exist. In the original one the PHY contains "
      "8b/10b or 128b/130b coding, the elastic buffer and receiver "
      "detection; in the newer **SerDes architecture** the PHY is little "
      "more than a serializer/deserializer with CDR, and the MAC does "
      "encoding, block alignment and clock compensation. The latter needs "
      "more controller RTL but makes PHYs simpler and more reusable across "
      "protocols.")

    h2("Controller design considerations")
    bul(["**Datapath width vs clock**: a Gen5 x16 port carries about 64 GB/s "
         "per direction, i.e. 512 bits at 1 GHz or 1024 bits at 500 MHz. "
         "At these widths several TLPs can start and end in the same cycle; "
         "TLP straddling logic (multiple SOP/EOP per beat) dominates RTL "
         "complexity.",
         "**Buffers**: replay buffer, posted/non-posted/completion receive "
         "queues sized from the credit round trip; completion reassembly "
         "for split read completions (Read Completion Boundary 64/128 B, "
         "Max_Read_Request_Size up to 4 KB, Max_Payload_Size 128 B-4 KB).",
         "**Tags**: 8-bit, 10-bit (Gen4+) or 14-bit (FLIT mode) tags; the "
         "number of outstanding reads x read size must cover memory latency "
         "x bandwidth, or reads will not saturate the link.",
         "**Bridging to the SoC**: an AXI bridge with inbound and outbound "
         "address translation windows (iATU), MSI capture in the root "
         "complex, DMA engines, and error/interrupt reporting to the GIC. "
         "Ordering rules must be preserved across the AXI boundary, which "
         "has different rules (Chapter 7).",
         "**Clocks and resets**: PIPE PCLK (changes with rate), core clock, "
         "AXI clock and aux clock (for L1.2/L2); PERST# fundamental reset; "
         "hot reset and FLR (function level reset) of individual functions.",
         "**Verification**: PCIe VIP, compliance test suites (the PCI-SIG "
         "Compliance Workshop), LTSSM coverage, error injection (LCRC, "
         "sequence, credit overflow, completion timeout) and long "
         "interoperability runs on FPGA or emulation with real drivers."])

    h2("CXL: Compute Express Link")
    p("**CXL** reuses the PCIe physical layer and electricals but adds "
      "coherent memory semantics. After link training in PCIe mode, the "
      "link negotiates CXL through **Alternate Protocol Negotiation** and "
      "then carries three multiplexed protocols in fixed-size flits:")
    tbl(["Protocol", "Direction", "What it does"],
        [["CXL.io", "both", "PCIe-equivalent: discovery, configuration, "
                            "interrupts, DMA, register access"],
         ["CXL.cache", "device -> host memory",
          "lets a device cache host memory coherently (the host is the home; "
          "channels H2D/D2H request, response, data)"],
         ["CXL.mem", "host -> device memory",
          "lets the host load/store device-attached memory with low latency "
          "(M2S Req/RwD, S2M NDR/DRS)"]],
        widths=[14, 22, 64], bold_first=True)
    tbl(["Device type", "Protocols", "Examples"],
        [["Type 1", "CXL.io + CXL.cache", "SmartNIC or accelerator without "
                                         "its own memory, caching host data"],
         ["Type 2", "CXL.io + CXL.cache + CXL.mem", "GPU/accelerator with "
          "local memory (HDM) shared coherently with the host"],
         ["Type 3", "CXL.io + CXL.mem", "memory expander: DRAM behind a CXL "
                                        "controller, pooled memory"]],
        widths=[14, 30, 56], bold_first=True)
    tbl(["Version", "Year", "PHY", "Key additions"],
        [["1.0 / 1.1", "2019", "PCIe 5.0, 32 GT/s", "direct attach, 68-byte flits, "
                                                   "Types 1-3"],
         ["2.0", "2020", "PCIe 5.0", "single-level switching, memory pooling with "
          "multi-logical devices (up to 16 LDs), hot plug, IDE link security"],
         ["3.0", "2022", "PCIe 6.0, 64 GT/s", "256-byte flits, multi-level switching "
          "and fabrics, memory sharing, back-invalidate for coherent device memory"],
         ["3.1 / 3.2", "2023 / 2024", "PCIe 6.x", "fabric and security "
                                                  "extensions, improved RAS and monitoring"]],
        widths=[12, 12, 20, 56], bold_first=True)
    p("Why CXL matters: the **CXL.cache/CXL.mem** paths bypass the PCIe "
      "transaction layer and its ordering machinery, so a load to CXL-attached "
      "memory costs roughly one extra NUMA hop (on the order of 100+ ns over "
      "local DRAM) rather than the microseconds of a PCIe DMA round trip. "
      "Type 3 memory expanders let servers add DRAM capacity and bandwidth "
      "without more DDR channels, and pooling lets that memory be assigned "
      "to hosts dynamically. The coherence protocol is a MESI-style "
      "host-managed scheme (Chapter 9); the device-side **DCOH** (device "
      "coherency engine) and the host's **home agent** are the new RTL "
      "blocks.")
    box("expert", "Expert note: latency, not bandwidth, is the CXL design goal",
        ["A CXL controller's RTL budget is dominated by latency: flit "
         "packing without waiting for a full flit, bypass paths around the "
         "CXL.io stack, and tight ARB/MUX logic. A PCIe endpoint that adds "
         "100 ns of pipeline is fine; a CXL.mem device that does the same "
         "doubles its added latency. Measure load-to-use latency in "
         "simulation from the first design review."])

    h2("Summary")
    bul(["PCIe is a point-to-point, packet-switched link that preserves the "
         "PCI software model (BDF, config space, BARs, capabilities).",
         "Rates double each generation: 8b/10b to Gen2, 128b/130b for Gen3-5, "
         "PAM4 + FLIT + FEC for Gen6/7.",
         "Transaction layer: TLPs (MRd/MWr/Cfg/Cpl/Msg/AtomicOp), three "
         "flow-control classes with credit gating (modulo compare) and "
         "ordering rules that keep producer-consumer correct and deadlock-free.",
         "Data link layer: sequence numbers, LCRC, replay buffer, Ack/Nak "
         "and flow-control DLLPs. Physical layer: LTSSM, TS1/TS2, "
         "equalization, polarity inversion and lane reversal.",
         "MSI/MSI-X are posted writes; power states L0s/L1/L1.x; AER, DPC, "
         "SR-IOV and ATS are standard server features.",
         "PIPE separates controller and PHY; CXL adds CXL.cache and CXL.mem "
         "for coherent, low-latency device and memory attach."])

    h2("Exercises")
    bul(["Use `tlp_pkg` to build the headers of: a 64-byte MWr to "
         "0x1_0000_0000; a 1-byte MRd at 0x1003; a CplD returning 128 of 256 "
         "requested bytes (what is Byte Count?). Check them with `ref_tlp.py`.",
         "A 4096-byte MRd is issued with a Read Completion Boundary of 64 B "
         "and Max_Payload_Size 256 B. List the possible completion sizes and "
         "the Lower Address / Byte Count fields of each.",
         "Modify `tb_fc.sv` so the receiver drains every 4 cycles and the "
         "UpdateFC latency is 40 cycles. How many data credits are needed "
         "to keep the transmitter from stalling? Verify by simulation.",
         "Explain why posted writes must be allowed to pass non-posted "
         "requests. Construct the deadlock that occurs otherwise with two "
         "devices doing peer-to-peer traffic.",
         "Estimate the replay buffer size for a Gen4 x8 port whose Ack "
         "round-trip is 700 ns.",
         "Compare MSI and a sideband interrupt wire from an endpoint's DMA "
         "engine: which ordering hazard does MSI remove?"],
        ordered=True)


# ---------------------------------------------------------------- Ch 19 ---
def _ch19():
    chapter("Ethernet: MAC, PHY and the xMII Family")
    p("Ethernet (IEEE 802.3) has run from 10 Mb/s coax in the 1980s to "
      "800 Gb/s optics today while keeping one thing constant: the **MAC "
      "frame**. Everything below the MAC - line codes, FEC, lanes, "
      "copper or fiber - has been replaced many times, but a frame captured "
      "on a 400G data-center link has the same header and the same CRC-32 "
      "FCS as one on a 1983 thick-coax network. For an SoC this layering is "
      "the key to the design: the MAC is digital RTL you write or license; "
      "the PHY is a separate chip or a hard macro; and a standard "
      "**media-independent interface** (the xMII family) joins them. "
      "Automotive Ethernet PHYs (100BASE-T1, 1000BASE-T1) are covered in "
      "Chapter 15; MDIO electrical details in Chapter 16.")

    h2("IEEE 802.3 and the layer model")
    diagram([
        "   OSI            IEEE 802.3 sublayers                      where it lives",
        "  +-------+   +----------------------------------------+",
        "  | Data  |   | MAC client (LLC / bridge / IP stack)   |   software, switch logic",
        "  | link  |   | MAC control (PAUSE, PFC)  - optional   |   RTL (MAC IP)",
        "  |       |   | MAC  (framing, FCS, addressing)        |   RTL (MAC IP)",
        "  +-------+   | Reconciliation Sublayer (RS)           |   RTL",
        "  |       |   +------ xMII: MII/RMII/GMII/RGMII/ ------+   <- pins or on-die bus",
        "  | Phys- |   | PCS  (4B5B, 8b/10b, 64b/66b, lanes)    |   PHY chip or SerDes RTL",
        "  | ical  |   | FEC  (RS-FEC, BASE-R FEC) - by speed   |   PHY / SerDes RTL",
        "  |       |   | PMA  (serialize, CDR, bit mux)         |   analog SerDes",
        "  |       |   | PMD  (optics / copper driver)          |   module / analog",
        "  |       |   | AN   (auto-negotiation)                |   PHY",
        "  +-------+   +----------------------------------------+",
        "                              MDI: connector / medium",
    ], "The 802.3 layering. The xMII is the boundary most SoC designers "
       "integrate; the PCS/PMA may be on-chip (SerDes-based SoCs) or in an "
       "external PHY (BASE-T copper).")

    h2("The frame")
    diagram([
        " | Preamble | SFD | Dest MAC | Src MAC | [802.1Q tag] | Type/Len | Payload     | FCS  |",
        " |  7 x 55  |  D5 |    6     |    6    | 81 00 + TCI  |    2     | 46..1500    |  4   |",
        " |<-- 8 bytes --->|<----------- 64 .. 1518 bytes (1522 with one VLAN tag) --------->|",
        "                                                        then IFG >= 12 byte times",
        "",
        " TCI (16 bits) = PCP[2:0] priority | DEI | VID[11:0] VLAN id",
        " Type/Len >= 0x0600: EtherType (0x0800 IPv4, 0x86DD IPv6, 0x0806 ARP,",
        "                     0x8100 VLAN, 0x88A8 S-tag, 0x8808 MAC control, 0x88F7 PTP)",
        " Type/Len <= 1500:   length of an 802.3 / LLC frame",
    ], "Ethernet frame format. The minimum frame (64 bytes from destination "
       "to FCS) came from CSMA/CD collision detection and was kept forever.")
    bul(["**Preamble + SFD**: 7 bytes of 0x55 and 0xD5. On the wire, LSB "
         "first, this is 62 alternating bits ending in '11' - originally "
         "for receiver clock sync, today mainly a delimiter (10G+ PCS "
         "encodes the start as a control character in lane 0).",
         "**Addresses**: 48-bit MACs. Bit 0 of the first byte is the I/G "
         "bit (1 = multicast/broadcast; FF:FF:FF:FF:FF:FF is broadcast), "
         "bit 1 is U/L (1 = locally administered).",
         "**Payload** 46-1500 bytes; shorter payloads are **padded** with "
         "zeros so the frame reaches 64 bytes. **Jumbo frames** (typically "
         "up to ~9000-9216 bytes) are a widely used non-standard extension.",
         "**FCS**: CRC-32 (polynomial 0x04C11DB7, reflected, initial value "
         "all ones, final complement) over destination address through "
         "padding - the same CRC as zlib/PNG. It is transmitted so that "
         "its least-significant byte in the 'reflected' convention goes "
         "first, which is why `struct.pack('<I', zlib.crc32(frame))` gives "
         "the on-wire FCS bytes.",
         "**IFG**: at least 96 bit times (12 bytes) of idle between frames. "
         "Together with preamble/SFD this adds 20 bytes of overhead to every "
         "frame."])
    eq(["wire bytes per minimum frame = 8 + 64 + 12 = 84 bytes = 672 bits",
        "max frame rate at 10 Gb/s   = 10e9 / 672 = 14.88 Mframes/s",
        "payload efficiency at 1500 B = 1500 / (1500 + 18 + 20) = 97.5%"],
       "The famous line-rate numbers. A 10G MAC must accept a new frame "
       "every 67.2 ns; at 100G every 6.7 ns - i.e. every few clock cycles.")

    h2("Speeds and PHY types")
    tbl(["Speed", "Example PHY", "Line code / modulation", "Standard"],
        [["10 Mb/s", "10BASE-T", "Manchester", "802.3i (1990)"],
         ["100 Mb/s", "100BASE-TX", "4B5B + MLT-3, 125 MBd", "802.3u (1995)"],
         ["1 Gb/s", "1000BASE-T / -X (SX, LX)", "4 pairs PAM5 / 8b/10b at 1.25 GBd",
          "802.3ab / 802.3z"],
         ["2.5 / 5 Gb/s", "2.5G/5GBASE-T", "reduced-rate 10GBASE-T coding", "802.3bz (2016)"],
         ["10 Gb/s", "10GBASE-R (SR/LR/KR), 10GBASE-T", "64b/66b at 10.3125 GBd; "
          "PAM16 (DSQ128) on copper", "802.3ae / 802.3an"],
         ["25 Gb/s", "25GBASE-R", "64b/66b at 25.78125 GBd, optional RS-FEC",
          "802.3by (2016)"],
         ["40 / 100 Gb/s", "40GBASE-R4, 100GBASE-R4", "4 x 10G / 4 x 25G lanes, "
          "RS(528,514) FEC", "802.3ba / 802.3bm"],
         ["200 / 400 Gb/s", "400GBASE-SR8 / -FR8", "PAM4, 26.5625 GBd per 50G lane, "
          "RS(544,514) FEC", "802.3bs (2017)"],
         ["100G per lane", "100/200/400GBASE-KR1/2/4...", "PAM4 at 53.125 GBd",
          "802.3ck (2022)"],
         ["800 Gb/s", "800GBASE-R8", "8 x 100G PAM4 lanes", "802.3df (2024)"],
         ["1.6 Tb/s", "200G-per-lane PAM4", "~106 GBd PAM4", "802.3dj (in progress)"]],
        widths=[14, 27, 36, 23], bold_first=True)
    p("From 10G upward, the MAC and PCS talk through a wide internal "
      "interface, the PCS uses **64b/66b** blocks (2-bit sync header + 64 "
      "scrambled bits, self-synchronizing scrambler x^58 + x^39 + 1) and "
      "multi-lane speeds insert **alignment markers** so the receiver can "
      "deskew lanes. From 50G-per-lane PAM4 onwards, **RS-FEC** is mandatory "
      "and adds on the order of 100 ns of latency - a real concern for "
      "low-latency trading and AI clusters.")

    h2("MAC functions")
    bul(["**Transmit**: prepend preamble/SFD, insert source address (optional), "
         "pad short frames, compute and append the FCS, enforce IFG, "
         "handle PAUSE (stop transmitting when paused), and, in the rare "
         "half-duplex 10/100 mode, CSMA/CD with backoff.",
         "**Receive**: detect SFD, check FCS, check length (runts < 64 bytes, "
         "oversize > max), filter destination address (exact match, "
         "multicast hash, promiscuous), strip FCS/padding if configured, "
         "recognize MAC control frames, and count everything in "
         "**statistics counters** (the RMON / 802.3 MIB).",
         "**Management**: MDIO master to read PHY registers, link state "
         "tracking, speed/duplex configuration from auto-negotiation results."])

    h2("The xMII family")
    tbl(["Interface", "Speed", "Data path", "Clock", "Signals (approx.)"],
        [["MII", "10/100M", "4-bit TXD/RXD", "25 / 2.5 MHz, from PHY (TX_CLK, RX_CLK)",
          "16 + MDC/MDIO"],
         ["RMII", "10/100M", "2-bit", "50 MHz REF_CLK shared", "7-8 + MDIO"],
         ["GMII", "1G", "8-bit", "125 MHz; GTX_CLK from MAC", "24-25 + MDIO"],
         ["RGMII", "10M-1G", "4-bit DDR", "125 MHz DDR (25 / 2.5 MHz at 100/10)",
          "12 + MDIO"],
         ["SGMII", "10M-1G", "serial 8b/10b", "1.25 GBd LVDS pair each way",
          "4 (8 with clocks)"],
         ["XGMII", "10G", "32-bit + 4 ctrl, DDR", "156.25 MHz", "74"],
         ["XAUI", "10G", "4 lanes 8b/10b", "3.125 GBd per lane", "16"],
         ["XFI / SFI", "10G", "1 serial lane 64b/66b", "10.3125 GBd", "4"],
         ["USXGMII", "10M-10G", "1 serial lane, rate replication", "10.3125 GBd", "4"],
         ["CAUI-4 / 100GAUI-2", "100G", "4 x 25G NRZ / 2 x 50G PAM4", "25.78 / 26.56 GBd",
          "16 / 8"]],
        widths=[16, 10, 22, 32, 20], bold_first=True,
        caption="Media-independent interfaces. Pin counts exclude power and the "
                "two MDIO wires.")
    diagram([
        "  RGMII transmit (1 Gb/s), one byte per 8 ns TXC period",
        "",
        "  TXC     ___/~~~~~~~\\_______/~~~~~~~\\_______/~~~~~~~\\___",
        "  TXD[3:0] ==X= b[3:0] =X= b[7:4] =X= b[3:0] =X= b[7:4] =X==",
        "  TX_CTL  ==X= TX_EN  =X= EN^ER  =X= TX_EN  =X= EN^ER  =X==",
        "              rising edge   falling edge",
        "",
        "  Data changes with the clock edge at the MAC pins (RGMII 1.x) -> a delay of",
        "  about 1.5-2 ns must be added (in the PHY: 'RGMII-ID', in the MAC, or on the",
        "  board) so the receiver samples in the middle of the data eye.",
    ], "RGMII halves GMII's pin count by using both clock edges, and "
       "multiplexes TX_EN and TX_ER onto one control pin.")
    box("warn", "Pitfall: RGMII delay applied twice (or not at all)",
        ["The single most common Ethernet bring-up bug on SoC boards: the "
         "2 ns RGMII clock delay must be inserted exactly once per direction "
         "- by the PHY (rgmii-id / rgmii-txid / rgmii-rxid in the Linux "
         "device tree), by the MAC's I/O delay lines, or by PCB trace "
         "length. Zero or double delay gives a link that negotiates fine "
         "(MDIO and auto-negotiation work) but drops or corrupts frames, "
         "often only at one temperature. Put the delay configuration in the "
         "SoC integration checklist and test at 10, 100 and 1000 Mb/s."])
    p("**SGMII** deserves a note: it carries the GMII byte stream over one "
      "1.25 GBd 8b/10b SerDes lane per direction (1000BASE-X coding), and "
      "supports 100M and 10M by repeating each byte 10 or 100 times. Its "
      "in-band auto-negotiation word (a Cisco-defined variant of Clause 37) "
      "tells the MAC the PHY's speed and link state. **USXGMII** extends the "
      "same idea to 10M-10G on a 10.3125 GBd lane, and multi-port variants "
      "carry several ports on one lane for switch-to-PHY links.")

    h2("Auto-negotiation and MDIO management")
    p("Twisted-pair PHYs negotiate speed and duplex with **Clause 28** "
      "auto-negotiation: each side sends **Fast Link Pulse** bursts encoding "
      "a 16-bit link code word (selector field, technology ability, remote "
      "fault, next page). Both sides pick the highest common ability by a "
      "fixed priority; 1000BASE-T adds next pages for master/slave "
      "resolution (who provides the clock). Backplane (KR) links use "
      "**Clause 73**, and 1000BASE-X uses **Clause 37**. If one side has "
      "auto-negotiation disabled, 'parallel detection' guesses the speed "
      "but must assume half duplex - the source of the classic duplex "
      "mismatch that gives a working but terribly slow link.")
    diagram([
        " Clause 22 MDIO frame (MDC <= 2.5 MHz, MDIO open-drain, sampled on MDC rising)",
        " | PRE (32 x 1) | ST 01 | OP 10=rd 01=wr | PHYAD 5 | REGAD 5 | TA 2 | DATA 16 | idle",
        "",
        " Clause 45: ST 00, 'address' frame then read/write frame;",
        "            PRTAD 5 | DEVAD 5 (MMD: PMA, PCS, AN ...) | 16-bit register address",
    ], "MDIO management frames (details in Chapter 16). Registers 0 "
       "(control) and 1 (status) of every Clause 22 PHY are standardized; "
       "bit 2 of register 1 is Link Status (latching low).")

    h2("Flow control: PAUSE and PFC")
    p("**PAUSE** (802.3x, Annex 31B) is a MAC control frame: destination "
      "01-80-C2-00-00-01, EtherType **0x8808**, opcode **0x0001** and a "
      "16-bit pause time in **quanta of 512 bit times**. A receiver whose "
      "buffers are filling sends PAUSE; the link partner's MAC stops "
      "transmitting (after finishing the current frame) for that time, or "
      "until a PAUSE with time 0. PAUSE stops the whole link, which causes "
      "head-of-line blocking, so data centers use **Priority Flow Control** "
      "(PFC, 802.1Qbb): opcode **0x0101**, an 8-bit class-enable vector and "
      "eight timers, pausing only selected priorities. PFC is what makes "
      "Ethernet 'lossless' enough for RoCE (RDMA over Converged Ethernet).")
    eq(["one quantum = 512 bit times = 51.2 ns at 10 Gb/s",
        "pause 0xFFFF quanta at 10 Gb/s = 65535 x 51.2 ns = 3.36 ms",
        "headroom needed >= (cable + PHY + MAC delay) x 2 x rate + 1 max frame"],
       "PAUSE arithmetic. The receiver must still absorb what is in flight "
       "after it sends PAUSE: buffer headroom grows with speed and cable length.")

    h2("Precision time: IEEE 1588 PTP")
    p("The **Precision Time Protocol** synchronizes clocks across a network "
      "to sub-microsecond (with hardware support, nanosecond-level) "
      "accuracy. A master sends **Sync** (and, in two-step mode, a "
      "**Follow_Up** carrying the precise transmit time t1); the slave "
      "records receive time t2, sends **Delay_Req** at t3 and gets t4 back "
      "in **Delay_Resp**.")
    eq(["mean path delay = ((t2 - t1) + (t4 - t3)) / 2",
        "offset          = ((t2 - t1) - (t4 - t3)) / 2     (assumes symmetric path)"],
       "The PTP servo equations.")
    bul(["Accuracy comes from **hardware timestamping**: the MAC (or PHY) "
         "latches a free-running, frequency-adjustable time counter when the "
         "SFD passes the xMII, so software and queueing delays are excluded.",
         "**One-step** mode writes t1 into the Sync frame on the fly (the MAC "
         "must patch the field and fix the UDP checksum / FCS in flight); "
         "**two-step** sends it in Follow_Up.",
         "Transparent clocks in switches add their residence time to a "
         "correction field. **gPTP** (IEEE 802.1AS) is the profile used by "
         "TSN and automotive.",
         "RTL owns: the timer with fractional increment (e.g. 32.32 "
         "fixed-point nanoseconds per clock) for frequency trimming, "
         "timestamp capture at a fixed pipeline point with known latency, "
         "PPS output and external timestamp inputs."])

    h2("Time-Sensitive Networking (TSN)")
    tbl(["Standard", "Mechanism", "Purpose"],
        [["802.1AS", "gPTP time synchronization", "common time base for all nodes"],
         ["802.1Qav", "credit-based shaper", "smooth audio/video (AVB) streams, "
                                             "bounded latency"],
         ["802.1Qbv", "time-aware shaper: gate control list opens/closes each "
                      "queue on a time schedule", "hard real-time slots (control loops)"],
         ["802.1Qbu / 802.3br", "frame preemption", "express frames interrupt "
                                                    "long frames to cut latency"],
         ["802.1CB", "frame replication and elimination", "seamless redundancy"],
         ["802.1Qci", "per-stream filtering and policing", "protect the schedule "
                                                           "from misbehaving talkers"]],
        widths=[20, 42, 38], bold_first=True)
    p("TSN turns best-effort Ethernet into a deterministic network for "
      "industrial control and in-vehicle backbones. In the MAC this means "
      "multiple transmit queues, per-queue gates driven by the PTP time, "
      "shapers, and a preemptible/express MAC pair.")

    h2("NIC offloads")
    bul(["**Checksum offload**: compute IPv4 header and TCP/UDP one's-complement "
         "checksums in the MAC (store-and-forward, because the checksum field "
         "precedes the data it covers) or verify them on receive.",
         "**TSO/LSO**: software hands one large buffer (up to 64 KB) and a "
         "header template; hardware cuts MSS-sized segments, updates IP ID, "
         "TCP sequence numbers, flags and checksums. **LRO/GRO** does the "
         "reverse on receive.",
         "**RSS**: a Toeplitz hash of the 5-tuple indexes an indirection table "
         "that selects a receive queue (and so a CPU core), spreading load "
         "while keeping each flow in order.",
         "**VLAN tag insertion/stripping**, multiple DMA rings with interrupt "
         "moderation, SR-IOV virtual functions (Chapter 18), and in "
         "data-center NICs, RDMA and crypto offload (MACsec, Chapter 26)."])

    h2("A MAC in RTL: TX framer and RX FCS checker")
    p("A MAC's transmit path is a small state machine around a CRC. Below "
      "is a complete GMII-style (8-bit, 125 MHz) framer: it takes a frame "
      "(destination MAC to end of payload) on a ready/valid stream, sends "
      "preamble and SFD, forwards the data, **pads** to 60 bytes, appends "
      "the complemented CRC LSB-first and enforces a 12-byte IFG. The "
      "receive checker runs the same CRC over data **and** FCS and compares "
      "with the constant residue 0xDEBB20E3 - no need to buffer the last "
      "four bytes to know where the FCS starts.")
    _v("eth", "eth.sv - byte-wide CRC-32, MAC TX framer and RX FCS checker.")
    _v("tb_eth", "tb_eth.sv - sends a 42-byte ARP-style frame (padded to 60), "
       "loops it into the checker, then repeats it with one bit flipped on "
       "the wire.")
    _o("eth", "Real vvp output: 72 bytes on the GMII (8 preamble/SFD + 60 "
       "frame + 4 FCS); FCS bytes a9 5a b7 99; the corrupted copy is "
       "rejected.")
    _v("ref_eth", "ref_eth.py - reference FCS with Python's zlib.crc32 and "
       "the residue check.")
    _o("ref_eth", "Real Python output. zlib.crc32 over the padded 60 bytes "
       "gives exactly the FCS the RTL transmitted, and the residue over "
       "frame + FCS is 0xDEBB20E3, the constant the RX checker compares to.")
    box("intuit", "Why a residue check works",
        ["Appending the complemented CRC makes the whole codeword (data + "
         "FCS) satisfy a fixed polynomial identity, so the LFSR state after "
         "the last FCS byte is the same constant for every good frame. The "
         "receiver just keeps clocking the CRC to the end of the frame and "
         "compares once, when RX_DV falls. USB's CRC16 residual 0x800D in "
         "Chapter 17 is the same trick."])
    h3("From 1G to 100G: what changes in the RTL")
    bul(["**Width**: 8 bits at 125 MHz (1G) becomes 64 bits at 156.25 MHz "
         "(10G), 64 bits at 390.625 MHz (25G) and 256-512 bits at a few "
         "hundred MHz for 100G-400G. The CRC must then process 8-64 bytes "
         "per clock: a parallel CRC (XOR tree derived from the matrix form), "
         "with a separate final stage for frames that end mid-word.",
         "**Alignment**: on XGMII a frame may start in lane 0 or lane 4; "
         "wider buses let two frames share a beat, so start/end detection, "
         "padding and FCS insertion become multi-lane problems (the same "
         "straddling problem as PCIe TLPs).",
         "**FIFOs**: TX FIFO for store-and-forward (checksum insertion, no "
         "underrun mid-frame - an underrun must be signalled with TX_ER or "
         "a bad FCS so the frame is dropped, never truncated silently); RX "
         "FIFO with drop-on-overflow at frame granularity and a status word "
         "per frame.",
         "**Clock domains**: the xMII/PCS clock (from the PHY or SerDes) is "
         "not the system clock; async FIFOs sit between MAC and DMA. The "
         "clock-compensation 'IFG stretching/shrinking' happens in the PCS."])

    h2("Where Ethernet sits in an SoC")
    tbl(["Block", "Typical owner", "Notes"],
        [["MAC + DMA (GMAC, XGMAC)", "RTL (licensed IP), integration", "AXI master for "
          "descriptors/data, APB/AXI-Lite for registers, interrupts"],
         ["PCS/PMA (SerDes-based)", "PHY team / vendor hard macro",
          "shared SerDes with PCIe/USB in many SoCs (combo PHY)"],
         ["External PHY (BASE-T)", "board / PHY vendor",
          "RGMII or SGMII to the SoC; MDIO for control"],
         ["Switch (multi-port)", "RTL", "lookup tables, queues, TSN, often "
                                       "integrated in automotive SoCs"],
         ["Drivers, PTP stack, TSN config", "software", "Linux stmmac/fec-style "
                                                       "drivers, linuxptp"]],
        widths=[26, 30, 44], bold_first=True)

    h2("Summary")
    bul(["The 802.3 MAC frame is fixed across all speeds: preamble, SFD, "
         "addresses, optional VLAN tag, EtherType/length, 46-1500 bytes "
         "payload, CRC-32 FCS, then at least 12 bytes of IFG.",
         "The PHY is split into PCS/FEC/PMA/PMD; the MAC-PHY boundary is an "
         "xMII: MII/RMII/GMII/RGMII in parallel, SGMII/USXGMII/XFI/CAUI in "
         "serial form.",
         "Auto-negotiation (Clause 28/37/73) picks speed and duplex; MDIO "
         "(Clause 22/45) manages PHY registers.",
         "PAUSE and PFC provide flow control; PTP with hardware timestamps "
         "gives ns-level time; TSN adds scheduled, shaped, preemptible traffic.",
         "The RTL MAC is a framer + CRC + FIFOs; wide MACs add parallel CRC "
         "and multi-frame-per-beat alignment. The FCS equals zlib.crc32 of the "
         "frame, and a receiver can check a fixed residue."])

    h2("Exercises")
    bul(["Modify `eth_tx_framer` to insert an 802.1Q VLAN tag (0x8100 + TCI) "
         "after the source address. What happens to the minimum payload? "
         "Check the new FCS with zlib.",
         "Add a destination-address filter to `eth_rx_fcs` that accepts only "
         "broadcast and one programmable unicast address.",
         "Compute the maximum frame rate and payload throughput at 25 Gb/s "
         "for 64-, 512- and 1518-byte frames.",
         "A 100 m 10GBASE-T link is paused with PFC. Estimate the buffer "
         "headroom needed per priority (propagation about 5 ns/m, PHY latency "
         "on the order of 2-3 us each way).",
         "Derive the RGMII setup/hold budget at 125 MHz DDR: the bit period is "
         "4 ns; with 2 ns of added delay and +/-500 ps of skew, what margin "
         "remains?",
         "Write the equations for a two-step PTP exchange with an asymmetric "
         "path (forward delay d1, reverse d2). What offset error results?"],
        ordered=True)


# ---------------------------------------------------------------- Ch 20 ---
def _ch20():
    chapter("Memory Interfaces: SDRAM, DDR4/DDR5, LPDDR, HBM, DFI and Flash")
    p("Every processor, GPU and AI accelerator is ultimately limited by how "
      "fast it can move data to and from memory, so the DRAM interface is "
      "usually the widest, fastest, most power-hungry and most "
      "timing-critical interface on an SoC. It is also unlike the other "
      "links in this part: DRAM is not a packet protocol with a smart "
      "partner on the other end but a **command-driven analog array** that "
      "does exactly what it is told, when it is told, and relies on the "
      "controller to respect dozens of timing rules. This chapter builds "
      "that model from the bank upward, then covers the DDR, LPDDR, GDDR "
      "and HBM families, the controller and PHY (joined by **DFI**), and "
      "finally the flash interfaces: raw NAND (ONFI/Toggle), eMMC, SD and "
      "UFS.")

    h2("SDRAM basics: banks, rows, columns")
    diagram([
        "   one DRAM device (e.g. DDR4 x8, 8 Gb)",
        "  +-------------------------------------------------------------+",
        "  | bank group 0         bank group 1   ...    bank group 3      |",
        "  | +------+ +------+    +------+              +------+          |",
        "  | |bank 0| |bank 1|... |bank 4| ...          |bank15|          |",
        "  | | rows | |      |    |      |              |      |          |",
        "  | | 64K  | |      |    |      |              |      |          |",
        "  | |------| |------|    |------|              |------|          |",
        "  | |sense | |sense |    |sense |  <- row buffer (1 KB page)      |",
        "  | |amps  | |amps  |    |amps  |     one open row per bank       |",
        "  | +--+---+ +--+---+    +--+---+                                 |",
        "  |    +---- column mux / prefetch 8n ---- I/O (DQ[7:0], DQS) ----|--> pins",
        "  +-------------------------------------------------------------+",
    ], "A DRAM device is several independent banks. Each bank is a 2-D array "
       "of 1T1C cells with one row buffer (the sense amplifiers).")
    p("A cell is one transistor and one capacitor; reading it is "
      "destructive and slow, so DRAM works a whole **row** (a 'page', "
      "typically 1-2 KB per device) at a time. **ACTIVATE** (ACT) copies a "
      "row into the bank's sense amplifiers; **READ/WRITE** then transfer "
      "bursts of **columns** from/to that open row; **PRECHARGE** (PRE) "
      "writes the row back and prepares the bank for another row. Because "
      "the capacitors leak, every row must be **REFRESHED** within a "
      "retention period (64 ms at normal temperature, 32 ms when hot), so "
      "the controller issues a REF command on average every **tREFI** "
      "(7.8 us for DDR4, 3.9 us for DDR5).")
    tbl(["Command", "Meaning"],
        [["ACT (bank, row)", "open a row: copy it into the bank's sense amplifiers"],
         ["RD / WR (bank, column)", "burst read or write from the open row (BL8 or BL16); "
                                    "RDA/WRA add auto-precharge"],
         ["PRE / PREA", "close the open row of one bank / all banks"],
         ["REF (all-bank / same-bank / per-bank)", "refresh a group of rows; banks "
                                                   "must be precharged"],
         ["MRS / MRW / MRR", "write or read mode registers (latencies, ODT, drive, "
                             "training modes)"],
         ["ZQCL / ZQCS (DDR4), ZQ start/latch (DDR5, LPDDR)", "calibrate driver and "
                                                             "termination impedance"],
         ["SRE / SRX, PDE / PDX", "enter/exit self-refresh and power-down"],
         ["DES / NOP", "no command this cycle"]],
        widths=[36, 64], bold_first=True)
    h3("Latencies and the key timing parameters")
    p("**CAS latency** CL (or RL, read latency) is the number of clocks "
      "from a READ command to the first data; **CWL** (write latency) the "
      "same for writes. A datasheet line such as 'DDR4-3200 22-22-22' means "
      "CL-tRCD-tRP = 22 clocks of 0.625 ns = 13.75 ns each. That absolute "
      "value has stayed around 13-15 ns for twenty years - DRAM got wider "
      "and faster at the pins, not faster in the array.")
    tbl(["Parameter", "Between", "Why it exists", "DDR4-3200 order of magnitude"],
        [["tRCD", "ACT -> RD/WR, same bank", "sense amplifiers must develop the row",
          "~13.75 ns (22 clk)"],
         ["tRP", "PRE -> ACT, same bank", "bitlines must be precharged", "~13.75 ns"],
         ["tRAS", "ACT -> PRE, same bank (min)", "row must be fully restored",
          "~32 ns"],
         ["tRC", "ACT -> ACT, same bank", "= tRAS + tRP", "~46 ns"],
         ["tRRD_S / _L", "ACT -> ACT, other bank (other / same bank group)",
          "power delivery / charge pump", "~2.5-5 ns / ~5-6.4 ns"],
         ["tFAW", "any 4 ACTs in a window", "peak current limit", "~20-30 ns"],
         ["tWR", "end of write data -> PRE", "write recovery into cells", "15 ns"],
         ["tWTR_S / _L", "end of write data -> RD", "bus turnaround inside DRAM",
          "~2.5 / 7.5 ns"],
         ["tRTP", "RD -> PRE", "read must finish before precharge", "7.5 ns"],
         ["tCCD_S / _L", "RD->RD or WR->WR (other / same bank group)",
          "column path cycle time", "4 clk / ~5-8 clk"],
         ["tRFC", "REF -> next valid command", "refresh takes many rows at once",
          "350 ns (8 Gb), 550 ns (16 Gb)"],
         ["tREFI", "average REF interval", "retention", "7.8 us (3.9 us hot)"]],
        widths=[14, 28, 30, 28], bold_first=True,
        caption="The core DRAM timing parameters. Exact values depend on "
                "device density, speed bin and vendor; always use the JEDEC "
                "speed-bin table or the datasheet.")
    diagram([
        "  CK     _/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_/~\\_",
        "  CMD    =ACT=====================RD================================PRE==========",
        "         |<------ tRCD --------->|<------- CL ------->|",
        "  DQS    ____________________________________________/~\\_/~\\_/~\\_/~\\________",
        "  DQ     ============================================<D0><D1>...<D7>=========",
        "         |<------------------------ tRAS (min) ------------------->|",
        "                                                                   |<-tRP->| ACT",
    ], "A closed-page read: ACT, wait tRCD, RD, data after CL (BL8 = 4 "
       "clocks of DDR data), PRE no earlier than tRAS after ACT, next ACT "
       "to that bank after tRP.")
    p("The timing checker below is the kind of passive monitor a DV team "
      "binds to a memory controller's DFI or DRAM command bus (and that "
      "memory models contain internally). It keeps per-bank state and "
      "timestamps and flags every rule it knows. Timing values are small "
      "cycle counts for readability, not a real speed bin.")
    _v("sdram_chk", "sdram_chk.sv - a per-bank SDRAM command-timing checker.")
    _v("tb_sdram", "tb_sdram.sv - a legal command sequence followed by a "
       "sequence of six illegal commands.")
    _o("sd", "Real vvp output. The legal sequence passes silently; each "
       "illegal command is flagged in the cycle it is issued, some with two "
       "violations (the ACT at cycle 52 breaks both tRP and tRC).")
    box("tip", "Interview insight: why tRC matters more than tRCD",
        ["Random accesses to the **same bank** are limited by tRC (~46 ns), "
         "i.e. about 22 million row activations per second per bank - "
         "hopeless for a 25 GB/s channel. Bandwidth comes from **bank "
         "parallelism** (16-32 banks, several ranks and channels) and "
         "**row-buffer locality** (many column bursts per activate). Every "
         "memory-controller feature - address mapping, reordering, page "
         "policy - exists to exploit those two."])

    h2("The DDR family")
    tbl(["Standard", "Data rate (MT/s)", "VDD / VDDQ", "Organization highlights"],
        [["DDR3", "800-2133", "1.5 V (DDR3L 1.35 V)", "8 banks, 8n prefetch, BL8, fly-by "
          "command/clock routing on DIMMs, 64-bit channel (72 with ECC)"],
         ["DDR4", "1600-3200", "1.2 V, VPP 2.5 V", "16 banks in 4 bank groups (x4/x8), "
          "POD I/O, DBI, CA parity, write CRC, internal VrefDQ"],
         ["DDR5", "3200-6400 (to 8800 in later bins)", "1.1 V", "32 banks in 8 bank "
          "groups (x4/x8), BL16, two independent 32-bit subchannels per DIMM (40 with "
          "ECC), on-die ECC, PMIC on DIMM, DFE receivers, same-bank refresh"],
         ["LPDDR4 / 4X", "up to 4266", "VDDQ 1.1 V / 0.6 V", "two x16 channels per "
          "die, 8 banks, 6-bit multi-cycle CA bus, BL16/32, CA training"],
         ["LPDDR5 / 5X", "up to 6400 / 8533 (and beyond)", "VDDQ 0.5 V",
          "16 banks (bank-group mode), WCK data clock separate from CK, DVFS, "
          "link ECC (5X)"],
         ["GDDR6 / 6X", "~12-24 Gb/s per pin", "1.35 V / 1.25 V", "two independent x16 "
          "channels per device, 16 banks; 6X (Micron) uses PAM4"],
         ["GDDR7", "~28-32+ Gb/s per pin", "lower than GDDR6", "PAM3 signalling, "
          "four independent channels per device"],
         ["HBM2E", "~3.2-3.6 Gb/s per pin", "1.2 V", "1024-bit stack, 8 channels x "
          "128 (16 pseudo-channels x 64), ~410-460 GB/s per stack"],
         ["HBM3 / 3E", "6.4 / ~9.2-9.8 Gb/s per pin", "1.1 V core, low-swing I/O",
          "16 channels x 64 (32 pseudo-channels), ~819 GB/s / ~1.2 TB/s per stack"],
         ["HBM4", "~6.4-8 Gb/s per pin", "-", "2048-bit stack, 32 channels, ~2 TB/s "
          "per stack"]],
        widths=[13, 20, 17, 50], bold_first=True,
        caption="DRAM families. Speeds are JEDEC (or announced) ranges; "
                "vendors ship faster non-JEDEC parts, especially for GDDR/HBM.")
    bul(["**DDR** (DIMMs) optimizes capacity and cost per bit: servers and "
         "PCs. **DDR5** splits each DIMM into two 32-bit **subchannels** so "
         "that BL16 still delivers a 64-byte cache line per burst, and moves "
         "voltage regulation onto the module.",
         "**LPDDR** is soldered next to (or stacked on) the SoC: narrow 16-bit "
         "channels, very low I/O voltage, deep power-down states and "
         "frequency scaling for phones, laptops and automotive.",
         "**GDDR** optimizes bandwidth per pin for GPUs on a PCB: very high "
         "per-pin rates, point-to-point, short traces.",
         "**HBM** optimizes bandwidth per watt: a **stack** of DRAM dies on a "
         "base logic die, connected by thousands of **TSVs**, placed on a "
         "**silicon interposer** (or bridge) next to the SoC so that 1024 "
         "(or 2048) data wires can run at modest per-pin rates over "
         "millimeter distances."])
    box("key", "On-die ECC is not system ECC",
        ["DDR5 (and LPDDR5) devices correct single-bit errors **inside** the "
         "chip (for example 8 check bits per 128 data bits) to cope with "
         "shrinking cells, but they do not report those corrections or "
         "protect the bus. Servers still need **side-band ECC** (the 40-bit "
         "subchannel: 32 data + 8 ECC) computed by the controller; mobile "
         "SoCs use **in-line ECC** that stores check bits in a reserved part "
         "of the address space, or link ECC on the interface."])

    h2("Source-synchronous capture: DQS and training")
    p("At several Gb/s per pin, no global clock can capture data across a "
      "board, so DDR is **source-synchronous**: every byte lane (8 DQ bits, "
      "a data mask/DBI bit) travels with its own differential **strobe DQS** "
      "generated by whoever drives the data. On **reads** the DRAM sends "
      "DQS **edge-aligned** with DQ and the controller PHY delays it by "
      "about a quarter clock to sample in the middle of the eye; on "
      "**writes** the controller sends DQS **center-aligned**.")
    diagram([
        " READ (from DRAM)                    WRITE (to DRAM)",
        " DQS  __/~~~\\___/~~~\\___/~~~\\__     DQS  ____/~~~\\___/~~~\\___/~~~\\",
        " DQ   ==X=D0=X=D1=X=D2=X=D3=X==       DQ   ==X=D0==X=D1==X=D2==X=D3=",
        "        ^ edge aligned: PHY delays     edges fall in the middle of each bit:",
        "          DQS by ~1/4 tCK (DLL/DQS     the controller shifts DQS by 90 deg",
        "          delay line) before sampling  before sending",
    ], "DQS/DQ alignment. The PHY's per-lane delay lines are set by training.")
    p("Because trace lengths, package skews and voltage/temperature differ "
      "per lane, a DDR PHY **trains** its delays at boot (and re-trains or "
      "tracks periodically):")
    bul(["**Write leveling** (DDR3 onward, needed by fly-by routing where CK "
         "reaches each DRAM at a different time): the DRAM samples CK with "
         "DQS and reports the value on DQ; the PHY sweeps the DQS delay until "
         "it finds the 0->1 transition, aligning DQS to CK at every device.",
         "**Read gate training**: find when the DQS preamble arrives, so the "
         "PHY enables its DQS input only during the burst (DQS is undriven, "
         "and noisy, between bursts).",
         "**Read and write data eye training**: sweep per-bit DQ delays (and "
         "VREF) with known patterns (MPR or a DRAM-internal pattern buffer) "
         "and center each bit in its eye.",
         "**CA training** (LPDDR4/5, DDR5) and **Vref training** for the "
         "command/address bus and the internal receivers.",
         "Firmware (often a microcontroller inside the PHY running vendor "
         "code) performs the sequence; results can be saved and restored to "
         "speed up resume from suspend."])
    p("**ODT** (on-die termination) terminates the bus inside the receiving "
      "DRAM instead of on the board, with separate values for the target "
      "and non-target ranks during writes (RTT_WR, RTT_NOM, RTT_PARK in "
      "DDR4). **ZQ calibration** trims output drivers and ODT against an "
      "external precision 240 ohm resistor, at initialization and "
      "periodically as temperature and voltage drift.")
    box("warn", "Pitfall: training passes at room temperature",
        ["DRAM interfaces that train at 25 C and fail at 85 C (or after a "
         "voltage droop) are common. Run memory tests across temperature and "
         "voltage corners, enable the PHY's periodic tracking (DQS drift "
         "compensation), schedule periodic ZQ calibration, and check that the "
         "controller's refresh rate doubles above 85 C (2x refresh / tREFI "
         "halved). 'Works on the bench' is not a sign-off criterion."])

    h2("Bank groups and refresh modes")
    p("DDR4 introduced **bank groups** because the internal column path "
      "could no longer cycle at the pin data rate. Back-to-back accesses to "
      "the **same** bank group must wait tCCD_L (and tRRD_L, tWTR_L); to "
      "**different** bank groups only tCCD_S = 4 clocks, which exactly "
      "matches a BL8 burst. A controller that does not alternate bank "
      "groups loses a large fraction of peak bandwidth at high data rates.")
    bul(["**All-bank refresh**: every bank closed, the whole device busy for "
         "tRFC. Up to 8 REF commands may be postponed or pulled in (DDR4) to "
         "fit around traffic.",
         "**Fine-granularity refresh** (DDR4 2x/4x) and **same-bank refresh** "
         "(DDR5 REFsb) / **per-bank refresh** (LPDDR) refresh a subset while "
         "other banks keep working - much lower refresh stall.",
         "**Self-refresh** keeps data during idle with the controller and PHY "
         "powered down; the DRAM refreshes itself from an internal oscillator.",
         "**Row hammer** mitigation: repeated activation of one row disturbs "
         "its neighbours; DDR5 adds **RFM** (refresh management) commands and "
         "vendors add target-row refresh (TRR). Controllers count activations "
         "per bank."])
    eq(["refresh overhead ~ tRFC / tREFI = 350 ns / 7.8 us = 4.5%  (DDR4 8 Gb)",
        "                                  550 ns / 3.9 us = 14%   (16 Gb, hot, all-bank)"],
       "Why refresh modes matter more with every density generation.")

    h2("Memory controller architecture")
    diagram([
        "  AXI/CHI ports --> +------------+   +------------+   +--------------+",
        "  (CPU, GPU, DMA)   | port arbiter| ->| address    | ->| command      |",
        "                    | QoS, write  |   | mapping    |   | queues (per  |",
        "                    | data buffer |   | (ch/rank/  |   | bank / rank) |",
        "                    +------------+   | BG/bank/row|   +------+-------+",
        "                                      | /col, XOR) |          |",
        "                                      +------------+          v",
        "  read data  <-- reorder buffer <-- ECC decode      +----------------+",
        "                                                    | scheduler:     |",
        "   refresh engine, ZQ timer, power-down, ------->   | FR-FCFS, page  |",
        "   row-hammer counters, scrubber                    | policy, timing |",
        "                                                    | checks, R/W    |",
        "                                                    | turnaround     |",
        "                                                    +-------+--------+",
        "                                                            | DFI",
        "                                                        DDR PHY",
    ], "Main blocks of a DRAM controller. The scheduler is where performance "
       "is won or lost; the protocol engine behind it must never violate a "
       "timing rule.")
    bul(["**Address mapping** decides which address bits select channel, "
         "rank, bank group, bank, row and column. Putting bank/bank-group "
         "bits low (and XOR-ing them with row bits) spreads sequential and "
         "strided streams across banks.",
         "**Scheduling**: the classic policy is **FR-FCFS** (first ready, "
         "first come first served): prefer commands that hit an open row, "
         "then the oldest. Real controllers add QoS classes, starvation "
         "limits and read priority.",
         "**Page policy**: **open page** leaves the row open hoping for "
         "another hit (good for streaming); **closed page** auto-precharges "
         "(good for random server traffic); adaptive policies predict per bank.",
         "**Read/write grouping**: each bus turnaround costs tens of clocks "
         "(tWTR, read-to-write gaps), so writes are buffered and drained in "
         "batches between high and low watermarks.",
         "**ECC and scrubbing**: SECDED over 64+8 bits (or symbol-based "
         "Chipkill-class codes on servers), background scrubbing, error "
         "logging and poisoning.",
         "**Low power**: power-down after idle timeouts, self-refresh entry, "
         "frequency change (LPDDR DVFS) coordinated with the PHY."])

    h2("DFI: the controller-PHY interface")
    p("The **DDR PHY Interface** (DFI) is an industry specification that "
      "separates the controller from the PHY so they can come from "
      "different vendors. The controller drives DRAM commands and write "
      "data as if it were at the pins; the PHY handles the analog I/O, "
      "delay lines, DLLs, training and clock-domain crossing to the DRAM "
      "clock.")
    tbl(["Interface group", "Representative signals", "Purpose"],
        [["Command", "dfi_address, dfi_bank / dfi_bg, dfi_cs, dfi_act_n, dfi_cke, "
                     "dfi_odt, dfi_reset_n", "DRAM commands, one set per phase"],
         ["Write data", "dfi_wrdata_en, dfi_wrdata, dfi_wrdata_mask",
          "timed by tphy_wrlat / tphy_wrdata after the WR command"],
         ["Read data", "dfi_rddata_en, dfi_rddata, dfi_rddata_valid",
          "rddata_en timed by trddata_en; PHY returns data with a valid flag"],
         ["Update", "dfi_ctrlupd_req/ack, dfi_phyupd_req/ack",
          "windows where the PHY may retune delays with no traffic"],
         ["Status", "dfi_init_start, dfi_init_complete, dfi_freq_change / "
                    "dfi_frequency", "initialization and frequency change"],
         ["Training", "dfi_rdlvl_*, dfi_wrlvl_*, or PHY-independent training "
                      "mode", "controller- or PHY-driven training steps"],
         ["Low power", "dfi_lp_ctrl_req, dfi_lp_data_req, dfi_lp_ack",
          "PHY power-down handshakes"]],
        widths=[16, 50, 34], bold_first=True)
    p("DFI supports **frequency ratios** of 1:1, 1:2 and 1:4 between the "
      "controller clock and the DRAM clock: at 1:4 the controller runs at a "
      "quarter of the DRAM clock and drives four **phases** (p0-p3) of "
      "command and data per controller cycle. A DDR5-6400 PHY (3.2 GHz CK) "
      "therefore talks to an 800 MHz controller that handles four command "
      "slots per cycle - the scheduler must place commands in the right "
      "phase to respect single-clock timing rules.")

    h2("Bandwidth and efficiency")
    eq(["peak BW = data rate x bus width / 8",
        "DDR4-3200 x64:            3200e6 x 64 / 8 = 25.6 GB/s per channel",
        "DDR5-6400 DIMM (2 x 32):  6400e6 x 64 / 8 = 51.2 GB/s per DIMM",
        "LPDDR5X-8533 x64:         8533e6 x 64 / 8 = 68.3 GB/s",
        "HBM3 stack (1024 x 6.4):  6.4e9 x 1024 / 8 = 819 GB/s"],
       "Peak bandwidth. Sustained efficiency is typically 60-90% of peak.")
    p("Efficiency losses come from refresh (a few % to over 10%), row misses "
      "(tRP + tRCD per miss when a row must be changed), bank conflicts "
      "(tRC), tFAW limits for random traffic, read-write turnarounds, and "
      "rank switching. Streaming reads with good locality reach 85-90%; "
      "random 64-byte accesses across a large footprint may fall well below "
      "50%. Architecture teams model this with cycle-accurate DRAM "
      "simulators (for example DRAMSim-style or Ramulator-style models) "
      "before choosing the number of channels.")

    h2("HBM: stacks, TSVs and interposers")
    diagram([
        "        HBM stack                  SoC / GPU die",
        "     +-------------+            +-----------------------+",
        "     | DRAM die 8  |            |                       |",
        "     | ...  (TSVs) |            |    compute            |",
        "     | DRAM die 1  |            |           +----------+|",
        "     | base (logic)| <-1024-2048 wires----> | HBM PHY  ||",
        "     +------+------+    ~mm on interposer   +----------+|",
        "  ==========|================================|============  silicon interposer",
        "  ==================================================== package substrate",
    ], "HBM is a 2.5D package: the stack and the SoC sit side by side on an "
       "interposer (CoWoS-style) or are joined by an embedded bridge.")
    bul(["Each stack has 4 to 16 DRAM dies connected by TSVs to a base die "
         "that contains the PHY-side I/O, test logic and (in HBM4) "
         "potentially customer logic.",
         "The interface is divided into independent channels (and "
         "pseudo-channels) - essentially many narrow DRAMs in parallel - "
         "so the controller is an array of channel controllers.",
         "Microbump connections are too fine to probe, so HBM includes an "
         "IEEE 1500 test port (Chapter 23), lane repair (spare data lanes) "
         "and, in HBM3, ECC options.",
         "Ownership: the PHY is a hard macro co-designed with the package "
         "team; the interposer routing is a signal-integrity sign-off item; "
         "the RTL team owns the controller array and its NoC connection."])

    h2("Flash interfaces")
    h3("Raw NAND: ONFI and Toggle")
    p("NAND flash is organized as **pages** (typically 4-16 KB plus a "
      "spare area for ECC) grouped into **blocks** (hundreds of pages). "
      "Reads and programs are per page, erases per block, and a page can "
      "only be programmed after its block is erased. The interface is an "
      "8-bit bidirectional bus, standardized by **ONFI** (Open NAND Flash "
      "Interface) and, in a compatible variant, by **Toggle DDR**.")
    tbl(["Signal", "Function"],
        [["CE#", "chip enable (one per die/target)"],
         ["CLE / ALE", "command latch enable / address latch enable"],
         ["WE# / RE# (RE_t/RE_c)", "write / read strobes (differential RE in fast modes)"],
         ["DQ[7:0], DQS (DQS_t/c)", "data bus and source-synchronous strobe (NV-DDR modes)"],
         ["R/B#", "ready/busy (open drain)"],
         ["WP#", "write protect"]],
        widths=[30, 70], bold_first=True)
    tbl(["Operation", "Command cycles", "Typical time"],
        [["Page read", "00h, 5 address cycles, 30h ... wait tR ... data out",
          "tR ~ 25-100 us (SLC fastest)"],
         ["Page program", "80h, address, data in, 10h ... wait tPROG",
          "tPROG ~ 0.2-2 ms"],
         ["Block erase", "60h, 3 row-address cycles, D0h ... wait tBERS", "a few ms"],
         ["Read status", "70h -> status byte (ready, fail)", "-"],
         ["Reset / Read ID / features", "FFh / 90h / EFh (set) EEh (get)", "-"]],
        widths=[24, 50, 26], bold_first=True)
    p("Interface speed grew from asynchronous SDR (tens of MT/s) through "
      "**NV-DDR**, **NV-DDR2** and **NV-DDR3** to more than 2000 MT/s in "
      "recent ONFI 5.x / Toggle generations, with ODT, ZQ and training - the "
      "same techniques as DRAM. Error correction moved from **BCH** codes "
      "(tens of bits correctable per 1 KB) to **LDPC** with soft-decision "
      "reads for TLC and QLC. A NAND controller (inside an SSD, eMMC or UFS "
      "device) therefore contains a multi-channel ONFI PHY, a strong ECC "
      "engine and a **flash translation layer** (FTL) in firmware for "
      "wear-leveling, garbage collection and bad-block management.")
    h3("Managed flash: eMMC, SD and UFS")
    tbl(["Interface", "Bus", "Modes / speed", "Protocol notes"],
        [["eMMC 5.1", "CLK, CMD, DAT[7:0], Data Strobe", "legacy 26 MHz, HS 52 MHz "
          "SDR/DDR, HS200 (200 MB/s), HS400 (400 MB/s)",
          "command/response on CMD with CRC7, data blocks with CRC16; tuning for HS200"],
         ["SD", "CLK, CMD, DAT[3:0]", "Default 12.5 MB/s, High Speed 25 MB/s, UHS-I "
          "SDR104 104 MB/s (1.8 V), UHS-II/III LVDS lanes",
          "same command set as MMC in spirit; SPI mode for simple hosts"],
         ["SD Express", "PCIe lanes on extra pins", "PCIe 3.0 x1 (~985 MB/s) to "
          "PCIe 4.0 x2", "NVMe protocol"],
         ["UFS 3.x / 4.x", "MIPI M-PHY, 2 lanes each way", "HS-Gear 4 (11.6 Gb/s/lane), "
          "Gear 5 (23.3 Gb/s/lane): UFS 4.0 ~4 GB/s class",
          "MIPI UniPro link layer; SCSI commands in UPIUs; command queue"],
         ["NVMe", "PCIe (Chapter 18)", "Gen3-Gen5 x4 typical", "submission/completion "
          "queues in host memory, doorbells, up to 64K queues"]],
        widths=[14, 22, 34, 30], bold_first=True)
    p("An SoC normally contains an **SD/eMMC host controller** (the SD "
      "Association's SDHCI register model is standard, with ADMA descriptor "
      "DMA) and, in phones, a **UFS host controller** (UFSHCI) with an "
      "M-PHY and UniPro stack. The storage device itself contains its own "
      "controller, NAND and FTL; the SoC only speaks the command protocol. "
      "Tuning (finding the sampling phase for HS200/SDR104) and voltage "
      "switching (3.3 V to 1.8 V signalling) are the usual bring-up pain "
      "points.")

    h2("Who owns what")
    tbl(["Area", "Owner", "Typical deliverables"],
        [["DDR PHY, I/O, DLLs, training firmware", "PHY vendor / analog team",
          "hard macro, timing models, training code, SI guidelines"],
         ["Memory controller, DFI integration, NoC ports", "RTL team",
          "configuration (ranks, mapping, QoS), ECC, performance counters"],
         ["Package, board, interposer", "package / SI / PI teams",
          "channel simulation, power integrity, HBM interposer routing"],
         ["DV", "DV team", "JEDEC memory models with timing checks, controller "
                           "traffic tests, DFI protocol checkers"],
         ["Boot firmware", "firmware team", "DRAM init and training sequence, "
                                            "margining tools, SPD read over I2C"]],
        widths=[30, 22, 48], bold_first=True)

    h2("Summary")
    bul(["DRAM is a command-driven array: ACT opens a row, RD/WR move bursts "
         "of columns, PRE closes it, REF keeps it alive. tRCD, tRP, tRAS, tRC, "
         "tRRD, tFAW, tWR and tRFC govern what may happen when.",
         "DDR4/DDR5 target capacity, LPDDR power, GDDR per-pin speed, HBM "
         "bandwidth per watt via wide stacked interfaces; DDR5 uses two 32-bit "
         "subchannels, BL16 and on-die ECC.",
         "Data is source-synchronous with DQS per byte lane; write leveling, "
         "read gate and eye training, ODT and ZQ calibration make multi-Gb/s "
         "capture work.",
         "Controllers win bandwidth with bank parallelism and row locality: "
         "address mapping, FR-FCFS scheduling, page policy, write batching, "
         "bank-group alternation and smart refresh.",
         "DFI separates controller and PHY, with phase-based 1:2/1:4 "
         "frequency ratios.",
         "Flash: ONFI/Toggle raw NAND with BCH/LDPC ECC and an FTL; eMMC/SD "
         "for simple managed storage, UFS (M-PHY + UniPro) for phones, NVMe "
         "over PCIe for SSDs."])

    h2("Exercises")
    bul(["Extend `sdram_chk` with tFAW (no more than four ACTs in any "
         "window of tFAW cycles) and tWTR; add a test sequence that "
         "violates each.",
         "For DDR4-3200 (tCK 0.625 ns) with tRCD = tRP = CL = 22, compute the "
         "latency of a row hit, a closed-bank access and a row conflict, in "
         "ns, from command to first data.",
         "A DDR5-4800 subchannel runs a random 64-byte read stream to one "
         "bank group with tRC = 48 ns. How many banks must be in use to "
         "reach 80% of peak bandwidth?",
         "Design an address mapping for a 2-channel, 2-rank, 32-bank DDR5 "
         "system that spreads a 4 KB-strided stream across all banks. Show "
         "which address bits you XOR.",
         "Compute the refresh overhead of a 16 Gb DDR4 device at 95 C with "
         "all-bank refresh, and explain how same-bank refresh changes the "
         "picture in DDR5.",
         "An LDPC-protected TLC NAND page is 16 KB with a 2 KB spare area. "
         "What code rate does that imply, and why do QLC devices need "
         "soft-decision reads?"],
        ordered=True)
