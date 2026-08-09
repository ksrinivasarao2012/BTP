"""
DENSITY CALIBRATION ON THE REAL PAPER ENV  (replaces the v14 sweep for setup.tex)
================================================================================
WHY THIS EXISTS
---------------
`FINAL_PARAMETER.md` calibrated density with `PhaseB2/density_sweep_v14_*.py`, whose
`generate_obstacles()` keeps a 5 cm raster and REJECTS any obstacle overlapping one already
placed. The real env (`Phase_CD/swarm_env_phasecd.py:287-292`) has NO overlap test: it sums
pi*r^2 with overlaps double-counted and stops early. Same label "0.27", different quantity:

    sweep @0.27 : 68.9 obstacles/map, mean area ~1.57 m^2, TRUE coverage 0.27
    env   @0.27 : 29.7 obstacles/map, mean area  3.79 m^2, true coverage UNKNOWN (< 0.27)

So the 96.8% solvability in setup.tex was measured on a different map distribution than the
one we evaluate on. This script re-measures solvability using the ENV'S OWN generator and the
ENV'S OWN BFS, so the number in the paper describes the maps we actually use.

HOW IT STAYS FAITHFUL
---------------------
It does NOT re-implement anything -- re-implementation is exactly what caused the original
mismatch. It subclasses the real env and intercepts `_is_map_solvable` so that the FIRST call
of each reset (the map-generation check at swarm_env_phasecd.py:294) has its true verdict
recorded and is then force-accepted. Forcing acceptance keeps attempt 0's map, which is an
UNBIASED sample of the generator; without it the env's 50-attempt retry loop would silently
resample until solvable and every map would score 100% by construction.
All later `_is_map_solvable` calls (drone spawn placement) pass through unchanged.

WHAT IT REPORTS, per density
----------------------------
  pct_all10_ok    fraction of maps where all 10 drones BFS-reach the goal   <- headline
  avg_drone_ok    drone-level reachability (softer, less noisy)
  wilson_95       Wilson 95% CI on pct_all10_ok (same interval the v14 table used)
  n_obs           mean obstacles per map          (compare: sweep 68.9 @0.27)
  mean_r          mean obstacle radius
  nominal_dens    mean sum(pi r^2)/area  -- what the generator THINKS it placed (overlaps double-counted)
  true_dens       mean rasterised coverage -- what is ACTUALLY covered  <- the overlap gap
  pct_blocked_start  maps with >=1 drone starting in a BFS-blocked cell (the sweep discarded these)

Usage (run python by FULL path; see CLAUDE.md PhaseB2 Commands):
  python calibrate_density_realenv.py                 # 2000 maps/density, 10 workers
  python calibrate_density_realenv.py 100 10          # 100-map TIMING PROBE first
  python calibrate_density_realenv.py 10000 10        # match the v14 sweep's map budget
Writes: Phase_CD/Noise_added/results_027/density_calibration_realenv.csv
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
os.environ["OMP_NUM_THREADS"] = "1"
import sys
import csv
import time
import numpy as np
from multiprocessing import Pool

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
_COLLAB = os.path.join(_PHASE_CD, "Collab_Perception")
for _p in (_ROOT, _PHASE_CD, _COLLAB, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)

# The seven densities of the v14 table, so the two are directly comparable row-for-row.
DENSITIES = (0.20, 0.25, 0.26, 0.27, 0.28, 0.29, 0.30)
SEED_BASE = 900_000_000          # distinct from the eval seeds (800_200_000 + map_idx)
SOLVABILITY_THRESHOLD = 0.95     # the fairness bar inherited from FINAL_PARAMETER.md sec 3


# ----------------------------------------------------------------------------- env subclass
def _make_env_cls():
    """Imported lazily inside the worker: the env pulls in heavy deps at import time."""
    from swarm_env_phasecd import SwarmLidarEnv_StepB10_8_0m

    class FirstAttemptEnv(SwarmLidarEnv_StepB10_8_0m):
        """Records attempt-0's solvability verdict, then force-accepts attempt 0.

        The env's generation loop is:
            for attempt in range(50):
                ...build obstacles...
                if self._validate_obstacles() and self._is_map_solvable(start_pos=spawn_center):
                    break
        `_validate_obstacles` re-checks the goal keep-out that generation already enforced
        (swarm_env_phasecd.py:291 vs :598), so it never short-circuits and the first
        `_is_map_solvable` call is always the map-generation check.
        """

        def reset(self, *args, **kwargs):
            self._fa_seen = False
            self._fa_verdict = None
            self._fa_bypass = True      # suppress EVERY solvability gate inside reset
            try:
                return super().reset(*args, **kwargs)
            finally:
                self._fa_bypass = False

        def _is_map_solvable(self, start_pos=None, grid_resolution=0.2):
            # Outside reset (our post-hoc measurement) -> the real, unmodified answer.
            if not getattr(self, "_fa_bypass", False):
                return super()._is_map_solvable(start_pos=start_pos, grid_resolution=grid_resolution)
            # Inside reset, TWO gates call this and BOTH must be neutralised, or the
            # measurement is circular:
            #   1. map generation (:294) -- retries up to 50x until solvable, so without the
            #      bypass every kept map is solvable by construction. We record attempt 0's
            #      true verdict here; that is the unbiased generator sample.
            #   2. clustered drone spawn (:319, :326) -- only accepts a start position that is
            #      ALREADY solvable. This is the one that made the first probe report 100.00%
            #      at all seven densities. Neutralising it leaves the geometric criteria
            #      (inter-drone spacing, obstacle clearance, goal clearance) intact, which is
            #      exactly how the v14 sweep's spawn_drones_clustered() placed drones.
            if not self._fa_seen:
                self._fa_seen = True
                self._fa_verdict = bool(
                    super()._is_map_solvable(start_pos=start_pos, grid_resolution=grid_resolution))
            return True

    return FirstAttemptEnv


# ----------------------------------------------------------------------------- geometry helpers
def true_coverage(obstacles, width, height, res=0.05):
    """Rasterised fraction of the field actually covered (overlaps counted ONCE).

    This is the number the v14 sweep controlled to 0.27 by construction; our env does not,
    so measuring it here is what quantifies the gap between the two definitions.
    """
    nx, ny = int(round(width / res)), int(round(height / res))
    covered = np.zeros((ny, nx), dtype=bool)
    for ox, oy, orr in obstacles:
        # bounding-box slice only -- a full-field distance test per obstacle is ~20x slower
        x0, x1 = max(0, int((ox - orr) / res)), min(nx, int((ox + orr) / res) + 1)
        y0, y1 = max(0, int((oy - orr) / res)), min(ny, int((oy + orr) / res) + 1)
        if x0 >= x1 or y0 >= y1:
            continue
        xs = (np.arange(x0, x1) + 0.5) * res - ox
        ys = (np.arange(y0, y1) + 0.5) * res - oy
        covered[y0:y1, x0:x1] |= (ys[:, None] ** 2 + xs[None, :] ** 2) <= orr ** 2
    return float(covered.mean())


def wilson(k, n, z=1.96):
    """Wilson score interval -- the same interval FINAL_PARAMETER.md sec 3 reports."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half) * 100.0, min(1.0, centre + half) * 100.0)


