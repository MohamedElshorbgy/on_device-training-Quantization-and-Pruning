"""Part V - Designing With Protocols (Chapters 24-27) of the protocols guide.

Verilog sources in SRC were simulated with Icarus Verilog 12 (iverilog -g2012 -Wall
+ vvp) or, where noted, Verilator 5.020 (--binary --timing [--assert]); the Python
scripts ran under Python 3. OUT holds the captured output verbatim (only the
trailing "$finish" line of each simulation is omitted).
"""

from proto_guide.common import *  # noqa: F401,F403

# --- sources and REAL simulator / script output (generated from runs) ---
SRC = {
    'dma': r'''
// Descriptor-based DMA: walks a linked list of descriptors in memory and streams each
// buffer out on an AXI4-Stream-style port. Descriptor = 3 words at address dp:
//   dp+0: [31] OWN (1 = HW owns)  [30] EOP (TLAST at end)  [29] EOC (end of chain)  [15:0] LEN
//   dp+1: buffer address (word)     dp+2: next descriptor address
module desc_dma #(parameter int AW = 8, parameter int DEPTH = 4) (
  input  logic          clk, rst_n,
  input  logic          start,                 // CSR "GO" (pulse)
  input  logic [AW-1:0] desc_base,             // CSR: first descriptor
  output logic          busy, irq, err,        // irq: chain done, err: descriptor not owned
  // one-port synchronous memory (read data valid 1 cycle after mem_re)
  output logic          mem_re, mem_we,
  output logic [AW-1:0] mem_addr,
  output logic [31:0]   mem_wdata,
  input  logic [31:0]   mem_rdata,
  // stream output
  output logic          m_tvalid, m_tlast,
  output logic [31:0]   m_tdata,
  input  logic          m_tready
);
  typedef enum logic [2:0] {IDLE, F0, F1, F2, F3, DATA, WB, DRAIN} st_t;
  st_t st;
  logic [AW-1:0] dp, ptr, nxt;
  logic [31:0]   w0;
  logic [15:0]   rem;
  // ---- data FIFO {last, data} + one read in flight (credit = free slots) ----
  logic [32:0] fifo [DEPTH];
  logic [$clog2(DEPTH):0] cnt;
  logic [$clog2(DEPTH)-1:0] wp, rp;
  logic pend, pend_last;
  wire  push = pend;                                  // read data returns -> push
  wire  pop  = m_tvalid && m_tready;
  wire  can_issue = (st == DATA) && (rem != 0) && (cnt + pend < DEPTH);
  assign m_tvalid = (cnt != 0);
  assign {m_tlast, m_tdata} = fifo[rp];
  assign busy = (st != IDLE);
  wire [31:0] w0_done = {1'b0, w0[30:0]};             // write-back value: OWN cleared

  always_comb begin
    mem_re = 1'b0; mem_we = 1'b0; mem_addr = dp; mem_wdata = '0;
    case (st)
      F0:   begin mem_re = 1'b1; mem_addr = dp;     end
      F1:   begin mem_re = 1'b1; mem_addr = dp + 1; end
      F2:   begin mem_re = 1'b1; mem_addr = dp + 2; end
      DATA: begin mem_re = can_issue; mem_addr = ptr; end
      WB:   begin mem_we = 1'b1; mem_addr = dp; mem_wdata = w0_done; end
      default: ;
    endcase
  end

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      st <= IDLE; irq <= 0; err <= 0; pend <= 0; pend_last <= 0;
      cnt <= 0; wp <= 0; rp <= 0; dp <= 0; ptr <= 0; nxt <= 0; rem <= 0; w0 <= 0;
    end else begin
      irq <= 1'b0;
      pend <= can_issue;
      pend_last <= can_issue && (rem == 1) && w0[30];
      if (push) begin fifo[wp] <= {pend_last, mem_rdata}; wp <= wp + 1; end
      if (pop)  rp <= rp + 1;
      cnt <= cnt + push - pop;
      case (st)
        IDLE: if (start) begin dp <= desc_base; err <= 1'b0; st <= F0; end
        F0:   st <= F1;
        F1:   begin w0 <= mem_rdata; st <= F2; end
        F2:   begin ptr <= mem_rdata[AW-1:0]; st <= F3; end
        F3:   begin
                nxt <= mem_rdata[AW-1:0];
                rem <= w0[15:0];
                if (!w0[31]) begin err <= 1'b1; irq <= 1'b1; st <= IDLE; end  // not ours
                else st <= DATA;
              end
        DATA: if (can_issue) begin ptr <= ptr + 1; rem <= rem - 1; end
              else if (rem == 0 && !pend) st <= WB;
        WB:   if (w0[29]) st <= DRAIN;      // OWN cleared this cycle: buffer returned
              else begin dp <= nxt; st <= F0; end
        DRAIN: if (cnt == 0) begin irq <= 1'b1; st <= IDLE; end
        default: st <= IDLE;
      endcase
    end
endmodule''',

    'tb_dma': r'''
module tb;
  logic clk = 0, rst_n = 0, start = 0;
  always #5 clk = ~clk;
  logic busy, irq, err, mem_re, mem_we, tv, tl, tr;
  logic [7:0] maddr; logic [31:0] mwd, mrd, td;
  logic [31:0] mem [256];
  desc_dma dut (.clk, .rst_n, .start, .desc_base(8'h10), .busy, .irq, .err,
    .mem_re, .mem_we, .mem_addr(maddr), .mem_wdata(mwd), .mem_rdata(mrd),
    .m_tvalid(tv), .m_tlast(tl), .m_tdata(td), .m_tready(tr));
  always_ff @(posedge clk) begin                      // memory model, 1-cycle read
    if (mem_re) mrd <= mem[maddr];
    if (mem_we) mem[maddr] <= mwd;
  end
  int cyc = 0, beats = 0, t0, t_first, bp;
  always @(posedge clk) cyc <= cyc + 1;
  always @(posedge clk) if (tv && tr) begin
    beats++;
    if (beats == 1) t_first = cyc;
    $display("cyc %3d  beat %0d  tdata=%08h tlast=%0d", cyc - t0, beats, td, tl);
  end
  task automatic run(input int bp_pct);
    bp = bp_pct; beats = 0;
    // descriptor chain: 0x10 -> 0x20 -> 0x30   (OWN | EOP | EOC | LEN)
    mem[8'h10] = 32'h8000_0003; mem[8'h11] = 32'h40; mem[8'h12] = 32'h20;
    mem[8'h20] = 32'hC000_0002; mem[8'h21] = 32'h50; mem[8'h22] = 32'h30;
    mem[8'h30] = 32'hE000_0004; mem[8'h31] = 32'h60; mem[8'h32] = 32'h00;
    for (int i = 0; i < 16; i++) begin
      mem[8'h40 + i] = 32'hA000_0000 + i; mem[8'h50 + i] = 32'hB000_0000 + i;
      mem[8'h60 + i] = 32'hC000_0000 + i;
    end
    @(posedge clk); t0 = cyc + 1; start <= 1; @(posedge clk); start <= 0;
    @(posedge irq);
    $display("irq at cyc %0d err=%0d beats=%0d  desc word0 after: %08h %08h %08h",
             cyc - t0, err, beats, mem[8'h10], mem[8'h20], mem[8'h30]);
  endtask
  always @(posedge clk) tr <= ($urandom_range(99) >= bp);
  initial begin
    repeat (2) @(posedge clk); rst_n = 1;
    $display("--- run 1: sink always ready ---");       run(0);
    $display("--- run 2: sink ready 50%% of cycles ---"); run(50);
    $display("--- run 3: restart on a chain software has not handed back ---");
    start <= 1; @(posedge clk); start <= 0; @(posedge irq);
    $display("irq err=%0d (descriptor 0x10 has OWN=0)", err);
    $finish;
  end
endmodule''',

    'link': r'''
// CRC-8 (poly x^8+x^2+x+1 = 0x07, init 0x00, MSB first) packet link: TX appends the CRC,
// RX checks that the CRC over payload+CRC is zero and flags a timeout on a stalled packet.
function automatic logic [7:0] crc8_step(input logic [7:0] c, input logic [7:0] d);
  logic [7:0] x;
  x = c ^ d;
  for (int i = 0; i < 8; i++) x = x[7] ? ((x << 1) ^ 8'h07) : (x << 1);
  return x;
endfunction

module link_tx (
  input  logic clk, rst_n,
  input  logic s_valid, s_last, input logic [7:0] s_data, output logic s_ready,
  output logic m_valid, m_last, output logic [7:0] m_data
);
  logic [7:0] crc; logic send_crc;
  assign s_ready = !send_crc;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin crc <= 0; send_crc <= 0; m_valid <= 0; m_last <= 0; m_data <= 0; end
    else if (send_crc) begin                         // append FCS byte, end of packet
      m_valid <= 1; m_last <= 1; m_data <= crc; crc <= 0; send_crc <= 0;
    end else begin
      m_valid <= s_valid; m_last <= 0; m_data <= s_data;
      if (s_valid) begin crc <= crc8_step(crc, s_data); send_crc <= s_last; end
    end
endmodule

module link_rx #(parameter int TMO = 16) (
  input  logic clk, rst_n,
  input  logic valid, last, input logic [7:0] data,
  output logic done, crc_ok, timeout
);
  logic [7:0] crc; logic in_pkt; logic [7:0] idle;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      crc <= 0; in_pkt <= 0; idle <= 0; done <= 0; crc_ok <= 0; timeout <= 0;
    end
    else begin
      done <= 0; timeout <= 0;
      if (valid) begin
        idle <= 0;
        if (last) begin                              // residue over payload+FCS must be 0
          done <= 1; crc_ok <= (crc8_step(crc, data) == 0); crc <= 0; in_pkt <= 0;
        end
        else begin crc <= crc8_step(crc, data); in_pkt <= 1; end
      end else if (in_pkt) begin
        idle <= idle + 1;
        if (idle == TMO - 1) begin timeout <= 1; in_pkt <= 0; crc <= 0; idle <= 0; end
      end
    end
endmodule''',

    'tb_link': r'''
module tb;
  logic clk = 0, rst_n = 0; always #5 clk = ~clk;
  logic sv = 0, sl = 0, sr, tv, tl, rv, rl, done, ok, tmo;
  logic [7:0] sd, td, rd;
  link_tx tx (.clk, .rst_n, .s_valid(sv), .s_last(sl), .s_data(sd), .s_ready(sr),
              .m_valid(tv), .m_last(tl), .m_data(td));
  link_rx rx (.clk, .rst_n, .valid(rv), .last(rl), .data(rd), .done, .crc_ok(ok),
              .timeout(tmo));
  // ---------------- error injector on the wire (the "channel") ----------------
  typedef enum {NONE, BIT1, BURST8, MULTI, DROP} inj_t;
  inj_t kind; int pos, len, idx = 0; logic [7:0] crc_seen;
  bit [7:0] flip [32];                       // per-byte XOR pattern for this packet
  logic [7:0] cur_flip;
  always @* cur_flip = flip[idx];
  assign rd = td ^ cur_flip;
  assign rl = tl;
  assign rv = tv && !(kind == DROP && tl);             // DROP: lose the FCS byte
  always @(posedge clk) if (tv) idx <= tl ? 0 : idx + 1;
  // ---------------- monitor + scoreboard ----------------
  bit [7:0] p [$], got_q [$];
  int n_pkts, n_inj, n_det_crc, n_det_tmo, n_escape, n_false, n_good, logged;
  always @(posedge clk) if (rv && !rl) got_q.push_back(rd);
  function bit same();                       // received payload == sent payload?
    if (got_q.size() != p.size()) return 0;
    foreach (p[i]) if (got_q[i] != p[i]) return 0;
    return 1;
  endfunction
  task check();
    string res;
    do @(negedge clk); while (!(done || tmo));           // RX verdict for this packet
    if (tmo)          begin res = "TIMEOUT";   n_det_tmo++; end
    else if (!ok)     begin res = "CRC ERROR"; n_det_crc++; end
    else if (!same()) begin res = "SILENT CORRUPTION (CRC escape)"; n_escape++; end
    else              begin res = "ok"; n_good++; end
    if (kind == NONE && res != "ok") n_false++;
    if ((kind != NONE && logged < 5) || (kind != NONE && res == "ok")
        || res.substr(0, 0) == "S") begin
      logged++; $display("pkt %4d  inject=%-6s -> %s", n_pkts, kind.name(), res);
    end
    got_q.delete();
  endtask
  task send();
    for (int i = 0; i < p.size(); i++) begin
      sv <= 1; sd <= p[i]; sl <= (i == p.size() - 1); @(posedge clk);
    end
    sv <= 0; sl <= 0; @(posedge clk);                    // FCS cycle
  endtask
  initial begin
    int r, n;
    repeat (2) @(posedge clk); rst_n <= 1; @(posedge clk);
    // known-answer test: CRC-8 of ASCII "123456789" must be 0xF4 (CRC-8/SMBUS check value)
    p = '{"1","2","3","4","5","6","7","8","9"}; kind = NONE; foreach (flip[i]) flip[i] = 0;
    fork send(); begin wait (tv && tl); crc_seen = td; end join
    $display("KAT: CRC-8 of \"123456789\" = %02h (expected f4)", crc_seen);
    check(); n_good = 0; logged = 0; repeat (20) @(posedge clk);
    for (n_pkts = 0; n_pkts < 4000; n_pkts++) begin
      p.delete(); n = $urandom_range(16, 4);
      repeat (n) p.push_back($urandom);
      r = $urandom_range(99);
      kind = (r < 50) ? NONE : (r < 62) ? BIT1 : (r < 75) ? BURST8 : (r < 90) ? MULTI : DROP;
      foreach (flip[i]) flip[i] = 0;
      case (kind)
        BIT1:   begin
                  pos = $urandom_range(8 * (n + 1) - 1); flip[pos / 8] ^= 8'h80 >> (pos % 8);
                end
        BURST8: begin                         // up to 8 consecutive bits, ends are flipped
                  len = $urandom_range(8, 2); pos = $urandom_range(8 * (n + 1) - len);
                  for (int b = 0; b < len; b++)
                    if (b == 0 || b == len - 1 || $urandom_range(1))
                      flip[(pos + b) / 8] ^= 8'h80 >> ((pos + b) % 8);
                end
        MULTI:  repeat (3) flip[$urandom_range(n)] ^= $urandom_range(255, 1);
        default: ;
      endcase
      if (kind != NONE) n_inj++;
      fork send(); check(); join
      repeat (20) @(posedge clk);                        // idle gap > RX timeout
    end
    $display("packets=%0d injected=%0d | crc_err=%0d timeout=%0d escaped=%0d | %s",
             n_pkts, n_inj, n_det_crc, n_det_tmo, n_escape,
             $sformatf("ok=%0d false=%0d", n_good, n_false));
    $finish;
  end
endmodule''',

    'sva': r'''
// Protocol checker for a valid/ready (AXI-style) channel: bind it to any interface.
module vr_checker #(parameter int W = 8) (
  input logic clk, rst_n, valid, ready, input logic [W-1:0] data
);
  // once asserted, VALID must stay high until the handshake (AXI: no withdrawal)
  a_hold:   assert property (@(posedge clk) disable iff (!rst_n)
                             valid && !ready |=> valid)
            else $error("VALID dropped before READY");
  // payload must be stable while waiting
  a_stable: assert property (@(posedge clk) disable iff (!rst_n)
                             valid && !ready |=> $stable(data))
            else $error("DATA changed during a stall");
  // no X on VALID out of reset
  a_known:  assert property (@(posedge clk) disable iff (!rst_n) !$isunknown(valid));
  c_stall:  cover property  (@(posedge clk) disable iff (!rst_n) valid && !ready);
endmodule

// a deliberately buggy source that breaks both rules when it is stalled
module bad_src (input logic clk, rst_n, ready, output logic valid, output logic [7:0] data);
  logic [2:0] t;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin valid <= 0; data <= 0; t <= 0; end
    else begin
      t <= t + 1;
      if (!valid || ready) begin valid <= 1; data <= data + 1; end
      else if (t == 6)     data  <= data + 8'h10;       // BUG 1: payload changes in a stall
      else if (t == 3)     valid <= 1'b0;               // BUG 2: VALID withdrawn
    end
endmodule

module tb;
  logic clk = 0, rst_n = 0, ready, valid; logic [7:0] data;
  always #5 clk = ~clk;
  bad_src     src (.*);
  vr_checker  chk (.*);
  initial begin
    ready = 0;
    #12 rst_n = 1;
    repeat (20) begin @(negedge clk); ready = ($urandom_range(3) == 0); end
    $finish;
  end
endmodule''',

    'secded': r'''
// Extended Hamming SECDED(13,8): code bit 0 = overall parity, bits 1..12 = Hamming
// positions (parity at 1,2,4,8; data at 3,5,6,7,9,10,11,12).
module secded_enc (input logic [7:0] d, output logic [12:0] c);
  always @* begin
    c = '0;
    {c[12], c[11], c[10], c[9], c[7], c[6], c[5], c[3]} = d;
    c[1] = c[3] ^ c[5] ^ c[7] ^ c[9] ^ c[11];
    c[2] = c[3] ^ c[6] ^ c[7] ^ c[10] ^ c[11];
    c[4] = c[5] ^ c[6] ^ c[7] ^ c[12];
    c[8] = c[9] ^ c[10] ^ c[11] ^ c[12];
    c[0] = ^c[12:1];                                   // overall parity -> even weight
  end
endmodule

module secded_dec (input logic [12:0] c, output logic [7:0] d,
                   output logic ce, output logic ue);   // corrected / uncorrectable
  logic [3:0] s; logic odd; logic [12:0] f;
  always @* begin
    s = '0;
    for (int i = 1; i <= 12; i++) if (c[i]) s ^= 4'(i);  // syndrome = XOR of set positions
    odd = ^c;
    f = c;
    ce = odd;                                          // odd weight: one bit flipped
    ue = !odd && (s != 0);                             // even weight, bad syndrome: two bits
    if (odd && s <= 12) f[s] = ~f[s];                  // s == 0 -> the parity bit itself
    d = {f[12], f[11], f[10], f[9], f[7], f[6], f[5], f[3]};
  end
endmodule''',

    'tb_secded': r'''
module tb;
  logic [7:0] d, q; logic [12:0] c, r; logic ce, ue;
  secded_enc enc (.d, .c);
  secded_dec dec (.c(r), .d(q), .ce, .ue);
  int n [4], ok [4], det [4], silent [4];              // indexed by number of flipped bits
  task automatic apply(input int k, input logic [12:0] e);
    r = c ^ e; #1;
    n[k]++;
    if (ue)             det[k]++;                      // flagged uncorrectable
    else if (q == d)    ok[k]++;                       // clean or correctly corrected
    else                silent[k]++;                   // wrong data delivered as good
  endtask
  initial begin
    for (int v = 0; v < 256; v++) begin
      d = v; #1;
      apply(0, 0);
      for (int i = 0; i < 13; i++) begin
        apply(1, 13'(1) << i);
        for (int j = i + 1; j < 13; j++) begin
          apply(2, (13'(1) << i) | (13'(1) << j));
          for (int k = j + 1; k < 13; k++)
            apply(3, (13'(1) << i) | (13'(1) << j) | (13'(1) << k));
        end
      end
    end
    for (int k = 0; k < 4; k++)
      $display("%0d-bit errors: %6d cases  correct data=%6d  flagged UE=%6d  silent bad=%6d",
               k, n[k], ok[k], det[k], silent[k]);
  end
endmodule''',

    'crc_exp': r'''
# Inject random and burst errors into CRC-protected frames; count what gets through.
import random, zlib

def make_crc8_table(poly=0x07):                 # CRC-8, MSB first, init 0x00 (CRC-8/SMBUS)
    t = []
    for b in range(256):
        c = b
        for _ in range(8):
            c = ((c << 1) ^ poly) & 0xFF if c & 0x80 else (c << 1) & 0xFF
        t.append(c)
    return t
T8 = make_crc8_table()

def crc8(data):
    c = 0
    for b in data:
        c = T8[c ^ b]
    return c

CRCS = {"CRC-8 ": (crc8, 1),                     # (function, FCS bytes)
        "CRC-32": (lambda d: zlib.crc32(d), 4)}  # IEEE 802.3 CRC-32
assert crc8(b"123456789") == 0xF4 and zlib.crc32(b"123456789") == 0xCBF43926

def frame(payload, name):
    f, n = CRCS[name]
    return payload + f(payload).to_bytes(n, "big")

def detected(rx, name):
    f, n = CRCS[name]
    return f(rx[:-n]) != int.from_bytes(rx[-n:], "big")

def corrupt(fr, kind, rng):
    nbits = 8 * len(fr)
    v = int.from_bytes(fr, "big")
    if kind[0] == "rand":                       # k independent random bit flips
        for pos in rng.sample(range(nbits), kind[1]):
            v ^= 1 << pos
    elif kind[0] == "burst":                    # burst of length L: both ends flipped
        L = kind[1]
        s = rng.randrange(nbits - L + 1)
        pat = (1 << (L - 1)) | 1 | (rng.getrandbits(L) if L > 2 else 0)
        v ^= (pat & ((1 << L) - 1)) << s
    else:                                       # whole frame replaced by garbage
        v = rng.getrandbits(nbits)
    return v.to_bytes(len(fr), "big")

rng = random.Random(2026)
TRIALS, PAYLOAD = 100000, 64
kinds = [("rand", 1), ("rand", 2), ("rand", 3), ("rand", 4), ("burst", 8), ("burst", 9),
         ("burst", 16), ("burst", 32), ("burst", 33), ("burst", 64), ("garbage", 0)]
print("%d trials per row, %d-byte payload + FCS (undetected / trials)" % (TRIALS, PAYLOAD))
print("%-14s %-22s %-22s" % ("error pattern", "CRC-8 (0x07)", "CRC-32 (802.3)"))
for kind in kinds:
    row = []
    for name in CRCS:
        miss = 0
        for _ in range(TRIALS):
            p = rng.randbytes(PAYLOAD)
            fr = frame(p, name)
            rx = corrupt(fr, kind, rng)
            if rx != fr and not detected(rx, name):
                miss += 1
        row.append("%5d  (%.2e)" % (miss, miss / TRIALS))
    label = "%d random bits" % kind[1] if kind[0] == "rand" else \
            "burst L=%d" % kind[1] if kind[0] == "burst" else "garbage frame"
    print("%-14s %-22s %-22s" % (label, row[0], row[1]))

# Exhaustive: 2-bit errors x^i + x^j escape iff g(x) divides x^(j-i) + 1
def pmod(a, g):
    dg = g.bit_length() - 1
    while a.bit_length() - 1 >= dg:
        a ^= g << (a.bit_length() - 1 - dg)
    return a
G8 = 0x107
order = next(d for d in range(1, 1000) if pmod((1 << d) | 1, G8) == 0)
print("CRC-8 0x07: smallest d with x^d = 1 mod g(x) is %d -> two flips %d bits apart escape"
      % (order, order))
for nb in (8, 16, 64):
    n = 8 * (nb + 1)
    bad = sum(n - d for d in range(1, n) if pmod((1 << d) | 1, G8) == 0)
    print("  %2d-byte payload: %6d of %7d two-bit patterns undetected"
          % (nb, bad, n * (n - 1) // 2))''',

    'bw': r'''
# DDR bandwidth budget for an edge-AI camera SoC (all rates in MB/s, 1 MB = 1e6 bytes)
W, H, FPS = 3840, 2160, 30
raw_bits = 12
nv12 = W * H * 1.5                                   # bytes per NV12 (YUV 4:2:0) frame

# 1) MIPI CSI-2 link from the sensor (RAW12, ~20% blanking + packet overhead assumed)
payload_gbps = W * H * FPS * raw_bits / 1e9
line_gbps = payload_gbps * 1.20
for lanes in (2, 4):
    print("CSI-2 RAW12 4K30: %.2f Gb/s payload, %.2f Gb/s on wire -> %d lanes x %.2f Gb/s"
          % (payload_gbps, line_gbps, lanes, line_gbps / lanes))

# 2) DDR clients: (name, read MB/s, write MB/s)
clients = [
    ("ISP out (NV12 4K30)",            0,                     nv12 * FPS),
    ("ISP 3DNR ref (rd+wr)",           nv12 * FPS,            nv12 * FPS),
    ("Scaler -> NPU input 640x640x3",  W * H * 1.5 * FPS,     640 * 640 * 3 * FPS),
    ("NPU weights 12 MB/frame",        12e6 * FPS,            0),
    ("NPU activation spill 20 MB/fr",  20e6 * FPS,            20e6 * FPS),
    ("H.265 enc (cur + 2 refs, recon)", 3 * nv12 * FPS,       nv12 * FPS),
    ("Display 1080p60 ARGB8888",       1920 * 1080 * 4 * 60,  0),
    ("CPU cluster + OS (allowance)",   800e6,                 400e6),
    ("Ethernet/USB/PCIe DMA",          150e6,                 150e6),
]
tot_r = sum(c[1] for c in clients); tot_w = sum(c[2] for c in clients)
print("%-34s %9s %9s" % ("client", "read", "write"))
for n, r, w in clients:
    print("%-34s %9.0f %9.0f" % (n, r / 1e6, w / 1e6))
print("%-34s %9.0f %9.0f   total %.0f MB/s" % ("SUM", tot_r / 1e6, tot_w / 1e6,
                                               (tot_r + tot_w) / 1e6))
# 3) Compare with DRAM options at a realistic efficiency
for name, mts, bits in (("LPDDR4X-4266 x32", 4266, 32), ("LPDDR5-6400 x32", 6400, 32),
                        ("LPDDR5X-8533 x32", 8533, 32)):
    peak = mts * 1e6 * bits / 8
    for eff in (0.65, 0.75):
        use = (tot_r + tot_w) / (peak * eff)
        print("%-17s peak %6.0f MB/s  eff %.0f%% -> usable %6.0f MB/s  load %4.0f%%"
              % (name, peak / 1e6, eff * 100, peak * eff / 1e6, use * 100))''',

}

