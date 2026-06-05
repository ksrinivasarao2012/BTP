import numpy as np
import pygame
from pettingzoo import ParallelEnv
from gymnasium import spaces, Env as GymEnv
from collections import deque
import math
import sys

# ======================================================
#  PHASE B MASTER v17: VECTOR FIELD HISTOGRAM (VFH) HYBRID
#  Architecture: 222D Actor | 530D Critic
#  Protocol: Strict V2X Sender-Broadcast with VFH Sub-Goals
#  Target: IEEE-Compliant Decentralized Avoidance (No Dijkstra)
# ======================================================

class SwarmLidarEnv_v17_Master(ParallelEnv):
    metadata = {'render_modes': ['human'], "name": "swarm_lidar_v17_master"}

    def __init__(self, render_mode=None, target_density=0.25):
        super().__init__()
        self.n_drones = 10
        self.max_steps = 800
        self.WIDTH, self.HEIGHT = 20.0, 20.0
        self.drone_radius = 0.15
        self.dt = 0.1
        self.max_velocity = 2.0
        
        # CURRICULUM RANGES (Initialized high, will be decayed by Trainer)
        self.current_r_sensor = 100.0 
        self.current_r_comm = 100.0

        self.possible_agents = [f"drone_{i}" for i in range(self.n_drones)]
        self.agent_name_mapping = dict(zip(self.possible_agents, list(range(self.n_drones))))
        
        # 222-Dim Actor | 530-Dim Critic Total Features
        self.obs_size = 222 + 530
        self.observation_spaces = {a: spaces.Box(low=-np.inf, high=np.inf, shape=(self.obs_size,), dtype=np.float32) for a in self.possible_agents}
        self.action_spaces = {a: spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32) for a in self.possible_agents}

        self.obstacles = [] # Will be populated by reset()
        self.target_density = target_density
        
    def _is_occluded(self, idx, target_idx):
        p1, p2 = self.positions[idx], self.positions[target_idx]
        d = p2 - p1; a = np.dot(d, d)
        if a < 1e-6: return False
        for ox, oy, orad in self.obstacles:
            center = np.array([ox, oy]); f = p1 - center
            b = 2 * np.dot(f, d); c = np.dot(f, f) - (orad + 0.1)**2
            disc = b**2 - 4*a*c
            if disc >= 0:
                disc = np.sqrt(disc)
                t1, t2 = (-b-disc)/(2*a), (-b+disc)/(2*a)
                if (0 <= t1 <= 1) or (0 <= t2 <= 1): return True
        return False

    def _prepare_broadcasts(self):
        """Phase B: Explicitly honest broadcasts."""
        self.broadcasts = {
            i: {
                'pos': self.positions[i].copy(),
                'vel': self.velocities[i].copy()
            } for i in range(self.n_drones)
        }

    def _observe(self, agent):
        idx = self.agent_name_mapping[agent]
        pos, vel = self.positions[idx], self.velocities[idx]
        lidar_16 = self._ray_cast_v14(idx) # 48D
        
        to_goal, dist_goal = self._compute_navigation_vector(agent)
        # 1. Self State (7D)
        escape_flag = 1.0 if self.escape_timer[agent] > 0 else 0.0
        obs_self = np.concatenate([vel/2.0, to_goal, [dist_goal/28.0], [np.arctan2(vel[1], vel[0])/np.pi], [escape_flag]])
        
        # 2. LiDAR (48D) - [Already 48D from ray_cast_v14]
        
        # 3. Neighbor Slots (144D): 9 x 16D
        neighbor_slots = []
        pos_discrepancies = []
        unverifiable_count = 0
        active_comm_count = 0
        
        for j in range(self.n_drones):
            if j == idx: continue
            slot = np.zeros(16, dtype=np.float32)
            if f"drone_{j}" in self.agents:
                d_j = np.linalg.norm(pos - self.positions[j])
                is_comm = 1.0 if d_j <= self.current_r_comm else 0.0
                is_visible = 1.0 if (d_j <= self.current_r_sensor and not self._is_occluded(idx, j)) else 0.0
                
                s_pos = np.zeros(2); s_vel = np.zeros(2)
                c_pos = np.zeros(2); c_vel = np.zeros(2); speed = 0.0; heading = 0.0
                stag = 0.0
                
                if is_visible:
                    s_pos = (self.positions[j] - pos) / self.WIDTH
                    s_vel = (self.velocities[j] - vel) / 4.0
                
                if is_comm:
                    active_comm_count += 1
                    msg = self.broadcasts[j]
                    c_pos = (msg['pos'] - pos) / self.WIDTH
                    c_vel = (msg['vel'] - vel) / 4.0
                    speed = np.linalg.norm(msg['vel']) / self.max_velocity
                    heading = np.arctan2(msg['vel'][1], msg['vel'][0]) / np.pi
                    if not is_visible: unverifiable_count += 1
                
                # Math: Discrepancy
                pos_disc = 0.0; vel_disc = 0.0
                if is_visible and is_comm:
                    pos_disc = np.linalg.norm(s_pos - c_pos)
                    vel_disc = np.linalg.norm(s_vel - c_vel)
                    pos_discrepancies.append(pos_disc)
                
                # Trust Availability
                t_avail = 0.0
                if is_visible and is_comm: t_avail = 1.0
                elif is_visible: t_avail = 0.5
                
                slot[0:2] = s_pos; slot[2:4] = s_vel; slot[4] = is_visible
                slot[5:7] = c_pos; slot[7:9] = c_vel; slot[9] = speed; slot[10] = heading; slot[11] = is_comm
                slot[12] = pos_disc; slot[13] = vel_disc; slot[14] = t_avail; slot[15] = 1.0 # is_active
            neighbor_slots.append(slot)
            
        # 4. Context (13D)
        vicinity = sum(1 for j in range(self.n_drones) if j!=idx and f"drone_{j}" in self.agents and np.linalg.norm(pos-self.positions[j]) < 1.0)
        congestion = vicinity / 10.0
        
        self.position_history[agent].append(pos.copy()); hist = list(self.position_history[agent])
        while len(hist) < 10: hist.insert(0, pos.copy())
        rel_hist = np.concatenate([(h - pos) / self.WIDTH for h in hist])
        
        mean_pos_disc = np.mean(pos_discrepancies) if pos_discrepancies else 0.0
        frac_unverifiable = unverifiable_count / (active_comm_count + 1e-5)
        
        obs_context = np.concatenate([rel_hist, [congestion], [mean_pos_disc], [frac_unverifiable]])
        
        obs_222 = np.concatenate([obs_self, lidar_16/8.0, np.concatenate(neighbor_slots), obs_context]).astype(np.float32)
        
        # 5. Global State (530D)
        # 10 drones x 52D (Pos(2), Vel(2), LiDAR(48)) = 520D
        global_state_520 = np.zeros(520, dtype=np.float32)
        for j in range(self.n_drones):
            if f"drone_{j}" in self.agents:
                g_lid = self._ray_cast_v14(j) / 8.0
                global_state_520[j*52 : (j+1)*52] = np.concatenate([self.positions[j]/self.WIDTH, self.velocities[j]/2.0, g_lid])
        
        padding_10 = np.zeros(10) # Future is_occluded_by_traitor space
        
        return np.concatenate([obs_222, global_state_520, padding_10])

    def _ray_cast_v14(self, idx):
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

        if self.obstacles:
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

    def _update_escape_state(self, agent, old_pos, old_vel, new_pos, new_vel, goal_progress, dist_goal):
        idx = self.agent_name_mapping[agent]
        self.goal_progress_history[agent].append(goal_progress)
        
        speed = np.linalg.norm(new_vel)
        if speed < 0.1:
            turn_sign = 0
        else:
            turn_sign = np.sign(new_vel[0]*old_vel[1] - new_vel[1]*old_vel[0])
        self.turn_history[agent].append(turn_sign)
        
        mean_progress = np.mean(self.goal_progress_history[agent]) if len(self.goal_progress_history[agent]) > 0 else 1.0
        
        hist = self.turn_history[agent]
        oscillation_score = sum(1 for i in range(1, len(hist)) if hist[i] != hist[i-1])
        
        neighbors = sum(1 for j in range(self.n_drones) if j!=idx and f"drone_{j}" in self.agents and np.linalg.norm(new_pos-self.positions[j]) < 1.5)
        
        progress_ratio = mean_progress / (dist_goal + 1e-6)
        poor_progress = progress_ratio < 0.005
        if dist_goal < 2.0:
            poor_progress = False
        oscillation = oscillation_score > 6
        congestion = neighbors >= 3
        
        # Compute Dynamic Blending Confidence (C)
        p_norm = min(1.0, max(0.0, mean_progress / 0.05))
        o_norm = max(0.0, 1.0 - (oscillation_score / 10.0))
        c_norm = max(0.0, 1.0 - (neighbors / 5.0))
        if self.escape_timer[agent] > 0:
            x = 3 * (p_norm - 0.5) + 2 * (o_norm - 0.5) + 2 * (c_norm - 0.5)
            new_C = 1.0 / (1.0 + np.exp(-x))
            self.escape_confidence[agent] = 0.8 * self.escape_confidence[agent] + 0.2 * new_C
        else:
            self.escape_confidence[agent] = 0.5
        
        # Early Exit Logic
        if self.escape_timer[agent] > 0 and neighbors < 2 and mean_progress > 0.05:
            self.escape_timer[agent] = 0
            self.escape_cooldown[agent] = 50

        # Trigger Activation
        if poor_progress and oscillation and congestion and self.escape_timer[agent] == 0 and self.escape_cooldown[agent] == 0:
            self.escape_timer[agent] = min(120, max(30, 3 * neighbors + self.steps_stagnant[agent]))
            self.escape_seed[agent] = np.random.randint(0, 10000)
        
        # Compute Direction if triggered or every N steps during escape
        update_interval = max(2, neighbors)
        if self.escape_timer[agent] > 0 and (self.escape_timer[agent] % update_interval == 0 or np.linalg.norm(self.escape_direction[agent]) < 0.1):
            lidar = self._ray_cast_v14(idx)
            min_dists = lidar[0::3]
            sector_width = (2 * np.pi) / 16
            
            goal_vec = self.goal - new_pos
            goal_vec = goal_vec / (np.linalg.norm(goal_vec) + 1e-6)
            
            sector_scores = []
            
            # Precompute neighbor flow to avoid redundant inner loops
            flow = np.zeros(2)
            total_weight = 0.0
            for j in range(self.n_drones):
                if j!=idx and f"drone_{j}" in self.agents:
                    dist_j = np.linalg.norm(self.positions[j] - new_pos)
                    if dist_j < 3.0:
                        vj = self.velocities[j]
                        speed = np.linalg.norm(vj)
                        if speed < 0.2:
                            continue
                        n_prog_hist = self.goal_progress_history[f"drone_{j}"]
                        n_mean_prog = np.mean(n_prog_hist) if len(n_prog_hist) > 0 else 0.0
                        progress = max(n_mean_prog, 0.0)
                        weight = max(0.1, speed * progress)
                        flow += weight * vj
                        total_weight += weight
            neighbor_flow = flow / (total_weight + 1e-6)

            for s in range(16):
                distance = min_dists[s]
                sector_width_score = sum(min_dists[(s+i)%16] for i in range(-2, 3))
                angle = s * sector_width
                sv = np.array([np.cos(angle), np.sin(angle)])
                forward_bias = max(0, np.dot(sv, goal_vec))
                flow_match = np.dot(sv, neighbor_flow)
                
                # Neighbor density in sector
                n_dens = 0
                for j in range(self.n_drones):
                    if j!=idx and f"drone_{j}" in self.agents:
                        vj = self.positions[j] - new_pos
                        dist_j = np.linalg.norm(vj)
                        if dist_j < 3.0:
                            ang_j = np.arctan2(vj[1], vj[0])
                            if ang_j < 0: ang_j += 2*np.pi
                            s_j = int((ang_j + sector_width/2) % (2*np.pi) // sector_width)
                            if s_j == s: n_dens += 1
                
                agent_bias = 0.05 * np.sin(self.escape_seed[agent] * angle)
                score = 0.40 * distance + 0.15 * sector_width_score + 0.20 * forward_bias - 0.20 * n_dens + 0.20 * flow_match + 0.05 * agent_bias
                sector_scores.append(score)
            
            best_s = np.argmax(sector_scores)
            best_ang = best_s * sector_width
            self.escape_direction[agent] = np.array([np.cos(best_ang), np.sin(best_ang)])

    def _compute_navigation_vector(self, agent):
        idx = self.agent_name_mapping[agent]
        pos = self.positions[idx]
        original_goal_vec = self.goal - pos
        dist_goal = np.linalg.norm(original_goal_vec)
        original_goal_vec = original_goal_vec / (dist_goal + 1e-6)
        
        if self.escape_timer[agent] > 0:
            C = self.escape_confidence[agent]
            to_goal = C * original_goal_vec + (1.0 - C) * self.escape_direction[agent]
            to_goal /= (np.linalg.norm(to_goal) + 1e-6)
        else:
            to_goal = original_goal_vec
            
        return to_goal, dist_goal

    def step(self, actions):
        if not self.agents: return {}, {}, {}, {}, {}
        old_pos = np.copy(self.positions)
        old_vel = np.copy(self.velocities)
        for agent, action in actions.items():
            idx = self.agent_name_mapping[agent]
            self.velocities[idx] += np.clip(action, -1.0, 1.0) * self.dt * 10.0
            sp = np.linalg.norm(self.velocities[idx])
            if sp > self.max_velocity: self.velocities[idx] = (self.velocities[idx]/sp) * self.max_velocity
            self.positions[idx] += self.velocities[idx] * self.dt
            self.positions[idx] = np.clip(self.positions[idx], 0.0, self.WIDTH)
        self.steps += 1; rewards, terms, truncs = {}, {}, {}
        self._prepare_broadcasts()
        
        # Evaluate states and compute rewards
        for agent in self.agents:
            idx = self.agent_name_mapping[agent]; pos = self.positions[idx]; dist_g = np.linalg.norm(self.goal-pos)
            goal_progress = np.linalg.norm(self.goal - old_pos[idx]) - dist_g
            
            # Decrement timers cleanly here (isolated from _observe)
            if self.escape_timer[agent] > 0:
                self.escape_timer[agent] -= 1
                if self.escape_timer[agent] <= 0:
                    self.escape_cooldown[agent] = 50
            elif self.escape_cooldown[agent] > 0:
                self.escape_cooldown[agent] -= 1
            
            # Update stateful escape mechanism BEFORE computing rewards or observations
            self._update_escape_state(agent, old_pos[idx], old_vel[idx], pos, self.velocities[idx], goal_progress, dist_g)
            
            if dist_g < self.best_dist_to_goal[agent] - 0.1: self.best_dist_to_goal[agent] = dist_g; self.steps_stagnant[agent] = 0
            else: self.steps_stagnant[agent] += 1
            
            # --- Anti-Exploit Rewards Strategy (Decoupled Phase E) ---
            progress_reward = 30.0 * goal_progress
            escape_reward = 0.0
            
            if self.escape_timer[agent] > 0:
                old_neighbors = sum(1 for j in range(self.n_drones) if j!=idx and f"drone_{j}" in self.agents and np.linalg.norm(old_pos[idx]-old_pos[j]) < 1.5)
                new_neighbors = sum(1 for j in range(self.n_drones) if j!=idx and f"drone_{j}" in self.agents and np.linalg.norm(pos-self.positions[j]) < 1.5)
                density_change = old_neighbors - new_neighbors
                escape_reward = 0.5 * density_change + 0.2 * max(goal_progress, 0.0)

            rew = progress_reward + escape_reward
            
            for j in range(self.n_drones):
                if j == idx or f"drone_{j}" not in self.agents: continue
                d_j = np.linalg.norm(self.positions[j] - pos)
                if d_j < 1.0 and self.steps_stagnant[f"drone_{j}"] > 30: rew -= 50.0 / (1.0+math.exp(10*(d_j-0.5)))
            
            hit = any(np.linalg.norm(pos - np.array([ox, oy])) < (0.15+orad) for ox, oy, orad in self.obstacles)
            hit = hit or (min(pos[0], self.WIDTH-pos[0], pos[1], self.HEIGHT-pos[1]) < 0.05) or any(np.linalg.norm(pos-self.positions[j]) < 0.3 for j in range(self.n_drones) if j!=idx and f"drone_{j}" in self.agents)
            
            if hit: rew -= 500.0; terms[agent] = True; self.infos[agent]["cause"] = "collision"
            elif dist_g < 0.75: rew += 500.0; terms[agent] = True; self.infos[agent]["cause"] = "success"
            else: terms[agent] = False
            rewards[agent] = rew
            truncs[agent] = self.steps >= self.max_steps
            if truncs[agent]: self.infos[agent]["cause"] = "timeout"
            
        obs = {a: self._observe(a) for a in self.agents}
        for a in list(self.agents):
            if terms[a] or truncs[a]: self.positions[self.agent_name_mapping[a]] = np.array([-100.0, -100.0]); self.agents.remove(a)
        return obs, rewards, terms, truncs, self.infos

    def reset(self, seed=None, options=None):
        self.agents = self.possible_agents[:]; self.steps = 0
        self.infos = {a: {} for a in self.agents}
        self.steps_stagnant = {a: 0 for a in self.agents}; self.best_dist_to_goal = {a: 99.0 for a in self.agents}
        self.position_history = {a: deque(maxlen=10) for a in self.agents}
        
        # --- Advanced Stateful Escape Tracking ---
        self.escape_timer = {a: 0 for a in self.agents}
        self.escape_cooldown = {a: 0 for a in self.agents}
        self.escape_direction = {a: np.zeros(2, dtype=np.float32) for a in self.agents}
        self.escape_confidence = {a: 0.5 for a in self.agents}
        self.escape_seed = {a: 0 for a in self.agents}
        self.goal_progress_history = {a: deque(maxlen=20) for a in self.agents}
        self.turn_history = {a: deque(maxlen=10) for a in self.agents}
        # -----------------------------------------
        
        self.goal = np.array([17.0, 17.0])
        spawn_mode = options.get("spawn_mode", "random") if options else "random"
        
        if spawn_mode == "clustered":
            while True:
                cx, cy = np.random.uniform(2.0, 18.0, 2)
                if np.linalg.norm(np.array([cx, cy]) - self.goal) > 8.0:
                    break
                    
        positions = []
        attempts = 0
        while len(positions) < self.n_drones:
            if spawn_mode == "clustered":
                p = np.array([np.random.uniform(cx - 1.25, cx + 1.25), np.random.uniform(cy - 1.25, cy + 1.25)])
                p = np.clip(p, 1.0, 19.0)
            else:
                p = np.random.uniform(1.0, 19.0, 2)
                
            valid = True
            if np.linalg.norm(p - self.goal) < 8.0:
                valid = False
            if valid and any(np.linalg.norm(p - q) < 0.8 for q in positions):
                valid = False
                
            if valid:
                positions.append(p)
                attempts = 0
            else:
                attempts += 1
                if attempts > 1000:
                    positions = []
                    attempts = 0
                    if spawn_mode == "clustered":
                        while True:
                            cx, cy = np.random.uniform(2.0, 18.0, 2)
                            if np.linalg.norm(np.array([cx, cy]) - self.goal) > 8.0:
                                break
                                
        self.positions = np.array(positions, dtype=np.float32)
        self.velocities = np.zeros((self.n_drones, 2))
        self.obstacles = self._generate_obstacles(self.target_density)
        self._prepare_broadcasts()
        return {a: self._observe(a) for a in self.agents}, self.infos

    def _generate_obstacles(self, density):
        obs = []
        n = int(density * 20); 
        for _ in range(n): obs.append((np.random.uniform(5, 15), np.random.uniform(5, 15), np.random.uniform(0.5, 1.5)))
        return obs
        
    def set_curriculum(self, r_sensor, r_comm):
        self.current_r_sensor = r_sensor
        self.current_r_comm = r_comm
        
    def set_target_density(self, density):
        self.target_density = density
        
    def close(self): pass
