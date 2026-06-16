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

# ======================================================
#  PHASE B10 v14_8.0m: COMMUNICATION RANGE ENFORCED
#  Fine-tunes from B10 v14 (full communication) weights
#  in the new B10_8.0m environment (limited range).
# ======================================================

class MAPPO_Extractor_B5(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        pi_layers = []
        last_layer_dim_pi = 130
        for curr_layer_dim in net_arch['pi']:
            pi_layers.append(nn.Linear(last_layer_dim_pi, curr_layer_dim))
            pi_layers.append(activation_fn())
            last_layer_dim_pi = curr_layer_dim
        self.policy_net = nn.Sequential(*pi_layers)

        vf_layers = []
        last_layer_dim_vf = 520
        for curr_layer_dim in net_arch['vf']:
            vf_layers.append(nn.Linear(last_layer_dim_vf, curr_layer_dim))
            vf_layers.append(activation_fn())
            last_layer_dim_vf = curr_layer_dim
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi = last_layer_dim_pi
        self.latent_dim_vf = last_layer_dim_vf

    def forward(self, features): return self.policy_net(features[:, :130]), self.value_net(features[:, 130:])
    def forward_actor(self, features): return self.policy_net(features[:, :130])
    def forward_critic(self, features): return self.value_net(features[:, 130:])

class MAPPO_Policy_B5(ActorCriticPolicy):
    def __init__(self, observation_space, action_space, lr_schedule, *args, **kwargs):
        super().__init__(observation_space, action_space, lr_schedule, *args, **kwargs)
    def _build_mlp_extractor(self) -> None:
        self.mlp_extractor = MAPPO_Extractor_B5(self.features_dim, self.net_arch, self.activation_fn)

# -----------------------------------------------------------
# Subprocess Worker – uses SwarmLidarEnv_StepB10_8_0m
# -----------------------------------------------------------
def worker(remote, parent_remote, density, drone_radius, safety_radius):
    import os
    os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
    os.environ["OMP_NUM_THREADS"] = "1"
    parent_remote.close()
    env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density)
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
        remote.close()

class MultiProcessPZEnv_B10_8_0m(VecEnv):
    def __init__(self, n_workers, density=0.20):
        self.closed = False
        self.n_workers = n_workers
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [Process(target=worker, args=(work_remote, remote, density, 0.15, 0.19), daemon=True) for (work_remote, remote) in zip(self.work_remotes, self.remotes)]
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
def run_v14_8_0m_training():
    num_cpu = 10
    v14_model_path = "models/apex_ultra_glide_v14_final.zip"

    # Robust path resolution (both paths hold the identical model file)
    possible_paths = [
        "models/apex_ultra_glide_v14_final.zip",
        os.path.join("v10_IEEE_Final", "v14_Best_Model_Archive", "model", "apex_ultra_glide_v14_final.zip"),
        "../../models/apex_ultra_glide_v14_final.zip",
        "../../../models/apex_ultra_glide_v14_final.zip",
        os.path.join(os.path.dirname(__file__), "../../models/apex_ultra_glide_v14_final.zip"),
        os.path.join(os.path.dirname(__file__), "../../../models/apex_ultra_glide_v14_final.zip")
    ]
    for p in possible_paths:
        if os.path.exists(p) or os.path.exists(p + ".zip"):
            v14_model_path = p
            break

    print(f"PHASE B10 v14_8.0m: Communication Range Enforced (8.0 meters)")
    print(f"  -> Loading pre-trained v14 weights from: {v14_model_path}")

    # Create the new B10_8.0m environment (with communication range enforced)
    # Start at density 0.30 to match V14's curriculum exactly
    base_env = MultiProcessPZEnv_B10_8_0m(n_workers=num_cpu, density=0.30)
    env = VecNormalize(base_env, norm_obs=False, norm_reward=True, clip_reward=10.0)

    # Load pre-trained v14 model and attach to the new environment
    model = PPO.load(
        v14_model_path,
        env=env,
        custom_objects={
            "policy_class": MAPPO_Policy_B5,
            "tensorboard_log": "./logs/"
        },
        device="auto"
    )
    # Lower the learning rate for fine-tuning (policy adapts to limited communication)
    model.learning_rate = 5e-5
    model.ent_coef = 0.015

    print(f"  -> v14 weights loaded successfully. Fine-tuning in B10_8.0m environment...")
    print(f"  -> TensorBoard logging initialized to ./logs/")
    print(f"  -> Communication range: 8.0 meters (enforced)")

    # Curriculum: IDENTICAL to V14 (2M @ 0.30, 3M @ 0.35).
    # Matching the curriculum exactly means communication range is the ONLY
    # difference between V14 and V14_8.0m -> clean causal comparison.
    curriculum = [
        (2_000_000, 0.30),   # Phase 1: Adaptation & Stabilization
        (3_000_000, 0.35),   # Phase 2: Hard high-density detour mastery
    ]

    os.makedirs("./models/checkpoints_b10v14_8_0m/", exist_ok=True)
    checkpoint_callback = CheckpointCallback(
        save_freq=500_000,
        save_path='./models/checkpoints_b10v14_8_0m/',
        name_prefix='b10v14_8_0m'
    )

    for steps, density in curriculum:
        print(f"\nPHASE: Density={density} | Steps={steps/1e6:.1f}M | Communication Range=8.0m")
        env.env_method("set_target_density", density)
        model.learn(total_timesteps=steps, reset_num_timesteps=False, callback=checkpoint_callback, progress_bar=True)
        model.save(f"./models/apex_ultra_glide_v14_8_0m_mid_{density}")

    model.save("./models/apex_ultra_glide_v14_8_0m_final")
    env.save("./models/vecnormalize_glide_v14_8_0m_final.pkl")
    env.close()
    print(f"\nPhase B10 v14_8.0m Training Complete (5M fine-tune steps, curriculum 0.30->0.35, 8.0m range enforced).")
    print(f"Models saved:")
    print(f"  - Policy: ./models/apex_ultra_glide_v14_8_0m_final.zip")
    print(f"  - VecNormalize: ./models/vecnormalize_glide_v14_8_0m_final.pkl")

if __name__ == "__main__":
    run_v14_8_0m_training()
