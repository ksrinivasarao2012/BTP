# Design A — Will it work? (Go / No-Go check plan)

**Purpose:** decide whether the attributable per-neighbor hazard channel (Design A, obs 130→157,
architecture change + training) is worth building — **before** spending training compute.

## The tension (why this plan exists)
- **Design B** (oracle, `probe_collab_lidar.py`, DONE ✅): rich obstacle sharing fused into LiDAR.
  Recovers short-LiDAR success to **92 / 94** *zero-shot on M0*. But it is **not attributable** — the
  drone can't tell which neighbor reported a hazard, so it **cannot carry the T-Cell trust mechanism.**
- **Design A** (built, not run): per-neighbor hazard slot → **attributable** → trust can discount the
  lying neighbor. The cost: (1) architecture change (130→157), and (2) **it cannot be tested zero-shot**
  — M0 has zero weights on the new channel, so the only "real" test is a training run.

So before committing to training, we run two cheap (no-train) checks that together tell us if Design A
is likely to work. **Run in order; stop at the first that fails.**

---

## CHECK 0 — Information sufficiency (NO training) ⟵ the key cheap gate
**Question:** Design A's channel is *lossy* — it shares only the **nearest obstacle per comm-neighbor**
(27 numbers), not the rich obstacle set Design B fused. Does that compact info carry **enough** to
recover success, or is it too thin?

**How (reuse the Design-B oracle, restrict what's shared):** fuse into the ego LiDAR **only** the single
nearest obstacle each comm-neighbor senses — i.e. *exactly the obstacles Design A's channel would
encode* — then run M0 zero-shot. This upper-bounds Design A without training. ✅ **Built:**
`probe_collab_restricted.py` (+ env flag `collab_nearest_only`).
```powershell
& $py Phase_CD\Collab_Perception\probe_collab_restricted.py models\apex_ultra_glide_v14_comm8_lidar_final.zip 30
```
Prints 4 rows/density: `short_l5` (77/85) · **`restricted_l5`** (Design-A ceiling) · `full_l5` (Design-B, ~92/94) · `full_l12` (sight ceiling). The number that matters is **`restricted_l5` vs `full_l5`**.

| oracle (lidar 5) | d0.20 | d0.30 | verdict |
|---|---|---|---|
| short_l5 | 77.0 | 84.7 | baseline |
| **restricted_l5** (Design A) | **92.3** | **93.0** | **PASS** |
| full_l5 (Design B) | 91.7 | 94.3 | rich reference |
- ✅ **PASSED:** `restricted_l5` (92.3 / 93.0) ≈ `full_l5` (91.7 / 94.3) — the compact **1-obstacle-per-neighbor** channel captures essentially all the value (the nearest obstacle is the collision-relevant one). Well above the ≥88/91 bar. **Design A is worth training.**

> Reference: short-LiDAR (no share) = 77 / 85 · full Design-B share = 92 / 94 · full sight = 92 / 95.

---

## CHECK 1 — Surgery plumbing (NO training)
Confirms the architecture change is wired correctly (the expanded model = M0 when hazards are 0).
```powershell
& $py Phase_CD\Collab_Perception\surgical_expand.py models\apex_ultra_glide_v14_comm8_lidar_final.zip models\collab_expanded_M0.zip
& $py Phase_CD\Collab_Perception\eval_collab.py models\collab_expanded_M0.zip 12 10 on 30
```
- ✅ **PASSED:** expanded M0 @ lidar=12 = **92.0 / 95.0** = M0's baseline exactly → surgery is identity-preserving, architecture wired correctly.

---

## CHECK 2 — The learned gate (TRAINING; 0 & 1 PASSED → cleared to run)  ✅ code built
Train comm-ON vs comm-OFF (`train_collab.py`), transfer from `collab_expanded_M0.zip`. **Start short
(~1–2 M steps)** to see early separation before committing the full ~5 M.
```powershell
& $py Phase_CD\Collab_Perception\train_collab.py 5 10 on    # share_hazards=True
& $py Phase_CD\Collab_Perception\train_collab.py 5 10 off   # ablation: hazards zeroed
# then eval both, no adversary:
& $py Phase_CD\Collab_Perception\eval_collab.py models\collab_l5_c10_hazardON_final.zip  5 10 on  200
& $py Phase_CD\Collab_Perception\eval_collab.py models\collab_l5_c10_hazardOFF_final.zip 5 10 off 200
```
- **Promising:** comm-ON pulls clearly ahead of comm-OFF early → continue to full → `comm_value ≥ ~5 pp` = gate passed.
- **Flat after a short train:** the learned model isn't using the channel → revisit encoding before more compute.

---

## Decision summary
| outcome | meaning | action |
|---|---|---|
| Check 0 strong + Check 1 pass | compact channel is sufficient & wired | train (Check 2) |
| Check 0 weak | encoding too lossy | enrich K, re-run Check 0 (or use Design B) |
| Check 1 fail | plumbing bug | fix env/surgery |
| Check 2 flat | channel not learnable as-is | enrich / reconsider |

## Honest notes
- Design A's real downside vs B: **no full zero-shot oracle** — Check 0 is a *ceiling proxy*, and the
  definitive test (Check 2) costs training. That is the price of attribution (which trust needs).
- If you want to avoid the architecture change entirely, **Design B can still carry a coarser trust
  signal** (distrust by direction/temporal consistency of fused hazards, not by named neighbor) — a viable fallback.
- Nothing here is run automatically — you run each check and bring the numbers to the ⛔ gate.
