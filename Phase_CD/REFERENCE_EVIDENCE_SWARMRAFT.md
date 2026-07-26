# SwarmRaft — paired claim/evidence sheet (full read, 2026-07-17)

## STATUS: ✅ CLOSED (2026-07-26) — verified independently by Srinivasa
Full 10-page read (arXiv:2508.00622v2). **No catches — our single descriptive sentence is
near-verbatim to their abstract.** One nuance documented (crash-fault consensus + Byzantine
sensor model) that a picky reviewer could raise; our wording already avoids it. Closed only
after Srinivasa's own audit.

**The paper:** Kapel Dev, Yash Madhwal, Sofia Shevelo, Pavel Osinenko, Yury Yanovich,
*"SwarmRaft: Leveraging Consensus for Robust Drone Swarm Coordination in GNSS-Degraded
Environments"*, arXiv:2508.00622v2 (25 Sep 2025), Skolkovo Institute of Science and Technology.
IEEE IoT Journal manuscript format ("VOL. NN" — not yet published).
PDF: `Phase_CD/Research paper/SwarmRaft.pdf` (10 pages).

**What the paper does (their own words):** *"a blockchain-inspired positioning and consensus
framework for maintaining coordination and data integrity in UAV swarms operating under
GNSS-denied conditions. SwarmRaft leverages the Raft consensus algorithm to enable distributed
drones (nodes) to agree on state updates such as location and heading"* (Abstract). Per-step
workflow (§III.A): leader elected via Raft collects each node's GNSS/INS position + inter-node
ranges, tests consistency (residual vs threshold T = µ_e + 3σ_e calibrated under honest
operation), votes honest/faulty, recovers faulty positions from peer estimates.

**The layered fault model (the nuance):**
- Consensus/communication layer = CRASH-fault Raft, explicitly NOT BFT: *"Byzantine
  Fault-Tolerant (BFT) protocols … assume adversarial behavior and incur unnecessary
  complexity for typical crash-fault scenarios in swarms"*; *"Raft … designed for environments
  where nodes (the drones) may fail by crashing, but not by acting maliciously"* (§I);
  Assumption 1: *"Nodes' compute and communication modules are honest"*.
- Sensor layer = BYZANTINE: Assumption 2: *"Only GNSS sensors can be Byzantine … Up to f
  nodes' GNSS sensors out of n may be arbitrarily corrupted, where n ≥ 2f + 1"*; a
  *"Byzantine-resilient evaluation mechanism to detect and correct malicious or faulty
  position reports"* (§III.A); attack scenarios: GNSS spoofing, ranging tampering, collusion
  among ≤ f sensors (§III.B).
- **Honest majority REQUIRED:** *"By enforcing the requirement n ≥ 2f+1 and using majority
  thresholds, the scheme guarantees that honest votes outnumber colluding malicious votes"*
  (§III.B). Also leader-based (elected leader does estimation/evaluation each step).

---

## USE 1 (the ONLY use) — related.tex ~lines 128–131 (Byzantine-resilience paragraph)
**WE WRITE (verbatim):** "Consensus-based coordination such as SwarmRaft~\cite{swarmraft2025}
fuses peer measurements to maintain agreement on state (e.g.\ position and heading) under
degraded conditions"

**THEY WROTE, phrase by phrase:**
- "Consensus-based coordination" ✓ — *"consensus-driven positioning"*, *"consensus framework
  for maintaining coordination"* (Abstract, §II close: *"lightweight, crash-tolerant
  localization framework that combines peer-based voting with distributed fault recovery"*).
- "fuses peer measurements" ✓ — *"peer-to-peer distance measurements"* (§III.A), *"combines
  GNSS, INS, and peer-to-peer fusion"* (§I), *"SwarmRaft's fused estimation"* (§III.D).
- "agreement on state (e.g. position and heading)" ✓ — **near-verbatim**: *"agree on state
  updates such as location and heading"* (Abstract).
