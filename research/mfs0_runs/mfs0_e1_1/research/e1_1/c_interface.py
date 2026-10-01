"""E1.1 C — independent write-dose interface: checks C1–C3, mapping C4–C9, switching C10."""
import json
import os
import random
import time

from e1_common import RESULTS, log_run
from sim import Rig, run_cycles
import device_mod

PR = json.load(open(os.path.join(os.path.dirname(__file__), 'preregistration_E1_1.json'), encoding='utf-8'))['C']
OUT = os.path.join(RESULTS, 'C')
os.makedirs(OUT, exist_ok=True)
t0 = time.time()
R = {}


def mod_rig(w0=0.5, n_hist=1, m=1.0, label='c'):
    rig = Rig(n_hist=n_hist, w0=w0, label=label)
    rig.dev = device_mod.PredictiveMemoryDevice(n_hist=n_hist, w0=w0)
    rig.dev.set_write_drive(m)
    return rig


SEQ8 = [dict(hist=0, y=y, dL=d) for y, d in zip([1, 1, 0, 1, 0, 0, 1, 0],
                                                  [0.3, 0.7, 0.4, 0.1, 0.8, 0.5, 0.45, 0.2])]

# C1 equivalence at m = 1
a = run_cycles(Rig(w0=0.5, label='c1v4'), SEQ8)
b = run_cycles(mod_rig(0.5, m=1.0, label='c1mod'), SEQ8)
c1 = max(max(abs(x['z_after'][0] - y['z_after'][0]), abs(x['pred'] - y['pred'])) for x, y in zip(a, b))
R['C1_max_diff_vs_v4'] = c1

# C2 readout independent of m (same state)
preds_off, preds_on = {}, {}
for m in (0.0, 0.5, 1.0, 1.5):
    r = mod_rig(1 - 0.37, m=m, label=f'c2off{m}')
    r.dev.write_enabled = False
    preds_off[m] = run_cycles(r, [dict(hist=0, y=1, dL=0.4)])[0]['pred']
    r = mod_rig(1 - 0.37, m=m, label=f'c2on{m}')
    preds_on[m] = run_cycles(r, [dict(hist=0, y=1, dL=0.4)])[0]['pred']   # read precedes the write
R['C2'] = dict(writes_off=preds_off, writes_on_first_read=preds_on,
               max_spread=max(max(preds_off.values()) - min(preds_off.values()),
                              max(preds_on.values()) - min(preds_on.values())))

# C3 m = 0 and charge scaling; C3b trap on v4 object
c3 = {}
for y in (1, 0):
    r = mod_rig(0.5, m=0.0, label=f'c3m0{y}')
    o = run_cycles(r, [dict(hist=0, y=y, dL=0.4)])[0]
    c3[f'm0_dz_y{y}'] = o['z_after'][0] - o['z_before'][0]
qs = {}
for m in (0.5, 1.0, 1.5):
    r = mod_rig(0.5, m=m, label=f'c3q{m}')
    run_cycles(r, [dict(hist=0, y=1, dL=0.4)])
    qs[m] = r.dev.h[0].q_up
c3['write_charge_up'] = qs
c3['charge_ratio_vs_m1'] = {m: qs[m] / qs[1.0] for m in qs}
rv = Rig(w0=0.5, label='c3trap')
rv.dev.rail_W.vdd = 150.0
trap = run_cycles(rv, [dict(hist=0, y=1, dL=0.4)])[0]['z_after'][0]
base = run_cycles(Rig(w0=0.5, label='c3base'), [dict(hist=0, y=1, dL=0.4)])[0]['z_after'][0]
c3['v4_rail_W_vdd_150_effect'] = trap - base
R['C3'] = c3

# C4–C9 mapping
EV = {'y0': (0, 0.45), 'y1_early': (1, 0.10), 'y1_late': (1, 0.80)}
GRID = PR['mapping']['z0']
EDGE = PR['mapping']['edge_z']
mp = {}
for m in PR['mapping']['m']:
    mp[m] = {}
    for ev, (y, dL) in EV.items():
        F = {}
        for z0 in GRID + EDGE:
            r = mod_rig(1 - z0, m=m, label=f'mp{m}{ev}{z0}')
            F[z0] = run_cycles(r, [dict(hist=0, y=y, dL=dL)])[0]['z_after'][0]
        h = (F[0.9] - F[0.1]) / 0.8
        al = 1 - h
        q = (F[0.1] - h * 0.1) / al
        res = max(abs(F[z] - ((1 - al) * z + al * q)) for z in GRID if z not in (0.1, 0.9))
        direction = all((F[z] > z) if y else (F[z] < z) for z in GRID)
        mp[m][ev] = dict(F=F, alpha=al, q=q, resid=res, direction_ok=direction)
R['mapping'] = mp

# C4 cross-write at m = 0.5, 1.5 + edges
cw = {}
for m in (0.5, 1.5):
    r = mod_rig([0.5, 0.5], n_hist=2, m=m, label=f'cw{m}')
    outs = run_cycles(r, [dict(hist=0, y=y, dL=0.4) for y in (1, 0, 1)] + [dict(hist=1, y=1, dL=0.4)])
    cw[m] = max(abs(o['z_after'][1 - o['hist']] - o['z_before'][1 - o['hist']]) for o in outs)
edge = {}
for m in PR['mapping']['m']:
    edge[m] = dict(z0_under_down=mp[m]['y0']['F'][0.0], z1_under_up=min(mp[m]['y1_early']['F'][1.0], mp[m]['y1_late']['F'][1.0]),
                   z001_down=mp[m]['y0']['F'][0.01], z099_up=mp[m]['y1_late']['F'][0.99])
