# 工作追踪看板 (Task Board)

<!-- Claude 必须在每次会话开始时读取本文件，执行任务前先登记，完成后立即更新 -->
<!-- 格式：每行一个任务，状态必须是：⚡执行中 | 📋待执行 | ⏸暂停 | ✅已完成 | ❌取消 -->

---

## ⏸️ 项目整体暂停（2026-09-06，用户决定）

**重启入口：先读 `cell-cell/工作追踪/暂停快照_2026-09-06.md`**（项目全景状态、
分支状态、阅读顺序都在那里）。本看板下方条目为暂停前（2026-07-08 最后更新）
的 organism 侧待办，落后于 git 实际进度约两个月——2026-07~08 的实际工作重心
是 TSS 理论轨（TSS-R0→R1b，已迁至顶层 `tss/`，见 `tss/README.md`），本看板
从未登记过这些任务。重启时以快照为准，不要直接从下方旧条目开工。

---

## ⚡ 当前执行中

| ID | 任务描述 | 开始日期 | 当前进度 | 下一步 |
|:---|:---|:---|:---|:---|
| （备注） | **MFS0-E0 已终结（终态 A，2026-09-29，§30 硬停止）**——MFS0_PHYSICAL_MEMORY_SUBSTRATE_CANDIDATE_QUALIFIED，详见✅已完成与 工作报告/MFS0-E0轮工作报告_StepDH_2026-09-29.md。下一问（方案 §33）：z₀→(W₁,Δ₁)→z₁→(W₂,Δ₂)→z₂ 已沉积态能否再被修改 | — | — | 等待下一轮外部方案 |
| （备注·已消费） | **MFS0-E0 方案评判（2026-09-23，ADOPT with amendments，见 交叉比对/MFS0-E0方案评判_2026-09-23.md）**。方案定位=对我方 Posterior-0 D-2 论点的正面回应（元件级设计轮）：Past→e（eligibility 电容）+ Later→M（调制）⇒ Δw（memristive 持久态）→ Future；两阶段（Phase A 物理绑定 / Phase B 持久沉积），六门 MFS0-M1~M6，六终态 A~F。**三项核心勘误**：E-1 §10 的 I_z=(w11−w10)−(w01−w00) 在乘性实现下是恒等式（w01=w10=w00）⇒ 不可证伪，主判据须改 NC3 选择性比值 Δw(NEAR)/Δw(TC)；E-2 物理乘法三档未指定（裸 Python×/双 FET 硬截零[theta_comparator 先例，已有 2026-09-06 用户裁定]/负载线自洽[仅 rail_latch]），§3 禁 if 却允许"ẇ∝e·M 最简近似"自相矛盾；E-4 M5 会撞 LIM-RPREC-READOUT-001（G(w)=1/(10−9.9w) 双曲，低 w 端 ΔG/G=0.117%≪Δw/w=0.97% 且 N-不变）⇒ 可事前解析预见的终态 E 风险，须先选高 w 工作点。**好消息**：时点可达性非硬阻塞（site23 已录窗 3542/4159/4577 + P0 新录 5402/6344 全晚于 W=rc_main），new_g0 预算可声明=0 | 2026-09-23 | 方案评判完毕（E-1~E-12 + R-1~R-4） | 等待 R-1（M(t) 驱动源四选一：ν/Ξ残差/CPG/H_τ，建议 H_τ 或 CPG）+ R-2（乘法档位，建议档2）+ R-3（与 RULING-P0-1 关系，建议保持 OPEN 待 MFS0 完成后合并裁定）+ R-4（初始 w 工作点偏离默认 0.1 改高 w 端） |
| （备注） | **Posterior-0 已终结（RULING-P0-1 = DEMOTED_TO_C，2026-09-23）**——用户裁定经 MFS0-E0 修订方案 §3 R-3 下发，采纳"载体分量改变是支配判据"，行使 FINAL_RULING 预登记的降格路径：effective_terminal=C / POSTERIOR_EFFECT_ADDITIVE_ONLY=TRUE **(at carrier)** / REORGANIZATION_V0_QUALIFIED=FALSE / READY_FOR_POSTERIOR_1=FALSE / POSTERIOR0_TERMINAL_C_FROZEN=TRUE，**+ THRESHOLD_READOUT_INTERACTION 保留为正发现**（I_W=1.651e-2/时序依赖 6.71×/block 逐位 0.0/transplant 双向 RMSE=0.0/hold6 一次过）。(at carrier) 限定为必需——§34 定义 C 为 I_W=0，而实测 I_W≫0 且因果闭合齐全，不带限定会与数据矛盾。追加式留痕（原 terminal_state 区块原样保留 + 新增 ruling_applied），实验数值与 p0_hold_seal.json 逐字节未改。日期勘误：降格生效于 2026-09-23 而非 2026-09-22（那日仅出读法对照与建议，主建议维持 A，裁定点当时 OPEN） | — | — | 禁 reopen Posterior-0 / 禁 Posterior-1；下一问"载体级基质何在"由 MFS0-E0 回答，且不得反向修改本轮结论 |
| （备注） | **D2-1 已冻结（FREEZE D2-1，方案 §30，2026-09-21）**——六门 D21-M1~M6 全 PASS 终态 A：D2_1_RECURSIVE_GENERATION_QUALIFIED + **G1_QUALIFIED**（REPLAY/REFERENCE 范围，live 仍受 CAUSAL_VARIANT_REQUIRED_BEFORE_LIVE_D2 约束）+ READY_FOR_POSTERIOR_0。素材：χ_ρ₂^(2) 候选 rc_main+hold5、冻结 g_rel2=1.3139e-2/θ₂=2.6209/rearm₂=456、谱系 relation.r_rho:d21_rho2(depth2)。禁 D2-1b/G1-v2/more relation cells/more sites/more modalities/large recursive sweep | — | — | 已被 Posterior-0 消费 |
| （备注） | **D2-0 已冻结（FREEZE D2-0，反馈 §二十四，2026-09-20）**——六门全 PASS 终态 A。下一轮：**D2-1/P2-C**（唯一问题：χ_ρ^(1) 能否再次成为关系输入——χ_ρ^(1)+χ_k^(0)→𝒞_ρ₂ 或 χ_ρ₁^(1)+χ_ρ₂^(1)→𝒞_ρ₃；若不能则 D2-0=terminal relation readout。素材：relation_occurrence_candidates.csv ×9，谱系 relation_rho:d2_rho0；v0 冻结参数 g_rel=0.25/theta_up_ρ=2.6164/rearm_ρ=456 步）。禁 Naturalization-v2/RelationCell-v2/更多 site/更多模态/更大网络/更大扫描 | — | — | 等待 D2-1/P2-C 方案 |
| （备注） | **G0 主线已冻结（FREEZE G0-CENTRIC MAINLINE，§25，2026-09-19）**——G0-R1/OCC 六门全 PASS 终态 A。下一轮：**D2-0 / P2-B**（多个真实 χ_i^(0) 经候选自然化 𝒩 进入关系结构 𝒞_ρ；消费口=tss/adapters/occurrence_port_v2.py，D2 不得读 G0 内部 neuron state；冻结参数 g_v2=2.5125e-2/theta=0.01/rearm=500/S0+B0）。禁止 G0-R2/R1b/Occurrence-v3/Entropy redesign/World-v3/Transduction-v3，除非 D2 产生可复现阻断性反例 | — | — | 等待 D2-0/P2-B 方案 |
| （旧指针） | G0-R0 已完成（G0_MULTIRATE_TIMEBASE_QUALIFIED）；G0-R1 范围原文：（**首次动 production 定点修改**：typed port implementation / B transition bridge / A target port plumbing / L1 input semantics rename / legacy compatibility + G0-R0 例外修复[L1 trace dt 化/delay_steps dt-aware/closure n→t_phys 映射]）→ Occurrence Revalidation（χ 全重验 + closure 阈值与 g 量级物理秒制重标；G0-R0 已示 bridge occ=1×5 与 L1 饱和 33.3% 信号；'逐状态比较非合法验收面'教训） |

