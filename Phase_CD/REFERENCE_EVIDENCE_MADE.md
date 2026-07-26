# MADE — paired claim/evidence sheet (full read, 2026-07-17)

## STATUS: ⏳ CLAUDE'S AUDIT DONE — **AWAITING SRINIVASA'S INDEPENDENT REVIEW**
Full 8-page read (arXiv:2310.11901v2). **This audit is unlike the others: MADE was the
MISSING must-cite (PRIOR_ART_SECOND_ORDER item 1) — so the deliverable is a NEW citation,
written from the paper, not a check of an old one.** Two manuscript edits + one new bib
entry made; every phrase sourced below. Closed only after Srinivasa's own audit.

**The paper:** Yangheng Zhao, Zhen Xiang, Sheng Yin, Xianghe Pang, Yanfeng Wang, Siheng
Chen (Shanghai Jiao Tong Univ. / UIUC), *"MADE: Malicious Agent Detection for Robust
Multi-Agent Collaborative Perception"*, arXiv:2310.11901v2 (8 Jul 2024, cs.CR).
⚠ Venue: IEEE-conference format, NO acceptance stated in the PDF → cited as arXiv with a
TODO-VERIFY (check the arXiv page Comments field; do not guess). PDF:
`Phase_CD/Research paper/MADE.pdf` (8 pages). ⚠ First download was accidentally a duplicate
of Conformity.pdf — caught by identical page/char counts, replaced by Srinivasa same day.

**What the paper does (their own words):** *"we propose Malicious Agent Detection (MADE), a
reactive defense specific to MAC perception that can be deployed by an agent to accurately
detect and then remove any potential malicious agent in its local collaboration network. In
particular, MADE inspects each agent in the network independently using a semi-supervised
anomaly detector based on a double-hypothesis test with the Benjamini-Hochberg procedure
for false positive control. For the two hypothesis tests, we propose a match loss statistic
and a collaborative reconstruction loss statistic, respectively, both based on the
consistency between the agent to be inspected and the ego agent"* (Abstract).
Threat = Tu et al. [32]: PGD-optimized perturbation δ on the intermediate FEATURE MAP a
malicious agent sends (adversarial-example attack, NOT geometric fabrication). Match loss =
Hungarian-matched box-set distance between ego-alone output Y_ego and ego+i fused output
Y_ego+i; CRL = autoencoder (trained on benign residual feature maps from a past-data set
D_B) reconstruction error on R_ego+i = Z_ego+i − Z_ego; conformal p-values + BH at α=0.05.
Results: V2X-SIM (DiscoNet) + DAIR-V2X (Where2comm), AP@0.5 recovered to within
1.27%/0.28% of the ground-truth 'Oracle' defender; beats ROBOSAC; holds against 2–3
malicious agents of 4 (independent AND jointly-optimized "collaborative/adaptive"); an
unsupervised MAD-based variant works without past data (weaker).

---

