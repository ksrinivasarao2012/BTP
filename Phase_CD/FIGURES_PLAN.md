# FIGURES PLAN — RAS manuscript

Every figure the paper needs, with its message, data source, plot type, and priority. Generate as **vector
PDF** into `Phase_CD/manuscript/figures/`, one matplotlib script per figure (reproducible from the ledger).
When we actually build these, load the `dataviz` skill first for the color/mark system.

**Production rules (Elsevier / RAS):**
- Vector **PDF**, fonts embedded; single-column width ~8.4 cm, double-column ~17.4 cm.
- **Must be legible in grayscale** (RAS is printed) — distinguish series by *linestyle/marker/hatch*, not color alone.
- Colorblind-safe palette; font >=8 pt at final size; no chartjunk; captions self-contained.
- Cite every figure in text; number in order of appearance.

---

## Summary

| # | figure | supports | data source | type | priority |
|---|--------|----------|-------------|------|----------|
| 1 | System/threat schematic | sec 3 Methods | (hand-drawn) | diagram | 🔴 essential |
| 2 | Comm anchor / dropout curve | sec 5.1 | `dropout_sweep_500.txt` | grouped bars or line | 🔴 essential |
| 3 | Naive filter collapse under noise | sec 5.3 | `naive_sweep_500.txt` | 2-panel line | 🔴 essential |
| 4 | Temporal vs robust: recall + recovery | sec 5.5 | `eval_f*_500.txt` + headline | 2-panel | 🔴 essential (the headline) |
| 5 | Offset-vector honest-vs-liar histogram | sec 5.5 | `probe_temporal_offset.py` | histogram | 🔴 essential (the mechanism) |
| 6 | Stealth/harm bind (offset) | sec 5.6 | `adaptive_offset_f2_500.txt` | twin-axis line | 🔴 essential (rebuttal) |
| 7 | Comm-loss robustness (R3) | sec 5.6 / discussion | `comm_loss_camouflage_500_k2.txt` | line vs p | 🟠 strong (rebuttal) |
| 8 | Density generalization (R7) | sec 5.7 / discussion | `density_sweep_camouflage_500_k2.txt` | line/bars vs density | 🟡 nice-to-have (may stay a table) |

Target: **6 essential + 1 strong** figures. Fig 8 can be a table if space is tight.

---

## Fig 1 — System and threat schematic  [hand-drawn, not data]
**Message:** in one glance: 10 drones, LiDAR sensing radius, comm radius (larger), a neighbour broadcasting
sensed obstacles, MIN-fusion into the ego LiDAR channel, a Byzantine drone injecting a phantom, and the trust
filter gating it.
**Content:** ego drone with 48-ray fan; one honest neighbour sharing a real obstacle; one traitor broadcasting
a phantom (dashed/red); a "trust gate" box on the fusion path. Inset: wall vs camouflage placement.
**Tooling:** draw in TikZ (inside LaTeX) or Inkscape -> PDF. No numbers.
**Why essential:** readers cannot follow the attack/defense without seeing the fusion path. First figure.

## Fig 2 — Communication is load-bearing (anchor + dropout)
**Message:** comm advantage appears only once sensing degrades; it is large at the ~33% operating point.
**Plot:** x = dropout {0%, 10%(~33% blind), 20%(~50% blind)}; two series ON vs OFF drone-level success; error
bars = 95% CI. Grouped bars (clear in grayscale via hatching) OR two lines with markers.
**Data:** `results_027/dropout_sweep_500.txt` (ON 88.7/87.7/86.2; OFF 90.0/46.3/35.4).
**Note:** annotate the +41 pp gap at 33% (our operating point).

## Fig 3 — Naive consistency trust is destructive under noise
**Message:** the obvious defense inverts under noise — precision collapses and it harms honest swarms.
**Plot:** 2 panels sharing x = sigma {0,0.2,0.4,0.6}.
  (a) detection **precision** 1.00 -> 0.23 (line, markers).
  (b) **no-harm** (FP-harm) 0 -> -27.5 pp and **recovery** going negative (two lines).
