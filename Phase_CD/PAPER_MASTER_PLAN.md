# TA-MAPPO — Paper Master Plan & Result Ledger

**Owner:** Srinivasa
**Last updated:** 2026-06-19
**Purpose:** Single source of truth for writing the paper. Contains the full narrative (from Phase B),
every measured result with the exact command that reproduces it, parameter justifications, the honest
limitations list, what is still pending and how to close it, the paper structure, and the target venue
with concrete reasoning. Read this first before writing any section.

> Working python: `C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe` (call by full path).
> All commands assume CWD = `D:\Swarm\BTP`.

---

## 1. The paper in one paragraph (thesis)

A drone swarm that **shares obstacle observations** over a short-range radio is far more resilient to
**LiDAR sensor failure** than one navigating on its own sensors (drone-level success **53% → 94%** under
~33% sensor dropout). But the same shared-perception channel — fused via a **min operation** into each
drone's obstacle map — opens a **Byzantine attack surface**: a traitor broadcasting **false obstacles**
overrides even a fully-sighted drone's own sensing, dropping honest-drone success by ~10–13 pp,
**independent of sensor dropout**. We show that a **naive consistency filter** defends this perfectly
under ideal sensing **but becomes actively destructive under realistic measurement noise** (it
false-accuses honest neighbours). A **principled, noise-aware "T-cell" trust filter** (self/non-self
consistency + reputation memory; a temporal-trust extension is specced in
`Phase_CD/Noise_added/TEMPORAL_TRUST_RUNBOOK.md` for the σ=0.6 camouflage limit) restores graceful
resilience — full recovery at moderate noise, partial
at severe noise — with **zero false positives**, against both naive and camouflaged attacks. We
characterise the fundamental limit (lies hidden within the sensor-noise band) and show, via noise-aware
fine-tuning (Option C), that the residual high-noise navigation degradation is a **genuine
perception-information limit, not a training artifact** — the defense never makes it worse.

---

## 2. Scope: why the paper starts at Phase B

Phase A (open field, no obstacles, 99.7%) and the earlier leaky Phase-B/C line are **out of scope**.
The paper begins at the **clean, leak-audited Phase-B baseline (M0)** because:
- M0 is the first CTDE-clean model (verified with `leak_test_local.py`: actor ignores the critic block
  0.0%, stagnation leak dead 0.2%; uses only LiDAR + an honest 8 m gated comm radio).
- Everything downstream (collaborative perception, attack, defense) is built on M0, so M0 is the natural
  and *defensible* starting point.
- Starting earlier would force us to re-explain the leakage cleanup, which is internal history, not a
  contribution.

**Disclose in the paper:** M0 carries two inherited idealizations (see §7) — an 8 m *perfect* comm radio
and a global Dijkstra goal-heading. Both must be stated openly.

---

## 3. Narrative arc

```
Phase B  : Clean baseline M0 (LiDAR + 8 m gated comm). No adversary: 95.6% (d=0.20).
   |
Phase 3  : Collaborative perception under sensor dropout.
   |          Neighbours' sensed obstacles fused (min) into the LiDAR slot -> survives blindness.
   |          RESULT: comm ON 94% vs OFF 53% drone-level (+41 pp). Communication is load-bearing.
   |
Phase 4a : The shared channel is an attack surface.
   |          A traitor broadcasts false obstacles; min-fusion lets the lie override own sight.
   |          RESULT: -10..-13 pp at k=2..3, INDEPENDENT of dropout (it's the fusion, not blindness).
   |
Phase 4b : Defense under IDEAL sensing.
   |          Consistency-trust filter ("see nothing where you claim something -> you lied").
   |          RESULT: near-full recovery, P/R ~1.00. (But this is the easy, idealized case.)
   |
Phase 4c : Realistic sensing breaks the NAIVE filter.
   |          Gaussian position noise -> naive fixed-threshold filter false-accuses honest drones
   |          -> WORSE than no defense. (precision 1.00 -> 0.23)
   |
Phase 4d : Principled NOISE-AWARE robust filter.
            eps scales with noise + slower reputation decay -> zero false positives, graceful recovery
            against both wall and camouflaged attacks. Residual gap = info-limit + nav-OOD.
```

---

## 4. System description (for the Methods section)

### 4.1 Environment
- 20×20 m arena, 10 drones, shared goal, circular obstacles, 1200-step episodes, BFS solvability check.
- Continuous 2-D velocity action. CTDE: 650-d obs = `[local(130) || global(520)]`; actor reads `[:130]`,
  critic `[130:]`; only the actor runs at evaluation.
- Obstacle density: early collab-perception / ideal-sensing tables (§5.2–5.5) were at **0.20**; the
  **noise / robust / temporal / adaptive line (§5.6 onward) standardizes on density 0.27** — the calibrated
  fairness ceiling (96.78% BFS-solvable, last density to clear the ≥95% bar; `FINAL_PARAMETER.md`). The agent
  clears 0.30 @ 93.6% (σ=0), so 0.27 is inside proven capability. Trained up to 0.35. Obstacle radii 0.2–2.5 m
  (measured mixture at 0.27: count 29.7, mean radius 0.907 m, bands 42/40/18% small/med/large). Goal kept
  clear within 2 m.
