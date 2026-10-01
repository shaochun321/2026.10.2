"""MFS0-E2 single entry.

  python -B run_e2.py dev      # development checks (dev seeds only)
  python -B run_e2.py formal   # 24 x 900 s main matrix (parallel workers, costs summed)
  python -B run_e2.py stress   # 2 x 3600 s stress streams
  python -B run_e2.py live     # 120 s live-boundary bridge + same-prefix fork
  python -B run_e2.py report   # evaluate_system over saved results
"""
import json
import os
import pickle
import random
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import e1_common  # noqa: F401,E402
from e1_common import log_run  # noqa: E402

PR = json.load(open(os.path.join(HERE, 'prereg_E2.json'), encoding='utf-8'))
RES = os.path.join(HERE, 'results')
DT = 0.001


def _y_and_edge(k, l_ticks, H):
    import bisect
    j = bisect.bisect_left(l_ticks, k)
    if j < len(l_ticks):
        d = (l_ticks[j] - k) * DT
        y = 1 if d < H - 1e-12 else 0
        edge = abs(d - H) <= 2 * DT
    else:
        y, edge = 0, False
    return y, edge


def formal_stream(s):
    from memory_core import MemoryCore
    from stream_runner import run_stream, PulseReplay
    from current_input_bridge import ReplayBridge
    from reference_solver import reference_z
    from scenario_builder import build_main
    t0 = time.time()
    sc = build_main(PR['main']['seed_outcome_base'] + s, PR['main']['seed_time_base'] + s)
    n = int(round(PR['main']['T_s'] / DT))
    hold = PR['main']['hold_ticks']
    core = MemoryCore()
    full = run_stream(core, ReplayBridge(sc['w'], sc['l'], label=f'F{s}'), n,
                      trace_every=20 if s == 0 else 0, hold_ticks=hold)
    t_full = time.time() - t0
    t1 = time.time()
    core_nw = MemoryCore()
    core_nw.set_write_drive(0.0)
    nw = run_stream(core_nw, PulseReplay(full['w_ticks'], full['l_ticks'], 3), n, hold_ticks=hold)
    t_nw = time.time() - t1
    t2 = time.time()
    core_sh = MemoryCore(carrier_of=[0, 0, 0], w0=[0.5])
    sh = run_stream(core_sh, PulseReplay(full['w_ticks'], full['l_ticks'], 3), n, hold_ticks=hold)
    t_sh = time.time() - t2
    H = core.H_nominal
    out = dict(s=s, gen_conflicts=sc['conflicts'], n_source_w=[len(x) for x in sc['w']], n_source_l=len(sc['l']))
    for name, res, cr in (('full', full, core), ('no_write', nw, core_nw), ('shared', sh, core_sh)):
        recs = res['port'].records
        rows = []
        for r in recs:
            y, edge = _y_and_edge(r.tick, res['l_ticks'], H)
            rows.append((r.tick, r.path, r.p_hat, y, r.status, edge))
        adm = [(r.tick, r.path) for r in recs if r.status == 'ADMITTED']
        zr = reference_z(cr, adm, res['l_ticks'], [k for k, _ in res['z_log']], DT, [1.0 - m._w_initial for m in cr.mem])
        dev = max(abs(z[c] - zr[c][k]) for k, z in res['z_log'] for c in range(len(cr.mem)))
        rd = max((abs(r.p_hat - zz) for r, (_, _, zz) in zip(recs, res['eval_z'])), default=0.0)
        out[name] = dict(rows=rows, max_readout_dev=rd, l_ticks=res['l_ticks'], rejected=[len(x) for x in res['rejected']],
                         n_accept=res['n_accept'], n_settle=res['n_settle'], max_dev_ref=dev,
                         hold=res['hold'], objects=(res['objects_start'], res['objects_end']),
                         final_w=res['final_w'], n_gate_w=[len(x) for x in res['w_ticks']])
    out['trace'] = full['trace'] if s == 0 else None
    out['z_log0'] = full['z_log'] if s == 0 else None
    out['cost_s'] = dict(full=t_full, no_write=t_nw, shared=t_sh)
    with open(os.path.join(RES, 'formal', f'stream_{s:02d}.pkl'), 'wb') as f:
        pickle.dump(out, f)
    return s, out['cost_s']


