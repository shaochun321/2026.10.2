"""MFS0-E3 minimal call example (core-level injection; a few seconds).

Build the conditional core from the frozen relation table, feed current entry pulses only,
read the immutable records and an independent read-only consumer.
"""
import json
import os

import e3_common as C
from conditional_memory_core import CondMemoryCore
from stream_runner import PulseInjector
from stream_runner_e3 import StreamRun
from prediction_port import ThresholdConsumer

pr = json.load(open(os.path.join(C.HERE, 'prereg_E3.json'), encoding='utf-8'))
splits = {int(k): v for k, v in pr['relation_table']['A_L_S'].items()}       # {0: 'C1', 1: 'C1', 2: 'C1'}
core = CondMemoryCore(splits)
cons = ThresholdConsumer()
# L at 0.5 s; W0 at 1.0 s (C1 = 1: L within H) and at 1.6 s (C1 = 0); L at 2.3 s inside window 2 only
run = StreamRun(PulseInjector([[1000, 1600], [], []], [500, 2300], 3), {'C': core}, 8000, consumers={'C': cons}).run()
for r in run.ports['C'].records:
    print(f"t={r.t:.3f}s path={r.path} p_hat={r.p_hat:.3f} cond={r.condition_id}={r.condition_value} "
          f"read={r.read_path} status={r.status} slot={r.slot}")
print('carriers z:', {str(n): round(1 - m.w, 4) for n, m in zip(core.carrier_names, core.mem)})
print('consumer hints:', cons.hints)
