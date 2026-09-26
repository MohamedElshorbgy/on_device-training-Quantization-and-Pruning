"""Appendices A-D of "Communication Protocols for SoC & ASIC - The Complete Guide".

A  Protocol comparison quick reference (with a Python-verified CRC table)
B  Glossary
C  100 communication-protocol interview questions with answers
D  Specifications, standards bodies and resources

The CRC table in Appendix A was produced by a generic bit-serial CRC model
(Python 3) and every "123456789" check value was compared with the published
catalogue value; the run output is pasted verbatim.
"""

from proto_guide.common import *  # noqa: F401,F403


# =============================================================================
# Appendix A - quick reference
# =============================================================================
_CRC_PY = [
    "# Generic bit-serial CRC (Rocksoft/Williams model) and catalogue check.",
    "def crc(data, w, poly, init, refin, refout, xorout):",
    "    top, mask = 1 << (w - 1), (1 << w) - 1",
    "    reg = init",
    "    for byte in data:",
    "        if refin:",
    "            byte = int(f\"{byte:08b}\"[::-1], 2)",
    "        for i in range(7, -1, -1):",
    "            fb = ((reg & top) != 0) ^ ((byte >> i) & 1)",
    "            reg = ((reg << 1) & mask) ^ (poly if fb else 0)",
    "    if refout:",
    "        reg = int(f\"{reg:0{w}b}\"[::-1], 2)",
    "    return reg ^ xorout",
    "",
    "# name, width, poly, init, refin, refout, xorout, expected check",
    "T = [",
    "    (\"CRC-5/USB\",        5, 0x05,       0x1F,       1, 1, 0x1F,       0x19),",
    "    (\"CRC-7/MMC\",        7, 0x09,       0x00,       0, 0, 0x00,       0x75),",
    "    (\"CRC-8/SMBUS\",      8, 0x07,       0x00,       0, 0, 0x00,       0xF4),",
    "    (\"CRC-8/MAXIM-DOW\",  8, 0x31,       0x00,       1, 1, 0x00,       0xA1),",
    "    (\"CRC-8/SAE-J1850\",  8, 0x1D,       0xFF,       0, 0, 0xFF,       0x4B),",
    "    (\"CRC-11/FLEXRAY\",  11, 0x385,      0x01A,      0, 0, 0x000,      0x5A3),",
    "    (\"CRC-15/CAN\",      15, 0x4599,     0x0000,     0, 0, 0x0000,     0x059E),",
    "    (\"CRC-16/USB\",      16, 0x8005,     0xFFFF,     1, 1, 0xFFFF,     0xB4C8),",
    "    (\"CRC-16/XMODEM\",   16, 0x1021,     0x0000,     0, 0, 0x0000,     0x31C3),",
    "    (\"CRC-16/KERMIT\",   16, 0x1021,     0x0000,     1, 1, 0x0000,     0x2189),",
    "    (\"CRC-16/IBM-SDLC\", 16, 0x1021,     0xFFFF,     1, 1, 0xFFFF,     0x906E),",
    "    (\"CRC-16/MCRF4XX\",  16, 0x1021,     0xFFFF,     1, 1, 0x0000,     0x6F91),",
    "    (\"CRC-17/CAN-FD\",   17, 0x1685B,    0x00000,    0, 0, 0x00000,    0x04F03),",
    "    (\"CRC-21/CAN-FD\",   21, 0x102899,   0x000000,   0, 0, 0x000000,   0x0ED841),",
    "    (\"CRC-24/BLE\",      24, 0x00065B,   0x555555,   1, 1, 0x000000,   0xC25A56),",
    "    (\"CRC-24/FLEXRAY-A\",24, 0x5D6DCB,   0xFEDCBA,   0, 0, 0x000000,   0x7979BD),",
    "    (\"CRC-32/ISO-HDLC\", 32, 0x04C11DB7, 0xFFFFFFFF, 1, 1, 0xFFFFFFFF, 0xCBF43926),",
    "    (\"CRC-32/ISCSI\",    32, 0x1EDC6F41, 0xFFFFFFFF, 1, 1, 0xFFFFFFFF, 0xE3069283),",
    "]",
    "msg = b\"123456789\"",
    "fails = 0",
    "for name, w, poly, init, ri, ro, xo, exp in T:",
    "    got = crc(msg, w, poly, init, ri, ro, xo)",
    "    ok = got == exp",
    "    fails += not ok",
    "    d = (w + 3) // 4",
    "    print(f\"{name:17s} w={w:2d} poly=0x{poly:0{d}X} check=0x{got:0{d}X} \"",
    "          f\"expect=0x{exp:0{d}X} {'PASS' if ok else 'FAIL'}\")",
    "import binascii, zlib",
    "print(f\"cross-check zlib.crc32      = 0x{zlib.crc32(msg):08X}\")",
    "print(f\"cross-check binascii.crc_hqx= 0x{binascii.crc_hqx(msg, 0):04X} (XMODEM)\")",
    "print(f\"{len(T) - fails}/{len(T)} catalogue check values reproduced\")",
]

_CRC_OUT = [
    "$ python3 crc_check.py",
    "CRC-5/USB         w= 5 poly=0x05 check=0x19 expect=0x19 PASS",
    "CRC-7/MMC         w= 7 poly=0x09 check=0x75 expect=0x75 PASS",
    "CRC-8/SMBUS       w= 8 poly=0x07 check=0xF4 expect=0xF4 PASS",
    "CRC-8/MAXIM-DOW   w= 8 poly=0x31 check=0xA1 expect=0xA1 PASS",
    "CRC-8/SAE-J1850   w= 8 poly=0x1D check=0x4B expect=0x4B PASS",
    "CRC-11/FLEXRAY    w=11 poly=0x385 check=0x5A3 expect=0x5A3 PASS",
    "CRC-15/CAN        w=15 poly=0x4599 check=0x059E expect=0x059E PASS",
    "CRC-16/USB        w=16 poly=0x8005 check=0xB4C8 expect=0xB4C8 PASS",
    "CRC-16/XMODEM     w=16 poly=0x1021 check=0x31C3 expect=0x31C3 PASS",
    "CRC-16/KERMIT     w=16 poly=0x1021 check=0x2189 expect=0x2189 PASS",
    "CRC-16/IBM-SDLC   w=16 poly=0x1021 check=0x906E expect=0x906E PASS",
    "CRC-16/MCRF4XX    w=16 poly=0x1021 check=0x6F91 expect=0x6F91 PASS",
    "CRC-17/CAN-FD     w=17 poly=0x1685B check=0x04F03 expect=0x04F03 PASS",
    "CRC-21/CAN-FD     w=21 poly=0x102899 check=0x0ED841 expect=0x0ED841 PASS",
    "CRC-24/BLE        w=24 poly=0x00065B check=0xC25A56 expect=0xC25A56 PASS",
    "CRC-24/FLEXRAY-A  w=24 poly=0x5D6DCB check=0x7979BD expect=0x7979BD PASS",
    "CRC-32/ISO-HDLC   w=32 poly=0x04C11DB7 check=0xCBF43926 expect=0xCBF43926 PASS",
    "CRC-32/ISCSI      w=32 poly=0x1EDC6F41 check=0xE3069283 expect=0xE3069283 PASS",
    "cross-check zlib.crc32      = 0xCBF43926",
    "cross-check binascii.crc_hqx= 0x31C3 (XMODEM)",
    "18/18 catalogue check values reproduced",
]


