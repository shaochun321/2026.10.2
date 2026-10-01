"""MFS0-E3 development / mechanism checks (plan §11, §10.4 flip scenarios, §5.1 boundary).

Core-level injection (PulseInjector, labelled CORE_INJECT) and dev seeds 9xxxxxxx only.
Writes results/dev/dev_checks_e3.json. Also used (function `flip_suite`) as the
deterministic condition-flip part of domain S.
"""
import json
import math
import os
import time

import e3_common as C
from memory_core import MemoryCore
from conditional_memory_core import CondMemoryCore
from stream_runner import PulseInjector
from stream_runner_e3 import StreamRun
from reference_solver_e3 import carriers_at, H
from prediction_port import ThresholdConsumer

DT = C.DT
SPL = {0: 'C1', 1: 'C1', 2: 'C1'}
jH = math.ceil(H / DT - 1e-9)


def inj_run(w, l, n, splits=SPL, z_every=1, **kw):
    core = CondMemoryCore(splits, **kw)
    run = StreamRun(PulseInjector(w, l, 3), {'C': core}, n, z_every=z_every).run()
    return core, run


def z_end(run, name, core):
    return run.log['C']['z'][-1][1][core.carrier_names.index(name)]


def ref_check(core, run):
    """Node carriers vs independent reference using the actually routed leaf."""
    s = run.summary('C')
    adm = [(k, i, r) for k, i, r, cv, kv in s['admit']]
    routes = {}
    for i, r, sel in s['route_log']:
        routes.setdefault((i, r), []).append(sel)
    used = {}
    exps = []
    mismatch = 0
    for rec in run.ports['C'].records:
        if rec.status != 'ADMITTED':
            continue
        cs = [('m', rec.path)]
        if rec.path in core.splits:
            key = (rec.path, rec.slot)
            n = used.get(key, 0)
            used[key] = n + 1
            sel = routes.get(key, [])[n] if n < len(routes.get(key, [])) else rec.condition_value
            mismatch += sel != rec.condition_value
            cs.append(('c', rec.path, sel))
        exps.append((rec.tick, cs))
    q = {nm: [k for k, _ in s['z']] for nm in core.carrier_names}
    zr = carriers_at(exps, run.l_ticks, q, DT)
    dev = max(abs(z[ci] - zr[nm][k]) for k, z in s['z'] for ci, nm in enumerate(core.carrier_names))
    rd = max((abs(r.p_hat - zz) for r, (_, _, zz) in zip(run.ports['C'].records, s['eval_z'])), default=0.0)
    return dev, dict(route_vs_latched_mismatch=mismatch, readout_dev=rd)


def flip_suite():
    R = {}
    # (a)+(b)+(c): same history, opposite K, overlapping settlement; condition flips while observing.
    #   L@500 → W0@1000 has C1=1 (age 0.5 s); W0@1600 has C1=0 (age 1.1 s > H);
    #   L@2300 lies only in window 2 [1600, 2640) and flips C1 to 1 during window 2.
    core, run = inj_run([[1000, 1600], [], []], [500, 2300], 8000)
    recs = [r for r in run.ports['C'].records if r.path == 0]
    dev, _ = ref_check(core, run)
    z1 = z_end(run, ('c', 0, 1), core) - 0.5
    z0 = z_end(run, ('c', 0, 0), core) - 0.5
    R['opposite_K_concurrent'] = dict(conds=[r.condition_value for r in recs], slots=[r.slot for r in recs],
                                      route_log=run.summary('C')['route_log'], dz_leaf1=z1, dz_leaf0=z0,
                                      ref_dev=dev, route_flips=core.route_flips,
                                      ok=[r.condition_value for r in recs] == [1, 0] and z1 < 0 and z0 > 0
                                      and dev <= 0.03 and core.route_flips == 0)
    # (d) third entry rejected; existing K/T/O unchanged vs a run without the third pulse
    c3, r3 = inj_run([[1000, 1600, 2000], [], []], [500, 2300], 2600, z_every=0)
    c2, r2 = inj_run([[1000, 1600], [], []], [500, 2300], 2600, z_every=0)
    st = lambda c: [(s.T.charge, s.O.charge, k.cap.charge) for s, k in zip(c.slots[0], c.K[0])]
    rec3 = [r for r in r3.ports['C'].records if r.path == 0]
    R['third_entry_rejected'] = dict(status=[r.status for r in rec3], state_identical=st(c3) == st(c2),
                                     ok=rec3[-1].status == 'CAPACITY_REJECTED' and st(c3) == st(c2))
    # (e) K high cleared, then a low admission on the same slot is not contaminated
    core, run = inj_run([[1000, 6000], [], []], [500], 12000, slot_order=[[0, 1], [0, 1], [0, 1]])
    recs = [r for r in run.ports['C'].records if r.path == 0]
    s = run.summary('C')
    R['K_clear_then_low'] = dict(conds=[r.condition_value for r in recs], slots=[r.slot for r in recs],
                                 route_log=s['route_log'], admit_K=[round(x[4], 4) for x in s['admit']],
                                 ok=[r.condition_value for r in recs] == [1, 0] and [r.slot for r in recs] == [0, 0]
                                 and [x[2] for x in s['route_log']] == [1, 0])
    # (f) drain, then ≥ 120 s silence: every carrier |Δw| ≤ 1e-6
    core = CondMemoryCore(SPL)
    run = StreamRun(PulseInjector([[1000], [1500], [2000]], [1300], 3), {'C': core}, 130000, z_every=0,
                    hold_ticks=(8000, 128000)).run()
    h = run.log['C']['hold']
    dmax = max(abs(a - b) for a, b in zip(h[8000], h[128000]))
    R['drain_hold_120s'] = dict(max_abs_dw=dmax, ok=dmax <= 1e-6)
    return R


