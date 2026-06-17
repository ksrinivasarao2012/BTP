"""
STAGE A2 — Train comm-ON vs comm-OFF model with Shared Hazards (677 dims).

Usage:
  python Phase_CD/Collab_Perception/train_collab.py 5 10 --hazard on
  python Phase_CD/Collab_Perception/train_collab.py 5 10 --hazard off
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import sys
import torch
import torch.nn as nn
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecEnv, VecNormalize
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.callbacks import CheckpointCallback

# chdir to repo root
_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
for _p in (_ROOT, _PHASE_CD, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)

from Phase_CD.Collab_Perception.swarm_env_collab import SwarmLidarEnv_StepB10_8_0m
from multiprocessing import Process, Pipe

CONGESTION_MODE = "lidar"
OBS_DIM = 130 + 27 + 520  # Design A Total: 677

class MAPPO_Extractor_B5(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        pi_layers, last = [], 157  # Local (130) + Hazards (27)
        for d in net_arch['pi']:
            pi_layers += [nn.Linear(last, d), activation_fn()]; last = d
        self.policy_net = nn.Sequential(*pi_layers)
        vf_layers, last_vf = [], 520
        for d in net_arch['vf']:
            vf_layers += [nn.Linear(last_vf, d), activation_fn()]; last_vf = d
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi, self.latent_dim_vf = last, last_vf

    def forward(self, f): return self.policy_net(f[:, :157]), self.value_net(f[:, 157:])
    def forward_actor(self, f): return self.policy_net(f[:, :157])
    def forward_critic(self, f): return self.value_net(f[:, 157:])

class MAPPO_Policy_B5(ActorCriticPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_B5(self.features_dim, self.net_arch, self.activation_fn)

def worker(remote, parent_remote, density, comm_range, lidar_range, congestion_mode, share_hazards, lidar_dropout):
    import os
    os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
    os.environ["OMP_NUM_THREADS"] = "1"
    parent_remote.close()
    env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density,
                                     communication_range=comm_range, congestion_mode=congestion_mode,
                                     lidar_range=lidar_range)
    env.share_hazards = share_hazards
    env.lidar_dropout_prob = lidar_dropout
    n_drones = 10
    ghost_obs = {}
    zero_obs = np.zeros(OBS_DIM, dtype=np.float32)
    try:
        while True:
            cmd, data = remote.recv()
            if cmd == 'step':
                actions = {f"drone_{i}": data[i] for i in range(n_drones) if f"drone_{i}" in env.agents}
                obs_d, rew_d, term_d, trunc_d, info_d = env.step(actions)
                obs_list, rew_list, done_list, info_list = [], [], [], []
                all_done = not env.agents
                for i in range(n_drones):
                    agent = f"drone_{i}"
                    if all_done:
                        pass
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
                remote.send(np.array([obs_d.get(f"drone_{i}", zero_obs) for i in range(n_drones)], dtype=np.float32))
            elif cmd == 'close':
                env.close(); break
            elif cmd == 'set_density':
                env.set_target_density(data)
            elif cmd == 'get_spaces':
                remote.send((env.observation_spaces["drone_0"], env.action_spaces["drone_0"]))
    except Exception:
        remote.close()

class MultiProcessPZEnv(VecEnv):
    def __init__(self, n_workers, density, comm_range, lidar_range, congestion_mode, share_hazards, lidar_dropout):
        self.closed = False
        self.n_workers = n_workers
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [Process(target=worker, args=(wr, r, density, comm_range, lidar_range, congestion_mode, share_hazards, lidar_dropout), daemon=True)
                   for (wr, r) in zip(self.work_remotes, self.remotes)]
        for p in self.ps: p.start()
        for r in self.work_remotes: r.close()
        self.remotes[0].send(('get_spaces', None))
        obs_space, act_space = self.remotes[0].recv()
        super().__init__(n_workers * 10, obs_space, act_space)

    def step_async(self, actions):
        for i in range(self.n_workers): self.remotes[i].send(('step', actions[i * 10:(i + 1) * 10]))

    def step_wait(self):
        obs, rews, dones, infos = zip(*[r.recv() for r in self.remotes])
        return np.concatenate(obs), np.concatenate(rews), np.concatenate(dones), [i for sub in infos for i in sub]

    def reset(self):
        for r in self.remotes: r.send(('reset', None))
        return np.concatenate([r.recv() for r in self.remotes])

    def close(self):
        if self.closed: return
        for r in self.remotes: r.send(('close', None))
        for p in self.ps: p.join()
        self.closed = True

    def set_density(self, d):
        for r in self.remotes: r.send(('set_density', d))

    def get_attr(self, n, indices=None): return [None] * self.num_envs
    def set_attr(self, n, v, indices=None): pass
    def env_method(self, name, *a, indices=None, **k):
        if name == "set_target_density": self.set_density(a[0])
    def env_is_wrapped(self, w, indices=None): return [False] * self.num_envs

def main():
    if len(sys.argv) < 3:
        print("Usage: python train_collab.py <lidar_range> <comm_range> --hazard <on|off>")
        sys.exit(1)
    lidar_range = float(sys.argv[1])
    comm_range = float(sys.argv[2])
    
    share_hazards = True
    lidar_dropout = 0.0
    
    # Parse CLI args
    args = sys.argv[3:]
    # parse options
    i = 0
    while i < len(args):
        arg = args[i].lower()
        if arg == "--hazard" and i + 1 < len(args):
            share_hazards = (args[i+1].lower() == "on")
            i += 2
        elif arg == "off":
            share_hazards = False
            i += 1
        elif arg == "on":
            share_hazards = True
            i += 1
        elif arg == "--dropout" and i + 1 < len(args):
            lidar_dropout = float(args[i+1])
            i += 2
        else:
            i += 1

    L = str(int(lidar_range)) if lidar_range == int(lidar_range) else str(lidar_range)
    C = str(int(comm_range)) if comm_range == int(comm_range) else str(comm_range)
    tag = "ON" if share_hazards else "OFF"
    drop_tag = f"_drop{lidar_dropout:.1f}" if lidar_dropout > 0.0 else ""

    base = "models/collab_expanded_M0.zip"
    if not os.path.exists(base):
        raise FileNotFoundError(f"Expanded base model not found at {base}. Run surgical_expand.py first.")

    print(f"STAGE A2 — Shared Hazard Train | lidar={lidar_range} m | comm={comm_range} m | hazards={tag} | dropout={lidar_dropout}")
    print(f"  -> transferring from: {base}")

    base_env = MultiProcessPZEnv(n_workers=10, density=0.30, comm_range=comm_range,
                                 lidar_range=lidar_range, congestion_mode=CONGESTION_MODE,
                                 share_hazards=share_hazards, lidar_dropout=lidar_dropout)
    env = VecNormalize(base_env, norm_obs=False, norm_reward=True, clip_reward=10.0)

    model = PPO.load(base, env=env, custom_objects={"policy_class": MAPPO_Policy_B5}, device="auto")
    model.learning_rate = 5e-5
    model.ent_coef = 0.015

    curriculum = [(2_000_000, 0.30), (3_000_000, 0.35)]
    out_label = f"collab_l{L}_c{C}_hazard{tag}{drop_tag}"
    ckpt_dir = f"./models/checkpoints_{out_label}/"
    os.makedirs(ckpt_dir, exist_ok=True)
    cb = CheckpointCallback(save_freq=500_000, save_path=ckpt_dir, name_prefix=out_label)

    for steps, density in curriculum:
        print(f"\nPHASE: density={density} | steps={steps/1e6:.1f}M | lidar={lidar_range}m | comm={comm_range}m | dropout={lidar_dropout}")
        env.env_method("set_target_density", density)
        model.learn(total_timesteps=steps, reset_num_timesteps=False, callback=cb, progress_bar=True)

    out = f"./models/{out_label}_final"
    model.save(out)
    env.save(f"./models/vecnormalize_{out_label}_final.pkl")
    env.close()
    print(f"\nDone. Model saved: {out}.zip")

if __name__ == "__main__":
    main()
