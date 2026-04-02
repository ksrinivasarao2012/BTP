import os
import torch
import torch.nn as nn
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecEnv, VecNormalize
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.callbacks import CheckpointCallback
from swarm_env_step_B5_v11 import SwarmLidarEnv_v11
from multiprocessing import Process, Pipe

# ======================================================
#  PHASE B5 v11: TRUST-VERIFICATION TRAINING (173D)
#  Architecture: Local 173D (Fixed Slots) | Global 400D
# ======================================================

class MAPPO_Extractor_v11(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        # Actor: 173D input
        last_dim_pi = 173
        pi_layers = []
        for curr in net_arch['pi']:
            pi_layers.append(nn.Linear(last_dim_pi, curr))
            pi_layers.append(activation_fn())
            last_dim_pi = curr
        self.policy_net = nn.Sequential(*pi_layers)

        # Critic: 400D input
        last_dim_vf = 400
        vf_layers = []
        for curr in net_arch['vf']:
            vf_layers.append(nn.Linear(last_dim_vf, curr))
            vf_layers.append(activation_fn())
            last_dim_vf = curr
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi = last_dim_pi
        self.latent_dim_vf = last_dim_vf

    def forward(self, features): 
        # features slice: [Batch, 173+400]
        return self.policy_net(features[:, :173]), self.value_net(features[:, 173:])
    def forward_actor(self, features): return self.policy_net(features[:, :173])
    def forward_critic(self, features): return self.value_net(features[:, 173:])

class MAPPO_Policy_v11(ActorCriticPolicy):
    def __init__(self, observation_space, action_space, lr_schedule, *args, **kwargs):
        super().__init__(observation_space, action_space, lr_schedule, *args, **kwargs)
    def _build_mlp_extractor(self) -> None:
        self.mlp_extractor = MAPPO_Extractor_v11(self.features_dim, self.net_arch, self.activation_fn)

def worker(remote, parent_remote, density):
    parent_remote.close()
    env = SwarmLidarEnv_v11(target_density=density)
    n_drones = 10
    ghost_obs = {}
    total_obs_dim = 173 + 400
    try:
        while True:
            cmd, data = remote.recv()
            if cmd == 'step':
                actions = {f"drone_{i}": data[i] for i in range(n_drones) if f"drone_{i}" in env.agents}
                obs_d, rew_d, term_d, trunc_d, info_d = env.step(actions)
                zero_obs = np.zeros(total_obs_dim, dtype=np.float32)
                o_l, r_l, d_l, i_l = [], [], [], []
                all_done = not env.agents
                for i in range(n_drones):
                    agent = f"drone_{i}"
                    if all_done: pass
                    elif term_d.get(agent, False) or trunc_d.get(agent, False):
                        last = obs_d.get(agent, zero_obs); ghost_obs[agent] = last
                        o_l.append(last); r_l.append(rew_d.get(agent,0.0)); d_l.append(False); i_l.append(info_d.get(agent,{}))
                    elif agent in ghost_obs:
                        o_l.append(ghost_obs[agent]); r_l.append(0.0); d_l.append(False); i_l.append({})
                    else:
                        o_l.append(obs_d.get(agent, zero_obs)); r_l.append(rew_d.get(agent,0.0)); d_l.append(False); i_l.append(info_d.get(agent,{}))
                if all_done:
                    new_obs_d, _ = env.reset()
                    ghost_obs.clear()
                    o_l = [new_obs_d.get(f"drone_{i}", zero_obs) for i in range(n_drones)]
                    r_l = [0.0]*n_drones; d_l = [True]*n_drones; i_l = [{}]*n_drones
                remote.send((np.array(o_l, dtype=np.float32), np.array(r_l, dtype=np.float32), np.array(d_l, bool), i_l))
            elif cmd == 'reset':
                obs_d, _ = env.reset(); ghost_obs.clear()
                remote.send(np.array([obs_d.get(f"drone_{i}", np.zeros(total_obs_dim)) for i in range(n_drones)], dtype=np.float32))
            elif cmd == 'close': env.close(); break
            elif cmd == 'get_spaces': remote.send((env.observation_spaces["drone_0"], env.action_spaces["drone_0"]))
    except Exception as e: print(f"Worker Error: {e}"); remote.close()

class MultiProcessEnv_v11(VecEnv):
    def __init__(self, n_workers, density=0.25):
        self.closed = False; self.n_workers = n_workers
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [Process(target=worker, args=(wr, r, density), daemon=True) for (wr, r) in zip(self.work_remotes, self.remotes)]
        for p in self.ps: p.start()
        for r in self.work_remotes: r.close()
        self.remotes[0].send(('get_spaces', None))
        obs_space, act_space = self.remotes[0].recv()
        super().__init__(n_workers * 10, obs_space, act_space)
    def step_async(self, actions):
        for i in range(self.n_workers): self.remotes[i].send(('step', actions[i*10:(i+1)*10]))
    def step_wait(self):
        o, r, d, i = zip(*[remote.recv() for remote in self.remotes])
        return np.concatenate(o), np.concatenate(r), np.concatenate(d), [item for sub in i for item in sub]
    def reset(self):
        for r in self.remotes: r.send(('reset', None))
        return np.concatenate([r.recv() for r in self.remotes])
    def close(self):
        if self.closed: return
        for r in self.remotes: r.send(('close', None))
        for p in self.ps: p.join(); self.closed = True
    def get_attr(self, name, i=None): return [None] * self.num_envs
    def set_attr(self, name, val, i=None): pass
    def env_method(self, name, *a, i=None, **k): pass
    def env_is_wrapped(self, cls, i=None): return [False] * self.num_envs

def run_v11_training():
    print(f"🌍 LAUNCHING PHASE B5 v11: Fixed-ID Dual-Track Trust Baseline (173D)")
    num_cpu = 10
    base_env = MultiProcessEnv_v11(n_workers=num_cpu, density=0.30)
    env = VecNormalize(base_env, norm_obs=False, norm_reward=True, clip_reward=10.0)
    
    policy_kwargs = dict(net_arch=dict(pi=[256, 256, 256], vf=[512, 512, 512]), activation_fn=nn.Tanh)
    
    model = PPO(MAPPO_Policy_v11, env, verbose=1, 
                learning_rate=3e-4, 
                n_steps=2048, 
                batch_size=256, 
                n_epochs=10, 
                gamma=0.99, 
                gae_lambda=0.95, 
                ent_coef=0.03, 
                policy_kwargs=policy_kwargs,
                tensorboard_log="./logs/v11_Research/")

    os.makedirs("./models/v11_Research/", exist_ok=True)
    checkpoint = CheckpointCallback(save_freq=500_000, save_path='./models/v11_Research/', name_prefix='v11_trust_baseline')
    
    print("\n[V11] Starting 10,000,000 steps scratch curriculum...")
    model.learn(total_timesteps=10_000_000, callback=checkpoint)
    
    model.save("./models/v11_Trust_Baseline_10M")
    env.save("./models/v11_Trust_Normalize.pkl")
    env.close()
    print(f"\n✅ Phase B5 v11 Training Complete. Trust-Verification Ready.")

if __name__ == "__main__":
    run_v11_training()
