"""
MFS0-E1 阶段 C：短程映射

目标：在 p ∈ {0.2, 0.5, 0.8}，r ∈ {0.95, 1.0, 1.05} 的 9 个点上，
     用三档 dt ∈ {0.001, 0.0025, 0.005} 各运行 50 次 Brier 评估，
     确定满足 δ_sim < 0.015 的最粗 dt。

预算：v3 §8 分配短程映射 ≤ 主实验预算（120 分钟）
风险：阶段 A 估算 11.5~23.0 h，超预算 5.75~11.5 倍

策略：
1. 先跑 pilot_speed_test：1 个点 × 3 档 dt × 50 次，测实际耗时
2. 根据实测外推全 9 点成本，判断是否继续
3. 若超预算 >2×，按 v3 §8 停止规则终止，交付 A+B

TYPE:INFRA
"""

import time
import numpy as np
from pathlib import Path
from predictive_memory_device import PredictiveMemoryDevice

# === 配置 ===
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DT_LEVELS = [0.001, 0.0025, 0.005]
P_GRID = [0.2, 0.5, 0.8]
R_GRID = [0.95, 1.0, 1.05]
N_TRIALS = 50
DELTA_SIM_THRESHOLD = 0.015  # δ_sim 上限（阶段 A 分配）

# 时间配置（秒）
T_WARMUP = 5.0       # 5s 预热期（past + later）
T_OBSERVE = 3.5      # 3.5s 观察期（τ_o）
T_SETTLE = 300.0     # 300s 结算期（τ_on）
T_TOTAL = T_WARMUP + T_OBSERVE + T_SETTLE


def generate_bernoulli_signal(p: float, T_total: float, dt: float, seed: int) -> np.ndarray:
    """
    生成伯努利脉冲序列

    参数：
        p: 发生概率
        T_total: 总时长（秒）
        dt: 时间步长（秒）
        seed: 随机种子

    返回：
        V(t)：电压序列，0.0 或 2.0 V
    """
    rng = np.random.RandomState(seed)
    n_steps = int(T_total / dt)
    events = rng.rand(n_steps) < p
    return events.astype(float) * 2.0  # 0 或 2V


def run_single_trial(p: float, r: float, dt: float, seed: int) -> dict:
    """
    单次试验：驱动器件，返回最终 z_pred 与解析期望

    参数：
        p: W1 发生概率
        r: W2/W1 比率
        dt: 时间步长
        seed: 随机种子

    返回：
        {
            'z_pred': float,  # 器件预测值（w1 - w2）
            'z_true': float,  # 解析期望（p - rp）
            'runtime': float  # 运行时间（秒）
        }
    """
    device = PredictiveMemoryDevice(dt=dt)

    # 生成信号
    V_in1 = generate_bernoulli_signal(p, T_TOTAL, dt, seed)
    V_in2 = generate_bernoulli_signal(r * p, T_TOTAL, dt, seed + 10000)

    # Later 固定：warmup 期间为 0，观察期为 2V，结算期为 0
    n_steps = len(V_in1)
    n_warmup = int(T_WARMUP / dt)
    n_observe = int(T_OBSERVE / dt)
    V_later = np.zeros(n_steps)
    V_later[n_warmup : n_warmup + n_observe] = 2.0

    # 驱动器件
    t_start = time.perf_counter()
    for i in range(n_steps):
        device.step(V_in1[i], V_in2[i], V_later[i], z_target=1)
    t_elapsed = time.perf_counter() - t_start

    # 读取结果
    z_pred = device.memristor_w1.w - device.memristor_w2.w
    z_true = p - r * p  # 解析期望

    return {
        'z_pred': z_pred,
        'z_true': z_true,
        'runtime': t_elapsed
    }


def compute_brier_score(predictions: np.ndarray, true_value: float) -> float:
    """
    计算 Brier 分数：均方误差

    参数：
        predictions: 预测值数组（N 次试验）
        true_value: 真实期望值

    返回：
        Brier 分数
    """
    return np.mean((predictions - true_value) ** 2)


def pilot_speed_test():
    """
    测速 pilot：在 (p=0.5, r=1.0) 上跑 3 档 dt × 50 次，
    外推全 9 点成本，判断是否继续。

    返回：
        {
            'dt_runtimes': {dt: runtime_sec},
            'projected_total_minutes': float,
            'continue': bool
        }
    """
    print("=" * 60)
    print("MFS0-E1 阶段 C：短程映射测速 pilot")
    print("=" * 60)
    print(f"测试点: p=0.5, r=1.0")
    print(f"dt 档位: {DT_LEVELS}")
    print(f"每档试验次数: {N_TRIALS}")
    print()

    dt_runtimes = {}

    for dt in DT_LEVELS:
        print(f"测试 dt={dt} ...")
        runtimes = []
        for trial in range(N_TRIALS):
            result = run_single_trial(p=0.5, r=1.0, dt=dt, seed=trial)
            runtimes.append(result['runtime'])

        avg_runtime = np.mean(runtimes)
        dt_runtimes[dt] = avg_runtime
        print(f"  平均单次耗时: {avg_runtime:.3f} s")

    # 外推全 9 点成本
    max_runtime = max(dt_runtimes.values())
    total_trials = len(P_GRID) * len(R_GRID) * len(DT_LEVELS) * N_TRIALS
    projected_seconds = total_trials * max_runtime
    projected_minutes = projected_seconds / 60

    print()
    print(f"外推全 9 点 × 3 档 dt × {N_TRIALS} 次:")
    print(f"  预计总耗时: {projected_minutes:.1f} 分钟")
    print(f"  预算上限: 120 分钟（主实验预算）")

    # 判断是否继续
    BUDGET_MINUTES = 120
    continue_mapping = projected_minutes <= 2 * BUDGET_MINUTES

    if continue_mapping:
        print(f"  ✓ 在 2× 预算内，继续执行")
    else:
        print(f"  ✗ 超预算 {projected_minutes / BUDGET_MINUTES:.1f}× > 2×，按 v3 §8 停止")

    print("=" * 60)
    print()

    return {
        'dt_runtimes': dt_runtimes,
        'projected_total_minutes': projected_minutes,
        'continue': continue_mapping
    }


