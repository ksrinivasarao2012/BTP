# Reference evidence — Vadivelu et al., "Learning to Communicate and Correct Pose Errors" (full read, 2026-07-26)

**Verdict: DOES NOT pre-empt us (benign, no adversary). Cite as related work — and, more usefully, cite it in
the discussion.tex BIAS limitation (assumption vi) as the precedent for the per-agent-offset correction we
punt to future work.** Full 16-page read (arXiv:2011.05289v1 = CoRL 2020; incl. appendices A–E + 44 refs).
Page-1 header verified = correct paper.

**The paper:** Nicholas Vadivelu, Mengye Ren, James Tu, Jingkang Wang, Raquel Urtasun (Uber ATG / Waterloo /
Toronto). CoRL 2020. Builds on **V2VNet**: nearby self-driving vehicles share intermediate BEV feature maps
for joint detection + motion forecasting ("PnP"). Dataset V2V-Sim, up to **7 SDVs**.

**What it does (their words):** *"Learned communication… exposes individual agents to the threat of erroneous
messages… the gain is quickly diminished in the presence of pose noise since the communication relies on
spatial transformations. Hence, we propose a novel neural reasoning framework that learns to communicate, to
estimate potential errors, and finally, to reach a consensus about those errors"* (Abstract). Three learned
modules: (i) **pose-regression** (predict the relative-pose correction per edge), (ii) **consistency module**
(MRF with Bayesian reweighting, student-t robust nodes, ICM inference → globally consistent absolute poses),
(iii) **attention aggregation** (learned soft weight `sⱼᵢ = σ(A(mᵢ‖mⱼᵢ))` that down-weights the messages that
remain noisy after correction). Metric = **AP@IoU 0.7** (detection) + **L2 displacement error** (forecasting)
— a **static dataset, no control policy, no navigation**.

---

## Why it does NOT pre-empt our claim (per-axis)
| Our axis | Vadivelu | Pre-empt? |
|---|---|---|
| **Adversary** | **None.** The "threat" is *benign localization noise* misaligning feature maps. No traitor, no fabrication, no attack model. | ✗ |
| **Closed-loop learned navigation, success metric** | AP@IoU + L2 forecasting on a **static replayed dataset**; no policy, no closed loop, no success rate. | ✗ |
| **Consistency-trust turning DESTRUCTIVE under noise** | They *learn to correct* the noise; they note V2VNet+data-aug "trusts them too little and discards too much information" (§4.2) but never show a consistency check becoming net-harmful. Different phenomenon. | ✗ |
| **Cross-agent TEMPORAL offset-bias test** | Explicitly **future work**: *"we can extend our work to exploit the temporal consistency of the pose error in incoming messages"* (Conclusion). Their consistency is single-frame. | ✗ |
| **Adaptive attacker** | N/A (no attacker). | ✗ |
| **Multi-robot** | Yes (≤7 SDVs) — but on-road cars, benign faults. | shared, benign |

**Bottom line:** it is the nearest *"robust multi-agent CP against bad messages under noise"* prior work, but
it is **benign fault-tolerance via learned correction**, not adversarial trust. Our combination-claim survives
untouched.

---

## ⭐ THE USEFUL CATCH (why full-reading this paid off) — cite it in the bias limitation
Our `discussion.tex` assumption (vi) discloses that **agent-specific systematic sensor bias** could wrongly
flag an honest neighbour, and proposes as future work: *"estimating and subtracting a per-neighbour global
offset before the residual bias test would separate the two."* **Vadivelu is a direct precedent that this fix
is feasible and known:**
- They evaluate **biased** noise explicitly: §4.2 "Biased noise" + Figure 4 — *"in the real world, a vehicle
  may experience systematic, biased error… the performance of the model stays well above single vehicle PnP."*
- Their pose-regression module **estimates and corrects a per-agent systematic pose offset** end-to-end —
  exactly the "estimate-and-subtract a per-neighbour offset" primitive we defer.

**Recommended edit (discussion.tex, assumption vi, the final future-work sentence):** append a citation so the
punt is backed by precedent, e.g. change *"…which we leave to future work."* →
*"…which we leave to future work; learned per-agent pose-offset correction of exactly this kind has been shown
effective against systematic bias in benign collaborative perception~\cite{vadivelu2020}."*
This turns a bare "future work" hand-wave into a grounded, defensible one — strengthens the honesty framing a
reviewer would otherwise probe.

## Precision trap (don't over-claim next to it)
Vadivelu's **attention module already down-weights/suppresses inconsistent messages** in multi-agent CP (benign).
Do **not** claim novelty on "excluding/attenuating inconsistent neighbour messages" as a primitive — that
exists here. Our novelty is the **adversarial persistent-bias detection via a cross-agent temporal offset**,
not message-reweighting itself. Our related.tex already frames it that way, so no edit needed — just a guardrail.

## refs.bib entry (needed if cited)
```bibtex
@inproceedings{vadivelu2020,
  title     = {Learning to Communicate and Correct Pose Errors},
  author    = {Vadivelu, Nicholas and Ren, Mengye and Tu, James and Wang,
               Jingkang and Urtasun, Raquel},
  booktitle = {Proceedings of the 4th Conference on Robot Learning (CoRL)},
  series    = {Proceedings of Machine Learning Research},
  year      = {2020}
}
```
(CoRL 2020 = PMLR vol. 155; add volume/pages if a reviewer wants them.)

## Novelty / publication impact
**No damage; small positive.** It costs one related-work-adjacent citation and, if we take the recommended
placement, converts our bias-limitation future-work sentence from a hand-wave into a precedent-backed claim.
Wording only; contribution untouched.
