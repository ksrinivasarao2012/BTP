# TA-MAPPO: Trust-Aware Multi-Agent Proximal Policy Optimization

A bio-inspired, trust-aware multi-agent reinforcement learning framework for resilient drone swarm navigation. Built using **PPO** (Proximal Policy Optimization) with **PettingZoo** parallel environments.

## 🎯 Project Overview

This project implements a **Trust-Attentive MAPPO (TA-MAPPO)** framework where a swarm of 10 drones learns to autonomously navigate to a shared goal coordinate in a 20×20 continuous space — while being resilient to adversarial "traitor" drones that try to sabotage the mission.

### Core Architecture
- **Dual-Sensing Paradigm**: LiDAR (trusted, cannot be spoofed) + Communication (untrusted, can be spoofed by traitors)
- **Bio-Inspired T-Cell Trust Mechanism**: 5 fault-indicator "Antigens" feed a recursive trust score $T_{ij} \in [0, 1]$
- **Feature Gating Network**: Trust scores gate communication features ($h_j \odot T_{ij}$), blinding the policy to traitor lies
- **CTDE (Centralized Training, Decentralized Execution)**: Centralized critic during training, decentralized actor at inference

## 📊 Current Results

### Phase 4 — Step A: Basic Swarm Convergence (No Obstacles, No Traitors)

| Metric | Result |
|:---|:---|
| **Drones** | 10 |
| **Field Size** | 20 × 20 continuous |
| **Success Rate** | **99.22%** (9,922 / 10,000 drones) |
| **Collision Rate** | 0.78% |
| **Timeout Rate** | 0.00% |
| **Episodes Tested** | 1,000 |

## 🗂️ Project Structure

```
Multi-agents/
├── swarm_env_step_A.py          # PettingZoo environment (10 drones, 20x20 field)
├── train_step_A.py              # PPO training script (fine-tuning from checkpoint)
├── test_suite_step_A.py         # Automated 1K-episode evaluation suite
├── evaluate_step_A.py           # Quick single-run evaluation script
├── generate_basic_test_cases.py # JSON test case generator
├── analyze_experiments.py       # TensorBoard log analysis utilities
├── models/                      # Saved PPO model checkpoints
│   ├── step_A_foundation_model.zip
│   ├── step_A_96.18_percent_success.zip
│   └── step_A_99.22_percent_success.zip
├── test_cases/                  # JSON test scenario files
├── trick_challenges/            # Documentation of discovered bugs
├── checklists/                  # Step completion tracking
├── ppo_swarm_tensorboard/       # TensorBoard training logs
└── requirements.txt
```

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Conda (recommended) or pip

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd Multi-agents

# Create conda environment (recommended)
conda create -n swarm_rl_v2 python=3.10 -y
conda activate swarm_rl_v2

# Install dependencies
pip install -r requirements.txt
```

### Training

```bash
# Train Step A (loads from checkpoint and fine-tunes)
python train_step_A.py

# Monitor training with TensorBoard
tensorboard --logdir ./ppo_swarm_tensorboard/
```

### Evaluation

```bash
# Run full 1,000-episode automated test suite
python test_suite_step_A.py 1k

# Run with visual PyGame rendering (watch the drones!)
python test_suite_step_A.py visual
```

### Live Preview

```bash
# Run the environment with random actions to preview the PyGame renderer
python swarm_env_step_A.py
```

## 🔧 Environment Details

### Observation Space (per drone)
- **16-ray LiDAR**: Distances to walls and other drones (360° coverage)
- **Broadcast State**: Goal direction, velocity, and neighbor information

### Action Space (per drone)
- Continuous 2D velocity vector $(v_x, v_y)$

### Reward Function
- **$R_{goal}$**: Potential-based reward for moving toward the goal
- **$R_{safe}$**: Collision penalties (walls: -100, drones: -50)
- **$R_{group}$**: Cohesion bonus for staying near teammates
- **Success Bonus**: +100 for reaching the goal + smooth-stop bonus

## 🐛 Key Bug Fix: Ghost Drone Problem

A critical physics bug was discovered and fixed: terminated drones left behind invisible hitboxes at the goal coordinate, causing subsequent drones to collide with "ghosts." This alone was responsible for capping the success rate at ~21%. See [`trick_challenges/ghost_drone_bug.md`](trick_challenges/ghost_drone_bug.md) for full details.

## 🗺️ Roadmap

- [x] **Step A**: Basic swarm convergence (0 traitors, 0 obstacles) — **99.22% ✅**
- [ ] **Step B**: Navigation with 20–30 static obstacles (LiDAR dodging)
- [ ] **Step C**: Deceptive traitors + obstacles (Trust $T_{ij}$ activation)
- [ ] **Step D**: Aggressive traitors + obstacles (Full TA-MAPPO)

## 📄 Reference

Based on: *Trust-Aware Bio-Inspired Swarm Defense using TA-MAPPO*  
See [`Objective and methodology.pdf`](Objective%20and%20methodology.pdf) for the full methodology.

## 📝 License

This project is part of academic research. Please contact the authors for usage permissions.
