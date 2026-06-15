# Phase C — Critical Design Refinements

**Date:** 2026-06-15
**Status:** IMPORTANT — fold these into the implementation. Companion to `PHASE_C_TRUST_DESIGN.md`.
**Source:** three refinements raised during design review. All three are validated below and made
implementation-ready, with honest caveats and trade-offs added.

These fix three real failure modes:
1. **Noisy velocity estimate → false positives** (env design)
2. **Dormant trust-slot weights stay ignored after transfer** (training)
3. **honest_success alone doesn't prove the detector works** (evaluation)

---

## Refinement 1 — Filter the velocity estimate (env design)

### The issue
Trust update uses the inferred neighbor velocity:
```
v_raw(t) = (sensed_pos_j(t) - sensed_pos_j(t-1)) / dt
```
Raw finite-difference of sensed positions is **noisy** (sensor jitter, temporary occlusion). Noise
inflates the velocity discrepancy → honest drones get **falsely flagged** as traitors (false positives).

### The change — EMA / low-pass filter
Smooth the sensed velocity before computing discrepancy:
```
v_hat(t) = beta * v_hat(t-1) + (1 - beta) * v_raw(t)        # EMA, beta in [0,1]
vel_disc = || claimed_vel_j - v_hat(t) || / D_v             # use v_hat, NOT v_raw
```
- `beta` ~ **0.7–0.9** (higher = smoother).
- Optionally smooth the **position** too before differencing (double low-pass), but usually EMA on velocity suffices.

### Engineering notes / caveats (important)
- **Filter the SENSED side only.** `claimed_vel_j` is the *broadcast* (what the traitor says) — do NOT
  filter it; the whole point is to compare the (smoothed) truth against the raw claim.
- **Lag vs noise trade-off:** higher `beta` reduces false positives but adds **lag** → a traitor that
  suddenly starts lying is detected **slower** (worse Time-to-Detect). Tune `beta` against TTD (Refinement 3).
- **Current-sim nuance:** in the present noiseless sim, `sensed_pos_j` = the *true* position, so `v_raw`
  is already exact and EMA changes little. **The EMA becomes essential once we add realistic LiDAR noise /
  occlusion** — which we SHOULD, both for realism and so the trust mechanism is tested under non-ideal
  sensing. Recommendation: add a small Gaussian sensing noise (e.g., σ ≈ 2–5 cm on sensed position) AND
  the EMA together, so false-positive robustness is demonstrated, not assumed.
- **Where:** in the env's per-neighbor `sensed_pos_hist` / velocity-estimate step (Section 3.2 of the
  trust spec), keep a per-(i,j) `v_hat` state alongside `sensed_pos_hist`.

---

## Refinement 2 — Trust auxiliary loss (training)

### The issue
In Phase B the 4th sync slot was always `0.0`, so the first-layer weights feeding it received **zero
gradient and are effectively dead**. After transfer to Phase C, an RL policy can sit in a **local
minimum where it keeps ignoring the now-active trust slot** — the trust signal exists but the policy
never learns to use it.

### The change — auxiliary regression head that reconstructs trust
Add a small auxiliary task that forces the **shared hidden features** to encode trust:
```
aux_head : shared_hidden_features  ->  predicted_trust (5 values, the closest-5 trust scores)
L_aux    = MSE( predicted_trust , actual_trust_values )
L_total  = L_PPO + lambda_aux * L_aux        # lambda_aux ~ 0.1 (tune)
```
This "wakes up" the representation: to minimize `L_aux`, the shared features must **carry trust**, which
the action head then has available.

### Engineering notes / caveats (important)
- **Attach the aux head to the SHARED HIDDEN layer, NOT the raw input.** If it reads the raw trust input
  it can learn an identity shortcut (copy input→output) without the features encoding anything. Reading
  hidden features forces the *representation* to hold trust.
- **It encourages, doesn't *guarantee*, that the action uses trust.** Aux loss shapes the representation;
  the action head still has to learn to act on it (RL does this once trust is informative under traitors).
- **Cheap complementary trick (recommended together):** before Phase C training, **re-initialize the dead
  first-layer weights** connected to the trust slot to small random values (they're frozen at stale values
  otherwise). Re-init + aux loss reliably revives the slot.
- **Implementation effort (SB3):** SB3 PPO has no native auxiliary-loss hook. You need:
  1. a **custom policy** whose forward also returns `predicted_trust` from the shared features,
  2. a **subclassed PPO** whose `train()` adds `lambda_aux * MSE(pred, actual)` to the loss.
  Moderate effort (~1 day). Keep `actual_trust_values` from the env (the table) as the regression target.
