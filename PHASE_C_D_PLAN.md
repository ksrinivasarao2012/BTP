# Phase C & Phase D — Design & Experiment Plan (Trust-Aware Resilience)

**Status:** planning (Phase B complete; this is the path to the headline contribution)
**Last updated:** 2026-06-15

---

## 0. Why this plan exists (the bridge from Phase B)

Phase B established the foundation that makes Phase C/D meaningful:

| Phase B finding | Consequence for C/D |
|-----------------|---------------------|
| Communication range is irrelevant (3≈8≈∞) | Don't bother attacking *range*; attack *content* |
| Communication **content** is load-bearing (blackout: collisions ↑3–5×, success −5–8pp) | Corrupting communication is a **real threat** worth defending |
| Drone-drone avoidance is done by **LiDAR**, not comm | A traitor can't blind LiDAR → must attack via **deception** (lies the policy trusts) |
| Actor is CTDE-clean (leakage test PASS); reserved trust slot exists in sync_features | The defense input channel is already in place |

**Core thesis of Phase C/D:** A silent dropout is survivable (LiDAR fallback). A **lying** agent is not — the policy *acts on false data*. The Trust-Aware (T-Cell) mechanism detects liars by cross-checking communicated state against LiDAR-sensed reality, restoring resilience.

---

## 1. The success metric under adversaries (IMPORTANT — changes from Phase B)

Traitors do not try to reach the goal, so they must be **excluded from the denominator**.

```
honest_success = (honest drones that reached goal) / (number of honest drones) * 100
```

With 2 traitors out of 10 → denominator = 8. (5 honest reach → 5/8 = 62.5%, NOT 5/10.)

