import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import torch
torch.set_num_threads(1)
import torch.nn as nn
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecEnv, VecNormalize
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback
from swarm_env_fixed import SwarmEnvFixed
from multiprocessing import Process, Pipe
import traceback

# ======================================================
#  PHASE B FIXED TRAINING
#  Density ceiling: 0.30 (validated by geometric sweep)
#  Stage 1 (0-5M):   density=0.15  — clean warm-up
#  Stage 2 (5-15M):  density=0.22  — medium difficulty
#  Stage 3 (15M+):   density=0.30  — full validated ceiling
# ======================================================

class CurriculumCallback(BaseCallback):
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.stage1_end = 5_000_000
        self.stage2_end = 15_000_000
        self._last_r_comm   = -1.0
        self._last_density  = -1.0

    def _on_step(self) -> bool:
        ts = self.num_timesteps

        if ts <= self.stage1_end:
            r_comm, r_sensor, density = 100.0, 100.0, 0.15
        elif ts <= self.stage2_end:
            frac = (ts - self.stage1_end) / (self.stage2_end - self.stage1_end)
            r_comm   = 100.0 - frac * 90.0   # 100 -> 10
            r_sensor = 100.0 - frac * 92.0   # 100 -> 8
            density  = 0.22
        else:
            r_comm, r_sensor, density = 10.0, 8.0, 0.30

        if abs(r_comm - self._last_r_comm) > 1e-4 or abs(density - self._last_density) > 1e-4:
            self.training_env.env_method("set_curriculum", r_sensor, r_comm)
            self.training_env.env_method("set_target_density", density)
            self._last_r_comm  = r_comm
            self._last_density = density

        if ts % 500_000 == 0:
            print(f"[Fixed] Step {ts}: R_comm={r_comm:.1f}m  R_sensor={r_sensor:.1f}m  Density={density:.2f}")
        return True


