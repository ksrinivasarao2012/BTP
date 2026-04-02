import numpy as np
import time
import torch
torch.set_num_threads(1)
import json
import glob
import os
import sys
from stable_baselines3 import PPO
from swarm_env_step_B import SwarmLidarEnv_StepB
# Import the 100-dim Phase B4 policy architecture
from train_step_B_congestion import MAPPO_Policy_B4 as MAPPO_Policy, MAPPO_Extractor_B4 as MAPPO_Extractor

# ======================================================
#  PHASE B: Test Suite (Static Obstacle Evaluation)
# ======================================================

def run_evaluation(env, model, num_episodes, description, options_list=None, base_seed=None, log_trajectories=False):
    """Run N episodes and tally successes vs collisions using the infos['cause'] tag."""
    csv_filename = None
    if log_trajectories:
        csv_filename = f"trajectories_{description.replace(' ', '_').lower()}.csv"
        f_csv = open(csv_filename, 'w')
        f_csv.write("Step,Agent,X,Y\n")

    print(f"\n{'='*60}")
    print(f"  TEST: {description}")
    print(f"  Episodes: {num_episodes}")
    if base_seed is not None:
        print(f"  Base Seed: {base_seed}")
    print(f"{'='*60}")
    
    total_success = 0
    total_collisions = 0
    total_timeouts = 0
    total_episode_all_success = 0
    total_episode_any_success = 0
    episode_times = []

    for ep in range(num_episodes):
        options = options_list[ep % len(options_list)] if options_list else None
        
        # INJECT THE SEED HERE: Unique seed per episode, reproducible per fold
        current_seed = base_seed + ep if base_seed is not None else None
        obs_d, info_d = env.reset(seed=current_seed, options=options)
        
        start_time = time.time()
        step_count = 0
        ep_successes = 0
        ep_collisions = 0
        
        # Track who has already finished to prevent overcounting
        tallied_agents = set() 
        
        while env.agents:
            actions = {}
            for agent in env.agents:
                idx = env.agent_name_mapping[agent]
                obs = obs_d[agent]
                action, _ = model.predict(obs, deterministic=True)
                actions[agent] = action
                
                # Logging Trajectories for Spaghetti Plots
                if log_trajectories:
                    # [FIX] Use shared state positions array
                    idx = env.unwrapped.agent_name_mapping[agent]
                    pos = env.unwrapped.positions[idx]
                    f_csv.write(f"{step_count},{agent},{pos[0]:.3f},{pos[1]:.3f}\n")
            
            obs_d, rewards, terms, truncs, infos = env.step(actions)
            step_count += 1
            
            # Only tally if we haven't counted this agent yet
            for agent in list(env.possible_agents):
                if agent not in tallied_agents and agent in infos and "cause" in infos[agent]:
                    cause = infos[agent]["cause"]
                    if cause == "success":
                        ep_successes += 1
                        tallied_agents.add(agent)
                    elif cause == "collision":
                        ep_collisions += 1
                        tallied_agents.add(agent)

            if env.render_mode == "human":
                env.render()
                import pygame
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        return 0.0, 0.0, 0.0, 0.0, 0.0  
        
        elapsed = time.time() - start_time
        episode_times.append(elapsed)
        
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
    
    total_drones_spawned = num_episodes * len(env.possible_agents)
    
    success_rate = (total_success / total_drones_spawned) * 100
    collision_rate = (total_collisions / total_drones_spawned) * 100
    timeout_rate = (total_timeouts / total_drones_spawned) * 100
    
    episode_all_success_rate = (total_episode_all_success / num_episodes) * 100
    episode_any_success_rate = (total_episode_any_success / num_episodes) * 100
    avg_time = np.mean(episode_times)
    
    print(f"\n📊 RESULTS: {description}")
    print(f"   Success Rate (per drone):   {success_rate:.1f}% ({total_success}/{total_drones_spawned})")
    print(f"   Collision Rate (per drone): {collision_rate:.1f}% ({total_collisions}/{total_drones_spawned})")
    print(f"   Timeout Rate (per drone):   {timeout_rate:.1f}% ({total_timeouts}/{total_drones_spawned})")
    print(f"   Episode Success (all {len(env.possible_agents)} drones): {episode_all_success_rate:.1f}% ({total_episode_all_success}/{num_episodes})")
    print(f"   Episode Success (>=1 drone):  {episode_any_success_rate:.1f}% ({total_episode_any_success}/{num_episodes})")
    print(f"   Avg Episode Time: {avg_time:.2f}s")
    if log_trajectories:
        f_csv.close()
        print(f"📁 Trajectories saved to {csv_filename}")

    return total_success, total_collisions, total_timeouts, total_drones_spawned, avg_time


def run_basic_edge_cases(model_path, specific_file=None, render=False):
    """Load and run all JSON test cases from test_cases/ directory."""
    env = SwarmLidarEnv_StepB(render_mode="human" if render else None)
    env.test_mode = True
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy})
    
    if specific_file:
        files = [specific_file]
    else:
        files = sorted(glob.glob("test_cases/basic/*.json")) + sorted(glob.glob("test_cases/edge/*.json"))
    
    for filepath in files:
        with open(filepath, "r") as f:
            test_case = json.load(f)
        
        name = test_case["name"]
        desc = test_case.get("description", "")
        scenarios = test_case["scenarios"]
        
        print(f"\n🧪 Loading: {name}")
        print(f"   {desc}")
        
        options_list = []
        for scenario in scenarios:
            opts = {}
            if "start_positions" in scenario:
                opts["start_positions"] = scenario["start_positions"]
            if "goal" in scenario:
                opts["goal"] = scenario["goal"]
            if "obstacles" in scenario:
                opts["obstacles"] = [tuple(obs) for obs in scenario["obstacles"]]
            options_list.append(opts)
        
        run_evaluation(env, model, num_episodes=len(scenarios), description=name, options_list=options_list)
    
    if render:
        import pygame
        pygame.quit()


