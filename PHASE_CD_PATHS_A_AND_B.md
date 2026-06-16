# Phase C/D — Two Paths Forward (A: Active Defense, B: Analysis Paper)

**Date:** 2026-06-16
**Why this file exists:** the probes settled the threat landscape with evidence. This documents the
two honest ways forward and how to decide between them — no guessing.

---

## 0. What the evidence established (the starting point)

| Finding | Evidence | Implication |
|---|---|---|
| Communication **deception** is inert | deception probe: ~0pp drop at f=2,3 | LiDAR overrides lies |
| Communication **range/blackout** barely matters | sweep flat 3-8-∞; blackout −5-8pp | swarm is LiDAR-grounded |
| **Physical ramming** is the real threat | ram probe: −9pp per rammer (f=1→3) | this is what to defend |
| **Retraining alone (M1) barely helps** | M1 ≈ M0 (+1-3pp) | implicit evasion insufficient |
| **Even an ORACLE dodge can't recover success** | naive + smart(LiDAR) oracles both ~75-80% | **local evasion is capped ~80%** |

**Core conclusion:** a committed, equal-speed rammer imposes an **oracle-bounded ~15-20pp loss** that
**local per-drone evasion cannot overcome** — it only converts collisions into timeouts. So a "learned
evasion" M2 would plateau where M1 already is. The defense must be **global** (Path A) — or we frame the
**analysis** as the contribution (Path B).

---

## PATH A — Active Defense (build a mechanism that actually helps)

Since *local* evasion is capped, the defense must be **swarm-level**. Three variants, in order of how
well they reconnect the project's pieces:

### A1 ★ Communication-based threat-sharing + trust (RECOMMENDED — unifies everything)
**Idea:** a drone that detects a rammer (hostile motion on its LiDAR) **broadcasts a threat alert**
(rammer location / "under attack"). Teammates use received alerts to (a) avoid the threat zone early —
**including rammers they can't yet see (occluded / beyond their own LiDAR)** — and (b) coordinate.

**Why this is the strongest path:**
- **Gives communication a real, load-bearing job** → finally answers "why use communication?" (early
  warning + beyond-LiDAR / NLOS awareness — the one thing LiDAR can't provide).
- **Revives the deception threat:** a traitor can broadcast **FALSE alerts** to herd honest drones away
  from the goal (→ timeouts) or into danger. So deception matters *again*.
- **Gives the T-Cell trust mechanism a real job:** cross-check a neighbor's threat-alert against your own
  sensing; distrust drones whose alerts don't match reality. **This is the unifying "Trust-Aware" contribution.**

**Honest caveat (from the oracle):** perfect threat info did NOT rescue a *targeted* drone (it dodged into
timeout). So threat-sharing likely **won't recover the targeted drone** — its value is protecting
*not-yet-targeted* drones, enabling coordination, and making trust matter. The contribution becomes
**"trust-aware threat-sharing under false-alert adversaries,"** not "evasion."

**Observation/mechanism:** add a per-neighbor **threat-alert** field (does neighbor j claim a threat near me?)
+ a **trust score** on those alerts (the reserved sync slot). Honest drone reroutes weighted by trusted alerts.

**Feasibility test FIRST (evidence, not guess):** a *threat-sharing oracle* — give every honest drone
perfect, shared knowledge of all rammer positions early (the upper bound of comm warning) and let them
reroute. If even that doesn't beat ~80% → comm-sharing can't rescue targets (expected); its value is then
purely the trust/false-alert story. If it *does* beat ~80% → comm warning genuinely helps; build it.

### A2 — Coordination / screening (teammates intercept the rammer)
**Idea:** healthy drones **body-block or screen** the rammer to protect a targeted teammate (sacrifice
geometry, not the mission). A genuinely *different* mechanism from evasion.
**Feasibility test:** a *coordination oracle* — when a rammer locks a target, the nearest healthy drone is
scripted to interpose. If honest_success rises → coordination works → learn it. If not → drop it.
**Caveat:** interposing means the blocker risks itself; net honest_success may not improve (you trade one
drone for another). The oracle tells us.

### A3 — Asymmetry (targeted drone gets a temporary speed/priority edge)
**Idea:** a drone under attack gets a short speed boost so it can actually outrun an equal-speed pursuer
(an equal-speed pursuer on pure pursuit *can* intercept; a faster evader cannot be caught).
**Feasibility test:** give the targeted drone +X% max speed in the oracle; see if success recovers.
**Caveat:** changes the physics/fairness; must be justified (e.g., "emergency burst"). But it's the one
change that *provably* breaks the interception (speed > pursuer ⇒ uncatchable).

### Path A — process (same evidence-first method that's served us)
1. **Oracle-test the chosen variant FIRST** (cheap, no training) to confirm it can recover success.
2. Only if the oracle beats ~80% → build the learned mechanism (M2) targeting that ceiling.
3. Headline = M1 (no defense) vs M2 (the mechanism), + the trust/false-alert ablation for A1.

### Path A — honest risk
We've now had **three** "promising" angles bounded by data (deception inert, retrain weak, evasion capped).
Path A could be a fourth — so **oracle-test before building.** The *safest* A-contribution is A1's **trust
angle** (false-alert defense), which is novel and uses all the pieces *regardless* of raw success recovery.

---

## PATH B — Analysis / Characterization Paper (honest, ~80% already done)

If you want to wrap up cleanly without a multi-week build, the work you've ALREADY done is a complete,
honest, publishable **characterization** of a LiDAR-grounded swarm's adversarial threat surface.

### B — the claim
> "A LiDAR-grounded MARL swarm is **robust to communication attacks** (deception and jamming are inert
> because sensing overrides them) but **vulnerable to physical adversaries** (ramming), and this physical
> loss is **fundamental**: even an oracle evader with perfect information and obstacle-aware dodging
> cannot recover it — motivating coordination-based defense as future work."

