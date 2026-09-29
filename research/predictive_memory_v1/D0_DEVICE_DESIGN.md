# MFS0-E1 D0 器件设计单

日期：2026-09-29 ｜ 分支/副本：`mfs0-e1`（R-1） ｜ 可行域计算：`d0_feasibility.py` → `data/d0_feasibility.json`
依据：`交叉比对/MFS0-E1下一阶段方案_器件设计与映射资格_2026-09-29.md` §3~§10、§9 D0 + `交叉比对/MFS0-E1方案评判_2026-09-29.md` E-1~E-6 + 用户裁定 R-1~R-3

> 本文件是**设计单**，不是实现。凡未推导出绝对值的参数一律标为 OPEN，不填数字。所有新组件属于 SEMI 候选，不主张已证实的生物学习机制（方案 §9 D0）。

## 一、状态表（完整列举，方案 §3）

| 状态 | 原语 | 充电来源 | 放电/复位路径 | 跨经验处理 |
|:---|:---|:---|:---|:---|
| e（资格） | Capacitor + R_e（E0 冻结 τ_e=0.3 s） | W 的**因果**驱动经 frozen bundle（E-6，新驱动） | 自然泄漏 R_e | 自然衰减；不复位 |
| V_T（计时） | Capacitor + 充电 FET | W 起始的因果支撑信号经 FET 从 PowerRail 充电 | 复位 FET（由结算结束触发） | 物理复位，残留入账 |
| V_o（观察） | Capacitor + R_o | later 本周期发生输入经 FET 置位 | R_o 泄漏 + 复位 FET（R-2） | 有限放电，不直接设零 |
| v（读出节点） | Capacitor C_s + 负载 R_L | 供电 V_D 经 R_S 与 G(V_o) 串联 | R_L 泄漏 + **独立复位支路**（R-2，k≈99） | 复位支路清除 |
| v_ref（互补参考） | 分压节点（与 V_D 同源） | V_D 分压 | — | 静态 |
| P（结算脉冲） | Capacitor + 双阈值 FET 对 | V_T 越上阈 | V_T 复位后放电 | 每周期一次 |
| w（载体） | Memristor（E0 同款） | J_dep / J_rec | 无（W_METABOLIC_LEAK=OFF） | **跨周期、跨阶段保持，禁止重建** |

## 二、节点图 1：观察 → 受供电约束的读出 → 互补门

```
later 输入 ──FET──▶ [V_o]──R_o──┐
                       │         ⏚
                       │ gate
         V_D ──R_S──[ G(V_o)=g_c(V_o−θ)₊ ]──▶ (v) ──R_L──⏚
                                               │  └──[复位FET, 导通 k/R_L]──⏚  ← P_reset
                                               C_s
  s  = v / V_H                  （y=1 支路门控）
  1−s = (v_ref − v)/V_H,  v_ref ≈ V_H = V_D·R_L/(R_S+R_L)   （R-3 路线 (a) 参考减法）
```

- 平台：G_min(R_S+R_L) ≥ 99（δ_plateau=0.01）
- 电导换算：g_c = gm/V_REF（沿用 RailLatch 路径 B 的写法，但**不继承其资格**）
- **R-3 选 (a)**：两候选的 ε_α 一阶上界相同（≈ε_ref+δ_plateau）；(b) 需要常通、可被关断的元件，仓库 MOSFET 只有增强型，得新建原语。(b) 的设计保留在 json 中。

## 三、节点图 2：载体 → 双参考 → 双向写入

```
I_0 ──▶ [Memristor w] ──▶ V_R = I_0·R(w)
          下参考 V_lo−V_th ─┐          ┌─ 上参考 V_hi+V_th
                            ▼          ▼
            u0' = V_R−(V_lo−V_th)    u1' = (V_hi+V_th)−V_R
                  │ FET_z0                 │ FET_z1        → 输出线性于 z / 1−z
  J_rec = g_r · a · (1−s) · u0      J_dep = g_d · a · s · u1
                  └────────┬───────────────┘
                     κ_m(J_dep − J_rec) → Memristor.w   （研究包装器：瞬时电流 × dt 一次）
  a = 资格门：FET_e(e) 与结算脉冲 P 的合成（同一 a 供两路，§2）
```

- **禁止**：下参考与上参考同向下移（复核意见 §5.2）；阈值补偿只用于 z / 1−z 状态因子，**不用于**资格门和发生检测门（它们依赖阈下截止）。
- **LIMITATION（继承 R-2 档位）**：a·s·u 的三因子合成在 Python 层仍是乘法，不是串联节点的自洽解。

## 四、可行域表（全部约束）

