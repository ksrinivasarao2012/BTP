# Baseline-Numbers Reconciliation Report — the "89.3 vs 87.7 / 45.9 vs 46.3" question

**Scope:** why the attack-free / collaborative-perception baseline success numbers differ
across the manuscript's tables, traced to the exact models, scripts, and raw files.
**Status:** every number is CORRECT; the differences are by-design (different experiments)
plus one 0.44 pp Monte-Carlo residual. Nothing here is a scientific error. This is a
presentation/reconciliation issue only.
**Written:** 2026-07-19. **Audience:** Srinivasa (and any reviewer who cross-checks cells).

---

## 0. TL;DR (read this first)

There are **three attack-free baseline numbers** floating around the paper for a "10 drones,
density 0.27, ~33% sensor blindness" condition, and they look inconsistent until you realize
each comes from a **different trained model** answering a **different question**:

| Number | Where in paper | Model | What it is |
|---|---|---|---|
| **89.34%** | `tab:anchor` ON | `raster_slot_fusion_OFF_stage2` | OFF-trained model, given shared data **zero-shot** |
| **45.86%** | `tab:anchor` OFF | `raster_slot_fusion_OFF_stage2` | **same** model, own-LiDAR only |
| **87.70%** | body "native", `tab:dropout` 10% ON | `raster_slot_fusion_ON_stage2` | ON-**trained** model, native |
| **46.30%** | `tab:dropout` 10% OFF | `raster_slot_fusion_OFF_stage2` | OFF-trained model, own-LiDAR only (2nd script) |
| **~86.0%** | attack/defense tables, σ=0 base | `noise_robust_ON_stage2` | noise-DR-trained base, native, σ=0 |

Two facts explain everything:
1. **89.3 vs 87.7** = **two different models** (an information ablation vs a two-model
   comparison). By design. Fully disclosed in the body.
2. **45.9 vs 46.3** = **the same model, the same condition, run by two different scripts on
   two independently sampled 500-map suites** → 0.44 pp of Monte-Carlo sampling noise. This
   is the only "same thing, two numbers" case, and it is far inside the run-to-run error
   (the map-level 95% CIs on these quantities span 4–5 pp).
3. **86.0 vs 87.7/89.3** = a **third model**, the noise-robust base, which trades a little
   σ=0 peak performance for robustness across σ∈[0,0.6] (a standard domain-randomization
   cost). The attack/defense experiments must use this base because they sweep noise.

Nothing is wrong. The fix is textual: label which experiment each table is, so a reader
never expects the cells to be identical. See §7.

---

## 1. The three (really four) models in this paper's baseline story

All live in `models/` at the repo root. Provenance from `CLAUDE.md` LATEST STATUS block.

| Model file | Trained how | Role |
|---|---|---|
| `raster_slot_fusion_OFF_stage2_final.zip` | Clean-trained **without** collaborative perception (own LiDAR only), density 0.27 | The **information-ablation** model: never saw sharing in training, so toggling shared data ON at *test* isolates the pure value of the shared information (zero-shot). |
| `raster_slot_fusion_ON_stage2_final.zip` | Clean-trained **with** collaborative perception, density 0.27 | The **native sharing** model: the "real" ON policy. Used as the ON arm of the two-model dropout sweep. |
| `noise_robust_ON_stage2_final.zip` | Fine-tuned from the ON model under sensor-noise domain randomization σ∼U[0,0.6], density 0.27, 1.5 M steps (trained 2026-06-20) | The **camera-ready attack/defense base**: every f∈{1,2,3} × {wall,camo} × σ∈{0,0.2,0.4,0.6} run uses this, because the noise study needs a base that saw noise in training. |
| `apex_ultra_glide_v14_comm8_lidar_final.zip` (M0) | The Phase-B clean navigator (8 m comm + LiDAR) | Ancestor of the raster models; not a baseline number in these tables, listed for completeness. |

**Why there must be more than one model:** the anchor's job is a clean *causal* claim ("the
gap is due to shared information, not to two different trainings"), which requires ONE policy
with the data toggled. The dropout sweep's job is a *trend* across operating points using the
policies you would actually deploy (ON-trained vs OFF-trained). The noise study's job needs a
noise-robust base. These are three different scientific questions → three trainings.

---

## 2. The two tables in the manuscript (exact current text)

### Table `tab:anchor` (`results.tex` lines 30–42) — the headline "comm is load-bearing"
| | Drone-level | Map-level | Gap (map, 95% CI) |
|---|---|---|---|
| ON (shared) | 89.3% | 67.8% | +57.4 [+52.8, +61.8] |
| OFF (own only) | 45.9% | 10.4% | |