OUT = {
    'dma': ['--- run 1: sink always ready ---', 'cyc   7  beat 1  tdata=a0000000 tlast=0', 'cyc   8  beat 2  tdata=a0000001 tlast=0', 'cyc   9  beat 3  tdata=a0000002 tlast=0', 'cyc  17  beat 4  tdata=b0000000 tlast=0', 'cyc  18  beat 5  tdata=b0000001 tlast=1', 'cyc  26  beat 6  tdata=c0000000 tlast=0', 'cyc  27  beat 7  tdata=c0000001 tlast=0', 'cyc  28  beat 8  tdata=c0000002 tlast=0', 'cyc  29  beat 9  tdata=c0000003 tlast=1', 'irq at cyc 32 err=0 beats=9  desc word0 after: 00000003 40000002 60000004', '--- run 2: sink ready 50% of cycles ---', 'cyc   9  beat 1  tdata=a0000000 tlast=0', 'cyc  11  beat 2  tdata=a0000001 tlast=0', 'cyc  12  beat 3  tdata=a0000002 tlast=0', 'cyc  17  beat 4  tdata=b0000000 tlast=0', 'cyc  19  beat 5  tdata=b0000001 tlast=1', 'cyc  26  beat 6  tdata=c0000000 tlast=0', 'cyc  29  beat 7  tdata=c0000001 tlast=0', 'cyc  30  beat 8  tdata=c0000002 tlast=0', 'cyc  32  beat 9  tdata=c0000003 tlast=1', 'irq at cyc 34 err=0 beats=9  desc word0 after: 00000003 40000002 60000004', '--- run 3: restart on a chain software has not handed back ---', 'irq err=1 (descriptor 0x10 has OWN=0)'],
    'link': ['KAT: CRC-8 of "123456789" = f4 (expected f4)', 'pkt    0  inject=BURST8 -> CRC ERROR', 'pkt    2  inject=BIT1   -> CRC ERROR', 'pkt    3  inject=MULTI  -> CRC ERROR', 'pkt    4  inject=DROP   -> TIMEOUT', 'pkt    6  inject=DROP   -> TIMEOUT', 'pkt  434  inject=MULTI  -> SILENT CORRUPTION (CRC escape)', 'pkt 2865  inject=MULTI  -> SILENT CORRUPTION (CRC escape)', 'pkt 3066  inject=MULTI  -> SILENT CORRUPTION (CRC escape)', 'packets=4000 injected=2022 | crc_err=1671 timeout=348 escaped=3 | ok=1978 false=0'],
    'sva': ['[55] %Error: sva.sv:8: Assertion failed in TOP.tb.chk.a_hold: VALID dropped before READY', '-Info: sva.sv:8: Verilog $stop, ignored due to +verilator+error+limit', '[135] %Error: sva.sv:8: Assertion failed in TOP.tb.chk.a_hold: VALID dropped before READY', '-Info: sva.sv:8: Verilog $stop, ignored due to +verilator+error+limit', '[165] %Error: sva.sv:12: Assertion failed in TOP.tb.chk.a_stable: DATA changed during a stall', '-Info: sva.sv:12: Verilog $stop, ignored due to +verilator+error+limit'],
    'secded': ['0-bit errors:    256 cases  correct data=   256  flagged UE=     0  silent bad=     0', '1-bit errors:   3328 cases  correct data=  3328  flagged UE=     0  silent bad=     0', '2-bit errors:  19968 cases  correct data=     0  flagged UE= 19968  silent bad=     0', '3-bit errors:  73216 cases  correct data=   512  flagged UE=     0  silent bad= 72704'],
    'crc_exp': ['100000 trials per row, 64-byte payload + FCS (undetected / trials)', 'error pattern  CRC-8 (0x07)           CRC-32 (802.3)        ', '1 random bits      0  (0.00e+00)          0  (0.00e+00)     ', '2 random bits    554  (5.54e-03)          0  (0.00e+00)     ', '3 random bits      0  (0.00e+00)          0  (0.00e+00)     ', '4 random bits    789  (7.89e-03)          0  (0.00e+00)     ', 'burst L=8          0  (0.00e+00)          0  (0.00e+00)     ', 'burst L=9        787  (7.87e-03)          0  (0.00e+00)     ', 'burst L=16       390  (3.90e-03)          0  (0.00e+00)     ', 'burst L=32       378  (3.78e-03)          0  (0.00e+00)     ', 'burst L=33       449  (4.49e-03)          0  (0.00e+00)     ', 'burst L=64       383  (3.83e-03)          0  (0.00e+00)     ', 'garbage frame    403  (4.03e-03)          0  (0.00e+00)     ', 'CRC-8 0x07: smallest d with x^d = 1 mod g(x) is 127 -> two flips 127 bits apart escape', '   8-byte payload:      0 of    2556 two-bit patterns undetected', '  16-byte payload:      9 of    9180 two-bit patterns undetected', '  64-byte payload:    810 of  134940 two-bit patterns undetected'],
    'bw': ['CSI-2 RAW12 4K30: 2.99 Gb/s payload, 3.58 Gb/s on wire -> 2 lanes x 1.79 Gb/s', 'CSI-2 RAW12 4K30: 2.99 Gb/s payload, 3.58 Gb/s on wire -> 4 lanes x 0.90 Gb/s', 'client                                  read     write', 'ISP out (NV12 4K30)                        0       373', 'ISP 3DNR ref (rd+wr)                     373       373', 'Scaler -> NPU input 640x640x3            373        37', 'NPU weights 12 MB/frame                  360         0', 'NPU activation spill 20 MB/fr            600       600', 'H.265 enc (cur + 2 refs, recon)         1120       373', 'Display 1080p60 ARGB8888                 498         0', 'CPU cluster + OS (allowance)             800       400', 'Ethernet/USB/PCIe DMA                    150       150', 'SUM                                     4274      2307   total 6581 MB/s', 'LPDDR4X-4266 x32  peak  17064 MB/s  eff 65% -> usable  11092 MB/s  load   59%', 'LPDDR4X-4266 x32  peak  17064 MB/s  eff 75% -> usable  12798 MB/s  load   51%', 'LPDDR5-6400 x32   peak  25600 MB/s  eff 65% -> usable  16640 MB/s  load   40%', 'LPDDR5-6400 x32   peak  25600 MB/s  eff 75% -> usable  19200 MB/s  load   34%', 'LPDDR5X-8533 x32  peak  34132 MB/s  eff 65% -> usable  22186 MB/s  load   30%', 'LPDDR5X-8533 x32  peak  34132 MB/s  eff 75% -> usable  25599 MB/s  load   26%'],
}



def _v(name, caption=None):
    """Show a verified source from SRC."""
    code(SRC[name].split("\n"), caption)


def _o(name, caption=None):
    """Show the real output captured for a run."""
    out(OUT[name], caption)


# =============================================================================
#                   PART V - DESIGNING WITH PROTOCOLS
# =============================================================================
def part5():
    part("Designing With Protocols",
         "Parts II to IV studied protocols one at a time. Real projects never "
         "meet a protocol alone: a USB, Ethernet or PCIe port is a controller "
         "with registers, DMA, buffers, several clock domains and a PHY "
         "behind a pad ring; it must be verified against a specification, "
         "certified by a standards body and made reliable, safe and secure; "
         "and it must be chosen and budgeted against every other interface "
         "on the chip. This final part is about those engineering skills - "
         "the architecture of a controller and its PHY integration, protocol "
         "verification from assertions to plugfests, reliability and "
         "security on links, and how to pick, size and budget the protocols "
         "of a whole SoC. It closes with a learning roadmap.")
    _ch24()
    _ch25()
    _ch26()
    _ch27()


