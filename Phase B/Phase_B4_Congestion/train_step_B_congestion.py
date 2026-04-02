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
from swarm_env_step_B import SwarmLidarEnv_StepB
from multiprocessing import Process, Pipe

# ======================================================
#  PHASE B4: CONGESTION CONTROL (TRAFFIC JAM CURRICULUM)
#  Goal: Bridge the 78% -> 90%+ gap in Clustered Spawning
#  Architecture: MAPPO with 100-Dim Local + 520-Dim Global
# ======================================================

class MAPPO_Extractor_B4(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        # Actor pi: input[:100] -> 100 local dims (LiDAR + Neighbors + Congestion)
        # Critic vf: input[100:] -> 520 global dims
        
        pi_layers = []
        last_layer_dim_pi = 100
        for curr_layer_dim in net_arch['pi']:
            pi_layers.append(nn.Linear(last_layer_dim_pi, curr_layer_dim))
            pi_layers.append(activation_fn())
            last_layer_dim_pi = curr_layer_dim
        self.policy_net = nn.Sequential(*pi_layers)

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
        return self.policy_net(features[:, :100]), self.value_net(features[:, 100:])

    def forward_actor(self, features):
        return self.policy_net(features[:, :100])

    def forward_critic(self, features):
        return self.value_net(features[:, 100:])

class MAPPO_Policy_B4(ActorCriticPolicy):
    def __init__(self, observation_space, action_space, lr_schedule, *args, **kwargs):
        super().__init__(observation_space, action_space, lr_schedule, *args, **kwargs)

    def _build_mlp_extractor(self) -> None:
        self.mlp_extractor = MAPPO_Extractor_B4(self.features_dim, self.net_arch, self.activation_fn)


# --- RESTORED: Environment Worker (Mixed Curriculum Support) ---
def worker(remote, parent_remote, density, drone_radius, safety_radius):
    parent_remote.close()
    env = SwarmLidarEnv_StepB(render_mode=None, target_density=density,
                              drone_radius=drone_radius, safety_radius=safety_radius)
    n_drones = 10
    ghost_obs = {}
    
    try:
        while True:
            cmd, data = remote.recv()
            if cmd == 'step':
                actions = {f"drone_{i}": data[i] for i in range(n_drones) if f"drone_{i}" in env.agents}
                obs_d, rew_d, term_d, trunc_d, info_d = env.step(actions)
                
                zero_obs = np.zeros(env.observation_space("drone_0").shape, dtype=np.float32)
                
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
                    terminal_obs = {f"drone_{i}": ghost_obs.get(f"drone_{i}", obs_d.get(f"drone_{i}", zero_obs)) for i in range(n_drones)}
                    
                    # [PHASE B4] MIXED CURRICULUM: 70% Clustered, 30% Random
                    mode = "clustered" if np.random.random() < 0.7 else "random"
                    new_obs_d, _ = env.reset(options={"spawn_mode": mode})
                    
                    ghost_obs.clear()
                    obs_list, rew_list, done_list, info_list = [], [], [], []
                    for i in range(n_drones):
                        agent = f"drone_{i}"
                        info = info_d.get(agent, {})
                        info['terminal_observation'] = terminal_obs[agent]
                        obs_list.append(new_obs_d.get(agent, zero_obs)); rew_list.append(rew_d.get(agent, 0.0)); done_list.append(True); info_list.append(info)
                
                remote.send((np.array(obs_list, dtype=np.float32), np.array(rew_list, dtype=np.float32), np.array(done_list, dtype=bool), info_list))
            
            elif cmd == 'reset':
                mode = "clustered" if np.random.random() < 0.7 else "random"
                obs_d, _ = env.reset(options={"spawn_mode": mode})
                ghost_obs.clear()
                obs = np.array([obs_d.get(f"drone_{i}", np.zeros(env.observation_space("drone_0").shape)) for i in range(n_drones)], dtype=np.float32)
                remote.send(obs)
            elif cmd == 'close': env.close(); break
            elif cmd == 'set_density': env.set_target_density(data)
            elif cmd == 'get_spaces': remote.send((env.observation_space("drone_0"), env.action_space("drone_0")))
    
    except Exception as e:
        remote.close()

class MultiProcessPZEnv_B4(VecEnv):
    def __init__(self, n_workers, density=0.20):
        self.closed = False
        self.n_workers = n_workers
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [Process(target=worker, args=(work_remote, remote, density, 0.15, 0.19), daemon=True)
                   for (work_remote, remote) in zip(self.work_remotes, self.remotes)]
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


# --- Training Flow ---
def run_congestion_training():
    num_cpu = 10 # 10 cores x 10 drones = 100 environments stepping in parallel!
    print(f"🔥 Phase B4: Congestion Control Curriculum Starting ({num_cpu} Cores)...")
    
    # 1. Initialize Custom Multiprocessing Environment
    base_env = MultiProcessPZEnv_B4(n_workers=num_cpu, density=0.20)
    env = VecNormalize(base_env, norm_obs=False, norm_reward=True, clip_reward=10.0)
    
    policy_kwargs = dict(
        net_arch=dict(pi=[256, 256, 128], vf=[256, 256, 128]),
        activation_fn=torch.nn.ReLU
    )

    model = PPO(MAPPO_Policy_B4, env, 
                learning_rate=2e-5, # Slower fine-tuning
                n_steps=2048,           
                batch_size=256, 
                ent_coef=0.015,         
                gamma=0.99,
                policy_kwargs=policy_kwargs,
                verbose=1,
                tensorboard_log="./ppo_swarm_tensorboard_congestion/")

    # 2. Weight Surgery
    OLD_MODEL_PATH = "./models/apex_ultra_mappo_final.zip"
    if os.path.exists(OLD_MODEL_PATH):
        print("🔭 Performing Weight Surgery (Apex-Ultra -> Phase B4 100-dim)...")
        with zipfile.ZipFile(OLD_MODEL_PATH, "r") as zip_f:
            with zip_f.open("policy.pth") as pth_f:
                old_params = torch.load(io.BytesIO(pth_f.read()), map_location="cpu", weights_only=True)
        
        new_state_dict = model.policy.state_dict()
        for key, val in old_params.items():
            if key == "mlp_extractor.policy_net.0.weight":
                new_val = torch.zeros((256, 100))
                new_val[:, :99] = val
                new_val[:, 99] = val[:, -1]
                new_state_dict[key] = new_val
            elif key in new_state_dict and new_state_dict[key].shape == val.shape:
                new_state_dict[key] = val
        model.policy.load_state_dict(new_state_dict)
        print("✅ Pre-trained weights adapted.")
    else:
        print("⚠️ No previous model found. Training entirely from scratch.")

    # 3. Stepped Curriculum
    curriculum = [
        (300_000, 0.20),
        (400_000, 0.30),
        (300_000, 0.35)
    ]

    total_steps = 0
    os.makedirs("./models/checkpoints_b4/", exist_ok=True)
    checkpoint_callback = CheckpointCallback(save_freq=100_000, save_path='./models/checkpoints_b4/', name_prefix='b4_congestion')

    for steps, density in curriculum:
        print(f"\n🚀 PHASE: Density={density} | Steps={steps/1e3}k")
        env.env_method("set_target_density", density)
        model.learn(total_timesteps=steps, reset_num_timesteps=False, callback=checkpoint_callback)
        total_steps += steps
        model.save(f"./models/apex_ultra_congestion_mid_{total_steps//1000}k")

    model.save("./models/apex_ultra_congestion_final")
    env.save("./models/vecnormalize_congestion_final.pkl")
    env.close()
    print("\n🏁 Phase B4 Training Complete. Model saved to ./models/apex_ultra_congestion_final")

if __name__ == "__main__":
    run_congestion_training()
