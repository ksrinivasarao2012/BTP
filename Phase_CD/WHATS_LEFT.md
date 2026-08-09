# WHAT'S LEFT — single status page for the RAS submission

_Created 2026-07-29. **This file is the answer to "what's remaining?"** — read it first.
Companions: `PAPER_TODO.md` (submission checklist) · `AUDIT_PENDING.md` (review gate) ·
`FORWARD_CITATION_SWEEP.md` (prior-art sweep) · `POST_SWEEP_TODO.md` (post-sweep queue)._

> 📌 **Counts live HERE and nowhere else.** Other files describe *what* was found, never *how
> many*. This rule exists because six files once disagreed about the same number
> (see `FORWARD_CITATION_SWEEP.md` Part 7).

---

## THE ONE-SCREEN ANSWER

| # | Work | Status | Effort |
|---|---|---|---|
| **1** | Dossier auditing | **3 of 18 closed** | 2–3 sessions |
| **2** | Must-cites wired into the paper | **1 of 7** | ~1 day |
| **3** | Hygiene (PDF integrity, venues, missing blocks) | mostly not started | ~2 hours |
| **4** | 🔴 **LaTeX compile** | **NEVER DONE** | ~30 min |
| **5** | 🔴 **Figures** | **ZERO drawn** | days |

> ⚠️ **The honest ranking.** Items 1–3 are *supporting material*. **Items 4–5 are the paper.**
> A perfectly audited citation set does not help if the document has never built and has no
> figures. Prior art is ~460 papers deep with **zero pre-emptions**; the manuscript has never
> been compiled once.

---

# 1. DOSSIER AUDITING — 15 of 18 remaining

**Rule:** verification is **Claude's work**; **Srinivasa reviews and approves**. A ☑ means
*"Srinivasa reviewed Claude's work and approved"*, never *"Srinivasa did the check"*.

### ✅ CLOSED (3)
| Paper | Ticks | Notes |
|---|---|---|
| **SwarmRaft** | ☑☑ | first closed under the full standard — **use as the template** |
| **3D-TC2** | ☑☑ | **M-2 scope error** found and corrected |
| **ADoPT** | ☑☑☑ | scope check **passed**; 2 wording corrections applied |

### 🟡 GROUP 1 — nearly done (2)
| Paper | What's needed |
|---|---|
| **TrustFlip** | Approved 2026-07-26, then rewritten. Needs fact/interpretation split on C-1/C-2/C-3 + **scope check on C-3** (it leans on their *"sensitivity-attribution dilemma"* — same structure that failed for 3D-TC2 and passed for ADoPT). ✅ 10/10 quotes exact. ⚠️ ref count was wrong (58→41); PDF was truncated, now restored |
| **LiDAR-Spoofing** | Written 2026-07-28, **never reviewed**. 🚨 **Open decision: C-5** — we assert a *priority claim on the authors' behalf* (*"the first work to…"*). **Recommend softening.** Also: its **forward-citation tree has never been swept** (Feb 2023, 3.5 years of citers, closest paper to this project) |

### 🟠 GROUP 2 — resynced 2026-07-28, content never audited (6)
Their `WE WRITE` blocks had drifted from `related.tex`; the **quotes are fixed but the content
was never reviewed**.

`PRBI` · `CAD` · `GCP` · **`TruPercept`** (⚠ largest surface: **7 uses across 4 files**) ·
`MATE` (3 uses) · `AerialTrust` (5 uses across 3 files)

### 🔴 GROUP 3 — never audited at all (7)
`CoDynTrust` · `MADE` · `ROBOSAC` · `Conformity` · `Coopernaut` · **`Vadivelu`** · `Stealthy-Fab`

🚨 **Vadivelu carries a known defect.** Its dossier holds a *"Recommended edit"*, not verified
applied text. The edit was applied to `discussion.tex` **and changed on the way in** — a
concluding clause was added that no dossier ever checked, and it uses a **benign-CP** result to
conclude an **adversarial-setting** concern is *"not an unaddressed vulnerability"*. That is a
scope step of the same shape as M-2.

