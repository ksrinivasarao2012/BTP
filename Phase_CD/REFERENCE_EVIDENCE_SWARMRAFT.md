# SwarmRaft — paired claim/evidence sheet

## STATUS: ☑ AUDITED & APPROVED (Srinivasa, 2026-07-26) — re-verified 2026-07-28
Full 10-page re-read 2026-07-28 under the verbatim-only standard. **Substance fully intact; one
verb form corrected inside quotation marks (M-1), zero manuscript impact.** Sign-off stands.

**Result of the re-audit:**
- ✅ `related.tex` sentence verified clause by clause; **"agree on state updates such as location
  and heading" is their abstract almost word for word**
- ✅ 11 of 12 quotes exact; **7 apparent failures were line-break artifacts** (two-column IEEE
  layout breaks aggressively, and the extractor also drops spaces: `thathonestvotes`)
- ❌ **M-1**: one verb form altered inside quotes — corrected
- ✅ "43-ref bibliography" claim **confirmed** (`[1]`–`[43]`)
- ✅ The layered crash-fault/Byzantine nuance was **already handled correctly** — the previous
  audit's most valuable work, and it survives scrutiny
- ⭐ **NEW:** a sharper differentiator found in their Figure 2 scaling result — see C-3

**The paper:** Kapel Dev, Yash Madhwal, Sofia Shevelo, Pavel Osinenko, Yury Yanovich (Skolkovo
Institute of Science and Technology), *"SwarmRaft: Leveraging Consensus for Robust Drone Swarm
Coordination in GNSS-Degraded Environments"*, arXiv:2508.00622v2 [cs.DC], 25 Sep 2025.
PDF: `Phase_CD/Research paper/SwarmRaft.pdf` (10 pages, intact).
⚠ Page header reads **"IEEE INTERNET OF THINGS JOURNAL, VOL. NN, NO. N, AUGUST 2025"** — an
IoT-J *manuscript template with unfilled volume/number*, i.e. **not yet published**. Cite as
arXiv preprint. Same pre-submission venue re-check class as PRBI/CoDynTrust.

---

## ❌ M-1 — THE MISQUOTE (the only defect found)

| | |
|---|---|
| **Dossier said** | *"**combines** GNSS, INS, and peer-to-peer fusion"* |
| **Paper says** (p.1, §I) | "approaches, such as SwarmRaft, that **combine** GNSS, INS, and peer-to-peer fusion" |
| **Problem** | verb form changed inside quotation marks. Grammatically tempting (SwarmRaft is singular) but the original agrees with *"approaches"*. Correct practice is `combine[s]` |
| **Manuscript impact** | **NONE** — not quoted in `related.tex` |
| **Status** | Corrected in Part A (**Q6**) |

---

# 🔍 HOW TO AUDIT THIS (~10 min)

### ⚠️ TRAP — this PDF is the worst of the four for search
Two-column IEEE layout, so **7 of 12 quotes are broken across lines**, and the extractor also
**deletes spaces around italics**: the file literally contains `thathonestvotes outnumber` and
`arehonest, authorized`. Searching a full sentence will nearly always fail.

| Reads continuously | In the file |
|---|---|
| "agree on state updates such as location and heading" | `…state updates`⏎`such as location…` |
| "compute and communication modules are honest" | `communication mod-`⏎`ules arehonest` |
| "honest votes outnumber colluding malicious votes" | `thathonestvotes outnumber`⏎`colluding…` |
| "crash-tolerant localization framework…" | `crash-tolerant localiza-`⏎`tion framework` |

Every fragment in Part A was **executed against the extracted text** before being written down.

---

# PART A — THEY WROTE (verbatim only)