def full_mapping():
    """
    完整短程映射：9 点 × 3 档 dt × 50 次

    返回：
        结果字典，存入 data/short_horizon_mapping.npz
    """
    print("=" * 60)
    print("MFS0-E1 阶段 C：完整短程映射")
    print("=" * 60)
    print(f"点阵: p={P_GRID}, r={R_GRID}（共 {len(P_GRID) * len(R_GRID)} 点）")
    print(f"dt 档位: {DT_LEVELS}")
    print(f"每点每档试验次数: {N_TRIALS}")
    print()

    results = {
        'p_grid': P_GRID,
        'r_grid': R_GRID,
        'dt_levels': DT_LEVELS,
        'n_trials': N_TRIALS,
        'brier_scores': {},  # {(p, r, dt): brier_score}
        'delta_sim': {},     # {dt: max_delta_sim_across_points}
        'selected_dt': None
    }

    for dt in DT_LEVELS:
        print(f"\n--- dt = {dt} ---")
        dt_brier_scores = []

        for p in P_GRID:
            for r in R_GRID:
                print(f"  (p={p}, r={r}) ", end='', flush=True)

                # 跑 N_TRIALS 次
                predictions = []
                for trial in range(N_TRIALS):
                    result = run_single_trial(p, r, dt, seed=trial)
                    predictions.append(result['z_pred'])

                # 计算 Brier 分数
                z_true = p - r * p
                brier = compute_brier_score(np.array(predictions), z_true)
                results['brier_scores'][(p, r, dt)] = brier
                dt_brier_scores.append(brier)

                print(f"Brier={brier:.6f}")

        # 当前 dt 的 δ_sim（最大 Brier）
        delta_sim_dt = np.max(dt_brier_scores)
        results['delta_sim'][dt] = delta_sim_dt
        print(f"  δ_sim(dt={dt}) = {delta_sim_dt:.6f}")

    # 选择满足 δ_sim < 0.015 的最粗 dt
    for dt in sorted(DT_LEVELS, reverse=True):  # 从粗到细
        if results['delta_sim'][dt] < DELTA_SIM_THRESHOLD:
            results['selected_dt'] = dt
            break

    if results['selected_dt'] is None:
        print(f"\n⚠ 警告：所有 dt 均不满足 δ_sim < {DELTA_SIM_THRESHOLD}")
        print(f"  最细档 dt={DT_LEVELS[0]} 的 δ_sim = {results['delta_sim'][DT_LEVELS[0]]:.6f}")
        print(f"  按 v3 §9 要求，需要更细的 dt 或放宽误差预算")
        results['selected_dt'] = DT_LEVELS[0]  # 默认最细
    else:
        print(f"\n✓ 选定 dt = {results['selected_dt']} (δ_sim = {results['delta_sim'][results['selected_dt']]:.6f})")

    # 存档
    output_file = DATA_DIR / "short_horizon_mapping.npz"
    np.savez(output_file, **results)
    print(f"\n结果已存: {output_file}")
    print("=" * 60)

    return results


if __name__ == "__main__":
    # 阶段 C.1：测速 pilot
    pilot_result = pilot_speed_test()

    # 阶段 C.2：根据测速结果决定是否继续
    if pilot_result['continue']:
        full_mapping()
    else:
        print("\n按 v3 §8 停止规则，短程映射终止。")
        print("交付阶段 A+B 成果，记录超预算原因。")

        # 记录停止原因
        stop_file = DATA_DIR / "C_STOPPED.txt"
        with open(stop_file, 'w') as f:
            f.write(f"MFS0-E1 阶段 C 停止记录\n")
            f.write(f"停止原因：短程映射测速 pilot 外推成本 {pilot_result['projected_total_minutes']:.1f} 分钟\n")
            f.write(f"超预算比例：{pilot_result['projected_total_minutes'] / 120:.2f}× > 2×\n")
            f.write(f"按 v3 §8：'可行域空/修订用尽/预算耗尽即停'\n")
            f.write(f"\n交付：阶段 A（误差预算）+ 阶段 B（器件设计 + 最小实现 + pilot）\n")
            f.write(f"提交：36bbe81\n")
        print(f"停止记录已写入: {stop_file}")
