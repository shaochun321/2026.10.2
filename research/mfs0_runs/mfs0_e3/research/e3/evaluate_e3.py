"""MFS0-E3 evaluation (plan §11, §12, §15). Reads only saved results; writes
results/E3_evaluation.json (+ trajectory figure via plot_e3.py).

Y = 1{gate-accepted L tick in [s, s+H)}; censored if the window is not complete within the
run (never scored as 0). Main metric per stream: domains A/L — equal-weight mean over the
three histories of the per-history Brier over ALL gate-accepted W records (rejections kept)
in the three active segments; domain X — history 0 (trigger W1) only.
d^CB = B(C) − B(B), d^CR = B(C) − B(R); two-sided 95 % t interval with df = n − 1, stream =
unit. Gates (pre-registered in prereg_E3.json) are applied exactly once.
"""
import json
import math
import os
import pickle
import statistics

import e3_common as C
from relation_spec import CANDIDATES, others
from reference_solver_e3 import carriers_at, q_of, censored, H

DT = C.DT
FIELDS = ['t', 'tick', 'path', 'p_hat', 'horizon_s', 'status', 'slot', 'free_slots_before', 'relation_id',
          'condition_id', 'condition_value', 'condition_net', 'read_path', 'p_hat_marginal']
SEGS = [(0.0, 240.0, 'S1'), (240.0, 480.0, 'S2'), (600.0, 900.0, 'S4')]


def seg_of(t):
    for a, b, n in SEGS:
        if a <= t < b:
            return n
    return None


def rows_of(gs, l_ticks, n_ticks):
    out = []
    for rec in gs['records']:
        r = dict(zip(FIELDS, rec))
        r['cens'] = censored(r['tick'], n_ticks, DT)
        r['y'] = None if r['cens'] else q_of(r['tick'], l_ticks, DT)
        j = min(range(len(l_ticks)), key=lambda x: abs(l_ticks[x] - r['tick'] - H / DT)) if l_ticks else None
        r['edge'] = j is not None and abs((l_ticks[j] - r['tick']) * DT - H) <= 2 * DT
        r['seg'] = seg_of(r['t'])
        out.append(r)
    return out


def brier(rs):
    return sum((r['p_hat'] - r['y']) ** 2 for r in rs) / len(rs) if rs else None


def decomposition(ps, ys):
    n = len(ps)
    mp, my = sum(ps) / n, sum(ys) / n
    vp = sum((p - mp) ** 2 for p in ps) / n
    vy = sum((y - my) ** 2 for y in ys) / n
    cv = sum((p - mp) * (y - my) for p, y in zip(ps, ys)) / n
    return dict(brier=(mp - my) ** 2 + vp + vy - 2 * cv, mean_residual_sq=(mp - my) ** 2, var_p=vp, var_y=vy, cov_py=cv, n=n)


def reliability(ps, ys, nb=10):
    tab = []
    for b in range(nb):
        idx = [k for k, p in enumerate(ps) if b / nb <= p < (b + 1) / nb or (b == nb - 1 and p == 1.0)]
        if idx:
            tab.append(dict(bin=[b / nb, (b + 1) / nb], n=len(idx), mean_p=sum(ps[k] for k in idx) / len(idx),
                            mean_y=sum(ys[k] for k in idx) / len(idx)))
    return tab


