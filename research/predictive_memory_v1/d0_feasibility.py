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


def passive_clear_settle_ratio_exact(x, rho):
    """v3 §3.1：精确比值 τ_off/τ_on = (1+x)/(1+ρx)，ρ=R_S/(R_S+R_L)。

    旧 E-1 隐含假设 ρ=0（R_S=0），只在该特殊情况下才有"普遍 99 倍"。
    """
    return (1 + x) / (1 + rho * x)


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

    # 1. 被动结构（v3 §3）：精确比值与幅度约束联合可行域
    # 要求：(a) τ_off/τ_on ≥ 分段比值下界（建立/清除都有各自残差要求）
    #       (b) v_∞ = V_H·x/(1+x) ≥ θ_FET（下游状态门可驱动）
    # 其中 V_H = (1−ρ)V_D，x = G(R_S+R_L)，ρ = R_S/(R_S+R_L)
    vdd = 2.0  # V_D，供电
    x_platform = pb  # x ≥ 99（平台精度）

    # 分段检查：T_clear 由零初态清到 v_off，T_settle 由 v_prev 建立到残差 δ_s
    # 建立残差相对定常值 δ_s，清除残差相对高压 v_off/V_H = δ_c
    # 精确比值：T_clear_req/T_settle_req = ln(v_prev/v_off) / ln(1/δ_s)
    # 保守取 v_prev=V_H（最大前值），v_off=δ_c·V_H
    ratio_req = math.log(1 / dc) / math.log(1 / ds)  # 约 4.6（δ_s=δ_c=0.01）

    passive_analysis = {}
    rho_test = [0.0, 0.1, 0.3, 0.5, 0.7, 0.85, 0.90, 0.95, 0.99]
    for rho in rho_test:
        tau_ratio = passive_clear_settle_ratio_exact(x_platform, rho)
        v_h = (1 - rho) * vdd
        v_inf = v_h * x_platform / (1 + x_platform)
        feasible = tau_ratio >= ratio_req and v_inf >= THETA_FET
        passive_analysis[f"rho={rho:.2f}"] = {
            "tau_off_over_tau_on": round(tau_ratio, 3),
            "V_H": round(v_h, 3),
            "v_inf": round(v_inf, 3),
            "feasible": feasible,
        }

    # 可行 ρ 上界：v_inf ≥ 0.3 V => (1−ρ)·2.0·0.99 ≥ 0.3 => ρ ≤ 0.8485
    rho_max_amplitude = 1 - THETA_FET / (vdd * x_platform / (1 + x_platform))

    passive_verdict = (
        f"Candidate P (passive load, no reset) is FEASIBLE for ρ ∈ [0, "
        f"{rho_max_amplitude:.2f}]. At ρ=0 (R_S=0, my E-1 assumption), "
        f"τ_off/τ_on={passive_clear_settle_ratio_exact(x_platform, 0):.0f}; "
        f"at ρ={rho_max_amplitude:.2f} (amplitude limit), "
        f"τ_off/τ_on={passive_clear_settle_ratio_exact(x_platform, rho_max_amplitude):.1f}. "
        f"Both exceed the required ratio {ratio_req:.1f}. "
        f"Candidate R (R-2 active reset) is needed only when ρ > "
        f"{rho_max_amplitude:.2f} or when v_inf must be < 0.3 V but still "
        f"drive a next-stage amplifier (not in this round)."
    )

    # 2. R-2 独立复位支路：给定可用时间比，所需 k
    # 复位期间并联 G_reset，τ_clear = C_s·(R_L‖R_r) = C_s·R_L/(1+k)，
    # k = G_reset·R_L。若要 τ_clear = τ_settle，则 k = τ_off/τ_settle − 1。
    # 在 ρ 接近 1 时（被动比值已接近 1），k 接近 0；在 ρ=0 时，k ≈ 99。
    ratios = {}
    for k in (0, 9, 49, 99, 199):
        ratios[k] = active_reset(dp, ds, dc, k)

    reset_note = (
        f"With reset conductance k·(1/R_L) during the reset phase, "
        f"τ_clear/(1+k) ≈ τ_settle. At ρ=0 (R_S=0), τ_off/τ_on=100, so k≈99 "
        f"brings the ratio to ≈1. At ρ={rho_max_amplitude:.2f}, the passive "
        f"ratio is already {passive_clear_settle_ratio_exact(x_platform, rho_max_amplitude):.1f}, "
        f"so k can be much smaller or zero."
    )

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
    e_lo, e_hi = E_ABOVE_THETA_OLD
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
        "v3_ruling_2026-09-29": "v3 评判 ADOPT with amendments",
        "deviation_from_v3_sec6": {
            "v3_requires": "independent copy without shared Git metadata",
            "actual": "worktree mfs0-e1 (branch mfs0-e1), shares .git/ with "
                      "J:/cell-cc",
            "reason": "adc3317/a108f9e (E0 fix + D0) already in mfs0-e1; "
                      "exporting to new location loses commit history",
            "protection": "mesquite-gecko working directory remains read-only; "
                          "all writes go to mfs0-e1; Python run with -B",
        },
        "design_budget": DESIGN,
        "passive_load_exact_analysis": {
            "formula": "tau_off/tau_on = (1+x)/(1+rho*x), rho=R_S/(R_S+R_L)",
            "x_platform": x_platform,
            "ratio_required": ratio_req,
            "rho_analysis": passive_analysis,
            "rho_max_for_amplitude": rho_max_amplitude,
            "verdict": passive_verdict,
        },
        "E1_withdrawn": "my E-1 '99x universal' assumed rho=0 (R_S=0), not "
                        "general; v3 §3 corrects this",
        "R2_active_reset_min_ratio_by_k": ratios,
        "R2_note": reset_note,
        "R2_updated_ruling": "R-2 active reset is OPTIONAL, not required. Use "
                             "candidate P (passive, no reset) when rho <= %.2f; "
                             "use candidate R (with reset) when rho > %.2f or "
                             "other constraints force it." % (rho_max_amplitude,
                                                              rho_max_amplitude),
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
        "D0_verdict": "FEASIBLE_CANDIDATE_P_IN_RHO_RANGE",
    }
    path = os.path.join(DATA, 'd0_feasibility.json')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    print("MFS0-E1 D0 feasibility (analytic, v3-corrected)")
    print(f"  E-1 withdrawn: my 99x assumed rho=0, not general")
    print(f"  Exact formula: tau_off/tau_on = (1+x)/(1+rho*x)")
    print(f"  Platform bound x >= {x_platform:.0f}, ratio required {ratio_req:.1f}")
    print(f"  Passive load (candidate P):")
    for rho_val in [0.0, 0.3, 0.5, 0.7, rho_max_amplitude]:
        info = passive_analysis[f"rho={rho_val:.2f}"]
        status = "FEASIBLE" if info["feasible"] else "out"
        print(f"    rho={rho_val:.2f}: ratio={info['tau_off_over_tau_on']:.1f}, "
              f"v_inf={info['v_inf']:.2f} V -> {status}")
    print(f"  Candidate P feasible for rho <= {rho_max_amplitude:.2f}")
    print(f"  Active reset (candidate R) k-values:")
    for k, r in ratios.items():
        print(f"    k={k:<3} -> min ratio {r:.2f}")
    print(f"  E-4 bias: dz(eps_alpha)={dz_alpha:+.4f}, bound={dz_bound:.4f}")
    print(f"  V_o,min examples: " + ", ".join(
        f"{k}: {v:.2f} V" for k, v in list(vo_examples.items())[:3]))
    print(f"  joint point: R_S+R_L >= {rs_rl_min:.0f}, C_s <= {cs_max:.2e}, "
          f"tau_o >= 1.44*T_hold")
    print(f"  wall: {wall['sec_per_experience']:.2f} s/exp; D2 (8x600) "
          f"≈ {wall['D2_600_experiences_x8_streams_hours']:.2f} h (x1.5-2 for E1)")
    print(f"  verdict: {out['D0_verdict']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
