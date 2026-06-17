"""
FEATURE IMPORTANCE (ablation sensitivity) for a Design-A collab model — like the version-1
"lidar + goal dominate" analysis, but for the 677-d collab obs. Tells us which obs segments the
policy actually relies on — in particular whether it uses the 27-d SHARED-HAZARD block at all
(the A2 gate came back ~0, so we expect hazard's drop to be ~0 = ignored).

Method: run no-adversary episodes; each config zeros ONE actor obs segment before model.predict,
and we report the success drop vs the un-ablated baseline. Larger drop = more important.

Actor obs layout (first 157 dims; [157:677] is the critic block and doesn't affect actions):
  vel[0:2] goal_dir[2:4] goal_dist[4:5] yaw[5:6] lidar[6:54] neighbors[54:99]
  congestion[99:100] sync[100:120] trajectory[120:130] HAZARD[130:157]

Usage:
    python feature_importance_collab.py models/collab_l5_c10_hazardON_final.zip 5 10 50
Args: [model_path] [lidar] [comm] [n_maps]
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
_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
for _p in (_ROOT, _PHASE_CD, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)
from swarm_env_collab import SwarmLidarEnv_StepB10_8_0m

DENSITIES = [0.20, 0.30]
LOCAL_NEW = 157
GLOBAL = 520
SEGMENTS = [("vel", 0, 2), ("goal_dir", 2, 4), ("goal_dist", 4, 5), ("yaw", 5, 6),
            ("lidar", 6, 54), ("neighbors", 54, 99), ("congestion", 99, 100),
            ("sync", 100, 120), ("trajectory", 120, 130), ("HAZARD", 130, 157)]


class MAPPO_Extractor_Collab(nn.Module):
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

    def forward(self, f): return self.policy_net(f[:, :LOCAL_NEW]), self.value_net(f[:, LOCAL_NEW:])
    def forward_actor(self, f): return self.policy_net(f[:, :LOCAL_NEW])
    def forward_critic(self, f): return self.value_net(f[:, LOCAL_NEW:])


class MAPPO_Policy_Collab(ActorCriticPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_Collab(self.features_dim, self.net_arch, self.activation_fn)


def run(model, density, lidar_range, comm_range, ablate, n_maps):
    """ablate = (lo, hi) to zero in each obs before predict, or None for baseline."""
    env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density,
                                     communication_range=comm_range, congestion_mode="lidar",
                                     lidar_range=lidar_range)
    env.share_hazards = True   # hazards PRESENT so we can test whether the policy uses them
    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
    reached = total = 0
    for map_idx in range(n_maps):
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
            obs_batch = np.array([obs_dict[a] for a in active], dtype=np.float32)
            if ablate is not None:
                obs_batch[:, ablate[0]:ablate[1]] = 0.0
            act, _ = model.predict(obs_batch, deterministic=True)
            action = {a: act[k] for k, a in enumerate(active)}
            obs_dict, _, terms, truncs, infos = env.step(action)
            for a in active:
                if (terms.get(a, False) or truncs.get(a, False)) and a not in finished:
                    finished.add(a)
                    total += 1
                    if infos[a].get("cause") == "success":
                        reached += 1
            if not env.agents:
                done = True
    env.close()
    return 100.0 * reached / max(total, 1)


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else "models/collab_l5_c10_hazardON_final.zip"
    lidar_range = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
    comm_range = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
    n_maps = int(sys.argv[4]) if len(sys.argv) > 4 else 50
    if not os.path.exists(model_path):
        for cand in (os.path.join("models", os.path.basename(model_path)), os.path.abspath(model_path)):
            if os.path.exists(cand):
                model_path = cand; break
    if not os.path.exists(model_path):
        print(f"[!] model not found: {model_path}"); return
    print(f"[*] FEATURE IMPORTANCE | {os.path.basename(model_path)} | lidar={lidar_range} comm={comm_range} | maps={n_maps}")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_Collab}, device="cpu")

    rows = []
    for density in DENSITIES:
        base = run(model, density, lidar_range, comm_range, None, n_maps)
        print(f"\n[DENSITY {density:.2f}]  baseline (no ablation) = {base:.2f}%")
        print(f"  {'segment':>12} {'dims':>9} | {'success':>8} | {'DROP':>7}")
        print(f"  {'baseline':>12} {'-':>9} | {base:7.2f}% | {0.0:6.2f}")
        for name, lo, hi in SEGMENTS:
            s = run(model, density, lidar_range, comm_range, (lo, hi), n_maps)
            drop = base - s
            print(f"  {name:>12} {f'[{lo}:{hi}]':>9} | {s:7.2f}% | {drop:6.2f}")
            rows.append({"density": density, "segment": name, "dims": f"{lo}:{hi}",
                         "baseline": base, "ablated_success": s, "drop": drop})

    out_dir = os.path.join(_HERE, "results")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "feature_importance_collab.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\n[OK] saved: {out}")
    print("    Big DROP = policy relies on that block. HAZARD drop ~0 => shared-hazard channel ignored")
    print("    (explains comm_value ~ 0). Expect lidar + goal_dir to dominate, as in version 1.")


if __name__ == "__main__":
    main()
