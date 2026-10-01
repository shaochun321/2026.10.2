"""MFS0-E2 development checks (plan §11A). Writes results/dev_checks.json. Dev seeds 9xxxx only."""
import json
import math
import os
import sys
import time

import e1_common  # noqa: F401  (paths)
from e1_common import log_run
from memory_core import MemoryCore
from stream_runner import run_stream, PulseInjector, PulseReplay
from current_input_bridge import ReplayBridge
from reference_solver import reference_z, q_of
from prediction_port import ThresholdConsumer, PredictionPort

DT = 0.001
OUT = os.path.join(os.path.dirname(__file__), 'results', 'dev')
os.makedirs(OUT, exist_ok=True)
R = {}
t0 = time.time()


def inj(w_ticks, l_ticks, n_ticks, n_hist=3, **core_kw):
    core = MemoryCore(n_hist=n_hist, **core_kw)
    res = run_stream(core, PulseInjector(w_ticks, l_ticks, n_hist), n_ticks, z_every=1)
    return core, res


def z_at(res, k, c=0):
    return res['z_log'][k][1][c]


# 1 isolated events, in/out window, window boundary (independent reference: H = τ ln(V_D/θ_hi))
core0 = MemoryCore()
H = core0.H_nominal
jH = math.ceil(H / DT - 1e-9)          # first tick index NOT in [s, s+H)
cases = {}
for name, dl in (('L_same_tick', 0), ('L_inside', 500), ('L_last_in', jH - 1), ('L_first_out', jH), ('L_far_out', 1500), ('no_L', None)):
    l = [] if dl is None else [100 + dl]
    core, res = inj([[100], [], []], l, 4000)
    dz = z_at(res, 3999) - 0.5
    cases[name] = dict(dz=dz, q_ref=q_of(100, l, H, DT) if l else 0)
R['window'] = dict(H_nominal=H, first_out_tick_offset=jH, cases=cases,
                   ok=all((c['dz'] > 0) == (c['q_ref'] == 1) for c in cases.values()))
print(f"[window] H={H:.6f} s, first-out offset {jH} ticks: " +
      " ".join(f"{k}:Δz={v['dz']:+.4f}(q={v['q_ref']})" for k, v in cases.items()) + f" ok={R['window']['ok']}")

# 2 two different histories overlapping, one L inside both windows → both write up
core, res = inj([[100], [400], []], [800], 5000)
R['cross_overlap_both_up'] = [z_at(res, 4999, 0) - 0.5, z_at(res, 4999, 1) - 0.5, z_at(res, 4999, 2) - 0.5]
print(f"[cross overlap] Δz per carrier {[round(x, 5) for x in R['cross_overlap_both_up']]} (expect +,+,0)")

# 3 same history, two slots settling concurrently with opposite q (core stress layer)
#    entries at 100 and 700: L at 1300 is in window 2 only ([700,1740)) and not window 1 ([100,1140))
core, res = inj([[100, 700], [], []], [1300], 6000)
admitted = [(100, 0), (700, 0)]
zr = reference_z(core, admitted, [1300], [5999], DT, 0.5)[0][5999]
zn = z_at(res, 5999)
# sequential software alternatives (for contrast only)
a = 0.1
seq_ud = (0.5 + a * (1 - 0.5)); seq_ud = seq_ud + a * (0 - seq_ud)
seq_du = (0.5 + a * (0 - 0.5)); seq_du = seq_du + a * (1 - seq_du)
R['same_hist_concurrent'] = dict(node=zn, reference=zr, diff=zn - zr, seq_up_then_down=seq_ud, seq_down_then_up=seq_du,
                                 slots_used=res['n_accept'][0], settle_entries=res['n_settle'][0])
print(f"[same-history concurrent opposite] node {zn:.5f} ref {zr:.5f} (diff {zn - zr:+.1e}); "
      f"sequential UD {seq_ud:.5f} DU {seq_du:.5f}; slots {res['n_accept'][0]} settles {res['n_settle'][0]}")

# 4 third entry beyond capacity: rejected, old experiences intact
core, res = inj([[100, 300, 500], [], []], [200], 6000)
recs = res['port'].records
R['capacity'] = dict(statuses=[r.status for r in recs], slots=[r.slot for r in recs],
                     n_accept=res['n_accept'][0], n_settle=res['n_settle'][0])
print(f"[capacity] statuses {R['capacity']['statuses']} slots {R['capacity']['slots']} "
      f"accepts {res['n_accept'][0]} settles {res['n_settle'][0]}")

# 5 long silence after drain: carrier constant; stream-end pending
core, res = inj([[100], [], []], [300], 140000)
w_after_drain = [x[1][0] for x in res['z_log'][5000:]]
R['silence_hold'] = dict(max_dz_after_drain=max(w_after_drain) - min(w_after_drain))
print(f"[silence] max |Δz| over 5 s..140 s after one experience: {R['silence_hold']['max_dz_after_drain']:.1e}")
core, res = inj([[100], [], []], [], 800)    # stream stops INSIDE the observation window
R['stream_end_in_window'] = dict(dz=z_at(res, 799) - 0.5, note='window [0.1, 1.14) s still open at stop: no write, Y censored')
core, res = inj([[100], [], []], [], 1500)   # window closed at 1.14 s, settle running at stop
R['stream_end_in_settle'] = dict(dz=z_at(res, 1499) - 0.5, note='window closed: non-occurrence established; partial settle write is legal')
print(f"[stream-end] stop in window Δz {R['stream_end_in_window']['dz']:+.2e} (censored); stop in settle Δz {R['stream_end_in_settle']['dz']:+.2e} (legal partial)")

