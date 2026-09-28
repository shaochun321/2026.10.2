# nexus_v1 降级追踪注册表 (Degradation Registry)

> **格式说明**: 见 RULES.md 原则 6
>
> **路径迁移说明（2026-09-06）**: `nexus_v1/generators|relations|events` 已整体
> 迁至顶层 `tss/`（纯搬迁，零改名零重构，见 `tss/README.md` 映射表）。以下
> 历史条目中的旧路径按该映射对应。
>
> **编号分叉已解决（2026-09-07，用户裁定重编号）**: 原与
> `nexus_v1/docs/degradation_registry.md` 的 DEG-015/016 编号冲突已解决——
> nexus_v1 版两条重编号为 DEG-022/DEG-023（含代码/文档引用同步）。
> **本文件是权威编号空间**（DEG-001~021 + LIM）；两份注册表后续新增
> 条目统一从 DEG-024 起顺延、先互查避让。

---

### DEG-001: MET 信号无法到达 HairCell (信号深度 1/6)
- **发现时间**: 2026-05-21
- **现象**: MET activation > 0, haircell activation = 0, signal_depth = 1/6
- **影响层**: HairCell, Afferent, Encoding, Column, Motor (全链路)
- **根因**: 多重因素:
  - tau_gate 单位不匹配 (5.0 实际 = 5000 steps)
  - Ca²⁺ 反转电位问题 (vm > E_Ca 后电流反转)
  - pre_trace 正反馈爆炸
- **状态**: FIXED
- **修复**: FIX-001, FIX-002, FIX-003, FIX-004

---

### DEG-002: 能量耗竭导致链路中断
- **发现时间**: 2026-05-22
- **现象**: 所有神经元 energy → 0.001，信号深度在 6/6 ↔ 4/6 振荡
- **影响层**: Column (主要), Motor, Encoding
- **根因**: metabolic_recovery (0.001) << 平均耗散 (30.32)，亏缺比 30322:1
- **状态**: FIXED (Encoding/Column), PARTIAL (Motor)
- **修复**: FIX-006 (P0 + VoltageRegulator)
- **备注**: Encoding energy 从 0.001 恢复到 12.0; Motor 仍耗尽 → DEG-009

---

### DEG-003: Column 电压跳变 (0 ↔ 6)
- **发现时间**: 2026-05-22
- **现象**: Column activation 在 0 和 ~6 之间跳变而非平滑
- **影响层**: Column → Motor
- **根因**: τ_RC(Column) = 3 ms << ISI(Afferent) = 80 ms；
  两次脉冲之间完全衰减（保留率 0%）
- **数学证明**: e^(-80/3) ≈ 2.7 × 10^{-12} ≈ 0
- **状态**: FIXED
- **修复**: FIX-006 (P0: τ_RC 增至 240ms, 保留率 72%)
- **验证**: Column activation 稳定在 10.98，不再跳变

---

### DEG-004: 传入放电率偏低
- **发现时间**: 2026-05-22
- **现象**: Regular afferent 12.5 Hz，生物目标 50-100 Hz
- **影响层**: Afferent → Encoding (信号驱动不足)
- **根因**: HC release_rate ≈ 0.01，HC→Aff synapse_gain = 80，
  导致充电速率 dV/dt = 0.048 × 80 × 0.001 / 0.5 = 0.0077/step。
  ISI = V_span / dV = (0.23 - 0.077) / 0.0077 ≈ 20 steps (50 Hz)。
  实测 80 steps 因为 release_rate 不稳定。
- **状态**: OPEN
- **修复**: 待分析

---

### DEG-005: Motor 放电过快
- **发现时间**: 2026-05-22
- **现象**: Motor 665 spikes / 3500 ms ≈ 190 Hz，生物最大约 200 Hz
- **影响层**: Motor
- **根因**: 下游增益链过强 (Enc→Col→Motor 多级放大)
- **状态**: SUPERSEDED by DEG-008
- **修复**: 补偿机制改变了行为模式

---

### DEG-006: NaN 在 Encoding 层传播
- **发现时间**: 2026-05-21
- **现象**: Encoding activation 爆炸到 10^255 → NaN
- **影响层**: Encoding → Column → Motor
- **根因**: MOSFET conduct(vm) 在高 vm 下线性增长无上限
- **状态**: FIXED
- **修复**: FIX-005 (activation clamp ±10)

---

