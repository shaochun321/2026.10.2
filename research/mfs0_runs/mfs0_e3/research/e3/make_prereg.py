"""Generate prereg_E3.json (formal freeze) or a short dev variant for the pipeline smoke.

  python -B make_prereg.py formal   → prereg_E3.json (refuses to overwrite)
  python -B make_prereg.py dev OUT  → dev prereg (dev seeds 9xxxxxxx, short streams)
"""
import json
import os
import sys
import time

import e3_common as C

RUNTIME = ['e3_common.py', 'relation_spec.py', 'reference_solver_e3.py', 'context_trace.py', 'routing_latch.py',
           'relation_operator.py', 'conditional_memory_core.py', 'prediction_port_e3.py', 'stream_runner_e3.py',
           'scenario_builder_e3.py', 'run_e3.py', 'evaluate_e3.py', 'plot_e3.py', 'dev_checks_e3.py']


def build(dev=False):
    rel = json.load(open(os.path.join(C.HERE, 'results', 'selection', 'relation_table.json')))
    sA = {k: v['candidate'] for k, v in rel['splits'].items()}
    piA = {k: v['pi_D1'] for k, v in rel['splits'].items()}
    T = 60.0 if dev else 900.0
    seeds = (lambda b: b + 60000000) if dev else (lambda b: b)
    dom = dict(
        A=dict(streams=2 if dev else 24, T_s=T, seed_outcome_base=seeds(30301001), seed_time_base=seeds(31301001),
               seed_R_base=seeds(38301001), splits=sA, pi_R=piA, hold_ticks=[] if dev else [485000, 600000],
               generator='E2 G1 build_main, unchanged'),
        X=dict(streams=2 if dev else 12, T_s=T, seed_outcome_base=seeds(32301001), seed_time_base=seeds(33301001),
               seed_R_base=seeds(38301101), splits={'0': 'C6'}, pi_R={'0': 0.5}, hold_ticks=[] if dev else [485000, 600000],
               generator='scenario_builder_e3.build_X'),
        L=dict(streams=1 if dev else 6, T_s=T, seed_outcome_base=seeds(34301001), seed_time_base=seeds(35301001),
               seed_R_base=seeds(38301201), splits=sA, pi_R=piA, hold_ticks=[], fork_at_s=T / 2,
               fork_seed=seeds(35302001), w_sites=[28, 31, 21], l_site=23,
               stimulus='E2 live stimulus (dT 0.05, 1 s pulses, W every U[5,8] s, L at +U[0.3,0.6] s with p_i, L spacing >= 5 s) on the A timeline'),
        S=dict(streams=1 if dev else 2, T_s=60.0 if dev else 3600.0, seed_outcome_base=seeds(36301001),
               seed_time_base=seeds(37301001), splits=sA, hold_ticks=[] if dev else [2410000, 2530000],
               generator='E2 build_stress + core-level overload (CORE_INJECT); + deterministic flip suite'))
    pr = dict(
        kind='DEV_PIPELINE_SMOKE (not evidence)' if dev else 'FORMAL',
        frozen_at=time.strftime('%Y-%m-%d %H:%M:%S'),
        plan='cell-cell/交叉比对/MFS0-E3条件关系记忆与结构综合_一轮贯通执行方案_2026-10-01.md',
        e2_baseline=dict(freeze_ok=all(v[2] for v in C.check_e2_freeze().values()),
                         note='E2 sources restored 2026-10-01 from ~/.claude/file-history (rewind in session d7fa5ca5); '
                              'all 12 freeze_E2 hashes match; 120 s prefix of E2 formal stream 0 reproduced bit-identically'),
        relation_table=dict(A_L_S=sA, X={'0': 'C6'}, selection=rel['selection'],
                            pi_R=dict(A_L=piA, X={'0': 0.5}, X_note='X condition is designed (uniform A, B): P(A xor B) = 0.5; '
                                                                    'an A-environment D1 rate has no meaning for X')),
        constants=dict(dt=C.DT, m=1.0, alpha0=0.10, H_s=1.0397207708399179, tau_x=1.0, V_x=2.0, tau_K=30.0, V_K_read=1.0,
                       K_free=1e-3, G_Krst=1e-3, w0_all_carriers=0.5),
        domains=dom,
        utility_gates=dict(practical_min_improvement=-0.005, leaf_min_total=120, leaf_min_per_stream=10,
                           leaf_streams_fraction=0.5, hist_min_per_stream=30, interval='two-sided 95% t, df = n-1, stream = unit',
                           main_metric=dict(A_L='equal-weight mean of per-history Brier over all non-censored gate-accepted W records '
                                                'in S1/S2/S4 (rejections kept)', X='history 0 (W1) only')),
        mechanism_thresholds=dict(carrier_vs_reference=0.03, readout_vs_carrier=0.01, relabel_reverse=1e-10,
                                  hold_dw=1e-6, condition_boundary_drift_max_dt=2, normal_domain_rejections=0),
        registered_deviations_and_idealisations=[
            'site 21 is not in tss FROZEN_THERMAL_SITES (28/31/23); used because the plan names it; wrapped with '
            'wrap_base_generator + CollectorBoundaryPort + PhysicalEntryGate exactly like 28/31/23 (dev: responds to its own '
            'stimulus, no cross-talk)',
            'PYTHONHASHSEED=0 for every run (bundle.py hash() symmetry-breaking makes live input magnitudes process-dependent)',
            'trace/condition boundary: node comparator reads (k-k_a-1)dt < d vs time reference (k-k_a)dt <= d -> +1 dt (measured)',
            'trace set error vs ideal x<-V_x: -2.43e-6 relative',
            'leaf write branches carry one extra series route switch: leaf dose = marginal dose x (1 - ~3e-5)',
            'split slots: extra admission condition K < K_free; K clears 75 ms after T < theta_lo (O clears 282 ms after when set) -> '
            'occupancy <= 3.128 s < 2 x 2.6 s, no extra rejection under the A contract',
            'C2: static resistive logic node, no delay/capacitance (C1 comparators inherited); L5: T/O/K read by MOSFET gates '
            'with zero gate current (ideal fan-out)',
            'L prefix fork: checkpoint = copy.deepcopy of the whole run (VariantCircuit holds local lambdas, not picklable)',
            'hold check A/X: [485 s, 600 s) = 115 s (E2 window); the 120 s criterion is asserted in S and the flip suite; '
            'L hold not asserted (live sites may still emit entries in the silent segment)',
            'selected relation C1 = X_L^(H) exploits the single-L-channel refractoriness/spacing of the environment, not a '
            'cross-history causal structure'],
        seed_check='exact-string search of all 132 seeds over Codex work/outputs and J:/cell-cc (excl. .git, mfs0_e3, the plan '
                   'text): only digit runs inside float mantissas of one CSV; no seed use',
        workers=3, budget_s=43200,
        code_hashes={f: C.sha16(os.path.join(C.HERE, f)) for f in RUNTIME})
    return pr


if __name__ == '__main__':
    if sys.argv[1] == 'formal':
        p = os.path.join(C.HERE, 'prereg_E3.json')
        if os.path.exists(p):
            raise SystemExit('prereg_E3.json exists; refusing to overwrite')
    else:
        p = sys.argv[2]
    pr = build(dev=sys.argv[1] == 'dev')
    if sys.argv[1] == 'formal' and len(sys.argv) > 2:
        pr['budget_estimate'] = json.loads(sys.argv[2])
    json.dump(pr, open(p, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(p, pr['code_hashes'])