# ── mechanism ──
def node_vs_reference(gs, rows, l_ticks):
    names = gs.get('carrier_names', [('m', i) for i in range(3)])
    routes = {}
    for i, r, sel in gs.get('route_log', []):
        routes.setdefault((i, r), []).append(sel)
    used, exps, mism = {}, [], 0
    splits = gs.get('splits', {})
    for r in rows:
        if r['status'] != 'ADMITTED':
            continue
        cs = [('m', r['path'])]
        if r['path'] in splits:
            key = (r['path'], r['slot'])
            n = used.get(key, 0)
            used[key] = n + 1
            lst = routes.get(key, [])
            sel = lst[n] if n < len(lst) else None
            if sel is None:
                sel = r['condition_value']          # settlement not reached (censored at run end)
            mism += sel != r['condition_value']
            cs.append(('c', r['path'], sel))
        exps.append((r['tick'], cs))
    q = {nm: [k for k, _ in gs['z']] for nm in names}
    zr = carriers_at(exps, l_ticks, q, DT)
    dev = max(abs(z[ci] - zr[nm][k]) for k, z in gs['z'] for ci, nm in enumerate(names))
    rd = max((abs(r['p_hat'] - zz) for r, (_, _, zz) in zip(rows, gs['eval_z'])), default=0.0)
    n_route = sum(len(v) for v in routes.values())
    n_split_adm = sum(1 for r in rows if r['status'] == 'ADMITTED' and r['path'] in splits)
    return dict(max_carrier_dev=dev, max_readout_dev=rd, route_vs_latched_mismatch=mism,
                routes=n_route, split_admissions=n_split_adm)


def _within(ticks, k, d):
    import bisect
    j = bisect.bisect_left(ticks, k) - 1
    return j >= 0 and (k - ticks[j]) * DT <= d + 1e-12


def cond_ref_slack(cand, i, k, w, l, slack):
    j, ll = others(i)
    s = dict(U=_within(w[j], k, H + slack), V=_within(w[ll], k, H + slack),
             Q=_within(l, k, H + slack), Q2=_within(l, k, 2 * H + slack))
    return 1 if CANDIDATES[cand][1](s) else 0


def condition_agreement(gs, rows, w, l):
    splits = gs.get('splits', {})
    n = dis = boundary = 0
    for r in rows:
        if r['path'] not in splits:
            continue
        c = splits[r['path']]
        ref = cond_ref_slack(c, r['path'], r['tick'], w, l, 0.0)
        n += 1
        if ref != r['condition_net']:
            dis += 1
            # boundary case: the node agrees with the reference evaluated with ≤ 2 dt more age
            if any(cond_ref_slack(c, r['path'], r['tick'], w, l, s * DT) == r['condition_net'] for s in (1, 2)):
                boundary += 1
    return dict(n=n, disagree=dis, boundary_le_2dt=boundary, unexplained=dis - boundary)


def mech_stream(d, g):
    gs = d['groups'][g]
    rows = rows_of(gs, d['l_ticks'], d['n_ticks'])
    m = node_vs_reference(gs, rows, d['l_ticks'])
    # every admitted experience whose settle window opens before run end (s + H < T_end) settles exactly once;
    # admissions later than that are counted as censored-at-end, never as settled
    late = sum(1 for r in rows if r['status'] == 'ADMITTED' and (d['n_ticks'] - r['tick']) * DT <= H + 2 * DT)
    na = sum(sum(x) for x in gs['n_accept'])
    ns = sum(sum(x) for x in gs['n_settle'])
    m['accept_eq_settle'] = ns == na - late and all(0 <= a - b <= 1 for xa, xb in zip(gs['n_accept'], gs['n_settle'])
                                                   for a, b in zip(xa, xb))
    m['unsettled_at_end'] = late
    m['objects_constant'] = gs['objects'][0] == gs['objects'][1]
    m['rejections'] = sum(len(x) for x in gs['rejected'])
    h = gs['hold']
    if len(h) == 2:
        a, b = sorted(h)
        m['hold_max_dw'] = max(abs(x - y) for x, y in zip(h[a], h[b]))
        m['hold_s'] = (b - a) * DT
    if 'splits' in gs:
        m['route_flips'] = gs['route_flips']
        m['leaf_entries_eq_admissions'] = all(sum(gs['leaf_settle_entries'][i][r]) == gs['n_settle'][i][r]
                                              for i in gs['splits'] for r in range(2))
        m['condition_vs_time_reference'] = condition_agreement(gs, rows, d['w_ticks'], d['l_ticks'])
    m['edge_records'] = sum(r['edge'] for r in rows)
    return m, rows


