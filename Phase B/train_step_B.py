import os
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from swarm_env_step_B import SwarmLidarEnv_StepB
from sb3_wrapper import SB3Wrapper # Assuming your wrapper is in this file

def make_env(rank, seed=0, density=0.05):
    """Utility function for multiprocessed env."""
    def _init():
        env = SwarmLidarEnv_StepB(render_mode=None)
        env.target_density = density
        # Ensure each core has a unique random seed
        env.reset(seed=seed + rank)
        return SB3Wrapper(env)
    return _init

def train_step_B():
    # 1. SETUP HARDWARE
    num_cpu = 12  # Using all 12 cores
    print(f"🚀 Initializing 16-Core Parallel Training (160 Drones Total)...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # =========================================================
    #  PHASE B1: The Sparse Field (5% Density)
    # =========================================================
    print("\n--- STARTING PHASE B1 (Sparse) ---")
    env_b1 = SubprocVecEnv([make_env(i, density=0.05) for i in range(num_cpu)])
    
    PHASE_A_MODEL = "../Phase A/models/step_A_foundation_model.zip"
    
    if os.path.exists(PHASE_A_MODEL):
        # We use custom_objects to force the learning rate update upon loading
        model = PPO.load(PHASE_A_MODEL, env=env_b1, custom_objects={"learning_rate": 3e-4})
    else:
        model = PPO("MlpPolicy", env_b1, learning_rate=3e-4, n_steps=1024, 
                    batch_size=256, n_epochs=10, verbose=1, tensorboard_log="./ppo_swarm_tensorboard/")

    model.learn(total_timesteps=2_000_000, reset_num_timesteps=True)
    model.save("./models/step_B1_sparse_field")
    env_b1.close()

    # =========================================================
    #  PHASE B2: The Moderate Forest (10% Density)
    # =========================================================
    print("\n--- STARTING PHASE B2 (Moderate) ---")
    env_b2 = SubprocVecEnv([make_env(i, density=0.10) for i in range(num_cpu)])
    
    # LOAD AND UPDATE: Using custom_objects is the ONLY way to change LR in SB3
    model = PPO.load("./models/step_B1_sparse_field.zip", env=env_b2, 
                     custom_objects={"learning_rate": 5e-5})
    
    model.learn(total_timesteps=1_500_000, reset_num_timesteps=False)
    model.save("./models/step_B2_moderate_forest")
    env_b2.close()

    # =========================================================
    #  PHASE B3: The Dense Forest (20% Density)
    # =========================================================
    print("\n--- STARTING PHASE B3 (Dense) ---")
    env_b3 = SubprocVecEnv([make_env(i, density=0.20) for i in range(num_cpu)])
    
    # FINAL TUNING: Lowering LR to 1e-5 for precision
    model = PPO.load("./models/step_B2_moderate_forest.zip", env=env_b3, 
                     custom_objects={"learning_rate": 1e-5})
    
    model.learn(total_timesteps=2_000_000, reset_num_timesteps=False)
    model.save("./models/step_B_foundation_model")
    env_b3.close()

    print("\n🎯 All 16 cores finished! Final Model: ./models/step_B_foundation_model.zip")

if __name__ == "__main__":
    train_step_B()