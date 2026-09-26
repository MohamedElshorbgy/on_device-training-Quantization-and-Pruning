"""Part V - After Tapeout (Chapters 20-23).

Packaging and multi-die integration, manufacturing test, yield and
reliability, silicon bring-up and characterisation, and the methodology and
economics of an ASIC project. Every Python model in this part (junction
temperature, bump budget, ground bounce, yield models, test cost, defect
level, Arrhenius acceleration, FIT/MTBF, shmoo, Vmin across corners, speed
binning and AVS, NRE and cost per good die) was run with python3 while
writing it; the out() cards are pasted verbatim from those runs. All cost,
price and defect-density inputs are illustrative assumptions, not foundry
data.
"""

from asic_guide.common import *  # noqa: F401,F403


def _eqa(lines, caption=None):
    """eq() centres each line; pad them to one width so columns stay aligned."""
    w = max(len(l) for l in lines)
    eq([l.ljust(w) for l in lines], caption)


# ---- Scripts and their captured outputs (python3, run while writing this part) ----
TJ_SRC = [
    '# Junction temperature for a few package / cooling options (illustrative thetas)',
    'P = 6.0          # W, chip power',
    'T_amb = 45.0     # deg C, ambient inside the enclosure',
    'cases = [        # name, theta_JA (C/W) or (theta_JC, theta_CS, theta_SA)',
    '    ("QFN-48, no heatsink, 2s2p board", 28.0, None),',
    '    ("FC-BGA 23mm, no heatsink",        14.0, None),',
    '    ("FC-BGA + small passive sink",     None, (0.3, 0.2, 5.5)),',
    '    ("FC-BGA + fan heatsink",           None, (0.3, 0.2, 1.8)),',
    ']',
    'for name, tja, stack in cases:',
    '    if stack:',
    '        tja = sum(stack)',
    '    tj = T_amb + P * tja',
    '    ok = "OK" if tj <= 105 else "TOO HOT"',
    '    print(f"{name:34s} theta_JA={tja:5.1f} C/W  Tj={tj:6.1f} C  {ok}")',
    '# Max power allowed for Tj_max = 105 C with the fan heatsink',
    'tja = 0.3 + 0.2 + 1.8',
    'print(f"Max power with fan sink at Tj<=105C: {(105 - T_amb) / tja:.1f} W")',
]
TJ_OUT = [
    'QFN-48, no heatsink, 2s2p board    theta_JA= 28.0 C/W  Tj= 213.0 C  TOO HOT',
    'FC-BGA 23mm, no heatsink           theta_JA= 14.0 C/W  Tj= 129.0 C  TOO HOT',
    'FC-BGA + small passive sink        theta_JA=  6.0 C/W  Tj=  81.0 C  OK',
    'FC-BGA + fan heatsink              theta_JA=  2.3 C/W  Tj=  58.8 C  OK',
    'Max power with fan sink at Tj<=105C: 26.1 W',
]
SSN_SRC = [
    '# Simultaneous switching noise: dV = N * L_eff * dI/dt, with shared return pins',
    'L_pin = 1.0e-9       # H, effective loop inductance of one ground pin+bond wire',
    'I_drv = 0.020        # A, peak current per output driver',
    't_r   = 0.5e-9       # s, output edge (current ramp) time',
    'for n_out, n_gnd in [(8, 1), (32, 1), (32, 4), (32, 8)]:',
    '    didt = n_out * I_drv / t_r               # total current slew on the return path',
    '    dv = (L_pin / n_gnd) * didt              # ground pins in parallel',
    '    print(f"{n_out:2d} outputs, {n_gnd} gnd pins: ground bounce ~ {dv*1000:6.0f} mV")',
]
SSN_OUT = [
    ' 8 outputs, 1 gnd pins: ground bounce ~    320 mV',
    '32 outputs, 1 gnd pins: ground bounce ~   1280 mV',
    '32 outputs, 4 gnd pins: ground bounce ~    320 mV',
    '32 outputs, 8 gnd pins: ground bounce ~    160 mV',
]
BUMPS_SRC = [
    '# Rough power-bump budget for a flip-chip die (all inputs are assumptions)',
    'P, VDD = 40.0, 0.75            # W, V core supply',
    'I = P / VDD                    # A total core current',
    'I_bump = 0.15                  # A allowed per bump (EM-limited; foundry/package specific)',
    'margin = 1.5                   # derate for non-uniform current sharing',
    'n_pwr = I / I_bump * margin    # VDD bumps; the same number again for VSS',
    'pitch_um = 150.0               # C4 bump pitch',
    'die_mm = 10.0',
    'sites = int(die_mm * 1000 / pitch_um) ** 2',
    'print(f"Core current            : {I:6.1f} A")',
    'print(f"VDD bumps needed        : {n_pwr:6.0f}  (+ same for VSS)")',
    'print(f"Bump sites on {die_mm:.0f}x{die_mm:.0f} mm : {sites:6d}  at {pitch_um:.0f} um pitch")',
    'print(f"Fraction used by power  : {2 * n_pwr / sites * 100:5.1f} %")',
]
BUMPS_OUT = [
    'Core current            :   53.3 A',
    'VDD bumps needed        :    533  (+ same for VSS)',
    'Bump sites on 10x10 mm :   4356  at 150 um pitch',
    'Fraction used by power  :  24.5 %',
]
YIELD_SRC = [
    'import math',
    'D0 = 0.1           # defects per cm^2 (mature-ish process, assumption)',
    'alpha = 3.0        # negative-binomial clustering parameter',
    'def poisson(A):  return math.exp(-A * D0)',
    'def murphy(A):   x = A * D0; return ((1 - math.exp(-x)) / x) ** 2',
    'def seeds(A):    return 1 / (1 + A * D0)',
    'def negbin(A):   return (1 + A * D0 / alpha) ** (-alpha)',
    'print(f"D0 = {D0} /cm^2, alpha = {alpha}")',
    'print(" Area(mm2)  Poisson  Murphy   Seeds  NegBin(a=3)")',
    'for a_mm2 in [10, 25, 50, 100, 200, 400, 600, 800]:',
    '    A = a_mm2 / 100.0                  # mm^2 -> cm^2',
    '    print(f"{a_mm2:9d}  {poisson(A):7.3f} {murphy(A):7.3f} {seeds(A):7.3f} {negbin(A):10.3f}")',
]
YIELD_OUT = [
    'D0 = 0.1 /cm^2, alpha = 3.0',
    ' Area(mm2)  Poisson  Murphy   Seeds  NegBin(a=3)',
    '       10    0.990   0.990   0.990      0.990',
    '       25    0.975   0.975   0.976      0.975',
    '       50    0.951   0.951   0.952      0.952',
    '      100    0.905   0.906   0.909      0.906',
    '      200    0.819   0.821   0.833      0.824',
    '      400    0.670   0.679   0.714      0.687',
    '      600    0.549   0.565   0.625      0.579',
    '      800    0.449   0.474   0.556      0.492',
]
YPLOT_SRC = [
    'import math',
    'D0, alpha = 0.3, 3.0                         # early-ramp defect density (assumption)',
    'models = {"N": lambda x: (1 + x / alpha) ** (-alpha),   # drawn first = wins ties',
    '          "M": lambda x: ((1 - math.exp(-x)) / x) ** 2,',
    '          "S": lambda x: 1 / (1 + x),',
    '          "P": lambda x: math.exp(-x)}',
    'rows, cols = 16, 80                          # ASCII canvas: yield 0..1 vs area 0..800 mm^2',
    'grid = [[" "] * cols for _ in range(rows)]',
    'for c in range(cols):',
    '    A_cm2 = (c + 1) / cols * 8.0             # 0..8 cm^2 = 0..800 mm^2',
    '    for tag, f in models.items():',
    '        y = f(A_cm2 * D0)',
    '        r = rows - 1 - int(round(y * (rows - 1)))',
    '        if grid[r][c] == " ":',
    '            grid[r][c] = tag',
    'for r in range(rows):',
    '    label = f"{1 - r / (rows - 1):4.2f} |"',
    '    print(label + "".join(grid[r]))',
    'print("     +" + "-" * cols)',
    'print("     0" + "".join(f"{a:>10d}" for a in range(100, 900, 100)) + " mm^2")',
    'print(f"D0={D0}/cm^2  P=Poisson M=Murphy S=Seeds N=neg.binomial(alpha={alpha:.0f})")',
]
YPLOT_OUT = [
    '1.00 |N                                                                               ',
    '0.93 | NN                                                                             ',
    '0.87 |   NNN                                                                          ',
    '0.80 |      NNNS                                                                      ',
    '0.73 |        PNNNSS                                                                  ',
    '0.67 |           PNNNNSSS                                                             ',
    '0.60 |               MNNNNSSSSS                                                       ',
    '0.53 |                  PMNNNNNSSSSSSSS                                               ',
    '0.47 |                       PMNNNNNNN SSSSSSSSSS                                     ',
    '0.40 |                           PPPMMNNNNNNN    SSSSSSSSSSSSSS                       ',
    '0.33 |                                 PPPMMMNNNNNNNNNN        SSSSSSSSSSSSSSSSSSSS   ',
    '0.27 |                                        PPPPPMMMMNNNNNNNNNNNNN               SSS',
    '0.20 |                                                PPPPPPPPMMMMMMNNNNNNNNNNNNNNNNNN',
    '0.13 |                                                           PPPPPPPPPPPPPMMMMMMMM',
    '0.07 |                                                                            PPPP',
    '0.00 |                                                                                ',
    '     +--------------------------------------------------------------------------------',
    '     0       100       200       300       400       500       600       700       800 mm^2',
    'D0=0.3/cm^2  P=Poisson M=Murphy S=Seeds N=neg.binomial(alpha=3)',
]
TESTCOST_SRC = [
    '# Test cost per good die: ATE cost/second x test time / (sites x yield x efficiency)',
    'ate_rate = 0.03              # $/s fully loaded tester + handler cost (assumption)',
    'def cost_per_good(t_test, sites, yld, eff=0.9):',
    '    # eff: multi-site efficiency (index time, retests, uneven site times)',
    '    t_per_die = t_test / (sites * eff)',
    '    return ate_rate * t_per_die / yld',
    'print("  test_s  sites  yield   $/good die")',
    'for t, s, y in [(2.0, 1, 0.90), (2.0, 4, 0.90), (2.0, 16, 0.90),',
    '                (8.0, 4, 0.90), (8.0, 4, 0.60), (0.5, 32, 0.95)]:',
    '    print(f"{t:8.1f} {s:6d} {y:6.2f} {cost_per_good(t, s, y):12.4f}")',
    '# Scan test time: patterns x (chain length + capture) / shift frequency',
    'patterns, chain_len, f_shift = 5000, 2000, 50e6',
    't_scan = patterns * (chain_len + 3) / f_shift',
    'print(f"Scan time: {patterns} patterns x {chain_len} bits @ {f_shift/1e6:.0f} MHz = "',
    '      f"{t_scan*1000:.1f} ms")',
]
TESTCOST_OUT = [
    '  test_s  sites  yield   $/good die',
    '     2.0      1   0.90       0.0741',
    '     2.0      4   0.90       0.0185',
    '     2.0     16   0.90       0.0046',
    '     8.0      4   0.90       0.0741',
    '     8.0      4   0.60       0.1111',
    '     0.5     32   0.95       0.0005',
    'Scan time: 5000 patterns x 2000 bits @ 50 MHz = 200.3 ms',
]
DPPM_SRC = [
    '# Williams-Brown: defect level DL = 1 - Y^(1 - T)   (Y = yield, T = fault coverage)',
    'print(" yield  coverage    DPPM")',
    'for y in (0.90, 0.50):',
    '    for t in (0.90, 0.95, 0.99, 0.995, 0.999):',
    '        dl = 1 - y ** (1 - t)',
    '        print(f"{y:6.2f} {t:9.3f} {dl*1e6:8.0f}")',
]
DPPM_OUT = [
    ' yield  coverage    DPPM',
    '  0.90     0.900    10481',
    '  0.90     0.950     5254',
    '  0.90     0.990     1053',
    '  0.90     0.995      527',
    '  0.90     0.999      105',
    '  0.50     0.900    66967',
    '  0.50     0.950    34064',
    '  0.50     0.990     6908',
    '  0.50     0.995     3460',
    '  0.50     0.999      693',
]
ARR_SRC = [
    'import math',
    'k = 8.617e-5                       # Boltzmann constant, eV/K',
    'def af_thermal(Ea, T_use_C, T_stress_C):',
    '    Tu, Ts = T_use_C + 273.15, T_stress_C + 273.15',
    '    return math.exp(Ea / k * (1 / Tu - 1 / Ts))',
    'print("Ea(eV)  Tuse  Tstress   AF")',
    'for Ea in (0.5, 0.7, 1.0):',
    '    print(f"{Ea:5.2f} {55:5d} {125:8d} {af_thermal(Ea, 55, 125):9.1f}")',
    '# HTOL sizing: how many device-hours prove a FIT target (zero failures, 60% conf.)',
    'Ea, AF = 0.7, af_thermal(0.7, 55, 125)',
    'chi2_60_2dof = 1.833               # chi-square(0.60, 2*0+2)',
    'fit_target = 10.0                  # failures per 1e9 device-hours at use conditions',
    'dev_hours_use = chi2_60_2dof / 2 / (fit_target * 1e-9)',
    'dev_hours_stress = dev_hours_use / AF',
    'print(f"AF(0.7 eV, 55->125C) = {AF:.1f}")',
    'print(f"Zero-fail proof of {fit_target:.0f} FIT @60%: {dev_hours_use:.3g} use device-hours")',
    'print(f"  = {dev_hours_stress:.3g} device-hours at 125C, e.g. "',
    '      f"{dev_hours_stress/1000:.0f} parts x 1000 h")',
]
ARR_OUT = [
    'Ea(eV)  Tuse  Tstress   AF',
    ' 0.50    55      125      22.4',
    ' 0.70    55      125      77.7',
    ' 1.00    55      125     501.5',
    'AF(0.7 eV, 55->125C) = 77.7',
    'Zero-fail proof of 10 FIT @60%: 9.16e+07 use device-hours',
    '  = 1.18e+06 device-hours at 125C, e.g. 1180 parts x 1000 h',
]
FIT_SRC = [
    '# FIT and MTBF arithmetic for a system built from several chips',
    'parts = [("SoC (logic + SRAM)", 1, 25.0), ("DRAM", 4, 10.0),',
    '         ("PMIC", 1, 5.0), ("Flash", 1, 8.0)]   # name, count, FIT each (assumptions)',
    'total = sum(n * f for _, n, f in parts)',
    'mtbf_h = 1e9 / total',
    'print(f"System FIT = {total:.0f}  -> MTBF = {mtbf_h:.3g} h = {mtbf_h/8760:.0f} years")',
    'fleet, years = 1_000_000, 1',
    'fails = total * 1e-9 * fleet * 8760 * years',
    'print(f"Expected failures in a fleet of {fleet:,} for {years} year: {fails:.0f}")',
]
FIT_OUT = [
    'System FIT = 78  -> MTBF = 1.28e+07 h = 1464 years',
    'Expected failures in a fleet of 1,000,000 for 1 year: 683',
]
SHMOO_SRC = [
    '# Toy silicon model: alpha-power-law path delay with corner and temperature effects',
    'ALPHA, K = 1.3, 0.38          # toy constants: TT part ~1.16 GHz at 0.80 V, 25 C',
    'CORNER = {"SS": (+0.04, 0.90), "TT": (0.0, 1.0), "FF": (-0.04, 1.10)}  # dVth, mobility',
    'SRAM_VMIN = 0.62              # below this the (toy) SRAM bit-cells fail at any speed',
    'def fmax_mhz(v, corner="TT", t_c=25.0):',
    '    dvth, mob = CORNER[corner]',
    '    vth = 0.35 + dvth - 0.0015 * (t_c - 25)          # Vth falls as T rises',
    '    mob *= ((t_c + 273.15) / 298.15) ** -1.5          # mobility falls as T rises',
    '    if v <= vth:',
    '        return 0.0',
    '    return 1000.0 * mob * (v - vth) ** ALPHA / (K * v)',
    'def passes(v, f, corner="TT", t_c=25.0):',
    '    return v >= SRAM_VMIN and f <= fmax_mhz(v, corner, t_c)',
    'def shmoo(corner, t_c):',
    '    volts = [0.60 + 0.025 * i for i in range(17)]     # 0.600 .. 1.000 V',
    '    print(f"Shmoo: corner={corner} T={t_c:.0f}C   \'*\' = pass  \'.\' = fail")',
    '    for f in range(1400, 399, -100):',
    '        row = "".join("*  " if passes(v, f, corner, t_c) else ".  " for v in volts)',
    '        print(f"{f:5d} MHz | {row}")',
    '    print("          +" + "---" * len(volts))',
    '    print("   VDD(V)  " + "".join(f"{v:<6.2f}" for v in volts[::2]))',
]
SHMOO_OUT = [
    '',
]
RUNSHMOO_SRC = [
    'from shmoo import *',
    'shmoo("TT", 25)',
]
RUNSHMOO_OUT = [
    "Shmoo: corner=TT T=25C   '*' = pass  '.' = fail",
    ' 1400 MHz | .  .  .  .  .  .  .  .  .  .  .  .  .  .  *  *  *  ',
    ' 1300 MHz | .  .  .  .  .  .  .  .  .  .  .  *  *  *  *  *  *  ',
    ' 1200 MHz | .  .  .  .  .  .  .  .  .  *  *  *  *  *  *  *  *  ',
    ' 1100 MHz | .  .  .  .  .  .  .  *  *  *  *  *  *  *  *  *  *  ',
    ' 1000 MHz | .  .  .  .  .  *  *  *  *  *  *  *  *  *  *  *  *  ',
    '  900 MHz | .  .  .  *  *  *  *  *  *  *  *  *  *  *  *  *  *  ',
    '  800 MHz | .  .  *  *  *  *  *  *  *  *  *  *  *  *  *  *  *  ',
    '  700 MHz | .  *  *  *  *  *  *  *  *  *  *  *  *  *  *  *  *  ',
    '  600 MHz | .  *  *  *  *  *  *  *  *  *  *  *  *  *  *  *  *  ',
    '  500 MHz | .  *  *  *  *  *  *  *  *  *  *  *  *  *  *  *  *  ',
    '  400 MHz | .  *  *  *  *  *  *  *  *  *  *  *  *  *  *  *  *  ',
    '          +---------------------------------------------------',
    '   VDD(V)  0.60  0.65  0.70  0.75  0.80  0.85  0.90  0.95  1.00  ',
]
VMIN_SRC = [
    'from shmoo import *',
    '# Vmin at two target clocks, and Fmax at a low and a high VDD, per corner and temperature',
    'def vmin(f, corner, t_c):',
    '    v = 0.50',
    '    while v <= 1.20 and not passes(v, f, corner, t_c):',
    '        v += 0.005',
    '    return v',
    'print("corner  T(C)  Vmin@500MHz  Vmin@1GHz  Fmax@0.65V  Fmax@0.90V")',
    'for corner in ("SS", "TT", "FF"):',
    '    for t_c in (-40, 25, 125):',
    '        print(f"{corner:>6} {t_c:5d} {vmin(500, corner, t_c):11.3f} "',
    '              f"{vmin(1000, corner, t_c):10.3f} {fmax_mhz(0.65, corner, t_c):11.0f} "',
    '              f"{fmax_mhz(0.90, corner, t_c):11.0f}")',
]
VMIN_OUT = [
    'corner  T(C)  Vmin@500MHz  Vmin@1GHz  Fmax@0.65V  Fmax@0.90V',
    '    SS   -40       0.655      0.825         496        1204',
    '    SS    25       0.620      0.845         632        1097',
    '    SS   125       0.620      0.910         741         994',
    '    TT   -40       0.620      0.730         734        1508',
    '    TT    25       0.620      0.720         846        1344',
    '    TT   125       0.620      0.710         929        1192',
    '    FF   -40       0.620      0.645        1021        1852',
    '    FF    25       0.620      0.620        1096        1620',
    '    FF   125       0.620      0.620        1142        1409',
]
COST_SRC = [
    'import math',
    '# ILLUSTRATIVE assumptions only - real wafer prices, D0 and NRE are negotiated and confidential',
    '#  node   wafer$  D0/cm2  die_mm2  pkg+test$  NRE($M: masks, EDA, IP, people)',
    'NODES = [',
    '    ("65nm",  2000, 0.08, 160.0, 1.50,  15),',
    '    ("28nm",  3000, 0.09,  60.0, 1.50,  35),',
    '    ("16nm",  6000, 0.10,  35.0, 1.80,  55),',
    '    ("7nm",  10000, 0.12,  16.0, 2.00, 200),',
    '    ("5nm",  17000, 0.15,  11.0, 2.20, 400),',
    ']',
    'WAFER_MM, EDGE_MM, ALPHA = 300.0, 3.0, 3.0',
    'def dies_per_wafer(a_mm2):',
    '    d = WAFER_MM - 2 * EDGE_MM                        # usable diameter',
    '    return int(math.pi * (d / 2) ** 2 / a_mm2 - math.pi * d / math.sqrt(2 * a_mm2))',
    'def die_yield(a_mm2, d0):',
    '    return (1 + a_mm2 / 100 * d0 / ALPHA) ** (-ALPHA)  # negative binomial',
    'print(" node  mm2   DPW  yield good/wfr $/good_die unit$ | unit$ + NRE share at volume")',
    'print(" " * 48 + "|     1M    10M   100M")',
    'for name, wafer, d0, area, pkg, nre in NODES:',
    '    dpw = dies_per_wafer(area)',
    '    y = die_yield(area, d0)',
    '    good = dpw * y',
    '    die_cost = wafer / good',
    '    unit = die_cost + pkg / 0.98                      # 98% final-test yield',
    '    amort = [unit + nre * 1e6 / vol for vol in (1e6, 1e7, 1e8)]',
    '    print(f"{name:>5} {area:4.0f} {dpw:5d} {y:6.3f} {good:8.0f} {die_cost:9.2f} {unit:5.2f} |"',
    '          + "".join(f"{c:7.2f}" for c in amort))',
]
COST_OUT = [
    ' node  mm2   DPW  yield good/wfr $/good_die unit$ | unit$ + NRE share at volume',
    '                                                |     1M    10M   100M',
    ' 65nm  160   372  0.882      328      6.09  7.62 |  22.62   9.12   7.77',
    ' 28nm   60  1047  0.948      992      3.02  4.55 |  39.55   8.05   4.90',
    ' 16nm   35  1829  0.966     1766      3.40  5.23 |  60.23  10.73   5.78',
    '  7nm   16  4079  0.981     4002      2.50  4.54 | 204.54  24.54   6.54',
    '  5nm   11  5974  0.984     5877      2.89  5.14 | 405.14  45.14   9.14',
]
BE_SRC = [
    '# Break-even volume between two nodes: NRE_a + V*unit_a = NRE_b + V*unit_b',
    'def breakeven(nre_a, unit_a, nre_b, unit_b):',
    '    return (nre_b - nre_a) * 1e6 / (unit_a - unit_b)',
    '# numbers taken from the cost table above (illustrative)',
    'print(f"65nm -> 28nm pays off above {breakeven(15, 7.62, 35, 4.55)/1e6:5.1f} M units")',
    'print(f"28nm -> 7nm  pays off above {breakeven(35, 4.55, 200, 4.54)/1e6:8.0f} M units"',
    '      "  (unit cost barely moves)")',
]
BE_OUT = [
    '65nm -> 28nm pays off above   6.5 M units',
    '28nm -> 7nm  pays off above    16500 M units  (unit cost barely moves)',
]
NRE_SRC = [
    '# ILLUSTRATIVE NRE build-up for a mid-size 16nm-class SoC (all numbers are assumptions)',
    'eng = [  # phase, months, average engineers',
    '    ("Spec + architecture",  4, 10), ("RTL + verification", 12, 45),',
    '    ("Physical design",       8, 25), ("Bring-up + qual",     6, 20)]',
    'LOADED = 250e3                              # $ per engineer-year incl. overhead',
    'people = sum(m / 12 * n * LOADED for _, m, n in eng)',
    'items = {',
    '    "Engineering (people)": people,',
    '    "EDA licences":         9e6,',
    '    "Third-party IP":      12e6,              # SerDes/DDR PHY, CPU, PLLs, memory compilers',
    '    "Mask set (1 full + 1 metal respin)": 5e6 + 1.5e6,',
    '    "Test chip / MPW":      1e6,',
    '    "Package + test dev":   2.5e6,           # substrate design, probe card, load boards',
    '    "Compute + infra":      3e6,',
    '}',
    'total = sum(items.values())',
    'for k, v in items.items():',
    '    print(f"{k:36s} ${v/1e6:6.1f}M  {v/total*100:5.1f}%")',
    'print(f"{\'TOTAL NRE\':36s} ${total/1e6:6.1f}M")',
    'print(f"Engineer-years: {sum(m / 12 * n for _, m, n in eng):.0f}")',
]
NRE_OUT = [
    'Engineering (people)                 $  18.8M   35.5%',
    'EDA licences                         $   9.0M   17.1%',
    'Third-party IP                       $  12.0M   22.7%',
    'Mask set (1 full + 1 metal respin)   $   6.5M   12.3%',
    'Test chip / MPW                      $   1.0M    1.9%',
    'Package + test dev                   $   2.5M    4.7%',
    'Compute + infra                      $   3.0M    5.7%',
    'TOTAL NRE                            $  52.8M',
    'Engineer-years: 75',
]
BINS_SRC = [
    'import random',
    'from shmoo import ALPHA, K, SRAM_VMIN',
    'random.seed(1)',
    '# Monte Carlo "production": each part gets its own Vth shift and mobility factor',
    'def fmax(v, dvth, mob, t_c=85.0):',
    '    vth = 0.35 + dvth - 0.0015 * (t_c - 25)',
    '    mob *= ((t_c + 273.15) / 298.15) ** -1.5',
    '    return 1000.0 * mob * (v - vth) ** ALPHA / (K * v)',
    'parts = [(random.gauss(0, 0.02), random.gauss(1.0, 0.04)) for _ in range(10000)]',
    '# 1) Speed binning at a fixed 0.80 V, 85 C (with a 3% tester guard-band)',
    'bins = {"1200 MHz": 0, "1050 MHz": 0, "900 MHz": 0, "reject": 0}',
    'for dvth, mob in parts:',
    '    f = fmax(0.80, dvth, mob) * 0.97',
    '    key = ("1200 MHz" if f >= 1200 else "1050 MHz" if f >= 1050',
    '           else "900 MHz" if f >= 900 else "reject")',
    '    bins[key] += 1',
    'for k, n in bins.items():',
    '    print(f"bin {k:9s}: {n:5d} parts  {n / len(parts) * 100:5.1f}%  " + "#" * (n // 200))',
    '# 2) AVS: per-part voltage for 1000 MHz at 85 C versus one fixed voltage for all parts',
    'def v_needed(dvth, mob, f=1000 / 0.97):',
    '    v = SRAM_VMIN                            # memories set the floor',
    '    while fmax(v, dvth, mob) < f:',
    '        v += 0.0025',
    '    return v',
    'vs = sorted(v_needed(d, m) for d, m in parts)',
    'v_fixed = vs[int(0.999 * len(vs))]           # fixed VDD must cover the 99.9th percentile part',
    'avg_p = sum((v / v_fixed) ** 2 for v in vs) / len(vs)   # dynamic power ~ V^2',
    'print(f"Fixed VDD for 99.9% of parts : {v_fixed:.3f} V")',
    'print(f"AVS voltages: min {vs[0]:.3f}  median {vs[len(vs) // 2]:.3f}  max {vs[-1]:.3f} V")',
    'print(f"Average dynamic power with AVS: {avg_p * 100:.1f}% of the fixed-VDD power")',
]
BINS_OUT = [
    'bin 1200 MHz :   584 parts    5.8%  ##',
    'bin 1050 MHz :  6561 parts   65.6%  ################################',
    'bin 900 MHz  :  2828 parts   28.3%  ##############',
    'bin reject   :    27 parts    0.3%  ',
    'Fixed VDD for 99.9% of parts : 0.900 V',
    'AVS voltages: min 0.620  median 0.735  max 0.945 V',
    'Average dynamic power with AVS: 67.1% of the fixed-VDD power',
]