def _appx_a():
    appendix("Protocol Comparison Quick Reference")
    p("Dense look-up tables for the protocols of this book. Numbers are the "
      "headline figures of the public specifications or widely published "
      "summaries of them; where a spec leaves a value to the implementation "
      "(or where vendors routinely exceed it) the table says __typically__. "
      "Chapter numbers in parentheses point to the in-depth treatment. "
      "Speeds of the newest generations are marked (*) - they move fast, "
      "so check the current spec revision before quoting them in a design "
      "review.")

    ah2("On-chip buses (Chapters 5-10)")
    tbl(["Bus", "Channels / phases", "Pipelining", "Bursts",
         "Outstanding / ordering", "Typical use"],
        [["APB (APB3/4/5)", "One shared address+data transfer: SETUP then "
          "ACCESS phase; `PSEL PENABLE PWRITE PADDR PWDATA PRDATA PREADY "
          "PSLVERR`", "None: >= 2 cycles per transfer",
          "None", "1; strictly in order",
          "Peripheral control/status registers (5)"],
         ["AHB / AHB-Lite (AHB5)", "Address phase and data phase; "
          "`HTRANS HADDR HBURST HSIZE HWRITE HREADY HRESP`",
          "Address of N+1 overlaps data of N", "SINGLE, INCR, INCR4/8/16, "
          "WRAP4/8/16; 1 KB boundary", "1 in data phase; in order; "
          "HREADY stalls", "MCU system bus, legacy memory buses (6)"],
         ["AXI3 / AXI4 (AXI5)", "5 independent channels AW, W, B, AR, R; "
          "VALID/READY on each", "Fully decoupled; address ahead of data",
          "INCR 1-256 beats (AXI3: 16), WRAP 2/4/8/16, FIXED 1-16; "
          "no 4 KB crossing", "Many; per-ID ordering, different IDs may "
          "complete out of order", "High-performance interconnect, DMA, "
          "DDR ports (7)"],
         ["AXI4-Lite", "Same 5 channels, no ID/LEN/SIZE fields",
          "Channel-decoupled", "Single beat only",
          "Usually 1 (protocol allows more, in order)",
          "Register slaves, CSR blocks (8)"],
         ["AXI4-Stream", "One channel: `TVALID TREADY TDATA TLAST TKEEP "
          "TSTRB TID TDEST TUSER`", "Every beat", "Unbounded packets marked "
          "by TLAST", "N/A (no addresses)", "DSP, video, network datapaths "
          "(8)"],
         ["ACE / ACE-Lite", "AXI + snoop channels AC (address), CR "
          "(response), CD (data)", "As AXI", "Cache-line bursts",
          "Many; barriers, 5-state lines UC/UD/SC/SD/I",
          "Cluster-level coherency; ACE-Lite for IO-coherent masters (9)"],
         ["CHI (B-E)", "Packetised layers (protocol, network, link); "
          "channels REQ, RSP, SNP, DAT per direction", "Flit pipelined, "
          "credit-based link", "Cache-line transactions", "Many; TxnID "
          "based, home-node ordering", "Mesh coherent interconnect, "
          "many-core servers (9)"],
         ["Wishbone B4", "Classic `CYC STB WE ACK` (+`STALL` in pipelined "
          "mode)", "Pipelined mode only", "Registered-feedback bursts "
          "(CTI/BTE)", "Pipelined: several; in order",
          "Open-source SoCs, FPGA (10)"],
         ["Avalon-MM / -ST", "`address read write waitrequest "
          "readdatavalid burstcount`", "Pipelined reads (readdatavalid)",
          "burstcount", "Several reads; in order", "Intel FPGA "
          "Platform Designer systems (10)"],
         ["TileLink (UL/UH/C)", "Channels A, B, C, D, E; TL-UL uses A and "
          "D only", "Channel-decoupled, ready/valid", "TL-UH/TL-C: "
          "multi-beat (power-of-2 size)", "Many; per-source ID",
          "RISC-V SoCs (Rocket/Chipyard); TL-C is coherent (10)"]],
        widths=[13, 22, 14, 16, 18, 17], bold_first=True)
    box("tip", "How to read the table in an interview",
        ["The two questions that separate the buses are __how many "
         "transactions can be in flight__ (1 for APB/AHB, many for "
         "AXI/CHI/TileLink) and __does the protocol carry coherency "
         "messages__ (ACE, CHI, TL-C). Everything else - widths, burst "
         "types - follows from those two design choices."])

    ah2("Low-speed peripheral and field buses (Chapters 11-16)")
    tbl(["Protocol", "Wires", "Max speed (typ.)", "Duplex", "Topology",
         "Addressing", "Error check"],
        [["UART (RS-232/485 PHY)", "TX, RX (+RTS/CTS); RS-485: 1 diff pair",
          "115.2 kbaud common; a few Mbaud typical max", "Full (RS-485 "
          "2-wire: half)", "Point-to-point (RS-485: multi-drop)", "None "
          "(9-bit mode in multi-drop)", "Optional parity, framing error"],
         ["SPI", "SCLK, COPI (MOSI), CIPO (MISO), CS_n per target",
          "Tens of MHz; ~50-100 MHz typical", "Full", "1 controller, "
          "star of CS lines or daisy chain", "Chip select", "None in "
          "protocol"],
         ["Quad/Octal SPI, xSPI", "CLK, CS_n, IO0-3 (or IO0-7) + DQS",
          "~100-200 MHz, SDR or DDR (xSPI: DDR up to ~400 MB/s)",
          "Half", "Controller + 1 flash per CS", "Command + address in "
          "frame", "Optional (device-specific ECC/CRC)"],
         ["I2C", "SCL, SDA (open drain, pull-ups)", "100 k / 400 k / "
          "1 M (Fm+) / 3.4 M (Hs); 5 M UFm (one-way)", "Half",
          "Multi-controller, multi-drop", "7- or 10-bit", "ACK/NACK only "
          "(SMBus adds CRC-8 PEC)"],
         ["I3C", "SCL (push-pull), SDA", "12.5 MHz SDR; HDR modes higher "
          "(HDR-DDR ~2x)", "Half", "Multi-drop, 1 active controller",
          "Dynamic 7-bit (ENTDAA)", "T-bit parity (SDR); CRC-5 (HDR-DDR)"],
         ["CAN (Classical)", "CAN_H, CAN_L differential", "1 Mb/s (at "
          "~40 m)", "Half", "Multi-master bus, 120 ohm ends", "11- or "
          "29-bit message ID", "CRC-15, stuffing, form, ACK, bit monitor"],
         ["CAN FD", "Same", "Arbitration <= 1 Mb/s; data typically 2-8 "
          "Mb/s", "Half", "As CAN", "As CAN", "CRC-17/21 + stuff count"],
         ["LIN", "1 wire (+GND, 12 V battery level)", "20 kb/s",
          "Half", "1 commander, up to ~16 responders", "6-bit frame ID "
          "+ 2 parity", "8-bit inverted checksum (classic/enhanced)"],
         ["I2S", "SCK (BCLK), WS (LRCLK), SD (+MCLK)", "e.g. 3.072 MHz "
          "(48 kHz x 2 x 32 bit)", "Simplex per data line", "Point-to-"
          "point", "None (slot by WS)", "None"],
         ["1-Wire", "DQ + GND (parasite power)", "~16 kb/s standard, "
          "~140 kb/s overdrive", "Half", "Multi-drop", "64-bit ROM ID",
          "CRC-8/MAXIM"],
         ["MDIO (Clause 22/45)", "MDC, MDIO", "2.5 MHz per 802.3 (many "
          "PHYs faster)", "Half", "1 station manager, up to 32 PHYs",
          "C22: 5-bit PHY + 5-bit reg; C45: +5-bit MMD, 16-bit reg",
          "None (turnaround bits only)"]],
        widths=[13, 17, 18, 9, 15, 14, 14], bold_first=True)

    ah2("High-speed serial links (Chapters 17-22)")
    tbl(["Link", "Rate per lane", "Encoding", "Lanes", "Reach (typ.)"],
        [["USB 1.1 LS / FS", "1.5 / 12 Mb/s", "NRZI + bit stuffing",
          "1 half-duplex D+/D-", "3 m (LS) / 5 m cable"],
         ["USB 2.0 HS", "480 Mb/s", "NRZI + bit stuffing", "1 half-duplex "
          "pair", "5 m cable"],
         ["USB 3.2 Gen 1 / Gen 2", "5 / 10 Gb/s", "8b/10b / 128b/132b",
          "1 TX + 1 RX pair (x2: 20 Gb/s on Type-C)", "~1-3 m cable "
          "(passive)"],
         ["USB4 v1 (Gen 2 / Gen 3)", "10 / 20 Gb/s", "64b/66b / "
          "128b/132b (+RS-FEC at Gen 3)", "2 lanes -> 20 / 40 Gb/s", "~0.8 m "
          "passive at 40G"],
         ["USB4 v2 (Gen 4) (*)", "40 Gb/s (PAM3)", "11b/7T PAM3 + FEC",
          "2 lanes -> 80 Gb/s (120/40 asymmetric)", "~1 m passive"],
         ["PCIe 1.x / 2.x", "2.5 / 5 GT/s", "8b/10b", "x1-x16 (x32 in "
          "early specs)", "~0.3-0.5 m FR4 channel"],
         ["PCIe 3.x / 4.0 / 5.0", "8 / 16 / 32 GT/s", "128b/130b",
          "x1-x16", "Loss budget ~22 / 28 / 36 dB at Nyquist; retimers "
          "beyond"],
         ["PCIe 6.x / 7.0 (*)", "64 / 128 GT/s (PAM4)", "1b/1b FLIT mode "
          "+ light FEC + CRC", "x1-x16", "~32-36 dB class channels"],
         ["Ethernet 10/100/1000BASE-T", "10 M / 100 M / 1 G", "Manchester / "
          "4B5B+MLT-3 / PAM5 (4 pairs)", "1-4 twisted pairs", "100 m"],
         ["10GBASE-R / 25GBASE-R", "10.3125 / 25.78125 GBd", "64b/66b "
          "(+RS-FEC at 25G)", "1 per direction", "Backplane ~1 m, "
          "optics km"],
         ["50/100/200 G per lane Ethernet (*)", "26.6 / 53.1 / 106.25 GBd "
          "PAM4", "64b/66b -> 256b/257b + RS(544,514) FEC", "1-8 (200G-"
          "1.6T ports)", "Host ~ tens of cm; optics"],
         ["MIPI D-PHY v1.2 / v2.x", "Up to 2.5 / 4.5 Gb/s", "None (raw, "
          "HS/LP modes)", "1 clock + 1-4 data lanes", "Tens of cm "
          "(in-phone flex)"],
         ["MIPI C-PHY v1.x / v2.x (*)", "Up to ~2.5 / ~6 Gsym/s "
          "(x 2.28 bit/sym)", "16 bits -> 7 symbols, 3-wire trios",
          "1-3 trios, embedded clock", "Tens of cm"],
         ["HDMI 1.4 / 2.0 (TMDS)", "3.4 / 6 Gb/s", "TMDS 8b/10b variant",
          "3 data + 1 clock", "~5-10 m cable"],
         ["HDMI 2.1 FRL / 2.2 (*)", "12 / 24 Gb/s", "16b/18b + RS FEC",
          "4 lanes -> 48 / 96 Gb/s", "~2-5 m (Ultra High Speed cable)"],
         ["DisplayPort 1.4 (HBR3)", "8.1 Gb/s", "8b/10b", "1, 2 or 4 "
          "main lanes + AUX", "~2-3 m"],
         ["DisplayPort 2.x (UHBR10/13.5/20)", "10 / 13.5 / 20 Gb/s",
          "128b/132b", "Up to 4 lanes -> 80 Gb/s", "~1-2 m at UHBR20"],
         ["JESD204B", "Up to 12.5 Gb/s", "8b/10b", "1-32+ lanes",
          "Board level"],
         ["JESD204C", "Up to 32 Gb/s", "64b/66b (also 8b/10b, 64b/80b)",
          "1-32+ lanes", "Board level"],
         ["UCIe 1.x-2.0 / 3.0 (*)", "4-32 GT/s / up to 64 GT/s",
          "None on the wire; 256 B flits with CRC + retry in the D2D "
          "adapter", "x16 standard package, x64 (x32) advanced",
          "~25 mm standard, ~2 mm advanced package"]],
        widths=[22, 19, 24, 19, 16], bold_first=True)
    box("note", "GT/s versus Gb/s",
        ["GT/s counts line symbols (transfers) per second before coding "
         "overhead; Gb/s is usually payload bits. PCIe 3.0: 8 GT/s x "
         "128/130 = 7.88 Gb/s per lane per direction = 0.985 GB/s. For PAM4 "
         "links the baud rate is half the bit rate (2 bits per symbol)."])

    ah2("Memory interfaces (Chapter 20)")
    tbl(["Memory", "Data rate per pin", "Device / channel width",
         "Voltage (core/IO)", "Peak bandwidth per device (example)"],
        [["DDR4 (JESD79-4)", "1600-3200 MT/s", "x4 / x8 / x16 device; "
          "64-bit (+8 ECC) DIMM", "VDD = VDDQ 1.2 V, VPP 2.5 V",
          "x16 @ 3200: 6.4 GB/s; DIMM: 25.6 GB/s"],
         ["DDR5 (JESD79-5)", "3200-6400 MT/s at launch, extended toward "
          "~8800 (*)", "x4 / x8 / x16; DIMM = 2 x 32-bit subchannels",
          "1.1 V (VPP 1.8 V); PMIC on DIMM", "x16 @ 6400: 12.8 GB/s; "
          "DIMM: 51.2 GB/s"],
         ["LPDDR4X (JESD209-4)", "Up to 4266 MT/s", "x16 channels "
          "(2 per die)", "VDD2 1.1 V, VDDQ 0.6 V", "x16 @ 4266: 8.5 GB/s"],
         ["LPDDR5 (JESD209-5)", "Up to 6400 MT/s", "x16 channels",
          "VDD2 ~1.05 V, VDDQ 0.5 V", "x16 @ 6400: 12.8 GB/s"],
         ["LPDDR5X (*)", "Up to 8533 MT/s (later bins ~9600-10700)",
          "x16 channels", "As LPDDR5 (lower VDD2 options)",
          "x16 @ 8533: 17.1 GB/s; x64 package: 68.3 GB/s"],
         ["GDDR6 (JESD250)", "Typically 14-20 Gb/s (NRZ)", "x32 device = "
          "2 x16 channels (x8 clamshell)", "1.35 V / 1.25 V",
          "16 Gb/s x 32: 64 GB/s"],
         ["GDDR7 (JESD239) (*)", "~28-32 Gb/s at launch, spec up to ~48 "
          "(PAM3)", "x32 device, 4 channels", "~1.2 / 1.1 V",
          "32 Gb/s x 32: 128 GB/s"],
         ["HBM2E", "3.2-3.6 Gb/s", "1024-bit stack, 8 x 128-bit channels",
          "1.2 V", "3.6 Gb/s: 460.8 GB/s per stack"],
         ["HBM3 (JESD238)", "6.4 Gb/s", "1024-bit, 16 x 64-bit channels "
          "(32 pseudo-channels)", "VDD 1.1 V, VDDQ 0.4 V",
          "819.2 GB/s per stack"],
         ["HBM3E (*)", "~8-9.8 Gb/s (vendor bins)", "1024-bit",
          "As HBM3", "9.6 Gb/s: 1228.8 GB/s per stack"],
         ["HBM4 (JESD270-4) (*)", "~8 Gb/s baseline", "2048-bit, 32 "
          "channels", "Vendor-specific options", "8 Gb/s: 2048 GB/s per "
          "stack"]],
        widths=[16, 21, 24, 18, 21], bold_first=True)
    eq(["Peak BW [GB/s] = data rate [MT/s or Gb/s per pin] x width [bits] / 8",
        "DDR5-6400 DIMM: 6400e6 x 64 / 8 = 51.2 GB/s  (sustained ~70-85%)",
        "HBM3 stack   : 6.4e9 x 1024 / 8 = 819.2 GB/s"],
        caption="Every peak number in the table is this one line; real "
                "efficiency is lower (refresh, turnarounds, page misses).")

    ah2("CRC polynomials per protocol (verified)")
    p("Parameters use the Rocksoft/Williams model that CRC catalogues use: "
      "__poly__ in normal (MSB-first) form without the implicit top bit, "
      "__init__ register preset, __refin/refout__ whether bytes enter and "
      "the result leaves LSB-first, and __xorout__ the final inversion. "
      "The __check__ column is the CRC of the ASCII string \"123456789\" - "
      "the universal self-test for a CRC implementation. Every check value "
      "below was reproduced by the Python script that follows and matched "
      "the published catalogue value (18/18 PASS). How a protocol maps "
      "fields onto the bit stream (which bits are covered, bit order on the "
      "wire, stuff bits) is protocol-specific - see the chapter.")
    tbl(["Protocol / use", "Catalogue name", "W", "Poly", "Init",
         "Refl.", "XorOut", "Check"],
        [["USB token / SOF (17)", "CRC-5/USB", "5", "0x05", "0x1F", "yes",
          "0x1F", "0x19"],
         ["SD/MMC command (20)", "CRC-7/MMC", "7", "0x09", "0x00", "no",
          "0x00", "0x75"],
         ["SMBus PEC; DDR4/5 write-CRC polynomial (13, 20)",
          "CRC-8/SMBUS", "8", "0x07", "0x00", "no", "0x00", "0xF4"],
         ["1-Wire ROM / scratchpad (16)", "CRC-8/MAXIM-DOW", "8", "0x31",
          "0x00", "yes", "0x00", "0xA1"],
         ["SAE J1850, AUTOSAR E2E CRC-8 (15)", "CRC-8/SAE-J1850", "8",
          "0x1D", "0xFF", "no", "0xFF", "0x4B"],
         ["FlexRay header (15)", "CRC-11/FLEXRAY", "11", "0x385", "0x01A",
          "no", "0x000", "0x5A3"],
         ["Classical CAN (15)", "CRC-15/CAN", "15", "0x4599", "0x0000",
          "no", "0x0000", "0x059E"],
         ["USB data packets (17)", "CRC-16/USB", "16", "0x8005", "0xFFFF",
          "yes", "0xFFFF", "0xB4C8"],
         ["SD data lines, XMODEM (20)", "CRC-16/XMODEM", "16", "0x1021",
          "0x0000", "no", "0x0000", "0x31C3"],
         ["IEEE 802.15.4, Bluetooth BR (-)", "CRC-16/KERMIT", "16",
          "0x1021", "0x0000", "yes", "0x0000", "0x2189"],
         ["HDLC / X.25 / PPP FCS-16 (3)", "CRC-16/IBM-SDLC", "16", "0x1021",
          "0xFFFF", "yes", "0xFFFF", "0x906E"],
         ["MIPI CSI-2 / DSI packet footer (21)", "CRC-16/MCRF4XX", "16",
          "0x1021", "0xFFFF", "yes", "0x0000", "0x6F91"],
         ["CAN FD, <= 16 data bytes (15)", "CRC-17/CAN-FD", "17",
          "0x1685B", "0x00000 (see note)", "no", "0x00000", "0x04F03"],
         ["CAN FD, > 16 data bytes (15)", "CRC-21/CAN-FD", "21",
          "0x102899", "0x000000 (see note)", "no", "0x000000", "0x0ED841"],
         ["Bluetooth LE link layer (-)", "CRC-24/BLE", "24", "0x00065B",
          "0x555555", "yes", "0x000000", "0xC25A56"],
         ["FlexRay frame, channel A (15)", "CRC-24/FLEXRAY-A", "24",
          "0x5D6DCB", "0xFEDCBA", "no", "0x000000", "0x7979BD"],
         ["Ethernet FCS, PCIe LCRC/ECRC poly, SATA, HDLC-32 (18, 19)",
          "CRC-32/ISO-HDLC", "32", "0x04C11DB7", "0xFFFFFFFF", "yes",
          "0xFFFFFFFF", "0xCBF43926"],
         ["iSCSI, SCTP, NVMe-oF data digest, ext4 (-)", "CRC-32/ISCSI "
          "(CRC-32C)", "32", "0x1EDC6F41", "0xFFFFFFFF", "yes",
          "0xFFFFFFFF", "0xE3069283"]],
        widths=[17, 17, 5, 14, 14, 5, 14, 14], bold_first=True)
    code(_CRC_PY, caption="crc_check.py - one generic bit-serial CRC engine "
         "reproduces every catalogue check value (the same shift-register "
         "structure as the RTL CRC generators of Chapters 3 and 26).")
    out(_CRC_OUT, caption="Real output (Python 3). zlib and binascii give "
        "independent cross-checks for CRC-32 and CRC-16/XMODEM.")
    box("warn", "PITFALL - same polynomial, different CRC",
        ["The CAN FD standard presets the CRC register with a 1 in its MSB "
         "and includes stuff bits in the calculation; the catalogue entries "
         "above use init = 0 over plain bytes, so they are a self-test of "
         "the polynomial engine, not a drop-in frame CRC. Likewise PCIe LCRC "
         "uses the Ethernet polynomial but its own bit mapping, and DDR4/5 "
         "write CRC uses x^{8}+x^{2}+x+1 over a JEDEC-defined bit matrix. "
         "Always validate against a known-good frame from the spec or an "
         "analyzer capture, not just \"123456789\"."])

    ah2("Line coding (Chapter 2)")
    tbl(["Code", "Bits -> symbols", "Overhead", "DC balance / run length",
         "Clock recovery", "Used by"],
        [["NRZ", "1 bit -> 1 level", "0%", "None / unbounded", "Needs "
          "scrambling or separate clock", "Parallel buses, SPI, DDR, "
          "most PAM2 SerDes after scrambling"],
         ["NRZI + bit stuffing", "1 -> no transition, 0 -> transition; "
          "stuff 0 after 6 ones", "0-16.7% (data-dependent)",
          "Not DC-balanced / max 7 bits", "Transitions guaranteed",
          "USB 1.x/2.0"],
         ["Manchester", "1 bit -> 2 half-bit levels", "100% (2x baud)",
          "Balanced / 1 bit", "Every bit has a mid transition",
          "10BASE-T, some RFID, DALI"],
         ["4B/5B (+ MLT-3)", "4 bits -> 5 bits; 3-level line", "25%",
          "Bounded run length", "Good", "100BASE-TX, FDDI"],
         ["8b/10b", "8 bits -> 10 bits, running disparity, K-codes",
          "25% (80% efficiency)", "Strict DC balance / max run 5",
          "Excellent; commas for alignment", "PCIe 1-2, USB 3 Gen 1, "
          "SATA, 1000BASE-X, DP 1.x, JESD204B"],
         ["TMDS", "8 bits -> 10 bits, transition-minimised", "25%",
          "DC balanced", "Separate clock channel", "HDMI 1.x-2.0, DVI"],
         ["64b/66b", "64 bits + 2-bit sync header, scrambled", "3.1%",
          "Statistical (scrambler) / sync header forces 1 transition per "
          "66 bits", "Good", "10G/25G/100G Ethernet, JESD204C, USB4 Gen 2"],
         ["128b/130b", "128 bits + 2-bit sync header, scrambled", "1.5%",
          "Statistical", "Good", "PCIe 3.0-5.0"],
         ["128b/132b", "128 bits + 4-bit header, scrambled", "3.0%",
          "Statistical", "Good", "USB 3.2 Gen 2, USB4 Gen 3, DP 2.x"],
         ["16b/18b", "16 bits + 2-bit header", "12.5%", "Statistical",
          "Good", "HDMI 2.1 FRL"],
         ["PAM4", "2 bits -> 1 of 4 levels (Gray coded)", "0% (needs FEC)",
          "Scrambled", "Half the baud of NRZ", "PCIe 6/7, 50-200 G/lane "
          "Ethernet, GDDR6X"],
         ["PAM3", "3 bits -> 2 ternary symbols (GDDR7); 11 b -> 7 trits "
          "(USB4 v2)", "~5% vs log2(3) ideal", "Scrambled", "Good",
          "GDDR7, USB4 v2, 100BASE-T1"],
         ["PAM5 / PAM16", "Multi-level with trellis/DSQ coding", "-",
          "Scrambled", "DSP-based", "1000BASE-T / 10GBASE-T"],
         ["C-PHY 3-phase", "16 bits -> 7 symbols on 3 wires", "2.28 "
          "bit/symbol", "Every symbol has a transition", "Embedded clock",
          "MIPI C-PHY"]],
        widths=[12, 22, 11, 18, 15, 22], bold_first=True)


