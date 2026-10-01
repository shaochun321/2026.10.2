# MFS0-E1 v4 器件设计（阶段 B）

代码：`device.py`（TYPE:SEMI）、`sim.py`（生成器与连续运行）、`e1_common.py`（输入换能）。
原语：`Capacitor / MOSFET / Memristor / PowerRail`，来自 4d4e424，未作修改。

## 1. 原语 API 清单（按源码实际核对）

| 原语 | 本设计用到的接口 | 需要注意的点 |
|:--|:--|:--|
| Capacitor | `voltage`、`inject(I, dt)`（KCL 账本） | `leak` 未使用：所有节点由 `relax()` 精确积分，再经 `inject` 记账 |
| MOSFET | `conduct(v)` = gm·(v−Vth)₊ | 阈下严格为 0（DEG-019），本设计的开关和门都依赖这一点 |
| Memristor | `resistance`、`update(current, pre, post)` | `update` 缺 dt（DEG-025），调用侧传 I·dt，dt 只乘一次 |
| PowerRail | `vdd`、`r_internal` | 各支路按戴维南源 (vdd, r_int) 串联求解 |
| RelationEventAdapter + PhysicalEntryGate | `step(θ, dt)` → spike → b↑ | 默认参数；每条输入路径一个实例，同一试验内不重建 |

## 2. 状态表

| 状态 | 物理对象 | 单位 | 初态（仅试验开始时设定） | 动力学 |
|:--|:--|:--|:--|:--|
| 换能器 W_i、L 的隐状态 | adapter 膜、collector 膜、entry gate 电容 | V | 构造默认值 | 生产代码，每 tick 推进 |
| T_i 计时/资格 | Capacitor C_T = 1e-5 F | V | 0 | C_T·Ṫ = G_set(b_Wi)·(V_D−T) − T/R_T |
| O 观察 | Capacitor C_o = 1e-5 F（全体历史共用） | V | 0 | C_o·Ȯ = G_setO·(V_D−O) − O/R_o − G_rst·O |
| w_i 持久载体 | Memristor（r_min=0.1，r_max=10） | 1 | w0 | ẇ = ½(I_dn − I_up)（经 `update`） |
| 能量账 | 累加器 | J | 0 | 只记账，不参与动力学 |

外部只提供 θ_W(t)、θ_L(t) 两条模板驱动。没有软件标志、计数器或 history_id 进入 `step()`。

## 3. 节点图

**观察与控制**

```
θ_Wi ─▶ Transducer ─▶ b_Wi ─▶ SW(gm_sw·b)──r_int──V_D ─▶ T_i ──R_T──⊥
θ_L  ─▶ Transducer ─▶ b_L  ─▶ SW(b_L) ─ Σ_i FET(T_i − 0.7) ─ r_int ─ V_D ─▶ O ──R_o──⊥
                                               O ── Π_i FET(0.6 − T_i)（串联复位）──⊥
settle_i = FET(T_i) ⊕ FET(1.3 − T_i)（串联）  ⇒ 仅在 θ_lo=0.3 ≤ T_i ≤ θ_hi=1.0 时导通
```

**写入与读出**

```
V_W ─ r_int ─ settle_i ─ FET(O)       ─ FET_z(V_hi+Vth−V_Ri) ─ R(w_i) ─▶ I_up,i （z 增）
V_W ─ r_int ─ settle_i ─ FET(V_D−O)   ─ FET_z(V_Ri−V_lo+Vth) ─ R(w_i) ─▶ I_dn,i （z 减）
V_W ─ R_s ─ R(w_i) = V_Ri；参考复制 V_lo = V_W·r_min/(R_s+r_min)，V_hi = V_W·r_max/(R_s+r_max)
read: Σ_i FET(T_i − 0.7) ⊕ FET_p(V_Ri − V_lo + Vth) ─▶ I_pred；p̂ = I_pred / I_fs（构造时常数）
```

"FET(x − c)" 表示栅极接理想差分节点（L1），差分电平取常数 c：
- 取 Vth 做补偿时，导通值即 gm·(v − ref)₊；
- θ_hi 方向的差分电平取 θ_hi − Vth，θ_lo 方向取 θ_lo + Vth。

## 4. 参数与来源

