"""E1.1 B — one-shot two-history confirmation on the unchanged v4 device.

Only the evaluation entry is new: 32 fresh streams, seeds 20261130+s, t intervals.
Device / generator / transduction are byte-identical copies of the v4 frozen files.
"""
import json
import os
import pickle
import random
import statistics as st
import time

from e1_common import RESULTS, log_run, budget_used_s
from sim import Rig, run_cycles, D_MIN, D_MAX

PR = json.load(open(os.path.join(os.path.dirname(__file__), 'preregistration_E1_1.json'), encoding='utf-8'))['B']
PH = PR['phases']
N_PER = PR['n_per_history_per_phase']
NS = PR['streams']
W = PR['eval_window']
T_CRIT = PR['t_crit_df31_0975']
OUT = os.path.join(RESULTS, 'B')


def schedule(s):
    rng = random.Random(PR['seed_base'] + s)
    sch = []
    for ph in PH:
        order = [0] * N_PER + [1] * N_PER
        rng.shuffle(order)
        for h in order:
            p = ph['p_W1'] if h == 0 else ph['p_W2']
            sch.append(dict(hist=h, y=1 if rng.random() < p else 0, dL=rng.uniform(D_MIN, D_MAX), label=h))
    return sch


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    streams, errors = [], []
    for s in range(NS):
        tic = time.time()
        try:
            sch = schedule(s)
            rig = Rig(n_hist=2, w0=[0.5, 0.5], label=f"B{s}")
            out = run_cycles(rig, sch)
            for o, c in zip(out, sch):
                o['label'] = c['label']
            streams.append(dict(s=s, out=out))
        except Exception as e:                    # execution anomaly -> ERROR, not a statistic
            errors.append(dict(s=s, err=repr(e)))
        log_run(stage='B', run_id=f'B_stream_{s}', wall_s=time.time() - tic, note='formal')
        if s == 0:
            print(f"stream 0 wall {time.time() - tic:.1f}s -> projected {NS * (time.time() - tic) / 60:.1f} min", flush=True)
    pickle.dump(dict(streams=streams, errors=errors), open(os.path.join(OUT, 'B_confirm.pkl'), 'wb'))

    R = dict(errors=errors, n_streams=len(streams))
    R['B1_max_cross_write'] = max(abs(o['z_after'][1 - o['label']] - o['z_before'][1 - o['label']])
                                  for S in streams for o in S['out'])
    zs = [z for S in streams for o in S['out'] for z in o['z_after']]
    R['state_range'] = [min(zs), max(zs)]
    R['n_outside_mapping_grid_0.02_0.98'] = sum(1 for z in zs if z < 0.02 or z > 0.98)
    R['n_state_values'] = len(zs)
    B2, B3 = [], []
    n_ph = 2 * N_PER
    for j, ph in enumerate(PH):
        for h in (0, 1):
            p = ph['p_W1'] if h == 0 else ph['p_W2']
            own = lambda S: [o for o in S['out'][j * n_ph:(j + 1) * n_ph] if o['label'] == h]
            wm = [st.mean(o['pred'] for o in own(S)[-W:]) for S in streams]
            m = st.mean(wm)
            hw = T_CRIT * st.stdev(wm) / len(wm) ** 0.5
            B2.append(dict(phase=j + 1, hist=h + 1, p=p, mean=m, t_half=hw,
                           mean_ok=abs(m - p) <= 0.05, precise=hw <= 0.03))
            if j > 0:
                hi = p > 0.5
                ns = [next((k + 1 for k, o in enumerate(own(S)) if (o['pred'] > 0.5) == hi), float('inf'))
                      for S in streams]
                B3.append(dict(exchange=j, hist=h + 1, median=st.median(ns), never=sum(n == float('inf') for n in ns)))
    R['B2'], R['B3'] = B2, B3
    b1 = R['B1_max_cross_write'] <= 1e-6
    b2m = all(b['mean_ok'] for b in B2)
    b2p = all(b['precise'] for b in B2)
    b3 = all(b['median'] <= 15 for b in B3)
    if errors:
        verdict = 'ERROR'
    elif not (b1 and b2m and b3):
        verdict = 'FAIL'
    elif not b2p:
        verdict = 'INCONCLUSIVE'
    else:
        verdict = 'PASS'
    R['verdict'] = dict(B1=b1, B2_mean=b2m, B2_precision=b2p, B3=b3, two_history=verdict)
    R['wall_s'] = time.time() - t0
    R['budget_used_s'] = budget_used_s()
    json.dump(R, open(os.path.join(OUT, 'B_confirm.json'), 'w'), indent=1, default=str)
    print(json.dumps(R, indent=1, default=str))


if __name__ == '__main__':
    main()
