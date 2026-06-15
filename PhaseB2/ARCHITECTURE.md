# Architecture Deep Dive
## Every Component Explained

---

## 1. The Big Picture

```
┌─────────────────────────────────────────────────────────────────┐
│                         ENVIRONMENT                             │
│   10 drones navigate 20×20m arena to shared goal               │
│   Arena has obstacles (density 0.05 → 0.25 across curriculum)  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
              Each drone produces a 151D observation
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                       GYM WRAPPER                               │
│   Stacks all 10 drones' 151D obs → 1510D global state          │
│   Concatenates: [local 151D || global 1510D] = 1661D            │
│   Feeds 1661D to SB3's PPO as a single observation              │
└─────────────────────────┬───────────────────────────────────────┘
                          │ 1661D observation
                          ▼
┌──────────────────────── MAPPO POLICY ───────────────────────────┐
│                                                                  │
│   ┌──────────────────────────┐  ┌───────────────────────────┐  │
│   │      ACTOR PATH          │  │      CRITIC PATH           │  │
│   │  (used at train + test)  │  │  (used at TRAINING ONLY)  │  │
│   │                          │  │                            │  │
│   │  obs[:151]  →  extractor │  │  obs[151:] → extractor    │  │
│   │     (86,400 params)      │  │    (939,648 params)        │  │
│   │           ↓              │  │          ↓                 │  │
│   │        128D features     │  │       128D features        │  │
│   │           ↓              │  │          ↓                 │  │
│   │  actor_mlp: 128→64 Tanh  │  │  critic_mlp: 128→64 Tanh  │  │
│   │           ↓              │  │          ↓                 │  │
│   │      action_net: 64→2    │  │   value_net: 64→1          │  │
│   │  Output: (vx, vy) action │  │  Output: scalar V(s)       │  │
│   └──────────────────────────┘  └───────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. The 151D Observation (What One Drone Sees)

Every drone gets exactly 151 numbers describing its world.

```
Index     Size     What it contains
──────    ────     ────────────────────────────────────────────────
0:72      72D      LiDAR rays
72:79      7D      Own state (position, velocity, goal)
79:151    72D      Neighbor slots (9 neighbors × 8D each)

TOTAL:   151D
```

### 2.1 LiDAR Rays — 72D (indices 0 to 71)

72 rays fired outward from the drone in all directions.
Each ray value = distance to nearest obstacle or wall, divided by 8.0 (max range).

```
Value = 1.0  → nothing in that direction within 8m (clear)
Value = 0.0  → obstacle right next to drone in that direction
Value = 0.5  → obstacle 4m away in that direction
```

Rays are arranged uniformly:
```
Ray 0:   0°    (east / right)
Ray 18: 90°    (north / up)
Ray 36: 180°   (west / left)
Ray 54: 270°   (south / down)
Ray 71: 355°   (almost back to east)
```

The drone cannot tell the difference between a wall and an obstacle from
LiDAR alone — both return the same distance reading.

### 2.2 Own State — 7D (indices 72 to 78)

```
Index    Content             Normalization
─────    ───────             ─────────────────────────────
72       vx (velocity x)     ÷ 1.2   → range roughly [-1, 1]
73       vy (velocity y)     ÷ 1.2   → range roughly [-1, 1]
74       x position          ÷ 20.0  → range [0, 1]
75       y position          ÷ 20.0  → range [0, 1]
76       goal_dx             ÷ 20.0  → signed direction to goal
77       goal_dy             ÷ 20.0  → signed direction to goal
78       dist_to_goal        ÷ 28.28 → range [0, 1] (28.28 = diagonal)
```

All values normalized so the neural network sees numbers in a consistent range.
Raw pixel or meter values would make learning unstable.

### 2.3 Neighbor Slots — 72D (indices 79 to 150)

9 slots, one per possible neighbor. Each slot is 8D.

```
Slot N starts at index: 79 + N * 8       (N = 0 to 8)