R['C4'] = dict(cross_write=cw, edges=edge)


def ideal(m):
    return 1 - 0.9 ** m


crit = {}
crit['C1'] = c1 <= 1e-10
crit['C2'] = R['C2']['max_spread'] <= 1e-10
crit['C3'] = max(abs(c3['m0_dz_y1']), abs(c3['m0_dz_y0'])) <= 1e-10
crit['C4'] = (all(mp[m][ev]['direction_ok'] for m in mp for ev in EV) and all(v == 0.0 for v in cw.values())
              and all(abs(e['z0_under_down']) <= 1e-12 and abs(e['z1_under_up'] - 1) <= 1e-12 for e in edge.values()))
crit['C5'] = all(abs(mp[m][ev]['q'] - (1 if ev.startswith('y1') else 0)) <= 0.005 for m in mp for ev in EV)
crit['C6'] = all(mp[m][ev]['resid'] <= 0.001 for m in mp for ev in EV)
rel = {m: {ev: mp[m][ev]['alpha'] / ideal(m) - 1 for ev in EV} for m in mp}
mono = all(mp[0.5][ev]['alpha'] < mp[1.0][ev]['alpha'] < mp[1.5][ev]['alpha'] for ev in EV)
crit['C7'] = all(abs(v) <= 0.03 for d in rel.values() for v in d.values()) and mono
sym = {m: max(abs(mp[m][u]['alpha'] - mp[m]['y0']['alpha']) / ((mp[m][u]['alpha'] + mp[m]['y0']['alpha']) / 2)
              for u in ('y1_early', 'y1_late')) for m in mp}
crit['C8'] = all(v <= 0.02 for v in sym.values())
fp = {}
for m in mp:
    for u in ('y1_early', 'y1_late'):
        ap, qp = mp[m][u]['alpha'], mp[m][u]['q']
        an, qn = mp[m]['y0']['alpha'], mp[m]['y0']['q']
        for p in (0.2, 0.8):
            fp[f'm{m}_{u}_p{p}'] = (p * ap * qp + (1 - p) * an * qn) / (p * ap + (1 - p) * an)
crit['C9'] = all(abs(v - float(k.split('_p')[1])) <= 0.01 for k, v in fp.items())
R['C7_rel_err'] = rel
R['C7_monotone'] = mono
R['C8_asym'] = sym
R['C9_fixed_points'] = fp

# C10 switching sequence
sched = [(0.5, 1.0, 1.5)[(n // 5) % 3] for n in range(60)]
rng = random.Random(20261230)
ys = [1 if rng.random() < (0.8 if n < 30 else 0.2) else 0 for n in range(60)]
dls = [rng.uniform(0.10, 0.80) for _ in range(60)]
r = mod_rig(0.5, m=1.0, label='c10')
dev_id = id(r.dev)
zi, zmax, rows = 0.5, 0.0, []
for n in range(60):
    r.dev.set_write_drive(sched[n])                   # set between cycles, before this cycle's settle
    o = run_cycles(r, [dict(hist=0, y=ys[n], dL=dls[n])])[0]
    zi = zi + ideal(sched[n]) * (ys[n] - zi)
    zmax = max(zmax, abs(o['z_after'][0] - zi))
    rows.append(dict(n=n, m=sched[n], y=ys[n], z=o['z_after'][0], z_ideal=zi, O_end=o['O_end'],
                     n_bw=o['n_bw'], n_bl=o['n_bl']))
integ = all(x['n_bw'] == [1] and x['n_bl'] == x['y'] and x['O_end'] < 1e-3 for x in rows) and id(r.dev) == dev_id
crit['C10'] = zmax <= 0.05 and integ
R['C10'] = dict(max_dev=zmax, integrity=integ, rows=rows)

R['criteria'] = crit
only_c7 = all(v for k, v in crit.items() if k != 'C7') and not crit['C7']
R['verdict'] = ('INTERFACE_PASS' if all(crit.values()) else
                'INTERFACE_USABLE_RATE_APPROX_FAIL' if only_c7 else 'INTERFACE_FAIL')
R['wall_s'] = time.time() - t0
json.dump(R, open(os.path.join(OUT, 'C_interface.json'), 'w'), indent=1, default=str)
log_run(stage='C', run_id='c_interface_rev0', wall_s=R['wall_s'], note='formal interface checks + mapping + switching')

print(f"C1 max diff vs v4 at m=1: {c1:.2e}")
print(f"C2 pred spread across m (writes off / first read): {R['C2']['max_spread']:.2e}  preds {preds_off}")
print(f"C3 m=0 dz: {c3['m0_dz_y1']:.2e} / {c3['m0_dz_y0']:.2e}; charge ratio {c3['charge_ratio_vs_m1']}; v4 rail_W.vdd trap effect {c3['v4_rail_W_vdd_150_effect']:.2e}")
for m in mp:
    print(f"m={m}: " + " | ".join(f"{ev}: α={mp[m][ev]['alpha']:.5f} (ideal {ideal(m):.5f}, rel {rel[m][ev]:+.4f}) q={mp[m][ev]['q']:+.5f} res={mp[m][ev]['resid']:.1e}" for ev in EV)
          + f" | asym {sym[m]:.4f}")
print(f"C4 cross write {cw}; edges {edge}")
print(f"C9 fixed points " + " ".join(f"{k}={v:.4f}" for k, v in fp.items()))
print(f"C10 max |z - z_ideal| = {zmax:.4f}; integrity {integ}")
print(f"criteria {crit}\nverdict {R['verdict']}  wall {R['wall_s']:.1f}s")
