import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
import warnings
warnings.filterwarnings("ignore")  # Suppress all warnings globally in the parent process

import sys
import time
import numpy as np
import pandas as pd
from stable_baselines3 import PPO
import multiprocessing
from datetime import datetime

def run_episode_batch_worker(args):
    import warnings
    warnings.filterwarnings("ignore")  # Suppress all warnings globally in child processes
    
    model_path, seed, num_episodes, mode, fold_idx, start_ep_idx, main_results_dir = args
    
    # Prevent internal PyTorch over-parallelization in subprocesses
    os.environ["OMP_NUM_THREADS"] = "1"
    import torch
    torch.set_num_threads(1)
    
    # Set seed for reproducible episodes
    np.random.seed(seed)
    
    # Load model on CPU dynamically mapping the policy class
    import sys
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
        
    from train_step_B5_sync_v15_master import MAPPO_Policy_v15
    from train_step_B5_sync import MAPPO_Policy_B5
    
    is_v15 = "v15" in os.path.basename(model_path)
    policy_cls = MAPPO_Policy_v15 if is_v15 else MAPPO_Policy_B5
    
    model = PPO.load(model_path, custom_objects={"policy_class": policy_cls}, device="cpu")
    obs_dim = model.observation_space.shape[0]

    # Select correct environment dynamically based on the model's observation dimension
    target_density = float(os.environ.get("OBSTACLE_DENSITY", "0.35"))
    if obs_dim == 732:
        from swarm_env_step_B5_v15_master import SwarmLidarEnv_v15_Final
        env = SwarmLidarEnv_v15_Final(render_mode=None, target_density=target_density)
    elif obs_dim == 650:
        from swarm_env_step_B5 import SwarmLidarEnv_StepB5
        env = SwarmLidarEnv_StepB5(render_mode=None, target_density=target_density)
    else:
        raise ValueError(f"Unsupported model observation dimension: {obs_dim}. Must be 650 (Sync) or 732 (Trust).")

    # Set up fold directory structures (clustered spawns are saved in 'dense' folder to match Phase B5 standards)
    fold_dir = os.path.join(main_results_dir, f"Fold_{fold_idx}")
    sub_folder = "random" if mode == "random" else "dense"
    output_dir = os.path.join(fold_dir, sub_folder)
    os.makedirs(output_dir, exist_ok=True)

    stats = {"success": 0, "collision": 0, "timeout": 0}
    total_drones = 0
    total_steps = 0
    
    for ep in range(num_episodes):
        current_seed = seed + ep
        obs_dict, _ = env.reset(seed=current_seed, options={"spawn_mode": mode})
        ep_done = False
        
        ep_successes = 0
        ep_collisions = 0
        tallied_agents = set()
        num_agents = len(env.possible_agents)
        step_count = 0
        
        current_goal_x, current_goal_y = env.goal[0], env.goal[1]
        current_obstacles_str = ";".join([f"{o[0]},{o[1]},{o[2]}" for o in env.obstacles])
        
        # Trajectory file setup
        ep_num = start_ep_idx + ep + 1
        csv_path = os.path.join(output_dir, f"ep_{ep_num}.csv")
        f_csv = open(csv_path, 'w')
        f_csv.write("Step,Agent,X,Y,Goal_X,Goal_Y,Obstacles\n")
        
        while not ep_done:
            active_agents = list(obs_dict.keys())
            if not active_agents:
                break
            
            obs_batch = np.array([obs_dict[agent] for agent in active_agents])
            action_batch, _ = model.predict(obs_batch, deterministic=True)
            action_dict = {agent: action_batch[i] for i, agent in enumerate(active_agents)}
            
            # Log position of each active agent before stepping the environment
            for agent in active_agents:
                idx = env.agent_name_mapping[agent]
                pos = env.positions[idx]
                f_csv.write(f"{step_count},{agent},{pos[0]:.3f},{pos[1]:.3f},{current_goal_x:.3f},{current_goal_y:.3f},\"{current_obstacles_str}\"\n")
                
            obs_dict, rews, terms, truncs, infos = env.step(action_dict)
            step_count += 1
            
            # Tally agent terminations/truncations step-by-step to prevent PettingZoo tracking bias
            for agent in env.possible_agents:
                if agent not in tallied_agents and agent in infos and "cause" in infos[agent]:
                    cause = infos[agent]["cause"]
                    if cause == "success":
                        ep_successes += 1
                        tallied_agents.add(agent)
                    elif cause == "collision":
                        ep_collisions += 1
                        tallied_agents.add(agent)
            
            if not env.agents:
                ep_done = True
                
        f_csv.close()
        
        ep_timeouts = num_agents - ep_successes - ep_collisions
        stats["success"] += ep_successes
        stats["collision"] += ep_collisions
        stats["timeout"] += ep_timeouts
        total_drones += num_agents
        total_steps += step_count
        
    env.close()
    return stats, total_drones, total_steps