### DEG-007: STDP 权重不演化
- **发现时间**: 2026-05-22
- **现象**: HC→Aff 权重 0.8000 不变, Enc→Col 权重 0.1500 不变
- **影响层**: 全链路 (学习不发生)
- **根因**: 待分析 — 可能是 pre_trace/post_trace 衰减过快
  或 stdp_lr 过小相对于 trace 幅度
- **状态**: OPEN
- **修复**: 待分析

---

### DEG-008: Motor 偏置自发放电过多
- **发现时间**: 2026-05-22
- **现象**: Motor 375/458 脉冲 (82%) 来自偏置电流驱动的自发放电，
  不是信号驱动。在传入信号到达前 (t<1500) 就已产生 375 spikes。
- **影响层**: Motor
- **根因**: bc_current=0.01 对 Motor (C=1, R=5) 过大，
  V_ss = 0.01/0.5 × 5 = 0.1，接近 v_peak=0.3 的 33%。
  加上 AGC base_gain=5 × bias 被放大。
- **状态**: OPEN
- **修复**: 待分析 — 可降低 Motor bc_current 或关闭 Motor AGC

---

### DEG-009: Motor energy 仍耗尽
- **发现时间**: 2026-05-22
- **现象**: Motor energy = 0.003 (几乎归零)
- **影响层**: Motor
- **根因**: 多重因素:
  1. Motor VR max_rate=3.0 不足以覆盖高频 spiking 耗散
  2. Binding layer activation 指数爆炸 (DEG-013) → heat=1000
- **状态**: FIXED
- **修复**: FIX-014 (VR 重校准 + 稳态调节), FIX-015 (Binding 饱和)

---

### DEG-010: 热耗散偏高
- **发现时间**: 2026-05-22
- **现象**: 总热耗散 1180 (主要来自偏置驱动的无信号放电)
- **影响层**: 全系统
- **根因**: 补偿机制增加了活跃神经元数 (19-20)，每个都在消耗能量
- **状态**: OPEN
- **修复**: 待分析 — 可能是正常代价

---

### DEG-011: MET 能量耗尽
- **发现时间**: 2026-05-22 (契约验证发现)
- **现象**: MET energy = 0.001 (C1 契约要求 > 0.5)
- **影响层**: MET
- **根因**: MET 无 VoltageRegulator，固定 metabolic_recovery=0.001
- **契约**: C1 energy > 0.5 → 违约
- **状态**: OPEN
- **修复**: 待分析 — 需要为 vestibular 层也加 VR

---

### DEG-012: HairCell 能量耗尽
- **发现时间**: 2026-05-22 (契约验证发现)
- **现象**: HC energy = 0.001 (C2 契约要求 > 0.5)
- **影响层**: HairCell
- **根因**: HC 无 VoltageRegulator，固定 metabolic_recovery=0.001
- **契约**: C2 energy > 0.5 → 违约
- **状态**: OPEN
- **修复**: 待分析 — 与 DEG-011 同根因，需扩展 VR 到 vestibular 层

---

### DEG-013: Binding layer activation 指数爆炸
- **发现时间**: 2026-05-23
- **现象**: BindingCell activation 从 53 → 8717+ (t=9500)，Motor heat=1000 (clamped)
- **影响层**: Binding → Motor
- **根因**: BindingCell.compute() 使用乘积式 Π ReLU((a-θ)/θ)，
  col_act=0.41, θ=0.05 → normalized=7.2, product=7.2²=52。
  随 col_act 增长，product 以 O(a^n) 速率爆炸，无饱和限制。
  爆炸的 activation 通过 mot._membrane.inject() 绕过 PowerRail
  直接注入 Motor 膜 → heat = (100)² × 0.1 = 1000 (clamped at 100)
- **状态**: FIXED
- **修复**: FIX-015

---

### DEG-014: Motor spike 永久抑制
- **发现时间**: 2026-05-23
- **现象**: Motor 在 18 次 spike 后永久静默, V_mem → -0.83
- **影响层**: Motor
- **根因**: 双重因素:
  1. tau_w=50s → w_adapt=0.35 几乎不衰减 (ε=0.99998/step)
  2. col_to_motor synapse_gain=10, 6 col sources → scaled=31 >> PowerRail max=10
     → v_avail=0, 正向注入为零, 仅剩 w_adapt 负注入 → V 不可逆下降
- **状态**: FIXED
- **修复**: FIX-016

---

