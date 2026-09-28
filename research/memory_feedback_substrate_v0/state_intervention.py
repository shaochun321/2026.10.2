"""state_intervention.py — MFS0-E0 Step G（w-only 双向移植）+ Step H（未来通路阻断）。

TYPE:INFRA（research/ 层；production READ_ONLY）。

依据：修订方案 §21（Step G）、§22（Step H）、§24 M6。

## Step G（最强因果门）

在 washout 完成、query 尚未开始的时刻执行 do(w_TC ← w_NEAR)。只移动
Memristor.w——不动 e / M / 膜电压 / 历史核 / event trace / query 态。
Memristor 的状态字段只有 w 与 _w_initial（semiconductor.py:223-259），后者
两臂同为 0.90，电导由 w 派生 ⇒ do(w) 已覆盖载体的全部可变状态。
随后原位施加同一 Q，要求 Response_TC' ≈ Response_NEAR（Step F 录得）；
反向 do(w_NEAR ← w_TC) 同理。双向成立 ⇒ MINIMAL_SUFFICIENT_STATE = w，
STOP_DEEPER_DECOMPOSITION。

两臂均为确定性重放（Step E 已证逐位可复现），不是新条件。

## Step H

保留已写好的 w，在 query 时物理切断 bundle → readout 的交付（开路）。
单突触读出链下，切断 w 所在通路即切断 Q 的全部输入，阻断后两臂相等是
结构保证而非独立证据 ⇒ 必须按 §22 登记 BLOCK_LIMITATION。为让阻断不只是
同义反复，同时记录切断点**上游**的 bundle 电流差：若 w→G 在切断点前仍有
差异、切断点后消失，则差异确实只经这一条通路进入未来。

运行：python -m research.memory_feedback_substrate_v0.state_intervention（repo 根）
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import mfs0_common as M  # noqa: E402
import factorial_trials as FT  # noqa: E402


def _load(name):
    with open(os.path.join(M.DATA, name), encoding='utf-8') as f:
        return json.load(f)


def washed_arm(name):
    a = FT.make_arm(name)
    r = FT.run_write_and_washout(a)
    assert r["washout_reached"], f"{name} washout not reached"
    return a, r


def transplant(recipient: str, donor_w: float, target_resp):
    """recipient 臂 washout 后只改 w，再原位 query。"""
    a, r = washed_arm(recipient)
    e_before, m_before = a.e, a.m
    v_before = a.gate.dst._membrane.voltage
    a.gate.mem.w = donor_w                       # do(w)：唯一被移动的量
    untouched = (a.e == e_before and a.m == m_before
                 and a.gate.dst._membrane.voltage == v_before)
    q = FT.query_in_place(a)
    d = FT.rms(q["response"], target_resp)
    return {"recipient": recipient, "w_recipient_before": r["w_washout"],
            "w_after_do": donor_w, "only_w_moved": untouched,
            "rms_vs_donor_response": d,
            "pass": d <= M.EPSILON_NUM and untouched,
            "NC6_query_write_freeze": q["NC6_query_write_freeze"]}


def blocked_query(name):
    """Step H：切断 bundle→readout；同时记录切断点上游的 bundle 电流。"""
    a, r = washed_arm(name)
    w_before = a.gate.w
    wins = M.delta_windows(M.DELTA_S23_TID_STEPB)
    q_drive = M.drive_from_ports(wins, FT.Q_STEPS + wins[0].t_up)
    g = a.gate
    vs, cur_up = [], []
    for k in range(wins[0].t_up, wins[0].t_up + FT.Q_STEPS):
        g.src.step(q_drive[k].value, M.DT_G)
        cur = g.bundle.propagate()
        cur_up.append(cur[0] if cur else 0.0)   # 切断点上游（仍含 G(w)）
        g.dst.step(0.0, M.DT_G)                 # 开路：不交付 readout
        vs.append(g.dst._membrane.voltage)
        FT.step_arm(a)
    return {"response": vs, "upstream_current": cur_up,
            "w_preserved": g.w == w_before, "w": g.w}


def main() -> int:
    M.assert_no_step_era_import()
    stepf = _load('query_responses_stepF.json')
    fr = _load('factorial_results.json')
    w_near = fr["arms"]["F11_near"]["w_washout"]
    w_tc = fr["arms"]["TC11"]["w_washout"]
    d_pre = FT.rms(stepf["F11_near"], stepf["TC11"])

    # ── Step G ──
    M.ledger_add("state_interventions", "stepG_forward_wTC<-wNEAR",
                 "do(w_TC <- w_NEAR) after washout, then identical Q")
    fwd = transplant("TC11", w_near, stepf["F11_near"])
    M.ledger_add("state_interventions", "stepG_reverse_wNEAR<-wTC",
                 "do(w_NEAR <- w_TC) after washout, then identical Q")
    rev = transplant("F11_near", w_tc, stepf["TC11"])
    g_pass = fwd["pass"] and rev["pass"]

    # ── Step H ──
    M.ledger_add("path_blocks", "stepH_readout_sever_both_arms",
                 "sever bundle->readout during Q on NEAR and TC arms")
    hn = blocked_query("F11_near")
    ht = blocked_query("TC11")
    d_block = FT.rms(hn["response"], ht["response"])
    d_upstream = FT.rms(hn["upstream_current"], ht["upstream_current"])
    h_pass = (d_block <= M.EPSILON_NUM and hn["w_preserved"]
              and ht["w_preserved"])

    out = {
        "step": "G+H",
        "pre_intervention_D_Q": d_pre,
        "stepG": {"forward": fwd, "reverse": rev,
                  "bidirectional_transfer": g_pass,
                  "MFS0_MINIMAL_SUFFICIENT_STATE_CANDIDATE":
                      "w" if g_pass else None,
                  "STOP_DEEPER_DECOMPOSITION": g_pass},
        "stepH": {"D_Q_blocked": d_block,
                  "upstream_bundle_current_rms_diff": d_upstream,
                  "w_preserved_NEAR": hn["w_preserved"],
                  "w_preserved_TC": ht["w_preserved"],
                  "pass": h_pass,
                  "BLOCK_LIMITATION": (
                      "single-synapse readout: severing the w-bearing path "
                      "removes the entire Q input, so post-block equality is "
                      "structurally guaranteed and is not independent "
                      "evidence. Informative part: the w-dependent "
                      "difference is still present upstream of the cut "
                      "(upstream_bundle_current_rms_diff) and vanishes "
                      "downstream of it, i.e. it enters the future only via "
                      "this path. Causal-carrier claim rests on Step G.")},
    }
    M.write_json('causal_interventions.json', out)
    M.write_json('path_blocks.json', out["stepH"])

    print("MFS0-E0 Step G+H")
    print(f"  pre-intervention D_Q = {d_pre:.6e}")
    for tag, r in (("forward", fwd), ("reverse", rev)):
        print(f"  G {tag:<7}: recipient={r['recipient']:<9} "
              f"w {r['w_recipient_before']:.6f} -> {r['w_after_do']:.6f}  "
              f"RMS vs donor = {r['rms_vs_donor_response']:.3e}  "
              f"only_w={r['only_w_moved']}  {'PASS' if r['pass'] else 'FAIL'}")
    print(f"  Step G bidirectional = {g_pass}")
    print(f"  H: D_Q blocked = {d_block:.3e}   upstream current diff = "
          f"{d_upstream:.6e}   w preserved = "
          f"{hn['w_preserved'] and ht['w_preserved']}   "
          f"{'PASS' if h_pass else 'FAIL'} (+BLOCK_LIMITATION)")
    return 0 if (g_pass and h_pass) else 1


if __name__ == '__main__':
    raise SystemExit(main())
