# MFS0-E1 执行计划（v3 方案落地版）

日期：2026-09-29  
方案来源：`J:/cell-cc/cell-cell/交叉比对/MFS0-E1贯通执行方案_v3_2026-09-29.md`（506 行，ADOPT）  
评判来源：`J:/cell-cc/cell-cell/交叉比对/MFS0-E1贯通方案v3评判_2026-09-29.md`（ADOPT with amendments）  
执行位置：`C:/Users/shaoc/AppData/Roaming/warp/Warp/data/worktrees/cell-cc/mfs0-e1`（worktree，分支 mfs0-e1）

---

## 零、前置完成项

| 阶段 | 内容 | 提交 | 状态 |
|:---|:---|:---|:---|
| D0 可行性分析 | 候选 P/R 按 ρ 择一；撤回"R-2 必需"；幅度约束 ρ≤0.85；判定 FEASIBLE_CANDIDATE_P_IN_RHO_RANGE | a108f9e | ✅ DONE |
| E0 修复 | Step D~H + hold6 + 终裁；生效终态 A_CONDITIONAL + HOLD_EXPOSURE（RULING-MFS0-R5） | adc3317→13265d1 | ✅ DONE |
| v3 评判 | 三项修订/补充（E-1 撤回、.git 偏离登记、双历史 later 路由设计要点） | 本文档 | ✅ DONE |

---

## 一、执行范围（v3 §1 + §7）

**贯通包：D0 → 实现 → 映射 → 封存 → 连续适应 → 双历史探针**

不再以"等待 D1"结束；阶段间自动推进，遇停止条件即停：
- 墙钟 4 h 耗尽（开发 60 / 主实验 120 / 双历史 45 / 余量 15 分钟）
- 可行域为空（联合约束无解）
- 修订次数用尽（最多两次结构修订）

---

## 二、六段工作（v3 §7 A~F）

### A. 建立副本、误差预算与成本草案（≤30 分钟）

**已偏离 v3 §6**：继续在 worktree `mfs0-e1`（共享 `.git/`），不导出独立副本。
- **原因**：adc3317/a108f9e 已在此分支；导出丢失历史。
- **保护**：mesquite-gecko 只读；所有写入限 mfs0-e1；Python 加 `-B`。
- **登记**：本偏离记录在 v3 评判、D0_DEVICE_DESIGN.md 追加节、本文档、memory。

**交付物**：
1. 源码来源清单（E0 提交号 + 原路径 + SHA）
2. 独立输出路径：`research/predictive_memory_v1/data/e1_*/`
3. 参数来源表（D0 冻结值 + 误差预算分配）
4. 运行记录格式（run_id / 调用次数 / 预算集合 / 内部子仿真）

**误差预算设计指标（v3 §7A）**：
- 映射后与固定目标参考的绝对状态偏差上界 ≤ 0.05
- 分配：δ_obs（观察）+ δ_comp（互补）+ tanh(β/4)（增益）+ ε_step（数值）
- 先设定，再分配；不得反向放宽

**成本草案**：
```
N_cycle ≈ ⌈(T_obs + T_write + T_clear + T_gap) / dt⌉
```
- 先解析估计，再用 pilot 短程测速（pilot 不转正式保留集）

### B. 联合设计与最小实现（≤60 分钟，含调试）

**优先候选 P**（D0 修订推荐）：ρ ∈ [0, 0.7]，被动负载，不加 R-2 复位支路。

**交付物**：
1. **完整状态表 + 两张节点连接图**：
   - 观察 / 互补 / 控制
   - 载体读出 / 双参考 / 写入
2. **节点方程、单位、供电、负载、输入与时序方程**
3. **约束共同可行域 + 一组候选参数**（来源标注）
4. **最小可运行器件实现 + 解析参考实现**（路径分离）

**设计要点（v3 §7B + 评判补充）**：
- 所有内部阈值触发、窗关闭、复位由状态动力学产生（禁止软件 `if history_id` 切换）
- 双向写入用 z、1−z；双参考为 V_lo−V_th、V_hi+V_th
- Memristor.update 的 dt 语义：包装器说明瞬时电流/积分电荷/载体增量，**只乘一次 dt**
- DEG-025（Memristor.update 缺 dt）：调用侧继续用 `current = I_write·dt` workaround

**双历史 later 路由设计（评判补充 §4.3）**：
- W1、W2 各自因果输入 → a1(t)、a2(t)
- 公共 later 输入 → 观察电容 V_o
- 结算时 P1 与 a1 合成 → W1 有效资格，P2 与 a2 合成 → W2 有效资格
- 各驱动独立 Memristor w1、w2（不共享）
- 禁止 `history_id` 索引 Python 对象

**三问审查（new-component skill 前置）**：
- Q1：生物学关联？（资格电容 / 观察态 / 持久载体）
- Q2：物理结构？（Sources → SynapticBundle → Targets，真实 Neuron 对象）
- Q3：参数推导？（τ、C、R、V_th 从约束求解，不手设）

### C. 短程映射（≤120 分钟，主实验时段）

**第一步：因果驱动重测 e 窗口**（D0 遗留 OPEN 项）
- 实现因果驱动适配器（E-6 要求）
- 重测 e 的写入可达窗（替代旧 [276, 2072]）
- 确定 T_obs、T_hold、τ_T 绝对值

