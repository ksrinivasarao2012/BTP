# LiDAR-Spoofing Safe Control — paired claim/evidence sheet (full read, 2026-07-28)

## STATUS: ☐ AWAITING SRINIVASA'S AUDIT
Full 9-page read of the PDF, every line including references. **Must-cite #1 of the 7** produced
by the forward-citation sweep; first of the 8 missing dossiers to be built.

**The paper:** Hongchao Zhang\*, Zhouchi Li\*, Shiyu Cheng, Andrew Clark (\*equal contribution),
*"Cooperative Perception for Safe Control of Autonomous Vehicles under LiDAR Spoofing Attacks"*,
**Symposium on Vehicles Security and Privacy (VehicleSec) 2023**, 27 Feb 2023, San Diego —
ISBN 1-891562-88-6, DOI 10.14722/vehiclesec.2023.23066, co-located with NDSS.
arXiv:2302.07341v1 [eess.SY], 14 Feb 2023. Washington University in St. Louis + Worcester
Polytechnic Institute; NSF grant CNS-1941670.
PDF: `Phase_CD/Research paper/LiDAR_Spoofing_SafeControl.pdf` (9 pages).

---

## 📐 STRUCTURE OF THIS FILE — read this once

Srinivasa's instruction, 2026-07-28: **"in the THEY WROTE place it should exactly match with the
paper writing; create a separate place for your inference."** This file is therefore split so
that the authors' words and our reasoning can never be confused:

| Part | Contains | Rule |
|---|---|---|
| **A** | **THEY WROTE** | **ONLY the authors' exact words.** Nothing of ours. Every entry carries a page, a section, and a Ctrl+F fragment that has been **executed against the file** |
| **B** | Our `.tex` text → which quote backs it | mapping only |
| **C** | **OUR INFERENCE** | our reasoning, never attributable to them |
| **D** | **VERIFIED BY ABSENCE** | claims proved by finding nothing, with the searches to reproduce |

**Why the split exists.** An earlier version of this file put quotes, synthesis and inference
under a single *"THEY WROTE"* heading. That laundered our reasoning into their authority — the
same defect that made the CATS differentiator wrong. Srinivasa caught it.

---

# 🔍 HOW TO AUDIT THIS (~15 min)

Open `Phase_CD/Research paper/LiDAR_Spoofing_SafeControl.pdf`.

### ⚠️ TRAP 1 — ligatures. Ctrl+F for `spoofing` returns ZERO hits.
The PDF stores "spoofing" as `spoo` + **ﬁ** + `ng`. Affected: *spoofing, identification,
classification, verified, first, defined, artificial*. **Search `spoo` instead.**

### ⚠️ TRAP 2 — hyphenation across line breaks.
The PDF splits words at line ends (`co-`⏎`ordination`, `kine-`⏎`matic`, `Discrete-`⏎`Time`), so a
phrase that reads continuously on the page will not match as a search string.

**Because of these two traps, every fragment in Part A was executed against the extracted text
before being written down.** Three of my first attempts failed and were replaced:

| ❌ Failed | ✅ Replacement |
|---|---|
| `burdensome level of coordination` | `burdensome level of` |
| `initialize two vehicles` | `two vehicles, denoted as` |
| `Discrete-Time Control Barrier Function` | `Model Predictive Control with Discrete` |

### ✅ One-minute check that our own correction was right
Our sweep file previously claimed *"no conclusion section exists"*. Go to **p.8, bottom** — you
will see **`VI. CONCLUSION`**, continuing onto p.9. The old note was **wrong**; corrected.

### What you are being asked to decide
1. 🚨 **Clause C-5** — we assert a **priority claim on the authors' behalf**. Keep or soften?
   (Recommendation: **soften**.)
2. Whether the two `related.tex` passages are fair to the paper.
3. Whether to authorise the forward sweep of this paper's citation tree (Open Item 1).

---

# PART A — THEY WROTE (verbatim only)