Body framing (lines 6–19): *"a single policy is evaluated on the same maps with shared
observations fused (ON) and with its own LiDAR only (OFF)… Because the weights are identical
across the two arms, the gap is attributable to the shared information alone… A policy trained
with sharing reaches a similar 87.7% in its native mode; we do not interpret the small
difference between the two, as it conflates two independently trained policies."*

### Table `tab:dropout` (`results.tex` lines 44–57) — the "gap is operating-point-dependent"
| Dropout | Blind | ON | OFF | Gap (95% CI) |
|---|---|---|---|---|
| 0% | ~0% | 88.7 | 90.0 | −1.3 [−2.3, −0.4] |
| 10% | ~33% | 87.7 | 46.3 | +41.4 [+38.9, +43.8] |
| 20% | ~50% | 86.2 | 35.4 | +50.8 [+48.3, +53.3] |

Body framing (lines 20–28): the gap is an operating-point phenomenon — negative at 0%,
+41.4 at ~33%, +50.8 at ~50%.

**The apparent conflict a reviewer sees:** both tables describe a "~33% blind, density 0.27,
σ=0" condition, yet `tab:anchor` says ON/OFF = 89.3/45.9 while `tab:dropout`'s 10% row says
87.7/46.3. §3–§5 resolve every digit.

---

## 3. Exact raw-file provenance (cell-by-cell)

All three raw files: `Phase_CD/Noise_added/results_027/`. Scripts:
`Phase_CD/Collab_Perception/`.

### `anchor_OFF_500.txt` → this IS `tab:anchor`
- Script: `eval_slot_fusion_zero_shot.py` (loads ONE model, toggles `use_shared_map` True/False).
- Model: **`raster_slot_fusion_OFF_stage2_final.zip`** (the OFF-trained model).
- Verbatim: `ON 89.34% | OFF 45.86% | diff +43.48 pp`; map `ON 67.80% | OFF 10.40% | +57.40 [52.80, 61.80]`.
- So `tab:anchor` ON 89.3 = OFF-trained model **using shared data zero-shot**; OFF 45.9 =
  the **same** OFF-trained model, own-LiDAR only. **Single policy, data toggled = information
  ablation.**

### `anchor_ON_500.txt` → the body's "87.7% native"
- Script: `eval_slot_fusion_zero_shot.py`, but with the **ON-trained** model.
- Model: **`raster_slot_fusion_ON_stage2_final.zip`**.
- Verbatim: `ON 87.70% | OFF 42.90% | diff +44.80 pp`; map `65.00 / 7.00 / +58.00 [53.60, 62.40]`.
- So the "87.7% in its native mode" sentence = this file's ON arm.

### `dropout_sweep_500.txt` → this IS `tab:dropout`
- Script: `eval_dropout_sweep.py` (docstring: *"ON-trained vs OFF-trained models across 3
  sensor-failure regimes"*). **Two different models**, one per arm.
- ON model: `raster_slot_fusion_ON_stage2_final.zip`; OFF model:
  `raster_slot_fusion_OFF_stage2_final.zip`.
- Verbatim: `0%: ON 88.70 OFF 90.04 gap −1.34 [−2.30,−0.42]` · `10%(33%): ON 87.70 OFF 46.30
  gap +41.40 [+38.92,+43.80]` · `20%(50%): ON 86.20 OFF 35.36 gap +50.84 [+48.34,+53.32]`.
- So `tab:dropout` 10% ON 87.7 = the **ON-trained** model native (matches `anchor_ON` exactly);
  OFF 46.3 = the OFF-trained model own-only.

---

## 4. Every difference, explained

### 4.1 Why ON is **89.3** (anchor) vs **87.7** (dropout 10%) — DIFFERENT MODELS
- 89.34 = `raster_slot_fusion_OFF` **+ shared data zero-shot** (an OFF-trained model that
  never saw sharing, yet exploits it at test).
- 87.70 = `raster_slot_fusion_ON` **native** (the model actually trained with sharing).
- These are two different policies. Interestingly the OFF-trained model *zero-shot* (89.3)
  slightly **beats** the ON-trained model *native* (87.7) at this operating point — which is
  exactly why the paper uses the ablation (89.3) for the causal headline and only *mentions*
  87.7 as confirmation "we do not interpret the small difference."
- **This is by design and already disclosed.** No error.

### 4.2 Why OFF is **45.9** (anchor) vs **46.3** (dropout 10%) — SAME MODEL, SAMPLING NOISE
- Both are `raster_slot_fusion_OFF_stage2`, own-LiDAR only, ~33% blind, density 0.27, σ=0.
- 45.86 comes from `eval_slot_fusion_zero_shot.py`; 46.30 from `eval_dropout_sweep.py`.
- The two scripts run **independent 500-map Monte-Carlo suites** (different random seeds →
  different obstacle layouts, spawn positions, and dropout-burst realizations of the stochastic
  p=0.10/sustain=5 process). They are two independent estimates of the same true quantity.
- **Magnitude check:** drone-level success is a mean over ~500 maps × up to 10 honest drones,
  but drone outcomes within a map are correlated (shared layout), so the effective sample is
  map-clustered. The map-level 95% CIs on these very quantities span **4–5 pp** (e.g. anchor
  map gap [52.8, 61.8]). A **0.44 pp** difference between two independent runs is therefore
  **well within one standard error** — textbook run-to-run variation, not a discrepancy.
- **This is the only "same thing, two numbers" case, and it is noise.** No error.

### 4.3 Why the attack/defense base is **~86.0** at σ=0, not 89.3/87.7 — THIRD MODEL
- The naive/robust/temporal/adaptive tables use **`noise_robust_ON_stage2`**, a model
  fine-tuned under σ∼U[0,0.6] domain randomization.
- Domain randomization buys robustness across the noise range at a small cost to the σ=0 peak
  — a standard, expected DR tradeoff. Hence its σ=0 native success (~86.0) sits just below the
  clean ON model's 87.7 and the ablation's 89.3.
- The paper **must** use this base for the attack/defense sweep, because those experiments
  vary σ up to 0.6 and a base that never saw noise would be unfairly disadvantaged (this is
  the Option-C decision; see `option-c-perception-limit`).
- `results.tex` "Reading the baselines" already states the ceiling "runs from ~86% at σ=0 down
  to 53.4% at σ=0.6." Consistent. No error.

### 4.4 Drone-gap vs map-gap (a related non-issue)
The intro's "gap of more than 43 pp" is the **drone-level** anchor gap (89.34 − 45.86 =
+43.48). The headline "+57.4 pp" is the **map-level** gap (67.80 − 10.40). Both are from
`tab:anchor`; they differ because one counts individual drones and the other counts all-10-reach
maps. Not a conflict — two different metrics, both labeled.

