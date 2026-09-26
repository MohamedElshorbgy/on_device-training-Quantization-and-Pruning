"""Part II - On-Chip Protocols (Chapters 5-10) of the communication-protocols
guide: AMBA APB, AHB, AXI4, AXI4-Lite/Stream, cache coherency (MESI, ACE,
CHI) and other on-chip protocols (Wishbone, Avalon, TileLink, OCP, NoCs).

Every Verilog/SystemVerilog design and testbench in SRC was compiled with
Icarus Verilog 12 (iverilog -g2012 -Wall) and simulated with vvp; OUT holds the
captured output verbatim (only the trailing "$finish called" line is omitted).
The AXI burst-address results were also cross-checked against the Python
reference model shown in SRC['axiaddr_py'].
"""

from proto_guide.common import *  # noqa: F401,F403

# --- Verilog sources and REAL Icarus Verilog 12 output (generated) ---
SRC = {
    'apb': r'''
// APB4 register slave: PSTRB byte writes, PPROT secure check, programmable
// wait states on one "slow" register, PSLVERR for bad accesses.
module apb4_regs #(parameter int WS = 2) (      // wait states on SLOW register
  input  logic        pclk, presetn,
  input  logic        psel, penable, pwrite,
  input  logic [7:0]  paddr,
  input  logic [2:0]  pprot,                    // [0] priv, [1] NON-secure, [2] instr
  input  logic [31:0] pwdata,
  input  logic [3:0]  pstrb,
  output logic [31:0] prdata,
  output logic        pready, pslverr
);
  localparam logic [7:0] CTRL = 8'h00, SCRATCH = 8'h04, KEY = 8'h08,
                         ID   = 8'h0C, SLOW    = 8'h10;
  logic [31:0] ctrl, scratch, key, slow;
  logic [3:0]  wcnt;
  wire setup  = psel & ~penable;
  wire access = psel &  penable;
  wire mapped = (paddr == CTRL) || (paddr == SCRATCH) || (paddr == KEY)
              || (paddr == ID)   || (paddr == SLOW);
  wire err    = !mapped
              || (pwrite && paddr == ID)                // read-only register
              || (paddr == KEY && pprot[1]);            // non-secure access to KEY

  // wait-state counter: loaded in SETUP, counts down during ACCESS
  always_ff @(posedge pclk or negedge presetn)
    if (!presetn)                    wcnt <= '0;
    else if (setup)                  wcnt <= (paddr == SLOW) ? 4'(WS) : 4'd0;
    else if (access && wcnt != 0)    wcnt <= wcnt - 4'd1;

  assign pready  = !(access && wcnt != 0);
  assign pslverr = access && pready && err;             // valid only in last cycle

  wire wr = access && pready && pwrite && !err;         // commit exactly once
  always_ff @(posedge pclk or negedge presetn)
    if (!presetn) begin ctrl <= '0; scratch <= '0; key <= '0; slow <= '0; end
    else if (wr)
      for (int b = 0; b < 4; b++) if (pstrb[b])
        case (paddr)
          CTRL:    ctrl   [8*b +: 8] <= pwdata[8*b +: 8];
          SCRATCH: scratch[8*b +: 8] <= pwdata[8*b +: 8];
          KEY:     key    [8*b +: 8] <= pwdata[8*b +: 8];
          SLOW:    slow   [8*b +: 8] <= pwdata[8*b +: 8];
          default: ;
        endcase

  always_comb
    if (!(access && !pwrite && !err)) prdata = '0;      // drive zero when not reading
    else case (paddr)
      CTRL:    prdata = ctrl;
      SCRATCH: prdata = scratch;
      KEY:     prdata = key;
      ID:      prdata = 32'h0A9B_0004;
      SLOW:    prdata = slow;
      default: prdata = '0;
    endcase
endmodule

// APB decoder + return mux: slave 0 at 0x00xx, slave 1 at 0x10xx,
// anything else is answered by a built-in default slave with PSLVERR.
module apb_mux (
  input  logic        psel, penable,
  input  logic [15:0] paddr,
  output logic        psel0, psel1,
  input  logic [31:0] prdata0, prdata1,
  input  logic        pready0, pready1, pslverr0, pslverr1,
  output logic [31:0] prdata,
  output logic        pready, pslverr
);
  assign psel0 = psel && paddr[15:8] == 8'h00;
  assign psel1 = psel && paddr[15:8] == 8'h10;
  wire   nomap = psel && !psel0 && !psel1;
  assign prdata  = psel0 ? prdata0  : psel1 ? prdata1  : 32'h0;
  assign pready  = psel0 ? pready0  : psel1 ? pready1  : 1'b1;
  assign pslverr = psel0 ? pslverr0 : psel1 ? pslverr1 : (nomap && penable);
endmodule''',

    'apb_tb': r'''
module tb;
  logic pclk = 0, presetn = 0;
  always #5 pclk = ~pclk;
  logic psel = 0, penable = 0, pwrite = 0;
  logic [15:0] paddr = 0; logic [31:0] pwdata = 0; logic [3:0] pstrb = 0;
  logic [2:0] pprot = 0;
  logic psel0, psel1, pready0, pready1, pslverr0, pslverr1, pready, pslverr;
  logic [31:0] prdata0, prdata1, prdata;
  int cyc = 0, viol = 0;

  apb_mux mux (.*);
  apb4_regs #(.WS(2)) s0 (.pclk, .presetn, .psel(psel0), .penable, .pwrite,
    .paddr(paddr[7:0]), .pprot, .pwdata, .pstrb, .prdata(prdata0),
    .pready(pready0), .pslverr(pslverr0));
  apb4_regs #(.WS(0)) s1 (.pclk, .presetn, .psel(psel1), .penable, .pwrite,
    .paddr(paddr[7:0]), .pprot, .pwdata, .pstrb, .prdata(prdata1),
    .pready(pready1), .pslverr(pslverr1));

  // ---- master tasks: SETUP for one cycle, then ACCESS until PREADY ----
  task automatic apb_xfer(input logic wr, input logic [15:0] a, input logic [31:0] d,
                          input logic [3:0] s, input logic [2:0] pr,
                          output logic [31:0] rd, output logic err);
    psel <= 1; penable <= 0; pwrite <= wr; paddr <= a; pprot <= pr;
    pwdata <= wr ? d : 32'h0; pstrb <= wr ? s : 4'h0;   // PSTRB=0 on reads
    @(posedge pclk); penable <= 1;
    do @(posedge pclk); while (!pready);
    rd = prdata; err = pslverr;
    psel <= 0; penable <= 0;
  endtask

  // ---- cycle trace + simple protocol checker ----
  logic [15:0] a_q; logic w_q; logic [31:0] d_q; logic stall_q = 0;
  always @(posedge pclk) begin
    cyc++;
    if (psel)
      $display("%3d  %-6s %04h %s %08h %b %b  %1b   %1b   %08h", cyc,
        penable ? (pready ? "ACCESS" : "ACC/w") : "SETUP", paddr, pwrite ? "W" : "R",
        pwdata, pstrb, pprot, pready, pslverr, prdata);
    if (stall_q && (paddr != a_q || pwrite != w_q || pwdata != d_q || !psel)) viol++;
    stall_q <= psel && penable && !pready;
    a_q <= paddr; w_q <= pwrite; d_q <= pwdata;
  end

  logic [31:0] rd; logic err;
  initial begin
    repeat (2) @(posedge pclk); presetn <= 1; @(posedge pclk);
    $display("cyc  phase  ADDR D PWDATA   STRB PROT RDY ERR PRDATA");
    apb_xfer(1, 16'h0004, 32'h1122_3344, 4'b1111, 3'b000, rd, err); // scratch
    apb_xfer(1, 16'h0004, 32'hAAAA_BBCC, 4'b0001, 3'b000, rd, err); // byte 0 only
    apb_xfer(0, 16'h0004, 0, 0, 3'b000, rd, err);
    apb_xfer(1, 16'h0010, 32'hCAFE_F00D, 4'b1111, 3'b000, rd, err); // 2 wait states
    apb_xfer(0, 16'h0010, 0, 0, 3'b000, rd, err);
    apb_xfer(1, 16'h0008, 32'h5EC0_0001, 4'b1111, 3'b010, rd, err); // non-secure->KEY
    apb_xfer(1, 16'h000C, 32'h0, 4'b1111, 3'b000, rd, err);         // write RO ID
    apb_xfer(0, 16'h100C, 0, 0, 3'b000, rd, err);                   // slave 1 ID
    apb_xfer(0, 16'h2000, 0, 0, 3'b000, rd, err);                   // unmapped
    @(posedge pclk);
    $display("protocol violations = %0d", viol);
    $finish;
  end
endmodule''',

    'ahb': r'''
// AHB-Lite SRAM slave (behavioural array): wait states, byte/halfword writes,
// and the two-cycle ERROR response for out-of-range addresses.
module ahb_sram #(parameter int BYTES = 1024) (
  input  logic        hclk, hresetn,
  input  logic        hsel, hready, hwrite,
  input  logic [31:0] haddr,
  input  logic [1:0]  htrans,                 // 00 IDLE 01 BUSY 10 NONSEQ 11 SEQ
  input  logic [2:0]  hsize, hburst,
  input  logic [3:0]  hprot,
  input  logic [31:0] hwdata,
  input  logic [1:0]  ws,                     // wait states for this transfer (demo knob)
  output logic [31:0] hrdata,
  output logic        hreadyout, hresp
);
  logic [31:0] mem [BYTES/4];
  // ---- address-phase register: captured only when HREADY is high ----
  logic        dp_valid, dp_write;
  logic [31:0] dp_addr;
  logic [2:0]  dp_size;
  logic [1:0]  cnt;                           // remaining wait states
  logic [1:0]  eph;                           // 0 none, 1 first ERROR cycle, 2 second

  wire xfer = hsel && htrans[1];              // NONSEQ or SEQ (IDLE/BUSY: no transfer)
  always_ff @(posedge hclk or negedge hresetn)
    if (!hresetn) begin dp_valid <= 0; cnt <= 0; eph <= 0; end
    else if (hready) begin                    // previous data phase done: sample address
      dp_valid <= xfer;  dp_write <= hwrite;  dp_addr <= haddr;  dp_size <= hsize;
      eph      <= (xfer && haddr >= BYTES) ? 2'd1 : 2'd0;
      cnt      <= (xfer && haddr <  BYTES) ? ws : 2'd0;
    end else if (eph == 1) eph <= 2;          // ERROR cycle 1 -> cycle 2
    else if (cnt != 0)     cnt <= cnt - 1;

  assign hreadyout = !dp_valid || (eph == 1 ? 1'b0 : eph == 2 ? 1'b1 : cnt == 0);
  assign hresp     =  dp_valid && eph != 0;   // 1 = ERROR, held for both cycles

  // byte-lane enables from HSIZE and the low address bits (little-endian)
  logic [3:0] be;
  wire  [1:0] lo = dp_addr[1:0];
  always_comb case (dp_size)
    3'd0:    be = 4'b0001 << lo;
    3'd1:    be = (lo >= 2) ? 4'b1100 : 4'b0011;
    default: be = 4'b1111;
  endcase

  wire [7:0] widx = dp_addr[$clog2(BYTES)-1:2];
  always_ff @(posedge hclk)                   // write in the last data-phase cycle
    if (dp_valid && dp_write && eph == 0 && hreadyout)
      for (int b = 0; b < 4; b++) if (be[b]) mem[widx][8*b +: 8] <= hwdata[8*b +: 8];

  assign hrdata = (dp_valid && !dp_write && eph == 0) ? mem[widx] : 32'h0;
endmodule''',

    'ahb_tb': r'''
module tb;
  logic hclk = 0, hresetn = 0;
  always #5 hclk = ~hclk;
  logic hsel = 1, hwrite = 0; logic [31:0] haddr = 0, hwdata = 0;
  logic [1:0] htrans = 0, ws = 0; logic [2:0] hsize = 2, hburst = 0;
  logic [3:0] hprot = 4'b0011;
  logic [31:0] hrdata; logic hreadyout, hresp, hready;
  assign hready = hreadyout;                  // single slave: HREADY = HREADYOUT
  ahb_sram dut (.*);

  // transfer list (parallel arrays): htrans, hburst, hsize, hwrite, ws, haddr, wdata
  logic [1:0] qt [32], qws [32]; logic [2:0] qb [32], qs [32]; logic qw [32];
  logic [31:0] qa [32], qd [32];
  localparam IDLE = 2'b00, BUSY = 2'b01, NSEQ = 2'b10, SEQ = 2'b11;
  localparam SINGLE = 3'b000, INCR4 = 3'b011;
  int nq = 0, ai = 0, cyc = 0, n_err = 0;
  logic go = 0;
  logic dp_rd = 0; logic [31:0] dp_a;         // TB copy of the data phase

  // pipelined driver: when HREADY is high the address phase on the bus is
  // accepted, its write data moves to HWDATA and the next address is driven
  always @(posedge hclk) if (go && hready && ai < nq) begin
    hwdata <= qw[ai] ? qd[ai] : 32'h0;
    dp_rd  <= (qt[ai] >= NSEQ) && !qw[ai];  dp_a <= qa[ai];
    ai = ai + 1;
    if (ai < nq) begin
      htrans <= qt[ai]; hburst <= qb[ai]; hsize <= qs[ai];
      hwrite <= qw[ai]; ws <= qws[ai];    haddr <= qa[ai];
    end else begin htrans <= IDLE; hwrite <= 0; end
  end

  function string tn(input logic [1:0] t);
    return t == 0 ? "IDLE  " : t == 1 ? "BUSY  " : t == 2 ? "NONSEQ" : "SEQ   ";
  endfunction
  always @(posedge hclk) if (go) begin
    cyc++;
    $write("%3d %s %03h %s %s %0d | %08h %1b %s", cyc, tn(htrans), haddr[11:0],
      hwrite ? "W" : "R", hburst == INCR4 ? "INCR4 " : "SINGLE", hsize, hwdata,
      hreadyout, hresp ? "ERR " : "OKAY");
    if (hready && dp_rd && !hresp) $display(" HRDATA=%08h", hrdata); else $display("");
    if (hresp) n_err++;
  end

  task automatic add(input logic [1:0] t, input logic [2:0] b, s, input logic w,
                     input logic [1:0] w_s, input logic [31:0] a, d);
    qt[nq] = t; qb[nq] = b; qs[nq] = s; qw[nq] = w; qws[nq] = w_s; qa[nq] = a; qd[nq] = d;
    nq++;
  endtask

  initial begin
    add(IDLE, SINGLE, 2, 0, 0, 32'h0,  32'h0);
    add(NSEQ, SINGLE, 2, 1, 0, 32'h00, 32'hDEADBEEF);
    add(NSEQ, INCR4,  2, 1, 0, 32'h10, 32'hA0A0A0A0);
    add(SEQ,  INCR4,  2, 1, 0, 32'h14, 32'hA1A1A1A1);
    add(SEQ,  INCR4,  2, 1, 0, 32'h18, 32'hA2A2A2A2);
    add(SEQ,  INCR4,  2, 1, 0, 32'h1C, 32'hA3A3A3A3);
    add(NSEQ, INCR4,  2, 0, 1, 32'h10, 32'h0);   // read burst, 1 wait/beat
    add(SEQ,  INCR4,  2, 0, 1, 32'h14, 32'h0);
    add(BUSY, INCR4,  2, 0, 1, 32'h18, 32'h0);   // master inserts BUSY
    add(SEQ,  INCR4,  2, 0, 1, 32'h18, 32'h0);
    add(SEQ,  INCR4,  2, 0, 1, 32'h1C, 32'h0);
    add(NSEQ, SINGLE, 0, 1, 0, 32'h01, 32'h00005500); // byte write, lane 1
    add(NSEQ, SINGLE, 2, 0, 0, 32'h00, 32'h0);
    add(NSEQ, SINGLE, 2, 0, 0, 32'h800, 32'h0);      // out of range
    add(IDLE, SINGLE, 2, 0, 0, 32'h0,  32'h0);
    repeat (2) @(posedge hclk); hresetn <= 1;
    $display("cyc HTRANS ADR D HBURST SZ | HWDATA   RDY RESP");
    @(posedge hclk); go <= 1;
    wait (ai >= nq); repeat (2) @(posedge hclk);
    $display("error-response cycles seen = %0d", n_err);
    $finish;
  end
endmodule''',

    'axiaddr': r'''
// AXI4 beat-address and byte-lane generator (combinational).
// For beat n (0-based) of a burst: address, active byte lanes, 4KB-crossing flag.
module axi_addr_gen #(parameter int DB = 8) (         // data bus width in bytes
  input  logic [31:0]   start,                        // AxADDR
  input  logic [7:0]    len,                          // AxLEN  (beats - 1)
  input  logic [2:0]    size,                         // AxSIZE (bytes = 2**size <= DB)
  input  logic [1:0]    burst,                        // 0 FIXED, 1 INCR, 2 WRAP
  input  logic [7:0]    n,                            // beat index
  output logic [31:0]   addr,
  output logic [DB-1:0] lanes,                        // byte lanes that carry data
  output logic          cross4k                       // INCR burst crosses 4KB: illegal
);
  logic [31:0] nbytes, aligned, total, wbound, linear, last, lo, hi;
  always_comb begin
    nbytes  = 32'd1 << size;
    aligned = start & ~(nbytes - 1);                  // start rounded down to size
    total   = nbytes * (len + 1);                     // bytes in burst (wrap container)
    wbound  = start & ~(total - 1);                   // wrap boundary (WRAP only)
    linear  = aligned + n * nbytes;
    case (burst)
      2'd0:    addr = start;                                    // FIXED
      2'd2:    addr = wbound | (linear & (total - 1));          // WRAP
      default: addr = (n == 0) ? start : linear;                // INCR
    endcase
    lo = addr % DB;                                   // first valid lane
    hi = (addr & ~(nbytes - 1)) % DB + nbytes - 1;    // end of size-aligned container
    for (int b = 0; b < DB; b++) lanes[b] = (b >= lo) && (b <= hi);
    last    = aligned + len * nbytes;
    cross4k = (burst == 2'd1) && ((start >> 12) != (last >> 12));
  end
endmodule''',

    'axiaddr_tb': r'''
module tb;
  logic [31:0] start, addr; logic [7:0] len, n; logic [2:0] size; logic [1:0] burst;
  logic [7:0] lanes; logic cross4k;
  axi_addr_gen #(.DB(8)) dut (.*);                   // 64-bit data bus
  int fd, lines = 0; bit ok;
  int starts [8], lens [6];
  initial begin
    starts[0] = 'h0;  starts[1] = 'h3;  starts[2] = 'h6;   starts[3] = 'h14;
    starts[4] = 'h38; starts[5] = 'h3E; starts[6] = 'hFF9; starts[7] = 'h1234;
    lens[0] = 0; lens[1] = 1; lens[2] = 3; lens[3] = 7; lens[4] = 15; lens[5] = 255;
    fd = $fopen("axi_addr_rtl.txt", "w");
    for (int bu = 0; bu < 3; bu++)
      for (int sz = 0; sz < 4; sz++)
        for (int li = 0; li < 6; li++)
          for (int si = 0; si < 8; si++) begin
            burst = bu; size = sz; len = lens[li]; start = starts[si];
            ok = 1;
            if (bu == 2) begin                         // WRAP: len 2/4/8/16, aligned start
              ok = (len == 1 || len == 3 || len == 7 || len == 15);
              start = start & ~((1 << sz) - 1);
            end
            if (bu == 0 && len > 15) ok = 0;           // FIXED: at most 16 beats
            if (ok) for (int k = 0; k <= len; k++) begin
              n = k; #1;
              $fdisplay(fd, "%0d %0d %0d %0h %0d %0h %02h %0d",
                        bu, sz, len, start, k, addr, lanes, cross4k);
              lines++;
            end
          end
    $fclose(fd);
    $display("RTL beats written: %0d", lines);
    // two worked examples for the text
    burst = 2; size = 2; len = 3; start = 32'h38;
    $write("WRAP4  x 4B @0x38 :");
    for (int k = 0; k < 4; k++) begin n = k; #1 $write(" %02h/%08b", addr[7:0], lanes); end
    $display("");
    burst = 1; size = 2; len = 3; start = 32'h3E;
    $write("INCR4  x 4B @0x3E :");
    for (int k = 0; k < 4; k++) begin n = k; #1 $write(" %02h/%08b", addr[7:0], lanes); end
    $display("");
    burst = 1; size = 3; len = 15; start = 32'hFF8; n = 0; #1;
    $display("INCR16 x 8B @0xFF8: crosses 4KB = %0d", cross4k);
  end
endmodule''',

    'axiaddr_py': r'''
# Python reference written directly from the AXI spec pseudo-code
# (Start_Address, Aligned_Address, Wrap_Boundary, Lower/Upper_Byte_Lane).
DB = 8
def beats(burst, size, length, start):
    nb, bl = 1 << size, length + 1
    aligned = (start // nb) * nb
    wrap_b  = (start // (nb * bl)) * (nb * bl)
    wrapped = False
    for n in range(1, bl + 1):                      # spec numbers beats from 1
        if n == 1:
            a = start
            lower = start - (start // DB) * DB
            upper = aligned + (nb - 1) - (start // DB) * DB
        else:
            if burst == 0: a = start
            else:
                a = aligned + (n - 1) * nb
                if burst == 2:
                    if wrapped or a >= wrap_b + nb * bl:
                        wrapped = True; a = start + (n - 1) * nb - nb * bl
            if burst == 0:
                lower = start - (start // DB) * DB
                upper = aligned + (nb - 1) - (start // DB) * DB
            else:
                lower = a - (a // DB) * DB
                upper = lower + nb - 1
        lanes = sum(1 << b for b in range(lower, upper + 1))
        last = aligned + length * nb
        cross = int(burst == 1 and (start >> 12) != (last >> 12))
        yield n - 1, a, lanes, cross

bad = total = 0
for line in open("axi_addr_rtl.txt"):
    bu, sz, ln, st, k, a, lanes, cr = line.split()
    bu, sz, ln, k, cr = int(bu), int(sz), int(ln), int(k), int(cr)
    st, a, lanes = int(st, 16), int(a, 16), int(lanes, 16)
    exp = list(beats(bu, sz, ln, st))[k]
    total += 1
    if exp != (k, a, lanes, cr):
        bad += 1
        if bad < 5: print("MISMATCH", line.strip(), exp)
print("python model compared %d beats, mismatches = %d" % (total, bad))''',

    'aximem': r'''
// AXI4 memory slave, 32-bit data, 4KB. One write and one read burst in flight
// (independent channels); FIXED/INCR/WRAP via axi_addr_gen; IDs echoed on B/R.
module axi4_mem #(parameter int IDW = 4) (
  input  logic           aclk, aresetn,
  // write address
  input  logic [IDW-1:0] awid,   input  logic [11:0] awaddr, input logic [7:0] awlen,
  input  logic [2:0]     awsize, input  logic [1:0]  awburst,
  input  logic           awvalid, output logic awready,
  // write data
  input  logic [31:0]    wdata,  input  logic [3:0]  wstrb,  input logic wlast,
  input  logic           wvalid, output logic wready,
  // write response
  output logic [IDW-1:0] bid,    output logic [1:0]  bresp,
  output logic           bvalid, input  logic bready,
  // read address
  input  logic [IDW-1:0] arid,   input  logic [11:0] araddr, input logic [7:0] arlen,
  input  logic [2:0]     arsize, input  logic [1:0]  arburst,
  input  logic           arvalid, output logic arready,
  // read data
  output logic [IDW-1:0] rid,    output logic [31:0] rdata,  output logic [1:0] rresp,
  output logic           rlast,  output logic rvalid, input logic rready
);
  logic [31:0] mem [1024];

  // ------------------------- write channel FSM ---------------------------
  typedef enum logic [1:0] {W_ADDR, W_DATA, W_RESP} wst_t;
  wst_t ws;
  logic [IDW-1:0] w_id;  logic [31:0] w_start, w_addr;  logic [7:0] w_len, w_n;
  logic [2:0] w_size;    logic [1:0] w_burst;  logic w_err;  logic [3:0] w_lanes;
  logic w_x4k;
  axi_addr_gen #(.DB(4)) wag (.start(w_start), .len(w_len), .size(w_size),
    .burst(w_burst), .n(w_n), .addr(w_addr), .lanes(w_lanes), .cross4k(w_x4k));

  assign awready = (ws == W_ADDR);
  assign wready  = (ws == W_DATA);
  assign bvalid  = (ws == W_RESP);
  assign bid     = w_id;
  assign bresp   = w_err ? 2'b10 : 2'b00;               // SLVERR : OKAY

  always_ff @(posedge aclk or negedge aresetn)
    if (!aresetn) ws <= W_ADDR;
    else case (ws)
      W_ADDR: if (awvalid) begin                        // AW handshake
        w_id <= awid; w_start <= {20'h0, awaddr}; w_len <= awlen;
        w_size <= awsize; w_burst <= awburst; w_n <= 0; w_err <= 0; ws <= W_DATA;
      end
      W_DATA: if (wvalid) begin                         // W handshake: one beat
        for (int b = 0; b < 4; b++)                     // strobe AND legal lanes
          if (wstrb[b] && w_lanes[b]) mem[w_addr[11:2]][8*b +: 8] <= wdata[8*b +: 8];
        if (wlast != (w_n == w_len)) w_err <= 1;         // WLAST protocol check
        w_n <= w_n + 1;
        if (w_n == w_len) ws <= W_RESP;
      end
      W_RESP: if (bready) ws <= W_ADDR;                 // B handshake
      default: ws <= W_ADDR;
    endcase

  // ------------------------- read channel FSM ----------------------------
  logic r_busy;  logic [IDW-1:0] r_id;  logic [31:0] r_start, r_addr;
  logic [7:0] r_len, r_n;  logic [2:0] r_size;  logic [1:0] r_burst;
  logic [3:0] r_lanes;  logic r_x4k;
  axi_addr_gen #(.DB(4)) rag (.start(r_start), .len(r_len), .size(r_size),
    .burst(r_burst), .n(r_n), .addr(r_addr), .lanes(r_lanes), .cross4k(r_x4k));

  assign arready = !r_busy;
  assign rvalid  =  r_busy;
  assign rid     =  r_id;
  assign rdata   =  mem[r_addr[11:2]];                  // whole word; master picks lanes
  assign rresp   =  2'b00;
  assign rlast   =  r_busy && (r_n == r_len);

  always_ff @(posedge aclk or negedge aresetn)
    if (!aresetn) r_busy <= 0;
    else if (!r_busy) begin
      if (arvalid) begin                                // AR handshake
        r_busy <= 1; r_id <= arid; r_start <= {20'h0, araddr}; r_len <= arlen;
        r_size <= arsize; r_burst <= arburst; r_n <= 0;
      end
    end else if (rready) begin                          // R handshake
      r_n <= r_n + 1;
      if (rlast) r_busy <= 0;
    end
endmodule''',

    'aximem_tb': r'''
module tb;
  logic aclk = 0, aresetn = 0;
  always #5 aclk = ~aclk;
  logic [3:0] awid = 0, arid = 0, bid, rid;  logic [11:0] awaddr = 0, araddr = 0;
  logic [7:0] awlen = 0, arlen = 0;  logic [2:0] awsize = 0, arsize = 0;
  logic [1:0] awburst = 0, arburst = 0, bresp, rresp;
  logic awvalid = 0, awready, wvalid = 0, wready, wlast = 0, bvalid, bready = 0;
  logic arvalid = 0, arready, rvalid, rready = 0, rlast;
  logic [31:0] wdata = 0, rdata;  logic [3:0] wstrb = 0;
  axi4_mem dut (.*);

  byte unsigned shadow [4096];                          // reference memory
  int beats_chk = 0, errs = 0;
  logic verbose = 1;

  // TB's own beat-address model (independent of the DUT's generator)
  function automatic int beat_addr(int st, int len, int sz, int bu, int n);
    int nb = 1 << sz, tot = nb * (len + 1), al = st / nb * nb, wb = st / tot * tot;
    if (bu == 0) return st;
    if (bu == 1) return n == 0 ? st : al + n * nb;
    return wb + (st - wb + n * nb) % tot;
  endfunction

  string bn [3];
  initial begin bn[0] = "FIXED"; bn[1] = "INCR"; bn[2] = "WRAP"; end

  task automatic axi_write(int id, int a, int len, int sz, int bu, int seed,
                           int bad_last = -1);
    int x = 0;
    fork
      begin                                             // AW channel
        @(posedge aclk); awvalid <= 1; awid <= id; awaddr <= a; awlen <= len;
        awsize <= sz; awburst <= bu;
        do @(posedge aclk); while (!awready);
        awvalid <= 0;
      end
      for (int n = 0; n <= len; n++) begin              // W channel (random gaps)
        int ba = beat_addr(a, len, sz, bu, n), nb = 1 << sz;
        logic [31:0] d = (seed + n + 1) * 32'h9E37_79B1;
        logic [3:0] s = 0;
        for (int b = ba % 4; b < (ba / nb * nb) % 4 + nb; b++) s[b] = 1;
        while ($urandom % 3 == 0) @(posedge aclk);
        wvalid <= 1; wdata <= d; wstrb <= s;
        wlast <= (bad_last >= 0) ? (n == bad_last) : (n == len);
        do @(posedge aclk); while (!wready);
        wvalid <= 0; wlast <= 0;
        for (int b = 0; b < 4; b++) if (s[b]) shadow[(ba & ~3) + b] = d[8*b +: 8];
      end
    join
    bready <= 1; do @(posedge aclk); while (!bvalid); bready <= 0;
    if (verbose) $display("WRITE id=%0d %-5s %2d x %0dB @%03h -> BID=%0d BRESP=%0s", id,
      bn[bu], len + 1, 1 << sz, 12'(a), bid, (bresp == 0) ? "OKAY" : "SLVERR");
  endtask

  task automatic axi_read(int id, int a, int len, int sz, int bu);
    @(posedge aclk); arvalid <= 1; arid <= id; araddr <= a; arlen <= len;
    arsize <= sz; arburst <= bu;
    do @(posedge aclk); while (!arready);
    arvalid <= 0;
    if (verbose) $write("READ  id=%0d %-5s %2d x %0dB @%03h ->", id, bn[bu],
                        len + 1, 1 << sz, 12'(a));
    for (int n = 0; n <= len; n++) begin
      int ba = beat_addr(a, len, sz, bu, n), nb = 1 << sz;
      rready <= ($urandom % 4 != 0);                    // random backpressure
      do begin @(posedge aclk); if (!rready) rready <= 1; end
      while (!(rvalid && rready));
      for (int b = ba % 4; b < (ba / nb * nb) % 4 + nb; b++)
        if (rdata[8*b +: 8] !== shadow[(ba & ~3) + b]) errs++;
      if (rid !== 4'(id) || rlast !== (n == len)) errs++;
      beats_chk++;
      if (verbose) $write(" %03h:%08h", 12'(ba), rdata);
    end
    rready <= 0;
    if (verbose) $display(" RID=%0d", rid);
  endtask

  int bu, sz, len, a;
  initial begin
    for (int i = 0; i < 1024; i++) dut.mem[i] = 0;      // SRAM model starts zeroed
    repeat (3) @(posedge aclk); aresetn <= 1;
    axi_write(1, 'h100, 3, 2, 1, 10);                   // INCR4, 4-byte beats
    axi_read (2, 'h108, 3, 2, 2);                       // WRAP4 starting mid-block
    axi_write(3, 'h202, 3, 1, 1, 20);                   // narrow: 2-byte beats
    axi_read (4, 'h200, 1, 2, 1);
    axi_write(5, 'h3F2, 2, 2, 1, 30);                   // unaligned start
    axi_read (6, 'h3F0, 3, 2, 1);
    axi_write(7, 'h300, 3, 2, 0, 40);                   // FIXED: same address 4 times
    axi_read (8, 'h300, 0, 2, 1);
    axi_write(9, 'h400, 3, 2, 1, 50, 1);                // WLAST on wrong beat
    verbose = 0;
    for (int i = 0; i < 300; i++) begin                 // random regression
      bu = $urandom % 3; sz = $urandom % 3;
      len = (bu == 2) ? (2 << ($urandom % 4)) - 1 : $urandom % 16;
      a = ($urandom % 3584) & ~((bu == 2) ? (1 << sz) - 1 : 0);
      if ($urandom % 2) axi_write(i % 16, a, len, sz, bu, i * 7);
      else              axi_read (i % 16, a, len, sz, bu);
    end
    $display("read beats checked = %0d, mismatches = %0d", beats_chk, errs);
    $finish;
  end
endmodule''',

    'axis': r'''
// AXI4-Stream 32 -> 8 bit width converter. Null bytes (TKEEP=0) are dropped,
// TLAST moves to the last kept byte of the packet.
module axis_32to8 (
  input  logic        aclk, aresetn,
  input  logic        s_tvalid, input logic [31:0] s_tdata, input logic [3:0] s_tkeep,
  input  logic        s_tlast,  output logic s_tready,
  output logic        m_tvalid, output logic [7:0] m_tdata, output logic m_tlast,
  input  logic        m_tready
);
  logic [31:0] d;  logic [3:0] k;  logic l;          // holding register
  wire  [3:0] k_nxt    = k & (k - 4'd1);             // clear lowest set keep bit
  wire        lastbyte = (k_nxt == 4'd0);
  wire        take     = m_tvalid && m_tready;

  assign m_tvalid = |k;
  assign m_tdata  = k[0] ? d[7:0] : k[1] ? d[15:8] : k[2] ? d[23:16] : d[31:24];
  assign m_tlast  = l && lastbyte;
  // accept a new word when empty, or when the last byte leaves this cycle
  assign s_tready = !m_tvalid || (take && lastbyte);

  always_ff @(posedge aclk or negedge aresetn)
    if (!aresetn)                   k <= '0;
    else if (s_tvalid && s_tready) begin d <= s_tdata; k <= s_tkeep; l <= s_tlast; end
    else if (take)                  k <= k_nxt;
endmodule''',

    'axis_tb': r'''
module tb;
  logic aclk = 0, aresetn = 0;
  always #5 aclk = ~aclk;
  logic s_tvalid = 0, s_tlast = 0, s_tready, m_tvalid, m_tlast, m_tready = 0;
  logic [31:0] s_tdata = 0; logic [3:0] s_tkeep = 0; logic [7:0] m_tdata;
  axis_32to8 dut (.*);

  byte unsigned exp_q [$];  bit exp_last [$];        // scoreboard
  int npk = 0, nbytes = 0, errs = 0, viol = 0, cyc = 0, trace = 1;

  // ---- source: random packets, random TVALID gaps, occasional null bytes ----
  task automatic send_packet(int len);
    int i = 0;
    while (i < len) begin
      logic [31:0] w = 0; logic [3:0] k = 0; logic last = 0;
      for (int b = 0; b < 4 && i < len; b++)
        if (($urandom % 8 != 0) || b == 3) begin    // ~1/8 of lanes left null
          w[8*b +: 8] = 8'($urandom); k[b] = 1;
          exp_q.push_back(w[8*b +: 8]); exp_last.push_back(i == len - 1); i++;
        end
      last = (i == len);
      while ($urandom % 4 == 0) @(posedge aclk);
      s_tvalid <= 1; s_tdata <= w; s_tkeep <= k; s_tlast <= last;
      do @(posedge aclk); while (!s_tready);
      s_tvalid <= 0;
    end
  endtask

  task automatic send_word(logic [31:0] w, logic [3:0] k, logic last);   // directed
    int top = 0;
    for (int b = 0; b < 4; b++) if (k[b]) top = b;
    for (int b = 0; b < 4; b++) if (k[b]) begin
      exp_q.push_back(w[8*b +: 8]); exp_last.push_back(last && b == top);
    end
    s_tvalid <= 1; s_tdata <= w; s_tkeep <= k; s_tlast <= last;
    do @(posedge aclk); while (!s_tready);
    s_tvalid <= 0;
  endtask

  // ---- sink: random TREADY, scoreboard, AXIS stability rule checker ----
  logic pend = 0; logic [8:0] held;
  always @(posedge aclk) begin
    cyc++;
    if (trace && (s_tvalid || m_tvalid))
      $display("%3d  S: v=%b r=%b keep=%b data=%08h last=%b | M: v=%b r=%b data=%02h last=%b",
        cyc, s_tvalid, s_tready, s_tkeep, s_tdata, s_tlast, m_tvalid, m_tready,
        m_tdata, m_tlast);
    if (pend && (!m_tvalid || {m_tlast, m_tdata} != held)) viol++;  // no change while stalled
    pend <= m_tvalid && !m_tready;  held <= {m_tlast, m_tdata};
    if (m_tvalid && m_tready) begin
      if (m_tdata != exp_q[0] || m_tlast != exp_last[0]) errs++;
      void'(exp_q.pop_front()); void'(exp_last.pop_front());
      nbytes++; if (m_tlast) npk++;
    end
    m_tready <= ($urandom % 3 != 0);
  end

  initial begin
    repeat (2) @(posedge aclk); aresetn <= 1;
    send_word(32'h44332211, 4'b1111, 0);              // traced example: 7 bytes,
    send_word(32'h88776655, 4'b1101, 0);              // byte 0x66 is a null byte
    send_word(32'h0000AA99, 4'b0011, 1);
    repeat (6) @(posedge aclk); trace = 0;
    for (int p = 0; p < 500; p++) send_packet(1 + $urandom % 40);
    repeat (50) @(posedge aclk);
    $display("packets=%0d bytes=%0d data/TLAST errors=%0d stability violations=%0d left=%0d",
             npk, nbytes, errs, viol, exp_q.size());
    $finish;
  end
endmodule''',

    'mesi': r'''
// One cache line shared by N snooping caches on an atomic bus (one bus
// transaction per cycle). MESI protocol with write-back memory.
// BUG=1 injects a classic error: snoopers ignore BusUpgr (no invalidation).
module mesi_sys #(parameter int N = 3, parameter bit BUG = 0) (
  input  logic        clk, rst_n,
  input  logic        req,                  // one processor request per cycle
  input  logic [1:0]  cpu,                  // which processor
  input  logic [1:0]  op,                   // 0 read, 1 write, 2 evict
  input  logic [15:0] wval,                 // value to write
  output logic [15:0] rval,                 // value returned to a read
  output logic [2:0]  bus,                  // bus transaction issued this cycle
  output logic [N-1:0][1:0]  st,                // line state in each cache
  output logic [N-1:0][15:0] val,               // line data in each cache
  output logic [15:0] mem                   // memory copy
);
  localparam logic [1:0] I = 0, S = 1, E = 2, M = 3;
  localparam logic [2:0] NONE = 0, BUSRD = 1, BUSRDX = 2, BUSUPGR = 3, WB = 4;

  // --- snoop results (wired-OR "shared" and "dirty" lines of a snooping bus) ---
  logic shared, dirty;  logic [15:0] owner_val;
  always_comb begin
    shared = 0; dirty = 0; owner_val = mem;
    for (int j = 0; j < N; j++) if (j != cpu && st[j] != I) begin
      shared = 1;
      if (st[j] == M) begin dirty = 1; owner_val = val[j]; end
    end
  end

  // --- requester side: which bus transaction does this request need? ---
  always_comb begin
    bus = NONE;
    if (req) case (op)
      0: if (st[cpu] == I) bus = BUSRD;                         // read miss
      1: if (st[cpu] == I) bus = BUSRDX;                        // write miss
         else if (st[cpu] == S) bus = BUSUPGR;                  // write hit on S
      2: if (st[cpu] == M) bus = WB;                            // dirty eviction
      default: ;
    endcase
    rval = (st[cpu] != I) ? val[cpu] : owner_val;
  end

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      mem <= 0;
      for (int j = 0; j < N; j++) begin st[j] <= I; val[j] <= 0; end
    end else if (req) begin
      // snooping caches react to the bus transaction
      for (int j = 0; j < N; j++) if (j != cpu)
        case (bus)
          BUSRD:   if (st[j] == M || st[j] == E) st[j] <= S;   // M also flushes
          BUSRDX:  st[j] <= I;
          BUSUPGR: if (!BUG) st[j] <= I;
          default: ;
        endcase
      if (dirty && (bus == BUSRD || bus == BUSRDX)) mem <= owner_val;   // flush
      // requesting cache
      case (op)
        0: if (st[cpu] == I) begin st[cpu] <= shared ? S : E; val[cpu] <= owner_val; end
        1: begin st[cpu] <= M; val[cpu] <= wval; end           // E->M is silent
        2: begin if (st[cpu] == M) mem <= val[cpu]; st[cpu] <= I; end
        default: ;
      endcase
    end
endmodule''',

    'mesi_tb': r'''
module tb;
  localparam int N = 3;
  logic clk = 0, rst_n = 0;  always #5 clk = ~clk;
  logic req = 0; logic [1:0] cpu = 0, op = 0; logic [15:0] wval = 0, rval, mem;
  logic [2:0] bus;
  logic [N-1:0][1:0] st0, st1;  logic [N-1:0][15:0] v0, v1;
  logic [15:0] rv0, rv1, m0, m1;  logic [2:0] b0, b1;
  mesi_sys #(.N(N), .BUG(0)) good (.clk, .rst_n, .req, .cpu, .op, .wval,
     .rval(rv0), .bus(b0), .st(st0), .val(v0), .mem(m0));
  mesi_sys #(.N(N), .BUG(1)) bad  (.clk, .rst_n, .req, .cpu, .op, .wval,
     .rval(rv1), .bus(b1), .st(st1), .val(v1), .mem(m1));

  function automatic string sn(logic [1:0] s); return s == 0 ? "I" : s == 1 ? "S" :
                                                     s == 2 ? "E" : "M"; endfunction
  function automatic string bn(logic [2:0] b); return b == 0 ? "-      " :
      b == 1 ? "BusRd  " : b == 2 ? "BusRdX " : b == 3 ? "BusUpgr" : "WrBack "; endfunction

  // invariant: at most one M/E copy, and an M/E copy excludes all other copies
  function automatic bit swmr_ok(logic [N-1:0][1:0] s);
    int own = 0, valid = 0;
    for (int j = 0; j < N; j++) begin own += (s[j] >= 2); valid += (s[j] != 0); end
    return own == 0 || (own == 1 && valid == 1);
  endfunction

  logic [15:0] golden = 0;              // last value written by anyone
  int inv_err [2], stale [2], reads = 0;
  task automatic do_op(int c, int o, int show);
    string on = o == 0 ? "RD" : o == 1 ? "WR" : "EV";
    cpu <= c; op <= o; wval <= golden + 1; req <= 1;
    @(negedge clk);                                   // combinational results
    if (o == 0) begin
      reads++;  if (rv0 != golden) stale[0]++;  if (rv1 != golden) stale[1]++;
    end
    if (show) $write("P%0d %s  bus=%s rd=%4h |", c, on, bn(b0), o == 0 ? rv0 : 16'h0);
    @(posedge clk); #1;
    if (o == 1) golden = golden + 1;
    if (!swmr_ok(st0)) inv_err[0]++;
    if (!swmr_ok(st1)) inv_err[1]++;
    if (show) $display(" good: %s %s %s mem=%4h | BUG: %s %s %s", sn(st0[0]), sn(st0[1]),
                       sn(st0[2]), m0, sn(st1[0]), sn(st1[1]), sn(st1[2]));
    req <= 0;
  endtask

  initial begin
    inv_err[0] = 0; inv_err[1] = 0; stale[0] = 0; stale[1] = 0;
    repeat (2) @(posedge clk); rst_n <= 1; @(posedge clk); #1;
    do_op(0, 0, 1);  do_op(0, 1, 1);  do_op(1, 0, 1);  do_op(2, 0, 1);
    do_op(1, 1, 1);  do_op(0, 0, 1);  do_op(2, 2, 1);  do_op(0, 1, 1);
    do_op(2, 1, 1);  do_op(1, 0, 1);  do_op(2, 2, 1);  do_op(1, 1, 1);
    for (int i = 0; i < 20000; i++) do_op($urandom % N, $urandom % 3, 0);
    $display("reads=%0d | good: stale=%0d SWMR violations=%0d | BUG=1: stale=%0d viol=%0d",
             reads, stale[0], inv_err[0], stale[1], inv_err[1]);
    $finish;
  end
endmodule''',

    'noc': r'''
// 5-port wormhole router with XY routing, 2-flit input buffers, valid/ready
// links (equivalent to 2 credits) and round-robin output allocation.
// Flit: [23] head [22] tail [21:20] dst x [19:18] dst y [17:0] tag + payload
module xy_router #(parameter int X = 0, parameter int Y = 0) (
  input  logic         clk, rst_n,
  input  logic [4:0]   in_valid,  output logic [4:0] in_ready,
  input  logic [119:0] in_data,                            // 5 ports x 24 bits
  output logic [4:0]   out_valid, input  logic [4:0] out_ready,
  output logic [119:0] out_data
);
  localparam int L = 0, N = 1, E = 2, S = 3, W = 4;       // port numbers

  function automatic int route(logic [23:0] f);            // dimension-order XY
    if (f[21:20] > X) return E;
    if (f[21:20] < X) return W;
    if (f[19:18] > Y) return N;
    if (f[19:18] < Y) return S;
    return L;
  endfunction

  // ---------------- input buffers (2 entries each) ----------------
  logic [23:0] head [5], tail [5];  logic [1:0] cnt [5];  logic [4:0] pop;
  always_comb for (int i = 0; i < 5; i++) in_ready[i] = (cnt[i] != 2);
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) for (int i = 0; i < 5; i++) cnt[i] <= 0;
    else for (int i = 0; i < 5; i++) begin
      logic push;  push = in_valid[i] && in_ready[i];
      if (pop[i]) head[i] <= tail[i];                      // shift
      if (push) begin
        if (cnt[i] - pop[i] == 0) head[i] <= in_data[24*i +: 24];
        else                      tail[i] <= in_data[24*i +: 24];
      end
      cnt[i] <= cnt[i] + push - pop[i];
    end

  // ---------------- output allocation (per-packet lock) ----------------
  logic [4:0] lock;  logic [2:0] owner [5], rr [5];
  always_comb begin
    pop = '0;
    for (int o = 0; o < 5; o++) begin
      out_valid[o]         = lock[o] && cnt[owner[o]] != 0;
      out_data[24*o +: 24] = head[owner[o]];
      if (out_valid[o] && out_ready[o]) pop[owner[o]] = 1'b1;
    end
  end

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin lock <= '0; for (int o = 0; o < 5; o++) rr[o] <= 0; end
    else for (int o = 0; o < 5; o++)
      if (lock[o]) begin                                     // release after the tail
        if (out_valid[o] && out_ready[o] && out_data[24*o + 22]) lock[o] <= 1'b0;
      end else begin                                         // round-robin grant
        logic done;  done = 0;
        for (int k = 0; k < 5; k++) begin
          int i;  logic busy;  i = (rr[o] + k) % 5;  busy = 0;
          for (int q = 0; q < 5; q++) if (lock[q] && owner[q] == i) busy = 1;
          if (!done && !busy && cnt[i] != 0 && head[i][23] && route(head[i]) == o) begin
            lock[o] <= 1'b1;  owner[o] <= i;  rr[o] <= (i + 1) % 5;  done = 1;
          end
        end
      end
endmodule

// 3x3 mesh. Node k = 3*y + x. Port 1 = north (y+1), 2 = east (x+1),
// 3 = south, 4 = west, 0 = local. Link (k,p) = bit 5*k+p, data 24*(5*k+p).
module mesh3x3 (
  input  logic clk, rst_n,
  input  logic [8:0] inj_valid, output logic [8:0] inj_ready, input logic [215:0] inj_data,
  output logic [8:0] ej_valid,  output logic [215:0] ej_data      // ejection always ready
);
  wire [44:0] iv, ir, ov, orr;  wire [1079:0] id, od;
  for (genvar y = 0; y < 3; y++) for (genvar x = 0; x < 3; x++) begin : node
    localparam int K = 3 * y + x;
    xy_router #(.X(x), .Y(y)) r (.clk, .rst_n,
      .in_valid(iv[5*K +: 5]),  .in_ready(ir[5*K +: 5]),   .in_data(id[120*K +: 120]),
      .out_valid(ov[5*K +: 5]), .out_ready(orr[5*K +: 5]), .out_data(od[120*K +: 120]));
    `define LINK(p, K2, p2) \
      assign iv[5*K+p] = ov[5*(K2)+p2]; \
      assign id[24*(5*K+p) +: 24] = od[24*(5*(K2)+p2) +: 24]; \
      assign orr[5*K+p] = ir[5*(K2)+p2];
    `define EDGE(p) \
      assign iv[5*K+p] = 1'b0; assign id[24*(5*K+p) +: 24] = '0; assign orr[5*K+p] = 1'b0;
    assign iv[5*K] = inj_valid[K];  assign id[24*5*K +: 24] = inj_data[24*K +: 24];
    assign inj_ready[K] = ir[5*K];  assign orr[5*K] = 1'b1;
    assign ej_valid[K] = ov[5*K];   assign ej_data[24*K +: 24] = od[24*5*K +: 24];
    if (y < 2) begin `LINK(1, K+3, 3) end else begin `EDGE(1) end   // north
    if (x < 2) begin `LINK(2, K+1, 4) end else begin `EDGE(2) end   // east
    if (y > 0) begin `LINK(3, K-3, 1) end else begin `EDGE(3) end   // south
    if (x > 0) begin `LINK(4, K-1, 2) end else begin `EDGE(4) end   // west
  end
endmodule''',

    'noc_tb': r'''
module tb;
  logic clk = 0, rst_n = 1;  always #5 clk = ~clk;
  logic [8:0] inj_valid = 0, inj_ready, ej_valid;
  logic [215:0] inj_data = 0, ej_data;
  mesh3x3 dut (.*);

  // flit: [23]H [22]T [21:20]dx [19:18]dy [17:14]src [13:8]seq [7:0]data
  localparam int NP = 40;                          // packets per source
  logic [23:0] txf [9*256];  int ntx [9], ptr [9];
  int plen [9*64], pdst [9*64], t_inj [9*64];
  int cyc = 0, got = 0, errs = 0, lat_sum [5], lat_n [5];
  int exp_idx [9], cur_src [9], cur_seq [9];       // receiver state per node
  logic go = 0, trace = 1;

  function automatic logic [23:0] flit(bit h, bit t, int d, int s, int q, int b);
    return {h, t, 2'(d % 3), 2'(d / 3), 4'(s), 6'(q), 8'(b)};
  endfunction
  task automatic mk_pkt(int s, int q, int d, int len);
    plen[64*s + q] = len; pdst[64*s + q] = d;
    for (int b = 0; b < len; b++) begin
      txf[256*s + ntx[s]] = flit(b == 0, b == len - 1, d, s, q, (q * 16 + b) & 8'hFF);
      ntx[s] = ntx[s] + 1;
    end
  endtask

  // ---- injection: each node streams its flit list, random gaps between packets ----
  always @(posedge clk) if (go) begin
    cyc++;
    for (int k = 0; k < 9; k++) begin
      if (inj_valid[k] && inj_ready[k]) ptr[k]++;
      if (ptr[k] < ntx[k] && (!inj_valid[k] || inj_ready[k])) begin
        logic [23:0] f;  f = txf[256*k + ptr[k]];
        if (!f[23] || $urandom % 4 == 0) begin     // heads wait a random time
          inj_valid[k] <= 1; inj_data[24*k +: 24] <= f;
          if (f[23]) t_inj[64*k + f[13:8]] = cyc;
        end else inj_valid[k] <= 0;
      end else if (ptr[k] >= ntx[k]) inj_valid[k] <= 0;
    end
  end

  // ---- ejection: check every packet arrives whole, in order, at the right node ----
  always @(posedge clk) if (go) for (int k = 0; k < 9; k++) if (ej_valid[k]) begin
    logic [23:0] f;  int s, q;
    f = ej_data[24*k +: 24];  s = f[17:14];  q = f[13:8];
    if (f[23]) begin cur_src[k] = s; cur_seq[k] = q; exp_idx[k] = 0; end
    if (s != cur_src[k] || q != cur_seq[k] || pdst[64*s + q] != k ||
        f[7:0] != ((q * 16 + exp_idx[k]) & 8'hFF) ||
        f[22] != (exp_idx[k] == plen[64*s + q] - 1))
      errs++;
    exp_idx[k]++;
    if (f[22]) begin
      int h;  h = (s % 3 > k % 3 ? s % 3 - k % 3 : k % 3 - s % 3)
                + (s / 3 > k / 3 ? s / 3 - k / 3 : k / 3 - s / 3);
      lat_sum[h] += cyc - t_inj[64*s + q];  lat_n[h]++;  got++;
    end
  end

  // ---- trace the links used by packet (src 0, seq 0) ----
  string pn [5];
  always @(posedge clk) if (go && trace)
    for (int k = 0; k < 9; k++) for (int p = 0; p < 5; p++)
      if (dut.ov[5*k+p] && dut.orr[5*k+p] && dut.od[24*(5*k+p) + 17 -: 10] == 0)
        $display("cyc %2d  router(%0d,%0d) -> %-5s  %s flit data=%02h", cyc, k % 3, k / 3,
          pn[p], dut.od[24*(5*k+p)+23] ? "HEAD" : dut.od[24*(5*k+p)+22] ? "TAIL" : "BODY",
          dut.od[24*(5*k+p) +: 8]);

  initial begin
    pn[0] = "LOCAL"; pn[1] = "NORTH"; pn[2] = "EAST"; pn[3] = "SOUTH"; pn[4] = "WEST";
    for (int k = 0; k < 9; k++) begin ntx[k] = 0; ptr[k] = 0; end
    for (int h = 0; h < 5; h++) begin lat_sum[h] = 0; lat_n[h] = 0; end
    mk_pkt(0, 0, 5, 3);                            // traced: (0,0) -> (2,1), 3 flits
    for (int k = 0; k < 9; k++)
      for (int q = (k == 0); q < NP; q++) begin
        int d;  d = $urandom % 9;  if (d == k) d = (d + 1) % 9;
        mk_pkt(k, q, d, 1 + $urandom % 4);
      end
    rst_n <= 0; repeat (2) @(posedge clk); rst_n <= 1; @(posedge clk); go <= 1;
    repeat (25) @(posedge clk); trace = 0;
    repeat (4000) @(posedge clk);
    $display("packets delivered=%0d/%0d  errors=%0d", got, 9 * NP, errs);
    for (int h = 1; h < 5; h++)
      $display("hops=%0d  packets=%3d  avg latency (head inject -> tail eject) = %0.1f cyc",
               h, lat_n[h], real'(lat_sum[h]) / lat_n[h]);
    $finish;
  end
endmodule''',

    'wb': r'''
// Wishbone B4 classic slave: 8 x 32-bit registers at 0x00-0x1C, registered
// ACK (one wait state per access), SEL byte enables, ERR above 0x1C.
module wb_regs (
  input  logic        clk_i, rst_i,          // Wishbone uses an active-high reset
  input  logic        cyc_i, stb_i, we_i,
  input  logic [5:0]  adr_i,                 // byte address, word aligned
  input  logic [31:0] dat_i,
  input  logic [3:0]  sel_i,
  output logic [31:0] dat_o,
  output logic        ack_o, err_o
);
  logic [31:0] r [8];
  wire req = cyc_i && stb_i && !ack_o && !err_o;   // new request (not the ack cycle)
  wire bad = adr_i[5];
  always_ff @(posedge clk_i)
    if (rst_i) begin ack_o <= 0; err_o <= 0; for (int i = 0; i < 8; i++) r[i] <= 0; end
    else begin
      ack_o <= req && !bad;                         // ACK or ERR terminates the cycle
      err_o <= req &&  bad;
      if (req && !bad) begin
        if (we_i) for (int b = 0; b < 4; b++)
                    if (sel_i[b]) r[adr_i[4:2]][8*b +: 8] <= dat_i[8*b +: 8];
        dat_o <= r[adr_i[4:2]];
      end
    end
endmodule''',

    'wb_tb': r'''
module tb;
  logic clk = 0, rst = 1;  always #5 clk = ~clk;
  logic cyc = 0, stb = 0, we = 0, ack, err;  logic [5:0] adr = 0;
  logic [31:0] dw = 0, dr;  logic [3:0] sel = 0;  int t = 0;
  wb_regs dut (.clk_i(clk), .rst_i(rst), .cyc_i(cyc), .stb_i(stb), .we_i(we),
               .adr_i(adr), .dat_i(dw), .sel_i(sel), .dat_o(dr), .ack_o(ack), .err_o(err));

  always @(posedge clk) if (!rst) begin
    t++;
    if (cyc) $display("%2d   %b   %b   %b  %02h  %b %08h |  %b   %b  %08h",
                      t, cyc, stb, we, adr, sel, dw, ack, err, ack && !we ? dr : 32'h0);
  end

  // classic single cycle: assert CYC+STB, hold everything until ACK or ERR
  task automatic wb_xfer(input logic w, input logic [5:0] a, input logic [31:0] d,
                         input logic [3:0] s, input logic keep_cyc = 0);
    cyc <= 1; stb <= 1; we <= w; adr <= a; dw <= d; sel <= s;
    do @(posedge clk); while (!(ack || err));
    stb <= 0; if (!keep_cyc) begin cyc <= 0; @(posedge clk); end   // bus released
  endtask

  initial begin
    repeat (2) @(posedge clk); rst <= 0; @(posedge clk);
    $display("clk CYC STB WE ADR SEL  DAT_W    | ACK ERR DAT_R");
    wb_xfer(1, 6'h04, 32'h1234_5678, 4'b1111);
    wb_xfer(1, 6'h04, 32'h0000_AB00, 4'b0010);       // byte lane 1 only
    wb_xfer(0, 6'h04, 0, 4'b1111, 1);                  // block read: CYC stays high
    wb_xfer(0, 6'h08, 0, 4'b1111);
    wb_xfer(0, 6'h24, 0, 4'b1111);                     // unmapped -> ERR
    @(posedge clk); $finish;
  end
endmodule''',

}

