"""Part I - Foundations (Chapters 1-4) of the communication-protocols guide.

Every Verilog/SystemVerilog design and testbench in SRC was compiled with Icarus
Verilog 12 (iverilog -g2012 -Wall) and simulated with vvp, except the SVA example,
which was built with Verilator 5.020 (--binary --timing --assert). The Python
references in SRC were run with Python 3. OUT holds the captured output verbatim
(only the trailing "$finish called" line is omitted).
"""

from proto_guide.common import *  # noqa: F401,F403
from proto_guide.common import box as _box

# --- sources and REAL simulator / Python output (generated) ---
SRC = {
    'enc8b10b': r'''
// 8b/10b encoder (combinational). code[9:0] = {a,b,c,d,e,i,f,g,h,j}; 'a' is sent first.
// Stores only the RD- column; the RD+ code is the bitwise complement whenever the
// sub-block is unbalanced or is 111000 / 1100 (balanced codes that alternate), and
// for every K-character 4b sub-block.
module enc8b10b (
  input  logic [7:0] d,          // HGF EDCBA
  input  logic       k,          // 1 = control (K) character
  input  logic       rd_in,      // running disparity: 0 = RD-, 1 = RD+
  output logic [9:0] code,
  output logic       rd_out
);
  logic [4:0] x;  logic [2:0] y;
  logic [5:0] s6m, s6;  logic [3:0] s4m, s4;  logic rd_mid;
  assign x = d[4:0];  assign y = d[7:5];

  function automatic logic flips6(input logic [5:0] s);   // unbalanced or 111000
    return ($countones(s) != 3) || (s == 6'b111000);
  endfunction
  function automatic logic flips4(input logic [3:0] s);
    return ($countones(s) != 2) || (s == 4'b1100);
  endfunction

  always_comb begin
    case (x)                     // 5b/6b, RD- column, abcdei
      5'd0: s6m = 6'b100111;  5'd1: s6m = 6'b011101;  5'd2: s6m = 6'b101101;
      5'd3: s6m = 6'b110001;  5'd4: s6m = 6'b110101;  5'd5: s6m = 6'b101001;
      5'd6: s6m = 6'b011001;  5'd7: s6m = 6'b111000;  5'd8: s6m = 6'b111001;
      5'd9: s6m = 6'b100101;  5'd10: s6m = 6'b010101; 5'd11: s6m = 6'b110100;
      5'd12: s6m = 6'b001101; 5'd13: s6m = 6'b101100; 5'd14: s6m = 6'b011100;
      5'd15: s6m = 6'b010111; 5'd16: s6m = 6'b011011; 5'd17: s6m = 6'b100011;
      5'd18: s6m = 6'b010011; 5'd19: s6m = 6'b110010; 5'd20: s6m = 6'b001011;
      5'd21: s6m = 6'b101010; 5'd22: s6m = 6'b011010; 5'd23: s6m = 6'b111010;
      5'd24: s6m = 6'b110011; 5'd25: s6m = 6'b100110; 5'd26: s6m = 6'b010110;
      5'd27: s6m = 6'b110110; 5'd28: s6m = k ? 6'b001111 : 6'b001110;
      5'd29: s6m = 6'b101110; 5'd30: s6m = 6'b011110; default: s6m = 6'b101011;
    endcase
    s6     = (rd_in && flips6(s6m)) ? ~s6m : s6m;
    rd_mid = ($countones(s6) > 3) ? 1'b1 : ($countones(s6) < 3) ? 1'b0 :
             (s6 == 6'b000111) ? 1'b1 : (s6 == 6'b111000) ? 1'b0 : rd_in;

    if (k) case (y)              // 3b/4b for K28.y (x.7 also for K23/27/29/30), fghj
      3'd0: s4m = 4'b1011; 3'd1: s4m = 4'b0110; 3'd2: s4m = 4'b1010; 3'd3: s4m = 4'b1100;
      3'd4: s4m = 4'b1101; 3'd5: s4m = 4'b0101; 3'd6: s4m = 4'b1001; default: s4m = 4'b0111;
    endcase
    else case (y)
      3'd0: s4m = 4'b1011; 3'd1: s4m = 4'b1001; 3'd2: s4m = 4'b0101; 3'd3: s4m = 4'b1100;
      3'd4: s4m = 4'b1101; 3'd5: s4m = 4'b1010; 3'd6: s4m = 4'b0110;
      // D.x.A7 avoids a run of five equal bits across the i/f boundary
      default: s4m = ((!rd_mid && (x == 17 || x == 18 || x == 20)) ||
                      ( rd_mid && (x == 11 || x == 13 || x == 14))) ? 4'b0111 : 4'b1110;
    endcase
    // every K 4b pair is a complement pair (even balanced K.x.1/2/5/6)
    s4     = (rd_mid && (k || flips4(s4m))) ? ~s4m : s4m;
    rd_out = ($countones(s4) > 2) ? 1'b1 : ($countones(s4) < 2) ? 1'b0 :
             (s4 == 4'b0011) ? 1'b1 : (s4 == 4'b1100) ? 1'b0 : rd_mid;
    code   = {s6, s4};
  end
endmodule''',
    'tb_8b10b': r'''
module tb;
  logic [7:0] d; logic k, rd_in, rd_out; logic [9:0] code;
  logic [10:0] gold [536];                // {code, rd_out} from ref8b10b.py
  // K28.0..K28.7, K23.7, K27.7, K29.7, K30.7
  function automatic logic [7:0] kbyte(input int i);
    return (i < 8) ? {i[2:0], 5'd28} : (i == 8) ? 8'hF7 : (i == 9) ? 8'hFB
                                     : (i == 10) ? 8'hFD : 8'hFE;
  endfunction
  enc8b10b dut (.*);
  int n = 0, bad = 0, run = 0, maxrun = 0, rds = 0, minrds = 0, maxrds = 0;
  logic last = 1'b0;
  initial begin
    $readmemh("golden_8b10b.hex", gold);
    // 1) exhaustive check against the Python reference: 256 D + 12 K codes, both RDs
    for (int kk = 0; kk < 2; kk++)
      for (int i = 0; i < (kk ? 12 : 256); i++)
        for (int r = 0; r < 2; r++) begin
          k = kk; rd_in = r; d = kk ? kbyte(i) : i[7:0]; #1;
          if ({code, rd_out} !== gold[n]) bad++;
          n++;
        end
    $display("table check : %0d codes vs Python reference, mismatches=%0d", n, bad);
    // 2) a few famous characters starting from RD-
    k = 0; rd_in = 0;
    d = 8'h00; #1 $display("D0.0  RD- -> %b %b", code[9:4], code[3:0]);
    d = 8'hB5; #1 $display("D21.5 RD- -> %b %b", code[9:4], code[3:0]);
    k = 1; d = 8'hBC; #1 $display("K28.5 RD- -> %b %b  (comma 0011111)", code[9:4], code[3:0]);
    rd_in = 1; #1 $display("K28.5 RD+ -> %b %b  (comma 1100000)", code[9:4], code[3:0]);
    // 3) 100k random characters as a serial stream: run length and running digital sum
    rd_in = 0;
    for (int c = 0; c < 100000; c++) begin
      k = ($urandom % 16 == 0); d = k ? kbyte($urandom % 12) : $urandom; #1;
      for (int b = 9; b >= 0; b--) begin
        run = (code[b] == last) ? run + 1 : 1; last = code[b];
        if (run > maxrun) maxrun = run;
        rds += code[b] ? 1 : -1;
        if (rds < minrds) minrds = rds; if (rds > maxrds) maxrds = rds;
      end
      rd_in = rd_out;
    end
    $display("stream      : 1000000 bits, max run length=%0d, digital sum in [%0d,%0d]",
             maxrun, minrds, maxrds);
    $finish;
  end
endmodule''',
    'ref8b10b': r'''
# Independent Python reference: dictionary tables straight from the 8b/10b code tables
D6 = {0:("100111","011000"),1:("011101","100010"),2:("101101","010010"),3:("110001",)*2,
 4:("110101","001010"),5:("101001",)*2,6:("011001",)*2,7:("111000","000111"),
 8:("111001","000110"),9:("100101",)*2,10:("010101",)*2,11:("110100",)*2,12:("001101",)*2,
 13:("101100",)*2,14:("011100",)*2,15:("010111","101000"),16:("011011","100100"),
 17:("100011",)*2,18:("010011",)*2,19:("110010",)*2,20:("001011",)*2,21:("101010",)*2,
 22:("011010",)*2,23:("111010","000101"),24:("110011","001100"),25:("100110",)*2,
 26:("010110",)*2,27:("110110","001001"),28:("001110",)*2,29:("101110","010001"),
 30:("011110","100001"),31:("101011","010100")}
K28_6 = ("001111","110000")
D4 = {0:("1011","0100"),1:("1001",)*2,2:("0101",)*2,3:("1100","0011"),4:("1101","0010"),
 5:("1010",)*2,6:("0110",)*2,7:("1110","0001")}
A7 = ("0111","1000")
K4 = {0:("1011","0100"),1:("0110","1001"),2:("1010","0101"),3:("1100","0011"),
 4:("1101","0010"),5:("0101","1010"),6:("1001","0110"),7:("0111","1000")}
KCODES = [(28,y) for y in range(8)] + [(23,7),(27,7),(29,7),(30,7)]

def rd_after(sub, rd):           # rd: 0 = RD-, 1 = RD+
    ones = sub.count("1"); zeros = len(sub) - ones
    if ones > zeros: return 1
    if ones < zeros: return 0
    if sub in ("000111", "0011"): return 1
    if sub in ("111000", "1100"): return 0
    return rd

def enc(byte, k, rd):
    x, y = byte & 31, byte >> 5
    s6 = (K28_6 if (k and x == 28) else D6[x])[rd]
    rd = rd_after(s6, rd)
    if k:
        s4 = K4[y][rd]
    elif y == 7 and ((rd == 0 and x in (17, 18, 20)) or (rd == 1 and x in (11, 13, 14))):
        s4 = A7[rd]
    else:
        s4 = D4[y][rd]
    rd = rd_after(s4, rd)
    return s6 + s4, rd

if __name__ == "__main__":
    lines = []
    for k in (0, 1):
        vals = range(256) if not k else [x | (y << 5) for x, y in KCODES]
        for b in vals:
            for rd in (0, 1):
                c, r = enc(b, k, rd)
                lines.append("%03x" % ((int(c, 2) << 1) | r))
    open("golden_8b10b.hex", "w").write("\n".join(lines) + "\n")
    print(len(lines), "vectors")
    for name, b, k in [("D0.0", 0, 0), ("D21.5", 0xB5, 0), ("K28.5", 0xBC, 1)]:
        print(name, enc(b,k,0)[0], enc(b,k,1)[0])''',
    'manch': r'''
// Manchester, IEEE 802.3 convention: '1' = low->high at mid-bit, '0' = high->low.
module manch_tx (
  input  logic clk,                  // runs at 2x the bit rate: one half-bit per cycle
  input  logic rst_n,
  input  logic bit_in,               // sampled at the start of each bit
  output logic bit_req,              // pulses when bit_in is consumed
  output logic line
);
  logic half, cur;
  assign bit_req = !half;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin half <= 1'b0; cur <= 1'b0; line <= 1'b0; end
    else begin
      if (!half) begin cur <= bit_in; line <= ~bit_in; end  // first half: complement
      else                            line <=  cur;         // second half: the bit
      half <= ~half;
    end
endmodule

// Decoder: samples the line at OSR samples per bit with its own, unrelated clock.
// It locks on the first edge (preamble of 1010... guarantees that is a mid-bit edge),
// then ignores edges for 3/4 of a bit so bit-boundary edges are skipped, and re-times
// itself on every mid-bit edge - this is the clock recovery.
module manch_rx #(parameter int OSR = 8) (
  input  logic clk, rst_n,
  input  logic line_in,              // asynchronous to clk
  output logic bit_valid,
  output logic bit_out,
  output logic locked
);
  logic [2:0] sync;                  // 2-flop synchronizer + previous sample
  logic [$clog2(2*OSR)-1:0] cnt;
  wire  s = sync[1], edge_det = sync[1] ^ sync[2];
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      sync <= '0; cnt <= '0; locked <= 1'b0; bit_valid <= 1'b0; bit_out <= 1'b0;
    end else begin
      sync      <= {sync[1:0], line_in};
      bit_valid <= 1'b0;
      if (!locked) begin
        if (edge_det) begin locked <= 1'b1; cnt <= '0; bit_valid <= 1'b1; bit_out <= s; end
      end else if (edge_det && cnt >= (3*OSR)/4 - 1) begin   // a mid-bit edge
        cnt <= '0; bit_valid <= 1'b1; bit_out <= s;          // rising -> 1
      end else if (cnt == (3*OSR)/2) begin                    // no mid-bit edge: lost
        locked <= 1'b0;
      end else cnt <= cnt + 1'b1;
    end
endmodule''',
    'scram': r'''
// Additive (synchronous) scrambler, G(X) = X^16+X^5+X^4+X^3+1 (the PCIe Gen1/2 and
// USB 3.x polynomial), 8 bits per clock, LSB first. Same module scrambles and
// descrambles: data XOR keystream. Both ends must reset the LFSR at the same symbol.
module scr_add (
  input  logic       clk, rst_n,
  input  logic       init,             // re-seed (PCIe: on every COM symbol)
  input  logic       en,
  input  logic [7:0] din,
  output logic [7:0] dout
);
  logic [15:0] lfsr, nxt;
  logic [7:0]  o;
  always @* begin                           // (Icarus: always_comb + loop selects)
    nxt = lfsr;  o = '0;
    for (int i = 0; i < 8; i++) begin         // unrolled: 8 serial steps per clock
      o   = {din[i] ^ nxt[15], o[7:1]};       // bit i ends up in o[i] after 8 shifts
      nxt = {nxt[14:0], 1'b0} ^ (nxt[15] ? 16'h0039 : 16'h0000);
    end
  end
  assign dout = o;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n)    lfsr <= 16'hFFFF;
    else if (init) lfsr <= 16'hFFFF;
    else if (en)   lfsr <= nxt;
endmodule

// Self-synchronous scrambler x^58 + x^39 + 1 (the 64b/66b polynomial), 1 bit/clock.
module scr_ss58 #(parameter bit DESCRAMBLE = 0) (
  input  logic clk, rst_n, en,
  input  logic din,
  output logic dout
);
  logic [57:0] s;                             // the last 58 LINE bits
  wire  fb = s[38] ^ s[57];
  assign dout = din ^ fb;
  wire  line_bit = DESCRAMBLE ? din : dout;   // the history always holds line bits
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n)  s <= DESCRAMBLE ? '0 : {58{1'b1}};   // deliberately different states
    else if (en) s <= {s[56:0], line_bit};
endmodule''',
    'ref_scr': r'''
def pcie_scramble(data, seed=0xFFFF):
    """Additive scrambler, G(X)=X^16+X^5+X^4+X^3+1, Galois form, LSB of each byte first."""
    l, out = seed, []
    for b in data:
        o = 0
        for i in range(8):
            fb = (l >> 15) & 1
            o |= (((b >> i) & 1) ^ fb) << i
            l = ((l << 1) & 0xFFFF) ^ (0x0039 if fb else 0)
        out.append(o)
    return out
if __name__ == "__main__":
    ks = pcie_scramble([0]*16)
    print(" ".join("%02X" % x for x in ks))
    msg = b"SoC links!"
    print(" ".join("%02X" % x for x in pcie_scramble(msg)))''',
    'crc': r'''
// Generic bit-serial CRC: a Galois LFSR, one message bit per clock (MSB-first form).
// Reflection (LSB-first bytes) is handled by the order the caller feeds bits in.
module crc_serial #(parameter int W = 32,
                    parameter logic [W-1:0] POLY = 32'h04C1_1DB7,
                    parameter logic [W-1:0] INIT = '1) (
  input  logic         clk, rst_n,
  input  logic         clear,        // load INIT at the start of a message
  input  logic         en,           // one message bit this clock
  input  logic         din,
  output logic [W-1:0] crc
);
  wire fb = crc[W-1] ^ din;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n)     crc <= INIT;
    else if (clear) crc <= INIT;
    else if (en)    crc <= {crc[W-2:0], 1'b0} ^ (fb ? POLY : '0);
endmodule

// CRC-32 (IEEE 802.3 / zlib), 8 bits per clock. The loop is unrolled by synthesis
// into one XOR tree (up to 14 inputs per bit, see Table 3.x). Bytes go LSB first.
module crc32_d8 (
  input  logic        clk, rst_n, clear, en,
  input  logic [7:0]  data,
  output logic [31:0] crc_reg,        // raw LFSR state
  output logic [31:0] fcs             // final value: bit-reversed and inverted
);
  function automatic logic [31:0] step8(input logic [31:0] c, input logic [7:0] d);
    for (int i = 0; i < 8; i++)
      c = {c[30:0], 1'b0} ^ ((c[31] ^ d[i]) ? 32'h04C1_1DB7 : 32'h0);
    return c;
  endfunction
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n)     crc_reg <= '1;
    else if (clear) crc_reg <= '1;
    else if (en)    crc_reg <= step8(crc_reg, data);
  always_comb
    for (int i = 0; i < 32; i++) fcs[i] = ~crc_reg[31 - i];
endmodule''',
    'tb_crc': r'''
module tb;
  logic clk = 0, rst_n = 0, clear = 0, en = 0, en8 = 0;  logic [7:0] byte_in;
  always #5 clk = ~clk;
  logic [31:0] c32, par_reg, par_fcs;  logic [15:0] c16;  logic [14:0] c15;
  logic [4:0]  c5, c5_out;
  // one serial LFSR per standard, all fed the same bits (in each standard's bit order)
  logic b_lsb, b_msb;
  crc_serial #(32, 32'h04C11DB7, 32'hFFFFFFFF)
                  u32 (.clk, .rst_n, .clear, .en, .din(b_lsb), .crc(c32));   // reflected
  crc_serial #(16, 16'h1021, 16'hFFFF)
                  u16 (.clk, .rst_n, .clear, .en, .din(b_msb), .crc(c16));   // MSB first
  crc_serial #(15, 15'h4599, 15'h0000)
                  u15 (.clk, .rst_n, .clear, .en, .din(b_msb), .crc(c15));
  crc_serial #(5, 5'h05, 5'h1F)
                  u05 (.clk, .rst_n, .clear, .en, .din(b_lsb), .crc(c5));
  crc32_d8 upar (.clk, .rst_n, .clear, .en(en8), .data(byte_in), .crc_reg(par_reg),
                 .fcs(par_fcs));

  function automatic logic [31:0] rev(input logic [31:0] v, input int w);
    rev = '0; for (int i = 0; i < w; i++) rev[i] = v[w-1-i];
  endfunction

  task automatic run(input string s, input logic [31:0] zlib_ref);
    @(negedge clk) clear = 1; @(negedge clk) clear = 0;
    for (int n = 0; n < s.len(); n++) begin
      byte_in = s[n]; en8 = 1;                         // parallel: 1 clock per byte
      for (int i = 0; i < 8; i++) begin                // serial: 8 clocks per byte
        b_lsb = byte_in[i]; b_msb = byte_in[7-i]; en = 1;
        @(negedge clk) en8 = 0;
      end
    end
    en = 0;
    $display("\"%s\"", s);
    $display("  CRC-32 serial   = %h   byte-parallel = %h   zlib.crc32 = %h %s",
             ~rev(c32, 32), par_fcs, zlib_ref,
             (~rev(c32, 32) == zlib_ref && par_fcs == zlib_ref) ? "MATCH" : "MISMATCH");
    c5_out = rev(c5, 5) ^ 5'h1F;                       // CRC-5/USB: refout, xorout=1F
    if (s == "123456789")
      $display("  CRC-16/IBM-3740 = %h   CRC-15/CAN = %h   CRC-5/USB = %h",
               c16, c15, c5_out);
  endtask
  initial begin
    #12 rst_n = 1;
    run("123456789", 32'hCBF43926);
    run("The quick brown fox jumps over the lazy dog", 32'h414FA339);
    $finish;
  end
endmodule''',
    'ref_crc': r'''
import zlib
def crc(data, w, poly, init, refin, refout, xorout):
    """Bit-serial Rocksoft-model CRC: the same algorithm as the serial RTL."""
    c, top, mask = init, 1 << (w - 1), (1 << w) - 1
    for b in data:
        for i in (range(8) if refin else range(7, -1, -1)):
            fb = ((c & top) != 0) ^ ((b >> i) & 1)
            c = ((c << 1) & mask) ^ (poly if fb else 0)
    if refout:
        c = int(format(c, "0%db" % w)[::-1], 2)
    return c ^ xorout
CAT = [  # name, width, poly, init, refin, refout, xorout
 ("CRC-5/USB",          5, 0x05, 0x1F, 1, 1, 0x1F),
 ("CRC-8/SMBUS",        8, 0x07, 0x00, 0, 0, 0x00),
 ("CRC-8/AUTOSAR",      8, 0x2F, 0xFF, 0, 0, 0xFF),
 ("CRC-15/CAN",        15, 0x4599, 0x0000, 0, 0, 0x0000),
 ("CRC-16/IBM-3740",   16, 0x1021, 0xFFFF, 0, 0, 0x0000),
 ("CRC-16/KERMIT",     16, 0x1021, 0x0000, 1, 1, 0x0000),
 ("CRC-16/USB",        16, 0x8005, 0xFFFF, 1, 1, 0xFFFF),
 ("CRC-32/ISO-HDLC",   32, 0x04C11DB7, 0xFFFFFFFF, 1, 1, 0xFFFFFFFF),
 ("CRC-32C",           32, 0x1EDC6F41, 0xFFFFFFFF, 1, 1, 0xFFFFFFFF),
]
if __name__ == "__main__":
    for n, *a in CAT:
        v = crc(b"123456789", *a)
        print("%-16s check('123456789') = 0x%0*X" % (n, (a[0] + 3) // 4, v))
    for s in (b"123456789", b"The quick brown fox jumps over the lazy dog"):
        print("zlib.crc32(%r) = 0x%08X" % (s.decode(), zlib.crc32(s)))''',
    'par_derive': r'''
# Derive the byte-parallel XOR equations of CRC-8 (poly 0x07, MSB first) by superposition:
# next_crc is linear in (crc, data), so feed each single '1' input bit and record which
# output bits it toggles.
def step(c, d, w=8, poly=0x07):
    for i in range(7, -1, -1):
        fb = ((c >> (w - 1)) & 1) ^ ((d >> i) & 1)
        c = ((c << 1) & ((1 << w) - 1)) ^ (poly if fb else 0)
    return c
terms = {o: [] for o in range(8)}
for j in range(8):
    for name, c, d in (("c", 1 << j, 0), ("d", 0, 1 << j)):
        r = step(c, d)
        for o in range(8):
            if (r >> o) & 1:
                terms[o].append((name, j))
for o in range(7, -1, -1):
    # c[j] and d[j] always appear together (x = c ^ d)
    xs = sorted({j for n, j in terms[o]}, reverse=True)
    assert all(("c", j) in terms[o] and ("d", j) in terms[o] for j in xs)
    print("crc'[%d] = %s" % (o, " ^ ".join("x[%d]" % j for j in xs)))''',
    'secded': r'''
// Hamming SECDED (72,64). Codeword bit k (k = 1..71) is Hamming position k; positions
// 1,2,4,...,64 hold the 7 check bits, the other 64 hold data. Bit 0 is overall parity.
module secded72_enc (
  input  logic [63:0] d,
  output logic [71:0] cw
);
  always @* begin
    int j;  j = 0;  cw = '0;
    for (int k = 1; k < 72; k++)                          // scatter data bits
      if ((k & (k - 1)) != 0) begin cw[k] = d[j]; j++; end
    for (int p = 0; p < 7; p++)                           // check bit at 2^p covers
      for (int k = 1; k < 72; k++)                        // every position with bit p set
        if (((k >> p) & 1) && (k != (1 << p))) cw[1 << p] ^= cw[k];
    cw[0] = ^cw[71:1];                                    // overall (DED) parity
  end
endmodule

module secded72_dec (
  input  logic [71:0] cw_in,
  output logic [63:0] d,
  output logic [6:0]  syndrome,
  output logic        ce,        // corrected single-bit error
  output logic        ue         // uncorrectable (double) error detected
);
  logic [71:0] cw;  logic ovp;
  always @* begin
    int j;
    syndrome = '0;
    for (int k = 1; k < 72; k++) if (cw_in[k]) syndrome ^= k[6:0];  // XOR of set positions
    ovp = ^cw_in;                                                    // 1 = odd # of flips
    cw  = cw_in;  ce = 1'b0;  ue = 1'b0;
    if (ovp) begin                                   // odd: assume one error, correct it
      if (syndrome < 72) begin cw[syndrome] = ~cw[syndrome]; ce = 1'b1; end
      else ue = 1'b1;                                // points outside the word: >= 3 flips
    end else if (syndrome != 0) ue = 1'b1;           // even and nonzero: double error
    j = 0;  d = '0;
    for (int k = 1; k < 72; k++)
      if ((k & (k - 1)) != 0) begin d[j] = cw[k]; j++; end
  end
endmodule''',
    'tb_secded': r'''
module tb;
  logic [63:0] d, dq;  logic [71:0] cw, rx;  logic [6:0] syn;  logic ce, ue;
  secded72_enc enc (.d, .cw);
  secded72_dec dec (.cw_in(rx), .d(dq), .syndrome(syn), .ce, .ue);
  int n0 = 0, bad0 = 0, n1 = 0, fix1 = 0, n2 = 0, det2 = 0, miss2 = 0;
  initial begin
    d = 64'h0123_4567_89AB_CDEF; rx = cw; #1;       // show one example
    $display("data=%h  check bits (pos 64,32,16,8,4,2,1,0) = %b%b%b%b%b%b%b%b", d,
             cw[64], cw[32], cw[16], cw[8], cw[4], cw[2], cw[1], cw[0]);
    rx = cw ^ (72'd1 << 37); #1;
    $display("flip bit 37 -> syndrome=%0d ce=%b ue=%b data %s", syn, ce, ue,
             dq == d ? "restored" : "WRONG");
    rx = cw ^ (72'd1 << 37) ^ (72'd1 << 5); #1;
    $display("flip bits 37,5 -> syndrome=%0d ce=%b ue=%b (detected only)", syn, ce, ue);
    for (int t = 0; t < 2000; t++) begin
      d = {$urandom, $urandom}; #1;
      rx = cw; #1; n0++; if (ce || ue || dq != d) bad0++;
      for (int b = 0; b < 72; b++) begin              // every single-bit error
        rx = cw ^ (72'd1 << b); #1; n1++;
        if (ce && !ue && dq == d) fix1++;
      end
      for (int e = 0; e < 20; e++) begin              // random double-bit errors
        int a, b;  a = $urandom % 72;  do b = $urandom % 72; while (b == a);
        rx = cw ^ (72'd1 << a) ^ (72'd1 << b); #1; n2++;
        if (ue && !ce) det2++; else miss2++;
      end
    end
    $display("no error    : %0d words,  false flags/corruption=%0d", n0, bad0);
    $display("single error: %0d cases,  corrected=%0d", n1, fix1);
    $display("double error: %0d cases,  detected (ue=1)=%0d, missed=%0d", n2, det2, miss2);
    $finish;
  end
endmodule''',
    'credit': r'''
// Credit-based flow control: TX may send only while it holds a credit; RX returns one
// credit each time it frees a buffer slot. Both directions have LAT cycles of latency.
module credit_link #(parameter int CREDITS = 4, parameter int LAT = 3) (
  input  logic clk, rst_n,
  input  logic rx_drain,                   // RX consumer takes one entry this cycle
  output logic sent, overflow,
  output int   occupancy
);
  logic [LAT-1:0] fwd, ret;                // data and credit-return pipelines
  int credits;
  assign sent = (credits > 0);             // TX always has data: send whenever allowed
  wire pop = rx_drain && (occupancy > 0);
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      fwd <= '0; ret <= '0; credits <= CREDITS; occupancy <= 0; overflow <= 1'b0;
    end else begin
      fwd       <= {fwd[LAT-2:0], sent};   // data takes LAT cycles to arrive
      ret       <= {ret[LAT-2:0], pop};    // a credit takes LAT cycles to come back
      credits   <= credits - sent + ret[LAT-1];
      occupancy <= occupancy + fwd[LAT-1] - pop;
      if (occupancy + fwd[LAT-1] - pop > CREDITS) overflow <= 1'b1;   // must never happen
    end
endmodule''',
    'serdes': r'''
`timescale 1ns/1ps
// Fractional baud-tick generator: tick rate = f_clk * INC / 2^16 (phase accumulator).
module tick_gen #(parameter int INC = 2416) (
  input  logic clk, rst_n,
  output logic tick                        // one-cycle pulse at OSR x baud
);
  logic [15:0] acc;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin acc <= '0; tick <= 1'b0; end
    else        {tick, acc} <= {1'b0, acc} + INC;      // carry out = tick
endmodule

// Framed serializer: start(0) | DW data bits LSB first | optional even parity | stop(1)
module ser_tx #(parameter int DW = 8, OSR = 16, PAR = 1) (
  input  logic          clk, rst_n, tick,
  input  logic          in_valid,
  output logic          in_ready,
  input  logic [DW-1:0] in_data,
  output logic          line             // registered: no glitches on the pin
);
  localparam int NB = DW + PAR + 2;       // bits per frame
  logic [NB-1:0] sh, frame;
  logic [$clog2(NB+1)-1:0] nleft;          // bits still to send
  logic [$clog2(OSR)-1:0]  ph;             // tick count inside the bit
  always_comb begin
    frame = '1; frame[0] = 1'b0; frame[DW:1] = in_data;
    if (PAR) frame[DW+1] = ^in_data;       // even parity
  end
  assign in_ready = (nleft == 0);
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin sh <= '1; nleft <= '0; ph <= '0; line <= 1'b1; end
    else begin
      if (in_valid && in_ready) begin sh <= frame; nleft <= NB; ph <= '0; end
      else if (tick && nleft != 0) begin
        ph <= ph + 1'b1;
        if (ph == OSR - 1) begin sh <= {1'b1, sh[NB-1:1]}; nleft <= nleft - 1'b1; end
      end
      line <= (nleft != 0) ? sh[0] : 1'b1;             // idle high
    end
endmodule

// Deserializer: 2-flop synchronizer, start-bit validation at mid-bit, 3-sample
// majority vote around each bit centre, framing and parity error flags.
module ser_rx #(parameter int DW = 8, OSR = 16, PAR = 1) (
  input  logic          clk, rst_n, tick,
  input  logic          line_async,
  output logic          out_valid,
  output logic [DW-1:0] out_data,
  output logic          frame_err, par_err
);
  localparam int NB = DW + PAR + 2;
  logic [1:0] sync;  wire ln = sync[1];
  logic       busy;
  logic [$clog2(OSR)-1:0]  ph;
  logic [$clog2(NB)-1:0]   bitn;
  logic [1:0]  smp;                        // first two of the three centre samples
  logic [NB-1:0] fr;                       // received frame, bit 0 = start
  wire maj = (smp[1] & smp[0]) | (smp[1] & ln) | (smp[0] & ln);
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      sync <= 2'b11; busy <= 1'b0; ph <= '0; bitn <= '0; smp <= '0; fr <= '0;
      out_valid <= 1'b0; out_data <= '0; frame_err <= 1'b0; par_err <= 1'b0;
    end else begin
      sync      <= {sync[0], line_async};
      out_valid <= 1'b0;
      if (tick) begin
        if (!busy) begin
          if (!ln) begin busy <= 1'b1; ph <= '0; bitn <= '0; end   // possible start
        end else begin
          ph <= ph + 1'b1;
          if (ph == OSR/2 - 1 || ph == OSR/2) smp <= {smp[0], ln};
          if (ph == OSR/2 + 1) begin                       // third sample: decide
            fr[bitn] <= maj;
            if (bitn == 0 && maj) busy <= 1'b0;            // glitch, not a start bit
            if (bitn == NB - 1) begin                      // stop bit centre: done
              busy      <= 1'b0;                           // re-arm for next start
              out_valid <= 1'b1;
              out_data  <= fr[DW:1];
              frame_err <= !maj;
              par_err   <= PAR ? (^fr[DW+PAR:1]) : 1'b0;   // even parity over data+P
            end
          end
          if (ph == OSR - 1) bitn <= bitn + 1'b1;
        end
      end
    end
endmodule''',
    'chk': r'''
`timescale 1ns/1ps
// Protocol checker, TX domain. It knows the bit timing (the same tick) and checks:
//  R1 edges only at a bit boundary (+-1 tick)        R2 start bit is 0
//  R3 stop bit is 1                                    R4 parity is even
//  R5 in_data is stable while in_valid && !in_ready (valid/ready rule)
module frame_chk #(parameter int DW = 8, OSR = 16, PAR = 1) (
  input logic clk, rst_n, tick, line,
  input logic in_valid, in_ready, input logic [DW-1:0] in_data
);
  localparam int NB = DW + PAR + 2;
  int ph, bitn, frames = 0, errors = 0;  logic busy = 0, prev = 1, pv = 0;
  logic [NB-1:0] fr;  logic [DW-1:0] pd;
  task automatic fail(input string rule);
    errors++; $display("  CHECK FAIL t=%0d us: %s (frame %0d)", $time / 1000, rule, frames);
  endtask
  always @(posedge clk) if (rst_n) begin
    if (pv && !in_ready && in_data !== pd) fail("R5 in_data changed while valid && !ready");
    pv <= in_valid && !in_ready;  pd <= in_data;
    prev <= line;
    if (!busy && prev && !line) begin busy <= 1; ph <= 0; bitn <= 0; end
    else if (busy) begin
      if (line != prev && ph > 1 && ph < OSR - 1) fail("R1 edge inside a bit");
      if (tick) begin
        if (ph == OSR/2) begin
          fr[bitn] = line;
          if (bitn == 0 && line)      fail("R2 start bit not 0");
          if (bitn == NB-1) begin
            if (!line)                  fail("R3 stop bit not 1");
            if (PAR && ^fr[DW+PAR:1])   fail("R4 parity error");
            frames++;  busy <= 0;
          end
        end
        ph <= (ph == OSR - 1) ? 0 : ph + 1;
        if (ph == OSR - 1) bitn <= bitn + 1;
      end
    end
  end
endmodule''',
    'tb_serdes': r'''
`timescale 1ns/1ps
module tb;
  // TX at 50 MHz, RX at 48 MHz: unrelated clocks, 115200 baud, 16x oversampling
  logic tclk = 0, rclk = 0, rst_n = 0;
  always #10.000 tclk = ~tclk;
  always #10.417 rclk = ~rclk;
  logic ttick, rtick, v = 0, rdy, line, ch, rv, fe, pe, kill = 0, flip = 0;
  logic [7:0] d = 0, rd;
  tick_gen #(2416) tg (.clk(tclk), .rst_n, .tick(ttick));   // 50e6*2416/65536 = 1.84326 MHz
  tick_gen #(2517) rg (.clk(rclk), .rst_n, .tick(rtick));   // 48e6*2517/65536 = 1.84351 MHz
  ser_tx    tx  (.clk(tclk), .rst_n, .tick(ttick), .in_valid(v), .in_ready(rdy), .in_data(d),
                 .line);
  assign ch = (line & ~kill) ^ flip;                        // the "channel": error injection
  ser_rx    rx  (.clk(rclk), .rst_n, .tick(rtick), .line_async(ch), .out_valid(rv),
                 .out_data(rd), .frame_err(fe), .par_err(pe));
  frame_chk chk (.clk(tclk), .rst_n, .tick(ttick), .line(ch), .in_valid(v), .in_ready(rdy),
                 .in_data(d));
  logic [7:0] q [$];  int got = 0, bad = 0, nfe = 0, npe = 0;
  always @(posedge rclk) if (rv) begin
    got++; nfe += fe; npe += pe;
    if (!fe && !pe && rd !== q[0]) bad++;
    void'(q.pop_front());
  end
  task automatic send(input logic [7:0] b);
    @(negedge tclk) v = 1; d = b; q.push_back(b);
    @(posedge tclk); while (!rdy) @(posedge tclk);           // handshake completes here
    @(negedge tclk) v = 0;
  endtask
  initial begin
    #100 rst_n = 1;
    for (int i = 0; i < 200; i++) send($urandom);
    wait (tx.nleft == 0); #20000;
    $display("clean   : sent 200, received %0d, data errors=%0d, frame_err=%0d, par_err=%0d,"
             , got, bad, nfe, npe);
    $display("          checker frames=%0d violations=%0d", chk.frames, chk.errors);
    // (1) channel forces the stop bit low; (2) channel flips data bit 0
    fork send(8'h55); begin wait (tx.nleft == 1); kill = 1; wait (tx.nleft == 0); kill = 0; end
    join
    fork send(8'hA7);
         begin wait (tx.nleft == 10); flip = 1; wait (tx.nleft == 9); flip = 0; end
    join
    wait (tx.nleft == 0); #20000;
    // (3) the producer breaks valid/ready: 0x22 waits for ready, then data changes to 0x33
    @(negedge tclk) v = 1; d = 8'h11; q.push_back(8'h11);   // accepted at once (TX idle)
    @(negedge tclk)        d = 8'h22; q.push_back(8'h22);   // TX busy: valid held high
    repeat (3) @(negedge tclk); d = 8'h33;                  // VIOLATION of the rule
    @(posedge tclk); while (!rdy) @(posedge tclk);
    @(negedge tclk) v = 0;
    #1000;
    wait (tx.nleft == 0); #20000;
    $display("injected: received %0d, frame_err=%0d, par_err=%0d, data errors=%0d,",
             got, nfe, npe, bad);
    $display("          checker violations=%0d", chk.errors);
    $finish;
  end
endmodule''',
    'sva': r'''
// Concurrent assertions for ser_tx, attached with bind (no change to the RTL).
module ser_tx_sva #(parameter int DW = 8) (
  input logic clk, rst_n, in_valid, in_ready, line, input logic [DW-1:0] in_data
);
  // valid/ready: once valid is up without ready, valid and data must hold
  a_hold:  assert property (@(posedge clk) disable iff (!rst_n)
                            in_valid && !in_ready |=> in_valid && $stable(in_data))
             else $error("hold rule");
  // an accepted word gives a start bit (0) two clocks later (line is registered)
  a_start: assert property (@(posedge clk) disable iff (!rst_n)
                            $past(in_valid && in_ready) |=> !line)
             else $error("no start bit");
  // idle line is high
  a_idle:  assert property (@(posedge clk) disable iff (!rst_n)
                            in_ready && $past(in_ready) |-> line)
             else $error("idle line low");
  c_accept: cover property (@(posedge clk) disable iff (!rst_n) in_valid && in_ready);
endmodule

bind ser_tx ser_tx_sva #(.DW(DW)) sva (.*);''',
    'sva_full': r'''
// Concurrent assertions for ser_tx, attached with bind (no change to the RTL).
module ser_tx_sva #(parameter int DW = 8) (
  input logic clk, rst_n, in_valid, in_ready, line, input logic [DW-1:0] in_data
);
  default clocking cb @(posedge clk); endclocking
  default disable iff (!rst_n);
  // valid/ready: once valid is up without ready, valid and data must hold
  a_hold:  assert property (in_valid && !in_ready |=> in_valid && $stable(in_data))
             else $error("a_hold: valid dropped or data changed before ready");
  // an accepted word produces a start bit (0) two clocks later (line is registered)
  a_start: assert property (in_valid && in_ready |=> ##1 !line)
             else $error("a_start: no start bit after handshake");
  // idle line is high
  a_idle:  assert property (in_ready && $past(in_ready) |-> line)
             else $error("a_idle: line low while idle");
  c_back2back: cover property (in_valid && in_ready ##[1:$] in_valid && in_ready);
endmodule

bind ser_tx ser_tx_sva #(.DW(DW)) u_sva (.*);''',
    'rise': r'''
# Open-drain bus: rise time (30% -> 70% VDD) of an RC pull-up and the pull-up range
import math
k = math.log(0.7 / 0.3)                  # t_r = RC * ln(0.7/0.3) = 0.8473 RC
print("t_r(30%%->70%%) = %.4f x Rp x Cb" % k)
vdd, vol = 3.3, 0.4
for mode, tr, iol in (("Sm  100 kHz", 1000e-9, 3e-3), ("Fm  400 kHz", 300e-9, 3e-3),
                      ("Fm+   1 MHz", 120e-9, 20e-3)):
    rmin = (vdd - vol) / iol
    rmax = ["%dpF:%5.0f" % (c * 1e12, tr / (k * c)) for c in (50e-12, 100e-12, 400e-12)]
    print("%s t_r<=%4.0f ns  Rp_min=%4.0f  Rp_max: %s" % (mode, tr * 1e9, rmin,
          ", ".join(rmax)))''',
    'od': r'''
// Open-drain pad as seen from RTL: the core never drives '1'. It drives oe=1 to pull
// the pin low and oe=0 to release it; the board pull-up makes the released level '1'.
module od_pad (
  input  logic pull_low,          // from the controller: 1 = drive the pin low
  output logic in,                // back to the controller (through a synchronizer)
  inout  wire  pin
);
  assign pin = pull_low ? 1'b0 : 1'bz;     // oe = pull_low, o = 0
  assign in  = pin;
endmodule

module tb;
  tri1 bus;                                // tri1 = net with a pull-up (resistor model)
  logic a = 0, b = 0;  logic ia, ib;
  od_pad pa (.pull_low(a), .in(ia), .pin(bus));
  od_pad pb (.pull_low(b), .in(ib), .pin(bus));
  initial begin
    $display("pull_low a b | bus  (wired-AND)");
    for (int i = 0; i < 4; i++) begin
      {a, b} = i[1:0]; #1 $display("         %0d %0d |  %b", a, b, bus);
    end
  end
endmodule''',
    'crcdiv': r'''
# Long division of 11010011101100 by 1011 (x^3+x+1) over GF(2), printing each step
msg, gen = "11010011101100", "1011"
r = list(msg + "000")                         # append 3 zero bits (multiply by x^3)
print(msg + " 000   <- message x^3")
for i in range(len(msg)):
    if r[i] == "1":
        for j in range(4):
            r[i + j] = "0" if r[i + j] == gen[j] else "1"
        pad = " " * (len(msg) - i - 3)
        print(" " * i + gen + pad + "    XOR at bit %2d -> %s" % (i, "".join(r)))
print("remainder (CRC) = " + "".join(r[-3:]))
import zlib
m = b"123456789"; fcs = zlib.crc32(m)
print("residue: crc32(msg+FCS) = 0x%08X" % zlib.crc32(m + fcs.to_bytes(4, "little")))''',
}

