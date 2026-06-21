# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## ⭐ ALWAYS FOLLOW THESE RULES

1. **Address the user as "Srinivasa," at the start of every response.**
2. **Never run any command or code automatically.** Always show the command first and wait for explicit confirmation before executing.

---

## ⭐ LATEST STATUS (2026-06-19) — read this first

**The paper is the Byzantine collaborative-perception + temporal-trust line.** Single source of truth =
`Phase_CD/PAPER_MASTER_PLAN.md` (full results ledger §5, parameter justifications §6, limitations §7,
pending items §8, paper structure §9, venue §10, file index §11, decision log §12). Target venue =
**MDPI *Drones*** (SCIE, IF ≈ 4.4). This LATEST STATUS block summarizes everything needed to WRITE the
paper; defer to PAPER_MASTER_PLAN for exact tables.

### The story arc (what the paper claims, in order)
1. **Phase-B navigator (no adversary)** — CTDE MAPPO, 10 drones, 20×20 m. Success 95.6% (d=0.20) /
   91.1% (d=0.30). Base model **M0 = `models/apex_ultra_glide_v14_comm8_lidar_final.zip`**.
2. **Phase-3 collaborative perception (THE ANCHOR, §5.2)** — neighbors share sensed obstacles (slot-fusion;
   per-neighbor obstacle lists fused by a MIN into the 48-ray LiDAR channel). Under ~33% LiDAR dropout, comm
   is load-bearing: **53% → 94%** success. This is the big clean figure.
3. **Phase-4 Byzantine false-obstacle attack (§5.3–5.5)** — traitors broadcast PERSISTENT phantom obstacles
   (not in ground truth, so the map stays solvable). Because fusion is a MIN, a fabricated near-obstacle
   overrides even a fully-sighted drone's own LiDAR → attack is **dropout-independent**. Two placements:
   **wall** (phantom barrier across the goal approach — easy to detect) and **camouflage** (phantom hugs a
   real obstacle on the corridor, extending it into the gap — hard to detect). `camouflage_gap` tunes the
   stealth/harm dial. k=2 traitors of 10 ≈ −12–25 pp honest-success drop.
4. **Consistency-trust defense ("T-cell" self/non-self, §5.4–5.5)** — per (observer i, neighbor j) trust
   t_ij∈[0,1], EWMA, reset each episode. If i is sighted and j broadcasts an obstacle i is positioned to
   see but doesn't → contradiction → t_ij↓; t_ij<τ ⇒ j excluded from i's fusion. Reads only what i
   physically senses (no privileged labels). Under IDEAL sensing this fully neutralizes wall + most
   camouflage.
5. **Noise breaks the naive filter (§5.6)** — add Gaussian σ to every drone's sensed obstacle positions
   (`sensor_noise`). Two honest views of one obstacle differ by ~√2σ; once that exceeds the fixed
   `verify_eps`, the verifier wrongly contradicts HONEST broadcasts → precision 1.00→0.32, defense becomes
   *worse than no defense*. (Quotable negative result.)
6. **ROBUST filter rescues precision (§5.7/5.8)** — noise-aware tolerance `eps = verify_eps + k_sigma·σ`
   (k_sigma=4) + slower decay (alpha=0.25). Precision back to 0.93–1.00, no-harm ≈ base, graceful recovery.
   BUT at **σ=0.6 + camouflage, recall collapses to 0.21** (recovery +1.4 pp) — the lie hides inside the
   widened band. This was the open weakness.
7. **Option C — is the high-noise base drop fixable? NO (§5.10, P1 CLOSED)** — fine-tuned the base under
   σ∈[0,0.6] domain-randomization for 3.5M steps (`models/noise_robust_ON_stage{0,1}_final.zip`). Base
   recovered only ~2.5 pp at σ=0.6 → the 92→70% navigation drop is a **genuine perception-information
   limit**, not a training artifact. (This is the *navigation* limit and it STANDS.)
