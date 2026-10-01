"""MFS0-E3 shared layer: paths, E2 baseline import, run ledger, statistics helpers.

TYPE:INFRA (research layer; production primitives and the frozen E2 core are READ_ONLY).

The E2 package (research/e2, copied from the restored independent E2 copy and checked
against results/freeze_E2.json) is imported unmodified: group B = E2 MemoryCore.
"""
import hashlib
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
E2_DIR = os.path.abspath(os.path.join(HERE, '..', 'e2'))
if E2_DIR not in sys.path:
    sys.path.insert(0, E2_DIR)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import e1_common  # noqa: E402,F401  (src + d21 paths for production objects)

sys.dont_write_bytecode = True
RES = os.environ.get('E3_RES', os.path.join(HERE, 'results'))      # dev pipeline smoke uses its own root
RUNS = os.path.join(HERE, 'runs.jsonl')                           # one ledger for every run, dev or formal
DT = 0.001
E2_FREEZE = os.path.join(E2_DIR, 'results', 'freeze_E2.json')


def sha16(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def check_e2_freeze():
    """Every file registered in freeze_E2.json must hash to its frozen value."""
    frz = json.load(open(E2_FREEZE, encoding='utf-8'))
    return {n: (sha16(os.path.join(E2_DIR, n)), h, sha16(os.path.join(E2_DIR, n)) == h) for n, h in frz.items()}


def log_run(**kw):
    kw.setdefault('t_end', time.time())
    os.makedirs(os.path.dirname(RUNS), exist_ok=True)
    with open(RUNS, 'a', encoding='utf-8') as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def budget_used_s():
    if not os.path.exists(RUNS):
        return 0.0
    with open(RUNS, encoding='utf-8') as f:
        return sum(json.loads(x).get('wall_s', 0.0) for x in f if x.strip())


# two-sided 95 % t quantiles, df = n − 1
_T975 = {1: 12.706205, 2: 4.302653, 3: 3.182446, 4: 2.776445, 5: 2.570582, 6: 2.446912, 7: 2.364624,
         8: 2.306004, 9: 2.262157, 10: 2.228139, 11: 2.200985, 12: 2.178813, 13: 2.160369, 14: 2.144787,
         15: 2.131450, 16: 2.119905, 17: 2.109816, 18: 2.100922, 19: 2.093024, 20: 2.085963,
         21: 2.079614, 22: 2.073873, 23: 2.068658, 24: 2.063899, 25: 2.059539}


def t_interval(xs):
    n = len(xs)
    m = sum(xs) / n
    if n < 2:
        return m, float('nan'), float('nan')
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    h = _T975[n - 1] * sd / math.sqrt(n)
    return m, m - h, m + h
