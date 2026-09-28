"""factorial_trials.py — MFS0-E0 Step E（2×2 + NC1~NC5）→ washout → Step F（query + NC6）。

TYPE:INFRA（research/ 层；production READ_ONLY）。

依据：修订方案 §15~§20、§24(M4/M5) + Step D 冻结（data/timing_manifest.json）。

## 臂的物理定义（每臂 e 链与 M 链**同时**运行，写入门逐步合成）

  W∈{0,1}：e 链 typed 端口 = [W 的 relation port] 或 []（空 ⇒ ϑ≡0）
  Δ∈{0,1}：M 链 typed 端口 = [Δ 窗] 或 []
  写入   ：每步 write_gate.write(e, M) —— I_write = FET_e(e)·FET_M(M)

  NC4 e 路阻断：tin 照常被 W 驱动、bundle 照常 propagate（换能保留），
               但其电流不交付 C_e（开路）
  NC5 M 路阻断：adapter 照常被 Δ 驱动（换能 + collector 保留），
               但 spike 不交付 entry gate（开路）

## washout（§19：由实测衰减决定，不用固定步数）

写相结束后继续运行两条链（零驱动），直到 e<ε_e 且 M<ε_M，记录 t_washout
与 Retention_w = |w(t_washout)−w0| / |w(t_write_end)−w0|。

## Step F query（§20）

Q = Step C 已资格化的同一条 typed 相位斜坡（query_response 的输入剖面）。
**在各臂自己的写入门对象上原位施加**，而不是按 w 新建电路——后者等价于
一次 w 移植，会让 Step G 变成同义反复。query 期间 e/M 链继续零驱动运行并
每步调用 write()：NC6 要求 query 前后 w 逐位不变。

运行：python -m research.memory_feedback_substrate_v0.factorial_trials（repo 根）
"""
from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import dataclass
from typing import List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import mfs0_common as M  # noqa: E402
from timing_freeze import NEAR_TID, tc_window  # noqa: E402

T_WASHOUT_CAP = 30000      # 仅防死循环的安全上限；washout 由 e/M 实测触发
Q_STEPS = 2000             # 同 Step C query_response 的 t_total


def _load(name):
    with open(os.path.join(M.DATA, name), encoding='utf-8') as f:
        return json.load(f)


@dataclass
class Arm:
    name: str
    elig: M.EligibilityParts
    modu: M.ModulationParts
    gate: M.WriteGate
    drive_e: list
    drive_m: list
    block_e: bool
    block_m: bool
    k: int = 0
    e: float = 0.0
    m: float = 0.0


def build_arm(name: str, with_w: bool, delta_wins: Optional[list],
              block_e: bool = False, block_m: bool = False) -> Arm:
    elig = M.build_eligibility(f"{name}_e")
    modu = M.build_modulation(f"{name}_m")
    M.assert_paths_independent(elig, modu)
    gate = M.build_write_gate(f"{name}_w")
    ports = [M.w_relation_port()] if with_w else []
    wins = list(delta_wins) if delta_wins else []
    return Arm(name, elig, modu, gate,
               M.drive_from_ports(ports, T_WASHOUT_CAP),
               M.drive_from_ports(wins, T_WASHOUT_CAP), block_e, block_m)


def step_arm(a: Arm) -> float:
    """推进一步：e 链、M 链各自物理推进，再写入。返回 I_write。"""
    th_e = a.drive_e[a.k].value if a.k < len(a.drive_e) else 0.0
    th_m = a.drive_m[a.k].value if a.k < len(a.drive_m) else 0.0
    if a.block_e:
        a.elig.tin.step(th_e, M.DT_G)
        a.elig.bundle.propagate()              # 换能保留，电流不交付（开路）
        a.elig.cell.step(0.0, M.DT_G)
        a.e = a.elig.e
    else:
        a.e = M.step_eligibility(a.elig, th_e)
    if a.block_m:
        a.modu.adapter.step(th_m, M.DT_G)      # 换能 + collector 保留
        b_up = a.modu.gate.step(0.0, M.DT_G)   # spike 不交付 entry gate
        a.modu._m = a.modu.kernel.step(b_up, M.DT_G)
        a.m = a.modu._m
    else:
        a.m = M.step_modulation(a.modu, th_m)
    a.k += 1
    return a.gate.write(a.e, a.m)


def last_drive_step(a: Arm) -> int:
    idx = [k for k, s in enumerate(a.drive_e) if s.value > 0.0]
    idx += [k for k, s in enumerate(a.drive_m) if s.value > 0.0]
    return max(idx) if idx else 0