class MAPPO_Extractor(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        pi_layers = []; last_dim = 202
        for h in net_arch['pi']:
            pi_layers += [nn.Linear(last_dim, h), activation_fn()]; last_dim = h
        self.policy_net = nn.Sequential(*pi_layers)

        vf_layers = []; last_dim = 530
        for h in net_arch['vf']:
            vf_layers += [nn.Linear(last_dim, h), activation_fn()]; last_dim = h
        self.value_net = nn.Sequential(*vf_layers)

        self.latent_dim_pi = last_dim if net_arch['pi'] else 202
        self.latent_dim_vf = last_dim if net_arch['vf'] else 530
        # recalculate correctly
        last_pi = 202
        for h in net_arch['pi']: last_pi = h
        last_vf = 530
        for h in net_arch['vf']: last_vf = h
        self.latent_dim_pi = last_pi
        self.latent_dim_vf = last_vf

    def forward(self, features):
        return self.policy_net(features[:, :202]), self.value_net(features[:, 202:])
    def forward_actor(self, features):  return self.policy_net(features[:, :202])
    def forward_critic(self, features): return self.value_net(features[:, 202:])


class MAPPO_Policy(ActorCriticPolicy):
    def __init__(self, observation_space, action_space, lr_schedule, *args, **kwargs):
        super().__init__(observation_space, action_space, lr_schedule, *args, **kwargs)
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor(self.features_dim, self.net_arch, self.activation_fn)


def worker(remote, parent_remote):
    import torch; torch.set_num_threads(1)
    parent_remote.close()
    env = SwarmEnvFixed()
    n_drones = 10; ghost_obs = {}; total_obs_dim = 202 + 530
    last_r_sensor = -1.0; last_r_comm = -1.0
    try:
        while True:
            cmd, data = remote.recv()
            if cmd == 'step':
                actions = {f"drone_{i}": data[i] for i in range(n_drones) if f"drone_{i}" in env.agents}
                obs_d, rew_d, term_d, trunc_d, info_d = env.step(actions)
                all_done = not env.agents
                zero_obs = np.zeros(total_obs_dim, dtype=np.float32)
                if all_done:
                    for i in range(n_drones):
                        agent = f"drone_{i}"
                        if agent not in info_d: info_d[agent] = {}
                        info_d[agent]["terminal_observation"] = obs_d.get(agent, zero_obs)
                    new_obs_d, reset_info_d = env.reset(); ghost_obs.clear()
                    o_l = [new_obs_d.get(f"drone_{i}", zero_obs) for i in range(n_drones)]
                    r_l = [0.0]*10; d_l = [True]*10
                    i_l = [info_d.get(f"drone_{i}", {}) for i in range(n_drones)]
                    for idx, an in enumerate([f"drone_{j}" for j in range(n_drones)]):
                        i_l[idx].update(reset_info_d.get(an, {}))
                else:
                    o_l, r_l, d_l, i_l = [], [], [], []
                    for i in range(n_drones):
                        agent = f"drone_{i}"
                        if term_d.get(agent,False) or trunc_d.get(agent,False):
                            last = obs_d.get(agent, zero_obs)
                            ghost_obs[agent] = last
                            o_l.append(last); r_l.append(rew_d.get(agent,0.0)); d_l.append(False); i_l.append(info_d.get(agent,{}))
                        elif agent in ghost_obs:
                            o_l.append(ghost_obs[agent]); r_l.append(0.0); d_l.append(False); i_l.append({})
                        else:
                            o_l.append(obs_d.get(agent,zero_obs)); r_l.append(rew_d.get(agent,0.0)); d_l.append(False); i_l.append(info_d.get(agent,{}))
                remote.send((np.array(o_l,dtype=np.float32), np.array(r_l,dtype=np.float32), np.array(d_l,bool), i_l))

            elif cmd == 'reset':
                obs_d, info_d = env.reset(); ghost_obs.clear()
                remote.send(np.array([obs_d.get(f"drone_{i}", np.zeros(total_obs_dim)) for i in range(n_drones)], dtype=np.float32))
            elif cmd == 'set_curriculum':
                r_sen, r_com = data
                if abs(r_sen-last_r_sensor)>1e-4 or abs(r_com-last_r_comm)>1e-4:
                    env.set_curriculum(r_sen, r_com); last_r_sensor, last_r_comm = r_sen, r_com
                remote.send(True)
            elif cmd == 'set_target_density':
                env.set_target_density(data); remote.send(True)
            elif cmd == 'close': env.close(); break
            elif cmd == 'get_spaces': remote.send((env.observation_spaces["drone_0"], env.action_spaces["drone_0"]))
    except Exception as e:
        print(f"[WORKER CRASH] {e}"); traceback.print_exc(); remote.close()


class MultiProcessEnv(VecEnv):
    def __init__(self, n_workers):
        self.closed = False; self.n_workers = n_workers
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [Process(target=worker, args=(wr,r), daemon=True) for wr,r in zip(self.work_remotes, self.remotes)]
        for p in self.ps: p.start()
        for r in self.work_remotes: r.close()
        self.remotes[0].send(('get_spaces', None)); obs_space, act_space = self.remotes[0].recv()
        super().__init__(n_workers*10, obs_space, act_space)
    def step_async(self, actions):
        for i in range(self.n_workers): self.remotes[i].send(('step', actions[i*10:(i+1)*10]))
    def step_wait(self):
        o,r,d,i = zip(*[remote.recv() for remote in self.remotes])
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
    def get_attr(self, name, i=None): return [None]*self.num_envs
    def set_attr(self, name, val, i=None): pass
    def env_method(self, name, *a, i=None, **k):
        if name == "set_curriculum":     return self.set_curriculum(*a)
        if name == "set_target_density": return self.set_target_density(*a)
        return [None]*self.num_envs
    def env_is_wrapped(self, cls, i=None): return [False]*self.num_envs


class SpawnModeCallback(BaseCallback):
    """Logs success/collision/timeout rates separately for clustered vs scattered spawn."""
    def __init__(self, log_freq=100_000, verbose=0):
        super().__init__(verbose)
        self.log_freq = log_freq
        self._next_log = log_freq
        self._counts = {
            "clustered":  {"success": 0, "collision": 0, "timeout": 0},
            "scattered":  {"success": 0, "collision": 0, "timeout": 0},
        }

    def _on_step(self) -> bool:
        for info in self.locals.get("infos", []):
            cause = info.get("cause")
            mode  = info.get("spawn_mode")
            if cause and mode and mode in self._counts:
                self._counts[mode][cause] = self._counts[mode].get(cause, 0) + 1

        if self.num_timesteps >= self._next_log:
            self._next_log += self.log_freq
            for mode, counts in self._counts.items():
                total = sum(counts.values())
                if total == 0: continue
                sr = counts["success"] / total
                cr = counts["collision"] / total
                tr = counts["timeout"] / total
                self.logger.record(f"spawn/{mode}_success_rate", sr)
                self.logger.record(f"spawn/{mode}_collision_rate", cr)
                self.logger.record(f"spawn/{mode}_timeout_rate", tr)
                if self.verbose:
                    print(f"[{mode}] success={sr:.1%}  collision={cr:.1%}  timeout={tr:.1%}  (n={total})")
            self.logger.dump(self.num_timesteps)
        return True


class TqdmCallback(BaseCallback):
    def __init__(self, total_timesteps, verbose=0):
        super().__init__(verbose)
        self.total_timesteps = total_timesteps
        self.pbar = None

    def _on_training_start(self):
        from tqdm import tqdm
        self.pbar = tqdm(total=self.total_timesteps, unit="steps", dynamic_ncols=True,
                         bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]")

    def _on_step(self) -> bool:
        if self.pbar:
            self.pbar.update(self.training_env.num_envs)
        return True

    def _on_training_end(self):
        if self.pbar:
            self.pbar.close()


def run_training():
    num_cpu  = 6
    base_env = MultiProcessEnv(n_workers=num_cpu)
    env      = VecNormalize(base_env, norm_obs=False, norm_reward=True, clip_reward=100.0, gamma=0.99)

    policy_kwargs = dict(
        net_arch=dict(pi=[512,512,256], vf=[512,512,256]),
        activation_fn=nn.Tanh
    )

    TOTAL_STEPS = 50_000_000
    print("[Fixed] Training from scratch — 50M steps, 6 workers")
    model = PPO(MAPPO_Policy, env, verbose=0,
                learning_rate=3e-4, n_steps=2048, batch_size=4096,
                n_epochs=10, gamma=0.99, gae_lambda=0.95, ent_coef=0.03,
                policy_kwargs=policy_kwargs,
                tensorboard_log="./logs/fixed/")

    os.makedirs("./models/fixed/", exist_ok=True)
    checkpoint  = CheckpointCallback(save_freq=5_000_000, save_path='./models/fixed/', name_prefix='fixed_gen')
    curriculum  = CurriculumCallback()
    progress    = TqdmCallback(total_timesteps=TOTAL_STEPS)
    spawn_log   = SpawnModeCallback(log_freq=100_000, verbose=1)

    model.learn(total_timesteps=TOTAL_STEPS, callback=[checkpoint, curriculum, progress, spawn_log],
                reset_num_timesteps=True, progress_bar=False)

    model.save("./models/fixed_final")
    env.save("./models/fixed_normalize.pkl")
    env.close()
    print("[Fixed] Done.")


if __name__ == "__main__":
    run_training()
