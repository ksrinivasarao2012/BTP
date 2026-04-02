import numpy as np
from pettingzoo import ParallelEnv
from gymnasium import spaces
from collections import deque
import math

# [V15 Master Vectorized Optimization - Hardened]
# This version combines high-performance NumPy broadcasting with IEEE-grade Trust metrics.
# Features: Vectorized LiDAR, Sigmoid LUT, Pairwise Distance Matrices.

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


class SwarmLidarEnv_v15_Final(ParallelEnv):
    metadata = {'render_modes': ['human'], "name": "swarm_lidar_v15_final"}

    def __init__(self, render_mode=None, target_density=0.20):
        super().__init__()
        self.render_mode  = render_mode
        self.target_density = target_density
        self.n_drones     = 10
        self.max_steps    = 800
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

    def set_curriculum(self, r_sensor: float, r_comm: float):
        self.current_r_sensor = float(r_sensor)
        self.current_r_comm = float(r_comm)

    def set_target_density(self, density: float):
        self.target_density = density

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
                # 52 dimensions per agent in critic input
                g_lid = self.lidar_cache.get(f"drone_{j}", self._ray_cast(j)) / R_SENSOR_NORM
                self.global_state[j * 52 : (j+1) * 52] = np.concatenate([
                    self.positions[j] / self.WIDTH,
                    self.velocities[j] / V_MAX_NORM,
                    g_lid
                ])

    def _ray_cast(self, idx):
        num_sectors, rays_per_sector = 16, 12
        num_rays = num_sectors * rays_per_sector
        max_range = R_SENSOR_NORM
        pos = self.positions[idx]
        
        sector_width = (2 * np.pi) / num_sectors
        center_angles = np.arange(num_sectors) * sector_width
        offsets = np.linspace(-sector_width/2, sector_width/2, rays_per_sector, endpoint=False)
        angles = (center_angles[:, np.newaxis] + offsets).flatten()
        
        ray_dirs = np.stack([np.cos(angles), np.sin(angles)], axis=1)
        min_dists = np.full(num_rays, max_range, dtype=np.float32)

        # Vectorized circle intersector
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

        # Boundaries
        for b, ax, side in [(self.WIDTH, 0, 1), (0, 0, -1), (self.HEIGHT, 1, 1), (0, 1, -1)]:
            mask = ray_dirs[:, ax] * side > 1e-6
            if np.any(mask):
                d = (b - pos[ax]) / ray_dirs[mask, ax]
                min_dists[mask] = np.minimum(min_dists[mask], np.where(d > 0, d, max_range).astype(np.float32))

        if self.obstacles:
            obs_array = np.array(self.obstacles)
            min_dists = np.minimum(min_dists, intersect_circles(obs_array[:, :2], obs_array[:, 2] + self.drone_radius))
        
        others = [j for j in range(self.n_drones) if j != idx and f"drone_{j}" in self.agents]
        if others:
            min_dists = np.minimum(min_dists, intersect_circles(self.positions[others], np.full(len(others), 2*self.drone_radius)))

        sector_res = min_dists.reshape(num_sectors, rays_per_sector)
        readings = np.zeros(num_sectors * 3, dtype=np.float32)
        readings[:num_sectors] = np.min(sector_res, axis=1)
        readings[num_sectors:2*num_sectors] = np.mean(sector_res, axis=1)
        readings[2*num_sectors:] = np.std(sector_res, axis=1)
        return readings

    def _observe(self, agent):
        idx = self.agent_name_mapping[agent]
        pos, vel = self.positions[idx], self.velocities[idx]
        dg = np.linalg.norm(self.goal - pos)
        ug = (self.goal - pos) / (dg + 1e-5)
        lidar_48 = self.lidar_cache.get(agent, self._ray_cast(idx))

        obs_self = np.concatenate([vel / V_MAX_NORM, ug, [dg / 28.28], [np.arctan2(vel[1], vel[0]) / np.pi]])
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
                    p_disc = np.linalg.norm(s_pos - c_pos) / R_SENSOR_NORM
                    v_disc = np.linalg.norm(s_vel - c_vel) / (2*V_MAX_NORM)
                    pos_discs.append(p_disc)

                slot[0:2] = s_pos / R_SENSOR_NORM
                slot[2:4] = s_vel / V_MAX_NORM
                slot[4] = is_vis
                slot[5:7] = c_pos / R_COMM_NORM
                slot[7:9] = c_vel / V_MAX_NORM
                slot[9], slot[10] = stag, is_comm
                slot[11], slot[12] = p_disc, v_disc
                slot[13] = 1.0 if (is_vis and is_comm) else (0.5 if is_vis else 0.0)
            neighbor_slots.append(slot)

        congestion = sum(1 for j in range(self.n_drones) if j != idx and f"drone_{j}" in self.agents and self.dist_matrix[idx, j] < 1.0) / self.n_drones
        self.position_history[agent].append(pos.copy())
        hist = list(self.position_history[agent])
        while len(hist) < 5: hist.insert(0, pos.copy())
        rel_hist = np.concatenate([(h - pos) / self.WIDTH for h in hist])

        m_p_disc = np.mean(pos_discs) if pos_discs else 0.0
        f_unv = (u_count / c_count) if c_count > 0 else 0.0
        obs_ctx = np.concatenate([rel_hist, [congestion], [m_p_disc], [f_unv]])
        
        obs_a = np.concatenate([obs_self, obs_lidar, np.concatenate(neighbor_slots), obs_ctx]).astype(np.float32)
        return np.concatenate([obs_a, self.global_state]).astype(np.float32)

    def _generate_obstacles(self, sc):
        target = (self.WIDTH * self.HEIGHT) * self.target_density; obs, cur = [], 0.0
        for _ in range(200):
            if cur >= target: break
            ch = np.random.random(); r = np.random.uniform(1.5, 2.5) if ch<0.2 else (np.random.uniform(0.6, 1.4) if ch<0.6 else np.random.uniform(0.2, 0.5))
            cx, cy = np.random.uniform(r, self.WIDTH-r), np.random.uniform(r, self.HEIGHT-r)
            if np.linalg.norm([cx,cy]-self.goal) <= r+2.0 or np.linalg.norm([cx,cy]-sc) <= r+1.65: continue
            if not any(np.linalg.norm([cx,cy]-np.array([ox,oy])) <= r+orad+0.5 for ox,oy,orad in obs):
                obs.append((cx, cy, r)); cur += np.pi * (r**2)
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
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nx, ny = x+dx, y+dy
                if 0<=nx<gs and 0<=ny<gs and grid[nx,ny] and (nx,ny) not in vis:
                    vis.add((nx,ny)); q.append((nx,ny))
        return False

    def reset(self, seed=None, options=None):
        self.agents, self.steps = self.possible_agents[:], 0
        self.infos = {a: {} for a in self.agents}
        self.steps_stagnant = {a: 0 for a in self.possible_agents}
        self.best_dist_to_goal = {a: 99.0 for a in self.possible_agents}
        self.position_history = {a: deque(maxlen=5) for a in self.possible_agents}
        self.last_actions = {a: np.zeros(2, dtype=np.float32) for a in self.possible_agents}
        
        self.goal = np.array(options["goal"]) if (options and "goal" in options) else np.array([np.random.uniform(2.0, 18.0), np.random.uniform(2.0, 18.0)])
        for _ in range(200):
            sc = np.random.uniform(2.0, 18.0, size=2)
            if np.linalg.norm(sc - self.goal) > 7.0: break
        else:
            # [FIX 1] Spawns exactly opposite the goal to prevent instant-wins
            sc = np.clip(np.array([self.WIDTH, self.HEIGHT]) - self.goal, 2.0, 18.0)
        self.start_center = sc

        for _ in range(50):
            self.obstacles = self._generate_obstacles(sc)
            if self._is_map_solvable(sc): break
        else: self.obstacles = []
        
        self.positions, self.velocities = np.zeros((self.n_drones, 2)), np.zeros((self.n_drones, 2))
        is_cl = np.random.random() < 0.5
        for i in range(self.n_drones):
            pl = False
            for _ in range(200):
                p = np.random.uniform(sc-1.5, sc+1.5, 2) if is_cl else np.random.uniform(1.0, 19.0, 2)
                if all(np.linalg.norm(p-self.positions[j]) >= 0.35 for j in range(i)) and all(np.linalg.norm(p-[ox,oy]) >= 0.2+orad for ox,oy,orad in self.obstacles):
                    self.positions[i], pl = p, True; break
            if not pl: self.positions[i] = np.clip(sc+np.random.uniform(-0.3, 0.3, 2), 0.3, 19.7)
        
        for a in self.agents: self.best_dist_to_goal[a] = np.linalg.norm(self.goal - self.positions[self.agent_name_mapping[a]])

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
            # [MICRO-OPT] math.exp is faster than np.exp for scalars
            mx = max(self.max_velocity * math.exp(-0.15 * nc), 0.75); sp = np.linalg.norm(self.velocities[idx])
            if sp > mx: self.velocities[idx] = (self.velocities[idx]/sp)*mx
            self.positions[idx] = np.clip(self.positions[idx] + self.velocities[idx]*self.dt, 0, 20.0)
        
        self.steps += 1
        self._compute_distance_matrix()
        self.lidar_cache = {a: self._ray_cast(self.agent_name_mapping[a]) for a in self.agents}
        self._prepare_global_state()
        
        rew, terms, truncs = {}, {}, {}
        for a in self.agents:
            idx, pos = self.agent_name_mapping[a], self.positions[idx]
            dg, sp = np.linalg.norm(self.goal-pos), np.linalg.norm(self.velocities[idx])
            ug = (self.goal-pos)/(dg+1e-6); r = 100.0*(np.linalg.norm(self.goal-old_p[idx])-dg)-0.25
            al = np.dot(self.velocities[idx]/(sp+1e-6), ug)
            if dg < self.best_dist_to_goal[a]-0.1: self.best_dist_to_goal[a], self.steps_stagnant[a] = dg, 0
            elif sp > 0.5 and al < 0.2: self.steps_stagnant[a] = max(0, self.steps_stagnant[a]-1)
            else: self.steps_stagnant[a] += 1
            if self.steps_stagnant[a] > 50: r -= min((self.steps_stagnant[a]-50)*0.25, 25.0)

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
                        # [FIX 2] Reduced to 0.2 to prevent proximity conflict
                        r += 0.2 * c_sim * max(0.0, al)

            if a in self.last_actions: r -= 0.05 * np.linalg.norm(act - self.last_actions[a])**2
            self.last_actions[a] = act.copy()
            ld = self.lidar_cache[a]; fm = (ld[31]+ld[16]+ld[17])/3.0; r += (fm/R_SENSOR_NORM)*0.2
            ml = np.min(ld[:16])
            if ml < 0.15: r -= ((0.15-ml)/0.15)**2

            hw = min(pos[0], 20-pos[0], pos[1], 20-pos[1]) <= 0.05
            ho = any(np.linalg.norm(pos-[ox,oy]) < 0.15+orad for ox,oy,orad in self.obstacles)
            hd = any(self.dist_matrix[idx,j] < 0.3 for j in range(self.n_drones) if j!=idx and f"drone_{j}" in self.agents)
            
            if hw or ho or hd:
                r, terms[a] = -500.0, True; self.infos[a]["cause"] = "collision"
            elif dg < 0.75:
                r += 500.0 + (100.0/(1.0+sp))
                terms[a], self.infos[a]["cause"] = True, "success"
            else: terms[a] = False
            rew[a], truncs[a] = float(r), self.steps >= self.max_steps
        
        obs = {a: self._observe(a) for a in self.agents}
        for a in list(self.agents):
            if terms.get(a, False) or truncs.get(a, False):
                self.positions[self.agent_name_mapping[a]] = np.array([-100.0, -100.0])
                self.agents.remove(a)
        return obs, rew, terms, truncs, self.infos

    def close(self): pass