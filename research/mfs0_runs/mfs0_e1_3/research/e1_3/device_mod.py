"""MFS0-E1.1 device copy with a split write rail (independent write-dose interface).

Only change vs v4 device.py (32da25e2ed9e910b): the shared V_W is split into
  V_S      — fixed sense/reference rail (v_sense, V_lo, V_hi, I_fs use it);
  rail_write.vdd = m · V_write0 — the write drive, the ONLY control entry
             (set via set_write_drive(m); step() reads rail_write.vdd).
gm_z is derived once from the m = 1 baseline and is never re-derived.

--- v4 docstring follows ---
MFS0-E1 correctable predictive memory — node-level device (stage B).

TYPE:SEMI (research layer; production primitives Capacitor / MOSFET / Memristor /
PowerRail are used unmodified). Design and parameter derivation: design.md.

Signal flow per history i (plan v4 §4.1), all physical, no Python branch on labels:
  W_i template → Transducer (RelationEventAdapter → PhysicalEntryGate) → b_Wi
  b_Wi → switch to rail → timer/eligibility node T_i (RC, τ_T)            [steps 1, 4]
  LATER template → Transducer → b_L → series(switch, window FET on T) → O   [step 2]
  O = shared observation node (RC hold τ_o, reset branch when all T < θ_lo) [steps 2, 6]
  settle gates: FET(T_i) ∧ FET(θ_hi + Vth − T_i) in series                  [step 4]
  UP branch  : settle_i + FET(O)           + FET(V_hi + Vth − V_Ri) → I_up  (z toward 1)
  DOWN branch: settle_i + FET(V_D + ... −O)+ FET(V_Ri − V_lo + Vth) → I_dn  (z toward 0)
  Memristor_i.update(I·dt)  (DEG-025 workaround: dt applied once at the call site)  [step 5]
  read: window FET(T_i) + FET(V_Ri − V_lo + Vth) → I_pred (summed over i)          [step 7]

Registered idealisations (TIER-2 family, see design.md §6):
  L1 difference nodes are ideal unity-gain differencers (infinite input impedance,
     no swing limit); the subtraction solves that declared node, nothing else.
  L2 each rail is a Thevenin source (vdd, r_internal) and each branch is solved as a
     series conductance chain; parallel branches do not load each other's rail.
  L3 the memristor has no read-disturb physics (conduct() is pure) and its sensing
     current does not write; only I_up / I_dn are passed to Memristor.update().
  L4 MOSFET.conduct(v)/1 V is used as a conductance in S (V_REF = 1 V).
"""
import math
from dataclasses import dataclass, field

from nexus_v1.components.semiconductor import Capacitor, MOSFET, Memristor, PowerRail

VTH = 0.3                       # MOSFET primitive default (semiconductor.py:130)


def series(*gs):
    """Series conductance chain; any zero element → 0 (open circuit)."""
    inv = 0.0
    for g in gs:
        if g <= 0.0:
            return 0.0
        inv += 1.0 / g
    return 1.0 / inv


def relax(cap, g_to_src, dt):
    """Exact solution of C dV/dt = Σ G_k (E_k − V) over dt (G_k constant in the step).

    Applied through Capacitor.inject with the equivalent mean current, so the
    capacitor's KCL ledger stays consistent. Returns that current.
    """
    gt = sum(g for g, _ in g_to_src)
    v = cap.voltage
    if gt <= 0.0:
        return 0.0
    v_inf = sum(g * e for g, e in g_to_src) / gt
    v_new = v_inf + (v - v_inf) * math.exp(-gt * dt / cap.capacitance)
    i_eq = cap.capacitance * (v_new - v) / dt
    cap.inject(i_eq, dt)
    return i_eq


@dataclass
class Params:
    V_D: float = 2.0            # logic/timer rail [V]
    r_int: float = 0.1          # PowerRail default r_internal [Ω]
    V_S: float = 100.0          # sense/reference rail [V], fixed
    V_write0: float = 100.0     # write drive at m = 1 [V]
    # timer / eligibility node
    C_T: float = 1e-5
    tau_T: float = 1.5          # [s]  design.md §3
    theta_hi: float = 1.0       # observation / settle boundary on T [V]
    # observation node
    C_o: float = 1e-5
    tau_o: float = 30.0         # [s]  hold through settle: design.md §4.1
    # switches
    gm_sw: float = 10.0         # switch transconductance [S/V]
    theta_lo: float = 0.3       # settle / idle boundary on T [V] (= VTH)
    gm_rst: float = 1e-2        # O reset branch [S/V]   design.md §4.2
    # sensing replica network
    R_s: float = 990.0          # sense source resistance [Ω]
    # write FETs (z-dependent) — derived from α⁰ in design.md §5
    gm_z: float = None          # derived in __init__ from alpha0 (design.md §5)
    alpha0: float = 0.10        # design learning rate per experience
    # read FET
    gm_p: float = 1e-3
    V_read: float = 1.0


@dataclass
class History:
    """Per-history hardware: timer node + persistent carrier."""
    T: Capacitor
    mem: Memristor
    q_up: float = 0.0           # cumulative write charge, for the ledger
    q_dn: float = 0.0