# ── utility ──
def per_hist_brier(rows, hists):
    out = {}
    for i in hists:
        rs = [r for r in rows if r['path'] == i and not r['cens'] and r['seg'] is not None]
        out[i] = (brier(rs), len(rs))
    return out


def domain_utility(dom, streams, pr):
    D = pr['domains'][dom]
    hists = [0] if dom == 'X' else [0, 1, 2]
    gate = pr['utility_gates']
    per = []
    for d in streams:
        st = {}
        for g in ('B', 'C', 'R'):
            rows = rows_of(d['groups'][g], d['l_ticks'], d['n_ticks'])
            pb = per_hist_brier(rows, hists)
            st[g] = dict(metric=sum(v[0] for v in pb.values()) / len(pb) if all(v[1] for v in pb.values()) else None,
                         per_hist={i: v[0] for i, v in pb.items()}, n_per_hist={i: v[1] for i, v in pb.items()}, rows=rows)
        per.append(st)
    ok_data = all(st[g]['metric'] is not None for st in per for g in st)
    res = dict(n_streams=len(per), data_complete=ok_data)
    if not ok_data:
        res['verdict'] = 'INCONCLUSIVE'
        res['reasons'] = ['DATA_INSUFFICIENT: a required history has no non-censored record in some stream']
        return res, per
    dCB = [st['C']['metric'] - st['B']['metric'] for st in per]
    dCR = [st['C']['metric'] - st['R']['metric'] for st in per]
    cb, cr = C.t_interval(dCB), C.t_interval(dCR)
    res.update(d_CB=dict(mean=cb[0], ci=[cb[1], cb[2]], per_stream=dCB), d_CR=dict(mean=cr[0], ci=[cr[1], cr[2]], per_stream=dCR),
               metric_means={g: sum(st[g]['metric'] for st in per) / len(per) for g in ('B', 'C', 'R')})
    # support
    splits = {int(k): v for k, v in D['splits'].items()}
    leaf_n = {f'{i}{k}': 0 for i in splits for k in (0, 1)}
    leaf_streams = {f'{i}{k}': 0 for i in splits for k in (0, 1)}
    for st in per:
        for i in splits:
            for k in (0, 1):
                n = sum(1 for r in st['C']['rows'] if r['path'] == i and not r['cens'] and r['seg'] and r['condition_value'] == k)
                leaf_n[f'{i}{k}'] += n
                leaf_streams[f'{i}{k}'] += n >= gate['leaf_min_per_stream']
    hist_min = min(st['C']['n_per_hist'][i] for st in per for i in hists)
    support_ok = all(v >= gate['leaf_min_total'] for v in leaf_n.values()) and \
        all(v >= math.ceil(len(per) / 2) for v in leaf_streams.values()) and hist_min >= gate['hist_min_per_stream']
    res.update(leaf_n=leaf_n, leaf_streams_ge10=leaf_streams, hist_min_per_stream=hist_min, support_ok=support_ok)
    reasons = []
    if not (cb[2] < 0):
        reasons.append('C-B interval upper bound not < 0' + (' (EFFECT_PRECISION)' if cb[0] < 0 else ' (NO_GAIN)'))
    if not (cr[2] < 0):
        reasons.append('C-R interval upper bound not < 0 (RANDOM_PARTITION_NOT_SEPARATED)')
    if not (cb[0] <= gate['practical_min_improvement']):
        reasons.append('C-B point estimate > -0.005 (GAIN_BELOW_TARGET)')
    if not support_ok:
        reasons.append('LOW_SUPPORT')
    if cb[1] > 0:
        res['verdict'] = 'FAIL'
    elif reasons:
        res['verdict'] = 'INCONCLUSIVE'
    else:
        res['verdict'] = 'PASS'
    res['reasons'] = reasons
    return res, per


