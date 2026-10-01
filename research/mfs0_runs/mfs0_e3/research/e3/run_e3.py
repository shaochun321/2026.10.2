"""MFS0-E3 single entry.

  python -B run_e3.py A        # 24 × 900 s original E2 environment, groups B/C/R (lockstep fan-out)
  python -B run_e3.py X        # 12 × 900 s joint-relation task, groups B/C/R
  python -B run_e3.py L        # 6 × 900 s live boundary (sites 28/31/21 → 23), B/C/R + 450 s prefix fork
  python -B run_e3.py S        # 2 × 3600 s stress (C) + deterministic condition-flip suite
  python -B run_e3.py repro    # fresh-process re-run of A stream 0 and X stream 0 (bit identity)
  python -B run_e3.py report   # evaluate_e3 over saved results
Every formal command refuses to run unless prereg_E3.json exists and all frozen hashes match,
and never overwrites an existing result file. Set PYTHONHASHSEED=0 (live input determinism).
"""
import copy
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import e3_common as C  # noqa: E402

DT = C.DT
PREREG = os.environ.get('E3_PREREG', os.path.join(HERE, 'prereg_E3.json'))


def load_prereg(check=True):
    pr = json.load(open(PREREG, encoding='utf-8'))
    if check:
        bad = [f for f, h in pr['code_hashes'].items() if C.sha16(os.path.join(HERE, f)) != h]
        bad += [f for f, ok in ((n, v[2]) for n, v in C.check_e2_freeze().items()) if not ok]
        if bad or os.environ.get('PYTHONHASHSEED') != '0':
            raise SystemExit(f'prereg check failed: {bad}, PYTHONHASHSEED={os.environ.get("PYTHONHASHSEED")}')
    return pr


def _out(dom, name):
    d = os.path.join(C.RES, 'formal', dom)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    if os.path.exists(p):
        raise SystemExit(f'refusing to overwrite {p}')
    return p


def _groups(splits, pi, rseed):
    from memory_core import MemoryCore
    from conditional_memory_core import CondMemoryCore
    from stream_runner_e3 import RandomPort
    cores = {'B': MemoryCore(), 'C': CondMemoryCore(splits), 'R': CondMemoryCore(splits, random_port=True)}
    return cores, RandomPort(rseed, pi)


def _rel_ids(splits):
    return {g: {i: f'{g}:e_{i}:{c}' for i, c in splits.items()} for g in ('C', 'R')}


def _pack(run, extra):
    out = dict(extra, w_ticks=run.w_ticks, l_ticks=run.l_ticks, n_ticks=run.n,
               groups={g: run.summary(g) for g in run.cores})
    return out


def replay_stream(dom, s, pr, out_path=None, n_ticks=None):
    from current_input_bridge import ReplayBridge
    from scenario_builder_e3 import build_A, build_X
    from stream_runner_e3 import StreamRun
    from prediction_port import ThresholdConsumer
    t0 = time.time()
    D = pr['domains'][dom]
    sc = (build_A if dom == 'A' else build_X)(D['seed_outcome_base'] + s, D['seed_time_base'] + s)
    splits = {int(k): v for k, v in D['splits'].items()}
    cores, rport = _groups(splits, D['pi_R'], D['seed_R_base'] + s)
    cons = ThresholdConsumer()
    n = n_ticks or int(round(D['T_s'] / DT))
    run = StreamRun(ReplayBridge(sc['w'], sc['l'], label=f'{dom}{s}'), cores, n, rport=rport,
                    hold_ticks=D['hold_ticks'], relation_ids=_rel_ids(splits), consumers={'C': cons},
                    trace_every=10 if s == 0 else 0, trace_window=(220000, 260000)).run()
    src = dict(n_source_w=[len(x) for x in sc['w']], n_source_l=len(sc['l']), conflicts=sc['conflicts'])
    if dom == 'X':
        src['triggers'] = sc['triggers']
    out = _pack(run, dict(domain=dom, s=s, source=src, consumer_hints=len(cons.hints), cost_s=time.time() - t0))
    if out_path:
        pickle.dump(out, open(out_path, 'wb'))
    return out


def formal_replay(args):
    dom, s = args
    pr = load_prereg()
    out = replay_stream(dom, s, pr, _out(dom, f'stream_{s:02d}.pkl'))
    return dom, s, out['cost_s']


