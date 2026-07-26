# 3D-TC2 — paired claim/evidence sheet (full read, 2026-07-17)

## STATUS: ⏳ CLAUDE'S AUDIT DONE — **AWAITING SRINIVASA'S INDEPENDENT REVIEW**
Full 6-page read (arXiv:2106.07833v1 = MAISP '21 workshop paper). **No catches — our single
sentence verifies phrase by phrase.** One optional wording polish offered (not required).
Their §4.4 limitation is a strong corroboration of our persistent-fabrication argument.
Closed only after Srinivasa's own audit.

**The paper:** Chengzeng You, Zhongyuan Hau, Soteris Demetriou (Imperial College London),
*"Temporal Consistency Checks to Detect LiDAR Spoofing Attacks on Autonomous Vehicle
Perception"*, 1st Workshop on Security and Privacy for Mobile AI (MAISP '21), ACM, 2021.
arXiv:2106.07833v1. ⚠ "3D-TC2" is the METHOD name, not the title — refs.bib already notes
this (corrected 2026-07-08) and the entry is exact ✓ (title, all 3 authors, MAISP venue,
arXiv ID vs. PDF stamp). PDF: `Phase_CD/Research paper/3D-TC2.pdf` (6 pages).

**What the paper does (their own words):** *"we explore the use of motion as a physical
invariant of genuine objects for detecting such attacks. Based on this, we propose a general
methodology, 3D Temporal Consistency Check (3D-TC2), which leverages spatio-temporal
information from motion prediction to verify objects detected by 3D Object Detectors"*
(Abstract). Setting = ONE autonomous vehicle's own LiDAR; attacker = laser-pulse spoofing
that injects ≤200 fake points to elicit ghost objects 5–8 m in front of the ego-vehicle.
Pipeline: MotionNet (deep model) predicts the current frame from the K=20 previous frames →
align with PointPillars/SECOND detections on a BEV grid → Cell-match Counting Strategy: a
detected box whose majority cell category is "background" (no motion history) is flagged.
*"objects (and their motion trajectory) should be consistent across consecutive 3D LiDAR
scenes and this temporal consistency would be disturbed when an adversary introduces a fake
object"* (§1). Results: DSR >98%, recall ~91–92% for spoofed Cars (worse for
pedestrians/cyclists — MotionNet classification limits); 41 Hz real-time; nuScenes mini,
362 attacked key frames, SINGLE-FRAME injection only.

---

## USE 1 (the ONLY use) — related.tex ~lines 111–116
**WE WRITE (verbatim):** "A separate line detects LiDAR spoofing against a \emph{single}
vehicle by exploiting temporal structure in its own sensor stream, e.g.\ motion-induced
consistency in 3D-TC2~\cite{tc2_2021} and point-level temporal consistency in
ADoPT~\cite{adopt2023}. These methods test whether observations from a single sensor remain
temporally self-consistent."

**THEY WROTE, phrase by phrase:**
- "detects LiDAR spoofing against a single vehicle" ✓ — threat model §3.1: spoofing the
  ego-vehicle's LiDAR returns, ghost objects *"5m-8m in front of the ego-vehicle"*; no
  inter-vehicle communication anywhere in the paper.
- "exploiting temporal structure in its own sensor stream" ✓ — *"leverages spatio-temporal
  information from motion prediction"* (Abstract); MotionNet consumes *"a sequence of
  consecutive scenes (3D point-clouds)"* from the same ego LiDAR (§3.3).
- "motion-induced consistency" ✓ — *"motion as a physical invariant of genuine objects"*
  (Abstract); *"objects (and their motion trajectory) should be consistent across
  consecutive 3D LiDAR scenes"* (§1); *"Our work is the first to propose motion as a
  physical invariant for 3D objects which it leverages to perform temporal consistency
  checks"* (§2). Our compression (genuine motion induces cross-frame consistency; an
  injected object has no history) is faithful. *Optional polish, Srinivasa's call:*
  "motion-prediction consistency" would name the mechanism even more literally; not
  required — "motion-induced" tracks their "motion as a physical invariant".
- "test whether observations from a single sensor remain temporally self-consistent" ✓ —
  the whole CMCS
  check compares the ego detector's current frame against a prediction built from the ego
  sensor's own previous frames (§3.2–3.3); nothing external is consulted.

**VERDICT: ✅ VERIFIED — no change needed.**

---

## Corroborations noted (useful under reviewer fire; no manuscript change)
- **Their own §4.4 admission = our persistent-fabrication point:** *"if the hidden object is
  temporally consistent (i.e. an adversarial object is placed on the road as the ego-vehicle
  approaches it), the approach will fail to detect such object."* And future work: *"consider
  a stronger adversary that is able to perform injection into continuous frames (temporal
  attacks) and study the robustness of the 3D-TC2 approach"* — i.e. they evaluated
  SINGLE-frame injection only; the detection signal is abrupt appearance vs. the scene's own
  past (spoofed box has *"no 'history' from the previous frames"*, §3.3). Our camouflage
  phantom is broadcast persistently from episode start → temporally self-consistent → this
  whole check class (like PRBI's Jaccard drop) keys on the wrong reference signal. Our
  related.tex already draws exactly this distinction WITHOUT claiming 3D-TC2 fails on our
  attack — correct posture, keep it.
- Their detection degrades on small objects (pedestrian DSR 47–57%) purely from the
  prediction model's limits — supports our "hand-designed statistical test needs no learned
  component" framing but we don't cite it for that; noted only.

## Second-order sweep (standing rule) — FULL 14-ref bibliography title scan done 2026-07-17
**Zero new candidates.** The refs are: LiDAR spoofing attacks (Petit '15 relay, Shin '17
Illusion-and-Dazzle, Cao '19 CCS, Cao '21 moving-target tracking, Sun USENIX '20 black-box +
CARLO/SVF), single-vehicle ghost defenses (Hau Shadow-Catcher, Hau Object-Removal-Attacks,
MSF-ADV), Hau & Lupu '19 (false-data injection in wireless SENSOR networks via correlations —
message layer, no perception exchange, out of family), AdVIT (video temporal consistency —
methodology), detectors/datasets (PointPillars, SECOND, MotionNet, nuScenes). All
single-vehicle sensor-attack line — the family our related.tex already brackets via
3D-TC2/ADoPT as its entry point; no collaborative-perception or multi-agent-trust member.

## Srinivasa's verification checklist (page pointers, arXiv v1)
| # | what to check | where in PDF |
|---|---|---|
| 1 | "motion as a physical invariant" + "temporal consistency" (our phrase source) | p.1 Abstract + §1 end |
| 2 | single ego-vehicle threat model, ghost objects 5–8 m in front, ≤200 spoofed points | p.2 §3.1 |
| 3 | mechanism = MotionNet prediction from own previous frames vs. current detection (CMCS) | p.2–3 §3.2–3.3 |
| 4 | "if the hidden object is temporally consistent … the approach will fail" + single-frame-only evaluation | p.5–6 §4.4 + §5 future work |

## Bookkeeping
- refs.bib `tc2_2021`: title exact ✓, authors You/Hau/Demetriou ✓, MAISP '21 ✓ (published
  workshop paper — NOT in the arXiv-preprint venue-recheck class), arXiv:2106.07833 ✓.
- No catches; no manuscript edits from this audit.
