"""MFS0-E2 input bridges: both deliver per-step entry pulses (b_W list, b_L) to the core.

ReplayBridge (R path, CAUSAL_REPLAY_REFERENCE + TEMPLATE_TRANSLATION):
  frozen templates (W = cal_C3_m, LATER = s23_ov) translated in time; each channel
  RelationEventAdapter → PhysicalEntryGate (production, default params, one object per
  channel for the whole stream). The schedule is held by the source; only the current
  ramp value is handed to the transducer each step.

LiveBridge (L path, project current boundary):
  project BaseGenerator (wrap_base_generator on a VariantCircuit, frozen thermal sites)
  driven by a causal stimulus callback returning the CURRENT dT only →
  collector → CollectorBoundaryPort.spike_output → PhysicalEntryGate.step(spike, dt).
  No occurrence port, no t_rearm, no future Boundary sample is read.
"""
from e1_common import Transducer, ramp, load_templates

_T = load_templates()
DUR = {'W': _T['W']['dur_s'], 'L': _T['L']['dur_s']}


class _Channel:
    __slots__ = ('starts', 'dur', 'k', 'tr')

    def __init__(self, starts, dur, label):
        self.starts = sorted(starts)
        self.dur = dur
        self.k = 0
        self.tr = Transducer(label)

    def theta(self, t):
        while self.k < len(self.starts) and t >= self.starts[self.k] + self.dur:
            self.k += 1
        if self.k < len(self.starts):
            return ramp(t, self.starts[self.k], self.dur)
        return 0.0

    def step(self, t, dt):
        return self.tr.step(self.theta(t), dt)[0]


class ReplayBridge:
    """w_starts: list per history of W template start times [s]; l_starts: LATER starts."""

    kind = "REPLAY"

    def __init__(self, w_starts, l_starts, label="R"):
        self.w = [_Channel(s, DUR['W'], f"{label}_W{i}") for i, s in enumerate(w_starts)]
        self.l = _Channel(l_starts, DUR['L'], f"{label}_L")

    def step(self, t, dt):
        return [c.step(t, dt) for c in self.w], self.l.step(t, dt)


class LiveBridge:
    """Project current-boundary bridge. stimulus(t) -> dict site -> current dT (causal)."""

    kind = "LIVE"

    def __init__(self, w_sites, l_site, stimulus):
        from nexus_v1.circuit.variant_adapter import VariantCircuit
        from nexus_v1.components.structural_address import AddressRegistry
        from tss.generators.base_generator import wrap_base_generator
        from tss.relations.boundary_process import CollectorBoundaryPort
        from tss.relations.entry_gate import make_entry_gate
        self.circuit = VariantCircuit()
        reg = AddressRegistry()
        self.sites = list(w_sites) + [l_site]
        self.gen, self.port, self.gate = {}, {}, {}
        for s in self.sites:
            g = wrap_base_generator(self.circuit, s, reg)
            self.gen[s] = g
            self.port[s] = CollectorBoundaryPort(generator_address=g.address, carrier_ref=g.collector)
            self.gate[s] = make_entry_gate(self.port[s])
        self.w_sites, self.l_site = list(w_sites), l_site
        self.stimulus = stimulus
        self.n_spikes = {s: 0 for s in self.sites}

    def step(self, t, dt):
        dT = self.stimulus(t)                      # current values only
        out = {}
        for s in self.sites:
            self.gen[s].feed(dT.get(s, 0.0), dt)   # production BaseGenerator.feed
            spk = self.port[s].spike_output        # CollectorBoundaryPort
            self.n_spikes[s] += spk > 0.5
            out[s] = self.gate[s].step(spk, dt)    # PhysicalEntryGate.step(spike_output, dt)
        return [out[s] for s in self.w_sites], out[self.l_site]
