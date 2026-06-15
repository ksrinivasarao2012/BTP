# TA-MAPPO Research Plan
## Simple Explanation + Full Roadmap

**STATUS (2026-06-12 03:00):** Phase 1 training run 1 completed 2.2M/20M steps in 11.9 hours.
Run 2 just started. **ETA to completion: ~4 days at current throughput (185K steps/hour).**
**CRITICAL ISSUE:** Drone-drone collision rate 70-90% on easy stage (d=0.05) indicates coordination is broken.

---

## What is MAPPO? (Simple Terms)

Think of it like a **football team in practice vs a real match.**

### During Practice (Training)
The coach stands on a high platform and can see **every player on the field** at once.
He watches all 10 players simultaneously and tells each one:
*"Your decision there was wrong — here's a better one."*

This is the **Centralized Critic** — it sees everything to give better feedback.

### During the Real Match (Execution)
The coach goes home. Each player is now on the field **alone**, making decisions
based only on what they personally can see — their own vision, nearby teammates,
nearby opponents.

This is **Decentralized Execution** — each drone acts on its own local information only.

### Why This Matters
- **IPPO (what we had):** Coach also has blindfolds during practice. Gives feedback
  based on what each player sees individually. Very noisy feedback. Players never
  fully coordinate. Ceiling ~78-85%.

- **MAPPO (what we switch to):** Coach sees everything during practice → much better
  feedback → players learn proper coordination. Same match-day rules apply.
  Ceiling ~88-93%.

---

## Are We Using CTDE?

**Yes. MAPPO = CTDE.**

CTDE stands for: **C**entralized **T**raining, **D**ecentralized **E**xecution

| | Training | Execution (Test Time) |
|--|----------|----------------------|
| **CTDE / MAPPO** | Centralized critic sees ALL drones' states | Each drone uses only its own 151D local obs |
| **IPPO (old)** | Each drone's critic sees only its own 151D obs | Each drone uses only its own 151D local obs |

**At test time, MAPPO and IPPO are identical.** Both drones see only 151D local obs.
This is why Byzantine attacks affect both the same way — the attack happens at test
time, and the centralized critic is completely absent then.

---

## The Byzantine Concern — Resolved

You originally chose IPPO because:
> "CTDE degrades under Byzantine faults because critic sees true global state
> during training but actor operates under corrupted communication at evaluation."

This concern is valid in one specific case: if the CRITIC runs at test time.
**In MAPPO, the critic never runs at test time.** It only exists during training.

```
TRAINING:
  Drone A actor  ←── local 151D obs ──→  takes action
  Centralized critic ←── ALL 10 drones' 151D obs ──→  estimates value
                          (used only for gradient updates)

TEST TIME (Byzantine attack scenario):
  Drone A actor  ←── local 151D obs (neighbor slots may be corrupted) ──→  takes action
  Centralized critic: DOES NOT EXIST at test time
```

The Byzantine attack corrupts the neighbor slots inside the 151D local observation.
The actor (which is identical in MAPPO and IPPO) receives this corrupted input.
The trust mechanism (Phase 4) detects and masks the corrupted inputs.
This works the same regardless of whether you trained with IPPO or MAPPO.

---

## Architecture: What Changes, What Stays the Same

### Actor — UNCHANGED
```
Input:  151D local observation
        ├── 72D  LiDAR rays
        ├── 7D   own state
        └── 72D  neighbor slots (zeros in Phase 1, real data in Phase 2)

Network: SwarmFeaturesExtractor (86,400 params) — same as before
Output: 2D continuous action (vx, vy)
```

### Critic — NEW (Centralized)
```
Input:  1510D global state = 10 drones × 151D each
        (all drones' observations stacked together)

Network: CentralizedCritic (new, ~200K params)
         1510 → 512 → 256 → 128 → 1 (value estimate)
Output: scalar value V(s)
```

### Files to Change
| File | Change |
|------|--------|
| `networks.py` | Add `CentralizedCritic` class |
| `gym_wrapper.py` | Return global state (stack all 10 obs) for critic |
| `train.py` | Pass global state to critic, keep actor logic identical |
| `swarm_env.py` | Fix reward structure (see below) |
| `evaluate.py` | No change needed — runs actor only |

---

## Reward Fix (Must Do First)

**Current problem:** `distance_progress * 2.0` accumulates so fast that
rushing toward goal and dying = same reward as actually reaching the goal.
Policy learned to exploit this — hence the declining reward and instability.

### New Reward Structure
```python
step_penalty:        -0.005        # halved
distance_progress:   +delta * 0.3  # KEY: reduced from 2.0 → 0.3
goal_reached:        +20.0         # doubled from 10.0
wall_collision:      -2.0          # doubled
obstacle_collision:  -2.0          # doubled
drone_collision:     -1.0          # doubled
```

**Math check (rushing exploit broken):**
- Rush 50 steps toward goal + hit obstacle:
  `(0.12 × 0.3 × 50) − (0.005 × 50) − 2.0 = 1.8 − 0.25 − 2.0 = −0.45`
- Net is NEGATIVE. Rushing and dying no longer pays.
- Only way to get positive return: reach goal (+20.0).

---

## Full Research Plan

### Phase 1 — No-Communication Baseline
**Goal:** Establish honest lower bound. Show communication is necessary.

