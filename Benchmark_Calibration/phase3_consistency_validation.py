import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from swarm_env_benchmark import SwarmLidarEnv_v20_SensingAblation

def reactive_agent_action(idx, env):
    """Simple LiDAR-based reactive navigator."""
    pos = env.positions[idx]
    vel = env.velocities[idx]
    
    goal_vec = env.goal - pos
    dist_goal = np.linalg.norm(goal_vec)
    if dist_goal > 0:
        goal_dir = goal_vec / dist_goal
    else:
        goal_dir = np.zeros(2)
        
    v_goal = goal_dir * env.max_velocity
    
    lidar = env._ray_cast_v20(idx)
    v_rep = np.zeros(2)
    threshold = 1.5
    
    for s in range(env.num_lidar_sectors):
        m_d = lidar[s*3]
        if 0 < m_d < threshold:
            dx = lidar[s*3 + 1]
            dy = lidar[s*3 + 2]
            force = (threshold - m_d) / m_d
            v_rep -= force * (np.array([dx, dy]) / m_d)
            
    v_desired = v_goal + 2.0 * v_rep
    speed = np.linalg.norm(v_desired)
    if speed > env.max_velocity:
        v_desired = (v_desired / speed) * env.max_velocity
        
    action = (v_desired - vel) * 0.5
    return np.clip(action, -1.0, 1.0)

def evaluate_single_config_p3(args):
    w, h, density, d_min, num_episodes = args
    env = SwarmLidarEnv_v20_SensingAblation(target_density=density, width=w, height=h, d_min=d_min)
    
    ep_drone_success_rates = []
    ep_episode_successes = []
    evaluated_episodes = 0
    
    for ep in range(num_episodes):
        try:
            env.reset()
        except RuntimeError:
            continue
            
        evaluated_episodes += 1
        active_agents = set(env.possible_agents)
        steps = 0
        successes = 0
        
        while active_agents and steps < env.max_steps:
            actions = {a: reactive_agent_action(env.agent_name_mapping[a], env) for a in active_agents}
            _, _, terms, truncs, infos = env.step(actions)
            steps += 1
            
            for agent in list(active_agents):
                if terms[agent] or truncs[agent]:
                    active_agents.remove(agent)
                    if infos[agent].get('cause') == 'success':
                        successes += 1
                        
        ep_drone_success_rates.append(successes / env.n_drones)
        ep_episode_successes.append(1.0 if successes == env.n_drones else 0.0)
        
    mean_drone_sr = np.mean(ep_drone_success_rates) if ep_drone_success_rates else 0
    std_drone_sr = np.std(ep_drone_success_rates) if ep_drone_success_rates else 0
    p10 = np.percentile(ep_drone_success_rates, 10) if ep_drone_success_rates else 0
    p50 = np.percentile(ep_drone_success_rates, 50) if ep_drone_success_rates else 0
    p90 = np.percentile(ep_drone_success_rates, 90) if ep_drone_success_rates else 0
    spread = p90 - p10
    mean_ep_sr = np.mean(ep_episode_successes) if ep_episode_successes else 0
    
    return {
        'Width': w, 'Height': h, 'Density': density, 'd_min': d_min,
        'Episodes_Run': evaluated_episodes,
        'Mean_Drone_Success_Rate': mean_drone_sr,
        'Std_Drone_Success_Rate': std_drone_sr,
        'P10_Drone_Success': p10,
        'P50_Drone_Success': p50,
        'P90_Drone_Success': p90,
        'Difficulty_Spread': spread,
        'Mean_Episode_Success_Rate': mean_ep_sr
    }

def run_phase3():
    try:
        phase2_df = pd.read_csv('results/phase2/phase2_survivors.csv')
    except FileNotFoundError:
        print("No Phase 2 survivors found. Run Phase 2 first.")
        return
        
    num_episodes = 5
    os.makedirs('results/phase3', exist_ok=True)
    os.makedirs('plots/consistency', exist_ok=True)
    os.makedirs('reports', exist_ok=True)
    
    tasks = []
    for _, row in phase2_df.iterrows():
        tasks.append((row['Width'], row['Height'], row['Density'], row['d_min'], num_episodes))
        
    print(f"Starting Phase 3 Evaluation of {len(tasks)} configurations using 8 cores...")
    
    from multiprocessing import Pool
    with Pool(processes=8) as pool:
        results = pool.map(evaluate_single_config_p3, tasks)
        
    phase3_df = pd.DataFrame(results)
    phase3_df.to_csv('results/phase3/phase3_results.csv', index=False)
    
    # Plotting Consistency
    for w in phase3_df['Width'].unique():
        sub = phase3_df[phase3_df['Width'] == w]
        if sub.empty: continue
        
        pivot_spread = sub.pivot(index='Density', columns='d_min', values='Difficulty_Spread')
        
        fig, ax = plt.subplots(figsize=(10,6))
        cax = ax.imshow(pivot_spread, cmap='magma_r', aspect='auto')
        fig.colorbar(cax)
        
        ax.set_xticks(np.arange(len(pivot_spread.columns)))
        ax.set_yticks(np.arange(len(pivot_spread.index)))
        ax.set_xticklabels(pivot_spread.columns)
        ax.set_yticklabels(pivot_spread.index)
        
        for i in range(len(pivot_spread.index)):
            for j in range(len(pivot_spread.columns)):
                val = pivot_spread.iloc[i, j]
                color = "white" if (val if pd.notnull(val) else 0) < 0.2 else "black"
                ax.text(j, i, f"{val:.2f}" if pd.notnull(val) else "NaN", ha="center", va="center", color=color)
                
        ax.set_xlabel('d_min')
        ax.set_ylabel('Density')
        ax.set_title(f'Difficulty Spread (P90-P10) for Size {w}')
        plt.tight_layout()
        plt.savefig(f'plots/consistency/spread_size_{w}.png')
        plt.close()

if __name__ == '__main__':
    run_phase3()
