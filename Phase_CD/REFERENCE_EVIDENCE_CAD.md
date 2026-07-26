# CAD — paired claim/evidence sheet (full read, 2026-07-17)

## STATUS: ✅ CLOSED (2026-07-17) — verified independently by Srinivasa against the PDF
Full 18-page read (arXiv:2309.12955v2). Found 2 items: **catch #22** (small, USE 1 wording) and
the long-**HELD catch #15b** now resolved (USE 2, the baseline-comparison clause — CAD portion
confirmed WRONG, whole clause rewritten in one pass as planned). Srinivasa completed the 5-item
checklist 2026-07-17 (plus caught the "two traitors" understatement, fixed in USE 1).

**The paper:** Qingzhao Zhang, Shuowei Jin, Ruiyang Zhu, Jiachen Sun, Xumiao Zhang,
Qi Alfred Chen, Z. Morley Mao, *"On Data Fabrication in Collaborative Vehicular Perception:
Attacks and Countermeasures"*, USENIX Security 2024. arXiv:2309.12955.
PDF: `Phase_CD/Research paper/CAD.pdf` (18 pages, arXiv v2 — byte-identical to the copy
Srinivasa placed 2026-07-16). Extracted text: scratchpad `cad_text.txt`.
Their code: github.com/zqzqz/AdvCollaborativePerception (stated open source, §6.2).

**What the paper does (their own words):**
- Attacks: *"we break the ground by proposing various real-time data fabrication attacks in
  which the attacker delivers crafted malicious data to victims"* (Abstract); *"a series of
  stealthy, targeted, and realistic attacks exploiting LiDAR-based collaborative perception"*
  (§1). Black-box **ray casting** vs early fusion (raw point clouds), white-box **online
  adversarial (PGD)** vs intermediate fusion (feature maps); success >86% on Adv-OPV2V;
  real-vehicle demos on MCity testbed with Baidu Apollo.
- Defense: *"we present a systematic anomaly detection approach that enables benign vehicles
  to jointly reveal malicious fabrication"* (Abstract). *"CAD requires each vehicle to generate
  and share an occupancy map, which is a 2D map labeling the 2D space into three classes, free,
  occupied, and unknown"* (§1). Two checks (§5.4): **occupancy consistency check** (a region
  occupied for one vehicle and free for another ⇒ conflict) and **perception-occupancy
  consistency check** (bounding boxes vs the merged map). Detects *"91.5% of attacks with a
  false positive rate of 3%"* (Abstract).
- ⚠ KEY FACT for our fix 15b: the occupancy maps are built with **classical geometry, not deep
  features** — *"ground fitting algorithms (e.g., RANSAC…)"*, *"clustering the remaining points
  based on point density"*, occupied regions are *"the convex hulls of the object clusters"*
  (§5.3); implementation = *"polygon operations in shapely and implementation of RANSAC and
  DBSCAN from Open3D"* (§6.2). Defense metrics = TPR/FPR/ROC of anomaly detection (§6.4.1),
  NOT average precision of object detection.

---

## USE 1 — related.tex lines 6–17 (opening of "Security of collaborative perception") — catch #22 fixed here
**WE WRITE (verbatim, after fix):** "Zhang et al.~\cite{zhang2024cad} demonstrate practical
data-fabrication attacks on vehicular collaborative perception and propose CAD, a detector in
which benign vehicles jointly reveal malicious fabrication through cross-vehicle
occupancy-consistency checks; the approach therefore relies on benign vehicles positioned to
observe the attacked region."

**THEY WROTE:**
- *"real-time data fabrication attacks"* + *"realizable in real-world experiments"* (Abstract)
  → "practical data-fabrication attacks" ✓
- *"enables benign vehicles to jointly reveal malicious fabrication"* (Abstract) → our "benign
  vehicles jointly reveal malicious fabrication" is **near-verbatim** ✓
- *"Occupancy consistency check reveals inconsistencies among synchronized occupancy maps"*
  (§5.4); *"We propose a cross-agent consistency check where all benign vehicles exchange
  evidence of anomalies to reveal adversarial behaviors jointly"* (§5.1) → "cross-vehicle
  occupancy-consistency checks" ✓ (their own compound term)
- **The load-bearing clause** — *"The detection could be successful only when at least a benign
  CAV observes the attacked region"* (§5.5 Limitations, p.8); also *"abnormal detection results
  … are revealed if the attacked region is observed by at least one benign CAV"* (§1) → our
  "relies on benign vehicles positioned to observe the attacked region" is **their own stated
  limitation, faithfully paraphrased** ✓

**CATCH #22 (fixed 2026-07-17):** we previously wrote "through cross-vehicle occupancy
**agreement**". Their mechanism reveals fabrication through occupancy **conflicts**
(inconsistencies), and their term is "consistency check" — "agreement" inverted the mechanism's
polarity. Fixed to "occupancy-consistency checks".

**Also supported (our follow-on differentiation, lines 11–13):** "we do not assume such a
benign observer of the attacked region … remains effective with up to three traitors among ten
robots." (UPDATED 2026-07-17, Srinivasa's catch: the sentence said "two traitors" — written
before the k=3 runs landed. The full k∈{1,2,3} matrix is now camera-ready: f=3 camouflage
recovery +13.6 pp, wall k=3 comm-loss +11.5…+7.5, all CIs>0 — so "up to three" is the
evidence-backed claim. This is a claim about OUR results, not about CAD.)
CAD's own words make the contrast for us: *"Though the system may identify the possible
attackers via majority voting, it is limited in effectiveness if benign CAVs do not dominate
the road"* (§5.5) and *"More attackers decrease the coverage of benign occupancy maps and cause
more false negatives"* (§6.4.2). ✓ our no-honest-majority claim is a genuine departure.

