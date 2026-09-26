"""Part IV - Implementation and Sign-off (Chapters 15-19).

Placement, clock tree synthesis, routing/SI/DFM, sign-off and ECO/tapeout/mask
making. Every out() card in this part was pasted from a real run in this
environment: Python 3 + numpy models (quadratic placement, Elmore clock-tree
skew, Lee maze routing, crosstalk, Black's equation, dies per wafer), netgen
1.5.133 LVS comparisons and a magic 8.3 DRC check. Commercial-tool reports,
where shown, are labelled as illustrative.
"""

from asic_guide.common import *  # noqa: F401,F403

# -----------------------------------------------------------------------------
# Scripts and captured outputs (verbatim from the runs described above)
# -----------------------------------------------------------------------------
_SRC_QPLACE = [
    '# Quadratic (clique-model) placement of a tiny netlist, then row legalization',
    'import numpy as np',
    'rng = np.random.default_rng(7)',
    'W, H = 100.0, 100.0                       # core size in um',
    'pads = {"IN0": (0, 20), "IN1": (0, 80), "OUT": (100, 50), "CLK": (50, 100)}',
    'cells = ["u1", "u2", "u3", "u4", "u5", "u6"]',
    'nets = [("IN0", "u1"), ("IN1", "u2"), ("u1", "u2", "u3"), ("u3", "u4"),',
    '        ("u4", "u5", "u6"), ("u6", "OUT"), ("CLK", "u4", "u5"), ("u2", "u5")]',
    'idx = {c: i for i, c in enumerate(cells)}',
    'n = len(cells)',
    '',
    'def hpwl(pos):',
    '    tot = 0.0',
    '    for net in nets:',
    '        xs = [pos[t][0] for t in net]; ys = [pos[t][1] for t in net]',
    '        tot += (max(xs) - min(xs)) + (max(ys) - min(ys))',
    '    return tot',
    '',
    '# Build A x = bx, A y = by: each k-pin net -> clique with weight 1/(k-1)',
    'A = np.zeros((n, n)); bx = np.zeros(n); by = np.zeros(n)',
    'for net in nets:',
    '    w = 1.0 / (len(net) - 1)',
    '    for i in range(len(net)):',
    '        for j in range(i + 1, len(net)):',
    '            a, b = net[i], net[j]',
    '            for s, t in ((a, b), (b, a)):',
    '                if s in idx:',
    '                    A[idx[s], idx[s]] += w',
    '                    if t in idx:',
    '                        A[idx[s], idx[t]] -= w',
    '                    else:',
    '                        bx[idx[s]] += w * pads[t][0]; by[idx[s]] += w * pads[t][1]',
    'x = np.linalg.solve(A, bx); y = np.linalg.solve(A, by)',
    '',
    'rand = {c: (rng.uniform(0, W), rng.uniform(0, H)) for c in cells}',
    'rand.update(pads)',
    'qp = {c: (x[idx[c]], y[idx[c]]) for c in cells}; qp.update(pads)',
    '',
    '# Legalize: snap to 10-um rows, 5-um sites, cells 10 um wide, no overlap (greedy)',
    'ROW, SITE, CW = 10.0, 5.0, 10.0',
    'used = {}',
    'leg = dict(pads)',
    'for c in sorted(cells, key=lambda c: qp[c][0]):',
    '    best = None',
    '    for r in range(int(H // ROW)):',
    '        yy = r * ROW + ROW / 2',
    '        xx = max(0.0, min(W - CW, round((qp[c][0] - CW / 2) / SITE) * SITE))',
    '        while any(abs(xx - u) < CW for u in used.get(r, [])):',
    '            xx += SITE',
    '        if xx > W - CW:',
    '            continue',
    '        d = abs(xx + CW / 2 - qp[c][0]) + abs(yy - qp[c][1])',
    '        if best is None or d < best[0]:',
    '            best = (d, r, xx, yy)',
    '    d, r, xx, yy = best',
    '    used.setdefault(r, []).append(xx)',
    '    leg[c] = (xx + CW / 2, yy)',
    '',
    'print("Laplacian-like matrix A (x and y share it):")',
    'for i in range(n):',
    '    print("  " + " ".join("%6.2f" % v for v in A[i]))',
    'print("%-4s %16s %16s %16s" % ("cell", "random (x,y)", "quadratic (x,y)", "legal (x,y)"))',
    'for c in cells:',
    '    print("%-4s  (%5.1f,%5.1f)    (%5.1f,%5.1f)    (%5.1f,%5.1f)" %',
    '          (c, rand[c][0], rand[c][1], qp[c][0], qp[c][1], leg[c][0], leg[c][1]))',
    'print("HPWL random placement   : %6.1f um" % hpwl(rand))',
    'print("HPWL quadratic (overlap): %6.1f um" % hpwl(qp))',
    'print("HPWL after legalization : %6.1f um" % hpwl(leg))',
]

_OUT_QPLACE = [
    'Laplacian-like matrix A (x and y share it):',
    '    2.00  -0.50  -0.50   0.00   0.00   0.00',
    '   -0.50   3.00  -0.50   0.00  -1.00   0.00',
    '   -0.50  -0.50   2.00  -1.00   0.00   0.00',
    '    0.00   0.00  -1.00   3.00  -1.00  -0.50',
    '    0.00  -1.00   0.00  -1.00   3.00  -0.50',
    '    0.00   0.00   0.00  -0.50  -0.50   2.00',
    'cell     random (x,y)  quadratic (x,y)      legal (x,y)',
    'u1    ( 62.5, 89.7)    ( 13.1, 43.8)    ( 15.0, 45.0)',
    'u2    ( 77.6, 22.5)    ( 21.5, 69.8)    ( 20.0, 65.0)',
    'u3    ( 30.0, 87.4)    ( 31.0, 65.3)    ( 30.0, 65.0)',
    'u4    (  0.5, 82.1)    ( 44.8, 73.7)    ( 50.0, 75.0)',
    'u5    ( 79.7, 46.8)    ( 42.4, 74.9)    ( 40.0, 75.0)',
    'u6    ( 30.3, 27.8)    ( 71.8, 62.1)    ( 70.0, 65.0)',
    'HPWL random placement   :  800.9 um',
    'HPWL quadratic (overlap):  277.1 um',
    'HPWL after legalization :  290.0 um',
]

_SRC_CTREE = [
    '# Elmore delay of a 16-sink H-tree vs an unbalanced "comb" tree on a 1 mm x 1 mm block',
    'r, c = 0.10, 0.20e-15      # wire: 0.10 ohm/um, 0.20 fF/um (typical upper-metal order)',
    'RDRV, CSINK = 50.0, 5e-15  # clock driver 50 ohm, 5 fF per sink (flop clock pins lumped)',
    '',
    'class Node:',
    '    def __init__(s, name, x, y):',
    '        s.name, s.x, s.y, s.kids, s.len = name, x, y, [], 0.0',
    '',
    'def link(par, ch, length=None):',
    '    ch.len = length if length is not None else abs(par.x-ch.x) + abs(par.y-ch.y)',
    '    par.kids.append(ch); return ch',
    '',
    "def cdown(n):              # total capacitance below and including node n's wire",
    '    n.cd = (CSINK if not n.kids else 0.0) + sum(cdown(k) for k in n.kids)',
    '    return n.cd + c * n.len',
    '',
    'def elmore(n, t, out):     # pi-model per segment: R_seg * (C_seg/2 + C_downstream)',
    '    R = r * n.len',
    '    t = t + R * (c * n.len / 2 + n.cd)',
    '    if not n.kids: out[n.name] = t',
    '    for k in n.kids: elmore(k, t, out)',
    '    return out',
    '',
    'def analyse(root, label):',
    '    ctot = cdown(root)',
    '    d = elmore(root, RDRV * ctot, {})',
    '    wl = sum_len(root)',
    '    v = sorted(d.values())',
    '    print("%-23s %5.0f %6.0f %8.1f %8.1f %7.1f" % (label, wl, ctot*1e15, v[0]*1e12,',
    '                                                  v[-1]*1e12, (v[-1]-v[0])*1e12))',
    '    return d',
    '',
    'def sum_len(n): return n.len + sum(sum_len(k) for k in n.kids)',
    '',
    'def htree(par, x, y, half, level, tag):',
    '    if level == 0:',
    '        link(par, Node("ff" + tag, x, y)); return',
    '    h = Node("h" + tag, x, y); link(par, h)',
    '    for i, (dx, dy) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1))):',
    '        htree(h, x + dx*half, y + dy*half, half/2, level-1, tag + str(i))',
    '',
    'sinks = [(125 + 250*i, 125 + 250*j) for i in range(4) for j in range(4)]',
    '',
    'print("%-23s %5s %6s %8s %8s %7s" % ("16 sinks, 1x1 mm", "wire", "C(fF)", "min(ps)",',
    '                                     "max(ps)", "skew"))',
    'root = Node("root", 500, 500)',
    'htree(root, 500, 500, 250, 2, "")',
    'dh = analyse(root, "H-tree (balanced)")',
    '',
    '# comb: driver at the left edge, one trunk along y=500, a branch per column',
    'root2 = Node("root", 0, 500); prev = root2',
    'for i, xcol in enumerate((125, 375, 625, 875)):',
    '    t = link(prev, Node("t%d" % i, xcol, 500)); prev = t',
    '    for j, ycol in enumerate((125, 375, 625, 875)):',
    '        link(t, Node("ff%d%d" % (i, j), xcol, ycol))',
    'dc = analyse(root2, "comb/fishbone (unbal.)")',
    '',
    '# comb again, with the driver in the centre of the trunk',
    'root3 = Node("root", 500, 500)',
    'for i, xcol in enumerate((125, 375, 625, 875)):',
    '    t = link(root3, Node("t%d" % i, xcol, 500))',
    '    for j, ycol in enumerate((125, 375, 625, 875)):',
    '        link(t, Node("ff%d%d" % (i, j), xcol, ycol))',
    'analyse(root3, "comb, centre-driven")',
    '',
    'print("\\ncomb/fishbone arrival per sink column (ps), row = y position:")',
    'for j in range(4):',
    '    print("  y=%3d: " % (125+250*j) + "  ".join("%6.1f" % (dc["ff%d%d" % (i, j)]*1e12)',
    '                                              for i in range(4)))',
]

_OUT_CTREE = [
    '16 sinks, 1x1 mm         wire  C(fF)  min(ps)  max(ps)    skew',
    'H-tree (balanced)        6000   1280     78.2     78.2     0.0',
    'comb/fishbone (unbal.)   4875   1055     66.0    106.0    40.0',
    'comb, centre-driven      5000   1080     57.1     65.2     8.1',
    '',
    'comb/fishbone arrival per sink column (ps), row = y position:',
    '  y=125:   67.4    87.0    99.9   106.0',
    '  y=375:   66.0    85.6    98.5   104.6',
    '  y=625:   66.0    85.6    98.5   104.6',
    '  y=875:   67.4    87.0    99.9   106.0',
]

_SRC_LEE = [
    '# Lee maze router: BFS wave expansion + backtrace on a single-layer grid',
    'from collections import deque',
    'GRID = [',
    '    "..........X.........",',
    '    "....................",',
    '    "..S.....#...........",',
    '    "........#...........",',
    '    "........#.....####..",',
    '    "..####..#........#..",',
    '    ".....#..#........#..",',
    '    ".....#..#####....#T.",',
    '    ".....#...........#..",',
    '    "..........Y.........",',
    ']',
    'R, C = len(GRID), len(GRID[0])',
    'g = [list(row) for row in GRID]',
    'find = lambda ch: next((r, c) for r in range(R) for c in range(C) if g[r][c] == ch)',
    'S, T = find("S"), find("T")',
    '',
    'def lee(src, dst, blocked):',
    '    dist = {src: 0}; q = deque([src]); expanded = 0',
    '    while q:                                   # 1) wave expansion',
    '        cur = q.popleft(); expanded += 1',
    '        if cur == dst: break',
    '        r, c = cur',
    '        for nr, nc in ((r-1, c), (r+1, c), (r, c-1), (r, c+1)):',
    '            if 0 <= nr < R and 0 <= nc < C and (nr, nc) not in dist \\',
    '               and not blocked(nr, nc):',
    '                dist[(nr, nc)] = dist[cur] + 1; q.append((nr, nc))',
    '    if dst not in dist: return None, expanded',
    '    path = [dst]                               # 2) backtrace, prefer going straight',
    '    while path[-1] != src:',
    '        r, c = path[-1]',
    '        nbrs = [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]',
    '        if len(path) > 1:                      # try same direction first -> fewer bends',
    '            pr, pc = path[-2]; nbrs.sort(key=lambda n: (n[0]-r, n[1]-c) != (r-pr, c-pc))',
    '        path.append(next(n for n in nbrs if dist.get(n) == dist[(r, c)] - 1))',
    '    return path[::-1], expanded',
    '',
    '',
    'A = (find("S"), find("T")); B = (find("X"), find("Y"))',
    '',
    'def route_all(order):',
    '    occ = {}                                   # grid cell -> net that owns it',
    '    res = {}',
    '    for name, (s, t) in order:',
    '        def blocked(r, c, name=name):',
    '            return g0[r][c] == "#" or occ.get((r, c), name) != name',
    '        path, exp = lee(s, t, blocked)',
    '        res[name] = (path, exp)',
    '        if path:',
    '            for cell in path: occ[cell] = name',
    '    return res, occ',
    '',
    'g0 = [row[:] for row in g]',
    'for label, order in (("order A then B", (("A", A), ("B", B))),',
    '                     ("order B then A", (("B", B), ("A", A)))):',
    '    res, occ = route_all(order)',
    '    pic = [row[:] for row in g0]',
    '    for cell, name in occ.items():',
    '        if pic[cell[0]][cell[1]] == ".": pic[cell[0]][cell[1]] = "*" if name == "A" else "+"',
    '    print("%s: " % label + "  ".join(("%s len=%d expanded=%d" % (n, len(p)-1, e)) if p',
    '          else ("%s UNROUTABLE (expanded=%d)" % (n, e)) for n, (p, e) in res.items()))',
    '    print("   " + "".join(str(c % 10) for c in range(C)))',
    '    for r in range(R): print("%2d " % r + "".join(pic[r]))',
]

_OUT_LEE = [
    'order A then B: A len=23 expanded=169  B len=27 expanded=116',
    '   01234567890123456789',
    ' 0 .+++++++++X.........',
    ' 1 .+*****************.',
    ' 2 .+S.....#.........*.',
    ' 3 .++++++.#.........*.',
    ' 4 ......+.#.....####*.',
    ' 5 ..####+.#........#*.',
    ' 6 .....#+.#........#*.',
    ' 7 .....#+.#####....#T.',
    ' 8 .....#+++++......#..',
    ' 9 ..........Y.........',
    'order B then A: B len=15 expanded=145  A UNROUTABLE (expanded=66)',
    '   01234567890123456789',
    ' 0 .......+++X.........',
    ' 1 .......+............',
    ' 2 ..S....+#...........',
    ' 3 .......+#...........',
    ' 4 .......+#.....####..',
    ' 5 ..####.+#........#..',
    ' 6 .....#.+#........#..',
    ' 7 .....#.+#####....#T.',
    ' 8 .....#.++++......#..',
    ' 9 ..........Y.........',
]

_SRC_XTALK = [
    '# Crosstalk on a 500-um victim between two parallel aggressors (lumped/Elmore estimates)',
    'import math',
    'VDD, L = 0.75, 500.0                  # supply (V), victim length (um)',
    'rw = 2.0                              # victim wire resistance, ohm/um (thin lower metal)',
    'cg = 0.08e-15                         # victim area+fringe cap to ground, F/um',
    'cc_min = 0.07e-15                     # coupling cap to EACH neighbour at min spacing, F/um',
    'cl = 3e-15                            # receiver pin cap',
    'rdrv = 800.0                          # victim driver output resistance (weak driver)',
    '',
    'def delay(k, cc):',
    '    """Elmore delay (0.69 * sum RC) with Miller factor k applied to both coupling caps."""',
    '    cw = (cg + 2 * k * cc) * L',
    '    return 0.69 * (rdrv * (cw + cl) + rw * L * (cw / 2 + cl))',
    '',
    'print("victim %d um, Rdrv=%d ohm: Cg=%.1f fF, Cc=%.1f fF per side (min spacing)"',
    '      % (L, rdrv, cg * L * 1e15, cc_min * L * 1e15))',
    'print("%-34s %9s %9s %9s %9s" % ("configuration", "k=0 (ps)", "k=1 (ps)", "k=2 (ps)",',
    '                                  "window"))',
    'for label, cc in (("min spacing", cc_min), ("2x spacing (Cc ~ 0.5x)", cc_min * 0.5),',
    '                  ("3x spacing (Cc ~ 0.3x)", cc_min * 0.3)):',
    '    d0, d1, d2 = (delay(k, cc) * 1e12 for k in (0, 1, 2))',
    '    print("%-34s %9.1f %9.1f %9.1f %8.1f%%" % (label, d0, d1, d2, 100 * (d2 - d0) / d1))',
    '# shielding: neighbours become VSS/VDD wires -> k is always 1, but Cc still loads the net',
    'd_sh = delay(1, cc_min) * 1e12',
    'print("%-34s %9s %9.1f %9s %8.1f%%" % ("shielded (VSS both sides)", "-", d_sh, "-", 0))',
    '',
    'print("\\nglitch on a quiet victim held low by its driver; one aggressor, parallel run Lc:")',
    'for lc in (100.0, 500.0):',
    '    cc = cc_min * lc',
    '    ctot = (cg * L + cc_min * L * 2) + cl        # everything on the victim, others quiet',
    '    for rhold in (300.0, 1500.0):',
    '        for tr in (30e-12, 100e-12):',
    '            tau = (rhold + rw * L / 2) * ctot',
    '            vp = VDD * (cc / ctot) * (tau / tr) * (1 - math.exp(-tr / tau))',
    '            print("  Lc=%3.0f um Rhold=%4.0f ohm slew=%3.0f ps -> peak=%3.0f mV (%2.0f%% VDD)"',
    '                  % (lc, rhold, tr * 1e12, vp * 1e3, 100 * vp / VDD))',
]

_OUT_XTALK = [
    'victim 500 um, Rdrv=800 ohm: Cg=40.0 fF, Cc=35.0 fF per side (min spacing)',
    'configuration                       k=0 (ps)  k=1 (ps)  k=2 (ps)    window',
    'min spacing                             39.6     102.4     165.2    122.6%',
    '2x spacing (Cc ~ 0.5x)                  39.6      71.0     102.4     88.4%',
    '3x spacing (Cc ~ 0.3x)                  39.6      58.4      77.3     64.5%',
    'shielded (VSS both sides)                  -     102.4         -      0.0%',
    '',
    'glitch on a quiet victim held low by its driver; one aggressor, parallel run Lc:',
    '  Lc=100 um Rhold= 300 ohm slew= 30 ps -> peak= 40 mV ( 5% VDD)',
    '  Lc=100 um Rhold= 300 ohm slew=100 ps -> peak= 28 mV ( 4% VDD)',
    '  Lc=100 um Rhold=1500 ohm slew= 30 ps -> peak= 44 mV ( 6% VDD)',
    '  Lc=100 um Rhold=1500 ohm slew=100 ps -> peak= 38 mV ( 5% VDD)',
    '  Lc=500 um Rhold= 300 ohm slew= 30 ps -> peak=198 mV (26% VDD)',
    '  Lc=500 um Rhold= 300 ohm slew=100 ps -> peak=141 mV (19% VDD)',
    '  Lc=500 um Rhold=1500 ohm slew= 30 ps -> peak=218 mV (29% VDD)',
    '  Lc=500 um Rhold=1500 ohm slew=100 ps -> peak=188 mV (25% VDD)',
]

