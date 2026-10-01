"""MFS0-E3 offline structure selector (plan §6). NEVER part of the runtime core.

Material: the 24 frozen E2 formal streams (all development material for E3). Only the
gate-accepted pulses are reused (W entry ticks = record ticks; L ticks); traces and
conditions are rebuilt causally from them by the time reference (relation_spec), and each
candidate is evaluated with the independent continuous reference (reference_solver_e3)
with the same α, delay, concurrency and initial value as the E3 core. Outcomes Y enter
only the evaluation (Brier) and the reference write targets, never a condition.

D1 = streams 0–11: per history choose the candidate with the largest mean Brier
improvement over the marginal reference (ties: fewer extra states, then lower index).
D2 = streams 12–23: validate only the D1 choice (paired per-stream t, upper < 0) and
the support rule (≥ 120 non-censored entries per leaf; ≥ 8 streams with ≥ 10 per leaf).
Output: results/selection/relation_table.json (+ full candidate table).
"""
import json
import os
import pickle
import time

import e3_common as C
from relation_spec import CANDIDATES, cond_ref, extra_state_key
from reference_solver_e3 import carriers_at, q_of, censored

DT = C.DT
N_TICKS = 900000
OUT = os.path.join(C.RES, 'selection')


def load_stream(s):
    d = pickle.load(open(os.path.join(C.E2_DIR, 'results', 'formal', f'stream_{s:02d}.pkl'), 'rb'))['full']
    rows = d['rows']
    w = [sorted(r[0] for r in rows if r[1] == i) for i in range(3)]
    adm = [sorted(r[0] for r in rows if r[1] == i and r[4] == 'ADMITTED') for i in range(3)]
    return w, adm, sorted(d['l_ticks'])


def eval_history(i, w, adm, l, cand):
    """Brier of history i under the marginal reference and (optionally) a candidate split."""
    ticks = [k for k in w[i] if not censored(k, N_TICKS, DT)]
    y = {k: q_of(k, l, DT) for k in ticks}
    if cand is None:
        z = carriers_at([(k, [('m', i)]) for k in adm[i]], l, {('m', i): ticks}, DT)[('m', i)]
        return sum((z[k] - y[k]) ** 2 for k in ticks) / len(ticks), None
    cond = {k: cond_ref(cand, i, k, w, l, DT) for k in w[i]}
    exps = [(k, [('c', i, cond[k])]) for k in adm[i]]
    q = {('c', i, 0): [k for k in ticks if cond[k] == 0], ('c', i, 1): [k for k in ticks if cond[k] == 1]}
    z = carriers_at(exps, l, q, DT)
    b = sum((z[('c', i, cond[k])][k] - y[k]) ** 2 for k in ticks) / len(ticks)
    n1 = sum(cond[k] for k in ticks)
    return b, dict(n0=len(ticks) - n1, n1=n1, y1=sum(y[k] for k in ticks if cond[k]) / max(n1, 1),
                   y0=sum(y[k] for k in ticks if not cond[k]) / max(len(ticks) - n1, 1))


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    data = [load_stream(s) for s in range(24)]
    # sanity: marginal reference equals the frozen E2 reference solver
    from reference_solver import reference_z
    from memory_core import MemoryCore
    w, adm, l = data[0]
    ad = sorted((k, i) for i in range(3) for k in adm[i])
    q = sorted(set(k for i in range(3) for k in w[i]))
    zr = reference_z(MemoryCore(), ad, l, q, DT, 0.5)
    mine = carriers_at([(k, [('m', i)]) for k, i in ad], l, {('m', i): q for i in range(3)}, DT)
    ref_check = max(abs(zr[i][k] - mine[('m', i)][k]) for i in range(3) for k in q)

    table = {}
    for i in range(3):
        base = {s: eval_history(i, *data[s], None)[0] for s in range(24)}
        for c in CANDIDATES:
            per = {}
            for s in range(24):
                b, info = eval_history(i, *data[s], c)
                per[s] = dict(d=b - base[s], **info)
            d1 = [per[s]['d'] for s in range(12)]
            n1_d1 = sum(per[s]['n1'] for s in range(12))
            n_d1 = n1_d1 + sum(per[s]['n0'] for s in range(12))
            table[f'H{i}_{c}'] = dict(history=i, cand=c, D1_mean_d=sum(d1) / 12, D1_t=C.t_interval(d1),
                                      pi_D1=n1_d1 / n_d1, per_stream=per)
    sel = {}
    for i in range(3):
        rows = [v for v in table.values() if v['history'] == i]
        best = min(rows, key=lambda v: (v['D1_mean_d'], extra_state_key(v['cand'])))
        c = best['cand']
        d2 = [best['per_stream'][s]['d'] for s in range(12, 24)]
        m, lo, hi = C.t_interval(d2)
        n0 = sum(best['per_stream'][s]['n0'] for s in range(12, 24))
        n1 = sum(best['per_stream'][s]['n1'] for s in range(12, 24))
        both10 = sum(1 for s in range(12, 24) if best['per_stream'][s]['n0'] >= 10 and best['per_stream'][s]['n1'] >= 10)
        gain_ok = best['D1_mean_d'] < 0 and hi < 0
        support_ok = n0 >= 120 and n1 >= 120 and both10 >= 8
        sel[i] = dict(candidate=c, D1_mean_d=best['D1_mean_d'], D2_mean_d=m, D2_ci=[lo, hi],
                      D2_leaf_n=[n0, n1], D2_streams_both_ge10=both10, pi_D1=best['pi_D1'],
                      gain_ok=gain_ok, support_ok=support_ok, split=gain_ok and support_ok)
    rel = dict(splits={str(i): dict(candidate=v['candidate'], pi_D1=v['pi_D1']) for i, v in sel.items() if v['split']},
               unsplit=[i for i, v in sel.items() if not v['split']], selection=sel,
               note='offline selector output; frozen before any E3 formal run; formal data never used for selection')
    json.dump(rel, open(os.path.join(OUT, 'relation_table.json'), 'w'), indent=1)
    slim = {k: {kk: vv for kk, vv in v.items() if kk != 'per_stream'} for k, v in table.items()}
    json.dump(dict(ref_check_max_abs=ref_check, candidates=slim, per_stream={k: v['per_stream'] for k, v in table.items()}),
              open(os.path.join(OUT, 'candidate_table.json'), 'w'), indent=1)
    C.log_run(stage='SELECT', run_id='structure_select', wall_s=time.time() - t0, note='offline selector on E2 formal streams (dev material)')
    print(f"reference cross-check vs E2 solver: max |Δz| = {ref_check:.2e}")
    for k, v in slim.items():
        print(f"{k:7s} D1 mean d={v['D1_mean_d']:+.5f}  CI=({v['D1_t'][1]:+.5f},{v['D1_t'][2]:+.5f})  pi={v['pi_D1']:.3f}")
    for i, v in sel.items():
        print(f"H{i}: {v['candidate']} D1={v['D1_mean_d']:+.5f} D2={v['D2_mean_d']:+.5f} CI=[{v['D2_ci'][0]:+.5f},{v['D2_ci'][1]:+.5f}] "
              f"leaf n={v['D2_leaf_n']} both>=10:{v['D2_streams_both_ge10']} split={v['split']}")


if __name__ == '__main__':
    main()
