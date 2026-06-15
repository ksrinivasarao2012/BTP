"""
Collision diagnostic — NO training.

Runs the env with a fixed "head straight to goal" greedy policy and records,
for every drone death, the CAUSE and the DISTANCE-TO-GOAL at death.

This answers: do drones die at spawn, mid-field, or in the goal funnel?
If a perfect straight-line policy still collides heavily, the problem is
structural (geometry), not the learning algorithm.
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import numpy as np
from collections import Counter
from swarm_env import SwarmEnv

N_EPISODES = 10
DENSITY = 0.05  # stage 1 density, same as the failing run


def greedy_action(pos, goal):
    """Unit vector toward goal (the easiest possible policy)."""
    d = goal - pos
    n = np.linalg.norm(d)
    if n < 1e-6:
        return np.zeros(2, dtype=np.float32)
    return (d / n).astype(np.float32)


def run():
    cause_counter = Counter()
    death_dists = {"drone_collision": [], "obstacle_collision": [],
                   "wall_collision": []}
    death_steps = {"drone_collision": [], "obstacle_collision": [],
                   "wall_collision": []}
    success_count = 0
    total_drones = 0
    spawn_min_spacings = []

    for ep in range(N_EPISODES):
        env = SwarmEnv(target_density=DENSITY, seed=1000 + ep)
        env.MAX_STEPS = 150
        obs, _ = env.reset()

        # record tightest spawn spacing
        pos = env.drone_positions.copy()
        dmat = np.linalg.norm(pos[:, None, :] - pos[None, :, :], axis=-1)
        np.fill_diagonal(dmat, np.inf)
        spawn_min_spacings.append(dmat.min())

        goal = env.goal.copy()
        total_drones += env.N_DRONES

        while len(env.active_drones) > 0 and env.step_count < env.MAX_STEPS:
            actions = {}
            for did in list(env.active_drones):
                actions[did] = env.get_shortest_path_direction(env.drone_positions[did])

            # snapshot distances BEFORE step (positions get zeroed on death)
            dist_now = {did: np.linalg.norm(goal - env.drone_positions[did])
                        for did in env.active_drones}

            obs, rew, dones, trunc, infos = env.step(actions)

            for did, info in infos.items():
                cause = info.get("cause")
                if cause is None:
                    continue
                cause_counter[cause] += 1
                if cause == "success":
                    success_count += 1
                elif cause in death_dists:
                    death_dists[cause].append(dist_now.get(did, np.nan))
                    death_steps[cause].append(env.step_count)

    print("=" * 60)
    print(f"  DIAGNOSTIC: {N_EPISODES} episodes, greedy straight-to-goal")
    print(f"  density={DENSITY}, {total_drones} total drone-trajectories")
    print("=" * 60)
    print(f"\n  Spawn min-spacing: mean={np.mean(spawn_min_spacings):.3f}m  "
          f"min={np.min(spawn_min_spacings):.3f}m  "
          f"(collision dist = {2*env.DRONE_RADIUS:.3f}m)")

    print(f"\n  OUTCOME BREAKDOWN (per drone):")
    for cause in ["success", "drone_collision", "obstacle_collision",
                  "wall_collision", "timeout"]:
        n = cause_counter.get(cause, 0)
        print(f"    {cause:20s}: {n:5d}  ({100*n/total_drones:5.1f}%)")

    print(f"\n  WHERE drones die (distance-to-goal at death):")
    for cause in ["drone_collision", "obstacle_collision", "wall_collision"]:
        d = np.array(death_dists[cause])
        d = d[~np.isnan(d)]
        if len(d) == 0:
            continue
        s = np.array(death_steps[cause])
        print(f"    {cause:20s}: dist mean={d.mean():5.2f}m  "
              f"median={np.median(d):5.2f}m  "
              f"min={d.min():4.2f}  max={d.max():5.2f}  |  "
              f"step mean={s.mean():6.1f}")

    # how many drone-collisions happen in the first 3 steps (= spawn cascade)
    dc_steps = np.array(death_steps["drone_collision"])
    if len(dc_steps) > 0:
        early = (dc_steps <= 3).sum()
        print(f"\n  Drone-collisions within first 3 steps (spawn cascade): "
              f"{early}/{len(dc_steps)} ({100*early/len(dc_steps):.1f}%)")
    print("=" * 60)


if __name__ == "__main__":
    run()
