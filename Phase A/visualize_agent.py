import numpy as np
import pygame
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
import sys
import json
import glob
import os

class DroneLidarEnv(gym.Env):
    metadata = {"render_modes": ["human"]}

    def __init__(self, render_mode=None):
        super().__init__()
        self.render_mode = render_mode
        

        self.dt = 0.1
        self.max_steps = 600
        self.max_velocity = 2.0
        self.gamma = 0.995
        
        self.WIDTH, self.HEIGHT = 700, 700
        self.screen, self.clock = None, None


        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(22,), dtype=np.float32)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)
        
        self.prev_action = np.zeros(2, dtype=np.float32)

        self.pos = np.zeros(2, dtype=np.float32)
        self.vel = np.zeros(2, dtype=np.float32)
        self.goal = np.zeros(2, dtype=np.float32)
        self.obstacles = []
        self.steps = 0
        
        self.path = []

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        if options and "config" in options:
            config = options["config"]
            
            if "start" in config:
                self.pos = np.array(config["start"], dtype=np.float32)
            else:
                self.pos = np.array([1.0, 1.0], dtype=np.float32) 
                
            self.goal = np.array(config["goal"], dtype=np.float32)
            # Ensure obstacles are a list of tuples (x, y, r)
            self.obstacles = [tuple(obs) for obs in config["obstacles"]]
            
        else:
            self.pos = np.array([np.random.uniform(0.8, 5.2), np.random.uniform(0.8, 5.2)], dtype=np.float32)
            self.vel = np.zeros(2, dtype=np.float32)
            
            for _ in range(100):
                cand = np.array([np.random.uniform(0.8, 6.2), np.random.uniform(0.8, 6.2)])
                if np.linalg.norm(cand - self.pos) > 3.0:
                    self.goal = cand
                    break
            else:
                self.goal = np.array([5.5, 5.5])

            self.obstacles = []
            num_obs = np.random.randint(6, 9)
            for _ in range(num_obs):
                for _ in range(20):
                    ox, oy = np.random.uniform(1, 6), np.random.uniform(1, 6)
                    r = np.random.uniform(0.3, 0.6)
                    if np.linalg.norm(self.pos - [ox, oy]) > (r+1.0) and \
                       np.linalg.norm(self.goal - [ox, oy]) > (r+1.0):
                        self.obstacles.append((ox, oy, r))
                        break

        self.vel = np.zeros(2, dtype=np.float32)
        self.steps = 0
        self.prev_action = np.zeros(2, dtype=np.float32)
        self.path = [self.pos.copy()]   
        return self._observe(), {}

    def _ray_cast(self):
        """Simulates LiDAR (Calculated but NOT Drawn)"""
        num_rays = 16
        max_range = 5.0
        readings = np.full(num_rays, max_range, dtype=np.float32)
        angles = np.linspace(0, 2*np.pi, num_rays, endpoint=False)
        
        for i, angle in enumerate(angles):
            ray_dir = np.array([np.cos(angle), np.sin(angle)])
            min_d = max_range
            
            for boundary, axis, direction in [(6.5, 0, 1), (-0.5, 0, -1), (6.5, 1, 1), (-0.5, 1, -1)]:
                if ray_dir[axis] * direction > 0:
                    d = (boundary - self.pos[axis]) / ray_dir[axis]
                    if 0 < d < min_d: min_d = d

            for ox, oy, r in self.obstacles:
                to_obs = np.array([ox, oy]) - self.pos
                proj = np.dot(to_obs, ray_dir)
                if proj > 0:
                    closest = self.pos + proj * ray_dir
                    dist_to_ray = np.linalg.norm(closest - np.array([ox, oy]))
                    if dist_to_ray < r:
                        intersect_dist = proj - np.sqrt(r**2 - dist_to_ray**2)
                        if 0 < intersect_dist < min_d: min_d = intersect_dist
            
            readings[i] = min_d
        return readings

    def _observe(self):
        dist_goal = np.linalg.norm(self.goal - self.pos)
        to_goal = (self.goal - self.pos) / (dist_goal + 1e-5)
        lidar = self._ray_cast() / 5.0
        obs = np.concatenate([
            self.vel / 2.0,
            to_goal,
            [dist_goal / 7.0],
            [np.arctan2(self.vel[1], self.vel[0])],
            lidar
        ])
        return np.array(obs, dtype=np.float32)

    def _potential(self, pos):
        return -np.linalg.norm(self.goal - pos)

    def step(self, action):
        action = np.clip(action, -1.0, 1.0)
        self.vel += action * self.dt * 5.0
        speed = np.linalg.norm(self.vel)
        if speed > self.max_velocity: self.vel = (self.vel / speed) * self.max_velocity
        
        old_pos = self.pos.copy()
        self.pos += self.vel * self.dt
        self.steps += 1
        
        self.path.append(self.pos.copy())
        
        dist_goal = np.linalg.norm(self.goal - self.pos)

        reward = 10.0 * (self.gamma * self._potential(self.pos) - self._potential(old_pos))
        reward -= 0.05 
        

        smoothness_penalty = np.linalg.norm(action - self.prev_action) * 0.5 
        reward -= smoothness_penalty
        self.prev_action = action.copy()

        terminated = False
        collision = False
        
        if not (-0.5 < self.pos[0] < 6.5 and -0.5 < self.pos[1] < 6.5):
            collision = True
        for ox, oy, r in self.obstacles:
            if np.linalg.norm(self.pos - [ox, oy]) < r:
                collision = True
                break
                
        if collision:
            reward = -100.0
            terminated = True
        elif dist_goal < 0.35:
            reward = 100.0 + (50.0 / (1.0 + speed))
            terminated = True
            
        truncated = self.steps >= self.max_steps
        return self._observe(), reward, terminated, truncated, {}

    def render(self):
        if self.screen is None:
            pygame.init()
            self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
            self.clock = pygame.time.Clock()
        
        self.clock.tick(30)
        self.screen.fill((30, 30, 30))
        def w2s(p): return int((p[0]+1)/8*self.WIDTH), int(self.HEIGHT - (p[1]+1)/8*self.HEIGHT)
        
        for ox, oy, r in self.obstacles:
            pygame.draw.circle(self.screen, (200, 60, 60), w2s((ox, oy)), int(r*85))
            
        pygame.draw.circle(self.screen, (60, 200, 60), w2s(self.goal), 15)
        
        for p in self.path:
            pygame.draw.circle(self.screen, (200, 200, 200), w2s(p), 2)
        
        
        pygame.draw.circle(self.screen, (100, 100, 255), w2s(self.pos), 10)
        
        
        heading = np.arctan2(self.vel[1], self.vel[0])
        nose_x = self.pos[0] + 0.3 * np.cos(heading)
        nose_y = self.pos[1] + 0.3 * np.sin(heading)
        pygame.draw.line(self.screen, (255, 255, 255), w2s(self.pos), w2s([nose_x, nose_y]), 2)
        
        pygame.display.flip()

