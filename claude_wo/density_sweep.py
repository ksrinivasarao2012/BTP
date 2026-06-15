"""
Density Sweep — finds the correct obstacle density ceiling for 20x20 training field.

Matches the actual training environment exactly:
  - Goal and start positions are random each map (like real training)
  - Goal and start clearance same as v15 _generate_obstacles
  - Obstacle wall clearance bug fixed (surface stays inside field)
  - BFS solvability checked with 2 * DRONE_RADIUS + margin    , sweeping margin in [0.10, 0.15, 0.20]
"""

import numpy as np
from collections import deque

FIELD_W      = 20.0
FIELD_H      = 20.0
DRONE_RADIUS = 0.15
MAPS_PER_DENSITY = 200

# --- Clearances (same as v15) ---
GOAL_CLEARANCE  = 2.00
START_CLEARANCE = 2.00

# Fixed wall clearance bug: obstacle surface must stay inside field
MIN_WALL_GAP = 0.20

# BFS clearance margins to sweep: drone sees obstacle as blocked within 2 * DRONE_RADIUS + margin    
BFS_MARGINS = [0.10, 0.15, 0.20]


def random_goal_and_start(rng):
    goal = rng.uniform(2.0, 18.0, size=2)
    for _ in range(200):
        sc = rng.uniform(2.0, 18.0, size=2)
        if np.linalg.norm(sc - goal) > 7.0:
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

        # Wall clearance fix: sample so surface stays >= MIN_WALL_GAP from edge
        lo   = r + MIN_WALL_GAP
        hi_x = FIELD_W - r - MIN_WALL_GAP
        hi_y = FIELD_H - r - MIN_WALL_GAP
        if lo >= hi_x or lo >= hi_y:
            continue
        cx = rng.uniform(lo, hi_x)
        cy = rng.uniform(lo, hi_y)

        if np.linalg.norm([cx, cy] - goal) <= r + GOAL_CLEARANCE:
            continue
        if np.linalg.norm([cx, cy] - sc) <= r + START_CLEARANCE:
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


def is_solvable(obstacles, start, goal, bfs_clearance):
    grid_res = 0.2
    gs = int(np.ceil(FIELD_W / grid_res))
    grid = np.ones((gs, gs), dtype=bool)

    for ox, oy, orad in obstacles:
        xm = max(0, int((ox - orad - bfs_clearance) / grid_res))
        xM = min(gs, int((ox + orad + bfs_clearance) / grid_res) + 1)
        ym = max(0, int((oy - orad - bfs_clearance) / grid_res))
        yM = min(gs, int((oy + orad + bfs_clearance) / grid_res) + 1)
        for gx in range(xm, xM):
            for gy in range(ym, yM):
                cx_c = gx * grid_res + grid_res / 2
                cy_c = gy * grid_res + grid_res / 2
                if np.sqrt((cx_c - ox)**2 + (cy_c - oy)**2) < orad + bfs_clearance:
                    grid[gx, gy] = False

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


def run_sweep():
    densities = [0.10, 0.15, 0.20, 0.25, 0.30,0.35]

    print(f"GOAL_CLEARANCE={GOAL_CLEARANCE}m  START_CLEARANCE={START_CLEARANCE}m  "
          f"MIN_WALL_GAP={MIN_WALL_GAP}m  Maps={MAPS_PER_DENSITY}  Field={FIELD_W}x{FIELD_H}m")
    print()

    # Pre-generate all maps once, reuse across BFS margin sweep
    all_maps = []
    for i in range(MAPS_PER_DENSITY):
        for d in densities:
            rng = np.random.default_rng(seed=i * 1000 + int(d * 100))
            goal, sc = random_goal_and_start(rng)
            obs, actual_d = generate_obstacles(d, goal, sc, rng)
            all_maps.append((d, obs, actual_d, sc, goal))

    for margin in BFS_MARGINS:
        bfs_clearance = 2 *  DRONE_RADIUS + margin    
        print(f"=== BFS clearance = 2 * DRONE_RADIUS + {margin} = {bfs_clearance:.2f}m ===")
        print(f"{'Target':>8} | {'Solvable%':>10} | {'Actual Density':>14} | {'Avg #Obs':>9}")
        print("-" * 50)

        recommended = None

        for d in densities:
            maps_for_d = [(obs, actual_d, sc, goal) for (dd, obs, actual_d, sc, goal) in all_maps if dd == d]
            solved = sum(1 for obs, _, sc, goal in maps_for_d if is_solvable(obs, sc, goal, bfs_clearance))
            avg_actual = np.mean([actual_d for _, actual_d, _, _ in maps_for_d])
            avg_obs    = np.mean([len(obs) for obs, _, _, _ in maps_for_d])
            solvability = solved / len(maps_for_d) * 100

            marker = " <-- below 90%" if solvability < 90 and recommended is None else ""
            if solvability < 90 and recommended is None:
                recommended = densities[max(0, densities.index(d) - 1)]

            print(f"{d:>8.2f} | {solvability:>9.1f}% | {avg_actual:>14.3f} | {avg_obs:>9.1f}{marker}")

        if recommended is None:
            recommended = densities[-1]

        print(f"  -> Recommended ceiling: {recommended:.2f}")
        print()


if __name__ == "__main__":
    run_sweep()
