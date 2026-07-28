# TrustFlip — paired claim/evidence sheet

## STATUS: ☑ AUDITED & APPROVED (Srinivasa, 2026-07-26) — re-verified 2026-07-28
Full 16-page re-read 2026-07-28 under the verbatim-only standard, **on a freshly downloaded PDF
after discovering the copy on disk was corrupt** (see below).

**Result of the re-audit:**
- ✅ **ALL 10 quotes VERIFIED EXACTLY — zero misquotes.** The only one of the four re-audited
  dossiers with a perfect quote record.
- ✅ All three second-order candidates confirmed present in the bibliography (**[9]** LUCIA,
  **[12]** Pretend Benign, **[13]** Stealthy-Fab)
- ✅ *"Q. Zhang = CAD's first author"* confirmed — Qingzhao Zhang is TrustFlip's **last** author
  and CAD's (**[8]**) **first** author
- ❌ **M-1: the bibliography count is wrong — 41 references, not 58.** Corrected below.
- 🚨 **The PDF on disk was truncated to 512 KB (95% of the file missing).** Restored.
- ⭐ **NEW:** their *"sensitivity-attribution dilemma"* is a direct analogue of our precision
  caveat — see C-3.

**The paper:** Yutong Liu, Chenyi Wang, Ming F. Li, Qingzhao Zhang (ECE Department, The
University of Arizona, Tucson, AZ), *"Adversarial Trust Poisoning in Vehicular Collaborative
Perception"*, arXiv:2605.22122v1 [cs.CR], 21 May 2026. 16 pages.
⚠ **The paper's TITLE is "Adversarial Trust Poisoning…"** — *TrustFlip* is the **attack's** name
inside the paper; *TrustReflect* is their mitigation. `refs.bib` `trustflip2026` carries the
correct full title. PDF: `Phase_CD/Research paper/TrustFlip.pdf` (11.4 MB, intact).

---

## 🚨 FILE-INTEGRITY INCIDENT (found 2026-07-28)

| | |
|---|---|
| **Symptom** | `pypdf` refused the file: *"EOF marker not found — Stream has ended unexpectedly"* |
| **Diagnosis** | On-disk size was **524,288 bytes = exactly 512 KB (0x80000)**, with **no `%%EOF` marker**. A download cut off mid-transfer at a round buffer boundary |
| **True size** | **11,406,064 bytes** — the stored copy was missing **95%** of the file |
| **Why it went unnoticed** | The text lives early in the file; the 11 MB is mostly point-cloud figures. A tolerant reader (MuPDF, used on 2026-07-17) could still extract the text, which is why the original dossier's *"16 pages… text intact"* note was written in good faith |
| **Action** | Re-downloaded from `arxiv.org/pdf/2605.22122`, verified `%PDF-1.7` header + `%%EOF` trailer + **16 pages**, replaced the corrupt file |
| **Lesson** | ⚠️ **The other 26 PDFs in `Research paper/` have not been integrity-checked.** A quick pass for missing `%%EOF` markers is owed — see Open Items |

---

## ❌ M-1 — THE BIBLIOGRAPHY COUNT IS WRONG

| | |
|---|---|
| **Dossier said** | *"Second-order sweep — **FULL 58-ref** bibliography title scan"*, and *"Rest of the **58**: …"* |
| **Actual count** | **41 references**, numbered `[1]`–`[41]`. Verified three ways: highest number cited = 41; distinct numbers = 41; numbers inside the REFERENCES section = 41 |
| **Same version?** | Yes — both the dossier and this re-audit use **arXiv:2605.22122v1**. Not a version difference |
| **Impact** | The **sweep itself is unaffected** — scanning 41 of 41 is complete, and all three candidates it reported are genuinely present. But a stated count that does not match its source is exactly the defect class we are eliminating |
| **Status** | Corrected to **41** throughout |

---

# 🔍 HOW TO AUDIT THIS (~10 min)

### ⚠️ TRAP — case sensitivity (new to this paper)
IEEE reference style uses **sentence case** in titles. Searching the title as commonly written
returns nothing:

| ❌ Search | ✅ Actually printed |
|---|---|
| `Pretend Benign` | "**Pretend benign**: A stealthy adversarial attack…" `[12]` |
| `Among Us` | "**Among us**: Adversarially robust collaborative perception…" `[14]` |
| `Stealthy Data Fabrication` | "From **stealthy data fabrication** to unsafe driving…" `[13]` |

All three of these produced **false alarms** during this re-audit before the reference list was
read directly. Search case-insensitively, or read the list.

---

# PART A — THEY WROTE (verbatim only)

> Every quote below was verified against the freshly downloaded PDF. **10 of 10 exact.**

| ID | Their exact words | Page / § | ✅ TESTED fragment |
|---|---|---|---|
| **Q1** | "We present TrustFlip, a novel attack that weaponizes consistency-based defenses to poison the trust assigned to benign vehicles. Instead of injecting false data into the collaboration pipeline, it deploys physical adversarial objects that are genuine but induce inconsistent observations among benign vehicles. The resulting inconsistencies are misattributed by the defense to the targeted vehicle, causing its trust score to degrade and eventually leading to its downweighting or exclusion from collaboration." | p.1, Abstract | `weaponizes consistency-based defenses` |
| **Q2** | "the attack removes the targeted benign vehicle from collaboration in up to 87.7% of scenarios and drops Average Precision (AP) by up to 13%" | p.1, Abstract | `up to 87.7% of scenarios` |
| **Q3** | "…TrustReflect, a lightweight self-reflection mechanism that marks disputed regions as uncertain and excludes them from trust evaluation, reducing the attack success rate by 35-100%." | p.1, Abstract | `reducing the attack success rate by 35-100%` |
| **Q4** | "The key insight is that these defenses cannot distinguish whether a cross-view inconsistency originates from a malicious vehicle or from an externally induced physical effect." | p.1, §I | `cannot distinguish whether a cross-view inconsistency` |
| **Q5** | "…any attacker capable of intentionally creating inconsistent observations among benign vehicles can weaponize the defense itself to suppress benign contributors." | p.1, §I | `weaponize the defense itself to suppress benign contributors` |
| **Q6** | "existing systems employ cross-vehicle inconsistency detection and trust estimation, **penalizing vehicles whose observations conflict with the majority**." | p.1, Abstract | `conflict with the majority` |
| **Q7** ⭐ | "They also expose a **sensitivity-attribution dilemma**: defenses that smooth over localized physical discrepancies are less affected by TrustFlip but may miss real single-object inconsistencies, while defenses sensitive enough to flag such discrepancies become exploitable unless they attribute the source correctly." | p.2, §I | `sensitivity-attribution dilemma` |
| **Q8** | "Importantly, the attacker does not compromise the victim, inject digital data, or interfere with V2V communication." | p.4, §III.B | `does not compromise the victim` |
| **Q9** | "TrustReflect does not by itself separate benign from malicious scenarios or objects, so the mitigation addresses the symptom rather than the cause. Certified separation between adversarial trust poisoning and benign cross-view inconsistencies remains an open problem." | p.14, §VI | `addresses the symptom rather than the cause` |
| **Q10** | title: "**Adversarial Trust Poisoning** in Vehicular Collaborative Perception" | p.1 | `Adversarial Trust Poisoning in Vehicular` |

### Their setup — verified

| Claim | Source | ✓ |
|---|---|---|
| Benchmark **OPV2V**; 4 defenses (**CAD, MATE, LUCIA, MADE**); 4 backbones (PIXOR, PointPillars, AttFusion, Where2Comm) | §I, §V.A | ✅ |
| Three shape priors: **FROMREAL, ATTACHED, HOLLOW** | §I, §IV | ✅ |
| Real-world LiDAR captures of fabricated prototypes | §V.E | ✅ |
| Early fusion **excluded** from the system model (bandwidth) | §III.A | ✅ |
| Attacker knowledge: offline **white-box** + runtime environmental | §III.B | ✅ |
| Bibliography = **41 refs** (`[1]`–`[41]`) — **NOT 58** | ref list | ✅ corrected |

