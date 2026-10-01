"""E1.3 A (+ conditional B) — reference-model screen: 3 fixed, frozen E1.2 feedback, CUSUM candidate."""
import json
import math
import os
import random
import statistics as st
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PR = json.load(open(os.path.join(HERE, 'prereg_AB.json'), encoding='utf-8'))
POL = list(PR['policies'])
OUT = os.path.join(HERE, 'results', 'AB')
os.makedirs(OUT, exist_ok=True)
KAP, H, K = 0.10, 0.80, 6


def run(name, ys, z0=0.5):
    """Returns rows (p_hat, m, alpha, y, fast_flag, trigger_after_this)."""
    z, h, sp, sm, bal = z0, 0.0, 0.0, 0.0, 0
    rows = []
    for y in ys:
        trig = False
        if name == 'cusum':
            fast = bal > 0
            m = 1.5 if fast else 0.5
        elif name == 'e12_feedback':
            fast = False
            m = 0.5 + min(1.0, abs(h) / 0.2)
        else:
            fast = False
            m = float(name.split('_')[1])
        a = 1 - 0.9 ** m
        p_hat = z
        z = z + a * (y - z)
        d = y - p_hat                       # o_n = Y_n (ideal readout)
        if name == 'cusum':
            if fast:
                bal -= 1
                sp = sm = 0.0
            else:
                sp = max(0.0, sp + d - KAP)
                sm = max(0.0, sm - d - KAP)
                if sp >= H or sm >= H:
                    bal, sp, sm, trig = K, 0.0, 0.0, True
        elif name == 'e12_feedback':
            h = 0.8 * h + 0.2 * d
        rows.append((p_hat, m, a, y, fast, trig))
    return rows


def gen_A(s):
    ry = random.Random(20270301 + s)
    rt = random.Random(20770301 + s)
    T = {}
    for p in (0.2, 0.5, 0.8):
        T[f'stable_{p}'] = ([1 if ry.random() < p else 0 for _ in range(360)], [p] * 360)
    ps = [0.8] * 120 + [0.2] * 120 + [0.8] * 120
    T['reversal'] = ([1 if ry.random() < p else 0 for p in ps], ps)
    _ = {k: [rt.uniform(0.10, 0.80) for _ in v[0]] for k, v in T.items()}
    return T


def gen_B(s):
    ry = random.Random(20270401 + s)
    rt = random.Random(20770401 + s)
    ps = [0.65] * 120 + [0.35] * 120 + [0.65] * 120
    T = ([1 if ry.random() < p else 0 for p in ps], ps)
    _ = [rt.uniform(0.10, 0.80) for _ in ps]
    return T


def mse(rows, ps, idx):
    return st.mean((rows[i][0] - ps[i]) ** 2 for i in idx)


def pooled_cov(a, b):
    ma, mb = st.mean(a), st.mean(b)
    return st.mean((x - ma) * (y - mb) for x, y in zip(a, b))


STAB = range(120, 360)
REV = list(range(120, 150)) + list(range(240, 270))


