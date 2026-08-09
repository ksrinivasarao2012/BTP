# REJECTION RISK REGISTER — RAS submission

Honest self-review: attack our own paper harder than a reviewer will. Target venue: Elsevier *Robotics
and Autonomous Systems*. Each risk = likelihood it sinks the paper + fix type (**framing** = cheap wording;
**experiment** = new runs; **retrain** = weeks). Status updated as we address each.

Severity: 🔴 serious (probable reject reason) · 🟠 moderate (major-revision request) · 🟡 minor (rebuttable).

---

## 🔴 R1 — No empirical comparison against existing defenses  [MOST LIKELY REJECT REASON]
**The objection:** we compare only our own variants (naive → robust → temporal). We never run CAD, PRBI,
or TruPercept on our benchmark and beat them. Reviewers routinely demand baseline comparison; ablations are
not baselines.
**Fix type:** experiment (implement 1–2 baselines) OR ironclad non-applicability argument (framing).
**Our argument (draft):** CAD needs a benign vehicle observing the attacked region + feature-level fusion;
PRBI is CAV detection-AP, no navigation loop, no ranging-noise regime; TruPercept scores object detections,
not geometric obstacle claims. But an argument alone may not satisfy a tough reviewer.
**Decision (2026-07-08):** [x] **ARGUE-ONLY.** Do NOT implement a baseline now. Write the full
non-applicability argument into Related Work + Discussion. Implement a baseline ONLY if a reviewer demands
it (held in reserve for rebuttal).
**Status: ✅ CLOSED 2026-07-09 — argue-only paragraph WRITTEN** (related.tex, final paragraph 'On baseline comparison'): representational non-transplantability argued per-method + the key reframe — our naive/robust filters ARE the native implementation of the consistency-family primitive (MATE/CAD lineage), so the internal comparison IS the family baseline. Real-baseline implementation stays in reserve for rebuttal.

## 🔴 R2 — Simplified perception model ("this isn't collaborative perception")
**The objection:** real collab perception fuses deep features / detections from point clouds or images. Ours
= ground-truth circular obstacles + Gaussian noise, shared as position lists. A CAV/perception reviewer may
call the abstraction too far from reality.
**Fix type:** framing (expensive to fully fix). Position as an *abstract model that isolates the trust/fusion
question*; lean on the robotics (not CAV) framing where circular-obstacle navigation is standard; state the
abstraction explicitly as a limitation.
**Status: ✅ CLOSED 2026-07-09 — 'Scope of the abstraction' paragraph added to methods.tex sec 3.1**: object-level modelling argued as deliberate (isolates the fusion/trust layer, like MTT reasons over detections not pixels); below-level phenomena explicitly scoped out to Discussion; offset-bias statistic noted as defined for any system that can associate claims with own views.

## 🔴 R3 — Idealized communication threatens the CORE mechanism  [MOST DANGEROUS UNKNOWN]
**The objection:** temporal filter needs >=20 frames of a neighbour's broadcasts to reach a verdict; we
assume lossless, zero-latency comm within 10 m. Under packet loss / delay the evidence accrues slower or
breaks. Reviewer: "does the headline result survive 20% packet loss?" — we don't currently know.
**Fix type:** experiment (cheap-ish): drop each broadcast with prob p in {0.1,0.2,0.3}, re-run temporal at
sigma=0.6 camouflage f=2, report recovery/recall vs p.
**Why do it:** if temporal survives moderate loss, it STRENGTHENS the paper; if it degrades gracefully, we
disclose honestly. Either way removes the scariest reviewer question.
**Status: ✅ CLOSED 2026-07-09 — TEMPORAL SURVIVES PACKET LOSS (k=2, 500 maps, 7h46m run).**
sigma=0.6 camouflage recovery vs loss p: **p=0 +12.3 [9.8,15.0] · p=0.1 +12.7 [10.1,15.3] · p=0.2 +11.2
[8.9,13.5] · p=0.3 +9.5 [7.1,11.8]** — all CIs well above 0; graceful ~1 pp decline per +0.1 loss. Recall
sags only 0.68→0.65 at 30% loss; precision *rises* 0.82→0.88 (fewer, cleaner verdicts); no-harm ~0 at every
(p, sigma) cell. Same pattern at all noise levels. Raw: `results_027/comm_loss_camouflage_500_k2.txt`.
**This converts the scariest unknown into a strength — write it into Results as the realism rebuttal.**
**SCOPE COMPLETE 2026-07-10: k=1, k=2, AND k=3 all done** (`*_k1.txt`, `comm_loss_camouflage_500_k2.txt`,
`*_k3.txt`). At 30% packet loss, recovery = +6.9 (k=1) / +9.5 (k=2) / +13.2 (k=3) — all CIs>0. The
comm-loss and density robustness hold at EVERY traitor count; no follow-up runs remain.


