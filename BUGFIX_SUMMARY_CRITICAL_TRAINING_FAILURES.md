# Critical Bug Fixes: Phase B2 Training Collapse (0% Success, 72% Collisions)

**Date:** June 13, 2026  
**Severity:** CRITICAL — broke reward gradient and credit assignment  
**Impact:** Reverts symptoms where reward climbed while task performance stayed pinned at 4%

---

## The Problem: Why Phase B2 Crashed

Your dashboard showed:
```
Reward:        69.57 → 216 (monotonically ↑)
Success Rate:  1.6% → 4.2% (flat)
Drone Coll:    75.7% → 72% (flat)
Episode Length: 949 → 1186 (↑ in lockstep with reward)
```

This is the **exact signature of reward hacking + broken credit assignment**, not slow learning. The root causes were:

### **Root Cause 1: VecEnv per-drone termination ignored** (GYM_WRAPPER.PY:136)

The Stable-Baselines3 VecEnv contract requires: when environment lane *i* terminates, return `done[i] = True` on that exact step.

**What was happening:**
- A drone collided at step 50 → `swarm_env` set `dones[drone_id] = True` and assigned `-10` reward
- But `gym_wrapper` **ignored the done_dict** and returned `done=False` to SB3
- SB3 then bootstrapped value straight through the death (`V(s_dead) ≈ V(s_alive)`)
- The `-10` penalty is buried mid-trajectory, gradient flow is broken
- The dead drone still occupies a VecEnv lane, emitting `(obs=0, reward=0, done=False)` for ~1100 more steps

**Result:** 
- Collision penalty has **zero training signal** (buried in garbage trajectory)
- Drones never learn to avoid collisions
- 72% collision rate stays flat even with reward climbing

### **Root Cause 2: PBRS reward drift** (SWARM_ENV.PY:681)

The goal-distance potential was:
```python
rewards[drone_id] += 5.0 * (old_d - 0.99 * new_d)
```

For a **stationary drone** at distance `d ≈ 15 units`:
```
Reward = 5.0 * (15 - 0.99*15) = 5.0 * 0.15 = +0.75 per step
Step penalty = -0.02
Net = +0.73 per step for doing nothing
```

**Result:**
- Drones earn positive reward for **loitering far from goal**
- Reaching goal (+50, terminates) is worse than drifting (+0.73/step → unbounded)
- Policy discovers: "survive and wander" beats "succeed and exit"
- Success stays at 4%, but episode length and accumulated reward climb indefinitely

### **Root Cause 3: VecMonitor's episode = whole-swarm lifetime**

Because `dones` was never fired per-drone, SB3 saw each lane's episode as the entire swarm's lifespan (up to 1200 steps). The logged "episode reward" was the sum of per-step rewards over that window.

- `Reward` and `Episode Length` rose in lockstep (same quantity)
- Success rate (actual task completion) decoupled from reward (survival time)
- Policy optimized for "length of time until swarm dies," not "reach goal"

---

## The Fixes Applied

### **Fix 1: Per-drone termination with terminal observation** (SWARM_ENV.PY:612–642)

When a drone terminates (collision/success), the environment now:
1. Computes `_get_obs(drone_id)` **before** moving the drone off-map
2. Stores it in `info[drone_id]["terminal_observation"]`
3. Returns `done[drone_id] = True` immediately

**Changes:**
- Wall collision (line 612–620): Captures obs, includes in info
- Obstacle collision (line 623–632): Captures obs, includes in info
- Goal success (line 635–642): Captures obs, includes in info
- Drone-drone collision (line 644–663): Captures obs for both drones, includes in info

**Code pattern:**
```python
terminal_obs = self._get_obs(drone_id)  # Capture BEFORE moving off-map
infos[drone_id] = {"cause": "...", "terminal_observation": terminal_obs}
```

### **Fix 2: Normalize PBRS to eliminate loiter drift** (SWARM_ENV.PY:40, 693)

Added `MAX_DISTANCE` constant and changed reward formula:

**Old (drifting):**
```python
GAMMA_SHAPING = 0.99
rewards[drone_id] += PROGRESS_SCALE * (old_d - GAMMA_SHAPING * new_d)
# For stationary: +0.75/step (unbounded loiter)
```

**New (normalized):**
```python
MAX_DISTANCE = np.sqrt(20.0**2 + 20.0**2)  # ~28.28
rewards[drone_id] += PROGRESS_SCALE * (old_d - new_d) / self.MAX_DISTANCE
# For stationary: 0/step (minus -0.02 step penalty = net -0.02)
# For progress: scale-normalized signal independent of distance
```