def save_evaluation_plot(df, timestamp, results_dir):
    try:
        import matplotlib.pyplot as plt
        
        # Set clean, professional typography and size
        plt.rcParams.update({
            'font.size': 11,
            'font.family': 'sans-serif',
            'axes.edgecolor': '#cccccc',
            'axes.linewidth': 0.8
        })
        
        # Extract means and standard deviations
        metrics = ["Success_Rate", "Collision_Rate", "Timeout_Rate"]
        categories = ["Success", "Collision", "Timeout"]
        
        r_means = [df[df["Mode"] == "random"][m].mean() for m in metrics]
        r_stds = [df[df["Mode"] == "random"][m].std() for m in metrics]
        
        c_means = [df[df["Mode"] == "clustered"][m].mean() for m in metrics]
        c_stds = [df[df["Mode"] == "clustered"][m].std() for m in metrics]
        
        # Fill NaN stds with 0 if running very few folds
        r_stds = [0.0 if np.isnan(s) else s for s in r_stds]
        c_stds = [0.0 if np.isnan(s) else s for s in c_stds]
        
        x = np.arange(len(categories))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(9, 6.5), dpi=300)
        
        # Harmonious modern colors (Sleek Teal for Random, Vibrant Coral for Clustered)
        rects1 = ax.bar(x - width/2, r_means, width, yerr=r_stds, label='Random Spawn',
                        color='#008080', edgecolor='none', alpha=0.9, capsize=5,
                        error_kw=dict(ecolor='#333333', lw=1.5, capthick=1.5))
        
        rects2 = ax.bar(x + width/2, c_means, width, yerr=c_stds, label='Cluster Spawn',
                        color='#FF6F61', edgecolor='none', alpha=0.9, capsize=5,
                        error_kw=dict(ecolor='#333333', lw=1.5, capthick=1.5))
        
        # Add labels, title and custom x-axis tick labels
        ax.set_ylabel('Percentage (%)', fontsize=12, fontweight='bold', labelpad=10)
        ax.set_title('Decentralized Swarm Navigation Performance: Phase B Master Model', 
                     fontsize=13, fontweight='bold', pad=20, color='#111111')
        ax.set_xticks(x)
        ax.set_xticklabels(categories, fontsize=11, fontweight='bold')
        ax.set_ylim(0, 105)
        
        # Sleek legend and grid
        ax.legend(frameon=True, facecolor='white', edgecolor='none', shadow=True, loc='upper right')
        ax.grid(axis='y', linestyle='--', alpha=0.5, color='#dddddd')
        
        # Attach a text label display
        def autolabel(rects):
            for rect in rects:
                height = rect.get_height()
                ax.annotate(f'{height:.1f}%',
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 3),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=9.5, fontweight='bold')
                            
        autolabel(rects1)
        autolabel(rects2)
        
        # Despine top and right axes for modern minimalist look
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        plt.tight_layout()
        
        png_filename = f"master_B5_evaluation_comparison_{timestamp}.png"
        png_path = os.path.join(results_dir, png_filename)
        plt.savefig(png_path, bbox_inches='tight')
        plt.close()
        print(f"✅ Comparison plot successfully saved to: {png_path}", flush=True)
    except Exception as e:
        print(f"⚠️ Could not generate plot automatically: {e}", flush=True)

