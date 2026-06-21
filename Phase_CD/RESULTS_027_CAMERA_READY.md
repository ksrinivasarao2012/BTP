# Camera-ready results ledger — density 0.27, 500 maps, stage-2 base, RANDOMIZED attack

**Setup (locked 2026-06-20).** Base model `models/noise_robust_ON_stage2_final.zip` (0.27 lock-in, 1.5M
steps, σ~U[0,0.6]). Density **0.27**. **500 maps/cond**, paired bootstrap 95% CIs (2000 resamples, seed
12345). Attack = **RANDOMIZED** (per-map n_phantom~U{3,4,5,6}, per-phantom radius from the real 42/40/18
obstacle mixture). Traitor sweep **f = 1, 2, 3**. Two attack modes: **wall** (easy) and **camouflage**
(stealthy). Driver: `Phase_CD/Noise_added/run_full_027_pipeline.{ps1,bat}`; raw logs in
`Phase_CD/Noise_added/results_027/eval_f{1,2,3}_{wall,camouflage}_500.txt`.

**Column legend.** `base` = clean ceiling (no attack, no defense). `attack/off` = attacked, NO defense (the
damage). `robust` = attacked + single-frame robust filter (k_sigma=4, alpha=0.25). `temporal` = attacked +
composed temporal filter (eps=0.6, min_k=20). `temp.nh` = NO attack, defense ON (proves no false-gating
harm → should ≈ base). `P/R` = detection precision/recall. `recovery` = defended − undefended(off), pp.
`no-harm` = temp.nh − base, pp (≈0 = safe).

> **What "winning" looks like:** (1) temporal ≥ robust at every σ; (2) the gap opens at high σ + camouflage
> (where single-frame recall collapses); (3) `no-harm` flat (CI touches 0) everywhere; (4) recovery CI does
> NOT touch 0 where we claim a win.

### Why `base` ≈ 86% (not 95%+) — read before interpreting any cell
`base` is clean of *attack* but **not** clean of *sensor failure*. Three deliberate stresses are stacked in:
1. **~33% sustained LiDAR dropout** (`lidar_dropout=0.10, dropout_sustain=5`) — every drone goes blind in
   bursts and must survive via comm-fusion. This is the *entire premise* of collaborative perception; with
   perfect sensing, sharing would be pointless. (The clean Phase-B M0 figures of 95.6%/91.1% had **no**
   dropout — a different, easier regime.)
2. **Density 0.27** (calibrated fairness ceiling) vs the 0.20 used for the §5.2 "53→94%" anchor.
3. **Noise-robustness-trained model** (stage2, σ-DR over [0,0.6]) — trades a little peak σ=0 performance for
   robustness across the whole noise range.
Together: clean-LiDAR+0.20+clean-model ≈ 94% (anchor) → 33%-dropout+0.27+noise-robust-model ≈ 86% (here).
It is the **same baseline for every condition**, so recovery / no-harm comparisons stay fair regardless of
the absolute ceiling. The σ=0.6 base of 53.4% is the **§5.10 navigation perception limit** (high-noise
navigation is genuinely information-starved), already disclosed.

**Reviewer Q — "why blind 33%? why not more? why blind at all?"**
- *Why blind at all:* partial observability is the norm in robotics (occlusion, range limits, reflective/
  absorptive surfaces, rain/dust, sensor faults). Dropout is what makes inter-agent sharing *load-bearing* —
  it is the motivation for the architecture, not a handicap we impose for fun.
- *Why ~33% specifically:* it is a **calibrated operating point**, not arbitrary — the regime where the comm
  contribution is maximally visible yet the map stays solvable. Too little dropout → comm is irrelevant
  (OFF≈ON, both high); too much → no drone has information to share (sender-gating: a blind drone shares
  nothing), so even comm can't help and the task becomes unsolvable. At 33%, OFF≈53% vs ON≈94% (§5.2) — the
  cleanest separation. Backed by the **dropout sweep** (`eval_dropout_sweep.py`, §5.2) showing the full curve;
  33% is a representative point on it, not a cherry-pick.
