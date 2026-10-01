# MFS0-E3 Theory: Conditional Relation Memory and Structure Synthesis

Outcomes and windows are inherited from E2 (`../e2/THEORY.md`).

## 1. Learning target

For each entry of history i at time s, the outcome is

Y = 1{N_L([s, s+H)) ≥ 1}, with H = 1.5·ln 2 = 1.039721 s.

N_L counts only L events that were actually accepted by the L entry gate.

The condition is computed from the state at step start:

k = c_i(x(s⁻)) ∈ {0, 1}.

The prediction is p̂ = R_{i,k}(z_{i,k}(s⁻)). Histories that are not split keep the E2 marginal readout.

## 2. Ideal gain and its limits

Within one history, the ideal Bayes Brier improvement of the conditional over the marginal is

B(p_i) − B(p_C) = E[(p_C − p_i)²].

For a binary condition this is π(1−π)(p₁−p₀)².

This is a representational upper bound only. It ignores finite samples, update noise, delay, condition-detection error and device cost. The evaluator reports separately: the in-sample oracle, the continuous reference, and the node. The resulting split is in `E3_evaluation.json`, field `ideal_vs_node`.

## 3. Structure

| Object | Physical realisation | Lifetime |
|:--|:--|:--|
| Event traces x_W0, x_W1, x_W2, x_L | one RC capacitor per path, C_x = 1e-5 F, τ_x = 1 s; set to V_x = V_D = 2 V by a switch from the rail | whole stream; shared by every reader |
| Literal X_a^(d) | ideal comparator (C1) of x_a against V_x·e^(−d/τ_x), d ∈ {H, 2H} | stateless |
| Relation operator | single literal: comparator output; compound literal: MOSFET pull-up network, G_pd pull-down, output comparator at V_D/2 (C2: static node) | stateless |
| Routing latch K | one capacitor per slot of a split history, τ_K = 30 s, read at 1 V, cleared after settlement through G_Krst = 1e-3 S | admission → settlement end + ≈75 ms |
| Marginal carrier m_i | E2 Memristor, branches as in E2 | whole stream |
| Leaf carriers c_i0, c_i1 | Memristor; branches = E2 branch chain + route switch gated by K read / complement | whole stream |

## 4. Candidate family (fixed in advance)

j and l are the other two histories in fixed order. The literals are U = X_Wj^(H), V = X_Wl^(H) and Q = X_L^(H).

The seven candidates are:

| Candidate | Condition |
|:--|:--|
| C1 | Q |
| C2 | X_L^(2H) |
| C3 | U |
| C4 | V |
| C5 | U ∧ V |
| C6 | U ⊕ V |
| C7 | Q ∧ (U ∨ V) |

**Selection is offline** (`structure_select.py`) and uses only the 24 E2 formal streams:
- D1 = streams 0–11 selects the candidate.
- D2 = streams 12–23 validates it with a paired t test (upper bound < 0) and a support check (each leaf ≥ 120; ≥ 8 streams with ≥ 10 per leaf).

**Result:** all three histories selected C1, and all passed D2.

**Interpretation:** C1 exploits the refractoriness and spacing (about 1.9 s) of the single L channel. If an L was accepted within the last H, another L can hardly fall inside the next H. This is real temporal structure in the environment, not a cross-history causal relation.

The joint task X uses C6 by prior specification. It is not something the selector discovered.

## 5. Step order (frozen; `conditional_memory_core.py`)

1. **Snapshot (old state).**
   - Read currents of all carriers.
   - Literals → condition (in R, the bit from the experiment random port instead).
2. **Admission (old slot state).** Requires T < θ_lo ∧ O < O_free; split slots additionally require K < K_free.
3. **T and K.**
   - T is set and leaks (E2).
   - K is set when the slot is admitted and the condition is 1.
   - K is held, and reset while T_new < θ_lo.
4. **O.** Set, hold and reset as in E2.
5. **Writes.**
   - All branch conductances are computed from the old carrier state.
   - Marginal branches are as in E2.
   - Leaf branches are routed by the K read.
   - Each carrier gets one node solution, V_M = RΣGE/(1+RΣG), and one update per step, with dt applied once.
6. **Traces.** They take this step's accepted pulses, which become visible from the next step.
7. **Records.** The caller emits immutable records from the snapshot taken in step 1.

With an empty relation table, the core is bit-identical to the E2 MemoryCore (dev check).

## 6. Registered idealisations

L1–L4 and C1 are inherited from E2.

Extensions:
- **C2:** the static logic node.
- **L5:** T, O and K are read by MOSFET gates with zero gate current (ideal fan-out).

Measured deviations:
- The trace boundary sits at +1 dt relative to the time reference: the comparator reads (k−k_a−1)dt < d, while the reference uses (k−k_a)dt ≤ d.
- The trace set error is −2.4e-6 (relative).
- The leaf dose is (1 − about 3e-5) × the marginal dose, because of the series route switch.
- K adds up to 75 ms of slot occupancy. The longest occupancy is 3.128 s, below 2 × 2.6 s.

## 7. Qualification scope

- The structure is chosen by an **external offline selector, not learned online**. The condition family is finite, and source stimuli are designed per task.
- L is the project's live boundary (BaseGenerator → CollectorBoundaryPort → PhysicalEntryGate). Sites are 28/31/21 → 23.
  - **Site 21 is not in FROZEN_THERMAL_SITES.**
  - The B/C/R groups are a paired-core comparison on one live source pass. They are not three independent live experiments.
- Comparators, logic and switches are behavioural MOSFET.conduct() devices. They are not transistor-level designs.
