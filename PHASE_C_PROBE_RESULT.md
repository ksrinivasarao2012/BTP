# Phase C Deception Probe — Result & Decision

**Date:** 2026-06-15
**Test:** existing `comm8_lidar` model (no retrain, no trust), f traitors with falsified broadcasts,
LiDAR kept true. Metric: honest_success over (n−f). Baseline (no traitors): 95.55% / 91.10%.

## Results

| Attack | density 0.20 | density 0.30 | max drop |
|--------|-------------:|-------------:|---------:|
| f=2 false_velocity | 95.31% | 91.38% | +0.24 pp |
| f=2 false_position | 95.38% | 91.31% | +0.17 pp |
| f=3 both (pos+vel) | 94.86% | 91.07% | +0.69 pp |

All within ±0.7pp = **noise**. (Files: `results/phase_c_probe/`.)

## Verdict
**Communication-based DECEPTION is NOT an effective attack on this swarm.** Even 3 traitors lying about
both position and velocity cause no measurable harm.

## Why
The swarm is **LiDAR-grounded**: a liar's true body still appears in honest drones' LiDAR (12m), which
dominates the policy (saliency 1.19 vs neighbor-comm 0.45). The goal is map-derived (Dijkstra, not
communicated), obstacles are sensed. So **there is no deception channel that LiDAR cannot override** →
lies are ignored. (Consistent with: comm-range sweep flat, comm=0 ≈ comm=8.)

## This is a FINDING (security property), not a failure
> "A LiDAR-grounded swarm is inherently robust to communication attacks — denial (jamming/blackout) and
> deception alike — because safety-critical information is sensed, not communicated."

## DECISION → pivot from informational to PHYSICAL adversaries
1. **Next probe:** physical aggression — traitors steer to **ram / block** honest drones (zero-shot on
   `comm8_lidar`). If honest_success drops → that is the real threat to defend.
2. **Reframe the defense:** against physical attackers the detector is **behavioral (LiDAR-based hostile-
   motion detection)**, NOT comm-vs-LiDAR mismatch (a rammer need not lie). Matches the "behavioral outlier
   detection" literature; needs no communication.
3. **Do NOT** build the comm-deception trust mechanism as the headline — there is nothing for it to defend.
4. **Do NOT** engineer the architecture to *make* comm matter — that would be manufacturing a result.

## Status of prior Phase C plan docs
`PHASE_C_TRUST_DESIGN.md` / `PHASE_CD_TRAITOR_ATTRIBUTES_AND_TIMELINE.md` assumed deception was the primary
threat. After this result, the deception/comm-mismatch trust mechanism is **deprecated as the headline**;
the behavioral/physical-aggression direction supersedes it. Update those docs if the physical probe confirms
a threat.
