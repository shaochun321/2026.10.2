"""
MFS0-E1 可修正预测记忆器件——最小实现（阶段 B）

TYPE: SEMI
日期：2026-09-30
方案来源：v3 §7B + B_DEVICE_DESIGN.md
三问审查：通过

设计要点：
- 候选 P（被动负载，ρ=0.6）
- 双历史 later 路由（公共 V_o，独立 w1/w2）
- 禁止 history_id 索引 Python 对象
- DEG-025 workaround：调用侧乘 dt

BIO: 资格迹（τ_e=0.300s）+ 观察缓冲（T_obs=3.5s）+ 持久载体（Retention_w=1.0）
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nexus_v1.components.semiconductor import Capacitor, MOSFET, Memristor, PowerRail


class PredictiveMemoryDevice:
    """
    可修正预测记忆器件（MFS0-E1）

    双历史 later 路由：
    - W1: past_event_1 → a1(t) + later → p1 → w1
    - W2: past_event_2 → a2(t) + later → p2 → w2

    参数来源：
    - τ_e = 0.300 s（E0 实测）
    - T_obs = 3.5 s（写入可达窗中点 3500 步 × 1 ms）
    - ρ = 0.6（D0 推荐）
    - V_D = 2.0 V（PowerRail 默认）
    """

    def __init__(self, dt=0.001):
        """
        参数：
            dt: 仿真步长（秒），默认 1 ms
        """
        self.dt = dt

        # 候选参数（B_DEVICE_DESIGN.md §七）
        self.rho = 0.6
        self.V_D = 2.0
        self.V_H = (1 - self.rho) * self.V_D  # 0.8 V
        self.x = 99  # 平台精度

        self.R_S = 84.0  # 源电阻（Ω）
        self.R_L = 56.0  # 负载电阻（Ω）
        self.R_o = 700.0  # 观察电阻（Ω）
        self.R_a = 60.0  # 资格电阻（Ω，两个资格通道相同）

        self.C_s = 5.357  # 状态电容（F）
        self.C_o = 0.005  # 观察电容（F）
        self.C_a = 0.005  # 资格电容（F，两个资格通道相同）

        self.V_th = 0.3  # MOSFET 阈值（V）
        self.theta_settle = 0.5  # 结算门阈值（V）

        # 时间常数（验证）
        self.tau_on = self.R_L * self.C_s  # 0.300 s
        self.tau_off = (self.R_S + self.R_L) * self.C_s  # 0.497 s
        self.tau_o = self.R_o * self.C_o  # 3.5 s
        self.tau_a = self.R_a * self.C_a  # 0.300 s

        # 资格电容（双通道）
        self.cap_a1 = Capacitor(capacitance=self.C_a, charge=0.0)
        self.cap_a2 = Capacitor(capacitance=self.C_a, charge=0.0)

        # 观察电容（公共）
        self.cap_o = Capacitor(capacitance=self.C_o, charge=0.0)

        # 状态电容
        self.cap_s = Capacitor(capacitance=self.C_s, charge=0.0)

        # 持久载体（双通道）
        self.memristor_w1 = Memristor(
            w=0.1,  # z_init
            r_min=0.1,
            r_max=10.0
        )
        self.memristor_w2 = Memristor(
            w=0.1,
            r_min=0.1,
            r_max=10.0
        )

        # 供电
        self.power_rail = PowerRail(vdd=self.V_D)

        # 内部状态
        self.a1 = 0.0  # 资格1（V）
        self.a2 = 0.0  # 资格2（V）
        self.v_o = 0.0  # 观察态（V）
        self.v_s = 0.0  # 状态电容电压（V）
        self.p1 = 0.0  # 结算门1（V）
        self.p2 = 0.0  # 结算门2（V）
        self.w1 = 0.1  # 载体1
        self.w2 = 0.1  # 载体2

    def step(self, V_in1, V_in2, V_later, z_target):
        """
        单步推进

        参数：
            V_in1: W1 历史输入（V）
            V_in2: W2 历史输入（V）
            V_later: 公共 later 输入（V）
            z_target: 目标预测（0 或 1，决定写入方向）

        返回：
            dict: 当前状态快照
        """
        # 1. 资格电容充电（独立通道）
        # RC 电路：I_net = (V_in - V_cap) / R
        I_a1 = (V_in1 - self.cap_a1.voltage) / self.R_a
        self.cap_a1.inject(I_a1, self.dt)
        self.a1 = self.cap_a1.voltage

        I_a2 = (V_in2 - self.cap_a2.voltage) / self.R_a
        self.cap_a2.inject(I_a2, self.dt)
        self.a2 = self.cap_a2.voltage

        # 2. 观察电容充电（公共）
        I_o = (V_later - self.cap_o.voltage) / self.R_o
        self.cap_o.inject(I_o, self.dt)
        self.v_o = self.cap_o.voltage

        # 3. 状态电容动力学（候选 P：被动负载）
        # 当前简化：假设 V_in = V_D（充电）或 0（放电）
        # 完整实现需要根据 z_target 切换供电
        V_in_s = self.V_D if z_target == 1 else 0.0
        I_in_s = (V_in_s - self.cap_s.voltage) / self.R_S if V_in_s > 0 else 0.0
        I_out_s = self.cap_s.voltage / self.R_L
        I_net_s = I_in_s - I_out_s
        self.cap_s.inject(I_net_s, self.dt)
        self.v_s = self.cap_s.voltage

        # 4. 结算门（阈值触发）
        self.p1 = self.a1 if self.v_o > self.theta_settle else 0.0
        self.p2 = self.a2 if self.v_o > self.theta_settle else 0.0

        # 5. 写入电流（双参考，互补门）
        # 简化：只考虑 p1/p2 门控，忽略 FET_z0/z1 的详细建模
        I_write1 = self.p1 * (z_target - self.w1)  # 简化学习规则
        I_write2 = self.p2 * (z_target - self.w2)

        # DEG-025 workaround：调用侧乘 dt
        self.w1 += I_write1 * self.dt
        self.w2 += I_write2 * self.dt

        # 钳位到 [0, 1]
        self.w1 = max(0.0, min(1.0, self.w1))
        self.w2 = max(0.0, min(1.0, self.w2))

        # 6. 读出（简化：线性电导）
        y1 = self.w1  # G(w1) · V_read，假设 V_read=1
        y2 = self.w2

        return {
            'a1': self.a1,
            'a2': self.a2,
            'v_o': self.v_o,
            'v_s': self.v_s,
            'p1': self.p1,
            'p2': self.p2,
            'w1': self.w1,
            'w2': self.w2,
            'y1': y1,
            'y2': y2,
        }

    def reset(self):
        """重置所有状态"""
        self.cap_a1 = Capacitor(capacitance=self.C_a, charge=0.0)
        self.cap_a2 = Capacitor(capacitance=self.C_a, charge=0.0)
        self.cap_o = Capacitor(capacitance=self.C_o, charge=0.0)
        self.cap_s = Capacitor(capacitance=self.C_s, charge=0.0)

        self.memristor_w1 = Memristor(w=0.1, r_min=0.1, r_max=10.0)
        self.memristor_w2 = Memristor(w=0.1, r_min=0.1, r_max=10.0)

        self.a1 = 0.0
        self.a2 = 0.0
        self.v_o = 0.0
        self.v_s = 0.0
        self.p1 = 0.0
        self.p2 = 0.0
        self.w1 = 0.1
        self.w2 = 0.1


def analytical_reference(p, alpha, n_cycles, z_init=0.1):
    """
    解析参考（固定学习率 α）

    参数：
        p: 目标概率（0 到 1）
        alpha: 学习率
        n_cycles: 经验次数
        z_init: 初始状态

    返回：
        z_final: 最终状态
    """
    z = z_init
    for _ in range(n_cycles):
        # 简化学习规则：z ← z + α(target − z)
        # target 以概率 p 为 1，否则为 0
        # 期望：E[Δz] = α(p − z)
        z = z + alpha * (p - z)
    return z


if __name__ == '__main__':
    # pilot 测试
    device = PredictiveMemoryDevice(dt=0.001)

    print("MFS0-E1 可修正预测记忆器件 pilot 测试")
    print(f"参数：ρ={device.rho}, τ_on={device.tau_on:.3f}s, τ_off={device.tau_off:.3f}s")
    print(f"      τ_o={device.tau_o:.3f}s, τ_a={device.tau_a:.3f}s")
    print(f"      V_H={device.V_H:.3f}V, v_∞={device.V_H * device.x / (1+device.x):.3f}V")
    print()

    # 单次经验循环（W1 激活，later 输入）
    print("单次经验循环（5000 步 = 5 s）:")
    for t_step in range(5000):
        t = t_step * device.dt

        # W1 激活（前 1 s）
        V_in1 = 2.0 if t < 1.0 else 0.0
        V_in2 = 0.0  # W2 不激活

        # later 输入（1.5~4.5 s）
        V_later = 2.0 if 1.5 <= t < 4.5 else 0.0

        # 目标预测（p=0.8，随机采样简化为固定）
        z_target = 1

        state = device.step(V_in1, V_in2, V_later, z_target)

        if t_step % 1000 == 0:
            print(f"t={t:.1f}s: a1={state['a1']:.3f}, v_o={state['v_o']:.3f}, "
                  f"p1={state['p1']:.3f}, w1={state['w1']:.3f}")

    print()
    print(f"最终 w1={device.w1:.6f}, w2={device.w2:.6f}")
    print()

    # 解析参考
    z_ref = analytical_reference(p=0.8, alpha=0.05, n_cycles=1, z_init=0.1)
    print(f"解析参考（α=0.05, p=0.8, 1 次）: z={z_ref:.6f}")
    print(f"偏差：{device.w1 - z_ref:.6f}")
