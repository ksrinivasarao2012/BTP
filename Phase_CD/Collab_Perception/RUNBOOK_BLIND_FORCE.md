# Runbook — Blind-Force Curriculum (Raster Architecture)

**Goal:** Train the raster model so the policy genuinely learns to use the shared-obstacle map
(`obs[130:178]`), then demonstrate that communication is load-bearing under LiDAR dropout.

**Gate:** `comm_value = comm-ON success − comm-OFF success ≥ 5 pp` at dropout=0.20, lidar=8m.

---

## Why the Previous Run Failed

Feature importance on `raster_l5_d0.4_ON_final` (the broken model):

| Segment | DROP |
|---------|------|
| goal_dir `[2:4]` | 18.80 pp |
| lidar `[6:54]` | 20.60 pp |
| **SHARED_MAP `[130:178]`** | **0.60 pp** ← dead |

PPO found a working policy using `goal_dir + own-LiDAR` and never touched the shared map.
Zero-initialized weights on `obs[130:178]` stayed near zero because the policy never *needed*
those weights — it could already navigate without them.

Two compounding failures in the old setup:
1. `lidar=5m` — massive distribution shift from M0 (trained at 12m), policy collapsed immediately.
2. `dropout=0.4, sustain=20` — at step-level blindness, both ego AND neighbors frequently blind
   → shared map empty most of the time → no gradient signal possible.

---

## The Fix: Blind-Force Stage 0

`dropout=0.60, sustain=1200` (= episode length).

At each episode reset, every drone independently rolls 60% probability to go blind for
the entire episode (sustain ≥ max_steps = 1200). Result each episode:
- **~6 drones permanently blind** — `obs[6:54]` zeroed, shared map is their ONLY obstacle info.
- **~4 drones permanently sighted** — normal LiDAR, populate the shared map for the blind drones.

This creates unavoidable gradient pressure: blind drones that crash get penalized; those that
use `obs[130:178]` to navigate get rewarded. Over 2M steps the shared-map weights become
non-trivially positive. Previous training never created this — drones were only briefly blind.

---

## 4-Stage Curriculum

**Blind fraction formula:** `bf = (p × s) / (p × s + 1)` — where p = dropout, s = sustain.

| Stage | Steps | LiDAR | Dropout | Sustain | Blind % | Density | Purpose |
|-------|-------|-------|---------|---------|---------|---------|---------|
| **S0 — Blind Force** | 2M | 12m | 0.60 | 1200 | **99.9%** episodic | 0.15 | Force shared-map weights nonzero |
| **S1 — Transition** | 1M | 10m | 0.10 | 5 | **33%** | 0.22 | LiDAR back 67% of steps; short blind windows reinforce map |
| **S2 — LiDAR 8m** | 1.5M | 8m | 0.20 | 25 | **83%** | 0.27 | Comm-only annulus (8–10m); model must rely on shared map |
| **S3 — Gate** | 2M | 8m | 0.20 | 25 | **83%** | 0.30 | Final gate condition density |

> ⚠ **Bug fixed (2026-06-18):** Original S1 was `dropout=0.30, sustain=50` → blind fraction `(0.30×50)/(0.30×50+1)` = **93.8%** — barely different from S0, no LiDAR recovery possible. Fixed to `dropout=0.10, sustain=5` → **33%**.

**Total: 6.5M steps per model (ON and OFF).**

Why LiDAR=8m matters: M0 was trained at 12m (comm=8m), so LiDAR > comm → shared map was
100% redundant. At 8m LiDAR with comm=10m, a **comm-only annulus of 8–10m** exists — obstacles
there are invisible to the ego but visible to neighbors. Shared map is non-redundant even
without dropout.

---

## Commands — Run One Stage at a Time

```powershell
$py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
cd "D:\Swarm\BTP"
```

### Stage 0 — Blind Force (run first, then STOP and check)

```powershell
& $py Phase_CD\Collab_Perception\train_raster.py 10 on 0
```

