"""
SMART ORACLE-EVASION — the TRUE evasion ceiling (LiDAR-aware dodge).

Unlike the naive 'flee straight away' oracle (which crashed into walls), this picks the
escape direction using the drone's OWN LiDAR: among the 16 sectors, choose the CLEAR one
(no nearby obstacle) that best increases distance from the rammer -> sidestep into open
space instead of backing into a wall. If boxed in, fall back to the policy.

Reads the drone's LiDAR from its observation: obs[6:22] = per-sector min distance / 12.
Sector k center direction = [cos(k*pi/8), sin(k*pi/8)] (matches the env's sector layout).

Interpretation (this is the CEILING of evasion):
  smart oracle success -> ~90%   => evasion IS viable -> BUILD M2 (M1 just didn't learn it)
  smart oracle success ~ 77/74   => threat is fundamentally hard (pinning) -> reframe defense

Usage:
    python probe_ram_oracle_smart.py                 # M0, f=2, full 200 maps
    python probe_ram_oracle_smart.py 2 models/apex_ultra_glide_v14_comm8_lidar_final.zip 30   # quick 30-map test
Args: [f] [model_path] [n_maps]
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy
from swarm_env_step_B10_8_0m import SwarmLidarEnv_StepB10_8_0m

DENSITIES = [0.20, 0.30]
NUM_MAPS = 200
DEFAULT_MODEL = "models/apex_ultra_glide_v14_comm8_lidar_final.zip"
COMM = 8.0
EVADE_DIST = 2.0      # start dodging when a rammer is within this range
CLEAR_THRESH = 2.5    # a LiDAR sector counts as "clear" if its nearest return is beyond this (m)
BASELINE = {0.20: 95.55, 0.30: 91.10}
# reference (no oracle): M0 ram f=2 = 77.38/73.50 ; naive oracle ~ 77.9/74.6

# 16 sector center directions (match env: center_angles = arange(16)*(2*pi/16))
_SECTOR_DIRS = np.array([[np.cos(k * np.pi / 8), np.sin(k * np.pi / 8)] for k in range(16)], dtype=np.float32)


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


def smart_escape(obs_vec, pos, rammer_pos, policy_act):
    """LiDAR-aware dodge: steer toward the clearest sector that moves away from the rammer."""
    lid_min = obs_vec[6:22] * 12.0           # 16 sector min distances (meters)
    flee = pos - rammer_pos
    n = np.linalg.norm(flee)
    if n < 1e-6:
        return policy_act
    flee_u = (flee / n).astype(np.float32)
    best_k, best_score = -1, 0.0             # require positive alignment with flee
    for k in range(16):
        if lid_min[k] > CLEAR_THRESH:        # clear direction
            score = float(_SECTOR_DIRS[k] @ flee_u)
            if score > best_score:
                best_score, best_k = score, k
    if best_k >= 0:
        return _SECTOR_DIRS[best_k].astype(np.float32)   # sidestep into clear, away-from-rammer space
    return policy_act                        # boxed in -> let the policy handle it


def main():
    f = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    model_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_MODEL
    n_maps = int(sys.argv[3]) if len(sys.argv) > 3 else NUM_MAPS
    traitors = set(range(f))
    if not os.path.exists(model_path):
        print(f"[!] model not found: {model_path}"); return
    print(f"[*] SMART ORACLE | model={model_path} | f={f} | EVADE_DIST={EVADE_DIST}m CLEAR={CLEAR_THRESH}m | maps={n_maps}")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    results = []
    for density in DENSITIES:
        env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density,
                                         communication_range=COMM, congestion_mode="lidar")
        env.traitor_indices = set(traitors); env.traitor_behavior = "ram"; env.deception_mode = "none"
        amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}

        h_reached = h_timeout = h_coll = h_drone = h_total = 0
        for map_idx in range(n_maps):
            if (map_idx + 1) % 100 == 0:
                print(f"  [{density:.2f}] {map_idx + 1}/{n_maps}")
            attempts = 0
            while True:
                seed = 900_000_000 + int(density * 100) * 10_000 + map_idx + attempts * 5_000
                obs_dict, _ = env.reset(seed=seed, options={"spawn_mode": "clustered"})
                if all(env._is_map_solvable(start_pos=env.positions[amap[a]]) for a in env.possible_agents):
                    break
                attempts += 1

            finished = set(); done = False
            while not done:
                active = [a for a in obs_dict.keys() if a not in finished]
                if not active:
                    break
                obs_batch = np.array([obs_dict[a] for a in active])
                act, _ = model.predict(obs_batch, deterministic=True)
                action = {}
                for k, a in enumerate(active):
                    idx = amap[a]
                    if idx in traitors:
                        action[a] = act[k]; continue
                    pos = env.positions[idx]
                    nearest_d, nearest_r = 1e9, None
                    for tj in traitors:
                        if env.possible_agents[tj] in env.agents:
                            d = np.linalg.norm(pos - env.positions[tj])
                            if d < nearest_d:
                                nearest_d, nearest_r = d, tj
                    if nearest_r is not None and nearest_d < EVADE_DIST:
                        action[a] = smart_escape(obs_dict[a], pos, env.positions[nearest_r], act[k])
                    else:
                        action[a] = act[k]
                obs_dict, _, terms, truncs, infos = env.step(action)
                for a in active:
                    if (terms.get(a, False) or truncs.get(a, False)) and a not in finished:
                        finished.add(a)
                        if amap[a] in traitors:
                            continue
                        h_total += 1
                        c = infos[a].get("cause")
                        if c == "success": h_reached += 1
                        elif c == "timeout": h_timeout += 1
                        elif c == "collision":
                            h_coll += 1
                            if infos[a].get("collision_type") == "drone": h_drone += 1
                if not env.agents:
                    done = True
        env.close()

        denom = max(h_total, 1)
        succ = 100.0 * h_reached / denom
        base = BASELINE.get(density)
        row = {"density": density, "f": f, "evasion": "smart_lidar",
               "oracle_honest_success": succ, "honest_timeout": 100.0 * h_timeout / denom,
               "honest_collision": 100.0 * h_coll / denom, "honest_drone_collision": 100.0 * h_drone / denom,
               "baseline_success": base}
        results.append(row)
        print(f"[*] d={density:.2f}: SMART oracle honest_success {succ:.2f}%  (baseline {base:.2f}%) "
              f"| timeout {row['honest_timeout']:.2f}% | coll {row['honest_collision']:.2f}% "
              f"(drone {row['honest_drone_collision']:.2f}%)")

    out_dir = os.path.join("results", "phase_c_probe")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"oracle_smart_f{f}.csv")
    pd.DataFrame(results).to_csv(out, index=False)
    print(f"\n[OK] saved: {out}")
    print("=" * 66)
    print("DECISION:")
    print("  smart oracle ~90%  -> evasion VIABLE -> BUILD M2 (M1 just didn't learn it)")
    print("  smart oracle ~77/74-> threat fundamentally hard (pinning) -> reframe defense")
    print("  refs: M0=77.4/73.5 | naive-oracle=77.9/74.6 | baseline(no rammer)=95.6/91.1")
    print("=" * 66)


if __name__ == "__main__":
    main()