def stage_A():
    t0 = time.time()
    NS, TC = PR['A']['streams'], PR['A']['t_crit_df63_0975']
    per = {p: dict(smean={q: [] for q in (0.2, 0.5, 0.8)}, smse={q: [] for q in (0.2, 0.5, 0.8)}, rmse=[],
                   trig={q: [] for q in (0.2, 0.5, 0.8)}, fastf={q: [] for q in (0.2, 0.5, 0.8)},
                   first_trig={q: [] for q in (0.2, 0.5, 0.8)}, delay=[], pool={q: dict(a=[], y=[], z=[]) for q in (0.2, 0.5, 0.8)})
           for p in POL}
    ident = {}
    for s in range(NS):
        T = gen_A(s)
        for pol in POL:
            d = per[pol]
            for q in (0.2, 0.5, 0.8):
                ys, ps = T[f'stable_{q}']
                r = run(pol, ys)
                d['smean'][q].append(st.mean(r[i][0] for i in STAB))
                d['smse'][q].append(mse(r, ps, STAB))
                d['trig'][q].append(sum(r[i][5] for i in STAB))
                d['fastf'][q].append(st.mean(r[i][4] for i in STAB))
                d['first_trig'][q].append(next((i for i, x in enumerate(r) if x[5]), None))
                d['pool'][q]['a'] += [r[i][2] for i in STAB]
                d['pool'][q]['y'] += [r[i][3] for i in STAB]
                d['pool'][q]['z'] += [r[i][0] for i in STAB]
            ys, ps = T['reversal']
            r = run(pol, ys)
            d['rmse'].append(mse(r, ps, REV))
            for sw in (120, 240):
                d['delay'].append(next((k for k in range(120) if r[sw + k][5]), None))
    S = {}
    for pol in POL:
        d = per[pol]
        S[pol] = dict(stable_mean={q: st.mean(v) for q, v in d['smean'].items()},
                      stable_t_half={q: TC * st.stdev(v) / math.sqrt(NS) for q, v in d['smean'].items()},
                      stable_mse={q: st.mean(v) for q, v in d['smse'].items()},
                      stable_loss=st.mean(st.mean(v) for v in d['smse'].values()),
                      reversal_loss=st.mean(d['rmse']))
        if pol == 'cusum':
            S[pol]['triggers_per_eval_window'] = {q: st.mean(v) for q, v in d['trig'].items()}
            S[pol]['fast_fraction'] = {q: st.mean(v) for q, v in d['fastf'].items()}
            ft = {q: [x for x in v if x is not None] for q, v in d['first_trig'].items()}
            S[pol]['first_trigger_median'] = {q: (st.median(v) if v else None) for q, v in ft.items()}
            S[pol]['streams_never_triggered'] = {q: sum(1 for x in v if x is None) for q, v in d['first_trig'].items()}
            dl = [x for x in d['delay'] if x is not None]
            S[pol]['switch_trigger_delay_median'] = st.median(dl) if dl else None
            S[pol]['switch_no_trigger_within_120'] = sum(1 for x in d['delay'] if x is None)
            cv = {}
            for q in (0.2, 0.5, 0.8):
                P = d['pool'][q]
                cv[q] = dict(cov_aY=pooled_cov(P['a'], P['y']), cov_az=pooled_cov(P['a'], P['z']),
                             bias=st.mean(P['z']) - q)
            S[pol]['pooled_per_p'] = cv
    F, B1 = S['cusum'], S['fixed_1']
    a1 = all(abs(F['stable_mean'][q] - q) <= 0.03 and F['stable_t_half'][q] <= 0.03 for q in (0.2, 0.5, 0.8))
    a2d = {q: F['stable_mse'][q] - B1['stable_mse'][q] for q in (0.2, 0.5, 0.8)}
    diffs = [f - b for f, b in zip(per['cusum']['rmse'], per['fixed_1']['rmse'])]
    ub = st.mean(diffs) + TC * st.stdev(diffs) / math.sqrt(NS)
    lb = st.mean(diffs) - TC * st.stdev(diffs) / math.sqrt(NS)
    a3 = F['reversal_loss'] <= 0.9 * B1['reversal_loss'] and ub < 0
    dom = [p for p in ('fixed_0.5', 'fixed_1', 'fixed_1.5')
           if S[p]['stable_loss'] <= F['stable_loss'] and S[p]['reversal_loss'] <= F['reversal_loss']]
    crit = dict(A1=a1, A2=all(v <= 0.005 for v in a2d.values()), A3=a3, A4=not dom)
    alt = min(('fixed_0.5', 'fixed_1.5'), key=lambda p: 0.5 * S[p]['stable_loss'] + 0.5 * S[p]['reversal_loss'])
    R = dict(summary=S, A2_delta=a2d, A3=dict(rel=F['reversal_loss'] / B1['reversal_loss'] - 1,
             paired_mean=st.mean(diffs), paired_t=[lb, ub]), A4_dominated_by=dom, criteria=crit,
             alt_fixed_for_C=alt, verdict='GO_B' if all(crit.values()) else 'POLICY_NOT_JUSTIFIED',
             wall_s=time.time() - t0)
    json.dump(R, open(os.path.join(OUT, 'A_screen.json'), 'w'), indent=1, default=str)
    with open(os.path.join(HERE, 'runs.jsonl'), 'a') as f:
        f.write(json.dumps(dict(stage='A', run_id='a_screen', wall_s=R['wall_s'])) + "\n")
    for pol in POL:
        x = S[pol]
        print(f"{pol:<13} mean {[round(x['stable_mean'][q], 4) for q in (0.2, 0.5, 0.8)]} "
              f"MSE {[round(x['stable_mse'][q], 5) for q in (0.2, 0.5, 0.8)]} stable {x['stable_loss']:.5f} rev {x['reversal_loss']:.5f}")
    c = S['cusum']
    print("cusum triggers/240 per p", {q: round(v, 2) for q, v in c['triggers_per_eval_window'].items()},
          "fast frac", {q: round(v, 3) for q, v in c['fast_fraction'].items()},
          "never triggered", c['streams_never_triggered'], "first trig median", c['first_trigger_median'])
    print("switch trigger delay median", c['switch_trigger_delay_median'], "no trigger within 120:", c['switch_no_trigger_within_120'])
    print("pooled per p", {q: {k: round(v, 6) for k, v in d.items()} for q, d in c['pooled_per_p'].items()})
    print("A2 delta", {q: round(v, 5) for q, v in a2d.items()}, "A3", {k: (round(v, 5) if isinstance(v, float) else [round(u, 5) for u in v]) for k, v in R['A3'].items()},
          "dominated by", dom)
    print("criteria", crit, "->", R['verdict'], "| alt fixed:", alt, f"| wall {R['wall_s']:.1f}s")
    return R