class PredictiveMemoryDevice:
    """N-history device; history i is selected only by which W input fires."""

    def __init__(self, n_hist=1, w0=0.5, p=None):
        self.p = p or Params()
        P = self.p
        self.rail_D = PowerRail(vdd=P.V_D)
        self.rail_write = PowerRail(vdd=P.V_write0)   # control entry: set_write_drive(m)
        self.fet = MOSFET(v_threshold=VTH, gm=1.0)   # stateless conduct(); gm applied per role
        w0s = w0 if isinstance(w0, (list, tuple)) else [w0] * n_hist
        self.h = [History(T=Capacitor(capacitance=P.C_T, charge=0.0),
                          mem=Memristor(w=w, r_min=0.1, r_max=10.0)) for w in w0s]
        self.O = Capacitor(capacitance=P.C_o, charge=0.0)
        m = self.h[0].mem
        self.V_lo = P.V_S * m.r_min / (P.R_s + m.r_min)      # replica r_min
        self.V_hi = P.V_S * m.r_max / (P.R_s + m.r_max)      # replica r_max
        self.I_fs = P.V_read * P.gm_p * (self.V_hi - self.V_lo)
        self.R_T = P.tau_T / P.C_T
        self.R_o = P.tau_o / P.C_o
        # settle window length on T(t) = V_D e^{-t/τ_T}: T from θ_hi down to θ_lo
        self.T_settle = P.tau_T * math.log(P.theta_hi / P.theta_lo)
        if P.gm_z is None:
            # dz/dt = ½ I, I ≈ V_W gm_z ΔV (1−z)  ⇒  α⁰ = 1 − exp(−½ V_W gm_z ΔV T_settle)
            P.gm_z = -math.log(1.0 - P.alpha0) / (0.5 * P.V_write0 * (self.V_hi - self.V_lo) * self.T_settle)
        self.write_enabled = True       # interventions: physical rail disconnection
        self.down_branch = True
        self.energy_D = 0.0
        self.energy_W = 0.0
        self.last = {}

    # conductance helpers (L4)
    def g(self, gm, v_gate):
        return gm * self.fet.conduct(v_gate)

    def v_sense(self, mem):
        R = mem.resistance
        return self.p.V_S * R / (self.p.R_s + R)

    def step(self, b_W, b_L, dt):
        """b_W: list of entry pulses (0/1) per history; b_L: later entry pulse (0/1)."""
        P = self.p
        g_rail_D = 1.0 / P.r_int
        V_wr = self.rail_write.vdd
        # 1/4. timer set by own W entry pulse; leak
        for hi, bw in zip(self.h, b_W):
            g_set = series(self.g(P.gm_sw, bw), g_rail_D)
            i = relax(hi.T, [(g_set, P.V_D), (1.0 / self.R_T, 0.0)], dt)
            if g_set > 0:
                self.energy_D += P.V_D * g_set * (P.V_D - hi.T.voltage) * dt
        # 2/6. observation node: set gated by later pulse AND any observation window;
        #      reset when every timer is below θ_lo (parallel window FETs / series reset FETs)
        g_win = sum(self.g(P.gm_sw, hi.T.voltage - (P.theta_hi - VTH)) for hi in self.h)
        g_setO = series(self.g(P.gm_sw, b_L), g_win, g_rail_D)
        g_rstO = series(*[self.g(P.gm_rst, (P.theta_lo + VTH) - hi.T.voltage) for hi in self.h])
        relax(self.O, [(g_setO, P.V_D), (1.0 / self.R_o, 0.0), (g_rstO, 0.0)], dt)
        if g_setO > 0:
            self.energy_D += P.V_D * g_setO * max(0.0, P.V_D - self.O.voltage) * dt
        vO = self.O.voltage
        # 5. writes
        g_obs = self.g(P.gm_sw, vO)
        g_nobs = self.g(P.gm_sw, P.V_D - vO)
        i_pred = 0.0
        for hi in self.h:
            vT = hi.T.voltage
            g_settle = series(self.g(P.gm_sw, vT), self.g(P.gm_sw, (P.theta_hi + VTH) - vT))
            vR = self.v_sense(hi.mem)
            R = hi.mem.resistance
            i_up = i_dn = 0.0
            if self.write_enabled:
                g_up = series(g_settle, g_obs, self.g(P.gm_z, (self.V_hi + VTH) - vR),
                              1.0 / R, 1.0 / P.r_int)
                i_up = V_wr * g_up
                if self.down_branch:
                    g_dn = series(g_settle, g_nobs, self.g(P.gm_z, vR - (self.V_lo - VTH)),
                                  1.0 / R, 1.0 / P.r_int)
                    i_dn = V_wr * g_dn
            # DEG-025: Memristor.update has no dt → pass charge I·dt (E0 WRITE_DT_CORRECTION)
            if i_up > 0:
                hi.mem.update(current=i_up * dt, pre_trace=0.0, post_trace=1.0)   # dw = −0.5 I dt
            if i_dn > 0:
                hi.mem.update(current=i_dn * dt, pre_trace=1.0, post_trace=0.0)   # dw = +0.5 I dt
            hi.q_up += i_up * dt
            hi.q_dn += i_dn * dt
            self.energy_W += V_wr * (i_up + i_dn) * dt
            # 7. read path (current output; normalised by the evaluator with build-time I_fs)
            g_read = series(self.g(P.gm_sw, vT - (P.theta_hi - VTH)),
                            self.g(P.gm_p, vR - (self.V_lo - VTH)))
            i_pred += P.V_read * g_read
        self.last = dict(O=vO, i_pred=i_pred)
        return i_pred

    def set_write_drive(self, m):
        """Write-dose control: V_write = m·V_write0, m ≥ 0."""
        if m < 0:
            raise ValueError('m must be >= 0')
        self.rail_write.vdd = m * self.p.V_write0

    def predict(self):
        """Actual output current of the read path, normalised by the fixed full scale."""
        return self.last.get('i_pred', 0.0) / self.I_fs

    def z(self, i=0):
        return 1.0 - self.h[i].mem.w