OUT = {
    '8b10b': ['table check : 536 codes vs Python reference, mismatches=0', 'D0.0  RD- -> 100111 0100', 'D21.5 RD- -> 101010 1010', 'K28.5 RD- -> 001111 1010  (comma 0011111)', 'K28.5 RD+ -> 110000 0101  (comma 1100000)', 'stream      : 1000000 bits, max run length=5, digital sum in [-2,4]'],
    'py8b10b': ['536 vectors', 'D0.0 1001110100 0110001011', 'D21.5 1010101010 1010101010', 'K28.5 0011111010 1100000101'],
    'manch': ['rx clock error  +0.0%: sent 2012 bits, decoded 2012, bit errors=0, locked=1', 'rx clock error +10.0%: sent 2012 bits, decoded 2012, bit errors=0, locked=1', 'rx clock error -10.0%: sent 2012 bits, decoded 2012, bit errors=0, locked=1', 'rx clock error +20.0%: sent 2012 bits, decoded 2012, bit errors=0, locked=1', 'rx clock error +30.0%: sent 2012 bits, decoded 2059, bit errors=3, locked=1', 'rx clock error -30.0%: sent 2012 bits, decoded 1428, bit errors=740, locked=1'],
    'scram': ['keystream (data=00): ff 17 c0 14 b2 e7 02 82', 'additive: 64 keystream bytes vs Python reference, mismatches=0', 'additive: 1 line-bit error -> 1 bit error(s) after descrambling', 'self-sync: wrong bits before lock=19 (all within the first 58)', 'self-sync: 1 line-bit error -> 3 bit errors (3-term polynomial)'],
    'pyscr': ['FF 17 C0 14 B2 E7 02 82 72 6E 28 A6 BE 6D BF 8D', 'AC 78 83 34 DE 8E 6C E9 01 4F'],
    'crc': ['"123456789"', '  CRC-32 serial   = cbf43926   byte-parallel = cbf43926   zlib.crc32 = cbf43926    MATCH', '  CRC-16/IBM-3740 = 29b1   CRC-15/CAN = 059e   CRC-5/USB = 19', '"The quick brown fox jumps over the lazy dog"', '  CRC-32 serial   = 414fa339   byte-parallel = 414fa339   zlib.crc32 = 414fa339    MATCH'],
    'pycrc': ["CRC-5/USB        check('123456789') = 0x19", "CRC-8/SMBUS      check('123456789') = 0xF4", "CRC-8/AUTOSAR    check('123456789') = 0xDF", "CRC-15/CAN       check('123456789') = 0x059E", "CRC-16/IBM-3740  check('123456789') = 0x29B1", "CRC-16/KERMIT    check('123456789') = 0x2189", "CRC-16/USB       check('123456789') = 0xB4C8", "CRC-32/ISO-HDLC  check('123456789') = 0xCBF43926", "CRC-32C          check('123456789') = 0xE3069283", "zlib.crc32('123456789') = 0xCBF43926", "zlib.crc32('The quick brown fox jumps over the lazy dog') = 0x414FA339"],
    'parderive': ["crc'[7] = x[7] ^ x[6] ^ x[5]", "crc'[6] = x[6] ^ x[5] ^ x[4]", "crc'[5] = x[5] ^ x[4] ^ x[3]", "crc'[4] = x[4] ^ x[3] ^ x[2]", "crc'[3] = x[7] ^ x[3] ^ x[2] ^ x[1]", "crc'[2] = x[6] ^ x[2] ^ x[1] ^ x[0]", "crc'[1] = x[6] ^ x[1] ^ x[0]", "crc'[0] = x[7] ^ x[6] ^ x[0]"],
    'parcost': ['D=  1 data bits/clock: XOR inputs per CRC bit  max=  3  avg=  1.8  total=  59', 'D=  8 data bits/clock: XOR inputs per CRC bit  max= 14  avg=  7.9  total= 252', 'D= 32 data bits/clock: XOR inputs per CRC bit  max= 34  avg= 28.2  total= 904', 'D= 64 data bits/clock: XOR inputs per CRC bit  max= 52  avg= 44.4  total=1422', 'D=128 data bits/clock: XOR inputs per CRC bit  max= 89  avg= 79.7  total=2550'],
    'secded': ['data=0123456789abcdef  check bits (pos 64,32,16,8,4,2,1,0) = 00111001', 'flip bit 37 -> syndrome=37 ce=1 ue=0 data restored', 'flip bits 37,5 -> syndrome=32 ce=0 ue=1 (detected only)', 'no error    : 2000 words,  false flags/corruption=0', 'single error: 144000 cases,  corrected=144000', 'double error: 40000 cases,  detected (ue=1)=40000, missed=0'],
    'secded_py': ['Python: check bits (pos 64,32,16,8,4,2,1,0) = 00111001'],
    'credit': ['credits= 2         throughput=0.250 flits/cycle  max RX occ=1  overflow=0', 'credits= 4         throughput=0.500 flits/cycle  max RX occ=1  overflow=0', 'credits= 6         throughput=0.750 flits/cycle  max RX occ=1  overflow=0', 'credits= 8         throughput=1.000 flits/cycle  max RX occ=1  overflow=0', 'credits=12         throughput=1.000 flits/cycle  max RX occ=1  overflow=0', 'credits= 8 slow RX throughput=0.504 flits/cycle  max RX occ=5  overflow=0'],
    'serdes': ['clean   : sent 200, received 200, data errors=0, frame_err=0, par_err=0,', '          checker frames=200 violations=0', '  CHECK FAIL t=19208 us: R3 stop bit not 1 (frame 200)', '  CHECK FAIL t=19303 us: R4 parity error (frame 201)', '  CHECK FAIL t=19327 us: R5 in_data changed while valid && !ready (frame 202)', 'injected: received 204, frame_err=1, par_err=1, data errors=1,', '          checker violations=3'],
    'sva': ['[190000] %Error: ser_tx_sva.sv:8: Assertion failed in TOP.tb.dut.sva.a_hold: hold rule', '-Info: ser_tx_sva.sv:8: Verilog $stop, ignored due to +verilator+error+limit', 'done at 175570 ns'],
    'rise': ['t_r(30%->70%) = 0.8473 x Rp x Cb', 'Sm  100 kHz t_r<=1000 ns  Rp_min= 967  Rp_max: 50pF:23604, 100pF:11802, 400pF: 2951', 'Fm  400 kHz t_r<= 300 ns  Rp_min= 967  Rp_max: 50pF: 7081, 100pF: 3541, 400pF:  885', 'Fm+   1 MHz t_r<= 120 ns  Rp_min= 145  Rp_max: 50pF: 2833, 100pF: 1416, 400pF:  354'],
    'od': ['pull_low a b | bus  (wired-AND)', '         0 0 |  1', '         0 1 |  0', '         1 0 |  0', '         1 1 |  0'],
    'crcdiv': ['11010011101100 000   <- message x^3', '1011               XOR at bit  0 -> 01100011101100000', ' 1011              XOR at bit  1 -> 00111011101100000', '  1011             XOR at bit  2 -> 00010111101100000', '   1011            XOR at bit  3 -> 00000001101100000', '       1011        XOR at bit  7 -> 00000000110100000', '        1011       XOR at bit  8 -> 00000000011000000', '         1011      XOR at bit  9 -> 00000000001110000', '          1011     XOR at bit 10 -> 00000000000101000', '           1011    XOR at bit 11 -> 00000000000000100', 'remainder (CRC) = 100', 'residue: crc32(msg+FCS) = 0x2144DF1C'],
}


