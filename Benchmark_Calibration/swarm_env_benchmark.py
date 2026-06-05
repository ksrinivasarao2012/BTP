import numpy as np
import pygame
from pettingzoo import ParallelEnv
from gymnasium import spaces, Env as GymEnv
from collections import deque
import math
import sys
import random
from scipy.ndimage import distance_transform_edt, label

# ======================================================
#  PHASE B v21 SENSING ABLATION: 80-RAY LIDAR + MLP
#  Architecture: 414D Actor | 2440D Critic
#  Protocol: Strict V2X Sender-Broadcast with VFH Sub-Goals
#  Purpose: Isolate sensing bottleneck vs memory bottleneck
#  Base: v19 geometric density (FROZEN benchmark)
#  Changes from v19: 80-ray LiDAR, max_velocity=1.2
# ======================================================

class SwarmLidarEnv_v20_SensingAblation(ParallelEnv):
    metadata = {'render_modes': ['human'], "name": "swarm_lidar_v20_sensing_ablation"}

    def __init__(self, render_mode=None, target_density=0.15, width=20.0, height=20.0, d_min=8.0):
        super().__init__()
        self.n_drones = 10
        self.max_steps = 800
        self.WIDTH, self.HEIGHT = width, height
        self.d_min = d_min
        self.drone_radius = 0.15
        self.dt = 0.1
        self.max_velocity = 1.2
        self.min_corridor_width = 0.40
        self.rectangle_probability = 0.30
        self.total_rejected_maps = 0
        self.total_failed_density = 0
        self.total_failed_connectivity = 0
        
        # CURRICULUM RANGES (Initialized high, will be decayed by Trainer)
        self.current_r_sensor = 100.0 
        self.current_r_comm = 100.0

        self.possible_agents = [f"drone_{i}" for i in range(self.n_drones)]
        self.agent_name_mapping = dict(zip(self.possible_agents, list(range(self.n_drones))))
        
        # v21: 80-ray LiDAR = 240D (80 sectors x 3 values)
        # Actor: 7D self + 240D lidar + 144D neighbors + 23D context = 414D
        # Critic: 10 drones x (2 pos + 2 vel + 240 lidar) = 2440D
        # Padding: 10D
        # Total: 414 + 2440 + 10 = 2864D
        self.num_lidar_sectors = 80
        self.lidar_dim = self.num_lidar_sectors * 3  # 240D
        self.actor_dim = 414
        self.critic_dim = 2440
        self.obs_size = self.actor_dim + self.critic_dim + 10
        self.observation_spaces = {a: spaces.Box(low=-np.inf, high=np.inf, shape=(self.obs_size,), dtype=np.float32) for a in self.possible_agents}
        self.action_spaces = {a: spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32) for a in self.possible_agents}

        self.obstacles = [] # Will be populated by reset()
        self.target_density = target_density
        self.actual_density = 0.0
        self._lidar_cache = {}
        
    def _is_occluded(self, idx, target_idx):
        p1, p2 = self.positions[idx], self.positions[target_idx]
        d = p2 - p1; a = np.dot(d, d)
        if a < 1e-6: return False
        
        # 1. Check circular obstacles
        for ox, oy, orad in self.obstacles:
            center = np.array([ox, oy]); f = p1 - center
            b = 2 * np.dot(f, d); c = np.dot(f, f) - (orad + 0.1)**2
            disc = b**2 - 4*a*c
            if disc >= 0:
                disc = np.sqrt(disc)
                t1, t2 = (-b-disc)/(2*a), (-b+disc)/(2*a)
                if (0 <= t1 <= 1) or (0 <= t2 <= 1): return True
                
        # 2. Check rectangular obstacles (AABBs)
        if hasattr(self, 'rectangles') and self.rectangles:
            for xmin, ymin, xmax, ymax in self.rectangles:
                # Inflate by 0.1 for consistent boundary buffer
                rx_min, ry_min = xmin - 0.1, ymin - 0.1
                rx_max, ry_max = xmax + 0.1, ymax + 0.1
                
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                
                t_min, t_max = 0.0, 1.0
                
                # Check X-axis slab
                if abs(dx) < 1e-8:
                    if p1[0] < rx_min or p1[0] > rx_max:
                        continue
                else:
                    tx1 = (rx_min - p1[0]) / dx
                    tx2 = (rx_max - p1[0]) / dx
                    t_min = max(t_min, min(tx1, tx2))
                    t_max = min(t_max, max(tx1, tx2))
                    
                # Check Y-axis slab
                if abs(dy) < 1e-8:
                    if p1[1] < ry_min or p1[1] > ry_max:
                        continue
                else:
                    ty1 = (ry_min - p1[1]) / dy
                    ty2 = (ry_max - p1[1]) / dy
                    t_min = max(t_min, min(ty1, ty2))
                    t_max = min(t_max, max(ty1, ty2))
                    
                if t_min <= t_max:
                    return True
                    
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
        lidar_obs = self._ray_cast_v20(idx) # 240D
        
        to_goal, dist_goal = self._compute_navigation_vector(agent)
        # 1. Self State (7D)
        escape_flag = 1.0 if self.escape_timer[agent] > 0 else 0.0
        obs_self = np.concatenate([vel/2.0, to_goal, [dist_goal/28.0], [np.arctan2(vel[1], vel[0])/np.pi], [escape_flag]])
        
        # 2. LiDAR (240D) - [80 sectors x 3 values from ray_cast_v20]
        
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
        
        obs_actor = np.concatenate([obs_self, lidar_obs/8.0, np.concatenate(neighbor_slots), obs_context]).astype(np.float32)
        
        # 5. Global State (2440D)
        # 10 drones x 244D (Pos(2), Vel(2), LiDAR(240)) = 2440D
        per_drone_global = 2 + 2 + self.lidar_dim  # 244
        global_state = np.zeros(self.critic_dim, dtype=np.float32)
        for j in range(self.n_drones):
            if f"drone_{j}" in self.agents:
                g_lid = self._ray_cast_v20(j) / 8.0
                global_state[j*per_drone_global : (j+1)*per_drone_global] = np.concatenate([self.positions[j]/self.WIDTH, self.velocities[j]/2.0, g_lid])
        
        padding_10 = np.zeros(10) # Future is_occluded_by_traitor space
        
        return np.concatenate([obs_actor, global_state, padding_10])

    def _ray_cast_v20(self, idx):
        """80 sectors x 3 values (min_dist, dx, dy) = 240D.
        
        v20 upgrade: 4x angular resolution over v14.
        Each sector covers 4.5° (vs 22.5° in v14).
        This eliminates the spatial aliasing that caused
        blind-spot collisions in narrow geometric corridors.
        """
        if hasattr(self, '_lidar_cache') and ("v20", idx) in self._lidar_cache:
            return self._lidar_cache[("v20", idx)]

        num_sectors = self.num_lidar_sectors  # 80
        rays_per_sector = 4  # Fewer rays per sector since sectors are narrower
        max_range = 8.0
        pos = self.positions[idx]
        sector_width = (2 * np.pi) / num_sectors
        center_angles = np.arange(num_sectors) * sector_width
        offsets = np.linspace(-sector_width/2, sector_width/2, rays_per_sector, endpoint=False)
        angles = (center_angles[:, np.newaxis] + offsets).flatten()
        ray_dirs = np.stack([np.cos(angles), np.sin(angles)], axis=1) 
        total_rays = num_sectors * rays_per_sector
        min_dists = np.full(total_rays, max_range, dtype=np.float32)

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
            return np.full(total_rays, max_range, dtype=np.float32)

        if self.obstacles:
            obs_array = np.array(self.obstacles, dtype=np.float32)
            min_dists = np.minimum(min_dists, intersect_circles(obs_array[:, :2], obs_array[:, 2] + self.drone_radius))

        if hasattr(self, 'rectangles') and self.rectangles:
            rect_array = np.array(self.rectangles, dtype=np.float32)
            # Inflate AABBs by drone_radius to handle collision volumes mathematically
            mins = rect_array[:, :2] - self.drone_radius
            maxs = rect_array[:, 2:] + self.drone_radius
            
            inv_dirs = 1.0 / (ray_dirs[:, np.newaxis, :] + 1e-8)
            t0 = (mins[np.newaxis, :, :] - pos[np.newaxis, np.newaxis, :]) * inv_dirs
            t1 = (maxs[np.newaxis, :, :] - pos[np.newaxis, np.newaxis, :]) * inv_dirs
            
            tmin = np.minimum(t0, t1)
            tmax = np.maximum(t0, t1)
            
            tmin_overall = np.max(tmin, axis=2)
            tmax_overall = np.min(tmax, axis=2)
            
            hit_mask = (tmax_overall >= tmin_overall) & (tmax_overall > 0)
            t_hit = np.where(hit_mask, np.maximum(tmin_overall, 0), max_range)
            min_dists = np.minimum(min_dists, np.min(t_hit, axis=1))

        others = [j for j in range(self.n_drones) if j != idx and f"drone_{j}" in self.agents]
        if others: min_dists = np.minimum(min_dists, intersect_circles(self.positions[others], np.full(len(others), 2.0 * self.drone_radius)))

        sector_res = min_dists.reshape(num_sectors, rays_per_sector)
        final = np.zeros(self.lidar_dim, dtype=np.float32)  # 240D
        for s in range(num_sectors):
            m_d = np.min(sector_res[s])
            ang = center_angles[s]
            final[s*3 : (s*3)+3] = [m_d, m_d * np.cos(ang), m_d * np.sin(ang)]
        if not hasattr(self, '_lidar_cache'):
            self._lidar_cache = {}
        self._lidar_cache[("v20", idx)] = final
        return final

    def _ray_cast_v14(self, idx):
        """Legacy 16-sector raycast kept for escape logic VFH sector scoring."""
        if hasattr(self, '_lidar_cache') and ("v14", idx) in self._lidar_cache:
            return self._lidar_cache[("v14", idx)]

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

        if hasattr(self, 'rectangles') and self.rectangles:
            rect_array = np.array(self.rectangles, dtype=np.float32)
            mins = rect_array[:, :2] - self.drone_radius
            maxs = rect_array[:, 2:] + self.drone_radius
            
            inv_dirs = 1.0 / (ray_dirs[:, np.newaxis, :] + 1e-8)
            t0 = (mins[np.newaxis, :, :] - pos[np.newaxis, np.newaxis, :]) * inv_dirs
            t1 = (maxs[np.newaxis, :, :] - pos[np.newaxis, np.newaxis, :]) * inv_dirs
            
            tmin = np.minimum(t0, t1)
            tmax = np.maximum(t0, t1)
            
            tmin_overall = np.max(tmin, axis=2)
            tmax_overall = np.min(tmax, axis=2)
            
            hit_mask = (tmax_overall >= tmin_overall) & (tmax_overall > 0)
            t_hit = np.where(hit_mask, np.maximum(tmin_overall, 0), max_range)
            min_dists = np.minimum(min_dists, np.min(t_hit, axis=1))

        others = [j for j in range(self.n_drones) if j != idx and f"drone_{j}" in self.agents]
        if others: min_dists = np.minimum(min_dists, intersect_circles(self.positions[others], np.full(len(others), 2.0 * self.drone_radius)))

        sector_res = min_dists.reshape(num_sectors, rays_per_sector)
        final_48 = np.zeros(48, dtype=np.float32)
        for s in range(num_sectors):
            m_d = np.min(sector_res[s])
            ang = center_angles[s]
            final_48[s*3 : (s*3)+3] = [m_d, m_d * np.cos(ang), m_d * np.sin(ang)]
        if not hasattr(self, '_lidar_cache'):
            self._lidar_cache = {}
        self._lidar_cache[("v14", idx)] = final_48
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
        self._lidar_cache = {}
        old_pos = np.copy(self.positions)
        old_vel = np.copy(self.velocities)
        for agent, action in actions.items():
            idx = self.agent_name_mapping[agent]
            self.velocities[idx] += np.clip(action, -1.0, 1.0) * self.dt * 10.0
            sp = np.linalg.norm(self.velocities[idx])
            if sp > self.max_velocity: self.velocities[idx] = (self.velocities[idx]/sp) * self.max_velocity
            self.positions[idx] += self.velocities[idx] * self.dt
            self.positions[idx, 0] = np.clip(self.positions[idx, 0], 0.0, self.WIDTH)
            self.positions[idx, 1] = np.clip(self.positions[idx, 1], 0.0, self.HEIGHT)
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
            
            # Store target and actual density in info for tracking
            self.infos[agent]["target_density"] = self.target_density
            self.infos[agent]["actual_density"] = self.actual_density
            
        obs = {a: self._observe(a) for a in self.agents}
        for a in list(self.agents):
            if terms[a] or truncs[a]: self.positions[self.agent_name_mapping[a]] = np.array([-100.0, -100.0]); self.agents.remove(a)
        return obs, rewards, terms, truncs, self.infos

    def reset(self, seed=None, options=None):
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)
        self.agents = self.possible_agents[:]; self.steps = 0
        self.infos = {a: {} for a in self.agents}
        self.steps_stagnant = {a: 0 for a in self.agents}
        self.best_dist_to_goal = {a: 99.0 for a in self.agents}
        self.positions_t_minus_1 = None
        
        # --- Persistent Memory Clear ---
        self.goal_progress_history = {a: deque(maxlen=20) for a in self.agents}
        self.turn_history = {a: deque(maxlen=10) for a in self.agents}
        self.position_history = {a: deque(maxlen=10) for a in self.agents}
        
        # --- Internal Escape States ---
        self.escape_timer = {a: 0 for a in self.agents}
        self.escape_direction = {a: np.zeros(2) for a in self.agents}
        self.escape_seed = {a: 0 for a in self.agents}
        self.escape_confidence = {a: 0.5 for a in self.agents}
        self.escape_cooldown = {a: 0 for a in self.agents}
        self.steps_stagnant = {a: 0 for a in self.agents}
        
        # -----------------------------------------
        # Benchmark Map Generation Pipeline
        # -----------------------------------------
        
        self.map_gen_attempts = 0
        while True:
            self.map_gen_attempts += 1
            if self.map_gen_attempts > 50:
                raise RuntimeError("Map generation failed")
            # --- Drone Spawning ---
            while True:
                self.goal = np.array([np.random.uniform(3.0, self.WIDTH - 3.0), np.random.uniform(3.0, self.HEIGHT - 3.0)])
                if self._is_goal_valid(self.goal):
                    break
            spawn_mode = options.get("spawn_mode", "random") if options else "random"
            drone_clearance = 1.2 if spawn_mode == "clustered" else 1.65  # Minimum clearance buffer between drones and spawned obstacles
            
            if spawn_mode == "clustered":
                while True:
                    cx = np.random.uniform(2.0, self.WIDTH - 2.0)
                    cy = np.random.uniform(2.0, self.HEIGHT - 2.0)
                    if np.linalg.norm(np.array([cx, cy]) - self.goal) > self.d_min:
                        break
                        
            positions = []
            attempts = 0
            while len(positions) < self.n_drones:
                if spawn_mode == "clustered":
                    p = np.array([np.random.uniform(cx - 1.25, cx + 1.25), np.random.uniform(cy - 1.25, cy + 1.25)])
                    p[0] = np.clip(p[0], 1.0, self.WIDTH - 1.0)
                    p[1] = np.clip(p[1], 1.0, self.HEIGHT - 1.0)
                else:
                    p = np.array([np.random.uniform(1.0, self.WIDTH - 1.0), np.random.uniform(1.0, self.HEIGHT - 1.0)])
                    
                valid = True
                if np.linalg.norm(p - self.goal) < self.d_min:
                    valid = False
                
                # Drone diameter = 0.3 m, Spawn separation = 0.8 m
                if valid and any(np.linalg.norm(p - q) < 0.8 for q in positions):
                    valid = False
                    
                if valid:
                    positions.append(p)
                    attempts = 0
                else:
                    attempts += 1
                    if attempts > 1000:
                        positions = []
                        break
                                    
            if len(positions) < self.n_drones:
                continue

            self.positions = np.array(positions, dtype=np.float32)
            self.velocities = np.zeros((self.n_drones, 2))
            
            # --- Obstacle Generation ---
            gen_result = self._generate_obstacles(self.target_density, drone_clearance)
            if gen_result is None:
                self.total_rejected_maps += 1
                self.total_failed_density += 1
                continue
            self.obstacles, self.rectangles, self.actual_density, occupied_grid = gen_result
            
            # --- Connectivity Validation ---
            if self._is_map_solvable(occupied_grid):
                self.occupied_grid = occupied_grid
                break
            else:
                self.total_rejected_maps += 1
                self.total_failed_connectivity += 1
        
        self._prepare_broadcasts()
        self._lidar_cache = {}
        return {a: self._observe(a) for a in self.agents}, self.infos

    def _generate_obstacles(self, density, drone_clearance):
        target_area = self.WIDTH * self.HEIGHT * density
        obstacles = []
        rectangles = []

        raster_res = 0.1 # 10cm grid
        rw = int(self.WIDTH / raster_res)
        rh = int(self.HEIGHT / raster_res)
        occupied = np.zeros((rw, rh), dtype=bool)
        current_area = 0.0

        MAX_OBSTACLE_ATTEMPTS = 2000
        MIN_NEW_AREA = 0.05

        for _ in range(MAX_OBSTACLE_ATTEMPTS):
            if current_area >= target_area:
                break

            is_rect = random.random() < self.rectangle_probability
            
            if is_rect:
                if random.random() < 0.5:
                    w = random.uniform(4.0, 6.0)
                    h = random.uniform(0.4, 0.8)
                else:
                    w = random.uniform(0.4, 0.8)
                    h = random.uniform(4.0, 6.0)
                    
                cx = random.uniform(w / 2.0, self.WIDTH - w / 2.0)
                cy = random.uniform(h / 2.0, self.HEIGHT - h / 2.0)
                
                xmin, xmax = cx - w / 2.0, cx + w / 2.0
                ymin, ymax = cy - h / 2.0, cy + h / 2.0
                
                valid = True
                for rx1, ry1, rx2, ry2 in rectangles:
                    if not (
                        xmax + 0.5 < rx1 or
                        xmin - 0.5 > rx2 or
                        ymax + 0.5 < ry1 or
                        ymin - 0.5 > ry2
                    ):
                        valid = False
                        break
                        
                if not valid:
                    continue
                
                r_eff = np.sqrt((w/2)**2 + (h/2)**2)
                if np.linalg.norm(np.array([cx, cy]) - self.goal) <= r_eff + 1.0:
                    continue
                conflict = False
                for pos in self.positions:
                    dx = max(xmin - pos[0], 0, pos[0] - xmax)
                    dy = max(ymin - pos[1], 0, pos[1] - ymax)
                    if np.sqrt(dx*dx + dy*dy) <= drone_clearance:
                        conflict = True
                        break
                if conflict:
                    continue
                    
                ixmin = max(0, int(xmin / raster_res))
                ixmax = min(rw, int(xmax / raster_res) + 1)
                iymin = max(0, int(ymin / raster_res))
                iymax = min(rh, int(ymax / raster_res) + 1)
                
                newly_covered_cells = np.sum(~occupied[ixmin:ixmax, iymin:iymax])
                newly_covered_area = newly_covered_cells * (raster_res**2)
                
                if newly_covered_area < MIN_NEW_AREA:
                    continue
                    
                current_area += newly_covered_area
                occupied[ixmin:ixmax, iymin:iymax] = True
                rectangles.append((xmin, ymin, xmax, ymax))
                
            else:
                ch = random.random()
                if ch < 0.214:
                    # 21.4% large (15% total)
                    r = random.uniform(1.5, 2.5)
                elif ch < 0.714:
                    # 50.0% medium (35% total)
                    r = random.uniform(0.6, 1.4)
                else:
                    # 28.6% small (20% total)
                    r = random.uniform(0.2, 0.5)

                cx = random.uniform(r / 2.0, self.WIDTH - r / 2.0)
                cy = random.uniform(r / 2.0, self.HEIGHT - r / 2.0)
                    
                if np.linalg.norm(np.array([cx, cy]) - self.goal) <= r + 1.0:
                    continue
                    
                conflict = False
                for pos in self.positions:
                    if np.linalg.norm(np.array([cx, cy]) - pos) <= r + drone_clearance:
                        conflict = True
                        break
                if conflict:
                    continue

                xmin_grid = max(0, int((cx - r) / raster_res))
                xmax_grid = min(rw, int((cx + r) / raster_res) + 1)
                ymin_grid = max(0, int((cy - r) / raster_res))
                ymax_grid = min(rh, int((cy + r) / raster_res) + 1)

                lx = np.arange(xmin_grid, xmax_grid) * raster_res + raster_res / 2
                ly = np.arange(ymin_grid, ymax_grid) * raster_res + raster_res / 2
                LX, LY = np.meshgrid(lx, ly, indexing='ij')

                new_cells = (LX - cx)**2 + (LY - cy)**2 <= r**2
                newly_covered_cells = np.sum(new_cells & ~occupied[xmin_grid:xmax_grid, ymin_grid:ymax_grid])
                newly_covered_area = newly_covered_cells * (raster_res**2)
                
                if newly_covered_area < MIN_NEW_AREA:
                    continue

                current_area += newly_covered_area
                occupied[xmin_grid:xmax_grid, ymin_grid:ymax_grid] |= new_cells
                obstacles.append((cx, cy, r))

        if current_area < target_area:
            return None # Guaranteed density failed

        achieved_density = current_area / (self.WIDTH * self.HEIGHT)
        return obstacles, rectangles, achieved_density, occupied
        
    def _is_goal_valid(self, goal):
        if not (2.0 <= goal[0] <= self.WIDTH - 2.0 and 2.0 <= goal[1] <= self.HEIGHT - 2.0):
            return False
            
        # Note: During initial map generation, obstacles and rectangles are empty here.
        # This check is maintained for potential mid-episode goal resampling or diagnostic usage.
        for cx, cy, r in self.obstacles:
            if np.linalg.norm(goal - np.array([cx, cy])) <= r + 2.0:
                return False
                
        if hasattr(self, 'rectangles'):
            for rx1, ry1, rx2, ry2 in self.rectangles:
                if (rx1 - 2.0 <= goal[0] <= rx2 + 2.0) and (ry1 - 2.0 <= goal[1] <= ry2 + 2.0):
                    return False
        return True

    def _is_map_solvable(self, occupied, raster_res=0.1):
        dist_transform = distance_transform_edt(~occupied) * raster_res
        inflated_occupied = dist_transform < (self.min_corridor_width / 2.0)
        
        gx = min(int(self.goal[0]/raster_res), inflated_occupied.shape[0]-1)
        gy = min(int(self.goal[1]/raster_res), inflated_occupied.shape[1]-1)
        
        if inflated_occupied[gx, gy]: 
            return False 
            
        visited = np.zeros_like(inflated_occupied, dtype=bool)
        queue = deque([(gx, gy)])
        visited[gx, gy] = True
        
        moves = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        
        while queue:
            x, y = queue.popleft()
            for dx, dy in moves:
                nx, ny = x + dx, y + dy
                if 0 <= nx < inflated_occupied.shape[0] and 0 <= ny < inflated_occupied.shape[1]:
                    if not inflated_occupied[nx, ny] and not visited[nx, ny]:
                        # Corner-cut prevention for diagonal moves
                        if dx != 0 and dy != 0:
                            if 0 <= x + dx < inflated_occupied.shape[0] and 0 <= y + dy < inflated_occupied.shape[1]:
                                if inflated_occupied[x + dx, y] and inflated_occupied[x, y + dy]:
                                    continue
                        visited[nx, ny] = True
                        queue.append((nx, ny))
                        
        for pos in self.positions:
            px = min(int(pos[0]/raster_res), inflated_occupied.shape[0]-1)
            py = min(int(pos[1]/raster_res), inflated_occupied.shape[1]-1)
            if inflated_occupied[px, py] or not visited[px, py]:
                return False
                
        return True

        
    def set_curriculum(self, r_sensor, r_comm):
        self.current_r_sensor = r_sensor
        self.current_r_comm = r_comm
        
    def set_target_density(self, density):
        self.target_density = density
        
    def close(self): pass
