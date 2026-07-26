# TruPercept — paired claim/evidence sheet (final, 2026-07-10)

Every place our manuscript cites TruPercept, shown as a PAIR:
**WE WRITE** = the exact current sentence in our `.tex` · **THEY WROTE** = the verbatim passage in
their PDF (`Phase_CD/Research paper/TruPercept.pdf`) that supports it, with their section number.
All 7 uses verified word-by-word on 2026-07-10 (9 correction rounds applied; see PAPER_TODO §C).
Ligature note: in their PDF, Ctrl+F for "verified/significantly/confidence" may fail (fi-ligature);
search shorter fragments (`veri`, `signi`, `conf`).

---

## USE 1 — Introduction ¶3: the problem is real

**WE WRITE (`sections/introduction.tex`):**
> The difficulty of getting this right is not hypothetical: an early study of trust-modulated
> cooperative perception found that cooperative fusion did not meaningfully improve accuracy over
> local perception, with false detections inserted at high confidence among the suspected
> causes~\cite{trupercept2020}.

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

**WE WRITE (`sections/related.tex`):**
> ...TruPercept further reports that unreliable agents which mostly report truthfully are not
> separated from honest ones by its trust model~\cite{trupercept2020} --- an early indication of
> the evasion regime we formalize. Where our setting departs further: TruPercept aggregates trust
> at a central server, whereas our verdicts are pairwise and local, as a swarm without
> infrastructure requires.

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

**WE WRITE (`sections/related.tex`):**
> ...while TruPercept, MATE, and its aerial extension score object detections and tracks; none is
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
