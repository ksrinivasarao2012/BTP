"""
Density Sweep for Specific v14 Densities (0.26, 0.27, 0.28, 0.29)
Evaluates solvability using the exact same structure as density_sweep_v14_10000maps.py.
Uses 10,000 random maps per density and chunked parallel processing.
"""

import os
import numpy as np
import csv
import time
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import sys

# ============================================================================
# FIXED ENVIRONMENT CONSTANTS
# ============================================================================

FIELD_W = 20.0
FIELD_H = 20.0
DRONE_RADIUS = 0.15
N_DRONES = 10
TOTAL_MAPS_PER_DENSITY = 10000  # 10,000 maps per density
CHUNK_SIZE = 500                # Evaluate in chunks of 500 maps per process
BFS_CLEARANCE = 0.20
SPAWN_MODE = "clustered"
SEED_OFFSET = 200_000_000

# BFS grid parameters
BFS_GRID_RES = 0.2
BFS_GRID_RES = 0.2
ARENA_MARGIN = 0.6
WALL_CLEARANCE = BFS_CLEARANCE

# ============================================================================
# v14 CONFIGURATION
# ============================================================================

CLUSTER_RADIUS = 1.5
SPAWN_OBSTACLE_CLEARANCE = 0.0
SC_GOAL_MIN_DIST = 8.0
GOAL_SPAWN_CLEARANCE = 8.0
INTER_DRONE_MIN = 0.30
GOAL_EXCLUSION_RADIUS = 2.0

DENSITIES = [0.26, 0.27, 0.28, 0.29]
if len(sys.argv) > 1:
    try:
        DENSITIES = [float(sys.argv[1])]
    except ValueError:
        print(f"Invalid density argument: {sys.argv[1]}. Using default list.")


# ============================================================================
# MAP GENERATION & BFS
# ============================================================================

def random_goal_and_start(rng, sc_goal_min_dist):
    goal_x = rng.uniform(2.0, 18.0)
    goal_y = rng.uniform(2.0, 18.0)

    for attempt in range(200):
        spawn_x = rng.uniform(2.0, 18.0)
        spawn_y = rng.uniform(2.0, 18.0)
        dist = np.sqrt((spawn_x - goal_x) ** 2 + (spawn_y - goal_y) ** 2)
        if dist > sc_goal_min_dist:
            return goal_x, goal_y, spawn_x, spawn_y

    if goal_x < 10.0:
        spawn_x = 18.0
    else:
        spawn_x = 2.0
    if goal_y < 10.0:
        spawn_y = 18.0
    else:
        spawn_y = 2.0

    return goal_x, goal_y, spawn_x, spawn_y

def generate_obstacles(target_density, goal, spawn_center, rng, goal_exclusion_radius):
    obstacles = []
    target_area = target_density * FIELD_W * FIELD_H
    covered_area = 0.0

    grid_res_raster = 0.05
    grid_size = int(FIELD_W / grid_res_raster)
    raster_grid = np.zeros((grid_size, grid_size), dtype=bool)

    for attempt in range(3000):
        rand_val = rng.random()
        if rand_val < 0.2:
            r = rng.uniform(1.5, 2.5)
        elif rand_val < 0.6:
            r = rng.uniform(0.6, 1.4)
        else:
            r = rng.uniform(0.2, 0.5)

        cx = rng.uniform(r, FIELD_W - r)
        cy = rng.uniform(r, FIELD_H - r)

        dist_to_goal = np.sqrt((cx - goal[0]) ** 2 + (cy - goal[1]) ** 2)
        if dist_to_goal < (r + goal_exclusion_radius):
            continue

        grid_x_min = max(0, int((cx - r) / grid_res_raster))
        grid_x_max = min(grid_size - 1, int((cx + r) / grid_res_raster))
        grid_y_min = max(0, int((cy - r) / grid_res_raster))
        grid_y_max = min(grid_size - 1, int((cy + r) / grid_res_raster))

        patch = raster_grid[grid_y_min:grid_y_max + 1, grid_x_min:grid_x_max + 1]
        if patch.any():
            marked_rows, marked_cols = np.where(patch)
            actual_gx = marked_cols + grid_x_min
            actual_gy = marked_rows + grid_y_min
            cell_cx = actual_gx * grid_res_raster + grid_res_raster / 2
            cell_cy = actual_gy * grid_res_raster + grid_res_raster / 2
            dists = np.sqrt((cell_cx - cx)**2 + (cell_cy - cy)**2)
            if np.any(dists <= r):
                continue

        obstacles.append((cx, cy, r))
        added_area = np.pi * r ** 2
        covered_area += added_area

        for gy in range(grid_y_min, grid_y_max + 1):
            for gx in range(grid_x_min, grid_x_max + 1):
                cell_cx = gx * grid_res_raster + grid_res_raster / 2
                cell_cy = gy * grid_res_raster + grid_res_raster / 2
                dist_to_center = np.sqrt((cell_cx - cx) ** 2 + (cell_cy - cy) ** 2)
                if dist_to_center <= r:
                    raster_grid[gy, gx] = True

        if covered_area >= target_area:
            break

    actual_density = covered_area / (FIELD_W * FIELD_H)
    return obstacles, actual_density

