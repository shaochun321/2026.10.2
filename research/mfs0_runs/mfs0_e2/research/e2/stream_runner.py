"""MFS0-E2 stream runner: steps bridge → core continuously; no labels, no settling logic.

The runner only moves time, forwards current pulses, emits prediction records and logs.
"""
from prediction_port import PredictionPort, PredictionRecord


class PulseReplay:
    """Feeds pulses recorded from a bridge run (same input, same timing) to another core."""
    kind = "PULSE_REPLAY"

    def __init__(self, w_ticks, l_ticks, n_hist):
        self.w = [set(x) for x in w_ticks]
        self.l = set(l_ticks)
        self.n = n_hist
        self.k = 0

    def step(self, t, dt):
        k = self.k
        self.k += 1
        return [1.0 if k in self.w[i] else 0.0 for i in range(self.n)], (1.0 if k in self.l else 0.0)


class PulseInjector(PulseReplay):
    """Core stress layer: pulses injected directly at the declared entry-pulse contract."""
    kind = "CORE_INJECT"


class CombinedBridge:
    """Replay bridge OR core-level injection (stress streams)."""

    def __init__(self, bridge, injector):
        self.b, self.inj = bridge, injector
        self.kind = bridge.kind + "+CORE_INJECT"

    def step(self, t, dt):
        w, l = self.b.step(t, dt)
        wi, li = self.inj.step(t, dt)
        return [max(a, b) for a, b in zip(w, wi)], max(l, li)


def run_stream(core, bridge, n_ticks, dt=0.001, port=None, z_every=100, trace_every=0,
               hold_ticks=(), consumer=None):
    port = port or PredictionPort()
    if consumer is not None:
        port.subscribe(consumer)
    n_h = core.n_hist
    w_ticks = [[] for _ in range(n_h)]
    l_ticks = []
    rej = [[] for _ in range(n_h)]
    z_log = []
    trace = []
    hold = {}
    hold_set = set(hold_ticks)
    eval_z = []
    n_car = len(core.mem)
    for k in range(n_ticks):
        t = k * dt
        if k in hold_set:
            hold[k] = [core.mem[c].w for c in range(n_car)]
        if z_every and k % z_every == 0:
            z_log.append((k, [core.z(c) for c in range(n_car)]))
        b_W, b_L = bridge.step(t, dt)
        any_w = any(b > 0.5 for b in b_W)
        free_before = [sum(1 for s in core.slots[i] if core.slot_free(s)) for i in range(n_h)] if any_w else None
        z_pre = [core.z(core.carrier_of[i]) for i in range(n_h)] if any_w else None
        i_read, acc, rejd = core.step(b_W, b_L, dt)
        if b_L > 0.5:
            l_ticks.append(k)
        for i in range(n_h):
            if b_W[i] > 0.5:
                w_ticks[i].append(k)
                if rejd[i]:
                    rej[i].append(k)
                eval_z.append((k, i, z_pre[i]))      # evaluator-side log (not part of the port)
                port.emit(PredictionRecord(t=t, tick=k, path=i, p_hat=i_read[i] / core.I_fs,
                                           horizon_s=core.H_nominal,
                                           status='CAPACITY_REJECTED' if rejd[i] else 'ADMITTED',
                                           slot=acc[i], free_slots_before=free_before[i]))
        if trace_every and k % trace_every == 0:
            trace.append((k, [core.z(c) for c in range(n_car)],
                          [[(s.T.voltage, s.O.voltage) for s in core.slots[i]] for i in range(n_h)]))
    return dict(port=port, eval_z=eval_z, w_ticks=w_ticks, l_ticks=l_ticks, rejected=rej, z_log=z_log,
                trace=trace, hold=hold,
                n_accept=[[s.n_accept for s in core.slots[i]] for i in range(n_h)],
                n_settle=[[s.n_settle for s in core.slots[i]] for i in range(n_h)],
                objects_end=core._object_count(), objects_start=core.n_object_ids,
                final_w=[m.w for m in core.mem])
