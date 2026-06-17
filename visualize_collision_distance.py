import os
import glob
import pandas as pd
import matplotlib.pyplot as plt

def find_latest_csv(results_dir="results"):
    """Return the most recent CSV file under results directory.
    The probe_speed_oracle saves CSVs under results/phase_c_probe/.
    """
    pattern = os.path.join(results_dir, "**", "*.csv")
    csv_files = glob.glob(pattern, recursive=True)
    if not csv_files:
        raise FileNotFoundError("No CSV files found under the results directory.")
    # Pick the newest by modification time
    latest = max(csv_files, key=os.path.getmtime)
    return latest

def main():
    try:
        csv_path = find_latest_csv()
        print(f"Loading CSV: {csv_path}")
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return

    # Expect a column named 'dist_to_rammer_at_collision' (added by the env)
    col_name = None
    for possible in ["dist_to_rammer_at_collision", "dist_to_rammer", "dist_to_rammer_at_coll"]:
        if possible in df.columns:
            col_name = possible
            break
    if col_name is None:
        print("Column with distance to rammer not found in CSV. Available columns:")
        print(df.columns.tolist())
        return

    distances = df[col_name].dropna()
    if distances.empty:
        print("No distance data to plot.")
        return

    plt.figure(figsize=(8, 5))
    plt.hist(distances, bins=30, color="#4A90E2", edgecolor="black", alpha=0.7)
    plt.title("Collision Distance to Rammer Distribution")
    plt.xlabel("Distance to Rammer (m)")
    plt.ylabel("Number of Collisions")
    plt.grid(True, linestyle='--', alpha=0.5)
    out_path = os.path.join(os.path.dirname(csv_path), "collision_distance_histogram.png")
    plt.tight_layout()
    plt.savefig(out_path)
    print(f"Histogram saved to {out_path}")
    plt.show()

if __name__ == "__main__":
    main()