- "under degraded conditions" ✓ — *"GNSS-Degraded Environments"* (title), *"GNSS-denied
  conditions"* (Abstract).

**Placement check (the paragraph is headed "Byzantine resilience in multi-robot systems"):**
fair — the paper itself uses the Byzantine model at the sensor layer (Assumption 2, the
"Byzantine-resilient evaluation mechanism") even though its consensus substrate is
crash-fault Raft. Our sentence claims neither BFT nor crash-only, so it inherits no error
either way.

**Follow-on contrast (lines 132–137), verified:** "These works protect state agreement …
verifies that content against the verifier's own sensing rather than against majority
agreement --- which is what permits operation without an honest local majority."
- SwarmRaft protects state agreement ✓ (position/heading).
- Majority agreement ✓ — n ≥ 2f+1 with majority voting is their explicit, load-bearing
  requirement, plus an elected leader. Our pairwise/no-majority/no-leader contrast is exactly
  right against this paper.

**VERDICT: ✅ VERIFIED — no change needed.**

---

## Corroborations noted (no manuscript change)
- Their fault-detection threshold (T = µ_e + 3σ_e from offline calibration under honest
  operation, Gaussian tail bound <0.01) is the same noise-calibrated-tolerance design as our
  robust filter (eps = verify_eps + k_sigma·σ, k_sigma=4) — independent support that
  noise-aware thresholds are the standard remedy; theirs guards position reports under an
  honest majority + leader, ours guards obstacle claims pairwise.
- Their Attack Scenario 1 (GNSS spoofing = position reports "offset by an arbitrary,
  potentially time-varying bias") is a persistent-bias threat like our camouflage offset —
  but detected spatially per-step against the peer-derived feasible region (needs the honest
  majority), not temporally accumulated.

## Second-order sweep (standing rule) — FULL 43-ref bibliography title scan done 2026-07-17
21 keyword hits + 22 non-hits manually reviewed. **Zero new candidates.** The hits are:
blockchain-consensus classics (PBFT/Castro-Liskov, Tendermint, Exonum, Ouroboros, Raft,
Dwork partial-synchrony, consensus SoKs), DTPBFT (dynamic-trust PBFT for UAV swarms —
consensus-layer blockchain trust, not perception content), a VANET security/trust-management
REVIEW (message layer; the van der Heijden survey judgment call in PRIOR_ART_SECOND_ORDER
item 5 already covers this niche), GNSS-spoofing impact on UAV swarms (sensor-layer attack
study, no perception exchange), and benign fault-tolerance works (predictive fault tolerance,
self-healing topologies, fault-tolerant cooperative navigation/topology). Non-hits: UAV/GNSS
surveys, formation control, comm optimization, blockchain whitepapers, flocking. Our
consensus-paragraph boundary sentence ("protect state agreement or collective
decision-making; our threat lives one layer below") covers the entire cluster.

## Srinivasa's verification checklist (page pointers, arXiv v2)
| # | what to check | where in PDF |
|---|---|---|
| 1 | "agree on state updates such as location and heading" (our near-verbatim source) | p.1 Abstract |
| 2 | crash-fault Raft choice, explicitly NOT BFT | p.1 §I (last paragraphs) |
| 3 | Byzantine SENSOR model + n ≥ 2f+1 honest majority + leader | p.3 §III.A–B, Assumptions 1–3 |
| 4 | peer-to-peer distance fusion / feasible-region localization | p.3–4 §III.A, §III.D |

## Bookkeeping
- refs.bib `swarmraft2025`: title + all 5 authors match the PDF title page ✓;
  arXiv:2508.00622 ✓. Cited as arXiv preprint ✓ — correct, the PDF is an IEEE IoT-J
  *manuscript* ("VOL. NN, NO. N") with no acceptance stated. ⚠ Same pre-submission
  venue re-check as PRBI/CoDynTrust (arXiv Comments field).
- No catches; no manuscript edits from this audit.
