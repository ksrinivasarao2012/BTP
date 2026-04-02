import os
import torch
import torch.nn as nn
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecEnv, VecNormalize
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback
from swarm_env_step_B5_v15_master import SwarmLidarEnv_v15_Final
from multiprocessing import Process, Pipe
import traceback

# ======================================================
#  PHASE B MASTER v15: RE-SYNCED TRAINING HARNESS
#  Stage 1: Warm-up (3M) | R=100
#  Stage 2: Decay  (5M)  | R=100 -> 10/8
#  Stage 3: Lock-in (12M)| R=10/8
# ======================================================

class CurriculumCallback(BaseCallback):
    def __init__(self, verbose=0):
        super().__init__(verbose)
        # --- IMAGE-SYNCHRONIZED STAGES ---
        self.stage1_end = 5_000_000
        self.stage2_end = 15_000_000
        self.stage3_end = 35_000_000
        self._last_r_comm = -1.0
        self._last_density = -1.0
    
    def _on_step(self) -> bool:
        ts = self.num_timesteps
        r_comm, r_sensor = 10.0, 8.0
        density = 0.20
        
        if ts <= self.stage1_end: 
            r_comm, r_sensor = 100.0, 100.0
            density = 0.20
        elif ts <= self.stage2_end:
            frac = (ts - self.stage1_end) / (self.stage2_end - self.stage1_end)
            r_comm = 100.0 - frac * (100.0 - 10.0) # Radio at 10m
            r_sensor = 100.0 - frac * (100.0 - 8.0) # Sensor at 8m
            density = 0.24
        elif ts <= self.stage3_end:
            r_comm, r_sensor = 10.0, 8.0
            density = 0.26
        else: 
            r_comm, r_sensor = 10.0, 8.0
            density = 0.28

        # [Problem 5 FIX] Dirty-check to avoid 40M redundant IPC calls
        if abs(r_comm - self._last_r_comm) > 1e-4 or abs(density - self._last_density) > 1e-4:
            self.training_env.env_method("set_curriculum", r_sensor, r_comm)
            self.training_env.env_method("set_target_density", density)
            self._last_r_comm = r_comm
            self._last_density = density
        
        # [V15 OPTIMIZATION] Reduced logging frequency for high-FPS tracking
        if ts % 500000 == 0:
            print(f"⏱️ [V15-Final] Step {ts}: R_comm={r_comm:.1f}m, R_sensor={r_sensor:.1f}m, Density={density:.2f}")
        return True


