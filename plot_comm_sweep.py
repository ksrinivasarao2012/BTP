"""
Plot the communication-range sensitivity curve.

Reads results/comm_sweep/comm*.csv (produced by eval_comm.py for each range)
and draws success rate vs communication range, one line per density.

Usage:
    python plot_comm_sweep.py
"""
import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

RES_DIR = os.path.join("results", "comm_sweep")
INF_PLOT_X = 12.0   # where to draw the "unlimited" point on the x-axis


def main():
    files = sorted(glob.glob(os.path.join(RES_DIR, "comm*_metrics.csv")))
    if not files:
        print(f"[!] No result CSVs in {RES_DIR}. Run eval_comm.py for each range first.")
        return

    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

    # x position for plotting: inf -> INF_PLOT_X
    df["x"] = df["comm_range"].apply(lambda r: INF_PLOT_X if r >= 1e8 else r)
    df = df.sort_values("x")

    print("\n=== Communication-range sweep (success %) ===")
    pivot = df.pivot_table(index="comm_label", columns="density", values="success_rate") * 100
    print(pivot.round(2).to_string())

    plt.rcParams.update({'font.size': 12, 'axes.edgecolor': '#cccccc'})
    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=300)

    for density in sorted(df["density"].unique()):
        sub = df[df["density"] == density].sort_values("x")
        ax.plot(sub["x"], sub["success_rate"] * 100, marker='o', linewidth=2,
                label=f"density {density:.2f}")

    # x ticks: numeric ranges + an "inf" label at INF_PLOT_X
    xticks = sorted(df["x"].unique())
    xlabels = ["∞" if abs(t - INF_PLOT_X) < 1e-6 else f"{t:g}" for t in xticks]
    ax.set_xticks(xticks)
    ax.set_xticklabels(xlabels)

    ax.set_xlabel("Communication range (m)")
    ax.set_ylabel("Success rate (%)")
    ax.set_title("Swarm success vs communication range")
    ax.set_ylim(0, 105)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend()

    # mark the chosen operating point (8 m) if present
    if (df["x"] == 8.0).any():
        ax.axvline(8.0, color='green', linestyle=':', alpha=0.6)
        ax.text(8.0, 5, " chosen: 8 m", color='green', fontsize=10, rotation=90, va='bottom')

    out = os.path.join(RES_DIR, "comm_range_sensitivity.png")
    plt.tight_layout()
    plt.savefig(out)
    plt.close()
    print(f"\n[OK] figure saved: {out}")


if __name__ == "__main__":
    main()
