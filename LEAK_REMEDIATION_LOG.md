# Leak Remediation Log — what was removed, re-run, and its impact

**Date:** 2026-06-16 · **Decision:** commit to **Path B (scientific analysis paper)**.
**Refs:** `MODEL_LEAK_LEDGER.md`, `CTDE_LEAKAGE_INVESTIGATION.md`, `leak_test_local.py`, `leaky/README.md`,
`CLEAN_SHEET_ACTION_PLAN.md`.

This log records exactly what was done to eliminate every leaky-model-derived result from the reported
pipeline, how much it is expected to change the numbers, and whether it changes any conclusion (Phase B or
Phase C/D).

---

## 1. What "leaky" meant (recap)
The actor (deployed drone brain) was fed information a real decentralized drone can't sense:
- **Omniscient neighbors** (no comm-range gate) — v10–v14 lineage, v15–v20 masters.
- **Ground-truth congestion** (`congestion_mode="env"`, exact count of drones within 1 m) — `v14_8_0m`,
  `comm3/5/0`. Measured actor dependence ≈ 4.6 % (`leak_test_local.py`).

The clean model **M0 = `apex_ultra_glide_v14_comm8_lidar_final.zip`** uses **8 m gated comm + LiDAR-based
congestion**; verified: global block 0.0 %, stagnation 0.2 %, congestion from own LiDAR.

## 2. What was REMOVED from the reported pipeline
- **Quarantined to `leaky/`** (STEP 0, done): 51 leaky model files (zips + pkls), all leaky result dirs
  (`eval_ablation`, `v14_8_0m_sweep`, `v14`, `v15`, `v17` k-folds, leaky `comm_sweep` CSVs), and the
  v14_8_0m trainer/dry-run code. `models/` and `results/` now contain ONLY clean artifacts.
  (The archive is kept as the scientific record of the issue — it is excluded, not cited. Delete `leaky/`
  entirely only if you want it physically gone; nothing in the clean pipeline depends on it.)

## 3. What was RE-RUN clean (on M0, `congestion=lidar`)
Scripts re-pointed from leaky `v14_8_0m` to clean **M0** and writing to **`results/clean/`**:
| Result | Script (edited) | Status |
|---|---|---|
| Feature-importance ablation (8 groups) | `eval_ablate_feature.py` → `results/clean/eval_ablation/` | ◐ running |
| Comm blackout (8 m → 0 m) | `eval_comm_blackout.py` → `results/clean/comm_sweep/` | ◐ running |
| Comm range sweep (eval-time gating 0/3/5/8/∞) | `eval_comm_sweep_clean.py` (new) → `results/clean/comm_sweep/` | ◐ running |
| Congestion ablation | superseded by feature-ablation `congestion` group (clean) | n/a |

> Comm-sweep method change: the old sweep trained one (leaky) model per range. The clean replacement
> evaluates the single clean M0 at different EVAL-TIME comm ranges (a deployment-robustness curve). This is
> the scientifically honest replacement that needs no leaky per-range models.

## 4. HOW MUCH does this change the numbers? (honest estimate, to be confirmed by §6)
- The contamination was the **mild** congestion leak (~4.6 % action dependence), not omniscience (the
  omniscient models were only the unlimited-range sweep point, now replaced by eval-time gating on M0).
- M0 leans **more** on its own-LiDAR congestion (11.6 %) than the leaky model did on ground-truth (4.6 %),
  so the clean feature-importance for "congestion" should **rise**, and **LiDAR stays dominant**.
- Absolute success on ablations/blackout/sweep should move by **a few points at most**; the **rankings and
  qualitative conclusions are expected to be unchanged or stronger.**
- Headline (95.55 / 91.10) is **unchanged** — it was always from M0.

## 5. Does this IMPROVE Phase C / Phase D? — NO (important, honest)
- **Phase C/D was already 100 % clean.** Ram scaling (−9 pp/rammer), deception (inert), and the oracle
  ceiling (~75–80 %) were ALL run on M0. The leak never touched them.