def live_stream(s):
    from current_input_bridge import LiveBridge
    from scenario_builder_e3 import build_L, LiveStimulus, L_SITES_W, L_SITE_L
    from stream_runner_e3 import StreamRun
    pr = load_prereg()
    D = pr['domains']['L']
    path = _out('L', f'stream_{s:02d}.pkl')
    t0 = time.time()
    sc = build_L(D['seed_outcome_base'] + s, D['seed_time_base'] + s)
    splits = {int(k): v for k, v in D['splits'].items()}
    cores, rport = _groups(splits, D['pi_R'], D['seed_R_base'] + s)
    stim = LiveStimulus(sc['pulses'])
    br = LiveBridge(list(L_SITES_W), L_SITE_L, stim)
    run = StreamRun(br, cores, int(round(D['T_s'] / DT)), rport=rport, hold_ticks=D['hold_ticks'],
                    relation_ids=_rel_ids(splits))
    fork = None
    if s == 0:
        kf = int(round(D['fork_at_s'] / DT))
        run.run(until=kf)
        ck_fork, ck_same = copy.deepcopy(run), copy.deepcopy(run)        # checkpoint: whole state
        t_main0 = time.time()
        run.run()
        t_main = time.time() - t_main0
        # (i) same-suffix resume from the checkpoint over 30 s must be bit-identical
        t1 = time.time()
        ck_same.run(until=kf + 30000)
        same = {g: [r for r in ck_same.ports[g].records] == [r for r in run.ports[g].records if r.tick < kf + 30000]
                for g in run.cores}
        same_z = {g: ck_same.log[g]['z'] == [z for z in run.log[g]['z'] if z[0] < kf + 30000] for g in run.cores}
        t_same = time.time() - t1
        # (ii) independent future from the checkpoint
        t2 = time.time()
        alt = build_L(None, None, fork_at=D['fork_at_s'], fork_seed=D['fork_seed'], base=sc['pulses'])
        ck_fork.src.stimulus.replace_future(alt['pulses'], D['fork_at_s'])
        ck_fork.run()
        t_fork = time.time() - t2
        fork = dict(fork_tick=kf, same_suffix_records_identical=same, same_suffix_z_identical=same_z,
                    prefix_records_identical={g: [r for r in ck_fork.ports[g].records if r.tick < kf] ==
                                              [r for r in run.ports[g].records if r.tick < kf] for g in run.cores},
                    fork_groups={g: ck_fork.summary(g) for g in ck_fork.cores},
                    fork_w_ticks=ck_fork.w_ticks, fork_l_ticks=ck_fork.l_ticks, fork_pulses=alt['pulses'],
                    cost_s=dict(main_suffix=t_main, same_check=t_same, fork_suffix=t_fork))
    else:
        run.run()
    out = _pack(run, dict(domain='L', s=s, source=dict(pulses=sc['pulses'], conflicts=sc['conflicts']),
                          spikes=dict(br.n_spikes), fork=fork, cost_s=time.time() - t0))
    pickle.dump(out, open(path, 'wb'))
    return 'L', s, out['cost_s']


def stress_stream(s):
    from current_input_bridge import ReplayBridge
    from scenario_builder_e3 import build_S
    from stream_runner import PulseInjector, CombinedBridge
    from stream_runner_e3 import StreamRun
    from conditional_memory_core import CondMemoryCore
    pr = load_prereg()
    D = pr['domains']['S']
    path = _out('S', f'stress_{s}.pkl')
    t0 = time.time()
    sc = build_S(D['seed_outcome_base'] + s, D['seed_time_base'] + s)
    splits = {int(k): v for k, v in D['splits'].items()}
    br = CombinedBridge(ReplayBridge(sc['w'], sc['l'], label=f'S{s}'), PulseInjector(sc['inj_w'], sc['inj_l'], 3))
    run = StreamRun(br, {'C': CondMemoryCore(splits)}, int(round(D['T_s'] / DT)), hold_ticks=D['hold_ticks'],
                    relation_ids=_rel_ids(splits)).run()
    out = _pack(run, dict(domain='S', s=s, source=dict(overload=sc['overload'], silence=sc['silence'],
                                                       n_inj_w=[len(x) for x in sc['inj_w']]), cost_s=time.time() - t0))
    pickle.dump(out, open(path, 'wb'))
    return 'S', s, out['cost_s']


def flip_suite_run():
    import dev_checks_e3
    path = _out('S', 'flip_suite.json')
    t0 = time.time()
    R = dev_checks_e3.flip_suite()
    R['cost_s'] = time.time() - t0
    json.dump(R, open(path, 'w'), indent=1, default=str)
    return R['cost_s']


def repro():
    pr = load_prereg()
    res = {}
    for dom in ('A', 'X'):
        t0 = time.time()
        new = replay_stream(dom, 0, pr)
        old = pickle.load(open(os.path.join(C.RES, 'formal', dom, 'stream_00.pkl'), 'rb'))
        res[dom] = {g: dict(records=new['groups'][g]['records'] == old['groups'][g]['records'],
                            final_w=new['groups'][g]['final_w'] == old['groups'][g]['final_w'])
                    for g in new['groups']}
        C.log_run(stage='REPRO', run_id=f'repro_{dom}_00', wall_s=time.time() - t0, note='fresh process re-run')
    p = _out('repro', 'repro.json')
    json.dump(res, open(p, 'w'), indent=1)
    print(res)


def main():
    cmd = sys.argv[1]
    workers = int(os.environ.get('E3_WORKERS', '3'))
    if cmd in ('A', 'X'):
        pr = load_prereg()
        n = pr['domains'][cmd]['streams']
        with Pool(workers) as pool:
            for dom, s, c in pool.imap_unordered(formal_replay, [(cmd, s) for s in range(n)]):
                C.log_run(stage='FORMAL', run_id=f'{dom}_{s:02d}', wall_s=c, note='parallel worker; B/C/R lockstep; cost summed')
                print(f'{dom} {s} done {c:.0f}s', flush=True)
    elif cmd == 'L':
        pr = load_prereg()
        with Pool(min(workers, pr['domains']['L']['streams'])) as pool:
            for dom, s, c in pool.imap_unordered(live_stream, range(pr['domains']['L']['streams'])):
                C.log_run(stage='FORMAL', run_id=f'L_{s:02d}', wall_s=c, note='live bridge; B/C/R lockstep; s=0 incl. fork')
                print(f'L {s} done {c:.0f}s', flush=True)
    elif cmd == 'S':
        pr = load_prereg()
        with Pool(2) as pool:
            for dom, s, c in pool.imap_unordered(stress_stream, range(pr['domains']['S']['streams'])):
                C.log_run(stage='FORMAL', run_id=f'S_{s}', wall_s=c, note='stress, C only')
                print(f'S {s} done {c:.0f}s', flush=True)
        c = flip_suite_run()
        C.log_run(stage='FORMAL', run_id='S_flip_suite', wall_s=c, note='deterministic core-injection flips')
    elif cmd == 'repro':
        repro()
    elif cmd == 'report':
        import evaluate_e3
        evaluate_e3.main()


if __name__ == '__main__':
    main()
