# Plan of Action — TA-MAPPO Phase B Benchmark Calibration
# Target: IEEE Journal Publication
# Last Updated: 2026-06-09 (rev 3 — CALIBRATION COMPLETE)

---

## ✅ STATUS: CALIBRATION COMPLETE

The density calibration is finished. Final numbers (1,000 maps/density point,
shared environment config, `final_validation_results_20260609_190542.csv`):

| Mode | Ceiling | Solvability at ceiling | 95% CI |
|---|---|---|---|
| **Clustered** | **0.30** | 92.5% ± 2.1% | [90.6%, 94.4%] |
| **Scattered** | **0.25** | 92.1% ± 1.6% | [90.7%, 93.5%] |

**Calibrated shared config:** og=1.5, osc=1.5, sp=0.50, sc_g=5.0, bfs=0.40
(gc=1.0, inter=0.20 free). Identical for both modes — only spawn protocol differs.

**What we did NOT do (and why):** the 906-combo Stage 2 tournament was
deliberately skipped. Environment parameters are design choices, not learned
hyperparameters, so only the chosen config needs high-resolution validation.
Going straight from the Stage 1 survey to the 1,000-map curve cut ~18 hours
of compute and produced a cleaner, more defensible result.

**Next:** set the calibrated params in the training env → run Phase B RL
training (see "After Calibration" below). The Stage 1/Stage 2 detail below
is kept as a methodology record.

---

## Overview

Before running Phase B RL training, we need to establish the correct
obstacle density and environment parameters through a rigorous geometric
feasibility calibration. This ensures every training episode is provably
solvable for all 10 drones — a requirement for both training stability
and IEEE peer review credibility.

The calibration is split into three completed/ongoing stages and two
upcoming stages, run separately for clustered and scattered spawn modes.

---

## What Has Been Done

### Stage 0 — v3 Full Sweep (COMPLETED, partially wasted)

- **Script:** `density_sweep_v3_10drone_5832combos.py`
- **What it did:** Swept 5,832 parameter combinations × 50 maps each
  (Stage 1), then passed 5,574 survivors to Stage 2 with 200 maps.
- **Problem:** Stage 1 filter was too loose (S2_MIN_CEILING=0.20,
  S2_MAX_CEIL_DIFF=0.10) — 95.6% of combos passed, making Stage 2
  essentially a repeat of the full sweep at 4× cost.
- **Stage 2 was killed** at 769/5574 combos (13.8% complete) to avoid
  further waste.
- **Results file:** `density_sweep_v5_results_20260608_153206.csv`
  (contains complete Stage 1 data for all 5,832 combos + partial Stage 2)

### Key Findings from Stage 0

| Finding | Detail |
|---|---|
| obs_goal_clearance=1.0 excluded | Only 0.10m BFS margin near goal — unsafe for 10-drone simultaneous approach |
| Clustered spawn is superior | Achieves ceiling=0.30 vs scattered ceiling=0.25 (with og=1.0) |
| Without og=1.0: both modes cap at 0.25 | og=1.5/2.0 is the safe choice; ceiling drops to 0.25 |
| bfs_clearance=0.40 (margin=0.10) | Consistently gives highest pct across all configs |
| inter_drone_min, goal_spawn_clr | Do not significantly affect ceiling — free parameters |
| Stage 1 (50 maps) has high variance | Most configs score 100% at d=0.25 — cannot discriminate |

### Why obs_goal_clearance=1.0 Was Excluded

Three compounding reasons:
1. **Physical margin:** obstacle surface at 1.0m from goal + BFS
   inflation 0.40m → navigable boundary only 0.60m from goal center.
   With goal arrival radius ~0.5m, only 0.10m (one BFS grid cell) of
   margin remains — below reliable path resolution.
2. **Multi-agent congestion:** 10 drones converge on one goal
   simultaneously. The 0.60m navigable zone cannot accommodate all 10
   without cascade near-goal collisions, corrupting the terminal reward.
3. **IEEE defensibility:** og=1.5 ("10× drone radius") has a clear
   physical justification reviewers can verify independently.

---

## Script Bugs Fixed (rev 2, 2026-06-09)

Eight problems identified and corrected before any scripts were run:

