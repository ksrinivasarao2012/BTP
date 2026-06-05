import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import torch
torch.set_num_threads(1)
import torch.nn as nn
import numpy as np
import sys
import traceback
from collections import deque
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecEnv, VecNormalize
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback
from stable_baselines3.common.policies import ActorCriticPolicy
from multiprocessing import Process, Pipe

# ============================================================
#  V20 SENSING ABLATION — 64-RAY LIDAR + MLP (NO MEMORY)
#  Purpose: Isolate sensing bottleneck vs memory bottleneck
#  Training from SCRATCH (new observation dimensions)
#  Environment: v19 geometric benchmark (FROZEN)
# ============================================================

TOTAL_TIMESTEPS   = 6_000_000
NUM_WORKERS       = 10
N_STEPS           = 1024
GAMMA             = 0.99
INITIAL_LR        = 3e-4   # Higher LR for training from scratch
FINAL_LR          = 1e-5
BATCH_SIZE        = 256     # Larger batch for higher-dim observations
N_EPOCHS          = 10
INITIAL_ENTROPY   = 0.02   # Higher initial entropy for exploration from scratch
FINAL_ENTROPY     = 0.001
CLIP_RANGE        = 0.2    # Standard clip for fresh training
CLIP_RANGE_VF     = 0.2
LOG_STD_MIN       = -3.0
LOG_STD_MAX       = 0.0
CHECKPOINT_FREQ   = 100_000  # More frequent checkpoints as recommended

CHECKPOINT_DIR    = r"d:\Swarm\BTP\models\v20_sensing_ablation_checkpoints"
FINAL_MODEL_PATH  = r"d:\Swarm\BTP\models\v20_SensingAblation_64ray.zip"
NORM_SAVE_PATH    = r"d:\Swarm\BTP\models\v20_SensingAblation_Normalize.pkl"

# v20 observation dimensions
ACTOR_DIM  = 366
CRITIC_DIM = 1960
TOTAL_DIM  = ACTOR_DIM + CRITIC_DIM + 10  # 2336


# ============================================================
#  CUSTOM MAPPO EXTRACTOR (Auto-detecting actor/critic dims)
# ============================================================
class MAPPO_Extractor_v20(nn.Module):
    """v20 actor-critic feature extractor with correct dimensions."""
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        self._pi_in = ACTOR_DIM   # 366
        pi_layers = []; last_dim_pi = self._pi_in
        for curr in net_arch['pi']:
            pi_layers.append(nn.Linear(last_dim_pi, curr))
            pi_layers.append(activation_fn())
            last_dim_pi = curr
        self.policy_net = nn.Sequential(*pi_layers)

        vf_in = ACTOR_DIM + CRITIC_DIM  # 2326
        vf_layers = []; last_dim_vf = vf_in
        for curr in net_arch['vf']:
            vf_layers.append(nn.Linear(last_dim_vf, curr))
            vf_layers.append(activation_fn())
            last_dim_vf = curr
        self.value_net = nn.Sequential(*vf_layers)

        self.latent_dim_pi = last_dim_pi
        self.latent_dim_vf = last_dim_vf

    def forward(self, features):
        pi_input = features[:, :self._pi_in]
        vf_input = features[:, :self._pi_in + CRITIC_DIM]
        return self.policy_net(pi_input), self.value_net(vf_input)

    def forward_actor(self, features):
        return self.policy_net(features[:, :self._pi_in])

    def forward_critic(self, features):
        return self.value_net(features[:, :self._pi_in + CRITIC_DIM])


class MAPPO_Policy_v20(ActorCriticPolicy):
    def __init__(self, observation_space, action_space, lr_schedule, **kwargs):
        super().__init__(
            observation_space, action_space, lr_schedule,
            net_arch={'pi': [256, 256], 'vf': [256, 256]},
            activation_fn=nn.Tanh,
            **kwargs
        )

    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_v20(
            self.features_dim,
            net_arch={'pi': [256, 256], 'vf': [256, 256]},
            activation_fn=nn.Tanh,
        )


# ============================================================
#  CALLBACKS
# ============================================================
class EntropyScheduleCallback(BaseCallback):
    def __init__(self, verbose=0):
        super().__init__(verbose)

    def _on_step(self) -> bool:
        progress_remaining = max(0.0, 1.0 - (self.num_timesteps / TOTAL_TIMESTEPS))
        self.model.ent_coef = FINAL_ENTROPY + (INITIAL_ENTROPY - FINAL_ENTROPY) * progress_remaining
        return True

def lr_schedule(progress_remaining: float) -> float:
    return FINAL_LR + (INITIAL_LR - FINAL_LR) * progress_remaining

