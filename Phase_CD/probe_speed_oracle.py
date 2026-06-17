# probe_speed_oracle.py
"""
Speed‑asymmetry oracle – give a targeted drone a temporary velocity boost
when a rammer gets within EVADE_DIST.  Measures whether boosting can
recover success > 80 % while keeping collisions low.
"""

import os, sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

# Avoid OpenMP duplicate runtime issues
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy
# --- run from anywhere: this folder + repo root on path; resolve relative paths to root ---
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)
# -----------------------------------------------------------------------------------------
from swarm_env_phasecd import SwarmLidarEnv_StepB10_8_0m

# ---------- Configuration ----------
DENSITIES = [0.20, 0.30]
DEFAULT_MODEL = "models/apex_ultra_glide_v14_comm8_lidar_final.zip"
COMM = 8.0
EVADE_DIST = 2.0          # when a rammer is this close we boost
BOOST = 1.4               # speed multiplier (change via CLI)
NUM_MAPS = 200
CLEAR_THRESH = 2.5        # a LiDAR sector is "clear" if its nearest return is beyond this (m)
# ----------------------------------

# 16 sector centre directions (match env: center_angles = arange(16)*(2*pi/16))
_SECTOR_DIRS = np.array([[np.cos(k * np.pi / 8), np.sin(k * np.pi / 8)] for k in range(16)],
                        dtype=np.float32)


def smart_escape(obs_vec, pos, rammer_pos, policy_act):
    """LiDAR-aware dodge: steer toward the clearest sector that moves away from the rammer.
    Identical to probe_ram_oracle_smart.py so the ONLY new variable is the speed boost."""
    lid_min = obs_vec[6:22] * 12.0
    flee = pos - rammer_pos
    n = np.linalg.norm(flee)
    if n < 1e-6:
        return policy_act
    flee_u = (flee / n).astype(np.float32)
    best_k, best_score = -1, 0.0
    for k in range(16):
        if lid_min[k] > CLEAR_THRESH:
            score = float(_SECTOR_DIRS[k] @ flee_u)
            if score > best_score:
                best_score, best_k = score, k
    if best_k >= 0:
        return _SECTOR_DIRS[best_k].astype(np.float32)
    return policy_act

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
    def forward(self, f):
        return self.policy_net(f[:, :130]), self.value_net(f[:, 130:])
    def forward_actor(self, f):
        return self.policy_net(f[:, :130])
    def forward_critic(self, f):
        return self.value_net(f[:, 130:])

class MAPPO_Policy_B5(ActorCriticPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_B5(self.features_dim,
                                                self.net_arch,
                                                self.activation_fn)

def main():
    global EVADE_DIST
    f = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    model_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MODEL
    boost = float(sys.argv[3]) if len(sys.argv) > 3 else BOOST
    n_maps = int(sys.argv[4]) if len(sys.argv) > 4 else NUM_MAPS
    # New optional arguments
    evade_dist = float(sys.argv[5]) if len(sys.argv) > 5 else EVADE_DIST
    brake = (len(sys.argv) > 6 and sys.argv[6].lower() == "--brake")
    EVADE_DIST = evade_dist

    traitors = set(range(f))
    print(f"[*] SPEED ORACLE | boost={boost} f={f} maps={n_maps}")

    model = PPO.load(model_path,
                     custom_objects={"policy_class": MAPPO_Policy_B5},
                     device="cpu")

    results = []
    # Track distances to rammer at collisions for analysis
    collision_distances = []
    for density in DENSITIES:
        env = SwarmLidarEnv_StepB10_8_0m(render_mode=None,
                                        target_density=density,
                                        communication_range=COMM,
                                        congestion_mode="lidar")
        # ensure speed boost dict exists
        env.speed_boost = {}
        env.traitor_indices = set(traitors)
        env.traitor_behavior = "ram"

        h_success = h_timeout = h_coll = h_coll_drone = h_coll_obstacle = h_total = 0
        for map_idx in range(n_maps):
            attempts = 0
            while True:
                seed = 900_000_000 + int(density * 100) * 10_000 + map_idx + attempts * 5_000
                obs_dict, _ = env.reset(seed=seed, options={"spawn_mode": "clustered"})
                if all(env._is_map_solvable(start_pos=env.positions[env.agent_name_mapping[a]])
                       for a in env.possible_agents):
                    break
                attempts += 1

            finished = set()
            while True:
                active = [a for a in obs_dict if a not in finished]
                if not active:
                    break
                obs_batch = np.array([obs_dict[a] for a in active])
                act, _ = model.predict(obs_batch, deterministic=True)

                action = {}
                for k, a in enumerate(active):
                    idx = env.agent_name_mapping[a]
                    if idx in traitors:
                        action[a] = act[k]
                        continue
                    # distance to nearest rammer
                    nearest_d, nearest_r = 1e9, None
                    for r_idx in traitors:
                        if env.possible_agents[r_idx] in env.agents:
                            d = np.linalg.norm(env.positions[idx] - env.positions[r_idx])
                            if d < nearest_d:
                                nearest_d, nearest_r = d, r_idx
                    # Record distance to rammer for later analysis
                    env.infos[a]["dist_to_rammer"] = float(nearest_d)
                    if nearest_r is not None and nearest_d < EVADE_DIST:
                        env.speed_boost[idx] = boost
                        action[a] = smart_escape(obs_dict[a], env.positions[idx],
                                                 env.positions[nearest_r], act[k])
                    else:
                        env.speed_boost[idx] = 1.0
                        action[a] = act[k]

                obs_dict, _, terms, truncs, infos = env.step(action)
                for a in active:
                    if (terms.get(a, False) or truncs.get(a, False)) and a not in finished:
                        finished.add(a)
                        if env.agent_name_mapping[a] in traitors:
                            continue
                        h_total += 1
                        cause = infos[a].get("cause")
                        if cause == "success":
                            h_success += 1
                        elif cause == "timeout":
                            h_timeout += 1
                        elif cause == "collision":
                            h_coll += 1
                            # Record distance to rammer at the moment of collision
                            dist = infos[a].get("dist_to_rammer")
                            if dist is not None:
                                collision_distances.append(dist)
                            coll_type = infos[a].get("collision_type", "unknown")
                            if coll_type == "drone":
                                h_coll_drone += 1
                            elif coll_type == "obstacle":
                                h_coll_obstacle += 1
                if not env.agents:
                    break
        denom = max(h_total, 1)
        row = {
            "density": density,
            "f": f,
            "boost": boost,
            "oracle_success": 100.0 * h_success / denom,
            "timeout": 100.0 * h_timeout / denom,
            "collision": 100.0 * h_coll / denom,
            "collision_drone": 100.0 * h_coll_drone / denom,
            "collision_obstacle": 100.0 * h_coll_obstacle / denom,
            "dist_to_rammer_at_collision": (np.mean(collision_distances) if collision_distances else np.nan),
        }
        results.append(row)
        print(f"[*] d={density:.2f} -> success {row['oracle_success']:.2f}% "
              f"| timeout {row['timeout']:.2f}% | coll {row['collision']:.2f}% "
              f"(drone {row['collision_drone']:.2f}% , obstacle {row['collision_obstacle']:.2f}% )")
        env.close()

    out_dir = os.path.join("results", "phase_c_probe")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir,
                f"oracle_speed_f{f}_b{boost:.2f}.csv")
    pd.DataFrame(results).to_csv(out_path, index=False)
    print(f"\n[OK] saved: {out_path}")

if __name__ == "__main__":
    main()