**Suggested order:** TrustFlip → LiDAR-Spoofing → **Vadivelu** (known defect) →
**TruPercept** (biggest surface) → the rest.

---

# 2. MUST-CITES — 6 of 7 not yet in the paper

The forward sweep's actual deliverable, **86% undelivered**.

| Paper | bib | related.tex | dossier | PDF |
|---|---|---|---|---|
| **LiDAR-Spoofing-Safe-Control** | ✅ | ✅ 2 uses | ✅ | ✅ |
| **CONClave** | ❌ | ❌ | ❌ | ✅ |
| **CATS** | ❌ | ❌ | ❌ | ✅ ⚠ body unverified |
| **SafeCoop** | ❌ | ❌ | ❌ | ✅ |
| **MVIG** | ❌ | ❌ | ❌ | ✅ |
| **GLST** | ❌ | ❌ | ❌ | ✅ |
| **RLCVP** | ❌ | ❌ | ❌ | ❌ IEEE-walled → campus wifi |
| **CP-Guard** *(pre-sweep gap)* | ❌ | ❌ | ❌ | ❌ **free on arXiv 2412.12000** |

**Why this matters:** `related.tex` says *"to our knowledge no prior work…"* while the six
closest papers go uncited. A reviewer from that community notices immediately.

➡️ Each will also need a dossier → **the audit queue grows from 18 to 25.**

---

# 3. HYGIENE

- [ ] 🚨 **Integrity-check the other 26 PDFs.** TrustFlip's was silently truncated to 512 KB
      (95% missing) and still looked readable. Check for a missing `%%EOF` trailer.
- [ ] 4 dossiers have **no `WE WRITE` blocks** — Coopernaut, ROBOSAC, Stealthy-Fab, Vadivelu
      (they predate the paired-sheet format, so dossier↔`.tex` cannot be machine-checked).
- [ ] **Venue confirmations** before submission: ADoPT (BMVC 2023 — arXiv PDF has no stamp) ·
      SwarmRaft (IoT-J template, `VOL. NN` unfilled) · TrustFlip (v1, no venue stated).
- [ ] `refs.bib` TODO-VERIFY notes (Coopernaut pages, Stealthy-Fab venue).
- [ ] 62 MB of PDFs are tracked in git on a **public** repo — check none are publisher PDFs.

---

# 4. 🔴 LATEX — NEVER COMPILED

**No `.pdf`, no `.aux`, no `.bbl` has ever existed. There is no LaTeX toolchain on this machine.**

```powershell
winget install MiKTeX.MiKTeX
```

Until this runs, we do not know whether the manuscript builds at all — a missing `\ref`, a broken
environment or a bib error would surface at submission time. **~30 minutes to find out.**

---

# 5. 🔴 FIGURES — ZERO DRAWN

`FIGURES_PLAN.md` specifies every figure (message, data source, plot type, priority, Elsevier
production rules). **Nothing has been drawn.** No `\includegraphics` anywhere; no `figures/`
directory. This is the long pole and it has not started.

---

## Also outstanding
- `temp.png` — a Task Manager screenshot; **left untracked by Srinivasa's decision** (not a figure).
- Task #3 in the task list: triage the defense cluster **CP-Guard, CP-Guard+, LUCIA**.
- `POST_SWEEP_TODO.md` ② — 4 claim rewordings + 3 additions, **none applied** to the manuscript.

---

## Scoreboard — update this block, nowhere else

| Metric | Value | As of |
|---|---|---|
| Dossiers closed | **3 / 18** | 2026-07-29 |
| Must-cites in the paper | **1 / 7** | 2026-07-29 |
| Papers eventually needing a dossier | **25** | 2026-07-29 |
| LaTeX compiled | **never** | 2026-07-29 |
| Figures drawn | **0** | 2026-07-29 |
| Prior-art pre-emptions found | **0** ✅ | 2026-07-28 |
