import os
import torch
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecEnv
from swarm_env_step_B import SwarmLidarEnv_StepB
from multiprocessing import Process, Pipe

# ======================================================
#  PHASE B: APEX INDIVIDUAL TRAINING (SURGICAL MLP)
# ======================================================

def worker(remote, parent_remote, density, drone_radius, safety_radius):
    """Worker process for a single PettingZoo environment."""
    parent_remote.close()
    env = SwarmLidarEnv_StepB(render_mode=None, target_density=density, 
                             drone_radius=drone_radius, safety_radius=safety_radius)
    
    try:
        while True:
            cmd, data = remote.recv()
            if cmd == 'step':
                actions = {f"drone_{i}": data[i] for i in range(10)}
                obs_d, rew_d, term_d, trunc_d, info_d = env.step(actions)
                
                if not env.agents:
                    obs_d, info_d = env.reset()
                
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
    def __init__(self, n_workers, density, drone_radius=0.15, safety_radius=0.19):
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
            
        self.remotes[0].send(('get_spaces', None))
        obs_space, act_space = self.remotes[0].recv()
        super().__init__(n_workers * 10, obs_space, act_space)

    def step_async(self, actions):
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

    def get_attr(self, attr_name, indices=None): return [None] * self.num_envs
    def set_attr(self, attr_name, value, indices=None): pass
    def env_method(self, method_name, *method_args, indices=None, **method_kwargs): pass
    def env_is_wrapped(self, wrapper_class, indices=None): return [False] * self.num_envs

def train_apex():
    num_cpu = 12  
    print(f"🔥 Launching Single-Phase APEX Training (10M Steps)...")
    TRAIN_RADIUS = 0.19 
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device} | Training Radius: {TRAIN_RADIUS}m")

    # Load from the current foundation model to refine it
    model_path = "./models/step_B_foundation_model.zip"
    
    # 25% Density: High difficulty for 90%+ target
    env = MultiProcessPZEnv(n_workers=num_cpu, density=0.25, drone_radius=TRAIN_RADIUS)
    
    model = PPO.load(model_path, env=env, 
                    custom_objects={
                        "learning_rate": 3e-5, 
                        "n_steps": 1024, 
                        "batch_size": 256
                    })

    # Continuous 10M Step Training
    model.learn(total_timesteps=10_000_000, progress_bar=True)
    
    model.save("./models/apex_step_B_model")
    env.close()

    print(f"\n🎯 Apex Training Finished! Final Model: ./models/apex_step_B_model.zip")

if __name__ == "__main__":
    train_apex()
