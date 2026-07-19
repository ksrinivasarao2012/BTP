# Parameter Justification — Phase_CD paper (Byzantine collab-perception + temporal trust)

> **Created:** 2026-06-19 · **Scope:** the *actual* experiment configuration used in the temporal-trust
> paper (Phase_CD line, target = Elsevier *Robotics and Autonomous Systems*; MDPI *Drones* ruled out
> 2026-06-26 by the NO-APC constraint). This consolidates the three existing justification sources and —
> critically — **flags every parameter still un-justified and every value that DIFFERS from the older docs.**
>
> **Existing sources (reuse, don't duplicate):**
> - `PARAMETER_JUSTIFICATION.md` (repo root) — physical/sensor params **with real citations** (RPLIDAR,
>   UWB, MAPPO, swarm-RL). ⚠️ written for the **v14 base env** (12 m LiDAR, 8 m comm) — see reconciliations.
> - `FINAL_PARAMETER.md` (repo root) — **density calibration** (10k-map BFS sweep; 0.27 = fairness ceiling).
> - `PAPER_MASTER_PLAN.md §6` — **defense / dropout / temporal** params (verify_eps, k_sigma, alpha, tau,
>   dropout, temporal_bias_eps, temporal_min_k).
>
> **Categories:** **A** = realism-anchored (needs a citation) · **B** = design/convention (state rationale)
> · **C** = empirically calibrated (cite our own result). **Status:** ✅ justified (where) · ⚠️ REMAINING.

---

## 0. ⚠️ CONFIG RECONCILIATIONS — resolve these FIRST (the experiments differ from the old docs)

The temporal-trust experiments call `_build_env(...)` (in `eval_temporal.py` / `eval_adaptive_attack.py` /
`probe_temporal_offset.py`) with values that **differ from `PARAMETER_JUSTIFICATION.md`**. The paper MUST
state the *actual* values below, not the base-env defaults.

| Parameter | Old doc (v14 base) | **Actual Phase_CD experiment** | Action |
|---|---|---|---|
| LiDAR effective range | 12.0 m | **8.0 m** (`lidar_range=8.0`) | Re-justify at 8 m (still ≤ RPLIDAR A1's 12 m capability → cite as "8 m operating range on a 12 m-class scanner", or cite a shorter-range UWB/ToF unit). |
| Communication range | 8.0 m | **10.0 m** (`communication_range=10.0`) | Re-justify at 10 m (≈50% of the 20 m arena). The "8 m gated comm / M0" phrasing is WRONG for this line. |
| LiDAR encoding | 192 rays → 48-d | **48-d = 16 sectors × {min,mean,std}** (`_cast48`) | Consistent — state as "48-d sector descriptor". Confirm underlying ray count if cited. |
| Obstacle density | 0.20–0.26 | **0.27** (`target_density=0.27`, set 2026-06-19) | ✅ justified by `FINAL_PARAMETER.md` (0.27 = last ≥95%-solvable). |
| Obs dimension | — | **650-d = 130 local + 520 global** | ✅ CTDE, cite MAPPO (PARAMETER_JUSTIFICATION §5). |

> **Why this matters:** a reviewer who reads "8 m comm" in one place and sees `communication_range=10.0` in
> the code will reject for inconsistency. Pick the real values (8 m LiDAR, 10 m comm, 0.27 density) and make
> every doc + the paper agree.

---

## 1. Already justified — reuse these (pointers, do not rewrite)

| Group | Params | Where justified | Cat |
|---|---|---|---|
| Physical platform | drone radius 0.15 m, safety 0.19 m, v_max 2.0 m/s, dt 0.1 s (10 Hz), episode 1200 steps, field 20×20 | `PARAMETER_JUSTIFICATION.md` A/B | A+B |
| Sensor class | LiDAR (RPLIDAR A1 class), 48-d sector encoding | `PARAMETER_JUSTIFICATION.md` §1–2 | A+B |
| Algorithm/CTDE | PPO/MAPPO, 650-d split obs | `PARAMETER_JUSTIFICATION.md` §5 | A |
| Swarm size | 10 drones (enables 10–40% traitor sweep) | `PARAMETER_JUSTIFICATION.md` B | B |
| **Density 0.27** | fairness ceiling, 96.78% solvable; agent clears 0.30 @ 93.6% | `FINAL_PARAMETER.md` §3–4 | C |
| Dropout | `lidar_dropout=0.10`, `dropout_sustain=5` (~33% blind) | `PAPER_MASTER_PLAN §6` | B |
| Single-frame defense | `verify_eps=0.6`, `k_sigma=4`, `alpha=0.25`, `tau=0.4` | `PAPER_MASTER_PLAN §6` | B+C |
| Temporal defense | `temporal_bias_eps=0.6`, `temporal_min_k=20` | `PAPER_MASTER_PLAN §6 + §5.11` | C |

---

## 2. ⚠️ REMAINING parameters to justify (the actual gaps — this is the work)

### 2.1 Sensing/comm ranges (8 m LiDAR, 10 m comm) — ✅ **WRITTEN 2026-06-20**
**Values:** LiDAR range **8.0 m**, communication range **10.0 m**, on a 20×20 m arena. Three pillars:

1. **Partial observability (why 8 m).** 8 m is ~40% of the arena width, so no drone ever observes the whole
   field. This is the *precondition* for collaborative perception to matter — with full-field sensing,
   sharing would be vacuous. Partial observability is what makes the problem real. Cat A+B.
2. **Comm > sensing (why 10 m > 8 m — the load-bearing choice).** The comm range is deliberately *larger*
   than the LiDAR range, guaranteeing a neighbour's broadcast can describe regions the ego cannot yet sense
   itself → sharing carries genuinely new information. If comm ≤ LiDAR, every shared observation would only
   duplicate the ego's own perception and collaboration would add nothing. The 2 m margin (25% reach
   extension) is simultaneously the channel collaborative perception exploits **and** the channel a Byzantine
   neighbour abuses — central to the paper's threat model. Cat A.
3. **Hardware grounding.** 8 m is within the reliable range of low-cost 2-D LiDAR (RPLIDAR-A1 class); 10 m
   matches short-range UWB / WiFi-Direct mesh links used for real swarm coordination (cite the sensor sources
   already in root `PARAMETER_JUSTIFICATION.md §1–2`). Cat B.

> Reconciliation: earlier v14-era docs said "12 m LiDAR / 8 m comm"; the Phase_CD env actually uses
> **8 m LiDAR / 10 m comm** — use these values everywhere and ensure comm > LiDAR is stated explicitly.

### 2.2 Attack model parameters — ✅ **MEASURED & JUSTIFIED 2026-06-20** (`measure_env_stats.py 0.27 300`)
**Real-obstacle ground truth (300 maps, density 0.27):** count mean **29.7** (median 29, range 15–56);
radius mean **0.907 m** (= the probability-weighted expectation `0.42·0.35 + 0.40·1.0 + 0.18·2.0`); bands
**42 % small [0.2,0.5] / 40 % medium [0.6,1.4] / 18 % large [1.5,2.5]**; mean area **3.79 m²**. These are
the numbers every attack parameter is now anchored to (no hand arithmetic).

| Param | Value | Justification (measured) |
|---|---|---|
| `n_phantom` | **per-map Uniform{3,4,5,6}** (was fixed 4) | A phantom wall of 3–6 obstacles = **10 / 13 / 16 / 20 %** of the 29.7-obstacle real field → plausibly dense, never a suspicious flood. Geometric lower bound: at mean radius 0.907 m + spacing 1.3 m the wall spans **4.9 m (k=3) → 8.8 m (k=6)**, so even the smallest wall clears the 4.0 m goal approach; k≥7 saturates the corridor (no added harm). Randomizing per map removes any "fixed-k" detector shortcut. Cat B. |
| `phantom_radius` | **per-phantom from the real 42/40/18 mixture** over [0.2,2.5] (was fixed 1.0) | Phantoms become **size-indistinguishable from real obstacles** — the strongest stealth choice and the hardest test for the defense (the filter cannot gate on "wrong size"). Replaces the arbitrary fixed 1.0 m. Cat B. |
| `phantom_block_dist` | 3.5 m | Wall placed 3.5 m up the goal approach — inside comm range (10 m) and LiDAR range (8 m) so honest drones *can* contradict it, yet close enough to actually block the final approach. Cat B. |
| `phantom_spacing` | 1.3 m | ≈ mean obstacle diameter (2·0.907≈1.8 m) minus overlap → a near-contiguous barrier without gaps a drone could thread. Cat B. |
| `camouflage_gap` | 0.3 m (default) | The stealth/harm dial; the clean bind is now swept via `phantom_center_offset` (§2.4). Cat B/C. |
| **traitor count f** | sweep **f = 1, 2, 3** (max f=3 per `Literature_Review_Template`) | f/N = 10/20/30 % Byzantine. f=3 is the literature-justified ceiling (bare minority < N/2). Headline cell f=2. Cat B. |

> **Note — the offset/bind sweep keeps FIXED radius.** The randomized radius/n_phantom is for the *headline
> realism* runs. The `phantom_center_offset` stealth/harm-bind demo (§2.4) must hold radius fixed so the only
> moving variable is the offset — otherwise the bind axis is confounded.

### 2.3 Noise levels (σ ∈ {0, 0.2, 0.4, 0.6} m) — ✅ **WRITTEN 2026-06-20**
`sensor_noise σ` = zero-mean Gaussian std (metres) added to every sensed obstacle position (models
range/localisation error). Swept in even **0.2 m steps**; σ=0 is the idealised-sensing ablation. **σ=0.6 m
is severe by three independent yardsticks:**

| yardstick | reasoning |
|---|---|
| **vs obstacle size** | Measured mean obstacle radius = **0.91 m** (small obstacles 0.2–0.5 m). σ=0.6 m is *on the order of the object being localised* → you can barely tell where the obstacle is. |
| **vs safety clearance** | Drone clearance is **0.20 m**; σ=0.6 is **3×** that → materially erodes collision margins. |
| **vs filter tolerance** | Two honest drones disagree by **√2·σ ≈ 0.85 m > verify_eps = 0.6 m** → exactly the regime where the naive filter misfires (§5.6). σ=0.6 is the natural stress point for the defence study. |

**Why not beyond 0.6 m:** the positional error then so far exceeds the obstacle scale that the shared map
becomes uninformative *for every agent* — a fundamental perception-information limit (§5.10), not a defence
failure. So 0.6 is the meaningful upper bound where the *defence* study is still informative. Sensor terms:
σ≈0.2 ≈ well-calibrated UWB; σ≈0.6 ≈ degraded multipath/NLOS. Cat B/C.

### 2.4 Adaptive-attacker sweep ranges (new this session) — **MED priority**
| Param | Sweep | Needs |
|---|---|---|
| `phantom_center_offset` | 0.0–2.5 m | The stealth/harm-bind axis (0 = on real obstacle/harmless, large = harmful). Mostly self-justifying as a sweep; state the range covers harmless→harmful. Cat B. |
| `phantom_jitter` | 0.0–1.0 m | Filter-aware "fake honest noise" attack. Self-justifying sweep. Cat B. |
| `phantom_duty` | 1.0–0.3 | Intermittent lying. Self-justifying sweep. Cat B. |

### 2.5 Training hyperparameters — ✅ **VERIFIED 2026-06-19 (read from checkpoints; full chain in
`M0_PROVENANCE_AND_LINEAGE.md`)**
- **Base (set at the v10 scratch `PPO()`, carried through every fine-tune):** `gamma=0.99`, `n_steps=2048`,
  `batch_size=256`, `n_epochs=10`, `gae_lambda=0.95`, `clip_range=0.2`, `vf_coef=0.5`, `max_grad_norm=0.5`,
  `n_envs=100`, **net_arch pi=[64,64]/vf=[64,64]** (⚠️ NOT [256,128] — that was the unrelated v15 line),
  `VecNormalize(norm_obs=False, norm_reward=True, clip_reward=10.0)`. Cat B (cite SB3 defaults where kept).
