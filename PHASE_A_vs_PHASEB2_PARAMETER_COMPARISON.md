# Phase A vs Phase B2: Complete Parameter Comparison

**Document Purpose:** Identify all parameters that are identical vs different between Phase A (baseline, 0% obstacles) and Phase B2 (difficulty calibration, ~25% obstacles).

---

## 1. ENVIRONMENT CONSTANTS

| Category | Parameter | Phase A | Phase B2 | Status | Notes |
|----------|-----------|---------|---------|--------|-------|
| **Swarm Composition** | Number of drones | 10 | 10 | ✅ **SAME** | Core team size |
| | Number of traitors | 0 | 0 | ✅ **SAME** | No adversarial agents yet |
| | Number of honest drones | 10 | 10 | ✅ **SAME** | All cooperative |
| **Field Dimensions** | Field width (FIELD_W / WIDTH) | 20.0 units | 20.0 units | ✅ **SAME** | 20×20 arena |
| | Field height (FIELD_H / HEIGHT) | 20.0 units | 20.0 units | ✅ **SAME** | 20×20 arena |
| **Physics Timestep** | dt (time per step) | 0.1 seconds | 0.1 seconds | ✅ **SAME** | Synchronous simulation |
| **Episode Duration** | max_steps / MAX_STEPS | 600 steps | 1200 steps | ❌ **DIFFERENT** | B2 has 2× duration for obstacles |
| **Physical Time per Episode** | dt × max_steps | 60 seconds | 120 seconds | ❌ **DIFFERENT** | B2 doubles wall-clock time |
| **Drone Size** | drone_radius / DRONE_RADIUS | 0.15 units | 0.15 units | ✅ **SAME** | Physical collision radius |
| **Drone Collision Distance** | collision_threshold | 0.25 units (2 × radius) | 0.30 units (2 × radius) | ⚠️ **SLIGHTLY DIFFERENT** | B2 uses `2 * DRONE_RADIUS` exactly |
| **Maximum Velocity** | max_velocity / V_MAX | 2.0 units/sec | 1.2 units/sec | ❌ **DIFFERENT** | B2 slower for obstacle navigation |
| **Goal Reach Threshold** | goal_distance_threshold | 0.75 units | 0.6 units | ❌ **DIFFERENT** | B2 stricter goal criterion |

---

## 2. SENSING: LiDAR CONFIGURATION

| Category | Parameter | Phase A | Phase B2 | Status | Notes |
|----------|-----------|---------|---------|--------|-------|
| **LiDAR Array** | Number of rays | 16 rays | 72 rays | ❌ **DIFFERENT** | B2 has 4.5× denser sensing |
| | Ray angular spacing | 22.5° apart | 5° apart | ❌ **DIFFERENT** | B2 provides finer resolution |
| | Maximum range | 8.0 units | 8.0 units | ✅ **SAME** | Detection horizon same |
| | Normalization method | distance / 8.0 | distance / 8.0 | ✅ **SAME** | 0-1 normalized readings |
| **LiDAR Vectorization** | Implementation | Per-ray Python loop | NumPy vectorized | ❌ **DIFFERENT** | B2 optimized for 72 rays |
| | Sigmoid LUT pre-computation | No | Optional (v15+) | ❌ **DIFFERENT** | B2 v15 adds activation LUT |

---

## 3. SENSING: WHAT LiDAR DETECTS

| Category | Parameter | Phase A | Phase B2 | Status | Notes |
|----------|-----------|---------|---------|--------|-------|
| **Wall Detection** | Detects field boundaries | ✅ Yes | ✅ Yes | ✅ **SAME** | Essential for all phases |
| **Drone Detection** | Detects other honest drones | ✅ Yes | ✅ Yes | ✅ **SAME** | Collision avoidance |
| **Obstacle Detection** | Detects circular obstacles | ❌ No | ✅ Yes | ❌ **DIFFERENT** | B2's major new feature |
| | Obstacle detection method | N/A (no obstacles) | Ray-circle vectorized intersection | ❌ **DIFFERENT** | Fast geometric computation |

---

## 4. COMMUNICATION & NEIGHBOR STATE SHARING

