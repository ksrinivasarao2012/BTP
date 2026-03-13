import numpy as np
import time
from test_suite_step_A import run_random_test, run_clustered_test

def run_k_fold(k=5, episodes_per_fold=1000):
    print(f"==================================================")
    print(f"🤖 K-FOLD VALIDATION LAUNCHED (K={k})")
    print(f"   Episodes per fold: {episodes_per_fold:,}")
    print(f"   Total drone simulations: {k * episodes_per_fold * 10:,} per category")
    print(f"==================================================\n")

    random_successes = []
    cluster_successes = []

    for fold in range(1, k + 1):
        print(f"\n--- FOLD {fold}/{k} ---")
        
        # 1. Random Scenarios
        # returns: successes, collisions, timeouts, total_drones, duration
        print(">> Running Random Spread Fold...")
        r_succ, r_coll, _, total, _ = run_random_test(episodes_per_fold, f"Fold {fold} - Random")
        r_sr = (r_succ / total) * 100.0
        random_successes.append(r_sr)
        
        # 2. Clustered Scenarios
        print("\n>> Running Dense Cluster Fold...")
        c_succ, c_coll, _, total, _ = run_clustered_test(episodes_per_fold, f"Fold {fold} - Clustered")
        c_sr = (c_succ / total) * 100.0
        cluster_successes.append(c_sr)
        
        print(f"Fold {fold} Results: Random= {r_sr:.2f}%, Clustered= {c_sr:.2f}%")

    print(f"\n==================================================")
    print(f"🏆 FINAL K-FOLD VALIDATION RESULTS")
    print(f"==================================================")
    
    r_mean = np.mean(random_successes)
    r_std = np.std(random_successes)
    print(f"[Random Spawns]    Mean Success Rate: {r_mean:.2f}% (StdDev: ±{r_std:.2f}%)")
    print(f"   Folds: {[round(x, 2) for x in random_successes]}")
    
    c_mean = np.mean(cluster_successes)
    c_std = np.std(cluster_successes)
    print(f"[Dense clusters]   Mean Success Rate: {c_mean:.2f}% (StdDev: ±{c_std:.2f}%)")
    print(f"   Folds: {[round(x, 2) for x in cluster_successes]}")
    
    # Save the final k-fold results to a quick text file for records too
    with open("k_fold_results.txt", "w") as f:
        f.write(f"K-Fold Validation (K={k}, Drones={k*episodes_per_fold*10})\n")
        f.write(f"Random: {r_mean:.2f}% ± {r_std:.2f}%\n")
        f.write(f"Cluster: {c_mean:.2f}% ± {c_std:.2f}%\n")

if __name__ == "__main__":
    run_k_fold(k=10, episodes_per_fold=200)