OUT = {
    'apb': [
        'cyc  phase  ADDR D PWDATA   STRB PROT RDY ERR PRDATA',
        '  4  SETUP  0004 W 11223344 1111 000  1   0   00000000',
        '  5  ACCESS 0004 W 11223344 1111 000  1   0   00000000',
        '  6  SETUP  0004 W aaaabbcc 0001 000  1   0   00000000',
        '  7  ACCESS 0004 W aaaabbcc 0001 000  1   0   00000000',
        '  8  SETUP  0004 R 00000000 0000 000  1   0   00000000',
        '  9  ACCESS 0004 R 00000000 0000 000  1   0   112233cc',
        ' 10  SETUP  0010 W cafef00d 1111 000  1   0   00000000',
        ' 11  ACC/w  0010 W cafef00d 1111 000  0   0   00000000',
        ' 12  ACC/w  0010 W cafef00d 1111 000  0   0   00000000',
        ' 13  ACCESS 0010 W cafef00d 1111 000  1   0   00000000',
        ' 14  SETUP  0010 R 00000000 0000 000  1   0   00000000',
        ' 15  ACC/w  0010 R 00000000 0000 000  0   0   cafef00d',
        ' 16  ACC/w  0010 R 00000000 0000 000  0   0   cafef00d',
        ' 17  ACCESS 0010 R 00000000 0000 000  1   0   cafef00d',
        ' 18  SETUP  0008 W 5ec00001 1111 010  1   0   00000000',
        ' 19  ACCESS 0008 W 5ec00001 1111 010  1   1   00000000',
        ' 20  SETUP  000c W 00000000 1111 000  1   0   00000000',
        ' 21  ACCESS 000c W 00000000 1111 000  1   1   00000000',
        ' 22  SETUP  100c R 00000000 0000 000  1   0   00000000',
        ' 23  ACCESS 100c R 00000000 0000 000  1   0   0a9b0004',
        ' 24  SETUP  2000 R 00000000 0000 000  1   0   00000000',
        ' 25  ACCESS 2000 R 00000000 0000 000  1   1   00000000',
        'protocol violations = 0',
    ],
    'ahb': [
        'cyc HTRANS ADR D HBURST SZ | HWDATA   RDY RESP',
        '  1 IDLE   000 R SINGLE 2 | 00000000 1 OKAY',
        '  2 NONSEQ 000 W SINGLE 2 | 00000000 1 OKAY',
        '  3 NONSEQ 010 W INCR4  2 | deadbeef 1 OKAY',
        '  4 SEQ    014 W INCR4  2 | a0a0a0a0 1 OKAY',
        '  5 SEQ    018 W INCR4  2 | a1a1a1a1 1 OKAY',
        '  6 SEQ    01c W INCR4  2 | a2a2a2a2 1 OKAY',
        '  7 NONSEQ 010 R INCR4  2 | a3a3a3a3 1 OKAY',
        '  8 SEQ    014 R INCR4  2 | 00000000 0 OKAY',
        '  9 SEQ    014 R INCR4  2 | 00000000 1 OKAY HRDATA=a0a0a0a0',
        ' 10 BUSY   018 R INCR4  2 | 00000000 0 OKAY',
        ' 11 BUSY   018 R INCR4  2 | 00000000 1 OKAY HRDATA=a1a1a1a1',
        ' 12 SEQ    018 R INCR4  2 | 00000000 1 OKAY',
        ' 13 SEQ    01c R INCR4  2 | 00000000 0 OKAY',
        ' 14 SEQ    01c R INCR4  2 | 00000000 1 OKAY HRDATA=a2a2a2a2',
        ' 15 NONSEQ 001 W SINGLE 0 | 00000000 0 OKAY',
        ' 16 NONSEQ 001 W SINGLE 0 | 00000000 1 OKAY HRDATA=a3a3a3a3',
        ' 17 NONSEQ 000 R SINGLE 2 | 00005500 1 OKAY',
        ' 18 NONSEQ 800 R SINGLE 2 | 00000000 1 OKAY HRDATA=dead55ef',
        ' 19 IDLE   000 R SINGLE 2 | 00000000 0 ERR',
        ' 20 IDLE   000 R SINGLE 2 | 00000000 1 ERR',
        ' 21 IDLE   000 R SINGLE 2 | 00000000 1 OKAY',
        ' 22 IDLE   000 R SINGLE 2 | 00000000 1 OKAY',
        'error-response cycles seen = 2',
    ],
    'axiaddr': [
        'RTL beats written: 11136',
        'WRAP4  x 4B @0x38 : 38/00001111 3c/11110000 30/00001111 34/11110000',
        'INCR4  x 4B @0x3E : 3e/11000000 40/00001111 44/11110000 48/00001111',
        'INCR16 x 8B @0xFF8: crosses 4KB = 1',
    ],
    'axiaddr_py': [
        'python model compared 11136 beats, mismatches = 0',
    ],
    'aximem': [
        'WRITE id=1 INCR   4 x 4B @100 -> BID=1 BRESP=OKAY',
        'READ  id=2 WRAP   4 x 4B @108 -> 108:08d12dfd 10c:a708a7ae 100:cc623a9b 104:6a99b44c RID=2',
        'WRITE id=3 INCR   4 x 2B @202 -> BID=3 BRESP=OKAY',
        'READ  id=4 INCR   2 x 4B @200 -> 200:fa8c0000 204:36fb7536 RID=4',
        'WRITE id=5 INCR   3 x 4B @3f2 -> BID=5 BRESP=OKAY',
        'READ  id=6 INCR   4 x 4B @3f0 -> 3f0:28b70000 3f4:c6ef3620 3f8:6526afd1 3fc:00000000 RID=6',
        'WRITE id=7 FIXED  4 x 4B @300 -> BID=7 BRESP=OKAY',
        'READ  id=8 INCR   1 x 4B @300 -> 300:3188ea6c RID=8',
        'WRITE id=9 INCR   4 x 4B @400 -> BID=9 BRESP=SLVERR',
        'read beats checked = 1197, mismatches = 0',
    ],
    'axis': [
        '  3  S: v=1 r=1 keep=1111 data=44332211 last=0 | M: v=0 r=1 data=xx last=x',
        '  4  S: v=1 r=0 keep=1101 data=88776655 last=0 | M: v=1 r=1 data=11 last=0',
        '  5  S: v=1 r=0 keep=1101 data=88776655 last=0 | M: v=1 r=0 data=22 last=0',
        '  6  S: v=1 r=0 keep=1101 data=88776655 last=0 | M: v=1 r=1 data=22 last=0',
        '  7  S: v=1 r=0 keep=1101 data=88776655 last=0 | M: v=1 r=1 data=33 last=0',
        '  8  S: v=1 r=0 keep=1101 data=88776655 last=0 | M: v=1 r=0 data=44 last=0',
        '  9  S: v=1 r=1 keep=1101 data=88776655 last=0 | M: v=1 r=1 data=44 last=0',
        ' 10  S: v=1 r=0 keep=0011 data=0000aa99 last=1 | M: v=1 r=1 data=55 last=0',
        ' 11  S: v=1 r=0 keep=0011 data=0000aa99 last=1 | M: v=1 r=0 data=77 last=0',
        ' 12  S: v=1 r=0 keep=0011 data=0000aa99 last=1 | M: v=1 r=1 data=77 last=0',
        ' 13  S: v=1 r=1 keep=0011 data=0000aa99 last=1 | M: v=1 r=1 data=88 last=0',
        ' 14  S: v=0 r=0 keep=0011 data=0000aa99 last=1 | M: v=1 r=1 data=99 last=0',
        ' 15  S: v=0 r=0 keep=0011 data=0000aa99 last=1 | M: v=1 r=0 data=aa last=1',
        ' 16  S: v=0 r=0 keep=0011 data=0000aa99 last=1 | M: v=1 r=0 data=aa last=1',
        ' 17  S: v=0 r=1 keep=0011 data=0000aa99 last=1 | M: v=1 r=1 data=aa last=1',
        'packets=501 bytes=10184 data/TLAST errors=0 stability violations=0 left=0',
    ],
    'mesi': [
        'P0 RD  bus=BusRd   rd=0000 | good: E I I mem=0000 | BUG: E I I',
        'P0 WR  bus=-       rd=0000 | good: M I I mem=0000 | BUG: M I I',
        'P1 RD  bus=BusRd   rd=0001 | good: S S I mem=0001 | BUG: S S I',
        'P2 RD  bus=BusRd   rd=0001 | good: S S S mem=0001 | BUG: S S S',
        'P1 WR  bus=BusUpgr rd=0000 | good: I M I mem=0001 | BUG: S M S',
        'P0 RD  bus=BusRd   rd=0002 | good: S S I mem=0002 | BUG: S M S',
        'P2 EV  bus=-       rd=0000 | good: S S I mem=0002 | BUG: S M I',
        'P0 WR  bus=BusUpgr rd=0000 | good: M I I mem=0002 | BUG: M M I',
        'P2 WR  bus=BusRdX  rd=0000 | good: I I M mem=0003 | BUG: I I M',
        'P1 RD  bus=BusRd   rd=0004 | good: I S S mem=0004 | BUG: I S S',
        'P2 EV  bus=-       rd=0000 | good: I S I mem=0004 | BUG: I S I',
        'P1 WR  bus=BusUpgr rd=0000 | good: I M I mem=0004 | BUG: I M I',
        'reads=6649 | good: stale=0 SWMR violations=0 | BUG=1: stale=859 viol=3570',
    ],
    'noc': [
        'cyc  4  router(0,0) -> EAST   HEAD flit data=00',
        'cyc  5  router(0,0) -> EAST   BODY flit data=01',
        'cyc  6  router(1,0) -> EAST   HEAD flit data=00',
        'cyc  7  router(0,0) -> EAST   TAIL flit data=02',
        'cyc  7  router(1,0) -> EAST   BODY flit data=01',
        'cyc  8  router(2,0) -> NORTH  HEAD flit data=00',
        'cyc  9  router(1,0) -> EAST   TAIL flit data=02',
        'cyc  9  router(2,0) -> NORTH  BODY flit data=01',
        'cyc 13  router(2,1) -> LOCAL  HEAD flit data=00',
        'cyc 14  router(2,0) -> NORTH  TAIL flit data=02',
        'cyc 14  router(2,1) -> LOCAL  BODY flit data=01',
        'cyc 15  router(2,1) -> LOCAL  TAIL flit data=02',
        'packets delivered=360/360  errors=0',
        'hops=1  packets=130  avg latency (head inject -> tail eject) = 9.4 cyc',
        'hops=2  packets=125  avg latency (head inject -> tail eject) = 12.7 cyc',
        'hops=3  packets= 79  avg latency (head inject -> tail eject) = 15.5 cyc',
        'hops=4  packets= 26  avg latency (head inject -> tail eject) = 18.4 cyc',
    ],
    'wb': [
        'clk CYC STB WE ADR SEL  DAT_W    | ACK ERR DAT_R',
        ' 2   1   1   1  04  1111 12345678 |  0   0  00000000',
        ' 3   1   1   1  04  1111 12345678 |  1   0  00000000',
        ' 5   1   1   1  04  0010 0000ab00 |  0   0  00000000',
        ' 6   1   1   1  04  0010 0000ab00 |  1   0  00000000',
        ' 8   1   1   0  04  1111 00000000 |  0   0  00000000',
        ' 9   1   1   0  04  1111 00000000 |  1   0  1234ab78',
        '10   1   1   0  08  1111 00000000 |  0   0  00000000',
        '11   1   1   0  08  1111 00000000 |  1   0  00000000',
        '13   1   1   0  24  1111 00000000 |  0   0  00000000',
        '14   1   1   0  24  1111 00000000 |  0   1  00000000',
    ],
}