8. **Temporal trust — the WIN (§5.11, P2+P4 CLOSED, done 2026-06-19)** — recovers the σ=0.6 camouflage
   recall collapse. **Mechanism:** the per-frame OFFSET VECTOR `d = (neighbour j's reported obstacle pos) −
   (ego's own sensed pos of the matched obstacle)` is ZERO-MEAN for honest j (`noise_j − noise_ego ~
   N(0,√2σ)`, cancels over frames) but a PERSISTENT bias for a camouflage liar (`gap − noise_ego`, mean =
   the gap). Filter keeps a per-(ego,neighbour,ego-track) running mean of d; once a bucket has
   ≥`temporal_min_k=20` samples, flag j if `‖mean‖ > temporal_bias_eps=0.6 m`. Composes (logical OR) with
   the single-frame robust check (fast path = wall; temporal slow path = camouflage). **Hand-coded; NO
   learned trust needed.**

### Temporal-trust numbers — CAMERA-READY (500 maps, density 0.27, base=stage2, RANDOMIZED attack)
**Headline σ=0.6 camouflage cell, k=2** (full per-f tables + CIs in `Phase_CD/RESULTS_027_CAMERA_READY.md`):
| metric | robust (single-frame) | **temporal (composed)** |
|---|---|---|
| recall | 0.13 | **0.69** |
| recovery vs undefended | +3.4 pp | **+12.2 pp** |
| success | 41.0% | **49.8%** (vs base 53.4) |
| precision | 0.92 | 0.82 |
| no-harm (k=0, defense ON) | — | **53.0% vs base 53.4% = −0.4 pp (flat, CI spans 0)** |

**Trend across f (σ=0.6 camouflage recovery, robust→temporal):** f=1 +1.9→**+7.1** (R 0.13→0.69); f=2
+3.4→**+12.2**; f=3 +5.3→**+13.6**. Attack *saturates* (f2→f3 adds ~3 pp damage); precision *rises* with f
(0.68→0.82→0.89) — defense most precise when threat is worst. Wall σ=0.6: robust +3.7→temporal **+9.7** (f=2).
Temporal ≥ robust at every noise level; wall never regresses; no-harm flat throughout.
**Adaptive attacker (filter-aware, σ=0.6 camo, 500 maps):** offset bind — as phantom centre-offset grows,
harm AND detection-recall climb together (offset 0 = harmless+invisible R0.03; offset 2.5 = harmful+caught
R0.70) → no free lunch. gap/jitter/duty all hold (jitter/duty *reduce the attacker's own harm* faster than
recall sags). **Probe evidence (dev, 150 maps):** oracle assoc AUC **0.99**, realistic assoc AUC **0.85–0.90**.

> NOTE: dev numbers (150 maps, density 0.25, stage1, fixed attack) were recall 0.21→0.78 / recovery +1.4→+7.7;
> superseded by the camera-ready above (harder 0.27 + size-indistinguishable phantoms → slightly lower
> absolute, same qualitative WIN).

### The precision caveat (write it honestly)
Temporal detection precision is **0.80–0.82 at σ=0.6** (< a 0.9 target). But precision was only a *proxy*
for false-gating harm, and the **no-harm column measures that harm directly and finds it ≈0** (own-LiDAR +
the Dijkstra heading cushion any wrongly-gated broadcasts). The residual false-flags are ultra-stealthy
camouflage buckets (phantom hugging so tightly it barely protrudes → statistically ≈ honest noise AND
nearly harmless — the **stealth/harm bind**). `eps=0.7` raises precision to ~0.85 but sacrifices harmful-
phantom recall, so **eps=0.6 is the operating point**.