| ID | Their exact words | Page / § | ✅ TESTED fragment |
|---|---|---|---|
| **Q1** | "This paper proposes SwarmRaft, a blockchain-inspired positioning and consensus framework for maintaining coordination and data integrity in UAV swarms operating under GNSS-denied conditions. SwarmRaft leverages the Raft consensus algorithm to enable distributed drones (nodes) to agree on state updates such as location and heading, even in the absence of GNSS signals for one or more nodes." | p.1, Abstract | `agree on state updates` ⚠break |
| **Q2** | "Byzantine Fault-Tolerant (BFT) protocols, e.g., Practical Byzantine Fault Tolerance (PBFT), Tendermint, Exonum… assume adversarial behavior and incur unnecessary complexity for typical crash-fault scenarios in swarms." | p.1, §I | `assume adversarial behavior and incur unnecessary` |
| **Q3** | "…crash-tolerant consensus protocols, such as Raft, which are designed for environments where nodes (the drones) may fail by crashing, but not by acting maliciously." | p.1, §I | `may fail by crashing, but not by` ⚠break |
| **Q4** | "SwarmRaft… leverages peer-to-peer distance measurements, crash fault-tolerant communication consensus, and a Byzantine-resilient evaluation mechanism to detect and correct malicious or faulty position reports." | p.3, §III.A | `peer-to-peer distance measurements` |
| **Q5** | "SwarmRaft introduces a lightweight, crash-tolerant localization framework that combines peer-based voting with distributed fault recovery…" | p.2, §II | `crash-tolerant localiza` ⚠hyphen |
| **Q6** ✅corrected | "…collaborative, consensus-driven approaches, such as SwarmRaft, that **combine** GNSS, INS, and peer-to-peer fusion to achieve robust and fault-tolerant state estimation in UAV swarms." | p.1, §I | `that combine GNSS, INS, and` |
| **Q7** | **Assumption 1:** "Nodes' compute and communication modules are honest, authorized, and synchronous." | p.3, §III.B | `communication mod` ⚠hyphen |
| **Q8** | **Assumption 2:** "Only GNSS sensors can be Byzantine, while INS are reliable. Up to f nodes' GNSS sensors out of n may be arbitrarily corrupted, where n ≥ 2f + 1." | p.3, §III.B | `Only GNSS sensors can be Byzantine` |
| **Q9** | **Assumption 3:** "True positions at time k = 0 are securely known." | p.3, §III.B | `securely known` |
| **Q10** | "By enforcing the requirement n ≥ 2f+1 and using majority thresholds, the scheme guarantees that honest votes outnumber colluding malicious votes, ensuring that no coalition of size ≤ f can force an incorrect global decision." | p.3, §III.B | `votes outnumber` ⚠break+spacing |
| **Q11** | "The protocol tolerates up to f Byzantine faults, including GNSS spoofing, range manipulation, and collusion." | p.5, §III.G | `Byzantine faults, including GNSS spoofing` |
| **Q12** | "…causing each compromised node to report position measurements… that are offset by an arbitrary, potentially time-varying bias." | p.3, §III.B, Attack 1 | `offset by an arbitrary, potentially` ⚠break |
| **Q13** | "We assume the communication graph among the n UAVs is fully connected and synchronous…" | p.3, §III.B | `fully connected and synchronous` |
| **Q14** | "…future research will focus on incorporating confidence-weighted fusion, **dynamic trust scores**, and asynchronous consensus strategies…" | p.8, §VI | `dynamic trust` |

### Their numbers — verified

| Claim | Source | ✓ |
|---|---|---|
| Threshold `T = µ_e + 3σ_e`, offline-calibrated under honest operation; Gaussian tail < 0.01 | §III.E | ✅ |
| Vote `+1 / −1`; `S_i ≥ 0` honest, `S_i < 0` faulty | §III.E.1 | ✅ |
| Monte Carlo: `n ∈ {3…17}`, `f ∈ {1…8}`, **10,000** trials | §V.B | ✅ |
| Mean recovery error **19 m → 0.28 m** as swarm grows at `n = 2f+1` | Fig. 2, §V.B | ✅ |
| Complexity: regular `O(N)`, leader `O(N²)`; < 6,000 flops for N ≤ 17 | Table II, §V.C | ✅ |
| Multilateration needs **≥ 3** non-faulty anchors, else fallback | **Algorithm 1, line 17** | ✅ |
| Bibliography = **43 refs** | `[1]`–`[43]` | ✅ |

---

# PART B — OUR `.tex` TEXT → WHICH QUOTE BACKS IT

## USE 1 — the ONLY use, **verified 2026-07-28** — `related.tex` lines **164–185** (`\cite{swarmraft2025}` at line 168)

> ✅ **"Only use" is now PROVEN, not assumed.** Searched `sections/*.tex`, `main.tex`,
> `highlights.tex`: the key `swarmraft2025` occurs **once**; the name `SwarmRaft` occurs
> **once**, same line. No orphan discussion.
>
> ⚠️ **Line numbers drift** — was `~134–137` until a paragraph was inserted above on 2026-07-28.
> Anchor on the `\cite` key: `grep -n "swarmraft2025" sections/*.tex`
> _(USE 2 below is the follow-on contrast inside the same paragraph, not a second citation site.)_

