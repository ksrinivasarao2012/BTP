# CoDynTrust — paired claim/evidence sheet (full read, 2026-07-17)

## STATUS: ✅ CLOSED (2026-07-18) — verified independently by Srinivasa
Full 7-page read (arXiv:2502.08169v1). Found 1 item — **catch #24, the most substantive
misclassification of the audit**: we called CoDynTrust an adversarial "defense"; it is a
BENIGN-FAULT robustness framework (temporal asynchrony) with no attacker anywhere in the
paper. Fixed in related.tex; wording polished twice with Srinivasa. Independently verified
and CLOSED by Srinivasa 2026-07-18.

**The paper:** Yunjiang Xu, Lingzhi Li, Jin Wang, Benyuan Yang, Zhiwen Wu, Xinhong Chen,
Jianping Wang, *"CoDynTrust: Robust Asynchronous Collaborative Perception via Dynamic Feature
Trust Modulus"*, arXiv:2502.08169v1 (12 Feb 2025), Soochow University / City University of
Hong Kong. PDF: `Phase_CD/Research paper/CoDynTrust.pdf` (7 pages, ICRA-style).
Code: github.com/CrazyShout/CoDynTrust.

**What the paper does (their own words):** *"temporal asynchrony in real-world environments,
caused by communication delays, clock misalignment, or sampling configuration differences, can
lead to information mismatches"* (Abstract). CoDynTrust = *"an uncertainty-encoded asynchronous
fusion perception framework"* that *"generates dynamic feature trust modulus (DFTM) for each
region of interest by modeling aleatoric and epistemic uncertainty as well as selectively
suppressing or retaining single-vehicle features"* (Abstract). DFTM *"is scattered back into
the feature map and scales each"* grid (§IV); linear extrapolation + BEV flow for delay
compensation (0–0.5 s); multi-scale hybrid fusion. Evaluated by **AP@0.5 / AP@0.7** on
**DAIR-V2X, V2XSet, OPV2V** under expected delays 0–500 ms.

**THE KEY NEGATIVE FACT (basis of catch #24):** a full-text keyword sweep for
`attack | malicious | adversar | byzantin | spoof | falsif | security | defen` returns
**ZERO hits** in 7 pages. The threat model is delays/noise/model flaws — never an adversary.
The "trust" in DFTM is per-ROI *uncertainty*, not agent trustworthiness against lying.

---

## USE 1 (the ONLY use) — related.tex ~lines 18–25 — catch #24 fixed here
**WE WROTE (before):** "Other **defenses** for feature-fusion collaborative perception include
CoDynTrust~\cite{codyntrust2025}, which weights intermediate feature contributions under
asynchrony, and GCP~\cite{gcp2025}, …; both are evaluated using Average Precision (AP) on
vehicular benchmarks."

**PROBLEM (catch #24):** CoDynTrust is NOT a defense. Calling it one misstates its threat
model (benign asynchrony, not adversaries) — exactly the misclassification GCP's own related
work avoids by separating "systematic" (CoBEVFlow, CoAlign) from "adversarial" challenges.
A CP-security reviewer would flag this immediately.

**WE WRITE (verbatim, current — after MADE insertion 2026-07-17 + Srinivasa's wording
polish 2026-07-18):**
"In feature-fusion collaborative perception, GCP~\cite{gcp2025} defends against malicious
agents by augmenting single-shot spatial-consistency checks with temporal motion-flow
reconstruction to expose blind-area attacks; MADE~\cite{made2024} detects and removes
malicious agents through hypothesis tests on the consistency between each inspected agent
and the ego agent, with statistical false-positive control; and CoDynTrust~\cite{codyntrust2025}
addresses the benign counterpart by weighting intermediate feature contributions according
to their estimated uncertainty, thereby mitigating temporal asynchrony rather than
adversarial behaviour; all three are evaluated using Average Precision (AP) on vehicular
benchmarks."

**⚠ Wording polish (Srinivasa, 2026-07-18, two passes):** (1) "weighting … by uncertainty
to withstand" → "by weighting … according to uncertainty to mitigate" (cleaner: "by" marks
the mechanism, "according to" the basis — no overloaded "by"; "mitigate" more precise than
"withstand"). (2) → "according to their estimated uncertainty, thereby mitigating temporal
asynchrony" (readability: "estimated uncertainty" names what DFTM computes — per-ROI
aleatoric + epistemic uncertainty; "thereby mitigating" states the causal link explicitly
instead of stacking infinitives). All faithful to their "Robust Asynchronous Collaborative
Perception" framing.

