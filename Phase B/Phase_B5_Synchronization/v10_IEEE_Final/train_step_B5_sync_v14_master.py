import os
import torch
import torch.nn as nn
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecEnv, VecNormalize
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback
from swarm_env_step_B5_v14_master import SwarmLidarEnv_v14_Master
from multiprocessing import Process, Pipe

# ======================================================
#  PHASE B MASTER v14: CURRICULUM TRAINING (202D)
#  Stage 1: Warm-up (2M) | R=100
#  Stage 2: Decay  (3M)  | R=100 -> 10/8
#  Stage 3: Lock-in (5M) | R=10/8
# ======================================================

class CurriculumCallback(BaseCallback):
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.stage1_end = 2_000_000
        self.stage2_end = 5_000_000
    
    def _on_step(self) -> bool:
        ts = self.num_timesteps
        r_comm = 100.0; r_sensor = 100.0
        
        if ts <= self.stage1_end:
            r_comm = 100.0; r_sensor = 100.0
        elif ts <= self.stage2_end:
            # Linear decay
            frac = (ts - self.stage1_end) / (self.stage2_end - self.stage1_end)
            r_comm = 100.0 - frac * (100.0 - 10.0)
            r_sensor = 100.0 - frac * (100.0 - 8.0)
        else:
            r_comm = 10.0; r_sensor = 8.0
            
        # Update environments across all processes
        self.training_env.env_method("set_ranges", r_comm, r_sensor)
        
        if ts % 100000 == 0:
            print(f"⏱️ [Curriculum] Step {ts}: R_comm={r_comm:.1f}m, R_sensor={r_sensor:.1f}m")
        return True

class MAPPO_Extractor_v14(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        # Actor Input: 202D
        pi_layers = []
        last_dim_pi = 202
        for curr in net_arch['pi']:
            pi_layers.append(nn.Linear(last_dim_pi, curr))
            pi_layers.append(activation_fn())
            last_dim_pi = curr
        self.policy_net = nn.Sequential(*pi_layers)

        # Critic Input: 530D
        vf_layers = []
        last_dim_vf = 530
        for curr in net_arch['vf']:
            vf_layers.append(nn.Linear(last_dim_vf, curr))
            vf_layers.append(activation_fn())
            last_dim_vf = curr
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi = last_dim_pi
        self.latent_dim_vf = last_dim_vf

    def forward(self, features): 
        return self.policy_net(features[:, :202]), self.value_net(features[:, 202:])
    def forward_actor(self, features): return self.policy_net(features[:, :202])
    def forward_critic(self, features): return self.value_net(features[:, 202:])

class MAPPO_Policy_v14(ActorCriticPolicy):
    def __init__(self, observation_space, action_space, lr_schedule, *args, **kwargs):
        super().__init__(observation_space, action_space, lr_schedule, *args, **kwargs)
    def _build_mlp_extractor(self) -> None:
        self.mlp_extractor = MAPPO_Extractor_v14(self.features_dim, self.net_arch, self.activation_fn)

def worker(remote, parent_remote, density):
    parent_remote.close()
    env = SwarmLidarEnv_v14_Master(target_density=density)
    n_drones = 10; ghost_obs = {}
    total_obs_dim = 202 + 530
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
                    new_obs_d, _ = env.reset(); ghost_obs.clear()
                    o_l = [new_obs_d.get(f"drone_{i}", zero_obs) for i in range(n_drones)]
                    r_l = [0.0]*10; d_l = [True]*10; i_l = [{}]*10
                remote.send((np.array(o_l, dtype=np.float32), np.array(r_l, dtype=np.float32), np.array(d_l, bool), i_l))
            elif cmd == 'reset':
                obs_d, _ = env.reset(); ghost_obs.clear()
                remote.send(np.array([obs_d.get(f"drone_{i}", np.zeros(total_obs_dim)) for i in range(n_drones)], dtype=np.float32))
            elif cmd == 'set_ranges':
                env.current_r_comm, env.current_r_sensor = data
                remote.send(True)
            elif cmd == 'close': env.close(); break
            elif cmd == 'get_spaces': remote.send((env.observation_spaces["drone_0"], env.action_spaces["drone_0"]))
    except Exception as e: remote.close()

class MultiProcessEnv_v14(VecEnv):
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
    def set_ranges(self, r_comm, r_sensor):
        for r in self.remotes: r.send(('set_ranges', (r_comm, r_sensor)))
        return [r.recv() for r in self.remotes]
    def close(self):
        if self.closed: return
        for r in self.remotes: r.send(('close', None))
        for p in self.ps: p.join(); self.closed = True
    def get_attr(self, name, i=None): return [None] * self.num_envs
    def set_attr(self, name, val, i=None): pass
    def env_method(self, name, *a, i=None, **k):
        if name == "set_ranges": return self.set_ranges(*a)
        return [None] * self.num_envs
    def env_is_wrapped(self, cls, i=None): return [False] * self.num_envs

def run_v14_master_training():
    print(f"🏆 LAUNCHING PHASE B MASTER v14: POMDP HARDENING (202D)")
    num_cpu = 10
    base_env = MultiProcessEnv_v14(n_workers=num_cpu, density=0.35) # Increased density
    env = VecNormalize(base_env, norm_obs=False, norm_reward=True, clip_reward=10.0)
    policy_kwargs = dict(net_arch=dict(pi=[512, 512, 256], vf=[1024, 512, 256]), activation_fn=nn.Tanh)
    model = PPO(MAPPO_Policy_v14, env, verbose=1, learning_rate=3e-4, n_steps=2048, batch_size=256, n_epochs=10, gamma=0.99, gae_lambda=0.95, ent_coef=0.03, policy_kwargs=policy_kwargs, tensorboard_log="./logs/v14_Master/")
    os.makedirs("./models/v14_Master/", exist_ok=True)
    checkpoint = CheckpointCallback(save_freq=1_000_000, save_path='./models/v14_Master/', name_prefix='v14_master_stage')
    curriculum = CurriculumCallback()
    print("\n[V14-Master] Starting 15,000,000 steps Stage-Wise Curriculum...")
    model.learn(total_timesteps=15_000_000, callback=[checkpoint, curriculum])
    model.save("./models/v14_Master_Final_15M")
    env.save("./models/v14_Master_Normalize.pkl")
    env.close(); print(f"\n✅ Phase B Master v14 Certification Complete. POMDP Baseline Locked.")

if __name__ == "__main__":
    run_v14_master_training()
