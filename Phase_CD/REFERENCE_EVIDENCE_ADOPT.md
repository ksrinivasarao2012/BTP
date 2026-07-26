# ADoPT — paired claim/evidence sheet (full read, 2026-07-17)

## STATUS: ✅ CLOSED (2026-07-26) — verified independently by Srinivasa
Full 17-page read (arXiv:2310.14504v1; BMVC 2023). **No catches — our phrase appears
literally in the paper title.** Two strong corroborations found: (1) their failure mode IS the camouflage
placement; (2) single-frame injection only, like 3D-TC2. Closed only after Srinivasa's own
audit.

**The paper:** Minkyoung Cho, Yulong Cao, Zixiang Zhou, Z. Morley Mao (Univ. of Michigan /
NVIDIA Research), *"ADoPT: LiDAR Spoofing Attack Detection Based on Point-Level Temporal
Consistency"*, BMVC 2023, arXiv:2310.14504v1. PDF: `Phase_CD/Research paper/ADoPT.pdf`
(17 pages incl. appendices).

**What the paper does (their own words):** *"we propose a novel framework, named ADoPT
(Anomaly Detection based on Point-level Temporal consistency), which quantitatively
measures temporal consistency across consecutive frames and identifies abnormal objects
based on the coherency of point clusters"* (Abstract). Single ego-vehicle setting; attacker
injects fake points (dense ≤200 pts / sparse ≤64 pts) into the ego LiDAR. Mechanism:
coherence-enhanced scene-flow estimation (NSFP-style MLP optimized at runtime + DBSCAN
coherence loss) warps L=10 historical frames into a synthesis; merge with incoming frame;
DBSCAN clusters made ONLY of incoming-frame points (no synthesis support) = fabricated
objects. Results on nuScenes: FPR <10%, TPR >85% (e.g. dense: FPR 4.5%, TPR 95–98%),
beating CARLO and 3D-TC2 especially on small objects. Raw-point-level → perception-model-
agnostic (no bounding-box dependence).

---

## USE 1 (the ONLY use) — related.tex ~lines 111–116 (shared sentence with 3D-TC2)
**WE WRITE (verbatim):** "A separate line detects LiDAR spoofing against a \emph{single}
vehicle by exploiting temporal structure in its own sensor stream, e.g.\ motion-induced
consistency in 3D-TC2~\cite{tc2_2021} and point-level temporal consistency in
ADoPT~\cite{adopt2023}. These methods test whether observations from a single sensor remain
temporally self-consistent."

**THEY WROTE, phrase by phrase:**
- "point-level temporal consistency" ✓ — **their exact title phrase**: "…Based on Point-Level
  Temporal Consistency"; *"measures temporal consistency at the point cloud level"* (§1).
  Verbatim — nothing to polish.
- "detects LiDAR spoofing against a single vehicle" ✓ — ego-vehicle threat model (§4):
  dense/sparse point injection into the ego LiDAR; no inter-vehicle communication anywhere
  (their refs [4],[36] on cooperative perception are cited only as raw-data motivation).
- "exploiting temporal structure in its own sensor stream" ✓ — synthesis of the ego
  sensor's own historical frames (F1…FL) compared against its own incoming frame FL+1 (§5).
- "test whether observations from a single sensor remain temporally self-consistent" ✓ — *"injected points
  demonstrate poor temporal consistency — appearing inconsistently within the point cloud
  frame over time"* (§5); after merging the synthesized and incoming frames, DBSCAN clusters
  containing synthesized points are discarded, and the remaining incoming-frame-only clusters
  are flagged as fabricated objects.

**VERDICT: ✅ VERIFIED — no change needed.**

---

## Corroborations noted (strong; no manuscript change required)
1. **Their failure case IS the camouflage geometry (§6.2 + Appendix C):** *"most failure
   cases arise when spoofed objects are attached to benign road objects"*; *"Using spatial
   clustering for attack detection predominantly fails when spoofed points are near benign
   road objects."* A phantom hugging real structure merges into the real object's cluster →
   missed. They dismiss the harm (*"does not significantly affect existing navigation
   decisions"*) because an attached fake is subsumed by avoiding the real object — TRUE in
   their free-standing-car scenes, FALSE in ours, where the camouflage phantom extends a
   real obstacle INTO the corridor gap and closes the passage. So even the strongest
   single-vehicle temporal defense concedes exactly the placement our attack uses, and its
   stated reason the miss is benign does not transfer to navigation-through-gaps. Reviewer
   one-liner ready. (Optional strengthening sentence for related.tex exists but is NOT
   required — our current text makes no claim about ADoPT's behaviour on our attack, which
   is the safe posture; Srinivasa's call whether to add it.)
2. **Single-frame injection only, persistent attack untested (§7):** *"While currently
   focused on single-frame fake object injection attacks…"* — same limitation class as
   3D-TC2 and PRBI: the reference signal is the scene's own past, and a persistent
   fabrication established from frame 1 is temporally self-consistent. Consistent with (not
   proof of) our reference-signal distinction; we claim nothing about it in the manuscript.
3. Their anomaly signal degrades near benign objects because CLUSTERS MERGE — a spatial
   association failure, cousin of the association problem our realistic-assoc probe (AUC
   0.85–0.90) quantifies. Noted only.

## Second-order sweep (standing rule) — FULL 37-ref bibliography title scan done 2026-07-17
**Zero new family members.** Refs: single-vehicle LiDAR attack line (Petit, Shin, Yan
DefCon, Cao/Sato/Sun, roadside physical attacks), single-vehicle defenses already bracketed
(CARLO, Shadow-Catcher, LOP/"Wraith", 3D-TC2, AdvIT, PercepGuard — all single-sensor or
single-camera consistency), Liu & Park TDSC'21 "Seeing is Not Always Believing" (perception-
error attack detection via one vehicle's OWN multi-sensor cross-check — single-vehicle,
LOW, out of family), scene-flow/registration methodology (ICP, NSFP, FlowNet3D, PointPWC,
neural prior, DCD, EMD), detectors/datasets (PointPillars, SECOND, nuScenes, Argoverse),
and two BENIGN cooperative-perception architectures: Cooper (ICDCS'19) and EMP (MobiCom'21)
— CP plumbing with no attacker/trust, covered by our existing CP framing; no defense-family
members.

## Srinivasa's verification checklist (page pointers, arXiv v1)
| # | what to check | where in PDF |
|---|---|---|
| 1 | title phrase = "…Based on Point-Level Temporal Consistency" (our verbatim phrase source) | p.1 title |
| 2 | single ego-vehicle threat model: dense (≤200 pts) / sparse (≤64 pts) injection | p.4 §4 |
| 3 | "most failure cases arise when spoofed objects are attached to benign road objects" | p.11 §6.2 Failure Cases + p.17 Appendix C |
| 4 | "currently focused on single-frame fake object injection attacks" | p.12 §7 Conclusion |

## Bookkeeping
- refs.bib `adopt2023`: title exact ✓ (incl. capitalization-protected {ADoPT}), authors
  Cho/Cao/Zhou/Mao ✓, BMVC 2023 ✓ (bib comment "VERIFIED" holds; arXiv v1 itself is
  LNCS-format without venue stamp — BMVC acceptance is public record, no re-check needed),
  arXiv:2310.14504 ✓ matches stamp.
- No catches; no manuscript edits from this audit.