def stress_stream(s):
    from memory_core import MemoryCore
    from stream_runner import run_stream, PulseInjector, CombinedBridge
    from current_input_bridge import ReplayBridge
    from reference_solver import reference_z
    from scenario_builder import build_stress
    t0 = time.time()
    sc = build_stress(PR['stress']['seed_outcome_base'] + s, PR['stress']['seed_time_base'] + s)
    n = int(round(PR['stress']['T_s'] / DT))
    core = MemoryCore()
    br = CombinedBridge(ReplayBridge(sc['w'], sc['l'], label=f'S{s}'), PulseInjector(sc['inj_w'], sc['inj_l'], 3))
    res = run_stream(core, br, n, hold_ticks=PR['stress']['hold_ticks'])
    adm = [(r.tick, r.path) for r in res['port'].records if r.status == 'ADMITTED']
    zr = reference_z(core, adm, res['l_ticks'], [k for k, _ in res['z_log']], DT, 0.5)
    dev = max(abs(z[c] - zr[c][k]) for k, z in res['z_log'] for c in range(3))
    recs = res['port'].records
    o0, o1 = sc['overload']
    out = dict(s=s, n_source_w=[len(x) for x in sc['w']], n_inj_w=[len(x) for x in sc['inj_w']],
               n_gate_w=[len(x) for x in res['w_ticks']],
               n_admitted=[sum(1 for r in recs if r.path == i and r.status == 'ADMITTED') for i in range(3)],
               n_rejected=[len(x) for x in res['rejected']],
               rejected_outside_overload=sum(1 for i in range(3) for k in res['rejected'][i]
                                             if not (o0 / DT <= k < o1 / DT + 3200)),
               n_accept=res['n_accept'], n_settle=res['n_settle'], objects=(res['objects_start'], res['objects_end']),
               hold=res['hold'], max_dev_ref=dev,
               records_after_overload=sum(1 for r in recs if r.tick > o1 / DT + 3200 and r.status == 'ADMITTED'),
               cost_s=time.time() - t0)
    with open(os.path.join(RES, 'stress', f'stress_{s}.pkl'), 'wb') as f:
        pickle.dump(out, f)
    return s, out['cost_s']


def _live_schedule(seed, T=120.0, fork_at=None, seed_fork=None):
    rng = random.Random(seed)
    pul = {28: [], 31: [], 23: []}
    for site, p_l in ((28, 0.8), (31, 0.2)):
        t = rng.uniform(1.0, 4.0) + (0.0 if site == 28 else 2.5)
        while t < T - 10.0:
            pul[site].append((t, t + 1.0))
            t += rng.uniform(5.0, 8.0)
    rl = random.Random(seed + 1)
    rf = random.Random(seed_fork) if seed_fork is not None else None
    ws = sorted((a, site) for site in (28, 31) for a, _ in pul[site])   # time order across sites
    for a, site in ws:
        p_l = 0.8 if site == 28 else 0.2
        fork = rf is not None and a >= fork_at
        r = rf if fork else rl
        if r.random() < ((1.0 - p_l) if fork else p_l):   # future differs only after fork_at
            d = a + r.uniform(0.3, 0.6)
            if all(abs(d - x) >= 5.0 for x, _ in pul[23]):
                pul[23].append((d, d + 1.0))
    return pul


def live_run(tag, seed, fork_at=None, seed_fork=None):
    from memory_core import MemoryCore
    from stream_runner import run_stream
    from current_input_bridge import LiveBridge
    pul = _live_schedule(seed, fork_at=fork_at, seed_fork=seed_fork)

    def stim(t):               # causal: returns only the current dT per site
        return {s: (0.05 if any(a <= t < b for a, b in iv) else 0.0) for s, iv in pul.items()}
    t0 = time.time()
    br = LiveBridge([28, 31], 23, stim)
    core = MemoryCore(n_hist=2, n_slot=2)
    res = run_stream(core, br, int(round(PR['live']['T_s'] / DT)), z_every=100)
    H = core.H_nominal
    rows = [(r.tick, r.path, r.p_hat, _y_and_edge(r.tick, res['l_ticks'], H)[0], r.status)
            for r in res['port'].records]
    return dict(tag=tag, rows=rows, z_log=res['z_log'], l_ticks=res['l_ticks'], w_ticks=res['w_ticks'],
                spikes=br.n_spikes, stim_pulses={k: len(v) for k, v in pul.items()},
                objects=(res['objects_start'], res['objects_end']), cost_s=time.time() - t0)


def main():
    cmd = sys.argv[1]
    if cmd == 'formal':
        os.makedirs(os.path.join(RES, 'formal'), exist_ok=True)
        with Pool(PR['workers']) as pool:
            for s, c in pool.imap_unordered(formal_stream, range(PR['main']['streams'])):
                for k, v in c.items():
                    log_run(stage='FORMAL', run_id=f'main_{s:02d}_{k}', wall_s=v, note='parallel worker; cost summed')
                print(f"stream {s} done {c}", flush=True)
    elif cmd == 'stress':
        os.makedirs(os.path.join(RES, 'stress'), exist_ok=True)
        with Pool(2) as pool:
            for s, c in pool.imap_unordered(stress_stream, range(PR['stress']['streams'])):
                log_run(stage='STRESS', run_id=f'stress_{s}', wall_s=c, note='parallel worker')
                print(f"stress {s} done {c:.0f}s", flush=True)
    elif cmd == 'live':
        os.makedirs(os.path.join(RES, 'live'), exist_ok=True)
        a = live_run('A', PR['live']['seed'])
        log_run(stage='LIVE', run_id='live_A', wall_s=a['cost_s'])
        b = live_run('B_fork', PR['live']['seed'], fork_at=PR['live']['fork_at_s'], seed_fork=PR['live']['seed'] + 7)
        log_run(stage='LIVE', run_id='live_B_fork', wall_s=b['cost_s'])
        pickle.dump(dict(A=a, B=b), open(os.path.join(RES, 'live', 'live.pkl'), 'wb'))
        print('live done', a['cost_s'], b['cost_s'])
    elif cmd == 'report':
        import evaluate_system
        evaluate_system.main()


if __name__ == '__main__':
    main()
