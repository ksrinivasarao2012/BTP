# PRBI — paired claim/evidence sheet (full read, 2026-07-17)

## STATUS: ✅ CLOSED (2026-07-17) — verified independently by Srinivasa against the PDF
Full 15-page read (arXiv:2603.08498v1). PRBI was the one reference whose uses were checked
BEFORE the dossier practice existed — this file closes that gap. Found 1 item (**catch #23**,
same imprecision class as #15a: "optimizes" → "is evaluated by"); all other uses verified.
⚠ The venue TODO-VERIFY (refs.bib says CVPR 2026; PDF states no acceptance) remains OPEN as a
pre-submission bib check — closure of the dossier does not close that item.

**The paper:** Yi Yu, Libing Wu, Zhuangzhuang Zhang, Jing Qiu, Lijuan Huo, Jiaqi Feng,
*"All Vehicles Can Lie: Efficient Adversarial Defense in Fully Untrusted-Vehicle Collaborative
Perception via Pseudo-Random Bayesian Inference"*, arXiv:2603.08498v1 (9 Mar 2026), Wuhan
University / Guangzhou University. PDF: `Phase_CD/Research paper/PRBI.pdf` (15 pages incl.
appendix). Extracted text: scratchpad `prbi_text.txt`.

**What the paper does (their own words):**
- Setting: *"fully untrusted-vehicle CP"* — *"all vehicles (including the ego one) must be
  treated as potentially malicious"*; *"All Vehicles Can Lie"* (§1). Fusion: feature-level
  (V2VNet/DiscoNet/mean/max/sum), V2X-Sim dataset, FaFNet backbone.
- Reference signal: *"using the reliable perception from the preceding frame as a dynamic
  reference"* (Abstract). *"if the similarity with the previous frame falls below a warning
  threshold ϵ, the frame is flagged as potentially attacked"* (§4.2). Similarity = **Jaccard**
  over consecutive detection sets Dt, Dt−1 (Eq. 5, Hungarian matching with IoU).
- Mechanism: pseudo-random binary grouping (2 verifications/frame), attacker count
  m = log2(1/η) (Eq. 9), per-vehicle Bayesian benign probability (Eq. 10–12), T-test
  convergence; theorems for convergence + floor-rounding.
- Attacks: PGD, BIM, C&W feature perturbations (§6.1); **intermittent attacks** = perturbations
  *"injected periodically every 1, 3, or 5 frames"* (§11.3, appendix).
- Metrics: **AP@0.5 / AP@0.7** on V2X-Sim + verification count/frame + ID/misclassification
  rate. Recovery: *"restores detection precision to between 79.4% and 86.9% of pre-attack
  levels"* (Abstract).

---

## USE 1 — related.tex lines 79–99 (the "closest to our mechanism" paragraph) — catch #23 fixed here
**WE WRITE (verbatim, after fix):** "Closest to our mechanism, the recent PRBI
defense~\cite{prbi2026} exploits frame-to-frame perceptual consistency to identify lying
vehicles in fully untrusted cooperative detection. It differs from our setting in three ways
that matter: it is evaluated by detection accuracy on feature-level fusion rather than by a
closed-loop navigation objective; it does not model ranging noise, and so does not confront the
honest-disagreement regime in which we show consistency checking becomes destructive; and while
it evaluates intermittent injection schedules, it does not consider a defense-aware attacker
that optimizes its fabrication against the deployed detector, as our stealth/harm-bind analysis
does."

**THEY WROTE / EVIDENCE per clause:**
- "frame-to-frame perceptual consistency" ✓ — *"leveraging temporal perceptual discrepancies"*
  (Abstract); *"inter-frame similarity is stably around 0.8 in benign scenarios, whereas
  adversarial settings cause it to drop sharply"* (§1).
- "fully untrusted cooperative detection" ✓ — *"fully untrusted-vehicle CP"* is their headline
  term (Abstract, §1, title).
- "evaluated by detection accuracy on feature-level fusion" ✓ — AP@0.5/0.7 on V2X-Sim with
  V2VNet/DiscoNet feature fusion (§6.1, Tab. 3). **CATCH #23 (fixed 2026-07-17):** we
  previously wrote "it *optimizes* a detection-accuracy metric" — PRBI does not optimize any
  metric (nothing is trained against AP); it is *evaluated* by it. Same imprecision class as
  catch #15a (GCP "optimize"→"evaluated by"). Fixed.
- "does not model ranging noise" ✓ — VERIFIED BY ABSENCE: keyword sweep of the full text for
  noise/localization error/sensor error → zero hits in the sensor-noise sense (their threat is
  adversarial feature perturbation δ, Eq. 1–2; no observation-noise model anywhere).
- "evaluates intermittent injection schedules" ✓ — §11.3: *"adversarial perturbations are
  injected periodically every 1, 3, or 5 frames"* (Tab. 6).
- "does not consider a defense-aware attacker" ✓ — attacks are standard PGD/BIM/C&W with
  fixed budgets; no attack is optimized against PRBI's detector anywhere in the paper.

**VERDICT: ✅ after fix.**

## USE 2 — related.tex lines 89–99 (the reference-signal distinction — the load-bearing part)
**WE WRITE (verbatim):** "More fundamentally, PRBI's alarm is raised when the Jaccard
similarity between the current and preceding detection sets falls below a
threshold~\cite{prbi2026}: it screens for a \emph{drop} in inter-frame agreement. Such a
criterion responds to perturbations of the scene relative to its recent past. A persistent
fabrication is temporally self-consistent once established; PRBI does not evaluate this attack
class, and we make no claim about how its detector would behave against it. The distinction we
draw is one of reference signal: PRBI compares the scene to its own past, whereas our test
compares a neighbour's claim to the verifier's independent sensing of the same object,
accumulated over time."

**THEY WROTE:**
- Jaccard between consecutive detection sets ✓ — Eq. 5: *"Jaccard similarity, defined for two
  consecutive detection sets Dt and Dt−1"*; alarm: *"if the similarity with the previous frame
  falls below a warning threshold ϵ, the frame is flagged as potentially attacked"* (§4.2).
- "screens for a drop" ✓ — their signal is exactly the similarity DROP (benign ≈0.8 vs
  adversarial <0.3, §4.1 F1; threshold ϵ=0.35 empirically, §11.4).
- "does not evaluate this attack class" ✓ — every evaluated attack is a per-frame adversarial
  perturbation (PGD/BIM/C&W, continuous or every-1/3/5-frames); no persistent geometric
  fabrication (phantom object held fixed over time) is evaluated. Our hedge ("we make no claim
  about how its detector would behave") is appropriately cautious — note for fairness that
  PRBI's reference is the previous *verified benign* output, not the raw previous frame, so
  the honest summary "compares the scene to its own past" remains accurate.

**VERDICT: ✅ VERIFIED.**

## USE 3 — `related.tex` lines **223–250** (the shared "On baseline comparison" paragraph)
_🔄 **RESYNCED 2026-07-28** — the quote below had gone stale; see the drift note._

**WE WRITE (verbatim, re-copied from live `related.tex` 2026-07-28):** "…**CAD, PRBI, GCP, and
MADE** defend the fused perception pipelines of vehicular detection stacks and are evaluated by
detection-level metrics (anomaly-detection rates or average precision)…"

**THEY WROTE:** *"exchange of feature-level sensory data"* (Abstract); attackers *"inject
adversarial perturbations into shared feature maps"* (§1); metrics AP@0.5/0.7 (§6.1). ✓
(Full clause evidence for all four papers: `REFERENCE_EVIDENCE_CAD.md` USE 2.)

> ⚠️ **DRIFT NOTE (2026-07-28).** This block previously quoted *"CAD, PRBI, **and GCP** defend…"*
> — a version that no longer exists. **MADE was added to the list after this dossier was
> written**, and on 2026-07-28 a LiDAR-Spoofing clause was inserted into the same paragraph.
> Neither change touched the PRBI clause itself, so **the verdict is unaffected** — but the
> quoted text was no longer what the manuscript said.
>
> 🔑 **Root cause, and it affects five dossiers.** This paragraph is quoted by **PRBI, CAD, GCP,
> MATE and AerialTrust**. Editing it silently invalidates the `WE WRITE` block in *every one of
> them at once*. **Whoever edits the "On baseline comparison" paragraph must resync all five.**

**VERDICT: ✅ VERIFIED against the current text.**

**VERDICT: ✅ VERIFIED.**

---

## Srinivasa's verification checklist (page pointers, arXiv v1 layout)
| # | what to check | where in PDF |
|---|---|---|
| 1 | "fully untrusted-vehicle" setting + "All Vehicles Can Lie" | p.1 title + Abstract + §1 |
| 2 | Jaccard over consecutive detection sets + warning threshold ϵ | p.4 §4.2 Eq. 5 |
| 3 | attacks = PGD/BIM/C&W feature perturbations; metrics = AP@0.5/0.7 on V2X-Sim | p.6 §6.1 + Tab. 3 |
| 4 | intermittent attacks every 1/3/5 frames | p.15 §11.3 + Tab. 6 (appendix) |
| 5 | NO sensor/ranging-noise model anywhere (verify by skimming §3 threat model + §6 setup) | p.3 §3, p.6 §6.1 |

## Bookkeeping
- refs.bib `prbi2026`: title + all 6 authors match the PDF title page ✓; arXiv:2603.08498 ✓
  matches the PDF stamp (v1, 9 Mar 2026).
- ⚠ **TODO-VERIFY (venue):** refs.bib says `booktitle = CVPR 2026`. The PDF is a CVPR-format
  arXiv preprint but nowhere states acceptance. Srinivasa: check the arXiv page's Comments
  field / CVPR 2026 program for acceptance before submission; if unconfirmed, cite as
  arXiv preprint.
- Catch #23 applied 2026-07-17: "it optimizes a detection-accuracy metric" → "it is evaluated
  by detection accuracy" (related.tex line ~82).
- All WE WRITE blocks above are verbatim from the tex files as of 2026-07-17.
- PRBI's related work swept for second-order prior art 2026-07-17 → nothing beyond the
  ROBOSAC/CP-Guard/MADE family (see `PRIOR_ART_SECOND_ORDER.md` item 3).