# =============================================================================
# Appendix B - glossary
# =============================================================================
_GLOSS = [
    ("8b/10b", "DC-balanced line code mapping 8 data bits to 10-bit symbols "
     "with running disparity and control (K) characters (2)."),
    ("64b/66b", "Scrambled 64-bit block with a 2-bit sync header (01 data, "
     "10 control); 3% overhead (2, 19)."),
    ("128b/130b", "PCIe 3.0-5.0 encoding: 128-bit block plus 2-bit sync "
     "header (18)."),
    ("ACE", "AXI Coherency Extensions: adds snoop channels AC/CR/CD and "
     "cache-state signalling to AXI (9)."),
    ("ACK / NAK", "Positive / negative acknowledgement; in PCIe DLLPs that "
     "retire or replay TLPs from the replay buffer (3, 18)."),
    ("AER", "PCIe Advanced Error Reporting capability (18)."),
    ("AHB", "AMBA Advanced High-performance Bus: pipelined address/data "
     "phases, single outstanding transfer (6)."),
    ("Alternate mode", "USB Type-C mechanism that hands SuperSpeed wires to "
     "DisplayPort or Thunderbolt (17)."),
    ("AMBA", "Arm's Advanced Microcontroller Bus Architecture family: APB, "
     "AHB, AXI, ACE, CHI, ATB, DTI (5-9)."),
    ("APB", "AMBA Advanced Peripheral Bus: two-phase, non-pipelined "
     "register bus (5)."),
    ("Arbitration", "Deciding which requester wins a shared resource; "
     "bitwise (CAN, I2C) or logic-based (interconnect) (3, 15)."),
    ("ATB", "AMBA Trace Bus carrying trace data to funnels and sinks (23)."),
    ("AUX channel", "DisplayPort half-duplex side channel for link training, "
     "EDID and DPCD access (21)."),
    ("Avalon", "Intel FPGA on-chip interface family (Avalon-MM, "
     "Avalon-ST) (10)."),
    ("AXI", "AMBA Advanced eXtensible Interface: five independent "
     "VALID/READY channels, IDs and bursts (7)."),
    ("AXI4-Stream", "Address-less streaming interface with TVALID/TREADY/"
     "TLAST (8)."),
    ("Backpressure", "A receiver throttling the sender (READY low, credits "
     "exhausted, PAUSE frames) (3)."),
    ("Bathtub curve", "BER versus sampling phase; its opening at a target "
     "BER is the timing margin (2)."),
    ("Baud", "Symbols per second; equals bit rate only for 2-level "
     "signalling (2)."),
    ("BER", "Bit error ratio; SerDes specs typically require 1e-12 or "
     "better (pre-FEC targets are looser) (2)."),
    ("Bit stuffing", "Inserting a complementary bit after N identical bits "
     "to guarantee edges (CAN after 5, USB after 6 ones) (11, 15, 17)."),
    ("BoW", "Bunch of Wires: OCP (Open Compute) die-to-die parallel "
     "interface (22)."),
    ("Boundary scan", "IEEE 1149.1 chain of cells at the pins, used to test "
     "board interconnect (23)."),
    ("BTA", "MIPI D-PHY Bus Turn-Around handing the lane to the other side "
     "(21)."),
    ("Burst", "Several data beats for one address phase (6, 7)."),
    ("CAN", "Controller Area Network, ISO 11898; multi-master differential "
     "bus with bitwise arbitration (15)."),
    ("CAN FD", "CAN with Flexible Data rate: up to 64 data bytes and a "
     "faster data phase (15)."),
    ("CAN XL", "Third CAN generation: up to 2048 data bytes, data phase "
     "typically 10-20 Mb/s (15)."),
    ("CDC", "Clock domain crossing; synchronizers and async FIFOs (4)."),
    ("CDR", "Clock and data recovery: extracts a sampling clock from the "
     "data transitions (2)."),
    ("CHI", "AMBA Coherent Hub Interface: packetised, credit-based coherent "
     "protocol for meshes (9)."),
    ("Chip select", "Per-target enable line in SPI (12)."),
    ("Clock stretching", "I2C target holding SCL low to delay the "
     "controller (13)."),
    ("CMN", "Arm Coherent Mesh Network, a CHI interconnect (9)."),
    ("Comma", "8b/10b symbol (K28.5) whose bit pattern cannot appear across "
     "symbol boundaries; used for alignment (2)."),
    ("Completer", "PCIe device that services a request (18)."),
    ("Compliance test", "Standardised test suite a product must pass for "
     "certification/logo (25)."),
    ("Controller / target", "Current I2C/SPI/I3C terms replacing "
     "master/slave (12-14)."),
    ("CoreSight", "Arm debug and trace architecture (DAP, CTI, ETM, "
     "funnels) (23)."),
    ("CPOL / CPHA", "SPI clock polarity and phase; four modes 0-3 (12)."),
    ("C-PHY", "MIPI 3-wire, 3-phase PHY with embedded clock (21)."),
    ("CRC", "Cyclic redundancy check: remainder of polynomial division "
     "over GF(2) (3, 26)."),
    ("Credit-based flow control", "Sender may transmit only while it holds "
     "credits advertised by the receiver (PCIe, CHI, UCIe) (3)."),
    ("CSI-2", "MIPI Camera Serial Interface 2 protocol layer (21)."),
    ("CTLE", "Continuous-time linear equaliser in a SerDes receiver (2)."),
    ("CXL", "Compute Express Link: CXL.io, CXL.cache and CXL.mem over the "
     "PCIe PHY (18)."),
    ("D2D adapter", "UCIe layer that adds CRC, retry and arbitration "
     "between protocol and PHY (22)."),
    ("DAP", "Arm Debug Access Port reached through JTAG or SWD (23)."),
    ("DBI", "Data bus inversion: inverting a byte to reduce transitions or "
     "zeros (DDR4, GDDR) (20)."),
    ("DDR", "Double data rate: data on both clock edges; also the JEDEC "
     "DRAM family (20)."),
    ("Deadlock", "Circular wait between agents or channels; prevented by "
     "ordering rules and virtual channels (3, 9)."),
    ("Decision feedback equaliser (DFE)", "Receiver equaliser that "
     "subtracts ISI of already-decided bits (2)."),
    ("De-emphasis", "Transmitter FIR that attenuates repeated bits to "
     "pre-compensate channel loss (2)."),
    ("DFI", "DDR PHY Interface between memory controller and PHY (20)."),
    ("Differential signalling", "Information carried as the difference of "
     "two complementary wires; rejects common-mode noise (2)."),
    ("DLLP", "PCIe Data Link Layer Packet: ACK/NAK, flow control, power "
     "management (18)."),
    ("DMA", "Direct memory access engine moving data without the CPU (24)."),
    ("DP (DisplayPort)", "VESA packetised display link with AUX channel "
     "(21)."),
    ("DQS", "DDR data strobe, source-synchronous with DQ (20)."),
    ("DSI", "MIPI Display Serial Interface (21)."),
    ("ECC", "Error correcting code, e.g. SECDED Hamming on memory (3, 26)."),
    ("ECRC", "PCIe end-to-end CRC on a TLP (18)."),
    ("EDID", "Extended Display Identification Data read over DDC (I2C) "
     "(21)."),
    ("Elastic buffer", "FIFO absorbing ppm frequency offset using SKP/idle "
     "insertion and deletion (2, 18)."),
    ("Embedded clock", "Clock recovered from data transitions rather than "
     "sent on its own wire (2)."),
    ("Endpoint", "USB: addressable buffer in a device; PCIe: a function at "
     "the leaf of the hierarchy (17, 18)."),
    ("ENTDAA", "I3C broadcast command that assigns dynamic addresses (14)."),
    ("Enumeration", "Host discovering and configuring devices (USB, PCIe) "
     "(17, 18)."),
    ("Equalisation", "TX FIR plus RX CTLE/DFE compensating channel loss "
     "(2)."),
    ("Exclusive access", "AXI/AHB load-exclusive/store-exclusive "
     "monitor-based atomic mechanism (7)."),
    ("Eye diagram", "Overlay of unit intervals showing voltage and timing "
     "margin (2)."),
    ("FEC", "Forward error correction, e.g. RS(544,514) in Ethernet (19, "
     "26)."),
    ("FIFO", "First-in first-out buffer; async FIFOs cross clock domains "
     "(4)."),
    ("FLIT", "Flow control unit: fixed-size link-layer packet (CHI, PCIe 6 "
     "FLIT mode, UCIe) (9, 18, 22)."),
    ("FlexRay", "Deterministic TDMA automotive bus at 10 Mb/s (15)."),
    ("Frame", "Delimited unit of transfer at the link layer (Ethernet, "
     "CAN, UART) (3)."),
    ("GDDR", "Graphics DDR DRAM family with high per-pin rates (20)."),
    ("Gray code", "Code in which consecutive values differ by one bit; used "
     "for async FIFO pointers and PAM4 levels (2, 4)."),
    ("GT/s", "Giga-transfers per second (symbol rate before coding) (18)."),
    ("Handshake", "Signal exchange that qualifies a transfer, e.g. "
     "VALID/READY, REQ/ACK (3)."),
    ("HBM", "High Bandwidth Memory: 3D-stacked DRAM with 1024-bit or wider "
     "interface on an interposer (20)."),
    ("HDCP", "High-bandwidth Digital Content Protection on HDMI/DP (26)."),
    ("HDMI", "High-Definition Multimedia Interface (21)."),
    ("HDR (I3C)", "I3C High Data Rate modes (HDR-DDR, HDR-BT, ...) (14)."),
    ("Hot plug", "Attaching a device while powered; detection via HPD, "
     "VBUS or presence pins (17, 21)."),
    ("I2C", "Inter-Integrated Circuit two-wire open-drain bus (NXP "
     "UM10204) (13)."),
    ("I2S", "Inter-IC Sound serial audio bus (16)."),
    ("I3C", "MIPI Improved Inter-Integrated Circuit: push-pull, in-band "
     "interrupts, dynamic addressing (14)."),
    ("IBI", "I3C In-Band Interrupt raised by a target on SDA (14)."),
    ("IDE", "PCIe Integrity and Data Encryption (AES-GCM on TLPs) (26)."),
    ("IEEE 1500", "Standard for embedded core test wrappers (23)."),
    ("IEEE 1588 (PTP)", "Precision Time Protocol for sub-microsecond clock "
     "sync over Ethernet (19)."),
    ("IEEE 1687 (IJTAG)", "Access network for embedded instruments using "
     "SIBs and ICL/PDL (23)."),
    ("IFG / IPG", "Ethernet inter-frame gap, minimum 96 bit times (19)."),
    ("Interleaving", "Spreading addresses over banks/channels to overlap "
     "accesses (20)."),
    ("Interposer", "Silicon or organic substrate connecting dies in a "
     "2.5D package (20, 22)."),
    ("ISI", "Inter-symbol interference caused by channel loss and "
     "reflections (2)."),
    ("Jitter", "Deviation of edges from ideal time; random (RJ) and "
     "deterministic (DJ) parts (2)."),
    ("JESD204", "JEDEC serial interface for data converters (B: 8b/10b, "
     "C: 64b/66b) (22)."),
    ("JTAG", "IEEE 1149.1 test access port: TCK, TMS, TDI, TDO, optional "
     "TRST (23)."),
    ("K-code", "8b/10b control symbol (COM, SKP, STP, ...) (2)."),
    ("Lane", "One differential pair per direction (or pair of pairs) of a "
     "serial link (2)."),
    ("Latency", "Time from request to response; with bandwidth sets "
     "outstanding requirements (Little's law) (7, 27)."),
    ("LCRC", "PCIe link CRC (32-bit) protecting a TLP hop by hop (18)."),
    ("LFSR", "Linear feedback shift register used for CRC, scramblers and "
     "PRBS (3)."),
    ("LIN", "Local Interconnect Network: single-wire 20 kb/s automotive "
     "bus (15)."),
    ("Link training", "Automatic negotiation of rate, width and "
     "equalisation (PCIe LTSSM, DP) (18, 21)."),
    ("LPDDR", "Low-power DDR DRAM for mobile (20)."),
    ("LTSSM", "PCIe Link Training and Status State Machine (18)."),
    ("LVDS", "Low-voltage differential signalling, ~350 mV swing (2)."),
    ("MAC", "Media Access Control layer (Ethernet framing, CRC, pause) "
     "(19)."),
    ("Manchester code", "Line code with a transition at mid-bit (2)."),
    ("MDIO", "Management Data I/O bus to Ethernet PHY registers (19)."),
    ("MESI / MOESI", "Cache coherence state protocols (9)."),
    ("Metastability", "Unresolved flop state after a setup/hold violation "
     "(4)."),
    ("MIPI", "MIPI Alliance: mobile interface specs (D-PHY, C-PHY, CSI-2, "
     "DSI, I3C) (14, 21)."),
    ("MLT-3", "Three-level line code cycling -1/0/+1 used by 100BASE-TX "
     "(19)."),
    ("MPS / MRRS", "PCIe Max Payload Size / Max Read Request Size (18)."),
    ("MSI / MSI-X", "Message-signalled interrupts as memory writes (18)."),
    ("Multi-drop", "Bus topology with several devices on the same wires "
     "(2)."),
    ("NoC", "Network-on-chip: packet-switched on-chip interconnect (10)."),
    ("NRZ", "Non-return-to-zero, two-level signalling (2)."),
    ("NRZI", "NRZ inverted: data encoded as presence/absence of a "
     "transition (17)."),
    ("OCP", "Open Core Protocol (OCP-IP; now under Accellera) socket "
     "standard (10)."),
    ("ONFI", "Open NAND Flash Interface (20)."),
    ("Open drain", "Output that only pulls low; high level from a pull-up "
     "resistor (13)."),
    ("Ordering model", "Rules on which transactions may pass others (AXI "
     "ID, PCIe relaxed ordering) (3, 7, 18)."),
    ("Outstanding transaction", "Request issued whose response has not yet "
     "returned (7)."),
    ("PAM4", "Four-level pulse-amplitude modulation, 2 bits per symbol "
     "(2)."),
    ("Parity", "Single-bit even/odd check detecting odd numbers of errors "
     "(3)."),
    ("PCIe", "PCI Express, packetised serial load/store interconnect "
     "(18)."),
    ("PCS", "Physical Coding Sublayer: encoding, scrambling, lane alignment "
     "(19)."),
    ("PHY", "Physical layer: analog front end plus PCS (2, 24)."),
    ("PIPE", "PHY Interface for PCI Express (and USB/SATA) between MAC and "
     "PHY (18, 24)."),
    ("PLL", "Phase-locked loop generating clocks from a reference (2)."),
    ("PMA", "Physical Medium Attachment: SerDes, CDR (19)."),
    ("PMBus", "Power Management Bus built on SMBus (13)."),
    ("Posted write", "Write needing no completion (PCIe memory write, AXI "
     "early response) (18)."),
    ("PRBS", "Pseudo-random bit sequence (PRBS7/15/31) for link test (2)."),
    ("Pre-emphasis", "TX boost of transitions to compensate loss (2)."),
    ("Preamble", "Known pattern before a frame for sync (Ethernet 7 x 0x55 "
     "+ SFD) (19)."),
    ("QSPI", "Quad SPI: four bidirectional data lines (12)."),
    ("Refresh", "Periodic DRAM row restore (tREFI ~3.9-7.8 us) (20)."),
    ("Repeated START", "I2C START without a preceding STOP (13)."),
    ("Replay buffer", "PCIe transmitter copy of unacknowledged TLPs (18)."),
    ("Retimer", "Active device that fully recovers and retransmits a link, "
     "resetting the jitter and loss budget (18)."),
    ("Root complex", "PCIe hierarchy root connecting CPU/memory (18)."),
    ("RS-232 / RS-485", "EIA/TIA electrical standards for UART links; "
     "single-ended / differential multi-drop (11)."),
    ("Running disparity", "8b/10b state tracking the ones-minus-zeros "
     "balance (2)."),
    ("Sample point", "Position within a bit where the receiver samples; "
     "CAN typically 75-87.5% (15)."),
    ("Scrambler", "LFSR XORed onto data to whiten the spectrum (2)."),
    ("SDR", "Single data rate (one transfer per clock) (2)."),
    ("SerDes", "Serializer/deserializer with CDR (2)."),
    ("SGMII", "Serial Gigabit MII, 1.25 GBd 8b/10b MAC-PHY link (19)."),
    ("Skew", "Arrival-time difference between parallel bits or lanes; "
     "removed by deskew (2)."),
    ("SKP ordered set", "PCIe/USB symbols inserted for clock compensation "
     "(18)."),
    ("SMBus", "System Management Bus, a stricter I2C derivative (13)."),
    ("Snoop", "Coherency query to other caches (9)."),
    ("Source-synchronous", "Clock or strobe sent alongside data (DDR DQS, "
     "D-PHY) (2)."),
    ("SPI", "Serial Peripheral Interface, 4-wire synchronous (12)."),
    ("Split transaction", "Request and response decoupled in time (AXI, "
     "PCIe, USB 2.0 hub split) (3)."),
    ("SSC", "Spread-spectrum clocking to cut EMI, e.g. -5000 ppm "
     "down-spread in PCIe (2)."),
    ("SWD", "Arm Serial Wire Debug, 2-pin alternative to JTAG (23)."),
    ("TDM", "Time-division multiplexing of several channels on one line "
     "(16)."),
    ("Termination", "Resistive match to the line impedance to stop "
     "reflections (2)."),
    ("TileLink", "Chip-scale interconnect standard from SiFive/Berkeley "
     "(10)."),
    ("TLP", "PCIe Transaction Layer Packet (18)."),
    ("Transaction ID", "Tag matching responses to requests (AXI ID, PCIe "
     "tag, CHI TxnID) (3)."),
    ("UCIe", "Universal Chiplet Interconnect Express die-to-die standard "
     "(22)."),
    ("UI", "Unit interval: one symbol time (2)."),
    ("USB", "Universal Serial Bus (17)."),
    ("Virtual channel", "Independent logical queues on one link preventing "
     "head-of-line blocking/deadlock (3, 18)."),
    ("VIP", "Verification IP: protocol BFM, monitor, checker and "
     "coverage (25)."),
    ("VALID / READY", "AMBA handshake: transfer when both high on a clock "
     "edge (7)."),
    ("Wishbone", "Open-source on-chip bus (OpenCores) (10)."),
    ("WRAP burst", "Burst whose address wraps at a size-aligned boundary, "
     "for critical-word-first cache fills (6, 7)."),
    ("Write strobe", "Byte enables (`WSTRB`, `PSTRB`, `HWSTRB`) (5, 7)."),
    ("xMII", "Ethernet MAC-PHY family: MII, RMII, GMII, RGMII, SGMII, "
     "XGMII, USXGMII (19)."),
    ("xSPI", "JEDEC JESD251 expanded SPI for octal DDR flash (12)."),
]


