"""
Slot-fusion single-stage trainer (adapted from train_raster.py).
Trains ON or OFF arm, one stage at a time. Chains stages automatically.

Usage:
  python train_slot_fusion.py on  0   # ON stage 0 (loads M0)
  python train_slot_fusion.py on  1   # ON stage 1 (loads ON stage 0)
  python train_slot_fusion.py off 0   # OFF stage 0 (loads M0)

No pauses. Set it and sleep.
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import sys
import tempfile
import torch
import torch.nn as nn
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecEnv, VecNormalize
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.callbacks import CheckpointCallback
from multiprocessing import Process, Pipe

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
for _p in (_ROOT, _PHASE_CD, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)
from swarm_env_raster import SwarmLidarEnv_Raster, OBS_DIM

N_WORKERS = 10
LOCAL = 130
GLOBAL = 520

# Curriculum: (steps, dropout, sustain, density, label)
# Dropout=0.10/sustain=5 => ~33% blind, realistic
# Progressive density: 0.15 → 0.25 → 0.35 (forces communication reliance)
# Safe path: 1M per stage (6M total) for full adaptation to fused obstacles
CURRICULUM = [
    (1_000_000, 0.10, 5, 0.15, "S0-Adapt"),
    (1_000_000, 0.15, 5, 0.25, "S1-Harder"),
    (1_000_000, 0.20, 5, 0.35, "S2-Final"),
]


class MAPPO_Extractor_M0(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        pi_layers, last = [], LOCAL
        for d in net_arch['pi']:
            pi_layers += [nn.Linear(last, d), activation_fn()]; last = d
        self.policy_net = nn.Sequential(*pi_layers)
        vf_layers, last_vf = [], GLOBAL
        for d in net_arch['vf']:
            vf_layers += [nn.Linear(last_vf, d), activation_fn()]; last_vf = d
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi, self.latent_dim_vf = last, last_vf

    def forward(self, f):
        return self.policy_net(f[:, :LOCAL]), self.value_net(f[:, LOCAL:])

    def forward_actor(self, f):
        return self.policy_net(f[:, :LOCAL])

    def forward_critic(self, f):
        return self.value_net(f[:, LOCAL:])


class MAPPO_Policy_M0(ActorCriticPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_M0(self.features_dim, self.net_arch, self.activation_fn)


# ── Worker for MultiProcessRasterEnv ──────────────────────────────────────────
def worker(remote, parent_remote, density, comm_range, lidar_range, dropout, sustain, use_shared, slot_fusion):
    import os
    os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
    os.environ["OMP_NUM_THREADS"] = "1"
    parent_remote.close()
    env = SwarmLidarEnv_Raster(
        render_mode=None,
        target_density=density,
        communication_range=comm_range,
        congestion_mode="lidar",
        lidar_range=lidar_range,
        lidar_dropout=dropout,
        dropout_sustain=sustain,
        use_shared_map=use_shared,
        probe_lidar_slot=False,
        slot_fusion=slot_fusion,
        straight_line_goal=False
    )
    n_drones = 10
    ghost_obs = {}
    zero_obs = np.zeros(650, dtype=np.float32)  # 650-d for slot-fusion
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
                        obs_list.append(last_obs)
                        rew_list.append(rew_d.get(agent, 0.0))
                        done_list.append(False)
                        info_list.append(info_d.get(agent, {}))
                    elif agent in ghost_obs:
                        obs_list.append(ghost_obs[agent])
                        rew_list.append(0.0)
                        done_list.append(False)
                        info_list.append({})
                    else:
                        obs_list.append(obs_d.get(agent, zero_obs))
                        rew_list.append(rew_d.get(agent, 0.0))
                        done_list.append(False)
                        info_list.append(info_d.get(agent, {}))
                if all_done:
                    new_obs_d, _ = env.reset(options={"spawn_mode": "clustered" if np.random.random() < 0.7 else "random"})
                    ghost_obs.clear()
                    obs_list, rew_list, done_list, info_list = [], [], [], []
                    for i in range(n_drones):
                        agent = f"drone_{i}"
                        obs_list.append(new_obs_d.get(agent, zero_obs))
                        rew_list.append(0.0)
                        done_list.append(True)
                        info_list.append({})
                remote.send((np.array(obs_list, dtype=np.float32), np.array(rew_list, dtype=np.float32),
                             np.array(done_list, dtype=bool), info_list))
            elif cmd == 'reset':
                obs_d, _ = env.reset(options={"spawn_mode": "clustered" if np.random.random() < 0.7 else "random"})
                ghost_obs.clear()
                remote.send(np.array([obs_d.get(f"drone_{i}", zero_obs) for i in range(n_drones)], dtype=np.float32))
            elif cmd == 'close':
                env.close()
                break
            elif cmd == 'get_spaces':
                remote.send((env.observation_spaces["drone_0"], env.action_spaces["drone_0"]))
    except Exception as e:
        print(f"[!] Worker error: {e}")
        remote.close()


class MultiProcessSlotFusionEnv(VecEnv):
    def __init__(self, n_workers, density, comm_range, lidar_range, dropout, sustain, use_shared):
        self.closed = False
        self.n_workers = n_workers
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [
            Process(target=worker,
                    args=(wr, r, density, comm_range, lidar_range, dropout, sustain, use_shared, True),
                    daemon=True)
            for (wr, r) in zip(self.work_remotes, self.remotes)
        ]
        for p in self.ps:
            p.start()
        for r in self.work_remotes:
            r.close()
        self.remotes[0].send(('get_spaces', None))
        obs_space, act_space = self.remotes[0].recv()
        super().__init__(n_workers * 10, obs_space, act_space)

    def step_async(self, actions):
        for i in range(self.n_workers):
            self.remotes[i].send(('step', actions[i * 10:(i + 1) * 10]))

    def step_wait(self):
        obs, rews, dones, infos = zip(*[r.recv() for r in self.remotes])
        return np.concatenate(obs), np.concatenate(rews), np.concatenate(dones), [i for sub in infos for i in sub]

    def reset(self):
        for r in self.remotes:
            r.send(('reset', None))
        return np.concatenate([r.recv() for r in self.remotes])

    def close(self):
        if self.closed:
            return
        for r in self.remotes:
            r.send(('close', None))
        for p in self.ps:
            p.join()
        self.closed = True

    def get_attr(self, n, indices=None):
        return [None] * self.num_envs

    def set_attr(self, n, v, indices=None):
        pass

    def env_method(self, name, *a, indices=None, **k):
        pass

    def env_is_wrapped(self, w, indices=None):
        return [False] * self.num_envs


def make_env(comm_range, lidar_range, dropout, sustain, density, use_shared):
    base = MultiProcessSlotFusionEnv(
        n_workers=N_WORKERS,
        density=density,
        comm_range=comm_range,
        lidar_range=lidar_range,
        dropout=dropout,
        sustain=sustain,
        use_shared=use_shared
    )
    env = VecNormalize(base, norm_obs=False, norm_reward=True, clip_reward=10.0)
    return env


def main():
    if len(sys.argv) < 3:
        print("Usage: python train_slot_fusion.py <on|off> <stage>")
        print("  python train_slot_fusion.py on  0   # ON stage 0")
        print("  python train_slot_fusion.py on  1   # ON stage 1 (loads stage 0)")
        sys.exit(1)

    mode = sys.argv[1].lower()
    stage = int(sys.argv[2])
    use_shared = (mode == "on")
    tag = "ON" if use_shared else "OFF"

    if stage < 0 or stage >= len(CURRICULUM):
        print(f"[!] stage must be 0–{len(CURRICULUM)-1}")
        return

    steps, dropout, sustain, density, label = CURRICULUM[stage]
    lidar_range = 8.0  # Fixed at 8m for slot-fusion
    comm_range = 10.0

    print(f"\n{'='*70}")
    print(f"SLOT-FUSION TRAINING | {tag:3s} | Stage {stage} — {label}")
    print(f"  steps={steps/1e6:.1f}M  dropout={dropout}  sustain={sustain}  "
          f"lidar={lidar_range}m  density={density:.2f}")
    blind_pct = dropout * sustain / (dropout * sustain + 1.0) * 100.0
    print(f"  expected blind: ~{blind_pct:.0f}%")
    print(f"{'='*70}\n")

    # Determine checkpoint to load
    if stage == 0:
        load_path = "models/apex_ultra_glide_v14_comm8_lidar_final.zip"
        print(f"[*] Loading M0: {load_path}")
    else:
        load_path = f"models/raster_slot_fusion_{tag}_stage{stage-1}_final.zip"
        print(f"[*] Loading previous stage: {load_path}")

    if not os.path.exists(load_path):
        for cand in (os.path.join("models", os.path.basename(load_path)), os.path.abspath(load_path)):
            if os.path.exists(cand):
                load_path = cand
                break

    if not os.path.exists(load_path):
        print(f"[!] Checkpoint not found: {load_path}")
        return

    # Create env
    env = make_env(comm_range, lidar_range, dropout, sustain, density, use_shared)

    # Load model
    model = PPO.load(load_path, env=env,
                     custom_objects={"policy_class": MAPPO_Policy_M0}, device="auto")
    model.learning_rate = 3e-5
    model.ent_coef = 0.020

    # Train
    print(f"[*] Training stage {stage}...")
    model.learn(total_timesteps=steps, reset_num_timesteps=False, progress_bar=True)

    # Save
    out_ckpt = f"models/raster_slot_fusion_{tag}_stage{stage}_final"
    model.save(out_ckpt)
    print(f"\n[OK] Saved: {out_ckpt}.zip")

    env.close()
    print(f"[*] Stage {stage} complete. Ready for eval or next stage.")


if __name__ == "__main__":
    main()