### B — what's ALREADY done (your existing results)
- Phase B: CTDE-clean navigator, 95.6/91.1; full feature-importance ablation (2 methods agree).
- Communication analysis: range sweep (flat), blackout (−5-8pp), **deception probe (inert)**, comm-binding diagnostic.
- Physical threat: **ram scaling f=1/2/3** (linear ~9pp/rammer).
- **Oracle ceiling: naive + smart(LiDAR) evasion both capped ~75-80%** → the fundamental-limit result.
- Leakage test (CTDE clean). Collision-type logging fixed.

### B — what's left (small)
- Confirm the oracle ceiling at **full 200 maps** (currently 30-map; signal already consistent).
- One **baseline** (ORCA via `evaluate_orca.py`).
- Optional multi-seed on the headline model.
- Writeup.

### B — paper structure
1. CTDE swarm navigator (Phase B) — performance + ablation.
2. Communication: helps modestly (occlusion), but the swarm is **robust to comm attacks** (deception/jamming inert). *Security property.*
3. Physical adversaries: ram threat scales linearly; **oracle-bounded ~15-20pp irreducible loss** for local methods.
4. Implication: physical resilience needs **coordination**, not local evasion (future work).

### B — honest assessment
A solid, *honest* characterization/analysis paper (a "what works, what doesn't, and the fundamental limit"
story). Mid-tier venue realistic. Weaker "novelty" than a working defense, but **fully supported by data
you already have** and zero risk of another bounded-angle surprise.

---

## Decision criteria (A vs B)

| If you... | Choose |
|---|---|
| have ~3-5 weeks and want a "we built a trust-aware defense" paper | **A1** (comm threat-sharing + trust), oracle-test first |
| want the unifying "Trust-Aware" story salvaged (comm + deception + trust all matter) | **A1** |
| want to wrap up honestly & soon with what's proven | **B** |
| are unsure | run the **A1 threat-sharing oracle** (1 day) — if it helps, do A; if not, do B |

**Recommended:** spend **one day** on the **A1 threat-sharing feasibility oracle** (+ the false-alert
trust angle). It's the highest-value test: it either unlocks Path A (and rescues the Trust-Aware framing)
or confirms Path B — and it directly answers your "detect+reroute via comm" question with data.

---

## On "detect + reroute via the communication channel" (your question)

- **Yes, do it via comm** — that's the *point*: comm shares threats LiDAR can't see (occluded/early), giving
  communication its first load-bearing role and reviving deception (false alerts) + trust (filter them).
- **But oracle-test the success claim:** the oracle proved perfect info doesn't rescue a *targeted* drone,
  so frame the win as **(a) protecting un-targeted drones + (b) trust-aware false-alert defense**, not "evasion."
- **The trust angle is the safe, novel contribution** even if raw recovery is bounded: *"honest drones share
  threat alerts; a traitor injects false alerts to herd the swarm; the T-Cell trust mechanism detects and
  ignores false alerts by cross-checking against local sensing."* That's a clean, defensible Trust-Aware paper.

---

## NOTES / QUESTIONS FOR CLAUDE
-
-
