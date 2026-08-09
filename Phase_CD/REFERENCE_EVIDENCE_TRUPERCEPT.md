# TruPercept — paired claim/evidence sheet

## STATUS: ☐ **AWAITING SRINIVASA'S REVIEW** — full re-audit 2026-07-29

> ⚠️ **Attribution.** All verification here — paper reading, quote checking, searches, drafting —
> is **CLAUDE'S WORK**. Srinivasa's role is **review and approval**.

**Why re-audited:** TruPercept has the **largest citation surface of any paper we cite** — 8
citation sites across **4 files** (`introduction`, `results`, `related` ×5, `discussion`). It was
also one of six dossiers whose `WE WRITE` blocks had drifted (resynced 2026-07-28).

**Re-audit results (2026-07-29), full 7-page re-read:**
- ✅ **PDF intact** — 1,291,148 bytes, valid `%%EOF` (the TrustFlip truncation check).
- ✅ **All 13 load-bearing quotes verified** against the paper text.
- ⚠️ **3 apparent failures were fi-ligature artifacts** (`confidence`, `significantly`,
  `verified`) — exactly what this file's own ligature note predicts. Re-verified with ligature
  normalisation: all three present. **Not errors.**
- ✅ **All 8 citation sites are documented** by the 7 USE blocks (USE 5 covers two adjacent
  citations in `related.tex`). Nothing undocumented.
- 🔄 **TWO blocks resynced** (each with an in-place drift note):
  - **USE 1** — the introduction paragraph was restructured 2026-07-29; only the framing clause
    changed, the load-bearing words are byte-identical.
  - **USE 5** — ⚠️ *found during this audit, not previously known.* A **MATE / aerial-framework
    clause was inserted mid-sentence** in `related.tex`, invalidating this block's text. Classic
    shared-paragraph drift: the edit was made for a different paper. No TruPercept claim changed.
- ✅ **The other five USE blocks re-checked against live `.tex` and match** — USE 2
  (`results.tex` 24–29), USE 3 (`related.tex` 66–70), USE 4 (81–97), USE 6 (223–247), USE 7
  (`discussion.tex` 42–49). Only USE 5 had drifted.
- ⭐ **NEW finding not previously recorded** — see *"Their own coordinated-attack admission"*. It is
  logged as a **CANDIDATE (not cited anywhere)**, with a scope check (C-1) and three banned
  sentences, because the naive reading of it is wrong: their trust model **did** catch the
  malicious vehicles; the weakness they admit is that accuracy degraded anyway.
- ⚠️ **One self-correction inside this re-audit, logged in Part D** — I wrote an absence claim
  before running its search; the search then returned a second hit, which became finding A-6. The
  error is recorded in place rather than silently repaired.

**Nothing in the manuscript changed as a result of this re-audit** apart from the USE 1 resync
(which tracked an edit made for other reasons). No claim we make about TruPercept was found wrong.

---

_(original header, 2026-07-10)_

Every place our manuscript cites TruPercept, shown as a PAIR:
**WE WRITE** = the exact current sentence in our `.tex` · **THEY WROTE** = the verbatim passage in
their PDF (`Phase_CD/Research paper/TruPercept.pdf`) that supports it, with their section number.
All 7 uses verified word-by-word on 2026-07-10 (9 correction rounds applied; see PAPER_TODO §C).
Ligature note: in their PDF, Ctrl+F for "verified/significantly/confidence" may fail (fi-ligature);
search shorter fragments (`veri`, `signi`, `conf`).

---

## USE 1 — Introduction ¶3: the problem is real

**WE WRITE (`sections/introduction.tex` line 57) — 🔄 RESYNCED 2026-07-29:**
> That this difficulty is not hypothetical is borne out by an early
> study of trust-modulated cooperative perception, which found that
> cooperative fusion did not meaningfully improve accuracy over local
> perception, with false detections inserted at high confidence among the
> suspected causes~\cite{trupercept2020}.

> ⚠️ **DRIFT NOTE (2026-07-29).** The introduction paragraph was restructured on 2026-07-29 (the
> orphaned *"Our third finding"* was removed and this citation moved from the middle of the
> paragraph to its end, where it corroborates the claim instead of delaying it).
> **Only the framing clause changed** — *"The difficulty of getting this right is not
> hypothetical:"* → *"That this difficulty is not hypothetical is borne out by"*.
> **The load-bearing words are byte-identical**: *"cooperative fusion did not meaningfully improve
> accuracy over local perception, with false detections inserted at high confidence among the
> suspected causes"*. The verification below therefore still holds unchanged.

