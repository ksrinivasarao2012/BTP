# MATE — paired claim/evidence sheet (re-audit, 2026-07-11)

## STATUS: ✅ CLOSED (2026-07-16) — verified independently by Srinivasa against the PDF
Claude's full-text read found 3 items (catches #18, #19, #20), all fixed in related.tex;
Srinivasa then audited all 4 uses against the paper and confirmed — no further mismatches.

Full 22-page re-read done. Format: **WE WRITE** = exact current `.tex` sentence · **THEY WROTE** =
verbatim passage from `Phase_CD/Research paper/MATE.pdf` (with section) · **Verdict**.

Paper: R. Spencer Hallyburton, Miroslav Pajic — "Security-Aware Sensor Fusion with MATE: the
Multi-Agent Trust Estimator", ACM CCS 2025 (published 22 Nov 2025; arXiv:2503.04954 v1, 6 Mar 2025).
Ligature note applies (hyphenation across line breaks also defeats grep — e.g. "preci-sion").

MATE is cited in **three places** (USE 1-3), plus it is covered by the family-limits passage (USE 4).

## What MATE actually is (established by the full read)
- **Setting: a SMART CITY** — "we consider an urban environment composed of networked mobile and
  static agents ('smart city')" (§1). NOT surveillance: "surveillance" appears once, in a REFERENCE
  TITLE ("Fooling automated surveillance cameras"); "reconnaissance" once, in passing.
- **Task:** maintain shared situational awareness (SA) via **multiple target tracking (MTT)**.
- **Architecture: CENTRALIZED** — "agents send local information to the smart-city data aggregator";
  "we ... discuss **centralized MTT** for collaborative fusion" (§3); "trusted computing centers
  (AGG) ... subsequently execute MTT".
- **Trust:** hidden-Markov model; sensor data -> trust pseudomeasurements (PSMs) -> Bayesian
  posteriors; PSMs are formed by comparing an agent's reported SA against **a prediction of what it
  should have observed**, using an online **field-of-view estimator** (LiDAR ray tracing).

---

# USE 1 — Related Work, object-level family sentence

**WE WRITE (`sections/related.tex`):**
> ...MATE~\cite{mate2025} formalizes this as Bayesian trust estimation over geometric observation
> consistency with explicit field-of-view reasoning, against false-positive, false-negative, and
> translation attacks on multi-target tracking;

**Phrase 1 — "Bayesian trust estimation" / "formalizes this"**
- THEY WROTE (Abstract): "Trust estimation can be cast as a hidden Markov model, and we solve it by
  mapping sensor data to trust pseudomeasurements (PSMs) that recursively update trust posteriors in
  a Bayesian context."
- Verdict: ✅ exact.

**Phrase 2 — "over geometric observation consistency"**
- THEY WROTE (§1): "PSMs are made comparing an agent's locally-estimated SA with a prediction of what
  it should have observed."
- Verdict: ✅ supported (their PSM is exactly a claim-vs-expected-observation consistency test).

**Phrase 3 — "with explicit field-of-view reasoning"**
- THEY WROTE (Abstract): "Essential to security-awareness are a novel field of view estimator..."
- THEY WROTE (§1): "The prediction leverages dynamic estimates of the agent's field of view (FOV) at
  each timestep... we implement a ray tracing algorithm on each agent's LiDAR point cloud to estimate
  FOVs online."
- Verdict: ✅ exact (and stronger than "explicit" — theirs is dynamic/occlusion-aware).

**Phrase 4 — "against false-positive, false-negative, and translation attacks"**
- THEY WROTE (§1): "the adversary may perturb sensing/detection data of the compromised agent by
  injecting false positives (FPs), creating false negatives (FNs), or translating existing objects."
- Verdict: ✅ exact, in their order and terminology.

**Phrase 5 — "on multi-target tracking"**
- THEY WROTE (§1): "...estimating both the number of objects that exist and the states of those
  objects (e.g., position, velocity) with multiple target tracking (MTT)."
- Verdict: ✅ exact.

**USE 1 verdict: ✅ every phrase verified; no change needed.**

---

# USES 2 & 3 — Related Work, the "On baseline comparison" paragraph

Both MATE mentions live in this ONE paragraph, so it is reproduced here IN FULL (verbatim,
`related.tex` lines 155-175). MATE's two claims are marked [USE 2] and [USE 3].

