# GCP — paired claim/evidence sheet (re-audit, 2026-07-11)

Full 15-page re-read done. Format is consistent throughout: **WE WRITE** = exact current `.tex`
sentence · **THEY WROTE** = verbatim passage(s) from `Phase_CD/Research paper/GCP.pdf` with section ·
**Verdict/notes**.

Paper: Tao, Hu, Hu, An, Cao, Fang — "GCP: Guarded Collaborative Perception with Spatial-Temporal
Aware Malicious Agent Detection", IEEE TDSC (accepted / to appear; arXiv:2501.02450 v2, 26 Apr 2026).
Ligature note applies (fi/fl merged in the PDF; search short fragments).

GCP is cited in **two places** in our manuscript (USE 1, USE 2). Every descriptive phrase inside
those two sentences is verified below as its own paired block.

## Essential 3-layer distinction (the source of the one finding)
- **Fusion protected:** intermediate FEATURE maps (V2VNet). §I: "feature-level fusion, where the
  collaborative CAVs send an intermediate representation of deep neural network models."
- **Attack (BAC):** perturbs the FEATURE map. §III.C: "the malicious CAV incorporates the optimized
  perturbation into its intermediate BEV feature before transmission."
- **GCP's own DETECTOR:** reads DECODED DETECTION OUTPUTS (bounding boxes, confidence maps, BEV
  flows). §II.C: "output-level malicious agent detection through hypothesis-and-verification
  frameworks."
=> GCP defends an intermediate-feature-fusion collaborative perception system, but its
   malicious-agent detection operates primarily on decoded perception outputs (bounding boxes,
   confidence maps, and BEV flows) rather than directly analyzing or modifying feature embeddings.

---

# USE 1 — Related Work, defenses-for-feature-fusion sentence

**WE WRITE (`sections/related.tex` lines 18–31) — 🔄 RESYNCED 2026-07-28, re-copied from the
live file:**
> In feature-fusion collaborative perception, GCP~\cite{gcp2025} defends against malicious agents
> by augmenting single-shot spatial-consistency checks with temporal motion-flow reconstruction
> to expose blind-area attacks; MADE~\cite{made2024} detects and removes malicious agents through
> hypothesis tests on the consistency between each inspected agent and the ego agent, with
> statistical false-positive control; and CoDynTrust~\cite{codyntrust2025} addresses the benign
> counterpart by weighting intermediate feature contributions according to their estimated
> uncertainty, thereby mitigating temporal asynchrony rather than adversarial behaviour; and
> ROBOSAC~\cite{robosac2023} rejects adversarial feature-map perturbations by sampling subsets of
> teammates until the collaborative output reaches consensus with the ego's own perception,
> falling back to ego-only perception when no consensus is found. **All four** are evaluated
> using Average Precision (AP) on vehicular benchmarks.

> ⚠️ **DRIFT NOTE (2026-07-28) — the worst of the six.** This block previously quoted a sentence
> that **no longer exists in any form**: *"Other defenses for feature-fusion collaborative
> perception include CoDynTrust…, and GCP…; **both** are evaluated using Average Precision."*
> The sentence has since been **restructured from two papers to four** (MADE and ROBOSAC added,
> "both" → "All four", opening clause rewritten).
>
> ✅ **Every GCP-specific phrase survived the rewrite unchanged** — *"augmenting single-shot
> spatial-consistency checks with temporal motion-flow reconstruction to expose blind-area
> attacks"* and the AP-metric clause are word-for-word intact. **The four phrase-level
> verifications below therefore still hold**; only the surrounding sentence changed.
>
> 🔑 **Lesson:** a `WE WRITE` block that quotes a *shared* sentence goes stale whenever **any**
> co-cited paper is added or removed — even when nothing about *this* paper changed.

The four descriptive phrases about GCP, each paired with its source:

**Phrase 1 — "single-shot spatial-consistency checks"**
- THEY WROTE (§IV.A): "GCP performs joint spatial-temporal consistency verification through two key
  components: (1) a confidence-scaled spatial concordance loss that adaptively evaluates detection
  consistency..."
- THEY WROTE (§IV.B): "Typically, when temporal context is not applicable, a spatial anomaly can be
  assumed to be detected when L_csc exceeds a threshold." (the single-shot / single-slot check)
- Verdict: ✅ exact.

**Phrase 2 — "temporal motion-flow reconstruction"**
- THEY WROTE (Abstract): "...simultaneously examining temporal anomalies by reconstructing
  historical bird's eye view motion flows in low-confidence regions."
- THEY WROTE (§IV.D): "there are three key components of BEV flow reconstruction: LSTM encoder, LSTM
  decoder, and temporal reconstruction loss estimator."
- Verdict: ✅ exact.

**Phrase 3 — "blind-area attacks"** (was "blind-area fabrications" — corrected 2026-07-11)
- THEY WROTE (§I, contributions): "We reveal a novel attack, dubbed as blind area confusion (BAC)
  attack, ... by generating subtle and dangerous perturbation in an ego CAV's less confident areas."
- Verdict: ✅ NOW matches their terminology. "blind area" + "attack" are both their words (BAC =
  Blind Area Confusion attack; they say attack / perturbation / malicious message).
- SELF-AUDIT ERROR CAUGHT (Srinivasa): the earlier version wrote "blind-area FABRICATIONS" and this
  block wrongly marked it "exact". "Fabrications" is OUR term (we use it for our own phantom-obstacle
  attack); GCP never says fabrication/fabricated. Rule: describe another paper in ITS terminology.
  Fixed to "blind-area attacks" in related.tex + here.