_SRC_BLACK = [
    "# Black's equation: MTTF = A * J^-n * exp(Ea / (k T)); everything relative to a reference",
    'import math',
    'k = 8.617e-5                     # Boltzmann constant, eV/K',
    'n, Ea = 2.0, 0.85                # typical Cu-interconnect fit values (foundry-specific!)',
    'Jref, Tref = 1.0, 105.0          # reference: 1.0 MA/cm^2 at 105 C  -> MTTF = 1.00 (normalised)',
    '',
    'def rel_mttf(J, Tc):',
    '    return (J / Jref) ** (-n) * math.exp(Ea / k * (1 / (Tc + 273.15) - 1 / (Tref + 273.15)))',
    '',
    'temps = (85, 105, 125, 150)',
    'print("relative MTTF (1.00 = 1 MA/cm^2 at 105 C), n=%.1f, Ea=%.2f eV" % (n, Ea))',
    'print("J (MA/cm^2) " + "".join("%10s" % ("%d C" % t) for t in temps))',
    'for J in (0.5, 1.0, 1.5, 2.0, 3.0):',
    '    print("   %4.1f     " % J + "".join("%10.2f" % rel_mttf(J, t) for t in temps))',
    '',
    'print("\\nallowed J for the SAME lifetime as 1 MA/cm^2 at 105 C:")',
    'for t in temps:',
    '    print("  %3d C : Jmax = %.2f MA/cm^2" % (t, math.sqrt(math.exp(Ea / k * (1 / (t + 273.15)',
    '          - 1 / (Tref + 273.15))))))',
    'print("\\nself-heating: a signal wire at 105 C ambient that heats by dT")',
    'for dT in (0, 5, 10, 20):',
    '    print("  dT=%2d C -> lifetime x %.2f" % (dT, rel_mttf(1.0, Tref + dT)))',
]

_OUT_BLACK = [
    'relative MTTF (1.00 = 1 MA/cm^2 at 105 C), n=2.0, Ea=0.85 eV',
    'J (MA/cm^2)       85 C     105 C     125 C     150 C',
    '    0.5          17.17      4.00      1.08      0.25',
    '    1.0           4.29      1.00      0.27      0.06',
    '    1.5           1.91      0.44      0.12      0.03',
    '    2.0           1.07      0.25      0.07      0.02',
    '    3.0           0.48      0.11      0.03      0.01',
    '',
    'allowed J for the SAME lifetime as 1 MA/cm^2 at 105 C:',
    '   85 C : Jmax = 2.07 MA/cm^2',
    '  105 C : Jmax = 1.00 MA/cm^2',
    '  125 C : Jmax = 0.52 MA/cm^2',
    '  150 C : Jmax = 0.25 MA/cm^2',
    '',
    'self-heating: a signal wire at 105 C ambient that heats by dT',
    '  dT= 0 C -> lifetime x 1.00',
    '  dT= 5 C -> lifetime x 0.71',
    '  dT=10 C -> lifetime x 0.51',
    '  dT=20 C -> lifetime x 0.27',
]

_SRC_DPW = [
    '# Gross dies per wafer, yield and cost per good die on a 300-mm wafer',
    'import math',
    'D = 300.0            # wafer diameter, mm',
    'EE = 3.0             # edge exclusion, mm',
    'SCRIBE = 0.1         # scribe (saw) street added to each die edge, mm',
    'D0 = 0.10            # defect density, defects/cm^2 (mature-process order of magnitude)',
    'WAFER_COST = 15000.0 # USD per processed wafer (advanced-node order of magnitude)',
    '',
    'def dpw_formula(w, h):',
    '    s = (w + SCRIBE) * (h + SCRIBE); d = D - 2 * EE',
    '    return math.pi * (d / 2) ** 2 / s - math.pi * d / math.sqrt(2 * s)',
    '',
    'def dpw_count(w, h):',
    '    """Exact count of whole dies on a grid (best of 4 grid offsets)."""',
    '    R = D / 2 - EE; W, H = w + SCRIBE, h + SCRIBE; best = 0',
    '    for ox in (0.0, W / 2):',
    '        for oy in (0.0, H / 2):',
    '            cnt = 0',
    '            nx, ny = int(R // W) + 2, int(R // H) + 2',
    '            for i in range(-nx, nx):',
    '                for j in range(-ny, ny):',
    '                    x0, y0 = i * W + ox, j * H + oy',
    '                    if all(math.hypot(x, y) <= R for x in (x0, x0 + W) for y in (y0, y0 + H)):',
    '                        cnt += 1',
    '            best = max(best, cnt)',
    '    return best',
    '',
    'print("300-mm wafer, %.0f-mm edge exclusion, %.2f-mm scribe, D0=%.2f/cm^2, wafer=$%.0f"',
    '      % (EE, SCRIBE, D0, WAFER_COST))',
    'print("%12s %8s %8s %8s %9s %11s" % ("die (mm)", "area", "formula", "counted",',
    '                                     "Y(Murphy)", "$/good die"))',
    'for w, h in ((2, 2), (5, 5), (10, 10), (15, 15), (20, 20), (26, 33)):',
    '    a = w * h; A = a / 100.0',
    '    y = ((1 - math.exp(-A * D0)) / (A * D0)) ** 2',
    '    gross = dpw_count(w, h)',
    '    print("%5.0f x %-5.0f %6.0f %9.0f %8d %8.1f%% %11.2f" % (w, h, a, dpw_formula(w, h), gross,',
    '          100 * y, WAFER_COST / (gross * y)))',
]

_OUT_DPW = [
    '300-mm wafer, 3-mm edge exclusion, 0.10-mm scribe, D0=0.10/cm^2, wafer=$15000',
    '    die (mm)     area  formula  counted Y(Murphy)  $/good die',
    '    2 x 2          4     15083    15110     99.6%        1.00',
    '    5 x 5         25      2482     2500     97.5%        6.15',
    '   10 x 10       100       601      612     90.6%       27.06',
    '   15 x 15       225       254      266     80.2%       70.32',
    '   20 x 20       400       136      148     67.9%      149.20',
    '   26 x 33       858        56       64     45.1%      520.06',
]

_SPI_SCH = [
    '* schematic: 2-input NAND followed by an inverter (AND2)',
    '.subckt and2 A B Y VDD VSS',
    'M1 n1 A VDD VDD pmos W=0.84u L=0.15u',
    'M2 n1 B VDD VDD pmos W=0.84u L=0.15u',
    'M3 n1 A x   VSS nmos W=0.64u L=0.15u',
    'M4 x  B VSS VSS nmos W=0.64u L=0.15u',
    'M5 Y  n1 VDD VDD pmos W=1.00u L=0.15u',
    'M6 Y  n1 VSS VSS nmos W=0.65u L=0.15u',
    '.ends',
]

_SPI_OK = [
    '* extracted layout netlist: device order and internal names differ',
    '.subckt and2 VSS VDD Y B A',
    'M10 Y net7 VSS VSS nmos W=0.65u L=0.15u',
    'M11 Y net7 VDD VDD pmos W=1.00u L=0.15u',
    'M12 net9 B VSS VSS nmos W=0.64u L=0.15u',
    'M13 net7 A net9 VSS nmos W=0.64u L=0.15u',
    'M14 net7 B VDD VDD pmos W=0.84u L=0.15u',
    'M15 net7 A VDD VDD pmos W=0.84u L=0.15u',
    '.ends',
]

_SPI_BAD = [
    '* layout netlist, two bugs: B pmos drain shorted to Y; inverter nmos too narrow',
    '.subckt and2 VSS VDD Y B A',
    'M10 Y net7 VSS VSS nmos W=0.42u L=0.15u',
    'M11 Y net7 VDD VDD pmos W=1.00u L=0.15u',
    'M12 net9 B VSS VSS nmos W=0.64u L=0.15u',
    'M13 net7 A net9 VSS nmos W=0.64u L=0.15u',
    'M14 Y B VDD VDD pmos W=0.84u L=0.15u',
    'M15 net7 A VDD VDD pmos W=0.84u L=0.15u',
    '.ends',
]

_SPI_W = [
    '* extracted layout netlist with one bug: the inverter nmos is drawn too narrow (0.42u vs 0.65u)',
    '.subckt and2 VSS VDD Y B A',
    'M10 Y net7 VSS VSS nmos W=0.42u L=0.15u',
    'M11 Y net7 VDD VDD pmos W=1.00u L=0.15u',
    'M12 net9 B VSS VSS nmos W=0.64u L=0.15u',
    'M13 net7 A net9 VSS nmos W=0.64u L=0.15u',
    'M14 net7 B VDD VDD pmos W=0.84u L=0.15u',
    'M15 net7 A VDD VDD pmos W=0.84u L=0.15u',
    '.ends',
]

_LVS_SETUP = [
    '# minimal netgen setup: compare MOSFET W and L with a 1% tolerance',
    '# (source/drain of built-in nmos/pmos devices are already permutable)',
    'foreach dev {nmos pmos} {',
    '  foreach c {-circuit1 -circuit2} {',
    '    property "$c $dev" tolerance {w 0.01} {l 0.01}',
    '  }',
    '}',
]

_OUT_LVS_OK = [
    'Reading netlist file lay_ok.spice',
    'Reading netlist file sch.spice',
    'Reading setup file setup.tcl',
    'Comparison output logged to file ok.out',
    'Logging to file "ok.out" enabled',
    "Contents of circuit 1:  Circuit: 'and2'",
    'Circuit and2 contains 6 device instances.',
    '  Class: pmos                  instances:   3',
    '  Class: nmos                  instances:   3',
    'Circuit contains 7 nets.',
    "Contents of circuit 2:  Circuit: 'and2'",
    'Circuit and2 contains 6 device instances.',
    '  Class: pmos                  instances:   3',
    '  Class: nmos                  instances:   3',
    'Circuit contains 7 nets.',
    '',
    'Circuit 1 contains 6 devices, Circuit 2 contains 6 devices.',
    'Circuit 1 contains 7 nets,    Circuit 2 contains 7 nets.',
    '',
    'Netlists match uniquely.',
    'Result: Circuits match uniquely.',
    'Logging to file "ok.out" disabled',
    'LVS Done.',
]

_OUT_LVS_BAD = [
    'NET mismatches: Class fragments follow (with fanout counts):',
    'Circuit 1: and2                            |Circuit 2: and2',
    '',
    '---------------------------------------------------------------------------------------',
    'Net: Y                                     |Net: n1',
    '  nmos/drain = 1                           |  pmos/drain = 2',
    '  pmos/drain = 2                           |  nmos/drain = 1',
    '                                           |  pmos/gate = 1',
    '                                           |  nmos/gate = 1',
    '                                           |',
    'Net: net7                                  |Net: Y',
    '  nmos/gate = 1                            |  pmos/drain = 1',
    '  pmos/gate = 1                            |  nmos/drain = 1',
    '  nmos/drain = 1                           |',
    '  pmos/drain = 1                           |',
    '---------------------------------------------------------------------------------------',
    'Netlists do not match.',
]

_OUT_LVS_W = [
    'Circuit 1 contains 6 devices, Circuit 2 contains 6 devices.',
    'Circuit 1 contains 7 nets,    Circuit 2 contains 7 nets.',
    '',
    'Netlists match uniquely.',
    'There were property errors.',
    'nmos10 vs. nmos6:',
    ' W circuit1: 4.2e-07   circuit2: 6.5e-07   (delta=43%, cutoff=1%)',
    'Result: Circuits match uniquely.',
    'Property errors were found.',
    'The following cells had property errors: and2',
    '',
    'Logging to file "w.out" disabled',
    'LVS Done.',
]

_SRC_DRC = [
    '# three metal1 shapes in the SCMOS (lambda-based) technology',
    'cellname rename (UNNAMED) demo',
    'box 0 0 3 20;     paint metal1   ;# OK: 3 lambda wide (min width 3)',
    'box 10 0 12 20;   paint metal1   ;# too narrow: 2 lambda',
    'box 14 0 17 20;   paint metal1   ;# 2 lambda from the previous wire (min space 3)',
    'box 0 0 17 20',
    'drc check',
    'drc catchup',
    'puts "DRC error count: [drc list count total]"',
    'foreach {why boxes} [drc listall why] {',
    '  puts "RULE: $why"',
    '  foreach b $boxes { puts "   at (lambda) [lrange $b 0 3]" }',
    '}',
    'quit -noprompt',
]

_OUT_DRC = [
    'DRC error count: 2',
    'RULE: First-level metal spacing must be at least 3 (MOSIS rule #7.2)',
    '   at (lambda) 14 0 15 20',
    'RULE: First-level metal width must be at least 3 (MOSIS rule #7.1)',
    '   at (lambda) 12 0 13 20',
]

_OUT_DRC_FIX = [
    'DRC error count: 0',
    'No errors found.',
]


