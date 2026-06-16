# CLEAN-SHEET ACTION PLAN — step-by-step runbook (with commands)

**Date:** 2026-06-16 · **Decision:** Path B (scientific analysis paper).
**Goal:** every reported number comes from the verified-clean model **M0** with the comm model disclosed.
**Refs:** `LEAK_REMEDIATION_LOG.md`, `MODEL_LEAK_LEDGER.md`, `CTDE_LEAKAGE_INVESTIGATION.md`, `leaky/README.md`.

---

## 0. SETUP (do this in every new terminal)

Open **PowerShell** in the project root `D:\Swarm\BTP`, then set the env-python shortcut:

```powershell
cd D:\Swarm\BTP
$py = "C:\Users\Srinivasa\miniconda3\envs\swarm_rl\python.exe"
```

> Why `$py`: `conda activate` does NOT switch the interpreter in this setup. Always call the env python by
> full path. Test it: `& $py -c "import stable_baselines3, torch, pandas; print('env OK')"` → should print `env OK`.

**The one clean model (headline):** `models/apex_ultra_glide_v14_comm8_lidar_final.zip` (= "M0").
Verify only clean models remain:
```powershell
Get-ChildItem models\*.zip | Select-Object Name
# expect ONLY: apex_ultra_glide_v14_comm8_lidar_final.zip, apex_ultra_glide_v14_comm0_nocong_final.zip, apex_ultra_glide_M1_ram_final.zip
```

---

## STEP 0 — Quarantine leaky artifacts  ☑ DONE (already executed)
51 leaky models + leaky results + v14_8_0m code were moved to `leaky/`. Nothing to run. To confirm:
```powershell
Get-ChildItem leaky\models | Measure-Object   # ~51 files
Get-ChildItem results -Directory               # clean dirs only: comm_sweep, phase_c_probe, phase1, phase2, phase3, clean
```

---

