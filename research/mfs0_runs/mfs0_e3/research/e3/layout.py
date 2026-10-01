"""MFS0-E3 structure synthesis: occupancy-interval analysis, layout comparison, device
accounting, relation hypergraph (plan §4.2, §7.1, §8). Offline / design-time only.

Occupancy of experience a: I_a = [s_a, f_a), f_a = first tick at which T, O and K of the
slot are all recyclable (measured on the node, dev_checks_e3 / _occK):
  2.846 s (no L observed, K = 0), 2.921 s (K = 1, no L), 3.128 s (L observed).
Writes results/layout/{resource_layout.json, relation_graph.json}.
"""
import json
import math
import os
import pickle

import e3_common as C
from relation_operator import NETWORK, cost as op_cost
from reference_solver_e3 import q_of

DT = C.DT
D_NO_L, D_K1, D_L = 2.846, 2.921, 3.128
GATE_RECOVERY = 1.204          # PhysicalEntryGate t_open (TSS-R1b): minimal same-path entry spacing
GAP_MIN_A = 2.60               # E2 generator contract (template 1.354 s + recovery 1.204 s)


def max_overlap(intervals):
    ev = sorted([(a, 1) for a, b in intervals] + [(b, -1) for a, b in intervals], key=lambda x: (x[0], x[1]))
    m = n = 0
    for _, d in ev:
        n += d
        m = max(m, n)
    return m


def occupancy_on_e2(relation):
    per_hist, glob = [0, 0, 0], 0
    from relation_spec import cond_ref
    for s in range(24):
        d = pickle.load(open(os.path.join(C.E2_DIR, 'results', 'formal', f'stream_{s:02d}.pkl'), 'rb'))['full']
        l = sorted(d['l_ticks'])
        w = [sorted(r[0] for r in d['rows'] if r[1] == i) for i in range(3)]
        allv = []
        for i in range(3):
            iv = []
            for k in w[i]:
                q = q_of(k, l, DT)
                kk = cond_ref(relation[i], i, k, w, l, DT) if i in relation else 0
                dur = D_L if q else (D_K1 if kk else D_NO_L)
                iv.append((k * DT, k * DT + dur))
            per_hist[i] = max(per_hist[i], max_overlap(iv))
            allv += iv
        glob = max(glob, max_overlap(allv))
    return per_hist, glob


def device_count(splits):
    """Count devices of the implemented dedicated layout (from the code structure)."""
    n_split = len(splits)
    slots = 6
    split_slots = 2 * n_split
    dev = {
        'capacitors': dict(T=slots, O=slots, K=split_slots, traces=4),
        'long_term_carriers': dict(marginal=3, conditional=2 * n_split),
        'comparators': dict(
            E2_slot_free_T=slots, E2_slot_free_O=slots, E2_window=slots,
            K_free=split_slots, K_read=split_slots, K_read_complement=split_slots,
            trace_thresholds=len({lit for c in splits.values() for p in NETWORK[c] for lit in p
                                  if lit.lstrip('~') in ('Q', 'Q2')}) +
            len({(i, lit.lstrip('~')) for i, c in splits.items() for p in NETWORK[c] for lit in p
                 if lit.lstrip('~') in ('U', 'V')}),
            operator_inverters=sum(op_cost(c)['inverter_comparators'] for c in splits.values()),
            operator_outputs=sum(op_cost(c)['output_comparator'] for c in splits.values())),
        'mosfet_switches': dict(
            E2_T_set=slots, E2_O_set=slots, E2_O_reset=slots,
            E2_write_chains=slots * 2 * 4, E2_read=3,
            trace_set=4, K_set=2 * split_slots, K_reset=split_slots,
            leaf_write_chains=split_slots * 2 * 2 * 5, leaf_read=2 * n_split, read_mux=2 * n_split,
            operator_switches=sum(op_cost(c)['switches'] for c in splits.values())),
        'resistors': dict(E2_R_T=slots, E2_R_o=slots, E2_sense=3, R_x=4, R_K=split_slots, R_Krst=split_slots,
                          leaf_sense=2 * n_split,
                          operator_pulldown=sum(op_cost(c)['pulldown'] for c in splits.values())),
        'read_ports_assumed_ideal_gate_fanout': dict(
            T_reads_per_slot='E2: T-set? no; window, free, settle×2, O-reset' + (', K-reset' if n_split else '')
            + (', leaf settle×4' if n_split else ''),
            O_reads_per_split_slot='marginal UP/DN + leaf UP/DN ×2 leaves',
            K_reads_per_split_slot='free, read, read-complement'),
    }
    tot = {k: sum(v.values()) for k, v in dev.items() if k != 'read_ports_assumed_ideal_gate_fanout'}
    return dev, tot