| 参数 | 值 | 依据 |
|:--|:--|:--|
| V_D、r_int | 2.0 V、0.1 Ω | E0 神经元 vdd = 2.0；PowerRail 默认 r_internal |
| Vth、θ_lo | 0.3 V | MOSFET 原语默认值，零自由参数 |
| θ_hi | 1.0 V | 观察窗 τ_T·ln(V_D/θ_hi) = 1.04 s；d_L 最晚 0.80 s，入口仍在窗内，余量 0.24 s |
| τ_T | 1.5 s | 同时满足三项：观察窗覆盖 d_L；结算长度 τ_T·ln(θ_hi/θ_lo) = 1.806 s；周期 4 s 内留出 1.05 s 空闲供 O 复位。BIO：行为时间尺度的资格迹为秒级（Gerstner et al. 2018 Front Neural Circuits 12:53；Yagishita et al. 2014 Science 345:1616 测得 0.3–2 s）。**不沿用 E0 的 τ_e = 0.3 s**：资格必须持续到观察窗关闭之后（方案 §3"未发生只能在窗口关闭后形成反向写入"） |
| τ_o | 30 s | O 须在结算结束前一直高于 V_D − Vth = 1.7（否则反向门误开）。最长保持约 2.75 s ⇒ τ_o ≥ 2.75/ln(2/1.7) = 16.9 s；取 30 s。实测结算末 O = 1.84 |
| C_T、C_o | 1e-5 F | 置位 RC ≈ μs，远小于 dt/4，一个 tick 的脉冲即可饱和；置位量与脉冲宽度无关（dt 稳健性的前提） |
| gm_sw | 10 S/V | 开关电导远大于写支路电导，串联时对 α 的影响可忽略 |
| gm_rst | 1e-2 S/V | 空闲期 ∫G_rst dt / C_o ≫ 9；实测周期末 O ≤ 5e-39 |
| R_s、V_W | 990 Ω、100 V | 测阻近恒流：读出非线性 ≤ 0.25%；R(w) ≤ 10 Ω 只占写支路电阻 1/(gm_z·ΔV) 的约 1.2% |
| gm_z | 1.1787e-3 S/V（推导） | α⁰ = 1 − exp(−½·V_W·gm_z·ΔV·T_settle)，其中 ½ 来自 `Memristor.update` 的 0.5 |
| α⁰ | 0.10 | 适应速度：均值动力学从 0.6 降到 0.05 需 24 次，短于每阶段 60 次中评价窗之前的 30 次 |
| gm_p、V_read | 1e-3、1 V | 读出标度；p̂ 以构造时算好的 I_fs 归一，与状态无关 |

**联合可行域**：以上约束同时成立；阶段 C 实测给出误差界 0.018（目标 0.05）。

## 5. 映射关系（由节点方程推出，没有写死目标式）

结算期内只有一侧支路导通：
- y = 1（O 已置位）：只有 UP 支路导通，ż ≈ ½·V_W·gm_z·ΔV·(1 − z)；
- y = 0（O 保持为 0）：只有 DOWN 支路导通，ż ≈ ½·V_W·gm_z·ΔV·z。

因此 b = k₊s₊ + k₋s₋，q = s₊ ∈ {0, 1}，每周期 α = 1 − exp(−∫ab dt)。
- q 的精确性来自参考端：V_R 等于 V_hi 或 V_lo 时，对应 FET 的导通值恰好为 0。
- α 的偏差来自三处：R(w) 串联、测阻非线性、开关电导有限。
- 阶段 C 实测：α ∈ [0.0988, 0.0996]，δ_q = 2.0e-3，仿射残差 ≤ 4.3e-4。

## 6. 登记的理想化与限制

- L1：差分节点为理想单位增益，输入阻抗无穷、无摆幅限制。
- L2：每条支路单独按"戴维南源 + 串联电导"求解，并联支路之间不互相加载供电轨。
- L3：Memristor 无读扰物理，读电流不写入。"读不扰动载体"是这个原语的前提，不是测出来的结果。
- L4：`MOSFET.conduct(v)` 按 V_REF = 1 V 当作电导使用。
- L5：乘法组成属 TIER-2（与 E0 的 `TIER2_LIMITATION` 同族）：各因子由器件产生，写电流是串联电导链的解，但差分节点是理想的。
- L6：能量账是近似记账，不参与守恒检验。
- L7：DEG-025 在调用侧补 dt，沿用 E0 的 WRITE_DT_CORRECTION 先例。
- 未实现：自动结构生长、重叠历史的信用分配、DA/STDP/CPC 闭环。

## 7. 与旧分支实现的关系

mfs0-e1 分支上的 `predictive_memory_device.py`（36bbe81）有四处违反 v4，本设计不复用其代码：
- 把 `z_target` 直接传进器件（违反 §3）；
- 结算用 Python `if` 实现；
- 把目标更新式直接写进载体（违反 §4.2）；
- Memristor 对象创建了但没有使用。

该分支的可行域推导（D0、ρ）适用于它自己的读出节点模型，与本设计的节点不同，也不沿用。
