import os
import subprocess
import sys
import pandas as pd
import glob

# ======================================================
#  PHASE B10: OBSTACLE DENSITY SWEEP RUNNER
#  Evaluates K=5 folds, 100 episodes per fold for
#  obstacle densities 0.20, 0.25, 0.30, and 0.35.
# ======================================================

densities = [0.20, 0.25, 0.30, 0.35]
model_path = "../../models/apex_ultra_glide_v14_final.zip"
cores = 5
episodes = 100
folds = 5

script_dir = os.path.dirname(os.path.abspath(__file__))
master_script = os.path.join(script_dir, "k_fold_master_B10.py")

print("=========================================================================")
print(f"🚀 STARTING MULTI-DENSITY SWEEP EXPERIMENT (K={folds}, {episodes} Eps/Fold)")
print(f"   Model: {os.path.basename(model_path)}")
print(f"   Densities to evaluate: {densities}")
print("=========================================================================\n")

for d in densities:
    print(f"\n=========================================================================")
    print(f"🔥 RUNNING EVALUATION SWEEP FOR OBSTACLE DENSITY = {d:.2f}")
    print(f"=========================================================================")
    
    # Set the environment variable for this run
    env = os.environ.copy()
    env["OBSTACLE_DENSITY"] = f"{d:.2f}"
    
    # Execute the k_fold_master_B10 script
    # Args: model_path, cores, total_episodes, num_folds
    cmd = [
        sys.executable, 
        "-u", 
        master_script, 
        model_path, 
        str(cores), 
        str(episodes), 
        str(folds)
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, cwd=script_dir)
    
    if result.returncode != 0:
        print(f"❌ Warning: Sweep for density {d:.2f} failed with exit code {result.returncode}")
    else:
        print(f"✅ Finished sweep for density {d:.2f} successfully!")

# ======================================================
#  COLLECT AND PRINT COMPARISON RESULTS
# ======================================================
print("\n" + "="*85)
print("📊 COMPILING MULTI-DENSITY SWEEP SUMMARY REPORT")
print("="*85)

results_dir = os.path.join(os.path.dirname(script_dir), "results", "v14")
summary_data = []

# Search for the CSV results files generated during this run
for d in densities:
    folder_pattern = os.path.join(results_dir, f"apex_ultra_glide_v14_final_density_{d:.2f}")
    csv_files = glob.glob(os.path.join(folder_pattern, "master_B10_evaluation_results_*.csv"))
    
    if not csv_files:
        print(f"⚠️ No results CSV found for density {d:.2f} in {folder_pattern}")
        continue
        
    # Pick the most recent CSV file
    csv_files.sort()
    latest_csv = csv_files[-1]
    
    try:
        df = pd.read_csv(latest_csv)
        for mode in ["random", "clustered"]:
            mode_df = df[df["Mode"] == mode]
            if not mode_df.empty:
                summary_data.append({
                    "Density": d,
                    "Mode": mode,
                    "Success_Mean": mode_df["Success_Rate"].mean(),
                    "Success_Std": mode_df["Success_Rate"].std(),
                    "Collision_Mean": mode_df["Collision_Rate"].mean(),
                    "Collision_Std": mode_df["Collision_Rate"].std(),
                    "Timeout_Mean": mode_df["Timeout_Rate"].mean(),
                    "Timeout_Std": mode_df["Timeout_Rate"].std()
                })
    except Exception as e:
        print(f"❌ Error reading {latest_csv}: {e}")

if not summary_data:
    print("No sweep results could be compiled. Please check the logs.")
    sys.exit(0)

# Print clean comparison tables
master_df = pd.DataFrame(summary_data)

for mode in ["random", "clustered"]:
    print(f"\n📈 NAVIGATION METRICS: {mode.upper()} SPAWN MODE")
    print("-" * 90)
    print(f"{'Density':<10} | {'Success Rate (Mean ± Std)':<30} | {'Collision Rate (Mean ± Std)':<30} | {'Timeout Rate'}")
    print("-" * 90)
    
    mode_results = master_df[master_df["Mode"] == mode].sort_values("Density")
    for _, row in mode_results.iterrows():
        s_std = 0.0 if pd.isna(row['Success_Std']) else row['Success_Std']
        c_std = 0.0 if pd.isna(row['Collision_Std']) else row['Collision_Std']
        t_std = 0.0 if pd.isna(row['Timeout_Std']) else row['Timeout_Std']
        
        s_str = f"{row['Success_Mean']:>6.2f}% ± {s_std:<4.2f}"
        c_str = f"{row['Collision_Mean']:>6.2f}% ± {c_std:<4.2f}"
        t_str = f"{row['Timeout_Mean']:>6.2f}% ± {t_std:<4.2f}"
        
        print(f"{row['Density']:>9.2f}  | {s_str:<28} | {c_str:<28} | {t_str}")
    print("-" * 90)

print("\n🎉 Multi-density sweep analysis complete!")
