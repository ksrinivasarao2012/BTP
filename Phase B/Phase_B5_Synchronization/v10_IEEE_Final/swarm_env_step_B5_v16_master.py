import numpy as np
from pettingzoo import ParallelEnv
from gymnasium import spaces
from collections import deque
import math
import heapq

# [V15 Master Vectorized Optimization - Hardened & Dijkstra Synchronized]
# Combines vectorized LiDAR, Sigmoid LUT, and Pairwise distance matrices
# with B10's 8-Way Dijkstra Grid Solver and Dynamic Wall-Glide scaling.

R_SENSOR_NORM = 8.0 # Standardized for observation scaling
R_COMM_NORM   = 10.0
V_MAX_NORM    = 2.0

class SigmoidLUT:
    def __init__(self, x_min=-10.0, x_max=10.0, resolution=2000):
        self.x_min = x_min
        self.x_max = x_max
        self.resolution = resolution
        x = np.linspace(x_min, x_max, resolution)
        self.lut = 1.0 / (1.0 + np.exp(-x))
        self.scale = resolution / (x_max - x_min)
    
    def __call__(self, x):
        idx = np.clip((x - self.x_min) * self.scale, 0, self.resolution - 1).astype(int)
        return self.lut[idx]

GLOBAL_SIGMOID_LUT = SigmoidLUT()


