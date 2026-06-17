"""
DESIGN-B ORACLE — does COLLABORATIVE obstacle perception recover short-LiDAR success?

Motivation (verified): comm carries ONLY drone positions, never obstacles; LiDAR already sees
drones within range; shortening LiDAR creates an OBSTACLE-sensing deficit that neighbor-position
comm cannot fix. Design B asks: if comm instead shared OBSTACLE perception (each drone tells
teammates within comm range about obstacles it senses), would success recover? If yes, comm CAN
carry non-redundant, poisonable value (false-hazard deception) -> build the trust defense.
If no, stop -> fundamental-limit paper.

This is a perfect-sharing UPPER BOUND, run ZERO-SHOT on M0 (collab keeps the 48-D LiDAR semantics
and M0's native /12 encoding, so no retraining is needed to test feasibility).

Three configs per density (no adversary, f=0):
  (1) short  : lidar=5, no sharing            -> the deficit baseline (~77/85)
  (2) collab : lidar=5, sharing ON (comm=10)  -> THE ORACLE
  (3) full   : lidar=12, no sharing           -> the ceiling (~92/95)

DECISION:
  collab climbs from (1) toward (3) (e.g. +8 pp, obstacle-collisions drop) -> shared obstacle
    perception works -> comm can be made valuable -> BUILD Design-A trust defense.
  collab ~= (1) -> sharing doesn't help -> STOP -> limit paper.

Usage:
    python probe_collab_lidar.py ../models/apex_ultra_glide_v14_comm8_lidar_final.zip 30
Args: [model_path] [n_maps]
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
_HERE = os.path.dirname(os.path.abspath(__file__))      # .../Phase_CD/Collab_Perception
_PHASE_CD = os.path.dirname(_HERE)                       # .../Phase_CD  (holds swarm_env_phasecd.py)
_ROOT = os.path.dirname(_PHASE_CD)                       # repo root     (holds models/, Phase_CD/)
for _p in (_ROOT, _PHASE_CD, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)
# ----------------------------------------------------------------------------------------------
from swarm_env_phasecd import SwarmLidarEnv_StepB10_8_0m

DENSITIES = [0.20, 0.30]
DEFAULT_MODEL = "models/apex_ultra_glide_v14_comm8_lidar_final.zip"
COMM = 10.0


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


def run_config(model, density, lidar_range, comm_range, collab, n_maps):
    env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density,
                                     communication_range=comm_range, congestion_mode="lidar",
                                     lidar_range=lidar_range)
    env.collab_comm = collab
    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
    reached = timeout = coll = c_obs = c_drone = c_wall = total = 0
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
            obs_batch = np.array([obs_dict[a] for a in active])
            act, _ = model.predict(obs_batch, deterministic=True)
            action = {a: act[k] for k, a in enumerate(active)}
            obs_dict, _, terms, truncs, infos = env.step(action)
            for a in active:
                if (terms.get(a, False) or truncs.get(a, False)) and a not in finished:
                    finished.add(a)
                    total += 1
                    c = infos[a].get("cause")
                    if c == "success": reached += 1
                    elif c == "timeout": timeout += 1
                    elif c == "collision":
                        coll += 1
                        ct = infos[a].get("collision_type")
                        if ct == "obstacle": c_obs += 1
                        elif ct == "drone": c_drone += 1
                        elif ct == "wall": c_wall += 1
            if not env.agents:
                done = True
    env.close()
    d = max(total, 1)
    return {"density": density, "lidar": lidar_range, "comm": comm_range, "collab": collab,
            "success": 100.0 * reached / d, "timeout": 100.0 * timeout / d,
            "coll": 100.0 * coll / d, "coll_obstacle": 100.0 * c_obs / d,
            "coll_drone": 100.0 * c_drone / d, "coll_wall": 100.0 * c_wall / d}


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    n_maps = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    # forgiving lookup: cwd was chdir'd to repo root, so try root-relative + models/<basename> fallbacks
    if not os.path.exists(model_path):
        for cand in (os.path.join("models", os.path.basename(model_path)), os.path.abspath(model_path)):
            if os.path.exists(cand):
                model_path = cand; break
    if not os.path.exists(model_path):
        print(f"[!] model not found: {model_path}"); return
    print(f"[*] COLLAB-LIDAR ORACLE (Design B) | {model_path} | comm={COMM} | maps={n_maps} | NO adversary")
    print("    configs: (1) lidar5 no-share | (2) lidar5 SHARE | (3) lidar12 full-sight ceiling")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    configs = [("short_l5", 5.0, COMM, False),
               ("collab_l5", 5.0, COMM, True),
               ("full_l12", 12.0, COMM, False)]
    rows = []
    for density in DENSITIES:
        print(f"\n[DENSITY {density:.2f}]")
        for label, lr, cr, cl in configs:
            r = run_config(model, density, lr, cr, cl, n_maps)
            r["config"] = label
            rows.append(r)
            print(f"  {label:>10} | success {r['success']:6.2f}% | coll {r['coll']:5.2f}% "
                  f"(obstacle {r['coll_obstacle']:5.2f} | drone {r['coll_drone']:5.2f} | wall {r['coll_wall']:4.2f}) "
                  f"| timeout {r['timeout']:.2f}%")

    out_dir = os.path.join(_HERE, "results")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "collab_lidar_oracle.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\n[OK] saved: {out}")
    print("=" * 72)
    print("DECISION: collab_l5 climbs from short_l5 toward full_l12 (obstacle-coll drops) ->")
    print("          shared obstacle perception WORKS -> comm can carry value -> BUILD trust defense.")
    print("          collab_l5 ~= short_l5 -> sharing doesn't help -> STOP -> limit paper.")
    print("=" * 72)


if __name__ == "__main__":
    main()
