"""
LOCAL-BLOCK CTDE leak test for M0 (apex_ultra_glide_v14_comm8_lidar_final).

The earlier leakage test only zeroed the GLOBAL/critic block obs[130:650] and showed the action was
invariant -> proves the actor ignores the critic block. But the B10 audit's leakage is INSIDE the actor's
own local block obs[0:130]: communicated neighbor VELOCITIES and neighbor STAGNATION counters. M0 was
TRANSFER-LEARNED from a model (swarm_env_step_B10.py) that fed those fields UNGATED (full omniscience) +
ground-truth congestion. So we must check: does M0's ACTOR actually USE those fields at execution?

Method: collect a large batch of real honest-drone observations (no traitors), get the deterministic
action for each, then re-query the action with specific fields ZEROED. If the action is ~invariant to a
field -> the actor doesn't use it (CTDE-clean for that field). If it changes -> the actor depends on it.

Field layout in obs[0:130]:
  obs_core      [0:54]   = vel[0:2] goaldir[2:4] dist[4] yaw[5] LiDAR[6:54]
  obs_neighbors [54:99]  = 9 neighbors x {rel_pos(2), norm_vel(2), is_active(1)}  -> neighbor k at 54+5k
  congestion    [99]
  sync_features [100:120]= 5 slots x {rel_vel(2), stagnation(1), pad(1)}          -> slot m at 100+4m
  trajectory    [120:130]
  (global/critic[130:650])

Ablations:
  NEIGH_VEL  : zero norm_vel of all 9 neighbors            (audit Violation #1)
  STAGNATION : zero stagnation of all 5 sync slots         (audit Violation #3)
  SYNC_RELVEL: zero rel_vel of all 5 sync slots            (communicated relative velocity)
  GLOBAL     : zero obs[130:650]                            (reproduce prior test; expect ~0 change)
  LIDAR      : zero obs[6:54]                               (SANITY: expect LARGE change -> test is sensitive)

Run: & "C:\\Users\\Srinivasa\\miniconda3\\envs\\swarm_rl\\python.exe" leak_test_local.py
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import sys
import numpy as np
import torch
import torch.nn as nn
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy
from swarm_env_step_B10_8_0m import SwarmLidarEnv_StepB10_8_0m

# args: [model_path] [congestion_mode]  -- congestion_mode should MATCH how the model was trained
#   clean M0:  python leak_test_local.py models/apex_ultra_glide_v14_comm8_lidar_final.zip lidar
#   v14_8_0m:  python leak_test_local.py models/apex_ultra_glide_v14_8_0m_final.zip env
MODEL = sys.argv[1] if len(sys.argv) > 1 else "models/apex_ultra_glide_v14_comm8_lidar_final.zip"
CONGESTION_MODE = sys.argv[2] if len(sys.argv) > 2 else "lidar"
COMM = 8.0
N_OBS_TARGET = 4000          # collect this many honest-drone obs vectors
DENSITIES = [0.20, 0.30]


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


def field_indices():
    neigh_vel, stag, sync_relvel = [], [], []
    for k in range(9):
        base = 54 + 5 * k
        neigh_vel += [base + 2, base + 3]          # norm_vel (2)
    for m in range(5):
        base = 100 + 4 * m
        sync_relvel += [base + 0, base + 1]        # rel_vel (2)
        stag += [base + 2]                         # stagnation (1)
    return {
        "NEIGH_VEL":   np.array(neigh_vel),
        "STAGNATION":  np.array(stag),
        "SYNC_RELVEL": np.array(sync_relvel),
        "CONGESTION":  np.array([99]),              # neighbor-count field (ground-truth if mode="env")
        "GLOBAL":      np.arange(130, 650),
        "LIDAR":       np.arange(6, 54),            # sanity sensitivity check
    }


def collect_obs(model):
    obs_list = []
    for density in DENSITIES:
        env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density,
                                         communication_range=COMM, congestion_mode=CONGESTION_MODE)
        env.traitor_indices = set(); env.traitor_behavior = "navigate"; env.deception_mode = "none"
        amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
        map_idx = 0
        while len(obs_list) < N_OBS_TARGET // len(DENSITIES) * (DENSITIES.index(density) + 1):
            attempts = 0
            while True:
                seed = 700_000_000 + int(density * 100) * 10_000 + map_idx + attempts * 5_000
                obs_dict, _ = env.reset(seed=seed, options={"spawn_mode": "clustered"})
                if all(env._is_map_solvable(start_pos=env.positions[amap[a]]) for a in env.possible_agents):
                    break
                attempts += 1
            map_idx += 1
            finished = set(); steps = 0
            while env.agents and steps < 400:
                active = [a for a in obs_dict.keys() if a not in finished]
                if not active:
                    break
                obs_batch = np.array([obs_dict[a] for a in active])
                # sub-sample obs to diversify (every step adds active drones' obs)
                for v in obs_batch:
                    obs_list.append(v.copy())
                act, _ = model.predict(obs_batch, deterministic=True)
                action = {a: act[k] for k, a in enumerate(active)}
                obs_dict, _, terms, truncs, _ = env.step(action)
                for a in active:
                    if terms.get(a, False) or truncs.get(a, False):
                        finished.add(a)
                steps += 1
                if len(obs_list) >= N_OBS_TARGET:
                    break
        env.close()
        if len(obs_list) >= N_OBS_TARGET:
            break
    return np.array(obs_list[:N_OBS_TARGET], dtype=np.float32)


def actions_for(model, obs):
    act, _ = model.predict(obs, deterministic=True)
    return np.asarray(act, dtype=np.float32)


def main():
    if not os.path.exists(MODEL):
        print(f"[!] model not found: {MODEL}"); return
    print(f"[*] LOCAL-BLOCK LEAK TEST | model={MODEL} | comm={COMM}m | congestion={CONGESTION_MODE}")
    model = PPO.load(MODEL, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    print("[*] collecting observations ...")
    obs = collect_obs(model)
    print(f"[*] collected {len(obs)} obs vectors (dim {obs.shape[1]})")

    base_act = actions_for(model, obs)
    act_scale = float(np.mean(np.linalg.norm(base_act, axis=1)) + 1e-9)
    fields = field_indices()

    print("\n" + "=" * 78)
    print(f"{'ABLATION':<14}{'mean |d_action|':>16}{'max |d_action|':>16}{'rel. to action':>18}")
    print("-" * 78)
    rows = []
    for name, idx in fields.items():
        ob2 = obs.copy()
        ob2[:, idx] = 0.0
        act2 = actions_for(model, ob2)
        delta = np.linalg.norm(act2 - base_act, axis=1)
        mean_d, max_d = float(delta.mean()), float(delta.max())
        rel = mean_d / act_scale
        rows.append((name, mean_d, max_d, rel))
        print(f"{name:<14}{mean_d:>16.5f}{max_d:>16.5f}{rel:>17.1%}")
    print("=" * 78)
    print("INTERPRETATION:")
    print("  LIDAR delta should be LARGE  -> confirms the test is sensitive (if ~0, test is broken).")
    print("  GLOBAL delta should be ~0     -> reproduces the prior critic-block result.")
    print("  NEIGH_VEL / STAGNATION / SYNC_RELVEL:")
    print("    ~0           -> actor IGNORES the field -> CTDE-CLEAN for it (transfer leak did NOT persist).")
    print("    non-trivial  -> actor DEPENDS on communicated velocity/stagnation -> MUST document comm model")
    print("                    (8m perfect comm) or remove+re-finetune.")
    print("=" * 78)


if __name__ == "__main__":
    main()
