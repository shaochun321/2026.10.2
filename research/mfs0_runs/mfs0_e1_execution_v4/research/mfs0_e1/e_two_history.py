"""Stage E — two pre-existing physical history paths W1/W2, exchange and recovery.

History identity lives only in which input path the generator drives; the
evaluator uses the label solely to score. Shared baseline: a 1-history device
whose single W input is driven by both templates (same waveform), labels kept
only for scoring.
"""
import json
import math
import os
import pickle
import random
import statistics as st
import time

from e1_common import RESULTS, log_run, budget_used_s
from sim import Rig, run_cycles, D_MIN, D_MAX

PR = json.load(open(os.path.join(os.path.dirname(__file__), 'preregistration.json'), encoding='utf-8'))['E_two_history']
PH = PR['phases']
N_PER = 60
NS = PR['streams']
W = 30


def schedule(s):
    rng = random.Random(20261030 + s)
    sch = []
    for ph in PH:
        order = [0] * N_PER + [1] * N_PER
        rng.shuffle(order)
        for h in order:
            p = ph['p_W1'] if h == 0 else ph['p_W2']
            sch.append(dict(hist=h, y=1 if rng.random() < p else 0, dL=rng.uniform(D_MIN, D_MAX), label=h))
    return sch


def ci95(xs):
    return st.mean(xs), 1.96 * st.stdev(xs) / math.sqrt(len(xs))


def main():
    t0 = time.time()
    streams = []
    for s in range(NS):
        tic = time.time()
        sch = schedule(s)
        rig = Rig(n_hist=2, w0=[0.5, 0.5], label=f"E{s}")
        out = run_cycles(rig, sch)
        for o, c in zip(out, sch):
            o['label'] = c['label']
        streams.append(dict(s=s, sch=sch, out=out))
        log_run(stage='E', run_id=f'E_stream_{s}', wall_s=time.time() - tic, note='formal')
        if s == 0:
            print(f"stream 0 wall {time.time() - tic:.1f}s -> projected {NS * (time.time() - tic) / 60:.1f} min", flush=True)
    shared = []
    for s in range(4):
        tic = time.time()
        sch = schedule(s)
        rig = Rig(n_hist=1, w0=0.5, label=f"Esh{s}")
        out = run_cycles(rig, [dict(hist=0, y=c['y'], dL=c['dL']) for c in sch])
        for o, c in zip(out, sch):
            o['label'] = c['label']
        shared.append(dict(s=s, out=out))
        log_run(stage='E', run_id=f'E_shared_{s}', wall_s=time.time() - tic, note='formal baseline')
    pickle.dump(dict(streams=streams, shared=shared), open(os.path.join(RESULTS, 'E_two_history.pkl'), 'wb'))

    R = {}
    R['B1_max_cross_write'] = max(abs(o['z_after'][1 - o['label']] - o['z_before'][1 - o['label']])
                                  for S in streams for o in S['out'])
    B2, B3, BR = [], [], []
    n_ph = 2 * N_PER
    for j, ph in enumerate(PH):
        for h in (0, 1):
            p = ph['p_W1'] if h == 0 else ph['p_W2']

            def own(S):
                seg = [o for o in S['out'][j * n_ph:(j + 1) * n_ph] if o['label'] == h]
                return seg
            wm = [st.mean(o['pred'] for o in own(S)[-W:]) for S in streams]
            m, hw = ci95(wm)
            B2.append(dict(phase=j + 1, hist=h + 1, p=p, mean_pred=m, ci_half=hw,
                           ok=abs(m - p) <= 0.05, precise=hw <= 0.03))
            br = st.mean(st.mean((o['pred'] - o['y']) ** 2 for o in own(S)[-W:]) for S in streams)
            brs = st.mean(st.mean((o['pred'] - o['y']) ** 2 for o in own(S)[-W:]) for S in shared)
            BR.append(dict(phase=j + 1, hist=h + 1, brier_device=br, brier_shared=brs,
                           brier_fixed05=0.25, brier_oracle=p * (1 - p)))
            if j > 0:
                new_high = p > 0.5
                ns = []
                for S in streams:
                    seg = own(S)
                    n = next((k + 1 for k, o in enumerate(seg) if (o['pred'] > 0.5) == new_high), float('inf'))
                    ns.append(n)
                B3.append(dict(exchange=j, hist=h + 1, median=st.median(ns), never=sum(n == float('inf') for n in ns)))
    R['B2'] = B2
    R['B3'] = B3
    R['brier'] = BR
    ok1 = R['B1_max_cross_write'] <= 1e-6
    ok2 = all(b['ok'] for b in B2)
    prec = all(b['precise'] for b in B2)
    ok3 = all(b['median'] <= 15 for b in B3)
    R['verdict'] = dict(B1=ok1, B2=ok2, B2_precise=prec, B3=ok3,
                        two_history=("PASS" if ok1 and ok2 and ok3 and prec else
                                     ("INCONCLUSIVE" if not prec else "FAIL")))
    R['wall_s'] = time.time() - t0
    R['budget_used_s'] = budget_used_s()
    json.dump(R, open(os.path.join(RESULTS, 'E_two_history.json'), 'w'), indent=1, default=str)
    print(json.dumps(R, indent=1, default=str))


if __name__ == '__main__':
    main()