def build_grid(obstacles, bfs_clearance=0.20, grid_res=0.2):
    grid_size = int(FIELD_W / grid_res)
    grid = np.ones((grid_size, grid_size), dtype=bool)

    obstacle_grid = np.zeros((grid_size, grid_size), dtype=bool)
    for cx, cy, r in obstacles:
        inflated_r = r + bfs_clearance
        x_min = max(0, int((cx - inflated_r) / grid_res))
        x_max = min(grid_size - 1, int((cx + inflated_r) / grid_res))
        y_min = max(0, int((cy - inflated_r) / grid_res))
        y_max = min(grid_size - 1, int((cy + inflated_r) / grid_res))

        xs = np.arange(x_min, x_max + 1) * grid_res + grid_res / 2
        ys = np.arange(y_min, y_max + 1) * grid_res + grid_res / 2
        xx, yy = np.meshgrid(xs, ys)
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        blocked = dist <= inflated_r
        obstacle_grid[y_min:y_max + 1, x_min:x_max + 1] |= blocked

    grid &= ~obstacle_grid
    wall_cells = max(1, int(np.ceil(WALL_CLEARANCE / grid_res)))
    grid[:wall_cells, :]  = False
    grid[-wall_cells:, :] = False
    grid[:, :wall_cells]  = False
    grid[:, -wall_cells:] = False

    return grid, grid_res

def bfs_reachable(grid, grid_res, drone_pos, goal_pos):
    grid_size = grid.shape[0]

    def pos_to_grid(x, y):
        gx = int(x / grid_res)
        gy = int(y / grid_res)
        return max(0, min(grid_size - 1, gx)), max(0, min(grid_size - 1, gy))

    start_gx, start_gy = pos_to_grid(drone_pos[0], drone_pos[1])
    goal_gx, goal_gy = pos_to_grid(goal_pos[0], goal_pos[1])

    if not grid[start_gy, start_gx] or not grid[goal_gy, goal_gx]:
        return False

    from collections import deque
    queue = deque([(start_gx, start_gy)])
    visited = set([(start_gx, start_gy)])

    directions = [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]

    while queue:
        gx, gy = queue.popleft()
        if gx == goal_gx and gy == goal_gy:
            return True

        for dx, dy in directions:
            nx, ny = gx + dx, gy + dy
            if (nx, ny) in visited: continue
            if not (0 <= nx < grid_size and 0 <= ny < grid_size): continue
            if not grid[ny, nx]: continue

            if dx != 0 and dy != 0:
                if not (grid[gy, gx + dx] and grid[gy + dy, gx]):
                    continue

            visited.add((nx, ny))
            queue.append((nx, ny))

    return False

