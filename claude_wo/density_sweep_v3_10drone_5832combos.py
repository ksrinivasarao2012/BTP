"""
Density Sweep v5 — 10-Drone Strict Solvability Check (5832 combos)
====================================================================
Finds the correct obstacle density ceiling for the 20x20m training field.

FIXES APPLIED (over v4):
1. Seed collision — index-based formula, each parameter in a non-overlapping decimal band.
2. Pool key efficiency — goal_spawn_clearance removed from pool key (36 pools: ogc×osc×scd).
3. futures blocking — as_completed() used for non-blocking parallel iteration.
4. obs_clearance_from_sc split — goal and spawn-center clearances now independent parameters.
5. Spawn/BFS clearance consistency — spawn cells validated against BFS grid before counting.
6. MIN_WALL_GAPS removed — obstacle boundary constraint now handled geometrically (r only).
   Obstacles guaranteed inside field: center sampled in [r, FIELD-r], surface never exits.
7. Diagonal corner-cutting fix — BFS now checks side cells before allowing diagonal moves.

Swept parameters (5832 = 3^6 × 4 × 2 combinations):
  OBS_GOAL_CLEARANCES       [1.0, 1.5, 2.0]      obstacle-free zone around goal
  OBS_SC_CLEARANCES         [1.5, 2.0, 2.5]      obstacle-free zone around spawn center
  SPAWN_OBSTACLE_CLEARANCES [0.40, 0.45, 0.50]   drone center to obstacle during spawn
  BFS_MARGINS               [0.10, 0.15, 0.20]   added to 2*drone_radius for BFS inflation
  SPAWN_INTER_DRONE_MINS    [0.20, 0.35, 0.50]   minimum inter-drone spacing at spawn
  GOAL_SPAWN_CLEARANCES     [1.0, 1.5, 2.0]      goal proximity check (fallback only)
  SC_GOAL_MIN_DISTS         [5.0, 6.0, 7.0, 8.0] minimum start-center to goal distance
  SPAWN_MODES               clustered / scattered

Other features:
  - Strict: all 10 drone spawn positions BFS-checked individually
  - Infeasibility threshold scaled to actual clean maps
  - Fallback spawns discard the map entirely
  - 6-core multiprocessing
  - Vectorized build_grid (np.meshgrid, 10× speedup)
  - Two-stage: Stage 1 (50 maps) → filter → Stage 2 (200 maps) on survivors
"""

import numpy as np
from collections import deque
import csv
import itertools
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

# ── Fixed constants ───────────────────────────────────────────────────────────
FIELD_W       = 20.0
FIELD_H       = 20.0
DRONE_RADIUS  = 0.15
N_DRONES      = 10
MAPS_PER_COMBINATION_S1 = 50    # Stage 1: quick survey
MAPS_PER_COMBINATION_S2 = 200   # Stage 2: deep validation
INFEASIBILITY_THRESHOLD = 150   # out of 50*10=500 for Stage 1

CLUSTERED_RADII    = [1.5, 2.0, 2.5, 3.5]
CLUSTERED_ATTEMPTS = 150
SCATTERED_ATTEMPTS = 150
FALLBACK_RING_RADII = [0.60, 1.20, 1.80, 2.50, 3.50]

# ── Swept parameters ──────────────────────────────────────────────────────────
OBS_GOAL_CLEARANCES       = [1.0, 1.5, 2.0]
OBS_SC_CLEARANCES         = [1.5, 2.0, 2.5]
SPAWN_OBSTACLE_CLEARANCES = [0.40, 0.45, 0.50]
BFS_MARGINS               = [0.10, 0.15, 0.20]
SPAWN_INTER_DRONE_MINS    = [0.20, 0.35, 0.50]
GOAL_SPAWN_CLEARANCES     = [1.0, 1.5, 2.0]
SC_GOAL_MIN_DISTS         = [5.0, 6.0, 7.0, 8.0]
DENSITIES                 = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]
SPAWN_MODES               = ["clustered", "scattered"]

NUM_WORKERS = 6

# Stage 1 → Stage 2 filter thresholds
S2_MIN_CEILING     = 0.20   # ceiling must be >= 0.20 to proceed to Stage 2
S2_MAX_FALLBACK_RT = 0.25   # fallback rate must be < 25% of maps
S2_MAX_CEIL_DIFF   = 0.10   # clustered vs scattered ceiling diff must be <= 0.10


