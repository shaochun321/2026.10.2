"""MFS0-E3 prediction records (immutable) + independent read-only consumer.

One record per gate-accepted W entry of every group, emitted from the step-1 snapshot
(old state). Rejections also produce a record (status CAPACITY_REJECTED, slot −1).
E3 adds: relation_id, condition_id, condition_value (the value that routed the
prediction/latch), condition_net (network output; differs from condition_value only in
the random-partition control R), read_path (carrier that produced p_hat), p_hat_marginal.
"""
from dataclasses import dataclass
from typing import Optional

from prediction_port import PredictionPort, ThresholdConsumer  # noqa: F401  (E2 port/consumer reused)


@dataclass(frozen=True)
class PredictionRecordE3:
    t: float
    tick: int
    path: int
    p_hat: float
    horizon_s: float
    status: str
    slot: int
    free_slots_before: int
    relation_id: Optional[str]
    condition_id: Optional[str]
    condition_value: Optional[int]
    condition_net: Optional[int]
    read_path: str
    p_hat_marginal: float
