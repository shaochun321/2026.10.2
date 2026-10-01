# MFS0-E0 Step 0/A/B/C 签收与下一批执行裁定

## 1. 当前签收

正式接受：

```text
STEP_0 = PASS
STEP_A = PASS
STEP_B = PASS
STEP_C = PASS

MFS0-M2 = PASS
MFS0-M3 = PASS
READOUT_FEASIBILITY = PASS

READY_FOR_STEP_D = YES
READY_FOR_MAIN_FACTORIAL = NO
```

`READY_FOR_MAIN_FACTORIAL` 暂不翻转的唯一阻断项是：

```text
STRICT_TIMING_CONTROL_NOT_YET_FROZEN
```

---

# 2. Step D 第一任务：严格区分三种 timing

不得把所有 later windows 简化为 NEAR/FAR。

必须区分：

```text
NEAR
WEAK_OVERLAP
ZERO_ELIGIBILITY_TIMING_CONTROL
```

当前：

```text
s23_far_b
```

由于仍与 eligibility write-reachable window 重叠 110 steps，只能登记：

```text
WEAK_OVERLAP
```

不得登记为：

```text
TIMING_CONTROL
```

---

# 3. NEAR 冻结规则

主实验建议冻结：

```text
NEAR = s23_ov
```

理由：

```text
first valid full-overlap candidate
predicted |Δw| = 6.08e-2
safely above floor
not selected by maximum expected effect
```

`s23_hold_timing` 可留作 secondary timing / sensitivity condition，不作为 canonical NEAR。

---

# 4. TIMING CONTROL 冻结规则

必须寻找：

```text
t_delta > eligibility_write_window_end
```

当前：

```text
eligibility_write_window_end = 4689
```

要求：

```text
FET_e.conduct(e) = 0
```

在 later write interval 全部成立或落在预注册 numerical tolerance 内。

同时尽可能满足与 NEAR：

```text
same site
same stimulus amplitude
same pulse/support duration
same physical path
same transduction family
same H_tau configuration
```

优先审计已冻结库存中：

```text
t_up = 5402
t_up = 6344
```

等晚时点 site23 trajectories。

在使用以前必须先进行：

```text
TIMING_MATCH_AUDIT
```

比较：

```text
source identity
pulse parameters
support duration
typed input family
occurrence duration
physical path
```

若找到严格匹配：

```text
STRICT_TIMING_CONTROL_AVAILABLE = TRUE
```

才冻结。

若不存在：

```text
STRICT_TIMING_CONTROL_AVAILABLE = FALSE
READY_FOR_MAIN_FACTORIAL = NO
```

不得用 `s23_far_b` 冒充零 eligibility control。

---

# 5. Step D 必须冻结的三个剩余量

在看到任何 factorial 输出以前写入 preregistration。

## epsilon_sel

```text
epsilon_sel =
max(
    10 * replay_or_nowrite_dw_floor,
    1e-6
)
```

## S_min

```text
S_min = 10
```

并要求：

\[
|\Delta w_{TC}|
/
|\Delta w_{NEAR}|
<0.1.
\]

ratio 不能独立构成 PASS。

同时必须：

\[
D_{sel}
=
|\Delta w_{NEAR}-\Delta w_{TC}|
>
\epsilon_{sel}.
\]

## predicted_I_z

由冻结的 Step A/B 轨迹和冻结 NEAR 条件解析生成。

不得从 factorial 结果拟合。

若：

```text
NEAR = s23_ov
```

当前预期 signed depletion：

```text
predicted_I_z ≈ -6.08e-2
```

最终值由脚本从冻结数据重新计算并落盘，不手工复制。

---

# 6. 文档勘误

原报告：

```text
四者均落在 e 写入可达窗内
```

改为：

```text
四个候选均与 e 写入可达窗存在非零 overlap；
其中 lag / far_b 只有部分窗口可写。
```

---

# 7. tau_e 身份补充

冻结值保持：

```text
TAU_E = 0.300 s
```

不得回调。

但依据分为：

```text
PHYSICAL PRIOR
= sub-second eligibility-like transient

DESIGN / IDENTIFIABILITY CONSTRAINT
= tau_e < tau_relation < tau_H
  to maintain temporal separability
```

不得声称：

```text
0.300 s is uniquely derived from project physics
```

---

# 8. M 的正式解释

冻结：

```text
M(t) =
recent later-entry history carried by H_tau_delta
```

不得解释为：

```text
reward
value
error
later-event intensity
later-event semantic importance
```

collector 多次 release 与 `b_up=1` 不意味着 M 编码 release count。

---

# 9. WRITE_DT_CORRECTION

继续沿用 research-side：

\[
I_{\rm arg}
=
I_{\rm write}\Delta t.
\]

但代码与报告必须明确：

```text
Memristor.update(current=...)
```

当前 API 的 `current` 参数在本轮调用中实际接收的是：

```text
time-integrated write-current increment
```

这是 production API 的量纲债务 workaround，不是新的物理参数。

所有 arm 必须统一使用。

本轮结束后登记独立 DEG：

```text
MEMRISTOR_UPDATE_MISSING_DT
```

具体编号按届时 registry 下一可用编号分配。

---

# 10. Step D 完成后的 Gate

只有同时满足：

```text
NEAR_FROZEN
STRICT_TIMING_CONTROL_FROZEN
epsilon_sel_FROZEN
S_min_FROZEN
predicted_I_z_FROZEN
budget_legal
```

才允许：

```text
READY_FOR_MAIN_FACTORIAL = YES
```

然后严格继续：

```text
Step E
→ NC1..NC6
→ washout
→ Step F
→ Step G
→ Step H
→ hold6
→ MFS0-M1..M6
→ terminal A..F
```

不得在 Step D 后重新修改：

```text
tau_e
tau_M
w0
FET thresholds
write polarity
write dt correction
NEAR
TIMING CONTROL
selection thresholds
```