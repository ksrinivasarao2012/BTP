"""
Stage 2 — CLUSTERED mode, 200 maps
====================================
Reads Stage 1 results from existing CSV.
Filter: S1 ceiling >= 0.30 AND og != 1.0.
Runs 200 fresh maps per surviving combo using a seed space completely
separate from Stage 1 (offset = 500,000,000; S1 max seed = 495,322,000).

Seed space layout (non-overlapping):
  S1 seeds   :         0 →   495,322,000
  S2 cluster : 500,000,000 → 2,495,322,000   (this script)
  S2 scatter : 2,500,000,000 → 4,495,322,000 (stage2_scattered_200maps.py)
  Final val  : 5,000,000,000 → 5,004,019,900 (final_validation_1000maps.py)
"""

import numpy as np
from collections import deque
import csv
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

# ── Constants ─────────────────────────────────────────────────────────────────
FIELD_W, FIELD_H   = 20.0, 20.0
DRONE_RADIUS       = 0.15
N_DRONES           = 10
DENSITIES          = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]
MAPS_PER_COMBO     = 200
NUM_WORKERS        = 6
# S1 max seed = 49*10M + 5*1M + 3*100K + 2*10K + 2*1K = 495,322,000
# S2 internal range with 200 maps = 0 → 199*10M + 5*1M + 3*100K + 2*10K + 2*1K = 1,995,322,000
# S2 clustered range = 500,000,000 → 2,495,322,000  (no overlap with S1)
SEED_OFFSET        = 500_000_000

CLUSTERED_RADII    = [1.5, 2.0, 2.5, 3.5]
CLUSTERED_ATTEMPTS = 150
FALLBACK_RING_RADII = [0.60, 1.20, 1.80, 2.50, 3.50]

# ── Filter thresholds ─────────────────────────────────────────────────────────
S1_CSV             = "density_sweep_v5_results_20260608_153206.csv"
# Target ceiling = 0.30: some og=1.5/2.0 combos DO show ceiling=0.30 in S1 (≈906
# combos when og=1.0 is excluded). Stage 1 ceiling labels are noisy at 50 maps
# (95% CI = ±6.9pp at p=90%), so Stage 2 (200 maps, CI ±3.4pp) is the
# authoritative re-classification.  Combos that are truly ceiling=0.25 will be
# correctly relabelled after 200 maps; the ranking then surfaces the real winners.
S2_TARGET_CEILING  = 0.30
# S2_MIN_PCT_AT_CEIL is redundant when S2_TARGET_CEILING = 0.30: ceiling=0.30 is
# defined as pct@0.30 >= 90% in S1, so every survivor already passes 80%.
# Set to 0.0 to make the selection logic explicit.
S2_MIN_PCT_AT_CEIL = 0.0
# obs_goal_clearance = 1.0 is excluded for three compounding reasons:
#   1. Physical margin: obstacle surface at 1.0m from goal, BFS inflation = 0.40m →
#      navigable boundary at 0.60m from goal center. With goal arrival radius ~0.5m,
#      the margin between "drone arrived" and "BFS obstacle wall" is only 0.10m —
#      one BFS grid cell (grid_res=0.2m), which is below reliable path resolution.
#   2. Multi-agent congestion: 10 drones converge on a single goal simultaneously.
#      At og=1.0, the obstacle-free zone around the goal is insufficient to hold 10
#      drones in final approach without triggering cascade collisions, undermining
#      the RL reward signal near the terminal state.
#   3. IEEE defensibility: og=1.5 and og=2.0 provide a clear physical rationale
#      ("10× and 13× drone radius obstacle-free zone") that reviewers can verify.
#      og=1.0 cannot be justified without extensive ablation — not worth the risk.
EXCLUDE_OBS_GOAL   = {1.0}

# ── Parameter lists (for index-based seed formula) ────────────────────────────
OBS_GOAL_CLEARANCES       = [1.0, 1.5, 2.0]
OBS_SC_CLEARANCES         = [1.5, 2.0, 2.5]
SPAWN_OBSTACLE_CLEARANCES = [0.40, 0.45, 0.50]
SC_GOAL_MIN_DISTS         = [5.0, 6.0, 7.0, 8.0]
GOAL_SPAWN_CLEARANCES     = [1.0, 1.5, 2.0]
BFS_MARGINS               = [0.10, 0.15, 0.20]
SPAWN_INTER_DRONE_MINS    = [0.20, 0.35, 0.50]


# ── Stage 1 filter ────────────────────────────────────────────────────────────

