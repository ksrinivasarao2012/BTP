# ROBOSAC — paired claim/evidence sheet (full read, 2026-07-21)

## STATUS: ⏳ CLAUDE'S FULL READ DONE — **AWAITING SRINIVASA'S REVIEW + the A4 insertion**
Full 10-page read (arXiv:2303.09495v3 = ICCV 2023; incl. all 48 refs). This is a **forward-looking**
dossier: ROBOSAC is **not yet in refs.bib and not yet cited** — the triage APPROVED citing it, so this sheet
establishes exactly what we may claim, gives the phrase-by-phrase THEY-WROTE backing for a proposed WE-WRITE
sentence, and flags the traps. **No catches against existing text (there is none yet); three precision traps
to avoid when we insert the citation.** Bibliography scan: **zero new family members.** Closed only after
Srinivasa's own read + the actual related.tex edit.

**The paper:** Yiming Li, Qi Fang, Jiamu Bai (NYU), Siheng Chen (SJTU / Shanghai AI Lab), Felix Juefei-Xu
(Meta AI), Chen Feng (NYU), *"Among Us: Adversarially Robust Collaborative Perception by Consensus"*,
**ICCV 2023**, arXiv:2303.09495v3 (18 Aug 2023, cs.RO). Code: `github.com/coperception/ROBOSAC`.
⚠ "ROBOSAC" is the METHOD name; the paper TITLE is "Among Us: …". PDF: `Phase_CD/Research paper/ROBOSAC.pdf`
(10 pages incl. references, verified page 1 header = correct paper, not a duplicate).

**What the paper does (their own words):** *"we propose ROBOSAC, a novel sampling-based defense strategy
generalizable to unseen attackers. Our key idea is that collaborative perception should lead to consensus
rather than dissensus in results compared to individual perception. This leads to our hypothesize-and-verify
framework: perception results with and without collaboration from a random subset of teammates are compared
until reaching a consensus"* (Abstract). Threat = **white-box feature-level adversarial perturbation** on the
shared intermediate feature map (the Tu et al.\ [14] attack): *"a maliciously-crafted imperceptible
perturbation added on the shared feature can drastically alter the perception output"* (§1). Mechanism =
RANSAC-style sampling: the ego samples a subset of `s` teammates, fuses, and compares the fused detections to
its **ego-only** detections via IoU-after-Hungarian-matching against a consensus threshold `ε=0.3`; on
consensus it outputs the fused result, else it resamples, ultimately falling back to ego-only. Derives the
attacker-free sampling math (Eq. 1/2) and an **A2CP** attacker-ratio estimator (Alg. 2). Task = **collaborative
3D object detection** on **V2X-Sim**; metric = **Average Precision @ IoU 0.5/0.7**; attacks = PGD/C&W/BIM.

---

## NOVELTY CHECK — does ROBOSAC pre-empt any of our claims? **NO** (5 axes)
| Our novelty | ROBOSAC | Pre-empt? |
|---|---|---|
| closed-loop learned **navigation** metric (success, not detection) | evaluated by **AP@IoU 0.5/0.7** on 3D detection (Tables 1–7) | ✗ |
| **destructive-filter-under-ranging-noise** regime | no honest-sensor noise model at all; honest disagreement never considered | ✗ |
| **camouflage within the noise tolerance** (geometric) | threat is a **feature-space adversarial δ**, not a geometric obstacle claim | ✗ |
| **cross-agent temporal offset-bias** test | has a "temporal consistency" *efficiency* variant, but it is **scene-vs-its-own-past** (see TRAP 1) | ✗ |
| operation **without an honest local majority** | sampling-based consensus whose cost explodes as benign agents grow scarce + needs η known (see TRAP 2) | ✗ (reinforces us) |

**Verdict: ROBOSAC does NOT pre-empt us.** Different threat (feature perturbation vs geometric fabrication),
different end metric (AP vs navigation), different mechanism (subset-sampling output-consensus vs pairwise
geometric offset), no ranging-noise/honest-disagreement regime. It is a **feature-level, AP-scored consensus
defense** — the same family bracket as MADE/GCP/CAD/CP-Guard.

---

## PROPOSED WE-WRITE (for A4 — Srinivasa's call on exact placement)
**Placement A (defense-family sentence, related.tex ~18–28, joining MADE/GCP/CoDynTrust):**
> "…and ROBOSAC~\cite{robosac2023} rejects adversarial feature-map perturbations by sampling subsets of
> teammates until the collaborative output reaches consensus with the ego's own perception."

