# Phase B — Communication & Congestion Experiment Runbook

**Purpose:** finish the Phase B ablations cleanly and decide the final 8m model design.
**How to use:** run each step's command(s), paste the printed numbers into its "RESULTS" box.
Claude can read this file later to interpret the filled-in results.

**Global protocol (already baked into the scripts — don't change):**
- 200 maps/density, densities **0.20 and 0.30**, deterministic policy
- fixed counting (`finished` set), identical seeds across all conditions (paired comparison)
- run commands one at a time, sequentially (CPU-bound), from `D:\Swarm\BTP`
- use the `(swarm_rl)` python

---

## ALREADY DONE (reference baselines — do not rerun)

| Condition | 0.20 success / coll | 0.30 success / coll | Source file |
|-----------|---------------------|---------------------|-------------|
| ∞ (V14 unlimited) | 96.45% / 1.05% | 90.90% / 2.70% | v14_sweep CSV |
| 8 m (env congestion) | 95.45% / 2.55% | 91.25% / 2.40% | v14_8_0m_sweep CSV |
| 5 m | 95.60% / 1.35% | 90.70% / 3.10% | comm5_metrics.csv |
| 3 m | 95.20% / 2.10% | 91.40% / 2.90% | comm3_metrics.csv |
| 8m→0 BLACKOUT (zero-shot) | 90.65% / 7.20% | 83.40% / 12.55% | comm8_to_0m_blackout |

Key facts already established:
- comm RANGE (3/5/8/∞) → no effect (flat).
- comm BLACKOUT → big drop, collisions 3–5×, worse at high density.
- comm=8 baseline has **0% drone-drone collisions** (all collisions are obstacles).
- leakage test: PASS (actor ignores global state).
- feature importance: LiDAR 1.19 > goal-dir 0.67 > obs_neighbors 0.45 > … > congestion 0.025 (least).

---

# EXPERIMENTS TO RUN

## EXP-1 — Retrained comm=0 ("used vs needed")
**Question:** the blackout was zero-shot (no retrain). If we retrain at comm=0, can LiDAR fully substitute for communication?
**Why:** distinguishes "comm is *used*" (blackout) from "comm is *needed*" (this).

```powershell
python train_comm.py 0
python eval_comm.py 0
```

**Expected:** partial-to-full recovery toward ~91–95% (LiDAR sees close drones), but collisions may stay a touch above comm=8 (velocity anticipation lost).

**RESULTS (fill in):**collision
```
comm=0 retrained, congestion=ON(env)
0.20: success 93.95%  timeout 2.70%  drone-coll 1.30%  collision 3.35%
0.30: success 88.45%  timeout 5.40%  drone-coll 1.60%  collision 6.15%
```

---

## EXP-2 — Congestion ablation in comm-off regime ("does congestion matter at all")
**Question:** with comm gone, does congestion add anything over raw LiDAR?
**Why:** comm-off is the only regime where congestion can't be redundant with obs_neighbors.
**Note:** EXP-1 already trains/evals `comm=0` (congestion ON). Here add the OFF arm.

```powershell
python train_comm.py 0 nocong
python eval_comm.py 0 nocong
```

**Compare to EXP-1.** Gap (EXP-1 − EXP-2) = congestion's contribution.

**Expected:** ≈ no gap → congestion redundant with LiDAR → can be dropped entirely.

**RESULTS (fill in):**
```
comm=0 retrained, congestion=OFF (nocong)
0.20: success 93.95%  timeout 3.20%  drone-coll 1.00%  collision 2.85%
0.30: success 89.10%  timeout 5.85%  drone-coll 2.70%  collision 5.05%
```

**Decision after EXP-1 & EXP-2:**
- [ ] No gap (≤~1pp) → DROP congestion (use nocong). CTDE idealization removed by deletion. → skip EXP-3.
- [ ] Gap exists → congestion matters → run EXP-3 to get a CTDE-clean version.

---

## EXP-3 — (only if EXP-2 shows a gap) Sensor-based (LiDAR) congestion at comm=0
**Question:** does a CTDE-clean LiDAR congestion recover the benefit that ground-truth congestion gave?

```powershell
python train_comm.py 0 lidar
python eval_comm.py 0 lidar
```

**Compare to EXP-1 (env congestion) and EXP-2 (none).** If `lidar` ≈ `env` → LiDAR congestion is a clean replacement.

**RESULTS (fill in):**
```
comm=0 retrained, congestion=LIDAR
0.20: success ____%  timeout ____%  collision ____%
0.30: success ____%  timeout ____%  collision ____%
```

---

## EXP-4 — CTDE-clean 8m production model (LiDAR congestion)
**Question:** does the final 8m model hold up when congestion comes from LiDAR instead of ground-truth?
**Why:** this is the model you'd actually report — removes the last CTDE idealization.

```powershell
python train_comm.py 8 lidar
python eval_comm.py 8 lidar
```

**Compare to 8m (env): 95.45% / 91.25%.** Expected: holds (~unchanged) since congestion is barely used.

**RESULTS (fill in):**
```
comm=8, congestion=LIDAR (CTDE-clean production model)
0.20: success 95.55%  timeout 2.00%  drone-coll 0.90%  collision 2.45%%
0.30: success 91.10%  timeout 5.65%  drone-coll 0.90%  collision 3.25%
```

---

## EXP-5 — (quick, optional) Eval-time congestion ablation on current 8m model
**Question:** does the *existing* 8m model rely on congestion? (no retrain)

```powershell
python eval_nocongestion.py
```

**Expected:** ≈ no change vs 95.45% / 91.25% (congestion barely used).

**RESULTS (DONE 2026-06-14):**
```
8m model, congestion zeroed at eval (no retrain)
0.20: success 96.05%  timeout 2.55%  drone-coll 0.00%  collision 1.40%
0.30: success 91.20%  timeout 6.05%  drone-coll 0.00%  collision 2.75%
VERDICT: no effect (0.20 slightly better, 0.30 unchanged; drone-coll stays 0%)
-> current 8m model does NOT use congestion -> congestion can be dropped.
```
``` this was run again in 2025-06-15  and this is the result of it 

(swarm_rl) D:\Swarm\BTP>python eval_nocongestion.py
C:\Users\Srinivasa\miniconda3\envs\swarm_rl\lib\site-packages\pygame\pkgdata.py:25: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.
  from pkg_resources import resource_stream, resource_exists
[*] CONGESTION ABLATION (eval-time) on existing model: models/apex_ultra_glide_v14_8_0m_final.zip
[*] comm=8.0m, use_congestion=False (no retraining)
  [0.20] 100/200
  [0.20] 200/200
[*] 8m no-congestion (eval-time) d=0.20: success 96.05% | timeout 2.55% | drone-coll 0.40% | coll 1.40%
  [0.30] 100/200
  [0.30] 200/200
[*] 8m no-congestion (eval-time) d=0.30: success 91.20% | timeout 6.05% | drone-coll 1.00% | coll 2.75%

[OK] saved: results\comm_sweep\comm8_nocong_evaltime_metrics.csv
```
---

## EXP-6 — (recommended) Re-run blackout with drone-collision logged
**Question:** confirm the blackout collision spike is specifically DRONE-DRONE (not obstacle).
**Why:** clinches the "communication = neighbor-anticipation" claim.
**Action needed:** add this one line to the `row` dict in `eval_comm_blackout.py`, then run:
```python
"drone_collision_rate": stats["drone_collision"] / tot,
```
```powershell
python eval_comm_blackout.py
```

**RESULTS (fill in):**
```
8m->0 blackout, drone-collision breakdown
0.20: success 90.65%  timeout 2.15%  coll 7.20%
0.30: success 83.40%  timeout 4.05%  coll 12.55%
```

---

# SUMMARY TABLE (fill in as you go — Claude will read this)

| Condition                 | 0.20 success | 0.20 coll | 0.30 success | 0.30 coll |
|---------------------------|-------------:|----------:|-------------:|----------:|
| ∞ (V14)                   | 96.45        | 1.05      | 90.90        | 2.70      |
| 8 m (env cong)            | 95.45        | 2.55      | 91.25        | 2.40      |
| 5 m                       | 95.60        | 1.35      | 90.70        | 3.10      |
| 3 m                       | 95.20        | 2.10      | 91.40        | 2.90      |
| **comm=0 (EXP-1)**        | 93.95        | 3.35      | 88.45        | 6.15      |
| **comm=0 nocong (EXP-2)** | 93.95        | 2.85      | 89.10        | 5.05      |
| **comm=0 lidar (EXP-3)**  | ____         | ____      | ____         | ____      |
| **8 m lidar (EXP-4)**     | 95.55        | 2.45      | 91.10        | 3.25      |
| 8m→0 blackout (zero-shot) | 90.65        | 7.20      | 83.40        | 12.55     |

---

# RUN ORDER (recommended)

1. **EXP-1** `train_comm.py 0` + `eval_comm.py 0`   (also completes the sweep endpoint)
2. **EXP-2** `train_comm.py 0 nocong` + `eval_comm.py 0 nocong`
3. Check EXP-1 vs EXP-2 gap → decide on EXP-3.
4. **EXP-4** `train_comm.py 8 lidar` + `eval_comm.py 8 lidar`   (the production model)
5. **EXP-5** `eval_nocongestion.py` (quick)
6. **EXP-6** add drone-coll line + rerun blackout (quick)

Time: each `train_comm` ≈ 50 min, each `eval` ≈ 20–60 min. Sequential, unattended.

---

# NOTES / QUESTIONS FOR CLAUDE (write anything here)
- 
-
