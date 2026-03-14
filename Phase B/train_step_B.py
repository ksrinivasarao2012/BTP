import os
import torch
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecEnv
from swarm_env_step_B import SwarmLidarEnv_StepB
from multiprocessing import Process, Pipe

def worker(remote, parent_remote, density, drone_radius, safety_radius):
    """Worker process for a single PettingZoo environment."""
    parent_remote.close()
    env = SwarmLidarEnv_StepB(render_mode=None, target_density=density, 
                             drone_radius=drone_radius, safety_radius=safety_radius)
    
    try:
        while True:
            cmd, data = remote.recv()
            if cmd == 'step':
                # Map NumPy actions back to PettingZoo dict
                actions = {f"drone_{i}": data[i] for i in range(10)}
                obs_d, rew_d, term_d, trunc_d, info_d = env.step(actions)
                
                # Auto-reset if all agents finished
                if not env.agents:
                    obs_d, info_d = env.reset()
                
                # Format response as NumPy arrays (10 agents per worker)
                obs = np.array([obs_d.get(f"drone_{i}", np.zeros(env.observation_space("drone_0").shape)) for i in range(10)], dtype=np.float32)
                rews = np.array([rew_d.get(f"drone_{i}", 0.0) for i in range(10)], dtype=np.float32)
                dones = np.array([term_d.get(f"drone_{i}", True) or trunc_d.get(f"drone_{i}", True) for i in range(10)], dtype=bool)
                infos = [info_d.get(f"drone_{i}", {}) for i in range(10)]
                
                remote.send((obs, rews, dones, infos))
            elif cmd == 'reset':
                obs_d, info_d = env.reset()
                obs = np.array([obs_d.get(f"drone_{i}", np.zeros(env.observation_space("drone_0").shape)) for i in range(10)], dtype=np.float32)
                remote.send(obs)
            elif cmd == 'close':
                env.close()
                remote.close()
                break
            elif cmd == 'get_spaces':
                remote.send((env.observation_space("drone_0"), env.action_space("drone_0")))
    except Exception as e:
        print(f"Worker Error: {e}")
        remote.close()

class MultiProcessPZEnv(VecEnv):
    """Stable Baselines 3 compatible VecEnv that runs multiple PettingZoo envs in parallel."""
    def __init__(self, n_workers, density, drone_radius=0.15, safety_radius=0.25):
        self.waiting = False
        self.closed = False
        self.n_workers = n_workers
        
        self.remotes, self.work_remotes = zip(*[Pipe() for _ in range(n_workers)])
        self.ps = [Process(target=worker, args=(work_remote, remote, density, drone_radius, safety_radius), daemon=True)
                   for (work_remote, remote) in zip(self.work_remotes, self.remotes)]
        
        for p in self.ps:
            p.start()
            
        for remote in self.work_remotes:
            remote.close()
            
        # Get spaces from the first worker
        self.remotes[0].send(('get_spaces', None))
        obs_space, act_space = self.remotes[0].recv()
        
        # SB3 expected: Total envs = workers * agents_per_worker
        super().__init__(n_workers * 10, obs_space, act_space)

    def step_async(self, actions):
        # Actions is [N_total, Action_Dim]
        for i in range(self.n_workers):
            worker_actions = actions[i*10:(i+1)*10]
            self.remotes[i].send(('step', worker_actions))
        self.waiting = True

    def step_wait(self):
        results = [remote.recv() for remote in self.remotes]
        self.waiting = False
        obs, rews, dones, infos = zip(*results)
        return np.concatenate(obs), np.concatenate(rews), np.concatenate(dones), [i for sub in infos for i in sub]

    def reset(self):
        for remote in self.remotes:
            remote.send(('reset', None))
        results = [remote.recv() for remote in self.remotes]
        return np.concatenate(results)

    def close(self):
        if self.closed: return
        for remote in self.remotes:
            remote.send(('close', None))
        for p in self.ps:
            p.join()
        self.closed = True

    def get_attr(self, attr_name, indices=None):
        return [None] * self.num_envs
    def set_attr(self, attr_name, value, indices=None):
        pass
    def env_method(self, method_name, *method_args, indices=None, **method_kwargs):
        pass
    def env_is_wrapped(self, wrapper_class, indices=None):
        return [False] * self.num_envs

def train_step_B():
    num_cpu = 12  
    print(f"🚀 Initializing {num_cpu}-Core Bravery & Flow Tuning...")
    # Training with THIN RADIUS (0.18m) for maximum corridor flow
    TRAIN_RADIUS = 0.18 
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device} | Training Radius: {TRAIN_RADIUS}m")

    os.makedirs("./models", exist_ok=True)

    # IEEE-Standard Policy Architecture (Expanded for complex coordination)
    policy_kwargs = dict(
        net_arch=dict(pi=[256, 256, 128], vf=[256, 256, 128])
    )

    # =========================================================
    #  PHASE B1: Sparse (5%) - Radius Inflated
    # =========================================================
    print("\n--- PHASE B1 (Sparse 5%) ---")
    env_b1 = MultiProcessPZEnv(n_workers=num_cpu, density=0.05, drone_radius=TRAIN_RADIUS)
    
    # Reset B1 to scratch training due to major sensor & architecture overhaul
    model = PPO("MlpPolicy", env_b1, 
                learning_rate=3e-4, 
                n_steps=512, 
                batch_size=256, 
                policy_kwargs=policy_kwargs,
                verbose=1)

    model.learn(total_timesteps=2_000_000, progress_bar=True)
    model.save("./models/industrial_B1")
    env_b1.close()

    # =========================================================
    #  PHASE B2: Moderate (10%) - Radius Inflated
    # =========================================================
    print("\n--- PHASE B2 (Moderate 10%) ---")
    env_b2 = MultiProcessPZEnv(n_workers=num_cpu, density=0.10, drone_radius=TRAIN_RADIUS)
    model = PPO.load("./models/industrial_B1.zip", env=env_b2, custom_objects={"learning_rate": 1e-4, "n_steps": 512})
    model.learn(total_timesteps=2_000_000, reset_num_timesteps=False, progress_bar=True)
    model.save("./models/industrial_B2")
    env_b2.close()

    # =========================================================
    #  PHASE B3: Dense (20%) - Radius Inflated
    # =========================================================
    print("\n--- PHASE B3 (Dense 20%) ---")
    env_b3 = MultiProcessPZEnv(n_workers=num_cpu, density=0.20, drone_radius=TRAIN_RADIUS)
    model = PPO.load("./models/industrial_B2.zip", env=env_b3, custom_objects={"learning_rate": 5e-5, "n_steps": 512})
    model.learn(total_timesteps=2_000_000, reset_num_timesteps=False, progress_bar=True)
    model.save("./models/industrial_B3")
    env_b3.close()

    # =========================================================
    #  PHASE B4: Hyper-Dense (30%) - Radius Inflated
    # =========================================================
    print("\n--- PHASE B4 (Hyper-Dense 30%) ---")
    env_b4 = MultiProcessPZEnv(n_workers=num_cpu, density=0.30, drone_radius=TRAIN_RADIUS)
    model = PPO.load("./models/industrial_B3.zip", env=env_b4, custom_objects={"learning_rate": 1e-5, "n_steps": 1024})
    model.learn(total_timesteps=2_000_000, reset_num_timesteps=False, progress_bar=True)
    model.save("./models/step_B_foundation_model")
    env_b4.close()

    print(f"\n🎯 Industrial Grade Training Finished! Final Model: ./models/step_B_foundation_model.zip")

if __name__ == "__main__":
    train_step_B()