### DEG-015: 机械输入无物理量纲（单位未定义）
- **发现时间**: 2026-06-30
- **现象**: `oto_x = 6.0 * sin(...)` 无物理单位；MET `gm=2.0` 无法对应真实力-电流转换系数
- **影响层**: MET（最上游），向下波及整条前庭链及所有依赖前庭信号的层
- **根因**: 架构设计时未绑定物理单位。信号幅度（6.0）、MET 跨导（gm）、HC 各通道阈值均为无量纲归一化值，缺乏到实际物理量（rad/s、m/s²、pA/nm）的映射。
- **后果**:
  1. FIFO 延迟（2 ms）、G_eff（α=5.0）等时域参数无法从生物第一性原理推导
  2. synapse_gain=16.0（FIX-P2）是工程倒推，而非来自生物学收敛比
  3. 任何参数调整都无法判断是否越出了生物合理范围
- **状态**: KNOWN_DEBT（系统可运行，但参数空间无锚点）
- **解决路径**: 见 `cell-cell/工作报告/技术债档案-前庭量纲带宽欠债_2026-06-30.md`
- **影响 DEG**: → 加剧 DEG-016（单纤维噪声无法用理论 SNR 约束）

---

### DEG-016: 单传入纤维每轴（N=1，无种群编码）
- **发现时间**: 2026-06-30
- **现象**: DR2（3D 距离缩减@200k）在同参数两次运行间差 30%（0.614 vs 0.880）
- **影响层**: Aff → Enc（及所有依赖前庭信号方向性的下游）
- **根因**: 每个前庭轴仅有 1 条规则 + 1 条不规则传入纤维（共 2 个 Neuron），而生物半规管有约 15,000 条并行传入纤维。种群编码 SNR 提升 √N≈122 倍在当前模型中缺失。Langevin 噪声在每次运行中随机决定 body 轨迹，噪声无处平均。
- **数学关系**: `SNR_model / SNR_bio ≈ √(2/15000) ≈ 1/87`（信噪比低 87 倍）
- **后果**:
  1. 单次实验结果对随机种子高度敏感，行为涌现结论需要多次运行统计
  2. DR2 等基于单次运行轨迹的指标不稳定
  3. 方向性学习（STDP |Δw|）的速率因轨迹差异而变（本次 0.112 vs P0 的 0.022）
- **状态**: KNOWN_DEBT（结构性简化，非偶然错误）
- **解决路径**: 见 `cell-cell/工作报告/技术债档案-前庭量纲带宽欠债_2026-06-30.md`
- **关联 DEG**: ← 被 DEG-015 加剧；→ 导致 DR2 指标不稳定

---

### DEG-017: 关键前庭增益参数工程倒推，无生物推导
- **发现时间**: 2026-06-30
- **参数清单**:
  | 参数 | 文件 | 当前值 | 推导来源 |
  |------|------|-------|---------|
  | `synapse_gain` (Aff→Enc) | hebbian.py | 16.0 | FIX-P2 工程补偿（Aff 实测 2 Hz，需让 Enc 过阈值）|
  | `G_eff α_vest` | network_layer.py | 5.0 | 实验拟合（使 G_eff≈14.7 匹配观测）|
  | `CONSUME_RATE` | variant_adapter.py | 9.75 | EXP-P5RouteA（drain/deposit 比值×65）|
  | `oto_x 幅度` | 实验脚本 | 6.0 | 无依据，随实验需要设定 |
- **影响**: 上述参数形成"参数岛"——互相依赖但都没有共同的生物量纲锚点，任何一个修改都可能需要重新调整其他参数（链式调参风险）
- **状态**: KNOWN_DEBT（有 BIO 原理注释但无数值推导）
- **解决路径**: 见 `cell-cell/工作报告/技术债档案-前庭量纲带宽欠债_2026-06-30.md`
- **关联 DEG**: ← 根因是 DEG-015（无量纲锚点）

---

### DEG-018: `occurrence.py` REFRACTORY→ARMED（τ_rearm）双时钟无物理载体
- **发现时间**: 2026-08-05（TSS-R1b 审计）
- **现象**: `generators/occurrence.py:329-344` 的 `_ClosurePhase.REFRACTORY` 阶段
  用纯整数计步判定重新武装（`t_step - self._t_down >= rearm_min_steps`），
  与退出判定（`theta_down` 阈值迟滞）是两个独立的软件时钟。
- **影响层**: `generators/occurrence.py`、`relations/entry_boundary.py`
  （TSS-R1a 参考检测器沿用了同一双时钟结构）
