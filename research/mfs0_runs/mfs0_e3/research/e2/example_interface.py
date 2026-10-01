"""Minimal usage of the E2 interface: core + replay bridge + prediction port + consumer.

python -B example_interface.py
"""
import e1_common  # noqa: F401
from memory_core import MemoryCore
from current_input_bridge import ReplayBridge
from prediction_port import PredictionPort, ThresholdConsumer
from stream_runner import run_stream

core = MemoryCore(n_hist=3, n_slot=2)
bridge = ReplayBridge(w_starts=[[1.0, 6.0, 11.0], [3.0, 8.0], [4.5]], l_starts=[1.4, 6.3, 11.2])
port = PredictionPort()
consumer = ThresholdConsumer()
res = run_stream(core, bridge, 16000, port=port, consumer=consumer)
for r in port.records:
    print(r)
print("consumer hints:", consumer.hints)
print("carriers z:", [round(core.z(c), 4) for c in range(3)])
