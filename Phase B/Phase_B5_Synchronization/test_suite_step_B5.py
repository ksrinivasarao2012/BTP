import numpy as np
import time
import torch
torch.set_num_threads(1)
import json
import glob
import os
import sys
from stable_baselines3 import PPO
from swarm_env_step_B5 import SwarmLidarEnv_StepB5 as SwarmLidarEnv
from train_step_B5_sync import MAPPO_Policy_B5 as MAPPO_Policy, MAPPO_Extractor_B5 as MAPPO_Extractor

# ======================================================
#  PHASE B5: Test Suite (Synchronization Evaluation)
#  120-dim Observation | Action-Sharing | TTC Rewards
# ======================================================

def run_evaluation(env, model, num_episodes, description, options_list=None, base_seed=None, log_trajectories=False, output_dir=None):
    """Run N episodes and tally successes vs collisions using the infos['cause'] tag."""
    if log_trajectories and output_dir:
        os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  TEST (B5 SYNC): {description}")
    print(f"  Episodes: {num_episodes}")
    if base_seed is not None:
        print(f"  Base Seed: {base_seed}")
    print(f"{'='*60}")

    total_success = 0
    total_collisions = 0
    total_timeouts = 0
    total_episode_all_success = 0
    total_episode_any_success = 0
    total_steps = 0
    episode_times = []

    for ep in range(num_episodes):
        options = options_list[ep % len(options_list)] if options_list else {"spawn_mode": "random"}
        current_seed = base_seed + ep if base_seed is not None else None
        obs_d, info_d = env.reset(seed=current_seed, options=options)

        start_time = time.time()
        step_count = 0
        ep_successes = 0
        ep_collisions = 0
        tallied_agents = set()

        current_goal_x, current_goal_y = env.goal[0], env.goal[1]
        current_obstacles_str = ";".join([f"{o[0]},{o[1]},{o[2]}" for o in env.obstacles])
        
        f_csv = None
        if log_trajectories and output_dir:
            csv_path = os.path.join(output_dir, f"ep_{ep+1}.csv")
            f_csv = open(csv_path, 'w')
            f_csv.write("Step,Agent,X,Y,Goal_X,Goal_Y,Obstacles\n")

        while env.agents:
            actions = {}
            for agent in env.agents:
                obs = obs_d[agent]
                action, _ = model.predict(obs, deterministic=True)
                actions[agent] = action
                if f_csv:
                    idx = env.agent_name_mapping[agent]
                    pos = env.positions[idx]
                    f_csv.write(f"{step_count},{agent},{pos[0]:.3f},{pos[1]:.3f},{current_goal_x:.3f},{current_goal_y:.3f},\"{current_obstacles_str}\"\n")

            obs_d, rewards, terms, truncs, infos = env.step(actions)
            step_count += 1
            for agent in list(env.possible_agents):
                if agent not in tallied_agents and agent in infos and "cause" in infos[agent]:
                    cause = infos[agent]["cause"]
                    if cause == "success":
                        ep_successes += 1
                        tallied_agents.add(agent)
                    elif cause == "collision":
                        ep_collisions += 1
                        tallied_agents.add(agent)

        elapsed = time.time() - start_time
        episode_times.append(elapsed)
        total_steps += step_count
        num_agents = len(env.possible_agents)

        total_success += ep_successes
        total_collisions += ep_collisions
        total_timeouts += (num_agents - ep_successes - ep_collisions)

        if ep_successes == num_agents:
            total_episode_all_success += 1
        if ep_successes > 0:
            total_episode_any_success += 1

        if (ep + 1) % max(1, num_episodes // 10) == 0:
            print(f"  Progress: {ep+1}/{num_episodes} | Drone successes: {total_success} | Collisions: {total_collisions} | Timeouts: {total_timeouts}")

        if f_csv:
            f_csv.close()

    total_drones_spawned = num_episodes * len(env.possible_agents)

    success_rate = (total_success / total_drones_spawned) * 100
    collision_rate = (total_collisions / total_drones_spawned) * 100
    timeout_rate = (total_timeouts / total_drones_spawned) * 100
    avg_steps = total_steps / num_episodes
    avg_time = np.mean(episode_times)
    total_time = sum(episode_times)

    print(f"\n{'='*42}")
    print(f"  RESULTS: {description}")
    print(f"{'='*42}")
    print(f"Total Episodes Run: {num_episodes}")
    print(f"Total Drones Evaluated: {total_drones_spawned}")
    print(f"Time Taken: {total_time:.2f} seconds")
    print(f"Average Steps/Episode: {avg_steps:.1f}")
    print(f"{'-'*42}")
    print(f"\U0001F3AF Success Rate:   {success_rate:.2f}% ({total_success})")
    print(f"\U0001F4A5 Collision Rate: {collision_rate:.2f}% ({total_collisions})")
    print(f"\u23F3 Timeout Rate:   {timeout_rate:.2f}% ({total_timeouts})")
    print(f"{'='*42}")

    return total_success, total_collisions, total_timeouts, total_drones_spawned, avg_time


def run_random_test(model_path, num_episodes, description="Random Spread B5", seed=None, log_trajectories=None, output_dir=None):
    """Run N episodes with randomly generated obstacles (using the density generator)."""
    env = SwarmLidarEnv(render_mode=None)
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy})
    options = [{"spawn_mode": "random"}] * num_episodes
    do_log = log_trajectories if log_trajectories is not None else (num_episodes <= 10)
    return run_evaluation(env, model, num_episodes, description, options, base_seed=seed, log_trajectories=do_log, output_dir=output_dir)


