import numpy as np
import time
import sys
import os
from test_suite_step_B5 import run_random_test, run_clustered_test

# ======================================================
#  PHASE B5: K-Fold Statistical Validation Script
#  120-dim Synchronization | IEEE Journal Standard
# ======================================================
def run_k_fold(model_path, k=10, episodes_per_fold=200, start_fold=1, end_fold=None):
    if end_fold is None: end_fold = k

    print(f"{'='*50}")
    print(f"\U0001F916 K-FOLD VALIDATION LAUNCHED (K={k})")
    print(f"   Episodes per fold: {episodes_per_fold}")
    print(f"   Total drone simulations: {k * episodes_per_fold * 10:,} per category")
    print(f"{'='*50}\n")

    random_successes, random_collisions, random_timeouts = [], [], []
    cluster_successes, cluster_collisions, cluster_timeouts = [], [], []

    main_results_dir = "results"
    os.makedirs(main_results_dir, exist_ok=True)

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
    
    print(f"\nClustered Mean:")
    print(f"  Success:   {np.mean(cluster_successes):.2f}% +/- {np.std(cluster_successes):.2f}%")
    print(f"  Collision: {np.mean(cluster_collisions):.2f}% +/- {np.std(cluster_collisions):.2f}%")
    print(f"  Timeout:   {np.mean(cluster_timeouts):.2f}% +/- {np.std(cluster_timeouts):.2f}%")
    print(f"{'='*50}\n")


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
