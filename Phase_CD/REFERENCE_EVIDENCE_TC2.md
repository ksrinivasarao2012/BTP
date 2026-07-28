# 3D-TC2 — paired claim/evidence sheet

## STATUS: ☑ AUDITED & APPROVED (Srinivasa, 2026-07-26) — sign-off STANDS after 2026-07-28 re-verification
**Srinivasa's ruling 2026-07-28:** the re-verification changed **no finding, no `related.tex`
word, and no `refs.bib` field**. The single defect (**M-1**) was a paraphrase inside this file's
own notes that never reached the manuscript. His original audit therefore stands; this file is
**not** re-opened, and the re-audit is recorded as a rigour upgrade only.

Originally closed 2026-07-26 after Srinivasa's audit. **Re-verified 2026-07-28**
under the verbatim-only standard (Srinivasa: *"in the THEY WROTE place it should exactly match
the paper writing; create a separate place for your inference"*). Full 6-page re-read, every
line including all four tables.

**Result of the re-audit:**
- ✅ **Substance is correct.** The single `related.tex` sentence is accurate in every respect.
- ✅ **9 of 10 quotes are exact.**
- ❌ **1 real misquote found** — see **M-1** below. Small, meaning preserved, but words were
  changed *inside quotation marks*.
- ✅ **The absence claim is now proved with numbers** (it was previously asserted).
- ✅ All numeric claims verified against the tables.

**The paper:** Chengzeng You\*, Zhongyuan Hau\*, Soteris Demetriou (\*equal contribution),
Imperial College London, *"Temporal Consistency Checks to Detect LiDAR Spoofing Attacks on
Autonomous Vehicle Perception"*, **1st Workshop on Security and Privacy for Mobile AI
(MAISP '21)**, 24 June 2021, ACM, 6 pages. DOI 10.1145/3469261.3469406.
arXiv:2106.07833v1 [cs.CR], 15 Jun 2021.
⚠ **"3D-TC2" is the METHOD name, not the title.** `refs.bib` already records this correctly.
PDF: `Phase_CD/Research paper/3D-TC2.pdf` (6 pages, intact, ends with `%%EOF`).

---

## ❌ M-1 — THE MISQUOTE (the only defect found)

| | |
|---|---|
| **Dossier said** | spoofed box has *"**no** 'history' from the previous frames"* |
| **Paper actually says** | *"it **does not have** "history" from the previous frames"* (p.3, §3.3) |
| **Problem** | "no" was substituted for "does not have" **inside quotation marks**. The meaning survives; the discipline does not |
| **Also** | the paper uses curly double quotes `"history"`, the dossier used single quotes |
| **Impact on the manuscript** | **NONE** — this phrase is not quoted in `related.tex`; it appeared only in the dossier's supporting notes |
| **Status** | Corrected below in Part A (**Q9**) |

---

# 🔍 HOW TO AUDIT THIS (~10 min)

Open `Phase_CD/Research paper/3D-TC2.pdf`.

### ⚠️ TRAP — line-break hyphenation
This PDF splits words and phrases at line ends. **Three of the dossier's quotes look like
misquotes but are not** — they are simply broken across lines in the file:

| Reads continuously on the page | In the file |
|---|---|
| "leverages spatio-temporal information" | `leverages spatio-`⏎`temporal` |
| "a sequence of consecutive scenes" | `consecutive`⏎`scenes` |
| "the approach will fail to detect such object" | `the approach`⏎`will fail` |

**Every fragment in Part A below was executed against the extracted text before being written
down.** Searching the full phrase will fail; search the tested fragment.

---

# PART A — THEY WROTE (verbatim only)

> **Nothing in this table is ours.** Reproduced word for word. Ellipses `…` mark omissions;
> nothing else is altered.

| ID | Their exact words | Page / § | ✅ TESTED fragment |
|---|---|---|---|
| **Q1** | "In this work, we explore the use of motion as a physical invariant of genuine objects for detecting such attacks. Based on this, we propose a general methodology, 3D Temporal Consistency Check (3D-TC2), which leverages spatio-temporal information from motion prediction to verify objects detected by 3D Object Detectors." | p.1, Abstract | `motion as a physical invariant of genuine objects` |
| **Q2** | "In the AV driving setting, we expect that objects (and their motion trajectory) should be consistent across consecutive 3D LiDAR scenes and this temporal consistency would be disturbed when an adversary introduces a fake object." | p.1, §1 | `should be consistent across` |
| **Q3** | "Our work is the first to propose motion as a physical invariant for 3D objects which it leverages to perform temporal consistency checks on 3D point clouds." | p.2, §2 | `first to propose motion as a physical invariant` |
| **Q4** | "We assume A_static enjoys state of the art sensor spoofing capabilities and can inject ≤ 200 points in a 3D scene." | p.2, §3.1 | `200 points` |
| **Q5** | "The adversary can launch ghost attacks by spoofing front-near objects (5m-8m in front of the ego-vehicle)." | p.2, §3.1 | `5m-8m in front of the ego-vehicle` |
| **Q6** | "We consider a white-box model-level spoofing adversary who has full knowledge of the internals of both the victim model and the detection mechanism." | p.2, §3.1 | `white-box model-level spoofing` |
| **Q7** | "MotionNet takes a sequence of consecutive scenes (3D point-clouds) as input…" | p.3, §3.3 | `sequence of consecutive` ⚠break |
| **Q8** | "MotionNet uses K = 20 by default." | p.4, footnote 1 | `MotionNet uses` |
| **Q9** ✅corrected | "Under a single frame LiDAR spoofing attack, when an object is successfully injected, it does not have "history" from the previous frames and hence there is no equivalent motion prediction of such category for the current frame." | p.3, §3.3 | `does not have` |
| **Q10** | "However, if the hidden object is temporally consistent (i.e. an adversarial object is placed on the road as the ego-vehicle approaches it), the approach will fail to detect such object." | p.5, §4.4 | `will fail to detect` ⚠break |
| **Q11** | "We also intend to consider a stronger adversary that is able to perform injection into continuous frames (temporal attacks) and study the robustness of the 3D-TC2 approach to such attacks." | p.6, §5 | `injection into continuous frames` |
| **Q12** | "Current defences have been shown to be effective on static 3D object detection using only information from the individual target scene… missing rich spatio-temporal information from previous frames." | p.2, §2 | `individual target scene` |

### Their numbers — verified against the tables

| Claim | Source | ✓ |
|---|---|---|
| Car DSR 98.58% (PointPillars) / 98.28% (SECOND) | **Table 3**, p.6 | ✅ |
| Car recall 91.75% / 92.23% | **Table 3** | ✅ |
| Pedestrian DSR 56.92% / 47.47% (much worse) | **Table 3** | ✅ |
| 362 attacked key frames, nuScenes mini | §4, §4.2 | ✅ |
| 41 Hz; total runtime 24 ms; +5 ms overhead | **Table 4**, §4.3 | ✅ |
| Beats CARLO (94.5%) and Shadow-Catcher (94%) | §4.2 Conclusion | ✅ |
| Bibliography = **14 references** | ref list `[1]`–`[14]` | ✅ |

---

# PART B — OUR `.tex` TEXT → WHICH QUOTE BACKS IT

## USE 1 — the ONLY use, **verified 2026-07-28** — `related.tex` lines **150–162** (`\cite{tc2_2021}` at line 153)

> ✅ **"Only use" is now PROVEN, not assumed.** Two searches across `sections/*.tex`, `main.tex`
> and `highlights.tex`: (a) the key `tc2_2021` occurs **once**; (b) the name `3D-TC2` occurs
> **once**, at the same line. No orphan discussion elsewhere.
>
> ⚠️ **Line numbers drift.** They were `~117–122` until 2026-07-28, when a 32-line paragraph was
> inserted higher in `related.tex` and pushed everything down ~36 lines. **Anchor on the `\cite`
> key, not the line number**, and re-derive with:
> `grep -n "tc2_2021" sections/*.tex`

**WE WRITE (verbatim from our manuscript):** "A separate line detects LiDAR spoofing against a
\emph{single} vehicle by exploiting temporal structure in its own sensor stream, e.g.\
motion-induced consistency in 3D-TC2~\cite{tc2_2021} and point-level temporal consistency in
ADoPT~\cite{adopt2023}. These methods test whether observations from a single sensor remain
temporally self-consistent."

| Our clause | Backed by |
|---|---|
| "detects LiDAR spoofing against a **single** vehicle" | **Q5** (ego-vehicle threat model) + **D-1** (absence of any cross-agent mechanism) |
| "exploiting temporal structure in its own sensor stream" | **Q1**, **Q7**, **Q8** |
| "motion-induced consistency" | **Q1**, **Q2**, **Q3** |
| "test whether observations from a single sensor remain temporally self-consistent" | **Q9**, **Q12** |

**VERDICT: ✅ VERIFIED — no manuscript change needed.** Every clause is supported by an exact
quote or a proved absence.

---

# PART C — OUR INFERENCE (our words, NOT theirs)

- **C-1 — "motion-induced consistency"** is *our* compression of **Q1**+**Q2**+**Q3**. They never
  use the phrase "motion-induced". The compression is faithful (genuine motion produces
  cross-frame consistency; an injected object has none — **Q9**), but it is our wording.
  _Optional polish, Srinivasa's call:_ "motion-prediction consistency" names their mechanism
  more literally. Not required.
- **C-2 — the reference-signal argument.** Our reading: this check class keys on **the scene's own
  past**, whereas ours keys on **a neighbour's claim vs the verifier's own sensing**. Analytic
  contrast, not a claim about their text.

---

# PART D — VERIFIED BY ABSENCE

> Previously this was *asserted* (*"no inter-vehicle communication anywhere in the paper"*).
> It is now **proved with counts**, reproducible by anyone.

**D-1 — 3D-TC2 is strictly single-vehicle.** Term-frequency over the full extracted text:

| Term | Hits |
|---|---|
| `collaborative` | **0** |
| `cooperative` | **0** |
| `V2V` / `V2X` | **0** / **0** |
| `neighbor` / `neighbour` | **0** / **0** |
| `multi-agent` | **0** |
| `other vehicles` | **0** |
| `communicat` | **1** — and it is *"ACM SIGSAC Conference on Computer and **Communications** Security"*, a **venue name in reference [6]**, not inter-vehicle communication |

**Conclusion: zero cross-agent mechanism of any kind.** The "single vehicle" clause in our
`related.tex` is not merely defensible — it is airtight.

---

# ⭐ CORROBORATION — their own limitation supports our argument

This paper's §4.4 and §5 are unusually favourable to us, and they are the authors' own words:

- **Q10** — a **temporally consistent** adversarial object *"will fail to detect"*.
- **Q11** — continuous-frame injection is listed as **future work**, i.e. **they evaluated
  single-frame injection only**.
- **Q9** — the detection signal is explicitly *abrupt appearance*: a spoofed box *"does not have
  'history' from the previous frames"*.

Our camouflage phantom is broadcast **persistently from episode start**, so it is temporally
self-consistent — exactly the case their own paper says this check misses.

⚠ **Posture to keep:** `related.tex` draws the reference-signal distinction **without** claiming
3D-TC2 fails on our attack. That is the correct and fair posture — their paper concerns a
different threat on a different platform. Keep it as is; deploy **Q10/Q11** only if a reviewer
pushes.

---

## Second-order sweep — full 14-ref bibliography scanned 2026-07-17
**Zero new candidates.** Refs are: LiDAR spoofing attacks (Petit '15 relay, Shin '17
Illusion-and-Dazzle, Cao '19 CCS, Cao '21 moving-target, Sun USENIX '20 + CARLO/SVF),
single-vehicle ghost defenses (Hau Shadow-Catcher, Object-Removal-Attacks, MSF-ADV), Hau & Lupu
'19 (false-data injection in wireless *sensor* networks — message layer, out of family), AdVIT
(video temporal consistency), and detectors/datasets (PointPillars, SECOND, MotionNet,
nuScenes). All single-vehicle; **no collaborative-perception or multi-agent-trust member.**

## Bookkeeping
- `refs.bib` `tc2_2021`: title exact ✅, authors You/Hau/Demetriou ✅, MAISP '21 ✅ (a
  *published workshop paper* — **not** in the arXiv-preprint venue-recheck class),
  arXiv:2106.07833 ✅.
- No manuscript edits arise from this audit.

## Re-audit changelog (2026-07-28)
1. **M-1 misquote corrected** — "no 'history'" → the authors' actual *"does not have 'history'"*.
2. Restructured into **Parts A–D** so quotes, inference and absence claims cannot be confused.
   The old *"THEY WROTE, phrase by phrase"* heading covered all three.
3. Every search fragment **executed** before being written; three line-break traps documented.
4. Absence claim upgraded from assertion to **counted evidence**.
5. Numeric claims cross-checked against Tables 2–4 and the reference list.

_Standing rule: not closed until Srinivasa re-signs (`AUDIT_PENDING.md`). Committed ≠ audited._
