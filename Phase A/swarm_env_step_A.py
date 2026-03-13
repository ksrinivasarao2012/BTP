import numpy as np
import pygame
from pettingzoo import ParallelEnv
from gymnasium import spaces
import math

# ======================================================
#  PHASE 4 - STEP A: 10 Drones, 0 Traitors, 0 Obstacles
# ======================================================
class SwarmLidarEnv_StepA(ParallelEnv):
    metadata = {'render_modes': ['human'], "name": "swarm_lidar_stepA_v0"}

    def __init__(self, render_mode=None):
        super().__init__()
        self.render_mode = render_mode
        self.n_drones = 10
        self.num_traitors = 0
        self.num_honest = 10
        
        # Physics Constants
        self.dt = 0.1
        self.max_steps = 600
        self.max_velocity = 2.0
        self.WIDTH, self.HEIGHT = 20.0, 20.0  # 20x20 Field
        
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

    def reset(self, seed=None, options=None):
        self.agents = self.possible_agents[:]
        self.terminations = {agent: False for agent in self.agents}
        self.truncations = {agent: False for agent in self.agents}
        self.infos = {agent: {} for agent in self.agents}
        self.steps = 0
        
        # 1. Configurable Start Positions
        if options and "start_positions" in options:
            self.positions = np.array(options["start_positions"], dtype=np.float32)
            self.velocities = np.zeros((self.n_drones, 2), dtype=np.float32)
        else:
            self.velocities = np.zeros((self.n_drones, 2), dtype=np.float32)
            if np.random.random() < 0.8:
                # --- CLUSTERED SPAWN (80%) ---
                # Pick a random center and pack drones in a 2x2 box with safe spacing
                cx = np.random.uniform(3.0, self.WIDTH - 3.0)
                cy = np.random.uniform(3.0, self.HEIGHT - 3.0)
                half = 1.0  # 2x2 box
                min_dist = 0.3
                placed = []
                for i in range(self.n_drones):
                    for _ in range(500):
                        x = np.random.uniform(cx - half, cx + half)
                        y = np.random.uniform(cy - half, cy + half)
                        x = np.clip(x, 0.3, self.WIDTH - 0.3)
                        y = np.clip(y, 0.3, self.HEIGHT - 0.3)
                        if all(np.sqrt((x-px)**2 + (y-py)**2) >= min_dist for px, py in placed):
                            placed.append([x, y])
                            break
                    else:
                        # Fallback: expand area slightly
                        x = np.random.uniform(cx - half - 1, cx + half + 1)
                        y = np.random.uniform(cy - half - 1, cy + half + 1)
                        x = np.clip(x, 0.3, self.WIDTH - 0.3)
                        y = np.clip(y, 0.3, self.HEIGHT - 0.3)
                        placed.append([x, y])
                    self.positions[i] = [placed[-1][0], placed[-1][1]]
            else:
                # --- RANDOM SPREAD SPAWN (50%) ---
                for i in range(self.n_drones):
                    self.positions[i] = [np.random.uniform(1.0, self.WIDTH - 1.0), np.random.uniform(1.0, self.HEIGHT - 1.0)]
            
        # 2. Configurable Global Goal
        if options and "goal" in options:
            self.goal = np.array(options["goal"], dtype=np.float32)
        else:
            self.goal = np.array([np.random.uniform(1.0, self.WIDTH - 1.0), np.random.uniform(1.0, self.HEIGHT - 1.0)], dtype=np.float32)

        observations = {agent: self._observe(agent) for agent in self.agents}
        return observations, self.infos

    def _ray_cast(self, agent_idx):
        """Simulates 16-ray LiDAR (Only Wall & Drone detection in Step A)"""
        num_rays = 16
        max_range = 8.0 
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
            
            # Drone Interaction checks (Look out for other honest drones to prevent crashing)
            for j in range(self.n_drones):
                if j == agent_idx: continue
                # NEW FIX: Ignore dead/vanished drones (no ghosts)
                if self.possible_agents[j] not in self.agents: continue 
                
                to_drone = self.positions[j] - pos
                proj = np.dot(to_drone, ray_dir)
                if proj > 0:
                    closest = pos + proj * ray_dir
                    dist_to_ray = np.linalg.norm(closest - self.positions[j])
                    drone_radius = 0.15 
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
            
            # Pure ground truth for Step A
            rel_pos = (self.positions[j] - pos) / self.WIDTH
            norm_vel = self.velocities[j] / self.max_velocity
            
            # Does this agent still exist, or is it a dead ghost?
            is_active = 1.0 if self.possible_agents[j] in self.agents else 0.0
            
            # Broadcast ID shape: [rel_x, rel_y, vel_x, vel_y, is_active]
            obs_neighbors.append(np.concatenate([rel_pos, norm_vel, [is_active]]))
            
        return np.concatenate([obs_core, np.concatenate(obs_neighbors)]).astype(np.float32)

    def step(self, actions):
        if not self.agents:
            return {}, {}, {}, {}, {}

        # Store old positions to calculate potential field differences later
        old_positions = np.copy(self.positions)

        # 1. Physics Update
        for agent, action in actions.items():
            idx = self.agent_name_mapping[agent]
            action = np.clip(action, -1.0, 1.0)
            
            self.velocities[idx] += action * self.dt * 5.0
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
                com_positions = [self.positions[j] for j in close_neighbors]
                local_com = np.mean(com_positions, axis=0)
                
                dist_to_com_now = np.linalg.norm(pos - local_com)
                dist_to_com_before = np.linalg.norm(old_pos - local_com)
                
                # Reward expanding away from the center of mass of the cluster
                delta_com = dist_to_com_now - dist_to_com_before
                rewards[agent] += np.clip(delta_com * 30.0, -3.0, 3.0)
                
                # Approach 2: "School Zone" Speed Limit
                # Penalize moving fast when surrounded by drones to avoid instantaneous collisions
                speed = np.linalg.norm(self.velocities[idx])
                safe_speed = self.max_velocity * 0.35 # 35% speed limit when tangled
                if speed > safe_speed:
                    speed_penalty = ((speed - safe_speed) / self.max_velocity) ** 2
                    rewards[agent] -= speed_penalty * len(close_neighbors) * 5.0
                    
                # Approach 3: Social Distancing Repulsion
                # Prevent funneling at the goal by severely penalizing any drone that gets within 0.4 units (collision is at 0.25)
                for j in close_neighbors:
                    dist = np.linalg.norm(pos - self.positions[j])
                    if dist < 0.4:
                        rewards[agent] -= (0.4 - dist) * 50.0
            
            # --- R_safe & Terminations ---
            hit_wall = False
            hit_drone = False
            
            # Map Bounds Validation (Crash if they touch the literal edge)
            distance_to_edge = min(pos[0], self.WIDTH - pos[0], pos[1], self.HEIGHT - pos[1])
            if distance_to_edge <= 0.05: 
                hit_wall = True
            
            # Swarm Drone-on-Drone Collision Check
            for j in range(self.n_drones):
                if j == idx: continue
                # NEW FIX: Ignore hitting drones that have already won/died
                if self.possible_agents[j] not in self.agents: continue 
                
                if np.linalg.norm(pos - self.positions[j]) < 0.25: # 2 * drone_radius
                    hit_drone = True
                    break

            if hit_wall:
                rewards[agent] = -100.0 # Absolute worst outcome
                self.terminations[agent] = True
                self.infos[agent] = {"cause": "collision"}
            elif hit_drone:
                rewards[agent] = -50.0  # Bad, but slightly less catastrophic than the edge of the world
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
            pygame.display.set_caption("Step A: 10 Drones (No Obstacles / No Traitors)")
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
    env = SwarmLidarEnv_StepA(render_mode="human")
    obs, info = env.reset()
    
    print("Environment Step A initialized! Running random actions to preview PyGame...")
    
    for _ in range(300):
        actions = {agent: env.action_space(agent).sample() for agent in env.agents}
        obs, rewards, term, trunc, info = env.step(actions)
        env.render()
        
        if not env.agents:
            obs, info = env.reset()
            
    pygame.quit()
    print("Preview complete.")