**WE WRITE (`sections/related.tex` lines 223–250) — FULL PARAGRAPH, 🔄 RESYNCED 2026-07-28:**
> \paragraph{On baseline comparison.}
> The defenses above cannot be transplanted onto our benchmark without distortion: **CAD, PRBI,
> GCP, and MADE defend the fused perception pipelines of vehicular detection stacks and are
> evaluated by detection-level metrics (anomaly-detection rates or average precision)**,
> **while TruPercept, MATE, and the same authors' aerial framework operate at the object and
> track level;** [USE 2]
> none is designed to operate directly on the geometric obstacle claims exchanged by our agents, and
> none produces the navigation-success outcome we measure --- a reimplementation would test our
> translation of each method rather than the method itself. **The cooperative fault-detection
> framework~\cite{lidarspoof2023} is closer in spirit but likewise not transplantable: … so
> porting it would replace both our message format and our control layer.** We instead compare against the
> \emph{primitive that the object-level family shares}: verifying a peer's claims against what the
> verifier itself was positioned to observe, accumulating trust, and excluding on contradiction.
> That primitive is implemented natively in our setting in two strengths --- the fixed-tolerance
> (naive) variant and the noise-aware robust variant (Section~\ref{sec:methods-defense}) --- and
> **it is the same visibility-and-consistency recipe underlying TruPercept~\cite{trupercept2020} and
> the MATE line~\cite{mate2025,aerialtrust2025}.** [USE 3] Our evaluation therefore reports how the
> family's core mechanism behaves in this regime --- including its noise-induced failure --- before
> showing what the temporal test adds on top of it.

## [USE 2] "MATE ... score[s] object detections and tracks"
**THEY WROTE (§1):** "Two traditional classes of metrics capture performance of the object existence
(number of objects) and state estimation capability of unsecured and trust-informed fusion: (1)
precision, recall, and F1-score, and (2) optimal subpattern assignment (OSPA)... we derive novel
trust-oriented metrics that compare trust PDFs to agent and track states."
**Verdict:** ✅ MATE scores object/track existence + state (P/R/F1, OSPA) plus trust metrics — i.e.
detections and tracks. Also ✅ the paragraph's "none produces the navigation-success outcome we
measure": MATE has NO navigation metric ("navigation" = 1 hit, a reference title).

## [USE 3] "the same visibility-and-consistency recipe underlying ... the MATE line"
**THEY WROTE (§1):** "PSMs are made comparing an agent's locally-estimated SA with a prediction of
what it should have observed. The prediction leverages dynamic estimates of the agent's field of
view (FOV) at each timestep."
**Verdict:** ✅ "visibility" = their FOV estimator; "consistency" = their SA-vs-expected comparison.
Exactly the primitive our naive/robust filters implement.

## ⚠️ NOTE on the rest of this paragraph (NOT a MATE issue)
The FIRST half of the opening sentence — "CAD, PRBI, and GCP operate on the deep feature maps ...
and score detection accuracy" — carries the **held fix 15b**: "deep feature maps" is imprecise for
GCP (output-level detector) and PRBI (Jaccard over detection sets), CAD is UNVERIFIED, and "detection
accuracy" is ambiguous (object-detection AP vs malicious-agent-detection accuracy). **Fix the whole
clause in one pass after CAD.pdf is read.** MATE's half of the sentence is verified correct.

---

# USE 4 — Related Work, family-limits passage (covers MATE without naming it)