def run_write_and_washout(a: Arm) -> dict:
    """写相 + 物理 washout。返回 w 轨迹要点与 washout 判定。"""
    w0 = a.gate.w
    t_drive_end = last_drive_step(a)
    t_write_end, n_write, integral = -1, 0, 0.0
    w_write_end = w0
    while a.k < T_WASHOUT_CAP:
        i_w = step_arm(a)
        if i_w > 0.0:
            t_write_end = a.k - 1
            n_write += 1
            integral += i_w * M.DT_G
            w_write_end = a.gate.w
        if (a.k > t_drive_end and a.e < M.EPSILON_E and a.m < M.EPSILON_M):
            break
    washed = a.e < M.EPSILON_E and a.m < M.EPSILON_M
    w_wo = a.gate.w
    dw = w_wo - w0
    retention = (None if w_write_end == w0
                 else abs(w_wo - w0) / abs(w_write_end - w0))
    return {"w0": w0, "w_write_end": w_write_end, "w_washout": w_wo,
            "dw": dw, "retention_w": retention,
            "t_drive_end": t_drive_end, "t_write_end": t_write_end,
            "steps_with_nonzero_write_current": n_write,
            "integral_I_dt": integral,
            "t_washout": a.k, "washout_reached": washed,
            "e_at_washout": a.e, "M_at_washout": a.m}


def query_in_place(a: Arm, sever_readout: bool = False) -> dict:
    """在该臂自己的写入门上原位施加 Q；e/M 链同步零驱动 + write()（NC6）。

    sever_readout=True 为 Step H 的未来通路阻断：Q 照常驱动 src 与 bundle
    （w 与 G(w) 保留），但 bundle 电流不交付 readout（开路）。
    """
    wins = M.delta_windows(M.DELTA_S23_TID_STEPB)
    q_drive = M.drive_from_ports(wins, Q_STEPS + wins[0].t_up)
    g = a.gate
    w_before = g.w
    vs = []
    for k in range(wins[0].t_up, wins[0].t_up + Q_STEPS):
        g.src.step(q_drive[k].value, M.DT_G)
        cur = g.bundle.propagate()
        g.dst.step(0.0 if sever_readout else (cur[0] if cur else 0.0),
                   M.DT_G)
        vs.append(g.dst._membrane.voltage)
        step_arm(a)                     # 零驱动（k 已过所有窗）→ 须零写入
    return {"response": vs, "w_before_query": w_before,
            "w_after_query": g.w,
            "NC6_query_write_freeze": g.w == w_before}


def rms(a, b) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))


ARMS = [
    # name,          W,     Δ,      block_e, block_m, budget category
    ("F00_near",     False, None,   False, False, "factorial_sets"),
    ("F10_near",     True,  None,   False, False, "factorial_sets"),
    ("F01_near",     False, "near", False, False, "factorial_sets"),
    ("F11_near",     True,  "near", False, False, "factorial_sets"),
    ("TC11",         True,  "tc",   False, False, "timing_controls"),
    ("NC4_eblock",   True,  "near", True,  False, "path_blocks"),
    ("NC5_mblock",   True,  "near", False, True,  "path_blocks"),
]


def arm_windows(tag):
    if tag == "near":
        return M.delta_windows(NEAR_TID)
    if tag == "tc":
        return [tc_window()]
    return None


def make_arm(name: str) -> Arm:
    spec = {a[0]: a for a in ARMS}[name]
    _, w, d, be, bm, _ = spec
    return build_arm(name, w, arm_windows(d), be, bm)