## USE 1 (NEW) — related.tex, feature-fusion sentence (~lines 18–29)
**WE WRITE (verbatim, added 2026-07-17):** "MADE~\cite{made2024} detects and removes
malicious agents through hypothesis tests on the consistency between each inspected agent
and the ego agent, with statistical false-positive control"
(inside: "In feature-fusion collaborative perception, GCP … ; MADE … ; and CoDynTrust …
addresses the benign counterpart …; all three are evaluated using Average Precision (AP)
on vehicular benchmarks.")

**THEY WROTE, phrase by phrase:**
- "detects and removes malicious agents" ✓ — *"accurately detect and then remove any
  potential malicious agent"* (Abstract); *"a reactive, detection-based defense … by
  detecting and removing malicious agents in the local collaboration network"* (§I).
- "hypothesis tests on the consistency between each inspected agent and the ego agent" ✓ —
  near-verbatim: *"double-hypothesis test … both based on the consistency between the agent
  to be inspected and the ego agent"* (Abstract); *"inspects each agent in the network
  independently"* (Abstract).
- "statistical false-positive control" ✓ — *"the Benjamini-Hochberg procedure for false
  positive control"* (Abstract); *"the false detection rate controlled by the
  Benjamini-Hochberg (BH) procedure"* (§IV-A).
- "all three are evaluated using Average Precision (AP) on vehicular benchmarks" ✓ — AP@0.5
  on V2X-SIM + DAIR-V2X (§V, Tables I/IV); GCP and CoDynTrust already verified in their
  own dossiers.
- Setting placement "feature-fusion collaborative perception" ✓ — *"MAC object detectors
  that conduct the collaboration in the intermediate feature space"* (§II-A).

## USE 2 (NEW) — related.tex "On baseline comparison" (~line 165)
**WE WRITE (verbatim, after edit):** "CAD, PRBI, GCP, and MADE defend the fused perception
pipelines of vehicular detection stacks and are evaluated by detection-level metrics
(anomaly-detection rates or average precision)"
- MADE fits both clauses ✓: fused-pipeline defense (intermediate feature space) and
  detection-level metrics (AP@0.5, TPR/FPR in Table II). Not transplantable to us for the
  same reason as the others: it inspects LEARNED FEATURE MAPS via a trained autoencoder +
  benign calibration data; our agents exchange geometric obstacle claims, and our end
  metric is navigation success.

**VERDICT: ✅ both uses verified at write time.**

---

## THE IMPORTANT NUANCE (why MADE must not be described as majority-based)
MADE is **ego-referenced, per-agent** — like us: the ego inspects each collaborator
independently against its OWN perception, with no voting and no honest-majority requirement
(unlike ROBOSAC's consensus sampling). So our no-honest-majority contrast (drawn in the
consensus paragraph and in the TruPercept/MATE centralization sentence) must NEVER name
MADE as a counter-example — and it doesn't. What still separates us from MADE:
1. **Threat class:** MADE defends PGD feature-map perturbations (adversarial examples);
   ours is geometric fabrication (phantom obstacles) in interpretable claims. Camouflage
   /placement has no analogue in their threat.
2. **Learned + data-hungry vs hand-designed:** MADE is *"semi-supervised"* — needs a benign
   feature-map set D_B *"collected locally from past instances"*, a trained autoencoder,
   and calibration sets (2800/1000 pairs). Our filter is a closed-form statistic with two
   interpretable parameters and no training data.
3. **No sensor-noise regime, no destructive-filter analysis, no navigation loop** — AP is
   the end metric; benign-cost appears only as the small no-attack AP dip (e.g. 64.97→60.58
   on DAIR-V2X, Table I), which is the detection-level cousin of our no-harm column but is
   never studied against noise.
4. Their *"adaptive attack"* = one attacker jointly optimizing MULTIPLE malicious agents'
   perturbations (stressing per-agent independence) — not a detector-aware attacker
   optimizing against the deployed test, so our stealth/harm-bind adaptive analysis is not
   pre-empted. Our combination-novelty paragraph survives unchanged.

## Second-order sweep (standing rule) — FULL 44-ref bibliography title scan done 2026-07-17
**Zero NEW candidates — every family-relevant ref is already tracked:** [13] = ROBOSAC
(item 3), [41] = CAD (cited, closed), [32] = Tu et al. 2021 (judgment-call item 5, named by
CAD+GCP+now MADE — third naming strengthens the case for the one-line cite). Rest: CP
architectures (Where2comm, DiscoNet, V2VNet, V2X-ViT, When2com), datasets (V2X-Sim,
DAIR-V2X), adversarial-ML classics (Szegedy, Madry PGD, physical patches, DPatch,
adversarial t-shirt), statistics classics (Benjamini-Hochberg, Storey, Hochberg&Tamhane,
Vovk conformal p-values, Hampel MAD, Kuhn Hungarian), U-Net, detectors, and
policy/regulatory pointers. Out of family.

## Srinivasa's verification checklist (page pointers, arXiv v2)
| # | what to check | where in PDF |
|---|---|---|
| 1 | "detect and then remove any potential malicious agent" + "double-hypothesis test" + "consistency between the agent to be inspected and the ego agent" + BH false-positive control | p.1 Abstract |
| 2 | threat = optimized perturbation on the SENT FEATURE MAP (Tu et al. attack), PGD | p.2–3 §III-B |
| 3 | ego-referenced statistics: match loss (Y_ego vs Y_ego+i), collaborative reconstruction loss (autoencoder on residuals, benign set D_B) | p.3–4 §IV-B/C |
| 4 | AP@0.5 within 1.27%/0.28% of Oracle; multi-agent "collaborative/adaptive" attacks; no-attack AP dip (benign cost) | p.5–6 Tables I, II, IV |

## Bookkeeping
- refs.bib `made2024` ADDED: title exact ✓, all 6 authors exact ✓, arXiv:2310.11901 ✓
  matches stamp; `@misc` + arXiv note; ⚠ TODO-VERIFY venue (arXiv Comments field) before
  submission — same class as PRBI/CoDynTrust/SwarmRaft/TrustFlip/Conformity.
- related.tex edits 2026-07-17: MADE clause added to the feature-fusion sentence
  ("both are" → "all three are"); "CAD, PRBI, and GCP defend" → "CAD, PRBI, GCP, and MADE
  defend" in On-baseline-comparison.
- PRIOR_ART_SECOND_ORDER item 1 (MADE missing must-cite) → RESOLVED by this audit.
- TrustFlip context: MADE is one of the four defenses TrustFlip attacks (CAD, MATE, LUCIA,
  MADE) — citing it also future-proofs the TrustFlip sentence.
