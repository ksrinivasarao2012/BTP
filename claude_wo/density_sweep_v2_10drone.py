"""
Density Sweep v2 — 10-Drone Strict Solvability Check
=====================================================
Finds the correct obstacle density ceiling for the 20x20m training field.

Key upgrades over v1:
  - Solvability checked from each of 10 drone ACTUAL spawned positions (strict: all 10 must pass)
  - Two spawn modes tested separately: CLUSTERED and SCATTERED
  - Full parameter sweep: BFS_MARGIN, SPAWN_INTER_DRONE_MIN, GOAL_SPAWN_CLEARANCE, SC_GOAL_MIN_DIST
  - Fallback spawn (no obstacle check) discards the map — not counted as solvability failure
  - Fallback also checks goal distance — if violated, map is discarded
  - Infeasibility criterion: if clean drone successes < 150 across 50 maps, combination is INFEASIBLE
  - CSV output for offline analysis
  - Fallback counter tracked per spawn mode
  - 4-core multiprocessing for combination runs (ProcessPoolExecutor)

Environment match (v15 fixed):
  - 20x20m arena, 10 drones, drone_radius=0.15m
  - Obstacle wall clearance: surface stays >= MIN_WALL_GAP (0.20m) from boundary
  - BFS grid resolution: 0.2m (matches _compute_shortest_path_distance_map)
  - Obstacle raster resolution: 0.05m (matches _generate_obstacles)
"""

import numpy as np
from collections import deque
import csv
import itertools
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

# ── Fixed constants ───────────────────────────────────────────────────────────
FIELD_W       = 20.0
FIELD_H       = 20.0
DRONE_RADIUS  = 0.15
N_DRONES      = 10
MAPS_PER_COMBINATION = 50          # max maps attempted per parameter combination
INFEASIBILITY_THRESHOLD = 150      # min clean drone successes out of 50*10=500

MIN_WALL_GAP  = 0.20
OBSTACLE_CLEARANCE_FROM_SC = 2.0   # fixed: obstacle must stay >= 2m from sc

SPAWN_OBSTACLE_CLEARANCE = 0.45    # + orad, matches reset()
CLUSTERED_RADII   = [1.5, 2.0, 2.5, 3.5]
CLUSTERED_ATTEMPTS = 150
SCATTERED_ATTEMPTS = 150
FALLBACK_RING_RADII = [0.60, 1.20, 1.80, 2.50, 3.50]

# ── Swept parameters ──────────────────────────────────────────────────────────
BFS_MARGINS           = [0.10, 0.15, 0.20]
SPAWN_INTER_DRONE_MINS = [0.20, 0.35, 0.50]
GOAL_SPAWN_CLEARANCES  = [1.0, 1.5, 2.0]
SC_GOAL_MIN_DISTS      = [5.0, 6.0, 7.0, 8.0]
DENSITIES              = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]
SPAWN_MODES            = ["clustered", "scattered"]

NUM_WORKERS = 4  # use 4 cores


# ── Map generation ────────────────────────────────────────────────────────────

def random_goal_and_start(rng, sc_goal_min_dist):
    goal = rng.uniform(2.0, 18.0, size=2)
    for _ in range(200):
        sc = rng.uniform(2.0, 18.0, size=2)
        if np.linalg.norm(sc - goal) > sc_goal_min_dist:
            return goal, sc
    sc = np.clip(np.array([FIELD_W, FIELD_H]) - goal, 2.0, 18.0)
    return goal, sc