> **Nothing in this table is ours.** Prose is reproduced word for word. Where a quote contains
> mathematics, subscripts are rendered readably (`Ob k` → `O^b_k`) and spaces the PDF extractor
> dropped around symbols are restored — **the words are untouched**. Such entries are marked ⓜ.
> Ellipses `…` mark text we omitted; nothing else is altered.

| ID | Their exact words | Page / §  | ✅ TESTED Ctrl+F fragment |
|---|---|---|---|
| **Q1** | "This approach exploits the fact that spoofing attacks can typically only be mounted on one vehicle at a time, and introduce additional points into the victim's scan that can be readily detected by comparison from other, non-modified scans." | p.1, Abstract | `only be mounted on one vehicle` |
| **Q2** | "We propose a control algorithm that guarantees that these estimated object locations are avoided." | p.1, Abstract | `guarantees that these estimated object` |
| **Q3** | "simultaneously spoofing multiple vehicles in a believable manner would involve a burdensome level of coordination among multiple distributed spoofers" | p.1, §I | `burdensome level of` ⚠hyphen |
| **Q4** | "While these spurious points may fool the targeted sensor, they will be absent from the scans of neighboring vehicles." | p.1, §I | `will be absent from` |
| **Q5** | "to the best of our knowledge this information sharing has not been used to detect and mitigate spoofing attacks" | p.1, §I | `this information sharing` ⚠hyphen *(not "…sharing has not been used" — PDF breaks after `has`)* |
| **Q6** | "Attacks on the positioning of the vehicle are out of scope." | p.2, §III-B | `are out of scope` |
| **Q7** | "In this paper, we assume that at most one attack occurs. The attack could be any of attacks NEO, PRA, or AO, and the autonomous vehicle (AV) does not know the attack type a priori." | p.3, §III-B | `at most one attack occurs` |
| **Q8** | "Due to the physical limitation of the spoofing hardware, the injected point can only be within a very narrow spoofing angle. Hence, in this paper, we assume that the relay adversary can only spoof one LiDAR sensor." | p.3, §III-B (NEO) | `can only spoof one LiDAR` |
| **Q9** ⓜ | "Formally, the occupied area U_jk is computed as the convex hull of P(O^b_k(x,S)) ∪ O^p_k(x,S)." | p.3, §IV-A | `occupied area Ujk is computed` |
| **Q10** ⓜ | "…which consists of the points where a straight line from the sensor to each point in O^b_k(x,S) intersects the ground." | p.3, §IV-A | `intersects the ground` |
| **Q11** ⓜ | "We enhance the robustness of these sampling errors by changing the boundaries of the occupied area to h^jk_l(x) − ‖a^jk_l‖ζ_h ≤ 0, where **ζ_h = ζ_n + ζ_r**, where ζ_n is the observation noise bound and ζ_r is a bound on the distance between neighboring sample points that can be obtained from the distance to the object and the angular resolution of the LiDAR." | p.3, §IV-A | `observation noise bound` |
| **Q12** | "At each time, Agent A collects the current observations of nearby agents…" | p.4, §IV-B | `collects the current observations` |
| **Q13** | "Agent A requests point cloud from nearby agents, i.e., Agent j." | p.4, Fig. 2 caption | `requests point cloud from` |
| **Q14** ⓜ | "If P(O^b_k(x_A,S_A ∪ e′)) \ U_Bk ≠ ∅, then Agent A is being targeted by an attack of type NEO." | p.5, **Lemma 2** | `being targeted by an attack of type NEO` |
| **Q15** | "In order to avoid collision between the vehicle and the unsafe region, we utilize Model Predictive Control with Discrete-Time Control Barrier Function (MPC-CBF)." | p.6, §IV-C | `Model Predictive Control with Discrete` ⚠hyphen |
| **Q16** | "The kine-matic bicycle model [16] adopted in this paper is defined as" | p.6, §IV-C | `bicycle model` ⚠hyphen |
| **Q17** | "We consider CARLA vehicle Model-3 as our control object and use (2) as the simplified vehicle model with l = 4 and dt = 0.03." | p.7, §V-B | `l = 4 and dt` |
| **Q18** | "We initialize two vehicles, denoted as Agents A and B, at locations (−54.34, 137.05) and (−34.34, 137.05), respectively." | p.7, §V-A | `two vehicles, denoted as` ⚠hyphen |
| **Q19** | "the vehicle drives from the location (−14.34, 137.05) to (−5.00, 135.25) without entering the unsafe region." | p.7, §V-B | `without entering the unsafe region` |
| **Q20** | "vehicles exchange LiDAR scan data and identify spoofing attacks by checking for disparities between the detected obstacles under each scan." | **p.9, §VI Conclusion** | `for disparities between the detected` ⚠hyphen |
| **Q21** | "we use the 3D bounding box provided by the LiDAR-based 3D object detection algorithms of the autonomous vehicles (AVs) [27]" | p.3, §IV-A | `bounding box provided` |
| **Q22** | "l is the wheelbase" | p.6, §IV-C | `is the wheelbase` |