**VERDICT: ✅ after fix.**

## USE 2 — related.tex lines 158–162 (baseline-comparison clause) — **HELD catch #15b RESOLVED here**
**WE WROTE (before):** "CAD, PRBI, and GCP operate on the deep feature maps of vehicular
detection stacks and score detection accuracy, while …"

**PROBLEM (why 15b was held for CAD, now confirmed):** for CAD this was wrong on BOTH halves.
(1) CAD's detector never touches deep feature maps — it consumes **occupancy maps built from
raw LiDAR with RANSAC/DBSCAN/convex hulls** (§5.3, §6.2) checked against final bounding boxes;
the paper's *attacks* target feature maps (intermediate fusion) and raw point clouds (early
fusion), but the *defense* deliberately sits at the occupancy level. (2) CAD is scored by
anomaly-detection **TPR/FPR/ROC** (§6.4.1), not object-detection accuracy. The GCP audit had
already found the same clause imprecise for GCP (detector reads decoded detections) and PRBI
(Jaccard over detection sets) — the fusion/attack is feature-level, the defenses are not.

**WE WRITE (verbatim, after fix, applied 2026-07-17):** "The defenses above cannot be
transplanted onto our benchmark without distortion: CAD, PRBI, and GCP defend the fused
perception pipelines of vehicular detection stacks and are evaluated by detection-level metrics
(anomaly-detection rates or average precision), while TruPercept, MATE, and the same authors'
aerial framework operate at the object and track level;"

**WHY the new wording is safe for all three:**
- "defend the fused perception pipelines of vehicular detection stacks" — CAD: attacks/defense
  are on early/intermediate-fusion CAV perception (§3–5) ✓; GCP: protects V2VNet feature-level
  fusion ✓ (GCP dossier); PRBI: re-verified from PRBI.pdf 2026-07-17 — *"exchange of
  feature-level sensory data"*, attackers *"inject perturbations into their feature maps"*,
  PRBI achieves *"robust fusion and attacker [identification]"* ✓.
- "evaluated by detection-level metrics (anomaly-detection rates or average precision)" — CAD:
  TPR/FPR (anomaly-detection rates) ✓; GCP: AP ✓ (dossier); PRBI: AP@0.5/AP@0.7 on V2X-Sim,
  re-verified from PRBI.pdf 2026-07-17 ✓. No method is evaluated on navigation.
  (PRBI's standalone dossier written 2026-07-17: `REFERENCE_EVIDENCE_PRBI.md`.)
- The paragraph's point (nothing in this family produces our navigation-success outcome or
  consumes geometric obstacle claims) is UNCHANGED and remains true — CAD's shared occupancy
  maps are defense-side metadata, not the perception messages a policy steers by.

**VERDICT: ✅ after fix. Catch #15b closed (was held since the GCP audit, 2026-07-11).**

---

## Bonus corroborations noted during the read (no manuscript change needed)
- Our related.tex line 21–22 says GCP "expose[s] blind-area attacks … evaluated using Average
  Precision (AP)" — consistent with CAD's independent framing of the defense space. No conflict.
- CAD evaluates **adaptive attackers** against its own defense (§6.4.1 "Other adaptive attacks")
  and reports a local-map-only TPR lower bound — good company for our adaptive-attacker study;
  no citation claim made, nothing to verify.
- CAD's robustness knobs (σ_occ area thresholds tolerating ~0.1 m localization error, §5.1) are
  the single-frame-tolerance idea our robust filter generalizes; we make no claim about this in
  the manuscript, so nothing to change.

## Srinivasa's verification checklist (page pointers, arXiv v2 layout)
| # | what to check | where in PDF |
|---|---|---|
| 1 | "enables benign vehicles to jointly reveal malicious fabrication" | p.1 Abstract |
| 2 | occupancy map = free/occupied/unknown, shared by each vehicle | p.1–2 §1; p.7 §5.2 |
| 3 | occupancy maps built via RANSAC / density clustering / convex hulls (NOT deep features) | p.7 §5.3; p.9 §6.2 "shapely … RANSAC and DBSCAN" |
| 4 | "only when at least a benign CAV observes the attacked region" + majority-voting limitation | p.8 §5.5 Limitations |
| 5 | defense scored by TPR/FPR/ROC (91.5% / 3%) | p.1 Abstract; p.12 §6.4.1 + Table 3 |

## Bookkeeping
- refs.bib `zhang2024cad`: title/authors/venue verified against PDF title page ✓ (USENIX
  Security 24, arXiv:2309.12955) — bib comment says "VERIFIED" and the full read confirms.
- Catch #22 applied 2026-07-17: "cross-vehicle occupancy agreement" → "cross-vehicle
  occupancy-consistency checks" (related.tex line ~9).
- Catch #15b applied 2026-07-17 (one-pass rewrite as planned in the GCP dossier): "operate on
  the deep feature maps … and score detection accuracy" → "defend the fused perception
  pipelines … evaluated by detection-level metrics (anomaly-detection rates or average
  precision)" (related.tex lines ~158–162).
- All WE WRITE blocks above are verbatim from the tex files as of 2026-07-17.
