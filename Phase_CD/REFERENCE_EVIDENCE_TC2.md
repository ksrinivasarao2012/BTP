# 3D-TC2 — paired claim/evidence sheet

## STATUS: ☑☑ CLOSED — verification by **Claude**, reviewed & approved by **Srinivasa** 2026-07-29

**Srinivasa reviewed the M-2 correction and the rebuilt C-3 on 2026-07-29 and approved.**
Re-verified at closure — all three checks pass:

| Check | Result |
|---|---|
| `WE WRITE` block ↔ live `related.tex` | ✅ **exact match, character for character** |
| Citation sites (by key **and** by name) | ✅ `tc2_2021` **1×**, `3D-TC2` **1×**, same line 153 — the only use |
| Paragraph line range | ✅ lines **150–162** (re-derived; anchor on the `\cite` key, not the number) |

---

### (history) ☐ AWAITING SRINIVASA'S REVIEW — a second defect (M-2) was found 2026-07-28

> ⚠️ **Attribution, stated explicitly.** All verification in this file — the paper reading, the
> quote checking, the counts, the searches, the drafting — is **CLAUDE'S WORK**. Srinivasa's role
> is **review and approval**. A ☑ means *"Srinivasa reviewed Claude's work and approved it"*,
> never *"Srinivasa performed the check"*.

| Date | Work | Done by | Reviewed & approved by |
|---|---|---|---|
| 2026-07-26 | Original dossier | **Claude** | **Srinivasa** ✅ |
| 2026-07-28 (first pass) | Quote re-verification, M-1, absence measurement | **Claude** | **Srinivasa** ✅ — ruled his sign-off stands |
| 2026-07-28 (second pass) | Fact/interpretation split — **found M-2** | **Claude** | ☐ **PENDING** |

🚨 **This file is re-opened.** The first re-verification pass checked quotes and missed a
**scope error in the corroboration section (M-2)** — the same overclaim class as the SwarmRaft
C-3 draft. It surfaced only when the fact/interpretation split forced each claim to name the
paper text supporting it. **Srinivasa's earlier approvals remain valid for what they covered;
the corrected C-3 section has not yet been reviewed.**

