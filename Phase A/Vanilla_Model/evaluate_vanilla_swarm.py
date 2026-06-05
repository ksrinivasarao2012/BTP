import numpy as np
from stable_baselines3 import PPO
from swarm_env_vanilla import SwarmLidarEnv_Vanilla
import supersuit as ss
import os

def evaluate(num_episodes=1000):
    print(f"Starting Evaluation of Vanilla Swarm Model ({num_episodes} episodes)...", flush=True)
    
    # 1. Setup Environment
    env = SwarmLidarEnv_Vanilla()
    env = ss.black_death_v3(env)
    env = ss.pettingzoo_env_to_vec_env_v1(env)
    env = ss.concat_vec_envs_v1(env, 1, num_cpus=1, base_class='stable_baselines3')

    # 2. Load Model
    model_path = "Vanilla_Model/vanilla_fixed_physics_model"
    if not os.path.exists(model_path + ".zip"):
        # Try local path if running from inside the folder
        model_path = "vanilla_fixed_physics_model"
        
    try:
        model = PPO.load(model_path)
        print("Model loaded successfully.", flush=True)
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    # 3. Stats Tracking
    stats = {"success": 0, "collision": 0, "timeout": 0}
    episodes_finished = 0
    
    # We track drone outcomes differently because agents can finish at different times
    drones_finished = 0

    while episodes_finished < num_episodes:
        obs = env.reset()
        # VecEnv reset returns the initial observation
        
        # We run until the environment indicates a reset (all agents done)
        # In SB3 VecEnv, it resets automatically, so we look for the 'terminal_observation'
        # or we just track 10 agents per episode.
        
        ep_drones_finished = 0
        while ep_drones_finished < 10:
            action, _ = model.predict(obs, deterministic=True)
            obs, rewards, dones, infos = env.step(action)
            
            for info in infos:
                if "cause" in info:
                    stats[info["cause"]] += 1
                    ep_drones_finished += 1
                    drones_finished += 1
        
        episodes_finished += 1
        if episodes_finished % 10 == 0:
            current_success = (stats['success'] / drones_finished) * 100
            current_collision = (stats['collision'] / drones_finished) * 100
            print(f"Progress: {episodes_finished}/{num_episodes} | Success: {current_success:.1f}% | Collision: {current_collision:.1f}%", flush=True)

    # 4. Final Report
    print("\n" + "="*40)
    print("       VANILLA SWARM TEST RESULTS")
    print("="*40)
    print(f"Total Drones Evaluated: {drones_finished}")
    print(f"Success Rate: {(stats['success']/drones_finished)*100:.2f}%")
    print(f"Collision Rate: {(stats['collision']/drones_finished)*100:.2f}%")
    print(f"Timeout Rate: {(stats.get('timeout', 0)/drones_finished)*100:.2f}%")
    print("="*40)

if __name__ == "__main__":
    evaluate(1000)