Within each 8D slot:
  [0]  rel_x          relative x position of neighbor  ÷ 20.0
  [1]  rel_y          relative y position of neighbor  ÷ 20.0
  [2]  neighbor vx    neighbor's x velocity            ÷ 1.2
  [3]  neighbor vy    neighbor's y velocity            ÷ 1.2
  [4]  neighbor dist  distance to neighbor             ÷ 28.28
  [5]  goal_dx        neighbor's x direction to goal   ÷ 28.28
  [6]  goal_dy        neighbor's y direction to goal   ÷ 28.28
  [7]  active_flag    1.0 if neighbor alive, 0.0 if done/dead
```

**In Phase 1:** All 72D are ZERO. Communication is disabled.
Drones are blind to each other except via LiDAR (they appear as obstacles).

**In Phase 2:** Real data fills these slots.
Drones can see each other's positions, velocities, and goal directions.

---

## 3. The 1661D Combined Observation (What SB3 Sees)

SB3's PPO accepts one observation per "agent" per step.
We use a trick to feed both local and global information in one vector.

```
Position   Size     Content
────────   ────     ───────────────────────────────────────────────
0:151      151D     Local observation of THIS drone (see Section 2)
151:302    151D     Drone 0's local observation
302:453    151D     Drone 1's local observation
453:604    151D     Drone 2's local observation
604:755    151D     Drone 3's local observation
755:906    151D     Drone 4's local observation
906:1057   151D     Drone 5's local observation
1057:1208  151D     Drone 6's local observation
1208:1359  151D     Drone 7's local observation
1359:1510  151D     Drone 8's local observation
1510:1661  151D     Drone 9's local observation

TOTAL: 1661D
```

The 1510D global block (obs[151:]) is all 10 drones stacked in order 0 to 9.
This includes the current drone too — that's fine, there's redundancy by design.

**Why this design works:**

The actor extractor reads only `obs[:151]`. The last 1510D are physically in
the tensor but the actor never looks at them. They are mathematically dead
weight for the actor.

The critic extractor reads only `obs[151:]`. The first 151D are ignored.

At evaluation, only the actor runs (SB3 calls `get_distribution(obs)`).
The critic never executes. The 1510D in the observation is still there but
nothing reads it. No wasted computation.

---

## 4. Actor Extractor — SwarmActorExtractor (86,400 params)

Takes 1661D input, slices first 151D, runs it through SwarmFeaturesExtractor.

```
Input: obs (batch, 1661)
         │
         │  local_obs = obs[:, :151]       ← slice, ignore the rest
         ▼
┌─────────────────────────────────────────────────────────────┐
│               SwarmFeaturesExtractor                        │
│                                                             │
│  Split into three parts:                                    │
│                                                             │
│  lidar     = obs[:, 0:72]      shape: (batch, 72)          │
│  own_state = obs[:, 72:79]     shape: (batch, 7)           │
│  neighbors = obs[:, 79:151]    shape: (batch, 72)          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  LiDAR Encoder                                       │  │
│  │  Linear(72 → 128) → LayerNorm(128) → Tanh            │  │
│  │  Linear(128 → 64) → LayerNorm(64)  → Tanh            │  │
│  │  Output: (batch, 64)                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Own State Encoder                                   │  │
│  │  Linear(7 → 32) → LayerNorm(32) → Tanh               │  │
│  │  Output: (batch, 32)                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Neighbor Encoder                                    │  │
│  │  Reshape: (batch, 72) → (batch, 9, 8)                │  │
│  │  Linear(8 → 32) → Tanh    [per slot, 9 times]        │  │
│  │  Multiply by active_flag  [zero out dead neighbors]  │  │
│  │  Sum over 9 slots, divide by num_active              │  │
│  │  Linear(32 → 32) → LayerNorm(32) → Tanh              │  │
│  │  Output: (batch, 32)                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Fusion: Concat [64, 32, 32] = (batch, 128)                │
│  Linear(128 → 256) → LayerNorm(256) → Tanh                 │
│  Linear(256 → 128) → LayerNorm(128) → Tanh                 │
│                                                             │
│  Output: (batch, 128)   ← features_dim                     │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
  actor_mlp: Linear(128 → 64) → Tanh
         │
         ▼
  action_net: Linear(64 → 2) + learnable log_std
         │
         ▼
  Output: (vx, vy) sampled from Gaussian