# ---------------------------------------------------------------- Ch 24 ---
def _ch24():
    chapter("Architecture of a Protocol Controller and PHY Integration",
            newpage=False)
    p("Open the block diagram of any interface IP - a USB device "
      "controller, an Ethernet MAC, a PCIe endpoint, an eMMC host, a MIPI "
      "CSI-2 receiver - and you find the same skeleton. On one side is the "
      "SoC: an AXI or AHB port for register access and another for DMA. On "
      "the other side is the pin: a PHY that turns bits into volts. In "
      "between sit the same half-dozen layers, whatever the protocol. "
      "Learn the skeleton once and every new interface becomes a variation "
      "on a theme; you also learn where the integration bugs live, because "
      "they live at the seams between those layers.")

    h2("The layered controller")
    diagram([
        "              SoC side                                         pin side",
        "  +----------------------------------------------------------------------+",
        "  | CPU/IC  --AXI/APB slave-->  [ CSR block ]  --> IRQ to GIC/PLIC         |",
        "  |                                  |  ctrl/status                        |",
        "  | DDR  <--AXI master-- [ DMA engine + descriptor fetch/write-back ]      |",
        "  |                                  |  data                               |",
        "  |                          [ TX / RX FIFOs, packet buffers ]  <- CDC     |",
        "  |                                  |                                     |",
        "  |                   [ protocol / link-layer engine ]  FSMs, CRC, retry   |",
        "  |                                  |                                     |",
        "  |                   [ PCS: encode, scramble, align, deskew ]             |",
        "  +----------------------------------|-------------------------------------+",
        "            standard PHY interface:  PIPE / DFI / UTMI / xMII / PPI",
        "  +----------------------------------|-------------------------------------+",
        "  | PHY: PMA SerDes/driver/receiver, PLL, CDR, calibration  (mixed-signal) |",
        "  +----------------------------------|-------------------------------------+",
        "                                 IO pads / bumps / balls"],
        "The universal skeleton of a protocol controller. Clock-domain "
        "crossings usually sit at the FIFOs (bus clock vs. link clock) and at "
        "the PHY interface (link clock vs. PHY-recovered clock).")
    tbl(["Layer", "Job", "Typical implementation", "Owner"],
        [["Host/bus interface", "Register access; DMA master port",
          "AXI4-Lite/APB slave, AXI4 master (Ch 5-8)", "RTL + SoC integration"],
         ["CSRs", "Configuration, status, interrupts, counters",
          "Generated from IP-XACT/SystemRDL", "RTL + firmware"],
         ["DMA engine", "Move payload between memory and FIFOs",
          "Descriptor rings/lists, scatter-gather", "RTL + driver"],
         ["Buffers / FIFOs", "Rate matching, CDC, retry storage, jitter "
          "absorption", "SRAM macros, async FIFOs", "RTL + PD (SRAM)"],
         ["Protocol / link engine", "Framing, handshakes, ACK/NAK, CRC, "
          "flow control, state machines", "FSMs, CRC units, timers",
          "RTL (the protocol expert)"],
         ["PCS", "Line coding, scrambling, lane alignment, deskew, "
          "elastic buffers", "8b/10b, 64b/66b, 128b/130b logic", "RTL / PHY"],
         ["PHY (PMA + analog)", "Serialize, drive, equalize, recover clock",
          "Hard macro from a PHY vendor", "Analog/PHY team or vendor"]],
        widths=[18, 30, 32, 20], bold_first=True)
    p("The split is not arbitrary. Everything above the PCS runs at a "
      "**parallel** clock of a few hundred MHz and is ordinary synthesizable "
      "RTL. The PCS may run at the same clock with a wide datapath (for "
      "example 32 or 64 bits per lane). The PMA runs at the **line rate** - "
      "gigahertz - and is custom analog and high-speed digital design that "
      "only a PHY team can build and characterize. The standard PHY "
      "interfaces exist precisely so that the two sides can come from "
      "different teams or companies.")

    h2("The host interface and the register block")
    p("Software sees a controller only through its registers, so the CSR "
      "block is the controller's user interface. A representative map for a "
      "generic packet controller:")
    tbl(["Offset", "Register", "Access", "Contents"],
        [["0x000", "ID / VERSION", "RO", "IP identifier and revision - lets "
          "one driver support several versions"],
         ["0x004", "CTRL", "RW", "Enable, soft reset, loopback, mode bits"],
         ["0x008", "STATUS", "RO", "Link up, speed, FIFO levels, busy"],
         ["0x00C", "INT_STATUS", "RW1C", "Event bits: RX done, TX done, error; "
          "write 1 to clear"],
         ["0x010", "INT_ENABLE", "RW", "Mask for each INT_STATUS bit"],
         ["0x020", "TX_DESC_BASE / RX_DESC_BASE", "RW", "Ring base addresses "
          "(64-bit: LO/HI pair)"],
         ["0x028", "TX_TAIL (doorbell)", "WO", "Software writes the index of "
          "the last valid descriptor"],
         ["0x02C", "TX_HEAD", "RO", "Hardware's current position"],
         ["0x100+", "Counters", "RO/RC", "Good/bad frames, CRC errors, drops, "
          "retries"]],
        widths=[10, 26, 10, 54], bold_first=False,
        caption="A typical controller register map. The exact layout is "
                "yours to define; the kinds of registers recur in every IP.")
    box("warn", "PITFALL: status and interrupt register races",
        "Classic CSR bugs: (1) a W1C bit that is set by hardware in the same "
        "cycle software writes 1 to clear it - hardware must win, or the "
        "event is lost; (2) read-to-clear counters that are cleared by a "
        "debugger's memory view; (3) 64-bit registers read as two 32-bit "
        "halves while the counter carries between the reads (latch the high "
        "half when the low half is read); (4) a doorbell register that is "
        "posted through a write buffer and overtakes the descriptor write it "
        "announces. Specify the behaviour of each case explicitly and check "
        "it in the testbench.")

    h2("DMA engines and descriptors")
    p("Any interface faster than a few Mb/s moves data by **DMA**: software "
      "prepares buffers in memory and describes them with **descriptors**; "
      "the controller fetches descriptors, moves the data and writes the "
      "descriptors back with status. The two common organizations:")
    diagram([
        "  Descriptor RING (NICs, USB xHCI, NVMe)       Linked LIST (many SoC DMAs)",
        "                                                ",
        "   base -> [d0][d1][d2][d3][d4][d5][d6][d7]      desc_base",
        "              ^HEAD (HW)     ^TAIL (SW)            |",
        "   HW consumes HEAD..TAIL-1, advances HEAD          v",
        "   SW fills at TAIL, writes TAIL doorbell         [ctrl|len|buf|next]--+",
        "   index wraps modulo ring size                                         v",
        "                                                  [ctrl|len|buf|next]--+",
        "   ownership: HEAD/TAIL indices or an                                   v",
        "   OWN bit in each descriptor                     [ctrl|len|buf|EOC ]"],
        "Rings suit continuous streams with a fixed pool of buffers; linked "
        "lists suit scatter-gather transfers of arbitrary shape.")
    p("Every descriptor format answers the same questions: **where** is the "
      "buffer (address, possibly 64-bit), **how long** it is, **what to do** "
      "(end of packet, interrupt on completion, checksum offload, "
      "timestamp) and **who owns it** now. Ownership is the heart of the "
      "protocol between hardware and software: software sets OWN=1 after it "
      "has fully written the descriptor, hardware clears it when it is done, "
      "and neither side touches a descriptor the other owns.")
    bul(["**Ordering.** The driver must write the descriptor, then a memory "
         "barrier (`dma_wmb()`/`wmb()` in Linux, `DSB` on Arm), then the "
         "doorbell. Hardware must write the data and status, then clear OWN "
         "(or advance HEAD), then raise the interrupt - in that order as "
         "seen by the CPU.",
         "**Coherency.** If the DMA port is not I/O-coherent (no ACE-Lite or "
         "CHI snooping, Chapter 9), the driver must clean the cache before a "
         "TX DMA and invalidate it before reading RX data. A missing "
         "invalidate returns stale data only sometimes - a notorious "
         "heisenbug.",
         "**Descriptor prefetch.** Fetching a descriptor costs one memory "
         "round-trip - often hundreds of nanoseconds behind an interconnect. "
         "High-rate engines prefetch several descriptors ahead and write "
         "back status in batches.",
         "**Scatter-gather.** One packet may span several buffers (a header "
         "buffer plus page-sized payload buffers); the end-of-packet flag "
         "marks where the frame ends, which on a stream interface becomes "
         "`TLAST` (Chapter 8)."])

    h2("Buffers, FIFOs and how big they must be")
    p("Buffers exist for four reasons, and each gives a sizing rule:")
    tbl(["Reason", "Sizing rule", "Example"],
        [["**Round-trip latency** (credits, pause, ACK)",
          "depth >= bandwidth x round-trip time", "PCIe replay buffer, "
          "Ethernet RX FIFO covering PAUSE reaction"],
         ["**Burst absorption** (producer bursts, consumer steady)",
          "depth >= burst x (1 - r_out / r_in)", "Camera line bursts into a "
          "slower bus"],
         ["**Latency jitter** (memory busy for a while)",
          "depth >= rate x worst-case stall", "Display FIFO riding out a "
          "DDR refresh or a bank conflict"],
         ["**Whole-packet storage**", "depth >= max packet (store and "
          "forward)", "MAC TX: checksum insertion, cut-through not "
          "allowed"]],
        widths=[30, 30, 40])
    eq(["Credit / round-trip sizing (the bandwidth-delay product):",
        "   depth_bytes >= BW_bytes_per_s x RTT_s",
        "",
        "Example: a link carrying 4 GB/s whose flow-control round trip is 500 ns",
        "   depth >= 4e9 x 500e-9 = 2000 bytes   -> round up, e.g. 2 KB + one max packet",
        "",
        "Jitter example: display reads 1920x1080x4 B at 60 Hz = 498 MB/s; DDR may stall",
        "the reader for 5 us (refresh + contention):",
        "   depth >= 498e6 x 5e-6 = 2490 bytes   -> e.g. 4 KB line buffer"],
        "If the buffer is smaller than bandwidth x round-trip, the link "
        "stalls waiting for credits and never reaches full rate.")
    p("Credit-based flow control (PCIe, CXL, UCIe, AXI-Stream bridges, NoCs) "
      "makes the rule explicit: the receiver advertises how much buffer it "
      "has, the transmitter decrements a counter for each unit sent, and the "
      "receiver returns credits as it frees space. With too few credits the "
      "transmitter idles during every round trip; with too many the "
      "receiver's SRAM is wasted. The worked example at the end of this "
      "chapter uses the same idea in miniature: the DMA engine issues a "
      "memory read only when its FIFO has room for the returning data, "
      "counting reads still in flight - a local credit loop.")
    box("tip", "Buffer size is a system decision",
        "Buffers are usually the largest area in a controller (a 10G MAC "
        "with jumbo-frame support, a PCIe controller with a replay buffer and "
        "receive queues). Size them from the worst-case round trip at the "
        "highest rate you must sustain, add one maximum packet, and state the "
        "assumption in the spec - then let the architect trade SRAM against "
        "performance explicitly.")

    h2("The protocol engine and the PCS")
    p("The protocol engine is where the chapters of Parts III and IV live: "
      "the USB token/data/handshake sequencer, the Ethernet MAC's framing, "
      "CRC and inter-frame gap, the PCIe transaction and data-link layers "
      "with their sequence numbers, ACK/NAK and replay buffer, the I2C "
      "master's START/STOP/arbitration logic. It is FSM-heavy, full of "
      "timers (timeouts, inter-packet gaps, retry intervals) and counters, "
      "and it is where most protocol bugs are found. Keep it separate from "
      "the DMA and buffer logic so it can be verified with protocol VIP "
      "alone.")
    p("Below it, the **physical coding sublayer (PCS)** handles line coding "
      "(8b/10b, 64b/66b, 128b/130b), scrambling, block/symbol alignment, "
      "multi-lane deskew and the **elastic buffer** that absorbs the ppm "
      "difference between the recovered receive clock and the local clock by "
      "inserting or deleting SKP/idle symbols (Chapter 2). Depending on the "
      "PHY interface, the PCS is either in the controller (PIPE 'SerDes "
      "architecture', where the PHY delivers raw parallel symbols) or in "
      "the PHY (original PIPE, where the PHY does 8b/10b and the elastic "
      "buffer).")

    h2("Standard PHY interfaces")
    tbl(["Interface", "Protocols", "What crosses it", "Notes"],
        [["**PIPE** (PHY Interface for PCI Express, SATA, USB, DisplayPort "
          "and USB4)", "PCIe, USB 3.x, SATA, DP, USB4",
          "Parallel data per lane (8-64 bits), K/control indicators, "
          "power-state and rate controls, RX status", "Intel-published; "
          "recent versions use a SerDes (raw data) mode and a message bus"],
         ["**DFI** (DDR PHY Interface)", "DDR3/4/5, LPDDR4/5",
          "Command/address, write data + mask, read data valid, "
          "training/update handshakes", "Frequency ratios 1:1, 1:2, 1:4 "
          "between controller and PHY clocks (Ch 20)"],
         ["**UTMI / UTMI+ / ULPI**", "USB 2.0", "8/16-bit data at 60/30 MHz, "
          "line state, op-mode, termination control", "ULPI is a 12-pin "
          "reduced interface to an external PHY"],
         ["**xMII**: MII, RMII, GMII, RGMII, SGMII, XGMII, USXGMII",
          "Ethernet", "Nibble/byte/word data + enable/error, or a SerDes",
          "MDIO/MDC for PHY management (Ch 16, 19)"],
         ["**PPI** (PHY Protocol Interface)", "MIPI CSI-2/DSI over D-PHY/"
          "C-PHY", "Byte/word per lane, HS/LP mode controls, escape mode",
          "Defined in the D-PHY/C-PHY specs"],
         ["**RDI / FDI**", "UCIe", "Raw or flit-aware die-to-die data "
          "between adapter and PHY/protocol layer", "Chapter 22"]],
        widths=[25, 18, 33, 24], bold_first=False)
    box("key", "Why standard PHY interfaces matter",
        "They let you buy a PHY hard macro from one vendor, a controller from "
        "another (or write it yourself), and integrate them with predictable "
        "effort. They also define the verification boundary: a controller "
        "can be verified against a PIPE/DFI/UTMI bus-functional model of the "
        "PHY long before the analog macro exists.")

    h2("Clock domains and CDC points")
    p("A controller rarely lives in one clock domain. A typical high-speed "
      "controller has at least three:")
    diagram([
        "  bus clock (200-400 MHz)     link/core clock (from PHY PLL)    PHY clocks",
        "  +----------------------+    +-------------------------------+  +-----------+",
        "  | AXI slave, CSRs,     |    | protocol engine, PCS,         |  | TX serial |",
        "  | DMA master           |    | CRC, retry, timers            |  | RX (CDR)  |",
        "  |   [async FIFO] <=====|====|=> [packet buffers]            |  |           |",
        "  |   CSR --[2FF / hshk]-|----|-> config (quasi-static)       |  |           |",
        "  |   IRQ <-[pulse sync]-|----|-- events                      |  |           |",
        "  |                      |    |   [elastic buffer] <==========|==|= rx_clk   |",
        "  +----------------------+    +-------------------------------+  +-----------+",
        "  aux clock (always-on, e.g. 32 kHz or ref clk): wake-up, low-power FSMs"],
        "CDC points of a typical controller: data through async FIFOs, "
        "control through synchronizers or handshakes, receive data through "
        "the PCS elastic buffer.")
    bul(["**Bus clock**: the SoC interconnect frequency - chosen by the SoC, "
         "not the protocol.",
         "**Link/core clock**: derived from the PHY PLL, e.g. line rate / "
         "datapath width (PCIe Gen4 at 16 GT/s with a 32-bit PIPE datapath "
         "and 128b/130b encoding runs around 500 MHz per lane).",
         "**Recovered receive clock**: from the CDR; same nominal frequency "
         "as the local clock but plesiochronous (up to a few hundred ppm "
         "apart), so the elastic buffer is mandatory.",
         "**Aux/always-on clock**: keeps wake-up detection alive while the "
         "main PLL is off (USB suspend, PCIe L1/L2, Ethernet energy-efficient "
         "idle)."])
    box("warn", "PITFALL: configuration registers crossing domains",
        "A 32-bit control register written in the bus domain and used "
        "directly in the link domain is a multi-bit CDC bug: during the "
        "update the link logic can see a mixture of old and new bits. Either "
        "declare such fields 'static' (only written while the link is "
        "disabled, documented and checked by an assertion) or transfer them "
        "with a handshake/MCP synchronizer. CDC tools will flag the crossing; "
        "the waiver must say which rule makes it safe.")

    h2("Reset, power-up and PHY bring-up sequencing")
    p("A PHY is not ready the moment reset is released. Its PLL must lock, "
      "its termination and drive strength must be **calibrated** against a "
      "precision resistor or a reference, its receivers may need offset "
      "calibration, and only then can the link-training state machine "
      "start. The controller and the firmware must follow the sequence the "
      "PHY data book specifies - a common source of 'link does not come "
      "up' bugs.")
    diagram([
        "  power good -> ref clock stable -> PHY reset released",
        "      |",
        "      v",
        "  PHY PLL locking ........ wait for pll_lock (typically tens of us)",
        "      |",
        "      v",
        "  calibration ............ impedance/termination, RX offset, (DDR: ZQ cal)",
        "      |                    wait for cal_done / phy_ready / PhyStatus",
        "      v",
        "  controller reset released (link/core clock now valid and stable)",
        "      |",
        "      v",
        "  firmware: program CSRs (mode, speed, buffers, descriptors) -> enable",
        "      |",
        "      v",
        "  link training / initialization: e.g. PCIe LTSSM Detect->Polling->Config->L0,",
        "  USB chirp / LFPS + training, Ethernet auto-negotiation, DDR write leveling",
        "      |",
        "      v",
        "  link up -> STATUS.link_up, interrupt -> data traffic"],
        "A generic bring-up sequence. The real one is in the PHY data book "
        "and the controller's programming guide; the order matters.")
    bul(["Hold the controller's link-domain logic in reset until the clock "
         "it runs on is stable - a PHY-generated clock that is still locking "
         "can glitch.",
         "Reset each clock domain with its own synchronized reset (reset "
         "synchronizer per domain), and define what a **soft reset** from the "
         "CSR resets (usually the link and DMA state, not the CSRs "
         "themselves).",
         "Low-power states reverse the sequence: stop traffic, drain DMA, "
         "enter the protocol low-power state (USB suspend/U3, PCIe L1, EEE "
         "LPI), gate clocks, possibly power down the PHY PLL, and keep the "
         "wake-up detector on the aux clock."])

    h2("Interrupts")
    p("Interrupts connect the controller's events to software. Good practice:")
    bul(["One **INT_STATUS** register with W1C event bits, an **INT_ENABLE** "
         "mask and a single level-sensitive output that is the OR of enabled "
         "pending bits. Level-sensitive lines do not lose events if software "
         "is slow; edge/pulse interrupts do.",
         "**Interrupt coalescing / moderation**: at millions of packets per "
         "second one interrupt per packet overwhelms the CPU. Raise the "
         "interrupt after N completions or T microseconds, whichever comes "
         "first (NICs, USB xHCI, NVMe all do this).",
         "**Message-signalled interrupts** (PCIe MSI/MSI-X, Arm GIC LPIs via "
         "ITS) are memory writes; they are ordered behind the data writes on "
         "the same path, which removes a whole class of races.",
         "Error interrupts (CRC errors, timeouts, overflows) usually go to a "
         "separate vector or a RAS/safety controller (Chapter 26)."])

    h2("Firmware and driver interaction")
    p("A controller is only as good as the programming model it gives "
      "software. The driver writer's view of the DMA controller built later "
      "in this chapter looks like this:")
    code([
        "// transmit one packet made of two buffers (pseudo-C driver code)",
        "d = &ring[tail];",
        "d[0].buf = hdr_dma;  d[0].len = 64;   d[0].ctrl = OWN;",
        "d[1].buf = pay_dma;  d[1].len = 1400; d[1].ctrl = OWN | EOP | IRQ;",
        "dma_wmb();                         // descriptors visible before doorbell",
        "writel(tail + 2, base + TX_TAIL);  // doorbell (posted write)",
        "...",
        "// interrupt handler",
        "st = readl(base + INT_STATUS);",
        "writel(st, base + INT_STATUS);     // W1C: acknowledge what we saw",
        "while (!(ring[head].ctrl & OWN)) { reclaim(head); head = next(head); }"],
        "The software half of the descriptor protocol. The barrier and the "
        "ownership check are the parts that break when the hardware gets the "
        "ordering wrong.")
    bul(["Provide an **ID/version register** and capability registers so one "
         "driver can handle several configurations of the IP.",
         "Make every error **observable** (sticky status bits, counters, the "
         "descriptor that failed) - post-silicon debug depends on it.",
         "Avoid registers that must be written in a magic order or within a "
         "time window; if unavoidable, document it in the programming guide "
         "and enforce it in hardware where possible.",
         "Deliver a **reference driver** or bare-metal test with the IP; the "
         "firmware team will use it for bring-up and the DV team can run it "
         "on an emulator."])

    h2("IP selection: build or buy, hard or soft")
    tbl(["Decision", "Build it yourself when...", "Buy (license) it when..."],
        [["Controller", "Simple protocol (UART, SPI, I2C, APB/AXI peripherals), "
          "differentiation matters, or you need unusual features",
          "Complex, spec-heavy protocols (USB 3.x/4, PCIe, CXL, DDR, "
          "HDMI/DP, MIPI CSI-2/DSI) where compliance history is worth more "
          "than license fees"],
         ["PHY", "Almost never for high-speed SerDes unless you are a PHY "
          "company; simple GPIO-based PHYs (I2C, SPI, UART) are just pads",
          "Any SerDes, DDR/LPDDR/HBM PHY, MIPI D-/C-PHY, USB 2.0 PHY: "
          "buy a silicon-proven hard macro in your exact process node"],
         ["Verification IP", "Rarely - writing a full compliance-grade VIP "
          "takes person-years", "Always for standard protocols; VIP vendors "
          "track spec errata and compliance checklists"]],
        widths=[16, 42, 42], bold_first=True)
    bul(["**Hard PHY**: a laid-out, characterized macro for one process "
         "(e.g. a 5 nm LPDDR5X PHY). It comes with timing models (LIB), "
         "abstracts (LEF), IBIS/S-parameter models and a silicon report. You "
         "cannot change it, only configure it.",
         "**Soft PHY / soft PCS**: synthesizable logic, portable across "
         "processes - realistic only for low-speed interfaces or the digital "
         "parts (PCS, PHY-side controller logic).",
         "**Evaluate** licensed IP on: silicon proof in your node, compliance "
         "certificates (USB-IF, PCI-SIG), deliverables (RTL, VIP, drivers, "
         "test chips), configurability, PPA numbers, support and errata "
         "history, and license terms (per-design vs. royalties)."])

    h2("Pad ring and IO cells")
    p("Every protocol ends at a pad. The IO library and the pad ring are "
      "physical-design and package decisions that constrain the protocols "
      "you can use.")
    tbl(["IO type", "Used for", "Characteristics"],
        [["**GPIO** (1.8/3.3 V, programmable drive, pull-up/down, Schmitt "
          "input)", "UART, SPI, I2C (open-drain mode), I2S, JTAG, CAN/LIN to "
          "transceivers", "Tens of MHz; muxed with other functions through "
          "pin-mux registers"],
         ["**Open-drain / fail-safe IO**", "I2C/SMBus/I3C", "Must not load the "
          "bus when unpowered; I3C needs push-pull and open-drain modes"],
         ["**LVDS / sub-LVDS / SLVS**", "Legacy camera/display, clock inputs",
          "Differential, few hundred mV swing, up to ~1 Gb/s per pair"],
         ["**DDR IO** (SSTL/POD/LVSTL)", "DDR4 (POD12), LPDDR4/5 (LVSTL)",
          "Part of the DDR PHY macro with calibrated ODT/drive"],
         ["**SerDes macros** (bump-attached)", "PCIe, USB 3.x, Ethernet, "
          "DP, SATA", "Not in the pad ring at all in flip-chip designs - "
          "the macro sits at the die edge with its own bumps, ESD and supplies"],
         ["**Analog / special pads**", "Crystal (XO), reference resistor for "
          "calibration, PLL supplies", "Dedicated, noise-isolated supply "
          "domains"]],
        widths=[27, 33, 40], bold_first=False)
    box("warn", "PITFALL: pin-mux and IO voltage surprises",
        "Late-found integration bugs: an I2C function muxed onto a pad that "
        "has no open-drain mode; an SD card interface that must switch from "
        "3.3 V to 1.8 V signalling (UHS-I) on a pad that supports only one "
        "voltage; a 3.3 V-only IO bank that shares a supply with a 1.8 V "
        "sensor interface; an RGMII bus spread over pads with mismatched "
        "delays. Review the pin list with the board and package teams before "
        "the pad ring is frozen.")

    h2("Worked example: a descriptor-based DMA-to-stream engine")
    p("To make the architecture concrete, here is a complete, small DMA "
      "engine of the kind that feeds a transmit protocol engine. It walks a "
      "**linked list of descriptors** in memory, checks the OWN bit, "
      "streams each buffer out on an AXI4-Stream-style `valid/ready` port "
      "with `TLAST` at the end of each packet, writes each descriptor back "
      "with OWN cleared, and raises an interrupt at the end of the chain. "
      "Its data path uses a 4-entry FIFO and a **credit rule**: a memory "
      "read is issued only if the FIFO has room for it plus every read "
      "still in flight, so back-pressure from the stream never overflows "
      "the FIFO - the bandwidth-delay rule of this chapter in one line of "
      "RTL (`can_issue`).")
    diagram([
        "   word  31   30   29   28 ........ 16  15 ................. 0",
        "  dp+0  [OWN][EOP][EOC][   reserved   ][        LEN (words)   ]",
        "  dp+1  [              buffer address (word)                  ]",
        "  dp+2  [              next descriptor address                ]",
        "",
        "  FSM:  IDLE -start-> F0 -> F1 -> F2 -> F3 --OWN=1--> DATA --> WB --EOC=0--> F0",
        "                                        |                       |",
        "                                        +--OWN=0: err, irq      +--EOC=1--> DRAIN",
        "                                             -> IDLE                  (irq) -> IDLE"],
        "Descriptor format and control FSM of the example DMA engine. F0-F3 "
        "fetch the three descriptor words through a one-cycle-latency memory "
        "port.")
    _v("dma", "desc_dma.sv - descriptor fetch, credit-controlled data reads, "
              "stream FIFO, write-back of the OWN bit and completion "
              "interrupt.")
    p("The testbench builds a three-descriptor chain in a memory model: two "
      "buffers (3 + 2 words) form the first packet (EOP on the second "
      "descriptor) and one 4-word buffer forms the second packet (EOP and "
      "EOC). It runs the chain with a sink that is always ready, then again "
      "with 50 % random back-pressure, and finally restarts the engine on the "
      "same chain without software handing the descriptors back.")
    _v("tb_dma", "tb_dma.sv - memory model, descriptor chain, random "
                 "back-pressure and a negative test of the ownership check.")
    _o("dma", "Real output (Icarus Verilog 12). Cycle numbers are relative to "
              "the start pulse.")
    p("What the run shows:")
    bul(["**Packetization is correct**: 9 beats, `TLAST` on beat 5 (end of the "
         "two-buffer packet) and beat 9, even though the first packet spans "
         "two descriptors - that is scatter-gather.",
         "**Back-pressure is lossless**: with the sink ready only half the "
         "time, the same 9 words arrive in order; the credit rule stalls "
         "memory reads instead of dropping data.",
         "**Write-back**: word 0 of each descriptor reads back with bit 31 "
         "(OWN) cleared (`80000003` -> `00000003`, `C0000002` -> "
         "`40000002`, `E0000004` -> `60000004`), handing the buffers back to "
         "software.",
         "**Ownership is enforced**: restarting on descriptors software has "
         "not re-armed ends immediately with `err=1` instead of re-sending "
         "stale buffers.",
         "**The cost of descriptor fetch is visible**: within a buffer the "
         "engine streams one word per cycle, but there is an 8-cycle bubble "
         "between buffers (write-back plus three dependent descriptor reads). "
         "With 3-word buffers that halves the throughput; with realistic "
         "memory latency (100+ cycles) it would be far worse. That is why "
         "production DMA engines **prefetch descriptors** into a small "
         "descriptor cache and overlap write-back with the next transfer."])
    box("expert", "Interview angle: sizing the DMA FIFO",
        "Q: 'Your DMA reads from DDR with 200 ns latency and must stream "
        "8 bytes per cycle at 500 MHz. How deep is the FIFO and how many "
        "reads must be outstanding?' A: bandwidth = 4 GB/s; bandwidth x "
        "latency = 800 bytes = 100 beats must be in flight to keep the "
        "stream busy. The FIFO must accept all of them when they return (at "
        "least 100 entries, in practice 128) and the AXI master must support "
        "enough outstanding transactions: with 64-byte bursts, 800/64 = 12.5, "
        "so at least 13 outstanding reads (IDs or a deep reorder-free "
        "queue). Too few outstanding transactions is the most common reason "
        "a DMA falls short of its bandwidth target.")

    h2("Integration checklist")
    checklist("Integrating a protocol controller and PHY", [
        "Clocks: every clock the IP needs is listed with frequency, source, "
        "jitter requirement and whether it may be gated; SDC constraints "
        "provided by the IP vendor are merged and reviewed.",
        "CDC: all crossings are identified (FIFOs, synchronizers, quasi-static "
        "configuration), and the CDC tool runs clean with justified waivers.",
        "Resets: reset per domain, release order matches the PHY data book, "
        "soft-reset scope documented.",
        "Power: power domains, isolation and retention for the controller, "
        "always-on wake-up logic, PHY power-down sequence, UPF reviewed.",
        "Bus interfaces: address map entry, AXI ID widths, outstanding "
        "transaction limits, burst sizes, QoS settings, coherency (ACE-Lite or "
        "cache maintenance in the driver).",
        "Buffers: SRAM sizes justified by bandwidth x latency, memory BIST "
        "and ECC/parity inserted where required.",
        "Interrupts: routed to the interrupt controller with the right type "
        "(level/edge/MSI), coalescing configured.",
        "PHY: interface (PIPE/DFI/UTMI/xMII/PPI) configuration matches on "
        "both sides; calibration resistors, reference clocks and supplies "
        "reach the macro; test modes (loopback, PRBS, BIST) are accessible.",
        "Pads: pin-mux, IO voltages, open-drain/fail-safe needs, ESD and "
        "package escape reviewed with board and package teams.",
        "DFT: scan wrappers or bypass for the PHY, IEEE 1500 / IJTAG access "
        "to PHY test registers (Chapter 23).",
        "Software: register map published, reference driver running on "
        "emulation, programming guide covers bring-up and error recovery.",
        "Verification: controller tested with protocol VIP, SoC-level test "
        "through the real PHY model, compliance plan agreed (Chapter 25)."])

    h2("Summary")
    bul(["Every protocol controller follows one skeleton: bus interface and "
         "CSRs, DMA, buffers, protocol engine, PCS, standard PHY interface, "
         "PHY and pads. Bugs live at the seams between the layers.",
         "Descriptors are a protocol between hardware and software: format, "
         "ownership, ordering (barrier before doorbell, data before status "
         "before interrupt) and coherency must all be specified.",
         "Size buffers from bandwidth x round-trip latency, burst and jitter "
         "requirements, and packet size; credits make the round-trip rule "
         "explicit.",
         "Standard PHY interfaces (PIPE, DFI, UTMI/ULPI, xMII, PPI, RDI/FDI) "
         "separate digital controllers from mixed-signal PHYs and define the "
         "verification boundary.",
         "Controllers span several clock domains; CDC points are the FIFOs, "
         "the configuration path, the interrupt path and the PCS elastic "
         "buffer.",
         "PHY bring-up follows a strict sequence: PLL lock, calibration, "
         "controller reset release, configuration, link training.",
         "Buy complex controllers, PHYs and VIP; build simple peripherals; "
         "review pads and pin-mux early; deliver a clean programming model."])

    h2("Exercises")
    bul(["Draw the layered architecture of a USB 2.0 device controller with a "
         "UTMI+ PHY. Mark each clock domain and every CDC point.",
         "A 10 Gb/s Ethernet MAC must honour PAUSE frames. The link partner "
         "may keep sending for up to 1 us after you request a pause (cable "
         "delay, frames in flight, reaction time). How much RX FIFO headroom "
         "is needed above the pause threshold? Add one maximum-size jumbo "
         "frame (9018 bytes) and give the total.",
         "Extend the example DMA engine with a two-entry descriptor prefetch "
         "so that the next descriptor is fetched while the current buffer is "
         "streaming. Estimate the new throughput for 3-word buffers.",
         "Write the driver sequence for receiving packets with an RX "
         "descriptor ring on a non-coherent DMA port. Where exactly do the "
         "cache clean and invalidate operations go, and what breaks if "
         "either is missing?",
         "List the checks you would make before accepting a licensed PCIe "
         "Gen5 PHY hard macro for a 5 nm SoC.",
         "Explain why a level-sensitive interrupt with W1C status bits cannot "
         "lose an event, while a pulse interrupt can. What must the hardware "
         "do when a set and a clear hit the same bit in the same cycle?"],
        ordered=True)