# =============================================================================
#     CHAPTER 20 - PACKAGING, 2.5D/3D INTEGRATION AND CHIPLETS
# =============================================================================
def _ch20():
    chapter("Packaging, 2.5D/3D Integration and Chiplets", newpage=False)
    p("The GDSII you signed off in Chapter 19 describes a sliver of silicon a "
      "fraction of a millimetre thick that cannot survive a fingerprint, "
      "cannot be soldered to a board and would cook itself within seconds at "
      "full power. The **package** turns that die into a product: it carries "
      "signals and power between micron-scale pads on the die and "
      "millimetre-scale balls on a printed circuit board, it pulls heat out, "
      "and it protects the die mechanically and chemically for ten or more "
      "years. For modern high-performance parts the package has become a "
      "design problem as hard as the die itself: a large AI accelerator is "
      "no longer one chip but a system of several compute dies, stacks of "
      "HBM memory and a silicon interposer, all assembled in one package.")
    p("Packaging is often treated as somebody else's problem until it is "
      "too late. In reality the package decisions - bump map, pad ring, "
      "power delivery, thermal solution - must be made during floorplanning "
      "(Chapter 14), and the package engineer is part of the core team from "
      "architecture onward. This chapter gives the ASIC engineer enough "
      "depth to have that conversation.")

    h2("What a package does")
    tbl(["Role", "What it means", "Typical owner concerns"], [
        ["Electrical: signals", "Route every die I/O to a board ball with "
         "controlled impedance and low crosstalk",
         "Trace length, impedance (50 ohm single-ended, 85-100 ohm "
         "differential), return paths, loss at SerDes Nyquist"],
        ["Electrical: power", "Deliver tens to hundreds of amps with "
         "millivolts of droop", "Number of power balls/bumps, plane "
         "layers, loop inductance, decoupling capacitors in the package"],
        ["Thermal", "Move watts from the junction to ambient",
         "theta_JC, lid and thermal interface material (TIM), heat "
         "spreader, hot spots"],
        ["Mechanical", "Hold the die flat, survive assembly and "
         "temperature cycling", "Warpage, coefficient of thermal expansion "
         "(CTE) mismatch, underfill, solder joint fatigue"],
        ["Environmental", "Keep moisture, ions and light out",
         "Moisture sensitivity level (MSL), mould compound, corrosion"],
        ["Interface to the board", "Fit the customer's PCB rules and "
         "assembly line", "Ball pitch (e.g. 0.4-1.0 mm), body size, "
         "footprint, rework"],
    ], widths=[1.3, 2.4, 2.8], caption="Table 20.1 - The jobs of a package.",
        bold_first=True)

    h2("Package families")
    p("Package types differ in how the die is connected (wire bond or flip "
      "chip), what it is mounted on (lead frame, laminate substrate, "
      "redistribution layers) and how the package attaches to the board "
      "(leads, lands or solder balls). The main families an ASIC team "
      "chooses from are:")
    tbl(["Package", "Construction", "I/O range", "Typical use"], [
        ["QFN (quad flat no-lead)", "Die on a copper lead frame, wire "
         "bonded, moulded; exposed thermal pad underneath", "8-100",
         "Low-cost MCUs, PMICs, sensors, RF"],
        ["QFP / LQFP", "Lead frame with gull-wing leads on four sides",
         "32-256", "Legacy MCUs, industrial parts that need visual solder "
         "inspection"],
        ["Wire-bond BGA (PBGA)", "Die wire bonded to a laminate "
         "substrate with solder balls on the bottom", "100-700",
         "Consumer SoCs, networking, cost-sensitive mid-range"],
        ["Flip-chip BGA (FCBGA)", "Die flipped face-down onto a "
         "build-up substrate through bumps; lid or bare die", "500-5000+",
         "CPUs, GPUs, FPGAs, switches, AI accelerators"],
        ["WLCSP (fan-in)", "Balls placed directly on the die through "
         "an RDL; package = die size", "4-400",
         "Mobile: PMICs, RF, audio, sensors"],
        ["Fan-out wafer/panel level (FOWLP, InFO-like)", "Dies embedded "
         "in a reconstituted mould wafer; RDL fans out beyond the die edge",
         "100-2000+", "Mobile application processors, RF modules, "
         "multi-die integration"],
        ["2.5D / 3D", "Several dies on an interposer or stacked (see "
         "20.5-20.6)", "Thousands to 100,000s of die-to-die wires",
         "HPC, AI, HBM-based products"],
    ], widths=[1.6, 2.8, 1.0, 2.0], caption="Table 20.2 - Main package "
       "families (I/O ranges are typical, not limits).", bold_first=True)
    diagram([
        "  QFN (wire bond, lead frame)          Flip-chip BGA",
        "",
        "    bond wire                          lid / heat spreader",
        "     .----.   mould compound          +==================================+",
        "    /  ##  \\                          |   TIM1                           |",
        "   | [ DIE ] |                        |   [#########  DIE  #########]    |",
        "   |=========| die-attach             |    o o o o o o o o o o o o o     |  <- bumps",
        "  _|_________|_  exposed pad          |    ~~~~~~~~ underfill ~~~~~~~    |",
        " |_|         |_| leads/lands          +----------------------------------+",
        "                                      |  build-up substrate (RDL,        |",
        "                                      |  core, planes, vias)             |",
        "                                      +----------------------------------+",
        "                                        O   O   O   O   O   O   O   O   O   <- balls",
        "  =============================== PCB ===========================================",
    ], "Figure 20.1 - Cross-sections: a wire-bonded QFN and a lidded "
       "flip-chip BGA (not to scale).")

    h2("Wire bond versus flip chip")
    p("In **wire bonding** the die sits face-up and fine gold or copper "
      "wires (typically 15-25 um diameter) connect pads on the die periphery "
      "to the lead frame or substrate. It is cheap, mature and flexible, but "
      "the I/O count is limited by the die perimeter, each wire adds "
      "roughly 1 nH of inductance per millimetre, and all power has to enter "
      "from the edge - which becomes an IR-drop problem for large, "
      "power-hungry dies.")
    p("In **flip chip** the die is turned face-down and connected through "
      "an **area array** of bumps across its whole surface. Classic "
      "**C4** (controlled collapse chip connection) solder bumps are on "
      "a pitch of roughly 130-200 um; **copper pillar** bumps with a solder "
      "cap allow finer pitch (tens of um) with less collapse; **micro-bumps** "
      "on 2.5D/3D interposers reach roughly 25-55 um pitch. After reflow the "
      "gap between die and substrate is filled with **underfill** epoxy, "
      "which shares the thermo-mechanical strain so that the bumps do not "
      "crack when the silicon (CTE about 2.6 ppm/K) and the organic "
      "substrate (CTE roughly 15-17 ppm/K) expand by different amounts.")
    tbl(["Aspect", "Wire bond", "Flip chip"], [
        ["I/O placement", "Periphery only (pad ring)", "Whole die area "
         "(bump array); I/O can sit near the logic it serves"],
        ["Power delivery", "From the edges; long wires; IR drop in the "
         "centre", "Power bumps everywhere over the grid; much lower R "
         "and L"],
        ["Inductance", "About 1 nH/mm of wire; few nH per connection",
         "Tens of pH per bump; loop L dominated by substrate"],
        ["Heat path", "Through die back into the lead frame / board",
         "Through the die backside into lid and heat sink"],
        ["Cost", "Lowest for low pin counts", "Higher: bumping, "
         "build-up substrate, underfill"],
        ["Die design impact", "Pad-limited vs core-limited trade-off "
         "(Chapter 14)", "Bump plan, RDL, bump-to-I/O assignment are part "
         "of the floorplan"],
    ], widths=[1.3, 2.4, 2.8], caption="Table 20.3 - Wire bond and flip chip "
       "compared.", bold_first=True)
    box("intuit", "Pad-limited dies",
        "If a wire-bonded design needs 400 signal and power pads at a 60 um "
        "pad pitch, the perimeter must be at least 24 mm, i.e. a die of 6 x 6 "
        "mm even if the logic fits in 2 x 2 mm. The die is **pad-limited** "
        "and you pay for empty silicon. Moving to flip chip (or staggered "
        "pads) turns it into a core-limited die and can halve its cost.")

    h2("Substrates, RDL and the package design flow")
    p("A flip-chip **substrate** is a small, very dense PCB. A typical "
      "build-up substrate has a glass-reinforced core with plated through "
      "holes and several thin build-up layers on each side (written e.g. "
      "4-2-4: four build-up layers, a two-layer core, four more), with "
      "laser-drilled micro-vias and line/space down to roughly 8-15 um in "
      "advanced substrates. Layers are allocated to signal routing, power "
      "planes and ground planes, much like a board stack-up. Substrates are "
      "a major part of the cost of a large FCBGA and have their own "
      "supply constraints (ABF build-up film shortages have delayed products "
      "in the past).")
    p("A **redistribution layer (RDL)** is one or more thin metal layers "
      "(copper, polyimide dielectric) patterned on top of a die or a "
      "reconstituted wafer to move connections from where the pads are to "
      "where the bumps or balls must be. Fan-in WLCSP uses RDL on the die "
      "itself; fan-out uses RDL that extends beyond the die edge onto the "
      "mould compound, which is how InFO-style packages achieve many I/Os "
      "and thin profiles without a laminate substrate.")
    diagram([
        "  Die team                     Package team                     Board team",
        "  --------                     ------------                     ----------",
        "  I/O list, pad/bump   ---->   bump map + ball map   <----     board escape,",
        "  locations, power             substrate stack-up               layer count,",
        "  domains, current     <----   routing, planes         ---->    ball pitch, PDN",
        "  per domain                   RLC extraction                   decap plan",
        "        \\                          |                               /",
        "         \\______  chip-package-board co-simulation (SI/PI/thermal) _/",
        "                             |",
        "                  package netlist + models (S-params, RLC)",
        "                  -> die sign-off (IR/EM, SSN) and board sign-off",
    ], "Figure 20.2 - Package design is a three-way negotiation that starts "
       "at floorplanning.")
    p("Package design is done in dedicated tools (Cadence Allegro Package "
      "Designer / SiP Layout, Siemens Xpedition Substrate Integrator, "
      "Synopsys 3DIC Compiler for multi-die). The deliverables that come "
      "back to the die team are a **bump/ball map**, a package netlist, "
      "extracted package models (RLC per net or S-parameters) for signal "
      "integrity, and a package power model for chip-package power "
      "integrity analysis (Chapter 18).")

    h2("2.5D integration: interposers and bridges")
    p("**2.5D** places several dies side by side on a common high-density "
      "interconnect layer that routes thousands of fine wires between them. "
      "The dies are not stacked on each other - hence '2.5'.")
    bul([
        "**Silicon interposer (CoWoS-like).** A large passive silicon die, "
        "made on an older process, carrying several metal layers with "
        "sub-micron wires and **through-silicon vias (TSVs)** down to the "
        "package substrate. Logic dies and HBM stacks sit on it via "
        "micro-bumps. It gives the densest die-to-die wiring but the "
        "interposer can exceed the lithography reticle size (stitched "
        "exposures) and is costly.",
        "**Silicon bridge (EMIB-like).** Instead of a full interposer, a "
        "small silicon bridge die is embedded in the organic substrate only "
        "under the edges of the dies it connects. Only the die-to-die "
        "wires use fine pitch; everything else uses ordinary substrate "
        "bumps. Cheaper and scales to large packages.",
        "**Organic / RDL interposer (CoWoS-R, InFO-type).** A fan-out RDL "
        "layer stack acts as the interposer: coarser than silicon (line "
        "widths of a couple of um) but cheaper, larger and mechanically "
        "more compliant.",
    ])
    diagram([
        "        HBM stack          logic die (SoC)          HBM stack",
        "       +--------+      +--------------------+     +--------+",
        "       | DRAM   |      |                    |     | DRAM   |",
        "       | DRAM   |      |                    |     | DRAM   |",
        "       | base   |      |                    |     | base   |",
        "       +-oooooo-+      +-oooooooooooooooooo-+     +-oooooo-+   <- micro-bumps",
        "  +---------------------------------------------------------------+",
        "  |  silicon interposer: fine BEOL wiring  ======  ======         | ",
        "  |      |TSV|              |TSV|                |TSV|           |",
        "  +---o-----o-----o-----o-----o-----o-----o-----o-----o-----o----+  <- C4 bumps",
        "  |            organic build-up substrate                        |",
        "  +---------------------------------------------------------------+",
        "      O    O    O    O    O    O    O    O    O    O    O    O      <- BGA balls",
    ], "Figure 20.3 - A 2.5D package: logic die and HBM on a silicon "
       "interposer (CoWoS-like).")

    h2("3D integration: TSVs and hybrid bonding")
    p("**3D** stacks dies vertically. Vertical connections pass through "
      "the silicon in **TSVs** - copper-filled holes typically a few "
      "microns to ~10 um in diameter - or directly between face-to-face "
      "bonded dies. Two bonding technologies dominate:")
    bul([
        "**Micro-bump (solder) stacking.** Dies are thinned, TSVs expose on "
        "the backside and the next die is soldered on with micro-bumps "
        "(pitch of tens of um). HBM DRAM stacks are built this way (or "
        "with newer hybrid bonding in future generations).",
        "**Hybrid bonding (Cu-Cu direct bond, SoIC-like, Foveros "
        "Direct-like).** Polished copper pads embedded in oxide are bonded "
        "directly without solder, at pitches of roughly 10 um down to a few "
        "um. This gives 10-100x the connection density of micro-bumps and "
        "very low energy per bit, at the cost of extreme surface flatness "
        "and cleanliness requirements.",
    ])
    tbl(["Interconnect", "Pitch (typical order)", "Density per mm^2",
         "Energy/bit (order)"], [
        ["Package substrate trace (2D MCM)", "100-150 um bump", "~50-100",
         "~1-2 pJ/bit (SerDes-less D2D)"],
        ["Silicon interposer micro-bump", "40-55 um", "~400-600",
         "~0.3-0.5 pJ/bit"],
        ["Hybrid bond", "3-10 um", "10,000-100,000", "<0.1 pJ/bit"],
    ], widths=[2.2, 1.5, 1.4, 1.8], caption="Table 20.4 - Orders of magnitude "
       "of die-to-die connection technologies (values vary widely by "
       "vendor and generation).", bold_first=True)
    box("warn", "Pitfall: 3D is a thermal problem first",
        "Stacking a hot logic die under (or over) another die multiplies "
        "power density and puts silicon, bond layers and possibly DRAM in "
        "the heat path. DRAM retention degrades at high temperature, so a "
        "memory-on-logic stack may force refresh-rate increases or power "
        "caps. Always run a thermal model of the stack before committing "
        "to a 3D architecture - and check that TSV keep-out zones (stress "
        "affects nearby transistor mobility) are in the floorplan.")

    h2("Chiplets, UCIe and HBM")
    p("A **chiplet** architecture splits what would have been one large "
      "monolithic SoC into several smaller dies assembled in one package. "
      "The motivations are economic and practical:")
    bul([
        "**Yield.** Yield falls roughly exponentially with die area "
        "(Chapter 21). Four 150 mm^2 dies can yield far better than one "
        "600 mm^2 die, and bad chiplets are discarded before assembly.",
        "**Reticle limit.** A single exposure field is about 26 x 33 mm "
        "(~858 mm^2); beyond that you must use multiple dies.",
        "**Mixed nodes.** Put compute on the leading-edge node and I/O, "
        "SerDes and analog - which scale poorly - on a cheaper mature node.",
        "**Reuse and product variants.** One compute chiplet plus a "
        "different I/O die yields a family of products with one tapeout "
        "of the expensive part.",
    ])
    p("The price is die-to-die (D2D) interfaces on every chiplet (area, "
      "power, latency), assembly cost and yield, a far harder test problem "
      "(below) and multi-die sign-off. Standard D2D interfaces make "
      "chiplets from different teams or vendors interoperable: **UCIe** "
      "(Universal Chiplet Interconnect Express) defines a physical layer "
      "for standard (organic substrate) and advanced (interposer/bridge) "
      "packages, a die-to-die adapter with CRC/retry, and protocol mapping "
      "for PCIe, CXL and streaming traffic; BoW (Bunch of Wires) is a "
      "simpler open alternative. The protocol details are covered in "
      "Chapter 22 of the companion Communication Protocols guide; here the "
      "point is that the D2D PHY is placed at the die edge facing its "
      "partner, its bump region is fixed by the standard, and it must be "
      "floorplanned together with the package.")
    p("**HBM (High Bandwidth Memory)** stacks several DRAM dies on a base "
      "(logic) die connected by TSVs, and exposes a very wide interface "
      "(1024 data bits per stack in HBM2/HBM3, doubled to 2048 in HBM4) "
      "at moderate per-pin rates. Because thousands of wires are needed, "
      "HBM requires an interposer or bridge. The ASIC team integrates an "
      "HBM controller and PHY IP, places the PHY at the die edge with its "
      "fixed bump footprint aligned to the HBM stack, and co-designs the "
      "interposer routing (short, length-matched, typically a few mm). "
      "Memory interfaces including HBM are covered in Chapter 20 of the "
      "companion Communication Protocols guide.")
    box("key", "Known-good die (KGD)",
        "In a multi-die package, one bad die scraps the whole assembly - "
        "including several expensive good dies and the interposer. If each "
        "of N dies has probability p of being good after wafer test, the "
        "assembled package is good with probability about p^{N} (ignoring "
        "assembly yield). Four dies at 98% give 92%; at 90% only 66%. So "
        "chiplets must be tested to **known-good-die** quality at wafer "
        "sort: full-speed tests, burn-in-like screens where needed and "
        "access to D2D interfaces through loopback or DFT (IEEE 1838 "
        "defines a test access architecture for 3D stacks), because "
        "micro-bumps are too small and fragile for conventional probing "
        "at full count.")

    h2("Package-chip co-design: bumps, power and signal integrity")
    h3("Bump planning")
    p("The **bump map** assigns every bump site on a flip-chip die to a "
      "signal, a power net or ground. Signal bumps sit close to the I/O "
      "cells they serve, high-speed differential pairs get shielding "
      "ground bumps, and power/ground bumps are spread across the core in "
      "a regular pattern that aligns with the top-metal power grid "
      "(Chapter 14). The number of power bumps is set by the current each "
      "bump can carry without electromigration failure and by the IR drop "
      "budget. A first-order budget is easy to compute:")
    code(BUMPS_SRC, caption="bumps.py - first-order power bump count "
         "(all inputs are assumptions).")
    out(BUMPS_OUT, caption="Output of bumps.py (python3).")
    p("A quarter of all bump sites go to one supply pair, before counting "
      "I/O supplies, other core domains and signals. This is why large "
      "flip-chip dies often have far more power and ground bumps than "
      "signal bumps, and why the bump plan must be frozen early: every "
      "change moves top-level power straps.")
    h3("Power delivery and simultaneous switching noise")
    p("The power delivery network (PDN) runs from the voltage regulator on "
      "the board, through board planes and decoupling capacitors, package "
      "balls, package planes and package capacitors, bumps and finally the "
      "on-die grid and on-die decap. Each stage has resistance and "
      "inductance, and together with the capacitances they form resonances. "
      "The designer targets a **PDN impedance** below Z_target = "
      "(allowed ripple) / (transient current) across frequency, typically "
      "from DC up to hundreds of MHz: the VRM covers low frequencies, board "
      "and package capacitors the middle, and on-die capacitance the "
      "highest frequencies. The worst droop is usually at the **first "
      "droop** resonance (tens to ~200 MHz) between package inductance and "
      "on-die capacitance.")
    _eqa(["Z_target = dV_allowed / dI_step       e.g. 0.05 V x 0.75 V / 20 A  ~ 1.9 mohm",
        "",
        "V_noise ~ L_loop x dI/dt              (inductive, 'L di/dt' noise)",
        "",
        "f_res = 1 / (2 x pi x sqrt(L_pkg x C_die))   first-droop resonance"],
       caption="Power integrity rules of thumb.")
    p("**Simultaneous switching noise (SSN)**, also called ground bounce, "
      "occurs when many output drivers switch at once and their combined "
      "current ramp flows through the shared inductance of the package "
      "power and ground connections. The script below shows why output "
      "banks need enough dedicated power/ground pins:")
    code(SSN_SRC, caption="ssn.py - ground bounce of an output bank.")
    out(SSN_OUT, caption="Output of ssn.py (python3).")
    p("32 outputs on a single ground wire would bounce the local ground by "
      "over a volt - enough to cause false switching in quiet inputs. "
      "Remedies: more power/ground pins per I/O bank (I/O libraries "
      "specify a maximum number of simultaneously switching outputs per "
      "supply pair), slew-rate-controlled drivers, staggered switching, "
      "differential signalling, on-package decoupling and flip chip.")
    h3("Package parasitics and signal integrity")
    p("Every package net has series resistance and inductance and "
      "capacitance to its neighbours and planes. For slow I/O a lumped RLC "
      "per pin (typical orders: a few nH and ~1 pF for wire-bond BGA "
      "nets, a fraction of a nH for flip-chip nets) is enough. For "
      "multi-gigabit SerDes, DDR and HBM the package is characterised as "
      "**S-parameters** (insertion loss, return loss, crosstalk) and "
      "simulated end to end with the die I/O model (IBIS or IBIS-AMI) "
      "and the board channel. Via stubs, ball-field breakout and plane "
      "changes create impedance discontinuities that show up as "
      "reflections in the eye diagram.")

    h2("Thermal design")
    p("Heat flows from the transistor junctions through the silicon to the "
      "package and on to ambient. Engineers model this path as a chain of "
      "**thermal resistances** (in deg C per watt), just as they would "
      "resistors in series:")
    _eqa(["Tj = Ta + P x theta_JA",
        "",
        "theta_JA ~ theta_JC + theta_CS + theta_SA     (junction->case->sink->ambient)",
        "",
        "Tj = Tc + P x theta_JC        (when the case temperature is known)"],
       caption="Steady-state junction temperature.")
    p("theta_JA is not a property of the package alone: JEDEC JESD51 "
      "defines how it is measured on standard test boards (1s or 2s2p) in "
      "still air or a wind tunnel, and the real value on your board can "
      "differ substantially. theta_JC measures the path to the top of the "
      "package (important when a heat sink is attached); psi_JT and "
      "psi_JB are characterisation parameters used to estimate Tj from a "
      "measured case-top or board temperature. The calculation itself is "
      "simple enough to script:")
    code(TJ_SRC, caption="tj.py - junction temperature for several package "
         "and cooling options (illustrative theta values).")
    out(TJ_OUT, caption="Output of tj.py (python3).")
    p("A 6 W chip is far too hot for a small QFN and even for a bare BGA "
      "in a warm enclosure; with a heat sink it is comfortable. Typical "
      "maximum junction temperatures are 105-125 deg C for commercial "
      "and industrial parts and up to 150 deg C for automotive grade 0. "
      "Remember that leakage rises strongly with temperature, which raises "
      "power, which raises temperature: at high power densities the "
      "calculation must iterate to check for **thermal runaway**.")
    bul([
        "**Heat spreaders and lids** flatten hot spots; **TIM1** (between "
        "die and lid) and **TIM2** (between lid and heat sink) are often "
        "the largest resistances in the stack.",
        "**Bare-die (lidless)** packages remove one TIM layer and are used "
        "for the highest-power parts, with careful mechanical design of the "
        "heat-sink pressure.",
        "**Hot spots** matter as much as total power: a 1 mm^2 block at "
        "several W/mm^2 can exceed Tj_max even when the average is fine. "
        "Thermal-aware floorplanning spreads hot blocks apart and places "
        "on-die temperature sensors at predicted hot spots.",
        "**Transient thermal** behaviour (seconds of time constant) is "
        "what dynamic thermal management (throttling, DVFS) exploits: "
        "turbo modes run above sustainable power for short bursts.",
    ])

    h2("Package reliability and qualification")
    p("The package fails in different ways from the die. The dominant "
      "mechanisms are thermo-mechanical: every power cycle and ambient "
      "temperature swing strains the joints because materials expand by "
      "different amounts.")
    tbl(["Mechanism", "Cause", "Test / mitigation"], [
        ["Solder joint fatigue", "CTE mismatch between package and board "
         "under temperature cycling", "Temperature cycling (e.g. JESD22-"
         "A104, -55/+125 deg C), board-level reliability tests; underfill, "
         "ball alloy choice"],
        ["Bump cracking / white bumps", "Die-substrate CTE mismatch; "
         "stress on fragile low-k dielectrics under bumps", "Underfill, "
         "chip-package interaction (CPI) rules, bump keep-outs"],
        ["Warpage", "Asymmetric layer stack and CTE; large bodies bow "
         "during reflow", "Balanced stack-up, stiffener rings, warpage "
         "measured versus temperature (shadow moire)"],
        ["Delamination / popcorn", "Absorbed moisture turns to steam in "
         "reflow", "MSL rating (J-STD-020) and dry-pack; bake before reflow"],
        ["Wire bond failures", "Intermetallic growth, corrosion (Cu wire), "
         "wire sweep", "High-temperature storage, HAST, bond process control"],
        ["Electromigration in bumps", "High current density in bumps and "
         "under-bump metallisation", "Current-per-bump limits in the bump "
         "plan (see above)"],
    ], widths=[1.4, 2.3, 2.9], caption="Table 20.5 - Package failure "
       "mechanisms.", bold_first=True)
    box("expert", "Interview insight: why not always use flip chip?",
        "A good answer weighs cost against need: flip chip requires wafer "
        "bumping, a more expensive build-up substrate and underfill, and "
        "its benefits (area I/O, low inductance, backside heat path) only "
        "pay off above roughly a few hundred I/Os, a few watts, or with "
        "high-speed interfaces. A 50-pin sensor hub belongs in a QFN or "
        "WLCSP; a 300 W accelerator has no choice. Mention that the "
        "decision constrains the floorplan (pad ring versus bump array) "
        "and must be made at architecture time.")
    box("warn", "Pitfall: freezing the die before the package",
        "Teams that finish the floorplan first and 'throw it over the wall' "
        "to packaging often discover that the ball map cannot escape on "
        "the customer's board in the allowed layer count, that differential "
        "pairs cross, or that one supply has too few balls. The fix then "
        "needs a die re-floorplan late in the schedule. Hold a joint "
        "die/package/board review before floorplan sign-off.")

    h2("Summary")
    bul([
        "The package provides electrical, thermal, mechanical and "
        "environmental functions; it is designed concurrently with the "
        "floorplan, not after tapeout.",
        "Families range from lead-frame QFN/QFP through wire-bond and "
        "flip-chip BGA to WLCSP and fan-out; flip chip gives area I/O, low "
        "inductance and a backside heat path at higher cost.",
        "2.5D uses silicon interposers, embedded bridges or RDL interposers "
        "for dense die-to-die wiring; 3D stacks dies with TSVs, micro-bumps "
        "or hybrid bonding.",
        "Chiplets trade D2D interface overhead and assembly complexity for "
        "yield, reticle-limit relief and mixed-node reuse; they require "
        "known-good-die testing and standards such as UCIe.",
        "Bump planning, PDN impedance, SSN and package parasitics are "
        "co-designed with the chip; Tj = Ta + P x theta_JA sets the "
        "thermal solution.",
        "Package reliability is dominated by CTE-driven fatigue, warpage "
        "and moisture; it is qualified with temperature cycling, MSL and "
        "related JEDEC tests.",
    ])

    h2("Exercises")
    bul([
        "A wire-bonded die needs 320 pads at 50 um pitch in a single row. "
        "What is the minimum square die size? If the logic needs only 4 "
        "mm^2, estimate how much silicon area is wasted.",
        "A 15 W chip in an FCBGA has theta_JC = 0.2 C/W, TIM2 = 0.15 C/W "
        "and a heat sink of 3.0 C/W. What is Tj at 50 deg C ambient? What "
        "sink resistance is needed to keep Tj <= 95 deg C?",
        "Modify bumps.py for a 1.0 V, 100 W die of 20 x 20 mm at 130 um "
        "bump pitch. What fraction of bump sites go to VDD/VSS?",
        "Four chiplets are assembled in one package, and 1% of the dies "
        "that pass wafer sort are actually defective (test escapes). "
        "Estimate the package yield from escapes alone, then repeat for "
        "an escape rate of 0.1%. Why does the escape rate matter more than "
        "the raw wafer-sort yield for multi-die packages?",
        "Explain, with a sketch, why an HBM stack must be on an interposer "
        "or bridge rather than an ordinary organic substrate.",
        "List three pieces of information the die team must give the "
        "package team before a first bump map can be drawn.",
    ], ordered=True)


