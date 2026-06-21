"""
Measure REAL-obstacle statistics in the Phase_CD env (grounds the attack-parameter justification
in measured fact, not hand arithmetic). Reports obstacle count, radius distribution vs the 20/40/40
mixture, mean radius/area, and phantom-as-%-of-real for n_phantom in {3,4,6}.

Usage:
  python measure_env_stats.py [density] [n_maps]
  python measure_env_stats.py 0.27 300
"""
import os, sys
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_COLLAB = os.path.join(_HERE, "Collab_Perception")
for _p in (_ROOT, _HERE, _COLLAB):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)

from env_collab_perception import CollabPerceptionEnv

density = float(sys.argv[1]) if len(sys.argv) > 1 else 0.27
n_maps = int(sys.argv[2]) if len(sys.argv) > 2 else 300

env = CollabPerceptionEnv(render_mode=None, target_density=density,
                          lidar_range=8.0, communication_range=10.0)

counts, radii = [], []
for i in range(n_maps):
    env.reset(seed=1000 + i, options={"spawn_mode": "clustered"})
    obs = np.array(env.obstacles, dtype=float) if env.obstacles else np.empty((0, 3))
    counts.append(len(obs))
    if len(obs):
        radii.extend(obs[:, 2].tolist())

counts = np.array(counts, dtype=float)
radii = np.array(radii, dtype=float)

print(f"\n=== Phase_CD env real-obstacle stats | density={density} | {n_maps} maps ===")
print(f"obstacle COUNT  : mean={counts.mean():.1f}  median={np.median(counts):.0f}  "
      f"min={int(counts.min())}  max={int(counts.max())}")
print(f"radius (m)      : mean={radii.mean():.3f}  median={np.median(radii):.3f}  "
      f"min={radii.min():.2f}  max={radii.max():.2f}")
print(f"radius bands (expect ~40/40/20):")
for lo, hi, lbl in [(0.2, 0.5, "small "), (0.6, 1.4, "medium"), (1.5, 2.5, "large ")]:
    frac = 100.0 * np.mean((radii >= lo - 1e-6) & (radii <= hi + 1e-6))
    print(f"   {lbl} [{lo},{hi}] : {frac:4.0f}%")
print(f"mean obstacle AREA = {np.mean(np.pi*radii**2):.2f} m^2   "
      f"(area-based count check: {density*400/np.mean(np.pi*radii**2):.1f})")
mc = counts.mean()
print(f"phantom as % of real obstacles:  3 -> {100*3/mc:.0f}%   4 -> {100*4/mc:.0f}%   6 -> {100*6/mc:.0f}%")
print("=" * 60)
