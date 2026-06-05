import numpy as np
import pygame
from pettingzoo import ParallelEnv
from gymnasium import spaces, Env as GymEnv
from collections import deque
import math
import sys

# ======================================================
#  PHASE B6 v10: SMART QUEUING & ASYMMETRIC YIELDING
#  Solves choke-point panics at 35% density with 12m LiDAR
# ======================================================
class SwarmLidarEnv_StepB6(ParallelEnv):
    metadata = {'render_modes': ['human'], "name": "swarm_lidar_stepB6_v0"}

    def __init__(self, render_mode=None, target_density=0.20, drone_radius=0.15, safety_radius=0.19):
        super().__init__()
        self.render_mode = render_mode
        self.target_density = target_density
        self.n_drones = 10
        self.num_traitors = 0
        self.num_honest = 10
        
        self.dt = 0.1
        self.max_steps = 800
        self.max_velocity = 2.0
        self.drone_radius = drone_radius 
        self.safety_radius = safety_radius 
        self.WIDTH, self.HEIGHT = 20.0, 20.0 
        
        self.obstacles = [] 
        self.possible_agents = [f"drone_{i}" for i in range(self.n_drones)]
        self.agent_name_mapping = dict(zip(self.possible_agents, list(range(self.n_drones))))

        self.positions = np.zeros((self.n_drones, 2), dtype=np.float32)
        self.velocities = np.zeros((self.n_drones, 2), dtype=np.float32)
        self.goal = np.array([18.0, 18.0], dtype=np.float32) 
        
        self.action_spaces = {agent: spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32) for agent in self.possible_agents}

        # 130-Dim Local (120 + 10 trajectory) + 520-Dim Global = 650 Total
        self.obs_size = 130 + 520
        self.observation_spaces = {agent: spaces.Box(low=-np.inf, high=np.inf, shape=(self.obs_size,), dtype=np.float32) for agent in self.possible_agents}
        
        # SB3 Gym Compatibility
        self.observation_space = self.observation_spaces["drone_0"]
        self.action_space = self.action_spaces["drone_0"]

        self.screen_width = 800
        self.screen_height = 800
        self.screen = None
        self.clock = None
        self.test_mode = False

        # Pre-compute LiDAR ray directions
        num_sectors = 16
        rays_per_sector = 12
        num_rays = num_sectors * rays_per_sector
        sector_width = (2 * np.pi) / num_sectors
        center_angles = np.arange(num_sectors) * sector_width
        offsets = np.linspace(-sector_width/2, sector_width/2, rays_per_sector, endpoint=False)
        angles = (center_angles[:, np.newaxis] + offsets).flatten()
        self.ray_dirs = np.stack([np.cos(angles), np.sin(angles)], axis=1).astype(np.float32)

    def set_target_density(self, density: float):
        self.target_density = density

    # [FIX 1] RESTORED: Map Solvability Check (from B4)
    def _is_map_solvable(self, start_pos=None, grid_resolution=0.2):
        if start_pos is None:
            start_pos = np.array([self.WIDTH / 2.0, self.HEIGHT / 2.0])
        grid_size = int(np.ceil(self.WIDTH / grid_resolution))
        grid = np.ones((grid_size, grid_size), dtype=bool)
        clearance_radius = self.drone_radius + 0.05
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
        spawn_cell = (np.clip(int(start_pos[0] / grid_resolution), 0, grid_size - 1),
                      np.clip(int(start_pos[1] / grid_resolution), 0, grid_size - 1))
        goal_cell = (np.clip(int(self.goal[0] / grid_resolution), 0, grid_size - 1),
                     np.clip(int(self.goal[1] / grid_resolution), 0, grid_size - 1))
        if not grid[spawn_cell[0], spawn_cell[1]] or not grid[goal_cell[0], goal_cell[1]]:
            return False
        queue = deque([spawn_cell])
        visited = set([spawn_cell])
        while queue:
            x, y = queue.popleft()
            if (x, y) == goal_cell: return True
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0: continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < grid_size and 0 <= ny < grid_size:
                        if grid[nx, ny] and (nx, ny) not in visited:
                            visited.add((nx, ny))
                            queue.append((nx, ny))
        return False

    def reset(self, seed=None, options=None):
        if seed is not None:
            np.random.seed(seed)
        self.agents = self.possible_agents[:]
        self.terminations = {agent: False for agent in self.agents}
        self.truncations = {agent: False for agent in self.agents}
        self.infos = {agent: {} for agent in self.agents}
        self.steps = 0
        self.obstacles = []
        self.lidar_cache = {}
        
        self.last_actions = {agent: np.zeros(2, dtype=np.float32) for agent in self.possible_agents}
        self.best_dist_to_goal = {agent: 999.0 for agent in self.possible_agents}
        self.steps_stagnant = {agent: 0 for agent in self.possible_agents}
        self.position_history = {agent: deque(maxlen=5) for agent in self.possible_agents}
        self.dispersion_time = None
        self.trajectory_data = [] 
        
        if options and "goal" in options:
            self.goal = np.array(options["goal"], dtype=np.float32)
            spawn_center = np.array([self.WIDTH / 2.0, self.HEIGHT / 2.0])
        else:
            self.goal = np.array([np.random.uniform(2.0, self.WIDTH - 2.0), np.random.uniform(2.0, self.HEIGHT - 2.0)], dtype=np.float32)
            for _ in range(200):
                spawn_center = np.array([np.random.uniform(3.0, self.WIDTH - 3.0), np.random.uniform(3.0, self.HEIGHT - 3.0)]) if np.random.random() < 0.8 else np.array([self.WIDTH / 2.0, self.HEIGHT / 2.0])
                if np.linalg.norm(spawn_center - self.goal) >= 8.0:
                    break
            else:
                spawn_center = np.clip(np.array([self.WIDTH, self.HEIGHT]) - self.goal, 3.0, self.WIDTH - 3.0)

        if options and "obstacles" in options:
            self.obstacles = options["obstacles"] 
            ver_start = np.array([self.WIDTH / 2.0, self.HEIGHT / 2.0])
            if options and "start_positions" in options:
                ver_start = np.mean(options["start_positions"], axis=0)
            self._cached_spawn_center = ver_start
        
        # [FIX 1] Generate obstacles WITH solvability check
        if not (options and "obstacles" in options):
            target_area = (self.WIDTH * self.HEIGHT) * self.target_density
            safe_goal_radius = 2.0

            for attempt in range(50):
                self.obstacles = []
                current_area = 0.0
                while current_area < target_area:
                    choice = np.random.random()
                    r = np.random.uniform(1.5, 2.5) if choice < 0.2 else np.random.uniform(0.6, 1.4) if choice < 0.6 else np.random.uniform(0.2, 0.5)
                    x, y = np.random.uniform(r, self.WIDTH - r), np.random.uniform(r, self.HEIGHT - r)
                    if np.linalg.norm(np.array([x, y]) - self.goal) < (r + safe_goal_radius): continue
                    self.obstacles.append((x, y, r))
                    current_area += np.pi * (r ** 2)
                if self._validate_obstacles() and self._is_map_solvable(start_pos=spawn_center):
                    break
            else:
                self.obstacles = []  # Fallback: empty map if no solvable layout found
            self._cached_spawn_center = spawn_center
        
        if options and "start_positions" in options:
            self.positions = np.array(options["start_positions"], dtype=np.float32)
            self.velocities = np.zeros((self.n_drones, 2), dtype=np.float32)
        else:
            self.velocities = np.zeros((self.n_drones, 2), dtype=np.float32)
            cx, cy = self._cached_spawn_center if hasattr(self, "_cached_spawn_center") else (np.random.uniform(3.0, self.WIDTH - 3.0), np.random.uniform(3.0, self.HEIGHT - 3.0))
            
            is_clustered = (options["spawn_mode"] == "clustered") if (options and "spawn_mode" in options) else (np.random.random() < 0.9)

            if is_clustered:
                half = 1.5  
                min_dist = 0.6 
                placed = []
                for i in range(self.n_drones):
                    found = False
                    for _ in range(500):
                        x, y = np.clip(np.random.uniform(cx - half, cx + half), 1.0, self.WIDTH - 1.0), np.clip(np.random.uniform(cy - half, cy + half), 1.0, self.HEIGHT - 1.0)
                        if all(np.sqrt((x-px)**2 + (y-py)**2) >= min_dist for px, py in placed) and all(np.sqrt((x-ox)**2 + (y-oy)**2) >= (self.drone_radius + orad) for ox, oy, orad in self.obstacles):
                            placed.append([x, y]); found = True; break
                    if not found:
                        for _ in range(100):
                            x = np.random.uniform(cx - half - 1.5, cx + half + 1.5)
                            y = np.random.uniform(cy - half - 1.5, cy + half + 1.5)
                            x, y = np.clip(x, 1.0, self.WIDTH - 1.0), np.clip(y, 1.0, self.HEIGHT - 1.0)
                            if all(np.sqrt((x-px)**2 + (y-py)**2) >= min_dist for px, py in placed) and all(np.sqrt((x-ox)**2 + (y-oy)**2) >= (self.drone_radius + orad) for ox, oy, orad in self.obstacles):
                                placed.append([x, y]); break
                        else:
                            placed.append([np.random.uniform(1.0, self.WIDTH-1.0), np.random.uniform(1.0, self.HEIGHT-1.0)])
                    self.positions[i] = np.array(placed[-1], dtype=np.float32)
            else:
                for i in range(self.n_drones):
                    placed = False
                    for _ in range(500):
                        x, y = np.random.uniform(1.0, self.WIDTH - 1.0), np.random.uniform(1.0, self.HEIGHT - 1.0)
                        if np.linalg.norm(np.array([x, y]) - self.goal) >= 8.0 and all(np.sqrt((x-ox)**2 + (y-oy)**2) >= (self.drone_radius + orad) for ox, oy, orad in self.obstacles):
                            if self._is_map_solvable(start_pos=np.array([x, y])):
                                self.positions[i] = np.array([x, y], dtype=np.float32)
                                placed = True
                                break
                    if not placed:
                        # Fallback to clustered area if completely random placements keep failing
                        for _ in range(100):
                            x, y = np.random.uniform(cx - 2.0, cx + 2.0), np.random.uniform(cy - 2.0, cy + 2.0)
                            x, y = np.clip(x, 1.0, self.WIDTH - 1.0), np.clip(y, 1.0, self.HEIGHT - 1.0)
                            if np.linalg.norm(np.array([x, y]) - self.goal) >= 8.0 and all(np.sqrt((x-ox)**2 + (y-oy)**2) >= (self.drone_radius + orad) for ox, oy, orad in self.obstacles):
                                self.positions[i] = np.array([x, y], dtype=np.float32)
                                break
            
        for i in range(self.n_drones):
            for ox, oy, orad in self.obstacles:
                dist = np.linalg.norm(self.positions[i] - np.array([ox, oy]))
                if dist < (self.drone_radius + orad):
                    vec = self.positions[i] - np.array([ox, oy])
                    norm = np.linalg.norm(vec)
                    vec = vec / norm if norm > 1e-6 else np.array([1.0, 0.0])
                    self.positions[i] = np.array([ox, oy]) + vec * (self.drone_radius + orad + 0.1)
                    self.positions[i] = np.clip(self.positions[i], 0.2, self.WIDTH - 0.2)
                    
        # Seed initial best distances
        for agent in self.agents:
            idx = self.agent_name_mapping[agent]
            self.best_dist_to_goal[agent] = np.linalg.norm(self.goal - self.positions[idx])
            self.steps_stagnant[agent] = 0

        observations = {agent: self._observe(agent) for agent in self.agents}
        return observations, self.infos

    def _ray_cast(self, agent_idx):
        """APEX-ULTRA: Vectorized Multi-Statistical Lidar Pooling (Min, Mean, Std)"""
        num_sectors = 16
        rays_per_sector = 12
        num_rays = num_sectors * rays_per_sector
        max_range = 12.0
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

    def _observe(self, agent):
        idx = self.agent_name_mapping[agent]
        pos = self.positions[idx]
        vel = self.velocities[idx]
        dist_goal = np.linalg.norm(self.goal - pos)
        to_goal = (self.goal - pos) / (dist_goal + 1e-5)
        lidar = self.lidar_cache[agent] if hasattr(self, 'lidar_cache') and agent in self.lidar_cache else self._ray_cast(idx)
        
        obs_core = np.concatenate([vel / self.max_velocity, to_goal, [dist_goal / (self.WIDTH * 1.414)], [np.arctan2(vel[1], vel[0]) / np.pi], lidar / 12.0])
        
        obs_neighbors = []
        sync_features = []
        distances = []
        for j in range(self.n_drones):
            if j != idx and self.possible_agents[j] in self.agents:
                distances.append((j, np.linalg.norm(pos - self.positions[j])))
        distances.sort(key=lambda x: x[1])
        closest_5 = [d[0] for d in distances[:5]]

        for j in range(self.n_drones):
            if j == idx: continue
            if self.possible_agents[j] in self.agents:
                rel_pos = (self.positions[j] - pos) / self.WIDTH
                norm_vel = self.velocities[j] / self.max_velocity
                is_active = 1.0
                if j in closest_5:
                    rel_vel = (self.velocities[j] - vel) / (2.0 * self.max_velocity)
                    stagnation_val = min(1.0, self.steps_stagnant[self.possible_agents[j]] / 50.0)
                    sync_features.append(np.concatenate([rel_vel, [stagnation_val, 0.0]]))
            else:
                rel_pos, norm_vel, is_active = np.zeros(2, dtype=np.float32), np.zeros(2, dtype=np.float32), 0.0
            obs_neighbors.append(np.concatenate([rel_pos, norm_vel, [is_active]]))
        
        while len(sync_features) < 5: sync_features.append(np.zeros(4, dtype=np.float32))

        neighbors_in_vicinity = sum(1 for j in range(self.n_drones) if j != idx and self.possible_agents[j] in self.agents and np.linalg.norm(pos - self.positions[j]) < 1.0)
        congestion_factor = np.array([neighbors_in_vicinity / self.n_drones], dtype=np.float32)
        
        obs_local = np.concatenate([obs_core, np.concatenate(obs_neighbors), congestion_factor, np.concatenate(sync_features)]).astype(np.float32)
        
        # [v6] Relative Trajectory History (translational invariant)
        self.position_history[agent].append(pos.copy())
        hist = list(self.position_history[agent])
        while len(hist) < 5: hist.insert(0, pos.copy())
        rel_hist = np.concatenate([(h - pos) / self.WIDTH for h in hist])  # 10 floats
        
        final_local = np.zeros(130, dtype=np.float32)
        copy_len = min(120, len(obs_local))
        final_local[:copy_len] = obs_local[:copy_len]
        final_local[120:130] = rel_hist  # Trajectory memory slots
        global_state = np.zeros(520, dtype=np.float32) 
        
        g_pos = np.zeros(self.n_drones * 2, dtype=np.float32)
        g_vel = np.zeros(self.n_drones * 2, dtype=np.float32)
        for j in range(self.n_drones):
            if self.possible_agents[j] in self.agents:
                g_pos[j*2:j*2+2] = self.positions[j] / self.WIDTH
                g_vel[j*2:j*2+2] = self.velocities[j] / self.max_velocity
        global_state[:40] = np.concatenate([g_pos, g_vel])

        # [FIX 3] Populate Critic Global State with LiDAR
        for j in range(self.n_drones):
            if self.possible_agents[j] in self.agents:
                agent_name = self.possible_agents[j]
                lidar_j = self.lidar_cache[agent_name] if hasattr(self, 'lidar_cache') and agent_name in self.lidar_cache else self._ray_cast(j)
                global_state[40 + j*48 : 40 + (j+1)*48] = lidar_j / 8.0

        return np.concatenate([final_local, global_state]).astype(np.float32)

    def _validate_obstacles(self):
        safe_goal_radius = max(self.drone_radius, 0.5) + 1.5 
        for ox, oy, or_ in self.obstacles:
            if np.linalg.norm(self.goal - np.array([ox, oy])) < (or_ + safe_goal_radius):
                return False
        return True

    def step(self, actions):
        if not self.agents: return {}, {}, {}, {}, {}
        old_positions = np.copy(self.positions)
        
        for agent in self.agents:
            self.terminations[agent] = False
            self.truncations[agent] = False

        for agent, action in actions.items():
            idx = self.agent_name_mapping[agent]
            action = np.clip(action, -1.0, 1.0)
            smoothness_penalty = -0.05 * np.linalg.norm(action - self.last_actions[agent])**2
            self.last_actions[agent] = action.copy()
            self.infos[agent]["smoothness_penalty"] = smoothness_penalty
            self.velocities[idx] += action * self.dt * 10.0
            speed = np.linalg.norm(self.velocities[idx])
            neighbors_count = sum(1 for j in range(self.n_drones) if j != idx and self.possible_agents[j] in self.agents and np.linalg.norm(self.positions[idx] - self.positions[j]) < 1.0)
            current_max = np.maximum(self.max_velocity * np.exp(-0.15 * neighbors_count), 0.75) 
            if speed > current_max: self.velocities[idx] = (self.velocities[idx] / speed) * current_max
            self.positions[idx] += self.velocities[idx] * self.dt
            self.positions[idx] = np.clip(self.positions[idx], 0.0, self.WIDTH)
            
        self.lidar_cache = {agent: self._ray_cast(self.agent_name_mapping[agent]) for agent in self.agents}
        self.steps += 1
        rewards = {agent: 0.0 for agent in self.agents}
        
        for agent in self.agents:
            idx = self.agent_name_mapping[agent]
            pos = self.positions[idx]
            dist_goal = np.linalg.norm(self.goal - pos)
            # 1. Base Goal Seeking Reward
            goal_progress = np.linalg.norm(self.goal - old_positions[idx]) - dist_goal
            reward_goal = 100.0 * goal_progress
            
            rewards[agent] += reward_goal - 0.25
            
            # 2. Advanced Stagnation Logic with Smart Queuing Yield
            speed = np.linalg.norm(self.velocities[idx])
            unit_to_goal = (self.goal - pos) / (dist_goal + 1e-6)
            alignment = np.dot(self.velocities[idx] / (speed + 1e-6), unit_to_goal)
            
            # Check if blocked by a drone in front (Optimized using standard math)
            is_blocked = False
            px, py = pos[0], pos[1]
            for j in range(self.n_drones):
                if j != idx and self.possible_agents[j] in self.agents:
                    dx_j = self.positions[j][0] - px
                    dy_j = self.positions[j][1] - py
                    dist_to_j = math.sqrt(dx_j**2 + dy_j**2)
                    if dist_to_j < 1.2:
                        dot_val = (dx_j * unit_to_goal[0] + dy_j * unit_to_goal[1]) / (dist_to_j + 1e-6)
                        if dot_val > 0.6:  # Drone j is in front of us blocking the goal
                            is_blocked = True
                            break
            
            if dist_goal < self.best_dist_to_goal[agent] - 0.1:
                self.best_dist_to_goal[agent] = dist_goal
                self.steps_stagnant[agent] = 0
            elif is_blocked:
                # [B6 SMART YIELD] Freeze stagnation penalty if we are blocked
                self.steps_stagnant[agent] = 0
                if speed < 0.2:
                    rewards[agent] += 0.5  # Reward for patiently queuing
            elif speed > 0.5 and alignment < 0.2:
                self.steps_stagnant[agent] = max(0, self.steps_stagnant[agent] - 1)
            else:
                self.steps_stagnant[agent] += 1
                
            if self.steps_stagnant[agent] > 50:
                frustration = min((self.steps_stagnant[agent] - 50) * 0.25, 25.0)
                rewards[agent] -= frustration

            vx, vy = self.velocities[idx][0], self.velocities[idx][1]
            for j in range(self.n_drones):
                if j == idx or self.possible_agents[j] not in self.agents: continue
                
                dx, dy = self.positions[j][0] - px, self.positions[j][1] - py
                dist = math.sqrt(dx*dx + dy*dy)
                dist_eps = dist + 1e-6
                
                dvx, dvy = vx - self.velocities[j][0], vy - self.velocities[j][1]
                closing_speed = (dx * dvx + dy * dvy) / dist_eps

                # [B5 SYNC] TTC Penalty (proactive long-range)
                if closing_speed > 0:
                    ttc = dist / closing_speed
                    if ttc < 1.0: rewards[agent] -= 10.0 * (1.0 - ttc)**2

                # [FIX 2] RESTORED: Asymmetric Closing-Velocity Yielding (from B4)
                if dist < 0.6:
                    if closing_speed > 0.1:
                        rewards[agent] -= 25.0 * closing_speed * (0.6 - dist)
                    # [FIX 3] RESTORED: Critical Buffer Penalty
                    if dist < 0.4:
                        rewards[agent] -= (0.4 - dist) * 100.0

                # [B6 FIX] Asymmetric Tailgating Repulsion
                if dist < 0.5:
                    urgency = (0.5 - dist) / 0.5
                    dot_vel_dir = (vx * dx + vy * dy) / (speed * dist_eps + 1e-6)
                    # If moving aggressively towards the other drone
                    if closing_speed > 0.15 and dot_vel_dir > 0.5:
                        rewards[agent] -= 50.0 * urgency**2  # Heavy penalty for aggressive tailgater
                    else:
                        rewards[agent] -= 10.0 * urgency  # Mild spacing penalty for passive yielder

                # [B5 SYNC] Goal-Gated Cohesive Flow
                if dist < 1.5:
                    v_self_norm = speed
                    v_neigh_norm = math.sqrt(self.velocities[j][0]**2 + self.velocities[j][1]**2)
                    if v_self_norm > 0.1 and v_neigh_norm > 0.1:
                        cos_sim = (vx * self.velocities[j][0] + vy * self.velocities[j][1]) / (v_self_norm * v_neigh_norm)
                        goal_progress = max(0.0, (vx * unit_to_goal[0] + vy * unit_to_goal[1]) / (v_self_norm + 1e-6))
                        rewards[agent] += 0.5 * cos_sim * goal_progress

            # Energy efficiency
            rewards[agent] += self.infos[agent].get("smoothness_penalty", 0.0)

            # [FIX 4] RESTORED: Front Clarity Reward + Near-Miss LiDAR Penalty
            lidar = self.lidar_cache[agent]
            front_indices = [15, 0, 1]
            clarity_score = np.mean([lidar[f] for f in front_indices])
            rewards[agent] += (clarity_score / 8.0) * 0.2

            min_lidar_dist = np.min(lidar[:16])
            if min_lidar_dist < 0.15:
                near_miss_penalty = -1.0 * ((0.15 - min_lidar_dist) / 0.15)**2
                rewards[agent] += near_miss_penalty

            # Optimized Collision Detection using standard math to avoid NumPy overhead in loops
            hit_wall = min(px, self.WIDTH - px, py, self.HEIGHT - py) <= 0.05
            
            hit_obstacle = False
            r_drone = self.drone_radius
            for ox, oy, orad in self.obstacles:
                if (px - ox)**2 + (py - oy)**2 < (r_drone + orad)**2:
                    hit_obstacle = True
                    break
                    
            hit_drone = False
            for j in range(self.n_drones):
                if j != idx and self.possible_agents[j] in self.agents:
                    ox, oy = self.positions[j][0], self.positions[j][1]
                    if (px - ox)**2 + (py - oy)**2 < (2 * r_drone)**2:
                        hit_drone = True
                        break
            
            if hit_wall or hit_obstacle or hit_drone:
                rewards[agent] = -500.0; self.terminations[agent] = True; self.infos[agent]["cause"] = "collision"
            elif dist_goal < 0.75:
                rewards[agent] += 500.0 + (100.0 / (1.0 + speed))
                self.terminations[agent] = True; self.infos[agent]["cause"] = "success"

        # [FIX 5] RESTORED: Timeout Cause Tagging
        if self.steps >= self.max_steps:
            for agent in self.agents:
                self.truncations[agent] = True
                self.infos[agent]["cause"] = "timeout"

        # Snapshot FIRST, then teleport dead drones
        observations = {agent: self._observe(agent) for agent in self.agents}
        for agent in self.possible_agents:
            if self.terminations.get(agent, False) or self.truncations.get(agent, False):
                idx = self.agent_name_mapping[agent]
                self.positions[idx] = np.array([-100.0, -100.0], dtype=np.float32)
                self.velocities[idx] = np.zeros(2, dtype=np.float32)
        self.agents = [agent for agent in self.agents if not (self.terminations[agent] or self.truncations[agent])]
        return observations, rewards, self.terminations, self.truncations, self.infos
