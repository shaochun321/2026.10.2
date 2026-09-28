"""closure_amendment.py — MFS0-E0 收口追加修订（RULING-MFS0-R5 落地）。

TYPE:INFRA（research/ 层；production READ_ONLY）。

依据：用户 2026-09-29 裁定（接受我方《MFS0方案v2评判_2026-09-29》建议）：
  R-5 = (a) H1 按项目先例判 FAIL(EXPOSED)，hold6 = 5/6，
        生效终态 A_CONDITIONAL + HOLD_EXPOSURE；
  R-1~R-4 = 我方与外部 v2 一致意见（E1 设计前提，本脚本只登记）。

**追加式**：原始数据、原 JSON 数值字段、原脚本一律不改（同 Posterior-0
RULING-P0-1 先例：原 terminal_state 原样保留 + superseded_by 指针 +
新增 ruling_applied 区块）。不重跑任何臂、不补 hold（no re-run）。

产出：data/closure_amendment.json；qualification_summary.json 仅新增键。

运行：python -m research.memory_feedback_substrate_v0.closure_amendment（repo 根）
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import mfs0_common as M  # noqa: E402

RULING_DATE = "2026-09-29"

USER_RULINGS = {
    "source": "user acceptance of 'MFS0方案v2评判_2026-09-29.md' recommendations",
    "R-1": "material route = CAUSAL_REPLAY_REFERENCE + TEMPLATE_TRANSLATION "
           "(time-translated qualified typed windows; no live qualification "
           "for translated upstream occurrences)",
    "R-2": "write window = dual-reference, dual-offset compensated "
           "complementary branches (u0 = V_s*z, u1 = V_s*(1-z); references may "
           "be lowered by V_th for exact linearity); uncompensated version kept "
           "only as a bias control",
    "R-3": "observation = finite-hold observation capacitor + finite physical "
           "reset + RC timer (RailLatch not default); the observation state "
           "MUST be saturated/clamped, or the alpha_+ distribution over event "
           "timing must be pre-registered",
    "R-4": "drop the '>=10% better than mismatch' gate; an equal-frequency "
           "independent feedback copy is a negative reference only",
    "R-5": "(a) H1 = FAIL(EXPOSED) per project precedent; hold6 = 5/6; "
           "effective terminal = A_CONDITIONAL + HOLD_EXPOSURE",
}

# 下游消费的新依赖（不在 Step 0 的 14 项 seal 内）——事后补证
DEPENDENCY_SUPPLEMENT = [
    "research/posterior_v0/data/p0_probe_manifest.json",
    "research/d2_recursive_v1/dataset_builder.py",
    "research/d2_recursive_v1/d21_common.py",
    "research/d2_relation_v0/relation_physical_impl.py",
    "research/d2_relation_v0/d2_common.py",
] + [f"research/memory_feedback_substrate_v0/{f}" for f in (
    "mfs0_common.py", "preregistration.py", "eligibility_physical.py",
    "semantic_erasure_audit.py", "modulation_physical.py",
    "persistent_state_audit.py", "readout_feasibility.py",
    "timing_freeze.py", "factorial_trials.py", "state_intervention.py",
    "heldout_eval.py", "final_qualification.py",
    "data/eligibility_characterization.json",
    "data/modulation_characterization.json",
    "data/persistent_state_characterization.json",
    "data/readout_feasibility.json", "data/semantic_erasure_audit.json",
    "data/timing_manifest.json", "data/factorial_results.json",
    "data/query_responses_stepF.json", "data/heldout_manifest.json",
    "data/heldout_seal.json", "data/heldout_results.json")]


def _load(name):
    with open(os.path.join(M.DATA, name), encoding='utf-8') as f:
        return json.load(f)


def _git(*args) -> str:
    return subprocess.run(["git", *args], cwd=M._ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()


def _sha_file(path) -> str:
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def main_checkout() -> str:
    """git worktree list 的第一项 = 主仓 checkout（Step 0 seal 在此计算）。"""
    for line in _git("worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            return line[len("worktree "):]
    raise RuntimeError("no main worktree found")


def hold_exposure_audit() -> dict:
    ho = _load('heldout_results.json')
    feas = {c["delta_tid"]: c["expected_dw"] for c in
            _load('readout_feasibility.json')[
                "expected_dw_from_measured_envelopes"]["candidates"]}
    status = {
        "H1_unseen_timing": {
            "exposure": "EXPOSED",
            "evidence": "Step C readout_feasibility computed the same "
                        "deterministic envelope integral for W=cal_C3_m x "
                        "s23_hold_timing before sealing: expected_dw = %r; "
                        "hold measured %r" % (
                            feas["s23_hold_timing"],
                            next(r["dw"] for r in ho["cases"]
                                 if r["case"] == "H1_unseen_timing")),
            "verdict_after_ruling": "FAIL(EXPOSED)"},
        "H2_unseen_dose": {
            "exposure": "NO_MFS0_PRE_EXPOSURE_FOUND",
            "note": "'dose' is an upstream material name (site23 amp 0.04); "
                    "MFS0 does not encode dose (ELIGIBILITY/M carry no "
                    "amplitude DOF)",
            "verdict_after_ruling": "PASS"},
        "H3_unseen_past": {
            "exposure": "NO_MFS0_PRE_EXPOSURE_FOUND",
            "verdict_after_ruling": "PASS"},
        "H4_far_zero_elig": {
            "exposure": "NO_MFS0_PRE_EXPOSURE_FOUND",
            "note": "exact zero is SELECTIVITY_BY_CONSTRUCTION (DEG-019)",
            "verdict_after_ruling": "PASS"},
        "H5_matched_tc_H3": {
            "exposure": "MATERIAL_REUSED_COMBINATION_UNSEEN",
            "note": "Delta material p0_probe_near_r1c was the Step E TC arm "
                    "(with W=cal_C3_m); the cal_C5_strong combination was not "
                    "run. Exact zero is SELECTIVITY_BY_CONSTRUCTION",
            "verdict_after_ruling": "PASS"},
        "H6_no_past_H1": {
            "exposure": "NO_MFS0_PRE_EXPOSURE_FOUND",
            "note": "exact zero is SELECTIVITY_BY_CONSTRUCTION (W=0 => e=0)",
            "verdict_after_ruling": "PASS"},
    }
    n_pass = sum(v["verdict_after_ruling"] == "PASS" for v in status.values())
    return {
        "precedent": {
            "d21_hold_seal": "hold exposure => FAIL, no re-run",
            "p0_hold_seal": "hold exposure => FAIL, no re-run (zero-recall)"},
        "protocol_deviation": "MFS0 heldout_seal.json omitted the "
                              "'hold exposure => FAIL' clause present in both "
                              "precedent seals; the ruling applies the "
                              "precedent rather than the omission",
        "original_results_unchanged": "data/heldout_results.json (6/6 as "
                                      "measured) is preserved verbatim",
        "per_case": status,
        "hold6_after_ruling": f"{n_pass}/{len(status)}",
        "discriminating_cases": ["H2_unseen_dose", "H3_unseen_past"],
        "caveat": "H2/H3 are condition-variant checks, not findings "
                  "statistically independent of the model structure",
    }


def budget_runlog() -> dict:
    """run_id 级逐次清单（v2 §2.3）。单位：一次 invocation 中实际执行的仿真。"""
    runs = []

    def add(rid, cat, script, sims, counted, note=""):
        runs.append({"run_id": rid, "category": cat, "script": script,
                     "simulations": sims, "counted_in_original_ledger": counted,
                     "note": note})

    add("A-1", "eligibility_calibration", "eligibility_physical", 1, True, "W=1")
    add("A-2", "eligibility_calibration", "eligibility_physical", 1, True, "W=0")
    add("B-1", "modulation_calibration", "modulation_physical", 2, False,
        "first run t_total=12000 (D1+D0), attempted")
    add("B-2", "modulation_calibration", "modulation_physical", 2, True,
        "re-run t_total=14000 (D1+D0)")
    add("C-1", "persistent_baseline", "persistent_state_audit", None, True,
        "five questions + C3 sensitivity probe; internal query sub-runs "
        "counted as one set")
    add("C-2", "persistent_baseline", "readout_feasibility", None, True,
        "4 Delta-chain envelope replays + numeric probes, one set")
    add("C-3", "persistent_baseline", "readout_feasibility", 1, True,
        "Step A W=1 e-envelope re-run")
    add("X-1", "factorial_sets", "main_factorial.py (main checkout, deleted)",
        0, False, "invocation 1: crashed before any simulation "
                  "(PortWindow indexing) — not a run")
    add("X-2", "factorial_sets", "main_factorial.py (main checkout, deleted)",
        6, False, "invocation 2: NEAR_e x3 + NEAR_M x3, then crashed "
                  "(missing TC file); invalid single-carrier design")
    add("X-3", "factorial_sets", "main_factorial.py (main checkout, deleted)",
        6, False, "invocation 3: same 6 sims, crashed (manifest path); invalid")
    add("X-4", "factorial_sets", "main_factorial.py (main checkout, deleted)",
        12, True, "invocation 4: all 4 conditions x3; invalid by construction "
                  "(I_write identically 0); ledger item "
                  "'invalid_single_carrier_run_2026-09-29' recorded only this "
                  "one and its note says 12 sims")
    add("D-1", "timing_points", "timing_freeze", 1, False,
        "Step A W=1 e-envelope re-run (merged, not itemised)")
    add("D-2", "timing_points", "timing_freeze", 1, True, "NEAR s23_ov profile")
    add("D-3", "timing_points", "timing_freeze", 1, True,
        "TC p0_probe_near_r1c profile")
    for arm, cat in (("F00_near", "factorial_sets"), ("F10_near", "factorial_sets"),
                     ("F01_near", "factorial_sets"), ("F11_near", "factorial_sets"),
                     ("TC11", "timing_controls"), ("NC4_eblock", "path_blocks"),
                     ("NC5_mblock", "path_blocks")):
        add(f"E-{arm}", cat, "factorial_trials", 1, True,
            "write + washout + in-place query")
    add("G-1", "state_interventions", "state_intervention", 1, True,
        "TC11 recipient re-run + do(w) + query")
    add("G-2", "state_interventions", "state_intervention", 1, True,
        "F11_near recipient re-run + do(w) + query")
    add("H-1", "path_blocks", "state_intervention", 2, True,
        "F11_near + TC11 re-runs with severed readout (one ledger item)")
    for c in ("H1_unseen_timing", "H2_unseen_dose", "H3_unseen_past",
              "H4_far_zero_elig", "H5_matched_tc_H3", "H6_no_past_H1"):
        add(f"HO-{c.split('_')[0]}", "heldout", "heldout_eval", 1, True, c)

    caps = M.ledger_init()["caps"]
    # 口径：一个 ledger 集合单位 = 一次有效/尝试 invocation 的该类条目；
    # 与原 ledger 同一集合单位，但 attempted 计入
    units = {
        "eligibility_calibration": 2, "modulation_calibration": 2 + 2,
        "persistent_baseline": 3, "timing_points": 2,
        "factorial_sets": 1 + 3,       # 有效 2x2 集 + 3 次模拟过的无效 invocation
        "timing_controls": 1, "path_blocks": 3, "state_interventions": 2,
        "heldout": 6}
    used_with_attempted = {k: f"{units.get(k, 0)}/{cap}"
                           for k, cap in caps.items()}
    legal = all(units.get(k, 0) <= cap for k, cap in caps.items())
    return {
        "runs": runs,
        "total_simulations_listed": sum(r["simulations"] or 0 for r in runs),
        "correction": "the invalid factorial actually simulated 24 times "
                      "across 3 invocations (6+6+12), not 12 as the original "
                      "ledger note states; one invocation crashed before "
                      "simulating",
        "usage_counting_attempted": used_with_attempted,
        "within_caps_counting_attempted": legal,
        "note": "factorial_sets reaches 4/4 when attempted invocations are "
                "counted — at the cap, not over it. Original "
                "budget_ledger.json preserved verbatim.",
    }


def dependency_supplement() -> dict:
    items = []
    for rel in DEPENDENCY_SUPPLEMENT:
        path = os.path.join(M._ROOT, rel)
        items.append({"path": rel, "sha256_now": _sha_file(path),
                      "last_commit": _git("log", "-1", "--format=%h", "--",
                                          rel)})
    return {"label": "POST_HOC_SUPPLEMENT",
            "audited": RULING_DATE,
            "meaning": "confirms which version is under review now; does NOT "
                       "establish that these were sealed at the time "
                       "(v2 §2.4). Provenance = git commit history.",
            "items": items}


def seal_raw_byte_on_main_checkout() -> dict:
    seal = _load('frozen_upstream_seal.json')["targets"]
    main = main_checkout()
    res = {rel: _sha_file(os.path.join(main, rel)) == h
           for rel, h in seal.items()}
    return {"main_checkout": main,
            "main_checkout_head": _git("-C", main, "rev-parse", "--short",
                                       "HEAD"),
            "raw_byte_equal": res, "all_equal": all(res.values())}


def main() -> int:
    M.assert_no_step_era_import()
    hx = hold_exposure_audit()
    bud = budget_runlog()
    dep = dependency_supplement()
    raw = seal_raw_byte_on_main_checkout()
    persist = _load('persistent_state_characterization.json')

    amendment = {
        "round": "MFS0-E0",
        "type": "APPEND_ONLY_CLOSURE_AMENDMENT",
        "date": RULING_DATE,
        "user_rulings_2026-09-29": USER_RULINGS,
        "hold_exposure_audit": hx,
        "C3_deviation": {
            "planned": "RailLatch dynamics as measurement-chain positive "
                       "control (plan §13 / §31 Step C)",
            "RailLatch_dynamics_positive_control": "NOT_ATTEMPTED",
            "actually_executed": "w-perturbation readout sensitivity probe",
            "probe": persist["positive_control_C3"]["chain_sensitivity_probe"],
            "report_correction": "Step0ABC report's 'RailLatch 正对照 PASS' "
                                 "should read: RailLatch imported only; the "
                                 "executed check is a w-perturbation "
                                 "sensitivity probe",
            "handling": "recorded as a Step C execution deviation; not part "
                        "of M1-M6; no re-run",
        },
        "structural_necessity": {
            "items": ["Step G bidirectional transplant", "Step H readout "
                      "sever", "NC6 query-write freeze"],
            "why": "the write gate's readout chain (src/bundle/dst) is never "
                   "stepped before the query, so w is the only differing "
                   "state on the query path",
            "wording": "E0 implemented the intended persistent-carrier causal "
                       "path; the transplant checks that the implementation "
                       "obeys that path and screens for hidden readout "
                       "differences under current conditions. It is not an "
                       "independent discovery of a new memory degree of "
                       "freedom.",
        },
        "budget_runlog": bud,
        "dependency_supplement": dep,
        "seal_raw_byte_on_sealing_checkout": raw,
    }
    M.write_json('closure_amendment.json', amendment)

    q = _load('qualification_summary.json')
    q["terminal_state"]["superseded_by"] = "ruling_applied"
    q["ruling_applied"] = {
        "ruling_id": "RULING-MFS0-R5",
        "decision_date": RULING_DATE,
        "decided_by": "user (accepted recommendation (a) in "
                      "MFS0方案v2评判_2026-09-29.md §三.1)",
        "effective_terminal": "A_CONDITIONAL",
        "qualifier": "HOLD_EXPOSURE",
        "hold6_after_ruling": hx["hold6_after_ruling"],
        "gates_M1_M6": "unchanged (all PASS as measured)",
        "disclosures": ["H1 EXPOSED -> FAIL (precedent: hold exposure => "
                        "FAIL, no re-run)",
                        "MFS0 heldout_seal omitted the exposure clause",
                        "C3 RailLatch dynamics positive control NOT_ATTEMPTED",
                        "Step G/H/NC6 structurally guaranteed",
                        "dependency seal supplemented post hoc"],
        "allowed_wording": "Within the replay reference scope, E0 established "
                           "a conditional minimal causal memory substrate "
                           "candidate (historical eligibility + independent "
                           "later physical modulation + persistent w); "
                           "held-out support is 5/6 with one exposed case.",
        "detail": "data/closure_amendment.json",
    }
    M.write_json('qualification_summary.json', q)

    print("MFS0-E0 closure amendment (RULING-MFS0-R5)")
    print(f"  hold6 after ruling      = {hx['hold6_after_ruling']}")
    print(f"  effective terminal      = A_CONDITIONAL + HOLD_EXPOSURE")
    print(f"  runlog simulations      = {bud['total_simulations_listed']} "
          f"(invalid factorial corrected to 24)")
    print(f"  budget incl. attempted  = {bud['usage_counting_attempted']}")
    print(f"  within caps             = {bud['within_caps_counting_attempted']}")
    print(f"  dependencies supplemented = {len(dep['items'])}")
    print(f"  seal raw-byte on {raw['main_checkout']} ({raw['main_checkout_head']})"
          f" all equal = {raw['all_equal']}")
    return 0 if (bud['within_caps_counting_attempted'] and raw['all_equal']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
