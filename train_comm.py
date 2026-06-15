"""
Generic communication-range trainer for the comm-range sensitivity sweep.

Fine-tunes from V14 (unlimited) at a SPECIFIED communication range, using the
SAME curriculum as V14/v14_8.0m (0.30 -> 0.35), so the only difference between
models in the sweep is the communication range.

Usage:
    python train_comm.py 3      # train a 3 m model
    python train_comm.py 5      # train a 5 m model

Note: 8 m (v14_8.0m) and inf (V14) already exist - do NOT retrain those.
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
from swarm_env_step_B10_8_0m import SwarmLidarEnv_StepB10_8_0m
from multiprocessing import Process, Pipe


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


def worker(remote, parent_remote, density, comm_range, use_congestion=True, congestion_mode="env"):
    import os
    os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
    os.environ["OMP_NUM_THREADS"] = "1"
    parent_remote.close()
    env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density, communication_range=comm_range, use_congestion=use_congestion, congestion_mode=congestion_mode)
    n_drones = 10
    ghost_obs = {}
    try:
        while True:
            cmd, data = remote.recv()
            if cmd == 'step':
                actions = {f"drone_{i}": data[i] for i in range(n_drones) if f"drone_{i}" in env.agents}
                obs_d, rew_d, term_d, trunc_d, info_d = env.step(actions)
                zero_obs = np.zeros(130 + 520, dtype=np.float32)
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
                remote.send(np.array([obs_d.get(f"drone_{i}", np.zeros(130 + 520)) for i in range(n_drones)], dtype=np.float32))
            elif cmd == 'close':
                env.close(); break
            elif cmd == 'set_density':
                env.set_target_density(data)
            elif cmd == 'get_spaces':
                remote.send((env.observation_spaces["drone_0"], env.action_spaces["drone_0"]))
    except Exception:
        remote.close()


class MultiProcessPZEnv(VecEnv):
    def __init__(self, n_workers, density, comm_range, use_congestion=True, congestion_mode="env"):
        self.closed = False
        self.n_workers = n_workers
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [Process(target=worker, args=(wr, r, density, comm_range, use_congestion, congestion_mode), daemon=True)
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


def find_v14():
    for p in [
        os.path.join("models", "apex_ultra_glide_v14_final.zip"),
        os.path.join("v10_IEEE_Final", "v14_Best_Model_Archive", "model", "apex_ultra_glide_v14_final.zip"),
    ]:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("V14 model not found - cannot transfer.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python train_comm.py <range> [nocong]")
        print("  e.g. python train_comm.py 8            (congestion ON)")
        print("       python train_comm.py 8 nocong     (congestion ablated -> always 0)")
        sys.exit(1)
    R = float(sys.argv[1])
    label = str(int(R)) if R == int(R) else str(R)
    # second arg: nocong | lidar | comm | both | env  (default env = legacy ground-truth)
    arg2 = sys.argv[2].lower() if len(sys.argv) > 2 else "env"
    use_congestion, congestion_mode, tag = True, "env", ""
    if arg2 in ("nocong", "no-congestion", "no_congestion"):
        use_congestion, tag = False, "_nocong"
    elif arg2 in ("lidar", "comm", "both"):
        congestion_mode, tag = arg2, f"_{arg2}"

    v14 = find_v14()
    print(f"PHASE B comm-sweep: comm_range={R} m | congestion={'OFF' if not use_congestion else congestion_mode}")
    print(f"  -> transferring from V14: {v14}")

    base_env = MultiProcessPZEnv(n_workers=10, density=0.30, comm_range=R, use_congestion=use_congestion, congestion_mode=congestion_mode)
    env = VecNormalize(base_env, norm_obs=False, norm_reward=True, clip_reward=10.0)

    model = PPO.load(v14, env=env, custom_objects={"policy_class": MAPPO_Policy_B5}, device="auto")
    model.learning_rate = 5e-5
    model.ent_coef = 0.015

    # IDENTICAL curriculum to V14 / v14_8.0m -> only comm range / congestion toggle differs
    curriculum = [(2_000_000, 0.30), (3_000_000, 0.35)]

    ckpt_dir = f"./models/checkpoints_comm{label}{tag}/"
    os.makedirs(ckpt_dir, exist_ok=True)
    cb = CheckpointCallback(save_freq=500_000, save_path=ckpt_dir, name_prefix=f"comm{label}{tag}")

    for steps, density in curriculum:
        print(f"\nPHASE: density={density} | steps={steps/1e6:.1f}M | comm={R}m | congestion={'ON' if use_congestion else 'OFF'}")
        env.env_method("set_target_density", density)
        model.learn(total_timesteps=steps, reset_num_timesteps=False, callback=cb, progress_bar=True)

    out = f"./models/apex_ultra_glide_v14_comm{label}{tag}_final"
    model.save(out)
    env.save(f"./models/vecnormalize_comm{label}{tag}_final.pkl")
    env.close()
    print(f"\nDone. Model saved: {out}.zip")


if __name__ == "__main__":
    main()