- Therefore removing the leak **produces no improvement in Phase C/D** and **does not change** the central
  finding: a committed equal-speed rammer imposes a **fundamental ~15–20 pp loss** that local evasion can't
  recover. Do **not** expect the clean redo to rescue C/D.
- Net effect of this whole exercise: it makes **Phase B's communication / feature analysis defensible**; it
  leaves **Phase C/D exactly as it was** (already clean).

## 6. CLEAN RESULTS (filled when the re-runs finish)

### 6a. Feature-importance ablation (M0, clean) — success %, timeout, drone‑collision, total‑collision (eval‑time zeroing)
| Feature zeroed | d=0.20 succ | d=0.30 succ | Δ vs none | rank | d=0.20 timeout | d=0.30 timeout | d=0.20 drone‑coll | d=0.30 drone‑coll | d=0.20 total‑coll | d=0.30 total‑coll |
|---|---|---|---|---|---|---|---|---|---|---|
| none (baseline) | 95.55% | 91.10% | 0 | — | 2.00% | 5.65% | 0.90% | 0.90% | 2.45% | 3.25% |
| LiDAR | 12.15% | 6.70% | -83.40 / -84.40 pp |  | 0.05% | 0.00% | 31.55% | 27.75% | 87.80% | 93.30% |
| obs_neighbors | 91.55% | 85.55% | -4.00 / -5.55 pp |  | 2.15% | 4.50% | 1.60% | 2.30% | 6.30% | 9.95% |
| sync | 94.35% | 88.90% | -1.20 / -2.20 pp |  | 2.15% | 4.65% | 1.30% | 2.50% | 3.50% | 6.45% |
| congestion | 95.90% | 91.10% | +0.35 / 0.00 pp |  | 2.90% | 6.55% | 0.20% | 1.00% | 1.20% | 2.35% |
| ego_vel | 93.00% | 88.65% | -2.55 / -2.45 pp |  | 1.25% | 2.80% | 1.80% | 2.80% | 5.75% | 8.55% |
| goal_dir | 63.00% | 63.80% | -32.55 / -27.30 pp |  | 36.55% | 35.80% | 0.30% | 0.20% | 0.45% | 0.40% |
| trajectory | 95.25% | 90.15% | -0.30 / -0.95 pp |  | 2.40% | 6.20% | 0.60% | 0.90% | 2.35% | 3.65% |

### 6b. Comm range sweep (M0, clean, eval-time gating, congestion=lidar)
| Range | d=0.20 | d=0.30 |
|---|---|---|
| 0 m (blackout) | 90.55% | 83.35% |
| 3 m | 94.50% | 89.35% |
| 5 m | 94.80% | 90.90% |
| 8 m (trained) | 95.55% | 91.10% |
| ∞ | 95.40% | 90.50% |

### 6c. Comm blackout (M0, clean)  ☑ DONE
| Condition | d=0.20 | d=0.30 | Δ |
|---|---|---|---|
| comm ON (8 m) | 95.55 | 91.10 | — |
| comm OFF (0 m) | **90.55** | **83.35** | **−5.0 / −7.75 pp** |

→ Confirms the prior (leaky-model) "−5 to −8 pp" finding. **Conclusion unchanged by cleaning the leak.**

### 6d. Comm robustness full sweep (200 maps/combo)

