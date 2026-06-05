import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
import sys
import numpy as np
from stable_baselines3 import PPO
from swarm_env_stigmergy import SwarmStigmergyEnv
from tqdm import tqdm
import multiprocessing

def run_benchmark_chunk(args):
    model_path, num_episodes, worker_id = args
    env = SwarmStigmergyEnv(render_mode=None, target_density=0.35)
    # Force CPU to avoid multiprocessing CUDA issues
    model = PPO.load(model_path, device="cpu")
    
    stats = {"success": 0, "collision": 0, "timeout": 0, "total_breadcrumbs": 0, "total_steps": 0}
    
    # Only show tqdm on the first worker to avoid terminal clutter
    iterator = range(num_episodes)
    if worker_id == 0:
        iterator = tqdm(iterator, desc=f"Worker 0 (Running {num_episodes} eps)")
        
    for ep in iterator:
        obs, _ = env.reset(options={"spawn_mode": "clustered" if np.random.random() < 0.7 else "random"})
        ep_done = False
        while not ep_done:
            active_agents = list(obs.keys())
            if not active_agents:
                break
            obs_batch = np.array([obs[agent] for agent in active_agents])
            action_batch, _ = model.predict(obs_batch, deterministic=True)
            action_dict = {agent: action_batch[i] for i, agent in enumerate(active_agents)}
            obs, rews, terms, truncs, infos = env.step(action_dict)
            
            stats["total_breadcrumbs"] += len(env.breadcrumbs)
            stats["total_steps"] += 1
            
            if not env.agents:
                # Collect all causes before drones were removed
                causes = [info.get("cause") for info in infos.values() if "cause" in info]
                if "success" in causes: stats["success"] += 1
                elif "collision" in causes: stats["collision"] += 1
                else: stats["timeout"] += 1
                ep_done = True
    
    env.close()
    return stats

def test(model_path, mode="visual", cores=1):
    if mode == "visual":
        env = SwarmStigmergyEnv(render_mode="human", target_density=0.35)
        model = PPO.load(model_path)
        print("Launching Visual Mode... Close window to exit.")
        while True:
            obs, _ = env.reset(options={"spawn_mode": "clustered"})
            ep_done = False
            while not ep_done:
                active_agents = list(obs.keys())
                if not active_agents:
                    break
                obs_batch = np.array([obs[agent] for agent in active_agents])
                action_batch, _ = model.predict(obs_batch, deterministic=True)
                action_dict = {agent: action_batch[i] for i, agent in enumerate(active_agents)}
                obs, rews, terms, truncs, infos = env.step(action_dict)
                env.render()
                if not env.agents: ep_done = True
                
    elif mode == "benchmark":
        num_episodes = 1000
        print(f"Starting 1M-Step Rigorous Benchmark (1000 Episodes) on {cores} Core(s)...")
        
        stats = {"success": 0, "collision": 0, "timeout": 0, "total_breadcrumbs": 0, "total_steps": 0}
        
        if cores <= 1:
            # Sequential fallback
            res = run_benchmark_chunk((model_path, num_episodes, 0))
            for k in stats: stats[k] += res[k]
        else:
            # Parallel execution
            episodes_per_core = num_episodes // cores
            # Handle remainder if num_episodes is not perfectly divisible
            remainder = num_episodes % cores
            args_list = []
            for i in range(cores):
                eps = episodes_per_core + (1 if i < remainder else 0)
                args_list.append((model_path, eps, i))
                
            with multiprocessing.Pool(cores) as pool:
                results = pool.map(run_benchmark_chunk, args_list)
                
            for res in results:
                for k in stats:
                    stats[k] += res[k]
        
        # Final Report
        print("\n" + "="*40)
        print("PHASE B: STIGMERGY BENCHMARK RESULTS")
        print("="*40)
        print(f"Total Episodes:    {num_episodes}")
        print(f"Success Rate:      {(stats['success']/num_episodes)*100:.2f}%")
        print(f"Collision Rate:    {(stats['collision']/num_episodes)*100:.2f}%")
        print(f"Timeout Rate:      {(stats['timeout']/num_episodes)*100:.2f}%")
        print(f"Avg Breadcrumbs:   {stats['total_breadcrumbs']/stats['total_steps']:.2f} per step")
        print(f"Total Steps Eval:  {stats['total_steps']}")
        print("="*40)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_stigmergy.py <model_zip> <visual|benchmark> [cores]")
    else:
        m_path = sys.argv[1]
        t_mode = sys.argv[2]
        c_count = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        test(m_path, t_mode, c_count)