# ----------------------------------------------------------------------------- worker
_W = {}


def _init(density):
    _W["cls"] = _make_env_cls()
    _W["env"] = _W["cls"](
        render_mode=None, target_density=density,
        communication_range=10.0, congestion_mode="lidar", lidar_range=8.0,
    )


def _one_map(map_idx):
    env = _W["env"]
    env.reset(seed=SEED_BASE + map_idx, options={"spawn_mode": "clustered"})

    obstacles = list(env.obstacles)
    n_obs = len(obstacles)
    radii = np.array([o[2] for o in obstacles], dtype=np.float64) if n_obs else np.zeros(0)
    area = float(env.WIDTH * env.HEIGHT)
    nominal = float(np.pi * (radii ** 2).sum() / area) if n_obs else 0.0

    # per-drone reachability from the ACTUAL spawn positions the env produced
    n_ok, blocked_start = 0, False
    for pos in env.positions:
        if env._is_map_solvable(start_pos=np.asarray(pos, dtype=np.float64)):
            n_ok += 1
    # a start cell inside an inflated obstacle is the "ill-posed" case the v14 sweep DISCARDED;
    # we count it instead of dropping it, so the denominator here is every generated map
    gr = 0.2
    gsz = int(np.ceil(env.WIDTH / gr))
    for pos in env.positions:
        gx = int(np.clip(int(pos[0] / gr), 0, gsz - 1))
        gy = int(np.clip(int(pos[1] / gr), 0, gsz - 1))
        for ox, oy, orr in obstacles:
            if (gx * gr + gr / 2 - ox) ** 2 + (gy * gr + gr / 2 - oy) ** 2 < (orr + env.drone_radius + 0.05) ** 2:
                blocked_start = True
                break
        if blocked_start:
            break

    return dict(
        all10=int(n_ok == env.n_drones),
        drone_ok=n_ok,
        n_drones=env.n_drones,
        first_attempt=int(bool(env._fa_verdict)),
        n_obs=n_obs,
        sum_r=float(radii.sum()),
        nominal=nominal,
        true_dens=true_coverage(obstacles, env.WIDTH, env.HEIGHT),
        blocked_start=int(blocked_start),
        # "clean" == well-posed, the SAME filter density_sweep_v14_specific.py:358-372 applied
        # before scoring. Bypassing the env's spawn solvability gate (necessary, or the metric is
        # circular) lets a drone land exactly touching an obstacle, since the env allows
        # spawn_obstacle_clearance=0.0 while BFS inflates obstacles by drone_radius+0.05. Those
        # maps are ill-posed, not hard. Only the CLEAN column is comparable to the v14 96.8%.
        clean=int(not blocked_start),
        all10_clean=int((not blocked_start) and n_ok == env.n_drones),
    )


