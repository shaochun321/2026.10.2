"""MFS0-E2 memory core — asynchronous multi-history, multi-slot correctable predictive memory.

TYPE:SEMI (research layer; production primitives Capacitor / MOSFET / Memristor /
PowerRail used unmodified). Theory and parameters: THEORY.md.

Inputs per step (current values only): b_W[i] (entry pulse of history path i, 0/1),
b_L (later entry pulse, 0/1), dt. No label, probability, phase or future time enters.

Per history i: persistent carrier Memristor_c(i) (c = carrier_of[i]; identity by default,
all-zero for the shared-carrier control) and an independent read branch.
Per slot (i, r): timer/eligibility capacitor T_ir, observation capacitor O_ir, own
settle gates, own UP/DOWN write branches, own O reset branch.

Step order (frozen, THEORY.md §3):
  1. read   : I_pred,i from the OLD carrier state (before any input of this step)
  2. accept : free_ir from OLD T/O (comparators); A_ir = b_Wi·free_ir·Π_{q<r}(1−free_iq)
  3. T      : set (accepted) + leak, exact RC
  4. O      : set when b_L and window comparator (T_ir ≥ θ_hi) on the NEW T; hold; reset
  5. write  : all branch conductances from the same OLD carrier state; one node solution
              per carrier; one signed-charge Memristor.update per carrier (DEG-025: ×dt)
Registered idealisations (TIER-2): L1 ideal differencers, L2 Thevenin rails / series
chains, L3 no read-disturb, L4 conduct()/1V as conductance, C1 ideal rail-to-rail
comparators (window, free) built on MOSFET.conduct()==0 hard cutoff (DEG-019).
"""
import math

from nexus_v1.components.semiconductor import Capacitor, MOSFET, Memristor, PowerRail

VTH = 0.3


def series(*gs):
    inv = 0.0
    for g in gs:
        if g <= 0.0:
            return 0.0
        inv += 1.0 / g
    return 1.0 / inv


def relax(cap, pairs, dt):
    """Exact C dV/dt = Σ G_k (E_k − V) over dt, applied through Capacitor.inject."""
    gt = 0.0
    ge = 0.0
    for g, e in pairs:
        gt += g
        ge += g * e
    if gt <= 0.0:
        return
    v = cap.voltage
    v_inf = ge / gt
    v_new = v_inf + (v - v_inf) * math.exp(-gt * dt / cap.capacitance)
    cap.inject(cap.capacitance * (v_new - v) / dt, dt)


class Params:
    V_D = 2.0
    r_int = 0.1
    V_S = 100.0            # fixed sense / reference rail
    V_write0 = 100.0       # write drive at m = 1
    C_T = 1e-5
    tau_T = 1.5
    theta_hi = 1.0
    theta_lo = 0.3
    C_o = 1e-5
    tau_o = 30.0
    gm_sw = 10.0
    gm_rst = 1e-2
    R_s = 990.0
    alpha0 = 0.10
    gm_p = 1e-3
    V_read = 1.0
    O_free = 1e-3          # O "cleared" level for the free comparator [V]
    G_cmp = 1e3            # comparator-driven switch conductance when ON [S]


class Slot:
    __slots__ = ('T', 'O', 'q_up', 'q_dn', 'n_accept', 'n_settle', 'in_settle')

    def __init__(self, P):
        self.T = Capacitor(capacitance=P.C_T, charge=0.0)
        self.O = Capacitor(capacitance=P.C_o, charge=0.0)
        self.q_up = 0.0
        self.q_dn = 0.0
        self.n_accept = 0
        self.n_settle = 0          # settle-window entries (must equal n_accept)
        self.in_settle = False