# =============================================================================
#     CHAPTER 21 - MANUFACTURING TEST, YIELD AND RELIABILITY
# =============================================================================
def _ch21():
    chapter("Manufacturing Test, Yield and Reliability")
    p("Every die the foundry ships is a gamble: some fraction carry "
      "defects - a particle that shorted two wires, a void in a via, a "
      "transistor with a weak gate oxide. **Manufacturing test** separates "
      "good dies from bad ones using the DFT structures designed in "
      "Chapter 10. **Yield** is the fraction that pass, and it sets the "
      "cost per good die. **Reliability** is about the dies that pass "
      "today but might fail after months or years in the field. The three "
      "are tightly linked: test quality determines how many defective "
      "parts escape to customers (DPPM), and screens such as burn-in "
      "exist to catch parts that would fail early in life.")
    p("Ownership: the **product/test engineering** team writes and "
      "maintains test programs and runs production test; **yield "
      "engineering** (with the foundry) analyses failures and drives "
      "yield up; **reliability/quality** engineering plans qualification "
      "and owns field-return analysis. The design team delivers the DFT "
      "patterns, test specification and failure diagnosis support.")

    h2("The test flow: from wafer to shipped part")
    diagram([
        " FAB         WAFER SORT (probe)        ASSEMBLY      FINAL TEST (FT)       SHIP",
        " -----       ------------------        --------      ---------------       ----",
        " wafer  ->  probe card touches pads -> saw, pick  -> handler + socket  ->  tape",
        " out        or bumps of each die       good dies,    full test at hot/     & reel",
        "            - continuity, IDDQ         package       cold, speed bin,",
        "            - scan/ATPG, MBIST         (Ch. 20)      burn-in (if any),",
        "            - analog trim, fuses                     SLT (if any)",
        "            -> wafer map (bins)                      -> bin + mark",
        "",
        "  Parametric test (PCM/WAT) on scribe-line structures runs in the fab before sort",
    ], "Figure 21.1 - A typical production test flow.")
    h3("Wafer sort")
    p("At **wafer sort** (also called wafer probe or CP, chip probe) a "
      "**probe card** with hundreds to tens of thousands of needles or "
      "MEMS probes contacts the pads or bumps of one or several dies at "
      "once. A **prober** steps the wafer under the card. The tester "
      "applies power, checks continuity and shorts, measures supply "
      "currents (including IDDQ where meaningful), runs scan/ATPG and "
      "memory BIST, and trims analog blocks, programming the results into "
      "eFuses or OTP. Each die gets a **bin** number recorded in a **wafer "
      "map**; bad dies are inked or, more commonly today, tracked "
      "electronically so that assembly picks only good dies. Sort cannot "
      "usually run everything at full speed or temperature (contact "
      "resistance, probe inductance), which is why a final test follows.")
    h3("Final test")
    p("After packaging, a **handler** places each part in a **socket** on "
      "a **load board** attached to the tester. Final test repeats the "
      "structural tests (the package may have introduced defects), adds "
      "at-speed functional tests, I/O parametric tests (VOH/VOL, leakage, "
      "timing), SerDes loopback and eye tests, and runs at the specified "
      "temperature corners (e.g. hot at 85-125 deg C, sometimes cold). "
      "Parts are sorted into bins by result and speed, then marked and "
      "packed.")

    h2("ATE architecture and the test program")
    p("**Automatic test equipment (ATE)** - families such as Advantest "
      "V93000/T2000 or Teradyne UltraFLEX/J750 - consists of a test head "
      "with many **pin electronics** channels (each able to drive and "
      "compare a digital waveform with programmable levels and timing), "
      "**device power supplies (DPS)** with current measurement, "
      "**parametric measurement units (PMU)** for force-voltage/measure-"
      "current tests, and optional analog, RF and high-speed instruments. "
      "A workstation runs the **test program**.")
    diagram([
        "   +-------------------- ATE mainframe / test head ---------------------+",
        "   | pin electronics x N   DPS (power)   PMU   AWG/digitiser   RF/HSIO  |",
        "   +-----------------------------------+--------------------------------+",
        "                                       |  pogo pins",
        "                         +-------------+-------------+",
        "                         |   load board / probe card  |  relays, decaps,",
        "                         |   socket or probe needles  |  loopback paths",
        "                         +-------------+-------------+",
        "                                       |",
        "                                  [ DUT ]   <- handler/prober controls",
        "                                               temperature and indexing",
    ], "Figure 21.2 - ATE, interface hardware and the device under test.")
    p("A test program is an ordered **test flow** of test suites: "
      "continuity, leakage, power-up and IDD, scan chain integrity, stuck-at "
      "ATPG, transition (at-speed) ATPG, memory BIST, analog/PLL tests, "
      "functional vectors, I/O specs. Each test has limits and a failing "
      "**soft bin** that maps to a **hard bin** (the physical sort "
      "category). Patterns come from the DFT tools as STIL or WGL files "
      "(Chapter 10) and are converted to the tester's format. The program "
      "also logs data (datalogs, STDF format) for yield analysis.")
    box("tip", "The test hand-off package",
        "Design/DFT delivers to test engineering: ATPG patterns (STIL) with "
        "expected responses and fault coverage reports; MBIST controller "
        "operation and expected signatures; a pin list with levels and "
        "timing; power-up sequence; analog trim procedures; the JTAG/IJTAG "
        "access description (BSDL for boundary scan, ICL/PDL for IEEE 1687 "
        "networks); and diagnosis support (failing-pattern to fault "
        "mapping). Missing any of these costs weeks on the tester.")

    h2("Test time and test cost")
    p("Test is expensive capital equipment amortised over seconds of "
      "tester time. The cost of test per good die is roughly the tester "
      "cost per second, times the test time, divided by the number of "
      "sites tested in parallel and by the yield. Scan test time is set "
      "by the number of patterns and the length of the longest scan "
      "chain - the motivation for scan compression (Chapter 10).")
    _eqa(["t_scan ~ N_patterns x (L_chain + capture cycles) / f_shift",
        "",
        "Cost_test/good die ~ (rate $/s) x t_test / (N_sites x site efficiency x yield)"],
       caption="Test time and cost.")
    code(TESTCOST_SRC, caption="testcost.py - cost of test per good die "
         "(the $/s rate is an assumption).")
    out(TESTCOST_OUT, caption="Output of testcost.py (python3).")
    p("Multi-site testing is the biggest lever: 16 sites cut cost per die "
      "16-fold if the tester has enough channels and the sites run "
      "concurrently. That is why test engineers push the design team to "
      "reduce the number of pins that must be contacted (reduced pin-count "
      "test through JTAG or a few scan pins), and why a 200 ms scan test "
      "matters: it is often the largest item in the budget.")

    h2("Binning, speed binning and adaptive test")
    p("**Binning** sorts tested parts into categories: hard bin 1 = good; "
      "other bins record the failure class (opens/shorts, leakage, scan, "
      "MBIST, functional). Many products also **speed bin**: parts are "
      "tested at several frequencies (or at several voltages for a fixed "
      "frequency) and sold as different SKUs; a CPU line might sell the "
      "fastest parts at a premium. Related techniques include **fusing "
      "off** defective cores or cache ways to sell partially good dies "
      "(harvesting), and programming per-part voltage tables "
      "(**adaptive voltage scaling**, AVS) into fuses so that fast, leaky "
      "parts run at lower voltage and slow parts at higher voltage.")
    p("**Adaptive test** uses data to change the test flow on the fly: "
      "skipping tests that never fail for a stable lot (test time "
      "reduction), adding tests when a wafer looks unusual, or rejecting "
      "**outliers** - dies that pass all limits but whose measurements "
      "sit far from their neighbours (part average testing, PAT, and "
      "nearest-neighbour residual methods, mandatory practice for "
      "automotive per AEC-Q001). A die that passes but has an IDDQ three "
      "sigma above its neighbours is more likely to fail in the field.")

    h2("Burn-in and system-level test")
    p("**Burn-in** operates parts at elevated voltage and temperature "
      "(e.g. 125 deg C and 1.1-1.4x nominal voltage) for hours to "
      "accelerate latent defects to failure before shipment - pushing the "
      "population past the infant mortality region of the bathtub curve "
      "(below). It is expensive (ovens, burn-in boards, hours of time, and "
      "some lifetime consumed), so many consumer products skip it or use "
      "short **wafer-level burn-in** or high-voltage stress tests instead, "
      "while automotive, server and aerospace products commonly use it.")
    p("**System-level test (SLT)** runs the part in an application-like "
      "board, booting firmware or an operating system and running real "
      "workloads. It catches defects that structural tests miss - "
      "marginal timing on paths not covered by ATPG, power-delivery "
      "interactions, analog/digital integration issues. SLT is now common "
      "for high-end SoCs despite its long test time (minutes), because "
      "structural coverage alone cannot reach single-digit DPPM for "
      "billion-transistor designs.")

    h2("Yield: defect density and yield models")
    p("**Yield** at wafer sort is the fraction of dies that pass. It "
      "combines **systematic** losses (design-process interactions, "
      "lithography hotspots, parametric shifts - addressed by DFM and "
      "process tuning) and **random defect** losses (particles). Random "
      "defect yield is modelled from the die's **critical area** and the "
      "**defect density** D0 (defects per cm^2). If defects landed "
      "independently (a Poisson process) the probability of a die with "
      "zero defects would be exp(-A x D0). In reality defects cluster "
      "(some wafer regions are dirtier), which improves yield for large "
      "dies relative to Poisson. Several classic models capture this:")
    _eqa(["Poisson:            Y = exp(-A D0)",
        "Murphy:             Y = ((1 - exp(-A D0)) / (A D0))^2",
        "Seeds:              Y = 1 / (1 + A D0)",
        "Negative binomial:  Y = (1 + A D0 / alpha)^(-alpha)    alpha = clustering factor",
        "",
        "Y_total = Y_systematic x Y_random      (alpha -> infinity gives Poisson)"],
       caption="Random-defect yield models (A = die area, D0 = defect "
       "density).")
    p("The negative binomial model is the industry workhorse: alpha "
      "(typically quoted around 1-5) tunes how clustered defects are; "
      "alpha -> infinity gives Poisson and alpha = 1 gives Seeds. The "
      "following script compares them against die area for a mature "
      "process and an early-ramp process:")
    code(YIELD_SRC, caption="yield_models.py - four yield models versus die "
         "area.")
    out(YIELD_OUT, caption="Output of yield_models.py (python3).")
    code(YPLOT_SRC, caption="yield_plot.py - ASCII plot of the models for an "
         "early-ramp D0 of 0.3/cm^2.")
    out(YPLOT_OUT, caption="Output of yield_plot.py (python3). Where curves "
        "coincide only one letter is drawn.")
    p("Small dies yield well under every model. Beyond a few hundred mm^2 "
      "the models diverge: Poisson predicts ~9% yield at 800 mm^2 while "
      "Seeds predicts ~29% - a threefold difference in cost per die. This "
      "is why yield models must be calibrated with the foundry's data for "
      "the specific process and die size, and it is the quantitative "
      "reason behind chiplets (Chapter 20).")
    box("math", "Critical area",
        "Not every defect kills a die: a particle smaller than the space "
        "between two wires does not short them. The **critical area** "
        "A_c(r) is the area in which the centre of a defect of radius r "
        "causes a fault; integrating A_c(r) over the defect size "
        "distribution gives the effective area to use in the models. Dense "
        "layouts (minimum spacing everywhere) have larger critical area, "
        "which is what DFM wire spreading and via doubling (Chapter 17) "
        "attack.")
    h3("Parametric versus functional yield")
    p("**Functional (defect) yield** loss is caused by hard faults: the "
      "die simply does not work. **Parametric yield** loss comes from "
      "dies that work but miss a specification - too slow at Fmax, too "
      "leaky for the standby-power spec, an ADC with insufficient "
      "linearity - because of process variation. Parametric yield is "
      "controlled at design time by sign-off margins (Chapter 9 corners "
      "and OCV) and on silicon by AVS, trimming and binning. A design "
      "with no timing margin can have perfect defect yield and still lose "
      "30% of dies to speed.")
    h3("Redundancy and repair")
    p("Large SRAMs dominate critical area in many SoCs, so they are built "
      "with **redundant rows and columns**. MBIST finds failing cells, a "
      "built-in redundancy analysis (BIRA) engine computes a repair "
      "solution, and the repair is programmed into eFuses (built-in self "
      "repair, BISR). Without repair a chip with 100 Mbit of SRAM would "
      "lose a large fraction of dies to single-bit failures; with repair "
      "most of those dies are saved. Designs also harvest defective cores "
      "or channels (see binning above).")

    h2("Test quality: coverage and DPPM")
    p("Customers specify quality as **DPPM** (defective parts per "
      "million shipped). Consumer products may tolerate hundreds of DPPM; "
      "automotive customers demand single-digit DPPM or a zero-defect "
      "programme. The classic Williams-Brown relation links the defect "
      "level to yield Y and fault coverage T:")
    _eqa(["DL = 1 - Y^(1 - T)          (defect level: fraction of shipped parts that are bad)"],
       caption="Williams-Brown defect level model.")
    code(DPPM_SRC, caption="dppm.py - defect level versus yield and fault "
         "coverage.")
    out(DPPM_OUT, caption="Output of dppm.py (python3).")
    p("Even 99.9% stuck-at coverage leaves ~100 DPPM at 90% yield and "
      "~700 DPPM at 50% yield under this model. Real escapes are dominated "
      "by defects that stuck-at faults do not model (resistive opens, "
      "bridges, small delay defects), which is why production test adds "
      "transition, path-delay, cell-aware and small-delay-defect ATPG, "
      "IDDQ, outlier screening and SLT.")

    h2("Reliability physics")
    p("Reliability failures are wear-out or random failures that occur "
      "after the part has passed test. The main silicon mechanisms are:")
    tbl(["Mechanism", "Physics", "Accelerated by", "Design mitigation"], [
        ["Electromigration (EM)", "Momentum transfer from electrons "
         "moves metal atoms; voids (opens) and hillocks (shorts). Black's "
         "equation: MTTF ~ A J^-n exp(Ea/kT), n ~ 1-2",
         "Current density, temperature", "EM sign-off (Chapter 18): wider "
         "wires, more vias, current limits per layer"],
        ["Time-dependent dielectric breakdown (TDDB)", "Traps accumulate "
         "in gate oxide (or inter-metal low-k) until a conductive path "
         "forms", "Electric field (voltage), temperature",
         "Voltage limits per oxide; overdrive rules; spacing for BEOL TDDB"],
        ["Hot carrier injection (HCI)", "High-energy carriers near the "
         "drain damage the oxide interface; Vth shifts, drive falls",
         "High Vds, fast edges, switching activity", "Limit overdrive, "
         "slew constraints, ageing-aware timing"],
        ["Bias temperature instability (NBTI/PBTI)", "Interface traps "
         "under gate bias at temperature raise |Vth| (NBTI in PMOS, PBTI "
         "in NMOS with high-k gates); partially recovers", "Gate bias, "
         "temperature, duty cycle", "Ageing derates in STA (end-of-life "
         "libraries), guard-bands, AVS"],
        ["Soft errors (SER)", "Alpha particles (from package/solder "
         "impurities) and atmospheric neutrons deposit charge and flip "
         "stored bits; not permanent damage", "Altitude, sensitive node "
         "charge, low supply voltage", "ECC on memories, parity, hardened "
         "flip-flops, interleaving, low-alpha materials"],
    ], widths=[1.5, 2.6, 1.4, 2.0], caption="Table 21.1 - Silicon reliability "
       "mechanisms.", bold_first=True)
    p("Soft error rates are expressed in **FIT** (failures in time: one "
      "failure per 10^{9} device-hours). SRAM SER is often quoted per Mbit "
      "(typical orders of hundreds to a few thousand FIT/Mbit for "
      "unprotected SRAM at sea level, depending on node). A chip with "
      "100 Mbit of unprotected SRAM therefore has a raw SER of tens of "
      "thousands of FIT - one upset every few years per chip, but many "
      "per day across a data-centre fleet. SECDED ECC reduces the "
      "visible rate by orders of magnitude, leaving multi-bit upsets, "
      "which bit interleaving addresses.")

    h2("The bathtub curve, FIT and MTBF")
    diagram([
        " failure",
        "  rate",
        "   |\\                                                       /",
        "   | \\                                                     /",
        "   |  \\  infant mortality                     wear-out   /",
        "   |   \\ (latent defects,                    (EM, TDDB, /",
        "   |    \\  screened by burn-in)               NBTI, HCI) /",
        "   |     `-.___                                     _.-'",
        "   |           `-------------------------------------'",
        "   |               useful life: ~constant random failure rate (FIT)",
        "   +--------------------------------------------------------------------> time",
        "        weeks              years                            10-20 years",
    ], "Figure 21.3 - The bathtub curve.")
    p("During useful life the failure rate lambda is approximately constant "
      "and failures follow an exponential distribution, so rates add "
      "across components and MTBF = 1/lambda. Wear-out must be pushed "
      "beyond the product lifetime (e.g. 10 years for consumer at a "
      "defined mission profile, 15 years or more for automotive) by the "
      "reliability sign-off rules.")
    _eqa(["1 FIT = 1 failure / 10^9 device-hours",
        "lambda_system = sum of lambda_i          (series system, constant rates)",
        "MTBF = 10^9 / FIT_total  hours          R(t) = exp(-lambda t)"],
       caption="FIT and MTBF arithmetic.")
    code(FIT_SRC, caption="fit.py - system FIT, MTBF and fleet failures "
         "(FIT values are assumptions).")
    out(FIT_OUT, caption="Output of fit.py (python3).")
    box("warn", "Pitfall: MTBF is not lifetime",
        "An MTBF of 1464 years does not mean a unit lasts 1464 years. It "
        "means that during the useful-life region, a large population "
        "fails at a rate of one unit per 1464 unit-years - here about 683 "
        "failures a year in a fleet of a million. Wear-out (the right "
        "side of the bathtub) will still end every unit's life after its "
        "design lifetime. Quote FIT for components and state the mission "
        "profile (temperature, voltage, duty cycle) the number assumes.")

    h2("Accelerated testing and the Arrhenius model")
    p("Nobody can wait ten years to see if a product survives ten years. "
      "Reliability tests therefore **accelerate** failure mechanisms with "
      "temperature, voltage, humidity or temperature swing, and use "
      "physical models to translate stress time into use time. For "
      "thermally activated mechanisms the **Arrhenius** acceleration "
      "factor is:")
    _eqa(["AF = exp[ (Ea / k) x (1/T_use - 1/T_stress) ]      T in kelvin",
        "k = 8.617e-5 eV/K   Ea = activation energy (mechanism-specific, ~0.3-1.0+ eV)",
        "",
        "Voltage acceleration (e.g. TDDB):  AF_V = exp[ gamma x (V_stress - V_use) ]",
        "Temperature cycling (Coffin-Manson): AF = (dT_stress / dT_use)^m"],
       caption="Acceleration models.")
    p("JEDEC JESD47 uses a default Ea of 0.7 eV for HTOL when the actual "
      "mechanism is unknown. The script computes acceleration factors and "
      "sizes an HTOL test that demonstrates a FIT target with zero "
      "failures, using the chi-square bound for the failure rate:")
    code(ARR_SRC, caption="arrhenius.py - Arrhenius acceleration and HTOL "
         "sample-size arithmetic.")
    out(ARR_OUT, caption="Output of arrhenius.py (python3).")
    p("At 0.7 eV one hour at 125 deg C is worth about 78 hours at 55 deg "
      "C. Demonstrating 10 FIT at 60% confidence with zero failures needs "
      "about 1.2 million stress device-hours - e.g. 1180 parts for 1000 "
      "hours. Standard HTOL (three lots of 77 parts for 1000 hours) "
      "therefore proves a much looser bound on its own; low-FIT claims "
      "rely on larger samples, longer tests, cumulative data across "
      "products and physics-of-failure models of each mechanism.")
    box("warn", "Pitfall: over-accelerating",
        "Acceleration is valid only while the stress triggers the same "
        "failure mechanism as use. Too high a temperature or voltage can "
        "activate new mechanisms (package materials degrade above their "
        "glass transition temperature, oxides break down by a different "
        "process), producing failures that would never happen in the "
        "field - or masking ones that would. Also, a single Ea cannot "
        "describe a product whose failures come from several mechanisms.")

    h2("Qualification: JEDEC, ESD, latch-up and AEC-Q100")
    p("**Qualification** is the formal demonstration, on parts from "
      "multiple production-representative lots, that the product meets "
      "its reliability targets. For commercial and industrial ICs the "
      "reference is **JEDEC JESD47** (stress-test-driven qualification of "
      "integrated circuits), which calls out the individual test "
      "methods. **AEC-Q100** defines the stricter automotive "
      "qualification, with temperature grades from grade 0 (-40 to +150 "
      "deg C ambient) to grade 3 (-40 to +85 deg C), with grade 1 (-40 to "
      "+125 deg C) the most common.")
    tbl(["Test", "Standard (typical)", "Purpose / typical conditions"], [
        ["HTOL - high-temperature operating life", "JESD22-A108",
         "Biased, exercised parts at ~125 deg C (Tj higher) for ~1000 h; "
         "3 lots x 77 parts is the common sample plan"],
        ["ELFR - early life failure rate", "JESD74 / AEC-Q100",
         "Hundreds to thousands of parts for 48-168 h to measure infant "
         "mortality"],
        ["HTSL - high-temperature storage", "JESD22-A103",
         "Unbiased bake, e.g. 150 deg C for 1000 h"],
        ["Temperature cycling (TC)", "JESD22-A104", "e.g. -55/+125 deg C, "
         "hundreds to 1000+ cycles; package integrity"],
        ["THB / HAST / uHAST", "JESD22-A101 / A110 / A118", "Humidity "
         "(85 deg C / 85% RH, or pressurised HAST at 110-130 deg C) with "
         "or without bias; corrosion"],
        ["Preconditioning / MSL", "JESD22-A113, J-STD-020", "Moisture "
         "soak and reflow before the other stresses"],
        ["ESD - HBM", "ANSI/ESDA/JEDEC JS-001", "Human body model; "
         "commonly >= 1-2 kV target"],
        ["ESD - CDM", "ANSI/ESDA/JEDEC JS-002", "Charged device model; "
         "commonly 250-500 V target (AEC-Q100 asks 750 V on corner pins)"],
        ["Latch-up", "JESD78", "Current injection (e.g. +/-100 mA) and "
         "supply overvoltage at max temperature; no latch-up allowed"],
        ["EM, TDDB, HCI, NBTI", "JEP / foundry wafer-level reliability",
         "Process qualification by the foundry; the product inherits it "
         "if design rules are met"],
    ], widths=[1.9, 1.6, 3.2], caption="Table 21.2 - Common qualification "
       "stresses (check the current revision of each standard for exact "
       "conditions).", bold_first=True)
    box("expert", "Interview insight: yield versus reliability versus quality",
        "Interviewers like to probe whether you separate these. **Yield** is "
        "about the factory: the fraction of dies that pass test (drives "
        "cost). **Quality** is about the customer on day one: the fraction "
        "of shipped parts that are defective (DPPM, driven by test "
        "coverage). **Reliability** is about time: the failure rate in the "
        "field (FIT) and the lifetime before wear-out. A product can have "
        "poor yield but excellent quality (strict test throws many dies "
        "away) - and good quality but poor reliability (it passes test but "
        "its oxide wears out in two years).")

    h2("Summary")
    bul([
        "Production test runs at wafer sort (probe card) and final test "
        "(handler, socket); ATE provides pin electronics, power supplies "
        "and measurement units driven by a test program of binned test "
        "suites.",
        "Test cost ~ tester $/s x time / (sites x yield); multi-site test, "
        "scan compression and reduced pin-count test are the main levers.",
        "Speed binning, harvesting, AVS fuses and adaptive/outlier test "
        "turn test data into revenue and quality.",
        "Random-defect yield falls with area x D0; Poisson, Murphy, Seeds "
        "and negative-binomial models diverge for large dies. Parametric "
        "yield is set by margins and variation; memory repair recovers "
        "defect yield.",
        "DPPM depends on yield and coverage (DL = 1 - Y^(1-T)); low DPPM "
        "needs more than stuck-at coverage.",
        "EM, TDDB, HCI, BTI and soft errors are the main reliability "
        "mechanisms; FIT/MTBF describe the useful-life region of the "
        "bathtub curve; Arrhenius and related models convert stress time "
        "to use time.",
        "Qualification follows JESD47 (commercial/industrial) or AEC-Q100 "
        "(automotive): HTOL, ELFR, HTSL, TC, humidity, ESD (HBM/CDM) and "
        "latch-up (JESD78).",
    ])

    h2("Exercises")
    bul([
        "A test takes 3.5 s on a $0.04/s tester with 8 sites at 92% "
        "multi-site efficiency and 85% yield. Compute the test cost per "
        "good die. What test time would halve it?",
        "Using the negative binomial model with D0 = 0.2/cm^2 and alpha = "
        "2, compute yield for one 600 mm^2 die and for four 150 mm^2 "
        "chiplets (assume perfect KGD test and 99% assembly yield). Which "
        "costs less per good product if silicon cost is proportional to "
        "area?",
        "Using Williams-Brown, what fault coverage is needed for 10 DPPM "
        "at 80% yield? Why might real DPPM still be higher?",
        "Compute the Arrhenius acceleration factor from 150 deg C stress "
        "to 85 deg C use for Ea = 0.7 eV. How many hours of HTOL at "
        "150 deg C represent 10 years at 85 deg C?",
        "A server has 32 DIMMs at 15 FIT each, 2 CPUs at 40 FIT each and "
        "other parts totalling 200 FIT. Compute its MTBF and expected "
        "failures per year in a fleet of 50,000 servers.",
        "Explain why NBTI requires 'end-of-life' timing libraries, and "
        "which team owns the decision on the ageing guard-band.",
    ], ordered=True)


