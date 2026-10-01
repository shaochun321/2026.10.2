"""Stage C — short-horizon mapping (plan v4 §5.3, §6 list). Writes results/mapping.json."""
import json
import os
import time

from e1_common import RESULTS, DT, log_run
from sim import Rig, run_cycles, PERIOD
from device import Params

t_start = time.time()
R = {}


def one(z0, y, dL=0.45, dt=DT, **kw):
    rig = Rig(w0=1.0 - z0, label=f"c_{z0}_{y}_{dL}_{dt}")
    for k, v in kw.items():
        setattr(rig.dev, k, v)
    o = run_cycles(rig, [dict(hist=0, y=y, dL=dL)], dt=dt)[0]
    return o, rig


# 1. multi-initial-state identification
Z0 = [0.02, 0.1, 0.3, 0.5, 0.7, 0.9, 0.98]
cases = [(1, 0.10), (1, 0.45), (1, 0.80), (0, 0.45)]
ident = {}
for y, dL in cases:
    F = {}
    for z0 in Z0:
        o, _ = one(z0, y, dL)
        F[z0] = o['z_after'][0]
        assert o['n_bw'] == [1] and o['n_bl'] == y, (o['n_bw'], o['n_bl'])
    z1, z2 = 0.1, 0.9
    h = (F[z2] - F[z1]) / (z2 - z1)
    alpha = 1 - h
    q = (F[z1] - h * z1) / (1 - h)
    resid = {z: F[z] - ((1 - alpha) * z + alpha * q) for z in Z0}
    # local (per-z) effective rate towards the ideal target y
    a_loc = {z: (F[z] - z) / (y - z) for z in Z0 if abs(y - z) > 1e-9}
    ident[f"y{y}_dL{dL}"] = dict(F=F, alpha=alpha, q=q, h=h,
                                 max_abs_resid=max(abs(v) for v in resid.values()),
                                 resid=resid, alpha_local=a_loc)
    print(f"[ident y={y} dL={dL}] alpha={alpha:.5f} q={q:.5f}  max|affine resid|={max(abs(v) for v in resid.values()):.2e}"
          f"  local alpha range [{min(a_loc.values()):.5f}, {max(a_loc.values()):.5f}]")
R['identification'] = ident

# error budget (plan §4.3)
a0 = Params().alpha0
alphas = [v['alpha'] for v in ident.values()]
alpha_min = min(alphas)
eps_alpha = max(abs(a - a0) for a in alphas)
delta_q = max(abs(v['q'] - (1 if k.startswith('y1') else 0)) for k, v in ident.items())
eps_step = max(v['max_abs_resid'] for v in ident.values())
bound = delta_q + (eps_alpha + eps_step) / alpha_min
R['error_budget'] = dict(alpha0=a0, alpha_min=alpha_min, eps_alpha=eps_alpha, delta_q=delta_q,
                         eps_step=eps_step, eps_alpha_over_amin=eps_alpha / alpha_min,
                         eps_step_over_amin=eps_step / alpha_min, bound_same_init=bound,
                         target=0.05, pass_=bound <= 0.05)
print(f"[budget] alpha_min={alpha_min:.5f} eps_alpha={eps_alpha:.2e} ({eps_alpha/alpha_min:.4f}) "
      f"delta_q={delta_q:.2e} eps_step={eps_step:.2e} ({eps_step/alpha_min:.4f}) -> bound {bound:.4f} (target 0.05)")

# readout mapping error (actual output vs z)
rd = []
for z0 in Z0:
    o, _ = one(z0, 0, 0.45)
    rd.append((z0, o['pred'], o['pred'] - z0))
R['readout'] = dict(points=rd, max_abs_err=max(abs(e) for _, _, e in rd))
print(f"[readout] max|pred - z| = {R['readout']['max_abs_err']:.4f}  " +
      "  ".join(f"{z}:{p:.4f}" for z, p, _ in rd))

# 2. dt robustness (representative cases)
dtr = {}
for y in (1, 0):
    vals = []
    for div in (1, 2, 4):
        o, _ = one(0.5, y, 0.45, dt=DT / div)
        vals.append(o['z_after'][0])
    dtr[f"y{y}"] = dict(z_after=vals, max_diff=max(abs(v - vals[0]) for v in vals))
    print(f"[dt] y={y}: z_after dt,dt/2,dt/4 = {[round(v, 7) for v in vals]}  max diff {dtr[f'y{y}']['max_diff']:.2e}")
R['dt_robustness'] = dtr

# 3. sequences at the minimum allowed interval (fixed period) + tail isolation
seq = {}
for name, ys, dls in (("yes_yes_yes_no", [1, 1, 1, 0], [0.80, 0.80, 0.80, 0.10]),
                      ("no_no", [0, 0], [0.45, 0.45])):
    rig = Rig(w0=0.5, label=f"seq_{name}")
    outs = run_cycles(rig, [dict(hist=0, y=y, dL=d) for y, d in zip(ys, dls)])
    rows = []
    for o in outs:
        z0 = o['z_before'][0]
        single, _ = one(z0, o['y'], o['dL'])
        rows.append(dict(y=o['y'], z_before=z0, z_after=o['z_after'][0],
                         single_cycle_z_after=single['z_after'][0],
                         diff_vs_single=o['z_after'][0] - single['z_after'][0],
                         O_end=o['O_end'], T_end=o['T_end'][0], n_bw=o['n_bw'], n_bl=o['n_bl']))
    seq[name] = rows
    print(f"[seq {name}] max|Δ vs isolated single cycle| = {max(abs(r['diff_vs_single']) for r in rows):.2e}; "
          f"O_end {[f'{r['O_end']:.1e}' for r in rows]}; entries W {[r['n_bw'] for r in rows]} L {[r['n_bl'] for r in rows]}")