---

## 📋 待执行

| ID        | 任务描述                                                            | 优先级 | 依赖  | 来源文档            |
| :-------- | :-------------------------------------------------------------- | :-- | :-- | :-------------- |
| DEG-025 修复 | Memristor.update 缺 dt（MEMRISTOR_UPDATE_MISSING_DT）：production API 加 dt 形参/改名，处理 A8 candidate_z 兼容；当前 MFS0 调用侧 current=I_write·dt workaround 在役 | P2 | 用户排期 | degradation_registry.md DEG-025 |
| MFS0 同步主仓 | 主仓 J:/cell-cc（feat/tss-theta）快进同步本轮提交（ff 前比对 untracked 冲突） | P2 | — | MFS0-E0 StepDH 报告 §六 |
| DA-P1 shadow饱和 | shadow内部根因：col calcium_rate全饱和(cri_v_clamp=1.0)→加快θ_M或降shadow输入增益；当前仅sg掩盖 | P1 | DA-rebal | STDP修复方案补充_评判与实测修正 §四 |
| 死锁二 增益调制 | STDP目标从方向极性→增益调制（thermo→yaw插可学习增益门控，分流抑制物理化，走三问） | P1 | DA-rebal PASS | STDP无效根因复核 §六 / 修复方案补充 §四 |
| 死锁二 前置 | 三问审查：G_eff乘法门控的Sources→Bundle→Targets+参数推导 | P1 | — | 修复方案补充 §四 |
| T-039b-rerun | T-078 fix-A后重跑J2确认（w_ccw漂移<0.01）                          | P3  | — | — |
| T-静默MVE | 4束全连接方向涌现MVE（phasic→spinal全连接200k）                      | P3  | 死锁二完成 | 运动势垫支实施方案§9.3 |
| T-Z验证 | Z轴热觉验证实验（解锁Z轴，热源偏Z±20单位，检验top/bot差异化）      | P3  | — | T-084实施说明 |

---

## ⏸ 暂停（有明确恢复条件）

| ID | 任务描述 | 暂停原因 | 恢复条件 |
|:---|:---|:---|:---|
| T-013 | HC-015（待定） | 用户明确暂缓 | 用户指示 |

---

## ✅ 已完成（最近20条）