def _appx_b():
    appendix("Glossary")
    p("Terms used across the book, in alphabetical order. Numbers in "
      "parentheses point to the chapter where the concept is treated in "
      "depth.")
    tbl(["Term", "Definition"],
        [[a, b] for a, b in sorted(_GLOSS, key=lambda t: t[0].lower())],
        widths=[24, 76], bold_first=True)


# =============================================================================
# Appendix C - interview questions
# =============================================================================
_Q = {"n": 0}


def qa(q, a):
    """One numbered interview question with its answer."""
    _Q["n"] += 1
    segs = ("Q%d. %s" % (_Q["n"], q)).split("`")
    p("".join(("**%s**" % s if s.strip() else s) if i % 2 == 0 else "`%s`" % s
              for i, s in enumerate(segs)))
    if isinstance(a, str):
        a = [a]
    for para in a:
        p(para)


def _appx_c():
    appendix("100 Communication Protocol Interview Questions with Answers")
    _Q["n"] = 0
    p("Grouped by topic, from screening questions to on-site design "
      "puzzles. Answer out loud first, then check. Numeric answers were "
      "worked out with Python; assumptions are stated so you can redo them "
      "with an interviewer's numbers.")

    ah2("Fundamentals and signalling")
    qa("What is the difference between synchronous, source-synchronous and "
       "embedded-clock (asynchronous serial) links?",
       "Synchronous: a common clock goes to both ends (APB, SPI from the "
       "controller's view). Source-synchronous: the transmitter sends a "
       "clock or strobe with the data (DDR DQS, D-PHY clock lane) so the "
       "flight times track. Embedded clock: no clock wire; the receiver's "
       "CDR recovers timing from data transitions (PCIe, USB 3, Ethernet), "
       "which requires a line code or scrambler that guarantees edges.")
    qa("Why are high-speed links differential?",
       "Common-mode noise and ground shifts cancel, radiated EMI is lower "
       "because the fields of the two wires cancel, swing per wire can be "
       "small (hundreds of mV), and the receiver has a well-defined "
       "crossing point, which reduces jitter.")
    qa("What is the unit interval of a 16 GT/s link, and what is the Nyquist "
       "frequency?",
       "UI = 1/16e9 = 62.5 ps. Nyquist (fastest 1010 pattern) is half the "
       "symbol rate: 8 GHz. Channel loss is always quoted at Nyquist.")
    qa("Compare 8b/10b and 128b/130b.",
       "8b/10b: 20% of the line rate is overhead, strict DC balance, max "
       "run length 5, commas for alignment. 128b/130b: 1.5% overhead, relies "
       "on a scrambler for DC balance/transitions and a 2-bit sync header "
       "for block alignment. PCIe 3.0 moved to 128b/130b so 8 GT/s delivers "
       "~2x the payload of 5 GT/s 8b/10b.")
    qa("Why does PAM4 need FEC when NRZ at the same bit rate often does not?",
       "Three eyes stacked in the same swing: each eye has one third of the "
       "amplitude (about -9.5 dB SNR penalty), so raw BER is far worse "
       "(~1e-6 to 1e-4 pre-FEC). FEC (RS in Ethernet, a light FEC plus CRC "
       "and retry in PCIe 6) recovers the target error rate.")
    qa("What is the purpose of a scrambler, and what is the difference "
       "between additive and self-synchronising scramblers?",
       "It whitens the data spectrum (EMI, DC balance, transitions for CDR). "
       "Additive (frame-synchronous, PCIe/USB): an LFSR sequence XORed onto "
       "data, both ends reset in lock-step - no error multiplication. "
       "Self-synchronising (64b/66b, x^{58}+x^{39}+1): the scrambled output "
       "feeds the LFSR, so the descrambler syncs automatically but one line "
       "error becomes up to 3 bit errors.")
    qa("Explain TX de-emphasis, CTLE and DFE in one sentence each.",
       ["De-emphasis: a TX FIR reduces the amplitude of repeated bits so "
        "high frequencies are relatively boosted. CTLE: an RX analog filter "
        "with a zero that boosts high frequencies (and noise). DFE: subtracts "
        "the ISI of already-decided bits, boosting no noise but vulnerable to "
        "error propagation."])
    qa("What is the difference between a redriver and a retimer?",
       "A redriver is an analog amplifier/equaliser: it restores amplitude "
       "but also passes jitter and noise through, and is protocol-unaware. "
       "A retimer has a CDR and full PHY (and for PCIe participates in link "
       "training), so it resets the jitter and loss budget at the cost of "
       "latency (tens of ns) and power.")

    ah2("Handshakes, flow control and CRC")
    qa("State the AXI VALID/READY rules that prevent deadlock.",
       "A source must not wait for READY before asserting VALID, and once "
       "VALID is asserted it must stay high with stable payload until the "
       "handshake. A destination may wait for VALID before asserting READY. "
       "The transfer happens on the edge where both are high.")
    qa("Credit-based versus ready/valid flow control - when is each better?",
       "Ready/valid is a per-cycle combinational back-pressure: simple, "
       "but READY must propagate backward within a cycle, which hurts over "
       "long distances. Credits decouple: the receiver pre-advertises buffer "
       "space, so the sender needs no same-cycle feedback; loop latency is "
       "hidden by enough credits (buffer >= bandwidth x round trip). Used by "
       "PCIe, CHI, UCIe, NoCs.")
    qa("How much receive buffer do you need for credit flow control on a "
       "link with a 200 ns credit round trip at 16 GB/s?",
       "Buffer >= bandwidth x round-trip time = 16e9 x 200e-9 = 3200 bytes. "
       "Anything less and the sender idles waiting for credits.")
    qa("What errors does a CRC-n always detect?",
       "All single-bit errors, all burst errors of length <= n, all odd "
       "numbers of bit errors if the polynomial has (x+1) as a factor, and "
       "all double-bit errors within the polynomial's period. Longer random "
       "errors escape with probability ~2^{-n}.")
    qa("Why are CRC registers preset to all ones and the result inverted?",
       "Preset: with init 0, leading zero bytes do not change the CRC, so "
       "missing/extra leading zeros go undetected. XorOut: makes appended "
       "zero bytes detectable and gives a constant non-zero residue at the "
       "receiver (for Ethernet CRC-32, running the CRC over frame + FCS "
       "always leaves the register at 0xDEBB20E3 before the final XOR).")
    qa("What is the CRC check value and why do engineers quote it?",
       "The CRC of ASCII \"123456789\". It pins down all parameters at once "
       "(poly, init, reflection, xorout): e.g. CRC-32 = 0xCBF43926, "
       "CRC-15/CAN = 0x059E. Appendix A shows a script reproducing 18 of "
       "them.")
    qa("How do you compute a CRC over a 64-bit word per clock in RTL?",
       "Unroll the bit-serial LFSR 64 times symbolically; each next-state "
       "bit becomes an XOR of some state bits and data bits (a GF(2) matrix "
       "multiply). Generate the equations with a script, verify against a "
       "bit-serial model, and pipeline the XOR trees if timing is tight.")
    qa("Detection versus correction: when do links use retry and when FEC?",
       "Retry (CRC + ACK/NAK replay, PCIe/USB 3/UCIe) is cheap when errors "
       "are rare, but costs round-trip latency on errors. FEC corrects "
       "without a return path at fixed latency cost; needed when raw BER is "
       "high (PAM4) or no retransmission exists (video, JESD204C).")

    ah2("APB and AHB")
    qa("Draw an APB write with one wait state.",
       ["T1 SETUP: PSEL=1, PENABLE=0, PADDR/PWRITE/PWDATA valid. T2 ACCESS: "
        "PENABLE=1, PREADY=0 (wait). T3: PREADY=1 - transfer completes at "
        "the end of this cycle. Total 3 cycles; address/data held stable "
        "throughout."])
    qa("What did APB3 and APB4 add?",
       "APB3: PREADY (wait states) and PSLVERR (error). APB4: PPROT "
       "(protection) and PSTRB (byte write strobes). APB5 adds wake-up, user "
       "signals and optional parity protection.")
    qa("How does AHB pipelining work, and what stalls it?",
       "The address phase of transfer N+1 overlaps the data phase of N. "
       "HREADY low extends the current data phase and therefore also holds "
       "the next address phase; all masters/slaves see the same HREADY "
       "(HREADYOUT from the selected slave via the mux).")
    qa("Why does an AHB ERROR response take two cycles?",
       "HRESP=ERROR is signalled first with HREADY low, then with HREADY "
       "high. The first cycle gives the master time to cancel the already "
       "pipelined next address phase (drive HTRANS=IDLE).")
    qa("What is the 1 KB boundary rule in AHB?",
       "A burst must not cross a 1 KB address boundary, so a slave's "
       "decoding (minimum slave region 1 KB) never changes mid-burst.")
    qa("Why do SoCs put an AHB/AXI-to-APB bridge in front of peripherals?",
       "APB is small and low-power: no pipelining, no bursts, simple "
       "decode. The bridge absorbs the complex protocol once, and hundreds "
       "of register blocks stay trivial and can sit on a slower clock.")
    qa("What are HTRANS encodings?",
       "IDLE (00), BUSY (01, master inserts a gap inside a burst), NONSEQ "
       "(10, first/single transfer), SEQ (11, subsequent burst beat).")

    ah2("AXI")
    qa("Name the five AXI channels and their direction.",
       "AW write address (M->S), W write data (M->S), B write response "
       "(S->M), AR read address (M->S), R read data + response (S->M).")
    qa("Can write data arrive before the write address?",
       "Yes. AXI allows W before AW; a slave must handle it (typically by "
       "buffering or by holding WREADY low until it sees AW, which is "
       "legal because a destination may wait). The B response must not be "
       "given before both the last W beat and AW have been accepted.")
    qa("What are the AXI4 burst length limits and the 4 KB rule?",
       "INCR: 1-256 beats (AXI3: 16); WRAP: 2, 4, 8 or 16 beats; FIXED: up "
       "to 16. No burst may cross a 4 KB boundary, because that is the "
       "smallest page/slave region.")
    qa("Compute the address of each beat of a 4-beat WRAP burst, 4-byte "
       "beats, start 0x38.",
       "Wrap boundary = 4 x 4 = 16 bytes, lower boundary 0x30. Beats: 0x38, "
       "0x3C, 0x30, 0x34.")
    qa("What ordering does AXI guarantee?",
       "Transactions with the same ID in the same direction complete in "
       "issue order; different IDs may complete out of order. There is no "
       "ordering between reads and writes; a master must wait for B before "
       "issuing a dependent read. AXI4 removed write interleaving (WID).")
    qa("What is the difference between OKAY, EXOKAY, SLVERR and DECERR?",
       "OKAY normal success (or failed exclusive), EXOKAY exclusive "
       "succeeded, SLVERR the slave was reached but reports an error, "
       "DECERR no slave at that address (usually from the interconnect's "
       "default slave).")
    qa("What is the purpose of AxCACHE and AxPROT?",
       "AxCACHE: bufferable, modifiable, read/write-allocate hints - tell "
       "interconnect and caches whether a transfer may be merged, split, "
       "buffered or cached. AxPROT: privileged, non-secure, instruction - "
       "used by firewalls/TrustZone filters.")
    qa("How do you register-slice an AXI channel without losing throughput?",
       "Use a skid buffer: register the payload forward and READY backward, "
       "with a second holding register to catch the beat that arrives in "
       "the cycle READY drops. It sustains 1 beat/clock and cuts both "
       "timing paths.")
    qa("What does an AXI interconnect do with IDs?",
       "It extends master IDs with port bits so responses route back, and "
       "tracks outstanding IDs per slave to maintain per-ID ordering (e.g. "
       "stalls a same-ID request to a different slave until earlier ones "
       "finish).")
    qa("Why can a master deadlock if it waits for AWREADY before driving "
       "WVALID?",
       "Because a slave is allowed to wait for WVALID before asserting "
       "AWREADY. Neither side moves. The spec forbids dependencies of "
       "VALID on READY exactly to avoid this.")

    ah2("Cache coherency")
    qa("Explain the MESI states.",
       "Modified: only copy, dirty. Exclusive: only copy, clean - can be "
       "written silently. Shared: possibly several clean copies. Invalid. "
       "MOESI adds Owned: dirty but shared, owner supplies data and is "
       "responsible for write-back.")
    qa("Snooping versus directory coherence?",
       "Snooping broadcasts requests to all caches - simple, low latency, "
       "but bandwidth grows with cores. Directory/snoop-filter keeps track "
       "of which caches hold each line and sends targeted snoops; scales to "
       "meshes (CHI home nodes).")
    qa("What is ACE-Lite used for?",
       "IO-coherent masters (DMA, GPU, accelerators) that have no cache "
       "(or do not need to be snooped) but whose reads must see dirty CPU "
       "data and whose writes must invalidate CPU copies.")
    qa("What is false sharing and why is it a protocol issue?",
       "Two cores write different variables in the same cache line; the "
       "line ping-pongs between Modified states with snoops and data "
       "transfers, though no data is truly shared. Fix by padding to the "
       "line size.")
    qa("Name the CHI node types.",
       "RN (request node: RN-F fully coherent, RN-I IO, RN-D with DVM), HN "
       "(home node: HN-F with snoop filter/SLC, HN-I for IO), SN (subordinate "
       "node, e.g. memory controller SN-F), and MN (miscellaneous node for "
       "DVM).")

    ah2("UART, SPI, I2C and I3C")
    qa("How many bit times does a UART 8N1 byte take, and what is the "
       "throughput at 115200 baud?",
       "10 bits (start + 8 + stop). 115200 / 10 = 11520 bytes/s.")
    qa("Why do UART receivers oversample 16x?",
       "To find the start-bit falling edge within 1/16 bit and then sample "
       "each bit near its centre (often majority of 3 samples), leaving "
       "margin for clock mismatch and noise.")
    qa("List the four SPI modes.",
       "Mode 0: CPOL=0, CPHA=0 - idle low, sample on rising edge. Mode 1: "
       "CPOL=0, CPHA=1 - sample on falling. Mode 2: CPOL=1, CPHA=0 - idle "
       "high, sample on falling. Mode 3: CPOL=1, CPHA=1 - sample on "
       "rising. Modes 0 and 3 are the most common.")
    qa("Why can SPI run much faster than I2C?",
       "Push-pull drivers (no RC pull-up rise time), separate data "
       "directions, no ACK or arbitration and no address phase. I2C's "
       "open-drain rise time with pull-ups and bus capacitance limits it.")
    qa("What happens during I2C arbitration?",
       "Each controller drives SDA and reads it back; open drain makes the "
       "bus a wired-AND. A controller that drives 1 but reads 0 has lost "
       "and backs off. The winner's message is undamaged, so arbitration is "
       "non-destructive.")
    qa("What are START and STOP conditions?",
       "START: SDA falls while SCL is high. STOP: SDA rises while SCL is "
       "high. All data changes happen while SCL is low.")
    qa("Name three things I3C improves over I2C.",
       "Push-pull SDR at 12.5 MHz (and HDR modes), in-band interrupts "
       "without extra pins, dynamic address assignment, common command "
       "codes, hot-join, and lower power. I2C legacy targets can share the "
       "bus if they have a spike filter.")
    qa("How does an I2C target signal \"not ready\"?",
       "By clock stretching (holding SCL low) or by NACKing its address "
       "until ready. SMBus bounds stretching by timeouts (25-35 ms).")
    qa("What is QSPI XIP?",
       "Execute-in-place: the QSPI controller maps flash into the CPU "
       "address space and translates AHB/AXI reads into read commands, "
       "often with a prefetch cache, so code runs directly from flash.")
    qa("How do you connect several SPI targets?",
       "Shared SCLK/COPI/CIPO with one CS_n per target (CIPO tri-stated "
       "when deselected), or daisy chain where CIPO of one feeds COPI of "
       "the next and one long shift frame covers all.")

    ah2("CAN")
    qa("How does CAN arbitration work?",
       "Dominant (0) overwrites recessive (1) on the bus. Nodes send the "
       "identifier MSB first and monitor the bus; a node reading dominant "
       "while sending recessive loses and becomes a receiver. Lowest ID "
       "wins, with no lost bus time.")
    qa("Why must the CAN bit time exceed about twice the propagation delay?",
       "During arbitration every node must see the other nodes' bits within "
       "the same bit before the sample point: signal travels to the far "
       "node and its dominant bit travels back. At ~5 ns/m plus transceiver "
       "delays (~100-250 ns loop each), 1 Mb/s limits the bus to about "
       "40 m.")
    qa("How long is a classical CAN frame with 8 data bytes, worst case?",
       "Standard (11-bit) data frame: 44 overhead bits + 64 data = 108 bits. "
       "Stuffing applies to the first 98 bits (SOF through CRC): worst case "
       "(34+64-1)/4 = 24 stuff bits. Plus 3 bits intermission -> 135 bit "
       "times, i.e. 135 us at 1 Mb/s.")
    qa("Describe CAN fault confinement.",
       "Each node keeps TEC/REC counters: error-active (< 128) sends active "
       "error flags, error-passive (>= 128) sends passive flags and waits "
       "extra, bus-off (TEC > 255) disconnects until 128 x 11 recessive "
       "bits are seen.")
    qa("What changes in CAN FD?",
       "Up to 64 data bytes, a faster data phase switched by the BRS bit, "
       "no remote frames, CRC-17/CRC-21 with a stuff-bit count and fixed "
       "stuff bits in the CRC field, and an ESI bit.")

    ah2("USB")
    qa("What are the four USB transfer types?",
       "Control (enumeration, endpoint 0), bulk (guaranteed delivery, "
       "no latency guarantee), interrupt (bounded latency polling), "
       "isochronous (reserved bandwidth, no retry).")
    qa("What is the maximum USB 2.0 high-speed bulk throughput?",
       "13 packets of 512 bytes per 125 us microframe: 6656 / 125e-6 = "
       "53.2 MB/s theoretical, typically 35-45 MB/s real.")
    qa("How does USB 2.0 encode bits, and why bit stuffing?",
       "NRZI: a 0 is a transition, a 1 is no transition. Long runs of 1s "
       "would give no edges, so a 0 is stuffed after six consecutive 1s.")
    qa("What is the role of the UTMI/ULPI interface?",
       "It separates the digital USB controller (link) from the analog PHY: "
       "UTMI is a parallel 8/16-bit on-chip interface at 60/30 MHz; ULPI "
       "is a reduced 12-pin version for an external PHY.")
    qa("How does USB detect full-speed versus low-speed and high-speed?",
       "A 1.5 k pull-up on D+ (FS) or D- (LS) at the device; HS capable "
       "devices then perform the chirp K/J handshake during reset to "
       "switch to HS terminations.")
    qa("What is USB Power Delivery?",
       "A protocol on the Type-C CC wire (BMC coded, 300 kb/s) negotiating "
       "voltage/current contracts up to 48 V / 5 A (240 W in EPR) and "
       "alternate modes.")

    ah2("PCI Express")
    qa("What are the three PCIe layers?",
       "Transaction layer (TLPs: memory, IO, config, message, completions; "
       "flow-control credits), data link layer (sequence numbers, LCRC, "
       "ACK/NAK replay, DLLPs), physical layer (encoding, scrambling, "
       "LTSSM link training, lane deskew).")
    qa("Compute PCIe 4.0 x16 bandwidth per direction.",
       "16 GT/s x 128/130 x 16 lanes / 8 = 31.5 GB/s per direction "
       "(~63 GB/s bidirectional) before TLP/DLLP overhead.")
    qa("What is the efficiency of 256-byte TLPs on Gen3+?",
       "Overhead per TLP roughly 4 framing + 2 sequence + 16 header (4DW) "
       "+ 4 LCRC = 26 bytes: 256 / 282 = 91%. With MPS = 128 it drops to "
       "~83%. ACK and flow-control DLLPs take a few percent more.")
    qa("Posted versus non-posted requests?",
       "Posted (memory writes, messages) need no completion - they consume "
       "only posted credits. Non-posted (memory/IO reads, config, IO "
       "writes) require a completion. Ordering rules let posted writes pass "
       "reads to avoid deadlock.")
    qa("What is the LTSSM and what are its main states?",
       "Link Training and Status State Machine: Detect -> Polling -> "
       "Configuration -> L0, with Recovery (speed change, equalisation, "
       "error recovery), L0s/L1/L2 power states, Loopback, Hot Reset, "
       "Disabled.")
    qa("How do BARs work?",
       "Software writes all ones to a BAR and reads back: the zeroed low "
       "bits give the size (e.g. 0xFFF00000 -> 1 MB). It then writes the "
       "assigned base address; the endpoint claims TLPs in that window.")
    qa("What changed in PCIe 6.0?",
       "PAM4 signalling at 64 GT/s, FLIT mode (fixed 256-byte flits with "
       "light FEC and CRC, 1b/1b encoding), L0p low-power width scaling; "
       "per-direction x16 ~ 121 GB/s after flit overhead.")
    qa("How does CXL relate to PCIe?",
       "CXL runs on the PCIe PHY (negotiated via alternate protocol in "
       "training) and multiplexes CXL.io (PCIe semantics), CXL.cache "
       "(device caches host memory coherently) and CXL.mem (host accesses "
       "device-attached memory). Type 1/2/3 devices use different subsets.")

    ah2("Ethernet")
    qa("What is the minimum Ethernet frame and why?",
       "64 bytes (dest 6 + src 6 + type 2 + payload 46 + FCS 4); for "
       "half-duplex CSMA/CD the frame had to last longer than a collision "
       "round trip (512 bit times). Kept for compatibility.")
    qa("What is the maximum packet rate of 10 GbE?",
       "Minimum frame 64 + preamble/SFD 8 + IFG 12 = 84 bytes = 672 bits: "
       "10e9 / 672 = 14.88 Mpps (1.488 Mpps at 1 GbE). A 64-bit datapath at "
       "156.25 MHz has ~10.5 cycles per packet.")
    qa("MAC, PCS, PMA, PMD - who does what?",
       "MAC: framing, FCS, pause, statistics. PCS: encoding (64b/66b), "
       "scrambling, lane alignment. PMA: serialisation, CDR. PMD: the "
       "medium-dependent driver/optics. The MII family (GMII, XGMII) sits "
       "between MAC and PCS.")
    qa("RGMII versus SGMII?",
       "RGMII: 4-bit DDR data + control at 125 MHz (12 pins), needs 2 ns "
       "clock-to-data skew (PHY or MAC internal delay or PCB). SGMII: one "
       "1.25 GBd 8b/10b SerDes pair each way, carries 10/100/1000 by "
       "symbol replication.")
    qa("What is IEEE 1588 PTP and what does hardware need?",
       "Precision Time Protocol: timestamp sync/delay messages at the MAC "
       "/PHY boundary so software can compute offset and path delay; "
       "accuracy of tens of ns requires hardware timestamping and an "
       "adjustable hardware clock.")
    qa("What is the Ethernet payload efficiency at 1500-byte payload?",
       "1500 / (1500 + 14 header + 4 FCS + 8 preamble + 12 IFG) = 1500/1538 "
       "= 97.5% (before IP/TCP headers).")

    ah2("DDR and memory")
    qa("Explain tRCD, CL and tRP.",
       "tRCD: ACTIVATE to READ/WRITE (open row). CL (tAA): READ command to "
       "first data. tRP: PRECHARGE to next ACTIVATE on that bank. A page "
       "miss costs tRP + tRCD + CL.")
    qa("Convert DDR4-3200 CL22 to nanoseconds.",
       "Clock = 1600 MHz, tCK = 0.625 ns; 22 x 0.625 = 13.75 ns. Absolute "
       "latency barely changes across generations; the clock count grows.")
    qa("Why does DDR use a data strobe and read leveling/write leveling?",
       "DQS is source-synchronous so data and strobe see the same flight "
       "time. With fly-by clock routing on DIMMs each DRAM sees CK at a "
       "different time; write leveling aligns DQS to CK per byte lane, "
       "read training finds the DQS/DQ eye centre.")
    qa("Why did DDR5 split the DIMM into two subchannels?",
       "Two independent 32-bit (40 with ECC) channels with BL16 give a "
       "64-byte access per subchannel, doubling concurrency and improving "
       "efficiency; it also added on-die ECC and an on-DIMM PMIC.")
    qa("What is the role of the DFI interface?",
       "The DDR PHY Interface standardises the boundary between memory "
       "controller and PHY: command, write data, read data, update and "
       "training handshakes, with a frequency ratio (1:2, 1:4).")
    qa("How does refresh affect bandwidth?",
       "Every tREFI (~3.9 us at high temperature, 7.8 us normal for DDR4) "
       "a REF blocks the rank for tRFC (~350 ns for 8 Gb dies): "
       "~350/7800 = 4.5% loss at normal temperature, twice that when hot. "
       "Per-bank/same-bank refresh in LPDDR/DDR5 reduces the impact.")
    qa("HBM versus GDDR: when to use which?",
       "HBM: very wide (1024-2048 bits) at modest pin rates, lowest pJ/bit "
       "and highest bandwidth per device, but needs 2.5D packaging and "
       "costs more. GDDR: narrow (x32) at very high pin rates on a standard "
       "PCB. AI accelerators favour HBM; consumer GPUs use GDDR.")

    ah2("MIPI, display and video")
    qa("What are D-PHY LP and HS modes?",
       "LP: 1.2 V single-ended, ~10 Mb/s, used for control, escape mode "
       "and turnaround. HS: ~200 mV differential, terminated, for bulk "
       "data. A lane enters HS via the LP-11 -> LP-01 -> LP-00 -> HS-0 "
       "sequence.")
    qa("How many D-PHY lanes for 4K60 RAW10 from a camera?",
       "3840 x 2160 x 60 x 10 = 4.98 Gb/s of pixels; with ~20% blanking "
       "and packet overhead ~6 Gb/s. Four lanes at ~1.5-2 Gb/s each fits "
       "(D-PHY v1.2 allows 2.5 Gb/s per lane).")
    qa("What is a CSI-2 long packet?",
       "Header: Data ID (VC + data type), 16-bit word count, ECC (6-bit, "
       "v2.0+ virtual channel extension), then payload and a 16-bit CRC "
       "footer. Short packets carry frame/line start/end.")
    qa("What is the TMDS clock for 1080p60 HDMI?",
       "Pixel clock 148.5 MHz; each TMDS channel carries 10 bits per pixel "
       "clock: 1.485 Gb/s per lane for 8-bit colour.")
    qa("DisplayPort versus HDMI architecture?",
       "DP is packetised with a fixed set of link rates and an AUX channel, "
       "and the source clock is regenerated from M/N values; HDMI 1.x/2.0 "
       "carries a pixel-locked TMDS clock (HDMI 2.1 FRL moved to "
       "packetised fixed rates too).")

    ah2("Debug and test")
    qa("What are the JTAG pins and the TAP controller?",
       "TCK, TMS, TDI, TDO, optional TRST. The TAP is a 16-state FSM "
       "driven by TMS; five TCKs with TMS=1 always reach Test-Logic-Reset. "
       "IR selects which data register (BYPASS, IDCODE, boundary scan, "
       "user) sits between TDI and TDO.")
    qa("What does SWD replace and how?",
       "It replaces 4/5-pin JTAG with SWDIO (bidirectional) and SWCLK, "
       "using packet requests with parity and ACK to access DP/AP "
       "registers of an Arm DAP.")
    qa("IEEE 1500 versus IEEE 1687?",
       "1500 standardises a test wrapper around cores (WIR, WBR, serial and "
       "parallel ports) for core-based test. 1687 (IJTAG) standardises a "
       "reconfigurable network (SIBs) to reach embedded instruments, "
       "described in ICL/PDL.")
    qa("How would you debug a link that trains but has CRC errors?",
       "Check eye margins (on-die eye monitor, BER vs equaliser settings), "
       "reference clock quality and SSC settings, crosstalk and power "
       "noise, lane polarity/ordering and CDC between PCS and controller; "
       "reproduce with PRBS loopback to separate PHY from protocol.")

    ah2("Design puzzles")
    qa("SPI controller: pad + board delay 2 ns each way, target clock-to-out "
       "8 ns, controller input setup 2 ns. Maximum SCLK?",
       ["In mode 0 the target launches CIPO on the falling edge and the "
        "controller samples on the next rising edge: half a period is "
        "available. Round trip = 2 (SCLK out) + 8 (tco) + 2 (back) + 2 "
        "(setup) = 14 ns <= T/2 -> T >= 28 ns -> fmax = 35.7 MHz.",
        "Fix: sample on a later edge (delayed/read-capture sampling): a "
        "full period is available, T >= 14 ns -> 71.4 MHz. This is why "
        "QSPI controllers have programmable read-capture delay or use DQS."])
    qa("UART 8N1: how much total baud-rate mismatch can be tolerated?",
       ["The receiver samples the stop bit at 9.5 bit times after the start "
        "edge; the accumulated error must stay under half a bit: "
        "0.5 / 9.5 = 5.26% total. Subtract the start-detection uncertainty "
        "of 1/16 bit with 16x oversampling: (0.5 - 0.0625) / 9.5 = 4.6%.",
        "Split between both ends and leave margin for edge distortion: the "
        "usual design rule is +/-2% per side (1-1.5% for long frames or "
        "noisy lines)."])
    qa("Choose an I2C pull-up for a 3.3 V Fast-mode bus with 200 pF.",
       ["Minimum (sink current): Rp_{min} = (VDD - VOL) / IOL = "
        "(3.3 - 0.4) / 3 mA = 967 ohm.",
        "Maximum (rise time, 30% to 70% = 0.8473 RC): Rp_{max} = t_{r} / "
        "(0.8473 x Cb) = 300 ns / (0.8473 x 200 pF) = 1.77 k.",
        "Pick ~1.2-1.5 k. (Standard mode, 1000 ns, 400 pF: up to 2.95 k.)"])
    qa("An AXI master must sustain 16 GB/s on a 128-bit bus at 1 GHz with "
       "200 ns read latency and 64-byte bursts. How many outstanding reads?",
       "Little's law: bytes in flight = bandwidth x latency = 16 B/cycle x "
       "200 cycles = 3200 B. 3200 / 64 = 50 outstanding transactions "
       "(so at least 6-bit ID/tag space or equivalent tracking, and 3.2 KB "
       "of read reorder buffering).")
    qa("What is the peak and realistic bandwidth of a DDR5-6400 DIMM?",
       "6400 MT/s x 64 bits / 8 = 51.2 GB/s peak. With refresh, bank "
       "conflicts, read/write turnarounds and page misses, typically "
       "70-85% efficiency: ~36-43 GB/s.")
    qa("Writer 100 MHz sends 120-word bursts back-to-back; reader drains "
       "one word per cycle at 80 MHz. Minimum FIFO depth?",
       "Burst lasts 120 / 100 MHz = 1.2 us. Reader removes 1.2 us x 80 MHz = "
       "96 words meanwhile. Depth >= 120 - 96 = 24 words, plus a few "
       "entries for synchronizer latency on the async pointers (round up "
       "to 32). Also verify the average rate: the idle gap between bursts "
       "must be >= 24 / 80 MHz = 0.3 us.")
    qa("How many lanes of PCIe 5.0 does a 400 Gb/s NIC need?",
       "400 Gb/s = 50 GB/s per direction. Gen5 lane: 32 x 128/130 / 8 = "
       "3.94 GB/s; with ~88% TLP efficiency ~3.5 GB/s -> 50 / 3.5 = 14.3, "
       "so x16 (with little headroom).")
    qa("I2C at 400 kHz: how many bytes per second can you read from a "
       "sensor register block?",
       "Each byte takes 9 SCL cycles (8 + ACK): max 44.4 kB/s raw. A "
       "register read of N bytes costs START + addr(W) + reg + Sr + addr(R) "
       "+ N data + STOP, so ~ (3 + N) x 9 + ~3 clocks; for N = 6: ~84 clocks "
       "= 210 us, i.e. ~28.6 kB/s effective.")
    qa("HBM3 stack bandwidth, and how many stacks for 3 TB/s?",
       "6.4 Gb/s x 1024 / 8 = 819.2 GB/s per stack; 3000 / 819.2 = 3.7 -> "
       "4 stacks (or 3 stacks of HBM3E at ~1.2 TB/s each).")
    qa("A camera outputs 1080p60 YUV422 8-bit. Minimum AXI write bandwidth "
       "into DDR, and the burst rate on a 64-bit, 250 MHz port?",
       "1920 x 1080 x 60 x 2 bytes = 249 MB/s. The port provides 8 B x "
       "250 MHz = 2 GB/s, so ~12.4% utilisation; with 16-beat (128 B) "
       "bursts that is ~1.95 M bursts/s - about one burst every 512 ns.")
    qa("Design a 4-to-1 SPI-flash read path that hides 100 ns flash "
       "latency at 50 MB/s. What prefetch buffer?",
       "Latency x bandwidth = 100e-9 x 50e6 = 5 bytes in flight; round up "
       "to the command granularity: a 2-line (e.g. 2 x 32-byte) prefetch "
       "buffer so the next line is requested while the current one "
       "drains. Also check command/address overhead: a 1-4-4 read with 8 "
       "dummy clocks costs ~16 clocks before data.")
    assert _Q["n"] == 100, "Appendix C must contain exactly 100 questions"


