"""
Diagnostic: Run a few episodes with a random policy and print
the BREAKDOWN of each reward component per step.

This tells us exactly which signal dominates and whether the
reward shaping is balanced.
"""
import numpy as np
from swarm_env import SwarmEnv

env = SwarmEnv(target_density=0.0, seed=42)

PROGRESS_SCALE = 5.0
GAMMA_SHAPING = 0.99
NEAR_MISS_DIST = 0.5
NEAR_MISS_PENALTY = 10.0
SCHOOL_ZONE_SPEED = 0.35

N_EPISODES = 5

for ep in range(N_EPISODES):
    obs, _ = env.reset()

    # Accumulators per component (aggregated across all drones)
    totals = {
        "step_penalty": 0.0,
        "progress": 0.0,
        "near_miss": 0.0,
        "school_zone": 0.0,
        "goal": 0.0,
        "drone_coll": 0.0,
        "wall_coll": 0.0,
    }
    step_count = 0
    n_success = 0
    n_drone_coll = 0

    while env.active_drones and env.step_count < env.MAX_STEPS:
        # Random actions
        actions = {d: np.random.uniform(-1, 1, 2) for d in env.active_drones}

        # --- Manually compute reward breakdown BEFORE env.step ---
        dist_before = {d: env.get_shortest_path_distance(env.drone_positions[d])
                       for d in env.active_drones}

        # Count near-miss pairs at this moment
        active = list(env.active_drones)
        nm_penalty_total = 0.0
        sz_penalty_total = 0.0
        for i, d in enumerate(active):
            close = 0
            for j, n in enumerate(active):
                if d == n:
                    continue
                sep = np.linalg.norm(env.drone_positions[d] - env.drone_positions[n])
                if sep < NEAR_MISS_DIST:
                    nm_penalty_total -= NEAR_MISS_PENALTY * (NEAR_MISS_DIST - sep)
                    close += 1
            if close > 0:
                speed = np.linalg.norm(env.drone_velocities[d])
                safe = env.V_MAX * SCHOOL_ZONE_SPEED
                if speed > safe:
                    sp = ((speed - safe) / env.V_MAX) ** 2
                    sz_penalty_total -= sp * close * 2.0

        # Step
        obs, rewards, dones, truncated, infos = env.step(actions)
        step_count += 1

        # Step penalty
        totals["step_penalty"] += -0.02 * len(active)

        # Progress
        for d in active:
            if d in env.active_drones or d in infos:
                if d in dist_before:
                    new_d_val = env.get_shortest_path_distance(env.drone_positions[d]) \
                        if d in env.active_drones else 0.0
                    old_d_val = dist_before[d]
                    # Only count for drones that didn't die
                    if d in env.active_drones:
                        totals["progress"] += PROGRESS_SCALE * (old_d_val - GAMMA_SHAPING * new_d_val)

        totals["near_miss"] += nm_penalty_total
        totals["school_zone"] += sz_penalty_total

        # Terminal events
        for d, info in infos.items():
            cause = info.get("cause")
            if cause == "success":
                totals["goal"] += 50.0
                n_success += 1
            elif cause == "drone_collision":
                totals["drone_coll"] += -10.0
                n_drone_coll += 1
            elif cause == "wall_collision":
                totals["wall_coll"] += -15.0

    print(f"\n{'='*60}")
    print(f"  EPISODE {ep+1}  |  {step_count} steps  |  "
          f"{n_success} success  |  {n_drone_coll} drone collisions")
    print(f"{'='*60}")
    for name, val in totals.items():
        per_step = val / max(step_count, 1)
        bar_len = int(min(abs(per_step) * 20, 40))
        bar = ("+" if val >= 0 else "-") * bar_len
        print(f"  {name:15s}: {val:+10.1f}  (per step: {per_step:+7.3f})  {bar}")
    print(f"  {'TOTAL':15s}: {sum(totals.values()):+10.1f}")