- **根因**: 标定记录 `exp_P2A1b_3_closure_calibration.py:65-70` 只证明
  `rearm_min_steps=500` 能把伪发生收敛为 1 次（即它实际扮演去抖动/防重复
  计数滤波器的角色），与 `theta_down` 解决的是同一个问题（同一物理支撑期
  内不要重复计数），未证明需要独立的第二时间常数。TSS-R1b 已用可重触发
  饱和 RC 门（`relations/entry_gate.py`）证明单时钟即可满足全部资格，
  且实测两个 oracle 变体（rearm=0 / rearm=500）在真实数据流上事件计数
  完全相同——即现有实测数据分辨不出第二个时钟做了什么。
- **状态**: KNOWN_DEBT（继承债务，此前多轮 P2-A/TSS 审计均未单独挑出）。
  TSS-R1b 裁定本轮**不修改** `occurrence.py`——它被 `occurrence_tap.py` /
  `r2_fork.py` / `test_occurrence_identity.py` /
  `test_p2a_generator_core.py`（显式依赖 `rearm_min_steps=0` 分支）等
  多个消费方依赖，混在审计+单支路物理化任务里改会扩大回归面。
- **解决路径**: 独立立项，参照 `relations/entry_gate.py` 的单时钟拓扑
  （Capacitor + MOSFET Zener 钳位）审查 `occurrence.py` 三态机是否可合并
  为二态。见 `cell-cell/工作报告/TSS-R1b_E上箭头物理实现映射审计_2026-08-05.md`。
- **处置（2026-09-07，审计先行裁定 → 不合并，降为已定量刻画的设计决定）**:
  EXP-DEG018-01（`tss/tests/_diag_deg018_dual_clock_equivalence.py`）双
  oracle（rearm=0/500）同流对比，按维度判定：
  ① 真实链路（site28 加热900步→撤热）发生计数与 t_up/t_down **等价**
  （occurrence @t_up=389/t_down=2238，两 oracle 相同）；
  ② **t_rearm 系统性 +500 步**——rearm 事件是 RelationFinalizer 的
  occurrence 登记触发点，偏移与实测关系窗 Δt₂⊂[35,319] 同数量级，
  消费方可见 ⇒ 时刻维度不等价；
  ③ 对抗边界：t_down 后 gap 步开新物理支撑 epoch 再越阈，gap∈{100,300}
  时 rearm=500 把第二次真实发生**整个丢失**（计数 1 vs 2，非延迟——
  REFRACTORY 期间 ARMED 分支不可达，若新 epoch 的驱动窗在重臂前结束则
  永久错过）；gap≥499 恢复等价。
  **结论**：第二时钟不是冗余——原登记"实测数据分辨不出第二个时钟做了
  什么"已被否证（它做两件事：延迟下游登记 +rearm 步、抑制重臂窗内的
  新发生）。按用户裁定不合并二态；该行为是否为**期望**语义（去抖 vs
  丢失真实发生）留待未来独立裁定，本条状态改为
  DESIGN_DECISION_QUANTIFIED（不再是"未证明需要"的债务）。
- **关联 DEG**: 无（首次登记）

---

### DEG-019: `MOSFET.conduct()` 阈下分支注释与实现不一致
- **发现时间**: 2026-08-05（TSS-R1b 审计）
- **现象**: `components/semiconductor.py:151-159` 注释承诺阈下有指数尾流
  电流（"In real MOSFETs, subthreshold current is always positive...
  physical drain current = |I_sub|"），但实现 `max(0.0, gm·nVT·(exp(x)-1))`
  在 `x = (v_gate - v_threshold)/nVT < 0` 时恒返回 **0.0**（因为
  `exp(x)-1 < 0`，被 `max(0.0, ·)` 截零）。
- **影响层**: `components/semiconductor.py`；任何依赖 MOSFET 阈下微导通
  的组件都会得到 0 而非期望的小正值。
- **根因**: 实现用 `max(0.0, ·)` 截断负值时，误把"取绝对值"的语义写成了
  "截断为 0"。
- **状态**: KNOWN_DEBT（当前被 `relations/entry_gate.py` 的
  `PhysicalEntryGate` 依赖为硬阈值整流器——门的开闭判定用
  `conduct(V_g) == 0.0` 作阈值门，依赖的是**当前实现行为**，不是注释
  承诺的语义）。`test_entry_gate.py::test_r1b_3_...` 内有锁定断言
  `conduct(θ_g - 1e-6) == 0.0`，若此实现被"修复"成注释承诺的语义
  （阈下返回微小正值），该测试会立刻失败并报警，而不是让
  `PhysicalEntryGate` 静默退化为永久微导通。
