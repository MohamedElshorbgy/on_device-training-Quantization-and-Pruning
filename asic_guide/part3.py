"""Part III - Power, Mixed-Signal and Physical Design Setup (Chapters 11-14).

Real runs shown with out() in this part:
  * Python parsing of the real SkyWater SKY130 HD Liberty file
    (sky130_fd_sc_hd__tt_025C_1v80.lib) for low-power special cells.
  * Yosys 0.33 synthesis of a small MAC/register-file block against the same
    Liberty file (with and without the low-power cells excluded).
  * Python (numpy) models: DVFS energy per operation, charge-pump PLL loop
    parameters, HBM discharge waveform, die-size estimate, SKY130 tech-LEF
    layer summary and a static IR-drop solve of a power mesh.
  * Icarus Verilog 12 run of a real-number (RNM) power-on-reset model.
UPF, SDC, Tcl, DEF and MMMC scripts are shown as examples and were not run
through a commercial tool.
"""

from asic_guide.common import *  # noqa: F401,F403


def _eqa(lines, caption=None):
    """eq() centres each line; pad them to one width so columns stay aligned."""
    w = max(len(l) for l in lines)
    eq([l.ljust(w) for l in lines], caption)


# =============================================================================
#            CHAPTER 11 - LOW-POWER DESIGN AND POWER INTENT (UPF)
# =============================================================================
def _ch11():
    chapter("Low-Power Design and Power Intent (UPF)", newpage=False)
    p("Power is no longer a number you look at after timing closes. For a "
      "phone SoC it sets battery life and the thermal envelope; for a data-"
      "centre accelerator it sets how many chips fit in a rack and what the "
      "electricity bill is; for an IoT sensor it decides whether the product "
      "runs for ten years on a coin cell or for ten weeks. In every modern "
      "ASIC, power is a first-class constraint that shapes the architecture "
      "(Chapter 5), the RTL (Chapter 6), the library choice (Chapter 4) and "
      "the whole back end (Chapters 13-18).")
    p("The companion RTL Design guide showed how to write clock-gating and "
      "operand-isolation RTL and gave a first UPF file. This chapter takes the "
      "implementation engineer's view: where every milliwatt comes from, how "
      "power is estimated at each stage and how accurate each estimate is, the "
      "full menu of techniques from architecture down to body bias, and the "
      "**power intent** file (UPF, IEEE 1801) in enough depth to write one for "
      "a multi-voltage, power-gated SoC and to follow it through simulation, "
      "synthesis, place-and-route and sign-off.")

    # ------------------------------------------------------------------------
    h2("Where the power goes")
    p("Total power splits into **dynamic** power (charging and discharging "
      "capacitance, plus short-circuit current while both networks conduct "
      "during a transition) and **static** power (leakage that flows whether "
      "or not anything toggles). Chapter 2 derived each term from device "
      "physics; here are the forms an implementation engineer uses daily.")
    _eqa(["P_total = P_switching + P_internal + P_leakage",
        "P_switching = alpha * C_load * V_DD^2 * f      (net/pin capacitance, 'switching power')",
        "P_internal  = sum over toggles of E_int(slew, load) * toggle_rate",
        "              (short-circuit + cell-internal node charging, from Liberty tables)",
        "P_leakage   = V_DD * (I_sub + I_gate + I_GIDL + I_junction)",
        "I_sub ~ exp((V_GS - V_th) / (n * v_T)),  v_T = kT/q = 26 mV at 300 K"],
       "Equation 11.1 - The three power components as reported by power tools. "
       "'alpha' is the activity factor (toggles per clock), f the clock "
       "frequency.")
    tbl(["Component", "Typical share", "Grows with", "Main levers"],
        [["Switching (net)", "30-50% of dynamic", "activity, wire C, V^2, f",
          "clock gating, data gating, lower V, shorter wires, low-C routing"],
         ["Internal (cell)", "30-50% of dynamic", "slew, activity, flop count",
          "fewer flops, good slews, multi-bit flops, gating"],
         ["Clock network", "20-45% of dynamic power",
          "flop count, tree depth, f", "clock gating, CTS with fewer buffers, "
          "multi-bit flops, lower clock swing"],
         ["Leakage", "a few % (HVT-heavy, cold) to over 30% (LVT-heavy, hot)",
          "temperature (exponential), low Vt, V_DD (DIBL), area",
          "multi-Vt, power gating, body bias, lower V_DD"]],
        widths=[18, 22, 28, 32], bold_first=True,
        caption="Table 11.1 - Power components and their levers. Shares vary "
                "widely with design style and node; the clock is often the "
                "single biggest consumer in a synchronous design.")
    box("intuit", "Why V^2 dominates every strategy",
        "Frequency enters dynamic power linearly, but achievable frequency "
        "itself falls roughly linearly with voltage above threshold. Scaling "
        "V and f together therefore reduces dynamic power roughly with the "
        "**cube** of V, and energy per operation (power / f) with the "
        "**square**. That single fact motivates DVFS, multi-voltage domains, "
        "near-threshold computing and 'race-to-idle' vs 'slow-and-steady' "
        "debates.")

    # ------------------------------------------------------------------------
    h2("Power analysis flow")
    p("A power number is only as good as its **activity** and its "
      "**parasitics**. As a project progresses, both become more accurate, "
      "and the power team (often part of the physical-design or "
      "methodology group, working with the architects) re-runs the analysis "
      "at each stage.")
    diagram([
        " stage          netlist            parasitics          activity          accuracy",
        " -------------  -----------------  ------------------  ----------------  ---------",
        " architecture   spreadsheet model  none                use-case profile  +-50%",
        " RTL            RTL (+ quick map)  wire-load/none      RTL sim (FSDB)    +-20-30%",
        " synthesis      mapped netlist     wire-load / est.    SAIF / FSDB       +-15-20%",
        " post-place     placed netlist     virtual route       SAIF / vectorless +-10-15%",
        " sign-off       routed netlist     extracted SPEF      gate-level FSDB   +-5-10%",
        "",
        "  RTL/gate sim --> FSDB/VCD (per-cycle toggles) --+",
        "               \\-> SAIF (toggle counts, T0/T1)  --+--> power tool --> average,",
        "  vectorless (set_switching_activity defaults) ----+    (PrimePower,    peak, per-",
        "  netlist + Liberty (power tables) + SPEF ----------+     Voltus, Joules instance,",
        "                                                        PowerArtist)   per-domain",
    ], "Figure 11.1 - Power estimation through the project. Accuracy ranges "
       "are typical rules of thumb, not guarantees; the dominant error is "
       "almost always unrepresentative activity, not the tool.")
    h3("Activity sources")
    bul(["**Vectorless** (statistical): the tool propagates default toggle "
         "rates and static probabilities from the inputs (e.g. 10-20% "
         "toggle rate on data, 100%/2 per cycle on clocks). Fast and needs no "
         "testbench, but can be wildly off for control-dominated logic. Used "
         "early and for power-grid design where a pessimistic assumption is "
         "acceptable.",
         "**SAIF** (Switching Activity Interchange Format): per-net toggle "
         "count (TC) and time at 0/1 (T0/T1) over a window. Small files, "
         "gives accurate **average** power, cannot give peak or cycle-by-cycle "
         "power.",
         "**FSDB/VCD** (waveforms): every transition with a time stamp; enables "
         "**time-based** (peak, per-cycle) power and the vectors used for "
         "**dynamic IR drop** (Chapter 18). Big files: pick short, meaningful "
         "windows.",
         "**Emulation-based** power: an emulator (Palladium, ZeBu, Veloce) runs "
         "real software for billions of cycles; activity is summarised per "
         "window to find the power hot-spots, then a short FSDB window is "
         "extracted for detailed analysis."])
    h3("Average vs peak, and which scenario to sign off")
    p("Average power drives battery life and the thermal design (with "
      "time constants of milliseconds to seconds); **peak** power and "
      "**di/dt** drive the package, the voltage regulator and the power grid "
      "(time constants of nanoseconds). They need different vectors: average "
      "power wants a representative workload (e.g. video playback, a "
      "benchmark), while peak wants the worst sustainable burst (all cores "
      "running a power virus, a DFT scan-shift pattern) and the worst "
      "**step** (from idle to full activity in a few cycles). Scan shift is "
      "notorious: with all flops toggling at 50% it can draw several times "
      "functional power, which is why DFT uses low-power shift patterns and "
      "slower shift clocks (Chapter 10).")
    box("warn", "PITFALL: a 'power number' without its conditions",
        "'The block is 120 mW' means nothing unless you state the corner "
        "(process, voltage, temperature), the activity source and scenario, "
        "the frequency, and whether it is average or peak. Leakage at the "
        "fast corner and 125 C can be 10-50x the typical value at 25 C; a "
        "dynamic number at typical voltage can be 30% below the worst case "
        "at high voltage. Always quote a power number with its PVT, mode "
        "and activity.")
    h3("Early estimation")
    p("Before RTL exists, the architect estimates power from similar blocks "
      "(mW per MHz per mm^2 or energy per operation), from the gate count and "
      "an average energy per gate toggle, and from memory access counts "
      "multiplied by energy per access from the memory compiler datasheet. "
      "RTL power tools (e.g. PowerArtist, Joules, PrimePower RTL) then do a "
      "quick internal synthesis and give per-module power with 20-30% "
      "accuracy, which is enough to decide where to add clock gating.")

    # ------------------------------------------------------------------------
    h2("Techniques by level of abstraction")
    p("The higher the level, the bigger the saving and the cheaper it is to "
      "apply early. A rough rule quoted in many low-power courses: "
      "architecture and system decisions can save 10x or more, RTL "
      "techniques 20-50%, and gate/physical optimisation 10-20%.")
    tbl(["Level", "Technique", "What it saves", "Cost / risk"],
        [["System", "DVFS, adaptive voltage scaling (AVS), race-to-idle, "
          "power states (sleep, retention, off)", "dynamic (V^2) and leakage",
          "PMIC/regulator, software governor, characterisation at many "
          "V/f points"],
         ["Architecture", "parallelism/pipelining at lower V, specialised "
          "accelerators, memory hierarchy (fewer DRAM accesses), data "
          "compression, near-memory compute", "dynamic, often by 10x+",
          "area, design effort"],
         ["RTL", "clock gating (module/register level), operand isolation, "
          "memory chip-select/light-sleep gating, glitch reduction, "
          "one-hot vs binary encoding", "dynamic 20-50%",
          "gating logic timing, DFT observability"],
         ["Synthesis", "automatic clock-gate insertion, multi-Vt "
          "assignment, multi-bit flops, low-power mapping", "dynamic and "
          "leakage 10-30%", "timing closure, hold fixes"],
         ["Implementation", "power gating (header/footer switches), "
          "retention, multi-voltage domains, level shifters, isolation",
          "leakage 90%+ in off domains", "area 5-15%, verification "
          "complexity, rush current, wake-up latency"],
         ["Device/circuit", "body bias (forward/reverse), high-Vt / long "
          "channel cells, SRAM retention voltage", "leakage", "bias "
          "generators, triple wells, limited in FinFET"]],
        widths=[14, 36, 20, 30], bold_first=True,
        caption="Table 11.2 - The low-power toolbox by abstraction level.")

    h3("System and architecture: DVFS, AVS and parallelism")
    p("**Dynamic voltage and frequency scaling (DVFS)** chooses an operating "
      "performance point (OPP) - a (V, f) pair - according to the load. The "
      "hardware must be characterised and signed off at every OPP (each is "
      "an STA corner), the PLL must re-lock or a glitch-free clock switch is "
      "needed, and the voltage must ramp **before** the frequency goes up and "
      "**after** it comes down. **Adaptive voltage scaling (AVS)** closes the "
      "loop: on-die monitors (ring oscillators, critical-path replicas, "
      "timing-error detectors) tell the regulator how much margin the "
      "particular die at its current temperature really has, recovering the "
      "guard band that a fixed OPP table must keep for slow silicon. "
      "**Parallelism**: two copies of a unit at half the frequency can run "
      "at a lower voltage; for the same throughput the energy per operation "
      "falls with V^2 while area doubles. This is why GPUs and AI "
      "accelerators are wide and relatively slow.")
    p("The following model uses an alpha-power-law delay (f proportional to "
      "(V - V_th)^alpha / V) and a leakage current that falls exponentially "
      "with V (DIBL) to show the energy per operation of one block across "
      "the voltage range. The parameters are illustrative, not from a "
      "specific process.")
    code(r'''# dvfs.py - energy per operation vs supply voltage (alpha-power-law delay model)
import numpy as np
C_eff, Vth, alpha = 50e-12, 0.35, 1.3   # F switched per op, V, velocity-sat. exponent
f_nom, I_leak0 = 1.0e9, 5e-3            # 1 GHz and 5 mA leakage at 0.90 V
def fmax(V):  k = f_nom / ((0.9 - Vth)**alpha / 0.9); return k * (V - Vth)**alpha / V
def ileak(V): return I_leak0 * np.exp((V - 0.9) / 0.3)
for V in [0.90, 0.80, 0.70, 0.60, 0.55, 0.50, 0.45, 0.42, 0.40]:
    f = fmax(V); Ed = C_eff * V**2 * 1e12; El = V * ileak(V) / f * 1e12
    ...                                           # print P_dyn, P_leak, E/op
Vs = np.linspace(0.37, 0.9, 2000)
E  = C_eff*Vs**2*1e12 + Vs*ileak(Vs)/fmax(Vs)*1e12   # pJ/op
i  = np.argmin(E)                                     # minimum-energy point''',
         "Listing 11.1 - Core of the DVFS energy model (printing lines "
         "elided).")
    out([" Vdd   fmax    P_dyn    P_leak   E_dyn/op  E_leak/op  E_total/op  leak%",
         " [V]   [MHz]   [mW]     [mW]     [pJ]      [pJ]       [pJ]",
         "0.90    1000    40.50    4.500     40.50      4.50      45.00      10%",
         "0.80     867    27.73    2.866     32.00      3.31      35.31       9%",
         "0.70     714    17.50    1.797     24.50      2.52      27.02       9%",
         "0.60     538     9.69    1.104     18.00      2.05      20.05      10%",
         "0.55     439     6.64    0.856     15.13      1.95      17.07      11%",
         "0.50     332     4.16    0.659     12.50      1.98      14.48      14%",
         "0.45     218     2.21    0.502     10.12      2.30      12.43      19%",
         "0.42     147     1.30    0.424      8.82      2.89      11.71      25%",
         "0.40     100     0.80    0.378      8.00      3.79      11.79      32%",
         "minimum-energy point: V = 0.412 V, f = 127 MHz, E = 11.65 pJ/op",
         "energy saving vs 0.90 V: 3.9x; speed penalty: 7.9x"],
        "Output of dvfs.py (python3 + numpy). Power falls 50x from 0.9 V to "
        "0.4 V, but energy per operation only 3.9x, and below about 0.41 V "
        "it rises again because leakage integrates over ever longer cycles.")
    p("Three lessons generalise. First, lowering V pays off quadratically "
      "only while dynamic energy dominates. Second, there is a "
      "**minimum-energy point** near threshold where leakage energy per "
      "operation starts to win; running slower than that wastes energy. "
      "Third, if the work has a deadline and the chip can be power-gated "
      "when idle, 'race to idle' at high V can beat 'slow and steady' only "
      "when leakage in the active state is large and the idle state is "
      "truly off - which is exactly the trade-off OS power governors "
      "evaluate. (The alpha-power law is inaccurate close to threshold; "
      "real near-threshold design uses characterised libraries.)")

    h3("RTL: clock gating, operand isolation, memory gating")
    p("Clock gating removes the clock from registers whose value will not "
      "change. Synthesis tools infer an **integrated clock-gating cell** "
      "(ICG: a latch plus an AND, glitch-free by construction) from "
      "enable-style RTL, typically for groups of at least 3-8 flops; "
      "architects add coarse module-level gates by hand. Operand isolation "
      "holds the inputs of an expensive datapath (multiplier, adder tree) "
      "constant when its result is not used. Memories are the other big "
      "win: drive chip-select only when accessing, and use the memory's "
      "**light-sleep** (periphery off), **deep-sleep** (array at retention "
      "voltage) and **shut-down** pins from the power controller. The "
      "coding details are in the companion RTL Design guide; what matters "
      "downstream is that every ICG is a timing endpoint (the enable has a "
      "setup check to the gating latch - the 'clock gating check'), sits in "
      "the clock tree and must be scan-controllable (test enable pin) "
      "(Chapters 9, 10 and 16).")

    h3("Implementation: multi-Vt, power gating and multi-voltage")
    bul(["**Multi-Vt**: libraries come in several threshold flavours (e.g. "
         "ULVT, LVT, SVT, HVT; on the order of 2-4x leakage change and "
         "10-30% speed change per step). Synthesis and P&R start with "
         "high-Vt everywhere it meets timing and swap to lower Vt only on "
         "critical paths. Many teams cap the LVT/ULVT fraction (e.g. a few "
         "percent of cells) as a leakage budget.",
         "**Power gating**: a switch transistor in series with the supply - "
         "a PMOS **header** between the real VDD and a virtual VDD, or an NMOS "
         "**footer** between virtual VSS and VSS - disconnects a whole domain. "
         "Headers are more common (easier with a common ground and "
         "standard-cell rows). Leakage of the domain drops by 10-100x to that "
         "of the switches themselves.",
         "**Retention**: a retention flop has a small always-on 'balloon' "
         "latch on the always-on supply that saves the state before power-"
         "down and restores it after power-up, so software does not need to "
         "save/restore registers. It costs area (often 20-40% bigger than a "
         "plain flop) and an always-on supply route.",
         "**Isolation**: outputs of a powered-down domain float to unknown "
         "values; an isolation cell (an AND/OR clamp on an always-on supply) "
         "forces them to a known safe value while the domain is off.",
         "**Level shifters**: a signal crossing from a low-voltage to a "
         "high-voltage domain cannot fully turn off the receiver's PMOS, "
         "causing crowbar current and slow edges, so it needs a level "
         "shifter (L->H is mandatory; H->L is often just a buffer on the low "
         "supply, but many methodologies insert shifters both ways). "
         "Combined **enable level shifters** also isolate.",
         "**Multi-voltage domains**: each voltage island has its own supply "
         "and can be at a different, fixed or DVFS-scaled voltage; SRAM "
         "arrays often have a separate, higher, rail (VDDM) because bit cells "
         "need more voltage than logic for stability.",
         "**Body bias**: reverse body bias (RBB) raises Vt and cuts leakage "
         "in standby; forward body bias (FBB) lowers Vt for speed. Very "
         "effective in bulk planar and especially FD-SOI (wide bias range "
         "through the thin BOX); weak in FinFET, where the fin is poorly "
         "coupled to the substrate."])
    diagram([
        "         VDD (real, always on from the package)",
        "   ======+=======================+=====================+=========",
        "         |                       |                     |",
        "      |--+  sleep_b (weak)    |--+  sleep_b (strong)   |   always-on",
        "  o---|  PMOS header       o--|  PMOS header           |   buffer/ICG",
        "      |--+  (few, small)      |--+  (many, large)      |   (KAPWR pin)",
        "         |                       |                     |",
        "   ------+----- VDD_SW (virtual, switched supply) -----+----------",
        "         |           |           |          |",
        "      [logic]     [logic]    [retention  [isolation   <- iso cells",
        "                              flop:        cell: on AON   sit in the",
        "                              main latch   supply, clamps  receiving",
        "                              on VDD_SW,   output to 0/1)  (parent/",
        "                              balloon on                   AON) domain",
        "                              VDD real]",
        "   =====================================================  VSS",
    ], "Figure 11.2 - A header-switched domain: weak switches turn on first "
       "to limit in-rush current, strong switches after; retention and "
       "always-on cells need a connection to the real (unswitched) supply.")

    h3("Real low-power cells in an open library")
    p("Low-power cells are ordinary Liberty cells with extra attributes that "
      "tell the tools what they are. The following script reads the real "
      "SkyWater SKY130 high-density library (typical corner, 25 C, 1.80 V) "
      "and prints the special cells next to a plain inverter and flip-flop.")
    code(r'''# lp_cells.py - find low-power special cells in the SKY130 HD Liberty file
import re
txt = open("sky130_fd_sc_hd__tt_025C_1v80.lib").read()
def cell_block(name):                     # brace-matched text of one cell group
    i = txt.index('cell ("%s")' % name); j = txt.index("{", i); d = 0
    for k in range(j, len(txt)):
        d += (txt[k] == "{") - (txt[k] == "}")
        if d == 0: return txt[i:k]
for c in ["inv_1", "dfxtp_1", "dlclkp_1", "sdlclkp_1", "lpflow_inputiso0p_1", ...]:
    b = cell_block("sky130_fd_sc_hd__" + c)
    # print area, cell_leakage_power and any of: clock_gating_integrated_cell,
    # is_isolation_cell, is_level_shifter, plus the output function and the
    # primary_power pg_pins when there is more than one''', "Listing 11.2 - "
         "Liberty attribute scan (abridged).")
    out(["cell                         area leak_nW  special attribute        function [power pins]",
         "inv_1                        3.75  0.0053  -                        (!A)",
         "dfxtp_1                     20.02  0.0084  -                        IQ",
         "dlclkp_1                    17.52  0.0088  icg=posedge              -",
         "sdlclkp_1                   18.77  0.0104  icg=posedge_precontrol   -",
         "lpflow_inputiso0p_1          7.51  0.0053  isolation_cell=true      (!SLEEP&A)",
         "lpflow_inputiso1n_1          7.51  0.0036  isolation_cell=true      (A) | (!SLEEP_B)",
         "lpflow_isobufsrc_1           6.26  0.0022  isolation_cell=true      (A&!SLEEP)",
         "lpflow_lsbuf_lh_isowell_4   40.04  0.0112  level_shifter=true       (A) [LOWLVPWR,VPWR]",
         "lpflow_clkbufkapwr_1         3.75  0.0012  -                        (A) [KAPWR,VPWR]",
         "lpflow_decapkapwr_4          5.00  0.0032  -                        - [KAPWR,VPWR]",
         "decap_4                      5.00  0.0032  -                        -",
         "tapvpwrvgnd_1              (not in timing library)"],
        "Output of lp_cells.py on the real SKY130 HD Liberty (area in um^2, "
        "leakage in nW as declared by leakage_power_unit; icg=posedge is the "
        "attribute value latch_posedge).")
    bul(["`dlclkp_1` is the ICG: `clock_gating_integrated_cell : "
         "latch_posedge` tells synthesis it may use it for clock gating; "
         "`sdlclkp` adds a test-enable (precontrol) input for scan.",
         "The `lpflow_inputiso*` and `isobufsrc` cells carry "
         "`is_isolation_cell : true` and pins flagged "
         "`isolation_cell_enable_pin` - the tools only use them where UPF asks "
         "for isolation.",
         "The level shifter has two primary power pins (LOWLVPWR for the input "
         "side, VPWR for the output side), `level_shifter_type : LH` and "
         "`input_voltage_range` / `output_voltage_range` (1.2-2.1 V here).",
         "`kapwr` cells have a **keep-alive** power pin (KAPWR): they sit "
         "physically inside a switched domain but are powered from the "
         "always-on rail - used for always-on clock buffers and feed-throughs.",
         "The tap cell is a physical-only cell (in the LEF, not in the timing "
         "library); Chapter 14 places it."])
    box("warn", "PITFALL: letting synthesis use special cells as logic",
        "Synthesising a small MAC/register-file block with Yosys against the "
        "full SKY130 library, the mapper happily used 45 "
        "`lpflow_isobufsrc_1` and 5 `lpflow_inputiso1p_1` cells as ordinary "
        "AND gates (real run, Chapter 13 shows the design). Functionally "
        "correct, but the P&R and low-power checkers then see 'isolation "
        "cells' that no UPF strategy asked for, and some of these cells have "
        "unusual power pins. Commercial flows mark such cells `dont_use` (and "
        "`dont_touch` where inserted); open flows use a trimmed library. The "
        "same applies to clock buffers/inverters in data paths, delay cells, "
        "and any cell the foundry lists as 'not for synthesis'.")

    # ------------------------------------------------------------------------
    h2("UPF (IEEE 1801) in depth")
    p("RTL describes function; **UPF** describes power intent: which "
      "supplies exist, which logic is powered by which supply, which domains "
      "can switch off or change voltage, and what protection is needed at "
      "every crossing. It is a Tcl-based format standardised as IEEE 1801 "
      "(UPF 1.0 was the Accellera version; IEEE 1801-2009 is UPF 2.0, -2013 "
      "UPF 2.1, -2015 UPF 3.0, -2018 UPF 3.1, with a later revision "
      "published since). Cadence's older CPF format expressed the same "
      "concepts; most flows today are UPF. Tool support lags the standard, "
      "so teams pin a version (commonly 2.1 or 3.x subsets) and a coding "
      "style guide.")
    h3("The object model")
    diagram([
        "  supply PORT (pin of the design/top)   VDD_AON   VDD_CPU   VDD_ACC   VSS",
        "        |                                  |         |         |       |",
        "  supply NET  (wire inside the scope)   VDD_AON   VDD_CPU   VDD_ACC   VSS",
        "        |                                  |         |  switch  |       |",
        "        |                                  |         +--[SW]-- VDD_CPU_SW",
        "  supply SET (named bundle of functions)   SS_AON = {power VDD_AON, ground VSS}",
        "                                           SS_CPU = {power VDD_CPU_SW, ground VSS}",
        "                                           SS_ACC = {power VDD_ACC, ground VSS}",
        "        |",
        "  POWER DOMAIN (instances + primary supply set + strategies)",
        "      PD_TOP (AON, 0.8 V) --- PD_CPU (switchable, 0.7/0.9 V DVFS)",
        "                          \\-- PD_ACC (0.6 V fixed, switchable)",
        "        |",
        "  STRATEGIES on the domain boundary: isolation, level shifter, retention",
        "  POWER STATES: legal combinations of supply states (the 'PST')",
    ], "Figure 11.3 - UPF objects. Strategies are written against domains and "
       "supply sets, never against individual cells; the tools choose and "
       "place the cells.")
    tbl(["Command", "Purpose", "Key options"],
        [["`upf_version`, `set_scope`, `load_upf`", "Version declaration, "
          "hierarchy scope, include a block UPF", "`load_upf blk.upf -scope "
          "u_blk` for hierarchical UPF"],
         ["`create_power_domain`", "Group instances with a primary supply",
          "`-elements`, `-include_scope`, `-supply {primary SS}`, "
          "`-supply {default_isolation SS}`, `-atomic`"],
         ["`create_supply_port / net`, `connect_supply_net`", "Supply "
          "topology", "`-direction in/out`, `-domain`, `-resolve` (rare)"],
         ["`create_supply_set`", "Bundle of power/ground (and n/p-well) "
          "functions", "`-function {power NET}`, `-function {ground NET}`, "
          "`-update`"],
         ["`create_power_switch`", "Switch topology, control and ack",
          "`-input_supply_port`, `-output_supply_port`, `-control_port`, "
          "`-ack_port`, `-on_state`, `-off_state`"],
         ["`set_isolation`", "Where and how to clamp", "`-applies_to "
          "inputs/outputs/both`, `-clamp_value 0/1/latch`, "
          "`-isolation_signal`, `-isolation_sense`, `-location self/parent`, "
          "`-diff_supply_only`, `-source/-sink`"],
         ["`set_level_shifter`", "Voltage-crossing rules", "`-rule "
          "low_to_high/high_to_low/both`, `-location`, `-threshold`, "
          "`-no_shift`"],
         ["`set_retention` (+ `set_retention_elements`)", "Which state is "
          "kept, with what controls", "`-retention_supply_set`, "
          "`-save_signal`, `-restore_signal`, `-elements`"],
         ["`add_power_state` / legacy `create_pst`, `add_pst_state`", "Legal "
          "power states of supply sets and domains", "`-supply_expr`, "
          "`-logic_expr`, `-simstate`"],
         ["`map_retention_cell`, `use_interface_cell`, `map_power_switch`",
          "Constrain which library cells implement a strategy",
          "`-lib_cells`, `-strategy`"],
         ["`set_port_attributes`, `set_design_attributes`", "Boundary "
          "information for block-level UPF", "`-driver_supply`, "
          "`-receiver_supply`, `-is_analog`"]],
        widths=[27, 30, 43], bold_first=True,
        caption="Table 11.3 - The UPF commands you will actually write. "
                "Option names changed between versions (UPF 3.0 prefers "
                "`-isolation_supply`/`-retention_supply`); follow the version "
                "your tools accept.")

    h3("A complete example: three domains, DVFS and power gating")
    p("The SoC below has an always-on top domain at 0.8 V (power "
      "controller, interrupt logic, wake-up timers), a CPU domain that runs "
      "at 0.7 or 0.9 V (DVFS) and can be switched off with state retention, "
      "and an accelerator domain at a fixed 0.6 V that can be switched off "
      "without retention. The PMU (power management unit) in the AON domain "
      "drives all controls.")
    code(r'''## ===== soc.upf : IEEE 1801 (UPF 2.1 style) ================================
upf_version 2.1
set_scope /
set_design_top soc_top

## ---- 1. supply ports and nets (top level) --------------------------------------
foreach s {VDD_AON VDD_CPU VDD_ACC VSS} {
    create_supply_port $s -direction in
    create_supply_net  $s
    connect_supply_net $s -ports $s
}
create_supply_net VDD_CPU_SW          ;# switched (virtual) CPU supply
create_supply_net VDD_ACC_SW          ;# switched (virtual) ACC supply

## ---- 2. supply sets --------------------------------------------------------------
create_supply_set SS_AON -function {power VDD_AON}    -function {ground VSS}
create_supply_set SS_CPU -function {power VDD_CPU_SW} -function {ground VSS}
create_supply_set SS_CPU_RET -function {power VDD_CPU} -function {ground VSS}
create_supply_set SS_ACC -function {power VDD_ACC_SW} -function {ground VSS}

## ---- 3. power domains ----------------------------------------------------------------
create_power_domain PD_TOP -include_scope -supply {primary SS_AON}
create_power_domain PD_CPU -elements {u_cpu} -supply {primary SS_CPU}
create_power_domain PD_ACC -elements {u_acc} -supply {primary SS_ACC}''',
         "Listing 11.3a - Supplies and domains.")
    code(r'''## ---- 4. power switches (headers placed in the switched domains) -------------------
create_power_switch SW_CPU -domain PD_CPU \
    -input_supply_port  {vin  VDD_CPU}     -output_supply_port {vout VDD_CPU_SW} \
    -control_port       {en   u_pmu/cpu_pwr_en} \
    -ack_port           {ack  u_pmu/cpu_pwr_ack} \
    -on_state  {ON  vin {en}}  -off_state {OFF {!en}}
create_power_switch SW_ACC -domain PD_ACC \
    -input_supply_port  {vin  VDD_ACC}     -output_supply_port {vout VDD_ACC_SW} \
    -control_port       {en   u_pmu/acc_pwr_en} \
    -ack_port           {ack  u_pmu/acc_pwr_ack} \
    -on_state  {ON  vin {en}}  -off_state {OFF {!en}}
map_power_switch SW_CPU -domain PD_CPU -lib_cells {HDRSW_X4}

## ---- 5. isolation: outputs of each switchable domain, cells in the parent (AON) --
set_isolation iso_cpu -domain PD_CPU -applies_to outputs \
    -isolation_supply_set SS_AON -clamp_value 0 \
    -isolation_signal u_pmu/cpu_iso_en -isolation_sense high -location parent
set_isolation iso_cpu_irqn -domain PD_CPU -elements {u_cpu/irq_n} \
    -isolation_supply_set SS_AON -clamp_value 1 \
    -isolation_signal u_pmu/cpu_iso_en -isolation_sense high -location parent
set_isolation iso_acc -domain PD_ACC -applies_to outputs \
    -isolation_supply_set SS_AON -clamp_value 0 \
    -isolation_signal u_pmu/acc_iso_en -isolation_sense high -location parent''',
         "Listing 11.3b - Switches and isolation. `HDRSW_X4` stands for "
         "whatever header cell the library provides. Note the separate "
         "strategy for the active-low interrupt, which must clamp to 1.")
    code(r'''## ---- 6. level shifters: every crossing between different voltages ---------------
set_level_shifter ls_cpu_out -domain PD_CPU -applies_to outputs -rule both \
    -location parent
set_level_shifter ls_cpu_in  -domain PD_CPU -applies_to inputs  -rule both \
    -location self
set_level_shifter ls_acc_out -domain PD_ACC -applies_to outputs -rule low_to_high \
    -location parent
set_level_shifter ls_acc_in  -domain PD_ACC -applies_to inputs  -rule high_to_low \
    -location self

## ---- 7. retention: architectural state of the CPU only ----------------------------
set_retention ret_cpu -domain PD_CPU -retention_supply_set SS_CPU_RET \
    -elements {u_cpu/u_regfile u_cpu/u_csr u_cpu/u_pc} \
    -save_signal    {u_pmu/cpu_save    high} \
    -restore_signal {u_pmu/cpu_restore high}
map_retention_cell ret_cpu -domain PD_CPU -lib_cells {RDFFX1 RDFFX2}''',
         "Listing 11.3c - Level shifting and retention. Isolation cells at the "
         "parent location for a crossing that is also a voltage change are "
         "usually merged into **enable level shifters**.")
    code(r'''## ---- 8. power states ---------------------------------------------------------------
add_power_state SS_AON -state ON   {-supply_expr {power == `{FULL_ON, 0.80}}}
add_power_state SS_CPU -state HV   {-supply_expr {power == `{FULL_ON, 0.90}}}
add_power_state SS_CPU -state LV   {-supply_expr {power == `{FULL_ON, 0.70}}}
add_power_state SS_CPU -state OFF  {-supply_expr {power == `{OFF}} -simstate CORRUPT}
add_power_state SS_ACC -state ON   {-supply_expr {power == `{FULL_ON, 0.60}}}
add_power_state SS_ACC -state OFF  {-supply_expr {power == `{OFF}} -simstate CORRUPT}

add_power_state PD_TOP -state RUN_FAST {-logic_expr {SS_CPU == HV  && SS_ACC == ON}}
add_power_state PD_TOP -state RUN_ECO  {-logic_expr {SS_CPU == LV  && SS_ACC == ON}}
add_power_state PD_TOP -state CPU_ONLY {-logic_expr {SS_CPU == HV  && SS_ACC == OFF}}
add_power_state PD_TOP -state SLEEP    {-logic_expr {SS_CPU == OFF && SS_ACC == OFF}}
## (any combination not listed, e.g. CPU OFF with ACC ON, is illegal)''',
         "Listing 11.3d - Power states. Static checkers compute every legal "
         "pair of (driver, receiver) states from this table and verify that "
         "each crossing has the isolation and shifting it needs.")
    p("The legacy **power state table** (PST) expresses the same information "
      "as a matrix over supply ports. You will still meet it in older "
      "IP deliveries and in some tool flows:")
    code(r'''add_port_state VDD_AON -state {ON 0.80}
add_port_state VDD_CPU -state {HV 0.90} -state {LV 0.70} -state {OFF off}
add_port_state VDD_ACC -state {ON 0.60} -state {OFF off}
create_pst soc_pst -supplies            {VDD_AON VDD_CPU VDD_ACC}
add_pst_state RUN_FAST -pst soc_pst -state {ON      HV      ON }
add_pst_state RUN_ECO  -pst soc_pst -state {ON      LV      ON }
add_pst_state CPU_ONLY -pst soc_pst -state {ON      HV      OFF}
add_pst_state SLEEP    -pst soc_pst -state {ON      OFF     OFF}''',
         "Listing 11.4 - The same states as a legacy PST (on real supply "
         "ports; switched nets inherit their state from the switch).")
    tbl(["Crossing (driver -> receiver)", "Voltages", "Can driver be off "
         "while receiver on?", "Needs"],
        [["PD_CPU -> PD_TOP", "0.7/0.9 -> 0.8", "yes (SLEEP)",
          "isolation + LS both ways (enable level shifter)"],
         ["PD_TOP -> PD_CPU", "0.8 -> 0.7/0.9", "no (AON never off)",
          "LS only (both directions depending on OPP)"],
         ["PD_ACC -> PD_TOP", "0.6 -> 0.8", "yes (CPU_ONLY, SLEEP)",
          "isolation + L->H shifter"],
         ["PD_TOP -> PD_ACC", "0.8 -> 0.6", "no", "H->L shifter (or buffer "
          "on the 0.6 V supply)"],
         ["PD_CPU -> PD_ACC", "0.7/0.9 -> 0.6", "no (CPU off => ACC off)",
          "H->L shifter; no isolation required by the state table"]],
        widths=[24, 18, 26, 32], bold_first=True,
        caption="Table 11.4 - What the state table implies at every crossing. "
                "A good exercise: add the state CPU OFF with ACC ON and see "
                "which row changes.")
    box("expert", "Interview insight: isolation location and supply",
        "Where do isolation cells go? With `-location parent` they sit in the "
        "receiving (usually always-on) domain and are powered by it, which is "
        "physically simple. With `-location self` they sit inside the "
        "switchable domain but must be powered from an always-on supply "
        "routed into that domain (a secondary power pin, like the KAPWR cells "
        "above). The isolation **enable** must itself come from an always-on "
        "domain and must be asserted before the supply drops and released "
        "only after it is stable again.")
    box("warn", "PITFALL: clamp values that break the receiver",
        "Clamping everything to 0 is the default and it is wrong for "
        "active-low signals (a request_n or reset_n clamped to 0 asserts it), "
        "for handshake signals where 0 means 'busy', and for bus signals where "
        "the receiver needs an IDLE encoding. Clamp values are a functional "
        "decision the RTL owner must review, signal by signal.")

    # ------------------------------------------------------------------------
    h2("UPF through the flow")
    p("One UPF (with per-stage additions) travels with the design from RTL "
      "to sign-off. Each tool reads it, implements its part, and writes out "
      "an updated UPF that describes what was built.")
    diagram([
        "  RTL + UPF (golden, 'power intent')",
        "     |---> static LP checks (VC LP, Conformal Low Power): syntax, consistency",
        "     |---> power-aware RTL simulation (VCS NLP, Xcelium, Questa PA)",
        "     v",
        "  synthesis (DC/FC, Genus): inserts ISO, LS, retention flops, maps ICGs;",
        "     writes netlist + UPF' (with implementation details, e.g. inserted cells)",
        "     |---> static LP checks on netlist (every crossing covered? cells legal?)",
        "     |---> LP-aware equivalence (RTL+UPF vs netlist+UPF')",
        "     v",
        "  P&R (Innovus, ICC2/FC, OpenROAD): creates domain regions, places switches,",
        "     routes secondary PG pins, builds per-domain grids, connects always-on;",
        "     writes netlist WITH PG connections + UPF''",
        "     |---> static LP checks on PG netlist; LVS knows the real supplies",
        "     v",
        "  sign-off: MV STA (per-supply voltages from the states), power/IR per domain,",
        "     rush-current analysis, power-aware gate-level simulation of the sequences",
    ], "Figure 11.4 - UPF through the flow. The low-power static checker is "
       "run at every hand-off, the same way STA and equivalence are.")
    tbl(["Stage", "Owner", "What UPF drives", "Typical checks"],
        [["RTL", "RTL/architecture + power architect", "Power-aware "
          "simulation: supplies turn on/off, corruption of off domains, "
          "isolation/retention behaviour", "UPF lint; missing isolation; "
          "PMU sequence tests"],
         ["Synthesis", "synthesis/implementation", "Cell insertion; "
          "domain-aware optimisation (no buffers from the wrong domain); "
          "multi-voltage timing", "LP check netlist vs UPF; LEC with UPF"],
         ["P&R", "physical design", "Voltage areas / domain regions, "
          "switch arrays, secondary PG routing, always-on buffering, level-"
          "shifter placement at the boundary", "PG connectivity; always-on "
          "paths; buffer supply legality"],
         ["Sign-off", "STA, power-integrity, verification", "Per-state "
          "timing, IR drop per domain, rush current, PA-GLS", "MV STA, IR/"
          "EM, LVS with PG netlist, LP check final"]],
        widths=[12, 22, 38, 28], bold_first=True,
        caption="Table 11.5 - Who uses the power intent at each stage.")
    p("Static checkers report issues with rule names such as missing "
      "isolation, isolation enable driven from a switchable domain, level "
      "shifter missing, retention control not always-on, or 'buffer powered "
      "by off domain on an always-on path'. An excerpt of the kind of summary "
      "they print:")
    code(["# ---- LP static check summary (ILLUSTRATIVE, not from a real run) ----",
          "Rule                         Severity  Count  Example",
          "ISO_MISSING                  error         3  u_acc/done -> u_noc/acc_done",
          "ISO_EN_NOT_AON               error         1  u_cpu/u_pmu_if/iso_q (PD_CPU)",
          "LS_MISSING_LH                error         2  u_acc/irq -> u_gic/irq[5]",
          "ISO_CLAMP_ACTIVE_LOW         warning       1  u_cpu/irq_n clamp 0",
          "AON_BUF_IN_SWITCHED          error         4  inserted by CTS in PD_CPU",
          "RET_CTRL_CORRUPTIBLE         error         1  u_pmu/cpu_save from PD_CPU",
          "Total: 11 errors, 1 warning"],
         "Illustrative LP-checker summary with generic rule names (every "
         "commercial tool has its own names and format).")

    # ------------------------------------------------------------------------
    h2("Power-aware verification")
    p("A normal simulator assumes every gate is always powered. A "
      "**power-aware** simulator reads the UPF, models supply nets as having "
      "a state and a voltage, and **corrupts** (drives X onto) every register "
      "and net of a domain whose supply is off (simstate CORRUPT). Isolation "
      "cells clamp, retention registers save and restore, and anything the "
      "UPF forgot shows up as X propagating into the live domains. The "
      "verification plan (Chapter 7) must include:")
    bul(["Every legal power-state transition, including the ones software "
         "rarely uses (e.g. RUN_ECO -> SLEEP -> RUN_FAST).",
         "Correct control sequences from the PMU (Figure 11.5), including "
         "wake-up events arriving at every step of a power-down sequence.",
         "Retention: state saved, domain off, domain back on, state restored "
         "and **non-retained** state reset correctly.",
         "Isolation clamps visible and correct in the receiving domain.",
         "Illegal states: the PMU must never create a state that is not in "
         "the state table (assertions on the supply states).",
         "Gate-level power-aware simulation of the sequences with the "
         "PG-connected netlist before tape-out."])
    diagram([
        "  power DOWN                                 power UP",
        "  1. stop clocks to the domain (ICG off)     1. switch enable (weak chain first)",
        "  2. assert save (retention)                 2. wait for ack (supply stable)",
        "  3. assert isolation enable                 3. assert reset of non-retained logic",
        "  4. (optional) assert reset                 4. assert restore (retention)",
        "  5. switch off; wait for ack                5. release reset",
        "                                             6. release isolation",
        "                                             7. restart clocks",
        "",
        "  clk_en  ~~~~~~~\\___________________________________________/~~~~~~",
        "  save    ________/~~\\____________________________________________________",
        "  iso_en  ___________/~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\\_________",
        "  pwr_en  ~~~~~~~~~~~~~~\\_____________________/~~~~~~~~~~~~~~~~~~~~~~~~~~~",
        "  VDD_SW  ~~~~~~~~~~~~~~~~\\___decays_______/''ramps''~~~~~~~~~~~~~~~~~~~~~",
        "  ack     ~~~~~~~~~~~~~~~~~~\\____________________/~~~~~~~~~~~~~~~~~~~~~~~~",
        "  restore ___________________________________________/~~\\________________",
    ], "Figure 11.5 - A typical power-down / power-up sequence. The exact "
       "order of reset and restore depends on the retention cell style; the "
       "invariants are: isolate before power goes away, un-isolate only after "
       "state is valid, and never clock a domain without power.")

    # ------------------------------------------------------------------------
    h2("Rush current and power-up sequencing")
    p("When a switched domain turns on, its whole decoupling and gate "
      "capacitance charges from (nearly) zero to VDD. If all switches close "
      "at once the in-rush current I = C * dV/dt can be amperes for "
      "nanoseconds, collapsing the supply of the **neighbouring, active** "
      "domains through the shared grid and package inductance.")
    _eqa(["I_rush = C_domain * dV/dt",
        "example: C_domain = 5 nF, V = 0.8 V, ramp in 20 ns -> I = 5e-9 * 0.8 / 20e-9 = 0.2 A",
        "         same domain ramped in 2 us through the weak chain -> I = 2 mA",
        "energy to charge: E = C V^2 = 3.2 nJ per wake-up (half is lost in the switches)"],
       "Equation 11.2 - Rush current and wake-up energy. Wake-up energy sets "
       "the minimum idle time for which power gating pays off (the "
       "break-even time).")
    bul(["**Daisy-chained switches**: the enable ripples through the switch "
         "cells (each has an enable-out pin); the chain delay spreads the "
         "turn-on over many nanoseconds to microseconds.",
         "**Two-stage (trickle + main)**: a chain of small, weak switches "
         "charges the domain slowly; when the virtual supply is near VDD the "
         "strong chain closes. The ack at the end of the last chain tells the "
         "PMU the domain is ready.",
         "Rush current and the resulting droop in neighbouring domains is a "
         "**sign-off check** (Chapter 18) done with dynamic power-integrity "
         "tools; the number and size of switches (IR drop when on) and the "
         "chain arrangement (rush when turning on) trade against each other.",
         "Chip-level **power-up sequencing** (which external rails come up "
         "first: typically core before I/O or as the I/O library requires; "
         "power-on reset; PLL lock; release of resets in order) is written "
         "into the spec with the board and PMIC team."])
    checklist("Low-power sign-off checklist", [
        "UPF lint clean; the same UPF version accepted by all tools in the flow.",
        "Every crossing covered by isolation / level shifting in every legal state.",
        "Isolation, retention and switch controls all driven from always-on logic.",
        "Clamp values reviewed by RTL owners (active-low and handshake signals).",
        "Power-aware simulation of all state transitions; PA-GLS of the sequences.",
        "LP-aware equivalence between RTL+UPF and final netlist+UPF.",
        "Always-on buffering and secondary PG pins routed; LVS with PG netlist.",
        "Multi-voltage STA at every OPP; level shifter timing and voltage ranges.",
        "Rush current and wake-up latency within budget; IR drop of switches in ON state.",
        "Leakage and dynamic power reported per domain, per state, at stated PVT.",
    ])

    h2("Summary")
    bul(["Power = switching + internal + leakage; the clock network and memories "
         "are usually the biggest dynamic consumers, leakage grows "
         "exponentially with temperature and lower Vt.",
         "Power estimates need activity (vectorless, SAIF, FSDB) and parasitics; "
         "accuracy improves from about +-50% at architecture to +-5-10% at "
         "sign-off. Quote power with PVT, mode and activity.",
         "The biggest savings are architectural (DVFS, parallelism, "
         "specialisation); RTL gating saves tens of percent; implementation "
         "techniques (multi-Vt, power gating, multi-voltage, body bias) attack "
         "leakage.",
         "Energy per operation has a minimum near threshold; below it, "
         "leakage dominates.",
         "UPF (IEEE 1801) describes supplies, domains, switches, isolation, "
         "level shifters, retention and legal power states; the same intent "
         "drives simulation, synthesis, P&R and sign-off, with static LP "
         "checks at each hand-off.",
         "Power gating needs a carefully ordered sequence (stop clocks, save, "
         "isolate, switch off; and the reverse) and controlled in-rush current "
         "through daisy-chained weak and strong switches."])
    h2("Exercises")
    bul(["A block has 2 nF of switched capacitance per cycle at 0.8 V and "
         "1 GHz with activity 0.15, and 30 mW of leakage at 0.8 V. Compute the "
         "dynamic power. If DVFS moves it to 0.65 V and 700 MHz and leakage "
         "scales as exp((V - 0.8)/0.25), what is the new total power and the "
         "new energy per cycle?",
         "Modify the UPF of Listings 11.3a-d to add a legal state where the "
         "CPU is OFF and the accelerator is ON. Which isolation and level-"
         "shifter strategies must change, and why?",
         "Explain why an isolation enable generated by a flop inside PD_CPU is "
         "a bug even though simulation of the 'happy path' passes.",
         "A domain has 8 nF of capacitance at 0.75 V. The neighbouring domain "
         "tolerates at most 30 mA of extra transient current. What is the "
         "minimum ramp time, and how would you implement it with switch "
         "chains?",
         "Using the dvfs.py model, change the leakage slope to exp((V - 0.9)/"
         "0.15) (a leakier process) and predict qualitatively how the "
         "minimum-energy point moves. Then run it.",
         "List three reasons a synthesis library should mark special cells "
         "(isolation, level shifters, always-on buffers, clock inverters) as "
         "dont_use for general mapping."], ordered=True)