def load_s1_clustered_survivors(csv_path):
    """
    Returns list of param-tuples that pass the Stage 2 filter for clustered mode.
    Each tuple: (ogc, osc, soc, sc_dist, gs_clr, bfs_margin, inter_min)
    """
    combos = {}
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            if r['stage'] != '1' or r['spawn_mode'] != 'clustered':
                continue
            key = (
                float(r['obs_goal_clearance']),
                float(r['obs_sc_clearance']),
                float(r['spawn_obstacle_clearance']),
                float(r['sc_goal_min_dist']),
                float(r['goal_spawn_clearance']),
                float(r['bfs_clearance']),
                float(r['inter_drone_min']),
            )
            if key not in combos:
                combos[key] = {'ceiling': r['recommended_ceiling'], 'by_density': {}}
            combos[key]['by_density'][r['density']] = float(r['pct_all10_ok'])

    survivors = []
    for key, data in combos.items():
        ogc = key[0]
        if ogc in EXCLUDE_OBS_GOAL:
            continue
        ceil = data['ceiling']
        if ceil == 'NONE':
            continue
        if float(ceil) < S2_TARGET_CEILING:
            continue
        pct = data['by_density'].get(str(S2_TARGET_CEILING),
              data['by_density'].get(f'{S2_TARGET_CEILING:.2f}', 0.0))
        if pct >= S2_MIN_PCT_AT_CEIL:
            survivors.append(key)

    return survivors


# ── Map generation ────────────────────────────────────────────────────────────

def random_goal_and_start(rng, sc_goal_min_dist):
    goal = rng.uniform(2.0, 18.0, size=2)
    for _ in range(200):
        sc = rng.uniform(2.0, 18.0, size=2)
        if np.linalg.norm(sc - goal) > sc_goal_min_dist:
            return goal, sc
    sc = np.clip(np.array([FIELD_W, FIELD_H]) - goal, 2.0, 18.0)
    return goal, sc


def generate_obstacles(target_density, goal, sc, rng, obs_goal_clearance, obs_sc_clearance):
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


# ── Clustered spawn ───────────────────────────────────────────────────────────

def simulate_clustered_spawn(sc, obstacles, goal, rng,
                              inter_drone_min, goal_spawn_clearance,
                              spawn_obstacle_clearance):
    positions = np.zeros((N_DRONES, 2), dtype=np.float32)
    fallback_count = 0

    for i in range(N_DRONES):
        placed = False
        for search_radius in CLUSTERED_RADII:
            for _ in range(CLUSTERED_ATTEMPTS):
                p = rng.uniform(sc - search_radius, sc + search_radius)
                p = np.clip(p, 0.6, 19.4)
                if (all(np.linalg.norm(p - positions[j]) >= inter_drone_min for j in range(i)) and
                    all(np.linalg.norm(p - np.array([ox, oy])) >= spawn_obstacle_clearance + orad
                        for ox, oy, orad in obstacles) and
                    np.linalg.norm(p - goal) >= goal_spawn_clearance):
                    positions[i] = p
                    placed = True
                    break
            if placed:
                break

        if not placed:
            angle = i * (2.0 * np.pi / N_DRONES)
            for r_dist in FALLBACK_RING_RADII:
                p = np.clip(sc + np.array([r_dist * np.cos(angle), r_dist * np.sin(angle)]),
                            0.6, 19.4)
                if all(np.linalg.norm(p - np.array([ox, oy])) >= spawn_obstacle_clearance + orad
                       for ox, oy, orad in obstacles):
                    positions[i] = p
                    placed = True
                    break

        if not placed:
            angle = i * (2.0 * np.pi / N_DRONES)
            p = np.clip(sc + np.array([0.60 * np.cos(angle), 0.60 * np.sin(angle)]),
                        0.6, 19.4)
            fallback_count += 1
            if np.linalg.norm(p - goal) < goal_spawn_clearance:
                return positions, fallback_count, f"drone_{i} fallback violates goal_spawn_clearance"
            positions[i] = p
            return positions, fallback_count, f"drone_{i} absolute fallback"

    return positions, fallback_count, None


# ── Worker ────────────────────────────────────────────────────────────────────

