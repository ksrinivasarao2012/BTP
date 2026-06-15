"""
Density Sweep v6 (Clustered) — IEEE RA-L Calibration for 10-Drone Clustered Spawn
FOCUSED VERSION: 2 Parameter Combinations Only

Validates maximum feasible obstacle density for 10-drone clustered spawn in a 20x20m arena.
2 parameter combinations × 5 densities × 100 maps = 1,000 total evaluations.
"""

import numpy as np
import csv
import time
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


# ============================================================================
# FIXED ENVIRONMENT CONSTANTS
# ============================================================================

FIELD_W = 20.0
FIELD_H = 20.0
DRONE_RADIUS = 0.15
N_DRONES = 10
MAPS_PER_COMBO = 1000
SOLVABILITY_THRESHOLD = 0.95
NUM_WORKERS = 4
BFS_CLEARANCE = 0.20
SPAWN_MODE = "clustered"
SEED_OFFSET = 100_000_000

# BFS grid parameters
BFS_GRID_RES = 0.2
ARENA_MARGIN = 0.6  # [0.6, 19.4] bounds for drone placement
WALL_CLEARANCE = BFS_CLEARANCE  # same inflation as obstacles = 0.20m


# ============================================================================
# PARAMETER SWEEP DEFINITIONS
# ============================================================================

DENSITIES = [0.20, 0.25, 0.30, 0.35, 0.40]

# FOCUSED: Only 2 parameter combinations
PARAMETER_COMBINATIONS = [
    # Combo 1: cr=1.5, osc=0.30, scg=7.0, gsc=6.0, inter=0.30, gexc=0.70
    (1.5, 0.30, 7.0, 6.0, 0.30, 0.70),
    # Combo 2: cr=2.0, osc=0.25, scg=8.0, gsc=5.0, inter=0.30, gexc=0.70
    (2.0, 0.25, 8.0, 5.0, 0.30, 0.70),
]


# ============================================================================
# MAP GENERATION: Goal and Spawn Center
# ============================================================================

def random_goal_and_start(rng, sc_goal_min_dist):
    """
    Sample goal and spawn center positions with minimum separation.

    Returns: (goal_x, goal_y, spawn_center_x, spawn_center_y)
    """
    goal_x = rng.uniform(2.0, 18.0)
    goal_y = rng.uniform(2.0, 18.0)

    for attempt in range(200):
        spawn_x = rng.uniform(2.0, 18.0)
        spawn_y = rng.uniform(2.0, 18.0)
        dist = np.sqrt((spawn_x - goal_x) ** 2 + (spawn_y - goal_y) ** 2)
        if dist > sc_goal_min_dist:
            return goal_x, goal_y, spawn_x, spawn_y

    # Fallback: place spawn at opposite corner from goal
    if goal_x < 10.0:
        spawn_x = 18.0
    else:
        spawn_x = 2.0
    if goal_y < 10.0:
        spawn_y = 18.0
    else:
        spawn_y = 2.0

    return goal_x, goal_y, spawn_x, spawn_y


# ============================================================================
# OBSTACLE GENERATION
# ============================================================================

def generate_obstacles(target_density, goal, spawn_center, rng, goal_exclusion_radius):
    """
    Generate obstacles at specified density with constraints.

    Returns: (obstacles list of (cx, cy, r), actual_density)
    obstacles: list of (center_x, center_y, radius)
    """
    obstacles = []
    target_area = target_density * FIELD_W * FIELD_H
    covered_area = 0.0

    # Raster grid for tracking occupied cells (5cm resolution)
    grid_res_raster = 0.05
    grid_size = int(FIELD_W / grid_res_raster)
    raster_grid = np.zeros((grid_size, grid_size), dtype=bool)

    for attempt in range(3000):
        # Sample obstacle radius
        rand_val = rng.random()
        if rand_val < 0.2:
            r = rng.uniform(1.5, 2.5)
        elif rand_val < 0.6:
            r = rng.uniform(0.6, 1.4)
        else:
            r = rng.uniform(0.2, 0.5)

        # Sample center position (geometric guarantee: surface in bounds)
        cx = rng.uniform(r, FIELD_W - r)
        cy = rng.uniform(r, FIELD_H - r)

        # Constraint: goal exclusion
        dist_to_goal = np.sqrt((cx - goal[0]) ** 2 + (cy - goal[1]) ** 2)
        if dist_to_goal < (r + goal_exclusion_radius):
            continue

        # Constraint: check raster grid for overlap with existing obstacles
        grid_x_min = max(0, int((cx - r) / grid_res_raster))
        grid_x_max = min(grid_size - 1, int((cx + r) / grid_res_raster))
        grid_y_min = max(0, int((cy - r) / grid_res_raster))
        grid_y_max = min(grid_size - 1, int((cy + r) / grid_res_raster))

        # Check actual circle overlap using raster cells
        # Only reject if a marked cell center is within radius of new obstacle
        patch = raster_grid[grid_y_min:grid_y_max + 1,
                            grid_x_min:grid_x_max + 1]
        if patch.any():
            # Get cell centers of marked cells in patch
            marked_rows, marked_cols = np.where(patch)
            actual_gx = marked_cols + grid_x_min
            actual_gy = marked_rows + grid_y_min
            cell_cx = actual_gx * grid_res_raster + grid_res_raster / 2
            cell_cy = actual_gy * grid_res_raster + grid_res_raster / 2
            dists = np.sqrt((cell_cx - cx)**2 + (cell_cy - cy)**2)
            if np.any(dists <= r):
                continue

        # No overlap found. Add obstacle and update grid.
        obstacles.append((cx, cy, r))
        added_area = np.pi * r ** 2
        covered_area += added_area

        # Mark raster cells as occupied
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