# =============================================================================
#         CHAPTER 12 - ANALOG/MIXED-SIGNAL, I/O AND ESD INTEGRATION
# =============================================================================
def _ch12():
    chapter("Analog/Mixed-Signal, I/O and ESD Integration")
    p("No SoC is purely digital. Even a 'digital' ASIC needs a clock "
      "generator, a reference voltage, a way to know that power is good, "
      "I/O cells that talk to the outside world at a different voltage, and "
      "protection against the thousands of volts a human finger or a "
      "handling machine can deliver. Most of these blocks are designed by "
      "analog/mixed-signal (AMS) specialists or bought as hard IP, but the "
      "digital implementation team integrates them: it floorplans them, "
      "routes their supplies, closes timing to their digital pins, verifies "
      "their interaction with the logic and signs off the chip-level ESD "
      "network. Most tape-out delays caused by 'the analog block' are really "
      "integration problems: missing views, wrong abstracts, noisy "
      "neighbours, or an ESD path nobody owned.")

    # ------------------------------------------------------------------------
    h2("The analog blocks in a typical SoC")
    tbl(["Block", "What it does", "Integration concerns"],
        [["Crystal oscillator (XO) pad cell", "Drives an external quartz "
          "crystal (e.g. 19.2/24/25/38.4 MHz) - the clean reference",
          "Dedicated pads, quiet supply, keep digital switching away"],
         ["PLL (phase-locked loop)", "Multiplies the reference to GHz clocks, "
          "sets frequency for DVFS", "Jitter spec, lock time, quiet supply "
          "(often own LDO), clock output routing, test/bypass mux"],
         ["DLL (delay-locked loop)", "Aligns phases (DDR DQS centring, "
          "de-skew); no VCO so no jitter accumulation", "Placement next to "
          "the PHY; delay-line matching"],
         ["RC / ring oscillators", "Low-accuracy clocks for boot, "
          "always-on timers, watchdogs", "Trimming, temperature drift"],
         ["Bandgap reference", "Temperature-stable voltage (about 1.2 V in "
          "silicon) and bias currents", "Everything analog depends on it; "
          "trim bits in OTP/fuses"],
         ["LDO / DC-DC (buck) regulators", "Generate internal rails; LDO is "
          "quiet but lossy (efficiency ~ Vout/Vin), buck is efficient but "
          "switching-noisy", "Large currents, pads for inductors, decap, "
          "stability, power-up order"],
         ["POR / brown-out detector", "Holds the chip in reset until the "
          "supply is valid", "Must work with no clock and at any ramp rate"],
         ["ADC / DAC", "Sensor, audio, RF baseband conversion (SAR, sigma-"
          "delta, pipeline, flash)", "Reference and clock purity, substrate "
          "noise, digital calibration logic"],
         ["Temperature / voltage sensors", "Thermal throttling, AVS, "
          "reliability monitors", "Distributed placement near hot spots"],
         ["SerDes / high-speed PHY", "PCIe, Ethernet, USB, DDR, MIPI links "
          "(TX FFE, RX CTLE/DFE, CDR)", "Bump/ball assignment, package "
          "channel, power isolation, huge IP deliverable set"],
         ["eFuse / OTP", "Trim, keys, repair data", "High-voltage programming "
          "supply, security"]],
        widths=[22, 40, 38], bold_first=True,
        caption="Table 12.1 - Common analog and mixed-signal blocks. The "
                "protocol side of SerDes and DDR PHYs is covered in the "
                "companion Communication Protocols guide.")

    # ------------------------------------------------------------------------
    h2("PLL fundamentals")
    p("A charge-pump PLL is a feedback loop that forces the divided-down "
      "output of a voltage-controlled oscillator to match the reference in "
      "phase and therefore in frequency: f_out = N * f_ref (integer-N) or "
      "(N + fraction) * f_ref (fractional-N, where a sigma-delta modulator "
      "dithers the divider).")
    diagram([
        "          +------+  UP   +--------+  Icp   +-------------+  Vctrl  +-------+",
        " f_ref -->|      |------>| charge |------->| loop filter |-------->|  VCO  |--+--> f_out",
        "          | PFD  |  DN   |  pump  |        |  R + C1 ||C2|         | Kvco  |  |",
        "    +---->|      |------>|        |        +-------------+         +-------+  |",
        "    |     +------+       +--------+                                           |",
        "    |                                                                         |",
        "    |                         +----------------+                             |",
        "    +-------------------------|  divider  / N  |<----------------------------+",
        "                              +----------------+",
        "",
        "  PFD: phase-frequency detector -> UP/DN pulses proportional to phase error",
        "  CP : converts pulse width to charge (+-Icp);  LF: charge -> control voltage",
        "  VCO: ring (compact, noisier, wide tuning) or LC (low jitter, big inductor)",
    ], "Figure 12.1 - Charge-pump PLL. The loop filter's resistor creates the "
       "stabilising zero; C2 smooths the ripple the charge pump injects every "
       "reference cycle.")
    _eqa(["omega_n = sqrt( Icp * Kvco / (2*pi * N * C1) )          (natural frequency)",
        "zeta    = (R/2) * sqrt( Icp * Kvco * C1 / (2*pi * N) )   (damping)",
        "zero    : f_z = 1/(2*pi*R*C1)     ripple pole: f_p3 = 1/(2*pi*R*C1*C2/(C1+C2))",
        "rule of thumb: loop bandwidth < f_ref/10 (discrete-time sampling limit)"],
       "Equation 12.1 - Second-order approximation of a type-II charge-pump "
       "PLL (Kvco in rad/s/V).")
    code(r'''# pll.py - type-II third-order charge-pump PLL loop parameters
import numpy as np
f_ref, N = 25e6, 80                       # 25 MHz reference, f_vco = 2 GHz
Icp, Kvco = 100e-6, 2*np.pi*1.0e9         # 100 uA, 1 GHz/V
R, C1, C2 = 8.0e3, 100e-12, 5e-12
wn   = np.sqrt(Icp*Kvco/(2*np.pi*N*C1))
zeta = R/2*np.sqrt(Icp*Kvco*C1/(2*np.pi*N))
w = 2*np.pi*np.logspace(3, 9, 200000); s = 1j*w          # exact open loop with C2
Z = (1 + s*R*C1) / (s*(C1+C2)*(1 + s*R*C1*C2/(C1+C2)))
G = Icp/(2*np.pi) * Z * Kvco/s / N
k = np.argmin(abs(abs(G) - 1)); pm = 180 + np.degrees(np.angle(G[k]))''',
         "Listing 12.1 - PLL loop calculation (print statements elided).")
    out(["f_vco            = 2.000 GHz",
         "natural freq fn  = 0.56 MHz",
         "damping zeta     = 1.41",
         "zero  fz         = 0.20 MHz",
         "pole  fp3        = 4.18 MHz",
         "unity-gain fc    = 1.45 MHz  (f_ref/fc = 17)",
         "phase margin     = 63.1 deg",
         "lock time ~ 4/(zeta*wn) = 0.80 us (to ~2% settling)"],
        "Output of pll.py. A 63-degree phase margin and a bandwidth 17x below "
        "the reference are healthy; the lock-time figure is only a rough "
        "second-order estimate (real lock includes frequency acquisition).")
    h3("Jitter, and how it reaches STA")
    bul(["**Period jitter**: deviation of each period from the ideal; "
         "**cycle-to-cycle jitter**: difference between adjacent periods; "
         "**long-term jitter / TIE**: accumulated edge displacement. PLL "
         "datasheets quote these as RMS and peak (peak ~ 6-7x RMS for "
         "Gaussian jitter at typical bit-error-style confidence levels, "
         "depending on sample count).",
         "Inside the loop bandwidth the output follows the reference (and "
         "its noise); outside it the VCO's own phase noise dominates. The "
         "loop bandwidth is therefore chosen to balance reference noise vs "
         "VCO noise, and supply noise sensitivity of ring VCOs makes the "
         "PLL supply one of the quietest on the chip.",
         "For digital timing, the PLL's period jitter (plus duty-cycle "
         "distortion and the clock tree's own supply-induced jitter) becomes "
         "part of `set_clock_uncertainty` for setup (Chapter 9). Hold checks "
         "on the same edge see no PLL jitter, only tree jitter."])
    h3("Clocking architecture")
    diagram([
        "  XTAL --[XO pad]--> ref_clk ----+-----------------------------> always-on timers",
        "                                 |",
        "                     +-----------v----+    +------------+   glitch-free",
        "  RC osc (boot) ---->| PLL0 (CPU,DVFS)|--->| clock mux  |--> div --> ICG --> CPU tree",
        "                     +----------------+    | (bypass,   |",
        "                     +----------------+    |  test clk) |--> div --> ICG --> NoC tree",
        "                     | PLL1 (fixed)   |--->|            |",
        "                     +----------------+    +------------+--> div --> ICG --> periph",
        "                                                ^",
        "   clock controller (AON): select, divide, gate, PLL lock/bypass, DFT OCC",
    ], "Figure 12.2 - A typical clock generation and distribution scheme. "
       "The clock controller is digital RTL owned by the SoC team; the PLLs "
       "are hard macros. Test clocks enter through on-chip clock controllers "
       "(OCC, Chapter 10).")

    # ------------------------------------------------------------------------
    h2("The AMS design flow")
    p("Analog blocks are designed at the transistor level with a completely "
      "different flow from the digital one, usually in Cadence Virtuoso "
      "(schematic and custom layout) with SPICE-class simulators (Spectre, "
      "HSPICE, Siemens AFS, Synopsys PrimeSim).")
    diagram([
        "  spec --> schematic --> pre-layout SPICE sims (DC, AC, transient, noise, PSS/pnoise)",
        "                |           x corners (SS/FF/SF/FS, V, T) + Monte Carlo (mismatch)",
        "                v",
        "          custom layout (matching: common centroid, interdigitation, dummies,",
        "                |         guard rings; symmetry; wide supply straps)",
        "                v",
        "          DRC / LVS (Calibre, Pegasus) --> parasitic extraction (StarRC,",
        "                |                          Quantus, Calibre xRC) --> post-layout sims",
        "                v",
        "          views for integration: GDS, CDL netlist, LEF abstract, Liberty (.lib),",
        "          behavioural/RNM model, integration guide, ESD/latch-up report",
    ], "Figure 12.3 - Analog design flow and the views it must deliver to "
       "the SoC team.")
    p("Where digital sign-off relies on STA and static checks, analog "
      "sign-off relies on simulation across corners and Monte Carlo "
      "(mismatch between 'identical' transistors is the dominant accuracy "
      "limit of comparators, current mirrors and DACs). Layout is "
      "performance: a differential pair that is not matched and symmetric "
      "does not meet offset specs no matter what the schematic says.")

    # ------------------------------------------------------------------------
    h2("AMS verification at the SoC level")
    p("A full-chip SPICE simulation of an SoC is impossible, yet the digital "
      "logic that configures, calibrates and monitors the analog blocks "
      "must be verified with them. The industry answer is a ladder of model "
      "abstractions:")
    tbl(["Model", "Language", "Speed", "Use"],
        [["Pure digital stub", "SV/Verilog", "fastest", "Connectivity only; "
          "dangerous if it hides behaviour"],
         ["Real-number model (RNM)", "SV `real`, user-defined nettypes "
          "(SV-2012 UDN), Cadence `wreal`", "near-digital (event-driven)",
          "Default for SoC regressions: voltages/currents as real values "
          "that change at events"],
         ["Behavioural analog", "Verilog-A / Verilog-AMS", "10-100x slower "
          "than digital", "Continuous-time behaviour (filters, loops) in "
          "an analog solver"],
         ["Transistor level", "SPICE netlist", "slowest", "Block sign-off; "
          "selected co-simulation of critical interactions"]],
        widths=[20, 28, 18, 34], bold_first=True,
        caption="Table 12.2 - The abstraction ladder. Mixed-signal simulators "
                "(Xcelium with Spectre AMS Designer, VCS with PrimeSim, "
                "Questa with Symphony) co-simulate digital and analog "
                "engines.")
    p("The key discipline is **model validation**: every RNM must be checked "
      "against the transistor-level schematic (same stimulus, compare "
      "outputs within tolerance), otherwise the SoC regression verifies "
      "the model writer's assumptions rather than the circuit. Below is a "
      "small RNM of a power-on-reset block - a comparator with hysteresis on "
      "a real-valued supply plus a digital delay counter - simulated with "
      "Icarus Verilog.")
    code(r'''`timescale 1ns/1ps
module por_rnm #(parameter real VTH_R = 1.35, VTH_F = 1.25, parameter int DLY = 8)
               (input real vdd, input logic osc_clk, output logic por_n);
  logic vok = 1'b0;                     // analog comparator output (digital)
  int   cnt = 0;
  always @(vdd) begin                   // re-evaluated whenever the real supply changes
    if (!vok && vdd > VTH_R) vok = 1'b1;
    else if (vok && vdd < VTH_F) vok = 1'b0;
  end
  always @(posedge osc_clk or negedge vok)
    if (!vok) begin cnt <= 0; por_n <= 1'b0; end
    else if (cnt < DLY) cnt <= cnt + 1;
    else por_n <= 1'b1;
  initial por_n = 1'b0;
endmodule
// tb: vdd ramps 0 -> 1.8 V in 0.1 V/100 ns steps, stays, dips to 1.1 V, recovers;
//     a 10 MHz osc_clk; $display on every change of por_n or the comparator''',
         "Listing 12.2 - Real-number POR model (testbench summarised in the "
         "last comment lines).")
    out(["  time(ns)   vdd(V)  por_n",
         "        0     0.00   0   (comparator=0)",
         "     1400     1.40   0   (comparator=1)",
         "     2250     1.80   1   (comparator=1)",
         "     3900     1.20   1   (comparator=0)",
         "     3900     1.20   0   (comparator=0)",
         "     4300     1.40   0   (comparator=1)",
         "     5150     1.80   1   (comparator=1)",
         "por_rnm.sv:28: $finish called at 6200000 (1ps)"],
        "iverilog -g2012 -Wall, vvp: reset is released 8 oscillator cycles "
        "after the rising threshold is crossed, asserted at once when the "
        "brown-out drops below the falling threshold, and the hysteresis "
        "(1.35/1.25 V) avoids chatter.")
    box("warn", "PITFALL: the 'always powered' analog model",
        "The most common SoC-level AMS bug is a behavioural model that ignores "
        "its own supply and enable pins: in simulation the PLL locks while "
        "its LDO is still off, or an ADC converts while its reference is "
        "disabled. Models must check supply/bias/enable pins and produce X or "
        "invalid outputs when they are not valid - and those checks must be "
        "validated against the schematic.")

    # ------------------------------------------------------------------------
    h2("Integration: analog-on-top vs digital-on-top")
    tbl(["", "Digital-on-top (DoT)", "Analog-on-top (AoT)"],
        [["Top-level owner", "Digital P&R tool (Innovus, ICC2/FC)",
          "Custom layout tool (Virtuoso); digital blocks are hard macros"],
         ["Typical chip", "Large SoC with a few analog macros", "Mostly "
          "analog chip (PMIC, sensor AFE, RF transceiver) with some "
          "digital control"],
         ["Analog block form", "Hard macro with LEF/Liberty/GDS views",
          "Native schematic/layout; digital comes in as placed-and-routed "
          "macros"],
         ["Chip-level verification", "STA + digital checks; analog "
          "treated as black boxes plus AMS co-sim", "Chip-level SPICE/AMS "
          "simulation; digital timing closed at block level"],
         ["Risk", "Noise coupling and supply mistakes around macros",
          "Digital timing and DFT integration handled by hand"]],
        widths=[18, 41, 41], bold_first=True,
        caption="Table 12.3 - The two integration styles. Mixed flows "
                "(OpenAccess-based interoperability between Virtuoso and "
                "Innovus) let each team edit its own part of one database.")
    h3("Views a hard macro must deliver")
    checklist("Hard-macro (analog IP) deliverables", [
        "GDSII/OASIS layout and a CDL/SPICE netlist for LVS (with black-box rules if needed).",
        "LEF abstract: size, pins (layer, shape, direction, USE SIGNAL/POWER/GROUND/ANALOG), "
        "obstructions (OBS) per layer, and the routing layers the chip may use over it.",
        "Liberty timing model for digital pins (setup/hold to its clocks, output delays, "
        "pin capacitance, leakage/power, pg_pin and related_power_pin attributes).",
        "Behavioural/RNM model validated against the schematic; UPF for its supplies.",
        "Integration guide: supply sequencing, decap, keep-outs, shielding, pin constraints.",
        "DRC/LVS/antenna clean reports; ESD and latch-up compliance statement.",
        "Test and trim: DFT access, BIST/loopback, trim fuses, characterisation data.",
    ])
    p("Timing models for hard macros come in two flavours: a **Liberty "
      "abstract** written by the IP team (black-box timing arcs per pin), or "
      "for digital hard blocks an **ETM** (extracted timing model) or "
      "**ILM** (interface logic model) generated from the block's own "
      "implementation (Chapter 13).")

    # ------------------------------------------------------------------------
    h2("Noise isolation")
    p("Digital logic injects noise into the shared substrate and supplies "
      "every clock edge; sensitive analog circuits (PLL VCOs, ADC "
      "comparators, bandgaps, LNAs) pick it up. Isolation is a combination "
      "of layout and planning:")
    diagram([
        "     digital logic         guard ring          analog block (deep n-well)",
        "  (noisy aggressor)     p+ tie to quiet      ",
        "                        ground  n-well ring    +---------------------------+",
        "   NMOS  PMOS             |      |             | p-well islands inside DNW |",
        "  ---n+--n+-p+---       -p+-   -n+-            |  NMOS  NMOS               |",
        "  p-substrate  ~~~~~~~~~~ |      |  ~~~~~~     +-----deep n-well-----------+",
        "   noise currents  -----> collected / blocked         (isolates p-well)",
        "  ================================== p-substrate ==============================",
    ], "Figure 12.4 - Substrate noise isolation: guard rings collect "
       "substrate current before it reaches the victim; a deep n-well "
       "(triple-well process) isolates the p-well of sensitive NMOS "
       "devices from the common substrate.")
    bul(["**Separate supplies and grounds** for analog (AVDD/AVSS), "
         "separate pads and package balls, joined only at the board or "
         "through back-to-back diodes for ESD.",
         "**Distance and floorplan**: keep high-activity digital (CPU "
         "cores, clock roots) and I/O drivers away from the PLL/ADC; put "
         "analog at the die edge next to its pads.",
         "**Guard rings** (p+ substrate ties, n-well rings) around both "
         "aggressors and victims; **deep n-well** under sensitive blocks.",
         "**Routing keep-outs and shielding**: no digital routing over "
         "analog macros (blockages on all or some layers), grounded "
         "shields beside sensitive analog nets, differential routing.",
         "**Clock and supply hygiene**: spread-spectrum or de-synchronised "
         "switching, on-chip decap, dedicated LDOs for the most sensitive "
         "blocks."])

    # ------------------------------------------------------------------------
    h2("I/O cells")
    p("I/O cells (pad cells) translate between the core's thin-oxide, "
      "low-voltage transistors and the outside world at 1.2, 1.8, 2.5 or "
      "3.3 V using thick-oxide devices. They are delivered as an **I/O "
      "library** from the foundry or an IP vendor, with Liberty, LEF, GDS "
      "and SPICE/IBIS models (IBIS is used by board engineers for signal "
      "integrity).")
    diagram([
        "  core side (VDD, 0.8 V)                    pad side (VDDIO, 1.8/3.3 V)",
        "",
        "  A (data out) --[level   ]--[pre-driver]--+--[big PMOS]--+",
        "  OE (enable)  --[shifter ]--[ + slew   ]--+--[big NMOS]--+----+----[ PAD ]--- bond/bump",
        "  DS[1:0] (drive strength) -> selects driver fingers  |        |",
        "  SR (slew rate)            -> pre-driver strength    | [pull-up/down R, keeper]",
        "  PU/PD (pulls)                                       |        |",
        "  Y (data in) <--[level shift]<--[Schmitt/CMOS rx]<---+   [ESD diodes to VDDIO/VSSIO]",
        "  IE (input enable, blocks floating-input crowbar current)",
    ], "Figure 12.5 - A bidirectional GPIO cell. The ESD diodes and the "
       "rail clamp elsewhere in the ring are part of every signal pad.")
    tbl(["Feature", "Purpose", "Design consideration"],
        [["Drive strength (e.g. 2/4/8/12 mA)", "Meet load/speed at the "
          "board", "Stronger drive = more SSO noise and EMI"],
         ["Slew-rate control", "Slow edges reduce ringing and SSO",
          "Must still meet the interface timing"],
         ["Pull-up / pull-down / keeper", "Define floating inputs, "
          "straps", "Weak (tens of kohm); check leakage in sleep"],
         ["Schmitt trigger input", "Hysteresis for slow or noisy edges "
          "(resets, buttons)", "Slightly slower; mandatory on reset pins"],
         ["Input enable / fail-safe", "Avoid crowbar current and back-"
          "powering when VDDIO is off", "Required when the other side can "
          "be powered while the chip is off"],
         ["Power-on control (POC)", "Keeps outputs tristated while the "
          "core supply ramps", "A global signal on the I/O ring"]],
        widths=[27, 36, 37], bold_first=True,
        caption="Table 12.4 - GPIO features the SoC team configures through "
                "control pins or registers.")
    h3("Pad types in the ring")
    bul(["**Signal pads**: digital GPIO, specialised (LVDS, I2C open-drain, "
         "oscillator), and **analog pads** (direct connection with ESD but "
         "no buffers; low series resistance).",
         "**Core supply pads** (VDD/VSS) feeding the core power ring or "
         "grid, and **I/O supply pads** (VDDIO/VSSIO) feeding the pad "
         "ring's own rails. Their number is set by current, EM, IR drop and "
         "SSO (the rule 'one VDDIO/VSSIO pair per N signal pads' comes from "
         "the I/O library's SSO guideline).",
         "**Corner cells** that continue the ring rails around corners; "
         "**filler/spacer cells** between pads that keep the rails and ESD "
         "bus continuous; **power-cut (break) cells** that split the ring "
         "into separately supplied segments (e.g. 1.8 V and 3.3 V banks) "
         "while keeping the ESD ground bus connected.",
         "Flip-chip designs place I/O and supply cells in the core area or "
         "an array; bumps connect through a redistribution layer (Chapter 14)."])

    # ------------------------------------------------------------------------
    h2("ESD: models and protection networks")
    p("Electrostatic discharge is a short, high-current event: a charged "
      "person or machine touching a pin, or the charged package itself "
      "discharging to a grounded tool. Thin gate oxides break down at a few "
      "volts and junctions melt at amperes, so every pin needs a path that "
      "carries amperes for nanoseconds while keeping the voltage across "
      "sensitive devices below their breakdown.")
    tbl(["Model", "What it represents", "Circuit / waveform", "Typical "
         "component-level target"],
        [["HBM (Human Body Model), ANSI/ESDA/JEDEC JS-001", "Charged person "
          "touching a pin", "100 pF through 1.5 kohm; ~2-10 ns rise, "
          "~150 ns decay; ~0.67 A per kV", "1-2 kV (industry councils "
          "argue 1 kV is safe with basic ESD control)"],
         ["CDM (Charged Device Model), ANSI/ESDA/JEDEC JS-002", "The "
          "package/die itself charged, discharging from one pin", "Very "
          "fast: sub-ns rise, peak currents of amperes, total duration "
          "~1-2 ns", "~250-500 V; large packages see higher currents"],
         ["MM (Machine Model)", "Charged tool", "200 pF, ~0 ohm",
          "Obsolete for qualification; still seen in old specs"],
         ["IEC 61000-4-2 (system level)", "ESD into the finished product",
          "150 pF / 330 ohm, up to 8 kV contact", "Board-level (TVS "
          "diodes); on-chip only for exposed pins such as USB"]],
        widths=[22, 20, 30, 28], bold_first=True,
        caption="Table 12.5 - ESD models. Exact targets are set by the "
                "product specification and the foundry's ESD guidelines.")
    code(r'''# hbm.py - HBM discharge (100 pF, 1.5 kohm, series L) into a shorted pin
import numpy as np
C, R, L = 100e-12, 1500.0, 7.5e-6        # L: assumed tester/loop inductance
for V0 in (2000.0, 4000.0):
    dt = 5e-12; t = np.arange(0, 1.0e-6, dt)
    q, i = C*V0, 0.0; I = np.empty_like(t)
    for n in range(len(t)):                  # semi-implicit Euler on the RLC loop
        di = (q/C - R*i)/L*dt; i += di; q -= i*dt; I[n] = i
    ...                                      # measure peak, 10-90% rise, 1/e decay''',
         "Listing 12.3 - HBM waveform model.")
    out(["V=2000 V: Ipeak=1.22 A (V/R=1.33 A), rise10-90=8.6 ns, decay(1/e)=150 ns",
         "V=4000 V: Ipeak=2.44 A (V/R=2.67 A), rise10-90=8.6 ns, decay(1/e)=150 ns",
         "RC time constant = 150 ns; energy 0.5CV^2 at 2 kV = 200 uJ"],
        "Output of hbm.py: a 2 kV HBM zap pushes about 1.2-1.3 A for ~150 ns "
        "through the protection network. The rise time depends on the "
        "assumed inductance; JS-001 specifies acceptable ranges for the "
        "tester waveform.")
    h3("The protection network")
    diagram([
        "  VDDIO rail ===+===========================+====================+=========",
        "                |                           |                    |",
        "              [D1] primary up-diode       [D3] secondary      [rail clamp]",
        "                |                           |                 RC-triggered",
        "  PAD ----------+------[R2 ~100-200 ohm]-----+----> receiver    big NMOS,",
        "  (bond/bump)   |       (secondary R)       |      gate        one every",
        "              [D2] primary down-diode     [D4] secondary      few pads",
        "                |                           |                    |",
        "  VSSIO rail ===+===========================+====================+=========",
        "                |",
        "        [back-to-back diodes] ---- VSS (core), AVSS (analog)",
        "",
        "  positive zap PAD->VSSIO : PAD -> D1 -> VDDIO -> rail clamp -> VSSIO",
        "  negative zap PAD->VSSIO : VSSIO -> D2 -> PAD",
    ], "Figure 12.6 - Dual-diode protection with a power-rail clamp. Every "
       "pin-to-pin combination must have a low-impedance path through diodes "
       "and clamps; current paths across domains go through the ground "
       "diodes and the clamps of both domains.")
    bul(["**Primary diodes** steer the current to the rails; the **rail "
         "clamp** is a large NMOS whose gate is driven by an RC detector: an "
         "ESD edge (ns) turns it on, a normal power-up (microseconds to "
         "milliseconds) does not. The RC time constant is typically chosen "
         "around a microsecond - long compared with HBM, short compared "
         "with power-up.",
         "The **secondary** stage (small resistor + small diodes/grounded-gate "
         "NMOS at the receiver) limits the voltage that reaches the thin "
         "gate oxide during fast CDM events.",
         "**Bus resistance matters**: the discharge path through the ring "
         "rails and clamps must be low-ohmic, so clamp spacing and rail "
         "widths are specified by the I/O library (for example 'one clamp "
         "every N pads' and a maximum resistance from any pad to its clamp).",
         "**Cross-domain CDM**: a signal crossing between two core supply "
         "domains can see a large voltage difference during CDM; the "
         "receiver gate needs local protection (a small clamp or resistor "
         "and diodes). Foundry ESD rule decks and dedicated tools (e.g. "
         "Calibre PERC, Pathfinder) check these paths at chip level "
         "(Chapter 18)."])

    h3("Latch-up")
    p("A CMOS inverter contains a parasitic PNPN thyristor (the PMOS source, "
      "n-well, p-substrate and NMOS source form a vertical PNP and a lateral "
      "NPN). If a transient injects enough current to forward-bias a well or "
      "substrate junction, the thyristor can latch into a low-impedance "
      "state between VDD and VSS and destroy the chip. Prevention is by "
      "layout: **well and substrate taps** close to every transistor (the "
      "tap cells of Chapter 14; the maximum tap distance is a foundry rule), "
      "**guard rings** around I/O devices and anything that can inject "
      "current, and spacing between NMOS and PMOS in I/O areas. "
      "Qualification follows JEDEC JESD78 (current injection of typically "
      "+-100 mA into I/O pins and an over-voltage test on supplies, at "
      "maximum operating temperature for the higher classes).")

    h3("Simultaneous switching output (SSO) noise")
    p("When many output drivers switch together, their current flows through "
      "the inductance of the I/O supply bonds, balls and package planes, and "
      "the local VSSIO bounces up (ground bounce) while VDDIO droops.")
    _eqa(["V_bounce ~ L_eff * N * dI/dt",
        "example: 16 drivers, each 20 mA in 1 ns, L_eff = 0.5 nH (one bond/ball pair shared)",
        "         V = 0.5e-9 * 16 * 0.02 / 1e-9 = 0.16 V  -> add supply pairs, slow the edges"],
       "Equation 12.2 - Ground bounce. Real analysis uses IBIS models and "
       "package models; this estimate explains the 'N signal pads per supply "
       "pair' rule.")
    box("key", "Who owns what",
        "The I/O library and ESD cells come from the foundry or IP vendor; the "
        "**pad-ring plan** (pad order, supply pads, domain breaks, clamps) is "
        "owned by the chip-level physical design team together with the "
        "package team; the **ESD sign-off** (all pin-pair paths, cross-domain "
        "checks) is usually owned by a chip-level ESD/reliability engineer "
        "using the foundry's ESD rules. Board-level SSO/SI is owned by the "
        "package/board SI team using IBIS models from the I/O library.")

    h2("Summary")
    bul(["Every SoC integrates PLLs/DLLs, oscillators, a bandgap, regulators, "
         "a POR, data converters, sensors and high-speed PHYs; the digital "
         "team owns their floorplan, supplies, timing interfaces and "
         "verification.",
         "A charge-pump PLL is a feedback loop (PFD, charge pump, loop "
         "filter, VCO, divider); bandwidth, damping and phase margin follow "
         "from Icp, Kvco, N and the filter. PLL jitter enters STA as clock "
         "uncertainty.",
         "Analog design is schematic, SPICE over corners and Monte Carlo, "
         "custom layout and extraction; SoC verification uses real-number "
         "models validated against transistor-level simulation.",
         "Hard macros must come with GDS, CDL, LEF, Liberty, a behavioural "
         "model, UPF and an integration guide; digital-on-top vs analog-on-"
         "top defines who owns the top level.",
         "Noise isolation uses separate supplies, distance, guard rings, deep "
         "n-well, keep-outs and shielding.",
         "I/O cells shift levels and drive the board; the pad ring includes "
         "signal, supply, corner, filler and break cells. ESD protection "
         "(diodes, RC rail clamps, secondary stages) is designed against HBM "
         "and CDM; latch-up is prevented by taps and guard rings; SSO limits "
         "the number of signal pads per supply pair."])
    h2("Exercises")
    bul(["In pll.py, double Icp. Predict how omega_n, zeta and the unity-gain "
         "frequency change, then verify. What happens to the phase margin if "
         "C2 is increased to 20 pF?",
         "A PLL datasheet quotes 3 ps RMS period jitter. What peak-to-peak "
         "value would you use in set_clock_uncertainty for setup, and what "
         "else would you add to it?",
         "Write a real-number model of an LDO whose output follows its input "
         "minus a 150 mV dropout and is 0.0 when disabled. How would you "
         "validate it against the schematic?",
         "Draw the ESD current path for a positive HBM zap from a GPIO pad "
         "to a core VSS pin in a chip whose core and I/O grounds are "
         "separate but connected by back-to-back diodes. Which elements "
         "carry the current?",
         "An interface has 32 outputs at 12 mA with 0.8 ns edges. The I/O "
         "library recommends at most 150 mV of bounce and each VSSIO ball "
         "contributes 0.8 nH. How many VSSIO balls are needed if only half "
         "the outputs switch in the same direction at once?"], ordered=True)