- *Why not more:* beyond ~33% the ON (comm) arm itself degrades because neighbours are blind too — the
  defense study would then be confounded by an unsolvable base. We deliberately sit in the
  "comm-is-load-bearing AND recoverable" band.

---

## f = 1 (1 traitor of 10)

### f=1 · WALL · 500 maps
| σ | base | off (attack) | robust (P/R) | temporal (P/R) | temp.nh | rob.rec | tmp.rec |
|---|---|---|---|---|---|---|---|
| 0.00 | 86.0 [83.8,88.2] | 81.4 [79.0,83.7] | 85.8 (1.00/0.98) | 86.0 (1.00/0.98) | 86.1 | +4.4 [3.0,5.8] | +4.5 [3.1,5.9] |
| 0.20 | 79.1 [76.3,81.8] | 73.8 [70.9,76.7] | 79.0 (0.98/0.90) | 78.7 (0.93/0.93) | 78.8 | +5.2 [3.6,6.7] | +4.9 [3.3,6.4] |
| 0.40 | 64.9 [61.6,68.2] | 61.3 [58.1,64.4] | 64.6 (0.92/0.57) | 64.2 (0.80/0.83) | 65.1 | +3.2 [1.6,4.9] | +2.9 [1.1,4.7] |
| 0.60 | 53.4 [49.8,56.6] | 47.6 [44.5,50.7] | 50.4 (0.88/0.27) | 53.4 (0.67/0.71) | 53.1 | +2.8 [1.1,4.6] | **+5.9 [4.2,7.7]** |

no-harm: +0.0 / −0.2 / +0.2 / −0.3 (all touch 0 → safe).

**Findings:**
- Mild attack at f=1 (damage −4.6 to −5.8 pp).
- σ ≤ 0.4: robust ≈ temporal (gaps inside CIs) — both fully neutralize a 1-traitor wall.
- **σ=0.6: robust recall collapses 0.27, recovers only +2.8; temporal holds recall 0.71, recovers +5.9 =
  FULL return to the 53.4 ceiling.** Temporal wins exactly where single-frame degrades.
- Detection recall trend: robust 0.98→0.90→0.57→**0.27**; temporal 0.98→0.93→0.83→**0.71**.
- no-harm flat everywhere.

### f=1 · CAMOUFLAGE · 500 maps  (the decisive mode)
| σ | base | off (attack) | robust (P/R) | temporal (P/R) | temp.nh | rob.rec | tmp.rec |
|---|---|---|---|---|---|---|---|
| 0.00 | 86.0 [83.8,88.2] | 74.4 [71.9,76.8] | 83.6 (1.00/0.97) | 83.6 (1.00/0.98) | 86.1 | +9.3 [7.3,11.3] | +9.2 [7.2,11.3] |
| 0.20 | 79.1 [76.2,81.8] | 69.0 [65.9,72.0] | 77.0 (0.98/0.89) | 77.4 (0.94/0.94) | 78.8 | +8.0 [6.3,9.9] | +8.4 [6.7,10.3] |
| 0.40 | 65.1 [61.7,68.3] | 55.7 [52.4,58.9] | 61.1 (0.93/0.44) | 63.4 (0.81/0.83) | 65.1 | +5.4 [3.4,7.6] | **+7.7 [5.6,9.8]** |
| 0.60 | 53.4 [49.8,56.6] | 44.4 [41.2,47.6] | 46.3 (0.84/0.13) | 51.6 (0.68/0.69) | 53.0 | **+1.9 [−0.1,3.9]** | **+7.1 [5.0,9.2]** |

no-harm: +0.0 / −0.2 / +0.1 / −0.4 (all touch 0 → safe).

**Findings (this is the strongest cell so far):**
- Camouflage hits ~2× harder than the wall even at f=1 (damage −9.0 to −11.6 pp).
- **σ=0.6 money shot: robust recovery +1.9 with CI [−0.1, +3.9] → TOUCHES ZERO (statistically no better
  than no defense). Temporal +7.1, CI [+5.0, +9.2] → solidly positive.** Temporal works exactly where robust
  dies. ← the headline sentence of the paper.
