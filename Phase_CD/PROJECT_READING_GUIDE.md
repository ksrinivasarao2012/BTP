# PROJECT READING GUIDE — read in THIS order to understand the whole research

A study path from zero to full understanding: the story first, then env code, then training, then
evaluation, then results. Each item says WHAT the file is, WHY it exists, and WHAT to take from it.
Depth key: 🔴 know cold (whiteboard) · 🟡 know well · 🟢 conceptual · ⚪ skim/reference.

> Golden rule while reading any env file: ask **"what does this class ADD over its parent?"** The envs
> form an inheritance chain that mirrors the paper's 5 ideas.

> **Revision 2026-08-09 — corrections pass.** Every file path, class name and parameter value below
> was re-checked against the code. Nothing was deleted; corrections are added in place and marked ⚠️.
> What changed: the **inheritance chain was wrong at two links** (Stage 1 header); "48-ray" is
> **192 rays → 48 dimensions**; "8 m comm" is **10 m**; the 42/40/18 radius mixture is a measured
> outcome, not the sampling rule; `setup.tex` and the evidence-dossier system were missing entirely;
> and a new **Known Documentation Defects** list at the end flags numbers that are still under
> repair. If you read an earlier copy of this guide, re-read Stage 1 and the defect list.

---

## STAGE 0 — The story before any code (~1 hr) 🔴
Read these so every code file later has a place to slot into.
1. **`Phase_CD/manuscript/sections/abstract.tex`** — the whole paper in ~240 words.
2. **`Phase_CD/manuscript/sections/introduction.tex`** — the 5 ideas + 5 contributions, in prose.
3. **`CLAUDE.md`** (top "LATEST STATUS" block only) — the story arc + what every model/file is.
4. **`Phase_CD/PAPER_MASTER_PLAN.md` §5** — the results ledger narrative (skim; you'll return to it).

The 5 ideas (your mental map for everything below):
`(1) sharing helps → (2) traitors can poison sharing → (3) naive checking backfires under noise →
(4) temporal offset-bias filter fixes it → (5) adaptive attacker can't win (stealth/harm bind)`

---

## STAGE 1 — The environment chain (~1 day) — the heart of the system
Read the env files IN THIS ORDER. Each adds one layer.

> ⚠️ **READ THIS FIRST — the authoritative inheritance chain (verified from the `import`/`class`
> lines, 2026-08-09).** Every camera-ready number comes from `NoisyByzantineEnv`, whose ancestry is:
>
> ```
> Phase_CD/swarm_env_phasecd.py            SwarmLidarEnv_StepB10_8_0m   <- THE base the paper runs
>   -> Collab_Perception/env_collab_perception.py   CollabPerceptionEnv  <- Idea 1 lives HERE
>     -> Collab_Perception/env_byzantine_trust.py     ByzantineTrustEnv
>       -> Collab_Perception/env_byzantine_adaptive.py  AdaptiveByzantineEnv
>         -> Noise_added/env_noisy_byzantine.py           NoisyByzantineEnv
> ```
>
> **Two files below are NOT links in this chain, and both are kept deliberately:**
> - **§1.1 `swarm_env_step_B10_8_0m.py` (repo root)** — the ANCESTOR that `swarm_env_phasecd.py`
>   was copied from. Read it for the physics/sensing/reward substrate and the Dijkstra heading.
>   It has **no `lidar_range` parameter**, so the "8 m LiDAR" of this project only exists in the
>   phasecd copy. CLAUDE.md: *"Pristine/committed — do not add experimental hooks here."*
> - **§1.2 `swarm_env_raster.py`** — a **SIBLING** of `CollabPerceptionEnv` (both inherit
>   `SwarmLidarEnv_StepB10_8_0m` directly). It is the raster/slot-fusion lineage used to TRAIN the
>   collaborative-perception models (§2.2), not the branch the Byzantine evals run.
>   ⚠️ **Trap:** it defines `_sample_dropout` / `_cast48` / `_fused_lidar` (`:100/:118/:141`) with
>   the SAME names as the real chain link (`env_collab_perception.py:56/:74/:97`). You will find
>   every function this guide names and still be in the wrong branch. Check the `class` line.
 
### 1.1 `swarm_env_step_B10_8_0m.py` (repo root) 🟢 — the BASE world
- **What:** the Phase-C/D navigation env — 20x20 m, 10 drones, 48-ray LiDAR (8 m), 8 m gated comm,
  1200-step episodes, continuous velocity actions.
- **Why it exists:** this is the physics + sensing + comm substrate everything else inherits.
- **Take away:** how a drone senses (48-ray cast), how comm range gates neighbours, and the **Dijkstra
  routed-heading at `obs[2:4]`** (~line 435) — the disclosed "external mission planner" input. Know WHAT
  it is and WHY we disclose it (Methods §3.1-3.2).
- ⚠️ **Corrections to the two lines above (verified in code 2026-08-09) — carry these forward:**
  - **"48-ray" is wrong.** The cast is **192 rays** (`num_sectors = 16` × `rays_per_sector = 12`,
    `:353-355`), reduced to a **48-DIMENSIONAL** descriptor (`16 sectors × {min, mean, std}`, `:388`).
    Say "192-ray LiDAR encoded as a 48-d sector descriptor." (`methods.tex:12` has the same error.)
  - **"8 m gated comm" is wrong for this paper.** That is only the constructor DEFAULT (`:18`); the
    camera-ready evals pass **`communication_range=10.0`** (`eval_temporal.py:94`). Comm is
    deliberately LARGER than the 8 m LiDAR so a neighbour can describe what you cannot yet sense —
    that margin is both the value of collaboration and the attack surface.
    `PARAMETER_JUSTIFICATION_PHASE_CD.md §0` flags the "8 m comm" phrasing as wrong for this line.
  - **The 8 m LiDAR is not settable here.** `lidar_range` exists only in the phasecd copy (§1.1b);
    this file's default sensing range is fixed at the older 12 m value.

### 1.1b `Phase_CD/swarm_env_phasecd.py` 🔴 — **the base the paper ACTUALLY runs** (added 2026-08-09)
- **What:** the Phase-C/D experimental copy of §1.1, plus `lidar_range`, `speed_boost`, and the
  collaborative-perception hooks. `class SwarmLidarEnv_StepB10_8_0m` — same class name as the root
  file, which is exactly why the two get confused. **Every env in the chain above inherits THIS one.**
- **Why it exists:** the root env is frozen; experimental hooks live here.
- **Take away — the map generator, because two paper claims depend on it:**
  - `:287-292` obstacle generation: draw radius from **20% U[1.5,2.5] / 40% U[0.6,1.4] / 40% U[0.2,0.5]**,
    accept if ≥ `r + 2.0` m from the goal, accumulate `sum(pi r^2)` until it reaches `density × 400`.
    **There is NO overlap test and NO minimum gap between obstacles** — obstacles may overlap freely,
    so the area sum double-counts and TRUE coverage is well below the nominal density (measured:
    **0.237 true at nominal 0.27**, see §5.1 below).
  - `:284` the generator retries up to **50 times** until `_validate_obstacles()` **and**
    `_is_map_solvable()` pass — which is why `methods.tex:11`'s "every evaluated map is verified
    solvable" is true *by construction*.
  - `:103,:192,:208` BFS solvability inflates every obstacle by `drone_radius + 0.05 = 0.20 m` on a
    0.2 m grid. **That inflation, not any spacing rule, is what guarantees traversable corridors.**
  - `:313` `min_dist = 0.6` — the one real minimum-separation parameter, and it is **drone-to-drone
    at spawn**, not obstacle-to-obstacle.

### 1.2 `Phase_CD/Collab_Perception/swarm_env_raster.py` 🟡 — adds COLLABORATIVE PERCEPTION (Idea 1)
- **What:** neighbours broadcast sensed obstacles; receiver fuses them into its LiDAR channel; adds
  sustained LiDAR dropout.
- **Why:** implements Idea 1 (sharing) and the sensor-failure regime that makes sharing necessary.
- **Take away — the 3 functions that matter:**
  - `_sample_dropout()` — the ~33%-blind burst model (blind-fraction formula).
  - `_cast48()` — renders shared obstacle lists into 48 rays.
  - `_fused_lidar()` — ⭐ **the MIN-fusion**: per ray, take the minimum over own + received. THIS is why
    the attack works later (a fake near-obstacle wins the min). Sender-gating: a blind drone shares nothing.
  → Methods §3.3.
- ⚠️ **Which file you are in matters (added 2026-08-09).** This is the **raster/slot-fusion lineage**
  (`class SwarmLidarEnv_Raster`), the branch the collaborative-perception MODELS were trained on
  (§2.2). The Byzantine EVALS run the sibling branch in §1.2b. The three functions above exist in
  **both files with identical names**, so finding them proves nothing — always check the `class` line.
  Read this file for the raster architecture and the training lineage; read §1.2b for the mechanism
  the results actually measure.

### 1.2b `Phase_CD/Collab_Perception/env_collab_perception.py` 🔴 — **the real Idea-1 link** (added 2026-08-09)
- **What:** `class CollabPerceptionEnv(SwarmLidarEnv_StepB10_8_0m)` — the collaborative-perception
  layer that `ByzantineTrustEnv` (§1.3) actually inherits.
- **Why:** this is where sharing + dropout are implemented for every number in the paper.
- **Take away — same three functions, but these are the ones that run:**
  - `_sample_dropout()` `:56` — the ~33%-blind burst model (`lidar_dropout=0.10`, `dropout_sustain=5`).
  - `_cast48()` `:74` — renders a shared obstacle list into the 48-d descriptor.
  - `_fused_lidar()` `:97` — ⭐ **the MIN-fusion.** Everything downstream (the attack, both filters)
    is a modification of this one method. If you understand only one function in the project, this
    is a strong candidate for it.

### 1.3 `Phase_CD/Collab_Perception/env_byzantine_trust.py` 🔴 — adds ATTACK + NAIVE TRUST (Ideas 2 & 3)
- **What:** some drones become traitors broadcasting phantom obstacles; adds the naive consistency-trust
  filter.
- **Why:** implements Idea 2 (the threat) and Idea 3's baseline defense.
- **Take away:**
  - `_generate_phantoms()` — wall-of-phantoms placement (`block_dist`, `spacing`).
  - `_sample_radius()` / `_radii_for()` — the RANDOMIZED attack (per-map n~U{3..6}, radii from the real
    42/40/18 obstacle mixture → phantoms look like real obstacles).
  - `_ego_judgement()` — ⭐ the naive single-frame check: "I'm positioned to see your claimed obstacle but
    I don't → contradiction"; EWMA trust update (`alpha`), exclusion threshold (`tau`).
  - `_fused_lidar()` override — a distrusted neighbour is dropped from fusion.
  → Methods §3.4, §3.6(a).
- ⚠️ **Correction — "42/40/18" is an OUTCOME, not the sampling rule (added 2026-08-09).**
  `_sample_radius()` (`:75-85`) draws **20% large / 40% medium / 40% small**, byte-identical to the
  real map generator's line (`swarm_env_phasecd.py:289`) — which is precisely what makes phantoms
  size-indistinguishable from real obstacles. The **42/40/18** figure in
  `PARAMETER_JUSTIFICATION_PHASE_CD §2.2` is the *realized* mixture measured over 300 generated maps:
  the goal keep-out rejects large candidates more often, so large obstacles end up under-represented
  (18% instead of 20%). Quote 20/40/40 when describing the CODE, 42/40/18 when describing the
  MEASURED field.

### 1.4 `Phase_CD/Collab_Perception/env_byzantine_adaptive.py` 🔴 — adds CAMOUFLAGE + adaptive knobs (Idea 5 setup)
- **What (short file):** the camouflage attack + the knobs a defense-aware attacker can turn.
- **Why:** camouflage is the hard attack that defeats single-frame checks; the knobs power Idea 5.
- **Take away:** `_generate_phantoms()` override — camouflage hugs a real obstacle (`camouflage_gap`); knobs
  `phantom_center_offset` (the stealth/harm bind axis), `phantom_jitter`, `phantom_duty`. Know what each
  knob means as an *attacker capability*. → Methods §3.4.

### 1.5 `Phase_CD/Noise_added/env_noisy_byzantine.py` 🔴🔴 — adds NOISE + ROBUST + TEMPORAL (Ideas 3 & 4) — THE FILE
- **What:** sensor noise + the noise-aware robust filter + the temporal offset-bias filter (our contribution).
- **Why:** this is where the paper's core happens — noise breaks naive checking (Idea 3), and temporal
  aggregation fixes it (Idea 4).
- **Take away — master these:**
  - `_sample_sensing()` — Gaussian σ noise on every sensed position (one draw/step, shared).
  - `_ego_judgement()` override — the robust filter: `eps = verify_eps + k_sigma*σ`. Understand the
    **√2σ honest-disagreement** argument (why fixed thresholds break under noise).
  - `_temporal_update()` — 🏆 **THE CONTRIBUTION.** Offset `d = neighbour's claim − my own view of the
    matched obstacle`; keep a running mean per (ego, neighbour, my-track); flag when count ≥ 20 and
    ‖mean‖ > 0.6. **Be able to DERIVE on paper: honest d ~ zero-mean (√2σ, cancels); liar d ~ persistent
    bias (never cancels).**
  - `_broadcast_phantoms()` — how jitter/duty adaptive attacks emit.
  - `_fused_lidar()` — the composed (robust OR temporal) verdict → EWMA → gate; also `comm_loss` (R3).
  → Methods §3.5, §3.6(b,c), Algorithm 1.

---

## STAGE 2 — How the models were TRAINED (~2-3 hrs) 🟢
You do NOT need to run these; understand what each produced. Read the docs first, code second.

### 2.1 Provenance doc (READ FIRST)
- **`Phase_CD/M0_PROVENANCE_AND_LINEAGE.md`** 🔴 — the full model family tree:
  `v10 (from scratch) → v11 → v12 → v13 → v14 = M0`, per-generation problem→fix→why, + PPO hyperparameters.
  This is the answer to "where did your model come from?" (→ paper supplementary).

### 2.2 The training scripts (skim to connect names to the doc) ⚪
- **`Phase_CD/Collab_Perception/surgical_expand_raster.py`** — obs-space surgery (130→178): grafts the
  shared-map input channels onto M0 so it can accept neighbour data. Warm-start, not from scratch.
- **`Phase_CD/Collab_Perception/train_slot_fusion.py`** (and `train_raster.py`) — trains the
  collaborative-perception model (ON/OFF variants) → `raster_slot_fusion_{ON,OFF}_stage*`.
- **`Phase_CD/Noise_added/train_noise_robust.py`** (driver `run_option_c.py`) — fine-tunes under
  sensor-noise domain randomization (σ~U[0,0.6]) → `noise_robust_ON_stage{0,1,2}_final`. **stage2 (0.27
  lock-in) is the base for EVERY camera-ready number.**
- **Model files (`models/`):** `apex_ultra_glide_v14_comm8_lidar_final` = M0 · `raster_slot_fusion_ON/OFF_stage2`
  = collab-perception · **`noise_robust_ON_stage2_final` = the paper's model.**

### 2.3 Hyperparameter proof ⚪
- **`Phase_CD/dump_hparams.py`** — reads the actual PPO hyperparameters out of a checkpoint (ground truth,
  not memory). Explains the numbers in the provenance doc's table.

---

## STAGE 3 — How results are MEASURED (~1-1.5 hrs) 🟡
Understand what the numbers mean before reading the numbers.

### 3.1 The measurement backbone
- **`Phase_CD/manuscript/sections/setup.tex`** 🟡 — **read this BEFORE the eval code.** It is the
  paper's own statement of the metrics (honest-drone success, recovery, no-harm, detection P/R), the
  500-map paired protocol, and the bootstrap. The code below implements exactly this; reading the
  definition first makes `eval_temporal.py` far easier.
  ⚠️ Its solvability sentence is under repair — see "Known documentation defects" at the end.
- **`Phase_CD/Noise_added/eval_temporal.py`** 🔴 — the main eval. Per (noise, attack) cell it runs 5 arms:
  `base / attack(off) / robust / temporal / temporal_nh`. **Learn the metric definitions:** honest-drone
  success (denominator = honest drones only), **recovery** = defended − undefended, **no-harm** = defense-on
  but no-attacker − base (≈0 = safe).
- **`Phase_CD/Noise_added/boot_ci.py`** 🟡 — paired-bootstrap CIs: resample the SAME 500 maps for both arms,
  take the CI of the DIFFERENCE (why our error bars are tight and fair). ~50 lines.

### 3.2 The mechanism-evidence probe
- **`Phase_CD/Noise_added/probe_temporal_offset.py`** 🟢 — shows the offset signal SEPARATES honest vs
  liar (AUC 0.99 oracle / 0.85-0.90 realistic) *before* any filter is built. This is why the filter works.

### 3.3 The other evals (skim — know what each produces)
Paths matter here — these live in **two different folders**:
- `Collab_Perception/eval_slot_fusion_zero_shot.py` ⚪ — Idea 1 anchor (comm ON vs OFF).
- `Collab_Perception/eval_dropout_sweep.py` ⚪ — the "why ~33% dropout" curve.
- `Noise_added/eval_noise_sweep.py` / `eval_noise_robust.py` ⚪ — Idea 3 (naive collapses) → robust filter.
- `Noise_added/eval_adaptive_attack.py` ⚪ — Idea 5 (offset/gap/jitter/duty sweeps, the stealth/harm bind).
- `Noise_added/eval_comm_loss.py` / `eval_density_sweep.py` ⚪ — R3/R7 rebuttal experiments (packet loss, density).
- **`Phase_CD/measure_env_stats.py`** ⚪ (at Phase_CD root, NOT in Noise_added) — measured the real
  obstacle stats (count 29.7, mean radius 0.907 m, realized 42/40/18 band mixture) that justify the
  attack parameters. `Noise_added/verify_randomized_attack.py` — confirms the randomized attack
  matches that mixture.
- **`Noise_added/calibrate_density_realenv.py`** 🟡 (added 2026-08-09) — re-measures map solvability
  using the REAL env generator, because the original calibration used a different one. See "Known
  documentation defects" below before quoting any solvability number.

---

## STAGE 4 — The RESULTS themselves (~1 hr) 🔴
Now read the numbers with full context.
- **`Phase_CD/RESULTS_027_CAMERA_READY.md`** — every camera-ready table (f=1,2,3 × wall/camo, anchor,
  dropout, naive, adaptive, comm-loss, density) with CIs. This is the evidence base.
- **`Phase_CD/manuscript/sections/results.tex`** — the same numbers written as the paper's narrative.
- Map each results subsection back to its idea (1→§5.1, 2→§5.2, 3→§5.3, robust→§5.4, 4→§5.5, 5→§5.6).
  ⚠️ **Those are `results.tex`'s subsection numbers, NOT `PAPER_MASTER_PLAN`'s.** The master plan
  numbers the same material differently (anchor §5.2, attack §5.3-5.5, naive-breaks §5.6, robust
  §5.7/5.8, perception limit §5.10, temporal §5.11). When someone cites "§5.11" they mean the master
  plan; when this guide says "§5.5" it means the manuscript. Check which document you are in.

---

## STAGE 5 — Honest limits & positioning (~30 min) 🟢
- **`Phase_CD/manuscript/sections/discussion.tex`** — the two independent limits (navigation vs security),
  the precision caveat, disclosed assumptions.
- **`Phase_CD/manuscript/sections/related.tex`** — how we differ from PRBI/GCP/MATE/AerialTrust/CAD/etc.
- **`Phase_CD/REJECTION_RISKS.md`** — every reviewer objection + our answer (your rebuttal prep).
- **`Phase_CD/PARAMETER_JUSTIFICATION_PHASE_CD.md`** — every parameter defended ("no magic numbers").
  ⚠️ Read it WITH the defect list below: its §0 range reconciliation is unresolved and its §2.5 is
  stale (it calls the 0.27 lock-in "optional"; it was actually done, `train_noise_robust.py:52`).
  Its companions are root `PARAMETER_JUSTIFICATION.md` (physical params, with real citation URLs)
  and root `FINAL_PARAMETER.md` (the density study).

---

## STAGE 5b — How our PRIOR-ART claims are verified (~30 min) 🟡 (added 2026-08-09)
Not optional if you will defend the paper. Every "X does not do Y" sentence in `related.tex` is
backed by a written evidence file, and the standard for those files is strict.
- **`Phase_CD/AUDIT_PENDING.md`** 🔴 — the master ledger: which dossiers Claude has verified, which
  Srinivasa has personally reviewed, and the **DOSSIER WRITING STANDARD**. Nothing counts as closed
  until Srinivasa signs it off; committed ≠ audited.
- **`Phase_CD/REFERENCE_EVIDENCE_*.md`** (18 files) 🟡 — one per cited paper, in four parts:
  **A** = the authors' exact words · **B** = our `.tex` sentence mapped to those quotes ·
  **C** = our interpretation, which may never be attributed to them · **D** = claims verified by
  ABSENCE (a reproducible search showing they never say a thing).
  Start with **`REFERENCE_EVIDENCE_SWARMRAFT.md`** — it is the designated template.
- **`Phase_CD/FORWARD_CITATION_SWEEP.md`** ⚪ — the forward-citation search for work that might
  pre-empt us; its STATUS block is the sole owner of the progress counts.
- **The two lessons worth internalising:** (1) a quote can be word-perfect and still WRONG, if it is
  used for a claim its surrounding section contradicts — this is why fact and interpretation are
  physically separated (see 3D-TC2 "M-2"); (2) an absence claim must be backed by an executed
  search, never by recollection.

---

## KNOWN DOCUMENTATION DEFECTS (open as of 2026-08-09) — do not quote these numbers yet
Kept here so a reader is not misled by docs that are mid-repair. Nothing below affects any
experimental RESULT; all of it is about how parameters are described.
1. **The density calibration used a DIFFERENT map generator.** Root `FINAL_PARAMETER.md` (and hence
   `setup.tex`'s "96.8% of sampled maps are solvable") comes from `PhaseB2/density_sweep_v14_*.py`,
   whose generator **rejects overlapping obstacles** (`:113-121`). The real env allows overlap. At
   the same label "0.27" the two produce different worlds — sweep: 68.9 obstacles, true coverage
   0.2725; real env: 28.0 obstacles, **true coverage 0.237**. `FINAL_PARAMETER.md §2`'s claim that
   the sweep reproduces the env "exactly" is true for spawn and BFS parameters, **false for obstacle
   generation**. Re-measurement in progress via `calibrate_density_realenv.py`; the early result is
   that our maps are solvable at **100%** across 0.20-0.30, i.e. 0.27 is nowhere near a feasibility
   ceiling for OUR generator — so the "fairness ceiling" justification for 0.27 must be replaced
   (train/eval density match is the honest reason: stage 2 trained at 0.27).
2. **`setup.tex` obstacle-count range** says 13-56; `PARAMETER_JUSTIFICATION_PHASE_CD §2.2` says
   15-56. One is wrong; unresolved.
3. **`methods.tex:12` says "48-ray planar LiDAR"** — it is 192 rays encoded to 48 dimensions.
4. **Root `PARAMETER_JUSTIFICATION.md` citations are bound to the wrong values** — it justifies
   12 m LiDAR / 8 m comm with real sources, but this paper runs **8 m / 10 m**.
5. **Parameters that appear NOWHERE in the manuscript:** goal tolerance (1.0 m,
   `swarm_env_phasecd.py:745`), goal keep-out (2.0 m), the BFS clearance (0.20 m) that is the only
   thing guaranteeing traversable corridors, and the fact that there is **no minimum gap between
   obstacles at all**. A consolidated parameter table for `setup.tex` is owed.
6. ~~**`RESULTS_027_CAMERA_READY.md`** had stray text pasted into the σ=0.20 robust-recovery cell.~~
   ✅ **FIXED 2026-08-09.** The cell read `+1provide7.8`; restored to **`+17.8 [14.9,20.7]`**,
   confirmed by Srinivasa and independently checked against the table's own columns
   (recovery = robust − off = 76.0 − 58.3 ≈ 17.8; the temporal column reconciles the same way).
   A repo-wide search found **no other corruption site** — every remaining "provide" is prose.
   *Lesson worth keeping: a stray paste inside a number survives every spell- and lint-check.
   The arithmetic self-consistency of a results table is the only thing that catches it.*

---

## THE DEEPEST TEST (do this before the viva/submission)
Explain, WITHOUT notes:
1. Why MIN-fusion makes the attack dropout-independent.
2. Why a fixed-threshold check becomes destructive under noise (the √2σ argument).
3. Why the temporal offset is zero-mean for honest neighbours but biased for a liar.
4. Why 20 samples and 0.6 m thresholds.
5. Why an adaptive attacker faces the stealth/harm bind.
If you can do all 5 at a whiteboard, you own the research.

---

## Suggested schedule
- **Day 1:** Stage 0 + Stage 1 (env chain) — the biggest and most important.
- **Day 2 morning:** Stage 2 (training) + Stage 3 (evaluation).
- **Day 2 afternoon:** Stage 4 (results) + Stage 5 (limits) + the deepest-test self-check.
- **Day 3 (only if you will defend the paper):** Stage 5b (how prior-art claims are verified) +
  the Known Documentation Defects list, so you know which numbers are still under repair.
Ask Claude about anything that resists — pair each env file with its Methods subsection as you read.
