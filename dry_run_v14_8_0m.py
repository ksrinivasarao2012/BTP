"""
Lightweight pre-flight check for the V14_8.0m run.
Does NOT start training. Loads the warm-start model, builds ONE env,
resets, and runs a few steps to confirm the full pipeline works.
"""
import os
import numpy as np

# Safe imports (train module is __main__-guarded, so this won't train)
from train_step_B10_extended_v14_8_0m import MAPPO_Policy_B5
from swarm_env_step_B10_8_0m import SwarmLidarEnv_StepB10_8_0m
from stable_baselines3 import PPO

print("[1] Imports OK")

# --- locate warm-start model ---
candidates = [
    "models/apex_ultra_glide_v14_final.zip",
    os.path.join("Phase B", "Phase_B5_Synchronization", "models", "apex_ultra_glide_v14_final.zip"),
    os.path.join("v10_IEEE_Final", "v14_Best_Model_Archive", "model", "apex_ultra_glide_v14_final.zip"),
]
model_path = next((p for p in candidates if os.path.exists(p)), None)
assert model_path, f"v14 model not found in: {candidates}"
print(f"[2] Found warm-start model: {model_path}")

# --- load model with custom policy ---
model = PPO.load(model_path, custom_objects={"policy_class": MAPPO_Policy_B5}, device="cpu")
print("[3] PPO.load + custom policy OK")

# --- build ONE env, confirm comm range, reset ---
env = SwarmLidarEnv_StepB10_8_0m(render_mode=None, target_density=0.30)
print(f"[4] Env built. communication_range = {env.communication_range} m | n_drones = {env.n_drones}")
obs_dict, infos = env.reset()
print(f"[5] reset() OK. agents = {len(obs_dict)} | obs dim = {next(iter(obs_dict.values())).shape}")

# --- run a few steps (mirrors eval batching) ---
finished = set()
for step in range(15):
    active = [a for a in obs_dict.keys() if a not in finished]
    if not active:
        break
    obs_batch = np.array([obs_dict[a] for a in active])
    action_batch, _ = model.predict(obs_batch, deterministic=True)
    action_dict = {a: action_batch[i] for i, a in enumerate(active)}
    obs_dict, rews, terms, truncs, infos = env.step(action_dict)
    for a in active:
        if terms.get(a, False) or truncs.get(a, False):
            finished.add(a)
print(f"[6] Ran {step+1} steps OK. action shape = {action_batch.shape} | terminated = {len(finished)}")
env.close()
print("\n[PASS] Full pipeline works: model load -> env -> reset -> predict -> step. Safe to run training.")