---

# PART B — OUR `.tex` TEXT → WHICH QUOTE BACKS IT

## USE 1 — `related.tex` lines 33–64 (the differentiator paragraph)

**WE WRITE (verbatim from our manuscript):** "Earlier than these, and the first work to carry a
cross-agent fabrication check through to a control guarantee, is the cooperative fault-detection
framework of Zhang, Li, Cheng, and Clark~\cite{lidarspoof2023}. A victim vehicle requests point
clouds from its neighbours and tests whether the projection of an obstacle it has detected is
contained in the \emph{occupied area} --- a convex hull of projected and obliquely projected
returns --- computed from a neighbour's scan; a containment failure identifies a non-existing,
i.e.\ fabricated, obstacle, and the reconstructed unsafe region is then enforced by a
model-predictive controller with discrete-time control-barrier constraints that guarantees the
estimated object locations are avoided. We do not claim the pairing of a cross-agent consistency
check with a control layer as novel. Three assumptions nevertheless separate that work from ours.
Its threat model assumes that at most one attack occurs and that a relay adversary can spoof only
one LiDAR sensor, on the stated grounds that spoofing several vehicles believably would demand
burdensome coordination among distributed spoofers; the detector inherits this assumption, since
a phantom is exposed precisely by its absence from an uncompromised neighbour's scan. Ours is the
complementary threat: the liars are the neighbours themselves, they may number up to seven of
ten, and the phantom is broadcast as a claim rather than injected into a victim's raw scan.
Second, observation noise enters as a fixed deterministic margin, the occupied-area boundaries
being inflated by an observation-noise bound plus a LiDAR-resolution bound. Such inflation is
conservative by construction and cannot by itself accuse an honest neighbour, but neither does it
produce the honest-disagreement regime we study, in which a tolerance wide enough to accommodate
noisy honest neighbours is also wide enough to conceal a camouflaged phantom. Third, the test is
per-frame and stateless --- neighbour scans are collected afresh at each time step and no
per-neighbour quantity persists across frames --- whereas our discriminator is a statistic
accumulated per neighbour over time. Their validation is a two-vehicle CARLA study reported
qualitatively, giving detection outcomes per attack type and a single reach-and-avoid trajectory
rather than a success rate over trials."

