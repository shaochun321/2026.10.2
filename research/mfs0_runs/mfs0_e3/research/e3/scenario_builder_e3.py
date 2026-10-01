"""MFS0-E3 task sources (source side only; no core ever sees any of this).

A : the frozen E2 G1 generator (scenario_builder.build_main) — unchanged environment.
X : joint-relation task. W1 (history 0) is the trigger; W2/W3 (histories 1/2) encode two
    uniform bits A, B before each trigger: A=1 → W2 template ≈0.70 s before W1, B=1 → W3
    ≈0.35 s before W1. Trigger gap = 5 s + Exp(mean 2 s). L template at W1 + U[0.1, 0.7] s
    with probability 0.85 if A⊕B else 0.15 (0–240 s), swapped 240–480 s, silence 480–600 s,
    restored 600–900 s. Source bits and draws are kept for evaluation only.
L : live boundary schedule for sites W = (28, 31, 21), L = 23 — the E2 live stimulus
    (dT = 0.05 for 1 s; W every U[5, 8] s per site; L after a W with prob p_i at
    +U[0.3, 0.6] s, L spacing ≥ 5 s), extended to three W sites and to the A timeline
    (p = (0.8, 0.2, 0.8) / (0.2, 0.8, 0.8) / silence / (0.8, 0.2, 0.8)).
    LiveStimulus returns only the current dT per site.
S : the frozen E2 stress layout (scenario_builder.build_stress).
"""
import random

from scenario_builder import build_main, build_stress, W_DUR, L_SPACING  # noqa: F401

X_SEG = [(0.0, 240.0, 0.85, 0.15), (240.0, 480.0, 0.15, 0.85), (600.0, 900.0, 0.85, 0.15)]
X_END_NEW = 894.0
A_LEAD, B_LEAD = 0.70, 0.35


def build_A(seed_outcome, seed_time):
    return build_main(seed_outcome, seed_time)


def build_X(seed_outcome, seed_time):
    rt, ry = random.Random(seed_time), random.Random(seed_outcome)
    w = [[], [], []]
    L, trig = [], []
    for a, b, p_x1, p_x0 in X_SEG:
        t = a + A_LEAD + rt.uniform(0.5, 3.0)
        while t + W_DUR + 1.5 <= b and t <= X_END_NEW - W_DUR:
            A, B = rt.random() < 0.5, rt.random() < 0.5
            w[0].append(t)
            if A:
                w[1].append(t - A_LEAD)
            if B:
                w[2].append(t - B_LEAD)
            x = A != B
            want = ry.random() < (p_x1 if x else p_x0)
            off = rt.uniform(0.1, 0.7)
            if want:
                L.append(t + off)
            trig.append(dict(t=t, A=A, B=B, xor=x, want=want))
            t += 5.0 + rt.expovariate(1.0 / 2.0)
    for x in w:
        x.sort()
    return dict(w=w, l=sorted(L), triggers=trig, conflicts=0)


L_SEG = [(0.0, 240.0, (0.8, 0.2, 0.8)), (240.0, 480.0, (0.2, 0.8, 0.8)), (600.0, 900.0, (0.8, 0.2, 0.8))]
L_SITES_W = (28, 31, 21)
L_SITE_L = 23
L_AMP, L_PULSE = 0.05, 1.0


def _seg_p(t):
    for a, b, p in L_SEG:
        if a <= t < b:
            return p
    return None


def build_L(seed_outcome, seed_time, T=900.0, fork_at=None, fork_seed=None, base=None):
    """Live stimulus schedule. With fork_at, pulses starting before fork_at are copied from
    `base` and the suffix is regenerated from fork_seed (independent future)."""
    if fork_at is not None:
        rt, ry = random.Random(fork_seed), random.Random(fork_seed + 1)
    else:
        rt, ry = random.Random(seed_time), random.Random(seed_outcome)
    t_lo = fork_at or 0.0
    pul = {s: [] for s in L_SITES_W + (L_SITE_L,)}
    if base is not None:
        for s in pul:
            pul[s] = [iv for iv in base[s] if iv[0] < t_lo]
    for idx, site in enumerate(L_SITES_W):
        for a, b, _ in L_SEG:
            if b <= t_lo:
                continue
            t = max(a, t_lo) + rt.uniform(1.0, 4.0) + 1.5 * idx
            while t + L_PULSE + 3.0 <= b and t < T - 10.0:
                pul[site].append((t, t + L_PULSE))
                t += rt.uniform(5.0, 8.0)
    ws = sorted((a, i) for i, site in enumerate(L_SITES_W) for a, _ in pul[site] if a >= t_lo)
    conflicts = 0
    for a, i in ws:
        p = _seg_p(a)
        if ry.random() < p[i]:
            d = a + ry.uniform(0.3, 0.6)
            if all(abs(d - x) >= 5.0 for x, _ in pul[L_SITE_L]):
                pul[L_SITE_L].append((d, d + L_PULSE))
            else:
                conflicts += 1
    for s in pul:
        pul[s].sort()
    return dict(pulses=pul, conflicts=conflicts)


class LiveStimulus:
    """Causal stimulus callback: returns the CURRENT dT per site only (picklable)."""

    def __init__(self, pulses):
        self.p = {s: list(v) for s, v in pulses.items()}
        self.k = {s: 0 for s in pulses}

    def __call__(self, t):
        out = {}
        for s, iv in self.p.items():
            k = self.k[s]
            while k < len(iv) and t >= iv[k][1]:
                k += 1
            self.k[s] = k
            out[s] = L_AMP if (k < len(iv) and iv[k][0] <= t) else 0.0
        return out

    def replace_future(self, pulses, t_from):
        """Prefix fork: keep everything already started before t_from, swap the future."""
        for s in self.p:
            keep = [iv for iv in self.p[s] if iv[0] < t_from]
            self.p[s] = keep + [iv for iv in pulses[s] if iv[0] >= t_from]
            self.k[s] = 0


def build_S(seed_outcome, seed_time):
    return build_stress(seed_outcome, seed_time)