def _v(name, caption=None):
    """Show a verified source (RTL, testbench or Python reference) from SRC."""
    code(SRC[name].strip("\n").split("\n"), caption)


def _o(name, caption=None):
    """Show the real simulator / Python output captured for an example."""
    out(OUT[name], caption)


def box(kind, title, body):
    """Common box(), but multi-item bodies get a leading dash per item."""
    if isinstance(body, (list, tuple)) and len(body) > 1:
        body = ["- " + b for b in body]
    _box(kind, title, body)


# =============================================================================
#                          PART I - FOUNDATIONS
# =============================================================================
def part1():
    part("Foundations",
         "Every protocol in this book, from a 100 kHz I2C sensor bus to a "
         "64 GT/s PCIe link, is built from the same small set of ideas: how "
         "bits become voltages and back, how the receiver knows when to sample, "
         "how two sides agree that a transfer happened, how a sender avoids "
         "overrunning a receiver, and how corrupted data is detected and "
         "repaired. This part builds that toolkit once - with a map of the SoC, "
         "the physics of signalling, line codes, scramblers, CRC and ECC, and "
         "the RTL and verification patterns every controller reuses - so the "
         "protocol chapters that follow can concentrate on what is unique to "
         "each standard.")
    _ch1()
    _ch2()
    _ch3()
    _ch4()