| Category | Parameter | Phase A | Phase B2 | Status | Notes |
|----------|-----------|---------|---------|--------|-------|
| **Communication Range** | comm_range | N/A (ground truth) | 8.0 units | ❌ **DIFFERENT** | B2 has finite sensing range |
| **Neighbor State Sharing** | Enabled | ✅ Yes | ✅ Yes | ✅ **SAME** | Decentralized consensus |
| | Distance metric | Ground truth Euclidean | Ground truth Euclidean | ✅ **SAME** | Honest position data |
| | Maximum neighbors communicated | 9 (all others) | 9 (within COMM_RANGE) | ⚠️ **FUNCTIONALLY SAME** | Closest 9 per-drone in B2 |
| | Broadcast components (Phase A) | rel_pos, vel, is_active | N/A | ❌ **DIFFERENT** | Different encoding |
| | Broadcast components (B2) | rel_pos, vel, goal_dir, is_active | rel_pos, vel, goal_dir, is_active | ✅ **SAME** | Same in B2 |

---

## 5. OBSERVATION SPACE & FEATURE ENGINEERING

### Phase A Observation (67D total per drone)

```
[0:16]     LiDAR rays (16 values)
[16:18]    Self velocity (vx, vy) / max_velocity
[18:20]    Goal direction (unit vector)
[20:21]    Distance to goal / (diagonal of arena)
[21:22]    Heading (arctan2 of velocity)
[22:67]    Neighbor data (9 neighbors × 5 values):
           - rel_pos (2D): relative position / WIDTH
           - vel (2D): neighbor velocity / max_velocity
           - is_active (1D): {0.0, 1.0}
```

### Phase B2 Observation (151D total per drone, with 1661D global option)

```
[0:72]     LiDAR rays (72 values, normalized)
[72:79]    Own state (7 values):
           - vx / V_MAX, vy / V_MAX
           - x / FIELD_W, y / FIELD_H
           - goal_direction_x, goal_direction_y (Dijkstra pathfinding)
           - dist_to_goal (via shortest-path distance map)
[79:151]   Neighbor slots (9 neighbors × 8 values):
           - rel_x / COMM_RANGE, rel_y / COMM_RANGE
           - n_vx / V_MAX, n_vy / V_MAX
           - neighbor_dist_to_goal (via shortest-path)
           - neighbor_goal_direction_x, _y (Dijkstra)
           - active_flag (1.0 if in range, 0.0 otherwise)
           - Padded with zeros if < 9 neighbors in range
```

| Aspect | Phase A | Phase B2 | Status | Notes |
|--------|---------|---------|--------|-------|
| **Observation Dimension** | 67D | 151D | ❌ **DIFFERENT** | B2 adds obstacle info + goal pathfinding |
| **LiDAR component** | 16D | 72D | ❌ **DIFFERENT** | Density increase |
| **Own state component** | 6D (vel, to_goal, dist, heading) | 7D (vel, pos, goal_dir, goal_dist) | ⚠️ **PARTIALLY DIFFERENT** | B2 includes absolute position |
| **Neighbor component per drone** | 5D each | 8D each | ❌ **DIFFERENT** | B2 adds goal_dir and goal_dist per neighbor |
| **Total neighbors in observation** | 9 | 9 | ✅ **SAME** | Both support 9 neighbors |
| **Normalization of distances** | WIDTH (20.0) or max_velocity (2.0) | COMM_RANGE (8.0) for spatial, V_MAX (1.2) for velocity | ❌ **DIFFERENT** | Different normalization constants |
| **Goal direction encoding** | Simple unit vector (goal - pos) / dist | Dijkstra shortest-path direction | ❌ **DIFFERENT** | B2 uses topological pathfinding |
| **Distance-to-goal encoding** | Euclidean / diagonal | Shortest-path distance / 28.28 | ❌ **DIFFERENT** | B2 accounts for obstacles |

---

## 6. OBSTACLE CONFIGURATION & GEOMETRY

| Category | Parameter | Phase A | Phase B2 | Status | Notes |
|----------|-----------|---------|---------|--------|-------|
| **Obstacle Density** | target_density | 0.0 (none) | 0.25 (configurable) | ❌ **DIFFERENT** | B2's primary challenge |
| **Obstacle Type** | Shape | N/A | Circular | ❌ **DIFFERENT** | Convex obstacles |
| **Obstacle Size Distribution** | N/A | Small: 0.2–0.5 units (20%) | Large: 0.6–1.4 units (40%) | Huge: 1.5–2.5 units (40%) | ❌ **DIFFERENT** | Varied obstacle sizes |
| **Obstacle Placement Constraints** | Wall clearance | N/A | SPAWN_WALL_CLEARANCE (0.60) | ❌ **DIFFERENT** | Obstacles kept away from edges |
| | Goal exclusion radius | N/A | GOAL_EXCLUSION_RADIUS (0.70) | ❌ **DIFFERENT** | Clear path to goal zone |
| | Min inter-obstacle distance | N/A | Prevents overlap | ❌ **DIFFERENT** | Realistic spacing |
| **Pathfinding for Obstacles** | BFS solvability check | N/A (trivial) | Full 10-drone BFS path existence | ❌ **DIFFERENT** | Ensures all drones can reach goal |
| | Dijkstra shortest-path map | None | Precomputed per episode | ❌ **DIFFERENT** | Topological guidance |
| | BFS grid resolution | N/A | 0.2 units | ❌ **DIFFERENT** | Fine granularity for collision checking |