# =============================================================================
#  CHAPTER 22 - SILICON BRING-UP, VALIDATION, CHARACTERISATION, QUALIFICATION
# =============================================================================
def _ch22():
    chapter("Silicon Bring-up, Validation, Characterisation and "
            "Qualification")
    p("Eight to sixteen weeks after tapeout (longer for advanced nodes, "
      "shorter with hot-lot processing) the first wafers come out of the "
      "fab, a few are packaged on an expedited line, and the most intense "
      "phase of the project begins. **Bring-up** answers 'is it alive?', "
      "**post-silicon validation** answers 'does it do what the spec says, "
      "in every mode?', **characterisation** answers 'how much margin do "
      "we have across process, voltage and temperature?', and "
      "**qualification** answers 'will it keep working for its lifetime?'. "
      "Only when all four pass does the part move from engineering "
      "samples (ES) to production.")
    diagram([
        " tapeout   first     first      bring-up      validation +       qual        PRA /",
        "   |       wafers    packaged   ('alive')     characterisation   lots        ramp",
        "   |         |       parts          |               |              |           |",
        "   v         v         v            v               v              v           v",
        " --+---------+---------+------------+---------------+--------------+-----------+-->",
        "   | fab 8-16 wk | pkg |  1-4 wk    |   2-6 months   |  2-4 months |",
        "   |             | 1-3 |            |                |             |",
        "   |  prepare: boards, sockets, test program, validation content, lab    |",
        "",
        " ES (engineering samples) -> CS (customer/commercial samples) -> production",
    ], "Figure 22.1 - Post-silicon timeline (durations are typical and vary "
       "widely).")

    h2("Preparing for silicon: the bring-up plan")
    p("Bring-up is won or lost before tapeout. While the wafers are in "
      "the fab, the team prepares a written **bring-up plan** that lists, "
      "in order, every step from applying power to running the first "
      "application, the expected result of each step, who owns it, and "
      "what to do if it fails. The plan relies on design-for-debug "
      "features that had to be in the RTL months earlier.")
    checklist("Bring-up readiness checklist", [
        "Bring-up (validation) boards designed, fabricated and assembled; "
        "at least one spare; power rails individually controllable and "
        "measurable (sense resistors, test points).",
        "Sockets for packaged parts (so parts can be swapped without "
        "rework); probe-able test points for clocks and resets.",
        "Bench equipment: programmable supplies with current limits, "
        "oscilloscope, logic analyser, spectrum analyser / BERT for "
        "SerDes, thermal forcing unit (thermostream) or chamber.",
        "JTAG debugger and scripts that can read the IDCODE and access "
        "internal registers without software running.",
        "Pre-silicon collateral ported to silicon: boot ROM image, first "
        "firmware, register access scripts, the same tests run in "
        "emulation/FPGA prototyping so that failures can be compared.",
        "A test program on ATE able to run scan and MBIST on the first "
        "parts, in parallel with the lab effort.",
        "Defined owners and a daily triage meeting; a bug tracker for "
        "silicon issues separate from pre-silicon bugs.",
    ])
    box("tip", "Bring-up board design",
        "Design the first board for **observability and control**, not "
        "cost: separate regulators (or at least jumpers and sense "
        "resistors) on every supply rail so you can measure each "
        "current and power rails up in any order; an external clock "
        "input as an alternative to on-chip PLLs; switches for every boot "
        "strap; headers for JTAG, UART and trace; margining circuits that "
        "let software move each supply by +/-10%; and thermal sensors "
        "near the part. The cost-reduced customer reference board comes "
        "later.")

    h2("First power-on and smoke tests")
    p("The first power-on is deliberately slow and paranoid. A typical "
      "sequence:")
    bul([
        "**Visual and continuity.** Check the board, check the part is "
        "seated correctly and orientation is right, measure rail-to-ground "
        "resistances with power off to catch shorts.",
        "**Current-limited ramp.** Raise each supply in its specified order "
        "with a tight current limit, watching current. A short (hundreds "
        "of mA at a few hundred mV) means stop. Compare the static current "
        "with the predicted leakage for the corner and temperature.",
        "**Clocks and reset.** Check the reference clock arrives, release "
        "reset, confirm the PLL locks (lock bit via JTAG or a debug pin), "
        "measure clock outputs if a debug clock-out mux exists.",
        "**JTAG alive.** Read the IDCODE through the TAP (IEEE 1149.1). "
        "This is the first proof that digital logic works: the TAP "
        "controller, instruction register and IDCODE path are functioning.",
        "**Register access.** Through the debug port (e.g. an Arm "
        "CoreSight DAP or RISC-V debug module) read and write on-chip "
        "registers and SRAM. Run MBIST through JTAG.",
        "**Boot.** Release the CPU from reset, fetch from the boot ROM, "
        "load code from external flash or through JTAG into SRAM, print "
        "the first message on a UART. The 'hello world' on the console is "
        "the traditional bring-up milestone.",
        "**Interfaces and power-up of domains.** Bring up DDR (training "
        "results), SerDes links, peripherals, then the power management "
        "modes (Chapter 11) one by one.",
    ], ordered=True)
    box("warn", "Pitfall: no escape path when the boot fails",
        "If the boot ROM has a bug, or the external flash interface does "
        "not work, a chip with no alternative boot source is a brick. "
        "Always provide at least two independent paths to get code running: "
        "boot straps selecting UART/USB/JTAG download, JTAG access to SRAM "
        "and CPU halt/run, and ROM patch registers. The same applies to "
        "PLLs (an external clock bypass) and to any analog block the "
        "digital logic depends on (bypass modes, fuse overrides).")
    p("JTAG and debug architecture (IEEE 1149.1 boundary scan, IEEE 1500 "
      "core wrappers, IEEE 1687 IJTAG, CoreSight and RISC-V debug) is "
      "covered in Chapter 10 and in Chapter 23 of the companion "
      "Communication Protocols guide.")

    h2("Post-silicon validation")
    p("Pre-silicon verification (Chapter 7) runs at simulation speed and "
      "sees only the modelled world. Silicon runs a billion times faster, "
      "at real voltages and temperatures, connected to real devices. "
      "**Post-silicon validation** exercises the part to find the bugs "
      "and margins that pre-silicon missed. It is organised by domain:")
    tbl(["Domain", "What is checked", "Typical methods"], [
        ["Functional", "Every feature and mode against the spec; "
         "corner-case interactions; power-mode transitions",
         "Directed tests, random instruction generators and "
         "self-checking tests running at speed, OS boot, compliance "
         "suites"],
        ["Electrical", "I/O levels and timing, SerDes eye and jitter, "
         "DDR margins, PLL jitter, ADC/DAC performance, supply "
         "sensitivity", "Scope/BERT measurements, eye scans with on-die "
         "margining, supply and temperature sweeps"],
        ["Performance", "Throughput, latency, bandwidth versus the "
         "architecture model", "Benchmarks, performance counters, "
         "comparison with the pre-silicon performance model"],
        ["Power and thermal", "Dynamic and leakage power per mode, "
         "wake-up latency, thermal behaviour", "Per-rail current "
         "measurement, power virus tests, thermal camera/sensors"],
        ["Compliance", "Standard interfaces meet their specs (USB, PCIe, "
         "Ethernet)", "Compliance test equipment, plug-fests"],
        ["Software/system", "Drivers, firmware, OS and customer "
         "workloads", "Reference board with the software stack"],
    ], widths=[1.2, 2.6, 2.8], caption="Table 22.1 - Post-silicon validation "
       "domains.", bold_first=True)
    box("intuit", "Why bugs survive to silicon",
        "Silicon runs as many cycles in one second as a simulator runs in "
        "weeks. Rare coincidences - a cache eviction racing with a "
        "power-state change during a specific interrupt - become "
        "near-certainties. Analog/digital interfaces are often only "
        "modelled behaviourally. And real software does things no test "
        "writer imagined. A clean pre-silicon sign-off lowers the number "
        "of silicon bugs; it never makes it zero.")

    h2("Debug infrastructure: seeing inside the silicon")
    p("On silicon you cannot add a $display. Observability must be "
      "designed in. The main mechanisms, from cheapest to richest:")
    bul([
        "**Debug registers and status bits** readable over JTAG/APB: state "
        "machine states, error flags, sticky exception bits, performance "
        "counters.",
        "**Scan dump.** Stop the clocks at a trigger point, switch the "
        "flops into scan mode and shift out the entire state of the chip "
        "through the scan chains. With the scan chain map from DFT "
        "insertion, a script turns the bit stream back into register "
        "names. It is destructive (the run ends) but gives total "
        "visibility at one instant - often combined with clock-stop on "
        "a trigger condition.",
        "**Trace.** Processor trace (Arm ETM/PTM, RISC-V E-Trace/N-Trace) "
        "compresses the program flow into a trace stream stored in an "
        "on-chip buffer or exported through a trace port; bus trace "
        "records transactions on selected interconnect links.",
        "**On-chip logic analysers (embedded trace/signal-capture "
        "buffers).** A trigger unit and SRAM buffer capture selected "
        "internal signals around an event, like an FPGA logic analyser; "
        "muxes select which signal groups are observed. Area is spent on "
        "silicon only where the designers predicted bugs might be.",
        "**Debug muxes to pins.** A few spare GPIOs that can be switched "
        "to observe internal clocks or state bits on a scope.",
        "**Focused ion beam (FIB) edits and physical probing.** Failure "
        "analysis labs can cut and reconnect metal lines on a die to "
        "test a fix, or probe internal nodes (laser voltage probing, "
        "emission microscopy) to localise a fault.",
    ])
    box("expert", "Interview insight: debugging a silicon hang",
        "A classic question: 'the chip hangs after a few hours of a "
        "stress test - how do you debug it?' A strong answer: reproduce "
        "and reduce (find the minimal test, check sensitivity to voltage, "
        "frequency and temperature - a sensitivity to V/F suggests a "
        "timing path, insensitivity suggests a logic bug); read status "
        "registers via JTAG while hung; use trace to find the last "
        "instructions and bus transactions; set up a trigger and scan dump "
        "at the hang; map the state back to RTL; reproduce the scenario in "
        "simulation or emulation using the dumped state; then decide on "
        "a software workaround, a metal fix or both.")

    h2("Characterisation: shmoo plots, Vmin and Fmax")
    p("**Characterisation** measures how the silicon's behaviour varies "
      "with voltage, frequency, temperature and process, on enough parts "
      "to be statistically meaningful. The basic tool is the **shmoo "
      "plot**: a pass/fail grid obtained by running a test at every "
      "combination of two parameters, usually supply voltage (x) and "
      "clock frequency or period (y). The shape reveals the physics: a "
      "diagonal boundary is the normal speed-voltage relationship; a "
      "vertical wall at low voltage is a Vmin limit that does not depend "
      "on frequency (typically SRAM bit-cell stability or a retention "
      "problem); holes or 'floating' fails inside the passing region "
      "point to noise, resonances or a logic bug triggered at specific "
      "settings.")
    p("The script below builds a simple model of a chip: an alpha-power "
      "law path delay (Chapter 2) whose threshold voltage and mobility "
      "depend on the process corner and on temperature, plus an SRAM "
      "that fails below a fixed Vmin. It then prints an ASCII shmoo, "
      "exactly as a characterisation engineer would print one from ATE "
      "data.")
    code(SHMOO_SRC, caption="shmoo.py - a toy silicon model (constants are "
         "illustrative, not from any process).")
    code(RUNSHMOO_SRC, caption="run_shmoo.py")
    out(RUNSHMOO_OUT, caption="Output of run_shmoo.py (python3): shmoo of "
        "the toy model, typical corner at 25 deg C.")
    p("The diagonal boundary is the timing limit; the failing column at "
      "0.60 V is the SRAM Vmin wall (0.62 V in the model) - no frequency, "
      "however low, passes there. "
      "On real silicon the plot would come from the test program looping "
      "over DPS voltage and pattern timing, and each cell might show a "
      "count of passing parts instead of a single character.")
    h3("Vmin and Fmax across corners and temperature")
    p("Production parts come from anywhere in the process distribution "
      "and operate from cold to hot. Characterisation therefore measures "
      "**Vmin** (the lowest voltage that passes at a target frequency) "
      "and **Fmax** (the highest frequency that passes at a given "
      "voltage) on parts from each **corner lot** and across "
      "temperature:")
    code(VMIN_SRC, caption="run_vmin.py - Vmin and Fmax of the toy model "
         "across corners and temperature.")
    out(VMIN_OUT, caption="Output of run_vmin.py (python3).")
    p("Three effects are visible, all of which occur on real silicon. "
      "First, the SS corner at hot needs far more voltage for 1 GHz than "
      "FF - the reason for AVS and speed binning. Second, at 500 MHz most "
      "corners are pinned at the 0.62 V SRAM limit: memory, not logic, "
      "sets Vmin. Third, the model shows **temperature inversion**: at "
      "0.65 V parts are faster hot than cold (threshold voltage falls "
      "with temperature and dominates at low overdrive), while at 0.90 V "
      "they are faster cold (mobility loss dominates). In low-voltage "
      "designs the worst-case timing corner can therefore be cold, which "
      "is why sign-off includes both temperature extremes (Chapter 9).")
    h3("Process split lots and corner lots")
    p("To characterise across process without waiting for years of "
      "natural variation, the team orders **split lots** or **corner "
      "lots** from the foundry: wafers deliberately processed with key "
      "parameters (implant doses, gate length) shifted to the edges of "
      "the process window - e.g. SS, FF, SF, FS wafers alongside TT. "
      "Measuring Vmin/Fmax, leakage and analog performance on these "
      "wafers verifies that the design works across the whole window the "
      "foundry guarantees. Correlation between measured silicon and "
      "sign-off corners (silicon-to-model correlation) is checked with "
      "on-die **ring oscillators** and **process monitors**, which also "
      "provide per-die speed data for binning and AVS.")
    tbl(["Parameter", "Typical sweep", "Deliverable"], [
        ["Fmax vs VDD", "Voltage in 10-25 mV steps x frequency, at "
         "cold/room/hot", "Shmoo plots, guard-band for datasheet"],
        ["Vmin", "Per part, per corner, per temperature, per memory "
         "instance", "Vmin distribution; AVS table; retention voltage"],
        ["Leakage / IDDQ", "Temperature and voltage", "Standby power "
         "spec, leakage-based screens"],
        ["I/O timing and levels", "Setup/hold, VIH/VIL, VOH/VOL, drive "
         "strength", "Datasheet AC/DC tables"],
        ["Analog", "PLL jitter, ADC ENOB/INL/DNL, LDO regulation, "
         "SerDes eye", "Datasheet analog tables, trim targets"],
        ["ESD / latch-up", "Per qualification standard", "Qualification "
         "report (Chapter 21)"],
    ], widths=[1.4, 2.6, 2.4], caption="Table 22.2 - What is characterised.",
        bold_first=True)

    h3("From characterisation to speed bins and AVS tables")
    p("Characterisation data on a few hundred parts is used to predict "
      "what millions of production parts will do. The script below adds "
      "random per-part variation (threshold-voltage shift and mobility) "
      "to the same toy model, 'tests' 10,000 parts at 0.80 V and 85 deg C "
      "with a 3% tester guard-band, sorts them into speed bins, and then "
      "compares a single fixed supply voltage with **adaptive voltage "
      "scaling**, where each part is fused with the lowest voltage that "
      "meets 1 GHz:")
    code(BINS_SRC, caption="bins.py - Monte Carlo speed binning and AVS "
         "(toy model, seeded random variation).")
    out(BINS_OUT, caption="Output of bins.py (python3).")
    p("Two business decisions fall straight out of such data. The bin "
      "split decides which SKUs marketing can promise in which "
      "quantities (here only ~6% of parts reach the top bin, so a "
      "1.2 GHz premium SKU must be priced and forecast accordingly). And "
      "AVS lets the typical part run at ~0.74 V instead of the 0.90 V "
      "that the slowest 0.1% would need, cutting average dynamic power "
      "by about a third; the cost is per-part test time to find the "
      "voltage, fuses to store it, and a power-management interface "
      "(PMIC or on-die regulator) that honours it.")

    h2("Managing validation: bug tracking and exit criteria")
    p("Post-silicon work is run like a project within the project. Every "
      "anomaly is logged as a **sighting**, reproduced, root-caused "
      "(design bug, board issue, test issue, software bug or "
      "specification ambiguity) and only then promoted to a silicon bug "
      "with a severity:")
    tbl(["Severity", "Definition", "Typical action"], [
        ["Critical (showstopper)", "No workaround; blocks a key feature "
         "or causes data corruption", "Respin (metal or full); may delay "
         "customer sampling"],
        ["High", "Workaround exists but costs performance, power or "
         "significant software effort", "Workaround in firmware/SDK; fix "
         "in next stepping"],
        ["Medium", "Workaround is simple; limited impact", "Erratum; fix "
         "if a respin happens anyway"],
        ["Low / documentation", "Behaviour differs from the spec but is "
         "harmless, or the spec was wrong", "Update the datasheet or "
         "reference manual"],
    ], widths=[1.4, 2.8, 2.4], caption="Table 22.3 - Silicon bug severity "
       "classes (names vary by company).", bold_first=True)
    p("Validation exit criteria mirror pre-silicon sign-off: the planned "
      "test content has run on the target number of parts across "
      "corners and temperatures; the rate of new sightings has flattened "
      "over several weeks; no critical bugs are open; every high bug has "
      "a documented workaround; compliance tests have passed; and power "
      "and performance meet the datasheet targets. Each silicon bug also "
      "feeds back to the pre-silicon team as an **escape analysis**: why "
      "did verification miss it, and what test, assertion or coverage "
      "point would have caught it? That analysis is what improves the "
      "next project's methodology (Chapter 23).")

    h2("Errata, workarounds and respins")
    p("Every complex chip has bugs in silicon. Each confirmed bug is "
      "root-caused and then classified: can it be worked around in "
      "software, firmware, board design or by avoiding a mode? Workable "
      "bugs are documented as **errata** (published to customers with "
      "workarounds) and fixed in the next revision if cheap. Bugs with no "
      "acceptable workaround force a **respin**.")
    tbl(["Respin type", "What changes", "Cost and time (typical order)",
         "When possible"], [
        ["Metal-only (ECO) respin", "Only some metal and via masks; "
         "fixes use spare cells or gate-array ECO cells placed at tapeout "
         "(Chapter 19)", "A fraction of a full mask set; weeks saved "
         "because base-layer wafers held at the fab ('wafer bank') can be "
         "finished with new metal masks", "Logic fixes that fit in spare "
         "resources; small analog tweaks"],
        ["Full (all-layer) respin", "All masks", "Full mask cost and full "
         "fab cycle time (months)", "Transistor-level changes, large logic "
         "changes, new IP"],
        ["Software / fuse workaround", "Nothing on silicon", "Engineering "
         "time only; possible performance cost", "Bug has a trigger that "
         "firmware can avoid, or a chicken bit disables the feature"],
    ], widths=[1.5, 2.2, 2.2, 1.8], caption="Table 22.4 - Ways to fix a "
       "silicon bug.", bold_first=True)
    box("tip", "Design for fixability",
        "Experienced teams tape out with **spare cells** sprinkled "
        "throughout the logic, **chicken bits** (register bits that disable "
        "new or risky features or select conservative behaviour), ROM "
        "**patch** mechanisms, programmable delay taps on critical "
        "interfaces, and a policy of **holding wafers** before metal "
        "layers so that a metal fix can be finished quickly. Revision "
        "naming conventions track this: A0 is first silicon; A1 a metal "
        "respin; B0 a full respin.")

    h2("From samples to production: ramp, qualification and datasheets")
    p("When validation and characterisation are complete and the silicon "
      "revision is frozen, the part goes through **product qualification** "
      "(the JEDEC or AEC-Q100 stresses of Chapter 21 on three lots of "
      "the final revision), and the organisation holds a **production "
      "release** (PRA) review. The **ramp to production** then scales "
      "volume: the test program is optimised for test time, yield "
      "learning continues with the foundry, test limits are tightened "
      "from characterisation data, and statistical process control "
      "monitors every lot.")
    p("The **datasheet** is generated from characterisation: each "
      "guaranteed specification is set from the measured distribution "
      "with a guard-band (for example, the measured mean minus several "
      "sigma across corners and temperature, further tightened for "
      "tester accuracy), and each value is marked as either tested in "
      "production or guaranteed by design/characterisation. Preliminary "
      "datasheets with target values are issued earlier and must be "
      "updated once silicon data exist.")
    h3("Lifecycle and product change notification")
    p("After release, a product is managed through its **lifecycle**: "
      "active, not recommended for new designs (NRND), last-time buy and "
      "end of life (EOL). Any change that could affect form, fit, function "
      "or reliability - a new fab or assembly site, a mask change, a new "
      "mould compound, a test flow change - requires a **product change "
      "notification (PCN)** to customers, often with requalification data "
      "(JEDEC J-STD-046 describes the process; automotive customers "
      "require it per AEC-Q100 change guidelines). Automotive and "
      "industrial customers often require 10-15 years of supply, which "
      "shapes the choice of process node and IP from the start.")
    box("warn", "Pitfall: characterising too few parts",
        "Datasheet limits derived from ten engineering samples from one "
        "lot will not hold across millions of production parts. "
        "Characterise hundreds of parts from multiple lots including "
        "corner lots, check distributions (not just pass/fail), and keep "
        "monitoring after release - the first production months often "
        "reveal a tail that samples missed.")

    h2("Summary")
    bul([
        "Bring-up is planned before tapeout: boards built for "
        "observability, debug access, bench equipment, ported pre-silicon "
        "tests and an ordered, owned plan.",
        "First power-on proceeds from current-limited rail ramps through "
        "clocks, JTAG IDCODE and register access to boot and interfaces; "
        "always design alternative boot and clock paths.",
        "Post-silicon validation covers functional, electrical, "
        "performance, power, compliance and software domains; debug "
        "infrastructure (scan dump, trace, on-chip logic analysers) must "
        "be designed in.",
        "Characterisation uses shmoo plots, Vmin/Fmax distributions, "
        "corner lots and temperature sweeps; watch for Vmin walls set by "
        "memory and for temperature inversion.",
        "Bugs are handled as errata with workarounds, metal-only respins "
        "(spare cells, held wafers) or full respins.",
        "Production release requires qualification, a datasheet derived "
        "from characterisation data with guard-bands, and lifecycle "
        "management with PCNs.",
    ])

    h2("Exercises")
    bul([
        "Write a 12-step bring-up plan for a small microcontroller with "
        "one PLL, a boot ROM, SPI flash and a UART. For each step state "
        "the pass criterion and the fallback if it fails.",
        "Modify shmoo.py so that a resonance causes failures only between "
        "900 and 1000 MHz at voltages below 0.75 V. Print the shmoo and "
        "describe how a validation engineer would recognise this pattern.",
        "Using run_vmin.py, determine the Vmin at 800 MHz for all nine "
        "corner/temperature combinations. Which combination should AVS "
        "fuse tables be built around, and why?",
        "A silicon bug corrupts data when two masters write the same "
        "cache line within 3 cycles. List three possible workarounds and "
        "discuss whether a metal-only fix is plausible.",
        "Explain the difference between a value 'tested in production' "
        "and 'guaranteed by characterisation' in a datasheet. Which "
        "would you choose for leakage current, and why?",
    ], ordered=True)


