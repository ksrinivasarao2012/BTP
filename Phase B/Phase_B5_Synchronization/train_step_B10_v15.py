import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import torch
import torch.nn as nn
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecEnv, VecNormalize
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.callbacks import CheckpointCallback, BaseCallback
from swarm_env_step_B10 import SwarmLidarEnv_StepB10
from multiprocessing import Process, Pipe

# ======================================================
#  PHASE B10 v15: Widened Network + Reward-Hardened Training
#  Trains from scratch with 256-128 architecture for
#  complex spatial reasoning in dense obstacle fields.
# ======================================================

class MAPPO_Extractor_v15(nn.Module):
    """Wider CTDE feature extractor: 256-128 for both actor and critic."""
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        # Actor: processes 130-dim local observation
        pi_layers = []
        last_layer_dim_pi = 130
        for curr_layer_dim in net_arch['pi']:
            pi_layers.append(nn.Linear(last_layer_dim_pi, curr_layer_dim))
            pi_layers.append(activation_fn())
            last_layer_dim_pi = curr_layer_dim
        self.policy_net = nn.Sequential(*pi_layers)

        # Critic: processes 520-dim global state
        vf_layers = []
        last_layer_dim_vf = 520
        for curr_layer_dim in net_arch['vf']:
            vf_layers.append(nn.Linear(last_layer_dim_vf, curr_layer_dim))
            vf_layers.append(activation_fn())
            last_layer_dim_vf = curr_layer_dim
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi = last_layer_dim_pi
        self.latent_dim_vf = last_layer_dim_vf

    def forward(self, features):
        return self.policy_net(features[:, :130]), self.value_net(features[:, 130:])
    def forward_actor(self, features):
        return self.policy_net(features[:, :130])
    def forward_critic(self, features):
        return self.value_net(features[:, 130:])


class MAPPO_Policy_v15(ActorCriticPolicy):
    """Custom MAPPO policy with 256-128 architecture."""
    def __init__(self, observation_space, action_space, lr_schedule, *args, **kwargs):
        # Override net_arch to use wider layers
        kwargs["net_arch"] = dict(pi=[256, 128], vf=[256, 128])
        super().__init__(observation_space, action_space, lr_schedule, *args, **kwargs)

    def _build_mlp_extractor(self) -> None:
        self.mlp_extractor = MAPPO_Extractor_v15(
            self.features_dim, self.net_arch, self.activation_fn
        )


class LogStdClampCallback(BaseCallback):
    """Clamps log_std to [-2.0, 1.0] after every update to prevent exploration divergence."""
    def __init__(self, min_log_std=-2.0, max_log_std=1.0, verbose=0):
        super().__init__(verbose)
        self.min_log_std = min_log_std
        self.max_log_std = max_log_std

    def _on_step(self) -> bool:
        with torch.no_grad():
            log_std = self.model.policy.log_std
            log_std.clamp_(self.min_log_std, self.max_log_std)
        return True


# -----------------------------------------------------------
# Subprocess Worker – uses SwarmLidarEnv_StepB10
# -----------------------------------------------------------
def worker(remote, parent_remote, density, drone_radius, safety_radius):
    import os
    os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
    os.environ["OMP_NUM_THREADS"] = "1"
    parent_remote.close()
    env = SwarmLidarEnv_StepB10(render_mode=None, target_density=density)
    n_drones = 10
    ghost_obs = {}
    try:
        while True:
            cmd, data = remote.recv()
            if cmd == 'step':
                actions = {f"drone_{i}": data[i] for i in range(n_drones) if f"drone_{i}" in env.agents}
                obs_d, rew_d, term_d, trunc_d, info_d = env.step(actions)
                zero_obs = np.zeros(130+520, dtype=np.float32)
                obs_list, rew_list, done_list, info_list = [], [], [], []
                all_done = not env.agents
                for i in range(n_drones):
                    agent = f"drone_{i}"
                    if all_done: pass
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
                remote.send(np.array([obs_d.get(f"drone_{i}", np.zeros(130+520)) for i in range(n_drones)], dtype=np.float32))
            elif cmd == 'close': env.close(); break
            elif cmd == 'set_density': env.set_target_density(data)
            elif cmd == 'get_spaces': remote.send((env.observation_spaces["drone_0"], env.action_spaces["drone_0"]))
    except Exception as e:
        print(f"Worker error: {e}", flush=True)
        remote.close()


