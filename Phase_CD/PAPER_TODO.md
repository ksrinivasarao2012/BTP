# PAPER TODO — RAS submission (Byzantine-resilient collaborative perception)

Single running checklist. Target venue: **Elsevier *Robotics and Autonomous Systems*** (free
subscription track, IF 5.2, Q1). Full context in `PAPER_MASTER_PLAN.md`; submission requirements in
`PAPER_MASTER_PLAN.md §10.1`. Manuscript lives in `Phase_CD/manuscript/`.

---

## A. Manuscript writing (in `Phase_CD/manuscript/sections/`)

- [x] `abstract.tex` — full draft (~226 words, camera-ready numbers)
- [x] `introduction.tex` — full draft (6 paragraphs, 5 contributions)
- [x] `related.tex` — full draft (CAD / PRBI / TrustFlip / 3D-TC2 / ADoPT / SwarmRaft differentiated)
- [x] `methods.tex` — full draft (verified against code); Algorithm 1 box included
- [x] `setup.tex` — full draft (metrics, 500-map protocol, paired bootstrap CIs)
- [x] `results.tex` — full draft (all camera-ready tables + figure callouts)
- [x] `discussion.tex` — full draft (two honest limits, precision caveat, disclosed assumptions)
- [x] `conclusion.tex` — full draft (summary + future work)

**ALL PROSE COMPLETE.** Remaining before submission = mechanical (B), citations (C), repo (D),
figures (E), author items (F), checks (G).

## B. Manuscript mechanical / formatting

- [x] **B1. Algorithm box** — `algorithm2e` added to `main.tex`; Algorithm 1 (composed per-step defense)
  written in `methods.tex §3.6`.
- [ ] **B2. Fill title-page TODOs in `main.tex`**: Professor's full name, institute/department, city.
- [ ] **B3. CRediT statement** — confirm each author's roles (draft is in `main.tex`).
- [ ] **B4. Data availability** — insert GitHub URL + Zenodo DOI once the release repo exists (see D).
- [ ] **B5. Highlights** — `highlights.tex` drafted; **verify each bullet ≤85 chars incl. spaces** (one is
  borderline at 85).
- [ ] **B6. Keywords** — confirm the 6 chosen keywords are the best for indexing.
- [ ] **B7. Supplementary material** — Methods §3.2 PROMISES "full hyperparameters and the training lineage
  in the supplementary material" — must assemble it: convert `M0_PROVENANCE_AND_LINEAGE.md` (v10→v14→M0
  chain, per-generation problem→fix→why, verified PPO hyperparameter table) + relevant
  `PARAMETER_JUSTIFICATION` tables into a supplementary PDF (elsarticle-compatible). Without this, the
  main-text promise dangles — reviewers check.

## C. References — ✅ ALL VERIFIED 2026-07-08 against primary sources (authors filled, no guesses)

- [x] PRBI 2603.08498 — Yu, Wu, Zhang, Qiu, Huo, Feng; CVPR 2026 ✅
- [x] TrustFlip 2605.22122 — Liu, Wang, Li, Zhang; 2026 ✅
- [x] CoDynTrust 2502.08169 — Xu, Li, Wang, Yang, Wu, Chen, Wang; 2025 (venue unspecified) ✅
- [x] 3D-TC2 2106.07833 — **TITLE CORRECTED** (was wrong): "Temporal Consistency Checks to Detect LiDAR
  Spoofing Attacks on Autonomous Vehicle Perception", You/Hau/Demetriou, MAISP 2021 ✅
- [x] ADoPT 2310.14504 — Cho, Cao, Zhou, Mao; BMVC 2023 ✅
- [x] Conformity game 2606.21206 — Ren, Zhao, Fang; 2026 ✅
- [x] SwarmRaft 2508.00622 — Dev, Madhwal, Shevelo, Osinenko, Yanovich; 2025 ✅
  **CAUTION: Raft = crash-FT, NOT Byzantine.** Prose reworded so it is not framed as a Byzantine defense.