# =============================================================================
#     CHAPTER 13 - PHYSICAL DESIGN OVERVIEW: DATA, FLOWS AND DESIGN PLANNING
# =============================================================================
def _ch13():
    chapter("Physical Design Overview: Data, Flows and Design Planning")
    p("Physical design (PD) - also called implementation or the back end - "
      "turns a gate-level netlist into the geometric shapes of every "
      "transistor, wire and via on every mask layer, while meeting timing, "
      "power, signal-integrity, reliability and manufacturability "
      "constraints. This chapter is the map for Part IV: the steps, the data "
      "that flows between them, how big designs are split into manageable "
      "pieces, and how the die size is estimated long before anything is "
      "placed. Chapter 14 then begins the actual implementation with the "
      "floorplan.")

    # ------------------------------------------------------------------------
    h2("From netlist to GDSII")
    diagram([
        "  netlist(.v) + SDC + UPF + DEF(floorplan hints) + tech/libraries (LEF, Liberty, RC)",
        "        |",
        "        v",
        "  [1] import / design setup   MCMM views, sanity checks (unresolved refs, SDC, UPF)",
        "        v",
        "  [2] floorplan               die/core, rows, IO ring/bumps, macros, blockages    (Ch 14)",
        "        v",
        "  [3] power plan              rings, straps, rails, switches, taps/endcaps        (Ch 14)",
        "        v",
        "  [4] placement + opt         global/detailed placement, scan reorder, sizing,   (Ch 15)",
        "        |                     buffering, early timing/congestion",
        "        v",
        "  [5] CTS + post-CTS opt      clock tree/mesh, skew, hold fixing starts          (Ch 16)",
        "        v",
        "  [6] routing + post-route    global/track/detail route, SI fixes, DFM vias,     (Ch 17)",
        "        |    opt              antenna fixes, fill",
        "        v",
        "  [7] sign-off                extraction(SPEF) -> STA, IR/EM, DRC/LVS/ERC/antenna,(Ch 18)",
        "        |                     LEC, LP checks; ECO loop back to [6]               (Ch 19)",
        "        v",
        "  GDSII/OASIS --> tapeout --> mask making                                      (Ch 19)",
    ], "Figure 13.1 - The implementation flow. In practice steps 4-6 are "
       "iterated many times, and sign-off findings feed back through ECOs.")
    p("Modern tools blur the steps: placement runs with trial routing and "
      "clock estimates, CTS is concurrent with optimisation, and "
      "'physically aware' synthesis (Genus iSpatial, Fusion Compiler, DC "
      "Topographical/NXT) places cells during synthesis so the netlist "
      "handed to PD already reflects real wire lengths. The conceptual "
      "sequence above is still how engineers reason about problems and how "
      "flows are scripted.")

    # ------------------------------------------------------------------------
    h2("Inputs: the data PD needs")
    tbl(["Input", "Format", "Content", "Provided by"],
        [["Netlist", "Verilog (structural)", "Instances of library cells and "
          "macros, connectivity, hierarchy", "Synthesis / DFT team"],
         ["Timing constraints", "SDC (Tcl)", "Clocks, generated clocks, I/O "
          "delays, exceptions, modes", "Front-end + STA team"],
         ["Power intent", "UPF (IEEE 1801)", "Domains, supplies, strategies, "
          "states (Chapter 11)", "Power architect"],
         ["Technology LEF", "LEF", "Layers, directions, pitches, widths, "
          "spacing rules, vias, sites, antenna rules", "Foundry PDK / "
          "library vendor"],
         ["Cell / macro LEF", "LEF", "Abstract of each cell: size, site, "
          "pins with shapes/layers, obstructions", "Library/IP vendors"],
         ["Timing/power libraries", "Liberty (.lib, compiled .db / .ldb), "
          "with CCS/ECSM/LVF data", "Delay/transition tables, constraints, "
          "power, pg_pins, per PVT corner", "Library/IP vendors"],
         ["RC extraction data", "QRC techfile (Cadence), TLU+ + layer map "
          "(Synopsys), captables; ITF/ICT source", "Per-layer R and C vs "
          "width/spacing for each RC corner", "Foundry PDK"],
         ["Floorplan / partitions", "DEF, Tcl, or tool DB", "Die/core, "
          "pins, macro positions from planning", "PD lead / top-level team"],
         ["Physical rules", "DRC/LVS/antenna/fill decks (Calibre SVRF, "
          "Pegasus, ICV)", "Sign-off rule checks", "Foundry PDK"],
         ["Parasitics of blocks", "SPEF", "Extracted RC of lower blocks for "
          "top-level timing", "Block PD teams"]],
        widths=[16, 24, 36, 24], bold_first=True,
        caption="Table 13.1 - PD inputs. Liberty, LEF and the technology "
                "files are described in detail in Chapters 3 and 4 and "
                "Appendix A.")
    p("Here is what a real technology LEF says about the metal stack of "
      "the open SKY130 process (a 130 nm, five-metal-plus-local-interconnect "
      "process). A short script reads the routing layers from the file used "
      "by the open-source flows:")
    code(r'''# techlef.py - summarise routing layers of the SKY130 HD technology LEF
import re
t = open("sky130_fd_sc_hd.tlef").read()
print("layer  dir  pitch  min_w  thick  Rsq(ohm)  R/um@min_w  EM Iavg(mA/um)")
for m in re.finditer(r"LAYER (\w+)\s+TYPE ROUTING ;(.*?)END \1", t, re.S):
    n, b = m.group(1), m.group(2)
    g = lambda k: re.search(k + r"\s+([\d.E-]+)", b)
    d = re.search(r"DIRECTION (\w)", b).group(1)
    w = float(g("WIDTH").group(1)); r = float(g("RESISTANCE RPERSQ").group(1))
    em = g("DCCURRENTDENSITY AVERAGE")
    print(...)       # name, dir, PITCH, WIDTH, THICKNESS, Rsq, Rsq/w, EM''',
         "Listing 13.1 - Reading the tech LEF.")
    out(["layer  dir  pitch  min_w  thick  Rsq(ohm)  R/um@min_w  EM Iavg(mA/um)",
         "li1     V   0.46   0.17    0.1  12.2000     71.765     -",
         "met1    H   0.34   0.14   0.35   0.1250      0.893     2.8",
         "met2    V   0.46   0.14   0.35   0.1250      0.893     2.8",
         "met3    H   0.68   0.30    0.8   0.0470      0.157     6.8",
         "met4    V   0.92   0.30    0.8   0.0470      0.157     6.8",
         "met5    H    3.4   1.60    1.2   0.0285      0.018     10.17"],
        "Output of techlef.py on the SKY130 HD technology LEF (units: um, "
        "ohm/square, ohm/um; EM limits are the LEF's average-current density "
        "at Tj = 90 C). The same file defines the standard-cell site "
        "`unithd`, 0.46 x 2.72 um.")
    p("Note the pattern that holds in every process: thin, dense lower "
      "layers for local routing (high resistance per um), thick, wide "
      "upper layers for power and long global wires (low resistance). "
      "Directions alternate (H/V) so that adjacent layers route "
      "orthogonally. Advanced nodes have 10-20 metal layers in several "
      "pitch classes (1x, 2x, 4x...) and add rules such as coloring for "
      "multi-patterning (Chapter 3).")

    # ------------------------------------------------------------------------
    h2("Outputs and databases")
    tbl(["Output", "Format", "Consumer"],
        [["Layout", "GDSII or OASIS (stream)", "Physical verification, "
          "merge with foundry cells, mask making"],
         ["Netlist (with and without PG)", "Verilog", "LVS (PG netlist), STA, "
          "LEC, gate-level simulation"],
         ["Placement/routing", "DEF (Design Exchange Format)", "Other tools, "
          "top-level integration, open-source flows"],
         ["Parasitics", "SPEF (IEEE 1481) from sign-off extraction",
          "STA, power, IR drop"],
         ["Delays", "SDF (IEEE 1497)", "Timing-annotated gate-level "
          "simulation"],
         ["Block models", "LEF abstract, Liberty ETM, ILM", "Top-level "
          "implementation and STA"],
         ["Reports", "text/HTML", "Sign-off reviews: timing, power, IR/EM, "
          "DRC/LVS, utilisation, congestion"]],
        widths=[26, 32, 42], bold_first=True,
        caption="Table 13.2 - PD outputs.")
    p("Each tool keeps the design in its own database: Cadence Innovus uses "
      "its native database and can read/write **OpenAccess (OA)**, the "
      "common database shared with Virtuoso for mixed-signal work; Synopsys "
      "IC Compiler II and Fusion Compiler use **NDM** (New Data Model) "
      "libraries; OpenROAD uses **OpenDB**, which is modelled on LEF/DEF. "
      "Between companies and tools, LEF/DEF/Verilog/SDC/SPEF are the "
      "lingua franca.")
    h3("A DEF excerpt, explained")
    code(r'''VERSION 5.8 ;
DESIGN mac_rf ;
UNITS DISTANCE MICRONS 1000 ;                          # 1 DB unit = 1 nm
DIEAREA ( 0 0 ) ( 180000 180000 ) ;                    # 180 x 180 um
ROW ROW_0 unithd 5520 10880 N  DO 367 BY 1 STEP 460 0 ;   # site, origin, orient, count
ROW ROW_1 unithd 5520 13600 FS DO 367 BY 1 STEP 460 0 ;   # flipped: shares rails
TRACKS X 230 DO 391 STEP 460 LAYER met2 ;              # routing grid, per layer
TRACKS Y 170 DO 529 STEP 340 LAYER met1 ;
COMPONENTS 2163 ;
- _1034_ sky130_fd_sc_hd__nand2_1 + PLACED ( 41400 27200 ) FS ;
- acc_reg_7_ sky130_fd_sc_hd__dfrtp_1 + PLACED ( 52900 29920 ) N ;
- TAP_12 sky130_fd_sc_hd__tapvpwrvgnd_1 + FIXED ( 12420 10880 ) N ;
END COMPONENTS
PINS 118 ;
- clk + NET clk + DIRECTION INPUT + USE CLOCK
  + LAYER met3 ( -150 -150 ) ( 150 150 ) + PLACED ( 0 90100 ) N ;
END PINS
SPECIALNETS 2 ;
- VPWR ( * VPWR ) + USE POWER
  + ROUTED met4 1600 + SHAPE STRIPE ( 20000 5000 ) ( 20000 175000 ) ;
END SPECIALNETS
NETS 1702 ;
- n_415 ( _1034_ Y ) ( acc_reg_7_ D )
  + ROUTED met1 ( 41630 27370 ) ( 52900 * ) M1M2_PR ( 52900 30090 ) ;
END NETS
END DESIGN''', "Listing 13.2 - A hand-written DEF excerpt (not tool output) "
         "using SKY130 names. `#` comments are added for explanation; "
         "DEF uses them too.")
    bul(["**UNITS** sets database units per micron; every coordinate is an "
         "integer in these units.",
         "**ROW** lines define placement rows built from the site in the "
         "LEF; alternate rows are flipped (N / FS) so neighbouring rows "
         "share a VDD or VSS rail.",
         "**TRACKS** define the routing grid on each layer (start, count, "
         "pitch); detailed routers put wires on tracks.",
         "**COMPONENTS** are instances with a status: UNPLACED, PLACED "
         "(movable), FIXED (tool must not move) or COVER (physical only).",
         "**SPECIALNETS** hold power/ground and other pre-routed nets "
         "(shapes such as STRIPE, RING, FOLLOWPIN); **NETS** hold signal "
         "routing as wire segments and vias; `*` repeats the previous "
         "coordinate."])

    # ------------------------------------------------------------------------
    h2("Flat vs hierarchical implementation")
    p("A block of a few million instances can be implemented flat in one "
      "tool run. A modern SoC with hundreds of millions of instances cannot: "
      "run time, memory and team parallelism force a **hierarchical** "
      "flow, where the chip is partitioned into blocks (partitions, tiles) "
      "that are implemented independently and then assembled at the top.")
    tbl(["", "Flat", "Hierarchical"],
        [["Capacity", "Up to roughly several million instances per run "
          "(tool and machine dependent)", "Unlimited: each block within "
          "capacity"],
         ["QoR", "Best: global optimisation across boundaries", "Boundary "
          "paths constrained by budgets; some pessimism"],
         ["Schedule", "One team, serial", "Parallel teams; blocks can close "
          "at different times; reuse of identical blocks (instantiate a "
          "CPU tile 8 times)"],
         ["ECO / late changes", "Whole-chip rerun", "Only the affected block"],
         ["Overheads", "-", "Budgeting, pin assignment, feedthroughs, "
          "abstracts, top-level integration and sign-off"]],
        widths=[16, 40, 44], bold_first=True,
        caption="Table 13.3 - Flat vs hierarchical implementation.")
    diagram([
        "   +-------------------------------- chip top ---------------------------------+",
        "   |  IO ring / bumps                                                          |",
        "   |   +-----------+  +-----------+    +-------------+   +--------------+     |",
        "   |   | CPU tile  |  | CPU tile  |    |  GPU block  |   |  DDR PHY     |     |",
        "   |   | (block A) |  | (block A) |    |  (block B)  |   |  (hard IP)   |     |",
        "   |   +-----+-----+  +-----+-----+    +------+------+   +------+-------+     |",
        "   |         |  pins placed by top-level     |                   |             |",
        "   |   ======+==== top-level channels / NoC routing + repeaters ==+=========    |",
        "   |   +-----------+    top-level glue logic (clock ctrl, PMU, fabric)        |",
        "   |   | SRAM macs |                                                           |",
        "   +---------------------------------------------------------------------------+",
        "   block teams receive: netlist, SDC with budgets, pin positions, block outline,",
        "   power grid template, UPF slice; they return: LEF abstract, ETM/ILM, SPEF, GDS",
    ], "Figure 13.2 - Hierarchical implementation. Channel-less (abutted) "
       "floorplans route top-level nets through the blocks as feedthroughs "
       "instead of using channels.")
    h3("Partitioning, pin assignment and budgeting")
    bul(["**Partitioning** follows the logical hierarchy where possible "
         "(ownership, reuse, UPF domains), sized so each block fits the "
         "tool and the schedule; highly connected logic stays together.",
         "**Pin assignment** places block pins where the top-level route "
         "wants them, aligned between neighbouring blocks for abutment.",
         "**Timing budgeting** splits the clock period of every cross-block "
         "path between the blocks and the top-level route: e.g. for a 1 ns "
         "path launched in block A and captured in block B through 300 ps of "
         "top-level wire, A gets an output delay and B an input delay that "
         "leave each block a fair share. Budgets are written as SDC "
         "`set_input_delay` / `set_output_delay` on the block ports and "
         "refined as blocks mature.",
         "**Block-level vs top-level**: blocks close their internal paths "
         "and their budgets; the top-level team closes the interface paths "
         "with the actual block timing models and the real top-level routing."])
    h3("Block models: abstracts, ETM and ILM")
    tbl(["Model", "What it contains", "Pros / cons"],
        [["LEF abstract", "Outline, pins, routing obstructions per layer",
          "Physical only; tiny"],
         ["ETM (extracted timing model)", "A Liberty cell for the whole "
          "block: arcs from input pins to registers (setup/hold) and from "
          "clocks to outputs, generated by STA (e.g. PrimeTime "
          "extract_model)", "Compact, hides IP; loses SI and some context "
          "sensitivity; one model per corner/mode"],
         ["ILM (interface logic model)", "The actual netlist and parasitics "
          "of only the interface logic (first/last register stages and the "
          "logic between them and the ports)", "Accurate, supports SI and "
          "OCV; bigger than ETM"],
         ["Full netlist + SPEF", "Everything (flat STA)", "Exact; the final "
          "sign-off is often run flat on large servers"]],
        widths=[20, 46, 34], bold_first=True,
        caption="Table 13.4 - Block models used at the top level.")

    # ------------------------------------------------------------------------
    h2("Design planning and die-size estimation")
    p("Before RTL is final, the PD lead must commit to a die size (the "
      "package, the wafer cost and the number of dies per wafer depend on "
      "it; Chapter 23). The estimate combines the standard-cell area from "
      "synthesis (or from gate-count estimates), the hard-macro areas from "
      "the memory compiler and IP datasheets, a target **utilisation**, "
      "and the I/O ring or bump array.")
    _eqa(["core_area = std_cell_area / utilisation + sum(macro_area incl. halos)",
        "die_side  = max( sqrt(core_area / AR) + 2 * io_ring_depth ,",
        "                 pads_per_side * pad_pitch + 2 * corner )   (wire-bond, in-line pads)",
        "utilisation = std_cell_area / (core_area - macro_area)  : typically 60-80%"],
       "Equation 13.1 - First-order die-size model (AR = aspect ratio). "
       "Routing-limited designs (many layers of dense wiring) need lower "
       "utilisation; regular datapaths can go higher.")
    p("To feed the model with a real number, a small MAC and 16x32 register "
      "file tile was synthesised with Yosys 0.33 against the SKY130 HD "
      "typical Liberty, with the low-power special cells removed from the "
      "library as Chapter 11 recommended:")
    code(r'''// mac_rf.v: 16x32 register file + registered 16x16 multiply + 48-bit accumulate
module mac_rf (input clk, input rst_n, input we, input [3:0] wa, ra0, ra1,
               input [31:0] wd, input acc_clr, output reg [47:0] acc);
  reg [31:0] rf [0:15];
  reg [15:0] a_q, b_q; reg [31:0] p_q;
  always @(posedge clk) if (we) rf[wa] <= wd;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin a_q <= 0; b_q <= 0; p_q <= 0; acc <= 0; end
    else begin
      a_q <= rf[ra0][15:0]; b_q <= rf[ra1][15:0];
      p_q <= a_q * b_q;
      acc <= acc_clr ? 48'd0 : acc + {16'd0, p_q};
    end
endmodule
# syn.ys (Yosys): read_verilog mac_rf.v; synth -top mac_rf -flatten; memory_map
#   dfflibmap -liberty hd_trim.lib; abc -liberty hd_trim.lib; opt_clean
#   stat -liberty hd_trim.lib''', "Listing 13.3 - The tile and the Yosys "
         "script (hd_trim.lib = the SKY130 HD tt_025C_1v80 Liberty with the "
         "50 lpflow/probe/delay cells removed).")
    out(["   Number of cells:               2163",
         "     sky130_fd_sc_hd__a21oi_1       67",
         "     sky130_fd_sc_hd__a22oi_1       64",
         "     sky130_fd_sc_hd__dfrtp_1      112",
         "     sky130_fd_sc_hd__dfxtp_1      256",
         "     sky130_fd_sc_hd__maj3_1       112",
         "     sky130_fd_sc_hd__mux2_1       256",
         "     sky130_fd_sc_hd__mux4_2       160",
         "     sky130_fd_sc_hd__nand2_1      166",
         "     sky130_fd_sc_hd__nor2_1       156",
         "     sky130_fd_sc_hd__xnor2_1      213",
         "     sky130_fd_sc_hd__xor2_1       203",
         "   ...  (28 further cell types with fewer instances)",
         "   Chip area for module '\\mac_rf': 23825.350400"],
        "Excerpt of the Yosys `stat -liberty` report (real run; the "
        "'...' line is an elision). Area in um^2. The 256 dfxtp + 256 mux2 "
        "are the register file (flops with recirculating write-enable "
        "muxes); maj3/xor/xnor are the adder cells of the multiplier and "
        "accumulator.")
    p("Flip-flops alone are 112 x 25.02 + 256 x 20.02 = about 7,930 um^2, one "
      "third of the tile - typical of register-heavy logic and a reason "
      "register files of this size are often replaced by a latch array or an "
      "SRAM macro. Now scale up to an accelerator of 64 such tiles plus "
      "glue logic, four SRAM macros and a PLL, and check both the core-"
      "limited and the pad-limited die size:")
    code(r'''# die_size.py - core-limited vs pad-limited die estimate
tile_area = 23825.35                   # um^2, parsed from the Yosys log above
std_area  = tile_area * 64 * 1.25      # 64 tiles + 25% glue (control, DFT, CTS buffers)
macros    = [("sram_8kx32", 4, 620.0, 410.0), ("pll", 1, 300.0, 300.0)]  # w, h (um)
halo, util, aspect = 10.0, 0.65, 1.0
io_ring, n_pads, pad_pitch, corner = 250.0, 180, 80.0, 250.0
macro_area = sum(c*(w+2*halo)*(h+2*halo) for _, c, w, h in macros)
core_area  = std_area/util + macro_area
core_w     = math.sqrt(core_area/aspect)
die_core   = core_w + 2*io_ring                    # core-limited die side
side_pad   = n_pads/4*pad_pitch + 2*corner         # pad-limited die side''',
         "Listing 13.4 - Die-size estimate (macro sizes and pad parameters "
         "are assumed example values; print statements elided).")
    out(["std-cell area (synthesis x 64 tiles x 1.25) =    1.906 mm^2",
         "macro area incl. halos                   =    1.203 mm^2",
         "core area @ 65% utilisation             =    4.136 mm^2  (2034 x 2034 um)",
         "die side, core-limited                   =     2534 um",
         "die side, pad-limited (180 pads @ 80 um) =     4100 um",
         "=> die 4100 x 4100 um = 16.81 mm^2, pad-limited",
         "   in-line 80 um   : pad side  4100 um -> die 16.81 mm^2 (pad-limited)",
         "   staggered 2-row : pad side  2300 um -> die 6.42 mm^2 (core-limited)",
         "   util 0.55 -> core 4.67 mm^2, core-limited die 7.08 mm^2",
         "   util 0.65 -> core 4.14 mm^2, core-limited die 6.42 mm^2",
         "   util 0.75 -> core 3.74 mm^2, core-limited die 5.93 mm^2",
         "   util 0.85 -> core 3.45 mm^2, core-limited die 5.55 mm^2"],
        "Output of die_size.py. With 180 in-line pads the die would be 2.6x "
        "larger than the logic needs; staggered pads (or flip-chip) make it "
        "core-limited again.")
    box("intuit", "Pad-limited vs core-limited",
        "A **pad-limited** die is larger than its logic requires because the "
        "perimeter must hold all the pads; the empty core area is wasted "
        "silicon (often filled with extra decap). A **core-limited** die is "
        "sized by its contents. Remedies for pad limitation: staggered or "
        "multi-row pads, fewer pads (serial interfaces instead of wide "
        "parallel buses), or flip-chip with an area bump array, where pad "
        "count scales with area instead of perimeter.")
    h3("Other planning decisions")
    bul(["**Aspect ratio**: close to 1 unless the package, a wide PHY edge "
         "or a reticle-stitching plan demands otherwise; extreme aspect "
         "ratios lengthen global wires and clock trees.",
         "**Macro count and shapes**: memory compilers offer many "
         "configurations (words x bits x mux factor, banking); the choice "
         "changes both area and aspect (a tall thin SRAM may fit a channel "
         "better).",
         "**Metal stack**: how many layers (cost) and which are reserved for "
         "power, clock and top-level buses.",
         "**Package and bump/ball plan**: co-designed with the package team "
         "from the start (Chapter 20).",
         "**Utilisation targets per block**: lower for congested, "
         "timing-critical or heavily multi-voltage blocks."])

    # ------------------------------------------------------------------------
    h2("MCMM: multi-corner, multi-mode setup")
    p("A design must meet timing in several **modes** (functional, scan "
      "shift, scan capture, low-power modes, each with its own SDC) at "
      "several **corners** (process/voltage/temperature for cells combined "
      "with RC corners for wires). Each mode-corner pair is a **scenario** "
      "or **analysis view**. P&R optimises all active scenarios "
      "concurrently: setup views at slow corners, hold views at fast corners "
      "(and at slow corners too, because hold can fail anywhere with OCV).")
    code(r'''# mmmc.tcl - Innovus-style MMMC view definition (example, not run)
create_library_set -name LIB_SS -timing {lib/ss_0p72v_125c.lib lib/sram_ss.lib}
create_library_set -name LIB_FF -timing {lib/ff_0p88v_m40c.lib lib/sram_ff.lib}
create_rc_corner   -name RC_CW  -qrc_tech tech/cworst.qrc  -temperature 125
create_rc_corner   -name RC_CB  -qrc_tech tech/cbest.qrc   -temperature -40
create_rc_corner   -name RC_RCW -qrc_tech tech/rcworst.qrc -temperature 125
create_delay_corner -name DC_SS_CW  -library_set LIB_SS -rc_corner RC_CW
create_delay_corner -name DC_SS_RCW -library_set LIB_SS -rc_corner RC_RCW
create_delay_corner -name DC_FF_CB  -library_set LIB_FF -rc_corner RC_CB
create_constraint_mode -name FUNC -sdc_files {sdc/func.sdc}
create_constraint_mode -name SHIFT -sdc_files {sdc/scan_shift.sdc}
create_analysis_view -name func_ss_cw  -constraint_mode FUNC  -delay_corner DC_SS_CW
create_analysis_view -name func_ss_rcw -constraint_mode FUNC  -delay_corner DC_SS_RCW
create_analysis_view -name func_ff_cb  -constraint_mode FUNC  -delay_corner DC_FF_CB
create_analysis_view -name shift_ff_cb -constraint_mode SHIFT -delay_corner DC_FF_CB
set_analysis_view -setup {func_ss_cw func_ss_rcw} -hold {func_ff_cb shift_ff_cb}''',
         "Listing 13.5 - MMMC setup. Synopsys tools express the same idea "
         "with create_mode / create_corner / create_scenario; OpenROAD "
         "reads multiple Liberty corners with define_corners. Corner names "
         "and file names here are placeholders.")
    tbl(["RC corner", "Meaning", "Typically worst for"],
        [["Cworst / Cbest", "Maximum / minimum total capacitance",
          "Short, load-dominated paths (Cworst: setup); hold (Cbest)"],
         ["RCworst / RCbest", "Maximum / minimum R*C product (thin, narrow "
          "wires)", "Long wire-dominated paths (RCworst: setup)"],
         ["Typical", "Nominal", "Power and typical-performance reporting"],
         ["CCworst variants", "Maximum coupling capacitance", "SI / "
          "crosstalk analysis"]],
        widths=[20, 44, 36], bold_first=True,
        caption="Table 13.5 - Interconnect corners. Temperature inversion at "
                "advanced nodes (cells slower when cold at low voltage) means "
                "setup must be checked cold as well as hot.")
    box("warn", "PITFALL: too many scenarios, or the wrong ones",
        "Every active scenario costs run time and memory. Teams start with a "
        "small dominant set (e.g. 2 setup + 2 hold) during placement and "
        "add the full sign-off set (often dozens) for post-route "
        "optimisation. Dropping a scenario that later turns out to be "
        "limiting (a low-voltage DVFS point, a scan mode at a fast corner) "
        "is a classic cause of late surprises. Review the scenario list "
        "with the STA sign-off owner.")

    # ------------------------------------------------------------------------
    h2("The PD tool landscape")
    tbl(["Task", "Cadence", "Synopsys", "Siemens / others", "Open source"],
        [["Physically aware synthesis", "Genus (iSpatial)", "Fusion Compiler, "
          "DC NXT", "-", "Yosys + ABC"],
         ["Place and route", "Innovus", "IC Compiler II, Fusion Compiler",
          "Aprisa (Siemens)", "OpenROAD"],
         ["Extraction", "Quantus", "StarRC", "Calibre xACT", "OpenRCX"],
         ["STA", "Tempus", "PrimeTime", "-", "OpenSTA"],
         ["Power / IR / EM", "Voltus", "PrimePower, RedHawk-SC "
          "(Ansys, now part of Synopsys)", "mPower", "PDNSim (OpenROAD)"],
         ["Physical verification", "Pegasus", "IC Validator", "Calibre",
          "Magic, KLayout, Netgen"],
         ["Equivalence", "Conformal", "Formality", "-", "Yosys eqy (limited)"]],
        widths=[20, 18, 24, 18, 20], bold_first=True,
        caption="Table 13.6 - Main tools by task (product names change; "
                "check current vendor offerings). Chapter 24 walks through "
                "the open-source flow.")

    # ------------------------------------------------------------------------
    h2("Teams and hand-offs")
    tbl(["From", "To", "Deliverables", "Acceptance checks"],
        [["RTL / front-end", "Synthesis", "Frozen RTL, SDC, UPF, file list",
          "Lint, CDC, UPF lint clean; SDC reviewed"],
         ["Synthesis + DFT", "PD", "Scan-inserted netlist, SDC per mode, "
          "UPF', scan DEF, reports", "LEC RTL vs netlist; timing with "
          "reasonable slack; no unmapped cells"],
         ["PD lead", "Block PD teams", "Floorplan/outline, pins, budgets, "
          "power-grid spec, partition UPF", "Agreed in a floorplan review"],
         ["Block PD", "Top-level PD / STA", "LEF, ETM/ILM, netlist, SPEF, "
          "GDS, reports", "Block sign-off checklist (Appendix A)"],
         ["Top-level PD", "Sign-off / tapeout", "Final GDS/OASIS, netlists, "
          "SPEF, all sign-off reports and waivers", "Tapeout checklist "
          "(Chapter 19)"],
         ["PD + package", "Package team", "Bump/pad coordinates, die size, "
          "power map", "Package-die co-design review (Chapter 20)"]],
        widths=[16, 18, 34, 32], bold_first=True,
        caption="Table 13.7 - Typical hand-offs around physical design.")
    box("expert", "Interview insight: 'What do you check first when you get a new netlist?'",
        "A strong answer: import it and look for unresolved references and "
        "black boxes, multiply-driven or floating nets, assign statements and "
        "tie-offs, dont_use or unexpected cells, scan chain presence, the "
        "cell count/area against the synthesis report, and run a quick "
        "zero-wire-load and placed timing check with the SDC to find "
        "missing clocks, unconstrained endpoints and obviously infeasible "
        "paths before investing hours in placement.")

    h2("Summary")
    bul(["PD converts a netlist into mask geometry through setup, floorplan, "
         "power plan, placement, CTS, routing and sign-off, with ECO loops.",
         "Inputs: netlist, SDC, UPF, tech/cell LEF, Liberty per corner, RC "
         "techfiles, rule decks; outputs: GDS/OASIS, netlists, DEF, SPEF, "
         "SDF, block models and reports.",
         "Real LEF data show the universal metal-stack pattern: thin, "
         "resistive lower layers and thick, low-resistance upper layers "
         "for power and global routing.",
         "Large designs are implemented hierarchically with partitions, pin "
         "assignment, timing budgets and block models (LEF, ETM, ILM).",
         "Die size = max(core-limited, pad-limited); utilisation, macros "
         "with halos, aspect ratio and the I/O strategy decide it.",
         "MCMM defines modes x corners as analysis views; choose the "
         "dominant scenarios early and the full set before sign-off."])
    h2("Exercises")
    bul(["Using die_size.py, find the utilisation at which the in-line-pad "
         "design stops being pad-limited if the pad count is reduced to 120.",
         "Explain why the DEF in Listing 13.2 alternates N and FS rows. What "
         "would go wrong if all rows were N?",
         "A path from block A to block B has a 1.25 GHz clock, 150 ps of "
         "top-level wire delay and 80 ps of clock uncertainty. Propose "
         "input/output delay budgets for both blocks and explain your split.",
         "List the MMMC views you would activate during placement and during "
         "post-route optimisation for a design with two DVFS points and a "
         "scan mode, at a node that shows temperature inversion.",
         "In the SKY130 table, how much longer can a met5 wire be than a "
         "minimum-width met1 wire for the same resistance? Why is met5 not "
         "used for all signal routing?"], ordered=True)


