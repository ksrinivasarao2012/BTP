import numpy as np
from stable_baselines3 import PPO
import supersuit as ss
import os
import time
import sys

# Add paths for environment imports
sys.path.append(os.path.abspath("./Hardened_Baseline"))
sys.path.append(os.path.abspath("./Vanilla_Model"))

# Import both environments
try:
    from swarm_env_step_A import SwarmLidarEnv_StepA
    from swarm_env_vanilla import SwarmLidarEnv_Vanilla
except ImportError as e:
    print(f"Import Error: {e}")
    print("Make sure you are running this from the 'Phase A' directory.")
    sys.exit(1)

def run_fold(model, env_class, seed, num_episodes, mode="random"):
    np.random.seed(seed)
    env = env_class()
    env = ss.black_death_v3(env)
    env = ss.pettingzoo_env_to_vec_env_v1(env)
    env = ss.concat_vec_envs_v1(env, 1, num_cpus=1, base_class='stable_baselines3')
    
    stats = {"success": 0, "collision": 0, "timeout": 0}
    total_drones = num_episodes * 10
    
    for _ in range(num_episodes):
        options = {}
        if mode == "cluster":
            # --- DENSE STRESS CLUSTER (1.0m box - 'The Elevator') ---
            cx, cy = np.random.uniform(5.0, 15.0, 2)
            positions = []
            for _ in range(10):
                for _ in range(1000):
                    # 1.0m box (cx-0.5 to cx+0.5)
                    x, y = np.random.uniform(cx - 0.5, cx + 0.5), np.random.uniform(cy - 0.5, cy + 0.5)
                    if all(np.linalg.norm(np.array([x,y]) - np.array(p)) >= 0.26 for p in positions):
                        positions.append([x, y])
                        break
                else: positions.append([cx + np.random.uniform(-0.2,0.2), cy + np.random.uniform(-0.2,0.2)]) 
            
            # Goal at least 10m away
            gx, gy = np.random.uniform(2, 18, 2)
            while np.linalg.norm(np.array([gx, gy]) - np.array([cx, cy])) < 10.0:
                gx, gy = np.random.uniform(2, 18, 2)
                
            options = {"start_positions": positions, "goal": [gx, gy]}
        
        obs = env.reset(options=options)
        drones_done = 0
        while drones_done < 10:
            action, _ = model.predict(obs, deterministic=True)
            obs, rewards, dones, infos = env.step(action)
            for info in infos:
                if "cause" in info:
                    stats[info["cause"]] += 1
                    drones_done += 1
    
    env.close()
    return {k: (v / total_drones) * 100 for k, v in stats.items()}

def run_10_fold(model_path, env_class, label):
    print(f"\n--- Evaluating {label} ---", flush=True)
    if not os.path.exists(model_path + ".zip"):
        print(f"Error: Model not found at {model_path}.zip", flush=True)
        return None
    model = PPO.load(model_path)
    
    results = {"random": [], "cluster": []}
    seeds = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    
    for mode in ["random", "cluster"]:
        print(f"  Testing Mode: {mode.upper()}...", flush=True)
        for i, seed in enumerate(seeds):
            scores = run_fold(model, env_class, seed, 200, mode=mode)
            results[mode].append(scores)
            print(f"    Fold {i+1}/10: Succ: {scores['success']:.1f}% | Coll: {scores['collision']:.1f}% | Time: {scores['timeout']:.1f}%", flush=True)
            
    return results

if __name__ == "__main__":
    master_model = "./Hardened_Baseline/models/step_A_foundation_model"
    vanilla_model = "./Vanilla_Model/vanilla_fixed_physics_model"
    
    vanilla_res = run_10_fold(vanilla_model, SwarmLidarEnv_Vanilla, "Vanilla (Fixed Physics)")
    master_res = run_10_fold(master_model, SwarmLidarEnv_StepA, "Master (Hardened)")
    
    if vanilla_res and master_res:
        print("\n" + "="*85, flush=True)
        print("           FINAL K-FOLD COMPARISON (K=10, Drones=20,000)", flush=True)
        print("="*85, flush=True)
        print(f"{'Model':<25} | {'Metric':<10} | {'Random Spawn':<20} | {'Cluster Spawn':<20}", flush=True)
        print("-" * 85, flush=True)
        
        for label, res in [("Vanilla (Fixed Physics)", vanilla_res), ("Master (Hardened)", master_res)]:
            for metric in ["success", "collision", "timeout"]:
                r_scores = [f[metric] for f in res["random"]]
                c_scores = [f[metric] for f in res["cluster"]]
                r_mean, r_std = np.mean(r_scores), np.std(r_scores)
                c_mean, c_std = np.mean(c_scores), np.std(c_scores)
                
                m_label = "Success %" if metric == "success" else "Collision %" if metric == "collision" else "Timeout %"
                row_label = label if metric == "success" else ""
                print(f"{row_label:<25} | {m_label:<10} | {r_mean:>6.2f}% ±{r_std:>4.2f} | {c_mean:>6.2f}% ±{c_std:>4.2f}", flush=True)
            print("-" * 85, flush=True)
        print("="*85, flush=True)
