"""
EGO-BLIND, "NEAREST-TO-EGO" test — the smarter compact channel.

k=1 nearest-to-NEIGHBOR collapsed when blind (~50%) because "the obstacle nearest to a neighbor"
is usually NOT the obstacle in the EGO's path. Fix: each comm-neighbor shares, among the obstacles
IT senses (within its lidar_range), the one NEAREST TO THE EGO. Still 1 obstacle/neighbor (27-d,
attributable) and CTDE-clean (neighbor uses the ego's broadcast position + its own sensed obstacles).

Runs 3 configs/density, ego blind, M0 zero-shot:
  full_blind      : neighbors share ALL they sense              (rich reference, ~88/90)
  near_neighbor   : neighbors share their own NEAREST obstacle  (= old Design A, ~50% FAIL)
  near_ego        : neighbors share the obstacle nearest to EGO (= THE NEW compact channel)  <- TEST

DECISION:
  near_ego >= ~85  -> compact 27-d channel suffices blind with smart selection -> Design A viable.
  near_ego marginal/low -> go to per-neighbor 8-sector map (option 3).

References: self_only 77/85 ; check0 (ego+shared) 92/93 ; full_blind ~88/90.

Usage:
    python probe_ego_blind_nearest2ego.py models/apex_ultra_glide_v14_comm8_lidar_final.zip 30
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


class EgoBlindEnv(SwarmLidarEnv_StepB10_8_0m):
    """Ego senses NO obstacles itself. share_mode in {full, near_neighbor, near_ego}."""
    share_mode = "full"

    def _ray_cast(self, agent_idx):
        num_sectors, rays_per_sector = 16, 12
        num_rays = num_sectors * rays_per_sector
        collab = self.collab_comm
        max_range = self.collab_range if collab else self.lidar_range
        pos = self.positions[agent_idx]
        ray_dirs = self.ray_dirs
        min_distances = np.full(num_rays, max_range, dtype=np.float32)

        for boundary, axis, direction in [(self.WIDTH, 0, 1), (0, 0, -1), (self.HEIGHT, 1, 1), (0, 1, -1)]:
            mask = ray_dirs[:, axis] * direction > 1e-6
            if np.any(mask):
                d = (boundary - pos[axis]) / ray_dirs[mask, axis]
                min_distances[mask] = np.minimum(min_distances[mask], np.where(d > 0, d, max_range).astype(np.float32))

        def intersect_circles(centers, radii):
            rel_pos = centers - pos
            proj = rel_pos @ ray_dirs.T
            rel_pos_sq = np.sum(rel_pos**2, axis=1, keepdims=True)
            dist_to_ray_sq = rel_pos_sq - proj**2
            hit_mask = (proj > 0) & (dist_to_ray_sq < radii[:, np.newaxis]**2)
            if np.any(hit_mask):
                sqrt_arg = radii[:, np.newaxis]**2 - dist_to_ray_sq
                dists = proj - np.sqrt(np.maximum(sqrt_arg, 0))
                dists[~hit_mask] = max_range
                return np.min(dists, axis=0)
            return np.full(num_rays, max_range, dtype=np.float32)

        if self.obstacles:
            obs_array = np.array(self.obstacles, dtype=np.float32)
            if collab:
                centers = obs_array[:, :2]
                keep = np.zeros(len(centers), dtype=bool)   # EGO BLIND: senses nothing itself
                d_ego = np.linalg.norm(centers - pos, axis=1)
                for j in range(self.n_drones):
                    if j != agent_idx and self.possible_agents[j] in self.agents \
                            and np.linalg.norm(pos - self.positions[j]) <= self.communication_range:
                        dj = np.linalg.norm(centers - self.positions[j], axis=1)
                        sensed = np.where(dj <= self.lidar_range)[0]   # obstacles neighbor j senses
                        if len(sensed) == 0:
                            continue
                        if self.share_mode == "full":
                            keep[sensed] = True
                        elif self.share_mode == "near_neighbor":
                            keep[sensed[int(np.argmin(dj[sensed]))]] = True
                        elif self.share_mode == "near_ego":
                            keep[sensed[int(np.argmin(d_ego[sensed]))]] = True
                obs_array = obs_array[keep]
            if len(obs_array):
                min_distances = np.minimum(min_distances, intersect_circles(obs_array[:, :2], obs_array[:, 2] + self.drone_radius))

        other_indices = [j for j in range(self.n_drones) if j != agent_idx and self.possible_agents[j] in self.agents]
        if other_indices:
            min_distances = np.minimum(min_distances, intersect_circles(self.positions[other_indices], np.full(len(other_indices), 2.0 * self.drone_radius, dtype=np.float32)))

        sector_res = min_distances.reshape(num_sectors, rays_per_sector)
        readings = np.zeros(num_sectors * 3, dtype=np.float32)
        readings[:num_sectors] = np.min(sector_res, axis=1)
        readings[num_sectors:2*num_sectors] = np.mean(sector_res, axis=1)
        readings[2*num_sectors:] = np.std(sector_res, axis=1)
        return readings


def run(model, density, share_mode, n_maps):
    env = EgoBlindEnv(render_mode=None, target_density=density,
                      communication_range=COMM, congestion_mode="lidar", lidar_range=5.0)
    env.collab_comm = True
    env.share_mode = share_mode
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
    return {"density": density, "share_mode": share_mode, "success": 100.0*reached/d,
            "coll": 100.0*coll/d, "coll_obstacle": 100.0*c_obs/d, "coll_drone": 100.0*c_drone/d,
            "timeout": 100.0*timeout/d}


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    n_maps = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    if not os.path.exists(model_path):
        for cand in (os.path.join("models", os.path.basename(model_path)), os.path.abspath(model_path)):
            if os.path.exists(cand):
                model_path = cand; break
    if not os.path.exists(model_path):
        print(f"[!] model not found: {model_path}"); return
    print(f"[*] EGO-BLIND NEAREST-TO-EGO test | {os.path.basename(model_path)} | lidar=5 comm={COMM} | maps={n_maps}")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    rows = []
    for density in DENSITIES:
        print(f"\n[DENSITY {density:.2f}]")
        for mode in ("full", "near_neighbor", "near_ego"):
            r = run(model, density, mode, n_maps)
            rows.append(r)
            print(f"  {mode:>13} | success {r['success']:6.2f}% | coll {r['coll']:5.2f}% "
                  f"(obstacle {r['coll_obstacle']:5.2f} | drone {r['coll_drone']:5.2f}) | timeout {r['timeout']:.2f}%")

    out_dir = os.path.join(_HERE, "results")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "ego_blind_nearest2ego.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\n[OK] saved: {out}")
    print("=" * 74)
    print("DECISION: near_ego >= ~85 -> smart compact (27-d, attributable) suffices blind -> Design A viable.")
    print("          near_ego marginal/low -> escalate to per-neighbor 8-sector map (option 3).")
    print("=" * 74)


if __name__ == "__main__":
    main()
