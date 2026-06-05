import numpy as np
from stable_baselines3 import PPO
import os
import sys
import time
import pygame

# Add paths for environment imports
sys.path.append(os.path.abspath("./Hardened_Baseline"))
sys.path.append(os.path.abspath("./Vanilla_Model"))

from swarm_env_step_A import SwarmLidarEnv_StepA
from swarm_env_vanilla import SwarmLidarEnv_Vanilla

def run_visual_episode(model_path, env_class, label, seed=42):
    print(f"\n--- Visualizing {label} ---")
    model = PPO.load(model_path)
    env = env_class(render_mode="human")
    
    # Generate a fixed cluster for consistency
    np.random.seed(seed)
    cx, cy = 10.0, 10.0
    positions = []
    for _ in range(10):
        for _ in range(500):
            x, y = np.random.uniform(cx - 0.75, cx + 0.75), np.random.uniform(cy - 0.75, cy + 0.75)
            if all(np.linalg.norm(np.array([x,y]) - np.array(p)) >= 0.3 for p in positions):
                positions.append([x, y])
                break
        else: positions.append([cx, cy])
    
    gx, gy = 18.0, 18.0 # Fixed goal for visualization
    options = {"start_positions": positions, "goal": [gx, gy]}
    
    obs, _ = env.reset(options=options)
    
    running = True
    while running:
        actions = {}
        # Master environment is Multi-Agent ParallelEnv
        if isinstance(obs, dict):
            for agent in env.agents:
                action, _ = model.predict(obs[agent], deterministic=True)
                actions[agent] = action
            obs, rewards, terminations, truncations, infos = env.step(actions)
            env.render()
            if not env.agents: running = False
        # If it's a wrapped VecEnv or similar (not the case here but for safety)
        else:
            action, _ = model.predict(obs, deterministic=True)
            obs, rewards, dones, infos = env.step(action)
            env.render()
            if any(dones): running = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                sys.exit()

    time.sleep(1)
    env.close()

if __name__ == "__main__":
    master_model = "./Hardened_Baseline/models/step_A_foundation_model"
    vanilla_model = "./Vanilla_Model/vanilla_fixed_physics_model"
    
    # Run Vanilla first
    run_visual_episode(vanilla_model, SwarmLidarEnv_Vanilla, "Vanilla (Fixed Physics)", seed=42)
    
    # Run Master second
    run_visual_episode(master_model, SwarmLidarEnv_StepA, "Master (Hardened)", seed=42)
    
    pygame.quit()
    print("\nVisualization complete!")