def spawn_drones_clustered(spawn_center, obstacles, goal, inter_drone_min,
                           spawn_obstacle_clearance, goal_spawn_clearance,
                           cluster_radius, rng):
    drone_positions = []
    fallback_count = 0
    sc_x, sc_y = spawn_center

    for drone_idx in range(N_DRONES):
        placed = False
        for search_radius in [cluster_radius * 1.0, cluster_radius * 1.33,
                              cluster_radius * 1.67, cluster_radius * 2.33]:
            if placed: break
            for attempt in range(150):
                dx = rng.uniform(-search_radius, search_radius)
                dy = rng.uniform(-search_radius, search_radius)
                px = sc_x + dx
                py = sc_y + dy

                px = np.clip(px, ARENA_MARGIN, FIELD_W - ARENA_MARGIN)
                py = np.clip(py, ARENA_MARGIN, FIELD_H - ARENA_MARGIN)

                valid = True
                for existing_pos in drone_positions:
                    dist = np.sqrt((px - existing_pos[0]) ** 2 + (py - existing_pos[1]) ** 2)
                    if dist < (2 * DRONE_RADIUS + inter_drone_min):
                        valid = False
                        break

                if not valid: continue

                for ox, oy, or_ in obstacles:
                    dist = np.sqrt((px - ox) ** 2 + (py - oy) ** 2)
                    if dist < (or_ + DRONE_RADIUS + spawn_obstacle_clearance):
                        valid = False
                        break

                if not valid: continue

                dist_to_goal = np.sqrt((px - goal[0]) ** 2 + (py - goal[1]) ** 2)
                if dist_to_goal < goal_spawn_clearance:
                    valid = False

                if valid:
                    drone_positions.append((px, py))
                    placed = True
                    break

        if not placed:
            for ring_radius in [cluster_radius * 0.40, cluster_radius * 0.80,
                                cluster_radius * 1.20, cluster_radius * 1.67,
                                cluster_radius * 2.33]:
                angle = (drone_idx * 2 * np.pi / N_DRONES)
                px = sc_x + ring_radius * np.cos(angle)
                py = sc_y + ring_radius * np.sin(angle)

                px = np.clip(px, ARENA_MARGIN, FIELD_W - ARENA_MARGIN)
                py = np.clip(py, ARENA_MARGIN, FIELD_H - ARENA_MARGIN)

                valid = True
                for ox, oy, or_ in obstacles:
                    dist = np.sqrt((px - ox) ** 2 + (py - oy) ** 2)
                    if dist < (or_ + DRONE_RADIUS + spawn_obstacle_clearance):
                        valid = False
                        break

                if valid:
                    drone_positions.append((px, py))
                    fallback_count += 1
                    placed = True
                    break

        if not placed:
            angle = (drone_idx * 2 * np.pi / N_DRONES)
            fallback_radius = cluster_radius * 0.40
            px = sc_x + fallback_radius * np.cos(angle)
            py = sc_y + fallback_radius * np.sin(angle)

            px = np.clip(px, ARENA_MARGIN, FIELD_W - ARENA_MARGIN)
            py = np.clip(py, ARENA_MARGIN, FIELD_H - ARENA_MARGIN)

            valid = True
            for existing_pos in drone_positions:
                dist = np.sqrt((px - existing_pos[0]) ** 2 + (py - existing_pos[1]) ** 2)
                if dist < (2 * DRONE_RADIUS + inter_drone_min):
                    valid = False
                    break

            if not valid: return None, 0

            for ox, oy, or_ in obstacles:
                dist = np.sqrt((px - ox) ** 2 + (py - oy) ** 2)
                if dist < (or_ + DRONE_RADIUS + spawn_obstacle_clearance):
                    valid = False
                    break

            if not valid: return None, 0

            dist_to_goal = np.sqrt((px - goal[0]) ** 2 + (py - goal[1]) ** 2)
            if dist_to_goal < goal_spawn_clearance:
                return None, 0

            drone_positions.append((px, py))
            fallback_count += 1

    return drone_positions, fallback_count

# ============================================================================
# CHUNK-BASED SOLVABILITY TASK
# ============================================================================

