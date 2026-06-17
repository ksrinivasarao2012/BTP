# Phase C/D Runbook — Short-LiDAR comm-reliance experiment (self-run, gate-first)

**You run the commands; paste numbers into the RESULTS tables; stop at each ⛔ checkpoint and bring this file (or the CSVs) to Claude before continuing.**

## Setup (read once)
- Python by full path (conda activate is a no-op here):
  ```powershell
  $py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
  ```
- **Run from the repo root** `D:\Swarm\BTP` (scripts live in `Phase_CD\` but self-resolve paths to root, so `models\` and `results\` work either way).
- **Clear stale bytecode before a run** (we hit a stale no-op bug once):
  ```powershell
  Get-ChildItem -Recurse -Directory __pycache__ | Remove-Item -Recurse -Force
  ```
- All results land in `Phase_CD\results\`.

## Why this experiment (one paragraph)
M0 is a LiDAR-driven policy that ignores communication, because the env is physically inverted (**LiDAR 12 m > comm 8 m**) — so comm is redundant and deception/trust have nothing to bite on. We **reduce LiDAR below comm** (the physically-correct ordering for small UAVs: radio out-ranges onboard depth sensing) and **retrain**, forcing reliance on LiDAR + goal **+ communication**. The gate: does communication then carry measurable, non-redundant value? If yes → it's poisonable → a T-Cell trust defense is earned. If no → a stronger fundamental-limit result.

---

## STAGE 0 — Geometry pre-gate (no training, ~minutes)
Confirms drones actually have neighbors in the "comm-only" annulus (`lidar < dist ≤ comm`) — the non-redundant info a trust mechanism could defend.

```powershell
& $py Phase_CD\probe_comm_geometry.py models\apex_ultra_glide_v14_comm8_lidar_final.zip 30
```
Output: `Phase_CD\results\comm_geometry.csv`. The number that matters is **mean nearest-5 in annulus** (the close neighbors that drive navigation).

**RESULTS (30 episodes/density, M0-spacing proxy):**

| density | lidar (m) | comm (m) | % steps annulus≥1 | mean #in annulus | mean nearest-5 in annulus |
|---|---|---|---|---|---|
| 0.20 | 5 | 8  | 17.6% | 0.327 | 0.085 |
| 0.20 | 5 | 10 | 21.5% | 0.436 | 0.125 |
| 0.30 | 5 | 8  | 27.6% | 0.535 | 0.225 |
| 0.30 | 5 | 10 | 29.8% | 0.701 | 0.302 |
| 0.30 | 4 | 10 | 42.0% | 1.073 | 0.425 |

> ✅ **CHECKPOINT 0 DECIDED → PRIMARY: LiDAR = 5 m, comm = 10 m** (best baseline-vs-exposure trade).
> **Backup A → LiDAR = 4 m, comm = 10 m** — ~2× the comm-only exposure (nearest-5 0.43 vs 0.30 at d0.30); use if the Stage 3 gate comes out weak (harder baseline is the cost).
> **Backup B → LiDAR = 5 m, comm = 8 m** — cleanest narrative (changes only ONE variable vs M0, which trained at comm 8).
> **Citation:** LiDAR ≈ 5 m = *effective drone-to-drone detection range under adverse (sunlight/dust) conditions* for compact rangefinders (Garmin LIDAR-Lite v3, Benewake TF02 — datasheet maxima are longer; cite the effective small-target range). Comm 10 m is well within ZigBee/WiFi (10–20 m+), restoring the physically-correct sensing < comm ordering.
> **Honest note:** exposure is meaningful but moderate (comm-only neighbor present ~22–30% of steps at LiDAR 5) — clears the "comm *can* matter" bar, but the Stage 3 gate stays genuinely uncertain.

---

## STAGE 1+2 — Env sanity + solvability (~minutes; optional short train)
Confirms the env change broke nothing, and that the chosen short LiDAR is still navigable.

**1. Additivity sanity** (default lidar=12 must reproduce M0 ram ≈ 80/74):
```powershell
& $py probe_ram.py 2 models\apex_ultra_glide_v14_comm8_lidar_final.zip 30
```
**2. Solvability at chosen LiDAR** (no retrain — expect a drop; just confirm it's not ~0):
```powershell
# chosen LIDAR=5 COMM=10; f=0 (no adversary). Expect a clear drop vs 95.6/91.1 — just confirm it's not ~0.
& $py Phase_CD\eval_shortlidar.py models\apex_ultra_glide_v14_comm8_lidar_final.zip 5 10 30
```

**RESULTS:**

| check | d=0.20 | d=0.30 | notes |
|---|---|---|---|
| additivity (lidar=12) — expect ≈80/74 |  |  |  |
| M0 @ short LiDAR, no retrain (success) |  |  |  |

> ⛔ **REVIEW CHECKPOINT 1 (quick / async):** bring the two rows. Claude green-lights the 5 M ablation, or relaxes LiDAR by 1 m if the task looks impossible.

---

## STAGE 3 — Ablation = THE GATE (2 trainings ~5 M steps each + eval)
Trains the pair that decides everything. **comm-ON vs comm-OFF**, same LiDAR.

```powershell
# comm-ON  (LiDAR 5, comm 10)
& $py Phase_CD\train_shortlidar.py 5 10
# comm-OFF (ablation: communication disabled -> neighbor block = zeros)
& $py Phase_CD\train_shortlidar.py 5 0
```
Models save to `models\short_lidar5_comm10_final.zip` / `models\short_lidar5_comm0_final.zip`. Then evaluate both, **no adversary**:
```powershell
& $py Phase_CD\eval_shortlidar.py models\short_lidar5_comm10_final.zip 5 10 200
& $py Phase_CD\eval_shortlidar.py models\short_lidar5_comm0_final.zip  5 0  200
```
Output: `Phase_CD\results\comm_value_ablation.csv` (the eval prints `comm_value` once both rows exist).

**RESULTS:**

| model | d=0.20 | d=0.30 |
|---|---|---|
| comm-ON  (`short_lidar5_comm10`) |  |  |
| comm-OFF (`short_lidar5_comm0`) |  |  |
| **comm_value = ON − OFF (pp)** |  |  |

> ⛔ **REVIEW CHECKPOINT 2 (CRITICAL — decides the paper):** bring the gate number.
> - `comm_value ≥ ~5–10 pp` → comm is used & poisonable → **proceed to Stage 4 (build the trust defense).** ✅
> - `comm_value ≈ 0` → comm redundant even under partial observability → **fundamental-limit paper; stop building.** ❌

---

## STAGE 4 — Byzantine attack + T-Cell trust defense  (DEFERRED — only if the gate passes)
Designed with Claude after Checkpoint 2. Sketch: traitor poisons comm in the comm-only annulus (env `deception_mode` / `_falsify_broadcast`, + a `false_alert` field) → measure no-defense drop → build T-Cell trust (agreement vs. directly-verifiable info) → oracle-test a perfect-trust upper bound → train **M2**. Headline: **no-trust vs trust at f = 1, 2, 3**, trust-ID ROC, no-traitor cost.

---

## Master results ledger (keep updated)

| stage | config | metric | d=0.20 | d=0.30 | date |
|---|---|---|---|---|---|
| 0 | geometry (chosen pair) | nearest-5 in annulus |  |  |  |
| 1 | additivity (lidar=12) | ram honest_success |  |  |  |
| 2 | M0 @ short LiDAR | no-adv success |  |  |  |
| 3 | comm-ON | no-adv success |  |  |  |
| 3 | comm-OFF | no-adv success |  |  |  |
| 3 | **gate** | **comm_value (pp)** |  |  |  |

## When to bring results to Claude
1. **After Stage 0** — required (Claude picks LiDAR/comm value + citation).
2. **After Stage 1+2** — quick (confirm trainable).
3. **After Stage 3 gate** — required, decides build-vs-limit (the whole paper hinges here).

## Reference numbers (established this session, M0, f=2)
no-defense 80.4/74.4 · evasion 79.7/73.8 · coordination 77.0/71.9 · speed 79.2/73.4 · clean baseline (no rammer) 95.6/91.1.