**⚠ Interim-wording correction (Srinivasa, 2026-07-17):** my first #24 fix opened with "Other
work hardens feature-fusion collaborative perception itself: GCP defends it…" — "hardens …
itself" re-introduced the catch-#15a imprecision for GCP (its detector is OUTPUT-level,
§II.C "output-level malicious agent detection"; it does not strengthen the fusion internally).
Final wording groups by SETTING ("In feature-fusion collaborative perception…") — the framing
the GCP dossier verified — and "defends against malicious agents" is GCP's own subtitle
("…Malicious Agent Detection").

**THEIR SUPPORT, clause by clause:**
- "weighting intermediate feature contributions by uncertainty" ✓ — DFTM *"scales each"*
  sparse-feature grid (§IV); *"modeling aleatoric and epistemic uncertainty as well as
  selectively suppressing or retaining single-vehicle features"* (Abstract).
- "to withstand temporal asynchrony" ✓ — their own problem statement (Abstract, §I).
- "rather than adversarial behaviour" ✓ — the zero-hit keyword sweep above.
- "evaluated using Average Precision (AP) on vehicular benchmarks" ✓ — AP@0.5/AP@0.7 tables
  on DAIR-V2X / V2XSet / OPV2V (§V, Table I: "performance comparison … at expected delays
  from 0ms to 500ms on three datasets").

**VERDICT: ✅ after fix.**

## Knock-on decision RESOLVED by this audit — the ROBOSAC one-liner (second-order item 3)
With CoDynTrust reclassified, the adversarial-defense example in that sentence is GCP alone.
Options: (a) leave as is — the sentence is accurate and the family is covered again in the
PRBI/baseline paragraphs; (b) add ROBOSAC ("Among Us", ICCV 2023, consensus sampling) as a
second defense example — strengthens family coverage AND its benign-majority requirement
reinforces our no-honest-majority contrast, but adds a new bib entry + audit obligation
(download + skim before writing any descriptive claim). **Recommendation: (b), one clause,
audited on arrival.** DECISION: Srinivasa's call.

---

## Srinivasa's verification checklist (page pointers, arXiv v1)
| # | what to check | where in PDF |
|---|---|---|
| 1 | threat model = delays/clock/sampling — NO attacker (skim Abstract + §I + §III) | p.1–2 |
| 2 | DFTM = per-ROI uncertainty (aleatoric + epistemic), scales features | p.1 Abstract; p.4 §IV |
| 3 | Ctrl+F the PDF for "attack", "malicious", "adversarial" → 0 results | whole PDF |
| 4 | AP@0.5/0.7 on DAIR-V2X, V2XSet, OPV2V, delays 0–500 ms | p.5–6 §V Table I |

## Bookkeeping
- refs.bib `codyntrust2025`: title + all 7 authors match the PDF title page ✓;
  arXiv:2502.08169 ✓ matches PDF stamp. Cited as arXiv preprint (venue "conference,
  unspecified" per bib comment) — ICRA-style format; ⚠ TODO-VERIFY before submission whether
  it has since been accepted somewhere (check arXiv page Comments field), same class as the
  PRBI CVPR check.
- Catch #24 applied 2026-07-17: "Other defenses … include CoDynTrust …" → GCP = the defense,
  CoDynTrust = "the benign counterpart … temporal asynchrony rather than adversarial
  behaviour" (related.tex ~18–25).
- ⚠ Cross-file note: `PAPER_MASTER_PLAN.md` §9.2 lists CoDynTrust among defense must-cites —
  the *citation* stands, but any master-plan wording implying it is an adversarial defense
  inherits catch #24.
- CoDynTrust's related work swept for second-order prior art 2026-07-17: cites CP
  architectures + asynchrony line (SyncNet, FFNet, CoBEVFlow, CoAlign, V2X-ViT) + uncertainty
  quantification classics — all benign-robustness or methodology; NO new defense-family
  members (consistent with it not being a security paper).
