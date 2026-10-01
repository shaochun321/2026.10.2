"""MFS0-E3 conditional memory core: E2 marginal memory + finite condition relations.

TYPE:SEMI (research layer; production Capacitor / MOSFET / Memristor / PowerRail
unmodified; E2 Params, series(), relax() and comparator convention reused verbatim).

Runtime inputs per step (current values only): b_W[i], b_L, dt, and — for the random-
partition control R only — r_bits[i] from the explicitly labelled experiment random
port. No probability, phase, outcome, source bit, future time or selector output other
than the frozen relation table (wiring) enters.

Per history i: marginal carrier ('m', i) exactly as E2 (memory_core.MemoryCore).
Per split history i: two leaf carriers ('c', i, 0/1), a RelationOperator on the shared
ContextTraces, and a RoutingLatch K on each of its two slots.

Step order (plan §7.4, frozen):
 1. snapshot: read currents of ALL carriers and the condition of every split history
    from the OLD state (traces before this step's pulses; carriers before writes);
 2. admission from OLD slot state: T < θ_lo ∧ O < O_free (∧ K < K_free for split slots);
 3. T set/leak (E2), then K set (admitted ∧ condition 1) / hold / reset (T_new < θ_lo);
 4. O set/hold/reset (E2);
 5. writes: every branch conductance from the OLD carrier state; marginal branches as E2;
    leaf branches routed by the K read; one node solution and one update per carrier;
 6. traces take this step's accepted pulses (visible from the next step);
 7. the caller emits immutable records from the step-1 snapshot.
With an empty relation table the core is bit-identical to E2 MemoryCore (dev check).
"""
from nexus_v1.components.semiconductor import Memristor
from memory_core import MemoryCore, series, relax, VTH
from context_trace import ContextTraces
from routing_latch import RoutingLatch
from relation_operator import RelationOperator