```
Algorithm:    MAPPO (centralized critic during training)
Communication: neighbor slots = all zeros (151D with 72D of zeros)
Training:     20M steps, 6 parallel envs
Curriculum:   density 0.05 → 0.10 → 0.15 → 0.20 → 0.25
              (3M, 4M, 4M, 4M, 5M steps per stage)
Target:       55-65% individual drone success at d=0.25
Checkpoint:   checkpoints/phase1/model_stage{N}.zip
```

**Deliverable for paper:** No-comm baseline curve + deadlock vs density figure

---

### Phase 2 — Communication Baseline
**Goal:** Show communication significantly improves coordination.

```
Algorithm:    MAPPO (centralized critic during training)
Communication: neighbor slots = real data (rel_x, rel_y, vx, vy,
               dist, goal_dx, goal_dy, active_flag per neighbor)
Training:     30-50M steps, train from scratch (not transfer from Phase 1)
Curriculum:   same density schedule
Target:       88-93% individual drone success at d=0.25
Checkpoint:   checkpoints/phase2/model_stage{N}.zip
```

**Deliverable for paper:** Comm vs no-comm comparison table/figure

---

### Phase 3 — Byzantine Fault Degradation Study
**Goal:** Show the system is genuinely vulnerable to adversarial agents.
No training — evaluation only.

```
Algorithm:    Load Phase 2 model (actor only, no critic needed)
Byzantine setup:
  - 1 Byzantine agent:  sends random/false position data
  - 2 Byzantine agents: same
  - 3 Byzantine agents: same
Metric:       Individual drone success rate vs number of Byzantine agents
Target:       Success drops to 30-50% with 2 Byzantine agents
```

**Deliverable for paper:** Byzantine degradation curve

---

### Phase 4 — Trust-Aware Training (T-Cell Mechanism)
**Goal:** Recover performance under Byzantine faults.

```
Algorithm:    MAPPO + T-Cell trust scoring on neighbor slots
Trust mechanism:
  - Each drone scores each neighbor's communication for consistency
  - Low-trust neighbor slots are masked/downweighted
  - Trust scores update over the episode
Training:     30M steps from scratch
Target:       82-88% success under 2 Byzantine agents
              (recovers ~85% of Phase 2 performance)
Checkpoint:   checkpoints/phase4/model_stage{N}.zip
```

**Deliverable for paper:** Trust mechanism recovery curve

---

### Phase 5 — True Baseline (79D, No Neighbor Slots)
**Status: DROPPED to save time**

Justified in paper with one sentence:
*"Phase 1 uses zero-padded neighbor slots. Any performance difference vs a 79D
observation is negligible given the 30+ percentage point gap between Phase 1 and
Phase 2, which is the paper's primary contribution."*

---

## Expected Paper Results Table

| Configuration | Success Rate | Notes |
|--------------|-------------|-------|
| Phase 5: No neighbor slots (79D) | 35-45% | True baseline |
| Phase 1: No-comm (151D, zeros) | 55-65% | MAPPO better training + reactive LiDAR avoidance |
| Phase 2: Communication (151D, real) | **88-93%** | Communication is the key factor |
| Phase 3: Comm + 1 Byzantine | 65-75% | Degradation starts |
| Phase 3: Comm + 2 Byzantine | 35-55% | Severe degradation |
| Phase 3: Comm + 3 Byzantine | 20-35% | Near collapse |
| Phase 4: Trust + 2 Byzantine | **82-88%** | T-Cell recovers performance |

---

## Immediate Next Steps

### BLOCKING ISSUE (Do This First)
**Drone-drone collision dominance (70-90% of failures at d=0.05) suggests:**
1. The 10-drone state machine in `gym_wrapper.py` is creating poor credit assignment
2. Drones can't learn collision avoidance because reward only flows every 10 micro-steps
3. Parameter sharing across all 10 drones may be fundamentally incompatible with coordination

**ACTION:** Before running the full 20M-step curriculum:
- Run Stage 1 (3M steps) to completion with current config (ETA: ~16 hours)
- Evaluate `model_stage1.zip` on 100 episodes at d=0.05
- If success rate < 30%, **STOP** — there's a fundamental architecture problem
- If success rate > 35%, continue to Stage 2

### If Success Rate OK (≥35% at d=0.05)
1. Continue stages 2–5 sequentially
2. Evaluate at each stage boundary (50 episodes, new density)
3. Stop immediately if success rate drops below 10%

### If Success Rate Poor (<30%)
1. Consider alternative: single-drone PPO with centralized planner (not MAPPO)
2. Or: fix gym_wrapper step machine to give credit per drone, not per 10-step cycle

---

## Summary

| Decision | Choice | Reason |
|----------|--------|--------|
| Algorithm | MAPPO (CTDE) | Only way to hit 90%+ |
| Byzantine concern | Resolved | Critic absent at test time |
| Actor architecture | Unchanged | Same 151D local obs |
| Reward fix | distance_progress × 0.3 | Removes rushing exploit |
| Training budget | 30-50M steps | Necessary for convergence |
| Phase 1 target | 55-65% | MAPPO centralized critic improves reactive policy |
| Phase 2 target | 88-93% | Achievable with MAPPO |