### IN PROGRESS (this session) — filter-aware ADAPTIVE attacker
Building an attacker that KNOWS the temporal filter exists, to pre-empt the #1 reviewer objection ("the
adversary is static/weak"). Three variants in the experimental env: (a) **jitter** — phantom + per-frame
zero-mean noise (predict: does NOT defeat the mean test, since jitter raises variance not mean);
(b) **intermittent lying** — broadcast the phantom only a fraction of frames (dilutes the bucket);
(c) **offset sweep** (the clean bind demo) — `phantom_center_offset` places the phantom an exact distance
from the hugged real obstacle's CENTRE (0 = on top → harmless+evasive; large → harmful but caught), so harm
and recall climb together → attacker has no free lunch. (`camouflage_gap` alone can't show this: it's a
surface gap, so the phantom centre is always ≥~1.5 m out → always caught, recall ~0.8 across the realizable
range.) Knob in `Collab_Perception/env_byzantine_adaptive.py` (default None = unchanged). Files (new):
adaptive hooks in `Noise_added/env_noisy_byzantine.py` + `Noise_added/eval_adaptive_attack.py` (sweeps
`offset|gap|jitter|duty`). See PAPER_MASTER_PLAN §5.11 / §8.1.

### The TWO honest limits (do not conflate — both disclosed in §7)
- **Navigation perception limit (§5.10, STANDS):** base success 92→70% as σ→0.6; sensor info the LiDAR
  never provided cannot be recovered. The defense never makes it worse.
- **Security/detection limit (§5.8, RECOVERED in §5.11):** the single-frame camouflage recall collapse —
  recovered temporally. These are independent.

### Mandatory disclosures (a reviewer kills the paper without them)
- **Dijkstra goal-direction crutch:** actor `obs[2:4]` is the gradient of a GLOBAL Dijkstra shortest-path
  map (`swarm_env_step_B10_8_0m.py:435`, `:98`) — a privileged routed heading. It dampens attack severity
  (reported drops are a LOWER bound) and is the **sole remaining RA-L blocker** (P3, weeks of retrain).
  Frame as "an external mission planner provides routed waypoints; the policy does local control +
  collision avoidance." Memory: `dijkstra-goal-direction-crutch`.
- **8 m comm model** (perfect, zero-latency within range). · **Idealized sensing** (the noise study addresses
  ranging noise but not occlusion). · **Hand-coded trust, not learned** (we proved the learned single-frame
  gate is untrainable as drawn). · **Neighbor-level filtering** (excludes a whole neighbor on one
  contradiction → information loss; obstacle-level is future work P6). · **Sim-only, 10 drones, 2-D,
  circular obstacles.**

### Models in `models/` for this line
`apex_ultra_glide_v14_comm8_lidar_final.zip` (M0 base) · `raster_slot_fusion_{ON,OFF}_stage2_final.zip`
(clean-trained collab-perception) · **`noise_robust_ON_stage{0,1}_final.zip`** (Option C noise-robust base;
**stage1 was the base for the §5.7–5.11 DEV tables** @ density 0.25) · **`noise_robust_ON_stage2_final.zip`**
(0.27 lock-in, 1.5M steps σ~U[0,0.6]; trained 2026-06-20 — **the base for ALL camera-ready f∈{1,2,3} runs at
density 0.27**).

### Reproduce the whole temporal-trust chain (run python by full path; see PhaseB2 Commands block)
```
$py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe" ; cd "D:\Swarm\BTP"
$M  = "models/noise_robust_ON_stage1_final.zip"
& $py Phase_CD\Noise_added\probe_temporal_offset.py $M 150 2 10 camouflage 0.6                  # STEP1 oracle (AUC 0.99)
& $py Phase_CD\Noise_added\probe_temporal_offset.py $M 150 2 10 camouflage 0.6 --assoc realistic # STEP2 (AUC 0.88)
& $py Phase_CD\Noise_added\selftest_temporal.py $M 5 0.6 20                                      # STEP3 sanity (R 0.97)
& $py Phase_CD\Noise_added\eval_temporal.py $M 150 2 10 wall                                     # STEP4 (WIN)
& $py Phase_CD\Noise_added\eval_temporal.py $M 150 2 10 camouflage                               # STEP4 (WIN)
```
Cold-start handoff for this experiment: `Phase_CD/Noise_added/TEMPORAL_TRUST_RUNBOOK.md`.
Memory files: `temporal-trust-result`, `option-c-perception-limit`, `dijkstra-goal-direction-crutch`.

