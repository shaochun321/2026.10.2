# MFS0 independent-copy research packages (E1 v4 → E3)

These are the independent research copies of the MFS0-E1 v4 through E3 rounds.

- **Origin:** `C:/Users/shaoc/Documents/Codex/2026-09-24/files-mentioned-by-the-user-2026/work/<dir>`.
- **Committed to git:** 2026-10-02.
- **Integrity:** every file is a byte-identical mirror; sha256 values are in `MANIFEST.sha256`.
- **Not committed:** `src/` and `__pycache__`.

Each copy's `src/` is exactly the project tree at commit **4d4e424**. All six copies were checked: 778/778 files match by blob hash.

| Round | Directory | Package | Report (`cell-cell/工作报告/`) | Verdict |
|:--|:--|:--|:--|:--|
| MFS0-E1 v4 | mfs0_e1_execution_v4 | research/mfs0_e1 | MFS0-E1_v4轮工作报告_2026-09-30.md | implementation/mapping/adaptation PASS; two_history INCONCLUSIVE |
| MFS0-E1.1 | mfs0_e1_1 | research/e1_1 | MFS0-E1.1轮工作报告_2026-09-30.md | two_history PASS; write-modulation INTERFACE_PASS |
| MFS0-E1.2 | mfs0_e1_2 | research/e1_2 | MFS0-E1.2轮工作报告_2026-09-30.md | POLICY_NOT_JUSTIFIED |
| MFS0-E1.3 | mfs0_e1_3 | research/e1_3 | MFS0-E1.3轮工作报告_2026-10-01.md | POLICY_NOT_JUSTIFIED (auto-rate branch paused) |
| MFS0-E2 | mfs0_e2 | research/e2 | MFS0-E2轮工作报告_2026-10-01.md | E2_PARTIAL |
| MFS0-E3 | mfs0_e3 | research/e3 (+ identical copy of research/e2) | MFS0-E3轮工作报告_2026-10-02.md | E3_PARTIAL |

## Reproduction

The packages use relative paths:
- `e1_common.py` resolves `../../src`;
- `e3_common.py` resolves `../e2`.

So first rebuild `src/` inside the copy. `.gitignore` excludes it, so it cannot be committed by mistake.

```bash
cd research/mfs0_runs/mfs0_e3
mkdir src && git archive 4d4e424 | tar -x -C src
cd research/e3
PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8 python -B example_interface_e3.py
PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8 python -B -c "import run_e3; run_e3.load_prereg(); print('prereg hashes OK')"
```

`PYTHONHASHSEED=0` is mandatory: live-bridge input amplitudes depend on `hash()`.

Formal results (`results/**.pkl`) and the cost ledgers (`runs.jsonl`) are committed as evidence. The run logs are `*.log` files; they were force-added despite the repo-wide `*.log` ignore.

The `results/**/X/` domain directories were also force-added. The repo-wide `x/` backup-folder rule matches `X/` because Windows paths are case-insensitive, so any later addition under `X/` needs `git add -f`.

`research/mfs0_runs/** -text` in `.gitattributes` keeps every file byte-exact on checkout. This matters because 94 text files use CRLF line endings, and the frozen sha16/sha256 hashes are computed over raw bytes.

## Incident note

On 2026-10-01 at 21:38, a Claude Code rewind in session d7fa5ca5 deleted every E2 file that had been created with the Write tool:
- the sources and prereg;
- README and THEORY;
- the work report and the memory file.

They were restored from `~/.claude/file-history/d7fa5ca5-…/<hash>@v2`, and all 12 `freeze_E2.json` hashes match. Committing these packages is the safeguard against a repeat.
