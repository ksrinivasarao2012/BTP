import numpy as np
import pygame
from pettingzoo import ParallelEnv
from gymnasium import spaces, Env as GymEnv
from collections import deque
import math
import sys

# ======================================================
#  PHASE B5 v13-CLEAN: NOISELESS IDENTITY BASELINE
#  Architecture: Fixed-ID Persistence (146D)
#  Signal: Explicit V2X Sender-Broadcast Layer
#  Goal: Absolute Performance Upper-Bound (95%+)
# ======================================================

class SwarmLidarEnv_v13_Clean(ParallelEnv):
    metadata = {'render_modes': ['human'], "name": "swarm_lidar_v13_clean"}

    def __init__(self, render_mode=None, target_density=0.25):
        super().__init__()
        self.n_drones = 10
        self.max_steps = 800
        self.WIDTH, self.HEIGHT = 20.0, 20.0
        self.drone_radius = 0.15
        self.dt = 0.1
        self.max_velocity = 2.0
        
        # SENSING RADII (No noise in this baseline)
        self.R_SENSOR = 8.0 
        self.R_COMM = 10.0

        self.possible_agents = [f"drone_{i}" for i in range(self.n_drones)]
        self.agent_name_mapping = dict(zip(self.possible_agents, list(range(self.n_drones))))
        
        # 146-Dim Local: 54(Self) + 81(9 Slots x 9D) + 1(Congestion) + 10(Memory)
        self.obs_size = 146 + 400
        self.observation_spaces = {a: spaces.Box(low=-np.inf, high=np.inf, shape=(self.obs_size,), dtype=np.float32) for a in self.possible_agents}
        self.action_spaces = {a: spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32) for a in self.possible_agents}
        
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
        """Step 1: Every drone generates its V2X broadcast packet once per step."""
        # No noise in the 'Clean' baseline
        self.broadcasts = {
            i: {
                'pos': self.positions[i].copy(),
                'vel': self.velocities[i].copy(),
                'stag': min(1.0, self.steps_stagnant[f"drone_{i}"] / 50.0)
            } for i in range(self.n_drones)
        }

    def _observe(self, agent):
        idx = self.agent_name_mapping[agent]
        pos, vel = self.positions[idx], self.velocities[idx]
        dist_goal = np.linalg.norm(self.goal - pos)
        to_goal = (self.goal - pos) / (dist_goal + 1e-5)
        lidar = self._ray_cast(idx)
        
        # Part 1: Self (54D)
        obs_self = np.concatenate([vel/2.0, to_goal, [dist_goal/28.0], [np.arctan2(vel[1], vel[0])/np.pi], lidar/8.0])
        
        # Part 2: Fixed-ID Teammates (81D total)
        teammate_blocks = []
        for j in range(self.n_drones):
            if j == idx: continue
            # 9D Block: [RelPosComm(2), RelVelComm(2), RelPosSensor(2), Stag(1), Vis(1), Comm(1)]
            slot = np.zeros(9, dtype=np.float32)
            if f"drone_{j}" in self.agents:
                d_j = np.linalg.norm(pos - self.positions[j])
                is_comm = 1.0 if d_j <= self.R_COMM else 0.0
                is_visible = 1.0 if (d_j <= self.R_SENSOR and not self._is_occluded(idx, j)) else 0.0
                
                # Step 2: Reception (Reading the broadcast packet)
                if is_comm:
                    msg = self.broadcasts[j]
                    slot[0:2] = (msg['pos'] - pos) / self.WIDTH  # Comm Pos
                    slot[2:4] = (msg['vel'] - vel) / 4.0        # Comm Vel
                    slot[6] = msg['stag']                        # Broadcasted Stagnation
                    slot[8] = 1.0                                # is_comm
                    
                # Sensor Truth (LiDAR 'Eyes')
                if is_visible:
                    slot[4:6] = (self.positions[j] - pos) / self.WIDTH # Sensor Pos Truth
                    slot[7] = 1.0                                      # is_visible
            
            teammate_blocks.append(slot)
            
        # Part 4: Swarm Metadata & Memory (11D)
        vicinity = sum(1 for j in range(self.n_drones) if j!=idx and f"drone_{j}" in self.agents and np.linalg.norm(pos-self.positions[j]) < 1.0)
        congestion = np.array([vicinity / 10.0])
        
        self.position_history[agent].append(pos.copy()); hist = list(self.position_history[agent])
        while len(hist) < 5: hist.insert(0, pos.copy())
        rel_hist = np.concatenate([(h - pos) / self.WIDTH for h in hist])
        
        obs_146 = np.concatenate([obs_self, np.concatenate(teammate_blocks), congestion, rel_hist]).astype(np.float32)
        
        # Global Critic (400D) - Standard MAPPO Omniscience
        global_state = np.zeros(400, dtype=np.float32)
        for j in range(self.n_drones):
            if f"drone_{j}" in self.agents:
                to_g = (self.goal - self.positions[j]) / (np.linalg.norm(self.goal-self.positions[j]) + 1e-5)
                g_lid = self._ray_cast(j, sectors=34) / 8.0
                global_state[j*40 : (j+1)*40] = np.concatenate([self.positions[j]/self.WIDTH, self.velocities[j]/2, to_g, g_lid])
        
        return np.concatenate([obs_146, global_state])

    def step(self, actions):
        if not self.agents: return {}, {}, {}, {}, {}
        old_pos = np.copy(self.positions)
        for agent, action in actions.items():
            idx = self.agent_name_mapping[agent]
            self.velocities[idx] += np.clip(action, -1.0, 1.0) * self.dt * 10.0
            sp = np.linalg.norm(self.velocities[idx])
            if sp > self.max_velocity: self.velocities[idx] = (self.velocities[idx]/sp) * self.max_velocity
            self.positions[idx] += self.velocities[idx] * self.dt
            self.positions[idx] = np.clip(self.positions[idx], 0.0, self.WIDTH)
            
        self.steps += 1; rewards, terms, truncs = {}, {}, {}
        
        # Prepare broadcasts for the OBSERVE phase
        self._prepare_broadcasts()
        
        for agent in self.agents:
            idx = self.agent_name_mapping[agent]; pos = self.positions[idx]; dist_g = np.linalg.norm(self.goal-pos)
            rew = 100.0 * (np.linalg.norm(self.goal - old_pos[idx]) - dist_g) - 0.25
            
            if dist_g < self.best_dist_to_goal[agent] - 0.1: self.best_dist_to_goal[agent] = dist_g; self.steps_stagnant[agent] = 0
            else: self.steps_stagnant[agent] += 1
            
            # Sigmoid Yielding Penalty ( capped at -50)
            for j in range(self.n_drones):
                if j == idx or f"drone_{j}" not in self.agents: continue
                d_j = np.linalg.norm(self.positions[j] - pos)
                if d_j < 1.0 and self.steps_stagnant[f"drone_{j}"] > 30:
                    rew -= 50.0 / (1.0 + math.exp(10 * (d_j - 0.5)))
            
            hit = any(np.linalg.norm(pos - np.array([ox, oy])) < (0.15 + orad) for ox, oy, orad in self.obstacles)
            hit = hit or (min(pos[0], self.WIDTH-pos[0], pos[1], self.HEIGHT-pos[1]) < 0.05)
            hit = hit or any(np.linalg.norm(pos - self.positions[j]) < 0.30 for j in range(self.n_drones) if j != idx and f"drone_{j}" in self.agents)
            
            if hit: rew = -500.0; terms[agent] = True; self.infos[agent]["cause"] = "collision"
            elif dist_g < 0.75: rew = 500.0; terms[agent] = True; self.infos[agent]["cause"] = "success"
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
        self._prepare_broadcasts()
        return {a: self._observe(a) for a in self.agents}, self.infos

    def _ray_cast(self, idx, sectors=16): return np.full(sectors*3 if sectors==16 else sectors, 8.0)
    def close(self): pass
