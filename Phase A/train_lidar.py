import numpy as np
import pygame
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
import torch

# ======================================================
#      IEEE-STANDARD SINGLE AGENT LIDAR ENV
# ======================================================
class DroneLidarEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(self, render_mode=None):
        super().__init__()
        self.render_mode = render_mode
        
        # Physics Constants 
        self.dt = 0.1
        self.max_steps = 600
        self.max_velocity = 2.0
        self.gamma = 0.995
        
        # Dimensions
        self.WIDTH, self.HEIGHT = 700, 700
        self.screen, self.clock = None, None

        # OBSERVATION SPACE: 
        # 16 Lidar Rays + 2 Vel + 2 Goal Vec + 1 Goal Dist + 1 Heading = 22 Values
        # This represents the "Physical Sensor" data 
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(22,), dtype=np.float32)
        
        # ACTION SPACE: Continuous Velocity Control (Vx, Vy) [cite: 58]
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)
        
        # Smoothing
        self.prev_action = np.zeros(2, dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # 1. Random Start & Goal (Prevents "Overfitting" to one path)
        self.pos = np.array([np.random.uniform(0.8, 5.2), np.random.uniform(0.8, 5.2)], dtype=np.float32)
        self.vel = np.zeros(2, dtype=np.float32)
        self.steps = 0
        self.prev_action = np.zeros(2, dtype=np.float32)
        
        # Ensure goal is at least 3.0m away
        for _ in range(100):
            cand = np.array([np.random.uniform(0.8, 6.2), np.random.uniform(0.8, 6.2)])
            if np.linalg.norm(cand - self.pos) > 3.0:
                self.goal = cand
                break
        else:
            self.goal = np.array([5.5, 5.5])

        # 2. Dense Obstacle Field (Static Obstacles) 
        # Generating 6-9 random obstacles to create a "Many Obstacles" scenario
        self.obstacles = []
        num_obs = np.random.randint(6, 9)
        for _ in range(num_obs):
            for _ in range(20):
                ox, oy = np.random.uniform(1, 6), np.random.uniform(1, 6)
                r = np.random.uniform(0.3, 0.6)
                # Don't spawn on top of drone or goal
                if np.linalg.norm(self.pos - [ox, oy]) > (r+1.0) and \
                   np.linalg.norm(self.goal - [ox, oy]) > (r+1.0):
                    self.obstacles.append((ox, oy, r))
                    break

        return self._observe(), {}

    def _ray_cast(self):
        """
        Simulates the 'Trusted Physical Sensor' (LiDAR).
        Computes distance to nearest object along 16 radial rays.
        """
        num_rays = 16
        max_range = 5.0
        readings = np.full(num_rays, max_range, dtype=np.float32)
        angles = np.linspace(0, 2*np.pi, num_rays, endpoint=False)
        
        for i, angle in enumerate(angles):
            ray_dir = np.array([np.cos(angle), np.sin(angle)])
            min_d = max_range
            
            # A. Wall Intersection
            # (Math to find intersection with x=0, x=7, y=0, y=7 bounds)
            for boundary, axis, direction in [(6.5, 0, 1), (-0.5, 0, -1), (6.5, 1, 1), (-0.5, 1, -1)]:
                if ray_dir[axis] * direction > 0:
                    d = (boundary - self.pos[axis]) / ray_dir[axis]
                    if 0 < d < min_d: min_d = d

            # B. Obstacle Intersection
            for ox, oy, r in self.obstacles:
                to_obs = np.array([ox, oy]) - self.pos
                proj = np.dot(to_obs, ray_dir)
                if proj > 0: # Object is in front
                    closest = self.pos + proj * ray_dir
                    dist_to_ray = np.linalg.norm(closest - np.array([ox, oy]))
                    if dist_to_ray < r:
                        # Pythagoras to find impact point
                        intersect_dist = proj - np.sqrt(r**2 - dist_to_ray**2)
                        if 0 < intersect_dist < min_d: min_d = intersect_dist
            
            readings[i] = min_d
        return readings

    def _observe(self):
        # Kinematics
        dist_goal = np.linalg.norm(self.goal - self.pos)
        to_goal = (self.goal - self.pos) / (dist_goal + 1e-5)
        
        # LiDAR (Normalized 0.0-1.0)
        lidar = self._ray_cast() / 5.0
        
        # Combine into state vector
        obs = np.concatenate([
            self.vel / 2.0,      # Normalized Vel
            to_goal,             # Goal Vector (x,y)
            [dist_goal / 7.0],   # Goal Dist
            [np.arctan2(self.vel[1], self.vel[0])], # Heading
            lidar                # 16 Ray Distances
        ])
        return np.array(obs, dtype=np.float32)

    def _potential(self, pos):
        return -np.linalg.norm(self.goal - pos)

    def step(self, action):
        # 1. Physics Update 
        action = np.clip(action, -1.0, 1.0)
        self.vel += action * self.dt * 5.0
        speed = np.linalg.norm(self.vel)
        if speed > self.max_velocity: self.vel = (self.vel / speed) * self.max_velocity
        
        old_pos = self.pos.copy()
        self.pos += self.vel * self.dt
        self.steps += 1
        dist_goal = np.linalg.norm(self.goal - self.pos)

        # 2. Rewards [cite: 61]
        # R_goal: Potential Field + Closing Speed
        reward = 10.0 * (self.gamma * self._potential(self.pos) - self._potential(old_pos))
        reward -= 0.05 # Existential penalty (time cost)

        # 3. Action Smoothing Check
        smoothness_penalty = np.linalg.norm(action - self.prev_action) * 0.5 
        reward -= smoothness_penalty
        self.prev_action = action.copy()
        
        # 4. Collision Logic (R_safe) [cite: 64]
        terminated = False
        collision = False
        
        # Wall Check
        if not (-0.5 < self.pos[0] < 6.5 and -0.5 < self.pos[1] < 6.5):
            collision = True
        # Obstacle Check
        for ox, oy, r in self.obstacles:
            if np.linalg.norm(self.pos - [ox, oy]) < r:
                collision = True
                break
                
        if collision:
            reward = -100.0 # Strict penalty as per PDF [cite: 64]
            terminated = True
        elif dist_goal < 0.35:
            reward = 100.0 + (50.0 / (1.0 + speed)) # Success Bonus
            terminated = True
            
        truncated = self.steps >= self.max_steps
        return self._observe(), reward, terminated, truncated, {}

    def render(self):
        if self.render_mode != "human": return
        if self.screen is None:
            pygame.init()
            self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
            self.clock = pygame.time.Clock()
        
        self.clock.tick(30)
        self.screen.fill((30, 30, 30)) # Dark Grey Background
        
        def w2s(p): # World to Screen
            return int((p[0]+1)/8*self.WIDTH), int(self.HEIGHT - (p[1]+1)/8*self.HEIGHT)
        
        # Draw Lidar Rays (Cyan Lines) - Visual Proof of Sensing
        lidar = self._ray_cast()
        angles = np.linspace(0, 2*np.pi, 16, endpoint=False)
        for i, dist in enumerate(lidar):
            end_x = self.pos[0] + dist * np.cos(angles[i])
            end_y = self.pos[1] + dist * np.sin(angles[i])
            pygame.draw.line(self.screen, (0, 200, 200), w2s(self.pos), w2s([end_x, end_y]), 1)

        # Draw Obstacles (Red)
        for ox, oy, r in self.obstacles:
            pygame.draw.circle(self.screen, (200, 60, 60), w2s((ox, oy)), int(r*85))
            
        # Draw Goal (Green) & Drone (Blue)
        pygame.draw.circle(self.screen, (60, 200, 60), w2s(self.goal), 15)
        pygame.draw.circle(self.screen, (100, 100, 255), w2s(self.pos), 10)
        
        pygame.display.flip()

# ======================================================
#      TRAINING LOOP
# ======================================================
if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "train"
    
    if mode == "train":
        print("🚀 Starting Single-Agent LiDAR Training (with Smoothing)...")
        # Parallelize environments for faster data collection
        env = SubprocVecEnv([lambda: DroneLidarEnv() for _ in range(8)])
        
        model = PPO("MlpPolicy", env, verbose=1, 
                   ent_coef=0.01, # Encourage exploration
                   gamma=0.995,   # Long horizon
                   learning_rate=3e-4)
        
        # Train for 1.5M steps to ensure robust obstacle avoidance
        model.learn(total_timesteps=1_500_000)
        model.save("lidar_single_agent_smooth")
        print("✅ Training Complete.")
        
    else:
        print("👀 Evaluating...")
        # Try both models
        try:
            model = PPO.load("lidar_single_agent_smooth")
        except:
            model = PPO.load("lidar_single_agent")
            
        env = DroneLidarEnv(render_mode="human")
        
        for ep in range(10):
            obs, _ = env.reset()
            done = False
            score = 0
            while not done:
                action, _ = model.predict(obs)
                obs, reward, term, trunc, _ = env.step(action)
                score += reward
                done = term or trunc
                env.render()
            print(f"Episode {ep+1}: Score {score:.1f}")