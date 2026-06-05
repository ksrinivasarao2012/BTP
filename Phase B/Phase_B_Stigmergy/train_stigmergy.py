import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
import torch
import torch.nn as nn
import numpy as np
import zipfile
import io
import json
from tqdm import tqdm
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecEnv, VecNormalize
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.callbacks import BaseCallback
from swarm_env_stigmergy import SwarmStigmergyEnv
from multiprocessing import Process, Pipe

# ======================================================
#  PHASE B: PRODUCTION STIGMERGY TRAINING
#  Integrated with Multiprocessing & TQDM Progress Bar
# ======================================================

class ProgressBarCallback(BaseCallback):
    def __init__(self, total_steps, verbose=0):
        super().__init__(verbose)
        self.pbar = None
        self.total_steps = total_steps

    def _on_training_start(self):
        self.pbar = tqdm(total=self.total_steps, desc="Training Progress")

    def _on_step(self):
        self.pbar.update(self.training_env.num_envs)
        return True

    def _on_training_end(self):
        self.pbar.close()

class StigmergyExtractor(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        pi_layers, last_dim = [], 204
        for d in net_arch['pi']: pi_layers.append(nn.Linear(last_dim, d)); pi_layers.append(activation_fn()); last_dim = d
        self.policy_net = nn.Sequential(*pi_layers)
        vf_layers, last_dim = [], 530
        for d in net_arch['vf']: vf_layers.append(nn.Linear(last_dim, d)); vf_layers.append(activation_fn()); last_dim = d
        self.value_net = nn.Sequential(*vf_layers)

        self.latent_dim_pi, self.latent_dim_vf = last_dim, last_dim
    def forward(self, f): return self.policy_net(f[:, :204]), self.value_net(f[:, 204:])
    def forward_actor(self, f): return self.policy_net(f[:, :204])
    def forward_critic(self, f): return self.value_net(f[:, 204:])

class StigmergyPolicy(ActorCriticPolicy):
    def __init__(self, observation_space, action_space, lr_schedule, *args, **kwargs):
        super().__init__(observation_space, action_space, lr_schedule, *args, **kwargs)
    def _build_mlp_extractor(self) -> None:
        self.mlp_extractor = StigmergyExtractor(self.features_dim, self.net_arch, self.activation_fn)

def worker(remote, parent_remote, density, config=None):
    parent_remote.close()
    
    stagnation_limit = config.get("stagnation_limit", 40) if config else 40
    breadcrumb_lifetime = config.get("breadcrumb_lifetime", 250) if config else 250
    repulsion_scale = config.get("repulsion_scale", 2.0) if config else 2.0
    sensing_radius = config.get("sensing_radius", 5.0) if config else 5.0

    env = SwarmStigmergyEnv(
        target_density=density,
        stagnation_limit=stagnation_limit,
        breadcrumb_lifetime=breadcrumb_lifetime,
        repulsion_scale=repulsion_scale,
        sensing_radius=sensing_radius
    )
    
    while True:
        cmd, data = remote.recv()
        if cmd == 'step':
            obs_d, rew_d, term_d, trunc_d, info_d = env.step({f"drone_{i}": data[i] for i in range(10) if f"drone_{i}" in env.agents})
            obs_list = [obs_d.get(f"drone_{i}", np.zeros(734)) for i in range(10)]
            rews = [rew_d.get(f"drone_{i}", 0.0) for i in range(10)]
            dones = [not env.agents] * 10
            if not env.agents:
                new_obs, _ = env.reset(options={"spawn_mode": "clustered" if np.random.random() < 0.7 else "random"})
                obs_list = [new_obs.get(f"drone_{i}", np.zeros(734)) for i in range(10)]
            remote.send((np.array(obs_list, dtype=np.float32), np.array(rews, dtype=np.float32), np.array(dones, dtype=bool), info_d))
        elif cmd == 'reset':
            obs, _ = env.reset(options={"spawn_mode": "clustered" if np.random.random() < 0.7 else "random"})
            remote.send(np.array([obs.get(f"drone_{i}", np.zeros(734)) for i in range(10)], dtype=np.float32))
        elif cmd == 'close': env.close(); break
        elif cmd == 'set_density': env.target_density = data
        elif cmd == 'get_spaces': remote.send((env.observation_space, env.action_space))

class MultiProcessEnv(VecEnv):
    def __init__(self, n_workers, density=0.20, config=None):
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [Process(target=worker, args=(wr, r, density, config), daemon=True) for (wr, r) in zip(self.work_remotes, self.remotes)]
        for p in self.ps: p.start()
        for r in self.work_remotes: r.close()
        self.remotes[0].send(('get_spaces', None))
        obs_s, act_s = self.remotes[0].recv()
        super().__init__(n_workers * 10, obs_s, act_s)
    def step_async(self, a): 
        for i in range(len(self.remotes)): self.remotes[i].send(('step', a[i*10:(i+1)*10]))
    def step_wait(self):
        obs, rews, dones, infos_list = zip(*[r.recv() for r in self.remotes])
        combined_infos = []
        for worker_info in infos_list:
            for k in range(10):
                combined_infos.append(worker_info.get(f"drone_{k}", {}))
        return np.concatenate(obs), np.concatenate(rews), np.concatenate(dones), combined_infos
    def reset(self):
        for r in self.remotes: r.send(('reset', None))
        return np.concatenate([r.recv() for r in self.remotes])
    def close(self):
        for r in self.remotes: r.send(('close', None))
        for p in self.ps: p.join()

    def get_attr(self, attr_name, indices=None): return [None] * self.num_envs
    def set_attr(self, attr_name, value, indices=None): pass
    def env_method(self, method_name, *method_args, indices=None, **method_kwargs):
        if method_name == "set_target_density":
            for r in self.remotes: r.send(('set_density', method_args[0]))
    def env_is_wrapped(self, wrapper_class, indices=None): return [False] * self.num_envs

def train():
    # Load optimal stigmergy config if it exists
    config = None
    if os.path.exists("best_stigmergy_config.json"):
        with open("best_stigmergy_config.json", "r") as f:
            config = json.load(f)
        print(f"Loaded optimal Stigmergy config: {config}")
    else:
        print("No optimal Stigmergy config found. Using default parameters.")

    num_cpu = 10
    
    # We fine-tune directly at density 0.35 since that is our target congested evaluation setting
    base_env = MultiProcessEnv(n_workers=num_cpu, density=0.35, config=config)
    env = VecNormalize(base_env, norm_obs=False, norm_reward=True)

    FINE_TUNE_MODEL = "stigmergy_b5_model_35.zip"
    if os.path.exists(FINE_TUNE_MODEL):
        print(f"Loading existing model for fine-tuning: {FINE_TUNE_MODEL}...")
        model = PPO.load(FINE_TUNE_MODEL, env=env, learning_rate=1e-5)
    else:
        print(f"Starting training from scratch and performing Weight Surgery...")
        policy_kwargs = dict(
            net_arch=dict(pi=[256, 256, 128], vf=[256, 256, 128]),
            activation_fn=torch.nn.ReLU
        )
        model = PPO(StigmergyPolicy, env, learning_rate=2e-5, n_steps=2048, batch_size=256, verbose=0, policy_kwargs=policy_kwargs)

        # --- WEIGHT SURGERY ---
        OLD_MODEL = "../Phase_B5_Synchronization/models/step_B5_v15_final.zip"
        if os.path.exists(OLD_MODEL):
            print(f"Weight Surgery: Adapting {OLD_MODEL} (202 -> 204 dims)...")
            with zipfile.ZipFile(OLD_MODEL, "r") as zip_f:
                with zip_f.open("policy.pth") as pth_f:
                    old_params = torch.load(io.BytesIO(pth_f.read()), map_location="cpu", weights_only=True)
            new_state = model.policy.state_dict()
            for k, v in old_params.items():
                if k == "mlp_extractor.policy_net.0.weight":
                    nv = torch.zeros((256, 204))
                    nv[:, :202] = v; new_state[k] = nv
                elif k in new_state and new_state[k].shape == v.shape: new_state[k] = v
            model.policy.load_state_dict(new_state)

    # Fine-tune model for 1,000,000 steps at target 0.35 density under optimal hyperparameters
    steps = 1_000_000
    dens = 0.35
    print(f"\nStarting Fine-Tuning: 1,000,000 steps at target density {dens}")
    for r in base_env.remotes: r.send(('set_density', dens))
    pbar_callback = ProgressBarCallback(total_steps=steps)
    model.learn(total_timesteps=steps, reset_num_timesteps=False, callback=pbar_callback)
    
    # Save optimized model as the final production model
    final_model_name = "stigmergy_b5_model_35"
    model.save(final_model_name)
    print(f"Optimized model successfully saved as {final_model_name}.zip!")

if __name__ == "__main__":
    train()