# ---------------------------------------------------------------- Ch 1 ----
def _ch1():
    chapter("Communication in an SoC: a Map of Protocols, Layers and the "
            "Roadmap", newpage=False)
    p("A system-on-chip is a city of intellectual-property (IP) blocks: CPU "
      "clusters, GPUs and NPUs, memory controllers, DMA engines, security "
      "islands, dozens of peripherals and a handful of very fast I/O ports. "
      "None of those blocks is useful alone. What turns them into a product is "
      "communication - on-chip buses carrying loads and stores, low-speed "
      "serial buses talking to sensors and power ICs, multi-gigabit links "
      "talking to other chips, memory interfaces feeding the processors, and "
      "debug ports that let engineers look inside. Each of those conversations "
      "follows a **protocol**: a precise contract for signals, timing, "
      "framing, ordering and error handling that two independently designed "
      "blocks can both implement and still interoperate.")
    p("This chapter draws the map. It places every protocol in this book on "
      "one SoC block diagram, classifies protocols along the axes that "
      "actually drive design decisions, introduces the layered model that "
      "lets us reason about a PCIe or USB stack one layer at a time, explains "
      "who builds which part of an interface (and who buys it), and closes "
      "with typical numbers and a roadmap from chapter to job role.")

    h2("Why protocols dominate SoC engineering")
    p("On a typical large SoC the majority of the gates in the design are "
      "licensed or reused IP, and most of the integration effort is spent "
      "on the **interfaces** between blocks: bus fabrics, bridges, clock and "
      "reset crossings, PHY integration and the verification of all of it. "
      "A protocol is what makes that reuse possible: a USB controller from "
      "one vendor connects to a USB PHY from another because both implement "
      "UTMI+ or PIPE; an Arm core connects to your accelerator because both "
      "speak AXI. When a protocol is misunderstood, the result is not a local "
      "bug but a system failure - a hang, silent data corruption, or a device "
      "that fails certification.")
    tbl(["What a protocol specifies", "Example questions it answers"],
        [["**Signals and electrical levels**", "Which wires exist, their "
          "direction, voltage swing, termination, drive strength"],
         ["**Timing**", "When is data valid? Which clock edge samples it? What "
          "are setup/hold, turnaround and minimum pulse widths?"],
         ["**Framing / encoding**", "How does the receiver find the start of "
          "a byte, packet or burst? How are bits encoded on the wire?"],
         ["**Transactions**", "What is a read, a write, a burst, a message, "
          "an interrupt? What response does each produce?"],
         ["**Flow control**", "How does a slow receiver stop a fast sender "
          "without losing data?"],
         ["**Ordering and coherency**", "Which operations may overtake which? "
          "When does a write become visible to other agents?"],
         ["**Errors and recovery**", "How are corruption, timeouts and "
          "protocol violations detected, reported and recovered?"],
         ["**Power and link management**", "How does the link enter and leave "
          "low-power states? Who may wake whom?"],
         ["**Discovery and configuration**", "How does software learn what is "
          "attached and set it up (addresses, enumeration, capability "
          "registers)?"]],
        widths=[1.1, 2.4], bold_first=False,
        caption="Table 1.1 - The dimensions every protocol specification covers.")
    box("key", "The one-sentence definition",
        "A protocol is a contract between two independently designed state "
        "machines. Everything in this book - wires, codes, handshakes, "
        "packets, credits, CRCs - exists so that both machines always agree "
        "on what the other one has done.")

    h2("The protocol map of a modern SoC")
    p("Figure 1.1 shows a representative application-processor or "
      "edge-AI SoC. The exact mix changes by market (a phone SoC has MIPI "
      "camera and display, a server chip has many PCIe/CXL lanes and DDR5 "
      "channels, a microcontroller may stop at AHB and APB), but the "
      "**structure** is universal: a high-performance coherent core, a "
      "hierarchy of on-chip buses, peripheral buses behind bridges, "
      "high-speed PHYs at the die edge, memory interfaces, and debug.")
    diagram([
        '  +---------------------------------- SoC die ----------------------------------+',
        '  |  +-----------+  +-----------+   +-----+  +-----+                            |',
        '  |  | CPU clstr |  | CPU clstr |   | GPU |  | NPU |   coherent agents          |',
        '  |  +-----+-----+  +-----+-----+   +--+--+  +--+--+                            |',
        '  |        |  CHI / ACE   |            | ACE-Lite / AXI                         |',
        '  |  +-----+--------------+------------+--------+----------+   +------------+   |',
        '  |  |   Coherent interconnect / NoC  (CHI, AXI, NoC pkts) |---| System     |   |',
        '  |  +---+---------+---------------+----------+----------+-+   | cache/SRAM |   |',
        '  |      | AXI     | AXI           | AXI      | AXI      |     +------------+   |',
        '  |  +---+----+ +--+-----------+ +-+------+ +-+------+ +-+-------------------+  |',
        '  |  | DDR/   | | PCIe / CXL   | | USB    | | Eth    | | Display/Camera      |  |',
        '  |  | LPDDR  | | ctrl         | | ctrl   | | MAC    | | DSI, CSI-2 ctrl     |  |',
        '  |  | ctrl   | +------+-------+ +--+-----+ +--+-----+ +-+-------------------+  |',
        '  |  +--+-----+   PIPE |     UTMI/PIPE |   xMII |       PPI |                   |',
        '  |     | DFI  +------+-----+ +-------+-+ +-----+--+ +------+---------------+   |',
        '  |  +--+----+ | PCIe SerDes| | USB PHY | | Eth PHY| | D-PHY / C-PHY        |   |',
        '  |  |DDR PHY| +------------+ +---------+ +--------+ +----------------------+   |',
        '  |  +-------+                                                                  |',
        '  |      AXI -> AHB bridge -> AHB -> APB bridge -> APB peripheral bus           |',
        '  |  +------+ +------+ +------+ +------+ +------+ +------+ +------+ +------+    |',
        '  |  | UART | | SPI/ | | I2C/ | | I3C  | | CAN  | | I2S/ | | GPIO | |timers|    |',
        '  |  |      | | QSPI | |SMBus | |      | | FD/XL| | TDM  | |      | | WDT  |    |',
        '  |  +------+ +------+ +------+ +------+ +------+ +------+ +------+ +------+    |',
        '  |  +------------------+  +---------------------+  +-------------------+       |',
        '  |  | UCIe / D2D adapt.|  | Debug: DAP (JTAG,   |  | DFT: 1149.1 TAP,  |       |',
        '  |  | to chiplets      |  | SWD), CoreSight     |  | IEEE 1500, 1687   |       |',
        '  |  +------------------+  +---------------------+  +-------------------+       |',
        '  +-----------------------------------------------------------------------------+',
        '     |HBM (on interposer)   |pins: DDR, PCIe, USB, Eth, MIPI, SPI, I2C, UART, JTAG',
    ], "Figure 1.1 - Where every protocol in this book lives on an SoC. CHI/ACE/"
       "AXI/AHB/APB inside; SPI, I2C, UART, I3C, CAN and I2S to peripherals; "
       "USB, PCIe, Ethernet, MIPI, DDR, HBM and UCIe at high speed; JTAG/SWD "
       "for debug and test.")
    p("Reading the figure from the processors outward:")
    bul(["**Coherent core.** CPU clusters and coherent accelerators exchange "
         "cache lines with a coherent interconnect using **AMBA CHI** (packet-"
         "based, used in large meshes) or **ACE** (an AXI extension). Chapter 9 "
         "covers MESI/MOESI, ACE and CHI.",
         "**System interconnect.** Bulk data moves on **AXI4** (Chapter 7), "
         "control registers on **AXI4-Lite** and streams on **AXI4-Stream** "
         "(Chapter 8). Large SoCs packetize these into a **network-on-chip** "
         "(Chapter 10).",
         "**Peripheral buses.** Bridges step down to **AHB** (Chapter 6) and "
         "**APB** (Chapter 5), where the register blocks of slow peripherals "
         "live.",
         "**Low-speed peripheral protocols** leave the chip on a few pins: "
         "**UART** (11), **SPI/QSPI/xSPI** (12), **I2C/SMBus/PMBus** (13), "
         "**I3C** (14), **CAN/LIN/FlexRay** (15) and **I2S/TDM/PDM** audio "
         "(16).",
         "**High-speed interfaces** pair a digital **controller** with an "
         "analog-heavy **PHY**: **USB** (17), **PCIe/CXL** (18), **Ethernet** "
         "(19), **DDR/LPDDR/HBM** and flash (20), **MIPI D-PHY/C-PHY, CSI-2, "
         "DSI**, HDMI and DisplayPort (21), and **SerDes, JESD204 and UCIe** "
         "for chip-to-chip and die-to-die (22).",
         "**Debug and test**: the **JTAG** TAP (IEEE 1149.1), **IEEE 1500** "
         "core wrappers, **IJTAG** (IEEE 1687) and Arm **CoreSight** with "
         "**SWD** (23)."])
    tbl(["Group", "Protocols", "Typical owner in the SoC team", "Ch."],
        [["On-chip coherent", "CHI, ACE, ACE-Lite", "Interconnect/fabric team, "
          "CPU subsystem", "9"],
         ["On-chip non-coherent", "AXI4, AXI4-Lite, AXI4-Stream, AHB, APB, "
          "TileLink, Wishbone, Avalon, OCP, NoC", "Fabric team, every IP "
          "designer", "5-10"],
         ["Low-speed peripheral", "UART, SPI, QSPI, xSPI, I2C, SMBus, I3C, CAN, "
          "LIN, I2S, PDM, 1-Wire, MDIO", "Peripheral subsystem RTL, firmware",
          "11-16"],
         ["High-speed serial", "USB 2/3/USB4, PCIe, CXL, Ethernet, MIPI, "
          "HDMI, DP", "Controller RTL + PHY (analog/mixed-signal) + SW", "17-19, 21"],
         ["Memory", "DDR4/5, LPDDR4/5, HBM, DFI, ONFI, eMMC, SD, UFS",
          "Memory subsystem team, PHY vendor, PD/SI", "20"],
         ["Chip-to-chip / D2D", "SerDes links, JESD204B/C, Aurora, "
          "Interlaken, UCIe, BoW", "Architecture, PHY, packaging", "22"],
         ["Debug / test", "JTAG, IEEE 1500, IEEE 1687, SWD, CoreSight, trace",
          "DFT team, debug architects", "23"]],
        widths=[1.2, 2.3, 2.0, 0.5], bold_first=True,
        caption="Table 1.2 - Protocol families, the team that usually owns "
                "them, and the chapter that covers them.")

    h2("Taxonomy: six ways to classify a link")
    p("Hundreds of protocols exist, but a handful of binary choices explain "
      "most of their differences. When you meet a new interface, place it on "
      "each axis below and you already know most of its architecture.")
    h3("On-chip versus off-chip")
    p("On-chip wires are short, cheap, numerous and share one silicon "
      "process, so on-chip protocols are **wide, parallel and synchronous** "
      "(an AXI data bus of 128-512 bits is normal) and rarely need error "
      "correction on the wires. Off-chip wires cost package balls, board "
      "area and power, see reflections, crosstalk and ground noise, and "
      "connect parts from different vendors - so off-chip protocols are "
      "**narrow**, carefully specified electrically, and usually protected "
      "by CRC or ECC.")
    h3("Parallel versus serial")
    p("A **parallel** bus sends many bits per clock on many wires (AXI, "
      "DDR's 64-bit data bus). Its limit is **skew**: all bits must arrive "
      "inside the same sampling window. A **serial** link sends bits one "
      "after another on one wire or differential pair; high-speed serial "
      "links embed the clock in the data and scale by adding **lanes** that "
      "are deskewed independently (PCIe x16, USB4 two lanes). Above a few "
      "hundred Mb/s per wire off-chip, serial wins because each lane "
      "recovers its own timing.")
    h3("Synchronous versus asynchronous (and how the clock travels)")
    p("A **synchronous** interface shares or forwards a clock (SPI's SCLK, "
      "I2C's SCL, DDR's CK and DQS). An **asynchronous** interface has no "
      "clock wire: UART agrees on a nominal baud rate and resynchronizes on "
      "each start bit; PCIe and USB 3 recover the clock from data "
      "transitions with a CDR. On chip, 'asynchronous' usually means the two "
      "sides run on unrelated clocks and the protocol must tolerate a "
      "clock-domain crossing. Chapter 2 treats clocking schemes in depth.")
    h3("Master/slave versus peer-to-peer")
    p("In a **master/slave** protocol (the current AMBA specifications say "
      "**Manager/Subordinate**; I2C and I3C now say **controller/target**) "
      "only the initiator starts transactions and the responder only "
      "answers - APB, AHB, AXI, SPI, I2C. **Peer** protocols let either side "
      "initiate: CAN nodes arbitrate for the bus, Ethernet stations send "
      "whenever they like, and PCIe endpoints issue their own DMA reads and "
      "writes (the root/endpoint distinction is about topology and "
      "configuration, not about who may start a transfer). Multi-master "
      "buses need **arbitration** - centralized (an AHB arbiter) or "
      "distributed (CAN's bitwise arbitration, I2C's wired-AND arbitration).")
    h3("Memory-mapped versus streaming versus packet")
    tbl(["Style", "What moves", "Addressing", "Examples"],
        [["**Memory-mapped**", "Reads and writes of addressed locations; every "
          "request gets a response", "Address on every transaction", "APB, "
          "AHB, AXI4, AXI4-Lite, CHI, register access over I2C/SPI"],
         ["**Streaming**", "An ordered flow of data words with framing "
          "markers (last, keep, user bits), usually no response", "None, or "
          "a destination ID (TDEST)", "AXI4-Stream, I2S, CSI-2 pixel streams "
          "inside the chip, JESD204 sample streams"],
         ["**Packet / message**", "Self-describing packets with a header "
          "(type, length, addresses or IDs), payload and CRC; may be routed "
          "and retried", "Header fields; routing by address or ID", "PCIe "
          "TLPs, USB packets, Ethernet frames, CAN frames, CHI flits, NoC "
          "packets"]],
        widths=[1.1, 2.2, 1.4, 2.2],
        caption="Table 1.3 - The three transfer styles. Many systems stack "
                "them: PCIe carries memory-mapped reads and writes inside "
                "packets.")
    h3("Putting the axes together")
    tbl(["Protocol", "On/off", "Width", "Clocking", "Initiators", "Style"],
        [["APB", "on", "parallel 8-32 b", "sync", "1 manager", "mem-mapped"],
         ["AXI4", "on", "parallel 32-1024 b", "sync", "many (via fabric)",
          "mem-mapped"],
         ["AXI4-Stream", "on", "parallel", "sync", "producer", "streaming"],
         ["CHI", "on", "parallel flits", "sync", "many", "packet"],
         ["UART", "off", "serial 1 wire/dir", "async (start bit)", "peer",
          "byte stream"],
         ["SPI", "off", "serial, 1/2/4/8 data", "sync (SCLK)", "1 host",
          "mem-mapped/cmd"],
         ["I2C", "off", "serial, 2 wires", "sync (SCL), open-drain",
          "multi-controller", "mem-mapped/cmd"],
         ["CAN", "off", "serial, 1 diff pair", "async + bit sync", "peer",
          "message"],
         ["USB 2.0", "off", "serial, 1 diff pair", "embedded (NRZI)",
          "host only", "packet"],
         ["PCIe", "off", "serial lanes x1-x16", "embedded (CDR)", "peer (RC/EP)",
          "packet"],
         ["DDR5", "off", "parallel 2 x 32 b (+ECC)", "source-sync (DQS)",
          "1 controller", "command/burst"],
         ["UCIe", "off (in-package)", "parallel lanes", "forwarded clock",
          "peer", "flit/packet"],
         ["JTAG", "off", "serial (TDI/TDO)", "sync (TCK)", "1 debugger",
          "scan shift"]],
        widths=[1.0, 0.8, 1.5, 1.4, 1.2, 1.1], bold_first=True,
        caption="Table 1.4 - A dozen protocols on the six axes.")

    h2("The layered model: PHY, PCS, link, transaction, application")
    p("Complex protocols are specified - and built - in **layers**. Each "
      "layer offers a service to the one above and hides the details of the "
      "one below. This is the idea behind the seven-layer OSI reference "
      "model, but SoC protocols use a flatter, more hardware-oriented "
      "stack:")
    diagram([
        "  Transmit side                                   Receive side",
        "  +-----------------------+                       +-----------------------+",
        "  | Application / SW      |  reads, writes, DMA   | Application / SW      |",
        "  +-----------------------+                       +-----------------------+",
        "  | Transaction layer     |  requests, completions, ordering, flow ctrl  |",
        "  +-----------------------+                       +-----------------------+",
        "  | Link (data link) layer|  sequence numbers, CRC, ACK/NAK, retry       |",
        "  +-----------------------+                       +-----------------------+",
        "  | PCS (logical PHY)     |  encoding, scrambling, framing, lane deskew  |",
        "  +-----------------------+                       +-----------------------+",
        "  | PMA / PMD (electrical)|  serializer, driver, equalizer, CDR, PLL     |",
        "  +-----------+-----------+                       +-----------+-----------+",
        "              |                    channel                    |",
        "              +===============================================+",
    ], "Figure 1.2 - The generic layered stack of a high-speed protocol. Each "
       "layer talks logically to its peer; physically, data goes down one "
       "side and up the other.")
    tbl(["Layer", "OSI analogue", "Job", "PCIe name", "Ethernet name",
         "Usually built as"],
        [["PMD / PMA", "1 Physical", "Drive and receive the analog signal, "
          "serialize, recover clock", "Electrical sub-block", "PMD, PMA",
          "Analog/mixed-signal hard macro"],
         ["PCS", "1 Physical (upper)", "Line coding, scrambling, block/symbol "
          "alignment, lane deskew, clock compensation", "Logical sub-block",
          "PCS (+ FEC)", "Synthesizable RTL, often in the PHY IP"],
         ["Link", "2 Data link", "Framing, CRC, sequence numbers, ACK/NAK "
          "retry, link-level flow control", "Data Link Layer (DLLP)", "MAC",
          "Controller RTL"],
         ["Transaction", "3-4 Network/Transport (loosely)", "Requests and "
          "completions, tags, ordering, credits, routing", "Transaction Layer "
          "(TLP)", "(above MAC: IP/TCP in software)", "Controller RTL"],
         ["Application", "5-7", "The user's reads, writes, DMA, messages",
          "Software, drivers", "Software stack", "SoC fabric bridge, "
          "firmware, driver"]],
        widths=[0.9, 1.0, 2.0, 1.1, 1.0, 1.4], bold_first=True,
        caption="Table 1.5 - Layers mapped to OSI and to two real stacks. OSI "
                "mapping is approximate; hardware standards define their own "
                "layers.")
    box("intuit", "Why layering matters to an RTL engineer",
        "Layers are also **team and IP boundaries**. The PHY vendor owns "
        "PMA/PMD (and often the PCS); your controller starts at a standard "
        "interface such as PIPE. The link layer can be verified with a "
        "transaction-level PHY model, the PHY with bit-level stimulus. When a "
        "bug appears, the first question is always: which layer dropped the "
        "ball?")
    p("Simple protocols collapse the stack. UART has a physical layer "
      "(voltage levels, or RS-232/RS-485 transceivers) and a link layer "
      "(start bit, data bits, optional parity, stop bit) and nothing else - "
      "any message structure is left to software. I2C adds addressing and "
      "an ACK bit per byte. SPI does not even define a word length. The "
      "higher the speed and the longer the distance, the more layers you "
      "need.")

    h2("Controller, PHY and IP: who builds what")
    p("Almost every off-chip interface on an SoC is split into a "
      "**controller** (digital logic that implements the protocol layers) "
      "and a **PHY** (the circuits that touch the pins). Between them sits "
      "a standardized, or at least documented, **PHY interface**. Knowing "
      "these interfaces is what lets you mix vendors and reason about "
      "integration.")
    diagram([
        "   SoC fabric          Controller (digital, RTL)       PHY (mixed-signal)     pins",
        "  +----------+   AXI  +---------------------------+  +--------------------+",
        "  | CPU, DMA |<------>| CSRs | transaction | link |  | PCS | PMA  | PMD   |==> TX",
        "  |          |   APB  |      |   layer     | layer|<>|     | SERDES | drv |<== RX",
        "  +----------+  (cfg) +---------------------------+  +--------------------+",
        "                              PHY interface:  PIPE (PCIe, USB3, SATA, USB4)",
        "                                             UTMI+ / ULPI (USB 2.0)",
        "                                             DFI (DDR/LPDDR memory PHY)",
        "                                             MII/RMII/GMII/RGMII/SGMII/XGMII",
        "                                             PPI (MIPI D-PHY/C-PHY)",
        "                                             FDI/RDI (UCIe adapter <-> PHY)",
    ], "Figure 1.3 - The controller/PHY split and the standard interface at the "
       "boundary for each protocol family.")
    tbl(["Deliverable", "Controller IP", "PHY IP", "SoC integrator"],
        [["Design", "Synthesizable RTL (Verilog/SV), sometimes encrypted",
          "Hard macro: GDS, LEF, timing libs (.lib), IBIS/AMI models; plus "
          "RTL for the PCS/digital wrapper", "Glue logic, bridges, clock/"
          "reset, pad ring, interrupts"],
         ["Verification", "Testbench, VIP hooks, coverage, compliance "
          "test results", "SPICE/AMS verification, silicon test chips, "
          "characterization reports", "SoC-level tests with VIP and real "
          "firmware; emulation"],
         ["Physical", "Constraints (SDC), floorplan guidance", "Placement "
          "rules, bump map, power-grid and ESD guidance, package/board "
          "guidelines", "Floorplan, PD, SI/PI analysis of package and board"],
         ["Software", "Driver reference code, register descriptions",
          "PHY firmware (training, calibration, adaptation) and settings",
          "Boot firmware, OS drivers, bring-up scripts"],
         ["Certification", "Compliance-tested configurations",
          "Electrical compliance reports", "Product certification (USB-IF, "
          "PCI-SIG workshops, MIPI conformance, HDMI ATC)"]],
        widths=[1.0, 1.8, 2.0, 1.8], bold_first=True,
        caption="Table 1.6 - Who delivers what for a typical high-speed "
                "interface.")
    bul(["**Build vs buy.** Low-speed peripherals (UART, SPI, I2C, timers) are "
         "commonly built in-house or taken from a free/open library; APB/AHB/"
         "AXI fabric is generated by tools or licensed; high-speed "
         "controllers and almost all multi-gigabit PHYs are licensed, because "
         "PHY design needs analog expertise, silicon proof in the target "
         "process and a compliance history.",
         "**Analog vs digital ownership.** PLLs, drivers, receivers, "
         "equalizers and CDRs are designed by analog/mixed-signal engineers "
         "in schematic; RTL engineers own the controller and PCS; "
         "firmware engineers own link training sequences that run on a "
         "microcontroller inside many modern PHYs (DDR training is the "
         "classic example).",
         "**Configuration explosion.** Licensed IP is highly parameterized "
         "(lane count, data-path width, buffer sizes, optional features). "
         "Every parameter choice is a verification and compliance risk - "
         "choose the configuration early and freeze it."])
    box("warn", "PITFALL - the 'it is just integration' trap",
        "Teams often schedule a licensed PCIe or DDR subsystem as a quick "
        "integration task. In practice the PHY's clocking, reset sequencing, "
        "power domains, test modes (scan, BIST, loopback), firmware loading "
        "and package/board signal integrity dominate the schedule. Read the "
        "PHY integration guide before the floorplan is frozen, not after.")

    h2("Trade-offs: bandwidth, latency, pins and power")
    p("Protocol choice is an engineering trade. Table 1.7 gives typical "
      "orders of magnitude for the interfaces in this book; later chapters "
      "give the exact rates of each generation. Numbers are per link or "
      "per lane as stated and are typical, not limits.")
    tbl(["Interface", "Raw rate (typical)", "Pins / wires", "Latency scale",
         "Energy scale"],
        [["APB / AHB / AXI (on-chip)", "32-1024 b x 0.2-2 GHz; e.g. 128 b "
          "at 1 GHz = 16 GB/s per direction", "hundreds of on-chip wires",
          "1-10s of cycles", "lowest (short wires)"],
         ["UART", "9600 b/s to a few Mb/s (115200 common)", "2 (TX, RX) + "
          "optional RTS/CTS", "~10 bit times per byte", "negligible"],
         ["SPI / QSPI / Octal xSPI", "tens of MHz to ~200 MHz SCLK; octal "
          "DDR at 200 MHz = 400 MB/s", "4 to 11", "few clocks", "low"],
         ["I2C / I3C", "I2C 100 k/400 k/1 M/3.4 Mb/s; I3C SDR 12.5 MHz", "2",
          "tens of us per register access", "low; pull-ups burn static "
          "power when low"],
         ["CAN / CAN FD / CAN XL", "CAN up to 1 Mb/s; FD data phase "
          "typically 2-8 Mb/s; XL around 10-20 Mb/s", "2 (CANH/CANL)",
          "arbitration + frame time", "low"],
         ["USB 2.0 / 3.x / USB4", "480 Mb/s; 5/10/20 Gb/s; USB4 20/40 Gb/s, "
          "v2.0 up to 80 Gb/s", "2 (USB 2) to 4 pairs", "us-scale", "moderate"],
         ["PCIe Gen3/4/5/6", "8/16/32/64 GT/s per lane, x1-x16", "4 wires per "
          "lane", "~100s of ns per round trip", "few pJ/bit (typical SerDes)"],
         ["Ethernet", "10 Mb/s to 800 Gb/s", "1-8 lanes", "us-scale incl. "
          "MAC/PCS/FEC", "few pJ/bit"],
         ["DDR5 / LPDDR5", "DDR5 4800-6400+ MT/s x 64 b = 38-51+ GB/s per "
          "DIMM channel", "~100+ signals per channel", "tens of ns",
          "tens of pJ per bit incl. DRAM core (typical)"],
         ["HBM3", "6.4 Gb/s/pin x 1024 = ~819 GB/s per stack", "~1024 data "
          "bumps + CA", "tens of ns", "low pJ/bit I/O (short interposer "
          "wires)"],
         ["UCIe", "4-32 GT/s per lane (v1.x), 16-64 lanes per module",
          "bumps, not package balls", "few ns", "well below 1 pJ/bit "
          "(advanced package, typical)"],
         ["JTAG / SWD", "TCK/SWCLK up to tens of MHz", "4-5 / 2", "slow",
          "negligible"]],
        widths=[1.4, 2.4, 1.3, 1.1, 1.3], bold_first=True,
        caption="Table 1.7 - Orders of magnitude. Always check the exact "
                "generation and configuration in the relevant chapter.")
    p("Two formulas cover most first-order bandwidth estimates:")
    eq(["effective BW = lanes x rate_per_lane x coding_efficiency x "
        "protocol_efficiency",
        "",
        "PCIe Gen3 x4 : 4 x 8 GT/s x 128/130 = 31.5 Gb/s = 3.94 GB/s per "
        "direction (before TLP overhead)",
        "DDR5-6400    : 6400 MT/s x 64 bit / 8 = 51.2 GB/s peak per DIMM "
        "(2 x 32-bit subchannels)",
        "HBM3 stack   : 6.4 Gb/s x 1024 bit / 8 = 819.2 GB/s peak"],
        "Eq. 1.1 - Peak and effective bandwidth.")
    p("**Protocol efficiency** is where the surprises live: headers, CRCs, "
      "idles, flow-control packets, DRAM refresh, bank conflicts and "
      "read/write turnarounds routinely cost 10-40% of the raw rate. A PCIe "
      "memory write with a 256-byte payload carries roughly 20-30 bytes of "
      "framing, header, sequence number and CRC, so small payloads are "
      "dramatically less efficient than large ones (Chapter 18 does the "
      "arithmetic).")
    box("expert", "Interview insight: latency versus bandwidth",
        "Bandwidth can be bought with width or lanes; latency cannot. A "
        "serial link adds serializer, encoder, CDR, elastic buffer and "
        "deskew latency on top of the flight time - tens of nanoseconds even "
        "for a very short channel. That is why CPUs still use wide parallel "
        "on-chip fabrics and why die-to-die standards such as UCIe use a "
        "forwarded clock and simple coding: in-package they can afford many "
        "slower wires and want the latency of a wire, not of a network.")

    h2("Anatomy of one transaction: a CPU reads a sensor")
    p("To see how the layers and protocols cooperate, follow one register "
      "read of an I2C temperature sensor from software:")
    diagram([
        " CPU core     AXI fabric     AXI->APB     I2C controller       pads    sensor",
        "    | LDR x0,[I2C_DATA]                                                    ",
        "    |--AR---------->|                                                      ",
        "    |               |--PSEL/PENABLE->|                                     ",
        "    |               |                |--(earlier: SW wrote CMD register)   ",
        "    |               |                |   START|addr+W|ACK|reg|ACK|Sr|addr+R",
        "    |               |                |   |ACK|data|NACK|STOP  ~ 36 SCL clk ",
        "    |               |                |------------ SDA/SCL -------->|     ",
        "    |               |                |<----------- data byte -------|     ",
        "    |               |                |--IRQ (RX full) or poll STATUS      ",
        "    |               |<-PRDATA,PREADY-|                                     ",
        "    |<-R (RDATA)----|                                                      ",
    ], "Figure 1.4 - One register read of an I2C sensor crosses a memory-mapped "
       "on-chip bus, a bridge, a controller and an off-chip serial protocol.")
    bul(["Software sees a **memory-mapped** register. The AXI read (Chapter 7) "
         "takes a few fabric cycles; the AXI-to-APB bridge (Chapter 5) adds "
         "at least two APB cycles.",
         "The I2C controller turns register writes into a **framed serial "
         "transaction** (Chapter 13): START, 7-bit address plus W, register "
         "index, repeated START, address plus R, one data byte, NACK, STOP - "
         "four 9-bit slots, about 36 SCL cycles plus START/STOP overhead, "
         "roughly 90 us at 400 kHz.",
         "Because 90 us is an eternity for a CPU (about 180 000 cycles at "
         "2 GHz), the controller buffers data in a FIFO and signals "
         "completion by interrupt or DMA; software never stalls the bus "
         "waiting for the sensor. This **decoupling** of a fast memory-mapped "
         "side from a slow serial side is the central architecture pattern "
         "of every peripheral controller (Chapter 4 and Chapter 24).",
         "Errors at each layer are reported differently: a NACK from the "
         "sensor becomes a status bit and interrupt; a decode error in the "
         "fabric becomes an AXI SLVERR/DECERR response that may raise a "
         "CPU exception."])

    h2("Roadmap: from chapter to job role")
    p("The book is ordered from foundations to integration. Readers with a "
      "specific role can follow a shorter path:")
    tbl(["Role", "Core chapters", "Then", "Focus"],
        [["**RTL / IP designer**", "1-8, 11-13", "9, 10, 24", "FSMs, "
          "handshakes, CDC, bus slaves and masters, controller micro-"
          "architecture"],
         ["**SoC integration / fabric**", "1, 3, 5-10", "18, 20, 22, 24, 27",
          "Interconnect, bridges, ordering, deadlock, QoS, address maps"],
         ["**Design verification (DV)**", "1-4, 5-8", "25, and each "
          "protocol's verification section", "Assertions, VIP, scoreboards, "
          "coverage, compliance"],
         ["**PHY / analog / SI**", "2, 17-22", "26", "Signalling, equalization, "
          "jitter, eye and BER, PHY interfaces"],
         ["**Firmware / drivers / bring-up**", "1, 11-16", "17-21, 23",
          "Register models, link training, error handling, debug access"],
         ["**DFT / debug**", "1, 4, 23", "25", "JTAG, IEEE 1500/1687, "
          "CoreSight, SWD"],
         ["**Architect**", "1, 3, 9, 18, 20, 22", "26, 27", "Protocol "
          "selection, bandwidth/latency budgets, reliability, security"]],
        widths=[1.4, 1.0, 1.4, 2.4],
        caption="Table 1.8 - Suggested paths through the book.")
    checklist("Before you move on, you should be able to:", [
        "Place any protocol on the six axes of Section 1.3.",
        "Sketch the SoC map of Figure 1.1 from memory and name the PHY "
        "interface of PCIe, USB 2.0, DDR and Ethernet.",
        "Explain what the controller, the PHY and the integrator each deliver.",
        "Estimate peak bandwidth with Eq. 1.1 and name three sources of "
        "protocol inefficiency."])

    h2("Summary")
    bul(["A protocol is a contract covering signals, timing, framing, "
         "transactions, flow control, ordering, errors, power and discovery.",
         "Every SoC has the same structure: coherent core (CHI/ACE), system "
         "fabric (AXI), peripheral buses (AHB/APB), low-speed serial "
         "peripherals, high-speed controller+PHY pairs, memory interfaces "
         "and debug/test.",
         "Six axes classify links: on/off chip, parallel/serial, clocking, "
         "initiator model, and memory-mapped/streaming/packet style.",
         "High-speed stacks are layered (PMD/PMA, PCS, link, transaction, "
         "application) and the layers double as IP and team boundaries.",
         "Controllers are RTL, PHYs are mixed-signal hard macros joined by "
         "standard interfaces (PIPE, UTMI+, DFI, xMII, PPI, FDI/RDI).",
         "Bandwidth scales with width and lanes; latency and energy per bit "
         "decide many architectural choices."])
    h2("Exercises")
    bul(["Classify MIPI I3C, AXI4-Stream, CAN FD and HBM3 on all six axes of "
         "Section 1.3. Which classification was hardest, and why?",
         "Compute the peak per-direction bandwidth of PCIe Gen4 x8 "
         "(16 GT/s, 128b/130b) and of a 256-bit AXI bus at 1.2 GHz. How "
         "many such AXI ports does it take to keep the PCIe link busy in "
         "both directions?",
         "For the I2C read of Figure 1.4, count SCL cycles precisely "
         "(including ACK/NACK bits) and compute the transaction time at "
         "100 kHz, 400 kHz and 1 MHz. How many 2 GHz CPU cycles is each?",
         "List the deliverables you would request from a PHY vendor before "
         "the floorplan freeze, and explain which SoC team consumes each.",
         "Choose an interface for (a) a 12-bit ADC at 1 MS/s, (b) a "
         "4K60 camera, (c) a board-management power controller, (d) a "
         "second die in the same package. Justify each choice using "
         "Table 1.7."])


