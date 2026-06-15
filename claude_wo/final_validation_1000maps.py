"""
Final IEEE Validation — density curve at 1000 maps/point, 5 independent batches
================================================================================
ONE shared environment config (verified from Stage 1 as top-tier for both
spawn modes — og=1.5/osc=1.5).  Only the spawn protocol differs between
clustered and scattered.  We sweep the density grid for each mode and report
the all-10-agent BFS-solvability curve with the ceiling marked.

This is the calibration figure + table for the paper.

Outputs:
  - Per-density mean ± std across 5 batches of 200 maps (= 1000 maps/point)
  - Ceiling (highest density with mean solvability >= 90%) per spawn mode
  - IEEE-ready summary line for each mode
  - final_validation_results_{timestamp}.csv
"""

import numpy as np
from collections import deque, defaultdict
import csv
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

# ══════════════════════════════════════════════════════════════════════════════
# CHOSEN CONFIG — single shared environment, both spawn modes
# Verified from Stage 1 (analyze_best_configs.py): og=1.5/osc=1.5 is the best
# defensible env config and is top-tier for BOTH spawn modes.  sc_g=5.0 keeps
# both modes bulletproof (clustered 100% @ 0.30, scattered ~98% @ 0.25).
# gc and inter are free spawn params (do not affect BFS) — fixed permissive.
# ══════════════════════════════════════════════════════════════════════════════

SHARED_ENV = {
    'obs_goal_clearance'       : 1.5,
    'obs_sc_clearance'         : 1.5,
    'spawn_obstacle_clearance' : 0.50,
    'sc_goal_min_dist'         : 5.0,
    'goal_spawn_clearance'     : 1.0,    # free param
    'bfs_clearance'            : 0.40,   # margin = 0.10
    'inter_drone_min'          : 0.20,   # free param
}

MODES             = ['clustered', 'scattered']
VALIDATE_DENSITIES = [0.15, 0.20, 0.25, 0.30, 0.35]   # curve around the ceiling

# Expected ceilings (Stage 1) — confirmed/refined by this run:
#   clustered -> 0.30,  scattered -> 0.25

# ══════════════════════════════════════════════════════════════════════════════

FIELD_W, FIELD_H  = 20.0, 20.0
DRONE_RADIUS      = 0.15
N_DRONES          = 10
N_BATCHES         = 5
MAPS_PER_BATCH    = 200           # total = 1000 maps per (mode, density)
NUM_WORKERS       = 6
# Seed space layout (non-overlapping):
#   S1 seeds   :          0 →   495,322,000
#   S2 cluster : 500,000,000 → 2,495,322,000
#   S2 scatter : 2,500,000,000 → 4,495,322,000
#   Final val  : 5,000,000,000 → 5,284,019,900
#     seed = SEED_BASE + mode_idx*2e8 + density_idx*2e7 + batch*1e6 + map_i*100
SEED_BASE         = 5_000_000_000

CLUSTERED_RADII    = [1.5, 2.0, 2.5, 3.5]
CLUSTERED_ATTEMPTS = 150
SCATTERED_ATTEMPTS = 150
FALLBACK_RING_RADII = [0.60, 1.20, 1.80, 2.50, 3.50]


# ── Map generation ────────────────────────────────────────────────────────────

def random_goal_and_start(rng, sc_goal_min_dist):
    goal = rng.uniform(2.0, 18.0, size=2)
    for _ in range(200):
        sc = rng.uniform(2.0, 18.0, size=2)
        if np.linalg.norm(sc - goal) > sc_goal_min_dist:
            return goal, sc
    sc = np.clip(np.array([FIELD_W, FIELD_H]) - goal, 2.0, 18.0)
    return goal, sc