- **解决路径**: 独立评估是否需要让阈下分支真正返回 `|I_sub|`（修复注释
  与实现的不一致），评估前必须先确认 `PhysicalEntryGate` 等依赖方的
  阈值判定方式需同步调整。
- **处置（2026-09-07，注释侧修复）**: `conduct()` docstring 已改为如实
  描述硬阈值截零行为，并标注该行为现为 load-bearing（PhysicalEntryGate
  开门判定依赖 `conduct(V)==0.0`）+ 迁移审计警告（任何行为修改必须先
  审计全部阈值依赖方，D-02）。**实现零改动**；"是否让阈下返回 |I_sub|"
  保持开放，但不再存在注释/实现不一致。状态: KNOWN_DEBT → RESOLVED
  (comment-side)。
- **关联 DEG**: 无（首次登记）

---

### DEG-020: `relation_occurrence.py`/`r2_fork.py` 独立声明相同魔数阈值，互不交叉引用
- **发现时间**: 2026-09-06（全项目结构审计）
- **现象**: `relations/relation_occurrence.py:198` 的
  `_RELATION_CLOSE_THRESHOLD = 1e-4` 与 `relations/r2_fork.py:127` 的
  `_R2_CLOSE_THRESHOLD = 1e-4` 数值完全相同，均用于"collector.pre_trace
  跌破此值 → 判定活动窗口关闭"，但两处各自独立声明，代码里互不引用、
  互不注释对方存在。对照 `generators/occurrence.py:32-42` 的
  `theta_up=0.01`/`theta_down=0.001`——那里有详细的 Q3 参数依据段落
  （引用具体标定脚本 EXP-P2A1b3-CALIBRATED），而这两处 `1e-4` 只有功能性
  描述注释（"关系窗口过期判据"），没有数值本身的推导来源。
- **影响层**: `relations/relation_occurrence.py`、`relations/r2_fork.py`
- **根因**: 两个文件是不同轮次（P2-B1X1e 与 R2-fork）先后开发，大概率是
  后者复制前者数值时未加交叉引用；数值相同可能是巧合（两者恰好都选了
  "远小于 theta_down=0.001 的数量级"这一常见 float 近零判据），也可能是
  故意复用但未留痕迹——现有资料无法区分。
- **状态**: KNOWN_DEBT（不影响当前测试通过；相同数值目前未观察到导致
  错误行为，但存在"改一处忘改另一处"的静默漂移风险）
- **解决路径**: 若确认两者语义等价，应提炼为一个共享命名常量并注明来源
  （或明确写出两者为何允许不同）；若语义不同（不同层级信号量纲不同），
  应各自比照 `occurrence.py` 的 Q3 段落补齐推导依据，而不是保留裸数字。
  本次审计不擅自合并或杜撰推导依据，仅完成登记 + 双向注释指向本条目。
- **处置（2026-09-07，已修复）**: 确认两处语义等价（同为 collector
  `pre_trace` 近零 ⇒ 活动窗口关闭判据）。已提炼为
  `relation_occurrence.RELATION_CLOSE_THRESHOLD` 单一声明点（r2_fork
  import 同一常量），来源诚实注记为"工程近零判据，取 ≪ theta_down=0.001
  一个数量级，保证窗口关闭严格晚于 occurrence 闭合"——不杜撰标定。
  状态: KNOWN_DEBT → RESOLVED。
- **关联 DEG**: 无（首次登记）

---

### DEG-021: `BaseGenerator.feed()` 与 `VariantCircuit.step()` 之间的双驱动无代码级护栏
- **发现时间**: 2026-09-06（全项目结构审计）
- **现象**: `generators/base_generator.py` 已有 `_claim_drive_mode()` 护栏，
  能阻止同一 `BaseGenerator` 实例被 `feed()`（MANUAL_CALIBRATION）和
  `feed_from_skin()`（WORLD_COUPLED）两种模式交替驱动（fail-fast raise）。
  但 `feed()` 的 docstring（约167-183行）另外声明"与 `circuit.step()` 互斥
  ...母本主循环二选一使用"——这一条约束**只停留在文档注释**，没有对应的
  运行时检查：如果调用方在同一个 tick 里既跑了
  `circuit.step()`（驱动同一批 collector/ensemble 神经元）又调用了
  `generator.feed(...)`，两条驱动路径会对同一批神经元对象做二次独立电流
  注入，代码不会报错也不会警告。
