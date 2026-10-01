"""Stage D — continuous adaptation 0.8 → 0.2 → 0.8 on one continuously running device per stream."""
import json
import math
import os
import pickle
import random
import statistics as st
import time

from e1_common import RESULTS, log_run, budget_used_s
from sim import Rig, run_cycles, bernoulli_schedule
from device import Params

PR = json.load(open(os.path.join(os.path.dirname(__file__), 'preregistration.json'), encoding='utf-8'))['D_main']
PH = PR['phases']
NS = PR['streams']
A0 = Params().alpha0
W = 30


def ps_list():
    return [ph['p'] for ph in PH for _ in range(ph['n'])]


def run_stream(s, **dev_attr):
    sch = bernoulli_schedule(ps_list(), 20260930 + s)
    rig = Rig(w0=1.0 - PR['z0'], label=f"D{s}")
    for k, v in dev_attr.items():
        setattr(rig.dev, k, v)
    rig_id = id(rig.dev)
    out = run_cycles(rig, sch)
    assert id(rig.dev) == rig_id
    return sch, out, dict(energy_D=rig.dev.energy_D, energy_W=rig.dev.energy_W,
                          q_up=rig.dev.h[0].q_up, q_dn=rig.dev.h[0].q_dn)


def z_ref(ys, z0):
    z, out = z0, []
    for y in ys:
        z = (1 - A0) * z + A0 * y
        out.append(z)
    return out


def ci95(xs):
    m = st.mean(xs)
    h = 1.96 * st.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else float('inf')
    return m, h


def main():
    t0 = time.time()
    streams = []
    for s in range(NS):
        tic = time.time()
        sch, out, led = run_stream(s)
        streams.append(dict(s=s, sch=sch, out=out, led=led))
        log_run(stage='D', run_id=f'D_stream_{s}', wall_s=time.time() - tic, note='formal')
        if s == 0:
            print(f"stream 0 wall {time.time() - tic:.1f}s  -> projected {NS * (time.time() - tic) / 60:.1f} min", flush=True)
    base = {}
    for name, attr in (('no_write', dict(write_enabled=False)), ('one_direction', dict(down_branch=False))):
        base[name] = []
        for s in range(4):
            tic = time.time()
            sch, out, led = run_stream(s, **attr)
            base[name].append(dict(s=s, sch=sch, out=out, led=led))
            log_run(stage='D', run_id=f'D_{name}_{s}', wall_s=time.time() - tic, note='formal baseline')
    pickle.dump(dict(streams=streams, base=base), open(os.path.join(RESULTS, 'D_main.pkl'), 'wb'))

    # ── evaluation ──
    R = {}
    bounds = [0]
    for ph in PH:
        bounds.append(bounds[-1] + ph['n'])
    dev_max = 0.0
    for S in streams:
        ys = [c['y'] for c in S['sch']]
        zr = z_ref(ys, PR['z0'])
        zd = [o['z_after'][0] for o in S['out']]
        dev_max = max(dev_max, max(abs(a - b) for a, b in zip(zd, zr)))
    R['A1_max_dev_vs_ref'] = dev_max

    def window(S, j):
        return S['out'][bounds[j + 1] - W:bounds[j + 1]]

    A2, A4 = [], []
    for j, ph in enumerate(PH):
        wm = [st.mean(o['pred'] for o in window(S, j)) for S in streams]
        m, h = ci95(wm)
        br = [st.mean((o['pred'] - o['y']) ** 2 for o in window(S, j)) for S in streams]
        brn = [st.mean((o['pred'] - o['y']) ** 2 for o in window(S, j)) for S in base['no_write']]
        br1 = [st.mean((o['pred'] - o['y']) ** 2 for o in window(S, j)) for S in base['one_direction']]
        A2.append(dict(phase=j + 1, p=ph['p'], mean_pred=m, ci_half=h, ok=abs(m - ph['p']) <= 0.05,
                       precise=h <= 0.03))
        A4.append(dict(phase=j + 1, brier_device=st.mean(br), brier_ci_half=ci95(br)[1],
                       brier_no_write=st.mean(brn), brier_one_dir=st.mean(br1),
                       brier_fixed05=0.25, brier_oracle=ph['p'] * (1 - ph['p']),
                       emp_rate=st.mean(o['y'] for S in streams for o in window(S, j))))
    R['A2'] = A2
    R['A4'] = A4
    A3 = []
    for j in (1, 2):
        new_high = PH[j]['p'] > 0.5
        ns = []
        for S in streams:
            seg = S['out'][bounds[j]:bounds[j + 1]]
            n = next((k + 1 for k, o in enumerate(seg) if (o['pred'] > 0.5) == new_high), None)
            ns.append(n if n is not None else float('inf'))
        srt = sorted(ns)
        A3.append(dict(reversal=j, median=st.median(ns), q25=srt[len(srt) // 4], q75=srt[3 * len(srt) // 4],
                       never=sum(1 for n in ns if n == float('inf'))))
    R['A3'] = A3
    integ = dict(w_entries_all_1=all(o['n_bw'] == [1] for S in streams for o in S['out']),
                 l_entries_eq_y=all(o['n_bl'] == o['y'] for S in streams for o in S['out']),
                 O_end_max=max(o['O_end'] for S in streams for o in S['out']),
                 energy_W_mean=st.mean(S['led']['energy_W'] for S in streams),
                 energy_D_mean=st.mean(S['led']['energy_D'] for S in streams))
    integ['ok'] = integ['w_entries_all_1'] and integ['l_entries_eq_y'] and integ['O_end_max'] < 1e-3
    R['A5'] = integ
    nw_dz = max(abs(o['z_after'][0] - o['z_before'][0]) for S in base['no_write'] for o in S['out'])
    od_mono = all(o['z_after'][0] >= o['z_before'][0] - 1e-15 for S in base['one_direction'] for o in S['out'])
    R['interventions'] = dict(no_write_max_dz=nw_dz, one_direction_monotone=od_mono,
                              one_direction_final_z=[S['out'][-1]['z_after'][0] for S in base['one_direction']])
    ok1 = dev_max <= 0.05
    ok2 = all(a['ok'] for a in A2)
    prec = all(a['precise'] for a in A2)
    ok3 = all(a['median'] <= 15 for a in A3)
    ok4 = all(A4[j]['brier_device'] < A4[j]['brier_no_write'] for j in (1, 2))
    R['verdict'] = dict(A1=ok1, A2=ok2, A2_precise=prec, A3=ok3, A4=ok4, A5=integ['ok'],
                        adaptation=("PASS" if (ok1 and ok2 and ok3 and ok4 and integ['ok'] and prec)
                                    else ("INCONCLUSIVE" if not prec else "FAIL")))
    R['wall_s'] = time.time() - t0
    R['budget_used_s'] = budget_used_s()
    json.dump(R, open(os.path.join(RESULTS, 'D_main.json'), 'w'), indent=1, default=str)
    print(json.dumps(R, indent=1, default=str))


if __name__ == '__main__':
    main()
