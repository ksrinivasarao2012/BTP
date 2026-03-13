# TA-MAPPO: Trust-Aware Multi-Agent Proximal Policy Optimization

A bio-inspired, trust-aware multi-agent reinforcement learning framework for resilient drone swarm navigation. Built using **PPO** (Proximal Policy Optimization) with **PettingZoo** parallel environments.

## 🎯 Project Overview

This project implements a **Trust-Attentive MAPPO (TA-MAPPO)** framework where a swarm of 10 drones learns to autonomously navigate to a shared goal coordinate in a 20×20 continuous space — while being resilient to adversarial "traitor" drones that try to sabotage the mission.

### Core Architecture
- **Dual-Sensing Paradigm**: LiDAR (trusted, cannot be spoofed) + Communication (untrusted, can be spoofed by traitors)
- **Bio-Inspired T-Cell Trust Mechanism**: 5 fault-indicator "Antigens" feed a recursive trust score $T_{ij} \in [0, 1]$
- **Feature Gating Network**: Trust scores gate communication features ($h_j \odot T_{ij}$), blinding the policy to traitor lies
- **CTDE (Centralized Training, Decentralized Execution)**: Centralized critic during training, decentralized actor at inference

---

## 🗂️ Project Structure

The project is structured sequentially by curriculum phases. 

```text
Multi-agents/
├── Phase A/                     # [COMPLETED] Basic swarm convergence (0 obstacles/traitors)
│   ├── swarm_env_step_A.py      # PettingZoo environment (10 drones, 20x20 field)
│   ├── train_step_A.py          # PPO training script
│   ├── test_suite_step_A.py     # Automated 1K-episode evaluation suite
│   ├── k_fold_validation.py     # 5-Fold statistical cross-validation script
│   ├── models/                  # Saved PPO model checkpoints
│   │   └── step_A_foundation_model.zip
│   ├── test_cases/              # JSON test scenario files
│   ├── Project_Summary_Step_A.md # ✅ Full story of Phase A's bug fixes & results
│   ├── analyze_crashes.py       # Diagnostic script identifying funnel failures
│   └── README.md                # Old readme archive
├── checklists/                  # Step completion tracking
├── trick_challenges/            # Documentation of discovered bugs
└── requirements.txt             # Python dependencies
```

---

## 📊 Phase A: Final Verified Results

Phase A (`[0 Traitors, 0 Obstacles]`) focused purely on swarm pathfinding and continuous multi-agent collision avoidance. It was successfully completed in March 2026.

After deploying the **Social Distancing Shock** and the **School Zone** velocity limit to untangle dense 2x2 drone clusters, the 5-Fold Validation Suite (5,000 simulations) yielded perfect stability:

| Metric | Result (5-Fold CV: 50,000 Drones) |
|:---|:---|
| **Drones** | 10 Honest Drones |
| **Field Size** | 20 × 20 continuous |
| **Random Spawns** | **99.68%** Mean Success (StdDev: ±0.19%) |
| **Dense 2x2 Clusters** | **95.78%** Mean Success (StdDev: ±0.42%) |
| **Timeout Rate** | 0.00% |

*(For full mechanical details on how we broke the 21% physics engine ceiling and the subsequent 89% cluster panic ceiling, please read `Phase A/Project_Summary_Step_A.md`)*

---

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

### Running the Phase A Codebase
```bash
cd "Phase A"

# Run the 5-Fold Statistical Validation Suite
python k_fold_validation.py

# Run Visual PyGame Rendering of Basic Tests (Watch the drones!)
python test_suite_step_A.py edge_case_1.json
```

---

## 🗺️ Roadmap

- [x] **Step A**: Basic swarm convergence (0 traitors, 0 obstacles) — **99.68% ✅**
- [ ] **Step B**: Navigation with 20–30 static obstacles (LiDAR dodging)
- [ ] **Step C**: Deceptive traitors + obstacles (Trust $T_{ij}$ activation)
- [ ] **Step D**: Aggressive traitors + obstacles (Full TA-MAPPO)

Next up is **Step B**, which will involve copying the foundational `swarm_env_step_A.py` into the root directory and upgrading the physics engine to instantiate static obstacles that block both LiDAR rays and physical thrust vectors.

---

## 📄 Reference
Based on: *Trust-Aware Bio-Inspired Swarm Defense using TA-MAPPO*  
See `Objective and methodology.pdf` for the full methodology.

## 📝 License
This project is part of academic research. Please contact the authors for usage permissions.
