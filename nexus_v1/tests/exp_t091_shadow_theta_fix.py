"""T-091: Shadow θ_M tau 对照验证（theta_m_tau 10000 对照 vs 1000 修复）

场景：复现 T-084（贴源饱腹 PH1=12k → 撤源 PH2=20k），唯一差异 = shadow 神经元 theta_m_tau。
判据：
- E0: 对照臂（τ=10000）必须复现 col calcium_rate 饱和（否则场景无效，判据不可用）
- E1: 修复臂 col 饱和率（rate>0.99）< 50%
- E2: 修复臂 shadow_to_da 峰值 < 对照臂峰值的 50%
机理观测（不参与判据）：col θ_m、enc→col 平均权重 — 检验"θ太慢→LTP不停→col饱和"链。

RESULT (2026-09-30): E0 FAIL — θ_m / w_ec / calcium_rate 双臂几乎一致，θ 链被证伪；
col 爬升归因 CRI 漏电 τ 量纲漂移。见 工作报告/DA-P1_shadow饱和根因_T091_2026-09-30.md。

REF: DA-P1 shadow饱和 / STDP修复方案补充_评判与实测修正_2026-07-08 §四 / T-084
"""
import sys
sys.path.insert(0, '.')

from nexus_v1.circuit.variant_adapter import VariantCircuit
from nexus_v1.components.world import HeatSource, Body, World

DT = 1.0
PH1 = 12_000
PH2 = 20_000
LOG = 2_000


def _build():
    src = HeatSource(position=[70.0, 50.0, 25.0], energy=500_000.0,
                     temperature=5.0, radius=30.0)
    src._drift = [0.0, 0.0, 0.0]
    body = Body(position=[10.0, 50.0, 25.0])
    world = World(heat_sources=[src], body=body)
    world.MIN_ALIVE = 0
    world.REGEN_PROB = 0.0
    c = VariantCircuit()
    c.world = world
    c.somatosensory.LATERAL_GAIN = 0.3
    for mn in c.motor_neurons.values():
        mn.config.output_gain = 0.1
    return c, world


def _shadow_da_current(c):
    tot = 0.0
    for b in getattr(c, 'bundles_shadow_to_da', []):
        cur = b.propagate()
        tot += sum(cur) if cur else 0.0
    return tot


def _enc_col_w(sb):
    ws = [m.w for bid, b in sb.bundles.items() if "enc_to_col" in bid
          for row in b._memristors for m in row]
    return sum(ws) / len(ws) if ws else float('nan')


def run_arm(tau):
    c, world = _build()
    tau_applied = False
    n_seen = -1
    peak_shdw = 0.0
    rows = []
    for step in range(1, PH2 + 1):
        if step == PH1:
            for s in list(world.heat_sources):
                if s.alive:
                    s.energy = 0.0
                    s.temperature = 0.0
        c.step({}, DT)
        sb = c.shadow_sandbox
        if sb._initialized and len(sb.neurons) != n_seen:
            # Per-neuron config override: only arm difference. Re-applied when
            # shadow grows (sprout/mitosis create neurons with the file default).
            for n in sb.neurons.values():
                n.config.theta_m_tau = tau
            n_seen = len(sb.neurons)
            tau_applied = tau_applied or step
        if sb._initialized and c._da_circuit_initialized:
            peak_shdw = max(peak_shdw, _shadow_da_current(c))
        if step % LOG == 0 and sb._initialized:
            cols = [n for nid, n in sb.neurons.items() if 'col' in nid]
            rates = [n.calcium_rate for n in cols]
            thetas = [n.config.theta_m for n in cols]
            sat = sum(1 for r in rates if r > 0.99)
            rows.append((step, sat, len(rates), max(rates), sum(thetas) / len(thetas),
                         _enc_col_w(sb), _shadow_da_current(c), c.dopamine.concentration))
    return tau_applied, peak_shdw, rows


def main():
    print("=" * 88)
    print("T-091: Shadow θ_M tau 对照（T-084 场景）")
    print("=" * 88)
    results = {}
    for tau in (10000.0, 1000.0):
        applied, peak, rows = run_arm(tau)
        if not applied:
            print(f"  ✗ τ={tau}: shadow 从未初始化，实验无效")
            return 2
        results[tau] = (peak, rows)
        print(f"\n[arm τ={tau:.0f}] tau applied at step {applied}")
        print(f"  {'step':>6}|{'sat':>6}|{'max_r':>6}|{'θ_m':>8}|{'w_ec':>7}|{'shdw':>7}|{'DA':>6}")
        for (s, sat, n, mr, th, w, sh, da) in rows:
            print(f"  {s:>6}|{sat:>2}/{n:<3}|{mr:>6.3f}|{th:>8.4f}|{w:>7.4f}|{sh:>7.3f}|{da:>6.3f}")
        print(f"  peak shadow_to_da = {peak:.3f}")

    peak_c, rows_c = results[10000.0]
    peak_f, rows_f = results[1000.0]
    sat_c = rows_c[-1][1] / rows_c[-1][2]
    sat_f = rows_f[-1][1] / rows_f[-1][2]

    print("\n[判据]")
    e0 = sat_c >= 0.5
    print(f"  E0 对照复现饱和: {sat_c*100:.1f}% ≥50% → {'PASS' if e0 else 'FAIL (场景不复现，E1/E2 无效)'}")
    e1 = sat_f < 0.5
    print(f"  E1 修复臂饱和率: {sat_f*100:.1f}% <50% → {'PASS' if e1 else 'FAIL'}")
    e2 = peak_c > 0 and peak_f < 0.5 * peak_c
    print(f"  E2 峰值比: {peak_f:.3f}/{peak_c:.3f} → {'PASS' if e2 else 'FAIL'}")
    ok = e0 and e1 and e2
    print("=" * 88)
    print(f"T-091: {'全部 PASS' if ok else '未通过'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