**短程映射目标（v3 §7C）**：
- 固定 ρ（优先 0.5~0.7），测 8 个独立 p ∈ {0.1, 0.2, ..., 0.8}
- 每个 p：50~100 次经验（足够收敛到 ±0.02 稳态）
- 记录 z_final、学习率 α 实测、残差 ε_step
- 对比解析参考（相同 α）

**dt 三档检查（v3 §9）**：
- dt ∈ {1 ms, 0.5 ms, 0.1 ms}
- 只用于短程映射（验证数值误差）
- 正式采用最粗满足误差预算的一档

**停止条件**：
- 墙钟 120 分钟耗尽
- 短程映射完成（8 个 p × 50~100 次）

### D. 冻结 + 连续适应（≤45 分钟）

**冻结项（v3 §7D）**：
- 参数：ρ、R_S、R_L、C_s、C_o、τ_T、k_+、k_−、dt
- 误差界：δ_obs、δ_comp、β、ε_step
- 状态表、节点图、方程

**连续适应（v3 §7D，条件触发）**：
- 条件：短程映射发现某个 p 的偏差 > 0.05（超设计指标）
- 动作：燃烧期修正（L_burn = ⌈ln(0.05/0.6)/ln(0.95)⌉ = 49 次，α=0.05）
- 记录：燃烧前后 z 差异、是否进入稳态

**停止条件**：
- 墙钟 45 分钟耗尽
- 连续适应完成

### E. 双历史探针（≤45 分钟，条件满足时）

**条件（v3 §7E）**：
- 墙钟剩余 ≥ 45 分钟
- 短程映射 + 连续适应均 PASS
- 双历史 later 路由已实现（B 步骤）

**探针内容**：
- 两条历史 W1、W2，局部资格 a1(t)、a2(t)
- 公共 later 输入（观察电容 V_o）
- 验证：W1 与 later 绑定后 w1 变化，W2 与 later 绑定后 w2 变化
- 选择性：W1 绑定时 w2 不变，W2 绑定时 w1 不变

**停止条件**：
- 墙钟 45 分钟耗尽
- 双历史探针完成

### F. 汇总交付（≤15 分钟）

**交付物（v3 §7F）**：
1. 设计文档：状态表、节点图、方程、参数表
2. 实验报告：短程映射结果、误差分析、连续适应记录、双历史探针结果（如有）
3. 数据封存：run_id 级记录、SHA、preregistration.json
4. 代码提交：器件实现、适配器、实验脚本
5. 下一步建议：若未完成双历史，给出剩余工作量估计

---

## 三、预算与停止规则（v3 §8）

| 项 | 预算 | 累计 | 停止条件 |
|:---|:---|:---|:---|
| 墙钟 | 4 h | — | 耗尽即停 |
| 开发调试 | 60 min | 90 min | A+B 完成 |
| 主实验（短程映射） | 120 min | 210 min | C 完成 |
| 连续适应 | 45 min | 255 min | D 完成或跳过 |
| 双历史探针 | 45 min | 300 min | E 完成或跳过（条件不满足） |
| 汇总交付 | 15 min | 315 min | F 完成 |
| 余量 | 15 min | 240 min | 缓冲 |

**其他停止条件**：
- 可行域为空（联合约束无解）
- 修订次数用尽（最多两次结构修订）

---

## 四、记录格式（v3 §7A + D0 修订 §六.3）

### run_id 级记录
```json
{
  "run_id": "e1_short_mapping_p08_r001",
  "stage": "C_short_mapping",
  "p": 0.8,
  "n_cycles": 50,
  "z_initial": 0.1,
  "z_final": 0.793,
  "alpha_realized": 0.0487,
  "epsilon_step": 0.0023,
  "analytical_reference": 0.800,
  "deviation": -0.007,
  "invocation_count": {
    "circuit.step": 15000,
    "memristor.update": 50
  },
  "budget_consumed": {
    "n_experience_cycles": 1,
    "n_sub_simulations": 0
  },
  "wall_clock_seconds": 12.3,
  "timestamp": "2026-09-29T..."
}
```

### 预算集合字段
- `n_experience_cycles`：经验周期数（外层循环）
- `n_sub_simulations`：内部子仿真数（如有）
- 缺失次数记 `UNKNOWN`（不按 0 求和）

---

## 五、偏离登记（v3 §6）

| v3 要求 | 实际 | 原因 | 保护 |
|:---|:---|:---|:---|
| 不共享 Git 元数据 | 继续在 worktree mfs0-e1（共享 `.git/`） | adc3317/a108f9e 已在此分支；导出丢失历史 | mesquite-gecko 只读；所有写入限 mfs0-e1；Python `-B` |

---

## 六、下一步

按本计划执行 A → B → C → D → (E) → F，遇停止条件即停。

开工前必须：
1. Read BACKLOG.md，登记"⚡执行中"
2. 调用 **new-component** skill（新增组件前置）
3. mesquite-gecko `git status` 核查干净

完成后必须：
1. BACKLOG.md 移入"✅已完成"，填 commit hash
2. 调用 **work-report** skill（写报告）
3. 调用 **verify-regression** skill（回归验证）