# =============================================================================
#                 CHAPTER 15 - PLACEMENT AND OPTIMISATION
# =============================================================================
def _ch15():
    chapter("Placement and Optimisation", newpage=False)
    p("Chapter 14 ended with a floorplan: a die outline, a core area cut into "
      "standard-cell rows, hard macros in fixed positions, an I/O ring and a "
      "power grid. What it does not yet contain is the bulk of the design - "
      "typically hundreds of thousands to tens of millions of standard cells "
      "that the synthesis netlist (Chapter 8) instantiates with no notion of "
      "where they will sit. **Placement** assigns every one of those cells a "
      "legal, non-overlapping location on a row site, and the **placement "
      "optimisation** that runs alongside it resizes, buffers and restructures "
      "the netlist so that, once cells are at their real positions, timing, "
      "congestion and power still close.")
    p("Placement is the step where the netlist first meets geometry, and it "
      "sets the ceiling for everything downstream. A poor placement cannot be "
      "rescued by clock tree synthesis or routing: the wires are already too "
      "long, the cells too crowded, the critical paths too spread out. That "
      "is why physical-design engineers spend far more iterations in "
      "placement than anywhere else, and why modern synthesis tools "
      "(\"physical synthesis\", Genus iSpatial, Fusion Compiler) run a "
      "placement engine internally before the netlist is ever handed over.")
    tbl(["Item", "Content"], [
        ["Owner", "Physical-design (PD/back-end) engineer for the block; "
                  "timing sign-off engineer reviews the post-place timing "
                  "reports; DFT engineer supplies scan-chain definitions."],
        ["Inputs", "Floorplanned database (DEF/OpenDB or tool DB) with macros, "
                   "blockages, power grid and pins; gate-level netlist; SDC; "
                   "Liberty (.lib) for all corners; tech + cell LEF; "
                   "scan DEF; UPF for multi-voltage designs; "
                   "don't-touch/size-only lists."],
        ["Outputs", "Placed and optimised database; updated netlist (with "
                    "new buffers and resized cells); reordered scan DEF; "
                    "timing, congestion and utilisation reports that gate "
                    "the move to CTS."],
        ["Typical runtime", "Hours for a 1-5 M instance block on a modern "
                            "multi-threaded tool; days for full-chip flat "
                            "runs, which is one reason designs are "
                            "partitioned into blocks (Chapter 13)."],
    ], widths=[1.2, 5], caption="Placement at a glance", bold_first=True)

    # ------------------------------------------------------------------
    h2("The placement problem")
    p("Formally, placement is an optimisation problem: find (x, y) for every "
      "movable cell such that cells do not overlap, every cell sits on a "
      "legal row site with the right orientation, and a cost function is "
      "minimised. The primary cost is **total wirelength**, because wire "
      "length drives wire capacitance (delay and dynamic power), routing "
      "demand (congestion) and coupling (crosstalk). Secondary costs are "
      "timing (weighted wirelength on critical nets), congestion, power "
      "(weighting high-activity nets) and, in multi-voltage designs, keeping "
      "cells inside their voltage areas.")
    p("Actual routed length is unknown until routing, so placers use cheap "
      "proxies. The industry-standard proxy is the **half-perimeter "
      "wirelength (HPWL)**: for each net, the half perimeter of the smallest "
      "rectangle enclosing all its pins. HPWL is exact for 2- and 3-pin nets "
      "routed as a Steiner tree and a good lower bound for larger nets.")
    eq(["HPWL(net) = (max x_i - min x_i) + (max y_i - min y_i)     over pins i of the net",
        "",
        "Total cost = sum over nets of  w_net * HPWL(net)",
        "",
        "w_net > 1 for timing-critical nets, high-activity nets (power), clock-adjacent nets"],
       caption="Half-perimeter wirelength, the universal placement metric")
    p("The problem is NP-hard even for the pure wirelength objective, so "
      "every production placer is a stack of heuristics. The major algorithm "
      "families, historically and today, are:")
    tbl(["Family", "Idea", "Where it is used"], [
        ["Min-cut partitioning", "Recursively bisect the netlist and the "
         "die (Fiduccia-Mattheyses, hMETIS) so few nets cross each cut.",
         "1990s placers (Capo); still used for coarse clustering and "
         "hierarchical/multi-level flows."],
        ["Simulated annealing", "Random swaps/moves accepted with probability "
         "exp(-dCost/T); temperature T slowly lowered (TimberWolf).",
         "Excellent quality on small problems; too slow for millions of "
         "cells; survives in detailed placement and macro placement."],
        ["Force-directed", "Nets act as springs pulling connected cells "
         "together; extra 'spreading forces' push cells out of dense "
         "regions.", "Conceptual basis of analytic placement (Kraftwerk)."],
        ["Analytic - quadratic", "Minimise sum w * (squared distance); the "
         "optimum solves a sparse linear system A x = b. Iterate with "
         "spreading anchors (FastPlace, SimPL).", "Fast global placement; "
         "initial placement in many commercial tools."],
        ["Analytic - nonlinear", "Smooth approximations of HPWL "
         "(log-sum-exp, weighted-average) plus a density penalty, "
         "minimised with gradient methods (NTUplace, APlace).", "Modern "
         "global placers."],
        ["Electrostatic (ePlace)", "Cells are positive charges; density "
         "overflow is the electric potential energy, solved by FFT on a "
         "grid (Poisson's equation); Nesterov gradient descent.",
         "ePlace/RePlAce - the global placer in OpenROAD; similar ideas in "
         "commercial engines."],
    ], widths=[1.4, 3.2, 2.4], caption="Placement algorithm families")

    h3("Quadratic placement in one paragraph")
    p("Replace HPWL by squared Euclidean distance and model every k-pin net "
      "as a **clique** of edges with weight 1/(k-1). The cost "
      "sum w_ij [(x_i - x_j)^{2} + (y_i - y_j)^{2}] separates into x and y, "
      "and each is a convex quadratic whose minimum is where the gradient is "
      "zero: A x = b_{x}, A y = b_{y}. A is a symmetric positive-definite "
      "Laplacian-like matrix (diagonal = total weight of edges at a cell, "
      "off-diagonal = minus the weight between two movable cells), and b "
      "collects the pull of fixed pins (I/O pads, macro pins). With no fixed "
      "pins A would be singular and all cells would collapse to one point - "
      "which is why I/O placement and macro placement (Chapter 14) must come "
      "first. Real solvers use conjugate gradient on millions of unknowns and "
      "replace the clique by the **Bound2Bound** net model, which reproduces "
      "HPWL much better for large nets.")
    p("The script below does exactly this for a six-cell netlist with four "
      "fixed pads, then runs a greedy legaliser that snaps cells to 10-um "
      "rows and 5-um sites without overlap. It prints the matrix, the "
      "positions and HPWL for a random placement, the quadratic optimum and "
      "the legal result.")
    code(_SRC_QPLACE, caption="qplace.py - quadratic placement plus a greedy "
                              "row legaliser (numpy)")
    out(_OUT_QPLACE, caption="Real output of python3 qplace.py")
    p("Three lessons show up even at this toy scale. First, the analytic "
      "optimum cuts HPWL by roughly 3x versus random placement, and cells "
      "are pulled toward the pads they connect to (u1 toward IN0, u6 toward "
      "OUT). Second, the quadratic solution is **not legal**: u4 and u5 sit "
      "2.4 um apart although each is 10 um wide. Third, legalisation costs "
      "wirelength (277 -> 290 um, about +5%); in a real design with "
      "millions of cells piled into the middle of the die, naive "
      "legalisation of an unspread solution would be catastrophic, which is "
      "why global placement must spread cells first.")
    box("intuit", "Why squared length still works",
        "Squared distance over-penalises long nets and under-penalises short "
        "ones, so a pure quadratic placement clusters cells. Placers fix "
        "this by re-weighting each edge by 1/(current length) in successive "
        "solves (making the quadratic mimic linear length) and by adding "
        "pseudo-nets that anchor each cell to a spread-out target position "
        "(SimPL's 'lower bound / upper bound' iteration).")

    # ------------------------------------------------------------------
    h2("The placement flow: global, legalisation, detailed")
    diagram([
        "  floorplanned DB + netlist + SDC + libs",
        "            |",
        "            v",
        "  +-----------------------+   coarse, overlapping positions; density-driven",
        "  | 1. global placement   |   spreading; timing/congestion weights on nets",
        "  +-----------------------+",
        "            |     (interleaved with early optimisation: buffer long nets,",
        "            v      remove unneeded buffers from synthesis, resize drivers)",
        "  +-----------------------+   snap to rows/sites, remove overlaps,",
        "  | 2. legalisation       |   honour blockages, fences, voltage areas,",
        "  +-----------------------+   cell-edge/spacing and pin-access rules",
        "            |",
        "            v",
        "  +-----------------------+   local swaps, flips, sliding windows,",
        "  | 3. detailed placement |   small-window optimal reordering",
        "  +-----------------------+",
        "            |",
        "            v",
        "  +-----------------------+   sizing, buffering, Vt swap, pin swap,",
        "  | 4. pre-CTS optimise   |   cloning, restructuring (ideal clocks)",
        "  +-----------------------+",
        "            |",
        "            v   scan reorder, spare cells, tie cells, timing/congestion gate -> CTS",
    ], caption="The placement stage inside a block implementation flow")
    h3("Global placement")
    p("Global placement finds approximate positions that minimise weighted "
      "wirelength subject to a **density constraint**: in every bin of a grid "
      "laid over the core, the total cell area must not exceed a target "
      "density (for example 0.6-0.8 of available area). Modern engines start "
      "with all cells clustered in the centre and iterate: each iteration "
      "reduces wirelength and increases a penalty on density overflow, so "
      "the design 'inflates' outward until overflow falls below a threshold "
      "(OpenROAD's RePlAce stops by default at about 10% overflow). Timing "
      "and congestion are fed back during this process, not only after it.")
    h3("Legalisation")
    p("Legalisation moves each cell the smallest possible distance to a "
      "legal location: on a row, aligned to the placement site grid, "
      "correctly oriented (alternate rows are flipped so VDD/VSS rails are "
      "shared), not overlapping, outside hard blockages, inside its fence or "
      "voltage area, and respecting advanced-node rules such as cell-edge "
      "spacing, implant/Vt-layer minimum width (neighbouring cells of "
      "different Vt may need filler or a minimum run), drain-sharing "
      "restrictions and pin-access constraints. Classic algorithms are "
      "Tetris (greedy, left to right) and Abacus (dynamic programming per "
      "row minimising squared displacement). Large displacement is a warning "
      "sign: it means global placement produced regions that were too dense.")
    h3("Detailed placement")
    p("Detailed placement improves a legal placement with local moves that "
      "keep it legal: swapping two cells, sliding a cell along its row, "
      "flipping a cell to bring its pin closer to the connected net, and "
      "exhaustively reordering small windows of 3-4 adjacent cells. It "
      "typically recovers a few percent of wirelength and repairs the damage "
      "done by legalisation and by optimisation (which inserts and resizes "
      "cells and then needs a local re-legalise). Simulated annealing is "
      "still competitive here because the move set is small and local.")

    # ------------------------------------------------------------------
    h2("Timing-driven and congestion-driven placement")
    p("A wirelength-optimal placement is often timing-poor: one long net on "
      "a critical path matters far more than a hundred short nets on slack-"
      "rich paths. **Timing-driven placement** runs a fast internal STA "
      "(with a virtual-route or Steiner-tree wire model and ideal clocks) "
      "between placement iterations, computes slack per net, and raises the "
      "weight of nets on critical paths (net weighting), or adds explicit "
      "path-length constraints. Typical net weight: w = 1 + alpha * "
      "(criticality)^{beta}, where criticality = 1 - slack/WNS_{ref}. "
      "The side effect is a trade: critical logic is pulled together, "
      "raising local density and possibly congestion.")
    p("**Congestion-driven placement** does the opposite type of trade. The "
      "tool runs a fast global route (or a probabilistic estimate such as "
      "RUDY - rectangular uniform wire density) to find regions where "
      "routing demand exceeds supply, then inflates the cells in those "
      "regions (**cell padding / inflation**) so they spread, or lowers the "
      "target density locally. Congestion is typically caused by:")
    bul([
        "**High-pin-density cells** clustered together (large AOI/OAI, "
        "multi-bit flops, wide muxes) - more pins per unit area than the "
        "local metal tracks can reach (pin-access congestion).",
        "**Macro corners and channels** - narrow channels between memories "
        "where many nets must squeeze through; always check the corners of "
        "large macros.",
        "**Logic structures with inherent global connectivity** - crossbars, "
        "large muxes, barrel shifters, FFT butterflies, wide AXI "
        "interconnects. These are an architecture/RTL problem (Chapter 6), "
        "not something the placer can fully fix.",
        "**Too high utilisation** - above roughly 70-80% cell utilisation "
        "in logic-dense blocks, routing typically fails at advanced nodes; "
        "the exact number depends on cell library track height and metal "
        "stack.",
    ])
    h3("Measuring congestion: GRC overflow")
    p("The global router divides the die into a grid of **global routing "
      "cells (GRCs, gcells)**, typically a few standard-cell rows high. "
      "For every gcell edge and every layer it knows the capacity (number "
      "of free tracks after blockages and pre-routes such as the power "
      "grid) and the demand (number of nets that the global route sends "
      "through). **Overflow = demand - capacity** when positive. Reports "
      "list total overflow, the worst overflow and the percentage of "
      "overflowing gcells per layer and direction, and a congestion map "
      "colours hot spots.")
    diagram([
        "   congestion map (H/V overflow per gcell, '.'=ok  '1'..'9'=tracks over capacity)",
        "",
        "      +--------------------------------------------------+",
        "      | . . . . . . . . . . . . . . . . . . . . . . . . . |",
        "      | . . . . . . . . 1 2 1 . . . . . . . . . . . . . . |",
        "      | . . +--------+ 2 4 3 1 . . . . . +----------+ . . |",
        "      | . . |  SRAM  | 3 6 5 2 . . . . . |   SRAM   | . . |",
        "      | . . |  macro | 2 5 4 1 . . . . . |   macro  | . . |",
        "      | . . +--------+ 1 2 1 . . . . . . +----------+ . . |",
        "      | . . . . . . . . . . . . . . 1 1 . . . . . . . . . |",
        "      +--------------------------------------------------+",
        "            hot spot in the channel beside the left macro -> add a partial",
        "            placement blockage, widen the channel, or move pins on the macro",
    ], caption="Reading a congestion map (schematic)")
    tbl(["Metric", "Typically acceptable after placement", "Action if worse"], [
        ["Total GRC overflow (both directions)", "well below 1% of gcells; "
         "no hot spots > 2-3 tracks", "cell padding, lower density, "
         "partial blockages, fix floorplan"],
        ["Pin density (pins/um^{2})", "within library/tool guideline",
         "spread high-pin cells, avoid big multi-bit cells in hot spots"],
        ["Cell utilisation (whole block)", "roughly 60-75% at advanced "
         "nodes (higher at mature nodes)", "grow block, remove redundant "
         "logic, move logic out"],
        ["Local density per bin", "no bins > ~90-95%", "density screens, "
         "tighter max-density setting"],
    ], widths=[2.2, 2.6, 2.4], caption="Congestion targets (rules of thumb; "
                                       "every team calibrates its own)")
    box("warn", "PITFALL - Congestion that shows up only after routing",
        "A placement with clean global-route overflow can still fail "
        "detailed routing because the estimate ignores pin access, via "
        "rules and double-patterning colouring. If the detailed router "
        "leaves thousands of DRCs in one region, go back to placement: "
        "pad the cells in that region and re-place, rather than trying to "
        "fix it in routing.")

    # ------------------------------------------------------------------
    h2("Pre-CTS optimisation")
    p("Once cells have positions, wire parasitics can be estimated and STA "
      "becomes meaningful. **Pre-CTS optimisation** (place_opt, "
      "repair_design/repair_timing in OpenROAD) fixes design-rule violations "
      "and setup timing with **ideal clocks** (zero skew, specified latency "
      "and uncertainty from the SDC). Hold is usually not fixed yet because "
      "real clock skew does not exist before CTS. The optimisation loop "
      "applies a menu of transforms, cheapest first:")
    tbl(["Transform", "What it does", "Cost / side effects"], [
        ["Gate sizing", "Swap a cell for a stronger (or weaker) drive "
         "strength of the same function (NAND2_X1 -> NAND2_X4).",
         "More area, more input cap (slows the previous stage), more "
         "leakage. Downsizing on non-critical paths recovers power."],
        ["Buffering / repeater insertion", "Split long or high-fanout nets "
         "with buffers or inverter pairs; isolate critical sinks from "
         "non-critical load.", "Area, power; must be placed legally; "
         "long nets need buffers at regular spacing (Chapter 2 wire "
         "delay grows with L^{2} unbuffered)."],
        ["Vt swap", "Replace an HVT/SVT cell by LVT/ULVT on a critical "
         "path, or LVT by HVT where slack allows.", "Leakage rises "
         "roughly 3-10x per Vt step; same footprint, so no re-placement. "
         "Often capped by an LVT percentage budget."],
        ["Pin swap", "Connect the latest-arriving signal to the fastest "
         "input pin of a cell with logically equivalent pins (e.g. the pin "
         "nearest the output in a NAND stack).", "Free - no area; limited "
         "gain."],
        ["Cloning (replication)", "Duplicate a driver so each copy drives "
         "part of the fanout, placed near its sinks.", "Area; breaks "
         "equivalence checking only if not recorded - tools keep it "
         "verifiable."],
        ["Logic restructuring", "Re-synthesise small cones (collapse, "
         "re-decompose, move late signals closer to the output).",
         "Tool-dependent; may need LEC care."],
        ["Useful movement", "Pull cells on critical paths closer together "
         "(incremental timing-driven placement).", "Local density."],
    ], widths=[1.4, 3.0, 2.6], caption="The pre-CTS optimisation toolbox")
    p("DRV (design-rule violation) fixing - max transition, max "
      "capacitance, max fanout from Liberty and SDC - comes before setup "
      "fixing, because a net with a 2 ns slew makes every timing number "
      "downstream meaningless. A useful order is: fix DRVs -> fix setup "
      "(WNS first, then TNS) -> recover area and leakage on slack-rich paths "
      "-> re-legalise -> incremental detailed placement.")
    code([
        "# OpenROAD-style placement script (commands exist in OpenROAD; values are examples)",
        "global_placement -density 0.65 -timing_driven -routability_driven",
        "estimate_parasitics -placement          ;# Steiner-tree RC from layer R/C",
        "repair_design                           ;# max slew/cap/fanout, long wires",
        "detailed_placement",
        "repair_timing -setup                    ;# sizing, buffering, Vt swap, cloning",
        "detailed_placement",
        "check_placement -verbose",
        "report_design_area",
        "report_checks -path_delay max -group_path_count 5",
        "report_tns ; report_wns",
    ], caption="A minimal open-source placement + optimisation sequence "
               "(OpenROAD commands; not run here - OpenROAD is covered in "
               "Chapter 24)")
    box("expert", "Interview insight - why not fix hold before CTS?",
        "Hold slack depends on the actual clock skew between launch and "
        "capture flops, which is only known after CTS. Fixing hold with "
        "ideal clocks inserts delay cells that may be unnecessary (wasting "
        "area and hurting setup) or insufficient. The exception is paths "
        "whose hold problem is independent of skew, such as scan shift "
        "paths between flops in the same leaf cluster with zero logic - "
        "some teams add a small hold margin there early.")
    box("warn", "PITFALL - Over-optimistic pre-CTS timing",
        "Ideal-clock timing uses the SDC set_clock_uncertainty to stand in "
        "for skew and jitter. If the pre-CTS uncertainty is smaller than "
        "the skew CTS will actually produce, setup looks clean after "
        "placement and collapses after CTS. Typical practice: pre-CTS "
        "uncertainty = expected skew + jitter + margin; post-CTS reduce it "
        "to jitter + margin because real skew is now computed.")

    # ------------------------------------------------------------------
    h2("Scan-chain reordering")
    p("Synthesis stitches scan chains (Chapter 10) in an order that knows "
      "nothing about placement - often alphabetical or by hierarchy - so the "
      "scan-in -> scan-out connections criss-cross the die. After placement "
      "the tool **reorders** each chain so consecutive flops are physically "
      "adjacent, cutting scan wirelength (and congestion) dramatically. The "
      "order is described by the **scan DEF** that DFT insertion writes: it "
      "defines each chain, its start and stop points, and which segments "
      "are **ordered** (must not change, e.g. a lockup latch pair or a "
      "shift register) versus **floating** (freely reorderable).")
    bul([
        "Reordering is allowed only within a chain and only across flops "
        "in the same clock domain/edge, unless the tool inserts lockup "
        "latches; flops of different power domains need isolation-aware "
        "handling.",
        "Chain lengths may be rebalanced between chains of the same "
        "compression group if the DFT engineer allows it; the ATPG "
        "patterns must then be regenerated from the final netlist.",
        "The hand-off back to DFT is the updated scan DEF plus the final "
        "netlist; ATPG is run on the post-layout netlist, not the "
        "synthesis one.",
        "Short scan paths between adjacent flops create hold problems after "
        "CTS - expect hold buffers on scan paths.",
    ])

    # ------------------------------------------------------------------
    h2("Spare cells, tie cells and density screens")
    h3("Spare cells")
    p("A **spare cell** is an unconnected gate (NAND, NOR, inverter, "
      "flip-flop, mux, sometimes a small cluster called a spare module) "
      "placed throughout the design with inputs tied off. If a bug is found "
      "after the base layers are fabricated, a **metal-only ECO** "
      "(Chapter 19) can rewire spare cells using only upper metal and via "
      "masks - far cheaper and faster than a full respin. Typical practice "
      "is to reserve a few percent of cell area (often 1-5%) and scatter "
      "spare clusters uniformly so every region has one within reach. An "
      "alternative is **ECO gate-array filler cells**: programmable base "
      "cells placed as fillers that can be turned into logic by metal "
      "changes.")
    h3("Tie cells")
    p("Inputs that must be constant are not connected directly to the "
      "VDD/VSS rails; they go through **TIEHI/TIELO cells**, which protect "
      "the gate oxide from ESD events on the supply and make the constant "
      "visible to LVS and ECO. Tie cells are inserted after placement and "
      "should be spread, with a maximum fanout per tie cell.")
    h3("Density screens and blockages")
    tbl(["Construct", "Effect", "Typical use"], [
        ["Hard placement blockage", "No standard cells at all",
         "Under macro halos, around analog blocks, channels reserved for "
         "routing"],
        ["Soft blockage", "No cells during global placement; buffers "
         "allowed by optimisation", "Narrow channels between macros"],
        ["Partial blockage (density screen)", "Limit cell density in a "
         "region to e.g. 40-60%", "Around congestion hot spots, near "
         "macro pins, high-pin-density logic"],
        ["Keep-out margin (halo)", "No cells within a distance of a macro "
         "or cell", "Macro edges, to leave room for pin access and "
         "reduce proximity effects"],
        ["Fence / region / bound", "Constrain listed cells into (fence: "
         "exclusively) or near an area", "Voltage areas, clustering of "
         "timing-critical groups, partition preparation"],
    ], widths=[1.8, 2.4, 2.8], caption="Placement constraints available in "
                                       "every commercial and open-source placer")

    # ------------------------------------------------------------------
    h2("Placement quality metrics and the go/no-go for CTS")
    p("Before moving on, the team reviews a fixed set of metrics. It is "
      "common to automate these into a 'QoR dashboard' compared run over "
      "run, because a regression (e.g. +3% wirelength after an innocent "
      "netlist drop) is much easier to diagnose early.")
    checklist("Post-placement review", [
        "All cells legally placed (check_placement / verify placement "
        "shows 0 overlaps, 0 off-site cells, 0 cells in blockages).",
        "Setup WNS/TNS with ideal clocks within the agreed pre-CTS "
        "budget (e.g. WNS >= -5% of the period, to be closed later); "
        "no max-transition/max-capacitance violations.",
        "Global-route overflow below threshold; congestion map reviewed "
        "around macros and channels.",
        "Utilisation and per-bin density within target; buffer and "
        "inverter count reasonable (a sudden jump means a timing or "
        "constraint problem, not a placement problem).",
        "HPWL and estimated total wirelength trended against previous "
        "runs.",
        "Leakage / Vt mix within budget (LVT %).",
        "Scan chains reordered; scan DEF written; spare and tie cells "
        "inserted.",
        "Multi-voltage checks: cells inside correct voltage areas, level "
        "shifters and isolation cells placed at domain boundaries.",
    ])
    box("tip", "What experienced PD engineers look at first",
        "Not the WNS number but the **shape** of the failing paths: are they "
        "long wires between distant macros (floorplan problem), deep logic "
        "(RTL/synthesis problem), high-fanout nets (constraint or buffering "
        "problem), or paths through congested regions (detours)? Each "
        "category has a different owner and fix.")

    h2("Summary")
    bul([
        "Placement assigns legal row/site locations to every standard "
        "cell; it minimises weighted HPWL subject to density, then "
        "timing, congestion and power.",
        "Global placement (analytic: quadratic or electrostatic/ePlace) "
        "gives spread, overlapping positions; legalisation snaps them to "
        "rows and sites; detailed placement polishes locally.",
        "The quadratic formulation reduces to solving A x = b; fixed pins "
        "(I/O, macros) make it well-posed. Our 6-cell run cut HPWL from "
        "801 um (random) to 277 um, and legalisation added ~5%.",
        "Timing-driven placement weights critical nets; congestion-driven "
        "placement pads cells in hot spots measured by GRC overflow.",
        "Pre-CTS optimisation (ideal clocks) fixes DRVs then setup via "
        "sizing, buffering, Vt swap, pin swap, cloning and restructuring; "
        "hold waits for CTS.",
        "Scan chains are reordered using the scan DEF; spare cells and "
        "tie cells are added; density screens, halos and fences steer the "
        "placer.",
    ])
    h2("Exercises")
    bul([
        "Compute the HPWL of a 4-pin net with pins at (0,0), (30,10), "
        "(12,40) and (25,25). What is the rectilinear Steiner length, and "
        "why is HPWL a lower bound?",
        "Modify qplace.py to remove all pads. Why does np.linalg.solve fail, "
        "and what does this say about floorplanning before placement?",
        "A block at 82% utilisation shows 4% GRC overflow concentrated "
        "between two SRAMs. List four fixes in order of cost and name the "
        "owner of each.",
        "Explain why a Vt swap is preferred to upsizing late in the flow, "
        "and give one case where upsizing is the only option.",
        "Why must scan-chain reordering respect clock domains and edges? "
        "What cell fixes a chain that crosses from a negative-edge to a "
        "positive-edge flop?",
        "Your pre-CTS WNS is +20 ps with 150 ps clock uncertainty. CTS "
        "achieves 60 ps skew and jitter is 30 ps. Estimate post-CTS WNS "
        "if you reduce uncertainty to jitter + 20 ps margin and skew "
        "happens to be fully against you on the critical path.",
    ], ordered=True)