- **影响层**: `generators/base_generator.py`；任何同时持有
  `VariantCircuit` 实例和其 wrap 出的 `BaseGenerator` 并在训练/测试脚本里
  混用两者 `.step()`/`.feed()` 的调用方
- **根因**: 要实现真正的运行时互锁，`BaseGenerator` 需要知道
  `VariantCircuit.step()` 本 tick 是否已经驱动过同一批神经元——这要求
  `VariantCircuit`（母体代码）暴露一个共享状态标记（例如"本 tick 是否已执行
  quantum-thermal 通路"），属于修改母体代码新增接口，不是 generators/ 内部
  能独立完成的修复，需要先与用户确认是否值得为此触碰
  `circuit/variant_adapter.py` 的 `step()` 热路径。
- **状态**: KNOWN_DEBT（当前所有已知测试/实验脚本按约定只用其中一种驱动
  方式，尚未观测到实际双驱动事故；风险是潜在的，不是已发生的）
- **解决路径**: 若要补齐，需在 `VariantCircuit` 侧新增一个当前 tick 的
  "quantum-thermal 通路已驱动"标记，供 `BaseGenerator.feed()` 检查并
  fail-fast——这一步涉及母体代码改动，按 RULES.md"不为加功能改母体代码"
  原则，本次审计不擅自实施，仅登记 + 在 `feed()` 文档处指向本条目。
- **处置（2026-09-07，已修复，用户授权母体最小标记）**:
  `VariantCircuit.step()` 维护单调 `self._step_serial`（1 行纯赋值，
  惰性初始化，热路径零分支）；`BaseGenerator.feed()/feed_from_skin()`
  经 `_check_no_dual_drive()` 检查两次 feed 之间 serial 是否前进，前进
  即 RuntimeError（基线取首次 feed 时值——wrap 前 warmup step 合法；
  `_circuit_ref=None` 旧调用形态自动退化为文档级约束）。验证:
  `tss/tests/test_deg021_dual_drive_interlock.py` T-DD-1~3 3/3 PASS +
  母体回归。状态: KNOWN_DEBT → RESOLVED。
- **关联 DEG**: 无（首次登记）

---

### DEG-024: `KernelEnergyProbe` 神经元热耗散量纲错误（少记 1000×）
- **发现时间**: 2026-09-07（外部评判《TSS (3) 全量实测后的最终修改清单》
  §1，跨账本交叉计数实测发现）
- **现象**: `tss/events/kernel_ledger.py` `record()` 写
  `total_neuron_heat += n.heat_output * dt`，但母体
  `nexus_v1/components/neuron.py` step() 末段把 `heat_output` 设为该步
  **实际扣除的能量**（`actual_drain`，energy per step），不是功率。
  外部实测同轨迹交叉计数：probe=0.00037058 vs 母体累计 heat=0.37058，
  ratio=0.001 恰等于 dt ⇒ 少记约 1000 倍。
- **影响层**: `tss/events/kernel_ledger.py`（ℒ 账本 neuron heat 一栏）；
  电容泄漏项 `V²/r_leak·dt` 是功率×dt，量纲正确不受影响
- **根因**: 误把 `heat_output` 当功率处理；T-KL-3 只做非负/非 NaN
  sanity check，无法拦截数量级错误——测试覆盖缺口与实现错误叠加。
- **处置（2026-09-08，已修复）**: ①去掉 `* dt`（`+= n.heat_output`）+
  量纲声明注释（"energy per step, NOT power——严禁再乘 dt"）；②新增
  **T-KL-5 跨账本守恒测试**：probe 计数 vs 母体 Σ `_cumulative_heat_out`
  增量，浮点级容差（rel_tol=1e-9，非百分比级），量纲错误复发会以
  ratio≈dt 的形态立即暴露。修复后实测 probe=0.3705778 与母体精确吻合。
  ℒ 状态**保持 EXISTS_PARTIAL**（MOSFET 耗散仍未建模，不因本修复升级）。
  状态: RESOLVED。
- **关联 DEG**: 无（首次登记；编号从 DEG-024 起遵循 2026-09-07 分叉
  解决规则）

---

### DEG-025: `Memristor.update` 缺 dt 因子（MEMRISTOR_UPDATE_MISSING_DT）
- **发现时间**: 2026-09-23（MFS0-E0 Step C 装配写入门时发现）；按
  《MFS0-E0 Step D–H 执行反馈与开工裁定》§9 于 2026-09-29 本轮收口登记