# =============================================================================
#  CHAPTER 23 - METHODOLOGY, PROJECT MANAGEMENT AND THE ECONOMICS OF AN ASIC
# =============================================================================
def _ch23():
    chapter("Methodology, Project Management and the Economics of an ASIC")
    p("The previous 22 chapters described what must be done to turn a "
      "specification into a shipping chip. This chapter is about how an "
      "organisation does it on time and on budget: the phases and "
      "milestones that structure a project, the reviews that gate each "
      "transition, the people and tools involved, the methodology that "
      "keeps hundreds of runs reproducible, and the cost model that "
      "decides whether the ASIC should be built at all. Technical leads "
      "who understand these topics make better engineering decisions, "
      "because almost every technical trade-off is ultimately a schedule, "
      "cost or risk trade-off.")

    h2("Project phases and milestones")
    p("Company vocabularies differ, but every ASIC project passes through "
      "the same sequence of **freezes** - points after which a class of "
      "change becomes expensive and requires formal approval.")
    diagram([
        " concept   spec      arch/uarch   RTL        RTL       netlist     tapeout   silicon",
        "  |       freeze      freeze     0.5/0.8    freeze     freeze        |       back",
        "  v         v           v          v          v          v           v         v",
        " -+---------+-----------+----------+----------+----------+-----------+---------+-->",
        "  |<-- architecture -->|<----- RTL design + verification ----->|",
        "  |                    |      |<-------- synthesis / timing closure -->|",
        "  |                    |           |<----------- physical design ---->|",
        "  |   floorplan/package/IP selection early ...      sign-off -->|",
        "  |                                                             |<-- bring-up,",
        "  |                                                                  validation",
        "",
        "  typical overall: 12-24 months from spec freeze to tapeout for a large SoC",
    ], "Figure 23.1 - Phases overlap; freezes mark where change control "
       "tightens.")
    tbl(["Milestone", "Meaning", "Exit criteria (examples)"], [
        ["Spec freeze", "Features, interfaces, PPA targets and "
         "package agreed with customer/marketing", "Signed product "
         "requirements; architecture spec reviewed; IP list chosen"],
        ["Architecture / micro-architecture freeze", "Block partitioning, "
         "clocks, power domains, memory map fixed", "Block specs, "
         "performance model results, area/power estimates, floorplan "
         "sketch, package concept"],
        ["RTL 0.5 / 0.8 (feature complete)", "All blocks coded; "
         "integration running", "Lint/CDC clean trend; basic tests pass; "
         "first synthesis and trial floorplan"],
        ["RTL freeze (1.0)", "No functional changes without an ECO "
         "process", "Coverage targets met; bug rate down; no open "
         "critical bugs; DFT inserted; UPF final"],
        ["Netlist freeze", "Synthesised, DFT-inserted netlist handed to "
         "physical design (or final)", "Equivalence checks pass; "
         "timing met at block level; ATPG coverage met"],
        ["Tapeout", "GDSII (OASIS) delivered to the foundry",
         "All sign-off checklists (Chapter 18-19) closed; waivers "
         "approved; tapeout review signed"],
        ["Silicon back / production release", "First parts in the lab; "
         "later, release to volume", "Bring-up plan executed; "
         "qualification and characterisation complete (Chapters 21-22)"],
    ], widths=[1.6, 2.2, 2.8], caption="Table 23.1 - Standard milestones.",
        bold_first=True)

    h2("Gating reviews")
    p("Each milestone is gated by a **review** with a checklist and named "
      "sign-off owners. Good reviews are data-driven: they look at "
      "coverage reports, lint and CDC waiver lists, timing summaries, "
      "power estimates, DRC/LVS results and the open-bug list, not at "
      "slide decks full of green traffic lights. Typical reviews are the "
      "architecture review, RTL freeze review, DFT review, floorplan and "
      "package review, pre-tapeout (sign-off) review and production "
      "release review. The output is a go/no-go decision plus an action "
      "list, and any **waiver** (a known violation accepted with "
      "justification) is recorded with an owner.")
    box("warn", "Pitfall: moving a freeze without moving the plan",
        "The most common schedule failure is not a slow team but a late "
        "change that is accepted without replanning: 'just one more "
        "feature' after RTL freeze reopens verification, synthesis, "
        "timing closure and DFT, and the tapeout date silently slips by "
        "months. Every post-freeze change needs an impact assessment from "
        "verification, implementation and DFT before it is approved.")

    h2("Team structure and headcount")
    p("A large SoC project involves dozens to hundreds of engineers across "
      "many disciplines, and the mix changes over time: architecture "
      "peaks early, verification in the middle, physical design towards "
      "tapeout, and validation after silicon returns.")
    tbl(["Role", "Main responsibility", "Peak phase"], [
        ["Architects", "Spec, performance/power models, trade-offs",
         "Concept to arch freeze"],
        ["RTL designers", "Micro-architecture and RTL for blocks; "
         "integration", "Arch freeze to RTL freeze"],
        ["Verification engineers", "Testbenches, coverage, formal, "
         "emulation; usually 1.5-3x the number of designers",
         "RTL 0.5 to RTL freeze"],
        ["DFT engineers", "Scan, compression, MBIST, JTAG, ATPG",
         "RTL freeze to tapeout"],
        ["Physical design (PD)", "Synthesis, floorplan, P&R, timing "
         "closure", "Netlist to tapeout"],
        ["Sign-off / STA / PI", "Timing, IR/EM, physical verification",
         "Last months before tapeout"],
        ["Analog / mixed-signal", "PLLs, ADCs, I/O, custom blocks",
         "Throughout; tapes out early test chips"],
        ["CAD / methodology", "Flows, scripts, licences, compute",
         "Throughout"],
        ["Package, SI/PI, test, product engineering", "Package design, "
         "test program, bring-up, characterisation", "Tapeout to "
         "production"],
        ["Software / firmware", "Boot, drivers, SDK; pre-silicon on "
         "emulation/FPGA", "Grows through the project; peaks after "
         "silicon"],
        ["Programme/project management", "Schedule, dependencies, risk, "
         "reporting", "Throughout"],
    ], widths=[1.6, 3.0, 1.8], caption="Table 23.2 - ASIC team roles.",
        bold_first=True)
    diagram([
        "                      Q1  Q2  Q3  Q4  Q5  Q6  Q7  Q8  Q9  Q10 Q11 Q12",
        "  Architecture        ### ### === ::: ... ... ... ... ... ...",
        "  RTL design          ... === ### ### ### === ::: ... ... ... ...",
        "  Verification            ... === ### ### ### ### === ::: ... ...",
        "  DFT                         ... ... ::: === === === ... ... ...",
        "  Physical design             ... ... ::: === ### ### ::: ...",
        "  Sign-off/STA/PI                     ... ::: === ### ...",
        "  Software/firmware           ... ... ::: ::: === === ### ### === ===",
        "  Test/product eng.                   ... ... ::: === ### ### ### ===",
        "  Validation/bring-up                     ... ... ::: ### ### === :::",
        "",
        "  staffing:  ... light   ::: moderate   === heavy   ### peak",
        "  milestones: spec freeze Q1, arch freeze Q2, RTL freeze Q6, tapeout end of Q8,",
        "              first silicon Q9, production release Q12 (a 3-year programme)",
    ], "Figure 23.2 - Qualitative staffing by discipline over a "
       "three-year programme (illustrative).")

    h2("Schedule risks")
    tbl(["Risk", "Symptom", "Mitigation"], [
        ["Late or unstable spec", "Features added after RTL freeze",
         "Spec freeze discipline, change control board, contract terms"],
        ["Third-party IP", "IP late, buggy or missing views (LEF, Liberty, "
         "models); hardened IP not qualified on your metal stack",
         "Qualify IP early; demand full deliverable lists; test chips; "
         "back-up vendors"],
        ["Verification closure", "Bug rate not converging; coverage "
         "stuck", "Track bug curves; emulation; formal on control logic; "
         "early integration"],
        ["Timing closure", "Many iterations between synthesis and P&R",
         "Early trial floorplans, physically aware synthesis, "
         "architecture changes rather than heroic PD"],
        ["Congestion / area", "Die size grows after floorplan",
         "Early placement trials; utilisation targets; memory "
         "floorplanning"],
        ["Power / IR", "Late IR-drop violations, thermal limits",
         "Early power estimation, power grid sign-off per iteration"],
        ["Foundry / PDK changes", "New PDK versions late in the project",
         "Lock PDK version; assess each update"],
        ["Tools and compute", "Licence shortages near tapeout, long "
         "runtimes", "Licence planning; cloud burst; hierarchical flows"],
        ["People", "Key-person dependencies, attrition",
         "Documentation, pairing, reviews"],
    ], widths=[1.5, 2.4, 2.8], caption="Table 23.3 - Common schedule risks.",
        bold_first=True)

    h2("The EDA tool landscape and licensing")
    p("Three large vendors supply most commercial EDA, each with a "
      "complete digital flow, plus specialists. Product names and "
      "ownership change frequently through acquisitions, so treat the "
      "table as orientation and check current offerings.")
    tbl(["Flow step", "Synopsys", "Cadence", "Siemens EDA", "Open source"], [
        ["Simulation", "VCS", "Xcelium", "Questa", "Verilator, Icarus"],
        ["Formal / equivalence", "VC Formal, Formality", "Jasper, "
         "Conformal", "Questa Formal", "SymbiYosys, Yosys eqy"],
        ["Emulation / prototyping", "ZeBu, HAPS", "Palladium, Protium",
         "Veloce", "FPGA boards"],
        ["Synthesis", "Design Compiler, Fusion Compiler", "Genus",
         "(Oasys; HLS: Catapult)", "Yosys + ABC"],
        ["Place & route", "IC Compiler II, Fusion Compiler", "Innovus",
         "Aprisa", "OpenROAD"],
        ["STA", "PrimeTime", "Tempus", "-", "OpenSTA"],
        ["DFT / ATPG", "TestMAX", "Modus", "Tessent", "(Fault, limited)"],
        ["Physical verification", "IC Validator", "Pegasus", "Calibre",
         "Magic, KLayout, Netgen"],
        ["Power integrity", "PrimePower, RedHawk-SC (from Ansys)",
         "Voltus", "mPower", "OpenROAD PDNSim"],
        ["Custom / analog", "Custom Compiler, PrimeSim", "Virtuoso, "
         "Spectre", "Solido, AFS", "Xschem, ngspice, Magic"],
    ], widths=[1.4, 1.6, 1.3, 1.2, 1.4], caption="Table 23.4 - Representative "
       "tools by flow step (not exhaustive).", bold_first=True)
    box("note", "Ownership changes: the Ansys caution",
        "Synopsys completed its acquisition of Ansys in 2025, so tools such "
        "as RedHawk-SC and Totem (power integrity) and the Ansys thermal "
        "and electromagnetic solvers now sit in the Synopsys portfolio; as "
        "a condition of approval some products were divested (for example "
        "Ansys PowerArtist went to Keysight). Many foundry sign-off "
        "certifications, older documents and job adverts still use the "
        "Ansys names. Always check current product names, ownership and "
        "foundry certification status rather than relying on this or any "
        "book.")
    p("**Licensing** is a major cost and a scheduling constraint. "
      "Licences are typically **time-based** (term licences of 1-3 years) "
      "and counted as simultaneous users per feature, managed by a licence "
      "server (FlexNet/FlexLM). Large companies negotiate **token** or "
      "'all-you-can-eat' pools; start-ups buy bundles at a discount for "
      "their first tapeout. Place-and-route and sign-off licences are the "
      "most expensive, and demand peaks in the months before tapeout, when "
      "many parallel runs compete. Foundry **sign-off certification** "
      "matters: DRC/LVS decks, extraction rule files and EM rules are "
      "released for specific tools, which can lock the flow.")
    p("**Open-source tools** (Chapter 24) - Yosys, OpenROAD/OpenLane, "
      "Magic, KLayout, Netgen, Verilator - are production-capable for "
      "open PDKs (SkyWater 130, GF180, IHP SG13G2) and are widely used for "
      "education, research and small commercial designs. They are not "
      "sign-off certified for leading-edge commercial nodes, whose PDKs "
      "are under NDA.")

    h2("Compute and infrastructure")
    p("An ASIC project is also a data-centre project. Full-chip P&R and "
      "sign-off jobs need hundreds of GB to multiple TB of RAM and run "
      "for hours to days; regressions run tens of thousands of "
      "simulations per night; a tapeout database with all its derived "
      "data runs to many terabytes. Typical infrastructure includes a "
      "compute farm with a job scheduler (LSF, Slurm, Grid Engine), "
      "high-performance NFS storage with snapshots, licence servers, "
      "emulators, and increasingly **cloud** capacity for peaks, which "
      "requires foundry approval for PDK data to leave the premises "
      "(most major foundries now have cloud-ready programmes).")

    h2("Methodology: flows, scripts, CI and version control")
    p("**Methodology** is the set of flows, scripts, conventions and "
      "checks that make results reproducible. A mature team can re-run "
      "any block from RTL to GDSII with one command and get the same "
      "result; an immature one relies on a single engineer's shell "
      "history. Key elements:")
    bul([
        "**Reference flows.** Scripted, parameterised Tcl/Python flows for "
        "each step (lint, CDC, synthesis, DFT, P&R, STA, PV), usually "
        "starting from vendor reference flows and adapted by the CAD team. "
        "Block owners change configuration, not the flow code.",
        "**Version control.** RTL, testbenches, constraints (SDC, UPF), "
        "scripts and flow configuration live in git (or Perforce). Large "
        "binary design data (libraries, layouts, databases) use design "
        "data management systems (e.g. Cliosoft SOS, IC Manage, "
        "Perforce/Helix, git-LFS) with check-in/check-out and tagging; "
        "every milestone and tapeout is a **tagged, reproducible "
        "release** including tool versions and PDK version.",
        "**Continuous integration.** Every commit triggers lint, a smoke "
        "simulation and possibly a quick synthesis; nightly regressions "
        "run full test suites, formal proofs, synthesis and trial P&R, "
        "tracking coverage, QoR (area, timing, power) and runtimes over "
        "time. Dashboards expose trends so that a timing or area "
        "regression is caught the day it is introduced.",
        "**Checklists and sign-off databases.** Each gating review pulls "
        "results from the regression database rather than hand-edited "
        "slides.",
        "**Consistency checks.** The same SDC and UPF used in synthesis, "
        "P&R and sign-off; automated checks that every block uses the "
        "approved library and PDK versions.",
    ])
    code([
        "# nightly.yml - sketch of a nightly design regression (CI job definitions)",
        "stages: [lint, sim, formal, synth, pnr_trial, report]",
        "lint:      run: make lint        # Verilator --lint-only / commercial lint",
        "sim:       run: make regress SEEDS=500 COV=1",
        "formal:    run: make formal      # property proofs, CDC, connectivity",
        "synth:     run: make synth CORNER=ss_0p72v_125c",
        "pnr_trial: run: make pnr STAGE=place_opt   # congestion and timing trend",
        "report:    run: python qor_dashboard.py --compare last_good",
    ], caption="An illustrative CI pipeline for a design repository (tool "
       "invocations abstracted behind make targets).")

    h2("The cost model: NRE")
    p("ASIC economics has two parts: **non-recurring engineering (NRE)** "
      "- the one-time cost to design and bring the chip to production - "
      "and **unit cost** - the cost of each part shipped. NRE is spread "
      "over the lifetime volume, which is why volume decides whether an "
      "ASIC beats an FPGA or an off-the-shelf part. The script below "
      "builds up an NRE estimate for a mid-size 16 nm-class SoC. Every "
      "number is an assumption chosen to be plausible, not data from a "
      "real project or foundry.")
    code(NRE_SRC, caption="nre.py - an illustrative NRE build-up "
         "(assumptions only).")
    out(NRE_OUT, caption="Output of nre.py (python3).")
    p("Even in this modest example people are only about a third of the "
      "cost; licences and IP together exceed them. At leading-edge nodes "
      "public industry estimates for a complex SoC run into hundreds of "
      "millions of dollars once software, validation and IP are included, "
      "and a full mask set alone is in the multi-million-dollar range, "
      "rising steeply with node because of EUV and multi-patterning "
      "layers. **Multi-project wafers (MPW)** or shuttles share one mask "
      "set among many designs and cut prototype costs to tens of "
      "thousands of dollars at mature nodes - the route most start-ups and "
      "universities use for test chips.")

    h2("The cost model: unit cost and cost per good die")
    p("Unit cost is built from the wafer cost, how many dies fit on a "
      "wafer, how many of those work, and the package, test and "
      "assembly-yield costs:")
    _eqa(["DPW ~ pi (d/2)^2 / A  -  pi d / sqrt(2 A)       d = usable wafer diameter",
        "",
        "Cost_die = C_wafer / (DPW x Y_die)",
        "",
        "Cost_unit = (Cost_die + C_package + C_test) / Y_final",
        "",
        "Cost_total(V) = NRE / V + Cost_unit              V = lifetime volume"],
       caption="Unit cost model.")
    p("The first term of DPW is the wafer area divided by the die area; "
      "the second subtracts partial dies around the edge. The following "
      "calculator applies the model to the same product implemented in "
      "five nodes. The design is assumed to shrink with each node (less "
      "than ideally, because SRAM, analog and I/O scale poorly), while "
      "wafer price and NRE rise. **All inputs are illustrative "
      "assumptions** in the rough range of public estimates; real wafer "
      "prices depend on volume, customer and negotiation and are "
      "confidential.")
    code(COST_SRC, caption="cost.py - cost per good die and per unit across "
         "nodes (illustrative assumptions).")
    out(COST_OUT, caption="Output of cost.py (python3).")
    code(BE_SRC, caption="breakeven.py - volume at which a more advanced "
         "node becomes cheaper overall.")
    out(BE_OUT, caption="Output of breakeven.py (python3).")
    p("Under these assumptions the silicon cost per good die is lowest at "
      "7 nm, but only slightly below 28 nm (16 nm is dearer than 28 nm "
      "because its wafer price rises faster than the die shrinks), and "
      "once NRE is included the advanced nodes are more expensive at every "
      "volume in the table. For a small die the "
      "package and test costs are comparable to the die cost, so shrinking "
      "the die buys little. The economic case for an advanced node is "
      "therefore **performance and energy efficiency** (and, for large "
      "dies, fitting the design at all), not cost - unless volumes reach "
      "the hundreds of millions. This is the quantitative core of many "
      "real node-selection decisions.")
    box("math", "Sensitivity analysis",
        "Cost models are only as good as their inputs. Always run "
        "sensitivities: +/-20% on wafer price, D0 doubled (early ramp), "
        "die area +15% (typical growth from the first estimate to "
        "tapeout), package cost for a larger body, and a lower volume "
        "forecast. If the decision flips under plausible changes, it was "
        "not a robust decision.")

    h2("Make versus buy")
    p("Before committing to an ASIC, compare the alternatives over the "
      "product lifetime:")
    tbl(["Option", "NRE", "Unit cost", "Time to market", "Best when"], [
        ["Off-the-shelf chip (ASSP/MCU)", "Lowest (board and software)",
         "Vendor's price", "Fastest", "A standard part meets the needs"],
        ["FPGA", "Low", "High (often tens to thousands of $)", "Fast; "
         "reprogrammable", "Low volume, changing requirements, "
         "prototyping"],
        ["Structured ASIC / FPGA conversion", "Medium", "Medium", "Medium",
         "Moderate volume, design proven in an FPGA"],
        ["Full-custom ASIC (in-house)", "Highest", "Lowest", "Slowest "
         "(18-36 months)", "High volume or a PPA/IP differentiation that "
         "nothing else provides"],
        ["ASIC via design-services partner", "High (partner margin)",
         "Low", "Medium-slow", "Team lacks back-end, packaging or "
         "foundry access"],
    ], widths=[1.6, 1.2, 1.3, 1.2, 2.0], caption="Table 23.5 - Make-versus-buy "
       "options.", bold_first=True)
    p("Within an ASIC project the same question repeats for each block: "
      "license a CPU, SerDes, DDR PHY or PLL, or design it in-house? "
      "Licensed hard IP costs licence fees and royalties but carries "
      "silicon proof; in-house design costs engineers and schedule risk "
      "but may differentiate the product. The usual rule is to buy "
      "anything that is a standard interface or not differentiating, and "
      "to invest in-house effort where the product competes.")

    h2("Risk management")
    p("Risk management runs throughout the project. The team keeps a "
      "**risk register** of identified risks, each with a likelihood, "
      "impact, owner, mitigation and trigger. Typical technical "
      "mitigations are **test chips** for new analog IP or new process "
      "nodes, early package and thermal studies, emulation and FPGA "
      "prototyping to start software early, conservative timing margins "
      "on first silicon, and design-for-fixability features (Chapter 22). "
      "Commercial mitigations include second-source IP, MPW slots booked "
      "in advance and foundry capacity reservations.")
    box("expert", "Interview insight: 'Should we build this ASIC?'",
        "A senior candidate answers with a model, not an opinion: estimate "
        "NRE (people x time, IP, masks, EDA), unit cost at the realistic "
        "volume (die size -> DPW -> yield -> package/test), compare the "
        "total cost of ownership with the FPGA/ASSP alternative over the "
        "product lifetime, then weigh non-cost factors - power, form "
        "factor, IP protection, supply security, time to market - and "
        "name the top three risks with mitigations. Mentioning the "
        "break-even volume and its sensitivity to schedule slip is a "
        "strong signal.")

    h2("Functional safety and security certification")
    p("Chips for cars, factories, medical devices and payment systems "
      "must be developed under certified processes. Certification is "
      "largely about **process and evidence**: documented requirements "
      "traced to design and verification, analyses of how faults are "
      "detected, and independent assessment. Retro-fitting it to a "
      "finished design is extremely expensive.")
    h3("ISO 26262 (road vehicles)")
    p("ISO 26262 defines **Automotive Safety Integrity Levels** ASIL A "
      "(lowest) to D (highest), derived from hazard analysis of the "
      "vehicle function. Part 5 covers hardware development and Part 11 "
      "gives guidance specific to semiconductors. A chip developed out of "
      "context of a specific car is a **Safety Element out of Context "
      "(SEooC)** with assumed safety requirements. Hardware must meet "
      "quantitative metrics:")
    tbl(["Metric", "ASIL B", "ASIL C", "ASIL D"], [
        ["Single-point fault metric (SPFM)", ">= 90%", ">= 97%", ">= 99%"],
        ["Latent fault metric (LFM)", ">= 60%", ">= 80%", ">= 90%"],
        ["Probabilistic metric for random hardware failures (PMHF)",
         "< 100 FIT", "< 100 FIT", "< 10 FIT"],
    ], widths=[3.0, 1.0, 1.0, 1.0], caption="Table 23.6 - ISO 26262 hardware "
       "architectural metric targets (item level).", bold_first=True)
    p("The chip team performs an **FMEDA** (failure modes, effects and "
      "diagnostic analysis), estimating base failure rates (e.g. from IEC "
      "TR 62380 / SN 29500 / IEC 61709 models, or measured SER and FIT) "
      "and the diagnostic coverage of each safety mechanism: lockstep "
      "CPUs, ECC on memories and buses, parity, watchdogs, clock and "
      "voltage monitors, logic BIST and memory BIST at key-on. **Fault "
      "injection** campaigns in simulation verify the claimed coverage. "
      "Development follows a safety plan with a safety manager, tool "
      "confidence levels for EDA tools, confirmation reviews and a "
      "**safety case**. Production quality requirements (AEC-Q100, "
      "near-zero DPPM, PAT) come on top.")
    h3("IEC 61508 and derivatives")
    p("IEC 61508 is the generic functional safety standard for "
      "electrical/electronic/programmable systems, with **Safety "
      "Integrity Levels** SIL 1 to SIL 4. It is the parent of sector "
      "standards (ISO 26262 for automotive, IEC 62304 for medical "
      "software, EN 50128/50129 for railway, IEC 61511 for process "
      "industries). Its hardware metrics use the **safe failure "
      "fraction (SFF)** and hardware fault tolerance to set allowable "
      "SILs, and IEC 61508-2 Annex E gives specific requirements for "
      "on-chip redundancy.")
    h3("Security: Common Criteria and related schemes")
    p("**Common Criteria** (ISO/IEC 15408) evaluates security products "
      "against a **Protection Profile** or Security Target, at "
      "**Evaluation Assurance Levels** EAL1-EAL7; smart-card and secure "
      "element chips are typically evaluated at EAL4+ to EAL6+ with "
      "'AVA_VAN.5' vulnerability analysis (resistance to high-attack-"
      "potential attackers, including side-channel and fault-injection "
      "attacks) in an accredited laboratory. Other schemes include FIPS "
      "140-3 for cryptographic modules, EMVCo for payment chips, SESIP "
      "and PSA Certified for IoT, and ISO/SAE 21434 for automotive "
      "cybersecurity engineering. For the chip team this means secure "
      "development lifecycle processes, secure site certification for "
      "design and manufacturing locations, countermeasures in the "
      "design (masking, sensors, secure boot, key storage) and extensive "
      "documentation.")
    box("warn", "Pitfall: bolting on safety or security late",
        "Safety and security requirements change the architecture: "
        "lockstep cores double CPU area, ECC widens every memory, secure "
        "key storage needs special memories and fuses, and the "
        "development process itself must be audited from the start. A "
        "team that decides to 'get ASIL B' after RTL freeze usually has "
        "to redo large parts of the project.")

    h2("Summary")
    bul([
        "Projects progress through spec, architecture, RTL, netlist and "
        "tapeout freezes, each gated by a data-driven review; late changes "
        "must be replanned, not squeezed in.",
        "Team composition shifts from architects to verification to "
        "physical design to validation; verification is typically the "
        "largest group.",
        "Synopsys, Cadence and Siemens supply most commercial EDA "
        "(Synopsys now also owns Ansys); licences, compute and foundry "
        "sign-off certification shape the flow; open-source tools cover "
        "open PDKs.",
        "Reproducible methodology means scripted flows, version-controlled "
        "and tagged design data, CI regressions and QoR dashboards.",
        "NRE = people + EDA + IP + masks + test chips + package/test "
        "development; unit cost = wafer cost / (DPW x yield) + package + "
        "test, divided by final yield. Advanced nodes pay off in "
        "performance and energy, and in cost only at very high volume.",
        "Make-versus-buy and risk registers structure the business "
        "decisions; ISO 26262, IEC 61508 and Common Criteria impose "
        "process, metrics and evidence that must be planned from day one.",
    ])

    h2("Exercises")
    bul([
        "Draw a milestone plan for a 40 mm^2 SoC with a 20-month schedule "
        "from spec freeze to tapeout. Place each freeze and review and "
        "state its exit criteria.",
        "Change cost.py to a 400 mm^2 design at 28 nm (scale the other "
        "nodes by the same ratios). Where is the cheapest node now, and "
        "why does the answer differ from the small-die case?",
        "Using nre.py, estimate the NRE if verification takes six months "
        "longer with the same team, and the resulting increase in cost per "
        "unit at 2 million units.",
        "An FPGA solution costs $80 per unit with $2M NRE; an ASIC costs "
        "$9 per unit with $30M NRE. Compute the break-even volume. How "
        "does a 9-month later market entry for the ASIC change the "
        "decision?",
        "For an ASIL D microcontroller, list five on-chip safety "
        "mechanisms and the fault classes each detects. Which of them "
        "contribute to the SPFM and which to the LFM?",
    ], ordered=True)


# =============================================================================
#                                  PART V
# =============================================================================
def part5():
    part("After Tapeout",
         "What happens once the GDSII has gone to the foundry: packaging, "
         "2.5D/3D integration and chiplets; manufacturing test, yield and "
         "reliability physics; silicon bring-up, validation, "
         "characterisation and qualification; and the methodology, project "
         "management and economics that decide whether an ASIC is worth "
         "building at all.")
    _ch20()
    _ch21()
    _ch22()
    _ch23()