R['sequences'] = seq

# 4. prefix consistency
a = Rig(w0=0.5, label='pfx_a'); b = Rig(w0=0.5, label='pfx_b')
pre = [dict(hist=0, y=1, dL=0.3), dict(hist=0, y=0, dL=0.5), dict(hist=0, y=1, dL=0.7)]
oa = run_cycles(a, pre + [dict(hist=0, y=1, dL=0.4)])
ob = run_cycles(b, pre + [dict(hist=0, y=0, dL=0.4)])
same = all(oa[i]['z_after'] == ob[i]['z_after'] and oa[i]['pred'] == ob[i]['pred'] for i in range(3))
R['prefix_consistency'] = dict(bitwise_equal_prefix=same, diverge_after=[oa[3]['z_after'][0], ob[3]['z_after'][0]])
print(f"[prefix] first 3 cycles bitwise equal: {same}; 4th differs: {oa[3]['z_after'][0]:.5f} vs {ob[3]['z_after'][0]:.5f}")

# 5. interventions
iv = {}
for y in (1, 0):
    o, _ = one(0.5, y, 0.45, write_enabled=False)
    iv[f"write_rail_open_y{y}"] = o['z_after'][0] - 0.5
    rig = Rig(w0=0.5, label=f'noW{y}')
    o = run_cycles(rig, [dict(hist=0, y=y, dL=0.45, w_on=False)])[0]
    iv[f"zero_eligibility_y{y}"] = o['z_after'][0] - 0.5
o, _ = one(0.5, 1, 1.20)           # later arrives after the observation window closed
iv["later_after_window_dL1.20"] = o['z_after'][0] - 0.5
o, _ = one(0.5, 1, 1.00)           # at the window edge
iv["later_at_window_edge_dL1.00"] = o['z_after'][0] - 0.5
o, _ = one(0.5, 0, 0.45, down_branch=False)
iv["down_branch_removed_y0"] = o['z_after'][0] - 0.5


class CutD(Params):
    pass


rig = Rig(w0=0.5, label='cutD')
dev = rig.dev
orig_step = dev.step
state = {'k': 0}


def cut_step(b_W, b_L, dt):
    state['k'] += 1
    if state['k'] * dt >= 0.40:
        dev.p.V_D = 0.0              # logic rail disconnected after W entry, before settle
    return orig_step(b_W, b_L, dt)


dev.step = cut_step
o = run_cycles(rig, [dict(hist=0, y=1, dL=0.20)])[0]
iv["V_D_cut_at_0.40s_y1"] = o['z_after'][0] - 0.5
R['interventions'] = iv
for k, v in iv.items():
    print(f"[intervention] {k}: Δz = {v:+.5f}")

# 6. read does not disturb the carrier
rig = Rig(w0=0.37, label='rd')
rig.dev.write_enabled = False
outs = run_cycles(rig, [dict(hist=0, y=1, dL=0.4), dict(hist=0, y=0, dL=0.4)] * 3)
R['read_disturb'] = dict(w_constant=all(o['z_after'][0] == 1 - 0.37 or abs(o['z_after'][0] - 0.63) < 1e-15 for o in outs),
                         preds=[o['pred'] for o in outs])
print(f"[read] carrier unchanged over 6 read cycles with writes off: {R['read_disturb']['w_constant']}; "
      f"preds {sorted(set(round(p, 12) for p in R['read_disturb']['preds']))}")

# 7. two-history selectivity (hist 1 never presented)
rig = Rig(n_hist=2, w0=[0.5, 0.5], label='sel')
outs = run_cycles(rig, [dict(hist=0, y=y, dL=0.4) for y in (1, 1, 0, 1, 0, 0)] +
                  [dict(hist=1, y=1, dL=0.4), dict(hist=1, y=0, dL=0.4)])
cross = [abs(o['z_after'][1 - o['hist']] - o['z_before'][1 - o['hist']]) for o in outs]
own = [abs(o['z_after'][o['hist']] - o['z_before'][o['hist']]) for o in outs]
single_ref, _ = one(0.5, 1, 0.4)
R['selectivity'] = dict(max_cross_write=max(cross), min_own_write=min(own),
                        first_hist1_cycle_vs_1hist_device=outs[6]['z_after'][1] - single_ref['z_after'][0])
print(f"[selectivity] max |Δz_other| = {max(cross):.2e}; min |Δz_own| = {min(own):.4f}; "
      f"hist1 first cycle vs 1-hist device: {R['selectivity']['first_hist1_cycle_vs_1hist_device']:+.2e}")

wall = time.time() - t_start
R['wall_s'] = wall
os.makedirs(RESULTS, exist_ok=True)
json.dump(R, open(os.path.join(RESULTS, 'mapping.json'), 'w'), indent=1, default=str)
log_run(stage='C', run_id='c_mapping', wall_s=wall, note='identification/dt/sequences/prefix/interventions/read/selectivity')
print(f"wall {wall:.1f}s")