| # | Problem | Fix |
|---|---|---|
| 1 | Clustered S2_TARGET_CEILING was 0.25, should be 0.30 | Changed to 0.30; ~906 combos with og≠1.0 showed ceiling=0.30 in S1 |
| 2 | pct filter (80%) was dead code — all ceiling≥0.25 combos pass it | Set S2_MIN_PCT_AT_CEIL=0.0 with explanatory comment |
| 3 | S1 ceiling labels noisy at 50 maps (95% CI ±6.9pp) | S2 (200 maps, CI ±3.4pp) is the authoritative re-classification |
| 4 | Scattered ceiling=0.30 not statistically credible (CI [81.1%, 99.3%]) | Scattered target kept at 0.25; 0.30 reported as bonus if confirmed |
| 5 | S2 seed offsets too small — overlap with S1 seeds | Clustered: 500M, Scattered: 2,500M (non-overlapping seed bands) |
| 6 | Final validation SEED_BASE=900M inside S2 scattered range | Changed to 5,000M (above S2 scattered max of 4,495,322,000) |
| 7 | Scattered Stage 2 ran 75 combos; gc/inter don't affect BFS | Deduplicated to unique (og,osc,sp,sc_g,bfs) env configs (~10–15) |
| 8 | Ranking noise: ±3.5pp CI at n=200, rank 1 vs rank 5 indistinct | Added 95% CI column in ranking; added equivalence note |

**Seed space layout (final, non-overlapping):**
```
S1 seeds   :          0 →   495,322,000
S2 cluster : 500,000,000 → 2,495,322,000
S2 scatter : 2,500,000,000 → 4,495,322,000
Final val  : 5,000,000,000 → 5,004,019,900
```

---

## How the Calibration Was Actually Done (COMPLETED)

We did NOT run the 906-combo Stage 2 tournament. After fixing the 8 script
bugs we re-examined the goal and realised that the environment parameters are
design choices, not learned hyperparameters — so only the chosen configuration
needs high-resolution validation. The actual pipeline executed was:

1. **Stage 1 survey** (already complete) — 5,832 combos × 50 maps.
   File: `density_sweep_v5_results_20260608_153206.csv`

2. **Config verification** — `analyze_best_configs.py` (run in swarm_rl env).
   - Confirmed `og=1.5, osc=1.5` is the best feasible config (osc=1.5 beats
     osc=2.0/2.5 on mean ceiling and pct@0.30).
   - Confirmed the SAME config is top-tier for both spawn modes → use one
     shared environment, vary only the spawn protocol.

3. **Final validation** — `final_validation_1000maps.py`, density curve at
   1,000 maps/point for both modes (disjoint seed space, base 5×10⁹).
   File: `final_validation_results_20260609_190542.csv`
   - Clustered ceiling **0.30** (92.5% ± 2.1%, 95% CI [90.6, 94.4])
   - Scattered ceiling **0.25** (92.1% ± 1.6%, 95% CI [90.7, 93.5])
   - Both lower CI bounds > 90% → claims survive the confidence interval.

4. **Figure** — `plot_calibration_curve.py` →
   `calibration_solvability_curve.pdf` / `.png` (solvability vs density,
   both modes, 95% CI bars, 90% threshold, ceilings starred).

5. **Paper text** — all numbers, the table, the figure snippet, and the
   methodology are filled in `paper_writing_notes.md`.

> The `stage2_clustered_200maps.py` and `stage2_scattered_200maps.py` scripts
> remain in the folder (bug-fixed) but were intentionally not run. They are
> kept only as a fallback if a reviewer ever demands the exhaustive 200-map
> tournament.

---

## ► NEXT PLAN OF ACTION: Phase B RL Training

The calibration is done. Everything below is the next phase of work.

---

### Environment Parameters (CALIBRATED — set these in training env)

Update `swarm_env_step_B5_v15_master.py` with the calibrated shared config
(identical for both spawn modes — only the spawn protocol differs):

| Parameter | Value |
|---|---|
| obs_goal_clearance | **1.5** |
| obs_sc_clearance | **1.5** |
| spawn_obstacle_clearance | **0.50** |
| sc_goal_min_dist | **5.0** |
| goal_spawn_clearance | 1.0 (free) |
| bfs_clearance | **0.40** (margin 0.10) |
| inter_drone_min | 0.20 (free) |
| Clustered density ceiling | **0.30** (92.5% ± 2.1%) |
| Scattered density ceiling | **0.25** (92.1% ± 1.6%) |

