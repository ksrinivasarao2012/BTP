# Conformity — paired claim/evidence sheet (full read, 2026-07-17)

## STATUS: ⏳ CLAUDE'S AUDIT DONE — **AWAITING SRINIVASA'S INDEPENDENT REVIEW**
Full 6-page read (arXiv:2606.21206v1). Our descriptive clause verifies phrase by phrase.
**One catch (#25, minor, FIXED):** the follow-on boundary sentence said "These works
*protect* state agreement or collective decision-making" — but this paper is an ANALYSIS
that models attack propagation, not a protection mechanism. Verb fixed. Closed only after
Srinivasa's own audit.

**The paper:** Ruixing Ren, Junhui Zhao, He Fang (Beijing Jiaotong Univ. / Fujian Normal
Univ.), *"Local Conformity-Based Evolutionary Game Modeling of UAV Swarm Under Byzantine
Attack"*, arXiv:2606.21206v1 (19 Jun 2026, eess.SY), 6 pages, conference format.
PDF: `Phase_CD/Research paper/Conformity.pdf`.

**What the paper does (their own words):** *"This paper constructs an evolutionary game
model for UAV swarm under malicious attacks based on graph evolutionary game theory,
revealing how local conformity rules govern the spread of deceptive strategies"* (Abstract).
Setting: N UAVs each measure a BINARY system state θ∈{0,1} with error probability ε and
report to a GROUND STATION for fusion. Malicious UAVs flip reports with probability Pa;
legitimate UAVs may be induced (via death-birth imitation of high-fitness neighbours) into
a "deceptive strategy" of inverting their own reports. Derives the ODE for the fraction p_m
of deceived legitimate UAVs and closed-form evolutionary stable states (Eq. 38). Findings:
conformity is an ATTACK AMPLIFIER (*"the conformity effect acts as an amplifier for
Byzantine attacks"*, Conclusion); higher observation error ε WEAKENS malicious induction;
more attackers (β) and higher attack intensity (Pa) raise the steady-state deception
fraction; topology-robust (regular/BA/ER, N=500). No defense is proposed — *"This study
provides a theoretical reference for designing security strategies"* (Conclusion).

---

## USE 1 (the ONLY use) — related.tex ~lines 131–132
**WE WRITE (verbatim):** "and evolutionary-game analyses~\cite{conformity2026} model how
deceptive strategies propagate through conformity dynamics under Byzantine influence."

**THEY WROTE, phrase by phrase:**
- "evolutionary-game analyses" ✓ — *"an evolutionary game model … based on graph
  evolutionary game theory"* (Abstract); it IS an analysis paper (model + ODE + ESS), and
  our verb is "model", not "defend" — correct level.
- "deceptive strategies propagate" ✓ — *"revealing how local conformity rules govern the
  spread of deceptive strategies"* (Abstract); *"uncovering the propagation mechanism of
  deceptive strategies within swarms"* (§I contributions). "Deceptive strategy" is THEIR
  term (S_m, a legitimate UAV inverting its reports after being induced).
- "through conformity dynamics" ✓ — *"local conformity rules (the tendency to align states
  with neighbors)"* (§I); death-birth imitation dynamics (§II).
- "under Byzantine influence" ✓ — title: *"…UAV Swarm Under Byzantine Attack"*; malicious
  UAVs = Byzantine attackers injecting false reports.

**VERDICT: ✅ VERIFIED.**

## CATCH #25 (minor, fixed 2026-07-17) — the boundary sentence's verb
**WE WROTE (before):** "These works protect state agreement or collective decision-making;
our threat lives one layer below…"
**PROBLEM:** "These works" = SwarmRaft + this paper. SwarmRaft protects; the conformity
paper PROTECTS NOTHING — it is a theoretical model of how an attack spreads (its own
conclusion offers only *"a theoretical reference for designing security strategies"*).
Same mistake class as #24 (describing a cited paper at the wrong level), low severity.
**WE WRITE (after, verbatim):** "These works protect state agreement or model attacks on
collective decision-making; our threat lives one layer below, in the \emph{perception
content} that robots exchange…" — now SwarmRaft→protects state agreement,
Conformity→models attacks on collective decision-making; the layer contrast is unchanged.

---

## Nuances noted (no manuscript change)
- **Their UAVs also judge neighbours by own sensing** — *"each UAV evaluates its neighbors'
  utilities based on its own sensor readings: neighbors whose reports match its local
  measurements are regarded as adopting the honest strategy"* (§II). Superficially close to
  our pairwise own-sensing verification, BUT it feeds an IMITATION rule (adopt high-fitness
  neighbour strategies) — which is exactly the vulnerability their paper studies. Our
  mechanism gates/excludes rather than imitates, reports are geometric obstacle claims (not
  1 bit), and there is no ground station. No novelty threat; if a reviewer raises it, the
  one-liner: "there, own-sensing comparison drives conformity (the attack vector); here it
  drives exclusion (the defense)."
- **Their ε-effect runs OPPOSITE to ours and does not conflict:** for them, more observation
  error WEAKENS the attack (decisions go random, diluting directed induction); for us, more
  ranging noise STRENGTHENS the camouflage attack (lie hides inside the honest tolerance).
  Different mechanisms — theirs is bit-flip voting, ours is geometric verification. No
  contradiction to disclose, but worth knowing if a reviewer juxtaposes them.

## Second-order sweep (standing rule) — FULL 15-ref bibliography title scan done 2026-07-17
**Zero new family members.** Refs: authors' own IoV/6G/ISAC papers ([1],[4],[10],[11]),
blockchain VANET trust management ([2] — message-layer trust, the van der Heijden-survey
niche already covered by PRIOR_ART_SECOND_ORDER item 5), UAV-swarm security SURVEY ([3],
ACM Comput. Surveys 2024 — optional background cite, LOW priority, no mechanism), hierarchical
authentication ([5]), secure comm/anti-jamming DL ([6],[7]), privacy-preserving consensus
under DoS ([8]), resilient formation-tracking under Byzantine attacks ([9] — CONTROL layer,
covered by our consensus-paragraph boundary), game-theoretic swarm reconfiguration ([13]),
misinformation-evolution ([12]), replicator equation on graphs ([14]), PhD thesis ([15]).
None touch perception-content exchange.

## Srinivasa's verification checklist (page pointers, arXiv v1)
| # | what to check | where in PDF |
|---|---|---|
| 1 | "revealing how local conformity rules govern the spread of deceptive strategies" (our phrase source) | p.1 Abstract |
| 2 | it models/analyzes only — no defense proposed ("theoretical reference for designing security strategies") | p.6 §V Conclusion |
| 3 | setting = binary state reports to a GROUND station; deceptive strategy S_m = inverted reports via imitation | p.1–2 §II |
| 4 | "the conformity effect acts as an amplifier for Byzantine attacks" | p.6 §V |

## Bookkeeping
- refs.bib `conformity2026`: title exact ✓, authors Ren/Zhao/Fang ✓, arXiv:2606.21206 ✓
  matches PDF stamp; cited as arXiv preprint ✓ (conference-style manuscript, no venue
  stated) — ⚠ same pre-submission venue re-check class as PRBI/CoDynTrust/SwarmRaft/TrustFlip.
- Catch #25 applied to related.tex (boundary-sentence verb) 2026-07-17.