class NaNCheckCallback(BaseCallback):
    def _on_step(self):
        for p in self.model.policy.parameters():
            if torch.isnan(p).any():
                print("NaN DETECTED IN PARAMETERS")
                return False
            if p.grad is not None:
                if torch.isnan(p.grad).any():
                    print("NaN DETECTED IN GRADIENTS")
                    return False
                if torch.isinf(p.grad).any():
                    print("INF DETECTED IN GRADIENTS")
                    return False
        return True

class MetricsCallback(BaseCallback):
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.successes = deque(maxlen=1000)
        self.collisions = deque(maxlen=1000)
        self.timeouts = deque(maxlen=1000)

    def _on_step(self) -> bool:
        for info in self.locals.get("infos", []):
            if "cause" in info:
                if info["cause"] == "success":
                    self.successes.append(1); self.collisions.append(0); self.timeouts.append(0)
                elif info["cause"] == "collision":
                    self.successes.append(0); self.collisions.append(1); self.timeouts.append(0)
                elif info["cause"] == "timeout":
                    self.successes.append(0); self.collisions.append(0); self.timeouts.append(1)

        if self.n_calls % 100 == 0 and len(self.successes) > 0:
            self.logger.record("metrics/success_rate", sum(self.successes)/len(self.successes))
            self.logger.record("metrics/collision_rate", sum(self.collisions)/len(self.collisions))
            self.logger.record("metrics/timeout_rate", sum(self.timeouts)/len(self.timeouts))

            infos = self.locals.get("infos", [])
            if len(infos) > 0 and "actual_density" in infos[0]:
                self.logger.record("metrics/actual_density", np.mean([i["actual_density"] for i in infos if "actual_density" in i]))
                self.logger.record("metrics/target_density", np.mean([i["target_density"] for i in infos if "target_density" in i]))
        return True

class LogStdClampCallback(BaseCallback):
    def __init__(self, log_std_min=LOG_STD_MIN, log_std_max=LOG_STD_MAX, verbose=0):
        super().__init__(verbose)
        self.log_std_min = log_std_min
        self.log_std_max = log_std_max

    def _on_step(self) -> bool:
        if hasattr(self.model.policy, "log_std"):
            with torch.no_grad():
                self.model.policy.log_std.data.clamp_(self.log_std_min, self.log_std_max)
        return True

class SaveVecNormalizeCallback(BaseCallback):
    def __init__(self, save_freq: int, save_path: str, verbose: int = 0):
        super().__init__(verbose)
        self.save_freq = save_freq
        self.save_path = save_path

    def _on_step(self) -> bool:
        if self.num_timesteps % self.save_freq == 0:
            vec_env = self.model.get_vec_normalize_env()
            if vec_env is not None:
                vec_env.save(self.save_path)
        return True

class CurriculumCallback_v20(BaseCallback):
    """Same geometric curriculum as v19 — environment is FROZEN."""
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self._last_r_comm = -1.0
        self._last_density = -1.0

    def _on_step(self) -> bool:
        ts = self.num_timesteps
        r_sensor = 100.0
        r_comm = 10.0  # Locked for benchmark specialization

        # Same True Geometric Curriculum as v19
        if ts < 1_000_000:
            prog = ts / 1_000_000.0
            density = 0.10 + (0.18 - 0.10) * prog
        elif ts < 2_000_000:
            prog = (ts - 1_000_000) / 1_000_000.0
            density = 0.18 + (0.26 - 0.18) * prog
        elif ts < 4_000_000:
            prog = (ts - 2_000_000) / 2_000_000.0
            density = 0.26 + (0.35 - 0.26) * prog
        else:
            density = 0.35

        if (abs(r_comm - self._last_r_comm) > 0.1 or abs(density - self._last_density) > 0.005):
            self.training_env.env_method("set_curriculum", r_sensor, r_comm)
            self.training_env.env_method("set_target_density", density)
            self._last_r_comm   = r_comm
            self._last_density  = density
            if self.verbose > 0:
                print(f"  [v20 Curriculum] Geometric Density = {density:.3f} | R_comm LOCKED = {r_comm:.1f}", flush=True)
        return True


