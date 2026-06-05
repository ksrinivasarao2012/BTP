import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ======================================================
#  PHASE B10: DENSITY SWEEP PLOTTING UTILITY
#  Collects K-fold results for densities [0.20, 0.25, 0.30, 0.35]
#  and generates professional academic plots.
# ======================================================

script_dir = os.path.dirname(os.path.abspath(__file__))
results_dir = os.path.join(script_dir, "results", "v14")
densities = [0.20, 0.25, 0.30, 0.35]

print("==================================================")
print("📈 RUNNING MULTI-DENSITY PLOT GENERATOR")
print("==================================================")

summary_data = []

# 1. Collect all CSV results
for d in densities:
    folder_pattern = os.path.join(results_dir, f"apex_ultra_glide_v14_final_density_{d:.2f}")
    csv_files = glob.glob(os.path.join(folder_pattern, "master_B10_evaluation_results_*.csv"))
    
    if not csv_files:
        print(f"⚠️ No results CSV found for density {d:.2f}")
        continue
        
    csv_files.sort()
    latest_csv = csv_files[-1]
    
    try:
        df = pd.read_csv(latest_csv)
        for mode in ["random", "clustered"]:
            mode_df = df[df["Mode"] == mode]
            if not mode_df.empty:
                for _, row in mode_df.iterrows():
                    summary_data.append({
                        "Density": d,
                        "Mode": mode,
                        "Success_Rate": row["Success_Rate"],
                        "Collision_Rate": row["Collision_Rate"],
                        "Timeout_Rate": row["Timeout_Rate"]
                    })
    except Exception as e:
        print(f"❌ Error reading {latest_csv}: {e}")

if not summary_data:
    print("❌ No data collected. Plot generation aborted.")
    sys.exit(1)

df_all = pd.DataFrame(summary_data)

# 2. Set up high-quality publication styling
plt.rcParams.update({
    'font.size': 11,
    'font.family': 'sans-serif',
    'axes.edgecolor': '#cccccc',
    'axes.linewidth': 0.8,
    'grid.linestyle': '--',
    'grid.alpha': 0.5,
    'grid.color': '#dddddd'
})

# Create 3 subplots: Success, Collision, and Timeout vs Obstacle Density
fig, axes = plt.subplots(1, 3, figsize=(18, 6.5), dpi=300)
metrics = ["Success_Rate", "Collision_Rate", "Timeout_Rate"]
titles = ["Success Rate vs. Density", "Collision Rate vs. Density", "Timeout Rate vs. Density"]
y_labels = ["Success Rate (%)", "Collision Rate (%)", "Timeout Rate (%)"]
colors = {"random": "#008080", "clustered": "#FF6F61"} # Teal and Coral
labels = {"random": "Random Spawn", "clustered": "Cluster Spawn"}
markers = {"random": "o", "clustered": "s"}

for idx, metric in enumerate(metrics):
    ax = axes[idx]
    
    for mode in ["random", "clustered"]:
        mode_df = df_all[df_all["Mode"] == mode]
        
        # Calculate means and std deviations for each density
        means = []
        stds = []
        for d in densities:
            d_scores = mode_df[mode_df["Density"] == d][metric]
            means.append(d_scores.mean())
            stds.append(d_scores.std() if len(d_scores) > 1 else 0.0)
            
        means = np.array(means)
        stds = np.array(stds)
        
        # Plot curve with markers and lines
        ax.plot(densities, means, label=labels[mode], color=colors[mode], 
                marker=markers[mode], linewidth=2.5, markersize=8, alpha=0.9)
        
        # Add beautiful shaded error margins (std dev)
        ax.fill_between(densities, means - stds, means + stds, 
                        color=colors[mode], alpha=0.15)
        
        # Add error bars (caps)
        ax.errorbar(densities, means, yerr=stds, fmt='none', ecolor=colors[mode], 
                    elinewidth=1.5, capsize=4, alpha=0.8)
        
        # Add text labels next to data points for clarity
        for i, d in enumerate(densities):
            ax.annotate(f"{means[i]:.1f}%", (d, means[i]), textcoords="offset points", 
                        xytext=(0, 8 if mode == "random" else -14), ha='center', 
                        fontsize=9, fontweight='bold', color=colors[mode])

    ax.set_title(titles[idx], fontsize=13, fontweight='bold', pad=15)
    ax.set_xlabel("Obstacle Density", fontsize=11, fontweight='bold', labelpad=10)
    ax.set_ylabel(y_labels[idx], fontsize=11, fontweight='bold', labelpad=10)
    ax.set_xticks(densities)
    ax.set_xlim(0.18, 0.37)
    
    if metric == "Success_Rate":
        ax.set_ylim(70, 102)
    elif metric == "Collision_Rate":
        ax.set_ylim(-1, 15)
    else:
        ax.set_ylim(-2, 22)
        
    ax.grid(True)
    ax.legend(frameon=True, facecolor='white', edgecolor='none', shadow=True, loc='best')
    
    # Despine for minimalist aesthetic
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

plt.suptitle("Decentralized Swarm Navigation: Multi-Density Sweep Analysis (v14)", 
             fontsize=15, fontweight='bold', y=0.98, color='#111111')
plt.tight_layout()

# Save comparison plot
out_path = os.path.join(results_dir, "density_sweep_comparison.png")
plt.savefig(out_path, bbox_inches='tight')
plt.close()

print(f"🎉 GORGEOUS MULTI-DENSITY PLOT GENERATED SUCCESSFULLY: {out_path}")
