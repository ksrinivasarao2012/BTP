# Collaborative-Perception Trust Defense — Runbook (Design A)

**Folder:** `Phase_CD/Collab_Perception/` · **Shared env:** `Phase_CD/swarm_env_phasecd.py` (oracle) → a new
`swarm_env_collab.py` for the trained build (Stage A1). **Models** live in repo-root `models/`; **results** in
`Phase_CD/Collab_Perception/results/`.

**You run the commands; paste numbers into the RESULTS tables; stop at each ⛔ checkpoint and bring results to Claude.**

```powershell
$py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
# clear stale bytecode before a run:
Get-ChildItem -Recurse -Directory __pycache__ | Remove-Item -Recurse -Force
```

---

## Why this exists (the pivot, in one paragraph)
Short-LiDAR-for-comm failed for a *verified* reason: communication carries only **drone positions** (redundant — LiDAR already sees drones), while shortening LiDAR creates an **obstacle**-sensing deficit that neighbor-position comm cannot fix. The Stage-0 oracle below proved the fix: if comm instead shares **obstacle perception**, short-LiDAR success recovers to full-sight levels. So the load-bearing channel is **shared hazards**, and a traitor broadcasting **false hazards** is a deception the victim's short LiDAR *cannot* override — exactly what a **T-Cell trust mechanism** defends. That earns the "Trust-Aware" title.

---

## STAGE 0 — Collaborative-perception oracle ✅ DONE (passed)
Perfect-sharing upper bound, zero-shot on M0 (no retrain). `collab_comm` fuses teammates' sensed obstacles into the ego LiDAR.
```powershell
& $py Phase_CD\Collab_Perception\probe_collab_lidar.py models\apex_ultra_glide_v14_comm8_lidar_final.zip 30
```
**Result (30 maps, no adversary):**

| config | d0.20 success | d0.30 success | obstacle-coll (d0.20/d0.30) |
|---|---|---|---|
| short LiDAR 5 (no share) | 77.0% | 84.7% | 13.7% / 10.7% |
| **collab LiDAR 5 (share)** | **91.7%** | **94.3%** | **1.3% / 2.7%** |
| full LiDAR 12 (ceiling) | 92.0% | 95.0% | 2.0% / 2.7% |

**Verdict:** shared obstacle perception recovers ~+15/+10 pp to the full-sight ceiling and collapses obstacle collisions → comm carries large, non-redundant value. **GO.** (Caveat: this is a perfect-sharing upper bound — the *trained* model will be lower, but the headroom is large.)

> Output: `Phase_CD\Collab_Perception\results\collab_lidar_oracle.csv`. Reproduce anytime — seeds are deterministic.

---

## STAGE A1 — Attributable shared-hazard channel + transfer surgery  ✅ CODE BUILT
- **`swarm_env_collab.py`** — env with the per-neighbor shared-hazard block. For each of the 9 comm-neighbor slots: the nearest obstacle that neighbor senses (within its `lidar_range`), in the ego frame → `(sin, cos, dist/15)` = **3 × 9 = 27 dims**; local obs `130 → 157`, total obs **677**. `env.share_hazards` toggles the channel (OFF → block = 0). Attributable per neighbor → falsifiable → trust can discount a liar.
- **`surgical_expand.py`** — expands M0's `mlp_extractor.policy_net.0.weight` `[h,130] → [h,157]`, **zero-init the 27 new cols**; every other tensor copied verbatim. Self-verifies (first-130 cols == M0, new 27 cols == 0) before saving.
- **`eval_collab.py`** — no-adversary eval for 157-d models (used here and in A2).

**Run it:**
```powershell
# 1) surgery -> models\collab_expanded_M0.zip  (prints "expanded 1", "new 27 cols all zero: True")
& $py Phase_CD\Collab_Perception\surgical_expand.py models\apex_ultra_glide_v14_comm8_lidar_final.zip models\collab_expanded_M0.zip
# 2) identity sanity: expanded model at FULL sight must reproduce M0
& $py Phase_CD\Collab_Perception\eval_collab.py models\collab_expanded_M0.zip 12 10 on 30
```

**RESULTS — A1 sanity:**

| check | d0.20 | d0.30 | result |
|---|---|---|---|
| surgery self-check | — | — | ✅ expanded 1, new 27 cols all zero |
| expanded M0 @ lidar=12 → reproduce M0 | **92.0** | **95.0** | ✅ = M0 baseline (identity-preserving) |

> ✅ **CHECKPOINT A1 PASSED** — surgery is identity-preserving and the architecture is wired correctly. Also **Check 0 (`DESIGN_A_FEASIBILITY.md`) passed**: restricted-share oracle = 92.3 / 93.0 ≈ full-share → the compact 27-d channel is rich enough. Cleared to train (A2).

---