```

**Parameter breakdown:**

```
LiDAR encoder:
  Linear(72, 128):   72×128 + 128    =   9,344
  LayerNorm(128):    128×2            =     256
  Linear(128, 64):   128×64 + 64     =   8,256
  LayerNorm(64):     64×2             =     128
  Subtotal:                               18,000 (approx)

Own state encoder:
  Linear(7, 32):     7×32 + 32       =     256
  LayerNorm(32):     32×2             =      64
  Subtotal:                                  320

Neighbor slot encoder:
  Linear(8, 32):     8×32 + 32       =     288
  Neighbor fusion:
    Linear(32, 32):  32×32 + 32      =   1,056
    LayerNorm(32):   32×2             =      64
  Subtotal:                                1,408

Fusion:
  Linear(128, 256):  128×256 + 256   =  33,024
  LayerNorm(256):    256×2            =     512
  Linear(256, 128):  256×128 + 128   =  33,024
  LayerNorm(128):    128×2            =     256
  Subtotal:                               66,816

Actor MLP head:
  Linear(128, 64):   128×64 + 64     =   8,256
  (this is actor_mlp in MAPPOPolicy, separate from extractor)

TOTAL (extractor only): ~86,400
```

---

## 5. Critic Extractor — SwarmCriticExtractor (939,648 params)

Takes 1661D input, slices last 1510D (global state), runs a plain MLP.
No split, no pooling — just a wide MLP over all drone data at once.

```
Input: obs (batch, 1661)
         │
         │  global_state = obs[:, 151:]    ← slice 1510D
         ▼
┌─────────────────────────────────────────────────────────────┐
│               SwarmCriticExtractor                          │
│                                                             │
│  Linear(1510 → 512) → LayerNorm(512) → Tanh                │
│  Linear(512  → 256) → LayerNorm(256) → Tanh                │
│  Linear(256  → 128) → LayerNorm(128) → Tanh                │
│                                                             │
│  Output: (batch, 128)                                       │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
  critic_mlp: Linear(128 → 64) → Tanh
         │
         ▼
  value_net: Linear(64 → 1)
         │
         ▼
  Output: scalar V(global_state)
```

**Parameter breakdown:**

```
Linear(1510, 512):  1510×512 + 512  = 773,632
LayerNorm(512):     512×2            =   1,024
Linear(512, 256):   512×256 + 256   = 131,328
LayerNorm(256):     256×2            =     512
Linear(256, 128):   256×128 + 128   =  32,896
LayerNorm(128):     128×2            =     256
───────────────────────────────────────────────
Extractor total:                      939,648   (verified by param count)

critic_mlp:
  Linear(128, 64):  128×64 + 64     =   8,256

value_net:
  Linear(64, 1):    64×1 + 1        =      65

FULL CRITIC TOTAL:                    947,969   (~948K)
```

**Why a plain MLP (no split encoding) for the critic?**

The actor needs the split encoder because its job is to ACT — it must interpret
each sensor component correctly. Permutation invariance matters for the actor.

The critic's job is to ESTIMATE value — it just needs to compress 1510D → 1 number
as accurately as possible. A plain MLP can find any pattern in the data.
The simpler the architecture the less that can go wrong during training.

---

## 6. MAPPOPolicy — How Actor and Critic Connect

```python
# During a training step (forward pass):
actor_features  = SwarmActorExtractor(obs)    # uses obs[:151]
critic_features = SwarmCriticExtractor(obs)   # uses obs[151:]

