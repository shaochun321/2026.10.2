# MFS0-E1 源码来源清单（阶段 A）

日期：2026-09-30  
执行计划：`EXECUTION_PLAN_V3.md` @ 538f6c8  
工作位置：`C:/Users/shaoc/AppData/Roaming/warp/Warp/data/worktrees/cell-cc/mfs0-e1`（worktree，分支 mfs0-e1）

---

## 一、E0 提交号（mesquite-gecko 分支）

| 提交 | 日期 | 内容 |
|:---|:---|:---|
| 13265d1 | 2026-09-29 | MFS0-E0 收口修订（RULING-MFS0-R5 落地，closure_amendment.py/json） |
| 2c0ccc3 | 2026-09-29 | MFS0-E0 终裁（final_qualification.py，六门汇总+终态A→A_CONDITIONAL） |
| 7bb53a4 | 2026-09-29 | MFS0-E0 hold6 封存（heldout_seal.json先写后提交，manifest+SHA） |
| 7d6b278 | 2026-09-29 | MFS0-E0 Step G+H（state_intervention.py，双向do(w)+读出切断） |
| 1deed56 | 2026-09-29 | MFS0-E0 Step E+F（factorial_trials.py，e/M同时驱动+原位query） |
| 9ab665f | 2026-09-29 | MFS0-E0 Step D（timing_freeze.py，NEAR/TC分类+三阈值冻结） |
| da97cc3 | 2026-09-29 | MFS0-E0 Step 0/A/B/C（四门全PASS，τ_e/τ_M实测+写入可达窗） |

**E1 本地提交（mfs0-e1 分支）：**

| 提交 | 日期 | 内容 |
|:---|:---|:---|
| 538f6c8 | 2026-09-30 | E1 执行计划 v3 落地版（EXECUTION_PLAN_V3.md） |
| 951ec1b | 2026-09-29 | D0 修订（撤回"R-2必需"，候选P/R按ρ择一） |
| a108f9e | 2026-09-29 | D0 器件设计单（FEASIBLE_IN_RATIOS_PENDING_CAUSAL_E） |
| adc3317 | 2026-09-29 | E0 修复（FC1~4 PASS，拒绝覆盖检查真正落地） |

---

## 二、E0 原路径与内容 SHA（用于溯源）

| 文件 | E0 路径（mesquite-gecko） | SHA-256（头 16 字节） |
|:---|:---|:---|
| timing_freeze.py | `research/memory_feedback_substrate_v0/timing_freeze.py` @ 9ab665f | 待计算 |
| factorial_trials.py | `research/memory_feedback_substrate_v0/factorial_trials.py` @ 1deed56 | 待计算 |
| state_intervention.py | `research/memory_feedback_substrate_v0/state_intervention.py` @ 7d6b278 | 待计算 |
| heldout_eval.py | `research/memory_feedback_substrate_v0/heldout_eval.py` @ 7bb53a4 | 待计算 |
| final_qualification.py | `research/memory_feedback_substrate_v0/final_qualification.py` @ 2c0ccc3 | 待计算 |
| closure_amendment.py | `research/memory_feedback_substrate_v0/closure_amendment.py` @ 13265d1 | 待计算 |

**设计参考**：
- E0 冻结参数：τ_e = 0.300000 s（实测）；τ_M = 0.600000 s（实测）；ε_sel = 1e-6；S_min = 10
- E0 写入可达窗：[2893, 4689] 步（≠存在窗 [2618, 8473]）
- E0 实测 Δw 范围：TC 精确 0，NEAR −6.078119e-2
- E0 Retention_w：1.0（实测，washout 后 w 无衰减）

---

## 三、E1 独立输出路径

**输出根目录**：`research/predictive_memory_v1/data/e1_*/`

| 子目录 | 用途 |
|:---|:---|
| `e1_stage_a/` | 阶段 A：源码清单、误差预算、成本草案 |
| `e1_stage_b/` | 阶段 B：器件实现、状态表、节点图、解析参考 |
| `e1_stage_c/` | 阶段 C：短程映射数据（8 个 p × 50~100 次） |
| `e1_stage_d/` | 阶段 D：冻结参数、连续适应记录 |
| `e1_stage_e/` | 阶段 E：双历史探针（条件满足时） |
| `e1_stage_f/` | 阶段 F：汇总交付（最终报告、SHA） |

**运行记录命名**：
```
e1_{stage}_{sub_task}_{param}_{run_id}.json
```

例：`e1_stage_c_short_mapping_p08_r001.json`

---

## 四、.git 共享偏离登记

**偏离 v3 §6 要求**：继续在 worktree `mfs0-e1`（共享 `.git/`），不导出独立副本。

**原因**：
- adc3317（E0 修复）与 a108f9e（D0）已在 mfs0-e1 分支
- 导出到新独立目录会丢失已有提交历史
- 重新 git init 成本高

**保护措施**：
1. mesquite-gecko 工作区保持只读，`git status` 每步核查
2. 所有实验数据、输出、临时文件只写入 mfs0-e1 的 `research/predictive_memory_v1/data/`
3. 不触碰原工作区路径（`C:/Users/shaoc/AppData/Roaming/warp/Warp/data/worktrees/cell-cc/mesquite-gecko`）
4. Python 以 `-B` 运行，不产生新字节码

**记录位置**：
- v3 评判：`J:/cell-cc/cell-cell/交叉比对/MFS0-E1贯通方案v3评判_2026-09-29.md` § 六
- D0 文档：`D0_DEVICE_DESIGN.md` 追加节（待写）
- 执行计划：`EXECUTION_PLAN_V3.md` § 二.A
- memory：`C:/Users/shaoc/.claude/projects/J--cell-cc/memory/project_mfs0_e1_v3_plan_adopted.md`
- 本清单：当前文档

---

## 五、下一步

阶段 A 剩余交付物：
1. 参数来源表（D0 冻结值 + 误差预算分配）
2. 运行记录格式（run_id / 调用次数 / 预算集合 / 内部子仿真）

见 `A_ERROR_BUDGET.md`（下一步创建）。
