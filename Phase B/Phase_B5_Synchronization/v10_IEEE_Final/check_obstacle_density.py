import random
import math
import numpy as np
import matplotlib.pyplot as plt
import multiprocessing
from tqdm import tqdm
from itertools import repeat
import csv
import heapq

# -------------------------------
# PARAMETERS
# -------------------------------
SEED = 42
WIDTH = 20.0
HEIGHT = 20.0
DRONE_RADIUS = 0.15
GRID_RES = 0.10  # Optimized grid resolution (10cm)

DENSITIES = [0.10, 0.15, 0.20, 0.25, 0.28, 0.30, 0.32, 0.35, 0.40, 0.45, 0.50]
TRIALS = 300  # Optimized trials per density to maintain tight 95% CI but run extremely fast

# -------------------------------
# OBSTACLE GENERATION
# -------------------------------
def generate_obstacles(start, goal, density):
    target_area = WIDTH * HEIGHT * density
    obstacles = []

    raster_res = 0.05
    rw = int(WIDTH / raster_res)
    rh = int(HEIGHT / raster_res)
    occupied = np.zeros((rw, rh), dtype=bool)
    current_area = 0.0

    for _ in range(2000):
        if current_area >= target_area:
            break

        ch = random.random()
        if ch < 0.2:
            r = random.uniform(1.5, 2.5)
        elif ch < 0.6:
            r = random.uniform(0.6, 1.4)
        else:
            r = random.uniform(0.2, 0.5)

        cx = random.uniform(r / 2.0, WIDTH - r / 2.0)
        cy = random.uniform(r / 2.0, HEIGHT - r / 2.0)

        if np.linalg.norm(np.array([cx, cy]) - goal) <= r + 2.0:
            continue
        if np.linalg.norm(np.array([cx, cy]) - start) <= r + 1.65:
            continue

        xmin = max(0, int((cx - r) / raster_res))
        xmax = min(rw, int((cx + r) / raster_res) + 1)
        ymin = max(0, int((cy - r) / raster_res))
        ymax = min(rh, int((cy + r) / raster_res) + 1)

        lx = np.arange(xmin, xmax) * raster_res + raster_res / 2
        ly = np.arange(ymin, ymax) * raster_res + raster_res / 2
        LX, LY = np.meshgrid(lx, ly, indexing='ij')

        new_cells = (LX - cx)**2 + (LY - cy)**2 <= r**2
        newly_covered = np.sum(new_cells & ~occupied[xmin:xmax, ymin:ymax])
        if newly_covered == 0:
            continue

        current_area += newly_covered * raster_res**2
        occupied[xmin:xmax, ymin:ymax] |= new_cells
        obstacles.append((cx, cy, r))

    achieved_rho = current_area / (WIDTH * HEIGHT)
    return obstacles, achieved_rho


# -------------------------------
# HELPERS
# -------------------------------
def to_cell(p):
    gs = int(np.ceil(WIDTH / GRID_RES))
    return (np.clip(int(p[0] / GRID_RES), 0, gs - 1), np.clip(int(p[1] / GRID_RES), 0, gs - 1))

