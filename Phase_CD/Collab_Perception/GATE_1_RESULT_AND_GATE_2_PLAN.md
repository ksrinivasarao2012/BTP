# Gate 1 Result + Gate 2 Step-by-Step Plan (CORRECTED)

**Owner:** Srinivasa  
**Date:** 2026-06-18  
**Status:** Gate 1 ZERO-SHOT EVIDENCE ✅ — Architecture fix validated. Next: train a fair OFF baseline + hardened eval to prove communication is load-bearing.

---

## Gate 1 Result — Slot-Fusion Zero-Shot ON/OFF

**Command run:**
```powershell
python eval_slot_fusion_zero_shot.py models\apex_ultra_glide_v14_comm8_lidar_final.zip 200
```

**Regime:** 8m LiDAR, dropout=0.10/sustain=5 (≈33% blind, realistic)

**Results:**
```
ON  (slot fusion + shared):   93.55%
OFF (own LiDAR only):         54.70%
Difference (ON - OFF):       +38.85 pp
```

**What this proves (zero-shot):**
1. ✅ The slot-fusion architecture works (no CTDE leakage, single `_cast48` at right scale)
2. ✅ Reusing M0's 130-d actor is sufficient (no new architecture, no surgery)
3. ✅ The shared map information is useful when placed in the slot the policy reads
4. ⚠️ **But:** this is a same-weights ablation. True proof comes after training fair ON/OFF baselines.

**Next:** Gate 2 — train ON and OFF models, then hardened eval (n=500, CI). Only then is "communication is load-bearing" fully justified.

---

## CRITICAL FIXES BEFORE GATE 2 (MUST DO FIRST)

### Fix 0: Ego-range inconsistency in `_fused_lidar`

**Problem:** Current `_fused_lidar` casts at `collab_range` (12m), but M0 was trained on `[6:54]` at 8m. Training now bakes in a sighted ego that sees 12m instead of 8m — a regime change.

**Fix:** In `swarm_env_raster.py`, update `_fused_lidar` to cast at **8m (`lidar_range`)**, not 12m:

```python
def _fused_lidar(self, idx):
    """Single _cast48 at 8m scale (ego's training regime, M0's native [6:54] scale).
    
    Union: {ego obstacles (if sighted), sender-gated neighbor obstacles, drones}
    Cast at lidar_range (8m), matching M0's training.
    """
    pos = self.positions[idx]
    c_list, r_list = [], []

    # Ego's own obstacles (only if sighted)
    if not self.lidar_blind[idx] and self.obstacles:
        arr = np.array(self.obstacles, dtype=np.float32)
        c_list.append(arr[:, :2])
        r_list.append(arr[:, 2])

    # Sender-gated neighbor obstacles
    if self.obstacles:
        arr = np.array(self.obstacles, dtype=np.float32)
        centers, radii = arr[:, :2], arr[:, 2]
        keep = np.zeros(len(centers), dtype=bool)
        for j in range(self.n_drones):
            if j == idx or self.possible_agents[j] not in self.agents:
                continue
            if self.lidar_blind[j]:
                continue
            if np.linalg.norm(pos - self.positions[j]) > self.communication_range:
                continue
            dj = np.linalg.norm(centers - self.positions[j], axis=1)
            keep |= (dj <= self.lidar_range)
        if keep.any():
            c_list.append(centers[keep])
            r_list.append(radii[keep])

    # Drones
    others = [j for j in range(self.n_drones) if j != idx and self.possible_agents[j] in self.agents]
    if others:
        c_list.append(self.positions[others])
        r_list.append(np.full(len(others), self.drone_radius, dtype=np.float32))

    # Cast at 8m (lidar_range, M0's native scale), not 12m
    if c_list:
        centers = np.concatenate(c_list)
        radii = np.concatenate(r_list)
    else:
        centers = np.empty((0, 2), np.float32)
        radii = np.empty((0,), np.float32)
    
    return self._cast48(pos, centers, radii, self.lidar_range) / self.lidar_range
```

