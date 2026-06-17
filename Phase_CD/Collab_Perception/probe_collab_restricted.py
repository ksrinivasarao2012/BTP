"""
CHECK 0 — Design-A information-sufficiency oracle (NO training).

Design A's channel is lossy: each comm-neighbor shares only its SINGLE NEAREST obstacle (27 dims),
not the rich set Design B fused. This probe upper-bounds Design A WITHOUT training: it reuses the
Design-B collaborative-LiDAR oracle but restricts each neighbor's contribution to its nearest
obstacle (env.collab_nearest_only=True), run ZERO-SHOT on M0.

Configs per density (no adversary):
  (1) short_l5      : lidar=5, no sharing               -> deficit baseline (~77/85)
  (2) restricted_l5 : lidar=5, share NEAREST-per-nbr    -> Design-A CEILING (the number that matters)
  (3) full_l5       : lidar=5, share ALL (=Design B)    -> rich-sharing reference (~92/94)
  (4) full_l12      : lidar=12, no sharing              -> sight ceiling (~92/95)

DECISION (Check 0):
  restricted_l5 close to full_l5 (e.g. >= ~88/91) -> compact channel is RICH ENOUGH -> Design A worth training.
  restricted_l5 much below full_l5 (<= ~83/88)    -> 1 obstacle/neighbor too lossy -> enrich encoding (or use Design B).

Usage:
    python probe_collab_restricted.py models/apex_ultra_glide_v14_comm8_lidar_final.zip 30
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
# this file lives 2 levels deep: Phase_CD/Collab_Perception/  -> repo root is two dirnames up
_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
for _p in (_ROOT, _PHASE_CD, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)
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


from concurrent.futures import ProcessPoolExecutor, as_completed

def run_config(model_path, density, lidar_range, comm_range, collab, nearest_only, n_maps):
    # Load model locally inside the worker process because PPO models cannot be pickled/passed directly to other processes
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")
    env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=density,
                                     communication_range=comm_range, congestion_mode="lidar",
                                     lidar_range=lidar_range)
    env.collab_comm = collab
    env.collab_nearest_only = nearest_only
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
    return {"density": density, "lidar": lidar_range, "collab": collab, "nearest_only": nearest_only,
            "success": 100.0*reached/d, "coll": 100.0*coll/d,
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
    print(f"[*] CHECK 0 — restricted-share oracle | {os.path.basename(model_path)} | comm={COMM} | maps={n_maps} | parallel (4 cores)")

    #        label,            lidar, collab, nearest_only
    configs = [("short_l5",      5.0,  False,  False),
               ("restricted_l5", 5.0,  True,   True),    # Design-A ceiling
               ("full_l5",       5.0,  True,   False),   # Design-B (rich)
               ("full_l12",      12.0, False,  False)]

    tasks = []
    for density in DENSITIES:
        for label, lr, cl, no in configs:
            tasks.append((label, density, lr, cl, no))

    rows = []
    # Run in parallel using 4 cores
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(run_config, model_path, density, lr, COMM, cl, no, n_maps): (label, density)
            for label, density, lr, cl, no in tasks
        }
        for fut in as_completed(futures):
            label, density = futures[fut]
            try:
                r = fut.result()
                r["config"] = label
                rows.append(r)
            except Exception as e:
                print(f"⚠️ Task failed for config={label}, density={density}: {e}")

    # Print results grouped by density
    for density in DENSITIES:
        print(f"\n[DENSITY {density:.2f}]")
        sub_rows = [r for r in rows if r["density"] == density]
        # Sort sub_rows to match original config ordering
        order = {"short_l5": 0, "restricted_l5": 1, "full_l5": 2, "full_l12": 3}
        sub_rows.sort(key=lambda x: order.get(x["config"], 99))
        for r in sub_rows:
            print(f"  {r['config']:>13} | success {r['success']:6.2f}% | coll {r['coll']:5.2f}% "
                  f"(obstacle {r['coll_obstacle']:5.2f} | drone {r['coll_drone']:5.2f}) | timeout {r['timeout']:.2f}%")

    out_dir = os.path.join(_HERE, "results")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "collab_restricted_oracle.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\n[OK] saved: {out}")
    print("=" * 72)
    print("CHECK 0: restricted_l5 close to full_l5 (>= ~88/91) -> compact channel RICH ENOUGH -> train Design A.")
    print("         restricted_l5 << full_l5 (<= ~83/88)       -> too lossy -> enrich encoding (or use Design B).")
    print("=" * 72)


if __name__ == "__main__":
    main()
