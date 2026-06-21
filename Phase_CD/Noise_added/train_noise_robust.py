"""
OPTION C — fine-tune the ON model to navigate NOISY perception (noise domain randomization).

Goal: remove the navigation-OOD confound. The model was trained on CLEAN perception, so `base`
collapses under sensor noise (92->68%). Here we FINE-TUNE it with Gaussian position noise randomized
per episode (sigma ~ U[lo, hi]) so it stays competent across the noise range. NO traitors, NO defense
during training (the trust filter is an eval-time layer). After this, re-run the noise/robust/camouflage
evals on the noise-robust model and update PAPER_MASTER_PLAN.md (P1).

Curriculum (fine-tune, low LR):
  Stage 0 (1.5M): sigma ~ U[0.0, 0.3], density 0.20   (gentle adaptation)
  Stage 1 (2.0M): sigma ~ U[0.0, 0.6], density 0.25   (full noise range, lock-in robustness)
  Stage 2 (1.5M): sigma ~ U[0.0, 0.6], density 0.27   (lock-in at the EVAL density 0.27)

Usage (run python by full path; conda env swarm_rl):
  python train_noise_robust.py 0     # stage 0 (loads raster_slot_fusion_ON_stage2_final.zip)
  python train_noise_robust.py 1     # stage 1 (loads noise_robust_ON_stage0_final.zip)
  python train_noise_robust.py 2     # stage 2 (loads noise_robust_ON_stage1_final.zip; 0.27 lock-in)
Saves: models/noise_robust_ON_stage{0,1,2}_final.zip
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import sys
import torch
import torch.nn as nn
import numpy as np
from tqdm import tqdm
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecEnv, VecNormalize
from stable_baselines3.common.policies import ActorCriticPolicy
from multiprocessing import Process, Pipe

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
_COLLAB = os.path.join(_PHASE_CD, "Collab_Perception")
for _p in (_ROOT, _PHASE_CD, _COLLAB, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)
from env_noisy_byzantine import NoisyByzantineEnv

N_WORKERS = 10
LOCAL = 130
GLOBAL = 520

# (steps, noise_lo, noise_hi, density, label)
CURRICULUM = [
    (1_500_000, 0.0, 0.3, 0.20, "S0-LightNoise"),
    (2_000_000, 0.0, 0.6, 0.25, "S1-FullNoise"),
    (1_500_000, 0.0, 0.6, 0.27, "S2-Density027LockIn"),   # train & evaluate both at 0.27 (eval density)
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


# ── worker: noisy env, NO traitors/defense, noise re-sampled each episode ────────
def worker(remote, parent_remote, density, noise_lo, noise_hi):
    import os
    os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
    os.environ["OMP_NUM_THREADS"] = "1"
    parent_remote.close()
    env = NoisyByzantineEnv(
        render_mode=None, target_density=density, communication_range=10.0,
        congestion_mode="lidar", lidar_range=8.0,
        lidar_dropout=0.10, dropout_sustain=5, use_shared_map=True,
        false_obstacle_attack=False, traitor_indices=[], trust_defense=False,
        sensor_noise=0.0,
    )
    n_drones = 10
    ghost_obs = {}
    zero_obs = np.zeros(650, dtype=np.float32)

    def _reset():
        env.sensor_noise = float(np.random.uniform(noise_lo, noise_hi))   # domain randomization
        mode = "clustered" if np.random.random() < 0.7 else "random"
        obs_d, _ = env.reset(options={"spawn_mode": mode})
        ghost_obs.clear()
        return obs_d

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
                        last_obs = obs_d.get(agent, zero_obs); ghost_obs[agent] = last_obs
                        obs_list.append(last_obs); rew_list.append(rew_d.get(agent, 0.0))
                        done_list.append(False); info_list.append(info_d.get(agent, {}))
                    elif agent in ghost_obs:
                        obs_list.append(ghost_obs[agent]); rew_list.append(0.0)
                        done_list.append(False); info_list.append({})
                    else:
                        obs_list.append(obs_d.get(agent, zero_obs)); rew_list.append(rew_d.get(agent, 0.0))
                        done_list.append(False); info_list.append(info_d.get(agent, {}))
                if all_done:
                    new_obs_d = _reset()
                    obs_list, rew_list, done_list, info_list = [], [], [], []
                    for i in range(n_drones):
                        agent = f"drone_{i}"
                        obs_list.append(new_obs_d.get(agent, zero_obs)); rew_list.append(0.0)
                        done_list.append(True); info_list.append({})
                remote.send((np.array(obs_list, dtype=np.float32), np.array(rew_list, dtype=np.float32),
                             np.array(done_list, dtype=bool), info_list))
            elif cmd == 'reset':
                obs_d = _reset()
                remote.send(np.array([obs_d.get(f"drone_{i}", zero_obs) for i in range(n_drones)], dtype=np.float32))
            elif cmd == 'close':
                env.close(); break
            elif cmd == 'get_spaces':
                remote.send((env.observation_spaces["drone_0"], env.action_spaces["drone_0"]))
    except Exception as e:
        print(f"[!] worker error: {e}")
        remote.close()


class MultiProcessNoisyEnv(VecEnv):
    def __init__(self, n_workers, density, noise_lo, noise_hi):
        self.closed = False
        self.n_workers = n_workers
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [Process(target=worker, args=(wr, r, density, noise_lo, noise_hi), daemon=True)
                   for (wr, r) in zip(self.work_remotes, self.remotes)]
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

    def get_attr(self, n, indices=None): return [None] * self.num_envs
    def set_attr(self, n, v, indices=None): pass
    def env_method(self, name, *a, indices=None, **k): pass
    def env_is_wrapped(self, w, indices=None): return [False] * self.num_envs


def make_env(density, noise_lo, noise_hi):
    base = MultiProcessNoisyEnv(N_WORKERS, density, noise_lo, noise_hi)
    return VecNormalize(base, norm_obs=False, norm_reward=True, clip_reward=10.0)


def main():
    if len(sys.argv) < 2:
        print("Usage: python train_noise_robust.py <stage 0|1>"); return
    stage = int(sys.argv[1])
    if stage < 0 or stage >= len(CURRICULUM):
        print(f"[!] stage must be 0-{len(CURRICULUM)-1}"); return

    steps, noise_lo, noise_hi, density, label = CURRICULUM[stage]
    print(f"\n{'='*70}")
    print(f"OPTION C — noise-robust fine-tune | Stage {stage} — {label}")
    print(f"  steps={steps/1e6:.1f}M  sigma~U[{noise_lo},{noise_hi}]  density={density}  (no traitors)")
    print(f"{'='*70}\n")

    if stage == 0:
        load_path = "models/raster_slot_fusion_ON_stage2_final.zip"
    else:
        load_path = f"models/noise_robust_ON_stage{stage-1}_final.zip"
    if not os.path.exists(load_path):
        for cand in (os.path.join("models", os.path.basename(load_path)), os.path.abspath(load_path)):
            if os.path.exists(cand):
                load_path = cand; break
    if not os.path.exists(load_path):
        print(f"[!] checkpoint not found: {load_path}"); return
    print(f"[*] loading: {load_path}")

    env = make_env(density, noise_lo, noise_hi)
    model = PPO.load(load_path, env=env, custom_objects={"policy_class": MAPPO_Policy_M0}, device="auto")
    model.learning_rate = 3e-5
    model.ent_coef = 0.020

    print(f"[*] fine-tuning stage {stage} ({steps/1e6:.1f}M steps)...")
    model.learn(total_timesteps=steps, reset_num_timesteps=False, progress_bar=True)

    out = f"models/noise_robust_ON_stage{stage}_final"
    model.save(out)
    env.close()
    print(f"\n[OK] saved: {out}.zip")
    print(f"[*] next: stage {stage+1}" if stage + 1 < len(CURRICULUM) else "[*] curriculum complete.")


if __name__ == "__main__":
    main()
