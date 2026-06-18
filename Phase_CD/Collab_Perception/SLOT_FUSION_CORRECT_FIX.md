# Slot-Fusion — Correct Ego-Range Fix + Re-run Plan

**Owner:** Srinivasa · **Date:** 2026-06-18
**Purpose:** record the correct fix for the 8 m/12 m ego-range issue, the right script paths, and what
must be re-run. Supersedes "Fix 0 = cast at 8 m" in `GATE_1_RESULT_AND_GATE_2_PLAN.md` (that version is
wrong — see §2).

> Rule: show every command to Srinivasa before running. ▶ = proposed, not auto-run.

---

## 1. Did the +38.85 pp test run at 8 m or 12 m? → effectively 12 m for sighted drones

Grounded in `swarm_env_raster.py` as it stands now:
- The env was configured `lidar_range=8.0` (`eval_slot_fusion_zero_shot.py:75`).
- BUT in `_fused_lidar` the **ego's own-obstacle branch appends ALL obstacles, unfiltered**
  (`swarm_env_raster.py:106–109`), and `_cast48` ranges to `collab_range = 12 m` (`:142`).
- So a **sighted drone detected obstacles out to 12 m, not 8 m.** (The neighbor-shared branch *is*
  correctly filtered to 8 m at `:124`.)

**Consequence:** the regime label "8 m LiDAR" was inaccurate for sighted drones. It affected ON and OFF
**equally** (both use ego sensing), so the *conclusion* "communication helps" still holds and the gap is
real. But the **absolute numbers (93.55 / 54.70) must be regenerated** after the fix, because the paper
claims an 8 m sensor. → **Yes, re-run after applying §3.**

---

## 2. Why "cast at 8 m" (the other doc's Fix 0) is WRONG

M0 was trained with its LiDAR normalized on the **12 m** scale. `collab_range = 12.0`
(`swarm_env_phasecd.py:48`) exists specifically so the fused obs stays **in-distribution** for M0
(`swarm_env_phasecd.py:46` comment). If you change `_cast48`/normalization to 8 m, every obstacle distance
lands on the wrong scale → M0 reads obstacles at the wrong range → zero-shot performance collapses. That
is a **normalization break, not a fix.**

**Correct principle:** keep the **cast + normalization at `collab_range` (12 m)** so M0 stays
in-distribution, but **restrict which obstacles the ego is allowed to sense to `lidar_range` (8 m)** —
exactly what the neighbor branch already does. Range is controlled by *which obstacles enter the list*,
not by the cast distance.

---

## 3. The correct fix (Fix 0) — `swarm_env_raster.py` only

### 3a. `_fused_lidar` ego branch (the ON path), lines ~105–109
REPLACE:
```python
        # 1. Ego's own obstacles (only if sighted; if blind, skip ego sensing)
        if not self.lidar_blind[idx] and self.obstacles:
            arr = np.array(self.obstacles, dtype=np.float32)
            c_list.append(arr[:, :2])
            r_list.append(arr[:, 2])
```
WITH:
```python
        # 1. Ego's own obstacles — ONLY those within the ego's 8 m sensor range (lidar_range).
        #    Cast/normalization stay at collab_range (12 m) so M0 stays in-distribution.
        if not self.lidar_blind[idx] and self.obstacles:
            arr = np.array(self.obstacles, dtype=np.float32)
            ego_keep = np.linalg.norm(arr[:, :2] - pos, axis=1) <= self.lidar_range   # 8 m filter
            if ego_keep.any():
                c_list.append(arr[ego_keep, :2])
                r_list.append(arr[ego_keep, 2])
```

### 3b. The OFF path in `_observe` has the SAME unfiltered ego bug, lines ~215–218
REPLACE:
```python
                if not self.lidar_blind[idx] and self.obstacles:
                    arr = np.array(self.obstacles, dtype=np.float32)
                    c_list.append(arr[:, :2])
                    r_list.append(arr[:, 2])
```
WITH:
```python
                if not self.lidar_blind[idx] and self.obstacles:
                    arr = np.array(self.obstacles, dtype=np.float32)
                    ego_keep = np.linalg.norm(arr[:, :2] - pos, axis=1) <= self.lidar_range   # 8 m filter
                    if ego_keep.any():
                        c_list.append(arr[ego_keep, :2])
                        r_list.append(arr[ego_keep, 2])
```

> Do NOT touch `_cast48`, `collab_range`, or the `/ self.collab_range` normalization. Leak-safety is
> unchanged: still ego-own + sender-gated neighbors + drones; no global/critic info; actor still 130-d.

---

## 4. Re-run after the fix (regenerate the headline number)

▶ (show first)
```powershell
$py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
cd "D:\Swarm\BTP"
& $py Phase_CD\Collab_Perception\eval_slot_fusion_zero_shot.py models\apex_ultra_glide_v14_comm8_lidar_final.zip 200
```
**What to expect:** sighted drones now see less (true 8 m), so both ON and OFF may drop from 93.55 / 54.70.
The ON−OFF gap should stay large and **may even widen** — with a real 8 m ego, the 8–10 m comm annulus from
neighbors becomes more valuable. Report the new ON / OFF / ON−OFF.

⏸ STOP and bring Srinivasa the new numbers before any training.

---

## 5. Correct script paths (use these, not the 698-d ones)

| Purpose | CORRECT script | Do NOT use |
|---|---|---|
| Slot-fusion ON/OFF eval | `eval_slot_fusion_zero_shot.py` (650-d, 130-d actor, `slot_fusion=True`) | `eval_raster.py` (698-d / 178-d) |
| "Did it use comm?" per stage | ON vs OFF eval at that dropout (toggle `use_shared_map`) | `feature_importance_raster.py` (ablates `[130:178]`, which slot-fusion doesn't have) |
| Training (when we get there) | new `train_slot_fusion.py` using `MultiProcessRasterEnv` from `train_raster.py`, `slot_fusion=True`, stage-chained | plain `SubprocVecEnv([env])` (can't wrap the 10-agent PettingZoo env) |

Model in/out names: load `models/apex_ultra_glide_v14_comm8_lidar_final.zip` (M0); save fine-tunes as
`models/raster_slot_fusion_{ON,OFF}_stage{N}_final.zip`.

---

## 6. Order of operations

1. **Apply Fix 0** (§3a + §3b) — ego filtered to 8 m, cast/normalize stay 12 m.
2. **Re-run §4 eval** — regenerate ON / OFF / ON−OFF at the true 8 m regime. ⏸ review.
3. Only then proceed to Gate 2 training (separate plan), after the eval/train scripts are corrected per §5.

## 7. Invariants (must stay true)
- Actor reads `obs[:130]` only (no CTDE leak).
- Sender-gating + comm-range preserved in the neighbor branch.
- Cast + normalization stay at `collab_range` (12 m) — M0 in-distribution.
- Ego now sees obstacles ≤ `lidar_range` (8 m) only; neighbors already did.
- Same fix applied to BOTH ON (`_fused_lidar`) and OFF (`_observe` OFF branch) so the comparison stays fair.