Full 6-page re-read, every line including all four tables, under the verbatim-only standard
(Srinivasa: *"in the THEY WROTE place it should exactly match the paper writing; create a separate
place for your inference"*).

**Result of the re-audit:**
- ✅ **The manuscript sentence is accurate in every respect** — unchanged, and unaffected by M-2.
- ✅ **9 of 10 quotes are exact**; **M-1** (paraphrase inside quotes) corrected.
- ❌ 🚨 **M-2 — the corroboration section attributed to the authors a claim about a different
  attack class.** Their §4.4 limitation concerns **object *hiding*** (Object Removal Attacks,
  MSF-ADV); our attack is **fabrication**. Corrected in **C-3** below.
- ✅ **The absence claim is now proved with numbers** (it was previously asserted).
- ✅ All numeric claims verified against the tables.
- ⭐ **Two new quotes found on the line-by-line pass (Q13, Q14)** which support the same point
  **more safely than Q10 did**: **Q13** is the authors' own hypothesis that the detection signal is
  *"any abrupt introduction of objects into a frame"* — about **fabrication**, their actual target,
  so no scope-stretching is needed. C-3 is now built on Q13 instead of the hiding paragraph.
- 📊 **"single frame" occurs 7 times** in this 6-page paper — the single-frame scope is explicit
  and repeated, not an inference of ours.

**Lesson:** M-2 is *not* a quoting error — the quote itself (**Q10**) was reproduced correctly,
including the word *"hidden"*. The error was in **what we concluded from it**. Verbatim accuracy
does not protect against scope errors; only the fact/interpretation split caught this.

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
| **Q10** ⚠️**SCOPE** | "However, if the **hidden** object is temporally consistent (i.e. an adversarial object is placed on the road as the ego-vehicle approaches it), the approach will fail to detect such object." | p.5, §4.4 — **under the subsection heading "Object hiding attacks"**, following "*other classes of attacks such as Object Removal Attacks and MSF-ADV that aims to hide objects from detection*" | `will fail to detect` ⚠break |
| **Q13** ⭐ **NEW 2026-07-28** | "As such, **we hypothesize that any abrupt introduction of objects into a frame**, which is a characteristic of LiDAR-based front-near object spoofing attack, **can be detected as an anomaly**." | p.2, §3.2 | `abrupt introduction of objects` |
| **Q14** ⭐ **NEW 2026-07-28** | "We evaluate the effectiveness of CMCS in detecting **single frame** object spoofing attacks in Section 4.2." | p.4, §3.3 | `detecting single frame object spoofing` |
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

**WE WRITE (verbatim from our manuscript) — 🔄 REWORDED 2026-07-29 on Srinivasa's instruction:**
"A separate line detects LiDAR spoofing by exploiting temporal consistency across consecutive
frames from a \emph{single} ego vehicle's own LiDAR, e.g.\ motion-induced consistency in
3D-TC2~\cite{tc2_2021} and point-level temporal consistency in ADoPT~\cite{adopt2023}. These
methods evaluate temporal consistency across consecutive frames from one vehicle."

> ✎ **WHY IT CHANGED (Srinivasa, 2026-07-29): literal fidelity over elegance.** The old wording
> used two phrases the papers never use. Measured across both PDFs:
>
> | phrase | 3D-TC2 | ADoPT | verdict |
> |---|---|---|---|
> | `sensor stream` | **0** | **0** | ❌ our abstraction — removed |
> | `self-consistent` | **0** | **0** | ❌ our abstraction — removed |
> | `temporal consistency` | **18** | **21** | ✅ **their term** — now used |
> | `across consecutive` | 2 | 4 | ✅ shared — now used |
> | `ego-vehicle` / `ego vehicle` | 5 | 2 | ✅ theirs — now used |
> | `LiDAR observations` | **0** | **0** | ❌ *also ours* — rejected from the proposed rewrite |
>
> Srinivasa's proposed replacement used *"a vehicle's own LiDAR observations"*; the count shows
> that phrase is **also absent from both papers**, so it was swapped for **"consecutive frames"**,
> which both papers do use. Nothing about the claim changed — only whose vocabulary carries it.
>
> ⚠️ **Residual synthesis, disclosed:** `single vehicle` appears **0 times** in either paper. It is
> **our** contrast, not their self-description — but it is factually correct and proved
> independently in **Part D** (zero cross-agent terms in 3D-TC2). Likewise *"motion-induced"*
> remains ours (**C-1**). **No survey sentence can be zero-synthesis; the goal is that every noun
> and verb tracks the source.**

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

> 📏 Split into paper-fact vs interpretation per the standard set by Srinivasa 2026-07-28
> (`AUDIT_PENDING.md` § DOSSIER WRITING STANDARD).

## C-1 — the phrase "motion-induced consistency"

**C-1.1 — PAPER FACTS.** They write *"motion as a physical invariant of genuine objects"*
(**Q1**), *"objects (and their motion trajectory) should be consistent across consecutive 3D
LiDAR scenes"* (**Q2**), and claim to be *"the first to propose motion as a physical invariant
for 3D objects"* (**Q3**).

**C-1.2 — OUR TECHNICAL INTERPRETATION.** *"Motion-induced consistency"* is **our compression** of
those three. **The authors never use the phrase "motion-induced".** The compression is faithful —
genuine motion produces cross-frame consistency, and an injected object has no history (**Q9**) —
but the wording is ours. _Optional polish, Srinivasa's call:_ "motion-prediction consistency"
names their mechanism more literally. Not required.

## C-2 — the reference-signal argument

**C-2.1 — PAPER FACTS.** Their check compares the current frame's detections against a prediction
built by MotionNet from the ego sensor's own previous frames (**Q7**, **Q8**); the flag is raised
when an object lacks history in those frames (**Q9**).

**C-2.2 — OUR TECHNICAL INTERPRETATION.** We characterise this as keying on **the scene's own
past**, whereas our test keys on **a neighbour's claim versus the verifier's own sensing**.
**The authors do not frame their work in terms of a "reference signal", and make no comparison to
cross-agent verification.** This is our analytic contrast, not a claim about their text.

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

**D-1.1 — MEASURED FACT.** Zero occurrences of any cross-agent term. Positively, their threat
model is spoofing of **the ego vehicle's own** LiDAR returns (**Q5**), and MotionNet consumes a
sequence of frames from **that same sensor** (**Q7**, **Q8**).

**D-1.2 — OUR TECHNICAL INTERPRETATION.** We read this as establishing that 3D-TC2 has no
cross-agent mechanism, which is what our "single vehicle" clause asserts. **The authors do not
describe their work as "single-vehicle" in contrast to anything; the scope is simply what they
built.** The measurement is fact; calling it "airtight" support for our clause is our judgement.

---

# 🚨 C-3 — CORROBORATION, **CORRECTED 2026-07-28: the previous version overclaimed**

## ❌ M-2 — THE OVERCLAIM (found on re-audit, same class as SwarmRaft C-3)

The previous version of this section read:

> *"Our camouflage phantom is broadcast persistently from episode start, so it is temporally
> self-consistent — **exactly the case their own paper says this check misses.**"*

**That is wrong.** The §4.4 sentence it leans on (**Q10**) appears under the subsection heading
**"Object hiding attacks"**, and its full context is:

> *"3D-TC2 was designed to detect spoofed objects that are elicited with LiDAR spoofing attacks.
> Recently, there have been other classes of attacks such as **Object Removal Attacks** and
> **MSF-ADV** that aims to **hide objects** from detection… However, if the **hidden** object is
> temporally consistent…, the approach will fail to detect such object."*

**Their statement is about HIDING a real object. Our attack FABRICATES a phantom.** Different
attack class. The authors say nothing about persistent fabrications, and attributing that claim
to them would be the CATS error again — asserting a rival fails at something they never addressed.

## C-3.1 — PAPER FACTS (what the authors actually state)

⭐ **The best evidence is Q13, found on the 2026-07-28 line-by-line re-read** — it concerns their
*fabrication* detection directly, so it needs none of the scope-stretching that broke M-2.

1. ⭐ **Q13** (§3.2) — their stated detection hypothesis: *"we hypothesize that **any abrupt
   introduction of objects into a frame**, which is a characteristic of LiDAR-based front-near
   object spoofing attack, can be detected as an anomaly."* **The signal is abruptness.**
2. **Q9** (§3.3) — the mechanism, explicitly scoped: *"**Under a single frame** LiDAR spoofing
   attack, when an object is successfully injected, it does not have "history" from the previous
   frames…"*
3. **Q14** (§3.3) — *"We evaluate the effectiveness of CMCS in detecting **single frame** object
   spoofing attacks in Section 4.2."*
4. **Q11** (§5, future work) — *"We also intend to consider a stronger adversary that is able to
   perform injection into **continuous frames** (temporal attacks)…"* → **continuous-frame
   injection is work they have not done.**
5. **Q10** (§4.4) — a temporally consistent **hidden** object will not be detected. ⚠️ **Scope:
   object *hiding* attacks (Object Removal / MSF-ADV), NOT fabrication.** This is the quote that
   caused M-2.

> **The scoping is not incidental.** The phrase **"single frame"** appears **7 times** in this
> 6-page paper. The authors are consistent and explicit that single-frame injection is what they
> address.

## C-3.2 — OUR TECHNICAL INTERPRETATION

By the authors' own hypothesis (**Q13**), the anomaly signal is the **abrupt introduction** of an
object. Our camouflage phantom is broadcast persistently from episode start, so it would not
present that abruptness. **The authors do not evaluate persistent fabrication and make no claim
about how 3D-TC2 would behave against it** — **Q11** lists continuous-frame injection as work they
have not yet done. This is our reasoning from their stated hypothesis, **not a result they report,
and not something we have tested against their system.**

**Two levels of safety, use the lower one first:**

| Strength | Claim | Needs |
|---|---|---|
| ✅ **Safest** | *"The authors state that continuous-frame (temporal) injection is future work; their evaluation covers single-frame injection."* | **Q11**/**Q14** verbatim — **no inference** |
| ⚠️ Stronger | *"Their stated signal is abrupt introduction (Q13), so a persistent fabrication would not present it."* | our inference from **Q13** — label it as such |

**Never** the third level — *"therefore 3D-TC2 fails on our attack"*. We have not run it.

## 🚫 SENTENCES THAT MUST NOT BE WRITTEN

| ❌ Do not write | Why |
|---|---|
| *"their own paper says this check misses our attack"* | **Q10 is about object *hiding*, not fabrication** |
| *"3D-TC2 fails against persistent fabrications"* | never evaluated by them; we have not tested it either |
| *"exactly the case their paper concedes"* | conflates two different attack classes |

✅ **Say instead:** *"The authors state that continuous-frame (temporal) injection attacks are
future work, i.e. their evaluation covers single-frame injection."* — that is **Q11** verbatim in
substance, and it needs no interpretation.

## ⚠ Posture to keep
`related.tex` draws the reference-signal distinction **without** claiming 3D-TC2 fails on our
attack. That remains the correct posture — different threat, different platform. **No manuscript
change.** Deploy **Q11** only if a reviewer pushes, and **never Q10 in that role.**

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
