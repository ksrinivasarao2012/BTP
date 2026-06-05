import re

with open("swarm_env_step_B5_v15_master.py", "r") as f:
    code = f.read()

# 1. Rename class
code = code.replace("SwarmLidarEnv_v15_Final", "SwarmLidarEnv_v16_Final")
code = code.replace('"swarm_lidar_v15_final"', '"swarm_lidar_v16_final"')

# 2. Replace _ray_cast block
raycast_v14 = """    def _ray_cast(self, idx):
        \"\"\"16 sectors x 3 values (min_dist, dx, dy) = 48D.\"\"\"
        num_sectors = 16; rays_per_sector = 8; max_range = 8.0
        pos = self.positions[idx]; sector_width = (2 * np.pi) / num_sectors
        center_angles = np.arange(num_sectors) * sector_width
        offsets = np.linspace(-sector_width/2, sector_width/2, rays_per_sector, endpoint=False)
        angles = (center_angles[:, np.newaxis] + offsets).flatten()
        ray_dirs = np.stack([np.cos(angles), np.sin(angles)], axis=1) 
        min_dists = np.full(num_sectors * rays_per_sector, max_range, dtype=np.float32)

        for boundary, axis, direction in [(self.WIDTH, 0, 1), (0, 0, -1), (self.HEIGHT, 1, 1), (0, 1, -1)]:
            mask = ray_dirs[:, axis] * direction > 1e-6
            if np.any(mask):
                d = (boundary - pos[axis]) / ray_dirs[mask, axis]
                min_dists[mask] = np.minimum(min_dists[mask], np.where(d > 0, d, max_range).astype(np.float32))

        def intersect_circles(centers, radii):
            rel_pos = centers - pos; proj = rel_pos @ ray_dirs.T
            rel_pos_sq = np.sum(rel_pos**2, axis=1, keepdims=True); dist_to_ray_sq = rel_pos_sq - proj**2
            hit_mask = (proj > 0) & (dist_to_ray_sq < radii[:, np.newaxis]**2)
            if np.any(hit_mask):
                sqrt_arg = radii[:, np.newaxis]**2 - dist_to_ray_sq
                return np.min(np.where(hit_mask, proj - np.sqrt(np.maximum(sqrt_arg, 0)), max_range), axis=0)
            return np.full(num_sectors * rays_per_sector, max_range, dtype=np.float32)

        if len(self.obstacles) > 0:
            obs_array = np.array(self.obstacles, dtype=np.float32)
            min_dists = np.minimum(min_dists, intersect_circles(obs_array[:, :2], obs_array[:, 2] + self.drone_radius))

        others = [j for j in range(self.n_drones) if j != idx and f"drone_{j}" in self.agents]
        if others: min_dists = np.minimum(min_dists, intersect_circles(self.positions[others], np.full(len(others), 2.0 * self.drone_radius)))

        sector_res = min_dists.reshape(num_sectors, rays_per_sector)
        final_48 = np.zeros(48, dtype=np.float32)
        for s in range(num_sectors):
            m_d = np.min(sector_res[s])
            ang = center_angles[s]
            final_48[s*3 : (s*3)+3] = [m_d, m_d * np.cos(ang), m_d * np.sin(ang)]
        return final_48"""

# Regex to find the _ray_cast block in v15
import re
pattern = re.compile(r'    def _ray_cast\(self, idx\):.*?return readings', re.DOTALL)
code = pattern.sub(raycast_v14, code)

# 3. KEEP v15 scalings (s_pos / R_SENSOR_NORM, c_pos / R_COMM_NORM, s_vel / V_MAX_NORM, etc.)
# No replacements here since they are already R_SENSOR_NORM (8.0) and R_COMM_NORM (10.0) in v15!

# 4. In step(), remove the fm reward and change min indexing
step_repl1 = "ld = self.lidar_cache[a]; fm = (ld[31]+ld[16]+ld[17])/3.0; r += (fm/R_SENSOR_NORM)*0.2"
step_tgt1 = "ld = self.lidar_cache[a]"
code = code.replace(step_repl1, step_tgt1)

step_repl2 = "ml = np.min(ld[:16])"
step_tgt2 = "ml = np.min(ld[0::3])"
code = code.replace(step_repl2, step_tgt2)

# Also fix the glide fallback scaling logic in _observe
glide_repl = "min_sector = np.argmin(lidar_48[:16])"
glide_tgt = "min_sector = np.argmin(lidar_48[0::3])"
code = code.replace(glide_repl, glide_tgt)

with open("swarm_env_step_B5_v16_master.py", "w") as f:
    f.write(code)

print("v16 generated successfully with 8.0/10.0 scaling.")