**Placement B (the no-honest-majority contrast, related.tex ~139–141 / Byzantine-robots para):** ROBOSAC is
the cleanest example of a *consensus/sampling* defense whose viability depends on being able to draw an
attacker-free subset — a good foil for our pairwise claim. Suggested clause:
> "Sampling-based consensus defenses such as ROBOSAC~\cite{robosac2023} must draw an attacker-free subset of
> teammates and know or estimate the attacker ratio; the sampling budget required grows sharply as benign
> agents become scarce. Our pairwise test needs neither a clean subset, a known ratio, nor a consensus vote."

**THEY-WROTE, phrase by phrase (for whichever we use):**
- "sampling subsets of teammates … until … consensus" ✓ — *"the robot samples a subset of teammates and
  compares the results with and without the sampled teammates. After the consensus is verified … the robot
  can output the perceptual results"* (§1); Alg. 1.
- "consensus with the ego's own perception" ✓ — the reference is **ego-only** output: *"Obtain the perception
  results of only using the ego-robot's message: Ŷ0 = fθ(M0)"* (Alg. 1, l.1); consensus = `d(Ŷs, Ŷ0) ≤ ε`.
- "adversarial feature-map perturbations" ✓ — *"an indistinguishable adversarial noise added on the shared
  intermediate representation can result in a lot of false detections"* (§2); Eq. 3 optimises `Mv + δ`.
- "must draw an attacker-free subset … know or estimate the attacker ratio" ✓ — *"a successful sampling is
  one that contains no attackers amongst the sampled s robots"* (§3.3); *"Assume that the attacker ratio is
  known as η"* (§3.3); the unknown-ratio case needs the whole A2CP estimator (§3.4, Alg. 2).
- "sampling budget … grows sharply as benign agents become scarce" ✓ — Table 1: for `s=1`, `N` = 3 (η=0.2) →
  6 (0.4) → 10 (0.6) → **21 (η=0.8)**; and at η=0.8 only `s=1` is achievable at all.

---

## THREE PRECISION TRAPS (do NOT let these slip into the citation)
**TRAP 1 — ROBOSAC's "temporal consistency" is NOT a cross-agent test.** Table 4 / §5.2: *"we further propose
to use temporal consistency instead of the difference between collaborative and individual perception to save
computations. Specifically, we compare the current output with the previous output for consensus
verification."* This is **scene-vs-its-own-past** (an efficiency trick to skip recomputing ego-only each
frame), the **same reference signal as PRBI's Jaccard-drop and 3D-TC2** — NOT a comparison of a neighbour's
claim to the ego's independent view. Our related.tex temporal paragraph's reference-signal distinction already
covers this class; if we ever mention ROBOSAC's temporal variant, say "scene-vs-own-past," never "cross-agent."

**TRAP 2 — do NOT write "ROBOSAC requires an honest majority" as a hard fact.** Table 1 shows it operates at
**η=0.8 (80% attackers)** with `s=1, N=21` — i.e. it can still find one benign teammate in a traitor-majority
regime, given enough sampling and a known ratio. The accurate contrast is about **cost + prerequisites**
(needs a clean-subset draw, needs η, budget explodes), NOT a blanket "needs a majority." State it as I did in
Placement B.

**TRAP 3 — we SHARE the "trust your own sensing" assumption; don't contrast on it.** ROBOSAC's consensus
reference is the ego-only output — it trusts the ego's own perception, exactly as our verifier trusts its own
sensing. The genuine contrast is the **mechanism** (all-or-nothing subset sampling + output-space consensus,
which under sustained attack degrades to ego-only / no collaboration) vs **ours** (per-neighbour geometric
offset that keeps honest neighbours while excluding the specific liar). Contrast the mechanism, not the
premise.

---

## Corroborations noted (useful under reviewer fire; no manuscript change required)
- **ROBOSAC's own limitation = an opening our stealth analysis lives in (§6):** *"we assume that although the
  input adversarial noise is imperceptible, its effect on the network output is significant … Future attackers
  might develop dangerous yet subtle perturbations in both the input and output to bypass our
  'outlier-detection-based' defense mechanism."* I.e. ROBOSAC concedes it keys on a **large output-space
  divergence**; an attack that keeps the fused output plausible evades it — precisely the regime our
  camouflage/stealth-harm-bind studies.
- **External cross-reference (Stealthy-Fab 2605.01301, read same day):** its Table 1 + §6.2.2 report ROBOSAC
  at **≤5% TPR** against small pose-perturbation because *"the shifted detection remains plausible"* and
  *"ROBOSAC's consensus sampling cannot isolate the attacker."* Independent evidence that consensus-sampling
  fails on plausibility-preserving attacks — cite via Stealthy-Fab if a reviewer probes, not as our own claim.