## STAGE A2 — Train comm-ON vs comm-OFF = THE GATE  ✅ code built (`train_collab.py`)
The ablation pair decides whether the *learned* model realizes the oracle's headroom. Each ~5 M steps,
transfers from `collab_expanded_M0.zip`. **Tip:** watch the first ~1–2 M steps for early separation
before letting both finish.
```powershell
# comm-ON  (hazard channel active),  lidar=5 comm=10, transfer from expanded M0
& $py Phase_CD\Collab_Perception\train_collab.py 5 10 on
# comm-OFF (hazard channel zeroed -> clean ablation)
& $py Phase_CD\Collab_Perception\train_collab.py 5 10 off
# eval both, NO adversary:
& $py Phase_CD\Collab_Perception\eval_collab.py models\collab_l5_c10_hazardON_final.zip  5 10 on  200
& $py Phase_CD\Collab_Perception\eval_collab.py models\collab_l5_c10_hazardOFF_final.zip 5 10 off 200
```
`comm_value = ON − OFF`. **Expectation:** Check 0 showed ~15 pp of headroom (77→92), so a trained comm-ON
should land clearly above comm-OFF; comm-OFF should plateau near the short-LiDAR level. Realistically
expect `comm_value` in the **~5–12 pp** range (training won't fully hit the oracle's perfect-sharing ceiling).

**RESULTS:**

| model | d0.20 | d0.30 |
|---|---|---|
| comm-ON (`collab_l5_c10_hazardON`) |  |  |
| comm-OFF (`collab_l5_c10_hazardOFF`) |  |  |
| **comm_value = ON − OFF (pp)** |  |  |

> ⛔ **CHECKPOINT A2 (critical):** `comm_value ≥ ~5 pp` → the channel is load-bearing → proceed to attack/trust. `~0` → the learned model can't use shared hazards → reconsider encoding before going further.

---

## STAGE A3 — False-hazard Byzantine attack (no defense)  ⏳ TO BUILD (`probe_false_hazard.py`)
A traitor broadcasts **phantom hazards** (and/or suppresses real ones) on its hazard slot. Measure honest_success drop on the comm-ON model, **no trust**, at f = 1, 2, 3.

**RESULTS:**

| f | honest_success d0.20 | d0.30 | drop vs no-attack |
|---|---|---|---|
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |

> ⛔ **CHECKPOINT A3:** the attack must clearly degrade success (the channel is poisonable). If it doesn't, the channel isn't load-bearing enough — revisit A2.

---

## STAGE A4 — T-Cell trust defense  ⏳ TO BUILD (oracle → trained M2)
1. **Perfect-trust oracle** (`probe_trust_oracle.py`): know traitor IDs, ignore their hazard slots → upper bound on recovery. Oracle-before-build, as always.
2. **Trust mechanism:** per-neighbor trust from agreement between a neighbor's broadcast hazard and what the ego drone can verify (its own LiDAR when the hazard falls within its short range; temporal consistency otherwise). Discount low-trust slots. (Design spec: `Phase_CD/PHASE_C_TRUST_DESIGN.md`.)
3. **Train M2** with trust, curriculum incl. false-hazard traitors.

**RESULTS — headline (no-trust vs trust):**

| f | no-trust (d0.20/d0.30) | trust M2 (d0.20/d0.30) | recovery |
|---|---|---|---|
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |

> ⛔ **CHECKPOINT A4:** trust recovers success toward the no-attack baseline → **the Trust-Aware paper.** Also report trust-ID ROC and the no-traitor cost (trust must not hurt the clean case).

---

## Master ledger (keep updated)

| stage | config | metric | d0.20 | d0.30 | date |
|---|---|---|---|---|---|
| 0 | collab oracle | success vs short/full | 91.7 / (77→92) | 94.3 / (85→95) | 2026-06-16 |
| 0b | restricted oracle (Design A info) | success | 92.3 ✅ | 93.0 ✅ | 2026-06-17 |
| A1 | expanded M0, hazard=0 | reproduce M0 | 92.0 ✅ | 95.0 ✅ | 2026-06-17 |
| A2 | comm-ON vs OFF | comm_value (pp) | _run train_collab_ |  |  |
| A3 | false-hazard f=2 | drop vs no-attack |  |  |  |
| A4 | trust M2 f=2 | recovery |  |  |  |

## When to bring results to Claude
1. **After A1 sanity** — confirm surgery is identity-preserving (quick).
2. **After A2 gate** — required; decides whether shared hazards are learnable/load-bearing.
3. **After A3 attack** — confirm the channel is poisonable.
4. **After A4** — the headline trust result.

## Reference (Stage 0 + prior)
collab oracle: short 77/85 → **collab 91.7/94.3** → full 92/95 · clean baseline (lidar12, no adversary) 92/95.
Verified facts: comm = drone-pos only; LiDAR sees drones+obstacles; short-LiDAR deficit = obstacle collisions.