# =============================================================================
#           CHAPTER 16 - CLOCK TREE SYNTHESIS AND CLOCK DISTRIBUTION
# =============================================================================
def _ch16():
    chapter("Clock Tree Synthesis and Clock Distribution")
    p("Up to placement, every clock in the design was **ideal**: the SDC "
      "said `create_clock -period 1.0 [get_ports clk]` and STA assumed the "
      "edge arrived at every flip-flop at the same instant (plus the "
      "uncertainty you declared). In silicon, one clock pin on the "
      "boundary must drive tens of thousands to millions of flop clock pins "
      "spread over square millimetres. **Clock tree synthesis (CTS)** builds "
      "the network of buffers, inverters, clock gates and wires that "
      "delivers the edge to every sink with controlled timing - and after "
      "CTS, STA switches to **propagated clocks** and the real skew becomes "
      "part of every path's slack.")
    p("The clock network is special in three ways. It switches every cycle "
      "(activity 1, or 2 transitions per cycle), so it is the single biggest "
      "consumer of dynamic power in most synchronous designs. It touches "
      "every sequential path, so its errors appear everywhere. And it is "
      "the reference for all timing, so its variability (OCV, jitter, "
      "crosstalk, IR drop) reduces the usable cycle time of the entire chip.")

    h2("Clock tree goals and the vocabulary")
    diagram([
        "                    source latency           network (insertion) latency",
        "   PLL/osc ----------------------> clk port ------+----------------> FF1/CK",
        "   (off-block)                                    |    t1 = 410 ps",
        "                                                  +----------------> FF2/CK",
        "                                                       t2 = 455 ps",
        "",
        "   latency (FF)   = source latency + network latency to that sink",
        "   global skew    = max(t_i) - min(t_i) over all sinks of the clock   = 45 ps",
        "   local skew     = t_capture - t_launch for a pair of flops that share a path",
        "   transition     = clock slew at each sink (e.g. <= 60-100 ps at advanced nodes)",
    ], caption="Latency and skew")
    tbl(["Goal", "Why", "Typical target (illustrative)"], [
        ["Low skew", "Skew is subtracted from setup slack (if capture "
         "is earlier) or hold slack (if capture is later).", "tens of ps "
         "for a block at GHz rates; a few % of the period"],
        ["Low / bounded latency", "Latency adds OCV-derated delay on "
         "the uncommon clock path, and must match between blocks that "
         "talk to each other.", "a few hundred ps inside a block"],
        ["Sharp, bounded transition", "Slow clock edges increase "
         "flop clk->Q and setup time, raise short-circuit power and "
         "sensitivity to noise.", "max clock transition set by the "
         "library/SDC; usually tighter than for data"],
        ["Low power", "Clock net + buffers + flop clock pins switch "
         "every cycle.", "minimise buffer count, wire cap; gate as close to "
         "the root as possible"],
        ["Robustness", "Tolerate OCV, jitter, IR drop, crosstalk, EM on "
         "high-activity nets.", "NDRs, shielding, balanced cell types"],
    ], widths=[1.4, 3.2, 2.4], caption="What CTS optimises")
    box("key", "Skew is only bad when it hurts a path",
        "Global skew between two flops that never exchange data is "
        "irrelevant to timing. What matters is **local skew on real "
        "timing paths**: setup slack = T - (data arrival) + (capture clock "
        "latency - launch clock latency) - setup - uncertainty. Positive "
        "skew (capture clock later) helps setup and hurts hold; negative "
        "skew does the opposite. Modern CTS therefore optimises skew per "
        "path group, not one global number.")

    h2("Clock tree structures")
    diagram([
        "   H-tree (symmetric)            fishbone / spine              clock mesh (grid)",
        "",
        "   +--+     +--+                  | | | | | | |           +--+--+--+--+--+",
        "   |  +--+--+  |                --+-+-+-+-+-+-+-- spine    |  |  |  |  |  |",
        "   +--+  |  +--+                  | | | | | | |           +--+--+--+--+--+",
        "         |                        ribs to local            |  |  |  |  |  |",
        "   +--+  |  +--+                  buffers/sinks           +--+--+--+--+--+",
        "   |  +--+--+  |                                          ^  ^  ^  ^  ^  ^",
        "   +--+  |  +--+                                     many drivers shorted by the mesh",
        "        root",
    ], caption="Canonical clock distribution topologies")
    tbl(["Structure", "Strengths", "Weaknesses", "Typical use"], [
        ["Conventional CTS (balanced buffered tree)", "Automatic, low "
         "power, flexible with irregular sink placement", "Skew and OCV grow "
         "with depth; common path short", "Most ASIC blocks"],
        ["H-tree", "Equal path length by construction -> near-zero nominal "
         "skew; long common path", "Needs regular sink distribution; wastes "
         "wire where sinks are sparse", "Top levels of trees; regular arrays"],
        ["Spine / fishbone", "Simple, low latency from a central trunk",
         "Skew grows along the spine unless driven from the centre",
         "Datapaths, bit-sliced structures"],
        ["Clock mesh", "Very low skew, insensitive to OCV and load changes "
         "(mesh shorts out variation)", "High power (short-circuit "
         "currents between drivers), needs SPICE-level analysis, hard to "
         "gate", "High-performance CPUs, GHz cores"],
        ["Multi-source CTS (MSCTS) / structured", "H-tree or mesh at top "
         "driving many tap points, then conventional local trees", "More "
         "setup effort; tap planning", "Large high-speed blocks; the "
         "modern middle ground"],
    ], widths=[1.7, 2.1, 2.1, 1.6], caption="Choosing a clock structure")

    h3("Elmore model of an H-tree versus an unbalanced tree")
    p("The Elmore delay (Chapter 2) of an RC tree is the sum, along the path "
      "from the root to a sink, of each segment resistance times all the "
      "capacitance downstream of it. It is an upper bound on the 50% delay "
      "for a step input and ranks tree topologies correctly, which is all "
      "we need. The script builds three unbuffered trees over the same 16 "
      "sinks on a 4x4 grid in a 1 mm x 1 mm block (upper-metal wire of "
      "0.1 ohm/um and 0.2 fF/um, a 50-ohm driver and 5 fF per sink "
      "cluster) and reports latency and skew.")
    eq(["T_Elmore(sink) = R_drv * C_total + sum over segments k on the root->sink path of",
        "                 R_k * ( C_k / 2  +  C_downstream(k) )",
        "",
        "skew = max over sinks T  -  min over sinks T"],
       caption="Elmore delay with a pi-model per wire segment")
    code(_SRC_CTREE, caption="ctree.py - Elmore latency and skew for three "
                             "clock topologies")
    out(_OUT_CTREE, caption="Real output of python3 ctree.py")
    p("The H-tree is perfectly balanced (0.0 ps skew) because every "
      "root-to-sink path has identical length and identical downstream "
      "load, but it uses 23% more wire (6000 vs 4875 um) and therefore more "
      "capacitance and power. The edge-driven fishbone has 40 ps of skew, "
      "almost entirely along the trunk: the last column sees all the trunk "
      "resistance. Driving the same comb from the centre cuts skew to 8 ps "
      "and even gives the lowest latency. Real CTS engines combine these "
      "ideas: a balanced structure at the top, then clustering of nearby "
      "sinks, buffer insertion to control slew, and **wire snaking** or "
      "buffer sizing to add delay on early branches.")
    box("note", "What this toy model leaves out",
        "A real clock tree is buffered every few hundred um (an unbuffered "
        "1 mm net would violate transition limits at advanced nodes), sink "
        "caps are unequal, and buffer delays vary with OCV. With buffers, "
        "skew comes mainly from unequal buffer stages and loads rather than "
        "from wire RC, and CTS balances by sizing buffers and adjusting the "
        "number of stages per branch.")

    h2("The CTS flow")
    diagram([
        "   placed DB  +  SDC clocks  +  CTS spec (targets, cells, NDRs, exceptions)",
        "        |",
        "        v",
        "   1. clock tracing: find sinks, stop/ignore/exclude pins, generated clocks, muxes",
        "   2. clustering: group nearby sinks, respecting clock gates and max fanout",
        "   3. tree building: insert clock buffers/inverters level by level (bottom-up",
        "      or top-down), route clock nets early with NDRs (clock pre-route)",
        "   4. balancing: skew groups, latency targets, snaking, sizing",
        "   5. clock-aware optimisation: useful skew (CCOpt), clock gate cloning/merging",
        "   6. switch STA to propagated clocks; update uncertainty; fix setup/hold",
        "        |",
        "        v",
        "   post-CTS DB -> routing (Chapter 17)",
    ], caption="Clock tree synthesis steps")
    h3("Clock specifications")
    p("CTS is driven by the SDC clocks plus a tool-specific specification: "
      "target skew, maximum transition (often a separate, tighter value for "
      "the clock), maximum fanout, target latency, the list of allowed "
      "buffers and inverters, the routing rules for clock nets, and "
      "exceptions. Important exceptions are **sink/stop pins** (treat as a "
      "leaf and balance to it), **ignore/exclude pins** (drive but do not "
      "balance, e.g. a clock going to a data pin of a flop for a divider "
      "check), and **float pins with pre-defined insertion delay** for hard "
      "macros whose internal clock tree already has latency (an SRAM or a "
      "hardened sub-block).")
    code([
        "# Illustrative CTS setup in generic Tcl (names differ by tool; values are examples)",
        "set_ccopt_property target_skew             0.030   ;# ns",
        "set_ccopt_property target_max_trans        0.060",
        "set_ccopt_property buffer_cells   {CKBUF_X4 CKBUF_X8 CKBUF_X16}",
        "set_ccopt_property inverter_cells {CKINV_X4 CKINV_X8 CKINV_X16}",
        "set_ccopt_property clock_gating_cells {ICG_X2 ICG_X4}",
        "# double-width, double-spacing rule on M5-M8 for trunk and leaf nets",
        "create_route_rule -name CLK_2W2S -width_multiplier 2 -spacing_multiplier 2",
        "create_route_type -name clk_trunk -route_rule CLK_2W2S -top M8 -bottom M5 \\",
        "                  -shield_net VSS",
        "set_ccopt_property route_type clk_trunk -net_type trunk",
        "# SRAM macro has 180 ps internal clock latency: balance to its CK pin minus that",
        "set_ccopt_property insertion_delay 0.180 -pin u_sram0/CLK",
    ], caption="A CTS specification (illustrative; property names modelled on "
               "Innovus CCOpt, not from a real run)")
    h3("Non-default routing rules (NDRs) and shielding")
    p("Clock nets are routed with **non-default rules**: double width "
      "lowers resistance (and EM current density), double spacing lowers "
      "coupling capacitance to neighbours and thus crosstalk-induced delay "
      "change. **Shielding** places VSS (or VDD) wires on both sides of a "
      "clock trunk so its neighbours are quiet by construction. Both cost "
      "routing tracks, so a common compromise is 2W2S plus shielding on "
      "trunks (few long nets, high impact) and default width with double "
      "spacing, or no NDR, on leaf nets (many short nets near the flops).")
    h3("Clock buffers versus clock inverters")
    p("Libraries provide dedicated clock cells (CKBUF, CKINV) with balanced "
      "rise/fall delays and strong, symmetric drive. Inverter-based trees "
      "use fewer transistors per stage and have lower latency and power "
      "than buffer trees; alternating polarities also help keep **duty "
      "cycle** intact, because a rise/fall delay imbalance in one stage is "
      "partly cancelled by the next. Inverter trees must have an even "
      "number of stages to each sink (or the tool must track polarity).")
    h3("Useful skew and concurrent clock/data optimisation")
    p("Zero skew is not optimal. If flop B has a critical input path and a "
      "slack-rich output path, delaying B's clock borrows time from the "
      "next stage: this is **useful skew**. Concurrent clock and data "
      "optimisation (CCOpt in Innovus, CCD in Fusion Compiler) builds the "
      "tree with per-sink latency targets computed from the slack of the "
      "paths entering and leaving each flop, optimising data-path sizing "
      "at the same time. It routinely recovers a few percent of frequency "
      "but must be constrained so hold does not explode and so it does not "
      "consume margin that sign-off OCV needs.")
    eq(["setup slack(A->B) = T + (L_B - L_A) - t_cq - t_logic - t_setup - uncertainty",
        "hold  slack(A->B) = t_cq + t_logic_min - t_hold - (L_B - L_A) - uncertainty_hold",
        "",
        "Raising L_B by d:  setup slack(A->B) += d   hold slack(A->B) -= d",
        "                   setup slack(B->C) -= d   hold slack(B->C) += d"],
       caption="Useful skew moves slack between adjacent stages (L = clock latency)")

    h2("Clock gating inside the tree")
    p("Integrated clock-gating cells (ICGs, Chapter 11) sit **in** the clock "
      "tree: the ICG's clock input is a node of the tree and its gated "
      "output drives a sub-tree. CTS has to balance the whole thing so "
      "sinks behind a gate have the same latency as ungated sinks. Tools "
      "clone ICGs with high fanout (so each copy drives a local cluster) "
      "and merge ICGs with identical enables, and they place ICGs close to "
      "the root of their sub-tree so the gated portion - where power is "
      "saved - is as large as possible.")
    p("The ICG enable has a real setup check against the clock at the ICG "
      "(the **clock-gating check**, inferred automatically by STA for "
      "known ICG cells). Because the ICG is earlier in the tree than the "
      "flops that generate the enable, the enable path sees a **negative "
      "skew**: the ICG clock arrives before the flop clocks. Placing ICGs "
      "too close to the root makes this check fail; too close to the "
      "leaves wastes power. Tools trade this automatically, but it is a "
      "classic place for late surprises.")
    box("warn", "PITFALL - Clock gating check after CTS",
        "Enable paths to ICGs often pass with ideal clocks and fail after "
        "CTS because the ICG's clock latency is, say, 250 ps smaller than "
        "the launching flop's. Budget for it pre-CTS (set_clock_gating_check "
        "margins or tighter constraints on enable logic) and keep enable "
        "logic shallow.")

    h2("OCV, CPPR, jitter and duty cycle")
    h3("On-chip variation on clock paths")
    p("Sign-off STA (Chapter 9) applies on-chip variation: for setup, the "
      "launch clock path and data path are computed late and the capture "
      "clock path early; for hold the opposite. With AOCV/POCV (Chapter 18) "
      "the derate depends on depth and distance, but the effect is the "
      "same: **every picosecond of clock latency not shared between launch "
      "and capture adds pessimism**. A 400 ps latency with a 5% derate "
      "difference costs up to about 20 ps of slack. This is why low "
      "latency and a long common path matter as much as low skew.")
    h3("Common path pessimism removal (CPPR / CRPR)")
    p("The part of the clock tree shared by launch and capture cannot be "
      "simultaneously fast and slow, yet OCV analysis derates it both ways. "
      "STA removes this double-count with **clock reconvergence pessimism "
      "removal (CRPR)**, also called CPPR: the difference between late and "
      "early arrival at the last common node is added back to the slack.")
    diagram([
        "            common path (derated late for launch AND early for capture)",
        "  clk --[B1]--[B2]--+--[B3]--[B4]--> FF_launch/CK    late  : 0.52 ns",
        "                    |",
        "                    +--[B5]--[B6]--> FF_capture/CK   early : 0.44 ns",
        "",
        "  at the common node (after B2): late arrival 0.26, early arrival 0.22",
        "  CPPR credit = 0.26 - 0.22 = 0.04 ns added back to setup slack",
    ], caption="CPPR in a picture (numbers illustrative)")
    h3("Jitter and duty-cycle distortion")
    p("**Jitter** is the time variation of the clock edge from its ideal "
      "position, generated by the PLL (reference noise, VCO phase noise) "
      "and added by the distribution (supply noise modulating buffer "
      "delay). **Cycle-to-cycle** and **period jitter** matter for setup "
      "between successive edges; they enter STA through "
      "set_clock_uncertainty. **Duty-cycle distortion** comes from unequal "
      "rise/fall delays accumulating along the tree; it matters for "
      "half-cycle paths (posedge to negedge), DDR interfaces and anything "
      "that uses both edges. Clock inverter trees and duty-cycle correctors "
      "control it; STA models it with set_clock_latency -rise/-fall or "
      "explicit half-period uncertainty.")
    eq(["post-CTS setup uncertainty  ~= PLL jitter (period) + supply-noise jitter + margin",
        "pre-CTS  setup uncertainty  ~= the above + expected skew",
        "hold uncertainty             ~= margin (+ skew pre-CTS); same-edge jitter cancels"],
       caption="How uncertainty is budgeted before and after CTS (typical practice)")

    h2("Generated clocks, clock muxes and multiple clocks")
    p("Clock dividers (`create_generated_clock -divide_by 2 -source ...`) "
      "and clock multiplexers complicate CTS. The generated clock's sinks "
      "must be balanced **through** the divider flop so that data paths "
      "between the master and divided domain see sensible skew; the CTS "
      "tool must therefore trace through the divider's clock pin to its "
      "output. For a **clock mux** (functional clock vs test clock, or two "
      "PLL outputs), the tree after the mux is shared, and the tool must "
      "balance each clock through the mux while not balancing clocks that "
      "are never active together (logically/physically exclusive clock "
      "groups in the SDC). Scan test clocks share the functional tree in "
      "most designs; the test-mode skew targets may be looser, because "
      "shift is slow, but hold must be met in both modes.")
    box("expert", "Interview insight - balancing across domains",
        "If clocks A and B are asynchronous, balancing their latencies to "
        "each other is pointless and wastes power; declare them in "
        "set_clock_groups -asynchronous and let CTS balance each on its own. "
        "If A and B are synchronous (same PLL, ratio clocks), their "
        "latencies must be balanced, or the inter-clock paths absorb the "
        "difference as skew. The question 'which clocks need to be "
        "balanced together?' is one of the first a CTS engineer asks the "
        "front-end team.")

    h2("Clock power")
    p("Clock power is P = alpha x C x V^{2} x f with activity alpha = 1 "
      "for the clock net (one full charge/discharge per cycle), where C "
      "includes clock wire, clock buffer input and output capacitance and "
      "every flop's clock pin (including the flop's internal clock "
      "inverters). In typical synchronous SoCs the clock network accounts "
      "for **roughly 30-40% of dynamic power** (sometimes more in "
      "flop-heavy designs), which makes it the first target of any power "
      "reduction.")
    eq(["P_clk = C_clk * V^2 * f",
        "",
        "example: C_clk = 1280 fF (the H-tree above, sinks included), V = 0.75 V, f = 1 GHz",
        "         P = 1.28e-12 * 0.5625 * 1e9 = 0.72 mW   for just 16 sink clusters",
        "a 1 M-flop block with ~1.5 fF/flop of pin + wire + buffer cap:",
        "         C ~ 1.5 nF  ->  P ~ 1.5e-9 * 0.5625 * 1e9 ~ 0.84 W"],
       caption="Clock power estimate (the arithmetic is exact; the per-flop "
               "capacitance is an order-of-magnitude assumption)")
    bul([
        "**Clock gating** (architectural, RTL-inferred ICGs, and gating "
        "close to the root) is the biggest lever.",
        "**Low-latency, low-buffer-count trees**: every avoided buffer "
        "stage removes its input/output cap and internal power.",
        "**Multi-bit flops** share the internal clock inverters and reduce "
        "the number of clock pins.",
        "**Avoid over-constraining skew**: tighter skew targets make trees "
        "deeper and fatter; ask for what the paths actually need.",
        "**NDR choice**: double spacing lowers coupling cap (and power); "
        "double width raises area cap slightly - wide wires are for "
        "resistance and EM, not for power.",
    ])

    h2("Post-CTS optimisation and hold fixing")
    p("After CTS the STA mode switches to `set_propagated_clock`, the "
      "clock uncertainty is reduced (skew is now computed), and the "
      "timing picture changes: some setup paths improve (useful skew), "
      "others degrade. **Post-CTS optimisation** repeats setup fixing with "
      "real clocks and, for the first time, fixes **hold** violations.")
    p("Hold fixing inserts delay (delay cells, buffers, or downsized "
      "cells) on the data path of violating paths. The art is to fix hold "
      "without breaking setup: the tool fixes hold at the endpoint "
      "(capture side) of paths whose setup slack is large, uses "
      "multi-corner awareness (hold is usually worst at the fast corner, "
      "setup at the slow corner, and a delay cell that fixes hold at FF "
      "adds several times more delay at SS), and avoids fixing 'false' "
      "hold violations created by missing constraints. Thousands of hold "
      "buffers after CTS are common in large blocks - especially on scan "
      "shift paths - but tens of thousands suggest a clock-tree or "
      "constraint problem.")
    tbl(["Symptom after CTS", "Likely cause", "Fix"], [
        ["Massive hold violations on scan paths", "Adjacent flops, zero "
         "logic, skew from different leaf buffers", "Normal - hold "
         "buffers; or reorder chains so neighbours share a leaf"],
        ["Setup degraded on inter-block paths", "Latency mismatch with "
         "other blocks", "Latency targets; update block timing models"],
        ["Clock transition violations", "Too few buffers, long clock "
         "routes, high fanout ICG", "Tighter max-fanout, clone ICGs, NDR"],
        ["Hold fixed at FF breaks setup at SS", "Delay cell ratio across "
         "corners", "Fix with MCMM, prefer small buffers, move clock "
         "(useful skew)"],
        ["Huge latency", "Deep tree, many clock muxes/gates, macros with "
         "large insertion delay", "Restructure, MSCTS, review macro "
         "insertion delays"],
    ], widths=[2.1, 2.4, 2.5], caption="Common post-CTS debugging patterns")
    h3("Reading a CTS report")
    code([
        "# Clock tree summary (illustrative, not from a real run; generic format)",
        "Clock      Sinks   Bufs  Invs  ICGs  Levels  Latency(min/max ps)  Skew(ps)  MaxTran",
        "---------  ------  ----  ----  ----  ------  -------------------  --------  -------",
        "core_clk   184312   212  3871  1406      11        412 / 448            36   58 ps",
        "axi_clk     22140    31   402   188       8        301 / 322            21   55 ps",
        "scan_clk   206452    -     -     -        -     (shares core/axi trees; test mode)",
        "jtag_tck      314    6     12     0       4        140 / 151            11   40 ps",
        "",
        "Skew groups       target  achieved   Worst sink pair",
        "core_clk/func       40        36     u_alu/acc_reg[31]/CK vs u_lsu/q_reg[3]/CK",
    ], caption="What a CTS summary typically contains (illustrative)")
    p("Read it top-down: sink count per clock (did every flop get "
      "found?), levels and latency (is the tree deeper than expected?), "
      "skew against target per skew group, maximum clock transition, and "
      "the worst sink pairs. A clock with far fewer sinks than the flop "
      "count in its domain usually means the SDC defines the clock on the "
      "wrong pin or a clock mux/gate is not traced; a very deep tree "
      "usually means a high-fanout ICG or an unnecessary balancing "
      "requirement between unrelated clocks.")
    tbl(["Hand-off", "From -> to", "Content"], [
        ["Clock spec", "Front-end/architect -> PD", "Clocks, frequencies, "
         "which clocks balance together, exceptions, latency targets for "
         "inter-block interfaces"],
        ["Post-CTS DB", "PD -> routing (same engineer)", "Clock nets "
         "routed with NDRs, clock cells fixed/dont_touch"],
        ["Clock latencies", "Block PD -> top-level/SoC PD", "Achieved "
         "insertion delay per clock port for top-level balancing and for "
         "block timing models (ETM/ILM)"],
        ["Clock power", "PD -> power team", "Clock net/buffer power for "
         "the power budget"],
    ], widths=[1.4, 2.2, 3.4], caption="CTS hand-offs")

    checklist("CTS sign-off gate before routing", [
        "All clocks built; no unbuffered/unbalanced sinks; report of "
        "ignore/exclude pins reviewed.",
        "Skew, latency and max transition within targets for every clock "
        "and every mode (functional and test).",
        "Setup and hold met (or within an agreed post-route budget) in "
        "all MCMM scenarios with propagated clocks.",
        "Clock nets routed (or pre-routed) with the specified NDR and "
        "shielding; clock cells are dont_touch from here on.",
        "Clock power reported and compared to the power budget.",
    ])

    h2("Summary")
    bul([
        "CTS turns ideal clocks into a physical network of buffers, "
        "inverters, ICGs and NDR-routed wires; STA then uses propagated "
        "clocks.",
        "Goals: low skew on paths that matter, low latency (less OCV), "
        "sharp transitions, low power, robustness.",
        "Structures range from conventional balanced trees through "
        "H-trees and spines to meshes and multi-source CTS. Our Elmore "
        "model gave 0 ps skew for an H-tree, 40 ps for an edge-driven "
        "fishbone and 8 ps when the same fishbone is centre-driven.",
        "Useful skew/CCOpt moves slack between stages; clock-gating checks "
        "and generated clocks/muxes need special care.",
        "CPPR removes pessimism on the common path; jitter and duty-cycle "
        "distortion enter via uncertainty and half-cycle paths.",
        "Clock power is typically 30-40% of dynamic power; hold is fixed "
        "after CTS, multi-corner aware.",
    ])
    h2("Exercises")
    bul([
        "Using ctree.py, add wire snaking to the edge-driven fishbone so "
        "every branch has the same Elmore delay. How much wire did you "
        "add and what happened to total capacitance?",
        "A launch flop has clock latency 520 ps (late), capture 470 ps "
        "(early), and the common path ends at a node with late/early "
        "arrivals of 300/270 ps. Compute the skew seen by setup before and "
        "after CPPR.",
        "Explain why inverter-based clock trees preserve duty cycle better "
        "than buffer-based ones.",
        "A flop B has 80 ps negative setup slack on its input path and "
        "+150 ps on its output path. How much useful skew would you apply, "
        "and what hold checks must you re-verify?",
        "Estimate clock power for 400 k flops at 1.2 GHz, 0.8 V, assuming "
        "2 fF of clock capacitance per flop including wire and buffers. "
        "What fraction is saved if 60% of flops are gated off 70% of the "
        "time?",
    ], ordered=True)