def generate_diagnostic_plots(main_results_dir):
    try:
        import matplotlib.pyplot as plt
        import glob
        
        csv_files = glob.glob(os.path.join(main_results_dir, "**", "*.csv"), recursive=True)
        print(f"\n🔍 Scanning {len(csv_files)} parallel trajectory logs for multi-drone failures...", flush=True)
        
        diagnostics_count = 0
        for csv_path in csv_files:
            try:
                df = pd.read_csv(csv_path)
                df['Step'] = pd.to_numeric(df['Step'], errors='coerce')
                agent_max_steps = df.groupby('Agent')['Step'].max()
                stuck_agents = agent_max_steps[agent_max_steps >= 799]
                
                # Generate diagnostic plot if 2 or more drones got stuck (timed out at 800 steps)
                if len(stuck_agents) >= 2:
                    plt.figure(figsize=(10, 10))
                    ax = plt.gca()
                    
                    # 1. Obstacles
                    obs_str = df['Obstacles'].iloc[0]
                    if isinstance(obs_str, str) and obs_str.strip():
                        for obs_item in obs_str.split(';'):
                            try:
                                ox, oy, orad = map(float, obs_item.split(','))
                                circle = plt.Circle((ox, oy), orad, color='gray', alpha=0.3)
                                ax.add_patch(circle)
                            except: continue
                            
                    # 2. Goal
                    gx, gy = df['Goal_X'].iloc[0], df['Goal_Y'].iloc[0]
                    plt.scatter(gx, gy, marker='*', s=300, color='gold', edgecolors='black', label='Goal', zorder=5)
                    
                    # 3. Trajectories
                    for agent in df['Agent'].unique():
                        agent_df = df[df['Agent'] == agent]
                        plt.plot(agent_df['X'], agent_df['Y'], alpha=0.7, linewidth=1.5, label=agent)
                        plt.scatter(agent_df['X'].iloc[0], agent_df['Y'].iloc[0], marker='o', s=40, zorder=4)
                        plt.scatter(agent_df['X'].iloc[-1], agent_df['Y'].iloc[-1], marker='x', s=60, zorder=4)
                        
                    plt.xlim(0, 20)
                    plt.ylim(0, 20)
                    ep_name = os.path.splitext(os.path.basename(csv_path))[0]
                    plt.title(f"Diagnostic: {ep_name} ({len(stuck_agents)} Drones Stuck)", fontweight='bold')
                    plt.grid(True, linestyle='--', alpha=0.5)
                    plt.xlabel("X (m)", fontweight='bold')
                    plt.ylabel("Y (m)", fontweight='bold')
                    
                    out_path = os.path.join(os.path.dirname(csv_path), f"{ep_name}_viz.png")
                    plt.savefig(out_path, dpi=150, bbox_inches='tight')
                    plt.close()
                    diagnostics_count += 1
            except Exception as e:
                continue
                
        if diagnostics_count > 0:
            print(f"✅ Generated {diagnostics_count} failure diagnostic plots in results folder!", flush=True)
        else:
            print(f"🎉 No multi-drone failure scenarios detected (Perfect navigation bounds)!", flush=True)
    except Exception as e:
        print(f"⚠️ Could not generate diagnostic plots: {e}", flush=True)

