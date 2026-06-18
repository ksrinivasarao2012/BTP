"""
Probe for the B1 raster env (swarm_env_raster.py).

A separate channel can't be tested zero-shot on M0, so this validates the env's SHARED-MAP COMPUTATION
by routing it through the LiDAR slot (probe_lidar_slot=True): ego blind to its own obstacles, the 48-d
shared map placed in obs[6:54], M0 run zero-shot.

Configs (lidar=5, comm=10, ego blind):
  dropout=0.0  -> all neighbors share -> should reproduce full_blind ~88/90 (validates _shared_lidar/_cast48)
  dropout=0.4  -> ~40% of neighbors blind & SHARE NOTHING (sender-gating) -> lower success (gating works)

Also prints the normal-mode obs dim (must be 698).

Usage:
    python probe_raster.py models/apex_ultra_glide_v14_comm8_lidar_final.zip 30
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
_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
for _p in (_ROOT, _PHASE_CD, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)
from swarm_env_raster import SwarmLidarEnv_Raster, OBS_DIM

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


def run(model, density, dropout, n_maps):
    env = SwarmLidarEnv_Raster(render_mode=None, target_density=density, communication_range=COMM,
                               congestion_mode="lidar", lidar_range=5.0,
                               lidar_dropout=dropout, probe_lidar_slot=True)
    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
    reached = timeout = coll = c_obs = c_drone = total = 0
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
            if not env.agents:
                done = True
    env.close()
    d = max(total, 1)
    return {"density": density, "dropout": dropout, "success": 100.0*reached/d, "coll": 100.0*coll/d,
            "coll_obstacle": 100.0*c_obs/d, "coll_drone": 100.0*c_drone/d, "timeout": 100.0*timeout/d}


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    n_maps = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    if not os.path.exists(model_path):
        for cand in (os.path.join("models", os.path.basename(model_path)), os.path.abspath(model_path)):
            if os.path.exists(cand):
                model_path = cand; break
    if not os.path.exists(model_path):
        print(f"[!] model not found: {model_path}"); return

    # obs-dim sanity (normal mode must be 698)
    chk = SwarmLidarEnv_Raster(render_mode=None, target_density=0.20, communication_range=COMM,
                               congestion_mode="lidar", lidar_range=5.0)
    o, _ = chk.reset(seed=1, options={"spawn_mode": "clustered"})
    dim = len(next(iter(o.values())))
    chk.close()
    print(f"[*] obs dim (normal mode) = {dim}  (expect {OBS_DIM})  ->  {'OK' if dim == OBS_DIM else 'MISMATCH!'}")

    print(f"[*] PROBE raster shared-map (via lidar slot, ego blind) | {os.path.basename(model_path)} | maps={n_maps}")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    rows = []
    for density in DENSITIES:
        print(f"\n[DENSITY {density:.2f}]")
        for dropout in (0.0, 0.4):
            r = run(model, density, dropout, n_maps)
            rows.append(r)
            print(f"  dropout={dropout:.1f} | success {r['success']:6.2f}% | coll {r['coll']:5.2f}% "
                  f"(obstacle {r['coll_obstacle']:5.2f} | drone {r['coll_drone']:5.2f}) | timeout {r['timeout']:.2f}%")

    out_dir = os.path.join(_HERE, "results")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "raster_probe.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\n[OK] saved: {out}")
    print("=" * 72)
    print("CHECK: dropout=0.0 ~= 88/90 -> shared-map code correct & sufficient.")
    print("       dropout=0.4 < dropout=0.0 -> sender-gating works (blind neighbors share nothing).")
    print("=" * 72)


if __name__ == "__main__":
    main()