- **Schedule:** you can **decay `lambda_aux` to ~0** late in training (it's a warm-up to break the local
  minimum; once trust is used, the aux task isn't needed).

---

## Refinement 3 — Detection metrics (evaluation)

### The issue
`honest_success` shows the *outcome* but not whether the **detector itself works**. Two policies could
have the same success for different reasons; we need to show the trust mechanism actually identifies
traitors (and doesn't wrongly accuse honest drones).

### The change — track and plot detection quality
Using the ground-truth traitor labels (**for metrics ONLY — never as policy input**):

| Metric | Definition | Target |
|--------|------------|--------|
| **False Positive Rate (FPR)** | fraction of (honest i, honest neighbor j, step) with `trust[i][j] > tau` | **< 5%** |
| **Time-to-Detect (TTD)** | steps from when a traitor starts lying until `trust[i][traitor] > tau` (first crossing); report mean & median | low (a few steps) |
| **Detection Rate / TPR** | fraction of (honest i, traitor j, in-range step) with `trust[i][j] > tau` | high (e.g. >90%) |
| **Trust separation** | distribution / AUC of `trust` for honest vs traitor neighbors | clear gap |

### Engineering notes / additions
- **Add a qualitative plot:** `trust[i][traitor](t)` over one episode — should rise and cross `tau` shortly
  after lies start. This single figure is the most convincing "the detector fires" evidence for a paper.
- **TTD vs EMA `beta`:** TTD directly measures the lag introduced by Refinement 1 — use it to pick `beta`
  (lowest `beta` that keeps FPR < 5%).
- **FPR vs `tau` and `alpha_rise`:** sweep these; report the FPR/TPR trade-off (a small ROC-style curve).
- **CTDE guard:** the traitor labels used here are **evaluation ground truth for scoring only**. They must
  **never** enter the observation or the trust computation (which uses only comm-vs-LiDAR discrepancy).

---

## How the three integrate (one picture)

```
LiDAR sensed pos ──► EMA filter (R1) ──► v_hat ─┐
                                                ├─► discrepancy ─► trust update (fast-rise/slow-decay)
traitor broadcast (claimed pos/vel) ────────────┘                         │
                                                                          ▼
                                        persistent identity trust table ──► sync 4th slot ──► policy
                                                                          │
                          aux loss (R2) reconstructs trust from features ─┘   (wakes the slot)
                                                                          │
                          metrics (R3): FPR, TTD, TPR, trust(t) plot ─────┘   (proves it works)
```

- **R1** makes the trust signal *clean* (fewer false positives).
- **R2** makes the policy *use* the trust signal (no dormant-weight local minimum).
- **R3** *proves* the mechanism works (not just that success improved).

---

## Updated parameter list (additions to the trust spec)

| Param | Meaning | Start |
|-------|---------|-------|
| `beta` | EMA smoothing for sensed velocity | 0.8 |
| sensing noise σ | optional Gaussian noise on sensed position (realism) | 0.02–0.05 m |
| `lambda_aux` | weight of the trust-reconstruction auxiliary loss | 0.1 (decay late) |
| `tau` | trust threshold for FPR/TTD/TPR scoring | 0.2–0.3 |

---

## Implementation checklist (additions to Phase C)

- [ ] **R1:** per-(i,j) `v_hat` EMA state; use `v_hat` in `vel_disc`; (recommended) add sensing noise σ.
- [ ] **R2:** custom policy with aux trust-prediction head on shared features; subclassed PPO adding
      `lambda_aux*MSE`; re-init dead trust-slot weights before training; optional `lambda_aux` decay.
- [ ] **R3:** log per-step `trust[i][j]` with traitor labels; compute FPR / TTD / TPR; save a
      `trust(t)` trajectory for one traitor; (optional) FPR–TPR sweep over `tau`.

---

## Honest summary

All three refinements are **correct and worth implementing**:
- **R1 (EMA):** essential *once sensing noise is added* (and harmless now); watch the lag→TTD trade-off.
- **R2 (aux loss):** the right fix for the dormant-slot local minimum; pair it with dead-weight re-init;
  budget ~1 day for the SB3 custom-loss plumbing.
- **R3 (detection metrics):** mandatory for a credible paper — they prove the *mechanism*, not just the
  *outcome*. The `trust(t)` plot is the single best figure.

These move Phase C from "trust score exists" to "trust score is clean, actually used, and demonstrably
correct" — exactly what a reviewer checks.