## STEP 1 — Scripts re-pointed to M0  ☑ DONE (already edited)
These 4 scripts were changed from leaky `v14_8_0m` → clean M0 + `congestion="lidar"`, output → `results\clean\`.
You don't need to edit anything; this is just so you know what changed:
| Script | What changed |
|---|---|
| `eval_ablate_feature.py` | `MODEL_PATH` → comm8_lidar; `CONGESTION_MODE="lidar"`; out → `results\clean\eval_ablation\` |
| `eval_comm_blackout.py` | model → comm8_lidar; env `congestion_mode="lidar"`; out → `results\clean\comm_sweep\` |
| `eval_comm_sweep_clean.py` | **NEW** clean sweep (one model, eval-time range gating) |
| `eval_ablate_feature.py congestion` | replaces the old `eval_nocongestion.py` leaky run |

Confirm a script points to M0:
```powershell
Select-String -Path eval_ablate_feature.py -Pattern "MODEL_PATH"
```

---

## STEP 2 — Run the clean Phase-B analysis re-runs  ◐ (these are currently running in background)

If you ever need to run them yourself, here are the exact commands. Each writes a CSV under `results\clean\`.
(~5–15 min per command; the feature ablation loops 8 times so it is the longest.)

### 2a. Feature-importance ablation (8 groups)
```powershell
foreach ($g in "none","lidar","neighbors","sync","congestion","egovel","goaldir","trajectory") { & $py eval_ablate_feature.py $g }
```
Output: `results\clean\eval_ablation\ablate_<group>_metrics.csv` (column `success_rate`, `drone_collision_rate`).

### 2b. Comm blackout (8 m → 0 m)
```powershell
& $py eval_comm_blackout.py
```
Output: `results\clean\comm_sweep\comm8_to_0m_blackout_metrics.csv`.

### 2c. Comm range sweep (clean, eval-time gating 0/3/5/8/∞)
```powershell
& $py eval_comm_sweep_clean.py
```
Output: `results\clean\comm_sweep\comm_range_sweep_clean.csv`.

### Read any result quickly
```powershell
Import-Csv results\clean\eval_ablation\ablate_none_metrics.csv | Format-Table
Import-Csv results\clean\comm_sweep\comm_range_sweep_clean.csv | Format-Table
```

---

## STEP 3 — Fill the result tables
Copy the `success_rate` values (×100 for %) from each CSV into the tables in `LEAK_REMEDIATION_LOG.md` §6.
- baseline = `ablate_none_metrics.csv` (this is the clean headline check; should ≈ 95.55 / 91.10).
- each feature's Δ = baseline − that feature's success.
- comm sweep: read `comm_range_sweep_clean.csv` rows (one per range × density).

---

## STEP 4 — (Recommended) Comm-degradation robustness eval — pre-empts "are you sure?"
This single experiment shows the policy survives noisy/dropped comm because it is LiDAR-grounded.
**Script not built yet.** It needs `comm_noise_std` / `comm_dropout_p` added to the broadcast in
`swarm_env_step_B10_8_0m._observe`, then an eval loop over noise levels. To create + run it, ask Claude:
> "build `eval_comm_robustness.py`: add comm_noise_std/comm_dropout_p to _observe, eval M0 over
>  noise σ∈{0,0.1,0.3} and dropout p∈{0,0.25,0.5}, save results/clean/comm_robustness.csv"

Then:
```powershell
& $py eval_comm_robustness.py
```
Fill table R6 in `LEAK_REMEDIATION_LOG.md`. Expectation: graceful degradation (no cliff).

---

## STEP 5 — (Optional) Multi-seed headline for error bars
The eval scripts use a fixed seed formula. For 3 seeds, change the seed base in `eval_ablate_feature.py`
(`seed = 900_000_000 + ...`) to `910_000_000`, `920_000_000`, re-run group `none`, and average. Or ask Claude
to parametrize `--seed_base`. Report mean ± sd on the 95.55 / 91.10 headline.

---

## STEP 6 — Paper edits (no code; do in the manuscript)

**(a) Add this comm-disclosure paragraph** (System/Observation section):
> "Each drone observes its own LiDAR (48 rays, 12 m range) and receives position/velocity broadcasts from
> peers within an 8 m communication range; communication is modeled as perfect and zero-latency. A
> centralized critic uses the global state during training only; it is never part of the actor's forward
> pass, so decentralized execution uses only local LiDAR plus ≤ 8 m communicated state."

**(b) Reword the deception claim** wherever it appears:
> NOT "communication is ignored" → USE "the swarm's success is robust to corrupted broadcasts because
> LiDAR-grounded collision avoidance dominates; corrupted comm shifts the action (~19 %) but not the outcome."

**(c) Headline model = M0 everywhere.** Cite only `results\clean\*` and `results\phase_c_probe\*`.

---

## STEP 7 — Supplementary material to ship with the paper
Include: `leak_test_local.py`, `CTDE_LEAKAGE_INVESTIGATION.md`, `MODEL_LEAK_LEDGER.md`,
`LEAK_REMEDIATION_LOG.md`, this runbook. They constitute reproducible proof the actor has no privileged info.

---

## WHAT IS ALREADY CLEAN — do NOT re-run (Phase C/D)
These used M0 from the start; numbers stand as-is:
| Result | Command (only if you want to reproduce) | CSV |
|---|---|---|
| Ram scaling f=1/2/3 | `& $py probe_ram.py 1` / `2` / `3` | `results\phase_c_probe\probe_ram_f*.csv` |
| Deception (inert) | `& $py probe_deception.py 2 false_velocity` | `results\phase_c_probe\probe_f2_*.csv` |
| Oracle ceiling (naive) | `& $py probe_ram_oracle.py 2 2.0 models\apex_ultra_glide_v14_comm8_lidar_final.zip 200` | `oracle_evade_f2_d2.0.csv` |
| Oracle ceiling (smart) | `& $py probe_ram_oracle_smart.py 2 models\apex_ultra_glide_v14_comm8_lidar_final.zip 200` | `oracle_smart_f2.csv` |
| Leak test (proof clean) | `& $py leak_test_local.py models\apex_ultra_glide_v14_comm8_lidar_final.zip lidar` | (console) |

> Reminder (honest): cleaning the leak does **not** improve Phase C/D — it was already clean. The fundamental
> ~15–20 pp ram loss stands. This whole runbook only makes the **Phase B comm/feature analysis** defensible.

---

## QUICK CHECKLIST
```
[x] STEP 0  quarantine leaky -> leaky/
[x] STEP 1  scripts re-pointed to M0 + congestion=lidar
[ ] STEP 2  run clean re-runs (2a feature ablation, 2b blackout, 2c comm sweep)   <-- running now
[ ] STEP 3  fill result tables in LEAK_REMEDIATION_LOG.md §6
[ ] STEP 4  (rec.) build + run eval_comm_robustness.py
[ ] STEP 5  (opt.) multi-seed headline
[ ] STEP 6  paper edits (disclosure paragraph, reword deception, headline=M0)
[ ] STEP 7  ship supplementary
```