# ============================================================================
# PATH PLANNING: BFS WITH CORNER-CUTTING PREVENTION
# ============================================================================

def build_grid(obstacles, bfs_clearance=0.20, grid_res=0.2):
    """
    Build BFS grid with inflated obstacles and wall clearance.

    Wall clearance (0.43m) only applies to open space; obstacles in the clearance
    zone override it (obstacle inflation handles the blocking).

    Returns: (grid, grid_res) where grid[y, x] is True if passable
    """
    grid_size = int(FIELD_W / grid_res)
    grid = np.ones((grid_size, grid_size), dtype=bool)

    # First: mark inflated obstacles
    obstacle_grid = np.zeros((grid_size, grid_size), dtype=bool)
    for cx, cy, r in obstacles:
        inflated_r = r + bfs_clearance

        # Find bounding box of cells to check
        x_min = max(0, int((cx - inflated_r) / grid_res))
        x_max = min(grid_size - 1, int((cx + inflated_r) / grid_res))
        y_min = max(0, int((cy - inflated_r) / grid_res))
        y_max = min(grid_size - 1, int((cy + inflated_r) / grid_res))

        # Create mesh of cell centers
        xs = np.arange(x_min, x_max + 1) * grid_res + grid_res / 2
        ys = np.arange(y_min, y_max + 1) * grid_res + grid_res / 2
        xx, yy = np.meshgrid(xs, ys)

        # Distance from each cell center to obstacle center
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)

        # Mark cells within inflated obstacle
        blocked = dist <= inflated_r
        obstacle_grid[y_min:y_max + 1, x_min:x_max + 1] |= blocked

    # Apply obstacle blocking to main grid
    grid &= ~obstacle_grid

    # Wall clearance: treat walls same as obstacle surfaces
    # Blocks any path within BFS_CLEARANCE of arena boundary
    wall_cells = max(1, int(np.ceil(WALL_CLEARANCE / grid_res)))
    grid[:wall_cells, :]  = False   # bottom wall
    grid[-wall_cells:, :] = False   # top wall
    grid[:, :wall_cells]  = False   # left wall
    grid[:, -wall_cells:] = False   # right wall

    return grid, grid_res


def bfs_reachable(grid, grid_res, drone_pos, goal_pos):
    """
    BFS with corner-cutting prevention.

    Returns: True if drone can reach goal
    """
    grid_size = grid.shape[0]

    # Convert positions to grid indices
    def pos_to_grid(x, y):
        gx = int(x / grid_res)
        gy = int(y / grid_res)
        return max(0, min(grid_size - 1, gx)), max(0, min(grid_size - 1, gy))

    start_gx, start_gy = pos_to_grid(drone_pos[0], drone_pos[1])
    goal_gx, goal_gy = pos_to_grid(goal_pos[0], goal_pos[1])

    # Check if start and goal are passable
    if not grid[start_gy, start_gx] or not grid[goal_gy, goal_gx]:
        return False

    # BFS
    from collections import deque
    queue = deque([(start_gx, start_gy)])
    visited = set([(start_gx, start_gy)])

    # 8-connected directions
    directions = [
        (0, 1), (1, 0), (0, -1), (-1, 0),  # cardinal
        (1, 1), (1, -1), (-1, 1), (-1, -1)  # diagonal
    ]

    while queue:
        gx, gy = queue.popleft()

        if gx == goal_gx and gy == goal_gy:
            return True

        for dx, dy in directions:
            nx, ny = gx + dx, gy + dy

            if (nx, ny) in visited:
                continue
            if not (0 <= nx < grid_size and 0 <= ny < grid_size):
                continue
            if not grid[ny, nx]:
                continue

            # Corner-cutting prevention: for diagonal moves, check side cells
            if dx != 0 and dy != 0:  # Diagonal move
                side1_x, side1_y = gx + dx, gy
                side2_x, side2_y = gx, gy + dy
                if not (grid[side1_y, side1_x] and grid[side2_y, side2_x]):
                    continue

            visited.add((nx, ny))
            queue.append((nx, ny))

    return False


