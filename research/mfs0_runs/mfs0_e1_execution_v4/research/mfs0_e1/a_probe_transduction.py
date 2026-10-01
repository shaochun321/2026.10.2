"""Stage A probe: template provenance + entry-pulse latency/count + per-step cost.

For each template alone (translated to start at t0 = 0.5 s) record every collector
spike and every entry pulse b↑, at dt, dt/2, dt/4. Also: bit-exact check that the
generator ramp equals production build_phase_drive at dt = 0.001.
"""
import time
from e1_common import (load_templates, ramp, Transducer, DT, log_run, SOURCE_COMMIT)
from tss.adapters.relation_replay_adapter import build_phase_drive
from d21_common import load_relation_ports

T = load_templates()
for k, v in T.items():
    print(f"template {k}: {v['key']} t_up={v['t_up']} t_rearm={v['t_rearm']} dur={v['dur_s']:.3f}s "
          f"sha16={v['sha16']} occ={v['occurrence_id']}")

# bit-exact ramp vs production build_phase_drive (untranslated, dt=0.001)
port = load_relation_ports()['cal_C3_m']
prod = build_phase_drive(port.t_rearm + 10, DT, [port])
mine = [ramp(k, port.t_up, port.t_rearm - port.t_up) for k in range(port.t_rearm + 10)]
diff = max(abs(a.value - b) for a, b in zip(prod, mine))
print(f"ramp vs build_phase_drive (step-index form): max|diff| = {diff:.1e}")

t_start = time.time()
for key in ('W', 'L'):
    dur = T[key]['dur_s']
    for div in (1, 2, 4):
        dt = DT / div
        tr = Transducer(f"probe_{key}_{div}")
        t0 = 0.5
        n = int(round((t0 + dur + 3.0) / dt))
        spikes, entries = [], []
        tic = time.time()
        for i in range(n):
            t = i * dt
            b, s = tr.step(ramp(t, t0, dur), dt)
            if s > 0.5:
                spikes.append(round(t - t0, 6))
            if b > 0.5:
                entries.append(round(t - t0, 6))
        us = (time.time() - tic) / n * 1e6
        print(f"  {key} dt={dt:.5f}: spikes {len(spikes)} (first {spikes[:3]} last {spikes[-1:] if spikes else None}) "
              f"entries {entries}  cost {us:.1f} us/step")
log_run(stage='A', run_id='a_probe_transduction', wall_s=time.time() - t_start,
        source_commit=SOURCE_COMMIT, note='template latency / dt probe')
