# Bug Analysis Report
## Every Issue — Problem or Not, and the Fix

---

## Summary Table

| # | File | Issue | Real Problem? | Severity |
|---|------|-------|---------------|----------|
| 1 | evaluate.py | Wrong class name: `SwarmGymWrapper` | YES — CRASH | FATAL |
| 2 | evaluate.py | Wrong constructor signature | YES — CRASH | FATAL |
| 3 | evaluate.py | Bogus sys.path insert | YES — warning | MINOR |
| 4 | evaluate.py | `env.n_drones` doesn't exist | YES — CRASH | FATAL |
| 5 | evaluate.py | `env.swarm_env.agents` doesn't exist | YES — logic error | FATAL |
| 6 | evaluate.py | `env._infos` doesn't exist | YES — CRASH | FATAL |
| 7 | evaluate.py | Wrong cause string `"collision"` | YES — silent wrong | HIGH |
| 8 | evaluate.py | `classify_timeout` deadlock always assumed | YES — metric fabricated | MEDIUM |
| 9 | evaluate.py | `render_first_n` accepted but unused | NO — dead arg | LOW |
| 10 | gym_wrapper.py | Self-tests assert 151D but obs is 1661D | YES — tests crash | HIGH |
| 11 | gym_wrapper.py | Docstring says Box(151,) | YES — misleading | LOW |
| 12 | train.py | `--resume 5` trains nothing silently | YES — silent no-op | MEDIUM |
| 13 | swarm_env.py | `_ray_circle_intersection` never called | NO — dead code | NONE |
| 14 | swarm_env.py | `_ray_wall_intersection` never called | NO — dead code | NONE |
| 15 | networks.py | `SwarmActorCriticPolicy` never used | NO — dead class | NONE |
| 16 | networks.py | `_DummyMlpExtractor` fragile SB3 coupling | NO — but watch SB3 upgrades | LOW |
| 17 | swarm_env.py | Neighbor pathway zeros in Phase 1 | NO — by design | NONE |
| 18 | train.py | `success_reward_threshold` stored, never read | NO — dead param | NONE |
| 19 | train.py | Best model across mixed densities | YES — metric confused | MEDIUM |
| 20 | swarm_env.py | Magic `28.28` appears raw and as variable | NO — cosmetic | NONE |
| 21 | gym_wrapper.py | 9/10 steps return zero reward | NO — by design | NONE |
| **22** | **evaluate.py** | **Macro/micro step conflation in eval loop** | **YES — metrics silently wrong** | **HIGH** |

---

## Detailed Analysis

---

### 1. evaluate.py — Wrong class name `SwarmGymWrapper`

**Problem? YES — FATAL CRASH**

```python
# Line 42 in evaluate.py (WRONG):
from gym_wrapper import SwarmGymWrapper

# What actually exists in gym_wrapper.py:
class SwarmFlatEnv:
```

`SwarmGymWrapper` does not exist. The import fails on the first line of the
function. `evaluate.py` cannot run at all — it crashes before doing anything.

**Fix:** Change the import and every usage.

```python
# CORRECT:
from gym_wrapper import SwarmFlatEnv
```

---

### 2. evaluate.py — Wrong constructor signature

**Problem? YES — FATAL CRASH**

```python
# Line 149 (WRONG):
env = SwarmGymWrapper(swarm_env_class=SwarmEnv, density=density, enable_communication=...)

# What SwarmFlatEnv actually accepts:
def __init__(self, density=0.25, enable_communication=False, seed=None):
```

`swarm_env_class` is not a parameter. Even if the import were fixed, the env
creation would crash with `TypeError: unexpected keyword argument`.

**Fix:** Remove `swarm_env_class=SwarmEnv`:

```python
env = SwarmFlatEnv(density=density, enable_communication=enable_communication)
```

---

### 3. evaluate.py — Bogus sys.path insert

**Problem? YES — minor but wrong**

```python
# Line 40 (WRONG):
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "PhaseB2"))
```

This adds `<current_dir>/PhaseB2` to the Python path. But the current dir IS
`PhaseB2`, so this adds `D:\Swarm\BTP\PhaseB2\PhaseB2` which doesn't exist.
The actual imports still work because Python also searches the working directory,
but the path manipulation is wrong and confusing.

**Fix:** Remove that line entirely. The script already runs from PhaseB2.

---

### 4. evaluate.py — `env.n_drones` doesn't exist

**Problem? YES — FATAL CRASH at runtime**

```python
# Lines 196, 209, 219, 268, 290, 293 (WRONG):
for drone_idx in range(env.n_drones):
```

