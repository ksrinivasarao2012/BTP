import os
import torch
import torch.nn as nn
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecEnv, VecNormalize
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback, CallbackList
from swarm_env_step_B import SwarmLidarEnv_StepB
from multiprocessing import Process, Pipe

# ======================================================
#  PHASE B: APEX-ULTRA + MAPPO TRAINING SCRIPT
#  Architecture: CTDE (Centralized Training, Decentralized Execution)
#  Sensing: 48-Statistical Lidar
#  Coordination: 520-Dim Global Critic State
# ======================================================

# --- MAPPO Custom Policy ---

class MAPPO_Extractor(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        # Actor pi: input[:99] -> 99 local dims
        # Critic vf: input[99:] -> 520 global dims
        
        # Build Actor (pi)
        pi_layers = []
        last_layer_dim_pi = 99
        for curr_layer_dim in net_arch['pi']:
            pi_layers.append(nn.Linear(last_layer_dim_pi, curr_layer_dim))
            pi_layers.append(activation_fn())
            last_layer_dim_pi = curr_layer_dim
        self.policy_net = nn.Sequential(*pi_layers)

        # Build Critic (vf)
        vf_layers = []
        last_layer_dim_vf = 520
        for curr_layer_dim in net_arch['vf']:
            vf_layers.append(nn.Linear(last_layer_dim_vf, curr_layer_dim))
            vf_layers.append(activation_fn())
            last_layer_dim_vf = curr_layer_dim
        self.value_net = nn.Sequential(*vf_layers)

        self.latent_dim_pi = last_layer_dim_pi
        self.latent_dim_vf = last_layer_dim_vf

    def forward(self, features):
        return self.policy_net(features[:, :99]), self.value_net(features[:, 99:])

    def forward_actor(self, features):
        return self.policy_net(features[:, :99])

    def forward_critic(self, features):
        return self.value_net(features[:, 99:])

class MAPPO_Policy(ActorCriticPolicy):
    def __init__(self, observation_space, action_space, lr_schedule, *args, **kwargs):
        super().__init__(observation_space, action_space, lr_schedule, *args, **kwargs)

    def _build_mlp_extractor(self) -> None:
        self.mlp_extractor = MAPPO_Extractor(self.features_dim, self.net_arch, self.activation_fn)

# --- Callbacks & Scheduling ---

def get_entropy_coef(step):
    """Linearly decay entropy from 0.025 (0-5M) to 0.01 (5M-10M)"""
    if step < 5_000_000:
        return 0.025
    else:
        decay_steps = 5_000_000
        progress = (step - 5_000_000) / decay_steps
        return 0.025 - (progress * (0.025 - 0.01))

class EntropyDecayCallback(BaseCallback):
    def __init__(self, verbose=0):
        super().__init__(verbose)

    def _on_step(self) -> bool:
        new_ent_coef = get_entropy_coef(self.model.num_timesteps)
        self.model.ent_coef = new_ent_coef
        self.model.ent_coef_tensor = torch.tensor(
            new_ent_coef,
            dtype=torch.float32,
            device=self.model.device
        )
        return True

# --- Environment Parallelization ---

def worker(remote, parent_remote, density, drone_radius, safety_radius):
    parent_remote.close()
    env = SwarmLidarEnv_StepB(render_mode=None, target_density=density, 
                             drone_radius=drone_radius, safety_radius=safety_radius)
    try:
        while True:
            cmd, data = remote.recv()
            if cmd == 'step':
                actions = {f"drone_{i}": data[i] for i in range(10)}
                obs_d, rew_d, term_d, trunc_d, info_d = env.step(actions)
                if not env.agents:
                    obs_d, info_d = env.reset()
                
                obs = np.array([obs_d.get(f"drone_{i}", np.zeros(env.observation_space("drone_0").shape)) for i in range(10)], dtype=np.float32)
                rews = np.array([rew_d.get(f"drone_{i}", 0.0) for i in range(10)], dtype=np.float32)
                dones = np.array([term_d.get(f"drone_{i}", True) or trunc_d.get(f"drone_{i}", True) for i in range(10)], dtype=bool)
                infos = [info_d.get(f"drone_{i}", {}) for i in range(10)]
                remote.send((obs, rews, dones, infos))
            elif cmd == 'reset':
                obs_d, info_d = env.reset()
                obs = np.array([obs_d.get(f"drone_{i}", np.zeros(env.observation_space("drone_0").shape)) for i in range(10)], dtype=np.float32)
                remote.send(obs)
            elif cmd == 'close':
                env.close(); remote.close(); break
            elif cmd == 'set_density':
                env.set_target_density(data)
            elif cmd == 'get_spaces':
                remote.send((env.observation_space("drone_0"), env.action_space("drone_0")))
    except Exception as e:
        import traceback
        print(f"[Worker ERROR] {e}")
        traceback.print_exc()
        remote.close()

class MultiProcessPZEnv(VecEnv):
    def __init__(self, n_workers, density, drone_radius=0.15, safety_radius=0.19):
        self.closed = False
        self.n_workers = n_workers
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [Process(target=worker, args=(work_remote, remote, density, drone_radius, safety_radius), daemon=True)
                   for (work_remote, remote) in zip(self.work_remotes, self.remotes)]
        for p in self.ps: p.start()
        for remote in self.work_remotes: remote.close()
        self.remotes[0].send(('get_spaces', None))
        obs_space, act_space = self.remotes[0].recv()
        super().__init__(n_workers * 10, obs_space, act_space)

    def step_async(self, actions):
        for i in range(self.n_workers):
            self.remotes[i].send(('step', actions[i*10:(i+1)*10]))

    def step_wait(self):
        obs, rews, dones, infos = zip(*[remote.recv() for remote in self.remotes])
        return np.concatenate(obs), np.concatenate(rews), np.concatenate(dones), [i for sub in infos for i in sub]

    def reset(self):
        for remote in self.remotes: remote.send(('reset', None))
        return np.concatenate([remote.recv() for remote in self.remotes])

    def close(self):
        if self.closed: return
        for remote in self.remotes: remote.send(('close', None))
        for p in self.ps: p.join()
        self.closed = True

    def set_density(self, density):
        for remote in self.remotes: remote.send(('set_density', density))
    def get_attr(self, attr_name, indices=None): return [None] * self.num_envs
    def set_attr(self, attr_name, value, indices=None): pass
    def env_method(self, method_name, *method_args, indices=None, **method_kwargs):
        if method_name == "set_target_density": self.set_density(method_args[0])
    def env_is_wrapped(self, wrapper_class, indices=None):
        return [False] * self.num_envs

# --- Main Training Flow ---

def train_apex_ultra():
    import multiprocessing
    num_cpu = 10
    print(f"Launching {num_cpu} workers on {multiprocessing.cpu_count()} core machine")
    os.makedirs("./models/checkpoints", exist_ok=True)
    print(f"🔥 Launching APEX-ULTRA MAPPO Curriculum Training (10M Steps)...")
    
    TRAIN_RADIUS = 0.19 
    
    # 1. Environment Setup (With Reward Normalization)
    base_env = MultiProcessPZEnv(n_workers=num_cpu, density=0.05, drone_radius=TRAIN_RADIUS)
    # VecNormalize is CRITICAL for the +/- 500 reward range scaling
    env = VecNormalize(base_env, norm_obs=False, norm_reward=True, clip_reward=10.0)
    
    # 2. Model Policy Configuration
    policy_kwargs = dict(
        net_arch=dict(pi=[256, 256, 128], vf=[256, 256, 128]),
        activation_fn=torch.nn.ReLU
    )

    # 3. Model Initialization (MAPPO_Policy slices observation into local/global parts)
    model = PPO(MAPPO_Policy, env, 
                learning_rate=3e-5,
                n_steps=2048,           
                batch_size=256, 
                ent_coef=0.025,         
                gamma=0.99,
                policy_kwargs=policy_kwargs,
                verbose=1,
                tensorboard_log="./ppo_swarm_tensorboard_ultra/")

    # 4. Callback Integration
    # SB3 save_freq is expressed in env.step() calls. 
    # Total desired steps per checkpoint = 250,000. 
    # env.num_envs = 120 (12 workers * 10 drones).
    checkpoint_freq = max(1, 250_000 // env.num_envs)
    
    checkpoint_callback = CheckpointCallback(
        save_freq=checkpoint_freq,
        save_path="./models/checkpoints/",
        name_prefix="apex_ultra"
    )
    entropy_callback = EntropyDecayCallback()
    callbacks = CallbackList([entropy_callback, checkpoint_callback])

    # 5. Curriculum Execution
    curriculum = [
        (1_000_000, 0.05), # Steps 0-1M
        (3_000_000, 0.12), # Steps 1M-4M
        (3_000_000, 0.20), # Steps 4M-7M
        (3_000_000, 0.25), # Steps 7M-10M
    ]

    total_elapsed = 0
    for steps, density in curriculum:
        print(f"\n🚀 CURRICULUM PHASE: Density={density*100}% | Steps={steps/1e6}M")
        env.env_method("set_target_density", density)
        
        model.learn(total_timesteps=steps, reset_num_timesteps=False, progress_bar=True, callback=callbacks)
        
        total_elapsed += steps
        model.save(f"./models/apex_ultra_mid_{total_elapsed//1000000}M")
        env.save(f"./models/vecnormalize_{total_elapsed//1000000}M.pkl")

    model.save("./models/apex_ultra_mappo_final")
    env.save("./models/vecnormalize_final.pkl")
    env.close()

    print(f"\n🎯 Apex-Ultra MAPPO Training Finished!")

if __name__ == "__main__":
    train_apex_ultra()