# ── Map generation ────────────────────────────────────────────────────────────

def random_goal_and_start(rng, sc_goal_min_dist):
    goal = rng.uniform(2.0, 18.0, size=2)
    for _ in range(200):
        sc = rng.uniform(2.0, 18.0, size=2)
        if np.linalg.norm(sc - goal) > sc_goal_min_dist:
            return goal, sc
    sc = np.clip(np.array([FIELD_W, FIELD_H]) - goal, 2.0, 18.0)
    return goal, sc


def generate_obstacles(target_density, goal, sc, rng,
                       obs_goal_clearance, obs_sc_clearance):
    """
    Obstacles guaranteed inside field: center sampled in [r, FIELD-r].
    Surface at minimum touches wall edge, never exits. No min_wall_gap needed.
    """
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

        # Geometric guarantee: center in [r, FIELD-r] → surface in [0, FIELD]
        # Surface never exits field boundary. No artificial gap needed.
        lo_x, hi_x = r, FIELD_W - r
        lo_y, hi_y = r, FIELD_H - r
        if lo_x >= hi_x or lo_y >= hi_y:
            continue
        cx = rng.uniform(lo_x, hi_x)
        cy = rng.uniform(lo_y, hi_y)

        if np.linalg.norm([cx, cy] - goal) <= r + obs_goal_clearance:
            continue
        if np.linalg.norm([cx, cy] - sc) <= r + obs_sc_clearance:
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
                # FIX: prevent diagonal corner cutting
                # Check both side cells are free before allowing diagonal move
                if dx != 0 and dy != 0:
                    if not grid[x + dx, y] or not grid[x, y + dy]:
                        continue
                vis.add((nx, ny))
                q.append((nx, ny))
    return False


# ── Spawn simulation ──────────────────────────────────────────────────────────