def generate_obstacles(target_density, goal, sc, rng):
    target_area = FIELD_W * FIELD_H * target_density
    obs = []
    raster_res = 0.05
    rw = int(FIELD_W / raster_res)
    rh = int(FIELD_H / raster_res)
    occupied = np.zeros((rw, rh), dtype=bool)
    cur_area = 0.0

    for _ in range(3000):
        if cur_area >= target_area:
            break

        ch = rng.random()
        if ch < 0.2:
            r = rng.uniform(1.5, 2.5)
        elif ch < 0.6:
            r = rng.uniform(0.6, 1.4)
        else:
            r = rng.uniform(0.2, 0.5)

        lo   = r + MIN_WALL_GAP
        hi_x = FIELD_W - r - MIN_WALL_GAP
        hi_y = FIELD_H - r - MIN_WALL_GAP
        if lo >= hi_x or lo >= hi_y:
            continue
        cx = rng.uniform(lo, hi_x)
        cy = rng.uniform(lo, hi_y)

        if np.linalg.norm([cx, cy] - goal) <= r + OBSTACLE_CLEARANCE_FROM_SC:
            continue
        if np.linalg.norm([cx, cy] - sc) <= r + OBSTACLE_CLEARANCE_FROM_SC:
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

        cur_area += newly_covered * raster_res**2
        occupied[xmin:xmax, ymin:ymax] |= new_cells
        obs.append((cx, cy, r))

    return obs, cur_area / (FIELD_W * FIELD_H)


# ── BFS ───────────────────────────────────────────────────────────────────────

def build_grid(obstacles, bfs_clearance, grid_res=0.2):
    gs = int(np.ceil(FIELD_W / grid_res))
    grid = np.ones((gs, gs), dtype=bool)
    cx_all = np.arange(gs) * grid_res + grid_res / 2
    CX, CY = np.meshgrid(cx_all, cx_all, indexing='ij')
    for ox, oy, orad in obstacles:
        xm = max(0, int((ox - orad - bfs_clearance) / grid_res))
        xM = min(gs, int((ox + orad + bfs_clearance) / grid_res) + 1)
        ym = max(0, int((oy - orad - bfs_clearance) / grid_res))
        yM = min(gs, int((oy + orad + bfs_clearance) / grid_res) + 1)
        patch = (CX[xm:xM, ym:yM] - ox)**2 + (CY[xm:xM, ym:yM] - oy)**2 < (orad + bfs_clearance)**2
        grid[xm:xM, ym:yM] &= ~patch
    return grid, gs


def bfs_reachable(grid, gs, start, goal, grid_res=0.2):
    def to_cell(p):
        return (int(np.clip(p[0] / grid_res, 0, gs - 1)),
                int(np.clip(p[1] / grid_res, 0, gs - 1)))

    sc_c, gc_c = to_cell(start), to_cell(goal)
    if not grid[sc_c] or not grid[gc_c]:
        return False

    q, vis = deque([sc_c]), {sc_c}
    while q:
        x, y = q.popleft()
        if (x, y) == gc_c:
            return True
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < gs and 0 <= ny < gs and grid[nx, ny] and (nx, ny) not in vis:
                vis.add((nx, ny))
                q.append((nx, ny))
    return False


# ── Spawn simulation ──────────────────────────────────────────────────────────