def diagnostics(dom, per, streams):
    hists = [0, 1, 2]
    out = {}
    for g in ('B', 'C', 'R'):
        allr = [r for st in per for r in st[g]['rows'] if not r['cens'] and r['seg']]
        dg = {}
        for i in hists:
            ri = [r for r in allr if r['path'] == i]
            seg = {}
            for sname in ('S1', 'S2', 'S4'):
                rs = [r for r in ri if r['seg'] == sname]
                if not rs:
                    continue
                e = dict(n=len(rs), y_mean=sum(r['y'] for r in rs) / len(rs), brier=brier(rs),
                         rejected=sum(r['status'] != 'ADMITTED' for r in rs))
                if g != 'B' and rs[0]['condition_value'] is not None:
                    for k in (0, 1):
                        rk = [r for r in rs if r['condition_value'] == k]
                        e[f'leaf{k}'] = dict(n=len(rk), y_mean=(sum(r['y'] for r in rk) / len(rk)) if rk else None,
                                             p_mean=(sum(r['p_hat'] for r in rk) / len(rk)) if rk else None)
                seg[sname] = e
            dg[i] = dict(segments=seg, decomposition=decomposition([r['p_hat'] for r in ri], [r['y'] for r in ri]) if ri else None,
                         reliability=reliability([r['p_hat'] for r in ri], [r['y'] for r in ri]),
                         reliability_marginal_readout=reliability([r['p_hat_marginal'] for r in ri], [r['y'] for r in ri]))
        # reversal windows: first 30 records per history after 240 s and after 600 s; stable tails: last 30 per segment
        rev, tail, e2last = {}, {}, {}
        for i in hists:
            for name, a, b in (('after240', 240.0, 480.0), ('after600', 600.0, 900.0)):
                vals = []
                for st in per:
                    rs = [r for r in st[g]['rows'] if r['path'] == i and not r['cens'] and a <= r['t'] < b][:30]
                    if rs:
                        vals.append(brier(rs))
                rev[f'{i}_{name}'] = sum(vals) / len(vals) if vals else None
            for sname, a, b in (('S1', 0, 240), ('S2', 240, 480), ('S4', 600, 900)):
                vals = []
                for st in per:
                    rs = [r for r in st[g]['rows'] if r['path'] == i and not r['cens'] and a <= r['t'] < b][-30:]
                    if rs:
                        vals.append(brier(rs))
                tail[f'{i}_{sname}'] = sum(vals) / len(vals) if vals else None
            for name, b in (('before240', 240.0), ('before900', 900.0)):
                vals = []
                for st in per:
                    rs = [r for r in st[g]['rows'] if r['path'] == i and not r['cens'] and r['t'] < b and r['seg']][-30:]
                    if rs:
                        vals.append(brier(rs))
                e2last[f'{i}_{name}'] = sum(vals) / len(vals) if vals else None
        out[g] = dict(per_history=dg, reversal_first30=rev, stable_tail_last30=tail, E2_last30=e2last)
    # recovery after reversal (C vs B): records until |p̂ − segment ȳ| ≤ 0.1 first / for good
    rec = {}
    for g in ('B', 'C'):
        firsts, stays = [], []
        for st in per:
            for i in hists:
                for a, b in ((240.0, 480.0), (600.0, 900.0)):
                    rs = [r for r in st[g]['rows'] if r['path'] == i and not r['cens'] and a <= r['t'] < b]
                    if len(rs) < 5:
                        continue
                    if g == 'C' and rs[0]['condition_value'] is not None:
                        ybar = {k: (sum(r['y'] for r in rs if r['condition_value'] == k) /
                                    max(1, sum(1 for r in rs if r['condition_value'] == k))) for k in (0, 1)}
                        err = [abs(r['p_hat'] - ybar[r['condition_value']]) for r in rs]
                    else:
                        yb = sum(r['y'] for r in rs) / len(rs)
                        err = [abs(r['p_hat'] - yb) for r in rs]
                    f = next((n for n, e in enumerate(err) if e <= 0.1), None)
                    last_out = max((n for n, e in enumerate(err) if e > 0.1), default=-1)
                    firsts.append(f if f is not None else len(err))
                    stays.append(last_out + 1)
        rec[g] = dict(first_within_0p1_median=statistics.median(firsts) if firsts else None,
                      stays_within_0p1_median=statistics.median(stays) if stays else None)
    out['recovery'] = rec
    # write activity per leaf (C, R): settlement entries, dose, net charge
    act = {}
    for g in ('C', 'R'):
        tot = {}
        for d in streams:
            gs = d['groups'][g]
            for i, (c0, c1) in gs['leaf'].items():
                for k, c in ((0, c0), (1, c1)):
                    e = tot.setdefault(f'{i}{k}', dict(settle_entries=0, dose=0.0, net=0.0))
                    e['settle_entries'] += sum(gs['leaf_settle_entries'][i][r][k] for r in range(2))
                    e['dose'] += gs['leaf_q_up'][c] + gs['leaf_q_dn'][c]
                    e['net'] += gs['leaf_q_up'][c] - gs['leaf_q_dn'][c]
        act[g] = tot
    out['leaf_activity'] = act
    return out