def main() -> int:
    M.assert_no_step_era_import()
    td = _load('timing_manifest.json')
    if not td["READY_FOR_MAIN_FACTORIAL"]:
        raise SystemExit("Step D gate not passed — §31 forbids factorial")
    thr = td["thresholds"]

    results, responses = {}, {}
    for name, _w, _d, _be, _bm, cat in ARMS:
        item = ("stepE_set_NEAR_2x2" if cat == "factorial_sets"
                else f"stepE_{name}")
        M.ledger_add(cat, item, "Step E arm(s), write + physical washout")
        a = make_arm(name)
        r = run_write_and_washout(a)
        q = query_in_place(a)
        r.update({k: v for k, v in q.items() if k != "response"})
        results[name] = r
        responses[name] = q["response"]

    near, tc = results["F11_near"], results["TC11"]
    dw_near, dw_tc = near["dw"], tc["dw"]

    # ── M4：选择性持久沉积 ──
    d_sel = abs(dw_near - dw_tc)
    s_sel = abs(dw_near) / max(abs(dw_tc), M.EPSILON_Z)
    tc_over_near = abs(dw_tc) / abs(dw_near) if dw_near != 0.0 else math.inf
    ret_near = near["retention_w"]
    m4_items = {
        "abs_dw_near_gt_eps_z": abs(dw_near) > M.EPSILON_Z,
        "D_sel_gt_eps_sel": d_sel > thr["EPSILON_SEL"],
        "S_sel_gt_S_min": s_sel > thr["S_MIN"],
        "tc_over_near_lt_0.1": tc_over_near < thr["TC_OVER_NEAR_MAX"],
        "washout_reached_all_arms": all(r["washout_reached"]
                                        for r in results.values()),
    }

    # ── I_z（一致性检查，§16）──
    w = {k: results[k]["w_washout"] for k in
         ("F00_near", "F10_near", "F01_near", "F11_near")}
    i_z = (w["F11_near"] - w["F10_near"]) - (w["F01_near"] - w["F00_near"])

    # ── NC ──
    # NC4/NC5「明显下降或消失」：沿用 Step D 冻结的同一比值上限（0.1）
    nc_max = thr["TC_OVER_NEAR_MAX"]
    nc = {
        "NC1_no_past":   {"arm": "F01_near", "dw": results["F01_near"]["dw"],
                          "pass": results["F01_near"]["dw"] == 0.0},
        "NC2_no_later":  {"arm": "F10_near", "dw": results["F10_near"]["dw"],
                          "pass": results["F10_near"]["dw"] == 0.0},
        "NC3_timing_control": {"arm": "TC11", "dw": dw_tc,
                               "pass": m4_items["tc_over_near_lt_0.1"]},
        "NC4_eligibility_path_block": {
            "arm": "NC4_eblock", "dw": results["NC4_eblock"]["dw"],
            "pass": abs(results["NC4_eblock"]["dw"]) < nc_max * abs(dw_near)},
        "NC5_modulation_path_block": {
            "arm": "NC5_mblock", "dw": results["NC5_mblock"]["dw"],
            "pass": abs(results["NC5_mblock"]["dw"]) < nc_max * abs(dw_near)},
        "NC6_query_write_freeze": {
            "pass": all(r["NC6_query_write_freeze"] for r in results.values())},
    }

    # ── M5：未来因果作用（§20）──
    eps_q = _load('readout_feasibility.json')["epsilon_Q_frozen_here"]["value"]
    d_q = rms(responses["F11_near"], responses["TC11"])
    m5 = d_q > eps_q
    m4 = all(m4_items.values()) and ret_near is not None and \
        ret_near >= M.RETENTION_W_MIN

    out = {
        "step": "E+F",
        "arms": results,
        "M4_selective_persistent_deposition": {
            "dw_near": dw_near, "dw_tc": dw_tc, "D_sel": d_sel,
            "S_sel": s_sel, "tc_over_near": tc_over_near,
            "retention_w_near": ret_near,
            "retention_rule": "|w(t_washout)-w0| / |w(t_write_end)-w0|, "
                              "measured per arm",
            "items": m4_items, "MFS0_M4": "PASS" if m4 else "FAIL"},
        "I_z_consistency": {"I_z_observed": i_z,
                            "predicted_I_z": thr["predicted_I_z"],
                            "abs_error": abs(i_z - thr["predicted_I_z"]),
                            "role": "IMPLEMENTATION_CONSISTENCY_CHECK (§16), "
                                    "not a qualification gate"},
        "negative_controls": nc,
        "M5_future_causal_action": {"D_Q": d_q, "epsilon_Q": eps_q,
                                    "compared": ["F11_near", "TC11"],
                                    "MFS0_M5": "PASS" if m5 else "FAIL"},
    }
    M.write_json('factorial_results.json', out)
    M.write_json('timing_controls.json', nc)
    # 响应轨迹供 Step G/H 对照（逐位比较需要原始序列）
    M.write_json('query_responses_stepF.json',
                 {"F11_near": responses["F11_near"],
                  "TC11": responses["TC11"]})

    print("MFS0-E0 Step E+F")
    for n, r in results.items():
        print(f"  {n:<11} dw={r['dw']:+.6e}  writing={r['steps_with_nonzero_write_current']:>4}"
              f"  t_washout={r['t_washout']}  washed={r['washout_reached']}"
              f"  NC6={r['NC6_query_write_freeze']}")
    print(f"\n  M4: D_sel={d_sel:.6e}  S_sel={s_sel:.3e}  TC/NEAR={tc_over_near:.3e}")
    for k, v in m4_items.items():
        print(f"    {'OK ' if v else 'FAIL'} {k}")
    print(f"  MFS0-M4 = {'PASS' if m4 else 'FAIL'}")
    print(f"  I_z observed={i_z:.6e}  predicted={thr['predicted_I_z']:.6e}")
    for k, v in nc.items():
        print(f"    {'OK ' if v['pass'] else 'FAIL'} {k}")
    print(f"  M5: D_Q={d_q:.6e} vs eps_Q={eps_q:.0e}  MFS0-M5 = {'PASS' if m5 else 'FAIL'}")
    return 0 if (m4 and m5 and all(v["pass"] for v in nc.values())) else 1


if __name__ == '__main__':
    raise SystemExit(main())
