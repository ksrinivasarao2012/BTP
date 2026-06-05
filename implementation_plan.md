# Synchronize & Fix Map Generator Logic

This plan addresses the massive statistical biases and topological loopholes found in both the simulation environment and the analytics script.

## User Review Required

> [!WARNING]
> This will alter the map generation behavior in your RL training simulator (`swarm_env_step_B5_v15_master.py`). This means future training sessions will be slightly more difficult as the map generator will now accurately check diagonal paths and properly handle map boundary obstacles. Please confirm this is acceptable.

## Proposed Changes

### 1. `swarm_env_step_B5_v15_master.py` (The MARL Simulator)

*   **[MODIFY]**: `swarm_env_step_B5_v15_master.py`
    *   **Fix 4-Way Pathfinding**: In `_is_map_solvable()`, update the queue exploration step to use 8-way diagonal connections instead of 4-way cardinal directions. Drones move diagonally, so the solvability checker needs to understand diagonal corridors.
    *   **Fix Wall Hugging Loophole**: Update `_generate_obstacles()` to allow circle centers `cx` and `cy` to extend slightly closer to the grid boundaries instead of strictly `r` away from the edge, eliminating the free, empty safe-zone ring around the map. (We will use `random.uniform(r/2, WIDTH - r/2)` as a safe compromise).

### 2. `check_obstacle density.py` (The Statistical Sandbox)

*   **[MODIFY]**: `check_obstacle density.py`
    *   **Synchronize Start/Goal Logic**: Re-write `sample_safe()` so that the Start (`sc`) and Goal coordinates aren't randomly placed 7.0 meters apart, but are positioned at exactly opposite ends of the map just like `swarm_env_step_B5_v15_master.py` does. We will remove the flawed `sample_full()` logic completely.
    *   **Synchronize 8-Way Graph Pathfinding**: Mirror the 8-way BFS diagonal fix mentioned above.
    *   **Fix the Biased Infinite Loop**: If `generate_obstacles()` fails to reach the targeted density limit (e.g. at density 0.35) after 500 packing attempts, we currently return `None` and the script quietly throws it in the trash and loops forever. I will change this to treat generation failures as **"Unsolvable" trials**. This mathematically exposes when a density is literally impossible to create.
    *   **Mirror Wall Hugging Fix**: Copy the updated circle boundary logic so it strictly matches the PettingZoo RL environment.

## Verification Plan

### Manual Verification
- Execute `python check_obstacle density.py`.
- Ensure it successfully completes, generates the `.png` and `.csv` files without an infinite loop, and accurately plots the "Safe Sampling" Solvability dropdown. The graph should properly collapse to a much lower success rate at higher densities.
- Run a short check on `swarm_env_step_B5_v15_master.py` to ensure PettingZoo initialization does not break with the newly updated methods.
