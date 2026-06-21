"""
Verify the randomized Byzantine attack: per-map n_phantom ~ U{3..6} and per-phantom radius drawn
from the REAL obstacle mixture (20% large / 40% medium / 40% small). Confirms the phantom population
is statistically indistinguishable-by-size from real obstacles, and that the offset/bind sweep keeps
a FIXED radius (randomize_attack=False).

Usage:
  python verify_randomized_attack.py [n_maps] [attack_mode]   # attack_mode = wall | camouflage
  python verify_randomized_attack.py 300 camouflage
"""
import os, sys
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
_COLLAB = os.path.join(os.path.dirname(_HERE), "Collab_Perception")
for _p in (_ROOT, os.path.dirname(_HERE), _COLLAB, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)

from env_noisy_byzantine import NoisyByzantineEnv

n_maps = int(sys.argv[1]) if len(sys.argv) > 1 else 300
mode = sys.argv[2] if len(sys.argv) > 2 else "camouflage"


def _bands(radii):
    radii = np.asarray(radii, float)
    return tuple(100.0 * np.mean((radii >= lo - 1e-6) & (radii <= hi + 1e-6))
                 for lo, hi in [(0.2, 0.5), (0.6, 1.4), (1.5, 2.5)])


def _collect(randomize):
    env = NoisyByzantineEnv(
        render_mode=None, target_density=0.27, communication_range=10.0,
        congestion_mode="lidar", lidar_range=8.0, lidar_dropout=0.10, dropout_sustain=5,
        use_shared_map=True, false_obstacle_attack=True, traitor_indices=[0, 1],
        attack_mode=mode, randomize_attack=randomize, n_phantom_range=(3, 6),
        phantom_radius=1.0, sensor_noise=0.4,
    )
    ks, rs = [], []
    for i in range(n_maps):
        env.reset(seed=1000 + i, options={"spawn_mode": "clustered"})
        ph = np.asarray(env._phantoms, float)
        ks.append(len(ph))
        if len(ph):
            rs.extend(ph[:, 2].tolist())
    env.close()
    return np.array(ks, float), np.array(rs, float)


print(f"\n=== randomized-attack verification | mode={mode} | {n_maps} maps ===")
ks, rs = _collect(randomize=True)
uniq, cnt = np.unique(ks.astype(int), return_counts=True)
print("randomize_attack = TRUE  (headline realism)")
print(f"  n_phantom per map : {dict(zip(uniq.tolist(), cnt.tolist()))}  "
      f"(mean={ks.mean():.2f}, expect ~4.5 over U{{3..6}})")
b = _bands(rs)
print(f"  phantom radius    : mean={rs.mean():.3f}  bands small/med/large = "
      f"{b[0]:.0f}/{b[1]:.0f}/{b[2]:.0f}%  (expect ~42/40/18, == REAL mixture)")

ks0, rs0 = _collect(randomize=False)
print("randomize_attack = FALSE (bind/offset sweep -> must be fixed)")
print(f"  n_phantom per map : {sorted(set(ks0.astype(int).tolist()))}  (expect single value = 4)")
print(f"  phantom radius    : unique = {np.unique(np.round(rs0,3)).tolist()}  (expect [1.0])")
print("=" * 60)