**Saves:** `models/raster_blind_ON_stage0_final.zip`

### ⛔ CHECKPOINT — Feature Importance After Stage 0

```powershell
& $py Phase_CD\Collab_Perception\feature_importance_raster.py `
    models\raster_blind_ON_stage0_final.zip 12 10 0.60 on 30
```

| SHARED_MAP drop | Decision |
|-----------------|----------|
| ≥ 5 pp | ✅ Proceed to Stage 1 |
| 2–5 pp | ⚠ Borderline — extend Stage 0 by 1M steps |
| < 2 pp | ❌ Something wrong — check sustain=1200 is applied in env |

### Stage 1 (only if Stage 0 passes)

```powershell
& $py Phase_CD\Collab_Perception\train_raster.py 10 on 1
```

### Stage 2

```powershell
& $py Phase_CD\Collab_Perception\train_raster.py 10 on 2
```

**Quick preview at Stage 2 end (30 maps):**
```powershell
& $py Phase_CD\Collab_Perception\eval_raster.py `
    models\raster_blind_ON_stage2_final.zip 8 10 0.20 on 30
```

### Stage 3 (Gate)

```powershell
& $py Phase_CD\Collab_Perception\train_raster.py 10 on 3
```

### comm-OFF (run alongside or after all ON stages)

```powershell
& $py Phase_CD\Collab_Perception\train_raster.py 10 off 0
# check FI, then:
& $py Phase_CD\Collab_Perception\train_raster.py 10 off 1
& $py Phase_CD\Collab_Perception\train_raster.py 10 off 2
& $py Phase_CD\Collab_Perception\train_raster.py 10 off 3
```

---

## Gate Eval (200 maps)

```powershell
& $py Phase_CD\Collab_Perception\eval_raster.py `
    models\raster_blind_ON_final.zip 8 10 0.20 on 200
& $py Phase_CD\Collab_Perception\eval_raster.py `
    models\raster_blind_OFF_final.zip 8 10 0.20 off 200
```

**Gate:** `comm_value = ON − OFF ≥ 5 pp` → shared channel load-bearing → proceed to B4 (trust module).

---

## Expected Results

| Model | d=0.20 | d=0.30 | Basis |
|-------|--------|--------|-------|
| comm-ON (dropout=0.20) | 78–87% | 74–83% | Probe proved shared map sufficient (85/91%) at dropout=0 |
| comm-OFF (dropout=0.20) | 58–72% | 55–68% | 75% of steps blind with no obstacle info → crashes dominate |
| **comm_value** | **~10–20 pp** | **~10–20 pp** | Structural gap — not hopeful |

Adversarial drop (f=2 rammers) confirmed at 8m LiDAR: **−17 pp** (identical to 12m).
Clean baseline at 8m (after retraining): expected ~90–93%.

---

## Key Files

| File | Role |
|------|------|
| `swarm_env_raster.py` | Env: 698-d obs, 48-d shared map, dropout + sender-gating |
| `surgical_expand_raster.py` | One-time surgery: M0 actor 130→178, zero-init |
| `train_raster.py` | This curriculum (4-stage, per-stage args) |
| `eval_raster.py` | Gate eval: comm_value at final dropout |
| `feature_importance_raster.py` | Verify shared map weights are non-trivial |
| `probe_raster.py` | B1 zero-shot validation (already passed: 85/91%) |
| `DESIGN_RASTER_TRUST.md` | Architecture spec + B4 trust module design |

---

## Status

| Step | Status |
|------|--------|
| B1 — Env validation (obs=698, shared-map code correct) | ✅ Done (85/91%) |
| B2 — Surgery identity check (expanded M0 = 92/95%) | ✅ Done |
| Lidar-8m adversarial impact probe | ✅ Done (−17 pp, same as 12m) |
| B3 — Blind-force curriculum (Stage 0) | ⏳ **Next** |
| B3 — Stages 1–3 + gate eval | Blocked on Stage 0 FI check |
| B4 — Trust module + traitor attack | Deferred until gate passes |