# -------------------------------
# DIJKSTRA SHORTEST PATH
# -------------------------------
def is_map_solvable(obstacles, start, goal):
    gs = int(np.ceil(WIDTH / GRID_RES))
    grid = np.ones((gs, gs), dtype=bool)
    clearance = DRONE_RADIUS + 0.05 

    for ox, oy, orad in obstacles:
        inflated_r = orad + clearance 
        xmin = max(0, int((ox - inflated_r) / GRID_RES))
        xmax = min(gs, int((ox + inflated_r) / GRID_RES) + 1)
        ymin = max(0, int((oy - inflated_r) / GRID_RES))
        ymax = min(gs, int((oy + inflated_r) / GRID_RES) + 1)

        gx_slice = np.arange(xmin, xmax) * GRID_RES + GRID_RES / 2
        gy_slice = np.arange(ymin, ymax) * GRID_RES + GRID_RES / 2
        GX, GY = np.meshgrid(gx_slice, gy_slice, indexing='ij')
        
        dist_sq = (GX - ox)**2 + (GY - oy)**2
        mask = dist_sq < inflated_r**2
        grid[xmin:xmax, ymin:ymax] &= (~mask)

    # [100% SURE-SHOT FIX] Inflate grid boundaries matching environmental wall collision buffer (0.05m)
    wall_boundary_cells = int(np.ceil(0.05 / GRID_RES))
    grid[:wall_boundary_cells, :] = False
    grid[-wall_boundary_cells:, :] = False
    grid[:, :wall_boundary_cells] = False
    grid[:, -wall_boundary_cells:] = False

    sc, gc = to_cell(start), to_cell(goal)
    if not grid[sc] or not grid[gc]: return None

    # Dijkstra setup
    pq = [(0.0, sc)]
    dist = {sc: 0.0}
    
    # Pre-compute diagonal cost for speed
    sqrt2 = math.sqrt(2)
    
    # Format: (dx, dy, cost, is_diagonal)
    moves = [
        (-1, 0, GRID_RES, False), (1, 0, GRID_RES, False), 
        (0, -1, GRID_RES, False), (0, 1, GRID_RES, False),
        (-1, -1, GRID_RES * sqrt2, True), (-1, 1, GRID_RES * sqrt2, True),
        (1, -1, GRID_RES * sqrt2, True), (1, 1, GRID_RES * sqrt2, True)
    ]

    while pq:
        d, curr = heapq.heappop(pq)
        if curr == gc:
            return d
        
        if d > dist.get(curr, float('inf')):
            continue
            
        x, y = curr
        for dx, dy, cost, is_diagonal in moves:
            nx, ny = x + dx, y + dy
            if 0 <= nx < gs and 0 <= ny < gs and grid[nx, ny]:
                # [CORNER-CUTTING FIX] For diagonal moves, ensure both cardinal neighbors are open!
                if is_diagonal:
                    if not (grid[x + dx, y] and grid[x, y + dy]):
                        continue  # Blocked by corner collision
                
                new_dist = d + cost
                if new_dist < dist.get((nx, ny), float('inf')):
                    dist[(nx, ny)] = new_dist
                    heapq.heappush(pq, (new_dist, (nx, ny)))
                    
    return None


# -------------------------------
# TRIAL WORKER
# -------------------------------
def run_single_trial(args):
    rho, seed = args
    random.seed(seed)
    np.random.seed(seed)
    
    # Sampling logic
    def sample_safe():
        goal = np.array([random.uniform(2.0, 18.0), random.uniform(2.0, 18.0)])
        for _ in range(200):
            start = np.array([random.uniform(2.0, 18.0), random.uniform(2.0, 18.0)])
            if np.linalg.norm(start - goal) > 7.0:
                return start, goal
        start = np.clip(np.array([WIDTH, HEIGHT]) - goal, 2.0, 18.0)
        return start, goal

    start, goal = sample_safe()
    obstacles, achieved_rho = generate_obstacles(start, goal, rho)
    
    path_length = is_map_solvable(obstacles, start, goal)
    is_solvable = 1 if path_length is not None else 0
    
    tortuosity = None
    if path_length is not None:
        sc, gc = to_cell(start), to_cell(goal)
        c_start = np.array([sc[0]*GRID_RES + GRID_RES/2, sc[1]*GRID_RES + GRID_RES/2])
        c_goal = np.array([gc[0]*GRID_RES + GRID_RES/2, gc[1]*GRID_RES + GRID_RES/2])
        grid_euclid = np.linalg.norm(c_start - c_goal)
        
        assert path_length >= grid_euclid - 1e-7, f"Dijkstra error: {path_length} < {grid_euclid}"
        
        euclid_dist = np.linalg.norm(start - goal)
        tortuosity = path_length / euclid_dist

    return is_solvable, achieved_rho, path_length, tortuosity