## 🔴 R13 — TruPercept's plausibility checker defeats the WALL attack (found 2026-07-09, full-text read)
**The objection:** TruPercept (IEEE IV 2020) already kills open-space phantoms with a frustum-cull
plausibility check: an object with no LiDAR returns in front but returns behind is provably absent. A
reviewer who knows it asks: "a 2019 method removes your wall attack — why does this paper matter?"
**Why we survive (argued, NOT proven — keep the wording defensible):**
1. Geometric plausibility tests derive power from rays traversing EMPTY SPACE at the claimed location. A
   camouflage phantom flush against a real obstacle coincides with returns the verifier genuinely receives,
   so such a test has little to discriminate on. ⚠️ **They never evaluate camouflage; we have never run their
   checker. Do NOT write 'defeats it by construction' / 'invisible to it' / 'no test can find it'.**
   Defensible phrasing only: *'unlikely to reject phantoms whose claimed geometry coincides with real
   returns'*, *'its effectiveness depends on rays passing through empty space, which camouflage avoids'*,
   *'not directly addressed by the plausibility checker'*. (Srinivasa's catch, 2026-07-10.)
2. Under ranging noise the residual offset shrinks below the tolerance the verifier must grant honest
   neighbours → a geometric test has correspondingly less to act on.
3. ⚠️ **CORRECTED 2026-07-10 (Srinivasa):** do NOT write 'their check requires raw point clouds' — TruPercept
   is LATE fusion; it exchanges object DETECTIONS, not raw data. The plausibility checker operates on the
   **verifier's own local LiDAR point cloud** (every vehicle already has one). Accurate phrasing:
   *'the plausibility checker requires access to the verifier's local point-cloud geometry'*. The real
   architectural difference from us: our agents verify against a **48-ray range profile / object-level
   sensing model**, not a dense point cloud, so a frustum-cull test is not directly available to them —
   state it that way if we state it at all.
4. Their trust is aggregated on a CENTRAL SERVER; a swarm has no infrastructure — ours is pairwise/local.
**Status: ✅ ADDRESSED 2026-07-09 — pre-empted in the manuscript.** `related.tex` now cites the plausibility
checker explicitly, explains why the wall attack is comparatively easy, and shows camouflage removes the
evidence by construction ("our temporal test does not seek a stronger *spatial* contradiction, which is
unavailable; it accumulates a *statistical* one over time"). Also added: central-vs-pairwise trust
difference. **Net: the paper's own tool is used to sharpen why camouflage is the hard case.**

## 🟢 SUPPORT FOUND — TruPercept strengthens us (same read)
- Their headline NEGATIVE result: *"none of the tested methods improve the perceptual accuracy by a
  meaningful margin over local perception"* — high-confidence false detections poisoned fusion; malicious
  agents "decrease performance significantly"; they note "a weakness in the model towards coordinated
  attacks." → cited in `introduction.tex` as evidence the problem is real and unsolved.
- Their evasion finding: *"trust value for unreliable vehicles is not significantly different than
  trustworthy vehicles… behaviours which mostly present true detections will be able to fool the current
  system."* → the camouflage principle, published in 2019. Cited in `discussion.tex` (new
  "verifiability boundary" subsection, paired with AerialTrust's spatial blind-spot admission).
- Their visibility weight (LiDAR-point-count Φ) = our positioned-to-see gate → reinforces R1 (our
  naive/robust filter IS the family's primitive).

---

## 🟠 R4 — Dijkstra routed-heading crutch (autonomy concern)
**The objection:** the policy is fed a globally-planned goal heading (obs[2:4]), so it is not doing
autonomous global navigation; this also dampens attack severity (reported drops are a lower bound).
**Fix type:** framing now ("external mission planner supplies routed waypoints; policy does local control +
collision avoidance" — already in Methods/Discussion); planner-free version = retrain (weeks), the true fix.
**Status:** DISCLOSED. Framing in place. Full fix deferred to future work.

## 🟠 R5 — Novelty vs PRBI (CVPR 2026, temporal consistency for lying vehicles)
**The objection:** PRBI also uses temporal consistency to catch lying vehicles in cooperative perception;
a skimming reviewer sees "already done."
**Our differentiators (must be airtight + early):** closed-loop navigation metric (not detection-AP);
explicit ranging-noise regime where single-frame checks become destructive; the offset-*bias* statistic
(zero-mean honest vs persistent lie), not generic frame consistency; adaptive-attacker stealth/harm bind.
**Fix type:** framing — sharpen differentiation, surface it in the Introduction, not only Related Work.
**Status: ✅ SUBSTANTIALLY CLOSED 2026-07-09 — full-text audit of PRBI (15 pp) done.**
Verified against their PDF: "noise" 0 hits, "navigation" 0 hits → claims 1–2 bulletproof; claim 3 refined
(they test intermittent injection, NOT a defense-aware optimizing attacker) — `related.tex` reworded.
NEW differentiator added from the read: PRBI's referee is FRAME-TO-FRAME similarity (detects disruption);
our persistent camouflage phantom is temporally self-consistent and would likely leave that signal intact —
their mechanism plausibly cannot even see our attack class. Sentence added to `related.tex` (hedged).
Their attack is bounded feature-map perturbation (PGD/C&W) — different threat type entirely.
**FULLY CLOSED 2026-07-09:** the disruption-vs-persistent-fabrication differentiation is now ALSO in the
Introduction (one sentence in the contribution paragraph, cross-ref to Related Work).

## 🟠 R6 — Attack depends on MIN-fusion ("self-inflicted vulnerability")
**The objection:** a phantom wins only because fusion takes the per-ray minimum; use confidence-weighted or
averaging fusion and the attack weakens — so is the problem self-inflicted?
**Fix type:** framing + optional experiment. Justify MIN as the *safe* conservative choice (respect
any teammate's evidence of a nearby obstacle); optionally show averaging fusion is unsafe under dropout
(trades safety for attack-resistance).
**Status: ✅ CLOSED 2026-07-10 — design-space paragraph added to methods.tex §3.3:** MIN acknowledged as one
point in a design space; averaging/confidence-weighting would dilute a fabricated return but equally dilute
a single TRUE near-obstacle detection (arithmetic fact, no empirical claim) → 'we adopt the conservative
rule and defend it... the vulnerability studied below is the price of that safety property, not an artifact
of an eccentric choice.' Intro 'as is common' overclaim also removed (E8). Optional averaging-under-
dropout experiment stays in reserve for rebuttal.

## 🟠 R7 — No scaling / generalization study
**The objection:** one arena size, 10 drones, density 0.27. Does it hold at 20 drones / other densities?
**Fix type:** experiment.
**Decision (2026-07-08):**
- [x] **DO the density-generalization sweep** (keep 10 drones, vary density) — cheap, no retrain.
- [x] **DROP 20-drone scaling** — requires retraining a 10-drone model, weeks of work. NOT doing now.
  Held in reserve; only revisit if a reviewer specifically demands agent-count scaling.
**Status: ✅ DENSITY CLOSED 2026-07-09 — GENERALIZES (k=2, sigma=0.6 camouflage, 500 maps).**
Recovery vs density: **0.20 +12.3 [9.8,14.8] · 0.24 +12.1 [9.4,14.7] · 0.27 +12.3 [9.8,15.0] · 0.30 +8.8
[6.4,11.2]** — flat +12 across 0.20–0.27, still solidly positive at 0.30 (harder maps shrink the ceiling for
everyone). No-harm ~0 everywhere; recall 0.78→0.61 as clutter rises (denser fields make camouflage easier to
hide) while precision rises 0.81→0.85. Not an artifact of 0.27. Raw:
`results_027/density_sweep_camouflage_500_k2.txt`. Drone-count scaling remains DEFERRED.

---

## 🟡 R8 — Low absolute success (86% -> 53%) reads as a weak system on a skim
**Fix:** framing — make the calibration rationale (stacked stresses: dropout + density 0.27 + noise-robust
model; same base for all arms so comparisons are fair) PROMINENT, not buried. Already argued in
RESULTS_027_CAMERA_READY "why base ~86%".
**Status: ✅ CLOSED 2026-07-09 — 'Reading the baselines' paragraph added at the top of Results** (before
the vulnerability subsection): stacked stresses named, 86->53.4 ceiling explained as navigation-information
limit, same-ceiling-for-every-arm fairness stated explicitly.

## 🟡 R9 — Camouflage attacker realism (needs to know real obstacle positions)
**Fix:** framing — an insider that senses knows nearby real obstacles; state this attacker capability
explicitly and justify it.
**Status:** OPEN — add one sentence to threat model.

## 🟡 R10 — Neighbour-level gating discards honest data
**Fix:** already disclosed as future work (obstacle-level gating). Keep.
**Status:** DISCLOSED.

## 🟡 R11 — Hand-coded trust reads as "just a threshold"
**Fix:** framing — sell the *characterization* (naive-destructive-under-noise + the offset-bias mechanism +
the bind) as the contribution, and the finding that no learned trust is needed as a positive result.
**Status:** in place in Intro/Discussion; keep prominent.

## 🟡 R12 — AI-declaration invites prose scrutiny
**Fix:** genuine human rewriting in the author's voice; author must own every sentence (also the
declaration's own requirement). Not machine-obvious phrasing.
**Status:** ONGOING — author read-through pending.

---

## PLAN OF RECORD (2026-07-08): PATH B
**Doing now:** framing changes (R1 argue-only, R5, R2, R8, R9, R11) + R3 comm-loss experiment
+ R7 density-generalization sweep.
**Deferred / held for rebuttal (NOT doing now):** R1 real-baseline implementation; R7 20-drone scaling
(needs retrain); R4 planner-free retrain; R6 averaging-fusion experiment (framing only for now).

### Task order
1. **[R3] Build + run comm-loss experiment** (env broadcast-drop hook + eval + overnight run). IN PROGRESS.
2. **[R7] Build + run density-generalization sweep** (same night's compute).
3. **[R5] Sharpen PRBI differentiation** in the Introduction.
4. **[R2/R8] Add "scope of abstraction" + prominent base-calibration** paragraphs.
5. **[R1] Write the baseline non-applicability argument** into Related Work + Discussion.
6. **[R9/R11/R6] One-sentence additions** (attacker capability; contribution framing; MIN-fusion rationale).
7. Fold R3 + R7 results into Results + REJECTION_RISKS status once runs land.

## Honest overall read
Methodologically sound and statistically strong (500 maps + paired CIs) — real and uncommon. The two classic
"revise-or-reject" exposures are **R1 (no baselines)** and **R2/R3 (realism: idealized comm + simplified
perception)**. Closing R3 and deciding R1 before submission is how a "major revision" becomes a "minor
revision."
