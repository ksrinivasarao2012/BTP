# Phase 4 (v2) — Consistency-Based T-Cell Trust Filter

**Owner:** Srinivasa
**Date:** 2026-06-19
**Status:** Plan — supersedes `PHASE_4_TRUST_MODULE_PLAN.md` (that version's *learned* gate
cannot train: the fusion is NumPy in the env, so no gradient reaches the gate, and its inputs
can't distinguish a liar from an honest drone). This v2 uses a **hand-coded consistency filter**
that requires **no retraining**.

---

## 0. Why v2 (what was wrong with v1)

The v1 learned `TCellTrustGate` is unlearnable as drawn:
1. **Causality loop** — the env builds `obs[6:54]` *before* the policy runs, but the gate's
   weights come *from* the policy. Env needs weights it doesn't have yet.
2. **No gradient path** — fusion (`_cast48`, `min`, masking) is NumPy inside the env. PPO sends
   **zero gradient** to the gate; it never learns.
3. **No discriminative input** — `[ego_blind, rel_pos, comm_active]` is identical for a liar and an
   honest drone. The *only* signal that exposes a false-obstacle liar is **disagreement** with
   other sensors. v2 builds the defense around exactly that.

**Key advantage of v2:** the filter changes *which neighbors feed the fused obs*. The trained
`raster_slot_fusion_ON_stage2_final.zip` already navigates on that fused slot, so the defense is
**zero-shot — no retraining**. Experiments are pure eval (hours, not days).

---

## 1. Threat model — coherent false-obstacle injection (the ONLY meaningful attack here)

Dropped from v1 and why:
- **Silence** = contributes nothing = indistinguishable from a dropout-blind drone, which the OFF
  baseline (53%) already handles. Down-weighting a silent node is a no-op. **No defense needed.**
- **Ramming** = physical attack, unrelated to the comm channel, and already a **failed
  fundamental-limit result** (~75–80% ceiling) in earlier Phase C/D. Report separately, do not
  fold into "trust."

**Kept attack — coherent false obstacles (must be a real attack, not v1's random flicker):**
A traitor `j` broadcasts a **persistent phantom** obstacle placed **on the victim's path to goal**
(or a fixed in-field phantom). Persistent + path-relevant = the victim detours/freezes. Implement as:
- At episode reset, each traitor picks a phantom center on the segment ego→goal region (or a fixed
  seed-stable point in the arena), radius ~ real-obstacle scale.
- Each step the traitor *adds that same phantom* to its broadcast set (coherent over time).
- Contrast with v1's `np.random.uniform` per-step flicker — that is a strawman; do **not** use it.

---

## 2. Defense — consistency-based T-Cell trust filter ("self / non-self")

**Intuition (immune metaphor):** a broadcast is "non-self" (rejected) if other sensors that *can
see that location* disagree with it. T-cell memory = per-neighbor trust accumulated over time, so a
repeat liar is driven to zero.

### 2.1 Per-broadcast validation (disagreement test)
For each obstacle `o` broadcast by neighbor `j`:
- **Verifiers** = agents `k ≠ j` (including ego) that are **non-blind** and within `lidar_range`
  of `o` (i.e. they *should* see `o` if it were real).
- If `#verifiers ≥ 1` and **no verifier actually senses an obstacle at `o`** → `o` is a phantom →
  flag this broadcast as inconsistent.
- If `o` is real, verifiers confirm it → not flagged.
- **Honest note (the fundamental limit):** if `#verifiers == 0` (only `j` is near `o`), the claim
  is **unfalsifiable** — include it with benefit of the doubt. A smart attacker places phantoms
  where no one else can check → residual damage. This caps the result below 100% and is a
  *feature* to disclose, not a bug.

> Why this isn't a leak: validation uses only what *other drones sense* (physically available to
> the swarm), not the env's hidden truth as a label. Implementation may read `self.obstacles` to
> compute "what verifier k senses," but that is exactly what k's own LiDAR would return — disclose
> this equivalence in the paper.

### 2.2 Trust state update (EWMA T-cell memory)
Per ego `i`, per neighbor `j`, maintain `t_{ij} ∈ [0,1]`, init `1.0`:
```
flag_j  = (fraction of j's broadcasts this step that are inconsistent) > tau_flag   # e.g. tau_flag=0.5
t_ij <- (1 - alpha) * t_ij + alpha * (0.0 if flag_j else 1.0)                       # alpha = 0.3
```
Fusion inclusion: neighbor `j` contributes to ego `i`'s fused map **only if `t_{ij} >= tau_trust`**
(e.g. `tau_trust = 0.5`). (Binary gate is cleaner to defend than radius-scaling; v1's
`radii * w_j` is geometrically dubious — drop it.)

### 2.3 Where it lives
Entirely in `swarm_env_raster.py` fusion path — **no network changes, no retraining**. Add a
`trust_defense` flag; when on, run §2.1–2.2 before building the fused `obs[6:54]`.

---

## 3. Implementation steps

### Step 1 — `swarm_env_raster.py`: traitor injection + trust filter
Add to `__init__`:
```python
traitor_indices=None,          # list[int]
traitor_behavior="false_obstacles_coherent",
trust_defense=False,           # apply T-Cell consistency filter
trust_alpha=0.3, tau_flag=0.5, tau_trust=0.5,
```
State: `self._phantoms = {}` (per-traitor fixed phantom, set on reset);
`self._trust = np.ones((n_drones, n_drones))` reset each episode.

New method `_fused_lidar_trust(idx)` = copy of `_fused_lidar` but:
- For a traitor neighbor `j`: its contributed obstacle set = its true sensed set **plus** its
  phantom(s) (coherent).
- Before adding `j`'s set, run validation (§2.1) → update `t[idx,j]` (§2.2) → include only if
  `t[idx,j] >= tau_trust`.
- When `trust_defense=False`: skip validation, include traitor broadcasts verbatim (this is the
  "attacked, undefended" condition).

`_observe`: when `slot_fusion and trust mode`, call `_fused_lidar_trust(idx)` instead of
`_fused_lidar(idx)`.

### Step 2 — `eval_trust_defense.py` (new)
Reuse the extractor/policy classes and the eval loop from `eval_slot_fusion_zero_shot.py`.
Model: `models/raster_slot_fusion_ON_stage2_final.zip`, `slot_fusion=True`, dropout=0.10/sustain=5.
Sweep the matrix in §4, paired per-map seeds, drone-level success + bootstrap CI, and the
detection metrics in §5. Emit `results/trust_defense.csv`.

---

## 4. Experiment matrix (all zero-shot on the ON model)

| # | Traitors `k` | Defense | Purpose |
|---|---|---|---|
| 1 | 0 | — | Baseline (target ~94%) |
| 2 | 0 | T-Cell | **No-harm check** — filter must NOT hurt honest swarm (≥~93%) |
| 3 | 1 | off | Attack is real (success must drop) |
| 4 | 1 | T-Cell | Recovery toward baseline |
| 5 | 2 | off | Stronger attack |
| 6 | 2 | T-Cell | Recovery |
| 7 | 3 | off | Saturation |
| 8 | 3 | T-Cell | Recovery |
| 9 | 1 | T-Cell | **Unfalsifiable-placement** phantom (no verifier) → honest limit |

500 maps/condition for final numbers (200 while iterating).

---

## 5. Metrics

- **Drone-level success %** + 95% bootstrap CI (primary).
- **Attack damage** = (no-defense) − baseline.  **Recovery** = (defended) − (no-defense).
- **Detection precision / recall** of traitor-flagging (we know ground-truth traitors in sim).
- **False-positive rate** on honest neighbors (must be ~0, else condition #2 fails).
- **Trust trajectory figure**: `t_ij` vs time for an honest vs a traitor neighbor (the money plot).

---

## 6. Success gates (decision)

| Gate | Target |
|---|---|
| #2 no-harm: defense ON, 0 traitors | ≥ ~93% (within noise of 94%) |
| #3 attack works: k=1 undefended | drop ≥ ~10 pp (else no story) |
| #4 recovery: k=1 defended | within ~3 pp of baseline |
| detection recall (verifiable phantoms) | ≥ ~0.9 |
| false-positive rate (honest) | ≤ ~0.02 |

Pass #2 + #3 + #4 → **trust defense validated**. #9 documents the limit, not a gate.

---

## 7. Limitations to disclose (write these in the paper — reviewers will probe)

1. Idealized sharing (ground-truth, noise-free, no latency/localization error).
2. Trust filter is **algorithmic, not learned** — frame novelty as application + immune framing.
3. Consistency detection fails for unfalsifiable phantoms (no verifier) — quantified by #9.
4. Dijkstra goal-heading crutch in `obs[2:4]` (privileged global path).
5. Sim-only, 10 drones, 2D, circular obstacles.

---

## 8. Paper narrative

1. Under LiDAR dropout, collaborative obstacle sharing recovers navigation: **53% → 94%** (+CI, +dropout sweep).
2. Sharing opens a **Byzantine vulnerability**: a single coherent false-obstacle broadcaster drops success by X pp.
3. A **consistency-based T-Cell trust filter** rejects "non-self" broadcasts and restores success to within Y pp of nominal, with detection recall ≥0.9 and ~0 false positives — **zero-shot, no retraining**.
4. We characterize the **fundamental limit**: unfalsifiable phantoms (no verifier) cause residual damage.
5. **TA-MAPPO**: trust-aware collaborative perception for Byzantine-resilient swarm navigation.

---

## 9. Timeline (no retraining → fast)

| Step | Effort |
|---|---|
| 1. Env: traitor + trust filter | ~3–4 h |
| 2. `eval_trust_defense.py` | ~2 h |
| 3. Run matrix (9 conds × 500) | ~3–5 h compute |
| 4. Figures + write-up | ~half day |
| **Total** | **~1.5 days** |

---

## 10. Path to a higher tier (if you want RA-L later — optional, not this week)

- **De-idealize sharing**: add Gaussian noise + localization error + packet drop to broadcasts;
  show the filter still works. (Biggest single credibility win.)
- **Option B learned trust**: feed raw per-neighbor 48-d maps as separate channels, fuse with a
  differentiable in-network attention/gate, + supervised aux traitor-detection head (privileged
  labels at train, dropped at test). Then "learned" is honest.
- Remove or justify the Dijkstra crutch.
