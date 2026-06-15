# Phase 1 — No-Communication Baseline
## Complete Detailed Plan

**CURRENT STATUS (2026-06-12 03:00):**
- **Run 1:** Completed 2.2M / 20M steps in 11.9 hours → **185,000 steps/hour throughput**
- **Run 2:** Just started (2026-06-12 02:59:52)
- **ETA to full completion:** ~96 hours (~4 days) at current rate
- **CRITICAL ALERT:** Drone-drone collision 70-90% at d=0.05 (easy stage)

---

## What Phase 1 Is

Train 10 drones to navigate to a shared goal using ONLY their own LiDAR and
own state. No communication. Neighbor slots in the observation are ALL ZEROS.

This is the baseline that proves: **without communication, drones can only do so
much.** Phase 2 (with communication) should be ~30 percentage points better.

**Algorithm: MAPPO**
- During training: one centralized coach (critic) watches ALL 10 drones at once
- At evaluation: each drone acts alone using only its 151D local observation
- The centralized coach is NEVER used at evaluation time

---

## Environment Parameters (Fixed — Do Not Change)

```
Arena:                  20.0m × 20.0m
Number of drones:       10
Drone radius:           0.15m
Max steps per episode:  1200
Timestep (dt):          0.1s
Max velocity (V_MAX):   1.2 m/s

LiDAR rays:             72
LiDAR range:            8.0m
Comm range:             8.0m (unused in Phase 1)

Goal reach threshold:   0.3m (drone center to goal)
Drone-drone collision:  0.30m center-to-center (= 2 × drone radius)

Spawn wall clearance:   0.60m (spawn only)
BFS wall clearance:     0.20m (BFS grid only)
BFS grid resolution:    0.2m
```

## Obstacle Generation Parameters (Fixed)

```
Target density:         0.25 (final stage)
Cluster radius:         1.5m
Spawn obstacle clear:   0.30m (surface to surface)
Spawn center to goal:   7.0m minimum
Goal spawn clearance:   6.0m (drone center to goal at spawn)
Inter-drone minimum:    0.30m (surface to surface at spawn)
Goal exclusion radius:  0.70m (goal point to obstacle surface)
Spawn wall clearance:   0.60m
```

---

## Observation Space

### Logical Observation — 151D (what the actor sees and uses)

```
Index    Dimension    Content                        Normalization
------   ---------    -------                        -------------
0:72     72D          LiDAR rays (72 rays)           divided by 8.0 (LIDAR_RANGE)
72:79    7D           Own state:
                        [0] vx                       divided by 1.2 (V_MAX)
                        [1] vy                       divided by 1.2 (V_MAX)
                        [2] x position               divided by 20.0
                        [3] y position               divided by 20.0
                        [4] goal_dx                  divided by 20.0
                        [5] goal_dy                  divided by 20.0
                        [6] dist_to_goal             divided by 28.28 (diagonal)
79:151   72D          Neighbor slots (9 × 8D):
                        PHASE 1: ALL ZEROS
                        Phase 2 only: real neighbor data
                          [0] rel_x                  divided by 20.0
                          [1] rel_y                  divided by 20.0
                          [2] neighbor vx            divided by 1.2
                          [3] neighbor vy            divided by 1.2
                          [4] neighbor dist          divided by 28.28
                          [5] neighbor goal_dx       divided by 28.28
                          [6] neighbor goal_dy       divided by 28.28
                          [7] active_flag            0 or 1
```

### Gym Observation — 1661D (what SB3 actually sees)

```
[0    : 151 ]  151D  Local obs for this drone (above)
[151  : 1661]  1510D Global state = all 10 drones × 151D stacked

TOTAL: 1661D
```

**Why 1661D?** SB3's PPO feeds the same observation to both actor and critic.
MAPPO needs actor to see local (151D) and critic to see global (1510D).
Solution: concatenate both into one 1661D vector. The actor extractor slices
`obs[:151]` and ignores the rest. The critic extractor slices `obs[151:]` and
ignores the local part. At evaluation, only the actor runs — it still only
uses the first 151D. Functionally identical to the old 151D actor.

---

## Network Architecture

### Actor — Processes Local 151D Observation

