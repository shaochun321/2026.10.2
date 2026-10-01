# MFS0-E2 研究包

完整报告在主仓：`J:/cell-cc/cell-cell/工作报告/MFS0-E2轮工作报告_2026-10-01.md`。理论、方程和接口契约见 `THEORY.md`。

## 模块

| 文件 | 职责 |
|:--|:--|
| memory_core.py | 长期载体、经历槽 T/O、局部资格、观察，以及合流写入（每个载体节点只求一次解） |
| current_input_bridge.py | ReplayBridge（R 路径：模板平移）、LiveBridge（L 路径：项目 BaseGenerator → CollectorBoundaryPort → PhysicalEntryGate） |
| prediction_port.py | 不可变的 PredictionRecord、PredictionPort、ThresholdConsumer（阈值 0.65） |
| stream_runner.py | 持续步进；PulseReplay / PulseInjector 用于对照组和核心压力层 |
| reference_solver.py | 连续参照解，只用于评价 |
| scenario_builder.py | 主任务流和压力流的生成器（只在源端运行） |
| evaluate_system.py | 全流评价、终态判定，并输出轨迹图 |
| run_e2.py | 单一入口：dev / formal / stress / live / report |
| example_interface.py | 接口最小调用样例 |
| dev_checks.py、dev_pipeline_smoke.py | 开发检查（只用开发种子 99xxx） |
| prereg_E2.json、results/freeze_E2.json | 冻结的协议与代码哈希 |
| runs.jsonl | 追加式运行账本；并行运行的成本逐项累加 |

## 复现（单进程下的预期墙钟）

```bash
cd research/e2
PYTHONIOENCODING=utf-8 python -B dev_checks.py          # 约 50 s，results/dev/
PYTHONIOENCODING=utf-8 python -B example_interface.py   # 约 3 s
PYTHONIOENCODING=utf-8 python -B run_e2.py formal       # 4 进程约 40 min（累计约 2.3 h）
PYTHONIOENCODING=utf-8 python -B run_e2.py stress       # 2 进程约 14 min
PYTHONIOENCODING=utf-8 python -B run_e2.py live         # 约 4.5 min
PYTHONIOENCODING=utf-8 python -B run_e2.py report       # 评价 + results/E2_stream0_trajectory.png
```

确定性：在新进程中重跑 stream 0，三种条件的记录与终态载体都逐位一致（results/repro/）。
