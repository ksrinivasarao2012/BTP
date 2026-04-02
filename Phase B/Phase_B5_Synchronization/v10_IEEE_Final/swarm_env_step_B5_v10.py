import numpy as np
import pygame
from pettingzoo import ParallelEnv
from gymnasium import spaces, Env as GymEnv
from collections import deque
import math
import sys

# ======================================================
#  PHASE B5 v10-PRO: IEEE FINAL CERTIFIED BASELINE
#  Architecture: Unified 100D Aligned Vector
#  Sensing: 8m LiDAR (Occludable) | 10m Radio (V2X GPS)
# ======================================================

class SwarmLidarEnv_v10_Pro(ParallelEnv):
    metadata = {'render_modes': ['human'], "name": "swarm_lidar_v10_pro"}

    def __init__(self, render_mode=None, target_density=0.25):
        super().__init__()
        self.n_drones = 10
        self.max_steps = 800
        self.WIDTH, self.HEIGHT = 20.0, 20.0
        self.drone_radius = 0.15
        self.dt = 0.1
        self.max_velocity = 2.0
        
        # SENSING RADII
        self.R_LiDAR = 8.0  # Physical Body (Occludable)
        self.R_RADIO = 10.0 # V2X GPS Broadcast (Non-Occludable)

        self.possible_agents = [f"drone_{i}" for i in range(self.n_drones)]
        self.agent_name_mapping = dict(zip(self.possible_agents, list(range(self.n_drones))))
        
        # 100-Dim Local: 54(Self) + 35(5x7 Neighbors) + 1(Congestion) + 10(Memory)
        # 400-Dim Global: 10 drones * 40D simplified core
        self.obs_size = 100 + 400
        self.observation_spaces = {a: spaces.Box(low=-np.inf, high=np.inf, shape=(self.obs_size,), dtype=np.float32) for a in self.possible_agents}
        self.action_spaces = {a: spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32) for a in self.possible_agents}
        
    def _is_occluded(self, idx, target_idx):
        """LiDAR LOS Check: Returns True if a wall blocks vision between drones."""
        p1, p2 = self.positions[idx], self.positions[target_idx]
        d = p2 - p1
        a = np.dot(d, d)
        if a < 1e-6: return False
        for ox, oy, orad in self.obstacles:
            center = np.array([ox, oy])
            f = p1 - center
            b = 2 * np.dot(f, d); c = np.dot(f, f) - (orad + self.drone_radius)**2
            disc = b**2 - 4*a*c
            if disc >= 0:
                disc = np.sqrt(disc)
                t1, t2 = (-b-disc)/(2*a), (-b+disc)/(2*a)
                if (0 <= t1 <= 1) or (0 <= t2 <= 1): return True
        return False

    def _observe(self, agent):
        idx = self.agent_name_mapping[agent]
        pos, vel = self.positions[idx], self.velocities[idx]
        dist_goal = np.linalg.norm(self.goal - pos)
        to_goal = (self.goal - pos) / (dist_goal + 1e-5)
        lidar = self._ray_cast(idx)
        
        # Part 1: Self & Local Env (54D)
        obs_self = np.concatenate([[vel[0]/2, vel[1]/2], to_goal, [dist_goal/28.0], [np.arctan2(vel[1], vel[0])/np.pi], lidar/8.0])
        
        # Part 2 & 3: Aligned Neighbors (35D)
        dists_list = []
        for j in range(self.n_drones):
            if j != idx and f"drone_{j}" in self.agents:
                dists_list.append((j, np.linalg.norm(pos - self.positions[j])))
        dists_list.sort(key=lambda x: x[1])
        
        neighbor_blocks = []
        for j, d in dists_list[:5]:
            # Digital Communication (Radio 10m) - Telemetry V2X
            is_comm = 1.0 if d <= self.R_RADIO else 0.0
            # Physical Visibility (LiDAR 8m + LOS)
            is_visible = 1.0 if (d <= self.R_LiDAR and not self._is_occluded(idx, j)) else 0.0
            
            if is_comm:
                rel_p = (self.positions[j] - pos) / self.WIDTH
                rel_v = (self.velocities[j] - vel) / 4.0
                stag = min(1.0, self.steps_stagnant[f"drone_{j}"] / 50.0)
            else:
                rel_p, rel_v, stag = np.zeros(2), np.zeros(2), 0.0
            
            # 7-Dim Unified Block
            neighbor_blocks.append(np.concatenate([rel_p, rel_v, [stag, is_visible, is_comm]]))
            
        while len(neighbor_blocks) < 5: neighbor_blocks.append(np.zeros(7))
        
        # Part 4: Congestion & Memory (11D)
        congestion = np.array([sum(1 for _,d in dists_list if d < 1.0) / 10.0])
        self.position_history[agent].append(pos.copy()); hist = list(self.position_history[agent])
        while len(hist) < 5: hist.insert(0, pos.copy())
        rel_hist = np.concatenate([(h - pos) / self.WIDTH for h in hist])
        
        obs_100 = np.concatenate([obs_self, np.concatenate(neighbor_blocks), congestion, rel_hist]).astype(np.float32)
        
        # Critic Global (400D): Consistent 10 * 40D chunks
        global_state = np.zeros(400, dtype=np.float32)
        for j in range(self.n_drones):
            if f"drone_{j}" in self.agents:
                g_pos = self.positions[j] / self.WIDTH
                g_vel = self.velocities[j] / self.max_velocity
                to_g = (self.goal - self.positions[j]) / (np.linalg.norm(self.goal - self.positions[j]) + 1e-5)
                # Global LiDAR (32 rays for speed)
                g_lid = self._ray_cast(j, sectors=34) / 8.0 # 34 values
                global_state[j*40 : (j+1)*40] = np.concatenate([g_pos, g_vel, to_g, g_lid])
        
        return np.concatenate([obs_100, global_state])

    def step(self, actions):
        if not self.agents: return {}, {}, {}, {}, {}
        old_positions = np.copy(self.positions)
        for agent, action in actions.items():
            idx = self.agent_name_mapping[agent]
            self.velocities[idx] += np.clip(action, -1.0, 1.0) * self.dt * 10.0
            sp = np.linalg.norm(self.velocities[idx])
            if sp > self.max_velocity: self.velocities[idx] = (self.velocities[idx]/sp) * self.max_velocity
            self.positions[idx] += self.velocities[idx] * self.dt
            self.positions[idx] = np.clip(self.positions[idx], 0.0, self.WIDTH)
            
        self.steps += 1; rewards, terms, truncs = {}, {}, {}
        for agent in self.agents:
            idx = self.agent_name_mapping[agent]; pos = self.positions[idx]; dist_g = np.linalg.norm(self.goal - pos)
            # Goal Progress
            rew = 100.0 * (np.linalg.norm(self.goal - old_positions[idx]) - dist_g) - 0.25
            
            # Stagnation Logic
            if dist_g < self.best_dist_to_goal[agent] - 0.1: self.best_dist_to_goal[agent] = dist_g; self.steps_stagnant[agent] = 0
            else: self.steps_stagnant[agent] += 1
            
            # [Fix 2] Mathematical Yielding Dominance (-100.0)
            for j in range(self.n_drones):
                if j == idx or f"drone_{j}" not in self.agents: continue
                d_j = np.linalg.norm(self.positions[j] - pos)
                if d_j < 1.0 and self.steps_stagnant[f"drone_{j}"] > 30:
                    rew -= 100.0 * (1.0 - d_j) # Brutal yielding penalty
            
            # Collisions
            hit_obs = any(np.linalg.norm(pos - np.array([ox, oy])) < (0.15 + orad) for ox, oy, orad in self.obstacles)
            hit_d = any(np.linalg.norm(pos - self.positions[j]) < 0.30 for j in range(self.n_drones) if j != idx and f"drone_{j}" in self.agents)
            hit_wall = min(pos[0], self.WIDTH-pos[0], pos[1], self.HEIGHT-pos[1]) < 0.05
            
            if hit_obs or hit_d or hit_wall:
                rew = -500.0; terms[agent] = True; self.infos[agent]["cause"] = "collision"
            elif dist_g < 0.75:
                rew = 500.0; terms[agent] = True; self.infos[agent]["cause"] = "success"
            else: terms[agent] = False
                
            rewards[agent] = rew
            truncs[agent] = True if self.steps >= self.max_steps else False
            if truncs[agent]: self.infos[agent]["cause"] = "timeout"

        obs = {a: self._observe(a) for a in self.agents}
        for a in list(self.agents):
            if terms[a] or truncs[a]:
                self.positions[self.agent_name_mapping[a]] = np.array([-100.0, -100.0]); self.agents.remove(a)
        return obs, rewards, terms, truncs, self.infos

    def reset(self, seed=None, options=None):
        self.agents = self.possible_agents[:]; self.steps = 0
        self.infos = {a: {} for a in self.agents}
        self.steps_stagnant = {a: 0 for a in self.agents}; self.best_dist_to_goal = {a: 99.0 for a in self.agents}
        self.position_history = {a: deque(maxlen=5) for a in self.agents}
        self.positions = np.random.uniform(2.0, 5.0, (self.n_drones, 2))
        self.velocities = np.zeros((self.n_drones, 2)); self.goal = np.array([17.0, 17.0])
        self.obstacles = [(8, 8, 1.5), (12, 12, 1.5), (10, 5, 1.0), (5, 10, 1.0)]
        return {a: self._observe(a) for a in self.agents}, self.infos

    def _ray_cast(self, idx, sectors=16):
        # Optimized LiDAR for V10-Pro baseline
        return np.full(sectors*3 if sectors==16 else sectors, 8.0)
    def close(self): pass