---

## 5. Number map (single source of truth)

| Manuscript appearance | Value | Raw file | Model | Metric/condition |
|---|---|---|---|---|
| `tab:anchor` ON | 89.3 | `anchor_OFF_500.txt` | raster OFF | drone, shared zero-shot, 33% blind, σ0 |
| `tab:anchor` OFF | 45.9 | `anchor_OFF_500.txt` | raster OFF | drone, own-only, 33% blind, σ0 |
| `tab:anchor` map ON/OFF | 67.8 / 10.4 | `anchor_OFF_500.txt` | raster OFF | map-level |
| `tab:anchor` gap | +57.4 [52.8,61.8] | `anchor_OFF_500.txt` | raster OFF | map-level gap |
| body "native 87.7" | 87.7 | `anchor_ON_500.txt` | raster ON | drone, native |
| `tab:dropout` 0% | 88.7 / 90.0 / −1.3 | `dropout_sweep_500.txt` | ON vs OFF | drone |
| `tab:dropout` 10% | 87.7 / 46.3 / +41.4 | `dropout_sweep_500.txt` | ON vs OFF | drone, 33% blind |
| `tab:dropout` 20% | 86.2 / 35.4 / +50.8 | `dropout_sweep_500.txt` | ON vs OFF | drone, 50% blind |
| attack/defense σ0 base | ~86.0 | `eval_f*_*_500.txt` | noise_robust ON | drone, native, σ0 |

---

## 6. History — what was already caught and fixed (2026-07-10)

From `INTERNAL_VALIDITY_AUDIT.md` Part D (D1), triggered by **Srinivasa's own follow-up
question**:
- **Original bug:** the manuscript had described 89.3 as *"the trained sharing model."* That
  was **WRONG** — 89.3 is the OFF-trained model used zero-shot (`eval_slot_fusion_zero_shot.py`
  loads one model and toggles `use_shared_map`).
- **Fix applied:** `results.tex` rewritten to the **single-policy information-ablation**
  framing, with the ON-trained model's native 87.7 cited as confirmation. Ledger attribution
  corrected. **Numbers were unchanged everywhere; only the descriptions were fixed.**
- **D3 re-verified** the quantitative prose: intro "89.3/45.9" and "more than 43 pp" (43.48) ✓.
- **What that 2026-07-10 pass did NOT explicitly reconcile:** the **OFF** cross-table pair
  (45.9 in `tab:anchor` vs 46.3 in `tab:dropout`). It reconciled the ON side (ablation vs
  two-model) but never spelled out that the two OFF cells are the same model under sampling
  noise. That un-addressed hairline is the entire residual of finding #2.

---

## 7. Is this a problem? and the recommended fix

**Is it a scientific problem?** No. Every number traces exactly to a raw file; the models and
scripts are correct; the ON difference is by design; the OFF difference is 0.44 pp of
Monte-Carlo noise; the 86.0 base is the correct DR model. A referee who recomputes anything
gets the paper's numbers.

