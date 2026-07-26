# TrustFlip — paired claim/evidence sheet (full read, 2026-07-17)

## STATUS: ⏳ CLAUDE'S AUDIT DONE — **AWAITING SRINIVASA'S INDEPENDENT REVIEW**
Full 16-page read (arXiv:2605.22122v1). **No catches — every phrase in our single use is
near-verbatim to their abstract ("weaponize" is their own verb).** One nuance documented on
our follow-on sentence; three second-order candidates found in their bibliography (LUCIA —
which my PRBI triage had missed — plus two attack-side papers). Closed only after Srinivasa's
own audit.

**The paper:** Yutong Liu, Chenyi Wang, Ming F. Li, Qingzhao Zhang (Univ. of Arizona;
Q. Zhang = CAD's first author), *"Adversarial Trust Poisoning in Vehicular Collaborative
Perception"*, arXiv:2605.22122v1 (21 May 2026, cs.CR). ⚠ NOTE: the paper's TITLE is
"Adversarial Trust Poisoning…" — **TrustFlip is the attack's name inside the paper**
(TrustReflect = their mitigation). Our bib key `trustflip2026` carries the correct full title.
PDF: `Phase_CD/Research paper/TrustFlip.pdf` (16 pages; MuPDF font warnings during
extraction, text intact).

**What the paper does (their own words):** *"We present TrustFlip, a novel attack that
weaponizes consistency-based defenses to poison the trust assigned to benign vehicles.
Instead of injecting false data into the collaboration pipeline, it deploys physical
adversarial objects that are genuine but induce inconsistent observations among benign
vehicles. The resulting inconsistencies are misattributed by the defense to the targeted
vehicle, causing its trust score to degrade and eventually leading to its downweighting or
exclusion from collaboration"* (Abstract). View-conditioned 3D-mesh optimization (FROMREAL /
ATTACHED / HOLLOW priors); evaluated on OPV2V against **CAD, MATE, LUCIA, MADE** over 4 CP
backbones; *"removes the targeted benign vehicle from collaboration in up to 87.7% of
scenarios and drops Average Precision (AP) by up to 13%"*; real-world LiDAR captures of
physical prototypes. TrustReflect (self-reflection masking) cuts attack success 35–100%.

---

## USE 1 (the ONLY use) — related.tex ~lines 103–109
**WE WRITE (verbatim):** "Complementing the defense literature, the TrustFlip
attack~\cite{trustflip2026} shows that consistency-based trust can itself be weaponized:
physically induced disagreements cause defenses to expel \emph{honest} vehicles. Our
evaluation addresses the same failure class by measuring \emph{no-harm} --- the success
cost of running the defense in attack-free swarms --- directly, and finding it statistically
indistinguishable from zero even under an adaptive attacker."

**⚠ Wording polish (Srinivasa, 2026-07-19):** "addresses \emph{exactly this} failure class"
→ "addresses \emph{the same} failure class". We measure the *same downstream failure*
(erroneous exclusion of honest agents), not TrustFlip's *attack mechanism* (physical
adversarial objects). "the same" removes any reading that we evaluate the TrustFlip attack
itself — consistent with the NUANCE block below.

**THEY WROTE, phrase by phrase:**
- "consistency-based trust can itself be weaponized" ✓ — *"weaponizes consistency-based
  defenses to poison the trust assigned to benign vehicles"* (Abstract); *"can weaponize the
  defense itself to suppress benign contributors"* (§I). **"Weaponize" is their verb.**
- "physically induced disagreements" ✓ — *"deploys physical adversarial objects that are
  genuine but induce inconsistent observations among benign vehicles"* (Abstract); *"an
  externally induced physical effect"* (§I).
- "cause defenses to expel honest vehicles" ✓ — *"leading to its downweighting or exclusion
  from collaboration"* (Abstract); *"removes the targeted benign vehicle from collaboration
  in up to 87.7% of scenarios"* (Abstract).
