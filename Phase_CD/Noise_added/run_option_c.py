"""
OPTION C — one-shot runner: trains the noise-robust model (stage 0 -> 1) then runs both noise evals.
Set it and sleep. Stops immediately if any step fails.

Pipeline:
  1. train_noise_robust.py 0        (1.5M steps, sigma~U[0,0.3])
  2. train_noise_robust.py 1        (2.0M steps, sigma~U[0,0.6])
  3. eval_noise_robust.py <model> <n_maps> 2 <workers> wall
  4. eval_noise_robust.py <model> <n_maps> 2 <workers> camouflage

Usage:
  python run_option_c.py                 # defaults: eval 150 maps, 10 workers
  python run_option_c.py 200 10          # eval n_maps=200, workers=10
"""
import os
import sys
import time
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
PY = sys.executable
MODEL = "models/noise_robust_ON_stage1_final.zip"


def run(step_name, args):
    cmd = [PY] + args
    print(f"\n{'='*72}\n>>> {step_name}\n    {' '.join(cmd)}\n{'='*72}", flush=True)
    t0 = time.time()
    rc = subprocess.run(cmd, cwd=_ROOT).returncode
    dt = (time.time() - t0) / 60.0
    if rc != 0:
        print(f"\n[!] FAILED: {step_name} (exit {rc}) after {dt:.1f} min. Stopping.")
        sys.exit(1)
    print(f"[OK] {step_name} done in {dt:.1f} min.")


def main():
    n_maps = sys.argv[1] if len(sys.argv) > 1 else "150"
    workers = sys.argv[2] if len(sys.argv) > 2 else "10"
    t_start = time.time()

    train = os.path.join("Phase_CD", "Noise_added", "train_noise_robust.py")
    eval_ = os.path.join("Phase_CD", "Noise_added", "eval_noise_robust.py")

    print(f"\n{'#'*72}\n# OPTION C PIPELINE — train (2 stages) + eval (wall, camouflage)\n"
          f"# eval: {n_maps} maps/cond, {workers} workers, k=2\n{'#'*72}")

    run("Stage 0 — light-noise fine-tune", [train, "0"])
    run("Stage 1 — full-noise fine-tune", [train, "1"])
    run("Eval — WALL attack vs noise",        [eval_, MODEL, n_maps, "2", workers, "wall"])
    run("Eval — CAMOUFLAGE attack vs noise",  [eval_, MODEL, n_maps, "2", workers, "camouflage"])

    hrs = (time.time() - t_start) / 3600.0
    print(f"\n{'#'*72}\n# OPTION C COMPLETE in {hrs:.1f} h")
    print(f"# Noise-robust model: {MODEL}")
    print(f"# Next: paste the two eval tables; update PAPER_MASTER_PLAN.md (S5.6-5.8, S12).\n{'#'*72}")


if __name__ == "__main__":
    main()