Also update the OFF arm in `_observe` to cast at 8m:

```python
        else:
            # OFF: ego obstacles only + drones, at 8m scale (fair baseline)
            pos = self.positions[idx]
            c_list, r_list = [], []
            if not self.lidar_blind[idx] and self.obstacles:
                arr = np.array(self.obstacles, dtype=np.float32)
                c_list.append(arr[:, :2])
                r_list.append(arr[:, 2])
            others = [j for j in range(self.n_drones) if j != idx and self.possible_agents[j] in self.agents]
            if others:
                c_list.append(self.positions[others])
                r_list.append(np.full(len(others), self.drone_radius, dtype=np.float32))
            if c_list:
                centers = np.concatenate(c_list)
                radii = np.concatenate(r_list)
            else:
                centers = np.empty((0, 2), np.float32)
                radii = np.empty((0,), np.float32)
            fused = self._cast48(pos, centers, radii, self.lidar_range) / self.lidar_range
```

**After this fix, verify:**
```powershell
$py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
cd "D:\Swarm\BTP"
# Quick sanity: ON should still be ~93%, OFF ~54%
& $py Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py models\apex_ultra_glide_v14_comm8_lidar_final.zip 50
```

---

## Gate 2 Step-by-Step Plan — Light Fine-Tune (3 stages, ~1.5M total steps)

**Goal:** Train ON and OFF models, then prove communication is load-bearing with honest statistics.

