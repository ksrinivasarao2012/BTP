import numpy as np
import time
import sys
import os
# Resolve OpenMP duplicate library issue (multiple OpenMP runtimes)
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
# Force single-threaded OpenMP to avoid performance degradation
os.environ["OMP_NUM_THREADS"] = "1"
from test_suite_step_B5 import run_random_test, run_clustered_test, FIXED_DENSITY
import json
import shutil
# ======================================================
#  PHASE B5: K-Fold Statistical Validation Script
#  120-dim Synchronization | IEEE Journal Standard
# ======================================================
def run_k_fold(model_path, k=10, episodes_per_fold=200, start_fold=1, end_fold=None):
    if end_fold is None: end_fold = k

    # Create a model‑specific results folder (e.g., "results/apex_ultra_sync_v8_final")
    model_base = os.path.splitext(os.path.basename(model_path))[0]
    main_results_dir = os.path.join("results", model_base)
    os.makedirs(main_results_dir, exist_ok=True)

    # Set up Logger to capture terminal output to a text log file
    log_filepath = os.path.join(main_results_dir, "evaluation_log.txt")
    class Logger(object):
        def __init__(self, filename, original_stdout):
            self.terminal = original_stdout
            self.log = open(filename, "w", encoding="utf-8")
        def write(self, message):
            self.terminal.write(message)
            self.log.write(message)
            self.log.flush()
        def flush(self):
            self.terminal.flush()
            self.log.flush()
        def close(self):
            self.log.close()

    original_stdout = sys.stdout
    logger_instance = Logger(log_filepath, original_stdout)
    sys.stdout = logger_instance

    print(f"{'='*50}")
    print(f"\U0001F916 K-FOLD VALIDATION LAUNCHED (K={k})")
    print(f"   Episodes per fold: {episodes_per_fold}")
    print(f"   Total drone simulations: {k * episodes_per_fold * 20:,} per category")
    print(f"{'='*50}\n")

    random_successes, random_collisions, random_timeouts = [], [], []
    cluster_successes, cluster_collisions, cluster_timeouts = [], [], []

    for fold in range(start_fold, end_fold + 1):
        fold_seed = fold * 1000
        fold_dir = os.path.join(main_results_dir, f"Fold_{fold}")
        random_dir = os.path.join(fold_dir, "random")
        dense_dir = os.path.join(fold_dir, "dense")

        # Capture trajectories for ALL folds as requested
        log_fold = True

        print(f"\n--- FOLD {fold}/{k} ---")

        # 1. Random Spread
        print(f">> Running Random Spread Fold...")
        print(f"[Fold {fold} - Random] Generating {episodes_per_fold} pure random scenarios...")
        r_succ, r_coll, r_timeo, total, _ = run_random_test(model_path, episodes_per_fold, f"Fold {fold} - Random", seed=fold_seed, log_trajectories=log_fold, output_dir=random_dir)
        random_successes.append((r_succ / total) * 100.0)
        random_collisions.append((r_coll / total) * 100.0)
        random_timeouts.append((r_timeo / total) * 100.0)

        # 2. Dense Cluster
        print(f"\n>> Running Dense Cluster Fold...")
        print(f"[Fold {fold} - Clustered] Generating {episodes_per_fold} clustered scenarios...")
        c_succ, c_coll, c_timeo, total, _ = run_clustered_test(model_path, episodes_per_fold, f"Fold {fold} - Clustered", seed=fold_seed, log_trajectories=log_fold, output_dir=dense_dir)
        cluster_successes.append((c_succ / total) * 100.0)
        cluster_collisions.append((c_coll / total) * 100.0)
        cluster_timeouts.append((c_timeo / total) * 100.0)

        print(f"\nFold {fold} Results: Random= {random_successes[-1]:.2f}%, Clustered= {cluster_successes[-1]:.2f}%")

    print(f"\n{'='*50}")
    print(f"FINAL K-FOLD SUMMARY (Folds {start_fold}-{end_fold})")
    print(f"{'='*50}")
    
    print(f"Random Mean:")
    print(f"  Success:   {np.mean(random_successes):.2f}% +/- {np.std(random_successes):.2f}%")
    print(f"  Collision: {np.mean(random_collisions):.2f}% +/- {np.std(random_collisions):.2f}%")
    print(f"  Timeout:   {np.mean(random_timeouts):.2f}% +/- {np.std(random_timeouts):.2f}%")
    print(f"{'='*50}\n")

    print(f"\nClustered Mean:")
    print(f"  Success:   {np.mean(cluster_successes):.2f}% +/- {np.std(cluster_successes):.2f}%")
    print(f"  Collision: {np.mean(cluster_collisions):.2f}% +/- {np.std(cluster_collisions):.2f}%")
    print(f"  Timeout:   {np.mean(cluster_timeouts):.2f}% +/- {np.std(cluster_timeouts):.2f}%")
    print(f"{'='*50}\n")

    # Restore standard output and close the log file to finalize it
    sys.stdout = original_stdout
    logger_instance.close()

    # -------------------------------------------------
    # Consolidate all results into a dedicated folder "v8"
    # -------------------------------------------------
    v8_dir = os.path.join("results", "v8")
    os.makedirs(v8_dir, exist_ok=True)
    # Store the obstacle density used for this run
    with open(os.path.join(v8_dir, "obstacle_density.txt"), "w") as f:
        f.write(str(FIXED_DENSITY))
    # Copy the model‑specific results (CSV files, plots, summary, and terminal log) into v8
    shutil.copytree(main_results_dir, os.path.join(v8_dir, model_base), dirs_exist_ok=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python evaluate_step_B5.py <model_path> [K] [ep_per_fold]")
        print("Example: python evaluate_step_B5.py ./models/apex_ultra_sync_final.zip 10 200")
        sys.exit(1)

    m_path = sys.argv[1]
    k_val = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    ep_count = int(sys.argv[3]) if len(sys.argv) > 3 else 200

    if not os.path.exists(m_path):
        print(f"Model not found: {m_path}")
        sys.exit(1)

    run_k_fold(m_path, k=k_val, episodes_per_fold=ep_count)