def simulate_spawn(sc, obstacles, goal, rng, spawn_mode,
                   inter_drone_min, goal_spawn_clearance, spawn_obstacle_clearance):
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
                    obs_ok   = all(np.linalg.norm(p - np.array([ox, oy])) >= (spawn_obstacle_clearance + orad)
                                   for ox, oy, orad in obstacles)
                    goal_ok  = np.linalg.norm(p - goal) >= goal_spawn_clearance
                    if inter_ok and obs_ok and goal_ok:
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
                obs_ok   = all(np.linalg.norm(p - np.array([ox, oy])) >= (spawn_obstacle_clearance + orad)
                               for ox, oy, orad in obstacles)
                goal_ok  = np.linalg.norm(p - goal) >= goal_spawn_clearance
                if inter_ok and obs_ok and goal_ok:
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
                obs_ok = all(np.linalg.norm(p - np.array([ox, oy])) >= (spawn_obstacle_clearance + orad)
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

            if np.linalg.norm(p - goal) < goal_spawn_clearance:
                return positions, fallback_count, \
                    f"drone_{i} fallback violates goal_spawn_clearance"

            positions[i] = p
            return positions, fallback_count, \
                f"drone_{i} placed via absolute fallback (no obstacle check)"

    return positions, fallback_count, None


# ── Per-combination worker ────────────────────────────────────────────────────

def run_combination_worker(args):
    maps, bfs_clearance, spawn_mode, inter_drone_min, goal_spawn_clearance, sc_goal_min_dist, \
        obs_goal_clearance, obs_sc_clearance, spawn_obstacle_clearance = args

    results = []

    for d in DENSITIES:
        maps_for_d = [(obs, actual_d, sc, goal, rng_seed)
                      for (dd, obs, actual_d, sc, goal, rng_seed) in maps if dd == d]

        clean_drone_successes = 0
        total_clean_maps      = 0
        total_discarded       = 0
        total_fallbacks       = 0
        maps_all10_ok         = 0
        sum_actual_density    = 0.0
        sum_obs_count         = 0

        for obs, actual_d, sc, goal, rng_seed in maps_for_d:
            spawn_rng = np.random.default_rng(
                seed=rng_seed + (0 if spawn_mode == "clustered" else 500000))

            positions, fallback_count, discard_reason = simulate_spawn(
                sc, obs, goal, spawn_rng, spawn_mode,
                inter_drone_min, goal_spawn_clearance, spawn_obstacle_clearance)

            total_fallbacks += fallback_count

            if discard_reason is not None:
                total_discarded += 1
                continue

            grid, gs = build_grid(obs, bfs_clearance)

            # Discard if any drone's spawn cell is inside BFS-inflated obstacle region
            grid_res = 0.2
            spawn_in_blocked = any(
                not grid[int(np.clip(positions[i][0] / grid_res, 0, gs - 1)),
                         int(np.clip(positions[i][1] / grid_res, 0, gs - 1))]
                for i in range(N_DRONES)
            )
            if spawn_in_blocked:
                total_discarded += 1
                continue

            total_clean_maps += 1
            sum_actual_density += actual_d
            sum_obs_count += len(obs)
            drones_ok = sum(1 for i in range(N_DRONES)
                            if bfs_reachable(grid, gs, positions[i], goal))
            clean_drone_successes += drones_ok
            if drones_ok == N_DRONES:
                maps_all10_ok += 1

        # Scale threshold to actual clean maps to handle high discard rates
        n_maps = len(maps_for_d)
        scaled_threshold = INFEASIBILITY_THRESHOLD * (total_clean_maps / n_maps) if n_maps > 0 else 0
        infeasible = (total_clean_maps == 0) or (clean_drone_successes < scaled_threshold)

        pct_all10    = (maps_all10_ok / total_clean_maps * 100) if total_clean_maps > 0 else 0.0
        avg_drone_ok = (clean_drone_successes / total_clean_maps) if total_clean_maps > 0 else 0.0
        avg_actual   = (sum_actual_density / total_clean_maps) if total_clean_maps > 0 else 0.0
        avg_obs      = (sum_obs_count / total_clean_maps) if total_clean_maps > 0 else 0.0

        results.append({
            "density"                 : d,
            "spawn_mode"              : spawn_mode,
            "bfs_clearance"           : bfs_clearance,
            "inter_drone_min"         : inter_drone_min,
            "goal_spawn_clearance"    : goal_spawn_clearance,
            "sc_goal_min_dist"        : sc_goal_min_dist,
            "obs_goal_clearance"      : obs_goal_clearance,
            "obs_sc_clearance"        : obs_sc_clearance,
            "spawn_obstacle_clearance": spawn_obstacle_clearance,
            "pct_all10_ok"            : pct_all10,
            "avg_drone_ok"            : avg_drone_ok,
            "clean_drone_successes"   : clean_drone_successes,
            "total_clean_maps"        : total_clean_maps,
            "total_discarded"         : total_discarded,
            "total_fallbacks"         : total_fallbacks,
            "avg_actual_density"      : avg_actual,
            "avg_obs_count"           : avg_obs,
            "infeasible"              : infeasible,
        })

    return (sc_goal_min_dist, goal_spawn_clearance, bfs_clearance, inter_drone_min,
            spawn_mode, obs_goal_clearance, obs_sc_clearance, spawn_obstacle_clearance), results


def recommended_ceiling(results):
    for i, r in enumerate(results):
        if r["infeasible"]:
            return DENSITIES[max(0, i - 1)] if i > 0 else None, "INFEASIBLE"
        if r["pct_all10_ok"] < 90.0:
            return DENSITIES[max(0, i - 1)] if i > 0 else None, "below_90pct"
    return DENSITIES[-1], "all_pass"


# ── Stage 1 → Stage 2 filter ─────────────────────────────────────────────────

def should_proceed_to_stage2(c_ceil, s_ceil, summary_rows, key):
    """
    Returns True if this parameter combination passes Stage 1 filters
    and should be re-run with 200 maps in Stage 2.
    """
    if c_ceil is None or s_ceil is None:
        return False

    conservative = min(c_ceil, s_ceil)

    # Filter 1: ceiling too low
    if conservative < S2_MIN_CEILING:
        return False

    # Filter 2: clustered vs scattered ceiling too different
    if abs(c_ceil - s_ceil) > S2_MAX_CEIL_DIFF:
        return False

    # Filter 3: high fallback rate in either mode
    for mode in ["clustered", "scattered"]:
        row = next((x for x in summary_rows if
                    x["obs_goal_clearance"]       == key[0] and
                    x["obs_sc_clearance"]          == key[1] and
                    x["spawn_obstacle_clearance"]  == key[2] and
                    x["sc_goal_min_dist"]          == key[3] and
                    x["goal_spawn_clearance"]      == key[4] and
                    x["bfs_clearance"]             == key[5] and
                    x["inter_drone_min"]           == key[6] and
                    x["spawn_mode"] == mode), None)
        if row and row["avg_fallback_rate"] >= S2_MAX_FALLBACK_RT:
            return False

    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def run_stage(stage_num, maps_per_combo, param_combos, map_pools,
              csv_writer, csv_file, total_combos):
    summary_rows = []
    completed = 0

    # Build worker args
    worker_args = []
    for ogc, osc, soc, sc_dist, gs_clr, bfs_margin, inter_min, spawn_mode in param_combos:
        bfs_clr = 2 * DRONE_RADIUS + bfs_margin
        maps    = map_pools[(ogc, osc, sc_dist)]
        # Trim or extend pool to match maps_per_combo
        maps_trimmed = [(d, obs, actual_d, sc, goal, rng_seed)
                        for (d, obs, actual_d, sc, goal, rng_seed) in maps][:maps_per_combo * len(DENSITIES)]
        worker_args.append((maps_trimmed, bfs_clr, spawn_mode, inter_min, gs_clr,
                            sc_dist, ogc, osc, soc))

    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = [executor.submit(run_combination_worker, args) for args in worker_args]

        for future in as_completed(futures):
            params, results = future.result()
            sc_dist, gs_clr, bfs_clr, inter_min, spawn_mode, ogc, osc, soc = params
            completed += 1

            ceil, reason = recommended_ceiling(results)

            # Compute avg fallback rate across all density levels for this combo
            total_fb = sum(r["total_fallbacks"] for r in results)
            total_maps = sum(r["total_clean_maps"] + r["total_discarded"] for r in results)
            avg_fb_rate = total_fb / total_maps if total_maps > 0 else 0.0

            trigger_str = ""
            if reason in ("below_90pct", "INFEASIBLE"):
                for r in results:
                    if ceil is None or r["density"] > ceil:
                        trigger_str = f" | d={r['density']} pct={r['pct_all10_ok']:.1f}%"
                        break

            print(f"[S{stage_num} {completed}/{total_combos}] "
                  f"og={ogc} osc={osc} sp={soc} sc_g={sc_dist} "
                  f"gc={gs_clr} bfs={bfs_clr:.2f} inter={inter_min} mode={spawn_mode} "
                  f"-> ceil={ceil} ({reason}){trigger_str}")

            for r in results:
                row = {**r,
                       "stage"               : stage_num,
                       "recommended_ceiling" : ceil if ceil is not None else "NONE",
                       "ceiling_reason"      : reason,
                       "avg_fallback_rate"   : avg_fb_rate}
                csv_writer.writerow(row)
                csv_file.flush()

            summary_rows.append({
                "obs_goal_clearance"      : ogc,
                "obs_sc_clearance"        : osc,
                "spawn_obstacle_clearance": soc,
                "sc_goal_min_dist"        : sc_dist,
                "goal_spawn_clearance"    : gs_clr,
                "bfs_clearance"           : bfs_clr,
                "inter_drone_min"         : inter_min,
                "spawn_mode"              : spawn_mode,
                "ceiling"                 : ceil,
                "reason"                  : reason,
                "avg_fallback_rate"       : avg_fb_rate,
            })

    return summary_rows


def run_sweep():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path  = f"density_sweep_v5_results_{timestamp}.csv"

    total_combos = (len(OBS_GOAL_CLEARANCES) * len(OBS_SC_CLEARANCES) *
                    len(SPAWN_OBSTACLE_CLEARANCES) * len(BFS_MARGINS) *
                    len(SPAWN_INTER_DRONE_MINS) * len(GOAL_SPAWN_CLEARANCES) *
                    len(SC_GOAL_MIN_DISTS) * len(SPAWN_MODES))

    print("=" * 80)
    print("Density Sweep v5 — 10-Drone Strict Solvability (Two-Stage)")
    print("=" * 80)
    print(f"Field={FIELD_W}x{FIELD_H}m  N_Drones={N_DRONES}  Workers={NUM_WORKERS}")
    print(f"Stage 1: {total_combos} combos × {MAPS_PER_COMBINATION_S1} maps")
    print(f"Stage 2: filtered combos × {MAPS_PER_COMBINATION_S2} maps")
    print(f"CSV output: {csv_path}\n")
    print("FIXES:")
    print("1. MIN_WALL_GAPS removed — geometric guarantee: center in [r, FIELD-r]")
    print("2. Diagonal BFS corner-cutting fixed — side cells checked before diagonal moves")
    print("3. Seed collision fixed (index-based non-overlapping bands)")
    print("4. obs_goal_clearance / obs_sc_clearance decoupled")
    print("5. Two-stage filtering: Stage 1 surveys, Stage 2 validates survivors\n")

    csv_fields = [
        "stage", "obs_goal_clearance", "obs_sc_clearance", "spawn_obstacle_clearance",
        "sc_goal_min_dist", "goal_spawn_clearance", "bfs_clearance",
        "inter_drone_min", "spawn_mode", "density",
        "pct_all10_ok", "avg_drone_ok", "clean_drone_successes",
        "total_clean_maps", "total_discarded", "total_fallbacks", "avg_fallback_rate",
        "avg_actual_density", "avg_obs_count", "infeasible",
        "recommended_ceiling", "ceiling_reason"
    ]

    # Pool key: (ogc, osc, sc_dist) — only params that affect obstacle generation
    # 3×3×4 = 36 pools
    print("Generating 36 map pools (reused across bfs/inter/spawn_mode/goal_spawn_clr)...\n")

    map_pool_keys = list(itertools.product(
        OBS_GOAL_CLEARANCES, OBS_SC_CLEARANCES, SC_GOAL_MIN_DISTS))
    map_pools = {}

    # Generate enough maps for Stage 2 (200) upfront — Stage 1 uses first 50
    for ogc, osc, sc_dist in map_pool_keys:
        pool = []
        for i in range(MAPS_PER_COMBINATION_S2):
            for d in DENSITIES:
                d_i   = DENSITIES.index(d)
                sc_i  = SC_GOAL_MIN_DISTS.index(sc_dist)
                ogc_i = OBS_GOAL_CLEARANCES.index(ogc)
                osc_i = OBS_SC_CLEARANCES.index(osc)
                rng_seed = (i     * 10_000_000 +
                            d_i   *  1_000_000 +
                            sc_i  *    100_000 +
                            ogc_i *     10_000 +
                            osc_i *      1_000)
                rng = np.random.default_rng(seed=rng_seed)
                goal, sc = random_goal_and_start(rng, sc_dist)
                obs, actual_d = generate_obstacles(d, goal, sc, rng, ogc, osc)
                pool.append((d, obs, actual_d, sc, goal, rng_seed))
        map_pools[(ogc, osc, sc_dist)] = pool

    print(f"Generated {len(map_pools)} map pools (200 maps each).\n")

    param_combos = list(itertools.product(
        OBS_GOAL_CLEARANCES, OBS_SC_CLEARANCES, SPAWN_OBSTACLE_CLEARANCES,
        SC_GOAL_MIN_DISTS, GOAL_SPAWN_CLEARANCES, BFS_MARGINS,
        SPAWN_INTER_DRONE_MINS, SPAWN_MODES))

    with open(csv_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_fields)
        writer.writeheader()

        # ── Stage 1 ───────────────────────────────────────────────────────────
        print("=" * 80)
        print(f"STAGE 1 — Survey ({MAPS_PER_COMBINATION_S1} maps/combo, {total_combos} combos)")
        print("=" * 80)

        s1_summary = run_stage(1, MAPS_PER_COMBINATION_S1, param_combos,
                               map_pools, writer, csvfile, total_combos)

        # ── Stage 1 → Stage 2 filtering ──────────────────────────────────────
        print("\n" + "=" * 80)
        print("STAGE 1 FILTER — Selecting combos for Stage 2")
        print("=" * 80)

        seen = set()
        s2_combos = []
        for r in s1_summary:
            key = (r["obs_goal_clearance"], r["obs_sc_clearance"],
                   r["spawn_obstacle_clearance"], r["sc_goal_min_dist"],
                   r["goal_spawn_clearance"], r["bfs_clearance"], r["inter_drone_min"])
            if key in seen:
                continue
            seen.add(key)

            c_row = next((x for x in s1_summary if
                          x["obs_goal_clearance"]       == key[0] and
                          x["obs_sc_clearance"]          == key[1] and
                          x["spawn_obstacle_clearance"]  == key[2] and
                          x["sc_goal_min_dist"]          == key[3] and
                          x["goal_spawn_clearance"]      == key[4] and
                          x["bfs_clearance"]             == key[5] and
                          x["inter_drone_min"]           == key[6] and
                          x["spawn_mode"] == "clustered"), None)
            s_row = next((x for x in s1_summary if
                          x["obs_goal_clearance"]       == key[0] and
                          x["obs_sc_clearance"]          == key[1] and
                          x["spawn_obstacle_clearance"]  == key[2] and
                          x["sc_goal_min_dist"]          == key[3] and
                          x["goal_spawn_clearance"]      == key[4] and
                          x["bfs_clearance"]             == key[5] and
                          x["inter_drone_min"]           == key[6] and
                          x["spawn_mode"] == "scattered"), None)

            c_ceil = c_row["ceiling"] if c_row else None
            s_ceil = s_row["ceiling"] if s_row else None

            if should_proceed_to_stage2(c_ceil, s_ceil, s1_summary, key):
                # Add both spawn modes to Stage 2
                for spawn_mode in SPAWN_MODES:
                    s2_combos.append((key[0], key[1], key[2], key[3],
                                      key[4], key[5] - 2*DRONE_RADIUS,  # back to margin
                                      key[6], spawn_mode))
                conservative = min(c_ceil, s_ceil)
                print(f"  PASS og={key[0]} osc={key[1]} sp={key[2]} sc_g={key[3]} "
                      f"gc={key[4]} bfs={key[5]:.2f} inter={key[6]} "
                      f"c:{c_ceil} s:{s_ceil} -> {conservative}")
            else:
                conservative = min(c_ceil, s_ceil) if (c_ceil and s_ceil) else "NONE"
                print(f"  FAIL og={key[0]} osc={key[1]} sp={key[2]} sc_g={key[3]} "
                      f"gc={key[4]} bfs={key[5]:.2f} inter={key[6]} "
                      f"c:{c_ceil} s:{s_ceil} -> {conservative}")

        print(f"\n  Stage 1: {total_combos} combos → Stage 2: {len(s2_combos)} combos\n")

        # ── Stage 2 ───────────────────────────────────────────────────────────
        if s2_combos:
            print("=" * 80)
            print(f"STAGE 2 — Deep Validation ({MAPS_PER_COMBINATION_S2} maps/combo, {len(s2_combos)} combos)")
            print("=" * 80)

            s2_summary = run_stage(2, MAPS_PER_COMBINATION_S2, s2_combos,
                                   map_pools, writer, csvfile, len(s2_combos))
        else:
            print("No combos passed Stage 1 filters.")
            s2_summary = []

    # ── Final summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("FINAL SUMMARY (Stage 2) — Conservative ceiling = min(clustered, scattered)")
    print("=" * 80)

    seen = set()
    for r in s2_summary:
        key = (r["obs_goal_clearance"], r["obs_sc_clearance"],
               r["spawn_obstacle_clearance"], r["sc_goal_min_dist"],
               r["goal_spawn_clearance"], r["bfs_clearance"], r["inter_drone_min"])
        if key in seen:
            continue
        seen.add(key)

        c_row = next((x for x in s2_summary if
                      x["obs_goal_clearance"]       == key[0] and
                      x["obs_sc_clearance"]          == key[1] and
                      x["spawn_obstacle_clearance"]  == key[2] and
                      x["sc_goal_min_dist"]          == key[3] and
                      x["goal_spawn_clearance"]      == key[4] and
                      x["bfs_clearance"]             == key[5] and
                      x["inter_drone_min"]           == key[6] and
                      x["spawn_mode"] == "clustered"), None)
        s_row = next((x for x in s2_summary if
                      x["obs_goal_clearance"]       == key[0] and
                      x["obs_sc_clearance"]          == key[1] and
                      x["spawn_obstacle_clearance"]  == key[2] and
                      x["sc_goal_min_dist"]          == key[3] and
                      x["goal_spawn_clearance"]      == key[4] and
                      x["bfs_clearance"]             == key[5] and
                      x["inter_drone_min"]           == key[6] and
                      x["spawn_mode"] == "scattered"), None)

        c_ceil = c_row["ceiling"] if c_row else None
        s_ceil = s_row["ceiling"] if s_row else None
        conservative = min(c_ceil, s_ceil) if (c_ceil and s_ceil) else "NONE"

        print(f"og={key[0]:.1f} osc={key[1]:.1f} sp={key[2]:.2f} "
              f"sc_g={key[3]:.1f} gc={key[4]:.1f} bfs={key[5]:.2f} inter={key[6]:.2f} "
              f"| c:{str(c_ceil):>6} s:{str(s_ceil):>6} -> {str(conservative):>6}")

    print(f"\nFull results saved to: {csv_path}")


if __name__ == "__main__":
    run_sweep()