# AUDIT PENDING — Srinivasa's own review (nothing below is "closed" until he signs off)

**Standing rule:** every triage verdict, dossier, and applied citation in this list is Claude's work and is
**NOT final** until Srinivasa personally audits it. Claude must keep adding to this list and must not treat any
item as settled. Committed to git ≠ audited — commits are checkpoints, the audit is the gate.

Legend: ☐ = awaiting Srinivasa's audit · ☑ = Srinivasa audited & approved · ✎ = Srinivasa found an issue (see note)

---

## A. Prior-art triage dossiers — ALL 17 need auditing (each has its own page-pointer checklist inside)
Cross-check each against the paper PDF in `Phase_CD/Research paper/` and against the claim it backs in
`related.tex`/`methods.tex`/`discussion.tex`. The per-reference "what to verify" prompts also live in
`REFERENCE_VERIFICATION_GUIDE.md` (Groups A/B/C/D). Grouped the same way here:

**Group A — collaborative-perception security (defenses + attacks) [11]**
- ☐ **CAD** — `REFERENCE_EVIDENCE_CAD.md` (strongest competitor; benign-observer + camouflage blind-spot claims)
- ☐ **CoDynTrust** — `REFERENCE_EVIDENCE_CODYNTRUST.md` (benign async, feature-level)
- ☐ **MADE** — `REFERENCE_EVIDENCE_MADE.md` (hypothesis-test malicious-agent detection)
- ☐ **GCP** — `REFERENCE_EVIDENCE_GCP.md` (spatial-temporal malicious-agent detection; TDSC accept year)
- ☐ **PRBI** — `REFERENCE_EVIDENCE_PRBI.md` (⭐ MOST IMPORTANT — the 3 "does not" novelty claims must be bulletproof)
- ☑ **TrustFlip** — `REFERENCE_EVIDENCE_TRUSTFLIP.md` (trust-poisoning, expels honest agents) — **Srinivasa audited & approved 2026-07-26; incl. the "expel"→"downweight or exclude" wording tightening**
- ☐ **TruPercept** — `REFERENCE_EVIDENCE_TRUPERCEPT.md` (trust modelling; detection-vs-feature wording)
- ☐ **MATE** — `REFERENCE_EVIDENCE_MATE.md` (Hallyburton & Pajic; Bayesian FoV trust — task #5)
- ☐ **AerialTrust** — `REFERENCE_EVIDENCE_AERIALTRUST.md` (same authors; UAV distributed trust — task #5)
- ☐ **ROBOSAC** — `REFERENCE_EVIDENCE_ROBOSAC.md` (full read; 5-axis table; 3 precision traps — task #1)
- ☐ **Stealthy-Fab / PosePert** — `REFERENCE_EVIDENCE_STEALTHY_FAB.md` (full read; novelty survives 4 axes — task #2)

**Group B — temporal spoof detection, single-vehicle [2]**
- ☑ **3D-TC2** — `REFERENCE_EVIDENCE_TC2.md` (⚠ title was wrong once; single-vehicle, motion consistency) — **Srinivasa audited & approved 2026-07-26; incl. the "purely"→"authors attribute to" note softening**
- ☑ **ADoPT** — `REFERENCE_EVIDENCE_ADOPT.md` (point-level temporal consistency, single-vehicle) — **Srinivasa audited & approved 2026-07-26**

**Group C — Byzantine multi-robot / swarm [2]**
- ☑ **SwarmRaft** — `REFERENCE_EVIDENCE_SWARMRAFT.md` (⚠ Raft, NOT Byzantine — verify our caution holds) — **Srinivasa audited & approved 2026-07-26; note left as-is by his call**
- ☐ **Conformity** — `REFERENCE_EVIDENCE_CONFORMITY.md` (evolutionary game, decision layer not perception)

**Group E — benign CP precedents (new category from this session) [2]**
- ☐ **Coopernaut** — `REFERENCE_EVIDENCE_COOPERNAUT.md` (benign paradigm, credit-clause safeguard; privileged-planner trap)
- ☐ **Vadivelu** — `REFERENCE_EVIDENCE_VADIVELU.md` (benign; bias-limitation catch; §4.2/Fig 4 + "temporal=future work")

**Also audit the audit tool itself:**
- ☐ **`REFERENCE_VERIFICATION_GUIDE.md`** — the grouped per-reference checklist (dated 2026-07-09; does NOT yet
  include ROBOSAC/Stealthy-Fab/Coopernaut/Vadivelu — fold them in during/after audit).

**Triaged INLINE in `PRIOR_ART_SECOND_ORDER.md` (task #4) — no standalone dossier; audit the verdict there:**
- ☐ **Tu et al. 2021** — "Adversarial Attacks on Multi-Agent Communication" (ICCV 2021, arXiv 2101.06560).
  Verdict: **cite one-line, no dossier** (seminal feature-level CP attack; named by CAD+GCP+MADE; AP-scored,
  no navigation → no pre-emption). Metadata in hand → the A4 Tu one-liner is APPLY-READY (related.tex attack
  sentence + refs.bib). Audit: PRIOR_ART_SECOND_ORDER items F / 5.
- ☐ **Pretend-Benign** (Lin et al., ICCV'25) — **ABSTRACT-LEVEL triage ONLY; body-grep OWED (PDF 403
  bot-blocked).** Verdict: cite-optional near TrustFlip, no pre-emption *expected* (feature-level defense-aware
  attack, no navigation/noise regime). NOT fully closed — needs a manual PDF pull to confirm the body. Audit:
  PRIOR_ART_SECOND_ORDER items G / 10.

**Also surfaced by the full-bibliography scan (PRIOR_ART_SECOND_ORDER items 6–9) — decide at related-work polish:**
- ◑ **Cavorsi et al. (ICRA'23 / T-RO 2024, arXiv 2303.04075)** — **TIER-1 DEEP CHECK DONE 2026-07-27, no pre-empt.**
  Binary hypothesis testing at a central fusion centre, **one-shot** noisy measurements → fails Q1 (no navigation)
  and Q3 (no temporal accumulation). ⭐ **Reframe: cite as SUPPORT, not a rival** — it tolerates *"potentially more
  malicious than legitimate robots"*, an independent precedent for our no-honest-majority claim. Nearest
  RAS-community work → still likely add 1–2 lines. ☐ until Srinivasa signs off on the verdict + the reframing.
- ◑ **Obst 2014 / Allig 2019 / Tsukada 2022** — earliest peer-claim-vs-own-sensing + CPM-misbehavior cluster.
  **Obst + Allig 3-question-checked 2026-07-27 (Srinivasa ran it himself) — both safe, but PDFs OWED**
  (IEEE-paywalled → `INSTITUTE_WIFI_TODO.md` Priority 1) before the differentiator wording is finalized.
  ⚠ **Srinivasa's finding: Allig DOES handle sensor noise** → see new precision trap in §D.
- ◑ **LUCIA / SOMBRA** (Wang et al., USENIX Sec'25) — **TIER-1 DEEP CHECK DONE 2026-07-27, no pre-empt.**
  SOMBRA = object-**removal** attack (opposite direction to our fabrication); LUCIA = trustworthiness-aware
  attention **within a single fusion step**, detection-scored. Fails Q1/Q2/Q3. Optional cite. Free PDF on
  usenix.org (no longer bot-blocked). ☐ until Srinivasa signs off.
- ◑ **Hallyburton & Pajic (CDC'24, arXiv 2403.16956)** — **TIER-1 DEEP CHECK DONE 2026-07-27, no pre-empt**
  (detection/estimation only, adversarial-compromise not honest-noise). ⚠ **BUT its hierarchical Bayesian trust
  DOES accumulate over time** → new precision trap in §D. Cite-optional as the MATE lineage anchor.

## B. The abstract-level second-order pass (the honesty correction to the "zero new" claim)
- ☐ **`SECOND_ORDER_ABSTRACT_PASS.md`** — abstract reads over the ROBOSAC+Stealthy-Fab bibliographies (112 refs).
  Verify: the "MIGHT BE SIMILAR" list (Coopernaut, Vadivelu — both now full-read) and the honest scope note
  (~27 abstracts read; ~323 title-only; ~500 other-bibliography refs NOT yet passed).
- ☐ **`PRIOR_ART_SECOND_ORDER.md`** — the triage plan/ledger for this whole second-order sweep.

## C. Manuscript edits applied on the strength of the above (audit the WORDING, not just the cite key)
- ☐ **related.tex — ROBOSAC #1** (defense family, "all four evaluated using AP"). Commit `4466b8ae`.
- ☐ **related.tex — ROBOSAC #2** (no-clean-subset/known-ratio foil for the majority claim). Commit `4466b8ae`.
- ☐ **related.tex — Coopernaut credit clause** ("our contribution is not that paradigm but the adversarial
  layer within it"). Commit `4466b8ae`.
- ☐ **related.tex — Stealthy-Fab differentiation** (4-axis: attack / control layer / metric / scope).
  Commit `4466b8ae`.
- ☐ **discussion.tex — Vadivelu in assumption (vi)** (bias future-work now precedent-backed). Commit `939035f8`.
- ☐ **refs.bib** — 4 new entries: robosac2023, stealthyfab2026, coopernaut2022, vadivelu2020.
  Verify: page/venue TODO-VERIFY notes (coopernaut pages; stealthyfab named venue) before submission.

## D. Precision traps Claude committed to honoring (audit that the wording did NOT violate them)
- ☐ ROBOSAC: no "cross-agent temporal" (it's scene-vs-own-past); no "needs a majority" (works at η=0.8); do
  not contrast on the shared "trust own sensing" premise.
- ☐ Coopernaut: don't claim the closed-loop-learned-CP-navigation paradigm as ours-first; don't use "they use
  a privileged planner" as a differentiator (we have the Dijkstra crutch).
- ☐ Stealthy-Fab: don't present the stealth/harm bind as ours-first (theirs is via perturbation magnitude).
- ☐ Vadivelu: don't claim novelty on message-reweighting/exclusion itself (their attention module does it, benign).
- ☐ **Allig (NEW 2026-07-27 — Srinivasa's own finding):** do NOT write "Allig ignores sensor noise". Allig
  **does** handle measurement uncertainty in fusion. Our differentiator vs Allig = **navigation (Q1) +
  cross-agent temporal accumulation (Q3)**, NOT noise. (Claude's abstract-level read had this wrong.)
- ☐ **NAVIGATION-METRIC CLAIM (NEW 2026-07-28, forward sweep):** do NOT write "first to evaluate a CP defense
  by navigation/driving success". **SafeCoop** (2025) reports the CARLA **Driving Score** under attack, and the
  **LiDAR-spoofing safe-control paper** (arXiv 2302.07341, 2023) proposes a control law that provably avoids the
  estimated obstacle, validated in CARLA. Safe wording: "first **under ranging noise, with a learned multi-agent
  policy, at a Byzantine fraction up to 7/10**."
- 🚨 **GCP TEMPORAL — THE BIGGEST TRAP (NEW 2026-07-28, from the CP-Guard forward sweep).** **GCP is already
  cross-agent temporal WITH per-neighbour state**: full text (2501.02450v2) shows it reconstructs motion
  trajectories of *"specific neighbor agents across frames"*, matching low-confidence boxes *"from a particular
  collaborator across historical frames"*, **K=5** frames, caching per-neighbour detection history + matching
  chains, with an **LSTM-autoencoder**. So **"first cross-agent temporal" is FALSE in every form — delete it.**
  Surviving differentiators vs GCP, and these must be the wording: (i) **navigation-success metric** (GCP =
  AP@0.5 only); (ii) **ranging-noise honest-disagreement regime** — GCP *"does not explicitly model"* it and
  calibrates thresholds by conformal p-values + Benjamini–Hochberg on clean data; (iii) **mechanism** — GCP
  learns an LSTM-AE reconstruction error over motion-flow sequences, ours is a **closed-form zero-mean test on
  a geometric offset vector** (that is what survives √2σ); (iv) **Byzantine fraction 7/10, no honest majority**.
  ⚠ Cross-check this against `REFERENCE_EVIDENCE_GCP.md` — the dossier must state the per-neighbour caching and
  K=5 explicitly, or it understates the rival.
- ☐ **PRBI is SAFE on the temporal axis (NEW 2026-07-28):** its "temporal perceptual discrepancy" uses the
  **ego's own preceding frame** as reference — one frame, per-frame operation, no per-neighbour accumulation.
  Safe to contrast, but do not overstate it as "non-temporal".
- ☐ **CROSS-AGENT-TEMPORAL CLAIM (NEW 2026-07-28):** do NOT write "first/only cross-agent temporal trust".
  **CONClave** (DAC'24) keeps per-participant std-dev-score buffers over consensus rounds; **CATS** (TVT'25)
  keeps long-term per-vehicle reputation; **MVIG** (CVPR'26) uses k=5-frame temporal graph learning. The novelty
  is **WHAT** accumulates: a **geometric offset-vector mean** that is zero-mean under honest noise and
  persistently biased for a camouflage liar. (Compose with the Hallyburton trap below — same failure mode.)
- ☐ **ADAPTIVE-ATTACKER CLAIM (NEW 2026-07-28):** do NOT write "first adaptive/defense-aware attacker" —
  **MVIG** (CVPR'26) and **Stealthy-Fab** both are. Reframe as "consistent with recent adaptive attacks".
- ☐ **Hallyburton (NEW 2026-07-27):** do NOT write "we are temporal, the trust literature is not". Hallyburton's
  hierarchical Bayesian trust **does** accumulate per-agent belief over frames. The true differentiator is **WHAT
  is accumulated**: they accumulate a trust score from **track existence/assignment**; we accumulate a
  **geometric offset vector** (neighbour's reported obstacle position − ego's own sensed position) whose *mean*
  separates zero-mean honest noise from a persistent camouflage bias.

## E. Still OPEN (not done, tracked so the audit list stays honest about coverage)
- ◑ **LUCIA / CP-Guard / CP-Guard+ triage** (task #3) — **ABSTRACT-triaged 2026-07-26** via PRBI's bibliography
  (`SECOND_ORDER_FULL_ABSTRACT_SWEEP.md` §3e). None pre-empts us (all AP/feature-level CP defenses/attacks; no
  navigation/noise/temporal/adaptive). **Srinivasa's decision 2026-07-26: CP-Guard is a PLANNED cite** →
  owed: (1) full-read + `REFERENCE_EVIDENCE_CP_GUARD.md` dossier (PDF may be bot-blocked → manual pull),
  (2) `related.tex` defense-family sentence + differentiator clause, (3) `cpguard2025` in refs.bib (AAAI 2025).
  CP-Guard+ / LUCIA remain optional. Still ☐ until the dossier is built and Srinivasa audits it.
- ◑ **Second-order FULL abstract sweep** (`SECOND_ORDER_FULL_ABSTRACT_SWEEP.md`) — mandate-B abstract read of
  EVERY reference in ALL 13 dossiered papers' bibliographies. **✅ ALL 13 COMPLETE 2026-07-26** (CAD 91, MADE 44,
  PRBI 37, GCP 35, MATE 47, AerialTrust 37, TruPercept 36, CoDynTrust 35, SwarmRaft 43, TrustFlip 41, 3D-TC2 14,
  ADoPT 37, Conformity 15 = ≈460 slots, ≈300 distinct abstracts). **ZERO pre-emptions.** Only actionable find =
  **CP-Guard planned cite**; optional = Cavorsi + classical VANET-trust reps. CAD's security subset already
  audited by Srinivasa. **Remaining audit = Srinivasa's skim of each other bibliography's security-relevant rows
  (the ~49 total, per the SECOND_ORDER file's ⭐/verdict tables).** Not closed until he signs off.
  **PROGRESS 2026-07-27:** the ~46 pending rows were split into **Tier 1 (6 rows that could actually hurt us)**
  and Tier 2 (40 out-by-category). All 6 Tier-1 rows deep-checked with the 3-question test
  (`SECOND_ORDER_FULL_ABSTRACT_SWEEP.md` §"TIER-1 DEEP CHECK"): **LUCIA, Cavorsi, Hallyburton closed clean**;
  **Obst + Allig safe but PDFs owed** (→ `INSTITUTE_WIFI_TODO.md`); **CP-Guard dossier still owed**.
  **2 precision traps found** (Allig-noise, Hallyburton-temporal) → recorded in §D. Tier 2 still awaits
  Srinivasa's by-category accept/reject.
- ◑ **Forward citation sweep** (`FORWARD_CITATION_SWEEP.md`) — **7 of 19 anchors done 2026-07-28** (CAD,
  ROBOSAC, TruPercept, Coopernaut, **ADoPT, 3D-TC2, CP-Guard**). **~220 citing papers examined; ~50 new papers
  the backward sweep could not reach.** Verdicts: **6 must-cite** (LiDAR-Spoofing-Safe-Control, SafeCoop,
  CONClave, CATS, MVIG, RLCVP) · 20 group-cite · ~75 no-cite · **4 unknown (not locatable — NO verdict)**.
  **Standing rule now in force: ZERO title-grade** — every verdict rests on ≥ abstract; unreachable papers are
  logged unknown, never "safe" (memory: `paper-reading-depth-standard`).
  **Compound novelty SURVIVES (0 pre-emptions), but 4 individual claims overstated → §D**, the worst being
  🚨 **GCP is already cross-agent temporal with per-neighbour K=5 state**.
  ✅ **Strengthened:** the temporal-detection lineage (ADoPT + 3D-TC2, 41 descendants individually read) is
  **entirely single-vehicle** — nobody there took the cross-agent step.
  ❌ **STILL TO DO — 12 anchors:** MADE, MATE, PRBI, GCP, CoDynTrust, TrustFlip, AerialTrust, Stealthy-Fab,
  SwarmRaft, Conformity, Vadivelu, Tu. Plus Srinivasa's Google-Scholar "Cited by → Since 2025" pass (Scholar
  blocks the fetcher — steps in Part 6 of that file), and the 2 PDFs he is downloading
  (Fake-Objects-CPM, ST-GNN).
- ☐ **Wan et al. T-ITS 2025 CP survey** — one scan (it indexes "adversarial attacks on CP").
- ☐ **Other ~500 title-rejections** from the 6-core + SwarmRaft/TrustFlip/3D-TC2/ADoPT/Conformity/MADE
  bibliographies — NOT abstract-passed yet.

## F. Earlier manuscript work (this line) — audit if not already reviewed
- ☐ Majority-boundary edits (tab:headline f=1–7; §5.11 local-neighbourhood framing; related.tex majority claim).
- ☐ Baseline reconciliation (dropout ablations; §ANCHOR lineage).
- ☐ Dijkstra goal-heading disclosure (discussion.tex assumption (i)).
- ☐ Sensor-bias limitation rewrite (discussion.tex assumption (vi) measured numbers).
- ☐ setup.tex obstacle-count range 15→13; probe AUC → 500-map 0.85–0.88.

---
_Last updated 2026-07-26. Claude: append new triage/citation/edit items here as they are produced; never delete
a row — flip ☐→☑ only when Srinivasa says so._
