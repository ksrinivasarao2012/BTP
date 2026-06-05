import os
import torch
import torch.nn as nn
import numpy as np
import zipfile
import io
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecEnv, VecNormalize
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.callbacks import CheckpointCallback
from swarm_env_step_B5 import SwarmLidarEnv_StepB5 
from multiprocessing import Process, Pipe

# ======================================================
#  PHASE B5: SWARM SYNCHRONIZATION (IEEE T-RO Standard)
#  Goal: 95%+ Dense Cluster Efficiency
#  Architecture: MAPPO 120-Dim Local + 520-Dim Global
# ======================================================

class MAPPO_Extractor_B5(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        # Actor pi: input[:132] -> 132 local dims (120 core + 10 trajectory history + 2 breadcrumb)
        pi_layers = []
        last_layer_dim_pi = 132
        for curr_layer_dim in net_arch['pi']:
            pi_layers.append(nn.Linear(last_layer_dim_pi, curr_layer_dim))
            pi_layers.append(activation_fn())
            last_layer_dim_pi = curr_layer_dim
        self.policy_net = nn.Sequential(*pi_layers)

        # Critic vf: input[132:] -> 520 global dims
        vf_layers = []
        last_layer_dim_vf = 520
        for curr_layer_dim in net_arch['vf']:
            vf_layers.append(nn.Linear(last_layer_dim_vf, curr_layer_dim))
            vf_layers.append(activation_fn())
            last_layer_dim_vf = curr_layer_dim
        self.value_net = nn.Sequential(*vf_layers)

        self.latent_dim_pi = last_layer_dim_pi
        self.latent_dim_vf = last_layer_dim_vf

    def forward(self, features): return self.policy_net(features[:, :132]), self.value_net(features[:, 132:])
    def forward_actor(self, features): return self.policy_net(features[:, :132])
    def forward_critic(self, features): return self.value_net(features[:, 132:])

class MAPPO_Policy_B5(ActorCriticPolicy):
    def __init__(self, observation_space, action_space, lr_schedule, *args, **kwargs):
        super().__init__(observation_space, action_space, lr_schedule, *args, **kwargs)
    def _build_mlp_extractor(self) -> None:
        self.mlp_extractor = MAPPO_Extractor_B5(self.features_dim, self.net_arch, self.activation_fn)

def worker(remote, parent_remote, density, drone_radius, safety_radius, config=None):
    parent_remote.close()
    
    stagnation_limit = config.get("stagnation_limit", 40) if config else 40
    breadcrumb_lifetime = config.get("breadcrumb_lifetime", 250) if config else 250
    repulsion_scale = config.get("repulsion_scale", 2.0) if config else 2.0
    sensing_radius = config.get("sensing_radius", 5.0) if config else 5.0

    env = SwarmLidarEnv_StepB5(
        render_mode=None, 
        target_density=density,
        stagnation_limit=stagnation_limit,
        breadcrumb_lifetime=breadcrumb_lifetime,
        repulsion_scale=repulsion_scale,
        sensing_radius=sensing_radius
    )
    n_drones = 10
    ghost_obs = {}
    try:
        while True:
            cmd, data = remote.recv()
            if cmd == 'step':
                actions = {f"drone_{i}": data[i] for i in range(n_drones) if f"drone_{i}" in env.agents}
                obs_d, rew_d, term_d, trunc_d, info_d = env.step(actions)
                zero_obs = np.zeros(env.observation_spaces["drone_0"].shape, dtype=np.float32)
                obs_list, rew_list, done_list, info_list = [], [], [], []
                all_done = not env.agents
                for i in range(n_drones):
                    agent = f"drone_{i}"
                    if all_done: pass
                    elif term_d.get(agent, False) or trunc_d.get(agent, False):
                        last_obs = obs_d.get(agent, zero_obs)
                        ghost_obs[agent] = last_obs
                        obs_list.append(last_obs); rew_list.append(rew_d.get(agent, 0.0)); done_list.append(False); info_list.append(info_d.get(agent, {}))
                    elif agent in ghost_obs:
                        obs_list.append(ghost_obs[agent]); rew_list.append(0.0); done_list.append(False); info_list.append({})
                    else:
                        obs_list.append(obs_d.get(agent, zero_obs)); rew_list.append(rew_d.get(agent, 0.0)); done_list.append(False); info_list.append(info_d.get(agent, {}))
                if all_done:
                    new_obs_d, _ = env.reset(options={"spawn_mode": "clustered" if np.random.random() < 0.7 else "random"})
                    ghost_obs.clear()
                    obs_list, rew_list, done_list, info_list = [], [], [], []
                    for i in range(n_drones):
                        agent = f"drone_{i}"
                        obs_list.append(new_obs_d.get(agent, zero_obs)); rew_list.append(0.0); done_list.append(True); info_list.append({})
                remote.send((np.array(obs_list, dtype=np.float32), np.array(rew_list, dtype=np.float32), np.array(done_list, dtype=bool), info_list))
            elif cmd == 'reset':
                obs_d, _ = env.reset(options={"spawn_mode": "clustered" if np.random.random() < 0.7 else "random"})
                ghost_obs.clear()
                remote.send(np.array([obs_d.get(f"drone_{i}", np.zeros(132+520)) for i in range(n_drones)], dtype=np.float32))
            elif cmd == 'close': env.close(); break
            elif cmd == 'set_density': env.set_target_density(data)
            elif cmd == 'get_spaces': remote.send((env.observation_spaces["drone_0"], env.action_spaces["drone_0"]))
    except Exception as e:
        remote.close()

class MultiProcessPZEnv_B5(VecEnv):
    def __init__(self, n_workers, density=0.20, config=None):
        self.closed = False
        self.n_workers = n_workers
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [Process(target=worker, args=(work_remote, remote, density, 0.15, 0.19, config), daemon=True) for (work_remote, remote) in zip(self.work_remotes, self.remotes)]
        for p in self.ps: p.start()
        for remote in self.work_remotes: remote.close()
        self.remotes[0].send(('get_spaces', None))
        obs_space, act_space = self.remotes[0].recv()
        super().__init__(n_workers * 10, obs_space, act_space)
    def step_async(self, actions):
        for i in range(self.n_workers): self.remotes[i].send(('step', actions[i*10:(i+1)*10]))
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
    def env_is_wrapped(self, wrapper_class, indices=None): return [False] * self.num_envs

def run_sync_training():
    import json
    
    # Load optimal stigmergy config if it exists
    config = None
    config_path = "best_stigmergy_config.json"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
        print(f"Loaded optimal Stigmergy config: {config}")
    else:
        print("No optimal Stigmergy config found. Using default parameters.")

    num_cpu = 10 
    print(f"PHASE B5: Stigmergy Fine-Tuning — 132-dim Obs ({num_cpu} Cores)...")
    base_env = MultiProcessPZEnv_B5(n_workers=num_cpu, density=0.35, config=config)
    env = VecNormalize(base_env, norm_obs=False, norm_reward=True, clip_reward=10.0)
    policy_kwargs = dict(net_arch=dict(pi=[256, 256, 128], vf=[256, 256, 128]), activation_fn=torch.nn.ReLU)

    # Check for existing fine-tuned model first to resume or initialize
    FINE_TUNE_MODEL = "./models/stigmergy_step_B5_sync_optimized.zip"
    if os.path.exists(FINE_TUNE_MODEL):
        print(f"Resuming from existing optimized model: {FINE_TUNE_MODEL}...")
        model = PPO.load(FINE_TUNE_MODEL, env=env, learning_rate=1e-5)
    else:
        print("Initializing new PPO model with 132-dim local observations...")
        model = PPO(MAPPO_Policy_B5, env, learning_rate=2e-5, n_steps=2048, batch_size=256, ent_coef=0.01, gamma=0.99, policy_kwargs=policy_kwargs, verbose=1)

        # --- WEIGHT SURGERY ---
        OLD_MODEL = "../../models/v15_Master_Recovered_Final.zip"
        if not os.path.exists(OLD_MODEL):
            OLD_MODEL = "./models/apex_ultra_glide_v14_final.zip"
            
        if os.path.exists(OLD_MODEL):
            print(f"Weight Surgery: Adapting {OLD_MODEL} (130 -> 132 local dims)...")
            with zipfile.ZipFile(OLD_MODEL, "r") as zip_f:
                with zip_f.open("policy.pth") as pth_f:
                    old_params = torch.load(io.BytesIO(pth_f.read()), map_location="cpu", weights_only=True)
            new_state = model.policy.state_dict()
            for k, v in old_params.items():
                if k == "mlp_extractor.policy_net.0.weight":
                    nv = torch.zeros((256, 132))
                    nv[:, :130] = v
                    new_state[k] = nv
                elif k in new_state and new_state[k].shape == v.shape:
                    new_state[k] = v
            model.policy.load_state_dict(new_state)
            print("Weight Surgery completed successfully!")
        else:
            print("Warning: No base pre-trained model found for surgery. Training from scratch.")

    # Extended deep fine-tuning for 3M steps at density 0.35 under optimal config
    steps = 3_000_000
    print(f"\nStarting Stigmergy Fine-Tuning: {steps} steps at obstacle density 0.35...")
    env.env_method("set_target_density", 0.35)
    
    os.makedirs("./models/checkpoints_stigmergy/", exist_ok=True)
    checkpoint_callback = CheckpointCallback(save_freq=500_000, save_path='./models/checkpoints_stigmergy/', name_prefix='stigmergy_B5')
    
    model.learn(total_timesteps=steps, reset_num_timesteps=False, callback=checkpoint_callback)
    
    model.save("./models/stigmergy_step_B5_sync_optimized")
    env.save("./models/vecnormalize_stigmergy_final.pkl")
    env.close()
    print("\nStigmergy Fine-Tuning Complete. Optimized model saved successfully!")

if __name__ == "__main__":
    run_sync_training()