# -------------------------------
# RUN EXPERIMENT
# -------------------------------
def run_analysis():
    print(f"\nSTARTING SCIENTIFIC HARDENED ANALYSIS (REPRODUCIBLE SEED={SEED})")
    
    final_rates = []
    final_rhos = []
    final_cis = []
    final_path_lengths = []
    final_tortuosities = []

    with multiprocessing.Pool(processes=10) as pool:
        for idx, rho in enumerate(DENSITIES):
            trial_seeds = [SEED + (idx * TRIALS) + i for i in range(TRIALS)]
            worker_args = zip(repeat(rho), trial_seeds)

            results = list(tqdm(
                pool.imap_unordered(run_single_trial, worker_args), 
                total=TRIALS, 
                leave=False, 
                desc=f"Density {rho:.2f}"
            ))

            n_solvable = sum(r[0] for r in results)
            s_rate = n_solvable / TRIALS
            avg_rho = np.mean([r[1] for r in results])
            
            valid_lengths = [r[2] for r in results if r[2] is not None]
            valid_torts = [r[3] for r in results if r[3] is not None]
            
            mean_path = np.mean(valid_lengths) if valid_lengths else None
            mean_tort = np.mean(valid_torts) if valid_torts else None
            
            se = math.sqrt(max(s_rate * (1 - s_rate) / TRIALS, 1e-12))
            
            final_rates.append(s_rate)
            final_rhos.append(avg_rho)
            final_cis.append(1.96 * se)
            final_path_lengths.append(mean_path)
            final_tortuosities.append(mean_tort)

            path_str = f"{mean_path:.2f}m" if mean_path is not None else "N/A"
            print(f"Target {rho:.2f} (Actual {avg_rho:.3f}) | Solvability: {s_rate:.3f} | Avg SPL: {path_str}")

    return final_rates, final_rhos, final_cis, final_path_lengths, final_tortuosities


# -------------------------------
# SAVE & PLOT
# -------------------------------
def save_results(rates, actual_rhos, cis, paths, torts):
    with open("solvability_hardened_results.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["TargetDensity", "ActualDensity", "SolvabilityRate", "CI_95", "AvgPathLength", "AvgTortuosity"])
        for i in range(len(DENSITIES)):
            writer.writerow([
                DENSITIES[i], 
                actual_rhos[i], 
                rates[i], 
                cis[i], 
                paths[i] if paths[i] is not None else "", 
                torts[i] if torts[i] is not None else ""
            ])
    print(f"\nResults saved to solvability_hardened_results.csv")

def plot_results(rates, actual_rhos, cis, paths, torts):
    fig, ax1 = plt.subplots(figsize=(10, 6))

    ax1.errorbar(actual_rhos, rates, yerr=cis, fmt='-o', color='#0D47A1', 
                 capsize=5, label="Solvability (95% CI)")
    ax1.axhline(y=0.8, color='red', linestyle='--', alpha=0.5, label="80% Crossover")
    ax1.set_xlabel(r"Actual Achieved Density ($\rho$)", fontsize=12)
    ax1.set_ylabel("Solvability Probability $P(S)$", color='#0D47A1', fontsize=12)
    ax1.tick_params(axis='y', labelcolor='#0D47A1')

    ax2 = ax1.twinx()
    paths_plot = [p if p is not None else np.nan for p in paths]
    ax2.plot(actual_rhos, paths_plot, '--s', color='#D81B60', alpha=0.7, label="Avg Path Length")
    ax2.set_ylabel("Average Shortest Path Length (m)", color='#D81B60', fontsize=12)
    ax2.tick_params(axis='y', labelcolor='#D81B60')
    
    plt.title("Hardened Swarm Solvability & Path Metrics\n(No Corner-Cutting | Actual Density Tracking)", fontsize=14)
    ax1.grid(True, alpha=0.3)
    
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
    
    plt.tight_layout()
    plt.savefig("solvability_hardened_final.png", dpi=300)
    print("Plot successfully saved to solvability_hardened_final.png")
    # Show plot only if in an interactive session
    import sys
    if sys.flags.interactive or hasattr(sys, 'ps1'):
        plt.show()
    else:
        print("Running in headless/background mode; plt.show() skipped to prevent blocking.")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    rates, actual_rhos, cis, paths, torts = run_analysis()
    save_results(rates, actual_rhos, cis, paths, torts)
    plot_results(rates, actual_rhos, cis, paths, torts)
    
    print("\n" + "="*60)
    print("FINAL SUMMARY (HARDENED BASELINE)")
    print("="*60)
    print(f"{'Target rho':<10} | {'Actual rho':<10} | {'Solvability':<12} | {'Avg SPL':<10} | {'Tortuosity':<10}")
    print("-" * 60)
    for i, rho in enumerate(DENSITIES):
        p_val = f"{paths[i]:<10.2f}" if paths[i] is not None else f"{'N/A':<10}"
        t_val = f"{torts[i]:<10.3f}" if torts[i] is not None else f"{'N/A':<10}"
        print(f"{rho:<10.2f} | {actual_rhos[i]:<10.3f} | {rates[i]:<12.3f} | {p_val} | {t_val}")
    print("="*60 + "\n")