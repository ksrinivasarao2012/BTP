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
| **1** | Dossier auditing | **3 of 18 closed** (TruPercept awaiting review) | 2–3 sessions |
| **2** | Must-cites wired into the paper | **1 of 7** | ~1 day |
| **3** | Hygiene (PDF integrity, venues, missing blocks) | mostly not started | ~2 hours |
| **4** | 🔴 **LaTeX compile** | **NEVER DONE** | ~30 min |
| **5** | 🔴 **Figures** | **ZERO drawn** | days |
| **6** | 🆕 **Density/parameter repair in `setup.tex`** | **open — a stated justification is wrong** | ~half day |
| **7** | 🆕 Reproduction check against the frozen tag | **owed** | ~1–2 h |
| ~~8~~ | ~~Artifact freeze (tag, untrack `.pyc`, ship all scripts)~~ | ✅ **DONE 2026-08-09** — tag `camera-ready-v1` → `8878ea30`, pushed | — |

> ⚠️ **The honest ranking.** Items 1–3 are *supporting material*. **Items 4–5 are the paper.**
> A perfectly audited citation set does not help if the document has never built and has no
> figures. Prior art is ~460 papers deep with **zero pre-emptions**; the manuscript has never
> been compiled once.
>
> 🆕 **Item 6 outranks 1–3.** It is the only open item where the paper currently states something
> we know to be **unsupported** — every other item is work not yet done, which is a different and
> lesser problem than a claim that is wrong on the page.

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

`PRBI` · `CAD` · `GCP` · `MATE` (3 uses) · `AerialTrust` (5 uses across 3 files)

**`TruPercept` — MOVED OUT of this group 2026-08-09.** Claude's full re-audit is **done**;
⬜ **awaiting Srinivasa's review**. Largest surface of any paper we cite: **8 citation sites across
4 files**, all documented. 13 load-bearing quotes verified (3 apparent failures were fi-ligature
artifacts). Two things need your eye: (i) a **new candidate finding**, logged but deliberately
**not cited** — their §VI.C *"weakness in the model towards coordinated attacks"*, which comes with
three banned sentences because their trust model **did** catch the malicious agents (0.13 vs 0.27);
misusing it would repeat M-2 exactly; (ii) a **self-correction logged in place** — an absence claim
was written before its search was run, and the search then returned a second hit (finding A-6).
Also found: **USE 5 had drifted** because a MATE clause was inserted mid-sentence in `related.tex`
— which means the MATE and AerialTrust dossiers now owe a cross-check on wording they never wrote.

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
- [ ] 🚨 **27 third-party PDFs are tracked in `Phase_CD/Research paper/` on a PUBLIC repo**
      (`github.com/ksrinivasarao2012/BTP`) — confirmed by `git ls-files` 2026-08-09, and now
      inside the pushed `camera-ready-v1` tag. This is redistribution of copyrighted papers.
      Removing them from the working tree is trivial; purging them from **history** is not, and
      gets harder with every commit. **Decide before submission.**
      (The publisher's own RAS author guide and `temp.png` are now gitignored and were never committed.)

---

# 6. 🆕 DENSITY / PARAMETER REPAIR — a stated justification is wrong

Found 2026-08-09. **Nothing here changes any experimental RESULT** — it is entirely about how
parameters are described and justified.

**The defect.** `setup.tex` says *"96.8% of sampled maps are solvable"*, and
`PAPER_MASTER_PLAN §8.1` justifies density 0.27 as the *"calibrated fairness ceiling"*. Both trace
to `FINAL_PARAMETER.md`, whose sweep (`PhaseB2/density_sweep_v14_specific.py:113-121`) uses a
generator that **rejects overlapping obstacles**. Our env has **no overlap test at all**. At the
same nominal 0.27 the two produce different worlds:

| | sweep @ 0.27 | our env @ 0.27 |
|---|---|---|
| obstacles/map | 68.9 | 28.0 |
| true coverage | 0.2725 | **0.237** |
| overlap | forbidden | unconstrained |

`FINAL_PARAMETER.md §2` claims the sweep reproduces the env *"exactly"* — true for spawn and BFS
parameters, **false for obstacle generation**.

**Measured replacement** (`Noise_added/calibrate_density_realenv.py`, probe): our maps are
**100% solvable at every density 0.20–0.30**, so **0.27 is nowhere near a feasibility ceiling for
our generator** and the stated reason for choosing it does not hold. The honest replacement is
**train/eval density match** — stage 2 was trained at 0.27 (`train_noise_robust.py:52`).

**Owed:**
- [ ] Full run: `calibrate_density_realenv.py 2000 10` (~1 h) or `10000 10` (~5 h)
- [ ] Rewrite the `setup.tex` solvability sentence; state true vs nominal coverage
- [ ] Rejustify 0.27 in `setup.tex` **and** `PAPER_MASTER_PLAN §8.1`
- [ ] Add the consolidated parameter table — goal tolerance (1.0 m), goal keep-out (2.0 m), BFS
      clearance (0.20 m), and the fact that there is **no minimum obstacle gap**, all currently
      absent from the manuscript
- [ ] Fix `methods.tex:12` "48-ray" → 192 rays encoded to 48 dimensions
- [ ] Rebind root `PARAMETER_JUSTIFICATION.md`'s citations, which justify 12 m LiDAR / 8 m comm
      while the paper runs **8 m / 10 m**
- [ ] Resolve `setup.tex` obstacle-count range 13–56 vs `§2.2`'s 15–56
- [ ] Update stale `PARAMETER_JUSTIFICATION_PHASE_CD §2.5` (calls the 0.27 lock-in "optional"; done)

Full list: `PROJECT_READING_GUIDE.md` → *"Known documentation defects"*.

---

# 7. 🆕 REPRODUCTION CHECK — owed against the frozen tag

`camera-ready-v1` states that the eval-code changes carried into it are behaviour-preserving.
That was established by **code inspection** (the `comm_loss > 0.0` guard short-circuits before the
RNG is drawn, so the random stream is untouched), **not by re-running**. That claim is now public.
- [ ] Re-run one camera-ready cell (σ=0.6 camouflage, f=2) and match the published number.
      Converts the tag's claim from *"should reproduce"* to *"does reproduce"*.

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
| Dossiers closed (Srinivasa-approved) | **3 / 18** | 2026-08-09 |
| Dossiers with Claude's audit done, awaiting review | **1** (TruPercept) | 2026-08-09 |
| Must-cites in the paper | **1 / 7** | 2026-07-29 |
| Papers eventually needing a dossier | **25** | 2026-07-29 |
| LaTeX compiled | **never** | 2026-08-09 |
| Figures drawn | **0** | 2026-08-09 |
| Prior-art pre-emptions found | **0** ✅ | 2026-07-28 |
| Code artifact frozen + pushed | ✅ **`camera-ready-v1` → `8878ea30`** | 2026-08-09 |
| Manuscript claims known to be **unsupported** | **1** (density 0.27 justification) | 2026-08-09 |
| Third-party PDFs published on the public repo | **27** ⚠️ | 2026-08-09 |