- [x] TruPercept — Hurl/Cohen/Czarnecki/Waslander, IEEE IV 2020 ✅
  **⚠ FACTUAL ERROR FOUND & FIXED 2026-07-09 (Srinivasa's manual check).** Our text claimed TruPercept
  "weighs deep feature contributions". Its abstract states: *"Based on the accuracy of reported **object
  detections** as verified locally..."* → it is OBJECT-LEVEL, verify-against-own-observation — i.e. the SAME
  family as MATE and our own single-frame check, not the feature camp. `related.tex` restructured: feature
  line = CoDynTrust + GCP; object-level verify-against-own-sensing line = TruPercept (2020) -> MATE (2025)
  -> AerialTrust (2025), with our single-frame filters explicitly named as members of that family and our
  contribution positioned "where this family breaks" (under noise). R1 baseline paragraph updated to match.
  **Net effect: a wrong claim removed AND the Related Work narrative strengthened.**
- [x] CAD 2309.12955 — Zhang et al., USENIX Security 2024 ✅ (prose reworded: no unverifiable "camouflage
  blind spot" claim; kept only what the abstract supports)
- [ ] OPTIONAL add if cited: MADE, "Among Us", CONClave, PhyScout (CCS'24) — verify each on arXiv first.
- [x] **GCP & MATE assessed + CITED 2026-07-09 (neither pre-empts):**
  - **GCP** (Tao et al., IEEE TDSC 2025, arXiv 2501.02450) — defends a "blind-area confusion" attack via
    spatial checks + temporal BEV motion-flow reconstruction; vehicular, detection-AP. Added to refs.bib +
    related.tex (differentiated: detection accuracy for feature fusion, not noise regime/navigation).
  - **MATE** (Hallyburton & Pajic, **CCS 2025**, arXiv 2503.04954) — **FULL-TEXT AUDITED 2026-07-09 (22 pp)**.
    Positive claims verified (HMM/Bayesian PSM trust ✓, geometric object-level consistency ✓, FOV reasoning ✓).
    **Negative-claim fix applied:** MATE DOES handle noisy sensors ("longitudinal filtering", resilience to
    natural FPs/FNs) → blanket wording would be false; `related.tex` reworded to credit this and narrow our
    claim to what holds: no harm-inversion regime characterization, no camouflage-inside-noise-tolerance, no
    closed-loop navigation metric (verified: camouflage/phantom 0 hits; navigation only in a ref title;
    metrics = assignment precision/recall/F1). NEW: their FP attack includes STATIC (persistent) fake objects
    — closest attack model to ours anywhere; their "attacker must stay dynamics-consistent" observation
    corroborates our persistent-phantom framing. Venue note: arXiv page has NO acceptance comment; CCS 2025
    rests on ACM DL (bib note added).
  - [x] **Aerial trust paper FULL-TEXT AUDITED 2026-07-09 (12 pp)** (Hallyburton & Pajic, ICCPS 2025,
    arXiv 2507.17875, v1-only Jul 2025, no acceptance note on arXiv — venue via ACM DL, Part A
    human-verified by Srinivasa). ALL our claims hold with the post-MATE rewording: "navigation" appears
    12x but ONLY as the shared data stream / pipeline box + future-work planning discussion — metrics are
    assignment P/R/F1 + trust-distribution accuracy, NO task success (claim ✓); camouflage/phantom 0 hits
    (claim ✓); noise = dataset randomization + "account for natural errors...noisy occluded sensors" =
    accommodation, not harm-regime characterization (covered by our "accommodates natural sensor error"
    wording ✓). NEW findings: their "trust builds gradually, degrades quickly" = our EWMA asymmetry
    philosophy (corroboration); they publish the FIRST multi-agent aerial CARLA dataset (useful for our
    future 3-D/hardware validation); finding that denser agent networks improve trust robustness.
- [x] **PRBI full-text verified 2026-07-09 (claims audit):** noise=0 hits, navigation=0 hits → claims 1–2
  bulletproof. Claim 3 refined in `related.tex` (they DO test intermittent injection schedules; they do NOT
  test a defense-aware/optimizing attacker). Their threat model = bounded feature-map perturbations
  (PGD/C&W), k up to n−1; totally different attack type from our geometric fabrication.

## D. Reproducibility / data availability (RAS "Option C" — REQUIRED, see §10.1)

- [ ] Build a CLEAN release repo (curated copy, do NOT clean the working repo) — see `PAPER_MASTER_PLAN.md`
  release-repo plan. Include: 2 envs used, the eval scripts, the 4 models used, `results_027/` logs, README,
  MIT LICENSE, requirements.txt; strip hardcoded paths.
- [ ] Push release repo public on GitHub (submission day).
- [ ] Mint a **Zenodo DOI** from the GitHub release → put DOI in `main.tex` Data availability + cite as
  `[dataset]/[software]`.

## E. Figures (generate from ledger numbers → `manuscript/figures/*.pdf`)

- [ ] Fig 1 — system/architecture diagram (drones, LiDAR, comm, fusion, attack, trust) — conceptual
- [ ] Fig 2 — dropout curve: ON vs OFF success at 0/33/50% blind (§5.2)
- [ ] Fig 3 — naive precision collapse / no-harm vs σ (§5.6)
- [ ] Fig 4 — temporal recall vs σ (robust vs temporal), and recovery bars across f=1,2,3 (§5.11)
- [ ] Fig 5 — offset-vector honest-vs-liar distribution (from `probe_temporal_offset.py`)
- [ ] Fig 6 — stealth/harm bind: harm & recall vs phantom offset (§5.11b)

## F. Author-facing submission items (§10.1)

- [ ] **Vitae** — ≤100-word bio + passport-type photo per author (editable format)
- [ ] **Declaration of competing interest** — via Elsevier declarations tool, upload as .docx
- [ ] **Generative-AI declaration** — already in `main.tex`; **Prof must approve wording** (co-author sign-off)
- [ ] Cover letter (not mandatory, but prepare a short one)
- [ ] Confirm Prof approves venue + no-APC + submission

## G. Pre-submission checks

- [ ] Read the WHOLE manuscript end-to-end; every sentence understood and owned (AI-declaration responsibility)
- [ ] All tables/figures cited in text; all refs cited both ways
- [ ] Compile clean in Overleaf (elsarticle), no `\todo` marks left
- [ ] arXiv preprint prepared to post on submission day (scoop protection)

---

# CODE TO READ — in this exact order (study path)

Read each file top-down asking: **"what does this class add over its parent?"** The 5 env files form an
inheritance chain that mirrors the paper. Pair each with its Methods subsection in `manuscript/sections/methods.tex`.

Depth key: 🔴 know cold (whiteboard, from memory) · 🟡 know well · 🟢 conceptual · ⚪ skim.

### Core environment chain (the mechanisms — ~1 day)

- [ ] **1. `swarm_env_step_B10_8_0m.py`** (repo root) — 🟢 base
  - Key: 48-ray LiDAR casting; 8 m gated comm; the Dijkstra routed heading at `obs[2:4]` (~line 435) —
    know WHAT it is and WHY we disclose it. → Methods §3.1, §3.2

- [ ] **2. `Phase_CD/Collab_Perception/swarm_env_raster.py`** — 🟡 know well
  - `_sample_dropout()` (l.100) — sustained-blindness model (~33% blind); blind-fraction formula.
  - `_cast48()` (l.118) — render shared obstacle lists into 48 rays.
  - `_fused_lidar()` (l.141) — ⭐ **MIN-fusion** — WHY the attack works (fabricated near reading wins the min).
  - Sender gating (blind drone shares nothing). → Methods §3.3

- [ ] **3. `Phase_CD/Collab_Perception/env_byzantine_trust.py`** — 🔴 know cold
  - `_generate_phantoms()` (l.92) — wall placement (`block_dist=3.5`, `spacing=1.3`).
  - `_sample_radius()`/`_radii_for()` (l.75/87) — randomized attack (n~U{3..6}, real 42/40/18 radii mix).
  - `_ego_judgement()` (l.113) — ⭐ naive single-frame trust check; EWMA (`alpha`), threshold (`tau`).
  - `_fused_lidar()` override (l.132) — distrusted neighbour excluded from fusion. → Methods §3.4, §3.6(a)

- [ ] **4. `Phase_CD/Collab_Perception/env_byzantine_adaptive.py`** — 🔴 short file, know all
  - `_generate_phantoms()` override (l.38) — ⭐ **camouflage** (phantom hugs a real obstacle, `camouflage_gap`);
    adaptive knobs `phantom_center_offset` (the bind axis), `phantom_jitter`, `phantom_duty`. → Methods §3.4

- [ ] **5. `Phase_CD/Noise_added/env_noisy_byzantine.py`** — 🔴🔴 THE file, whiteboard mastery
  - `_sample_sensing()` (l.144) — Gaussian σ noise on sensed positions (one draw/step, shared).
  - `_ego_judgement()` override (l.170) — ⭐ robust filter `eps = 0.6 + 4σ` (the √2σ argument).
  - `_temporal_update()` (l.110) — 🏆 **THE CONTRIBUTION**: offset `d = reported − own_sensed`, running mean
    per (ego,neighbour,track), flag when count ≥ 20 and ‖mean‖ > 0.6. **Must derive: honest d ~ N(0,√2σ)
    zero-mean; liar d biased.**
  - `_broadcast_phantoms()` (l.87) — how jitter/duty adaptive attacks emit.
  - `_fused_lidar()` (l.186) — composed (robust OR temporal) verdict → EWMA → gate. → Methods §3.5, §3.6(b,c)

### Evaluation (what the numbers mean — ~1–1.5 h)

- [ ] **6. `Phase_CD/Noise_added/eval_temporal.py`** — 🟡 the 5 conditions per cell (base/attack/robust/
  temporal/no-harm); what recovery & no-harm mean; honest-drone-only success denominator.
- [ ] **7. `Phase_CD/Noise_added/boot_ci.py`** — 🟡 paired bootstrap: resample the SAME 500 maps for both
  arms, take the CI of the DIFFERENCE. (~50 lines.)
- [ ] **8. `Phase_CD/Noise_added/eval_adaptive_attack.py`** — ⚪ the sweep grid (offset/gap/jitter/duty).
- [ ] **9. `Phase_CD/Noise_added/probe_temporal_offset.py`** — ⚪ AUC evidence the offset signal separates
  honest/liar (Fig 5 source).

### Training story — read the DOCS, not the trainer code (~1–2 h)

- [ ] **10. `Phase_CD/M0_PROVENANCE_AND_LINEAGE.md`** — 🟢 training history v10→M0 + PPO hyperparameters.
- [ ] **11. `Phase_CD/PARAMETER_JUSTIFICATION_PHASE_CD.md`** — 🟢 every parameter defended.

### The deepest test (before submission)
- [ ] Explain the temporal filter to the Prof **without notes**: offset vector, zero-mean vs persistent bias,
  why 20 samples, why 0.6 m, and why MIN-fusion makes the attack dropout-independent.