**Data:** `results_027/naive_sweep_500.txt`.
**Why essential:** this is the motivating negative result; the visual "it goes below zero" is powerful.

## Fig 4 — Temporal vs robust: the main result  [HEADLINE]
**Message:** temporal matches robust everywhere and pulls ahead exactly at high-noise camouflage; advantage
grows with traitor count.
**Plot:** 2 panels.
  (a) detection **recall vs sigma** for camouflage, two lines: robust (collapses to 0.13) vs temporal (holds
      0.69) at sigma=0.6. Mark the 0.13 -> 0.69 jump.
  (b) **recovery bars across f=1,2,3** at sigma=0.6 camouflage: robust vs temporal side by side, 95% CI whiskers.
**Data:** `eval_f2_camouflage_500.txt` (panel a) + headline table f=1,2,3 (panel b).
**Why essential:** this is *the* result; it must be a figure, not only a table.

## Fig 5 — The mechanism: offset-vector distribution
**Message:** honest neighbours' aggregated offset clusters near zero (noise cancels); fabrications sit far
above the threshold — the classes separate.
**Plot:** overlaid histograms (or violin/KDE) of aggregated offset magnitude ||mean d|| for honest vs phantom
links at sigma=0.6, K>=20; vertical dashed line at eta=0.6 m (the threshold). Annotate AUC 0.99 (oracle) /
0.85-0.90 (realistic).
**Data:** `probe_temporal_offset.py` (needs a small mod to dump per-link ||mean|| values to CSV).
**Why essential:** shows *why* it works, not just *that* it works. Reviewers love a mechanism figure.

## Fig 6 — Stealth/harm bind (offset sweep)  [REBUTTAL]
**Message:** the adaptive attacker cannot be both stealthy and harmful — harm and detection recall rise together.
**Plot:** twin-y line, x = phantom centre-offset {0..2.5}. Left y = harm (pp), right y = detection recall.
Both curves rise together; shade the "stealthy+harmless" corner (offset 0) and "harmful+caught" corner (2.5).
**Data:** `results_027/adaptive_offset_f2_500.txt` (harm -0.8..+14.3; recall 0.03..0.70).
**Why essential:** pre-empts the "static attacker is a strawman" objection in one picture.

## Fig 7 — Temporal survives lossy communication (R3)  [REBUTTAL — after overnight run]
**Message:** the defense degrades *gracefully* under packet loss; recovery stays positive.
**Plot:** x = packet-loss p {0,0.1,0.2,0.3}; y = sigma=0.6 camouflage recovery (pp), with 95% CI band; optional
second line = detection recall vs p. Possibly a small multiples panel per noise level.
**Data:** `results_027/comm_loss_camouflage_500_k2.txt` (from the R3 run).
**Why strong:** directly answers the single most likely reviewer question (idealized comm). Only build after the
run lands and IF recovery indeed stays positive (if it collapses, we disclose honestly in text instead).

## Fig 8 — Density generalization (R7)  [optional — may stay a table]
**Message:** the result is not an artifact of density 0.27.
**Plot:** x = density {0.20,0.24,0.27,0.30}; y = recovery (pp) with CI; flat-ish positive line = generalizes.
**Data:** `results_027/density_sweep_camouflage_500_k2.txt`.
**Decision:** if it holds cleanly and space is tight, fold into a sentence + small table instead of a figure.

---

## Build order (when we generate them)
1. Figs 2,3,4,6 — straight from existing ledger `.txt` (no new runs). Do these first.
2. Fig 5 — needs a small dump hook in `probe_temporal_offset.py` (emit per-link ||mean|| to CSV), then plot.
3. Figs 7,8 — after the R3/R7 overnight run lands.
4. Fig 1 — schematic, do last (or in parallel; it is drawing, not data).

## Open questions for Srinivasa
- Fig 2: grouped bars vs lines — preference?
- Fig 8: figure or table?
- Any figure you want ADDED (e.g., an offset x noise heatmap, or a per-f detection-precision trend)?
