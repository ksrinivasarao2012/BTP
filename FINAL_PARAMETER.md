# FINAL PARAMETER — v14 Density Calibration (PERMANENT — DO NOT DELETE)

> **Status:** LOCKED / OFFICIAL RECORD
> **Last updated:** 2026-06-13
> **Purpose:** Authoritative, verified record of the v14 density calibration —
> geometric solvability, agent performance, the environment match, and the
> chosen operating density. **Do not delete or overwrite.**

---

## 1. Locked v14 parameters

| Parameter | Value |
|-----------|-------|
| `cluster_radius` | 1.5 |
| `spawn_obstacle_clearance` | 0.0 |
| `sc_goal_min_dist` | 8.0 |
| `goal_spawn_clearance` | 8.0 |
| `inter_drone_min` (→ effective min_dist) | 0.30 (→ 0.60) |
| `goal_exclusion_radius` | 2.0 |
| drone_radius / n_drones / field | 0.15 / 10 / 20×20 |
| BFS solvability grid / clearance | 0.2 m / 0.20 m (= drone_radius + 0.05) |

---

## 2. Environment match (VERIFIED)

- The real v14 model is **`apex_ultra_glide_v14_final.zip`**, trained by
  `train_step_B10_extended_v14.py` → **`swarm_env_step_B10.py`**.
- Live and archived `swarm_env_step_B10.py` are **byte-identical** (`diff` confirmed).
- `swarm_env_step_B10_8_0m.py` (planned 8.0M-step variant) has **identical** map-generation
  parameters; its model was **never trained** (no `_8_0m_final.zip` on disk).
- ⚠️ `swarm_env_step_B5_v14_master.py` is **NOT** the v14 env (old toy env: fixed corner
  spawn, fixed goal (17,17), count-based obstacles). Do not use it for calibration.
- The sweep script **`density_sweep_v14_10000maps.py`** reproduces the v14 env's generation,
  spawn, and solvability parameters **exactly**.

---

## 3. Geometric solvability (10,000 maps/density)

Metric = `pct_all10_ok` = (maps where all 10 drones can BFS-reach goal) / **clean maps**.
Threshold = **95%** (`SOLVABILITY_THRESHOLD = 0.95`). Wilson 95% CIs.

| Density | actual | Solvability | clean n | Wilson 95% CI | Verdict |
|---------|--------|-------------|---------|---------------|---------|
| 0.20 | 0.205 | 99.22% | 4596 | [98.9, 99.4] | ✅ PASS |
| 0.25 | 0.253 | 97.86% | 3124 | [97.3, 98.3] | ✅ PASS |
| 0.26 | 0.263 | 96.53% | 2827 | [95.8, 97.1] | ✅ PASS (curriculum lock-in) |
| **0.27** | 0.272 | 96.78% | 2547 | [96.0, 97.4] | ✅ **PASS — last clear pass (ceiling)** |
| 0.28 | 0.282 | 94.30% | 2351 | [93.3, 95.2] | ⚠️ BORDERLINE (CI straddles 95) |
| 0.29 | 0.292 | 92.40% | 2092 | [91.2, 93.5] | ❌ FAIL |
| 0.30 | 0.302 | 89.65% | 1932 | [88.2, 90.9] | ❌ FAIL |

Source CSVs (PhaseB2/): `density_sweep_v14_10000maps_results_20260613_191313.csv`,
`density_sweep_v14_specific_results_20260613_222013.csv`.

**Fairness ceiling = 0.27.** The 95% line is crossed at 0.28.

Note: d=0.35 was only ever measured at 5/11 clean maps (100-map params run, CI [21, 72]) —
NOT a validated figure. Reject d ≥ 0.28 by the measured ceiling; d ≥ 0.30 also by monotonicity.

---

## 4. Agent performance (v14 model, 200 maps/density, ~2000 drone-outcomes)

From `evaluate_v14_densities.py` (real model + real env). Scored only on maps the env
filters to be 100% solvable for all 10 drones (so denominator differs from §3).

| Density | Agent success | Wilson 95% CI (n≈2000) |
|---------|---------------|------------------------|
| 0.10 | 99.26% | [98.8, 99.6] |
| 0.15 | 98.81% | [98.2, 99.2] |
| 0.20 | 97.10% | [96.3, 97.7] |
| 0.25 | 95.92% | [95.0, 96.7] |
| 0.30 | 93.62% | [92.5, 94.6] |

**The agent is NOT the bottleneck** — it clears even 0.30 at 93.6% on solvable maps.
The density cap is about FEASIBILITY (unsolvable raw maps), not agent capability.

---

## 5. Conclusion

- **Operating density 0.25–0.26 is fully justified** (high solvability + high agent success).
  Curriculum lock-in at **0.26** is verified feasible.
- **Maximum fair density = 0.27** if more difficulty is wanted (still ≥95% solvable).
- **Reject d ≥ 0.28** (solvability drops below the 95% fairness bar).
- Solvability (§3) and agent success (§4) are different metrics with different denominators
  and must not be conflated; both are reported here for completeness.
