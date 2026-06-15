"""
Diagnostic: Compare trained policy vs greedy baseline.

Loads the trained model and runs it for 200 episodes at density 0.05,
tracking where drones actually go and die.

Key question: do they approach the goal like greedy does, or do they
approach-then-peel-away?
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import numpy as np
from collections import Counter
from stable_baselines3 import PPO
from gym_wrapper import SwarmVecEnv

N_EPISODES = 50  # Increased for statistically robust diagnostic
DENSITY = 0.05
MODEL_PATH = "checkpoints/phase2/model_stage1"


def run_trained_policy():
    """Run trained policy and measure where drones die."""

    # Try to load model
    try:
        model = PPO.load(MODEL_PATH)
        print(f"[OK] Loaded model from {MODEL_PATH}")
    except Exception as e:
        print(f"[FAIL] Failed to load model: {e}")
        print(f"  Available checkpoints:")
        import glob
        for ckpt in sorted(glob.glob("checkpoints/phase2/model_*")):
            print(f"    {ckpt}")
        return

    cause_counter = Counter()
    death_dists_by_cause = {"drone_collision": [], "obstacle_collision": [],
                            "wall_collision": [], "success": []}
    min_dists_per_drone = []  # Minimum distance to goal achieved by each drone

    success_count = 0
    total_drones = 0

    for ep in range(N_EPISODES):
        env = SwarmVecEnv(density=DENSITY, seed=2000 + ep,
                          enable_communication=True)
        env.swarm_env.MAX_STEPS = 150
        obs, _ = env.reset()
        goal = env.swarm_env.goal.copy()
        total_drones += env.swarm_env.N_DRONES

        # Track min distance per drone this episode
        drone_min_dist = {i: 100.0 for i in range(env.swarm_env.N_DRONES)}

        episode_done = False
        step_count = 0
        while not episode_done:
            step_count += 1
            # Use trained policy (predict actions for all 10 drones in parallel)
            action, _ = model.predict(obs, deterministic=True)

            # SNAPSHOT: Record all active drone distances BEFORE step (before positions get erased at [-100, -100])
            dist_now = {}
            for did in range(env.swarm_env.N_DRONES):
                if did in env.swarm_env.active_drones:
                    dist = np.linalg.norm(goal - env.swarm_env.drone_positions[did])
                    dist_now[did] = dist
                    drone_min_dist[did] = min(drone_min_dist[did], dist)

            obs, rew, dones, infos = env.step(action)
            episode_done = np.all(dones)

            # Collect causes from infos
            for did in range(env.swarm_env.N_DRONES):
                info = infos[did]
                cause = info.get("cause")
                if cause:
                    cause_counter[cause] += 1

                    if cause == "success":
                        success_count += 1
                        death_dists_by_cause["success"].append(0.0)
                    else:
                        # Use PRE-STEP distance snapshot (true physical location), not post-erase [-100, -100]
                        death_at_dist = dist_now.get(did, 20.0)
                        death_at_dist = min(death_at_dist, 20.0)
                        if cause in death_dists_by_cause:
                            death_dists_by_cause[cause].append(death_at_dist)

                    # Record minimum approach distance
                    min_dists_per_drone.append(drone_min_dist[did])

        env.close()

    print("=" * 70)
    print(f"  TRAINED POLICY: {N_EPISODES} episodes, density={DENSITY}")
    print(f"  {total_drones} total drone-trajectories")
    print("=" * 70)

    print(f"\n  OUTCOME BREAKDOWN (per drone):")
    for cause in ["success", "drone_collision", "obstacle_collision",
                  "wall_collision", "timeout"]:
        n = cause_counter.get(cause, 0)
        pct = 100.0 * n / total_drones if total_drones > 0 else 0
        print(f"    {cause:20s}: {n:5d}  ({pct:5.1f}%)")

    print(f"\n  CLOSEST APPROACH (min distance to goal achieved by each drone):")
    if min_dists_per_drone:
        min_dists = np.array(min_dists_per_drone)
        print(f"    mean={min_dists.mean():5.2f}m  "
              f"median={np.median(min_dists):5.2f}m  "
              f"min={min_dists.min():4.2f}  max={min_dists.max():5.2f}")

    print(f"\n  WHERE drones die (distance-to-goal at death):")
    for cause in ["success", "drone_collision", "obstacle_collision", "wall_collision"]:
        d = np.array(death_dists_by_cause[cause])
        if len(d) == 0:
            continue
        print(f"    {cause:20s}: mean={d.mean():5.2f}m  "
              f"median={np.median(d):5.2f}m  min={d.min():4.2f}  max={d.max():5.2f}")

    print("\n" + "=" * 70)
    print("  COMPARISON vs GREEDY BASELINE:")
    print("    Greedy: 23% success, 40% drone collision")
    print("    Greedy: Drones approach to ~3m from goal then crash")
    print("=" * 70)


if __name__ == "__main__":
    run_trained_policy()
