import os
import sys
import time
import multiprocessing as mp
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import heapq
from scipy.ndimage import distance_transform_edt

from swarm_env_benchmark import SwarmLidarEnv_v20_SensingAblation



def evaluate_config(args):
    cfg_start = time.time()
    w, h, density, d_min, num_maps, raster_res = args
    env = SwarmLidarEnv_v20_SensingAblation(target_density=density, width=w, height=h, d_min=d_min)
    
    success_count = 0
    total_attempts = 0
    
    gen_times = []
    path_lengths = []
    tortuosities = []
    corridor_widths = []
    actual_d_mins = []
    actual_densities = []
    
    reachable_drones = 0
    total_drones = 0
    
    for i in range(num_maps):
        start_time = time.time()
        total_attempts += 1
        try:
            env.reset()
            gen_times.append(time.time() - start_time)
            success_count += 1
            
            # Verify actual d_min
            min_dist_to_goal = min([np.linalg.norm(pos - env.goal) for pos in env.positions])
            actual_d_mins.append(min_dist_to_goal)
            actual_densities.append(env.actual_density)
            
            # Use pre-built occupancy grid
            occupied_grid = env.occupied_grid
            
            rw = int(env.WIDTH / raster_res)
            rh = int(env.HEIGHT / raster_res)
                    
            dist_transform = distance_transform_edt(~occupied_grid) * raster_res
            inflated_occupied = dist_transform < 0.2  # True = obstacle or within 0.2m clearance
            
            gx = min(int(env.goal[0]/raster_res), rw-1)
            gy = min(int(env.goal[1]/raster_res), rh-1)

            # Build cost grid: inf where inflated_occupied, else 1.0
            cost = np.where(inflated_occupied, np.inf, 1.0)

            # Dijkstra from goal cell outward
            dist_map = np.full(inflated_occupied.shape, np.inf, dtype=np.float64)
            prev_map = np.full(inflated_occupied.shape + (2,), -1, dtype=np.int32)
            dist_map[gx, gy] = 0.0
            heap = [(0.0, gx, gy)]

            moves = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
            move_costs = [1.0, 1.0, 1.0, 1.0, 1.4142, 1.4142, 1.4142, 1.4142]

            while heap:
                d, x, y = heapq.heappop(heap)
                if d > dist_map[x, y]:
                    continue
                for (dx, dy), dc in zip(moves, move_costs):
                    nx, ny = x+dx, y+dy
                    if 0 <= nx < inflated_occupied.shape[0] and 0 <= ny < inflated_occupied.shape[1]:
                        if inflated_occupied[nx, ny]:
                            continue
                        # prevent diagonal corner cuts
                        if dx != 0 and dy != 0:
                            if 0 <= x+dx < inflated_occupied.shape[0] and 0 <= y+dy < inflated_occupied.shape[1]:
                                if inflated_occupied[x+dx, y] and inflated_occupied[x, y+dy]:
                                    continue
                        nd = d + dc
                        if nd < dist_map[nx, ny]:
                            dist_map[nx, ny] = nd
                            prev_map[nx, ny] = [x, y]
                            heapq.heappush(heap, (nd, nx, ny))

            # Now read off each drone using dist_map and prev_map
            for pos in env.positions:
                total_drones += 1
                px = min(int(pos[0]/raster_res), rw-1)
                py = min(int(pos[1]/raster_res), rh-1)

                if np.isinf(dist_map[px, py]):
                    continue  # unreachable

                reachable_drones += 1
                p_len = dist_map[px, py] * raster_res
                euc_dist = np.linalg.norm(pos - env.goal)
                path_lengths.append(p_len)
                tortuosities.append(p_len / (euc_dist + 1e-6))

                # Trace path back to collect corridor widths
                cx_t, cy_t = px, py
                min_cw_val = np.inf
                visited_path = set()
                while not (cx_t == gx and cy_t == gy):
                    if cx_t < 0 or cy_t < 0 or cx_t >= rw or cy_t >= rh:
                        break
                    if (cx_t, cy_t) in visited_path:
                        break
                    visited_path.add((cx_t, cy_t))
                    
                    min_cw_val = min(min_cw_val, dist_transform[cx_t, cy_t])
                    prev = prev_map[cx_t, cy_t]
                    cx_t, cy_t = int(prev[0]), int(prev[1])
                if not np.isinf(min_cw_val) and (cx_t == gx and cy_t == gy):
                    corridor_widths.append(min_cw_val * 2.0)
                    
        except RuntimeError:
            pass
            
        # Early termination for unfeasible configurations
        if total_attempts >= 10 and success_count == 0:
            break
        # Safety valve: abort early if success rate is too low to ever meet the 95% survival threshold
        if total_attempts >= 20 and (success_count / total_attempts) < 0.75:
            break
            
    total_generation_attempts = (
        success_count
        + env.total_failed_density
        + env.total_failed_connectivity
    )
    map_acceptance_rate = (
        success_count / total_generation_attempts
        if total_generation_attempts > 0 else 0.0
    )
    density_failure_rate = (
        env.total_failed_density / total_generation_attempts
        if total_generation_attempts > 0 else 0.0
    )
    connectivity_failure_rate = (
        env.total_failed_connectivity / total_generation_attempts
        if total_generation_attempts > 0 else 0.0
    )
    
    reachability_rate = reachable_drones / total_drones if total_drones > 0 else 0.0
    
    mean_gen_time = np.mean(gen_times) if gen_times else float('nan')
    mean_path_len = np.mean(path_lengths) if path_lengths else float('nan')
    mean_tort = np.mean(tortuosities) if tortuosities else float('nan')
    
    mean_cw = np.mean(corridor_widths) if corridor_widths else float('nan')
    min_cw = np.min(corridor_widths) if corridor_widths else float('nan')
    p10_cw = np.percentile(corridor_widths, 10) if corridor_widths else float('nan')
    
    mean_actual_d_min = np.mean(actual_d_mins) if actual_d_mins else float('nan')
    std_actual_d_min = np.std(actual_d_mins) if actual_d_mins else float('nan')
    
    mean_actual_density = np.mean(actual_densities) if actual_densities else float('nan')
    std_actual_density = np.std(actual_densities) if actual_densities else float('nan')
    
    p10_tort = np.percentile(tortuosities, 10) if tortuosities else float('nan')
    p50_tort = np.percentile(tortuosities, 50) if tortuosities else float('nan')
    p90_tort = np.percentile(tortuosities, 90) if tortuosities else float('nan')
    
    p10_path = np.percentile(path_lengths, 10) if path_lengths else float('nan')
    p50_path = np.percentile(path_lengths, 50) if path_lengths else float('nan')
    p90_path = np.percentile(path_lengths, 90) if path_lengths else float('nan')
    
    path_found_count = reachable_drones
    path_failure_count = total_drones - reachable_drones
    
    print(
        f"Finished {w}x{h} "
        f"density={density} "
        f"d_min={d_min} "
        f"in {time.time() - cfg_start:.1f}s"
    )
    return {
        'Width': w,
        'Height': h,
        'Density': density,
        'Mean_Actual_Density': mean_actual_density,
        'Std_Actual_Density': std_actual_density,
        'd_min': d_min,
        'Mean_Actual_d_min': mean_actual_d_min,
        'Std_Actual_d_min': std_actual_d_min,
        'Maps_Accepted': success_count,
        'Maps_Rejected': env.total_rejected_maps,
        'Map_Acceptance_Rate': map_acceptance_rate,
        'Density_Failure_Rate': density_failure_rate,
        'Connectivity_Failure_Rate': connectivity_failure_rate,
        'Gen_Time': mean_gen_time,
        'Reachability_Rate': reachability_rate,
        'Path_Found_Count': path_found_count,
        'Path_Failure_Count': path_failure_count,
        'Mean_Path_Length': mean_path_len,
        'P10_Path_Length': p10_path,
        'P50_Path_Length': p50_path,
        'P90_Path_Length': p90_path,
        'Mean_Tortuosity': mean_tort,
        'Mean_Stretch_Ratio': mean_tort,
        'P10_Tortuosity': p10_tort,
        'P50_Tortuosity': p50_tort,
        'P90_Tortuosity': p90_tort,
        'Min_Corridor_Width': min_cw,
        'Mean_Corridor_Width': mean_cw,
        'P10_Corridor_Width': p10_cw
    }


