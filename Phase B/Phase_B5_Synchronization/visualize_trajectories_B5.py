import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob

def visualize_episode(csv_path, output_dir):
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
        return

    # Filter: Only plot if 2 or more drones hit the 800-step timeout
    df['Step'] = pd.to_numeric(df['Step'], errors='coerce')
    agent_max_steps = df.groupby('Agent')['Step'].max()
    stuck_agents = agent_max_steps[agent_max_steps >= 799]
    
    if len(stuck_agents) < 2:
        return # Skip this episode

    if not os.path.exists(output_dir): 
        os.makedirs(output_dir)

    plt.figure(figsize=(10, 10))
    ax = plt.gca()

    # 1. Plot Obstacles (extracted from the first row of CSV)
    obs_str = df['Obstacles'].iloc[0]
    if isinstance(obs_str, str) and obs_str.strip():
        for obs_item in obs_str.split(';'):
            try:
                ox, oy, orad = map(float, obs_item.split(','))
                circle = plt.Circle((ox, oy), orad, color='gray', alpha=0.3, label='Obstacle' if 'Obstacle' not in [l.get_label() for l in ax.get_lines()] else "")
                ax.add_patch(circle)
            except: continue

    # 2. Plot Goal
    gx, gy = df['Goal_X'].iloc[0], df['Goal_Y'].iloc[0]
    plt.scatter(gx, gy, marker='*', s=300, color='gold', edgecolors='black', label='Goal', zorder=5)

    # 3. Plot Trajectories
    for agent in df['Agent'].unique():
        agent_df = df[df['Agent'] == agent]
        plt.plot(agent_df['X'], agent_df['Y'], alpha=0.7, linewidth=1.5, label=agent)
        # Mark start (circle) and end (X)
        plt.scatter(agent_df['X'].iloc[0], agent_df['Y'].iloc[0], marker='o', s=40, zorder=4)
        plt.scatter(agent_df['X'].iloc[-1], agent_df['Y'].iloc[-1], marker='x', s=60, zorder=4)

    plt.xlim(0, 20)
    plt.ylim(0, 20)
    ep_name = os.path.basename(csv_path).replace('.csv', '')
    plt.title(f"Diagnostic: {ep_name} ({len(stuck_agents)} Drones Stuck)")
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.xlabel("X (m)")
    plt.ylabel("Y (m)")
    
    out_path = os.path.join(output_dir, f"{ep_name}_viz.png")
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Generated failure diagnostic: {out_path}")

def process_all_results(base_results_dir="results", base_plots_dir="results"):
    csv_files = glob.glob(os.path.join(base_results_dir, "**", "*.csv"), recursive=True)
    print(f"Found {len(csv_files)} trajectory files. Scanning for multi-drone failures...")

    for csv_path in csv_files:
        # Determine output path: results/Fold_1/random/ep_1.csv -> plots/Fold_1/random/
        rel_path = os.path.relpath(os.path.dirname(csv_path), base_results_dir)
        output_dir = os.path.join(base_plots_dir, rel_path)
        visualize_episode(csv_path, output_dir)

if __name__ == "__main__":
    process_all_results()
