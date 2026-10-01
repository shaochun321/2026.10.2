"""E3 step 0: restored E2 baseline — freeze hashes + 120 s prefix reproduction of formal stream 0.

Writes results/dev/e2_restore_check.json. Uses the frozen E2 seeds of stream 0 only to
reproduce saved E2 records (baseline verification, not new evidence).
"""
import json
import os
import pickle
import time

import e3_common as C
from memory_core import MemoryCore
from stream_runner import run_stream
from current_input_bridge import ReplayBridge
from scenario_builder import build_main

t0 = time.time()
frz = C.check_e2_freeze()
PR = json.load(open(os.path.join(C.E2_DIR, 'prereg_E2.json'), encoding='utf-8'))
sc = build_main(PR['main']['seed_outcome_base'], PR['main']['seed_time_base'])
K = 120000
res = run_stream(MemoryCore(), ReplayBridge(sc['w'], sc['l'], label='F0'), K)
old = pickle.load(open(os.path.join(C.E2_DIR, 'results', 'formal', 'stream_00.pkl'), 'rb'))['full']
old_rows = [(r[0], r[1], r[2], r[4]) for r in old['rows'] if r[0] < K]
new_rows = [(r.tick, r.path, r.p_hat, r.status) for r in res['port'].records]
same = old_rows == new_rows
l_same = [x for x in old['l_ticks'] if x < K] == res['l_ticks']
out = dict(freeze={k: v[2] for k, v in frz.items()}, freeze_all_ok=all(v[2] for v in frz.values()),
           prefix_ticks=K, n_rows=len(new_rows), rows_bit_identical=same, l_ticks_identical=l_same)
os.makedirs(os.path.join(C.RES, 'dev'), exist_ok=True)
json.dump(out, open(os.path.join(C.RES, 'dev', 'e2_restore_check.json'), 'w'), indent=1)
C.log_run(stage='DEV', run_id='e2_restore_check', wall_s=time.time() - t0, note='E2 baseline restore verification')
print(out)
