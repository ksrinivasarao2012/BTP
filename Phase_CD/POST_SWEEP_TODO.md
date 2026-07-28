# POST-SWEEP TODO — everything owed after the forward-citation sweep finishes
_Created 2026-07-28. Companion to `FORWARD_CITATION_SWEEP.md` (the sweep itself) and
`AUDIT_PENDING.md` (Srinivasa's sign-off gate)._

**Purpose.** The forward sweep keeps producing work that cannot be done *during* the sweep — verbatim
verifications, dossiers, wording fixes. This file is the queue. Srinivasa's instruction 2026-07-28:
finish the forward sweep of every anchor **first**, then work this list.

**Ordering rule:** ⓪ finish the sweep → ① verify everything we QUOTE → ② fix the wording → ③ build the
missing dossiers → ④ Srinivasa's audit → ⑤ manuscript mechanics.

---

## ⓪ FINISH THE FORWARD SWEEP FIRST (blocking everything below)

| # | Anchor | Status |
|---|---|---|
| 1–9 | CAD · ROBOSAC · TruPercept · Coopernaut · ADoPT · 3D-TC2 · CP-Guard · MADE · GCP | ✅ done |
| 10 | **ROBOSAC gap** — true count is **56**, not 45; **7 new papers** found at offset 45–55 still unread | ❌ **do first, it is a known hole** |
| 11–20 | PRBI · MATE · AerialTrust · TrustFlip · Stealthy-Fab · CoDynTrust · Tu et al. · Vadivelu · SwarmRaft · Conformity | ❌ not started |

⚠️ **Use the verified pagination method** (`limit=10`, titles-only, plus a boundary probe at a high offset).
The old single-`limit=100` call silently truncated — that is how Coopernaut appeared to have 43 citers when it
actually has **189**.

---

## ① VERBATIM VERIFICATION — every paper we QUOTE

**Why this section exists.** On 2026-07-28 the CATS differentiator turned out to be **wrong** once its real text
was read. It had been built on a summarised abstract. Any sentence in our manuscript that quotes or paraphrases
another paper is checkable by a reviewer, so each one must be verified against **raw text**.

**The verification method that works** (no summarising model in the loop):
```bash
# abstracts, verbatim, many at once:
curl -sL "http://export.arxiv.org/api/query?id_list=<id1>,<id2>,..." -o abs.xml
# full text / conclusions:
curl -sL "https://arxiv.org/pdf/<id>" -o p.pdf     # then pypdf + regex the Conclusion
```
…then **`Read` the file**. `Read` returns raw bytes. `WebFetch` truncates quotes to ~125 chars and `WebSearch`
paraphrases — neither can certify wording.

### 1a. ✅ Already verified verbatim (7)
LiDAR-Spoofing-Safe-Control · SafeCoop · CONClave · CATS · MVIG · AFFormer · Towards-V2X-Survey
→ quote bank recorded in `FORWARD_CITATION_SWEEP.md` Part 0c.

### 1b. ❌ OWED — papers we quote but have NOT verified

| # | Paper | Why it's owed | How to get it |
|---|---|---|---|
| 1 | 🚨 **RLCVP** (IEEE TMC 11006384) | **Level-1 must-cite.** Differentiator rests on abstract only. Exactly the CATS failure mode | ❌ Not on arXiv → **`INSTITUTE_WIFI_TODO.md` PRIORITY 0** |
| 2 | ⚠️ **CATS — BODY** (arXiv 2503.00659) | Abstract verified; but *"phantom red-light violator"* and the *"majority view"* mechanism are **body claims** read through a summariser. Must confirm from raw text before either is written | ✅ PDF already downloaded — extract and re-read |
| 3 | **CP-Guard** (2412.12000) | Planned cite, **no dossier yet**. Conclusion read once via WebFetch (summarised) | ✅ arXiv — curl→Read |
| 4 | **GCP body** (2501.02450) | The K=5 / per-neighbour-cache / LSTM-AE findings — our single most important differentiator — came through a **summarising fetch**, not raw text | ✅ arXiv — curl→Read. **High priority: claim-rewording #4 depends on it** |
| 5 | **The 17 dossiers** | Built by pypdf over real PDFs, so on **solid ground** — but never re-checked since, and the CATS lesson (abstract vs body nuance) may apply to any of them | ⚠️ Spot-check the load-bearing quote in each during Srinivasa's audit |

### 1c. ⚠️ EXPECT MORE — the sweep is not finished
Ten anchors remain (§⓪). Each may surface a **new Level-1 paper**, and every new Level-1 paper lands here
needing verbatim verification. **This list will grow. Do not treat it as final until the sweep is closed.**

---

## ② WORDING FIXES OWED IN THE MANUSCRIPT

All five are in `AUDIT_PENDING.md` §D with full evidence. None is applied yet.

| # | Fix | Trigger |
|---|---|---|
| 1 | Drop "first to evaluate a CP defense by navigation/driving success" | SafeCoop (69.15% CARLA driving score); LiDAR-Spoofing (guaranteed-avoidance control law) |
| 2 | Drop "first cross-agent temporal trust" | CONClave, CATS, MVIG all accumulate over time |
| 3 | Drop "first adaptive/defense-aware attacker" | MVIG, Stealthy-Fab, Hyper3Def |
| 4 | 🚨 **Delete the temporal-priority claim entirely** | **GCP** already does per-neighbour temporal with K=5 cached frames |
| 5 | 🚨 **Never write "CATS requires an honest majority"** | Retracted 2026-07-28. Use instead: *"Sensor-based attacks … are considered out of scope"*, its trusted-Security-Authority assumption, and its **4.2× rate of blocking good messages** |

**Positive additions owed too:**
- ⭐ Cite the V2X survey's **σ = 0.6 m** result (*"AP@0.5 drops 70.5% when position error std is 0.6m"*) in the
  **setup / parameter-justification** section — independent validation of our noise level.
- ⭐ Use the **two-disjoint-literatures** framing (uncertainty-aware CP never meets an adversary; adversarial CP
  never meets honest noise) instead of any bare "first to X" claim. Backed by ~24 papers read at full-abstract
  depth plus the survey's own section structure.
- Add **PhyScout** and **AFFormer** as deliberate **boundary contrasts** (single-vehicle spatio-temporal;
  cross-agent temporal for *channel* noise) to pre-empt "isn't this just X?".

---

## ③ DOSSIERS OWED
- [ ] **CP-Guard** → `REFERENCE_EVIDENCE_CP_GUARD.md` + `related.tex` sentence + `cpguard2025` in `refs.bib`
- [ ] Decide whether the 6 Level-1 forward-sweep papers each need a dossier, or whether the verified quote bank
      in Part 0c is sufficient backing for their paragraphs.

---

## ④ SRINIVASA'S AUDIT QUEUE (nothing is closed without this)
- [ ] 13 of 17 prior-art dossiers still unaudited (TrustFlip, 3D-TC2, ADoPT, SwarmRaft done)
- [ ] The ~49 security-relevant rows from the second-order sweep
- [ ] All 5 wording fixes above, before they go into the manuscript
- [ ] The forward sweep's Level-1/2/3 categorisation
- [ ] Google Scholar "Cited by → Since 2025" pass (Scholar blocks the fetcher — only Srinivasa can run it)

---

## ⑤ MANUSCRIPT MECHANICS (untouched, and the real submission risk)
- [ ] **Zero figures built** — `FIGURES_PLAN.md` exists, nothing drawn
- [ ] **LaTeX never compiled end-to-end**
- [ ] `refs.bib` TODO-VERIFY notes (Coopernaut pages, Stealthy-Fab venue)
- [ ] RAS submission mechanics

> Honest note: the prior-art work is ~95% done and has found **zero pre-emptions**. Items ⑤ are now the larger
> risk to actually submitting.

---

_Standing rule: nothing here is "done" until Srinivasa personally audits it (`AUDIT_PENDING.md`)._
