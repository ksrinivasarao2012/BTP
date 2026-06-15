# Phase B — EVAL-TIME Ablation Runbook (NO retraining)

**Purpose:** measure which observation features the 8m model *depends on*, at the
PERFORMANCE level (success/collision), by zeroing one feature group at eval time.
No training — fast. Complements the retrain runbook (EXPERIMENT_RUNBOOK.md).

**Method:** load the existing `v14_8.0m` model, zero one feature group in the
observation before each action, run the density sweep. Tool: `eval_ablate_feature.py`.

**What it answers:** does *this trained model* RELY on feature X?
**What it does NOT answer:** is X NECESSARY for the task? (eval-time zeroing is
out-of-distribution and overstates importance — that needs the retrain runbook.)

**Protocol:** 200 maps/density, densities 0.20 & 0.30, deterministic, fixed counting,
same seeds. Run from `D:\Swarm\BTP`, `(swarm_rl)` python, sequentially.
Each run ≈ 20–60 min (eval only, no training).

---

## STEP 0 — Baseline sanity (no ablation)
Confirms the harness reproduces the 8m baseline.
```powershell
python eval_ablate_feature.py none
```
**Expected:** ≈ 95.45% / 91.25% (matches the 8m baseline).

**RESULTS:**
```
none (baseline)
0.20: success 95.45%  timeout 2.00%  drone-coll 0.40%  total-coll 2.55%
0.30: success 91.25%  timeout 6.35%  drone-coll 0.40%  total-coll 2.40%
```

---

## STEP 1 — LiDAR  (expect: collapse — it's the dominant feature, 1.19 saliency)
```powershell
python eval_ablate_feature.py lidar
```
**RESULTS:**
```
lidar zeroed [6:54]
0.20: success 12.15%  timeout 0.00%  drone-coll 30.30%  total-coll 87.85%
0.30: success 8.25%   timeout 0.00%  drone-coll 29.00%  total-coll 91.75%


## STEP 2 — Goal direction (Dijkstra) (expect: large drop — can't navigate, 0.67)
```powershell
python eval_ablate_feature.py goaldir
```
**RESULTS:**
```
goaldir zeroed [2:4]
0.20: success 60.85%  timeout 38.80%  drone-coll 0.10%  total-coll 0.35%
0.30: success 62.90%  timeout 36.65%  drone-coll 0.30%  total-coll 0.45%
``` 

## STEP 3 — Neighbors (obs_neighbors) (expect: collisions rise — comm channel, 0.45)
```powershell
python eval_ablate_feature.py neighbors
```
**RESULTS:**
```
neighbors zeroed [54:99]
0.20: success 91.70%  timeout 2.55%  drone-coll 1.70%  total-coll 5.75%
0.30: success 84.40%  timeout 5.80%  drone-coll 2.40%  total-coll 9.80%
```

## STEP 4 — Sync (rel-vel + stagnation) (expect: small-moderate, 0.17)
```powershell
python eval_ablate_feature.py sync
```
**RESULTS:**
```
sync zeroed [100:120]
0.20: success 94.30%  timeout 2.60%  drone-coll 1.10%  total-coll 3.10%
0.30: success 89.45%  timeout 5.35%  drone-coll 2.00%  total-coll 5.20%
```

## STEP 5 — Congestion (expect: ~no change — 0.025; already confirmed by eval_nocongestion)
```powershell
python eval_ablate_feature.py congestion
```
**RESULTS:**
```
congestion zeroed [99]
0.20: success 96.05%  timeout 2.55%  drone-coll 0.40%  total-coll 1.40%
0.30: success 91.20%  timeout 6.05%  drone-coll 1.00%  total-coll 2.75%
```

## STEP 6 — Ego velocity (expect: minor, 0.22)
```powershell
python eval_ablate_feature.py egovel
```
**RESULTS:**
```
egovel zeroed [0:2]
0.20: success 94.35%  timeout 1.60%  drone-coll 1.40%  total-coll 4.05%
0.30: success 89.50%  timeout 3.50%  drone-coll 2.10%  total-coll 7.00%
```

## STEP 7 — Trajectory memory (expect: ~no change, 0.03)
```powershell
python eval_ablate_feature.py trajectory
```
**RESULTS:**
```
trajectory zeroed [120:130]
0.20: success 95.50%  timeout 2.35%  drone-coll 0.50%  total-coll 2.15%
0.30: success 89.95%  timeout 7.05%  drone-coll 0.70%  total-coll 3.00%
```

---
success 12.15%  timeout 0.00%  drone-coll 30.30%  total-coll 87.85%
0.30: success 8.25%   timeout 0.00%  drone-coll 29.00%  total-coll 91.75%
# SUMMARY TABLE (fill in — Claude will read this)

Baseline 8m = 95.45% / 91.25% success.

| Ablated feature  | 0.20 success | 0.20 coll | 0.30 success | 0.30 coll | drop @0.30 |
|----------------- |-------------:|----------:|-------------:|----------:|-----------:|
| none (baseline)  |    95.45%    |  02.55%   |    91.25%    |  02.40%   | 0          |
| LiDAR            |    12.15%    |  87.85%   |    08.25%    |  91.75%   | __      __ |
| goal direction   |    60.85%    |  00.35%   |    62.90%    |  00.45%   | __      __ |
| neighbors (comm) |    91.70%    |  05.75%   |    84.40%    |  09.80%   | __      __ |
| sync (comm)      |    94.30%    |  03.10%   |    89.45%    |  05.20%   | __      __ |
| congestion       |    96.05%    |  01.40%   |    91.20%    |  02.75%   | __      __ |
| ego velocity     |    94.35%    |  04.05%   |    89.50     |  07.00%   | __      __ |
| trajectory       |    95.50%    |  02.15%   |    89.95%    |  03.00%   | __      __ |

---

# EXPECTED RANKING (from action-level saliency, to cross-check)

LiDAR (1.19) ≫ goal-dir (0.67) > neighbors (0.45) > ego-vel (0.22) > sync (0.17) ≫ congestion (0.025) ≈ trajectory (0.03)

→ Performance drops should follow roughly this order. If they do, the two methods
agree and the importance story is solid. Biggest expected drops: LiDAR, goal-dir.
Near-zero drops expected: congestion, trajectory (confirming they can be dropped).

---

# RUN ORDER

0. `none` (sanity — must match 95.45/91.25)
1. `lidar`  2. `goaldir`  3. `neighbors`  4. `sync`  5. `congestion`  6. `egovel`  7. `trajectory`

Results auto-save to `results/eval_ablation/ablate_<group>_metrics.csv`.

---

# NOTES / QUESTIONS FOR CLAUDE
-
-