`SwarmFlatEnv` has no `n_drones` attribute. `swarm_env.N_DRONES` exists.
This crashes the moment the first episode runs.

**Fix:** Use a module-level constant or access via the env:

```python
N_DRONES = 10   # fixed for this project
# or:
env.swarm_env.N_DRONES
```

---

### 5. evaluate.py — `env.swarm_env.agents` doesn't exist

**Problem? YES — always returns wrong result**

```python
# Line 227 (WRONG):
if drone_name not in env.swarm_env.agents:
```

`SwarmEnv` has no `agents` attribute. It has `active_drones`, which is a
`set` of integers (not strings). `drone_name` is `"drone_0"`, `"drone_1"` etc.
Even if you renamed `.agents` to `.active_drones`, comparing `"drone_0"` to
`{0, 1, 2, ...}` always returns `True` — so every drone would appear terminated
on step 1, and the entire episode logic would tally all 10 drones as terminated
immediately.

**Fix:** The whole per-drone termination detection approach is wrong.
Read causes from `info["causes"]` dict (which is `{drone_id: cause_string}`)
the same way the training callback does. No need to poll `.agents` at all.

```python
# CORRECT — use info dict (matches how train.py callback works):
for drone_id, cause in info.get("causes", {}).items():
    if cause == "success":
        ...
```

---

### 6. evaluate.py — `env._infos` doesn't exist

**Problem? YES — AttributeError crash**

```python
# Line 229 (WRONG):
if drone_name in env._infos and "cause" in env._infos[drone_name]:
```

`SwarmFlatEnv` stores the last info per drone in `self._last_info`, not `_infos`.
`env._infos` would raise `AttributeError`.

**Fix:** Not needed once issue #5 is fixed. Read causes from the `info` dict
returned by `step()`, not from internal wrapper state.

---

### 7. evaluate.py — Wrong cause string `"collision"`

**Problem? YES — collisions silently never tallied**

```python
# Line 238 (WRONG):
elif cause == "collision":
    ep_collisions += 1
```

`SwarmEnv` (in `step()`) emits exactly these cause strings:
```python
{"cause": "wall_collision"}
{"cause": "obstacle_collision"}
{"cause": "drone_collision"}
{"cause": "success"}
{"cause": "timeout"}
```

The string `"collision"` is never emitted. Every collision would pass through
the elif without matching, and `ep_collisions` would always remain 0 while
the drone is silently unaccounted for. The paper's collision metrics would be
completely wrong.

**Fix:** Match the actual cause strings:

```python
elif cause == "wall_collision":
    counters["wall_collisions"] += 1
elif cause == "obstacle_collision":
    counters["obstacle_collisions"] += 1
elif cause == "drone_collision":
    counters["drone_collisions"] += 1
```

---

### 8. evaluate.py — `classify_timeout` deadlock always assumed

**Problem? YES — timeout breakdown metric is fabricated**

```python
# Lines 97-101 in the function (the comment admits it):
if displacement < 0.5:
    # In a full implementation, we would check for nearby stuck neighbors.
    # For simplicity, we classify stuck drones as inter_drone_deadlock...
    # Default to inter_drone_deadlock.
    return "inter_drone_deadlock"
```

Any stuck drone (displacement < 0.5m) is called `inter_drone_deadlock` even
if it is stuck on an obstacle with no neighbors nearby. The function cannot
distinguish these cases without neighbor position data at that moment.

The "obstacle_blockage" return value from line 254 is dead — the function never
reaches it.

**Is it a problem?** YES — for the paper, the timeout breakdown table would
show inflated inter_drone_deadlock numbers and zero obstacle_blockage numbers.
A reviewer would ask about this.

**Realistic fix:** Classify into just two buckets — stuck (displacement < 0.5m)
and genuinely still moving. Label them "stuck_timeout" and "moving_timeout".
Do NOT claim obstacle vs drone discrimination unless you have that data:

```python
def classify_timeout(position_history):
    if len(position_history) < 50:
        return "moving_timeout"
    pos_start = list(position_history)[-50][1]
    pos_end   = list(position_history)[-1][1]
    if np.linalg.norm(pos_end - pos_start) < 0.5:
        return "stuck_timeout"
    return "moving_timeout"
```

This is honest. Both are timeouts; we just note whether the drone was moving.

---

### 9. evaluate.py — `render_first_n` accepted but unused

**Problem? NO — just dead argument**

The `--render N` argument is parsed and passed to `evaluate()`, but
`render_first_n` is never read inside the function.

**Is it a problem?** No crash, no wrong results. The user might expect rendering
but get none. It's misleading documentation.

