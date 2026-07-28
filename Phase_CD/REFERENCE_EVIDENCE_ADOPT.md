# ADoPT — paired claim/evidence sheet

## STATUS: ☑ AUDITED & APPROVED (Srinivasa, 2026-07-26) — re-verified 2026-07-28
Re-read in full 2026-07-28 (**all 17 pages incl. Appendices A, B, C**) under the verbatim-only
standard. **Substance fully intact; one paraphrase-inside-quotes corrected (M-1), zero manuscript
impact.** Sign-off stands.

**Result of the re-audit:**
- ✅ `related.tex` clause *"point-level temporal consistency"* is **their literal title phrase**
- ✅ 9 of 10 quotes exact; 2 apparent failures were line-break artifacts, not errors
- ❌ **M-1**: one quote paraphrased and mis-attributed to §1 — corrected below
- ✅ "37-ref bibliography" claim **confirmed** (refs run `1.`–`37.`)
- ⭐ The camouflage corroboration is **stronger than previously recorded** — see the sharpened
  argument below, now with their Appendix C reasoning quoted in full

**The paper:** Minkyoung Cho¹, Yulong Cao², Zixiang Zhou¹, Z. Morley Mao¹ (¹University of
Michigan, ²NVIDIA Research), *"ADoPT: LiDAR Spoofing Attack Detection Based on Point-Level
Temporal Consistency"*, **BMVC 2023**, arXiv:2310.14504v1 [cs.CV], 23 Oct 2023.
PDF: `Phase_CD/Research paper/ADoPT.pdf` (17 pages incl. appendices, intact, ends `%%EOF`).
⚠ The arXiv PDF carries **no venue stamp** (LNCS format); BMVC 2023 rests on public record. The
acknowledgements do thank *"our area chairs and anonymous reviewers"*, consistent with a
reviewed conference.

---

## ❌ M-1 — THE MISQUOTE (the only defect found)

| | |
|---|---|
| **Dossier said** | *"measures temporal consistency at the point cloud level"* — attributed to **§1** |
| **§1 actually says** | "This understanding enables **the measurement of** temporal consistency at the point cloud level." (p.2) |
| **§7 actually says** | "…by **measuring** temporal consistency at the point cloud level." (p.12) |
| **Two problems** | (a) "the measurement of" was rewritten as "measures" **inside quotation marks**; (b) the phrasing quoted is closer to **§7**, but was cited as **§1** |
| **Manuscript impact** | **NONE** — never quoted in `related.tex` |
| **Status** | Corrected in Part A (**Q2a/Q2b**, both sections now given exactly) |

---

# 🔍 HOW TO AUDIT THIS (~10 min)

### ⚠️ TRAP — line-break hyphenation (worse in this PDF than most)
Two dossier quotes look wrong but are correct; the file simply breaks them:

| Reads continuously | In the file |
|---|---|
| "most failure cases arise when spoofed objects are attached…" | `most`⏎`failure cases … are at-`⏎`tached` (**two** breaks) |
| "does not significantly affect existing navigation decisions" | `does not significantly affect`⏎`existing navigation decisions` |

Every fragment in Part A was **executed against the extracted text** before being written down.

---

# PART A — THEY WROTE (verbatim only)

> **Nothing in this table is ours.** Reproduced word for word. `…` marks omissions.