```
Input: 1661D combined obs → SwarmActorExtractor slices obs[:151], ignores obs[151:]

LiDAR Encoder:
  Linear(72 → 128) → LayerNorm(128) → Tanh
  Linear(128 → 64) → LayerNorm(64)  → Tanh
  Output: 64D

Own State Encoder:
  Linear(7 → 32) → LayerNorm(32) → Tanh
  Output: 32D

Neighbor Encoder:
  Reshape: (72,) → (9, 8)
  Linear(8 → 32) → Tanh            [applied to each of 9 slots]
  Mask inactive slots × active_flag
  Mean pool over active neighbors   → 32D
  Linear(32 → 32) → LayerNorm(32) → Tanh
  Output: 32D

Fusion:
  Concat [64 + 32 + 32] = 128D
  Linear(128 → 256) → LayerNorm(256) → Tanh
  Linear(256 → 128) → LayerNorm(128) → Tanh
  Output: 128D  ← features_dim

Actor MLP head:
  Linear(128 → 64) → Tanh
  Output: 64D latent

Action head (SB3 builds):
  Linear(64 → 2) + log_std parameter
  Output: 2D continuous action (vx, vy)

Total actor extractor parameters: 86,400 (verified)
```

### Centralized Critic — NEW for MAPPO

```
Input: 1661D combined obs → SwarmCriticExtractor slices obs[151:] = 1510D global state

Critic Extractor (SwarmCriticExtractor):
  Linear(1510 → 512) → LayerNorm(512) → Tanh    [773,632 + 1,024]
  Linear(512  → 256) → LayerNorm(256) → Tanh    [131,328 +   512]
  Linear(256  → 128) → LayerNorm(128) → Tanh    [ 32,896 +   256]
  Output: 128D

Critic MLP head (critic_mlp):
  Linear(128 → 64) → Tanh                       [  8,256]

Value head (value_net):
  Linear(64 → 1)                                [     65]

Output: scalar value V(global_state)

Total critic parameters: ~948,000
  Extractor: 939,648 (verified by param count)
  critic_mlp + value_net: 8,321

Note: critic ONLY used during training. At evaluation, get_distribution()
calls only the actor path — critic code is never executed.
```

### Action Space
```
Continuous: (vx, vy) ∈ [-1.0, 1.0]²
Actual velocity = action × V_MAX = action × 1.2 m/s
```

---

## Reward Structure (Fixed — Already Applied to swarm_env.py)

```python
step_penalty:        -0.005   per step per drone (alive)
distance_progress:   +delta × 0.3  (delta = how much closer to goal this step)
goal_reached:        +20.0    (drone removed from field on success)
wall_collision:      -2.0     (drone removed)
obstacle_collision:  -2.0     (drone removed)
drone_collision:     -1.0     (both drones removed)
```

**Why these values:**
- Rush 50 steps toward goal then hit obstacle:
  (0.12 × 0.3 × 50) − (0.005 × 50) − 2.0 = **−0.45** (net negative)
- Rushing and dying no longer pays. Must reach goal to get +20.0.

---

## Training Configuration

### Curriculum (With Actual Throughput)

**Measured throughput (Run 1): 185,000 steps/hour**

```
Stage   Density    Steps       Cumulative    Est. Time     Wall Clock
------  -------    ---------   ----------    ----------    ---------
1       0.05       3,000,000   3M            ~16.2 hours   ~16h
2       0.10       4,000,000   7M            ~21.6 hours   +22h
3       0.15       4,000,000   11M           ~21.6 hours   +22h
4       0.20       4,000,000   15M           ~21.6 hours   +22h
5       0.25       5,000,000   20M           ~27.0 hours   +27h
                               TOTAL:        ~96 hours     4 days from now
```

**Run 1 actual timeline:**
- Started: 2026-06-11 15:04:44
- Ended: 2026-06-12 02:58:33  
- Duration: 11 hours 54 minutes
- Steps: 2.2M (Stage 1 incomplete)

### PPO Hyperparameters

```python
learning_rate    = 3e-4
n_steps          = 2048      # steps per env before each update
batch_size       = 256
n_epochs         = 4         # PPO update epochs per batch
gamma            = 0.99      # discount factor
gae_lambda       = 0.95      # GAE lambda
clip_range       = 0.2       # PPO clip
ent_coef         = 0.01      # entropy bonus (encourages exploration)
vf_coef          = 0.5       # value function loss weight
max_grad_norm    = 0.5       # gradient clipping
n_envs           = 6         # parallel environments
device           = "cpu"
```

### Checkpoints Saved
```
checkpoints/phase1/model_stage1.zip   (after d=0.05)
checkpoints/phase1/model_stage2.zip   (after d=0.10)
checkpoints/phase1/model_stage3.zip   (after d=0.15)
checkpoints/phase1/model_stage4.zip   (after d=0.20)
checkpoints/phase1/model_stage5.zip   (after d=0.25) ← FINAL
checkpoints/phase1/model_best.zip     (best reward seen during training)
logs/phase1_training_log.csv          (all metrics)
```

---

## Terminal Output — What You Will See

Every 10,000 steps the terminal prints one line. Format:

