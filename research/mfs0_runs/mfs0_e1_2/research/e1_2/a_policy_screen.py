"""E1.2 A — cheap reference-model screen of 3 fixed speeds vs the single feedback candidate."""
import json
import math
import os
import random
import statistics as st
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PR = json.load(open(os.path.join(HERE, 'prereg_A.json'), encoding='utf-8'))
NS = PR['streams']
TC = PR['t_crit_df63_0975']
OUT = os.path.join(HERE, 'results', 'A')
os.makedirs(OUT, exist_ok=True)


def policy_m(name, h):
    if name == 'feedback':
        return 0.5 + min(1.0, abs(h) / 0.2)
    return float(name.split('_')[1])


def run(name, ys, z0=0.5):
    """Ideal reference: returns per-step (p_hat, m, alpha, y)."""
    z, h, rows = z0, 0.0, []
    for y in ys:
        m = policy_m(name, h)            # fixed before this outcome
        a = 1 - 0.9 ** m
        p_hat = z
        rows.append((p_hat, m, a, y))
        z = z + a * (y - z)
        h = 0.8 * h + 0.2 * (y - p_hat)  # o_n = Y_n in the ideal model
    return rows


def gen(s):
    ry = random.Random(20270101 + s)
    rt = random.Random(20770101 + s)
    tasks = {}
    for p in (0.2, 0.5, 0.8):
        tasks[f'stable_{p}'] = ([1 if ry.random() < p else 0 for _ in range(360)], [p] * 360)
    ps = [0.8] * 120 + [0.2] * 120 + [0.8] * 120
    tasks['reversal'] = ([1 if ry.random() < p else 0 for p in ps], ps)
    dls = {k: [rt.uniform(0.10, 0.80) for _ in v[0]] for k, v in tasks.items()}
    return tasks, dls


def mse(rows, ps, idx):
    return st.mean((rows[i][0] - ps[i]) ** 2 for i in idx)


def cov(a, b):
    ma, mb = st.mean(a), st.mean(b)
    return st.mean((x - ma) * (y - mb) for x, y in zip(a, b))