def simulate_spawn(sc, obstacles, goal, rng, spawn_mode,
                   inter_drone_min, goal_spawn_clearance):
    """
    Mirrors reset() spawn logic for both modes.
    Returns (positions, fallback_count, discard_reason).
    discard_reason is None if spawn is clean, else a string explanation.
    fallback_count tracks absolute last-resort placements (no obstacle check).
    """
    positions  = np.zeros((N_DRONES, 2), dtype=np.float32)
    fallback_count = 0

    for i in range(N_DRONES):
        placed = False

        if spawn_mode == "clustered":
            for search_radius in CLUSTERED_RADII:
                for _ in range(CLUSTERED_ATTEMPTS):
                    p = rng.uniform(sc - search_radius, sc + search_radius)
                    p = np.clip(p, 0.6, 19.4)
                    inter_ok = all(np.linalg.norm(p - positions[j]) >= inter_drone_min
                                   for j in range(i))
                    obs_ok   = all(np.linalg.norm(p - np.array([ox, oy])) >= (SPAWN_OBSTACLE_CLEARANCE + orad)
                                   for ox, oy, orad in obstacles)
                    if inter_ok and obs_ok:
                        positions[i] = p
                        placed = True
                        break
                if placed:
                    break
        else:  # scattered
            for _ in range(SCATTERED_ATTEMPTS):
                p = rng.uniform(1.0, 19.0, size=2)
                p = np.clip(p, 0.6, 19.4)
                inter_ok = all(np.linalg.norm(p - positions[j]) >= inter_drone_min
                               for j in range(i))
                obs_ok   = all(np.linalg.norm(p - np.array([ox, oy])) >= (SPAWN_OBSTACLE_CLEARANCE + orad)
                               for ox, oy, orad in obstacles)
                if inter_ok and obs_ok:
                    positions[i] = p
                    placed = True
                    break

        if not placed:
            # Ring fallback with obstacle check
            angle = i * (2.0 * np.pi / N_DRONES)
            for r_dist in FALLBACK_RING_RADII:
                p = np.clip(
                    sc + np.array([r_dist * np.cos(angle), r_dist * np.sin(angle)]),
                    0.6, 19.4)
                obs_ok = all(np.linalg.norm(p - np.array([ox, oy])) >= (SPAWN_OBSTACLE_CLEARANCE + orad)
                             for ox, oy, orad in obstacles)
                if obs_ok:
                    positions[i] = p
                    placed = True
                    break

        if not placed:
            # Absolute last resort — no obstacle check
            angle = i * (2.0 * np.pi / N_DRONES)
            p = np.clip(
                sc + np.array([0.60 * np.cos(angle), 0.60 * np.sin(angle)]),
                0.6, 19.4)
            fallback_count += 1

            # Check goal distance — fallback offset can violate minimum separation
            if np.linalg.norm(p - goal) < goal_spawn_clearance:
                return positions, fallback_count, \
                    f"drone_{i} fallback violates goal_spawn_clearance"

            positions[i] = p
            # Discard: fallback placed without obstacle check
            return positions, fallback_count, \
                f"drone_{i} placed via absolute fallback (no obstacle check)"

    return positions, fallback_count, None  # clean spawn


# ── Per-combination worker (for multiprocessing) ───────────────────────────────

def run_combination_worker(args):
    """
    Worker function for ProcessPoolExecutor.
    Takes (maps, bfs_clearance, spawn_mode, inter_drone_min, goal_spawn_clearance, sc_goal_min_dist)
    Returns list of result dicts (one per density).
    """
    maps, bfs_clearance, spawn_mode, inter_drone_min, goal_spawn_clearance, sc_goal_min_dist = args

    results = []

    for d in DENSITIES:
        maps_for_d = [(obs, actual_d, sc, goal, rng_seed)
                      for (dd, obs, actual_d, sc, goal, rng_seed) in maps if dd == d]

        clean_drone_successes = 0
        total_clean_maps      = 0
        total_discarded       = 0
        total_fallbacks       = 0
        maps_all10_ok         = 0

        for obs, actual_d, sc, goal, rng_seed in maps_for_d:
            spawn_rng = np.random.default_rng(
                seed=rng_seed + (0 if spawn_mode == "clustered" else 500000))

            positions, fallback_count, discard_reason = simulate_spawn(
                sc, obs, goal, spawn_rng, spawn_mode,
                inter_drone_min, goal_spawn_clearance)

            total_fallbacks += fallback_count

            if discard_reason is not None:
                total_discarded += 1
                continue  # do not count toward solvability

            # Clean spawn — check BFS for all 10 drones
            total_clean_maps += 1
            grid, gs = build_grid(obs, bfs_clearance)
            drones_ok = sum(1 for i in range(N_DRONES)
                            if bfs_reachable(grid, gs, positions[i], goal))
            clean_drone_successes += drones_ok
            if drones_ok == N_DRONES:
                maps_all10_ok += 1

        # Infeasibility check
        infeasible = clean_drone_successes < INFEASIBILITY_THRESHOLD

        pct_all10 = (maps_all10_ok / total_clean_maps * 100) if total_clean_maps > 0 else 0.0
        avg_drone_ok = (clean_drone_successes / total_clean_maps) \
                       if total_clean_maps > 0 else 0.0
        avg_actual = np.mean([x[1] for x in maps_for_d])
        avg_obs    = np.mean([len(x[0]) for x in maps_for_d])

        results.append({
            "density"            : d,
            "spawn_mode"         : spawn_mode,
            "bfs_clearance"      : bfs_clearance,
            "inter_drone_min"    : inter_drone_min,
            "goal_spawn_clearance": goal_spawn_clearance,
            "sc_goal_min_dist"   : sc_goal_min_dist,
            "pct_all10_ok"       : pct_all10,
            "avg_drone_ok"       : avg_drone_ok,
            "clean_drone_successes": clean_drone_successes,
            "total_clean_maps"   : total_clean_maps,
            "total_discarded"    : total_discarded,
            "total_fallbacks"    : total_fallbacks,
            "avg_actual_density" : avg_actual,
            "avg_obs_count"      : avg_obs,
            "infeasible"         : infeasible,
        })

    return (sc_goal_min_dist, goal_spawn_clearance, bfs_clearance, inter_drone_min, spawn_mode), results