class MultiProcessPZEnv_v15(VecEnv):
    def __init__(self, n_workers, density=0.20):
        self.closed = False
        self.n_workers = n_workers
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [Process(target=worker, args=(work_remote, remote, density, 0.15, 0.19), daemon=True)
                    for (work_remote, remote) in zip(self.work_remotes, self.remotes)]
        for p in self.ps: p.start()
        for remote in self.work_remotes: remote.close()
        self.remotes[0].send(('get_spaces', None))
        obs_space, act_space = self.remotes[0].recv()
        super().__init__(n_workers * 10, obs_space, act_space)

    def step_async(self, actions):
        for i in range(self.n_workers): self.remotes[i].send(('step', actions[i*10:(i+1)*10]))
    def step_wait(self):
        obs, rews, dones, infos = zip(*[remote.recv() for remote in self.remotes])
        return np.concatenate(obs), np.concatenate(rews), np.concatenate(dones), [i for sub in infos for i in sub]
    def reset(self):
        for remote in self.remotes: remote.send(('reset', None))
        return np.concatenate([remote.recv() for remote in self.remotes])
    def close(self):
        if self.closed: return
        for remote in self.remotes: remote.send(('close', None))
        for p in self.ps: p.join()
        self.closed = True
    def set_density(self, density):
        for remote in self.remotes: remote.send(('set_density', density))
    def get_attr(self, attr_name, indices=None): return [None] * self.num_envs
    def set_attr(self, attr_name, value, indices=None): pass
    def env_method(self, method_name, *method_args, indices=None, **method_kwargs):
        if method_name == "set_target_density": self.set_density(method_args[0])
    def env_is_wrapped(self, wrapper_class, indices=None): return [False] * self.num_envs


# -----------------------------------------------------------
# Training Entry Point
# -----------------------------------------------------------
def run_v15_training():
    num_cpu = 10

    print("=" * 70)
    print("  PHASE B10 v15: Widened Network Training (256-128)")
    print("  Training from scratch with reward-hardened environment")
    print("=" * 70)

    # Create the B10 environment (starts at low density)
    base_env = MultiProcessPZEnv_v15(n_workers=num_cpu, density=0.20)
    env = VecNormalize(base_env, norm_obs=False, norm_reward=True, clip_reward=10.0)

    # Create fresh PPO model with wider network
    model = PPO(
        policy=MAPPO_Policy_v15,
        env=env,
        learning_rate=3e-4,
        n_steps=4096,
        batch_size=512,
        n_epochs=5,
        gamma=0.995,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        verbose=1,
        device="auto",
    )

    # Initialize log_std to 0.0 (std=1.0) for controlled exploration
    with torch.no_grad():
        model.policy.log_std.fill_(0.0)

    print(f"  Network: Actor 130->256->128->2 | Critic 520->256->128->1")
    print(f"  log_std initialized to 0.0 (std=1.0)")
    total_params = sum(p.numel() for p in model.policy.parameters())
    print(f"  Total parameters: {total_params:,}")

    os.makedirs("./models/checkpoints_b10v15/", exist_ok=True)
    checkpoint_callback = CheckpointCallback(
        save_freq=500_000,
        save_path='./models/checkpoints_b10v15/',
        name_prefix='b10v15'
    )
    log_std_clamp = LogStdClampCallback(min_log_std=-2.0, max_log_std=1.0)

    # 3-Phase Curriculum
    curriculum = [
        (5_000_000, 0.20, 3e-4),   # Phase 1: Basic navigation
        (5_000_000, 0.30, 1.5e-4), # Phase 2: Complex detours
        (5_000_000, 0.35, 5e-5),   # Phase 3: Target density mastery
    ]

    for phase_idx, (steps, density, lr) in enumerate(curriculum, 1):
        print(f"\n{'='*50}")
        print(f"  PHASE {phase_idx}/3: Density={density} | Steps={steps/1e6:.0f}M | LR={lr}")
        print(f"{'='*50}")
        env.env_method("set_target_density", density)
        model.learning_rate = lr
        # Decay entropy coefficient across phases
        model.ent_coef = max(0.002, 0.01 * (0.5 ** (phase_idx - 1)))
        print(f"  ent_coef={model.ent_coef}")
        model.learn(
            total_timesteps=steps,
            reset_num_timesteps=False,
            callback=[checkpoint_callback, log_std_clamp],
        )
        model.save(f"./models/apex_v15_wide_phase{phase_idx}")
        print(f"  Phase {phase_idx} checkpoint saved.")

    # Save final model
    model.save("./models/apex_v15_wide_final")
    env.save("./models/vecnormalize_v15_wide_final.pkl")
    env.close()

    # Print final log_std
    final_log_std = model.policy.log_std.detach().cpu().numpy()
    print(f"\n{'='*70}")
    print(f"  TRAINING COMPLETE: 15M steps across 3 phases")
    print(f"  Final log_std: {final_log_std} (std={np.exp(final_log_std)})")
    print(f"  Model saved: ./models/apex_v15_wide_final.zip")
    print(f"{'='*70}")


if __name__ == "__main__":
    run_v15_training()
