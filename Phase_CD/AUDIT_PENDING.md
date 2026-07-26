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
- ☐ **TrustFlip** — `REFERENCE_EVIDENCE_TRUSTFLIP.md` (trust-poisoning, expels honest agents)
- ☐ **TruPercept** — `REFERENCE_EVIDENCE_TRUPERCEPT.md` (trust modelling; detection-vs-feature wording)
- ☐ **MATE** — `REFERENCE_EVIDENCE_MATE.md` (Hallyburton & Pajic; Bayesian FoV trust — task #5)
- ☐ **AerialTrust** — `REFERENCE_EVIDENCE_AERIALTRUST.md` (same authors; UAV distributed trust — task #5)
- ☐ **ROBOSAC** — `REFERENCE_EVIDENCE_ROBOSAC.md` (full read; 5-axis table; 3 precision traps — task #1)
- ☐ **Stealthy-Fab / PosePert** — `REFERENCE_EVIDENCE_STEALTHY_FAB.md` (full read; novelty survives 4 axes — task #2)

**Group B — temporal spoof detection, single-vehicle [2]**
- ☐ **3D-TC2** — `REFERENCE_EVIDENCE_TC2.md` (⚠ title was wrong once; single-vehicle, motion consistency)
- ☐ **ADoPT** — `REFERENCE_EVIDENCE_ADOPT.md` (point-level temporal consistency, single-vehicle)

**Group C — Byzantine multi-robot / swarm [2]**
- ☐ **SwarmRaft** — `REFERENCE_EVIDENCE_SWARMRAFT.md` (⚠ Raft, NOT Byzantine — verify our caution holds)
- ☐ **Conformity** — `REFERENCE_EVIDENCE_CONFORMITY.md` (evolutionary game, decision layer not perception)

**Group E — benign CP precedents (new category from this session) [2]**
- ☐ **Coopernaut** — `REFERENCE_EVIDENCE_COOPERNAUT.md` (benign paradigm, credit-clause safeguard; privileged-planner trap)
- ☐ **Vadivelu** — `REFERENCE_EVIDENCE_VADIVELU.md` (benign; bias-limitation catch; §4.2/Fig 4 + "temporal=future work")

**Also audit the audit tool itself:**
- ☐ **`REFERENCE_VERIFICATION_GUIDE.md`** — the grouped per-reference checklist (dated 2026-07-09; does NOT yet
  include ROBOSAC/Stealthy-Fab/Coopernaut/Vadivelu — fold them in during/after audit).

**Triaged but NOT in dossier form (task #4 — flag for Srinivasa):**
- ☐ **Tu et al. 2021** + **Pretend-Benign (PB)** — marked triaged (task #4) but there is **no
  `REFERENCE_EVIDENCE_*` file** for either. Confirm whether they were handled inline (abstract pass) or still
  owe a dossier.

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

## E. Still OPEN (not done, tracked so the audit list stays honest about coverage)
- ☐ **LUCIA / CP-Guard / CP-Guard+ triage** (task #3) — named CP-security defenses, NOT yet triaged (PDFs were
  bot-blocked; may need Srinivasa to download).
- ☐ **Forward citation sweep** on the ~6 anchor papers (who cites CAD/MADE/MATE/PRBI/ROBOSAC/TruPercept).
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