**⚠ Camera-ready setup LOCKED 2026-06-20 (`PAPER_MASTER_PLAN §8.1`):** the §5.11/CLAUDE tables above are
**DEV numbers** (150 maps, density 0.25, base=stage1, FIXED attack, k=2). The publication runs change five
axes: **500 maps · density 0.27 · base=`noise_robust_ON_stage2_final` · RANDOMIZED attack** (per-map
n_phantom~U{3,4,5,6}, per-phantom radius from the real 42/40/18 obstacle mixture — verified
`verify_randomized_attack.py`) · swept over **f = 1, 2, 3** (literature ceiling). One-command driver (train
stage2 + the whole f-sweep eval matrix, Tee-logged to `Noise_added/results_027/`):
```
powershell -ExecutionPolicy Bypass -File Phase_CD\Noise_added\run_full_027_pipeline.ps1            # train+eval
powershell -ExecutionPolicy Bypass -File Phase_CD\Noise_added\run_full_027_pipeline.ps1 -SkipTrain # eval only
```
Paired-bootstrap 95% CIs are **implemented** (`boot_ci.py`); `eval_temporal.py`/`eval_adaptive_attack.py`
print a "95% CONFIDENCE INTERVALS" block (success cells, paired recovery/no-harm diffs, detection P/R; seed
12345). The adaptive `offset/gap/jitter/duty` sweeps stay **fixed-radius** (`randomize_attack=False`, so the
swept axis isn't confounded) and are run separately: `eval_adaptive_attack.py … 500 2 10 {offset,gap,jitter,
duty}`. **Replace the §5.11 dev cells once `results_027/` lands.** Status 2026-06-20: stage2 trained; f-sweep
eval running.

> NOTE: The older Phase-C/D RAMMING line (M0, deception inert, ramming ~−9 pp/rammer, the 3 defense oracles
> capped ~75–80%, and the 3 `backup/OPTION_*.md` paper options) is a **separate, shelved direction** — NOT
> the current paper. Sections further below that say "Pathfinding (analysis only)" or cite leaky-model
> numbers predate the cleanup; defer to this block, `PAPER_MASTER_PLAN.md`, and `MODEL_LEAK_LEDGER.md`.

---

## Project Overview

**TA-MAPPO** (Trust-Aware Multi-Agent Proximal Policy Optimization) — a bio-inspired MARL framework for resilient drone swarm navigation. 10 autonomous drones navigate to a shared goal using dual-sensing (LiDAR + inter-agent communication) and a bio-inspired "T-Cell" trust mechanism that defends against adversarial "traitor" drones.

**4-Phase curriculum:**
- **Phase A** (COMPLETE — 99.68% success): 20×20 field, 10 drones, no obstacles, no traitors
- **Phase B** (COMPLETE — clean baseline): Static obstacle avoidance, 48-ray vectorized LiDAR. Clean model **M0 = `models/apex_ultra_glide_v14_comm8_lidar_final.zip`** (8 m gated comm + LiDAR congestion, CTDE-clean). No-adversary success 95.6% (d=0.20) / 91.1% (d=0.30).
- **Phase C/D** (IN PROGRESS — adversarial defense, the "Trust-Aware" contribution): traitors + trust. Established on M0: comm **deception is INERT** (LiDAR overrides lies); physical **ramming** is the real threat (~−9 pp/rammer); the three reactive-motion defense oracles — **evasion / coordination / speed-asymmetry — all FAIL** the ~85% bar (fundamental-limit result). Current direction: **collaborative obstacle perception** (neighbors share sensed obstacles, rasterized into a fixed 48-d channel) + a **T-Cell trust-weighted fusion** defense, tested under LiDAR-dropout (sensor failure). **B3 dropout gate pending.** All C/D work lives in `Phase_CD/`.

## PhaseB2 — MAPPO Clean Reboot (ACTIVE)

`PhaseB2/` is a **from-scratch, self-contained reimplementation** started after the earlier Phase B line was deemed flawed. It is independent of the Phase A/B/C/D code above — its own env, wrapper, networks, training, and evaluation. This is the current active development target for the IEEE RA-L paper.

**Goal:** prove communication is necessary for 90%+ success. Phase 1 (no comm) establishes an honest 55–65% baseline; Phase 2 (comm) targets 88–93%; Phase 3 = Byzantine degradation; Phase 4 = simplified T-Cell trust recovery. Phase 5 (true 79D baseline) **dropped** — justified in one sentence in the paper.

**Algorithm: MAPPO (CTDE).** SB3 PPO feeds the same observation to both actor and critic, so MAPPO is achieved with a **1661D combined observation** = `[local 151D || global 1510D]`. The actor extractor slices `obs[:151]`; the critic extractor slices `obs[151:]`. At evaluation only the actor runs — the critic is never executed.

| Aspect | PhaseB2 detail |
|--------|----------------|
| **Env** | `PhaseB2/swarm_env.py` — `SwarmEnv`: 20×20m, 10 drones, **72-ray** LiDAR (range 8m), 1200-step episodes, circular obstacles, BFS solvability check, 8m gated comm |
| **Local obs** | 151D = 72 LiDAR + 7 own-state + 72 neighbor slots (9 × 8D). Phase 1: neighbor slots all **zeros** (comm disabled). Phase 2: real neighbor data |
| **Gym obs** | 1661D combined (151 local + 1510 global); 10-drone state-machine wrapper `SwarmFlatEnv` in `PhaseB2/gym_wrapper.py` |
| **Actor** | `SwarmActorExtractor` (86,400 params) → split LiDAR/own-state/neighbor encoders + mean-pool fusion → 128D |
| **Critic** | `SwarmCriticExtractor` (939,648 params) → plain MLP 1510→512→256→128, training-only |
| **Reward** | step −0.005, progress +Δ×0.3, goal +20.0, wall/obstacle −2.0, drone −1.0 (the ×0.3 progress weight breaks the old rush-and-die exploit) |
| **Curriculum** | 5 stages, density 0.05→0.10→0.15→0.20→0.25, 20M steps total (3M/4M/4M/4M/5M), 7 parallel envs (SubprocVecEnv) |

### PhaseB2 Commands

```powershell
# Run python by FULL path; conda env is swarm_rl (NOT swarm_rl_v2)
$py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
cd "D:\Swarm\BTP\PhaseB2"