| ID | 任务描述 | 完成日期 | Commit |
|:---|:---|:---|:---|
| MFS0-E0 | Step D~H + hold6 + 六门终裁：**M1~M6 全 PASS + hold6 6/6 → 终态 A MFS0_PHYSICAL_MEMORY_SUBSTRATE_CANDIDATE_QUALIFIED**。Step D NEAR=s23_ov / TC=p0_probe_near_r1c（实测零门控；脉冲 600 vs 900 LIMITATION，用户 2026-09-29 条件接受）/ ε_sel=1e-6 / S_min=10 / predicted_I_z=−6.078e-2；Step E Δw_NEAR=−6.078e-2、Δw_TC 精确 0、NC1~NC6 全过、I_z 观测=预测、Retention_w=1.0 实测；Step F 原位 query D_Q=2.116；Step G 双向 do(w) RMS=0.0 逐位（w=最小充分态+STOP）；Step H 切断后 D_Q=0、上游电流差 1.06e-1（BLOCK_LIMITATION）；hold6 先封后跑 6/6。登记 DEG-025（Memristor.update 缺 dt）。执行失误如实登记：首版在主仓动手+单载体 factorial（I_write 恒 0），已撤回并计 attempted_run；SHA 收口 8 项仅 EOL 差异（内容与封存 blob 一致）。回归 21/21+contracts 13/15（C2/C3⊆DEG-004）+vp+fast43 | 2026-09-29 | 9ab665f/1deed56/7d6b278/7bb53a4/2c0ccc3 |
| MFS0-E0评判 | 外部方案《MAINLINE V2 — Memory/Feedback Substrate-0（MFS0-E0）》评判分析（25 节/1705 行）：三路代码核实取证（持久载体/typed 端口与驱动链/调制原语与时间单位）。**衔接**：四状态字符串吻合，两处失真（§0 漏引 G1_QUALIFIED 的 REPLAY/REFERENCE scope；§0「Posterior-0 已结束」与存档 READY_FOR_POSTERIOR_1=pending ruling 不符，§22 终态 D 把六门全 PASS 的 A_CONDITIONAL 称作"失败类型"）。**E-1~E-12**：E-1 I_z 恒等式不可证伪（与 Posterior-0 D-2 对偶：那里加法性是架构必然⇒不可能 PASS，这里乘性是实现选择⇒不可能 FAIL）；E-2 乘法三档未指定；E-3 写电流入口 Memristor.update(semiconductor.py:277-280，Strukov 型)主干零调用但 candidate_z.py:228-244 已有跑通原型，建议指名复用；E-4 M5 撞 LIM-RPREC-READOUT-001（低 w 端 dG/dw=0.122 vs 高 w 端 990，差三个数量级）；E-5 w 是边际稳定连续统非 latch（A8 F4 λ=1.000）+ 主干 lambda_metabolic 使 w 趋零 vs research 层 apply_dw 无衰减；E-6 RailLatch 不在主干（只在 research/A8_state_audit/，持久量是 V 非 w，F1 终态条件化）；E-7 χ→I_e 无强度通道（build_phase_drive 只读 t_up/t_rearm，幅值口 amplitude_port_stub 机器封死）；E-8 读出面陷阱（activation 过 MOSFET θ=0.3 硬截零，须显式读 _membrane.voltage）；E-9 SEMANTIC_ERASURE_AUDIT 九个污染点坐标 + 既有反例 temporal_r_prec_plastic 常数喂入须先认领 + Neuromodulator 在 production 是死 ODE；E-10 §19 时间纪律须点名禁区（compensation.py τ 注释按 dt=1.0 写，dt=0.001 下放大 1000×）且逻辑上排除复用 bundle eligibility（步制 300/5000 + 线性衰减非指数）；E-11 三处衔接与预算（补 new_g0=0 承诺）；E-12 τ_e 自由度漏洞（§9 堵了幅值没堵时间常数）。**R-1~R-4** → **ADOPT with amendments**。报告存 交叉比对/ | 2026-09-23 | c94c07c |
| Posterior-0收口 | 终裁读法对照与存档入库（纯文档轮，零代码改动）：①《Posterior-0终裁读法对照与建议_2026-09-22.md》——争点=𝔅≠id 授予面（读出投影 H_W vs 载体分量 Z_W）；读法 B 依据五条（方案 §23/§24 定义域值域与非平凡度量全写在 H_W 上、§34 终态 C 分界文字=I_W=0 且四终态无 Z_W、反馈 §十七 PL2 反定义、§二十五六门无 Z 分解要求、§十八/§21 STOP_DEEPER_DECOMPOSITION）；读法 A 正面依据两条（方案 §22/反馈 §十九）但受两重限缩（§十九条件从句"若观察到新 occurrence"未成立——R-2 裁 C 通道+实测 PNS=False；Z_W/Z_Δ 叠加在同一膜标量上无可操作测量定义）；**D-1~D-3 决定性考量**（C 的机读语义失真/载体加法性是纯 RC+frozen+禁塑性的架构必然⇒该裁定实为路线级否定/自曝条款+operator_class+命名纪律已足以记录 NF-P1）；建议=维持 A_CONDITIONAL（次优=收窄宣称名 POSTERIOR_READOUT_REORGANIZATION_V0+登记 CARRIER_LEVEL_REORGANIZATION=NOT_ESTABLISHED），不建议降格 C。②LIM-POSTERIOR-TIMING-FAR 从轮内本地登记转入 cell-cell/docs/degradation_registry.md（status=NOT_ATTEMPTED，含与 LIM 定义偏差的诚实声明+解除路径=补测 1 条 t_on≈6540/P=900 轨迹）。③三份未入库文档（外部方案原文/外部反馈/轮工作报告）归档 + main 快进同步。回归沿用上轮基线（21/21+vp+fast43，参数零改动） | 2026-09-22 | a77cb81 |
| Posterior-0 | 后验重组织资格轮（反馈全裁定后执行）：Step A substrate（膜面 τ=500 步/qrel 窗 6131/activation 坍缩=DEG-019 读出效应）+ reachability（probe1 P600 失败→R-1(c) 一次后备 P900 成功 NEAR=(5402,5541,6041)；L1 尾容限<23 步）；Step B/C MIDDLE=(6344,…) 可达+H3 hold 轨迹+hold6 SHA 封存+LIM-FAR；Step D 2×2×3 集：I_W(act)=1.651e-2≫ε、I_W(膜)=3e-15、时序依赖 6.71×、PNS=False、PL1(膜)=1.141；Step E 分离性审计 w_shift_vm=3e-15（NF-P1 载体加法）+交互定位 k*=6497（阈值门控机制）；Step F block 逐位消除（BLOCK_LIMITATION 能耗项披露）+transplant 正反向 RMSE=0.0 逐位（单细胞膜态=最小充分载体+STOP）；Step G hold6 一次过 6/6（M_Q 符号翻转 +0.25/−0.065）→ **六门全 PASS，终态 A_CONDITIONAL + RULING_EXPOSURE**。回归 21/21+vp+fast43；预算 4/4+7/12+3/4+3/4+3/4+1/3+6/6 | 2026-09-21 | 410eeae |
| Posterior-0评判 | 外部方案《MAINLINE V2 — Posterior Construction-0》评判分析：衔接零失真（冻结参数/终态/载体/REPLAY范围/目录惯例全核实）；**E-1 硬阻塞发现**：§6 要求 t_Δ>t_rearm=5387（rc_main），但现有 site23 窗最晚 t_up=4577 且 NF-1 潜伏期漂移封锁晚 t_on 录制——far 时点物理不可达；E-2 NF-2 约束 Δ/Q 通道指派（R 单独越阈+52% 触发新发生→PARALLEL_NEW_STATE 混淆，建议 C 主通道）；E-3 M5 阻断半门退化（端口移除≡Δ=0 臂，改断 bundle 保换能）；E-4 无塑性基质→P1 持久性只相对 washout 成立+energy 唯一单调基质须单列；E-5 rearm 无物理 reset→终态 B 改分级；E-6 Q-scale 无幅值 DOF（typed 合同）；E-7 回归/预算口径/命名撞名。R-1（时点三选，建议缩窗为默认）/R-2（通道指派）/R-3（Z 分量+washout 预注册）→ **ADOPT with amendments**。报告存 交叉比对/ 并抄主仓 | 2026-09-21 | 08fb853 |
| D2-1/P2-C | 关系发生递归消费与首次 G1 资格（评判 ADOPT with amendments 后执行）：**六门 D21-M1~M6 全 PASS → 终态 A：D2_1_RECURSIVE_GENERATION_QUALIFIED + G1_QUALIFIED + READY_FOR_POSTERIOR_0 + FREEZE D2-1**。StepB RelationOccurrencePortV1（tss/adapters 纯记录）+ relation track 重放重建 4 条逐位 bit-exact + site23 轨迹 7 条≤8 + hold6 SHA 封存（NF-1 潜伏期漂移 521→637 步登记）；StepC 𝒞_ρ₂ 新实例标定 9 点≤10（g_canon2=1.3139e-2/τ₂=0.456s/死区=MOSFET 阈下截零）；StepD E1 递归接受（RT-2 峰值饱和证伪登记+RT2r 根因核验；NF-2 单亲触发 R+52%/C−2.8%）/E2 DEPTH_NON_COLLAPSE（RMSE≈1.35，边界移位 725~825 步）/E3 twin 存在级分叉（X2.902≥θ₂>Y2.547）+tier1 膜态移植 RMSE=0.0 逐位等化=G1_STATE_DIMENSION_CAUSALLY_SUPPORTED+STOP/E4 blockR occ1→0 存在级、blockC 仅边界级；StepE hold6 一次过零回调+六门全 PASS。预算 7/8+4/16+9/10+1/4+3/4+6/6；回归 21/21×2+fast43；报告 D2-1-P2-C轮工作报告_2026-09-21.md | 2026-09-21 | 449b84a/5271c13/e81e067/9b06845 |
| D2-0/P2-B | 自然化接口与第一次真实关系生成（评判 ADOPT+反馈全接受后执行）：**六门 D2-M1~M6 全 PASS → D2_RELATION_PROCESS_V0_QUALIFIED + RELATION_OCCURRENCE_CANDIDATE + FREEZE D2-0**。Step0 UTF-8（实际病灶=r1_occ 5 脚本）；Step1 22 轨迹+RawOccurrenceTrack 缓存 11MB+port×36+hold SHA=f05f6a24 封存；Step2 N1/N2=QUALIFIED_REFERENCE、N0/N3=INSUFFICIENT（N3 被预注册 Q7 否决 4.06e-2>1%）；Step3 replay adapter（production 唯一新增）+换能链+RelationCell（τ_decay 实测 0.456s vs 设计 0.5s）+adaptive 标定 7 评估 g_rel=0.25；Step4 C0-C5+NC1-4 全 PASS（T1 镜像预判证伪：根因=site28/31 潜伏期差 8ms parent 个体性）；Step4b C6 记忆确认（x(t0) 0.559 vs 0.049）+tier1 膜态移植 RMSE=0.0=最小充分候选；Step5 closure 新鲜推导（theta=2.6164/rearm=456）cal 双父×9 全 1/单父全 0+hold8 盲评零回调。回归 21/21×2+fast43×2；预算 22/24 轨迹、7/16 评估、3/6 干预 | 2026-09-20 | 1a9b9c3/25af802/a96473b/249e63b/bec3b4d/c39af26/2a735b9 |
| D2-0评判 | 外部方案《MAINLINE V2 — D2-0/P2-B》评判分析：与 G0-R1 终裁衔接无一处失真；§36 UTF-8 实测属实（r1_revalidation.json 为 GBK）；§38 实测答案=否（tss/relations 全家 live 电路耦合，元件级可复用，缺口=replay adapter）；修正案 E-1~E-7（raw track 缺口致 N3 当前不可计算/换能强制 HC-009 路径/N1,N2 因果性条款/自激门继承 epoch 门控/UTF-8 范围/预算核算）；RULING_REQUIRED R-1（site28,31主+23攻击）/R-2（不建 relations_v2）/R-3（UTF-8 范围）→ **ADOPT with amendments** | 2026-09-20 | 51f2cec |
| G0-R1/OCC | 生产回接+基础发生最终资格轮（R-1~R-4 裁定后执行）：**六门全 PASS → G0_OCCURRENCE_V2_QUALIFIED + D1_SUFFICIENT_FOR_D2 + FREEZE G0 主线**。Step1 三笔时间债务修复零 diff（D1 trace dt 化×4 类，E4 审计漂移比 0.500→1.000 独立证实；D2 delay_tau_s 双字段；D3 to_physical 映射）；Step2 typed 端口（UdotTSample 类型强制+amplitude 存根）+B 桥 g_v2=2.5125e-2（预注册规则推导，g_v1 饱和 0.578 清偿；负结果 N-1：S0+B1=结构性错误，live=S0+B0）；Step3 cal16/hold12 SHA 封存+重验（canonical=(0.01,500)=v1 值 v2 域内确认，合法域 42/64 失败沿双侧定位，dose latency 严格有序）；Step4 hidden dynamics 第一例（相位 twin 可见 1e-5/隐藏 L2=1.37→未来分叉→Z_full 移植逐位等化=SUPPORTED，Z_low 不充分=相位在膜电荷，STOP §14）；Step5 hold12 盲评 12/12 零回调+OccurrencePortV2。回归 21/21+fast43+17 冻结脚本零 diff | 2026-09-19 | 2fe5f8d/38eae9d/4b95339/d037eb7/79070a4/46fb873 |
| G0-R1-OCC评判 | 外部方案《MAINLINE V2 — G0-R1-OCC》评判分析：存档事实引用全部核实无误（33.3% 饱和/occ=1×5/rearm=0.5s/S1 因果性登记/例外三项均与 G0-R0/T1-B 报告吻合，范围与 G0R0_FINAL_RULING 下轮建议逐字对齐）；三笔时间债务代码逐行证实；勘误 E-1~E-10（§28 nexus_v1/generators/ 已迁 tss/、§11 REUSE 与 census GAP 冲突、D1 行为零 diff 判据、D2 legacy 逐位不变、live=S0 属合同修订、统计量预注册、DEG-018 重跑义务、held-out 扩集重封存、干预登记 DIAGNOSTIC、§15 预期管理）；RULING_REQUIRED R-1~R-4 → **ADOPT with amendments** | 2026-09-19 | 0f47a4d |
| G0-R0 | 统一物理时间与多率回接（外部 45 节 ADOPT with D1-D6）：**状态 A 裁定**（GENERATOR_DT=0.001 物理秒，行为实验 E1-E4；T1-B C2 断言勘误）；census+例外三项定点登记；MultiRateScheduler N_sub=1000，S1=CANONICAL（因果性登记）；全向量 D4 FIRST_RESULT FAIL 原样保留→两层分解：Tier-1 接口一阶收敛（比 0.101）/Tier-2=G0_OSCILLATOR_PHASE_SENSITIVITY（先证 exp_P2A1b_3）；RC τ 五位不变；DELAY_STEP_COUPLING 实证（隐性）；剂量 1.0010 无复制+旧 1:1 耦合=0.00101 定量化；replay 逐位+Twin-2 无泄漏+B 桥五场景 PASS 且 occ=1×5（登记）+B_BRIDGE_L1_SATURATION → **G0_MULTIRATE_TIMEBASE_QUALIFIED**；回归 21+vp+fast43+12 冻结脚本零 diff+git 完整性核查 OK | 2026-09-19 | fbaf57f |
| T1-B | Transduction v2 跨 World 标定轮（外部 61 节方案 ADOPT with C1-C5）：层级冲突 RESOLVED_AT_CONTRACT_LEVEL+MAINLINE_TIMEBASE_CONTRACT(Δt_ext=1s)+U_T/U_Ṫ typed port 冻结；cal30+hold20(SHA封存blind) 零拟合 canonical：A 30/30+20/20、B 30/30+20/20 QUALIFIED，legacy 全域复现旧病；cross-pair+LORO 零失败 CO_ADAPTATION=LOW；timebase 三判据（naive 差分 ×0.100/档定量证伪）；双 twin 无泄漏+replay 逐位；smoke 链路存活 occ=0 登记 → **TRANSDUCTION_V2_QUALIFIED**（A 长期口/B 过渡桥/TARGET=A/BRIDGE=B）；回归 21+vp+fast43+九冻结脚本零 diff | 2026-09-19 | c484be0 |
| W1 | World v2 构建轮（外部 65 节方案 ADOPT with B1-B6）：world_v2_core（Spec/Sampler/Episode/BoundaryView 纯元组隔离/Ledger，production 零改动，Θ_legal 异质 κ+独立 r_leak）；六门+§39 全 PASS——M1 残差 4.96e-11+dt 三档收敛；M2 Θ_legal 系综 PR 1.06→3.33（单刺激/均匀κ低值如实并报为负结果）；M3 τ_env 100× vs τ_diff 1.00× 解绑；M4 30 episodes；M5 FULL 3.90 vs REDUCED 2e-17；M6 场隐藏+源隐藏双孪生 ESTABLISHED+因果阻断残差 2.5e-13/精确 0.0；B4 谱稳定界四点全符（逐点界漏判勘误）→ **WORLD_V2_RAW_QUALIFIED**+MAINLINE_V2_STARTED；回归 21+vp+fast 43 绿+WT0/T1A 复跑零 diff | 2026-09-18 | 894762f |
| T1-A | Transduction–L1 职责分离轮（外部方案 ADOPT with A1-A5）：审计三合一（支路级 PORT_SEMANTIC_MISMATCH=CONFIRMED 仅 WORLD_COUPLED；生产支路 SkinPatch.dT 自洽；LAYER_CATEGORY_CONFLICT 新登记；L1=瞬时无态整流器）+Q1 五卡（速率敏感=幅值+受体内适应态涌现，载体在 L1）+R1-R8×5 候选诊断（legacy 八负结果复演；A retention≡1.0 保真基准；B 真速率敏感且不动 L1 自洽；C 层位否决 REJECTED_AT_D_LAYER；M 对照反丢区分度证实"v2 更薄"）+五门（A YES/B YES/C PARTIAL/D NOT_REQUIRED/E PORT_CHANGE_REQUIRED）→ **T1A_ARCHITECTURE_READY**+G0_PORT_CONTRACT_CHANGE_REQUIRED 登记；§29 WT0 四脚本复跑逐位一致+回归 21+vp+fast 43 绿 | 2026-09-18 | 563ac0b |
| WT0 | World–Boundary–Transduction 联合资格轮（R-1~R-4 裁定后执行）：三对象合同+Y_B 双配置冻结(R-3)；正对照 ESTABLISHED（三门 PASS，分叉 18.6811=外部基准）；Replay 两 Gate 逐位一致 HIDDEN_SIDE_CHANNEL=PASS；剂量攻击 R-4 复现 CONFIRMED（duration 390 精确吻合，q_max 差~1%归协议时长）；CrossPair 198 对合法域内无保真区（retention>1 失真或=0 湮灭）CO_ADAPTATION_RISK=HIGH；角色审计 OVERLAPPING_UNRESOLVED（u 按 dT_raw 速率语义被消费）→ 终裁 WT0_TRANSDUCTION_CONTRACT_UNRESOLVED（T1-A 解除职责重叠后 W1 方可开工，与 R-1 序一致）；回归 21+vp+tss fast 43 绿 | 2026-09-18 | f8a14da |
| WT0/T1A评判 | 两外部方案评判分析：窗口数值核实无误；Hidden-World 正对照完全复现且补全缺失协议(t_drive=100/amp=1.0,1.996/边界=node0 单节点)；职责混叠实锤(u 按 dT_raw 速率语义消费 vs ThermalDeltaNeuron dT/dt 合同)；4 项 RULING_REQUIRED(首轮归属/T0-B 命名/Y_B 边界基数/外部 G0 数据复现)；建议合并序 WT0→T1-A→W1→T1-B→G0；存档 交叉比对/ 并抄送主仓 | 2026-09-18 | d5dcb96 |
| Phase T0 | 𝒟_i 转导合同重资格化（测量轮，nexus_v1/tss 零改动）：资格窗双侧有界 scale∈[0.65,1.5]（0.36 十倍程，地板侧实测夹层含解析预测✓，高幅侧新发现顶棚塌缩）+u_interior 违约（参考类轨迹>92%被地板 clip，占比≤5.3%）+W0-E 窗内放大定性为基线归零失真+下游利用率41%→TRANSDUCTION_V2=REQUIRED；T1 设计要点4项登记；回归21+vp+tss fast 43 绿 | 2026-09-18 | 6548e24 |
| 主线重启-R1 | TSS收尾与主线重启第一轮(F0+M0+W0)：TSS_FREEZE冻结文档(13项+四分类表替代目录重组)+MAINLINE_COMPONENT_AUDIT(七类归类,温感实例登记层剥离)+WORLD_V1_REQUALIFICATION(W0-A~E实测:3自由度/单尺度/线性单吸引子/域内PRESERVED域外COLLAPSE→塌缩在D_i转导窗非场层;WORLD_V2=REQUIRED)+P2_TSS对照矩阵(7行无一凭名判同);母体21+tss fast 43+G0 7/7绿 | 2026-09-18 | fbccfa1 |
| F1-R4 | F1 A8-v2 最小物理闭合复审(第四轮)：rail因果化(路径B电导×负载线,断电I_fb逐位0,分界720步=解析T_off*)+N=1最小化(能耗基准83.66/582.42双复现)+方法勘误3件(clamp等时长20s复测DT_LIMITED保持/census全递归1125项/spike_times分类purge实证)+M5-P第六门PASS→F1_A8v2_PHYSICALLY_VALIDATED(条件化Scale-B);新fingerprint bdbdb0305c191e94;21/21+tss fast 43绿 | 2026-09-18 | a312190 |
| Skill化瘦身 | CLAUDE.md 28.9KB→15.7KB：按需知识移入4个项目skill(.claude/skills/ verify-regression/work-report/exp-script/new-component)，每会话省~5k token；过时Current state(2026-07-02)替换为暂停快照指针；修正失效引用(*.log→test_runs/、七节→六段式) | 2026-09-17 | d75a6e2 |
| DA重标验证 | T-088 RPE签名3/4(新奇爆发/撤源dip/非饱和;S1阈值假失败)+T-089热趋性保全2/4(P1到源/P4动态PASS;P2/P3非回归=第二把锁);印证两把锁模型;安全 | 2026-07-08 | 2b711ac |
| DA源重标(总闸门) | 修DA=1.0饱和：intake_to_da sg1.0→0.05(G(w=1)=10致10×超标)/shadow_to_da sg1.0→0.1(col饱和);拒绝AG Fix-2(satiety-5.0→DA≡0);实测DA恢复动态范围(接近1.0→进食0.2→撤源0.06);21/21 PASS | 2026-07-08 | 928d92a |
| STDP根因复核+方案评判 | ①STDP无意义两层根因(冗余+DA饱和)②DA=1.0修订版Fix-2评判(可逆性破坏)③修复方案补充评判(实测T-084修正病灶:intake+8~14A为真凶,非shadow BCM缺θ_M)；4份报告 | 2026-07-08 | — |
| T-080 运动势垫支 | DecisionCircuit三阶段全PASS：Phase A置信积分器/Phase B FSM+WTA/Phase C马达连接;6项修复(Memristor floor/GABA符号/dT_actual全列);体步骤3721到源驻留;21/21 PASS | 2026-07-08 | 4bb83b1 |
| T-071-fix-A Step4 | sp2y_w=0.200 × 200k长程：J1=1882步(PASS)/J3=0.0%漂移(PASS)/J5 ν=10^13量纲待诊断；Top-10 noci高Xin正常 | 2026-07-07 | — |
| T-084/T-085 | Z轴热觉8束（col_therm_top/bot_*→move_z ±2.5）+ spinal_fwd双侧收敛前进核团（1神经元+3束），21/21 PASS | 2026-07-07 | f1a44c9 |
| NuProbe集成 | NuProbe 挂入 VariantCircuit 主循环（每步update/1000步report），import+init+_ledger_post_step+summary()；CLAUDE.md强制规范更新 | 2026-07-07 | 3b03e6a |
| T-078 | w_cw异常衰减根因分析+修复：phasic.energy→0.001时_apply_metabolic_tax触发（7000×预期），fix-A=max(energy,0.5)；21/21 PASS | 2026-07-07 | c727201 |
| T-071-fix-A Step1-3 | sp2y_w 0.020→0.050→0.100→0.200；Step3 approach_step=1960（最佳），DR5=73.8%，无振荡；回归21/21 PASS | 2026-07-07 | 432406b |
| T-065 | 物理驱逐实验（100k步热源瞬移）：3/4 PASS；J2=43步重定位新源（vs设计30k步上限）；J3最近距=0.3；J4 FAIL=找源太快fill未下降5%（正向副作用）；热趋性泛化能力确认 | 2026-07-07 | 86c0821 |
| T-071 | STDP断路诊断：H-B确认（I_spinal/I_thermo=0.09%，1000:1悬殊）；sp2y_w=0.020是根因；phasic钳制-0.1V使D1学负向；报告T071_STDP断路诊断报告_2026-07-07.md | 2026-07-07 | 74c93fb |
| T-076 | 半规管信号注入（Phase 0+0.5+1）：Cupula IIR实装 + ANGULAR_GAIN=300000校准（MET_yaw=0.32）+ 旋转激活验证4/4 PASS（onset/adapt/stop反向/基线）；21/21 PASS | 2026-07-07 | 1c2cfd9/d35ac6b/1b64339 |
| T-075 | friction/NOCI标定：4/6 PASS；J1/J3 FAIL=设计缺陷（离散vs连续/梯度公式错误）；修订后6/6 PASS；NOCI余量16667×，热源外均值0.006 | 2026-07-07 | — |
| T-074 | 接口联立标定（muscle.gain+eta）：3/4 PASS；J1 v=0.1517✅；J2 FAIL=测试设计缺陷（body未锁定，接触效率38%）；J3 τ比=0.289✅；J4 step8622✅；eta=0.06文档已修正 | 2026-07-07 | — |
| T-072b | 冷期权重保留（100k，REGEN_PROB=0.0001）：3/4 PASS；冷期=2856步（短于预期10k）；DA_ema_min=0.9963（J3 FAIL=判据设计缺陷，冷期太短）；w_ccw 100%保留；τ_conf校准留阶段A就地做 | 2026-07-07 | — |
| T-072 | 热源消失多周期（200k，三周期）：形式2/4 PASS；修订后4/4 PASS；w_ccw保留率98.6%/150k步；T_rel3=1680<T_rel2=4832（65%改善）；J2/J3判据设计缺陷已记录 | 2026-07-07 | — |
| T-039b | 诈胡核查重跑（P0后全冻结STDP，50k）：3/3 PASS；DR5%=44.2%≤55%（随机基线）；w_ccw漂移=0.0004；P0不植入硬连线方向性 | 2026-07-07 | 0f85dc4 |
| T-073 | P0验证（50k）：3/3 PASS；w_ccw保留率99.8%（vs P0前≈0%）；Motor全程0=对流漂移主导运动（新增T-077诊断） | 2026-07-07 | 4d3526a |
| T-070 | η验证（BMR=0.003, VitalOsc→0.003→撤回0.005）：η=41%（单次填充陷阱），投影200k η=10.3%，VitalOsc撤回，BMR保留0.003；commit 86057a4 | 2026-07-07 | 86057a4 |
| T-068_prep | 物理接口规范文档（皮肤/口器/前庭/马达参数审计）| 2026-07-07 | — |
| T-068b | STDP架构解剖报告：学习目标冗余（D1弧重建已有硬连线）/CPC完全硬编码/梯度1D压缩/信号容量=1；四项缺陷分析；P0=DA慢积分(T-073) | 2026-07-07 | — |
| T-073_impl | P0实装：bundle.py DA_ema+lambda_metabolic；variant_adapter.py _D1_W0/WMAX/LR具名常量+_W_SPINAL_WTA HARDCODE-RECORD；21/21 PASS | 2026-07-07 | 4d3526a |
| T-067 | 交叉接线翻转实验（防诈胡第三层）：0/3 FAIL；正确束未能稳定击败反接束；Foraging窗口仅35k步，fill饱和后LTD冲洗消除所有分化；STDP无法在单次觅食窗口内完成方向线路选择 | 2026-07-07 | — |
| T-066 | 镜像几何实验（各200k步）：1/2 PASS；G1/G2 均对称衰减至w=0.0006（平局），Δw_F峰值0.192/0.199 ✅；方向未翻转（均名义CCW）FAIL；五样本多样性否定固定结构偏置 | 2026-07-06 | — |
| T-063 | 双热源鞍点实验（200k）：5/6 PASS；L2a=0.2511 ✅ DSI=56.49 ✅ SDI=91.8% ✅ η=8.4% ✅ 死锁1.9% ✅；侧选择FAIL（双饱和至0.300，30k内两侧均访问）；DR5=0.0%；T4.1=4.45x | 2026-07-06 | — |
| T-064 | BMR 0.002→0.0025验证（50k）：2/2 PASS；η=14.9% ✅；fill_min=0.2766 ✅；意外：CW胜出（vs T-062 CCW），同配置下胜出方随机，非结构偏置 | 2026-07-06 | — |
| T-062 | 200k新指标验收：5/7 PASS；L2a Δw=0.2881 ✅；L2b DSI=4.7M ✅（单热源饱和，标注不适用）；L2c η=4.59% ❌（触发T-064）；L1 DR5=0%（热源中心无梯度，正常）；T4.1=5.77x ✅；SDI=94.9% | 2026-07-06 | — |
| T-061 | 前庭消融验证（α=0.02 vs 1.0，各50k步）：PASS（DR5下降0% < 15%）；两组均DR5=0%（50k CPG随机性）；对照组step40k w_ccw=0.300>>w_cw=0.003短暂分化；HC-061登记（半规管零占位）| 2026-07-06 | — |
| T-060 | L2指标重构+50k基线：全部FAIL（DR5=0%，Foraging=0步）；body初始在热场外（dist=60>r=30），CPG随机性50k不足；确认L2指标需200k或双热源场景 | 2026-07-06 | — |
| T-059 | 200k步长程验证（T-058修复版）：L1/L3/L4/L5 PASS，L2 |Δw|=0.002（双束对称饱和，非STDP失效）；DR5=66.3%，dist@10k=0.4，SDI=92.5% | 2026-07-06 | 9d5485a |
| T-058 | T-057修复：P0-A探针(bundle名+T4.1路径)+P0-B gain_max 1.5→1.15；21/21 PASS，20k验证|Δw|=0.283@10k | 2026-07-06 | 9d5485a |
| T-057 | 200k步长程验证（原版）：L4/L5 PASS，L1/L2/L3 FAIL；脚本bug+fill饱和两重问题，见 T057_FAIL诊断报告 | 2026-07-06 | — |
| T-056 | 两阶段Phase2首次接触（20k步）：DA峰值1.0 ✅/fill 0.3→0.58 ✅/\|Δw\|=0（指标待改进，见报告） | 2026-07-06 | — |
| T-055 | 两阶段Phase1冷区BMR验证（25k步）：fill↓/hunger↑/phasic=0 均PASS；V4指标设计问题 | 2026-07-06 | — |
| T-054 | 诈胡验证（50k步STDP全冻结）：DR5=51.0%≤55% PASS，T-043非硬连线方向来源 | 2026-07-06 | — |
| T-050 | P2-H shadow_nu验证：ν实测值在百万级（>0.01 ✅），shadow输入激活s_enc_therm_front=1.23；nu_neuron.activation=0（_NU_SCALE校准问题，登记T-053）| 2026-07-06 | — |
| T-047 | P0-B：shadow层输入增强（16条frozen束：3 Motor+12 relay+1 energy），H_struct 7.03→7.14，21/21 PASS | 2026-07-06 | 85274e9 |
| T-048 | P1-G 饥饿r_leak调制（EMA τ=1000，_hunger_ema，gain≤1.5×），21/21 PASS，T4.1=4.04x | 2026-07-06 | bafeae4 |
| T-051 | P0-A relay侧向抑制：已存在（bundles_relay_lateral_inh 4条，sg=-1.0/w=0.3，已注册 get_all_bundles）| 2026-07-06 | — |
| T-044 | 50k 验证：4/4 PASS（DR5%=76.5%/|Δw|=0.110/无死锁2.2%/T4.1=3.30x）| 2026-07-06 | — |
| T-043 | yaw层交叉抑制束实装（spinal_ccw→yaw_cw + spinal_cw→yaw_ccw，W=0.020/sg=-1.0，frozen，get_all_bundles注册），21/21 PASS | 2026-07-06 | 4ac8d98 |
| T-042 | F-I曲线诊断：phasic钳位(-0.1V)是根本原因，Ia压制比1.09×（峰值），T-045取消，T-043参数W=0.020/sg=-1.0 | 2026-07-06 | — |
| T-046 | P1-F：前庭N=3激活（VestibularChain(n_hair_cells=3)，21/21 PASS，variant_adapter.py+1行import） | 2026-07-06 | — |
| T-041 | 200k步长程复测：T4.1全程3.65x→5.56x（PASS），P8-3/P8-4 FAIL（时间点问题）| 2026-07-05-06 | 08e4c76 |
| T-040 | 热源侧向反转：G1 PASS(w_ccw=0.2994>w_cw=0.0058)，G2 FAIL(CPG随机性50k不足) | 2026-07-05 | — |
| T-039 | D1消融诈胡核心验证：|Δw|=0，DR5%=50%(随机基线)，D1 STDP=唯一方向来源 | 2026-07-05 | — |
| T-038 | 50k步验证：T4.1 4.09→4.38x稳定，DR5%峰值75%，|Δw|=0.295，全部PASS | 2026-07-05 | — |
| T-037 | T4.1修复：VOR axis bundles 冻结STDP（3.97x）+ spinal_to_yaw w 0.002→0.020，21/21 PASS | 2026-07-05 | 44214c9 |
| T-036 | 200k步长程实验：全部PASS（P4-1 Δw=0.2991/P4-2 DR5%=60%/P4-3 w_ccw=0.2998），自我修复机制确认 | 2026-07-05 | — |
| T-035 | 两阶段实验第二阶段：50k步，P3-4/P3-5/P3-6 全部PASS，|Δw|=0.2821（CCW胜出，step 40k大逆转） | 2026-07-05 | — |
| T-034 | 两阶段实验第一阶段：20k步，P3-1/P3-2 PASS（fill 0.300→0.260，DA=0.66），P3-3 WARN | 2026-07-05 | — |
| T-033 | 50k步P0验证：P0-1/P0-2 PASS，P0-3 FAIL（热场环境不适合），yaw权重衰减（phasic≈0） | 2026-07-05 | — |
| T-033(P0) | P0三条物理修复：phasic钳位/intake→DA/BMR | 2026-07-05 | cac24ca |
| T-032 | 200k 步长程实验：fill=0.999✅，yaw FAIL（无分化），T4.1=0.25x，DA@热源=0.0（需分析） | 2026-07-05 | — |
| T-031 | Step 7：脆弱点3 V_feed→CPC + relay自适应增益（gate control AGC） | 2026-07-05 | a3aa9c6 |
| T-030 | Step 4：consume_nearby 移除（ThermalMouth 摄食切换） | 2026-07-05 | 9c31026 |
| T-031a | repair_cost 累积→瞬时+回归测试重标定（T4.1/T3.2） | 2026-07-05 | d20c443 |
| T-029 | 能量链修复：ThermalMouth eta 0.02→0.06 | 2026-07-05 | 818ce17 |
| T-028 | 饱腹 P1 Step 6：脊髓推挽互抑 Ia interneurons（sg=-1.0, w=0.1） | 2026-07-05 | 6c3fa65 |
| T-027 | 饱腹 P0 Step 5：slow_relay τ 双侧同步 5000→15000 + _W_RS 同步 | 2026-07-05 | 89ac1d5 |
| T-025 | 饱腹 P0 Step 1-3（IntakeSensor钳位+SatietyV_ss验证+Schmitt触发器） | 2026-07-05 | db9819c |
| T-012 | DelayedBundle 前庭接入（Aα/C纤维延迟） | 2026-07-05 | 38eec5c |
| T-011 | Ca²⁺ Phase B（CalciumChannel 接入 HairCell） | 2026-07-05 | 38eec5c |
| T-010 | HC-008 ReleaseNeuron（Ca²⁺→IHC重构） | 2026-07-05 | 38eec5c |
| T-024 | 前庭 Phase B（N=1→3 扩展）| 2026-07-04 | ec582fd |
| T-023 | 规模泛化 Prep（SkinPatch/Body 物理几何属性） | 2026-07-04 | 507921f |
| T-022 | 体感 Phase 3：环流耦合清洁化 | 2026-07-04 | 1121a72 |
| T-021 | P2-8 短程测试：noci 热前锋响应验证 | 2026-07-04 | — |
| T-020 | SomatosensoryChain 12贴片实际激活（T-015遗漏） | 2026-07-04 | 845ebf2 |
| T-015 | 体感重构 Phase 2：4→12贴片扩展（chain.py常量） | 2026-07-04 | c380be6 |
| T-014 | HC-011 shadow全连接（if/elif→21束STDP） | 2026-07-04 | 55bd015 |
| T-009 | HC-010 AGC移除+stub向后兼容 | 2026-07-04 | 55bd015 |
| T-008 | HC-025 MotorRhythm Kuramoto→VdP | 2026-07-04 | fd79dfe |
| T-007 | Ca²⁺ Phase A（CalciumChannel+CalciumDynamics 独立组件） | 2026-07-03 | 7963d28 |
| T-006 | HC-009 Phase 2（ThermalInputNeuron+NociInputNeuron+换能束） | 2026-07-03 | bc6d292 |
| T-005 | HC-009 Phase 1（ThermalInputNeuron 骨架） | 2026-07-03 | 51d4c41 |
| T-004 | EnergyStore 物理化+三接口 | 2026-07-03 | 6b296fd |
| T-003 | HC-016 yaw方向性（thermo_input→yaw bundle） | 2026-07-03 | — |
| T-002 | P0 HC-005/006/013/018 删除+DR5 patch温差 | 2026-07-02 | — |
| T-001 | P2 HC-007/002 relay→enc STDP bundles | 2026-07-02 | 5c2fade |

