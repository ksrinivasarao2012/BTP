import os
import sys

# --- run from anywhere: put repo root and script folder on path + resolve relative paths ---
_HERE = os.path.dirname(os.path.abspath(__file__))
_PHASE_CD = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_PHASE_CD)
for _p in (_ROOT, _PHASE_CD, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.chdir(_ROOT)

import torch
import numpy as np
import pandas as pd
from stable_baselines3 import PPO

# Load the trained model
model_path = "models/collab_l5_c10_hazardON_final.zip"
if not os.path.exists(model_path):
    print(f"Model not found at {model_path}")
    exit(1)

from Phase_CD.Collab_Perception.train_collab import MAPPO_Policy_B5

model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")
# Extract the first layer weights of the policy net
# Shape is [64, 677] (677 input features, 64 hidden units)
weights = model.policy.mlp_extractor.policy_net[0].weight.data.numpy()

# Absolute weights
abs_weights = np.abs(weights)

# Feature blocks:
# 1. Local State (0-129)
# 2. Shared Hazard slots (130-156)
# 3. Global State (157-676)
local_mean = np.mean(abs_weights[:, :130])
hazard_mean = np.mean(abs_weights[:, 130:157])
global_mean = np.mean(abs_weights[:, 157:])

print("=== Mean Absolute Weight Magnitudes (First Layer) ===")
print(f"Local State (dims 0-129):     {local_mean:.6f}")
print(f"Shared Hazard (dims 130-156):  {hazard_mean:.6f}")
print(f"Global State (dims 157-676):  {global_mean:.6f}")
print("=====================================================")

# Breakdown per neighbor slot (each has 3 dimensions)
print("\n=== Shared Hazard Block (Breakdown per Neighbor Slot) ===")
for slot in range(9):
    idx = 130 + slot * 3
    slot_mean = np.mean(abs_weights[:, idx:idx+3])
    print(f"  Slot {slot} (neighbor {slot}): {slot_mean:.6f}")
print("=========================================================")
