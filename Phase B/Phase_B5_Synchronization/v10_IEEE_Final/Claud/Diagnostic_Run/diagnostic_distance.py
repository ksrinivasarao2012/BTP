import numpy as np
import matplotlib.pyplot as plt
import os
import time
from swarm_env_step_B5_v20_sensing_ablation import SwarmLidarEnv_v20_SensingAblation

def run_diagnostic():
    print("Initializing environment...")
    env = SwarmLidarEnv_v20_SensingAblation(width=20.0, height=20.0, target_density=0.30)
    
    N_MAPS = 1000
    
    # We call reset once here to initialize properties like goal
    env.reset(seed=0)
    print("Environment Width :", env.WIDTH)
    print("Environment Height:", env.HEIGHT)
    print("Goal:", env.goal)
    
    all_distances = []
    map_means = []
    map_mins = []
    map_maxs = []
    
    print(f"Collecting distance metrics for {N_MAPS} maps...")
    
    t0 = time.time()
    for i in range(N_MAPS):
        # We pass seed=i so generation is deterministic if the env uses it,
        # but also to just fulfill the instruction loop
        env.reset(seed=i)
        
        goal = env.goal
        positions = env.positions
        
        dists = []
        for pos in positions:
            distance = np.linalg.norm(pos - goal)
            dists.append(distance)
            all_distances.append(distance)
            
        map_means.append(np.mean(dists))
        map_mins.append(np.min(dists))
        map_maxs.append(np.max(dists))
        
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1}/{N_MAPS} maps...")
            
    t1 = time.time()
    print(f"Collection complete in {t1 - t0:.2f} seconds.\n")
    
    all_distances = np.array(all_distances)
    map_means = np.array(map_means)
    map_mins = np.array(map_mins)
    map_maxs = np.array(map_maxs)
    
    # Complete Dataset Stats
    d_mean = np.mean(all_distances)
    d_std = np.std(all_distances)
    d_min = np.min(all_distances)
    d_max = np.max(all_distances)
    
    p05 = np.percentile(all_distances, 5)
    p10 = np.percentile(all_distances, 10)
    p25 = np.percentile(all_distances, 25)
    p50 = np.percentile(all_distances, 50)
    p75 = np.percentile(all_distances, 75)
    p90 = np.percentile(all_distances, 90)
    p95 = np.percentile(all_distances, 95)
    
    # Map Stats
    mean_map_means = np.mean(map_means)
    std_map_means = np.std(map_means)
    mean_map_mins = np.mean(map_mins)
    mean_map_maxs = np.mean(map_maxs)
    
    print("=================================================")
    print("START-GOAL DISTANCE ANALYSIS")
    print("=================================================")
    print(f"Maps Analyzed: {N_MAPS}")
    print(f"Total Distances: {len(all_distances)}\n")
    
    print(f"Mean: {d_mean:.2f}")
    print(f"Std:  {d_std:.2f}")
    print(f"Min:  {d_min:.2f}")
    print(f"Max:  {d_max:.2f}\n")
    
    print(f"P05:  {p05:.2f}")
    print(f"P10:  {p10:.2f}")
    print(f"P25:  {p25:.2f}")
    print(f"P50:  {p50:.2f}")
    print(f"P75:  {p75:.2f}")
    print(f"P90:  {p90:.2f}")
    print(f"P95:  {p95:.2f}\n")
    
    print(f"Mean(Map Means):    {mean_map_means:.2f}")
    print(f"Std(Map Means):     {std_map_means:.2f}\n")
    print(f"Mean(Map Minimums): {mean_map_mins:.2f}")
    print(f"Mean(Map Maximums): {mean_map_maxs:.2f}")
    print("=================================================")
    
    # Interpretation Section
    print("\n=================================================")
    print("INTERPRETATION SECTION")
    print("=================================================")
    print("1. Current hardcoded threshold: 8.0 m")
    print("2. Proposed scaled threshold:   0.40 * 40 = 16.0 m")
    
    print("\n3. Comparison:")
    print(f"   - P10  : {p10:.2f} m")
    print(f"   - P50  : {p50:.2f} m")
    print(f"   - Mean : {d_mean:.2f} m")
    print(f"   - P90  : {p90:.2f} m")
    
    print("\n4. Recommendation:")
    
    # Automatic logic for recommendation
    if 16.0 <= p10:
        print("   -> 16 m is heavily within the legacy distribution (<= P10).")
        print("   -> The proposed 16 m threshold is well-justified and safely scaled.")
    elif 16.0 > p50:
        print("   -> WARNING: 16 m is greater than the median (P50) of the legacy distribution.")
        print("   -> 16 m would significantly increase benchmark difficulty relative to the legacy distribution.")
    elif 16.0 > p10:
        print(f"   -> 16 m is higher than the P10 ({p10:.2f}m) but below the Median ({p50:.2f}m).")
        print("   -> 16 m may slightly increase minimum difficulty, cutting out easy spawns, but remains feasible.")
    
    print("=================================================\n")

    # Generate Histogram
    plt.figure(figsize=(10, 6))
    plt.hist(all_distances, bins=50, color='skyblue', edgecolor='black', alpha=0.7)
    
    # Add Markers
    plt.axvline(d_mean, color='red', linestyle='dashed', linewidth=2, label=f'Mean: {d_mean:.2f}m')
    plt.axvline(p50, color='green', linestyle='dashed', linewidth=2, label=f'Median: {p50:.2f}m')
    plt.axvline(p10, color='purple', linestyle='dotted', linewidth=2, label=f'P10: {p10:.2f}m')
    plt.axvline(p90, color='orange', linestyle='dotted', linewidth=2, label=f'P90: {p90:.2f}m')
    
    plt.title("Start-Goal Distance Distribution (Current Benchmark)")
    plt.xlabel("Distance to Goal (m)")
    plt.ylabel("Frequency")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    output_dir = os.path.dirname(os.path.abspath(__file__))
    plot_path = os.path.join(output_dir, "distance_distribution.png")
    plt.tight_layout()
    plt.savefig(plot_path, dpi=200)
    print(f"Saved histogram to: {plot_path}")

if __name__ == "__main__":
    run_diagnostic()
