import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from swarm_env_benchmark import SwarmLidarEnv_v20_SensingAblation

def reactive_agent_action(idx, env):
    """Simple LiDAR-based reactive navigator."""
    pos = env.positions[idx]
    vel = env.velocities[idx]
    
    # 1. Goal seeking
    goal_vec = env.goal - pos
    dist_goal = np.linalg.norm(goal_vec)
    if dist_goal > 0:
        goal_dir = goal_vec / dist_goal
    else:
        goal_dir = np.zeros(2)
        
    v_goal = goal_dir * env.max_velocity
    
    # 2. Obstacle avoidance using LiDAR
    lidar = env._ray_cast_v20(idx)
    v_rep = np.zeros(2)
    threshold = 1.5
    
    for s in range(env.num_lidar_sectors):
        m_d = lidar[s*3]
        if m_d < threshold and m_d > 0:
            dx = lidar[s*3 + 1]
            dy = lidar[s*3 + 2]
            # repulsive force inversely proportional to distance
            force = (threshold - m_d) / m_d
            dir_vec = np.array([dx, dy]) / m_d
            v_rep -= force * dir_vec
            
    v_desired = v_goal + 2.0 * v_rep
    speed = np.linalg.norm(v_desired)
    if speed > env.max_velocity:
        v_desired = (v_desired / speed) * env.max_velocity
        
    # P-controller for acceleration (action is delta velocity)
    action = (v_desired - vel) * 0.5
    action = np.clip(action, -1.0, 1.0)
    return action

def evaluate_single_config_p2(args):
    w, h, density, d_min, num_episodes = args
    env = SwarmLidarEnv_v20_SensingAblation(target_density=density, width=w, height=h, d_min=d_min)
    
    successes = 0
    collisions = 0
    timeouts = 0
    evaluated_drones = 0
    total_episodes = 0
    episode_successes = 0
    ep_lengths = []
    times_to_goal = []
    escape_triggers = []
    
    for ep in range(num_episodes):
        try:
            obs, infos = env.reset()
        except RuntimeError:
            # Should be rare since these passed Phase 1
            continue
            
        total_episodes += 1
        evaluated_drones += env.n_drones
            
        active_agents = set(env.possible_agents)
        
        steps = 0
        agent_times = {a: 0 for a in env.possible_agents}
        agent_escapes = {a: 0 for a in env.possible_agents}
        agent_prev_escape_timer = {a: 0 for a in env.possible_agents}
        
        episode_successes_this_ep = 0
        
        while active_agents and steps < env.max_steps:
            actions = {}
            for agent in list(active_agents):
                idx = env.agent_name_mapping[agent]
                actions[agent] = reactive_agent_action(idx, env)
                
                # Track escape triggers based on environment's internal state
                curr_timer = env.escape_timer[agent]
                if curr_timer > 0 and agent_prev_escape_timer[agent] == 0:
                    agent_escapes[agent] += 1
                agent_prev_escape_timer[agent] = curr_timer
                
            obs, rewards, terms, truncs, infos = env.step(actions)
            steps += 1
            
            for agent in list(active_agents):
                agent_times[agent] += 1
                if terms[agent] or truncs[agent]:
                    active_agents.remove(agent)
                    cause = infos[agent].get('cause', 'unknown')
                    if cause == 'success':
                        successes += 1
                        episode_successes_this_ep += 1
                        times_to_goal.append(agent_times[agent] * env.dt)
                    elif cause == 'collision':
                        collisions += 1
                    else:
                        timeouts += 1
                    
                    ep_lengths.append(agent_times[agent])
                    escape_triggers.append(agent_escapes[agent])
                    
        if episode_successes_this_ep == env.n_drones:
            episode_successes += 1
                    
    drone_succ_rate = successes / evaluated_drones if evaluated_drones > 0 else 0
    ep_succ_rate = episode_successes / total_episodes if total_episodes > 0 else 0
    coll_rate = collisions / evaluated_drones if evaluated_drones > 0 else 0
    time_rate = timeouts / evaluated_drones if evaluated_drones > 0 else 0
    
    return {
        'Width': w, 'Height': h, 'Density': density, 'd_min': d_min,
        'Successes': successes,
        'Collisions': collisions,
        'Timeouts': timeouts,
        'Drone_Success_Rate': drone_succ_rate,
        'Episode_Success_Rate': ep_succ_rate,
        'Collision_Rate': coll_rate,
        'Timeout_Rate': time_rate,
        'Mean_Episode_Length': np.mean(ep_lengths) if ep_lengths else 0,
        'Mean_Time_To_Goal': np.mean(times_to_goal) if times_to_goal else 0,
        'Mean_Escape_Triggers': np.mean(escape_triggers) if escape_triggers else 0
    }

def run_phase2():
    try:
        survivors_df = pd.read_csv('results/phase1/phase1_survivors.csv')
    except FileNotFoundError:
        print("No survivors file found. Run Phase 1 first.")
        return
        
    num_episodes = 5
    os.makedirs('results/phase2', exist_ok=True)
    os.makedirs('plots/difficulty', exist_ok=True)
    
    tasks = []
    for _, row in survivors_df.iterrows():
        tasks.append((row['Width'], row['Height'], row['Density'], row['d_min'], num_episodes))
        
    print(f"Starting Phase 2 Evaluation of {len(tasks)} configurations using 8 cores...")
    
    from multiprocessing import Pool
    with Pool(processes=8) as pool:
        results = pool.map(evaluate_single_config_p2, tasks)
        
    df = pd.DataFrame(results)
    df.to_csv('results/phase2/phase2_results.csv', index=False)
    
    # Phase 3 Selection Criteria
    phase2_survivors = df[(df['Drone_Success_Rate'] >= 0.40) & (df['Drone_Success_Rate'] <= 0.80)]
    phase2_survivors.to_csv('results/phase2/phase2_survivors.csv', index=False)
    
    # Plotting
    for w in df['Width'].unique():
        sub = df[df['Width'] == w]
        if sub.empty: continue
        
        pivot_success = sub.pivot(index='Density', columns='d_min', values='Drone_Success_Rate')
        
        fig, ax = plt.subplots(figsize=(10,6))
        cax = ax.imshow(pivot_success, cmap='viridis', aspect='auto')
        fig.colorbar(cax)
        
        ax.set_xticks(np.arange(len(pivot_success.columns)))
        ax.set_yticks(np.arange(len(pivot_success.index)))
        ax.set_xticklabels(pivot_success.columns)
        ax.set_yticklabels(pivot_success.index)
        
        for i in range(len(pivot_success.index)):
            for j in range(len(pivot_success.columns)):
                val = pivot_success.iloc[i, j]
                # Light text for dark background, dark text for light
                color = "black" if (val if pd.notnull(val) else 0) > 0.5 else "white"
                ax.text(j, i, f"{val:.2f}" if pd.notnull(val) else "NaN", ha="center", va="center", color=color)
                
        ax.set_xlabel('d_min')
        ax.set_ylabel('Density')
        ax.set_title(f'Reactive Baseline Drone Success Rate (Size {w})')
        plt.tight_layout()
        plt.savefig(f'plots/difficulty/drone_success_rate_size_{w}.png')
        plt.close()

if __name__ == '__main__':
    run_phase2()