def run_chunk_task(args):
    density, start_seed, num_maps, task_id = args
    
    clean_maps = 0
    discarded_maps = 0
    total_fallbacks = 0
    maps_all10_ok = 0
    total_drone_successes = 0
    sum_actual_density = 0.0
    sum_obs_count = 0

    for map_idx in range(num_maps):
        map_seed = start_seed + map_idx
        rng = np.random.RandomState(map_seed)

        goal_x, goal_y, spawn_x, spawn_y = random_goal_and_start(rng, SC_GOAL_MIN_DIST)
        goal = (goal_x, goal_y)
        spawn_center = (spawn_x, spawn_y)

        obstacles, actual_density_achieved = generate_obstacles(
            density, goal, spawn_center, rng, GOAL_EXCLUSION_RADIUS
        )
        sum_actual_density += actual_density_achieved
        sum_obs_count += len(obstacles)

        drone_positions, fallback_count = spawn_drones_clustered(
            spawn_center, obstacles, goal, INTER_DRONE_MIN,
            SPAWN_OBSTACLE_CLEARANCE, GOAL_SPAWN_CLEARANCE,
            CLUSTER_RADIUS, rng
        )

        if drone_positions is None:
            discarded_maps += 1
            continue

        grid, grid_res = build_grid(obstacles, BFS_CLEARANCE, BFS_GRID_RES)

        goal_gx = np.clip(int(goal[0] / grid_res), 0, grid.shape[1] - 1)
        goal_gy = np.clip(int(goal[1] / grid_res), 0, grid.shape[0] - 1)
        if not grid[goal_gy, goal_gx]:
            discarded_maps += 1
            continue

        map_valid = True
        for dx, dy in drone_positions:
            gx = np.clip(int(dx / grid_res), 0, grid.shape[1] - 1)
            gy = np.clip(int(dy / grid_res), 0, grid.shape[0] - 1)
            if not grid[gy, gx]:
                map_valid = False
                break

        if not map_valid:
            discarded_maps += 1
            continue

        clean_maps += 1
        total_fallbacks += fallback_count
        map_drone_successes = 0

        for drone_pos in drone_positions:
            if bfs_reachable(grid, grid_res, drone_pos, goal):
                map_drone_successes += 1
                total_drone_successes += 1

        if map_drone_successes == N_DRONES:
            maps_all10_ok += 1

    return {
        'density': density,
        'clean_maps': clean_maps,
        'discarded_maps': discarded_maps,
        'total_fallbacks': total_fallbacks,
        'maps_all10_ok': maps_all10_ok,
        'total_drone_successes': total_drone_successes,
        'sum_actual_density': sum_actual_density,
        'sum_obs_count': sum_obs_count,
        'num_maps': num_maps
    }

