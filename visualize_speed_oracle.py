# visualize_speed_oracle.py

"""Visualization script for the speed‑oracle probe results.

The probe writes a CSV file (default path:
`results/phase_c_probe/oracle_speed_f{f}_b{boost:.2f}.csv`) with the
following columns:
    density, f, boost, oracle_success, timeout, collision,
    collision_drone, collision_obstacle

This script loads that CSV and produces two quick visualisations:
1. **Stacked bar chart** showing the breakdown of collisions (drone vs.
   obstacle) for each density.
2. **Line plot** of success, timeout and total collision percentages.

Run it from the repository root (or adjust the `csv_path` variable):

```bash
python visualize_speed_oracle.py
```

If you want to visualise a specific boost or number of traitors, edit the
`csv_path` accordingly.
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt

# ------------------------------------------------------------
# Configuration – adjust if you saved the CSV elsewhere.
# ------------------------------------------------------------
# Example default CSV name (matches probe_speed_oracle.py output)
DEFAULT_CSV = os.path.join("results", "phase_c_probe", "oracle_speed_f2_b1.40.csv")

# Allow overriding via command line argument
csv_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV

if not os.path.isfile(csv_path):
    print(f"[!] CSV file not found: {csv_path}")
    sys.exit(1)

# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------
df = pd.read_csv(csv_path)
# Ensure numeric sorting by density (and optionally by boost)
df = df.sort_values(by=["density", "boost"])

# ------------------------------------------------------------
# Plot 1 – Stacked bar chart of collision sub‑types
# ------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 5))
indices = range(len(df))
width = 0.6

# Bottom bar: obstacle collisions
ax.bar(
    indices,
    df["collision_obstacle"],
    width,
    label="Obstacle Collision",
    color="#ff6f61",
)
# Top bar: drone collisions stacked on top of obstacle
ax.bar(
    indices,
    df["collision_drone"],
    width,
    bottom=df["collision_obstacle"],
    label="Drone Collision",
    color="#6b5b95",
)

ax.set_xticks(indices)
ax.set_xticklabels([f"{d:.2f}" for d in df["density"]], rotation=45)
ax.set_ylabel("Collision %")
ax.set_xlabel("Density (drones / area)")
ax.set_title("Collision breakdown by density")
ax.legend()

plt.tight_layout()
plt.savefig("collision_breakdown.png")
print("[OK] saved: collision_breakdown.png")

# ------------------------------------------------------------
# Plot 2 – Success / Timeout / Total Collision trends
# ------------------------------------------------------------
fig2, ax2 = plt.subplots(figsize=(8, 5))
ax2.plot(df["density"], df["oracle_success"], marker="o", label="Success")
ax2.plot(df["density"], df["timeout"], marker="s", label="Timeout")
ax2.plot(df["density"], df["collision"], marker="^", label="Collision")

ax2.set_xlabel("Density (drones / area)")
ax2.set_ylabel("Percentage %")
ax2.set_title("Oracle performance metrics by density")
ax2.legend()

plt.tight_layout()
plt.savefig("performance_trends.png")
print("[OK] saved: performance_trends.png")

# ------------------------------------------------------------
# Optional: Show plots interactively (comment out if running headless)
# ------------------------------------------------------------
# plt.show()
