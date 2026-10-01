"""MFS0-E3 independent continuous reference (evaluation / offline selection only).

Extends the E2 reference (research/e2/reference_solver.py, ż_c = Σ_r λ_r (q_r − z_c),
rectangular settle kernel λ0 = −ln(0.9)/S on [s+H, s+H+S)) to arbitrary carrier ids:
every admitted experience writes its marginal carrier ('m', i) and, when history i is
split, also the leaf carrier ('c', i, k) latched at entry. Exact piecewise integration.
"""
import bisect
import math

H = 1.5 * math.log(2.0)
S = 1.5 * math.log(1.0 / 0.3)
LAM0 = -math.log(1 - 0.10) / S


def q_of(k_s, l_ticks, dt, h=H):
    j = bisect.bisect_left(l_ticks, k_s)
    return 1 if j < len(l_ticks) and (l_ticks[j] - k_s) * dt < h - 1e-12 else 0


def censored(k_s, n_ticks, dt, h=H):
    """Outcome window [s, s+H) not complete inside the run."""
    return k_s * dt + h > n_ticks * dt + 1e-12


def carriers_at(experiences, l_ticks, queries, dt, z0=0.5):
    """experiences: list of (tick, [carrier ids]); queries: {carrier: sorted ticks}.
    Returns {carrier: {tick: z(state before tick)}}."""
    per = {}
    for k, cs in experiences:
        q = q_of(k, l_ticks, dt)
        a = k * dt + H
        for c in cs:
            per.setdefault(c, []).append((a, a + S, q))
    out = {}
    for c, qt in queries.items():
        ivs = per.get(c, [])
        events = sorted([(a, 1, q) for a, b, q in ivs] + [(b, -1, q) for a, b, q in ivs])
        z, t_cur, nB, nQ, ei, res = z0, 0.0, 0, 0, 0, {}
        for k in qt:
            tq = k * dt
            while ei < len(events) and events[ei][0] <= tq:
                nxt, d, q = events[ei]
                if nB > 0:
                    B = nB * LAM0
                    z = nQ / nB + (z - nQ / nB) * math.exp(-B * (nxt - t_cur))
                t_cur = nxt
                nB += d
                nQ += d * q
                ei += 1
            if nB > 0:
                B = nB * LAM0
                z = nQ / nB + (z - nQ / nB) * math.exp(-B * (tq - t_cur))
            t_cur = tq
            res[k] = z
        out[c] = res
    return out
