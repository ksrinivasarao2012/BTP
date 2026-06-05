import numpy as np
import time
import json
import glob
import os
from stable_baselines3 import PPO
from swarm_env_step_A import SwarmLidarEnv_StepA

def run_evaluation(env, model, num_episodes, description, options_list=None):
    successes = 0
    collisions = 0
    timeouts = 0
    total_steps = 0

    start_time = time.time()
    
    for i in range(num_episodes):
        options = options_list[i] if options_list else None
        obs, info = env.reset(options=options)
        
        episode_success = 0
        episode_collision = 0
        episode_steps = 0
        
        while env.agents:
            actions = {}
            for agent in env.agents:
                action, _ = model.predict(obs[agent], deterministic=True)
                actions[agent] = action
                
            obs, rewards, terminations, truncations, infos = env.step(actions)
            
            if getattr(env.unwrapped, 'render_mode', None) == "human":
                env.render()
                time.sleep(0.04) 
                
            episode_steps += 1
            
            for agent, term in terminations.items():
                if term and agent in rewards:
                    cause = infos[agent].get("cause")
                    if cause == "collision":
                        episode_collision += 1
                    elif cause == "success":
                        episode_success += 1
                        
            for agent, trunc in truncations.items():
                if trunc and agent not in terminations:
                    pass

        successes += episode_success
        collisions += episode_collision
        timeouts += (10 - episode_success - episode_collision)
        total_steps += episode_steps
        
        if (i + 1) % 1000 == 0:
            print(f"   ... Processed {i+1}/{num_episodes} episodes")

    duration = time.time() - start_time
    total_drones = num_episodes * 10
    
    print(f"\n{'='*40}")
    print(f" RESULTS: {description}")
    print(f"{'='*40}")
    print(f"Total Episodes Run: {num_episodes}")
    print(f"Total Drones Evaluated: {total_drones}")
    print(f"Time Taken: {duration:.2f} seconds")
    print(f"Average Steps/Episode: {total_steps / num_episodes:.1f}")
    print("-" * 40)
    print(f"🎯 Success Rate:   {(successes / total_drones * 100):.2f}% ({successes})")
    print(f"💥 Collision Rate: {(collisions / total_drones * 100):.2f}% ({collisions})")
    print(f"⏳ Timeout Rate:   {(timeouts / total_drones * 100):.2f}% ({timeouts})")
    print(f"{'='*40}\n")
    
    return successes, collisions, timeouts, total_drones, duration

def run_basic_edge_cases(specific_file=None):
    print("\n[1] Loading Basic Edge Cases from JSON...")
    model = PPO.load("./models/step_A_foundation_model")
    
    # Render visually only if we are watching a specific single case!
    render = "human" if specific_file else None
    env = SwarmLidarEnv_StepA(render_mode=render)
    
    # Load all JSON files in the basic test cases folder
    if specific_file:
        json_path = f"test_cases/basic/{specific_file}"
        if not json_path.endswith('.json'):
            json_path += '.json'
        json_files = [json_path]
    else:
        json_files = glob.glob("test_cases/basic/*.json")
        
    if not json_files or not os.path.exists(json_files[0]):
        print(f"❌ No JSON files found matching {json_files}")
        return
        
    options_list = []
    descriptions = []
    for file in sorted(json_files):
        with open(file, 'r') as f:
            data = json.load(f)
            # The JSON holds an array of scenarios. For basic edge cases, there's usually just 1 per file.
            for scenario in data["scenarios"]:
                options_list.append({
                    "start_positions": scenario["start_positions"],
                    "goal": scenario["goal"]
                })
            descriptions.append(data["name"])

    scenario_name = descriptions[0] if specific_file else "JSON-Loaded Basic Edge Cases"
    print(f"Loaded {len(options_list)} distinct Edge Case Scenarios.")
    
    run_evaluation(env, model, len(options_list), scenario_name, options_list)
    env.close()

def run_random_test(num_episodes, description):
    print(f"[{description}] Generating {num_episodes:,} pure random scenarios...")
    model = PPO.load("./models/step_A_foundation_model")
    env = SwarmLidarEnv_StepA(render_mode=None)
    
    # Generate entirely random setups beforehand
    options_list = []
    for _ in range(num_episodes):
        options_list.append({
            "start_positions": [[np.random.uniform(1.0, 19.0), np.random.uniform(1.0, 19.0)] for _ in range(10)],
            "goal": [np.random.uniform(1.0, 19.0), np.random.uniform(1.0, 19.0)]
        })
        
    res = run_evaluation(env, model, num_episodes, description, options_list)
    env.close()
    return res