**Fix:** Either implement it (call `env.swarm_env.render()` for the first N
episodes) or remove the argument. Since this is Phase 1 (CPU training, no
display server needed), removing it is fine for now.

---

### 10. gym_wrapper.py — Self-tests assert 151D but obs is 1661D

**Problem? YES — self-tests crash immediately**

```python
# Lines 280, 285, 291, 298, 305 (WRONG):
assert obs.shape == (151,), f"Reset obs shape wrong: {obs.shape}"
```

After the MAPPO update, `observation_space = Box(1661,)` and `reset()`/`step()`
return 1661D observations via `_combined_obs()`. Every assert fails on line 1.

Running `python gym_wrapper.py` to validate the env would crash immediately,
giving false confidence in a broken env or false alarm about a working one.

**Fix:** Change all asserts to check for 1661:

```python
assert obs.shape == (1661,), f"Reset obs shape wrong: {obs.shape}"
```

---

### 11. gym_wrapper.py — Docstring says Box(151,)

**Problem? YES — misleading but not a crash**

The class docstring at the top says:
```
  - observation_space = Box(151,) — local observation for one drone
```

It is now `Box(1661,)`. Anyone reading the docs would have wrong expectations.

**Fix:** Update to:
```
  - observation_space = Box(1661,) — combined local (151D) + global (1510D)
```

---

### 12. train.py — `--resume 5` trains nothing silently

**Problem? YES — silent no-op**

```python
def resume_training(resume_from_stage: int = 5, ...):
    start_stage = resume_from_stage
    for stage in CURRICULUM[start_stage:]:   # CURRICULUM has indices 0-4
        ...
```

`CURRICULUM[5:]` = empty list. If someone runs `--resume 5` (or uses the
default `resume_from_stage=5`), the function prints "Loading checkpoint..."
and then prints "Resume training complete!" having trained nothing.
No error, no warning.

**Why `--resume 5` is also logically wrong:** The flag is documented as
"stage N is complete, resume from next stage." If stage 5 is complete,
ALL stages are done — there is nothing to resume. But the function should say
so explicitly instead of silently exiting.

**Fix:** Add a guard:

```python
start_stage = resume_from_stage
remaining = CURRICULUM[start_stage:]
if not remaining:
    print(f"[INFO] All stages complete through stage {resume_from_stage}. Nothing to resume.")
    return
```

Also: the default `resume_from_stage=5` in the function signature implies
"default is to resume from the end," which is useless. Change default to `None`
and require the user to specify it.

---

### 13 & 14. swarm_env.py — `_ray_circle_intersection` and `_ray_wall_intersection` never called

**Problem? NO — dead code, zero impact on training or evaluation**

Both methods are fully implemented (32 lines total) and completely unused.
`_get_lidar()` reimplements both inline using vectorized NumPy, which is
~10x faster. The methods were the original per-ray Python implementation
that was replaced by the vectorized version.

**Impact on training:** None. `_get_lidar()` is called, these are not.
**Impact on performance:** None for training. They are parsed once at import.
**Fix:** Safe to delete both methods (saves ~32 lines). Not urgent.

---

### 15. networks.py — `SwarmActorCriticPolicy` never used

**Problem? NO — completely harmless dead class**

```python
class SwarmActorCriticPolicy(ActorCriticPolicy):
    """Original IPPO policy — kept for reference only. Use MAPPOPolicy for training."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
```

`train.py` uses `MAPPOPolicy`. Nothing imports `SwarmActorCriticPolicy`.
It adds ~5 lines and one import. No runtime impact.

**Fix:** Safe to delete. Not urgent.

---

### 16. networks.py — `_DummyMlpExtractor` fragile SB3 coupling

**Problem? NO — works now, but flag for library upgrades**

```python
class _DummyMlpExtractor(nn.Module):
    latent_dim_pi = 64
    latent_dim_vf = 64
    def forward(self, x): return x, x
```

SB3 internally checks `mlp_extractor.latent_dim_pi` and `latent_dim_vf` to
build the action/value heads. The dummy satisfies those checks.

**Risk:** If SB3 upgrades and adds more checks or changes the interface for
`mlp_extractor`, this dummy breaks silently. No error at import — it would
break at the first gradient step.

**Is it a problem now?** No. We are on a pinned version of SB3.
**Mitigation:** Pin `stable-baselines3==X.Y.Z` in requirements.txt.
That way a `pip install --upgrade` doesn't silently break training.

---

### 17. swarm_env.py — Neighbor pathway zeros in Phase 1

**Problem? NO — this is by design**

In Phase 1, `enable_communication=False`. The neighbor slot code in `_get_obs()`:
```python
if (not self.enable_communication or ...):
    obs.extend([0.0] * 8)
```

