"""
FEATURE IMPORTANCE (ablation sensitivity) for the raster model — 698-d obs layout.

Tells us which obs segments the policy relies on — in particular whether it uses the
48-d SHARED-OBSTACLE-MAP channel (separate from ego LiDAR).

Method: run no-adversary episodes; each config zeros ONE actor obs segment before
model.predict, and we report the success drop vs the un-ablated baseline. Larger
drop = more important.

Raster actor obs layout (first 178 dims; [178:698] is the critic block):
  vel[0:2] goal_dir[2:4] goal_dist[4:5] yaw[5:6] lidar[6:54] neighbors[54:99]
  congestion[99:100] sync[100:120] trajectory[120:130] SHARED_MAP[130:178]

Usage:
    python feature_importance_raster.py models/raster_l5_d0.4_ON_final.zip 5 10 0.4 on 50
Args: [model_path] [lidar] [comm] [dropout] [on|off] [n_maps]
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
from swarm_env_raster import SwarmLidarEnv_Raster

DENSITIES = [0.20, 0.30]
LOCAL_NEW = 178  # 130 base + 48 shared-map
GLOBAL = 520
DROPOUT_SUSTAIN = 20
STRAIGHT_LINE = False  # set by --straight-line CLI flag; Gate-0 probe (remove Dijkstra heading)

# Segments: (name, start_idx, end_idx) in the actor's 178-d local observation
SEGMENTS = [
    ("vel", 0, 2),
    ("goal_dir", 2, 4),
    ("goal_dist", 4, 5),
    ("yaw", 5, 6),
    ("lidar", 6, 54),
    ("neighbors", 54, 99),
    ("congestion", 99, 100),
    ("sync", 100, 120),
    ("trajectory", 120, 130),
    ("SHARED_MAP", 130, 178),  # the raster channel — 48-d communicated obstacles
]


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

    def forward(self, f):
        return self.policy_net(f[:, :LOCAL_NEW]), self.value_net(f[:, LOCAL_NEW:])

    def forward_actor(self, f):
        return self.policy_net(f[:, :LOCAL_NEW])

    def forward_critic(self, f):
        return self.value_net(f[:, LOCAL_NEW:])


class MAPPO_Policy_Raster(ActorCriticPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_Raster(self.features_dim, self.net_arch, self.activation_fn)


def run(model, density, lidar_range, comm_range, dropout_prob, use_shared, ablate, n_maps):
    """
    ablate = (lo, hi) to zero in each obs before predict, or None for baseline.
    use_shared = True/False to enable/disable the shared-map channel (for on/off comparison).
    """
    env = SwarmLidarEnv_Raster(
        render_mode=None,
        target_density=density,
        communication_range=comm_range,
        congestion_mode="lidar",
        lidar_range=lidar_range,
        lidar_dropout=dropout_prob,
        dropout_sustain=DROPOUT_SUSTAIN,
        use_shared_map=use_shared,
        probe_lidar_slot=False,
        straight_line_goal=STRAIGHT_LINE
    )
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

        finished = set()
        done = False
        while not done:
            active = [a for a in obs_dict.keys() if a not in finished]
            if not active:
                break
            obs_batch = np.array([obs_dict[a] for a in active], dtype=np.float32)

            # Apply ablation if specified
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
    global STRAIGHT_LINE
    if "--straight-line" in sys.argv:
        STRAIGHT_LINE = True
        sys.argv = [a for a in sys.argv if a != "--straight-line"]

    model_path = sys.argv[1] if len(sys.argv) > 1 else "models/raster_l5_d0.4_ON_final.zip"
    lidar_range = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
    comm_range = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
    dropout_prob = float(sys.argv[4]) if len(sys.argv) > 4 else 0.4
    comm_mode = sys.argv[5].lower() if len(sys.argv) > 5 else "on"
    n_maps = int(sys.argv[6]) if len(sys.argv) > 6 else 50

    use_shared = (comm_mode == "on")

    if not os.path.exists(model_path):
        for cand in (os.path.join("models", os.path.basename(model_path)), os.path.abspath(model_path)):
            if os.path.exists(cand):
                model_path = cand
                break

    if not os.path.exists(model_path):
        print(f"[!] model not found: {model_path}")
        return

    print(f"[*] FEATURE IMPORTANCE | {os.path.basename(model_path)} | lidar={lidar_range} comm={comm_range} dropout={dropout_prob} mode={comm_mode} | maps={n_maps}")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_Raster}, device="cpu")

    rows = []
    for density in DENSITIES:
        base = run(model, density, lidar_range, comm_range, dropout_prob, use_shared, None, n_maps)
        print(f"\n[DENSITY {density:.2f}]  baseline (no ablation) = {base:.2f}%")
        print(f"  {'segment':>15} {'dims':>9} | {'success':>8} | {'DROP':>7}")
        print(f"  {'baseline':>15} {'-':>9} | {base:7.2f}% | {0.0:6.2f}")

        for name, lo, hi in SEGMENTS:
            s = run(model, density, lidar_range, comm_range, dropout_prob, use_shared, (lo, hi), n_maps)
            drop = base - s
            print(f"  {name:>15} {f'[{lo}:{hi}]':>9} | {s:7.2f}% | {drop:6.2f}")
            rows.append({
                "density": density,
                "segment": name,
                "dims": f"{lo}:{hi}",
                "baseline": base,
                "ablated_success": s,
                "drop": drop
            })

    out_dir = os.path.join(_HERE, "results")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"feature_importance_raster_{comm_mode}.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\n[OK] saved: {out}")
    print("    Big DROP = policy relies on that block.")
    print("    SHARED_MAP drop ~0 => raster channel ignored (comm not working).")
    print("    SHARED_MAP drop > 0 => policy uses neighbor obstacles for navigation.")


if __name__ == "__main__":
    main()