---

# PART B — OUR `.tex` TEXT → WHICH QUOTE BACKS IT

## USE 1 — the ONLY use, **verified 2026-07-28** — `related.tex` lines **142–148** (`\cite{trustflip2026}` at line 143)

> ✅ **"Only use" is now PROVEN, not assumed.** Searched `sections/*.tex`, `main.tex`,
> `highlights.tex`: the key `trustflip2026` occurs **once**; the name `TrustFlip` occurs
> **once** (line 142, the same sentence); **`TrustReflect` occurs zero times** — we never
> mention their mitigation. No orphan discussion.
>
> ⚠️ **Line numbers drift** — was `~109–115` until a paragraph was inserted above on 2026-07-28.
> Anchor on the `\cite` key: `grep -n "trustflip2026" sections/*.tex`

**WE WRITE (verbatim from our manuscript):** "Complementing the defense literature, the TrustFlip
attack~\cite{trustflip2026} shows that consistency-based trust can itself be weaponized:
physically induced disagreements cause defenses to downweight or exclude \emph{honest} vehicles.
Our evaluation addresses the same failure class by measuring \emph{no-harm} --- the success cost
of running the defense in attack-free swarms --- directly, and finding it statistically
indistinguishable from zero even under an adaptive attacker."

| Our clause | Backed by |
|---|---|
| "consistency-based trust can itself be **weaponized**" | **Q1**, **Q5** — *"weaponize"* is **their own verb** |
| "physically induced disagreements" | **Q1** (*"deploys physical adversarial objects… induce inconsistent observations"*) |
| "cause defenses to **downweight or exclude** honest vehicles" | **Q1** — near-verbatim (*"downweighting or exclusion from collaboration"*) |
| "addresses **the same** failure class" | **C-1** (ours — see the nuance below) |

**Wording history, both retained:**
- ✎ **Srinivasa 2026-07-19:** *"addresses **exactly this** failure class"* → *"**the same** failure
  class"*. We measure the same downstream failure (erroneous exclusion of honest agents), not
  TrustFlip's *attack mechanism*. Correct and still correct.
- ✎ **Srinivasa 2026-07-26:** *"cause defenses to **expel** honest vehicles"* → *"**downweight or
  exclude**"*. Their abstract frames harm as a spectrum (**Q1**); "expel" captured only the
  severe endpoint. The current wording is near-verbatim to **Q1** *and* better matched to our
  graded no-harm metric. **Both edits verified as improvements.**

**VERDICT: ✅ VERIFIED — no manuscript change needed.**

---

# PART C — OUR INFERENCE (our words, NOT theirs)

- **C-1 — "the same failure class."** Ours. The class = *a defense harming honest agents through
  misattributed inconsistency*. TrustFlip **engineers** that inconsistency with physical objects;
  our no-harm metric measures the **naturally arising** version (noise-induced false gating) plus
  behaviour under our adaptive attacker. **We do NOT evaluate an attacker that plants physical
  objects to frame a specific honest drone** — outside our threat model, since our traitors lie in
  broadcasts and never modify the physical scene. Our sentence claims only that we **measure** the
  failure class, which is accurate; it makes no claim of defeating TrustFlip-style framing.
  **Reviewer one-liner:** *"physical-scene manipulation is outside our threat model; the failure
  mode it triggers — honest exclusion — is exactly the quantity our no-harm column measures."*
- **C-2 — the majority contrast.** **Q6** states their target defenses penalise vehicles *"whose
  observations conflict with the majority"*. Our pairwise test consults no majority, so the
  TrustFlip mechanism has no majority to turn against us. **Ours to observe, not their claim** —
  and do not overstate it: a framing attack could still bias a pairwise verifier's own sensing.
- **C-3 — ⭐ NEW: their dilemma is our precision caveat.** **Q7** names a
  *"sensitivity-attribution dilemma"* — smooth over local discrepancies and you miss real ones;
  be sensitive enough to flag them and you become exploitable. That is structurally the same bind
  as our **stealth/harm** result and our **precision 0.80–0.82** caveat: the residual false flags
  are ultra-stealthy camouflage buckets that are statistically ≈ honest noise *and* nearly
  harmless. **Independent third-party evidence that this trade-off is intrinsic to
  consistency-based CP defense, not a weakness peculiar to our filter.** Strong material for the
  discussion section — but the framing is ours.

