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
            
            # Force PyGame to draw the frame if we are in human observation mode!
            if getattr(env.unwrapped, 'render_mode', None) == "human":
                env.render()
                time.sleep(0.04) # Cap it visually at ~25 FPS so you can actually watch them!
                
            episode_steps += 1
            
            # Tally metrics when an agent terminates
            for agent, term in terminations.items():
                if term and agent in rewards:
                    if rewards[agent] <= -50.0:  # Penalty for collision
                        episode_collision += 1
                    elif rewards[agent] >= 50.0: # Reward for success
                        episode_success += 1
                        
            # Quick hack to make sure we don't count truncations forever if they just timeout
            for agent, trunc in truncations.items():
                if trunc and agent not in terminations:
                    # Timeouts are implicitly handled by subtracting successes and collisions from total
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
        
    run_evaluation(env, model, num_episodes, description, options_list)
    env.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_suite_step_A.py [basic|10k|1m|<edge_case_filename>]")
        print("  basic               : Runs ALL JSON edge cases silently")
        print("  edge_case_1_...     : Watch a single edge case in PyGame")
        print("  1k                  : Generates and runs 1,000 completely random setups")
        print("  10k                 : Generates and runs 10,000 completely random setups")
        print("  1m                  : Generates and runs 1,000,000 completely random setups")
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
    else:
        # User passed a specific JSON filename to execute visually!
        run_basic_edge_cases(specific_file=mode)
