# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**TA-MAPPO** (Trust-Aware Multi-Agent Proximal Policy Optimization) — a bio-inspired MARL framework for resilient drone swarm navigation. 10 autonomous drones navigate to a shared goal using dual-sensing (LiDAR + inter-agent communication) and a bio-inspired "T-Cell" trust mechanism that defends against adversarial "traitor" drones.

**4-Phase curriculum:**
- **Phase A** (COMPLETE — 99.68% success): 20×20 field, 10 drones, no obstacles, no traitors
- **Phase B** (IN PROGRESS): Static obstacle avoidance with 48-ray vectorized LiDAR; currently in B5 Synchronization sub-phase (v15+ variants)
- **Phase C** (PLANNED): Deceptive traitors + obstacles; trust mechanism activates
- **Phase D** (PLANNED): Aggressive traitors + full TA-MAPPO

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

## Architecture

### Core Concepts

| Component | Detail |
|-----------|--------|
| **RL algorithm** | PPO via Stable-Baselines3 (`MultiInputPolicy` with custom extractor) |
| **Environment** | PettingZoo `ParallelEnv` — all 10 agents act simultaneously |
| **Observation space** | Split-brain: 202D local (LiDAR rays + ego state) + 530D global (all drone positions/velocities) |
| **Action space** | Continuous 2D velocity `(vx, vy) ∈ [-1, 1]²` |
| **Sensing (Phase B)** | 48-ray vectorized LiDAR with sigmoid LUT for fast forward pass |
| **Pathfinding (analysis only)** | BFS (solvability check), Dijkstra/A* (tortuosity metrics) on a 10cm grid |

### Policy Architecture (`MAPPO_Extractor_v15`)

Custom `BaseFeaturesExtractor` that feeds local observations to the actor and full global observations to the critic — implementing the centralized-training / decentralized-execution (CTDE) pattern.

### Environment Files (by phase)

- `Phase A/Hardened_Baseline/swarm_env_step_A.py` — Phase A environment (16-ray LiDAR, 600-step episodes)
- `Phase B/*/swarm_env_step_B.py` — Phase B4 with static obstacles
- `Phase B/Phase_B5_Synchronization/v10_IEEE_Final/swarm_env_step_B5_v15_master.py` — current master (48-ray vectorized LiDAR, 1200-step episodes, Dijkstra distance map, sigmoid LUT)

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
