import os
import pygame
import supersuit as ss
from stable_baselines3 import PPO
from stable_baselines3.ppo import MlpPolicy
from stable_baselines3.common.vec_env import VecEnv
import numpy as np

# Import the upgraded environment
from swarm_env_step_A import SwarmLidarEnv_StepA

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
        action_dict = {agent: self.actions[i] for i, agent in enumerate(self.agents) if agent in self.pz_env.agents}
        obs_d, rew_d, term_d, trunc_d, info_d = self.pz_env.step(action_dict)
        
        if not self.pz_env.agents:
            obs_d, info_d = self.pz_env.reset()
            obs = np.array([obs_d[agent] for agent in self.agents], dtype=np.float32)
            rews = np.zeros(self.num_envs, dtype=np.float32)
            dones = np.ones(self.num_envs, dtype=bool)
            return obs, rews, dones, [{}] * self.num_envs
            
        obs = np.array([obs_d.get(agent, np.zeros(self.observation_space.shape)) for agent in self.agents], dtype=np.float32)
        rews = np.array([rew_d.get(agent, 0.0) for agent in self.agents], dtype=np.float32)
        dones = np.array([term_d.get(agent, True) or trunc_d.get(agent, True) for agent in self.agents], dtype=bool)
        infos = [info_d.get(agent, {}) for agent in self.agents]
        return obs, rews, dones, infos

    def close(self): self.pz_env.close()
    def get_attr(self, attr_name, indices=None): return [getattr(self, attr_name)] * self.num_envs
    def set_attr(self, attr_name, value, indices=None): pass
    def env_method(self, method_name, *method_args, indices=None, **method_kwargs): pass
    def env_is_wrapped(self, wrapper_class, indices=None): return [False] * self.num_envs

def run_training_experiment(run_name, lr, gamma, ent_coef, batch_size):
    print(f"\n🚀 Starting Run: {run_name}")
    print(f"Parameters -> LR: {lr}, Gamma: {gamma}, Ent_Coef: {ent_coef}, Batch_Size: {batch_size}")
    
    env = SwarmLidarEnv_StepA(render_mode=None)
    env = SB3Wrapper(env)
    
    def linear_schedule(initial_value):
        def func(progress_remaining):
            return progress_remaining * initial_value
        return func

    model = PPO(
        MlpPolicy,
        env,
        verbose=1,
        learning_rate=linear_schedule(lr),
        tensorboard_log="./ppo_swarm_tensorboard_experiments/",
        n_steps=2048,           
        batch_size=batch_size,         
        n_epochs=10,            
        gamma=gamma,            
        ent_coef=ent_coef,
        device="cpu"
    )

    TOTAL_TIMESTEPS = 1_000_000 # 1M is enough to see which curve is learning fastest
    
    model.learn(total_timesteps=TOTAL_TIMESTEPS, tb_log_name=run_name)

    os.makedirs("./models/experiments", exist_ok=True)
    model.save(f"./models/experiments/{run_name}_model")
    env.close()

if __name__ == "__main__":
    import torch
    print(f"PyTorch using device: {torch.device('cuda' if torch.cuda.is_available() else 'cpu')}")
    
    # Define our hyperparameter grid search!
    configs = [
        # Baseline from our single-agent analysis
        {"name": "Exp_1_Baseline", "lr": 3e-4, "gamma": 0.995, "ent_coef": 0.01, "batch": 256},
        
        # High Exploration (Good for avoiding local minima like walls)
        {"name": "Exp_2_High_Entropy", "lr": 3e-4, "gamma": 0.995, "ent_coef": 0.05, "batch": 256},
        
        # Far-Sighted (Forces drone to care more about the distant goal than immediate safety maxing)
        {"name": "Exp_3_Long_Horizon", "lr": 3e-4, "gamma": 0.999, "ent_coef": 0.01, "batch": 256},
        
        # Fast Learning Rate (Aggressive gradient updates)
        {"name": "Exp_4_High_LR", "lr": 1e-3, "gamma": 0.990, "ent_coef": 0.01, "batch": 512},
    ]
    
    for conf in configs:
        run_training_experiment(
            run_name=conf["name"], 
            lr=conf["lr"], 
            gamma=conf["gamma"], 
            ent_coef=conf["ent_coef"], 
            batch_size=conf["batch"]
        )
        
    print("\n✅ All 4 Experimental runs complete!")
    print("Run `tensorboard --logdir ./ppo_swarm_tensorboard_experiments/` to compare models!")