- Detection recall: robust 0.97→0.89→0.44→**0.13** (catches ~1 in 8 lies at σ=0.6); temporal
  0.98→0.94→0.83→**0.69** (holds).
- Temporal at σ=0.6 restores 44.4→51.6 (≈ ceiling 53.4 within overlapping CIs).
- Precision caveat: temporal 0.68 at σ=0.6, but no-harm flat → false flags cost ≈0 success.
- Trend vs wall: the stealthier the attack, the bigger temporal's advantage (robust +2.8 wall → +1.9 camo).

---

## f = 2 (2 traitors of 10)  ✅ DONE

### f=2 · WALL · 500 maps
| σ | base | off (attack) | robust (P/R) | temporal (P/R) | temp.nh | rob.rec | tmp.rec |
|---|---|---|---|---|---|---|---|
| 0.00 | 86.0 [83.8,88.2] | 71.8 [68.8,74.7] | 85.7 (1.00/0.98) | 85.7 (1.00/0.98) | 86.1 | +13.9 [11.6,16.3] | +13.9 [11.6,16.4] |
| 0.20 | 79.1 [76.2,81.8] | 64.5 [61.4,67.8] | 77.6 (0.99/0.90) | 78.6 (0.97/0.92) | 78.8 | +13.1 [10.6,15.7] | +14.1 [11.7,16.7] |
| 0.40 | 65.0 [61.6,68.2] | 54.8 [51.4,58.0] | 62.5 (0.96/0.57) | 63.9 (0.90/0.82) | 65.1 | +7.8 [5.3,10.3] | +9.2 [6.7,11.6] |
| 0.60 | 53.4 [49.8,56.6] | 43.5 [40.5,46.5] | 47.2 (0.94/0.26) | 53.2 (0.82/0.70) | 53.1 | +3.7 [1.7,5.7] | **+9.7 [7.5,11.9]** |

no-harm: +0.0 / −0.2 / +0.1 / −0.3 (all touch 0 → safe).
**σ=0.6:** temporal +9.7 (recall 0.70) vs robust +3.7 (recall 0.26) → temporal restores 43.5→53.2 ≈ ceiling.

### f=2 · CAMOUFLAGE · 500 maps
| σ | base | off (attack) | robust (P/R) | temporal (P/R) | temp.nh | rob.rec | tmp.rec |
|---|---|---|---|---|---|---|---|
| 0.00 | 86.0 [83.8,88.2] | 63.5 [60.6,66.6] | 83.9 (1.00/0.97) | 83.9 (1.00/0.97) | 86.1 | +20.3 [17.6,23.1] | +20.3 [17.6,23.1] |
| 0.20 | 79.1 [76.2,81.8] | 58.3 [55.1,61.6] | 76.0 (0.99/0.86) | 76.9 (0.97/0.94) | 78.8 | +17.8 [14.9,20.7] | +18.6 [16.0,21.5] |
| 0.40 | 64.9 [61.6,68.2] | 47.7 [44.5,50.8] | 58.8 (0.96/0.45) | 64.1 (0.91/0.81) | 65.1 | +11.1 [8.3,14.0] | **+16.4 [13.8,19.2]** |
| 0.60 | 53.4 [49.8,56.6] | 37.6 [34.6,40.6] | 41.0 (0.92/0.13) | 49.8 (0.82/0.69) | 53.0 | +3.4 [0.9,5.8] | **+12.2 [9.8,14.9]** |

no-harm: +0.0 / −0.2 / +0.2 / −0.4 (all touch 0 → safe).
**σ=0.6 (worst case):** temporal +12.2 (recall 0.69) vs robust +3.4 (recall 0.13, CI barely off 0) → temporal
restores 37.6→49.8 (≈ceiling within overlapping CIs). Strongest demonstration yet.