& $py train.py --phase 1                       # Phase 1: no-comm baseline (20M steps)
& $py train.py --phase 2                       # Phase 2: comm enabled
& $py train.py --phase 1 --resume 2            # resume from completed stage 2 (valid: 1-4)
& $py evaluate.py --model checkpoints/phase1/model_stage5.zip --episodes 1000 --density 0.25
& $py evaluate.py --model checkpoints/phase2/model_stage5.zip --episodes 1000 --density 0.25 --communication
& $py gym_wrapper.py                            # env self-tests (check_env + shape asserts)
& $py networks.py                               # extractor self-test + param counts
```

### PhaseB2 Docs

- `PhaseB2/PLAN.md` — MAPPO explained simply (football-team analogy), CTDE/Byzantine rationale, full 5-phase roadmap, expected results table
- `PhaseB2/PHASE1_PLAN.md` — exhaustive Phase 1 spec: all params, obs/network breakdown, per-stage GO/NO-GO health checks, terminal-output format
- `PhaseB2/ARCHITECTURE.md` — 12-section component deep-dive (151D/1661D layout, actor/critic param breakdowns, gym state machine, physics loop)
- `PhaseB2/BUG_ANALYSIS.md` — 22 audited issues with problem/not-problem verdicts + fixes (all 22 resolved; key one was evaluate.py macro/micro-step conflation)

## Environment Setup

```bash
conda create -n swarm_rl_v2 python=3.10
conda activate swarm_rl_v2
pip install -r requirements.txt   # in Phase A/ root
```

Key dependencies: `stable-baselines3`, `pettingzoo`, `gymnasium`, `torch`, `numpy`, `pygame`, `tensorboard`

## Common Commands

```bash
# Phase A — training, evaluation, validation
cd "Phase A/Hardened_Baseline"
python train_step_A.py                        # Train Phase A PPO
python test_suite_step_A.py                   # 1K-episode evaluation
python test_suite_step_A.py visual            # Same with PyGame rendering
python k_fold_validation.py                   # 5-fold cross-validation (50K simulations)

