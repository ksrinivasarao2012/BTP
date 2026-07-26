# AerialTrust — paired claim/evidence sheet (full re-read, 2026-07-16)

## STATUS: ✅ CLOSED (2026-07-17) — verified independently by Srinivasa against the PDF
Full 12-page read. Found 1 item (catch #21, fixed in related.tex); all other uses verified
against verbatim text. Srinivasa completed the 5-item checklist 2026-07-17.

**The paper:** Hallyburton & Pajic, *"Trust-Based Assured Sensor Fusion in Distributed Aerial
Autonomy"*, ICCPS 2025 (ACM/IEEE, CPS-IoT Week), Duke University. arXiv:2507.17875.
PDF: `Phase_CD/Research paper/AerialTrust.pdf` (12 pages).
⚠️ Ligature trap: search short fragments (`veri`, `preci`) — Ctrl+F on full words can fail.

**What the paper does (their own words):** *"a trust-based framework for assured sensor fusion
in distributed multi-agent networks, utilizing a hidden Markov model (HMM)-based approach to
estimate the trustworthiness of agents and their provided information in a decentralized
fashion"* (Abstract). Setting: *"intelligence, surveillance, and reconnaissance (ISR) missions"*
with *"Ad hoc networks of unmanned aerial vehicles (UAVs)"*. UAVs carry downward-facing (BEV)
gimbaled cameras detecting/tracking GROUND objects; tracks are shared and fused with covariance
intersection (DDF). Trust = Beta distributions updated by pseudomeasurements (PSMs) from pairwise
FOV-aware consistency comparisons; trust weights the fusion (Algorithm 3). Evaluated on the first
multi-agent aerial CARLA dataset (50 agents), metrics = precision/recall/F1, OSPA, trust accuracy.
Attacks: false positive / false negative / translation.

---

## USE 1 — methods.tex lines 146–151 (EWMA design justification)
**WE WRITE (verbatim):** "With $\alpha=0.25$, trust builds gradually under consistent behaviour
but collapses within a few contradictions; the same qualitative requirement --- gradual accrual,
rapid degradation --- has been articulated independently, within a different (Bayesian) trust
formalism, by Hallyburton and Pajic~\cite{aerialtrust2025}."

**THEY WROTE (§5.1, p.5):** *"Moreover, trust should build gradually with consistent behavior,
but degrade quickly with inconsistencies."*
And the formalism is Bayesian: *"Trust estimates are represented by parametric Beta
distributions over the domain [0,1]"* (§1); *"A strength of Bayesian estimation is in the
ability to incorporate prior information"* (§5.3.3). They even implement the asymmetry as a
"Negatively-Weighted Update" (§5.3.7): negative PSMs get extra weight B_cn.

**VERDICT: ✅ VERIFIED — near-verbatim.** "gradual accrual, rapid degradation" ↔ "build
gradually … degrade quickly". "Bayesian trust formalism" ✓ (Beta/HMM).

## USE 2 — related.tex ~line 31 (family sentence) — **CATCH #21 fixed here**
**WE WROTE (before):** "and **its aerial extension**~\cite{aerialtrust2025} carries that
hidden-Markov trust estimation to **UAV surveillance networks**"

**PROBLEM (catch #21):** the ICCPS paper NEVER describes itself as an extension of MATE. Its
stated lineage is the authors' CDC'24 Bayesian-trust paper: *"as we previously proposed in
[16]"* (§1); MATE is cited separately as ground-vehicle work: *"Recent works considered trust
of ground-vehicles in urban environments [17]"* (§2.4, [17] = MATE). Same authors, same
mechanism family — but "its aerial extension" was OUR inference, exactly the class of wording
we've been purging. Also their setting term is **ISR**, not "surveillance networks".

**WE WRITE (after fix, verbatim, related.tex lines 31–34):** "; and the same authors' aerial
framework~\cite{aerialtrust2025} carries that hidden-Markov trust estimation to ad hoc UAV
networks on intelligence, surveillance, and reconnaissance (ISR) missions --- the setting
nearest to ours in the literature."

**THEIR SUPPORT:** same authors (Hallyburton & Pajic on both) ✓; *"hidden Markov model
(HMM)-based approach"* (Abstract) ✓; *"Ad hoc networks of unmanned aerial vehicles (UAVs)"* +
*"intelligence, surveillance, and reconnaissance (ISR) missions"* (Abstract) ✓. ("the setting
nearest to ours" is our comparative judgment, clearly ours.)

**VERDICT: ✅ after fix.**

## USE 3 — related.tex lines 66–71 (centralized-vs-distributed contrast)
**WE WRITE (verbatim):** "Where our setting departs further:
TruPercept~\cite{trupercept2020} aggregates trust at a central server and MATE~\cite{mate2025}
at a central computing centre (the aerial framework~\cite{aerialtrust2025} does distribute the
estimation), whereas our verdicts are pairwise and local, as a swarm without infrastructure
requires."

**THEY WROTE:** *"estimate the trustworthiness of agents and their provided information **in a
decentralized fashion**"* (Abstract); *"In a distributed context, **each agent performs its own
local trust estimation process** using data shared among nearby agents"* (§1); Figure 6 note:
*"Ego agents perform the inner loop **on their own platforms (distributed)**"*.

**VERDICT: ✅ VERIFIED.** Distributed/decentralized is their explicit, repeated claim.

## USE 4 — related.tex lines 159–161 and 171–174 (baseline-comparison paragraph, two sentences)
**WE WRITE (verbatim, lines 169–174):** "That primitive is implemented natively in our setting
in two strengths --- the fixed-tolerance (naive) variant and the noise-aware robust variant
(Section~\ref{sec:methods-defense}) --- and it is the same visibility-and-consistency recipe
underlying TruPercept~\cite{trupercept2020} and the MATE line~\cite{mate2025,aerialtrust2025}."

**WE WRITE (verbatim, lines 158–161, after the 2026-07-16 fixes):** "CAD, PRBI, and GCP operate
on the deep feature maps of vehicular detection stacks and score detection accuracy, while
TruPercept, MATE, and the same authors' aerial framework operate at the object and track level;"
(⚠ two fixes landed here 2026-07-16: (1) this sentence still said "its aerial extension" after
the first catch-#21 pass — it carries no `\cite`, so the citation sweep missed it; (2) Srinivasa's
polish: "score object detections and tracks" → "operate at the object and track level" — the
paper's literal evaluation targets are P/R/F1, OSPA, and agent/track trust accuracy, so
"object and track level" is the exactly-literal description while "score detections" was a
slight broadening.)

**THEY WROTE (mechanism):** PSMs are *"generated with pairwise comparisons between each agent's
most recent situational awareness and **a prediction of what the agent should have seen** based
on its position, sensing capability, and **field of view (FOV)**"* (§1) — visibility (FOV
filtering, §5.3.1) + consistency (assignment proximity, §5.3.2). ✓
**THEY WROTE (metrics — "score object detections and tracks"):** §6.4: *"precision, recall, and
F1-score"*, *"The Optimal Sub-Pattern Assignment (OSPA) measures MTT performance"*, plus track/
agent *"trust accuracy"*. All object/track-level. **No navigation/mission metric** — "Navigation"
appears only as a platform-local module in Figs 2/4, never as an evaluation metric. ✓

**VERDICT: ✅ VERIFIED.** ("MATE line" = our grouping label; defensible: same authors, shared
Beta/PSM/FOV mechanism, and this paper cites both [16] and MATE [17].)

## USE 5 — discussion.tex lines 36–42 (the verifiability boundary) — the load-bearing quote
**WE WRITE (verbatim):** "First, trust models are blind wherever verification is impossible:
Hallyburton and Pajic report that fabrications injected into regions no other agent observes
cannot be detected by existing methods~\cite{aerialtrust2025}. Our camouflage attack is the
statistical analogue of that spatial blind spot --- the verifier \emph{does} observe the
region, but ranging noise forces a tolerance wide enough to hide the lie inside it."

**THEY WROTE (§7.3, p.9 — near-verbatim):** *"It is important to note that the adversary model
is applied randomly across the agent's entire FOV. **In regions where false positives are
injected without overlap from other agents, these false positives cannot be detected using
existing methods.** This modeling choice implies that some degree of performance degradation is
unavoidable by construction due to the randomness of overlap of FOVs."*

**VERDICT: ✅ VERIFIED — this is their sentence, faithfully paraphrased.** ("fabrications
injected" ↔ "false positives are injected"; "regions no other agent observes" ↔ "without
overlap from other agents"; "cannot be detected using existing methods" verbatim.)

---

## Srinivasa's verification checklist (page pointers)
| # | what to check | where in PDF |
|---|---|---|
| 1 | "build gradually … degrade quickly" | p.5, §5.1, paragraph "Trust as enhancement to Byzantine robustness" |
| 2 | HMM + decentralized + ISR + ad hoc UAV networks | p.1 Abstract |
| 3 | lineage: "previously proposed in [16]"; MATE=[17] ground vehicles | p.1 §1 / p.2–3 §2.4 |
| 4 | metrics P/R/F1 + OSPA + trust accuracy (no navigation metric) | p.8 §6.4 + p.12 Appendix A |
| 5 | the blind-spot sentence ("cannot be detected using existing methods") | p.9, §7.3, last paragraph |

## Bookkeeping
- refs.bib `aerialtrust2025`: ICCPS 2025, Hallyburton & Pajic — matches the PDF title page ✓
  (verified earlier via ACM DL; arXiv:2507.17875 ✓ matches PDF header)
- Catch #21 applied 2026-07-16: "its aerial extension" → "the same authors' aerial framework"
  (related.tex, THREE places — lines ~31, ~68, and the uncited line ~161 found during the
  verbatim-quote pass); "UAV surveillance networks" → "ad hoc UAV networks on … (ISR) missions".
  Verified: `grep -i "aerial extension|surveillance network"` over manuscript/ → 0 matches.
- All WE WRITE blocks above are verbatim from the tex files as of 2026-07-16 (line numbers given).