# =============================================================================
#      CHAPTER 14 - FLOORPLANNING, POWER PLANNING AND THE I/O RING
# =============================================================================
def _ch14():
    chapter("Floorplanning, Power Planning and the I/O Ring")
    p("The floorplan is the single most leveraged decision in physical "
      "design. A good floorplan makes placement, clock tree synthesis and "
      "routing converge almost by themselves; a bad one produces congestion, "
      "long wires and timing violations that no amount of optimisation can "
      "fix, and it is expensive to change once the power grid, macros and "
      "pins are frozen. Experienced PD engineers spend days on a floorplan "
      "and review it with the architects, the package team and the power-"
      "integrity team before running a single full placement.")
    p("This chapter covers the physical skeleton of a chip or block: core "
      "and rows, the I/O ring or bump array, macro placement, blockages, "
      "the power delivery network (PDN) with its IR-drop and EM budgets, "
      "decoupling capacitance, power-switch placement, well taps and "
      "endcaps, pin assignment and the checks that say a floorplan is ready.")

    # ------------------------------------------------------------------------
    h2("Die, core, rows and sites")
    diagram([
        "  +----------------------------- die (DIEAREA) ------------------------------+",
        "  | corner |  IO  |  IO  |  IO  |  IO  |  IO  |  IO  |  IO  |  IO  | corner |",
        "  +--------+------+------+------+------+------+------+------+------+--------+",
        "  |  IO    |  core-to-IO spacing (power ring lives here)             |  IO    |",
        "  +--------+  +-----------------------------------------------------+ +------+",
        "  |  IO    |  | row 3  FS   |VSS|  cells  cells  cells  cells     | |  IO  |",
        "  |        |  | row 2  N    |VDD|  <- rows share rails (flipped)  | |      |",
        "  |  IO    |  | row 1  FS   |VSS|  +--------+  halo              | |  IO  |",
        "  |        |  | row 0  N    |VDD|  | SRAM   |  (no cells)        | |      |",
        "  |  IO    |  |                   +--------+                     | |  IO  |",
        "  |        |  +---------------------- core area -----------------+ |      |",
        "  +--------+------+------+------+------+------+------+------+------+--------+",
        "  | corner |  IO  |  IO  |  IO  |  IO  |  IO  |  IO  |  IO  |  IO  | corner |",
        "  +--------------------------------------------------------------------------+",
    ], "Figure 14.1 - Die, I/O ring, core and rows. Rows are made of sites; "
       "alternate rows are flipped so VDD and VSS rails are shared.")
    bul(["The **site** is the placement grid unit from the LEF: width = one "
         "placement pitch (often the contacted poly pitch), height = the "
         "cell height (in SKY130 HD `unithd` is 0.46 x 2.72 um). Every "
         "standard cell's width is an integer number of sites.",
         "**Rows** fill the core; each row has an orientation (N or FS). The "
         "core height is normally an integer number of rows, and the core "
         "edges are snapped to the site grid and to the manufacturing grid.",
         "The **core** must leave room between it and the I/O ring for the "
         "core power ring and for routing from the pads to the core pins.",
         "Multi-height cells (double-height flops, multi-row cells at "
         "advanced nodes) require rows to be built so that their rails "
         "line up."])
    _eqa(["rows       = floor(core_height / row_height)",
        "sites/row  = floor(core_width / site_width)",
        "example SKY130 HD: core 2034 um x 2034 um -> 747 rows x 4421 sites"],
       "Equation 14.1 - Row arithmetic.")

    # ------------------------------------------------------------------------
    h2("The I/O ring")
    p("In a wire-bond chip the I/O cells form a ring around the core; each "
      "signal and supply pad has a bond pad connected by a gold or copper "
      "wire to the package lead frame or substrate. Pad-limited vs core-"
      "limited sizing was quantified in Chapter 13; here is how the ring "
      "itself is built.")
    bul(["**Pad order** comes from the package and board: the package team "
         "assigns balls/leads, the PD team maps them to pad positions so that "
         "bond wires do not cross and have acceptable lengths and angles.",
         "**Supply pads** are interleaved according to the I/O library's "
         "SSO and ESD rules (e.g. one VDDIO/VSSIO pair per N signal pads) and "
         "the core current (core VDD/VSS pads spread around the ring so the "
         "core ring is fed from all sides).",
         "**Corner cells** continue the pad-ring rails; **pad fillers** close "
         "the gaps so the I/O rails and the ESD bus are continuous; "
         "**break (cut) cells** separate I/O voltage banks.",
         "**Staggered pads** (two rows, inner and outer) halve the effective "
         "pitch at the cost of longer bond wires and bonding constraints.",
         "The I/O cells' core-side pins are connected to core logic with "
         "ordinary signal routing; timing to/from the pads is part of the "
         "I/O constraints (set_input_delay/set_output_delay, Chapter 9)."])
    h3("Flip-chip: bumps and the redistribution layer")
    diagram([
        "  top view (bump array)                       cross-section",
        "   o   o   o   o   o   o   o   o               package substrate",
        "     V   G   V   G   V   G   V                ===========================",
        "   o   o   o   o   o   o   o   o                  |  |  |  |  solder bumps",
        "     G   V   G   V   G   V   G                ----o--o--o--o------------- ",
        "   S   S   o   o   o   o   S   S               RDL (redistribution layer,",
        "   S   S   V   G   V   G   S   S                thick Al/Cu top metal)",
        "   S   S   o   o   o   o   S   S               passivation + top vias",
        "  V/G: core power/ground bumps over the core   ---- metal stack ---------",
        "  S  : signal bumps near their I/O cells        ---- devices (face down) ----",
        "  o  : further power/ground bumps              silicon substrate (backside up)",
    ], "Figure 14.2 - Flip-chip: bumps over the whole die area. Power bumps "
       "are distributed over the core, so current enters the grid vertically "
       "close to where it is used.")
    bul(["Bumps (C4 solder or copper pillar) sit on a regular array with a "
         "pitch typically in the range of about 100-200 um for package "
         "bumps (much finer for micro-bumps and hybrid bonding in 2.5D/3D, "
         "Chapter 20).",
         "The **RDL** (redistribution layer), a thick top metal (often "
         "aluminium), routes each bump to its I/O cell or power grid "
         "entry point. RDL routing is done by the P&R tool or a package "
         "co-design tool, with its own DRC.",
         "I/O cells can be placed in the core area ('area I/O') or still at "
         "the periphery; power bumps feed the grid directly from above, "
         "which makes IR drop far smaller than with a peripheral ring (see "
         "the IR-drop run later in this chapter).",
         "The bump map is a joint deliverable of the PD and package teams "
         "and is frozen early because the substrate design takes weeks."])

    # ------------------------------------------------------------------------
    h2("Macro placement")
    p("Hard macros (SRAMs, ROMs, register files, PLLs, PHYs, analog IP) are "
      "big, rectangular, fixed obstacles with many pins on one or more "
      "edges. They are placed before the standard cells, usually by hand or "
      "with a macro placer followed by manual refinement.")
    tbl(["Guideline", "Why"],
        [["Place macros at the core periphery, pins facing the core",
          "Keeps the centre free for standard cells and gives short, "
          "uncongested pin access"],
         ["Follow the data flow: macros near the logic that uses them, "
          "and in the order data travels", "Shorter nets, less buffering "
          "and fewer long timing paths"],
         ["Leave channels between macros sized for the pins and the "
          "routes through them (and for buffers)", "Narrow channels with "
          "many pins become routing hot-spots"],
         ["Use halos / keep-outs around macros", "Room for pin access, "
          "power connections and to keep noisy cells away"],
         ["Orient macros so that pins face each other where they connect, "
          "and respect allowed orientations (some macros must not be "
          "rotated because of poly direction)", "Legal and short "
          "connections"],
         ["Align macros and avoid 'notches' and thin slivers of standard-"
          "cell area", "Slivers become congested, poorly-placed regions"],
         ["Keep analog/sensitive macros at the die edge near their pads, "
          "away from high-activity logic", "Noise isolation (Chapter 12)"],
         ["Group identical macros, abut where the macro allows it (shared "
          "rings)", "Area efficiency, regular power grid"]],
        widths=[55, 45], bold_first=False,
        caption="Table 14.1 - Macro-placement guidelines.")
    h3("Blockages")
    tbl(["Blockage", "Effect", "Typical use"],
        [["Hard placement blockage", "No standard cells at all", "Macro "
          "halos, channels that must stay empty, analog keep-outs"],
         ["Soft placement blockage", "No cells during initial placement; "
          "optimisation may put buffers there", "Narrow channels between "
          "macros (buffers allowed, logic not)"],
         ["Partial placement blockage", "Maximum cell density in the "
          "area (e.g. 40%)", "Congested regions, around high-pin-density "
          "macros"],
         ["Routing blockage", "No routing on given layers", "Over analog "
          "macros, under bumps, for shielding"]],
        widths=[24, 38, 38], bold_first=True,
        caption="Table 14.2 - Placement and routing blockages.")

    # ------------------------------------------------------------------------
    h2("Power delivery network design")
    p("The PDN carries current from the package (pads or bumps) through a "
      "ring, a mesh of wide straps on the upper metals, via stacks, and the "
      "thin **follow-pin rails** on metal 1 that run along every row to the "
      "cells' VDD/VSS pins. Its job is to keep the voltage at every cell "
      "within budget (IR drop), to keep current density in every wire and "
      "via below the electromigration limit, and to use as little routing "
      "resource as possible.")
    diagram([
        "     VDD ring (met4/met5)                               bump or pad",
        "  +==================================================+     |",
        "  ||   |       |       |       |       |       |    ||     v",
        "  ||===+=======+=======+=======+=======+=======+====||  <- met5 horizontal straps",
        "  ||   |       |       |       |       |       |    ||",
        "  ||   |  met4 vertical straps (pitch P, width W)   ||",
        "  ||   |       |       |       |       |       |    ||",
        "  ||===+=======+=======+=======+=======+=======+====||",
        "  ||---+-------+-------+-------+-------+-------+----||  <- met1 follow-pin rails",
        "  ||---+-------+-------+-------+-------+-------+----||     (one per row boundary)",
        "  +==================================================+",
        "  at every met4 x met1 crossing: via stack met1-via-met2-via2-met3-via3-met4",
    ], "Figure 14.3 - A typical standard-cell PDN: ring, orthogonal "
       "upper-metal straps, via stacks and follow-pin rails. VSS is "
       "interleaved with VDD in the same pattern.")
    h3("Choosing pitch and width")
    bul(["**Metal budget**: power straps typically take something like 10-30% "
         "of the tracks on the layers they use (more on the top layers, less "
         "on the signal-critical middle layers). Every strap track is a "
         "track signals cannot use.",
         "**IR drop** falls with more metal; for a mesh fed from its edges "
         "the drop depends mainly on the metal **density** (W/P), while the "
         "pitch sets the drop along the follow-pin rails between straps.",
         "**Via stacks** at every strap/rail crossing block routing tracks on "
         "the intermediate layers; very dense straps on a high layer "
         "multiply the via-stack blockage below it.",
         "**EM**: each strap segment and via array must carry its current "
         "within the average (and RMS/peak) current-density limits from the "
         "technology LEF / foundry EM rules at the target junction "
         "temperature and lifetime.",
         "**Alignment**: straps aligned to the placement/routing grid and "
         "(at advanced nodes) to the power-rail and via rules; standard cells "
         "often must not sit under certain strap/via positions (pin access)."])
    h3("IR-drop budget")
    _eqa(["V_cell = V_pkg - (I * R)_package - (I * R)_grid - L * di/dt - (dynamic droop)",
        "typical budget: static (average-current) IR drop  <= ~2-3% of VDD",
        "                dynamic (peak, time-domain) drop    <= ~5-10% of VDD total",
        "STA must then be signed off with the voltage actually seen, or with",
        "a voltage-aware derate (IR-drop-aware STA, Chapter 18)"],
       "Equation 14.2 - IR-drop budgeting. Exact percentages are set per "
       "project; the library corner voltage (e.g. 0.72 V for a 0.8 V "
       "nominal at -10%) already includes part of the regulator tolerance.")
    p("To see how pitch, width and feed style interact, the script below "
      "solves the static IR drop of a VDD mesh numerically. It uses the real "
      "SKY130 sheet resistances and EM limits read from the technology LEF "
      "in Chapter 13: met4 vertical and met5 horizontal straps of equal "
      "width W at pitch P over a 2 x 2 mm core drawing a uniform 0.5 W/mm^2 "
      "(1.11 A at 1.8 V). The mesh is fed either by an ideal ring on all "
      "four sides (wire bond) or by ideal flip-chip bumps on a 200 um grid. "
      "Each strap crossing is a node that sinks the current of its P x P "
      "tile; Kirchhoff's current law gives one linear equation per node, "
      "solved with numpy. The drop along the met1 rails between two straps "
      "is added analytically.")
    _eqa(["node k:  sum_j g_kj * (V_j - V_k) + g_feed * (VDD - V_k) = I_k,   I_k = J * P^2",
        "g(met4 segment) = W / (Rsq4 * P),   g(met5 segment) = W / (Rsq5 * P)",
        "rail drop between straps (uniform load, fed at both ends) = i' * r' * P^2 / 8",
        "   i' = J * row_height (A per um of rail),  r' = Rsq1 / W_rail (ohm per um)"],
       "Equation 14.3 - The mesh model (a 2D resistive network) and the rail "
       "drop.")
    code(r'''# irdrop.py - static IR drop of a VDD mesh (SKY130 Rsq / EM from the tech LEF)
import numpy as np
VDD, CORE, J = 1.8, 2000.0, 0.5e-6 / 1.8   # V, um, A/um^2 (0.5 W/mm^2 at 1.8 V)
RSQ4, RSQ5, RSQ1 = 0.047, 0.0285, 0.125    # ohm/sq  (met4, met5, met1)
EM4 = 6.8e-3                                # A per um of met4 width (Iavg, 90 C)
ROW, W_RAIL, BUMP = 2.72, 0.48, 200.0       # row height, met1 rail width, bump pitch
def mesh_drop(P, W4, W5, feed):
    n = int(round(CORE / P)) - 1            # interior strap intersections per side
    A = np.zeros((n*n, n*n)); b = np.full(n*n, J * P * P)    # node sink current
    g4, g5 = W4 / (RSQ4 * P), W5 / (RSQ5 * P)                # segment conductances
    step = int(round(BUMP / P))
    for i in range(n):
        for j in range(n):
            k = i * n + j
            for di, dj, g in ((1, 0, g4), (-1, 0, g4), (0, 1, g5), (0, -1, g5)):
                ii, jj = i + di, j + dj
                if 0 <= ii < n and 0 <= jj < n:
                    A[k, k] -= g; A[k, ii * n + jj] += g
                elif feed == "ring":                            # tied to the ring
                    A[k, k] -= g; b[k] -= g * VDD
            if feed == "bump" and (i + 1) % step == 0 and (j + 1) % step == 0:
                A[k, k] -= 1e3; b[k] -= 1e3 * VDD              # ~ideal bump (1 mohm)
    V = np.linalg.solve(A, b).reshape(n, n)
    i_edge = ((VDD - V[0, :]) * g4).max() if feed == "ring" else 0.0
    return VDD - V.min(), i_edge
def rail_drop(P):     # uniform load on a rail fed from both ends: i r P^2 / 8
    return J * ROW * (RSQ1 / W_RAIL) * P * P / 8
# ... sweep (P, W) for both feeds and print (see output)''',
         "Listing 14.1 - The IR-drop solver (the sweep and print loop is "
         "elided). The largest case has 79 x 79 = 6,241 nodes; the whole "
         "sweep runs in a few seconds.")
    out(["Core 2000 um square, 1.11 A total (0.5 W/mm^2 at 1.8 V)",
         " feed  pitch  W     met4   mesh   rail   total   %VDD   ring-edge I / EM limit",
         "       [um]  [um]   use%   [mV]   [mV]   [mV]           per strap [mA]",
         " ring   400   8.0    2.0   131.1    3.9   135.0    7.5%     40.2 /  54.4 ok",
         " ring   200   8.0    4.0    71.7    1.0    72.7    4.0%     25.6 /  54.4 ok",
         " ring   100   8.0    8.0    36.1    0.2    36.3    2.0%     14.1 /  54.4 ok",
         " ring    50   8.0   16.0    18.1    0.1    18.1    1.0%      7.4 /  54.4 ok",
         " ring   400  40.0   10.0    26.2    3.9    30.1    1.7%     40.2 / 272.0 ok",
         " ring   200  20.0   10.0    28.7    1.0    29.7    1.6%     25.6 / 136.0 ok",
         " ring   100  10.0   10.0    28.9    0.2    29.1    1.6%     14.1 /  68.0 ok",
         " ring    50   5.0   10.0    28.9    0.1    29.0    1.6%      7.4 /  34.0 ok",
         " bump   100   8.0    8.0     2.7    0.2     3.0    0.2%      -",
         " bump    50   8.0   16.0     2.3    0.1     2.4    0.1%      -",
         " bump    25   8.0   32.0     1.6    0.0     1.6    0.1%      -",
         " bump   100  10.0   10.0     2.2    0.2     2.4    0.1%      -",
         " bump    50   5.0   10.0     3.7    0.1     3.8    0.2%      -",
         " bump    25   2.5   10.0     4.9    0.0     5.0    0.3%      -"],
        "Output of irdrop.py (python3 + numpy 2.4). VDD network only; the "
        "VSS network adds a similar drop (ground bounce), so the total "
        "supply collapse is about twice these numbers.")
    p("What the run shows:")
    bul(["**With a fixed strap width**, halving the pitch halves the mesh "
         "drop - but only because it doubles the metal used (2% -> 16% of "
         "met4).",
         "**At a fixed metal density** (10%), the ring-fed mesh drop is "
         "almost independent of pitch (about 29 mV): a fine mesh of narrow "
         "straps and a coarse mesh of wide straps have the same effective "
         "sheet resistance. The pitch then matters for the local met1 rail "
         "drop (3.9 mV at 400 um vs 0.1 mV at 50 um) and for how evenly "
         "cells are served - and a finer pitch costs more via stacks.",
         "**Feeding from bumps** instead of the periphery cuts the drop by "
         "roughly 10x for the same metal, because current travels at most "
         "about half a bump pitch laterally instead of half the die. This "
         "is why high-power chips are flip-chip. With bumps, finer, narrower "
         "straps at the same density show slightly __more__ drop: the current "
         "crowds into the few straps next to each bump.",
         "**EM** is comfortably met on the met4 straps here; in real designs "
         "the limiting EM items are usually the via arrays at the ring and "
         "at the bump/pad connections and narrow lower-level straps, which "
         "this model does not include.",
         "Real IR analysis (Voltus, RedHawk-SC, PDNSim) extracts the whole "
         "grid including vias, uses the actual per-instance currents from "
         "power analysis, and includes the package model; this simple model "
         "is for sizing the grid before placement."])
    box("warn", "PITFALL: designing the grid for average power only",
        "A grid that meets static IR drop with average current can still "
        "fail dynamic IR drop when a large block wakes up, when a clock "
        "starts, or during scan capture with all flops toggling in the same "
        "cycle. Size the grid with a power map that includes the realistic "
        "worst-case activity per region (from vectorless peak estimates or "
        "early FSDB) and plan decap for the transients.")
    h3("Decoupling capacitance")
    p("Decap cells (and the intrinsic capacitance of non-switching logic) "
      "act as a local charge reservoir that supplies current for the first "
      "nanoseconds of a transient, before the grid and package inductance "
      "can respond.")
    _eqa(["C_decap >= Q / dV_allowed = I_step * t_response / dV_allowed",
        "example: 0.5 A step in a region, package responds after ~1 ns,",
        "         allowed droop 40 mV  ->  C >= 0.5 * 1e-9 / 0.04 = 12.5 nF"],
       "Equation 14.4 - Decap sizing, first order. Thin gate oxide gives "
       "on the order of 10 fF per um^2 of gate area (less per um^2 of decap "
       "cell), so 12.5 nF is on the order of a square millimetre - a real area cost, which is why decap is "
       "concentrated near high-activity regions and why MIM/deep-trench "
       "capacitors exist in some processes.")
    bul(["Decap cells leak (they are large gate-oxide capacitors); use them "
         "where needed, not everywhere, and prefer thick-oxide or lower-leakage "
         "decap variants where the library offers them.",
         "Standard flows insert decap after placement and fill remaining "
         "gaps with decap-type filler cells in hot regions and plain fillers "
         "elsewhere.",
         "Pre-placed decap near clock roots, around large macros and in "
         "switched domains' always-on areas is part of the floorplan."])

    # ------------------------------------------------------------------------
    h2("Power domains and power switches in the floorplan")
    p("Each UPF power domain (Chapter 11) becomes a physical region "
      "(voltage area / power domain region) with its own grid. Cells of a "
      "domain must be placed inside its region; always-on cells inside a "
      "switched domain need the real supply routed to their secondary pins.")
    diagram([
        "  column-style (grid) switches                 ring-style switches",
        "  +------------------------------+             +===========================+",
        "  |  S   .   .   S   .   .   S   |             || S S S S S S S S S S S S ||",
        "  |  S   .   .   S   .   .   S   |             || S +-------------------+ S ||",
        "  |  S  cells .  S  cells .  S   |             || S |  switched domain  | S ||",
        "  |  S   .   .   S   .   .   S   |             || S |  (no switches      | S ||",
        "  |  S   .   .   S   .   .   S   |             || S |   inside)         | S ||",
        "  +------------------------------+             || S +-------------------+ S ||",
        "  S = header columns under the VDD straps;     || S S S S S S S S S S S S ||",
        "  daisy-chained enable runs through them       +===========================+",
    ], "Figure 14.4 - Switch placement. Columns (a regular array under the "
       "power straps) give lower IR drop inside the domain and are the norm "
       "for standard-cell domains; rings suit macros and small domains.")
    bul(["The number of switches is set by the domain's peak current and the "
         "allowed IR drop across the switches in the ON state; their chaining "
         "is set by the rush-current limit (Chapter 11).",
         "Level shifters and isolation cells are placed at the domain boundary "
         "(in the domain given by the UPF `-location`), often in dedicated "
         "rows or regions with both supplies available.",
         "Domain regions need spacing or a guard between them when their "
         "wells are at different potentials (different supply voltages "
         "require separate n-wells for the PMOS)."])

    # ------------------------------------------------------------------------
    h2("Well taps, endcaps and physical-only cells")
    bul(["**Well-tap cells** connect the n-well to VDD and the p-substrate/"
         "p-well to VSS at regular intervals. Modern standard cells are "
         "'tapless' (no taps inside each cell) to save area, so the flow must "
         "insert tap cells in a checkerboard at a maximum distance set by the "
         "foundry's latch-up rule; the open-source SKY130 flows place them "
         "every 13-14 um (the physical-only cell `tapvpwrvgnd_1` seen in "
         "Chapter 11).",
         "**Endcap (boundary) cells** terminate every row at the core and "
         "macro edges, completing the well and implant layers so that the "
         "last real cell sees a regular environment (required by DRC at "
         "advanced nodes).",
         "Other physical-only cells: **filler** cells (continuity of wells "
         "and rails in gaps), **decap** fillers, **tie-hi/tie-lo** cells "
         "(constant inputs never connect a gate directly to a rail, for ESD "
         "reasons), spare cells for ECOs (Chapter 19), and antenna diodes.",
         "All of these are inserted during floorplan (taps, endcaps) or at "
         "the end of placement/routing (fillers), are in the LEF but not "
         "(or only trivially) in Liberty, and appear in the netlist used for "
         "LVS."])

    # ------------------------------------------------------------------------
    h2("Pin assignment")
    p("For a block, the ports must be placed on its boundary where the "
      "top-level route or the abutting neighbour expects them: on the "
      "correct layer (usually middle layers, with the preferred direction "
      "perpendicular to the edge), on the routing grid, with enough spacing, "
      "grouped by bus, and close to the logic that uses them. Top-down "
      "flows derive block pin positions from a top-level trial route; the "
      "positions are frozen early because they are shared by two teams. "
      "Clock pins are placed where the top-level clock can reach them with "
      "minimal insertion delay, and critical timing pins face their "
      "partners.")

    # ------------------------------------------------------------------------
    h2("A floorplan script")
    code(r'''# floorplan.tcl - OpenROAD-style floorplan + PDN for SKY130 HD (example, not run;
# option names vary between OpenROAD versions)
read_lef sky130_fd_sc_hd.tlef ; read_lef sky130_fd_sc_hd_merged.lef
read_liberty sky130_fd_sc_hd__tt_025C_1v80.lib
read_verilog accel.v ; link_design accel ; read_sdc accel.sdc
initialize_floorplan -die_area "0 0 2534 2534" -core_area "250 250 2284 2284" \
                     -site unithd
make_tracks
place_pins -hor_layers met3 -ver_layers met2           ;# block-style pin placement
tapcell -distance 14 -tapcell_master sky130_fd_sc_hd__tapvpwrvgnd_1 \
        -endcap_master sky130_fd_sc_hd__decap_3
add_global_connection -net VDD -pin_pattern {^VPWR$} -power
add_global_connection -net VSS -pin_pattern {^VGND$} -ground
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name core -voltage_domains CORE
add_pdn_ring    -grid core -layers {met4 met5} -widths 10 -spacings 2 -core_offsets 5
add_pdn_stripe  -grid core -layer met1 -width 0.48 -followpins
add_pdn_stripe  -grid core -layer met4 -width 10 -pitch 100 -offset 20
add_pdn_stripe  -grid core -layer met5 -width 10 -pitch 100 -offset 20
add_pdn_connect -grid core -layers {met1 met4}
add_pdn_connect -grid core -layers {met4 met5}
pdngen''', "Listing 14.2 - A floorplan and PDN script in OpenROAD Tcl "
         "(the 100 um / 10 um straps correspond roughly to the 1.6% ring-fed row "
         "of the IR-drop table). Commercial tools use equivalent commands "
         "(floorPlan, addRing, addStripe, sroute in Innovus; "
         "initialize_floorplan, create_pg_mesh_pattern, compile_pg in ICC2).")

    # ------------------------------------------------------------------------
    h2("Floorplan quality checks")
    checklist("Floorplan review checklist", [
        "Die/core size, aspect ratio and utilisation agree with the plan; rows and sites legal.",
        "I/O ring or bump map matches the package; supply pads meet SSO/ESD/EM rules.",
        "Macros on grid, legal orientation, pins facing the core, halos and channels sized.",
        "No slivers or notches; standard-cell area contiguous; blockages intentional.",
        "Power grid complete: every macro and row connected; no floating PG shapes.",
        "Early static IR drop and EM on the grid within budget (with a realistic power map).",
        "Power domains, switches, always-on routes, level-shifter/isolation areas in place.",
        "Tap and endcap cells inserted; DRC clean on the floorplan (PG + macros + taps).",
        "Pins placed on legal layers/tracks, near their logic; feedthroughs planned.",
        "Trial placement + global route: congestion map and timing acceptable.",
    ])
    box("expert", "Interview insight: 'How do you know your floorplan is good?'",
        "Run a quick placement and global route on it and look at three "
        "things: the congestion map (hot-spots around macro corners and "
        "channels), the timing of the worst paths (are they long because of "
        "macro placement?) and the wire-length/flight-line picture between "
        "macros and logic. Then iterate the floorplan, not the optimisation "
        "settings. Also mention the power grid: early IR drop with a "
        "vectorless power map, and that the grid's track usage leaves enough "
        "routing resources.")

    h2("Summary")
    bul(["The floorplan sets die/core, rows and sites, the I/O ring or bump "
         "array, macro positions, blockages, power domains and pins; it is "
         "the most leveraged decision in PD.",
         "Wire-bond chips use a peripheral pad ring with corner, filler and "
         "break cells; flip-chip uses an area bump array and an RDL, and "
         "feeds power from above.",
         "Macros go to the periphery following the data flow, with halos, "
         "adequate channels and legal orientations; hard, soft and partial "
         "blockages shape placement.",
         "The PDN is rings, upper-metal straps, via stacks and follow-pin "
         "rails; the numerical mesh model shows that mesh IR drop tracks "
         "metal density, pitch controls the local rail drop, and bump "
         "feeding cuts the drop by about an order of magnitude.",
         "IR drop is budgeted (static around 2-3%, dynamic around 5-10% "
         "total, project-dependent) and EM limits come from the tech rules; "
         "decap supplies the first nanoseconds of transients.",
         "Switched domains get switch columns or rings, boundary cells and "
         "always-on routing; tap and endcap cells are inserted at floorplan; "
         "pins are assigned on legal layers near their logic."])
    h2("Exercises")
    bul(["Compute the number of rows and sites per row for a 1.5 x 1.2 mm "
         "SKY130 HD core. How many tap cells are needed if one is placed every "
         "14 um in every row (ignore the checkerboard offset)?",
         "Extend irdrop.py to model the VSS grid and the package: add a "
         "20 mohm resistance in series with every bump. How does the "
         "bump-fed drop change, and which term now dominates?",
         "With the ring feed, find the strap width at 100 um pitch that "
         "keeps the total VDD drop below 1% of VDD. What fraction of met4 "
         "and met5 does it use?",
         "A region of 0.25 mm^2 can see a current step of 150 mA. The "
         "package responds in 2 ns and the allowed droop is 30 mV. How much "
         "decap is needed, and what fraction of the region is that at "
         "10 fF/um^2?",
         "Sketch a floorplan for a block with four SRAM macros (each 600 x "
         "400 um, pins on one long edge) and a datapath that reads all four "
         "every cycle. Justify your macro orientation and channel widths.",
         "Explain why the mesh drop at 10% density with the ring feed is "
         "nearly independent of pitch, using the idea of an equivalent "
         "sheet resistance."], ordered=True)


# =============================================================================
def part3():
    part("Power, Mixed-Signal and Physical Design Setup",
         "Power intent and low-power techniques, the analog, clocking, I/O and "
         "ESD blocks every SoC must integrate, and the start of the back end: "
         "physical-design data, flows, design planning, floorplanning, power "
         "grids and the I/O ring.")
    _ch11()
    _ch12()
    _ch13()
    _ch14()