actor_latent  = actor_mlp(actor_features)     # 128 → 64
critic_latent = critic_mlp(critic_features)   # 128 → 64

values       = value_net(critic_latent)        # 64 → 1
distribution = action_dist(actor_latent)       # 64 → Gaussian(2D)
actions      = distribution.sample()           # 2D action
log_prob     = distribution.log_prob(actions)  # scalar
```

```python
# At evaluation (get_distribution called by SB3 predict()):
actor_features = SwarmActorExtractor(obs)      # only this runs
actor_latent   = actor_mlp(actor_features)     # 128 → 64
distribution   = action_dist(actor_latent)     # Gaussian
action         = distribution.mode()           # deterministic: take mean
```

The critic extractor and critic_mlp and value_net are NEVER called at evaluation.

---

## 7. The Gym Wrapper — How 1661D Gets Built

Every 10 drone actions, SwarmEnv steps once and returns 10 new observations.
The gym wrapper stores all 10 observations and combines them.

```python
def _get_global_obs(self):
    # Stack all 10 drones' latest 151D obs → 1510D
    global_obs = np.zeros(10 * 151)
    for drone_id in range(10):
        obs = self._last_obs.get(drone_id, np.zeros(151))
        global_obs[drone_id * 151 : (drone_id+1) * 151] = obs
    return global_obs     # shape: (1510,)

def _combined_obs(self, drone_id):
    local  = self._last_obs.get(drone_id, np.zeros(151))
    global = self._get_global_obs()                        # (1510,)
    return np.concatenate([local, global])                 # (1661,)
```

**The state machine (how 10 drones share one SB3 env):**

SB3 calls `step()` once per "agent step". We have 10 drones but one env.
Solution: cycle through drones 0–9, collecting one action per call.
On the 10th call, apply all 10 actions to SwarmEnv at once.

```
step() call 1  → collect action for drone 0, return drone 1's obs
step() call 2  → collect action for drone 1, return drone 2's obs
...
step() call 9  → collect action for drone 8, return drone 9's obs
step() call 10 → collect action for drone 9
                  → execute all 10 actions in SwarmEnv
                  → get new observations from SwarmEnv
                  → return drone 0's new obs, total reward
```

Reward returned is the SUM of all 10 drones' rewards from that SwarmEnv step.

---

## 8. SwarmEnv — The Physics Layer

What actually moves the drones and checks for collisions.

```
ARENA
┌──────────────────────────────────────┐
│    goal (fixed position)             │
│      ●                               │
│                                      │
│  ████   ██   drone positions         │
│           ●  ●                       │
│   ██    ●  ●                         │
│        ████  ●   ●                   │
│                                      │
│           ●  ●                       │
└──────────────────────────────────────┘
  20m × 20m, obstacles as rectangles
```

**Per-step physics:**

```
1. Receive action (vx, vy) for each drone
2. Clamp to [-1, 1], multiply by V_MAX = 1.2 m/s
3. Integrate position: x += vx * dt,  y += vy * dt   (dt = 0.1s)
4. Check collisions:
   - drone vs wall    → terminate drone, reward -2.0
   - drone vs obstacle → terminate drone, reward -2.0
   - drone vs drone   → terminate both,  reward -1.0 each
   - drone at goal    → terminate drone, reward +20.0
