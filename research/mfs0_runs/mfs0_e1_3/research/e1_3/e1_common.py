"""MFS0-E1 v4 — shared layer: paths, template sources, input transduction, run ledger.

TYPE:INFRA (research-layer assembly; production primitives READ_ONLY).

Input route (plan v4 §3): CAUSAL_REPLAY_REFERENCE + TEMPLATE_TRANSLATION.
Two templates, both recorded D2-1 products at commit 4d4e424:
  W     = RelationOccurrencePortV1 'cal_C3_m'   (relation_occurrence_manifest.csv)
  LATER = site23 PortWindow 's23_ov'            (site23_occurrence_manifest.csv)
A template contributes only its typed window (t_up, t_rearm); the drive is the
production build_phase_drive ramp ϑ = (t − t_up)/(t_rearm − t_up) on that window
(no amplitude DOF). Translation = shifting the window start in physical time;
the ramp duration is kept. No stretching, scaling or clipping.

The learner only ever receives ϑ_W(t), ϑ_L(t) through RelationEventAdapter →
PhysicalEntryGate (both production tss objects, default parameters). Probabilities,
outcome labels, phases, template names and future times stay in the generator.
"""
import os
import sys
import json
import time
import math
import hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', 'src'))
for p in (ROOT, os.path.join(ROOT, 'research', 'd2_relation_v0'),
          os.path.join(ROOT, 'research', 'd2_recursive_v1')):
    if p not in sys.path:
        sys.path.insert(0, p)
sys.dont_write_bytecode = True

RESULTS = os.path.join(HERE, 'results')
RUNS = os.path.join(HERE, 'runs.jsonl')
DT = 0.001                      # canonical GENERATOR_DT (G0-R0 ruling: physical seconds)
SOURCE_COMMIT = "4d4e424decefb1ee5698f7dbca4e62594b41d8e4"

W_TEMPLATE = ("relation_occurrence_manifest.csv", "cal_C3_m")
L_TEMPLATE = ("site23_occurrence_manifest.csv", "s23_ov")


def sha16(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def load_templates():
    """Return {'W': (dur_s, meta), 'L': (dur_s, meta)} from the recorded manifests."""
    from d21_common import load_relation_ports, load_site23_windows, DATA
    pw = load_relation_ports()[W_TEMPLATE[1]]
    lw = load_site23_windows()[L_TEMPLATE[1]][0]
    out = {
        'W': dict(src=os.path.join(DATA, W_TEMPLATE[0]), key=W_TEMPLATE[1],
                  t_up=pw.t_up, t_rearm=pw.t_rearm, dur_s=(pw.t_rearm - pw.t_up) * DT,
                  occurrence_id=pw.occurrence_id, layer="RelationOccurrencePortV1"),
        'L': dict(src=os.path.join(DATA, L_TEMPLATE[0]), key=L_TEMPLATE[1],
                  t_up=lw.t_up, t_rearm=lw.t_rearm, dur_s=(lw.t_rearm - lw.t_up) * DT,
                  occurrence_id=lw.occurrence_id, layer="site23 PortWindow"),
    }
    for v in out.values():
        v['sha16'] = sha16(v['src'])
    return out


def ramp(t, t0, dur):
    """build_phase_drive value on a translated window [t0, t0+dur)."""
    return (t - t0) / dur if t0 <= t < t0 + dur else 0.0


class Transducer:
    """Template drive → RelationEventAdapter → PhysicalEntryGate → entry pulse b↑.

    Production objects, default parameters; one instance per input path, created
    once per trial and stepped every tick (continuous-run boundary, plan §3).
    """

    def __init__(self, label):
        from nexus_v1.components.structural_address import AddressRegistry
        from tss.relations.relation_event_adapter import RelationEventAdapter
        from tss.relations.entry_gate import PhysicalEntryGate
        from d21_common import relation2_address
        reg = AddressRegistry()
        _r2, _r, addr_c = relation2_address()
        self.adapter = RelationEventAdapter(reg, addr_c, addr_c, label)
        self.gate = PhysicalEntryGate(generator_address=self.adapter.generator_address)

    def step(self, theta, dt):
        spike = self.adapter.step(theta, dt)
        return self.gate.step(spike, dt), spike


def log_run(**kw):
    kw.setdefault('t_end', time.time())
    with open(RUNS, 'a', encoding='utf-8') as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def budget_used_s():
    if not os.path.exists(RUNS):
        return 0.0
    tot = 0.0
    with open(RUNS, encoding='utf-8') as f:
        for line in f:
            tot += json.loads(line).get('wall_s', 0.0)
    return tot
