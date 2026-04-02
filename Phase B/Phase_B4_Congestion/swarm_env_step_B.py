import numpy as np
import pygame
from pettingzoo import ParallelEnv
# make env also satisfy Gymnasium for SB3 vector wrappers
from gymnasium import spaces, Env as GymEnv
import math
import sys

# ======================================================
#  PHASE B: 10 Drones, 0 Traitors, STATIC OBSTACLES
#  APEX-ULTRA UPGRADE: Statistical LiDAR + Graduated Near-Miss
# ======================================================
class SwarmLidarEnv_StepB(ParallelEnv, GymEnv):
    metadata = {'render_modes': ['human'], "name": "swarm_lidar_stepB_v0"}

    def __init__(self, render_mode=None, target_density=0.20, drone_radius=0.15, safety_radius=0.19):
        super().__init__()
        self.render_mode = render_mode
        self.target_density = target_density
        self.n_drones = 10
        self.num_traitors = 0
        self.num_honest = 10
        
        # Physics Constants
        self.dt = 0.1
        self.max_steps = 600
        self.max_velocity = 2.0
        self.drone_radius = drone_radius  # Physical radius (used for collisions)
        self.safety_radius = safety_radius # Safety buffer (used for social distance and inflation)
        self.WIDTH, self.HEIGHT = 20.0, 20.0  # 20x20 Field
        
        # Phase B Static Obstacles
        self.obstacles = [] # List of tuples: (x, y, radius)
        
        # Agent Identification
        self.possible_agents = [f"drone_{i}" for i in range(self.n_drones)]
        self.agent_name_mapping = dict(zip(self.possible_agents, list(range(self.n_drones))))

        # Shared State Tensors
        self.positions = np.zeros((self.n_drones, 2), dtype=np.float32)
        self.velocities = np.zeros((self.n_drones, 2), dtype=np.float32)
        self.goal = np.array([18.0, 18.0], dtype=np.float32) # Global Goal
        
        # Action Space: (Vx, Vy) continuous control [-1, 1]
        self.action_spaces = {
            agent: spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32) 
            for agent in self.possible_agents
        }

        # [PHASE B4] Updated Observation Dimensions
        # LOCAL  (100): LiDAR-48 + Self_vel-2 + To_goal-2 + Dist_goal-1 + Heading-1 + Neighbors(5x9)-45 + Congestion-1 = 100
        # GLOBAL (520): All Drone Pos (20) + All Drone Vel (20) + All Drone LiDAR Full (480)
        # Total = 620 Dims
        self.obs_size = (55 + (5 * (self.n_drones - 1))) + 520
        self.observation_spaces = {
            agent: spaces.Box(low=-np.inf, high=np.inf, shape=(self.obs_size,), dtype=np.float32)
            for agent in self.possible_agents
        }

        # PyGame Rendering
        self.screen_width = 800
        self.screen_height = 800
        self.screen = None
        self.clock = None
        self.test_mode = False

    # helper for external wrappers
    def set_target_density(self, density: float):
        """Allow external code (VecEnv.env_method) to change density."""
        self.target_density = density

    def reset(self, seed=None, options=None):
        self.agents = self.possible_agents[:]
        self.terminations = {agent: False for agent in self.agents}
        self.truncations = {agent: False for agent in self.agents}
        self.infos = {agent: {} for agent in self.agents}
        self.steps = 0
        self.obstacles = []
        self.lidar_cache = {}
        
        # 1. Configurable Global Goal
        if options and "goal" in options:
            self.goal = np.array(options["goal"], dtype=np.float32)
        else:
            self.goal = np.array([np.random.uniform(2.0, self.WIDTH - 2.0), np.random.uniform(2.0, self.HEIGHT - 2.0)], dtype=np.float32)

        # 2. Phase B Obstacle Generation (Surface Area Density)
        if options and "obstacles" in options:
            self.obstacles = options["obstacles"] # Load from exact JSON
            
            # Determine start position for solvability check
            ver_start = np.array([self.WIDTH / 2.0, self.HEIGHT / 2.0])
            if options and "start_positions" in options:
                ver_start = np.mean(options["start_positions"], axis=0)
            
            if not self._is_map_solvable(start_pos=ver_start):
                print(f"⚠️  WARNING: JSON map might be unsolvable from {ver_start}!")
            
            self._cached_spawn_center = ver_start
        
        # Generate random obstacles ONLY if not already provided via options
        if not (options and "obstacles" in options):
            target_area = (self.WIDTH * self.HEIGHT) * self.target_density
            current_area = 0.0
            
            safe_goal_radius = 2.0 
            
            if np.random.random() < 0.8:
                spawn_center = np.array([np.random.uniform(3.0, self.WIDTH - 3.0), np.random.uniform(3.0, self.HEIGHT - 3.0)])
            else:
                spawn_center = np.array([self.WIDTH / 2.0, self.HEIGHT / 2.0])

            max_attempts = 15
            attempt = 0
            while attempt < max_attempts:
                self.obstacles = []
                current_area = 0.0
                
                while current_area < target_area:
                    choice = np.random.random()
                    if choice < 0.2:
                        r = np.random.uniform(1.5, 2.5) # Rare massive boulders
                    elif choice < 0.6:
                        r = np.random.uniform(0.6, 1.4) # Common medium blocks
                    else:
                        r = np.random.uniform(0.2, 0.5) # Abundant tiny pillars
                        
                    x = np.random.uniform(r, self.WIDTH - r)
                    y = np.random.uniform(r, self.HEIGHT - r)
                    
                    if np.linalg.norm(np.array([x, y]) - self.goal) < (r + safe_goal_radius):
                        continue
                        
                    self.obstacles.append((x, y, r))
                    current_area += np.pi * (r ** 2)
                
                if self._is_map_solvable(start_pos=spawn_center):
                    break
                else:
                    attempt += 1
            
            if attempt >= max_attempts:
                self.obstacles = []
            
            self._cached_spawn_center = spawn_center
        
        # 3. Configurable Start Positions
        if options and "start_positions" in options:
            self.positions = np.array(options["start_positions"], dtype=np.float32)
            self.velocities = np.zeros((self.n_drones, 2), dtype=np.float32)
            
            for i in range(self.n_drones):
                for j in range(i + 1, self.n_drones):
                    dist = np.linalg.norm(self.positions[i] - self.positions[j])
                    if dist < (self.drone_radius * 2.1):
                        vec = self.positions[j] - self.positions[i]
                        if np.linalg.norm(vec) < 1e-4: vec = np.array([0.1, 0.1])
                        self.positions[j] += (vec / np.linalg.norm(vec)) * 0.1
        else:
            self.velocities = np.zeros((self.n_drones, 2), dtype=np.float32)
            if hasattr(self, "_cached_spawn_center"):
                cx, cy = self._cached_spawn_center
            else:
                cx, cy = np.random.uniform(3.0, self.WIDTH - 3.0), np.random.uniform(3.0, self.HEIGHT - 3.0)
            
            # [PHASE B4 FIX] Read the curriculum option from the trainer!
            if options and "spawn_mode" in options:
                is_clustered = (options["spawn_mode"] == "clustered")
            else:
                # Default behavior: 70% Clustered (Mixed Curriculum)
                is_clustered = np.random.random() < 0.7

            if is_clustered:
                half = 1.0  
                min_dist = 0.4
                placed = []
                for i in range(self.n_drones):
                    found_valid = False
                    for attempt in range(500):
                        x = np.random.uniform(cx - half, cx + half)
                        y = np.random.uniform(cy - half, cy + half)
                        x = np.clip(x, 0.3, self.WIDTH - 0.3)
                        y = np.clip(y, 0.3, self.HEIGHT - 0.3)
                        
                        drone_valid = all(np.sqrt((x-px)**2 + (y-py)**2) >= min_dist for px, py in placed)
                        obstacle_valid = all(np.sqrt((x-ox)**2 + (y-oy)**2) >= (self.drone_radius + orad) for ox, oy, orad in self.obstacles)
                        
                        if drone_valid and obstacle_valid:
                            placed.append([x, y])
                            found_valid = True
                            break
                    
                    if not found_valid:
                        for _ in range(100):
                            x = np.random.uniform(cx - half - 1.5, cx + half + 1.5)
                            y = np.random.uniform(cy - half - 1.5, cy + half + 1.5)
                            x = np.clip(x, 0.3, self.WIDTH - 0.3)
                            y = np.clip(y, 0.3, self.HEIGHT - 0.3)
                            drone_valid = all(np.sqrt((x-px)**2 + (y-py)**2) >= min_dist for px, py in placed)
                            obstacle_valid = all(np.sqrt((x-ox)**2 + (y-oy)**2) >= (self.drone_radius + orad) for ox, oy, orad in self.obstacles)
                            if drone_valid and obstacle_valid:
                                placed.append([x, y])
                                break
                        else:
                            placed.append([np.random.uniform(1.0, self.WIDTH-1.0), np.random.uniform(1.0, self.HEIGHT-1.0)])
                    self.positions[i] = np.array(placed[-1], dtype=np.float32)
            else:
                for i in range(self.n_drones):
                    valid = False
                    for _ in range(100):
                        x = np.random.uniform(1.0, self.WIDTH - 1.0)
                        y = np.random.uniform(1.0, self.HEIGHT - 1.0)
                        if all(np.sqrt((x-ox)**2 + (y-oy)**2) >= (self.drone_radius + orad) for ox, oy, orad in self.obstacles):
                            self.positions[i] = np.array([x, y], dtype=np.float32)
                            valid = True
                            break
                    if not valid:
                        self.positions[i] = np.array([np.random.uniform(1.0, self.WIDTH-1.0), np.random.uniform(1.0, self.HEIGHT-1.0)], dtype=np.float32)
            
        # Nudge out of obstacles
        for i in range(self.n_drones):
            for ox, oy, orad in self.obstacles:
                dist = np.linalg.norm(self.positions[i] - np.array([ox, oy]))
                if dist < (self.drone_radius + orad):
                    vec = self.positions[i] - np.array([ox, oy])
                    norm = np.linalg.norm(vec)
                    if norm < 1e-6:
                        vec = np.array([np.random.uniform(-1, 1), np.random.uniform(-1, 1)])
                        norm = np.linalg.norm(vec)
                    vec_normalized = vec / (norm + 1e-6)
                    safe_distance = self.drone_radius + orad + 0.1
                    self.positions[i] = np.array([ox, oy]) + vec_normalized * safe_distance
                    self.positions[i][0] = np.clip(self.positions[i][0], 0.2, self.WIDTH - 0.2)
                    self.positions[i][1] = np.clip(self.positions[i][1], 0.2, self.HEIGHT - 0.2)
                    
        # [PHASE B4] State Tracking
        self.last_actions = {agent: np.zeros(2, dtype=np.float32) for agent in self.agents}
        self.dispersion_time = None
        self.trajectory_data = [] # Stores (step, agent_id, x, y) if logging is needed
                    
        observations = {agent: self._observe(agent) for agent in self.agents}
        return observations, self.infos

    def _is_map_solvable(self, start_pos=None, min_path_width=0.4, grid_resolution=0.2):
        from collections import deque
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
        spawn_cell = (int(start_pos[0] / grid_resolution), int(start_pos[1] / grid_resolution))
        goal_cell = (int(self.goal[0] / grid_resolution), int(self.goal[1] / grid_resolution))
        spawn_cell = (np.clip(spawn_cell[0], 0, grid_size - 1), np.clip(spawn_cell[1], 0, grid_size - 1))
        goal_cell = (np.clip(goal_cell[0], 0, grid_size - 1), np.clip(goal_cell[1], 0, grid_size - 1))
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

    def _ray_cast(self, agent_idx):
        """APEX-ULTRA: Vectorized Multi-Statistical Lidar Pooling (Min, Mean, Std)"""
        num_sectors = 16
        rays_per_sector = 12
        num_rays = num_sectors * rays_per_sector
        max_range = 8.0
        pos = self.positions[agent_idx]

        # 1. Precompute all ray angles and directions
        sector_width = (2 * np.pi) / num_sectors
        center_angles = np.arange(num_sectors) * sector_width
        offsets = np.linspace(-sector_width/2, sector_width/2, rays_per_sector, endpoint=False)
        angles = (center_angles[:, np.newaxis] + offsets).flatten()
        
        ray_dirs = np.stack([np.cos(angles), np.sin(angles)], axis=1) # (192, 2)

        # Initialize distances with max_range
        min_distances = np.full(num_rays, max_range, dtype=np.float32)

        # 2. Vectorized Wall Intersections
        # Walls: X=WIDTH, X=0, Y=HEIGHT, Y=0
        for boundary, axis, direction in [(self.WIDTH, 0, 1), (0, 0, -1), (self.HEIGHT, 1, 1), (0, 1, -1)]:
            # d = (boundary - pos[axis]) / ray_dirs[:, axis]
            # Only consider rays moving towards the boundary
            mask = ray_dirs[:, axis] * direction > 1e-6
            if np.any(mask):
                d = (boundary - pos[axis]) / ray_dirs[mask, axis]
                valid = d > 0
                d_clipped = np.where(valid, d, max_range).astype(np.float32)
                min_distances[mask] = np.minimum(min_distances[mask], d_clipped)

        # 3. Vectorized Circle Intersections (Obstacles & Drones)
        def intersect_circles(centers, radii):
            # centers: (N, 2), radii: (N,)
            # rel_pos: (N, 2)
            rel_pos = centers - pos
            # proj: (N, num_rays) = rel_pos (N, 2) @ ray_dirs.T (2, num_rays)
            proj = rel_pos @ ray_dirs.T
            
            # closest_dist_sq = |rel_pos|^2 - proj^2
            rel_pos_sq = np.sum(rel_pos**2, axis=1, keepdims=True)
            dist_to_ray_sq = rel_pos_sq - proj**2
            
            # Mask for rays that actually hit the circle
            # 1. proj > 0 (circle is in front of ray)
            # 2. dist_to_ray_sq < radii^2
            hit_mask = (proj > 0) & (dist_to_ray_sq < radii[:, np.newaxis]**2)
            
            if np.any(hit_mask):
                sqrt_arg = radii[:, np.newaxis]**2 - dist_to_ray_sq
                # intersect_dist = proj - sqrt(sqrt_arg)
                dists = proj - np.sqrt(np.maximum(sqrt_arg, 0))
                # Update min_distances across all rays
                # We need to take the min over all circles (axis 0) for each ray (axis 1)
                dists[~hit_mask] = max_range
                global_min_dists = np.min(dists, axis=0)
                return global_min_dists
            return np.full(num_rays, max_range, dtype=np.float32)

        # Obstacles
        if self.obstacles:
            obs_array = np.array(self.obstacles, dtype=np.float32)
            obs_centers = obs_array[:, :2]
            obs_radii = obs_array[:, 2] + self.drone_radius
            min_distances = np.minimum(min_distances, intersect_circles(obs_centers, obs_radii))

        # Drones
        other_indices = [j for j in range(self.n_drones) 
                         if j != agent_idx and self.possible_agents[j] in self.agents]
        if other_indices:
            drone_centers = self.positions[other_indices]
            drone_radii = np.full(len(other_indices), 2.0 * self.drone_radius, dtype=np.float32)
            min_distances = np.minimum(min_distances, intersect_circles(drone_centers, drone_radii))

        # 4. Statistical Pooling per Sector
        # Reshape to (num_sectors, rays_per_sector)
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
        if hasattr(self, 'lidar_cache') and agent in self.lidar_cache:
            lidar = self.lidar_cache[agent]
        else:
            lidar = self._ray_cast(idx)
        obs_core = np.concatenate([
            vel / self.max_velocity,
            to_goal,
            [dist_goal / (self.WIDTH * 1.414)], 
            [np.arctan2(vel[1], vel[0]) / np.pi],
            lidar / 8.0
        ])
        obs_neighbors = []
        for j in range(self.n_drones):
            if j == idx: continue
            if self.possible_agents[j] in self.agents:
                rel_pos = (self.positions[j] - pos) / self.WIDTH
                norm_vel = self.velocities[j] / self.max_velocity
                is_active = 1.0
            else:
                rel_pos = np.zeros(2, dtype=np.float32)
                norm_vel = np.zeros(2, dtype=np.float32)
                is_active = 0.0
            obs_neighbors.append(np.concatenate([rel_pos, norm_vel, [is_active]]))
        
        obs_local_core = np.concatenate([obs_core, np.concatenate(obs_neighbors)]).astype(np.float32)

        # [PHASE B5] IEEE Augmented Sensing (Top 5 Synchronization Features)
        sync_features = []
        drone_distances = []
        for j in range(self.n_drones):
            if j == idx: continue
            drone_distances.append((j, np.linalg.norm(pos - self.positions[j])))
        
        drone_distances.sort(key=lambda x: x[1])
        top_5 = drone_distances[:5]
        
        for j, dist in top_5:
            if self.possible_agents[j] in self.agents:
                n_dist_goal = np.linalg.norm(self.goal - self.positions[j])
                neighbor_to_goal = (self.goal - self.positions[j]) / (n_dist_goal + 1e-5)
                rel_vel = (vel - self.velocities[j]) / (self.max_velocity + 1e-5)
            else:
                neighbor_to_goal = np.zeros(2, dtype=np.float32)
                rel_vel = np.zeros(2, dtype=np.float32)
            sync_features.append(np.concatenate([neighbor_to_goal, rel_vel]))
        
        while len(sync_features) < 5:
            sync_features.append(np.zeros(4, dtype=np.float32))
        sync_vector = np.concatenate(sync_features).astype(np.float32)

        # 1.5 [PHASE B4] Congestion Factor (1 dim)
        neighbors_in_vicinity = 0
        for j in range(self.n_drones):
            if j == idx: continue
            if self.possible_agents[j] in self.agents:
                if np.linalg.norm(pos - self.positions[j]) < 1.0:
                    neighbors_in_vicinity += 1
        congestion_factor = np.array([neighbors_in_vicinity / self.n_drones], dtype=np.float32)
        
        # Final Local Observation: 100 + 20 = 120 dims
        obs_local = np.concatenate([obs_local_core, sync_vector, congestion_factor])

        # 2. Global State (520 Dims) for CTDE Critic
        # All Drone Pos (20) + All Drone Vel (20) + All Drone LiDAR Full (480)
        global_pos = np.zeros(self.n_drones * 2, dtype=np.float32)
        global_vel = np.zeros(self.n_drones * 2, dtype=np.float32)
        for j in range(self.n_drones):
            agent_j = self.possible_agents[j]
            if agent_j in self.agents:
                global_pos[j*2 : j*2+2] = self.positions[j] / self.WIDTH
                global_vel[j*2 : j*2+2] = self.velocities[j] / self.max_velocity
        
        global_lidars = []
        for j in range(self.n_drones):
            agent_j = self.possible_agents[j]
            if agent_j not in self.agents:
                global_lidars.append(np.zeros(48, dtype=np.float32))
            elif hasattr(self, 'lidar_cache') and agent_j in self.lidar_cache:
                global_lidars.append(self.lidar_cache[agent_j] / 8.0)
            else:
                global_lidars.append(np.ones(48, dtype=np.float32))
        
        global_state = np.concatenate([global_pos, global_vel, np.concatenate(global_lidars)])
            
        if self.test_mode:
            padding = np.zeros(520, dtype=np.float32)
            return np.concatenate([obs_local, padding]).astype(np.float32)
        return np.concatenate([obs_local, global_state]).astype(np.float32)

    def step(self, actions):
        if not self.agents: return {}, {}, {}, {}, {}
        old_positions = np.copy(self.positions)
        for agent, action in actions.items():
            idx = self.agent_name_mapping[agent]
            action = np.clip(action, -1.0, 1.0)
            
            # [PHASE B4] ENERGY EFFICIENCY (Action Smoothing)
            smoothness_penalty = -0.05 * np.linalg.norm(action - self.last_actions[agent])**2
            self.last_actions[agent] = action.copy()
            # Note: Penalty is added to final rewards below
            self.infos[agent]["smoothness_penalty"] = smoothness_penalty

            self.velocities[idx] += action * self.dt * 10.0
            speed = np.linalg.norm(self.velocities[idx])
            
            # [PHASE B4] DYNAMIC VELOCITY CAPPING
            neighbors_count = 0
            for j in range(self.n_drones):
                if j == idx or self.possible_agents[j] not in self.agents: continue
                if np.linalg.norm(self.positions[idx] - self.positions[j]) < 1.0:
                    neighbors_count += 1
            
            # Cap velocity based on local density (Exp decay)
            current_max = self.max_velocity * np.exp(-0.15 * neighbors_count)
            current_max = np.maximum(current_max, 0.5) # Minimum 0.5m/s buffer

            if speed > current_max: 
                self.velocities[idx] = (self.velocities[idx] / speed) * current_max
            
            self.positions[idx] += self.velocities[idx] * self.dt
            # Logging trajectory data
            self.trajectory_data.append((self.steps, agent, self.positions[idx][0], self.positions[idx][1]))
            self.positions[idx][0] = np.clip(self.positions[idx][0], 0.0, self.WIDTH)
            self.positions[idx][1] = np.clip(self.positions[idx][1], 0.0, self.HEIGHT)
        self.lidar_cache = {agent: self._ray_cast(self.agent_name_mapping[agent]) for agent in self.agents}
        self.steps += 1
        rewards = {agent: 0.0 for agent in self.agents}
        for agent in self.agents:
            self.terminations[agent] = False
            self.truncations[agent] = False
        for agent in self.agents:
            idx = self.agent_name_mapping[agent]
            pos = self.positions[idx]
            old_pos = old_positions[idx]
            dist_goal = np.linalg.norm(self.goal - pos)
            old_dist_goal = np.linalg.norm(self.goal - old_pos)
            rewards[agent] += 100.0 * (old_dist_goal - dist_goal) - 0.25 # Progress + Living
            # 2. [PHASE B4] ASYMMETRIC CLOSING-VELOCITY YIELDING 
            for j in range(self.n_drones):
                if j == idx or self.possible_agents[j] not in self.agents: continue
                dist = np.linalg.norm(pos - self.positions[j])
                if dist < 0.6:
                    # Closing Velocity Check: (Pj - Pi) dot (Vi - Vj)
                    rel_pos = self.positions[j] - pos
                    rel_vel = self.velocities[idx] - self.velocities[j]
                    closing_speed = np.dot(rel_pos / (dist + 1e-6), rel_vel)
                    
                    if closing_speed > 0.1: # Distance is shrinking
                        rewards[agent] -= 25.0 * closing_speed * (0.6 - dist)
                    
                    if dist < 0.4: # Critical Buffer
                        rewards[agent] -= (0.4 - dist) * 100.0
            
            # 3. Energy Efficiency Bonus
            rewards[agent] += self.infos[agent].get("smoothness_penalty", 0.0)
            lidar = self.lidar_cache[agent]
            front_indices = [15, 0, 1]
            clarity_score = np.mean([lidar[f] for f in front_indices])
            rewards[agent] += (clarity_score / 8.0) * 0.2
            
            # --- APEX-ULTRA: Graduated Near-Miss Penalty ---
            min_lidar_dist = np.min(lidar[:16])
            if min_lidar_dist < 0.15:
                near_miss_penalty = -1.0 * ((0.15 - min_lidar_dist) / 0.15)**2
                rewards[agent] += near_miss_penalty
            
            hit_wall = min(pos[0], self.WIDTH - pos[0], pos[1], self.HEIGHT - pos[1]) <= 0.05
            hit_obstacle = any(np.linalg.norm(pos - np.array([ox, oy])) < (self.drone_radius + orad) for ox, oy, orad in self.obstacles)
            hit_drone = any(np.linalg.norm(pos - self.positions[j]) < (2 * self.drone_radius) for j in range(self.n_drones) if j != idx and self.possible_agents[j] in self.agents)
            if hit_wall or hit_obstacle:
                rewards[agent] = -500.0 
                self.terminations[agent] = True
                self.infos[agent]["cause"] = "collision"
            elif hit_drone:
                rewards[agent] = -500.0 
                self.terminations[agent] = True
                self.infos[agent]["cause"] = "collision"
            elif dist_goal < 0.75:
                rewards[agent] += 500.0 + (100.0 / (1.0 + np.linalg.norm(self.velocities[idx])))
                self.terminations[agent] = True
                self.infos[agent]["cause"] = "success"
        # --- [PHASE B4] CLUSTER EFFICIENCY METRIC 
        if self.dispersion_time is None and self.agents:
            # Average distance to nearest neighbor
            nearest_dists = []
            for i in range(self.n_drones):
                if self.possible_agents[i] not in self.agents: continue
                dists = [np.linalg.norm(self.positions[i] - self.positions[j]) for j in range(self.n_drones) 
                         if i != j and self.possible_agents[j] in self.agents]
                if dists: nearest_dists.append(min(dists))
            
            if nearest_dists and np.mean(nearest_dists) > 1.0:
                self.dispersion_time = self.steps
        
        if self.steps >= self.max_steps:
            for agent in self.agents:
                self.truncations[agent] = True
                self.infos[agent]["cause"] = "timeout"
        
        # Inject T-disperse into final info
        if self.dispersion_time:
            for agent in self.agents: self.infos[agent]["t_disperse"] = self.dispersion_time

        # 1. SNAPSHOT FIRST — capture exact crash state before teleportation
        observations = {agent: self._observe(agent) for agent in self.agents}

        # 2. TELEPORT DEAD DRONES — move them out of the way
        for agent in self.possible_agents:
            if self.terminations[agent] or self.truncations[agent]:
                idx = self.agent_name_mapping[agent]
                self.positions[idx] = np.array([-100.0, -100.0], dtype=np.float32)
                self.velocities[idx] = np.zeros(2, dtype=np.float32)

        # 3. REMOVE FROM ACTIVE LIST — after snapshot and teleport
        self.agents = [agent for agent in self.agents if not (self.terminations[agent] or self.truncations[agent])]

        return observations, rewards, self.terminations, self.truncations, self.infos

    def render(self):
        if self.render_mode != "human": return
        if self.screen is None:
            pygame.init()
            pygame.display.set_caption("Phase B - Swarm LiDAR Sim")
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
            self.clock = pygame.time.Clock()
        
        # 1. THE CRITICAL FIX: Pump the OS event queue so the window doesn't freeze
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        self.clock.tick(30)
        self.screen.fill((30, 30, 30)) # Dark gray background
        
        def w2s(x, y): 
            # Maps 20x20 physics coordinates to 800x800 screen pixels (flips Y axis)
            return int((x / self.WIDTH) * self.screen_width), int(self.screen_height - (y / self.HEIGHT) * self.screen_height)

        # 2. Draw Goal
        pygame.draw.circle(self.screen, (60, 200, 60), w2s(self.goal[0], self.goal[1]), int((0.75 / self.WIDTH) * self.screen_width))
        
        # 3. Draw Obstacles (With Fat Boundary Visualization)
        for ox, oy, orad in self.obstacles:
            center = w2s(ox, oy)
            actual_radius_px = int((orad / self.WIDTH) * self.screen_width)
            fat_radius_px = int(((orad + self.drone_radius) / self.WIDTH) * self.screen_width)
            
            # Draw the actual solid physical obstacle (Solid Gray)
            pygame.draw.circle(self.screen, (150, 150, 150), center, actual_radius_px)

        # 4. Draw Drones and their Velocity Vectors
        drone_radius_px = max(1, int((self.drone_radius / self.WIDTH) * self.screen_width))
        for agent in self.agents:
            idx = self.agent_name_mapping[agent]
            screen_pos = w2s(self.positions[idx][0], self.positions[idx][1])
            
            # Draw Drone Body
            pygame.draw.circle(self.screen, (100, 100, 255), screen_pos, drone_radius_px)
            
            # Draw Velocity line (shows which way it is flying)
            vel = self.velocities[idx]
            if np.linalg.norm(vel) > 0.1:
                end_x = self.positions[idx][0] + vel[0] * 0.5
                end_y = self.positions[idx][1] + vel[1] * 0.5
                pygame.draw.line(self.screen, (255, 255, 255), screen_pos, w2s(end_x, end_y), 2)

        pygame.display.flip()

# ======================================================
#  UPDATED MAIN TESTING LOOP
# ======================================================
if __name__ == "__main__":
    env = SwarmLidarEnv_StepB(render_mode="human")
    env.test_mode = True
    obs, info = env.reset()
    
    print("🚀 Running Visual Test! Close the PyGame window to stop.")
    
    # Changed from 100 steps to an infinite loop so it doesn't close instantly
    while True:
        # Sample random actions to make them fly around randomly
        actions = {agent: env.action_space(agent).sample() for agent in env.agents}
        obs, rewards, term, trunc, info = env.step(actions)
        
        env.render()
        
        if not env.agents: 
            obs, info = env.reset()