**WE WRITE (verbatim from our manuscript):** "Consensus-based coordination such as
SwarmRaft~\cite{swarmraft2025} fuses peer measurements to maintain agreement on state (e.g.\
position and heading) under degraded conditions"

| Our clause | Backed by |
|---|---|
| "Consensus-based coordination" | **Q1**, **Q5** |
| "fuses peer measurements" | **Q4**, **Q6** |
| "agreement on state (e.g. position and heading)" | **Q1** — *"agree on state updates such as location and heading"*, near-verbatim |
| "under degraded conditions" | **Q1** (*"GNSS-denied conditions"*) + title (*"GNSS-Degraded Environments"*) |

## USE 2 — the follow-on contrast, ~lines 138–147

**WE WRITE:** "These works protect state agreement or model attacks on collective
decision-making; our threat lives one layer below, in the \emph{perception content} that robots
exchange, and our defense verifies that content against the verifier's own sensing rather than
against majority agreement. Because each verdict is pairwise, the mechanism is structurally
independent of the number of liars…"

| Our clause | Backed by |
|---|---|
| "protect state agreement" | **Q1** — position/heading, not perception content |
| "rather than against **majority agreement**" | **Q8**, **Q10** — `n ≥ 2f+1` and majority thresholds are their explicit, load-bearing requirement |
| "pairwise… independent of the number of liars" | **C-3** (ours) — contrast with **Q10** + Algorithm 1's ≥3-anchor requirement |

**Placement check** — the paragraph is headed *"Byzantine resilience in multi-robot systems"*.
**Fair:** the paper itself uses the Byzantine model at the *sensor* layer (**Q8**, **Q11**,
**Q4**) even though its consensus substrate is crash-fault Raft (**Q2**, **Q3**). Our sentence
asserts neither BFT nor crash-only, so it inherits no error either way.

**VERDICT: ✅ VERIFIED — no manuscript change needed.**

---

# PART C — OUR INFERENCE (our words, NOT theirs)

- **C-1 — the layer argument** ("our threat lives one layer below"). Ours. Defensible from
  **Q1** (they agree on *position*, we defend *perception content*), but our framing.
- **C-2 — noise-threshold parallel.** Their `T = µ_e + 3σ_e` calibrated under honest operation is
  the same design instinct as our robust filter (`eps = verify_eps + k_sigma·σ`, k_sigma=4).
  Independent support that noise-aware tolerances are the standard remedy. Ours to observe.
- **C-3 — the recovery-stage anchor requirement.** ⚠️ **REWRITTEN 2026-07-28 after Srinivasa
  rejected the first draft as overclaiming.** The insight survives; the causal language does not.
  Split into paper-fact and interpretation below, per his standard.

### C-3.1 — PAPER FACTS (explicitly stated by the authors)
1. SwarmRaft assumes an **honest-majority model**, requiring `n ≥ 2f+1` (**Q8**, **Q10**).
2. During recovery, **if fewer than three verified (non-faulty) neighbours remain, Algorithm 1
   skips multilateration and falls back to INS propagation** (Algorithm 1 line 17; §III.F note).
3. Figure 2 reports recovery error decreasing from **approximately 19 m** (smallest swarm) to
   **approximately 0.28 m** (largest swarm), and the paper states that **recovery accuracy
   improves with swarm size**.

### C-3.2 — OUR TECHNICAL INTERPRETATION (derived from the algorithm, **not** stated by the authors)
Because multilateration estimates a position from multiple verified neighbours, the recovery
stage requires **enough trusted anchors in addition to** satisfying the protocol's honest-majority
assumption. Algorithm 1 therefore imposes an **algorithmic dependency beyond the security
assumption**: when fewer than three verified neighbours remain, multilateration is not attempted
and the protocol falls back to INS propagation.

**The paper does not explicitly attribute the improvement in Figure 2 to the increasing number of
verified neighbours.** However, this interpretation is consistent with the recovery algorithm,
which estimates positions using multilateration from verified neighbours.

