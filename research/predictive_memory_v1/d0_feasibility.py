"""d0_feasibility.py — MFS0-E1 D0：器件设计可行域分析（纯解析，不运行器件仿真）。

TYPE:INFRA（research/ 层；production READ_ONLY）。

依据：`cell-cell/交叉比对/MFS0-E1下一阶段方案_器件设计与映射资格_2026-09-29.md`
§5~§8、§9 D0 + 我方评判 `MFS0-E1方案评判_2026-09-29.md` E-1~E-5 +
用户 2026-09-29 裁定 R-1（独立副本 mfs0-e1 分支）、R-2（独立有限复位支路
为必需项）、R-3（互补门两候选并列比较，按 ε_α 上界择一）。

本脚本只回答"约束是否有共同解"，不实现器件。所有参数分三类标注：
  FROZEN   — 继承已冻结且有依据的值（E0 / 原语默认）
  DESIGN   — 本阶段为设计目标预先选定的误差预算（非物理常数）
  DERIVED  — 由前两类推导
没有来源的量一律不填，列为 OPEN。

输出：data/d0_feasibility.json（写入 research/predictive_memory_v1/）
运行：python -B -m research.predictive_memory_v1.d0_feasibility（repo 根）
"""
from __future__ import annotations

import json
import math
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(_HERE, 'data')

# ── FROZEN ────────────────────────────────────────────────────────────
DT = 0.001                    # s，GENERATOR_DT（G0-R0 冻结）
THETA_FET = 0.3               # V，MOSFET 原语 v_threshold（semiconductor.py:130）
GM = 1.0                      # MOSFET 原语 gm
V_REF = 1.0                   # V，路径 B 电导换算 g_c = gm/V_REF（rail_latch.py 先例）
R_MIN, R_MAX = 0.1, 10.0      # Memristor 原语
TAU_E = 0.300                 # s，E0 冻结（Step A 实测 0.300000）
# E0 Step A 实测（旧非因果驱动；E-6：因果驱动下须重测，这里只作量级参考）
E_PEAK_OLD = 3.305
W_SUPPORT_OLD_STEPS = 3971 - 2617      # W 旧窗 t_up→t_rearm = 1354 步
E_ABOVE_THETA_OLD = (276, 2072)        # e>θ 相对 t_up 的步数（本脚本前实测）
US_PER_STEP_E0 = 33.2                  # 墙钟，E0 单臂实测 μs/步

# ── DESIGN（误差预算，本阶段预先选定，非物理常数）─────────────────────
DESIGN = {
    "delta_plateau": 0.01,     # 读出平台相对误差
    "delta_settle": 0.01,      # 最晚事件的建立残差
    "delta_clear": 0.01,       # 无事件时残留 v_off/V_H（与 δ_obs 同阶）
    "eps_alpha": 0.05,         # 两路有效 α 相对失配上限
    "p_task": 0.8,             # 任务概率（评估用，不进器件）
}

# ── E0 时序参考（site23 later 发生潜伏期，D2-1 NF-1）─────────────────
LATENCY_SITE23 = (521, 637)            # 步，t_on→t_up，存在漂移


def plateau_bound(d):
    """§5.1：G_min(R_S+R_L) ≥ (1−δ)/δ。"""
    return (1 - d) / d


def passive_clear_settle_ratio(dp, ds, v_ratio):
    """评判 E-1：单节点被动负载下 T_clear/T_settle 的最小值（C_s、G 约掉）。"""
    return plateau_bound(dp) * math.log(v_ratio) / math.log(1 / ds)


def active_reset(dp, ds, dc, k_reset):
    """R-2 独立有限复位支路：复位期间并联导通 R_r = R_L/k_reset。

    清除时常 τ_clear = C_s·(R_L‖R_r) = C_s·R_L/(1+k)；建立时常仍 ≈ C_s·R_L
    （平台下界处 1/G ≪ R_S+R_L）。于是比值条件变为
        T_clear/T_settle ≥ plateau_bound·ln(1/dc) / ((1+k)·ln(1/ds))
    k 由复位 FET 的导通电导与 R_L 之比决定（设计量）。
    """
    return plateau_bound(dp) * math.log(1 / dc) / ((1 + k_reset) *
                                                    math.log(1 / ds))