**Additional metrics to report (the traitor's "damage"):**
- `honest_success` (primary)
- `honest_collision_rate` — split into: collisions **caused by a traitor** vs honest-honest vs obstacle
- `honest_timeout_rate`
- `traitor_detection_rate` (Phase C+): fraction of traitor-steps correctly flagged low-trust
- `false_positive_rate`: honest neighbors wrongly distrusted
- `time_to_detect`: steps until a traitor is flagged

Env hooks already exist: set `num_traitors`, `num_honest` (currently 0 / 10).

---

## 2. PHASE C — Deceptive traitors + the trust mechanism

### 2.1 Threat model (Phase C = deception, not yet physical aggression)
Traitors are physically present (LiDAR sees them) and navigate plausibly, but **lie on the communication channel**:
- **C-attack-1 — false position:** broadcast a position offset from the true one.
- **C-attack-2 — false velocity/intent:** broadcast a velocity pointing away from actual motion (poisons honest drones' collision anticipation).
- **C-attack-3 — fake stagnation:** broadcast high stagnation ("I'm stuck") to trigger needless rerouting/timeouts.
- Start with one attack type, then combined.

### 2.2 The defense — T-Cell trust mechanism
Each honest drone, for each neighbor `j` it can sense **and** hear:
1. Compare **communicated** state (broadcast pos/vel) against **LiDAR-sensed** state (actual pos, inferred motion).
2. Large, persistent discrepancy → **low trust** for `j`.
3. Write the trust score into the **reserved trust slot** in sync_features (the `0.0` placeholder from Phase B).
4. Policy learns to **down-weight / ignore** low-trust neighbors and rely on LiDAR for them.

Design choices to decide:
- Trust as a **hand-designed detector** (discrepancy threshold + decay) vs a **learned** head. Recommended: start hand-designed (interpretable, easy to validate), then optionally learned.
- Trust scale: `0.0 = trusted` (consistent with Phase B all-zeros), rising toward `1.0 = suspected traitor`.
- Trust is **per-neighbor**, updated each step, with temporal smoothing (one bad reading ≠ permanent distrust).

### 2.3 Training
- **Transfer from the comm-enabled 8m model** (NOT comm=0 — the comm pathway must be alive). Use the final CTDE-clean 8m model from Phase B.
- Curriculum: introduce traitors gradually (e.g., 0 → 1 → 2 traitors; mild → strong deception).
- Keep LiDAR 12m, comm 8m, densities as in Phase B for comparability.
- The trust slot, dormant in Phase B, now receives real signal → its weights "wake up" during C training.

### 2.4 Phase C experiments (the headline)
| ID | Condition | Measures |
|----|-----------|----------|
| C-0 | No traitors (sanity) | honest_success ≈ Phase B 8m |
| C-1 | 2 traitors, deception, **trust OFF** | baseline damage |
| C-2 | 2 traitors, deception, **trust ON** | resilience |
| C-3 | C-1 vs C-2 per attack type (pos / vel / stagnation) | which attack hurts, which trust defends |
| C-4 | sweep #traitors (1,2,3) trust ON vs OFF | scaling of defense |

**Headline result:** `honest_success` with traitors, **trust ON vs OFF**. The gap = the T-Cell contribution. Plus `traitor_detection_rate` / `false_positive_rate` to show the mechanism works, not just that scores improve.

### 2.5 Honest caveat (plan around it)
Because the swarm is **LiDAR-dominant**, *pure* deception has a bounded ceiling (LiDAR + goal-dir = ~70% of the decision, un-forgeable). So Phase C deception-only may show a **modest** trust-ON vs trust-OFF gap. Two mitigations:
- Use **combined** deception (pos + vel + stagnation) to maximize the corruptible surface.
- If the gap is small, that itself is an honest finding ("the LiDAR-grounded policy is inherently robust to deception; trust adds X%") — but the **strong** adversarial story needs Phase D (physical aggression).

---

## 3. PHASE D — Aggressive traitors + full TA-MAPPO

### 3.1 Threat model (Phase D = deception + physical aggression)
Traitors actively try to **cause collisions / block** honest drones:
- **D-attack-1 — ramming:** maneuver toward honest drones to collide.
- **D-attack-2 — blocking:** park in chokepoints / on the shortest path.
- **D-attack-3 — deception + ramming:** lie about velocity *while* charging (LiDAR sees position, but anticipation is poisoned) — the hardest case.

This is where the threat is unambiguous: LiDAR detects the physical traitor, but avoiding an *actively hostile* mover (that also lies) is genuinely hard — so the defense clearly matters.

### 3.2 Defense — full TA-MAPPO
- Trust mechanism from Phase C **+** learned evasive/robust policy against hostile movers.
- Honest drones: distrust liars (comm cross-check) **and** treat low-trust physical neighbors as high-priority dynamic obstacles (avoid aggressively via LiDAR).

### 3.3 Training
- Transfer from the **Phase C** trust-aware model.
- Curriculum: passive traitors → blocking → ramming → ramming+deception; 1 → 2 → 3 traitors.

### 3.4 Phase D experiments
| ID | Condition | Measures |
|----|-----------|----------|
| D-0 | Phase C model vs aggressive traitors (no D-training) | how badly C alone fails |
| D-1 | 2 aggressive traitors, **TA-MAPPO OFF** (no trust/robustness) | baseline damage |
| D-2 | 2 aggressive traitors, **TA-MAPPO ON** | resilience |
| D-3 | attack-type breakdown (ram / block / ram+lie) | what TA-MAPPO defends |
| D-4 | scaling: 1/2/3 aggressive traitors | breakdown point |

**Headline result:** `honest_success` under aggressive traitors, **TA-MAPPO ON vs OFF**, with detection metrics. This is the paper's culmination.

---

## 4. Implementation checklist (env + training + eval)

### Env (`swarm_env_step_B10_8_0m.py` or a Phase-C fork)
- [ ] `num_traitors` / `num_honest` honored throughout (spawn, metrics, termination).
- [ ] Traitor behavior policy: deception (corrupt the broadcast that honest drones receive) and/or scripted/learned hostile maneuvers.
- [ ] Honest observation: traitor's **communicated** state is the (possibly false) broadcast; traitor's **LiDAR** signature is the true physical position.
- [ ] Populate the **trust slot** in sync_features with the T-Cell score (replaces the Phase B `0.0`).
- [ ] Metrics: `honest_success`, traitor-caused collisions, detection/false-positive rates. Collision typing already fixed (env tags `collision_type`).
- [ ] Keep CTDE clean: trust computed from **locally available** signals (own LiDAR + received broadcasts), never ground truth.

### Training
- [ ] Phase C: transfer from CTDE-clean 8m model; traitor + deception curriculum.
- [ ] Phase D: transfer from Phase C model; aggression curriculum.

### Eval (reuse the fixed harness)
- [ ] Same 200-maps/density, deterministic, fixed counting, paired seeds.
- [ ] Report over **honest** drones only.
- [ ] trust/TA-MAPPO ON vs OFF as the paired comparison.

---

## 5. CTDE / rigor guardrails (carry over from Phase B)

- Trust score must be computed from **locally observable** quantities only (own LiDAR + received messages). Do **not** use ground-truth "is this drone a traitor" as policy input — that would be a leak (it's the label, available only at training for metrics).
- Re-run the **leakage test** on the Phase C/D actor (global state must not affect the action).
- Honest framing: distinguish "comm is *used*" (Phase B blackout) from "comm-deception is *defended*" (Phase C trust ON vs OFF).
- Single-seed caveat still applies — note it; add seeds if a venue demands.

---

## 6. The paper arc (how it all connects)

1. **Phase B:** resilient navigation; communication is load-bearing for coordination but range-insensitive; LiDAR handles drone-avoidance. (Foundation + motivation.)
2. **Phase C:** a deceptive agent that lies on the (load-bearing) comm channel degrades the swarm; the T-Cell trust mechanism detects and neutralizes it. (Core contribution.)
3. **Phase D:** against *aggressive* traitors (lie + ram), full TA-MAPPO sustains honest success where the undefended swarm collapses. (Culmination.)

**One-line pitch:** *"Communication makes the swarm coordinate but also makes it attackable; TA-MAPPO keeps an honest swarm reaching its goal even when adversaries lie and ram."*

---

## 7. Open decisions (for you to choose)

- [ ] Trust mechanism: hand-designed detector first, or learned head? (recommend hand-designed first)
- [ ] Number of traitors for the headline (2/10 is a clean 20%).
- [ ] Phase C deception: single attack type for clarity, or combined for impact?
- [ ] Whether Phase C and D are separate papers or one paper with two results.
- [ ] Add training seeds for statistical significance? (venue-dependent)

---

## 8. NOTES / QUESTIONS FOR CLAUDE
-
-
