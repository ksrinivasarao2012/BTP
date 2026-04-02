# Phase B Implementation Plan: Static Obstacle Avoidance (LiDAR Dodging)

## 🎯 Objective
Upgrade the Phase A environment to include 20-30 static obstacles. The swarm of 10 honest drones must learn to navigate from arbitrary start positions to the goal while autonomously dodging these obstacles using their 16-ray LiDAR readings. 
*Constraint:* 0 Traitors are introduced in this phase.

## 🏗️ 1. Environment Upgrades (`swarm_env_step_B.py`)

We will duplicate the stable `swarm_env_step_A.py` and modify its physics engine to handle static environmental geometry.

### A. Obstacle Generation (Dynamic Density Coverage)
Instead of hardcoding "25 obstacles of 1.5m radius", the generator will use a **Target Surface Area Density** (e.g., $15\%$ to $30\%$ of the map). 
- The generator will dynamically spawn a localized mix of Large Obstacles (e.g., $R=2.5m$), Medium Obstacles ($R=1.0m$), and Tiny Obstacles ($R=0.2m$) until the target density is reached.
- **Mathematical Constraint (The Choke-Point Verifier):** To ensure a map with massive obstacles isn't physically unsolvable, the generator will run a quick Breadth-First Search (BFS) or distance-matrix check upon instantiation. It will guarantee that at least one contiguous $0.6m$-wide channel exists from the start zone to the goal. If a generated layout is mathematically walled off, the seed is rejected and redrawn.
- **LiDAR Blind-Spot Ray-Casting:** Because we are now allowing tiny obstacles ($<0.5m$) which can slip between the standard 16 LiDAR rays, we will introduce a **Ray-Sweeping** mechanic. The 16 rays will jitter their angle during the 0.1s physics frame (effectively casting 32 or 64 rays and pooling the minimum distance) to ensure tiny obstacles cannot remain invisible.

### B. LiDAR Raycasting Overhaul
- The current $16$-ray LiDAR only returns the minimum normalized distance to:
  1. The 4 bounding walls.
  2. The other 9 agent drones.
- **Modification Required:** The raycasting loop must be upgraded to perform Line-Sphere Intersection math against all $N$ static obstacles. If an obstacle obscures a ray before it hits a wall/drone, the LiDAR must register the obstacle distance instead.

### C. Physical Collision Detection
- Add a new loop to the environment's `step()` physics check. 
- During every $10Hz$ frame, calculate the Euclidean distance from every drone to every static obstacle center.
- If $Distance \le (DroneRadius + ObstacleRadius)$, instantly trigger `terminated=True` and deliver the $-100$ collision penalty.

## 🧠 2. Observation Space Changes

The **Dual Observation Modality** remains structurally the same, but the data within the LiDAR array becomes exponentially more complex.

- **Local LiDAR Array (16 floats):** Will now dynamically spike as drones fly past obstacles. The network must learn to correlate a shortened LiDAR ray with the need for an immediate lateral thrust adjustment.
- **Global Broadcast Array:** Remains the exact same (relative goal vector, neighbor velocities).

*Crucial Note:* Because the state-space shape (number of inputs) is identical to Phase A, we **CAN** use the `step_A_foundation_model.zip` as the pre-trained starting point for Phase B!

## 🎓 3. Curriculum Training Strategy (`train_step_B.py`)

If we immediately drop 30 obstacles into the map, the Phase A model will likely panic and crash instantly. We need a Curriculum setup.

### Phase B1: The Sparse Field (1M Timesteps)
- Train the `step_A_foundation_model.zip` on an environment with only **5 to 10** small static obstacles.
- Goal: Teach the physical mapping between a shortened LiDAR ray and the $-100$ obstacle death consequence without overwhelming the agent.

### Phase B2: The Dense Forest (2M Timesteps)
- Ramp the environment up to **20 to 30** obstacles.
- Goal: Teach complex pathfinding. Drones will need to learn to temporarily fly *away* from the goal to maneuver around large blockade walls.

## 🧪 4. Evaluation and Verification (`test_suite_step_B.py`)

We will duplicate the test suite and upgrade it to handle obstacle rendering in PyGame.
We will require two new basic Edge Case JSONs:
1. **The Wall Test:** A massive line of obstacles blocking the direct path to the goal, forcing the drones to detour around the flanks.
2. **The Maze Test:** A dense grouping of staggered obstacles requiring S-curve flying maneuvers.

**Success Criteria:** 90%+ convergence success rate on the 1K Random Spawn test in the Dense Forest environment.
