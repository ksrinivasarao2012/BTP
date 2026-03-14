# Phase B: Project Structure Guide

This document provides a comprehensive overview of every file and folder within the Phase B directory.

## 📂 Directories

### `models/`
- **Purpose**: Stores the trained neural network weights (PPO models).
- **Contents**: 
  - `step_B_foundation_model.zip`: The final trained model for static obstacle avoidance.
  - `step_B1_sparse_field.zip`: Intermediate model trained on 5-10% intensity.
  - `step_B2_moderate_forest.zip`: Intermediate model trained on 10-15% intensity.

### `test_cases/`
- **Purpose**: Contains predefined geometric scenarios for deterministic testing.
- **Sub-folders**:
  - `basic/`: Scenarios like "Single Pillar" or "Narrow Corridor" for sanity checks.
  - `edge/`: Harder traps like "U-Shape Trap" or "Micro-Minefield" to test edge cases.

### `ppo_swarm_tensorboard/`
- **Purpose**: Log files for visualization in TensorBoard.
- **Contents**: Training metrics (reward curves, entropy, value loss). Use `tensorboard --logdir .` to view.

---

## 📜 Core Environment & Physics

### `swarm_env_step_B.py`
- **Purpose**: The primary simulation engine for Phase B.
- **Why it's used**: It defines the physics of the 20x20 field, the 10 drones, and the circular static obstacles.
- **Contains**: 
  - LiDAR Ray-Sweeping math.
  - Choke-Point Verifier (BFS) to ensure maps are solvable.
  - Collision detection and Reward function logic.

### `validate_physics_engine.py`
- **Purpose**: A standalone test suite for the environment itself.
- **Why it's used**: To verify that the environment code is bug-free before wasting hours on training.
- **Contains**: Automated tests for raycasting, spawn safety, and map solvability.

---

## 🎓 Training Scripts

### `train_step_B.py` (Optimized)
- **Purpose**: The high-performance training script using 12 CPU cores.
- **Why it's used**: Official script to train the model from scratch or Phase A warm-starts.
- **Contains**: 3-stage curriculum (Sparse → Moderate → Dense).

### `train_step_B_final.py`
- **Purpose**: A stable, single-threaded training script.
- **Why it's used**: Useful for debugging or training on systems with low CPU resources.

---

## 🧪 Evaluation & Visualization

### `test_suite_step_B.py`
- **Purpose**: Benchmark script to evaluate model performance.
- **Why it's used**: To get an objective "Success Rate" percentage against random and fixed scenarios.
- **Contains**: Logic to load JSON test cases and run them sequentially.

### `generate_test_cases_B.py`
- **Purpose**: Script to create the deterministic JSON test files.
- **Why it's used**: To regenerate the test scenarios if the file format or maps change.

---

## 📜 Documentation

### `Phase_B_Implementation_Plan.md`
- **Purpose**: Theoretical roadmap for building Phase B.

### `Phase_B_Test_Cases_Explanations.md`
- **Purpose**: Deep dive into the mathematical reasoning behind each test scenario.

### `Phase_B_Theoretical_Justification.md`
- **Purpose**: Academic justification for the chosen LiDAR range, density, and PPO hyperparameters.
