# V14_8.0m — Communication-Range Ablation: Detailed Plan

> **Created:** 2026-06-13
> **Scope:** Execution plan for the `v14_8.0m` study (8.0-metre communication
> range enforcement), integrating the verified v14 density calibration.
> **Companion file:** [`FINAL_PARAMETER.md`](FINAL_PARAMETER.md) (density calibration record).

---

## 0. Terminology correction

`8_0m` = **8.0 METRES communication range**, NOT 8.0 million steps. It is an
*ablation study*: take the trained v14 model and restrict each drone's view of
other drones to an 8.0 m radius, then measure the performance cost. This tests
whether the swarm still works without global (privileged) inter-agent state —
the concern raised in the CTDE audit.

---

## 1. What already exists (NOT created in this work — pre-existing in repo)

| Role | File | Key facts (with line refs) |
|------|------|----------------------------|
| Environment | `swarm_env_step_B10_8_0m.py` | `communication_range = 8.0` (L27); neighbor masking `if distance_to_j <= self.communication_range` (L423). Map-generation params **identical** to v14 env `swarm_env_step_B10.py` (verified by diff). |
| Training | `train_step_B10_extended_v14_8_0m.py` | Warm-starts `apex_ultra_glide_v14_final.zip` (L137-167); LR `5e-5`, `ent_coef 0.015` (L169-170); curriculum `[(2M, 0.30), (3M, 0.35)]` (L178-181); saves `apex_ultra_glide_v14_8_0m_final` (L196). |
| Evaluation | `evaluate_v14_8_0m_densities.py` | Loads `apex_ultra_glide_v14_8_0m_final.zip` (L59); densities `[0.10,0.15,0.20,0.25,0.30]` (L79); 200 maps, retries until solvable; writes `v14_8_0m_density_sweep_metrics.csv`. |

**Model status:** `apex_ultra_glide_v14_8_0m_final.zip` does **not** exist → the
training has **not been run yet**.

---

## 2. Scientific objective

Isolate the causal effect of **communication range** on swarm navigation:

- **Baseline (V14):** full/global inter-agent observation → `apex_ultra_glide_v14_final` (exists).
- **Treatment (V14_8.0m):** identical in every way except neighbors beyond 8.0 m
  are masked out of the observation.
- **Clean-comparison principle:** everything else (env physics, curriculum,
  hyperparameters) must stay identical so range is the *only* changed variable.

---

## 3. KEY DECISION — training density (resolve before running)

The existing curriculum trains at **0.30 → 0.35**. Our calibration
([`FINAL_PARAMETER.md`](FINAL_PARAMETER.md) §3) shows both are **below the 95%
solvability ceiling (0.27)**: d=0.30 = 89.65% solvable, d≥0.28 fails.

| Option | Curriculum | Pro | Con |
|--------|-----------|-----|-----|
| **A — keep 0.30→0.35 (recommended)** | identical to V14 | comm-range is the ONLY variable → clean causal ablation | trains on the "solvable subset" of an infeasible density (selection bias, but identical bias to V14 baseline, so it cancels in the comparison) |
| B — recalibrate to ≤0.27 | fair densities | every training map fully fair | comm-range is no longer the only difference vs V14 → confounded; would require **retraining the V14 baseline** at the new density too |

**Recommendation: Option A.** The training env retries-until-solvable, so both
V14 and V14_8.0m train on the same solvable distribution; keeping the curriculum
identical preserves the clean causal comparison. The 0.27 ceiling governs
**evaluation fairness and reporting**, not this specific ablation's training.

---

## 4. Execution steps

1. **Pre-flight checks**
   - Confirm `models/apex_ultra_glide_v14_final.zip` and
     `models/vecnormalize_glide_v14_final.pkl` exist (warm-start source).
   - Confirm GPU/CPU availability; training uses `num_cpu = 10` workers.
2. **Run training** — `python train_step_B10_extended_v14_8_0m.py`
   - 5M fine-tune steps (2M @ 0.30, then 3M @ 0.35); checkpoints every 500k.
   - Outputs: `apex_ultra_glide_v14_8_0m_mid_0.3.zip`, `..._mid_0.35.zip`,
     `apex_ultra_glide_v14_8_0m_final.zip`, `vecnormalize_glide_v14_8_0m_final.pkl`.
3. **Run evaluation** — `python evaluate_v14_8_0m_densities.py`
   - Sweeps `[0.10,0.15,0.20,0.25,0.30]`, 200 maps each (per-drone success).
   - Output: `v10_IEEE_Final/results/v14_sweep/v14_8_0m_density_sweep_metrics.csv` + plots.
4. **Head-to-head comparison**
   - Compare against the V14 baseline sweep (already done):
     0.10→99.26%, 0.15→98.81%, 0.20→97.10%, 0.25→95.92%, 0.30→93.62%.
   - Report per-density delta (V14 − V14_8.0m) = performance cost of limited comms.
5. **Statistical rigor**
   - Report Wilson 95% CIs (n≈2000 per density), as in `FINAL_PARAMETER.md`.
   - A delta is meaningful only if the two CIs do not overlap.

---

## 5. Reporting / fairness integration

- For every evaluated density, report the **raw solvability** beside agent success
  (from `FINAL_PARAMETER.md` §3), e.g. "0.30: 93.6% success **on the 89.65%
  solvable subset**." This prevents over-claiming.
- Headline comparison should highlight the **fair densities (≤0.27)** — especially
  0.25 — where ≥95% of maps are genuinely solvable.

---

## 6. Risks & open items

- **Confound risk:** do NOT change hyperparameters or curriculum unless also
  re-running the V14 baseline identically.
- **Warm-start mismatch:** verify the VecNormalize stats are loaded/handled
  consistently between baseline and treatment.
- **Comm-range masking correctness:** confirm L423 masking applies to the global
  critic observation as intended (CTDE) and matches the study's claim.
- **Untested:** the 8.0 m value itself is a design choice; a small sweep of
  comm ranges (e.g. 4/6/8/10 m) would strengthen the causal story but is optional.

---

## 7. Deliverables

1. Trained `apex_ultra_glide_v14_8_0m_final.zip` (+ checkpoints).
2. `v14_8_0m_density_sweep_metrics.csv` + comparison plots.
3. V14 vs V14_8.0m delta table with Wilson CIs.
4. A short results write-up tying the performance cost to the CTDE audit finding.