# ---------------------------------------------------------------- Ch 2 ----
def _ch2():
    chapter("Signalling Fundamentals: Single-Ended vs Differential, Clocking, "
            "Line Coding, SerDes, Jitter and Eyes")
    p("Before a protocol can define packets it must get individual bits "
      "across a wire. This chapter covers the physical and logical "
      "techniques every interface is built from: how a '1' and a '0' are "
      "represented electrically, how the receiver knows when to sample, how "
      "bit streams are coded so that clocks can be recovered and DC balance "
      "kept, how multi-gigabit SerDes transceivers are organized, and how "
      "link quality is measured with jitter, eye diagrams and bit error "
      "ratio. Three pieces of RTL are built and simulated: an 8b/10b "
      "encoder checked exhaustively against a Python reference, a Manchester "
      "encoder/decoder pair with clock recovery, and additive and "
      "self-synchronous scramblers.")

    h2("Single-ended signalling and CMOS logic levels")
    p("A **single-ended** signal is one wire referenced to ground. The "
      "driver pulls the line towards VDD for '1' and towards ground for '0'; "
      "the receiver compares the voltage against input thresholds. Four "
      "numbers define a logic family:")
    tbl(["Parameter", "Meaning"],
        [["V_{OH} (min)", "Lowest voltage a driver guarantees for a '1' at its "
          "rated current"],
         ["V_{OL} (max)", "Highest voltage a driver guarantees for a '0'"],
         ["V_{IH} (min)", "Lowest voltage a receiver guarantees to read as '1'"],
         ["V_{IL} (max)", "Highest voltage a receiver guarantees to read as '0'"]],
        widths=[1, 3])
    eq(["NM_H = V_OH - V_IH        NM_L = V_IL - V_OL"],
       "Eq. 2.1 - Noise margins: how much noise the wire may add before a "
       "receiver misreads a bit.")
    tbl(["Family (JEDEC-style)", "VDDIO", "V_{IH} min", "V_{IL} max", "Typical use"],
        [["LVTTL / LVCMOS 3.3 V", "3.3 V", "2.0 V", "0.8 V", "Legacy GPIO, "
          "UART/SPI/I2C on boards"],
         ["LVCMOS 2.5 V", "2.5 V", "1.7 V", "0.7 V", "Older FPGA banks, RGMII"],
         ["LVCMOS 1.8 V", "1.8 V", "0.65 x VDD", "0.35 x VDD", "Mobile GPIO, "
          "SPI flash, SD, eMMC"],
         ["LVCMOS 1.2 V", "1.2 V", "0.65 x VDD", "0.35 x VDD", "Low-voltage "
          "sensors, I3C at 1.2 V"]],
        widths=[1.5, 0.7, 0.9, 0.9, 2.0],
        caption="Table 2.1 - Common single-ended I/O standards (typical "
                "thresholds; always confirm in the device datasheet).")
    p("Single-ended signalling is cheap - one pin per bit - but it has three "
      "weaknesses that limit speed and distance: it shares a noisy ground "
      "reference between chips; many outputs switching together draw large "
      "currents through package inductance, creating **simultaneous "
      "switching output (SSO)** noise or ground bounce; and the full-swing "
      "signal radiates and couples into neighbours. Practical ceilings are "
      "in the low hundreds of Mb/s per pin on a board, which is why parallel "
      "single-ended buses (DDR, the old PCI) needed ever lower swings, "
      "on-die termination and training as speeds rose.")
    box("note", "What an I/O cell gives the RTL",
        "A general-purpose I/O pad has an output-data input, an output-enable, "
        "and an input-data output, plus static controls: drive strength, "
        "slew rate, pull-up/pull-down enable, Schmitt-trigger enable and "
        "input enable. The RTL controls only the digital triplet (Section "
        "4.5); the analog behaviour is set by the pad library and the pin-mux "
        "configuration.")

    h2("Open-drain outputs and pull-ups")
    p("An **open-drain** (open-collector in bipolar days) output can only "
      "pull the line **low**; to send a '1' it releases the line and an "
      "external **pull-up resistor** R_{p} charges the bus capacitance "
      "C_{b} towards VDD. Any device pulling low wins, which gives a "
      "**wired-AND**: the line is high only if every device releases it. "
      "I2C, SMBus, the I3C open-drain phase, 1-Wire, and interrupt or reset "
      "lines shared by several chips all rely on this property - for "
      "multi-controller arbitration, clock stretching and ACK bits.")
    diagram([
        "            VDD",
        "             |",
        "            [Rp]  pull-up resistor",
        "             |",
        "   bus  -----+-----------+-------------+           waveform on the bus:",
        "             |           |             |",
        "           [Cb]      +---+---+     +---+---+        ______        ______",
        "   (wiring + pins)   | NMOS  |     | NMOS  |      /       |      /",
        "             |       | dev A |     | dev B |     /  RC    | fast/",
        "            GND      +---+---+     +---+---+   _/  rise   |___/  ...",
        "                        GND           GND          (fall: NMOS pulls low)",
    ], "Figure 2.1 - Open-drain bus. Any device can pull low; the resistor "
       "and total capacitance set the slow rising edge.")
    p("The rising edge is a simple RC charge, so its 30%-70% rise time (the "
      "definition used by the I2C specification) is:")
    eq(["V(t) = VDD x (1 - exp(-t / (Rp x Cb)))",
        "t_r(30% -> 70%) = Rp x Cb x ln(0.7/0.3) = 0.8473 x Rp x Cb",
        "Rp_max = t_r(max) / (0.8473 x Cb)      Rp_min = (VDD - V_OL(max)) / I_OL"],
       "Eq. 2.2 - Pull-up sizing: too large and edges are too slow; too small "
       "and a driver cannot pull the line below V_OL.")
    _v("rise", "Python used to size I2C pull-ups for Standard-mode, Fast-mode "
       "and Fast-mode Plus (rise-time limits 1000/300/120 ns, sink current "
       "3 mA or 20 mA at V_OL = 0.4 V).")
    _o("rise", "Real output. With 400 pF (the Sm/Fm bus limit), Fast-mode "
       "needs a pull-up of at most ~885 ohm yet at least ~967 ohm at 3 mA: "
       "no solution - which is why heavily loaded buses use buffers, "
       "current-source pull-ups or Fm+ drivers.")
    box("warn", "PITFALL - open-drain design and integration bugs",
        ["Driving '1' actively on an open-drain line (a push-pull GPIO "
         "configured by mistake) creates contention with any device pulling "
         "low and defeats arbitration and clock stretching.",
         "Forgetting that the rise time, not the clock frequency, limits "
         "speed: a 400 kHz bus with long cables may need 100 kHz.",
         "Pull-ups to the wrong rail when devices sit in different voltage "
         "domains - use a level shifter designed for bidirectional "
         "open-drain lines.",
         "Static power: every time the line is held low, VDD/Rp flows - "
         "about 1 mA for 3.3 V and 3.3 kohm."])

    h2("Differential signalling: LVDS, CML and SLVS")
    p("A **differential** link sends the signal on two wires, P and N, "
      "driven in opposite directions; the receiver looks only at the "
      "difference V_{P} - V_{N}. Noise that couples equally onto both wires "
      "(**common-mode noise**) cancels, return current flows mostly in the "
      "pair itself, and the swing can be small - a few hundred millivolts - "
      "which reduces power and emissions and makes gigabit rates practical. "
      "Every high-speed serial protocol in this book is differential.")
    diagram([
        "   V_P  ---\\       /-----\\       /---      differential signal",
        "            \\     /       \\     /          Vdiff = V_P - V_N",
        "   V_CM - - -X - -X - - - - X - -X - - -    (swing +-Vod)",
        "            /     \\       /     \\         common mode",
        "   V_N  ---/       \\-----/       \\---      V_CM = (V_P + V_N) / 2",
        "",
        "   peak-to-peak differential swing = 2 x Vod",
    ], "Figure 2.2 - A differential pair and its common-mode level.")
    tbl(["Family", "Swing (typical)", "Common mode", "Termination", "Where used"],
        [["**LVDS** (TIA/EIA-644)", "|V_OD| ~350 mV (247-454 mV); "
          "~3.5 mA current loop", "~1.2 V",
          "100 ohm differential at RX", "Display (FPD-Link), older "
          "camera/ADC links, FPGA I/O, clock distribution"],
         ["**CML** (current-mode logic)", "~400-1000 mV p-p differential",
          "near VDD (resistive loads to VDD)", "50 ohm per leg to VDD "
          "(on-die)", "Multi-gigabit SerDes: PCIe, USB 3, Ethernet, SATA "
          "(inside PHYs)"],
         ["**SLVS** (e.g. SLVS-400)", "~200 mV", "~200 mV", "100 ohm "
          "differential", "MIPI D-PHY high-speed mode; low-power camera and "
          "display links"],
         ["**Sub-LVDS / scalable LVDS**", "~150 mV", "~0.9 V", "100 ohm",
          "Image sensors, low-power FPGA links"]],
        widths=[1.3, 1.7, 1.1, 1.2, 2.0], bold_first=False,
        caption="Table 2.2 - Differential signalling families (values "
                "typical; standards define min/max ranges).")
    p("High-speed SerDes transmitters are almost always **CML-style current "
      "steering** drivers or, increasingly at low supply voltages, "
      "voltage-mode (SST) drivers; both present a matched 50 ohm source per "
      "leg. AC coupling capacitors in series with each wire (required by "
      "PCIe and USB 3) block DC, so the two chips can use different "
      "common-mode levels - and so the data stream must itself be "
      "**DC-balanced**, which is the job of line coding and scrambling.")

    h2("Termination and reflections")
    p("A board trace is a **transmission line** with characteristic "
      "impedance Z_{0} (typically 50 ohm single-ended, 85-100 ohm "
      "differential). When a signal edge meets an impedance change, part of "
      "it reflects:")
    eq(["Gamma = (Z_L - Z_0) / (Z_L + Z_0)",
        "open end (Z_L = inf): Gamma = +1     short: Gamma = -1     matched: "
        "Gamma = 0",
        "treat as a transmission line when  edge time  <  ~2 x round-trip "
        "flight time"],
       "Eq. 2.3 - Reflection coefficient. Propagation on FR-4 is roughly "
       "6-7 ps/mm (about 15-17 cm per ns).")
    tbl(["Scheme", "How", "Pros / cons", "Examples"],
        [["Series (source)", "R at the driver so R_drv + R_s = Z_0",
          "No DC power; only for point-to-point, receiver at the end",
          "LVCMOS clocks, SPI SCLK on long traces"],
         ["Parallel (end)", "R = Z_0 to ground or VTT at the receiver",
          "Clean edges; burns DC power", "Old DDR (SSTL to VTT)"],
         ["On-die termination (ODT)", "Switchable R inside the receiver, "
          "enabled only when receiving", "No board parts, dynamic; needs "
          "calibration (ZQ)", "DDR3/4/5, LPDDR, GDDR"],
         ["Differential 100 ohm", "R across P/N at RX (on-die in SerDes)",
          "Matched pair; low power for current-mode drivers", "LVDS, PCIe, "
          "USB, MIPI HS"]],
        widths=[1.1, 1.8, 2.0, 1.5],
        caption="Table 2.3 - Termination schemes.")
    box("tip", "What the digital designer must know",
        "You rarely compute reflections yourself - SI engineers do that with "
        "IBIS/IBIS-AMI models and channel simulations - but you configure "
        "ODT values, drive strengths and slew settings through PHY registers, "
        "and you own the firmware that calibrates them (ZQ calibration, "
        "impedance trim). Wrong settings produce 'software' bugs that are "
        "really signal integrity.")

    h2("Clocking schemes: how the receiver knows when to sample")
    p("Every receiver must sample each bit inside its **valid window**. The "
      "clocking scheme decides where the sampling clock comes from, and it "
      "is the single most important property of an interface's timing.")
    h3("Common-clock (system-synchronous)")
    p("Both chips receive the same clock from a board oscillator; data "
      "launched on one edge is captured on the next edge at the other chip. "
      "Classic PCI and early SDRAM worked this way. The whole round of "
      "delays must fit into one period, so frequency tops out quickly:")
    eq(["T_clk >= t_co + t_flight + t_su + t_skew(clock) + t_jitter",
        "t_hold <= t_co(min) + t_flight(min) - t_skew(clock)"],
       "Eq. 2.4 - Common-clock timing budget. Flight time and clock skew "
       "count against every cycle.")
    h3("Source-synchronous and double data rate")
    p("The transmitter sends a **strobe or clock alongside the data**, "
      "routed with matched length, so both experience the same flight "
      "delay and it cancels out of the budget. DDR SDRAM's DQS strobe, "
      "RGMII's TXC/RXC and the MIPI D-PHY clock lane are examples. Most such "
      "interfaces use **DDR** (double data rate): data changes on both "
      "edges, doubling throughput for the same clock frequency. The "
      "strobe is edge-aligned with data on DDR reads (the controller delays "
      "it by ~90 degrees internally) and centre-aligned on DDR writes.")
    diagram([
        '                 _____     _____     _____     _____     _____',
        '  DQS       _____|    |____|    |____|    |____|    |____|    |',
        '  DQ (DDR)       X D0 X D1 X D2 X D3 X D4 X D5 X D6 X D7 X D8 X D9',
        '                 ^    ^    ^    ^    ^    ^    ^    ^    ^    ^   both edges',
        "",
        "   write (centre-aligned):  strobe edge in the middle of each data eye",
        "   read  (edge-aligned)  :  RX delays DQS by ~1/4 period to centre it",
    ], "Figure 2.3 - Source-synchronous DDR: a strobe travels with the data.")
    h3("Forwarded clock")
    p("A forwarded-clock link sends a **clock lane** with a group of data "
      "lanes (HDMI TMDS up to HDMI 2.0, MIPI D-PHY, UCIe, HBM). The receiver "
      "still needs per-lane deskew (training) at high rates, but it avoids a "
      "full CDR per lane - lower power and latency, ideal for short, "
      "matched channels such as in-package die-to-die links.")
    h3("Embedded clock and clock-data recovery (CDR)")
    p("Long-reach and high-rate serial links send **no clock at all**. The "
      "receiver's CDR locks a local oscillator to the **transitions in the "
      "data**, and places the sampling point in the centre of each bit. "
      "This removes skew between lanes from the timing budget entirely - "
      "each lane tracks its own phase - at the price of requiring enough "
      "transitions (coding or scrambling), a lock time, and elastic buffers "
      "to absorb the small frequency difference between the two ends' "
      "reference clocks (for example up to +-300 ppm in PCIe, which "
      "inserts and deletes SKP ordered sets to compensate).")
    tbl(["Scheme", "Clock source at RX", "Rate limit set by", "Examples"],
        [["Common clock", "Shared board clock", "Flight time + skew in "
          "one period", "PCI, early SDRAM, simple SPI at low speed"],
         ["Source-synchronous", "Strobe/clock sent with data", "Skew "
          "within the group, duty-cycle distortion", "DDR DQS, RGMII, SPI "
          "flash (DQS in Octal DDR), ONFI"],
         ["Forwarded clock", "Dedicated clock lane", "Lane-to-lane skew "
          "(trained), jitter tracking", "D-PHY, HDMI (TMDS), UCIe, HBM"],
         ["Embedded clock + CDR", "Recovered from data transitions", "Channel "
          "loss and jitter; CDR bandwidth", "PCIe, USB 3, SATA, Ethernet "
          "SerDes, DisplayPort, C-PHY"],
         ["Asynchronous oversampled", "Local clock, resync per frame", "Clock "
          "tolerance x frame length", "UART, CAN (with resynchronization)"]],
        widths=[1.2, 1.4, 1.7, 2.1],
        caption="Table 2.4 - Clocking schemes compared.")

    h2("Line coding")
    p("A **line code** maps data bits to the symbols actually sent. It "
      "exists to satisfy the channel and the receiver: enough transitions "
      "for clock recovery (**transition density**), a bounded run of equal "
      "symbols (**run length**), zero average (**DC balance**) for AC-coupled "
      "links, special symbols for **framing and alignment**, and sometimes "
      "error detection. Every property costs bandwidth, measured as "
      "**coding efficiency**.")
    diagram([
        "  data bits      1     0     1     1     0     0     0     1",
        "               ______      ____________                  ______",
        "  NRZ                |_____|           |_________________|        level = bit",
        "                     __________________      ______",
        "  NRZI (USB2)  ______|                 |_____|     |___________   0 = toggle",
        "                  ______      ___   ______   ___   ___      ___",
        "  Manchester   ___|     |_____|  |__|     |__|  |__|  |_____|     1 = low->high",
        "",
        "  Manchester has a transition in the middle of every bit: the clock is always there.",
    ], "Figure 2.4 - NRZ, NRZI (USB 2.0 convention: a '0' toggles the line) "
       "and Manchester for the same bits.")
    tbl(["Code", "Efficiency", "DC balance / run length", "Used by"],
        [["NRZ", "100%", "None; unbounded runs", "On-chip, UART, SPI; "
          "high-speed links only together with scrambling"],
         ["NRZI + bit stuffing", "~ 100% minus stuffing (worst case 1 bit "
          "in 7)", "Stuff a 0 after six 1s", "USB 2.0 (bit stuffing), "
          "HDLC-style framing"],
         ["Manchester", "50% (2 baud per bit)", "Perfect DC balance, a "
          "transition every bit", "10BASE-T Ethernet, many RFID/IR links, "
          "DALI"],
         ["8b/10b", "80%", "Running disparity bounds DC; max run 5",
          "PCIe Gen1/2, USB 3.x Gen1, SATA, 1000BASE-X, DisplayPort 1.x, "
          "JESD204B"],
         ["64b/66b", "96.97%", "Scrambled payload + 2-bit sync header",
          "10G/25G/100G Ethernet PCS, JESD204C, Interlaken"],
         ["128b/130b", "98.46%", "Scrambled + 2-bit sync header", "PCIe "
          "Gen3/4/5"],
         ["128b/132b", "96.97%", "Scrambled + 4-bit header", "USB 3.2 Gen 2, "
          "DisplayPort 2.x"],
         ["PAM4 (+ FEC)", "2 bits per symbol", "Gray-coded 4 levels; "
          "precoding options", "PCIe Gen6 (FLIT mode), 200G/400G/800G "
          "Ethernet, 112G SerDes"]],
        widths=[1.1, 1.2, 1.9, 2.4],
        caption="Table 2.5 - Line codes. Efficiency is payload bits / line "
                "bits.")
    h3("8b/10b in detail")
    p("IBM's 8b/10b code (Widmer and Franaszek, 1983) splits each byte "
      "`HGF EDCBA` into a 5-bit part `EDCBA` (value x) and a 3-bit part "
      "`HGF` (value y), written **D.x.y** for data and **K.x.y** for "
      "control characters. The 5-bit part becomes six bits `abcdei` and the "
      "3-bit part four bits `fghj`; bit `a` is transmitted first. Each "
      "sub-block has either equal numbers of ones and zeros (**disparity** "
      "0) or a disparity of +-2. The encoder tracks the **running "
      "disparity** (RD): when RD is negative it chooses the variant with "
      "more ones, when positive the one with more zeros, so the line never "
      "drifts more than a few bits away from DC balance.")
    diagram([
        "  byte:   H G F   E D C B A          10-bit code (a sent first)",
        "          \\___/   \\_______/          a b c d e i   f g h j",
        "            y         x       ->     \\_________/   \\_____/",
        "           3b/4b     5b/6b             6b block    4b block",
        "",
        "  RD-  ->  pick the variant with more 1s ;  RD+ -> the one with more 0s",
        "  disparity +-2 sub-blocks flip RD; balanced 111000/000111, 1100/0011 alternate",
        "",
        "  K28.5 (RD-) = 001111 1010    comma 0011111 : cannot appear in data",
        "  K28.5 (RD+) = 110000 0101    comma 1100000 : RX aligns symbols on it",
    ], "Figure 2.5 - 8b/10b structure, running disparity and the K28.5 comma.")
    p("Three special cases trip up every first implementation: the "
      "alternate encoding **D.x.A7** (`0111`/`1000` instead of `1110`/`0001`) "
      "for x = 17, 18, 20 with RD- and x = 11, 13, 14 with RD+, which "
      "prevents a run of five equal bits across the `i`/`f` boundary; the "
      "balanced sub-blocks `111000`/`000111` and `1100`/`0011`, which "
      "alternate with RD even though they do not change it; and the "
      "K-character 4-bit codes, whose RD+ forms are complements even when "
      "balanced. The encoder below stores only the RD- table and derives "
      "RD+ codes by complementing.")
    _v("enc8b10b", "8b/10b encoder: 5b/6b and 3b/4b tables, running "
       "disparity, D.x.A7 and K characters (K28.0-K28.7, K23.7, K27.7, "
       "K29.7, K30.7).")
    p("The reference model is written differently on purpose - as the two "
      "published tables, RD- and RD+ columns typed separately - so that a "
      "misunderstanding cannot be copied into both. It produces a hex file "
      "of 536 golden vectors ({code, RD_out} for every D and K character "
      "from both starting disparities).")
    _v("ref8b10b", "Independent Python reference (ref8b10b.py) that writes "
       "golden_8b10b.hex.")
    _o("py8b10b", "Real Python output (code shown as abcdei fghj; RD- and "
       "RD+ variants).")
    _v("tb_8b10b", "Testbench: exhaustive table comparison, famous "
       "characters, and a one-million-bit random stream with a 1-in-16 "
       "chance of a K character.")
    _o("8b10b", "Real Icarus Verilog output: all 536 codes match Python; the "
       "stream never exceeds a run of 5 and the running digital sum stays "
       "within a band of 6.")
    box("intuit", "Why the comma matters",
        "A receiver that has just locked its CDR sees an endless bit stream "
        "with no idea where 10-bit symbols start. The **comma** sequences "
        "0011111 and 1100000 occur only inside K28.1, K28.5 and K28.7 and "
        "never across data character boundaries, so the PCS slides its "
        "symbol boundary until a comma lands in the right place (comma "
        "alignment). PCIe Gen1/2 uses K28.5 as COM at the start of every "
        "ordered set for exactly this reason.")
    h3("64b/66b and 128b/130b: block codes with sync headers")
    p("8b/10b's 25% overhead is too costly above ~5 Gb/s. Newer codes "
      "scramble the payload for transitions and DC balance and add only a "
      "short **sync header** per block. 64b/66b (10GBASE-R) prefixes each "
      "64-bit block with `01` (data) or `10` (control); `00` and `11` are "
      "invalid, so the header always contains a transition and the "
      "receiver finds block boundaries by hunting for a position where "
      "headers are consistently valid. PCIe Gen3-5's 128b/130b uses the same "
      "idea with a 2-bit header per 128-bit block (`10` = data, `01` = "
      "ordered set). DC balance is only statistical, so the scrambler is "
      "mandatory.")
    diagram([
        "  64b/66b block:   | 2-bit sync | 64 bits scrambled payload (x^58+x^39+1) |",
        "                     01 = data   10 = control   00/11 = invalid",
        "  128b/130b block: | 2-bit sync | 16 bytes scrambled payload          |",
        "                     10 = data   01 = ordered set     (PCIe Gen3-Gen5)",
    ], "Figure 2.6 - Block codes with sync headers.")
    h3("PAM4")
    p("NRZ sends one bit per symbol (two levels). **PAM4** sends two bits per "
      "symbol using four levels, halving the symbol rate for the same bit "
      "rate and therefore the channel loss at Nyquist. The price: three "
      "stacked eyes, each about a third of the NRZ eye height (roughly a "
      "9.5 dB SNR penalty), more sensitivity to non-linearity, and a raw "
      "bit error ratio that requires **forward error correction**. PCIe 6.0 "
      "(64 GT/s) pairs PAM4 with fixed-size FLITs and a lightweight FEC plus "
      "CRC; 400G/800G Ethernet uses RS(544,514) FEC. Gray coding (levels "
      "00, 01, 11, 10) makes a one-level slip cost only one bit.")
    h3("Manchester coding with clock recovery - run example")
    p("Manchester coding guarantees a transition in the middle of every "
      "bit, so the receiver can recover the clock with simple logic. The "
      "IEEE 802.3 convention is '1' = low-to-high and '0' = high-to-low at "
      "mid-bit. The decoder below oversamples with its own, unrelated "
      "clock at 8 samples per bit. It locks on the first edge (a preamble "
      "of 1010... contains only mid-bit edges), then ignores any edge "
      "during the first three quarters of a bit - those are bit-boundary "
      "edges - and re-times itself on each mid-bit edge. That re-timing is "
      "a tiny digital CDR.")
    _v("manch", "Manchester encoder (one half-bit per clock) and "
       "oversampling decoder with edge-based clock recovery.")
    _o("manch", "Real Icarus output: 2 000 random bits after an 8-bit "
       "preamble at 12.5 Mb/s, for different receiver clock errors (TB "
       "tb_manch.sv, +OFS plusarg).")
    p("Because the decoder re-times on every bit, it tolerates enormous "
      "clock errors - +-20% is error-free - compared with UART, which must "
      "survive a whole frame without resynchronization (Section 4.3). At "
      "+30% the ignore window becomes too short relative to the slower "
      "incoming bits and boundary edges start to be accepted as data; at "
      "-30% the decoder loses bits. The cost of this robustness is the 2x "
      "bandwidth of Manchester coding.")

    h2("Scrambling")
    p("A **scrambler** XORs the data with a pseudo-random sequence from a "
      "linear-feedback shift register (LFSR). It does not add bits, yet it "
      "makes long runs and repetitive patterns statistically rare, spreads "
      "the spectrum (lower EMI peaks) and gives the CDR transitions. Two "
      "architectures exist, with opposite trade-offs.")
    diagram([
        "  ADDITIVE (synchronous)                 SELF-SYNCHRONOUS (multiplicative)",
        "  +--------------+                       d --(+)------------+-----> line",
        "  | LFSR (seed)  |--k--+                      ^             |",
        "  +--------------+     |                      |  +----------v---------+",
        "  d ------------------(+)---> line            +--| shift reg of LINE  |",
        "  line ---------------(+)---> d               |  | bits, taps 39, 58  |",
        "   (RX has an identical LFSR, reset at        |  +--------------------+",
        "    the same symbol, e.g. PCIe COM)          RX: d = line ^ taps(line)",
    ], "Figure 2.7 - Additive scrambling needs synchronized LFSRs; "
       "self-synchronous scrambling feeds back the line bits themselves.")
    tbl(["", "Additive (synchronous)", "Self-synchronous"],
        [["Keystream", "Independent LFSR", "Function of previous line bits"],
         ["Synchronization", "Both LFSRs must be reset together (explicit "
          "sync symbol or ordered set)", "Automatic after N bits (N = LFSR "
          "length)"],
         ["Error propagation", "None: 1 line error -> 1 data error", "1 line "
          "error -> one error per polynomial term (3 for x^58+x^39+1)"],
         ["Examples", "PCIe Gen1/2 and USB 3 Gen1 (X^16+X^5+X^4+X^3+1), PCIe "
          "Gen3+ (23-bit LFSR per lane), DisplayPort", "64b/66b Ethernet "
          "(x^58+x^39+1), SONET/SDH payloads, JESD204C"]],
        widths=[1.1, 2.3, 2.3], bold_first=True,
        caption="Table 2.6 - Scrambler architectures.")
    p("The RTL below implements both. The additive scrambler is written "
      "byte-parallel: a loop of eight serial LFSR steps inside one "
      "combinational block, which synthesis flattens into an XOR network - "
      "the same unrolling technique used for parallel CRCs in Chapter 3. "
      "Its keystream is checked against a Python model of the same "
      "polynomial, seed `FFFF`, LSB first.")
    _v("scram", "Byte-parallel additive scrambler (PCIe Gen1/2 / USB 3 Gen1 "
       "polynomial) and a bit-serial self-synchronous x^58+x^39+1 "
       "scrambler/descrambler.")
    _v("ref_scr", "Python reference for the additive scrambler.")
    _o("pyscr", "Real Python output: keystream (scrambling sixteen 0x00 "
       "bytes) and a scrambled ASCII string.")
    _o("scram", "Real Icarus output from tb_scram.sv: RTL keystream equals "
       "Python for 64 bytes; error propagation of both architectures.")
    p("The keystream `FF 17 C0 14 B2 E7 02 82 ...` is also the well-known "
      "start of the Gen1 scrambling sequence that appears in PCIe and USB 3 "
      "debug traces - useful to recognize on a protocol analyzer. The "
      "self-synchronous pair demonstrates both of its properties: the "
      "descrambler started in the wrong state and still produced correct "
      "data after at most 58 bits (19 wrong bits here), and one flipped line "
      "bit produced exactly three data errors.")
    box("warn", "PITFALL - scrambler bugs that pass simple tests",
        ["Scrambling and descrambling with the same wrong polynomial or bit "
         "order still round-trips perfectly in a loopback test. Always "
         "compare against the specification's published sequence or an "
         "independent model, as done here.",
         "Additive scramblers must skip or reset on exactly the symbols the "
         "spec says (PCIe Gen1/2 does not advance on SKP symbols and resets "
         "on COM). An off-by-one here corrupts every byte after the first "
         "SKP ordered set.",
         "Bit order: most serial specs send LSB first; parallel data paths "
         "in your RTL may be MSB-first. Document the convention in the "
         "module header."])

    h2("SerDes architecture")
    p("A **SerDes** (serializer/deserializer) transceiver is the PHY of every "
      "multi-gigabit link. Figure 2.8 shows its blocks; the PCS portion is "
      "RTL, the rest is analog/mixed-signal.")
    diagram([
        "  TX                                                                 channel",
        "  data -> [PCS: encode 8b10b/128b130b, scramble] -> [serializer N:1] -> [FFE] -> [driver]=>",
        "                                                        ^",
        "                                               [TX PLL: ref clk x M]",
        "",
        "  RX",
        "  =>[term]-[CTLE]-[VGA]-(+)-[slicer]-+-> [deserializer 1:N] -> [PCS] -> data",
        "                         ^           |      ^                 block/comma align",
        "                         +--[DFE taps]<-+    |                 descramble, decode",
        "                                        |    |                 elastic buffer",
        "                                   [CDR: phase detector + loop filter]  lane deskew",
        "                                        (recovered clock)",
    ], "Figure 2.8 - SerDes transceiver. FFE = feed-forward equalizer (TX "
       "de-emphasis/pre-shoot), CTLE = continuous-time linear equalizer, "
       "DFE = decision-feedback equalizer, CDR = clock-data recovery.")
    tbl(["Block", "Function", "Owner"],
        [["**PLL**", "Multiplies a clean reference (e.g. 100 MHz for PCIe) to "
          "the bit-rate clock (often half or quarter rate with multi-phase "
          "outputs)", "Analog"],
         ["**Serializer**", "Parallel-to-serial conversion (e.g. 32:1) in a "
          "tree of multiplexers", "Analog/custom digital"],
         ["**TX FFE**", "A short FIR filter (pre-cursor, main, post-cursor "
          "taps) that pre-distorts the signal to cancel channel low-pass "
          "loss - PCIe presets and de-emphasis", "Analog, coefficients set by "
          "link training"],
         ["**RX CTLE**", "Analog high-pass peaking filter that boosts high "
          "frequencies attenuated by the channel", "Analog, adaptive"],
         ["**RX DFE**", "Subtracts the ISI of previous decided bits (post-"
          "cursor taps); does not amplify noise, unlike a linear equalizer",
          "Mixed-signal, adaptive"],
         ["**CDR**", "Phase detector (e.g. bang-bang/Alexander) plus loop "
          "filter steering a phase interpolator or VCO to the eye centre",
          "Mixed-signal"],
         ["**Deserializer**", "Serial-to-parallel conversion, producing the "
          "PCS-side word clock", "Custom digital"],
         ["**PCS**", "Encoding/decoding, scrambling, block/comma alignment, "
          "elastic buffer (clock compensation), lane-to-lane deskew, PRBS "
          "generators/checkers, loopback", "RTL"]],
        widths=[1.0, 3.8, 1.2], bold_first=False,
        caption="Table 2.7 - SerDes building blocks.")
    p("Modern links **train** their equalizers at start-up: in PCIe Gen3+ "
      "the two ends negotiate TX FFE presets and coefficients during the "
      "Recovery.Equalization phase of the LTSSM, while each receiver adapts "
      "its CTLE and DFE. The controller RTL drives this process through the "
      "PIPE interface; the adaptation algorithms live inside the PHY, often "
      "in firmware.")

    h2("Jitter, eye diagrams and bit error ratio")
    p("**Jitter** is the deviation of signal edges from their ideal "
      "positions in time. It is decomposed because different components "
      "add differently:")
    tbl(["Component", "Cause", "Distribution"],
        [["Random jitter (RJ)", "Thermal and device noise in PLLs, drivers, "
          "receivers", "Gaussian, unbounded; specified as RMS sigma"],
         ["Data-dependent jitter (DDJ/ISI)", "Channel loss and reflections: "
          "an edge's timing depends on previous bits", "Bounded; reduced by "
          "equalization"],
         ["Duty-cycle distortion (DCD)", "Unequal rise/fall or clock duty "
          "cycle", "Bounded, two values"],
         ["Periodic jitter (PJ)", "Coupling from supplies, spread-spectrum "
          "clocking, crosstalk at fixed frequencies", "Bounded, sinusoidal"],
         ["Bounded uncorrelated (BUJ)", "Crosstalk from other lanes",
          "Bounded"]],
        widths=[1.5, 2.8, 1.8],
        caption="Table 2.8 - Jitter components. DJ = all bounded parts.")
    p("Overlaying many bit periods of the received waveform on an "
      "oscilloscope gives the **eye diagram**. The open area in the middle "
      "is where the receiver can sample safely; its height is the voltage "
      "margin and its width the timing margin.")
    diagram([
        "        ____________          ____________",
        "       /            \\        /            \\",
        "  ____/   +------+   \\______/   +------+   \\____     eye height:",
        "      \\   | mask |   /      \\   | mask |   /         vertical opening",
        "       \\  +------+  /        \\  +------+  /",
        "  ______\\__________/__________\\__________/______     eye width:",
        "        ^<-- UI -->^                                horizontal opening",
        "     crossing   crossing  (jitter smears the crossings horizontally)",
    ], "Figure 2.9 - Eye diagram with a compliance mask. One unit interval "
       "(UI) = one bit time.")
    p("Because random jitter is Gaussian, the eye keeps closing slowly as "
      "you look for rarer events. Total jitter is therefore quoted **at a "
      "bit error ratio**, typically 10^{-12}:")
    eq(["TJ(BER) = DJ(dual-Dirac) + 2 x Q(BER) x RJ_rms",
        "Q(1e-12) = 7.03  ->  TJ(1e-12) = DJ + 14.07 x RJ_rms",
        "bits needed to claim BER < 1e-12 with 95% confidence and 0 errors "
        "~ 3 / 1e-12 = 3e12"],
       "Eq. 2.5 - The dual-Dirac jitter model and BER test length. At "
       "10 Gb/s, 3e12 bits take 5 minutes.")
    diagram([
        "  log10(BER)",
        "     0 |*                                                   *",
        "    -3 | *                                                 *",
        "    -6 |   *                                             *",
        "    -9 |     *                                         *",
        "   -12 |       *  <-------- eye opening at 1e-12 -->  *",
        "   -15 |         *                                  *",
        "       +---------------------------------------------------> sample phase",
        "        0                     0.5 UI                   1 UI",
    ], "Figure 2.10 - Bathtub curve: BER versus sampling phase. The walls are "
       "the tails of the jitter distributions; the flat floor is where the "
       "CDR should sample.")
    box("expert", "Interview insight: BER is a system number",
        "A 'BER of 1e-12' at 32 GT/s means an error every ~31 seconds per "
        "lane - about one every two seconds on an x16 link. That is why "
        "every high-speed protocol pairs its PHY with link-level CRC and "
        "retry (Chapter 3) and, at PAM4 rates, FEC: the PHY makes errors "
        "rare, the link layer makes them invisible.")

    h2("Summary")
    bul(["Single-ended CMOS signalling is simple but limited by shared "
         "ground, SSO noise and full swing; noise margins come from "
         "V_OH/V_IH and V_IL/V_OL.",
         "Open-drain buses give wired-AND behaviour; the RC pull-up sets the "
         "rise time (t_r = 0.8473 RpCb for 30-70%) and bounds the bus "
         "capacitance and speed.",
         "Differential signalling (LVDS, CML, SLVS) rejects common-mode "
         "noise and enables small swings and gigabit rates; termination "
         "matches the line to suppress reflections.",
         "Clocking scheme - common, source-synchronous, forwarded, or "
         "embedded with CDR - determines an interface's timing budget.",
         "Line codes (NRZI, Manchester, 8b/10b, 64b/66b, 128b/130b, PAM4) "
         "trade efficiency for transitions, DC balance and framing; the "
         "8b/10b RTL matched an independent Python model on all 536 codes.",
         "Scramblers are additive (need sync, no error spread) or "
         "self-synchronous (auto-sync, error multiplication).",
         "SerDes = PLL, serializer, FFE, driver, CTLE, DFE, CDR, deserializer "
         "and PCS; equalizers are trained at link start-up.",
         "Jitter (RJ + DJ) closes the eye; TJ and BER must be quoted "
         "together, and link-layer CRC/retry handles the residual errors."])
    h2("Exercises")
    bul(["A 1.8 V I2C bus has 250 pF of capacitance and must meet the "
         "Fast-mode 300 ns rise time. Compute Rp_max and Rp_min for a 3 mA "
         "sink at V_OL = 0.4 V. Is there a valid resistor?",
         "Encode the bytes 0x00, 0xBC (as K28.5) and 0xF1 starting from "
         "RD-, by hand, using Figure 2.5 and the tables in the encoder. "
         "Check your answer with ref8b10b.py.",
         "Write the matching 8b/10b decoder with code-violation and "
         "disparity-error outputs. Close the loop with enc8b10b and inject "
         "single-bit errors: what fraction are detected?",
         "Modify manch_rx to use 4 samples per bit. Measure the new "
         "clock-error tolerance with the +OFS plusarg and explain the "
         "result.",
         "Show that a single line-bit error through the self-synchronous "
         "x^58+x^39+1 descrambler produces errors at offsets 0, 39 and 58. "
         "Why does 64b/66b not need to reset its scrambler, while PCIe Gen1 "
         "does?",
         "Using Eq. 2.5, a link has DJ = 0.15 UI and RJ = 0.02 UI RMS. What "
         "is the eye opening at BER 1e-12 and at 1e-15?"])