def recommended_ceiling(results):
    """First density where pct_all10_ok < 90%, take previous. None if all pass."""
    for i, r in enumerate(results):
        if r["infeasible"]:
            return DENSITIES[max(0, i - 1)] if i > 0 else None, "INFEASIBLE"
        if r["pct_all10_ok"] < 90.0:
            return DENSITIES[max(0, i - 1)] if i > 0 else None, "below_90pct"
    return DENSITIES[-1], "all_pass"


# ── Main ──────────────────────────────────────────────────────────────────────

def run_sweep():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path  = f"density_sweep_v2_results_{timestamp}.csv"

    print("=" * 80)
    print("Density Sweep v2 — 10-Drone Strict Solvability (4-core multiprocessing)")
    print("=" * 80)
    print(f"Field={FIELD_W}x{FIELD_H}m  N_Drones={N_DRONES}  "
          f"Maps/Combination={MAPS_PER_COMBINATION}  Workers={NUM_WORKERS}")
    print(f"Infeasibility threshold: clean_drone_successes < {INFEASIBILITY_THRESHOLD} "
          f"(out of {MAPS_PER_COMBINATION * N_DRONES})")
    print(f"Acceptance: ALL {N_DRONES}/{N_DRONES} drones BFS-reachable (strict)")
    print(f"CSV output: {csv_path}")
    print()

    csv_fields = [
        "sc_goal_min_dist", "goal_spawn_clearance", "bfs_clearance",
        "inter_drone_min", "spawn_mode", "density",
        "pct_all10_ok", "avg_drone_ok", "clean_drone_successes",
        "total_clean_maps", "total_discarded", "total_fallbacks",
        "avg_actual_density", "avg_obs_count", "infeasible",
        "recommended_ceiling", "ceiling_reason"
    ]

    all_csv_rows = []
    summary_rows = []

    param_combos = list(itertools.product(
        SC_GOAL_MIN_DISTS, GOAL_SPAWN_CLEARANCES, BFS_MARGINS,
        SPAWN_INTER_DRONE_MINS, SPAWN_MODES))

    total_combos = len(param_combos)
    print(f"Total parameter combinations: {total_combos}")
    print(f"Generating map pools per (sc_goal_min_dist, goal_spawn_clearance)...\n")

    # Group combos by (sc_goal_min_dist, goal_spawn_clearance) to share map pools
    map_pool_keys = list(itertools.product(SC_GOAL_MIN_DISTS, GOAL_SPAWN_CLEARANCES))
    map_pools = {}

    for sc_dist, gs_clr in map_pool_keys:
        pool = []
        for i in range(MAPS_PER_COMBINATION):
            for d in DENSITIES:
                rng_seed = i * 100000 + int(d * 1000) * 100 + int(sc_dist * 10) * 10 + int(gs_clr * 100)
                rng = np.random.default_rng(seed=rng_seed)
                goal, sc = random_goal_and_start(rng, sc_dist)
                obs, actual_d = generate_obstacles(d, goal, sc, rng)
                pool.append((d, obs, actual_d, sc, goal, rng_seed))
        map_pools[(sc_dist, gs_clr)] = pool
        print(f"  Pool ready: sc_goal_min_dist={sc_dist}  goal_spawn_clearance={gs_clr}  "
              f"({len(pool)} maps)")

    print()
    print("Running combinations with multiprocessing...\n")

    # Prepare worker arguments
    worker_args = []
    for sc_dist, gs_clr, bfs_margin, inter_min, spawn_mode in param_combos:
        bfs_clr = 2 * DRONE_RADIUS + bfs_margin
        maps    = map_pools[(sc_dist, gs_clr)]
        worker_args.append((maps, bfs_clr, spawn_mode, inter_min, gs_clr, sc_dist))

    # Run combinations in parallel
    with open(csv_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_fields)
        writer.writeheader()

        with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
            futures = [executor.submit(run_combination_worker, args) for args in worker_args]

            completed = 0
            for future in futures:
                params, results = future.result()
                sc_dist, gs_clr, bfs_clr, inter_min, spawn_mode = params
                completed += 1

                print(f"[{completed}/{total_combos}] "
                      f"sc_goal={sc_dist}  goal_clr={gs_clr}  "
                      f"bfs={bfs_clr:.2f}  inter={inter_min}  mode={spawn_mode}")

                ceil, reason = recommended_ceiling(results)

                print(f"  {'Density':>8} | {'All10%':>7} | {'AvgOK':>6} | "
                      f"{'CleanMaps':>10} | {'Discarded':>9} | {'Fallbacks':>9} | {'Infeasible':>10}")
                print("  " + "-" * 75)

                for r in results:
                    inf_marker = " INFEASIBLE" if r["infeasible"] else ""
                    print(f"  {r['density']:>8.2f} | {r['pct_all10_ok']:>6.1f}% | "
                          f"{r['avg_drone_ok']:>5.1f}/10 | "
                          f"{r['total_clean_maps']:>10} | {r['total_discarded']:>9} | "
                          f"{r['total_fallbacks']:>9} | {str(r['infeasible']):>10}{inf_marker}")

                    row = {**r,
                           "recommended_ceiling": ceil if ceil is not None else "NONE",
                           "ceiling_reason"     : reason}
                    writer.writerow(row)
                    csvfile.flush()
                    all_csv_rows.append(row)

                print(f"  -> Ceiling: {ceil}  ({reason})\n")

                summary_rows.append({
                    "sc_goal_min_dist"   : sc_dist,
                    "goal_spawn_clearance": gs_clr,
                    "bfs_clearance"      : bfs_clr,
                    "inter_drone_min"    : inter_min,
                    "spawn_mode"         : spawn_mode,
                    "ceiling"            : ceil,
                    "reason"             : reason,
                })

    # ── Final summary ─────────────────────────────────────────────────────────
    print("=" * 80)
    print("FINAL SUMMARY — Conservative ceiling = min(clustered, scattered)")
    print("=" * 80)
    print(f"{'sc_dist':>7} | {'gs_clr':>6} | {'bfs_clr':>7} | {'inter':>5} | "
          f"{'clustered':>10} | {'scattered':>10} | {'conservative':>13}")
    print("-" * 75)

    # Pair clustered and scattered for each param combo
    seen = set()
    for r in summary_rows:
        key = (r["sc_goal_min_dist"], r["goal_spawn_clearance"],
               r["bfs_clearance"], r["inter_drone_min"])
        if key in seen:
            continue
        seen.add(key)

        c_row = next((x for x in summary_rows if
                      x["sc_goal_min_dist"] == key[0] and
                      x["goal_spawn_clearance"] == key[1] and
                      x["bfs_clearance"] == key[2] and
                      x["inter_drone_min"] == key[3] and
                      x["spawn_mode"] == "clustered"), None)
        s_row = next((x for x in summary_rows if
                      x["sc_goal_min_dist"] == key[0] and
                      x["goal_spawn_clearance"] == key[1] and
                      x["bfs_clearance"] == key[2] and
                      x["inter_drone_min"] == key[3] and
                      x["spawn_mode"] == "scattered"), None)

        c_ceil = c_row["ceiling"] if c_row else None
        s_ceil = s_row["ceiling"] if s_row else None

        if c_ceil is not None and s_ceil is not None:
            conservative = min(c_ceil, s_ceil)
        else:
            conservative = "NONE"

        print(f"{key[0]:>7} | {key[1]:>6} | {key[2]:>7.2f} | {key[3]:>5} | "
              f"{str(c_ceil):>10} | {str(s_ceil):>10} | {str(conservative):>13}")

    print(f"\nFull results saved to: {csv_path}")


if __name__ == "__main__":
    run_sweep()