**Review note (f=2):** no anomalies. base & temp.nh identical to f=1 (correct — both are k=0). Attack damage
~2× f=1. Temporal ≥ robust in every cell; advantage widens with σ and with stealth (2.6× wall / 3.6× camo at
σ=0.6). The script's "NO-HARM-FAILS -> tune" is a FALSE ALARM: it triggers on precision<0.9 (0.82), but the
no-harm column (the direct harm measure) is ≈0 with CIs spanning zero → no tuning needed (precision caveat).

## f = 3 (3 traitors of 10)  ✅ DONE  (literature ceiling)

### f=3 · WALL · 500 maps
| σ | base | off (attack) | robust (P/R) | temporal (P/R) | temp.nh | rob.rec | tmp.rec |
|---|---|---|---|---|---|---|---|
| 0.00 | 86.0 [83.8,88.2] | 68.8 [65.5,71.9] | 85.3 (1.00/0.98) | 85.1 (1.00/0.98) | 86.1 | +16.5 [13.6,19.3] | +16.4 [13.5,19.2] |
| 0.20 | 79.1 [76.3,81.8] | 58.6 [55.5,61.9] | 78.5 (1.00/0.90) | 77.8 (0.98/0.93) | 78.8 | +19.9 [16.8,22.9] | +19.2 [16.3,22.3] |
| 0.40 | 64.9 [61.6,68.2] | 50.4 [47.1,53.8] | 62.3 (0.98/0.59) | 65.2 (0.94/0.82) | 65.1 | +11.9 [9.0,14.7] | +14.8 [12.1,17.8] |
| 0.60 | 53.2 [49.6,56.5] | 41.3 [38.3,44.5] | 45.9 (0.97/0.26) | 52.6 (0.89/0.72) | 53.0 | +4.5 [2.1,6.8] | **+11.3 [8.8,13.6]** |

no-harm: −0.2 / −0.2 / +0.2 / −0.2 (all touch 0 → safe).
**σ=0.6:** temporal +11.3 (recall 0.72) vs robust +4.5 (recall 0.26) → restores 41.3→52.6 ≈ ceiling.

### f=3 · CAMOUFLAGE · 500 maps
| σ | base | off (attack) | robust (P/R) | temporal (P/R) | temp.nh | rob.rec | tmp.rec |
|---|---|---|---|---|---|---|---|
| 0.00 | 86.0 [83.8,88.2] | 60.9 [57.9,64.1] | 83.2 (1.00/0.97) | 83.3 (1.00/0.97) | 86.0 | +22.4 [19.2,25.3] | +22.4 [19.2,25.3] |
| 0.20 | 79.1 [76.3,81.8] | 55.2 [51.8,58.5] | 75.6 (1.00/0.86) | 76.6 (0.98/0.95) | 78.8 | +20.4 [17.2,23.6] | +21.5 [18.3,24.6] |
| 0.40 | 65.0 [61.7,68.3] | 43.5 [40.5,46.8] | 55.3 (0.97/0.43) | 61.6 (0.95/0.81) | 65.1 | +11.7 [8.9,14.8] | **+18.1 [15.2,20.9]** |
| 0.60 | 53.3 [49.8,56.6] | 35.3 [32.3,38.3] | 40.5 (0.95/0.12) | 48.9 (0.89/0.68) | 53.0 | +5.3 [2.5,8.0] | **+13.6 [10.9,16.5]** |

no-harm: +0.0 / −0.2 / +0.2 / −0.3 (all touch 0 → safe).
**σ=0.6 (worst case):** temporal +13.6 (recall 0.68) vs robust +5.3 (recall 0.12) → restores 35.3→48.9.

**Review note (f=3):** no anomalies. (1) **Attack saturates** — f=2→f=3 adds only ~3pp damage vs the huge
f=1→f=2 jump (overlapping/redundant phantoms); f=3 (lit. ceiling) is not a runaway. (2) **Precision improves
with f** — σ=0.6 camo precision 0.68(f1)→0.82(f2)→**0.89**(f3): the defense is most precise when the threat
is worst (precision caveat shrinks). (3) Low-noise wall temporal ≤0.7pp below robust but CIs fully overlap
(tied) — same harmless pattern as f1/f2. NO-HARM-FAILS warning = false alarm (precision<0.9 trigger; real
no-harm ≈0).

