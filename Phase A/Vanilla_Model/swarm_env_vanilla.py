import numpy as np
from pettingzoo import ParallelEnv
from gymnasium import spaces
import math

class SwarmLidarEnv_Vanilla(ParallelEnv):
    metadata = {'render_modes': ['human'], "name": "swarm_lidar_vanilla_v0"}

    def __init__(self, render_mode=None):
        super().__init__()
        self.render_mode = render_mode
        self.n_drones = 10
        self.dt = 0.1
        self.max_steps = 600
        self.max_velocity = 2.0
        self.WIDTH, self.HEIGHT = 20.0, 20.0
        self.possible_agents = [f"drone_{i}" for i in range(self.n_drones)]
        self.agent_name_mapping = dict(zip(self.possible_agents, list(range(self.n_drones))))
        self.positions = np.zeros((self.n_drones, 2), dtype=np.float32)
        self.velocities = np.zeros((self.n_drones, 2), dtype=np.float32)
        self.goal = np.array([18.0, 18.0], dtype=np.float32)
        
        obs_size = 22 + (5 * (self.n_drones - 1))
        self.observation_spaces = {a: spaces.Box(low=-np.inf, high=np.inf, shape=(obs_size,), dtype=np.float32) for a in self.possible_agents}
        self.action_spaces = {a: spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32) for a in self.possible_agents}

    def reset(self, seed=None, options=None):
        self.agents = self.possible_agents[:]
        self.terminations = {agent: False for agent in self.agents}
        self.truncations = {agent: False for agent in self.agents}
        self.infos = {agent: {} for agent in self.agents}
        self.steps = 0
        self.positions = np.random.uniform(2.0, 18.0, (self.n_drones, 2)).astype(np.float32)
        self.velocities = np.zeros((self.n_drones, 2), dtype=np.float32)
        self.goal = np.random.uniform(2.0, 18.0, 2).astype(np.float32)
        return {a: self._observe(a) for a in self.agents}, {a: {} for a in self.agents}

    def _ray_cast(self, agent_idx):
        num_rays, max_range = 16, 8.0
        readings = np.full(num_rays, max_range, dtype=np.float32)
        angles = np.linspace(0, 2*np.pi, num_rays, endpoint=False)
        pos = self.positions[agent_idx]
        for i, angle in enumerate(angles):
            ray_dir = np.array([math.cos(angle), math.sin(angle)])
            min_d = max_range
            # Wall checks
            for boundary, axis, direction in [(self.WIDTH, 0, 1), (0, 0, -1), (self.HEIGHT, 1, 1), (0, 1, -1)]:
                if ray_dir[axis] * direction > 0:
                    d = (boundary - pos[axis]) / ray_dir[axis]
                    if 0 < d < min_d: min_d = d
            # Drone Interaction checks (WITH GHOST FIX)
            for j in range(self.n_drones):
                if j == agent_idx or self.possible_agents[j] not in self.agents: continue
                to_drone = self.positions[j] - pos
                proj = np.dot(to_drone, ray_dir)
                if proj > 0:
                    dist_to_ray = np.linalg.norm((pos + proj * ray_dir) - self.positions[j])
                    if dist_to_ray < 0.15:
                        intersect_dist = proj - math.sqrt(0.15**2 - dist_to_ray**2)
                        if 0 < intersect_dist < min_d: min_d = intersect_dist
            readings[i] = min_d
        return readings

    def _observe(self, agent):
        idx = self.agent_name_mapping[agent]
        pos, vel = self.positions[idx], self.velocities[idx]
        dist_goal = np.linalg.norm(self.goal - pos)
        to_goal = (self.goal - pos) / (dist_goal + 1e-5)
        obs_self = np.concatenate([vel/2.0, to_goal, [dist_goal/28.0], [np.arctan2(vel[1], vel[0])], self._ray_cast(idx)/8.0])
        obs_neighbors = []
        for j in range(self.n_drones):
            if j == idx: continue
            obs_neighbors.append(np.concatenate([(self.positions[j]-pos)/20.0, self.velocities[j]/2.0, [1.0 if self.possible_agents[j] in self.agents else 0.0]]))
        return np.concatenate([obs_self, np.concatenate(obs_neighbors)]).astype(np.float32)

    def step(self, actions):
        old_positions = np.copy(self.positions)
        self.infos = {agent: {} for agent in self.agents}
        for agent, action in actions.items():
            idx = self.agent_name_mapping[agent]
            self.velocities[idx] += np.clip(action, -1.0, 1.0) * self.dt * 5.0
            speed = np.linalg.norm(self.velocities[idx])
            if speed > self.max_velocity: self.velocities[idx] = (self.velocities[idx]/speed)*self.max_velocity
            self.positions[idx] = np.clip(self.positions[idx] + self.velocities[idx]*self.dt, 0.0, self.WIDTH)
        
        self.steps += 1
        rewards, terminations, truncations = {}, {}, {}
        for agent in self.agents:
            idx = self.agent_name_mapping[agent]
            pos, old_pos = self.positions[idx], old_positions[idx]
            dg, odg = np.linalg.norm(self.goal-pos), np.linalg.norm(self.goal-old_pos)
            
            # VANILLA REWARDS ONLY
            rewards[agent] = 10.0 * (odg - dg) - 0.05
            
            # Collision Check
            collision = any(np.linalg.norm(pos-self.positions[j]) < 0.25 for j in range(self.n_drones) if j!=idx and self.possible_agents[j] in self.agents)
            off_map = min(pos[0], 20-pos[0], pos[1], 20-pos[1]) <= 0.05
            
            info = {}
            if collision or off_map:
                rewards[agent], terminations[agent] = -50.0, True
                info["cause"] = "collision"
            elif dg < 0.75:
                rewards[agent], terminations[agent] = 100.0, True
                info["cause"] = "success"
            else:
                terminations[agent] = False
                
            truncations[agent] = self.steps >= self.max_steps
            if truncations[agent] and not terminations[agent]:
                info["cause"] = "timeout"
                
            self.infos[agent] = info
            
        self.agents = [a for a in self.agents if not (terminations[a] or truncations[a])]
        return {a: self._observe(a) for a in self.agents}, rewards, terminations, truncations, self.infos
    
    def observation_space(self, agent): return self.observation_spaces[agent]
    def action_space(self, agent): return self.action_spaces[agent]

    def render(self):
        if self.render_mode != "human": return
        if not hasattr(self, 'screen') or self.screen is None:
            import pygame
            pygame.init()
            pygame.display.set_caption("Vanilla Swarm Visualization")
            self.screen = pygame.display.set_mode((800, 800))
            self.clock = pygame.time.Clock()
            
        import pygame
        self.clock.tick(30)
        self.screen.fill((30, 30, 30))
        
        def w2s(p):
            px = max(0.0, min(float(p[0]), self.WIDTH))
            py = max(0.0, min(float(p[1]), self.HEIGHT))
            return int((px / self.WIDTH) * 800), int(800 - (py / self.HEIGHT) * 800)
            
        pygame.draw.circle(self.screen, (60, 200, 60), w2s(self.goal), 20)
        for agent in self.possible_agents:
            idx = self.agent_name_mapping[agent]
            color = (100, 100, 255) if agent in self.agents else (255, 50, 50)
            pygame.draw.circle(self.screen, color, w2s(self.positions[idx]), 8)
            
        pygame.display.flip()