- Code: `Phase_CD/Collab_Perception/env_collab_perception.py` (clean paper env, reproduces M0's obs math).

### 4.2 M0 clean baseline (Phase B)
- Model: `models/apex_ultra_glide_v14_comm8_lidar_final.zip`.
- 48-ray vectorized LiDAR (8 m), 8 m **gated** comm (neighbour pos/vel within 8 m), LiDAR congestion.
- CTDE-clean (leak-audited). No-adversary: **95.6% (d=0.20) / 91.1% (d=0.30)**.

### 4.3 Collaborative perception (Phase 3, the "slot-fusion" architecture)
- The own-LiDAR slot `obs[6:54]` is **replaced** by a fused 48-d channel:
  `fused = normalize( cast48( UNION{ ego own obstacles (if sighted), sender-gated neighbour obstacles,
  other drones } ) )` at 8 m scale.
- **Sensor dropout:** per-step, per-drone, *sustained* blindness. `lidar_dropout=0.10, dropout_sustain=5`
  ⇒ ~33% blind. A blind drone senses nothing for itself **and** (sender-gating) shares nothing.
- **ON** (`use_shared_map=True`): neighbours fill the slot → survives the drone's own blindness.
  **OFF**: own LiDAR only (comm-disabled ablation).
- **The min-fusion is the crux:** it buys dropout-robustness *and* is the later attack surface.
- Trained models: `models/raster_slot_fusion_ON_stage2_final.zip`, `..._OFF_stage2_final.zip`
  (3-stage curriculum, 1M steps each, density 0.15→0.25→0.35).

### 4.4 Byzantine attack model (Phase 4)
- Traitors broadcast a **persistent fabricated phantom** that is NOT a real obstacle (so true map
  solvability is unchanged — a victim that ignored the lie could still reach goal).
- **wall** mode: phantom wall across the (locally open) goal-approach — easy to detect.
- **camouflage** mode: phantoms **hug real obstacles** on the spawn→goal corridor, pushed into the gap —
  hard to detect. `camouflage_gap` tunes the stealth/harm dial.
- Phantoms enter only via the fused channel (a comm attack); the OFF path has no attack surface.
- Code: `Collab_Perception/env_byzantine_trust.py`, `env_byzantine_adaptive.py`.

### 4.5 Consistency-trust defense ("T-cell" self/non-self)
- Per (observer i, neighbour j) trust `t_ij ∈ [0,1]`, EWMA, reset to 1.0 each episode.
- When i is **sighted**, it judges j's broadcast: a broadcast obstacle within i's own sensing range that
  matches **no** real obstacle there is a **contradiction** (i sees the spot is empty ⇒ fabricated).
- Contradiction drives `t_ij` down; a clean judgement toward 1. When i is **blind** it has no opinion
  (`t_ij` unchanged) ⇒ a caught traitor stays caught through blind windows (reputation memory).
- `t_ij < τ` ⇒ neighbour j excluded from i's fusion entirely.
- **Naive** variant: fixed tolerance `verify_eps=0.6`, `alpha=0.5`, `tau=0.5`.
- **Robust** variant: noise-aware tolerance `eps = 0.6 + 4·σ`, slower `alpha=0.25`, `tau=0.4`.
- Honesty: the check reads true obstacle positions only to answer "would my own LiDAR confirm this?"
  (= what i physically senses), **not** a privileged traitor label. Phantom identity is never used.

### 4.6 Noise model (Phase 4d)
- Per drone, per step: each sensed obstacle position perturbed by `N(0, σ)` (radii kept true).
- Applied consistently: a drone **navigates on**, **broadcasts**, and **verifies against** its own
  (independently) noisy view. Physical sensing *range* uses true distance; the *measured position* is noisy.
- Phantoms are exact (the attacker fabricates precisely).
- Code: `Phase_CD/Noise_added/env_noisy_byzantine.py`.

---

## 5. Results ledger (every number + the command that reproduces it)

> All eval uses honest-drone success (traitors excluded from numerator AND denominator, denom = 10−k),
> paired bootstrap 95% CIs over maps. Regime unless noted: 8 m LiDAR, dropout=0.10/sustain=5 (~33% blind),
> density 0.20.

### 5.1 Phase B baseline (no adversary)
| d | success |
|---|---|
| 0.20 | 95.6% |
| 0.30 | 91.1% |

### 5.2 Phase 3 — collaborative perception under dropout (THE ANCHOR: comm is load-bearing)

**CAMERA-READY @ density 0.27, 500 maps, zero-shot (both ON/OFF models):**
| Condition | Drone-level | Map-level (all 10 reach) |
|---|---|---|
| ON (shared map + temporal trust) | **89.34%** | **67.80%** |
| OFF (own LiDAR only) | **45.86%** | **10.40%** |
| **Gap** | **+43.48 pp** | **+57.40 pp, CI [+52.80, +61.80]** |

**Dropout curve (same ON/OFF models across three dropout levels, 500 maps):**
| Dropout level | Blindness (est.) | ON | OFF | Gap | Significance |
|---|---|---|---|---|---|
| 0% | ~0% | 88.70% | 90.04% | −1.34 pp | not significant |
| 10% | ~33% | 87.70% | 46.30% | **+41.40 pp** | **✓ huge, CI [+38.9, +43.8]** |
| 20% | ~50% | 86.20% | 35.36% | **+50.84 pp** | **✓ huge, CI [+48.3, +53.3]** |

**Story:** at 0% dropout (perfect sensing), comm is *optional* (both models succeed equally). At 10% (~33% blind,
the operating point), OFF collapses to 46.3% while ON holds 87.7% → **+41 pp gap, maximum-contrast regime**
where collaboration becomes *load-bearing*. At 20% (50% blind), advantage amplifies (+51 pp). *This is why
dropout exists in the threat model: to make inter-agent sharing necessary, not peripheral.*

**Full tables with 95% CIs:** `RESULTS_027_CAMERA_READY.md` §5.2.

### 5.3 Phase 4a — attack potency (clean sensing, wall, drone-level honest)
| k | honest % | drop vs k=0 | 95% CI |
|---|---|---|---|
| 0 | 93.87% | — | — |
| 1 | 89.70% | +4.16 | [+2.64, +5.78] |
| 2 | 82.88% | +10.99 | [+8.21, +13.95] |
| 3 | 80.67% | +13.20 | [+9.98, +16.61] |

**Dropout-independence (k=2, the mechanism finding):**
| dropout | blind | attack drop | CI |
|---|---|---|---|
| 0.00 | 0% | +10.49 | [+6.81, +14.38] |
| 0.10 | 33% | +11.68 | [+8.00, +15.62] |
| 0.20 | 50% | +11.55 | [+8.11, +15.15] |
| 0.30 | 60% | +12.02 | [+8.75, +15.53] |

→ The attack is the **min-fusion**, not the blind window (it hurts even at 0% blindness).
Reproduce:
```
& $py Phase_CD\Collab_Perception\probe_attack_potency.py models\raster_slot_fusion_ON_stage2_final.zip 300        # k-sweep
& $py Phase_CD\Collab_Perception\probe_attack_potency.py models\raster_slot_fusion_ON_stage2_final.zip 200 dropout # dropout-indep
```

### 5.4 Phase 4b — defense under IDEAL sensing (wall, parallel matrix, 200 maps)
no-harm (k=0, defense ON) = 92.85% vs 92.85% baseline (Δ +0.00).
| k | no-def | defense | recovery | 95% CI | P/R |
|---|---|---|---|---|---|
| 1 | 89.06% | 93.28% | +4.22 | [+2.44, +6.11] | 1.00/0.99 |
| 2 | 81.06% | 92.69% | +11.62 | [+8.06, +15.44] | 1.00/0.98 |
| 3 | 80.14% | 92.50% | +12.36 | [+8.50, +16.36] | 1.00/0.98 |
Reproduce:
```
& $py Phase_CD\Collab_Perception\eval_parallel.py models\raster_slot_fusion_ON_stage2_final.zip 200 matrix 2 10
```

### 5.5 Phase 4c — attack modes under IDEAL sensing (k=2, 500 maps, baseline 93.86%)
| attack | no-def | drop | defense | recovery | P/R |
|---|---|---|---|---|---|
| wall | 84.50% | +9.36 | 93.37% | +8.87 | 1.00/0.99 |
| camouflage | 81.40% | +12.46 | 93.20% | +11.80 | 1.00/0.99 |
→ Camouflage is the *stronger* attack (not a strawman), yet defense still catches it under ideal sensing.
Gap sweep (camouflage) showed P/R stays 1.00 at all gaps — **phantom size, not gap, controls stealth**
under ideal sensing (radius=1.0 keeps the centre detectably in open space).
Reproduce:
```
& $py Phase_CD\Collab_Perception\eval_parallel.py models\raster_slot_fusion_ON_stage2_final.zip 500 attackcmp 2 10
& $py Phase_CD\Collab_Perception\eval_parallel.py models\raster_slot_fusion_ON_stage2_final.zip 300 gapsweep  2 10
```

### 5.6 Phase 4d-i — NAIVE filter CRACKS under noise (wall, k=2, 500 maps, 0.27 density, camera-ready)

**Why naive consistency checking (fixed tolerance) fails under sensor noise:**
| σ (m) | base | attack | naive-defense (precision/recall) | FP-harm | recovery |
|---|---|---|---|---|---|
| 0.0 | 85.94 | 72.25 | 85.90 (1.00/0.98) | +0.00 | +13.65 pp |
| 0.2 | 79.00 | 63.08 | 62.80 (0.28/0.98) | **−13.94 pp** | **−0.27 pp** |
| 0.4 | 65.58 | 51.55 | 38.30 (0.23/0.96) | **−27.48 pp** | **−13.25 pp** |
| 0.6 | 54.88 | 41.15 | 33.05 (0.23/0.94) | **−21.60 pp** | **−8.10 pp** |

**The mechanism:** under noise σ, two honest drones perceive the same obstacle at slightly different positions
(disagreement ~√2σ ≈ 0.85 m at σ=0.6). A fixed-tolerance filter (e.g., eps=0.6 m) expecting agreement →
rejects *both* honest reports as potentially lying → gating out honest neighbors → swarm fragments
(FP-harm −21.60 pp at σ=0.6). **Naive filter becomes *worse than no defense*.** This motivates the
noise-aware robust filter (§5.7).

Full tables & interpretation: `RESULTS_027_CAMERA_READY.md` §5.6.

### 5.7 Phase 4d-ii — ROBUST filter, naive vs robust (wall, 150 maps)
**Primary table = noise-robust base (Option C, `noise_robust_ON_stage1_final.zip`):**
| noise | base | attack | naive (P/R) | robust (P/R) | robust no-harm | robust recovery |
|---|---|---|---|---|---|---|
| 0.0 | 91.1 | 81.3 | 91.5 (1.00/0.98) | 91.8 (1.00/0.98) | 91.1 | +10.4 |
| 0.2 | 88.7 | 72.9 | 74.8 (0.32/0.98) | 88.2 (0.99/0.91) | 88.7 | +15.2 |
| 0.4 | 80.9 | 68.7 | 48.3 (0.23/0.98) | 77.8 (0.97/0.69) | 80.1 | +9.2 |
| 0.6 | 69.9 | 57.2 | 44.4 (0.23/0.96) | 62.8 (0.95/0.39) | 68.1 | +5.6 |
→ Robust filter **fixes false positives** (precision 0.95–1.00, no-harm ≈ base) and recovers gracefully.
The clean-trained base (`raster_slot_fusion_ON_stage2_final.zip`) gave near-identical robust numbers
(0.6: base 67.4 → robust 62.5, +5.5) — i.e. Option C did **not** change the filter's behaviour; see §5.10.

### 5.8 Phase 4d-iii — ROBUST filter vs CAMOUFLAGE under noise (150 maps)
**Primary table = noise-robust base (Option C, `noise_robust_ON_stage1_final.zip`):**
| noise | base | attack | naive (P/R) | robust (P/R) | robust no-harm | robust recovery |
|---|---|---|---|---|---|---|
| 0.0 | 91.1 | 78.4 | 91.0 (1.00/0.99) | 90.0 (1.00/0.97) | 91.1 | +11.6 |
| 0.2 | 88.7 | 76.4 | 77.7 (0.32/0.99) | 86.8 (0.99/0.94) | 88.9 | +10.3 |
| 0.4 | 81.1 | 66.1 | 47.4 (0.23/0.98) | 75.5 (0.98/0.57) | 79.9 | +9.4 |
| 0.6 | 70.2 | 56.0 | 44.1 (0.23/0.97) | 57.4 (0.93/0.21) | 68.0 | +1.4 |
→ Robust filter survives camouflage at moderate noise; at severe noise+camouflage **recall collapses
(0.21)** — the genuine hard regime — but precision stays high (0.93, never destructive). The +1.4pp
recovery at σ=0.6 is within noise. This was the **single-frame** limit (a lie hidden inside the honest
sensor-noise band cannot be contradicted on any one frame); it is **recovered temporally in §5.11**
(recall 0.21 → 0.78, recovery +1.4 → +7.7 pp) by aggregating the offset-vector bias over frames.
Reproduce (5th arg = attack mode):
```
& $py Phase_CD\Noise_added\eval_noise_robust.py models\noise_robust_ON_stage1_final.zip 150 2 10 wall
& $py Phase_CD\Noise_added\eval_noise_robust.py models\noise_robust_ON_stage1_final.zip 150 2 10 camouflage
```

### 5.9 Recovery against the correct ceiling (read recovery vs `base` at each noise, not absolute)
Robust filter (noise-robust base), fraction of the `base − attack` gap it closes:
| noise | wall | camouflage |
|---|---|---|
| 0.0 | ~100% | 91% |
| 0.2 | 96% | 85% |
| 0.4 | 75% | 63% |
| 0.6 | 44% | 10% |

### 5.10 Option C — does a noise-trained base recover the high-noise ceiling? (NO — it's a real limit)
Fine-tuned the ON model under per-episode noise domain-randomization (σ~U[0,0.3] for 1.5M steps, then
σ~U[0,0.6] for 2.0M steps; LR 3e-5; no traitors, no defense — the filter is an eval-time layer).
Output: `models/noise_robust_ON_stage{0,1}_final.zip`. **The base barely moved:**
| noise | base (clean-trained) | base (noise-robust) | Δ |
|---|---|---|---|
| 0.0 | 92.2 | 91.1 | −1.1 |
| 0.2 | 87.1 | 88.7 | +1.6 |
| 0.4 | 79.5 | 80.9 | +1.4 |
| 0.6 | 67.4 | 69.9 | +2.5 |
→ **Key finding:** 3.5M steps of noise training recovered only ~2.5pp at σ=0.6. The 92→70% degradation
is therefore **not** a navigation-OOD training artifact — it is a **genuine perception-information limit**:
at σ=0.6 obstacle positions are fundamentally uncertain and no training recovers them. This *resolves* the
old Limitation 5 (it is reframed as a characterised limit, not a fixable confound) and closes P1. The
robust filter's behaviour is unchanged on the noise-robust base (§5.7/5.8 primary tables), confirming the
defense is safe (precision 0.93–1.00, no-harm ≈ base) regardless of how the base was trained.
**Scope note:** §5.10 is the *navigation* perception limit (the base success ceiling at high σ) and it
**still stands** — temporal trust does not, and cannot, recover sensor information the LiDAR never
provided. What §5.11 recovers is the distinct *security/detection* limit (the single-frame recall collapse
of §5.8); the two are independent.
Reproduce:
```
& $py Phase_CD\Noise_added\run_option_c.py 150 10   # trains both stages, runs both evals
```

### 5.11 Temporal trust — breaking the single-frame noise-band limit (P2/P4, **WIN**)
The σ=0.6 camouflage recall collapse (§5.8, recall 0.21) is a limit of **single-frame** verification, not
of consistency detection per se. A camouflage phantom hugging a real obstacle is never contradicted on
any one frame (it sits inside the widened `eps = 0.6 + 4σ = 3.0 m` band), but the *per-frame offset
vector* it induces is **persistently biased**, whereas an honest neighbour's is **zero-mean**:
> `d_t = (neighbour j's reported obstacle position) − (ego's own sensed position of the matched obstacle)`.
> Honest j: `d_t = noise_j(t) − noise_ego(t) ~ N(0, √2·σ)` → `‖mean(d_t)‖ → 0` over frames.
> Camouflage liar: `d_t = gap_vector − noise_ego(t)` → `‖mean(d_t)‖` stays at the (non-zero) gap.

**Filter (hand-coded, P4):** per `(ego, neighbour, ego-track m*)` keep a running mean of `d_t`
(`env_noisy_byzantine.py` `_temporal_update`). Once a bucket has `≥ temporal_min_k = 20` samples, flag the
neighbour if `‖mean‖ > temporal_bias_eps = 0.6 m`. **Composes (logical OR) with the single-frame robust
check**, which stays the fast path for open-space (wall) phantoms; temporal is the slow path for
camouflage. `temporal_bias_eps` stays TIGHT (0.6 m) — temporal is precisely what lets us avoid the 3.0 m
widened band.

**Probe evidence the mechanism is sound** (`probe_temporal_offset.py`, σ=0.6 camouflage, 150 maps):
- *Oracle association* (statistics only): AUC **0.99**; honest `‖mean‖` p90 = 0.38 vs phantom p10 = 0.87 at
  Kmin=10; median usable-K = 19 (honest) / 45 (phantom) — dropout does not starve the window.
- *Realistic association* (no ground-truth labels; nearest-sighted match): mean-bias AUC **0.85–0.90**
  (Kmin 5–20). The signal survives hand association → buildable without learning.

> ✅ **CAMERA-READY DONE (2026-06-20).** Tables below are the **publication** numbers: **500 maps, density
> 0.27, base = `noise_robust_ON_stage2_final` (0.27 lock-in), RANDOMIZED attack** (per-map n_phantom~U{3,4,5,6},
> per-phantom radius from the real 42/40/18 obstacle mixture), swept **f = 1, 2, 3**, paired-bootstrap 95% CIs.
> Full per-f tables + CIs in **`RESULTS_027_CAMERA_READY.md`**; raw logs in
> `Phase_CD\Noise_added\results_027\eval_f{1,2,3}_{wall,camouflage}_500.txt`. The dev numbers (150 maps,
> density 0.25, stage1, fixed attack) are retired; the qualitative WIN held (temporal recovers the σ=0.6
> camouflage recall collapse, no-harm flat, wall never regresses), with the headline cell slightly lower in
> absolute terms (harder density 0.27 + size-indistinguishable phantoms), as expected.

**STEP-4 CAMERA-READY (500 maps, density 0.27, base=stage2, RANDOMIZED attack, `eps=0.6, min_k=20`;
`eval_temporal.py`). Headline f=2 shown; full f=1,2,3 + CIs in `RESULTS_027_CAMERA_READY.md`.**

*Wall (f=2):*
| noise | base | attack | robust (P/R) | temporal (P/R) | temp no-harm | rob.rec | **tmp.rec** |
|---|---|---|---|---|---|---|---|
| 0.0 | 86.0 | 71.8 | 85.7 (1.00/0.98) | 85.7 (1.00/0.98) | 86.1 | +13.9 | +13.9 |
| 0.2 | 79.1 | 64.5 | 77.6 (0.99/0.90) | 78.6 (0.97/0.92) | 78.8 | +13.1 | +14.1 |
| 0.4 | 65.0 | 54.8 | 62.5 (0.96/0.57) | 63.9 (0.90/0.82) | 65.1 | +7.8 | +9.2 |
| 0.6 | 53.4 | 43.5 | 47.2 (0.94/0.26) | 53.2 (0.82/0.70) | 53.1 | +3.7 | **+9.7** |

*Camouflage (f=2, the decisive cell):*
| noise | base | attack | robust (P/R) | temporal (P/R) | temp no-harm | rob.rec | **tmp.rec** |
|---|---|---|---|---|---|---|---|
| 0.0 | 86.0 | 63.5 | 83.9 (1.00/0.97) | 83.9 (1.00/0.97) | 86.1 | +20.3 | +20.3 |
| 0.2 | 79.1 | 58.3 | 76.0 (0.99/0.86) | 76.9 (0.97/0.94) | 78.8 | +17.8 | +18.6 |
| 0.4 | 64.9 | 47.7 | 58.8 (0.96/0.45) | 64.1 (0.91/0.81) | 65.1 | +11.1 | **+16.4** |
| 0.6 | 53.4 | 37.6 | 41.0 (0.92/**0.13**) | 49.8 (0.82/**0.69**) | 53.0 | +3.4 | **+12.2** |

*Trend across f (σ=0.6 camouflage recovery):* f=1 robust +1.9 (R 0.13) vs temporal +7.1 (R 0.69); f=2
+3.4 vs **+12.2**; f=3 +5.3 vs **+13.6**. Attack saturates (f2→f3 adds ~3 pp damage); detection precision
*rises* with f (0.68→0.82→0.89 at σ=0.6) — defense is most precise when threat is worst.

**Majority-boundary extension f=4,5,6,7 (§5.11b, 500 maps, DONE 2026-07-19) — the "no honest majority" PROOF.**
Each honest ego has ≤9−f honest neighbours (excluded from own set), so f≥5 ⇒ neighbourhood majority-traitor
in expectation; f=6→4 honest, f=7→3 honest (honest minority). σ=0.6 camo temporal recovery [95% CI]:
f=4 **+14.7 [12.0,17.6]** (R0.66,P0.93); f=5 (5:5 tie) **+15.2 [11.9,18.4]** (R0.67,P0.96); f=6 (minority)
**+15.1 [11.6,18.6]** (R0.67,P0.97); f=7 (minority) **+10.9 [7.4,14.5]** (R0.66,P0.98). **All CIs exclude 0**
→ majority claim proven. Robust single-frame at f=7 is **+1.9 [−1.3,5.2] (spans 0, NOT significant)** → temporal
is load-bearing. Precision **monotone 0.68→0.98** across f=1–7; no-harm flat ≈−0.4 (CI spans 0) at every f
(kills the 20-map f=6 −5.5pp scare = small-sample noise). **Honest caveat:** absolute success still falls with f
(temporal 48.8→41.9); filter recovers a stable *fraction*, not traitor-count-invariance. f=8,9 untested → claim
stated "up to seven of ten." Files `eval_f{4,5,6,7}_camouflage_500.txt`; manuscript `tab:headline` now f=1–7.

**Baseline reconciliation (silly-thing #2 CLOSED, 500 maps, DONE 2026-07-19).** Single-policy dropout ablations
(one model, `use_shared_map` toggled) unify the disagreeing baseline numbers: anchor model
(`raster_slot_fusion_OFF_stage2`) 10%-dropout **ON 89.26 / OFF 46.14** reproduces `tab:anchor` (89.3/45.9) by
construction; attacked model (`noise_robust_ON_stage2`, attack off, noise 0) 10%-dropout **ON 85.84 / OFF 41.80
(+44 pp)** → the model we attack has its OWN sharing-load-bearing number ≈ the 86% base. One clean lineage; the
89→86 gap = noise-DR tax. Files `dropout_ablation_500.txt`, `dropout_ablation_noisy_500.txt`.

→ **WIN (camera-ready, f=2).** At σ=0.6 camouflage, temporal lifts recall **0.13 → 0.69** and recovery
**+3.4 → +12.2 pp**, with **no-harm essentially flat** (k=0 defense ON = 53.0 vs base 53.4, **−0.4 pp**, CI
spans 0) at every noise level, and **wall does not regress** (temporal ≥ robust throughout; f=2 wall σ=0.6
+3.7 → +9.7). The trend strengthens with threat: at f=3, σ=0.6 camouflage recovery +5.3 → **+13.6**. The lone
caveat: detection **precision falls to 0.82 at σ=0.6, f=2** (below a 0.9 target; but it *rises* with f to
0.89 at f=3) — and precision was only a *proxy* for false-gating harm, while the no-harm column measures that
harm directly and finds it ≈0. The residual false-flags are ultra-stealthy
camouflage buckets (phantom hugging so tightly it barely protrudes → statistically indistinguishable from
honest noise *and* nearly harmless; the genuine residue, consistent with the camouflage stealth/harm bind).
`eps=0.7` raises precision to ~0.85 but sacrifices harmful-phantom recall, so `eps=0.6` is the operating
point. Reproduce:
```
& $py Phase_CD\Noise_added\probe_temporal_offset.py models\noise_robust_ON_stage1_final.zip 150 2 10 camouflage 0.6
& $py Phase_CD\Noise_added\probe_temporal_offset.py models\noise_robust_ON_stage1_final.zip 150 2 10 camouflage 0.6 --assoc realistic
& $py Phase_CD\Noise_added\eval_temporal.py models\noise_robust_ON_stage1_final.zip 150 2 10 wall
& $py Phase_CD\Noise_added\eval_temporal.py models\noise_robust_ON_stage1_final.zip 150 2 10 camouflage
```

### 5.11b Filter-aware adaptive attacker + offset×noise BIND (camera-ready, 500 maps)  ✅ DONE
The strongest reviewer rebuttal: an attacker who *knows* the temporal filter exists still cannot win.
Four adaptive knobs swept at σ=0.6 over f=1,2,3 (`run_adaptive`), plus the **offset × noise matrix**
(σ∈{0,0.2,0.4} × f∈{1,2,3}, 9 runs, `run_offset_noise`):
- **offset (the stealth/harm bind):** as the phantom centre-offset grows, harm AND detection-recall climb
  *together* — offset=0 is harmless+invisible (recall ~0), offset=2.5 is harmful (+8.5..+18.8 pp) + caught
  (recall 0.66–0.98). **No free lunch, and the bind holds at EVERY noise level** (σ=0,0.2,0.4): the attacker
  can never be both stealthy and harmful. Precision rises with offset (genuine phantoms dominate flags).
- **gap / jitter / duty:** all hold across f=1,2,3 — jitter (zero-mean) doesn't beat the mean test, and
  jitter/duty *reduce the attacker's own harm* faster than they dent recall.
Full matrix + CIs: `RESULTS_027_CAMERA_READY.md` (offset×NOISE matrix). Raw logs:
`results_027/adaptive_{offset,gap,jitter,duty}_f{1,2,3}_500.txt` + `adaptive_offset_noise_sigma{0,0.2,0.4}_f{1,2,3}_500.txt`.

---

## 6. Parameter justifications (put these in the paper — no magic numbers)

- **`verify_eps = 0.6 m` base tolerance:** ~obstacle-radius scale; matches position-match granularity.
- **`k_sigma = 4` (eps = 0.6 + 4σ):** two independent honest views of one obstacle differ by ~√2·σ;
  95% coverage needs ~2√2·σ ≈ 2.8σ; k=4 adds ~40% safety margin so honest noisy matches pass while
  open-space phantoms (meters off) still flag.
- **`alpha = 0.25` (EWMA decay):** with τ=0.4, a persistent liar is excluded in ~3–4 steps while an
  honest neighbour survives 1–2 noisy mismatches (grace period). Naive α=0.5 condemns in 2 steps (too
  hair-trigger under noise).
- **`tau = 0.4–0.5`:** sub-50% trust ⇒ exclusion (standard reputation-system threshold).
- **dropout 0.10 / sustain 5 (~33% blind):** realistic intermittent burst sensor failure; blind fraction
  = p·s/(1+p·s).
- **`temporal_bias_eps = 0.6 m` (§5.11):** the offset-vector-mean threshold; set at the *honest* mean-bias
  p95 (≈0.5–0.6 m at K=20 from the realistic-association probe) so honest neighbours rarely trip while the
  persistent camouflage bias (median >1 m) clears it. Stays TIGHT — temporal aggregation, not a widened
  band, is what separates the classes.
- **`temporal_min_k = 20` (§5.11):** minimum frames in a per-track bucket before a verdict; chosen from the
  probe's K-sweep (realistic-association AUC rises 0.79→0.90 as Kmin 1→20) and a self-test P/R sweep
  (min_k=10→20 lifts precision 0.45→0.78 by filtering transient mis-association spikes). Honest noise
  averages to zero by K=20 (p90 0.74→0.33); the phantom bias does not.

---

## 7. Limitations (the full honest list — disclose ALL)

1. **Idealized sensing in the clean experiments** (perfect ranging, no occlusion). *Being addressed* by
   the noise study (§5.6–5.8) and Option C (§8).
2. **Hand-coded trust, not learned.** The trust filter is an algorithmic consistency rule, not learned by
   the policy (we proved the learned gate is untrainable as drawn: env fusion is non-differentiable, no
   gradient, no discriminative single-frame input). Claim "a bio-inspired trust filter," NOT "the policy
   learned to distrust."
3. **Dijkstra goal-direction crutch:** `obs[2:4]` is a privileged GLOBAL shortest-path heading. It
   dampens attack severity (always pulls the drone back on route), so reported drops are a *lower bound*.
4. **Idealized 8 m comm radio** (perfect, instant, error-free within range).
5. **Perception-information limit under severe noise (characterised, not a confound):** `base` degrades
   92→70% as σ→0.6. We tested whether this was a navigation-OOD training artifact (Option C: 3.5M steps
   of noise domain-randomization fine-tuning) — it recovered only ~2.5pp (§5.10), so the degradation is a
   **genuine perception limit** (obstacle positions are fundamentally uncertain at high σ), independent of
   the security problem. The defense never makes it worse (no-harm ≈ base at every σ); it simply cannot
   recover navigation information that the sensor never provided. This caps high-noise recovery as a
   fundamental limit, not a fixable gap.
6. **Neighbor-level filtering (information loss):** the consistency filter operates at the **neighbor
   level**: if a neighbor broadcasts even ONE contradicted obstacle (e.g., a phantom mixed with real
   reports), the **entire neighbor is distrusted and excluded**, losing both fabricated AND correct
   obstacles. This is conservative (protects against mixed attacks) but incurs information loss. A more
   sophisticated approach (future work: §8 P6) would filter at the **obstacle level**, accepting good
   reports while rejecting only the contradicted ones. Impact: the reported recovery numbers assume this
   conservative strategy; obstacle-level filtering would likely improve recovery at the cost of
   complexity.
7. **Sim-only**, 10 drones, 2-D, circular obstacles.

---

## 8. Pending justifications & how to close them

| # | Gap | How to close | Cost | Priority |
|---|---|---|---|---|
| P1 | ~~Noise robustness of the *base* model (Limitation 5)~~ | **DONE (Option C, §5.10).** Fine-tuned under σ∈[0,0.6] for 3.5M steps; base recovered only ~2.5pp at σ=0.6 → high-noise degradation is a genuine perception limit, not OOD. Limitation 5 reframed as characterised limit. | — | **CLOSED** |
| P2 | "Is hardcoded enough or is learned trust needed?" | **ANSWERED: hardcoded is enough.** The hand-coded temporal rule (P4, §5.11) recovers the σ=0.6 camouflage limit (recall 0.21→0.78, +7.7 pp, no-harm flat). **Learned trust is NOT needed.** | — | **CLOSED** |
| P3 | Dijkstra crutch (Limitation 3) | Retrain with straight-line bearing instead of Dijkstra heading; re-measure. (Separate, larger effort) | weeks | LOW (disclose for now) |
| P4 | Temporal-hardcoded baseline (fair-baseline rigor) | **DONE (§5.11, WIN).** Offset-vector running-mean per (ego,neighbour,track); `eps=0.6, min_k=20`, composed with single-frame robust. σ=0.6 camo recall 0.21→0.78, recovery +1.4→+7.7 pp, no-harm flat (+0.2 pp), wall no regress. Precision 0.82 (residual = ultra-stealthy ≈ harmless camouflage). | — | **CLOSED** |
| P5 | Stealth/harm "boxed-in" claim under ideal sensing | Phantom-SIZE sweep (radius small → can hide but harmless) | ~hours | LOW |
| P6 | Obstacle-level filtering (vs neighbor-level, Limitation 6) | Instead of excluding entire neighbor if one obstacle contradicts, accept good reports and reject only the contradicted ones. Requires per-obstacle trust tracking. | ~2–3 days | LOW (disclose + defer) |

**Recommended order:** P1 (Option C) ✅ → P4 (temporal hardcoded) ✅ → P2 (learned vs limit) ✅ **all done →
write.** P3/P5/P6 are disclose-or-future-work unless aiming above mid-tier. The only remaining RA-L
blocker is **P3 (Dijkstra crutch, weeks of retrain)**; for MDPI *Drones* the arc is now complete + strong.
(Venue note: MDPI *Drones* superseded 2026-06-26 by the NO-APC constraint → current target Elsevier *RAS*, §10.)

### 8.1 Final-run checklist — **500 maps + density 0.27 + stage-2 base + RANDOMIZED attack + f∈{1,2,3}**
**Setup locked 2026-06-20.** The camera-ready runs differ from the §5.11 dev tables on five axes:
1. **Maps:** 150 → **500** (tight paired-bootstrap CIs).
2. **Density:** 0.25/0.20 → **0.27** (calibrated fairness ceiling; §4.1).
3. **Base model:** `noise_robust_ON_stage1_final` → **`noise_robust_ON_stage2_final`** (0.27 lock-in,
   1.5M steps, σ~U[0,0.6]; `train_noise_robust.py 2`). ✅ trained 2026-06-20.
4. **Attack:** FIXED (n_phantom=4, r=1.0) → **RANDOMIZED** — per-map n_phantom~U{3,4,5,6}, per-phantom
   radius from the real 42/40/18 mixture (`randomize_attack=True`, verified by `verify_randomized_attack.py`:
   n̄=4.54, radius bands 44/38/18 == real). Phantoms are now size-indistinguishable from real obstacles.
5. **Traitor sweep:** k=2 only → **f = 1, 2, 3** (30% literature ceiling per `Literature_Review_Template`),
   **EXTENDED 2026-07-19 to f = 4, 5, 6, 7** to back the "operates without an honest local majority" claim
   empirically (§5.11b) — f=5 is a 5:5 tie, f≥6 an honest minority; temporal recovery stays CI-significant
   throughout. The f=1–3 rows remain the literature-normal headline; f=4–7 is the majority-boundary stress test.

**Bootstrap-CI computation is IMPLEMENTED** (`Phase_CD/Noise_added/boot_ci.py`): `eval_temporal.py` and
`eval_adaptive_attack.py` print a "95% CONFIDENCE INTERVALS" block (paired bootstrap over maps, 2000
resamples, seed 12345) for every success cell, the recovery/no-harm diffs (paired), and detection P/R.

**One-command driver (training + the full f-sweep eval matrix, with Tee logging):**
```
powershell -ExecutionPolicy Bypass -File Phase_CD\Noise_added\run_full_027_pipeline.ps1          # train + eval
powershell -ExecutionPolicy Bypass -File Phase_CD\Noise_added\run_full_027_pipeline.ps1 -SkipTrain # eval only
```
Outputs → `Phase_CD\Noise_added\results_027\eval_f{1,2,3}_{wall,camouflage}_500.txt`.

| run | command (`python <script> <stage2-model> 500 <f> 10 <args>`) | status |
|---|---|---|
| §5.11 temporal — wall, f=1/2/3 | `eval_temporal.py … 500 {1,2,3} 10 wall` | ⏳ in pipeline |
| §5.11 temporal — camouflage, f=1/2/3 | `eval_temporal.py … 500 {1,2,3} 10 camouflage` | ⏳ in pipeline |
| adaptive — **stealth/harm bind** (FIXED radius) | `eval_adaptive_attack.py … 500 2 10 offset` | ⏳ separate (keeps fixed radius — bind axis) |
| adaptive — gap / jitter / duty (FIXED radius) | `eval_adaptive_attack.py … 500 2 10 {gap,jitter,duty}` | ⏳ separate |
| (optional) probe evidence | `probe_temporal_offset.py … 500 2 10 camouflage 0.6` (+`--assoc realistic`) | descriptive; 150 ample |

> **Note:** the adaptive `offset/gap/jitter/duty` sweeps deliberately keep the **fixed-radius** attack
> (`randomize_attack=False`) so the single swept axis (e.g. centre-offset) isn't confounded by random size —
> they are NOT in `run_full_027_pipeline.ps1`; run them separately when needed.

- **CI method (implemented in `boot_ci.py`):** paired bootstrap over the per-map success vectors
  (`rates[ci]`), resampling map indices jointly across conditions so the *same* maps are compared (paired);
  reports point estimate + [2.5, 97.5] percentiles. Detection P/R bootstrap over per-map TP/FP/FN vectors
  (`pr_ci`). Fixed seed (12345) → reproducible.
- Re-running at 500 will shift point estimates by ≤~1–2 pp (sampling noise); the *conclusions* (recall
  0.21→0.78, no-harm flat, the bind) are large enough that 150 already establishes them — 500 is for
  publication-grade tightness, not to re-decide any gate.
- For reference, the ideal-sensing tables already use higher counts (§5.4 = 200 maps, §5.5 = 500 maps), so
  500 for the noise/temporal tables keeps the paper internally consistent.

---

## 9. Paper structure (section-by-section)

**Working title:** *Trust-Aware Collaborative Perception for Byzantine-Resilient Drone-Swarm Navigation
under Sensor Failure.*

1. **Introduction** — swarms, sensor failure, the comm double-edge (resilience + attack surface),
   contributions (**5**): (i) comm-resilience quantification (53→94 under dropout); (ii) min-fusion
   Byzantine vulnerability + its dropout-independence; (iii) the naive consistency filter is *destructive*
   under sensor noise (worse than no defense); (iv) a noise-aware bio-inspired trust filter with graceful
   degradation; (v) **temporal trust** — a per-frame offset-vector aggregation that recovers the
   single-frame camouflage limit (recall 0.21→0.78) at ≈zero no-harm cost, with an adaptive-attacker
   stealth/harm-bind analysis showing the recovery is not gameable.
2. **Related work** — collaborative/cooperative perception; Byzantine-robust multi-robot systems &
   robust sensor fusion; trust/reputation; MARL navigation. **Use the cite list + differentiation table in
   §9.2** (must-cite: CAD/USENIX'24, CoDynTrust, MADE, Among Us, TruPercept, CONClave; 3D-TC2, ADoPT,
   PhyScout). Position as *application + characterization + the temporal mechanism*, not a new heavy
   algorithm. Lead with CAD's stated camouflage blind-spot as the gap we close.
3. **System & Methods** — §4 (env, M0, slot-fusion, attack, naive+robust trust, noise model) **+ §5.11
   temporal filter** (offset-vector running mean; zero-mean honest vs persistent-bias liar; composed OR
   with the single-frame check; knobs `temporal_bias_eps=0.6`, `temporal_min_k=20`, justified in §6).
4. **Experimental Setup** — metrics (honest-drone success, detection P/R, paired bootstrap CI), regimes
   (σ∈{0,0.2,0.4,0.6} × {wall, camouflage}), seeds, reproducibility (cite the clean repo + the temporal
   probe/eval scripts in §11).
5. **Results** — §5: 5.2 anchor → 5.3 vulnerability → 5.4/5.5 ideal defense → 5.6 naive collapse →
   5.7/5.8 robust recovery → 5.9 ceiling reading → **5.11 temporal trust (the WIN)** → **adaptive-attacker
   stealth/harm bind** (the new experiment). Money figures: **5.2** (comm-resilience), **5.6-vs-5.7**
   (naive-destructive vs robust-graceful), and **5.11** (temporal recall 0.21→0.78 + the offset-vector
   honest-vs-liar distribution plot from `probe_temporal_offset.py`).
6. **Discussion & Limitations** — §7 honestly; the stealth/harm tradeoff (now *demonstrated* via the
   adaptive attacker, not just asserted); the navigation vs security limits (§5.10 stands, §5.8 recovered);
   the precision-0.82 caveat reconciled by the flat no-harm column.
7. **Conclusion & Future work** — Dijkstra-free retrain (the one RA-L blocker), obstacle-level filtering
   (P6), real-robot, noisy comm, learned trust (now shown *unnecessary* for this threat).

**Lead the abstract & contributions with §5.2 (53→94)** as the cleanest anchor; **§5.11 (temporal trust) is
the methodological standout** that lifts the paper above a pure characterization. Both carry it even if a
reviewer is lukewarm on the (classic-family) base defense.

### 9.1 One-paragraph abstract draft (for reuse)
*Drone swarms can survive sensor dropout by sharing perception over a radio, but that same channel is an
attack surface: a single Byzantine drone broadcasting fabricated obstacles overrides honest LiDAR through
min-fusion, independent of dropout. A consistency-trust filter neutralizes this under ideal sensing, but we
show it becomes destructive under realistic ranging noise, and that even a noise-aware robust variant fails
against a camouflage attack at high noise (recall 0.21) because a lie hidden inside the sensor-noise band is
not contradictable on any single frame. We introduce a temporal-trust rule that aggregates the per-frame
offset between a neighbour's report and the verifier's own view: honest disagreement is zero-mean and
cancels, while a persistent fabrication does not — recovering recall to 0.78 and success by +7.7 pp at zero
measurable cost to honest swarms. We further show an adaptive, filter-aware attacker cannot escape this: to
evade temporal detection the phantom must collapse onto a real obstacle, where it blocks no new space — a
stealth/harm bind. Experiments use 10-drone CTDE-MAPPO navigation with paired-bootstrap statistics over
150-map suites.*

### 9.2 Related work — cite list + differentiation (prior-art audit, 2026-06-19)
> A literature scan found a DENSE field in collaborative-perception security — **almost all autonomous-vehicle
> (CAV), deep-feature fusion, single-frame, consensus/majority-based**. **No paper does our exact thing**
> (cross-agent temporal offset-vector trust for *camouflage* false-obstacle attacks under sensor noise in a
> *drone-swarm MARL* navigator). **The real submission risk is omitting these citations** — reviewers in this
> area know them; the Related Work MUST cite and differentiate group A (trust/defense) and group B (temporal
> spoofing detection). Frame our novelty as the *combination + two characterizations* (naive-destructive
> under noise; the stealth/harm bind), NOT as "trust for collab perception" or "temporal consistency" alone.

**Group A — trust / Byzantine defense in cooperative perception (CAV unless noted):**

| Work | What it does | How OURS differs (one-line rebuttal) |
|---|---|---|
| **CAD** — Zhang et al., *On Data Fabrication in Collaborative Vehicular Perception*, USENIX Sec'24 (arXiv 2309.12955) — **the strongest competitor** | Cross-VEHICLE **occupancy-map consensus** (free/occupied/unknown), **single-frame** (motion only for sync); detects 91.5% data-fabrication attacks. **Explicitly states it needs ≥1 benign CAV observing the attacked region, and does NOT cover camouflaged objects.** | We use the verifier's **own** sensed view vs a neighbour (not a benign-majority occupancy vote) → works at **k=2 of 10** with no benign observer of the region; we **target camouflage** (CAD's stated blind spot) via **temporal** offset-bias; we **model ranging noise** (where single-frame consistency breaks). Cite CAD as the SOTA single-frame consistency defense whose camouflage blind-spot **motivates** our temporal method. |
| **CoDynTrust** (arXiv 2502.08169) | Dynamic **feature**-trust modulus from aleatoric/epistemic **uncertainty**; targets **temporal asynchrony** (delays/clock), **single-frame**, deep-feature fusion. | We target an **adversarial Byzantine** liar (not benign async); **explicit object-list** fusion (not deep features); **temporal accumulation** of a disagreement vector (not per-frame uncertainty). |
| **MADE**; **Among Us** (consensus); **TruPercept**; **CONClave** (authenticated consensus + trust scoring) | Malicious-agent detection / robust collab perception via **consensus / majority vote / authentication**, mostly single-frame, CAV. | We need **no majority consensus** (k=2 of 10) and **no PKI/authentication**; the discriminator is a physics-grounded **temporal zero-mean-vs-bias** test on the ego's own disagreement, robust under noise. |

**Group B — temporal consistency to detect spoofing (the closest MECHANISM family — differentiate hard):**

| Work | What it does | How OURS differs |
|---|---|---|
| **3D-TC2** (arXiv 2106.07833); **ADoPT** (arXiv 2310.14504); **PhyScout** (CCS'24) | **Own-sensor** LiDAR spoof detection on a **single AV**, using a **motion/physical invariant** (a real object moves consistently frame-to-frame) or point-level temporal alignment. ~98% on spoofed objects. | Ours is **cross-agent**: the statistic is the **temporal mean of the disagreement vector between a neighbour's broadcast and the ego's own noisy view** (zero-mean honest noise vs persistent lie-bias) — a *communication-trust* test, not an own-sensor motion-consistency test. Different threat (Byzantine broadcast, not own-LiDAR spoof) and different invariant. |

**Honest novelty statement for the paper:** the *statistic* (averaging cancels zero-mean noise; persistent
bias survives) is **elementary** — the contribution is its **application** as a cross-agent communication-trust
discriminator for camouflage attacks under noise, the **demonstrated stealth/harm bind** showing an adaptive
attacker cannot evade-and-harm, and the **"naive consistency filter is worse than no defense under noise"**
result. This is a solid MDPI *Drones* contribution; it is deliberately **not** pitched as a top-venue
algorithmic novelty (consistent with §10). (Venue note: MDPI *Drones* superseded 2026-06-26 → now Elsevier
*RAS*, §10; the contribution-strength point is venue-agnostic.)

---

## 10. Target venue + concrete reasoning (Option A = highest acceptance odds)

> No venue is a guarantee. Below is the honest probability ordering for *sound, complete, honestly-framed*
> work like this.

> **⚠ CONSTRAINT UPDATE 2026-06-26: NO APC (Prof's decision — no publication fees).** This rules out ALL
> MDPI journals (mandatory APC; *Drones* = CHF 2600) and IEEE Access (~$2k). New primary = hybrid Elsevier
> journals under the **subscription track (free to publish**; paper is paywalled, not OA — acceptable).

**Primary targets under NO-APC constraint (verified 2026-06-26 via web):**
| Venue | Indexing / IF | Cost | Why it fits |
|---|---|---|---|
| **Robotics and Autonomous Systems** (Elsevier) — **PRIMARY** | SCIE, **IF 5.2, Q1** | **free** (subscription track) | MARL-native audience; multi-robot autonomy + learning; sim-only routine; equal IF to Drones at zero cost. Slower review (~3–5 mo). |
| **Aerospace Science and Technology** (Elsevier) — ambitious backup | SCIE, **IF 6.4, Q1** | **free** (subscription track) | Publishes UAV-swarm coordination & fault-tolerant cooperative navigation; risk: aerospace reviewers may demand 3-D vehicle dynamics. |
| *Swarm Intelligence* (Springer) — niche fallback | SCIE, IF ~2–3 (unverified) | free (subscription track) | Perfect topical niche (swarm + trust); lower IF, slow. |

**RAS timeline + framing (verified 2026-06-26):** desk check days–2 wks · first decision ~3–5 mo ·
realistic submission→published **~6–9 mo** · ₹0 under subscription track. RAS scope names *multi-robot
systems, sensor data integration, learning for autonomous systems, decision-making* — all hit. RAS does
NOT name "security" → **frame resilience-first** ("resilient collaborative perception for multi-robot
navigation"; Byzantine agents = hardest fault model), which is also the civilian framing we want.
**Scoop protection: post the arXiv preprint the same day we submit** (Elsevier permits; timestamps priority
through the long review).

**Fresh novelty sweep 2026-06-26 (nothing pre-empts; three NEW must-cites):**
1. **PRBI "All Vehicles Can Lie" (CVPR 2026, arXiv 2603.08498)** — closest: temporal frame-consistency vs
   lying vehicles in V2X CP. Differentiate: detection-AP/feature-level/vehicles vs our closed-loop MARL
   *navigation*, no noise-vs-lie separation (our zero-mean/persistent-bias mechanism), no camouflage-in-noise
   attack, no adaptive attacker/bind.
2. **TrustFlip/TrustReflect (arXiv 2605.22122)** — attacks consistency-based trust to make it *exclude honest
   agents* (87.7%). Cite as the vulnerability class our measured **no-harm ≈ 0** directly addresses (timely!).
3. **Local-conformity evolutionary game, UAV Byzantine (arXiv 2606.21206)** — Byzantine on consensus/strategy,
   game-theoretic; complementary, related-work cite, zero overlap.
Unique to us (verified again): false-obstacle Byzantine inside closed-loop MARL navigation · camouflage
hiding inside the sensor-noise band · temporal offset-bias filter (zero-mean vs persistent) · adaptive
attacker stealth/harm bind · measured no-harm.

### 10.1 RAS submission requirements — VERIFIED from the official Guide for Authors PDF (2026-07-08,
`Phase_CD/Papers/RAS_guide_for_authors.pdf`, 24 pp; page refs in brackets)
- **NO "Your Paper Your Way"** — assumption was WRONG. Editable source required: “.tex for LaTeX… **A PDF is
  not an acceptable source file**” [p10]. Double-column only permitted for LaTeX. Use Elsevier's LaTeX
  template (elsarticle) from day one [p10]. The system builds the review PDF from our sources [p22].
- **Highlights: REQUIRED** — 3–5 bullets, ≤85 chars incl. spaces, separate editable file with "highlights"
  in the filename [p11–12].
- **Abstract ≤250 words**, standalone, avoid references [p11]. **Keywords: 1–7**, avoid multi-word/"and"/"of" [p11].
- **Title page**: title (no abbreviations), authors + affiliations (full postal addr + emails), corresponding
  author designated [p11].
- **Declarations (all mandatory):** competing interests via Elsevier declarations tool, uploaded as .doc/.docx
  [pasted §]; **CRediT** author statement [p17]; funding sources.
- **⚠ Generative-AI declaration REQUIRED [p7]:** AI use in manuscript preparation MUST be declared in a
  section before the references, exact template: *“During the preparation of this work the author(s) used
  [TOOL] in order to [REASON]. After using this tool/service, the author(s) reviewed and edited the content
  as needed and take(s) full responsibility for the content of the published article.”* → We will declare
  Claude (Anthropic) assistance in drafting/editing. Authors bear full responsibility; AI cannot be an author.
- **Vitae REQUIRED**: ≤100-word bio + passport-type photo per author, editable format [pasted §].
- **Research data: Option C applies [p15] — REQUIRED** to deposit research data (incl. code/models) in a
  repository AND cite/link it in the article, or state why not. → Plan: public GitHub repo + Zenodo DOI
  (code, eval scripts, results_027 logs, model checkpoints); cite with [dataset]/[software] format [p20].
- **Preprints allowed** — “will not count as prior publication” [p7]; free SSRN option at submission; arXiv
  fine under Elsevier sharing policy. (Scoop protection confirmed in their own words.)
- **Structure**: numbered sections 1.1/1.1.1; abstract outside numbering; acknowledgements in a separate
  section directly before references [p17]; appendices A/B with Eq. (A.1) numbering [pasted §].
- **NO page/word limit** stated anywhere for regular papers; **NO graphical abstract** requirement (section
  absent from the guide).
- **No mandatory cover letter / suggested reviewers** in the guide [p22] (Editorial Manager may still offer
  fields at submission; prepare a short cover letter anyway — good practice).
- Checklist [p22]: corresponding author w/ full contact; ALL files uploaded incl. captions; spelling checked;
  every reference cited both ways; copyright permission for reused material.

**Superseded (APC-blocked) ranking kept for reference:**
| Venue | Indexing / IF | Why it fit |
|---|---|---|
| MDPI *Drones* | SCIE, IF 5.2 (2025), JCR Q2 (RS) / CiteScore Q1 (Aero) | Exact scope — blocked by CHF 2600 APC |
| MDPI *Sensors* | SCIE, IF ≈ 3.4 | Blocked by APC |
| IEEE Access | SCIE, IF ≈ 3.4 | Blocked by APC (~$2k) |

**MDPI *Drones* — VERIFIED from journal site 2026-06-26 (primary source, pasted by Srinivasa):**
- IF **5.2 (2025)**, 5-yr 5.3 · JCR **Q2** (Remote Sensing) · CiteScore **Q1** (Aerospace Eng.) · SCIE ✓
- Median **first decision ~21.1 days**; acceptance→publication 2.9 days (H1-2026 medians). APC CHF 2600.
- Scope fit is *explicit*: their "Development" topic list names **security systems, autonomy, navigation, AI,
  machine learning, mission planning** (+ sensor fusion under "Design") — the paper hits all of them.
- Special requirement: must directly address unmanned platforms (we do, trivially).
- **Dual Use Policy**: keep the paper's framing strictly civilian (sensor faults + Byzantine faults in
  cooperative perception) — accurate anyway, and avoids dual-use review friction.

**Why the acceptance odds are genuinely high here (the "practical proof"):**
1. **Completeness** — full arc (baseline → resilience → vulnerability → defense → realistic stress),
   exactly what these journals reward.
2. **Statistical rigor** — paired bootstrap 95% CIs, 200–500-map runs, parallelized & reproducible.
3. **A non-trivial finding beyond "we built a defense"** — *the naive filter is worse than no defense
   under noise*, and *the vulnerability is dropout-independent (min-fusion)*. These are quotable.
4. **Honest limitations** — reviewers forgive disclosed limits; they punish hidden ones.
5. **Clear anchor result** (53→94) that is large and clean.

**Stretch (NOT yet):** IEEE RA-L / ICRA / IROS — would reject as-is on *novelty* (consistency-based
Byzantine filtering is classic) + *idealization*. Option C (§5.10) and now **temporal trust (§5.11)** add a
genuinely interesting result (a single-frame detection limit *recovered* by temporal offset-bias
aggregation, with a clean zero-mean-vs-persistent-bias mechanism). The **one remaining RA-L blocker is the
Dijkstra crutch** (P3, remove/justify + retrain) — learned trust (P2) is no longer a blocker since the
hand-coded temporal rule suffices.

**Out of reach:** AAMAS / CoRL / NeurIPS (insufficient algorithmic novelty).

**Decision:** target **MDPI *Drones*** first (best scope fit + high odds). With Option C + temporal trust
complete it is a *safe* accept there, now with a **stronger defense section** (§5.11 is the standout
result). RA-L is viable only after the Dijkstra-free retrain (P3).

> **⚠ SUPERSEDED 2026-06-26:** the MDPI *Drones* decision above was overturned by the NO-APC constraint
> (see the §10 CONSTRAINT UPDATE). **Current primary target = Elsevier *Robotics and Autonomous Systems***
> (free subscription track; backup = Elsevier *Aerospace Science and Technology*). The Drones decision is
> retained here as the record of the prior choice and why it changed.

---

## 11. File index (for reproduction)

| Purpose | File |
|---|---|
| Clean Phase-3 env | `Collab_Perception/env_collab_perception.py` |
| Byzantine attack + trust env | `Collab_Perception/env_byzantine_trust.py` |
| Adaptive/camouflage attack env | `Collab_Perception/env_byzantine_adaptive.py` |
| Noisy-sensing env (+ robust filter knob) | `Noise_added/env_noisy_byzantine.py` |
| Phase-3 ON/OFF eval | `Collab_Perception/eval_slot_fusion_zero_shot.py` |
| Dropout sweep | `Collab_Perception/eval_dropout_sweep.py` |
| Attack potency probe (k & dropout) | `Collab_Perception/probe_attack_potency.py` |
| Parallel matrix / attackcmp / gapsweep | `Collab_Perception/eval_parallel.py` |
| Noise sweep (naive) | `Noise_added/eval_noise_sweep.py` |
| Noise sweep (naive vs robust, wall/camo) | `Noise_added/eval_noise_robust.py` |
| Temporal-trust filter (env knobs `temporal_*`) | `Noise_added/env_noisy_byzantine.py` (`_temporal_update`) |
| Temporal-trust probe (oracle + realistic assoc) | `Noise_added/probe_temporal_offset.py` |
| Temporal-trust self-test (5-map sanity) | `Noise_added/selftest_temporal.py` |
| Temporal-trust eval (§5.11, wall/camo; `randomize_attack`, f-arg) | `Noise_added/eval_temporal.py` |
| Randomized-attack verifier (n_phantom + radius mixture) | `Noise_added/verify_randomized_attack.py` |
| Real-obstacle stats measurement (count/radius/area) | `Phase_CD/measure_env_stats.py` |
| Full 0.27 pipeline (train stage2 + f∈{1,2,3} 500-map evals) | `Noise_added/run_full_027_pipeline.{ps1,bat}` |
| Temporal-trust runbook (cold-start handoff) | `Noise_added/TEMPORAL_TRUST_RUNBOOK.md` |
| Parameter justification (Phase_CD superset) | `PARAMETER_JUSTIFICATION_PHASE_CD.md` |
| M0 provenance / transfer-learning lineage | `M0_PROVENANCE_AND_LINEAGE.md` |
| Models | `models/apex_ultra_glide_v14_comm8_lidar_final.zip` (M0); `raster_slot_fusion_{ON,OFF}_stage2_final.zip`; `noise_robust_ON_stage1_final.zip` (Option C base for the §5.7–5.11 **dev** tables); **`noise_robust_ON_stage2_final.zip` (0.27 lock-in — base for ALL camera-ready f∈{1,2,3} runs)** |

**Verification:** the parallel runners reproduce the serial numbers (same seed formula + deterministic
predict) — verified: parallel matrix matched serial within <0.2 pp.

---

## 12. Decision log / open questions

- [x] Comm is load-bearing under dropout (53→94). **Settled (5.2).**
- [x] Attack vulnerability is the min-fusion, not the blind window. **Settled (5.3).**
- [x] Naive filter collapses under noise; robust filter recovers. **Settled (5.6–5.8).**
- [x] **Does a noise-trained base + robust filter close the high-noise camouflage gap?** → **NO (Option C, §5.10).**
  Noise training recovered only ~2.5pp at σ=0.6 → high-noise ceiling is a perception limit, not OOD.
  Robust filter stays safe (precision 0.93–1.00, no-harm ≈ base) but recall→0.21 at σ=0.6+camo = the
  characterised fundamental limit. **P1 closed.**
- [x] **Is learned (temporal) trust needed, or is a temporal-hardcoded rule enough?** → **Hardcoded is
  enough (§5.11, WIN).** Offset-vector temporal rule recovers σ=0.6 camo recall 0.21→0.78 (+7.7 pp),
  no-harm flat. Learned trust (P2) **not needed**. **P4 + P2 closed.**
- [ ] Dijkstra-free retrain — deferred (P3), disclose for now. **Sole remaining RA-L blocker.**

**Next action:** Option C (§5.10) AND temporal trust (§5.11) are DONE; the ledger is updated through §5.11
and §6–§8/§10/§12 reflect the WIN. The results arc is complete, self-consistent, and now has a standout
defense result. Begin **drafting the paper** (§9 structure) targeting Elsevier *RAS* (was MDPI *Drones* until
the NO-APC constraint 2026-06-26, §10) — §5.11 is the money section alongside §5.2 (comm-resilience). RA-L only
after the Dijkstra-free retrain (P3).
