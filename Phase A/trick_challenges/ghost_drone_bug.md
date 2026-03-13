# Physics Bug: The "Ghost Drone" Convergence Trap

## Discovered In: Phase 4, Step A
**Objective:** 10 Drones converge on a single $(x, y)$ coordinate.
**Symptom:** AI convergence hard-stuck at `~21%` success rate despite flawless kinematic training over 5 Million timesteps.

## Root Cause Analysis
The multi-agent physics engine (`swarm_env_step_A.py`) relied on the PettingZoo `self.agents` list to track which drones were "alive" in the simulation. When a drone reached the physical goal $(x,y)$, it was rewarded `+100` and immediately removed from `self.agents` (making it `terminated = True`).

Visually, the drone vanished from the PyGame renderer. 

Mathematically, however, its $(x,y)$ coordinates remained permanently hardcoded inside the `self.positions` Numpy Tensor. 

Because the collision loop and the 16-ray LiDAR physics raycaster iterated over `range(self.n_drones)` (which always looped from 0 to 9) regardless of the agent's life status, the very first fast drone to reach the goal accidentally left behind an **invisible, indestructible physical barrier** dead-center on the goal coordinate. 

When the other 9 slower drones attempted to reach the goal afterward, they literally collided with the invisible hitboxes of their already-successful teammates. They instantly died, received a `-50` penalty, and failed the episode. The only reason it reached 21% success was due to 2 or 3 drones arriving on the exact same discrete engine tick before the hitboxes locked down the goal point.

## Solution
1. **LiDAR Patch:** Explicitly check if the target index is still inside `self.agents` before calculating a physical ray intersection.
2. **Hitbox Patch:** Explicitly skip collision penalty distance-checks for neighbors that have already reached the goal and terminated.

*By ignoring successfully terminated agents, the goal zone physically clears up, allowing the remaining drones to flow in and "stack" sequentially.*
