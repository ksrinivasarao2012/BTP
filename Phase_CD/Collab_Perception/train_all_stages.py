"""
Master trainer: chains all 6 stages (ON 0,1,2 then OFF 0,1,2) automatically.
No pauses. Set it and sleep. Saves each stage model.

Usage:
  python train_all_stages.py

That's it. Runs: ON 0 → ON 1 → ON 2 → OFF 0 → OFF 1 → OFF 2
Each stage saves its model. Total ~3M steps, 10 cores.
"""
import subprocess
import sys
import time

STAGES = [
    ("on",  0),
    ("on",  1),
    ("on",  2),
    ("off", 0),
    ("off", 1),
    ("off", 2),
]

def run_stage(mode, stage):
    """Run a single stage via train_slot_fusion.py"""
    cmd = [
        sys.executable,
        "Phase_CD/Collab_Perception/train_slot_fusion.py",
        mode,
        str(stage)
    ]
    print(f"\n{'='*70}")
    print(f"Starting: {' '.join(cmd)}")
    print(f"{'='*70}\n")
    result = subprocess.run(cmd, cwd="D:/Swarm/BTP")
    return result.returncode == 0


def main():
    print(f"\n{'='*70}")
    print("SLOT-FUSION FULL CURRICULUM (all 6 stages)")
    print(f"{'='*70}")
    print("Stages to run:")
    for mode, stage in STAGES:
        print(f"  {mode.upper()} Stage {stage}")
    print(f"{'='*70}\n")

    start_time = time.time()
    failed = []

    for i, (mode, stage) in enumerate(STAGES):
        print(f"\n[{i+1}/{len(STAGES)}] Running {mode.upper()} Stage {stage}...")
        if not run_stage(mode, stage):
            print(f"[!] FAILED: {mode.upper()} Stage {stage}")
            failed.append((mode, stage))
            break  # Stop on failure
        else:
            print(f"[OK] {mode.upper()} Stage {stage} complete")

    elapsed = time.time() - start_time
    hours = elapsed / 3600.0

    print(f"\n{'='*70}")
    print(f"CURRICULUM FINISHED")
    print(f"{'='*70}")
    print(f"Total time: {hours:.1f} hours")

    if failed:
        print(f"\nFailed stages: {failed}")
        print("[!] Training did not complete all 6 stages.")
        sys.exit(1)
    else:
        print(f"\n[✓] All 6 stages trained successfully!")
        print("\nModels saved:")
        print("  models/raster_slot_fusion_ON_stage0_final.zip")
        print("  models/raster_slot_fusion_ON_stage1_final.zip")
        print("  models/raster_slot_fusion_ON_stage2_final.zip")
        print("  models/raster_slot_fusion_OFF_stage0_final.zip")
        print("  models/raster_slot_fusion_OFF_stage1_final.zip")
        print("  models/raster_slot_fusion_OFF_stage2_final.zip")
        print("\nNext: run hardened eval (n=500, CI)")
        print("  $py eval_slot_fusion_zero_shot.py models/raster_slot_fusion_ON_stage2_final.zip 500")
        print("  $py eval_slot_fusion_zero_shot.py models/raster_slot_fusion_OFF_stage2_final.zip 500")


if __name__ == "__main__":
    main()