Applied to our threat model (10 drones, 7 adversarial neighbours), SwarmRaft's assumptions are not
satisfied: the protocol violates the required `n ≥ 2f+1` condition, and an honest drone may have
only two honest neighbours, preventing multilateration. **This is our application of the paper's
assumptions to our setting, not a result reported by the authors.**

### C-3.3 — 🚫 SENTENCES THAT MUST NOT BE WRITTEN (Srinivasa, 2026-07-28)
The following appeared in the first draft of C-3 and are **banned** — each asserts something the
paper never demonstrates:

| ❌ Do not write | Why |
|---|---|
| *"The 19 m → 0.28 m curve **proves** this."* | The paper never says that |
| *"The majority rule was satisfied and the method **still couldn't recover**."* | The paper never demonstrates a recovery failure |
| *"Recovery improves **because** there are more anchors."* | Reasonable, but our inference — not their conclusion |

✅ **Say instead:** *"Algorithm 1 requires at least three verified neighbours for multilateration;
otherwise the protocol falls back to INS propagation."* · *"The paper reports that recovery
accuracy improves with swarm size."* · *"One plausible explanation, consistent with the recovery
algorithm, is that larger swarms provide more verified neighbours for multilateration."*

**Use:** this is the answer if a reviewer asks why a
  consensus scheme could not simply be dropped into our setting.
- **C-4 — a small internal tension in their paper** (noted for completeness, not used against
  them): **Q7** says compute and communication modules are honest, yet Attack Scenario 3 allows
  compromised nodes to coordinate *"both their reported measurements and their votes"* — while
  Algorithm 1 has the **leader** compute all votes. Not our concern; do not raise it.

---

# PART D — VERIFIED BY ABSENCE

**D-1 — SwarmRaft defends *position/state*, never *perception content*.** No shared obstacle
maps, no object claims, no sensed-environment exchange anywhere in the paper. What agents
exchange is: GNSS position, INS increments, and inter-node **ranges** (§III.B–D). Its threat
model is GNSS spoofing, range tampering and collusion (**Q11**) — all about *where the drones
are*, never *what they see*. Our layer distinction is therefore structural, not rhetorical.

---

## Second-order sweep — full 43-ref bibliography scanned 2026-07-17, count re-confirmed 2026-07-28
21 keyword hits + 22 non-hits manually reviewed. **Zero new candidates.** Hits: blockchain
consensus classics (PBFT/Castro–Liskov, Tendermint, Exonum, Ouroboros, Raft/Ongaro–Ousterhout,
Dwork partial synchrony, consensus SoKs), DTPBFT (dynamic-trust PBFT for UAV swarms —
consensus-layer trust, not perception content), a VANET security/trust-management review
(message layer), GNSS-spoofing impact studies (sensor layer, no perception exchange), benign
fault-tolerance work (predictive fault tolerance, self-healing topologies, fault-tolerant
cooperative navigation). Non-hits: UAV/GNSS surveys, formation control, comms optimisation,
blockchain whitepapers, flocking. Our consensus-paragraph boundary sentence covers the cluster.

## Bookkeeping
- `refs.bib` `swarmraft2025`: title + all 5 authors match the title page ✅; arXiv:2508.00622 ✅.
  Cited as arXiv preprint ✅ — correct, since the PDF is an IoT-J *manuscript* (`VOL. NN, NO. N`)
  with no acceptance stated. ⚠ Re-check the arXiv Comments field before submission.
- No manuscript edits arise from this audit.

## Re-audit changelog (2026-07-28)
1. **M-1 corrected** — *"combines"* → their actual *"combine"* (**Q6**).
2. Restructured into **Parts A–D**; quotes, inference and absence claims now separated.
3. Every fragment executed first; **four** line-break/spacing traps documented — this PDF is the
   most search-hostile of the four.
4. **C-3 added** — the ≥3-anchor requirement (Algorithm 1) and the 19 m → 0.28 m scaling curve
   give a quantitative version of our no-majority contrast that the previous audit did not have.
5. **D-1 added** — position-vs-perception distinction stated as a checkable absence.
6. Numbers cross-checked against Fig. 2, Table II, Algorithm 1 and the 43-entry reference list.
7. The layered crash-fault/Byzantine nuance was **already correct** and is retained unchanged —
   the strongest part of the original dossier.

_Standing rule: not closed until Srinivasa signs (`AUDIT_PENDING.md`). Committed ≠ audited._
