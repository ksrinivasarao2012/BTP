import numpy as np
import matplotlib.pyplot as plt
from collections import deque


class SwarmEnv:
    """
    2D continuous multi-agent drone swarm navigation environment.
    10 autonomous drones navigate to a shared goal in a 20x20 field
    with randomly generated circular obstacles.
    """

    # Fixed environment constants
    FIELD_W = 20.0
    FIELD_H = 20.0
    DRONE_RADIUS = 0.15
    N_DRONES = 10
    DT = 0.1
    MAX_STEPS = 1200
    V_MAX = 1.2
    LIDAR_RAYS = 72
    LIDAR_RANGE = 8.0
    COMM_RANGE = 8.0
    GOAL_REACH_THRESHOLD = 0.6
    DRONE_DRONE_COLLISION_DIST = 2 * DRONE_RADIUS
    SPAWN_WALL_CLEARANCE = 0.60  # minimum distance from wall to drone center at spawn time only
    BFS_WALL_CLEARANCE = 0.20    # wall clearance padding used in BFS grid construction only
    BFS_GRID_RES = 0.2

    # Benchmark map generation parameters
    TARGET_DENSITY = 0.25
    CLUSTER_RADIUS = 1.5
    SPAWN_OBSTACLE_CLEARANCE = 0.30
    SC_GOAL_MIN_DIST = 7.0
    GOAL_SPAWN_CLEARANCE = 6.0
    INTER_DRONE_MIN = 0.30
    GOAL_EXCLUSION_RADIUS = 0.70

    # Max distance (diagonal of field) for normalizing reward potentials
    MAX_DISTANCE = np.sqrt(20.0**2 + 20.0**2)  # ~28.28 units

    def __init__(self, target_density=0.25, seed=None,
                 enable_communication=False):
        """
        Initialize the swarm environment.

        Args:
            target_density: Obstacle density (default 0.25)
            seed: Random seed for reproducibility
            enable_communication: If True, fill neighbor slots with real data
        """
        self.target_density = target_density
        self.enable_communication = enable_communication
        self.rng = np.random.RandomState(seed)

        self.step_count = 0
        self.active_drones = set(range(self.N_DRONES))
        self.drone_positions = np.zeros((self.N_DRONES, 2), dtype=np.float32)
        self.drone_velocities = np.zeros((self.N_DRONES, 2), dtype=np.float32)
        self.goal = np.zeros(2, dtype=np.float32)
        self.obstacles = []
        self._lidar_cache = {}

    def _generate_obstacles(self):
        """Generate random circular obstacles until target density is reached."""
        field_area = self.FIELD_W * self.FIELD_H
        target_area = field_area * self.target_density

        grid_res = 0.05
        grid_w = int(np.ceil(self.FIELD_W / grid_res))
        grid_h = int(np.ceil(self.FIELD_H / grid_res))
        occupied = np.zeros((grid_w, grid_h), dtype=bool)

        self.obstacles = []
        current_area = 0.0
        attempts = 0
        max_attempts = 3000

        while current_area < target_area and attempts < max_attempts:
            r = self.rng.uniform(0, 1)
            if r < 0.2:
                radius = self.rng.uniform(1.5, 2.5)
            elif r < 0.6:
                radius = self.rng.uniform(0.6, 1.4)
            else:
                radius = self.rng.uniform(0.2, 0.5)

            cx = self.rng.uniform(radius, self.FIELD_W - radius)
            cy = self.rng.uniform(radius, self.FIELD_H - radius)

            overlaps = False
            for (ox, oy), or_ in self.obstacles:
                if np.sqrt((cx - ox)**2 + (cy - oy)**2) < radius + or_:
                    overlaps = True
                    break

            if overlaps:
                attempts += 1
                continue

            if np.sqrt((cx - self.goal[0])**2 + (cy - self.goal[1])**2) < \
                    self.GOAL_EXCLUSION_RADIUS + radius:
                attempts += 1
                continue

            gx_min = max(0, int(np.floor((cx - radius) / grid_res)))
            gx_max = min(grid_w - 1, int(np.ceil((cx + radius) / grid_res)))
            gy_min = max(0, int(np.floor((cy - radius) / grid_res)))
            gy_max = min(grid_h - 1, int(np.ceil((cy + radius) / grid_res)))

            # Build array of cell centers in bounding box
            xs = (np.arange(gx_min, gx_max + 1) + 0.5) * grid_res
            ys = (np.arange(gy_min, gy_max + 1) + 0.5) * grid_res
            xx, yy = np.meshgrid(xs, ys, indexing='ij')

            # Find which cells fall inside the new obstacle circle
            inside = (xx - cx)**2 + (yy - cy)**2 <= radius**2

            # Check if any of those cells are already occupied
            patch = occupied[gx_min:gx_max+1, gy_min:gy_max+1]
            if np.any(inside & patch):
                attempts += 1
                continue

            # Mark only the cells inside the circle as occupied
            occupied[gx_min:gx_max+1, gy_min:gy_max+1] |= inside
            self.obstacles.append(((cx, cy), radius))
            current_area += np.pi * radius**2
            attempts += 1

        if current_area < target_area * 0.95:
            return False
        return True

    def _sample_goal(self):
        """Sample goal position, must not be within any obstacle."""
        for _ in range(200):
            gx = self.rng.uniform(2.0, 18.0)
            gy = self.rng.uniform(2.0, 18.0)

            in_obstacle = False
            for (ox, oy), radius in self.obstacles:
                if np.sqrt((gx - ox)**2 + (gy - oy)**2) < radius + self.GOAL_EXCLUSION_RADIUS:
                    in_obstacle = True
                    break

            if not in_obstacle:
                self.goal = np.array([gx, gy], dtype=np.float32)
                return True

        return False

    def _sample_spawn_center(self):
        """Sample spawn center, must be >= SC_GOAL_MIN_DIST from goal."""
        for _ in range(200):
            sx = self.rng.uniform(2.0, 18.0)
            sy = self.rng.uniform(2.0, 18.0)

            if np.sqrt((sx - self.goal[0])**2 + (sy - self.goal[1])**2) >= \
                    self.SC_GOAL_MIN_DIST:
                return np.array([sx, sy], dtype=np.float32)

        return np.array([2.0, 2.0], dtype=np.float32)

    def _is_valid_drone_position(self, px, py, placed, check_neighbors=True):
        """Check if drone position satisfies all constraints."""
        if not (self.SPAWN_WALL_CLEARANCE <= px <= self.FIELD_W - self.SPAWN_WALL_CLEARANCE and
                self.SPAWN_WALL_CLEARANCE <= py <= self.FIELD_H - self.SPAWN_WALL_CLEARANCE):
            return False

        for (ox, oy), radius in self.obstacles:
            dist = np.sqrt((px - ox)**2 + (py - oy)**2)
            if dist < radius + self.DRONE_RADIUS + self.SPAWN_OBSTACLE_CLEARANCE:
                return False

        if np.sqrt((px - self.goal[0])**2 + (py - self.goal[1])**2) < \
                self.GOAL_SPAWN_CLEARANCE:
            return False

        if check_neighbors:
            for px2, py2 in placed:
                if np.sqrt((px - px2)**2 + (py - py2)**2) < \
                        2 * self.DRONE_RADIUS + self.INTER_DRONE_MIN:
                    return False

        return True

    def _place_drones(self, spawn_center):
        """
        Place 10 drones by randomly sampling within cluster radius.

        First tries CLUSTER_RADIUS. If that fails, retries with fallback radius.
        """
        def attempt_placement(radius):
            placed = []
            for drone_idx in range(self.N_DRONES):
                placed_this_drone = False
                for attempt in range(150):
                    angle = self.rng.uniform(0, 2 * np.pi)
                    dist = self.rng.uniform(0, radius)
                    px = spawn_center[0] + dist * np.cos(angle)
                    py = spawn_center[1] + dist * np.sin(angle)

                    if self._is_valid_drone_position(px, py, placed):
                        placed.append([px, py])
                        placed_this_drone = True
                        break

                if not placed_this_drone:
                    return None

            return placed

        placed = attempt_placement(self.CLUSTER_RADIUS)
        if placed is None:
            placed = attempt_placement(self.CLUSTER_RADIUS + 1.5)
        if placed is None:
            return False

        for i in range(self.N_DRONES):
            self.drone_positions[i] = placed[i]

        return True

    def _bfs_solvability_check(self):
        """Verify all 10 drones have valid BFS paths to goal."""
        grid_res = self.BFS_GRID_RES
        grid_w = int(np.ceil(self.FIELD_W / grid_res))
        grid_h = int(np.ceil(self.FIELD_H / grid_res))
        blocked = np.zeros((grid_w, grid_h), dtype=bool)

        for (ox, oy), radius in self.obstacles:
            inflate = radius + self.BFS_WALL_CLEARANCE
            i_min = max(0, int(np.floor((ox - inflate) / grid_res)))
            i_max = min(grid_w - 1, int(np.ceil((ox + inflate) / grid_res)))
            j_min = max(0, int(np.floor((oy - inflate) / grid_res)))
            j_max = min(grid_h - 1, int(np.ceil((oy + inflate) / grid_res)))

            xs = (np.arange(i_min, i_max + 1) + 0.5) * grid_res
            ys = (np.arange(j_min, j_max + 1) + 0.5) * grid_res
            xx, yy = np.meshgrid(xs, ys, indexing='ij')

            inside = (xx - ox)**2 + (yy - oy)**2 <= inflate**2
            blocked[i_min:i_max+1, j_min:j_max+1] |= inside

        clearance_cells = int(np.ceil(self.BFS_WALL_CLEARANCE / grid_res))
        blocked[:clearance_cells, :] = True
        blocked[-clearance_cells:, :] = True
        blocked[:, :clearance_cells] = True
        blocked[:, -clearance_cells:] = True

        goal_x = int(self.goal[0] / grid_res)
        goal_y = int(self.goal[1] / grid_res)
        goal_x = np.clip(goal_x, 0, grid_w - 1)
        goal_y = np.clip(goal_y, 0, grid_h - 1)

        for drone_id in range(self.N_DRONES):
            start_x = int(self.drone_positions[drone_id, 0] / grid_res)
            start_y = int(self.drone_positions[drone_id, 1] / grid_res)
            start_x = np.clip(start_x, 0, grid_w - 1)
            start_y = np.clip(start_y, 0, grid_h - 1)

            if not self._bfs_path_exists(blocked, (start_x, start_y),
                                        (goal_x, goal_y)):
                return False

        return True

    def _bfs_path_exists(self, blocked, start, goal):
        """BFS with corner-cutting prevention."""
        queue = deque([start])
        visited = set([start])
        grid_w, grid_h = blocked.shape

        while queue:
            x, y = queue.popleft()

            if (x, y) == goal:
                return True

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1),
                           (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                nx, ny = x + dx, y + dy

                if not (0 <= nx < grid_w and 0 <= ny < grid_h):
                    continue

                if (nx, ny) in visited or blocked[nx, ny]:
                    continue

                if dx != 0 and dy != 0:
                    if blocked[x + dx, y] or blocked[x, y + dy]:
                        continue

                visited.add((nx, ny))
                queue.append((nx, ny))

        return False

    def _compute_shortest_path_distance_map(self):
        """Dijkstra Shortest-Path Grid Solver for exact 8-way diagonal physics"""
        import heapq
        grid_resolution = self.BFS_GRID_RES # 0.2
        grid_w = int(np.ceil(self.FIELD_W / grid_resolution))
        grid_h = int(np.ceil(self.FIELD_H / grid_resolution))
        grid = np.ones((grid_w, grid_h), dtype=bool)
        clearance_radius = self.DRONE_RADIUS + 0.05
        
        # Mark obstacle regions as blocked
        for (ox, oy), orad in self.obstacles:
            x_range = np.arange(max(0, int((ox - orad - clearance_radius) / grid_resolution)),
                               min(grid_w, int((ox + orad + clearance_radius) / grid_resolution) + 1))
            y_range = np.arange(max(0, int((oy - orad - clearance_radius) / grid_resolution)),
                               min(grid_h, int((oy + orad + clearance_radius) / grid_resolution) + 1))
            for gx in x_range:
                for gy in y_range:
                    cell_x = gx * grid_resolution + grid_resolution / 2
                    cell_y = gy * grid_resolution + grid_resolution / 2
                    if np.sqrt((cell_x - ox)**2 + (cell_y - oy)**2) < (orad + clearance_radius):
                        grid[gx, gy] = False
                        
        goal_cell = (np.clip(int(self.goal[0] / grid_resolution), 0, grid_w - 1),
                     np.clip(int(self.goal[1] / grid_resolution), 0, grid_h - 1))
                     
        self.shortest_path_map = np.full((grid_w, grid_h), 999.0, dtype=np.float32)
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
                    if 0 <= nx < grid_w and 0 <= ny < grid_h:
                        if grid[nx, ny]:
                            step_dist = np.sqrt(dx**2 + dy**2) * grid_resolution
                            new_dist = curr_dist + step_dist
                            if new_dist < self.shortest_path_map[nx, ny]:
                                self.shortest_path_map[nx, ny] = new_dist
                                heapq.heappush(pq, (new_dist, nx, ny))

    def get_shortest_path_distance(self, pos):
        """O(1) topological shortest-path distance query"""
        grid_resolution = self.BFS_GRID_RES
        grid_w = int(np.ceil(self.FIELD_W / grid_resolution))
        grid_h = int(np.ceil(self.FIELD_H / grid_resolution))
        gx = np.clip(int(pos[0] / grid_resolution), 0, grid_w - 1)
        gy = np.clip(int(pos[1] / grid_resolution), 0, grid_h - 1)
        dist = self.shortest_path_map[gx, gy]
        if dist >= 999.0:
            return np.linalg.norm(self.goal - pos)
        return dist

    def get_shortest_path_direction(self, pos):
        """Returns the unit vector pointing in the direction of shortest path descent"""
        grid_resolution = self.BFS_GRID_RES
        grid_w = int(np.ceil(self.FIELD_W / grid_resolution))
        grid_h = int(np.ceil(self.FIELD_H / grid_resolution))
        gx = np.clip(int(pos[0] / grid_resolution), 0, grid_w - 1)
        gy = np.clip(int(pos[1] / grid_resolution), 0, grid_h - 1)
        
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
                    if 0 <= nx < grid_w and 0 <= ny < grid_h:
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

    def _generate_map(self):
        """Generate obstacles, goal, and drone spawn."""
        max_retries = 20

        for attempt in range(max_retries):
            if not self._sample_goal():
                continue

            self.obstacles = []
            if not self._generate_obstacles():
                continue

            spawn_center = self._sample_spawn_center()
            if not self._place_drones(spawn_center):
                continue

            if not self._bfs_solvability_check():
                continue

            # Precompute Dijkstra Topological Shortest Path Map
            self._compute_shortest_path_distance_map()

            self.drone_velocities = np.zeros((self.N_DRONES, 2), dtype=np.float32)
            return True

        raise RuntimeError("Failed to generate valid map after 20 retries")

    def _get_lidar(self, drone_id):
        """Compute 72-ray LiDAR for a drone (vectorized)."""
        if drone_id in self._lidar_cache:
            return self._lidar_cache[drone_id]

        pos = self.drone_positions[drone_id]
        angles = np.linspace(0, 2 * np.pi, self.LIDAR_RAYS, endpoint=False)
        ray_dirs = np.stack([np.cos(angles), np.sin(angles)], axis=1)

        distances = np.full(self.LIDAR_RAYS, self.LIDAR_RANGE, dtype=np.float32)

        # --- Walls (analytical per-ray) ---
        for wall_coord, axis in [(0.0, 0), (self.FIELD_W, 0),
                                (0.0, 1), (self.FIELD_H, 1)]:
            with np.errstate(divide='ignore', invalid='ignore'):
                t = (wall_coord - pos[axis]) / ray_dirs[:, axis]
            valid = t > 1e-6
            distances = np.where(valid & (t < distances), t, distances)

        # --- Obstacles (vectorized ray-circle intersection) ---
        if self.obstacles:
            obs_centers = np.array([[ox, oy] for (ox, oy), _ in self.obstacles],
                                dtype=np.float32)
            obs_radii = np.array([r for _, r in self.obstacles], dtype=np.float32)

            oc = pos - obs_centers
            proj = ray_dirs @ oc.T
            oc_sq = np.sum(oc**2, axis=1)
            r_sq = obs_radii**2

            disc = proj**2 - (oc_sq - r_sq)
            hit = disc >= 0
            sqrt_disc = np.where(hit, np.sqrt(np.maximum(disc, 0)), 0)

            t1 = -proj - sqrt_disc
            t2 = -proj + sqrt_disc

            t_near = np.where(t1 > 1e-6, t1,
                    np.where(t2 > 1e-6, t2, np.float32(np.inf)))
            t_near = np.where(hit, t_near, np.inf)

            min_obs = np.min(t_near, axis=1)
            distances = np.minimum(distances, min_obs)

        # --- Other active drones (vectorized ray-circle intersection) ---
        other_ids = [i for i in self.active_drones if i != drone_id]
        if other_ids:
            other_pos = self.drone_positions[other_ids]
            oc = pos - other_pos
            r_sq = self.DRONE_RADIUS**2

            proj = ray_dirs @ oc.T
            oc_sq = np.sum(oc**2, axis=1)
            disc = proj**2 - (oc_sq - r_sq)

            hit = disc >= 0
            sqrt_disc = np.where(hit, np.sqrt(np.maximum(disc, 0)), 0)

            t1 = -proj - sqrt_disc
            t2 = -proj + sqrt_disc
            t_near = np.where(t1 > 1e-6, t1,
                    np.where(t2 > 1e-6, t2, np.float32(np.inf)))
            t_near = np.where(hit, t_near, np.inf)

            min_drone = np.min(t_near, axis=1)
            distances = np.minimum(distances, min_drone)

        distances = np.clip(distances, 0, self.LIDAR_RANGE)
        result = (distances / self.LIDAR_RANGE).astype(np.float32)
        self._lidar_cache[drone_id] = result
        return result

    def _get_obs(self, drone_id):
        """
        Build 151D observation vector.
        Component 1: LiDAR (72D)
        Component 2: Own state (7D)
        Component 3: Neighbor slots (72D)
        Total: 72 + 7 + 72 = 151D
        """
        obs = []

        # LiDAR (72D)
        lidar = self._get_lidar(drone_id)
        obs.extend(lidar)

        # Own state (7D)
        vx = self.drone_velocities[drone_id, 0] / self.V_MAX
        vy = self.drone_velocities[drone_id, 1] / self.V_MAX
        x = self.drone_positions[drone_id, 0] / self.FIELD_W
        y = self.drone_positions[drone_id, 1] / self.FIELD_H
        
        # Use Dijkstra topological steering direction and shortest path distance
        to_goal_dir = self.get_shortest_path_direction(self.drone_positions[drone_id])
        goal_dx = to_goal_dir[0]
        goal_dy = to_goal_dir[1]
        dist_to_goal = self.get_shortest_path_distance(self.drone_positions[drone_id]) / 28.28

        obs.extend([vx, vy, x, y, goal_dx, goal_dy, dist_to_goal])

        # Neighbor slots (72D: 9 neighbors × 8 values)
        neighbors_data = []
        for neighbor_id in range(self.N_DRONES):
            if neighbor_id == drone_id:
                continue

            neighbor_dist = np.linalg.norm(
                self.drone_positions[neighbor_id] - self.drone_positions[drone_id])

            if (neighbor_id in self.active_drones and neighbor_dist <= self.COMM_RANGE):
                neighbor_pos = self.drone_positions[neighbor_id]
                neighbor_vel = self.drone_velocities[neighbor_id]

                # Normalize relative coordinates by COMM_RANGE (8.0m) to improve spatial resolution
                rel_x = (neighbor_pos[0] - self.drone_positions[drone_id, 0]) / self.COMM_RANGE
                rel_y = (neighbor_pos[1] - self.drone_positions[drone_id, 1]) / self.COMM_RANGE
                n_vx = neighbor_vel[0] / self.V_MAX
                n_vy = neighbor_vel[1] / self.V_MAX
                
                # Consistent Dijkstra pathing for neighbors
                n_dist_goal = self.get_shortest_path_distance(neighbor_pos) / 28.28
                n_goal_dir = self.get_shortest_path_direction(neighbor_pos)
                n_goal_dx = n_goal_dir[0]
                n_goal_dy = n_goal_dir[1]
                active_flag = 1.0

                neighbors_data.append((
                    neighbor_dist, 
                    [rel_x, rel_y, n_vx, n_vy, n_dist_goal, n_goal_dx, n_goal_dy, active_flag]
                ))

        # Sort neighbors by distance (closest first)
        neighbors_data.sort(key=lambda x: x[0])

        # Fill the slots
        for _, slot_features in neighbors_data:
            obs.extend(slot_features)

        # Pad remaining slots with zeros
        remaining_slots = (self.N_DRONES - 1) - len(neighbors_data)
        for _ in range(remaining_slots):
            obs.extend([0.0] * 8)

        obs_array = np.array(obs, dtype=np.float32)
        assert len(obs_array) == 151, f"Observation shape {len(obs_array)} != 151"
        return obs_array

    def step(self, actions):
        """
        Step environment with actions for all active drones.

        Args:
            actions: dict {drone_id: np.array([vx, vy])}

        Returns:
            obs, rewards, dones, truncated, infos
        """
        self._lidar_cache.clear()
        self.step_count += 1

        dist_before = {drone_id: self.get_shortest_path_distance(self.drone_positions[drone_id])
                       for drone_id in self.active_drones}

        old_positions = self.drone_positions.copy()

        # Apply actions
        for drone_id, action in actions.items():
            dist_to_goal = np.linalg.norm(self.goal - self.drone_positions[drone_id])
            if dist_to_goal < 2.5:
                v_max = 0.4
            else:
                v_max = self.V_MAX

            vx = np.clip(action[0] * v_max, -v_max, v_max)
            vy = np.clip(action[1] * v_max, -v_max, v_max)

            new_x = self.drone_positions[drone_id, 0] + vx * self.DT
            new_y = self.drone_positions[drone_id, 1] + vy * self.DT

            self.drone_positions[drone_id] = [new_x, new_y]
            self.drone_velocities[drone_id] = [vx, vy]

        rewards = {drone_id: -0.02 for drone_id in self.active_drones.copy()}
        dones = {}
        truncated = {}
        infos = {}

        drones_to_remove = set()

        # Drone-obstacle collision, wall collision, and goal reaching
        for drone_id in list(self.active_drones):
            collision = False

            # Wall collision detection
            drone_x = self.drone_positions[drone_id, 0]
            drone_y = self.drone_positions[drone_id, 1]
            if (drone_x < self.DRONE_RADIUS or drone_x > self.FIELD_W - self.DRONE_RADIUS or
                drone_y < self.DRONE_RADIUS or drone_y > self.FIELD_H - self.DRONE_RADIUS):
                # Capture terminal obs BEFORE moving drone off-map
                terminal_obs = self._get_obs(drone_id)
                rewards[drone_id] = -15.0
                dones[drone_id] = True
                infos[drone_id] = {"cause": "wall_collision", "terminal_observation": terminal_obs}
                drones_to_remove.add(drone_id)
                self.drone_positions[drone_id] = [-100.0, -100.0]
                collision = True

            # Obstacle collision detection
            if not collision:
                for (ox, oy), radius in self.obstacles:
                    dist = np.linalg.norm(self.drone_positions[drone_id] - np.array([ox, oy]))
                    if dist < radius + self.DRONE_RADIUS:
                        # Capture terminal obs BEFORE moving drone off-map
                        terminal_obs = self._get_obs(drone_id)
                        rewards[drone_id] = -15.0
                        dones[drone_id] = True
                        infos[drone_id] = {"cause": "obstacle_collision", "terminal_observation": terminal_obs}
                        drones_to_remove.add(drone_id)
                        self.drone_positions[drone_id] = [-100.0, -100.0]
                        collision = True
                        break

            if not collision:
                dist_to_goal = np.linalg.norm(self.goal - self.drone_positions[drone_id])
                if dist_to_goal < self.GOAL_REACH_THRESHOLD:
                    # Capture terminal obs BEFORE moving drone off-map
                    terminal_obs = self._get_obs(drone_id)
                    rewards[drone_id] = 50.0
                    dones[drone_id] = True
                    infos[drone_id] = {"cause": "success", "terminal_observation": terminal_obs}
                    drones_to_remove.add(drone_id)
                    self.drone_positions[drone_id] = [-100.0, -100.0]

        # Drone-drone collisions
        active_list = list(self.active_drones - drones_to_remove)
        for i in range(len(active_list)):
            for j in range(i + 1, len(active_list)):
                drone_i = active_list[i]
                drone_j = active_list[j]

                dist = np.linalg.norm(self.drone_positions[drone_i] -
                                     self.drone_positions[drone_j])
                if dist < self.DRONE_DRONE_COLLISION_DIST:
                    # Capture terminal obs BEFORE moving drones off-map
                    terminal_obs_i = self._get_obs(drone_i)
                    terminal_obs_j = self._get_obs(drone_j)
                    rewards[drone_i] = -10.0
                    rewards[drone_j] = -10.0
                    dones[drone_i] = True
                    dones[drone_j] = True
                    infos[drone_i] = {"cause": "drone_collision", "terminal_observation": terminal_obs_i}
                    infos[drone_j] = {"cause": "drone_collision", "terminal_observation": terminal_obs_j}
                    drones_to_remove.add(drone_i)
                    drones_to_remove.add(drone_j)
                    self.drone_positions[drone_i] = [-100.0, -100.0]
                    self.drone_positions[drone_j] = [-100.0, -100.0]

        # Potential-field progress reward (pure potential, normalized)
        # + Near-miss penalty + School-zone speed limit (ported from Phase A)
        PROGRESS_SCALE = 5.0       # compensates for slower V_MAX (1.2 vs Phase A's 2.0)
        NEAR_MISS_DIST = 0.5       # warning zone before collision (0.3m)
        NEAR_MISS_PENALTY = 10.0   # penalty scale for near-misses
        SCHOOL_ZONE_DIST = 0.6     # cluster detection radius
        SCHOOL_ZONE_SPEED = 0.35   # 35% of V_MAX when clustered

        surviving = self.active_drones - drones_to_remove
        for drone_id in list(surviving):
            pos = self.drone_positions[drone_id]
            if drone_id in dist_before:
                old_d = dist_before[drone_id]
                new_d = self.get_shortest_path_distance(pos)
                # Pure potential: r = scale × (old_dist − new_dist) / max_distance
                # Normalized to prevent loiter-reward drift. Stationary drone gets 0 reward (minus step penalty).
                rewards[drone_id] += PROGRESS_SCALE * (old_d - new_d) / self.MAX_DISTANCE

            # --- Cohesion Reward (R_group) ---
            # Small continuous bonus for staying within communication/cohesion range (0.6m to 4.0m)
            neighbors_in_range = 0
            for neighbor_id in surviving:
                if neighbor_id == drone_id:
                    continue
                dist_to_neighbor = np.linalg.norm(pos - self.drone_positions[neighbor_id])
                if 0.6 < dist_to_neighbor < 4.0:
                    neighbors_in_range += 1
            rewards[drone_id] += neighbors_in_range * 0.01

            # --- COM Expansion Reward & School-Zone Speed Limit ---
            close_neighbors = []
            for neighbor_id in surviving:
                if neighbor_id == drone_id:
                    continue
                dist_now = np.linalg.norm(pos - self.drone_positions[neighbor_id])
                dist_before_step = np.linalg.norm(old_positions[drone_id] - old_positions[neighbor_id])
                if dist_now < 0.55 or dist_before_step < 0.55:
                    close_neighbors.append(neighbor_id)

            if len(close_neighbors) > 0:
                # Unified Center of Mass Expansion
                com_positions = [self.drone_positions[nid] for nid in close_neighbors]
                local_com = np.mean(com_positions, axis=0)
                
                dist_to_com_now = np.linalg.norm(pos - local_com)
                dist_to_com_before = np.linalg.norm(old_positions[drone_id] - local_com)
                
                # Reward expanding away from the center of mass of the cluster
                delta_com = dist_to_com_now - dist_to_com_before
                rewards[drone_id] += np.clip(delta_com * 30.0, -3.0, 3.0)

                # School-zone speed limit (penalize moving fast when clustered)
                speed = np.linalg.norm(self.drone_velocities[drone_id])
                safe_speed = self.V_MAX * SCHOOL_ZONE_SPEED
                if speed > safe_speed:
                    speed_penalty = ((speed - safe_speed) / self.V_MAX) ** 2
                    rewards[drone_id] -= speed_penalty * len(close_neighbors) * 2.0

            # --- Near-miss penalty (social distancing) ---
            # Penalize being close to another drone BEFORE collision happens
            for neighbor_id in surviving:
                if neighbor_id == drone_id:
                    continue
                sep_dist = np.linalg.norm(pos - self.drone_positions[neighbor_id])
                if sep_dist < NEAR_MISS_DIST:
                    rewards[drone_id] -= NEAR_MISS_PENALTY * (NEAR_MISS_DIST - sep_dist)

            # Dense separation reward (only active when obstacles present)
            if self.target_density > 0.0:
                for neighbor_id in surviving:
                    if neighbor_id == drone_id:
                        continue
                    sep_dist = np.linalg.norm(pos - self.drone_positions[neighbor_id])
                    if sep_dist < 0.6:
                        rewards[drone_id] -= 0.05 * ((0.6 - sep_dist) ** 2)

        self.active_drones -= drones_to_remove

        # Truncation at max steps
        for drone_id in list(self.active_drones):
            if self.step_count >= self.MAX_STEPS:
                truncated[drone_id] = True
                infos[drone_id] = {"cause": "timeout"}
            else:
                truncated[drone_id] = False

            if drone_id not in dones:
                dones[drone_id] = False

        obs = {drone_id: self._get_obs(drone_id) for drone_id in self.active_drones}

        return obs, rewards, dones, truncated, infos

    def reset(self, seed=None, density=None):
        """Reset environment and generate new map."""
        if seed is not None:
            self.rng = np.random.RandomState(seed)

        if density is not None:
            self.target_density = density

        self.step_count = 0
        self.active_drones = set(range(self.N_DRONES))
        self._lidar_cache.clear()

        self._generate_map()

        obs = {drone_id: self._get_obs(drone_id) for drone_id in range(self.N_DRONES)}
        infos = {}

        return obs, infos

    def render(self):
        """Render environment using matplotlib."""
        plt.clf()

        # Field boundary
        plt.plot([0.0, self.FIELD_W, self.FIELD_W, 0.0, 0.0],
                 [0.0, 0.0, self.FIELD_H, self.FIELD_H, 0.0], 'k-', linewidth=2)

        # Obstacles
        for (ox, oy), radius in self.obstacles:
            circle = plt.Circle((ox, oy), radius, color='grey', alpha=0.5)
            plt.gca().add_patch(circle)

        # Goal
        goal_circle = plt.Circle(tuple(self.goal), self.GOAL_REACH_THRESHOLD,
                                 color='green', alpha=0.7)
        plt.gca().add_patch(goal_circle)

        # Active drones
        for drone_id in self.active_drones:
            pos = self.drone_positions[drone_id]
            drone_circle = plt.Circle(tuple(pos), self.DRONE_RADIUS,
                                     color='blue', alpha=0.8)
            plt.gca().add_patch(drone_circle)
            plt.text(pos[0], pos[1], str(drone_id), fontsize=8, ha='center')

        # LiDAR rays for drone 0
        if 0 in self.active_drones:
            lidar = self._get_lidar(0)
            drone_pos = self.drone_positions[0]

            for ray_idx in range(self.LIDAR_RAYS):
                angle = 2 * np.pi * ray_idx / self.LIDAR_RAYS
                end_dist = lidar[ray_idx] * self.LIDAR_RANGE
                end_x = drone_pos[0] + end_dist * np.cos(angle)
                end_y = drone_pos[1] + end_dist * np.sin(angle)

                plt.plot([drone_pos[0], end_x], [drone_pos[1], end_y],
                        'r-', linewidth=0.5, alpha=0.3)

        plt.xlim(0, self.FIELD_W)
        plt.ylim(0, self.FIELD_H)
        plt.gca().set_aspect('equal')
        plt.pause(0.01)

    def sanity_check(self):
        """
        Run 5 episodes with random actions to verify environment.
        Drones spawn within SPAWN_WALL_CLEARANCE of walls, but can move throughout
        the full [0, FIELD_W] × [0, FIELD_H] arena during episodes. Wall collisions
        occur when drone center moves within DRONE_RADIUS of field boundary.
        """
        print("Running sanity check...")

        maps_generated = 0
        total_steps = 0
        successful_drones = 0

        for episode in range(5):
            obs, _ = self.reset()
            maps_generated += 1

            for step in range(self.MAX_STEPS):
                actions = {}
                for drone_id in self.active_drones:
                    actions[drone_id] = self.rng.uniform(-1, 1, 2)

                obs, rewards, dones, truncated, infos = self.step(actions)
                total_steps += 1

                for drone_id, o in obs.items():
                    assert o.shape == (151,), f"Obs shape {o.shape} != (151,)"

                for drone_id, info in infos.items():
                    if info.get("cause") == "success":
                        successful_drones += 1

                if len(self.active_drones) == 0:
                    break

        avg_steps = total_steps / maps_generated if maps_generated > 0 else 0
        success_rate = successful_drones / (maps_generated * self.N_DRONES)

        print(f"Maps generated: {maps_generated}")
        print(f"Average steps per episode: {avg_steps:.1f}")
        print(f"Success rate: {success_rate:.2%}")
        print("Sanity check passed!")
