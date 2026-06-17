"""
EGO-BLIND, DESIGN-A test: can a blind drone navigate on the COMPACT (nearest-per-neighbor)
shared channel — i.e. exactly what Design A's 27-d hazard block delivers — not the rich full set?

Your probe_ego_blind.py shares the FULL neighbor obstacle set (Design B) -> 88/90. That validates
rich sharing, not Design A. Here each blind ego receives, per comm-neighbor, ONLY that neighbor's
single NEAREST obstacle (within lidar_range). Runs BOTH configs for a direct comparison:
  full_blind    : ego blind, neighbors share ALL they sense (= your 88/90 reference)
  nearest_blind : ego blind, neighbors share NEAREST only (= Design A's compact info)  <- THE TEST

DECISION:
  nearest_blind >= ~85          -> compact channel suffices when blind -> Lever 2 premise holds for Design A.
  nearest_blind ~77-83          -> marginal -> enrich Design A encoding (k-nearest / ego-relevant obstacle).
  nearest_blind near/below 77   -> 1 obstacle/neighbor insufficient when blind -> must enrich before Lever 2.

References: self_only (no share) 77/85 ; check0 (ego+shared) 92/93 ; full_blind ~88/90 (your probe).

Usage:
    python probe_ego_blind_designA.py models/apex_ultra_glide_v14_comm8_lidar_final.zip 30
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

DENSITIES = [0.20]
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
    """Ego senses NO obstacles itself. 
    share_k_nearest: how many obstacles neighbor shares (0 = all).
    share_to_ego: if True, neighbor shares the obstacles closest to the EGO. If False, closest to ITSELF.
    """
    share_k_nearest = 0
    share_to_ego = False

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
                for j in range(self.n_drones):
                    if j != agent_idx and self.possible_agents[j] in self.agents \
                            and np.linalg.norm(pos - self.positions[j]) <= self.communication_range:
                        dj_to_neighbor = np.linalg.norm(centers - self.positions[j], axis=1)
                        visible_mask = dj_to_neighbor <= self.lidar_range
                        visible_idx = np.where(visible_mask)[0]
                        if len(visible_idx) > 0:
                            if self.share_to_ego:
                                # Distance of neighbor's visible obstacles to the ego drone
                                dj_to_ego = np.linalg.norm(centers[visible_idx] - pos, axis=1)
                                sorted_visible = visible_idx[np.argsort(dj_to_ego)]
                            else:
                                # Distance of neighbor's visible obstacles to neighbor itself
                                sorted_visible = visible_idx[np.argsort(dj_to_neighbor[visible_idx])]
                            
                            if self.share_k_nearest > 0:
                                for idx in sorted_visible[:self.share_k_nearest]:
                                    keep[idx] = True
                            else:
                                keep[visible_idx] = True
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


def run(model, density, k_nearest, share_to_ego, n_maps):
    env = EgoBlindEnv(render_mode=None, target_density=density,
                      communication_range=COMM, congestion_mode="lidar", lidar_range=5.0)
    env.collab_comm = True
    env.share_k_nearest = k_nearest
    env.share_to_ego = share_to_ego
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
    if k_nearest == 0:
        config_name = "full_blind"
    else:
        target_str = "to_ego" if share_to_ego else "to_neighbor"
        config_name = f"k={k_nearest}_{target_str}"
    return {"density": density, "config": config_name,
            "success": 100.0*reached/d, "coll": 100.0*coll/d, "coll_obstacle": 100.0*c_obs/d,
            "coll_drone": 100.0*c_drone/d, "timeout": 100.0*timeout/d}


def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    n_maps = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    if not os.path.exists(model_path):
        for cand in (os.path.join("models", os.path.basename(model_path)), os.path.abspath(model_path)):
            if os.path.exists(cand):
                model_path = cand; break
    if not os.path.exists(model_path):
        print(f"[!] model not found: {model_path}"); return
    print(f"[*] EGO-BLIND DESIGN-A test | {os.path.basename(model_path)} | lidar=5 comm={COMM} | maps={n_maps}")
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")

    rows = []
    for density in DENSITIES:
        print(f"\n[DENSITY {density:.2f}]")
        
        # 1. Full Blind (Reference)
        r = run(model, density, 0, False, n_maps)
        rows.append(r)
        print(f"  {r['config']:>20} | success {r['success']:6.2f}% | coll {r['coll']:5.2f}% "
              f"(obstacle {r['coll_obstacle']:5.2f} | drone {r['coll_drone']:5.2f}) | timeout {r['timeout']:.2f}%")
        
        # 2. Nearest-to-neighbor (k=1..5)
        for k in [1, 2, 3]:
            for to_ego in [False, True]:
                r = run(model, density, k, to_ego, n_maps)
                rows.append(r)
                print(f"  {r['config']:>20} | success {r['success']:6.2f}% | coll {r['coll']:5.2f}% "
                      f"(obstacle {r['coll_obstacle']:5.2f} | drone {r['coll_drone']:5.2f}) | timeout {r['timeout']:.2f}%")

    out_dir = os.path.join(_HERE, "results")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "ego_blind_designA.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\n[OK] saved: {out}")
    print("=" * 74)
    print("DECISION (nearest_blind = Design A's compact channel, ego blind):")
    print("  >= ~85   -> compact channel suffices blind -> Lever 2 premise holds for Design A.")
    print("  ~77-83   -> marginal -> enrich encoding (k-nearest / ego-relevant obstacle).")
    print("  <= ~77   -> 1 obstacle/neighbor insufficient blind -> enrich before Lever 2.")
    print("=" * 74)


if __name__ == "__main__":
    main()
