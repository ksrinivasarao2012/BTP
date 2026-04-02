import numpy as np
import time
import sys
import os
from test_suite_step_B import run_random_test, run_clustered_test

# ======================================================
#  PHASE B: K-Fold Statistical Validation Script
# ======================================================

def run_k_fold(model_path, k=10, episodes_per_fold=100, start_fold=1, end_fold=None):
    if end_fold is None: end_fold = k
    
    print(f"==================================================")
    print(f"🤖 K-FOLD VALIDATION (FOLD {start_fold} TO {end_fold})")
    print(f"   Model: {model_path}")
    print(f"   Episodes per fold: {episodes_per_fold:,}")
    print(f"==================================================\n")

    random_successes = []
    cluster_successes = []

    for fold in range(start_fold, end_fold + 1):
        # Use a predictable seed for each fold (e.g., 1000, 2000, ...)
        fold_seed = fold * 1000 
        
        # Capture trajectories ONLY for the first fold (first 10 eps) for visualization
        log_fold = (fold == 1)
        
        print(f"\n--- FOLD {fold}/{k} ---")
        print(f">> Running Random Spread Fold (Seed: {fold_seed})...")
        r_succ, r_coll, _, total, _ = run_random_test(model_path, episodes_per_fold, f"Fold {fold} - Random", seed=fold_seed, log_trajectories=log_fold)
        r_sr = (r_succ / total) * 100.0
        random_successes.append(r_sr)
        
        # 2. Clustered Scenarios
        print(f"\n>> Running Dense Cluster Fold (Seed: {fold_seed})...")
        c_succ, c_coll, _, total, _ = run_clustered_test(model_path, episodes_per_fold, f"Fold {fold} - Clustered", seed=fold_seed, log_trajectories=log_fold)
        c_sr = (c_succ / total) * 100.0
        cluster_successes.append(c_sr)
        
        print(f"Fold {fold} Results: Random= {r_sr:.2f}%, Clustered= {c_sr:.2f}%")

    # If we are only running a single fold, we don't need the grand mean here
    if start_fold == end_fold:
        print(f"\n✅ Fold {start_fold} complete.")
    else:
        print(f"\nSummary for Folds {start_fold}-{end_fold}:")
        print(f"Random Mean: {np.mean(random_successes):.2f}%")
        print(f"Cluster Mean: {np.mean(cluster_successes):.2f}%")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python evaluate_step_B.py <model_path> [K] [ep_per_fold] [start_f] [end_f]")
        sys.exit(1)
        
    m_path = sys.argv[1]
    k_val = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    ep_count = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    start_f = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    end_f = int(sys.argv[5]) if len(sys.argv) > 5 else k_val
    
    if not os.path.exists(m_path):
        print(f"❌ Model not found: {m_path}")
        sys.exit(1)
        
    run_k_fold(m_path, k=k_val, episodes_per_fold=ep_count, start_fold=start_f, end_fold=end_f)
