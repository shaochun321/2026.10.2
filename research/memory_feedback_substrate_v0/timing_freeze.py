"""timing_freeze.py — MFS0-E0 Step D：冻结 NEAR / TIMING CONTROL / 三个剩余阈值。

TYPE:INFRA（research/ 层；production READ_ONLY）。

依据：修订方案 §17/§16/§31 + 《MFS0-E0 Step D–H 执行反馈与开工裁定》§2~§5、§10
+ 用户 2026-09-29 裁定（TC 条件接受，见 TC_RULING）。

## 三类 timing（裁定 §2）

  NEAR                           = Δ 写窗与 e 写入可达窗完全重叠
  WEAK_OVERLAP                   = 部分重叠（仍有非零写电流）——不得冒充 TC
  ZERO_ELIGIBILITY_TIMING_CONTROL = 整个 later 写区间内 FET_e.conduct(e)=0

判据全部**实测**：e 取 Step A W=1 臂（逐位可复现），M 取 Δ 链真实重放，
逐步计算 I_write = FET_e(e)·FET_M(M)。TC 要求整条轨迹上 I_write 精确为 0。

## TC_RULING（用户 2026-09-29）

库存中不存在与 NEAR 在上游脉冲长度上严格匹配的晚时点 site23 轨迹：
NEAR s23_ov 为 600 步脉冲；晚时点 600 步脉冲打不出 occurrence（D2-1 NF-1
s23_far 零发生 / Posterior-0 probe1_P600 support_window_too_short），
Posterior-0 被迫改用 900 步（R1C_FALLBACK）。其余各项（位点/幅值/typed 家族/
occurrence 时长 139/639 步/物理路径）逐项相同，且 MFS0 只经 build_phase_drive
消费 (t_up, t_rearm)，两者喂入 M 链的是同一条 639 步相位斜坡。
用户裁定：条件接受为 TYPED_INTERFACE_MATCHED_TIMING_CONTROL，登记 LIMITATION。

## 三阈值（裁定 §5；factorial 前落盘）

  ε_sel = max(10·nowrite_floor, 1e-6)，nowrite_floor 取 Step C 实测的
          零输入 w 漂移与 sham-repeat 二者之大者
  S_min = 10，另要求 |Δw_TC|/|Δw_NEAR| < 0.1；ratio 不得单独构成 PASS
  predicted_I_z：Tier-2 实现下 w10=w01=w00=w0（任一因子阈下写电流精确为 0），
          故 I_z = Δw_11(NEAR)，由冻结包络积分给出，不从 factorial 拟合

运行：python -m research.memory_feedback_substrate_v0.timing_freeze（repo 根）
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import mfs0_common as M  # noqa: E402
import eligibility_physical as EA  # noqa: E402
from nexus_v1.components.semiconductor import MOSFET  # noqa: E402
from relation_physical_impl import PortWindow  # noqa: E402

NEAR_TID = "s23_ov"
TC_TID = "p0_probe_near_r1c"
P0_MANIFEST = os.path.join(M._ROOT, 'research', 'posterior_v0', 'data',
                           'p0_probe_manifest.json')
D21_BUILDER = os.path.join(M._D21, 'dataset_builder.py')
S_MIN = 10.0
TC_OVER_NEAR_MAX = 0.1


def _load(name):
    with open(os.path.join(M.DATA, name), encoding='utf-8') as f:
        return json.load(f)


def tc_window() -> PortWindow:
    with open(P0_MANIFEST, encoding='utf-8') as f:
        entry = json.load(f)[TC_TID]
    t_up, _t_down, t_rearm = entry["occ"][0]
    return PortWindow(t_up, t_rearm, f"posterior_v0:{TC_TID}#e1")


def write_profile(e_trace, wins, t_total, ident) -> dict:
    """真实 Δ 链重放 + 实测 e 轨迹 → 逐步写电流（不写 w，只计量）。"""
    drive = M.drive_from_ports(wins, t_total)
    p = M.build_modulation(ident)
    fe = MOSFET(v_threshold=M.FET_V_THRESHOLD, gm=M.FET_GM)
    fm = MOSFET(v_threshold=M.FET_V_THRESHOLD, gm=M.FET_GM)
    integral, n_write, i_peak, gate_e_max = 0.0, 0, 0.0, 0.0
    m_write = []
    for k in range(t_total):
        m = M.step_modulation(p, drive[k].value)
        e = e_trace[k] if k < len(e_trace) else 0.0
        ge, gm = fe.conduct(e), fm.conduct(m)
        if gm > 0.0:
            m_write.append(k)
            gate_e_max = max(gate_e_max, ge)
        i_w = ge * gm
        if i_w > 0.0:
            n_write += 1
            i_peak = max(i_peak, i_w)
            integral += i_w * M.DT_G
    return {"delta_window": [wins[0].t_up, wins[0].t_rearm],
            "M_write_interval": ([m_write[0], m_write[-1]] if m_write
                                 else [-1, -1]),
            "max_FET_e_during_M_write_interval": gate_e_max,
            "steps_with_nonzero_write_current": n_write,
            "I_write_peak": i_peak,
            "integral_I_dt": integral,
            "predicted_dw": -0.5 * integral}


def match_audit() -> dict:
    """TIMING_MATCH_AUDIT（裁定 §4）：逐项比较，事实取自两轮存档。"""
    with open(P0_MANIFEST, encoding='utf-8') as f:
        tc = json.load(f)[TC_TID]
    sys.path.insert(0, M._D21)
    import dataset_builder as DB  # noqa: E402
    near_spec = {t: (t_on, a) for t, t_on, a, _ in DB.S23_CAL}[NEAR_TID]
    d21 = {w.occurrence_id: w for w in M.delta_windows(NEAR_TID)}
    near_w = M.delta_windows(NEAR_TID)[0]
    tc_up, tc_down, tc_rearm = tc["occ"][0]
    import csv
    with open(os.path.join(M.D21_DATA, 'site23_occurrence_manifest.csv'),
              encoding='utf-8') as f:
        near_row = next(r for r in csv.DictReader(f)
                        if r["traj"] == NEAR_TID)
    near_down = int(near_row["t_down"])
    items = {
        "source_identity": {"NEAR": "site23 pulse channel C", "TC":
                            "site23 pulse channel C", "match": True},
        "stimulus_amplitude": {"NEAR": near_spec[1], "TC": tc["spec"]["amp"],
                               "match": near_spec[1] == tc["spec"]["amp"]},
        "pulse_support_duration_steps": {"NEAR": DB.P,
                                         "TC": tc["spec"]["length"],
                                         "match": DB.P == tc["spec"]["length"]},
        "typed_input_family": {"NEAR": "site23 PortWindow -> build_phase_drive",
                               "TC": "site23 occurrence -> PortWindow -> "
                                     "build_phase_drive", "match": True},
        "occurrence_duration_up_to_down": {
            "NEAR": near_down - near_w.t_up, "TC": tc_down - tc_up,
            "match": (near_down - near_w.t_up) == (tc_down - tc_up)},
        "occurrence_duration_up_to_rearm": {
            "NEAR": near_w.t_rearm - near_w.t_up, "TC": tc_rearm - tc_up,
            "match": (near_w.t_rearm - near_w.t_up) == (tc_rearm - tc_up)},
        "physical_path": {"NEAR": "RelationEventAdapter -> PhysicalEntryGate "
                                  "-> PhysicalHistoryKernel (H_tau^Delta)",
                          "TC": "identical (same build_modulation)",
                          "match": True},
    }
    del d21
    return items


def main() -> int:
    M.assert_no_step_era_import()
    step_c = _load('readout_feasibility.json')
    persist = _load('persistent_state_characterization.json')
    e_write_win = step_c["expected_dw_from_measured_envelopes"][
        "e_write_reachable_window"]

    # ── 1. 实测包络 + NEAR / TC 写电流剖面 ──
    t_total = M.T_TOTAL_STEPB
    e_trace = EA.run_arm(True, t_total)["e"]
    M.ledger_add("timing_points", "stepD_NEAR_s23_ov",
                 "measured write profile at NEAR (real Delta-chain replay)")
    near = write_profile(e_trace, M.delta_windows(NEAR_TID), t_total,
                         "stepD_near")
    M.ledger_add("timing_points", "stepD_TC_p0_probe_near_r1c",
                 "measured write profile at TIMING CONTROL candidate")
    tc = write_profile(e_trace, [tc_window()], t_total, "stepD_tc")

    # ── 2. timing 分类（Step C 已测四候选 + 本步 TC）──
    classes = {}
    for c in step_c["expected_dw_from_measured_envelopes"]["candidates"]:
        n = c["steps_with_nonzero_write_current"]
        lo, hi = c["delta_window"]
        full = e_write_win[0] <= lo and hi <= e_write_win[1]
        classes[c["delta_tid"]] = ("NEAR_ELIGIBLE" if full and n > 0 else
                                   "WEAK_OVERLAP" if n > 0 else
                                   "ZERO_ELIGIBILITY")
    classes[TC_TID] = ("ZERO_ELIGIBILITY"
                       if tc["steps_with_nonzero_write_current"] == 0
                       else "WEAK_OVERLAP")
    tc_zero = (tc["steps_with_nonzero_write_current"] == 0
               and tc["max_FET_e_during_M_write_interval"] == 0.0)

    # ── 3. 匹配审计 + 用户裁定 ──
    audit = match_audit()
    mismatches = [k for k, v in audit.items() if not v["match"]]

    # ── 4. 三阈值 ──
    # 键缺失即 KeyError——不以默认 0 充当实测 floor
    nowrite_floor = max(
        abs(persist["persistence_contract"]["zero_input_drift_5000_steps"]),
        abs(persist["determinism"]["same_w_repeat_rms_diff"]),
        abs(step_c["numeric_readout"]["sham_repeat_rms"]))
    eps_sel = max(10.0 * nowrite_floor, M.EPSILON_NUM)
    predicted_iz = near["predicted_dw"]

    ready = (tc_zero and near["steps_with_nonzero_write_current"] > 0
             and abs(predicted_iz) > M.EPSILON_Z)

    manifest = {
        "step": "D",
        "NEAR": {"tid": NEAR_TID, "class": classes[NEAR_TID],
                 "reason": "first valid full-overlap candidate; not selected "
                           "by maximum expected effect (s23_hold_timing "
                           "predicts 3.7x larger and is kept only as "
                           "secondary sensitivity condition)",
                 **near},
        "TIMING_CONTROL": {
            "tid": TC_TID, "class": classes[TC_TID], **tc,
            "zero_eligibility_measured": tc_zero,
            "status": "TYPED_INTERFACE_MATCHED_TIMING_CONTROL",
            "STRICT_TIMING_CONTROL_AVAILABLE": False,
            "user_ruling": "2026-09-29 conditional acceptance",
            "LIMITATION": "upstream pulse/support duration differs "
                          "(NEAR 600 steps vs TC 900 steps). Forced by NF-1 "
                          "latency drift: a 600-step site23 pulse at late "
                          "timing produces no occurrence (D2-1 s23_far; "
                          "Posterior-0 probe1_P600). All other items match, "
                          "and MFS0 consumes only (t_up, t_rearm) via "
                          "build_phase_drive, so both drive the M chain "
                          "with the same 639-step phase ramp."},
        "timing_classes": classes,
        "timing_match_audit": audit,
        "timing_match_mismatches": mismatches,
        "thresholds": {
            "EPSILON_SEL": eps_sel,
            "EPSILON_SEL_rule": "max(10 * nowrite_floor, 1e-6)",
            "nowrite_floor": nowrite_floor,
            "S_MIN": S_MIN,
            "TC_OVER_NEAR_MAX": TC_OVER_NEAR_MAX,
            "ratio_alone_not_pass": True,
            "predicted_I_z": predicted_iz,
            "predicted_I_z_basis": "Tier-2: w10=w01=w00=w0 exactly (a "
                                   "sub-threshold factor hard-zeroes "
                                   "I_write), so I_z = dw_11(NEAR); integral "
                                   "of measured e and replayed M envelopes",
            "predicted_dw_TC": tc["predicted_dw"],
        },
        "write_current_api_note": "Memristor.update(current=...) receives a "
                                  "time-integrated write-current increment "
                                  "(I_write*dt) in this round: a workaround "
                                  "for the production API missing dt "
                                  "(MEMRISTOR_UPDATE_MISSING_DT, DEG to be "
                                  "registered at round close); applied "
                                  "identically to every arm.",
        "READY_FOR_MAIN_FACTORIAL": ready,
        "frozen_after_step_d": ["tau_e", "tau_M", "w0", "FET thresholds",
                                "write polarity", "write dt correction",
                                "NEAR", "TIMING CONTROL",
                                "selection thresholds"],
    }
    M.write_json('timing_manifest.json', manifest)

    prereg = _load('preregistration.json')
    prereg["step_d_freeze"] = {
        "date": "2026-09-29",
        "resolves_deferred": ["EPSILON_SEL", "S_MIN", "predicted_Iz"],
        "EPSILON_SEL": eps_sel, "S_MIN": S_MIN,
        "TC_OVER_NEAR_MAX": TC_OVER_NEAR_MAX,
        "predicted_I_z": predicted_iz,
        "NEAR": NEAR_TID, "TIMING_CONTROL": TC_TID,
        "TIMING_CONTROL_status": "TYPED_INTERFACE_MATCHED (user ruling "
                                 "2026-09-29, LIMITATION registered)",
        "READY_FOR_MAIN_FACTORIAL": ready,
        "source": "data/timing_manifest.json",
    }
    M.write_json('preregistration.json', prereg)

    print("MFS0-E0 Step D — timing freeze")
    print(f"  e write-reachable window = {e_write_win}")
    for tid, cls in classes.items():
        print(f"    {tid:<22} {cls}")
    print(f"  NEAR {NEAR_TID}: steps_writing={near['steps_with_nonzero_write_current']}"
          f"  predicted dw={near['predicted_dw']:.6e}")
    print(f"  TC   {TC_TID}: steps_writing={tc['steps_with_nonzero_write_current']}"
          f"  max FET_e during M write={tc['max_FET_e_during_M_write_interval']:.3e}"
          f"  M write interval={tc['M_write_interval']}")
    print(f"  match mismatches = {mismatches}")
    print(f"  eps_sel={eps_sel:.3e}  S_min={S_MIN}  predicted_I_z={predicted_iz:.6e}")
    print(f"\n  READY_FOR_MAIN_FACTORIAL = {ready}")
    return 0 if ready else 1


if __name__ == '__main__':
    raise SystemExit(main())
