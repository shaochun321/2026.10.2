"""heldout_eval.py — MFS0-E0 hold6：先 SHA 封存、后一次性运行、零回调。

TYPE:INFRA（research/ 层；production READ_ONLY）。

依据：修订方案 §23。全部 calibration 完成后冻结 τ_e / τ_M / w0 / 写入参数 /
FET 参数 / timing / washout / floors / query / 全部阈值，再建 hold6：
3 × main-history + 3 × matched timing/control。

用法（repo 根）：
  python -m research.memory_feedback_substrate_v0.heldout_eval --seal
      写 heldout_manifest.json + heldout_seal.json（首次运行前，单独提交）
  python -m research.memory_feedback_substrate_v0.heldout_eval
      校验 manifest SHA 与封存一致后一次性运行；运行后 NO RETUNING

判据（封存于 manifest，运行前固定）：
  DEPOSIT     : |Δw|>ε_z ∧ Retention_w≥RETENTION_W_MIN ∧ D_Q(vs w0 基线)>ε_Q
  NO_DEPOSIT  : |Δw| < TC_OVER_NEAR_MAX·|Δw_NEAR(Step E)|
  二者共同    : washout 实测到达 ∧ NC6（query 前后 w 逐位不变）
w0 基线响应 = Step F 的 TC11 响应（该臂 w 精确为 w0）。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import mfs0_common as M  # noqa: E402
import factorial_trials as FT  # noqa: E402
from relation_physical_impl import PortWindow  # noqa: E402

P0_MANIFEST = os.path.join(M._ROOT, 'research', 'posterior_v0', 'data',
                           'p0_probe_manifest.json')

CASES = [
    {"case": "H1_unseen_timing", "W": "cal_C3_m",
     "delta": "s23_hold_timing", "expect": "DEPOSIT"},
    {"case": "H2_unseen_dose", "W": "cal_C3_m",
     "delta": "s23_hold_dose", "expect": "DEPOSIT"},
    {"case": "H3_unseen_past", "W": "cal_C5_strong",
     "delta": "s23_ov", "expect": "DEPOSIT"},
    {"case": "H4_far_zero_elig", "W": "cal_C3_m",
     "delta": "p0_middle", "expect": "NO_DEPOSIT"},
    {"case": "H5_matched_tc_H3", "W": "cal_C5_strong",
     "delta": "p0_probe_near_r1c", "expect": "NO_DEPOSIT"},
    {"case": "H6_no_past_H1", "W": None,
     "delta": "s23_hold_timing", "expect": "NO_DEPOSIT"},
]


def _load(name):
    with open(os.path.join(M.DATA, name), encoding='utf-8') as f:
        return json.load(f)


def build_manifest() -> dict:
    td = _load('timing_manifest.json')
    fr = _load('factorial_results.json')
    thr = td["thresholds"]
    return {
        "round": "MFS0-E0",
        "cases": CASES,
        "rules": {
            "DEPOSIT": "|dw|>EPSILON_Z and retention_w>=RETENTION_W_MIN and "
                       "D_Q_vs_w0_baseline>EPSILON_Q",
            "NO_DEPOSIT": "|dw| < TC_OVER_NEAR_MAX*|dw_NEAR_stepE|",
            "both": "washout_reached and NC6_query_write_freeze",
        },
        "frozen": {
            "TAU_E": M.TAU_E, "TAU_M": M.TAU_M, "INITIAL_W": M.INITIAL_W,
            "FET_V_THRESHOLD": M.FET_V_THRESHOLD, "FET_GM": M.FET_GM,
            "WRITE_POLARITY": M.WRITE_POLARITY,
            "WRITE_DT_CORRECTION": "current = I_write*dt",
            "EPSILON_E": M.EPSILON_E, "EPSILON_M": M.EPSILON_M,
            "EPSILON_Z": M.EPSILON_Z, "RETENTION_W_MIN": M.RETENTION_W_MIN,
            "EPSILON_Q": _load('readout_feasibility.json')[
                "epsilon_Q_frozen_here"]["value"],
            "EPSILON_SEL": thr["EPSILON_SEL"], "S_MIN": thr["S_MIN"],
            "TC_OVER_NEAR_MAX": thr["TC_OVER_NEAR_MAX"],
            "dw_NEAR_stepE": fr["arms"]["F11_near"]["dw"],
            "query": "Step C typed phase ramp, Q_STEPS=%d, in place"
                     % FT.Q_STEPS,
            "washout": "until e<EPSILON_E and M<EPSILON_M (measured)",
        },
        "exposure_note": "s23_hold_timing appeared only in the Step C "
                         "analytic envelope integral (a prediction, not an "
                         "arm run); p0_probe_near_r1c is the frozen TC; "
                         "p0_middle / s23_hold_dose / cal_C5_strong have "
                         "never been run in MFS0.",
    }


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True,
                                     ensure_ascii=False).encode()).hexdigest()


def delta_wins(tid):
    if tid.startswith("p0_"):
        with open(P0_MANIFEST, encoding='utf-8') as f:
            up, _dn, re = json.load(f)[tid]["occ"][0]
        return [PortWindow(up, re, f"posterior_v0:{tid}#e1")]
    return M.delta_windows(tid)


def run_case(c) -> tuple:
    name = c["case"]
    elig = M.build_eligibility(f"{name}_e")
    modu = M.build_modulation(f"{name}_m")
    M.assert_paths_independent(elig, modu)
    gate = M.build_write_gate(f"{name}_w")
    ports = [M.load_relation_ports()[c["W"]]] if c["W"] else []
    a = FT.Arm(name, elig, modu, gate,
               M.drive_from_ports(ports, FT.T_WASHOUT_CAP),
               M.drive_from_ports(delta_wins(c["delta"]), FT.T_WASHOUT_CAP),
               False, False)
    r = FT.run_write_and_washout(a)
    q = FT.query_in_place(a)
    r.update({k: v for k, v in q.items() if k != "response"})
    return r, q["response"]


def main() -> int:
    M.assert_no_step_era_import()
    man = build_manifest()
    if "--seal" in sys.argv:
        M.write_json('heldout_manifest.json', man)
        M.write_json('heldout_seal.json',
                     {"heldout_manifest_sha256": _sha(man),
                      "sealed": "2026-09-29",
                      "discipline": "sealed before first hold run; no "
                                    "parameter/threshold/window may be tuned "
                                    "from hold outcomes (zero-recall)"})
        print(f"hold6 sealed: {_sha(man)}")
        return 0

    sealed = _load('heldout_seal.json')["heldout_manifest_sha256"]
    on_disk = _load('heldout_manifest.json')
    if _sha(on_disk) != sealed or _sha(man) != sealed:
        raise SystemExit("HOLD SEAL MISMATCH — manifest changed after sealing")

    fz = man["frozen"]
    base = _load('query_responses_stepF.json')["TC11"]
    rows = []
    for c in CASES:
        M.ledger_add("heldout", c["case"], "sealed hold6 case, single run")
        r, resp = run_case(c)
        d_q = FT.rms(resp, base)
        common = r["washout_reached"] and r["NC6_query_write_freeze"]
        if c["expect"] == "DEPOSIT":
            ok = (abs(r["dw"]) > fz["EPSILON_Z"]
                  and r["retention_w"] is not None
                  and r["retention_w"] >= fz["RETENTION_W_MIN"]
                  and d_q > fz["EPSILON_Q"])
        else:
            ok = abs(r["dw"]) < fz["TC_OVER_NEAR_MAX"] * abs(fz["dw_NEAR_stepE"])
        rows.append({**c, "dw": r["dw"], "retention_w": r["retention_w"],
                     "steps_writing": r["steps_with_nonzero_write_current"],
                     "t_washout": r["t_washout"],
                     "washout_reached": r["washout_reached"],
                     "NC6": r["NC6_query_write_freeze"],
                     "D_Q_vs_w0_baseline": d_q,
                     "pass": bool(ok and common)})

    n_pass = sum(r["pass"] for r in rows)
    M.write_json('heldout_results.json',
                 {"manifest_sha256": sealed, "cases": rows,
                  "passed": n_pass, "total": len(rows),
                  "HOLD6": "PASS" if n_pass == len(rows) else "FAIL",
                  "no_retuning": True})
    print("MFS0-E0 hold6 (sealed %s…)" % sealed[:12])
    for r in rows:
        print(f"  {r['case']:<18} expect={r['expect']:<10} dw={r['dw']:+.6e} "
              f"writing={r['steps_writing']:>4} D_Q={r['D_Q_vs_w0_baseline']:.3e} "
              f"ret={r['retention_w']}  {'PASS' if r['pass'] else 'FAIL'}")
    print(f"  hold6 = {n_pass}/{len(rows)}")
    return 0 if n_pass == len(rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
