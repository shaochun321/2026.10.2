"""MFS0-E2 prediction output port + an independent read-only consumer.

Contract: one immutable PredictionRecord per gate-accepted W entry, emitted at the
start of that step from the read currents of the OLD state (before the step's inputs).
status ∈ {ADMITTED, CAPACITY_REJECTED}; slot = −1 when rejected. p_hat is always the
actual read-branch output (never replaced by 0 for 'unknown'). Records cannot be
modified after emission (frozen dataclass; port exposes a tuple view).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class PredictionRecord:
    t: float                # physical time [s] of the entry step
    tick: int
    path: int               # input path identity (which wired W input fired)
    p_hat: float            # actual read current / I_fs, before this step's inputs
    horizon_s: float        # H: observation horizon the prediction refers to
    status: str             # ADMITTED | CAPACITY_REJECTED
    slot: int               # admitted slot index, −1 if rejected
    free_slots_before: int  # capacity state seen by the entry


class PredictionPort:
    def __init__(self):
        self._rec = []
        self._subs = []

    def emit(self, rec):
        self._rec.append(rec)
        for f in self._subs:
            f(rec)

    def subscribe(self, fn):
        self._subs.append(fn)

    @property
    def records(self):
        return tuple(self._rec)


class ThresholdConsumer:
    """Independent consumer: issues a hint when p_hat ≥ 0.65 (fixed in advance).

    Reads only PredictionRecord fields; holds no reference to the core.
    """
    THRESH = 0.65

    def __init__(self):
        self.hints = []

    def __call__(self, rec):
        if rec.p_hat >= self.THRESH:
            self.hints.append((rec.tick, rec.path, rec.p_hat))
