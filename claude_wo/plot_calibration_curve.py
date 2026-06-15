"""
Calibration figure — all-agent BFS solvability vs obstacle density.
Reads final_validation_results_*.csv (1000 maps/point, 5 batches) and produces
an IEEE-quality figure: both spawn modes, 95% CI error bars, 90% feasibility
threshold line, and the calibrated density ceilings marked.

Outputs: calibration_solvability_curve.png (300 dpi) + .pdf (vector for LaTeX)
"""

import sys
import glob
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Locate the CSV (newest final_validation_results_*.csv unless given) ─────────
CSV = sys.argv[1] if len(sys.argv) > 1 else None
if CSV is None:
    matches = sorted(glob.glob("final_validation_results_*.csv"))
    if not matches:
        raise SystemExit("No final_validation_results_*.csv found.")
    CSV = matches[-1]
print(f"Reading: {CSV}")

df = pd.read_csv(CSV)

# Per (mode, density): mean, std, 95% CI (constant within group — take first).
g = (df.groupby(['mode', 'density'])
       .agg(mean_pct=('mean_pct', 'first'),
            std_pct=('std_pct', 'first'),
            ci95=('ci95', 'first'))
       .reset_index())

# ── Styling (IEEE single-column) ───────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.linewidth": 0.8,
    "mathtext.fontset": "dejavuserif",
})
# Colorblind-safe (Wong): blue, vermillion
STYLE = {
    'clustered': dict(color='#0072B2', marker='o', ls='-',  label='Clustered'),
    'scattered': dict(color='#D55E00', marker='s', ls='--', label='Scattered'),
}

fig, ax = plt.subplots(figsize=(3.5, 2.7), dpi=300)

ceilings = {}
for mode in ['clustered', 'scattered']:
    sub = g[g['mode'] == mode].sort_values('density')
    if sub.empty:
        continue
    x = sub['density'].values
    y = sub['mean_pct'].values
    yerr = sub['ci95'].values
    st = STYLE[mode]
    ax.errorbar(x, y, yerr=yerr, capsize=2.5, capthick=0.8, elinewidth=0.8,
                lw=1.3, ms=4.5, color=st['color'], marker=st['marker'],
                ls=st['ls'], label=st['label'], zorder=3)
    # ceiling = highest density with mean >= 90
    feasible = sub[sub['mean_pct'] >= 90.0]
    if not feasible.empty:
        ceilings[mode] = float(feasible['density'].max())

# 90% feasibility threshold
ax.axhline(90.0, color='0.4', ls=':', lw=1.0, zorder=1)
ax.text(g['density'].min(), 90.6, '90% feasibility threshold',
        fontsize=7, color='0.35', va='bottom', ha='left')

# Mark ceilings with a star + leader-arrow label placed in open lower-left space
# (keeps the two labels from colliding near the top of the plot).
ANNOT = {
    'scattered': (0.158, 74),
    'clustered': (0.205, 63),
}
for mode, dens in ceilings.items():
    row = g[(g['mode'] == mode) & (g['density'] == dens)].iloc[0]
    yv = row['mean_pct']
    col = STYLE[mode]['color']
    ax.plot([dens], [yv], marker='*', ms=11, color=col,
            markeredgecolor='white', markeredgewidth=0.6, zorder=5)
    ax.annotate(f"{mode} ceiling = {dens:g}",
                xy=(dens, yv), xytext=ANNOT[mode],
                fontsize=7, color=col, fontweight='bold', ha='left', va='center',
                arrowprops=dict(arrowstyle='->', color=col, lw=0.9,
                                shrinkA=1, shrinkB=4))

ax.set_xlabel("Obstacle density")
ax.set_ylabel("All-agent BFS solvability (%)")
ax.set_xticks(sorted(g['density'].unique()))
ax.set_ylim(45, 104)
ax.grid(True, ls='-', lw=0.4, alpha=0.25)
ax.legend(loc='lower left', fontsize=8, frameon=True, framealpha=0.9,
          edgecolor='0.8', handlelength=2.2)
fig.tight_layout(pad=0.4)

for ext in ('png', 'pdf'):
    out = f"calibration_solvability_curve.{ext}"
    fig.savefig(out, bbox_inches='tight')
    print(f"Saved: {out}")

# Console echo of what the figure shows
print("\nCeilings (highest density with mean >= 90%):")
for mode in ['clustered', 'scattered']:
    if mode in ceilings:
        row = g[(g['mode'] == mode) & (g['density'] == ceilings[mode])].iloc[0]
        print(f"  {mode:10s}: {ceilings[mode]:g}  "
              f"({row['mean_pct']:.1f}% +/- {row['std_pct']:.1f}%, "
              f"95% CI +/-{row['ci95']:.1f}%)")