def main():
    t0 = time.time()
    R = {}
    # 1 no-split core ≡ E2 MemoryCore (bit-identical), dev replay stream
    from current_input_bridge import ReplayBridge
    from scenario_builder import build_main
    sc = build_main(97000011, 97100011)
    from stream_runner import PulseReplay
    base = StreamRun(ReplayBridge(sc['w'], sc['l'], label='dv'), {'B': MemoryCore()}, 120000).run()
    W, L = base.w_ticks, base.l_ticks
    r = StreamRun(PulseReplay(W, L, 3), {'B': MemoryCore(), 'C0': CondMemoryCore({})}, 120000).run()
    R['nosplit_bit_identical_E2'] = [x.p_hat for x in r.ports['B'].records] == [x.p_hat for x in r.ports['C0'].records] \
        and [m.w for m in r.cores['B'].mem] == [m.w for m in r.cores['C0'].mem]
    # 2 relabel + reverse summation (split core)
    a = StreamRun(PulseReplay(W, L, 3), {'C': CondMemoryCore(SPL)}, 120000).run()
    b = StreamRun(PulseReplay(W, L, 3), {'C': CondMemoryCore(SPL, slot_order=[[1, 0]] * 3, reverse_sum=True)}, 120000).run()
    R['relabel_reverse_max'] = max(abs(x.w - y.w) for x, y in zip(a.cores['C'].mem, b.cores['C'].mem))
    R['relabel_reverse_pred_max'] = max(abs(x.p_hat - y.p_hat) for x, y in zip(a.ports['C'].records, b.ports['C'].records))
    # 3 node vs reference on the dev stream; n_accept == n_settle; leaf settle entries == split admissions
    core = a.cores['C']
    dev, info = ref_check(core, a)
    s = a.summary('C')
    R['dev_stream_ref_dev'] = dev
    R.update(info)
    R['accept_eq_settle'] = s['n_accept'] == s['n_settle']
    R['leaf_entries_eq_admissions'] = all(sum(core.leaf_settle_entries[i][rr]) == core.slots[i][rr].n_accept
                                          for i in range(3) for rr in range(2))
    R['route_flips'] = core.route_flips
    # 4 consumer on/off identical
    cons = ThresholdConsumer()
    c1 = StreamRun(PulseReplay(W, L, 3), {'C': CondMemoryCore(SPL)}, 60000, consumers={'C': cons}).run()
    c2 = StreamRun(PulseReplay(W, L, 3), {'C': CondMemoryCore(SPL)}, 60000).run()
    R['consumer_on_off_identical'] = [m.w for m in c1.cores['C'].mem] == [m.w for m in c2.cores['C'].mem]
    R['consumer_hints'] = len(cons.hints)
    # 5 window boundary for leaves (last-in / first-out / same tick), C1 leaf 0 (no recent L)
    cases = {}
    for name, dl in (('L_same_tick', 0), ('L_last_in', jH - 1), ('L_first_out', jH), ('no_L', None)):
        l = [] if dl is None else [3000 + dl]
        cc, rr = inj_run([[3000], [], []], l, 8000, z_every=0)
        cases[name] = dict(dz_leaf0=cc.z(cc.leaf[0][0]) - 0.5, dz_marg=cc.z(0) - 0.5)
    R['leaf_window'] = dict(first_out_offset=jH, cases=cases,
                            ok=cases['L_same_tick']['dz_leaf0'] > 0 and cases['L_last_in']['dz_leaf0'] > 0
                            and cases['L_first_out']['dz_leaf0'] < 0 and cases['no_L']['dz_leaf0'] < 0)
    # 6 trace comparator boundary vs time reference: L at tick 1000, W0 at 1000+d
    bd = {}
    for d in range(jH - 3, jH + 4):
        cc, rr = inj_run([[1000 + d], [], []], [1000], 1000 + d + 5, z_every=0)
        rec = [x for x in rr.ports['C'].records if x.path == 0][0]
        bd[d] = dict(node=rec.condition_net, ref=int(d * DT <= H + 1e-12))
    last_node = max(d for d, v in bd.items() if v['node'] == 1)
    last_ref = max(d for d, v in bd.items() if v['ref'] == 1)
    R['trace_boundary'] = dict(cases=bd, last_on_node=last_node, last_on_ref=last_ref,
                               offset_ticks=last_node - last_ref, ok=abs(last_node - last_ref) <= 2)
    # 2H threshold boundary (C2 literal)
    j2 = math.floor(2 * H / DT + 1e-9)
    b2 = {}
    for d in range(j2 - 2, j2 + 4):
        cc, rr = inj_run([[1000 + d], [], []], [1000], 1000 + d + 5, z_every=0, splits={0: 'C2'})
        b2[d] = [x for x in rr.ports['C'].records if x.path == 0][0].condition_net
    R['trace_boundary_2H'] = dict(cases=b2, last_on_node=max(d for d, v in b2.items() if v == 1), last_on_ref=j2)
    # 7 occupancy: admission → slot free (T, O, K all recyclable), with/without observed L; K vs O clear
    occ = {}
    for name, l in (('no_L', []), ('L_observed', [1500])):
        core = CondMemoryCore({0: 'C1'})
        run = StreamRun(PulseInjector([[1000], [], []], l, 3), {'C': core}, 1, z_every=0)
        t_T = t_K = t_O = t_free = None
        for k in range(1, 8000):
            run.n = k + 1
            run.run()
            s0, K0 = core.slots[0][0], core.K[0][0]
            if t_T is None and k > 1000 and s0.T.voltage < core.P.theta_lo:
                t_T = k
            if t_K is None and t_T is not None and K0.is_free():
                t_K = k
            if t_O is None and t_T is not None and not core.cmp_on(s0.O.voltage - (core.P.O_free - 0.3)):
                t_O = k
            if t_free is None and k > 1000 and core.slot_free_c(0, 0):
                t_free = k
                break
        occ[name] = dict(T_below_lo_s=(t_T - 1000) * DT, K_clear_after_T_s=(t_K - t_T) * DT if t_K else None,
                         O_clear_after_T_s=(t_O - t_T) * DT if t_O else None, occupancy_s=(t_free - 1000) * DT)
    R['occupancy'] = occ
    # 8 condition-flip suite (also the deterministic part of domain S)
    R['flip_suite'] = flip_suite()
    # 9 K hold margin + trace set error
    core = CondMemoryCore(SPL)
    R['K_hold'] = dict(need_s=core.K[0][0].hold_need_s, margin_V=core.K[0][0].hold_margin_V)
    R['trace_set_error_rel'] = core.traces.set_error
    R['objects'] = (core.n_object_ids, core._object_count())
    R['wall_s'] = time.time() - t0
    os.makedirs(os.path.join(C.RES, 'dev'), exist_ok=True)
    json.dump(R, open(os.path.join(C.RES, 'dev', 'dev_checks_e3.json'), 'w'), indent=1, default=str)
    C.log_run(stage='DEV', run_id='dev_checks_e3', wall_s=R['wall_s'], note='mechanism checks, dev seeds + core injection')
    print(json.dumps(R, indent=1, default=str))


if __name__ == '__main__':
    main()
