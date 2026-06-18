# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## ⭐ ALWAYS FOLLOW THESE RULES

1. **Address the user as "Srinivasa," at the start of every response.**
2. **Never run any command or code automatically.** Always show the command first and wait for explicit confirmation before executing.

---

## ⭐ LATEST STATUS (2026-06-16) — read this first

**Decision point: choosing among 3 paper directions in `backup/`.** All reactive Phase-C/D defenses failed; a
leakage audit forced a cleanup. Summary of what was done this session:

### Leakage audit & cleanup (DONE)
- **Clean headline model = `models/apex_ultra_glide_v14_comm8_lidar_final.zip` (M0)** — 8 m gated comm + LiDAR
  congestion. Verified clean with `leak_test_local.py`: actor ignores the global/critic block (0.0%) and neighbor
  stagnation (0.2%); it uses LiDAR + 8 m communicated neighbor pos/vel (~10–19%, a *modeled radio*, must be disclosed).
- **Leaky artifacts quarantined → `leaky/`**: 51 models (v10–v14 lineage, v15–v20 masters, `v14_8_0m`, `comm3/5/0`
  — ground-truth congestion / omniscient neighbors) + their leaky results + the v14_8_0m trainer. `models/` now holds
  ONLY clean models (M0, `comm0_nocong`, `M1_ram`). See `leaky/README.md`, `MODEL_LEAK_LEDGER.md`.
- **Phase-B analysis re-run clean** into `results/clean/` (feature ablation, comm blackout, comm range sweep). Scripts
  `eval_ablate_feature.py` / `eval_comm_blackout.py` / `eval_comm_sweep_clean.py` / `eval_comm_robustness.py` now point
  to M0 + `congestion="lidar"`. Blackout confirmed prior finding (−5/−7.75 pp). See `LEAK_REMEDIATION_LOG.md`.
- **⚠ Dijkstra goal-direction crutch (key finding):** actor `obs[2:4]` is the gradient of a GLOBAL Dijkstra
  shortest-path map (`swarm_env_step_B10_8_0m.py:435`, `:98`) — a privileged, map-aware routed heading. This is *why*
  communication is inert (the drone already has complete nav info). Memory: `dijkstra-goal-direction-crutch`.

### Phase C/D findings (all on clean M0 — valid)
- Deception INERT (~0 pp) · ramming ~−9 pp/rammer (f=2 = 77.4/73.5) · M1 retrain barely helps · **all 3 reactive
  defense oracles (evasion / coordination / speed-asymmetry) cap ~75–80% → fundamental-limit result.**

### The 3 options (in `backup/`) — pick one, each has a self-contained new-chat prompt
1. **`backup/OPTION_1_LIMIT_PAPER.md`** — fundamental-limit/characterization paper. Safe floor (workshop/mid-tier),
   low effort. Must disclose the 8 m comm model + the Dijkstra heading.
2. **`backup/OPTION_2_COMM_MATTERS.md`** — *recommended upside.* Remove the Dijkstra crutch + degrade LiDAR so comm
   becomes load-bearing → revives deception/trust. Run the 1-day feasibility probe FIRST.
3. **`backup/OPTION_3_OBSTACLE_AVOIDANCE.md`** — weakest; blocked by the Dijkstra crutch (must remove + retrain) and a
   crowded SOTA field.

### Key docs from this session
`CTDE_LEAKAGE_INVESTIGATION.md` (leak test + reviewer rebuttal) · `MODEL_LEAK_LEDGER.md` (leaky-vs-clean tables +
results audit) · `LEAK_REMEDIATION_LOG.md` (what was removed/re-run + impact) · `CLEAN_SHEET_ACTION_PLAN.md` (runbook) ·
`PHASE_C_FINAL_TRY_PLAN.md` (the defense oracles) · `NEW_CHAT_PROMPT_PHASE_CD.md`. Reproduce the leak test:
`& $py leak_test_local.py models\apex_ultra_glide_v14_comm8_lidar_final.zip lidar`.

> NOTE: sections below predate this cleanup. Where they say "Pathfinding (analysis only)" or cite leaky-model
> numbers, defer to this LATEST STATUS block and `MODEL_LEAK_LEDGER.md`.

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
