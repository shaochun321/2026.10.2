"""MFS0-E2 scenario generation (source side only; the learner never sees any of this).

Main task, 900 s, 3 histories, 1 LATER channel, 4 segments:
  S1 0–240 s   p = (0.8, 0.2, 0.8)
  S2 240–480 s p = (0.2, 0.8, 0.8)     (H1/H2 relation exchanged)
  S3 480–600 s no new W / L (silence; pending experiences settle first)
  S4 600–900 s p = (0.8, 0.2, 0.8)     (previous relation restored); new events stop at END_NEW
Generation: per history an irregular renewal process of W template starts
(gap = GAP_MIN + Exp(mean GAP_MEAN − GAP_MIN)); for each W, with prob p an L template
is placed at W + U[L_OFF_MIN, L_OFF_MAX] unless an L start already lies there or the
channel spacing L_SPACING would be violated (then: no new L; logged as a conflict).
One global L stream is formed first; Y is computed later by the evaluator from the
actually gate-accepted L entries, never from these draws.
"""
import random

SEG = [(0.0, 240.0, (0.8, 0.2, 0.8)), (240.0, 480.0, (0.2, 0.8, 0.8)),
       (480.0, 600.0, None), (600.0, 900.0, (0.8, 0.2, 0.8))]
T_TOTAL = 900.0
END_NEW = 894.0          # last W start ≤ END_NEW − W_dur; leaves > 4 s drain
GAP_MIN = 2.60           # same-channel: W template 1.354 s + entry-gate recovery 1.204 s
GAP_MEAN = 5.0
L_OFF_MIN, L_OFF_MAX = 0.05, 0.95   # template start offset after W start (entry ≈ +2 ms)
L_SPACING = 1.90         # same-channel LATER: template 0.639 s + recovery 1.204 s
W_DUR = 1.354


def _segment(t):
    for a, b, p in SEG:
        if a <= t < b:
            return p, (a, b)
    return None, None


def build_main(seed_outcome, seed_time, n_hist=3):
    rt = random.Random(seed_time)
    ry = random.Random(seed_outcome)
    w = [[] for _ in range(n_hist)]
    for i in range(n_hist):
        t = rt.uniform(0.5, 3.0)
        while True:
            p, ab = _segment(t)
            if p is None:
                # skip silence: jump to the next active segment start
                nxt = [s[0] for s in SEG if s[2] is not None and s[0] > t]
                if not nxt:
                    break
                t = nxt[0] + rt.uniform(0.5, 3.0)
                continue
            a, b = ab
            if t + W_DUR + 1.5 > b or t > END_NEW - W_DUR:
                nxt = [s[0] for s in SEG if s[2] is not None and s[0] >= b]
                if not nxt:
                    break
                t = nxt[0] + rt.uniform(0.5, 3.0)
                continue
            w[i].append(t)
            t += GAP_MIN + rt.expovariate(1.0 / (GAP_MEAN - GAP_MIN))
    # L stream: process W in time order across histories
    allw = sorted((t, i) for i in range(n_hist) for t in w[i])
    L = []
    conflicts = 0
    draws = []
    for t, i in allw:
        p, _ = _segment(t)
        want = ry.random() < p[i]
        off = rt.uniform(L_OFF_MIN, L_OFF_MAX)
        draws.append((t, i, want))
        if not want:
            continue
        if any(t <= x < t + 1.0 for x in L):
            continue                      # already an L in this window
        placed = _place(L, t, off)
        if not placed:
            conflicts += 1
    return dict(w=w, l=L, conflicts=conflicts, draws=draws)


def _place(L, t, off):
    """Place an L start in [t+L_OFF_MIN, t+L_OFF_MAX] respecting channel spacing.
    First the drawn offset; if it conflicts, the earliest feasible offset on a 10 ms grid.
    Dev revision G1 (generator only, before freeze): reduces drops that compressed Y rates."""
    cands = [t + off] + [t + L_OFF_MIN + 0.01 * k for k in range(int((L_OFF_MAX - L_OFF_MIN) / 0.01) + 1)]
    for c in cands:
        if all(abs(c - x) >= L_SPACING for x in L):
            L.append(c)
            L.sort()
            return True
    return False


def build_stress(seed_outcome, seed_time, n_hist=3, T=3600.0):
    """Stress stream, 3600 s: normal / core-level overload bursts / recovery / long silence.

    Returns replay-layer schedule (normal parts) + core-injection pulses (overload).
      0–1200 s    normal (p = 0.8, 0.2, 0.8)
      1200–1260 s overload: core-level W pulses every 0.4 s per history (entry-contract layer)
      1260–2400 s normal recovery (p = 0.2, 0.8, 0.8)
      2400–2560 s silence (≥ 130 s: drain + 120 s hold)
      2560–3590 s normal (p = 0.8, 0.2, 0.8); new events stop at 3590 s
    """
    rt = random.Random(seed_time)
    ry = random.Random(seed_outcome)
    segs = [(0.0, 1200.0, (0.8, 0.2, 0.8)), (1260.0, 2400.0, (0.2, 0.8, 0.8)),
            (2560.0, 3590.0, (0.8, 0.2, 0.8))]
    w = [[] for _ in range(n_hist)]
    for i in range(n_hist):
        for a, b, p in segs:
            t = a + rt.uniform(0.5, 3.0)
            while t + W_DUR + 1.5 <= b:
                w[i].append(t)
                t += GAP_MIN + rt.expovariate(1.0 / (GAP_MEAN - GAP_MIN))
    allw = sorted((t, i) for i in range(n_hist) for t in w[i])
    L, conflicts = [], 0
    for t, i in allw:
        p = next(s[2] for s in segs if s[0] <= t < s[1])
        want = ry.random() < p[i]
        off = rt.uniform(L_OFF_MIN, L_OFF_MAX)
        if not want or any(t <= x < t + 1.0 for x in L):
            continue
        if not _place(L, t, off):
            conflicts += 1
    inj = [[round((1200.0 + 0.4 * k + 0.13 * i) / 0.001) for k in range(150)] for i in range(n_hist)]
    inj_l = [round((1200.2 + 0.8 * k) / 0.001) for k in range(75)]
    return dict(w=w, l=L, conflicts=conflicts, inj_w=inj, inj_l=inj_l,
                silence=(2400.0, 2560.0), overload=(1200.0, 1260.0), segs=segs)