def stage_B():
    t0 = time.time()
    NS, TC = PR['B_conditional']['streams'], PR['B_conditional']['t_crit_df31_0975']
    rm = {p: [] for p in POL}
    for s in range(NS):
        ys, ps = gen_B(s)
        for pol in POL:
            rm[pol].append(mse(run(pol, ys), ps, REV))
    diffs = [f - b for f, b in zip(rm['cusum'], rm['fixed_1'])]
    m = st.mean(diffs)
    hw = TC * st.stdev(diffs) / math.sqrt(NS)
    R = dict(reversal_loss={p: st.mean(v) for p, v in rm.items()}, paired_mean=m, paired_t=[m - hw, m + hw],
             rel=st.mean(rm['cusum']) / st.mean(rm['fixed_1']) - 1,
             verdict='TRANSFER_OK' if m <= 0.005 else 'TRANSFER_FAIL', wall_s=time.time() - t0)
    R['gain_status'] = ('clear_gain' if m + hw < 0 else 'clear_degradation' if m - hw > 0 else 'no_clear_difference')
    json.dump(R, open(os.path.join(OUT, 'B_transfer.json'), 'w'), indent=1)
    with open(os.path.join(HERE, 'runs.jsonl'), 'a') as f:
        f.write(json.dumps(dict(stage='B', run_id='b_transfer', wall_s=R['wall_s'])) + "\n")
    print("B reversal loss", {p: round(v, 5) for p, v in R['reversal_loss'].items()})
    print(f"B paired cusum - fixed_1: {m:+.5f} [{m - hw:+.5f}, {m + hw:+.5f}] rel {R['rel']:+.4f} -> {R['verdict']} ({R['gain_status']})")
    return R


if __name__ == '__main__':
    ra = stage_A()
    if ra['verdict'] == 'GO_B':
        stage_B()
