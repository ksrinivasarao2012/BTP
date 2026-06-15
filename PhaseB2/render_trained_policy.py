import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import numpy as np
import matplotlib.pyplot as plt
from stable_baselines3 import PPO
from gym_wrapper import SwarmVecEnv

def main():
    model_path = "checkpoints/phase2/model_stage1"
    
    if not os.path.exists(f"{model_path}.zip"):
        print(f"Error: Model checkpoint {model_path}.zip not found.")
        return

    print(f"Loading trained policy from {model_path}...")
    model = PPO.load(model_path)
    
    # Initialize env with communication enabled
    env = SwarmVecEnv(density=0.05, enable_communication=True, seed=42)
    env.swarm_env.MAX_STEPS = 150
    
    plt.ion()
    fig = plt.figure(figsize=(8, 8))
    
    n_episodes = 5
    for ep in range(n_episodes):
        print(f"\n--- Episode {ep + 1}/{n_episodes} ---")
        obs = env.reset()
        done = False
        step = 0
        
        while not done:
            step += 1
            # Predict actions using the policy
            action, _ = model.predict(obs, deterministic=True)
            
            # Step the environment
            obs, rewards, dones, infos = env.step(action)
            done = np.all(dones)
            
            # Render using matplotlib
            env.swarm_env.render()
            
            # Print status update
            active_count = len(env.swarm_env.active_drones)
            print(f"Step {step:3d} | Active Drones: {active_count:2d}", end="\r")
            
            if done:
                break
        
        print(f"\nEpisode {ep + 1} finished in {step} steps.")
        plt.pause(2.0)  # Pause between episodes
        
    plt.ioff()
    plt.show()
    env.close()

if __name__ == "__main__":
    main()
