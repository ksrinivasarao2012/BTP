"""
STEP 2 — Train M1: retrain the swarm against RAMMERS, NO explicit threat signal.

Tests whether the swarm learns to evade physical attackers purely from retraining
(the existing collision penalty). Transfer from comm8_lidar.

Design (pragmatic):
- Rammers (drones in traitor_indices) are SCRIPTED env hazards: the env overrides their
  actions via _ram_action (traitor_behavior="ram"). They are EXCLUDED from learning by
  feeding their VecEnv slots a zero-obs + reward 0 (so ~no gradient), while the env still
  drives their ramming. Honest drones (the rest) learn normally from the -500 collision
  penalty when rammed.
- Episode resets when all HONEST drones are done (rammers ignored).
- num_envs stays n_workers*10 (rammer slots kept but inert) -> no VecEnv-size change across
  the f-curriculum.

Usage:
    python train_ram_M1.py
Produces: models/apex_ultra_glide_M1_ram_final.zip
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import torch
import torch.nn as nn
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecEnv, VecNormalize
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.callbacks import CheckpointCallback
from swarm_env_step_B10_8_0m import SwarmLidarEnv_StepB10_8_0m
from multiprocessing import Process, Pipe

OBS_DIM = 130 + 520
CONGESTION_MODE = "lidar"   # match the comm8_lidar transfer base
COMM = 8.0


class MAPPO_Extractor_B5(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        pi_layers, last = [], 130
        for d in net_arch['pi']:
            pi_layers += [nn.Linear(last, d), activation_fn()]; last = d
        self.policy_net = nn.Sequential(*pi_layers)
        vf_layers, last_vf = [], 520
        for d in net_arch['vf']:
            vf_layers += [nn.Linear(last_vf, d), activation_fn()]; last_vf = d
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi, self.latent_dim_vf = last, last_vf

    def forward(self, f): return self.policy_net(f[:, :130]), self.value_net(f[:, 130:])
    def forward_actor(self, f): return self.policy_net(f[:, :130])
    def forward_critic(self, f): return self.value_net(f[:, 130:])


class MAPPO_Policy_B5(ActorCriticPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_B5(self.features_dim, self.net_arch, self.activation_fn)


def worker(remote, parent_remote, density, comm_range, congestion_mode, traitor_indices):
    import os
    os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
    os.environ["OMP_NUM_THREADS"] = "1"
    parent_remote.close()
    env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density,
                                     communication_range=comm_range, congestion_mode=congestion_mode)
    n_drones = 10
    traitors = set(traitor_indices)
    env.traitor_indices = set(traitors)
    env.traitor_behavior = "ram"
    env.deception_mode = "none"
    zero_obs = np.zeros(OBS_DIM, dtype=np.float32)
    ghost_obs = {}

    def is_traitor(i):
        return i in traitors

    try:
        while True:
            cmd, data = remote.recv()
            if cmd == 'step':
                # send actions for living agents (env overrides rammer actions internally)
                actions = {f"drone_{i}": data[i] for i in range(n_drones) if f"drone_{i}" in env.agents}
                obs_d, rew_d, term_d, trunc_d, info_d = env.step(actions)
                # reset when all HONEST drones are done (ignore rammers)
                honest_left = [a for a in env.agents if env.agent_name_mapping[a] not in traitors]
                all_done = not honest_left

                obs_list, rew_list, done_list, info_list = [], [], [], []
                for i in range(n_drones):
                    agent = f"drone_{i}"
                    if is_traitor(i):
                        # rammer slot: inert in the learning buffer
                        obs_list.append(zero_obs); rew_list.append(0.0); done_list.append(False); info_list.append({})
                        continue
                    if all_done:
                        pass  # overwritten in the reset block below
                    elif term_d.get(agent, False) or trunc_d.get(agent, False):
                        last_obs = obs_d.get(agent, zero_obs); ghost_obs[agent] = last_obs
                        obs_list.append(last_obs); rew_list.append(rew_d.get(agent, 0.0)); done_list.append(False); info_list.append(info_d.get(agent, {}))
                    elif agent in ghost_obs:
                        obs_list.append(ghost_obs[agent]); rew_list.append(0.0); done_list.append(False); info_list.append({})
                    else:
                        obs_list.append(obs_d.get(agent, zero_obs)); rew_list.append(rew_d.get(agent, 0.0)); done_list.append(False); info_list.append(info_d.get(agent, {}))

                if all_done:
                    new_obs_d, _ = env.reset(options={"spawn_mode": "clustered" if np.random.random() < 0.7 else "random"})
                    env.traitor_indices = set(traitors); env.traitor_behavior = "ram"; env.deception_mode = "none"
                    ghost_obs.clear()
                    obs_list, rew_list, done_list, info_list = [], [], [], []
                    for i in range(n_drones):
                        agent = f"drone_{i}"
                        if is_traitor(i):
                            obs_list.append(zero_obs); rew_list.append(0.0); done_list.append(True); info_list.append({})
                        else:
                            obs_list.append(new_obs_d.get(agent, zero_obs)); rew_list.append(0.0); done_list.append(True); info_list.append({})

                remote.send((np.array(obs_list, dtype=np.float32), np.array(rew_list, dtype=np.float32),
                             np.array(done_list, dtype=bool), info_list))

            elif cmd == 'reset':
                obs_d, _ = env.reset(options={"spawn_mode": "clustered" if np.random.random() < 0.7 else "random"})
                env.traitor_indices = set(traitors); env.traitor_behavior = "ram"; env.deception_mode = "none"
                ghost_obs.clear()
                out = []
                for i in range(n_drones):
                    out.append(zero_obs if is_traitor(i) else obs_d.get(f"drone_{i}", zero_obs))
                remote.send(np.array(out, dtype=np.float32))
            elif cmd == 'set_traitors':
                traitors = set(data)
                env.traitor_indices = set(traitors)
            elif cmd == 'set_density':
                env.set_target_density(data)
            elif cmd == 'close':
                env.close(); break
            elif cmd == 'get_spaces':
                remote.send((env.observation_spaces["drone_0"], env.action_spaces["drone_0"]))
    except Exception as e:
        remote.close()


class MultiProcessRamEnv(VecEnv):
    def __init__(self, n_workers, density, comm_range, congestion_mode, traitor_indices):
        self.closed = False
        self.n_workers = n_workers
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [Process(target=worker, args=(wr, r, density, comm_range, congestion_mode, list(traitor_indices)), daemon=True)
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

    def set_traitors(self, indices):
        for r in self.remotes: r.send(('set_traitors', list(indices)))

    def get_attr(self, n, indices=None): return [None] * self.num_envs
    def set_attr(self, n, v, indices=None): pass
    def env_method(self, name, *a, indices=None, **k):
        if name == "set_target_density": self.set_density(a[0])
        elif name == "set_traitors": self.set_traitors(a[0])
    def env_is_wrapped(self, w, indices=None): return [False] * self.num_envs


def find_base():
    for p in ["models/apex_ultra_glide_v14_comm8_lidar_final.zip",
              "models/apex_ultra_glide_v14_8_0m_final.zip"]:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("comm8_lidar base model not found.")


def main():
    num_cpu = 10
    base = find_base()
    print(f"STEP 2 — M1: retrain vs RAMMERS (no explicit signal). Transfer from: {base}")

    # start with f=1 rammer (drone 0), density 0.30
    base_env = MultiProcessRamEnv(num_cpu, density=0.30, comm_range=COMM,
                                  congestion_mode=CONGESTION_MODE, traitor_indices=[0])
    env = VecNormalize(base_env, norm_obs=False, norm_reward=True, clip_reward=10.0)

    model = PPO.load(base, env=env, custom_objects={"policy_class": MAPPO_Policy_B5}, device="auto")
    model.learning_rate = 5e-5
    model.ent_coef = 0.015

    # curriculum: (steps, density, rammer indices)
    curriculum = [
        (2_000_000, 0.30, [0]),       # warm up vs 1 rammer
        (3_000_000, 0.35, [0, 1]),    # then 2 rammers at the harder density
    ]

    os.makedirs("./models/checkpoints_M1_ram/", exist_ok=True)
    cb = CheckpointCallback(save_freq=500_000, save_path="./models/checkpoints_M1_ram/", name_prefix="M1_ram")

    # Set up the SB3 Logger to output both to standard output (for tables) and TensorBoard
    from stable_baselines3.common.logger import configure
    new_logger = configure("./logs/tb_M1_ram/", ["stdout", "tensorboard"])
    model.set_logger(new_logger)

    # Re-add tqdm progress bar integration
    from stable_baselines3.common.callbacks import ProgressBarCallback
    pbar_cb = ProgressBarCallback()

    for steps, density, traitors in curriculum:
        print(f"\nPHASE: density={density} | rammers={traitors} | steps={steps/1e6:.1f}M")
        env.env_method("set_target_density", density)
        env.env_method("set_traitors", traitors)
        model.learn(total_timesteps=steps, reset_num_timesteps=False, callback=[cb, pbar_cb])

    out = "./models/apex_ultra_glide_M1_ram_final"
    model.save(out)
    env.save("./models/vecnormalize_M1_ram_final.pkl")
    env.close()
    print(f"\nDone. M1 saved: {out}.zip")
    print("Next: eval with  python probe_ram.py 2 models/apex_ultra_glide_M1_ram_final.zip")


if __name__ == "__main__":
    main()
