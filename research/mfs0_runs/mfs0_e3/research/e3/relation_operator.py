"""MFS0-E3 relation operator: node implementation of the finite condition family.

TYPE:SEMI (research layer; production MOSFET.conduct switches; ideal comparators C1;
static resistive logic node — registered idealisation C2: no propagation delay, no
node capacitance; the logic is evaluated on step-start comparator outputs only).

Literals are comparator outputs at rail levels {0, V_D}: U = X_Wj^(H), V = X_Wl^(H),
Q = X_L^(H), Q2 = X_L^(2H); complements come from a second comparator with swapped
inputs (that is the "inverter", counted). Single-literal candidates use the comparator
output directly. Compound candidates are a pull-up network of MOSFET switches
(gm_sw) from V_D through the rail conductance to a logic node with pull-down G_pd;
an output comparator at V_D/2 restores the level:
  C5 = U·V            : one series path            [U, V]
  C6 = U⊕V            : two series paths in parallel [U, ¬V] ‖ [¬U, V]
  C7 = Q·(U + V)      : two series paths in parallel [Q, U] ‖ [Q, V]
The Python boolean reference (relation_spec.CANDIDATES) is only a functional reference.
"""
from memory_core import series

NETWORK = {
    'C1': [['Q']], 'C2': [['Q2']], 'C3': [['U']], 'C4': [['V']],
    'C5': [['U', 'V']],
    'C6': [['U', '~V'], ['~U', 'V']],
    'C7': [['Q', 'U'], ['Q', 'V']],
}
G_PD = 1e-3


class RelationOperator:
    def __init__(self, core, traces, hist, cand):
        self.core, self.tr, self.i, self.cand = core, traces, hist, cand
        j, l = [h for h in range(3) if h != hist]
        # literal → (trace index, threshold)
        self.lit = {'U': (j, 'H'), 'V': (l, 'H'), 'Q': (3, 'H'), 'Q2': (3, '2H')}
        self.paths = NETWORK[cand]
        self.single = len(self.paths) == 1 and len(self.paths[0]) == 1 and not self.paths[0][0].startswith('~')

    def literals(self):
        """Step-start comparator outputs (bool) for every literal this candidate reads."""
        out = {}
        for p in self.paths:
            for x in p:
                b = x.lstrip('~')
                if b not in out:
                    idx, w = self.lit[b]
                    out[b] = self.tr.above(idx, w)
        return out

    def evaluate(self, lits=None):
        """Returns (condition bit, logic node voltage)."""
        P = self.core.P
        lits = lits if lits is not None else self.literals()
        if self.single:
            on = lits[self.paths[0][0]]
            return (1 if on else 0), (P.V_D if on else 0.0)
        g = self.core.g
        g_up = 0.0
        for p in self.paths:
            gs = []
            for x in p:
                val = (not lits[x[1:]]) if x.startswith('~') else lits[x]
                gs.append(g(P.gm_sw, P.V_D if val else 0.0))
            g_up += series(*gs)
        g_up = series(g_up, 1.0 / P.r_int) if g_up > 0 else 0.0
        v_node = P.V_D * g_up / (g_up + G_PD)
        on = self.core.cmp_on(v_node - (0.5 * P.V_D - 0.3))
        return (1 if on else 0), v_node


def cost(cand):
    """Device count of one operator instance (threshold comparators counted separately/global)."""
    paths = NETWORK[cand]
    if len(paths) == 1 and len(paths[0]) == 1:
        return dict(switches=0, inverter_comparators=0, pulldown=0, output_comparator=0)
    inv = len({x for p in paths for x in p if x.startswith('~')})
    return dict(switches=sum(len(p) for p in paths), inverter_comparators=inv, pulldown=1, output_comparator=1)