| Our clause | Backed by |
|---|---|
| "requests point clouds from its neighbours" | **Q13**, **Q12** |
| "occupied area — a convex hull of projected and obliquely projected returns" | **Q9**, **Q10** |
| "a containment failure identifies a non-existing … obstacle" | **Q14** |
| "model-predictive controller with discrete-time control-barrier constraints" | **Q15** |
| "guarantees the estimated object locations are avoided" | **Q2** (near-verbatim of their sentence) |
| "at most one attack occurs" | **Q7** (verbatim) |
| "a relay adversary can spoof only one LiDAR sensor" | **Q8** (verbatim), **Q1** |
| "spoofing several vehicles believably would demand burdensome coordination among distributed spoofers" | **Q3** |
| "a phantom is exposed precisely by its absence from an uncompromised neighbour's scan" | **Q4** |
| "observation noise enters as a fixed deterministic margin … observation-noise bound plus a LiDAR-resolution bound" | **Q11** |
| "neighbour scans are collected afresh at each time step" | **Q12** |
| "two-vehicle CARLA study" | **Q18** |
| "a single reach-and-avoid trajectory" | **Q19** |
| "the first work to carry a cross-agent fabrication check through to a control guarantee" | ⚠ **NOT BACKED BY ANY QUOTE — see C-5** |
| "no per-neighbour quantity persists across frames" | **D-1** (absence) |
| "rather than a success rate over trials" | **D-3** (absence) |
| "the liars are the neighbours themselves … up to seven of ten" | **C-1** (ours — describes *our* work) |

## USE 2 — `related.tex` lines **223–250** (`\cite{lidarspoof2023}` at line 233) — why it is not a transplantable baseline

> ✅ **Citation sites verified 2026-07-28:** the key `lidarspoof2023` occurs **exactly twice**
> across `sections/*.tex`, `main.tex` and `highlights.tex` — line 35 (USE 1) and line 233
> (USE 2). Both are documented here; there is no third, undocumented use.
> ⚠️ Line numbers drift — anchor on the key: `grep -n "lidarspoof2023" sections/*.tex`

**WE WRITE (verbatim from our manuscript):** "The cooperative fault-detection
framework~\cite{lidarspoof2023} is closer in spirit but likewise not transplantable: its detector
consumes raw point clouds and per-agent occupied areas rather than the object-level claims our
agents exchange, and its safety argument is discharged by a model-predictive controller on a
kinematic vehicle model rather than by a learned policy, so porting it would replace both our
message format and our control layer."

| Our clause | Backed by |
|---|---|
| "consumes raw point clouds" | **Q20** ("exchange LiDAR scan data"), **Q12** |
| "per-agent occupied areas" | **Q9** (the `U_jk` per-agent-per-obstacle definition) |
| "a model-predictive controller on a kinematic vehicle model" | **Q15**, **Q16**, **Q17**, **Q22** |
| "rather than by a learned policy" | **D-2** (absence) + **Q21** (their detector is off-the-shelf) |
| "porting it would replace both our message format and our control layer" | **C-4** (ours) |

---

# PART C — OUR INFERENCE (our words, NOT theirs)

**Nothing here may be attributed to the authors.** These are our readings; each is defensible
from Part A but none is a sentence they wrote.

- **C-1 — "the liars are the neighbours themselves, up to seven of ten."** Describes **our**
  threat model, contrasted with theirs. Not a claim about their paper.
- **C-2 — "inflation is conservative by construction and cannot by itself accuse an honest
  neighbour."** Our reading of the *sign* of the term in **Q11**: the margin **enlarges** the
  occupied area, so containment is easier to satisfy and a containment failure — the accusation —
  is harder to trigger. Structurally sound, but it is our observation, not their statement.
- **C-3 — "the detector inherits this assumption."** Our inference linking **Q7/Q8** (threat model)
  to **Q4/Q14** (the mechanism). They never write the word "inherits".
- **C-4 — "porting it would replace both our message format and our control layer."** Our
  reasoning from Q9/Q12/Q15–Q17. Entirely about *our* benchmark.
- **C-5 — 🚨 "the first work to carry a cross-agent fabrication check through to a control
  guarantee."** **A PRIORITY CLAIM WE MAKE ON THEIR BEHALF.** Their own text (**Q5**) claims only
  the weaker *"this information sharing has not been used to detect and mitigate spoofing
  attacks."* We have **not** swept their citation tree, so we cannot substantiate a "first".
  **Recommendation: soften to "an early work that carries…"** — asserting a third party's
  priority carries our risk with none of the benefit.
- **C-6 — the verification-direction argument** (see below). Ours entirely; it is an analytic
  contrast, not a claim about their text.