5. Cast 72 LiDAR rays from each surviving drone
6. Build 151D observation for each surviving drone
7. Add distance progress reward: +delta × 0.3
8. Add step penalty: -0.005
```

**Obstacle generation:**

Obstacles are placed at episode reset using a BFS-verified algorithm.
The algorithm guarantees at least one clear path from spawn to goal.

```
1. Place obstacles randomly at target density
2. Run BFS from goal to all spawn points
3. If any spawn is unreachable → regenerate
4. Keep trying until a valid map is found
5. Obstacles use cluster placement: choose a center, place 3-6 nearby
```

---

## 9. Reward Structure — Why Each Term Exists

```
Term                  Value      Purpose
────────────────────  ─────────  ──────────────────────────────────────────
step_penalty          -0.005     Pressure to be efficient, not idle
distance_progress     +Δ × 0.3  Reward moving toward goal (weak signal)
goal_reached          +20.0      Primary objective — make this dominate
wall_collision        -2.0       Hard boundary: walls kill you
obstacle_collision    -2.0       Hard boundary: obstacles kill you
drone_collision       -1.0       Soft boundary: avoid peers
```

**Why distance_progress is 0.3 not 2.0:**

Old value (2.0) created an exploit:
```
Rush 50 steps at max speed toward goal, hit obstacle:
  progress reward: ~0.12 m/step × 2.0 × 50 = +12.0
  step penalty:    -0.005 × 50              = -0.25
  obstacle hit:                               -2.0 (old) / -1.0 (old)
  Net: +12.0 - 0.25 - 1.0 = +10.75  (POSITIVE — exploit pays off)
```

New value (0.3):
```
Rush 50 steps at max speed toward goal, hit obstacle:
  progress reward: ~0.12 × 0.3 × 50 = +1.80
  step penalty:    -0.005 × 50       = -0.25
  obstacle hit:                        -2.0
  Net: 1.80 - 0.25 - 2.0 = -0.45  (NEGATIVE — exploit broken)
```

Only way to get positive total return: reach goal (+20.0).

---

## 10. Parameter Sharing — One Policy, 10 Drones

All 10 drones share the same neural network weights.
This is standard MARL practice for homogeneous agents.

```
Training:
  Drone 0 obs → same MAPPOPolicy → action 0
  Drone 1 obs → same MAPPOPolicy → action 1
  ...
  Drone 9 obs → same MAPPOPolicy → action 9

  All 10 (obs, action, reward, next_obs) tuples go into the SAME replay buffer
  One gradient update improves behavior for ALL drones
```

**Benefit:** 10× more training data per environment step.
A single episode gives 10 drones × 1200 max steps = 12,000 training transitions.

**Requirement:** All drones must use the same observation format.
This is why we normalize everything — Drone 3 at position (5,10) and Drone 7
at position (15,3) both produce obs in the same [-1,1] range. The network
sees them as equivalent situations.

---

## 11. Full Component Summary

```
File              Class/Function            What it does
────────────────  ────────────────────────  ─────────────────────────────────
swarm_env.py      SwarmEnv                  Physics, LiDAR, rewards, collisions
gym_wrapper.py    SwarmFlatEnv              1661D obs assembly, 10-drone state machine
networks.py       SwarmFeaturesExtractor    Actor feature extraction from 151D
networks.py       SwarmActorExtractor       Slices 151D from 1661D, wraps above
networks.py       SwarmCriticExtractor      Slices 1510D from 1661D, plain MLP
networks.py       MAPPOPolicy               Wires actor + critic into SB3-compatible policy
train.py          CurriculumCallback        Logs metrics, saves best model
train.py          train()                   5-stage curriculum loop
evaluate.py       evaluate()                Load actor, run N episodes, report stats
```

---

## 12. What Changes Phase 1 → Phase 2

Only one change: `enable_communication = True`

```
Phase 1:
  gym_wrapper passes enable_communication=False to SwarmEnv
  SwarmEnv fills neighbor slots with ZEROS in every obs
  Drones are effectively blind to each other except via LiDAR

Phase 2:
  gym_wrapper passes enable_communication=True to SwarmEnv
  SwarmEnv fills neighbor slots with real data (within comm_range = 8m)
  Drones can see each other's positions, velocities, goal directions

Network architecture: IDENTICAL between Phase 1 and Phase 2
Training setup:       IDENTICAL
Only difference:      what those 72 neighbor-slot values contain
```

This is intentional — the network learns to USE communication in Phase 2
because the data is there. In Phase 1, the neighbor encoder always receives
zeros and learns to ignore it. The architecture supports both.