def v_o_min(g_min_si):
    """E-2：观察电压最低有效值 V_o,min = θ_o + G_min/g_c，g_c = gm/V_REF。"""
    return THETA_FET + g_min_si / (GM / V_REF)


def z_star(p, a_plus, a_minus):
    return p * a_plus / (p * a_plus + (1 - p) * a_minus)


def complement_candidates(eps_ref_rel):
    """R-3：互补门两候选的 ε_α 上界（解析，小失配一阶）。

    (a) 参考减法：1−s 由 (V_H,ref − v)/V_H 形成，V_H,ref 与读出平台 V_H 的
        相对失配 ε_ref 直接成为 y=0 支路增益误差 ⇒ ε_α ≈ ε_ref + δ_plateau
        （平台残差在 y=0 时使 1−s 偏离 1）。
    (b) 抑制型：常通支路被 s 关断，y=0 支路增益由常通支路自身电导决定，
        与读出平台无关 ⇒ ε_α ≈ ε_ref(常通电导 vs 写支路电导) ；但 y=1 时
        关断不完全的残余 ≈ 平台残差 δ_plateau 进入 J_rec（错误方向写入）。
    两者一阶都约为 ε_ref + δ_plateau；区别在误差出现在哪一路：(a) 在 α₋ 的
    幅值，(b) 在 y=1 时的反向泄漏。故选择依据是元件可用性而非精度。
    """
    dp = DESIGN["delta_plateau"]
    return {
        "a_reference_subtraction": {
            "eps_alpha_bound": eps_ref_rel + dp,
            "error_location": "alpha_minus magnitude (y=0 branch gain)",
            "needs_new_primitive": False,
            "needs": "a reference node tracking V_H (same supply, matched "
                     "divider) + a subtraction node; built from Capacitor/"
                     "MOSFET/PowerRail",
        },
        "b_inhibitory_normally_on": {
            "eps_alpha_bound": eps_ref_rel + dp,
            "error_location": "residual reverse write when y=1 "
                              "(incomplete turn-off)",
            "needs_new_primitive": True,
            "needs": "a normally-on channel turned OFF by s; the repo MOSFET "
                     "is enhancement-only (conducts above threshold), so this "
                     "is not available as a primitive — would need a new "
                     "depletion/inhibitory element with its own Q1-Q3",
        },
    }


