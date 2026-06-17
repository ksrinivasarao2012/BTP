# run_grid_one_seed.py
# -------------------------------------------------
# Quick timing test – runs the oracle with a single seed
# -------------------------------------------------
# This script is identical to run_grid.py but sets NUM_SEEDS = 1
# so we can estimate the per‑run duration on this machine.

import itertools
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

# ----------------------------------------------------------------------
# USER‑CONFIGURABLE ranges – adjust if you want a different sweep size
# ----------------------------------------------------------------------
BOOST_VALUES   = [1.0, 1.2, 1.4, 1.6]          # speed‑multiplier
EVADE_VALUES  = [2.0, 3.0, 4.0, 5.0]          # distance (metres) at which boost fires
NUM_SEEDS     = 1                               # *** ONE SEED FOR TIMING ***
MODEL_PATH    = "models/apex_ultra_glide_v14_comm8_lidar_final.zip"
F_NUM         = 2                               # number of rammer agents
MAPS_PER_RUN = 30                              # maps per individual run
USE_BRAKE    = False                           # set True to include the brake flag

# ----------------------------------------------------------------------
# Helper to run one oracle invocation and parse its output
# ----------------------------------------------------------------------
def run_one(boost: float, evade: float, seed_idx: int) -> Tuple[float, float, float, float, float]:
    cmd = [
        sys.executable,
        str(Path(__file__).parent / "Phase_CD" / "probe_speed_oracle.py"),
        str(F_NUM),
        MODEL_PATH,
        f"{boost}",
        f"{MAPS_PER_RUN}",
        f"{evade}",
    ]
    if USE_BRAKE:
        cmd.append("--brake")
    completed = subprocess.run(
        cmd,
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Probe failed (boost={boost}, evade={evade}, seed={seed_idx})\nSTDERR: {completed.stderr}"
        )
    pattern = re.compile(r"\[\*\] d=([0-9.]+) -> success\s+([0-9.]+)%\s+\|\s+timeout\s+([0-9.]+)%\s+\|\s+coll\s+([0-9.]+)%")
    successes, timeouts, collisions = [], [], []
    for line in completed.stdout.splitlines():
        m = pattern.search(line)
        if m:
            successes.append(float(m.group(2)))
            timeouts.append(float(m.group(3)))
            collisions.append(float(m.group(4)))
    if not successes:
        raise ValueError(f"No result lines parsed for boost={boost}, evade={evade}")
    avg_success = sum(successes) / len(successes)
    avg_timeout = sum(timeouts) / len(timeouts)
    avg_collision = sum(collisions) / len(collisions)
    return (boost, evade, avg_success, avg_timeout, avg_collision)

# ----------------------------------------------------------------------
# Main driver – builds the grid, launches workers, aggregates results
# ----------------------------------------------------------------------
def main() -> None:
    param_grid: List[Tuple[float, float]] = list(itertools.product(BOOST_VALUES, EVADE_VALUES))
    futures = []
    with ProcessPoolExecutor(max_workers=None) as executor:
        for boost, evade in param_grid:
            for seed_idx in range(NUM_SEEDS):
                futures.append(executor.submit(run_one, boost, evade, seed_idx))
        results: List[Tuple[float, float, float, float, float]] = []
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as exc:
                print(f"⚠️  A run failed: {exc}", file=sys.stderr)
    # Aggregate across seeds (here only 1 seed, but code stays generic)
    agg = {}
    for boost, evade, succ, to, coll in results:
        agg.setdefault((boost, evade), []).append((succ, to, coll))
    print("\n=== Timing‑test results (1 seed, 30 maps) ===")
    header = f"{'BOOST':>6} | {'EVADE_DIST':>10} | {'SUCCESS%':>9} | {'TIMEOUT%':>9} | {'COLLISION%':>10}"
    print(header)
    print('-' * len(header))
    for (boost, evade), vals in sorted(agg.items()):
        succ_mean = sum(v[0] for v in vals) / len(vals)
        to_mean   = sum(v[1] for v in vals) / len(vals)
        coll_mean = sum(v[2] for v in vals) / len(vals)
        print(f"{boost:6.2f} | {evade:10.2f} | {succ_mean:9.2f} | {to_mean:9.2f} | {coll_mean:10.2f}")

if __name__ == "__main__":
    main()