- **现象**: `nexus_v1/components/semiconductor.py` `Memristor.update`
  写 `dw = 0.5·current·(pre−post)` 后直接 `apply_dw(dw)`，**没有 Δt**。
  它自称 Strukov 型，而 Strukov 方程是 `dw/dt ∝ i(t)`，离散化应为
  `Δw = k·i·Δt`。dt=1.0 旧约定下二者等价；在 dt_G=0.001 下每步写入量
  放大 1000×——MFS0 实测重叠窗内 I_write 峰≈1.0 ⇒ 单步 dw≈−0.5 ⇒ 一步
  撞 w_min 钳位。
- **影响层**: 所有在 dt≠1.0 下调用 `Memristor.update` 的路径。主干目前
  零调用（评判 E-3），实际影响面为 research 层（MFS0-E0 写入门、A8
  candidate_z 原型）。
- **根因**: 与 E-10 同族的步制地雷（同族：`bundle.py` eligibility_tau /
  da_ema_tau、`compensation.py` 全部 τ 注释）——API 在 dt=1.0 时代设计，
  时间积分隐含在"每步"里。
- **处置（未修 production）**: MFS0-E0 在调用侧传 `current = I_write·dt`
  （`research/memory_feedback_substrate_v0/mfs0_common.py` WriteGate.write），
  所有臂统一；该参数在本轮实际承载的是**时间积分后的写电流增量**，是
  量纲债务 workaround，不是新物理参数。修复 production API（加 dt 形参或
  改名）须另立任务并处理 A8 原型的兼容性。状态: OPEN（workaround 在役）。
- **关联 DEG**: 无（E-10 同族，见 MFS0-E0 方案评判）

---

## LIM 已知限制（非退化，结构性未达标项）

> 与 DEG 的区别：DEG 是"曾经工作现在退化/发现的缺陷"；LIM 是"从未达标、
> 且已定量证明在当前结构下不可达的资格项"。LIM 不许通过调阈值/调参数
> "修复"——只能通过独立设计轮的结构变更解除。

### LIM-RPREC-READOUT-001: r_prec 学习效应量经下游读出后结构性不可达 1% 阈值
- **首次登记**: 2026-07-29（P2-B1R 报告，`cell-cell/工作报告/P2-B1R_局部因果复放验证_方案Aprime_2026-07-29.md`，原表述"L2 未达标，单束信噪比不足"）；2026-09-06 转入本注册表（此前仅在工作报告中，外部实测反馈清单 §1 独立复现后补登）
- **现象**: `tss.tests.test_r_prec_replay_simple` 效应量层稳定失败——权重
  学习 +0.97%（0.108750→0.109802）但下游电流积分仅 +0.0033% < 1% 阈值；
  外部评判以 PYTHONHASHSEED=0/1/2 三次独立复现（3/3 FAIL，数值一致）。
  `test_r_prec_replay` 的 T-RPP-R2（learned-vs-blocked 距离 0.000076<0.01）
  同根因。
- **根因**（`tss/tests/_diag_rprec_effect_compression.py`，2026-09-06 定量）:
  总压缩 297× = 环节A 8.3×（Memristor 低 w 工作点：ΔG/G=Δw·(r_max−r_min)/R
  =0.117% ≪ Δw/w=0.97%）× 环节B 35.8×（训练期积分稀释：collector 活动
  窗口在前中期，而 da_ema_tau=50000 使权重增量后置——25% Δw 到 step
  31500 才到位，末段 10% 窗口两组电流均为 0，活动窗与增长窗不相交）。
  **即使消除环节B，效应上限 0.117% 仍低于 1% 阈值一个数量级**；达标需
  Δw≈0.009（9× 现有学习量）或读出结构变更。
- **处置**（2026-09-06，双层资格拆分，外部反馈 §8）: 机制层
  （`test_rpp_r1_mechanism`，Δw>0）PASS 保留；效应量层断言与 1% 阈值
  **原样保留**并加 `pytest.mark.xfail(LIM 指针)`——负结果保持可见，
  不合并宣告"learning PASS"。
- **解除路径**: 独立设计轮——候选方向：多束并行读出（√N 信噪比增益，
  参照 DEG-016 种群编码分析）/ 读出工作点上移 / 效应量判据改为机制层
  可检验的等效量。任何解除必须先过三问，禁止调阈值放行。
