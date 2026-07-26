# Nice-to-have citations (NOT must-have) — optional related-work additions

**What this file is.** During the full abstract sweep of every dossiered paper's bibliography
(`SECOND_ORDER_FULL_ABSTRACT_SWEEP.md`), some references turned out to be *legitimately related* but
**not pre-empting** our contribution. None of these are required — the paper is complete, correct, and
novel without any of them. They are logged here only so Srinivasa can decide, at related-work polish time,
whether to spend a sentence adding breadth.

**Hard rule (be honest):** every row below is **OPTIONAL**. Dropping all of them carries **zero risk** to
correctness or the novelty claim. This file exists so nothing is silently forgotten — not because anything
here is owed. A row graduates to the manuscript only if Srinivasa says so.

**Columns:** *Ref* = paper · *Found in* = whose bibliography surfaced it · *What it is* = one-line gist ·
*Why nice-to-have* = the marginal upside of citing it · *Priority* = how much it would add (all are ≤ low).

---

## From CAD's bibliography (swept 2026-07-26)

| Ref | Found in | What it is | Why nice-to-have | Priority |
|-----|----------|-----------|------------------|----------|
| **MISO-V** — Liu et al., *Misbehavior Detection for Collective Perception Services in Vehicular Communications* (IEEE IV 2021) | CAD [57] | Classical (rule-based) misbehavior detection that exploits **multiple vehicles' overlapping observations** to cross-verify the semantic correctness of collective-perception messages. | The **closest classical ancestor** of our "verify a peer's claim against what I also observe." Citing it in one sentence lets us explicitly say our learned, noise-aware, **temporal** filter differs from this classical rule-based cross-verification line — strengthens the related-work framing and pre-empts a V2X-misbehavior reviewer. | Low (highest-value of the three) |
| **Ambrosin et al.** — *Design of a Misbehavior Detection System for Objects-Based Shared Perception V2X Applications* (IEEE ITSC 2019) | CAD [23] | Rule/plausibility-based misbehavior-detection **system design** at the collective-perception-message (CPM) layer. | A second representative of the classical CPM-misbehavior-detection family. Redundant once MISO-V is cited; include only if you want two exemplars of the classical line. | Very low (redundant after MISO-V) |
| **OCEAN** — Zhao et al., *A Collaborative V2X Data Correction Method for Road Safety* (IEEE T-Reliability 2022) | CAD [89] | Rationality + Q-learning method that **detects and corrects** erroneous V2X data from defective sensors **or selfish senders** (~80% detection). | Handles "selfish" (adversarial-ish) senders, so it's tangentially in our threat space — but it operates on **V2X message attributes** (BSM-style), not shared-obstacle perception fusion, and has no learned navigation / no ranging-noise regime / no adaptive attacker. Weakest link of the three; cite only for completeness if a reviewer pushes on "data correction." | Very low |

**Note on coverage:** our manuscript already cites CAD, MADE, and MATE, which collectively represent the
collaborative-perception-security / misbehavior-detection family. The three rows above are *additional*
classical exemplars, not gaps. Recommended default = **cite none**, or at most **MISO-V alone** as one
sentence if you want the maximally-thorough related-work section.

---

## From PRBI's bibliography (swept 2026-07-26) — HIGHER priority than the CAD set