| noise_std | dropout_p | density | success % | timeout % | collision % |
|-----------|-----------|---------|-----------|-----------|--------------|
| 0.0 | 0.0 | 0.20 | 94.6 | 3.6 | 1.8 |
| 0.0 | 0.0 | 0.30 | 93.6 | 3.8 | 2.6 |
| 0.0 | 0.25 | 0.20 | 92.4 | 4.8 | 2.8 |
| 0.0 | 0.25 | 0.30 | 90.2 | 3.8 | 6.0 |
| 0.0 | 0.5 | 0.20 | 89.8 | 4.8 | 5.4 |
| 0.0 | 0.5 | 0.30 | 90.4 | 3.8 | 5.8 |
| 0.1 | 0.0 | 0.20 | 95.2 | 3.8 | 1.0 |
| 0.1 | 0.0 | 0.30 | 93.6 | 3.8 | 2.6 |
| 0.1 | 0.25 | 0.20 | 94.6 | 3.8 | 1.6 |
| 0.1 | 0.25 | 0.30 | 90.0 | 4.8 | 5.2 |
| 0.1 | 0.5 | 0.20 | 91.0 | 3.6 | 5.4 |
| 0.1 | 0.5 | 0.30 | 89.2 | 3.2 | 7.6 |
| 0.3 | 0.0 | 0.20 | 94.2 | 2.8 | 3.0 |
| 0.3 | 0.0 | 0.30 | 91.2 | 4.8 | 4.0 |
| 0.3 | 0.25 | 0.20 | 93.0 | 4.0 | 3.0 |
| 0.3 | 0.25 | 0.30 | 89.4 | 3.8 | 6.8 |
| 0.3 | 0.5 | 0.20 | 90.0 | 3.8 | 6.2 |
| 0.3 | 0.5 | 0.30 | 89.8 | 3.2 | 7.0 |
| 0.0 | 0.0 | 0.20 | 95.25 | 2.10 | 2.65 |
| 0.0 | 0.0 | 0.30 | 91.15 | 5.20 | 3.65 |
| 0.0 | 0.25 | 0.20 | 94.25 | 2.35 | 3.40 |
| 0.0 | 0.25 | 0.30 | 90.10 | 4.45 | 5.45 |
| 0.3 | 0.0 | 0.30 | 89.90 | 5.60 | 4.50 |
| 0.3 | 0.25 | 0.20 | 94.70 | 2.10 | 3.20 |
| 0.3 | 0.25 | 0.30 | 89.20 | 4.30 | 6.50 |
| 0.3 | 0.5 | 0.20 | 93.85 | 2.30 | 3.85 |
| 0.3 | 0.5 | 0.30 | 87.55 | 3.50 | 8.95 |
| 0.0 | 0.0 | 0.20 | 95.55 | 2.00 | 2.45 |
| 0.0 | 0.0 | 0.30 | 91.10 | 5.65 | 3.25 |
| 0.0 | 0.25 | 0.20 | 94.15 | 2.35 | 3.50 |
| 0.0 | 0.25 | 0.30 | 88.85 | 5.15 | 6.00 |
| 0.0 | 0.5 | 0.20 | 93.00 | 2.30 | 4.70 |
| 0.0 | 0.5 | 0.30 | 88.50 | 3.95 | 7.55 |
| 0.1 | 0.0 | 0.20 | 95.65 | 1.75 | 2.60 |
| 0.1 | 0.0 | 0.30 | 90.85 | 5.50 | 3.65 |
| 0.1 | 0.25 | 0.20 | 94.10 | 2.70 | 3.20 |
| 0.1 | 0.25 | 0.30 | 89.50 | 4.95 | 5.55 |
| 0.1 | 0.5 | 0.20 | 93.20 | 2.00 | 4.80 |
| 0.1 | 0.5 | 0.30 | 88.00 | 3.95 | 8.05 |
| 0.3 | 0.0 | 0.20 | 95.00 | 2.15 | 2.85 |

## 7. Path B framing (scientific + realistic)
- Headline model = M0 everywhere; cite only `results/clean/*` and `results/phase_c_probe/*`.
- Claims: (i) navigator 95.55/91.10; (ii) **comm robust to attack** — range insensitive + deception inert,
  reworded as "robust **despite** comm influence (~19 %), because LiDAR grounds collision avoidance";
  (iii) **physical adversary is the real, fundamental threat** — ram −9 pp/rammer, oracle-bounded ~80 %.
- Disclose the 8 m comm model (one paragraph). Ship `leak_test_local.py` + this log as supplementary.
- Honest scope: deception inert *in this LiDAR-grounded design*; oracle is an upper bound; comm modeled as
  perfect/zero-latency (optionally add the comm-noise robustness eval to bound that assumption).