### C-6 in full — the sharpest distinction, and it is our analysis
- **Theirs:** the **ego is the victim**; its own scan was corrupted by an external spoofer.
  Neighbours are **assumed honest** and are used to vindicate or refute the ego's own perception.
  Trust flows **neighbour → ego**.
- **Ours:** the **neighbour is the liar**; the ego's own sensing checks a neighbour's broadcast
  claim. Trust flows **ego → neighbour**.

Their central premise (**Q4**) — *the phantom is absent from neighbours' scans* — **inverts** in
our regime, where the phantom originates *with* the neighbours and up to seven of ten assert it.
This is the cleanest one-sentence differentiator available and should survive into the final text.

---

# PART D — VERIFIED BY ABSENCE

Claims established by finding **nothing**. These are the ones a reader cannot confirm from a
quote, so each carries the search to reproduce it. **These are the highest-value checks in this
file** — if any fails, a `related.tex` clause is wrong.

| ID | Our claim | Search the PDF for | Expected |
|---|---|---|---|
| **D-1** | "no per-neighbour quantity persists across frames" | `trust` · `reputation` · `history` · `previous frame` | **no hits** in a detection sense. The only temporal element is MPC's receding horizon — *control* lookahead, not *detection* memory |
| **D-2** | "rather than by a learned policy" | `train` · `learn` · `neural` · `network` | appears only in related-work citations, **never as their own method**. Their detector front end is off-the-shelf (**Q21**, ref [27] = Zamanakos et al., *a survey*) |
| **D-3** | "no success rate over trials" | `Table` · `accuracy` · `%` · `rate` | **no results table exists anywhere in the paper.** All results are figures + prose (Figs. 4–6), plus the single trajectory of **Q19** |

---

# The 3-question test

| Q | Test | This paper | Verdict |
|---|---|---|---|
| **Q1** | Closed-loop navigation scored by **task success**? | Closed loop ✅ (MPC-CBF drives the car) but **not scored by task success** — one qualitative trajectory (**Q19**), no success rate (**D-3**) | **PARTIAL** |
| **Q2** | Sensor noise making **honest agents disagree**? | ❌ Noise is a **deterministic bound** folded into a conservative margin (**Q11**). Honest disagreement is engineered away, never studied as a regime | **NO** |
| **Q3** | Per-neighbour statistic **accumulated across frames**? | ❌ Per-frame, stateless (**Q12**, **D-1**) | **NO** |

**NOT A PRE-EMPTION.** Closest paper in *threat model* — fabricated obstacles + cross-agent
comparison + control — and we say so plainly. Fails Q2 and Q3 outright; Q1 only partially.

---

# ⚠️ OPEN ITEMS OWED

1. 🚨 **Its forward-citation tree has never been swept.** Published Feb 2023 — **3.5 years** of
   citers, and by our own ledger the closest paper to this project. If a pre-emption of the
   compound claim exists anywhere, the likeliest place is work building directly on this.
   **Highest-value remaining prior-art task.**
2. **C-5 priority claim** — keep or soften. Recommendation: **soften**.
3. Confirm the VehicleSec venue string against the official proceedings listing. We took it
   verbatim from the paper's own p.1 footer — strong, but it is the camera-ready's
   self-description rather than an independent record.

---

## Record of corrections to our own files, made while building this dossier
- **`FORWARD_CITATION_SWEEP.md` Part 0c** said *"No conclusion section exists"* → **WRONG**, §VI is
  on pp. 8–9 (**Q20** is from it). An abstract-grade error caught only by the full read. Corrected.
- **This file, first version** put quotes, synthesis and inference under one *"THEY WROTE"*
  heading, and shipped **three untested Ctrl+F strings, two of which did not match**. Both
  defects caught by Srinivasa. Restructured into Parts A–D; every fragment now executed first.

_Standing rule: not closed until Srinivasa personally audits it (`AUDIT_PENDING.md`).
Committed ≠ audited._