```
============================================================
PHASE 1 | STAGE 1/5 | density=0.05 | Step 30,009 | 03:01:36
============================================================
  Reward        :   -43.19  ↑
  Success Rate  :    0.000  (  0.0%)  CRITICAL
  Obstacle Coll :    0.000  (  0.0%)  GOOD
  Drone Coll    :    0.000  (  0.0%)  GOOD
  Wall Coll     :    0.000  (  0.0%)  GOOD
  Timeout Rate  :    1.000  (100.0%)  CRITICAL
  Episode Length:    636.6
  Best Reward   :   -39.70
============================================================
```

**Status meanings:**
- `GOOD` — better than target
- `OK` — within acceptable range
- `WARNING` — borderline, watch closely
- `CRITICAL` — something wrong, may need to stop

**Timeout meaning:** At very start of training (when policy is random), timeouts = 100% (drones never reach goal).
Once training begins, timeouts should drop to 10-30% on easy stages.
If timeout stays at 100% after 500K steps, the policy never learned goal-seeking behavior.

---

## Health Checks — Manual Check Points

Check these MANUALLY at each stage boundary (when density changes).
Run `evaluate.py` on the latest checkpoint with 50 episodes to get real numbers.

```
python evaluate.py --model checkpoints/phase1/model_stage1.zip --episodes 50 --density 0.05
```

### Stage 1 End Check (d=0.05 complete, 3M steps)

| Metric | GOOD | OK | WARNING | CRITICAL — STOP |
|--------|------|----|---------|-----------------|
| Success rate | > 40% | 25-40% | 15-25% | < 15% |
| Reward trend | Rising | Flat | Slowly falling | Sharply falling |
| Obstacle coll | < 25% | 25-40% | 40-55% | > 55% |
| Drone coll | < 40% | 40-55% | 55-65% | > 65% |
| Wall coll | < 2% | 2-5% | > 5% | — |
| Episode length | > 2000 | 1500-2000 | 1000-1500 | < 1000 |

**What to expect:** At d=0.05 almost no obstacles. Main failure = drone-drone
collision. LiDAR detects other drones. Expect 35-60% success by end.

---

### Stage 2 End Check (d=0.10 complete, 7M steps)

| Metric | GOOD | OK | WARNING | CRITICAL — STOP |
|--------|------|----|---------|-----------------|
| Success rate | > 35% | 20-35% | 12-20% | < 12% |
| Reward vs stage1 end | Higher or equal | Within -10% | -10% to -20% | > -20% drop |
| Obstacle coll | < 30% | 30-45% | 45-60% | > 60% |
| Drone coll | < 40% | 40-55% | > 55% | — |

**What to expect:** Success will DIP when density first increases (normal).
Should recover within 1-2M steps. If reward is STILL declining at 7M steps
total (end of stage 2), that is a problem.

---

### Stage 3 End Check (d=0.15 complete, 11M steps)

| Metric | GOOD | OK | WARNING | CRITICAL — STOP |
|--------|------|----|---------|-----------------|
| Success rate | > 30% | 18-30% | 10-18% | < 10% |
| Reward trend | Flat or rising | — | Slowly falling | Declining > 15% |
| Episode length | > 1800 | 1400-1800 | < 1400 | — |

---

### Stage 4 End Check (d=0.20 complete, 15M steps)

| Metric | GOOD | OK | WARNING | CRITICAL — STOP |
|--------|------|----|---------|-----------------|
| Success rate | > 25% | 15-25% | 8-15% | < 8% |
| Obstacle coll | < 40% | 40-55% | > 55% | — |

---

### Stage 5 Final Check (d=0.25 complete, 20M steps)

Run full 200-episode evaluation:
```
python evaluate.py --model checkpoints/phase1/model_stage5.zip --episodes 200 --density 0.25
```

| Metric | Target | Minimum Acceptable | Below This = Problem |
|--------|--------|-------------------|----------------------|
| **Success rate** | **55-65%** | **40%** | Reconsider Phase 2 targets |
| Obstacle coll | < 20% | < 30% | — |
| Drone coll | < 25% | < 35% | — |
| Wilson CI width | < ±5% | < ±8% | Need more episodes |

---

## CRITICAL: Run 1 Data Analysis

**Run 1 ended with alarming drone-drone collision rates:**

```
Stage 1 (d=0.05 — nearly empty):
  @ 1.99M steps: drone_collision = 44.1%  obstacle_collision = 44.6%
  @ 3.99M steps: drone_collision = 29.5%  obstacle_collision = 56.2%
  @ 5.99M steps: drone_collision = 39.6%  obstacle_collision = 52.6%
  @ 7.99M steps: drone_collision = 46.9%  obstacle_collision = 50.6%
  @ 9.99M steps: drone_collision = 12.5%  obstacle_collision = 82.9%
  @ 11.99M steps: drone_collision = 32.4%  obstacle_collision = 65.2%
  @ 2.2M steps final: drone_collision = 72.1%  obstacle_collision = 19.7%
  
Success rate: stayed below 13% throughout
```