# Phase B — current active work
cd "Phase B/Phase_B5_Synchronization/v10_IEEE_Final"
python train_step_B5_sync_v15_master.py       # 50M-step curriculum training
python k_fold_master_B10.py                   # Statistical validation (latest version)
python evaluate_v16_IEEE_Final.py             # Benchmark evaluation
python check_obstacle_density.py              # Density sweep / solvability analysis

# Benchmark Calibration (density tuning)
cd Benchmark_Calibration
python phase1_geometric_feasibility.py        # Phase 1: geometric feasibility
python phase2_difficulty_calibration.py       # Phase 2: difficulty calibration
```

```powershell
# Phase C/D — adversarial defense (Windows/PowerShell; run python by FULL path)
$py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
# threat / defense oracles on M0 (repo root):
& $py probe_ram.py 2 models\apex_ultra_glide_v14_comm8_lidar_final.zip 200      # ramming threat
& $py probe_coord_oracle.py 2 models\apex_ultra_glide_v14_comm8_lidar_final.zip 200  # (Phase_CD probes)
# Collaborative-perception RASTER architecture (Phase_CD/Collab_Perception/) — see RUNBOOK_RASTER.md:
& $py Phase_CD\Collab_Perception\surgical_expand_raster.py models\apex_ultra_glide_v14_comm8_lidar_final.zip models\raster_expanded_M0.zip
& $py Phase_CD\Collab_Perception\train_raster.py 5 10 0.4 on     # comm-ON under LiDAR dropout (gate)
& $py Phase_CD\Collab_Perception\eval_raster.py models\raster_l5_d0.4_ON_final.zip 5 10 0.4 on 200
```

## Architecture

### Core Concepts

| Component | Detail |
|-----------|--------|
| **RL algorithm** | PPO via Stable-Baselines3 (`MultiInputPolicy` with custom extractor) |
| **Environment** | PettingZoo `ParallelEnv` — all 10 agents act simultaneously |
| **Observation space** | Split-brain: local (actor) + global (critic). **Phase C/D env (`swarm_env_step_B10_8_0m`) = 130 local + 520 global = 650**; raster Lever-2 variant = 130 + 48 shared-map + 520 = **698**. (Phase A/B envs differ.) |
| **Action space** | Continuous 2D velocity `(vx, vy) ∈ [-1, 1]²` |
| **Sensing (Phase B)** | 48-ray vectorized LiDAR with sigmoid LUT for fast forward pass |
| **Pathfinding (analysis only)** | BFS (solvability check), Dijkstra/A* (tortuosity metrics) on a 10cm grid |

### Policy Architecture (`MAPPO_Extractor_v15`)

Custom `BaseFeaturesExtractor` that feeds local observations to the actor and full global observations to the critic — implementing the centralized-training / decentralized-execution (CTDE) pattern.

### Environment Files (by phase)

- `Phase A/Hardened_Baseline/swarm_env_step_A.py` — Phase A environment (16-ray LiDAR, 600-step episodes)
- `Phase B/*/swarm_env_step_B.py` — Phase B4 with static obstacles
- `Phase B/Phase_B5_Synchronization/v10_IEEE_Final/swarm_env_step_B5_v15_master.py` — Phase B master (48-ray vectorized LiDAR, 1200-step episodes, Dijkstra distance map, sigmoid LUT)
- `swarm_env_step_B10_8_0m.py` (repo root) — **Phase C/D env / M0's env**: 8 m gated comm, LiDAR congestion, traitor + deception hooks (`traitor_indices`, `traitor_behavior` ram/navigate, `deception_mode`, `_ram_action`, `_falsify_broadcast`), 650-d obs, 1200-step. **Pristine/committed — do not add experimental hooks here.**
- `Phase_CD/swarm_env_phasecd.py` — Phase C/D experimental copy: adds `lidar_range`, `speed_boost`, and collaborative-perception oracle hooks (`collab_comm`, `collab_nearest_only`)
- `Phase_CD/Collab_Perception/swarm_env_raster.py` — raster Lever-2 env: 48-d shared-obstacle-map channel at obs[130:178] + per-step sustained LiDAR dropout + sender-gating (blind drone shares nothing); 698-d obs

### Reward Function

Multi-term potential-based reward: `R_goal` (progress toward goal) + `R_safe` (collision avoidance) + `R_group` (cohesion) + `R_cluster` (anti-clustering). Reward shaping is the primary tuning lever between versions.

## Curriculum Structure (Phase B v15)

3-stage curriculum baked into `train_step_B5_sync_v15_master.py`:
1. **Warm-up** (0–5M steps): obstacle density 0.20, relaxed penalties
2. **Decay** (5–15M steps): density ramps to 0.26, penalties tighten
3. **Lock-in** (15–50M steps): density fixed at 0.26, full penalties

## Key Design Decisions & Bugs Fixed

- **Ghost drone bug** (Phase A): drones that reached the goal kept occupying space, causing collisions. Fixed by removing them from the active agent list immediately on arrival. This was the root cause of the 21% ceiling.
- **Social distancing + school zone velocity damping**: prevents drone clustering near the goal that caused cascade collisions.
- **Vectorized LiDAR** (Phase B): replaced per-ray Python loops with NumPy batched segment intersection — critical for training speed at 48 rays × 10 drones.
- **Sigmoid LUT**: pre-computed lookup table for the LiDAR activation, avoids repeated `np.exp` calls in the hot path.

## Model Checkpoints

- Phase A models: `Phase A/Hardened_Baseline/models/`
- Phase B v15–v20 models: `models/` (repo root) and `Phase B/Phase_B5_Synchronization/models/`
- Phase C/D models (repo root `models/`): **M0** `apex_ultra_glide_v14_comm8_lidar_final.zip` (clean baseline) · `apex_ultra_glide_M1_ram_final.zip` (M1, retrained vs rammers, barely helps) · `raster_expanded_M0.zip` (surgery 130→178 for the raster actor)
- TensorBoard logs: `Phase B/Phase_B5_Synchronization/ppo_swarm_tensorboard/` and `logs/`

## Benchmark Calibration

`Benchmark_Calibration/` holds the two-phase density calibration pipeline:
- **Phase 1** (`phase1_geometric_feasibility.py`): sweeps obstacle density for three grid sizes (20×20, 30×30, 40×40), filtering configurations where BFS reports < 95% solvability.
- **Phase 2** (`phase2_difficulty_calibration.py`): among feasible configs, finds the density band where agent success rate falls in the 40–70% "sweet spot" (not trivial, not impossible).
Results land in `Benchmark_Calibration/results/` and plots in `Benchmark_Calibration/plots/`.

## Documentation

- `Phase A/Hardened_Baseline/Project_Summary_Step_A.md` — complete Phase A narrative including the ghost-drone bug story
- `Phase B/docs/Phase_B_Implementation_Plan.md` — Phase B design and milestones
- `Phase B/docs/Phase_B_File_Structure_Guide.md` — file-by-file Phase B breakdown
- `BTP_Final_Report_Outline.md` — academic report structure (IEEE format)
- **Phase C/D** — short-LiDAR thread: `Phase_CD/PHASE_CD_PROGRESS_LOG.md`, `Phase_CD/PHASE_CD_ACTION_PLAN.md`, `Phase_CD/PHASE_CD_RUNBOOK.md`; oracle plan `PHASE_C_FINAL_TRY_PLAN.md` (repo root). **Collaborative-perception (current) thread** in `Phase_CD/Collab_Perception/`: `DESIGN_RASTER_TRUST.md` (architecture + trust module), `RUNBOOK_RASTER.md` (live build/run B1–B4, the make-or-break dropout gate), `DESIGN_A_FEASIBILITY.md`.