def main() -> int:
    os.makedirs(DATA, exist_ok=True)
    dp, ds, dc = (DESIGN["delta_plateau"], DESIGN["delta_settle"],
                  DESIGN["delta_clear"])
    pb = plateau_bound(dp)

    # 1. 被动结构（方案 §5.1/5.2）——E-1 比值
    passive = passive_clear_settle_ratio(dp, ds, 1 / dc)

    # 2. R-2 独立复位支路：给定可用时间比，所需 k
    # 可用时间：观察窗必须落在 e 写入可达窗内（§8 第二式）。以旧驱动量级估：
    # 可用于"结算+清除"的时间 ≈ e>θ 窗尾 − 最晚发生时刻；最晚发生
    # ≈ W 起点 + 潜伏期上限。建立时间受最晚事件约束。
    e_lo, e_hi = E_ABOVE_THETA_OLD
    t_settle_budget = None   # OPEN：须因果驱动下重测 e 窗后才能定
    ratios = {}
    for k in (0, 9, 49, 99, 199):
        ratios[k] = active_reset(dp, ds, dc, k)

    # 3. E-4：目标偏差合成
    p = DESIGN["p_task"]
    ea = DESIGN["eps_alpha"]
    dz_alpha = z_star(p, 1.0, 1.0 - ea) - p        # α₋ 偏小 ε_α
    dz_bound = dc + p * (1 - p) * ea

    # 4. E-2：V_o,min 需要 G_min；G_min 由 R_S+R_L 与平台界定——
    # G_min(R_S+R_L) ≥ 99。R_S+R_L 未定（OPEN），故给出 V_o,min 关于
    # (R_S+R_L) 的函数值，以 R_L 取 E0 读出负载同量级（C_E·R_E: R=3.0）为例。
    vo_examples = {f"R_S+R_L={r}": v_o_min(pb / r) for r in (3.0, 10.0, 30.0,
                                                              100.0)}

    # 5. 时序可行性（§8）：量级检查
    lat_lo, lat_hi = LATENCY_SITE23
    time_feas = {
        "e_write_reachable_old_rel_t_up": [e_lo, e_hi],
        "later_latency_range_steps": [lat_lo, lat_hi],
        "note": "the observation window must close after the latest valid "
                "later occurrence (t_on + latency_max + settle) AND the write "
                "must finish before e drops below the FET threshold "
                "(t_up + %d steps under the OLD non-causal drive). With "
                "latency up to %d steps the remaining settle+write budget is "
                "at most %d steps, minus the later stimulus onset offset. "
                "The causal drive (E-6) changes e; this budget is therefore "
                "OPEN until D1 re-measures e." % (e_hi, lat_hi,
                                                  e_hi - lat_hi),
        "T_clear_not_in_e_window": "clearing happens AFTER the write, so it "
                                   "costs cycle length (wall clock), not "
                                   "e-window budget",
    }

    # 6. 联合可行点示例（比值层面）：观察电压须在供电内
    # 神经元既有 vdd=2.0（mfs0_common build_* NeuronConfig）→ V_set ≤ 2.0；
    # 保持衰减允许 V_set·exp(−T_hold/τ_o) ≥ V_o,min。取保持衰减因子下限 h
    # （DESIGN 选择，τ_o ≥ T_hold/ln(1/h)）。
    vdd_neuron = 2.0
    h = 0.5
    vo_budget = vdd_neuron * h                      # V_o,min 上限
    rs_rl_min = pb / ((vo_budget - THETA_FET) * GM / V_REF)
    settle_budget_s = 0.100                         # DESIGN：≤100 步建立
    cs_max = settle_budget_s / (math.log(1 / ds) * rs_rl_min)
    joint = {
        "V_set_max_supply": vdd_neuron,
        "hold_decay_floor_h": h,
        "V_o_min_budget": vo_budget,
        "required_Rs_plus_RL_min": rs_rl_min,
        "settle_budget_s": settle_budget_s,
        "C_s_max_for_settle": cs_max,
        "tau_o_min_for_hold_T_s": "T_hold / ln(1/h) = %.3f·T_hold" % (
            1 / math.log(1 / h)),
        "reading": "a consistent point exists in ratio terms: R_S+R_L ≥ "
                   "%.0f (so that V_o,min ≤ %.1f V within a 2 V supply), "
                   "C_s ≤ %.2e so that the latest event settles within "
                   "100 steps, τ_o ≥ 1.44·T_hold, plus an active reset with "
                   "k ≈ 99 to clear as fast as it settles. Absolute values "
                   "remain OPEN until the causal e window fixes T_hold." % (
                       rs_rl_min, vo_budget, cs_max),
    }

    # 7. 墙钟估计（E-5）
    cycle_steps = {"T_obs": "OPEN", "T_write": "OPEN"}
    # 以 E0 量级给上界：一次经验 ≈ e 衰减至可忽略(≈3783 步 e>1e-3) + 清除
    per_exp_steps = 3783 + 2000
    wall = {"steps_per_experience_estimate": per_exp_steps,
            "basis": "E0 e>1e-3 tail (3783 steps rel. t_up, old drive) + a "
                     "2000-step clear/reset allowance",
            "us_per_step_E0": US_PER_STEP_E0,
            "sec_per_experience": per_exp_steps * US_PER_STEP_E0 * 1e-6,
            "D2_600_experiences_x8_streams_hours":
                600 * 8 * per_exp_steps * US_PER_STEP_E0 * 1e-6 / 3600,
            "note": "E0 single-circuit rate; E1 adds 3-4 nodes per step, so "
                    "expect 1.5-2x"}

    out = {
        "stage": "MFS0-E1 D0 feasibility (analytic only)",
        "rulings_2026-09-29": {
            "R-1": "independent copy = branch mfs0-e1 (worktree mfs0-e1), "
                   "from 4d4e424; mesquite-gecko read-only",
            "R-2": "independent finite reset branch is REQUIRED",
            "R-3": "complement gate: compare (a) reference subtraction vs "
                   "(b) inhibitory normally-on, choose by eps_alpha bound",
        },
        "design_budget": DESIGN,
        "E1_passive_single_node": {
            "plateau_bound_G_RsRL": pb,
            "min_Tclear_over_Tsettle": passive,
            "verdict": "passive load alone needs T_clear ≈ %.0f x T_settle; "
                       "adopt R-2 active reset" % passive,
        },
        "R2_active_reset_min_ratio_by_k": ratios,
        "R2_reading": "with reset conductance k·(1/R_L) during the reset "
                      "phase, the ratio drops as 1/(1+k); k≈99 brings it to "
                      "≈1 (clear as fast as settle). k is set by the reset "
                      "FET conductance, a DESIGN quantity with a physical "
                      "cost (reset drain current from the rail).",
        "E2_V_o_min_examples": vo_examples,
        "E2_reading": "V_o,min = θ + G_min·V_REF/gm; a small total load "
                      "resistance forces a large G_min and a V_o,min well "
                      "above 0.3 V, tightening the observation-hold "
                      "inequality V_set·exp(−T_hold/τ_o) ≥ V_o,min.",
        "E4_target_bias": {"dz_from_eps_alpha": dz_alpha,
                           "bound_delta_clear_plus_p1p_eps": dz_bound},
        "R3_complement_candidates": complement_candidates(ea - dp),
        "R3_choice": "(a) reference subtraction — equal first-order ε_α "
                     "bound to (b), and (b) requires a new non-primitive "
                     "normally-on element. Choose (a); keep (b) documented.",
        "timing_feasibility": time_feas,
        "joint_feasible_point_ratio_level": joint,
        "wall_clock": wall,
        "OPEN": ["e waveform under causal drive (E-6) → e write window, "
                 "T_obs upper bound", "R_S, R_L, C_s absolute values "
                 "(only their ratios are fixed here)", "observation "
                 "capacitor tau_o and V_set", "RC timer tau_T and threshold",
                 "reset FET conductance k", "V_H reference divider"],
        "D0_verdict": "FEASIBLE_IN_RATIOS_PENDING_CAUSAL_E",
    }
    path = os.path.join(DATA, 'd0_feasibility.json')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    print("MFS0-E1 D0 feasibility (analytic)")
    print(f"  plateau bound G(Rs+RL) >= {pb:.0f}")
    print(f"  passive min T_clear/T_settle = {passive:.1f}")
    for k, r in ratios.items():
        print(f"  active reset k={k:<3} -> min ratio {r:.2f}")
    print(f"  V_o,min examples: " + ", ".join(
        f"{k}: {v:.2f} V" for k, v in vo_examples.items()))
    print(f"  E-4 bias: dz(eps_alpha)={dz_alpha:+.4f}, bound={dz_bound:.4f}")
    print(f"  timing: e>theta window (old) {E_ABOVE_THETA_OLD}, later "
          f"latency {LATENCY_SITE23} -> margin <= {e_hi - lat_hi} steps")
    print(f"  wall: {wall['sec_per_experience']:.2f} s/experience; D2 "
          f"(8x600) ≈ {wall['D2_600_experiences_x8_streams_hours']:.2f} h "
          f"(x1.5-2 for E1)")
    print(f"  joint point: R_S+R_L >= {rs_rl_min:.0f}, C_s <= {cs_max:.2e}, "
          f"tau_o >= 1.44*T_hold, reset k~99")
    print(f"  verdict: {out['D0_verdict']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