# ADDED SEED PARAMETER HERE
def run_random_test(model_path, num_ep, description, seed=None, log_trajectories=None):
    """Run N episodes with randomly generated obstacles (using the density generator)."""
    env = SwarmLidarEnv_StepB(render_mode=None)
    env.test_mode = True
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy})
    
    do_log = log_trajectories if log_trajectories is not None else (num_ep <= 10)
    return run_evaluation(env, model, num_ep, description, base_seed=seed, log_trajectories=do_log)


def generate_clustered_positions(cluster_center, cluster_size=2.0, min_dist=0.3, n_drones=10):
    positions = []
    max_attempts = 500
    cx, cy = cluster_center
    half = cluster_size / 2.0
    for i in range(n_drones):
        for attempt in range(max_attempts):
            x = np.random.uniform(cx - half, cx + half)
            y = np.random.uniform(cy - half, cy + half)
            x = np.clip(x, 0.2, 19.8)
            y = np.clip(y, 0.2, 19.8)
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
            x = np.clip(x, 0.2, 19.8)
            y = np.clip(y, 0.2, 19.8)
            positions.append([x, y])
    return positions


# ADDED SEED PARAMETER AND NUMPY SEEDING HERE
def run_clustered_test(model_path, num_episodes, description, seed=None, log_trajectories=None):
    """Start all drones in a tight cluster and place goal far away."""
    env = SwarmLidarEnv_StepB(render_mode=None)
    env.test_mode = True
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy})
    
    # Anchor the numpy random generator for this specific validation fold
    if seed is not None:
        np.random.seed(seed)
        
    options_list = []
    for _ in range(num_episodes):
        cluster_cx = np.random.uniform(3.0, 17.0)
        cluster_cy = np.random.uniform(3.0, 17.0)
        positions = generate_clustered_positions(
            cluster_center=[cluster_cx, cluster_cy],
            cluster_size=2.0,
            min_dist=0.3,
            n_drones=10
        )
        for _ in range(100):
            gx = np.random.uniform(1.0, 19.0)
            gy = np.random.uniform(1.0, 19.0)
            if np.sqrt((gx - cluster_cx)**2 + (gy - cluster_cy)**2) > 8.0:
                break
        options_list.append({"start_positions": positions, "goal": [gx, gy]})
        
    do_log = log_trajectories if log_trajectories is not None else (num_episodes <= 10)
    return run_evaluation(env, model, num_episodes, description, options_list, base_seed=seed, log_trajectories=do_log)


def run_1k_random(model_path):
    """The canonical 1K Random Spawn benchmark for Phase B."""
    run_random_test(model_path, 1000, "1K Random Spawn (20% Density)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_suite_step_B.py <model_path> [basic|edge|1k|cluster|all|<json_file>]")
        print("  basic          : Runs all Basic JSON test cases")
        print("  edge           : Runs all Edge JSON test cases")
        print("  1k             : Runs 1,000 episodes with random 20% density obstacles")
        print("  cluster        : Runs 1,000 clustered-start episodes")
        print("  all            : Runs basic+edge+1k random+cluster")
        print("  <json_file>    : Runs a specific JSON test case with PyGame rendering")
        print("\nExample:")
        print("  python test_suite_step_B.py ./models/step_B_foundation_model.zip basic")
        sys.exit(1)
    
    model_path = sys.argv[1]
    mode = sys.argv[2]
    
    if not os.path.exists(model_path):
        print(f"❌ Model not found: {model_path}")
        sys.exit(1)
    
    if mode == "basic":
        run_basic_edge_cases(model_path)
    elif mode == "edge":
        run_basic_edge_cases(model_path, specific_file=None)
        env = SwarmLidarEnv_StepB(render_mode=None)
        env.test_mode = True
        model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy})
        files = sorted(glob.glob("test_cases/edge/*.json"))
        for filepath in files:
            with open(filepath, "r") as f:
                test_case = json.load(f)
            scenarios = test_case["scenarios"]
            options_list = []
            for scenario in scenarios:
                opts = {}
                if "start_positions" in scenario: opts["start_positions"] = scenario["start_positions"]
                if "goal" in scenario: opts["goal"] = scenario["goal"]
                if "obstacles" in scenario: opts["obstacles"] = [tuple(obs) for obs in scenario["obstacles"]]
                options_list.append(opts)
            run_evaluation(env, model, len(scenarios), test_case["name"], options_list)
    elif mode == "1k":
        num_ep = 1000
        if len(sys.argv) > 3:
            for arg in sys.argv[3:]:
                if arg.isdigit():
                    num_ep = int(arg)
                    break
        run_random_test(model_path, num_ep, f"{num_ep} Random Spawn (20% Density)")
    elif mode == "cluster":
        num_ep = 1000
        if len(sys.argv) > 3:
            for arg in sys.argv[3:]:
                if arg.isdigit():
                    num_ep = int(arg)
                    break
        run_clustered_test(model_path, num_ep, f"{num_ep} Clustered Starts")
    elif os.path.exists(mode):
        render_flag = "--no-render" not in sys.argv
        run_basic_edge_cases(model_path, specific_file=mode, render=render_flag)
    else:
        print(f"❌ Unknown mode: {mode}")
        sys.exit(1)