**Phrase 4 — "evaluated using Average Precision (AP) on vehicular benchmarks"** (was "by detection
accuracy" — corrected 2026-07-11)
- THEY WROTE (§V.A): "Evaluation metrics include Average Precision (AP@0.5, AP@0.7) for accuracy and
  Frames Per Second (FPS) for efficiency."
- THEY WROTE (Abstract): "achieving up to 34.69% improvements in AP@0.5..."
- THEY WROTE (§I): setting is "connected and autonomous vehicles (CAVs)"; §V fusion = "V2VNet".
- Verdict: ✅ now uses their exact metric name.
- AMBIGUITY FIX (Srinivasa): "detection accuracy" was ambiguous — could read as OBJECT-detection
  accuracy (AP, what GCP reports) OR MALICIOUS-AGENT-detection accuracy (which GCP does NOT report in
  that phrase). Changed to "Average Precision (AP)" — GCP's own metric name, unambiguous, and fair
  for both GCP and CoDynTrust without over-specifying CoDynTrust's exact IoU thresholds (only
  abstract-checked). NOTE: the SAME ambiguous phrase "score detection accuracy" sits in USE 2
  (baseline paragraph) — fold this same fix into the held 15b CAD pass.

**FINDING on this sentence (catch #15a — FIXED):** the earlier version headed this "Feature-level
trust modulation ... GCP", which was IMPRECISE — CoDynTrust genuinely weights feature contributions
(title: "Dynamic Feature Trust Modulus"), but GCP does OUTPUT-level detection (§II.C), not feature
modulation. Regrouped by SETTING ("defenses for feature-fusion CP"), and "both optimize detection
accuracy" -> "both are evaluated by detection accuracy" (they don't optimize accuracy directly;
they detect malicious agents and report AP). Applied 2026-07-11.

---

# USE 2 — Related Work, baseline paragraph

**WE WROTE (`sections/related.tex`) — SUPERSEDED 2026-07-17 (fix 15b applied; current verbatim
text + full evidence in `REFERENCE_EVIDENCE_CAD.md` USE 2):**
> ...CAD, PRBI, and GCP operate on the deep feature maps of vehicular detection stacks and score
> detection accuracy, while TruPercept, MATE, and its aerial extension score object detections and
> tracks; none is designed to operate directly on the geometric obstacle claims exchanged by our
> agents, and none produces the navigation-success outcome we measure...

**THEY WROTE (§II.C):** "primarily focusing on output-level malicious agent detection through
hypothesis-and-verification frameworks." (GCP is in this output-level family.)
**THEY WROTE (§IV.B / IV.C-D):** CSCLoss matches ego's DETECTED bounding boxes vs collaborative ones
(Kuhn-Munkres); temporal module reconstructs BEV FLOW of bounding boxes. => detector reads
DETECTIONS, not raw feature maps.

**Verdict:** the "score detection accuracy" half is ✅ (AP metrics). The "operate on the deep
feature maps" half is 🟡 IMPRECISE for GCP — its detector reads decoded detection OUTPUTS. (Same is
loosely true of PRBI, whose Jaccard detector reads detection SETS.) The FUSION and the ATTACK are
feature-level; the DEFENSE is output-level.

**FINDING (catch #15b — HELD for CAD):** do not edit piecemeal — the sentence also asserts this
about **CAD, which is still UNAUDITED**. Fix the whole clause in ONE pass after CAD.pdf is read.
Proposed target: "CAD, PRBI, and GCP defend feature-fusion vehicular pipelines and are scored by
detection accuracy (AP), while..." — re-verify the CAD portion against CAD's full text before
applying.

---

# Metadata (bibliography)

**WE CITE (`refs.bib`):** IEEE Transactions on Dependable and Secure Computing, accepted / to
appear, year 2026; note "arXiv:2501.02450".
**SOURCE:** arXiv page — v1 5 Jan 2025, v2 26 Apr 2026, cs.CV; Comments field "Accepted by IEEE
TDSC" (no year/pages on the journal side yet).
**Verdict:** ✅ (year corrected 2025 -> 2026/to-appear in the first audit — Srinivasa's catch).

---

# Context noted (NOT cited — for our own differentiation records)
- GCP evaluates INTERMITTENT attack modes (§V: Random / Poisson / Susceptible-Infectious), like
  PRBI's intermittent schedules; BAC is designed to bypass the SINGLE-SHOT detector family (a
  defense-aware attack against that family, not against GCP itself).
- No sensor-ranging-noise regime; no navigation/closed-loop metric; no camouflage-in-noise.
  ("noise" in the paper = adversarial perturbation + Kalman process noise, not sensor ranging
  noise.) => consistent with our differentiation; nothing to change.

---

# Correction history on this reference
1. Year/venue: TDSC "2025" -> "2026, accepted/to appear" (Srinivasa's catch, first audit).
2. [x] APPLIED 2026-07-11 — catch #15a: USE 1 regrouped (GCP no longer called "feature-level trust
   modulation"; "optimize" -> "evaluated by"). Every descriptive phrase verbatim-verified above.
3. [x] APPLIED 2026-07-17 — catch #15b: whole clause rewritten in one pass after the CAD full
   read confirmed the claim was WRONG for CAD too (occupancy maps via RANSAC/DBSCAN/convex hulls,
   scored by TPR/FPR — not deep feature maps, not detection accuracy). New wording: "CAD, PRBI,
   and GCP defend the fused perception pipelines of vehicular detection stacks and are evaluated
   by detection-level metrics (anomaly-detection rates or average precision)". Evidence + the
   applied text: `REFERENCE_EVIDENCE_CAD.md` USE 2.