---

## 7. REWARD FUNCTION

### Phase A Reward Components

| Component | Formula / Value | Coefficient | Notes |
|-----------|-----------------|-------------|-------|
| **R_goal: Potential Field** | 10.0 × (0.995 × (−dist) − (−old_dist)) | 10.0 | Progress toward goal |
| **R_time: Existential Penalty** | −0.05 | −0.05 | Per-step time cost |
| **R_group: Cohesion** | neighbors_in_range × 0.01 | 0.01 | Stay near swarm (0.6–4.0m range) |
| **R_cluster: COM Expansion** | clip(delta_com × 30.0, −3.0, 3.0) | 30.0 | Prevent clustering |
| **R_school: Speed Limit (clustered)** | −((speed − safe_speed) / v_max)² × count × 5.0 | −5.0 per neighbor | Damping when tangled |
| **R_social: Social Distancing** | −(0.4 − dist) × 50.0 | −50.0 | Penalize < 0.4m separation |
| **R_success: Goal Reached** | +100.0 + 50.0/(1 + speed) | +100 base | Bonus for smooth arrival |
| **R_collision_drone: Drone Collision** | −50.0 | −50.0 | Inter-drone crash penalty |
| **R_collision_wall: Wall Collision** | −100.0 | −100.0 | Boundary violation penalty |
| **Safe speed threshold (school zone)** | 0.35 × max_velocity = 0.7 units/sec | 35% | Speed limit when clustered |
| **Near-miss distance** | 0.4 units | N/A | Social distancing zone |

### Phase B2 Reward Components

| Component | Formula / Value | Coefficient | Notes |
|-----------|-----------------|-------------|-------|
| **R_goal: Potential Field (PBRS)** | PROGRESS_SCALE × (old_d − GAMMA × new_d) | 5.0 | Compensated for slower V_MAX |
| | PROGRESS_SCALE = 5.0 | 5.0 | Adjusted for V_MAX=1.2 |
| | GAMMA_SHAPING = 0.99 | 0.99 | Matches PPO discount |
| **R_time: Step penalty** | −0.02 | −0.02 | Per-step cost (lower than Phase A) |
| **R_group: Cohesion** | neighbors_in_range × 0.01 | 0.01 | Same as Phase A (0.6–4.0m) |
| **R_cluster: COM Expansion** | clip(delta_com × 30.0, −3.0, 3.0) | 30.0 | Same as Phase A |
| **R_school: Speed Limit** | −((speed − safe_speed) / V_MAX)² × count × 2.0 | −2.0 per neighbor | Reduced from Phase A |
| **R_near_miss: Penalize closeness** | −NEAR_MISS_PENALTY × (NEAR_MISS_DIST − sep_dist) | −10.0 | Explicit near-miss zone (0.5m) |
| **R_dense_sep: Obstacle-induced separation** | −0.05 × ((0.6 − dist)²) | −0.05 | Only active when density > 0 |
| **R_success: Goal Reached** | +50.0 | +50.0 | Lower base than Phase A |
| **R_collision_drone: Drone Collision** | −10.0 | −10.0 | Reduced from Phase A |
| **R_collision_wall: Wall Collision** | −15.0 | −15.0 | Reduced from Phase A |
| **R_collision_obstacle: Obstacle Hit** | −15.0 | −15.0 | New penalty in B2 |
| **Safe speed threshold** | 0.35 × V_MAX = 0.42 units/sec | 35% | Same percentage as A, lower absolute |
| **Near-miss distance** | 0.5 units | N/A | Larger zone than Phase A (0.4) |

