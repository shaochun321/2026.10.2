# 复现

## 环境

- Windows，Python 3.14，只用标准库，无第三方依赖。
- 源码位于同目录的 `src/`，是从提交 4d4e424 用 `git archive` 导出的版本（见 `source_manifest.json`）。
- 运行时加 `-B`，不写 pyc。

## 入口与预期成本（单进程）

```bash
cd research/mfs0_e1
PYTHONIOENCODING=utf-8 python -B a_probe_transduction.py   # 模板溯源、入口脉冲、dt 探针        约 5 s
PYTHONIOENCODING=utf-8 python -B c_mapping.py              # 阶段 C 短程映射 → results/mapping.json  约 30 s
PYTHONIOENCODING=utf-8 python -B d_main.py                 # 阶段 D：24 条流 + 8 条基线 → results/D_main.json  约 21 min
PYTHONIOENCODING=utf-8 python -B e_two_history.py          # 阶段 E：12 条流 + 4 条共享基线 → results/E_two_history.json
```

## 确定性

- 生成器种子写在 `preregistration.json`。模型里没有随机数，同样的输入会得到逐位相同的结果（前缀一致性检验已证实）。
- 冻结文件的哈希见 `results/freeze_hashes.json`，是在任何正式流生成之前记录的。

## 运行账本

`runs.jsonl` 是追加式账本，逐条记录每次运行（含开发运行与冒烟测试）的阶段、run_id 和墙钟时间。