# =============================================================================
#               CHAPTER 17 - ROUTING, SIGNAL INTEGRITY AND DFM
# =============================================================================
def _ch17():
    chapter("Routing, Signal Integrity and DFM")
    p("Routing creates the physical metal and vias that implement every "
      "connection of the netlist, obeying hundreds to thousands of design "
      "rules (Chapter 3), meeting timing with real parasitics, and "
      "producing geometry that the fab can print and polish reliably. "
      "After CTS the clock nets are already routed; routing now completes "
      "the remaining signal nets - often millions of them across 10-15+ "
      "metal layers - and then hands the design to extraction and sign-off. "
      "Three disciplines meet here: **combinatorial routing algorithms**, "
      "**signal integrity** (crosstalk, noise, electromigration) and "
      "**design for manufacturability** (fill, density, lithography "
      "hotspots, via redundancy).")

    h2("Routing layers, tracks and preferred directions")
    p("Each routing layer has a **preferred direction** (horizontal or "
      "vertical, alternating layer to layer), a **pitch** (track spacing), "
      "and minimum width/spacing. Lower layers are thin and dense (short "
      "local connections, pin access), intermediate layers carry "
      "block-level routes, and thick upper layers carry long global wires, "
      "clock trunks and power. Wrong-way routing on a layer is allowed in "
      "older nodes but restricted or forbidden at advanced nodes, where "
      "lower metals are unidirectional and printed with multiple patterning.")
    diagram([
        "   layer    dir  relative pitch   typical role",
        "   ------   ---  --------------   -----------------------------------------",
        "   AP/RDL    -      very thick    bumps, redistribution, package interface",
        "   M13-M14   H/V    ~ 20-50x      top power grid, global clocks",
        "   M9-M12    H/V    ~ 4-10x       global signal routes, clock trunks, PG straps",
        "   M4-M8     H/V    ~ 1.5-2x      block-level signal routing",
        "   M1-M3     H/V    1x (tightest) cell pins, local routing, multi-patterned",
        "   MEOL      -      -             local interconnect / contacts to gate & S/D",
        "",
        "   (layer counts and ratios vary widely by node and foundry option)",
    ], caption="A generic advanced-node metal stack (schematic)")
    p("The router works on a **track grid** derived from the LEF: each "
      "`LAYER` statement gives direction, pitch, width and spacing tables, "
      "and each `VIA`/`VIARULE` defines legal vias. Cell pins, defined in "
      "the cell LEF, must be reached from tracks - at advanced nodes **pin "
      "access** (how many distinct ways a router can land on a pin) is a "
      "first-order problem that library designers and placement tools "
      "(cell spacing, flipping) address together.")

    h2("Global routing, track assignment and detailed routing")
    diagram([
        "   +-----------------+    gcell grid, capacity per edge/layer, route each net as",
        "   | global routing  |--> a sequence of gcells (Steiner tree + maze/pattern routes);",
        "   +-----------------+    minimise overflow and wirelength; layer assignment",
        "            |",
        "            v",
        "   +-----------------+    assign each global segment to an actual track in its",
        "   | track assignment|--> panel; long straight segments first; avoid parallel",
        "   +-----------------+    runs of critical nets (early crosstalk control)",
        "            |",
        "            v",
        "   +-----------------+    exact geometry: pin access, vias, jogs; fix all spacing,",
        "   | detailed routing|--> end-of-line, min-area, via enclosure, cut spacing, colour",
        "   +-----------------+    rules; rip-up and reroute iterations until DRC count -> 0",
        "            |",
        "            v",
        "   search & repair, redundant vias, post-route opt, fill, extraction -> sign-off",
    ], caption="The three routing stages")
    p("**Global routing** divides the die into gcells and decides, for each "
      "net, which gcells and layers it will use - without committing to "
      "tracks. Because it is fast, it is also the congestion estimator used "
      "during placement. **Track assignment** turns the coarse routes into "
      "segments on specific tracks within each panel (a row or column of "
      "gcells), which is where long parallel runs can be avoided. "
      "**Detailed routing** then produces exact DRC-correct geometry, "
      "working in small windows and iterating **rip-up and reroute** until "
      "no violations remain.")

    h3("Maze routing: the Lee algorithm")
    p("The Lee algorithm (1961) is the textbook detailed router. It is "
      "a breadth-first search on a grid: from the source, label every "
      "reachable free cell with its distance (the **wave expansion**), "
      "stop when the target is labelled, then **backtrace** from target to "
      "source by always stepping to a neighbour whose label is one less. "
      "It is guaranteed to find a shortest path if one exists, but needs "
      "memory and time proportional to the grid area. Improvements include "
      "A* search (expand toward the target first), bidirectional search, "
      "cost functions penalising vias, bends and congestion (Soukup, "
      "Hadlock), and line-probe routers (Hightower, Mikami-Tabuchi) that "
      "trace straight lines instead of cells - fast but not complete.")
    p("The script below routes two 2-pin nets on a 10 x 20 grid with "
      "obstacles (`#`). Each net's routed cells become blockages for the "
      "next net. Routing in two different orders shows the most important "
      "property of sequential routing: **the result depends on net order**, "
      "and an early net can make a later one unroutable.")
    code(_SRC_LEE, caption="lee2.py - Lee maze router with BFS wave "
                           "expansion, backtrace and net ordering")
    out(_OUT_LEE, caption="Real output of python3 lee2.py (* = net A, "
                          "+ = net B, # = blockage)")
    p("Routed A-then-B, both nets complete: A takes 23 grid units (Manhattan "
      "distance 21, a 2-unit detour over the wall) and B detours to 27 "
      "units around A. Routed B-then-A, B takes its shortest 15-unit path "
      "down column 7 and walls off the left half of the grid, so A "
      "becomes **unroutable**. A real router would now **rip up** B (or "
      "the nets blocking A), route A, and **reroute** B with a history "
      "cost that discourages the contested cells - negotiated congestion "
      "routing (PathFinder) formalises exactly this. Production routers "
      "iterate this on millions of nets while also checking every design "
      "rule, which is why detailed routing dominates back-end runtime.")

    h3("Design-rule-driven routing")
    p("Modern detailed routers are driven by far more than width and "
      "spacing: end-of-line spacing, minimum area and minimum enclosed "
      "area, minimum step, parallel-run-length-dependent spacing tables, "
      "via enclosure and cut-spacing rules, via-to-via spacing across "
      "layers, and multi-patterning colour rules (two same-colour shapes "
      "on a double-patterned layer must be further apart than two "
      "different-colour shapes). The router must also avoid 'odd cycles' "
      "that cannot be coloured. Rules come from the tech LEF (or the tool's "
      "tech file), which the foundry and tool vendor co-develop.")

    h2("Vias, redundant vias and non-default rules")
    p("A single via is a reliability and yield weak point: a void or "
      "misalignment in one cut opens the net, and a single cut carries "
      "current density limited by EM. **Redundant (double-cut) via "
      "insertion** after routing replaces single-cut vias by two-cut or "
      "bar vias wherever space allows; typical targets are a high "
      "percentage (often 90%+ where possible) of vias doubled, "
      "especially on clock and power-critical nets. Foundry DFM rules may "
      "be 'recommended' rules that are scored rather than mandatory.")
    p("**Non-default rules (NDRs)** - introduced for clocks in Chapter "
      "16 - are also applied to critical signal nets: wider wires for long "
      "high-speed routes (lower resistance), extra spacing for noise-"
      "sensitive nets (analog references, asynchronous resets), and "
      "multiple-cut vias for high-current nets. Each NDR consumes "
      "tracks, so they are used selectively.")

    h2("Crosstalk: coupling, delta delay and glitches")
    p("At advanced nodes wires are tall and narrow and packed at minimum "
      "spacing, so a large fraction of each wire's capacitance - often "
      "more than half - is **coupling capacitance** C_{c} to its "
      "neighbours rather than to ground. When a neighbour (the **aggressor**) "
      "switches, charge is injected into the **victim** through C_{c}. Two "
      "effects follow:")
    bul([
        "**Delta delay (crosstalk-induced delay change)**: if aggressor and "
        "victim switch at overlapping times, the effective coupling "
        "capacitance is multiplied by the **Miller factor** k: k = 0 when "
        "they switch in the same direction (the victim speeds up), k = 1 "
        "when the aggressor is quiet, k = 2 when they switch in opposite "
        "directions (the victim slows down). STA with SI uses this for "
        "setup (slowdown on data, speed-up on the capture clock) and hold "
        "(the reverse).",
        "**Glitch (functional noise)**: if the victim is quiet (held by its "
        "driver), an aggressor transition creates a voltage bump. If the "
        "bump exceeds the receiver's noise margin and propagates to a "
        "flop, latch or asynchronous pin during its sensitive window, it "
        "corrupts state. Noise analysis compares glitch height and width "
        "against noise-immunity curves from the library.",
    ])
    eq(["C_eff(victim) = C_ground + k * C_c          k in {0, 1, 2}",
        "",
        "glitch peak (lumped, ramp aggressor of slew tr, victim holder R, tau = R*C_tot):",
        "   V_peak = VDD * (C_c / C_tot) * (tau / tr) * (1 - exp(-tr / tau))",
        "   -> bounded by the charge-sharing limit VDD * C_c / C_tot when tau >> tr"],
       caption="First-order crosstalk models")
    p("The script estimates both effects for a 500-um victim on thin "
      "lower metal (2 ohm/um) with a weak 800-ohm driver, whose ground "
      "capacitance is 40 fF and coupling to each neighbour is 35 fF at "
      "minimum spacing - numbers typical in order of magnitude for an "
      "advanced node, but not for any particular process.")
    code(_SRC_XTALK, caption="xtalk.py - Miller-factor delay window and "
                             "lumped glitch estimate")
    out(_OUT_XTALK, caption="Real output of python3 xtalk.py")
    p("At minimum spacing, the victim's delay can be anything from 40 to "
      "165 ps depending on what its neighbours do - a window larger than "
      "the nominal delay itself. Doubling the spacing shrinks the window; "
      "shielding with ground wires removes the variation entirely (k is "
      "always 1) but does **not** reduce the delay, since the shield is "
      "still a capacitance. Glitch height scales with the length of the "
      "parallel run and the aggressor's slew: a 100-um overlap produces "
      "~5% VDD, while a 500-um run with a sharp aggressor reaches ~26-29% "
      "VDD, enough to worry about on an asynchronous reset or a clock.")
    box("key", "Timing windows make SI analysis tractable",
        "Assuming every aggressor switches at the worst moment is hugely "
        "pessimistic. SI-aware STA (PrimeTime SI, Tempus SI) computes the "
        "**arrival windows** of victims and aggressors and only counts "
        "aggressors whose windows overlap, iterating because delta delays "
        "move the windows. Logical correlation (two nets that can never "
        "switch together) and aggressor filtering by coupling size reduce "
        "pessimism further.")
    h3("Fixing crosstalk")
    tbl(["Fix", "How it helps", "Cost"], [
        ["Increase spacing / NDR", "Reduces C_c roughly in proportion to "
         "the extra spacing", "Routing tracks"],
        ["Shielding", "Neighbour becomes a quiet supply wire", "Two tracks "
         "per shielded net; slightly higher C_ground"],
        ["Layer promotion", "Move the net to a thicker/wider upper layer "
         "with lower R and different neighbours", "Vias, upper-layer "
         "resources"],
        ["Upsize the victim driver", "Stronger holder: smaller glitch, "
         "faster transition, smaller delta delay", "Area, power, input "
         "cap upstream"],
        ["Buffer insertion", "Breaks a long parallel run into shorter "
         "coupled segments; restores slew", "Cells, placement"],
        ["Downsize / slow the aggressor", "Slower aggressor slew injects "
         "less charge", "Aggressor timing"],
        ["Reroute (ECO route)", "Separate the two nets physically",
         "Router iterations"],
    ], widths=[1.8, 3.4, 1.8], caption="SI repair techniques")

    h2("Antenna effect")
    p("During fabrication, metal layers are etched with plasma. A long "
      "metal segment connected to a transistor gate - but not yet to any "
      "diffusion that could discharge it, because the connecting upper "
      "layer has not been built - collects charge from the plasma and "
      "can drive current through the thin gate oxide, damaging it "
      "(shifting Vth or causing early breakdown). This is the **antenna "
      "effect** (plasma-induced gate-oxide damage). Foundries specify "
      "antenna rules as ratios of the metal (or via) area connected to a "
      "gate, layer by layer, to the gate area, often cumulative across "
      "layers and relaxed when a diode is connected.")
    diagram([
        "  problem:                                   fixes:",
        "",
        "  M1 long wire (etched first, floating)       a) layer jump (bridge up to a higher",
        "  ==============================+                layer near the gate, so the long",
        "                                |                piece is only connected once the",
        "                              [gate]             gate's upper layer exists)",
        "   driver's drain connects",
        "   only through M5 (built later)             b) antenna diode (reverse-biased",
        "   -> no discharge path during M1 etch          diffusion) on the gate net",
        "",
        "  antenna ratio = (area of metal Mx connected to gate) / (gate oxide area)",
    ], caption="The antenna effect and its standard fixes")
    bul([
        "**Layer jumping (bridging)**: break the offending lower-layer wire "
        "and jump up to a higher layer just before the gate, so during the "
        "etch of the lower layer only a short piece is attached to the "
        "gate. Routers do this automatically.",
        "**Antenna diodes**: an ANTENNA cell (a reverse-biased diode to "
        "substrate) near the gate gives the charge a discharge path; it adds "
        "a small capacitance and leakage.",
        "**Driver placement**: a diffusion (driver output) on the same net "
        "discharges it; nets with a driver close to the receiver rarely "
        "violate.",
        "Antenna checks are part of physical verification (Chapter 18); "
        "the LEF carries antenna data (ANTENNAGATEAREA, "
        "ANTENNADIFFAREA and per-layer ratio rules) so the router can fix "
        "them during routing.",
    ])

    h2("Electromigration on signal nets")
    p("Electromigration (EM, Chapter 18 in detail) is metal atom transport "
      "by the electron wind; it is usually associated with power grids "
      "but also affects signal nets that carry high switching currents: "
      "clock nets, high-fanout drivers, long heavily loaded nets. Signal "
      "EM uses **RMS and peak current** limits (bidirectional AC current "
      "partially heals, so average-current limits apply mostly to "
      "unidirectional power currents) and depends on temperature. Fixes: "
      "widen the wire (NDR), add parallel routes or multi-cut vias, reduce "
      "the driver strength or its load, split the net.")

    h2("Design for manufacturability (DFM)")
    p("A design that passes DRC can still yield poorly. DFM covers the "
      "rules and practices that make the layout robust to manufacturing "
      "variation. Most of it is driven by the physics of lithography and "
      "chemical-mechanical polishing (CMP) introduced in Chapter 3.")
    tbl(["DFM topic", "Problem", "Action in implementation"], [
        ["Metal density rules", "CMP removes copper and dielectric at rates "
         "that depend on local pattern density: sparse areas dish, dense "
         "areas erode, giving thickness variation (and so R/C variation "
         "and planarity problems)", "Min/max density per window (e.g. "
         "sliding windows tens of um wide) per layer; checked in DRC"],
        ["Metal fill (dummy fill)", "Low-density windows", "Insert "
         "floating (or tied) fill shapes after routing; timing-aware fill "
         "keeps distance from critical nets because fill adds coupling "
         "capacitance; extraction must see the fill"],
        ["Lithography hotspots", "Patterns that print poorly under process "
         "window variation (pinching, bridging) even though they pass DRC",
         "Litho-friendly routing, pattern-matching DFM checks, foundry "
         "hotspot libraries, fixing in ECO"],
        ["Via redundancy", "Single-cut via failures", "Double-cut/bar "
         "vias (see above)"],
        ["Wire spreading and widening", "Critical-area defects: random "
         "particles short close wires or open thin ones", "Spread wires "
         "where tracks are free; widen where possible"],
        ["Recommended rules", "Foundry rules beyond the minimum that "
         "improve yield", "Scored DFM checks; fix where cheap"],
        ["Multi-patterning colouring", "Decomposition failures, overlay "
         "sensitivity", "Colour-aware routing; balanced colour density"],
    ], widths=[1.5, 2.8, 2.7], caption="DFM measures applied during and "
                                       "after routing")
    box("warn", "PITFALL - Fill after timing sign-off",
        "Metal fill adds capacitance to nearby wires. If fill is inserted "
        "after the final extraction and STA, the sign-off timing is no "
        "longer the timing of the taped-out design. Insert fill before "
        "the final extraction (or use a fill-aware extraction mode) and "
        "re-run SI/timing on the filled database.")

    h2("Post-route optimisation")
    p("Once real routes exist, parasitics are accurate and SI effects "
      "appear. Post-route optimisation fixes the residual setup, hold, "
      "transition and SI violations with the same toolbox as before - "
      "sizing, buffer insertion, Vt swap, hold delay insertion - but "
      "every change now requires **ECO routing**: rip up and reroute the "
      "affected nets while leaving the rest untouched. Changes must be "
      "small and local; the goal is convergence, not re-optimisation. The "
      "loop 'extract -> STA with SI -> fix -> ECO route -> DRC check' "
      "runs until timing, SI and DRC are all clean.")

    code([
        "# OpenROAD-style routing sequence (real OpenROAD command names; example values;",
        "# not run here - see Chapter 24 for the open-source flow)",
        "set_routing_layers -signal met1-met5 -clock met3-met5",
        "global_route -congestion_iterations 50 -verbose",
        "estimate_parasitics -global_routing",
        "repair_timing                        ;# last chance with GR parasitics",
        "detailed_route -output_drc route_drc.rpt -droute_end_iter 64",
        "repair_antennas                      ;# insert diodes where jumping was not enough",
        "density_fill -rules fill.json        ;# metal fill",
        "extract_parasitics -ext_model_file rcx_patterns.rules",
        "write_spef top.spef",
    ], caption="The routing stage as an open-source script")
    tbl(["Detailed-route DRCs left over", "Usual root cause", "Where to fix"], [
        ["Many shorts/spacing in one region", "Local congestion or pin "
         "access", "Placement: pad cells, lower density, re-place"],
        ["Violations at macro edges", "Macro pins on blocked tracks, "
         "missing halo", "Floorplan: halo, pin layer/placement"],
        ["Min-area / end-of-line on short stubs", "Router corner cases",
         "Search-and-repair iterations, ECO route"],
        ["Violations inside or at IP boundaries", "Abstract (LEF) does "
         "not match the GDS (missing obstructions)", "Fix the LEF with the "
         "IP owner; not a router problem"],
        ["Colour conflicts", "Odd cycles on multi-patterned layers",
         "Reroute locally; check cell library compliance"],
    ], widths=[2.2, 2.4, 2.4], caption="Triaging leftover routing DRCs")

    h2("RC extraction and SPEF")
    p("**Parasitic extraction** computes the resistance and capacitance of "
      "every routed net from its geometry and the process's interconnect "
      "technology file (ITF/ICT, compiled into a tool-specific TLUplus/"
      "QRC tech file). Sign-off extractors (StarRC, Quantus, Calibre "
      "xACT, and in open source OpenRCX) use pattern-matching against "
      "field-solver-built tables, or a field solver directly for critical "
      "nets. Extraction must be done at each **RC corner** (typical, "
      "Cworst, Cbest, RCworst, RCbest - thickness and width variations "
      "pull R and C in correlated directions), and at the right "
      "temperature for resistance.")
    p("The standard output is **SPEF** (Standard Parasitic Exchange Format, "
      "IEEE 1481), a text format listing, per net, the total capacitance, "
      "each node's ground capacitance, coupling capacitances to other nets, "
      "and the resistor network.")
    code([
        "*SPEF \"IEEE 1481-1998\"",
        "*DESIGN \"top\"",
        "*T_UNIT 1 NS",
        "*C_UNIT 1 FF",
        "*R_UNIT 1 OHM",
        "*L_UNIT 1 HENRY",
        "*NAME_MAP",
        "*1 n42",
        "*2 u7",
        "*3 u9",
        "*D_NET *1 5.13                  // net n42, total cap 5.13 fF",
        "*CONN",
        "*I *2:Y O *L 0 *D INV_X2        // driver pin",
        "*I *3:A I *L 1.2                // load pin, 1.2 fF pin cap",
        "*CAP",
        "1 *1:1 1.10                     // ground cap at internal node",
        "2 *1:2 1.45",
        "3 *1:2 *17:3 1.38               // coupling cap to another net",
        "*RES",
        "1 *2:Y *1:1 12.5",
        "2 *1:1 *1:2 40.2",
        "3 *1:2 *3:A 8.1",
        "*END",
    ], caption="The structure of a SPEF file (hand-written illustrative "
               "fragment, not from a real run; comments added)")
    box("tip", "Sanity-check the extraction",
        "Before trusting sign-off numbers, check that every net was "
        "extracted (no 'unannotated nets' in STA), that the RC corner "
        "matches the timing corner, that coupling caps are present (SI "
        "needs them - a 'ground-only' extraction silently disables "
        "crosstalk analysis) and that fill was included.")

    h2("Summary")
    bul([
        "Routing is global routing (gcells, congestion), track "
        "assignment, and detailed routing with rip-up and reroute; layers "
        "have preferred directions and pitch, advanced lower layers are "
        "unidirectional and multi-patterned.",
        "The Lee maze router finds shortest paths by BFS and backtrace; our "
        "run showed that net order can make a net unroutable, which "
        "rip-up and reroute resolves.",
        "Crosstalk changes delay (Miller factor 0..2) and creates glitches; "
        "our 500-um example had a 40-165 ps delay window at minimum "
        "spacing. Fixes: spacing, shielding, layer promotion, sizing, "
        "buffering.",
        "Antenna violations are fixed by layer jumping and diodes; signal "
        "EM by widening and multi-cut vias.",
        "DFM: density rules and fill (CMP), litho hotspots, redundant "
        "vias, wire spreading; fill must be in the extracted database.",
        "Post-route optimisation uses ECO routing; extraction at every RC "
        "corner produces SPEF for sign-off STA.",
    ])
    h2("Exercises")
    bul([
        "Modify lee2.py to add a via cost: give the grid two layers "
        "(H-only and V-only) and count a layer change as cost 3. How does "
        "the route for net A change?",
        "Why is k = 2 the worst case for setup on a data path but the best "
        "case for hold? Which Miller factor would SI analysis use on the "
        "capture clock path for a setup check?",
        "A 1.5-mm net on M2 fails an antenna check. Give two fixes and "
        "explain which one the router prefers and why.",
        "Explain why metal fill changes timing and how you would make "
        "sure sign-off accounts for it.",
        "List the five common RC extraction corners and state which one is "
        "typically worst for setup on long wire-dominated paths and which "
        "for short gate-dominated paths.",
    ], ordered=True)