- **设计轮一（2026-09-07，用户裁定方向=多束并行读出；EXP-LIM-01
  `tss/tests/_diag_lim_population_readout_model.py`，模型先行）**：
  实测标度律否证候选①的充分性——
  ① 效应量层（replay_simple 1% 相对阈值）**N-不变**：N=1 相对效应
  0.0035% vs N=4 0.0034%（每束 Δw 全同 +0.00105，分子分母同乘 N）；
  上限被 Memristor 低 w 工作点钉死在 ΔG/G≈0.117%，与束数无关 ⇒
  **多束并行读出结构上不能解除此层**；
  ② 阻断距离层（replay R2 0.01 绝对阈值）随 N 近线性（实测
  4.035×@N=4，DA 末段活动 1.000× 未饱和），线性外推 N*≈132 束——
  可解除但仅此一层，且 132 束无独立生物推导支撑（如立项需先过三问）。
  **处置**：不建 N* 束生产原型（模型先行避免无效结构堆叠）；LIM 保持
  未达标可见（xfail 原样）；剩余候选方向缩窄为：读出工作点上移
  （受 w≤0.5 饱和边缘约束）/ 判据改机制层等效量（需外部评判认可）。
- **关联**: DEG-016（单纤维 N=1 信噪比），外部实测反馈清单 §1/§8

### LIM-POSTERIOR-TIMING-FAR: Posterior-0 FAR 时点（δt=4τ）未测

- **首次登记**: 2026-09-21（Posterior-0 轮内本地登记，commit `410eeae`）；
  2026-09-22 转入本注册表（此前仅存在于轮内文件，跨轮不可见）
- **status**: `NOT_ATTEMPTED`（**不是** UNREACHABLE）
- **⚠ 与本节 LIM 定义的偏差（诚实登记）**: 本节 LIM 定义要求"已定量证明
  在当前结构下不可达"，本条**不满足**该要求——它是预算耗尽导致的未测，
  外推提示**可能可达**。沿用 LIM 命名是因为外部反馈 §三已预先指定
  「FAR 不可达登记 `LIM-POSTERIOR-TIMING`，它不是实验失败」；登记目的
  是跨轮可见性，而非宣告结构性不可达。若后续补测确认不可达，再改
  status 并补根因。
- **现象**: 方案 §19 的三点时窗网格 δt = {1,2,4}×τ_residual，本轮只完成
  NEAR（δt=1τ，t_up=5402，R1C_FALLBACK）与 MIDDLE（δt=2τ，t_up=6344）；
  FAR（δt=4τ）未尝试 ⇒ §19 "interaction alive → boundary → interaction
  gone" 的第三段（gone）未实测，时窗结论只到 MIDDLE 的边界值
  （I_W=2.478e-3，NEAR 的 1/6.7）。
- **原因**: `new_g0` 物理轨迹预算 4/4 耗尽——probe1（t_on=4780/P=600，
  零 occurrence，NF-1 尾容限 <23 步）/ probe2_r1c（同 t_on，P=900，成功）/
  middle / hold_timing。其中 1 条消耗在 NEAR 点的可达性探边上
  （R-1(a) 主路径实测失败 → R-1(c) 一次后备）。
- **外推（未测）**: `t_on ≈ 6540 / P = 900` 可能可达；NF-1 潜伏期漂移模型
  在 t_on=5660 处外推误差仅 10 步（预测 6334 vs 实测 6344），仍近线性，
  但 P=900 支撑窗在更晚 t_on 的尾容限未验证。
- **解除路径**: 补测 1 条 `new_g0` 轨迹（t_on≈6540/P=900）；须在新一轮的
  预算 ledger 中预注册，不得挪用 Posterior-0 已冻结的预算口径。若补测
  仍零 occurrence，则本条按 NF-1 家族根因升级为真 LIM 并补定量根因。
- **证据位置**: `research/posterior_v0/POSTERIOR0_NEGATIVE_RESULTS.md`
  （§LIM-POSTERIOR-TIMING-FAR）/ `data/p0_timing_freeze.json` `limits[0]`
  （机读）/ `data/qualification_summary.json` / 生成点
  `research/posterior_v0/dataset_builder.py:98`（同处另有条件性
  `LIM-POSTERIOR-TIMING-MIDDLE`，本轮 MIDDLE 可达故未触发）
- **关联**: NF-1（site23 换能潜伏期随 t_on 单调漂移，D2-1 轮登记）、
  DEG-019（MOSFET 阈下截零——本轮读出面机制）；Posterior-0 终态
  `A_CONDITIONAL` 不依赖 FAR 点（六门判据均在 NEAR 面成立）