def ideal_vs_node(dom, per, streams, pr):
    """Representation / estimation / device losses (domain mean, history-averaged)."""
    D = pr['domains'][dom]
    splits = {int(k): v for k, v in D['splits'].items()}
    hists = [0] if dom == 'X' else [0, 1, 2]
    res = dict(node_C=[], ref_C=[], node_B=[], ref_B=[], oracle_marg=[], oracle_cond=[])
    for st, d in zip(per, streams):
        for g, key_node, key_ref in (('B', 'node_B', 'ref_B'), ('C', 'node_C', 'ref_C')):
            rows = st[g]['rows']
            gs = d['groups'][g]
            exps = []
            for r in rows:
                if r['status'] != 'ADMITTED':
                    continue
                cs = [('m', r['path'])] + ([('c', r['path'], r['condition_value'])] if (g == 'C' and r['path'] in splits) else [])
                exps.append((r['tick'], cs))
            q = {}
            for r in rows:
                c = ('c', r['path'], r['condition_value']) if (g == 'C' and r['path'] in splits) else ('m', r['path'])
                q.setdefault(c, []).append(r['tick'])
            zr = carriers_at(exps, d['l_ticks'], {c: sorted(v) for c, v in q.items()}, DT)
            bn, br_ = [], []
            for i in hists:
                rs = [r for r in rows if r['path'] == i and not r['cens'] and r['seg']]
                bn.append(brier(rs))
                br_.append(sum((zr[('c', i, r['condition_value']) if (g == 'C' and i in splits) else ('m', i)][r['tick']] - r['y']) ** 2
                               for r in rs) / len(rs))
            res[key_node].append(sum(bn) / len(bn))
            res[key_ref].append(sum(br_) / len(br_))
        # oracle: per segment empirical rates (marginal vs conditional on the C condition value)
        rows = st['C']['rows']
        om, oc = [], []
        for i in hists:
            rs = [r for r in rows if r['path'] == i and not r['cens'] and r['seg']]
            sm = sc_ = 0.0
            for sname in ('S1', 'S2', 'S4'):
                ss = [r for r in rs if r['seg'] == sname]
                if not ss:
                    continue
                ym = sum(r['y'] for r in ss) / len(ss)
                sm += sum((ym - r['y']) ** 2 for r in ss)
                for k in (0, 1):
                    sk = [r for r in ss if (r['condition_value'] if i in splits else 0) == k]
                    if sk:
                        yk = sum(r['y'] for r in sk) / len(sk)
                        sc_ += sum((yk - r['y']) ** 2 for r in sk)
            om.append(sm / len(rs))
            oc.append(sc_ / len(rs))
        res['oracle_marg'].append(sum(om) / len(om))
        res['oracle_cond'].append(sum(oc) / len(oc))
    m = {k: sum(v) / len(v) for k, v in res.items()}
    m['representation_gain_oracle'] = m['oracle_marg'] - m['oracle_cond']
    m['estimation_loss_C_ref_minus_oracle'] = m['ref_C'] - m['oracle_cond']
    m['device_loss_C_node_minus_ref'] = m['node_C'] - m['ref_C']
    m['device_loss_B_node_minus_ref'] = m['node_B'] - m['ref_B']
    return m