# =============================================================================
#   CHAPTER 18 - SIGN-OFF: TIMING, POWER INTEGRITY, RELIABILITY, PHYSICAL VER.
# =============================================================================
def _ch18():
    chapter("Sign-off: Timing, Power Integrity, Reliability and Physical "
            "Verification")
    p("**Sign-off** is the set of independent, golden-tool checks that "
      "must all pass before a design is allowed to tape out. The word "
      "matters: implementation tools (Innovus, Fusion Compiler, OpenROAD) "
      "have built-in timers, extractors and DRC checkers, but their results "
      "are estimates tuned for speed. Sign-off uses separately qualified "
      "tools and foundry-certified rule decks - PrimeTime or Tempus for "
      "timing, StarRC or Quantus for extraction, RedHawk or Voltus for "
      "power integrity, Calibre, Pegasus or IC Validator for physical "
      "verification, Conformal or Formality for equivalence - and every "
      "waiver is written down and approved. A chip fails in silicon because "
      "one of these checks was skipped, run on the wrong data, or waived "
      "without understanding.")
    diagram([
        "                 final routed DB (DEF/OASIS + netlist)",
        "                                |",
        "       +-----------+-----------+-+----------+-------------+-------------+",
        "       v           v           v            v             v             v",
        "   extraction   physical     formal      power/IR/EM   low-power    reliability",
        "   (SPEF, all   verif.       equiv.      (static +     (UPF static  (EM, aging,",
        "    RC corners) DRC LVS ERC  RTL vs      dynamic)      checks)      self-heat)",
        "       |        antenna,     netlist        |             |             |",
        "       v        density         |           |             |             |",
        "   STA (MCMM,       |           |           v             |             |",
        "   SI, POCV) <------+-----------+---- IR-aware timing     |             |",
        "       |            |           |           |             |             |",
        "       +------------+-----------+-----------+-------------+-------------+",
        "                                |",
        "                sign-off review: all clean or waived -> tapeout",
    ], caption="The sign-off checks and how they feed each other")

    h2("Timing sign-off")
    p("Chapter 9 covered STA theory; here we look at what makes sign-off "
      "STA different from the timing inside the implementation tool.")
    h3("Multi-corner multi-mode (MCMM)")
    p("A **mode** is a set of constraints (functional, scan shift, scan "
      "capture, MBIST, low-power retention...). A **corner** is a "
      "combination of process (library corner: SS, TT, FF, and at advanced "
      "nodes SSG/FFG global corners), voltage, temperature and RC "
      "extraction corner. A **scenario** is a mode x corner pair. Sign-off "
      "runs every scenario that could be worst for some check. Temperature "
      "inversion at advanced nodes (cells can be slower at low temperature "
      "at low voltage) means both -40 C and 125 C (or the product's "
      "range) are needed for setup.")
    tbl(["Scenario (example)", "Library PVT", "RC corner", "Checks"], [
        ["func_ss_cold", "SSG, 0.675 V, -40 C", "Cworst / RCworst",
         "setup (temperature inversion), max transition"],
        ["func_ss_hot", "SSG, 0.675 V, 125 C", "RCworst", "setup, EM "
         "current (hot)"],
        ["func_ff_cold", "FFG, 0.825 V, -40 C", "Cbest / RCbest", "hold"],
        ["func_ff_hot", "FFG, 0.825 V, 125 C", "Cbest", "hold, leakage"],
        ["func_tt", "TT, 0.75 V, 85 C", "typical", "power "
         "reporting, reference"],
        ["shift_ss / shift_ff", "SS / FF", "RCworst / Cbest", "scan "
         "shift setup (slow clock) and hold (critical!)"],
        ["capture_ff", "FF", "Cbest", "at-speed capture hold"],
    ], widths=[1.6, 1.9, 1.5, 2.3], caption="A typical sign-off corner "
         "list for a 0.75-V nominal design (values illustrative; the real "
         "list comes from the foundry and product requirements)")
    h3("Variation modelling: OCV, AOCV, POCV/LVF")
    tbl(["Model", "How derate is applied", "Pessimism"], [
        ["Flat OCV", "One late and one early derate (e.g. +/-5%) on all "
         "cells and nets", "High for deep paths, possibly optimistic for "
         "very short ones"],
        ["AOCV", "Derate from tables indexed by path depth and distance: "
         "random variation averages out over many stages", "Lower"],
        ["POCV / SOCV", "Each cell arc has a sigma; path sigma computed "
         "statistically (root-sum-square); check at mean +/- n*sigma "
         "(typically 3)", "Lowest; standard at 16 nm and below"],
        ["LVF (Liberty Variation Format)", "Liberty tables of sigma per "
         "arc, slew and load (ocv_sigma_cell_rise etc.), including "
         "asymmetric early/late sigma", "Data format used by POCV"],
    ], widths=[1.5, 3.6, 1.9], caption="On-chip variation models in sign-off STA")
    h3("SI and the rest of the sign-off STA checklist")
    bul([
        "**SI on**: coupling caps from SPEF, delta delay with timing "
        "windows, and noise/glitch analysis on all nets (Chapter 17).",
        "**All checks, not only setup/hold**: max transition, max "
        "capacitance, min pulse width (clock high/low), minimum period, "
        "recovery/removal on asynchronous resets, clock-gating checks, "
        "data-to-data checks, latch time borrowing.",
        "**Constraints are signed off too**: unconstrained endpoints = 0 "
        "(or reviewed), no unintended false paths or multicycle paths, "
        "clock-domain crossings handled by CDC sign-off (Chapter 6), IO "
        "constraints agreed with the SoC top.",
        "**Consistency**: the netlist in STA is exactly the netlist in LVS "
        "and LEC; the SPEF was extracted from the same layout; library "
        "versions match the foundry release.",
    ])
    code([
        "# Illustrative PrimeTime-style sign-off script fragment (not from a real run)",
        "set_app_var si_enable_analysis true",
        "set_app_var timing_pocvm_enable_analysis true",
        "set_app_var timing_remove_clock_reconvergence_pessimism true",
        "read_verilog top.post_route.v ; link_design top",
        "read_parasitics -keep_capacitive_coupling top.rcworst_m40.spef.gz",
        "read_sdc top.func.sdc",
        "update_timing -full",
        "report_global_timing",
        "report_constraint -all_violators -max_transition -max_capacitance",
        "report_analysis_coverage          ;# untested / unconstrained checks",
        "report_si_bottleneck              ;# nets with largest delta delay",
        "report_noise -all_violators",
    ], caption="Sign-off STA essentials (commands modelled on PrimeTime; "
               "illustrative)")

    h2("Power integrity: IR drop and voltage-drop-aware timing")
    p("The power grid (Chapter 14) has resistance, so current flowing from "
      "the bumps to the cells causes a **voltage drop (IR drop)** on VDD and "
      "a **ground bounce** on VSS. A cell that sees 0.70 V instead of 0.75 V "
      "is slower - cell delay sensitivity to supply is typically several "
      "percent delay per few percent of voltage at advanced nodes - and "
      "severe drop can cause functional failure.")
    tbl(["Analysis", "What it computes", "When used"], [
        ["Static IR drop", "Average current per cell (from average power "
         "at a given activity), DC solve of the resistive grid", "Early "
         "grid sizing; catches missing vias/straps, weak connections; "
         "typical budget a few % of VDD"],
        ["Dynamic IR drop (vectorless)", "Tool chooses switching "
         "scenarios statistically to meet a target toggle rate, solves the "
         "RLC grid in time including decap and package", "Coverage "
         "without vectors; can be pessimistic or miss real hot spots"],
        ["Dynamic IR drop (vector-based)", "Uses real activity (VCD/FSDB/"
         "SAIF) from simulation or emulation of worst-case workloads, "
         "including scan capture", "Sign-off for realistic peaks; needs "
         "good vectors"],
        ["Voltage-drop-aware timing", "Annotates each cell's effective "
         "supply from IR analysis back into STA (or uses the IR-aware "
         "delay models)", "Critical paths through hot spots; clock trees"],
        ["Power-up / rush current", "Current when a power-gated domain "
         "turns on", "Power switch sequencing (Chapter 11)"],
    ], widths=[1.8, 3.2, 2.0], caption="Power-integrity analyses")
    eq(["static:  V_drop(node) = sum over grid resistors on the path of I_branch * R_branch",
        "dynamic: V_drop(t) = I(t) * R  +  L * dI/dt   (grid, package and bump inductance),",
        "         mitigated by on-die decap: charge dQ = C_decap * dV supplies the fast peak"],
       caption="Static versus dynamic voltage drop")
    box("warn", "PITFALL - Scan capture IR drop",
        "During at-speed scan capture, a large fraction of all flops can "
        "toggle in the same cycle - far more than in any functional mode. "
        "The resulting dynamic drop can make good silicon fail at-speed "
        "tests (yield loss from overkill). Run vector-based IR on real "
        "ATPG patterns and use low-power ATPG fill or staggered capture "
        "if needed (Chapter 10).")

    h2("Reliability sign-off: EM, self-heating and aging")
    h3("Electromigration and Black's equation")
    p("Electromigration is the gradual transport of metal atoms by "
      "momentum transfer from electrons. Over years it creates voids "
      "(opens, resistance increase) and hillocks/extrusions (shorts). The "
      "median time to failure follows **Black's equation**. Foundries "
      "translate it into current-density limits per layer, width and "
      "temperature (average current for unidirectional flow, RMS for "
      "Joule heating, peak for signal nets), for a target lifetime (for "
      "example 10 years at a given junction temperature) and a failure-"
      "rate criterion.")
    eq(["MTTF = A * J^(-n) * exp( Ea / (k * T) )",
        "",
        "J  = current density (A/cm^2)       n  ~ 1 to 2 (fit; 2 often used)",
        "Ea = activation energy (eV)         k  = 8.617e-5 eV/K    T = absolute temperature",
        "A  = technology/geometry constant   (Cu interconnect: Ea typically ~0.8-0.9 eV)"],
       caption="Black's equation for electromigration lifetime")
    p("The script normalises lifetime to 1.0 at 1 MA/cm^{2} and 105 C, "
      "using n = 2 and Ea = 0.85 eV (typical fit values; real ones are "
      "foundry-specific), and shows how quickly margin disappears with "
      "temperature and current density.")
    code(_SRC_BLACK, caption="black.py - relative EM lifetime")
    out(_OUT_BLACK, caption="Real output of python3 black.py")
    p("Two lessons are worth memorising. Lifetime falls roughly 4x for "
      "every 20 C rise near 105 C with these parameters, so the "
      "**temperature** at which EM limits are specified matters as much "
      "as the current. And because lifetime goes as J^{-2}, a wire that is "
      "50% over its limit loses more than half its life - EM violations are "
      "not 'small' just because the overshoot is small. **Self-heating** "
      "of wires (Joule heating from RMS current) and of FinFET/GAA devices "
      "(heat trapped in narrow fins) raises local temperature by several "
      "degrees above the ambient junction temperature, which the EM check "
      "must include.")
    h3("Device aging in timing")
    bul([
        "**NBTI** (negative-bias temperature instability) raises the |Vth| "
        "of PMOS transistors held on (gate low) at high temperature; it "
        "partially recovers when stress is removed. Clock trees with "
        "gated (stopped) clocks age asymmetrically, distorting duty cycle.",
        "**HCI** (hot-carrier injection) degrades NMOS (and PMOS) by "
        "energetic carriers near the drain during switching; it grows "
        "with switching activity and is worst for high-activity, "
        "high-slew nets.",
        "**PBTI** matters for NMOS with high-k gate stacks; **TDDB** "
        "(time-dependent dielectric breakdown) is a gate-oxide and "
        "inter-metal dielectric lifetime issue set by voltage.",
        "In sign-off, aging is handled by **aged libraries** (Liberty "
        "characterised with end-of-life Vth shifts, e.g. after 10 years at "
        "the mission profile) or aging derates; automotive designs "
        "(AEC-Q100, ISO 26262 mission profiles) require it explicitly.",
    ])

    h2("Physical verification: DRC")
    p("**Design rule checking (DRC)** verifies that every polygon of the "
      "final layout obeys the foundry's manufacturing rules: widths, "
      "spacings, enclosures, extensions, areas, densities, and advanced-"
      "node rules such as multi-patterning colouring, tip-to-tip, "
      "voltage-dependent spacing and via/cut rules. The sign-off rule deck "
      "(Calibre SVRF, Pegasus PVL, ICV runsets; KLayout and Magic decks for "
      "open PDKs) is released by the foundry and must be used unmodified. "
      "Sign-off DRC runs on the **merged GDSII/OASIS**: the block layout "
      "streamed out with all standard-cell, IP and memory layouts "
      "substituted for their abstracts - the implementation tool only ever "
      "saw LEF abstracts.")
    p("The demo uses the open-source **magic** layout tool with its "
      "built-in SCMOS (MOSIS scalable, lambda-based) technology: three "
      "metal-1 wires, one legal, one too narrow, and one too close to its "
      "neighbour, then a batch DRC.")
    code(_SRC_DRC, caption="drc.tcl - run with: magic -dnull -noconsole -T "
                           "scmos drc.tcl")
    out(_OUT_DRC, caption="Real output (last lines) of magic 8.3.105 DRC on "
                          "the deliberately broken layout")
    out(_OUT_DRC_FIX, caption="After widening the middle wire to 3 lambda "
                              "and moving the third wire to 3 lambda spacing "
                              "(drc_fix.tcl): clean")
    p("Magic reports each violation with the rule text from the "
      "technology file and the error region (the area where the rule "
      "fails, in lambda). A production DRC run on a large SoC reports "
      "results per rule in a database (Calibre RVE, KLayout marker "
      "browser), and the team drives the count to zero or to a list of "
      "formally waived violations (for example, known foundry-approved "
      "IP exceptions).")
    tbl(["DRC category", "Examples", "Typical origin"], [
        ["Base width/space", "M2.W.1, M2.S.1, via enclosure", "Manual "
         "edits, pin access, IP abutment"],
        ["Density", "Metal/poly/diffusion density min/max per window",
         "Missing or blocked fill, large macros"],
        ["Antenna", "Metal-to-gate area ratios", "Long nets; checked in "
         "PV with antenna rules"],
        ["Multi-patterning", "Colouring conflicts, same-colour spacing",
         "Router corner cases, IP boundaries"],
        ["Off-grid / structural", "Shapes off manufacturing grid, "
         "acute angles, non-rectilinear", "Imported IP, logos"],
        ["Boundary/ESD/latch-up", "Well tap distance, guard rings, "
         "ESD rules", "I/O ring, analog IP (Chapter 12)"],
    ], widths=[1.6, 3.0, 2.4], caption="Where DRC violations usually come "
                                       "from at sign-off")

    h2("Physical verification: LVS")
    p("**Layout versus schematic (LVS)** proves that the layout implements "
      "the intended circuit. It has two stages:")
    bul([
        "**Extraction**: from the layout polygons, the LVS rule deck "
        "recognises devices (a poly shape crossing diffusion is a MOSFET; "
        "its W and L are measured), resistors, capacitors and diodes, and "
        "traces connectivity through contacts and vias to build a "
        "**layout netlist**. Labels (text on pins) name the nets.",
        "**Comparison**: the layout netlist is compared with the reference "
        "(schematic) netlist - for a digital block, the post-route Verilog "
        "netlist converted to SPICE with the standard cells' transistor-"
        "level CDL netlists. Comparison is graph isomorphism: devices are "
        "matched by type and connectivity, iteratively refining partitions "
        "of nets and devices until everything is uniquely matched or a "
        "mismatch is isolated. Device properties (W, L, number of fins, "
        "multiplier, resistor length) are compared within tolerance.",
    ])
    p("The demo compares hand-written SPICE netlists of an AND2 cell "
      "(NAND2 + inverter) with the open-source LVS tool **netgen** "
      "(used in the OpenLane flow). The 'layout' netlists deliberately use "
      "different device names, internal net names, device order and port "
      "order, which LVS must see through.")
    code(_SPI_SCH, caption="sch.spice - reference (schematic) netlist")
    code(_SPI_OK, caption="lay_ok.spice - 'extracted' netlist, same circuit, "
                          "different names and order")
    code(_LVS_SETUP, caption="setup.tcl - tells netgen to compare W and L "
                             "with 1% tolerance")
    out(_OUT_LVS_OK, caption="Real output of: netgen-lvs -batch lvs "
                             "\"lay_ok.spice and2\" \"sch.spice and2\" "
                             "setup.tcl ok.out (netgen 1.5.133)")
    p("Now two classic layout bugs: the drain of the B-input PMOS is "
      "connected to Y instead of the internal node (a **short/miswire**), "
      "and the inverter NMOS is drawn narrower than intended.")
    code(_SPI_BAD, caption="lay_bad.spice - a miswire plus a device-size "
                           "error")
    out(_OUT_LVS_BAD, caption="Real netgen report (bad.out, excerpt): the "
                              "net-fragment view that pinpoints the miswire")
    p("netgen cannot match nets Y (layout) and n1 (schematic) because their "
      "**fanout signatures** differ: layout net Y has two PMOS drains and one "
      "NMOS drain but no gate connections, while schematic n1 also drives a "
      "PMOS and an NMOS gate. This is how every LVS tool reports "
      "connectivity errors - as mismatched partitions, from which the "
      "engineer infers the physical short or open. Fixing only the "
      "miswire and leaving the narrow transistor gives a topological "
      "match with a **property error**:")
    code(_SPI_W, caption="lay_w.spice - connectivity fixed, W still wrong")
    out(_OUT_LVS_W, caption="Real netgen output: circuits match "
                            "topologically but the W property differs by 43%")
    tbl(["LVS error", "What you see", "Typical cause"], [
        ["Short", "Two named nets merged into one (e.g. 'VDD and n12 "
         "shorted', or a net with too many connections)", "Overlapping "
         "metal, a stray via, fill touching a wire, mislabelled pin text"],
        ["Open", "One schematic net split into two layout nets", "Missing "
         "via, broken wire, missing connection to a well/substrate tap"],
        ["Missing / extra port", "Pin lists differ", "Pin not labelled in "
         "layout, top-level text on wrong layer, port renamed"],
        ["Device mismatch", "Extra or missing devices, wrong type (e.g. "
         "LVT vs SVT)", "Wrong cell variant, missing implant layer, "
         "decap/filler cells not in the netlist"],
        ["Property mismatch", "W/L/nfin/multiplier out of tolerance",
         "Wrong cell version, manual edit"],
        ["Well/substrate connectivity", "Bulk terminals on wrong net",
         "Missing taps, multi-voltage wells, tapless cells without "
         "tap cells"],
    ], widths=[1.4, 2.8, 2.8], caption="Common LVS errors")
    box("tip", "Debugging LVS on a real chip",
        "Fix **shorts first** - a single short (for example a power-to-"
        "ground short through a mislabelled pin) merges thousands of nets "
        "and produces an avalanche of secondary mismatches. Then fix "
        "opens, then ports, then devices, then properties. Always check "
        "the texts/labels and the power connections before believing a "
        "large mismatch report.")

    h2("ERC, antenna and density checks")
    bul([
        "**ERC (electrical rule checks)**: floating gates, floating wells, "
        "nets with no driver or multiple drivers, gates tied directly to "
        "supply (instead of tie cells), wells connected to the wrong "
        "supply, missing ESD protection on pad nets, and in multi-voltage "
        "designs thin-oxide devices connected to high-voltage nets.",
        "**Antenna**: run with the foundry antenna deck on the final "
        "layout; must be clean (router fixes plus diodes, Chapter 17).",
        "**Density**: min/max density per window for every relevant layer "
        "after fill; the foundry also checks density gradient between "
        "neighbouring windows.",
        "**Other foundry checks** often run at tapeout: latch-up rules, ESD "
        "rules, reliability rules for thick-metal and bump layers, and "
        "DFM/recommended-rule scoring.",
    ])

    h2("Formal equivalence checking")
    p("Every netlist transformation after RTL - synthesis, scan insertion, "
      "placement optimisation, CTS, hold fixing, ECOs - could introduce a "
      "functional change. Rerunning full simulation on each netlist is "
      "impossible, so **logic equivalence checking (LEC)** proves "
      "mathematically that two designs implement the same function. The "
      "tool maps **compare points** (primary outputs, flop and latch "
      "inputs, black-box inputs) between the two designs, then proves each "
      "compare point's logic cone equivalent using BDDs and SAT solvers.")
    diagram([
        "  RTL  --LEC-->  synthesis netlist  --LEC-->  DFT netlist  --LEC-->  post-route netlist",
        "                    (retiming, clock gating,     (scan mux: constrain      (buffers, sizing,",
        "                     multibit, constant-flop     scan_enable = 0)           cloning, ECOs)",
        "                     removal need guidance)",
    ], caption="The chain of equivalence checks")
    bul([
        "Non-equivalences are debugged by the counter-example (input "
        "vector) the tool produces.",
        "Synthesis optimisations that change the state encoding "
        "(retiming, FSM re-encoding, register merging, constant or "
        "duplicate register removal) need **guidance files** (SVF in "
        "Formality, or equivalent) or explicit setup, otherwise they "
        "appear as mismatches or unmapped points.",
        "Scan insertion is verified with scan-enable constrained to "
        "functional mode; clock-gating insertion needs clock-gate "
        "recognition.",
        "**Unmapped or 'unreachable' compare points must be reviewed**, not "
        "ignored; an aborted (inconclusive) cone is not a pass.",
        "The post-route netlist LEC is the sign-off check that a physical "
        "optimisation or ECO did not change function.",
    ])

    h2("Low-power sign-off (UPF static checks)")
    p("For designs with power intent (Chapter 11), the final netlist must "
      "be checked against the UPF (IEEE 1801) with a static low-power "
      "verifier (VC LP, Conformal Low Power): every signal crossing from "
      "a switchable domain to an always-on domain has an isolation cell "
      "with the right clamp value and enable; every crossing between "
      "different voltages has a level shifter; retention flops are "
      "connected to the right save/restore controls and supplies; power "
      "switches are connected and chained; always-on cells in switchable "
      "domains take their supply from the always-on rail (secondary PG "
      "pin); and no path goes through a powered-down domain unprotected. "
      "The check runs on the power-aware netlist (with PG pins) that also "
      "goes to LVS.")

    h2("The sign-off criteria checklist")
    checklist("Tapeout sign-off (typical block/chip criteria)", [
        "STA: setup/hold/DRV clean in all MCMM scenarios with SI and "
        "POCV; zero unconstrained endpoints (or reviewed); constraints "
        "reviewed and frozen.",
        "Extraction: all nets annotated, all RC corners, fill included.",
        "IR drop: static and dynamic within budget (e.g. a few % static, "
        "~10% dynamic peak - project-specific); IR-aware timing clean.",
        "EM: power and signal EM clean at the mission-profile temperature; "
        "self-heating included where the foundry requires.",
        "Aging: timing with aged libraries or derates, if required by the "
        "product.",
        "DRC (all decks: base, antenna, density, DFM-mandatory), LVS "
        "clean, ERC clean - on the final merged GDS/OASIS.",
        "LEC: RTL vs final netlist equivalent (possibly through the "
        "chain); no aborted points.",
        "Low-power static checks clean against the final UPF.",
        "DFT: final ATPG coverage on the post-layout netlist meets target; "
        "scan and MBIST simulations with SDF pass.",
        "Gate-level simulation with SDF (selected tests) passes at the "
        "timing corners.",
        "Every waiver documented, reviewed and signed by the owner.",
    ])

    h2("Summary")
    bul([
        "Sign-off uses independent, foundry-certified golden tools and "
        "rule decks; implementation-tool results are estimates.",
        "Timing sign-off: MCMM scenarios (mode x PVT x RC corner), SI, "
        "POCV/LVF, all check types, frozen constraints.",
        "Power integrity: static and dynamic (vectorless and vector-based) "
        "IR drop, voltage-drop-aware timing, scan-capture peaks.",
        "Reliability: EM via Black's equation (our run: lifetime ~4x "
        "shorter per +20 C, J^-2 dependence), self-heating, aging "
        "(NBTI/HCI) via aged libraries.",
        "Physical verification: DRC (magic flagged width and spacing "
        "errors), LVS (netgen matched renamed netlists, located a miswire "
        "and a W error), ERC, antenna, density.",
        "LEC proves each netlist equivalent to the previous; UPF static "
        "checks verify power intent on the final netlist.",
    ])
    h2("Exercises")
    bul([
        "Why can a design fail setup at -40 C but pass at 125 C at an "
        "advanced node? Which corners must therefore be in the sign-off "
        "list?",
        "Using black.py, find the current-density limit at 125 C that "
        "gives the same lifetime as 1.5 MA/cm^2 at 85 C.",
        "Edit lay_ok.spice to create an **open** (split net7 into two "
        "nets) and run netgen. Describe the mismatch report and how you "
        "would locate the open in a layout viewer.",
        "Explain why an LVS short between VDD and a signal net produces "
        "hundreds of mismatches, and in what order you would debug a "
        "report with 3 shorts, 12 opens and 40 property errors.",
        "Which synthesis optimisations make LEC fail without guidance, "
        "and why?",
        "A block passes vectorless dynamic IR but fails at-speed scan "
        "tests on the tester. What happened and what analysis would have "
        "caught it?",
    ], ordered=True)