**WE WRITE (`sections/related.tex`) — CURRENT (catches #18 + #19 APPLIED 2026-07-11):**
> This line accommodates natural sensor error through longitudinal filtering, and observes that an
> attacker must remain dynamics-consistent to evade local filtering; ... Where our setting departs
> further: TruPercept aggregates trust at a central server and MATE at a central computing centre
> (its aerial extension does distribute the estimation), whereas our verdicts are pairwise and local,
> as a swarm without infrastructure requires. None of this line characterizes the regime in which the
> consistency check itself turns harmful under ranging noise (our destructive-filter result),
> considers fabrications geometrically camouflaged within the noise tolerance of real objects, or
> measures impact on a closed-loop learned navigation task --- their trust protects a shared
> perception picture, whether for driving, a smart city, or aerial surveillance, whereas ours
> protects the obstacle map a policy steers by.

**THEY WROTE — "longitudinal filtering" (our positive claim):**
> "A shortcoming of Byzantine models is their inability to handle noisy, error-prone sensor data by
> requiring unrealistic perfect perception. **We solve this challenge with longitudinal filtering.**"
- Verdict: ✅ exact. (This is the quote that killed our earlier FALSE claim that MATE ignores sensor
  noise — first audit.)

**THEY WROTE — "attacker must remain dynamics-consistent":**
> "In the worst case, manipulations will propagate over time in attacker-defined trajectories
> stealthily consistent with plausible dynamics..." / "Attacks not obeying plausible dynamics will be
> filtered by agent-local algorithms; thus, the attacker must inject longitudinally-consistent traces."
- Verdict: ✅ exact.

**THEY WROTE — central architecture (our new claim):**
> "...we describe platform-level algorithms for agent's local inference and discuss **centralized
> MTT** for collaborative fusion." / "...to **trusted computing centers (AGG)** that subsequently
> execute MTT."
- Verdict: ✅ MATE is centralized. (AerialTrust, by contrast, states "each agent performs its own
  local trust estimation process" — hence our parenthetical.)

**ABSENCE checks (our negative claims), verified by full-text sweep:**
| our claim | evidence |
|---|---|
| no noise-harm-regime characterization | MATE *accommodates* noise (longitudinal filtering) but never shows a consistency check becoming destructive; no noise-magnitude sweep; "ranging noise" 0 hits |
| no camouflage-in-noise fabrication | "camouflage" **0 hits** |
| no closed-loop navigation metric | "closed-loop" 0 hits; "success rate" 0 hits; "navigation" **1 hit — a REFERENCE TITLE** (Bar-Shalom, *Estimation with applications to tracking and navigation*). Metrics are P/R/F1, OSPA, trust accuracy. |

**FINDINGS on this passage (both APPLIED 2026-07-11):**
- **catch #18 — "their trust protects a SURVEILLANCE picture" was WRONG.** The sentence covers the
  whole line: TruPercept = autonomous **driving**; MATE = **smart city** SA; only AerialTrust is
  surveillance/ISR. This is the SAME error class as catch #8 (where we wrongly put TruPercept "in
  surveillance settings" in the baseline paragraph) — it had survived in this second passage.
  **Fixed to:** "their trust protects a shared perception picture, whether for driving, a smart city,
  or aerial surveillance."
- **catch #19 — strengthening (opportunity, not error):** our text credited only TruPercept with
  central trust aggregation. The full read shows **MATE is centralized too** ("centralized MTT",
  "trusted computing centers (AGG)"), which sharpens our decentralization contrast. Added — with an
  honest parenthetical that the aerial extension *does* distribute, so we do not overclaim the line.

---

# Metadata (bibliography)
**WE CITE (`refs.bib`):** Hallyburton & Pajic, "Security-Aware Sensor Fusion with MATE: the
Multi-Agent Trust Estimator", Proc. 2025 ACM SIGSAC CCS; note arXiv:2503.04954.
**SOURCE:** arXiv v1 6 Mar 2025 (no acceptance note on the arXiv page); CCS 2025 venue confirmed via
ACM DL (doi 10.1145/3719027.3765193), published 22 Nov 2025 — **verified in-browser by Srinivasa**.
**Verdict:** ✅.

---

# Context noted (NOT cited)
- MATE reports ~94% reduction in adversary-driven OSPA error and detects compromised agents with
  "near 90% accuracy" — useful if we ever need to characterize the family's detection performance.
- MATE explicitly criticizes Byzantine models for "requiring unrealistic perfect perception" — the
  problem our §5.6 destructive-filter result quantifies. Independent motivation for our finding.

---

# Correction history on this reference
1. **First audit (2026-07-09):** killed a FALSE negative claim — we had written that this line does
   not handle sensor noise; MATE explicitly does ("longitudinal filtering"). Passage reworded.
2. [x] **catch #18 (2026-07-11):** "their trust protects a surveillance picture" — wrong for
   TruPercept (driving) and MATE (smart city). Fixed to "a shared perception picture, whether for
   driving, a smart city, or aerial surveillance."
3. [x] **catch #19 (2026-07-11):** added MATE's central computing centre to the decentralization
   contrast (with the honest aerial-extension parenthetical).
4. [x] **catch #20 (2026-07-11):** the central-architecture sentence named TruPercept, MATE and the
   aerial extension while making specific factual claims about all three, with NO citations
   attached. Citations added (`\cite{trupercept2020}`, `\cite{mate2025}`, `\cite{aerialtrust2025}`).
   Found by a full citation-ledger audit (17 cited <-> 17 in refs.bib, 0 broken, 0 orphans).
5. [ ] **OPEN — same problem in the baseline paragraph (related.tex:157-158):** "CAD, PRBI, and GCP
   operate on the deep feature maps ... while TruPercept, MATE, and its aerial extension score
   object detections and tracks" names SIX papers with specific claims and NO citations in the
   sentence (CAD/PRBI/GCP are uncited anywhere in that paragraph). **Fold the citation fix into the
   held 15b pass** (after CAD is read), so the clause gets its wording AND its citations in one go.
6. [ ] **15b still HELD:** the baseline sentence's CAD/PRBI/GCP half ("deep feature maps", "detection
   accuracy") — fix after CAD is read. MATE's half of that sentence is verified correct.
