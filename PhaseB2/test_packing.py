"""Quick test: can 10 drones actually fit in a cluster?"""
import numpy as np

DRONE_RADIUS = 0.15
CLUSTER_RADIUS = 1.5
N_DRONES = 10
rng = np.random.RandomState(42)

def test_packing(inter_drone_min, trials=1000):
    min_dist = 2 * DRONE_RADIUS + inter_drone_min
    success = 0
    for _ in range(trials):
        placed = []
        ok = True
        for d in range(N_DRONES):
            found = False
            for attempt in range(150):
                angle = rng.uniform(0, 2 * np.pi)
                dist = rng.uniform(0, CLUSTER_RADIUS)
                px = dist * np.cos(angle)
                py = dist * np.sin(angle)
                valid = all(
                    np.sqrt((px - qx)**2 + (py - qy)**2) >= min_dist
                    for qx, qy in placed
                )
                if valid:
                    placed.append((px, py))
                    found = True
                    break
            if not found:
                ok = False
                break
        if ok:
            success += 1
    return success / trials

print(f"{'INTER_DRONE_MIN':>20} | {'Real min dist':>15} | {'Fit rate (R=1.5)':>18} | {'Fit rate (R=3.0)':>18}")
print("-" * 80)
for idm in [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]:
    real_dist = 2 * DRONE_RADIUS + idm
    rate_15 = test_packing(idm)
    # Also test with fallback radius
    old_cr = CLUSTER_RADIUS
    CLUSTER_RADIUS = 3.0
    rate_30 = test_packing(idm)
    CLUSTER_RADIUS = old_cr
    print(f"{idm:>20.2f} | {real_dist:>15.2f} | {rate_15:>17.1%} | {rate_30:>17.1%}")
