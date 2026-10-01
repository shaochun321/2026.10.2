"""MFS0-E3 shared event traces (plan §5.1).

TYPE:SEMI (research layer; production Capacitor + MOSFET switch, E2 rail and relax primitive).

One RC trace per input path a ∈ {W0, W1, W2, L}, shared by every history and every
threshold reading (no capacitor copied per reader). Input = the gate-accepted pulse of
that path only. Set: the pulse closes a switch to rail V_D (= V_x = 2 V) through the same
series switch + rail-internal conductance the E2 T-capacitor uses; leak: R_x = τ_x/C_x.
Bounded set error vs the ideal x ← V_x: v_inf/V_x − 1 = −(1/R_x)/g_set ≈ −2.4e-6 (logged).

Thresholds are read by ideal comparators (C1 extension) against reference levels
V_x·e^(−d/τ_x), d ∈ {H, 2H}: ON iff x > level; equality → OFF; start-up x = 0 → OFF.
The trace describes "most recent accepted event", NOT the entry gate's recovery state
(the gate is also refreshed by suppressed raw spikes; the trace is not).
"""
import math

from nexus_v1.components.semiconductor import Capacitor
from memory_core import series, relax, VTH

TRACE_NAMES = ('W0', 'W1', 'W2', 'L')


class ContextTraces:
    C_x = 1e-5
    tau_x = 1.0

    def __init__(self, core):
        P = core.P
        self.core = core
        self.V_x = P.V_D
        self.R_x = self.tau_x / self.C_x
        self.cap = [Capacitor(capacitance=self.C_x, charge=0.0) for _ in TRACE_NAMES]
        self.g_set = series(core.g(P.gm_sw, 1.0), 1.0 / P.r_int)
        self.H = core.H_nominal
        self.level = {'H': self.V_x * math.exp(-self.H / self.tau_x),
                      '2H': self.V_x * math.exp(-2.0 * self.H / self.tau_x)}
        self.set_error = (self.V_x * self.g_set / (self.g_set + 1.0 / self.R_x)) / self.V_x - 1.0

    def voltages(self):
        return [c.voltage for c in self.cap]

    def above(self, idx, which):
        """Comparator X_a^(d): ON iff x_a > V_x e^(−d/τ_x)."""
        return self.core.cmp_on(self.cap[idx].voltage - (self.level[which] - VTH))

    def step(self, pulses, dt):
        """pulses: [b_W0, b_W1, b_W2, b_L] (gate-accepted, this step); called in step-order item 6."""
        for c, b in zip(self.cap, pulses):
            relax(c, [(self.g_set if b > 0.5 else 0.0, self.V_x), (1.0 / self.R_x, 0.0)], dt)