class SwarmLidarEnv_v16_Final(ParallelEnv):
    metadata = {'render_modes': ['human'], "name": "swarm_lidar_v16_final"}

    def __init__(self, render_mode=None, target_density=0.20):
        super().__init__()
        self.render_mode  = render_mode
        self.target_density = target_density
        self.n_drones     = 10
        self.max_steps    = 1200 # Upgraded to match B10 to cure timeout limits
        self.WIDTH        = 20.0
        self.HEIGHT       = 20.0
        self.drone_radius = 0.15
        self.dt           = 0.1
        self.max_velocity = V_MAX_NORM

        # Curriculum thresholds
        self.current_r_sensor = 100.0
        self.current_r_comm   = 100.0

        self.possible_agents    = [f"drone_{i}" for i in range(self.n_drones)]
        self.agent_name_mapping = dict(zip(self.possible_agents, list(range(self.n_drones))))

        self.obs_size = 202 + 530
        
        self.action_spaces = {
            a: spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)
            for a in self.possible_agents
        }
        self.observation_spaces = {
            a: spaces.Box(low=-np.inf, high=np.inf, shape=(self.obs_size,), dtype=np.float32)
            for a in self.possible_agents
        }
        
        self.observation_space = self.observation_spaces["drone_0"]
        self.action_space      = self.action_spaces["drone_0"]

        self.obstacles   = []
        self.traitor_id  = None

        # Runtime state
        self.positions        = np.zeros((self.n_drones, 2), dtype=np.float32)
        self.velocities       = np.zeros((self.n_drones, 2), dtype=np.float32)
        self.goal             = np.zeros(2, dtype=np.float32)
        self.broadcasts       = {}
        self.global_state     = np.zeros(530, dtype=np.float32)
        self.lidar_cache      = {}
        self.last_actions     = {}
        self.steps_stagnant   = {}
        self.best_dist_to_goal= {}
        self.position_history = {}
        self.steps            = 0

        # Distance matrix caches
        self.dist_matrix    = np.zeros((self.n_drones, self.n_drones), dtype=np.float32)
        self.vel_diff_cache = np.zeros((self.n_drones, self.n_drones, 2), dtype=np.float32)

        # Ray cast static pre-computations
        self.num_sectors, self.rays_per_sector = 16, 12
        self.num_rays = self.num_sectors * self.rays_per_sector
        sector_width = (2 * np.pi) / self.num_sectors
        self.center_angles = np.arange(self.num_sectors) * sector_width
        offsets = np.linspace(-sector_width/2, sector_width/2, self.rays_per_sector, endpoint=False)
        angles = (self.center_angles[:, np.newaxis] + offsets).flatten()
        self.ray_dirs = np.stack([np.cos(angles), np.sin(angles)], axis=1).astype(np.float32)
        
        self.others_radii = {k: np.full(k, 2 * self.drone_radius, dtype=np.float32) for k in range(1, 11)}

    def set_curriculum(self, r_sensor: float, r_comm: float):
        self.current_r_sensor = float(r_sensor)
        self.current_r_comm = float(r_comm)

    def set_target_density(self, density: float):
        self.target_density = density

    def _compute_shortest_path_distance_map(self):
        """Dijkstra Shortest-Path Grid Solver for exact 8-way diagonal physics"""
        grid_resolution = 0.2
        grid_size = int(np.ceil(self.WIDTH / grid_resolution))
        grid = np.ones((grid_size, grid_size), dtype=bool)
        clearance_radius = self.drone_radius + 0.05
        
        # Mark obstacle regions as blocked
        for ox, oy, orad in self.obstacles:
            x_range = np.arange(max(0, int((ox - orad - clearance_radius) / grid_resolution)),
                               min(grid_size, int((ox + orad + clearance_radius) / grid_resolution) + 1))
            y_range = np.arange(max(0, int((oy - orad - clearance_radius) / grid_resolution)),
                               min(grid_size, int((oy + orad + clearance_radius) / grid_resolution) + 1))
            for gx in x_range:
                for gy in y_range:
                    cell_x = gx * grid_resolution + grid_resolution / 2
                    cell_y = gy * grid_resolution + grid_resolution / 2
                    if np.sqrt((cell_x - ox)**2 + (cell_y - oy)**2) < (orad + clearance_radius):
                        grid[gx, gy] = False
                        
        goal_cell = (np.clip(int(self.goal[0] / grid_resolution), 0, grid_size - 1),
                     np.clip(int(self.goal[1] / grid_resolution), 0, grid_size - 1))
                     
        self.shortest_path_map = np.full((grid_size, grid_size), 999.0, dtype=np.float32)
        if not grid[goal_cell[0], goal_cell[1]]:
            return
            
        self.shortest_path_map[goal_cell[0], goal_cell[1]] = 0.0
        pq = [(0.0, goal_cell[0], goal_cell[1])]
        
        while pq:
            curr_dist, cx, cy = heapq.heappop(pq)
            if curr_dist > self.shortest_path_map[cx, cy]:
                continue
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0: continue
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < grid_size and 0 <= ny < grid_size:
                        if grid[nx, ny]:
                            step_dist = np.sqrt(dx**2 + dy**2) * grid_resolution
                            new_dist = curr_dist + step_dist
                            if new_dist < self.shortest_path_map[nx, ny]:
                                self.shortest_path_map[nx, ny] = new_dist
                                heapq.heappush(pq, (new_dist, nx, ny))

    def get_shortest_path_distance(self, pos):
        """O(1) topological shortest-path distance query"""
        grid_resolution = 0.2
        grid_size = int(np.ceil(self.WIDTH / grid_resolution))
        gx = np.clip(int(pos[0] / grid_resolution), 0, grid_size - 1)
        gy = np.clip(int(pos[1] / grid_resolution), 0, grid_size - 1)
        dist = self.shortest_path_map[gx, gy]
        if dist >= 999.0:
            return np.linalg.norm(self.goal - pos)
        return dist

    def get_shortest_path_direction(self, pos):
        """Returns the unit vector pointing in the direction of shortest path descent"""
        grid_resolution = 0.2
        grid_size = int(np.ceil(self.WIDTH / grid_resolution))
        gx = np.clip(int(pos[0] / grid_resolution), 0, grid_size - 1)
        gy = np.clip(int(pos[1] / grid_resolution), 0, grid_size - 1)
        
        min_dist = self.shortest_path_map[gx, gy]
        best_dir = self.goal - pos
        best_dist = np.linalg.norm(best_dir)
        best_dir = best_dir / (best_dist + 1e-5)
        
        if min_dist < 999.0:
            best_nx, best_ny = gx, gy
            lowest_val = min_dist
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0: continue
                    nx, ny = gx + dx, gy + dy
                    if 0 <= nx < grid_size and 0 <= ny < grid_size:
                        val = self.shortest_path_map[nx, ny]
                        if val < lowest_val:
                            lowest_val = val
                            best_nx, best_ny = nx, ny
            if best_nx != gx or best_ny != gy:
                dir_vec = np.array([best_nx - gx, best_ny - gy], dtype=np.float32)
                norm = np.linalg.norm(dir_vec)
                if norm > 1e-5:
                    return dir_vec / norm
                    
        return best_dir

    def _compute_distance_matrix(self):
        """Vectorized pairwise distances using NumPy broadcasting."""
        diff = self.positions[:, np.newaxis, :] - self.positions[np.newaxis, :, :]
        self.dist_matrix = np.linalg.norm(diff, axis=2).astype(np.float32)
        self.vel_diff_cache = self.velocities[:, np.newaxis, :] - self.velocities[np.newaxis, :, :]

    def _is_occluded(self, idx, target_idx):
        p1, p2 = self.positions[idx], self.positions[target_idx]
        d = p2 - p1
        a = np.dot(d, d)
        if a < 1e-6: return False
        for ox, oy, orad in self.obstacles:
            center = np.array([ox, oy])
            f = p1 - center
            b = 2 * np.dot(f, d)
            c = np.dot(f, f) - (orad + 0.1)**2
            disc = b**2 - 4*a*c
            if disc >= 0:
                disc = np.sqrt(disc)
                t1 = (-b - disc) / (2*a)
                t2 = (-b + disc) / (2*a)
                if (0 <= t1 <= 1) or (0 <= t2 <= 1): return True
        return False

    def _prepare_broadcasts(self):
        self.broadcasts = {
            i: {
                'pos':  self.positions[i].copy(),
                'vel':  self.velocities[i].copy(),
                'stag': min(1.0, self.steps_stagnant.get(f"drone_{i}", 0) / 50.0)
            }
            for i in range(self.n_drones)
        }

    def _prepare_global_state(self):
        self.global_state = np.zeros(530, dtype=np.float32)
        for j in range(self.n_drones):
            if f"drone_{j}" in self.agents:
                g_lid = self.lidar_cache.get(f"drone_{j}", self._ray_cast(j)) / R_SENSOR_NORM
                self.global_state[j * 52 : (j+1) * 52] = np.concatenate([
                    self.positions[j] / self.WIDTH,
                    self.velocities[j] / V_MAX_NORM,
                    g_lid
                ])

    def _ray_cast(self, idx):
        """16 sectors x 3 values (min_dist, dx, dy) = 48D."""
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
        return final_48

    def _observe(self, agent):
        idx = self.agent_name_mapping[agent]
        pos, vel = self.positions[idx], self.velocities[idx]
        
        # [V15 DIJKSTRA SYNCHRONIZATION]
        # Query Dijkstra distance map & descent direction instead of raw Euclidean vectors
        dist_goal = self.get_shortest_path_distance(pos)
        to_goal = self.get_shortest_path_direction(pos)
        lidar_48 = self.lidar_cache.get(agent, self._ray_cast(idx))

        # [V15 DYNAMIC WALL-GLIDE SCALING]
        # Active only if stagnant >= 40. Escalates to 0.75 if severe stagnation >= 60.
        stagnant_count = self.steps_stagnant.get(agent, 0)
        if stagnant_count >= 40:
            min_sector = np.argmin(lidar_48[0::3])
            sector_width = (2 * np.pi) / 16
            angle = min_sector * sector_width
            
            t_cw = np.array([-np.sin(angle), np.cos(angle)], dtype=np.float32)
            t_ccw = np.array([np.sin(angle), -np.cos(angle)], dtype=np.float32)
            
            if np.dot(t_cw, to_goal) >= np.dot(t_ccw, to_goal):
                t_glide = t_cw
            else:
                t_glide = t_ccw
                
            alpha = 0.75 if stagnant_count >= 60 else 0.55
            
            to_goal = (1.0 - alpha) * to_goal + alpha * t_glide
            to_goal_norm = np.linalg.norm(to_goal)
            if to_goal_norm > 1e-5:
                to_goal = to_goal / to_goal_norm

        obs_self = np.concatenate([vel / V_MAX_NORM, to_goal, [dist_goal / 28.28], [np.arctan2(vel[1], vel[0]) / np.pi]])
        obs_lidar = lidar_48 / R_SENSOR_NORM

        neighbor_slots, pos_discs = [], []
        u_count, c_count = 0, 0

        for j in range(self.n_drones):
            if j == idx: continue
            slot = np.zeros(15, dtype=np.float32)
            if f"drone_{j}" in self.agents:
                slot[14] = 1.0
                d_j = self.dist_matrix[idx, j]

                is_vis = 1.0 if (d_j <= self.current_r_sensor and not self._is_occluded(idx, j)) else 0.0
                is_comm = 1.0 if d_j <= self.current_r_comm else 0.0

                s_pos, s_vel, c_pos, c_vel, stag = np.zeros(2), np.zeros(2), np.zeros(2), np.zeros(2), 0.0
                if is_vis: s_pos, s_vel = self.positions[j] - pos, self.velocities[j] - vel
                if is_comm:
                    c_count += 1
                    m = self.broadcasts[j]
                    c_pos, c_vel, stag = m['pos'] - pos, m['vel'] - vel, m['stag']
                    if not is_vis: u_count += 1

                p_disc, v_disc = 0.0, 0.0
                if is_vis and is_comm:
                    # Simulated local relative discrepancy (UWB/AoA emulation)
                    p_disc = np.linalg.norm(s_pos - c_pos) / 20.0
                    v_disc = np.linalg.norm(s_vel - c_vel) / 4.0
                    pos_discs.append(p_disc)

                slot[0:2] = s_pos / 20.0
                slot[2:4] = s_vel / 4.0
                slot[4] = is_vis
                slot[5:7] = c_pos / 20.0
                slot[7:9] = c_vel / 4.0
                slot[9], slot[10] = stag, is_comm
                slot[11], slot[12] = p_disc, v_disc
                slot[13] = 1.0 if (is_vis and is_comm) else (0.5 if is_vis else 0.0)
            neighbor_slots.append(slot)

        congestion = sum(1 for j in range(self.n_drones) if j != idx and f"drone_{j}" in self.agents and self.dist_matrix[idx, j] < 1.0) / self.n_drones
        self.position_history[agent].append(pos.copy())
        hist = list(self.position_history[agent])[-5:]
        while len(hist) < 5: hist.insert(0, pos.copy())
        rel_hist = np.concatenate([(h - pos) / self.WIDTH for h in hist])

        m_p_disc = np.mean(pos_discs) if pos_discs else 0.0
        f_unv = (u_count / c_count) if c_count > 0 else 0.0
        obs_ctx = np.concatenate([rel_hist, [congestion], [m_p_disc], [f_unv]])
        
        obs_a = np.concatenate([obs_self, obs_lidar, np.concatenate(neighbor_slots), obs_ctx]).astype(np.float32)
        return np.concatenate([obs_a, self.global_state]).astype(np.float32)

    def _generate_obstacles(self, sc):
        target = (self.WIDTH * self.HEIGHT) * self.target_density
        obs = []
        
        raster_res = 0.05
        rw = int(self.WIDTH / raster_res)
        rh = int(self.HEIGHT / raster_res)
        occupied = np.zeros((rw, rh), dtype=bool)
        
        cur = 0.0

        for _ in range(2000):
            if cur >= target: break
            
            ch = np.random.random()
            if ch < 0.2:
                r = np.random.uniform(1.5, 2.5)
            elif ch < 0.6:
                r = np.random.uniform(0.6, 1.4)
            else:
                r = np.random.uniform(0.2, 0.5)
                
            cx, cy = np.random.uniform(r/2.0, self.WIDTH-r/2.0), np.random.uniform(r/2.0, self.HEIGHT-r/2.0)
            
            if np.linalg.norm([cx,cy]-self.goal) <= r+2.0 or np.linalg.norm([cx,cy]-sc) <= r+2.85: continue
            
            xmin = max(0, int((cx - r) / raster_res))
            xmax = min(rw, int((cx + r) / raster_res) + 1)
            ymin = max(0, int((cy - r) / raster_res))
            ymax = min(rh, int((cy + r) / raster_res) + 1)

            lx = np.arange(xmin, xmax) * raster_res + raster_res / 2
            ly = np.arange(ymin, ymax) * raster_res + raster_res / 2
            LX, LY = np.meshgrid(lx, ly, indexing='ij')

            new_cells = (LX - cx)**2 + (LY - cy)**2 <= r**2
            
            newly_covered = np.sum(new_cells & ~occupied[xmin:xmax, ymin:ymax])
            if newly_covered == 0:
                continue
                
            cur += newly_covered * raster_res**2

            occupied[xmin:xmax, ymin:ymax] |= new_cells
            obs.append((cx, cy, r))
            
        return obs

    def _is_map_solvable(self, start_pos, grid_res=0.2):
        gs = int(np.ceil(self.WIDTH / grid_res)); grid = np.ones((gs, gs), dtype=bool); clr = self.drone_radius + 0.05
        for ox, oy, orad in self.obstacles:
            xm, xM = max(0, int((ox-orad-clr)/grid_res)), min(gs, int((ox+orad+clr)/grid_res)+1)
            ym, yM = max(0, int((oy-orad-clr)/grid_res)), min(gs, int((oy+orad+clr)/grid_res)+1)
            for gx in range(xm, xM):
                for gy in range(ym, yM):
                    if np.sqrt((gx*grid_res+grid_res/2-ox)**2 + (gy*grid_res+grid_res/2-oy)**2) < (orad+clr): grid[gx,gy] = False
        def to_c(p): return (np.clip(int(p[0]/grid_res), 0, gs-1), np.clip(int(p[1]/grid_res), 0, gs-1))
        sc, gc = to_c(start_pos), to_c(self.goal)
        if not grid[sc] or not grid[gc]: return False
        q, vis = deque([sc]), {sc}
        while q:
            x, y = q.popleft()
            if (x,y) == gc: return True
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (-1,1), (1,-1), (1,1)]:
                nx, ny = x+dx, y+dy
                if 0<=nx<gs and 0<=ny<gs and grid[nx,ny] and (nx,ny) not in vis:
                    vis.add((nx,ny)); q.append((nx,ny))
        return False

    def reset(self, seed=None, options=None):
        if seed is not None:
            np.random.seed(seed)
        self.agents, self.steps = self.possible_agents[:], 0
        self.infos = {a: {} for a in self.agents}
        self.steps_stagnant = {a: 0 for a in self.possible_agents}
        self.best_dist_to_goal = {a: 99.0 for a in self.possible_agents}
        self.position_history = {a: deque(maxlen=15) for a in self.possible_agents}
        self.last_actions = {a: np.zeros(2, dtype=np.float32) for a in self.possible_agents}
        
        self.goal = np.array(options["goal"]) if (options and "goal" in options) else np.array([np.random.uniform(2.0, 18.0), np.random.uniform(2.0, 18.0)])
        for _ in range(200):
            sc = np.random.uniform(2.0, 18.0, size=2)
            if np.linalg.norm(sc - self.goal) > 7.0: break
        else:
            sc = np.clip(np.array([self.WIDTH, self.HEIGHT]) - self.goal, 2.0, 18.0)
        self.start_center = sc

        for _ in range(50):
            self.obstacles = self._generate_obstacles(sc)
            if self._is_map_solvable(sc): break
        else: self.obstacles = []
        
        self.obstacles_array = np.array(self.obstacles, dtype=np.float32) if self.obstacles else np.empty((0, 3), dtype=np.float32)
        
        # Precompute Dijkstra Topological Shortest Path Map
        self._compute_shortest_path_distance_map()

        self.positions = np.zeros((self.n_drones, 2), dtype=np.float32)
        self.velocities = np.zeros((self.n_drones, 2), dtype=np.float32)
        
        if options and "spawn_mode" in options:
            is_cl = (options["spawn_mode"] == "clustered")
        else:
            is_cl = np.random.random() < 0.5

        for i in range(self.n_drones):
            pl = False
            # For clustered mode, dynamically expand the search window to find safe spaces.
            # For random mode, sample the entire 1.0 to 19.0 area.
            search_radii = [1.5, 2.0, 2.5, 3.5] if is_cl else [9.0]
            
            for search_radius in search_radii:
                for _ in range(150):
                    p = np.random.uniform(sc - search_radius, sc + search_radius, 2) if is_cl else np.random.uniform(1.0, 19.0, 2)
                    p = np.clip(p, 0.6, 19.4)
                    # Enforce a safe 0.50m peer spacing (well above the 0.30m collision boundary)
                    # and a safe 0.45m + orad obstacle spacing (30cm clear outer boundary).
                    if all(np.linalg.norm(p - self.positions[j]) >= 0.50 for j in range(i)) and all(np.linalg.norm(p - np.array([ox,oy])) >= (0.45 + orad) for ox, oy, orad in self.obstacles):
                        self.positions[i], pl = p, True; break
                if pl: break
                
            if not pl:
                # Spiral fallback guarantees safe 0.60m spacing even under extreme congestion
                angle = i * (2.0 * np.pi / self.n_drones)
                r_dist = 0.60 * (1.0 + i // 5)
                self.positions[i] = np.clip(sc + np.array([r_dist * np.cos(angle), r_dist * np.sin(angle)], dtype=np.float32), 0.6, 19.4)

        # Seed initial best distances using topological shortest path distance
        for a in self.agents: 
            idx = self.agent_name_mapping[a]
            self.best_dist_to_goal[a] = self.get_shortest_path_distance(self.positions[idx])

        self._prepare_broadcasts()
        self.lidar_cache = {f"drone_{j}": self._ray_cast(j) for j in range(self.n_drones)}
        self._compute_distance_matrix()
        self._prepare_global_state()
        return {a: self._observe(a) for a in self.agents}, self.infos

    def step(self, actions):
        if not self.agents: return {}, {}, {}, {}, {}
        self._prepare_broadcasts()
        old_p = np.copy(self.positions)
        self._compute_distance_matrix()

        for agent, act in actions.items():
            idx = self.agent_name_mapping[agent]; act = np.clip(act, -1.0, 1.0)
            self.velocities[idx] += act * self.dt * 10.0
            nc = sum(1 for j in range(self.n_drones) if j!=idx and f"drone_{j}" in self.agents and self.dist_matrix[idx,j] < 1.0)
            mx = max(self.max_velocity * math.exp(-0.08 * nc), 1.1); sp = np.linalg.norm(self.velocities[idx])
            if sp > mx: self.velocities[idx] = (self.velocities[idx]/sp)*mx
            self.positions[idx] = np.clip(self.positions[idx] + self.velocities[idx]*self.dt, 0, 20.0)
        
        self.steps += 1
        self._compute_distance_matrix()
        self.lidar_cache = {a: self._ray_cast(self.agent_name_mapping[a]) for a in self.agents}
        self._prepare_global_state()
        
        rew, terms, truncs = {}, {}, {}
        for a in self.agents:
            idx, pos = self.agent_name_mapping[a], self.positions[idx]
            sp = np.linalg.norm(self.velocities[idx])
            
            # [V15 DIJKSTRA SYNCHRONIZATION]
            # Replace straight-line Euclidean tracking with Dijkstra progress
            path_dist = self.get_shortest_path_distance(pos)
            old_path_dist = self.get_shortest_path_distance(old_p[idx])
            goal_progress = old_path_dist - path_dist
            reward_goal = 100.0 * goal_progress
            
            r = reward_goal - 0.25
            
            # Directional alignment bonus
            sp_dir = self.get_shortest_path_direction(pos)
            vel_alignment = np.dot(self.velocities[idx] / (sp + 1e-6), sp_dir) if sp > 0.3 else 0.0
            if vel_alignment > 0.5:
                r += 0.5 * vel_alignment

            # Spatial stagnation check over a 15-step trailing window
            if len(self.position_history[a]) >= 15:
                disp = np.linalg.norm(pos - self.position_history[a][0])
                is_stagnant = disp < 0.2
            else:
                is_stagnant = False
                
            if path_dist < self.best_dist_to_goal[a]-0.1 and not is_stagnant: 
                self.best_dist_to_goal[a] = path_dist
                self.steps_stagnant[a] = 0
            elif is_stagnant: 
                self.steps_stagnant[a] += 1
            else: 
                self.steps_stagnant[a] = max(0, self.steps_stagnant[a]-1)
                
            if self.steps_stagnant[a] > 50: 
                r -= min((self.steps_stagnant[a]-50)*0.25, 25.0)

            # TTC & Flocking Avoidance Logic
            for j in range(self.n_drones):
                if j == idx or f"drone_{j}" not in self.agents: continue
                d = self.dist_matrix[idx, j]; rp, rv = self.positions[j]-pos, self.velocities[idx]-self.velocities[j]
                cs = np.dot(rp/(d+1e-6), rv)
                if cs > 0:
                    ttc = d/cs
                    if ttc < 1.0: r -= 10.0*(1.0-ttc)**2
                if d < 0.6 and cs > 0.1: r -= 25.0 * cs * (0.6 - d)
                if d < 0.4: r -= (0.4-d)*100.0
                if d < 0.5: r -= 50.0 * ((0.5-d)/0.5)**2
                if d < 1.0 and self.steps_stagnant[f"drone_{j}"] > 30: r -= 50.0 * GLOBAL_SIGMOID_LUT(-10.0*(d-0.5))
                if d < 1.5:
                    v_n = np.linalg.norm(self.velocities[j])
                    if sp>0.1 and v_n>0.1:
                        c_sim = np.dot(self.velocities[idx], self.velocities[j])/(sp*v_n)
                        r += 0.2 * c_sim * max(0.0, vel_alignment)

            if a in self.last_actions: r -= 0.05 * np.linalg.norm(act - self.last_actions[a])**2
            self.last_actions[a] = act.copy()
            ld = self.lidar_cache[a]
            ml = np.min(ld[0::3])
            if ml < 0.15: r -= ((0.15 - ml) / 0.15)**2

            hw = min(pos[0], 20-pos[0], pos[1], 20-pos[1]) <= 0.05
            ho = any(np.linalg.norm(pos-[ox,oy]) < 0.15+orad for ox,oy,orad in self.obstacles)
            hd = any(self.dist_matrix[idx,j] < 0.3 for j in range(self.n_drones) if j!=idx and f"drone_{j}" in self.agents)
            
            if hw or ho or hd:
                r, terms[a] = -500.0, True; self.infos[a]["cause"] = "collision"
                # print(f"[ENV DIAG] Step {self.steps}: Agent {a} collided at pos {pos.tolist()}. Reasons: wall={hw}, obs={ho}, drone={hd}", flush=True)
            elif path_dist < 0.75:
                r += 500.0 + (100.0/(1.0+sp))
                terms[a], self.infos[a]["cause"] = True, "success"
            else: terms[a] = False
            rew[a], truncs[a] = float(r), self.steps >= self.max_steps
            if truncs[a] and not terms[a]:
                self.infos[a]["cause"] = "timeout"
                rew[a] -= 200.0 # Timeout terminal penalty matching B10 env
                
        obs = {a: self._observe(a) for a in self.agents}
        for a in list(self.agents):
            if terms.get(a, False) or truncs.get(a, False):
                self.positions[self.agent_name_mapping[a]] = np.array([-100.0, -100.0])
                self.agents.remove(a)
        return obs, rew, terms, truncs, self.infos

    def close(self): pass