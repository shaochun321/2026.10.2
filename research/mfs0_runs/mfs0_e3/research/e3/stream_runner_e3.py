"""MFS0-E3 lockstep stream runner.

One input source (replay bridge, live bridge or core injector) is stepped once per tick;
its gate-accepted pulses fan out unchanged to every group core (B = frozen E2
MemoryCore, C = CondMemoryCore, R = CondMemoryCore with the random port). The runner only
moves time, forwards pulses, draws the R-group random bits from its own labelled source,
emits immutable records and logs. It holds no outcome, phase or label.

StreamRun is resumable; the prefix-fork checkpoint is a copy.deepcopy of the whole object
(source, bridge, cores, traces, K, random sources, logs). The live bridge holds a
VariantCircuit with local lambdas, so pickling is not available; deepcopy is (dev check).
"""
import random

from memory_core import MemoryCore
from conditional_memory_core import CondMemoryCore  # noqa: F401  (group C/R core type)
from prediction_port_e3 import PredictionRecordE3, PredictionPort


class RandomPort:
    """Experiment random source of the R control (ablation device; not a project generator).
    One bit per gate-accepted W entry of a split history, P(1) = π_i (frozen from D1)."""

    def __init__(self, seed, pi):
        self.rng = random.Random(seed)
        self.pi = {int(k): v for k, v in pi.items()}

    def bits(self, b_W):
        out = [0.0, 0.0, 0.0]
        for i in range(3):
            if b_W[i] > 0.5 and i in self.pi:
                out[i] = 1.0 if self.rng.random() < self.pi[i] else 0.0
        return out


class StreamRun:
    def __init__(self, source, cores, n_ticks, dt=0.001, rport=None, z_every=100, hold_ticks=(),
                 relation_ids=None, trace_every=0, consumers=None, trace_window=None):
        self.src, self.cores, self.n, self.dt = source, cores, n_ticks, dt
        self.rport = rport
        self.z_every, self.hold_set, self.trace_every = z_every, set(hold_ticks), trace_every
        self.trace_window = trace_window
        self.relation_ids = relation_ids or {}
        self.k = 0
        self.ports = {g: PredictionPort() for g in cores}
        for g, fn in (consumers or {}).items():
            self.ports[g].subscribe(fn)
        self.w_ticks = [[] for _ in range(3)]
        self.l_ticks = []
        self.log = {g: dict(z=[], hold={}, rejected=[[] for _ in range(3)], admit=[], trace=[], eval_z=[]) for g in cores}

    def _step_e2(self, g, core, b_W, b_L):
        any_w = any(b > 0.5 for b in b_W)
        free_before = [sum(1 for s in core.slots[i] if core.slot_free(s)) for i in range(3)] if any_w else None
        z_pre = [core.z(core.carrier_of[i]) for i in range(3)] if any_w else None
        i_read, acc, rej = core.step(b_W, b_L, self.dt)
        for i in range(3):
            if b_W[i] > 0.5:
                p = i_read[i] / core.I_fs
                self.log[g]['eval_z'].append((self.k, i, z_pre[i]))
                self._emit(g, i, p, p, 'm%d' % i, rej[i], acc[i], free_before[i], None, None, None)

    def _step_c(self, g, core, b_W, b_L, r_bits):
        z_pre = [1.0 - m.w for m in core.mem] if any(b > 0.5 for b in b_W) else None
        res = core.step(b_W, b_L, self.dt, r_bits)
        for i in range(3):
            if b_W[i] > 0.5:
                p, c = core.p_hat(res['i_read'], i, res['cond'])
                self.log[g]['eval_z'].append((self.k, i, z_pre[c]))     # evaluator-side, not a port field
                pm = res['i_read'][i] / core.I_fs
                cv, cn = res['cond'].get(i, (None, None))
                self._emit(g, i, p, pm, core.carrier_names[c], res['rejected'][i], res['accepted'][i],
                           res['free_before'][i], cv, cn, core.splits.get(i))
                if not res['rejected'][i] and i in core.K:
                    r = res['accepted'][i]
                    self.log[g]['admit'].append((self.k, i, r, cv, core.K[i][r].v))

    def _emit(self, g, i, p, pm, path, rej, slot, free_before, cv, cn, cand):
        rid = self.relation_ids.get(g, {}).get(i)
        self.ports[g].emit(PredictionRecordE3(
            t=self.k * self.dt, tick=self.k, path=i, p_hat=p, horizon_s=1.5 * 0.6931471805599453,
            status='CAPACITY_REJECTED' if rej else 'ADMITTED', slot=slot, free_slots_before=free_before,
            relation_id=rid, condition_id=cand, condition_value=cv, condition_net=cn, read_path=str(path),
            p_hat_marginal=pm))
        if rej:
            self.log[g]['rejected'][i].append(self.k)

    def run(self, until=None):
        until = self.n if until is None else min(until, self.n)
        while self.k < until:
            k = self.k
            t = k * self.dt
            for g, core in self.cores.items():
                if k in self.hold_set:
                    self.log[g]['hold'][k] = [m.w for m in core.mem]
                if self.z_every and k % self.z_every == 0:
                    self.log[g]['z'].append((k, [1.0 - m.w for m in core.mem]))
                in_win = self.trace_window is None or self.trace_window[0] <= k < self.trace_window[1]
                if self.trace_every and k % self.trace_every == 0 and hasattr(core, 'splits') and in_win:
                    self.log[g]['trace'].append((k, [1.0 - m.w for m in core.mem],
                                                 [[(s.T.voltage, s.O.voltage) for s in core.slots[i]] for i in range(3)],
                                                 {i: [x.v for x in core.K[i]] for i in core.K}, core.traces.voltages()))
            b_W, b_L = self.src.step(t, self.dt)
            if b_L > 0.5:
                self.l_ticks.append(k)
            for i in range(3):
                if b_W[i] > 0.5:
                    self.w_ticks[i].append(k)
            r_bits = self.rport.bits(b_W) if (self.rport is not None and any(b > 0.5 for b in b_W)) else None
            for g, core in self.cores.items():
                if hasattr(core, 'splits'):
                    self._step_c(g, core, b_W, b_L, r_bits if core.random_port else None)
                else:
                    self._step_e2(g, core, b_W, b_L)
            self.k += 1
        return self

    def summary(self, g):
        core = self.cores[g]
        out = dict(records=[tuple(r.__dict__.values()) for r in self.ports[g].records],
                   record_fields=list(PredictionRecordE3.__dataclass_fields__),
                   z=self.log[g]['z'], hold=self.log[g]['hold'], rejected=self.log[g]['rejected'],
                   eval_z=self.log[g]['eval_z'],
                   n_accept=[[s.n_accept for s in core.slots[i]] for i in range(3)],
                   n_settle=[[s.n_settle for s in core.slots[i]] for i in range(3)],
                   objects=(core.n_object_ids, core._object_count()), final_w=[m.w for m in core.mem],
                   q_up=[[s.q_up for s in core.slots[i]] for i in range(3)],
                   q_dn=[[s.q_dn for s in core.slots[i]] for i in range(3)])
        if hasattr(core, 'splits'):
            out.update(carrier_names=core.carrier_names, admit=self.log[g]['admit'], splits=core.splits,
                       leaf=core.leaf, leaf_q_up=core.leaf_q_up, leaf_q_dn=core.leaf_q_dn,
                       leaf_settle_steps=core.leaf_settle_steps, leaf_settle_entries=core.leaf_settle_entries,
                       route_log=core.route_log, route_flips=core.route_flips,
                       trace=self.log[g]['trace'])
        return out