def worker(args):
    ogc, osc, soc, sc_dist, gs_clr, bfs_clr, inter_min, maps = args
    grid_res = 0.2
    results = []

    for d in DENSITIES:
        maps_d = [(obs, ad, sc, goal, seed) for (dd, obs, ad, sc, goal, seed) in maps if dd == d]
        clean_ok = total_clean = total_disc = total_fb = all10_ok = 0
        sum_ad = sum_obs = 0.0

        for obs, actual_d, sc, goal, seed in maps_d:
            rng = np.random.default_rng(seed=seed)
            positions, fb, discard = simulate_clustered_spawn(
                sc, obs, goal, rng, inter_min, gs_clr, soc)
            total_fb += fb
            if discard:
                total_disc += 1
                continue

            grid, gs = build_grid(obs, bfs_clr)
            if any(not grid[int(np.clip(positions[i][0] / grid_res, 0, gs - 1)),
                           int(np.clip(positions[i][1] / grid_res, 0, gs - 1))]
                   for i in range(N_DRONES)):
                total_disc += 1
                continue

            total_clean += 1
            sum_ad += actual_d
            sum_obs += len(obs)
            ok = sum(1 for i in range(N_DRONES)
                     if bfs_reachable(grid, gs, positions[i], goal))
            clean_ok += ok
            if ok == N_DRONES:
                all10_ok += 1

        n = len(maps_d)
        scaled_thresh = 150 * (total_clean / n) if n > 0 else 0
        infeasible = (total_clean == 0) or (clean_ok < scaled_thresh)
        pct = (all10_ok / total_clean * 100) if total_clean > 0 else 0.0
        avg_ok = (clean_ok / total_clean) if total_clean > 0 else 0.0
        avg_ad = (sum_ad / total_clean) if total_clean > 0 else 0.0
        avg_obs = (sum_obs / total_clean) if total_clean > 0 else 0.0
        fb_rate = total_fb / (total_clean + total_disc) if (total_clean + total_disc) > 0 else 0.0

        results.append({
            'density': d, 'pct_all10_ok': pct, 'avg_drone_ok': avg_ok,
            'clean_drone_successes': clean_ok, 'total_clean_maps': total_clean,
            'total_discarded': total_disc, 'total_fallbacks': total_fb,
            'avg_fallback_rate': fb_rate, 'avg_actual_density': avg_ad,
            'avg_obs_count': avg_obs, 'infeasible': infeasible,
        })

    # Recommended ceiling
    ceil, reason = None, 'all_pass'
    for i, r in enumerate(results):
        if r['infeasible']:
            ceil = DENSITIES[i - 1] if i > 0 else None
            reason = 'INFEASIBLE'
            break
        if r['pct_all10_ok'] < 90.0:
            ceil = DENSITIES[i - 1] if i > 0 else None
            reason = 'below_90pct'
            break
    if ceil is None and reason == 'all_pass':
        ceil = DENSITIES[-1]

    return (ogc, osc, soc, sc_dist, gs_clr, bfs_clr, inter_min), results, ceil, reason


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = f"stage2_clustered_{timestamp}.csv"

    print("=" * 70)
    print("Stage 2 — CLUSTERED mode, 200 maps")
    print("=" * 70)
    print(f"Loading Stage 1 results from: {S1_CSV}")

    survivors = load_s1_clustered_survivors(S1_CSV)
    print(f"Combos passing filter (og!=1.0, S1 ceiling>={S2_TARGET_CEILING}, pct@d={S2_TARGET_CEILING}>={S2_MIN_PCT_AT_CEIL}%): {len(survivors)}")
    if not survivors:
        print("No survivors. Loosen S2_MIN_PCT_AT_CEIL or S2_TARGET_CEILING.")
        return

    # Generate 200 fresh maps per unique (ogc, osc, sc_dist)
    print("\nGenerating map pools...")
    pool_keys = list({(k[0], k[1], k[3]) for k in survivors})
    map_pools = {}
    for ogc, osc, sc_dist in pool_keys:
        pool = []
        for i in range(MAPS_PER_COMBO):
            for d in DENSITIES:
                d_i   = DENSITIES.index(d)
                sc_i  = SC_GOAL_MIN_DISTS.index(sc_dist)
                ogc_i = OBS_GOAL_CLEARANCES.index(ogc)
                osc_i = OBS_SC_CLEARANCES.index(osc)
                seed  = (SEED_OFFSET +
                         i          * 10_000_000 +
                         d_i        *  1_000_000 +
                         sc_i       *    100_000 +
                         ogc_i      *     10_000 +
                         osc_i      *      1_000)
                rng = np.random.default_rng(seed=seed)
                goal, sc = random_goal_and_start(rng, sc_dist)
                obs, actual_d = generate_obstacles(d, goal, sc, rng, ogc, osc)
                pool.append((d, obs, actual_d, sc, goal, seed))
        map_pools[(ogc, osc, sc_dist)] = pool
    print(f"Generated {len(map_pools)} map pools.\n")

    csv_fields = [
        'obs_goal_clearance', 'obs_sc_clearance', 'spawn_obstacle_clearance',
        'sc_goal_min_dist', 'goal_spawn_clearance', 'bfs_clearance', 'inter_drone_min',
        'density', 'pct_all10_ok', 'avg_drone_ok', 'clean_drone_successes',
        'total_clean_maps', 'total_discarded', 'total_fallbacks', 'avg_fallback_rate',
        'avg_actual_density', 'avg_obs_count', 'infeasible',
        'recommended_ceiling', 'ceiling_reason',
    ]

    summary = []
    completed = 0
    total = len(survivors)

    with open(out_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()

        worker_args = []
        for ogc, osc, soc, sc_dist, gs_clr, bfs_clr, inter_min in survivors:
            bfs_margin = round(bfs_clr - 2 * DRONE_RADIUS, 4)
            maps = map_pools[(ogc, osc, sc_dist)]
            worker_args.append((ogc, osc, soc, sc_dist, gs_clr, bfs_clr, inter_min, maps))

        with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
            futures = [executor.submit(worker, a) for a in worker_args]
            for future in as_completed(futures):
                params, results, ceil, reason = future.result()
                ogc, osc, soc, sc_dist, gs_clr, bfs_clr, inter_min = params
                completed += 1
                print(f"[{completed}/{total}] og={ogc} osc={osc} sp={soc} "
                      f"sc_g={sc_dist} gc={gs_clr} bfs={bfs_clr:.2f} inter={inter_min} "
                      f"-> ceil={ceil} ({reason})")
                for r in results:
                    row = {**r,
                           'obs_goal_clearance': ogc, 'obs_sc_clearance': osc,
                           'spawn_obstacle_clearance': soc, 'sc_goal_min_dist': sc_dist,
                           'goal_spawn_clearance': gs_clr, 'bfs_clearance': bfs_clr,
                           'inter_drone_min': inter_min,
                           'recommended_ceiling': ceil if ceil else 'NONE',
                           'ceiling_reason': reason}
                    writer.writerow(row)
                f.flush()
                summary.append({'params': params, 'ceil': ceil, 'reason': reason,
                                 'results': results})

    # ── Final ranking ─────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("FINAL RANKING — Clustered, sorted by pct_all10_ok at ceiling density")
    print("=" * 70)

    def score(entry):
        if not entry['ceil'] or entry['ceil'] == 'NONE':
            return (-1, 0, 0)
        ceil_d = str(entry['ceil'])
        r_at_ceil = next((r for r in entry['results']
                          if str(r['density']) == ceil_d), None)
        pct = r_at_ceil['pct_all10_ok'] if r_at_ceil else 0
        clean = r_at_ceil['total_clean_maps'] if r_at_ceil else 0
        disc = r_at_ceil['total_discarded'] if r_at_ceil else 0
        return (float(entry['ceil']), pct, clean, -disc)

    ranked = sorted(summary, key=score, reverse=True)
    print(f"\n{'Rank':>4} | {'og':>4} | {'osc':>4} | {'sp':>5} | {'sc_g':>5} | "
          f"{'gc':>4} | {'bfs':>5} | {'inter':>5} | {'ceil':>6} | {'pct@ceil':>9} | "
          f"{'95%CI':>8} | {'clean':>6}")
    print("-" * 100)
    for rank, entry in enumerate(ranked[:20], 1):
        p = entry['params']
        ceil_d = str(entry['ceil'])
        r_at_ceil = next((r for r in entry['results']
                          if str(r['density']) == ceil_d), None)
        pct = r_at_ceil['pct_all10_ok'] if r_at_ceil else 0
        clean = r_at_ceil['total_clean_maps'] if r_at_ceil else 0
        p_frac = pct / 100.0
        ci = 1.96 * ((p_frac * (1 - p_frac) / max(clean, 1)) ** 0.5) * 100
        print(f"{rank:>4} | {p[0]:>4} | {p[1]:>4} | {p[2]:>5} | {p[3]:>5} | "
              f"{p[4]:>4} | {p[5]:>5.2f} | {p[6]:>5} | {str(entry['ceil']):>6} | "
              f"{pct:>8.1f}% | ±{ci:>5.1f}% | {clean:>6}")
    print("\n  Note: configs within ±3.5pp of the top are statistically equivalent at n=200."
          "\n  goal_spawn_clearance and inter_drone_min are free parameters — they do not"
          "\n  affect BFS feasibility. The top env config is (og, osc, sp, sc_g, bfs).")

    print(f"\nFull results saved to: {out_csv}")
    print("\n*** TOP CONFIG FOR IEEE (copy to final_validation_1000maps.py) ***")
    best = ranked[0]
    p = best['params']
    print(f"  obs_goal_clearance       = {p[0]}")
    print(f"  obs_sc_clearance         = {p[1]}")
    print(f"  spawn_obstacle_clearance = {p[2]}")
    print(f"  sc_goal_min_dist         = {p[3]}")
    print(f"  goal_spawn_clearance     = {p[4]}")
    print(f"  bfs_clearance            = {p[5]:.2f}")
    print(f"  inter_drone_min          = {p[6]}")
    print(f"  spawn_mode               = clustered")
    print(f"  recommended_ceiling      = {best['ceil']}")


if __name__ == "__main__":
    run()
