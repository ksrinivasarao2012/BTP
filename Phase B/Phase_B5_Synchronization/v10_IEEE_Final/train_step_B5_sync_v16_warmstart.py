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
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecEnv, VecNormalize
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback
from multiprocessing import Process, Pipe

# ============================================================
#  V16 WARMSTART FROM V14 — HYBRID BEST-OF-BOTH-WORLDS
#  We use the massive [512,512,256] network from v14 and 
#  load its exact weights, bypassing 15M steps of learning!
# ============================================================

TOTAL_TIMESTEPS   = 2_000_000
NUM_WORKERS       = 10
N_STEPS           = 2048
BATCH_SIZE        = 512
N_EPOCHS          = 10
LEARNING_RATE     = 3e-5         # Lower LR because we are fine-tuning v14
ENT_COEF          = 0.005        # Low entropy to preserve v14 collision avoidance
CLIP_RANGE        = 0.10
GAMMA             = 0.99
GAE_LAMBDA        = 0.95
MAX_GRAD_NORM     = 0.5
LOG_STD_MIN       = -2.5
LOG_STD_MAX       = 0.0
CHECKPOINT_FREQ   = 250_000

WARM_INIT_MODEL   = r"d:\Swarm\BTP\models\apex_ultra_glide_v14_final.zip"
CHECKPOINT_DIR    = r"d:\Swarm\BTP\models\v16_checkpoints"
FINAL_MODEL_PATH  = r"d:\Swarm\BTP\models\v16_Master_Final.zip"
NORM_SAVE_PATH    = r"d:\Swarm\BTP\models\v16_Master_Normalize.pkl"

