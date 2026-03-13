# Phase A: File Guide & Overview

This document explains the purpose, contents, and role of every file located inside the `Phase A` directory. Phase A successfully achieved basic swarm convergence (10 drones flying to a goal without colliding, with 0 traitors and 0 obstacles).

##  Environment & Physics
The core laws of physics and the simulation world.

- **`swarm_env_step_A.py`**
  - **Purpose:** The fundamental Gym/PettingZoo environment.
  - **Contents:** Contains the `SwarmLidarEnv_StepA` class. Defines the 10 drones, their continuous $(v_x, v_y)$ action space, the 16-ray LiDAR observation space, and the PyGame rendering. This file also contains the critical **Reward Function** (`R_goal`, `R_safe`, `R_group`, `R_cluster`) which determines how the drones learn to spread out, obey speed limits, and funnel into the goal.

## 🧠 Training & Neural Networks
The actual AI learning mechanics.

- **`train_step_A.py`**
  - **Purpose:** The primary script to train the PPO (Proximal Policy Optimization) model.
  - **Contents:** Wraps the PettingZoo environment into a Stable-Baselines3 compatible vectorized environment. It instantiates the `PPO` neural network, defines learning rates, entropy coefficients, and executes the multi-million timestep curriculum loops (e.g., 80% clustered spawns). Saves the resulting models to the `models/` folder.
- **`train_step_A_experiments.py`**
  - **Purpose:** An alternative training script used for running parallel experiments with different hyperparameters.
  - **Contents:** Similar to `train_step_A.py`, but designed to output to different TensorBoard logging directories to compare different learning strategies without overwriting the main model.

## 🧪 Evaluation & Testing
Scripts used to mathematically verify that the trained AI actually works.

- **`test_suite_step_A.py`**
  - **Purpose:** The master evaluation script capable of running massive statistical stress tests.
  - **Contents:** Contains functions to generate thousands of random and clustered spawn scenarios. Calculates and prints out the final `Success Rate`, `Collision Rate`, and `Timeout Rate`. Can be run via command line (e.g., `python test_suite_step_A.py cluster 1k`).
- **`k_fold_validation.py`**
  - **Purpose:** A rigorous statistical tool to prove the model's reliability.
  - **Contents:** Runs a K-Fold cross-validation (usually 5 folds of 1,000 episodes). It calls `test_suite_step_A.py` multiple times to calculate the Mean and Standard Deviation of the success rates across 50,000 different simulated drones.
- **`evaluate_step_A.py`**
  - **Purpose:** A quick, dirty, and fast evaluation script.
  - **Contents:** Usually loads the model and runs just a few episodes. Often used for quick visual checks in PyGame rather than massive statistical logging.

## 🛠️ Diagnostics & Analysis
Tools built to figure out why the AI was failing during the early development stages.

- **`analyze_crashes.py`**
  - **Purpose:** A specialized debugging script used to diagnose the "funneling" problem at the goal.
  - **Contents:** Runs the environment silently and explicitly records the *(x, y)* coordinate of every single collision, printing the average distance to the goal when drones crash. This historically proved that 10 drones could not physically fit into a 0.5m radius simultaneously.
- **`analyze_experiments.py`** & **`inspect_tb.py`**
  - **Purpose:** Utilities to read TensorBoard log files.
  - **Contents:** Python scripts that parse the binary TensorBoard event files to extract numerical data out of the graphs (like episode reward means) for programmatic use.
- **`visualize_tests.py`**
  - **Purpose:** A dedicated rendering script.
  - **Contents:** Forces PyGame to open and visually runs specifically generated edge-cases so human researchers can watch the drones' behavior in slow-motion and diagnose visual anomalies.
- **`generate_basic_test_cases.py`**
  - **Purpose:** A scenario builder.
  - **Contents:** Procedurally generates deterministic starting positions for the drones (like perfect circles, lines, or tight clusters) and saves them as `.json` files in the `test_cases/` folder.

## 📚 Documentation & Results
Written archives of human knowledge regarding the project.

- **`Project_Summary_Step_A.md`**
  - **Purpose:** The complete, sequential story of Phase A.
  - **Contents:** Explains how the environment was built, explains the "Ghost Drone" bug that capped success at 21%, details the "Social Distancing" and "School Zone" reward fixes, and records the final 99.68% 5-Fold Validation statistics.
- **`trick_challenges/ghost_drone_bug.md`**
  - **Purpose:** A deep-dive post-mortem of a specific physics engine failure.
  - **Contents:** Thorough documentation of how completed drones were becoming "invisible walls" that killed other drones, and the specific code lines changed to fix it.
- **`README.md`**
  - **Purpose:** The old Phase A readme.
  - **Contents:** Archive of the repository's root readme before Phase B began.

## 📁 Folders / Directories

- **`models/`**: Holds the `.zip` files of the trained PyTorch neural networks (e.g., `step_A_foundation_model.zip`).
- **`test_cases/`**: Holds `.json` files containing exact XY coordinate spawns for deterministic, repeatable testing.
- **`ppo_swarm_tensorboard/`**: Holds binary log files generated by Stable-Baselines3 during training. These are read by launching the TensorBoard server.