All 72 neighbor dimensions are zeros. The neighbor encoder in `SwarmFeaturesExtractor`
processes `(batch, 9, 8)` of all-zeros and produces all-zero slot features.
After masking by `active_flag` (which is 0.0 for all slots since no neighbors
are filled), the mean-pooled result is all-zeros.

The fusion layer receives `[64D lidar, 32D own_state, 32D zeros]` = 128D.
The 32D zero chunk is ignored by the network — it learns weights that produce
meaningful outputs from the 96D that actually carry information.

**Performance cost:** Small. Processing zeros through a linear layer + tanh is
fast. The overhead is ~32D of linear algebra over zeros per drone per step.
Not worth optimizing.

**Is there wasted observation space?** Yes — 72D of zeros per step per drone.
But Phase 2 uses those same 72D for real data. One architecture for both phases
is the correct tradeoff.

---

### 18. train.py — `success_reward_threshold` stored but never read

**Problem? NO — dead parameter, zero impact**

```python
def __init__(self, ..., success_reward_threshold: float = 0.0):
    self.success_reward_threshold = success_reward_threshold
```

This is never read in the callback. It was presumably meant to trigger early
stopping when a success threshold is met, but that logic was never implemented.

**Fix:** Remove the parameter or implement the feature. Removing is safer.

---

### 19. train.py — Best model saved across heterogeneous densities

**Problem? YES — the metric is confused**

```python
if mean_reward > self.best_mean_reward:
    self.best_mean_reward = mean_reward
    self.model.save(f"checkpoints/phase{self.phase}/model_best")
```

At density 0.05 (stage 1), rewards are high because few obstacles → easy →
many successes → high episode reward. At density 0.25 (stage 5), rewards are
lower because more obstacles → more failures → lower episode reward.

The "best" model by reward will almost certainly be a stage 1 or stage 2
checkpoint — not the most capable model. You'd load `model_best.zip` thinking
it's the final model, but it's actually trained only on d=0.05.

**Fix:** Either:
1. Save `model_best` only within the current stage (reset `best_mean_reward`
   at each stage start), OR
2. Ignore `model_best` entirely and always use `model_stage5.zip` for evaluation.

Option 2 is simplest. The `model_stage5.zip` checkpoint IS the final model.
`model_best` in a curriculum context is misleading.

**Recommended change:**

```python
# In train() loop, after model.learn():
# Only save best within the current stage
callback.best_mean_reward = -np.inf  # reset at each stage boundary
```

---

### 20. swarm_env.py — Magic `28.28` raw vs named variable

**Problem? NO — cosmetic inconsistency**

```python
# Line 455 — raw magic number:
dist_to_goal = np.linalg.norm(self.goal - self.drone_positions[drone_id]) / 28.28

# Line 460 — same value as a named variable:
arena_diag = 28.28
```

`28.28 ≈ sqrt(20² + 20²)` = arena diagonal. Correct value. Used consistently.
The named variable `arena_diag` appears 7 lines below the raw use, making it
slightly inconsistent.

**Impact on training:** Zero. The number is the same.
**Fix:** Move `arena_diag = 28.28` (or compute it as `np.sqrt(FIELD_W**2 + FIELD_H**2)`)
to a class constant, and use it everywhere. Low priority.

---

### 21. gym_wrapper.py — 9 of 10 steps return zero reward

**Problem? NO — this is how the state machine works, and PPO handles it**

The drone-cycle state machine collects one drone's action per `step()` call.
For the 9 intermediate steps (drones 1–9), it returns `reward=0.0` and `done=False`.
On the 10th step, it executes all 10 actions and returns the real total reward.

SB3's PPO stores these as rollout transitions. 9/10 of all stored transitions
have `reward=0` and `done=False`. This means:
- Credit assignment is diffuse — the reward appears at every 10th transition
- The value function learns to output ~0 for the intermediate states

**Is this a real training problem?** It's suboptimal but not catastrophic.
The policy still sees the correct observations for each drone and produces
actions. The value function is slightly noisier because of the 0-reward states.
This is the accepted tradeoff for using a single SB3 PPO with parameter sharing
over 10 drones.

**Alternative:** A proper multi-agent PPO implementation with separate rollout
buffers per drone would be cleaner, but that requires rewriting the training loop
outside SB3. Not worth it for the paper's scope.

---

### 22. evaluate.py — Macro/micro step conflation in eval loop

**Problem? YES — steps-to-success metric is 10× inflated, deadlock window is 10× compressed**