# ---------------------------------------------------------------- Ch 25 ---
def _ch25():
    chapter("Verifying Protocols: VIP, Assertions, Compliance and "
            "Interoperability")
    p("A protocol controller is verified three times. First in simulation, "
      "against a model of the specification (verification IP, assertions, "
      "scoreboards, coverage). Then against **other people's "
      "implementations** - compliance test suites, certification labs and "
      "interoperability plugfests - because two designs that both 'meet the "
      "spec' can still fail to talk to each other. Finally in silicon, with "
      "protocol analyzers, bit-error-rate testers and eye scans. This "
      "chapter walks through all three, with a running assertion checker and "
      "an error-injection testbench that you can reuse as templates. The "
      "companion Verilog & SystemVerilog guide covers UVM mechanics; here "
      "the focus is on what is special about **protocols**.")

    h2("Why protocols are hard to verify")
    bul(["**The specification is the reference model** - hundreds of pages of "
         "prose, timing tables and state machines, with optional features, "
         "errata and ECNs. Every 'shall' is a check someone has to write.",
         "**Two sides must agree.** Bugs appear only with particular "
         "partners: a host that sends a legal but unusual sequence, a device "
         "that responds at the edge of a timing window.",
         "**Error paths dominate.** A link spends most of its code on "
         "retries, timeouts, recovery and low-power transitions that normal "
         "traffic never exercises.",
         "**Layers and clocks.** Transaction, link and physical layers "
         "interact across clock domains and power states; a bug may need a "
         "retry during a speed change during a power-state exit.",
         "**Timescales.** Link training, low-power entry/exit and timeouts "
         "take micro- to milliseconds - millions of cycles of simulation."])

    h2("Architecture of protocol verification IP")
    p("Verification IP (VIP) packages the knowledge of a protocol into "
      "reusable testbench components. Whether written in UVM, cocotb or "
      "plain SystemVerilog, a VIP has the same shape:")
    diagram([
        "+----------------------------------- env -----------------------------------+",
        "|  +------------------------ agent (active) --------------------------+     |",
        "|  | sequencer --> driver ==pins==> DUT ==pins==> monitor             |     |",
        "|  |    ^   sequences:                 ^ protocol checker (SVA)       |     |",
        "|  |    |   normal, corner,            |       |                      |     |",
        "|  |    |   error injection            +-------+ observed txns        |     |",
        "|  +----|--------------------------------------|----------------------+     |",
        "|       |                                      v                            |",
        "|  test / virtual sequence         [ scoreboard ] <-- reference model       |",
        "|                                  [ coverage   ]                           |",
        "+---------------------------------------------------------------------------+"],
        "The canonical VIP agent. A passive agent has only the monitor and "
        "checker and is used to observe a link between two real designs.")
    tbl(["Component", "Role for a protocol", "Examples"],
        [["**Sequence items / sequences**", "Transactions at the protocol's "
          "level of abstraction, with constraints for legal and illegal "
          "values", "AXI burst, USB transfer, PCIe TLP, Ethernet frame"],
         ["**Driver**", "Turns transactions into pin activity with correct "
          "timing; can be told to violate it (error injection)",
          "Drives VALID/READY, SCL/SDA, D+/D-, PIPE lanes"],
         ["**Monitor**", "Reconstructs transactions from pins, never drives",
          "Assembles bursts, frames, TLPs; timestamps them"],
         ["**Protocol checker**", "Checks every rule of the spec on every "
          "cycle (assertions)", "Handshake stability, timing windows, "
          "legal state transitions"],
         ["**Scoreboard**", "Compares what came out with what should have, "
          "using a reference model", "Data integrity, ordering, "
          "responses"],
         ["**Coverage**", "Measures which features and corner cases were "
          "exercised", "Transaction types x sizes x responses x errors"],
         ["**Configuration**", "Selects spec version, options, speeds, "
          "roles (host/device, master/slave)", "USB 2.0 vs 3.2, AXI4 vs "
          "AXI5, lane count"]],
        widths=[22, 45, 33], bold_first=False)
    box("key", "Commercial VIP versus home-grown",
        "For complex standard protocols (PCIe, USB, Ethernet, DDR, MIPI, "
        "CXL, UCIe) teams almost always license VIP: it comes with thousands "
        "of spec-derived checks, compliance-style test suites and "
        "maintenance as the specification evolves. Home-grown VIP is right "
        "for simple buses, proprietary protocols and quick block-level "
        "checkers - like the ones in this chapter.")

    h2("Protocol assertion libraries")
    p("Assertions are the cheapest, densest form of protocol checking: one "
      "line per rule, evaluated every cycle in simulation, in emulation "
      "(if synthesizable) and in formal verification. A good library is "
      "written once per protocol and **bound** to every instance of the "
      "interface. Some representative rules (SystemVerilog Assertions; "
      "shown for reference, not all of these constructs are run below):")
    code([
        "// ---- AXI (any channel with VALID/READY/payload) ----",
        "a_valid_hold:  assert property (@(posedge aclk) disable iff (!aresetn)",
        "                 awvalid && !awready |=> awvalid);",
        "a_addr_stable: assert property (@(posedge aclk) disable iff (!aresetn)",
        "                 awvalid && !awready |=> $stable({awaddr, awlen, awsize, awburst}));",
        "a_wrap_len:    assert property (@(posedge aclk) disable iff (!aresetn)",
        "                 awvalid && awburst == 2'b10 |-> awlen inside {1, 3, 7, 15});",
        "a_4k:          assert property (@(posedge aclk) disable iff (!aresetn)",
        "                 awvalid && awburst == 2'b01 |->",
        "                 (awaddr[11:0] + ((awlen + 1) << awsize)) <= 13'h1000);",
        "// ---- APB: SETUP phase is exactly one cycle, then ACCESS ----",
        "a_setup:       assert property (@(posedge pclk) disable iff (!presetn)",
        "                 psel && !penable |=> psel && penable);",
        "a_access_hold: assert property (@(posedge pclk) disable iff (!presetn)",
        "                 psel && penable && !pready |=> psel && penable &&",
        "                 $stable({paddr, pwrite, pwdata}));",
        "// ---- SPI mode 0: MOSI must not change at a rising (sampling) SCLK edge ----",
        "a_spi_mode0:   assert property (@(posedge clk_chk) disable iff (cs_n)",
        "                 $rose(sclk) |-> $stable(mosi));  // clk_chk oversamples SCLK",
        "// ---- liveness with a bound: every request gets a response ----",
        "a_resp:        assert property (@(posedge aclk) disable iff (!aresetn)",
        "                 arvalid && arready |-> ##[1:256] rvalid);"],
        "A small AXI/APB/SPI assertion library (illustrative). The AXI rules "
        "come straight from the AMBA specification: no VALID withdrawal, "
        "stable payload during a stall, legal WRAP lengths, bursts must not "
        "cross 4 KB.")
    p("The last rule deserves a comment: a real AXI response has no fixed "
      "latency, so the 'within 256 cycles' bound is a **testbench "
      "assumption** (a watchdog), not a spec rule. Formal tools can prove "
      "'eventually' properties without an arbitrary bound. The SPI rule "
      "shows another point: assertions on source-synchronous interfaces "
      "must be clocked by the interface clock or oversampled by a faster "
      "checker clock, and they must be disabled when chip select is "
      "inactive.")
    p("Now a runnable example. The checker below captures the two core "
      "valid/ready rules plus an X-check, and is connected to a "
      "deliberately buggy source that, when stalled, sometimes withdraws "
      "VALID and sometimes changes its payload. Verilator 5.020 supports "
      "simple concurrent assertions (implication, `$stable`, `$isunknown`) "
      "but not cycle-delay ranges in sequences, which is why the cover "
      "property is kept to a single-cycle expression.")
    _v("sva", "sva.sv - a reusable valid/ready protocol checker, a buggy "
              "source and a small testbench.")
    _o("sva", "Real output of Verilator 5.020 (`--binary --timing --assert`, "
              "run with `+verilator+error+limit+100` so that simulation "
              "continues after the first failure). Times are in ns.")
    p("Both bugs are caught at the exact cycle they occur, with the name of "
      "the rule that broke - far easier to debug than a scoreboard mismatch "
      "hundreds of cycles later. This is why every protocol interface in a "
      "serious SoC has its checker bound in every simulation, and why "
      "assertion-based VIP is also the property set for formal verification "
      "of simple interfaces (APB, AXI4-Lite slaves), where a formal tool "
      "can prove that no input sequence violates them.")

    h2("Scoreboards for packet protocols")
    p("A scoreboard answers 'did the right data come out?'. For packet "
      "protocols that question has several parts, each needing a design "
      "decision:")
    tbl(["Question", "Scoreboard technique"],
        [["Was every packet delivered, exactly once?", "Expected queue; at "
          "end of test the queue must be empty; duplicates flagged"],
         ["In the right order?", "In-order FIFO compare when the protocol "
          "guarantees order (Ethernet port, AXI same ID); per-ID/per-stream "
          "queues when order is only per ID or per virtual channel (AXI "
          "different IDs, PCIe relaxed ordering)"],
         ["With the right content?", "Reference model applies the "
          "transformation (header insertion, CRC, padding, VLAN tag, "
          "encryption) before comparing"],
         ["Were dropped packets supposed to be dropped?", "Model predicts "
          "drops (bad CRC, filter miss, FIFO overflow policy) and counts "
          "them"],
         ["Did errors get reported correctly?", "Compare status fields, "
          "counters and interrupts with the injected errors"]],
        widths=[32, 68])
    box("warn", "PITFALL: a scoreboard that cannot fail",
        "Common testbench bugs: the expected queue is filled from the DUT's "
        "own output (so it always matches); comparisons are skipped when the "
        "queue is empty; the end-of-test check for leftover packets is "
        "missing; or errors are counted but never make the test fail. "
        "Always run a **negative test** - break the DUT on purpose (the "
        "buggy source above, a flipped bit below) and confirm the testbench "
        "reports it.")

    h2("Error injection")
    p("Error handling is specified as carefully as normal operation - and "
      "exercised far less. Error injection makes those paths run. Every "
      "protocol has its characteristic faults:")
    tbl(["Injection", "What it tests", "Protocols"],
        [["Bit flips in data or CRC", "CRC checking, discard, error "
          "counters, retry", "Ethernet, USB, PCIe (LCRC/ECRC), CAN, "
          "MIPI CSI-2 (ECC/CRC)"],
         ["NACK / NAK / STALL / retry responses", "Retry logic and limits",
          "I2C NACK, USB NAK/STALL, PCIe NAK DLLP, AXI SLVERR/DECERR"],
         ["Dropped or truncated packets", "Timeouts, sequence-number gaps",
          "PCIe replay timer, USB timeouts, TCP-like layers"],
         ["Timeouts (no response)", "Watchdogs and completion timeouts",
          "PCIe completion timeout, I2C clock stretching limits, SMBus "
          "35 ms timeout"],
         ["Back-pressure / credit starvation", "Buffers, flow control, "
          "deadlock freedom", "AXI READY low, PCIe credits withheld, "
          "Ethernet PAUSE"],
         ["Protocol violations", "Robustness to a misbehaving partner",
          "Illegal tokens, bad lengths, framing errors, arbitration loss"],
         ["Physical impairments", "CDR, equalization, elastic buffer",
          "Jitter, ppm offset, lane skew, polarity inversion (in AMS or "
          "PHY models)"]],
        widths=[25, 35, 40], bold_first=False)
    p("The following self-checking testbench exercises a small **CRC-8 "
      "protected packet link**: a transmitter appends a CRC-8 frame check "
      "sequence (polynomial 0x07, the CRC-8/SMBUS variant used by SMBus "
      "packet error checking), a receiver checks it and runs a timeout for "
      "packets that stall. Between them sits an error injector - the "
      "'channel' - that for each packet chooses no error, a single-bit "
      "flip, a burst of up to 8 bits, three corrupted bytes, or a dropped "
      "FCS byte.")
    _v("link", "link.sv - CRC-8 transmitter and receiver with timeout.")
    _v("tb_link", "tb_link.sv - error injector, monitor and scoreboard. The "
                  "scoreboard compares the received payload with what was "
                  "sent, independently of the CRC verdict.")
    _o("link", "Real output of Verilator 5.020 (`--binary --timing`). The "
               "first five injected packets are logged, plus every silent "
               "corruption.")
    p("Reading the result:")
    bul(["The **known-answer test** passes: CRC-8 of the ASCII string "
         "'123456789' is 0xF4, the published check value of CRC-8/SMBUS, and "
         "the same value was computed by an independent Python reference.",
         "Every single-bit error and every burst of up to 8 bits was caught "
         "(an n-bit CRC detects all bursts of length <= n), and every dropped "
         "FCS byte ended in a TIMEOUT rather than a hang.",
         "**Three packets with multi-byte corruption passed the CRC check.** "
         "The scoreboard caught them anyway because it compares payloads, "
         "not CRC verdicts, and reported **silent corruption**. About 600 "
         "packets got three corrupted bytes, and a random error pattern "
         "escapes an 8-bit CRC with probability about 1/256, so 2 to 3 "
         "escapes is exactly what theory predicts. Chapter 26 measures this "
         "for CRC-8 versus CRC-32.",
         "**No false alarms**: none of the 1978 clean packets was flagged. A "
         "checker that raises false errors is as broken as one that misses "
         "real ones."])
    box("expert", "Interview angle: what does this TB prove?",
        "It proves the RX detects what a CRC-8 can detect, reports "
        "timeouts, and never flags good packets. It also demonstrates that "
        "CRC-8 is too weak for this channel if multi-byte corruption is "
        "plausible - a system-level finding, not an RTL bug. A good DV "
        "engineer reports both kinds of result.")

    h2("Coverage models for protocols")
    p("Functional coverage is the answer to 'are we done?'. For a protocol "
      "it is built from the specification's features and their "
      "combinations:")
    code([
        "covergroup axi_wr_cg with function sample(axi_txn t);",
        "  burst: coverpoint t.burst { bins fixed = {0}; bins incr = {1}; bins wrap = {2}; }",
        "  len:   coverpoint t.len   { bins one = {0}; bins short_ = {[1:3]};",
        "                              bins mid = {[4:15]}; bins long_ = {[16:255]}; }",
        "  size:  coverpoint t.size  { bins b[] = {[0:3]}; }          // 1..8 bytes/beat",
        "  resp:  coverpoint t.resp  { bins okay = {0}; bins exokay = {1};",
        "                              bins slverr = {2}; bins decerr = {3}; }",
        "  unal:  coverpoint t.unaligned;",
        "  stall: coverpoint t.max_wready_stall { bins none = {0}; bins some = {[1:4]};",
        "                                         bins long_ = {[5:$]}; }",
        "  burst_x_len:  cross burst, len  { ignore_bins wrap_one = binsof(burst.wrap)",
        "                                                        && binsof(len.one); }",
        "  burst_x_resp: cross burst, resp;",
        "endgroup"],
        "A protocol coverage model: transaction types x sizes x responses x "
        "timing, with illegal combinations excluded (a WRAP burst of length "
        "1 is illegal in AXI).")
    bul(["**Transaction space**: every type, size, length, alignment and "
         "response, and their meaningful crosses.",
         "**State space**: every state and legal transition of the protocol "
         "FSMs (link training states, power states), including transitions "
         "taken during errors.",
         "**Error space**: every injected error type in every relevant state "
         "(a CRC error during retry, a timeout during a speed change).",
         "**Timing space**: back-to-back traffic, maximum stalls, minimum "
         "gaps, simultaneous events on different channels.",
         "**Configuration space**: speeds, widths, lane counts, optional "
         "features on and off."])
    box("tip", "Link coverage to the specification",
        "Mature teams keep a verification plan that maps every numbered "
        "requirement of the spec (and every compliance checklist item) to "
        "assertions, tests and coverage points. When a spec errata or ECN "
        "arrives, the plan shows exactly which checks must change.")

    h2("Compliance test suites and certification")
    p("Passing your own testbench proves you implemented your reading of the "
      "specification. Compliance testing checks it against the standards "
      "body's reading, using independent test equipment and suites. For "
      "consumer and interoperability-critical protocols, passing is the "
      "price of using the logo.")
    tbl(["Protocol family", "Organization / programme", "What is tested"],
        [["USB 2.0 / 3.x / USB4 / Type-C / PD", "**USB-IF** compliance "
          "workshops and authorized independent test labs; products listed "
          "on the integrators list", "Electrical (eye, jitter, "
          "signal quality), link and protocol layer, Type-C/PD, "
          "interoperability with a gold suite of hosts/devices"],
         ["PCI Express", "**PCI-SIG** compliance workshops; Integrators "
          "List", "Electrical (TX/RX, reference clock), link/transaction "
          "layer, configuration space checks, interoperability"],
         ["Ethernet (and many others)", "**UNH-IOL** (University of New "
          "Hampshire InterOperability Laboratory); IEEE 802.3 conformance "
          "test plans", "PMA/PMD electrical, auto-negotiation, MAC/PCS "
          "conformance, interoperability"],
         ["MIPI (D-PHY, C-PHY, CSI-2, DSI, I3C)", "**MIPI Alliance** "
          "conformance test suites, member interoperability events and "
          "third-party labs", "PHY electrical conformance, protocol "
          "conformance"],
         ["HDMI / DisplayPort", "HDMI Authorized Test Centers; VESA "
          "compliance programme", "Electrical, protocol, HDCP, EDID and "
          "link training"],
         ["CAN / CAN FD", "ISO 16845 conformance test plans, often "
          "executed by test houses", "Protocol controller conformance"],
         ["Bluetooth, Wi-Fi (for completeness)", "Bluetooth SIG "
          "qualification; Wi-Fi Alliance certification", "RF and protocol"]],
        widths=[24, 38, 38], bold_first=False)
    bul(["Compliance tests are mostly **black-box tests at the pins** run on "
         "a test board, so the silicon must have the required test modes: "
         "compliance patterns, loopback, PRBS generators/checkers, test "
         "modes such as USB 2.0 Test_J/Test_K/Test_Packet or the PCIe "
         "compliance state of the LTSSM. Missing test modes are an RTL "
         "bug found far too late.",
         "Most standards bodies make **pre-silicon** checks possible too: "
         "commercial VIP ships with compliance-style suites, and some bodies "
         "publish test specifications to members.",
         "Budget time for compliance: a failed electrical test may need a "
         "board respin or PHY setting changes; a failed protocol test may "
         "need a firmware patch or - worst case - a silicon respin."])

    h2("Interoperability plugfests")
    p("A **plugfest** is an event where many vendors bring pre-release "
      "products and test them against each other, typically under NDA and "
      "organized by the standards body or a lab. Interoperability failures "
      "found there are often ambiguities in the specification rather than "
      "clear bugs: two readings of a timing window, an optional feature one "
      "side assumes, an unusual but legal packet sequence. The fixes flow "
      "back into errata, ECNs and the next compliance suite. For an SoC team "
      "the practical lesson is to test early against **several** real "
      "partners (hosts, switches, memories, displays), not just the one on "
      "the evaluation board.")

    h2("Emulation and FPGA prototyping")
    p("Simulation runs a large SoC at perhaps 10-1000 cycles per second, "
      "hardware emulators at around a megahertz, FPGA prototypes at tens "
      "of megahertz. Protocols are a special difficulty for both, because "
      "the outside world does not slow down: a USB host, an Ethernet "
      "switch or a PCIe root complex expects real timing.")
    diagram([
        "  real PC / switch / phone          speed bridge             emulator",
        "  (PCIe Gen4 x4 at full rate) <==> [ PHY + controller ] <==> [ DUT at 1 MHz ]",
        "                                   [ large buffers,    ]     transactors",
        "                                   [ protocol-level    ]     or pins",
        "                                   [ rate adaptation   ]",
        "",
        "  alternatives: virtual host models (transactors in the emulator), FPGA",
        "  prototypes with the IP's FPGA PHY, or a slowed-down link where allowed"],
        "A speed bridge terminates the real-speed protocol and replays it to "
        "the slow DUT, stretching timers where the protocol allows.")
    bul(["**Speed bridges / rate adapters**: boxes that terminate the "
         "protocol at full speed on one side and talk to the emulator at "
         "low speed on the other. They work well for protocols with flow "
         "control and tolerant timers (PCIe, USB, Ethernet with buffering), "
         "badly for hard real-time links.",
         "**Transactors / virtual models**: the peer device (a host, a "
         "memory) is modelled in software connected to the emulator through "
         "a transaction-level interface. Faster to set up, no real-world "
         "quirks.",
         "**FPGA prototypes**: controller RTL on an FPGA with the FPGA's "
         "SerDes standing in for the ASIC PHY; excellent for firmware and "
         "driver bring-up, and for running real operating systems and "
         "compliance-like software tests before tapeout.",
         "What prototypes cannot tell you: analog behaviour, the real PHY's "
         "equalization, and timing at the target clock frequency."])

    h2("Post-silicon validation")
    p("When silicon returns, protocol validation moves to the lab. Its tools:")
    tbl(["Tool", "What it shows", "Used for"],
        [["**Protocol analyzer / exerciser**", "Decoded packets, "
          "timing, errors, LTSSM or link-state traces; exercisers also "
          "generate traffic and inject errors", "PCIe, USB, Ethernet, "
          "MIPI, DDR bus analyzers, low-speed (I2C/SPI/CAN) decoders on "
          "logic analyzers and scopes"],
         ["**BERT** (bit error rate tester)", "Pattern generator + error "
          "detector: measures BER, jitter tolerance, stressed-eye RX "
          "performance", "SerDes receiver characterization and compliance"],
         ["**Real-time oscilloscope**", "Eye diagrams, jitter decomposition "
          "(RJ/DJ), rise times, compliance masks", "TX electrical "
          "compliance"],
         ["**On-die eye scan / margining**", "Receiver's own view of the "
          "eye: sweep sampling phase and threshold and count errors",
          "In-system margin checks; PCIe Lane Margining at the Receiver "
          "(Gen4+)"],
         ["**PRBS generators/checkers and loopbacks**", "Near-end/far-end "
          "loopback, PRBS7/15/23/31 patterns with error counters", "Bring-up "
          "and production test of links without a partner"],
         ["**On-chip trace and counters**", "Error counters, state "
          "histories, trace buffers (Chapter 23)", "Debugging rare "
          "failures in the field"]],
        widths=[27, 42, 31], bold_first=False)
    box("tip", "Design for validation",
        "Everything in the table above except the external instruments must "
        "be designed into the RTL: PRBS generators/checkers per lane, "
        "loopback paths, eye-scan hooks in the PHY, sticky error counters, "
        "link-state trace buffers, test-mode registers reachable over JTAG. "
        "They cost little area and save weeks in the lab.")

    h2("Protocol verification sign-off checklist")
    checklist("Before declaring a protocol block verified", [
        "Verification plan maps spec requirements and compliance checklist "
        "items to tests, assertions and coverage.",
        "Protocol checkers (SVA) are bound on every interface instance in "
        "every test, with zero unexpected failures.",
        "Scoreboard checks delivery, ordering, content and error reporting; "
        "negative tests prove it can fail.",
        "Error injection covers each fault class in each relevant state; "
        "recovery returns the link to normal operation.",
        "Functional coverage closed (or holes reviewed and waived); code "
        "coverage reviewed for unreachable or untested logic.",
        "Low-power entry/exit, reset during traffic and speed/width changes "
        "tested.",
        "Interoperability tests with at least one independent model or real "
        "partner (VIP from another vendor, FPGA prototype with real "
        "devices).",
        "Compliance test modes (patterns, loopback, PRBS) present and "
        "tested; compliance plan and lab slots booked.",
        "Formal proof of the simple interfaces (APB/AXI-Lite slaves, "
        "arbiters) and CDC/RDC sign-off done."])

    h2("Summary")
    bul(["Protocol verification happens in three stages: simulation against a "
         "model of the spec, compliance and interoperability against other "
         "implementations, and post-silicon validation in the lab.",
         "VIP = sequences, driver, monitor, protocol checker, scoreboard and "
         "coverage; license it for complex standards, write it for simple "
         "ones.",
         "Assertions catch protocol violations at the exact cycle; bind a "
         "checker to every interface instance and reuse the same properties "
         "for formal verification.",
         "Packet scoreboards must check delivery, order, content and error "
         "reporting - and must be proven able to fail.",
         "Error injection exercises the code that matters most in the field; "
         "the example showed CRC-8 catching all short bursts but letting "
         "about 1/256 of random multi-byte corruptions through.",
         "Compliance (USB-IF, PCI-SIG, UNH-IOL, MIPI, HDMI/VESA) needs test "
         "modes in the silicon; plugfests find specification ambiguities.",
         "Emulation needs speed bridges or transactors for real-world "
         "protocols; silicon validation needs analyzers, BERTs, eye scans "
         "and designed-in PRBS/loopback/counters."])

    h2("Exercises")
    bul(["Write SVA properties for an I2C target: (a) SDA may change only "
         "while SCL is low, except for START and STOP; (b) after the eighth "
         "data bit the transmitter releases SDA for the ACK bit. How do you "
         "clock the checker?",
         "Design a scoreboard for an AXI interconnect with 4 managers and "
         "8 subordinates, where ordering is only guaranteed per ID. What "
         "data structure do you use and how do you detect a lost "
         "transaction?",
         "Modify the CRC-8 link testbench to use a 16-bit CRC (CRC-16/CCITT, "
         "polynomial 0x1021). Predict the number of silent corruptions for "
         "the same run and check your prediction.",
         "Write a coverage model for USB 2.0 bulk transfers: token types, "
         "data PIDs (DATA0/DATA1 toggle), handshake responses, packet sizes "
         "and the error cases you would inject.",
         "List the test modes a PCIe Gen4 controller and PHY must provide "
         "for compliance and lab bring-up. Which of them must be designed "
         "into the RTL?",
         "Explain why a speed bridge can work for PCIe but is much harder "
         "for MIPI CSI-2 from a real camera sensor."],
        ordered=True)


