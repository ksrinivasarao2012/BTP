import os
import time
import random
import heapq
import numpy as np
import matplotlib.pyplot as plt
from collections import deque
from scipy.ndimage import distance_transform_edt

class TopologyValidator:
    """
    Validates benchmark topologies by generating maps and measuring
    geometric properties: BFS solvability, Minimum Corridor Width (W_min), and Path Tortuosity.
    """
    def __init__(self, width, height, density, num_maps=100, seed=42):
        self.WIDTH = float(width)
        self.HEIGHT = float(height)
        self.density = density
        self.num_maps = num_maps
        self.raster_res = 0.1
        self.rw = int(self.WIDTH / self.raster_res)
        self.rh = int(self.HEIGHT / self.raster_res)
        
        self.drone_radius = 0.15
        self.seed = seed
        
        self.stats = {
            "attempts": 0,
            "density_failures": 0,
            "reachability_rejections": 0,
            "corridor_rejections": 0,
            "pair_reachability_rejections": 0,
            "pair_corridor_rejections": 0,
            "valid_maps": 0,
            "w_path_mins": [],
            "w_smoothed_mins": [],
            "w_p10s": [],
            "w_means": [],
            "tortuosities": [],
            "actual_densities": [],
            "sample_occupancies": []
        }

    def _generate_obstacles(self):
        target_area = self.WIDTH * self.HEIGHT * self.density
        occupied = np.zeros((self.rw, self.rh), dtype=bool)
        current_area = 0.0

        MAX_ATTEMPTS = 5000
        MIN_NEW_AREA = 0.05

        rectangles = []

        for _ in range(MAX_ATTEMPTS):
            if current_area >= target_area:
                break

            is_rect = random.random() < 0.30
            
            if is_rect:
                if random.random() < 0.5:
                    w = random.uniform(4.0, 6.0)
                    h = random.uniform(0.4, 0.8)
                else:
                    w = random.uniform(0.4, 0.8)
                    h = random.uniform(4.0, 6.0)
                    
                cx = random.uniform(w / 2.0, self.WIDTH - w / 2.0)
                cy = random.uniform(h / 2.0, self.HEIGHT - h / 2.0)
                
                xmin, xmax = cx - w / 2.0, cx + w / 2.0
                ymin, ymax = cy - h / 2.0, cy + h / 2.0
                
                valid = True
                for rx1, ry1, rx2, ry2 in rectangles:
                    if not (
                        xmax + 0.5 < rx1 or
                        xmin - 0.5 > rx2 or
                        ymax + 0.5 < ry1 or
                        ymin - 0.5 > ry2
                    ):
                        valid = False
                        break
                        
                if not valid:
                    continue
                
                ixmin = max(0, int(xmin / self.raster_res))
                ixmax = min(self.rw, int(xmax / self.raster_res) + 1)
                iymin = max(0, int(ymin / self.raster_res))
                iymax = min(self.rh, int(ymax / self.raster_res) + 1)
                
                newly_covered_cells = np.sum(~occupied[ixmin:ixmax, iymin:iymax])
                newly_covered_area = newly_covered_cells * (self.raster_res**2)
                
                if newly_covered_area < MIN_NEW_AREA: continue
                
                current_area += newly_covered_area
                occupied[ixmin:ixmax, iymin:iymax] = True
                rectangles.append((xmin, ymin, xmax, ymax))
                
            else:
                ch = random.random()
                if ch < 0.214:
                    r = random.uniform(1.5, 2.5) # Large (15% total)
                elif ch < 0.714:
                    r = random.uniform(0.6, 1.4) # Medium (35% total)
                else:
                    r = random.uniform(0.2, 0.5) # Small (20% total)

                cx = random.uniform(r / 2.0, self.WIDTH - r / 2.0)
                cy = random.uniform(r / 2.0, self.HEIGHT - r / 2.0)

                xmin = max(0, int((cx - r) / self.raster_res))
                xmax = min(self.rw, int((cx + r) / self.raster_res) + 1)
                ymin = max(0, int((cy - r) / self.raster_res))
                ymax = min(self.rh, int((cy + r) / self.raster_res) + 1)

                lx = np.arange(xmin, xmax) * self.raster_res + self.raster_res / 2
                ly = np.arange(ymin, ymax) * self.raster_res + self.raster_res / 2
                LX, LY = np.meshgrid(lx, ly, indexing='ij')

                new_cells = (LX - cx)**2 + (LY - cy)**2 <= r**2
                newly_covered_cells = np.sum(new_cells & ~occupied[xmin:xmax, ymin:ymax])
                newly_covered_area = newly_covered_cells * (self.raster_res**2)
                
                if newly_covered_area < MIN_NEW_AREA:
                    continue

                current_area += newly_covered_area
                occupied[xmin:xmax, ymin:ymax] |= new_cells

        if current_area < target_area:
            return None # Guaranteed density failed

        actual_density = current_area / (self.WIDTH * self.HEIGHT)

        # Mark boundary walls as occupied
        occupied[0, :] = True; occupied[-1, :] = True
        occupied[:, 0] = True; occupied[:, -1] = True
        return occupied, actual_density

    def _analyze_map(self, dist_map, navigable, start_pos, goal_pos):
        sx = min(int(start_pos[0]/self.raster_res), self.rw-1)
        sy = min(int(start_pos[1]/self.raster_res), self.rh-1)
        gx = min(int(goal_pos[0]/self.raster_res), self.rw-1)
        gy = min(int(goal_pos[1]/self.raster_res), self.rh-1)
        
        if not navigable[sx, sy] or not navigable[gx, gy]:
            return None # Start or Goal is blocked by obstacle geometry
            
        # A* Algorithm on grid using Octile distance heuristic
        dist = np.full((self.rw, self.rh), np.inf, dtype=np.float32)
        dist[sx, sy] = 0
        
        dx_start = abs(sx - gx)
        dy_start = abs(sy - gy)
        h_start = max(dx_start, dy_start) + 0.414 * min(dx_start, dy_start)
        
        pq = [(h_start, 0.0, sx, sy)] # (f, g, x, y)
        parent = np.full((self.rw, self.rh, 2), -1, dtype=int)
        
        moves = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        move_costs = [1.0, 1.0, 1.0, 1.0, 1.414, 1.414, 1.414, 1.414]
        
        found = False
        closed = set()
        while pq:
            f, d, x, y = heapq.heappop(pq)
            
            if (x, y) in closed:
                continue
            closed.add((x, y))
            
            if d > dist[x, y]: continue
            if x == gx and y == gy:
                found = True
                break
                
            for (dx, dy), cost in zip(moves, move_costs):
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.rw and 0 <= ny < self.rh:
                    if navigable[nx, ny]:
                        # Diagonal corner cutting check
                        if dx != 0 and dy != 0:
                            if not (navigable[x + dx, y] and navigable[x, y + dy]):
                                continue # Blocked by orthogonal corners
                                
                        nd = d + cost
                        if nd < dist[nx, ny]:
                            dist[nx, ny] = nd
                            parent[nx, ny] = [x, y]
                            
                            dx_h = abs(nx - gx)
                            dy_h = abs(ny - gy)
                            h = max(dx_h, dy_h) + 0.414 * min(dx_h, dy_h)
                            
                            heapq.heappush(pq, (nd + h, nd, nx, ny))
                            
        if not found:
            return None # BFS Rejection (Unsolvable)
            
        # Reconstruct shortest path
        path = []
        curr = (gx, gy)
        while curr != (sx, sy):
            path.append(curr)
            px, py = parent[curr[0], curr[1]]
            curr = (px, py)
        path.append((sx, sy))
        
        # W_path metrics (width of corridor along path)
        path_dists = [dist_map[px, py] for px, py in path]
        
        w_min = 2.0 * min(path_dists)
        w_p10 = 2.0 * np.percentile(path_dists, 10)
        w_mean = 2.0 * np.mean(path_dists)
        
        # Smoothed w_min (moving average over 5 cells = 0.5m) to prevent single-pixel saturation
        window = 5
        if len(path_dists) >= window:
            smoothed_dists = np.convolve(path_dists, np.ones(window)/window, mode='valid')
            w_smoothed_min = 2.0 * min(smoothed_dists)
        else:
            w_smoothed_min = w_min
            
        # Corridor Rejection Filter (Stage 2)
        # MIN_SMOOTHED_CORRIDOR = ~1.33x drone diameter (Loosened to 0.40m for generation efficiency)
        MIN_SMOOTHED_CORRIDOR = 0.35
        if w_smoothed_min < MIN_SMOOTHED_CORRIDOR:
            return ("CORRIDOR_REJECT", w_smoothed_min)
        
        # Tortuosity = L_actual / L_euclidean
        l_actual = dist[gx, gy] * self.raster_res
        
        sx_world = sx * self.raster_res + self.raster_res / 2
        sy_world = sy * self.raster_res + self.raster_res / 2
        gx_world = gx * self.raster_res + self.raster_res / 2
        gy_world = gy * self.raster_res + self.raster_res / 2
        
        l_euclidean = np.linalg.norm([gx_world - sx_world, gy_world - sy_world])
        tortuosity = l_actual / l_euclidean
        
        return w_min, w_smoothed_min, w_p10, w_mean, tortuosity

    def run(self):
        random.seed(self.seed)
        np.random.seed(self.seed)
        
        print(f"\n--- Validating Regime: {self.WIDTH}x{self.HEIGHT} | Density: {self.density:.2f} ---")
        print(f"  [INFO] Computational Raster Resolution: {self.raster_res}m")
        t0 = time.time()
        
        while self.stats["valid_maps"] < self.num_maps:
            self.stats["attempts"] += 1
            
            if self.stats["attempts"] > 2000 and self.stats["valid_maps"] == 0:
                print(f"  [ABORT] Cannot generate valid maps. Thresholds too aggressive. Rejects: {self.stats['corridor_rejections']} corridor, {self.stats['density_failures']} density.", flush=True)
                break
                
            gen_result = self._generate_obstacles()
            if gen_result is None:
                self.stats["density_failures"] += 1
                continue
                
            occupied, actual_density = gen_result
            
            # Precompute distance transform once per map for O(N) performance
            dist_map = distance_transform_edt(~occupied) * self.raster_res
            navigable = dist_map >= self.drone_radius
            
            pairs_valid = 0
            map_w_mins = []
            map_w_smoothed_mins = []
            map_w_p10s = []
            map_w_means = []
            map_tortuosities = []
            
            # Sample up to 10 random start/goal pairs, keep up to 3 valid ones
            diag = np.sqrt(self.WIDTH**2 + self.HEIGHT**2)
            # Enforce long-range navigation (e.g., ~19.8m minimum distance on a 40x40 map)
            # to prevent trivial, purely local pathfinding solutions.
            min_sep = 0.35 * diag
            
            corridor_reject_count = 0
            for _ in range(10):
                sx, sy = random.uniform(3.0, self.WIDTH-3.0), random.uniform(3.0, self.HEIGHT-3.0)
                gx, gy = random.uniform(3.0, self.WIDTH-3.0), random.uniform(3.0, self.HEIGHT-3.0)
                if np.linalg.norm(np.array([sx, sy]) - np.array([gx, gy])) < min_sep:
                    continue
                    
                analysis = self._analyze_map(dist_map, navigable, np.array([sx, sy]), np.array([gx, gy]))
                if analysis is None:
                    self.stats["pair_reachability_rejections"] += 1
                    continue
                
                if isinstance(analysis, tuple) and analysis[0] == "CORRIDOR_REJECT":
                    self.stats["pair_corridor_rejections"] += 1
                    corridor_reject_count += 1
                    continue
                    
                w, w_smooth, wp10, wmean, t = analysis
                map_w_mins.append(w)
                map_w_smoothed_mins.append(w_smooth)
                map_w_p10s.append(wp10)
                map_w_means.append(wmean)
                map_tortuosities.append(t)
                pairs_valid += 1
                    
                if pairs_valid >= 3:
                    break
            
            if pairs_valid == 0:
                if corridor_reject_count > 0:
                    self.stats["corridor_rejections"] += 1
                else:
                    self.stats["reachability_rejections"] += 1
                continue
                

            self.stats["w_path_mins"].extend(map_w_mins)
            self.stats["w_smoothed_mins"].extend(map_w_smoothed_mins)
            self.stats["w_p10s"].extend(map_w_p10s)
            self.stats["w_means"].extend(map_w_means)
            self.stats["tortuosities"].extend(map_tortuosities)
            self.stats["actual_densities"].append(actual_density)
            self.stats["valid_maps"] += 1
            
            # Save a few occupancies for visual grid
            if len(self.stats["sample_occupancies"]) < 5:
                self.stats["sample_occupancies"].append(occupied)
                
            if self.stats["valid_maps"] % 10 == 0:
                print(f"  Attempt {self.stats['attempts']} -> Valid: {self.stats['valid_maps']}/{self.num_maps} (Map Rejects: {self.stats['corridor_rejections']} corr, {self.stats['reachability_rejections']} reach | Pair Rejects: {self.stats['pair_corridor_rejections']} corr, {self.stats['pair_reachability_rejections']} reach)", flush=True)
                
        t1 = time.time()
        print(f"Validation complete in {t1-t0:.2f}s")
        return self.stats