def generate_obstacles(target_density, goal, sc, rng, ogc, osc):
    target_area = FIELD_W * FIELD_H * target_density
    obs, cur_area = [], 0.0
    raster_res = 0.05
    rw, rh = int(FIELD_W / raster_res), int(FIELD_H / raster_res)
    occupied = np.zeros((rw, rh), dtype=bool)

    for _ in range(3000):
        if cur_area >= target_area:
            break
        ch = rng.random()
        r = rng.uniform(1.5, 2.5) if ch < 0.2 else \
            rng.uniform(0.6, 1.4) if ch < 0.6 else rng.uniform(0.2, 0.5)

        lo_x, hi_x = r, FIELD_W - r
        lo_y, hi_y = r, FIELD_H - r
        if lo_x >= hi_x or lo_y >= hi_y:
            continue
        cx, cy = rng.uniform(lo_x, hi_x), rng.uniform(lo_y, hi_y)

        if np.linalg.norm([cx, cy] - goal) <= r + ogc:
            continue
        if np.linalg.norm([cx, cy] - sc) <= r + osc:
            continue

        xmin = max(0, int((cx - r) / raster_res))
        xmax = min(rw, int((cx + r) / raster_res) + 1)
        ymin = max(0, int((cy - r) / raster_res))
        ymax = min(rh, int((cy + r) / raster_res) + 1)
        lx = np.arange(xmin, xmax) * raster_res + raster_res / 2
        ly = np.arange(ymin, ymax) * raster_res + raster_res / 2
        LX, LY = np.meshgrid(lx, ly, indexing='ij')
        new_cells = (LX - cx)**2 + (LY - cy)**2 <= r**2
        newly = np.sum(new_cells & ~occupied[xmin:xmax, ymin:ymax])
        if newly == 0:
            continue
        cur_area += newly * raster_res**2
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
        patch = ((CX[xm:xM, ym:yM] - ox)**2 +
                 (CY[xm:xM, ym:yM] - oy)**2) < (orad + bfs_clearance)**2
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
                if dx != 0 and dy != 0:
                    if not grid[x + dx, y] or not grid[x, y + dy]:
                        continue
                vis.add((nx, ny))
                q.append((nx, ny))
    return False


# ── Spawn ─────────────────────────────────────────────────────────────────────

def simulate_spawn(sc, obstacles, goal, rng, cfg):
    positions = np.zeros((N_DRONES, 2), dtype=np.float32)
    soc  = cfg['spawn_obstacle_clearance']
    inter = cfg['inter_drone_min']
    gc   = cfg['goal_spawn_clearance']
    mode = cfg['spawn_mode']
    fallback_count = 0

    for i in range(N_DRONES):
        placed = False

        if mode == 'clustered':
            for search_radius in CLUSTERED_RADII:
                for _ in range(CLUSTERED_ATTEMPTS):
                    p = rng.uniform(sc - search_radius, sc + search_radius)
                    p = np.clip(p, 0.6, 19.4)
                    if (all(np.linalg.norm(p - positions[j]) >= inter for j in range(i)) and
                        all(np.linalg.norm(p - np.array([ox, oy])) >= soc + orad
                            for ox, oy, orad in obstacles) and
                        np.linalg.norm(p - goal) >= gc):
                        positions[i] = p
                        placed = True
                        break
                if placed:
                    break
        else:
            for _ in range(SCATTERED_ATTEMPTS):
                p = rng.uniform(1.0, 19.0, size=2)
                p = np.clip(p, 0.6, 19.4)
                if (all(np.linalg.norm(p - positions[j]) >= inter for j in range(i)) and
                    all(np.linalg.norm(p - np.array([ox, oy])) >= soc + orad
                        for ox, oy, orad in obstacles) and
                    np.linalg.norm(p - goal) >= gc):
                    positions[i] = p
                    placed = True
                    break

        if not placed:
            angle = i * (2.0 * np.pi / N_DRONES)
            for r_dist in FALLBACK_RING_RADII:
                p = np.clip(sc + np.array([r_dist * np.cos(angle), r_dist * np.sin(angle)]),
                            0.6, 19.4)
                if all(np.linalg.norm(p - np.array([ox, oy])) >= soc + orad
                       for ox, oy, orad in obstacles):
                    positions[i] = p
                    placed = True
                    break

        if not placed:
            angle = i * (2.0 * np.pi / N_DRONES)
            p = np.clip(sc + np.array([0.60 * np.cos(angle), 0.60 * np.sin(angle)]),
                        0.6, 19.4)
            fallback_count += 1
            if np.linalg.norm(p - goal) < gc:
                return positions, fallback_count, "fallback violates goal_spawn_clearance"
            positions[i] = p
            return positions, fallback_count, "absolute fallback"

    return positions, fallback_count, None


