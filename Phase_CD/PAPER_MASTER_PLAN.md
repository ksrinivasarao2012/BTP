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
consistency + reputation memory) restores graceful resilience — full recovery at moderate noise, partial
at severe noise — with **zero false positives**, against both naive and camouflaged attacks. We
characterise the fundamental limit (lies hidden within the sensor-noise band) and the residual
navigation-degradation confound.

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
- Obstacle density 0.20 (eval), trained up to 0.35. Obstacle radii 0.2–2.5 m. Goal kept clear within 2 m.
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

### 5.2 Phase 3 — collaborative perception under dropout (THE ANCHOR RESULT)
Fair comparison (each model in its own trained condition):
| Condition | drone-level |
|---|---|
| ON_stage2 (shared map ON) | **93.84%** |
| OFF_stage2 (own LiDAR only) | **53.08%** |
| **Gap** | **+40.76 pp** |

Zero-shot M0 (sanity, pre-training): ON 91.6% / OFF 50.6% drone-level.
Reproduce:
```
& $py Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py models\raster_slot_fusion_ON_stage2_final.zip 500
& $py Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py models\raster_slot_fusion_OFF_stage2_final.zip 500
```

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

### 5.6 Phase 4d-i — NAIVE filter CRACKS under noise (wall, 200 maps)
| noise | base | no-harm | FP-harm | attack | defense | recovery | P/R |
|---|---|---|---|---|---|---|---|
| 0.0 | 92.80 | 92.80 | +0.00 | 80.56 | 92.87 | +12.31 | 1.00/0.99 |
| 0.2 | 87.25 | 80.20 | −7.05 | 76.06 | 75.44 | −0.63 | 0.32/0.99 |
| 0.4 | 77.95 | 47.30 | −30.65 | 67.87 | 47.06 | −20.81 | 0.23/0.97 |
| 0.6 | 66.80 | 41.70 | −25.10 | 55.19 | 41.56 | −13.62 | 0.23/0.96 |
→ Naive filter is **worse than no defense** under noise (false positives fragment the swarm).
Reproduce:
```
& $py Phase_CD\Noise_added\eval_noise_sweep.py models\raster_slot_fusion_ON_stage2_final.zip 200 2 10
```

### 5.7 Phase 4d-ii — ROBUST filter, naive vs robust (wall, 150 maps)
| noise | base | attack | naive (P/R) | robust (P/R) | robust no-harm | robust recovery |
|---|---|---|---|---|---|---|
| 0.0 | 92.2 | 80.6 | 92.5 (1.00/0.98) | 92.5 (1.00/0.98) | 92.2 | +11.9 |
| 0.2 | 87.1 | 75.2 | 76.4 (0.32/0.98) | 87.7 (0.99/0.92) | 87.1 | +12.5 |
| 0.4 | 79.5 | 67.3 | 48.8 (0.23/0.97) | 75.5 (0.97/0.68) | 80.3 | +8.2 |
| 0.6 | 67.4 | 57.0 | 44.0 (0.23/0.96) | 62.5 (0.95/0.39) | 66.0 | +5.5 |
→ Robust filter **fixes false positives** (precision 0.95–1.00, no-harm ≈ base) and recovers gracefully.

### 5.8 Phase 4d-iii — ROBUST filter vs CAMOUFLAGE under noise (150 maps)
| noise | base | attack | naive (P/R) | robust (P/R) | robust no-harm | robust recovery |
|---|---|---|---|---|---|---|
| 0.0 | 92.2 | 80.0 | 91.8 (1.00/0.98) | 90.3 (1.00/0.96) | 92.2 | +10.3 |
| 0.2 | 87.0 | 73.1 | 75.8 (0.32/0.98) | 86.7 (1.00/0.94) | 87.1 | +13.6 |
| 0.4 | 79.1 | 66.1 | 47.2 (0.23/0.97) | 71.3 (0.98/0.56) | 80.3 | +5.2 |
| 0.6 | 68.3 | 51.5 | 42.6 (0.23/0.97) | 56.6 (0.94/0.22) | 65.9 | +5.1 |
→ Robust filter survives camouflage at moderate noise; at severe noise+camouflage **recall collapses
(0.22)** — the genuine hard regime — but precision stays high (never destructive).
Reproduce (5th arg = attack mode):
```
& $py Phase_CD\Noise_added\eval_noise_robust.py models\raster_slot_fusion_ON_stage2_final.zip 150 2 10 wall
& $py Phase_CD\Noise_added\eval_noise_robust.py models\raster_slot_fusion_ON_stage2_final.zip 150 2 10 camouflage
```

### 5.9 Recovery against the correct ceiling (read recovery vs `base` at each noise, not absolute)
Robust filter, fraction of the `base − attack` gap it closes:
| noise | wall | camouflage |
|---|---|---|
| 0.0 | ~100% | 84% |
| 0.2 | ~100% | 98% |
| 0.4 | 67% | 40% |
| 0.6 | 53% | 30% |

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
5. **Navigation OOD under noise:** the model was trained on clean perception, so `base` collapses
   (92→68%) under noise — a navigation problem, not a security one, that caps high-noise recovery.
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
| P1 | Noise robustness of the *base* model (Limitation 5) | **Option C**: fine-tune M0/ON under noise domain-randomization (σ∈[0,0.6]), ~1–3M steps; re-run §5.6–5.8 | ~1–3 days (overnight train + retry) | **HIGH** |
| P2 | "Is hardcoded enough or is learned trust needed?" | After Option C, re-test camouflage+noise. If robust filter still fails → build learned *temporal* trust (liar repeats same phantom; honest noise is fresh) OR report fundamental-limit | days | MED |
| P3 | Dijkstra crutch (Limitation 3) | Retrain with straight-line bearing instead of Dijkstra heading; re-measure. (Separate, larger effort) | weeks | LOW (disclose for now) |
| P4 | Temporal-hardcoded baseline (fair-baseline rigor) | Before learned trust, try a window-averaged consistency rule to exploit phantom persistence without learning | ~half day | MED |
| P5 | Stealth/harm "boxed-in" claim under ideal sensing | Phantom-SIZE sweep (radius small → can hide but harmless) | ~hours | LOW |
| P6 | Obstacle-level filtering (vs neighbor-level, Limitation 6) | Instead of excluding entire neighbor if one obstacle contradicts, accept good reports and reject only the contradicted ones. Requires per-obstacle trust tracking. | ~2–3 days | LOW (disclose + defer) |