def _v(name, caption=None):
    """Show a verified source listing from SRC."""
    code(SRC[name].split("\n"), caption)


def _o(name, caption=None):
    """Show real simulator (or Python model) output captured from a run."""
    out(OUT[name], caption)


def _wave(sigs, W=7, NW=10):
    """ASCII timing diagram. sigs: list of (name, kind, values) where kind is
    'clk' (values = number of cycles), 'bit' (string of 0/1 per cycle),
    'bus' (list of labels per cycle, '' = no valid value) or 'txt'."""
    n = max(v if k == "clk" else len(v) for _, k, v in sigs)
    out = []
    for name, kind, vals in sigs:
        s = name.ljust(NW)
        if kind == "clk":
            h = W // 2
            s += ("/" + "~" * (h - 1) + "\\" + "_" * (W - h - 1)) * vals
        elif kind == "bit":
            prev = None
            for v in vals:
                lvl = "~" if v == "1" else "_"
                if prev is not None and v != prev:
                    s += "/" if v == "1" else "\\"
                else:
                    s += lvl
                s += lvl * (W - 1)
                prev = v
        else:
            runs, i = [], 0
            while i < len(vals):
                j = i
                while j < len(vals) and vals[j] == vals[i]:
                    j += 1
                runs.append((vals[i], j - i)); i = j
            first = True
            for lab, cnt in runs:
                width = cnt * W
                if kind == "txt":
                    s += lab.center(width)
                    continue
                seg = "=" * (width - 1) if lab == "" else (" " + lab + " ").center(width - 1)
                pre = ("=" if lab == "" else " ") if first else "X"
                s += pre + seg
                first = False
        out.append(s.rstrip())
    return out


# =============================================================================
#                      PART II - ON-CHIP PROTOCOLS
# =============================================================================
def part2():
    part("On-Chip Protocols",
         "Inside the die, every processor, accelerator, memory controller "
         "and peripheral talks through on-chip buses. This part covers them "
         "from the simplest to the most sophisticated: the AMBA family (APB, "
         "AHB, AXI4, AXI4-Lite and AXI4-Stream), the cache-coherency "
         "protocols that keep many caches consistent (MESI/MOESI, ACE and "
         "CHI), and the alternatives - Wishbone, Avalon, TileLink, OCP - "
         "together with the networks-on-chip that carry all of them across "
         "large SoCs.")
    _ch5()
    _ch6()
    _ch7()
    _ch8()
    _ch9()
    _ch10()