| 约束 | 条件 | D0 结果 | 状态 |
|:---|:---|:---|:---|
| 平台 | G_min(R_S+R_L) ≥ (1−δ_p)/δ_p | ≥ 99 | DERIVED |
| 平台 vs 清除（被动） | T_clear/T_settle ≥ 99·ln(1/δ_c)/ln(1/δ_s) | **99**，被动结构不现实 | 采纳 R-2 |
| 平台 vs 清除（复位 k） | 比值 ÷ (1+k) | k=49 → 1.98；k=99 → 0.99 | DESIGN k≈99 |
| 观察最低电压 | V_o,min = θ + G_min·V_REF/gm | R_S+R_L=3 → 33 V（不可行）；=141 → 1.0 V | 需 R_S+R_L ≥ 141 |
| 供电内保持 | V_set·e^{−T_hold/τ_o} ≥ V_o,min，V_set ≤ vdd=2.0 | 取 h=0.5 → τ_o ≥ 1.44·T_hold | T_hold OPEN |
| 建立 | 最晚事件 ln(1/δ_s)·C_s·(R_S+R_L) ≤ 100 步 | C_s ≤ 1.54e-4 | DERIVED |
| 观察窗 | T_source+L_trans+T_settle+T_margin < T_obs | 潜伏期 521~637 步（NF-1 漂移） | OPEN（因果 e） |
| 资格窗 | T_obs + T_write < T_e,reachable | 旧驱动 e>θ 为 [276, 2072]，扣潜伏期后余量 ≤ 1435 步 | **OPEN：须因果驱动重测** |
| 复位残留 | v_res ≤ δ_c·V_H | δ_c = 0.01 | DESIGN |
| 两路失配 | ε_α ≤ 0.05 | Δz\* = +0.0081（p=0.8）；合成界 0.018 | DESIGN |
| 墙钟 | 每次经验步数 × 33 μs/步 | ~0.19 s/次；D2 8×600 ≈ 0.26 h（E1 ×1.5~2） | 估计 |

**D0 判定：`FEASIBLE_IN_RATIOS_PENDING_CAUSAL_E`**。在比值层面存在一组相容的解；绝对值依赖因果驱动下的 e 窗口（E-6），只能在 D1 第一步测量后确定。

## 五、逐元件三问

| 元件 | Q1 对应物 | Q2 结构（原语 / 连接） | Q3 参数依据 |
|:---|:---|:---|:---|
| 因果输入适配器 | 感觉通路只传递已到达的信号 | research 层适配器：只输出"支撑是否存在"或"固定标称时长归一"，不读 t_rearm | 标称时长取 E0 已录窗的中位长度（639 步，已冻结素材），不按轨迹个别调整 |
| 观察电容 V_o | 突触后 Ca²⁺ 短时积累（亚秒至秒级） | Capacitor + R_o；置位 FET 由 later 输入驱动；复位 FET | τ_o ≥ 1.44·T_hold（由保持不等式推出）；T_hold OPEN |
| 读出节点 v | 受限电源的放大级（SEMI；无直接生物对应，登记为工程元件） | V_D–R_S–G(V_o)–(v)–R_L，C_s | R_S+R_L ≥ 141、C_s ≤ 1.54e-4（DERIVED）；V_D 取 neuron vdd=2.0（FROZEN） |
| 复位支路 | 抑制性分流（shunting） | FET 并联 R_L，由结算结束脉冲驱动 | k≈99（DESIGN，代价是复位期间的漏电流，计入能量账） |
| 互补参考 v_ref | —（SEMI 工程元件） | 与 V_D 同源的分压 | 分压比 = R_L/(R_S+R_L)，与平台同式；失配计入 ε_α |
| RC 计时 + 结算脉冲 | 周期性采样窗 | Capacitor 充电 + 双阈值 FET 对（上阈开窗、下阈关窗）；**不用** `if t==t_c` | τ_T、阈值 OPEN；须满足 T_obs 两不等式 |
| 状态因子 FET_z0/z1 | — | 双参考（V_lo−V_th / V_hi+V_th）+ MOSFET 原语 | V_th=0.3（FROZEN）；I_0 使 V_Z=I_0·9.9 落在供电内 |
| 写入包装器 | 三因子可塑性（资格 × 结果 × 状态） | Memristor.w，瞬时电流 × dt 只乘一次 | κ_m、g_d=g_r 由目标 α 反推（方案 §2：先定适应次数，再推 η） |

**复用检查（new-component Step 0）**：`compensation.py` 里没有观察/平台读出/复位功能的组件。仓库中唯一带迟滞的实现是 `variant_adapter.py` 的 DwellSensor Schmitt，它使用 Python 布尔状态（`_dwell_is_discharging`），不能作为物理结算脉冲的先例。PhysicalEntryGate 的 Zener 钳位与 t_open=τ·ln(V_H/θ) 可作为时序推导的先例，但其资格不转移（方案 §3）。

## 六、交给 D1 的第一步

1. 实现因果驱动适配器，**重测 e 的写入可达窗**，据此确定 T_obs、T_hold、τ_T 的绝对值（消除全部 OPEN 项中的时间量）。
2. 按上表比值取一组绝对值，冻结后再做方案 §9 D1 检查表的全部八项。
3. 调用次数、预算集合、内部子仿真分字段记录；缺失的次数记 UNKNOWN，不按 0 求和（复核意见 §3.2）。
