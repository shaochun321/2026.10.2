"""final_qualification.py — MFS0-E0 六门终裁（MFS0-M1~M6）+ 终态 + 收口完整性。

TYPE:INFRA（research/ 层；production READ_ONLY）。

依据：修订方案 §24（六门）、§29（终态 A~F）、§30（硬停止）、§10.1（SHA 收口）。
只汇总各步已落盘的证据，**不运行任何新臂**；另做四项收口核查：
上游 SHA BEFORE==AFTER、production/tss 自本轮起点零 diff、预算合法、
hold 封存一致。

输出分离（复核意见 §3.1，2026-09-29）：本程序的汇总写入
`qualification_historical.json`（历史口径，可反复重算）；正式生效状态
`qualification_summary.json` 是唯一有效状态入口，已带裁定时本程序拒绝
写入（ALREADY_RULED）。

运行：python -m research.memory_feedback_substrate_v0.final_qualification（repo 根）
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import mfs0_common as M  # noqa: E402
import preregistration as PR  # noqa: E402
from heldout_eval import _sha  # noqa: E402
from tss.adapters.relation_occurrence_port_v1 import (  # noqa: E402
    RelationOccurrencePortV1)

HISTORICAL_FILE = 'qualification_historical.json'
EFFECTIVE_FILE = 'qualification_summary.json'   # 唯一有效状态入口

ROUND_BASE_COMMIT = "da97cc3"      # Step 0/A/B/C 收口后、本批开工前的 HEAD
SEAL_COMMIT = "9c4dfb8"            # Step 0：frozen_upstream_seal.json 写入的提交


def _load(name):
    with open(os.path.join(M.DATA, name), encoding='utf-8') as f:
        return json.load(f)


def _git(*args) -> bytes:
    return subprocess.run(["git", *args], cwd=M._ROOT, capture_output=True,
                          check=True).stdout


def seal_check(seal_targets: dict) -> dict:
    """SHA 收口的两层核查。

    第一层（原始字节）：本 checkout 的文件字节 SHA 与 Step 0 封存值比较——
    照算照报，不改规则。封存在主仓 checkout 计算，而本 worktree 的
    checkout 换行符不同（core.autocrlf=true 下两处 checkout 时点不同），
    故原始字节可能不等。
    第二层（内容）：去除 CR 后，与 git 在封存提交中存储的 blob 比较。
    判定以第二层为准；第一层不等但第二层相等的，登记为 EOL_ONLY 并列出。
    """
    raw_mismatch, eol_only, content_changed = [], [], []
    for rel, h in seal_targets.items():
        if PR.sha256_of(rel) == h:
            continue
        raw_mismatch.append(rel)
        with open(os.path.join(M._ROOT, rel), 'rb') as f:
            wt = f.read().replace(b'\r\n', b'\n')
        blob = _git("show", f"{SEAL_COMMIT}:{rel}").replace(b'\r\n', b'\n')
        (eol_only if wt == blob else content_changed).append(rel)
    return {"raw_byte_mismatch": raw_mismatch, "eol_only": eol_only,
            "content_changed": content_changed,
            "content_unchanged": not content_changed}


def budget_check(led: dict):
    """预算合法性（复核意见 §3.1-3）：attempted 与有效运行一并计入上限。

    原 ledger 口径把 attempted 排除在 used 之外，会让超限的失败尝试仍报
    budget_legal。此处 used 统计全部条目；attempted 另列以便追溯。
    """
    used = {}
    for e in led["entries"]:
        used[e["category"]] = used.get(e["category"], 0) + 1
    attempted = [e for e in led["entries"] if e["attempted_only"]]
    ok = all(used.get(c, 0) <= cap for c, cap in led["caps"].items())
    return ok, used, attempted


def write_effective_status(historical: dict) -> str:
    """唯一有效状态入口的写入守卫（复核意见 §3.1-2）。

    若正式文件已存在且带裁定（terminal_state.superseded_by），**拒绝写入**：
    生效状态只能由裁定落地脚本（closure_amendment.py）以追加方式修改。
    仅当正式文件不存在时（首次终裁），才以历史汇总初始化之。
    """
    path = os.path.join(M.DATA, EFFECTIVE_FILE)
    if os.path.exists(path):
        cur = _load(EFFECTIVE_FILE)
        if "superseded_by" in cur.get("terminal_state", {}):
            return (f"{EFFECTIVE_FILE} UNCHANGED (ALREADY_RULED: "
                    f"{cur['ruling_applied']['ruling_id']} -> "
                    f"{cur['ruling_applied']['effective_terminal']})")
        return f"{EFFECTIVE_FILE} UNCHANGED (exists; historical only)"
    M.write_json(EFFECTIVE_FILE, historical)
    return f"{EFFECTIVE_FILE} INITIALISED from historical summary"


def production_diff() -> list:
    out = subprocess.run(
        ["git", "diff", "--name-only", ROUND_BASE_COMMIT, "HEAD", "--",
         "nexus_v1", "tss", "governance"],
        cwd=M._ROOT, capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines()
            if p.strip() and "__pycache__" not in p]


def main() -> int:
    M.assert_no_step_era_import()
    elig = _load('eligibility_characterization.json')
    modu = _load('modulation_characterization.json')
    sem = _load('semantic_erasure_audit.json')
    td = _load('timing_manifest.json')
    fr = _load('factorial_results.json')
    ci = _load('causal_interventions.json')
    ho = _load('heldout_results.json')
    seal = _load('frozen_upstream_seal.json')

    # ── 收口完整性 ──
    sc = seal_check(seal["targets"])
    prod_changed = production_diff()
    led = M.ledger_init()
    budget_ok, used, attempted = budget_check(led)
    hold_seal_ok = (_sha(_load('heldout_manifest.json'))
                    == _load('heldout_seal.json')["heldout_manifest_sha256"]
                    == ho["manifest_sha256"])

    ports = list(M.load_relation_ports().values())
    typed_ok = all(isinstance(p, RelationOccurrencePortV1) for p in ports)

    integrity = {
        "frozen_SHA_unchanged_content": sc["content_unchanged"],
        "production_unchanged_since_round_base": not prod_changed,
        "budget_legal": budget_ok,
        "heldout_locked": hold_seal_ok,
        "semantic_audit_PASS": sem.get("SEMANTIC_ERASURE_AUDIT") == "PASS",
        "lineage_valid": (modu["independence_R1"]["no_shared_e_carrier"]
                          and elig["W_material"]["lineage"]
                          == "relation.r_rho:d2_rho0"),
        "single_physical_time": M.DT_G == 0.001,
    }

    gates = {
        "MFS0-M1_typed_historical_entry": typed_ok,
        "MFS0-M2_physical_eligibility": elig["MFS0_M2"] == "PASS",
        "MFS0-M3_physical_later_modulation": modu["MFS0_M3"] == "PASS",
        "MFS0-M4_selective_persistent_deposition":
            fr["M4_selective_persistent_deposition"]["MFS0_M4"] == "PASS",
        "MFS0-M5_future_causal_action":
            fr["M5_future_causal_action"]["MFS0_M5"] == "PASS",
        "MFS0-M6_causal_carrier_integrity":
            ci["stepG"]["bidirectional_transfer"] and all(integrity.values()),
    }
    # 负对照 NC1~NC6（复核意见 §3.1-3：必要结果须进入终裁）
    nc = fr["negative_controls"]
    nc_ok = all(v["pass"] for v in nc.values())
    hold_ok = ho["HOLD6"] == "PASS"

    m4 = fr["M4_selective_persistent_deposition"]
    if all(gates.values()) and hold_ok and nc_ok:
        terminal = ("A", "MFS0_PHYSICAL_MEMORY_SUBSTRATE_CANDIDATE_QUALIFIED")
    elif not gates["MFS0-M2_physical_eligibility"]:
        terminal = ("B", "MFS0_PHYSICAL_ELIGIBILITY_NOT_ESTABLISHED")
    elif not gates["MFS0-M3_physical_later_modulation"]:
        terminal = ("C", "MFS0_PHYSICAL_MODULATION_NOT_ESTABLISHED")
    elif abs(m4["dw_near"]) <= M.EPSILON_Z:
        terminal = ("D", "MFS0_PERSISTENT_DEPOSITION_NOT_ESTABLISHED")
    elif not gates["MFS0-M5_future_causal_action"]:
        terminal = ("E", "MFS0_PERSISTENT_STATE_CAUSALITY_NOT_ESTABLISHED")
    elif not m4["items"]["D_sel_gt_eps_sel"]:
        terminal = ("F", "MFS0_NONSELECTIVE_WRITE_ONLY")
    else:
        terminal = ("UNRESOLVED", "gate failure outside §29 mapping — see "
                                  "gates/integrity")

    out = {
        "round": "MFS0-E0",
        "gates": {k: "PASS" if v else "FAIL" for k, v in gates.items()},
        "hold6": f"{ho['passed']}/{ho['total']}",
        "negative_controls": {k: "PASS" if v["pass"] else "FAIL"
                              for k, v in nc.items()},
        "integrity": integrity,
        "integrity_detail": {"seal_check": sc, "seal_commit": SEAL_COMMIT,
                             "production_changed": prod_changed,
                             "budget_used": used, "budget_caps": led["caps"],
                             "attempted_runs": attempted,
                             "round_base_commit": ROUND_BASE_COMMIT},
        "terminal_state": {"code": terminal[0], "name": terminal[1]},
        "allowed_interpretation": (
            "The system has, for the first time, a minimal causal memory "
            "substrate candidate made of a historical eligibility, an "
            "independent later physical modulation and a persistent "
            "structural state." if terminal[0] == "A" else None),
        "forbidden_claims": ["memory solved", "learning solved",
                             "consolidation solved", "Posterior qualified",
                             "Xin qualified", "cognition",
                             "semantic learning",
                             "fully emergent analog multiplication"],
        "registered_limitations": {
            "TIER2_LIMITATION": M.TIER2_LIMITATION,
            "TIMING_CONTROL": td["TIMING_CONTROL"]["LIMITATION"],
            "BLOCK_LIMITATION": ci["stepH"]["BLOCK_LIMITATION"],
            "SELECTIVITY_BY_CONSTRUCTION": (
                "NC1/NC2/NC4/NC5 and the TC arm are exact zeros because a "
                "sub-threshold factor hard-zeroes I_write (DEG-019). "
                "S_sel=%.3e is inflated by the EPSILON_Z denominator floor; "
                "the selectivity claim rests on D_sel, not on the ratio "
                "(§17)." % m4["S_sel"]),
            "I_Z_IS_CONSISTENCY_ONLY": "I_z observed equals predicted by "
                                       "construction of the Tier-2 gate "
                                       "(§16); it is not independent "
                                       "evidence.",
            "W_PERSISTENCE_IDENTITY": "marginal continuous persistence / "
                                      "integrator-like, NOT a bistable "
                                      "latch",
            "MEMRISTOR_UPDATE_MISSING_DT": "research-side workaround "
                                           "current=I_write*dt used for all "
                                           "arms; DEG to be registered at "
                                           "round close",
        },
        "posterior0_relation": "POSTERIOR0_TERMINAL_C_FROZEN unchanged (R-3); "
                               "this result must not be read as 'Posterior-0 "
                               "actually passed'.",
        "HARD_STOP": True,
    }

    # 历史汇总与生效状态分离（复核意见 §3.1-1/2）：本程序只写历史对象
    M.write_json(HISTORICAL_FILE, out)
    status = write_effective_status(out)
    print(f"  effective-status file: {status}")

    print("MFS0-E0 final qualification")
    for k, v in out["gates"].items():
        print(f"  {v:<4} {k}")
    print(f"  hold6 = {out['hold6']}")
    for k, v in integrity.items():
        print(f"    {'OK ' if v else 'FAIL'} {k}")
    if sc["raw_byte_mismatch"] or prod_changed:
        print(f"    raw-byte mismatch={len(sc['raw_byte_mismatch'])} "
              f"(EOL-only={len(sc['eol_only'])}, "
              f"content changed={sc['content_changed']})  "
              f"production_changed={prod_changed}")
    print(f"  budget used = {used}")
    print(f"  attempted-only runs = {len(attempted)}")
    print(f"\n  TERMINAL = {terminal[0]} — {terminal[1]}")
    return 0 if terminal[0] == "A" else 1


if __name__ == '__main__':
    raise SystemExit(main())