# ---------------------------------------------------------------- Ch 3 ----
def _ch3():
    chapter("Handshakes, Flow Control, Ordering and Error Detection")
    p("Chapter 2 moved individual bits. This chapter is about **agreement**: "
      "how two sides agree that a transfer happened (handshakes), how a "
      "sender avoids overrunning a receiver (flow control), what order "
      "operations take effect in (ordering), how a system avoids "
      "waiting forever (deadlock), and how corrupted data is detected and "
      "repaired (parity, checksums, CRC, ECC and retry). These mechanisms "
      "recur in every protocol from APB to PCIe; learn them once here. The "
      "run examples are a credit-based link, bit-serial and byte-parallel "
      "CRC generators checked against Python's `zlib.crc32`, and a (72,64) "
      "SECDED encoder/decoder with error injection.")

    h2("The valid/ready handshake")
    p("The most common on-chip handshake is **valid/ready** (AXI's "
      "VALID/READY, AXI4-Stream's TVALID/TREADY, and countless internal "
      "pipelines). The source drives `valid` with the payload; the "
      "destination drives `ready`. A transfer happens on **every clock edge "
      "where both are high** - no more, no less.")
    diagram([
        '            ___   ___   ___   ___   ___   ___   ___   ___',
        '  clk          |__|  |__|  |__|  |__|  |__|  |__|  |__|  |__',
        '                  ______________________________',
        '  valid     ______|                             |___________',
        '            ______            ______________________________',
        '  ready           |___________|',
        '  data      ------< A  >< A  >< A  >< B  >< C  >------------',
        '                   wait  wait  X A   X B   X C    (X = transfer at the next edge)',
        "",
        "  rule 1: a transfer occurs on each edge with valid && ready",
        "  rule 2: once valid is high, it and data stay stable until the transfer",
        "  rule 3: valid must not depend combinationally on ready (no waiting for ready)",
        "  rule 4: ready may depend on valid, may be high before valid, may drop freely",
    ], "Figure 3.1 - Valid/ready: the source holds A through two stalled "
       "cycles; B and C then transfer back to back.")
    tbl(["valid", "ready", "Meaning"],
        [["0", "0", "Idle"],
         ["0", "1", "Destination can accept; nothing offered (allowed)"],
         ["1", "0", "Offer pending, destination stalls - source must hold "
          "valid and data"],
         ["1", "1", "Transfer on this edge; source may present the next item "
          "in the next cycle"]],
        widths=[0.6, 0.6, 4])
    box("warn", "PITFALL - the four classic valid/ready bugs",
        ["**Waiting for ready before raising valid.** If both sides wait for "
         "the other, the system deadlocks. AXI explicitly forbids the source "
         "from waiting; the destination may wait.",
         "**Retracting valid** (or changing data) before the transfer - "
         "e.g. an arbiter that switches to another requester while the "
         "current one is stalled. Chapter 4's checker (rule R5) and the SVA "
         "`a_hold` catch exactly this.",
         "**Combinational loop:** ready computed from valid on one side and "
         "valid from ready on the other.",
         "**Counting a transfer on valid alone** in a monitor or scoreboard, "
         "which double-counts stalled items."])
    h3("Pipelining ready: skid buffers")
    p("In a long pipeline, `ready` becomes a long combinational path "
      "running backwards through every stage. Registering it breaks the "
      "path but introduces a one-cycle lag: when the downstream stage drops "
      "ready, the upstream stage does not see it until the next cycle and "
      "sends one more item. A **skid buffer** is a two-entry buffer that "
      "absorbs that extra item so no data is lost and full throughput is "
      "kept. The companion RTL Design guide builds one; here the key "
      "protocol insight is the general rule: **a stage whose ready is "
      "registered needs as many spare entries as the number of cycles "
      "between the stall and the sender seeing it.** Credit-based flow "
      "control, below, is the same rule scaled up to a long link.")

    h2("Request/acknowledge: 2-phase and 4-phase handshakes")
    p("When there is no common clock - between clock domains, or in "
      "asynchronous logic - handshakes use **req/ack** signal events "
      "instead of sampled levels.")
    diagram([
        '  4-phase (return-to-zero): four events per transfer',
        '                 _________         _________',
        '  req         ___|        |________|        |_____   1 req up (data valid)',
        '                    _________         _________      2 ack up (data taken)',
        '  ack         ______|        |________|        |__   3 req down, 4 ack down',
        '',
        '  2-phase (transition signalling): every edge is an event',
        '                 __________________',
        '  req         ___|                 |______________   req edge 1: transfer A',
        '                    __________________               ack edge 1: A taken',
        '  ack         ______|                 |___________   req edge 2: transfer B, ...',
    ], "Figure 3.2 - 4-phase and 2-phase req/ack handshakes.")
    tbl(["", "4-phase (level)", "2-phase (toggle)"],
        [["Events per transfer", "4", "2"],
         ["Logic", "Simple level logic, easy to reason about", "Needs XOR "
          "edge detectors / toggle flops"],
         ["Throughput across a CDC", "Lower: each transfer waits 2 round "
          "trips through synchronizers", "About twice the 4-phase rate"],
         ["Typical use", "CDC of multi-bit control words, async bus bridges",
          "Pulse synchronizers, toggle-based CDC handshakes"]],
        widths=[1.3, 2.3, 2.3], bold_first=True)
    p("Both are the standard way to move a multi-bit value between clock "
      "domains: hold the data stable, send the request through a "
      "synchronizer, sample the data when the request arrives, and "
      "acknowledge. Chapter 4 revisits this for controllers whose interface "
      "clock differs from the system clock.")

    h2("Flow control")
    p("**Flow control** prevents a fast sender from overflowing a slow "
      "receiver. The design question is always the same: when the receiver "
      "says 'stop', how much data is already in flight, and where does it "
      "go? Three families answer it differently.")
    tbl(["Mechanism", "Signal", "Where used", "Needs buffer headroom?"],
        [["Back-pressure (ready/wait)", "A per-cycle stall signal", "AXI, "
          "AHB HREADY, APB PREADY, on-chip pipelines", "Only the skid "
          "entries for registered ready"],
         ["Start/stop (XON/XOFF, pause)", "'Stop sending' / 'resume' "
          "messages or pins", "UART RTS/CTS and XON/XOFF, Ethernet PAUSE "
          "and PFC", "Yes: everything sent during the reaction time"],
         ["Credit-based", "The receiver grants a count of free buffers; the "
          "sender spends one per packet", "PCIe, CXL, CHI, NoCs, USB4, "
          "InfiniBand", "Buffers = credits; loss-free by construction"]],
        widths=[1.5, 1.8, 2.0, 1.7],
        caption="Table 3.1 - Flow-control families.")
    h3("Credit-based flow control")
    p("With **credits**, the receiver advertises how many buffer slots it "
      "has. The sender keeps a counter, decrements it for every packet "
      "sent, and stops at zero; the receiver returns a credit each time it "
      "frees a slot. Overflow is impossible by construction - no stop "
      "signal can arrive too late. The cost is buffering: to keep the link "
      "busy, the credits must cover the whole **credit loop** - the time "
      "from sending a packet until its credit returns:")
    eq(["credits_needed >= ceil( RTT_credit_loop x rate / packet_size )",
        "throughput = min(1, credits / RTT)   (in packets per cycle, 1 packet"
        " per cycle max)"],
       "Eq. 3.1 - Credit sizing. RTT includes wire latency both ways plus "
       "processing and credit-return delays.")
    _v("credit", "A credit-based link with 3-cycle latency in each "
       "direction: data pipeline, credit-return pipeline, occupancy and an "
       "overflow detector.")
    _o("credit", "Real Icarus output: the credit loop is 8 cycles, so "
       "throughput is credits/8 until 8 credits; a slow receiver throttles "
       "the link without ever overflowing.")
    p("The measured throughput follows Eq. 3.1 exactly: 2 credits give 25%, "
      "6 give 75%, and 8 - the round-trip time in cycles - saturate the "
      "link. More credits than the RTT buy nothing when the receiver keeps "
      "up; when it does not, credits simply cap the in-flight data and the "
      "sender waits.")
    h3("How PCIe does it")
    p("PCIe keeps **six** credit types per virtual channel: header and data "
      "credits for each of Posted requests (memory writes, messages), "
      "Non-Posted requests (reads, configuration and I/O writes) and "
      "Completions - PH, PD, NPH, NPD, CplH, CplD. One header credit covers "
      "one TLP header; one data credit covers 16 bytes (4 DW) of payload. "
      "Credits are initialized by InitFC DLLPs after link-up and returned "
      "with UpdateFC DLLPs; an advertisement of 0 means 'infinite'. Counters "
      "are modular (8-bit header, 12-bit data in the classic scheme), and a "
      "TLP may be sent only if:")
    eq(["(CREDIT_LIMIT - (CREDITS_CONSUMED + credits_for_this_TLP)) mod 2^N  "
        "<=  2^N / 2"],
       "Eq. 3.2 - PCIe credit gating with modulo-2^N counters (N = counter "
       "width). Half the counter space distinguishes 'enough' from 'wrapped'.")
    box("expert", "Interview insight: why posted/non-posted/completion are separate",
        "If reads, writes and completions shared one buffer pool, a flood of "
        "reads could consume all space while the completions that would "
        "free it are stuck behind them - a protocol deadlock. Separate credit "
        "pools per class (and ordering rules that let posted writes pass "
        "blocked reads) guarantee that completions can always make progress.")
    h3("XON/XOFF and pause frames")
    p("Start/stop flow control is simpler but needs **headroom**: the "
      "receiver must say 'stop' early enough to absorb everything already "
      "in flight. UART software flow control sends the ASCII XOFF (DC3, "
      "0x13) and XON (DC1, 0x11) characters; hardware flow control uses the "
      "RTS/CTS pins (Chapter 11). Ethernet's IEEE 802.3x **PAUSE** frame is a "
      "MAC Control frame (EtherType 0x8808, opcode 0x0001, destination "
      "01-80-C2-00-00-01) carrying a pause time in quanta of 512 bit times; "
      "**Priority Flow Control** (IEEE 802.1Qbb, opcode 0x0101) pauses each "
      "of eight priorities separately, which lossless data-centre fabrics "
      "rely on.")
    eq(["headroom >= rate x (t_detect + t_send_stop + t_flight x 2 + "
        "t_sender_react) + max_frame"],
       "Eq. 3.3 - Buffer headroom above the XOFF threshold.")

    h2("Retry: acknowledgements, windows and go-back-N")
    p("Detecting an error is only half the job; a reliable link must also "
      "**recover** by resending. The link keeps a copy of every unacknowledged "
      "packet in a **replay buffer** and numbers packets so that the "
      "receiver can say which ones arrived.")
    tbl(["Scheme", "How it works", "Buffering", "Examples"],
        [["Stop-and-wait", "Send one packet, wait for ACK, then the next",
          "1 packet; throughput limited by RTT", "Simple sensor links, "
          "USB 2.0 control transfers (per transaction)"],
         ["Go-back-N", "Send up to N unacknowledged packets; on NAK or "
          "timeout, resend from the first unacknowledged one", "N packets at "
          "TX; RX needs no reorder buffer", "PCIe data link layer, CXL.io, "
          "many SerDes link layers"],
         ["Selective repeat", "Resend only the missing packets; RX "
          "reorders", "N packets at both ends", "TCP with SACK, some "
          "die-to-die link layers"],
         ["FEC (no retry)", "Add redundancy to correct errors in place",
          "None, but latency and bandwidth for parity", "400G Ethernet "
          "RS-FEC, PCIe 6 FEC (combined with CRC + retry)"]],
        widths=[1.1, 2.4, 1.6, 1.8],
        caption="Table 3.2 - Retry and correction strategies.")
    diagram([
        "  TX seq:  10   11   12   13   14   15      replay buffer holds 10..15",
        "  RX:      ok   ok   BAD  (13,14,15 discarded: out of sequence)",
        "  RX -> TX:          NAK(11)   'last good = 11'",
        "  TX:      purge 10,11 ; replay 12 13 14 15 ; continue with 16",
        "  RX -> TX:                          ACK(15) -> purge 12..15",
    ], "Figure 3.3 - Go-back-N as in the PCIe data link layer: the NAK "
       "carries the last good sequence number.")
    p("PCIe's data link layer is the canonical hardware example. Every TLP "
      "carries a 12-bit **sequence number** and a 32-bit **LCRC**. The "
      "receiver returns ACK or NAK DLLPs naming the last good sequence "
      "number; ACKs may be coalesced to save bandwidth. A **REPLAY_TIMER** "
      "triggers a replay when no acknowledgement arrives, and a 2-bit "
      "**REPLAY_NUM** counter escalates to link retraining after repeated "
      "replays. The window cannot exceed half the sequence space (2048 "
      "TLPs) so that old and new numbers are never confused.")
    eq(["replay buffer bytes >= link rate x (ACK round-trip time + ACK "
        "coalescing delay) + max TLP size"],
       "Eq. 3.4 - Replay-buffer sizing - the retry analogue of Eq. 3.1.")

    h2("Ordering models")
    p("When several transactions are in flight, the protocol must say "
      "which may overtake which. Too strict and performance suffers; too "
      "loose and software sees stale data.")
    tbl(["Model", "Rule", "Examples"],
        [["Strict in-order", "Everything completes in issue order",
          "APB, AHB (one outstanding), simple FIFOs, UART"],
         ["ID-based", "Same ID (or same tag/stream) in order; different IDs "
          "may complete out of order", "AXI (per ID and per direction), CHI "
          "TxnID, NoCs"],
         ["Producer-consumer (PCIe)", "Posted writes stay in order; reads and "
          "completions may not pass earlier posted writes; posted writes must "
          "be able to pass blocked reads", "PCIe, CXL.io"],
         ["Relaxed", "Opt-in attributes allow more reordering (PCIe Relaxed "
          "Ordering, ID-Based Ordering)", "PCIe RO/IDO for bulk DMA"],
         ["Weak memory model", "The CPU architecture defines ordering; the "
          "fabric only guarantees completion and barriers", "Arm, RISC-V "
          "RVWMO with fences"]],
        widths=[1.4, 3.2, 1.9],
        caption="Table 3.3 - Ordering models.")
    p("The **producer-consumer** pattern explains most rules. A device "
      "writes a data buffer and then writes a 'done' flag (both posted). "
      "The CPU reads the flag, then the data. If the flag could overtake "
      "the data, or the CPU's data read could overtake the device's "
      "earlier data writes, the CPU would read stale data. That is why PCIe "
      "forbids a read or completion from passing a posted write in the same "
      "direction (unless relaxed attributes are set), and why AXI masters "
      "that need ordering across IDs must wait for a write response before "
      "issuing the dependent transaction.")
    box("warn", "PITFALL - ordering bugs in bridges",
        "Protocol bridges (AXI to PCIe, AXI to AHB, NoC to AXI) are where "
        "ordering bugs live: a bridge that accepts a write, returns BRESP "
        "early ('early response') and then lets a later read to the same "
        "device overtake the buffered write breaks producer-consumer "
        "semantics. Document the ordering guarantee of every bridge and "
        "test same-address write-then-read through it.")

    h2("Deadlock basics")
    p("A **deadlock** is a cycle of agents each waiting for a resource held "
      "by the next. Four conditions (Coffman) must all hold: mutual "
      "exclusion, hold-and-wait, no pre-emption, and circular wait. "
      "Protocol designers break the **circular wait**:")
    bul(["**Separate message classes.** Requests and responses use "
         "different channels or virtual channels, so a response is never "
         "stuck behind a request that needs that response to make progress "
         "(AXI's separate AR/R/AW/W/B channels, CHI's REQ/RSP/SNP/DAT "
         "channels, PCIe's P/NP/Cpl credits).",
         "**Guaranteed sinking.** Responses must always be accepted "
         "(consumed without waiting on anything else) - an AXI master should "
         "only issue reads it can accept the data for.",
         "**Routing restrictions in NoCs** (dimension-order routing on a "
         "mesh) prevent cyclic channel dependencies.",
         "**No hidden dependencies** in slaves: an AXI slave must not wait "
         "for write data of a later transaction before completing an "
         "earlier one, and must not make the AW channel wait for W in a "
         "way the specification does not allow."])
    diagram([
        "   Master A --- req ---> [ shared queue ] ---> Slave B",
        "      ^                                          |",
        "      +---- rsp <--- [ same queue, full ] <------+",
        "   A waits for space to send a request; the queue is full of requests",
        "   that B cannot complete because B's responses are stuck behind them.",
        "   Fix: give responses their own queue (message class) that always drains.",
    ], "Figure 3.4 - A request/response deadlock through a shared buffer.")

    h2("Error detection: parity and checksums")
    p("**Parity** adds one bit so that the number of ones is even (even "
      "parity) or odd (odd parity). It detects every odd number of flipped "
      "bits and no even number. Per-byte parity is cheap and common on "
      "internal buses, SRAMs and register files, and UART frames can carry "
      "a parity bit.")
    p("**Checksums** add words arithmetically. The Internet checksum "
      "(RFC 1071) is the 16-bit ones'-complement sum of 16-bit words. It is "
      "cheap in software but weak: it cannot detect reordered words and "
      "misses many bursts. Hardware links therefore use CRCs.")

    h2("CRC: the mathematics")
    p("A **cyclic redundancy check** treats the message as a polynomial "
      "over GF(2) - bits are coefficients, addition is XOR, there are no "
      "carries. With a generator polynomial G(x) of degree n, the sender "
      "computes")
    eq(["CRC = ( M(x) x x^n ) mod G(x)          transmitted T(x) = M(x) x x^n + CRC",
        "T(x) mod G(x) = 0   ->  the receiver divides again and checks for a "
        "zero (or fixed) remainder"],
       "Eq. 3.5 - CRC as polynomial division modulo 2.")
    p("The division is ordinary long division in which subtraction is XOR. "
      "The classic textbook example divides 11010011101100 by x^3+x+1 "
      "(1011):")
    _v("crcdiv", "Python that prints each XOR step of the long division "
       "(and, at the end, the CRC-32 residue used by receivers).")
    _o("crcdiv", "Real Python output: the 3-bit CRC is 100.")
    p("An error pattern E(x) goes undetected only if G(x) divides E(x). "
      "Choosing G well gives strong guarantees:")
    bul(["all **single-bit** errors (G has at least two terms);",
         "all **odd numbers** of bit errors if (x+1) divides G;",
         "all **burst** errors of length <= n, and all but a fraction "
         "2^{-(n-1)} of bursts of length n+1 and 2^{-n} of longer bursts;",
         "all **double-bit** errors within the polynomial's period;",
         "a guaranteed **Hamming distance** that depends on message length - "
         "for CRC-32 (0x04C11DB7) Koopman's published tables give HD = 4 "
         "for messages up to about 91 kbit and HD = 5 up to about 3 kbit. "
         "Polynomial choice for a new protocol should come from such "
         "tables, not from intuition."])
    h3("The parameter model")
    p("Two implementations of 'CRC-16' routinely disagree because a CRC is "
      "defined by more than its polynomial. The Rocksoft/Williams parameter "
      "model (used by the RevEng catalogue) pins it down with: **width**, "
      "**poly** (normal MSB-first form, top bit implicit), **init** "
      "(register preset), **refin** (process each byte LSB first), "
      "**refout** (bit-reverse the final register), **xorout** (value XORed "
      "at the end) and **check** (the CRC of the ASCII string "
      "\"123456789\").")
    tbl(["Name", "Width", "Poly", "Init", "RefIn/Out", "XorOut", "Check",
         "Used by"],
        [["CRC-5/USB", "5", "0x05", "0x1F", "yes/yes", "0x1F", "0x19",
          "USB token packets"],
         ["CRC-8/SMBUS", "8", "0x07", "0x00", "no/no", "0x00", "0xF4",
          "SMBus PEC, many sensors"],
         ["CRC-8/AUTOSAR", "8", "0x2F", "0xFF", "no/no", "0xFF", "0xDF",
          "Automotive E2E protection"],
         ["CRC-15/CAN", "15", "0x4599", "0x0000", "no/no", "0x0000",
          "0x059E", "Classical CAN frames"],
         ["CRC-16/IBM-3740 (CCITT-FALSE)", "16", "0x1021", "0xFFFF", "no/no",
          "0x0000", "0x29B1", "Many embedded links"],
         ["CRC-16/KERMIT", "16", "0x1021", "0x0000", "yes/yes", "0x0000",
          "0x2189", "Kermit, Bluetooth-style variants"],
         ["CRC-16/USB", "16", "0x8005", "0xFFFF", "yes/yes", "0xFFFF",
          "0xB4C8", "USB data packets"],
         ["CRC-32/ISO-HDLC", "32", "0x04C11DB7", "0xFFFFFFFF", "yes/yes",
          "0xFFFFFFFF", "0xCBF43926", "Ethernet FCS, PCIe LCRC/ECRC, zlib, "
          "SATA"],
         ["CRC-32C (Castagnoli)", "32", "0x1EDC6F41", "0xFFFFFFFF",
          "yes/yes", "0xFFFFFFFF", "0xE3069283", "iSCSI, SCTP, storage "
          "file systems"]],
        widths=[1.7, 0.5, 0.9, 0.9, 0.7, 0.9, 0.9, 1.6],
        caption="Table 3.4 - Common CRCs. Check values computed by the "
                "Python reference below; they match the RevEng catalogue.")
    _v("ref_crc", "Generic bit-serial CRC in Python (the same algorithm as "
       "the RTL), producing Table 3.4's check values, plus zlib.crc32 on "
       "two strings.")
    _o("pycrc", "Real Python output.")
    box("note", "CRC-16-CCITT is a family, not a CRC",
        "The polynomial x^16+x^12+x^5+1 (0x1021) appears in HDLC/X.25, "
        "Bluetooth, SD cards and MIPI CSI-2 packet footers - with different "
        "init values, reflection and final XOR. Always implement from the "
        "full parameter set in the specification, and test with its "
        "published example packet.")
    h3("Serial LFSR implementation")
    p("In hardware the division is a **Galois LFSR**: shift the register "
      "left one bit per message bit; if the bit shifted out XOR the "
      "incoming message bit is 1, XOR the polynomial into the register.")
    diagram([
        "  CRC-8 example, G = x^8 + x^2 + x + 1 (0x07), MSB-first:",
        "",
        "   +---------------+----------------+",
        "   |               v                v",
        "   +-> [c0] --> (XOR) --> [c1] --> (XOR) --> [c2] --> [c3] -> ... -> [c7] --+",
        "   ^                                                                        |",
        "   +--------------------- fb ------------------------- (XOR) <--------------+",
        "                                                          ^",
        "                                                         din",
        "   next: c0 = fb, c1 = c0 ^ fb, c2 = c1 ^ fb, c3..c7 = c2..c6, fb = c7 ^ din",
    ], "Figure 3.5 - Galois LFSR for CRC-8: an XOR gate before every "
       "register whose power appears in G(x).")
    _v("crc", "A parameterized bit-serial CRC and a byte-parallel CRC-32 "
       "(Ethernet/zlib). Reflection is handled by feeding each byte LSB "
       "first; the final value is bit-reversed and inverted.")
    _v("tb_crc", "Testbench: four serial CRCs (CRC-32, CRC-16/IBM-3740, "
       "CRC-15/CAN, CRC-5/USB) and the byte-parallel CRC-32 run over the "
       "same strings; expected values come from Python's zlib.crc32.")
    _o("crc", "Real Icarus Verilog output: serial and byte-parallel RTL both "
       "equal zlib.crc32 on '123456789' and on the pangram; the other CRCs "
       "match Table 3.4.")
    p("A useful receiver trick follows from Eq. 3.5: running the CRC over "
      "the message **and its transmitted FCS** gives a constant, the "
      "**residue**, whatever the message. For the Ethernet CRC-32 the final "
      "(inverted) value is 0x2144DF1C, as the last line of the long-division "
      "script shows; the raw register holds 0xC704DD7B (0xDEBB20E3 in "
      "reflected form). A MAC can therefore check the FCS on the fly "
      "without knowing where the frame ends until it ends.")
    h3("Parallel CRC derivation")
    p("At 10 Gb/s and above a bit-serial CRC cannot keep up: the data path "
      "is 32 to 512 bits wide per clock. Because the CRC is **linear** over "
      "GF(2), the next state after D input bits is a fixed XOR function of "
      "the current state and the D data bits: crc' = A x crc XOR B x d. The "
      "matrices can be derived by unrolling the serial loop (as `step8` in "
      "`crc32_d8` does - synthesis flattens it) or explicitly by "
      "superposition: feed a single 1 in each state or data position and "
      "record which output bits toggle.")
    _v("par_derive", "Deriving the byte-parallel CRC-8 (0x07) equations by "
       "superposition.")
    _o("parderive", "Real Python output (x = crc XOR data, bitwise; this "
       "simplification holds when the data width equals the CRC width).")
    p("The cost grows with the data width. Running the same superposition "
      "on CRC-32 gives the XOR fan-in per output bit:")
    _o("parcost", "Real Python output (par_cost.py): XOR inputs per CRC-32 "
       "bit for D data bits per clock.")
    p("At 128 bits per clock each CRC bit is an XOR of up to 89 inputs - "
      "about seven levels of 2-input XOR, which is why wide MACs pipeline "
      "the CRC or split it into per-lane partial CRCs combined later. Real "
      "links also must handle a **last word that is only partly valid** "
      "(the byte-enable problem): typical solutions compute the CRC for "
      "each possible valid-byte count in parallel and select, or process "
      "the tail in a narrower final stage.")

    h2("ECC: Hamming codes and SECDED")
    p("Detection plus retry works for links; for **memories**, where "
      "there is nothing to retry from, errors must be **corrected**. The "
      "Hamming distance d of a code determines its power: it can detect "
      "d-1 errors or correct floor((d-1)/2). A **Hamming code** (d = 3) "
      "places parity bits at positions 1, 2, 4, 8, ... of the codeword; "
      "parity bit 2^p covers every position whose index has bit p set. On "
      "reception, the recomputed parities - the **syndrome** - spell out "
      "the index of a single flipped bit directly. Adding one overall "
      "parity bit raises the distance to 4: **SECDED** (single-error "
      "correct, double-error detect).")
    tbl(["Overall parity", "Syndrome", "Diagnosis", "Action"],
        [["0 (even)", "0", "No error", "Pass data"],
         ["1 (odd)", "!= 0, points inside the word", "Single-bit error at "
          "position = syndrome", "Flip that bit, report corrected error "
          "(CE)"],
         ["1 (odd)", "0", "Error in the overall parity bit itself",
          "Data is fine, report CE"],
         ["0 (even)", "!= 0", "Double-bit error", "Report uncorrectable "
          "error (UE); do not use data"],
         ["1 (odd)", "points outside the word", ">= 3 errors", "Report UE"]],
        widths=[1.0, 1.6, 2.0, 2.0],
        caption="Table 3.5 - SECDED decode table.")
    p("For 64 data bits, 7 Hamming check bits cover positions 1-71 and one "
      "overall parity bit makes the classic **(72,64)** code used on ECC "
      "DIMMs and in SRAM and cache ECC. Production designs usually use "
      "**Hsiao** codes - the same (72,64) size, but with odd-weight "
      "check-matrix columns chosen to minimize XOR depth and give faster "
      "double-error detection. DDR5 adds an internal **on-die ECC** (a SEC "
      "code over 128 data bits) in addition to any system-level ECC. The "
      "plain Hamming construction below is the easiest to understand.")
    _v("secded", "SECDED (72,64) encoder and decoder: Hamming positions "
       "1-71, check bits at powers of two, overall parity in bit 0.")
    _v("tb_secded", "Testbench: a worked example, then 2 000 random words "
       "with every single-bit error and 20 random double-bit errors each.")
    _o("secded", "Real Icarus Verilog output: all 144 000 single-bit errors "
       "corrected, all 40 000 double-bit errors detected, no false flags.")
    _o("secded_py", "Real output of ref_secded.py, an independent Python "
       "encoder: the same check bits for 0x0123456789ABCDEF.")
    box("warn", "PITFALL - ECC integration bugs",
        ["**Partial writes.** Writing one byte of an ECC-protected 64-bit "
         "word requires read-modify-write; forgetting it corrupts check "
         "bits and turns every later read into a false error.",
         "**Uninitialized memory** has random check bits; reading it before "
         "initialization floods the system with UEs. Initialize (scrub) at "
         "boot.",
         "**Silent correction.** Log and count corrected errors - a rising "
         "CE rate is the only warning before a UE - and write the corrected "
         "value back (scrubbing) so single errors do not accumulate into "
         "doubles.",
         "**Address errors.** Plain ECC over data does not detect a read "
         "from the wrong address; fold address bits into the code if that "
         "matters (common in safety designs, Chapter 26)."])

    h2("Summary")
    bul(["Valid/ready transfers on every edge where both are high; the "
         "source must not wait for ready and must hold valid and data until "
         "the transfer.",
         "4-phase and 2-phase req/ack handshakes move data between "
         "unrelated clocks; 2-phase needs half the events.",
         "Back-pressure, start/stop and credits are the three flow-control "
         "families; credits make overflow impossible but must cover the "
         "credit round trip (throughput = credits/RTT, as simulated).",
         "Go-back-N retry with sequence numbers, ACK/NAK and a replay "
         "buffer (PCIe DLL) turns rare bit errors into invisible retries.",
         "Ordering rules (in-order, ID-based, producer-consumer, relaxed) "
         "and separate message classes keep software correct and systems "
         "deadlock-free.",
         "A CRC is polynomial division over GF(2), fully specified only by "
         "width, poly, init, refin, refout and xorout; serial and "
         "byte-parallel RTL matched zlib.crc32.",
         "Parallel CRCs follow from linearity; XOR depth grows with data "
         "width.",
         "Hamming SECDED (72,64) corrects all single and detects all double "
         "errors, as the exhaustive single-error and random double-error "
         "simulation showed."])
    h2("Exercises")
    bul(["A PCIe-like link has 400 ns of credit round-trip time, 16 GB/s of "
         "payload bandwidth and 256-byte payloads. How many data credits "
         "(16 bytes each) and header credits are needed for full "
         "throughput?",
         "Extend credit_link so that credits are returned in batches of four "
         "(like coalesced UpdateFC DLLPs). Predict and then measure the "
         "throughput for 8 and 12 credits.",
         "Compute by hand the CRC-8/SMBUS of the two bytes 0x01 0x02 using "
         "the parallel equations of the output card, and check with "
         "ref_crc.py.",
         "Modify crc32_d8 to accept 32 bits per clock with a 2-bit count of "
         "valid bytes in the last word. Verify against zlib.crc32 for "
         "message lengths 1 to 64.",
         "Show that the (72,64) code in secded72_dec miscorrects some triple "
         "errors. Write a testbench that measures the fraction of triple "
         "errors reported as CE, UE and silently wrong.",
         "Draw the go-back-N sequence of Figure 3.3 for the case where the "
         "NAK itself is lost. Which timer recovers the link, and how many "
         "TLPs are replayed?"])