# ============================================================================
# SPAWN SIMULATION: CLUSTERED MODE
# ============================================================================

def spawn_drones_clustered(spawn_center, obstacles, goal, inter_drone_min,
                           spawn_obstacle_clearance, goal_spawn_clearance,
                           cluster_radius, rng):
    """
    Attempt to place 10 drones in clustered spawn mode.

    Returns: (drone_positions, fallback_count) or (None, 0) if failed
    drone_positions: list of (x, y) for each drone
    fallback_count: number of drones placed using fallback mechanisms
    """
    drone_positions = []
    fallback_count = 0
    sc_x, sc_y = spawn_center

    for drone_idx in range(N_DRONES):
        placed = False

        # Phase 1A: Clustered search (scale relative to cluster_radius)
        for search_radius in [cluster_radius * 1.0, cluster_radius * 1.33,
                              cluster_radius * 1.67, cluster_radius * 2.33]:
            if placed:
                break

            for attempt in range(150):
                # Sample position in search box
                dx = rng.uniform(-search_radius, search_radius)
                dy = rng.uniform(-search_radius, search_radius)
                px = sc_x + dx
                py = sc_y + dy

                # Clip to bounds
                px = np.clip(px, ARENA_MARGIN, FIELD_W - ARENA_MARGIN)
                py = np.clip(py, ARENA_MARGIN, FIELD_H - ARENA_MARGIN)

                # Check constraints
                valid = True

                # Inter-drone constraint
                for existing_pos in drone_positions:
                    dist = np.sqrt((px - existing_pos[0]) ** 2 + (py - existing_pos[1]) ** 2)
                    if dist < (2 * DRONE_RADIUS + inter_drone_min):
                        valid = False
                        break

                if not valid:
                    continue

                # Obstacle constraint
                for ox, oy, or_ in obstacles:
                    dist = np.sqrt((px - ox) ** 2 + (py - oy) ** 2)
                    if dist < (or_ + DRONE_RADIUS + spawn_obstacle_clearance):
                        valid = False
                        break

                if not valid:
                    continue

                # Goal constraint
                dist_to_goal = np.sqrt((px - goal[0]) ** 2 + (py - goal[1]) ** 2)
                if dist_to_goal < goal_spawn_clearance:
                    valid = False

                if valid:
                    drone_positions.append((px, py))
                    placed = True
                    break

        # Phase 1B: Fallback ring (scale with cluster_radius)
        if not placed:
            for ring_radius in [cluster_radius * 0.40, cluster_radius * 0.80,
                                cluster_radius * 1.20, cluster_radius * 1.67,
                                cluster_radius * 2.33]:
                angle = (drone_idx * 2 * np.pi / N_DRONES)
                px = sc_x + ring_radius * np.cos(angle)
                py = sc_y + ring_radius * np.sin(angle)

                # Clip to bounds
                px = np.clip(px, ARENA_MARGIN, FIELD_W - ARENA_MARGIN)
                py = np.clip(py, ARENA_MARGIN, FIELD_H - ARENA_MARGIN)

                # Check obstacle constraint only
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

        # Phase 1C: Absolute fallback (scale with cluster_radius, check all constraints)
        if not placed:
            angle = (drone_idx * 2 * np.pi / N_DRONES)
            fallback_radius = cluster_radius * 0.40
            px = sc_x + fallback_radius * np.cos(angle)
            py = sc_y + fallback_radius * np.sin(angle)

            # Clip to bounds
            px = np.clip(px, ARENA_MARGIN, FIELD_W - ARENA_MARGIN)
            py = np.clip(py, ARENA_MARGIN, FIELD_H - ARENA_MARGIN)

            # Check all constraints
            valid = True

            # Inter-drone constraint
            for existing_pos in drone_positions:
                dist = np.sqrt((px - existing_pos[0]) ** 2 + (py - existing_pos[1]) ** 2)
                if dist < (2 * DRONE_RADIUS + inter_drone_min):
                    valid = False
                    break

            if not valid:
                # Discard map entirely
                return None, 0

            # Obstacle constraint
            for ox, oy, or_ in obstacles:
                dist = np.sqrt((px - ox) ** 2 + (py - oy) ** 2)
                if dist < (or_ + DRONE_RADIUS + spawn_obstacle_clearance):
                    valid = False
                    break

            if not valid:
                # Discard map entirely
                return None, 0

            # Goal constraint
            dist_to_goal = np.sqrt((px - goal[0]) ** 2 + (py - goal[1]) ** 2)
            if dist_to_goal < goal_spawn_clearance:
                # Discard map entirely
                return None, 0

            drone_positions.append((px, py))
            fallback_count += 1

    return drone_positions, fallback_count