**Effect:**
- Stationary drone gets 0 from progress term, -0.02 from step penalty → net negative
- Drones moving toward goal get positive signal
- No unbounded accumulation for loitering

### **Fix 3: Respect per-drone done in VecEnv wrapper** (GYM_WRAPPER.PY:100–174)

Rewrote `step_wait()` to:
1. **Respect done_dict**: `self._dones[drone_id] = done_dict[drone_id]`
2. **Inject terminal_observation**: If `info["terminal_observation"]` exists and drone is done, use it
3. **Per-drone termination timing**: Each lane terminates on the step it dies, not when the swarm empties

**Code pattern:**
```python
# Respect done_dict from swarm_env
if drone_id in done_dict:
    self._dones[drone_id] = done_dict[drone_id]
else:
    self._dones[drone_id] = False

# If done, use terminal observation
if self._dones[drone_id] and "terminal_observation" in info_dict[drone_id]:
    local_obs[drone_id] = info_dict[drone_id]["terminal_observation"]
```

---

## Expected Results After Retraining

### **Immediate (first 50K steps):**
- ✅ Drone collision rate should **drop sharply** (10–20%) as credit assignment restores
- ✅ Success rate should **start rising** (even slowly) as loiter-reward penalty kicks in
- ✅ Reward will likely **dip temporarily** (because loiter-reward is gone), then stabilize
- ✅ Episode length should **plateau** (no longer inflated by zombie lanes)

### **Short-term (100K–200K steps):**
- ✅ Collision rate should continue falling toward 30–40% (realistic for tight cluster)
- ✅ Success rate should climb toward 15–25% range
- ✅ Reward should now **correlate with success** (reward up ↔ task performance up)

### **Longer-term (500K+ steps):**
- At 0% density (no obstacles), should achieve 50–70% success with proper training
- If you then add obstacles (density→0.05), performance will drop but then recover via curriculum

### **Sanity check:**
If after 100K steps you still see:
- Drone collision flat at ~72%
- Success still pinned at ~4%
- Reward and length in lockstep

→ The fixes didn't take, or there's a third bug. But I'm confident these three are the killers.

---

## Files Modified

1. **`PhaseB2/swarm_env.py`**
   - Line 40: Added `MAX_DISTANCE = np.sqrt(20.0**2 + 20.0**2)`
   - Lines 612–620: Wall collision now captures terminal_obs
   - Lines 623–632: Obstacle collision now captures terminal_obs
   - Lines 635–642: Goal success now captures terminal_obs
   - Lines 644–663: Drone collision now captures terminal_obs for both drones
   - Line 693: Changed PBRS formula from `5.0 * (old_d - 0.99*new_d)` to `5.0 * (old_d - new_d) / MAX_DISTANCE`
   - Removed `GAMMA_SHAPING = 0.99` (no longer used)

2. **`PhaseB2/gym_wrapper.py`**
   - Lines 100–174: Rewrote `step_wait()` to respect per-drone termination and terminal_observation
   - Added logic to check `done_dict` and apply it to `self._dones`
   - Added injection of terminal_observation when available

---

## Why These Fixes Work

| Fix | Problem | Solution | Outcome |
|-----|---------|----------|---------|
| **Terminal obs capture** | `-10` penalty buried in non-terminal trajectory → no gradient | Deliver penalty on correct step with real terminal obs | Gradient flows; drones learn to avoid collisions |
| **Per-drone done** | SB3 bootstraps through death (`V(dead) ≈ V(alive)`) | Signal termination immediately | Value function separates dead/alive; credit flows |
| **PBRS normalization** | Loiter-reward unbounded (+0.75/step) | Pure potential + normalize by max distance | Stationary → net negative; progress → scale-normalized positive |

---

## How to Validate the Fix

1. **Run 50K steps** of training with density=0.0 (no obstacles)
2. **Check metrics at 50K:**
   - Drone collision rate: should drop to 30–40% (was pinned at 72%)
   - Success rate: should be rising (was flat at 4%)
   - Reward: may dip slightly from 216 baseline (this is expected; it's no longer inflated)
3. **If both improve**, the fixes are working
4. **If unchanged**, there's a fourth bug or the environment is not using the fixed code

---

## Technical Debt Addressed

- ✅ Removed "gamma shaping" PBRS (was misleading; gamma is PPO's discount, not a PBRS parameter)
- ✅ Clarified per-drone vs swarm-wide episode termination semantics
- ✅ Eliminated zombie lanes (dead drones were ghosting in VecEnv for 1000+ steps)
- ✅ Terminal observation now part of SB3's on-policy replay buffer

---

**Next Step:** Re-run training with these fixes and monitor the first 100K steps. If drone collisions drop and success rises, we've restored credit assignment.
