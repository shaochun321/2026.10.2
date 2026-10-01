"""Dev-only: exercise formal/stress/live/evaluate pipeline end to end with DEV seeds (99xxx).
Results go to results/devpipe/ and are development evidence only."""
import os
import pickle
import sys
import time
from multiprocessing import Pool

import run_e2 as R
from e1_common import log_run

DEV = os.path.join(R.RES, 'devpipe')


def _cfg():
    R.RES = DEV
    R.PR['main']['seed_outcome_base'] = 99100
    R.PR['main']['seed_time_base'] = 99600
    R.PR['stress']['seed_outcome_base'] = 99200
    R.PR['stress']['seed_time_base'] = 99700
    R.PR['stress']['T_s'] = 1300.0
    R.PR['stress']['hold_ticks'] = [1270000, 1290000]
    R.PR['live']['seed'] = 99800


def f_formal(s):
    _cfg()
    return R.formal_stream(s)


def f_stress(s):
    _cfg()
    return R.stress_stream(s)


if __name__ == '__main__':
    for d in ('formal', 'stress', 'live', 'dev'):
        os.makedirs(os.path.join(DEV, d), exist_ok=True)
    t0 = time.time()
    with Pool(3) as pool:
        jobs = [pool.apply_async(f_formal, (s,)) for s in (0, 1)] + [pool.apply_async(f_stress, (0,))]
        _cfg()
        a = R.live_run('A', R.PR['live']['seed'])
        b = R.live_run('B', R.PR['live']['seed'], fork_at=R.PR['live']['fork_at_s'], seed_fork=R.PR['live']['seed'] + 7)
        pickle.dump(dict(A=a, B=b), open(os.path.join(DEV, 'live', 'live.pkl'), 'wb'))
        costs = [j.get() for j in jobs]
    tot = sum(sum(c.values()) if isinstance(c, dict) else c for _, c in costs) + a['cost_s'] + b['cost_s']
    log_run(stage='DEV', run_id='dev_pipeline_smoke', wall_s=tot, note='dev seeds; parallel costs summed')
    import shutil
    shutil.copy(os.path.join(R.RES.replace('devpipe', ''), 'dev', 'dev_checks.json'), os.path.join(DEV, 'dev', 'dev_checks.json'))
    import evaluate_system as E
    E.RES = DEV
    E.PR['stress']['hold_ticks'] = [1270000, 1290000]
    E.main()
    print(f"dev pipeline wall {time.time() - t0:.0f}s, summed cost {tot:.0f}s")