| Reward Aspect | Phase A | Phase B2 | Status | Notes |
|---------------|---------|---------|--------|-------|
| **Overall Structure** | Multi-term potential-based | Potential-based PBRS + proximity penalties | ✅ **SAME** | Both use similar approach |
| **R_goal scaling** | 10.0 × potential | 5.0 × potential | ❌ **DIFFERENT** | B2 compensates for V_MAX |
| **Existential penalty** | −0.05 | −0.02 | ❌ **DIFFERENT** | B2 is gentler |
| **Cohesion reward (R_group)** | +0.01 per neighbor in range | +0.01 per neighbor in range | ✅ **SAME** | Identical |
| **COM expansion (R_cluster)** | ±30.0 (clip to ±3.0) | ±30.0 (clip to ±3.0) | ✅ **SAME** | Identical |
| **School zone speed penalty** | −5.0 per neighbor | −2.0 per neighbor | ❌ **DIFFERENT** | B2 is less harsh |
| **Social distancing penalty** | −50.0 × gap | Implicit in near-miss | ❌ **DIFFERENT** | B2 uses explicit NEAR_MISS |
| **Collision penalties** | Drone: −50, Wall: −100 | Drone: −10, Wall: −15, Obstacle: −15 | ❌ **DIFFERENT** | B2 penalties much smaller |
| **Success reward** | +100 + 50/(1+speed) | +50.0 flat | ❌ **DIFFERENT** | B2 simpler, lower |
| **Obstacle separation** | N/A | −0.05 × ((0.6 − dist)²) | ❌ **DIFFERENT** | B2-specific dense separation |

---

## 8. TRAINING CONFIGURATION

### Phase A Training (train_step_A.py)

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Total training timesteps** | 1,000,000 | 1M steps |
| **Algorithm** | PPO (Stable-Baselines3) | Multi-agent via parameter sharing |
| **Learning rate** | 5e-5 | Very low for fine-tuning |
| **Entropy coefficient** | 0.005 | Low entropy for exploitation |
| **Curriculum strategy** | 80% clustered + 20% random spawns | No obstacle progression |
| **Model checkpoint** | Pre-loaded "step_A_foundation_model" | Transfer learning from prior run |
| **Reset num timesteps** | False | Continue from checkpoint |
| **TensorBoard logging** | ./ppo_swarm_tensorboard/ | Training curves |

### Phase B2 Training (train.py)

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Total training timesteps** | 3,000,000 (per stage) | Curriculum-dependent; baseline is 3M for stage 0 |
| **Algorithm** | PPO (Stable-Baselines3) | Via MAPPOPolicy custom network |
| **Learning rate** | 3e-4 | Higher than Phase A (2× exploration needed) |
| **n_steps** | 2048 | Rollout buffer size per update |
| **Batch size** | 256 | Mini-batch for gradient steps |
| **n_epochs** | 4 | PPO inner-loop training epochs |
| **Gamma (discount factor)** | 0.99 | Long-horizon value estimation |
| **GAE lambda** | 0.95 | Generalized Advantage Estimation smoothing |
| **Clip range (epsilon)** | 0.2 | PPO probability ratio clipping |
| **Entropy coefficient** | 0.01 | Higher than Phase A for exploration |
| **Value function coefficient** | 0.5 | Critic loss weight |
| **Max grad norm** | 0.5 | Gradient clipping magnitude |
| **Curriculum stages** | 6 stages: 0.0, 0.05, 0.10, 0.15, 0.20, 0.25 | Density progression |
| **Steps per stage** | 3,000,000 | 18M total steps |
| **Logging interval** | 10,000 steps | Metrics recorded every 10K |
| **Model save strategy** | Best + per-stage checkpoints | Tracks best at each density |
| **TensorBoard logging** | ./logs/ | Training curves |

| Training Aspect | Phase A | Phase B2 | Status | Notes |
|-----------------|---------|---------|--------|-------|
| **Algorithm** | PPO | PPO | ✅ **SAME** | Same RL backbone |
| **Framework** | Stable-Baselines3 | Stable-Baselines3 | ✅ **SAME** | Same library |
| **Learning rate** | 5e-5 | 3e-4 | ❌ **DIFFERENT** | B2 is 6× higher |
| **Entropy coefficient** | 0.005 | 0.01 | ❌ **DIFFERENT** | B2 encourages exploration more |
| **Gamma** | Not explicitly set | 0.99 | ⚠️ **DIFFERENT** | A uses SB3 default (0.99); B2 explicit |
| **Curriculum structure** | Spawn distribution (80/20 split) | Density progression (6 stages) | ❌ **DIFFERENT** | A trains on varied start; B2 on obstacles |
| **Total steps** | 1M | 3M per curriculum stage (18M baseline) | ❌ **DIFFERENT** | B2 much longer training |
| **Checkpoint strategy** | Single pre-loaded foundation model | Multi-stage progressive training | ❌ **DIFFERENT** | B2 curriculum-aware |

