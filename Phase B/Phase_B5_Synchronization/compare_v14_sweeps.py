"""
Side-by-side comparison of the OLD (pre-fix) and NEW (fixed) V14 density sweeps.
Run AFTER you have re-run evaluate_v14_densities.py with the double-count fix.

Usage:
    python compare_v14_sweeps.py
"""
import os
import pandas as pd

base = os.path.join("v10_IEEE_Final", "results", "v14_sweep")
old_path = os.path.join(base, "v14_density_sweep_metrics_OLD.csv")
new_path = os.path.join(base, "v14_density_sweep_metrics.csv")

if not os.path.exists(old_path):
    print(f"[!] OLD backup not found at {old_path}")
    print("    Did you back up the original CSV before re-running? See instructions.")
    raise SystemExit(1)
if not os.path.exists(new_path):
    print(f"[!] NEW CSV not found at {new_path} - run evaluate_v14_densities.py first.")
    raise SystemExit(1)

old = pd.read_csv(old_path)
new = pd.read_csv(new_path)

cmp = pd.DataFrame({
    "density": old["density"],
    "OLD_success%": (old["success_rate"] * 100).round(2),
    "NEW_success%": (new["success_rate"] * 100).round(2),
    "succ_delta": ((new["success_rate"] - old["success_rate"]) * 100).round(2),
    "OLD_timeout%": (old["timeout_rate"] * 100).round(2),
    "NEW_timeout%": (new["timeout_rate"] * 100).round(2),
    "time_delta": ((new["timeout_rate"] - old["timeout_rate"]) * 100).round(2),
})

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)
print("\n=== V14 sweep: OLD (pre-fix) vs NEW (fixed) ===\n")
print(cmp.to_string(index=False))

max_shift = cmp["succ_delta"].abs().max()
print("\n" + "=" * 60)
if max_shift < 0.5:
    print(f"VERDICT: max success shift = {max_shift:.2f}pp  ->  OLD CSV was effectively correct.")
else:
    print(f"VERDICT: max success shift = {max_shift:.2f}pp  ->  OLD CSV was BUGGY. Use the NEW numbers.")
print("=" * 60)