# ---------------------------------------------------------------- Ch 4 ----
def _ch4():
    chapter("Implementing and Verifying Protocols in RTL")
    p("Chapters 2 and 3 described what happens on the wire. This chapter is "
      "about building it: the architecture shared by almost every protocol "
      "controller, and the recurring RTL building blocks - baud and bit "
      "timing generators, shift registers, oversampling receivers with "
      "majority voting, synchronizers, tri-state and open-drain pad "
      "interfaces, timeouts - followed by the verification side: protocol "
      "checkers, SystemVerilog assertions, bus functional models, VIP and "
      "compliance. The run example is a generic, parameterized framed "
      "serializer/deserializer pair (start bit, data, optional parity, stop "
      "bit) running on two unrelated clocks, with an independent protocol "
      "checker that catches injected errors, and SVA properties run in "
      "Verilator.")

    h2("Generic controller architecture")
    p("Open the block diagram of a UART, SPI, I2C, CAN or even USB "
      "controller and you find the same five layers. Learning the pattern "
      "once makes every new controller familiar:")
    diagram([
        "     system clock domain (clk_sys)                     interface clock / pins",
        "  +-------------+   +-----------+   +--------------+   +------------+   +-----+",
        "  | Bus slave   |   | CSR bank  |   | TX FIFO      |   | Protocol   |   | PHY/|",
        "  | APB/AHB/AXI |-->| CTRL,STAT |-->|  (async if   |-->| engine FSM |-->| pad |==>",
        "  | (Ch. 5-8)   |<--| IRQ, CFG  |<--|   clocks     |<--| framing,   |<--| i/f |<==",
        "  +-------------+   +-----+-----+   | differ)      |   | bit timing,|   |o/oe/i",
        "        ^                 |         | RX FIFO      |   | shifters,  |   +-----+",
        "        | DMA req/ack     | irq     +--------------+   | CRC, error |",
        "        +-----------------+-----> interrupt ctrl        +------------+",
    ], "Figure 4.1 - The universal peripheral controller: register "
       "interface, CSRs, FIFOs, protocol engine, pad interface.")
    tbl(["Block", "Responsibility", "Design notes"],
        [["**Bus slave / register interface**", "Decode APB/AHB/AXI accesses "
          "into register reads and writes", "Usually generated from a "
          "register description (IP-XACT, SystemRDL); must respond to every "
          "access, including unmapped addresses"],
         ["**CSR bank**", "Control, status, interrupt enable/status, "
          "configuration (baud divisor, mode, polarity)", "Clear rules "
          "for W1C status, sticky errors, read side effects (reading a data "
          "register pops the FIFO)"],
         ["**FIFOs**", "Decouple bursty software/DMA from the fixed-rate "
          "wire; cross clock domains", "Depth from latency tolerance "
          "(interrupt latency x line rate); thresholds for interrupts/DMA"],
         ["**Protocol engine**", "The FSM that sequences frames: start, "
          "address, data, acknowledge, stop, turnaround, retries", "Where "
          "the specification's state diagrams live; keep it separate from "
          "bit timing"],
         ["**Bit-level datapath**", "Shift registers, bit counters, baud/"
          "prescaler, oversampling, CRC, parity, stuffing", "Parameterize "
          "widths; reuse across protocols"],
         ["**Pad interface**", "o/oe/i triplets, synchronizers on inputs, "
          "glitch filters", "Never tri-state inside the core; keep inputs "
          "asynchronous until synchronized"]],
        widths=[1.4, 2.3, 2.9],
        caption="Table 4.1 - Controller blocks and their responsibilities.")
    box("tip", "Split control from timing",
        "A robust controller separates **what** to send (the protocol FSM, "
        "which advances once per bit or per symbol) from **when** (a timing "
        "generator that emits single-cycle ticks). The FSM then runs on the "
        "system clock with a clock-enable, which keeps the whole block in "
        "one clock domain, simplifies STA, and lets one design serve many "
        "baud rates.")

    h2("Bit timing generation: prescalers and fractional baud")
    p("Low-speed serial protocols run at rates far below the system clock, "
      "so the controller derives a **tick** - a one-cycle enable - at the "
      "bit rate or at a multiple of it (16x oversampling is traditional for "
      "UARTs). Generating a divided **clock** instead would create a new "
      "clock domain, a clock-tree to balance and CDC paths; a tick keeps "
      "everything synchronous.")
    tbl(["Method", "Rate", "Error", "Notes"],
        [["Integer prescaler", "f_clk / N", "Up to half a count: for f_clk = "
          "50 MHz and 16 x 115200 Hz, N = 27 gives 1.852 MHz, +0.47%",
          "Simple; error grows as N gets small"],
         ["Integer + fractional (UART DLL/DLM + DLF)", "f_clk / (N + F/16)",
          "Much smaller", "Common in 16550-compatible UARTs"],
         ["Phase accumulator", "f_clk x INC / 2^K", "At most f_clk / 2^K "
          "resolution; tick-to-tick jitter of one clk", "Any rate; used "
          "below with K = 16"]],
        widths=[1.4, 1.2, 2.6, 1.6],
        caption="Table 4.2 - Bit-timing generators.")
    eq(["INC = round( f_tick x 2^16 / f_clk ) = round( 1.8432 MHz x 65536 / "
        "50 MHz ) = 2416",
        "f_tick = 50 MHz x 2416 / 65536 = 1.843262 MHz  ->  error = +34 ppm",
        "RX at 48 MHz: INC = 2517 -> 1.843506 MHz -> +166 ppm"],
       "Eq. 4.1 - Phase-accumulator baud generation for 115200 baud x 16.")
    p("The accumulator's tick spacing alternates between 27 and 28 clocks "
      "so its average is exact to a few ppm; the resulting cycle-to-cycle "
      "jitter of one system clock (20 ns, under 0.25% of a bit at 115200 "
      "baud) is harmless.")

    h2("Shift registers, serializers and oversampling receivers")
    p("The transmit datapath is a **parallel-in, serial-out** shift "
      "register: load a whole frame (start bit, data, parity, stop), then "
      "shift one bit per bit-time. LSB-first (UART, most SerDes PCS "
      "lanes) versus MSB-first (SPI usually, I2C, CAN) is just the shift "
      "direction, but mixing conventions between the RTL and the "
      "software driver is a classic bring-up bug.")
    p("The receiver is harder because it must find the bits in time. An "
      "asynchronous receiver samples the line at OSR times the bit rate "
      "(OSR = 16 here):")
    bul(["**Start detection.** In idle, a low sample may be a start bit. "
         "Wait half a bit and check again: if the line is high again it was "
         "a glitch and the receiver returns to idle.",
         "**Centre sampling.** From the start-bit centre, sample every OSR "
         "ticks - each sample lands in the centre of a data bit.",
         "**Majority vote.** Take three samples around the centre (ticks 7, "
         "8, 9 of 16) and vote, which suppresses short noise spikes.",
         "**Framing check.** The stop bit must be 1; otherwise flag a "
         "**framing error** (and a line held low for a whole frame is a "
         "**break** condition).",
         "**Resynchronize every frame.** Return to idle in the middle of "
         "the stop bit so the next start edge re-aligns the timing."])
    diagram([
        '          ______                ________________',
        '  line          |_______________|               |_______ ...',
        '                |<- start bit ->|<- data bit 0->|',
        '  tick          0      789     0      789     (16 ticks per bit)',
        '                       ^^^             ^^^',
        '              start still 0?      vote = bit 0',
    ], "Figure 4.2 - 16x oversampling: start-bit validation and three-sample "
       "majority vote at the bit centre.")
    p("How much clock mismatch can such a receiver take? The last sample "
      "(stop-bit centre) is 9.5 bit times after the start edge for 8N1 "
      "(1 start + 8 data + half the stop bit), and the start edge itself is "
      "only known to within one tick (1/16 bit). The accumulated timing "
      "error must stay within half a bit:")
    eq(["9.5 x |delta_f / f| + 1/16  <  0.5    ->   |delta_f / f| < 4.6 % "
        "(total, TX + RX)",
        "with parity (8E1: 10.5 bits): < 4.2 %",
        "in practice keep each side under ~1-2 % to leave margin for edge "
        "distortion"],
       "Eq. 4.2 - Clock tolerance of an oversampling asynchronous receiver.")

    h2("Synchronizers and clock-domain crossing")
    p("A protocol controller almost always has at least two timing "
      "domains: the **system clock** of the bus interface and FIFOs, and "
      "the **interface timing** - either a derived tick (UART, I2C master), "
      "an external clock (SPI slave's SCLK, I2S BCLK, JTAG TCK), or a "
      "PHY's recovered clock (USB, PCIe, Ethernet). The standard CDC toolkit "
      "(covered in depth in the companion RTL Design guide) applies:")
    tbl(["What crosses", "Technique", "Protocol example"],
        [["A level-sensitive asynchronous input (RX line, SDA, CTS)",
          "2-flop (or 3-flop) synchronizer before any logic uses it",
          "UART RX (`sync` in ser_rx below), I2C SDA/SCL, GPIO"],
         ["A single-cycle event", "Toggle + synchronizer + edge detect "
          "(pulse synchronizer)", "'frame done' from an SPI SCLK domain to "
          "clk_sys"],
         ["A multi-bit value that changes rarely", "Req/ack handshake "
          "(Section 3.2), data held stable", "Configuration registers into "
          "a PHY clock domain"],
         ["A stream of data", "Asynchronous FIFO with Gray-coded pointers",
          "USB/Ethernet PHY clock to system clock; SPI slave data"],
         ["An externally supplied clock with its data", "Capture in the "
          "external clock domain, then an async FIFO or handshake",
          "SPI slave, I2S, JTAG TAP"]],
        widths=[2.0, 2.2, 2.3],
        caption="Table 4.3 - CDC techniques in protocol controllers.")
    box("warn", "PITFALL - sampling a slow bus with a fast clock",
        ["Oversampling an external clock such as SCL or SCLK with clk_sys "
         "(instead of using it as a clock) works only when clk_sys is several "
         "times faster than the external clock and the input is synchronized "
         "and glitch-filtered first. Without the filter, ringing on a slow "
         "edge produces double clock pulses - a classic I2C bug.",
         "The 2-flop synchronizer adds 2-3 cycles of latency. Protocols with "
         "tight turnaround (an I2C ACK, an SPI slave's first MISO bit) must "
         "budget for it.",
         "Never synchronize the bits of a multi-bit bus independently; they "
         "can resolve on different cycles."])

    h2("Tri-state and open-drain modelling in RTL")
    p("Inside a synthesizable core there are **no tri-state buses**: every "
      "bidirectional pin is represented by three separate signals, and "
      "the actual tri-state buffer lives in the I/O pad cell instantiated "
      "at the chip top level:")
    tbl(["Signal", "Direction (core view)", "Meaning"],
        [["`x_o`", "output", "Value to drive when enabled"],
         ["`x_oe` (or `x_en`)", "output", "1 = drive the pin, 0 = release "
          "(high impedance)"],
         ["`x_i`", "input", "Value seen at the pin (asynchronous - "
          "synchronize before use)"]],
        widths=[1.2, 1.4, 3.0])
    p("An **open-drain** output is the special case `x_o = 0` and "
      "`x_oe = pull_low`: the core never drives a '1'. The pad model below "
      "and the `tri1` net (a wire with a pull-up) reproduce the wired-AND "
      "behaviour of an I2C line in simulation.")
    _v("od", "Open-drain pad model and a two-device wired-AND bus.")
    _o("od", "Real Icarus output: the bus is high only when nobody pulls "
       "low.")
    box("note", "Where the tri-state really goes",
        "In the SoC top level the o/oe/i triplet connects to a pad cell "
        "(or to a pin-mux that routes it to one of several pads). Keeping "
        "tri-states out of the core lets synthesis, scan insertion, "
        "equivalence checking and emulation work normally; many FPGA and "
        "emulation flows cannot handle internal tri-states at all.")

    h2("Timeouts and error recovery")
    p("Real links misbehave: devices are unplugged mid-transfer, a slave "
      "holds a line low after a brown-out, noise corrupts a frame. A "
      "controller that waits forever for an event that never comes is a "
      "hang that no software can fix. Every protocol engine therefore "
      "needs explicit recovery paths:")
    tbl(["Mechanism", "Example"],
        [["**Watchdog / timeout counters** on every wait state",
          "SMBus: a device holding SCL low longer than 25-35 ms must be "
          "treated as timed out; PCIe completion timeouts; AXI slave "
          "response timeouts in safety SoCs"],
         ["**Bus recovery sequences**", "I2C bus clear: if SDA is stuck low, "
          "the controller clocks SCL up to nine times until the slave "
          "releases SDA, then issues STOP"],
         ["**Error counters and states**", "CAN's transmit/receive error "
          "counters with error-active, error-passive and bus-off states "
          "(Chapter 15)"],
         ["**Retry with limits**", "PCIe REPLAY_NUM rollover triggers link "
          "retraining (Section 3.4)"],
         ["**Sticky status and interrupts**", "Framing, parity, overrun, "
          "NACK, arbitration-lost bits that stay set until software clears "
          "them (write-1-to-clear)"],
         ["**Soft reset / flush**", "A register bit that returns the protocol "
          "engine to idle and empties FIFOs without resetting the SoC"]],
        widths=[1.6, 4.4],
        caption="Table 4.4 - Recovery mechanisms every controller should "
                "consider.")
    box("warn", "PITFALL - error paths are the least-tested paths",
        "Directed tests exercise the happy path; the error recovery FSM "
        "transitions are often never simulated until silicon. Make every "
        "error condition injectable from the testbench (as the channel "
        "model below does), cover each recovery transition, and check that "
        "the controller returns to a clean idle afterwards.")

    h2("Run example: a framed serializer/deserializer with a checker")
    p("The example ties the chapter together. `ser_tx` and `ser_rx` are "
      "parameterized by data width `DW`, oversampling ratio `OSR` and "
      "parity `PAR`; the frame is start (0), DW data bits LSB first, "
      "optional even parity, stop (1) - the UART frame of Chapter 11, but "
      "the same structure appears in LIN, DMX and many proprietary links. "
      "The transmitter runs at 50 MHz and the receiver at 48 MHz, each "
      "with its own phase-accumulator tick generator (Eq. 4.1), so the line "
      "is truly asynchronous to the receiver.")
    _v("serdes", "tick_gen, ser_tx and ser_rx: fractional baud ticks, "
       "parallel-load shift register with registered output, and a "
       "receiver with 2-flop synchronizer, start validation, majority vote, "
       "framing and parity checks.")
    p("The checker is written independently of the receiver, as a "
      "verification engineer would: it knows the timing (the same tick as "
      "the transmitter) and encodes the specification as five rules. It "
      "watches the line after the channel, so it sees exactly what a "
      "compliance analyzer would see, and it watches the valid/ready "
      "interface on the producer side.")
    _v("chk", "frame_chk: an independent protocol checker with five rules, "
       "including the valid/ready stability rule from Chapter 3.")
    _v("tb_serdes", "Testbench: 200 clean frames, then three injected "
       "faults - a stop bit forced low, a flipped data bit, and a producer "
       "that changes data while waiting for ready.")
    _o("serdes", "Real Icarus Verilog output.")
    p("Reading the result: in the clean run all 200 bytes arrive intact "
      "across the two unrelated clocks and the checker sees 200 legal "
      "frames. Each injected fault is caught where it should be: the forced "
      "stop bit is a framing error in the receiver **and** an R3 violation "
      "in the checker; the flipped bit is a parity error in both; the "
      "valid/ready violation is invisible to the receiver - the frame is "
      "perfectly legal on the wire, it just carries the wrong byte (the "
      "'data errors=1') - and only the checker's R5 identifies the real "
      "culprit. That asymmetry is the whole argument for protocol checkers "
      "at **interfaces**, not just end-to-end scoreboards.")

    h2("Protocol checkers with SystemVerilog assertions")
    p("Hand-written checkers like `frame_chk` are portable, but "
      "**SystemVerilog Assertions** (SVA) express temporal rules far more "
      "compactly, work in simulation and formal verification alike, and "
      "report exactly which rule failed and when. Below is a full-SVA "
      "version of three rules for `ser_tx`, attached with `bind` so the RTL "
      "is untouched. It uses `default clocking`, `default disable iff` and "
      "sequence delays, which commercial simulators and formal tools "
      "support; Verilator 5.020 rejected those constructs, so this version "
      "is shown **without a run**.")
    _v("sva_full", "Full-SVA checker for ser_tx (not run: needs a simulator "
       "or formal tool with complete SVA support).")
    p("Rewriting the same properties in the subset Verilator 5.020 "
      "supports - explicit clocking and `disable iff` per property, `$past` "
      "instead of `##1` - gives a version that does run. The testbench "
      "(tb_sva.sv) reproduces the valid/ready violation of the previous "
      "section.")
    _v("sva", "The Verilator-compatible version of the properties.")
    _o("sva", "Real Verilator 5.020 output (--binary --timing --assert; "
       "run with +verilator+error+limit+10 so the simulation continues). "
       "Times are in ps: the violation is flagged at 190 ns, the first "
       "clock edge after in_data changed.")
    tbl(["Property style", "Example", "Checks"],
        [["Stability", "`valid && !ready |=> valid && $stable(data)`",
          "Handshake hold rules (AXI, AXI-Stream, any valid/ready)"],
         ["Response", "`req |-> ##[1:16] ack`", "Bounded latency; "
          "no hang"],
         ["Sequence", "`start |=> addr ##8 ack_bit`", "Framing order of a "
          "serial protocol"],
         ["Mutual exclusion", "`$onehot0({gnt0, gnt1, gnt2})`", "Arbiter "
          "grants, one driver on a bus"],
         ["Reset / idle", "`!rst_n |=> line == 1'b1`", "Idle-state "
          "requirements"],
         ["Cover", "`cover property (valid && ready ##1 valid && ready)`",
          "Back-to-back transfers were actually exercised"]],
        widths=[1.1, 2.9, 2.2],
        caption="Table 4.5 - Assertion patterns for protocol rules.")
    box("expert", "Interview insight: assertions at the boundary",
        "Put interface assertions in a separate checker module bound to the "
        "port list, not inside the RTL. The same file then checks the "
        "design in simulation, is proven by formal tools, travels with the "
        "IP to the SoC team, and - for AMBA protocols - can be replaced by "
        "the vendor's protocol-checker IP. Assume-guarantee reasoning makes "
        "the rules on one side of an interface the constraints of the "
        "other side in formal verification.")

    h2("Bus functional models, VIP and compliance")
    p("A **bus functional model (BFM)** is testbench code that drives and "
      "samples an interface at the pin level from high-level calls - the "
      "`send()` task in `tb_serdes` is a minimal one. A **verification IP "
      "(VIP)** is a complete, reusable package for a protocol: typically a "
      "UVM agent with a driver (BFM), a monitor, a sequencer with sequence "
      "libraries, protocol assertions, functional coverage and, for "
      "complex protocols, a full reference model of the link partner.")
    tbl(["Component", "Role", "In this chapter's example"],
        [["Driver / BFM", "Converts transactions into pin wiggles; can "
          "inject errors", "`send()` task"],
         ["Monitor", "Reconstructs transactions from pins (passive)",
          "The RX side of `frame_chk`"],
         ["Checker / assertions", "Encodes protocol rules", "`frame_chk` "
          "rules R1-R5, SVA properties"],
         ["Scoreboard", "Compares observed with expected data end-to-end",
          "The queue `q` and `data errors` count"],
         ["Coverage", "Measures which scenarios were exercised", "(add: "
          "parity values, back-to-back frames, each error type)"],
         ["Sequences / tests", "Stimulus scenarios: random, directed, "
          "error injection", "200 random frames + three fault injections"]],
        widths=[1.3, 2.7, 2.2],
        caption="Table 4.6 - Anatomy of a VIP, mapped onto the run example.")
    p("VIP can be **active** (drives the interface, standing in for a "
      "missing link partner) or **passive** (only monitors and checks, for "
      "use at SoC level where both sides are real RTL). For standard "
      "protocols teams buy commercial VIP rather than write it, because "
      "the VIP's value lies in the thousands of spec rules and corner cases "
      "it already encodes; writing your own is justified for proprietary "
      "or very simple interfaces.")
    h3("Compliance and interoperability")
    p("Passing your own tests proves only that your reading of the "
      "specification is self-consistent. Standard bodies therefore run "
      "**compliance programs**: electrical tests of the PHY (eye masks, "
      "jitter tolerance, return loss), protocol tests of the link and "
      "transaction layers (often scripted test suites run with an "
      "exerciser), and **interoperability** events (plugfests, PCI-SIG "
      "compliance workshops, USB-IF certification, MIPI conformance "
      "testing, HDMI Authorized Test Centers). For RTL teams the practical "
      "implications are: use a compliance-aware VIP in pre-silicon "
      "verification, keep PHY test modes (loopback, PRBS generators and "
      "checkers, compliance patterns) accessible from software, and plan "
      "for certification in the schedule.")
    checklist("Protocol-controller verification checklist", [
        "Every rule in the specification's timing diagrams has an assertion "
        "or checker rule, bound at the interface.",
        "Random stimulus with back-pressure on every valid/ready interface, "
        "including long stalls and back-to-back transfers.",
        "Clock ratios swept (fast/slow system clock versus interface rate) "
        "and clock tolerance at the specification limits.",
        "Every error type injectable and every recovery path covered, "
        "including return to idle.",
        "Reset in the middle of a transfer; soft reset and FIFO flush.",
        "CDC and reset-domain crossing sign-off on the controller.",
        "Register model tests: reset values, access types, W1C, side effects.",
        "Compliance or VIP-based protocol tests for standard interfaces."])

    h2("Summary")
    bul(["Protocol controllers share one architecture: bus slave and CSRs, "
         "FIFOs, a protocol FSM, a bit-level datapath and a pad interface.",
         "Generate bit timing as clock-enable ticks - integer, fractional or "
         "phase-accumulator (Eq. 4.1) - rather than divided clocks.",
         "Oversampling receivers validate the start bit, sample at the bit "
         "centre with a majority vote and resynchronize every frame; 8N1 "
         "tolerates about 4.6% total clock error (Eq. 4.2).",
         "Synchronize every asynchronous input, use handshakes or async "
         "FIFOs for multi-bit data, and budget synchronizer latency.",
         "Model bidirectional pins as o/oe/i triplets; open-drain means "
         "o = 0 and oe = pull-low; real tri-states belong in pad cells.",
         "Every wait needs a timeout and every error a recovery path, all "
         "injectable in the testbench.",
         "The framed SerDes ran error-free across 50/48 MHz clocks; an "
         "independent checker and SVA caught injected framing, parity and "
         "valid/ready violations, one of which the receiver could not see.",
         "VIP = driver + monitor + checks + scoreboard + coverage + "
         "sequences; compliance programs close the gap between "
         "self-consistency and interoperability."])
    h2("Exercises")
    bul(["Compute the integer prescaler and the phase-accumulator INC for "
         "921 600 baud x 16 from a 100 MHz clock. What is each method's "
         "rate error?",
         "Change ser_rx to OSR = 8 and sample at ticks 3, 4, 5. Re-derive "
         "Eq. 4.2 for this case and test the tolerance by changing the RX "
         "INC value in tb_serdes.",
         "Add a break detector to ser_rx (line low for a full frame) and an "
         "overrun flag (a new frame completes while out_valid data has not "
         "been read). Add checker rules for both.",
         "Write SVA properties for ser_rx: a framing error must be reported "
         "iff the stop-bit majority vote was 0; out_valid is a single-cycle "
         "pulse. Run them with Verilator's supported subset.",
         "Sketch the o/oe/i connections for an I2C controller (SCL and SDA) "
         "including clock stretching. Which inputs need synchronizers and "
         "glitch filters?",
         "Turn tb_serdes into a minimal UVM-style structure: separate the "
         "driver, monitor, scoreboard and a coverage group counting data "
         "values, parity values and error types."])