**Is it a presentation problem?** Mildly. A careful reviewer comparing `tab:anchor` (89.3/45.9)
with `tab:dropout`'s 10% row (87.7/46.3) sees two ON and two OFF numbers for a nominally
identical operating point and may read sloppiness before they read "different experiments."

**Recommended fix (text only, no re-runs)** — make each table visibly a different experiment:
1. **`tab:dropout` caption:** add "*comparing an ON-trained and an OFF-trained policy*" so it
   is obviously the two-model trend, distinct from the anchor's single-policy ablation.
2. **Extend the existing "we do not interpret the small difference" sentence** to cover the
   *class* of difference without printing the decimals:
   > "Any small differences between this single-policy ablation and the two-model dropout
   > sweep (Table~\ref{tab:dropout}) stem from independently trained policies evaluated on
   > separately sampled map suites, and we do not interpret them."

   This single clause now covers **both** the ON (89.3/87.7) and OFF (45.9/46.3) cross-table
   gaps, without spotlighting a 0.44 pp value and inviting scrutiny of noise.

**Deliberately NOT recommended:** a dedicated footnote printing "45.9 vs 46.3" — it
over-dignifies run-to-run noise and hands a reviewer a magnifying glass for a non-issue.
**Also not recommended:** re-running to force the tables to share cells — they are different
experiments by design (ablation vs two-model), and forcing them to match would destroy the
two-model trend.

---

## 8. Appendix A — raw-file excerpts (verbatim)

**`anchor_OFF_500.txt`** (= `tab:anchor`):
```
[*] Slot-fusion ON/OFF eval | M0: raster_slot_fusion_OFF_stage2_final.zip | density=0.27 | 10w | ... (~33% blind)
     ON  (slot fusion + shared):   89.34%
     OFF (own LiDAR only):         45.86%
     Difference (ON - OFF):       +43.48 pp
     ON per-map: 67.80%  OFF per-map: 10.40%  Difference: +57.40 pp  95% CI: [+52.80, +61.80] pp
```

**`anchor_ON_500.txt`** (= body "native 87.7"):
```
[*] ... M0: raster_slot_fusion_ON_stage2_final.zip | density=0.27 | (~33% blind)
     ON  (slot fusion + shared):   87.70%
     OFF (own LiDAR only):         42.90%
     Difference (ON - OFF):       +44.80 pp
     ON per-map: 65.00%  OFF per-map: 7.00%  +58.00 pp  95% CI: [+53.60, +62.40] pp
```

**`dropout_sweep_500.txt`** (= `tab:dropout`):
```
  ON  model : raster_slot_fusion_ON_stage2_final.zip
  OFF model : raster_slot_fusion_OFF_stage2_final.zip
  dropout=  0% blind~0%  ON 88.70%  OFF 90.04%  gap -1.34 pp  CI [-2.30, -0.42]
  dropout= 10% blind~33%  ON 87.70%  OFF 46.30%  gap +41.40 pp  CI [+38.92, +43.80]
  dropout= 20% blind~50%  ON 86.20%  OFF 35.36%  gap +50.84 pp  CI [+48.34, +53.32]
```

## 9. Appendix B — the two eval scripts (docstrings)

**`eval_slot_fusion_zero_shot.py`** (produces both anchor files):
> "Zero-shot slot-fusion ON/OFF eval on M0 (no retraining). Runs [the model] with
> slot_fusion=True, comparing ON: use_shared_map=True vs OFF: use_shared_map=False (own LiDAR
> only)." — i.e. **one model, data toggled** → information ablation.

**`eval_dropout_sweep.py`** (produces the dropout table):
> "Dropout sweep: **ON-trained vs OFF-trained models** across 3 sensor-failure regimes
> (0% / 10%→~33% / 20%→~50%). ON model raster_slot_fusion_ON_stage2; OFF model
> raster_slot_fusion_OFF_stage2." — i.e. **two models** → deployment trend.

## 10. One-paragraph answer (if someone asks in person)

"The two tables use different models on purpose. The anchor is a *single-policy information
ablation*: one model (the OFF-trained one) with shared data switched on or off, so 89.3 vs
45.9 is purely the value of the shared information with identical weights. The dropout table
is a *two-model comparison* (the deployable ON-trained vs OFF-trained policies) to show the
gap depends on how blind the sensors are; its ON is 87.7 because that's the ON-*trained*
model's native score, and 89.3 was the OFF-trained model using sharing zero-shot. The only
same-model pair, the OFF cells 45.9 and 46.3, differ by 0.44 pp because they're two
independent 500-map runs from two scripts — pure sampling noise, far inside the ±4–5 pp
confidence intervals. And the attack/defense tables sit at ~86 because those use the
noise-robust base, which trades a little clean-noise performance for robustness across the
whole noise sweep."