def main():
    rel = json.load(open(os.path.join(C.RES, 'selection', 'relation_table.json')))
    splits = {int(k): v['candidate'] for k, v in rel['splits'].items()}
    per_hist, glob = occupancy_on_e2(splits)
    bound_contract = math.ceil(D_L / GAP_MIN_A)
    bound_gate = math.ceil(D_L / GATE_RECOVERY)
    dev_d, tot_d = device_count(splits)
    # pooled layout: P shared slots; each slot stores history id (⌈log2 3⌉ = 2 bit latches) + condition bit;
    # arbitration of simultaneous entries; routing from every slot to every carrier (3 marginal + 6 leaves).
    P_needed_contract = 3 * bound_contract
    pooled = dict(slots_required_to_keep_E2_input_contract=P_needed_contract,
                  slots_observed_dev_max=glob,
                  per_slot_extra=dict(history_id_latches=2, condition_latch=1, arbitration_comparators='priority encoder ≥ 3',
                                      write_chains=(3 + 6) * 2, versus_dedicated_write_chains=2 + 4),
                  verdict=('no state saving: keeping the E2 input contract needs %d slots (= dedicated); fewer slots '
                           'would reject inputs E2 accepts; per-slot identity latches, arbitration and 9-way routing '
                           'increase every other cost' % P_needed_contract))
    layout = dict(
        chosen='dedicated', rule='plan §8: equal function + input contract first; pooled is dominated',
        occupancy_durations_s=dict(no_L_K0=D_NO_L, K1_no_L=D_K1, L_observed=D_L),
        dev_material_max_concurrency=dict(per_history=per_hist, global_=glob, source='24 E2 formal streams (dev material)'),
        conservative_bounds=dict(per_history_under_A_contract=bound_contract,
                                 per_history_under_gate_recovery_only=bound_gate,
                                 note='gate-recovery-only inputs can exceed 2 slots → CAPACITY_REJECTED (E2 semantics, kept)'),
        pooled=pooled,
        identity_information_lower_bound_bits=dict(per_split_slot=1, total=2 * len(splits), implemented='1 binary K per split slot'),
        dedicated_devices=dev_d, dedicated_totals=tot_d,
        state_account=dict(capacitor_states=sum(dev_d['capacitors'].values()),
                           long_term_carriers=sum(dev_d['long_term_carriers'].values()),
                           E2=dict(capacitor_states=12, long_term_carriers=3)),
        not_counted=['rails (shared V_D, V_write, V_S, V_read)', 'reference dividers for comparator levels',
                     'source/bridge interfaces', 'log memory (separate account)'])
    hyper = []
    for i in range(3):
        hyper.append(dict(id=f'e_m{i}', kind='marginal', inputs=[dict(port=f'W{i}', type='gate-accepted entry pulse', unit='0/1 per tick')],
                          condition=None, output=dict(port='L', window='[s, s+H)', H_s=1.0397207708399179),
                          local_state=f'slot pair (T,O) of history {i}', carrier=f'm{i}',
                          write_route='settle window (θ_lo<T<θ_hi) × O-polarity → marginal node', cost='E2'))
        if i in splits:
            c = splits[i]
            for k in (0, 1):
                hyper.append(dict(id=f'e_{i}{k}', kind='conditional',
                                  inputs=[dict(port=f'W{i}', type='gate-accepted entry pulse', unit='0/1 per tick'),
                                          dict(port='trace ' + ','.join(sorted({x.lstrip('~') for p in NETWORK[c] for x in p})),
                                               type='RC trace voltage via comparator', unit='V')],
                                  condition=dict(candidate=c, network=NETWORK[c], value=k,
                                                 visible='step start (x(s^-)), before this step’s pulses'),
                                  output=dict(port='L', window='[s, s+H)', H_s=1.0397207708399179),
                                  local_state=f'slot (T,O,K) of history {i}; K latched at admission',
                                  carrier=f'c{i}{k}', write_route='K read (comparator) → route switch → leaf node',
                                  cost=dict(op=op_cost(c), per_slot='K cap + 3 comparators + 3 switches + 10 write FETs per leaf pair')))
    os.makedirs(os.path.join(C.RES, 'layout'), exist_ok=True)
    json.dump(layout, open(os.path.join(C.RES, 'layout', 'resource_layout.json'), 'w'), indent=1, ensure_ascii=False)
    json.dump(dict(domain_A_L=dict(splits=splits, hyperedges=hyper),
                   domain_X=dict(splits={0: 'C6'}, note='pre-specified expressive-capacity task (plan §10.2)')),
              open(os.path.join(C.RES, 'layout', 'relation_graph.json'), 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(dict(per_hist=per_hist, glob=glob, bounds=layout['conservative_bounds'], totals=tot_d,
                          state=layout['state_account']), indent=1))


if __name__ == '__main__':
    main()