def main():
    t0 = time.time()
    POL = list(PR['policies'])
    stab_idx = range(120, 360)
    rev_idx = list(range(120, 150)) + list(range(240, 270))
    per = {pol: {'stable_mean': {p: [] for p in (0.2, 0.5, 0.8)}, 'stable_mse': {p: [] for p in (0.2, 0.5, 0.8)},
                 'rev_mse': [], 'm_mean': [], 'sat': [], 'brier': [], 'cov_aY': [], 'cov_az': [], 'rec': []}
           for pol in POL}
    for s in range(NS):
        tasks, _ = gen(s)
        for pol in POL:
            d = per[pol]
            allm = []
            for p in (0.2, 0.5, 0.8):
                ys, ps = tasks[f'stable_{p}']
                rows = run(pol, ys)
                d['stable_mean'][p].append(st.mean(rows[i][0] for i in stab_idx))
                d['stable_mse'][p].append(mse(rows, ps, stab_idx))
                d['brier'].append(st.mean((rows[i][0] - rows[i][3]) ** 2 for i in stab_idx))
                d['cov_aY'].append(cov([rows[i][2] for i in stab_idx], [rows[i][3] for i in stab_idx]))
                d['cov_az'].append(cov([rows[i][2] for i in stab_idx], [rows[i][0] for i in stab_idx]))
                allm += [r[1] for r in rows]
            ys, ps = tasks['reversal']
            rows = run(pol, ys)
            d['rev_mse'].append(mse(rows, ps, rev_idx))
            allm += [r[1] for r in rows]
            for sw, hi in ((120, False), (240, True)):
                d['rec'].append(next((k + 1 for k in range(120) if (rows[sw + k][0] > 0.5) == hi), float('inf')))
            d['m_mean'].append(st.mean(allm))
            d['sat'].append(sum(1 for m in allm if m >= 1.5) / len(allm))

    R = {'summary': {}}
    for pol in POL:
        d = per[pol]
        R['summary'][pol] = dict(
            stable_mean={p: st.mean(v) for p, v in d['stable_mean'].items()},
            stable_t_half={p: TC * st.stdev(v) / math.sqrt(NS) for p, v in d['stable_mean'].items()},
            stable_mse={p: st.mean(v) for p, v in d['stable_mse'].items()},
            stable_loss=st.mean(st.mean(v) for v in d['stable_mse'].values()),
            reversal_loss=st.mean(d['rev_mse']), m_mean=st.mean(d['m_mean']), sat_frac=st.mean(d['sat']),
            recovery_median=st.median(d['rec']), brier_stable=st.mean(d['brier']),
            cov_alpha_Y=st.mean(d['cov_aY']), cov_alpha_z=st.mean(d['cov_az']))
    F, B1 = R['summary']['feedback'], R['summary']['fixed_1']
    a1 = all(abs(F['stable_mean'][p] - p) <= 0.03 and F['stable_t_half'][p] <= 0.03 for p in (0.2, 0.5, 0.8))
    a2 = {p: F['stable_mse'][p] - B1['stable_mse'][p] for p in (0.2, 0.5, 0.8)}
    diffs = [f - b for f, b in zip(per['feedback']['rev_mse'], per['fixed_1']['rev_mse'])]
    ub = st.mean(diffs) + TC * st.stdev(diffs) / math.sqrt(NS)
    a3 = F['reversal_loss'] <= 0.9 * B1['reversal_loss'] and ub < 0
    dom = [pol for pol in ('fixed_0.5', 'fixed_1', 'fixed_1.5')
           if R['summary'][pol]['stable_loss'] <= F['stable_loss'] and R['summary'][pol]['reversal_loss'] <= F['reversal_loss']]
    crit = dict(A1=a1, A2=all(v <= 0.005 for v in a2.values()), A3=a3, A4=not dom)
    R['A2_delta'] = a2
    R['A3'] = dict(rel=F['reversal_loss'] / B1['reversal_loss'] - 1, paired_mean=st.mean(diffs), paired_t_upper=ub)
    R['A4_dominated_by'] = dom
    alt = min(('fixed_0.5', 'fixed_1.5'), key=lambda p: 0.5 * R['summary'][p]['stable_loss'] + 0.5 * R['summary'][p]['reversal_loss'])
    R['alt_fixed_for_C'] = alt
    R['criteria'] = crit
    R['verdict'] = 'CANDIDATE_JUSTIFIED' if all(crit.values()) else 'POLICY_NOT_JUSTIFIED'
    R['wall_s'] = time.time() - t0
    json.dump(R, open(os.path.join(OUT, 'A_screen.json'), 'w'), indent=1)
    with open(os.path.join(HERE, 'runs.jsonl'), 'a') as f:
        f.write(json.dumps(dict(stage='A', run_id='a_policy_screen', wall_s=R['wall_s'])) + "\n")
    for pol in POL:
        S = R['summary'][pol]
        print(f"{pol:<10} stable mean {[round(S['stable_mean'][p], 4) for p in (0.2, 0.5, 0.8)]} "
              f"half {[round(S['stable_t_half'][p], 4) for p in (0.2, 0.5, 0.8)]} "
              f"MSE {[round(S['stable_mse'][p], 5) for p in (0.2, 0.5, 0.8)]} | stable_loss {S['stable_loss']:.5f} "
              f"rev_loss {S['reversal_loss']:.5f} | m {S['m_mean']:.3f} sat {S['sat_frac']:.3f} rec {S['recovery_median']} "
              f"cov(a,Y) {S['cov_alpha_Y']:+.2e} cov(a,z) {S['cov_alpha_z']:+.2e}")
    print("A2 delta", {p: round(v, 5) for p, v in a2.items()}, "A3", {k: round(v, 5) for k, v in R['A3'].items()},
          "A4 dominated by", dom)
    print("criteria", crit, "->", R['verdict'], "| alt fixed for C:", alt, f"| wall {R['wall_s']:.1f}s")


if __name__ == '__main__':
    main()
