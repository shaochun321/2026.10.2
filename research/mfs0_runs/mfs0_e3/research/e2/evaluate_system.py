"""MFS0-E2 evaluation over saved results (prereg_E2.json criteria). Writes results/E2_evaluation.json + figure."""
import glob
import inspect
import json
import math
import os
import pickle
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, 'results')
PR = json.load(open(os.path.join(HERE, 'prereg_E2.json'), encoding='utf-8'))
TC = PR['t_crit_df23_0975']
DT = 0.001
H = PR['structure']['window_H_s']


def tci(xs):
    m = st.mean(xs)
    h = TC * st.stdev(xs) / math.sqrt(len(xs))
    return m, m - h, m + h, h


def by_hist(rows, i):
    return [r for r in rows if r[1] == i]


def last_before(rows, t_end, n=30):
    sel = [r for r in rows if r[0] * DT < t_end]
    return sel[-n:]


def first_after(rows, t0, n=30):
    return [r for r in rows if r[0] * DT >= t0][:n]


def brier(rs):
    return st.mean((r[2] - r[3]) ** 2 for r in rs)


def main():
    S = [pickle.load(open(f, 'rb')) for f in sorted(glob.glob(os.path.join(RES, 'formal', 'stream_*.pkl')))]
    E = dict(n_streams=len(S))
    segs = PR['main']['segments']
    active = [(a, b) for a, b, p in segs if p != 'silence']
    # ── counts / overlap / edges ──
    counts = {f"S{j + 1}": [min(sum(1 for r in by_hist(s['full']['rows'], i) if a <= r[0] * DT < b) for s in S)
                            for i in range(3)] for j, (a, b, p) in enumerate(segs) if p != 'silence'}
    ov = []
    for s in S:
        adm = sorted((r[0], r[1]) for r in s['full']['rows'] if r[4] == 'ADMITTED')
        n_ov = 0
        for k, (t, i) in enumerate(adm):
            if any(j != i and abs(t - u) * DT < H for u, j in adm[max(0, k - 20):k + 20]):
                n_ov += 1
        ov.append(n_ov / len(adm))
    E['counts_min_per_history'] = counts
    E['overlap_fraction'] = dict(min=min(ov), mean=st.mean(ov))
    E['edge_cases'] = sum(sum(1 for r in s['full']['rows'] if r[5]) for s in S)
    E['gen_conflicts_mean'] = st.mean(s['gen_conflicts'] for s in S)
    E['three_denominators'] = dict(source_W=sum(sum(s['n_source_w']) for s in S),
                                   gate_accepted_W=sum(sum(s['full']['n_gate_w']) for s in S),
                                   slot_admitted_W=sum(sum(1 for r in s['full']['rows'] if r[4] == 'ADMITTED') for s in S),
                                   source_L=sum(s['n_source_l'] for s in S),
                                   gate_accepted_L=sum(len(s['full']['l_ticks']) for s in S))
    # ── U: Brier paired ──
    U = {}
    brier_ok, brier_fail = True, False
    for wname, t_end in (('stable_S1', 240.0), ('recovery_S4', 900.0)):
        for i in range(3):
            for ctl in ('no_write', 'shared'):
                d = [brier(last_before(by_hist(s['full']['rows'], i), t_end)) -
                     brier(last_before(by_hist(s[ctl]['rows'], i), t_end)) for s in S]
                m, lo, hi, h = tci(d)
                U[f"{wname}_H{i + 1}_vs_{ctl}"] = dict(mean=m, lo=lo, hi=hi)
                brier_ok &= hi < 0
                brier_fail |= lo > 0
    cal = {}
    cal_ok, cal_fail = True, False
    for j, (a, b) in enumerate(active):
        for i in range(3):
            v = [st.mean(r[2] - r[3] for r in last_before(by_hist(s['full']['rows'], i), b)) for s in S]
            m, lo, hi, h = tci(v)
            nm = ['S1', 'S2', 'S4'][j]
            cal[f"{nm}_H{i + 1}"] = dict(mean=m, t_half=h)
            cal_ok &= abs(m) <= 0.05 and h <= 0.04
            cal_fail |= abs(m) > 0.05
    rep = {}
    for t0 in (240.0, 600.0):
        for i in range(3):
            rep[f"after_{int(t0)}_H{i + 1}"] = {c: st.mean(brier(first_after(by_hist(s[c]['rows'], i), t0)) for s in S)
                                                for c in ('full', 'no_write', 'shared')}
    rec = {}
    for i in (0, 1):
        ns = []
        for s in S:
            rows = by_hist(s['full']['rows'], i)
            post = [r for r in rows if 240.0 <= r[0] * DT < 480.0]
            yr = st.mean(r[3] for r in post)
            ns.append(next((k + 1 for k, r in enumerate(post) if abs(r[2] - yr) <= 0.1), float('inf')))
        rec[f"H{i + 1}_S2"] = dict(median=st.median(ns), never=sum(n == float('inf') for n in ns))
    E['U'] = dict(brier_paired=U, calibration=cal, reversal_window_brier=rep, recovery_experiences=rec)
    # ── M ──
    M = {}
    M['accept_eq_settle'] = all(s[c]['n_accept'] == s[c]['n_settle'] for s in S for c in ('full', 'no_write', 'shared'))
    M['max_dev_ref_full'] = max(s['full']['max_dev_ref'] for s in S)
    M['max_dev_ref_shared'] = max(s['shared']['max_dev_ref'] for s in S)
    M['max_readout_dev'] = max(s[c]['max_readout_dev'] for s in S for c in ('full', 'shared'))
    hk = PR['main']['hold_ticks']
    M['hold_main_max_dw'] = max(abs(a - b) for s in S for c in ('full', 'shared')
                                for a, b in zip(s[c]['hold'][hk[0]], s[c]['hold'][hk[1]]))
    M['objects_constant'] = all(s[c]['objects'][0] == s[c]['objects'][1] for s in S for c in ('full', 'no_write', 'shared'))
    from memory_core import MemoryCore
    sig = list(inspect.signature(MemoryCore.step).parameters)
    M['core_step_signature'] = sig
    M['no_label_input'] = sig == ['self', 'b_W', 'b_L', 'dt']
    dev = json.load(open(os.path.join(RES, 'dev', 'dev_checks.json')))
    M['dev_window_ok'] = dev['window']['ok']
    M['dev_relabel'] = dev['relabel_invariance_max']
    M['dev_equivalence_e11'] = dev['equivalence_e11']['max_diff']
    C = {'main_rejections': sum(sum(s['full']['rejected']) for s in S)}
    ST = [pickle.load(open(f, 'rb')) for f in sorted(glob.glob(os.path.join(RES, 'stress', 'stress_*.pkl')))]
    hs = PR['stress']['hold_ticks']
    C['stress'] = [dict(n_inj_w=x['n_inj_w'], n_gate_w=x['n_gate_w'], n_admitted=x['n_admitted'],
                        n_rejected=x['n_rejected'], rejected_outside_overload=x['rejected_outside_overload'],
                        accept_eq_settle=x['n_accept'] == x['n_settle'], objects=x['objects'],
                        hold_max_dw=max(abs(a - b) for a, b in zip(x['hold'][hs[0]], x['hold'][hs[1]])),
                        max_dev_ref=x['max_dev_ref'], records_after_overload=x['records_after_overload']) for x in ST]
    LV = pickle.load(open(os.path.join(RES, 'live', 'live.pkl'), 'rb'))
    A, B = LV['A'], LV['B']
    fk = int(PR['live']['fork_at_s'] / DT)
    L = dict(rows_A=len(A['rows']), rows_B=len(B['rows']), spikes=A['spikes'],
             entries_A=[len(x) for x in A['w_ticks']] + [len(A['l_ticks'])],
             prefix_rows_identical=[r for r in A['rows'] if r[0] < fk] == [r for r in B['rows'] if r[0] < fk],
             prefix_z_identical=[z for z in A['z_log'] if z[0] < fk] == [z for z in B['z_log'] if z[0] < fk],
             diverged_after=[r for r in A['rows'] if r[0] >= fk] != [r for r in B['rows'] if r[0] >= fk] or
                            [z for z in A['z_log'] if z[0] >= fk] != [z for z in B['z_log'] if z[0] >= fk],
             T_s=PR['live']['T_s'], objects=A['objects'],
             p_hat_last_half={i: [r[2] for r in A['rows'] if r[1] == i and r[0] >= fk] for i in (0, 1)})
    E['M'], E['C'], E['LIVE'] = M, C, L
    mech = (M['accept_eq_settle'] and M['max_dev_ref_full'] <= 0.03 and M['max_dev_ref_shared'] <= 0.03 and
            M['max_readout_dev'] <= 0.01 and M['hold_main_max_dw'] <= 1e-6 and M['objects_constant'] and
            M['no_label_input'] and M['dev_window_ok'] and M['dev_relabel'] <= 1e-10 and
            all(x['hold_max_dw'] <= 1e-6 for x in C['stress']) and L['prefix_rows_identical'] and L['prefix_z_identical'])
    counts_ok = all(min(v) >= 30 for v in counts.values()) and E['overlap_fraction']['min'] >= 0.10
    util = 'PASS' if (brier_ok and cal_ok and counts_ok) else ('FAIL' if (brier_fail or cal_fail) else 'INCONCLUSIVE')
    cap = (C['main_rejections'] == 0 and all(x['accept_eq_settle'] and x['objects'][0] == x['objects'][1] and
                                                 x['rejected_outside_overload'] == 0 and x['records_after_overload'] > 0 and
                                                 sum(x['n_rejected']) > 0 for x in C['stress']))
    live_ok = L['prefix_rows_identical'] and L['prefix_z_identical'] and L['diverged_after']
    live_evidence = 'PREDICTIVE_EVIDENCE_INSUFFICIENT' if min(L['entries_A'][:2]) < 30 else 'EVIDENCE_REPORTED'
    V = dict(MECHANISM='PASS' if mech else 'FAIL', PREDICTIVE_UTILITY=util,
             REPLAY_INTEGRATION='PASS' if len(S) == PR['main']['streams'] else 'FAIL',
             LIVE_INPUT_INTEGRATION=('PASS' if live_ok else 'FAIL') + ' / LIVE_INPUT_CONNECTED / ' + live_evidence,
             CAPACITY_AND_RECOVERY='PASS' if cap else 'FAIL')
    V['E2'] = 'E2_PASS' if all(v.startswith('PASS') for v in V.values()) else 'E2_PARTIAL'
    E['verdicts'] = V
    json.dump(E, open(os.path.join(RES, 'E2_evaluation.json'), 'w'), indent=1, default=str)
    _figure(S[0])
    print(json.dumps(E, indent=1, default=str)[:12000])