class CondMemoryCore(MemoryCore):
    def __init__(self, splits=None, w0=0.5, random_port=False, slot_order=None, reverse_sum=False):
        super().__init__(n_hist=3, n_slot=2, w0=w0, slot_order=slot_order, reverse_sum=reverse_sum)
        self.splits = {int(k): v for k, v in (splits or {}).items()}
        self.random_port = random_port
        self.traces = ContextTraces(self)
        self.leaf = {}            # i -> (carrier index of leaf 0, of leaf 1)
        self.op = {}
        self.K = {}               # i -> [RoutingLatch per slot]
        for i in sorted(self.splits):
            c0 = len(self.mem)
            self.mem += [Memristor(w=w0, r_min=0.1, r_max=10.0), Memristor(w=w0, r_min=0.1, r_max=10.0)]
            self.leaf[i] = (c0, c0 + 1)
            self.op[i] = RelationOperator(self, self.traces, i, self.splits[i])
            self.K[i] = [RoutingLatch(self) for _ in range(self.n_slot)]
        self.carrier_names = [('m', i) for i in range(3)] + \
            [('c', i, k) for i in sorted(self.splits) for k in (0, 1)]
        # per-leaf write bookkeeping (dose = Σ|I_j|dt per branch, net charge = signed Σ)
        self.leaf_q_up = [0.0] * len(self.mem)
        self.leaf_q_dn = [0.0] * len(self.mem)
        self.leaf_settle_steps = [0] * len(self.mem)
        self.leaf_settle_entries = [[[0, 0] for _ in range(self.n_slot)] for _ in range(3)]
        self._in_leaf_settle = [[None] * self.n_slot for _ in range(3)]
        self.route_log = []
        self.route_flips = 0
        self.n_object_ids = self._object_count()

    def _object_count(self):
        n = len(self.mem) + sum(len(s) for s in self.slots) * 2
        if hasattr(self, 'traces'):
            n += len(self.traces.cap) + sum(len(v) for v in self.K.values())
        return n

    # ── read-only snapshot (step-order item 1) ──
    def snapshot(self, r_bits=None):
        i_read = [self.P.V_read * self.g(self.P.gm_p, self.v_sense(m) - (self.V_lo - VTH)) for m in self.mem]
        cond, level, lits = {}, {}, {}
        for i in self.splits:
            li = self.op[i].literals()
            k_net, v_node = self.op[i].evaluate(li)
            lits[i] = li
            if self.random_port:
                k = 1 if (r_bits is not None and r_bits[i] > 0.5) else 0
            else:
                k = k_net
            cond[i] = (k, k_net)
            level[i] = self.P.V_D if k else 0.0
        return i_read, cond, level, lits

    def slot_free_c(self, i, r):
        s = self.slots[i][r]
        if not self.slot_free(s):
            return False
        return self.K[i][r].is_free() if i in self.K else True

    # ── one step ──
    def step(self, b_W, b_L, dt, r_bits=None):
        P = self.P
        # 1. snapshot from OLD state. Read branches and the logic node are stateless (L3, C2): they are
        #    evaluated only on steps where an entry consumes them — output-identical to every-step evaluation.
        any_w = b_W[0] > 0.5 or b_W[1] > 0.5 or b_W[2] > 0.5
        if any_w:
            i_read, cond, level, lits = self.snapshot(r_bits)
        else:
            i_read, cond, level, lits = None, {}, {i: 0.0 for i in self.splits}, {}
        # 2. admission from OLD slot state
        accepted = [-1] * 3
        rejected = [False] * 3
        free_before = [None] * 3
        for i in range(3):
            if b_W[i] > 0.5:
                free_before[i] = sum(1 for r in range(self.n_slot) if self.slot_free_c(i, r))
                for r in self.slot_order[i]:
                    if self.slot_free_c(i, r):
                        accepted[i] = r
                        break
                if accepted[i] < 0:
                    rejected[i] = True
        g_rail = 1.0 / P.r_int
        # 3. T set/leak (E2) ; K set/hold/reset
        for i in range(3):
            for r, s in enumerate(self.slots[i]):
                g_set = series(self.g(P.gm_sw, 1.0), g_rail) if accepted[i] == r else 0.0
                if accepted[i] == r:
                    s.n_accept += 1
                elif s.T.charge == 0.0:
                    continue                  # undriven empty capacitor: relax is an exact no-op
                relax(s.T, [(g_set, P.V_D), (1.0 / self.R_T, 0.0)], dt)
            if i in self.K:
                lv = level[i]
                for r, s in enumerate(self.slots[i]):
                    if accepted[i] != r and self.K[i][r].cap.charge == 0.0:
                        continue              # undriven empty K: exact no-op
                    self.K[i][r].step(accepted[i] == r, lv, s.T.voltage, dt)
        # 4. O set (window on NEW T) / hold / reset  (E2)
        for i in range(3):
            for s in self.slots[i]:
                vT = s.T.voltage
                win = self.cmp_on(vT - (P.theta_hi - VTH))
                if s.O.charge == 0.0 and not (win and b_L > 0.5):
                    continue                  # undriven empty O: exact no-op
                g_setO = series(self.g(P.gm_sw, b_L), P.G_cmp, g_rail) if (win and b_L > 0.5) else 0.0
                g_rst = self.g(P.gm_rst, (P.theta_lo + VTH) - vT)
                relax(s.O, [(g_setO, P.V_D), (1.0 / self.R_o, 0.0), (g_rst, 0.0)], dt)
        # 5. writes — all conductances from the OLD carrier state
        Vw = self.rail_write.vdd
        n_car = len(self.mem)
        sumG = [0.0] * n_car
        sumGE = [0.0] * n_car
        branches = []
        vRc = [self.v_sense(m) for m in self.mem]
        hist_order = range(2, -1, -1) if self.reverse_sum else range(3)
        for i in hist_order:
            c = i
            vR = vRc[c]
            gz_up = self.g(self.gm_z, (self.V_hi + VTH) - vR)
            gz_dn = self.g(self.gm_z, vR - (self.V_lo - VTH))
            split = i in self.K
            if split:
                leaf_gz = []
                for cl in self.leaf[i]:
                    v = vRc[cl]
                    leaf_gz.append((cl, self.g(self.gm_z, (self.V_hi + VTH) - v), self.g(self.gm_z, v - (self.V_lo - VTH))))
            rs = range(self.n_slot - 1, -1, -1) if self.reverse_sum else range(self.n_slot)
            for r in rs:
                s = self.slots[i][r]
                vT = s.T.voltage
                g_settle = series(self.g(P.gm_sw, vT), self.g(P.gm_sw, (P.theta_hi + VTH) - vT))
                now = g_settle > 0.0
                if now and not s.in_settle:
                    s.n_settle += 1
                s.in_settle = now
                if g_settle <= 0.0 or Vw <= 0.0:
                    if split:
                        self._in_leaf_settle[i][r] = None
                    continue
                vO = s.O.voltage
                g_o_up = self.g(P.gm_sw, vO)
                g_o_dn = self.g(P.gm_sw, P.V_D - vO)
                g_up = series(g_settle, g_o_up, gz_up, g_rail)
                g_dn = series(g_settle, g_o_dn, gz_dn, g_rail)
                if g_up > 0:
                    sumG[c] += g_up
                    sumGE[c] += g_up * Vw
                    branches.append((s, c, g_up, +1))
                if g_dn > 0:
                    sumG[c] += g_dn
                    sumGE[c] -= g_dn * Vw
                    branches.append((s, c, g_dn, -1))
                if split:
                    k_on = self.K[i][r].read()                 # routing by the held K only
                    sel = 1 if k_on else 0
                    if self._in_leaf_settle[i][r] is None:
                        self._in_leaf_settle[i][r] = sel
                        self.leaf_settle_entries[i][r][sel] += 1
                        self.route_log.append((i, r, sel))
                    elif self._in_leaf_settle[i][r] != sel:
                        self.route_flips += 1                   # K read changed inside one settlement
                    for kk, (cl, gzu, gzd) in enumerate(leaf_gz):
                        g_route = self.g(P.gm_sw, P.V_D if (kk == sel) else 0.0)
                        if g_route <= 0.0:
                            continue
                        gu = series(g_settle, g_o_up, gzu, g_route, g_rail)
                        gd = series(g_settle, g_o_dn, gzd, g_route, g_rail)
                        if gu > 0:
                            sumG[cl] += gu
                            sumGE[cl] += gu * Vw
                            branches.append((None, cl, gu, +1))
                        if gd > 0:
                            sumG[cl] += gd
                            sumGE[cl] -= gd * Vw
                            branches.append((None, cl, gd, -1))
        for c in range(n_car):
            if sumG[c] <= 0.0:
                continue
            R = self.mem[c].resistance
            V_M = R * sumGE[c] / (1.0 + R * sumG[c])
            I_M = sumGE[c] / (1.0 + R * sumG[c])
            if I_M > 0:
                self.mem[c].update(current=I_M * dt, pre_trace=0.0, post_trace=1.0)
            elif I_M < 0:
                self.mem[c].update(current=-I_M * dt, pre_trace=1.0, post_trace=0.0)
            if c >= 3:
                self.leaf_settle_steps[c] += 1
            for s, cc, gj, sign in branches:
                if cc == c:
                    Ij = gj * (sign * Vw - V_M)
                    if s is None:
                        if sign > 0:
                            self.leaf_q_up[c] += Ij * dt
                        else:
                            self.leaf_q_dn[c] += -Ij * dt
                    elif sign > 0:
                        s.q_up += Ij * dt
                    else:
                        s.q_dn += -Ij * dt
        # 6. traces take this step's accepted pulses
        self.traces.step([b_W[0], b_W[1], b_W[2], b_L], dt)
        return dict(i_read=i_read, cond=cond, lits=lits, accepted=accepted, rejected=rejected,
                    free_before=free_before)

    def p_hat(self, snap_i_read, i, cond):
        """Read path: leaf selected by the step-start condition (mux) for split histories."""
        if i in self.splits:
            c = self.leaf[i][cond[i][0]]
            return snap_i_read[c] / self.I_fs, c
        return snap_i_read[i] / self.I_fs, i
