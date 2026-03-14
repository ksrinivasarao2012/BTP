#!/usr/bin/env python3
"""
PHASE B: Multi-Agent Training Script (Static Obstacles)
Curriculum: Sparse Field (B1) → Dense Forest (B2)

Simple, stable version using single environment.
"""

import os
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from swarm_env_step_B import SwarmLidarEnv_StepB

def make_env(target_density=0.20):
    """Create a single environment with specific density."""
    def _init():
        env = SwarmLidarEnv_StepB(render_mode=None)
        env.target_density = target_density
        return env
    return _init

def train_step_B():
    print("🚀 Initializing Phase B Training (0 Traitors, STATIC OBSTACLES)...")
    
    # =========================================================
    #  PHASE B1: The Sparse Field (Low Density → Learn LiDAR)
    # =========================================================
    print("\n" + "="*60)
    print("  PHASE B1: THE SPARSE FIELD")
    print("  Density: 10% | Goal: Learn LiDAR-to-Motor coupling")
    print("="*60)
    
    # Wrap for SB3 with DummyVecEnv
    wrapped_env_b1 = DummyVecEnv([make_env(target_density=0.10)])
    
    # Manually set observation and action spaces
    dummy_env = SwarmLidarEnv_StepB(render_mode=None)
    obs_space = dummy_env.observation_space(dummy_env.possible_agents[0])
    act_space = dummy_env.action_space(dummy_env.possible_agents[0])
    wrapped_env_b1.observation_space = obs_space
    wrapped_env_b1.action_space = act_space
    
    # Load Phase A foundation model as warm start
    PHASE_A_MODEL = "../Phase A/models/step_A_foundation_model.zip"
    
    if os.path.exists(PHASE_A_MODEL):
        print(f"🤖 Loading Phase A model from {PHASE_A_MODEL} as warm start...")
        model = PPO.load(PHASE_A_MODEL, env=wrapped_env_b1)
        # Update learning rate and entropy for B1
        model.learning_rate = 3e-4
        model.ent_coef = 0.01
    else:
        print("⚠️  No Phase A model found. Training from scratch...")
        model = PPO(
            "MlpPolicy",
            wrapped_env_b1,
            learning_rate=3e-4,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,
            verbose=1,
            tensorboard_log="./ppo_swarm_tensorboard/"
        )
    
    B1_TIMESTEPS = 1_000_000
    print(f"\n🔥 Phase B1: Training for {B1_TIMESTEPS:,} timesteps (Sparse Field)...")
    print("   Obstacles: ~10% density (few scattered obstacles)")
    print("   TensorBoard: tensorboard --logdir ./ppo_swarm_tensorboard/\n")
    
    model.learn(total_timesteps=B1_TIMESTEPS, reset_num_timesteps=True)
    
    # Save B1 checkpoint
    os.makedirs("./models", exist_ok=True)
    model.save("./models/step_B1_sparse_field")
    print("✅ Phase B1 Complete! Saved to ./models/step_B1_sparse_field.zip")
    
    wrapped_env_b1.close()
    
    # =========================================================
    #  PHASE B2: The Dense Forest (High Density → Complex Paths)
    # =========================================================
    print("\n" + "="*60)
    print("  PHASE B2: THE DENSE FOREST")
    print("  Density: 20% | Goal: Complex pathfinding & detours")
    print("="*60)
    
    # Create new environment with 20% density
    # Wrap for SB3
    wrapped_env_b2 = DummyVecEnv([make_env(target_density=0.20)])
    wrapped_env_b2.observation_space = obs_space
    wrapped_env_b2.action_space = act_space
    
    # Fine-tune the B1 model with lower LR for stability
    model = PPO.load("./models/step_B1_sparse_field.zip", env=wrapped_env_b2)
    model.learning_rate = 5e-5
    model.ent_coef = 0.005
    
    B2_TIMESTEPS = 2_000_000
    print(f"\n🔥 Phase B2: Training for {B2_TIMESTEPS:,} timesteps (Dense Forest)...")
    print("   Obstacles: ~20% density (complex obstacle fields)")
    print("   TensorBoard: tensorboard --logdir ./ppo_swarm_tensorboard/\n")
    
    model.learn(total_timesteps=B2_TIMESTEPS, reset_num_timesteps=False)
    
    # Save final B model
    model.save("./models/step_B_foundation_model")
    print("✅ Phase B2 Complete! Final model saved to ./models/step_B_foundation_model.zip")
    
    wrapped_env_b2.close()
    print("\n🎯 Phase B Training Pipeline Complete!")

if __name__ == "__main__":
    import torch
    print(f"PyTorch using device: {torch.device('cuda' if torch.cuda.is_available() else 'cpu')}")
    train_step_B()