# ---------------------------------------------------------------- Ch 5 ----
def _ch5():
    chapter("AMBA APB: The Advanced Peripheral Bus", newpage=False)
    p("Every SoC has hundreds of small registers: UART baud dividers, GPIO "
      "direction bits, timer compare values, PLL settings, interrupt masks. "
      "None of them needs bandwidth; all of them need a bus that is cheap in "
      "gates, easy to decode, trivially timed and simple to verify. That bus "
      "is the **AMBA Advanced Peripheral Bus (APB)**. It is the slowest and "
      "simplest member of the AMBA family, and for exactly that reason it is "
      "the protocol that most engineers write first and that shows up in "
      "every tapeout: a typical smartphone SoC has dozens of APB subsystems "
      "hanging off AXI or AHB bridges.")
    p("This chapter covers APB in full: its history from APB2 to APB5, "
      "every signal, the three-state transfer machine, cycle-accurate timing "
      "with and without wait states, error signalling, protection and byte "
      "strobes, the bridge that feeds it and the decoder that fans it out. "
      "We finish with a verified APB4 slave, an address decoder with a "
      "default slave, and a testbench master whose trace shows wait states "
      "and PSLVERR cycle by cycle. The companion RTL Design guide built a "
      "minimal APB register block; here the focus is the protocol itself and "
      "the corner cases that interviewers and verification engineers probe.")

    h2("Where APB sits and why it exists")
    p("APB is a **non-pipelined**, single-requester, single-outstanding "
      "protocol. One transfer occupies at least two clock cycles and nothing "
      "else happens on the bus until it finishes. Compare that with AHB "
      "(pipelined address/data) and AXI (independent channels, many "
      "outstanding transactions). APB gives up all performance to gain:")
    bul(["**Tiny area**: no burst logic, no pipelining, no IDs. A slave is a "
         "decoder, a few flops and a read mux.",
         "**Easy timing**: all signals are registered by the requester and "
         "sampled on the next rising edge; APB clocks (PCLK) are usually a "
         "divided, slower copy of the system clock, which relaxes timing on "
         "long wires across the die.",
         "**Low power**: signals toggle only during an access; APB5 even "
         "adds a wake-up hint so the peripheral clock can be gated.",
         "**Simple verification**: the whole protocol is a handful of "
         "assertions (Section 5.9)."])
    diagram([
        "   +--------+   AXI/CHI   +-------------+   AXI   +-----------+  APB  +------+",
        "   |  CPU   |============>| interconnect|========>| AXI-to-APB|=====> | UART |",
        "   | cluster|             |  (NoC/xbar) |         |  bridge   |   |   +------+",
        "   +--------+             +-------------+         | (APB      |   +-> | GPIO |",
        "                                 |                |  master)  |   |   +------+",
        "                                 v                +-----------+   +-> |Timer |",
        "                          DDR, SRAM, accel.                       |   +------+",
        "                                                                  +-> | PLL  |",
        "                                                                      +------+",
    ], "APB is the leaf of the SoC bus tree: one bridge (the only APB requester) "
       "fans out to many low-bandwidth peripherals.")
    box("key", "Terminology: manager/subordinate",
        "Older AMBA specifications say master/slave; issues published since "
        "about 2020 use **Requester/Completer** for APB and **Manager/"
        "Subordinate** for AHB and AXI. Signal names did not change. This "
        "book uses master/slave and manager/subordinate interchangeably, "
        "because both appear in RTL, documentation and interviews.")

    h2("History: APB2, APB3, APB4 and APB5")
    tbl(["Version", "AMBA generation", "What it added", "Typical use today"],
        [["**APB2** (often just 'APB')", "AMBA 2 (1999)",
          "Base protocol: PSEL, PENABLE, PWRITE, PADDR, PWDATA, PRDATA. "
          "Every transfer exactly 2 cycles, no wait, no error",
          "Legacy IP; still seen in old peripherals"],
         ["**APB3**", "AMBA 3 (2003-2004)",
          "**PREADY** (wait states) and **PSLVERR** (error response)",
          "Very common baseline for IP"],
         ["**APB4**", "AMBA 4 (2010)",
          "**PPROT[2:0]** (privilege, security, instruction) and "
          "**PSTRB[n-1:0]** (write byte strobes)",
          "Default choice for new designs"],
         ["**APB5**", "AMBA 5 (spec issues from about 2020 on)",
          "PWAKEUP; optional user signals (PAUSER, PWUSER, PRUSER, PBUSER); "
          "optional parity check signals for functional safety; later "
          "issues add Realm Management Extension support (PNSE)",
          "Safety (ISO 26262) and power-managed SoCs"]],
        widths=[16, 16, 44, 24], bold_first=True)
    p("The versions are backward compatible in a useful way: an APB3 slave "
      "works on an APB4 bus if you leave PPROT/PSTRB unconnected (it simply "
      "writes all bytes and ignores protection), and an APB2 slave works on "
      "an APB3 bus if you tie its PREADY high and PSLVERR low in the "
      "decoder. The reverse is not true: an APB4 slave that relies on PSTRB "
      "must see real strobes, so a bridge that drives PSTRB = 0 for writes "
      "(a common integration bug) turns every write into a no-op.")

    h2("Signal reference")
    p("All APB signals are prefixed with **P**. The requester drives "
      "everything except PRDATA, PREADY and PSLVERR, which each completer "
      "drives back through a multiplexer in the decoder.")
    tbl(["Signal", "Width", "Driver", "Meaning"],
        [["PCLK", "1", "clock", "All signals are timed to its rising edge"],
         ["PRESETn", "1", "reset", "Active-low reset, usually the system reset "
          "synchronized to PCLK"],
         ["PADDR", "up to 32", "requester", "Byte address; may be unaligned "
          "in principle but real peripherals decode word addresses"],
         ["PSELx", "1 per slave", "requester/decoder", "Selects completer x; "
          "high for the whole transfer"],
         ["PENABLE", "1", "requester", "Low in the SETUP cycle, high in the "
          "ACCESS cycle(s)"],
         ["PWRITE", "1", "requester", "1 = write, 0 = read"],
         ["PWDATA", "8/16/32", "requester", "Write data, valid while PWRITE "
          "is high"],
         ["PSTRB", "PWDATA/8", "requester", "APB4: one bit per byte lane of "
          "PWDATA; must be all zero for reads"],
         ["PPROT[2:0]", "3", "requester", "APB4: [0] 1 = privileged, [1] 1 = "
          "**non-secure**, [2] 1 = instruction access"],
         ["PRDATA", "8/16/32", "completer", "Read data, sampled in the last "
          "ACCESS cycle"],
         ["PREADY", "1", "completer", "APB3+: low extends the ACCESS phase "
          "(wait states)"],
         ["PSLVERR", "1", "completer", "APB3+: error for this transfer, only "
          "meaningful when PSEL, PENABLE and PREADY are all high"],
         ["PWAKEUP", "1", "requester", "APB5: activity hint, may rise before "
          "PSEL so the completer can ungate clocks"],
         ["PAUSER, PWUSER,\nPRUSER, PBUSER", "user", "both", "APB5: "
          "user-defined sideband (for example a master ID or QoS hint)"],
         ["xxxCHK", "varies", "both", "APB5 optional odd-parity check bits "
          "per signal group, for safety mechanisms"]],
        widths=[18, 12, 18, 52], bold_first=True)
    box("warn", "PITFALL: PPROT[1] is NON-secure",
        "PPROT[1] = 1 means a **non-secure** access (the same polarity as "
        "AxPROT[1] in AXI). Designers who read it as 'secure = 1' build "
        "TrustZone firewalls that block the secure world and let the "
        "normal world in. Write the polarity into the register "
        "specification and cover both values in the testbench.")

    h2("The transfer state machine")
    p("The APB specification describes the requester with three states. "
      "Every transfer visits SETUP exactly once and ACCESS one or more "
      "times:")
    diagram([
        "                    no transfer",
        "                   +---------+",
        "                   |         v",
        "                +------------------+",
        "                |      IDLE        |   PSEL=0, PENABLE=0",
        "                +------------------+",
        "                   | transfer                    ^",
        "                   v                             | PREADY=1 and",
        "                +------------------+             | no transfer",
        "                |      SETUP       |   PSEL=1, PENABLE=0 (exactly 1 cycle)",
        "                +------------------+             |",
        "                   | always                      |",
        "                   v                             |",
        "  PREADY=0      +------------------+-------------+",
        "  +------------>|      ACCESS      |   PSEL=1, PENABLE=1",
        "  |             +------------------+-------------+",
        "  +---------------|                              | PREADY=1 and",
        "                                                 | next transfer -> SETUP",
    ], "APB requester operating states. Address, control and write data must "
       "stay stable from SETUP until the ACCESS cycle in which PREADY is high.")
    bul(["**IDLE**: PSELx low. The bus parks here when there is nothing to do.",
         "**SETUP**: PSELx rises, PADDR/PWRITE/PWDATA/PSTRB/PPROT become valid, "
         "PENABLE is low. Lasts exactly one PCLK cycle.",
         "**ACCESS**: PENABLE rises. The completer samples the transfer; if "
         "PREADY is low the requester stays in ACCESS with everything held "
         "stable. When PREADY is high the transfer completes on that rising "
         "edge; the requester returns to IDLE or goes straight to SETUP for "
         "a back-to-back transfer (PSEL may stay high, PENABLE must drop)."])
    p("Two consequences follow. First, the best-case throughput is **one "
      "transfer per two PCLK cycles**: at 100 MHz with 32-bit data that is "
      "200 MB/s peak, plenty for registers but nothing like a data path. "
      "Second, because PENABLE must go low between transfers, a completer "
      "can always recognize the start of a new transfer as the "
      "`PSEL & ~PENABLE` cycle.")

    h2("Timing diagrams")
    p("In the diagrams below each column is one PCLK cycle. Signals change "
      "just after a rising edge and are sampled by the completer (or "
      "requester) on the next rising edge; '=' marks a bus with no valid "
      "value.")
    h3("Write and read without wait states")
    diagram(_wave([
        ("", "txt", ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]),
        ("PCLK", "clk", 7),
        ("PADDR", "bus", ["", "A1", "A1", "A2", "A2", "", ""]),
        ("PWRITE", "bit", "0111000"),
        ("PSEL", "bit", "0111100"),
        ("PENABLE", "bit", "0010100"),
        ("PWDATA", "bus", ["", "D1", "D1", "", "", "", ""]),
        ("PRDATA", "bus", ["", "", "", "", "Q2", "", ""]),
        ("PREADY", "bit", "0010100"),
        ("state", "txt", ["IDLE", "SETUP", "ACCESS", "SETUP", "ACCESS", "IDLE", "IDLE"]),
    ]), "Write to A1 followed immediately by a read of A2. PSEL stays high "
        "between the transfers; PENABLE drops for the second SETUP. The "
        "write completes at the edge ending T3, the read data Q2 is sampled "
        "at the edge ending T5.")
    h3("Transfers with wait states")
    diagram(_wave([
        ("", "txt", ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"]),
        ("PCLK", "clk", 8),
        ("PADDR", "bus", ["", "A1", "A1", "A1", "A1", "", "", ""]),
        ("PWRITE", "bit", "00000000"),
        ("PSEL", "bit", "01111000"),
        ("PENABLE", "bit", "00111000"),
        ("PREADY", "bit", "00001000"),
        ("PRDATA", "bus", ["", "", "", "", "Q1", "", "", ""]),
        ("PSLVERR", "bit", "00000000"),
        ("state", "txt", ["IDLE", "SETUP", "ACC", "ACC", "ACC", "IDLE", "IDLE", "IDLE"]),
    ]), "Read with two wait states. The completer holds PREADY low in T3 and "
        "T4; the requester keeps PADDR, PWRITE, PSEL and PENABLE stable. "
        "PRDATA is only required to be valid in the final ACCESS cycle (T5).")
    p("PREADY is **don't care** outside ACCESS: many completers simply "
      "drive it high all the time except when they need to stall, and a "
      "completer that never stalls ties it to 1. The requester, however, "
      "must only look at PREADY when PSEL and PENABLE are both high.")
    h3("Error response")
    diagram(_wave([
        ("", "txt", ["T1", "T2", "T3", "T4", "T5", "T6"]),
        ("PCLK", "clk", 6),
        ("PADDR", "bus", ["", "A1", "A1", "A1", "", ""]),
        ("PWRITE", "bit", "011100"),
        ("PSEL", "bit", "011100"),
        ("PENABLE", "bit", "001100"),
        ("PREADY", "bit", "000100"),
        ("PSLVERR", "bit", "000100"),
        ("state", "txt", ["IDLE", "SETUP", "ACC", "ACC", "IDLE", "IDLE"]),
    ]), "A write that fails: PSLVERR is high in the last ACCESS cycle, "
        "together with PREADY. PSLVERR is only sampled in that cycle.")
    p("The APB specification is deliberately loose about what an error "
      "means. A failed write **may or may not** have changed the "
      "completer's state, and a failed read may return any data. It is "
      "the bridge's job to convert PSLVERR into the upstream error "
      "(SLVERR on AXI, ERROR on AHB) so that software sees a bus fault. "
      "Typical reasons for asserting PSLVERR are: an access to an unmapped "
      "offset inside the peripheral, a write to a read-only register, a "
      "non-secure or unprivileged access to a protected register (PPROT), "
      "a FIFO overflow, or a timeout in a clock-domain-crossing wrapper.")
    box("tip", "Tie off unused completer outputs",
        "An APB2 peripheral on an APB3/4 bus has no PREADY/PSLVERR. Tie "
        "PREADY = 1 and PSLVERR = 0 **inside the decoder**, per port. "
        "Leaving them floating in RTL gives X in simulation and random "
        "values in silicon, and the lint tool will only warn.")

    h2("PSTRB and PPROT in practice")
    p("**PSTRB** lets software do byte and halfword writes to a 32-bit APB "
      "register, which matters for C code that writes `uint8_t` fields in a "
      "packed register struct. The completer ANDs each byte lane's write "
      "enable with its strobe bit. Two rules: PSTRB must be all zero for "
      "reads, and an APB4 completer is allowed to ignore PSTRB (treating "
      "every write as full-word) only if the register specification says "
      "so. Sparse strobes (for example 4'b1001) are legal and must be "
      "handled or explicitly flagged as an error.")
    p("**PPROT** carries the same three attributes as AXI's AxPROT: "
      "privilege, security and instruction/data. In a TrustZone system a "
      "secure peripheral (a key store, the secure watchdog, a TZPC "
      "configuration block) checks PPROT[1] and answers non-secure "
      "accesses with PSLVERR, or with read-as-zero/write-ignored (RAZ/WI) "
      "if the security architecture prefers not to reveal the register's "
      "existence. Whichever policy is chosen must be consistent across the "
      "SoC and written down for the firmware team.")

    h2("Bridges: how APB is fed")
    p("An APB bus has exactly one requester, and it is almost always a "
      "bridge from a faster protocol. The bridge is an AHB or AXI "
      "completer on one side and the APB requester on the other.")
    h3("AHB-to-APB bridge")
    p("The AHB side captures the address phase (HADDR, HWRITE, HSIZE, "
      "HPROT) when HSEL and HREADY are high and the transfer is NONSEQ or "
      "SEQ. For a read it can start the APB SETUP immediately; for a write "
      "it must wait one cycle because HWDATA only arrives in the AHB data "
      "phase. While the APB transfer runs the bridge holds HREADYOUT low. "
      "PSLVERR becomes the two-cycle AHB ERROR response (Chapter 6). A "
      "typical non-buffered bridge therefore costs about three AHB cycles "
      "per write and per read at equal clocks, more when PCLK is a "
      "divided clock. Some bridges **post** writes (return OKAY on AHB "
      "before the APB write finishes) to hide the latency, which means "
      "PSLVERR on a posted write can no longer be reported to the "
      "requester that caused it.")
    h3("AXI-to-APB bridge")
    p("An AXI bridge must also serialize: it accepts one AW+W or one AR at a "
      "time (arbitrating between reads and writes), splits any burst into "
      "individual APB transfers, generates PSTRB from WSTRB, maps AxPROT to "
      "PPROT, and returns B or R with SLVERR if any beat saw PSLVERR. "
      "Because APB has no IDs, the bridge echoes the stored AXI ID. The "
      "Arm CoreLink bridges also support **multiple APB ports**, i.e. the "
      "decoder of Section 5.8 is built into the bridge.")
    box("expert", "Clock domains and APB",
        "The APB clock is frequently a synchronous divided clock (PCLK = "
        "HCLK/2, /4) with a clock-enable in the bridge, so no CDC is needed. "
        "When a peripheral lives in a truly asynchronous domain (for example "
        "an always-on block), put an **APB asynchronous bridge** (a "
        "request/acknowledge handshake, Chapter 4) in front of it: the APB "
        "transfer on the fast side waits with PREADY low until the slow side "
        "acknowledges. Budget several slow-clock cycles of latency per "
        "access and never poll such a register in a tight loop.")

    h2("Decoding and multiplexing multiple completers")
    p("PADDR, PWRITE, PENABLE, PWDATA, PSTRB and PPROT are broadcast to all "
      "completers. The decoder turns the address into one-hot PSELx and "
      "multiplexes PRDATA, PREADY and PSLVERR back from the selected "
      "completer:")
    diagram([
        "                PADDR[high bits]",
        "                     |",
        "                +----v----+  PSEL0   +-----------+",
        "   PSEL ------->| address |--------->| completer0|--+ PRDATA0/PREADY0/PSLVERR0",
        "                | decoder |  PSEL1   +-----------+  |",
        "                |         |--------->| completer1|--+ PRDATA1/...",
        "                |         |  (none)  +-----------+  |",
        "                |         |------+                  |",
        "                +---------+      v                  v",
        "                          +-------------+    +-------------+",
        "                          | default     |--->| return mux  |--> PRDATA,",
        "                          | slave: ERR  |    | (select by  |    PREADY,",
        "                          +-------------+    |  PSELx)     |    PSLVERR",
        "                                             +-------------+",
    ], "APB decoder: one-hot PSELx, a return multiplexer, and a default slave "
       "that answers unmapped addresses with PSLVERR.")
    bul(["**Decode on PADDR only while PSEL is high.** When the requester is "
         "idle, all PSELx must be low.",
         "**Default slave.** An address that hits nothing must still "
         "complete, otherwise the bus hangs forever with PREADY low. The "
         "decoder answers it with PREADY = 1 and PSLVERR = 1 in ACCESS.",
         "**Mux PRDATA with PSELx, not with PADDR alone**, and drive zero "
         "when nothing is selected; this avoids X propagation in simulation "
         "and saves power in silicon.",
         "Use **AND-OR multiplexing** (each completer drives zero when not "
         "selected, then OR everything) when there are many completers; it "
         "synthesizes to a shallow tree and is the style used in many "
         "commercial APB subsystems."])

    h2("Verification: the protocol rules as assertions")
    p("Almost the whole APB protocol can be checked with a handful of "
      "SystemVerilog assertions bound to the interface. A checker like this "
      "belongs on every APB port in the SoC-level testbench:")
    code([
        "// APB protocol checker (bind to every APB port)",
        "property p_setup_then_access;      // SETUP is followed by ACCESS",
        "  @(posedge pclk) disable iff (!presetn)",
        "    psel && !penable |=> psel && penable;",
        "endproperty",
        "property p_stable_in_access;       // everything stable until PREADY",
        "  @(posedge pclk) disable iff (!presetn)",
        "    psel && penable && !pready |=> $stable({paddr, pwrite, pwdata, pstrb, pprot})",
        "                                   && psel && penable;",
        "endproperty",
        "property p_enable_drops;           // PENABLE low after completion",
        "  @(posedge pclk) disable iff (!presetn)",
        "    psel && penable && pready |=> !penable;",
        "endproperty",
        "property p_read_strobes_zero;      // APB4: PSTRB = 0 on reads",
        "  @(posedge pclk) disable iff (!presetn) psel && !pwrite |-> pstrb == '0;",
        "endproperty",
        "a1: assert property (p_setup_then_access);",
        "a2: assert property (p_stable_in_access);",
        "a3: assert property (p_enable_drops);",
        "a4: assert property (p_read_strobes_zero);",
        "c1: cover  property (@(posedge pclk) psel && penable && !pready);   // saw a wait",
        "c2: cover  property (@(posedge pclk) psel && penable && pready && pslverr);",
    ], "Four assertions and two covers capture nearly all of APB. The covers "
       "prove that the test actually exercised wait states and errors.")
    p("Add a **timeout** assertion (PREADY must rise within N cycles, where "
      "N comes from the peripheral's specification) and an X-check on "
      "PRDATA when PREADY is high for a read. For register-level "
      "verification the UVM register layer (Chapter 25) drives this "
      "interface through an adapter; the APB agent is the simplest VIP most "
      "DV engineers ever write, which is why it is the classic first UVM "
      "project.")

    h2("Hands-on: APB4 slave, decoder and a testbench master")
    p("The example has three pieces. `apb4_regs` is an APB4 completer with "
      "five registers: CTRL and SCRATCH (read/write), KEY (secure only: a "
      "non-secure access, PPROT[1] = 1, gets PSLVERR), ID (read-only: a "
      "write gets PSLVERR) and SLOW, which inserts a programmable number "
      "of wait states. Writes honour PSTRB and commit exactly once, in the "
      "final ACCESS cycle. `apb_mux` decodes two completers at 0x00xx and "
      "0x10xx and contains a default slave for everything else.")
    _v("apb", "apb4_regs (APB4 completer) and apb_mux (decoder, return mux "
              "and default slave).")
    p("The testbench master is a single task that performs SETUP for one "
      "cycle and then ACCESS until PREADY is sampled high, exactly the "
      "state machine of Section 5.4. A monitor prints every cycle in which "
      "PSEL is high and checks that address, direction and write data do "
      "not change while the completer is stalling.")
    _v("apb_tb", "Testbench: APB master task, cycle trace and a stability "
                 "checker. Compiled with iverilog -g2012 -Wall.")
    _o("apb", "Real Icarus Verilog output. ACC/w marks an ACCESS cycle with "
              "PREADY low (a wait state).")
    p("Read the trace from top to bottom:")
    bul(["Cycles 4-5: a full-word write to SCRATCH, two cycles, no wait.",
         "Cycles 6-9: a write with PSTRB = 0001 changes only byte 0 (0xCC), "
         "so the read-back is 0x112233CC. Note PSTRB = 0000 on the read.",
         "Cycles 10-17: SLOW inserts two wait states on both the write and "
         "the read. The completer drives PRDATA early (cycle 15), but only "
         "the value in cycle 17, when PREADY is high, counts.",
         "Cycle 19: a non-secure write (PPROT = 010) to KEY returns PSLVERR. "
         "Cycle 21: a write to the read-only ID register returns PSLVERR.",
         "Cycle 23: the read of 0x100C reaches the second completer and "
         "returns its ID. Cycle 25: 0x2000 matches nothing, and the default "
         "slave completes the transfer with PSLVERR instead of hanging the "
         "bus.",
         "Transfers run back to back: SETUP follows ACCESS directly, with PSEL "
         "staying high, which the protocol allows."])
    box("warn", "PITFALL: committing a write more than once",
        "A completer that writes its register whenever `psel && penable && "
        "pwrite` is true commits the write in **every** wait-state cycle. "
        "That is harmless for a plain register but fatal for a FIFO push, a "
        "write-1-to-clear status bit or a counter increment. Qualify every "
        "side effect with PREADY, as `wr` does in `apb4_regs`. The same "
        "rule applies to read side effects (clear-on-read registers, FIFO "
        "pops): they must happen exactly once, in the completing cycle.")
    box("warn", "PITFALL: combinational PREADY paths",
        "PREADY often comes from deep inside a peripheral (a FIFO full flag, "
        "a CDC handshake). If it is combinational from PADDR through the "
        "decoder, the peripheral and the return mux back into the bridge, it "
        "can become the critical path of the whole APB subsystem. Keep "
        "PREADY registered where possible, as the wait counter in the "
        "example does.")

    h2("Who owns what, and interview insights")
    tbl(["Team", "APB responsibilities"],
        [["RTL (IP)", "Completer logic, register map, PSLVERR policy, "
          "exactly-once side effects, PSTRB/PPROT handling"],
         ["RTL (integration)", "Bridge and decoder configuration, address map, "
          "tie-offs for APB2/APB3 IP, clock ratio between HCLK and PCLK"],
         ["DV", "APB VIP and assertions, register-model tests (reset values, "
          "access types), error and wait-state coverage"],
         ["PD / STA", "Usually easy; watch long PRDATA/PREADY return paths "
          "on a large die, and the multicycle constraints of a divided PCLK"],
         ["Firmware", "Register headers, byte-access rules, handling of bus "
          "faults raised by PSLVERR"]],
        widths=[22, 78], bold_first=True)
    box("expert", "Interview questions you should be able to answer",
        ["**Why does APB need two cycles minimum?** SETUP gives the "
         "completer one full cycle of stable address/control to decode "
         "before PENABLE says 'do it now'; this is what makes the protocol "
         "timing-friendly and decode-friendly without pipelining.",
         "**Can PSEL stay high between two transfers?** Yes, when the second "
         "transfer is to the same completer; PENABLE must still go low for "
         "one SETUP cycle.",
         "**What happens if a slave never asserts PREADY?** The bus and the "
         "CPU hang. Real SoCs add a timeout monitor in the bridge that "
         "forces an error response after N cycles.",
         "**When is PRDATA valid?** Only in the last ACCESS cycle "
         "(PSEL & PENABLE & PREADY & !PWRITE)."])

    h2("Summary")
    bul(["APB is the non-pipelined, single-outstanding leaf bus for "
         "registers and low-bandwidth peripherals; its only requester is a "
         "bridge.",
         "APB3 added PREADY and PSLVERR, APB4 added PPROT and PSTRB, APB5 "
         "adds PWAKEUP, user and parity signals.",
         "Every transfer is SETUP (one cycle) plus ACCESS (one or more "
         "cycles, extended by PREADY low); all requester signals are stable "
         "until the completing edge.",
         "PSLVERR and PRDATA are only meaningful in the final ACCESS cycle; "
         "side effects must happen exactly once, in that cycle.",
         "A decoder produces one-hot PSELx, multiplexes the return signals "
         "and needs a default slave so unmapped accesses complete with an "
         "error instead of hanging.",
         "The verified example showed wait states, PSTRB byte writes, "
         "PPROT-based security errors and a default-slave error."])

    h2("Exercises")
    bul(["Draw the timing diagram for a write with one wait state followed "
         "by a read with zero wait states to a different completer. Mark the "
         "edges where each completer samples its inputs.",
         "Modify `apb4_regs` so that KEY is read-as-zero/write-ignored "
         "(RAZ/WI) for non-secure accesses instead of returning PSLVERR. "
         "What does firmware lose and gain with each policy?",
         "An APB peripheral runs at PCLK = HCLK/4 with a clock-enable in the "
         "AHB-to-APB bridge. Count the HCLK cycles for a zero-wait APB read, "
         "from the AHB address phase to the AHB data phase completing.",
         "Write an SVA property that fails if PSLVERR is ever high while "
         "PREADY is low during ACCESS, and explain why a completer might "
         "legitimately do that (hint: what does the spec require?).",
         "Add a timeout to `apb_mux`: if PREADY stays low for 64 cycles, "
         "force PREADY = 1 and PSLVERR = 1. What must the completer do when "
         "its late PREADY finally arrives?",
         "Estimate the maximum register-write rate (writes per second) of a "
         "CPU at 2 GHz writing an APB register at PCLK = 50 MHz through a "
         "non-posted bridge with 20 ns of interconnect latency each way."])


# ---------------------------------------------------------------- Ch 6 ----
def _ch6():
    chapter("AMBA AHB and AHB-Lite")
    p("The **Advanced High-performance Bus (AHB)** sits between APB and AXI. "
      "It introduced the idea that dominates every fast on-chip bus since: "
      "**pipelining** the address of the next transfer with the data of the "
      "current one, so that a stream of transfers moves one word per clock. "
      "AHB is still everywhere in microcontrollers (every Arm Cortex-M0/M3/"
      "M4 core exposes AHB-Lite, Cortex-M23/M33 expose AHB5), in "
      "low-power subsystems of large SoCs, in on-chip flash controllers and "
      "in countless third-party IP blocks. Understanding its address/data "
      "pipeline is also the best preparation for AXI.")

    h2("Three generations: AHB, AHB-Lite and AHB5")
    tbl(["Variant", "Spec", "Key features", "Status"],
        [["**AHB** (multi-master)", "AMBA 2 (1999)",
          "Shared bus with a central **arbiter** (HBUSREQx, HGRANTx, HLOCKx, "
          "HMASTER, HMASTLOCK); 2-bit HRESP with OKAY, ERROR, **RETRY** and "
          "**SPLIT**; HSPLITx for split transactions",
          "Obsolete for new design; complex, poor for multi-master "
          "throughput"],
         ["**AHB-Lite**", "AMBA 3 (2006)",
          "**Single master** per bus; 1-bit HRESP (OKAY/ERROR); no "
          "arbitration signals, no RETRY/SPLIT. Multiple masters are "
          "handled by a **multi-layer interconnect** instead",
          "The workhorse of MCUs and peripheral subsystems"],
         ["**AHB5**", "AMBA 5 (2015)",
          "AHB-Lite plus: **HNONSEC** (TrustZone), **HEXCL/HEXOKAY** "
          "(exclusive access), HMASTER, extended HPROT[6:0] memory "
          "types, optional user signals (HAUSER, HWUSER, HRUSER, HBUSER), "
          "a secure/non-secure split, and (in later issues) parity check "
          "signals; formally renamed master/slave to manager/subordinate",
          "Cortex-M23/M33/M55/M85 and new IP"]],
        widths=[16, 13, 50, 21], bold_first=True)
    p("The rest of this chapter describes AHB-Lite (and AHB5, which is a "
      "superset) in detail, then shows how the multi-master problem is "
      "solved with a multi-layer interconnect, and finally what the old "
      "AMBA 2 arbitration looked like, because legacy IP and interview "
      "questions still use it.")

    h2("Signal reference (AHB-Lite / AHB5)")
    tbl(["Signal", "Dir (from master)", "Meaning"],
        [["HCLK, HRESETn", "global", "Clock (all signals timed to its rising edge) "
          "and active-low reset"],
         ["HADDR[31:0]", "out", "Byte address of the transfer (address phase)"],
         ["HTRANS[1:0]", "out", "00 **IDLE**, 01 **BUSY**, 10 **NONSEQ**, 11 **SEQ**"],
         ["HWRITE", "out", "1 = write, 0 = read"],
         ["HSIZE[2:0]", "out", "Bytes per beat = 2^HSIZE: 000 byte, 001 half, 010 word, "
          "011 dword, up to 111 = 1024 bits; must not exceed the bus width"],
         ["HBURST[2:0]", "out", "000 SINGLE, 001 INCR (undefined length), 010 WRAP4, "
          "011 INCR4, 100 WRAP8, 101 INCR8, 110 WRAP16, 111 INCR16"],
         ["HPROT[3:0] / [6:0]", "out", "[0] 1 = data (0 = opcode fetch), [1] 1 = privileged, "
          "[2] bufferable, [3] cacheable. AHB5 extended memory types: [3] "
          "becomes modifiable, plus [4] lookup, [5] allocate, [6] shareable"],
         ["HMASTLOCK", "out", "Current transfer is part of a locked sequence"],
         ["HWDATA", "out", "Write data (**data phase**, one cycle after the address)"],
         ["HNONSEC", "out", "AHB5: 1 = non-secure transfer"],
         ["HEXCL, HMASTER", "out", "AHB5: exclusive transfer; master ID for the monitor"],
         ["HSELx", "decoder", "Selects slave x (combinational decode of HADDR)"],
         ["HRDATA", "in", "Read data from the slave, through the read mux"],
         ["HREADYOUT", "slave out", "Slave: 0 = extend the data phase (wait state)"],
         ["HREADY", "in (to all)", "Multiplexed HREADYOUT of the slave in the data "
          "phase; tells **every** slave and the master that the bus moved"],
         ["HRESP", "in", "0 OKAY, 1 ERROR (AHB-Lite/AHB5)"],
         ["HEXOKAY", "in", "AHB5: exclusive transfer succeeded"]],
        widths=[20, 14, 66], bold_first=True)
    box("key", "HREADY versus HREADYOUT",
        "Each slave **drives** HREADYOUT and **receives** HREADY. HREADY is "
        "the HREADYOUT of whichever slave currently owns the data phase, "
        "selected by the slave multiplexer. A slave must only sample the "
        "address phase (HSEL, HADDR, HTRANS...) when HREADY is high, "
        "because while another slave is stalling, the address on the bus "
        "is not yet accepted. Forgetting this is the number-one AHB slave bug.")

    h2("The pipeline: address phase and data phase")
    p("Every AHB transfer has an **address phase** (one cycle, or longer if "
      "the previous transfer is stalled) and a **data phase** (one cycle "
      "plus wait states). The data phase of transfer N overlaps the "
      "address phase of transfer N+1:")
    diagram(_wave([
        ("", "txt", ["T1", "T2", "T3", "T4", "T5", "T6"]),
        ("HCLK", "clk", 6),
        ("HADDR", "bus", ["A", "B", "C", "C", "", ""]),
        ("HTRANS", "bus", ["NSEQ", "NSEQ", "NSEQ", "NSEQ", "IDLE", "IDLE"]),
        ("HWRITE", "bit", "100000"),
        ("HWDATA", "bus", ["", "D(A)", "", "", "", ""]),
        ("HRDATA", "bus", ["", "", "", "D(B)", "D(C)", ""]),
        ("HREADY", "bit", "111011"),
        ("phase", "txt", ["A:addr", "A:data", "B:wait", "B:data", "C:data", ""]),
    ], W=8), "Three transfers: write A, read B (one wait state), read C. The "
        "address phase of C is extended in T3 because the data phase of B "
        "is stalled (HREADY low); the master must hold HADDR/HTRANS until "
        "HREADY is high.")
    p("Rules that follow from the pipeline:")
    bul(["The slave captures the address/control into registers at the end "
         "of the address phase (HSEL & HREADY & HTRANS[1]) and uses the "
         "**registered** copy during the data phase.",
         "Write data arrives one cycle after its address, so a write to "
         "an SRAM cannot happen in the address phase; read data, in "
         "contrast, can be fetched from a synchronous SRAM by presenting "
         "the address in the address phase so that data is ready in the "
         "data phase with zero wait states.",
         "When the slave inserts wait states (HREADYOUT low), the master "
         "holds the **next** address stable. The spec allows only a few "
         "HTRANS changes during waits (for example IDLE to NONSEQ, or "
         "BUSY to SEQ); an address, once presented with NONSEQ or SEQ, must "
         "be held until accepted.",
         "Peak throughput is **one beat per cycle**, twice APB's best case."])

    h2("Transfer types: HTRANS")
    tbl(["HTRANS", "Name", "Meaning", "Slave response"],
        [["00", "IDLE", "No transfer. Used when the master has nothing to do, "
          "and after a locked sequence", "OKAY, zero wait states"],
         ["01", "BUSY", "Inside a burst: the master needs a cycle (for example, "
          "its data is not ready) but the burst continues. HADDR shows the "
          "next address of the burst", "OKAY, zero wait; ignore the transfer"],
         ["10", "NONSEQ", "First beat of a burst, or a single transfer; address "
          "unrelated to the previous one", "Normal transfer"],
         ["11", "SEQ", "Remaining beats of a burst; address = previous + "
          "size (wrapped for WRAPx)", "Normal transfer"]],
        widths=[10, 12, 50, 28], bold_first=True)
    p("A useful mental model: HTRANS[1] means **there is a real transfer**, "
      "HTRANS[0] means **this continues a burst**. A slave that never needs "
      "burst information can decode only HTRANS[1], exactly as the SRAM "
      "slave below does.")

    h2("Bursts, wrapping and the 1KB boundary")
    p("HBURST tells the slave how many beats follow and how the address "
      "advances. Fixed-length bursts (INCR4/8/16, WRAP4/8/16) allow a "
      "memory controller to prefetch; INCR is an undefined-length burst "
      "that ends when the master issues NONSEQ or IDLE.")
    tbl(["HBURST", "Type", "Beats", "Address sequence (word size, start 0x38)"],
        [["000", "SINGLE", "1", "0x38"],
         ["001", "INCR", "any", "0x38, 0x3C, 0x40, ... until NONSEQ/IDLE"],
         ["010", "WRAP4", "4", "0x38, 0x3C, **0x30**, 0x34 (wraps at 16 bytes)"],
         ["011", "INCR4", "4", "0x38, 0x3C, 0x40, 0x44"],
         ["100", "WRAP8", "8", "0x38, 0x3C, **0x20**, 0x24, 0x28, 0x2C, 0x30, 0x34"],
         ["101", "INCR8", "8", "0x38 ... 0x54"],
         ["110 / 111", "WRAP16 / INCR16", "16", "wrap at 64 bytes / linear"]],
        widths=[12, 18, 8, 62], bold_first=True)
    p("Wrapping bursts exist for **cache line fills**: the CPU asks first for "
      "the word it missed on (the critical word) and the burst wraps around "
      "the line boundary to fetch the rest. The wrap boundary is "
      "beats x bytes-per-beat, which for WRAP4 of words is 16 bytes.")
    box("warn", "PITFALL: the 1KB boundary",
        "An AHB burst must **never cross a 1KB address boundary**. Slaves are "
        "decoded on at least 1KB granularity, so crossing would silently move "
        "the middle of a burst into a different slave that never saw the "
        "NONSEQ. Masters must split INCR bursts at 1KB (DMA engines "
        "forget this, typically when the transfer length is not a multiple "
        "of the burst size). Compare with AXI's 4KB rule in Chapter 7.")
    p("Bursts can be **terminated early**. In multi-master AMBA 2 AHB a "
      "master that lost the bus stopped mid-burst; in AHB-Lite the master "
      "may abandon a burst after an ERROR response; in a multi-layer "
      "system a burst can be broken by the interconnect. Slaves therefore "
      "must never rely on seeing all the SEQ beats promised by HBURST; "
      "they may use HBURST only as a prefetch hint.")

    h2("Wait states and the two-cycle error response")
    p("A slave extends the data phase by driving HREADYOUT low. There is no "
      "protocol limit, but the specification recommends that slaves do "
      "not insert more than about 16 wait states so that the bus cannot be "
      "blocked for long; slow slaves should instead be moved behind a "
      "bridge or use a split/retry strategy (AMBA 2).")
    p("An **ERROR** response always takes **two cycles**:")
    diagram(_wave([
        ("", "txt", ["T1", "T2", "T3", "T4", "T5"]),
        ("HCLK", "clk", 5),
        ("HADDR", "bus", ["A", "B", "B", "", ""]),
        ("HTRANS", "bus", ["NSEQ", "NSEQ", "IDLE", "IDLE", "IDLE"]),
        ("HREADY", "bit", "10111"),
        ("HRESP", "bit", "01100"),
        ("phase", "txt", ["A:addr", "A:ERR1", "A:ERR2", "", ""]),
    ], W=8), "Two-cycle ERROR: cycle 1 has HRESP = 1 with HREADY = 0, "
        "cycle 2 has HRESP = 1 with HREADY = 1. The master used cycle 1 to "
        "cancel the pipelined transfer B by changing HTRANS to IDLE.")
    p("Why two cycles? Because of the pipeline: when the error for A is "
      "signalled, the address of the next transfer B is already on the "
      "bus. The first cycle (HREADY low) holds B off and gives the master "
      "time to decide whether to **cancel** it (drive IDLE) or continue. "
      "Without that extra cycle B would already be accepted by the time "
      "the master saw the error. The master is allowed, but not required, "
      "to cancel the rest of a burst after an ERROR.")
    box("tip", "The default slave",
        "Every AHB decoder needs a **default slave** that is selected for "
        "unmapped addresses. It answers IDLE/BUSY with a zero-wait OKAY and "
        "NONSEQ/SEQ with the two-cycle ERROR. Without it an access to a "
        "hole in the memory map selects nothing, HREADY is undefined and "
        "the system hangs.")

    h2("Multiple masters: arbitration, multi-layer AHB and HMASTLOCK")
    h3("AMBA 2 AHB: shared bus with an arbiter")
    p("In the original AHB, several masters shared one set of address/data "
      "wires. Each master raised HBUSREQx, the arbiter chose one by "
      "priority and raised HGRANTx; the granted master took ownership of "
      "the address bus when HREADY was high, and one cycle later of the "
      "data bus. HMASTER told split-capable slaves which master was on the "
      "bus. A slow slave could answer **SPLIT** (the arbiter masks that "
      "master until the slave raises its HSPLITx bit) or **RETRY** (the "
      "master tries again), freeing the bus for others. The protocol "
      "worked, but only one transfer could be in flight in the whole "
      "system, and verifying SPLIT/RETRY corner cases was notoriously hard.")
    h3("Multi-layer AHB (AHB-Lite interconnect matrix)")
    p("AHB-Lite removed arbitration from the protocol. Each master gets its "
      "own **layer**, i.e. its own AHB-Lite bus. An **interconnect matrix** "
      "sits between masters and slaves and contains, per slave port, an "
      "arbiter and a multiplexer, and per master port, an input stage that "
      "can hold (buffer) one address phase while the target slave is busy "
      "with another master:")
    diagram([
        "   CPU (layer 0)  ----+                          +---> SRAM0",
        "                      |   +------------------+   |",
        "   DMA (layer 1)  ----+-->| input stages     |---+---> SRAM1",
        "                      |   | + per-slave      |   |",
        "   Debug (layer 2)----+   |   arbiter & mux  |   +---> AHB-to-APB bridge",
        "                          +------------------+   |",
        "                                                 +---> Flash controller",
    ], "Multi-layer AHB: masters talk to different slaves in parallel; only "
       "masters that want the same slave in the same cycle are arbitrated.")
    p("From the master's point of view, losing arbitration just looks like "
      "wait states (the input stage holds HREADY low). CPU instruction "
      "fetches from flash and DMA transfers to SRAM therefore proceed "
      "simultaneously, which is why Cortex-M based MCUs call this a "
      "**bus matrix**. Arbitration is usually fixed priority or round-robin "
      "per slave port, and the matrix is generated by a configuration tool.")
    h3("Locked transfers: HMASTLOCK")
    p("HMASTLOCK marks a sequence (typically a read-modify-write for a "
      "semaphore, as produced by an older CPU's SWP instruction) that must "
      "be **indivisible**. In a multi-layer interconnect, once a master "
      "starts a locked sequence to a slave, the arbiter for that slave "
      "must not grant any other master until the lock is released. The "
      "specification recommends that a master insert an IDLE transfer "
      "after a locked sequence so the interconnect can release the lock "
      "cleanly. Modern systems replace locking with **exclusive access** "
      "(AHB5 HEXCL, AXI exclusives, Chapter 7), which does not block "
      "other masters.")

    h2("The AHB-to-APB bridge")
    p("The bridge is an AHB-Lite slave and the single APB requester "
      "(Chapter 5). Its FSM is a good exercise in pipeline thinking:")
    diagram([
        "  AHB   : | addr A (read) | data A ........................|",
        "  bridge:       capture A  -> APB SETUP -> APB ACCESS (PREADY)",
        "  HREADYOUT:  1            |     0     |      0   ->  1       |",
        "",
        "  AHB   : | addr B (write) | data B (HWDATA valid) ..................|",
        "  bridge:       capture B   -> wait for HWDATA -> SETUP -> ACCESS",
        "  HREADYOUT:  1             |       0          |   0   |  0 -> 1     |",
    ], "Read: APB SETUP can start right after the address phase. Write: "
       "PWDATA only exists in the AHB data phase, so SETUP starts one cycle "
       "later (unless the bridge posts the write).")
    bul(["HSIZE and HADDR[1:0] become PSTRB for APB4 completers; HPROT[1] and "
         "HNONSEC map to PPROT[0] and PPROT[1]. HPROT[0] = 0 (opcode fetch) "
         "maps to PPROT[2] = 1 (instruction).",
         "PSLVERR becomes the two-cycle HRESP ERROR.",
         "Bursts are split into single APB transfers; HTRANS = BUSY cycles "
         "are answered OKAY and ignored.",
         "If PCLK is HCLK divided by N, the bridge advances its APB FSM only "
         "on the PCLK enable, and the AHB wait-state count scales with N."])

    h2("Hands-on: AHB-Lite SRAM slave with wait states and ERROR")
    p("The slave below is a behavioural 1KB SRAM with the features that "
      "matter for protocol learning: it samples the address phase only "
      "when HREADY is high, supports byte and halfword writes from HSIZE "
      "and HADDR[1:0], inserts a per-transfer number of wait states (a "
      "demo input `ws`, standing in for, say, a flash or a slow memory), "
      "and answers out-of-range addresses with the two-cycle ERROR. A real "
      "SRAM slave would present the read address to a synchronous macro "
      "in the address phase; here an array read keeps the focus on the "
      "protocol.")
    _v("ahb", "ahb_sram: AHB-Lite slave with a registered address phase, "
              "wait-state counter, byte lanes and two-cycle ERROR.")
    p("The testbench is a **pipelined** master: a list of transfers is "
      "walked by a clocked process that, whenever HREADY is high, moves "
      "the current address-phase transfer into the data phase (driving its "
      "HWDATA) and drives the next address. This is the minimum correct "
      "structure for any AHB master model.")
    _v("ahb_tb", "Testbench: pipelined AHB-Lite master replaying a transfer "
                 "list (single write, INCR4 write, INCR4 read with BUSY, "
                 "byte write, error).")
    _o("ahb", "Real Icarus Verilog output. Each line is one HCLK cycle: "
              "address-phase signals on the left, data-phase signals on "
              "the right, and read data printed when a read data phase "
              "completes.")
    p("What to look for in the trace:")
    bul(["**Pipelining** (cycles 2-7): the address of each INCR4 beat is on "
         "HADDR while the previous beat's data is on HWDATA, e.g. in cycle 4 "
         "the SEQ address 0x014 appears with data 0xA0A0A0A0 of beat 0x010.",
         "**Wait states** (cycles 8-14): the read burst was issued with one "
         "wait state per beat. HREADY goes low every other cycle and the "
         "master holds the next address (SEQ 0x014 appears twice).",
         "**BUSY** (cycles 10-11): the master inserted a BUSY in the middle "
         "of the read burst. It carries the next address (0x018) but no "
         "transfer; in cycle 12 the SEQ 0x018 follows with zero waits for "
         "the BUSY 'data phase'.",
         "**Byte write** (cycles 15-17): HSIZE = 0 at address 0x001 writes lane "
         "1 only (HWDATA = 0x00005500), and the read of 0x000 in cycle 18 "
         "returns 0xDEAD55EF: the other three bytes are untouched.",
         "**ERROR** (cycles 18-20): 0x800 is outside the 1KB SRAM. The data "
         "phase shows HRESP = ERR with HREADY = 0, then ERR with HREADY = 1, "
         "exactly the two-cycle response."])
    box("warn", "PITFALL: sampling the address when HREADY is low",
        "If `ahb_sram` captured the address phase with `if (hsel)` instead "
        "of `if (hready)`, then during the wait states of cycle 8 it would "
        "re-capture SEQ 0x014 every cycle and restart its wait counter "
        "forever, or, in a multi-slave system, capture an address that "
        "belongs to a transfer still waiting for a different slave. "
        "Every AHB slave must qualify its address register with HREADY.")
    box("warn", "PITFALL: read-after-write hazards in zero-wait SRAM slaves",
        "A zero-wait SRAM slave presents read addresses to the macro in "
        "the address phase but can only write in the data phase. A write "
        "to X immediately followed by a read of X therefore reads the macro "
        "before the write lands. Real designs keep a one-entry **write "
        "buffer** and forward its data on an address match, or insert one "
        "wait state on the conflicting read. Directed tests for "
        "write-then-read to the same address catch this; random tests "
        "rarely do.")

    h2("Verification and integration notes")
    bul(["**Protocol assertions**: address/control stable while HREADY is "
         "low (except the permitted HTRANS changes); SEQ addresses follow "
         "the burst rules; no 1KB crossing; HRESP two-cycle shape; BUSY "
         "only inside bursts; slaves answer IDLE/BUSY with zero-wait OKAY.",
         "**Coverage**: all HBURST x HSIZE combinations the IP supports, "
         "BUSY inside bursts, wait states on the first and last beat, "
         "early burst termination, back-to-back reads and writes to the "
         "same address.",
         "**Endianness**: AHB is little-endian in practice; big-endian "
         "legacy systems used BE-32 or BE-8 byte-lane mapping, which the "
         "AHB5 spec lists as an interface property. Check the lane mapping "
         "of every bridge.",
         "**Timing**: HREADY is a global, combinational signal that "
         "returns from the selected slave to all slaves and the master; on "
         "a large multi-slave bus it is often the critical path. Keep "
         "HREADYOUT registered in slaves and limit the number of slaves "
         "per layer."])
    tbl(["Team", "AHB responsibilities"],
        [["RTL", "Slave pipeline registers, HREADY qualification, wait-state "
          "and error logic, bus matrix configuration"],
         ["DV", "AHB VIP (master, slave, monitor), protocol assertions, burst "
          "and error coverage, multi-master contention tests"],
         ["PD/STA", "HREADY and HRDATA mux paths, fan-out of HADDR/HWDATA"],
         ["Firmware", "Memory map, handling of bus faults, exclusive/lock usage"]],
        widths=[16, 84], bold_first=True)

    h2("Summary")
    bul(["AHB pipelines the address phase of one transfer with the data "
         "phase of the previous one, reaching one beat per cycle.",
         "AHB-Lite is single-master with 1-bit HRESP; multiple masters use a "
         "multi-layer bus matrix; AHB5 adds security (HNONSEC), exclusives "
         "and extended memory attributes.",
         "HTRANS (IDLE/BUSY/NONSEQ/SEQ), HBURST (SINGLE, INCR, INCRx, WRAPx) "
         "and HSIZE describe every transfer; bursts must not cross 1KB.",
         "Slaves stall with HREADYOUT low, must sample address phases only "
         "when HREADY is high, and signal ERROR over two cycles so the "
         "master can cancel the pipelined next transfer.",
         "The verified SRAM slave showed pipelined bursts, BUSY, wait states, "
         "byte writes and the two-cycle ERROR."])

    h2("Exercises")
    bul(["Draw the timing diagram of a WRAP4 read of words starting at "
         "0x2C with one wait state on the second beat. List the addresses "
         "and the cycle in which each HRDATA is sampled.",
         "Extend `ahb_sram` with a one-entry write buffer so that reads can "
         "be served with zero wait states from a synchronous SRAM model, "
         "and write a test that proves the read-after-write hazard is "
         "handled.",
         "A DMA engine must copy 3000 bytes starting at address 0x0000_03F0 "
         "using INCR16 bursts of words. How many bursts, of what types, does "
         "it issue so that no burst crosses 1KB?",
         "Why is the ERROR response two cycles long but the OKAY response "
         "only one? What would break if ERROR were a single cycle?",
         "Sketch the input stage of a multi-layer AHB interconnect: what must "
         "it store, and what does it drive on HREADYOUT toward its master "
         "when the target slave is busy with another layer?",
         "Compute the maximum sustained bandwidth of a 32-bit AHB-Lite bus "
         "at 150 MHz reading from a flash that needs 3 wait states per "
         "NONSEQ and 0 per SEQ, using INCR8 bursts."])


# ---------------------------------------------------------------- Ch 7 ----
def _ch7():
    chapter("AMBA AXI4 in Depth")
    p("AXI (Advanced eXtensible Interface) is the protocol of the SoC "
      "backbone. CPU clusters, GPUs, NPUs, DMA engines, PCIe and USB "
      "controllers, display engines and DDR controllers all speak AXI or "
      "one of its descendants, and every major interconnect (Arm CoreLink "
      "NIC/NI, Arteris FlexNoC, Synopsys DesignWare, Xilinx SmartConnect) "
      "is built around it. AXI replaces AHB's single shared pipeline with "
      "**five independent channels**, each with its own VALID/READY "
      "handshake, and adds **transaction IDs** so that many transactions "
      "can be in flight and complete out of order. That is what lets a "
      "single AXI port keep a DDR controller with 100+ ns latency busy.")
    p("This chapter is deliberately thorough, because AXI is the protocol "
      "you will debug most often: channels and every signal, the handshake "
      "dependency rules, burst address arithmetic (verified against a "
      "Python model), the 4KB rule, narrow and unaligned transfers, "
      "ordering and IDs, exclusive access, memory types, responses, the "
      "differences between AXI3, AXI4 and AXI5, interconnect components "
      "and performance math. It ends with an AXI4 memory slave that "
      "handles FIXED, INCR and WRAP bursts under a randomized testbench.")

    h2("Five channels")
    diagram([
        "        MANAGER (master)                              SUBORDINATE (slave)",
        "   +----------------------+   AW: write address   +----------------------+",
        "   |                      |---------------------->|                      |",
        "   |                      |   W : write data      |                      |",
        "   |                      |---------------------->|                      |",
        "   |                      |   B : write response  |                      |",
        "   |                      |<----------------------|                      |",
        "   |                      |   AR: read address    |                      |",
        "   |                      |---------------------->|                      |",
        "   |                      |   R : read data+resp  |                      |",
        "   |                      |<----------------------|                      |",
        "   +----------------------+                       +----------------------+",
        "   Every channel: xVALID from the source, xREADY from the destination,",
        "   and the payload is transferred on each rising edge where both are high.",
    ], "The five AXI channels. Writes use AW, W and B; reads use AR and R. "
       "The channels are independent: no channel shares wires with another.")
    p("A write is one AW transfer, one or more W transfers (the beats, the "
      "last marked WLAST) and one B transfer. A read is one AR transfer "
      "and one or more R transfers (the last marked RLAST), each R beat "
      "carrying its own response. Because the address and data of a write "
      "travel on different channels, write data may even arrive **before** "
      "its address.")

    h2("Signal reference")
    tbl(["Channel", "Signals (AXI4)", "Notes"],
        [["**AW**", "AWID, AWADDR, AWLEN[7:0], AWSIZE[2:0], AWBURST[1:0], "
          "AWLOCK, AWCACHE[3:0], AWPROT[2:0], AWQOS[3:0], AWREGION[3:0], "
          "AWUSER, AWVALID, AWREADY",
          "One transfer per write burst"],
         ["**W**", "WDATA, WSTRB, WLAST, WUSER, WVALID, WREADY",
          "No WID in AXI4: write data must be in AW order"],
         ["**B**", "BID, BRESP[1:0], BUSER, BVALID, BREADY",
          "One response per burst, after the last beat"],
         ["**AR**", "ARID, ARADDR, ARLEN, ARSIZE, ARBURST, ARLOCK, ARCACHE, "
          "ARPROT, ARQOS, ARREGION, ARUSER, ARVALID, ARREADY",
          "One transfer per read burst"],
         ["**R**", "RID, RDATA, RRESP[1:0], RLAST, RUSER, RVALID, RREADY",
          "One response per beat"],
         ["global", "ACLK, ARESETn", "All signals sampled on ACLK rising edge; "
          "VALIDs low during reset"]],
        widths=[10, 56, 34], bold_first=True)
    tbl(["Field", "Encoding"],
        [["AxLEN", "Beats - 1: 0..255 for INCR (1-256 beats); FIXED max 16 beats; "
          "WRAP 2, 4, 8 or 16 beats"],
         ["AxSIZE", "Bytes per beat = 2^AxSIZE (1 to 128 bytes); must not exceed "
          "the data bus width"],
         ["AxBURST", "00 FIXED, 01 INCR, 10 WRAP, 11 reserved"],
         ["AxLOCK", "AXI4: 0 normal, 1 exclusive (AXI3 had 2 bits incl. locked)"],
         ["AxCACHE", "[0] Bufferable, [1] Modifiable, [2]/[3] allocate hints "
          "(Section 7.9)"],
         ["AxPROT", "[0] privileged, [1] non-secure, [2] instruction"],
         ["AxQOS", "4-bit priority hint; higher value = more important "
          "(by convention)"],
         ["AxREGION", "Up to 16 address regions for one physical interface, "
          "so a slave can avoid its own decoder"],
         ["xRESP", "00 OKAY, 01 EXOKAY, 10 SLVERR, 11 DECERR"],
         ["WSTRB", "One bit per byte lane of WDATA; 1 = lane holds valid data"]],
        widths=[16, 84], bold_first=True)

    h2("The handshake and its dependency rules")
    p("Every channel uses the same two-wire handshake (Chapter 3): the "
      "source asserts **VALID** when payload is available, the destination "
      "asserts **READY** when it can accept, and the transfer happens on "
      "the rising edge where both are high. Three orderings are legal:")
    diagram(_wave([
        ("", "txt", ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9"]),
        ("ACLK", "clk", 9),
        ("VALID", "bit", "011001001"),
        ("READY", "bit", "001011001"),
        ("PAYLOAD", "bus", ["", "P1", "P1", "", "", "P2", "", "", "P3"]),
        ("xfer", "txt", ["", "", "^P1", "", "", "^P2", "", "", "^P3"]),
    ], W=7), "P1: VALID before READY (source waits, payload held). P2: READY "
        "before VALID (destination waiting, transfer as soon as VALID "
        "rises). P3: both in the same cycle. The transfer happens at the "
        "end of the cycle marked ^.")
    box("key", "The two rules that prevent deadlock",
        ["**1. A source must not wait for READY before asserting VALID.** "
         "(Otherwise two blocks that each wait for the other deadlock.)",
         "**2. Once VALID is asserted it must stay asserted, with stable "
         "payload, until the handshake completes.** READY, in contrast, may "
         "be asserted and deasserted freely before VALID arrives, and a "
         "destination **may** wait for VALID before asserting READY."])
    p("On top of the per-channel rule, the specification defines "
      "**dependencies between channels**. The spec draws them as arrows; "
      "the ASCII version below uses a single arrow for 'must wait for' and "
      "a double arrow for 'must wait for both':")
    diagram([
        "  READ TRANSACTION",
        "    ARVALID --+                       (slave may wait for ARVALID before ARREADY)",
        "    ARREADY --+==> RVALID             RVALID only after the AR handshake",
        "                   RREADY             (master may wait for RVALID before RREADY)",
        "",
        "  WRITE TRANSACTION (AXI4)",
        "    AWVALID    WVALID                 master must NOT wait for AWREADY or",
        "                                      WREADY before asserting AWVALID/WVALID",
        "    AWREADY    WREADY                 slave MAY wait for AWVALID and/or WVALID",
        "                                      before asserting AWREADY or WREADY",
        "    AWVALID --+",
        "    AWREADY --+",
        "    WVALID  --+==> BVALID             BVALID only after the AW handshake AND",
        "    WREADY  --+                       the handshake of the LAST W beat (WLAST)",
        "                   BREADY             (master may wait for BVALID before BREADY)",
    ], "Channel dependencies. The AW handshake as a condition for BVALID was "
       "added in AXI4; AXI3 required only the last W beat.")
    box("warn", "PITFALL: the classic AXI deadlocks",
        ["A master that waits for AWREADY before driving WVALID, attached to "
         "a slave that waits for WVALID before driving AWREADY: legal for the "
         "slave, illegal for the master; the system hangs on the first write.",
         "A slave (or interconnect) that combinationally makes READY depend "
         "on VALID and a master that makes VALID depend on READY: a "
         "combinational loop, not just a deadlock.",
         "A bridge that accepts AW for write A, then waits for W of write B "
         "because it arbitrates channels independently: W data must follow "
         "AW order, and the bridge must never reorder them."])
    p("A practical consequence: an AXI slave must be able to accept W beats "
      "that arrive before their AW (or apply backpressure with WREADY low "
      "until AW arrives, which is what the example slave in Section 7.14 "
      "does), and a master must be ready to present all W beats "
      "regardless of when AWREADY rises.")

    h2("Burst types and address calculation")
    p("AXI bursts come in three flavours, set by AxBURST:")
    bul(["**FIXED**: every beat uses the same address. Used for FIFOs and "
         "peripheral data registers (a UART TX register written 16 times).",
         "**INCR**: the address increments by the transfer size each beat. "
         "The normal type for memory.",
         "**WRAP**: incrementing, but wrapping at an aligned boundary of "
         "(beats x size) bytes. Used for critical-word-first cache line "
         "fills. Start address must be aligned to AxSIZE and the length must "
         "be 2, 4, 8 or 16."])
    p("The specification gives the address of every beat with a small set "
      "of formulas. With beats numbered N = 1, 2, ... and "
      "Data_Bus_Bytes the width of the data bus in bytes:")
    eq(["Number_Bytes    = 2 ^ AxSIZE",
        "Burst_Length    = AxLEN + 1",
        "Aligned_Address = INT(Start_Address / Number_Bytes) x Number_Bytes",
        "Address_1       = Start_Address                          (first beat)",
        "Address_N       = Aligned_Address + (N - 1) x Number_Bytes   (INCR, N >= 2)",
        "Wrap_Boundary   = INT(Start_Address / (Number_Bytes x Burst_Length))",
        "                  x (Number_Bytes x Burst_Length)",
        "WRAP: if Address_N = Wrap_Boundary + Number_Bytes x Burst_Length",
        "      then Address_N = Wrap_Boundary, and subsequent beats continue from it",
        "Lower_Byte_Lane = Address_N - INT(Address_N / Data_Bus_Bytes) x Data_Bus_Bytes",
        "Upper_Byte_Lane = Lower_Byte_Lane + Number_Bytes - 1       (aligned beats)",
        "first beat:       Aligned_Address + Number_Bytes - 1",
        "                  - INT(Start_Address / Data_Bus_Bytes) x Data_Bus_Bytes"],
       "AXI beat address and byte-lane equations (paraphrased from the AXI "
       "specification). FIXED bursts repeat Address_1 and its lanes.")
    p("A worked example: a WRAP4 burst of 4-byte beats starting at 0x38. "
      "Number_Bytes = 4, Burst_Length = 4, so the wrap container is 16 bytes "
      "and Wrap_Boundary = 0x30. The addresses are 0x38, 0x3C, then 0x40 = "
      "0x30 + 16 wraps to **0x30**, then 0x34. The critical word 0x38 comes "
      "first, and the whole 16-byte line 0x30-0x3F is fetched.")
    h3("Verified: a burst-address generator against a Python model")
    p("The combinational module below computes, for beat n of a burst, "
      "the beat address, the active byte lanes on a 64-bit bus and a flag "
      "for an illegal 4KB crossing. Note how simple the hardware form of "
      "WRAP is: since the container is a power of two, the wrapped address "
      "is the boundary OR'ed with the low bits of the linear address.")
    _v("axiaddr", "axi_addr_gen: beat address, byte lanes and 4KB check. "
                  "The same module is reused inside the AXI slave of "
                  "Section 7.14.")
    p("The testbench sweeps FIXED, INCR and WRAP bursts, all sizes from 1 "
      "to 8 bytes, lengths from 1 to 256 beats and aligned/unaligned start "
      "addresses, writing every beat to a file. The Python model was written "
      "**independently from the specification's pseudo-code** (beat "
      "numbering from 1, the explicit 'wrap when Address_N reaches the "
      "boundary' test and the separate first-beat lane formula) and "
      "compares every line.")
    _v("axiaddr_tb", "Sweep testbench and three worked examples.")
    _v("axiaddr_py", "Independent Python reference model that checks the "
                     "RTL output file.")
    _o("axiaddr", "Icarus Verilog output: worked examples as address/lanes "
                  "(lane 0 is the rightmost bit).")
    _o("axiaddr_py", "Python cross-check of all 11136 beats: zero mismatches.")
    p("The worked examples read as follows. WRAP4 at 0x38 on a 64-bit bus "
      "gives 38, 3C, 30, 34, alternating between the lower and upper word "
      "lanes. The unaligned INCR4 at 0x3E with 4-byte beats has a first beat "
      "that only uses lanes 6 and 7 (bytes 0x3E-0x3F): the rest of that "
      "4-byte container, 0x3C-0x3D, lies before the start address. "
      "Subsequent beats are aligned. The INCR16 of 8-byte beats at 0xFF8 "
      "would cover 0xFF8-0x1077, crossing 0x1000, so it is flagged.")

    h2("The 4KB boundary rule")
    p("**A burst must not cross a 4KB address boundary.** The reason is the "
      "same as AHB's 1KB rule, scaled up: the smallest region an "
      "interconnect decodes to a slave, and the smallest MMU page, is 4KB. "
      "A burst that crossed a boundary could start in one slave and end in "
      "another, or straddle two pages with different physical mappings. "
      "Because of the rule, an interconnect can route an entire burst "
      "using only its first address.")
    bul(["For INCR the check is: page(Start_Address) == page(Aligned_Address "
         "+ AxLEN x Number_Bytes). With 256 beats x 16 bytes = 4096 bytes, "
         "only a perfectly 4KB-aligned maximal burst fits.",
         "WRAP bursts never cross, because their container is aligned and "
         "at most 16 x 128 = 2048 bytes.",
         "Masters (DMA engines, bridges from PCIe or USB) must split "
         "transfers at 4KB; a protocol checker should flag violations, and "
         "some interconnects split or reject them."])

    h2("Narrow, unaligned and sparse transfers")
    p("A **narrow transfer** has AxSIZE smaller than the data bus: for "
      "example 2-byte beats on a 64-bit bus. The active lanes then move "
      "from beat to beat (0-1, 2-3, 4-5, 6-7, 0-1, ...), and the master "
      "must put each beat's data on the right lanes and set WSTRB "
      "accordingly. An **unaligned** transfer has a start address that is "
      "not a multiple of AxSIZE; only the first beat is affected, and "
      "WSTRB (writes) or the master's own lane selection (reads) discards "
      "the bytes below the start address. **Sparse** writes simply clear "
      "WSTRB bits anywhere; this is how a master writes a partial word, and "
      "how it 'cancels' the remainder of a burst, since AXI has no early "
      "termination: all AxLEN + 1 beats must always be transferred.")
    box("warn", "PITFALL: WSTRB outside the legal lanes",
        "WSTRB may only be high for lanes inside the beat's legal byte lanes "
        "(the equations above). A slave that blindly writes every lane with "
        "WSTRB = 1 corrupts neighbouring bytes when a buggy master drives "
        "strobes outside the transfer; robust slaves AND WSTRB with the "
        "computed lanes, as `axi4_mem` does.")

    h2("IDs, ordering and outstanding transactions")
    p("Every AW and AR carries an ID (AWID, ARID), echoed on the "
      "corresponding B (BID) and R (RID). The ordering rules are:")
    bul(["Transactions with the **same ID in the same direction** complete "
         "in the order they were issued. Read data for the same ARID "
         "returns in order; write responses for the same AWID return in "
         "order.",
         "Transactions with **different IDs** have no ordering relationship; "
         "the slave or interconnect may complete them in any order.",
         "**Reads and writes are never ordered with respect to each other**, "
         "even with the same ID. A master that must read what it just wrote "
         "waits for the B response first (or relies on a guarantee "
         "documented for a specific slave).",
         "In AXI4 the read data of different IDs may be **interleaved** "
         "beat by beat (RID changes between beats of different bursts); "
         "a slave declares its read data reordering depth.",
         "**Write data interleaving was removed in AXI4**: WID no longer "
         "exists, and W beats must arrive in the same order as their AW "
         "transfers. AXI3 allowed interleaving W beats of different AWIDs, "
         "which almost no slave supported."])
    p("IDs are also how the interconnect routes responses: when a crossbar "
      "merges several masters onto one slave port it **extends** the ID with "
      "the master's port number, and uses those extra bits to steer B and R "
      "back. A slave port behind a 4-master crossbar therefore sees IDs two "
      "bits wider than any master produces, which is why slave IP has a "
      "configurable ID width.")
    box("expert", "Ordering models in practice",
        "Many masters use a single ID (a simple DMA channel) and therefore get "
        "strict in-order completion for free. CPUs use several IDs so that "
        "a slow device read does not block a fast cache refill. The "
        "interconnect must keep the per-ID order even when the two "
        "transactions go to different slaves; the usual solution is to "
        "stall a new transaction whose ID already has outstanding "
        "transactions to a **different** slave (a 'single-slave-per-ID' "
        "rule), because responses from two slaves could otherwise return "
        "out of order.")

    h2("Exclusive access")
    p("Exclusive access implements load-linked/store-conditional "
      "semantics (Arm LDREX/STREX, LDXR/STXR; RISC-V LR/SC maps onto the "
      "same mechanism) without locking the bus:")
    bul(["The master issues an **exclusive read** (AxLOCK = 1). An "
         "**exclusive monitor** at the slave (or in the interconnect) "
         "records the address and the master's ID and returns EXOKAY.",
         "The master computes, then issues an **exclusive write** to the same "
         "address with the same ID, size and length.",
         "If no other master wrote the monitored location in between, the "
         "write happens and returns **EXOKAY**. Otherwise the write is "
         "**not** performed and returns **OKAY**, meaning 'exclusive failed'; "
         "software retries the sequence.",
         "Constraints: the burst must be at most 16 beats, the total size a "
         "power of two up to 128 bytes, and the address aligned to it.",
         "A slave without exclusive support answers the exclusive read with "
         "OKAY (not EXOKAY), telling the master exclusives are not supported "
         "there; its exclusive writes then always update memory and return "
         "OKAY, so software must not rely on them."])
    p("In coherent systems the monitor for cacheable memory lives in the CPU "
      "cluster (the local monitor plus the coherency protocol); the AXI "
      "exclusive monitor matters for non-cacheable shared memory, for "
      "example a mailbox between a CPU and a DSP.")

    h2("Memory attributes: AxCACHE and AxPROT")
    p("AxCACHE tells the interconnect and slaves how a transaction may be "
      "handled. **Bufferable** (bit 0) allows an early write response from "
      "an intermediate point. **Modifiable** (bit 1, called Cacheable in "
      "AXI3) allows the transaction to be split, merged, widened or have "
      "its data prefetched; non-modifiable transactions must reach the "
      "destination exactly as issued, which is what device registers need. "
      "Bits 2 and 3 are allocation hints for caches. The AXI4 memory types "
      "are:")
    tbl(["Memory type", "ARCACHE", "AWCACHE"],
        [["Device Non-bufferable", "0000", "0000"],
         ["Device Bufferable", "0001", "0001"],
         ["Normal Non-cacheable Non-bufferable", "0010", "0010"],
         ["Normal Non-cacheable Bufferable", "0011", "0011"],
         ["Write-through No-allocate", "1010", "0110"],
         ["Write-through Read-allocate", "1110", "0110"],
         ["Write-through Write-allocate", "1010", "1110"],
         ["Write-through Read and Write-allocate", "1110", "1110"],
         ["Write-back No-allocate", "1011", "0111"],
         ["Write-back Read-allocate", "1111", "0111"],
         ["Write-back Write-allocate", "1011", "1111"],
         ["Write-back Read and Write-allocate", "1111", "1111"]],
        widths=[54, 23, 23], bold_first=True,
        caption="AXI4 memory types (AxCACHE encodings from the AXI4 "
                "specification). For reads bit 2 is Allocate and bit 3 Other "
                "Allocate; for writes the roles are swapped.")
    p("AxPROT carries privilege (bit 0), **non-secure** (bit 1) and "
      "instruction (bit 2). TrustZone firewalls (for example a TZC-400 in "
      "front of DDR) check AxPROT[1] against per-region permissions and "
      "respond with an error (or read-as-zero) to violations.")

    h2("Responses")
    tbl(["xRESP", "Name", "Meaning"],
        [["00", "OKAY", "Normal success; or failure of an exclusive access"],
         ["01", "EXOKAY", "Exclusive access succeeded"],
         ["10", "SLVERR", "The slave was reached but reports an error: "
          "unsupported size, FIFO overflow, read-only register, ECC "
          "uncorrectable error, firewall violation"],
         ["11", "DECERR", "Decode error, normally generated by the "
          "interconnect's default slave: no slave at this address"]],
        widths=[10, 14, 76], bold_first=True)
    p("Reads have a response per beat (a burst can mix OKAY and SLVERR), "
      "writes one response for the whole burst. Note that every beat of an "
      "erroring burst must still be transferred: a slave returning SLVERR "
      "on the first read beat still returns all AxLEN + 1 beats with RLAST "
      "on the last.")

    h2("AXI3, AXI4 and AXI5")
    tbl(["Feature", "AXI3 (2003)", "AXI4 (2010)", "AXI5 (AMBA 5)"],
        [["Max INCR burst", "16 beats", "256 beats", "256 beats"],
         ["Write interleaving", "Allowed (WID)", "Removed (no WID)", "Removed"],
         ["AxLOCK", "2 bits (locked + exclusive)", "1 bit (exclusive)", "1 bit"],
         ["QoS / REGION / USER", "No", "Yes", "Yes"],
         ["BVALID dependency", "After last W", "After last W and AW", "Same as AXI4"],
         ["AxCACHE[1]", "Cacheable", "Modifiable", "Modifiable"],
         ["New in AXI5", "-", "-", "Atomic transactions (AWATOP), parity/"
          "check signals, poison, cache stashing, persistent CMOs, "
          "memory tagging (MTE), MPAM, wakeup signals, unique-ID "
          "indication, untranslated transactions, trace and loopback "
          "signals (most optional)"]],
        widths=[20, 22, 22, 36], bold_first=True)
    p("AXI5 features are enabled per interface through **interface "
      "properties** (for example Atomic_Transactions, Poison, "
      "Check_Type), so an 'AXI5' port may be almost identical to AXI4. "
      "Always read the interface property list of an IP, not just its "
      "protocol name. AMBA 5 also contains ACE5 and CHI, covered in "
      "Chapter 9.")

    h2("Interconnect building blocks")
    tbl(["Component", "What it does", "Design notes"],
        [["**Crossbar / switch**", "Connects M masters to S slaves; per-slave "
          "arbitration, per-master decode; extends IDs", "Sparse connectivity "
          "saves area; QoS arbitration uses AxQOS"],
         ["**Default slave**", "Answers unmapped addresses with DECERR",
          "Must still consume all W beats and return all R beats"],
         ["**Width converter** (upsizer/downsizer)", "Changes data width; "
          "splits or packs beats, rewrites AxLEN/AxSIZE and WSTRB",
          "Downsizing a 256-beat burst may need splitting into several "
          "bursts; must respect modifiable bit"],
         ["**Clock converter**", "Crosses clock domains with async FIFOs on "
          "all five channels", "Adds latency of a few cycles of each clock "
          "(Chapter 4)"],
         ["**Register slice**", "Pipeline stage on a channel (full or "
          "skid buffer) to break long paths", "Adds one cycle latency; a "
          "full-throughput slice needs two entries"],
         ["**Protocol converter**", "AXI4 to AXI3/AXI4-Lite/AHB/APB",
          "Splits bursts, serializes, handles ID mapping"],
         ["**Firewall / TZC**", "Security filtering by address and AxPROT",
          "Returns SLVERR or DECERR or RAZ/WI"],
         ["**Exclusive monitor**", "Tracks exclusive reads per ID",
          "Needed in front of non-coherent shared memory"]],
        widths=[22, 42, 36], bold_first=True)

    h2("Performance: bandwidth, latency and outstanding transactions")
    p("The raw bandwidth of one AXI data channel is width x frequency. "
      "A 128-bit bus at 1 GHz moves 16 bytes per cycle, 16 GB/s per "
      "direction; AXI's separate R and W channels mean reads and writes can "
      "each use that simultaneously. Achieved bandwidth is lower because "
      "of three effects:")
    bul(["**Bubbles** between bursts or inside them (VALID or READY low).",
         "**Latency** not covered by enough outstanding transactions.",
         "**Narrow or short bursts**: a 4-byte access on a 16-byte bus uses "
         "25% of the lanes; a single-beat burst pays the full address and "
         "response overhead for one beat."])
    p("The key sizing rule is **Little's law**: to sustain bandwidth BW with "
      "round-trip latency L, the number of bytes in flight must be BW x L, "
      "so the required number of outstanding transactions is:")
    eq(["Outstanding = ceil( Bandwidth x Latency / Bytes_per_transaction )",
        "",
        "Example: 128-bit @ 1 GHz = 16 GB/s, read latency 150 ns, 64-byte bursts",
        "         16e9 B/s x 150e-9 s = 2400 bytes in flight -> 2400 / 64 = 37.5 -> 38",
        "Example: 64-bit @ 800 MHz = 6.4 GB/s, latency 100 ns, 64-byte bursts",
        "         6.4e9 x 100e-9 = 640 bytes -> 10 outstanding transactions"],
       "Outstanding depth = bandwidth-delay product / transaction size.")
    p("This is why a DMA engine with only 4 outstanding reads cannot saturate "
      "DDR no matter how wide its bus, and why every interconnect component "
      "on the path (crossbar, clock converter, width converter) must also "
      "be configured for enough **acceptance capability**. The number of IDs "
      "matters too: if all 38 transactions share one ID, the slave must "
      "return them in order, which prevents a DDR controller from "
      "reordering for page hits.")
    box("tip", "Performance debugging checklist",
        ["Measure per channel: cycles with VALID & READY, VALID & !READY "
         "(slave backpressure) and !VALID (master starvation).",
         "Plot outstanding transactions over time; a flat line at the "
         "configured limit means you are latency-bound.",
         "Check burst length and size distributions: a 'bandwidth problem' "
         "is often a master issuing single-beat or narrow transfers.",
         "Look for write-response stalls: a master that waits for B before "
         "the next AW has an effective outstanding depth of one."])

    h2("Hands-on: an AXI4 memory slave with FIXED, INCR and WRAP bursts")
    p("`axi4_mem` is a 4KB, 32-bit AXI4 memory slave. The write and read "
      "paths are independent state machines, so a read can proceed while a "
      "write is in progress, but each path handles one burst at a time "
      "(no outstanding transactions, the simplest legal choice). Both paths "
      "reuse `axi_addr_gen` for beat addresses and byte lanes. Writes "
      "honour WSTRB AND the legal lanes, check that WLAST arrives exactly on "
      "the last beat (answering SLVERR otherwise) and echo AWID on BID. "
      "Reads echo ARID and generate RLAST.")
    _v("aximem", "axi4_mem: AXI4 slave with independent write/read FSMs, "
                 "burst address generation and WLAST checking.")
    p("Look at the handshake choices: AWREADY is high only in W_ADDR, so the "
      "slave waits for the address before accepting data (WREADY is low "
      "until then). That is allowed: the **slave** may wait for AWVALID "
      "before asserting WREADY; only the **master** may not wait. BVALID "
      "rises after both the AW and the last W handshake, satisfying the "
      "AXI4 dependency.")
    p("The testbench master drives AW and W from two parallel threads "
      "(fork/join) with random gaps on WVALID, applies random backpressure "
      "on RREADY, keeps a byte-accurate shadow memory using its **own** "
      "beat-address function, and checks every byte of every read beat, "
      "RID and RLAST. After nine directed transactions it runs 300 random "
      "bursts of all types, sizes and lengths.")
    _v("aximem_tb", "AXI4 testbench master with shadow memory, random "
                    "backpressure and a random regression.")
    _o("aximem", "Real Icarus Verilog output: directed transactions, then the "
                 "random-regression summary.")
    bul(["**WRAP4 at 0x108** returns 108, 10C, 100, 104: the critical word "
         "first, wrapping inside the 16-byte container 0x100-0x10F that the "
         "INCR4 write filled.",
         "**Narrow writes**: four 2-byte beats starting at 0x202 land in "
         "0x202-0x209; the following read of 0x200 shows the low half-word "
         "of 0x200 untouched (0000) and the next word fully written.",
         "**Unaligned INCR at 0x3F2**: the first beat only writes bytes "
         "0x3F2-0x3F3 (read back as 28b7 in the upper half of 0x3F0); the "
         "burst of 3 beats ends at 0x3FB, so 0x3FC stays zero.",
         "**FIXED** writes 4 beats to 0x300; the last beat's data survives.",
         "**Bad WLAST** (asserted on beat 2 of 4) returns BRESP = SLVERR.",
         "1197 read beats of random traffic matched the shadow memory byte "
         "for byte."])
    box("warn", "PITFALL: RLAST, BID and RID in multi-outstanding slaves",
        "This slave has one burst in flight per direction, so RID and BID "
        "are simply the stored IDs. As soon as a slave accepts several "
        "transactions it must keep a queue of {ID, length} per direction and "
        "must never return responses of the same ID out of order. The two "
        "most common bugs in hand-written AXI slaves are an RLAST that is "
        "off by one on single-beat bursts (AxLEN = 0) and a B response "
        "issued before the AW handshake when W arrives first.")

    h2("Verification and ownership")
    bul(["**Protocol checkers**: Arm provides AXI protocol assertions "
         "(historically the 'AXI protocol checker' SVA); commercial VIP "
         "from Cadence, Synopsys and Siemens include AXI monitors with "
         "hundreds of checks (stability, dependencies, 4KB, WRAP rules, "
         "exclusive rules, ID ordering).",
         "**Scoreboards** must model ordering per ID and handle out-of-order "
         "completion across IDs.",
         "**Performance verification** (latency histograms, bandwidth per "
         "master, QoS behaviour) is a separate activity, often done with "
         "traffic generators on an emulator or FPGA prototype.",
         "**Ownership**: the interconnect team (RTL + configuration) owns "
         "crossbars, converters and QoS; IP teams own their AXI ports; DV "
         "owns VIP integration and system traffic tests; the performance "
         "architecture team owns outstanding-depth and bandwidth budgets; "
         "PD owns register-slice placement on long AXI routes."])

    h2("Summary")
    bul(["AXI has five independent channels (AW, W, B, AR, R), each with a "
         "VALID/READY handshake: VALID must not wait for READY and must hold "
         "until the handshake.",
         "BVALID waits for AW and the last W; RVALID waits for AR. A slave "
         "may wait for VALID before READY, a master may not wait for READY "
         "before VALID.",
         "FIXED, INCR (up to 256 beats) and WRAP (2/4/8/16 beats) bursts "
         "follow exact address and lane equations; bursts never cross 4KB "
         "and cannot be terminated early.",
         "IDs order same-ID transactions per direction; different IDs may "
         "complete out of order; reads and writes are unordered; AXI4 has "
         "no write interleaving.",
         "Exclusives, AxCACHE memory types, AxPROT security and the four "
         "responses complete the protocol; AXI5 adds optional atomics, "
         "parity, poison, MTE and more.",
         "Outstanding transactions = bandwidth x latency / transaction size.",
         "The burst generator matched a Python model on 11136 beats and the "
         "AXI4 slave passed directed and random tests."])

    h2("Exercises")
    bul(["List the addresses and WSTRB values (64-bit bus) of an INCR burst "
         "with AWADDR = 0x1003, AWSIZE = 2, AWLEN = 3. Check your answer with "
         "the Python model.",
         "A master issues AR with ARID = 3 to a slow peripheral, then AR "
         "with ARID = 3 to DDR. What can the interconnect do, and what must "
         "it not do? What changes if the second read uses ARID = 4?",
         "Extend `axi4_mem` to accept up to four outstanding read bursts "
         "(an AR queue) and return them in order. Which testbench checks "
         "prove that ID order is preserved?",
         "A 256-bit AXI port at 1.2 GHz reads DDR with a 120 ns average "
         "latency using 128-byte bursts. How many outstanding reads are "
         "needed for 80% of peak bandwidth?",
         "Explain why a WRAP burst of 16 beats x 128 bytes can never cross "
         "a 4KB boundary, and write an SVA property that checks the 4KB "
         "rule for INCR bursts.",
         "Design (block diagram and FSM) a downsizer from a 128-bit AXI4 "
         "slave port to a 32-bit master port. How are AxLEN, AxSIZE, WSTRB "
         "and RLAST transformed, and what happens to a 256-beat INCR burst?"])


# ---------------------------------------------------------------- Ch 8 ----
def _ch8():
    chapter("AXI4-Lite and AXI4-Stream")
    p("Full AXI4 is powerful but heavy. Two lighter members of the family "
      "cover the two most common special cases. **AXI4-Lite** is AXI4 "
      "stripped to single-beat register accesses: the standard control "
      "interface of IP blocks, especially in FPGA designs, where it plays "
      "the role that APB plays in ASICs. **AXI4-Stream** drops addresses "
      "altogether and becomes a point-to-point, flow-controlled data pipe "
      "with packet framing: the backbone of video, networking, DSP and DMA "
      "data paths. Both reuse AXI's VALID/READY handshake, so everything "
      "you learned in Chapter 7 about the handshake carries over.")

    h2("AXI4-Lite: what is removed")
    tbl(["Aspect", "AXI4", "AXI4-Lite"],
        [["Burst length", "1-256 beats", "Always 1 (no AxLEN, no xLAST)"],
         ["Transfer size", "Any AxSIZE up to the bus width",
          "Always the full bus width (no AxSIZE); partial writes use WSTRB"],
         ["Data width", "8 to 1024 bits", "32 or 64 bits"],
         ["IDs", "AWID/ARID, reordering", "None: all transactions in order "
          "per direction (AXI5-Lite later allows optional IDs)"],
         ["Exclusive access", "AxLOCK, EXOKAY", "Not supported"],
         ["Memory attributes", "AxCACHE, AxQOS, AxREGION", "Not present: "
          "treated as Device Non-bufferable"],
         ["Protection", "AxPROT", "AxPROT (kept, needed for security)"],
         ["Responses", "OKAY, EXOKAY, SLVERR, DECERR", "OKAY, SLVERR, DECERR"]],
        widths=[20, 36, 44], bold_first=True)
    p("The remaining signals are AWADDR, AWPROT, AWVALID, AWREADY; WDATA, "
      "WSTRB, WVALID, WREADY; BRESP, BVALID, BREADY; ARADDR, ARPROT, "
      "ARVALID, ARREADY; RDATA, RRESP, RVALID, RREADY: 19 signals plus "
      "clock and reset. An AXI4-Lite slave can be connected to an AXI4 "
      "master only through a **protocol converter** (or a master known to "
      "issue single-beat, full-width transactions), because the converter "
      "must split bursts and reflect IDs, which the Lite slave does not "
      "return.")
    box("key", "AXI4-Lite versus APB",
        "Both are register buses. APB has a two-cycle minimum per access, "
        "one requester and no pipelining, and is the natural ASIC choice "
        "behind a bridge. AXI4-Lite keeps independent read and write "
        "channels and can overlap transactions, so it can sustain one "
        "access per cycle per direction, but costs more flops per port. "
        "FPGA ecosystems standardize on AXI4-Lite because their "
        "interconnect generators and IP catalogues are AXI-based; ASIC "
        "peripheral subsystems usually stay on APB.")

    h2("Designing an AXI4-Lite register slave")
    p("The address and data of a write arrive on independent channels, in "
      "either order and possibly in different cycles. The slave has three "
      "legal strategies:")
    bul(["**Wait for both.** Keep AWREADY and WREADY low until AWVALID and "
         "WVALID are both high, then raise both READYs for one cycle. "
         "Simple and legal (a slave may wait for VALID before READY), at the "
         "cost of one extra cycle of latency.",
         "**Capture independently.** Accept AW into an address register and W "
         "into a data register whenever each arrives, then perform the write "
         "when both registers are full. Higher throughput, more flops.",
         "**Skid buffers on every channel.** The high-performance version: "
         "READY is registered and never depends combinationally on VALID, "
         "at the cost of two-entry buffers per channel."])
    p("After the write, BVALID must be raised and **held until BREADY**. "
      "While a B response is pending the slave must not accept another "
      "write unless it can queue its response. The read side is the same "
      "pattern: accept AR, raise RVALID with RDATA/RRESP, hold both until "
      "RREADY, and only then accept the next AR (or buffer).")
    code([
        "// Write path core of a 'capture independently' AXI4-Lite slave",
        "assign awready = !aw_full && !bvalid;     // no new write while B is pending",
        "assign wready  = !w_full  && !bvalid;",
        "always_ff @(posedge aclk) if (!aresetn) begin",
        "  aw_full <= 0; w_full <= 0; bvalid <= 0;",
        "end else begin",
        "  if (awvalid && awready) begin aw_full <= 1; aw_q <= awaddr; end",
        "  if (wvalid  && wready)  begin w_full  <= 1; w_q <= wdata; s_q <= wstrb; end",
        "  if (aw_full && w_full && !bvalid) begin  // both halves present: do it",
        "    reg_write(aw_q, w_q, s_q);            // honour WSTRB byte lanes",
        "    bresp  <= decode_ok(aw_q) ? 2'b00 : 2'b10;",
        "    bvalid <= 1; aw_full <= 0; w_full <= 0;",
        "  end",
        "  if (bvalid && bready) bvalid <= 0;      // hold B until accepted",
        "end",
    ], "Structure of a robust AXI4-Lite write path (fragment). The companion "
       "RTL Design guide contains a complete, simulated AXI4-Lite register "
       "block.")
    box("warn", "PITFALL: the most common AXI4-Lite slave bugs",
        ["**Dropping BVALID or RVALID** before the READY handshake because "
         "the slave assumes the master is always ready. Many masters "
         "(and all good VIP) apply backpressure.",
         "**Accepting a new AR while RVALID is stalled** and overwriting "
         "RDATA, or accepting a new write while BVALID is stalled and "
         "losing a response. Several widely copied vendor templates were "
         "shown (by formal verification, notably in public write-ups from "
         "the open-source community) to fail exactly this way under "
         "backpressure.",
         "**Requiring AWVALID and WVALID in the same cycle**, which only "
         "works with masters that happen to drive them together.",
         "**Ignoring WSTRB**, so that a byte store from the CPU clobbers "
         "the other three bytes of the register.",
         "**Decoding the full address including AWADDR[1:0]** or the upper "
         "bits, so that an aliasing or unaligned address hits nothing.",
         "**Read side effects on the AR handshake executed twice** "
         "(clear-on-read, FIFO pop) when the design re-evaluates the read "
         "while RVALID is stalled."])
    p("Formal verification is exceptionally effective here: a property set "
      "of about twenty assertions (stability, response counting, no "
      "response without request) proves an AXI4-Lite slave correct for all "
      "backpressure patterns in minutes. SymbiYosys with an open AXI-Lite "
      "property file, or a commercial formal tool with AXI assertion IP, "
      "should be part of every register-block sign-off (Chapter 25).")

    h2("AXI4-Stream: signals")
    p("An AXI4-Stream interface has one direction: a **transmitter** "
      "(master) sends transfers to a **receiver** (slave). There are no "
      "addresses, responses or IDs in the AXI sense; TID and TDEST are "
      "routing fields.")
    tbl(["Signal", "Width", "Meaning"],
        [["ACLK, ARESETn", "1", "Clock and active-low reset"],
         ["TVALID", "1", "Transmitter has a valid transfer"],
         ["TREADY", "1", "Receiver can accept (optional: if absent, "
          "treated as always 1)"],
         ["TDATA", "8n", "Payload, an integer number of bytes"],
         ["TSTRB", "n", "Per byte: 1 = data byte, 0 = position byte"],
         ["TKEEP", "n", "Per byte: 0 = null byte (not part of the stream)"],
         ["TLAST", "1", "Marks the last transfer of a packet"],
         ["TID", "i", "Stream identifier, for interleaving several streams "
          "(recommended at most 8 bits)"],
         ["TDEST", "d", "Routing destination (recommended at most 4 bits)"],
         ["TUSER", "u", "Sideband: user-defined, typically a multiple of "
          "the number of data bytes"],
         ["TWAKEUP", "1", "AXI5-Stream: activity hint for power management"]],
        widths=[20, 10, 70], bold_first=True)
    tbl(["TKEEP", "TSTRB", "Byte type", "Meaning"],
        [["1", "1", "Data byte", "Valid data, transmitted"],
         ["1", "0", "Position byte", "Placeholder whose position matters "
          "(for example unwritten bytes in a frame buffer), value undefined"],
         ["0", "0", "Null byte", "Not part of the stream; may be removed or "
          "inserted freely"],
         ["0", "1", "Reserved", "Must not be used"]],
        widths=[10, 10, 18, 62], bold_first=True)
    p("Most streams need neither: a **continuous aligned stream** has "
      "TKEEP = TSTRB = all ones on every transfer, and designs omit the "
      "signals. The common exception is the last transfer of a packet "
      "whose byte length is not a multiple of the bus width: TKEEP marks "
      "the valid bytes of that final beat (a 'continuous unaligned "
      "stream' in spec terms).")

    h2("Packets, framing and backpressure")
    p("TLAST groups transfers into **packets**: an Ethernet frame, a video "
      "line, a DMA buffer, a DSP block. The protocol does not define a "
      "maximum packet length; the application does. Every component in a "
      "stream path makes one of three choices about packets:")
    bul(["**Transparent**: pass TLAST along with the data (register slices, "
         "FIFOs, width converters).",
         "**Packet-aware**: switches and arbiters must not interleave two "
         "packets on one output, so they lock the output from the first "
         "transfer to the transfer with TLAST.",
         "**Store-and-forward**: a **packet FIFO** holds a whole packet and "
         "releases it only when TLAST arrived (so the downstream never "
         "stalls mid-packet), or drops a packet flagged bad in TUSER at "
         "its end (Ethernet FCS errors)."])
    diagram(_wave([
        ("", "txt", ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]),
        ("ACLK", "clk", 7),
        ("TVALID", "bit", "0111110"),
        ("TREADY", "bit", "1101110"),
        ("TDATA", "bus", ["", "W0", "W1", "W1", "W2", "W3", ""]),
        ("TKEEP", "bus", ["", "1111", "1111", "1111", "1111", "0011", ""]),
        ("TLAST", "bit", "0000010"),
        ("xfer", "txt", ["", "^W0", "", "^W1", "^W2", "^W3", ""]),
    ], W=8), "A 14-byte packet on a 32-bit stream: three full words and a "
        "last word with TKEEP = 0011. The receiver stalls in T3; the "
        "transmitter holds W1 until the handshake in T4.")

    h2("Data width conversion")
    p("Width converters appear wherever a 512-bit DMA meets a 64-bit MAC or "
      "an 8-bit UART. Their behaviour is fixed by the byte-stream view of "
      "AXI4-Stream: the sequence of data and position bytes must be "
      "preserved, null bytes may be dropped or added, and TLAST must stay "
      "on the last byte of the packet.")
    bul(["**Downsizing** (wide to narrow): each wide transfer becomes up to "
         "N narrow transfers, lowest byte lanes first (little-endian byte "
         "order), skipping null bytes. TLAST goes on the last emitted "
         "transfer of a wide transfer that had TLAST.",
         "**Upsizing** (narrow to wide): accumulate narrow transfers until "
         "the wide word is full **or TLAST arrives**; a packet ending early "
         "is flushed with the unused lanes marked null (TKEEP = 0). TUSER "
         "is typically concatenated per byte or ORed, depending on meaning.",
         "Non-integer ratios (for example 24 to 32 bits for RGB pixels) need "
         "a gearbox with a byte shift register; they are a common source "
         "of off-by-one bugs at packet ends."])

    h2("Switching and routing streams")
    p("An **AXI4-Stream switch** (or interconnect) routes transfers by TDEST "
      "from S inputs to M outputs. Arbitration happens at packet boundaries: "
      "once an input wins an output, it keeps it until TLAST (or, in "
      "designs that allow it, a TID-based interleave). A **broadcaster** "
      "copies a stream to several outputs and must combine their TREADYs "
      "(a transfer completes only when all outputs accepted it, which "
      "needs care to avoid duplicating data to a fast output while a slow "
      "one stalls). A **combiner** merges several narrow streams into one "
      "wide one. TID lets several logical streams share one physical "
      "interface with transfers interleaved; a receiver that cannot handle "
      "interleaving needs one reassembly buffer per TID.")

    h2("Video over AXI4-Stream")
    p("The dominant convention, defined by Xilinx (AMD) in its video IP "
      "user guides and followed by many others, carries one video frame "
      "as a sequence of lines:")
    bul(["**TUSER[0] = SOF** (start of frame) on the first pixel of each "
         "frame.",
         "**TLAST = EOL** (end of line) on the last pixel of each line.",
         "TDATA holds one or more pixels per clock (1, 2, 4 or 8 pixels per "
         "clock for 4K and above), with components packed in a defined "
         "order; there is no blanking: TVALID is simply low between lines.",
         "A video timing controller and a 'stream to video out' block "
         "re-create HSYNC/VSYNC/blanking at the display interface "
         "(Chapter 21); the reverse block converts camera timing to a "
         "stream."])
    diagram([
        "  frame:  line 0: [SOF]p0 p1 p2 ... p1919[EOL]   line 1: p0 ... p1919[EOL]   ...",
        "  TUSER0:          1   0  0         0                    0        0",
        "  TLAST :          0   0  0         1                    0        1",
        "  1080 lines x 1920 pixels, 1 pixel/clock at 60 fps -> about 124 Mpixel/s active",
        "  (the 148.5 MHz 1080p60 pixel clock includes blanking; the stream does not)",
    ], "Video over AXI4-Stream: SOF in TUSER[0], EOL in TLAST.")
    box("warn", "PITFALL: lost frame synchronization",
        "If a block drops or duplicates a transfer, every following line is "
        "shifted and the image tears until the next SOF. Robust video "
        "receivers therefore resynchronize on SOF, count pixels per line "
        "and flag 'early EOL' and 'late EOL' errors, which is the first "
        "thing to check in a video pipeline hang.")

    h2("DMA: memory-mapped to stream and back")
    p("A **DMA engine** is the bridge between the memory-mapped world "
      "(AXI4) and the stream world (AXI4-Stream). By convention the two "
      "directions are named from the memory's point of view:")
    tbl(["Channel", "Direction", "What it does"],
        [["**MM2S**", "memory -> stream", "Reads a buffer with AXI4 read bursts "
          "and emits it as a stream packet, TLAST on the last byte, TKEEP "
          "on a partial last beat"],
         ["**S2MM**", "stream -> memory", "Writes an incoming stream packet to a "
          "buffer with AXI4 write bursts; the packet length is only known "
          "at TLAST, so the engine reports the received byte count in a "
          "status register or descriptor"]],
        widths=[14, 20, 66], bold_first=True)
    p("Simple DMAs are programmed with one address/length per transfer; "
      "**scatter-gather** DMAs fetch chains of descriptors from memory, "
      "each pointing to a buffer, so that a stream of packets lands in a "
      "ring of buffers without CPU involvement per packet. Design points "
      "that matter: burst splitting at 4KB (Chapter 7), enough outstanding "
      "reads for DDR latency, what S2MM does when a packet is longer than "
      "the buffer (truncate and flag, or continue into the next "
      "descriptor), and cache coherency of the buffers (Chapter 9).")

    h2("Hands-on: a 32-to-8 bit stream downsizer with TKEEP and TLAST")
    p("`axis_32to8` converts a 32-bit stream into bytes. It holds one input "
      "word and its TKEEP; each output handshake clears the lowest set "
      "TKEEP bit (`k & (k - 1)`), so null bytes are skipped automatically. "
      "TLAST is asserted on the last kept byte of a word that carried "
      "TLAST. The input is accepted when the register is empty or when its "
      "last byte leaves in the same cycle, so the converter sustains one "
      "byte per clock with no bubble between words.")
    _v("axis", "axis_32to8: AXI4-Stream downsizer that removes null bytes and "
               "moves TLAST to the last valid byte.")
    p("The testbench sends one directed packet (7 bytes, with a null byte in "
      "the middle word) and then 500 random packets of 1 to 40 bytes in "
      "which about one lane in eight is a null byte. TVALID has random gaps "
      "and TREADY random backpressure. A scoreboard compares every output "
      "byte and TLAST with the expected byte stream, and a checker verifies "
      "the AXI4-Stream rule that the output's TVALID, TDATA and TLAST stay "
      "stable while TREADY is low.")
    _v("axis_tb", "Testbench: directed + random packets, random "
                  "backpressure, scoreboard and stability checker.")
    _o("axis", "Real Icarus Verilog output: cycle trace of the directed "
               "packet, then the summary of 501 packets.")
    bul(["Cycle 3: word 0x44332211 is accepted into the empty converter.",
         "Cycles 4-9: bytes 11, 22, 33, 44 leave; in cycle 5 and 8 the sink "
         "is not ready and the byte is held (same data, TVALID high).",
         "The second word 0x88776655 has TKEEP = 1101: byte 0x66 is a null "
         "byte and never appears on the output (55 is followed by 77).",
         "The last word has TKEEP = 0011 and TLAST, so TLAST appears on 0xAA, "
         "the last kept byte, and is held through two stall cycles (15-16).",
         "Note the input side: TREADY rises exactly in the cycle where the "
         "last byte of the held word is taken (cycles 9 and 13): no bubble."])
    box("warn", "PITFALL: combinational TREADY and all-null TLAST beats",
        ["In this design `s_tready` depends combinationally on `m_tready`. "
         "That is legal, but chaining many such blocks creates a long "
         "combinational ready path through the whole pipeline. Insert a "
         "**register slice** (a two-entry skid buffer) every few stages.",
         "A transfer with TKEEP = 0000 and TLAST = 1 can occur in "
         "AXI4-Stream (it ends a packet with no data). This converter "
         "would load it, see no valid byte and lose the TLAST. A production "
         "converter must either forbid such transfers (and assert on them) "
         "or hold back each output byte until the next input transfer "
         "shows whether a TLAST follows, so that TLAST can still be "
         "attached to the previous valid byte. Many IP cores simply "
         "document that TLAST must accompany at least one valid byte."])

    h2("Summary")
    bul(["AXI4-Lite keeps AXI's five channels but only single-beat, "
         "full-width, in-order transactions without IDs, exclusives or "
         "cache attributes; it is the FPGA-world register bus.",
         "AXI4-Lite slaves must handle AW and W in any order, hold BVALID and "
         "RVALID until accepted, honour WSTRB and never lose a response under "
         "backpressure; formal verification catches these bugs quickly.",
         "AXI4-Stream is an addressless VALID/READY pipe with TDATA, "
         "TKEEP/TSTRB byte qualifiers, TLAST packet framing and TID/TDEST/"
         "TUSER sideband.",
         "Width converters, switches (packet-locked on TLAST), packet FIFOs "
         "and DMA MM2S/S2MM engines are the standard stream components; video "
         "uses TUSER[0] = SOF and TLAST = EOL.",
         "The verified downsizer handled null bytes, partial last words and "
         "random backpressure on 501 packets without error."])

    h2("Exercises")
    bul(["Write the complete read path of the AXI4-Lite slave whose write "
         "path is shown in Section 8.2, including a clear-on-read status "
         "register whose side effect happens exactly once.",
         "Design the matching 8-to-32 bit **upsizer**: how does it handle a "
         "packet of 6 bytes, and what TKEEP does its last output word carry?",
         "A stream switch has two inputs sending 1500-byte packets to the "
         "same output. Why must it lock the output until TLAST, and what is "
         "the worst-case latency for the second input at 16 bytes per cycle?",
         "An S2MM DMA receives a 9000-byte jumbo frame into 2048-byte "
         "buffers. Describe the descriptor and status sequence you would "
         "implement.",
         "For 4K (3840 x 2160) at 60 frames per second with 2 pixels per "
         "clock, compute the minimum stream clock frequency (active pixels "
         "only) and the TDATA width for 10-bit YUV 4:2:2.",
         "Add an SVA property set to `axis_tb` that checks TKEEP/TSTRB "
         "reserved combinations and that TLAST is never asserted on a "
         "transfer whose TKEEP is all zero."])


# ---------------------------------------------------------------- Ch 9 ----
def _ch9():
    chapter("Cache Coherency Protocols: MESI/MOESI, ACE and CHI")
    p("A modern application processor has 8 to 200+ cores, each with private "
      "L1 and L2 caches, plus GPUs, NPUs and I/O masters that read and write "
      "the same DRAM. As soon as two caches can hold a copy of the same "
      "memory location, the hardware must make sure nobody reads a stale "
      "value. That is the job of a **cache coherency protocol**. On the "
      "wires it becomes the most complex protocol in the SoC: ACE extends "
      "AXI with snoop channels, and CHI replaces buses altogether with a "
      "packetized, credit-based protocol over a mesh network.")
    p("This chapter builds the concepts from the ground up: the coherence "
      "invariants, the MSI/MESI/MOESI state machines, snooping versus "
      "directories, AMBA ACE and ACE-Lite, AMBA CHI (layers, channels, "
      "nodes, flows, credits and retry), memory consistency models and "
      "barriers, and a preview of CXL.cache and CXL.mem. The hands-on part "
      "is a MESI model with three caches whose invariant checker catches an "
      "injected protocol bug within a few transactions.")

    h2("Why coherence, and what exactly it guarantees")
    p("Consider two cores that both cached address X = 0. Core 0 writes "
      "X = 1 into its own cache (write-back, so memory still holds 0). If "
      "core 1 now reads X from its cache it gets 0, forever. Coherence "
      "protocols forbid this with two invariants, per memory location:")
    bul(["**SWMR (single-writer, multiple-reader)**: at any time either one "
         "cache may write the location (and nobody else holds a copy), or "
         "any number of caches may read it (and nobody writes).",
         "**Data-value invariant**: a read returns the value of the most "
         "recent write in the coherence order of that location."])
    box("key", "Coherence versus consistency",
        "**Coherence** is about a single address: all agents agree on the "
        "order of writes to that address. **Consistency** (the memory "
        "model) is about the order in which accesses to **different** "
        "addresses become visible. Coherence is implemented by the protocol "
        "in this chapter; consistency is defined by the ISA (x86-TSO, Arm, "
        "RISC-V RVWMO) and implemented by the cores and interconnect, "
        "using barriers where the programmer needs ordering (Section 9.6).")
    p("The granularity of coherence is the **cache line** (64 bytes on "
      "almost all current Arm, x86 and RISC-V application processors). Two "
      "variables in the same line written by different cores bounce the "
      "line back and forth: **false sharing**, a classic performance bug "
      "that the protocol handles correctly but slowly.")

    h2("MSI, MESI and MOESI")
    p("Each cache keeps a small state per line. The simplest useful protocol "
      "has three states: **M**odified (only copy, dirty), **S**hared "
      "(clean, maybe other copies) and **I**nvalid. MESI adds **E**xclusive "
      "(only copy, clean): a line read when no other cache has it becomes "
      "E, and a later write upgrades it to M **silently**, without any bus "
      "transaction, which removes most upgrade traffic for private data. "
      "MOESI adds **O**wned (dirty but shared): the owner supplies data to "
      "readers and remains responsible for the eventual write-back, so a "
      "dirty line can be shared without first writing memory.")
    h3("MESI transitions on processor requests")
    tbl(["State", "Processor read", "Processor write", "Eviction"],
        [["**I**", "BusRd; -> E if no other copy, else -> S",
          "BusRdX (read for ownership); -> M", "-"],
         ["**S**", "Hit, stay S", "BusUpgr (invalidate others); -> M",
          "Silent -> I (or Evict notification)"],
         ["**E**", "Hit, stay E", "Hit, **silent** -> M", "Silent -> I"],
         ["**M**", "Hit, stay M", "Hit, stay M", "Write back; -> I"]],
        widths=[10, 32, 32, 26], bold_first=True)
    h3("MESI transitions on snooped bus transactions")
    tbl(["State", "Snooped BusRd", "Snooped BusRdX", "Snooped BusUpgr"],
        [["**I**", "-", "-", "-"],
         ["**S**", "Stay S", "-> I", "-> I"],
         ["**E**", "-> S (assert 'shared')", "-> I", "(cannot happen)"],
         ["**M**", "Supply data (flush), memory updated; -> S", "Supply data; -> I",
          "(cannot happen)"]],
        widths=[10, 34, 30, 26], bold_first=True)
    p("MOESI differs only where M or O see a BusRd: M supplies the data and "
      "goes to **O** instead of S, without updating memory; O supplies data "
      "on later BusRds and writes back on eviction. Intel's **MESIF** adds "
      "**F**orward, a designated clean sharer that answers requests so that "
      "exactly one cache responds. The ACE and CHI state names map onto "
      "these letters:")
    tbl(["MOESI", "ACE / CHI name", "Unique?", "Dirty?"],
        [["M", "UniqueDirty (UD)", "yes", "yes"],
         ["E", "UniqueClean (UC)", "yes", "no"],
         ["O", "SharedDirty (SD)", "no", "yes"],
         ["S", "SharedClean (SC)", "no", "no"],
         ["I", "Invalid (I)", "-", "-"],
         ["-", "CHI only: UniqueCleanEmpty (UCE), UniqueDirtyPartial (UDP)",
          "yes", "no / partial"]],
        widths=[12, 54, 14, 20], bold_first=True)

    h2("Snooping versus directories")
    p("A **snooping** protocol broadcasts every coherent request to all "
      "caches, which check their tags and respond. It is simple and fast "
      "for a handful of agents, which is why ACE-based clusters of up to "
      "about eight cores use it. Broadcast traffic grows with the number "
      "of agents squared, so large systems use a **directory**: a home "
      "node per address range records which caches may hold each line "
      "(a presence bit-vector, or a limited pointer list) and sends "
      "snoops only to them.")
    tbl(["Aspect", "Snooping", "Directory / snoop filter"],
        [["Request path", "Broadcast to all caches", "To the home node, which "
          "snoops only recorded sharers"],
         ["Scalability", "Poor beyond ~8-16 agents", "Hundreds of agents"],
         ["Latency", "One broadcast, fast for small systems",
          "Extra hop to the home (indirection)"],
         ["Storage", "None", "Directory or snoop-filter SRAM, sized for the "
          "total private-cache capacity"],
         ["Examples", "Classic SMP buses, ACE clusters", "Arm CMN (CHI) snoop "
          "filters, AMD/Intel server fabrics"]],
        widths=[16, 38, 46], bold_first=True)
    p("In practice most SoCs use a **snoop filter**: an inclusive directory "
      "of the lines held in the private caches, located at the home node. "
      "When the snoop filter runs out of entries it must **back-invalidate** "
      "a line from the caches, a performance effect worth checking in "
      "system benchmarks.")

    h2("AMBA ACE: AXI Coherency Extensions")
    p("ACE (AMBA 4, 2011) turns AXI into a snooping protocol for clusters "
      "such as Cortex-A15/A7 big.LITTLE systems connected by a CCI "
      "interconnect. It adds signals to the existing channels and three new "
      "channels for snoops:")
    tbl(["Where", "Added signals", "Purpose"],
        [["AR", "ARSNOOP[3:0], ARDOMAIN[1:0], ARBAR[1:0]", "Coherent read type, "
          "shareability domain, barrier"],
         ["AW", "AWSNOOP[2:0], AWDOMAIN[1:0], AWBAR[1:0], AWUNIQUE",
          "Coherent write type, domain, barrier, 'line held unique'"],
         ["R", "RRESP[3:2] = {IsShared, PassDirty}", "Tells the master the final "
          "state: shared or unique, and whether it inherits dirtiness"],
         ["RACK, WACK", "1 bit each, master to interconnect",
          "Acknowledge that the R/B response was consumed (ordering of "
          "snoops against responses)"],
         ["**AC** (snoop address)", "ACVALID, ACREADY, ACADDR, ACSNOOP[3:0], ACPROT",
          "Interconnect to master: snoop request"],
         ["**CR** (snoop response)", "CRVALID, CRREADY, CRRESP[4:0]",
          "Master to interconnect: DataTransfer, Error, PassDirty, IsShared, "
          "WasUnique"],
         ["**CD** (snoop data)", "CDVALID, CDREADY, CDDATA, CDLAST",
          "Master to interconnect: the line's data when DataTransfer = 1"]],
        widths=[20, 38, 42], bold_first=True)
    p("**Domains** (AxDOMAIN) limit the scope of coherence: Non-shareable, "
      "Inner Shareable (typically the CPU clusters), Outer Shareable (adds, "
      "for example, a GPU) and System. The main transaction groups are:")
    tbl(["Group", "Transactions", "Use"],
        [["Non-snooping", "ReadNoSnoop, WriteNoSnoop", "Non-shareable memory"],
         ["Coherent reads", "ReadOnce, ReadClean, ReadNotSharedDirty, "
          "**ReadShared**, **ReadUnique**", "ReadShared for loads, ReadUnique "
          "for a store miss (full line with ownership), ReadOnce for a "
          "one-time snapshot not kept in cache"],
         ["Dataless ownership", "**CleanUnique**, **MakeUnique**", "CleanUnique: "
          "upgrade a Shared line to Unique (invalidate others, others' dirty "
          "data is written back); MakeUnique: get ownership of a line that "
          "will be fully overwritten, without fetching data"],
         ["Cache maintenance", "CleanShared, CleanInvalid, MakeInvalid",
          "Software cache maintenance (clean/invalidate by address)"],
         ["Coherent writes", "WriteUnique, WriteLineUnique", "Write into "
          "shareable memory without holding the line (I/O masters)"],
         ["Memory update", "**WriteBack**, WriteClean, WriteEvict, Evict",
          "Eviction of dirty (WriteBack), cleaning (WriteClean), clean "
          "eviction to a lower cache (WriteEvict), eviction notice for snoop "
          "filters (Evict)"],
         ["Other", "Barriers, DVM Operation / DVM Sync / DVM Complete",
          "Ordering barriers; distributed virtual memory messages (TLB and "
          "branch-predictor invalidation broadcast)"]],
        widths=[18, 34, 48], bold_first=True)
    diagram([
        "  CPU0 (ACE)               CCI interconnect                 CPU1 (ACE, line in UD)",
        "     | AR: ReadShared X          |                                   |",
        "     |-------------------------->|  AC: ReadShared X                 |",
        "     |                           |---------------------------------->|",
        "     |                           |  CR: DataTransfer=1, IsShared=1,  |",
        "     |                           |      PassDirty=1                  |",
        "     |                           |<----------------------------------|",
        "     |                           |  CD: line data (CDLAST)           |",
        "     |                           |<----------------------------------| -> SC",
        "     |  R: data, IsShared=1,     |                                   |",
        "     |     PassDirty=1 (-> SD)   |                                   |",
        "     |<--------------------------|                                   |",
        "     | RACK                      |                                   |",
        "     |-------------------------->|                                   |",
    ], "An ACE ReadShared that hits a dirty line in another CPU: the snooped "
       "cache supplies the data on CD and passes the dirty responsibility to "
       "the requester (it ends in SharedDirty, i.e. MOESI's O state).")
    h3("ACE-Lite")
    p("**ACE-Lite** has the extra AR/AW signals but **no snoop channels**: "
      "the master has no coherent cache of its own, so it never needs to be "
      "snooped, but its reads and writes snoop the CPU caches. This is "
      "**I/O coherency**: a DMA engine, GPU or network controller behind "
      "ACE-Lite can read data a CPU just wrote into its cache without "
      "software cache cleaning. ACE-Lite supports ReadOnce, WriteUnique, "
      "WriteLineUnique, the non-snooping transactions, cache maintenance "
      "and barriers; **ACE-Lite + DVM** adds DVM messages for SMMUs.")
    box("warn", "PITFALL: 'coherent' DMA that is not",
        "An I/O master is only coherent if its transactions are marked "
        "shareable (AxDOMAIN) with the right AxCACHE attributes **and** the "
        "interconnect port is configured to snoop. A driver that maps a "
        "buffer as non-cacheable on one side and cacheable on the other, or "
        "an SoC integration that ties AxDOMAIN to non-shareable, produces "
        "rare stale-data bugs that look like software races. Put a "
        "directed coherency test (CPU writes, DMA reads immediately) into "
        "the SoC bring-up suite.")

    h2("AMBA CHI: the Coherent Hub Interface")
    p("CHI (AMBA 5, first issue 2014) was designed for scalable systems: "
      "tens to hundreds of requesters on a mesh network, such as Arm's "
      "CMN-600/CMN-700 based server and infrastructure SoCs. Instead of "
      "wires per transaction field it sends **flits** (packets) over "
      "**channels**, with explicit source and target node IDs, and it "
      "separates concerns into layers:")
    tbl(["Layer", "Responsibility"],
        [["**Protocol**", "Transactions and their message flows, cache states, "
          "ordering, retry and protocol credits"],
         ["**Network**", "Packetizing messages, node IDs (SrcID, TgtID), "
          "routing across the interconnect topology"],
         ["**Link**", "Flow control between two adjacent components with "
          "link-layer credits, link activation/deactivation handshake, flit "
          "transfer per channel"],
         ["Physical", "Wires, clocking, possibly die-to-die links; not "
          "defined by the CHI specification itself (implementation-specific)"]],
        widths=[16, 84], bold_first=True)
    h3("Channels and node types")
    p("Each node has a transmit and a receive side of four channels: **REQ** "
      "(requests), **RSP** (responses without data, e.g. CompAck, RetryAck, "
      "Comp), **SNP** (snoops, home to requester) and **DAT** (data, e.g. "
      "CompData, SnpRespData, write data).")
    tbl(["Node", "Role"],
        [["**RN-F**", "Fully coherent requester with a cache (a CPU cluster)"],
         ["**RN-D**", "I/O coherent requester that also accepts DVM snoops "
          "(for example an SMMU)"],
         ["**RN-I**", "I/O coherent requester without a cache (typically the "
          "bridge from an ACE-Lite/AXI I/O subsystem)"],
         ["**HN-F**", "Fully coherent home node: point of coherence for its "
          "address slice, holds the snoop filter and often a slice of the "
          "system level cache"],
         ["**HN-I**", "Home node for I/O (non-coherent) address space"],
         ["**SN-F**", "Subordinate node for normal memory (a DDR controller)"],
         ["**SN-I**", "Subordinate node for I/O peripherals"],
         ["**MN**", "Miscellaneous node: DVM and barrier handling"]],
        widths=[12, 88], bold_first=True)
    h3("A CHI read flow")
    diagram([
        "  RN-F0 (requester)       HN-F (home, snoop filter)   RN-F1 (holds UD)    SN-F (DDR)",
        "     |                           |                            |                     |",
        "     |-- REQ ReadShared -------->|                            |                     |",
        "     |                           |-- SNP SnpShared ---------->|                     |",
        "     |<- DAT CompData (DCT: direct cache transfer) -----------|                     |",
        "     |                           |<- RSP SnpResp -------------|                     |",
        "     |-- RSP CompAck ----------->|                            |                     |",
        "  on a miss in all caches:",
        "     |-- REQ ReadShared -------->|-- REQ ReadNoSnp -------------------------------->|",
        "     |<- DAT CompData (DMT: direct memory transfer) --------------------------------|",
        "     |-- RSP CompAck ----------->|                            |                     |",
    ], "CHI ReadShared: with a snoop hit, the snooped RN-F can send data "
       "straight to the requester (DCT); on a miss the memory node can do so "
       "(DMT). The requester's CompAck lets the home close the transaction.")
    h3("Credits and retry")
    p("CHI has two independent flow-control mechanisms:")
    bul(["**Link-layer credits (L-credits)**: per channel and per link, the "
         "receiver grants credits (one per free flit buffer, signalled on a "
         "credit-valid wire) and the transmitter may only send a flit when "
         "it holds a credit. This is the credit-based flow control of "
         "Chapter 3 and Section 10.6, and it means a link never drops a "
         "flit.",
         "**Protocol retry**: a home node may not have a free tracker for a "
         "new request. It then answers **RetryAck** and later sends "
         "**PCrdGrant** (a protocol credit of a given type) when resources "
         "free up; the requester resends the request, now marked as using "
         "that credit (AllowRetry = 0), and it is guaranteed to be accepted. "
         "This prevents a request from occupying network buffers while "
         "waiting, which is essential for deadlock freedom."])
    box("expert", "Why CHI scales where ACE does not",
        ["Snoops go only where the snoop filter says the line lives.",
         "Home nodes are distributed: each HN-F owns an address hash slice, "
         "so coherence bandwidth grows with the mesh.",
         "Direct transfers (DCT, DMT, and DWT for writes) remove the home "
         "from the data path.",
         "Everything is a message with IDs and credits, so the same "
         "protocol runs across chiplets (CHI over a die-to-die link such as "
         "UCIe, Chapter 22) with only the link and physical layers "
         "changing."])

    h2("Memory consistency models and barriers")
    p("Coherence alone does not say when a write to X becomes visible "
      "relative to a write to Y. The ISA's memory model does:")
    tbl(["Model", "Key property", "Used by"],
        [["**Sequential consistency (SC)**", "All accesses appear in one "
          "global order consistent with each program's order", "Reference "
          "model; too restrictive for fast hardware"],
         ["**TSO** (total store order)", "Like SC except a load may pass an "
          "earlier store to a different address (the store buffer)",
          "x86 (x86-TSO), SPARC TSO, RISC-V Ztso option"],
         ["**Weak / relaxed**", "Loads and stores to different addresses may "
          "be reordered unless ordered by a dependency or barrier",
          "Arm (v8/v9), RISC-V RVWMO, POWER"],
         ["**Release consistency**", "Ordering only at acquire (after a "
          "lock/flag read) and release (before a lock/flag write)",
          "Arm LDAR/STLR, RISC-V .aq/.rl, C/C++ atomics"]],
        widths=[26, 44, 30], bold_first=True)
    code([
        "// Message-passing litmus test (MP).       x = data, f = flag, both 0 initially",
        "// Core 0                 Core 1",
        "   x = 42;                while (f == 0) ;",
        "   f = 1;                 r = x;           // SC, TSO: r == 42 guaranteed",
        "",
        "// On Arm / RISC-V the stores or loads may be reordered, so r == 0 is allowed",
        "// unless ordered, for example:",
        "   x = 42;                while (f == 0) ;",
        "   DMB ISHST  (or STLR)   DMB ISHLD  (or LDAR f)      // Arm",
        "   f = 1;                 r = x;",
        "// RISC-V: fence w,w between the stores; fence r,r between the loads",
    ], "The message-passing litmus test and the barriers that make it work "
       "on weakly ordered machines.")
    p("Barriers reach the interconnect too. A **DMB** only orders the core's "
      "own accesses; a **DSB** additionally waits until earlier accesses "
      "have **completed**, which for writes means the B response (or the "
      "CHI Comp) has returned from the point of coherence or the device. "
      "This is why device drivers use a DSB before triggering a DMA engine "
      "through a register write: the descriptor writes must be visible to "
      "the DMA first. ACE had explicit barrier transactions (AxBAR); later "
      "AMBA 5 protocols removed barrier transactions and rely on response "
      "semantics instead.")

    h2("Preview: CXL.cache and CXL.mem")
    p("Compute Express Link (Chapter 18) carries coherency **off chip**, "
      "over the PCIe physical layer. It multiplexes three protocols on one "
      "link:")
    tbl(["Protocol", "Direction and purpose", "Channels"],
        [["**CXL.io**", "PCIe-equivalent: discovery, configuration, DMA, "
          "interrupts", "PCIe TLPs"],
         ["**CXL.cache**", "A device (accelerator) caches **host** memory "
          "coherently; the host snoops the device", "D2H Req/Resp/Data, H2D "
          "Req/Resp/Data"],
         ["**CXL.mem**", "The host reads and writes **device-attached** "
          "memory with load/store semantics (memory expansion, pooling)",
          "M2S Req and RwD; S2M NDR and DRS (plus back-invalidate channels "
          "from CXL 3.0)"]],
        widths=[14, 50, 36], bold_first=True)
    p("Device types: **Type 1** (cache, no memory: smart NIC) uses .io + "
      ".cache; **Type 2** (accelerator with its own memory) uses all three; "
      "**Type 3** (memory expander) uses .io + .mem. Versions 1.1 and 2.0 "
      "run on the PCIe 5.0 PHY at 32 GT/s (2.0 adds switching and memory "
      "pooling); 3.x moves to PCIe 6.x at 64 GT/s with PAM4 and FLIT mode "
      "and adds fabrics, memory sharing and back-invalidate snoops for "
      "device-managed coherence. Inside the SoC, a CXL controller is "
      "typically an RN (for .cache) or an SN/HN (for .mem) on the CHI mesh.")

    h2("Hands-on: a MESI model with invariant checking")
    p("The model below keeps one cache line in three caches on an **atomic "
      "snooping bus**: each cycle one processor request is served together "
      "with its bus transaction, so there are no transient states. It "
      "implements the tables of Section 9.2 directly: requester actions in "
      "one block, snooper reactions in a loop over the other caches, and "
      "wired-OR 'shared' and 'dirty' snoop results. A parameter `BUG` "
      "injects a realistic error: snoopers ignore BusUpgr, so a write hit "
      "on a Shared line does not invalidate the other copies.")
    _v("mesi", "mesi_sys: one line, N snooping caches, MESI with write-back "
               "memory and an optional injected bug.")
    p("The testbench instantiates a correct and a buggy system side by side "
      "and feeds both the same request stream: twelve directed operations, "
      "then 20000 random reads, writes and evictions. After every request it "
      "checks **SWMR** (at most one M/E copy, and an M/E copy excludes all "
      "others) and the **data-value invariant**: every value written is a "
      "new number, and every read must return the latest one.")
    _v("mesi_tb", "Testbench: shared stimulus, SWMR check and a golden "
                  "latest-value model for stale-read detection.")
    _o("mesi", "Real Icarus Verilog output. The bus column and read data "
               "refer to the correct system; the right-hand states are the "
               "buggy system's.")
    bul(["P0 reads (miss, no sharers): **E**. P0 writes: E -> M **silently** "
         "(bus = '-').",
         "P1 reads: BusRd; P0 flushes (memory becomes 0001) and both end in S. "
         "P2 reads: all three S.",
         "P1 writes: **BusUpgr**. Correct system: I M I. Buggy system: "
         "**S M S**, an SWMR violation visible immediately.",
         "P0 reads next: in the correct system it misses and gets 0002 from "
         "P1 (who flushes). In the buggy system P0 still holds a Shared copy "
         "and hits on stale data 0001; the counters at the end show 859 "
         "stale reads and 3570 SWMR violations in the buggy model, zero in "
         "the correct one."])
    box("expert", "From this model to real protocol verification",
        ["Real protocols are not atomic: a request, its snoops and responses "
         "are separate messages, so caches have **transient states** (for "
         "example IS^D: 'was I, sent a read, waiting for data'). Most bugs "
         "live in races between a snoop and an in-flight request to the same "
         "line.",
         "Industry practice is to model-check the protocol at the "
         "architectural level (Murphi, TLA+, or formal tools on an abstract "
         "RTL model) and then run SWMR/data-value scoreboards in RTL "
         "simulation and emulation with heavy same-line contention.",
         "A scoreboard like the one above, attached to an SoC simulation, "
         "is the most valuable coherency check you can write: it is "
         "independent of the protocol details."])

    h2("Ownership and integration")
    tbl(["Team", "Coherency responsibilities"],
        [["Architecture", "Protocol choice (ACE vs CHI), snoop filter sizing, "
          "home-node count, SLC policy, coherency domains"],
         ["RTL", "Cache controllers and their transient states, home nodes, "
          "ACE/CHI bridges, DVM handling"],
         ["DV / formal", "Protocol VIP (ACE/CHI), coherency scoreboards, "
          "litmus tests on the full SoC, formal checks of cache FSMs"],
         ["Firmware / OS", "Memory attributes in page tables, cache "
          "maintenance for non-coherent masters, barriers in drivers"],
         ["Performance", "Snoop latency and bandwidth, false-sharing "
          "analysis, snoop-filter back-invalidation rates"]],
        widths=[18, 82], bold_first=True)

    h2("Summary")
    bul(["Coherence enforces SWMR and the data-value invariant per cache "
         "line; consistency (TSO, weak, release) orders different addresses "
         "and is enforced with barriers.",
         "MSI, MESI (silent E -> M upgrade) and MOESI (dirty sharing with an "
         "owner) are the core state machines; ACE/CHI name the states UC, "
         "UD, SC, SD, I (CHI adds UCE and UDP).",
         "Snooping broadcasts and suits small clusters; directories and "
         "snoop filters scale to large meshes.",
         "ACE adds snoop channels AC/CR/CD and coherent transaction types "
         "to AXI; ACE-Lite gives I/O coherency without snoop channels.",
         "CHI is a layered, packetized protocol (REQ/RSP/SNP/DAT) with RN, "
         "HN and SN nodes, link credits, protocol retry and direct transfers.",
         "CXL.cache and CXL.mem extend coherency and memory semantics over "
         "the PCIe PHY.",
         "The MESI model's invariant checker found the injected BusUpgr bug "
         "at the first upgrade and reported hundreds of stale reads."])

    h2("Exercises")
    bul(["Extend `mesi_sys` to MOESI: add the O state, make M -> O on a "
         "snooped BusRd without a memory update, and adapt the invariants. "
         "How much memory write traffic does the random test save?",
         "Draw the message sequence for a store miss (ReadUnique) in CHI when "
         "two other RN-Fs hold the line in SC. Which snoops are sent, and when "
         "may the requester write?",
         "Explain why the E state saves bus traffic for private data, and "
         "construct an access sequence where MESI and MSI produce a different "
         "number of bus transactions.",
         "Write the store-buffering (SB) litmus test and explain why "
         "r1 == r2 == 0 is allowed under TSO but not under SC. Which barrier "
         "forbids it on Arm?",
         "A DMA engine writes a buffer through ACE-Lite with WriteUnique "
         "while a CPU holds some of those lines in UD. Describe what the "
         "interconnect must do for each line.",
         "Estimate the snoop-filter size (entries) needed for 64 cores with "
         "1 MB private L2 each and 64-byte lines, and discuss what happens "
         "when it is under-provisioned."])


# --------------------------------------------------------------- Ch 10 ----
def _ch10():
    chapter("Other On-Chip Protocols: Wishbone, Avalon, TileLink, OCP and NoCs")
    p("AMBA dominates commercial SoCs, but it is not the only on-chip "
      "protocol you will meet. Open-source cores and FPGA soft-SoCs use "
      "**Wishbone**; Intel (Altera) FPGA designs use **Avalon**; RISC-V SoCs "
      "from SiFive, the Rocket Chip generator and OpenTitan use "
      "**TileLink**; older consumer SoCs used **OCP** and IBM **CoreConnect**. "
      "And inside every large SoC, all of these ride on a **network-on-chip "
      "(NoC)** that packetizes transactions and routes them across the die. "
      "This chapter surveys the alternatives at the level needed to "
      "integrate, bridge and debug them, then dives into NoC fundamentals "
      "with a working 3x3 mesh of wormhole routers.")

    h2("Wishbone B4")
    p("Wishbone is an open, royalty-free bus defined by Silicore and "
      "maintained by the OpenCores community; revision **B4** (2010) is the "
      "current one. Its philosophy is minimalism: a handful of signals, "
      "named from the point of view of the module (suffix _O for outputs, "
      "_I for inputs), an active-high synchronous reset and a single "
      "clock.")
    tbl(["Signal (master side)", "Meaning"],
        [["CLK_I, RST_I", "Clock and active-high reset"],
         ["CYC_O", "A bus cycle is in progress (held for a whole block of "
          "transfers; also used as the arbitration request)"],
         ["STB_O", "Strobe: this cycle carries a valid transfer request"],
         ["WE_O", "1 = write, 0 = read"],
         ["ADR_O, DAT_O, DAT_I", "Address, write data, read data"],
         ["SEL_O", "Byte select, one bit per byte lane (like WSTRB)"],
         ["ACK_I, ERR_I, RTY_I", "Normal termination, error, retry"],
         ["STALL_I", "Pipelined mode: slave cannot accept a new request"],
         ["LOCK_O", "Indivisible sequence"],
         ["CTI_O, BTE_O", "Registered-feedback bursts: cycle type (classic, "
          "constant-address, incrementing, end-of-burst) and burst type "
          "(linear, 4/8/16-beat wrap)"],
         ["TGA/TGC/TGD", "User tags on address, cycle and data"]],
        widths=[26, 74], bold_first=True)
    h3("Classic and pipelined cycles")
    p("In the **classic** cycle, the master asserts CYC and STB with address "
      "and data and holds them until the slave terminates the transfer with "
      "ACK (or ERR/RTY). A slave with a registered ACK therefore costs at "
      "least two clocks per transfer, similar to APB. In **pipelined** mode "
      "(introduced in B4), STB means 'new request this cycle'; the master "
      "may issue one request per clock while STALL is low, and ACKs come "
      "back later, one per request and in order, while CYC stays high "
      "until the last ACK. That turns Wishbone into a single-outstanding-"
      "queue protocol with AHB-like throughput.")
    diagram(_wave([
        ("", "txt", ["T1", "T2", "T3", "T4", "T5", "T6"]),
        ("CLK", "clk", 6),
        ("CYC", "bit", "011110"),
        ("STB", "bit", "011100"),
        ("ADR", "bus", ["", "A0", "A1", "A2", "", ""]),
        ("STALL", "bit", "000000"),
        ("ACK", "bit", "001110"),
        ("DAT_I", "bus", ["", "", "D0", "D1", "D2", ""]),
    ], W=7), "Pipelined Wishbone read of three words: requests in T2-T4, "
        "acknowledgements with data one cycle later in T3-T5; CYC drops "
        "after the last ACK.")
    h3("Hands-on: a Wishbone classic slave")
    p("A register slave with a registered ACK (one wait state), SEL byte "
      "enables and ERR for unmapped addresses. The `!ack_o && !err_o` term "
      "in `req` is the important detail: in a classic cycle the master is "
      "still asserting STB in the cycle where ACK is high, and without that "
      "term the slave would see a second request and acknowledge twice.")
    _v("wb", "wb_regs: Wishbone B4 classic slave.")
    _v("wb_tb", "Testbench with a classic-cycle master task; a block read "
                "keeps CYC asserted between two transfers.")
    _o("wb", "Real Icarus Verilog output: every transfer takes two clocks "
             "(request, then ACK); SEL = 0010 writes only byte 1; the block "
             "read in cycles 8-11 keeps CYC high; 0x24 terminates with ERR.")
    box("warn", "PITFALL: bridging Wishbone to AXI",
        "Wishbone has no IDs, no separate read/write channels and (in "
        "classic mode) at most one transfer in flight, so a Wishbone-to-AXI "
        "bridge is easy but slow. The reverse direction must serialize AXI "
        "bursts and, for pipelined Wishbone, count outstanding requests to "
        "match ACKs with the right AXI beat. The most frequent bug is "
        "forgetting RTY_I and ERR_I termination paths, which hang the bridge "
        "when a slave answers with them.")

    h2("Intel Avalon: Avalon-MM and Avalon-ST")
    p("Avalon is the interface family of Intel (formerly Altera) FPGA "
      "Platform Designer (formerly Qsys). Recent documentation calls the "
      "roles **host** and **agent**.")
    tbl(["Avalon-MM signal", "Meaning"],
        [["address, byteenable", "Address and byte lanes. Hosts use byte "
          "addresses; agents by default see word addresses, and the "
          "interconnect converts"],
         ["read, write, writedata, readdata", "Command strobes and data"],
         ["waitrequest", "Agent cannot accept the command this cycle (the "
          "host holds it), i.e. the inverse of READY"],
         ["readdatavalid", "Pipelined reads: data returns later, in order, "
          "one pulse per read beat"],
         ["burstcount", "Burst length in beats (bursts are always incrementing)"],
         ["response, writeresponsevalid", "OKAY, SLVERR/SLAVEERROR, "
          "DECODEERROR; optional write responses"],
         ["lock, debugaccess", "Locked sequences; debugger access"]],
        widths=[30, 70], bold_first=True)
    p("**Avalon-ST** is the streaming counterpart: valid, ready, data, "
      "channel, error, startofpacket, endofpacket and empty (number of "
      "unused symbols in the last beat, where AXI4-Stream uses TKEEP). Its "
      "notable difference from AXI4-Stream is the **readyLatency** "
      "parameter: with readyLatency = N the source may send data N cycles "
      "after ready was asserted, which allows ready to be pipelined but "
      "means an adapter (a small FIFO) is needed to connect to an AXI4-Stream "
      "interface, whose behaviour corresponds to readyLatency = 0.")

    h2("TileLink")
    p("TileLink was created at UC Berkeley and SiFive for the Rocket Chip "
      "generator and is now maintained under the Chips Alliance. It is a "
      "chip-scale, **coherent-capable** protocol with a clean layered "
      "design and three conformance levels:")
    tbl(["Level", "Operations", "Typical use"],
        [["**TL-UL** (Uncached Lightweight)", "Get, PutFullData, PutPartialData; "
          "single-beat", "Peripherals; OpenTitan uses TL-UL as its whole "
          "on-chip bus"],
         ["**TL-UH** (Uncached Heavyweight)", "Adds multi-beat bursts, atomics "
          "(ArithmeticData, LogicalData) and hints (Intent)", "Memory and "
          "accelerators"],
         ["**TL-C** (Cached)", "Adds Acquire/Probe/Release/Grant for "
          "coherent caches", "Coherent CPU clusters, L2 caches"]],
        widths=[26, 46, 28], bold_first=True)
    p("TileLink messages travel on up to **five channels**, each with its "
      "own valid/ready handshake:")
    diagram([
        "          master (client)                          slave (manager)",
        "   A: requests  (Get, Put, Acquire, atomics) ------------------------->",
        "   B: probes    (Probe, forwarded ops)       <-------------------------   TL-C",
        "   C: releases  (ProbeAck[Data], Release[Data]) ---------------------->   TL-C",
        "   D: responses (AccessAck[Data], Grant[Data], ReleaseAck) <-----------",
        "   E: GrantAck  (completes an Acquire)       ------------------------->   TL-C",
        "",
        "   fields: opcode, param, size, source (ID), address, mask, data, corrupt;",
        "           D also has sink (ID for E) and denied",
    ], "TileLink channels. TL-UL and TL-UH use only A and D; TL-C adds B, C and E.")
    p("Deadlock freedom is built into the rules: channels have a priority "
      "order (A lowest, then B, C, D, E highest), and a message on a "
      "channel may never wait for a message on a lower-priority channel. "
      "Coherence uses **permissions** (None, Branch = read-only, Trunk/Tip = "
      "read-write) rather than MESI letters, but the concepts map directly "
      "onto Chapter 9: Acquire is ReadShared/ReadUnique, Probe is a snoop, "
      "Release is a write-back.")
    box("tip", "TileLink in practice",
        "The Rocket Chip and Chipyard generators describe TileLink networks "
        "in Chisel with 'diplomacy', which negotiates parameters (widths, "
        "supported sizes and operations) between every client and manager at "
        "elaboration time. When bridging to AXI (TLToAXI4, AXI4ToTL), the "
        "source field maps to AXI IDs and TL's per-message size maps to "
        "AxLEN/AxSIZE.")

    h2("OCP: the Open Core Protocol")
    p("OCP was promoted from 2001 by the OCP-IP consortium (Sonics, TI, "
      "Nokia and others) as a **configurable socket**: instead of fixing a "
      "bus, it defines a large menu of optional features from which each "
      "core picks a profile, and an interconnect (often a Sonics NoC) "
      "adapts. Its basic signals are MCmd (IDLE, WR, RD, RDEX, RDL, WRNP, "
      "WRC, BCST), MAddr, MData, MByteEn, SCmdAccept, SResp (NULL, DVA, "
      "FAIL, ERR) and SData, with optional bursts (MBurstLength, "
      "MBurstSeq), threads (MThreadID) and tags (MTagID) for out-of-order "
      "completion. TI's OMAP phones used it extensively. The OCP-IP "
      "assets were transferred to **Accellera** in 2013; new designs rarely "
      "choose OCP, but it remains in legacy IP and its thread concept "
      "influenced later NoCs.")

    h2("IBM CoreConnect")
    p("CoreConnect (1999) was IBM's bus architecture for PowerPC 4xx "
      "embedded SoCs and, for a decade, Xilinx's embedded-processor "
      "platform (PowerPC 405/440 hard cores, early MicroBlaze). It had "
      "three buses: **PLB** (Processor Local Bus, 32 to 128 bits, pipelined "
      "and split read/write), **OPB** (On-chip Peripheral Bus, simpler) and "
      "**DCR** (Device Control Register bus, a daisy-chained ring for "
      "configuration registers). Xilinx moved to AXI around 2009-2010, "
      "and CoreConnect now matters mostly for maintaining old designs.")

    h2("Networks-on-chip: packets, flits, routing and flow control")
    p("A crossbar connecting M masters to S slaves costs O(M x S) wires and "
      "cannot be placed and routed across a 400 mm^2 die at GHz speeds. A "
      "**network-on-chip** replaces it with routers connected by short, "
      "registered links, and transports each transaction as a **packet**. "
      "The masters and slaves keep their native protocols (AXI, AHB, APB, "
      "CHI); **network interface units (NIUs)** at the edge convert "
      "transactions to packets and back.")
    diagram([
        "  AXI master --[NIU]--(R)-----(R)-----(R)--[NIU]-- DDR ctrl (AXI slave)",
        "                       |       |       |",
        "  AHB master --[NIU]--(R)-----(R)-----(R)--[NIU]-- APB subsystem",
        "                       |       |       |",
        "  CHI RN-F  ---------(R)-----(R)-----(R)--------- HN-F / SLC slice",
        "",
        "  packet = head flit [route | dest | VC | type | txn id] + body flits + tail",
        "  flit   = flow-control unit (one buffer slot);  phit = what one link moves per cycle",
    ], "A NoC: NIUs packetize protocol transactions, routers (R) forward flits.")
    h3("Topologies")
    tbl(["Topology", "Properties", "Where used"],
        [["Crossbar / partial crossbar", "Single hop, O(n^2) wiring", "Small "
          "subsystems, inside routers"],
         ["Ring", "Simple, low area, latency grows with n", "Older Arm CCN, "
          "earlier Intel client ring bus"],
         ["2D mesh", "Regular, scalable, easy to floorplan", "Arm CMN, many-core "
          "server CPUs, AI accelerators"],
         ["Torus", "Mesh plus wrap-around links, lower diameter, needs "
          "deadlock care", "Some HPC/AI chips"],
         ["Tree / irregular", "Matches the floorplan and traffic", "Commercial "
          "NoC generators (FlexNoC, NI-700)"]],
        widths=[24, 44, 32], bold_first=True)
    h3("Switching and routing")
    bul(["**Store-and-forward**: a router receives the whole packet before "
         "forwarding; latency grows with packet length times hops.",
         "**Virtual cut-through**: forwarding starts as soon as the head "
         "arrives, but a router must have room for the whole packet.",
         "**Wormhole**: forwarding starts with the head flit and buffers are "
         "per flit; a packet stretches across several routers like a worm. "
         "Minimal buffering, the default for on-chip networks, but a blocked "
         "head stalls every link the worm occupies.",
         "**Dimension-order (XY) routing**: travel in X until the column "
         "matches, then in Y. Deterministic, trivially simple, in-order per "
         "source/destination pair, and deadlock-free on a mesh because no "
         "packet ever turns from Y back into X.",
         "**Adaptive routing** (west-first, odd-even turn models) routes "
         "around congestion but may reorder packets, which the NIU must "
         "then fix for protocols like AXI that require per-ID ordering."])
    h3("Credit-based flow control")
    p("Flits must never be dropped, so each link uses **credit-based flow "
      "control**: the sender keeps a counter of free buffer slots in the "
      "receiver, decrements it for every flit sent and increments it when "
      "the receiver returns a credit (one per freed slot). For full "
      "throughput the buffer depth must cover the **credit round trip**: "
      "link latency forward, processing, and credit latency back. With a "
      "one-cycle link each way and one cycle of processing, a router needs "
      "at least three buffers per input (per virtual channel) to sustain one "
      "flit per cycle. A valid/ready link with a registered 'not full' "
      "READY, as in the example below, is the degenerate case of credits "
      "with zero return latency.")

    h2("Virtual channels and deadlock")
    p("A **virtual channel (VC)** is a separate buffer queue sharing one "
      "physical link, with flits of different VCs interleaved on the wires. "
      "VCs serve three purposes:")
    bul(["**Head-of-line blocking relief**: a blocked packet in one VC no "
         "longer blocks packets behind it in another VC.",
         "**Routing deadlock avoidance**: on rings and tori a cyclic "
         "dependency between buffers can deadlock even with minimal "
         "routing; a 'dateline' that moves packets to a second VC when they "
         "cross it breaks the cycle.",
         "**Protocol (message-dependent) deadlock avoidance**: a slave that "
         "cannot send a response because the network is full of requests "
         "that wait for that slave deadlocks the system. Requests and "
         "responses must use separate VCs or physically separate networks. "
         "That is why AXI NoCs have separate request and response networks, "
         "and why CHI defines four channel classes (REQ, RSP, SNP, DAT)."])
    box("key", "Two kinds of deadlock",
        "**Routing deadlock** is a cycle in the channel-dependency graph of "
        "the network itself; it is removed by the routing function (XY, turn "
        "models) or by VCs with a dateline. **Protocol deadlock** is a cycle "
        "through the endpoints (request waits for response waits for "
        "request); it is removed by separating message classes and by "
        "guaranteeing that endpoints always sink responses. A NoC can be "
        "free of the first and still suffer the second.")
    h3("Router microarchitecture")
    p("A classic input-queued VC router processes a head flit in stages: "
      "**RC** (route computation), **VA** (virtual-channel allocation at "
      "the output), **SA** (switch allocation, a separable arbiter per "
      "input and output), **ST** (switch traversal) and **LT** (link "
      "traversal). Body flits skip RC and VA. Production routers use "
      "lookahead routing and speculation to cut this to one or two cycles "
      "per hop at the target frequency; the physical-design team decides "
      "how many pipeline stages the links need across the floorplan.")

    h2("Commercial NoCs and AMBA over a NoC")
    bul(["**Arteris FlexNoC** (non-coherent) and **Ncore** (coherent): NIUs "
         "for AXI, AHB, APB, OCP and others; a configurable transport with "
         "its own packet format; widely used in mobile and automotive SoCs.",
         "**Arm CoreLink NIC-400 / NI-700**: AMBA network interconnects for "
         "AXI/AHB/APB; **CMN-600/CMN-700** are CHI coherent mesh networks "
         "with crosspoints (XPs), HN-F slices and SN-F ports.",
         "In-house NoCs at large SoC vendors, often generated from a "
         "topology description, plus chiplet extensions over UCIe "
         "(Chapter 22)."])
    p("Transporting AXI over a NoC raises questions the NIU must answer: "
      "**ordering** (per-ID order across different destinations: the "
      "initiator NIU either stalls or reorders responses), **ID "
      "compression** (map wide AXI IDs to small NoC transaction tags), "
      "**4KB and burst splitting** (large bursts may be chopped into "
      "several packets), **QoS** (AxQOS to packet priority, with "
      "bandwidth regulators and pressure propagation), **clock and power "
      "domains** (asynchronous links and power-down handshakes inside the "
      "NoC), **security** (firewalls in the target NIU) and **safety** "
      "(ECC or parity on flits, duplicated routers for ASIL D).")

    h2("Protocol comparison")
    tbl(["Protocol", "Topology", "Outstanding / ordering", "Bursts", "Coherent",
         "Typical use"],
        [["APB", "Bridge + decoder", "1, in order", "No", "No", "Registers"],
         ["AHB-Lite / AHB5", "Bus, multi-layer matrix", "1 pipelined", "INCR/WRAP, 1KB",
          "No", "MCUs, peripheral subsystems"],
         ["AXI4", "Crossbar / NoC", "Many, per-ID order", "Up to 256, 4KB",
          "No (ACE: yes)", "SoC backbone"],
         ["AXI4-Lite", "Crossbar", "In order", "No", "No", "FPGA register access"],
         ["AXI4-Stream", "Point to point", "N/A (stream)", "Packets (TLAST)",
          "No", "Data paths, video, DMA"],
         ["ACE / ACE-Lite", "Snooping interconnect", "Many", "Cache lines",
          "Yes / I/O", "CPU clusters (AMBA 4)"],
         ["CHI", "Mesh NoC", "Many, retry and credits", "Cache lines", "Yes",
          "Servers, high-end mobile"],
         ["Wishbone B4", "Shared bus / crossbar", "1 (classic), queue "
          "(pipelined)", "Via CTI/BTE", "No", "Open-source IP, LiteX"],
         ["Avalon-MM", "Platform Designer fabric", "Pipelined reads, in order",
          "burstcount", "No", "Intel FPGA"],
         ["TileLink", "Crossbar / NoC", "Many (source IDs)", "Power-of-2 sizes",
          "TL-C: yes", "RISC-V SoCs, OpenTitan"],
         ["OCP", "Sonics NoC etc.", "Threads/tags", "Configurable", "Optional",
          "Legacy SoCs"]],
        widths=[15, 17, 19, 15, 12, 22], bold_first=True,
        caption="On-chip protocols at a glance (see Appendix A for the full "
                "quick-reference).")

    h2("Hands-on: a 3x3 mesh of XY wormhole routers")
    p("`xy_router` has five ports (local, north, east, south, west), a "
      "2-flit input buffer per port, XY route computation on the head flit "
      "and a per-output **lock**: when a head flit wins round-robin "
      "arbitration for an output, that output stays allocated to the same "
      "input until the tail flit has passed, which is wormhole switching. "
      "Links use valid/ready with READY = 'buffer not full'. `mesh3x3` "
      "instantiates nine routers with generate loops and ties off the mesh "
      "edges. Flits are 24 bits: head/tail flags, destination (x, y) and, "
      "for checking, a source/sequence tag in every flit.")
    _v("noc", "xy_router (5-port wormhole router, XY routing) and mesh3x3.")
    p("Every node injects 40 packets of 1 to 4 flits to random destinations "
      "with random gaps, all nodes concurrently. The ejection side checks "
      "that each packet arrives whole, in order, at the right node, with the "
      "right payload, and measures the latency from head injection to tail "
      "ejection as a function of hop count. A monitor traces the links used "
      "by one 3-flit packet from node (0,0) to node (2,1).")
    _v("noc_tb", "Testbench: concurrent random traffic on all nine nodes, "
                 "packet integrity checks, latency statistics and a link "
                 "trace.")
    _o("noc", "Real Icarus Verilog output.")
    bul(["The traced packet goes **east, east, then north**: XY routing "
         "finishes the X dimension first. Each hop costs 2 cycles here (one "
         "to buffer the flit, one to win the output), and the body and tail "
         "follow the head one cycle apart: a worm spanning three routers at "
         "cycle 7.",
         "Between cycles 9 and 13 the head waits inside router (2,1), whose "
         "local output is held by another packet; the tail waits one router "
         "behind and only crosses (2,0) -> north at cycle 14. The whole worm "
         "stalls in place without losing a flit.",
         "All 360 packets arrived intact with zero errors: no deadlock, no "
         "interleaving of packets on an output, correct payload order.",
         "Average latency rises by about 3 cycles per hop (9.4, 12.7, 15.5, "
         "18.4 cycles for 1-4 hops): 2 cycles of router pipeline plus "
         "queueing under load, plus the serialization of up to 4 flits."])
    box("warn", "PITFALL: releasing the lock on the wrong flit",
        "A wormhole router that releases its output allocation on a flit "
        "count instead of the tail flag, or that re-arbitrates an output while "
        "the current packet's input buffer is momentarily empty, interleaves "
        "flits of two packets on the same link. Downstream the packet "
        "structure is destroyed and the error surfaces far away, as a "
        "corrupted AXI burst at some target. Protocol checkers on every NoC "
        "link (head...tail contiguity per VC) find this in the first minutes "
        "of simulation.")

    h2("Summary")
    bul(["Wishbone B4 is the minimal open bus (CYC/STB/ACK), with classic "
         "and pipelined (STALL) modes and registered-feedback bursts.",
         "Avalon-MM (waitrequest, readdatavalid, burstcount) and Avalon-ST "
         "(readyLatency, empty, SOP/EOP) are Intel FPGA's equivalents of "
         "AXI4 and AXI4-Stream.",
         "TileLink has five channels (A-E), three conformance levels (TL-UL, "
         "TL-UH, TL-C) and a channel-priority rule for deadlock freedom; OCP "
         "and CoreConnect are legacy but still met in old IP.",
         "NoCs packetize transactions into flits, route them (XY on a mesh), "
         "use wormhole switching and credit-based flow control, and use "
         "virtual channels and separate message classes against routing and "
         "protocol deadlock.",
         "The 3x3 mesh delivered 360 random packets intact, showing wormhole "
         "stalls and latency growing with hop count."])

    h2("Exercises")
    bul(["Convert `wb_regs` to Wishbone pipelined mode: STALL low always, one "
         "request per cycle, ACK one cycle later. Write a testbench that "
         "issues four back-to-back reads with CYC held high.",
         "Map an AXI4 INCR8 read burst onto Avalon-MM and onto TileLink TL-UH. "
         "Which fields carry the length and the ID in each?",
         "Draw the channel-dependency graph of a 2x2 mesh with XY routing and "
         "show it is acyclic. Then add a single Y-then-X route and find the "
         "cycle.",
         "A router input has a 1-cycle link, 1-cycle credit return and "
         "1-cycle internal pipeline. How many flit buffers per VC are needed "
         "for full throughput? What happens to throughput with 2 buffers?",
         "Modify `noc_tb` so that every node sends to node (2,2) (a hotspot). "
         "Predict and then measure the latency and the throughput of the "
         "ejection port.",
         "Explain why AXI over a NoC with adaptive routing needs a reorder "
         "buffer in the initiator NIU, and size it for 16 outstanding "
         "64-byte reads."])


