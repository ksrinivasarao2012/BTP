"""
B3 — Train the raster model with BLIND-FORCING curriculum.

Root cause of the previous failure: the policy ignored the shared map entirely
(SHARED_MAP feature-importance drop = 0.60 pp vs LiDAR drop = 20.60 pp). PPO found
a perfectly good policy using goal_dir + own-LiDAR and never needed the shared map.

FIX — 4-stage curriculum that forces shared-map learning:

  Stage 0 (blind-force, 2M): dropout=0.60, sustain=1200 (episode length).
    At each episode reset, each drone independently goes blind with 60% probability and
    STAYS blind for the entire episode (sustain >= max_steps). Result: ~6 drones are
    episodically blind, ~4 are sighted. The 4 sighted drones populate the shared map;
    the 6 blind drones MUST learn to use it — there is no other obstacle source. This
    creates unavoidable gradient pressure on obs[130:178] weights. lidar=12m keeps
    sighted drones in-distribution (M0's native range). density=0.15 (sparse) gives
    blind drones a fighting chance to learn before the density increases.

  Stage 1 (transition, 1M): dropout=0.30, sustain=50, lidar=10m, density=0.22.
    Reduce sustained blindness; step LiDAR down. Policy already has shared-map weights
    from Stage 0 — this consolidates them under shorter blind windows.

  Stage 2 (LiDAR step-down, 1.5M): dropout=0.20, sustain=25, lidar=8m, density=0.27.
    LiDAR at 8m creates the comm-only annulus (8-10m). Moderate dropout.

  Stage 3 (gate, 2M): dropout=0.20, sustain=25, lidar=8m, density=0.30.
    Final gate condition. Gate: comm_value = ON - OFF >= ~5 pp.

Usage:
    Stage 0 only  : python train_raster.py 10 on  0       <- run Stage 0, stop, check FI
    Stage 1 only  : python train_raster.py 10 on  1       <- resume from stage0 checkpoint
    Stage 2 only  : python train_raster.py 10 on  2
    Stage 3 only  : python train_raster.py 10 on  3
    All stages    : python train_raster.py 10 on          <- runs all 4 without pausing
Args: <comm_range> <on|off> [stage_index]

Health checks (run between stages):
    python feature_importance_raster.py models/<ckpt>.zip 12 10 0.60 on 30   # after Stage 0
    python feature_importance_raster.py models/<ckpt>.zip  8 10 0.20 on 30   # after Stage 3
    SHARED_MAP drop should be >= 5 pp after Stage 0, >= 10 pp after Stage 3.
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
_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
for _p in (_ROOT, _PHASE_CD, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)
from swarm_env_raster import SwarmLidarEnv_Raster, OBS_DIM
from multiprocessing import Process, Pipe

CONGESTION_MODE = "lidar"
LOCAL_NEW = 178
GLOBAL    = 520
EXPANDED_BASE = "models/raster_expanded_M0.zip"
N_WORKERS = 10   # parallel env workers

# ── Curriculum ────────────────────────────────────────────────────────────────
# (steps, density, dropout, sustain, lidar_range, label)
# sustain=1200 = full episode length → episodic blindness (blind for whole episode)
CURRICULUM = [
    (2_000_000, 0.15, 0.60, 1200, 12.0, "S0-BlindForce"),
    # S1: dropout=0.10 sustain=5 → blind%=(0.10×5)/(0.10×5+1)=33%; drones have LiDAR 67% of steps
    # OLD BUG: dropout=0.30 sustain=50 → 93.8% blind (barely different from S0, no recovery possible)
    (1_000_000, 0.22, 0.10,    5, 10.0, "S1-Transition"),
    (1_500_000, 0.27, 0.20,   25,  8.0, "S2-LiDAR8m"),
    (2_000_000, 0.30, 0.20,   25,  8.0, "S3-Gate"),
]


# ── Architecture (unchanged from B2) ─────────────────────────────────────────
class MAPPO_Extractor_Raster(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        pi_layers, last = [], LOCAL_NEW
        for d in net_arch['pi']:
            pi_layers += [nn.Linear(last, d), activation_fn()]; last = d
        self.policy_net = nn.Sequential(*pi_layers)
        vf_layers, last_vf = [], GLOBAL
        for d in net_arch['vf']:
            vf_layers += [nn.Linear(last_vf, d), activation_fn()]; last_vf = d
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi, self.latent_dim_vf = last, last_vf
    def forward(self, f):        return self.policy_net(f[:, :LOCAL_NEW]), self.value_net(f[:, LOCAL_NEW:])
    def forward_actor(self, f):  return self.policy_net(f[:, :LOCAL_NEW])
    def forward_critic(self, f): return self.value_net(f[:, LOCAL_NEW:])


class MAPPO_Policy_Raster(ActorCriticPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_Raster(self.features_dim, self.net_arch, self.activation_fn)


# ── Multiprocess env ──────────────────────────────────────────────────────────
def worker(remote, parent_remote, density, comm_range, lidar_range, dropout, sustain, use_shared):
    import os
    os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
    os.environ["OMP_NUM_THREADS"] = "1"
    parent_remote.close()
    env = SwarmLidarEnv_Raster(
        render_mode=None, target_density=density, communication_range=comm_range,
        congestion_mode=CONGESTION_MODE, lidar_range=lidar_range,
        lidar_dropout=dropout, dropout_sustain=sustain, use_shared_map=use_shared
    )
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
                    new_obs_d, _ = env.reset(options={"spawn_mode": "clustered" if np.random.random() < 0.7 else "random"})
                    ghost_obs.clear()
                    obs_list, rew_list, done_list, info_list = [], [], [], []
                    for i in range(n_drones):
                        agent = f"drone_{i}"
                        obs_list.append(new_obs_d.get(agent, zero_obs)); rew_list.append(0.0)
                        done_list.append(True); info_list.append({})
                remote.send((np.array(obs_list, dtype=np.float32), np.array(rew_list, dtype=np.float32),
                             np.array(done_list, dtype=bool), info_list))
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


class MultiProcessRasterEnv(VecEnv):
    def __init__(self, n_workers, density, comm_range, lidar_range, dropout, sustain, use_shared):
        self.closed = False
        self.n_workers = n_workers
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [
            Process(target=worker,
                    args=(wr, r, density, comm_range, lidar_range, dropout, sustain, use_shared),
                    daemon=True)
            for (wr, r) in zip(self.work_remotes, self.remotes)
        ]
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


def make_env(comm_range, lidar_range, dropout, sustain, density, use_shared,
             vecnorm_load_path=None):
    """Create a new MultiProcessRasterEnv wrapped in VecNormalize.
    If vecnorm_load_path is given, reload reward-norm stats from it.
    """
    base = MultiProcessRasterEnv(
        n_workers=N_WORKERS, density=density, comm_range=comm_range,
        lidar_range=lidar_range, dropout=dropout, sustain=sustain, use_shared=use_shared
    )
    if vecnorm_load_path and os.path.exists(vecnorm_load_path):
        env = VecNormalize.load(vecnorm_load_path, base)
        env.training = True
    else:
        env = VecNormalize(base, norm_obs=False, norm_reward=True, clip_reward=10.0)
    return env


def main():
    if len(sys.argv) < 3:
        print("Usage: python train_raster.py <comm_range> <on|off> [stage_index]")
        print("  Stage 0 only : python train_raster.py 10 on 0")
        print("  Stage 1 only : python train_raster.py 10 on 1")
        print("  All stages   : python train_raster.py 10 on")
        sys.exit(1)

    comm_range = float(sys.argv[1])
    use_shared = sys.argv[2].lower() == "on"
    tag = "ON" if use_shared else "OFF"
    # Optional: run only a single stage (0-3). If omitted, runs all stages.
    only_stage = int(sys.argv[3]) if len(sys.argv) > 3 else None

    if not os.path.exists(EXPANDED_BASE):
        print(f"[!] expanded base not found: {EXPANDED_BASE}")
        print("    run surgical_expand_raster.py first.")
        return

    print(f"\n{'='*68}")
    print(f"RASTER BLIND-FORCE CURRICULUM  |  comm={comm_range}m  |  shared={tag}")
    print(f"  base : {EXPANDED_BASE}")
    print(f"  stages:")
    for i, (steps, density, dropout, sustain, lidar, label) in enumerate(CURRICULUM):
        blind_pct = dropout * sustain / (dropout * sustain + max(1 - dropout, 1e-6)) * 100
        print(f"    [{i}] {label:20s}  {steps/1e6:.1f}M steps  "
              f"lidar={lidar}m  dropout={dropout}  sustain={sustain}  "
              f"blind~{blind_pct:.0f}%  density={density}")
    print(f"{'='*68}\n")

    out_label = f"raster_blind_{tag}"
    ckpt_dir  = f"./models/checkpoints_{out_label}/"
    os.makedirs(ckpt_dir, exist_ok=True)

    # ── Decide which stages to run ────────────────────────────────────────────
    if only_stage is not None:
        stages_to_run = [only_stage]
        print(f"[*] Running SINGLE stage: {only_stage}")
    else:
        stages_to_run = list(range(len(CURRICULUM)))
        print(f"[*] Running ALL stages: {stages_to_run}")

    first_stage = stages_to_run[0]

    # ── Determine starting checkpoint ────────────────────────────────────────
    # Stage 0 always starts from the expanded M0.
    # Later stages start from the previous stage's final checkpoint.
    if first_stage == 0:
        load_path   = EXPANDED_BASE
        vecnorm_path = None
    else:
        prev_stage   = first_stage - 1
        load_path    = f"./models/{out_label}_stage{prev_stage}_final.zip"
        vecnorm_path = f"./models/vecnormalize_{out_label}_stage{prev_stage}.pkl"
        if not os.path.exists(load_path):
            print(f"[!] Stage {prev_stage} checkpoint not found: {load_path}")
            print(f"    Run stage {prev_stage} first.")
            return

    print(f"[*] Loading from: {load_path}")

    # ── Initial env (first stage params) ─────────────────────────────────────
    fi_steps, fi_dens, fi_drop, fi_sust, fi_lidar, _ = CURRICULUM[first_stage]
    env = make_env(comm_range, fi_lidar, fi_drop, fi_sust, fi_dens, use_shared,
                   vecnorm_load_path=vecnorm_path)
    model = PPO.load(load_path, env=env,
                     custom_objects={"policy_class": MAPPO_Policy_Raster}, device="auto")
    model.learning_rate = 3e-5   # lower LR for fine-tuning on top of M0
    model.ent_coef      = 0.020  # slightly higher entropy to explore shared-map usage

    cb = CheckpointCallback(save_freq=500_000, save_path=ckpt_dir, name_prefix=out_label)

    # ── Stage loop ────────────────────────────────────────────────────────────
    for i, (steps, density, dropout, sustain, lidar, label) in enumerate(CURRICULUM):
        if i not in stages_to_run:
            continue
        print(f"\n{'─'*68}")
        print(f"STAGE {i} — {label}")
        print(f"  steps={steps/1e6:.1f}M  density={density}  dropout={dropout}  "
              f"sustain={sustain}  lidar={lidar}m")
        blind_pct = dropout * sustain / (dropout * sustain + max(1 - dropout, 1e-6)) * 100
        print(f"  expected blind fraction: ~{blind_pct:.0f}% of steps per drone")
        if i == 0:
            print(f"  [Stage 0] ~{(1-dropout)*10:.0f} sighted drones per episode share obs[130:178].")
            print(f"  [Stage 0] ~{dropout*10:.0f} blind drones must learn from shared map.")
        print(f"{'─'*68}")

        if i > first_stage:
            # Save VecNormalize stats, close old env, rebuild with new stage params
            prev_norm_path = tempfile.mktemp(suffix=".pkl")
            env.save(prev_norm_path)
            env.close()
            env = make_env(comm_range, lidar, dropout, sustain, density, use_shared,
                           vecnorm_load_path=prev_norm_path)
            model.set_env(env)
        else:
            # First stage of this run: env already created above; set density
            env.env_method("set_target_density", density)

        model.learn(total_timesteps=steps, reset_num_timesteps=False,
                    callback=cb, progress_bar=True)

        # ── Stage-end checkpoint + reminder ──────────────────────────────────
        stage_ckpt = f"./models/{out_label}_stage{i}_final"
        model.save(stage_ckpt)
        env.save(f"./models/vecnormalize_{out_label}_stage{i}.pkl")
        print(f"\n[Stage {i} done] checkpoint: {stage_ckpt}.zip")

        if i == 0:
            print("\n" + "!"*68)
            print("STAGE 0 DONE — run feature importance BEFORE continuing:")
            print(f"  python Phase_CD/Collab_Perception/feature_importance_raster.py \\")
            print(f"    {stage_ckpt}.zip 12 {comm_range} 0.60 {'on' if use_shared else 'off'} 30")
            print("  SHARED_MAP drop should be >= 5 pp (was 0.60 pp before).")
            print("  If still < 3 pp -> increase sustain or dropout in Stage 0 and retrain.")
            print("!"*68)
        elif i == 2:
            print("\n" + "!"*68)
            print("STAGE 2 DONE — quick gate preview (30 maps):")
            print(f"  python Phase_CD/Collab_Perception/eval_raster.py \\")
            print(f"    {stage_ckpt}.zip 8 {comm_range} 0.20 {'on' if use_shared else 'off'} 30")
            print("!"*68)

    # ── Final save (only when Stage 3 is the last stage run) ─────────────────
    env.close()
    if stages_to_run[-1] == len(CURRICULUM) - 1:
        out_final = f"./models/{out_label}_final"
        model.save(out_final)
        print(f"[*] Final model saved: {out_final}.zip")

    print(f"\n{'='*68}")
    print(f"TRAINING COMPLETE  ->  {out_final}.zip")
    print(f"\nGATE EVAL (200 maps, lidar=8m, dropout=0.20):")
    print(f"  python Phase_CD/Collab_Perception/eval_raster.py \\")
    print(f"    {out_final}.zip 8 {comm_range} 0.20 {'on' if use_shared else 'off'} 200")
    print(f"\nFEATURE IMPORTANCE (final):")
    print(f"  python Phase_CD/Collab_Perception/feature_importance_raster.py \\")
    print(f"    {out_final}.zip 8 {comm_range} 0.20 {'on' if use_shared else 'off'} 50")
    print(f"{'='*68}\n")


if __name__ == "__main__":
    main()