`SwarmFlatEnv.step()` is a 10-drone state machine. Each call advances ONE drone's
turn. Every 10th call constitutes one real simulation tick.

The original evaluate.py loop (and the first rewrite) called `env.step()` once
per predict call, incrementing `ep_steps` every micro-step:

```python
while True:
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, done, truncated, info = env.step(action)
    ep_steps += 1                        # ← wrong: counts micro-steps
    pos_history[i].append(ep_steps, p)   # ← wrong: records 10× per real tick
```

**Consequence 1 — steps_to_success is 10× too large:**
If a drone reaches the goal after 500 real simulation steps, `ep_steps = 5000`
micro-steps. The paper metric "mean steps to success" would report 5000, not 500.

**Consequence 2 — deadlock classification window is 10× too short:**
`deque(maxlen=300)` was intended to store 300 real ticks (30 simulated seconds).
With micro-step recording, it holds only 30 real ticks (3 seconds).
`classify_timeout`'s "50-step window" checks over 5 real ticks = 0.5 seconds —
far too short to detect deadlock.

**Why it doesn't affect training:** SB3's rollout collection works at micro-step
level by design. The wrapper feeds SB3 one transition per drone per micro-step.
This is correct for PPO. The conflation only matters in evaluate.py where we
want human-meaningful metrics.

**Fix:** Use `env._drone_cycle == 0` as the macro-step boundary:

```python
macro_steps = 0
while True:
    # Only at the start of each real simulation tick
    if env._drone_cycle == 0:
        macro_steps += 1
        for drone_id in env.swarm_env.active_drones:
            pos_history[drone_id].append((macro_steps, pos.copy()))

    action, _ = model.predict(obs, deterministic=True)
    obs, reward, done, truncated, info = env.step(action)

    for drone_id, cause in info.get("causes", {}).items():
        if cause == "success":
            steps_to_success.append(macro_steps)   # real steps, not micro
```

`env._drone_cycle` starts at 0 after reset. It increments 0→1→...→9→0 with
each step call. Checking it BEFORE the call tells us whether we're starting
a new real tick. The 10th micro-step (which executes SwarmEnv) resets it to 0,
so the NEXT loop iteration starts a new real tick.

**This is the most important fix** — even a "working" evaluate.py (with issues
1–8 fixed but not this one) would produce wrong paper numbers.

---

## What Needs to Be Fixed Right Now

These are the ones that prevent the code from running at all:

```
MUST FIX (crashes or wrong paper numbers):
  evaluate.py  — complete rewrite needed (issues 1-8, 22)
  gym_wrapper.py — fix self-test assertions (issue 10)
  gym_wrapper.py — fix class docstring (issue 11)

SHOULD FIX (silent wrong behavior):
  train.py     — fix resume empty case (issue 12)
  train.py     — fix best-model selection across densities (issue 19)

CAN DELETE (dead code, zero impact on training):
  swarm_env.py — delete _ray_circle_intersection, _ray_wall_intersection
  networks.py  — delete SwarmActorCriticPolicy
  train.py     — remove success_reward_threshold parameter

DO NOTHING (intentional design):
  Neighbor zeros in Phase 1 (#17)
  0-reward intermediate steps (#21)
  _DummyMlpExtractor (#16) — just pin SB3 version
```

---

## Speed & Synchronization Notes

**Training speed** is already well-optimized:
- LiDAR is vectorized NumPy (not Python loops) ✓
- 7 parallel environments via SubprocVecEnv ✓
- No unnecessary Python objects in the hot path ✓

**What will actually slow training:**
1. BFS solvability check at every episode reset — runs on a 100×100 grid.
   At density 0.25 with 20 retry attempts in the worst case, this can take
   0.5-2 seconds per reset. With 7 envs and ~3,000 episodes across 20M steps,
   that is ~3,000 × 1.5s = ~75 minutes in reset overhead alone.
   This is the single largest performance cost. It cannot be easily avoided
   because the BFS is what guarantees map solvability.

2. Obstacle collision loop in `step()` iterates over all obstacles per drone.
   At d=0.25 with ~15-20 obstacles, this is 10 drones × 20 obstacles = 200
   distance checks per step. This is Python, not NumPy. Acceptable for now.

**Evaluation speed:**
- Single env, sequential — expected ~1 minute per 100 episodes for 1000 total.
- For paper results (1000 episodes) this is ~10 minutes. Acceptable.

**Synchronization** (SubprocVecEnv):
- Each subprocess has its own Python interpreter and NumPy state ✓
- No shared memory issues ✓
- `env_method("set_density", density)` sends a command to all subprocesses
  synchronously ✓ (uses subprocess pipes, SB3 handles this correctly)