# ============================================================
#  WORKER PROCESS
# ============================================================
def worker(remote, parent_remote):
    import torch; torch.set_num_threads(1)
    parent_remote.close()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from swarm_env_step_B5_v20_sensing_ablation import SwarmLidarEnv_v20_SensingAblation
    env = SwarmLidarEnv_v20_SensingAblation()
    N = 10
    total_dim = TOTAL_DIM
    ghost_obs = {}
    last_r_sensor = 100.0; last_r_comm = 100.0
    ep_rews = [0.0] * N
    ep_lens = [0] * N
    try:
        while True:
            cmd, data = remote.recv()
            if cmd == 'step':
                actions = {f"drone_{i}": data[i] for i in range(N) if f"drone_{i}" in env.agents}
                obs_d, rew_d, term_d, trunc_d, info_d = env.step(actions)
                zero_obs = np.zeros(total_dim, dtype=np.float32)
                all_done = not env.agents
                if all_done:
                    for i in range(N):
                        a = f"drone_{i}"
                        if a not in info_d: info_d[a] = {}
                        info_d[a]["terminal_observation"] = obs_d.get(a, zero_obs)
                        info_d[a]["episode"] = {"r": ep_rews[i] + rew_d.get(a, 0.0), "l": ep_lens[i] + 1}
                        ep_rews[i] = 0.0
                        ep_lens[i] = 0
                    new_obs_d, ri = env.reset()
                    ghost_obs.clear()
                    o_l = [new_obs_d.get(f"drone_{i}", zero_obs) for i in range(N)]
                    r_l, d_l = [0.0]*N, [True]*N
                    i_l = [info_d.get(f"drone_{i}", {}) for i in range(N)]
                    for idx, an in enumerate([f"drone_{j}" for j in range(N)]):
                        i_l[idx].update(ri.get(an, {}))
                else:
                    o_l, r_l, d_l, i_l = [], [], [], []
                    for i in range(N):
                        a = f"drone_{i}"
                        if term_d.get(a, False) or trunc_d.get(a, False):
                            last = obs_d.get(a, zero_obs)
                            ghost_obs[a] = last
                            r = rew_d.get(a, 0.0)
                            info_a = info_d.get(a, {})
                            info_a["episode"] = {"r": ep_rews[i] + r, "l": ep_lens[i] + 1}
                            ep_rews[i] = 0.0
                            ep_lens[i] = 0
                            o_l.append(last); r_l.append(r); d_l.append(False); i_l.append(info_a)
                        elif a in ghost_obs:
                            o_l.append(ghost_obs[a]); r_l.append(0.0); d_l.append(True); i_l.append({})
                            del ghost_obs[a]
                        elif a not in obs_d:
                            o_l.append(zero_obs); r_l.append(0.0); d_l.append(True); i_l.append({})
                        else:
                            r = rew_d.get(a, 0.0)
                            ep_rews[i] += r
                            ep_lens[i] += 1
                            o_l.append(obs_d[a]); r_l.append(r); d_l.append(False); i_l.append(info_d.get(a,{}))
                remote.send((np.array(o_l,dtype=np.float32), np.array(r_l,dtype=np.float32), np.array(d_l,bool), i_l))
            elif cmd == 'reset':
                obs_d, info_d = env.reset(); ghost_obs.clear()
                remote.send(np.array([obs_d.get(f"drone_{i}", np.zeros(total_dim)) for i in range(N)], dtype=np.float32))
            elif cmd == 'set_curriculum':
                r_sen, r_com = data
                if abs(r_sen - last_r_sensor) > 1e-4 or abs(r_com - last_r_comm) > 1e-4:
                    env.set_curriculum(r_sen, r_com)
                    last_r_sensor, last_r_comm = r_sen, r_com
                remote.send(True)
            elif cmd == 'set_target_density':
                env.set_target_density(data); remote.send(True)
            elif cmd == 'close':
                env.close(); break
            elif cmd == 'get_spaces':
                remote.send((env.observation_spaces["drone_0"], env.action_spaces["drone_0"]))
    except Exception as e:
        print(f"[WORKER CRASH] {e}"); traceback.print_exc()
        try: remote.send(('error', str(e)))
        except: pass
        remote.close()