---

## §5.2 Collaborative-perception anchor @ 0.27, 500 maps (zero-shot)  🔵 ON done / OFF running
**ON model** (`raster_slot_fusion_ON_stage2`, shared map ON):
- drone-level success **87.70%** · map-level (all 10 reach) **65.00%**
- vs the ON model's *own-LiDAR-only* eval: drone 42.90% / map 7.00% → **+58.0 pp map-level, CI [+53.6,+62.4]**.

**OFF model** (`raster_slot_fusion_OFF_stage2`, own-LiDAR only): ⏳ _to fill from anchor_OFF_500.txt_

→ Confirms comm is load-bearing at 0.27 under ~33% blindness (the §5.2 "comm ON ≫ comm OFF" anchor; the
0.20 version was 93.84% vs 53.08%; 0.27 is harder so slightly lower, as expected).

---

## Adaptive results captured so far (σ=0.6, camouflage)

### gap sweep (camouflage_gap) — recovery = temporal − off
**f=1:** gap0.0 off46.4 temp51.8(+5.4, P0.69/R0.70) · gap0.3 off44.2 temp50.1(+5.9, 0.70/0.70) ·
gap0.6 off43.6 temp51.1(+7.5, 0.70/0.70) · gap1.0 off44.8 temp51.9(+7.0, 0.69/0.72) ·
gap1.5 off45.6 temp51.2(+5.7, 0.70/0.74).
**f=2:** gap0.0 off42.4 temp50.8(+8.5, P0.83/R0.69) · gap0.3 off38.8 temp50.7(+11.9, 0.83/0.70) ·
gap0.6 off38.7 temp50.5(+11.8, 0.84/0.70) · gap1.0 off39.2 temp50.2(+11.0, 0.83/0.71) ·
gap1.5 off40.9 temp50.5(+9.6, 0.83/0.73). Bind holds: recovery positive across all gaps; recall steady ~0.70.

### jitter sweep (phantom_jitter)
**f=1:** j0.0 off44.3 temp50.1(+5.8, R0.70) · j0.3 off44.6 temp50.8(+6.2, 0.69) · j0.6 off46.2 temp51.1(+5.0,
0.66) · j1.0 off47.8 temp51.1(+3.3, 0.61).
**f=2:** j0.0 off38.8 temp50.7(+11.9, R0.70) · j0.3 off39.9 temp49.6(+9.7, 0.68) · j0.6 off42.1 temp50.4(+8.3,
0.66) · j1.0 off45.6 temp50.2(+4.6, 0.61).
Reading: jitter *reduces the attack's own harm* (off rises 38.8→45.6) faster than it dents recovery —
zero-mean jitter doesn't beat the mean test; recall only sags mildly (0.70→0.61). No free lunch.

> ⚠️ **LOST to a bad UTF-16 converter (2026-06-20), must RE-RUN:** offset f2, offset f3, gap f3, jitter f3,
> duty f3. (offset f1, anchor_ON, all temporal f1/f2/f3 survive as numbers in this file from console pastes;
> gap f1/f2 + jitter f1/f2 captured above; duty f1/f2 were still running.)

