import numpy as np
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
import time
import sys
from save_performance import save_results

# ======================================================
#      HEADLESS LIDAR ENV (OPTIMIZED FOR BATCH TEST)
# ======================================================
class DroneLidarBatchEnv(gym.Env):
    def __init__(self):
        super().__init__()
        
        # Physics Constants 
        self.dt = 0.1
        self.max_steps = 600
        self.max_velocity = 2.0
        self.gamma = 0.995
        
        # Dimensions (Logical only, no screen)
        self.WIDTH, self.HEIGHT = 700, 700

        # Observation & Action Space
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(22,), dtype=np.float32)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)
        
        # Smoothing
        self.prev_action = np.zeros(2, dtype=np.float32)

        # State placeholders
        self.pos = np.zeros(2, dtype=np.float32)
        self.vel = np.zeros(2, dtype=np.float32)
        self.goal = np.zeros(2, dtype=np.float32)
        self.obstacles = []
        self.steps = 0

    def _dist_point_to_segment(self, p, a, b):
        """Calculates distance from point p to line segment ab"""
        ab = b - a
        ap = p - a
        if np.dot(ab, ab) == 0: return np.linalg.norm(ap)
        t = np.clip(np.dot(ap, ab) / np.dot(ab, ab), 0, 1)
        closest = a + t * ab
        return np.linalg.norm(p - closest)

    def reset(self, seed=None, options=None):
        # 1. Loop until we find a valid "Hard" configuration
        while True:
            # Random Start & Goal
            self.pos = np.array([np.random.uniform(0.8, 6.2), np.random.uniform(0.8, 6.2)], dtype=np.float32)
            
            # Find a goal at least 4.0m away (Long distance)
            for _ in range(20):
                cand = np.array([np.random.uniform(0.8, 6.2), np.random.uniform(0.8, 6.2)], dtype=np.float32)
                if np.linalg.norm(cand - self.pos) > 4.0:
                    self.goal = cand
                    break
            else:
                continue # Retry if goal is too close

            # 2. Generate Dense Obstacles (6 to 9)
            self.obstacles = []
            candidates = []
            num_obs = np.random.randint(6, 9)
            
            for _ in range(num_obs):
                for _ in range(10): # Try to place non-overlapping
                    ox, oy = np.random.uniform(1, 6), np.random.uniform(1, 6)
                    r = np.random.uniform(0.3, 0.6)
                    # Check overlap with Start/Goal
                    if np.linalg.norm(self.pos - [ox, oy]) > (r+0.8) and \
                       np.linalg.norm(self.goal - [ox, oy]) > (r+0.8):
                        candidates.append((ox, oy, r))
                        break
            
            # 3. CRITICAL CHECK: Are there 2+ objects BETWEEN start and goal?
            blocking_count = 0
            for ox, oy, r in candidates:
                d = self._dist_point_to_segment(np.array([ox, oy]), self.pos, self.goal)
                # If obstacle is close to the direct line path, it's a "blocker"
                if d < (r + 0.3): # radius + drone_safety_margin
                    blocking_count += 1
            
            if blocking_count >= 2:
                self.obstacles = candidates
                break # Found a valid hard scenario!

        self.vel = np.zeros(2, dtype=np.float32)
        self.steps = 0
        self.prev_action = np.zeros(2, dtype=np.float32)
        return self._observe(), {}

    def _ray_cast(self):
        """Optimized LiDAR calculation"""
        num_rays = 16
        max_range = 5.0
        readings = np.full(num_rays, max_range, dtype=np.float32)
        angles = np.linspace(0, 2*np.pi, num_rays, endpoint=False)
        
        # Pre-compute obstacle array for speed
        obs_arr = np.array([(o[0], o[1], o[2]) for o in self.obstacles], dtype=np.float32)
        
        for i, angle in enumerate(angles):
            ray_dir = np.array([np.cos(angle), np.sin(angle)])
            min_d = max_range
            
            # Wall Intersection
            for boundary, axis, direction in [(6.5, 0, 1), (-0.5, 0, -1), (6.5, 1, 1), (-0.5, 1, -1)]:
                if ray_dir[axis] * direction > 0:
                    d = (boundary - self.pos[axis]) / ray_dir[axis]
                    if 0 < d < min_d: min_d = d

            # Obstacle Intersection
            if len(obs_arr) > 0:
                to_obs = obs_arr[:, :2] - self.pos
                proj = np.dot(to_obs, ray_dir)
                
                # Mask: projected > 0
                valid_mask = proj > 0
                if np.any(valid_mask):
                    valid_proj = proj[valid_mask]
                    valid_to_obs = to_obs[valid_mask]
                    valid_r = obs_arr[valid_mask, 2]
                    
                    # Closest point distance
                    closest = self.pos + valid_proj[:, None] * ray_dir
                    dist_to_ray = np.linalg.norm(closest - (self.pos + valid_to_obs), axis=1)
                    
                    # Intersection check
                    hit_mask = dist_to_ray < valid_r
                    if np.any(hit_mask):
                        # Calculate impact distance
                        offsets = np.sqrt(valid_r[hit_mask]**2 - dist_to_ray[hit_mask]**2)
                        impact_dists = valid_proj[hit_mask] - offsets
                        
                        # Filter for positive and min
                        pos_impacts = impact_dists[impact_dists > 0]
                        if len(pos_impacts) > 0:
                            min_d = min(min_d, np.min(pos_impacts))

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

    def step(self, action):
        action = np.clip(action, -1.0, 1.0)
        self.vel += action * self.dt * 5.0
        speed = np.linalg.norm(self.vel)
        if speed > self.max_velocity: self.vel = (self.vel / speed) * self.max_velocity
        
        self.pos += self.vel * self.dt
        self.steps += 1
        self.prev_action = action.copy() # Update for consistency, though unused in calc here
        
        dist_goal = np.linalg.norm(self.goal - self.pos)
        
        terminated = False
        truncated = False
        outcome = "RUNNING"
        
        # Wall Check
        if not (-0.5 < self.pos[0] < 6.5 and -0.5 < self.pos[1] < 6.5):
            terminated = True
            outcome = "CRASH_WALL"

        # Obstacle Check
        elif any(np.linalg.norm(self.pos - [o[0], o[1]]) < o[2] for o in self.obstacles):
            terminated = True
            outcome = "CRASH_OBS"
                
        # Success Check
        elif dist_goal < 0.35:
            terminated = True
            outcome = "SUCCESS"
            
        # Timeout Check
        elif self.steps >= self.max_steps:
            truncated = True
            outcome = "TIMEOUT"

        return self._observe(), 0, terminated, truncated, {"outcome": outcome}