---

# PART D — VERIFIED BY ABSENCE

**D-1 — no digital intrusion.** **Q8**: the attacker *"does not compromise the victim, inject
digital data, or interfere with V2V communication."* TrustFlip is **purely physical-world**. Our
threat is the complement: our traitors **do** inject false content into broadcasts and never
touch the physical scene. The two threat models are disjoint, which is exactly why our sentence
claims only shared *failure class*, never shared mechanism.

---

## Second-order sweep — full **41**-ref bibliography scanned 2026-07-17, re-confirmed 2026-07-28
Three candidates, all **confirmed present** in the reference list:
1. **LUCIA** = `[9]` Wang et al., *"From threat to trust: Exploiting attention mechanisms for
   attacks and defenses in cooperative perception"*, **USENIX Security 25**, pp. 7387–7406.
   ⚠ This paper was **PRBI's ref [28] and my PRBI-sweep triage missed it** — corrected then, and
   it remains open as task #3 (defense cluster: CP-Guard, CP-Guard+, LUCIA).
2. **Pretend Benign** = `[12]` Lin et al., **ICCV 2025**, pp. 19947–19956 — defense-aware
   stealthy attack, same family as TrustFlip.
3. **Stealthy-Fab** = `[13]` Zhang, Zhang & Mao, arXiv:2605.01301, 2026 — already dossiered
   (`REFERENCE_EVIDENCE_STEALTHY_FAB.md`).

Rest of the 41: CP architectures/datasets/backbones (V2VNet, When2com, V2X-ViT, Where2Comm,
OPV2V, PIXOR, PointPillars, Cooper, EMP, F-Cooper, Coopernaut, VIPS, FusionEye), the physical
adversarial-object line (single-vehicle — our 3D-TC2/ADoPT entry point), **CP-FREEZER** `[10]`
(latency/availability attack — out of family), CAD `[8]`, ROBOSAC `[14]`, MADE `[15]`,
CP-Guard+ `[16]`, MATE `[17]`, and differentiable-rendering utilities. **No other family member.**

## Bookkeeping
- `refs.bib` `trustflip2026`: title *"Adversarial Trust Poisoning in Vehicular Collaborative
  Perception"* ✅ matches the PDF title page; authors Liu/Wang/Li/Zhang ✅; arXiv:2605.22122 ✅
  matches the stamp; cited as arXiv preprint ✅ (v1, no venue stated). ⚠ Same pre-submission
  venue re-check class as PRBI/CoDynTrust/SwarmRaft.
- No manuscript edits arise from this audit.

## ⚠️ OPEN ITEM OWED
🚨 **Integrity-check the other 26 PDFs in `Research paper/`.** TrustFlip's was silently truncated
and still appeared readable to a tolerant extractor. A one-pass check for a missing `%%EOF`
trailer would catch any others. Until that runs, we do not know whether any other dossier rests
on a partial file.

## Re-audit changelog (2026-07-28)
1. 🚨 **Corrupt PDF found and replaced** (512 KB truncated → 11.4 MB intact, 16 pages verified).
2. **M-1 corrected** — bibliography is **41 refs**, not 58.
3. **All 10 quotes re-verified against the intact file — 10/10 exact, zero misquotes.**
4. Restructured into **Parts A–D**.
5. **Case-sensitivity trap documented** — three false alarms (`Pretend benign`, `Among us`,
   `From stealthy data fabrication`) caused by IEEE sentence-case titles.
6. **C-3 added** — their *"sensitivity-attribution dilemma"* (**Q7**) as third-party support for
   our precision caveat.
7. Both of Srinivasa's earlier wording edits re-checked against the source and **confirmed as
   improvements**.

_Standing rule: not closed until Srinivasa signs (`AUDIT_PENDING.md`). Committed ≠ audited._