- ROBOSAC is **attacker-agnostic / generalises to unseen attacks** (its headline advantage over adversarial
  training; Table 5: 77.9 AP vs PGD, 74.5 vs C&W, where PGD-adversarial-training collapses to 43.2 on C&W).
  Orthogonal to us; noted only.

## Second-order sweep — 48-ref bibliography: title scan 2026-07-21 + ABSTRACT pass 2026-07-26
⚠ **CORRECTION (2026-07-26):** the title scan's "zero new" was over-stated. The abstract pass
(`SECOND_ORDER_ABSTRACT_PASS.md`) surfaced **[27] Vadivelu et al., "Learning to Communicate and Correct Pose
Errors" (CoRL'20)** — a **benign** precedent (robust multi-agent CP against pose/localization NOISE via a
learned consensus over message errors; no adversary, no trust filter). It does **NOT** pre-empt us, but earns
a related-work line (nearest "robust multi-agent CP against bad messages" prior work); I had title-rejected it
as "benign fault." Full-PDF read owed once Srinivasa provides `Vadivelu.pdf`. **Zero new *defense/attack*
family members otherwise.** The remaining refs are: adversarial-ML classics ([13] Szegedy, [33] FGSM, [34] BIM, [47]
PGD/Madry, [48] C&W, [15] adv-examples survey, [16] robustness-accuracy tradeoff, [32] adv attacks/defenses
survey, [35–37] black-box/transfer); the RANSAC methodology line ([17] RANSAC survey, [38] Fischler-Bolles,
[39] MSAC, [40] MLESAC, [41–44] SfM/pose utilities); CP architectures/datasets ([5] V2VNet, [7] CoBEVT,
[10] When2com, [11] DiscoNet, [22] V2X-Sim, [23] Who2com, [24] GNN co-perception, [26] Kim'15 cooperative
driving, [8][9] Cooper/infra-CP); single-vehicle / benign-fault perception ([1–4] BEV/SSC surveys, [18][20][21]
scene-completion & UAV tracking, [28] Tu physical-adversarial LiDAR, [29] adversarial-trajectory,
[30] Cao sensor-attack, [31] multi-sensor adversarial robustness — all **single-vehicle**); benign
uncertainty/pose ([12][25] conformal/UQ collaborative, **[27] Vadivelu et al. "Learning to communicate and
correct pose errors"** — benign POSE-ERROR correction, same Tu/Ren/Urtasun cluster, out of our adversarial
family); and [14] Tu et al. 2021 = **already tracked** (the seminal CP attack, in the second-order list). The
one borderline, [27], is benign fault-tolerance (à la CoAlign), not adversarial → not promoted. No
collaborative-perception TRUST/consistency-defense member beyond what we already cite.

## Srinivasa's verification checklist (page pointers, arXiv v3)
| # | what to check | where in PDF |
|---|---|---|
| 1 | "consensus rather than dissensus … hypothesize-and-verify … random subset of teammates" | p.1 Abstract |
| 2 | threat = adversarial δ on the shared **feature map** (not geometric claims) | p.1 §1 + p.5 Eq. 3 |
| 3 | consensus reference is **ego-only** output Ŷ0; `d`=IoU after Hungarian match, `ε=0.3` | p.3 Alg. 1 + p.5 |
| 4 | needs attacker-free subset + η known (or A2CP estimate); N blows up with η (Table 1) | p.3 §3.3, p.4 §3.4, p.6 Tab.1 |
| 5 | **temporal variant = current-vs-previous output** (scene-vs-own-past), efficiency only | p.7 §5.2 + Table 4 |
| 6 | metric = AP@IoU 0.5/0.7; task = 3D detection on V2X-Sim | p.6 §5.1 + Tables 3,5 |
| 7 | limitation: keys on large output divergence; subtle in-and-out perturbations could bypass | p.8 §6 |

## Bookkeeping — TODO before A4
- **refs.bib entry does NOT yet exist.** Add:
  `@inproceedings{robosac2023, title={Among Us: Adversarially Robust Collaborative Perception by Consensus},
  author={Li, Yiming and Fang, Qi and Bai, Jiamu and Chen, Siheng and Juefei-Xu, Felix and Feng, Chen},
  booktitle={Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV)}, pages={186--195},
  year={2023}}` (page 186–195 per Stealthy-Fab's ref [27]; ICCV 2023 is public record — NOT in the
  arXiv-preprint venue-recheck class).
- Not cited in any section yet → the A4 insert (Placement A and/or B above) is a NEW citation, not an edit.
- No manuscript catches from this read (no existing text to catch); traps 1–3 are for the insertion.