---

## 9. NETWORK ARCHITECTURE

### Phase A Network (via SB3 MlpPolicy)

- **Type**: Standard Multi-Layer Perceptron
- **Input**: 67D observation
- **Architecture**: SB3 default MlpPolicy
- **Output**: Actor (2D action) + Critic (1D value)
- **Feature extraction**: Implicit in first dense layer
- **Comments**: Simple dense network, no special structure

### Phase B2 Network (MAPPOPolicy with SwarmFeaturesExtractor)

- **Type**: Custom feature extractor + Actor-Critic heads
- **Input**: 1661D observation (151D local + 1510D global)
- **Feature Extractor** (SwarmFeaturesExtractor):
  - **LiDAR encoder**: 72D → 128D → 64D (LayerNorm + Tanh)
  - **Own state encoder**: 7D → 32D (LayerNorm + Tanh)
  - **Neighbor encoder**: 9 × 8D slots → mean-pool → 32D (permutation-invariant)
  - **Fusion**: Concatenate (64 + 32 + 32) → 128D output
  - **Activation**: Tanh, LayerNorm (for stability)
- **Actor head**: 128D input → outputs 2D continuous action
- **Critic head**: 128D input → outputs 1D scalar value
- **Key design**: Modular encoders + mean pooling for neighbor robustness

| Architecture Aspect | Phase A | Phase B2 | Status | Notes |
|---|---|---|---|---|
| **Base network type** | SB3 MlpPolicy | Custom MAPPOPolicy | ❌ **DIFFERENT** | B2 specialized for swarm |
| **Feature extractor** | Implicit in SB3 | Explicit SwarmFeaturesExtractor | ❌ **DIFFERENT** | B2 has component-wise processing |
| **LiDAR processing** | Dense layer | Conv-like: 72→128→64 | ❌ **DIFFERENT** | B2 deeper, wider |
| **Own state processing** | Dense layer | Dedicated: 7→32 | ❌ **DIFFERENT** | B2 modular |
| **Neighbor processing** | Dense layer | Mean-pooling (permutation-invariant) | ❌ **DIFFERENT** | B2 robust to neighbor ordering |
| **Normalization** | None specified | LayerNorm + Tanh | ❌ **DIFFERENT** | B2 uses modern techniques |
| **Total feature dim** | Implicit (SB3 default ~64) | Explicit 128D | ⚠️ **DIFFERENT** | B2 larger feature space |

---

## 10. SUMMARY: SAME vs DIFFERENT

### ✅ **IDENTICAL PARAMETERS** (Will transfer well)

1. **n_drones** = 10
2. **num_traitors** = 0 (cooperative setting)
3. **Field dimensions** = 20.0 × 20.0
4. **dt** = 0.1 seconds
5. **LiDAR max range** = 8.0 units
6. **Drone radius** = 0.15 units
7. **Cohesion reward coefficient** = 0.01 per neighbor
8. **COM expansion reward scale** = 30.0
9. **Safe speed threshold percentage** = 35% of max velocity
10. **PPO algorithm framework** = Stable-Baselines3
11. **Gamma discount factor** ≈ 0.99 (both)
12. **Communication via ground truth** = Both share real neighbor state

### ❌ **SIGNIFICANTLY DIFFERENT** (Will require retraining)

1. **max_steps**: 600 → 1200 (2× longer episodes)
2. **max_velocity**: 2.0 → 1.2 (40% slower)
3. **LiDAR rays**: 16 → 72 (4.5× denser sensing)
4. **Observation size**: 67D → 151D (2.3× larger)
5. **Goal reach distance**: 0.75 → 0.6 units (stricter)
6. **Obstacle configuration**: 0% → 25% density (major complexity)
7. **Reward scaling**: 10.0 → 5.0 for goal reward
8. **Collision penalties**: Much smaller in B2 (−50 → −10 for drone)
9. **Learning rate**: 5e-5 → 3e-4 (6× higher)
10. **Entropy coefficient**: 0.005 → 0.01 (more exploration)
11. **Network architecture**: Dense MLP → Custom SwarmFeaturesExtractor
12. **Training duration**: 1M → 3M steps per curriculum stage
13. **Curriculum strategy**: Spawn distribution → Obstacle density progression
14. **Pathfinding**: Euclidean → Dijkstra shortest-path (for goal direction)