class MAPPO_Extractor_v15(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        # Actor: 202D
        pi_layers = []; last_dim_pi = 202
        for curr in net_arch['pi']:
            pi_layers.append(nn.Linear(last_dim_pi, curr)); pi_layers.append(activation_fn())
            last_dim_pi = curr
        self.policy_net = nn.Sequential(*pi_layers)
        # Critic: 530D
        vf_layers = []; last_dim_vf = 530
        for curr in net_arch['vf']:
            vf_layers.append(nn.Linear(last_dim_vf, curr)); vf_layers.append(activation_fn())
            last_dim_vf = curr
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi = last_dim_pi; self.latent_dim_vf = last_dim_vf
    def forward(self, features): return self.policy_net(features[:, :202]), self.value_net(features[:, 202:])
    def forward_actor(self, features): return self.policy_net(features[:, :202])
    def forward_critic(self, features): return self.value_net(features[:, 202:])

class MAPPO_Policy_v15(ActorCriticPolicy):
    def __init__(self, observation_space, action_space, lr_schedule, *args, **kwargs):
        super().__init__(observation_space, action_space, lr_schedule, *args, **kwargs)
    def _build_mlp_extractor(self) -> None:
        self.mlp_extractor = MAPPO_Extractor_v15(self.features_dim, self.net_arch, self.activation_fn)

def worker(remote, parent_remote):
    parent_remote.close()
    env = SwarmLidarEnv_v15_Final()
    n_drones = 10; ghost_obs = {}; total_obs_dim = 202 + 530
    
    # [Problem 5] Dirty-Check Cache inside worker
    last_r_sensor = -1.0
    last_r_comm = -1.0

    try:
        while True:
            cmd, data = remote.recv()
            if cmd == 'step':
                actions = {f"drone_{i}": data[i] for i in range(n_drones) if f"drone_{i}" in env.agents}
                obs_d, rew_d, term_d, trunc_d, info_d = env.step(actions)
                
                # [Problem 1] Determine if episode is completely finished
                all_done = not env.agents
                zero_obs = np.zeros(total_obs_dim, dtype=np.float32)
                
                if all_done:
                    # Save terminal observations for PPO bootstrapping
                    for i in range(n_drones):
                        agent = f"drone_{i}"
                        if agent not in info_d: info_d[agent] = {}
                        info_d[agent]["terminal_observation"] = obs_d.get(agent, zero_obs)
                    
                    # Reset environment
                    new_obs_d, reset_info_d = env.reset()
                    ghost_obs.clear()
                    
                    # Construct return lists for the reset state
                    o_l = [new_obs_d.get(f"drone_{i}", zero_obs) for i in range(n_drones)]
                    r_l = [0.0]*10
                    d_l = [True]*10 # Signaling boundary
                    i_l = [info_d.get(f"drone_{i}", {}) for i in range(n_drones)]
                    # Merge reset infos safely if needed
                    for idx, agent_name in enumerate([f"drone_{j}" for j in range(n_drones)]):
                        i_l[idx].update(reset_info_d.get(agent_name, {}))
                else:
                    o_l, r_l, d_l, i_l = [], [], [], []
                    for i in range(n_drones):
                        agent = f"drone_{i}"
                        if term_d.get(agent, False) or trunc_d.get(agent, False):
                            last = obs_d.get(agent, zero_obs)
                            ghost_obs[agent] = last
                            o_l.append(last); r_l.append(rew_d.get(agent,0.0)); d_l.append(False); i_l.append(info_d.get(agent,{}))
                        elif agent in ghost_obs:
                            o_l.append(ghost_obs[agent]); r_l.append(0.0); d_l.append(False); i_l.append({})
                        else:
                            o_l.append(obs_d.get(agent, zero_obs)); r_l.append(rew_d.get(agent,0.0)); d_l.append(False); i_l.append(info_d.get(agent,{}))
                
                remote.send((np.array(o_l, dtype=np.float32), np.array(r_l, dtype=np.float32), np.array(d_l, bool), i_l))
                
            elif cmd == 'reset':
                obs_d, info_d = env.reset(); ghost_obs.clear()
                remote.send(np.array([obs_d.get(f"drone_{i}", np.zeros(total_obs_dim)) for i in range(n_drones)], dtype=np.float32))
                
            elif cmd == 'set_curriculum':
                r_sen, r_com = data
                # [Problem 5] Dirty-check inside worker as well
                if abs(r_sen - last_r_sensor) > 1e-4 or abs(r_com - last_r_comm) > 1e-4:
                    env.set_curriculum(r_sen, r_com)
                    last_r_sensor, last_r_comm = r_sen, r_com
                remote.send(True)
                
            elif cmd == 'set_target_density':
                env.set_target_density(data); remote.send(True)
                
            elif cmd == 'close': env.close(); break
            elif cmd == 'get_spaces': remote.send((env.observation_spaces["drone_0"], env.action_spaces["drone_0"]))
            
    except Exception as e:
        # [Problem 2] Refined Exception Handling
        print(f"\n[WORKER CRASH] Exception in worker process: {e}")
        traceback.print_exc()
        remote.close()

class MultiProcessEnv_v15(VecEnv):
    def __init__(self, n_workers):
        self.closed = False; self.n_workers = n_workers
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [Process(target=worker, args=(wr, r), daemon=True) for (wr, r) in zip(self.work_remotes, self.remotes)]
        for p in self.ps: p.start()
        for r in self.work_remotes: r.close()
        self.remotes[0].send(('get_spaces', None)); obs_space, act_space = self.remotes[0].recv()
        super().__init__(n_workers * 10, obs_space, act_space)
    def step_async(self, actions):
        for i in range(self.n_workers): self.remotes[i].send(('step', actions[i*10:(i+1)*10]))
    def step_wait(self):
        o, r, d, i = zip(*[remote.recv() for remote in self.remotes])
        return np.concatenate(o), np.concatenate(r), np.concatenate(d), [item for sub in i for item in sub]
    def reset(self):
        for r in self.remotes: r.send(('reset', None))
        return np.concatenate([r.recv() for r in self.remotes])
    def set_curriculum(self, r_sensor, r_comm):
        for r in self.remotes: r.send(('set_curriculum', (r_sensor, r_comm)))
        return [r.recv() for r in self.remotes]
    def set_target_density(self, density):
        for r in self.remotes: r.send(('set_target_density', density))
        return [r.recv() for r in self.remotes]
    def close(self):
        if self.closed: return
        for r in self.remotes: r.send(('close', None))
        for p in self.ps: p.join(); self.closed = True
    def get_attr(self, name, i=None): return [None] * self.num_envs
    def set_attr(self, name, val, i=None): pass
    def env_method(self, name, *a, i=None, **k):
        if name == "set_curriculum": return self.set_curriculum(*a)
        if name == "set_target_density": return self.set_target_density(*a)
        return [None] * self.num_envs
    def env_is_wrapped(self, cls, i=None): return [False] * self.num_envs

def run_v15_master_training():
    num_cpu = 10; base_env = MultiProcessEnv_v15(n_workers=num_cpu)
    # [Training Issue 5 FIX] Added gamma=0.99 and relaxed clipping
    env = VecNormalize(base_env, norm_obs=False, norm_reward=True, clip_reward=100.0, gamma=0.99)
    policy_kwargs = dict(
        net_arch=dict(pi=[512, 512, 256], vf=[512, 512, 256]), 
        activation_fn=nn.Tanh
    )
    # [Problem 7 FIX] batch_size=4096
    model = PPO(MAPPO_Policy_v15, env, verbose=1, learning_rate=3e-4, n_steps=2048, batch_size=4096, n_epochs=10, gamma=0.99, gae_lambda=0.95, ent_coef=0.03, policy_kwargs=policy_kwargs, tensorboard_log="./logs/v15_Master/")
    
    os.makedirs("./models/v15_Master/", exist_ok=True)
    # [Training Issue 6 FIX] save_freq=10,000,000 for 50M run
    checkpoint = CheckpointCallback(save_freq=10_000_000, save_path='./models/v15_Master/', name_prefix='v15_master_gen')
    curriculum = CurriculumCallback()
    
    print("\n🥇 [V15-Master] Initializing Terminal Certification Run (50M steps)...")
    # [Terminal UI FIX] Added progress_bar=True for real-time tracking
    model.learn(total_timesteps=50_000_000, callback=[checkpoint, curriculum], progress_bar=True)
    model.save("./models/v15_Master_Final_50M"); env.save("./models/v15_Master_Normalize.pkl"); env.close()

if __name__ == "__main__":
    run_v15_master_training()