class MemoryCore:
    def __init__(self, n_hist=3, n_slot=2, w0=0.5, carrier_of=None, slot_order=None, reverse_sum=False):
        P = self.P = Params()
        self.n_hist, self.n_slot = n_hist, n_slot
        self.carrier_of = list(carrier_of) if carrier_of is not None else list(range(n_hist))
        n_car = max(self.carrier_of) + 1
        w0s = w0 if isinstance(w0, (list, tuple)) else [w0] * n_car
        self.mem = [Memristor(w=w, r_min=0.1, r_max=10.0) for w in w0s]
        self.slots = [[Slot(P) for _ in range(n_slot)] for _ in range(n_hist)]
        # priority order of slots within a history (test: relabelling invariance)
        self.slot_order = slot_order or [list(range(n_slot)) for _ in range(n_hist)]
        self.reverse_sum = reverse_sum
        self.max_dw_without_branch = 0.0
        self.fet = MOSFET(v_threshold=VTH, gm=1.0)
        self.rail_D = PowerRail(vdd=P.V_D, r_internal=P.r_int)
        self.rail_write = PowerRail(vdd=P.V_write0, r_internal=P.r_int)
        m = self.mem[0]
        self.V_lo = P.V_S * m.r_min / (P.R_s + m.r_min)
        self.V_hi = P.V_S * m.r_max / (P.R_s + m.r_max)
        self.I_fs = P.V_read * P.gm_p * (self.V_hi - self.V_lo)
        self.R_T = P.tau_T / P.C_T
        self.R_o = P.tau_o / P.C_o
        self.T_settle = P.tau_T * math.log(P.theta_hi / P.theta_lo)
        self.gm_z = -math.log(1 - P.alpha0) / (0.5 * P.V_write0 * (self.V_hi - self.V_lo) * self.T_settle)
        self.H_nominal = P.tau_T * math.log(P.V_D / P.theta_hi)
        self.n_object_ids = self._object_count()

    # ── primitives ──
    def g(self, gm, v):
        return gm * self.fet.conduct(v)

    def cmp_on(self, v):
        """Ideal comparator (C1): ON iff MOSFET.conduct(v) > 0, i.e. v > Vth."""
        return self.fet.conduct(v) > 0.0

    def v_sense(self, mem):
        R = mem.resistance
        return self.P.V_S * R / (self.P.R_s + R)

    def set_write_drive(self, m):
        if m < 0:
            raise ValueError("m must be >= 0")
        self.rail_write.vdd = m * self.P.V_write0

    def _object_count(self):
        return len(self.mem) + sum(len(s) for s in self.slots) * 2

    # ── state queries (read-only) ──
    def slot_free(self, s):
        """Free iff T < θ_lo and O < O_free (two comparators, AND)."""
        return (not self.cmp_on(s.T.voltage - (self.P.theta_lo - VTH))) and \
               (not self.cmp_on(s.O.voltage - (self.P.O_free - VTH)))

    def read_currents(self):
        """Independent per-history read branch (not gated by any observation window)."""
        out = []
        for i in range(self.n_hist):
            vR = self.v_sense(self.mem[self.carrier_of[i]])
            out.append(self.P.V_read * self.g(self.P.gm_p, vR - (self.V_lo - VTH)))
        return out

    def z(self, c):
        return 1.0 - self.mem[c].w

    # ── one step ──
    def step(self, b_W, b_L, dt):
        P = self.P
        # 1. read from OLD state
        i_read = self.read_currents()
        # 2. acceptance from OLD slot state
        accepted = [-1] * self.n_hist
        rejected = [False] * self.n_hist
        for i in range(self.n_hist):
            if b_W[i] > 0.5:
                for r in self.slot_order[i]:
                    if self.slot_free(self.slots[i][r]):
                        accepted[i] = r
                        break
                if accepted[i] < 0:
                    rejected[i] = True
        g_rail = 1.0 / P.r_int
        # 3. T set/leak
        for i in range(self.n_hist):
            for r, s in enumerate(self.slots[i]):
                g_set = series(self.g(P.gm_sw, 1.0), g_rail) if accepted[i] == r else 0.0
                if accepted[i] == r:
                    s.n_accept += 1
                relax(s.T, [(g_set, P.V_D), (1.0 / self.R_T, 0.0)], dt)
        # 4. O set (window on NEW T) / hold / reset
        for i in range(self.n_hist):
            for s in self.slots[i]:
                vT = s.T.voltage
                win = self.cmp_on(vT - (P.theta_hi - VTH))
                g_setO = series(self.g(P.gm_sw, b_L), P.G_cmp, g_rail) if (win and b_L > 0.5) else 0.0
                g_rst = self.g(P.gm_rst, (P.theta_lo + VTH) - vT)
                relax(s.O, [(g_setO, P.V_D), (1.0 / self.R_o, 0.0), (g_rst, 0.0)], dt)
        # 5. writes: branch conductances from OLD carrier state, one node solution per carrier
        Vw = self.rail_write.vdd
        n_car = len(self.mem)
        sumG = [0.0] * n_car
        sumGE = [0.0] * n_car
        branches = []
        vRc = [self.v_sense(m) for m in self.mem]
        hist_order = range(self.n_hist - 1, -1, -1) if self.reverse_sum else range(self.n_hist)
        for i in hist_order:
            c = self.carrier_of[i]
            vR = vRc[c]
            gz_up = self.g(self.gm_z, (self.V_hi + VTH) - vR)
            gz_dn = self.g(self.gm_z, vR - (self.V_lo - VTH))
            sl = self.slots[i][::-1] if self.reverse_sum else self.slots[i]
            for s in sl:
                vT = s.T.voltage
                g_settle = series(self.g(P.gm_sw, vT), self.g(P.gm_sw, (P.theta_hi + VTH) - vT))
                now = g_settle > 0.0
                if now and not s.in_settle:
                    s.n_settle += 1
                s.in_settle = now
                if g_settle <= 0.0 or Vw <= 0.0:
                    continue
                vO = s.O.voltage
                g_up = series(g_settle, self.g(P.gm_sw, vO), gz_up, g_rail)
                g_dn = series(g_settle, self.g(P.gm_sw, P.V_D - vO), gz_dn, g_rail)
                if g_up > 0:
                    sumG[c] += g_up
                    sumGE[c] += g_up * Vw
                    branches.append((s, c, g_up, +1))
                if g_dn > 0:
                    sumG[c] += g_dn
                    sumGE[c] -= g_dn * Vw
                    branches.append((s, c, g_dn, -1))
        for c in range(n_car):
            if sumG[c] <= 0.0:
                continue                   # no settle branch of this carrier: no driven write
            R = self.mem[c].resistance
            V_M = R * sumGE[c] / (1.0 + R * sumG[c])
            I_M = sumGE[c] / (1.0 + R * sumG[c])          # signed: >0 raises z (UP)
            if I_M > 0:
                self.mem[c].update(current=I_M * dt, pre_trace=0.0, post_trace=1.0)
            elif I_M < 0:
                self.mem[c].update(current=-I_M * dt, pre_trace=1.0, post_trace=0.0)
            for s, cc, gj, sign in branches:
                if cc == c:
                    Ij = gj * (sign * Vw - V_M)
                    if sign > 0:
                        s.q_up += Ij * dt
                    else:
                        s.q_dn += -Ij * dt
        return i_read, accepted, rejected

    def predict(self, i_read):
        return [x / self.I_fs for x in i_read]