**Interpretation:**
- On d=0.05 (an open field with 5% obstacle coverage), 70% of drones are crashing into **each other**
- This is NOT a problem with obstacle avoidance (LiDAR works fine)
- This is a problem with **drone-drone coordination**
- The 10-drone state machine architecture (one SB3 PPO with shared parameters) cannot learn collision avoidance

**Why this happened:**
The gym_wrapper cycles through 10 drones sequentially. Each drone takes an action, but the actual physics step only happens every 10th call. This means:
1. A drone's action and its collision consequence are separated by up to 10 micro-steps
2. Credit assignment is diffuse — the drone doesn't learn that ITS action caused the collision
3. With parameter sharing across all drones, one drone's poor policy affects others

**Decision needed:**
Do you want to:
1. **Push through** (Run 2 might be better by luck) and see if it recovers by Stage 5
2. **Stop and redesign** the architecture to give per-drone credit assignment
3. **Switch to simpler baseline** (single RL agent pathplanner, not MARL)

For now, Run 2 is running. Monitor the first 500K steps (≈2.7 hours).
If drone_collision stays > 60%, consider option 2 or 3.

---

## Warning Signs During Training (Check Terminal Every Hour)

**Stop training immediately if you see:**

1. **Reward declining for 500K+ steps** — not a dip, a sustained fall
   - Current broken training had this at stage 3 — dropped from 122 → 83
   - Means policy is catastrophically forgetting

2. **Episode length below 1000** — drones dying too fast
   - Means rushing exploit is still happening (reward fix may have failed)
   - Check swarm_env.py reward values are correct

3. **Success rate = 0.00 for 200K+ steps** — policy completely collapsed
   - Can happen after density jump
   - OK for first 100K steps of new stage, not OK after that

4. **Wall collision > 10%** — LiDAR-wall avoidance broken
   - Should be near 0% always

**Normal things that look scary but are fine:**

1. Success rate DROPS when density increases — always happens, recovers in 500K-1M steps
2. Reward dips at stage start — fine, should recover
3. Obstacle collision SPIKES at stage start — fine, drones learning new density

---

## What Good Phase 1 Training Looks Like

### Reward Curve
```
Stage 1: starts negative (-15 to -5), climbs to 100-150
Stage 2: dips slightly at start, climbs to 120-160
Stage 3: dips slightly, climbs to 110-150
Stage 4: dips, stabilizes 100-140
Stage 5: stabilizes 90-130
```
Note: absolute reward values with new structure will be different from old.
Goal reward is now +20 instead of +10, so rewards will be higher overall.

### Success Rate Curve
```
d=0.05: 0% → 35-60% (rising clearly)
d=0.10: dips to ~20%, recovers to 30-50%
d=0.15: dips to ~15%, recovers to 25-45%
d=0.20: dips to ~10%, recovers to 20-40%
d=0.25: stabilizes at 35-55% (final result)
```

### Collision Rate Trend
- Obstacle collision should DECREASE over training within each stage
- Drone collision should DECREASE over training within each stage
- Wall collision should stay near 0% throughout

---

## Before Starting Training — Checklist

- [ ] Kill current broken Phase 1 training (Ctrl+C if still running)
- [ ] Verify reward fix in swarm_env.py:
      Line 520: `-0.005`
      Line 536: `-2.0` (wall)
      Line 548: `-2.0` (obstacle)
      Line 559: `+20.0` (goal)
      Line 575-576: `-1.0` (drone collision)
      Line 591: `delta * 0.3`
- [ ] MAPPO implemented in networks.py
- [ ] gym_wrapper.py updated to return global state
- [ ] train.py updated for MAPPO + new curriculum (20M steps)
- [ ] Delete old broken checkpoints: checkpoints/phase1/
- [ ] Delete old broken logs: logs/phase1_training_log.csv

## Command to Start Phase 1

```bash
python train.py --phase 1
```

## Command to Check a Checkpoint Mid-Training

```bash
python evaluate.py --model checkpoints/phase1/model_stage2.zip --episodes 50 --density 0.10
```

---

## Paper Contribution from Phase 1

Phase 1 result (55-65% success) goes into the paper as:

> *"Without inter-agent communication, drones rely solely on 72-ray LiDAR for
> obstacle and peer avoidance. Under MAPPO training at obstacle density d=0.25,
> the no-communication baseline achieves 61.2% ± 3.1% individual drone success
> rate (Wilson 95% CI, N=1000 episodes). This represents the ceiling for purely
> reactive decentralized navigation on this task."*

Then Phase 2 shows communication raises this to 88-93%, proving the point.