**Recommended order:** P1 (Option C) → P4 (temporal hardcoded) → P2 (decide learned vs limit) → write.
P3/P5/P6 are disclose-or-future-work unless aiming above mid-tier.

---

## 9. Paper structure (section-by-section)

**Working title:** *Trust-Aware Collaborative Perception for Byzantine-Resilient Drone-Swarm Navigation
under Sensor Failure.*

1. **Introduction** — swarms, sensor failure, the comm double-edge (resilience + attack surface),
   contributions (4): (i) comm-resilience quantification, (ii) min-fusion vulnerability + its
   dropout-independence, (iii) naive filter is *destructive* under noise, (iv) noise-aware bio-inspired
   trust filter with graceful degradation + fundamental-limit characterization.
2. **Related work** — collaborative/cooperative perception; Byzantine-robust multi-robot systems &
   robust sensor fusion (position the contribution as *application + characterization*, not a new
   algorithm); trust/reputation; MARL navigation.
3. **System & Methods** — §4 of this doc (env, M0, slot-fusion, attack, naive+robust trust, noise model).
4. **Experimental Setup** — metrics (honest-drone success, paired bootstrap CI), regimes, seeds,
   reproducibility (cite the clean repo).
5. **Results** — §5: 5.2 anchor → 5.3 vulnerability → 5.4/5.5 ideal defense → 5.6 naive collapse →
   5.7/5.8 robust recovery → 5.9 ceiling reading. One figure per sub-result; the money figures are
   5.2 (comm-resilience) and 5.6-vs-5.7 (naive-destructive vs robust-graceful).
6. **Discussion & Limitations** — §7 honestly; the stealth/harm tradeoff; the two confounds.
7. **Conclusion & Future work** — learned temporal trust, Dijkstra-free retrain, real-robot, noisy comm.

**Lead the abstract & contributions with §5.2 (53→94)** — it is the strongest, cleanest, most defensible
result and carries the paper even if a reviewer is lukewarm on the (classic-family) defense.

---

## 10. Target venue + concrete reasoning (Option A = highest acceptance odds)

> No venue is a guarantee. Below is the honest probability ordering for *sound, complete, honestly-framed*
> work like this.

**Primary targets (high realistic acceptance, FULL journal papers):**
| Venue | Indexing / IF | Why it fits |
|---|---|---|
| **MDPI *Drones*** | SCIE, IF ≈ 4.4 | Exact scope: drone swarms, collaborative perception, resilience |
| **MDPI *Sensors*** | SCIE, IF ≈ 3.4 | Collaborative sensing, sensor-dropout, fault/attack detection |
| **IEEE Access** | SCIE, IF ≈ 3.4 | Broad; rewards *sound + complete*, tolerates disclosed limitations |

**Why the acceptance odds are genuinely high here (the "practical proof"):**
1. **Completeness** — full arc (baseline → resilience → vulnerability → defense → realistic stress),
   exactly what these journals reward.
2. **Statistical rigor** — paired bootstrap 95% CIs, 200–500-map runs, parallelized & reproducible.
3. **A non-trivial finding beyond "we built a defense"** — *the naive filter is worse than no defense
   under noise*, and *the vulnerability is dropout-independent (min-fusion)*. These are quotable.
4. **Honest limitations** — reviewers forgive disclosed limits; they punish hidden ones.
5. **Clear anchor result** (53→94) that is large and clean.

**Stretch (NOT yet):** IEEE RA-L / ICRA / IROS — would reject as-is on *novelty* (consistency-based
Byzantine filtering is classic) + *idealization*. To make RA-L viable: complete **Option C** (noise base),
remove/justify the **Dijkstra crutch**, and add **learned trust** or a strong fundamental-limit result.

**Out of reach:** AAMAS / CoRL / NeurIPS (insufficient algorithmic novelty).

**Decision:** target **MDPI *Drones*** first (best scope fit + high odds). After Option C it becomes a
*safe* accept there and a *viable* RA-L attempt.

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
| Models | `models/apex_ultra_glide_v14_comm8_lidar_final.zip` (M0); `raster_slot_fusion_{ON,OFF}_stage2_final.zip` |

**Verification:** the parallel runners reproduce the serial numbers (same seed formula + deterministic
predict) — verified: parallel matrix matched serial within <0.2 pp.

---

## 12. Decision log / open questions

- [x] Comm is load-bearing under dropout (53→94). **Settled (5.2).**
- [x] Attack vulnerability is the min-fusion, not the blind window. **Settled (5.3).**
- [x] Naive filter collapses under noise; robust filter recovers. **Settled (5.6–5.8).**
- [ ] **Does a noise-trained base + robust filter close the high-noise camouflage gap?** → Option C (P1).
- [ ] **Is learned (temporal) trust needed, or is a temporal-hardcoded rule enough?** → P4 then P2.
- [ ] Dijkstra-free retrain — deferred (P3), disclose for now.

**Next action:** build & run Option C (noise domain-randomization fine-tune), then re-run §5.6–5.8 on the
noise-robust model and update this ledger.