class MultiProcessEnv_v20(VecEnv):
    def __init__(self, n_workers):
        self.closed = False; self.n_workers = n_workers
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [Process(target=worker, args=(wr, r), daemon=False)
                   for wr, r in zip(self.work_remotes, self.remotes)]
        for p in self.ps: p.start()
        for r in self.work_remotes: r.close()
        self.remotes[0].send(('get_spaces', None))
        obs_space, act_space = self.remotes[0].recv()
        super().__init__(n_workers * 10, obs_space, act_space)
    def step_async(self, actions):
        for i in range(self.n_workers): self.remotes[i].send(('step', actions[i*10:(i+1)*10]))
    def step_wait(self):
        for remote in self.remotes:
            if not remote.poll(timeout=90):
                raise RuntimeError("Worker timeout/deadlock")
        results = [remote.recv() for remote in self.remotes]
        for res in results:
            if isinstance(res, tuple) and len(res) >= 1 and isinstance(res[0], str) and res[0] == 'error':
                raise RuntimeError(f"Worker crashed: {res[1]}")
        o, r, d, i = zip(*results)
        return np.concatenate(o), np.concatenate(r), np.concatenate(d), [item for sub in i for item in sub]
    def reset(self):
        for r in self.remotes: r.send(('reset', None))
        for r in self.remotes:
            if not r.poll(timeout=90):
                raise RuntimeError("Worker timeout/deadlock during reset")
        results = [r.recv() for r in self.remotes]
        for res in results:
            if isinstance(res, tuple) and len(res) >= 1 and isinstance(res[0], str) and res[0] == 'error':
                raise RuntimeError(f"Worker crashed during reset: {res[1]}")
        return np.concatenate(results)
    def set_curriculum(self, r_sensor, r_comm):
        for r in self.remotes: r.send(('set_curriculum', (r_sensor, r_comm)))
        return [r.recv() for r in self.remotes]
    def set_target_density(self, density):
        for r in self.remotes: r.send(('set_target_density', density))
        return [r.recv() for r in self.remotes]
    def close(self):
        if self.closed: return
        for r in self.remotes: r.send(('close', None))
        for p in self.ps:
            p.join(timeout=10)
            if p.is_alive():
                p.terminate()
        self.closed = True
    def get_attr(self, name, i=None):    return [None]*self.num_envs
    def set_attr(self, name, val, i=None): pass
    def env_method(self, name, *a, i=None, **k):
        if name == "set_curriculum":     return self.set_curriculum(*a)
        if name == "set_target_density": return self.set_target_density(*a)
        return [None]*self.n_workers
    def env_is_wrapped(self, cls, i=None): return [False]*self.num_envs


# ============================================================
#  MAIN TRAINING
# ============================================================
def run_v20_sensing_ablation():
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(FINAL_MODEL_PATH), exist_ok=True)

    print("======================================================================")
    print("  V20 SENSING ABLATION — 64-RAY LIDAR + MLP (Training from Scratch)")
    print("======================================================================")
    print(f"  Total Steps    : {TOTAL_TIMESTEPS:,}")
    print(f"  Workers        : {NUM_WORKERS}")
    print(f"  Obs Dim        : {TOTAL_DIM} (Actor: {ACTOR_DIM}D | Critic: {CRITIC_DIM}D)")
    print(f"  LiDAR Sectors  : 64 (vs 16 in v19)")
    print(f"  Max Velocity   : 1.2 (vs 2.0 in v19)")
    print(f"  LR             : {INITIAL_LR} -> {FINAL_LR}")
    print(f"  Batch Size     : {BATCH_SIZE}")
    print(f"  Checkpoint Freq: {CHECKPOINT_FREQ:,}")
    print("======================================================================\n", flush=True)

    base_env = MultiProcessEnv_v20(n_workers=NUM_WORKERS)
    env = VecNormalize(base_env, norm_obs=True, norm_reward=True, clip_obs=10.0, clip_reward=10.0)

    print("[1/2] Creating fresh PPO model with MAPPO_Policy_v20...", flush=True)
    model = PPO(
        MAPPO_Policy_v20,
        env,
        learning_rate=lr_schedule,
        n_steps=N_STEPS,
        batch_size=BATCH_SIZE,
        n_epochs=N_EPOCHS,
        gamma=GAMMA,
        ent_coef=INITIAL_ENTROPY,
        clip_range=CLIP_RANGE,
        clip_range_vf=CLIP_RANGE_VF,
        max_grad_norm=0.5,
        verbose=1,
        tensorboard_log=os.path.join(CHECKPOINT_DIR, "tb_logs"),
    )

    checkpoint_cb = CheckpointCallback(
        save_freq=max(CHECKPOINT_FREQ // 100, 1),
        save_path=CHECKPOINT_DIR,
        name_prefix="v20_sensing_ckpt"
    )
    log_std_cb    = LogStdClampCallback()
    curriculum_cb = CurriculumCallback_v20()
    nan_check_cb  = NaNCheckCallback()
    save_vec_cb   = SaveVecNormalizeCallback(save_freq=CHECKPOINT_FREQ, save_path=NORM_SAVE_PATH)
    ent_schedule_cb = EntropyScheduleCallback()
    metrics_cb    = MetricsCallback()

    print("\n[2/2] Starting V20 Sensing Ablation Training...\n", flush=True)
    model.learn(
        total_timesteps=TOTAL_TIMESTEPS,
        callback=[checkpoint_cb, log_std_cb, curriculum_cb, nan_check_cb, save_vec_cb, ent_schedule_cb, metrics_cb],
        progress_bar=False,
        reset_num_timesteps=True,
    )

    print(f"\n[DONE] Saving final model to: {FINAL_MODEL_PATH}", flush=True)
    model.save(FINAL_MODEL_PATH)
    env.save(NORM_SAVE_PATH)
    env.close()
    print("[DONE] v20 Sensing Ablation Training complete!", flush=True)

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    run_v20_sensing_ablation()