# ---------------------------------------------------------------- Ch 26 ---
def _ch26():
    chapter("Reliability and Security on Links: CRC/ECC, Retry, Safety and "
            "Link Encryption")
    p("Every link eventually delivers a wrong bit. Every link that leaves a "
      "chip can eventually be probed, replayed or tampered with. And in cars, "
      "factories and medical devices a wrong bit can hurt someone. This "
      "chapter pulls together the techniques that make links **reliable** "
      "(detect, correct, retry, report), **safe** (ISO 26262 diagnostic "
      "coverage) and **secure** (authentication, encryption, access control "
      "on buses, secure debug). Chapter 3 introduced parity, CRC and ECC; "
      "here we quantify them and place them in real protocols.")

    h2("Error models: how links fail")
    tbl(["Error type", "Cause", "Typical protection"],
        [["**Random single-bit errors**", "Thermal/random noise and jitter on "
          "SerDes links; the bit error rate (BER) is set by the eye margin",
          "CRC + retry; FEC at high rates"],
         ["**Burst errors**", "DFE error propagation in equalized receivers, "
          "crosstalk events, supply noise, a lost CDR lock, scrambler "
          "multiplication", "CRC (detects bursts <= its width), "
          "interleaved or symbol-based FEC (Reed-Solomon)"],
         ["**Soft errors in storage**", "Particle strikes (alpha, neutrons) "
          "on SRAM/DRAM/flops", "ECC on memories, parity on buffers, "
          "scrubbing"],
         ["**Hard / permanent faults**", "Opens, shorts, stuck-at, aging, "
          "electromigration", "BIST, lane degrade/spare lanes, safety "
          "mechanisms, redundancy"],
         ["**Systematic / protocol errors**", "Design bugs, misconfiguration, "
          "a misbehaving partner", "Timeouts, protocol checkers, "
          "sequence numbers, error reporting"],
         ["**Malicious**", "Probing, injection, replay, glitching",
          "Authentication, encryption with integrity, tamper detection"]],
        widths=[22, 43, 35], bold_first=False)
    eq(["Errors per second  =  BER x line rate",
        "",
        "BER 1e-12 at 16 Gb/s    ->  0.016 errors/s  =  about one error per minute",
        "BER 1e-12 at 16 lanes x 32 Gb/s  ->  about one error every 2 s",
        "BER 1e-6 (PAM4 raw, before FEC) at 64 Gb/s  ->  64,000 errors/s",
        "",
        "Poisson: P(k errors in an n-bit frame) = (n p)^k e^(-n p) / k!,  p = BER"],
       "Even an excellent link makes errors routinely; the protocol must "
       "detect every one that matters.")
    p("Two consequences drive protocol design. First, at modern rates "
      "**detection plus retry** is not optional anywhere errors can "
      "corrupt state. Second, PAM4 signalling (PCIe 6.0, 200G/400G Ethernet) "
      "trades raw BER for bandwidth: its raw BER is orders of magnitude "
      "worse than NRZ, so **forward error correction** becomes mandatory and "
      "its latency becomes a design parameter.")

    h2("What a CRC can detect")
    p("A CRC with generator polynomial g(x) of degree r appends r check bits. "
      "An error pattern e(x) is **undetected** exactly when g(x) divides e(x). "
      "From that algebra come the guarantees:")
    tbl(["Property", "Condition", "Consequence"],
        [["All single-bit errors", "g(x) has at least two terms",
          "Always true for standard CRCs"],
         ["All odd numbers of bit errors", "(x + 1) divides g(x)",
          "CRC-8 0x07, CRC-16/CCITT; not CRC-32 (IEEE)"],
         ["All double-bit errors", "Codeword length <= order of g(x) (the "
          "smallest d with g | x^{d} + 1)", "The Hamming distance falls to 2 "
          "beyond that length"],
         ["All bursts of length <= r", "g(x) has a nonzero x^{0} term",
          "Any 8-bit CRC catches every 8-bit burst"],
         ["Bursts of length r + 1", "-", "Escape probability 2^{-(r-1)}"],
         ["Longer bursts / random garbage", "-", "Escape probability "
          "about 2^{-r}"]],
        widths=[28, 38, 34])
    p("The **Hamming distance (HD)** of a CRC-protected frame is the smallest "
      "number of bit flips that can go undetected; it depends on both the "
      "polynomial and the frame length. Koopman's published tables are the "
      "standard reference: for example the IEEE 802.3 CRC-32 gives HD = 4 "
      "over every Ethernet frame length, while the simple CRC-8 0x07 gives "
      "HD = 4 only up to 119 data bits (15 bytes) and HD = 2 beyond. The "
      "choice of CRC is therefore a function of frame size:")
    tbl(["CRC", "Where", "Protects"],
        [["CRC-5", "USB token packets", "11-bit address/endpoint or frame "
          "number"],
         ["CRC-16", "USB data packets; many serial links", "Up to 1024-byte "
          "USB 2.0 payloads"],
         ["CRC-15, CRC-17, CRC-21", "CAN, CAN FD (17 for <= 16 data bytes, 21 "
          "for longer)", "Short automotive frames (plus bit stuffing checks)"],
         ["CRC-32 (IEEE 802.3)", "Ethernet FCS, SATA, many others", "Frames up "
          "to 1518 bytes; HD = 4 still holds for 9 KB jumbo frames"],
         ["32-bit LCRC / ECRC", "PCIe data link layer / end-to-end",
          "TLPs per hop / end to end"],
         ["CRC-16 or CRC-32 variants", "MIPI CSI-2 packet footer (16-bit); "
          "SATA, UCIe, CXL flits", "Payloads and flits"]],
        widths=[22, 40, 38],
        caption="CRCs you will meet. Always pair a CRC with a frame length "
                "limit; its guarantees hold only up to a length.")

    h3("Experiment: CRC-8 versus CRC-32 under random and burst errors")
    p("The script below builds 64-byte frames with random payloads, appends "
      "either a CRC-8 (polynomial 0x07) or the Ethernet CRC-32, injects "
      "errors of a chosen kind and counts how many corrupted frames pass the "
      "check. It first asserts the known check values of both CRCs "
      "(0xF4 and 0xCBF43926 for '123456789'), then finishes with an exact "
      "calculation of how many two-bit error patterns escape CRC-8 at "
      "different frame lengths.")
    _v("crc_exp", "crc_exp.py - Monte-Carlo error injection on CRC-protected "
                  "frames plus an exhaustive two-bit analysis.")
    _o("crc_exp", "Real output (Python 3, about 10 s).")
    p("Every line of that table matches the theory:")
    bul(["**Odd numbers of flips never escape CRC-8** (1 and 3 random bits: "
         "0 escapes) because 0x107 = (x + 1)(x^{7} + x^{6} + x^{5} + x^{4} + x^{3} + "
         "x^{2} + 1) has the factor x + 1.",
         "**Two random flips do escape CRC-8** at this frame length: the "
         "order of g(x) is 127, so two flips exactly 127 bits apart (or a "
         "multiple) are invisible. On a 520-bit codeword 810 of the 134,940 "
         "two-bit patterns (0.60 %) escape; the Monte-Carlo run measured "
         "0.55 %. On an 8-byte payload the codeword is shorter than 127 bits "
         "and there are no such escapes - HD depends on length.",
         "**Bursts up to 8 bits are always caught**, bursts of 9 escape at "
         "7.87e-3, matching 2^{-7} = 7.81e-3, and longer bursts or garbage "
         "escape at about 3.9e-3 = 2^{-8}.",
         "**CRC-32 caught everything** in 1.1 million corrupted frames. Its "
         "escape probability for random garbage is about 2^{-32} = "
         "2.3e-10, so zero escapes is expected; demonstrating an escape "
         "would need billions of trials. For the 4-random-bit row, CRC-32's "
         "HD of 4 at this length means some 4-bit patterns can escape in "
         "principle, but they are a vanishingly small fraction."])
    box("key", "Residual error rate",
        "What a system designer actually needs is the **residual (undetected) "
        "error rate** = frame error rate x probability that an error escapes "
        "the check. With BER 1e-12, 1500-byte frames and CRC-32 it is far "
        "below one undetected frame in the life of the universe for random "
        "errors - but only if the error model is right. Bursts from DFE "
        "error propagation or a scrambler with multiplying behaviour change "
        "the picture, which is why standards analyse CRC and scrambler "
        "together.")

    h2("Forward error correction")
    p("FEC adds redundancy so the receiver can **correct** errors without a "
      "retransmission. Links use it when the raw BER is too high for "
      "detect-and-retry to be efficient, or when there is no return channel "
      "or no time to retry.")
    tbl(["FEC", "Where", "Key numbers"],
        [["**RS(528,514)** 'KR4'", "100GBASE-KR4/CR4 and other 25G-per-lane "
          "NRZ Ethernet", "Reed-Solomon over 10-bit symbols, 14 parity "
          "symbols, corrects up to 7 symbol errors per codeword"],
         ["**RS(544,514)** 'KP4'", "50G/100G/200G/400G PAM4 Ethernet "
          "(e.g. 400GBASE-DR4), 100GBASE-KP4", "30 parity symbols, corrects "
          "up to 15 symbol errors; a 10-bit symbol absorbs a whole short "
          "burst"],
         ["**PCIe 6.0 FLIT FEC**", "PCIe 6.0 (64 GT/s PAM4), CXL 3.x",
          "256-byte flit: 236 bytes TLP, 6 bytes DLP, 8 bytes CRC, 6 bytes "
          "FEC made of three interleaved single-symbol-correcting codes; "
          "lightweight for low latency, with CRC + retry behind it"],
         ["**LDPC**", "10GBASE-T, Wi-Fi, 5G, some SerDes proposals",
          "Near-Shannon performance, iterative decoding, higher latency and "
          "power"],
         ["**Hamming / BCH**", "Memories, NAND flash (BCH/LDPC), some "
          "low-latency links", "Bit-level correction, simple decoders"]],
        widths=[20, 35, 45], bold_first=False)
    diagram([
        "  PCIe 6.0 flit (256 bytes)",
        "  +------------------------------+-------+--------+--------+",
        "  | TLP bytes (236)              | DLP 6 | CRC 8  | FEC 6  |",
        "  +------------------------------+-------+--------+--------+",
        "  receiver: FEC corrects small errors -> CRC checks the result",
        "            CRC fail -> NAK -> replay the flit (link-level retry)",
        "",
        "  Ethernet 400G: 64b/66b blocks -> transcode 256b/257b -> RS(544,514)",
        "            symbols interleaved across lanes; uncorrectable -> mark frame bad"],
        "FEC in two modern links. PCIe keeps FEC deliberately light (a few ns "
        "of latency) and relies on CRC + retry for the rest; Ethernet uses a "
        "strong RS code because it has no link-level retry.")
    box("intuit", "Why symbol-based codes like bursts",
        "A Reed-Solomon code over 10-bit symbols counts errors in symbols, "
        "not bits. A 9-bit burst that lands inside one or two symbols costs "
        "only one or two of its 15 correctable symbols. That is exactly the "
        "error shape a DFE receiver produces, and why RS rather than a "
        "bit-level code protects PAM4 Ethernet.")
    p("FEC is not free: RS(544,514) decoding adds on the order of 100 ns of "
      "latency at 100G-class rates, and its gates and SRAM are a noticeable "
      "part of a high-speed MAC/PCS. PCIe 6.0 chose a lightweight FEC "
      "precisely to keep load-to-use latency low.")

    h2("ECC on memories and links")
    p("Error-correcting codes protect data **at rest**: SRAM buffers, "
      "caches, DRAM, retry buffers. The workhorse is the extended Hamming "
      "**SECDED** code - single-error correction, double-error detection. "
      "For 64 data bits it needs 8 check bits, the familiar (72,64) code of "
      "ECC DIMMs and many on-chip memories. Here is a byte-wide version, "
      "SECDED(13,8), with an exhaustive test of every single, double and "
      "triple error on every data value:")
    _v("secded", "secded.sv - SECDED(13,8) encoder and decoder. The "
                 "syndrome is the XOR of the positions of all set bits; the "
                 "overall parity bit distinguishes single from double "
                 "errors.")
    _v("tb_secded", "tb_secded.sv - exhaustive error injection: all 256 data "
                    "values x all 1-, 2- and 3-bit error patterns.")
    _o("secded", "Real output (Icarus Verilog 12).")
    bul(["All 3328 single-bit errors are **corrected** and all 19,968 "
         "double-bit errors are **flagged uncorrectable** - exactly the "
         "SECDED contract.",
         "**Triple errors are the trap**: 72,704 of 73,216 produce wrong data "
         "reported as a corrected single error (the parity looks odd, so the "
         "decoder 'fixes' one bit and makes things worse or leaves them "
         "wrong). SECDED says nothing about three errors, which is why memory "
         "designs **scrub** (periodically read and correct) so single errors "
         "never accumulate into multiple ones, and why bit-interleaving "
         "places the bits of one codeword physically apart so that one "
         "particle strike upsets only one bit per word."])
    tbl(["Where ECC appears", "Scheme"],
        [["On-chip SRAM (caches, buffers)", "SECDED per 32/64-bit word, or "
          "parity for data that can be re-fetched (instruction caches)"],
         ["DDR4/DDR5 DIMMs (side-band ECC)", "Extra DRAM devices store check "
          "bits: 72-bit channels for DDR4 (SECDED or stronger), 40-bit "
          "subchannels on DDR5 ECC DIMMs; server controllers use symbol-based "
          "'chipkill' codes that survive a whole device failing"],
         ["DDR5 on-die ECC", "Inside every DDR5 device (single-error "
          "correction over 128 data bits); invisible to the controller and "
          "not a replacement for system ECC"],
         ["LPDDR (inline ECC)", "No extra pins: the controller stores check "
          "bits in a reserved part of the same memory, costing bandwidth "
          "and capacity"],
         ["Link retry buffers, NoC packets", "SECDED or parity on the "
          "stored flits"],
         ["HBM", "ECC bits carried alongside data (device-specific options)"]],
        widths=[32, 68])

    h2("Link-level retry versus end-to-end protection")
    p("Detection alone only tells you something is wrong. A protocol must "
      "then decide **who retransmits**. There are two schools, and real "
      "systems use both:")
    tbl(["Approach", "How", "Examples", "Trade-off"],
        [["**Link-level retry**", "Each hop keeps a replay buffer; the "
          "receiver ACKs good packets and NAKs bad ones; the transmitter "
          "replays from the buffer", "PCIe DLL (12-bit sequence number, "
          "LCRC, ACK/NAK DLLPs, replay timer), CXL, UCIe, USB 3.x link "
          "layer, CAN automatic retransmission", "Fast recovery "
          "(sub-microsecond), invisible to software; costs a replay buffer "
          "per hop"],
         ["**End-to-end**", "Only the endpoints check; lost or corrupted data "
          "is retransmitted by a higher layer", "Ethernet (MAC drops bad "
          "frames, TCP retransmits), PCIe ECRC, AUTOSAR E2E", "No per-hop "
          "state; recovery is slower (milliseconds for TCP) but also "
          "catches errors inside switches and bridges"],
         ["**Transaction retry**", "Host re-issues the transaction a limited "
          "number of times", "USB 2.0 (a transaction is typically retried up "
          "to three times before the host reports an error), I2C NACK "
          "handling in software", "Simple; relies on the host"]],
        widths=[15, 32, 30, 23], bold_first=False)
    box("key", "The end-to-end argument",
        "A link CRC protects the wire, not the switch in the middle: a bit "
        "flipped inside a switch's buffer after the CRC was checked and "
        "before it was regenerated arrives with a perfect new CRC. That is "
        "why PCIe offers ECRC in addition to LCRC, why switches protect their "
        "internal buffers with ECC/parity, and why safety-critical software "
        "adds its own end-to-end checks. Link retry makes the common case "
        "fast; end-to-end checks make the rare case safe.")

    h2("Timeouts and error reporting")
    p("A link that stops responding must not hang the SoC. Every requester "
      "needs a timeout, and every error needs somewhere to go.")
    bul(["**Completion timeouts**: a PCIe requester that never receives a "
         "completion reports a completion timeout (the configurable ranges "
         "span tens of microseconds to seconds; the default is typically "
         "in the 50 us to 50 ms range). On-chip, an AXI transaction to a "
         "powered-down or hung slave needs an interconnect timeout unit that "
         "returns SLVERR/DECERR instead of stalling the CPU forever.",
         "**Response codes**: AXI BRESP/RRESP (OKAY, EXOKAY, SLVERR, "
         "DECERR), APB PSLVERR, AHB HRESP, PCIe completion status (SC, UR, "
         "CA, CRS), USB STALL.",
         "**PCIe Advanced Error Reporting (AER)** classifies errors as "
         "**correctable** (e.g. receiver error, bad TLP/DLLP fixed by "
         "replay), **uncorrectable non-fatal** (e.g. completion timeout, "
         "unsupported request, poisoned TLP) and **uncorrectable fatal** (e.g. "
         "data link protocol error, receiver overflow), with status, mask "
         "and severity registers and a header log of the offending TLP.",
         "**Poisoning**: data known to be bad (uncorrectable ECC error) is "
         "forwarded marked as poisoned (PCIe EP bit, CHI data poison, AXI5 "
         "poison) so it is not silently consumed, and the error is reported "
         "where the data is used.",
         "**RAS architecture**: on SoCs, errors from memories, links and "
         "interconnect are collected in error records (Arm RAS extension or "
         "a vendor RAS controller) and raised as interrupts to firmware, "
         "which logs, corrects, isolates or resets."])
    box("warn", "PITFALL: errors that disappear",
        "Frequent post-silicon complaint: 'the link retrains every few hours "
        "and nobody knows why'. Correctable errors were counted in a register "
        "that wraps, or masked by default, or cleared by the driver without "
        "logging. Make error counters saturating and sticky, expose them to "
        "software, and log them - correctable-error trends are the early "
        "warning of a marginal link.")

    h2("Functional safety: ISO 26262 on links and buses")
    p("In automotive (and similarly IEC 61508 industrial) designs, "
      "reliability becomes a quantified, audited requirement. ISO 26262 "
      "assigns each safety goal an **ASIL** from A (lowest) to D (highest) "
      "and, for hardware, sets targets on how well random faults are "
      "detected:")
    tbl(["Metric", "ASIL B", "ASIL C", "ASIL D"],
        [["Single-point fault metric (SPFM)", ">= 90 %", ">= 97 %", ">= 99 %"],
         ["Latent fault metric (LFM)", ">= 60 %", ">= 80 %", ">= 90 %"],
         ["Probabilistic metric for random hardware failures (PMHF)",
          "< 100 FIT", "< 100 FIT", "< 10 FIT"]],
        widths=[46, 18, 18, 18],
        caption="ISO 26262-5 hardware architectural metric targets "
                "(1 FIT = 1 failure per 10^{9} device-hours).")
    p("**Diagnostic coverage (DC)** is the fraction of faults in a block that "
      "a safety mechanism detects. Communication paths have their own "
      "catalogue of mechanisms:")
    tbl(["Safety mechanism", "Protects against", "Typical DC claim"],
        [["Parity on buses / registers", "Single-bit faults in data/address",
          "Low-medium (misses even-bit faults)"],
         ["ECC (SECDED) on memories and buses", "Single and double-bit faults",
          "High"],
         ["CRC on messages", "Corruption on links", "High (depends on CRC and "
          "length)"],
         ["**AMBA 5 interface protection**", "Faults on AXI/CHI wires and in "
          "the interconnect", "Parity check signals per signal group (names "
          "ending in CHK, e.g. `AWADDRCHK`, `WDATACHK`) generated at the "
          "source, checked at the destination"],
         ["Timeouts / watchdogs", "Lost or stuck transactions", "Medium-high"],
         ["**Lockstep** (dual-core or duplicated logic, delayed by a few "
          "cycles and compared)", "Any fault in the duplicated logic, "
          "including the bus master", "High"],
         ["**E2E protection** (AUTOSAR E2E profiles)", "Corruption, loss, "
          "repetition, delay, masquerade anywhere between sender and receiver "
          "software", "High for communication faults"],
         ["Built-in self-test at start-up (LBIST/MBIST)", "Latent permanent "
          "faults", "Improves LFM"]],
        widths=[30, 38, 32], bold_first=False)
    p("AUTOSAR **E2E protection** is the software counterpart of the "
      "end-to-end argument: the sender adds a CRC computed over the data "
      "and a **data ID**, plus an **alive/sequence counter**; the receiver "
      "checks CRC, counter continuity and timing. This detects not only "
      "corruption but lost, repeated, reordered, delayed and misrouted "
      "messages - the full list of communication faults the standard asks "
      "you to consider - regardless of how many buses and gateways the "
      "message crossed.")
    box("expert", "Interview angle: why is parity not enough for ASIL D?",
        "Parity detects only odd numbers of flipped bits, and a single fault "
        "in shared logic (a mux select, an address decoder) can corrupt data "
        "and its parity consistently. High-ASIL designs therefore combine "
        "ECC or CRC for data, protection of control signals (AMBA 5 check "
        "signals cover VALID/READY too), timeouts for liveness, and "
        "redundancy (lockstep) for logic, then prove the coverage with fault "
        "injection campaigns in simulation or emulation.")

    h2("Security on links")
    p("Security threats to links are different from random errors: an "
      "attacker chooses the errors. A CRC is no protection at all - anyone "
      "can recompute it. Integrity against an attacker needs a "
      "cryptographic MAC (message authentication code), confidentiality "
      "needs encryption, and both need keys that were exchanged with an "
      "**authenticated** partner.")
    tbl(["Mechanism", "Link", "How it works"],
        [["**PCIe IDE** (Integrity and Data Encryption)", "PCIe 5.0 (as an "
          "ECN) and 6.0", "AES-GCM with 256-bit keys protects TLPs per "
          "stream (link IDE between neighbours, selective IDE end to end "
          "through switches); keys are programmed with the IDE_KM protocol "
          "over DMTF SPDM secure sessions after device authentication"],
         ["**CXL IDE**", "CXL 2.0 and later", "AES-GCM-256 on CXL.io, "
          "CXL.cache and CXL.mem flits, with a containment or skid mode to "
          "trade latency against when data may be consumed"],
         ["**MACsec** (IEEE 802.1AE)", "Ethernet, hop by hop", "GCM-AES-128 "
          "(256 optional) per frame; a SecTAG after the MAC addresses "
          "(EtherType 0x88E5) and a 16-byte ICV before the FCS; keys "
          "agreed by MKA (IEEE 802.1X); line-rate crypto in the MAC/PHY"],
         ["**HDCP 2.x**", "HDMI, DisplayPort, (wireless) display links",
          "Receiver authentication with certificates, a locality check "
          "(round-trip time limit) and AES-128 in counter mode to encrypt "
          "content"],
         ["**USB Type-C Authentication**", "USB", "Certificate-based "
          "challenge/response so a host can verify a device or charger "
          "before trusting it"],
         ["**SPDM** (DMTF)", "PCIe, CXL, USB, MCTP-based management",
          "Device identity (certificates), measurement attestation and secure "
          "sessions: the common authentication layer under several of the "
          "above"]],
        widths=[25, 18, 57], bold_first=False)
    bul(["**Latency and area**: an AES-GCM engine at hundreds of Gb/s is a "
         "wide, pipelined datapath adding tens of nanoseconds; on-chip links "
         "are usually trusted and left unencrypted, while off-chip links "
         "that cross untrusted hardware (a PCIe bus in a cloud server, a "
         "CXL memory expander) get IDE.",
         "**Replay and ordering**: authenticated encryption uses a counter or "
         "packet number as the nonce, which also detects replayed or dropped "
         "packets - the security analogue of sequence numbers.",
         "**Keys** live in hardware key slots loaded by a security "
         "controller; the RTL must make sure they are not readable over the "
         "normal bus or visible in scan chains."])

    h2("On-chip access control: TrustZone, AxPROT and firewalls")
    p("Inside the SoC the threat is a less-privileged master (a normal-world "
      "OS, a DMA-capable peripheral, a compromised accelerator) reading or "
      "writing what it should not. The bus protocols carry the attributes "
      "needed to stop it:")
    tbl(["Signal", "Meaning", "Notes"],
        [["`AxPROT[0]`", "1 = privileged access", "From the CPU's exception "
          "level / mode"],
         ["`AxPROT[1]`", "1 = **non-secure** access (the TrustZone NS bit)",
          "Secure memory and peripherals reject or ignore NS accesses"],
         ["`AxPROT[2]`", "1 = instruction access", "Hint for caches/"
          "firewalls"],
         ["`HPROT`, `HNONSEC` (AHB5), `PPROT` (APB4+)", "Equivalent "
          "attributes on AHB and APB", "Must be propagated through bridges"],
         ["`AxUSER`, `AxID`, stream IDs", "Master identity",
          "Used by SMMUs and firewalls to apply per-master rules"]],
        widths=[27, 38, 35], bold_first=False)
    bul(["**TrustZone address-space controllers / memory firewalls** (e.g. "
         "Arm TZC-400-style components) sit in front of DRAM and check each "
         "access's security attribute and master ID against programmable "
         "regions.",
         "**Peripheral protection controllers** mark each peripheral secure "
         "or non-secure; the interconnect or bridge returns an error (or "
         "read-as-zero, write-ignored) for violations.",
         "**MPUs and SMMUs/IOMMUs** restrict what DMA masters can reach - "
         "essential because a DMA engine that can write anywhere bypasses "
         "all CPU-side protection.",
         "**Propagation** is where bugs hide: a bridge that drops `PPROT`, an "
         "AXI-to-AHB converter that ties `HNONSEC` to 0 (making every access "
         "secure!), a DMA that issues all accesses with its own secure "
         "attribute on behalf of non-secure software (the 'confused "
         "deputy')."])
    box("warn", "PITFALL: tie-offs that grant privileges",
        "When integrating IP with fewer attribute bits than the "
        "interconnect, engineers tie the missing inputs to constants. Tying "
        "`AxPROT` to 3'b000 declares every access **secure and privileged**. "
        "Tie-offs of security attributes must default to the least "
        "privilege (non-secure, unprivileged) and be reviewed by the "
        "security architect.")

    h2("Secure debug and lifecycle")
    p("Debug ports (JTAG, SWD, CoreSight DAP, Chapter 23) can read and write "
      "everything - that is their job, and it makes them the easiest attack "
      "path into a product. Secure SoCs therefore gate debug:")
    bul(["**Authentication signals**: Arm cores and CoreSight components "
         "take `DBGEN` (invasive debug), `NIDEN` (non-invasive: trace, "
         "profiling) and secure variants `SPIDEN`/`SPNIDEN`; a security "
         "controller drives them, not a tie-off.",
         "**Debug authentication**: a challenge-response protocol (signed "
         "certificate or token) unlocks debug for an authorized user, "
         "possibly only for the non-secure world.",
         "**Lifecycle states** stored in OTP/fuses: e.g. test/manufacturing, "
         "development, production (debug locked), RMA (return: re-opened "
         "after secrets are erased), end of life. Transitions are one-way "
         "or authenticated; production parts must not expose scan chains or "
         "memory BIST that can dump secrets.",
         "**Scan and DFT**: scan chains can shift out key registers; secure "
         "designs reset or exclude secret-holding flops when entering test "
         "mode."])

    h2("Fault-injection and physical attacks")
    p("An attacker with physical access can cause errors deliberately to "
      "skip a security check - for example glitching the clock or supply "
      "exactly when the boot ROM compares a signature. Links and their "
      "error handling are part of this attack surface.")
    tbl(["Attack", "Method", "Countermeasures"],
        [["Clock glitching", "Insert a short clock pulse so a flop captures "
          "before logic settles", "Clock monitors, glitch filters, "
          "internal oscillators for security logic"],
         ["Voltage glitching", "Brief supply droop or spike",
          "Voltage/brown-out detectors, sensors that reset the chip"],
         ["Electromagnetic / laser fault injection", "Localized upsets of "
          "individual gates or flops", "Redundant computation and "
          "comparison, duplicated checks, light sensors, shields"],
         ["Side-channel analysis", "Power or EM traces leak key bits",
          "Masked/constant-time crypto implementations"],
         ["Bus probing / interposers", "Read or modify off-chip traffic",
          "Link encryption (IDE, MACsec), memory encryption, tamper "
          "detection"]],
        widths=[22, 35, 43], bold_first=False)
    box("tip", "Reliability and security meet",
        "The same hardware serves both goals: parity and ECC also detect "
        "many injected faults, duplicated FSMs with comparison (lockstep for "
        "security) catch glitches, and error counters reveal an attack in "
        "progress. Design security-critical FSMs with sparse, "
        "Hamming-distant state encodings and a safe default for illegal "
        "states.")

    h2("Summary")
    bul(["Links fail randomly (BER), in bursts, through soft and hard faults, "
         "through design bugs and through attacks; each needs a different "
         "defence.",
         "An r-bit CRC detects all bursts up to r bits, lets about 2^{-r} of "
         "random garbage through, and its Hamming distance depends on the "
         "frame length - the experiment showed CRC-8 losing HD = 4 beyond "
         "119 data bits while CRC-32 caught every corrupted frame.",
         "FEC (RS(528,514), RS(544,514), PCIe 6.0 flit FEC, LDPC) corrects "
         "errors at the cost of latency and area; PAM4 links need it.",
         "SECDED corrects one and detects two errors per word but miscorrects "
         "most triple errors; scrubbing and bit-interleaving keep errors "
         "single.",
         "Link-level retry (PCIe, CXL, UCIe) gives fast recovery; end-to-end "
         "checks (ECRC, TCP, AUTOSAR E2E) catch errors inside the path.",
         "Timeouts, response codes, AER-style classification, poisoning and "
         "a RAS architecture make errors visible and recoverable.",
         "ISO 26262 quantifies safety (SPFM/LFM/PMHF per ASIL) and uses parity, "
         "ECC, CRC, AMBA 5 check signals, timeouts, lockstep and E2E "
         "protection as safety mechanisms.",
         "Security needs cryptographic integrity (PCIe/CXL IDE, MACsec, HDCP) "
         "with authenticated key exchange (SPDM), correct propagation of "
         "AxPROT/NS attributes, firewalls and SMMUs, locked-down debug and "
         "fault-injection countermeasures."])

    h2("Exercises")
    bul(["A 25 Gb/s link runs at BER 1e-12 and carries 1500-byte frames "
         "protected by CRC-32. Estimate the frame error rate and the rate of "
         "undetected frames assuming random garbage escapes with probability "
         "2^{-32}. How would a 1e-6 raw BER change the design?",
         "Modify crc_exp.py to measure CRC-16/CCITT (polynomial 0x1021) on "
         "the same frames. Which rows change, and why?",
         "Extend the SECDED(13,8) decoder so that it also flags syndromes "
         "13-15 (which cannot come from a single error) as uncorrectable. "
         "How do the triple-error statistics change?",
         "Explain step by step how PCIe's data link layer recovers from a "
         "corrupted TLP and from a lost ACK DLLP. Which timers and counters "
         "are involved?",
         "For an ASIL D brake controller receiving wheel-speed messages over "
         "CAN FD through a gateway, list the communication faults ISO 26262 "
         "asks you to consider and the mechanism that detects each.",
         "An AXI DMA engine executes descriptors written by non-secure "
         "software. What attributes should its memory accesses carry, and "
         "what goes wrong if it always issues secure accesses?"],
        ordered=True)