# =============================================================================
# Appendix D - specifications and resources
# =============================================================================
def _appx_d():
    appendix("Specifications, Standards Bodies and Resources")
    p("Where the authoritative documents live, what open-source RTL to "
      "study, and which tools to install. Access models vary: some "
      "specifications are free after registration (Arm AMBA, NXP I2C, "
      "several MIPI and JEDEC documents), others need membership or "
      "purchase (PCI-SIG, IEEE, ISO, full MIPI PHY specs). Items marked "
      "(*) are vendor, product or access claims that may change - verify "
      "on the owner's website.")

    ah2("Standards bodies and key documents")
    tbl(["Body", "Protocols", "Key documents (as commonly referenced)"],
        [["Arm (AMBA)", "APB, AHB, AXI, ACE, CHI, ATB, AXI-Stream, DTI",
          "AMBA APB Protocol Spec (IHI 0024), AMBA AHB/AHB5 (IHI 0033), "
          "AMBA AXI and ACE / AXI Protocol Spec (IHI 0022), AMBA CHI "
          "Architecture Spec (IHI 0050), AXI4-Stream (IHI 0051); CoreSight "
          "Architecture Spec, ADIv5/ADIv6 (IHI 0031 / IHI 0074). Free "
          "download (*)"],
         ["USB-IF", "USB 2.0, 3.2, USB4, Type-C, PD, device classes",
          "USB 2.0 Spec, USB 3.2 Spec, USB4 Spec (v1, v2), USB Type-C "
          "Cable and Connector Spec, USB Power Delivery Spec; UTMI+ and "
          "PIPE (Intel-published) for PHY interfaces"],
         ["PCI-SIG", "PCI Express", "PCI Express Base Specification "
          "(Rev. 1.0-7.0), CEM (card electromechanical) spec, PIPE; "
          "member access (*)"],
         ["CXL Consortium", "Compute Express Link", "CXL Specification "
          "1.1, 2.0, 3.x"],
         ["IEEE", "Ethernet, test, time", "802.3 (Ethernet; clauses per "
          "PHY type, e.g. 22 MII/MDIO, 45 MDIO, 49 10GBASE-R, 91 RS-FEC), "
          "802.1Q/TSN, 1149.1 (JTAG), 1149.6 (AC-coupled boundary scan), "
          "1500 (core test wrapper), 1687 (IJTAG), 1588 (PTP), 1800 "
          "(SystemVerilog), 1800.2 (UVM)"],
         ["JEDEC", "DRAM, flash, converters", "JESD79-4 (DDR4), JESD79-5 "
          "(DDR5), JESD209-4/-5 (LPDDR4/5, 5X), JESD250 (GDDR6), JESD239 "
          "(GDDR7), JESD235 (HBM/HBM2), JESD238 (HBM3), JESD270-4 (HBM4), "
          "JESD84 (eMMC), JESD220 (UFS), JESD251 (xSPI), JESD216 (SFDP), "
          "JESD204B/C (serial converter interface). Many free after "
          "registration (*)"],
         ["MIPI Alliance", "Camera, display, sensors", "D-PHY, C-PHY, "
          "M-PHY, A-PHY, CSI-2, DSI/DSI-2, I3C and I3C Basic (I3C Basic is "
          "publicly downloadable (*)), SoundWire, RFFE"],
         ["VESA", "DisplayPort, eDP, DSC", "DisplayPort Standard 1.4 / "
          "2.1, eDP, Display Stream Compression (DSC), DisplayID"],
         ["HDMI Forum / HDMI LA", "HDMI", "HDMI Specification 1.4b, 2.0, "
          "2.1, 2.2 (adopter access (*))"],
         ["ISO", "Automotive", "ISO 11898-1 (CAN data link, incl. CAN FD), "
          "ISO 11898-2 (high-speed CAN PHY), ISO 17987 (LIN), ISO 17458 "
          "(FlexRay), ISO 26262 (functional safety); CiA (CAN in "
          "Automation) publishes CAN XL (CiA 610) and application layers"],
         ["NXP", "I2C", "UM10204 I2C-bus specification and user manual "
          "(free)"],
         ["SMBus / PMBus (SBS-IF, SMIF)", "SMBus, PMBus", "System "
          "Management Bus Specification 3.x, PMBus Parts I-III"],
         ["UCIe Consortium", "Die-to-die", "UCIe Specification 1.0, 1.1, "
          "2.0, 3.0"],
         ["Open Compute Project", "Die-to-die", "Bunch of Wires (BoW) "
          "specification"],
         ["RISC-V International / CHIPS Alliance", "TileLink, debug",
          "TileLink Specification (SiFive, maintained in the CHIPS "
          "Alliance), RISC-V External Debug Support spec"],
         ["Accellera", "OCP, UVM, IP-XACT", "Open Core Protocol "
          "specification, UVM library, IEEE 1685 IP-XACT"],
         ["OpenCores", "Wishbone", "Wishbone B4 specification (free)"],
         ["ONFI / SD Association", "NAND, SD", "ONFI 4.x/5.x, SD "
          "Physical Layer Simplified Specification (free)"],
         ["TIA / EIA", "Serial lines", "TIA-232-F (RS-232), TIA-485-A "
          "(RS-485), TIA-644 (LVDS)"]],
        widths=[17, 20, 63], bold_first=True)
    box("tip", "Reading a big spec efficiently",
        ["Start with the overview/architecture chapter and the list of "
         "state machines, then read the signal or packet definitions, then "
         "the ordering and error rules. Keep the errata and ECN list next to "
         "the base spec: many interview and integration bugs live in ECNs."])

    ah2("Open-source IP to study")
    tbl(["Project", "What to learn from it"],
        [["Alex Forencich: verilog-axi, verilog-axis, verilog-ethernet, "
          "verilog-pcie, verilog-i2c, verilog-uart; Corundum NIC",
          "Production-quality AXI crossbars, register slices, DMA, "
          "10/25G Ethernet MAC/PCS, PCIe DMA; paired cocotbext-axi / "
          "-eth / -pcie Python models for verification. Some repos have "
          "been reorganised or archived over time (*)"],
         ["lowRISC OpenTitan", "Security-grade UART, SPI host/device, "
          "I2C, USB device, TileLink-UL crossbar, with DV (UVM) "
          "environments and documentation of every block"],
         ["PULP Platform axi (ETH Zurich)", "Parameterised AXI4+ATOPs "
          "crossbars, bursts splitters, ID remappers, CDC, with "
          "randomised verification"],
         ["LiteX: LiteDRAM, LitePCIe, LiteEth, LiteSPI, LiteSATA",
          "Complete Python-generated SoC ecosystem (Migen/Amaranth-style "
          "HDL): DRAM controllers and PHYs, PCIe DMA, Ethernet MAC"],
         ["OpenCores I2C master, SPI, UART16550", "Classic small cores "
          "(Wishbone) - good to read, but check for known bugs before "
          "reusing"],
         ["Chipyard / Rocket Chip (Berkeley)", "TileLink (Diplomacy) "
          "interconnect generators, AXI/TileLink bridges, SiFive blocks"],
         ["ZipCPU: wb2axip and blog", "Formally verified AXI/AXI-Lite/"
          "Wishbone slaves, bridges and skid buffers; articles on common "
          "AXI bugs found by formal"],
         ["Other", "SpinalHDL/VexRiscv bus libraries, Verilog "
          "USB (e.g. usb_cdc cores), Enjoy-Digital/LiteX boards, "
          "open-source MIPI CSI-2 receivers - quality varies (*)"]],
        widths=[34, 66], bold_first=True)

    ah2("Tools")
    tbl(["Category", "Examples", "Notes"],
        [["Simulation / formal", "Icarus Verilog, Verilator, cocotb, "
          "SymbiYosys; commercial Xcelium, VCS, Questa, JasperGold, VC "
          "Formal", "Use protocol assertions (Arm-published AXI SVA, "
          "ZipCPU formal properties) early"],
         ["Verification IP", "Commercial VIP from Cadence, Synopsys, "
          "Siemens, Avery, SmartDV (*); open cocotbext-* models",
          "Compliance-level VIP for PCIe/USB/DDR is almost always bought"],
         ["Logic analyzers / decoders", "sigrok + PulseView (open-source, "
          "100+ decoders: I2C, SPI, UART, CAN, 1-Wire, JTAG, USB LS/FS), "
          "Saleae Logic (*)", "Cheap FX2-based analyzers work with sigrok "
          "for low-speed buses"],
         ["Protocol analyzers", "Total Phase Beagle/Aardvark (I2C/SPI/USB), "
          "Teledyne LeCroy and Ellisys (USB, PCIe), Keysight (PCIe, "
          "DDR), Vector CANalyzer/CANoe and PEAK PCAN (CAN) (*)",
          "Necessary for high-speed protocol bring-up; often rented"],
         ["Oscilloscopes / BERT", "Real-time scopes with serial decode and "
          "compliance apps, BERTs for jitter tolerance (Keysight, Tektronix, "
          "R&S, Anritsu) (*)", "PHY/SI team owns eye, jitter and "
          "compliance measurements"],
         ["Packet capture", "Wireshark (Ethernet, USB via usbmon/USBPcap, "
          "CAN via SocketCAN), tcpdump", "Great for decoding real traffic "
          "against your mental model"],
         ["Debug", "OpenOCD, pyOCD, Segger J-Link, Lauterbach TRACE32 (*)",
          "JTAG/SWD access; CoreSight trace capture"],
         ["CRC / coding helpers", "Greg Cook's CRC RevEng catalogue, "
          "Python crcmod/crccheck, OutputLogic-style parallel CRC "
          "generators (*)", "Verify every CRC against a catalogue check "
          "value and a real frame"]],
        widths=[18, 50, 32], bold_first=True)

    ah2("Books and courses")
    tbl(["Title / resource", "Covers"],
        [["Budruk, Anderson, Shanley / Jackson, Budruk: __PCI Express "
          "System Architecture__ and __PCI Express Technology 3.0__ "
          "(MindShare)", "PCIe layers, TLPs, LTSSM in great depth"],
         ["Jan Axelson: __USB Complete__, __Serial Port Complete__",
          "USB from the device/firmware side; UART/RS-232/RS-485"],
         ["Howard Johnson, Martin Graham: __High-Speed Digital Design: A "
          "Handbook of Black Magic__", "Transmission lines, termination, "
          "crosstalk"],
         ["Eric Bogatin: __Signal and Power Integrity - Simplified__",
          "Channel loss, reflections, SI intuition for SerDes"],
         ["Bruce Jacob, Spencer Ng, David Wang: __Memory Systems: Cache, "
          "DRAM, Disk__", "DRAM timing, controllers, scheduling"],
         ["Nagarajan, Sorin, Hill, Wood: __A Primer on Memory Consistency "
          "and Cache Coherence__ (2nd ed.)", "MESI/MOESI, directories, "
          "consistency models - free PDF (*)"],
         ["Charles Spurgeon, Joann Zimmerman: __Ethernet: The Definitive "
          "Guide__", "Ethernet media, frames, auto-negotiation"],
         ["Kenneth Parker: __The Boundary-Scan Handbook__",
          "IEEE 1149.x, board test"],
         ["Nicola Da Dalt, Ali Sheikholeslami: __Understanding Jitter and "
          "Phase Noise__", "Jitter decomposition, CDR, PLL noise"],
         ["Behzad Razavi: __Design of Integrated Circuits for Optical "
          "Communications__", "CDR, SerDes front ends"],
         ["Arm Developer documentation and AMBA training; Verification "
          "Academy (Siemens); ChipVerify; ZipCPU blog (*)",
          "Protocol tutorials, UVM and formal verification of buses"],
         ["Vendor application notes (TI, Analog Devices, NXP, Microchip, "
          "Intel/AMD FPGA IP user guides) (*)", "Practical I2C pull-up, "
          "CAN bit timing, JESD204 and SerDes configuration guides"]],
        widths=[55, 45], bold_first=True)
    box("note", "A suggested reading order",
        ["1) The free specs first: NXP UM10204, AMBA APB/AXI, Wishbone B4, "
         "SD simplified spec. 2) Study one open-source controller per spec "
         "(verilog-i2c, verilog-axi, OpenTitan SPI) and simulate it. "
         "3) Move to SerDes-based protocols with the MindShare PCIe book "
         "and verilog-ethernet. 4) Finish with coherency (Primer, CHI "
         "spec) and memory (JEDEC DDR5 plus the Jacob book)."])


def appendices():
    part("Appendices",
         numbered=False,
         blurb="Protocol comparison tables with a verified CRC catalogue, a "
         "glossary of about 180 terms, 100 interview questions with worked "
         "answers, and the specifications, open-source IP, tools and books "
         "that make up the protocol engineer's library.")
    _appx_a()
    _appx_b()
    _appx_c()
    _appx_d()