# ----------------------------------------------------------------------------- driver
def main():
    n_maps = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    n_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    # optional 3rd arg: comma-separated subset, e.g. "0.26,0.27,0.28" -- lets a huge map budget
    # be spent only on the densities that actually decide the ceiling.
    densities = DENSITIES
    if len(sys.argv) > 3:
        densities = tuple(float(x) for x in sys.argv[3].split(",") if x.strip())

    out_dir = os.path.join(_HERE, "results_027")
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, "density_calibration_realenv.csv")

    print("=" * 96)
    print(f"DENSITY CALIBRATION -- REAL PAPER ENV (swarm_env_phasecd) | {n_maps} maps/density | "
          f"{n_workers} workers")
    print("  Overlapping obstacles ALLOWED (unlike the v14 sweep) -- 'nominal' is what the")
    print("  generator counts, 'true' is what is actually covered. The gap is the whole point.")
    print("=" * 96)
    hdr = (f"{'dens':>5} {'CLEAN ok':>9} {'wilson 95%':>16} {'n_cln':>6} "
           f"{'allmaps':>8} {'drone':>8} {'n_obs':>7} {'mean_r':>6} "
           f"{'nominal':>8} {'true':>7} {'blk_st':>7} {'sec':>6}  verdict")
    print(hdr)
    print("-" * len(hdr))

    rows = []
    t_all = time.time()
    for d in densities:
        t0 = time.time()
        with Pool(processes=n_workers, initializer=_init, initargs=(d,)) as pool:
            res = pool.map(_one_map, range(n_maps), chunksize=8)
        dt = time.time() - t0

        n = len(res)
        k_all10 = sum(r["all10"] for r in res)
        pct_all10 = 100.0 * k_all10 / n
        lo, hi = wilson(k_all10, n)
        # the v14-comparable figure: solvability among WELL-POSED maps only
        n_clean = sum(r["clean"] for r in res)
        k_clean = sum(r["all10_clean"] for r in res)
        pct_clean = 100.0 * k_clean / n_clean if n_clean else 0.0
        clo, chi = wilson(k_clean, n_clean)
        drone_ok = 100.0 * sum(r["drone_ok"] for r in res) / sum(r["n_drones"] for r in res)
        n_obs = np.mean([r["n_obs"] for r in res])
        mean_r = (sum(r["sum_r"] for r in res) / max(1, sum(r["n_obs"] for r in res)))
        nominal = np.mean([r["nominal"] for r in res])
        true_d = np.mean([r["true_dens"] for r in res])
        blk = 100.0 * sum(r["blocked_start"] for r in res) / n
        first = 100.0 * sum(r["first_attempt"] for r in res) / n

        # the ceiling is judged on the CLEAN column -- that is the v14-comparable quantity
        verdict = "PASS" if clo >= SOLVABILITY_THRESHOLD * 100 else (
            "BORDERLINE" if pct_clean >= SOLVABILITY_THRESHOLD * 100 else "FAIL")

        print(f"{d:5.2f} {pct_clean:8.2f}% [{clo:6.2f},{chi:6.2f}] {n_clean:6d} "
              f"{pct_all10:8.2f}% {drone_ok:7.2f}% {n_obs:7.2f} {mean_r:6.3f} "
              f"{nominal:8.4f} {true_d:7.4f} {blk:6.1f}% {dt:6.1f}  {verdict}")

        rows.append(dict(
            density=d, n_maps=n,
            pct_all10_clean=pct_clean, clean_wilson_lo=clo, clean_wilson_hi=chi, n_clean=n_clean,
            pct_all10_allmaps=pct_all10, allmaps_wilson_lo=lo, allmaps_wilson_hi=hi,
            avg_drone_ok=drone_ok, pct_first_attempt_solvable=first, avg_obs_count=n_obs,
            mean_radius=mean_r, nominal_density=nominal, true_density=true_d,
            pct_blocked_start=blk, verdict=verdict, seconds=dt,
        ))
        # rewrite the CSV after EVERY density: at 100k maps/density this run is many hours,
        # and a crash in the last row must not cost the completed ones.
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    print("-" * len(hdr))
    print(f"total {time.time() - t_all:.1f}s   ->  {out_csv}")
    print()
    print("READ THIS BEFORE PUTTING NUMBERS IN setup.tex:")
    print("  * 'true' < 'nominal' is EXPECTED and is the overlap gap. Quote 'true' as the")
    print("    realised coverage; quote the target 0.27 only as the generator's setting.")
    print("  * pct_all10_ok here is over EVERY generated map. The v14 table's 96.8% was over")
    print("    'clean' maps only (ill-posed ones discarded), so the two are NOT interchangeable.")
    print("  * The ceiling is the last density whose Wilson LOWER bound clears 95%.")


if __name__ == "__main__":
    main()
