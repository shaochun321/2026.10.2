"""Generator + continuous-run harness (the only place that knows y, p, phases).

Cycle (period PERIOD, physical seconds), generator side:
  t = W_OFF          : W_i template window starts (history i of this cycle)
  t = W_OFF + READ   : evaluator samples the device's actual output (before any later input)
  t = W_OFF + d_L    : if y = 1, LATER template window starts; d_L ~ U[D_MIN, D_MAX]
The device receives only the per-tick ramp values through its Transducers.
"""
import random
from e1_common import Transducer, ramp, load_templates, DT
from device import PredictiveMemoryDevice, Params

PERIOD = 4.0
W_OFF = 0.10
READ = 0.05
D_MIN, D_MAX = 0.10, 0.80

_T = load_templates()
DUR_W, DUR_L = _T['W']['dur_s'], _T['L']['dur_s']


class Rig:
    """Device + its input transducers; created once per independent trial."""

    def __init__(self, n_hist=1, w0=0.5, params=None, label='rig'):
        self.dev = PredictiveMemoryDevice(n_hist=n_hist, w0=w0, p=params)
        self.tw = [Transducer(f"{label}_W{i}") for i in range(n_hist)]
        self.tl = Transducer(f"{label}_L")
        self.t = 0.0          # continuous physical time across cycles
        self.n = 0            # tick counter (for the drive only)


def run_cycles(rig, schedule, dt=DT, trace=None):
    """schedule: list of dict(hist=i, y=0/1, dL=float). Returns per-cycle records."""
    out = []
    n_cyc = int(round(PERIOD / dt))
    k_read = int(round((W_OFF + READ) / dt))
    for c in schedule:
        t_c = rig.n * dt
        pred = None
        z_before = [rig.dev.z(i) for i in range(len(rig.dev.h))]
        n_bw = [0] * len(rig.tw)
        n_bl = 0
        w_on = c.get('w_on', True)
        for k in range(n_cyc):
            t = (rig.n + k) * dt - t_c           # time within this cycle
            b_w = []
            for i, tr in enumerate(rig.tw):
                th = ramp(t, W_OFF, DUR_W) if (i == c['hist'] and w_on) else 0.0
                b = tr.step(th, dt)[0]
                n_bw[i] += b > 0.5
                b_w.append(b)
            th_l = ramp(t, W_OFF + c['dL'], DUR_L) if c['y'] else 0.0
            b_l = rig.tl.step(th_l, dt)[0]
            n_bl += b_l > 0.5
            rig.dev.step(b_w, b_l, dt)
            if k == k_read:
                pred = rig.dev.predict()
            if trace is not None:
                trace.append((t_c + t, rig.dev.h[c['hist']].T.voltage, rig.dev.O.voltage,
                              rig.dev.z(c['hist'])))
        rig.n += n_cyc
        out.append(dict(hist=c['hist'], y=c['y'], dL=c['dL'], pred=pred,
                        z_before=z_before, z_after=[rig.dev.z(i) for i in range(len(rig.dev.h))],
                        O_end=rig.dev.O.voltage, n_bw=n_bw, n_bl=n_bl,
                        T_end=[h.T.voltage for h in rig.dev.h]))
    return out


def bernoulli_schedule(ps, seed, hist=None, n_hist=1):
    """ps: list of per-cycle p(y=1) (generator only). hist: per-cycle history index."""
    rng = random.Random(seed)
    sch = []
    for j, p in enumerate(ps):
        sch.append(dict(hist=hist[j] if hist else 0, y=1 if rng.random() < p else 0,
                        dL=rng.uniform(D_MIN, D_MAX)))
    return sch
