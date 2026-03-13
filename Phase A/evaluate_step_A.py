import time
import pygame
import numpy as np
from stable_baselines3 import PPO
from swarm_env_step_A import SwarmLidarEnv_StepA

def evaluate():
    print("👀 Loading trained Step A model...")
    model_path = "./models/step_A_foundation_model"
    model = PPO.load(model_path)
    
    # We use the raw PettingZoo environment for evaluation, no SuperSuit wrappers
    # because we want to see the dictionary output and render it naturally.
    env = SwarmLidarEnv_StepA(render_mode="human")
    
    for episode in range(5):
        print(f"--- Episode {episode + 1} ---")
        obs, info = env.reset()
        
        while env.agents:
            actions = {}
            for agent in env.agents:
                # Predict action using the trained model for each individual drone
                action, _ = model.predict(obs[agent], deterministic=True)
                actions[agent] = action
                
            obs, rewards, terminations, truncations, infos = env.step(actions)
            env.render()
            # Un-comment this if you want to slow down the visuals to watch them closer
            # time.sleep(0.03) 
            
    pygame.quit()
    print("Evaluation complete!")

if __name__ == "__main__":
    evaluate()