# ---------------------------------------------------------------- Ch 27 ---
def _ch27():
    chapter("Choosing and Budgeting Protocols for an SoC, and the Learning "
            "Roadmap")
    p("The previous 26 chapters described protocols one by one. An SoC "
      "architect faces the inverse problem: given a product - a camera, a "
      "phone, an automotive controller, an AI accelerator card - which "
      "protocols should the chip have, how many lanes and pins, how much "
      "memory bandwidth, and what will they cost in area, power and "
      "licences? This chapter gives a method, a comparison table to choose "
      "from, worked bandwidth and latency budgets, a reference edge-AI SoC "
      "and, to close the book, a roadmap for learning all of this.")

    h2("From requirements to a protocol")
    diagram([
        "  product requirements (use cases, data rates, partners, cost, safety)",
        "        |",
        "        v",
        "  1. Who is on the other end?  (standard device -> the standard it speaks:",
        "        |                        DDR/LPDDR, camera -> CSI-2, SSD -> PCIe/NVMe)",
        "        v",
        "  2. Bandwidth (sustained + peak) and latency needed?  -> class of link",
        "        |",
        "        v",
        "  3. Distance / medium: on-die, die-to-die, board, cable, vehicle harness",
        "        |",
        "        v",
        "  4. Pins, power, area, licence cost, ecosystem, certification",
        "        |",
        "        v",
        "  5. Reliability / safety / security requirements (CRC? retry? ASIL? IDE?)",
        "        |",
        "        v",
        "  choice + lane/pin count + controller/PHY IP + budget entries"],
        "A protocol selection flow. The first question usually decides: if "
        "the partner is a standard part, you speak its protocol.")
    bul(["**Partner first.** A DRAM speaks DDR/LPDDR/HBM, a camera sensor "
         "speaks MIPI CSI-2 (sometimes SLVS-EC or LVDS), an SSD speaks PCIe "
         "(NVMe), a PMIC speaks I2C/SPMI/I3C, a sensor hub speaks I2C, SPI or "
         "I3C, a car network speaks CAN FD, LIN or automotive Ethernet. The "
         "choice is often made for you; the architecture work is in the "
         "number of instances, lanes and speeds.",
         "**On-chip** choices are yours: APB for registers, AXI for "
         "high-bandwidth masters and memory, ACE-Lite/CHI where coherency is "
         "needed, AXI-Stream for pipelines, a NoC when the number of "
         "initiators and targets grows (Chapters 5-10).",
         "**Chip-to-chip between your own devices**: PCIe/CXL if you want "
         "software and ecosystem support, a lightweight SerDes protocol "
         "(Aurora, Interlaken, JESD204 for converters) if you want low "
         "overhead, UCIe/BoW for dies in one package (Chapter 22).",
         "**Prefer the simplest protocol that meets the need**: a sensor "
         "that sends 100 bytes a second does not need I3C HDR; a status LED "
         "controller does not need SPI when I2C is already routed."])

    h2("The big comparison table")
    tbl(["Protocol", "Rate (typ./max)", "Signals / pins", "Reach",
         "Topology", "Cplx", "Typical SoC use"],
        [["UART", "115.2 kb/s - few Mb/s", "2 (TX, RX) + opt. RTS/CTS",
          "Board; km with RS-485", "Point-to-point", "Low",
          "Console, debug, BT/GNSS modules"],
         ["SPI", "10-100+ MHz", "4 + 1 CS per target", "Board", "1 controller, "
          "N targets", "Low", "Sensors, displays, NOR flash, ADCs"],
         ["Quad/Octal SPI, xSPI", "Up to ~200 MHz DDR x8 (~400 MB/s)",
          "6-12", "Board", "Point-to-point", "Med", "Boot flash, XIP, PSRAM"],
         ["I2C", "100 k / 400 k / 1 M / 3.4 Mb/s", "2 open-drain", "Board",
          "Multi-drop, multi-controller", "Low/Med", "PMIC, EEPROM, sensors, "
          "config"],
         ["I3C", "12.5 Mb/s SDR, more in HDR modes", "2", "Board",
          "Multi-drop, dynamic addressing, in-band interrupts", "Med",
          "Sensor hubs, DDR5 SPD/sideband"],
         ["CAN FD", "Arbitration <= 1 Mb/s, data phase typically 2-8 Mb/s",
          "2 (via transceiver)", "~40 m (vehicle)", "Multi-drop bus", "Med",
          "Automotive ECUs"],
         ["I2S / TDM", "Few Mb/s", "3-4", "Board", "Point-to-point",
          "Low", "Audio codecs, microphones"],
         ["APB / AHB / AXI", "Bus clock x width (AXI: tens of GB/s)",
          "On-chip wires", "On-die", "Bus / crossbar / NoC", "Low to High",
          "Registers, memory, DMA"],
         ["USB 2.0 / 3.2 / USB4", "480 Mb/s / 5-20 Gb/s / 40-80 Gb/s",
          "2 / +4 / Type-C", "Cable, few m", "Tiered star (host-centric)",
          "High", "Peripherals, charging, docking"],
         ["PCIe Gen4 / 5 / 6", "16 / 32 / 64 GT/s per lane", "4 per lane "
          "+ refclk", "Board, cable with retimers", "Point-to-point, "
          "switches", "Very high", "SSD, NIC, accelerators, CXL"],
         ["Ethernet (1G-400G)", "1-400 Gb/s", "RGMII 12, SGMII/SerDes 4",
          "100 m copper, km fibre", "Switched", "High", "Networking, "
          "automotive backbone"],
         ["LPDDR5/5X", "6400-8533+ MT/s x16 channel", "~35-45 per x16 "
          "channel", "Package/board, cm", "Point-to-point", "Very high",
          "Main memory of mobile/edge SoCs"],
         ["HBM3/3E", "6.4-9.6 Gb/s per pin x 1024", "1024 data + CA; thousands of micro-bumps",
          "Interposer, mm", "Point-to-point", "Very high", "AI/HPC memory"],
         ["MIPI CSI-2 / DSI (D-PHY)", "Up to 2.5 (v1.2) / 4.5 (v2.5) Gb/s per lane, 1-4 lanes",
          "2 per lane + clock pair", "Board / flex, cm", "Point-to-point",
          "Med/High", "Cameras, displays"],
         ["UCIe", "4-32 GT/s per lane", "Many micro-bumps per module",
          "Package, mm", "Die-to-die", "High", "Chiplets"],
         ["JTAG / SWD", "~10-50 MHz", "4-5 / 2", "Board", "Daisy chain / "
          "point-to-point", "Low/Med", "Debug, boundary scan, test"]],
        widths=[12, 16, 14, 13, 13, 10, 22], bold_first=True,
        caption="Protocol comparison (typical values; exact maxima depend "
                "on the spec version and implementation). Appendix A has a "
                "longer quick-reference.")

    h2("Bandwidth budgeting: a worked example")
    p("The most consequential budget in most SoCs is **DRAM bandwidth**, "
      "because almost every high-rate client passes through it. Consider an "
      "edge-AI camera: a 4K30 sensor, an ISP, a neural-network accelerator "
      "(NPU) running object detection, an H.265 encoder for recording and "
      "streaming, and a 1080p60 local display.")
    diagram([
        "  sensor --CSI-2 4L--> [ISP] <--3DNR ref frames--> DDR",
        "                         |",
        "                         +--NV12 frames--> DDR --+--> [H.265 enc] <--ref frames--> DDR",
        "                                                 |          |",
        "                                                 |          +--> bitstream --> ETH/USB",
        "                                                 +--> [scaler] --> DDR --> [NPU]",
        "                                                                             ^",
        "                                                  weights, activation spills |",
        "                                                                             v",
        "                                                                            DDR",
        "  DDR --> [display ctrl] --DSI/HDMI--> 1080p60 panel      CPU <--> DDR (OS, apps)"],
        "Data flow of the edge-AI camera. Every arrow that touches DDR "
        "costs bandwidth - often more than once per frame.")
    p("The script below turns the data flow into numbers. Each client's "
      "traffic is derived from frame sizes and rates; the less predictable "
      "clients (NPU weights and activation spills, CPU) are explicit "
      "assumptions that the architect would refine with the NPU compiler "
      "and CPU benchmarks.")
    _v("bw", "bw.py - a first-order DRAM bandwidth budget and a CSI-2 lane "
             "check.")
    _o("bw", "Real output (Python 3).")
    p("How to read the budget:")
    bul(["**The camera link**: 4K30 RAW12 is 2.99 Gb/s of pixels; with an "
         "assumed 20 % for blanking and packet overhead it needs about "
         "3.6 Gb/s. Four D-PHY lanes at about 0.9 Gb/s each leave plenty of "
         "margin (D-PHY v1.2 allows up to 2.5 Gb/s per lane); two lanes at "
         "1.8 Gb/s also fit, saving four pins at a smaller margin.",
         "**Total DRAM traffic** is about 6.6 GB/s - though the sensor "
         "delivers only 0.37 GB/s: every stage that stores and re-reads a "
         "frame multiplies traffic. The encoder alone (current frame plus "
         "reference reads and reconstructed-frame writes) is almost "
         "1.5 GB/s.",
         "**Efficiency** is the key assumption: real DRAM delivers perhaps "
         "60-80 % of its peak because of refresh, bank conflicts, "
         "read/write turnarounds and page misses (Chapter 20). At 65 % "
         "efficiency an LPDDR4X-4266 x32 interface would be 59 % loaded - "
         "workable but with little headroom for peaks; LPDDR5-6400 x32 "
         "brings it to about 40 %.",
         "**Headroom**: architects typically keep the average load well below "
         "the usable bandwidth (often targeting 60-70 % or less) because "
         "clients are bursty and real-time clients (display, ISP) must never "
         "starve. QoS in the interconnect and memory controller gives the "
         "display and ISP priority over the CPU and NPU."])
    box("tip", "Cut traffic before buying bandwidth",
        "The cheapest bandwidth is the traffic you never generate: stream "
        "ISP output directly to the encoder and scaler through on-chip "
        "buffers instead of DDR, keep NPU weights in on-chip SRAM when the "
        "model fits, use frame-buffer compression (lossless compression "
        "schemes for display and video buffers typically save 30-50 %), "
        "and pick 8-bit instead of 10-bit formats where quality allows.")
    box("warn", "PITFALL: budgeting averages only",
        "A budget computed from averages hides peaks: a 20 ms NPU burst "
        "overlapping an encoder reference fetch and a display refresh can "
        "exceed peak bandwidth even when the average load is 50 %. Model the "
        "worst concurrent phase, check the FIFO depth of every real-time "
        "client against the worst stall (Chapter 24), and validate with a "
        "cycle-accurate performance model or emulation running real "
        "traffic.")

    h2("Latency budgets")
    p("Some products care more about latency than bandwidth: a driver-"
      "assistance camera must go from photons to braking decision in tens of "
      "milliseconds; a control loop over an industrial bus must close in "
      "microseconds; a CPU load that misses the cache waits for DRAM. "
      "Latency budgets are built the same way - sum every stage and add "
      "margin:")
    tbl(["Stage (camera-to-decision example)", "Typical contribution",
         "Levers"],
        [["Sensor exposure + readout", "Several ms to one frame time "
          "(33 ms at 30 fps)", "Higher frame rate, rolling vs global "
          "shutter"],
         ["CSI-2 transfer", "Same as readout (streaming, line by line)",
          "More lanes do not reduce it if the sensor reads out slower"],
         ["ISP", "A few lines to a frame, depending on whether it stores "
          "full frames (3DNR)", "Line-based processing, bypass stages"],
         ["DDR write + NPU read", "Up to one frame if the NPU waits for a "
          "complete frame", "Tile/slice-based hand-off"],
         ["NPU inference", "Milliseconds to tens of ms", "Model size, INT8, "
          "SRAM tiling"],
         ["Decision output over CAN FD / Ethernet", "Hundreds of us to ms",
          "Priority/TSN scheduling"]],
        widths=[34, 36, 30], bold_first=False)
    tbl(["Transaction", "Order of magnitude"],
        [["AXI access to a local SRAM", "A few cycles"],
         ["AXI read through an interconnect to DRAM (loaded)", "About "
          "80-150 ns"],
         ["PCIe read round trip (host memory from a device)", "About "
          "0.5-1 us"],
         ["UCIe / die-to-die hop", "A few ns (adapter + PHY)"],
         ["I2C register read at 400 kHz (address + reg + data, ~40 bits)",
          "About 100 us"],
         ["CAN FD frame, 64 bytes, data phase 2-5 Mb/s", "Around 150-400 us"]],
        widths=[62, 38],
        caption="Latency reference points (orders of magnitude, not "
                "guarantees).")

    h2("Pin and IO budgets")
    p("Pins are expensive: they set the package size and ball count, board "
      "layers and cost. An IO budget lists every interface, its signal "
      "count, IO type and voltage, and the pads it needs:")
    tbl(["Interface", "Signals", "IO type", "Notes"],
        [["LPDDR5 x32 (2 x16 channels)", "~80-90", "DDR PHY bumps",
          "Plus supplies; placed on the die edge nearest the DRAM"],
         ["MIPI CSI-2 4-lane D-PHY", "10 (4 data pairs + clock pair)",
          "D-PHY macro", "x2 for two cameras"],
         ["MIPI DSI 4-lane or HDMI 2.0", "10 / 19-pin connector",
          "PHY macro", "Plus HPD, DDC (I2C)"],
         ["PCIe Gen4 x1 or x2", "4 per lane + 2 refclk", "SerDes macro",
          "For Wi-Fi module or NVMe"],
         ["USB 3.2 Gen1 + USB 2.0", "4 SS + 2 HS (+ Type-C CC)", "SerDes + "
          "USB 2.0 PHY", "Type-C needs a PD controller or on-chip logic"],
         ["Gigabit Ethernet RGMII", "12 + MDIO/MDC 2", "GPIO (1.8/2.5/3.3 V)",
          "Delay (2 ns) on RGMII clocks: PHY, MAC or PCB"],
         ["eMMC/SD or UFS", "11 (eMMC 8-bit) / 4+refclk (UFS)", "GPIO / "
          "M-PHY", "Boot and storage"],
         ["Octal SPI flash", "11-12", "GPIO", "Boot ROM path"],
         ["I2C x4, SPI x2, UART x3, I2S x2, CAN FD x2", "~40", "GPIO (muxed)",
          "Pin-mux makes these flexible"],
         ["JTAG/SWD, boot mode, reset, clocks, PMIC", "~15", "GPIO / analog",
          "Fixed function, not muxed"]],
        widths=[30, 22, 18, 30], bold_first=False)
    p("Pin-muxing lets many low-speed peripherals share pads - the product "
      "chooses which functions appear on which balls. High-speed interfaces "
      "cannot be muxed freely: their pads are part of PHY macros with fixed "
      "placement, and their package routing is part of the signal-integrity "
      "budget.")

    h2("Power, area and cost")
    tbl(["Link class", "Energy per bit (order of magnitude)", "Comment"],
        [["On-chip wire / NoC", "~0.1 pJ/bit per mm plus switching",
          "Cheapest; grows with distance"],
         ["Die-to-die (UCIe, BoW) in a package", "Roughly 0.3-1 pJ/bit",
          "Short, unterminated or lightly terminated, dense bumps"],
         ["HBM", "A few pJ/bit (interface)", "Wide and slow per pin; "
          "interposer"],
         ["LPDDR5/5X", "A few pJ/bit (interface), more with DRAM core",
          "Low-swing, unterminated or lightly terminated"],
         ["Board-level SerDes (PCIe, USB, Ethernet)", "Roughly 5-15 pJ/bit",
          "Equalization, CDR, termination; long-reach costs most"],
         ["Low-speed GPIO protocols", "High per bit, tiny in total",
          "Irrelevant to power at kb/s-Mb/s rates"]],
        widths=[34, 34, 32],
        caption="Indicative energy per bit. Use vendor data for real "
                "budgets; these ratios are what matters for "
                "architecture.")
    bul(["**Idle power** often dominates average power: link power states "
         "(USB U1-U3, PCIe L0s/L1/L1 substates, Ethernet EEE, D-PHY LP mode, "
         "LPDDR self-refresh) and clock gating matter as much as active "
         "pJ/bit.",
         "**Area**: a SerDes lane is a large mixed-signal macro; a DDR PHY "
         "occupies a long stretch of die edge; controllers with deep buffers "
         "are SRAM-dominated. Low-speed peripherals are nearly free by "
         "comparison.",
         "**Cost** includes licence fees and royalties for controllers and "
         "PHYs, VIP licences, compliance testing and logo programmes, "
         "standards-body membership, package and board cost of pins, and "
         "the schedule risk of a complex interface."])

    h2("A reference edge-AI SoC and its protocol map")
    diagram([
        "                        +-------------------------------------------------+",
        "LPDDR5X x32   <=======> | DDR PHY | LPDDR ctrl <----------+  coherent NoC |",
        "2x cameras -CSI-2 4L--> | D-PHY RX | CSI-2 RX | ISP -AXI->+  (CHI + AXI)  |",
        "panel <----DSI 4L------ | D-PHY TX | display <-AXI--------+  with QoS     |",
        "                        | CPU cluster (4x) -CHI---------->+       |       |",
        "                        | NPU (SRAM + DMA) -AXI---------->+       |       |",
        "                        | H.265 codec -AXI--------------->+       |       |",
        "NVMe/Wi-Fi <-PCIe G4--> | SerDes | PCIe RC -ACE-Lite----->+       |       |",
        "USB-C <-USB 3.2 / 2.0-> | SerDes+UTMI | xHCI/DRD -AXI---->+       |       |",
        "Ethernet PHY <-RGMII--> | GMAC (TSN, MACsec) -AXI-------->+       |       |",
        "boot flash <--xSPI----> | xSPI controller -AXI----------->+       |       |",
        "eMMC / SD <-----------> | SDHC -AXI---------------------->+       |       |",
        "                        | APB bridge <----------------------------+       |",
        "                        |   -> I2C x4, I3C, SPI x2, UART x3,              |",
        "                        |      I2S x2, CAN FD x2, PWM, GPIO               |",
        "PMIC <--I2C/SPMI------> | security subsystem (keys, OTP, lifecycle)       |",
        "debugger <-JTAG/SWD---> | CoreSight DAP + trace; 1500/IJTAG to PHYs       |",
        "                        +-------------------------------------------------+"],
        "Protocol map of a representative edge-AI vision SoC. Every "
        "protocol of this book appears somewhere on it.")
    tbl(["Subsystem", "Protocols", "Chapter"],
        [["Memory", "LPDDR5X, DFI, AXI/CHI to the memory controller, QoS",
          "7, 9, 20"],
         ["Vision in / out", "MIPI CSI-2 and DSI over D-PHY; HDMI/DP on "
          "some variants", "21"],
         ["Compute", "CHI (coherent CPU cluster), AXI (NPU, codec), "
          "AXI-Stream inside pipelines", "7-9"],
         ["Expansion and storage", "PCIe Gen4 (NVMe/Wi-Fi), USB 3.2 + 2.0 "
          "with Type-C, xSPI, eMMC/SD", "12, 17, 18, 20"],
         ["Networking", "Gigabit Ethernet RGMII with TSN; optional MACsec",
          "19, 26"],
         ["Control and peripherals", "APB, I2C, I3C, SPI, UART, I2S, CAN FD",
          "5, 11-16"],
         ["Debug, test, security", "JTAG/SWD, CoreSight, IEEE 1500/1687, "
          "TrustZone attributes, secure debug", "23, 26"]],
        widths=[22, 58, 20], bold_first=True)

    h2("The learning roadmap")
    p("Protocols are learned best by building them. The roadmap below "
      "orders them so that each step reuses what the previous one taught; "
      "every step ends with RTL, a self-checking testbench and - from "
      "step 2 on - a demonstration on an inexpensive FPGA board talking to "
      "real devices.")
    tbl(["Step", "Learn", "Build (and put on an FPGA)", "Skills gained"],
        [["1", "Digital basics, FSMs, CDC (Ch 2-4)", "UART TX/RX with "
          "oversampling; talk to a PC terminal", "Serial framing, "
          "oversampling, synchronizers, testbenches"],
         ["2", "SPI (Ch 12)", "SPI controller reading a sensor or an ADC; "
          "SPI flash read", "Modes (CPOL/CPHA), shift registers, chip "
          "select timing"],
         ["3", "I2C (Ch 13)", "I2C controller reading an EEPROM or "
          "temperature sensor", "Open-drain, arbitration, clock "
          "stretching, ACK/NACK"],
         ["4", "APB (Ch 5)", "APB register block + APB wrappers for your "
          "UART/SPI/I2C", "CSRs, bus handshakes, register maps"],
         ["5", "AXI4-Lite / AXI4 / AXI-Stream (Ch 7-8)", "AXI-Lite slave, "
          "AXI DMA to stream (Ch 24), connect to a soft or hard CPU",
          "Channels, bursts, IDs, back-pressure, performance"],
         ["6", "Ethernet MAC (Ch 19)", "10/100/1G MAC with RGMII, CRC-32, "
          "send UDP packets to a PC", "Framing, CRC, xMII, MDIO, PHY "
          "bring-up, Wireshark debugging"],
         ["7", "PCIe or USB (Ch 17-18)", "Use the FPGA's hard PCIe/USB block; "
          "write the DMA engine and a Linux driver", "Layered protocols, "
          "enumeration, config space, drivers"],
         ["8", "Memory, video, D2D, safety/security (Ch 20-26)", "DDR "
          "controller via vendor PHY; CSI-2 receiver; verification with "
          "SVA/UVM and error injection", "System-level integration and "
          "verification"]],
        widths=[6, 22, 40, 32], bold_first=False)
    bul(["**Read the specs**: start with the short, public ones (NXP "
         "UM10204 for I2C, Arm AMBA APB/AXI specifications, Motorola/NXP "
         "SPI application notes), then move to summaries of the large ones "
         "(PCIe, USB) before tackling their full text.",
         "**Use real tools**: a logic analyzer with protocol decoders for "
         "UART/SPI/I2C/CAN, Wireshark for Ethernet, lspci/lsusb and kernel "
         "logs for PCIe/USB. Seeing real traffic teaches what the timing "
         "diagrams mean.",
         "**Verify like a professional**: every project gets a self-checking "
         "testbench, assertions on its interfaces, error injection and "
         "coverage - the habits of Chapter 25.",
         "**Publish**: a clean repository of these projects with testbenches "
         "and waveforms is the best evidence of skill in an interview."])

    h2("Roles: who does what with protocols")
    tbl(["Role", "Protocol work"],
        [["**SoC architect**", "Selects protocols, sizes lanes, bandwidth, "
          "latency and buffers; defines the interconnect and QoS"],
         ["**RTL / IP design engineer**", "Designs controllers, bridges, "
          "DMA engines, PCS logic; integrates vendor IP"],
         ["**Design verification (DV)**", "Builds testbenches with VIP, "
          "assertions, scoreboards, coverage; runs error injection and "
          "compliance-style suites"],
         ["**PHY / analog / mixed-signal**", "Designs SerDes, DDR and MIPI "
          "PHYs, PLLs, equalizers; characterizes jitter and eyes"],
         ["**Physical design / package / SI-PI**", "Places PHY macros and "
          "pad rings, routes high-speed signals, does signal and power "
          "integrity for package and board"],
         ["**DFT**", "Test access to PHYs (IEEE 1500/1687), loopback and "
          "PRBS for production test, boundary scan"],
         ["**Firmware / driver**", "Bring-up sequences, drivers, link "
          "training firmware, error handling and power management"],
         ["**Post-silicon validation**", "Protocol analyzers, BERT, "
          "compliance testing, interoperability, margining"],
         ["**Safety / security architect**", "Safety mechanisms and "
          "metrics, link encryption, access control, secure debug"]],
        widths=[30, 70])

    h2("Interview preparation")
    p("Protocol questions are staples of RTL, DV and architecture "
      "interviews. They test whether you understand **why** a protocol works "
      "the way it does, not whether you memorized a table. Prepare to:")
    bul(["**Draw timing diagrams** from memory: APB write with wait states, "
         "AXI write with WVALID before AWVALID, SPI mode 0 and 3, an I2C "
         "read with repeated START, a UART frame with parity.",
         "**Explain design choices**: why AXI has separate address and data "
         "channels, why I2C is open-drain, why PCIe uses credits and ACK/NAK, "
         "why USB uses NRZI with bit stuffing, why CAN arbitration is "
         "non-destructive, why HBM is wide and slow.",
         "**Compute**: link bandwidth after encoding overhead (8b/10b, "
         "128b/130b), DRAM bandwidth with efficiency, FIFO depth for a burst "
         "or a round trip, number of outstanding transactions for a target "
         "throughput, CRC properties.",
         "**Write RTL on a whiteboard**: a UART transmitter, an SPI "
         "controller, an APB slave, a valid/ready skid buffer, a CRC "
         "generator, a round-robin arbiter.",
         "**Debug scenarios**: 'the AXI master hangs', 'the I2C bus is stuck "
         "low', 'PCIe link trains to Gen1 only', 'Ethernet drops 1 packet in "
         "10^{5}', 'USB enumerates on one host but not another'. Walk through "
         "hypotheses and the measurements that distinguish them.",
         "Appendix C has 100 protocol interview questions with answers."])
    box("expert", "Three questions that separate levels",
        "(1) 'Can an AXI slave wait for WVALID before asserting AWREADY?' - "
        "yes; it is the master that must not make VALID depend on READY. "
        "(2) 'Why does PCIe need both flow-control credits and ACK/NAK?' - "
        "credits prevent receiver buffer overflow, ACK/NAK recovers from "
        "transmission errors; they solve different problems at different "
        "layers. (3) 'How many outstanding reads does a DMA need to reach "
        "10 GB/s with 150 ns memory latency and 64-byte bursts?' - "
        "bandwidth x latency = 1500 bytes, so at least 24 outstanding "
        "64-byte reads.")

    h2("Final checklist")
    checklist("Protocols on an SoC: the end-to-end checklist", [
        "Each external interface is chosen from the partner's standard, with "
        "version, speed, lane count and options documented.",
        "On-chip protocols and interconnect topology chosen per traffic "
        "class (registers, bulk data, coherent, streaming), with QoS.",
        "Bandwidth budget per client and for DRAM, with efficiency and peak "
        "phases; latency budget for the critical paths.",
        "Buffers and outstanding transactions sized from bandwidth x "
        "latency; FIFOs of real-time clients cover worst-case stalls.",
        "Pin/IO budget agreed with package and board; pin-mux, IO voltages "
        "and open-drain needs verified.",
        "Clock, reset, power-domain and low-power-state plans per "
        "interface; PHY bring-up sequence captured in the programming guide.",
        "Controller/PHY/VIP make-or-buy decided; silicon proof and "
        "compliance status of licensed IP checked.",
        "Verification plan with protocol checkers, scoreboards, error "
        "injection, coverage, formal where it fits; compliance and "
        "interoperability testing scheduled.",
        "Reliability: CRC/FEC/ECC/retry/timeouts/error reporting specified; "
        "error counters visible to software.",
        "Safety (ASIL targets, safety mechanisms, metrics) and security "
        "(IDE/MACsec, access control attributes, secure debug) reviewed.",
        "Test modes for bring-up and production (loopback, PRBS, BIST, "
        "IEEE 1500 access) designed in.",
        "Firmware and drivers developed on FPGA/emulation before silicon."])

    h2("Summary")
    bul(["Choose protocols from the partner outward: standard devices "
         "dictate their interfaces; on-chip and chip-to-chip choices trade "
         "bandwidth, latency, pins, power, cost and ecosystem.",
         "Budget DRAM bandwidth client by client with realistic efficiency "
         "(roughly 60-80 %) and headroom; reduce traffic before adding "
         "bandwidth.",
         "Budget latency stage by stage, and pins, power, area and licences "
         "per interface.",
         "A reference edge-AI SoC uses nearly every protocol in this book: "
         "LPDDR, CSI-2/DSI, CHI/AXI/APB, PCIe, USB, Ethernet, xSPI, eMMC, "
         "I2C/I3C/SPI/UART/I2S/CAN FD and JTAG/SWD.",
         "Learn by building, in order: UART, SPI, I2C, APB, AXI, Ethernet "
         "MAC, then PCIe/USB with FPGA hard blocks - each with a "
         "self-checking testbench.",
         "Protocol work spans architecture, RTL, DV, PHY, PD, DFT, firmware, "
         "validation, safety and security - the best engineers understand "
         "enough of each to work across the seams."])

    h2("Exercises")
    bul(["Redo the bandwidth budget for an 8-megapixel 60 fps camera and a "
         "4K60 display. Which LPDDR configuration do you need at 70 % "
         "efficiency and a 65 % maximum load?",
         "The NPU's weights (12 MB per frame) could be kept in on-chip SRAM "
         "if you add 12 MB of SRAM. Estimate the bandwidth saved and discuss "
         "whether the area is worth it.",
         "Choose protocols for a smart industrial sensor node: a 16-bit "
         "ADC at 1 MS/s, a temperature sensor, a 10 Mb/s-class network link "
         "to a PLC over 50 m, and a firmware update path. Justify each "
         "choice and count the pins.",
         "Build the latency budget for a lane-keeping camera that must react "
         "within 50 ms from photon to CAN FD message. Which stages would you "
         "optimize first?",
         "Plan your own learning roadmap for the next six months using the "
         "table in this chapter: pick a board, list the peripherals you will "
         "connect and the testbench you will write for each step.",
         "Answer the three 'questions that separate levels' in your own "
         "words, then write one more question of that kind for USB and one "
         "for DDR."],
        ordered=True)
