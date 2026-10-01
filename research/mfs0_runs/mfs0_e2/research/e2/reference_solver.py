"""MFS0-E2 continuous reference (THEORY.md §6) — research/evaluation only, never in the loop.

ż_c = Σ_r λ_r(t) (q_r − z_c) over all admitted experiences whose history maps to carrier c.
Each admitted experience at entry time s: q = 1{accepted L tick in [s, s+H)}; its settle
kernel is the ideal rectangle λ0 = −ln(0.9)/S on [s+H, s+H+S). Integrated exactly
piecewise (B, Q constant between breakpoints).
"""
import bisect
import math


def ideal_constants(core, dt):
    H = core.H_nominal
    S = core.T_settle
    lam0 = -math.log(1 - core.P.alpha0) / S
    return H, S, lam0


def q_of(k_s, l_ticks, H, dt):
    j = bisect.bisect_left(l_ticks, k_s)
    return 1 if j < len(l_ticks) and (l_ticks[j] - k_s) * dt < H - 1e-12 else 0


def reference_z(core, admitted, l_ticks, query_ticks, dt, z0):
    """admitted: list of (tick, hist). Returns {carrier: {tick: z_ref(state before tick)}}."""
    H, S, lam0 = ideal_constants(core, dt)
    per_car = {}
    for k, i in admitted:
        c = core.carrier_of[i]
        per_car.setdefault(c, []).append((k * dt + H, k * dt + H + S, q_of(k, l_ticks, H, dt)))
    out = {}
    for c in range(len(core.mem)):
        ivs = per_car.get(c, [])
        bps = sorted({0.0} | {a for a, b, q in ivs} | {b for a, b, q in ivs})
        qt = sorted(query_ticks)
        res = {}
        z = z0[c] if isinstance(z0, (list, tuple)) else z0
        t_cur = 0.0
        # active interval bookkeeping via sweep
        events = sorted([(a, 1, q) for a, b, q in ivs] + [(b, -1, q) for a, b, q in ivs])
        ei = 0
        nB = 0
        nQ = 0
        qi = 0
        while qi < len(qt):
            tq = qt[qi] * dt
            nxt = events[ei][0] if ei < len(events) else float('inf')
            if nxt <= tq:
                if nB > 0:
                    B = nB * lam0
                    Q = nQ / nB
                    z = Q + (z - Q) * math.exp(-B * (nxt - t_cur))
                t_cur = nxt
                _, d, q = events[ei]
                nB += d
                nQ += d * q
                ei += 1
            else:
                if nB > 0:
                    B = nB * lam0
                    Q = nQ / nB
                    z = Q + (z - Q) * math.exp(-B * (tq - t_cur))
                t_cur = tq
                res[qt[qi]] = z
                qi += 1
        out[c] = res
    return out