def run_k_fold_master(model_path, cores=10, total_episodes=200, num_folds=10):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = "results/v8"
    os.makedirs(results_dir, exist_ok=True)
    
    # Save the obstacle density preference file (always 0.35 density)
    with open(os.path.join(results_dir, "obstacle_density.txt"), "w") as f:
        f.write("0.35")
        
    model_base = os.path.splitext(os.path.basename(model_path))[0]
    main_results_dir = os.path.join(results_dir, model_base)
    os.makedirs(main_results_dir, exist_ok=True)
    
    log_filename = f"master_B5_evaluation_log_{timestamp}.txt"
    log_path = os.path.join(main_results_dir, log_filename)
    
    class Logger(object):
        def __init__(self, filename, original_stdout):
            self.terminal = original_stdout
            self.log = open(filename, "w", encoding="utf-8")
        def write(self, message):
            self.terminal.write(message)
            self.log.write(message)
            self.log.flush()
        def flush(self):
            self.terminal.flush()
            self.log.flush()
        def close(self):
            self.log.close()

    original_stdout = sys.stdout
    logger_instance = Logger(log_path, original_stdout)
    sys.stdout = logger_instance

    print(f"\n==================================================", flush=True)
    print(f"🤖 K-FOLD VALIDATION LAUNCHED (K={num_folds}, {cores} Cores Parallelized)", flush=True)
    print(f"   Episodes per fold: {total_episodes} (Total: {total_episodes * num_folds} drone flights total)", flush=True)
    print(f"   Dynamic Hardware Acceleration: Parallelized episodes within folds", flush=True)
    print(f"==================================================\n", flush=True)

    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}", flush=True)
        sys.stdout = original_stdout
        logger_instance.close()
        return None
        
    results_data = []
    
    # Calculate episodes per core (minimum 1)
    episodes_per_worker = max(1, total_episodes // cores)
    actual_cores = min(cores, total_episodes)
    
    for fold_idx in range(num_folds):
        print(f"\n=======================================================", flush=True)
        print(f"  --- FOLD {fold_idx+1}/{num_folds} ---", flush=True)
        print(f"=======================================================\n", flush=True)
        
        for mode in ["random", "clustered"]:
            print(f"[{mode.upper()} Spawn] Evaluating {total_episodes} episodes across {actual_cores} cores...", flush=True)
            
            # Record start time for this fold
            start_time = time.time()
            
            base_seed = (fold_idx + 1) * 1000
            
            # Map episodes across active worker cores with tracking variables
            args_list = []
            remaining_eps = total_episodes
            current_start_ep = 0
            
            for w in range(actual_cores):
                # Ensure even distribution if not perfectly divisible
                eps_this_worker = remaining_eps if w == (actual_cores - 1) else episodes_per_worker
                worker_seed = base_seed + w * episodes_per_worker
                
                args_list.append((
                    model_path, 
                    worker_seed, 
                    eps_this_worker, 
                    mode, 
                    fold_idx + 1, 
                    current_start_ep, 
                    main_results_dir
                ))
                
                remaining_eps -= eps_this_worker
                current_start_ep += eps_this_worker
            
            fold_stats = {"success": 0, "collision": 0, "timeout": 0}
            fold_drones = 0
            fold_steps = 0
            
            with multiprocessing.Pool(actual_cores) as pool:
                results = pool.map(run_episode_batch_worker, args_list)
                
            for stats, total_drones, total_steps in results:
                for k in fold_stats.keys():
                    fold_stats[k] += stats[k]
                fold_drones += total_drones
                fold_steps += total_steps
                
            elapsed_time = time.time() - start_time
            avg_steps = fold_steps / total_episodes if total_episodes > 0 else 0
            
            success_rate = (fold_stats["success"] / fold_drones) * 100
            collision_rate = (fold_stats["collision"] / fold_drones) * 100
            timeout_rate = (fold_stats["timeout"] / fold_drones) * 100
            
            print(f"\n==========================================", flush=True)
            print(f"  RESULTS: Fold {fold_idx+1} - {mode.capitalize()}", flush=True)
            print(f"==========================================", flush=True)
            print(f"Total Episodes Run: {total_episodes}", flush=True)
            print(f"Total Drones Evaluated: {fold_drones}", flush=True)
            print(f"Time Taken: {elapsed_time:.2f} seconds", flush=True)
            print(f"Average Steps/Episode: {avg_steps:.1f}", flush=True)
            print(f"------------------------------------------", flush=True)
            print(f"🎯 Success Rate:   {success_rate:>6.2f}% ({fold_stats['success']})", flush=True)
            print(f"💥 Collision Rate: {collision_rate:>6.2f}% ({fold_stats['collision']})", flush=True)
            print(f"⏳ Timeout Rate:   {timeout_rate:>6.2f}% ({fold_stats['timeout']})", flush=True)
            print(f"==========================================\n", flush=True)
            
            results_data.append({
                "Mode": mode,
                "Fold": fold_idx + 1,
                "Success_Rate": success_rate,
                "Collision_Rate": collision_rate,
                "Timeout_Rate": timeout_rate
            })
            
    # Save results to CSV directly in results/v8/
    df = pd.DataFrame(results_data)
    csv_filename = f"master_B5_evaluation_results_{timestamp}.csv"
    csv_path = os.path.join(main_results_dir, csv_filename)
    df.to_csv(csv_path, index=False)
    print(f"✅ Results successfully saved to: {csv_path}", flush=True)
    
    # Generate and save comparison plot inside results/v8/model_base/
    save_evaluation_plot(df, timestamp, main_results_dir)
    
    # Scan logs and generate failure diagnostics plots automatically for all folds
    generate_diagnostic_plots(main_results_dir)
    
    # Calculate and print final K-fold summary comparison table
    print("\n" + "="*85, flush=True)
    print(f"           PHASE B MASTER: K-FOLD COMPARISON (K={num_folds}, {total_episodes} Eps/Fold)", flush=True)
    print("="*85, flush=True)
    print(f"{'Metric':<25} | {'Random Spawn':<25} | {'Cluster Spawn':<25}", flush=True)
    print("-" * 85, flush=True)
    
    for metric in ["Success_Rate", "Collision_Rate", "Timeout_Rate"]:
        r_scores = df[df["Mode"] == "random"][metric]
        c_scores = df[df["Mode"] == "clustered"][metric]
        
        r_mean, r_std = r_scores.mean(), r_scores.std()
        c_mean, c_std = c_scores.mean(), c_scores.std()
        
        emoji = "🎯" if "Success" in metric else ("💥" if "Collision" in metric else "⏳")
        m_label = f"{emoji} {metric.replace('_', ' ')}"
        
        print(f"{m_label:<25} | {r_mean:>6.2f}% ± {r_std:>4.2f}            | {c_mean:>6.2f}% ± {c_std:>4.2f}", flush=True)
        
    print("="*85, flush=True)

    # Restore standard stdout and close log file
    sys.stdout = original_stdout
    logger_instance.close()
    print(f"✅ Terminal log successfully saved to: {log_path}", flush=True)

if __name__ == "__main__":
    default_model = "../models/apex_ultra_sync_v8_final.zip"
    
    m_path = sys.argv[1] if len(sys.argv) > 1 else default_model
    c_count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    eps_count = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    folds_count = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    
    if not os.path.exists(m_path) and not m_path.endswith('.zip'):
        m_path += '.zip'
        
    run_k_fold_master(m_path, cores=c_count, total_episodes=eps_count, num_folds=folds_count)