**THEY WROTE (§VI.A):**
> "The most important insight is that none of the tested methods improve the perceptual accuracy
> by a meaningful margin over the local perception methods. ... Two plausible explanations for the
> poor TruPercept results are: 1) The alignment issues with the synthetic data could reduce
> performance for cooperative, but not local, perception. 2) Each perspective can introduce false
> detections ... likely caused by false detections from nearby vehicles being inserted with high
> scores."

**Match:** "did not meaningfully improve" = their "not ... by a meaningful margin"; "among the
suspected causes" honours their TWO "plausible explanations". ("naively" removed — their failing
methods included trust modelling; catch #9.)

---

## USE 2 — Results §anchor/dropout: sharing gives no advantage at 0% dropout

**WE WRITE (`sections/results.tex`):**
> ...at $0\%$ dropout sharing confers no advantage --- the gap is in fact slightly negative
> ($-1.3$ pp, CI $[-2.3,-0.4]$), consistent with the early observation that cooperative
> perception did not meaningfully improve over local perception~\cite{trupercept2020}...

**THEY WROTE (§VI.A):** same passage as USE 1 ("none of the tested methods improve the perceptual
accuracy by a meaningful margin over the local perception methods").

**Match:** now a direct restatement of their result — no interpretive clause. (History: catch #10
replaced "statistically indistinguishable", which our own CI contradicted; catch #11 then removed
"perception that is already intact" — OUR diagnosis of WHY, which TruPercept never concludes; they
only report the result and offer two candidate explanations.)

---

## USE 3 — Related Work: what TruPercept is (object-level family)

**WE WRITE (`sections/related.tex`):**
> TruPercept~\cite{trupercept2020} evaluates reported object detections as verified locally,
> weighting each evaluation by the visibility of the claimed object from the verifier's viewpoint
> before computing peer trust;

**THEY WROTE (Abstract):**
> "Based on the accuracy of reported object detections as verified locally, communicated messages
> can be fused to augment perception performance..."

**THEY WROTE (§III.C):**
> "The evaluation from each vehicle v will be aggregated in proportion to how visible the
> detection is from each evaluator perspective v (i.e., Phi_v(theta))."  ·  and their Eq. (4):
> vehicle (peer) trust is aggregated FROM detection-level trust over a freshness window.

**Match:** now mirrors their actual pipeline order — evaluate detections locally -> weight by
visibility -> aggregate into peer trust. (History: catch #4 moved TruPercept out of the wrong
"deep feature" grouping; catch #12 fixed "scores peers by..." which collapsed the detection-level
and peer-level stages into one step.)

---

## USE 4 — Related Work: the plausibility checker (pre-empting "their checker kills your attack")

**WE WRITE (`sections/related.tex`):**
> It is instructive that TruPercept additionally rejects \emph{open-space} phantoms with a
> plausibility check that culls the sensor frustum toward a claimed object: an object with no
> returns in front of it, but returns behind it, is deemed absent with high
> confidence~\cite{trupercept2020}. Operationally, such a test derives its evidence from rays
> passing through empty space at the claimed location, which is exactly what a phantom placed in
> free space provides --- and, in our own experiments, one reason the conspicuous wall attack
> proves comparatively easy to detect (Section~\ref{sec:res-temporal}). A camouflaged phantom is
> designed to avoid supplying that evidence: placed flush against a real obstacle, its claimed
> volume coincides with returns the verifier genuinely receives from nearby structure, so a
> free-space plausibility test has little to discriminate on. We note that TruPercept does not
> evaluate camouflaged fabrications, and we make no claim about the behaviour of its checker in
> our setting; the point is that geometric plausibility tests derive their power from rays
> traversing empty space, and camouflage attacks intentionally deny them that.

**THEY WROTE (§III.E):**
> "This could be taken advantage of if a malicious agent were to insert false detections where
> there are no points. ... If there are points behind the object, and no points in front or within
> the object bounding box, then the existence of the object is false with high confidence. ...
> The TruPercept system incorporates a novel plausibility checker which performs a frustum cull on
> the point cloud. The frustum is centered to the object center... If more than 10% of the points
> are closer than the object center, it is considered plausible."

**Match:** mechanism described in their words; "camouflage" = 0 hits in their PDF → our explicit
disclaimer. (Wording softened from "defeats it by construction" — catch #3; "requires raw point
clouds" error removed — catch #5 of the wording series.)

---

## USE 5 — Related Work: evasion finding + central-server contrast

**WE WRITE (`sections/related.tex` lines 103–113) — 🔄 RESYNCED 2026-07-29, character-exact:**
> ...TruPercept further reports that unreliable agents which mostly
> report truthfully are not separated from honest ones by its trust
> model~\cite{trupercept2020} --- an early indication of the evasion regime we
> formalize. Where our setting departs further:
> TruPercept~\cite{trupercept2020} aggregates trust at a central server and
> MATE~\cite{mate2025} at a central computing centre (the aerial
> framework~\cite{aerialtrust2025} does distribute the estimation), whereas
> our verdicts are pairwise and local, as a swarm without infrastructure
> requires.

> ⚠️ **DRIFT NOTE (2026-07-29).** The block previously recorded here read *"TruPercept aggregates
> trust at a central server, whereas our verdicts are pairwise and local…"*. The live sentence has
> since had a **MATE / aerial-framework clause inserted mid-sentence**. This is textbook
> **shared-paragraph drift**: the edit was made for MATE's sake and silently invalidated
> TruPercept's `WE WRITE` block. **No TruPercept claim changed** — every word this dossier
> verifies (*"aggregates trust at a central server"*, *"our verdicts are pairwise and local, as a
> swarm without infrastructure requires"*) is byte-identical. The evidence below still holds.
> ⬜ **Cross-check owed:** the inserted clause asserts things about **MATE** and **AerialTrust** —
> *"at a central computing centre"* and *"does distribute the estimation"*. Those are **not this
> dossier's to verify**; they must be checked in `REFERENCE_EVIDENCE_MATE.md` and
> `REFERENCE_EVIDENCE_AERIALTRUST.md`, both of which are still unaudited.

**THEY WROTE (§VI.C):**
> "The trust value for unreliable vehicles is not significantly different than trustworthy
> vehicles. It is likely that behaviours such as the unreliable behaviour, which mostly present
> true detections, will be able to fool the current system."

**THEY WROTE (§III.C):**
> "Trust calculation can be done centrally or by each vehicle. Central aggregation introduces a
> strong system requirement (central server), but is better as vehicles only enter within
> proximity of each other for short time periods... Trust values are calculated for each object
> and then vehicle on the central server and then periodically broadcast..."

**Match:** "mostly report truthfully" = their "mostly present true detections"; "aggregates at a
central server" = their implemented choice (we say "aggregates", not "must aggregate" — they note
the per-vehicle alternative exists).

---

## USE 6 — Related Work: baseline paragraph (why not run it as a baseline)

**WE WRITE (`sections/related.tex` lines 223–250) — 🔄 RESYNCED 2026-07-28:**
> ...while TruPercept, MATE, and **the same authors' aerial framework operate at the object and
> track level**; none is
> designed to operate directly on the geometric obstacle claims exchanged by our agents, and none
> produces the navigation-success outcome we measure --- a reimplementation would test our
> translation of each method rather than the method itself. ... That primitive ... is the same
> visibility-and-consistency recipe underlying TruPercept~\cite{trupercept2020} and the MATE
> line~\cite{mate2025,aerialtrust2025}.
> (History: catch #14 — "none consumes ..." implied impossibility; softened to "is designed to
> operate directly on", which leaves the translation-layer possibility open, consistent with our
> own reimplementation caveat.)

**THEY WROTE (§III.A + §VI):**
> "An object instance ... is detailed with a class (vehicle, pedestrian, cyclist), 3D position ...
> 3D bounding box dimensions ... heading ... and a score."  ·  Metrics: "% AP" throughout
> Tables I-III. ("navigation" / "success rate" appear nowhere in their evaluation.)

**Match:** they score detections by AP; no navigation outcome exists to compare against.
("in surveillance settings" removed — TruPercept is autonomous driving; catch #8.)

---

## USE 7 — Discussion: verifiability boundary

**WE WRITE (`sections/discussion.tex`):**
> Second, an attacker that mostly reports truthfully evades trust accumulation: TruPercept
> observed that unreliable agents were not separated from honest ones by trust
> scores~\cite{trupercept2020}. Our adaptive-attacker study makes this quantitative and then
> closes it: evasion requires collapsing the fabrication onto real geometry, at which point it
> blocks no new space.

**THEY WROTE (§VI.C):** same passage as USE 5 ("not significantly different than trustworthy...").

**Match:** direct; the second sentence is about OUR study (bind table, `adaptive_offset_f2_500.txt`).

---

## ⭐ Their own coordinated-attack admission (NEW, 2026-07-29) — **CANDIDATE, NOT YET USED**

> **Status: NOT CITED ANYWHERE IN THE MANUSCRIPT.** This block records verified evidence found
> during the 2026-07-29 re-read. It has **no `WE WRITE` counterpart** because we do not currently
> use it. Do not treat its absence from the `.tex` as drift. If we ever wire it in, the wording
> must come from Part-A below, not from Part-B.

### PART A — PAPER FACTS (their exact words, §VI.C "Trust Levels")

**A-1. What their "malicious" behaviour actually is:**
> "Malicious: a vehicle and pedestrian are inserted in front of the ego-vehicle for every frame
> from 10% of vehicles."

**A-2. The harm:**
> "The malicious detections decrease the performance significantly, even for pedestrians."

**A-3. The admission (verbatim):**
> "The malicious detections behaviour represents a coordinated attack between 10% of the vehicles
> specifically targeted towards the ego-vehicle. This shows a weakness in the model towards
> coordinated attacks."

**A-4. Their measured trust separation:**
> "The mean trust values at the termination of the experiments were: 0.27 trustworthy, 0.25
> unreliable, and 0.13 malicious."

**A-5. And — critically — they state the malicious agents WERE caught:**
> "The trust model was able to detect blatantly malicious behaviour with a much higher success."

**A-6. The same detect-but-don't-remove pattern, stated for a single frame (§V.A, "Scenario 1:
Algorithm Analysis Using a Single-Frame") — found while re-running the Part-D searches:**
> "A false detection in a dangerous location (less than 10m away, directly in its trajectory, and
> oncoming) for the ego-vehicle is inserted into the broadcast of the oncoming vehicle. The false
> detection is given a high detection score (1.0) in an attempt to fool the ego-vehicle."

and, two sentences later:
> "Unfortunately the false detection, although the score is decreased, is still present. However,
> if the plausibility checker is also run, it can eliminate the possibility that the false
> detection exists while still maintaining the pedestrian which is occluded."

**Tested Ctrl+F fragments** (each verified to sit on a single PDF line, no fi/ffi ligature, no
hyphenation across the fragment — so each should match in a reader's find box):
| fragment | for |
|---|---|
| `a vehicle and pedestrian are inserted in front` | A-1 |
| `malicious detections decrease the performance` | A-2 (stops before the `fi` ligature) |
| `represents a coordinated attack between 10% of the vehicles` | A-3 |
| `weakness in the model towards coordinated attacks` | A-3 |
| `0.27 trustworthy, 0.25 unreliable, and 0.13` | A-4 |
| `The trust model was able to detect blatantly` | A-5 |
| `detection score (1.0) in an attempt to fool the ego-vehicle` | A-6 |
| `although the score is decreased, is still present` | A-6 |

### PART C — OUR TECHNICAL INTERPRETATION (**not attributable to the authors**)

> ⚠️ Everything below is OUR reading. TruPercept states A-1..A-5 and nothing further. None of the
> sentences here may be presented as the authors' conclusion.

**C-1. SCOPE CHECK — what their admitted weakness is, and what it is NOT.**
Read together, A-2 + A-3 + A-5 say: their trust model **identified** the malicious vehicles
(trust 0.13, well below 0.27) and perception accuracy **still degraded significantly**. Their
admitted weakness is therefore **detection without sufficient mitigation** under a coordinated
minority, *not* a failure to detect. **This distinction is load-bearing.** Writing "TruPercept's
trust model fails to catch coordinated attackers" would be the same class of error as the
3D-TC2 M-2 scope failure — a correct quote used for a claim its context contradicts.

**A-6 independently corroborates this reading in the authors' own words**, on a single frame and
without any aggregation: the trust mechanism *downweighted* the injected false detection but did
not remove it (*"although the score is decreased, is still present"*), and it was the
**plausibility checker** — not the trust score — that eliminated it. Note the coupling to USE 4:
the component that actually removed the phantom is the **free-space** frustum test whose evidence
a camouflaged fabrication is designed not to supply. We may state that coupling only as OUR
reading; TruPercept never discusses camouflage (`camouflage` = 0 hits, recorded at USE 4).

**BANNED SENTENCES** (each contradicted by A-5; never write any of these):
- ❌ "TruPercept could not detect coordinated attackers."
- ❌ "Their trust model breaks down when multiple agents lie."
- ❌ "Their 0.13 malicious trust value shows the attack evaded detection." *(0.13 is the LOWEST of
  the three — it shows the opposite.)*

**C-2. What it legitimately supports.** A-3 is an author-stated open weakness under a
**multi-agent, persistently-fabricating** adversary — the same adversary class we sweep in
$f = 1\ldots7$. It is usable as corroboration that multi-traitor coordination was flagged as an
open problem by an early trust-modelling paper, i.e. motivation for our $f$-sweep. It is **not**
usable as a comparison of detection performance, because they report AP and mean trust and we
report navigation success and detection recall — different quantities on different tasks.

**C-3. Why it is only a candidate.** Our current multi-traitor argument rests on our own
$f = 4\ldots7$ CIs, which do not need external corroboration. Adding this citation buys motivation
but adds a scope-error surface (C-1). Recommendation: **hold unless a reviewer challenges the
premise that coordinated multi-agent fabrication is an open problem**, in which case cite A-3.

### PART D — VERIFIED BY ABSENCE (searches re-run and **corrected** 2026-07-29)

> ⚠️ **Self-correction, logged.** My first draft of this Part D asserted *"the only 'fool'
> occurrence is about the unreliable behaviour."* **That was wrong** — running the search returned
> **two** hits. The second (line 436 of the extracted text, §V.A) is the source of A-6 above. The
> claim was written before the search was executed; that is precisely the failure mode this
> dossier standard exists to prevent, so it is recorded rather than quietly fixed.

Search performed over the full extracted text
(`scratchpad/trupercept_text.txt`, 7 pages, case-insensitive):

| pattern | hits | where |
|---|---|---|
| `fool` | **2** | L436 §V.A (→ A-6); L594 §VI.C (the *unreliable* behaviour, already USE 5 / USE 7) |
| `evade` / `evasi` | 0 | — |
| `undetected` | 0 | — |
| `escape` | 0 | — |
| `not detected` | 0 | — |
| `coordinat` | **2** | L586, L588 — both in the A-3 sentence pair; the word appears nowhere else |

**What this establishes:** the authors nowhere claim the coordinated/malicious attack *evaded*
trust scoring. Both surviving statements about their mechanism being defeated concern the
**unreliable** (mostly-truthful) behaviour, not the malicious one. Confirms C-1 and the banned
sentences above.

---

## Bibliography entry (`manuscript/refs.bib`)
```bibtex
@inproceedings{trupercept2020,
  title     = {{TruPercept}: Trust Modelling for Autonomous Vehicle
               Cooperative Perception from Synthetic Data},
  author    = {Hurl, Braden and Cohen, Robin and Czarnecki, Krzysztof and
               Waslander, Steven},
  booktitle = {2020 IEEE Intelligent Vehicles Symposium (IV)},
  pages     = {341--347},
  year      = {2020}
}
```
Metadata verified against arXiv 1909.07867 + IEEE IV 2020 listing.

## Correction history on this reference (for the record)
1. "weighs deep feature contributions" -> object detections (family regrouped).
2. "defeats the plausibility checker by construction" -> hedged mechanism argument + disclaimer.
3. "their check requires raw point clouds" -> removed (late fusion; checker uses verifier's LOCAL cloud).
4. Intro "failed to improve at all, because..." -> "did not meaningfully improve ... suspected causes".
5. Intro "naively fusing" -> "cooperative fusion" (their failing methods included trust).
6. Baseline "in surveillance settings" -> removed (autonomous driving).
7. Results "statistically indistinguishable" at 0% dropout -> honest negative gap + hedged parallel cite.
