"""
Dump the GROUND-TRUTH PPO hyperparameters embedded in a trained checkpoint.
This avoids guessing from the (overloaded) v10->v14 trainer lineage — the .zip stores what was
actually used. Usage:
  python dump_hparams.py models/apex_ultra_glide_v14_comm8_lidar_final.zip
"""
import sys, os
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
from stable_baselines3 import PPO

path = sys.argv[1] if len(sys.argv) > 1 else "models/apex_ultra_glide_v14_comm8_lidar_final.zip"
m = PPO.load(path, device="cpu")

def val(x):
    try:
        return x(1.0) if callable(x) else x      # unwrap SB3 schedules (lr, clip_range)
    except Exception:
        return x

print(f"\n=== PPO hyperparameters embedded in {os.path.basename(path)} ===")
for k in ["gamma", "n_steps", "batch_size", "n_epochs", "gae_lambda",
          "clip_range", "clip_range_vf", "ent_coef", "vf_coef",
          "learning_rate", "max_grad_norm", "n_envs"]:
    print(f"  {k:16s} = {val(getattr(m, k, '?'))}")
print(f"  lr_schedule(1.0) = {val(getattr(m, 'lr_schedule', '?'))}")
try:
    print(f"  net_arch        = {m.policy.net_arch}")
except Exception:
    pass
print("=" * 60)