- **Per-stage overrides:** M0 `lr=5e-5, ent_coef=0.015`; Option-C noise base `lr=3e-5, ent_coef=0.020`.
- **Option-C curriculum:** stage0 = 1.5M steps σ~U[0,0.3] @ density 0.20; stage1 = 2.0M steps σ~U[0,0.6] @
  density 0.25.
- **0.27 switch:** lock-in trained at 0.25; eval now at 0.27. `FINAL_PARAMETER.md §4` shows the agent clears
  0.30 @ 93.6% (σ=0) → 0.27 is within capability; optional short 0.27 lock-in fine-tune for a clean
  "trained & evaluated at 0.27" claim. Cat C.

### 2.6 Reward function weights — ✅ **EXTRACTED 2026-06-19** (`swarm_env_step_B10_8_0m.py` lines 594–753)
Per-agent per-step sum of the following terms (inherited unchanged by the collab/noise envs):
| Term | Value | Note |
|---|---|---|
| **Progress to goal** | `+100.0 × Δ(shortest-path dist)` | ⚠️ uses the **Dijkstra** path-distance map → the disclosed crutch is *in the reward too* |
| Time/step penalty | `−0.25` per step | encourages finishing |
| Path-alignment bonus | `+0.5 × vel_alignment` (only if >0.5 & speed>0.3) | reward moving along the path heading |
| Yield-while-blocked | `+0.5` (or `×decay`) when slow & blocked by a drone | learned queuing/yielding |
| Over-block penalty | `−0.15 × min((blk−50)/25,1)` | discourages permanent blocking |
| Frustration (stagnation) | `−min((stag−50)×0.25, 25.0)` | escalating anti-stagnation |
| Time-to-collision | `−10.0 × (1−ttc)²` if ttc<1 | predictive collision avoidance |
| Closing-speed (near) | `−25.0 × closing_speed × (0.6−dist)` if dist<0.6 | |
| Proximity (very near) | `−(0.4−dist) × 100.0` if dist<0.4 | |
| Head-on urgency | `−50.0 × urgency²` (aimed) / `−10.0 × urgency` | dist<0.5 |
| Co-alignment bonus | `+0.5 × cos_sim × alignment_progress` | dist<1.5; flock toward goal |
| Smoothness | `−0.05 × ‖Δaction‖²` | jerk penalty |
| Front clarity | `+0.2 × (front_lidar_mean/8)` | reward clear path ahead |
| Near-miss | `−1.0 × ((0.15−min_lidar)/0.15)²` | |
| **Collision (terminal)** | `= −500.0`, terminate | wall/obstacle/drone |
| **Goal (terminal)** | `+500.0 + 100.0/(1+speed)` | bonus for arriving slow/controlled |
| Timeout | `−200.0` | at max_steps |
- **Justification framing:** dominant shaping is the **Dijkstra-progress term (×100)** — disclose that the
  reward, not just the obs, uses the global path map (ties to Limitation 3). Collision `−500` ≫ step costs
  so safety dominates; the goal `+500` makes success the clear attractor. The many small social terms
  (yield/co-align/clarity) are the learned-etiquette shaping from the v10→v14 curriculum. Cat B/C.