# ============================================================================
# SOLVABILITY MEASUREMENT
# ============================================================================

def measure_solvability(density, sc_goal_min_dist, goal_excl_radius,
                       inter_drone_min, spawn_obstacle_clearance,
                       goal_spawn_clearance, cluster_radius, seed_base, num_maps=100):
    """
    Measure solvability for a single density by generating fresh maps.

    Each map gets fresh goal, spawn_center, and obstacles.
    Seed formula: seed_base + map_idx

    Returns: dict with metrics including avg_actual_density and avg_obs_count
    """
    clean_maps = 0
    discarded_maps = 0
    total_fallbacks = 0
    maps_all10_ok = 0
    total_drone_successes = 0
    sum_actual_density = 0.0
    sum_obs_count = 0

    for map_idx in range(num_maps):
        # Generate fresh RNG per map
        map_seed = seed_base + map_idx
        rng = np.random.RandomState(map_seed)

        # Fresh goal and spawn center per map
        goal_x, goal_y, spawn_x, spawn_y = random_goal_and_start(rng, sc_goal_min_dist)
        goal = (goal_x, goal_y)
        spawn_center = (spawn_x, spawn_y)

        # Fresh obstacles per map at this density
        obstacles, actual_density_achieved = generate_obstacles(
            density, goal, spawn_center, rng, goal_excl_radius
        )
        sum_actual_density += actual_density_achieved
        sum_obs_count += len(obstacles)
        # Spawn drones
        drone_positions, fallback_count = spawn_drones_clustered(
            spawn_center, obstacles, goal, inter_drone_min,
            spawn_obstacle_clearance, goal_spawn_clearance,
            cluster_radius, rng
        )

        if drone_positions is None:
            discarded_maps += 1
            continue

        # Build BFS grid
        grid, grid_res = build_grid(obstacles, BFS_CLEARANCE, BFS_GRID_RES)

        # Validate goal position is passable in grid
        goal_gx = int(goal[0] / grid_res)
        goal_gy = int(goal[1] / grid_res)
        goal_gx = np.clip(goal_gx, 0, grid.shape[1] - 1)
        goal_gy = np.clip(goal_gy, 0, grid.shape[0] - 1)
        if not grid[goal_gy, goal_gx]:
            discarded_maps += 1
            continue

        # Validate spawn positions in grid
        map_valid = True
        for dx, dy in drone_positions:
            gx = int(dx / grid_res)
            gy = int(dy / grid_res)
            gx = np.clip(gx, 0, grid.shape[1] - 1)
            gy = np.clip(gy, 0, grid.shape[0] - 1)
            if not grid[gy, gx]:
                map_valid = False
                break

        if not map_valid:
            discarded_maps += 1
            continue

        # Count solvable drones for this map
        clean_maps += 1
        total_fallbacks += fallback_count
        map_drone_successes = 0

        for drone_pos in drone_positions:
            if bfs_reachable(grid, grid_res, drone_pos, goal):
                map_drone_successes += 1
                total_drone_successes += 1

        # Check if all 10 drones succeeded for this map
        if map_drone_successes == N_DRONES:
            maps_all10_ok += 1

    # Calculate metrics
    if clean_maps == 0:
        pct_all10_ok = 0.0
        avg_drone_ok = 0.0
        avg_fallback_rate = 0.0
    else:
        pct_all10_ok = maps_all10_ok / clean_maps
        avg_drone_ok = (total_drone_successes / (clean_maps * N_DRONES)) * 100.0
        avg_fallback_rate = total_fallbacks / clean_maps if clean_maps > 0 else 0.0

    avg_actual_density = sum_actual_density / num_maps if num_maps > 0 else 0.0
    avg_obs_count = sum_obs_count / num_maps if num_maps > 0 else 0

    return {
        'pct_all10_ok': pct_all10_ok,
        'avg_drone_ok': avg_drone_ok,
        'clean_drone_successes': total_drone_successes,
        'total_clean_maps': clean_maps,
        'total_discarded': discarded_maps,
        'total_fallbacks': total_fallbacks,
        'avg_fallback_rate': avg_fallback_rate,
        'avg_actual_density': avg_actual_density,
        'avg_obs_count': avg_obs_count,
    }


