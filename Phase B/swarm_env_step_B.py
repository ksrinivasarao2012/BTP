import numpy as np
import pygame
from pettingzoo import ParallelEnv
# make env also satisfy Gymnasium for SB3 vector wrappers
from gymnasium import spaces, Env as GymEnv
import math

# ======================================================
#  PHASE B: 10 Drones, 0 Traitors, STATIC OBSTACLES
# ======================================================
class SwarmLidarEnv_StepB(ParallelEnv, GymEnv):
    metadata = {'render_modes': ['human'], "name": "swarm_lidar_stepB_v0"}

    def __init__(self, render_mode=None, target_density=0.20, drone_radius=0.15, safety_radius=0.18):
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

        # Observation Space:
        # Lidar (16) + self_vel (2) + to_goal (2) + dist_goal (1) + heading (1) 
        # + [neighbor_pos (2) + neighbor_vel (2) + broadcast_id (1)] * (N-1)
        obs_size = 22 + (5 * (self.n_drones - 1))
        self.observation_spaces = {
            agent: spaces.Box(low=-np.inf, high=np.inf, shape=(obs_size,), dtype=np.float32)
            for agent in self.possible_agents
        }

        # PyGame Rendering
        self.screen_width = 800
        self.screen_height = 800
        self.screen = None
        self.clock = None

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
        
        # 1. Configurable Global Goal
        if options and "goal" in options:
            self.goal = np.array(options["goal"], dtype=np.float32)
        else:
            self.goal = np.array([np.random.uniform(2.0, self.WIDTH - 2.0), np.random.uniform(2.0, self.HEIGHT - 2.0)], dtype=np.float32)

        # 2. Phase B Obstacle Generation (Surface Area Density)
        if options and "obstacles" in options:
            self.obstacles = options["obstacles"] # Load from exact JSON
            # Still verify solvability for loaded maps
            if not self._is_map_solvable():
                print("⚠️  Loaded map is unsolvable! Resorting to random generation...")
                self.obstacles = []
        
        # Generate random obstacles if needed or if loaded map was invalid
        if not self.obstacles:
            target_area = (self.WIDTH * self.HEIGHT) * self.target_density
            current_area = 0.0
            
            # Avoid placing obstacles directly on top of the goal
            safe_goal_radius = 2.0 
            
            # Determine intended spawn center for solvability check
            if np.random.random() < 0.8:
                spawn_center = np.array([np.random.uniform(3.0, self.WIDTH - 3.0), np.random.uniform(3.0, self.HEIGHT - 3.0)])
            else:
                spawn_center = np.array([self.WIDTH / 2.0, self.HEIGHT / 2.0])

            # Keep regenerating until we get a solvable map
            max_attempts = 15
            attempt = 0
            while attempt < max_attempts:
                self.obstacles = []
                current_area = 0.0
                
                while current_area < target_area:
                    # Pick a random size (Massive, Medium, or Tiny)
                    choice = np.random.random()
                    if choice < 0.2:
                        r = np.random.uniform(1.5, 2.5) # Rare massive boulders
                    elif choice < 0.6:
                        r = np.random.uniform(0.6, 1.4) # Common medium blocks
                    else:
                        r = np.random.uniform(0.2, 0.5) # Abundant tiny pillars
                        
                    x = np.random.uniform(r, self.WIDTH - r)
                    y = np.random.uniform(r, self.HEIGHT - r)
                    
                    # Check goal clearance
                    if np.linalg.norm(np.array([x, y]) - self.goal) < (r + safe_goal_radius):
                        continue
                        
                    self.obstacles.append((x, y, r))
                    current_area += np.pi * (r ** 2)
                
                # Verify this map is solvable from the intended spawn location
                if self._is_map_solvable(start_pos=spawn_center):
                    break  # ✅ Solvable map found
                else:
                    attempt += 1
            
            if attempt >= max_attempts:
                print(f"⚠️  Failed to generate solvable map after {max_attempts} attempts! Using sparse fallback.")
                self.obstacles = []  # Empty obstacles as fallback
            
            # --- Continue with drone placement using the verified spawn_center if clustered ---
            # (Note: We'll reuse spawn_center later in the clustered spawn logic to stay consistent)
            self._cached_spawn_center = spawn_center
        
        
        # 3. Configurable Start Positions (Spawning Drones)
        if options and "start_positions" in options:
            self.positions = np.array(options["start_positions"], dtype=np.float32)
            self.velocities = np.zeros((self.n_drones, 2), dtype=np.float32)
        else:
            self.velocities = np.zeros((self.n_drones, 2), dtype=np.float32)
            # Use the center we verified during obstacle generation if it was a clustered intent
            if hasattr(self, "_cached_spawn_center"):
                cx, cy = self._cached_spawn_center
                is_clustered = (np.linalg.norm(self._cached_spawn_center - np.array([self.WIDTH/2, self.HEIGHT/2])) > 1e-1) or (np.random.random() < 0.8)
            else:
                cx, cy = np.random.uniform(3.0, self.WIDTH - 3.0), np.random.uniform(3.0, self.HEIGHT - 3.0)
                is_clustered = np.random.random() < 0.8

            if is_clustered:
                # --- CLUSTERED SPAWN ---
                half = 1.0  # 2x2 box
                min_dist = 0.3
                placed = []
                for i in range(self.n_drones):
                    found_valid = False
                    for attempt in range(500):
                        x = np.random.uniform(cx - half, cx + half)
                        y = np.random.uniform(cy - half, cy + half)
                        x = np.clip(x, 0.3, self.WIDTH - 0.3)
                        y = np.clip(y, 0.3, self.HEIGHT - 0.3)
                        
                        # Check drone-to-drone distance
                        drone_valid = all(np.sqrt((x-px)**2 + (y-py)**2) >= min_dist for px, py in placed)
                        
                        # Check obstacle collision (FIX: Add this check!)
                        obstacle_valid = all(np.sqrt((x-ox)**2 + (y-oy)**2) >= (self.drone_radius + orad) for ox, oy, orad in self.obstacles)
                        
                        if drone_valid and obstacle_valid:
                            placed.append([x, y])
                            found_valid = True
                            break
                    
                    if not found_valid:
                        # Fallback: expand area and try again
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
                            # Last resort: pick any random position
                            placed.append([np.random.uniform(1.0, self.WIDTH-1.0), np.random.uniform(1.0, self.HEIGHT-1.0)])
                    
                    self.positions[i] = np.array(placed[-1], dtype=np.float32)
            else:
                # --- RANDOM SPREAD SPAWN (20%) ---
                for i in range(self.n_drones):
                    valid = False
                    for _ in range(100):
                        x = np.random.uniform(1.0, self.WIDTH - 1.0)
                        y = np.random.uniform(1.0, self.HEIGHT - 1.0)
                        
                        # Check obstacle collision during random spawn
                        if all(np.sqrt((x-ox)**2 + (y-oy)**2) >= (self.drone_radius + orad) for ox, oy, orad in self.obstacles):
                            self.positions[i] = np.array([x, y], dtype=np.float32)
                            valid = True
                            break
                    
                    if not valid:
                        # Fallback to push-out logic
                        self.positions[i] = np.array([np.random.uniform(1.0, self.WIDTH-1.0), np.random.uniform(1.0, self.HEIGHT-1.0)], dtype=np.float32)
            
        # 4. FINAL SAFETY CHECK: Pop out any drones still inside obstacles
        for i in range(self.n_drones):
            for ox, oy, orad in self.obstacles:
                dist = np.linalg.norm(self.positions[i] - np.array([ox, oy]))
                if dist < (self.drone_radius + orad):
                    # Calculate direction to push drone out
                    vec = self.positions[i] - np.array([ox, oy])
                    norm = np.linalg.norm(vec)
                    if norm < 1e-6:
                        # Drone exactly at obstacle center - push in random direction
                        vec = np.array([np.random.uniform(-1, 1), np.random.uniform(-1, 1)])
                        norm = np.linalg.norm(vec)
                    
                    # Push drone out with safety margin
                    vec_normalized = vec / (norm + 1e-6)
                    safe_distance = self.drone_radius + orad + 0.1  # Extra margin
                    self.positions[i] = np.array([ox, oy]) + vec_normalized * safe_distance
                    
                    # Clamp to map bounds
                    self.positions[i][0] = np.clip(self.positions[i][0], 0.2, self.WIDTH - 0.2)
                    self.positions[i][1] = np.clip(self.positions[i][1], 0.2, self.HEIGHT - 0.2)
                    
        observations = {agent: self._observe(agent) for agent in self.agents}
        return observations, self.infos

    def _is_map_solvable(self, start_pos=None, min_path_width=0.4, grid_resolution=0.2):
        """
        B1.2: Choke-Point Verifier
        
        Uses BFS on a discretized grid to verify that a path exists from the start
        to the goal.
        
        Args:
            start_pos: (x, y) starting coordinate. Defaults to map center.
            min_path_width: Minimum corridor width required (default 0.4m for 0.3m drone)
            grid_resolution: Granularity of BFS grid (default 0.2m)
        """
        from collections import deque
        
        if start_pos is None:
            start_pos = np.array([self.WIDTH / 2.0, self.HEIGHT / 2.0])
        
        # Discretize the map into grid cells
        grid_size = int(np.ceil(self.WIDTH / grid_resolution))
        grid = np.ones((grid_size, grid_size), dtype=bool)  # True = passable
        
        # Mark obstacle cells as blocked
        # Clearance: Drone radius + small safety margin
        clearance_radius = self.drone_radius + 0.05 # 0.20m radius total clearance
        
        for ox, oy, orad in self.obstacles:
            # Find all grid cells within obstacle's collision radius
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
        
        # BFS from the actual start center to goal
        spawn_cell = (int(start_pos[0] / grid_resolution), int(start_pos[1] / grid_resolution))
        goal_cell = (int(self.goal[0] / grid_resolution), int(self.goal[1] / grid_resolution))
        
        # Clamp to grid bounds
        spawn_cell = (np.clip(spawn_cell[0], 0, grid_size - 1), np.clip(spawn_cell[1], 0, grid_size - 1))
        goal_cell = (np.clip(goal_cell[0], 0, grid_size - 1), np.clip(goal_cell[1], 0, grid_size - 1))
        
        # If spawn or goal is blocked, map is unsolvable
        if not grid[spawn_cell[0], spawn_cell[1]] or not grid[goal_cell[0], goal_cell[1]]:
            return False
        
        # BFS traversal
        queue = deque([spawn_cell])
        visited = set([spawn_cell])
        
        while queue:
            x, y = queue.popleft()
            
            # Check if we reached the goal
            if (x, y) == goal_cell:
                return True  # ✅ Path found!
            
            # Explore neighbors (8-connected grid)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    
                    # Check bounds and passability
                    if 0 <= nx < grid_size and 0 <= ny < grid_size:
                        if grid[nx, ny] and (nx, ny) not in visited:
                            visited.add((nx, ny))
                            queue.append((nx, ny))
        
        # If BFS completes without reaching goal, map is unsolvable
        return False

    def _ray_cast(self, agent_idx):
        """
        Simulates Volumetric Sector-Scanning (IEEE Journal Standard).
        Instead of 16 discrete rays, we use 16 sensor channels, each covering a 22.5-degree FOV.
        We sample 3 points within each FOV and return the MINIMUM distance to ensure no blind spots.
        """
        num_sectors = 16
        max_range = 8.0 
        readings = np.full(num_sectors, max_range, dtype=np.float32)
        sector_width = (2*np.pi) / num_sectors
        pos = self.positions[agent_idx]
        
        for i in range(num_sectors):
            center_angle = i * sector_width
            min_d = max_range
            
            # IEEE High-Fidelity: Sample 5 points within each 22.5° FOV
            # This ensures that even at 8m range, no obstacle can slip through.
            sub_angles = np.linspace(center_angle - sector_width/2, 
                                    center_angle + sector_width/2, 5)
            
            for angle in sub_angles:
                ray_dir = np.array([math.cos(angle), math.sin(angle)])
                
                # Wall checks
                for boundary, axis, direction in [(self.WIDTH, 0, 1), (0, 0, -1), (self.HEIGHT, 1, 1), (0, 1, -1)]:
                    if ray_dir[axis] * direction > 0:
                        d = (boundary - pos[axis]) / ray_dir[axis]
                        if 0 < d < min_d: min_d = d
                        
                # Static Obstacle Checks (C-space inflation)
                for ox, oy, orad in self.obstacles:
                    to_obs = np.array([ox, oy]) - pos
                    proj = np.dot(to_obs, ray_dir)
                    if proj > 0:
                        closest = pos + proj * ray_dir
                        dist_to_ray = np.linalg.norm(closest - np.array([ox, oy]))
                        # Inflate obstacle by drone radius
                        inflated_radius = orad + self.drone_radius
                        if dist_to_ray < inflated_radius:
                            intersect_dist = proj - math.sqrt(inflated_radius**2 - dist_to_ray**2)
                            if 0 < intersect_dist < min_d:
                                min_d = intersect_dist
                
                # Drone Interaction checks
                for j in range(self.n_drones):
                    if j == agent_idx: continue
                    if self.possible_agents[j] not in self.agents: continue 
                    
                    to_drone = self.positions[j] - pos
                    proj = np.dot(to_drone, ray_dir)
                    if proj > 0:
                        closest = pos + proj * ray_dir
                        dist_to_ray = np.linalg.norm(closest - self.positions[j])
                        drone_radius = self.drone_radius
                        if dist_to_ray < drone_radius:
                            intersect_dist = proj - math.sqrt(drone_radius**2 - dist_to_ray**2)
                            if 0 < intersect_dist < min_d: min_d = intersect_dist

            readings[i] = min_d
        return readings

    def _observe(self, agent):
        idx = self.agent_name_mapping[agent]
        pos = self.positions[idx]
        vel = self.velocities[idx]
        
        dist_goal = np.linalg.norm(self.goal - pos)
        to_goal = (self.goal - pos) / (dist_goal + 1e-5)
        lidar = self._ray_cast(idx) / 8.0 # Normalize
        
        # Self Kinematics (22 values)
        obs_core = np.concatenate([
            vel / self.max_velocity,
            to_goal,
            [dist_goal / (self.WIDTH * 1.414)], 
            [np.arctan2(vel[1], vel[0])],
            lidar
        ])
        
        # Neighbor Broadcast States (Digital Communication)
        obs_neighbors = []
        for j in range(self.n_drones):
            if j == idx: continue
            
            # Ground truth relative sensing
            rel_pos = (self.positions[j] - pos) / self.WIDTH
            norm_vel = self.velocities[j] / self.max_velocity
            is_active = 1.0 if self.possible_agents[j] in self.agents else 0.0
            
            obs_neighbors.append(np.concatenate([rel_pos, norm_vel, [is_active]]))
            
        return np.concatenate([obs_core, np.concatenate(obs_neighbors)]).astype(np.float32)

    def step(self, actions):
        if not self.agents:
            return {}, {}, {}, {}, {}

        old_positions = np.copy(self.positions)

        # 1. Physics Update
        for agent, action in actions.items():
            idx = self.agent_name_mapping[agent]
            action = np.clip(action, -1.0, 1.0)
            
            # Industrial Standard: High-Torque Acceleration (10.0 instead of 5.0)
            # This allows the drone to physically execute the "Dodge" maneuver.
            self.velocities[idx] += action * self.dt * 10.0
            speed = np.linalg.norm(self.velocities[idx])
            if speed > self.max_velocity: 
                self.velocities[idx] = (self.velocities[idx] / speed) * self.max_velocity
                
            self.positions[idx] += self.velocities[idx] * self.dt
            
            # PHYSICAL BOUNDARY CONSTANT: Prevent flying off map
            self.positions[idx][0] = np.clip(self.positions[idx][0], 0.0, self.WIDTH)
            self.positions[idx][1] = np.clip(self.positions[idx][1], 0.0, self.HEIGHT)

        self.steps += 1
        rewards = {agent: 0.0 for agent in self.agents}
        
        # 2. Reward Calculation
        for agent in self.agents:
            idx = self.agent_name_mapping[agent]
            pos = self.positions[idx]
            old_pos = old_positions[idx]
            dist_goal = np.linalg.norm(self.goal - pos)
            old_dist_goal = np.linalg.norm(self.goal - old_pos)
            
            # --- R_goal: Potential Field ---
            # Reward for moving closer to the goal, penalize for moving away
            r_goal = 10.0 * (0.995 * (-dist_goal) - (-old_dist_goal))
            r_goal -= 0.05 # Existential penalty (time cost)
            rewards[agent] += r_goal
            
            # --- R_group: Cohesion Reward ---
            # Reward for staying near other honest drones (within 4.0m)
            r_group = 0.0
            neighbors_in_range = 0
            for j in range(self.n_drones):
                if j == idx: continue
                dist_to_neighbor = np.linalg.norm(pos - self.positions[j])
                if 0.6 < dist_to_neighbor < 4.0: 
                    neighbors_in_range += 1
            rewards[agent] += (neighbors_in_range * 0.01) # Small continuous bonus
            
            # --- R_cluster: Center of Mass & Speed Limit (School Zone) ---
            close_neighbors = []
            for j in range(self.n_drones):
                if j == idx: continue
                if self.possible_agents[j] not in self.agents: continue
                if np.linalg.norm(pos - self.positions[j]) < 0.55 or np.linalg.norm(old_pos - old_positions[j]) < 0.55:
                    close_neighbors.append(j)
                    
            if len(close_neighbors) > 0:
                # Approach 1: Unified Center of Mass Expansion
                # DEACTIVATED: Causes "Wall-Ramming" in narrow corridors.
                # com_positions = [self.positions[j] for j in close_neighbors]
                # local_com = np.mean(com_positions, axis=0)
                # dist_to_com_now = np.linalg.norm(pos - local_com)
                # dist_to_com_before = np.linalg.norm(old_pos - local_com)
                # delta_com = dist_to_com_now - dist_to_com_before
                # rewards[agent] += np.clip(delta_com * 30.0, -3.0, 3.0)
                
                # Approach 2: "School Zone" Speed Limit
                # Penalize moving fast when surrounded by drones to avoid instantaneous collisions
                speed = np.linalg.norm(self.velocities[idx])
                safe_speed = self.max_velocity * 0.35 # 35% speed limit when tangled
                if speed > safe_speed:
                    speed_penalty = ((speed - safe_speed) / self.max_velocity) ** 2
                    rewards[agent] -= speed_penalty * len(close_neighbors) * 2.0 # Reduced from 5.0 for flow
                    
                # Approach 3: Social Distancing Repulsion
                # Prevent funneling by penalizing drones within safety_radius * 1.2
                repulsion_dist = self.safety_radius * 1.2
                for j in close_neighbors:
                    dist = np.linalg.norm(pos - self.positions[j])
                    if dist < repulsion_dist:
                        rewards[agent] -= (repulsion_dist - dist) * 50.0 # Reduced from 75 for confidence
            
            # --- R_safe & Terminations ---
            hit_wall = False
            hit_drone = False
            hit_obstacle = False
            
            # Map Bounds Validation (Crash if they touch the literal edge)
            distance_to_edge = min(pos[0], self.WIDTH - pos[0], pos[1], self.HEIGHT - pos[1])
            if distance_to_edge <= 0.05: 
                hit_wall = True
            
            # Phase B: Static Obstacle Collision Check (C-space)
            for ox, oy, orad in self.obstacles:
                if np.linalg.norm(pos - np.array([ox, oy])) < (self.drone_radius + orad):
                    hit_obstacle = True
                    break
            
            # Swarm Drone-on-Drone Collision Check
            for j in range(self.n_drones):
                if j == idx: continue
                # NEW FIX: Ignore hitting drones that have already won/died
                if self.possible_agents[j] not in self.agents: continue 
                
                if np.linalg.norm(pos - self.positions[j]) < (2 * self.drone_radius):
                    hit_drone = True
                    break

            if hit_wall:
                rewards[agent] = -100.0 # Baseline penalty
                self.terminations[agent] = True
                self.infos[agent] = {"cause": "collision"}
            elif hit_obstacle:
                rewards[agent] = -100.0 
                self.terminations[agent] = True
                self.infos[agent] = {"cause": "collision"}
            elif hit_drone:
                rewards[agent] = -50.0  # Baseline penalty
                self.terminations[agent] = True
                self.infos[agent] = {"cause": "collision"}
            elif dist_goal < 0.75:
                # Success check
                speed = np.linalg.norm(self.velocities[idx])
                rewards[agent] += 100.0 + (50.0 / (1.0 + speed)) # Success + smooth stop bonus
                self.terminations[agent] = True
                self.infos[agent] = {"cause": "success"}
                
        # Truncations (Timeout)
        if self.steps >= self.max_steps:
             for agent in self.agents:
                 self.truncations[agent] = True

        self.agents = [agent for agent in self.agents if not (self.terminations[agent] or self.truncations[agent])]
        observations = {agent: self._observe(agent) for agent in self.agents}
        
        return observations, rewards, self.terminations, self.truncations, self.infos

    def render(self):
        if self.render_mode != "human": return
        if self.screen is None:
            pygame.init()
            pygame.display.set_caption("Phase B: 10 Drones + Static Obstacles")
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
            self.clock = pygame.time.Clock()
            
        self.clock.tick(30)
        self.screen.fill((30, 30, 30))
        
        def w2s(p):
            # Strict visual clamp so even if float math has an epsilon error it won't draw off map
            px = max(0.0, min(float(p[0]), self.WIDTH))
            py = max(0.0, min(float(p[1]), self.HEIGHT))
            return int((px / self.WIDTH) * self.screen_width), int(self.screen_height - (py / self.HEIGHT) * self.screen_height)
            
        # Draw Goal
        pygame.draw.circle(self.screen, (60, 200, 60), w2s(self.goal), 20)
            
        # Draw Phase B Static Obstacles
        for ox, oy, orad in self.obstacles:
            radius_pixels = int((orad / self.WIDTH) * self.screen_width)
            pygame.draw.circle(self.screen, (150, 150, 150), w2s((ox, oy)), radius_pixels)
            # Draw a darker outline for depth
            pygame.draw.circle(self.screen, (100, 100, 100), w2s((ox, oy)), radius_pixels, 2)
            
        # Draw Agents (Only draw active agents to prevent ghost drones)
        for agent in self.agents:
            idx = self.agent_name_mapping[agent]
            pygame.draw.circle(self.screen, (100, 100, 255), w2s(self.positions[idx]), 8)
            
        pygame.display.flip()

    def observation_space(self, agent):
        return self.observation_spaces[agent]

    def action_space(self, agent):
        return self.action_spaces[agent]

# Execution test block
if __name__ == "__main__":
    env = SwarmLidarEnv_StepB(render_mode="human")
    obs, info = env.reset()
    
    print("Environment Phase B initialized! Running random actions to preview PyGame...")
    
    for _ in range(300):
        actions = {agent: env.action_space(agent).sample() for agent in env.agents}
        obs, rewards, term, trunc, info = env.step(actions)
        env.render()
        
        if not env.agents:
            obs, info = env.reset()
            
    pygame.quit()
    print("Preview complete.")
