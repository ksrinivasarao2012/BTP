import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shutil

csv_file = "master_B5_evaluation_results_20260517_141922.csv"
results_dir = "results/v8"
os.makedirs(results_dir, exist_ok=True)

# Save obstacle density preference file
with open(os.path.join(results_dir, "obstacle_density.txt"), "w") as f:
    f.write("0.35")

# Copy CSV to results/v8/
shutil.copy(csv_file, os.path.join(results_dir, csv_file))
print(f"✅ Copied CSV to: {os.path.join(results_dir, csv_file)}")

df = pd.read_csv(csv_file)
timestamp = "20260517_141922"

# Set clean, professional typography and size
plt.rcParams.update({
    'font.size': 11,
    'font.family': 'sans-serif',
    'axes.edgecolor': '#cccccc',
    'axes.linewidth': 0.8
})

metrics = ["Success_Rate", "Collision_Rate", "Timeout_Rate"]
categories = ["Success", "Collision", "Timeout"]

r_means = [df[df["Mode"] == "random"][m].mean() for m in metrics]
r_stds = [df[df["Mode"] == "random"][m].std() for m in metrics]

c_means = [df[df["Mode"] == "clustered"][m].mean() for m in metrics]
c_stds = [df[df["Mode"] == "clustered"][m].std() for m in metrics]

r_stds = [0.0 if np.isnan(s) else s for s in r_stds]
c_stds = [0.0 if np.isnan(s) else s for s in c_stds]

x = np.arange(len(categories))
width = 0.35

fig, ax = plt.subplots(figsize=(9, 6.5), dpi=300)

# Harmonious modern colors (Sleek Teal for Random, Vibrant Coral for Clustered)
rects1 = ax.bar(x - width/2, r_means, width, yerr=r_stds, label='Random Spawn',
                color='#008080', edgecolor='none', alpha=0.9, capsize=5,
                error_kw=dict(ecolor='#333333', lw=1.5, capthick=1.5))

rects2 = ax.bar(x + width/2, c_means, width, yerr=c_stds, label='Cluster Spawn',
                color='#FF6F61', edgecolor='none', alpha=0.9, capsize=5,
                error_kw=dict(ecolor='#333333', lw=1.5, capthick=1.5))

# Add labels, title and custom x-axis tick labels
ax.set_ylabel('Percentage (%)', fontsize=12, fontweight='bold', labelpad=10)
ax.set_title('Decentralized Swarm Navigation Performance: Phase B Master Model (v8)', 
             fontsize=13, fontweight='bold', pad=20, color='#111111')
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=11, fontweight='bold')
ax.set_ylim(0, 105)

# Sleek legend and grid
ax.legend(frameon=True, facecolor='white', edgecolor='none', shadow=True, loc='upper right')
ax.grid(axis='y', linestyle='--', alpha=0.5, color='#dddddd')

# Attach a text label display
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.1f}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9.5, fontweight='bold')
                    
autolabel(rects1)
autolabel(rects2)

# Despine top and right axes for modern minimalist look
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()

png_filename = f"master_B5_evaluation_comparison_{timestamp}.png"
png_path = os.path.join(results_dir, png_filename)
plt.savefig(png_path, bbox_inches='tight')
plt.close()
print(f"✅ Comparison plot successfully saved to: {png_path}")