### Curriculum Design (Phase B v16)

For **clustered** training (primary mode, ceiling 0.30):

```
Stage 1 — Warm-up    (0–5M steps):   density = 0.15
Stage 2 — Ramp       (5–15M steps):  density ramps 0.15 → 0.28
Stage 3 — Lock-in    (15–50M steps): density fixed at 0.28–0.30
```

> **Lock-in note:** the calibrated ceiling is 0.30 (92.5% solvable). At 0.30,
> ~7.5% of episodes have ≥1 agent with no valid path. For a cleaner terminal
> reward signal you may lock-in at **0.28** (≈96% solvable) and still report
> the *ceiling* as 0.30 — the calibration claim is about feasibility, the
> lock-in density is a training-stability choice. Do NOT train above 0.30.

For **scattered** training (if used), cap the ceiling at 0.25.

### Validation After Training

After Phase B training completes:
1. Run `k_fold_master_B10.py` — 5-fold cross-validation
2. Run `evaluate_v16_IEEE_Final.py` — benchmark evaluation
3. Compare success rate against Phase A baseline (99.68%)
4. Target: ≥ 85% success rate at ceiling density for Phase B

---

## File Index

| File | Purpose | Status |
|---|---|---|
| `density_sweep_v5_results_20260608_153206.csv` | Stage 1 survey results (5,832 combos × 50 maps) | input |
| `analyze_best_configs.py` | Verifies best config from Stage 1 (osc=1.5, shared-config) | done |
| `final_validation_1000maps.py` | Density-curve validation, 1000 maps/point, both modes | done |
| `final_validation_results_20260609_190542.csv` | **The numbers cited in the paper** | done |
| `plot_calibration_curve.py` | Generates the solvability-vs-density figure | done |
| `calibration_solvability_curve.pdf` / `.png` | **The paper figure** (vector + preview) | done |
| `paper_writing_notes.md` | All IEEE paper text, table, figure snippet, justifications | done |
| `plan_of_action.md` | This file | living |
| `stage2_clustered_200maps.py`, `stage2_scattered_200maps.py` | Bug-fixed Stage 2 scripts — NOT run (fallback only) | unused |
| `stage2_selected_configs.txt` | Config list from the rejected Stage 2 path | obsolete |

---

## Summary Timeline

```
DONE   Stage 1 survey (5,832 combos × 50 maps)
DONE   analyze_best_configs.py — verified og=1.5/osc=1.5, shared config
DONE   final_validation_1000maps.py — clustered 0.30 / scattered 0.25
DONE   plot_calibration_curve.py — paper figure
DONE   paper_writing_notes.md — all numbers/table/figure/methodology filled
NEXT   Set calibrated params in swarm_env_step_B5_v15_master.py
NEXT   Run Phase B RL training (50M steps, lock-in density 0.28)
NEXT   k_fold_master_B10.py + evaluate_v16_IEEE_Final.py
NEXT   Write IEEE paper using paper_writing_notes.md
```

---

## Decision Log (Why We Did What We Did)

| Decision | Reason |
|---|---|
| Exclude og=1.0 | <0.10m BFS margin near goal; unsafe for 10-drone convergence |
| Separate clustered/scattered | Different ceilings, different best configs, separate IEEE numbers |
| Clustered S2 ceiling = 0.30 | ~906 og≠1.0 combos showed ceiling=0.30 in S1; Stage 2 confirms or rejects |
| Scattered S2 ceiling = 0.25 | Scattered ceiling=0.30 not credible (S1 CI [81.1%, 99.3%] at n=41-42) |
| Scattered deduplicated by env config | gc and inter_drone_min do not affect BFS — running 75 variants is noise |
| 200 maps in Stage 2 | 95% CI ≤ ±3.4pp — tight enough for publication |
| 1000 maps in final validation | Eliminates seed-reuse criticism; 5 independent batches give mean ± std |
| Non-overlapping seed bands (S1/S2/final) | Prevents seed reuse across stages; bands verified non-overlapping |
| Diagonal corner-cutting fix in BFS | Prevents artificial paths through obstacle corners |
