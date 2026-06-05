import numpy as np
from pettingzoo import ParallelEnv
from gymnasium import spaces
from collections import deque
import math
import pygame

# [V15 Master Vectorized Optimization + STIGMERGY UPGRADE]
R_SENSOR_NORM = 8.0
R_COMM_NORM   = 10.0
V_MAX_NORM    = 2.0

class SigmoidLUT:
    def __init__(self, x_min=-10.0, x_max=10.0, resolution=2000):
        self.x_min, self.x_max, self.resolution = x_min, x_max, resolution
        x = np.linspace(x_min, x_max, resolution)
        self.lut = 1.0 / (1.0 + np.exp(-x))
        self.scale = resolution / (x_max - x_min)
    def __call__(self, x):
        idx = np.clip((x - self.x_min) * self.scale, 0, self.resolution - 1).astype(int)
        return self.lut[idx]

GLOBAL_SIGMOID_LUT = SigmoidLUT()

class SwarmStigmergyEnv(ParallelEnv):
    metadata = {'render_modes': ['human'], "name": "swarm_stigmergy_v15"}

    def __init__(self, render_mode=None, target_density=0.20, stagnation_limit=40, breadcrumb_lifetime=250, repulsion_scale=2.0, sensing_radius=5.0):
        super().__init__()
        self.render_mode = render_mode
        self.target_density = target_density
        self.stagnation_limit = stagnation_limit
        self.breadcrumb_lifetime = breadcrumb_lifetime
        self.repulsion_scale = repulsion_scale
        self.sensing_radius = sensing_radius
        self.n_drones = 10
        self.max_steps = 800
        self.WIDTH, self.HEIGHT = 20.0, 20.0
        self.drone_radius = 0.15
        self.dt = 0.1
        self.max_velocity = V_MAX_NORM
        self.current_r_sensor, self.current_r_comm = 100.0, 100.0

        self.possible_agents = [f"drone_{i}" for i in range(self.n_drones)]
        self.agent_name_mapping = {a: i for i, a in enumerate(self.possible_agents)}

        # [STIGMERGY] Base B5 Local = 202. Adding Breadcrumb (2) = 204. Global = 530.
        self.obs_size = 204 + 530
        
        self.action_spaces = {a: spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32) for a in self.possible_agents}
        self.observation_spaces = {a: spaces.Box(low=-np.inf, high=np.inf, shape=(self.obs_size,), dtype=np.float32) for a in self.possible_agents}
        self.observation_space, self.action_space = self.observation_spaces["drone_0"], self.action_spaces["drone_0"]

        self.obstacles = []
        self.positions = np.zeros((self.n_drones, 2), dtype=np.float32)
        self.velocities = np.zeros((self.n_drones, 2), dtype=np.float32)
        self.goal = np.zeros(2, dtype=np.float32)
        self.broadcasts = {}
        self.global_state = np.zeros(530, dtype=np.float32)
        self.lidar_cache, self.last_actions = {}, {}
        self.steps_stagnant, self.best_dist_to_goal = {}, {}
        self.position_history = {}
        self.steps = 0
        self.dist_matrix = np.zeros((self.n_drones, self.n_drones), dtype=np.float32)
        self.vel_diff_cache = np.zeros((self.n_drones, self.n_drones, 2), dtype=np.float32)

        # [STIGMERGY STATE]
        self.breadcrumbs = [] # list of ((x, y), lifetime)
        self.screen = None

    def _compute_distance_matrix(self):
        diff = self.positions[:, np.newaxis, :] - self.positions[np.newaxis, :, :]
        self.dist_matrix = np.linalg.norm(diff, axis=2).astype(np.float32)
        self.vel_diff_cache = self.velocities[:, np.newaxis, :] - self.velocities[np.newaxis, :, :]

    def _is_occluded(self, idx, target_idx):
        p1, p2 = self.positions[idx], self.positions[target_idx]
        d = p2 - p1
        a = np.dot(d, d)
        if a < 1e-6: return False
        for ox, oy, orad in self.obstacles:
            f = p1 - np.array([ox, oy])
            b = 2 * np.dot(f, d); c = np.dot(f, f) - (orad + 0.1)**2
            disc = b**2 - 4*a*c
            if disc >= 0:
                disc = np.sqrt(disc)
                if 0 <= (-b - disc)/(2*a) <= 1 or 0 <= (-b + disc)/(2*a) <= 1: return True
        return False

    def _prepare_broadcasts(self):
        self.broadcasts = {i: {'pos': self.positions[i].copy(), 'vel': self.velocities[i].copy(), 'stag': min(1.0, self.steps_stagnant.get(f"drone_{i}", 0) / 50.0)} for i in range(self.n_drones)}

    def _prepare_global_state(self):
        self.global_state = np.zeros(530, dtype=np.float32)
        for j in range(self.n_drones):
            if f"drone_{j}" in self.agents:
                g_lid = self.lidar_cache.get(f"drone_{j}", self._ray_cast(j)) / R_SENSOR_NORM
                self.global_state[j*52 : (j+1)*52] = np.concatenate([self.positions[j]/self.WIDTH, self.velocities[j]/V_MAX_NORM, g_lid])

    def _ray_cast(self, idx):
        num_sectors, rays_per_sector = 16, 12
        max_range = R_SENSOR_NORM
        pos = self.positions[idx]
        angles = (np.arange(16)[:, None] * (2*np.pi/16) + np.linspace(-np.pi/16, np.pi/16, 12, endpoint=False)).flatten()
        ray_dirs = np.stack([np.cos(angles), np.sin(angles)], axis=1)
        min_dists = np.full(192, max_range, dtype=np.float32)

        def intersect_circles(centers, radii):
            rel_pos = centers - pos; proj = rel_pos @ ray_dirs.T
            dist_to_ray_sq = np.sum(rel_pos**2, axis=1, keepdims=True) - proj**2
            hit_mask = (proj > 0) & (dist_to_ray_sq < radii[:, None]**2)
            if np.any(hit_mask):
                dists = proj - np.sqrt(np.maximum(radii[:, None]**2 - dist_to_ray_sq, 0))
                dists[~hit_mask] = max_range
                return np.min(dists, axis=0)
            return np.full(192, max_range, dtype=np.float32)

        for b, ax, side in [(self.WIDTH, 0, 1), (0, 0, -1), (self.HEIGHT, 1, 1), (0, 1, -1)]:
            mask = ray_dirs[:, ax] * side > 1e-6
            if np.any(mask):
                d = (b - pos[ax]) / ray_dirs[mask, ax]
                min_dists[mask] = np.minimum(min_dists[mask], np.where(d > 0, d, max_range).astype(np.float32))

        if self.obstacles:
            obs = np.array(self.obstacles)
            min_dists = np.minimum(min_dists, intersect_circles(obs[:, :2], obs[:, 2] + self.drone_radius))
        
        others = [j for j in range(self.n_drones) if j != idx and f"drone_{j}" in self.agents]
        if others: min_dists = np.minimum(min_dists, intersect_circles(self.positions[others], np.full(len(others), 2*self.drone_radius)))

        sector_res = min_dists.reshape(16, 12)
        return np.concatenate([np.min(sector_res, 1), np.mean(sector_res, 1), np.std(sector_res, 1)])

    def _observe(self, agent):
        idx = self.agent_name_mapping[agent]
        pos, vel = self.positions[idx], self.velocities[idx]
        dg = np.linalg.norm(self.goal - pos)
        obs_self = np.concatenate([vel/V_MAX_NORM, (self.goal-pos)/(dg+1e-5), [dg/28.28, np.arctan2(vel[1], vel[0])/np.pi]])
        obs_lidar = self.lidar_cache.get(agent, self._ray_cast(idx)) / R_SENSOR_NORM

        neighbor_slots, pos_discs, u_count, c_count = [], [], 0, 0
        for j in range(self.n_drones):
            if j == idx: continue
            slot = np.zeros(15, dtype=np.float32)
            if f"drone_{j}" in self.agents:
                slot[14] = 1.0; d_j = self.dist_matrix[idx, j]
                is_vis = 1.0 if (d_j <= self.current_r_sensor and not self._is_occluded(idx, j)) else 0.0
                is_comm = 1.0 if d_j <= self.current_r_comm else 0.0

                s_pos, s_vel, c_pos, c_vel, stag = np.zeros(2), np.zeros(2), np.zeros(2), np.zeros(2), 0.0
                if is_vis: s_pos, s_vel = self.positions[j]-pos, self.velocities[j]-vel
                if is_comm:
                    c_count += 1; m = self.broadcasts[j]
                    c_pos, c_vel, stag = m['pos']-pos, m['vel']-vel, m['stag']
                    if not is_vis: u_count += 1

                p_disc, v_disc = 0.0, 0.0
                if is_vis and is_comm:
                    p_disc, v_disc = np.linalg.norm(s_pos-c_pos)/R_SENSOR_NORM, np.linalg.norm(s_vel-c_vel)/(2*V_MAX_NORM)
                    pos_discs.append(p_disc)

                slot[:2], slot[2:4], slot[4] = s_pos/R_SENSOR_NORM, s_vel/V_MAX_NORM, is_vis
                slot[5:7], slot[7:9] = c_pos/R_COMM_NORM, c_vel/V_MAX_NORM
                slot[9], slot[10], slot[11], slot[12] = stag, is_comm, p_disc, v_disc
                slot[13] = 1.0 if (is_vis and is_comm) else (0.5 if is_vis else 0.0)
            neighbor_slots.append(slot)

        self.position_history[agent].append(pos.copy())
        hist = list(self.position_history[agent])
        while len(hist) < 5: hist.insert(0, pos.copy())
        
        # [STIGMERGY SENSOR]
        obs_breadcrumb = np.zeros(2, dtype=np.float32)
        if self.breadcrumbs:
            dists = [np.linalg.norm(pos - np.array(b[0])) for b in self.breadcrumbs]
            if dists and min(dists) < self.sensing_radius:
                obs_breadcrumb = (np.array(self.breadcrumbs[np.argmin(dists)][0]) - pos) / self.sensing_radius

        congestion = sum(1 for j in range(self.n_drones) if j!=idx and f"drone_{j}" in self.agents and self.dist_matrix[idx,j]<1.0)/self.n_drones
        obs_ctx = np.concatenate([np.concatenate([(h-pos)/self.WIDTH for h in hist]), [congestion], [np.mean(pos_discs) if pos_discs else 0.0], [(u_count/c_count) if c_count > 0 else 0.0]])
        
        obs_a = np.concatenate([obs_self, obs_lidar, np.concatenate(neighbor_slots), obs_ctx, obs_breadcrumb]).astype(np.float32)
        return np.concatenate([obs_a, self.global_state]).astype(np.float32)

    def reset(self, seed=None, options=None):
        self.agents, self.steps = self.possible_agents[:], 0
        self.infos = {a: {} for a in self.agents}
        self.steps_stagnant = {a: 0 for a in self.possible_agents}
        self.best_dist_to_goal = {a: 99.0 for a in self.possible_agents}
        self.position_history = {a: deque(maxlen=5) for a in self.possible_agents}
        self.last_actions = {a: np.zeros(2, dtype=np.float32) for a in self.possible_agents}
        self.breadcrumbs = []
        
        self.goal = np.array(options["goal"]) if (options and "goal" in options) else np.array([np.random.uniform(2.0, 18.0), np.random.uniform(2.0, 18.0)])
        for _ in range(200):
            sc = np.random.uniform(2.0, 18.0, 2)
            if np.linalg.norm(sc - self.goal) > 7.0: break
        else: sc = np.clip(np.array([20.0, 20.0]) - self.goal, 2.0, 18.0)
        
        target = (self.WIDTH * self.HEIGHT) * self.target_density; obs, cur = [], 0.0
        for _ in range(500):
            if cur >= target: break
            r = np.random.uniform(0.6, 1.4) if np.random.random() < 0.6 else np.random.uniform(0.2, 0.5)
            cx, cy = np.random.uniform(r/2, 20-r/2), np.random.uniform(r/2, 20-r/2)
            if np.linalg.norm([cx,cy]-self.goal) <= r+2.0 or np.linalg.norm([cx,cy]-sc) <= r+1.65: continue
            obs.append((cx, cy, r)); cur += np.pi * r**2
        self.obstacles = obs
        
        self.positions, self.velocities = np.zeros((self.n_drones, 2)), np.zeros((self.n_drones, 2))
        is_cl = np.random.random() < 0.5
        if options and "spawn_mode" in options:
            is_cl = (options["spawn_mode"] == "clustered")
        for i in range(self.n_drones):
            for _ in range(200):
                p = np.random.uniform(sc-1.5, sc+1.5, 2) if is_cl else np.random.uniform(1.0, 19.0, 2)
                if all(np.linalg.norm(p-self.positions[j]) >= 0.35 for j in range(i)) and all(np.linalg.norm(p-[ox,oy]) >= 0.2+orad for ox,oy,orad in self.obstacles):
                    self.positions[i] = p; break
            else: self.positions[i] = np.clip(sc+np.random.uniform(-0.3, 0.3, 2), 0.3, 19.7)
            self.best_dist_to_goal[f"drone_{i}"] = np.linalg.norm(self.goal - self.positions[i])

        self._compute_distance_matrix()
        self._prepare_broadcasts()
        self.lidar_cache = {f"drone_{j}": self._ray_cast(j) for j in range(self.n_drones)}
        self._prepare_global_state()
        return {a: self._observe(a) for a in self.agents}, self.infos

    def step(self, actions):
        if not self.agents: return {}, {}, {}, {}, {}
        self._prepare_broadcasts()
        old_p = np.copy(self.positions)
        self._compute_distance_matrix()

        # Decay Breadcrumbs
        self.breadcrumbs = [(p, t-1) for p, t in self.breadcrumbs if t > 1]

        for agent, act in actions.items():
            idx = self.agent_name_mapping[agent]; act = np.clip(act, -1.0, 1.0)
            self.velocities[idx] += act * self.dt * 10.0
            nc = sum(1 for j in range(self.n_drones) if j!=idx and f"drone_{j}" in self.agents and self.dist_matrix[idx,j] < 1.0)
            mx = max(self.max_velocity * math.exp(-0.15 * nc), 0.75); sp = np.linalg.norm(self.velocities[idx])
            if sp > mx: self.velocities[idx] = (self.velocities[idx]/sp)*mx
            self.positions[idx] = np.clip(self.positions[idx] + self.velocities[idx]*self.dt, 0, 20.0)
        
        self.steps += 1
        self._compute_distance_matrix()
        self.lidar_cache = {a: self._ray_cast(self.agent_name_mapping[a]) for a in self.agents}
        self._prepare_global_state()
        
        rew, terms, truncs = {}, {}, {}
        for a in self.agents:
            # BUG FIX 1: 'idx' must be resolved before 'pos', they cannot be on same line
            agent_idx = self.agent_name_mapping[a]
            pos = self.positions[agent_idx]
            dg = np.linalg.norm(self.goal - pos)
            sp = np.linalg.norm(self.velocities[agent_idx])
            ug = (self.goal - pos) / (dg + 1e-6)
            r = 100.0 * (np.linalg.norm(self.goal - old_p[agent_idx]) - dg) - 0.25
            al = np.dot(self.velocities[agent_idx] / (sp + 1e-6), ug)
            # BUG FIX 2: 'act' is not defined here, get it from actions dict
            act = actions.get(a, np.zeros(2, dtype=np.float32))

            # Stagnation & Breadcrumb drop
            if dg < self.best_dist_to_goal[a] - 0.1:
                self.best_dist_to_goal[a], self.steps_stagnant[a] = dg, 0
            elif sp > 0.5 and al < 0.2:
                self.steps_stagnant[a] = max(0, self.steps_stagnant[a] - 1)
            else:
                self.steps_stagnant[a] += 1

            if self.steps_stagnant[a] > self.stagnation_limit:
                if not any(np.linalg.norm(pos - np.array(b[0])) < 0.5 for b in self.breadcrumbs):
                    self.breadcrumbs.append((tuple(pos), self.breadcrumb_lifetime))
                r -= min((self.steps_stagnant[a] - self.stagnation_limit) * 0.25, 25.0)

            # Breadcrumb repulsion
            if self.breadcrumbs:
                min_b = min(np.linalg.norm(pos - np.array(b[0])) for b in self.breadcrumbs)
                if min_b < 1.0: r -= (1.0 - min_b) * self.repulsion_scale

            # Neighbor penalties
            for j in range(self.n_drones):
                if j == agent_idx or f"drone_{j}" not in self.agents: continue
                d = self.dist_matrix[agent_idx, j]
                cs = np.dot((self.positions[j] - pos) / (d + 1e-6), self.velocities[agent_idx] - self.velocities[j])
                if cs > 0 and d / (cs + 1e-6) < 1.0: r -= 10.0 * (1.0 - d / (cs + 1e-6))**2
                if d < 0.6 and cs > 0.1: r -= 25.0 * cs * (0.6 - d)
                if d < 0.4: r -= (0.4 - d) * 100.0
                vj_norm = np.linalg.norm(self.velocities[j])
                if d < 1.5 and sp > 0.1 and vj_norm > 0.1:
                    r += 0.2 * (np.dot(self.velocities[agent_idx], self.velocities[j]) / (sp * vj_norm)) * max(0.0, al)

            r -= 0.05 * np.linalg.norm(act - self.last_actions[a])**2
            self.last_actions[a] = act.copy()
            ld = self.lidar_cache[a]
            r += ((ld[31] + ld[16] + ld[17]) / 24.0) * 0.2
            ml = np.min(ld[:16])
            if ml < 0.15: r -= ((0.15 - ml) / 0.15)**2

            hit_wall = min(pos[0], 20-pos[0], pos[1], 20-pos[1]) <= 0.05
            hit_obs = any(np.linalg.norm(pos - np.array([ox, oy])) < 0.15 + orad for ox, oy, orad in self.obstacles)
            hit_drone = any(self.dist_matrix[agent_idx, j] < 0.3 for j in range(self.n_drones) if j != agent_idx and f"drone_{j}" in self.agents)

            if hit_wall or hit_obs or hit_drone:
                r, terms[a] = -500.0, True; self.infos[a]["cause"] = "collision"
            elif dg < 0.75:
                r += 500.0 + (100.0 / (1.0 + sp)); terms[a], self.infos[a]["cause"] = True, "success"
            else:
                terms[a] = False
            rew[a], truncs[a] = float(r), self.steps >= self.max_steps
            if truncs[a] and not terms[a]:
                self.infos[a]["cause"] = "timeout"
        
        obs = {a: self._observe(a) for a in self.agents}
        for a in list(self.agents):
            if terms.get(a, False) or truncs.get(a, False):
                self.positions[self.agent_name_mapping[a]] = [-100, -100]; self.agents.remove(a)
        return obs, rew, terms, truncs, self.infos

    def render(self):
        if self.render_mode != "human": return
        if self.screen is None: pygame.init(); self.screen = pygame.display.set_mode((800, 800)); self.clock = pygame.time.Clock()
        self.screen.fill((30, 30, 30))
        def w2s(x, y): return int((x/20)*800), int(800 - (y/20)*800)
        for b in self.breadcrumbs: pygame.draw.circle(self.screen, (200, 50, 50), w2s(*b[0]), 5)
        pygame.draw.circle(self.screen, (0, 255, 0), w2s(*self.goal), 15)
        for ox, oy, orad in self.obstacles: pygame.draw.circle(self.screen, (100, 100, 100), w2s(ox, oy), int((orad/20)*800))
        for i in range(self.n_drones):
            if f"drone_{i}" in self.agents: pygame.draw.circle(self.screen, (100, 100, 255), w2s(*self.positions[i]), 8)
        pygame.display.flip(); self.clock.tick(30)