def load_domain(dom):
    d = os.path.join(C.RES, 'formal', dom)
    fs = sorted(f for f in os.listdir(d) if f.startswith('stream_')) if os.path.isdir(d) else []
    return [pickle.load(open(os.path.join(d, f), 'rb')) for f in fs]


def main():
    pp = os.environ.get('E3_PREREG', os.path.join(C.HERE, 'prereg_E3.json'))
    pr = json.load(open(pp, encoding='utf-8'))
    E = dict(prereg_sha16=C.sha16(pp))
    mech_ok = True
    complete = True
    for dom in ('A', 'X', 'L'):
        streams = load_domain(dom)
        if len(streams) != pr['domains'][dom]['streams']:
            complete = False
            E[dom] = dict(missing=True, found=len(streams))
            continue
        mech = {g: [mech_stream(d, g)[0] for d in streams] for g in ('B', 'C', 'R')}
        agg = {}
        for g, ms in mech.items():
            a = dict(max_carrier_dev=max(m['max_carrier_dev'] for m in ms), max_readout_dev=max(m['max_readout_dev'] for m in ms),
                     accept_eq_settle=all(m['accept_eq_settle'] for m in ms), objects_constant=all(m['objects_constant'] for m in ms),
                     rejections=sum(m['rejections'] for m in ms), edge_records=sum(m['edge_records'] for m in ms),
                     route_vs_latched_mismatch=sum(m['route_vs_latched_mismatch'] for m in ms),
                     hold_max_dw=max((m.get('hold_max_dw', 0.0) for m in ms)), hold_s=ms[0].get('hold_s'))
            if g != 'B':
                a.update(route_flips=sum(m['route_flips'] for m in ms),
                         leaf_entries_eq_admissions=all(m['leaf_entries_eq_admissions'] for m in ms),
                         condition_vs_time_reference={k: sum(m['condition_vs_time_reference'][k] for m in ms)
                                                      for k in ('n', 'disagree', 'boundary_le_2dt', 'unexplained')})
            agg[g] = a
        ok = all(a['max_carrier_dev'] <= 0.03 and a['max_readout_dev'] <= 0.01 and a['accept_eq_settle'] and
                 a['objects_constant'] and a['rejections'] == 0 and a['route_vs_latched_mismatch'] == 0 and
                 a['hold_max_dw'] <= 1e-6 for a in agg.values()) and \
            all(agg[g]['route_flips'] == 0 and agg[g]['leaf_entries_eq_admissions'] and
                agg[g]['condition_vs_time_reference']['unexplained'] == 0 for g in ('C', 'R'))
        mech_ok &= ok
        util, per = domain_utility(dom, streams, pr)
        E[dom] = dict(mechanism=agg, mechanism_ok=ok, utility=util, diagnostics=diagnostics(dom, per, streams),
                      ideal_vs_node=ideal_vs_node(dom, per, streams, pr),
                      source=[d['source'].get('conflicts') for d in streams],
                      gate_entries=[[len(x) for x in d['w_ticks']] + [len(d['l_ticks'])] for d in streams],
                      cost_s=[d['cost_s'] for d in streams])
        if dom == 'X':
            trig = []
            for d in streams:
                rs = [r for r in rows_of(d['groups']['C'], d['l_ticks'], d['n_ticks']) if r['path'] == 0]
                ticks = [r['tick'] for r in rs]
                import bisect
                m = n = 0
                for tr in d['source']['triggers']:
                    j = bisect.bisect_left(ticks, int(tr['t'] / DT))
                    if j < len(rs) and abs(rs[j]['tick'] * DT - tr['t']) < 0.05:
                        n += 1
                        m += rs[j]['condition_net'] == int(tr['xor'])
                trig.append((n, m, len(d['source']['triggers'])))
            E['X']['input_check_cond_eq_source_xor'] = dict(matched=sum(x[1] for x in trig), found=sum(x[0] for x in trig),
                                                            triggers=sum(x[2] for x in trig))
        if dom == 'L':
            f = streams[0].get('fork')
            if f:
                first_div = min([t for i in range(3) for t in set(f['fork_w_ticks'][i]) ^ set(streams[0]['w_ticks'][i])] +
                                [t for t in set(f['fork_l_ticks']) ^ set(streams[0]['l_ticks'])], default=None)
                same_until = {g: [r for r in f['fork_groups'][g]['records'] if r[1] < first_div] ==
                              [r for r in streams[0]['groups'][g]['records'] if r[1] < first_div] for g in f['fork_groups']}
                E['L']['fork'] = dict(fork_tick=f['fork_tick'], first_divergent_input_tick=first_div,
                                      records_identical_until_first_divergent_input=same_until,
                                      same_suffix_records_identical=f['same_suffix_records_identical'],
                                      same_suffix_z_identical=f['same_suffix_z_identical'],
                                      fork_records_after=len([r for r in f['fork_groups']['C']['records'] if r[1] >= f['fork_tick']]),
                                      cost_s=f['cost_s'])
            E['L']['spikes'] = [d['spikes'] for d in streams]
    # S
    S = load_domain('S')
    sp = os.path.join(C.RES, 'formal', 'S')
    S = [pickle.load(open(os.path.join(sp, f), 'rb')) for f in sorted(os.listdir(sp)) if f.startswith('stress_')] if os.path.isdir(sp) else []
    flips = json.load(open(os.path.join(sp, 'flip_suite.json'))) if os.path.exists(os.path.join(sp, 'flip_suite.json')) else None
    if len(S) == pr['domains']['S']['streams'] and flips:
        res = []
        for d in S:
            m, rows = mech_stream(d, 'C')
            o0, o1 = d['source']['overload']
            rej = [k for i in range(3) for k in d['groups']['C']['rejected'][i]]
            res.append(dict(mech={k: v for k, v in m.items()},
                            rejected=len(rej), rejected_outside_overload=sum(1 for k in rej if not (o0 / DT <= k < o1 / DT + 3200)),
                            admitted_after_overload=sum(1 for r in rows if r['tick'] > o1 / DT + 3200 and r['status'] == 'ADMITTED')))
        cap_ok = all(r['rejected'] > 0 and r['rejected_outside_overload'] == 0 and r['admitted_after_overload'] > 0 and
                     r['mech']['accept_eq_settle'] and r['mech']['objects_constant'] and r['mech']['hold_max_dw'] <= 1e-6 and
                     r['mech']['route_vs_latched_mismatch'] == 0 and r['mech']['route_flips'] == 0 for r in res) and \
            all(v['ok'] for k, v in flips.items() if isinstance(v, dict) and 'ok' in v)
        E['S'] = dict(streams=res, flip_suite=flips, capacity_ok=cap_ok)
    else:
        complete = False
        E['S'] = dict(missing=True)
    rp = os.path.join(C.RES, 'formal', 'repro', 'repro.json')
    E['repro'] = json.load(open(rp)) if os.path.exists(rp) else None
    dev = json.load(open(os.path.join(C.HERE, 'results', 'dev', 'dev_checks_e3.json')))
    E['dev_checks'] = {k: dev[k] for k in ('nosplit_bit_identical_E2', 'relabel_reverse_max', 'relabel_reverse_pred_max',
                                           'consumer_on_off_identical', 'trace_boundary', 'leaf_window', 'K_hold')}
    dev_ok = dev['nosplit_bit_identical_E2'] and dev['relabel_reverse_max'] <= 1e-10 and dev['consumer_on_off_identical'] \
        and dev['trace_boundary']['ok'] and dev['leaf_window']['ok']
    repro_ok = E['repro'] is not None and all(v['records'] and v['final_w'] for dom in E['repro'].values() for v in dom.values())
    E['budget_used_s'] = C.budget_used_s()
    # verdicts
    V = {}
    V['MECHANISM'] = 'PASS' if (mech_ok and dev_ok and repro_ok and complete) else ('FAIL' if complete else 'INCOMPLETE')
    lay = os.path.join(C.HERE, 'results', 'layout')
    V['STRUCTURE_AND_RESOURCES'] = 'DELIVERED' if all(os.path.exists(os.path.join(lay, f)) for f in ('relation_graph.json', 'resource_layout.json')) else 'INCOMPLETE'
    V['ORIGINAL_DOMAIN_UTILITY'] = E['A']['utility']['verdict'] if 'utility' in E.get('A', {}) else 'INCOMPLETE'
    V['JOINT_RELATION_CAPABILITY'] = E['X']['utility']['verdict'] if 'utility' in E.get('X', {}) else 'INCOMPLETE'
    if 'fork' in E.get('L', {}):
        f = E['L']['fork']
        live_ok = all(f['records_identical_until_first_divergent_input'].values()) and \
            all(f['same_suffix_records_identical'].values()) and all(f['same_suffix_z_identical'].values())
        V['LIVE_INPUT_INTEGRATION'] = 'PASS' if live_ok else 'FAIL'
    else:
        V['LIVE_INPUT_INTEGRATION'] = 'INCOMPLETE'
    V['LIVE_PREDICTIVE_UTILITY'] = E['L']['utility']['verdict'] if 'utility' in E.get('L', {}) else 'INCOMPLETE'
    V['CAPACITY_AND_RECOVERY'] = ('PASS' if E['S'].get('capacity_ok') else 'FAIL') if 'capacity_ok' in E['S'] else 'INCOMPLETE'
    hard_fail = V['MECHANISM'] == 'FAIL' or V['LIVE_INPUT_INTEGRATION'] == 'FAIL'
    if hard_fail:
        V['E3'] = 'E3_FAIL'
    elif 'INCOMPLETE' in V.values():
        V['E3'] = 'E3_INCOMPLETE'
    elif all(V[k] == 'PASS' for k in ('ORIGINAL_DOMAIN_UTILITY', 'JOINT_RELATION_CAPABILITY', 'LIVE_PREDICTIVE_UTILITY',
                                      'CAPACITY_AND_RECOVERY')):
        V['E3'] = 'E3_PASS'
    else:
        V['E3'] = 'E3_PARTIAL'
    E['verdicts'] = V
    json.dump(E, open(os.path.join(C.RES, 'E3_evaluation.json'), 'w'), indent=1, default=str)
    try:
        import plot_e3
        plot_e3.main()
    except Exception as e:          # figure failure must not hide the evaluation
        print('figure failed:', e)
    print(json.dumps(V, indent=1))
    for dom in ('A', 'X', 'L'):
        if 'utility' in E.get(dom, {}):
            u = E[dom]['utility']
            print(dom, u['verdict'], 'CB', u.get('d_CB', {}).get('mean'), u.get('d_CB', {}).get('ci'),
                  'CR', u.get('d_CR', {}).get('mean'), u.get('d_CR', {}).get('ci'), u.get('reasons'))


if __name__ == '__main__':
    main()