# 3b near-simultaneous opposite writes on one carrier (plan §6.2 example, z0 = 0.4)
core, res = inj([[100, 101], [], []], [1140], 6000, w0=0.6)
zn = z_at(res, 5999)
zr = reference_z(core, [(100, 0), (101, 0)], [1140], [5999], DT, 0.4)[0][5999]
R['plan_6_2_example'] = dict(node=zn, reference=zr, ideal_simultaneous=0.419, seq_up_down=0.414, seq_down_up=0.424,
                             q=[q_of(100, [1140], H, DT), q_of(101, [1140], H, DT)])
print(f"[§6.2 example] q={R['plan_6_2_example']['q']} node {zn:.5f} ref {zr:.5f} ideal 0.419 (sequential 0.414 / 0.424)")

# 6 relabelling / summation order invariance (both slots of history 0 active)
patt_w = [[100, 700, 5000, 5600], [300], [2000]]
patt_l = [500, 1300, 5300]
_, ra = inj(patt_w, patt_l, 10000)
_, rb = inj(patt_w, patt_l, 10000, slot_order=[[1, 0], [1, 0], [1, 0]], reverse_sum=True)
dmax = max(abs(x[1][c] - y[1][c]) for x, y in zip(ra['z_log'], rb['z_log']) for c in range(3))
R['relabel_invariance_max'] = dmax
print(f"[relabel + reversed sum] max |Δz| = {dmax:.1e}")

# 7 equivalence with E1.1 device_mod on a single-history periodic sequence (m=1)
sys.path.insert(0, os.path.dirname(__file__))
from sim import Rig, run_cycles           # E1 generator/harness (copied)
import e1_1_device_mod_REFERENCE as DM
seq = [dict(hist=0, y=y, dL=d) for y, d in zip([1, 0, 1, 1, 0, 0, 1, 0], [0.3, 0.45, 0.7, 0.2, 0.5, 0.6, 0.4, 0.25])]
rig = Rig(w0=0.5, label='eq_e11')
rig.dev = DM.PredictiveMemoryDevice(n_hist=1, w0=0.5)
e11 = [o['z_after'][0] for o in run_cycles(rig, seq)]
w_st = [[4.0 * c + 0.10 for c in range(8)], [], []]
l_st = [4.0 * c + 0.10 + d['dL'] for c, d in enumerate(seq) if d['y']]
core = MemoryCore()
res = run_stream(core, ReplayBridge(w_st, l_st, label='eq_e2'), 32001, z_every=4000)
e2 = [x[1][0] for x in res['z_log'][1:9]]
R['equivalence_e11'] = dict(max_diff=max(abs(a - b) for a, b in zip(e11, e2)), e11=e11, e2=e2)
print(f"[equivalence vs E1.1 device_mod] max |Δz| at cycle ends = {R['equivalence_e11']['max_diff']:.2e}")

# 8 replay stream: reference, readout, consumer on/off, speed
from scenario_builder import build_main
sc = build_main(99000, 99500)
n60 = 60000
wl = [[t for t in x if t < 58.0] for x in sc['w']]
ll = [t for t in sc['l'] if t < 59.0]
tic = time.time()
core = MemoryCore()
cons = ThresholdConsumer()
resA = run_stream(core, ReplayBridge(wl, ll, label='dvA'), n60, consumer=cons)
speed = (time.time() - tic) / n60 * 1e6
coreB = MemoryCore()
resB = run_stream(coreB, ReplayBridge(wl, ll, label='dvB'), n60)
same = resA['z_log'] == resB['z_log']
adm = [(r.tick, r.path) for r in resA['port'].records if r.status == 'ADMITTED']
qt = [k for k, _ in resA['z_log']]
zr = reference_z(core, adm, resA['l_ticks'], qt, DT, 0.5)
ref_dev = max(abs(z[c] - zr[c][k]) for k, z in resA['z_log'] for c in range(3))
rd = max(abs(r.p_hat - (1 - 0) * 0 - r.p_hat) for r in resA['port'].records)  # placeholder, replaced below
zmap = dict(resA['z_log'])
# readout reference: p_hat vs carrier z at the same (pre-step) state; exact z needs per-tick log, so use a z_every=1 rerun
coreC = MemoryCore()
resC = run_stream(coreC, ReplayBridge(wl, ll, label='dvC'), n60, z_every=1)
zC = dict(resC['z_log'])
rd = max(abs(r.p_hat - zC[r.tick][r.path]) for r in resC['port'].records)
R['replay60'] = dict(us_per_step=speed, consumer_on_off_identical=same, hints=len(cons.hints),
                     max_dev_vs_reference=ref_dev, max_readout_vs_z=rd,
                     n_records=len(resA['port'].records), rejected=sum(len(x) for x in resA['rejected']),
                     n_accept=resA['n_accept'], n_settle=resA['n_settle'])
print(f"[replay 60 s] {speed:.0f} us/step; consumer on/off identical {same} (hints {len(cons.hints)}); "
      f"max |z − z_ref| {ref_dev:.4f}; max |p̂ − z| {rd:.4f}; records {len(resA['port'].records)}, rejected {R['replay60']['rejected']}; "
      f"accept {resA['n_accept']} settle {resA['n_settle']}")

R['wall_s'] = time.time() - t0
json.dump(R, open(os.path.join(OUT, 'dev_checks.json'), 'w'), indent=1, default=str)
log_run(stage='DEV', run_id='dev_checks_r0', wall_s=R['wall_s'], note='development checks, dev seeds 99xxx')
print(f"wall {R['wall_s']:.1f}s")