### 2.7 Evaluation protocol — **LOW priority (mostly self-justifying)**
- 150 maps (dev) / 500 maps (camera-ready); deterministic seed + solvability retry; honest-drone-only
  denominator; **paired-bootstrap 95% CIs** (`boot_ci.py`, 2000 resamples, seed 12345). State as the
  statistical-rigor protocol; cite the bootstrap method. Cat B. ✅ implemented.

---

## 3. Priority checklist (what to actually write before submission)

1. **[HIGH] ✅ DONE — sensing/comm ranges written** (8 m LiDAR / 10 m comm, comm>LiDAR rationale + hardware
   grounding; reconciliation note added). (§2.1)
2. **[HIGH] ✅ DONE — attack parameters justified** (measured: n_phantom, radii mixture, spacing, f-sweep). (§2.2)
3. **[MED] ✅ DONE — noise range written** ({0,0.2,0.4,0.6}; σ=0.6 severe by 3 yardsticks; §5.10 limit). (§2.3)
4. **[MED] ✅ DONE — base PPO hyperparameters + reward weights extracted & verified** (§2.5, §2.6;
   provenance in `M0_PROVENANCE_AND_LINEAGE.md`).
5. **[MED] ✅ DONE — 0.27 train/eval position stated** (clears 0.30 @ 93.6%; optional 0.27 lock-in). (§2.5)
6. **[LOW] One paragraph** on the adaptive-sweep ranges and the eval/CI protocol. (§2.4, §2.7) — *writing*

> **All FACTUAL extraction is now complete** (params, hyperparameters, reward, lineage, leak status — §1,
> §2.4–§2.7 + the two companion docs). The only items left are **pure writing tasks** (§2.1 range
> reconciliation prose, §2.2 attack-param rationale, §2.3 noise-range rationale) — no more code archaeology
> needed. After those three paragraphs, the "Experimental Setup / Parameters" section is reviewer-complete.

---
*Companion to `PARAMETER_JUSTIFICATION.md` (physical, cited), `FINAL_PARAMETER.md` (density), and
`PAPER_MASTER_PLAN.md §6` (defense). This file is the Phase_CD-specific superset + gap list.*
