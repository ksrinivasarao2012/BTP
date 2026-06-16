# `leaky/` — QUARANTINE (do NOT use for reported results)

**Created:** 2026-06-16. Everything here was trained with, or produced by, a model that feeds the **actor**
privileged information it could not sense in real decentralized flight. See `../MODEL_LEAK_LEDGER.md` and
`../CTDE_LEAKAGE_INVESTIGATION.md` for the full audit and `../leak_test_local.py` for the test.

## Why these are leaky
- **Omniscient neighbors** (no comm range gate) — `swarm_env_step_B10.py` & earlier envs: the actor saw ALL
  drones' positions/velocities regardless of distance. (v10–v14 lineage, v15–v20 masters.)
- **Ground-truth congestion** (`congestion_mode="env"`) — an exact count of drones within 1 m, not sensed.
  (`v14_8_0m`, `comm3`, `comm5`, `comm0`.) Measured ~4.6 % actor dependence (leak_test_local.py).

## Contents
- `models/` — 51 files: v10–v14 lineage, v15–v20 masters, `v14_8_0m`, `comm3/5/0` + their vecnormalize pkls.
- `results/` — `comm_sweep/` (leaky CSVs), `eval_ablation/`, `v14_8_0m_sweep/`, `v14/`, `v15/`, `v17/` (k-folds).
- `code/` — `train_step_B10_extended_v14_8_0m.py` (env-congestion trainer), `dry_run_v14_8_0m.py`.

## What is CLEAN (kept in repo root, NOT here)
- `models/apex_ultra_glide_v14_comm8_lidar_final.zip` ← **M0, the publication headline** (8 m comm + LiDAR congestion)
- `models/apex_ultra_glide_v14_comm0_nocong_final.zip` (clean, no comm)
- `models/apex_ultra_glide_M1_ram_final.zip` (clean, ram-trained)
- `results/phase_c_probe/` (ram/deception/oracle — all run on M0), `results/comm_sweep/comm8_lidar*` + `comm0_nocong*`

> The leaky env code itself (`Phase B/Phase_B5_Synchronization/swarm_env_step_B10.py`, ungated) is left in the
> Phase B tree as historical record; it is not used by the clean pipeline.