def generate_clustered_positions(cluster_center, cluster_size=3.0, min_dist=0.6, n_drones=10):
    positions = []
    max_attempts = 500
    cx, cy = cluster_center
    half = cluster_size / 2.0
    for i in range(n_drones):
        for attempt in range(max_attempts):
            x = np.random.uniform(cx - half, cx + half)
            y = np.random.uniform(cy - half, cy + half)
            x = np.clip(x, 1.0, 19.0)
            y = np.clip(y, 1.0, 19.0)
            valid = True
            for px, py in positions:
                if np.sqrt((x - px)**2 + (y - py)**2) < min_dist:
                    valid = False
                    break
            if valid:
                positions.append([x, y])
                break
        else:
            x = np.random.uniform(cx - half - 0.5, cx + half + 0.5)
            y = np.random.uniform(cy - half - 0.5, cy + half + 0.5)
            x = np.clip(x, 1.0, 19.0)
            y = np.clip(y, 1.0, 19.0)
            positions.append([x, y])
    return positions


def run_clustered_test(model_path, num_episodes, description="Dense Cluster B5", seed=None, log_trajectories=None, output_dir=None):
    """Start all drones in a tight cluster using the environment's hardened spawner."""
    env = SwarmLidarEnv(render_mode=None)
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy})

    if seed is not None:
        np.random.seed(seed)

    options_list = []
    for _ in range(num_episodes):
        # Let the environment generate a safe, clustered spawn with obstacles checked
        obs_d, info_d = env.reset(options={"spawn_mode": "clustered"})
        
        # Ensure the goal is far enough (min 8.0m)
        cluster_cx, cluster_cy = env._cached_spawn_center if hasattr(env, "_cached_spawn_center") else (10, 10)
        gx, gy = env.goal
        
        for _ in range(500): # Reroll goal if too close or overlapping
            env.goal = np.array([gx, gy], dtype=np.float32)
            if np.sqrt((gx - cluster_cx)**2 + (gy - cluster_cy)**2) > 8.0 and env._validate_obstacles():
                break
            gx = np.random.uniform(1.0, 19.0)
            gy = np.random.uniform(1.0, 19.0)
        
        options_list.append({
            "start_positions": env.positions.copy(),
            "goal": [gx, gy],
            "obstacles": env.obstacles.copy()
        })

    do_log = log_trajectories if log_trajectories is not None else (num_episodes <= 10)
    return run_evaluation(env, model, num_episodes, description, options_list, base_seed=seed, log_trajectories=do_log, output_dir=output_dir)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_suite_step_B5.py <model_path> [1k|cluster|all]")
        print("  1k       : Runs 1,000 random episodes")
        print("  cluster  : Runs 1,000 clustered-start episodes")
        print("  all      : Runs both 1k random + cluster")
        sys.exit(1)

    model_path = sys.argv[1]
    mode = sys.argv[2]

    if not os.path.exists(model_path):
        print(f"Model not found: {model_path}")
        sys.exit(1)

    if mode == "1k":
        run_random_test(model_path, 1000, "1K Random Spawn (B5 Sync)")
    elif mode == "cluster":
        run_clustered_test(model_path, 1000, "1K Clustered Starts (B5 Sync)")
    elif mode == "all":
        run_random_test(model_path, 1000, "1K Random Spawn (B5 Sync)")
        run_clustered_test(model_path, 1000, "1K Clustered Starts (B5 Sync)")
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)