# ======================================================
#      MASSIVE BATCH TESTER
# ======================================================
if __name__ == "__main__":
    
    # 1. Configuration
    NUM_EPISODES = 1_000 
    MODEL_PATH = "lidar_single_agent"
    
    print(f"🚀 Starting Batch Test: {NUM_EPISODES} Episodes")
    print("Conditions: Random Start/Goal, At least 2 Obstacles Blocking Path")

    # 2. Load Model
    try:
        model = PPO.load("lidar_single_agent_smooth")
        print("✅ Model 'lidar_single_agent_smooth' loaded.")
    except:
        try:
            model = PPO.load("lidar_single_agent")
            print("⚠️ 'lidar_single_agent_smooth' not found. Loaded 'lidar_single_agent'.")
        except:
            print("❌ Error: Model not found. Train it first!")
            sys.exit()

    env = DroneLidarBatchEnv()
    
    # 3. Counters
    stats = {
        "SUCCESS": 0,
        "CRASH_OBS": 0,
        "CRASH_WALL": 0,
        "TIMEOUT": 0
    }

    start_time = time.time()
    
    # 4. The Loop
    for i in range(NUM_EPISODES):
        obs, _ = env.reset()
        done = False
        
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, _, term, trunc, info = env.step(action)
            done = term or trunc
            
            if done:
                outcome = info["outcome"]
                stats[outcome] += 1
        
        # Progress Bar
        if (i+1) % 100 == 0:
            elapsed = time.time() - start_time
            rate = (i+1) / elapsed
            print(f"Progress: {i+1}/{NUM_EPISODES} | Rate: {rate:.1f} eps/sec | "
                  f"Succ: {stats['SUCCESS']} ({stats['SUCCESS']/(i+1)*100:.1f}%) | "
                  f"Crash: {stats['CRASH_OBS']+stats['CRASH_WALL']}")

    # 5. Final Report
    print("\n" + "="*40)
    print("       FINAL BATCH RESULTS")
    print("="*40)
    print(f"Total Episodes: {NUM_EPISODES}")
    print(f"✅ Success Rate: {stats['SUCCESS']/NUM_EPISODES*100:.2f}%")
    print(f"💥 Obstacle Crashes: {stats['CRASH_OBS']/NUM_EPISODES*100:.2f}%")
    print(f"🧱 Wall Crashes:     {stats['CRASH_WALL']/NUM_EPISODES*100:.2f}%")
    print(f"⏳ Timeouts:         {stats['TIMEOUT']/NUM_EPISODES*100:.2f}%")
    print("="*40)
    
    # Save to CSV
    save_results("evaluate_1k.py", NUM_EPISODES, stats['SUCCESS'], stats['CRASH_OBS'], stats['CRASH_WALL'], stats['TIMEOUT'])