class MAPPO_Extractor_v16(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        pi_layers = []; last_dim_pi = 202
        for curr in net_arch['pi']:
            pi_layers.append(nn.Linear(last_dim_pi, curr))
            pi_layers.append(activation_fn())
            last_dim_pi = curr
        self.policy_net = nn.Sequential(*pi_layers)
        
        vf_layers = []; last_dim_vf = 530
        for curr in net_arch['vf']:
            vf_layers.append(nn.Linear(last_dim_vf, curr))
            vf_layers.append(activation_fn())
            last_dim_vf = curr
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi = last_dim_pi
        self.latent_dim_vf = last_dim_vf

    def forward(self, f):      return self.policy_net(f[:,:202]), self.value_net(f[:,202:])
    def forward_actor(self, f):  return self.policy_net(f[:,:202])
    def forward_critic(self, f): return self.value_net(f[:,202:])

class MAPPO_Policy_v16(ActorCriticPolicy):
    def __init__(self, obs_sp, act_sp, lr_schedule, *a, **kw):
        super().__init__(obs_sp, act_sp, lr_schedule, *a, **kw)
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_v16(
            self.features_dim, self.net_arch, self.activation_fn
        )

def warm_init_from_v14(model, v14_path):
    print(f"\n  [WarmInit] Loading EXACT v14 weights from: {v14_path}", flush=True)
    import zipfile, io
    with zipfile.ZipFile(v14_path) as z:
        with z.open("policy.pth") as f:
            v14_params = torch.load(io.BytesIO(f.read()), map_location="cpu", weights_only=True)

    v16_sd = model.policy.state_dict()
    transferred, skipped = 0, 0

    for k, v14_tensor in v14_params.items():
        if k not in v16_sd:
            skipped += 1
            continue
        # Ensure shape match
        if v16_sd[k].shape == v14_tensor.shape:
            v16_sd[k] = v14_tensor.clone()
            transferred += 1
        else:
            print(f"Shape mismatch on {k}: {v16_sd[k].shape} vs {v14_tensor.shape}")

    model.policy.load_state_dict(v16_sd)
    print(f"  [WarmInit] Transferred {transferred} exact tensors from v14!\n", flush=True)

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

class CurriculumCallback_v16(BaseCallback):
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self._last_r_comm = -1.0
        self._last_density = -1.0

    def _on_step(self) -> bool:
        ts = self.num_timesteps
        density = 0.35 # Directly lock to 0.35 since v14 is already a master of dodging
        r_comm, r_sensor = 10.0, 8.0

        if (abs(r_comm - self._last_r_comm) > 0.5 or abs(density - self._last_density) > 0.005):
            self.training_env.env_method("set_curriculum", r_sensor, r_comm)
            self.training_env.env_method("set_target_density", density)
            self._last_r_comm   = r_comm
            self._last_density  = density
            print(f"  [Curriculum] Step {self.num_timesteps:,}: Density locked at 0.35", flush=True)
        return True

def worker(remote, parent_remote):
    import torch; torch.set_num_threads(1)
    parent_remote.close()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from swarm_env_step_B5_v16_master import SwarmLidarEnv_v16_Final
    env = SwarmLidarEnv_v16_Final()
    N = 10
    total_dim = 202 + 530
    ghost_obs = {}
    last_r_sensor, last_r_comm = -1.0, -1.0

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
                            o_l.append(last); r_l.append(rew_d.get(a,0.0)); d_l.append(False); i_l.append(info_d.get(a,{}))
                        elif a in ghost_obs:
                            o_l.append(ghost_obs[a]); r_l.append(0.0); d_l.append(False); i_l.append({})
                        else:
                            o_l.append(obs_d.get(a,zero_obs)); r_l.append(rew_d.get(a,0.0)); d_l.append(False); i_l.append(info_d.get(a,{}))
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
        print(f"[WORKER CRASH] {e}"); traceback.print_exc(); remote.close()

class MultiProcessEnv_v16(VecEnv):
    def __init__(self, n_workers):
        self.closed = False; self.n_workers = n_workers
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [Process(target=worker, args=(wr, r), daemon=True)
                   for wr, r in zip(self.work_remotes, self.remotes)]
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
    def set_curriculum(self, r_sensor, r_comm):
        for r in self.remotes: r.send(('set_curriculum', (r_sensor, r_comm)))
        return [r.recv() for r in self.remotes]
    def set_target_density(self, density):
        for r in self.remotes: r.send(('set_target_density', density))
        return [r.recv() for r in self.remotes]
    def close(self):
        if self.closed: return
        for r in self.remotes: r.send(('close', None))
        for p in self.ps: p.join()
        self.closed = True
    def get_attr(self, name, i=None):    return [None]*self.num_envs
    def set_attr(self, name, val, i=None): pass
    def env_method(self, name, *a, i=None, **k):
        if name == "set_curriculum":     return self.set_curriculum(*a)
        if name == "set_target_density": return self.set_target_density(*a)
        return [None]*self.num_envs
    def env_is_wrapped(self, cls, i=None): return [False]*self.num_envs

def run_v16_training():
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(FINAL_MODEL_PATH), exist_ok=True)

    print("\n" + "="*70, flush=True)
    print("  V16 WARMSTART FROM V14 — HYBRID BEST-OF-BOTH-WORLDS", flush=True)
    print("="*70, flush=True)
    print(f"  Total Steps    : {TOTAL_TIMESTEPS:,}", flush=True)
    print(f"  Workers        : {NUM_WORKERS}", flush=True)
    print(f"  LR             : {LEARNING_RATE}", flush=True)
    print(f"  Entropy Coef   : {ENT_COEF}", flush=True)
    print("="*70 + "\n", flush=True)

    base_env = MultiProcessEnv_v16(n_workers=NUM_WORKERS)
    env = VecNormalize(
        base_env,
        norm_obs=False,
        norm_reward=True,
        clip_reward=100.0,
        gamma=GAMMA
    )

    # EXACT V14 ARCHITECTURE
    policy_kwargs = dict(
        net_arch=dict(pi=[512, 512, 256], vf=[1024, 512, 256]),
        activation_fn=nn.Tanh
    )

    print("[1/2] Building MASSIVE [512,512,256] PPO model...", flush=True)
    model = PPO(
        MAPPO_Policy_v16,
        env,
        verbose=0,
        learning_rate=LEARNING_RATE,
        n_steps=N_STEPS,
        batch_size=BATCH_SIZE,
        n_epochs=N_EPOCHS,
        gamma=GAMMA,
        gae_lambda=GAE_LAMBDA,
        ent_coef=ENT_COEF,
        clip_range=CLIP_RANGE,
        max_grad_norm=MAX_GRAD_NORM,
        policy_kwargs=policy_kwargs,
        tensorboard_log=os.path.join(CHECKPOINT_DIR, "tb_logs"),
    )

    if os.path.exists(WARM_INIT_MODEL):
        warm_init_from_v14(model, WARM_INIT_MODEL)
    else:
        print(f"[ERROR] v14 model not found at {WARM_INIT_MODEL}", flush=True)
        sys.exit(1)

    checkpoint_cb = CheckpointCallback(
        save_freq=CHECKPOINT_FREQ,
        save_path=CHECKPOINT_DIR,
        name_prefix="v16_master",
        verbose=1
    )
    log_std_cb   = LogStdClampCallback()
    curriculum_cb = CurriculumCallback_v16()

    print("[2/2] Starting V16 Warmstart Fine-Tuning...\n", flush=True)
    model.learn(
        total_timesteps=TOTAL_TIMESTEPS,
        callback=[checkpoint_cb, log_std_cb, curriculum_cb],
        progress_bar=False,
        reset_num_timesteps=True,
    )

    print(f"\n[DONE] Saving final model to: {FINAL_MODEL_PATH}", flush=True)
    model.save(FINAL_MODEL_PATH)
    env.save(NORM_SAVE_PATH)
    env.close()
    print("[DONE] Training complete!", flush=True)

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    run_v16_training()