# ============================================================================
# COMBINATION PROCESSING
# ============================================================================

def process_combination(combo_data):
    """
    Process a single parameter combination across all 5 densities.

    combo_data: tuple of (cluster_r, spawn_obs_clear, sc_goal_dist, goal_spawn_clear,
                          inter_drone, goal_excl, combo_idx, total_combos)
    """
    (cluster_r, spawn_obs_clear, sc_goal_dist, goal_spawn_clear,
     inter_drone, goal_excl, combo_idx, total_combos) = combo_data

    results = []
    ceiling = None
    ceiling_reason = "all_pass"
    infeasible = False

    for density_idx, density in enumerate(DENSITIES):
        # Generate seed base per density: SEED_OFFSET + combo_idx*10M + density_idx*1M
        seed_base = (SEED_OFFSET + combo_idx * 10_000_000 + density_idx * 1_000_000) % (2**32)

        # Measure solvability (generates fresh goal, spawn, obstacles per map)
        metrics = measure_solvability(
            density, sc_goal_dist, goal_excl,
            inter_drone, spawn_obs_clear, goal_spawn_clear,
            cluster_r, seed_base, MAPS_PER_COMBO
        )

        # Always append results first, regardless of pass/fail
        results.append({
            'density': density,
            'actual_density': metrics['avg_actual_density'],
            'pct_all10_ok': metrics['pct_all10_ok'],
            'avg_drone_ok': metrics['avg_drone_ok'],
            'clean_drone_successes': metrics['clean_drone_successes'],
            'total_clean_maps': metrics['total_clean_maps'],
            'total_discarded': metrics['total_discarded'],
            'total_fallbacks': metrics['total_fallbacks'],
            'avg_fallback_rate': metrics['avg_fallback_rate'],
            'obs_count': metrics['avg_obs_count'],
        })

        # Then check pass/fail and update ceiling
        passes = metrics['pct_all10_ok'] >= SOLVABILITY_THRESHOLD and metrics['total_clean_maps'] > 0

        if passes:
            ceiling = density  # keep updating as higher densities pass
        else:
            if density_idx == 0:
                ceiling = None
                ceiling_reason = "failed_at_minimum"
                infeasible = True
            else:
                ceiling = DENSITIES[density_idx - 1]
                ceiling_reason = f"failed_at_{density:.2f}"
            break  # stop testing higher densities once one fails

    # If loop completed without break, all densities passed
    if ceiling_reason == "all_pass":
        ceiling = DENSITIES[-1]

    return {
        'cluster_radius': cluster_r,
        'spawn_obstacle_clearance': spawn_obs_clear,
        'sc_goal_min_dist': sc_goal_dist,
        'goal_spawn_clearance': goal_spawn_clear,
        'inter_drone_min': inter_drone,
        'goal_exclusion_radius': goal_excl,
        'results': results,  # List of dicts, one per density, each with its own actual_density/obs_count
        'ceiling': ceiling,
        'ceiling_reason': ceiling_reason,
        'infeasible': infeasible,
        'combo_idx': combo_idx,
    }


# ============================================================================
# MAIN SWEEP
# ============================================================================