---

## ❌ 取消/无效

| ID | 任务描述 | 取消原因 |
|:---|:---|:---|
| T-052 | P0-C S2 spinal门槛调整 | S2参数从未被写入代码，当前 v_threshold=0.01 正常工作，v5.0文档分歧已消除 |
| T-049 | P1-D feed_alignment物理重建 | HC-006零值问题已由 T-031（Step7 _v_feed→CPC）解决，不需要再加relay_front路径 |
| T-053 | nu_neuron校准修复（_NU_SCALE/τ失配） | 远景阶段二再激活。当前P0主线不需要ν→DA工作。物理分析保留为技术笔记（T-053分析报告_2026-07-06.md） |

---

## 使用规则（Claude 操作说明）

### 何时读取
- **每次会话开始**：第一步读取本文件，掌握积压状态
- **用户要求"继续"/"做下一步"时**：先看这里

### 何时写入
| 事件 | 操作 |
|:---|:---|
| 决定做某任务 | 移入"⚡执行中"，写开始日期 |
| 任务完成 | 移入"✅已完成"，填 Commit hash |
| 发现遗留/新需求 | 加入"📋待执行" |
| 用户说暂缓 | 移入"⏸暂停"，写恢复条件 |
| 确认不做 | 移入"❌取消"，写原因 |

### 任务 ID 规则
- 新任务：看当前最大 ID+1，例如已有 T-024 则下一个是 T-025
- 不重复使用旧 ID

### 上下文压缩前
将所有"⚡执行中"的任务备注写清楚（进展到哪一步、下一步是什么），防止压缩后丢失上下文。
