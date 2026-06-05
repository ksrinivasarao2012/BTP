import os
import sys
import numpy as np
import json
import multiprocessing
from stable_baselines3 import PPO
from swarm_env_stigmergy import SwarmStigmergyEnv

# Force CPU to avoid CUDA over-allocation in multiprocessing
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"

def evaluate_config_worker(args):
    model_path, seed, num_episodes, target_density, config = args
    stagnation_limit = config["stagnation_limit"]
    breadcrumb_lifetime = config["breadcrumb_lifetime"]
    repulsion_scale = config["repulsion_scale"]
    sensing_radius = config["sensing_radius"]
    
    np.random.seed(seed)
    
    # Instantiate environment with customized Stigmergy params
    env = SwarmStigmergyEnv(
        target_density=target_density,
        stagnation_limit=stagnation_limit,
        breadcrumb_lifetime=breadcrumb_lifetime,
        repulsion_scale=repulsion_scale,
        sensing_radius=sensing_radius
    )
    
    model = PPO.load(model_path, device="cpu")
    stats = {"success": 0, "collision": 0, "timeout": 0}
    total_drones = 0
    
    for ep in range(num_episodes):
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
            
            if not env.agents:
                causes = [info.get("cause") for info in infos.values() if "cause" in info]
                for cause in causes:
                    if cause in stats:
                        stats[cause] += 1
                total_drones += len(causes)
                ep_done = True
                
    env.close()
    if total_drones == 0: total_drones = 1
    return stats, total_drones

def evaluate_config(model_path, config, target_density=0.35, num_episodes=20, cores=4):
    episodes_per_core = num_episodes // cores
    remainder = num_episodes % cores
    args_list = []
    
    for i in range(cores):
        eps = episodes_per_core + (1 if i < remainder else 0)
        seed = 1000 + i * 100
        args_list.append((model_path, seed, eps, target_density, config))
        
    with multiprocessing.Pool(cores) as pool:
        results = pool.map(evaluate_config_worker, args_list)
        
    combined_stats = {"success": 0, "collision": 0, "timeout": 0}
    combined_drones = 0
    for stats, total_drones in results:
        for k in combined_stats:
            combined_stats[k] += stats[k]
        combined_drones += total_drones
        
    success_rate = (combined_stats["success"] / combined_drones) * 100
    collision_rate = (combined_stats["collision"] / combined_drones) * 100
    timeout_rate = (combined_stats["timeout"] / combined_drones) * 100
    
    return success_rate, collision_rate, timeout_rate

def run_grid_sweep(model_path, cores=8):
    print("\n" + "="*70)
    print("STARTING STIGMERGY HYPERPARAMETER SWEEP")
    print("="*70)
    
    # Focused Grid for fast convergence and high statistical relevance
    stagnation_limits = [30, 40]
    repulsion_scales = [1.0, 2.0, 4.0]
    breadcrumb_lifetimes = [150, 250]
    sensing_radii = [4.0, 6.0]
    
    total_configs = len(stagnation_limits) * len(repulsion_scales) * len(breadcrumb_lifetimes) * len(sensing_radii)
    print(f"Evaluating {total_configs} unique configurations in parallel...")
    print(f"{'Config #':<10} | {'Stag.':<5} | {'Lifetime':<8} | {'Repuls.':<7} | {'Radius':<6} | {'Succ %':<7} | {'Coll %':<7} | {'Time %':<7}")
    print("-" * 80)
    
    best_config = None
    best_success = -1.0
    best_collision = 100.0
    history = []
    
    idx = 1
    for stag in stagnation_limits:
        for life in breadcrumb_lifetimes:
            for rep in repulsion_scales:
                for rad in sensing_radii:
                    config = {
                        "stagnation_limit": stag,
                        "breadcrumb_lifetime": life,
                        "repulsion_scale": rep,
                        "sensing_radius": rad
                    }
                    
                    # Evaluate config with 20 episodes (200 drone flights)
                    succ, coll, timeout = evaluate_config(model_path, config, target_density=0.35, num_episodes=20, cores=cores)
                    print(f"#{idx:<9} | {stag:<5} | {life:<8} | {rep:<7.1f} | {rad:<6.1f} | {succ:>6.2f}% | {coll:>6.2f}% | {timeout:>6.2f}%")
                    
                    history.append({
                        "id": idx,
                        "config": config,
                        "success": succ,
                        "collision": coll,
                        "timeout": timeout
                    })
                    
                    # Selection Criteria: Maximize Success, minimize Collision if tied
                    if (succ > best_success) or (abs(succ - best_success) < 1e-4 and coll < best_collision):
                        best_success = succ
                        best_collision = coll
                        best_config = config
                        
                    idx += 1
                    
    print("\n" + "="*70)
    print("SWEEP COMPLETED SUCCESSFULLY!")
    print("="*70)
    print("Optimal Stigmergy Configuration:")
    print(json.dumps(best_config, indent=4))
    print(f"Maximum success rate achieved during sweep: {best_success:.2f}% (Collision: {best_collision:.2f}%)")
    print("="*70)
    
    # Save optimal config to JSON
    with open("best_stigmergy_config.json", "w") as f:
        json.dump(best_config, f, indent=4)
    print("Optimal configurations saved to best_stigmergy_config.json!")

if __name__ == "__main__":
    default_model = "stigmergy_b5_model_35.zip"
    m_path = sys.argv[1] if len(sys.argv) > 1 else default_model
    c_count = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    
    if not os.path.exists(m_path) and not m_path.endswith('.zip'):
        m_path += '.zip'
        
    run_grid_sweep(m_path, cores=c_count)