These three are **direct siblings of ROBOSAC and MADE, which we already cite**. None pre-empts us (all are
AP/detection-scored feature-level CP defenses/attacks — no learned-navigation-success metric, no ranging-noise
honest-disagreement regime, no cross-agent temporal offset test, no adaptive attacker). But because they are
**recent, named SOTA CP malicious-agent defenses in exactly the family paragraph we already write**, a
CP-security reviewer is more likely to expect them than the CAD-set classics. Still optional — but if you add
any nice-to-haves at all, add these first. (This closes task #3: CP-Guard / CP-Guard+ / LUCIA triage.)

| Ref | Found in | What it is | Why nice-to-have | Priority |
|-----|----------|-----------|------------------|----------|
| **CP-Guard** — Hu et al., AAAI 2025 | PRBI [9] (also its "PASAC" baseline) | Per-agent CP defense: sample-consensus (**PASAC**) + collaborative-consistency loss vs ego; detects/removes malicious agents in BEV-segmentation CP. | Named SOTA CP defense in the exact ROBOSAC/MADE/PRBI family we contrast against; one clause differentiates it (BEV-seg AP metric, no navigation/noise/temporal/adaptive). | ⭐ **PLANNED CITE** (Srinivasa 2026-07-26) |

> **⭐ DECISION (Srinivasa, 2026-07-26): CP-Guard is a PLANNED cite, not merely optional.** Treat it like
> ROBOSAC: (1) **full-read + build `REFERENCE_EVIDENCE_CP_GUARD.md`** dossier (abstract triage above is only the
> first pass; the PDF was bot-blocked, so a manual pull may be needed); (2) add it to the defense-family
> sentence in `related.tex` alongside ROBOSAC/MADE/PRBI with a one-clause differentiator (BEV-segmentation AP
> metric; no closed-loop navigation objective, no ranging-noise honest-disagreement regime, no cross-agent
> temporal test, no adaptive attacker); (3) add `cpguard2025` to `refs.bib` (AAAI 2025, 39(22):23203–23211).
> **Owed before submission. Tracked in AUDIT_PENDING.md.** CP-Guard+ and LUCIA stay optional unless you want the
> feature-level / object-removal contrasts too.
| **CP-Guard+** — Hu et al., arXiv 2025 (2502.07807) | PRBI [8] | Feature-level malicious-agent detector needing no final-perception verification; contributes CP-GuardBench + Dual-Centered Contrastive Loss. | Recent follow-up to CP-Guard; same family. Redundant if CP-Guard is cited, unless you want the "feature-level, no output-verification" contrast. | Low |
| **LUCIA / "From Threat to Trust" (SOMBRA)** — Wang et al., USENIX Sec 2025 | PRBI [28] | Attention-fusion **object-removal** attack (SOMBRA) + attention-based defense in cooperative perception. | Recent CP attack+defense; complements our TrustFlip/CAD attack-side discussion (object *removal* vs our *fabrication*). | Low |

**Note:** all three PDFs were bot-blocked earlier (task #3), so this triage is **abstract-level**. If you
decide to cite CP-Guard, a full-read + dossier (like ROBOSAC) would be the thorough path before submission.

---

## From AerialTrust's bibliography (swept 2026-07-26) — RAS-community relevance

| Ref | Found in | What it is | Why nice-to-have | Priority |
|-----|----------|-----------|------------------|----------|
| **Cavorsi et al.** — "Exploiting Trust for Resilient Hypothesis Testing with Malicious Robots" (IEEE T-RO 2024, Gil group) | AerialTrust [7] | Resilient **binary hypothesis testing** in adversarial multi-robot crowdsensing; inter-robot **trust observations** tolerate malicious robots even when they **outnumber** legitimate ones. | **Closest Robotics-community (our target venue = Elsevier RAS) work** on trust-based resilience to a malicious majority. Doesn't pre-empt (different task: hypothesis-testing, not obstacle-perception+navigation; no ranging-noise/temporal), but a RAS reviewer may expect the robotics-trust lineage acknowledged. Resolves AUDIT_PENDING item 6. | Low (RAS-context; below CP-Guard) |

**Also noted (not tabled, even lower priority):** the classical **Byzantine-consensus** refs Grigoropoulos
(BFT for UAV missions) and Kihlstrom (Byzantine fault detectors) sit in the same bucket as our already-cited
Lamport — cite only if expanding the BFT-lineage sentence.

---

_Last updated 2026-07-26. Append new optional finds here as later bibliographies (TruPercept, CoDynTrust, …)
are swept; keep the "all optional, zero-risk-to-drop" framing. Nothing here is final until Srinivasa decides._