**Key decisions:**
- No surgery, no new architecture (reuse M0's 130-d actor)
- Training: ON arm with neighbors, OFF arm without (fair comparison)
- Evaluation: ON vs OFF with n=500, seeded dropout, CI (not FI gates)
- Dropout regime: 0.10 → 0.15 → 0.20 (33% → 45% → 60% blind)

---

## Step 1: Create `train_slot_fusion.py`

**File:** `D:\Swarm\BTP\Phase_CD\Collab_Perception\train_slot_fusion.py`

This script loads M0, chains stages, and trains ON or OFF arm. Adapted from `train_raster.py` but for 130-d slot-fusion models.

**Key requirements:**
- Load M0 (or previous stage checkpoint)
- Use `MultiProcessRasterEnv` (from `train_raster.py`) to handle PettingZoo 10-agent env
- Chain stages: Stage 1/2 load their previous checkpoint, not restart from M0
- Save to `models/raster_slot_fusion_{ON|OFF}_stage{0|1|2}_final.zip`

**See full template below** (copy from `train_raster.py` and adapt lines marked ADAPT).

---

## Step 2: Train ON arm, Stage 0 (500k steps, dropout=0.10)

**Command:**
```powershell
$py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
cd "D:\Swarm\BTP"
& $py Phase_CD\Collab_Perception\train_slot_fusion.py 500000 on 0
```

**What happens:**
- Loads M0 (first time), or `models/raster_slot_fusion_ON_stage0_final.zip` if resuming
- Trains with `slot_fusion=True, use_shared_map=True, dropout=0.10, sustain=5`
- Saves: `models/raster_slot_fusion_ON_stage0_final.zip`

**After this step (on Haiku's approval), measure:**
```powershell
& $py Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py models\raster_slot_fusion_ON_stage0_final.zip 200
```

Report ON, OFF, and ON−OFF. ✅ Gate passes if ON−OFF ≥ 10 pp (learning is working).

---

## Step 3: Train ON arm, Stage 1 (500k steps, dropout=0.15)

**Command:**
```powershell
& $py Phase_CD\Collab_Perception\train_slot_fusion.py 500000 on 1
```

**What happens:**
- Loads `models/raster_slot_fusion_ON_stage0_final.zip` (continues from Stage 0)
- Trains with dropout=0.15
- Saves: `models/raster_slot_fusion_ON_stage1_final.zip`

**After this step, measure:**
```powershell
& $py Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py models\raster_slot_fusion_ON_stage1_final.zip 200
```

✅ Gate passes if ON−OFF still ≥ 10 pp (no collapse under higher dropout).

---

## Step 4: Train ON arm, Stage 2 (500k steps, dropout=0.20)

**Command:**
```powershell
& $py Phase_CD\Collab_Perception\train_slot_fusion.py 500000 on 2
```

**Loads Stage 1, trains with dropout=0.20, saves Stage 2 final.**

**After this step, measure:**
```powershell
& $py Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py models\raster_slot_fusion_ON_stage2_final.zip 200
```

✅ Gate passes if ON−OFF ≥ 10 pp (policy is robust to high blindness).

---

## Step 5: Train OFF arm (Stages 0–2, same schedule)

**Commands (one stage at a time):**
```powershell
& $py Phase_CD\Collab_Perception\train_slot_fusion.py 500000 off 0
& $py Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py models\raster_slot_fusion_OFF_stage0_final.zip 200

& $py Phase_CD\Collab_Perception\train_slot_fusion.py 500000 off 1
& $py Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py models\raster_slot_fusion_OFF_stage1_final.zip 200

& $py Phase_CD\Collab_Perception\train_slot_fusion.py 500000 off 2
& $py Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py models\raster_slot_fusion_OFF_stage2_final.zip 200
```

**Expected:** OFF training should show lower ON−OFF (no benefit from neighbors, as expected). OFF final should achieve ~55–60% solo success.

---

## Step 6: Hardened Gate 3 Eval (n=500, CI)

**Extend `eval_slot_fusion_zero_shot.py` to support n≥500 and bootstrap CI.**

**Commands (after ON/OFF training complete):**
```powershell
& $py Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py models\raster_slot_fusion_ON_stage2_final.zip 500
& $py Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py models\raster_slot_fusion_OFF_stage2_final.zip 500
```

**Output should include:**
- ON success rate
- OFF success rate
- ON−OFF point estimate
- 95% bootstrap CI on the difference
- Interpretation: CI lower bound > 0?

**Expected:**
- ON: ~95–97%
- OFF: ~55–60%
- ON−OFF: ~35–40 pp
- 95% CI: [lower_bound, upper_bound], lower_bound > 0

**Final decision gate:** ✅ CI lower bound > 0 AND ON−OFF ≥ 10 pp?
- **YES** → "Communication is load-bearing (trained models, fair baseline, honest stats)." Proceed to **Phase 4: Trust module + traitor attacks**.
- **NO** → Reassess (extend training, adjust dropout schedule, or fall back to OPTION_1).

---

## Training Script: `train_slot_fusion.py` (CORRECTED)

```python
"""
Light fine-tune of M0 for slot-fusion architecture.
Chains stages: Stage 1/2 load their previous checkpoint, not M0.
Uses MultiProcessRasterEnv (from train_raster.py) to handle PettingZoo ParallelEnv.

Usage: python train_slot_fusion.py [steps] [on|off] [stage] [--resume]
"""
import os, sys
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"
sys.path.insert(0, "../../")
import numpy as np
from stable_baselines3 import PPO
import torch.nn as nn
from stable_baselines3.common.policies import ActorCriticPolicy

# ---- COPY from train_raster.py / eval_slot_fusion_zero_shot.py ----
class MAPPO_Extractor_M0(nn.Module):
    def __init__(self, features_dim, net_arch, activation_fn):
        super().__init__()
        LOCAL, GLOBAL = 130, 520
        pi_layers, last = [], LOCAL
        for d in net_arch['pi']:
            pi_layers += [nn.Linear(last, d), activation_fn()]; last = d
        self.policy_net = nn.Sequential(*pi_layers)
        vf_layers, last_vf = [], GLOBAL
        for d in net_arch['vf']:
            vf_layers += [nn.Linear(last_vf, d), activation_fn()]; last_vf = d
        self.value_net = nn.Sequential(*vf_layers)
        self.latent_dim_pi, self.latent_dim_vf = last, last_vf

    def forward(self, f):
        return self.policy_net(f[:, :130]), self.value_net(f[:, 130:])

    def forward_actor(self, f):
        return self.policy_net(f[:, :130])

    def forward_critic(self, f):
        return self.value_net(f[:, 130:])


class MAPPO_Policy_M0(ActorCriticPolicy):
    def _build_mlp_extractor(self):
        self.mlp_extractor = MAPPO_Extractor_M0(self.features_dim, self.net_arch, self.activation_fn)

# ---- COPY MultiProcessRasterEnv from train_raster.py ----
# (This handles the 10-agent PettingZoo env across subprocesses)
# Lines 40–90 of train_raster.py — include the entire class

# ---- Main training logic ----
def main():
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 500000
    mode = sys.argv[2].lower() if len(sys.argv) > 2 else "on"
    stage = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    
    use_shared = (mode == "on")
    dropout_sched = [0.10, 0.15, 0.20]
    dropout = dropout_sched[stage]
    
    print(f"[*] Training slot-fusion {mode.upper()} stage {stage} | dropout={dropout} | steps={steps}")
    
    # Determine checkpoint to load
    if stage == 0:
        load_path = "models/apex_ultra_glide_v14_comm8_lidar_final.zip"
        print(f"    Loading M0: {load_path}")
    else:
        load_path = f"models/raster_slot_fusion_{mode.upper()}_stage{stage - 1}_final.zip"
        print(f"    Loading previous stage: {load_path}")
    
    if not os.path.exists(load_path):
        for cand in (os.path.join("models", os.path.basename(load_path)), os.path.abspath(load_path)):
            if os.path.exists(cand):
                load_path = cand
                break
    
    if not os.path.exists(load_path):
        print(f"[!] Checkpoint not found: {load_path}")
        return
    
    # Load model
    model = PPO.load(load_path, custom_objects={"policy_class": MAPPO_Policy_M0}, device="cpu")
    
    # Set up env using MultiProcessRasterEnv (from train_raster.py)
    # ADAPT: call the env constructor with slot_fusion=True, use_shared_map=use_shared, dropout, sustain
    env = MultiProcessRasterEnv(
        num_workers=7,
        target_density=0.20,
        communication_range=10.0,
        congestion_mode="lidar",
        lidar_range=8.0,
        lidar_dropout=dropout,
        dropout_sustain=5,
        use_shared_map=use_shared,
        slot_fusion=True,  # CRITICAL
        straight_line_goal=False
    )
    model.set_env(env)
    
    # Train
    print(f"    Training for {steps} steps...")
    model.learn(total_timesteps=steps)
    
    # Save
    out = f"models/raster_slot_fusion_{mode.upper()}_stage{stage}_final.zip"
    model.save(out)
    print(f"[OK] Saved: {out}")
    env.close()


if __name__ == "__main__":
    main()
```

> **NOTE:** You must copy `MultiProcessRasterEnv` from `train_raster.py` (lines ~40–90) into this script. It's the worker class that handles PettingZoo's 10-agent `ParallelEnv` across subprocesses.

---

## Checklist Before Running Gate 2

- [ ] Fix 0: Ego-range updated in `_fused_lidar` (cast at 8m, not 12m)
- [ ] Zero-shot eval still ~93/54 after Fix 0
- [ ] `train_slot_fusion.py` written with `MultiProcessRasterEnv` (copy from `train_raster.py`)
- [ ] `eval_slot_fusion_zero_shot.py` extended to n=500 + bootstrap CI output
- [ ] Ready for Haiku: each step is explicit, no FI gates (only ON/OFF evals), correct scripts everywhere

---

## Key Invariants (DO NOT BREAK)

- ✅ Actor reads `obs[:130]` only (no CTDE leak)
- ✅ Sender-gating and comm-range enforced in `_fused_lidar` (no privileged info)
- ✅ OFF arm is ego-only, ON arm adds neighbors (fair comparison)
- ✅ Both arms cast at 8m scale (M0's training scale, no regime change)
- ✅ Stage chaining: Stage 1 loads Stage 0, Stage 2 loads Stage 1 (curriculum, not restart from M0)