| ID | Their exact words | Page / § | ✅ TESTED fragment |
|---|---|---|---|
| **Q1** | "we propose a novel framework, named ADoPT (Anomaly Detection based on Point-level Temporal consistency), which quantitatively measures temporal consistency across consecutive frames and identifies abnormal objects based on the coherency of point clusters" | p.1, Abstract | `quantitatively measures tem` ⚠break |
| **Q2a** ✅corrected | "This understanding enables the measurement of temporal consistency at the point cloud level." | p.2, **§1** | `point cloud level` |
| **Q2b** ✅corrected | "We present the ADoPT framework, designed to detect LiDAR spoofing attacks on AVs by measuring temporal consistency at the point cloud level." | p.12, **§7** | `by measuring temporal consistency` |
| **Q3** | "…the observation that injected points demonstrate poor temporal consistency — appearing inconsistently within the point cloud frame over time…" | p.5, §5 | `injected points demonstrate poor temporal consistency` |
| **Q4** | "Dense point injection attacks inject up to 200 points and achieve a high Attack Success Rate (ASR) of 96%-97%… sparse point injection attacks inject up to 64 points… with an ASR of less than 21%." | p.4, §4 | `inject up to 200 points` |
| **Q5** | "As we employ the spatial clustering method for attack detection, most failure cases arise when spoofed objects are attached to benign road objects." | **p.11, §6.2** | `failure cases arise when spoofed` ⚠2 breaks |
| **Q6** | "Although classified as false negatives, the spoofed object is identified as part of the benign object it is attached to; thus, it does not significantly affect existing navigation decisions or trigger numerous sudden alarms." | p.11, §6.2 | `does not significantly affect` ⚠break |
| **Q7** | "Using spatial clustering for attack detection predominantly fails when spoofed points are near benign road objects… While this leads to a false negative, it does not markedly influence driving decisions or result in the failure to trigger true alarms, **considering the imperative to avoid collisions with the benign object that remains in place**." | **p.17, Appendix C** | `predominantly fails when spoofed` |
| **Q8** | "While currently focused on single-frame fake object injection attacks, ADoPT has the potential to address LiDAR spoofing attacks spanning consecutive frames…" | p.12, §7 | `While currently focused on single-frame fake object injection attacks` |
| **Q9** | "We utilize 10 historical frames at a 10 Hz frequency to align with 3D-TC, allowing for a fair comparison…" | p.11, §6.1 | `10 historical frames` |
| **Q10** | "Harnessing the rich and comprehensive information present in raw sensor data [36,4], our approach offers profound advantages…" | p.2, §1 | `rich and comprehensive information` |
| **Q11** | title: "ADoPT: LiDAR Spoofing Attack Detection Based on **Point-Level Temporal Consistency**" | p.1, title | `Point-Level Temporal Consistency` |

### Their numbers — verified against Table 1 (p.9)

| | FP↓ | TP D.CAR | TP D.CYL | TP D.PED | sparse FP↓ | TP S.CAR |
|---|---|---|---|---|---|---|
| CARLO | 47.2 | 48.0 | 49.4 | 48.0 | 47.9 | 54.4 |
| 3D-TC2 (PP) | 20.7 | 98.6 | 95.0 | 56.9 | 16.6 | 53.5 |
| 3D-TC2 (SEC) | 19.6 | 98.3 | 45.8 | 47.5 | 16.3 | 84.2 |
| **ADoPT** | **4.5** | **97.2** | **98.3** | **95.2** | **9.3** | **85.4** |

Abstract's *"< 10% false positive, > 85% true positive"* ✅ consistent. Latency 2.1 s, reducible
to 0.7 s at ~87% of accuracy (§6.2) ✅. Bibliography = **37 refs** ✅.

---

# PART B — OUR `.tex` TEXT → WHICH QUOTE BACKS IT

## USE 1 — the ONLY use, **verified 2026-07-28** — `related.tex` lines **150–162** (`\cite{adopt2023}` at line 154; sentence shared with 3D-TC2)

> ✅ **"Only use" is now PROVEN, not assumed.** Searched `sections/*.tex`, `main.tex`,
> `highlights.tex`: the key `adopt2023` occurs **once**; the name `ADoPT` occurs **once**, same
> line. No orphan discussion.
>
> ⚠️ **Line numbers drift** — was `~117–122` until a paragraph was inserted above on 2026-07-28.
> Anchor on the `\cite` key: `grep -n "adopt2023" sections/*.tex`

**WE WRITE (verbatim from our manuscript):** "A separate line detects LiDAR spoofing against a
\emph{single} vehicle by exploiting temporal structure in its own sensor stream, e.g.\
motion-induced consistency in 3D-TC2~\cite{tc2_2021} and point-level temporal consistency in
ADoPT~\cite{adopt2023}. These methods test whether observations from a single sensor remain
temporally self-consistent."

| Our clause | Backed by |
|---|---|
| "**point-level temporal consistency**" | **Q11** — *their own title*. Verbatim; nothing to polish |
| "detects LiDAR spoofing against a **single** vehicle" | **Q4** (ego-LiDAR injection threat model) + **D-1** |
| "exploiting temporal structure in its own sensor stream" | **Q1**, **Q3**, **Q9** |
| "test whether observations from a single sensor remain temporally self-consistent" | **Q3**, **Q2a/Q2b** |

**VERDICT: ✅ VERIFIED — no manuscript change needed.**

---

# PART C — OUR INFERENCE (our words, NOT theirs)

- **C-1 — the reference-signal argument** (their check keys on *the ego's own past*; ours on *a
  neighbour's claim vs the verifier's own sensing*). Analytic contrast, not their text.
- **C-2 — 🔑 "their harmlessness argument does not transfer to our setting."** Ours entirely.
  See the sharpened corroboration below. Defensible from **Q6**+**Q7**, but it is our reasoning
  about *our* scenario and must never be attributed to them.

---

# PART D — VERIFIED BY ABSENCE

**D-1 — ADoPT's mechanism is single-vehicle.**