def _figure(s0):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    tr = s0['trace']
    ks = [x[0] * DT for x in tr]
    fig, ax = plt.subplots(5, 1, figsize=(15, 13), sharex=False)
    lo, hi = 100.0, 160.0
    sel = [j for j, t in enumerate(ks) if lo <= t < hi]
    tt = [ks[j] for j in sel]
    for i in range(3):
        for r in range(2):
            ax[0].plot(tt, [tr[j][2][i][r][0] for j in sel], lw=0.8, label=f"T H{i + 1}s{r}")
            ax[1].plot(tt, [tr[j][2][i][r][1] for j in sel], lw=0.8, label=f"O H{i + 1}s{r}")
    ax[0].axhline(1.0, ls=':', c='k'); ax[0].axhline(0.3, ls=':', c='k')
    ax[0].set_ylabel('slot T [V]'); ax[1].set_ylabel('slot O [V]')
    ax[0].legend(ncol=6, fontsize=7); ax[1].legend(ncol=6, fontsize=7)
    rows = s0['full']['rows']
    for i, col in enumerate(('C0', 'C1', 'C2')):
        rr = [r for r in rows if r[1] == i and lo <= r[0] * DT < hi]
        ax[2].vlines([r[0] * DT for r in rr], i, i + 0.8, colors=col)
    ax[2].vlines([k * DT for k in s0['full']['l_ticks'] if lo <= k * DT < hi], 3, 3.8, colors='k')
    ax[2].set_yticks([0.4, 1.4, 2.4, 3.4]); ax[2].set_yticklabels(['W1 entry', 'W2 entry', 'W3 entry', 'L entry'])
    ax[2].set_xlim(lo, hi); ax[0].set_xlim(lo, hi); ax[1].set_xlim(lo, hi)
    zl = s0['z_log0']
    for c, col in enumerate(('C0', 'C1', 'C2')):
        ax[3].plot([k * DT for k, _ in zl], [z[c] for _, z in zl], c=col, lw=1, label=f"carrier z H{c + 1}")
        rr = [r for r in rows if r[1] == c]
        ax[3].scatter([r[0] * DT for r in rr], [r[2] for r in rr], s=4, c=col)
        ax[4].scatter([r[0] * DT for r in rr], [r[3] + 0.05 * c for r in rr], s=3, c=col)
    for t in (240, 480, 600):
        ax[3].axvline(t, c='gray', ls='--'); ax[4].axvline(t, c='gray', ls='--')
    rej = [r for r in rows if r[4] != 'ADMITTED']
    ax[4].scatter([r[0] * DT for r in rej], [1.3] * len(rej), marker='x', c='r', label='CAPACITY_REJECTED')
    ax[3].set_ylabel('z (line) / p̂ (dots)'); ax[4].set_ylabel('Y (actual)')
    ax[3].legend(fontsize=8); ax[4].set_xlabel('physical time [s]')
    ax[0].set_title('MFS0-E2 stream 0 (formal): slots, entries, carriers, predictions, outcomes on one time axis')
    fig.tight_layout()
    fig.savefig(os.path.join(RES, 'E2_stream0_trajectory.png'), dpi=110)


if __name__ == '__main__':
    main()