# =============================================================================
#                CHAPTER 19 - ECOs, TAPEOUT AND MASK MAKING
# =============================================================================
def _ch19():
    chapter("ECOs, Tapeout and Mask Making")
    p("No large chip reaches tapeout on the first pass of the flow. Bugs "
      "are found in late verification, timing fails in a corner that was "
      "added late, a customer changes a register default, or first silicon "
      "reveals a problem. An **engineering change order (ECO)** is a small, "
      "controlled modification of a design that is already implemented, "
      "done without re-running synthesis and place-and-route from scratch. "
      "This chapter covers ECOs, the tapeout process that hands the design "
      "to the foundry, and what the foundry and mask shop then do with it "
      "- the last steps under the design team's control and the most "
      "expensive ones to get wrong.")

    h2("Why ECOs, and what kinds exist")
    p("Re-running the full flow after a one-line RTL fix would take days "
      "to weeks, would reshuffle every placement and route, and would "
      "invalidate all sign-off results. An ECO touches only what must "
      "change, so most sign-off results remain valid and only incremental "
      "checks are needed. ECOs are classified by what they change and by "
      "when they happen.")
    tbl(["ECO type", "What changes", "Typical tool flow"], [
        ["Functional ECO", "Logic function (a bug fix, a feature "
         "disable, a register reset value)", "RTL fix -> re-synthesise -> "
         "ECO tool computes a minimal patch -> apply to the implemented "
         "netlist -> ECO place & route"],
        ["Timing ECO", "No function change: sizing, buffering, Vt swap, "
         "hold fixing", "Sign-off STA generates fixes (PrimeTime ECO, "
         "Tempus ECO) -> ECO route"],
        ["DRC / SI / EM ECO", "Geometry: reroute, spacing, shielding, "
         "wire widening", "Implementation tool ECO route; PV rerun"],
        ["Pre-mask ECO", "Before base layers are released; any layer may "
         "change", "Full-layer ECO; new cells can be added anywhere"],
        ["Post-mask (metal-only) ECO", "After base layers are fabricated "
         "or masks made; only metal and via masks may change", "Spare "
         "cells or ECO gate-array cells rewired with metal"],
    ], widths=[1.5, 2.6, 2.9], caption="ECO types")

    h2("Functional ECO flow")
    diagram([
        "  RTL_v1 --synth--> netlist_v1 --P&R, DFT, opt--> impl_netlist_v1 (+ layout)",
        "    |",
        "    | bug fix",
        "    v",
        "  RTL_v2 --synth--> netlist_v2   (reference: what we want)",
        "",
        "  ECO tool (Conformal ECO / Formality ECO):",
        "     compare impl_netlist_v1 (revised) against RTL_v2 or netlist_v2 (golden),",
        "     find the smallest set of cones that differ, synthesise a patch",
        "     using available cells (or only spare cells for metal-only)",
        "    |",
        "    v",
        "  patch (Tcl/Verilog) -> apply to impl DB -> ECO place (legalise new cells",
        "  near their fanin/fanout, or map to spare cells) -> ECO route",
        "    |",
        "    v",
        "  LEC: impl_netlist_v2 vs RTL_v2  |  STA  |  DRC/LVS  |  scan/ATPG update",
    ], caption="A functional ECO with a formal ECO tool")
    p("The formal ECO tools (Cadence Conformal ECO, Synopsys Formality "
      "ECO) are built on equivalence-checking engines: they identify which "
      "compare points became non-equivalent and search the implemented "
      "netlist for **rectification points** - internal nets where a small "
      "new cone restores equivalence - re-using existing logic wherever "
      "possible. A good patch for a small RTL change is typically a few to "
      "a few dozen cells. Manual ECOs (the engineer edits the netlist by "
      "hand) are still used for tiny changes, especially metal-only, but "
      "must always be followed by LEC.")
    box("warn", "PITFALL - The ECO that was not verified",
        "Every ECO must be followed by LEC against the new RTL, STA at all "
        "corners, DRC/LVS on the final layout and, for DFT-visible changes, "
        "updated ATPG. Teams under schedule pressure skip one of these "
        "'because the change is tiny' - which is precisely how a tiny "
        "change breaks scan chains or introduces a hold violation at the "
        "fast corner.")
    box("tip", "Freezing and tracking",
        "Late in a project, RTL is 'frozen' and every change becomes an "
        "ECO with a ticket: the RTL diff, the reason, the patch, and the "
        "LEC/STA/PV results. This record is invaluable when the same fix "
        "must be carried into the next chip revision or a derivative.")

    code([
        "# Illustrative Conformal-ECO-style flow (command names modelled on the tool;",
        "# not from a real run). G = golden (new RTL/netlist), R = revised (implemented)",
        "read_design  -golden  rtl_v2/*.sv          ;# or the re-synthesised netlist_v2",
        "read_design  -revised impl_netlist_v1.v",
        "set_system_mode lec",
        "add_compared_points -all",
        "compare                                   ;# -> list of non-equivalent points",
        "analyze_eco  -ecopin_dofile eco_pins.do   ;# find rectification points",
        "optimize_patch -spare_file spares.txt -workdir eco_out   ;# map patch to spares",
        "write_eco_design -newfile impl_netlist_v2.v",
    ], caption="Shape of a formal functional-ECO run (illustrative)")
    tbl(["Step", "Owner", "Deliverable"], [
        ["Bug fix in RTL", "RTL/design engineer", "RTL diff, updated "
         "tests, ECO ticket"],
        ["Patch generation", "Synthesis/ECO engineer", "Patch netlist or "
         "Tcl, LEC report: patched netlist == new RTL"],
        ["ECO implementation", "PD engineer", "ECO-placed and routed DB, "
         "changed-cell list"],
        ["Re-sign-off", "STA, PV, DFT, power owners", "Incremental STA, "
         "DRC/LVS, updated ATPG and IR/EM reports"],
    ], widths=[1.6, 2.0, 3.4], caption="Who does what in a functional ECO")

    h2("Timing ECOs")
    p("Near tapeout, the remaining timing violations are usually a handful "
      "of paths in specific corners. Sign-off STA tools can generate "
      "**timing ECO** fixes directly (PrimeTime ECO: fix_eco_timing, "
      "fix_eco_drc; Tempus ECO), because they have the accurate SI/POCV "
      "view of timing. They propose sizing, Vt swaps and buffer insertions "
      "with physical awareness (free space and legal sites from the DEF), "
      "write a change list, and the implementation tool applies it with ECO "
      "placement and routing. Several loops of 'sign-off STA -> ECO -> "
      "extract -> STA' are normal in the final weeks. Leakage and power "
      "recovery (swapping to HVT where slack allows) is done the same way.")

    h2("Metal-only ECOs, spare cells and ECO cells")
    p("After the base (FEOL) layers of the wafers are processed - or at "
      "least after their masks have been made - changing a transistor "
      "costs a new full mask set and months. But changing only upper "
      "metal and via masks costs a fraction and can be done on "
      "**held wafers**: foundries can process wafers up to a chosen metal "
      "layer and park them ('metal hold' / 'pre-metal hold'), so a metal "
      "ECO resumes from there and first-fix silicon comes back in weeks "
      "rather than months.")
    diagram([
        "   before the ECO:                           after a metal-only ECO:",
        "",
        "   A ----[AND2]---- Y  (bug: needs A&B&C)    A ----[AND2]--+",
        "   B ----[    ]                              B ----[    ]  +--[spare AND2]---- Y",
        "                                             C -------------+  (inputs were",
        "   spare AND2 (inputs tied to TIELO,                              tied off; now",
        "   output floating) 40 um away                                    rewired in M2-M5)",
        "",
        "   only metal/via masks change; transistors stay where they were",
    ], caption="Metal-only ECO using a pre-placed spare cell")
    bul([
        "**Spare cells** (Chapter 15) are placed during implementation: a "
        "mix of inverters, NAND/NOR, AOI/OAI, muxes and flops, with inputs "
        "tied off. The ECO tool maps the patch onto the nearest suitable "
        "spare cells; the distance matters for timing, so they are spread "
        "uniformly.",
        "**ECO gate-array cells (programmable fillers)**: base cells whose "
        "transistors are pre-built but unconnected, placed as filler in "
        "empty space. A metal ECO turns them into the needed gates by "
        "adding the intra-cell connections in metal. They give more "
        "flexibility than a fixed spare-cell mix at the cost of lower "
        "density and performance.",
        "Only layers from a chosen metal upward are changed ('M2+ ECO', "
        "'via3+ ECO'); the fewer layers changed, the cheaper and faster "
        "the respin - but the harder the routing of the patch.",
        "Post-mask ECOs are also the standard way to fix bugs found on "
        "first silicon in a B0/B1 stepping ('metal fix' revisions).",
    ])

    h2("The tapeout process")
    p("**Tapeout** is the release of the final layout database to the "
      "foundry (historically on magnetic tape). It is a formal process with "
      "a checklist, a data package and a sign-off meeting, typically owned "
      "by a tapeout/PD lead with representatives from every team, and it "
      "is scheduled months in advance because the foundry reserves "
      "capacity in its mask shop and fab.")
    diagram([
        "   final block DBs --> chip assembly --> final PV/STA/IR/LEC --> stream-out",
        "                                                                     |",
        "   seal ring, logos, fill, marks <---------------------------------- +",
        "                  |",
        "                  v",
        "   merged GDSII/OASIS --> foundry DRC/LVS at the foundry ('tapeout checks')",
        "                  |",
        "                  v",
        "   tapeout forms / jobview (layer list, mask options, CD bias, ID) --> mask shop",
    ], caption="Tapeout data flow")
    h3("Final checks")
    bul([
        "All sign-off criteria of Chapter 18 met or waived, on the exact "
        "database to be streamed out.",
        "Chip-level items: I/O ring and ESD connectivity, bump/pad "
        "coordinates matching the package design (Chapter 20), power "
        "domains, top-level timing between blocks, analog/IP integration "
        "reviews (Chapter 12), chip-level ERC.",
        "IP deliverables verified: every hard IP (memories, PHYs, PLLs) is "
        "the exact version the foundry and IP vendor approved, with the "
        "vendor's GDS merged, and any 'IP tag'/tracking layer requirements "
        "met.",
        "Documentation: DRC/LVS summaries, waiver list, top-level pin "
        "list, die size, layer usage.",
    ])
    h3("Stream-out: GDSII and OASIS")
    p("The final layout is written in **GDSII** (Stream format, the "
      "industry standard since the 1970s, a binary hierarchical format of "
      "cells, boundaries, paths, texts and cell references, with each shape "
      "tagged by a layer number and datatype - originally 0-63, commonly "
      "0-255, and up to the 16-bit field limit in modern tools) or **OASIS** "
      "(SEMI P39, typically several to ten times more compact thanks to "
      "repetitions and delta encoding, and free of GDSII limits such as the "
      "16-bit record length that caps the vertex count of a polygon). Advanced-node chips are delivered in "
      "OASIS because full-chip GDSII with fill can reach hundreds of GB.")
    p("A **layer map** file translates the tool's layer names to the "
      "foundry's layer/datatype numbers. Getting it wrong is catastrophic "
      "yet easy: a missing entry silently drops a layer, a swapped "
      "datatype turns drawing shapes into text or into a 'blockage' layer "
      "that is not manufactured.")
    code([
        "# layer map (format and numbers illustrative; each PDK defines its own)",
        "# tool_layer   purpose     gds_layer  gds_datatype",
        "M1             drawing     31         0",
        "M1             pin         31         2",
        "M1             label       31         1",
        "VIA1           drawing     51         0",
        "M2             drawing     32         0",
        "M2             fill        32         9",
        "PR_BOUNDARY    drawing     235        0",
    ], caption="A layer map, the Rosetta stone of stream-out")
    h3("Seal ring, logos, fill and marks")
    bul([
        "**Seal ring**: a continuous ring of all metal and via layers (and "
        "diffusion) around the die edge, grounded, that stops cracks from "
        "the dicing saw and moisture/ion ingress through the dielectric "
        "stack from reaching the circuitry. Usually a foundry-provided "
        "structure; its corners are often chamfered.",
        "**Scribe line** (saw street) outside the seal ring holds the "
        "foundry's process-control monitors and alignment marks; designers "
        "normally do not draw it.",
        "**Logos, die ID, mask revision text**: drawn in top metal (and "
        "often in every metal layer's revision field) so a die can be "
        "identified under a microscope; must obey DRC and density rules.",
        "**Dummy fill** for all layers (front-end: diffusion and poly fill; "
        "back-end: metal fill), inserted with the foundry's fill utility or "
        "deck, then included in the final DRC/extraction.",
        "**Chip-level corner and CMP structures**, alignment and overlay "
        "marks where the foundry requires them in the die.",
    ])
    h3("Foundry checks, jobview and tapeout forms")
    p("The foundry reruns DRC with its own deck version on the received "
      "database (sometimes also LVS on provided netlists), checks the data "
      "against the order (die size, layer list, frame) and reports "
      "violations back. The customer fills the **tapeout forms** (often "
      "called a jobview or tape-out information sheet): product ID, "
      "process option and metal stack, list of layers to be made into masks "
      "and their revision, die and frame dimensions, fill and optical "
      "shrink options, bump/probe information and the order quantity. "
      "Errors on the forms (wrong metal option, a mask layer left off) are "
      "as fatal as layout errors.")

    checklist("Tapeout-day checklist (condensed)", [
        "Database frozen: tagged in revision control with the exact "
        "netlist, UPF, SDC, libraries, PDK and rule-deck versions used "
        "for sign-off.",
        "Final stream-out done from the frozen DB with the approved layer "
        "map; file checksums recorded.",
        "DRC/LVS/antenna/density/ERC rerun on the streamed-out file "
        "(not on the tool database) with the foundry-released decks.",
        "Seal ring, logo, die ID and mask revision text present and DRC "
        "clean; fill inserted and included in the last extraction.",
        "IP versions and vendor sign-offs checked against the foundry's "
        "approved list; required IP tag layers present.",
        "Die size, frame, scribe width and orientation match the "
        "package drawing and the tapeout form.",
        "Tapeout forms (layer list, mask revision per layer, process "
        "options) reviewed by two people; waiver list attached.",
        "Metal-hold instructions (which wafers to park before which "
        "layer) agreed with the foundry.",
    ])
    box("expert", "Interview insight - why do masks get revision letters?",
        "Each mask layer carries its own revision code. A metal-only ECO "
        "changes, say, only M3-M6 and V2-V5, so only those masks are "
        "re-made and get new revision letters, while the base-layer masks "
        "keep theirs. Chip steppings such as A0 -> A1 (metal fix) versus "
        "A0 -> B0 (base-layer change) follow the same logic, and the die "
        "ID text drawn in each layer lets failure analysis tell which "
        "combination a given part was built with.")

    h2("Mask data preparation: OPC, RET, SRAF and fracturing")
    p("The shapes a designer draws are not the shapes that print. At "
      "advanced nodes, feature sizes are far below the 193-nm wavelength "
      "of ArF immersion lithography (and still close to the resolution "
      "limit for 13.5-nm EUV), so diffraction rounds corners, shortens line "
      "ends and makes printed width depend on neighbours. **Mask data "
      "preparation (MDP)** - performed by the foundry or mask shop - "
      "transforms the design into mask patterns that print as intended.")
    diagram([
        "   drawn (design)          after OPC (on mask)           printed on wafer",
        "",
        "   +------------+        +-+----------+-+             .------------.",
        "   |            |        | |          | |  serifs,   (              )",
        "   +------------+        +-+----------+-+  hammer-    '------------'",
        "                          ^ line-end extension  heads  (close to drawn)",
        "",
        "   isolated line + SRAFs (sub-resolution assist features, do not print):",
        "        ||        ||  |==============|  ||        ||",
        "      assist    assist   main line   assist    assist",
    ], caption="Optical proximity correction and assist features (schematic)")
    tbl(["Step", "Purpose"], [
        ["Retargeting / biasing", "Adjust drawn sizes to the target that "
         "should print (rule-based corrections)"],
        ["OPC (optical proximity correction)", "Model-based: fragment "
         "every edge and move fragments so a lithography + resist model "
         "predicts the printed contour matches the target; adds serifs and "
         "hammerheads. Full-chip OPC takes very large compute clusters"],
        ["RET (resolution enhancement techniques)", "Umbrella term: OPC, "
         "SRAFs, phase-shift masks, off-axis illumination, source-mask "
         "optimisation (SMO), multi-patterning decomposition"],
        ["SRAF insertion", "Assist features below the printing threshold "
         "make isolated features behave like dense ones, enlarging the "
         "process window"],
        ["Multi-patterning decomposition", "Split a layer into 2-4 masks "
         "(LELE, SADP/SAQP cut/mandrel masks) with colour-aware rules"],
        ["ILT (inverse lithography)", "Compute the mask as an inverse "
         "problem; curvilinear shapes, now practical with multi-beam "
         "writers"],
        ["Verification (ORC/LFD)", "Simulate the corrected mask over the "
         "process window to find hotspots before writing"],
        ["Fracturing", "Convert polygons into the primitive shapes "
         "(trapezoids/rectangles) of the mask writer's format (e.g. MEBES, "
         "VSB formats), with proximity-effect correction for the e-beam"],
    ], widths=[2.0, 5.0], caption="Mask data preparation steps")
    h3("Mask writing and mask sets")
    p("A photomask (reticle) is a quartz plate with a patterned absorber "
      "(chrome or MoSi for DUV; a multilayer reflector with an absorber "
      "for EUV), written by **electron-beam** writers (variable-shaped "
      "beam, or multi-beam for complex/curvilinear masks) or laser writers "
      "for non-critical layers. It is inspected for defects, repaired, and "
      "covered with a **pellicle** to keep particles out of focus. A scanner "
      "images the reticle at 4x reduction, so a 26 mm x 33 mm maximum "
      "field on the wafer corresponds to 104 mm x 132 mm on the mask.")
    p("A **mask set** is one mask per patterned layer (and per exposure for "
      "multi-patterned layers). The number and cost grow steeply with the "
      "node. The figures below are widely quoted industry orders of "
      "magnitude, not quotes from any foundry.")
    tbl(["Node (approx.)", "Masks in a set", "Mask set cost (order of magnitude)"], [
        ["180-130 nm", "~20-35", "~$0.1-0.3 M"],
        ["65-40 nm", "~35-45", "~$0.5-1.5 M"],
        ["28 nm", "~40-50", "~$1-3 M"],
        ["16/14/12 nm FinFET", "~60-70", "~$4-7 M"],
        ["7 nm (DUV + EUV variants)", "~70-85", "~$10-15 M"],
        ["5 nm and below", "~80-100+", "~$15-30+ M"],
    ], widths=[1.8, 1.6, 2.6], caption="Mask sets by node (rough public "
         "estimates; actual numbers vary widely by foundry, options, EUV "
         "layer count and contract)")

    h2("MPW shuttles")
    p("A **multi-project wafer (MPW)** run shares one mask set among many "
      "designs: each customer buys a slot (a few mm^{2} to tens of mm^{2}) "
      "on a shared reticle, and receives a small number of packaged or "
      "bare dies (tens to a few hundred). Foundries and brokers (for "
      "example Europractice, MOSIS historically, and foundry-run shuttle "
      "programs) schedule shuttles on fixed dates. MPWs are the standard "
      "way to prototype test chips, IP and academic designs, and "
      "open-source PDK programs have offered free or low-cost shuttles "
      "for SKY130 and GF180 designs. Limits: fixed schedule, few parts, "
      "no volume, and only the foundry's standard process options.")

    h2("Reticles, dies per wafer and cost per die")
    p("The scanner exposes the wafer one **field** at a time; a field is "
      "at most 26 mm x 33 mm (858 mm^{2}) on standard DUV/EUV scanners, "
      "which is the **reticle limit** for a single die. Small dies are "
      "arrayed several per field. The number of dies on a wafer is "
      "estimated by a classic formula that subtracts the partial dies at "
      "the edge:")
    eq(["gross dies per wafer  DPW ~= pi * (d/2)^2 / S  -  pi * d / sqrt(2 * S)",
        "",
        "d = usable wafer diameter (mm, after edge exclusion),",
        "S = die area including scribe (mm^2)",
        "",
        "yield (Murphy): Y = ((1 - exp(-A * D0)) / (A * D0))^2  A = die area (cm^2),",
        "                                                       D0 = defects/cm^2",
        "cost per good die = wafer cost / (DPW * Y)"],
       caption="Dies per wafer and cost per good die (yield models: Chapter 21)")
    code(_SRC_DPW, caption="dpw.py - gross dies per wafer by formula and by "
                           "exact counting, yield and cost per good die")
    out(_OUT_DPW, caption="Real output of python3 dpw.py")
    p("The formula agrees with exact grid counting to within a few percent "
      "(counting with the best grid offset gains a little). The economics "
      "are brutal for large dies: going from 10 x 10 mm to 20 x 20 mm "
      "quadruples area but cuts gross dies from 612 to 148 and yield from "
      "91% to 68%, so cost per good die rises about 5.5x ($27 -> $149). A "
      "reticle-limit die costs over $500 before packaging and test even "
      "with a mature defect density - one of the main arguments for "
      "chiplets (Chapter 20). The $15k wafer cost and D0 = 0.1/cm^{2} are "
      "illustrative orders of magnitude.")
    box("math", "Amortising the mask set",
        "Total cost per chip = (NRE) / volume + cost per good die + package "
        "+ test. With a $10 M mask set and 100 k units, masks add $100 per "
        "chip - far more than the 10 x 10 mm die itself. At 10 M units they "
        "add $1. This is why low-volume products use older nodes, MPWs or "
        "FPGAs (Chapter 23).")

    h2("From tapeout to first silicon")
    diagram([
        "  week 0        tapeout: GDS/OASIS + forms delivered",
        "  +1 to +2      foundry checks, jobview sign-off, fix-and-resubmit if needed",
        "  +1 to +4      MDP: OPC/RET, fracturing, mask writing, inspection, repair",
        "                (masks are written in layer order so fab can start early)",
        "  +3 to +16     wafer fabrication: hundreds of process steps; roughly",
        "                1-1.5 days per mask layer is a common rule of thumb;",
        "                'hot lots' at premium priority run faster",
        "  +12 to +20    wafer test (probe) at foundry/OSAT, dicing, packaging",
        "                (engineering samples often in a fast-turn package)",
        "  +14 to +22    first silicon on the bench -> bring-up (Chapter 22)",
        "",
        "  totals: roughly 2-4 months at mature nodes, 4-6 months at advanced nodes",
    ], caption="Typical timeline from tapeout to first silicon (orders of "
               "magnitude; strongly foundry-, node- and priority-dependent)")
    p("While the wafers are in the fab, the team is not idle: bring-up "
      "boards, test programs, silicon validation plans and software are "
      "prepared (Chapter 22), and a subset of wafers is typically held "
      "before the upper metals so that metal-only ECO fixes can be "
      "processed quickly if bring-up finds a bug.")

    h2("Summary")
    bul([
        "ECOs are minimal, controlled changes after implementation: "
        "functional (formal ECO tools compute patches), timing (sign-off STA "
        "generates fixes) and DRC/SI; every ECO needs LEC, STA and PV.",
        "Pre-mask ECOs may change any layer; post-mask ECOs change only "
        "metal/via masks, using spare cells or ECO gate-array fillers, and "
        "can use wafers held before metallisation.",
        "Tapeout: final checks, stream-out to GDSII/OASIS through a "
        "verified layer map, seal ring, logos, fill, foundry DRC and "
        "tapeout forms.",
        "Mask data preparation: retargeting, OPC, SRAFs, multi-patterning "
        "decomposition, ILT, verification, fracturing, e-beam writing.",
        "Mask sets range from ~$0.1 M at mature nodes to tens of $M at "
        "the leading edge; MPW shuttles share the cost.",
        "Dies per wafer ~ pi (d/2)^2/S - pi d/sqrt(2S); our run showed cost "
        "per good die rising 5.5x when die area quadruples from 100 to "
        "400 mm^2.",
    ])
    h2("Exercises")
    bul([
        "A bug requires changing an AND to an AND-OR function after base "
        "layers are fabricated. Which spare cells would you want nearby, "
        "and what checks must be rerun?",
        "Explain why a missing entry in the layer map might not be caught "
        "by the design team's own DRC but would be caught by LVS - or "
        "might not be caught at all.",
        "Use dpw.py to find the die size (square) at which the formula and "
        "the exact count differ by more than 10%. Why does the formula "
        "break down for large dies?",
        "Your product needs 50 k units per year. Compare total cost per "
        "unit for a 100-mm^2 die at 28 nm (mask set $2 M, wafer $3 k) "
        "versus a 40-mm^2 die at 7 nm (mask set $12 M, wafer $10 k), "
        "ignoring package and test.",
        "List three things that can go wrong on tapeout forms and their "
        "consequence.",
    ], ordered=True)


CHAPTERS = [_ch15, _ch16, _ch17, _ch18, _ch19]


# =============================================================================
def part4():
    part("Implementation and Sign-off",
         "From a floorplanned block to a manufacturable mask set: placement "
         "and optimisation, clock tree synthesis, routing with signal "
         "integrity and DFM, the sign-off checks that decide whether a chip "
         "may be taped out, and the ECO, tapeout and mask-making steps that "
         "turn a database into physical photomasks.")
    for ch in CHAPTERS:
        ch()