⚠️ **Important qualification — do NOT overstate this.** Unlike 3D-TC2 (which has *zero* hits),
ADoPT **does cite cooperative perception**: **Cooper** (ICDCS'19, ref [4]) and **EMP:
Edge-Assisted Multi-Vehicle Perception** (MobiCom'21, ref [36]). A blanket claim that
"cooperative perception appears nowhere" would be **false**.

What is true, and what our clause actually needs: **both are cited only as evidence that raw
sensor data is information-rich** — see **Q10**, *"Harnessing the rich and comprehensive
information present in raw sensor data [36,4]"*. Neither contributes a mechanism. **ADoPT
consumes only the ego vehicle's own historical frames F₁…F_L against its own incoming frame
F_{L+1}** (§5, **Q9**). The "single sensor" clause is therefore correct as written.

---

# ⭐ CORROBORATION — their own failure mode IS our camouflage attack

The strongest external support in the whole dossier set, and it is the authors' own words.

**Q5 (§6.2):** *"most failure cases arise when spoofed objects are **attached to benign road
objects**."*

That is precisely our camouflage placement — a phantom flush against real structure, so it
merges into the real object's cluster and is missed. **The strongest single-vehicle temporal
defense in the literature concedes exactly the geometry our attack uses.**

**They then dismiss the harm** — and their stated reason is what matters (**Q7**, Appendix C):

> *"…it does not markedly influence driving decisions… **considering the imperative to avoid
> collisions with the benign object that remains in place**."*

**Why that reasoning does not transfer (C-2, ours):** their argument holds because avoiding the
real object also avoids anything stuck to it — true for a free-standing car in an open lane. In
**our** setting the camouflage phantom **extends a real obstacle across the corridor gap the
drone must pass through**. Avoiding the real obstacle does *not* avoid the phantom's claimed
extent; the passage is closed. Their harmlessness argument is **scenario-dependent**, and
gap-navigation is the scenario where it breaks.

**Q8 (§7):** *"While currently focused on **single-frame** fake object injection attacks…"* —
same limitation class as 3D-TC2 and PRBI. A persistent fabrication established from frame 1 is
temporally self-consistent.

⚠ **Posture to keep:** `related.tex` makes **no claim** about ADoPT's behaviour on our attack.
That is correct and fair — different threat, different platform. Hold **Q5/Q7** in reserve for a
reviewer who asks *"wouldn't a point-level temporal check catch your camouflage phantom?"*
The answer is their own §6.2 plus the scenario argument above.

---

## Second-order sweep — full 37-ref bibliography scanned 2026-07-17, count re-confirmed 2026-07-28
**Zero new family members.** Single-vehicle LiDAR attack line (Petit, Shin, Yan DefCon,
Cao/Sato/Sun, roadside physical attacks); single-vehicle defenses already bracketed (CARLO,
Shadow-Catcher, LOP/"Wraith", 3D-TC2 [35], AdvIT, PercepGuard); Liu & Park TDSC'21 (one
vehicle's own multi-sensor cross-check — out of family); scene-flow/registration methodology
(ICP, NSFP, FlowNet3D, PointPWC, neural prior, DCD); detectors/datasets (PointPillars, SECOND,
nuScenes, Argoverse); and **two benign cooperative-perception architectures — Cooper [4] and
EMP [36] — CP plumbing with no attacker and no trust model.** No defense-family member.

## Bookkeeping
- `refs.bib` `adopt2023`: title exact ✅ (capitalization-protected `{ADoPT}`), authors
  Cho/Cao/Zhou/Mao ✅, BMVC 2023 ✅ (public record; arXiv v1 itself carries no venue stamp),
  arXiv:2310.14504 ✅.
- No manuscript edits arise from this audit.

## Re-audit changelog (2026-07-28)
1. **M-1 corrected** — the paraphrased-and-mis-attributed "point cloud level" quote replaced by
   the exact §1 and §7 sentences (**Q2a**, **Q2b**).
2. Restructured into **Parts A–D**; the old *"THEY WROTE, phrase by phrase"* heading mixed
   quotes, absence claims and our inference.
3. Every fragment executed before being written; two line-break traps documented.
4. **D-1 qualified** — flagged that ADoPT *does* cite cooperative perception (Cooper, EMP), so
   the absence claim must be about the **mechanism**, not the citations. Previously stated
   correctly but easy to over-read.
5. Camouflage corroboration **sharpened** with Appendix C's full reasoning (**Q7**), making
   explicit why their harmlessness argument fails in gap-navigation.
6. Numbers cross-checked against Table 1 and the 37-entry reference list.

_Standing rule: not closed until Srinivasa signs (`AUDIT_PENDING.md`). Committed ≠ audited._