# ── Batch worker ──────────────────────────────────────────────────────────────

def run_batch(args):
    """One batch of MAPS_PER_BATCH maps at a fixed (mode, density)."""
    cfg, density, seed_base = args
    ogc = cfg['obs_goal_clearance']
    osc = cfg['obs_sc_clearance']
    sc_dist = cfg['sc_goal_min_dist']
    bfs_clr = cfg['bfs_clearance']
    grid_res = 0.2

    all10_ok = total_clean = total_disc = 0

    for i in range(MAPS_PER_BATCH):
        seed = seed_base + i * 100
        rng = np.random.default_rng(seed=seed)
        goal, sc = random_goal_and_start(rng, sc_dist)
        obs, _ = generate_obstacles(density, goal, sc, rng, ogc, osc)

        spawn_rng = np.random.default_rng(seed=seed + 1)
        positions, fb, discard = simulate_spawn(sc, obs, goal, spawn_rng, cfg)
        if discard:
            total_disc += 1
            continue

        grid, gs = build_grid(obs, bfs_clr)
        if any(not grid[int(np.clip(positions[k][0] / grid_res, 0, gs - 1)),
                       int(np.clip(positions[k][1] / grid_res, 0, gs - 1))]
               for k in range(N_DRONES)):
            total_disc += 1
            continue

        total_clean += 1
        ok = sum(1 for k in range(N_DRONES)
                 if bfs_reachable(grid, gs, positions[k], goal))
        if ok == N_DRONES:
            all10_ok += 1

    pct = (all10_ok / total_clean * 100) if total_clean > 0 else 0.0
    return density, pct, total_clean, total_disc


# ── Validate one spawn mode across the density grid ────────────────────────────