def main():
    """Run the focused density sweep for 2 parameter combinations."""

    combinations = PARAMETER_COMBINATIONS
    total_combos = len(combinations)
    print(f"Total parameter combinations: {total_combos}")
    print(f"Expected runtime: 30-40 minutes with {NUM_WORKERS} workers\n")

    # Output CSV setup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = Path(__file__).parent / f"density_sweep_v6_two_combos_results_{timestamp}.csv"

    csv_file = open(csv_path, 'w', newline='')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow([
        'cluster_radius', 'spawn_obstacle_clearance', 'sc_goal_min_dist',
        'goal_spawn_clearance', 'inter_drone_min', 'goal_exclusion_radius',
        'spawn_mode', 'density', 'pct_all10_ok', 'avg_drone_ok',
        'clean_drone_successes', 'total_clean_maps', 'total_discarded',
        'total_fallbacks', 'avg_fallback_rate', 'avg_actual_density',
        'avg_obs_count', 'infeasible', 'recommended_ceiling', 'ceiling_reason'
    ])
    csv_file.flush()

    # Prepare combo data for processing
    combo_data_list = []
    for idx, (cluster_r, spawn_obs_clear, sc_goal_dist, goal_spawn_clear,
              inter_drone, goal_excl) in enumerate(combinations):
        combo_data_list.append((
            cluster_r, spawn_obs_clear, sc_goal_dist, goal_spawn_clear,
            inter_drone, goal_excl, idx, total_combos
        ))

    # Process combinations in parallel
    ceiling_distribution = {d: 0 for d in DENSITIES}
    ceiling_distribution[None] = 0
    all_results = []

    start_time = time.time()

    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {
            executor.submit(process_combination, combo_data): combo_data
            for combo_data in combo_data_list
        }

        completed = 0
        for future in as_completed(futures):
            completed += 1
            try:
                result = future.result()
            except Exception as e:
                combo_data = futures[future]
                print(f"[ERROR] Combo {combo_data[6]}: {e}")
                continue
            all_results.append(result)

            # Write each density result to CSV (use per-density actual_density and obs_count)
            for density_result in result['results']:
                csv_writer.writerow([
                    result['cluster_radius'],
                    result['spawn_obstacle_clearance'],
                    result['sc_goal_min_dist'],
                    result['goal_spawn_clearance'],
                    result['inter_drone_min'],
                    result['goal_exclusion_radius'],
                    SPAWN_MODE,
                    density_result['density'],
                    density_result['pct_all10_ok'],
                    density_result['avg_drone_ok'],
                    density_result['clean_drone_successes'],
                    density_result['total_clean_maps'],
                    density_result['total_discarded'],
                    density_result['total_fallbacks'],
                    density_result['avg_fallback_rate'],
                    density_result['actual_density'],  # Per-density value, not average
                    density_result['obs_count'],  # Per-density value, not average
                    result['infeasible'],
                    result['ceiling'],
                    result['ceiling_reason'],
                ])
            csv_file.flush()

            # Track ceiling distribution
            ceiling = result['ceiling']
            if ceiling in ceiling_distribution:
                ceiling_distribution[ceiling] += 1

            # Console output
            ceil_str = (f"{result['ceiling']:.2f}"
                        if result['ceiling'] is not None
                        else "NONE")
            print(f"[{completed}/{total_combos}] "
                  f"cr={result['cluster_radius']:.1f} "
                  f"osc={result['spawn_obstacle_clearance']:.2f} "
                  f"scg={result['sc_goal_min_dist']:.1f} "
                  f"gsc={result['goal_spawn_clearance']:.1f} "
                  f"inter={result['inter_drone_min']:.2f} "
                  f"gexc={result['goal_exclusion_radius']:.2f} "
                  f"→ ceil={ceil_str}")

            # Per-density density tracking
            for dr in result['results']:
                actual = dr['actual_density']
                target = dr['density']
                diff = actual - target
                print(f"    d={target:.2f} → actual={actual:.3f} "
                      f"({'under' if diff < 0 else 'over'} by {abs(diff):.3f}) "
                      f"pct_all10={dr['pct_all10_ok']*100:.1f}%")

    csv_file.close()

    # Print summary
    elapsed_time = time.time() - start_time
    print(f"\n{'='*70}")
    print(f"FOCUSED SWEEP COMPLETE")
    print(f"{'='*70}")
    print(f"Total time: {elapsed_time / 3600:.1f} hours")
    print(f"Results saved to: {csv_path}")
    print(f"\nCeiling distribution:")
    for density in DENSITIES:
        count = ceiling_distribution.get(density, 0)
        print(f"  {density:.2f}: {count} combos")
    if ceiling_distribution.get(None, 0) > 0:
        print(f"  Infeasible: {ceiling_distribution[None]} combos")


if __name__ == "__main__":
    main()
