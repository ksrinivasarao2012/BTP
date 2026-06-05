import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
import sys
import numpy as np
from stable_baselines3 import PPO
from swarm_env_stigmergy import SwarmStigmergyEnv
import multiprocessing
from tqdm import tqdm

def run_fold_worker(args):
    model_path, seed, num_episodes, mode, fold_idx = args
    
    # Optimization: Prevent internal PyTorch over-parallelization in subprocesses
    os.environ["OMP_NUM_THREADS"] = "1"
    
    # Set seed for reproducible folds
    np.random.seed(seed)
    
    env = SwarmStigmergyEnv(render_mode=None, target_density=0.35)
    # Force CPU to avoid CUDA multiprocessing locks
    model = PPO.load(model_path, device="cpu")
    
    stats = {"success": 0, "collision": 0, "timeout": 0}
    total_drones = 0
    
    # Show progress for the first fold to indicate activity
    iterator = range(num_episodes)
    if fold_idx == 0:
        iterator = tqdm(iterator, desc=f"Fold 1 Progress", leave=False)
        
    for ep in iterator:
        obs, _ = env.reset(options={"spawn_mode": mode})
        ep_done = False
        while not ep_done:
            active_agents = list(obs.keys())
            if not active_agents:
                break
            obs_batch = np.array([obs[agent] for agent in active_agents])
            action_batch, _ = model.predict(obs_batch, deterministic=True)
            action_dict = {agent: action_batch[i] for i, agent in enumerate(active_agents)}
            obs, rews, terms, truncs, infos = env.step(action_dict)
            
            if not env.agents:
                causes = [info.get("cause") for info in infos.values() if "cause" in info]
                for cause in causes:
                    if cause in stats:
                        stats[cause] += 1
                total_drones += len(causes)
                ep_done = True
                
    env.close()
    
    if total_drones == 0: total_drones = 1
    scores = {k: (v / total_drones) * 100 for k, v in stats.items()}
    return fold_idx, scores

def run_10_fold(model_path, label, cores=10):
    print(f"\n--- Evaluating Phase B: {label} ---", flush=True)
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}", flush=True)
        return None
        
    results = {"random": [], "cluster": []}
    seeds = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    num_episodes = 200 # 200 episodes per fold (2000 drones) matches Phase A
    
    for mode in ["random", "clustered"]:
        print(f"  Testing Mode: {mode.upper()}...", flush=True)
        
        args_list = [(model_path, seeds[i], num_episodes, mode, i) for i in range(10)]
        mode_scores = [None] * 10
        
        # Parallelize the 10 folds across the CPU cores
        with multiprocessing.Pool(cores) as pool:
            for fold_idx, scores in pool.imap_unordered(run_fold_worker, args_list):
                mode_scores[fold_idx] = scores
                print(f"    Fold {fold_idx+1}/10: Succ: {scores['success']:.1f}% | Coll: {scores['collision']:.1f}% | Time: {scores['timeout']:.1f}%", flush=True)
                
        # Store for final report
        store_mode = "cluster" if mode == "clustered" else mode
        results[store_mode] = mode_scores
            
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python k_fold_stigmergy.py <model_zip> [cores]")
        sys.exit(1)
        
    m_path = sys.argv[1]
    c_count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    res = run_10_fold(m_path, "Stigmergy Model", cores=c_count)
    
    if res:
        print("\n" + "="*85, flush=True)
        print("           PHASE B: K-FOLD COMPARISON (K=10, 200 Eps/Fold)", flush=True)
        print("="*85, flush=True)
        print(f"{'Model':<25} | {'Metric':<10} | {'Random Spawn':<20} | {'Cluster Spawn':<20}", flush=True)
        print("-" * 85, flush=True)
        
        for metric in ["success", "collision", "timeout"]:
            r_scores = [f[metric] for f in res["random"]]
            c_scores = [f[metric] for f in res["cluster"]]
            r_mean, r_std = np.mean(r_scores), np.std(r_scores)
            c_mean, c_std = np.mean(c_scores), np.std(c_scores)
            
            m_label = "Success %" if metric == "success" else "Collision %" if metric == "collision" else "Timeout %"
            row_label = "Stigmergy" if metric == "success" else ""
            print(f"{row_label:<25} | {m_label:<10} | {r_mean:>6.2f}% ±{r_std:>4.2f} | {c_mean:>6.2f}% ±{c_std:>4.2f}", flush=True)
        print("="*85, flush=True)