- Root cause, in their words (useful if a reviewer probes): *"these defenses cannot
  distinguish whether a cross-view inconsistency originates from a malicious vehicle or from
  an externally induced physical effect"* (§I).

**NUANCE on our follow-on sentence (no change made):** the failure class = a defense harming
honest agents via misattributed inconsistency. TrustFlip *engineers* that inconsistency with
physical objects; our no-harm metric measures the *naturally arising* version (noise-induced
false gating) plus behaviour under our adaptive attacker. We do NOT evaluate an attacker that
plants physical objects to frame a specific honest drone (outside our threat model — our
traitors lie in broadcasts, they don't modify the physical scene). Our sentence claims only
that we MEASURE the failure class directly, which is accurate; it makes no claim of defeating
TrustFlip-style framing. If a reviewer pushes, the one-line answer: "physical-scene
manipulation is outside our threat model; the failure mode it triggers (honest exclusion) is
the quantity our no-harm column measures."

**VERDICT: ✅ VERIFIED — no change needed.**

---

## Second-order sweep — FULL 58-ref bibliography title scan done 2026-07-17
Three NEW candidates (logged in PRIOR_ART_SECOND_ORDER.md):
1. **LUCIA** (Wang et al., "From Threat to Trust: Exploiting Attention Mechanisms for Attacks
   and Defenses in Cooperative Perception") — attention-level trust modulation defense;
   TrustFlip treats it as one of four SOTA defenses. ⚠ This same paper was **PRBI's ref [28]
   and my PRBI-sweep triage MISSED it** (it sat in the keyword-hit list unpromoted) — now
   corrected. Same cluster as ROBOSAC/CP-Guard/MADE (item 3).
2. **"Pretend Benign"** (Lin et al.) — a stealthy attack exploiting vulnerabilities in CP
   defenses (defense-aware attacker, like TrustFlip). LOW-MED: triage abstract for overlap
   with our adaptive-attacker framing.
3. **"From Stealthy Data Fabrication to Unsafe Driving: Realistic Scenario Attacks on
   Collaborative Perception"** (Zhang, Zhang & Mao, arXiv) — MEDIUM: title suggests
   scenario/driving-level attack outcomes; must check it does not weaken our
   "success-not-detection-accuracy as the end metric" novelty phrasing (expected outcome:
   attack-only case studies, no defense, no learned navigation policy — like CAD's Apollo
   demos — but verify from abstract).
Rest of the 58: CP architectures/datasets/backbones, physical adversarial-object line
(Cao/Tu/Zhu — single-vehicle, our 3D-TC2/ADoPT entry point), CP-FREEZER (latency/availability
attack — out of family), CAD-author fabrication follow-ups (attack-side of the already-cited
CAD line), differentiable-rendering utilities. No other family members.

## Srinivasa's verification checklist (page pointers, arXiv v1)
| # | what to check | where in PDF |
|---|---|---|
| 1 | "weaponizes consistency-based defenses" + physical objects + "downweighting or exclusion" | p.1 Abstract |
| 2 | 87.7% removal of targeted benign vehicle, 13% AP drop | p.1 Abstract + p.2 contributions |
| 3 | evaluated against CAD, MATE, LUCIA, MADE (the defense set) | p.2 §I / p.3 §II.B |
| 4 | "cannot distinguish whether a cross-view inconsistency originates from a malicious vehicle or from an externally induced physical effect" | p.1–2 §I |

## Bookkeeping
- refs.bib `trustflip2026`: title "Adversarial Trust Poisoning in Vehicular Collaborative
  Perception" ✓ matches PDF; authors Liu/Wang/Li/Zhang ✓; arXiv:2605.22122 ✓ matches stamp;
  cited as arXiv preprint ✓ (v1, no venue stated). Same pre-submission venue re-check class
  as PRBI/CoDynTrust/SwarmRaft.
- No catches; no manuscript edits from this audit.
