import os
import pygame
import numpy as np
import supersuit as ss
from stable_baselines3 import PPO
from stable_baselines3.ppo import MlpPolicy
from swarm_env_step_A import SwarmLidarEnv_StepA

# ======================================================
#  PHASE 4 - STEP A: Multi-Agent Training Script
# ======================================================

def train_step_A():
    print("🚀 Initializing Step A Training (0 Traitors, 0 Obstacles)...")
    
    # 1. Instantiate the PettingZoo Environment
    env = SwarmLidarEnv_StepA(render_mode=None)
    
    # SB3 compatibility wrapper
    # Since all agents have the exact same observation and action space,
    # we can treat this practically as a single-agent environment generating a batch of 10!
    # SB3 requires natively vectorized environments for parallel agent processing.
    from stable_baselines3.common.vec_env import VecEnv
    
    class SB3Wrapper(VecEnv):
        def __init__(self, pz_env):
            self.pz_env = pz_env
            self.agents = pz_env.possible_agents
            self.num_envs = len(self.agents)
            
            obs_space = pz_env.observation_space(self.agents[0])
            act_space = pz_env.action_space(self.agents[0])
            super().__init__(self.num_envs, obs_space, act_space)
            
        def reset(self):
            obs_d, _ = self.pz_env.reset()
            return np.array([obs_d[agent] for agent in self.agents], dtype=np.float32)

        def step_async(self, actions):
            self.actions = actions

        def step_wait(self):
            # Map batched NumPy array back to PettingZoo dict
            action_dict = {agent: self.actions[i] for i, agent in enumerate(self.agents) if agent in self.pz_env.agents}
            
            obs_d, rew_d, term_d, trunc_d, info_d = self.pz_env.step(action_dict)
            
            # Universal Auto-Reset
            if not self.pz_env.agents:
                obs_d, info_d = self.pz_env.reset()
                obs = np.array([obs_d[agent] for agent in self.agents], dtype=np.float32)
                rews = np.zeros(self.num_envs, dtype=np.float32)
                dones = np.ones(self.num_envs, dtype=bool)
                infos = [{} for _ in range(self.num_envs)]
                return obs, rews, dones, infos
                
            # If agent died, it just inputs zeros until universe resets
            obs = np.array([obs_d.get(agent, np.zeros(self.observation_space.shape)) for agent in self.agents], dtype=np.float32)
            rews = np.array([rew_d.get(agent, 0.0) for agent in self.agents], dtype=np.float32)
            
            # Gym expects `done` to combine term/trunc
            dones = np.array([term_d.get(agent, True) or trunc_d.get(agent, True) for agent in self.agents], dtype=bool)
            infos = [info_d.get(agent, {}) for agent in self.agents]
            
            return obs, rews, dones, infos

        def close(self):
            self.pz_env.close()
            
        def get_attr(self, attr_name, indices=None):
            return [getattr(self, attr_name)] * self.num_envs
            
        def set_attr(self, attr_name, value, indices=None):
            pass
            
        def env_method(self, method_name, *method_args, indices=None, **method_kwargs):
            pass
            
        def env_is_wrapped(self, wrapper_class, indices=None):
            return [False] * self.num_envs

    env = SB3Wrapper(env)

    # 3. Model Configuration (Decentralized Actor-Critic via parameter sharing)
    # This architecture matches the CTDE paradigm for Step A (no Trust Mechanism needed yet)
    
    # Learning Rate Schedule (Linear decay for better final convergence)
    def linear_schedule(initial_value):
        def func(progress_remaining):
            return progress_remaining * initial_value
        return func

    print("🤖 Loading PPO Model for Curriculum Fine-Tuning (clustered + spread spawns)...")
    custom_objects = {
        "learning_rate": 5e-5,  # Low LR for stable fine-tuning the final 2%
        "ent_coef": 0.005        # Lower entropy to exploit the school zone / COM rules aggressively
    }
    model = PPO.load("./models/step_A_foundation_model.zip", env=env, custom_objects=custom_objects)

    # 4. Training Execution — Curriculum: 80% clustered + 20% random spawns
    TOTAL_TIMESTEPS = 1_000_000
    
    print(f"🔥 Starting Curriculum Training for {TOTAL_TIMESTEPS:,} timesteps!")
    print("   Environment now spawns drones in tight 2x2 clusters 80% of the time.")
    print("Check progress: tensorboard --logdir ./ppo_swarm_tensorboard/ \n")
    
    model.learn(total_timesteps=TOTAL_TIMESTEPS, reset_num_timesteps=False)

    # 5. Save the Foundation Model
    os.makedirs("./models", exist_ok=True)
    model.save("./models/step_A_foundation_model")
    print("✅ Training Complete! Model saved to ./models/step_A_foundation_model.zip")

    # Close environment
    env.close()

if __name__ == "__main__":
    import torch
    print(f"PyTorch using device: {torch.device('cuda' if torch.cuda.is_available() else 'cpu')}")
    train_step_A()
