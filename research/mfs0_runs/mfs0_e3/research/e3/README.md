# MFS0-E3 Research Package (Conditional Relation Memory and Structure Synthesis)

- The full report is in the main repo at `J:/cell-cc/cell-cell/工作报告/MFS0-E3轮工作报告_2026-10-02.md`.
- Theory, structure and idealisations are in `THEORY.md`.
- The baseline is `../e2`, the E2 package restored from file-history and checked against all 12 `freeze_E2.json` hashes. Group B uses its MemoryCore without modification.

## Modules

| File | Role |
|:--|:--|
| context_trace.py | 4 shared RC event traces + threshold comparators |
| relation_spec.py | candidate family C1–C7 + independent time reference (evaluation only) |
| relation_operator.py | node implementation of the conditions (comparators / switch network) + device cost |
| structure_select.py | offline selector on the E2 streams (D1 select / D2 validate); not part of the runtime |
| routing_latch.py | K latch: set / hold / read / reset after settlement / free condition |
| conditional_memory_core.py | marginal + conditional carriers, per-node solution, frozen step order |
| reference_solver_e3.py | independent continuous reference (evaluation / selection only) |
| prediction_port_e3.py | immutable PredictionRecordE3 (condition_id / value / net / read_path / p_hat_marginal) |
| stream_runner_e3.py | lockstep runner: one input pass fans out to B/C/R; the R random port; deepcopy checkpoint |
| scenario_builder_e3.py | A (E2 G1) / X (joint task) / L (live stimulus) / S (E2 stress) sources |
| layout.py | occupancy intervals, dedicated vs pooled layout, device count, relation hypergraph |
| run_e3.py | single entry: A / X / L / S / repro / report |
| evaluate_e3.py, plot_e3.py | evaluation, verdicts, trajectory figure |
| dev_checks_e3.py | mechanism checks + condition-flip suite (dev seeds / core injection) |
| make_prereg.py → prereg_E3.json | freeze: relation table, seeds, gates, deviations, code hashes |
| example_interface_e3.py | minimal call example |
| runs.jsonl | append-only cost ledger (dev + formal; parallel costs added item by item) |

## Reproduction

Run every command with `PYTHONHASHSEED=0`.

```bash
cd research/e3
PYTHONHASHSEED=0 python -B dev_e2_restore_check.py    # E2 hashes + 120 s bit-identical prefix
PYTHONHASHSEED=0 python -B structure_select.py        # results/selection/
PYTHONHASHSEED=0 python -B layout.py                  # results/layout/
PYTHONHASHSEED=0 python -B dev_checks_e3.py           # results/dev/
PYTHONHASHSEED=0 python -B example_interface_e3.py
./formal_all.sh                                       # A, X, L, S, repro, report (3 workers)
```

`run_e3.py` refuses to run in either of these cases:
- the code hashes do not match `prereg_E3.json`;
- a result file already exists.
