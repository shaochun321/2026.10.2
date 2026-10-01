"""MFS0-E3 relation specification: shared event traces, the finite candidate family C1–C7,
and the independent time reference for conditions (evaluation / offline selection only).

TYPE:INFRA (specification + evaluator reference; never inside the runtime core loop).

Traces (plan §5.1): one RC trace per input path a ∈ {W0, W1, W2, L}; ideal reading
  x_a ← V_x on an accepted pulse, ẋ_a = −x_a/τ_x, τ_x = 1 s, V_x = 2 V,
  X_a^(d) = 1[x_a > V_x·e^(−d/τ_x)], d ∈ {H, 2H}; equality → 0; start-up → 0.
Time reference (independent of the node): an event accepted at tick k_a is "within d"
of an entry at tick k iff 0 < (k − k_a)·dt ≤ d. The node trace is set in step-order
item 6 of tick k_a and therefore first visible at tick k_a + 1; its comparator reads
(k − k_a − 1)·dt < d. Expected boundary offset node − reference = +1 dt (registered,
criterion §11.7 allows ≤ 2 dt); measured, never tuned away.

Candidates for history i, with j, l the other two histories in fixed index order:
  U = X_Wj^(H), V = X_Wl^(H), Q = X_L^(H), Q2 = X_L^(2H).
"""
import bisect
import math

TAU_X = 1.0
V_X = 2.0
H = 1.5 * math.log(2.0)          # = τ_T·ln(V_D/θ_hi) of the frozen E2 core
TRACES = ('W0', 'W1', 'W2', 'L')

# name: (inputs needed, boolean function of dict(U,V,Q,Q2), node cost key)
CANDIDATES = {
    'C1': (('Q',), lambda s: s['Q']),
    'C2': (('Q2',), lambda s: s['Q2']),
    'C3': (('U',), lambda s: s['U']),
    'C4': (('V',), lambda s: s['V']),
    'C5': (('U', 'V'), lambda s: s['U'] and s['V']),
    'C6': (('U', 'V'), lambda s: s['U'] != s['V']),
    'C7': (('Q', 'U', 'V'), lambda s: s['Q'] and (s['U'] or s['V'])),
}
# node implementation cost (relation_operator.py builds exactly these; see resource_layout)
#   comparators: threshold comparators reading traces (shared across histories when the
#   same trace/threshold pair is reused — counted once globally in the layout), logic:
#   pass-transistor switch networks + pull-down + output comparator.
LOGIC_COST = {
    'C1': dict(threshold_inputs=1, logic_gates=0, switches=0, inverters=0),
    'C2': dict(threshold_inputs=1, logic_gates=0, switches=0, inverters=0),
    'C3': dict(threshold_inputs=1, logic_gates=0, switches=0, inverters=0),
    'C4': dict(threshold_inputs=1, logic_gates=0, switches=0, inverters=0),
    'C5': dict(threshold_inputs=2, logic_gates=1, switches=2, inverters=0),
    'C6': dict(threshold_inputs=2, logic_gates=1, switches=4, inverters=2),
    'C7': dict(threshold_inputs=3, logic_gates=2, switches=4, inverters=0),
}


def extra_state_key(name):
    c = LOGIC_COST[name]
    return (c['threshold_inputs'] + c['logic_gates'] + c['inverters'], int(name[1:]))


def others(i):
    j, l = [h for h in range(3) if h != i]
    return j, l


def thr(d):
    return V_X * math.exp(-d / TAU_X)


def within(ticks, k, d, dt):
    """Time reference: ∃ accepted event k_a < k with (k − k_a)·dt ≤ d (ticks sorted)."""
    j = bisect.bisect_left(ticks, k) - 1
    return j >= 0 and (k - ticks[j]) * dt <= d + 1e-12


def signals_ref(i, k, w_ticks, l_ticks, dt):
    j, l = others(i)
    return dict(U=within(w_ticks[j], k, H, dt), V=within(w_ticks[l], k, H, dt),
                Q=within(l_ticks, k, H, dt), Q2=within(l_ticks, k, 2 * H, dt))


def cond_ref(name, i, k, w_ticks, l_ticks, dt):
    return 1 if CANDIDATES[name][1](signals_ref(i, k, w_ticks, l_ticks, dt)) else 0
