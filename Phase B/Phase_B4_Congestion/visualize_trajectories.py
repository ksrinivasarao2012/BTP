import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os

def plot_swarm_trajectories(csv_path, title, save_filename):
    """
    Reads trajectory data and plots the paths of all 10 drones to visualize
    congestion yielding, dispersion, and goal-seeking behavior.
    """
    if not os.path.exists(csv_path):
        print(f"❌ Could not find {csv_path}")
        return

    # Load Data: Expected columns -> [Step, Agent_ID, X, Y]
    try:
        df = pd.read_csv(csv_path, names=["Step", "Agent", "X", "Y"], header=0)
    except Exception as e:
        print(f"❌ Error reading {csv_path}: {e}")
        return

    plt.figure(figsize=(8, 8))
    
    # Plot Environment Boundaries & Goal
    plt.xlim(0, 20)
    plt.ylim(0, 20)
    plt.gca().set_aspect('equal', adjustable='box')
    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel("X Coordinate (m)")
    plt.ylabel("Y Coordinate (m)")
    
    # Draw Goal Region (Green Circle)
    goal_circle = plt.Circle((18.0, 18.0), 0.75, color='limegreen', alpha=0.5, label="Goal")
    plt.gca().add_patch(goal_circle)

    # Define a color map for the 10 drones
    colors = plt.cm.tab10(np.linspace(0, 1, 10))

    # Plot each drone's trajectory
    agents = df["Agent"].unique()
    for idx, agent in enumerate(agents):
        agent_data = df[df["Agent"] == agent]
        plt.plot(agent_data["X"], agent_data["Y"], color=colors[idx % 10], alpha=0.7, linewidth=1.5)
        
        # Mark Start Position (Dot)
        if not agent_data.empty:
            plt.scatter(agent_data["X"].iloc[0], agent_data["Y"].iloc[0], color=colors[idx % 10], s=30, edgecolors='black', zorder=5)
            
            # Mark End Position (X)
            plt.scatter(agent_data["X"].iloc[-1], agent_data["Y"].iloc[-1], color='red', marker='x', s=50, zorder=5)

    # Aesthetic grid
    plt.grid(True, linestyle='--', alpha=0.5)
    
    # Save high-res for IEEE/Thesis formats
    plt.savefig(save_filename, dpi=300, bbox_inches='tight')
    print(f"✅ Saved plot to {save_filename}")
    plt.close()

if __name__ == "__main__":
    plot_swarm_trajectories("trajectories_fold_1_-_random.csv", "Phase B4: Random Spread Performance", "spaghetti_random_b4.png")
    plot_swarm_trajectories("trajectories_fold_1_-_clustered.csv", "Phase B4: Dense Cluster Performance", "spaghetti_clustered_b4.png")
    print("✅ Spaghetti Plot for Clustered category generated: spaghetti_clustered_b4.png")
