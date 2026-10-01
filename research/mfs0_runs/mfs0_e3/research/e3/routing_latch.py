"""MFS0-E3 routing latch K (plan §7.2): per slot of a split history, holds the condition
value latched at admission until the slot's settlement is complete.

TYPE:SEMI (research layer; production Capacitor + MOSFET switches; ideal comparators C1).

Set   : at admission, through series(accept switch, condition-level switch, rail) to V_D
        when the step-start condition is 1; nothing is driven when it is 0 (K is already
        cleared — admission requires it).
Hold  : R_K = τ_K/C_K, τ_K = 30 s. Read comparator K > V_K_read = 1 V.
        Worst-case hold need = observation + settlement = τ_T·ln(V_D/θ_lo) = 2.846 s:
        K(2.846 s) = 2·e^(−2.846/30) = 1.819 V → margin 0.819 V above the read level.
Reset : only after the slot's settlement is complete — comparator (T < θ_lo, the same
        level that ends the settle window) closes a switch through R_Krst to ground;
        G_Krst = 1e-3 S → τ = 10 ms, 2 V → K_free = 1 mV in 7.6 τ = 76 ms.
Free  : K < K_free (comparator) is an extra admission condition of split slots, so a
        stale 1 can never contaminate a following 0.
The Python value written into logs is only a record; routing is decided by the K read.
"""
import math

from nexus_v1.components.semiconductor import Capacitor
from memory_core import series, relax, VTH


class RoutingLatch:
    C_K = 1e-5
    tau_K = 30.0
    V_K_read = 1.0
    K_free = 1e-3
    G_Krst = 1e-3

    def __init__(self, core):
        P = core.P
        self.core = core
        self.cap = Capacitor(capacitance=self.C_K, charge=0.0)
        self.R_K = self.tau_K / self.C_K
        self.g_rail = 1.0 / P.r_int
        self.hold_need_s = P.tau_T * math.log(P.V_D / P.theta_lo)
        self.hold_margin_V = P.V_D * math.exp(-self.hold_need_s / self.tau_K) - self.V_K_read

    @property
    def v(self):
        return self.cap.voltage

    def is_free(self):
        return not self.core.cmp_on(self.cap.voltage - (self.K_free - VTH))

    def read(self):
        """Comparator: 1 iff K > V_K_read."""
        return self.core.cmp_on(self.cap.voltage - (self.V_K_read - VTH))

    def step(self, accept, cond_level, vT_new, dt):
        """accept: this slot admitted the entry this step; cond_level: logic level (V_D or 0)
        of the step-start condition; vT_new: the slot's T after this step's T update."""
        P = self.core.P
        g = self.core.g
        g_set = series(g(P.gm_sw, 1.0), g(P.gm_sw, cond_level), self.g_rail) if accept else 0.0
        done = self.core.cmp_on((P.theta_lo + VTH) - vT_new)          # T < θ_lo: settlement complete
        g_rst = series(P.G_cmp, self.G_Krst) if done else 0.0
        relax(self.cap, [(g_set, P.V_D), (1.0 / self.R_K, 0.0), (g_rst, 0.0)], dt)