def main():
    num_workers = min(8, os.cpu_count() or 1)

    print("=" * 80)
    print("  RUNNING HIGH-PRECISION DENSITY SOLVABILITY SWEEP (10,000 MAPS)")
    print(f"  Target Parameters: cr=1.5, osc=0.0, scg=8.0, gsc=8.0, inter=0.30")
    print(f"  Densities to Evaluate: {DENSITIES}")
    print(f"  Parallelization: Using {num_workers} parallel workers")
    print("=" * 80)

    # Prepare chunks
    tasks = []
    task_id = 0
    for density in DENSITIES:
        num_chunks = TOTAL_MAPS_PER_DENSITY // CHUNK_SIZE
        for chunk_idx in range(num_chunks):
            start_seed = (SEED_OFFSET + int(density * 100) * 50_000 + chunk_idx * CHUNK_SIZE) % (2**32)
            tasks.append((density, start_seed, CHUNK_SIZE, task_id))
            task_id += 1

    start_time = time.time()
    
    # Store aggregated metrics per density
    aggregated = {
        d: {
            'clean_maps': 0,
            'discarded_maps': 0,
            'total_fallbacks': 0,
            'maps_all10_ok': 0,
            'total_drone_successes': 0,
            'sum_actual_density': 0.0,
            'sum_obs_count': 0,
            'num_maps': 0
        } for d in DENSITIES
    }

    completed_tasks = 0
    total_tasks = len(tasks)

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(run_chunk_task, task): task for task in tasks}
        
        for future in as_completed(futures):
            res = future.result()
            d = res['density']
            
            # Aggregate results
            aggregated[d]['clean_maps'] += res['clean_maps']
            aggregated[d]['discarded_maps'] += res['discarded_maps']
            aggregated[d]['total_fallbacks'] += res['total_fallbacks']
            aggregated[d]['maps_all10_ok'] += res['maps_all10_ok']
            aggregated[d]['total_drone_successes'] += res['total_drone_successes']
            aggregated[d]['sum_actual_density'] += res['sum_actual_density']
            aggregated[d]['sum_obs_count'] += res['sum_obs_count']
            aggregated[d]['num_maps'] += res['num_maps']
            
            completed_tasks += 1
            if completed_tasks % 5 == 0 or completed_tasks == total_tasks:
                elapsed = time.time() - start_time
                pct_done = (completed_tasks / total_tasks) * 100
                print(f"  [PROGRESS] {completed_tasks}/{total_tasks} chunks completed ({pct_done:.1f}%) | Elapsed: {elapsed:.1f}s", flush=True)

    # Save to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = Path(__file__).parent / f"density_sweep_v14_specific_results_{timestamp}.csv"

    with open(csv_path, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow([
            'cluster_radius', 'spawn_obstacle_clearance', 'sc_goal_min_dist',
            'goal_spawn_clearance', 'inter_drone_min', 'goal_exclusion_radius',
            'spawn_mode', 'density', 'pct_all10_ok', 'avg_drone_ok',
            'clean_drone_successes', 'total_clean_maps', 'total_discarded',
            'total_fallbacks', 'avg_fallback_rate', 'avg_actual_density',
            'avg_obs_count'
        ])
        
        for d in DENSITIES:
            data = aggregated[d]
            clean = data['clean_maps']
            total = data['num_maps']
            
            pct_all10_ok = data['maps_all10_ok'] / clean if clean > 0 else 0.0
            avg_drone_ok = (data['total_drone_successes'] / (clean * N_DRONES)) * 100.0 if clean > 0 else 0.0
            avg_fallback_rate = data['total_fallbacks'] / clean if clean > 0 else 0.0
            avg_actual_density = data['sum_actual_density'] / total
            avg_obs_count = data['sum_obs_count'] / total
            
            csv_writer.writerow([
                CLUSTER_RADIUS,
                SPAWN_OBSTACLE_CLEARANCE,
                SC_GOAL_MIN_DIST,
                GOAL_SPAWN_CLEARANCE,
                INTER_DRONE_MIN,
                GOAL_EXCLUSION_RADIUS,
                SPAWN_MODE,
                d,
                pct_all10_ok,
                avg_drone_ok,
                data['total_drone_successes'],
                clean,
                data['discarded_maps'],
                data['total_fallbacks'],
                avg_fallback_rate,
                avg_actual_density,
                avg_obs_count
            ])
            
    print("\n" + "=" * 80)
    print("  FINAL 10,000-MAP EVALUATION SUMMARY")
    print("=" * 80)
    for d in DENSITIES:
        data = aggregated[d]
        clean = data['clean_maps']
        total = data['num_maps']
        pct_all10_ok = data['maps_all10_ok'] / clean if clean > 0 else 0.0
        avg_actual_density = data['sum_actual_density'] / total
        print(f"  d={d:.2f} -> actual_density={avg_actual_density:.3f} | maps_solvable={pct_all10_ok*100:.2f}% (Clean Maps: {clean}/{total})")
    
    elapsed_time = time.time() - start_time
    print("=" * 80)
    print(f"Sweep complete in {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes).")
    print(f"CSV saved to: {csv_path}")
    print("=" * 80)

if __name__ == "__main__":
    main()