def generate_clustered_positions(cluster_center, cluster_size=2.0, min_dist=0.3, n_drones=10):
    """Generate n_drones positions tightly packed in a cluster_size x cluster_size box
    around cluster_center, with guaranteed minimum spacing of min_dist between each pair."""
    positions = []
    max_attempts = 500
    
    cx, cy = cluster_center
    half = cluster_size / 2.0
    
    for i in range(n_drones):
        for attempt in range(max_attempts):
            x = np.random.uniform(cx - half, cx + half)
            y = np.random.uniform(cy - half, cy + half)
            
            # Clamp to field bounds (stay 0.2 from walls to avoid instant wall death)
            x = np.clip(x, 0.2, 19.8)
            y = np.clip(y, 0.2, 19.8)
            
            # Check distance to all previously placed drones
            valid = True
            for px, py in positions:
                if np.sqrt((x - px)**2 + (y - py)**2) < min_dist:
                    valid = False
                    break
            
            if valid:
                positions.append([x, y])
                break
        else:
            # Fallback: if we can't fit, slightly expand the area
            x = np.random.uniform(cx - half - 0.5, cx + half + 0.5)
            y = np.random.uniform(cy - half - 0.5, cy + half + 0.5)
            x = np.clip(x, 0.2, 19.8)
            y = np.clip(y, 0.2, 19.8)
            positions.append([x, y])
    
    return positions

def run_clustered_test(num_episodes, description):
    """Stress test: all 10 drones start in a tight cluster, goal placed far away."""
    print(f"[{description}] Generating {num_episodes:,} clustered scenarios...")
    model = PPO.load("./models/step_A_foundation_model")
    env = SwarmLidarEnv_StepA(render_mode=None)
    
    options_list = []
    for _ in range(num_episodes):
        # Random cluster center (keep away from walls so drones don't spawn OOB)
        cluster_cx = np.random.uniform(3.0, 17.0)
        cluster_cy = np.random.uniform(3.0, 17.0)
        
        # Generate tightly packed positions with safe spacing
        positions = generate_clustered_positions(
            cluster_center=[cluster_cx, cluster_cy],
            cluster_size=2.0,   # 2x2 box
            min_dist=0.3,       # safe above collision threshold of 0.25
            n_drones=10
        )
        
        # Place goal far from the cluster (at least 8 units away)
        for _ in range(100):
            gx = np.random.uniform(1.0, 19.0)
            gy = np.random.uniform(1.0, 19.0)
            dist_to_cluster = np.sqrt((gx - cluster_cx)**2 + (gy - cluster_cy)**2)
            if dist_to_cluster > 8.0:
                break
        
        options_list.append({
            "start_positions": positions,
            "goal": [gx, gy]
        })
    
    res = run_evaluation(env, model, num_episodes, description, options_list)
    env.close()
    return res

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_suite_step_A.py [basic|1k|cluster|<edge_case_filename>]")
        print("  basic               : Runs ALL JSON edge cases silently")
        print("  edge_case_1_...     : Watch a single edge case in PyGame")
        print("  1k                  : Generates and runs 1,000 completely random setups")
        print("  10k                 : Generates and runs 10,000 completely random setups")
        print("  cluster             : 1,000 episodes with drones in tight 2x2 clusters")
        print("  cluster10k          : 10,000 episodes with drones in tight 2x2 clusters")
        sys.exit(1)
        
    mode = sys.argv[1].lower()
    
    if mode == "basic":
        run_basic_edge_cases()
    elif mode == "1k":
        run_random_test(1000, "1K Completely Random Test Cases")
    elif mode == "10k":
        run_random_test(10000, "10k Completely Random Test Cases")
    elif mode == "1m":
        run_random_test(1000000, "1M Completely Random Test Cases")
    elif mode == "cluster":
        run_clustered_test(1000, "1K Clustered Stress Test (2x2 box)")
    elif mode == "cluster10k":
        run_clustered_test(10000, "10K Clustered Stress Test (2x2 box)")
    else:
        # User passed a specific JSON filename to execute visually!
        run_basic_edge_cases(specific_file=mode)