## Adaptive / filter-aware attacker  ⏳ PENDING (separate, fixed-radius, f=1,2,3 per decision)
- **offset** (stealth/harm bind — THE reviewer-rebuttal figure)
- **gap** (surface-gap robustness)
- **jitter** (zero-mean jitter doesn't beat the mean test)
- **duty** (intermittent lying only dilutes)
> Decision 2026-06-20: run all four at f=1,2,3 (Option 2, full symmetry) = 12 runs.
> Driver: `Phase_CD\Noise_added\run_adaptive_027_pipeline.{ps1,bat}` → `results_027\adaptive_{sweep}_f{f}_500.txt`.

---

# MASTER CHECKLIST — every camera-ready test (so nothing is forgotten)

| # | group | run(s) | maps | needs train? | status |
|---|---|---|---|---|---|
| 1 | **Temporal defense (headline)** | `eval_temporal.py` f=1,2,3 × {wall,camo} | 500 | ❌ (stage2 done) | ✅✅✅✅✅✅ DONE (pipeline 14h41m) |
| 2 | **Collab anchor §5.2 @0.27** | bundle `run_extras_027_pipeline` (ON+OFF zero-shot) | 500 | ❌ zero-shot | ⏳ |
| 3 | **Dropout sweep @0.27** ("why 33%") | bundle `run_extras_027_pipeline` | 500 | ❌ zero-shot | ⏳ |
| 4 | **Naive-filter-breaks §5.6 @0.27** | bundle `run_extras_027_pipeline` | 500 | ❌ | ⏳ |
| 5 | **Adaptive attacker** (fixed-radius) | bundle `run_adaptive_027_pipeline` (offset/gap/jitter/duty × f=1,2,3 = 12) | 500 | ❌ | ⏳ |

**Bundle drivers (cmd):** `Phase_CD\Noise_added\run_extras_027_pipeline.bat` (groups 2+3+4, ~quick) ·
`Phase_CD\Noise_added\run_adaptive_027_pipeline.bat` (group 5, the long one).
| 6 | (optional) **probe evidence** | `probe_temporal_offset.py <stage2> 500 2 10 camouflage 0.6` (+`--assoc realistic`) | 500 | ❌ | optional |

**Run count:** 6 (temporal) + 2 (anchor) + 1 (dropout) + 1 (naive) + 12 (adaptive) = **22 runs** (+optional probe).
**Training:** all done (stage2). Everything left is evaluation only.

**Integration tasks (after numbers land):**
- [ ] Fill f=2/f=3 tables + adaptive/anchor/dropout/naive sections in THIS file.
- [ ] Replace PAPER_MASTER_PLAN §5.11 dev cells (150/0.25/stage1/fixed) with camera-ready (500/0.27/stage2/random).
- [ ] Update CLAUDE.md LATEST STATUS numbers.
- [ ] Update §5.2/§5.6 in PAPER_MASTER_PLAN to the 0.27 anchor + add dropout-sweep figure.

---

## Running headline (update as cells land)
- **f=1 wall:** temporal ≥ robust; full recovery at σ=0.6 (+5.9 vs robust +2.8); no-harm flat.
- **f=1 camouflage:** at σ=0.6 robust recovery touches zero (+1.9, CI [−0.1,3.9]) while temporal stays
  solidly positive (+7.1) — the cleanest demonstration of the thesis.
- **f=2 confirms the trend amplifies:** damage ~2× f=1; temporal advantage at σ=0.6 grows to 2.6× (wall) /
  3.6× (camo). camo σ=0.6: temporal +12.2 (recall 0.69) vs robust +3.4 (recall 0.13). no-harm flat.
- **f=3 (lit. ceiling) — temporal headline COMPLETE.** Holds at f=3; attack saturates (f=2→f=3 only +3pp
  damage) and precision climbs to 0.89. No anomalies across all 6 cells.

### THE headline table for the paper — σ=0.6 CAMOUFLAGE recovery across f (the worst case)
| f (traitors) | undefended | robust rec (recall) | **temporal rec (recall)** | temporal × robust | no-harm |
|---|---|---|---|---|---|
| 1 | 44.4 | +1.9 (0.13) | **+7.1 (0.69)** | 3.7× | −0.4 |
| 2 | 37.6 | +3.4 (0.13) | **+12.2 (0.69)** | 3.6× | −0.4 |
| 3 | 35.3 | +5.3 (0.12) | **+13.6 (0.68)** | 2.6× | −0.3 |

→ Across the full literature-justified threat range (f=1..3), at the hardest noise (σ=0.6) and stealthiest
attack (camouflage), the single-frame robust filter catches ~1-in-8 lies and recovers little; the temporal
filter catches ~7-in-10 and recovers 7-14 pp — with zero measurable harm to honest drones. **This is the
paper's central result, now at 500 maps / density 0.27 / randomized attack with tight CIs.**