if __name__ == "__main__":
    
    try:
        model = PPO.load("lidar_single_agent_smooth")
        print("✅ Model 'lidar_single_agent_smooth' loaded.")
    except:
        try:
            model = PPO.load("lidar_single_agent")
            print("⚠️ 'lidar_single_agent_smooth' not found. Loaded 'lidar_single_agent'.")
        except:
            print("❌ Error: Could not load model. Train it first!")
            sys.exit()

    test_files = []
    
    if len(sys.argv) > 1:
        provided_file = sys.argv[1]
        if os.path.exists(provided_file):
            test_files = [provided_file]
        else:
            print(f"❌ Error: The file '{provided_file}' does not exist.")
            sys.exit()
    else:

        test_files = sorted(glob.glob("test_case_*.json"))
        if not test_files:
            test_files = sorted(glob.glob("test_cases/test_case_*.json"))
            
    if not test_files:
        print("⚠️ No test case files found! Running random episodes.")
        
        env = DroneLidarEnv(render_mode="human")
        for ep in range(10):
            obs, _ = env.reset()
            done = False
            score = 0
            while not done:
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, term, trunc, _ = env.step(action)
                score += reward
                done = term or trunc
                env.render()
                pygame.time.wait(10)
            print(f"Random Episode {ep+1}: Score {score:.1f}")
            
    else:
        print(f"✅ Found {len(test_files)} test cases.")

        env = DroneLidarEnv(render_mode="human")

        for filename in test_files:
            print(f"\n🎬 Loading {filename}...")
            
            options = {}
            with open(filename, 'r') as f:
                config = json.load(f)
                options["config"] = config
            
            obs, _ = env.reset(options=options)
            done = False
            score = 0
            steps = 0
            
            pygame.time.wait(500) 

            while not done:
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, term, trunc, _ = env.step(action)
                score += reward
                steps += 1
                done = term or trunc
                env.render()

            min_dist = np.linalg.norm(env.goal - env.pos)
            outcome = "✅ SUCCESS" if score > 0 else f"❌ FAILED (Dist: {min_dist:.2f}m)"
            print(f"Result: {outcome} | Steps: {steps}")