def plot_regime_results(results_dict, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    regimes = list(results_dict.keys())
    
    n = len(regimes)
    cols = min(3, n)
    rows = (n + cols - 1) // cols
    
    # 1. Plot W_path metrics Histograms
    plt.figure(figsize=(5 * cols, 4 * rows))
    for i, regime in enumerate(regimes):
        plt.subplot(rows, cols, i+1)
        w_mins = results_dict[regime]["w_path_mins"]
        w_smooths = results_dict[regime]["w_smoothed_mins"]
        
        plt.hist(w_smooths, bins=30, alpha=0.6, color='orange', edgecolor='black', label='Smoothed W_min (Filter)')
        plt.hist(w_mins, bins=30, alpha=0.5, color='skyblue', edgecolor='black', label='W_min (Absolute)')
        plt.title(f"Corridor Width Distributions | {regime}")
        plt.xlabel("Local Path Corridor Width (m)")
        plt.ylabel("Frequency")
        plt.axvline(np.mean(w_smooths), color='red', linestyle='dashed', linewidth=2, label=f"Mean Smoothed: {np.mean(w_smooths):.2f}m")
        plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "w_path_histograms.png"), dpi=150)
    plt.close()
    
    # 2. Plot Tortuosity Histograms
    plt.figure(figsize=(5 * cols, 4 * rows))
    for i, regime in enumerate(regimes):
        plt.subplot(rows, cols, i+1)
        torts = results_dict[regime]["tortuosities"]
        plt.hist(torts, bins=30, color='lightgreen', edgecolor='black')
        plt.title(f"Path Tortuosity | {regime}")
        plt.xlabel("Tortuosity (L_actual / L_euclidean)")
        plt.ylabel("Frequency")
        plt.axvline(np.mean(torts), color='red', linestyle='dashed', linewidth=2, label=f"Mean: {np.mean(torts):.2f}")
        plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "tortuosity_histograms.png"), dpi=150)
    plt.close()
    
    print("\n=========================================================")
    print("             GEOMETRIC REACHABILITY TABLE                ")
    print("=========================================================")
    print(f"{'Regime':<20} | {'Total Attempts':<15} | {'Reach Rejections':<18} | {'Corridor Rejects':<18} | {'Reachability Rate':<15}")
    print("-" * 95)
    for r in regimes:
        s = results_dict[r]
        attempts_reaching_check = s["attempts"] - s["density_failures"]
        pass_rate = s["valid_maps"] / max(1, attempts_reaching_check) * 100
        print(f"{r:<20} | {attempts_reaching_check:<15} | {s['reachability_rejections']:<18} | {s['corridor_rejections']:<18} | {pass_rate:.1f}%")
        
    print("\n=========================================================")
    print("               MAP GENERATION EFFICIENCY TABLE           ")
    print("=========================================================")
    print(f"{'Regime':<20} | {'Mean Density':<15} | {'Retries/Valid Map':<20}")
    print("-" * 75)
    for r in regimes:
        s = results_dict[r]
        mean_d = np.mean(s["actual_densities"])
        retries_per = (s["attempts"] - s["valid_maps"]) / max(1, s["valid_maps"])
        print(f"{r:<20} | {mean_d:<15.3f} | {retries_per:<20.2f}")
        
    print("\n=========================================================")
    print("                  GEOMETRIC TOPOLOGY STATS               ")
    print("=========================================================")
    print(f"{'Regime':<20} | {'W_min (mean+/-std)':<20} | {'W_sm_min (mean+/-std)':<22} | {'W_p10 (mean+/-std)':<20} | {'Tortuosity (mean+/-std)':<20}")
    print("-" * 110)
    for r in regimes:
        s = results_dict[r]
        wm = np.mean(s["w_path_mins"])
        ws = np.std(s["w_path_mins"])
        wsm = np.mean(s["w_smoothed_mins"])
        wss = np.std(s["w_smoothed_mins"])
        wp10m = np.mean(s["w_p10s"])
        wp10s = np.std(s["w_p10s"])
        tm = np.mean(s["tortuosities"])
        ts = np.std(s["tortuosities"])
        print(f"{r:<20} | {wm:.2f} +/- {ws:.2f} m{'':<3} | {wsm:.2f} +/- {wss:.2f} m{'':<5} | {wp10m:.2f} +/- {wp10s:.2f} m{'':<3} | {tm:.2f} +/- {ts:.2f}")
        
    # 4. Generate Sample Grids
    for regime in regimes:
        samples = results_dict[regime]["sample_occupancies"]
        plt.figure(figsize=(15, 3))
        for i, occ in enumerate(samples):
            plt.subplot(1, 5, i+1)
            plt.imshow(occ.T, cmap='Greys', origin='lower')
            plt.title(f"Sample {i+1}")
            plt.axis('off')
        plt.suptitle(f"Sample Maps - {regime}", y=1.05)
        plt.tight_layout()
        filename = f"sample_maps_{regime.replace(' ', '_').replace(':', '')}.png"
        plt.savefig(os.path.join(output_dir, filename), dpi=150, bbox_inches='tight')
        plt.close()
        
    print(f"\n[OK] Validation artifacts saved to {output_dir}/")


if __name__ == "__main__":
    # Test Regimes:
    # 1. 30x30 | ρ=0.20
    # 2. 30x30 | ρ=0.30
    # 3. 40x40 | ρ=0.30
    # 4. 40x40 | ρ=0.35
    
    configs = [
    ("30x30 D=0.20", 30, 30, 0.20),
    ("30x30 D=0.25", 30, 30, 0.25),
    ("30x30 D=0.30", 30, 30, 0.30),
    ("30x30 D=0.35", 30, 30, 0.35),
    ("40x40 D=0.25", 40, 40, 0.25),
    ("40x40 D=0.30", 40, 40, 0.30),
    ("40x40 D=0.35", 40, 40, 0.35),
]
    NUM_MAPS_PER_REGIME = 500
    
    results = {}
    for i, (name, w, h, d) in enumerate(configs):
        val = TopologyValidator(width=w, height=h, density=d, num_maps=NUM_MAPS_PER_REGIME, seed=42+i)
        results[name] = val.run()
        
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation_results")
    plot_regime_results(results, output_dir)