### ⚠️ **FUNCTIONALLY SIMILAR BUT DIFFERENT VALUES**

1. **Communication range**: N/A (ground truth) → 8.0 units (finite)
2. **Neighbor slots**: Same count (9) but different encoding (5D → 8D per neighbor)
3. **Speed limits**: Same 35% threshold, different absolute values
4. **Social distancing**: Same concept, different implementations
5. **Reward structure**: Similar approach but different coefficients/triggers

---

## 11. CRITICAL IMPLICATIONS FOR TRANSFER LEARNING

### **Can Phase A models be directly used in Phase B2?**

**Short answer: NO** — too many fundamental changes.

**Key blockers:**

1. **Observation mismatch**: 67D → 151D (incompatible input shape)
2. **Network architecture**: SB3 MlpPolicy → SwarmFeaturesExtractor (different)
3. **Reward function**: Coefficients and penalties changed (different incentives)
4. **Action consequence**: Slower drones + longer episodes (different dynamics)
5. **Pathfinding**: Euclidean directions → Dijkstra paths (different goal encoding)

### **What will transfer successfully:**

1. ✅ **Core navigation intent**: Moving toward goal while avoiding collision
2. ✅ **Swarm coordination**: Cohesion + COM expansion + school zone remain
3. ✅ **Team composition**: Same 10-drone setup
4. ✅ **Sensing modality**: Still LiDAR-based (just more rays)
5. ✅ **Communication**: Ground truth neighbor state sharing

### **Recommendation:**

- **Do NOT attempt zero-shot transfer** from Phase A model to B2
- **DO use Phase A insights** for reward shaping, spawn strategies, and architecture design
- **DO fine-tune B2 from scratch** with longer training (curriculum helps)
- **DO leverage curriculum learning** (density progression) to handle obstacle complexity

---

## 12. FILE LOCATIONS & IMPLEMENTATION DETAILS

### Phase A Core Files
- Environment: `Phase A/Hardened_Baseline/swarm_env_step_A.py` (361 lines)
- Training: `Phase A/Hardened_Baseline/train_step_A.py` (121 lines)
- Test/Validation: `Phase A/Hardened_Baseline/test_suite_step_A.py`, `k_fold_validation.py`

### Phase B2 Core Files
- Environment: `PhaseB2/swarm_env.py` (864 lines)
- Gym Wrapper: `PhaseB2/gym_wrapper.py` (vectorized interface)
- Network: `PhaseB2/networks.py` (custom feature extractor)
- Training: `PhaseB2/train.py` (curriculum-aware training loop)
- Evaluation: `PhaseB2/evaluate.py`, `benchmark_cores.py`

---

## 13. PARAMETER QUICK-REFERENCE TABLE

| Parameter | Phase A | Phase B2 | Match |
|-----------|---------|---------|-------|
| N_drones | 10 | 10 | ✅ |
| Field size | 20×20 | 20×20 | ✅ |
| dt | 0.1 | 0.1 | ✅ |
| max_steps | 600 | 1200 | ❌ |
| max_velocity | 2.0 | 1.2 | ❌ |
| LiDAR rays | 16 | 72 | ❌ |
| LiDAR range | 8.0 | 8.0 | ✅ |
| obs_dim | 67 | 151 | ❌ |
| drone_radius | 0.15 | 0.15 | ✅ |
| goal_threshold | 0.75 | 0.6 | ❌ |
| obstacle_density | 0.0 | 0.25 | ❌ |
| lr | 5e-5 | 3e-4 | ❌ |
| ent_coef | 0.005 | 0.01 | ❌ |
| gamma | 0.99* | 0.99 | ✅ |
| r_goal_scale | 10.0 | 5.0 | ❌ |
| r_cohesion | 0.01 | 0.01 | ✅ |
| r_collision_drone | -50 | -10 | ❌ |
| safe_speed_pct | 35% | 35% | ✅ |
| network | MlpPolicy | MAPPOPolicy | ❌ |

---

**Document Generated:** June 13, 2026  
**Last Updated:** Analysis based on latest codebase  
**Scope:** Phase A (v10 Hardened Baseline) vs Phase B2 (v6 Density Sweep)
