"""
Verify if neighbor-shared obstacle information alone is navigationally sufficient.
Ego is blind (its own positions removed from collab sensor checks), navigating
zero-shot on M0 using only neighbor-shared obstacle projections in the LiDAR channel.
"""
import os
import sys
import numpy as np
import pandas as pd
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy

# Path setup
_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
for _p in (_ROOT, _PHASE_CD, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)

from Phase_CD.swarm_env_phasecd import SwarmLidarEnv_StepB10_8_0m
from Phase_CD.Collab_Perception.probe_collab_restricted import MAPPO_Policy_B5, MAPPO_Extractor_B5

class EgoBlindEnv(SwarmLidarEnv_StepB10_8_0m):
    def _ray_cast(self, agent_idx):
        # Override _ray_cast to exclude ego's own sensor positions
        num_sectors = 16
        rays_per_sector = 12
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
                # EGO-BLIND: sensors list excludes the ego drone 'pos'
                sensors = []
                for j in range(self.n_drones):
                    if j != agent_idx and self.possible_agents[j] in self.agents \
                            and np.linalg.norm(pos - self.positions[j]) <= self.communication_range:
                        sensors.append(self.positions[j])
                
                if len(sensors) > 0:
                    sensors = np.array(sensors, dtype=np.float32)
                    d_so = np.linalg.norm(obs_array[:, :2][None, :, :] - sensors[:, None, :], axis=2)
                    obs_array = obs_array[d_so.min(axis=0) <= self.lidar_range]
                else:
                    obs_array = np.empty((0, 3), dtype=np.float32)

            if len(obs_array):
                min_distances = np.minimum(min_distances, intersect_circles(obs_array[:, :2], obs_array[:, 2] + self.drone_radius))

        # We still want to see other drones locally for basic avoidance
        other_indices = [j for j in range(self.n_drones) if j != agent_idx and self.possible_agents[j] in self.agents]
        if other_indices:
            min_distances = np.minimum(min_distances, intersect_circles(self.positions[other_indices], np.full(len(other_indices), 2.0 * self.drone_radius, dtype=np.float32)))

        sector_res = min_distances.reshape(num_sectors, rays_per_sector)
        readings = np.zeros(num_sectors * 3, dtype=np.float32)
        readings[:num_sectors] = np.min(sector_res, axis=1)
        readings[num_sectors:2*num_sectors] = np.mean(sector_res, axis=1)
        readings[2*num_sectors:] = np.std(sector_res, axis=1)
        return readings

def run_eval(model_path, density, lidar_range, comm_range, collab, n_maps):
    env = EgoBlindEnv(render_mode=None, target_density=density,
                       communication_range=comm_range, congestion_mode="lidar",
                       lidar_range=lidar_range)
    env.collab_comm = collab
    amap = {a: env.agent_name_mapping[a] for a in env.possible_agents}
    model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")
    
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
    return {"density": density, "success": 100.0*reached/d, "coll": 100.0*coll/d,
            "coll_obstacle": 100.0*c_obs/d, "coll_drone": 100.0*c_drone/d, "timeout": 100.0*timeout/d}

def main():
    model_path = "models/apex_ultra_glide_v14_comm8_lidar_final.zip"
    n_maps = 30
    print(f"[*] EGO-BLIND COLLAB ORACLE | model={model_path} | comm=10.0 | maps={n_maps}")
    
    # We evaluate LiDAR=5m, sharing ON, but ego is blind.
    for density in [0.20, 0.30]:
        r = run_eval(model_path, density, 5.0, 10.0, True, n_maps)
        print(f"  d={density:.2f}: success {r['success']:.2f}% | coll {r['coll']:.2f}% "
              f"(obstacle {r['coll_obstacle']:.2f}% | drone {r['coll_drone']:.2f}%) | timeout {r['timeout']:.2f}%")

if __name__ == "__main__":
    main()