def validate_mode(env, mode, mode_idx):
    cfg = dict(env)
    cfg['spawn_mode'] = mode
    print(f"\n{'='*70}")
    print(f"{mode.upper()} — density sweep, {N_BATCHES}×{MAPS_PER_BATCH} = "
          f"{N_BATCHES*MAPS_PER_BATCH} maps per density")
    print(f"{'='*70}")
    for k, v in cfg.items():
        print(f"  {k:28s} = {v}")
    print()

    # Submit every (density, batch) job up front for full core utilisation.
    jobs = []
    for di, density in enumerate(VALIDATE_DENSITIES):
        for b in range(N_BATCHES):
            seed_base = (SEED_BASE + mode_idx * 200_000_000 +
                         di * 20_000_000 + b * 1_000_000)
            jobs.append((cfg, density, seed_base))

    per_density = defaultdict(list)   # density -> [(pct, clean, disc), ...]
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = [executor.submit(run_batch, j) for j in jobs]
        for future in as_completed(futures):
            density, pct, clean, disc = future.result()
            per_density[density].append((pct, clean, disc))

    # Summarise per density and locate the ceiling.
    print(f"  {'density':>8} | {'mean%':>7} | {'std%':>6} | {'95%CI':>14} | "
          f"{'clean':>6} | {'disc':>5}")
    print("  " + "-" * 62)
    rows = []
    ceiling = None
    for density in VALIDATE_DENSITIES:
        pcts = [p for p, _, _ in per_density[density]]
        clean = sum(c for _, c, _ in per_density[density])
        disc = sum(d for _, _, d in per_density[density])
        mean = float(np.mean(pcts))
        std = float(np.std(pcts, ddof=1))
        ci = 1.96 * std / np.sqrt(N_BATCHES)
        rows.append({'density': density, 'mean': mean, 'std': std, 'ci': ci,
                     'clean': clean, 'disc': disc, 'pcts': pcts})
        mark = ""
        if mean >= 90.0:
            ceiling = density            # highest density still >= 90%
        else:
            mark = "  <-- below 90%"
        print(f"  {density:>8.2f} | {mean:>6.2f}% | {std:>5.2f}% | "
              f"[{mean-ci:>5.1f},{mean+ci:>5.1f}] | {clean:>6} | {disc:>5}{mark}")

    print(f"\n  >>> {mode.upper()} CEILING = {ceiling}  "
          f"(highest density with mean all-10 solvability >= 90%)")
    if ceiling is not None:
        cr = next(r for r in rows if r['density'] == ceiling)
        print(f"  IEEE line: \"{mode}: {cr['mean']:.1f}% ± {cr['std']:.1f}% "
              f"all-agent solvability at d={ceiling} "
              f"({N_BATCHES*MAPS_PER_BATCH} maps, 95% CI: "
              f"[{cr['mean']-cr['ci']:.1f}%, {cr['mean']+cr['ci']:.1f}%])\"")

    return rows, ceiling


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = f"final_validation_results_{timestamp}.csv"

    print("=" * 70)
    print("Final IEEE Validation — density curve, 1000 maps/point, shared config")
    print("=" * 70)

    all_rows = {}
    ceilings = {}
    for mode_idx, mode in enumerate(MODES):
        rows, ceiling = validate_mode(SHARED_ENV, mode, mode_idx)
        all_rows[mode] = rows
        ceilings[mode] = ceiling

    # Write per-batch CSV (one row per mode×density×batch — the raw evidence).
    with open(out_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['mode', 'density', 'batch', 'pct_all10_ok',
                         'mean_pct', 'std_pct', 'ci95',
                         'obs_goal_clearance', 'obs_sc_clearance',
                         'spawn_obstacle_clearance', 'sc_goal_min_dist',
                         'bfs_clearance', 'goal_spawn_clearance', 'inter_drone_min'])
        for mode in MODES:
            for r in all_rows[mode]:
                for b, pct in enumerate(r['pcts']):
                    writer.writerow([
                        mode, r['density'], b + 1, f"{pct:.4f}",
                        f"{r['mean']:.4f}", f"{r['std']:.4f}", f"{r['ci']:.4f}",
                        SHARED_ENV['obs_goal_clearance'], SHARED_ENV['obs_sc_clearance'],
                        SHARED_ENV['spawn_obstacle_clearance'], SHARED_ENV['sc_goal_min_dist'],
                        SHARED_ENV['bfs_clearance'], SHARED_ENV['goal_spawn_clearance'],
                        SHARED_ENV['inter_drone_min']])

    print(f"\n{'='*70}")
    print("FINAL SUMMARY — shared env config (og=1.5, osc=1.5, sp=0.50, sc_g=5.0, bfs=0.40)")
    print(f"{'='*70}")
    for mode in MODES:
        ceil = ceilings[mode]
        if ceil is not None:
            cr = next(r for r in all_rows[mode] if r['density'] == ceil)
            print(f"  {mode:10s}: ceiling = {ceil}  ->  {cr['mean']:.1f}% ± {cr['std']:.1f}% "
                  f"(95% CI [{cr['mean']-cr['ci']:.1f}%, {cr['mean']+cr['ci']:.1f}%])")
        else:
            print(f"  {mode:10s}: no density reached 90% — check config")

    print(f"\nResults saved to: {out_csv}")


if __name__ == "__main__":
    run()