def run_phase1():
    arena_sizes = [(20,20), (30,30), (40,40)]
    densities = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
    d_min_candidates = {
        (20,20): [4, 6, 8, 10, 12],
        (30,30): [6, 9, 12, 15, 18],
        (40,40): [8, 12, 16, 20, 24]
    }
    
    num_maps = 150
    if len(sys.argv) > 1:
        try:
            num_maps = int(sys.argv[1])
        except ValueError:
            pass
    raster_res = 0.1
    
    os.makedirs('results/phase1', exist_ok=True)
    os.makedirs('plots/feasibility', exist_ok=True)
    os.makedirs('reports', exist_ok=True)
    
    results = []
    completed_keys = set()
    csv_path = 'results/phase1/phase1_results.csv'
    if os.path.exists(csv_path):
        try:
            df_existing = pd.read_csv(csv_path)
            for _, row in df_existing.iterrows():
                completed_keys.add((int(row['Width']), int(row['Height']), float(row['Density']), int(row['d_min'])))
                results.append(row.to_dict())
            print(f"Loaded {len(completed_keys)} previously completed configurations from {csv_path}.")
        except Exception as e:
            print(f"Error reading existing CSV: {e}")

    tasks = []
    for size in arena_sizes:
        w, h = size
        for density in densities:
            for d_min in d_min_candidates[size]:
                if size == (20, 20) and density == 0.40:
                    continue
                if (w, h, density, d_min) not in completed_keys:
                    tasks.append((w, h, density, d_min, num_maps, raster_res))
                
    NUM_WORKERS = 10
    print(f"Starting multiprocessing pool with {NUM_WORKERS} workers for {len(tasks)} remaining configurations...")
    
    if tasks:
        with mp.Pool(NUM_WORKERS) as pool:
            completed = len(completed_keys)
            total = len(completed_keys) + len(tasks)
            for res in pool.imap_unordered(evaluate_config, tasks):
                results.append(res)
                completed += 1
                print(f"[{completed}/{total}] Configurations complete.")
                # Save incrementally after each task completes
                df_temp = pd.DataFrame(results)
                df_temp.to_csv('results/phase1/phase1_results.csv', index=False)
            
    df = pd.DataFrame(results)
    df = df[~((df['Width'] == 20) & (df['Height'] == 20) & (df['Density'] == 0.40))]
    df.to_csv('results/phase1/phase1_results.csv', index=False)
    
    # Selection criteria
    passed_df = df[(df['Map_Acceptance_Rate'] >= 0.95) & (df['P10_Corridor_Width'] >= 0.4) & (df['Reachability_Rate'] >= 0.99)]
    passed_df.to_csv('results/phase1/phase1_survivors.csv', index=False)
    
    # Plotting
    for size in arena_sizes:
        sub_df = df[(df['Width'] == size[0]) & (df['Height'] == size[1])]
        if sub_df.empty: continue
        
        pivot_success = sub_df.pivot(index='Density', columns='d_min', values='Map_Acceptance_Rate')
        
        fig, ax = plt.subplots(figsize=(10, 6))
        cax = ax.imshow(pivot_success, cmap='RdYlGn', aspect='auto')
        fig.colorbar(cax)
        ax.set_xticks(np.arange(len(pivot_success.columns)))
        ax.set_yticks(np.arange(len(pivot_success.index)))
        ax.set_xticklabels(pivot_success.columns)
        ax.set_yticklabels(pivot_success.index)
        for i in range(len(pivot_success.index)):
            for j in range(len(pivot_success.columns)):
                val = pivot_success.iloc[i, j]
                ax.text(j, i, f"{val:.2f}" if pd.notnull(val) else "NaN", ha="center", va="center", color="black")
        ax.set_xlabel('d_min')
        ax.set_ylabel('Density')
        ax.set_title(f'Map Gen Success Rate for Size {size}')
        plt.tight_layout()
        plt.savefig(f'plots/feasibility/success_rate_{size[0]}x{size[1]}.png')
        plt.close()
        
        pivot_tort = sub_df.pivot(index='Density', columns='d_min', values='Mean_Tortuosity')
        
        fig, ax = plt.subplots(figsize=(10, 6))
        cax = ax.imshow(pivot_tort, cmap='coolwarm', aspect='auto')
        fig.colorbar(cax)
        ax.set_xticks(np.arange(len(pivot_tort.columns)))
        ax.set_yticks(np.arange(len(pivot_tort.index)))
        ax.set_xticklabels(pivot_tort.columns)
        ax.set_yticklabels(pivot_tort.index)
        for i in range(len(pivot_tort.index)):
            for j in range(len(pivot_tort.columns)):
                val = pivot_tort.iloc[i, j]
                ax.text(j, i, f"{val:.2f}" if pd.notnull(val) else "NaN", ha="center", va="center", color="black")
        ax.set_xlabel('d_min')
        ax.set_ylabel('Density')
        ax.set_title(f'Mean Tortuosity for Size {size}')
        plt.tight_layout()
        plt.savefig(f'plots/feasibility/tortuosity_{size[0]}x{size[1]}.png')
        plt.close()

    # Generate summary report
    with open('reports/phase1_summary.txt', 'w') as f:
        f.write("Phase 1 Geometric Feasibility Summary\n")
        f.write("="*40 + "\n")
        f.write(f"Total configurations tested: {len(df)}\n")
        f.write(f"Maps evaluated per configuration (num_maps): {num_maps}\n\n")
        f.write("Selection Criteria:\n")
        f.write("  - Map Acceptance Rate >= 95%\n")
        f.write("  - P10 Corridor Width >= 0.4 m\n")
        f.write("  - Reachability Rate >= 99%\n\n")
        f.write(f"Configurations Passed: {len(passed_df)}\n\n")
        f.write("Passed Configurations:\n")
        f.write(passed_df[['Width', 'Height', 'Density', 'd_min', 'Mean_Tortuosity']].to_string(index=False))
        
if __name__ == '__main__':
    run_phase1()